#!/usr/bin/env python3
"""
tests/check_hunt_wick_since_entry.py  v5.0
v5.0  2026-10-28  OTV5 r52 (HUNT.15) — THE HUNT'S TARGET-WICK TAKE-OFF JUDGES ONLY A BAR THE TRADE LIVED THROUGH.
      TSLA 2026-10-28, trade c0e55b76: LiquidityHunt short, entry 13:38:00.93 UTC (09:38:00 ET), target 405.8409.
      At 09:38:15 exit_engine._hunt_at_target judged the 09:37 bar (low 405.78, close 406.44: a wick through the
      target, close short of it) and closed the trade "hunt_target_wicked" - but that bar had closed BEFORE the entry.
      The 09:38 bar closed 405.50, beyond the target (the rule's "accepted: hold"), and TSLA ran to 397.18.
      Driven through the REAL ExitEngine._hunt_at_target with the feed store's TSLA and CRM bars; only the clock is
      pinned.

  W1  TSLA at 09:38:15 with the 09:38 row forming (closed_pos -2 = 09:37, ended 09:38:00 <= entry): no exit
  W2  TSLA at 09:38:15 with no 09:38 row yet (closed_pos -1 = 09:37): no exit either
  W3  TSLA at 09:39:15 judging 09:38 (close 405.50 beyond the target): no exit (accepted - as before)
  W4  CRM c4f1b1bd (entry 09:36:00.85, long, target 240.89): at 09:37:03 the 09:36 bar - the one holding the entry,
      high 240.965, close 240.88 - still exits hunt_target_wicked, exactly as it did that day
  W5  an unreadable entry time keeps today's reading (TSLA's 09:37 wick exits, as before)

Born red on 7258a26 (and ce32c3c) at W1 and W2.
Run:  python3 tests/check_hunt_wick_since_entry.py
"""
import datetime as D
import os
import sys
import tempfile
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_s = tempfile.mkdtemp(prefix="check_hunt_wick_since_entry.")
for _k, _v in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived.db"), ("OT_RESTING_DB", "resting.db"),
               ("OT_FEED_DB", "feed.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_RESTING_STOP_STATE", "rs.json"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(_s, _v)
os.environ.setdefault("OT_INSTRUMENT", "TSLA")
import pandas as pd                                             # noqa: E402
from execution import exit_engine as XE                          # noqa: E402

ET = ZoneInfo("America/New_York")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def at(h, m, s=0.0):
    return D.datetime(2026, 10, 28, h, m, int(s), int(round((s % 1) * 1e6)), tzinfo=ET)


def frame(bars):
    idx = pd.DatetimeIndex([at(9, m) for m, *_ in bars])
    return pd.DataFrame({"open": [b[1] for b in bars], "high": [b[2] for b in bars],
                         "low": [b[3] for b in bars], "close": [b[4] for b in bars]}, index=idx)


# feed store, 2026-10-28 (ET minute, O, H, L, C)
TSLA = [(35, 407.085, 407.1962, 405.82, 405.94), (36, 405.945, 406.6699, 405.8017, 406.17),
        (37, 406.21, 406.59, 405.78, 406.44), (38, 406.4, 406.46, 405.4001, 405.5),
        (39, 405.45, 405.7352, 404.75, 404.8099)]
CRM = [(35, 240.05, 240.62, 239.5301, 240.53), (36, 240.42, 240.965, 240.3, 240.88),
       (37, 240.985, 241.6, 240.64, 241.3324)]
TSLA_REC = {"trade_id": "c0e55b76", "strategy": "LiquidityHunt", "direction": "short",
            "underlying_target": 405.8409, "entry_time": "2026-10-28T13:38:00.933962+00:00"}
CRM_REC = {"trade_id": "c4f1b1bd", "strategy": "LiquidityHunt", "direction": "long",
           "underlying_target": 240.89, "entry_time": "2026-10-28T13:36:00.847817+00:00"}

xe = XE.ExitEngine(paper_trading=True)
_orig = XE.now_et


def run(rec, bars, now):
    XE.now_et = lambda: now
    try:
        return xe._hunt_at_target(dict(rec), frame(bars))
    finally:
        XE.now_et = _orig


print("check_hunt_wick_since_entry (HUNT.15)")
r1 = run(TSLA_REC, TSLA[:4], at(9, 38, 15.65))                  # 09:38 forming -> -2 = 09:37
check("W1 TSLA 09:38:15, 09:38 forming: the pre-entry 09:37 wick does not exit", r1 == "", r1[:70])
r2 = run(TSLA_REC, TSLA[:3], at(9, 38, 15.65))                  # no 09:38 row -> -1 = 09:37
check("W2 TSLA 09:38:15, no 09:38 row: still no exit", r2 == "", r2[:70])
r3 = run(TSLA_REC, TSLA[:5], at(9, 39, 15.0))                   # 09:39 forming -> 09:38 (405.50, beyond)
check("W3 TSLA 09:39:15 on 09:38 (closed beyond the target): no exit, accepted", r3 == "", r3[:70])
r4 = run(CRM_REC, CRM, at(9, 37, 3.0))                          # 09:37 forming -> 09:36 holds the entry
check("W4 CRM 09:37:03 on 09:36 (the entry's own bar wicked 240.89): exits as before",
      r4.startswith("hunt_target_wicked: target 240.89"), r4[:70])
r5 = run(dict(TSLA_REC, entry_time="not a time"), TSLA[:4], at(9, 38, 15.65))
check("W5 an unreadable entry time keeps today's reading (the 09:37 wick exits)",
      r5.startswith("hunt_target_wicked: target 405.84"), r5[:70])

print("RESULT:", "FAIL " + ",".join(FAILED) if FAILED else "PASS")
sys.exit(1 if FAILED else 0)
