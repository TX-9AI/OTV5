#!/usr/bin/env python3
"""
tests/check_push_allowlist.py  v5.0
v5.0  2026-11-03  OTV5 r72 (PARK.5) — new. A BOX UPLOADS ITS OWN SYMBOL AND NOTHING ELSE. The operator, 2026-11-03: "Make
      sure the boxes not trading qqq are hard blocked from uploading any other symbol." warehouse/s3_push v5.8's
      allow-list (sym_family, allowed_symbol), asked by every stage, exercised END TO END through s3_push.main() with a
      fake boto3 and a box tree that holds this box's own data AND another symbol's in every stream.
  A1  sym_family: QQQ_EXT -> QQQ, .AMZN251103C250 -> AMZN, .SPXW251103P5800 -> SPX, VIX -> VIX, "" -> ""; allowed_symbol:
      an unknown own symbol allows nothing, an unlabelled row is the box's own, VIX only from the SPX box
  A2  AN EQUITY BOX (AMZN) WITH QQQ IN EVERY STREAM: main --verify uploads no object under sym=QQQ or sym=VIX, and no
      uploaded body carries a QQQ (or VIX) row - trades, shadow trades, circuit breaker, ohlc, candles, the feed series
      (symbol and streamer_symbol), the derived series and lifecycle tables, liquidity ledger, chain snapshots, shadow,
      signal journal
  A3  ...and AMZN's own data still ships in every one of those streams (the allow-list is not a blackout)
  A4  ...one FOREIGN DROPPED line names the dropped counts, and it prints BEFORE the DRAIN line
  A5  THE QQQ BOX uploads QQQ only: an AMZN row in its store never leaves it
  A6  THE SPX BOX still owns the VIX family (VIX candles ship) and its .SPXW option rows ship as SPX
  A7  AN UNKNOWN OWN SYMBOL UPLOADS NOTHING: zero PUTs, one S3_PUSH SKIPPED line, the DRAIN line reads failed=1 SHORT
  A8  a series batch made ONLY of foreign rows ships nothing and still advances the table's high-water mark (no stall)
  A9  a mixed series batch ships the own rows only, and the mark covers the whole batch
Mutation-tested: allowed_symbol always True (A2 red), the trades stage without me= (A2 red), the unknown-symbol skip
removed (A7 red).
"""
import gzip
import io
import json
import os
import re
import sqlite3
import sys
import tempfile
import types
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
ET = ZoneInfo("America/New_York")

# A private HOME before s3_push is imported: every store, tree and ledger path derives from it at import time.
_HOME = tempfile.mkdtemp(prefix="push_allowlist_")
os.environ["HOME"] = _HOME
os.environ["OT_S3_PUSH"] = "1"
for _k in ("OT_WAREHOUSE_STATE", "OT_CHAIN_ROOT", "OT_PUSH_PAUSE_FLAG", "OT_TRADES_DB", "OT_SHADOW_TRADES_DB",
           "OT_S3_SERIES_BATCH", "OT_S3_SERIES_BUDGET_S", "OT_S3_SERIES_DRAIN_BUDGET_S", "OT_INSTRUMENT"):
    os.environ.pop(_k, None)

FAILED = []
N = [0]


def check(name, ok, detail=""):
    N[0] += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  -- {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class FakeS3:
    def __init__(self):
        self.store = {}

    def put_object(self, Bucket=None, Key=None, Body=None):
        self.store[Key] = Body

    def get_object(self, Bucket=None, Key=None):
        body = self.store[Key]
        return {"Body": types.SimpleNamespace(read=lambda: body)}

    def get_paginator(self, _name):
        store = self.store

        class _P:
            def paginate(self, Bucket=None, Prefix=""):
                yield {"Contents": [{"Key": k, "Size": len(v)} for k, v in store.items() if k.startswith(Prefix)]}
        return _P()


def _y():
    return (datetime.now(ET) - timedelta(days=1)).date()


def build_box(SP, own, foreign):
    """A box tree holding `own`'s data and `foreign`'s in every stream SP ships (and VIX candles)."""
    import shutil
    for p in (os.path.join(_HOME, "options-trader"), os.path.join(_HOME, "eod"), SP.STATE_DIR):
        shutil.rmtree(p, ignore_errors=True)
    day = _y().isoformat()
    t10 = datetime.combine(_y(), datetime.min.time().replace(hour=10), tzinfo=ET)
    ts = t10.timestamp()
    os.makedirs(os.path.dirname(SP.TRADES_DB), exist_ok=True)
    c = sqlite3.connect(SP.TRADES_DB)
    c.execute("CREATE TABLE trades (trade_id TEXT, symbol TEXT, entry_time TEXT, pnl_usd REAL)")
    c.execute("CREATE TABLE circuit_breaker_events (id INTEGER, symbol TEXT, event_time TEXT, why TEXT)")
    for i, s in enumerate((own, foreign)):
        c.execute("INSERT INTO trades VALUES (?,?,?,?)", (f"t{i}", s, t10.isoformat(), 1.0))
        c.execute("INSERT INTO circuit_breaker_events VALUES (?,?,?,?)", (i + 1, s, t10.isoformat(), "x"))
    c.commit()
    c.close()
    c = sqlite3.connect(SP.SHADOW_TRADES_DB)
    c.execute("CREATE TABLE trades (trade_id TEXT, symbol TEXT, entry_time TEXT)")
    for i, s in enumerate((own, foreign)):
        c.execute("INSERT INTO trades VALUES (?,?,?)", (f"s{i}", s, t10.isoformat()))
    c.commit()
    c.close()
    os.makedirs(os.path.dirname(SP.FEED_DB), exist_ok=True)
    c = sqlite3.connect(SP.FEED_DB)
    c.execute("CREATE TABLE candles (symbol TEXT, interval TEXT, ts_epoch_ms INTEGER, open REAL, high REAL, low REAL, "
              "close REAL, volume REAL)")
    for s in (own, foreign, "VIX"):
        for k in range(3):
            c.execute("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", (s, "1m", int(ts * 1000) + k * 60000, 1, 1, 1, 1, 9))
    c.execute("CREATE TABLE quote_series (streamer_symbol TEXT, ts_epoch REAL, bid REAL, ask REAL)")
    c.execute("CREATE TABLE prints (symbol TEXT, ts_epoch REAL, price REAL)")
    oroot = "SPXW" if own == "SPX" else own                     # SPX's options stream as .SPXW
    for k, s in enumerate((own, f".{oroot}251103C250", foreign, f".{foreign}251103C500")):
        c.execute("INSERT INTO quote_series VALUES (?,?,?,?)", (s, ts + k, 1, 2))
    for k, s in enumerate((own, foreign)):
        c.execute("INSERT INTO prints VALUES (?,?,?)", (s, ts + k, 1))
    c.commit()
    c.close()
    c = sqlite3.connect(SP.DERIVED_DB)
    c.execute("CREATE TABLE indicator_series (symbol TEXT, interval TEXT, ts_epoch REAL, v REAL)")
    c.execute("CREATE TABLE plan_check (symbol TEXT, ts_epoch REAL, name TEXT)")
    for k, s in enumerate((own, foreign)):
        c.execute("INSERT INTO indicator_series VALUES (?,?,?,?)", (s, "1m", ts + k, 1))
        c.execute("INSERT INTO plan_check VALUES (?,?,?)", (s, ts + k, "x"))
    c.commit()
    c.close()
    for root, suf, body in ((SP.OHLC_ROOT, ".csv", "ts,open\n1,2\n"), (SP.LIQ_ROOT, ".json", "{}\n"),
                            (SP.SHADOW_ROOT, ".jsonl", '{"ts_epoch": 1}\n'),
                            (SP.JOURNAL_ROOT, ".jsonl", '{"ts_epoch": 1, "event": "e"}\n')):
        os.makedirs(os.path.join(root, day), exist_ok=True)
        for s in (own, foreign):
            with open(os.path.join(root, day, s + suf), "w") as fh:
                fh.write(body.replace("ts,open", f"ts,{s}") if suf == ".csv" else body)
    os.makedirs(os.path.join(SP.SRC_ROOT, day), exist_ok=True)
    for s in (own, foreign):
        with gzip.open(os.path.join(SP.SRC_ROOT, day, s + ".jsonl.gz"), "wb") as fh:
            fh.write(json.dumps({"ts_epoch": ts, "underlying": s}).encode() + b"\n")
    return day


def run_main(SP, fake, own_override=None):
    fake.store.clear()
    SP._FOREIGN.clear()
    saved = SP.own_symbol
    if own_override is not None:
        SP.own_symbol = lambda: own_override
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            SP.main(["--verify"])
    finally:
        SP.own_symbol = saved
    return buf.getvalue()


def rows_of(body):
    d = json.loads(body)
    r = d.get("record")
    return r if isinstance(r, list) else [r]


def foreign_in(store, foreign_fam, SP):
    """Keys under a foreign partition, and uploaded rows whose symbol is the foreign family."""
    bad_keys = [k for k in store if f"/sym={foreign_fam}/" in k]
    bad_rows = []
    for k, v in store.items():
        if "/fleet/" in k or k.startswith("fleet/"):
            continue
        for r in rows_of(v):
            if isinstance(r, dict):
                s = r.get("symbol") or r.get("streamer_symbol") or r.get("underlying")
                if s and SP.sym_family(s) == foreign_fam:
                    bad_rows.append(k)
            elif isinstance(r, str) and f"ts,{foreign_fam}" in r:
                bad_rows.append(k)
    return bad_keys, bad_rows


def main():
    from warehouse import s3_push as SP
    fake = FakeS3()
    sys.modules["boto3"] = types.SimpleNamespace(client=lambda *a, **k: fake)

    # A1
    fam = {s: SP.sym_family(s) for s in ("QQQ_EXT", ".AMZN251103C250", ".SPXW251103P5800", "VIX", "", None, "^VIX")}
    al = (SP.allowed_symbol("QQQ", "") is False and SP.allowed_symbol("", "AMZN") is True
          and SP.allowed_symbol("VIX", "SPX") is True and SP.allowed_symbol("VIX", "AMZN") is False
          and SP.allowed_symbol("QQQ_EXT", "QQQ") is True and SP.allowed_symbol("QQQ", "AMZN") is False
          and SP.allowed_symbol(".SPXW251103P5800", "SPX") is True)
    check("A1 sym_family / allowed_symbol rules",
          fam == {"QQQ_EXT": "QQQ", ".AMZN251103C250": "AMZN", ".SPXW251103P5800": "SPX", "VIX": "VIX", "": "",
                  None: "", "^VIX": "VIX"} and al, f"{fam} allowed_ok={al}")

    # A2-A4: the AMZN box, QQQ everywhere
    build_box(SP, "AMZN", "QQQ")
    os.environ["OT_INSTRUMENT"] = "AMZN"
    out = run_main(SP, fake)
    bk, br = foreign_in(fake.store, "QQQ", SP)
    vk = [k for k in fake.store if "/sym=VIX/" in k]
    check("A2 equity box: no QQQ (or VIX) object or row uploaded from any stream", not bk and not br and not vk,
          f"keys={bk[:4]} rows={br[:4]} vix={vk[:3]}")
    want = ("/trades/", "/shadow_trades/", "/circuit_breaker/", "/ohlc/", "/candles/", "/quote_series/", "/prints/",
            "/indicator_series/", "/derived_plan_check/", "/liquidity_ledger/", "/chain_snapshots/", "/shadow/",
            "/signal_journal/")
    missing = [w for w in want if not any(w in k and "/sym=AMZN/" in k for k in fake.store)]
    check("A3 ...and AMZN's own rows still ship in every stream", not missing, f"missing {missing}")
    lines = out.splitlines()
    fi = next((i for i, l in enumerate(lines) if l.startswith("FOREIGN DROPPED ")), -1)
    di = next((i for i, l in enumerate(lines) if l.startswith("DRAIN ")), -1)
    check("A4 ...one FOREIGN DROPPED line with counts, before the DRAIN line",
          fi >= 0 and di > fi and sum(l.startswith("FOREIGN DROPPED ") for l in lines) == 1
          and "candles=" in lines[fi] and "trades=" in lines[fi] and "quote_series=2" in lines[fi],
          f"foreign@{fi} drain@{di} {lines[fi] if fi >= 0 else out[-300:]!r}")

    # A5: the QQQ box, AMZN in its store
    build_box(SP, "QQQ", "AMZN")
    os.environ["OT_INSTRUMENT"] = "QQQ"
    run_main(SP, fake)
    bk, br = foreign_in(fake.store, "AMZN", SP)
    own = [k for k in fake.store if "/sym=QQQ/" in k and "/candles/" in k]
    check("A5 the QQQ box uploads QQQ only (no AMZN object or row)", not bk and not br and own, f"{bk[:3]} {br[:3]}")

    # A6: the SPX box keeps VIX
    build_box(SP, "SPX", "QQQ")
    os.environ["OT_INSTRUMENT"] = "SPX"
    run_main(SP, fake)
    vix = [k for k in fake.store if "/candles/" in k and "/sym=VIX/" in k]
    spxw = [k for k in fake.store if "/quote_series/" in k and "/sym=SPX/" in k
            and any(str(r.get("streamer_symbol", "")).startswith(".SPXW") for r in rows_of(fake.store[k]))]
    bk, br = foreign_in(fake.store, "QQQ", SP)
    check("A6 the SPX box still ships the VIX family and its .SPXW rows, and no QQQ", vix and spxw and not bk and not br,
          f"vix={vix[:2]} spxw={spxw[:2]} bad={bk[:2]}{br[:2]}")

    # A7: unknown own symbol
    build_box(SP, "AMZN", "QQQ")
    os.environ.pop("OT_INSTRUMENT", None)
    out = run_main(SP, fake, own_override="")
    m = re.search(r"^DRAIN host=\S+ sym=\S+ drained=\S+ pushed=(\d+) failed=(\d+) .* (\S+)$", out, re.M)
    check("A7 own symbol unknown: zero PUTs, one S3_PUSH SKIPPED line, DRAIN failed=1 SHORT",
          not fake.store and out.count("S3_PUSH SKIPPED") == 1 and m and m.group(1) == "0"
          and m.group(2) == "1" and m.group(3) == "SHORT", f"puts={list(fake.store)[:3]} out={out[-300:]!r}")

    # A8 / A9: the series high-water mark
    db = os.path.join(_HOME, "series_only.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE quote_series (streamer_symbol TEXT, ts_epoch REAL, bid REAL)")
    c.execute("CREATE TABLE prints (symbol TEXT, ts_epoch REAL, price REAL)")
    t0 = datetime.combine(_y(), datetime.min.time().replace(hour=11), tzinfo=ET).timestamp()
    c.executemany("INSERT INTO quote_series VALUES (?,?,?)", [(".QQQ251103C500", t0 + i, 1) for i in range(5)])
    c.executemany("INSERT INTO prints VALUES (?,?,?)",
                  [("AMZN" if i % 2 else "QQQ", t0 + i, 1) for i in range(6)])
    c.commit()
    c.close()
    fake.store.clear()
    SP._FOREIGN.clear()
    led = {}
    r = SP.push_series(fake, "B", db, led, "AMZN", None, tables=("quote_series",))
    check("A8 a foreign-only series batch ships nothing and still advances the mark",
          r == (0, 0) and not fake.store and abs(float(led.get("series|quote_series", 0)) - (t0 + 4)) < 1e-6,
          f"r={r} led={led}")
    led = {}
    r = SP.push_series(fake, "B", db, led, "AMZN", None, tables=("prints",))
    shipped = [x for k, v in fake.store.items() for x in rows_of(v)]
    check("A9 a mixed series batch ships the own rows only; the mark covers the whole batch",
          r[0] >= 1 and shipped and all(x["symbol"] == "AMZN" for x in shipped) and len(shipped) == 3
          and abs(float(led.get("series|prints", 0)) - (t0 + 5)) < 1e-6, f"r={r} shipped={shipped} led={led}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print(f"\nGREEN — {N[0]} of {N[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
