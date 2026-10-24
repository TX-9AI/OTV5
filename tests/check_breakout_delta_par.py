#!/usr/bin/env python3
"""
tests/check_breakout_delta_par.py  v1.0
v1.0  2026-09-21  OTV4TEST r82 — born RED at 8a41b3d.

🔴 THE OPERATOR'S RULING, 2026-09-21: *"the breakout needs the delta stop not
the 100% stop."*

🔑 BREAKOUT INHERITED A GUILLOTINE NOBODY WROTE FOR IT. `management.py`
documents its target as *"a debit exit for the RUNAWAY only"* and implements it
as `strategy not in BUTTERFLIES` — every debit strategy in the tree. MEASURED
2026-09-21: eight `target_hit` exits, every one at delta **0.619-0.650**,
capping winners while real convexity remained. That cap is also WHY no Breakout
has ever reached par delta: 1 of 45 book-wide, and that one was VOLT.

  B1  at PAR delta the Breakout exits on delta_par
  B2  CONTROL: below par it is HELD even with premium PAST the old target
  B3  CONTROL: a NON-Breakout debit still gets target_hit — scoped, not deleted
  B4  no delta from the feed -> HOLD, not guess (r82 killed the extrinsic proxy)

Drives the REAL ManagementPlan.decide() (§21).
Run:  python3 tests/check_breakout_delta_par.py
"""
from __future__ import annotations
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = tempfile.mkdtemp(prefix="check_breakout_delta_par.")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_s, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))

FAIL: list = []
def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])

import config
from strategy.management import get_management_plan

def _rec(strategy, delta=None, prem_key="current_delta"):
    r = {"trade_id": "BRK00082", "strategy": strategy, "direction": "long",
         "option_side": "call", "strike": 734.0, "contracts": 50,
         "entry_premium": 0.70, "target_premium": 1.40, "stop_premium": 0.53,
         "underlying_stop": 700.00,          # far away: the structure stop must not fire
         "underlying_entry": 736.26,
         "entry_time": "2026-09-21T14:21:00+00:00"}
    if delta is not None:
        r[prem_key] = delta
    return r

PLAN = get_management_plan()
def _decide(rec, prem):
    return PLAN.decide(dict(rec), prem, df_1m=None, open_records=[])

# B1 — par delta exits
_i1 = _decide(_rec("Breakout", delta=0.985), 1.60)
check("B1 at PAR delta the Breakout exits on delta_par",
      _i1 is not None and getattr(_i1, "condition", "") == "delta_par",
      f"intent={getattr(_i1,'reason',None)!r}")

# B2 — THE CONTROL THAT PROVES THE GUILLOTINE IS GONE. Premium is PAST the old
# +100% target (1.60 > 1.40) and delta is mid-range: r81's code would have
# fired target_hit here. It must now HOLD.
_i2 = _decide(_rec("Breakout", delta=0.640), 1.60)
check("B2 CONTROL: below par it HOLDS even past the old +100% target",
      _i2 is None or getattr(_i2, "condition", "") != "target",
      f"intent={getattr(_i2,'reason',None)!r} — 0.640 is the delta its 8 real "
      f"target exits fired at on 2026-09-21")

# B3 — SCOPED, NOT DELETED. The runaway keeps the target the rule was written
# for; removing it everywhere would be a different ruling than the one given.
_i3 = _decide(_rec("RunawayContinuation", delta=0.640), 1.60)
check("B3 CONTROL: a NON-Breakout debit still gets target_hit",
      _i3 is not None and getattr(_i3, "condition", "") == "target",
      f"intent={getattr(_i3,'reason',None)!r}")

# B4 — no delta means HOLD. r82 measured extrinsic-from-mid as a proxy for par
# and killed it: it reaches zero at delta 0.82, two hours early on 81b1afae.
_i4 = _decide(_rec("Breakout", delta=None), 1.60)
check("B4 no delta from the feed -> HOLD, not guess",
      _i4 is None or getattr(_i4, "condition", "") not in ("delta_par", "target"),
      f"intent={getattr(_i4,'reason',None)!r}")

print(f"\n{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} problem(s) {FAIL}")
sys.exit(1 if FAIL else 0)
