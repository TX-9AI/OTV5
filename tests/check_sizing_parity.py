#!/usr/bin/env python3
"""tests/check_sizing_parity.py  v1.0
THE REFACTOR MOVED THREE RULES. IT MUST NOT HAVE MOVED THEIR ARITHMETIC.

v1.0  2026-08-30  r192 — the 25-row golden table, captured by running
      r191's own code before any edit, pinning that the refactor moved
      three rules without moving their arithmetic.

🔑 THE TABLE BELOW WAS CAPTURED BY RUNNING r191's OWN CODE BEFORE ANY EDIT.
That is what makes it evidence rather than decoration: it is not what I think
the rules should return, it is what they DID return, read off the tree that has
been trading. r192 relocated `compute_size` to `_size_budget` and
`compute_condor_leg_size` to `_size_vertical` behind one door; if a single
number below moves, the change stopped being a move and became a rewrite, and
nobody asked for a rewrite of the budget, butterfly or vertical rules.

⚠️ THE GRID IS DELIBERATELY MIXED. Twelve long_debit rows across three
stop_premium values (the r121 risk denominator, which is OFF by default — the
rows prove it stays off), eight butterfly rows across the VIX half-size flag,
five vertical rows. Each block carries BOTH allowed and refused outcomes: a
parity table of only-passing cases would not notice a rejection rung
disappearing, which is exactly the class of change ORB's cap exemption is.

⚠️ ORB GEOMETRY IS NOT IN THIS TABLE, and must never be added to it. It has no
r191 behaviour to be at parity WITH — it did not reach the order at all. Its
correctness lives in check_orb_geometry_size.py, which asserts the ordered
quantity. Mixing the two would let "unchanged" and "newly working" share one
green.

Born red at r191: `size_for` does not exist there.

Run:  python3 tests/check_sizing_parity.py
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")

# (rule, inputs, (contracts, cost_per_contract, total_cost, max_loss, allowed))
GOLD = [
    ("long_debit", (0.35, 0.0),  (5, 35.0, 175.0, 175.0, True)),
    ("long_debit", (0.35, 0.2),  (5, 35.0, 175.0, 175.0, True)),
    ("long_debit", (0.35, 0.9),  (5, 35.0, 175.0, 175.0, True)),
    ("long_debit", (0.8, 0.0),   (2, 80.0, 160.0, 160.0, True)),
    ("long_debit", (0.8, 0.2),   (2, 80.0, 160.0, 160.0, True)),
    ("long_debit", (0.8, 0.9),   (2, 80.0, 160.0, 160.0, True)),
    ("long_debit", (1.2, 0.0),   (1, 120.0, 120.0, 120.0, True)),
    ("long_debit", (1.2, 0.2),   (1, 120.0, 120.0, 120.0, True)),
    ("long_debit", (1.2, 0.9),   (1, 120.0, 120.0, 120.0, True)),
    ("long_debit", (2.4, 0.0),   (0, 0.0, 0.0, 0.0, False)),
    ("long_debit", (2.4, 0.2),   (0, 0.0, 0.0, 0.0, False)),
    ("long_debit", (2.4, 0.9),   (0, 0.0, 0.0, 0.0, False)),
    ("butterfly",  (0.4, False), (5, 40.0, 200.0, 200.0, True)),
    ("butterfly",  (0.4, True),  (2, 40.0, 80.0, 80.0, True)),
    ("butterfly",  (0.9, False), (2, 90.0, 180.0, 180.0, True)),
    ("butterfly",  (0.9, True),  (1, 90.0, 90.0, 90.0, True)),
    ("butterfly",  (1.1, False), (1, 110.0, 110.0, 110.0, True)),
    ("butterfly",  (1.1, True),  (0, 0.0, 0.0, 0.0, False)),
    ("butterfly",  (2.75, False), (0, 0.0, 0.0, 0.0, False)),
    ("butterfly",  (2.75, True),  (0, 0.0, 0.0, 0.0, False)),
    ("vertical",   (1.0, 0.3),   (2, 70.0, 140.0, 140.0, True)),
    ("vertical",   (2.0, 0.6),   (1, 140.0, 140.0, 140.0, True)),
    ("vertical",   (2.0, 1.2),   (2, 80.0, 160.0, 160.0, True)),
    ("vertical",   (5.0, 0.6),   (0, 0.0, 0.0, 0.0, False)),
    ("vertical",   (5.0, 5.5),   (0, 0.0, 0.0, 0.0, False)),
]


def main():
    from risk.risk_manager import get_risk_manager
    rm = get_risk_manager()

    if not hasattr(rm, "size_for"):
        # Named failure, never a traceback — see check_orb_geometry_size G0.
        print("  FAIL  P0 RiskManager exposes the single sizing door `size_for`")
        print("\nFAILED 1: P0 — the parity table cannot be exercised")
        return 1

    bad = []
    for rule, inp, exp in GOLD:
        if rule == "long_debit":
            r = rm.size_for("long_debit", premium=inp[0], stop_premium=inp[1])
        elif rule == "butterfly":
            r = rm.size_for("butterfly", net_debit=inp[0],
                            butterfly_half_size=inp[1])
        else:
            r = rm.size_for("vertical", spread_width=inp[0], credit=inp[1])
        got = (r.contracts, round(r.cost_per_contract, 2),
               round(r.total_cost, 2), round(r.max_loss, 2), r.allowed)
        if got != exp:
            bad.append(f"{rule}{inp}: r191 gave {exp}, now {got}")

    print(f"  {'PASS' if not bad else 'FAIL'}  P1 all {len(GOLD)} r191 rows "
          f"reproduce exactly under size_for()")
    for b in bad[:8]:
        print("        " + b)

    # P2 — every rule names itself, so a trade record can answer "which sizer
    # decided this" without reconstructing it from the log. r181 was invisible
    # for two days precisely because nothing on the row said.
    rules = {
        rm.size_for("long_debit", premium=0.35).rule,
        rm.size_for("butterfly", net_debit=0.4).rule,
        rm.size_for("vertical", spread_width=1.0, credit=0.3).rule,
        rm.size_for("long_debit", premium=1.2, orb_width=6.35,
                    orb_stop_distance=0.61).rule,
    }
    ok2 = rules == {"budget", "butterfly", "vertical", "orb_geometry"}
    print(f"  {'PASS' if ok2 else 'FAIL'}  P2 each rule stamps its name on the "
          f"result  — {sorted(rules)}")

    # P3 — an UNKNOWN structure must fall to the budget rule, not to geometry
    # and not to a permissive default. Same direction as the debit cutoff:
    # a strategy that forgets to declare gets the restrictive reading.
    unknown = rm.size_for("no_such_structure", premium=0.35)
    ok3 = unknown.rule == "budget" and unknown.contracts == 5
    print(f"  {'PASS' if ok3 else 'FAIL'}  P3 unknown structure falls closed to "
          f"the budget rule  — rule={unknown.rule} n={unknown.contracts}")

    print()
    fails = (1 if bad else 0) + (0 if ok2 else 1) + (0 if ok3 else 1)
    if fails:
        print(f"FAILED {fails} — the refactor changed behaviour it was not "
              f"supposed to touch")
        return 1
    print("check_sizing_parity: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
