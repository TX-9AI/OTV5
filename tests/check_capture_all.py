#!/usr/bin/env python3
"""
tests/check_capture_all.py  v5.2
v5.2  2026-11-08  OTV5 r99 (CAP.6) — measured on the fleet: candles-recent needs candle-feed stopped too (G1), it has no
      timer any more (C3/T1 back to the three REST timers, plus the r98 unit removed), and the front-futures lookup runs in
      the streams' own event loop (F1 pick_front + the async lookup; W1 fails if tasty_client.run_async is used).
v5.1  2026-11-08  OTV5 r98 (CAP.6) — candles-recent: C3/T1 re-stated for the fourth timer (it opens a stream, so it must
      refuse while optionsbot is active: G1); L1 the lookback windows and labels (1d / 1d_eth / 1h / 5m, the extended-hours
      daily asked with extended_trading_hours=True); F1 front-month futures from /instruments/futures; W1 the SPX box adds
      CONTEXT + futures; C1 allows warehouse/self_close.py, which RUNS the tool (it reads nothing it records).
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
  T1  the installer writes three timers at the documented times (REST modes), MemoryMax and idle IO set, and removes
      r98's optbot-capture-candles-recent unit where present
  G1  candles-recent refuses (no session opened) while optionsbot or candle-feed is active; unknown counts as active
  L1  candles-recent asks 1d (21 d), 1d extended hours (21 d, label 1d_eth), 1h (5 d), 5m (3 d), one stream at a time,
      and files each under raw/candles_full/interval=<label>/
  F1  pick_front / _front_futures: the active-month contract per product, else the nearest; none -> skipped, not guessed
  W1  on the SPX box candles-recent adds CONTEXT and the front futures (looked up in the same loop); elsewhere only its own
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
                                                "warehouse/self_close.py",
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
    cal = re.findall(r"([\w-]+)\)\s+printf '([^']*)'", inst)
    times = {k: re.findall(r"(\d\d:\d\d):00", v) for k, v in cal}
    check("T1 three timers at 09:38/15:52, 09:42/12:30/16:15, 16:25; idle IO, MemoryMax; r98's candles-recent unit "
          "is removed where present",
          times == {"metrics": ["09:38", "15:52"], "chain": ["09:42", "12:30", "16:15"], "events": ["16:25"]}
          and "IOSchedulingClass=idle" in inst and "MemoryMax=" in inst
          and 'RETIRED="candles-recent"' in inst and 'rm -f "/etc/systemd/system/optbot-capture-$m.timer"' in inst,
          str(times))

    # ── G1 / L1 / F1 / W1 ──
    import asyncio
    opened = []

    async def fake_candles(_s, symbols, interval, since, idle_s=20.0, max_s=600.0, eth=False):
        opened.append((tuple(symbols), interval, since.date(), eth))
        return {sym: {1793836800000: {k: (sym if k == "event_symbol" else 1793836800000 if k == "time" else 1.0)
                                      for k in ca.CANDLE_FIELDS}} for sym in symbols}

    fut = {"ES": {"items": [{"streamer-symbol": "/ESU26:XCME", "expiration-date": "2026-09-18"},
                            {"streamer-symbol": "/ESH27:XCME", "expiration-date": "2027-03-19"},
                            {"streamer-symbol": "/ESZ26:XCME", "expiration-date": "2026-12-18", "active-month": True}]},
           "NQ": {"items": [{"streamer-symbol": "/NQZ26:XCME", "expiration-date": "2026-12-18"},
                            {"streamer-symbol": "/NQH27:XCME", "expiration-date": "2027-03-19"}]},
           "XX": {"items": []}}

    class FakeSession:
        loops = []

        async def _get(self, path, params=None):
            FakeSession.loops.append(asyncio.get_running_loop())
            return fut.get(params["product-code[]"][0], {"items": []}) if path == "/instruments/futures" else {}

    real_candles, real_active = ca._candles, ca.streams_active
    ca._candles = fake_candles
    raw_store = {}

    class Keep2:
        def put_object(self, **kw):
            raw_store[kw["Key"]] = kw["Body"]

    fake.client = lambda *_a, **_k: Keep2()
    ds = types.ModuleType("data.tasty_client")
    ds.get_session = lambda: opened.append("SESSION") or FakeSession()
    ds.run_async = lambda c: (_ for _ in ()).throw(AssertionError("run_async used: a second event loop"))
    sys.modules["data.tasty_client"] = ds
    ca._load_service_env = lambda: 0
    os.environ["OT_INSTRUMENT"] = "NVDA"
    ca.streams_active = lambda: True
    rc_g = ca.main(["candles-recent"])
    g_refused = rc_g == 0 and opened == []
    real_sub = subprocess.run

    def units(active):
        return lambda cmd, **k: types.SimpleNamespace(stdout="active\n" if cmd[-1] in active else "inactive\n")
    try:
        subprocess.run = units({"candle-feed"})
        feed_only = real_active() is True
        subprocess.run = units({"optionsbot"})
        bot_only = real_active() is True
        subprocess.run = units(set())
        neither = real_active() is False
        subprocess.run = lambda *a, **k: (_ for _ in ()).throw(OSError("no systemctl"))
        unknown_active = real_active() is True
    finally:
        subprocess.run = real_sub
    check("G1 candles-recent refuses while optionsbot OR candle-feed is active (no session opened); both stopped runs; "
          "unknown counts as active",
          g_refused and feed_only and bot_only and neither and unknown_active,
          f"rc={rc_g} opened={opened} feed={feed_only} bot={bot_only} neither={neither} unknown={unknown_active}")
    ca.streams_active = lambda: False
    opened.clear()
    raw_store.clear()
    rc_l = ca.main(["candles-recent"])
    want = [(("NVDA",), "1d", 21, False), (("NVDA",), "1d", 21, True), (("NVDA",), "1h", 5, False),
            (("NVDA",), "5m", 3, False)]
    today = ca.et_now().date()
    got_l = [(o[0], o[1], (today - o[2]).days, o[3]) for o in opened if o != "SESSION"]
    labels = sorted(re.search(r"interval=([^/]+)/", k).group(1) for k in raw_store)
    check("L1 lookbacks 1d/1d_eth 21d, 1h 5d, 5m 3d (eth only for 1d_eth), filed per label; NVDA only off the SPX box (W1)",
          rc_l == 0 and got_l == want and labels == ["1d", "1d_eth", "1h", "5m"]
          and all(f"/sym=NVDA/pulled={today}.csv.gz" in k for k in raw_store), f"{got_l} {labels}")
    picks = [ca.pick_front(fut[p]["items"]) for p in ("ES", "NQ", "XX")]
    FakeSession.loops.clear()
    ff = asyncio.run(ca._front_futures(FakeSession(), ("ES", "NQ", "XX")))
    check("F1 front futures: active-month wins, else the nearest expiry; a product with none is skipped",
          picks == ["/ESZ26:XCME", "/NQZ26:XCME", None] and ff == ["/ESZ26:XCME", "/NQZ26:XCME"], f"{picks} {ff}")
    os.environ["OT_INSTRUMENT"] = "SPX"
    ca.FUT_PRODUCTS = ("ES",)
    real_ff = ca._front_futures
    ca._front_futures = lambda s, products=("ES",): real_ff(s, products)
    opened.clear()
    FakeSession.loops.clear()
    rc_w = ca.main(["candles-recent"])
    syms_spx = next((o[0] for o in opened if o != "SESSION"), ())
    check("W1 the SPX box adds CONTEXT and the front futures, looked up inside the streams' own event loop",
          rc_w == 0 and syms_spx[:1] == ("SPX",) and set(ca.CONTEXT) <= set(syms_spx) and "/ESZ26:XCME" in syms_spx
          and len(FakeSession.loops) == 1, f"rc={rc_w} {syms_spx} loops={len(FakeSession.loops)}")
    ca._candles = real_candles

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
