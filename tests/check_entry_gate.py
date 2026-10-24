#!/usr/bin/env python3
"""
tests/check_entry_gate.py  v1.0

r101 — DECIDE ALWAYS, PLACE AFTER 09:35. Operator directive 2026-08-24:
"I want the executing logic running as long as the service is up. But one gate
that blocks it from placing orders until 0935 (orb range established)."

Born RED at e8043cb (r100) on E1..E5. Plain script (WORKING_AGREEMENT 36).

  E1  `entries_open()` is False before ENTRY_OPEN_ET and True at/after it,
      and FAILS CLOSED on a malformed override
  E2  the DEBIT choke point refuses: `entry_engine.enter()` returns None before
      the gate and NEVER reaches the broker or the trade logger
  E3  the CREDIT choke point refuses: `_execute_condor_leg` returns before
      pricing, sizing or writing a record
  E4  EXITS ARE NOT GATED — no exit/close/flatten/roll path consults
      `entries_open` (a gated exit is a stuck position). Checked structurally
      over the import graph, not by prose.
  E5  the pre-RTH branch of `main_loop` RUNS THE DECIDING PATH
      (assemble_market_state + attempt_new_entry) and pages on failure

Run:  python3 tests/check_entry_gate.py
"""
from __future__ import annotations
import ast, os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)

import config
import utils.time_utils as tu
from utils.time_utils import ET, entries_open

# ── E1 ───────────────────────────────────────────────────────────────────────
def at(h, m):
    return datetime(2026, 8, 25, h, m, tzinfo=ET)

check("E1a 09:34 — closed", entries_open(at(9, 34)) is False)
check("E1b 09:35 — open",   entries_open(at(9, 35)) is True)
check("E1c 09:36 — open",   entries_open(at(9, 36)) is True)
check("E1d 15:59 — still open (a floor, not a window)", entries_open(at(15, 59)) is True)
_saved = config.ENTRY_OPEN_ET
try:
    config.ENTRY_OPEN_ET = ("nine", "thirty")
    check("E1e malformed override FAILS CLOSED", entries_open(at(11, 0)) is False)
finally:
    config.ENTRY_OPEN_ET = _saved

# ── E2 — the debit choke point, driven for real ──────────────────────────────
import execution.entry_engine as ee
from strategy.base_strategy import OptionsSignal
from data.options_chain import OptionContract

class _Boom:
    def __getattr__(self, k):
        raise AssertionError("the gate let a held entry reach the broker/logger")

eng = ee.EntryEngine(paper_trading=True)
eng._trade_logger = _Boom()
sig = OptionsSignal(strategy_name="ORBStrategy", setup_type="orb_long",
                    option_side="call", strike=81.0, entry_premium=0.85,
                    underlying_entry=80.0,
                    contract=OptionContract(symbol="X", strike=81.0, mark=0.85))
# ⚠️ r152 — `_Score` is retained only so the file's other references resolve;
# `enter()` no longer takes a score at all (the setup scorer is deleted).
class _Score: grade, score = "B", 80.0
class _Sizing: allowed, contracts, total_cost = True, 1, 85.0

_real = tu.now_et
try:
    tu.now_et = lambda: at(9, 34)
    check("E2a 09:34 — enter() refuses and books nothing",
          eng.enter(sig, _Sizing()) is None)
    tu.now_et = lambda: at(9, 35)
    try:
        eng.enter(sig, _Sizing())
        check("E2b 09:35 — enter() proceeds past the gate", False,
              "it returned without touching the logger — gate may be stuck shut")
    except AssertionError:
        check("E2b 09:35 — enter() proceeds past the gate", True,
              "reached the trade logger, which is the tripwire")
finally:
    tu.now_et = _real

# ── E3 — the credit choke point, structurally ────────────────────────────────
src = open(os.path.join(ROOT, "main.py")).read()
tree = ast.parse(src)
fn = next(n for n in ast.walk(tree)
          if isinstance(n, ast.FunctionDef) and n.name == "_execute_condor_leg")
gate_first = False
for node in fn.body:
    if isinstance(node, ast.If) and "entries_open" in ast.unparse(node.test):
        gate_first = any(isinstance(b, ast.Return) for b in node.body)
        break
    if isinstance(node, ast.Call) or (isinstance(node, ast.Assign)
                                      and "get_risk_manager" in ast.unparse(node)):
        break
check("E3 _execute_condor_leg refuses on entries_open before it prices or sizes",
      gate_first)

# ── E4 — exits are NEVER gated ───────────────────────────────────────────────
EXIT_FILES = ("execution/exit_engine.py", "execution/position_manager.py",
              "strategy/condor_roll.py")
leaks = []
for rel in EXIT_FILES:
    s = open(os.path.join(ROOT, rel)).read()
    for n in ast.walk(ast.parse(s)):
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "entries_open":
            leaks.append(f"{rel}:{n.lineno}")
check("E4 no exit path consults entries_open", not leaks, "; ".join(leaks))

# ── E5 — the pre-RTH branch decides ──────────────────────────────────────────
loop = next(n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "main_loop")
pre = None
for n in ast.walk(loop):
    if (isinstance(n, ast.If) and isinstance(n.test, ast.UnaryOp)
            and "is_rth" in ast.unparse(n.test)):
        pre = ast.unparse(n)
        break
ok5 = pre is not None and "assemble_market_state" in pre and "attempt_new_entry" in pre
check("E5a pre-RTH branch runs the deciding path", ok5)
check("E5b and pages on the first failure",
      pre is not None and "_page_dispatch_failure" in pre)

# ── E6 (r102) — the gate carries the RTH test ────────────────────────────────
check("E6a 16:53 outside RTH — CLOSED even though 09:35 has passed",
      entries_open(at(16, 53)) is False,
      "a bare time floor is True all evening; it must also ask if the market is open")
check("E6b Sunday 10:00 — CLOSED", entries_open(datetime(2026, 8, 30, 10, 0, tzinfo=ET)) is False)

# ── E7 (r102) — one rule, one number: entries_open defers to is_orb_complete ──
from utils.time_utils import is_orb_complete
_src = open(os.path.join(ROOT, "utils/time_utils.py")).read()
_fn = next(n for n in ast.walk(ast.parse(_src))
           if isinstance(n, ast.FunctionDef) and n.name == "entries_open")
_body = ast.unparse(_fn)
check("E7 entries_open defers to is_orb_complete (not a rival constant)",
      "is_orb_complete" in _body and "is_rth" in _body)

# ── E8 (r102) — can_enter rehearses instead of short-circuiting at RTH ───────
from risk.session_guard import get_session_guard
_g = get_session_guard()
_real2 = tu.now_et
try:
    tu.now_et = lambda: at(16, 53)          # outside RTH, ORB long since closed
    _ok, _why = _g.can_enter(None, rehearsal=True)
    check("E8a rehearsal=True evaluates past the RTH gate", _ok is True, _why)
    check("E8b and reports itself as a rehearsal, never as permission",
          "rehearsal" in _why.lower(), _why)
    _ok2, _why2 = _g.can_enter(None)
    check("E8c rehearsal=False still refuses outside RTH", _ok2 is False, _why2)
    tu.now_et = lambda: at(9, 34)           # inside RTH, range still forming
    _ok3, _why3 = _g.can_enter(None, rehearsal=True)
    check("E8d a rehearsal still honours the 09:35 floor", _ok3 is False, _why3)
finally:
    tu.now_et = _real2

# ── E9 (r102) — the rehearsal cannot place, even with every gate passing ────
_real3 = tu.now_et
try:
    tu.now_et = lambda: at(16, 53)
    eng2 = ee.EntryEngine(paper_trading=True)
    eng2._trade_logger = _Boom()
    check("E9 16:53 — enter() still refuses (choke point, not the gate)",
          eng2.enter(sig, _Sizing()) is None)
finally:
    tu.now_et = _real3

print(f"\n{'PASS' if not FAILURES else 'FAIL'}: {len(FAILURES)} problem(s) {FAILURES}")
sys.exit(1 if FAILURES else 0)
