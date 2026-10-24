#!/usr/bin/env python3
"""
tests/check_manage_call.py  v1.2

v1.2  2026-09-26  OTV4TEST r149 (EOD.1) — M3 and M4 RE-POINTED; the ORDER REVERSES. The operator:
      "Resting limit orders at 1545, ladder exits at 1550 if they're not the assignment risk type."
      The credit vertical (assignment risk) now goes FIRST, at EOD_RESTING_AT_ET (15:45), and the
      debit is HELD until EOD_LADDER_AT_ET (15:50). M3a/M3b at 15:46: vertical closed, debit held and
      still open, nothing failed. M3c at the resting minute: the same. M3d at the ladder minute: both.
      Both minutes still DERIVED from config, and the assert now pins resting BEFORE ladder. M4: the
      manage pass is gated on eod_close_due(False) — held debits stay managed until 15:50.

v1.1  2026-09-20  OTV4TEST r71 (LATE.1) — M3c RE-POINTED, M3d ADDED, BOTH
      MINUTES DERIVED. Until r71 the hard close and the vertical hold were THE
      SAME MINUTE, so an assertion written against 15:45 could not say which of
      the two it was pinning — and M3c ("both flattened") went red the moment
      the operator separated them. RE-POINTED AT THE NEW CONTRACT, NOT LOOSENED
      (r33/r43/r64): M3c now pins THE GAP — at `HARD_CLOSE_ET` the debit goes
      and the credit STAYS — and M3d pins the hold itself.
      🔑 BOTH READ FROM `config`, PLUS AN ASSERT THAT THE HOLD IS AFTER THE
      CLOSE, so one literal can never again stand for two different facts.
      ⚠️ THE EVIDENCE IT WAS ALWAYS MEANT TO BE DERIVED WAS IN THE FILE: this
      module has carried `import config` UNUSED since v1.0.
v1.0  2026-08-24  OTV4 r99 (ea6d773, MAINLINE — inherited at the fork) —
      born RED at df44518 (r98) on M1, M3, M4. That commit is the one that
      introduced "verticals hold to 15:45"; r71 is what supersedes it.

r99 — THE MANAGE BRANCH MUST BE CALLABLE, AND THE FLATTEN MUST HOLD VERTICALS.

Born RED at df44518 (r98) on M1, M3, M4. Plain script (WA 36).

  M1  every `pos_mgr.<method>(kw=...)` call in main.py passes ONLY keywords the
      PositionManager method actually accepts (the `ms=None` TypeError class —
      r65 renamed the retired label kwarg at the call and deleted it from the signature; every
      tick with an open position raised into the loop catch-all)
  M2  the call is exercised for real: a stub PositionManager receives the
      exact kwargs main passes and does not raise
  M3  flatten_all HOLDS a credit vertical before VERTICAL_HOLD_TO_ET and
      FLATTENS it after (executed against a patched clock). r71 — the hard
      close and the hold are no longer the same minute, so M3c pins the gap
      (debit out, credit held) and M3d pins the hold itself.
  M4  main.py's hard-close branch runs a manage pass while verticals are held

Run:  python3 tests/check_manage_call.py
"""
from __future__ import annotations
import ast, os, sys, inspect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)

import execution.position_manager as pm
src = open(os.path.join(ROOT, "main.py")).read()
tree = ast.parse(src)

# M1 — kwargs at every pos_mgr.<method>() call vs the real signature
bad = []; seen = 0
for node in ast.walk(tree):
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "pos_mgr"):
        meth = getattr(pm.PositionManager, node.func.attr, None)
        if meth is None:
            bad.append(f"{node.func.attr}: no such method"); continue
        params = inspect.signature(meth).parameters
        accepts_kw = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
        seen += 1
        for kw in node.keywords:
            if kw.arg is not None and kw.arg not in params and not accepts_kw:
                bad.append(f"line {node.lineno} {node.func.attr}({kw.arg}=...)")
check("M1 every pos_mgr.* call in main.py matches its signature", not bad, "; ".join(bad) or f"{seen} calls")

# M2 — replay main's manage kwargs against the real method on a stub instance
calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
         and n.func.attr == "manage_open_position"]
ok = bool(calls)
for n in calls:
    kws = {k.arg: None for k in n.keywords}
    try:
        inspect.signature(pm.PositionManager.manage_open_position).bind(object(), **kws)
    except TypeError as e:
        ok = False; print("     ", e)
check("M2 manage_open_position kwargs bind against the real signature", ok, f"{len(calls)} call(s)")

# M3 — flatten_all holds a credit vertical before 15:45, flattens after
import config
from datetime import datetime
from utils.time_utils import ET
booked = []
class _TL:
    def get_open_trades(self): return []
class _PM(pm.PositionManager):
    def __init__(self):
        self.paper_trading = True; self._trade_logger = _TL(); self._open_records = []
    def _fetch_current_premium(self, record, chain=None): return 0.10
    def _execute_exit(self, record, decision, premium):
        booked.append(record["trade_id"]); return True
vert = {"trade_id": "VERT0001", "strategy": "SweepCreditSpread", "setup_type": "sweep_credit_call",
        "is_condor_leg": 1, "entry_premium": 0.30, "contracts": 1}
deb  = {"trade_id": "DEBT0001", "strategy": "ORBStrategy", "setup_type": "orb", "entry_premium": 0.50, "contracts": 1}
real_now = pm.now_et if hasattr(pm, "now_et") else None
import utils.time_utils as tu
_orig = tu.now_et
try:
    rest_h, rest_m = config.EOD_RESTING_AT_ET
    lad_h, lad_m = config.EOD_LADDER_AT_ET
    assert (rest_h, rest_m) < (lad_h, lad_m), "assignment risk must rest BEFORE the debit ladder"
    tu.now_et = lambda: datetime(2026, 8, 24, 15, 46, tzinfo=ET)
    p = _PM(); p._open_records = [dict(vert), dict(deb)]; booked.clear()
    failed = p.flatten_all("hard_close")
    check("M3a 15:46 — vertical closed (assignment risk), debit HELD", booked == ["VERT0001"] and not failed,
          f"booked={booked} failed={failed}")
    check("M3b 15:46 — held debit stays in open records", any(r["trade_id"] == "DEBT0001" for r in p._open_records))
    tu.now_et = lambda: datetime(2026, 8, 24, rest_h, rest_m, tzinfo=ET)
    p = _PM(); p._open_records = [dict(vert), dict(deb)]; booked.clear()
    p.flatten_all("hard_close")
    check(f"M3c {rest_h:02d}:{rest_m:02d} resting — vertical closed, debit STILL HELD",
          booked == ["VERT0001"] and any(r["trade_id"] == "DEBT0001" for r in p._open_records),
          f"booked={booked}")
    tu.now_et = lambda: datetime(2026, 8, 24, lad_h, lad_m, tzinfo=ET)
    p = _PM(); p._open_records = [dict(vert), dict(deb)]; booked.clear()
    p.flatten_all("hard_close")
    check(f"M3d {lad_h:02d}:{lad_m:02d} ladder — both flattened",
          sorted(booked) == ["DEBT0001", "VERT0001"], f"booked={booked}")
finally:
    tu.now_et = _orig

# M4 — the hard-close branch in main_loop runs a manage pass for held verticals
loop = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main_loop")
hc = None
for n in ast.walk(loop):
    if isinstance(n, ast.If) and "is_hard_close_time" in ast.unparse(n.test):
        hc = ast.unparse(n); break
check("M4 r149: hard-close branch manages held debits until they are due (eod_close_due(False))",
      hc is not None and "manage_open_position" in hc and "eod_close_due" in hc and "_ecd(False)" in hc)

print(f"\n{'PASS' if not FAILURES else 'FAIL'}: {len(FAILURES)} problem(s) {FAILURES}")
sys.exit(1 if FAILURES else 0)
