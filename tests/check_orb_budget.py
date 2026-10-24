#!/usr/bin/env python3
"""tests/check_orb_budget.py  v1.0
ORB SIZES TO min(GEOMETRY, BUDGET), AND A CONTRACT DEARER THAN THE BUDGET IS
REFUSED RATHER THAN FLOORED TO ONE.

v1.0  2026-08-31  r201 — born red at r200: `ORB_BUDGET_USD` does not exist and
      the geometry rule has no budget clamp at all.

🔴 THE MEASUREMENT THAT CAUSED THIS. On 2026-08-31 an SPX ORB opened
**50 contracts at $6.95 = $34,750 of premium** on paper. ORB is the only
strategy that sizes on GEOMETRY rather than on risk, so `max(1, floor(width /
stop_distance))` grew without bound as the impulsive stop tightened. Operator:
*"Knowing that we can end up with a nominal position size in the 10s of
thousands of dollars was eye opening. We are going to rein that in."*

🔑 B3 IS THE CHECK THAT PROVES THE OPERATOR'S SCALING CURVE, and the point is
that there is NO RAMP — the curve is what two clamps produce when they meet.
*"The smallest stops get the maximum budget, the biggest stops get a 1 lot
maximum. Everything else falls somewhere in between."* A tight stop makes
geometry large so the BUDGET binds; a wide stop makes geometry small so
GEOMETRY binds. Anyone later tempted to add a ramp should read B3 first.

⚠️ B4 PINS REFUSAL, NOT FLOOR-TO-ONE. A single contract costing more than the
whole budget cannot be inside that budget, and flooring to 1 would blow through
the exact ceiling this exists to impose. `_size_budget` already refuses on the
same arithmetic (`insufficient_capital`), so ORB now behaves like every other
rule at its own budget instead of uniquely.

⚠️ B6 PINS THAT PAPER IS CONSTRAINED TOO. Operator was explicit that paper's
"unlimited" is the ACCOUNT, not the trade. An unconstrained paper sizer
overstates every P&L number against live and makes the two incomparable.

Run:  python3 tests/check_orb_budget.py
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")

_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def main():
    try:
        from config import ORB_BUDGET_USD, ORB_BUDGET_IS_DEFAULT  # noqa: F401
    except ImportError as exc:
        check("B0 config exposes ORB_BUDGET_USD", False, str(exc))
        print("\nFAILED 1: B0 — ORB has no budget at all")
        return 1

    from risk.risk_manager import get_risk_manager
    rm = get_risk_manager()

    def orb(prem, w, d, budget):
        return rm.size_for("long_debit", premium=prem, orb_width=w,
                           orb_stop_distance=d, budget_usd=budget)

    # ── B1: the day that caused this ──────────────────────────────────────
    # SPX, 08-31: 50 contracts at $6.95. Under a $5,000 budget it is 7.
    r = orb(6.95, 25.0, 0.50, 5000)
    check("B1 the $34,750 SPX position is capped by the budget",
          r.contracts == 7 and r.allowed and r.total_cost <= 5000,
          f"n={r.contracts} cost=${r.total_cost:.0f} "
          f"(geometry wanted {r.geometry_wanted})")

    # ── B2: geometry still binds where it is the smaller number ───────────
    r = orb(0.56, 6.35, 3.0, 5000)
    check("B2 a wide stop is bound by GEOMETRY, not the budget",
          r.contracts == r.geometry_wanted < r.budget_allowed,
          f"n={r.contracts} geom={r.geometry_wanted} budget={r.budget_allowed}")

    # ── B3: THE CURVE, and it is not a ramp ───────────────────────────────
    # 🔑 One width, one premium, stops from tight to wide. The result must fall
    # monotonically and END AT 1 — the operator's rule, produced by two clamps
    # rather than by a tuned curve.
    seq = [orb(1.00, 10.0, d, 3000).contracts
           for d in (0.10, 0.25, 0.50, 1.0, 2.0, 5.0, 10.0)]
    check("B3 tight stops get the budget, wide stops get a 1-lot, monotone "
          "in between",
          seq == sorted(seq, reverse=True) and seq[0] == 30 and seq[-1] == 1,
          f"stops 0.10→10.0 give {seq}")

    # ── B4: refuse, do not floor ──────────────────────────────────────────
    r = orb(12.00, 25.0, 0.5, 1000)      # one contract = $1,200 > $1,000
    check("B4 a contract dearer than the whole budget is REFUSED, not 1-lotted",
          (not r.allowed) and r.contracts == 0
          and "orb_budget" in (r.reject_reason or ""),
          f"allowed={r.allowed} n={r.contracts} why={r.reject_reason!r}")

    # ── B5: both clamps are recorded ──────────────────────────────────────
    # ⚠️ Setting a live budget later must be a QUERY against banked paper data,
    # not a guess. Same shape as r198's wing_stretch.
    r = orb(6.95, 25.0, 0.50, 5000)
    check("B5 geometry_wanted and budget_allowed ride on the result",
          r.geometry_wanted == 50 and r.budget_allowed == 7,
          f"wanted={r.geometry_wanted} allowed={r.budget_allowed}")

    # ── B6: paper is constrained too ──────────────────────────────────────
    check("B6 the clamp applies in PAPER — it is not a live-only gate",
          os.environ.get("OT_PAPER_TRADING") == "1" and orb(6.95, 25.0, 0.5,
                                                            5000).contracts == 7,
          "paper's 'unlimited' is the ACCOUNT, not the trade")

    # ── B7: no other rule gained a budget ─────────────────────────────────
    # ⚠️ The budget is ORB's. Butterfly stays on regular position sizing and
    # keeps firing alongside an open trade (r197) — the operator's ruling, and
    # the reason ORB "owning the budget" does not starve it.
    bf = rm.size_for("butterfly", net_debit=0.40, budget_usd=1)
    check("B7 the butterfly ignores the ORB budget entirely",
          bf.rule == "butterfly" and bf.contracts > 0,
          f"rule={bf.rule} n={bf.contracts}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_orb_budget: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
