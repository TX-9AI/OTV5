#!/usr/bin/env python3
# tests/check_spx_tick.py  v1.0
# v1.0  2026-10-03  OTV4TEST r190 (AUD.1) — shared with otv4 TICK.1. Everything after the closing
#       docstring is byte-identical with otv4's gate; these lines and the r106 venv bootstrap sit ABOVE
#       the docstring so the body hash holds and the lander (system python3) can import the modules.
import glob as _g, os as _o, sys as _s          # OTV4TEST: r106 venv bootstrap, kept ABOVE the docstring
for _sp in _g.glob(_o.path.join(_o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))),
                                "venv", "lib", "python*", "site-packages")):
    if _sp not in _s.path:                       # so the shared body below is byte-identical with otv4's
        _s.path.insert(1, _sp)
"""
tests/check_spx_tick.py  v1.0
v1.0  2026-10-03  TICK.1 — AN SPX SINGLE-LEG CLOSE AT $3+ POSTS IN DIMES.

  Cboe: SPX/SPXW series trade in $0.05 below $3.00 and $0.10 at or above.
  ExitEngine._round_to_tick used $0.05 for SPX at every premium, so a live
  single-leg close at 12.35 would be rejected. Drives the REAL _round_to_tick.
  T1  SPX single leg 12.37 -> 12.40 (the defect: 12.35)
  T2  SPXW single leg 3.04 -> 3.00 (at the boundary, dimes)
  T3  UNCHANGED: SPX single leg 2.37 -> 2.35 (below $3, nickels)
  T4  UNCHANGED: SPX spread (not single_leg) 12.37 -> 12.35
  T5  UNCHANGED: QQQ single leg 12.37 -> 12.37 (pennies)
  BORN RED on otv4 2220461 at T1 T2 (no single_leg parameter there).

Run:  python3 tests/check_spx_tick.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


def rt(price, sym, single):
    from execution.exit_engine import ExitEngine
    try:
        return ExitEngine._round_to_tick(price, {"symbol": sym}, single_leg=single)
    except TypeError:
        return ExitEngine._round_to_tick(price, {"symbol": sym})


def main():
    got = rt(12.37, "SPX", True)
    check("T1 SPX single leg 12.37 -> 12.40", abs(got - 12.40) < 1e-9, f"got {got}")
    got = rt(3.04, "SPXW", True)
    check("T2 SPXW single leg 3.04 -> 3.00", abs(got - 3.00) < 1e-9, f"got {got}")
    got = rt(2.37, "SPX", True)
    check("T3 UNCHANGED: SPX single leg 2.37 -> 2.35", abs(got - 2.35) < 1e-9, f"got {got}")
    got = rt(12.37, "SPX", False)
    check("T4 UNCHANGED: SPX spread 12.37 -> 12.35", abs(got - 12.35) < 1e-9, f"got {got}")
    got = rt(12.37, "QQQ", True)
    check("T5 UNCHANGED: QQQ single leg 12.37 -> 12.37", abs(got - 12.37) < 1e-9, f"got {got}")
    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — SPX single-leg closes post a valid increment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
