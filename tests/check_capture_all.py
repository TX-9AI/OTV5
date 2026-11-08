#!/usr/bin/env python3
"""
tests/check_capture_all.py  v5.0
v5.0  2026-11-08  OTV5 r94 (CAP.1) — new. tools/capture_all.py records everything TastyTrade serves that the feed does
      not keep, into the warehouse; deploy/install_capture_timer.sh schedules it; retention_purge v5.3 purges its spool.
      The operator, 2026-11-08: "If they offer it, we better be downloading it. Non-negotiable."

  C1  RECORDING ONLY, inbound: no module outside tools/capture_all.py (and this gate / the file map) names capture_all,
      capture_spool, or the new warehouse prefixes, so no trading code path can read what it records
  C2  RECORDING ONLY, outbound: capture_all imports nothing from strategy/, execution/, risk/, derived/, main or config
      (its only repo import is data.tasty_client)
  C3  REST only in the scheduled modes: the timer runs metrics / chain / events; DXLinkStreamer appears only in _candles
  S1  spool_put: a successful PUT deletes the spool file; a failing PUT keeps it and returns KEPT; flush re-puts it
  S2  dry run PUTs nothing and leaves nothing in the spool
  K1  keys: metrics -> raw/market_metrics/dt=<ET day>/sym=<box>/HHMMSS.json.gz; chain -> raw/chain_rest/...; the chain
      listing -> raw/chain_listing/...; events -> raw/corporate_events/kind=/sym=/pulled=
  K2  the RAW response is stored whole: a field TastyTrade adds tomorrow survives the round trip (no model, no column list)
  B1  chain batches are at most 100 symbols (the by-type combined limit) and every option of every expiry is asked
      when --max-dte is not given; --max-dte drops only the later expiries
  T1  the installer writes three timers at the documented times, REST modes only, MemoryMax and idle IO set
  R1  retention_purge: spool files older than 3 days are counted (dry) / removed (apply); fresh files and dirs untouched
"""
from __future__ import annotations

import gzip
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

RAN, FAILED = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(("PASS " if ok else "FAIL ") + name + ("" if ok or not detail else f"  -- {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _py_files():
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in (".git", "venv", "__pycache__", "data", "logs", "node_modules")]
        for f in files:
            if f.endswith((".py", ".sh")):
                yield os.path.join(d, f)


def main() -> int:
    import tools.capture_all as ca

    # ── C1 / C2 / C3 ──
    allowed = {os.path.join(ROOT, p) for p in ("tools/capture_all.py", "tests/check_capture_all.py",
                                                "tests/gen_file_map.py", "deploy/install_capture_timer.sh",
                                                "warehouse/retention_purge.py", "setup_ec2.sh",
                                                "tests/check_bootstrap.py")}
    pat = re.compile(r"capture_all|capture_spool|raw/market_metrics|raw/chain_rest|raw/chain_listing|"
                     r"raw/corporate_events|raw/candles_full")
    hits = [os.path.relpath(p, ROOT) for p in _py_files() if p not in allowed and pat.search(open(p, errors="ignore").read())]
    check("C1 recording only: nothing else in the tree names capture_all, its spool or its prefixes", not hits, str(hits))
    src = open(os.path.join(ROOT, "tools", "capture_all.py")).read()
    imps = re.findall(r"^\s*(?:from|import)\s+([\w.]+)", src, re.M)
    bad = [i for i in imps if i.split(".")[0] in ("strategy", "execution", "risk", "derived", "main", "config",
                                                  "warehouse", "database", "notifications", "analysis")]
    repo = [i for i in imps if i.split(".")[0] in ("data",)]
    check("C2 capture_all imports no trading code (only data.tasty_client)", not bad and set(repo) <= {"data.tasty_client"},
          f"bad={bad} repo={repo}")
    inst = open(os.path.join(ROOT, "deploy", "install_capture_timer.sh")).read()
    dx_where = [m.start() for m in re.finditer(r"DXLinkStreamer", src)]
    cand_s, cand_e = src.index("async def _candles"), src.index("def do_candles")
    check("C3 timer modes are metrics/chain/events only; DXLink appears only inside _candles",
          'MODES="metrics chain events"' in inst and "candles" not in inst.split("MODES=")[1].split("\n")[0]
          and all(cand_s <= w < cand_e for w in dx_where[1:]) and dx_where,
          f"dx at {dx_where}")

    # ── S1 / S2 ──
    tmp = tempfile.mkdtemp()
    ca.SPOOL = os.path.join(tmp, "spool")
    puts = []

    class OK:
        def put_object(self, **kw):
            puts.append(kw["Key"])

    class Bad:
        def put_object(self, **kw):
            raise OSError("no s3")

    fake = types.ModuleType("boto3")
    sys.modules["boto3"] = fake
    fake.client = lambda *_a, **_k: OK()
    r1 = ca.spool_put("raw/x/a.json.gz", b"abc", False)
    left1 = os.listdir(ca.SPOOL)
    fake.client = lambda *_a, **_k: Bad()
    r2 = ca.spool_put("raw/x/b.json.gz", b"abc", False)
    left2 = os.listdir(ca.SPOOL)
    fake.client = lambda *_a, **_k: OK()
    n = ca.flush_spool(False)
    check("S1 PUT ok deletes; PUT fail keeps (KEPT); flush re-puts and empties",
          r1 == "PUT" and left1 == [] and r2 == "KEPT" and len(left2) == 1 and n == 1
          and os.listdir(ca.SPOOL) == [] and puts == ["raw/x/a.json.gz", "raw/x/b.json.gz"], f"{r1} {r2} {n} {puts}")
    puts.clear()
    r3 = ca.spool_put("raw/x/c.json.gz", b"abc", True)
    check("S2 dry run PUTs nothing, leaves nothing", r3 == "DRY" and not puts and os.listdir(ca.SPOOL) == [])

    # ── K1 / K2 / B1 with a fake session ──
    calls = []
    chain = {"items": [{"expirations": [
        {"expiration-date": "2026-11-09", "strikes": [{"call": f"C{i}", "put": f"P{i}"} for i in range(120)]},
        {"expiration-date": "2027-12-17", "strikes": [{"call": f"LC{i}", "put": f"LP{i}"} for i in range(30)]}]}]}

    def fake_get(_s, path, params=None):
        calls.append((path, params))
        if path.startswith("/option-chains/"):
            return chain
        if path == "/market-data/by-type":
            syms = next(iter(params.values()))
            return {"items": [{"symbol": s, "open-interest": 7, "brand-new-field": {"x": 1}} for s in syms]}
        if path == "/market-metrics":
            return {"items": [{"symbol": "SPX", "implied-volatility-index-rank": "0.3", "future-field": 42}]}
        if "historic-corporate-events" in path:
            return {"items": [{"occurred-date": "2026-01-01"}]}
        return {"risk-free-rate": "0.04"}

    ca._get = fake_get
    ca.PAUSE_S = 0
    os.environ["OT_INSTRUMENT"] = "SPX"
    fake.client = lambda *_a, **_k: OK()
    stored = {}

    class Keep:
        def put_object(self, **kw):
            stored[kw["Key"]] = json.loads(gzip.decompress(kw["Body"]))

    fake.client = lambda *_a, **_k: Keep()
    ca.do_metrics(None, ["SPX"], False)
    ca.do_chain(None, ["SPX"], None, False)
    ca.do_events(None, ["SPX", "AMZN"], False)
    keys = sorted(stored)
    day = ca.et_now().date()
    k_ok = (any(re.fullmatch(rf"raw/market_metrics/dt={day}/sym=SPX/\d{{6}}\.json\.gz", k) for k in keys)
            and any(re.fullmatch(rf"raw/chain_rest/dt={day}/sym=SPX/\d{{6}}\.json\.gz", k) for k in keys)
            and f"raw/chain_listing/dt={day}/sym=SPX/chain.json.gz" in keys
            and f"raw/corporate_events/kind=earnings/sym=AMZN/pulled={day}.json.gz" in keys
            and f"raw/corporate_events/kind=dividends/sym=AMZN/pulled={day}.json.gz" in keys
            and not any("sym=SPX/pulled" in k and "corporate" in k and "risk_free" not in k for k in keys))
    check("K1 warehouse keys per mode (an index has no earnings/dividends)", k_ok, str(keys))
    m = next(v for k, v in stored.items() if "market_metrics" in k)
    ch = next(v for k, v in stored.items() if "chain_rest" in k)
    check("K2 raw stored whole: unknown fields survive (metrics future-field, by-type brand-new-field)",
          m["response"]["items"][0].get("future-field") == 42
          and ch["options"][0].get("brand-new-field") == {"x": 1} and m["meta"]["source"] == "tastytrade")
    bt = [p for path, p in calls if path == "/market-data/by-type" and "equity-option" in p]
    asked = [s for p in bt for s in p["equity-option"]]
    check("B1 batches <= 100 and every option of every expiry asked",
          all(len(p["equity-option"]) <= 100 for p in bt) and len(asked) == 300 and len(set(asked)) == 300
          and ch["meta"]["asked"] == 300 and len(ch["options"]) == 300, f"{len(asked)} batches={len(bt)}")
    calls.clear()
    stored.clear()
    ca.do_chain(None, ["SPX"], 45, False)
    asked45 = [s for path, p in calls if path == "/market-data/by-type" and "equity-option" in p for s in p["equity-option"]]
    check("B1b --max-dte 45 drops only the 2027 expiry", len(asked45) == 240 and not any(s.startswith("L") for s in asked45),
          str(len(asked45)))

    # ── T1 ──
    cal = re.findall(r"(\w+)\)\s+printf '([^']*)'", inst)
    times = {k: re.findall(r"(\d\d:\d\d):00", v) for k, v in cal}
    check("T1 three timers at 09:38/15:52, 09:42/12:30/16:15, 16:25; idle IO, MemoryMax",
          times == {"metrics": ["09:38", "15:52"], "chain": ["09:42", "12:30", "16:15"], "events": ["16:25"]}
          and "IOSchedulingClass=idle" in inst and "MemoryMax=" in inst, str(times))

    # ── R1 ──
    import warehouse.retention_purge as rp
    sp = os.path.join(tmp, "spool2")
    os.makedirs(os.path.join(sp, "adir"))
    old, new = os.path.join(sp, "old.gz"), os.path.join(sp, "new.gz")
    for p in (old, new):
        open(p, "wb").write(b"x")
    os.utime(old, (time.time() - 4 * 86400,) * 2)
    dry = rp._spool_purge(sp, rp.CAPTURE_SPOOL_DAYS, False)
    still = os.path.exists(old)
    app = rp._spool_purge(sp, rp.CAPTURE_SPOOL_DAYS, True)
    check("R1 spool purge: >3 days counted dry, removed on apply; fresh file and dir kept",
          rp.CAPTURE_SPOOL_DAYS == 3 and dry == 1 and still and app == 1 and not os.path.exists(old)
          and os.path.exists(new) and os.path.isdir(os.path.join(sp, "adir")))
    rsrc = open(os.path.join(ROOT, "warehouse", "retention_purge.py")).read()
    check("R1b retention_purge's run calls the spool purge", 'removed["spool/capture_spool"] = _spool_purge(' in rsrc)

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} of {len(RAN)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
