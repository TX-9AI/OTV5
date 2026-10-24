#!/usr/bin/env python3
"""
tests/check_exit_single_grid.py  v1.0
v1.0  2026-10-03  TICK.2 — A SINGLE-LEG MARK CLOSE LANDS ON THE VENUE GRID.

  Found by OTV4TEST (MSG-1003-23), measured here: ExitEngine._exit_limit priced
  a FLOOR-policy (or walk-fallback) close with limit_at_mark(mark, floor=tick)
  and NO symbol, so it only rounded to cents. The walk path and the entry ladder
  already snap through execution/tick_size. On a non-penny name a single option
  at $3+ trades in dimes, so a 4.37 close limit is an invalid increment LIVE.

  Drives the REAL _exit_limit (floor policy via a 'hard_stop' reason) with the
  quote stashed on the record, no venue rule cached (the list fallback):
  G1  AVGO (penny class, nickels at $3+), on-nickel quote 4.30/4.40, sell at
      mark 4.37 -> 4.40 (snapped UP for a sell, the trader's favour) — the
      defect: 4.37
  G2  a quote OFF the nickel (4.33/4.41) proves a penny grid -> 4.37 kept
  G3  UNCHANGED: an AVGO VERTICAL at 4.37 -> 4.37 (complex orders not touched)
  G4  a NON-penny name below $3 (nickels): sell at 2.37 -> 2.40 — defect: 2.37
  BORN RED on otv4 f4be1db at G1 G4.

Run:  python3 tests/check_exit_single_grid.py
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


def main():
    from execution.exit_engine import ExitEngine
    eng = ExitEngine.__new__(ExitEngine)        # no init: _exit_limit needs no state

    def lim(sym, structure, mark, bid, ask, side="sell"):
        rec = {"trade_id": "g1", "symbol": sym, "_exit_bid": bid, "_exit_ask": ask}
        px, why = eng._exit_limit(rec, "hard_stop_25%", mark, side, structure)
        return round(float(px), 4), why

    got = lim("AVGO", "single", 4.37, 4.30, 4.40)
    check("G1 AVGO single-leg mark close snaps to the nickel grid (4.40)",
          abs(got[0] - 4.40) < 1e-9, f"got {got}")
    got = lim("QQQ", "single", 4.37, 4.33, 4.41)
    check("G2 an off-nickel quote proves pennies: 4.37 kept", abs(got[0] - 4.37) < 1e-9,
          f"got {got}")
    got = lim("AVGO", "vertical", 4.37, 4.30, 4.40, side="buy")
    check("G3 UNCHANGED: a vertical is not snapped (4.37)", abs(got[0] - 4.37) < 1e-9,
          f"got {got}")
    got = lim("NOTAPENNYNAME", "single", 2.37, 2.30, 2.40)
    check("G4 a non-penny name below $3 snaps to nickels (2.40)", abs(got[0] - 2.40) < 1e-9,
          f"got {got}")
    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — a single-leg mark close posts a valid increment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
