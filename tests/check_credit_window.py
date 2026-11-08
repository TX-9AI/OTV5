#!/usr/bin/env python3
"""
tests/check_credit_window.py  v5.1
v5.1  2026-11-08  OTV5 r76 (RETIRE.1) — RE-POINTED (WA 38.4): the sweep plan is removed, so C1/C2 read the TCS plan alone and C3/C4 (which drove the
      sweep plan) go with it; C5 unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
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

  C1  CLASS: the credit plan reads no *_ET key that config does not define
  C2  the ADMISSION end and the TCS plan's end are the same number
  C5  the TCS end is config.CREDIT_ENTRY_END_ET, 15:40
  (r76: C3/C4 drove the sweep plan, which is removed with the sweep)

Run:  python3 tests/check_credit_window.py
"""
from __future__ import annotations
import ast, os, sys, tempfile
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
import strategy.tcs_plan as TP
from execution.position_manager import rules, TCS

# ── C1 — THE CLASS, NOT THE LINE (§20) ────────────────────────────────────
# Walk the credit plan for `getattr(config, "<KEY>", ...)` where KEY names a window, and fail on any config does
# not define. r76: the sweep plan is removed; TCS is the one credit plan with an entry.
_missing = []
for mod in (TP,):
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
check("C1 CLASS: every *_ET key the credit plan reads is DEFINED in config",
      not _missing,
      f"missing={_missing} — a window bound on a silent default is r317's defect")

# ── C2 — the table and the plan must agree ────────────────────────────────
T = rules()
_adm_tcs = tuple(T[TCS].window[1])
_pl_tcs = tuple(TP.window_end())
check("C2 the ADMISSION end and the TCS plan's end are the same number",
      _adm_tcs == _pl_tcs, f"admission tcs={_adm_tcs}; plan tcs={_pl_tcs}")

check("C5 the TCS end is the one credit end (one constant, not four literals)",
      tuple(TP.window_end()) == tuple(config.CREDIT_ENTRY_END_ET) == (15, 40),
      f"tcs={tuple(TP.window_end())} credit_end={tuple(config.CREDIT_ENTRY_END_ET)}")

print(f"\n{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} problem(s) {FAIL}")
sys.exit(1 if FAIL else 0)
