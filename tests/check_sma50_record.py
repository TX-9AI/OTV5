#!/usr/bin/env python3
"""
tests/check_sma50_record.py  v1.1

Every trade's entry snapshot records the 5-minute 50 SMA (regular hours and
extended), the entry's side of it, and the session's opening-candle cross; the
backfill tool adds the same key to past rows and nothing else.

v1.1  2026-10-23  OTV4TEST r315 (SMA.2) — S6 expects schema v 3: r315 adds "sma50_mtf" beside an
      UNCHANGED "sma50_5m" (check_sma50_mtf M1). The assertion moved with the schema; nothing else did.
v1.0  2026-09-30  OTV4TEST r183 (SMA.1). The operator, 2026-09-30: "I want it
      in the trades log", then "yes" to recording it, backfilling and testing.

WHAT IT DRIVES (WA 21): the REAL analysis.entry_snapshot.sma50_context and
build(), and the REAL tools/backfill_sma50.run, over a scratch feed store of
synthetic 1m bars whose SMA is known by construction and a scratch trades store
built with the live logger's own schema (database.trade_logger.TradeLogger).

  S1  60 flat 5m bars at 100 then a long entered at 101: SMA 100, dist +1, "with";
      a short at 101: dist -1, "against"
  S2  only 40 closed 5m bars: sma None, and it says how many there were
  S3  the forming bar is NOT counted (closed bars only)
  S4  the 09:30 candle opened under the prior-50 SMA and closed over it -> "above";
      one that stayed over it -> "none"; an entry before 09:35 -> null
  S5  the extended-hours series is read from <SYMBOL>_EXT, separately
  S6  build() carries "sma50_5m" and v 3 (r315); a missing feed store puts "err" INSIDE
      the key and never raises or sets the payload's own err
  S7  backfill dry run writes nothing
  S8  backfill --apply adds the key to rows lacking it, keeps every other key,
      marks the row, and a second run changes nothing

BORN RED on 59ba004 (r178): the function, the key and the tool are absent there.

Run:  python3 tests/check_sma50_record.py
"""
from __future__ import annotations

import datetime as dt
import glob as _glob
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _base in (ROOT, os.path.expanduser("~/options-trader")):
    _found = _glob.glob(os.path.join(_base, "venv", "lib", "python*", "site-packages"))
    for _sp in _found:
        if _sp not in sys.path:
            sys.path.insert(1, _sp)
    if _found:
        break
sys.path.insert(0, ROOT)
_SCR = tempfile.mkdtemp(prefix="check_sma50_record_",
                        dir="/var/tmp" if os.path.isdir("/var/tmp") else None)
FEED = os.path.join(_SCR, "feed_store.db")
os.environ["OT_FEED_DB"] = FEED
os.environ["OT_TRADES_DB"] = os.path.join(_SCR, "trades.db")
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
ET = ZoneInfo("America/New_York")

FAIL = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(label.split()[0])


def guard(label, fn, detail=lambda: ""):
    try:
        ok = bool(fn())
    except Exception as exc:                                    # noqa: BLE001
        print(f"  FAIL  {label}  [raised {type(exc).__name__}: {exc}]")
        FAIL.append(label.split()[0])
        return
    check(label, ok, detail())


def feed(rows):
    if os.path.exists(FEED):
        os.unlink(FEED)
    c = sqlite3.connect(FEED)
    c.execute("CREATE TABLE candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, ts_epoch_ms "
              "INTEGER NOT NULL, open REAL, high REAL, low REAL, close REAL, volume REAL, "
              "PRIMARY KEY (symbol, interval, ts_epoch_ms))")
    c.executemany("INSERT INTO candles VALUES (?, '1m', ?, ?, ?, ?, ?, 1000)", rows)
    c.commit()
    c.close()


def bars_1m(symbol, start, n5, px_fn):
    """n5 five-minute buckets of 1m bars from `start` (epoch), close = px_fn(i5, j1)."""
    out = []
    for i in range(n5):
        for j in range(5):
            t = start + i * 300 + j * 60
            o, c = px_fn(i, j)
            out.append((symbol, int(t * 1000), o, max(o, c), min(o, c), c))
    return out


def ep(y, mo, d, h, mi):
    return dt.datetime(y, mo, d, h, mi, tzinfo=ET).timestamp()


from analysis import entry_snapshot as es                        # noqa: E402

_R = {}
flat = lambda i, j: (100.0, 100.0)                                # noqa: E731
T0 = ep(2026, 9, 29, 12, 0)                                       # a mid-day run, no 09:30 bar


def _s1():
    feed(bars_1m("QQQ", T0, 60, flat))
    t = T0 + 60 * 300
    lo = es.sma50_context(t, 101.0, "long")["rth"]
    sh = es.sma50_context(t, 101.0, "short")["rth"]
    _R["s1"] = (lo, sh)
    return (abs(lo["sma"] - 100) < 1e-9 and abs(lo["dist"] - 1) < 1e-9 and lo["side"] == "with"
            and abs(sh["dist"] + 1) < 1e-9 and sh["side"] == "against")


guard("S1 SMA 100: a long at 101 is +1 'with'; a short at 101 is -1 'against'", _s1,
      lambda: str(_R.get("s1")))


def _s2():
    feed(bars_1m("QQQ", T0, 40, flat))
    r = es.sma50_context(T0 + 40 * 300, 101.0, "long")["rth"]
    _R["s2"] = r
    return r["sma"] is None and "40 closed 5m bars" in r.get("why", "")


guard("S2 only 40 closed 5m bars: sma None, and it says how many", _s2, lambda: str(_R.get("s2")))


def _s3():
    # 50 closed bars at 100, then a FORMING bar at 200: it must not move the SMA
    feed(bars_1m("QQQ", T0, 50, flat) + [("QQQ", int((T0 + 50 * 300) * 1000), 200, 200, 200, 200)])
    r = es.sma50_context(T0 + 50 * 300 + 90, 101.0, "long")["rth"]
    _R["s3"] = r
    return abs(r["sma"] - 100) < 1e-9


guard("S3 the forming bar is not counted (closed bars only)", _s3, lambda: str(_R.get("s3")))


def _s4():
    pre = ep(2026, 9, 29, 12, 0)                                   # 60 prior bars at 100
    o930 = ep(2026, 9, 30, 9, 30)
    up = bars_1m("QQQ", pre, 60, flat) + bars_1m(
        "QQQ", o930, 3, lambda i, j: ((99.0, 99.5) if (i, j) == (0, 0) else (100.5, 101.0)))
    feed(up)
    a = es.sma50_context(ep(2026, 9, 30, 9, 45), 101.0, "long")["rth"]
    stay = bars_1m("QQQ", pre, 60, flat) + bars_1m("QQQ", o930, 3, lambda i, j: (101.0, 101.0))
    feed(stay)
    b = es.sma50_context(ep(2026, 9, 30, 9, 45), 101.0, "long")["rth"]
    c = es.sma50_context(ep(2026, 9, 30, 9, 33), 101.0, "long")["rth"]
    _R["s4"] = (a.get("open_cross"), b.get("open_cross"), c.get("open_cross"))
    return _R["s4"] == ("above", "none", None)


guard("S4 open cross: under->over = 'above'; stayed over = 'none'; before 09:35 = null", _s4,
      lambda: str(_R.get("s4")))


def _s5():
    feed(bars_1m("QQQ", T0, 60, flat) + bars_1m("QQQ_EXT", T0, 60, lambda i, j: (90.0, 90.0)))
    r = es.sma50_context(T0 + 60 * 300, 101.0, "long")
    _R["s5"] = (r["rth"]["sma"], r["ext"]["sma"])
    return abs(r["rth"]["sma"] - 100) < 1e-9 and abs(r["ext"]["sma"] - 90) < 1e-9


guard("S5 the extended-hours series is read from QQQ_EXT, separately", _s5, lambda: str(_R.get("s5")))


def _s6():
    feed(bars_1m("QQQ", T0, 60, flat))
    p1 = es.build({"price": 101.0}, "long")
    os.unlink(FEED)
    p2 = es.build({"price": 101.0}, "long")
    _R["s6"] = (p1.get("v"), "sma50_5m" in p1, p2.get("sma50_5m"), p2.get("err"))
    return (p1.get("v") == 3 and "sma50_5m" in p1 and "err" in (p2.get("sma50_5m") or {})
            and "err" not in p2)


guard("S6 build() carries sma50_5m and v 3; a missing store puts err INSIDE the key only", _s6,
      lambda: str(_R.get("s6")))

# ── the backfill ──────────────────────────────────────────────────────────────
from database.trade_logger import TradeLogger                    # noqa: E402
import tools.backfill_sma50 as BF                                # noqa: E402

TDB = os.environ["OT_TRADES_DB"]
TradeLogger(TDB)                                                 # the live schema, scratch file
_c = sqlite3.connect(TDB)
_et = dt.datetime.fromtimestamp(T0 + 60 * 300, dt.timezone.utc).isoformat()
_c.execute("INSERT INTO trades (trade_id, symbol, strategy, direction, status, entry_time, "
           "underlying_entry, entry_snapshot) VALUES ('A','QQQ','VOLT','long','closed',?,101.0,?)",
           (_et, json.dumps({"v": 1, "px": 101.0, "fvg": [1, 2]})))
_c.execute("INSERT INTO trades (trade_id, symbol, strategy, direction, status, entry_time, "
           "underlying_entry, entry_snapshot) VALUES ('B','QQQ','VOLT','short','closed',?,101.0,?)",
           (_et, json.dumps({"v": 2, "sma50_5m": {"keep": "me"}})))
_c.commit()
_c.close()
feed(bars_1m("QQQ", T0, 60, flat) + bars_1m("QQQ_EXT", T0, 60, flat))


def snaps():
    c = sqlite3.connect(TDB)
    try:
        return dict(c.execute("SELECT trade_id, entry_snapshot FROM trades").fetchall())
    finally:
        c.close()


def _s7():
    before = snaps()
    n = BF.run(False, TDB, FEED, "QQQ", "stamp")
    _R["s7"] = n
    return snaps() == before and n["would_write"] == 1 and n["already"] == 1


guard("S7 backfill dry run writes nothing (1 would be written, 1 already carries the key)", _s7,
      lambda: str(_R.get("s7")))


def _s8():
    n1 = BF.run(True, TDB, FEED, "QQQ", "stamp")
    s = snaps()
    a, b = json.loads(s["A"]), json.loads(s["B"])
    n2 = BF.run(True, TDB, FEED, "QQQ", "stamp2")
    _R["s8"] = (n1, n2, a.get("sma50_5m", {}).get("rth"), b)
    return (n1["written"] == 1 and a.get("fvg") == [1, 2] and a.get("v") == 1
            and a["sma50_5m"]["rth"]["side"] == "with" and a.get("sma50_backfilled") == "stamp"
            and b == {"v": 2, "sma50_5m": {"keep": "me"}} and n2["written"] == 0)


guard("S8 --apply adds the key, keeps the rest, marks the row; a second run changes nothing", _s8,
      lambda: str(_R.get("s8")))

shutil.rmtree(_SCR, ignore_errors=True)
print()
if FAIL:
    print(f"RED — {len(FAIL)} failed: {sorted(set(FAIL))}")
    sys.exit(1)
print("GREEN — the 5m 50 SMA and the opening cross are recorded; the backfill adds only that")
sys.exit(0)
