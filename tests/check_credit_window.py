#!/usr/bin/env python3
"""
tests/check_credit_window.py  v1.0
v1.0  2026-09-21  OTV4TEST r81 (LATE.2) — born RED at 8a1f0c2.

🔴 r71 WIDENED THE CREDIT ENTRY WINDOW TO 15:40 AND IT NEVER REACHED THE CODE.
The admission table moved. `VERTICAL_HOLD_TO_ET` moved. FOUR separate literals
did not, and THE PLAN RUNS BEFORE ADMISSION — sweep_plan and tcs_plan stamp
DORMANT at 14:00 and never emit a signal, so the widened window is never
consulted. Measured on the operator's board 2026-09-21 14:11 ET: "past 14:00
ET — observing only" and "past TCS_ENTRY_END_ET 14", with admission reading
(15,40) at the same instant.

⚠️ WHY r71'S OWN GATE PASSED IS THE FINDING. `check_late_credit_window`
imports NO PLAN MODULE — every assertion is against the admission table and
config constants. It tested the thing that changed rather than the thing that
decides (§21 from the other side: a gate can drive *a* runtime and still miss
the deciding one).

  C1  CLASS: no credit plan reads a *_ET key that config does not define
  C2  the ADMISSION end and EVERY plan's end are the same number
  C3  DRIVEN: the sweep plan is NOT dormant at 14:30 ET
  C4  DRIVEN CONTROL: it IS still dormant at 15:45 — the window still ends
  C5  DRIVEN: the TCS plan is NOT dormant at 14:30 ET

Run:  python3 tests/check_credit_window.py
"""
from __future__ import annotations
import ast, os, sys, tempfile, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 🔴 FAIL CLOSED ON THE STORES, BEFORE ANY REPO IMPORT. Driving a real plan
# WRITES plan rows; the first cut of this checker tried to write to the LIVE
# derived store and was saved only by "database is locked". r72's replay
# contaminated the live plan corpus with 20 rows exactly this way.
_scratch = tempfile.mkdtemp(prefix="check_credit_window.")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_scratch, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_scratch, "derived_store.db"))
FAIL: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])

import config
import strategy.sweep_plan as SP
import strategy.tcs_plan as TP
from execution.position_manager import rules, SWEEP, TCS

# ── C1 — THE CLASS, NOT THE LINE (§20) ────────────────────────────────────
# r317 repaired `SWEEP_CS_LATEST_ET` after a missing key made its default the
# only source. This fork then wrote `SWEEP_CS_LATEST_ET_FORK` — a NEW name,
# never added to config — and the identical defect came back. So this walks
# EVERY credit plan for `getattr(config, "<KEY>", ...)` where KEY names a
# window, and fails on any config does not define. Scoped to *_ET keys on
# purpose: an optional tuning knob may legitimately carry a default, a WINDOW
# BOUND may not, and a canary that refuses correct code is §36's named failure.
_missing = []
for mod in (SP, TP):
    src = open(mod.__file__, encoding="utf-8").read()
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "getattr" and len(node.args) >= 2
                and isinstance(node.args[0], ast.Name) and node.args[0].id == "config"
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)):
            key = node.args[1].value
            if key.endswith("_ET") or key.endswith("_ET_FORK"):
                if not hasattr(config, key):
                    _missing.append(f"{os.path.basename(mod.__file__)}:{key}")
check("C1 CLASS: every *_ET key a credit plan reads is DEFINED in config",
      not _missing,
      f"missing={_missing} — a window bound on a silent default is r317's defect")

# ── C2 — the table and the plans must agree ───────────────────────────────
T = rules()
_adm_sweep = tuple(T[SWEEP].window[1])
_adm_tcs   = tuple(T[TCS].window[1])
_pl_sweep  = tuple(SP.LATEST_ET)
_pl_tcs    = tuple(TP.window_end())
check("C2 the ADMISSION end and EVERY plan end are the same number",
      _adm_sweep == _pl_sweep == _adm_tcs == _pl_tcs,
      f"admission sweep={_adm_sweep} tcs={_adm_tcs}; plan sweep={_pl_sweep} tcs={_pl_tcs} "
      f"— r71 moved the table and left the plans at (14, 0)")

# ── C3/C4/C5 — DRIVEN through the real plan (§21) ─────────────────────────
# 🔑 READ THE PLAN'S OWN VERDICT, not a reconstruction of it. `dormant()` is
# EDGE-TRIGGERED (r41's latch) so the module globals are cleared between drives
# — otherwise the second call goes quiet and a dead gate reads as a pass.
import strategy.plan as PLAN

def _verdict_at(hh, mm):
    PLAN._DORMANT.clear(); PLAN._ASKED.clear()
    pl = SP.SweepPlan()
    pl.prepare(price_now=740.0, now_et=dt.time(hh, mm), chain=None,
               orb_high=741.0, orb_low=735.0, df_1m=None)
    return getattr(pl.planner, "_last", None)

_v1430 = _verdict_at(14, 30)
_w1430 = str(_v1430[2]) if _v1430 else ""
check("C3 DRIVEN: the sweep plan is NOT refused by entry_window at 14:30 ET",
      "entry_window" not in _w1430,
      f"verdict={_v1430!r} — at (14,0) this read 'past 14:00 ET — observing only'; "
      f"reaching a LATER gate is the proof the window opened")

_v1545 = _verdict_at(15, 45)
_w1545 = str(_v1545[2]) if _v1545 else ""
check("C4 DRIVEN CONTROL: it IS still refused at 15:45 — the window still ends",
      "entry_window" in _w1545 and "15:40" in _w1545,
      f"verdict={_v1545!r} — a fix that removed the bound entirely would pass "
      f"C3 and silently delete the window")

check("C5 the TCS end moved with it (one constant, not four literals)",
      tuple(TP.window_end()) == tuple(config.CREDIT_ENTRY_END_ET) == (15, 40),
      f"tcs={tuple(TP.window_end())} credit_end={tuple(config.CREDIT_ENTRY_END_ET)}")

print(f"\n{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} problem(s) {FAIL}")
sys.exit(1 if FAIL else 0)
