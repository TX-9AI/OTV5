#!/usr/bin/env python3
"""tests/check_plan_r_owner.py — v5.0
v5.0  2026-10-25  (PLN.R) — A STRATEGY'S OWN R VERDICT SURVIVES THE PLAN'S ECONOMICS. debit_directional /
      credit_spread / butterfly overwrote check("r") and self.r after Breakout judged its own price R, so the
      stored row showed the premium R with no verdict.

Drives the real PlanTick (strategy/plan.py).
  P1  Breakout's shape: check("r", 3.79, True) then debit_directional -> checks["r"] is (3.79, True), t.r is 3.79
  P2  ...and the premium R is kept as checks["r_premium"] (value == the economics R, verdict None)
  P3  a refused R (verdict False) also stands
  P4  a plan that never judged R is unchanged: checks["r"] is (economics R, None), no r_premium, executable() decides
  P5  credit_spread and butterfly obey the same rule

Born red on 4d4942b (OTV5 r24) at P1 P2 P3 P5.
Run:  python3 tests/check_plan_r_owner.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_fails = []


def ck(tag, ok, msg=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {tag}  {msg}")
    if not ok:
        _fails.append(tag)


def tick():
    """A real PlanTick from a real Plan; no terminal is called, so nothing is written."""
    from strategy import plan as P
    P.REGISTRY.pop("PlnRCheck", None)
    pl = P.Plan("PlnRCheck", ("r",))
    pl.symbol = "TST"
    return pl.tick(700.0, "long")


def main():
    t = tick()
    t.check("r", 3.79, True)
    t.debit_directional(2.50, 0.50, 0.05, 1.0, 4.0, invalidation=699.0, trigger=701.0)
    ck("P1", t.checks.get("r") == (3.79, True) and t.r == 3.79, f"r check {t.checks.get('r')} t.r {t.r}")
    rp = t.checks.get("r_premium")
    ck("P2", rp is not None and rp[1] is None and rp[0] is not None and abs(rp[0] - 3.79) > 1e-9,
       f"r_premium {rp}")

    t = tick()
    t.check("r", 0.4, False)
    t.debit_directional(2.50, 0.50, 0.05, 1.0, 4.0)
    ck("P3", t.checks.get("r") == (0.4, False) and t.r == 0.4, f"{t.checks.get('r')} t.r {t.r}")

    t = tick()
    t.debit_directional(2.50, 0.50, 0.05, 1.0, 4.0)
    econ = t.r
    ck("P4", t.checks.get("r") == (econ, None) and "r_premium" not in t.checks and econ is not None,
       f"{t.checks.get('r')} r_premium={'r_premium' in t.checks}")

    t1 = tick()
    t1.check("r", 2.0, True)
    try:
        t1.credit_spread(100.0, 99.0, 0.40)
    except TypeError:
        t1.credit_spread(100.0, 99.0, 0.40, invalidation=101.0)
    t2 = tick()
    t2.check("r", 2.0, True)
    t2.butterfly(1.00, 5.0)
    ck("P5", t1.checks.get("r") == (2.0, True) and t2.checks.get("r") == (2.0, True)
       and "r_premium" in t1.checks and "r_premium" in t2.checks,
       f"credit {t1.checks.get('r')} fly {t2.checks.get('r')}")


if __name__ == "__main__":
    main()
    print("FAIL: " + " ".join(_fails) if _fails else "ALL PASS")
    sys.exit(1 if _fails else 0)
