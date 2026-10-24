#!/usr/bin/env python3
"""tests/check_orb_geometry_size.py  v2.1
v2.1  2026-08-31  r201 — the geometry cases pass an EXPLICIT budget so they
      measure the arithmetic and not the box's risk setting, and G3c is
      rewritten: it pinned the 08-28 cap exemption, which r201 REVERSES.
      Replaced rather than deleted — geometry is still exempt from the
      RISK-PER-TRADE rule and is now bound by its OWN budget. Two ceilings,
      and conflating them is how a reversal gets half-applied later.
ORB sizes on ACTUAL risk, and THE ORDER RECEIVES THAT NUMBER.

v2.0  2026-08-30  r192 — REWRITTEN TO EXECUTE. v1.0 pinned the bug:
      it re-implemented the geometry inside the test and asserted the
      PRESENCE of `signal.contracts = _geo` in main.py source. G5 now
      captures the quantity handed to `_place_single_leg`.

🔴 v1.0 DID NOT MISS r181's DEFECT — IT PINNED IT, AND THAT IS WHY THIS IS A
REWRITE RATHER THAN AN EXTENSION. Its G1-G3 re-implemented the geometry inside
the test (`def geo(w,d): return max(1,int(w//d))...`) and asserted against that
private copy, so they passed whether or not the repo computed anything at all.
Its G5 read main.py as SOURCE TEXT and asserted `"signal.contracts = _geo" in
b` — the presence of the exact assignment that wrote a field the order never
reads. It was green for two days while every ORB trade shipped one lot, and any
correct repair would have turned it red. WORKING_AGREEMENT §21: a test that
reads source and never executes proves nothing, and this one argued for the bug.

🔑 G5 IS THE ONLY CHECK THAT WOULD HAVE CAUGHT r181, and it is the reason this
file exists: it captures the quantity handed to `_place_single_leg` — the
argument that becomes the broker order — and asserts it equals the geometry.
Everything above it is arithmetic; only G5 is the claim.

Born red at r191 (4eaceb9): `size_for` does not exist there, and the ordered
quantity is the budget rule's answer regardless of geometry.

Run:  python3 tests/check_orb_geometry_size.py
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
    from risk.risk_manager import get_risk_manager
    rm = get_risk_manager()

    # ⚠️ DEGRADE TO A NAMED FAILURE, NEVER A TRACEBACK. Against a tree with no
    # single sizing door this whole file is inapplicable, and an AttributeError
    # would report "the checker crashed" where the truth is "the invariant is
    # violated". Same lesson as r191's C10.
    if not hasattr(rm, "size_for"):
        check("G0 RiskManager exposes the single sizing door `size_for`", False,
              "no size_for — sizing policy is still spread across the caller "
              "and two methods; every check below is unrunnable")
        print()
        print("FAILED 1: G0 (see above) — the rest cannot execute")
        return 1

    # ⚠️ r201 — AN EXPLICIT BUDGET, SO THESE MEASURE THE GEOMETRY. ORB is now
    # clamped by ORB_BUDGET_USD, default one trade's risk; without this every
    # case below would measure the sandbox's risk setting instead of the
    # arithmetic it exists to pin. Budget behaviour: tests/check_orb_budget.py.
    _BIG = 10_000_000.0

    def geo(w, d, premium=1.20, budget=_BIG):
        return rm.size_for("long_debit", premium=premium, budget_usd=budget,
                           orb_width=w, orb_stop_distance=d)

    # ── G1-G3: the rule itself, EXECUTED against the repo's own sizer ──────
    # The operator's two worked extremes, 2026-08-28: a shallow break near the
    # boundary carries little risk per contract and sizes up; a deep one sizes
    # down. Both risk about the same dollars at the structure stop.
    check("G1a shallow break 6.35 / 0.61 -> 10 lots", geo(6.35, 0.61).contracts == 10,
          f"got {geo(6.35, 0.61).contracts}")
    check("G1b deep break 6.35 / 6.05 -> 1 lot", geo(6.35, 6.05).contracts == 1)
    check("G2 worst entry (stop == width) -> exactly 1", geo(6.35, 6.35).contracts == 1)
    check("G3 degenerate geometry -> 1, never leveraged on bad arithmetic",
          geo(6.35, 0).contracts == 1 and geo(6.35, 7.0).contracts == 1
          and geo(0, 1).contracts == 1)
    check("G3b the rule identifies itself on the result",
          geo(6.35, 0.61).rule == "orb_geometry", geo(6.35, 0.61).rule)

    # ── G3c — SUPERSEDED AND REPLACED, NOT LOOSENED ───────────────────────
    # 🔴 This pinned the 2026-08-28 ruling that ORB had NO notional cap (C.24).
    # r201 REVERSES it after an SPX setup opened $34,750 of premium on 08-31 —
    # "we are going to rein that in" — so the old assertion now asserts the
    # opposite of the operator's position. Replaced rather than deleted,
    # because what is still worth pinning is that geometry answers to its OWN
    # budget and not to the risk-per-trade rule. Two different ceilings.
    _rich = rm.size_for("long_debit", premium=2.40, orb_width=6.35,
                        orb_stop_distance=0.61, budget_usd=5000)
    _by_risk = rm.size_for("long_debit", premium=2.40)
    check("G3c geometry answers to the ORB budget, not to the risk rule",
          _rich.allowed and _rich.contracts >= 1 and not _by_risk.allowed
          and _rich.rule == "orb_geometry",
          f"orb_budget=$5000 -> n={_rich.contracts} allowed={_rich.allowed}; "
          f"risk rule allowed={_by_risk.allowed}")

    # ── G4: everything else is untouched ──────────────────────────────────
    # A long_debit that supplies NO geometry takes the budget rule, and its
    # answer must be the budget rule's answer, not 1 and not a geometry count.
    _plain = rm.size_for("long_debit", premium=0.35)
    check("G4 a long_debit with no geometry keeps the budget rule",
          _plain.rule == "budget" and _plain.contracts == 5,
          f"rule={_plain.rule} n={_plain.contracts}")

    # ── G5: THE ORDERED QUANTITY. The whole point. ────────────────────────
    from execution import entry_engine as ee

    captured = {}

    class _Contract:
        symbol, strike, expiry, mark = "TEST  260830C00196000", 196.0, "2026-08-30", 1.20

    class _Sig:
        strategy_name = "ORBStrategy"
        setup_type = "ORB Long"
        direction = "long"
        option_side = "call"
        is_butterfly = False
        strike, expiry = 196.0, "2026-08-30"
        entry_premium = 1.20
        net_debit = 0.0
        contract = _Contract()
        underlying_entry, underlying_stop, underlying_target = 197.15, 195.89, 202.85
        orb_range_high, orb_range_low = 196.50, 190.15
        vix_at_signal = 15.0
        is_fed_day = False
        conviction = 0.0
        notes = ""
        setup_grade = "UNGRADED"

        def stop_premium(self):            return 0.90
        def trail_activation_premium(self): return 1.80
        def target_premium(self):          return 2.40

    def _spy(self, signal, contracts):
        captured["qty"] = contracts
        return None, "", 0          # book nothing; we only want the argument

    _real = ee.EntryEngine._place_single_leg
    _real_open = ee.entries_open
    try:
        ee.EntryEngine._place_single_leg = _spy
        ee.entries_open = lambda *a, **k: True
        sizing = rm.size_for("long_debit", premium=1.20, budget_usd=_BIG,
                             orb_width=6.35, orb_stop_distance=0.61)
        ee.EntryEngine(paper_trading=True).enter(signal=_Sig(), sizing=sizing)
    finally:
        ee.EntryEngine._place_single_leg = _real
        ee.entries_open = _real_open

    check("G5 THE ORDER RECEIVES THE GEOMETRY COUNT (10, not the budget's 1)",
          captured.get("qty") == 10,
          f"_place_single_leg was handed {captured.get('qty')!r}")

    # ── G6: the r181 override is GONE from the caller ─────────────────────
    # Shape of a DEFINITION, not a mention: main.py's v4.27 changelog names
    # `signal.contracts = _geo` while explaining its removal, so a bare string
    # match would go red on the documentation the rules require (WA §20).
    src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    check("G6 no sizing policy left in the caller — the assignment is deleted",
          "\n                signal.contracts = _geo" not in src
          and "_geo = max(1, int(_w // _d))" not in src)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_orb_geometry_size: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
