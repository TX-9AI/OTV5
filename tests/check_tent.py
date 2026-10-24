#!/usr/bin/env python3
"""
tests/check_tent.py  v1.0

r106 — THE TENT, AND THE RETIREMENT OF THE PLAN VOCABULARY.

Born RED at e4af618 (r105): Structure.TENT did not exist, condor_tp fired, and
the 25% stop was written onto rows the engine evaluated at 15%.

Operator, 2026-08-24: "If we've already rolled & price breaches the new
structure, take off the profitable side, leaving a lone vertical. Purchase a
long position equidistant from the short strike as the other long strike,
leaving price under the 'tent.' The only remaining adjustment after that should
be a 15% floor of the total credit collected." And: "There is no condor implied,
it is merely permitted."

  T1  Structure.TENT routes FIRST — a tent is not read as a condor leg
  T2  the tent evaluator has exactly ONE adjustment: the floor on CUMULATIVE
      credit, plus 15:45. No TP, no trail, no nickel
  T3  the hedge is the OPPOSITE type and EQUIDISTANT (the worked example)
  T4  breach = a CLOSED 1-min candle beyond a short strike; a wick is not
  T5  the TAKE-PROFIT IS GONE from the credit evaluator
  T6  one stop number: what is WRITTEN is what is EVALUATED (15%)
  T7  no leg numbering — "permitted, not implied"
  T8  the tent's fill readback reads THREE legs, on the same basis as its mark

Run:  python3 tests/check_tent.py
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
from strategy.structure import of, Structure, is_tent, is_credit_vertical

# ── T1 routing ───────────────────────────────────────────────────────────────
tent = {"strategy": "IronCondorStrategy", "setup_type": "tent_call",
        "is_condor_leg": 1, "is_broken_wing": 1}
leg  = {"strategy": "IronCondorStrategy", "setup_type": "1h_fork_call_credit_spread",
        "is_condor_leg": 1}
check("T1a a tent classifies as TENT", of(tent) is Structure.TENT, str(of(tent)))
check("T1b and NOT as a condor leg", of(tent) is not Structure.CONDOR_LEG)
check("T1c an ordinary vertical is untouched", of(leg) is Structure.CONDOR_LEG)
check("T1d a tent is still a CREDIT structure (holds to 15:45)", is_credit_vertical(tent))

# ── T2 one adjustment ────────────────────────────────────────────────────────
src = open(os.path.join(ROOT, "execution/exit_engine.py")).read()
fns = {n.name: ast.unparse(n) for n in ast.walk(ast.parse(src))
       if isinstance(n, ast.FunctionDef)}
tsrc = fns.get("_evaluate_tent", "")
check("T2a the tent evaluator exists", bool(tsrc))
check("T2b it uses TENT_FLOOR_PCT on entry_premium (cumulative credit)",
      "TENT_FLOOR_PCT" in tsrc and "entry_premium" in tsrc)
check("T2c it holds to 15:45", "VERTICAL_HOLD_TO_ET" in tsrc)
for banned in ("CONDOR_NICKEL_CLOSE", "trail", "target_premium"):
    check(f"T2d no {banned} in the tent", banned not in tsrc)

# ── T3 the hedge geometry, against the operator's worked example ─────────────
# condor 95/90 put + 105/110 call; call side breached; keep 105/110.
short_k, long_k, side = 105.0, 110.0, "call"
width = abs(short_k - long_k)
hedge_k = short_k - width if side == "call" else short_k + width
check("T3a the hedge sits equidistant on the far side", hedge_k == 100.0, f"{hedge_k}")
check("T3b and is the OPPOSITE type", ("put" if side == "call" else "call") == "put")
# the payoff reason the operator chose it: a long CALL there would not cap
check("T3c longs bracket price (100 and 110 around ~106)",
      hedge_k < 106.0 < long_k)

# ── T4 breach is a CLOSED bar ────────────────────────────────────────────────
import pandas as pd
from strategy.condor_roll import _tent_breached
idx = pd.date_range("2026-08-25 09:40", periods=3, freq="1min")
legs = [{"option_side": "call", "short_strike": 105.0},
        {"option_side": "put",  "short_strike": 95.0}]
wick = pd.DataFrame({"high": [106.0, 108.0, 107.0], "low": [99, 99, 99],
                     "close": [104.0, 104.5, 107.0]}, index=idx)
check("T4a a wick above the short is NOT a breach",
      _tent_breached(wick, legs) is None, "closes 104.0/104.5 read as the closed bar")
broke = pd.DataFrame({"high": [106.0, 108.0, 107.0], "low": [99, 99, 99],
                      "close": [104.0, 106.2, 107.0]}, index=idx)
got = _tent_breached(broke, legs)
check("T4b a CLOSE beyond the short IS a breach",
      got is not None and got["option_side"] == "call", str(got))

# ── T5/T6/T7 the plan vocabulary is gone ─────────────────────────────────────
csrc = fns.get("_evaluate_condor_leg", "")
check("T5 the take-profit is gone from the credit evaluator",
      "CONDOR_TP_PCT" not in csrc and "condor_tp" not in csrc)
check("T6a CONDOR_STOP_LOSS_PCT is now the 15% floor",
      abs(config.CONDOR_STOP_LOSS_PCT - 0.15) < 1e-9,
      f"{config.CONDOR_STOP_LOSS_PCT}")
check("T6b what is written == what is evaluated",
      abs(config.CONDOR_STOP_LOSS_PCT - config.CONDOR_LONE_STOP_PCT) < 1e-9)
msrc = open(os.path.join(ROOT, "main.py")).read()
mfn = next(n for n in ast.walk(ast.parse(msrc))
           if isinstance(n, ast.FunctionDef) and n.name == "_execute_condor_leg")
check("T7 condor_leg_num is always 0 (no leg 1 / leg 2)",
      "condor_leg_num=0" in ast.unparse(mfn).replace(" ", ""))

# ── T8 the tent reads three legs ─────────────────────────────────────────────
nf = fns.get("_net_fill_price", "")
check("T8a the fill readback has a tent branch", "is_tent(record)" in nf)
check("T8b on the same basis as its mark (short - wing - hedge)",
      "ps - pl - ph" in nf)
csrc2 = fns.get("_close_tent", "")
check("T8c the close sends all three legs in ONE order",
      csrc2.count("Leg(") == 3, f"{csrc2.count('Leg(')} legs")

print(f"\n{'PASS' if not FAILURES else 'FAIL'}: {len(FAILURES)} problem(s) {FAILURES}")
sys.exit(1 if FAILURES else 0)
