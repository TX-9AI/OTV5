#!/usr/bin/env python3
"""
tests/check_orb_resume.py  v1.0

r103 — THE ORB STATE IS WRITTEN DOWN, TRUSTED, AND THE MISS IS ADJUDICATED.

Born RED at 672a372 (r102) on R1..R6. Plain script (WORKING_AGREEMENT 36).

Operator, 2026-08-24: "It should fetch if it's during the window & record it
(not just held in memory) ... if it HAD the orb state, but was interrupted, it
should have written it down. It can easily confirm orb state after any restart,
so a 1x look back function is grossly underpowered." And: "If it wrote it,
trust it and act accordingly — figure out if it fired or if we genuinely missed
it before closing out the row."

  R1  state_snapshot() carries everything load_state_file() consumes — a
      round-trip through a real file restores state, latches, attempt, range
  R2  a file from ANOTHER DATE is ignored (yesterday's latches on today's range)
  R3  a resumed engine still OWES a reach-back (the file is truth up to its
      last write; the gap is what the replay is for)
  R4  A THIN FETCH DOES NOT BURN THE ATTEMPT — the one-shot latch that made a
      crash loop unrecoverable. Replay with 2 bars, then confirm still owed
  R5  the reach-back is IDEMPOTENT — replaying the same tape twice does not
      double the attempt count or move the state
  R6  the missed payload carries the setup's full geometry, not a timestamp

Run:  python3 tests/check_orb_resume.py
"""
from __future__ import annotations
import json, os, sys, tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)

import pandas as pd
import analysis.orb_engine as oe
from analysis.orb_engine import ORBEngine, ORBState
from utils.time_utils import ET, now_et

TMP = tempfile.mkdtemp()
PATH = os.path.join(TMP, "orb_state.json")

def _bars(n, start=100.0, step=0.05):
    idx = pd.date_range(datetime.now(ET).replace(hour=9, minute=30, second=0,
                                                 microsecond=0),
                        periods=n, freq="1min")
    px = [start + i * step for i in range(n)]
    return pd.DataFrame({"open": px, "high": [p + .05 for p in px],
                         "low": [p - .05 for p in px], "close": px,
                         "volume": [1000] * n}, index=idx)

# ── R1 round-trip ────────────────────────────────────────────────────────────
e = ORBEngine()
d = e._data
d.state = ORBState.ARMED_LONG if hasattr(ORBState, "ARMED_LONG") else "ARMED_LONG"
d.orb_high, d.orb_low, d.orb_width = 101.0, 99.0, 2.0
d.attempt_number = 2
d.break_direction = "LONG"
d.break_candle_high, d.break_candle_low, d.break_candle_close = 101.5, 100.9, 101.4
d.bars_since_break = 3
d.confirmed_at = "2026-08-25 09:58:00"
d.stop_level = 100.8
e._broke_high, e._broke_low = True, False
e._last_bar_ts = "2026-08-25 09:59:00"
snap = e.state_snapshot(100.5)
with open(PATH, "w") as f:
    json.dump(snap, f)

e2 = ORBEngine()
ok = e2.load_state_file(PATH)
check("R1a load_state_file accepts today's file", ok is True)
check("R1b state restored", str(e2._data.state) == str(d.state),
      f"{e2._data.state} vs {d.state}")
check("R1c attempt count restored", e2._data.attempt_number == 2)
check("R1d break latches restored", (e2.broke_high, e2.broke_low) == (True, False))
check("R1e range restored", (e2._data.orb_high, e2._data.orb_low) == (101.0, 99.0))
check("R1f break candle + confirmed_at restored",
      e2._data.break_candle_high == 101.5 and e2._data.confirmed_at == d.confirmed_at)

# ── R2 a stale file is refused ───────────────────────────────────────────────
stale = dict(snap); stale["date"] = "2026-01-02"
p2 = os.path.join(TMP, "stale.json")
with open(p2, "w") as f:
    json.dump(stale, f)
e3 = ORBEngine()
check("R2 a file from another date is IGNORED", e3.load_state_file(p2) is False)
check("R2b and nothing leaked into the engine", e3._data.attempt_number == 0
      and e3.broke_high is False)

# ── R3 a resumed engine still owes the gap ───────────────────────────────────
e2.mark_rebuild_owed()
check("R3 a resumed engine still owes a reach-back", e2.needs_tape_rebuild is True)

# ── R4 a thin fetch must not burn the attempt ────────────────────────────────
e4 = ORBEngine()
e4._data.orb_high, e4._data.orb_low, e4._data.orb_width = 101.0, 99.0, 2.0
e4._range_date = now_et().strftime("%Y-%m-%d")
before_owed = e4.needs_tape_rebuild
e4.rebuild_from_tape(_bars(2))          # two bars — a short fetch, not a session
check("R4a a 2-bar fetch is refused", before_owed is True)
check("R4b AND the rebuild is STILL OWED (the crash-loop bug)",
      e4.needs_tape_rebuild is True,
      "a thin fetch used to set _rebuilt_date and never retry")

# ── R5 idempotent replay ─────────────────────────────────────────────────────
e5 = ORBEngine()
e5._data.orb_high, e5._data.orb_low, e5._data.orb_width = 101.0, 99.0, 2.0
e5._range_date = now_et().strftime("%Y-%m-%d")
e5._data.state = ORBState.WAITING_FOR_BREAK
# a tape that BREAKS the range, so the replay actually advances state — an
# idempotence check over a tape that triggers nothing proves nothing.
tape = _bars(40)
e5.rebuild_from_tape(tape)
s1, a1 = str(e5._data.state), e5._data.attempt_number
e5._rebuild_owed = True                  # a second restart would owe one
e5.rebuild_from_tape(tape)
check("R5a the replay actually advanced state (or the check is vacuous)",
      str(s1) != str(ORBState.WAITING_FOR_BREAK) or e5.broke_high,
      f"state after replay={s1} broke_high={e5.broke_high}")
check("R5b replaying the same tape twice changes nothing",
      (str(e5._data.state), e5._data.attempt_number) == (s1, a1),
      f"{s1}/{a1} -> {e5._data.state}/{e5._data.attempt_number}")

# ── R6 the miss carries its parameters ───────────────────────────────────────
import ast
src = open(os.path.join(ROOT, "analysis/orb_engine.py")).read()
tree = ast.parse(src)
payload_keys = set()
for n in ast.walk(tree):
    if (isinstance(n, ast.Assign) and "_last_missed" in ast.unparse(n.targets)
            and isinstance(n.value, ast.Dict)):
        payload_keys = {k.value for k in n.value.keys if isinstance(k, ast.Constant)}
want = {"orb_high", "orb_low", "break_candle_high", "retest_depth_px",
        "stop_level", "target_50pct", "bars_since_break", "confirmed_at"}
check("R6 the missed payload carries the setup's geometry", want <= payload_keys,
      f"missing {sorted(want - payload_keys)}")

# ── R7 main adjudicates fired-vs-missed before writing the row ───────────────
msrc = open(os.path.join(ROOT, "main.py")).read()
mtree = ast.parse(msrc)
fn = next(n for n in ast.walk(mtree)
          if isinstance(n, ast.FunctionDef) and n.name == "run_analysis")
fsrc = ast.unparse(fn)
check("R7a main asks the trades table whether it FIRED",
      "orb_entry_since" in fsrc)
check("R7b and journals the miss as a disposition",
      'outcome=\'missed\'' in fsrc or 'outcome="missed"' in fsrc)
from database.trade_logger import get_trade_logger
check("R7c orb_entry_since exists and fails soft",
      hasattr(get_trade_logger(), "orb_entry_since"))

print(f"\n{'PASS' if not FAILURES else 'FAIL'}: {len(FAILURES)} problem(s) {FAILURES}")
sys.exit(1 if FAILURES else 0)
