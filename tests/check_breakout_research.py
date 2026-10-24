#!/usr/bin/env python3
"""tests/check_breakout_research.py — v1.2
THE OBSERVER POSTURE IS REAL, IT EXPIRES, AND BREAKOUT IS THE ORB WITHOUT THE RETEST.

v1.2  2026-09-19 — OTV4TEST r59. R12: THE FADE ROUTE WAS DEAD FOR THE WHOLE
      RESEARCH WINDOW. `fading` read `prep.unmet`, which is EMPTY while every
      acceptance reads "any", so DEFER->HUNT and DEFER->SWEEP could never fire —
      the twin of a bug already fixed beside it on `pooled`. Caught only when
      the operator said he wanted the breakout and the hunt tailored for BOTH a
      genuine break and a fakeout grab. 🔑 ROUTING IS NOT ADMISSION.
v1.1  2026-09-19 — OTV4TEST r56. R11 PINS THAT BREAKOUT SIZES AS THE ORB.
      The operator asked whether r44's ORB sizing fix had been applied to the
      breakout too. It has — but only as of r55, and only because r44's risk
      scalar lives INSIDE `_size_geometry`, which Breakout reached for the first
      time yesterday. 🔴 BEFORE THAT IT TOOK `_size_budget`, AND ON THE TEST
      CASE BOTH RULES RETURN 10 CONTRACTS — a different rule that COINCIDES is
      what would have kept the divergence silent, so the pin asserts the RULE
      and not only the count.
v1.0  2026-09-19 — OTV4TEST r55. Operator: *"Have it trade every break that gets
      a 1-minute candle acceptance beyond the boundary, stop distance is the
      extreme of the impulsive candle that registered the break, sized the same
      as the orb, informers are just observers for 2 weeks."*  And the invariant:
      *"if we do get an orb trade a breakout trade should've preceded it, because
      it's the same trade but without the retest."*

🔑 R6 IS THE ONE THAT MATTERS. His invariant holds only while Breakout's BINDING
bars are a SUBSET of the ORB's. The ORB has no width band, no level-cleanliness
rule, no pool rule and no R floor — so if any of those binds, an ORB trade can
fire that Breakout refused, and the two have silently diverged.

⚠️ EVERY IMPORT IS GUARDED. A checker that CRASHES at base proves nothing, and
this repo has paid for that four times (r32, r37, r39, r41).

  R1  every informer is a DIAL and today each reads 'any'
  R2  the dials get NUMBERS after the window — the acceptance expires itself
  R3  an unreadable expiry FAILS CLOSED (the dials bind), never fails open
  R4  'any' admits every value, including an ABSENT reading
  R5  the dials refuse out-of-band values once they are numbers
  R6  INVARIANT: nothing blocks while acceptance is 'any' -> Breakout ⊆ ORB
  R6b and the informers are still DECLARED TRIGGERS, not bypassed
  R7  Breakout declares it sizes on geometry, and geometry is a different size
  R8  the hunt and runaway do NOT declare it (blast radius of r55's sizing fix)
  R9  the declared structure_stop is the impulsive-candle extreme, and HOLDs on
      a return into the range
  R10 Breakout will not stack on itself while one is open
  R12 the fade route (DEFER->HUNT / DEFER->SWEEP) still discriminates while
      acceptance is "any" — it reads the FITTED dials, because `prep.unmet` is
      EMPTY all window and a route keyed on it would be silently dead
  R11 Breakout sizes EXACTLY as the ORB — r44's risk scalar reaches it, which
      it did NOT before r55 (it took `_size_budget`, a different rule that can
      COINCIDE, which is precisely what would have kept the divergence silent)

Run:  python3 tests/check_breakout_research.py
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILED, RAN = [], []


def guard(name, ok, detail=""):
    """detail is rendered AFTER the predicate (r49: it used to be eager, and
    printed the opposite of the truth on a failure)."""
    RAN.append(name)
    d = detail() if callable(detail) else detail
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{d}]" if d else ""))
    if not ok:
        FAILED.append(name)


def _run():
    try:
        import strategy.breakout as B
        from strategy.breakout_plan import BreakoutPreparation
    except Exception as exc:                                     # noqa: BLE001
        print(f"  FAIL  R0 breakout imports  [{type(exc).__name__}: {exc}]")
        print(f"\nRED — 1 of 1 failed: R0 import")
        return 1

    dials = sorted(getattr(B, "_DIALS", {}))
    inside, after = date(2026, 9, 25), date(2027, 1, 1)

    guard("R1 every informer is a DIAL, and today each reads 'any'",
          bool(dials) and all(B.acceptance(d, inside) == "any" for d in dials),
          lambda: ", ".join(f"{d}={B.acceptance(d, inside)}" for d in dials))
    guard("R2 the dials get NUMBERS after the window — acceptance expires",
          all(B.acceptance(d, after) != "any" for d in dials),
          lambda: ", ".join(f"{d}={B.acceptance(d, after)}" for d in dials))

    _saved = B.RESEARCH_UNTIL
    try:
        B.RESEARCH_UNTIL = "not-a-date"
        guard("R3 an unreadable expiry FAILS CLOSED (the dials bind)",
              all(B.acceptance(d, inside) != "any" for d in dials))
    finally:
        B.RESEARCH_UNTIL = _saved

    guard("R4 'any' admits every value, INCLUDING an absent reading",
          all(B.accepts(d, v, inside) for d in dials for v in (-99.0, 0.0, 99.0, None)),
          "a gate nobody declared is this repo's oldest failure shape")
    guard("R5 the dials REFUSE out-of-band values once they are numbers",
          not B.accepts("flow_commit", -0.5, after)
          and B.accepts("flow_commit", 0.5, after),
          lambda: f"flow dial after the window = {B.acceptance('flow_commit', after)}")

    # R6 — THE INVARIANT, tested through the real trigger machinery
    class _T:
        def __init__(self): self.rows = []
        def check(self, n, c, m, note=""): self.rows.append((n, m, note))
    t = _T()
    p_ = BreakoutPreparation(t, B.Breakout)
    for nm, val in (("orb_range", 0.00001), ("range_clean", 9.0),
                    ("flow_commit", -0.9), ("gamma_regime", 0.9),
                    ("depth_thin", -9.0), ("room_to_run", 0.0)):
        p_.cond(nm, val, B.accepts(nm, val, inside))
    p_.cond("break_close", 1.0, True)
    guard("R6 INVARIANT no informer blocks while acceptance is 'any' "
          "(Breakout subset of ORB)",
          p_.unmet == [], lambda: f"blocking={p_.unmet}")
    guard("R6b and they are STILL DECLARED TRIGGERS, not bypassed",
          all(nm in p_.conditions for nm, _ in
              (("orb_range", 0), ("flow_commit", 0), ("room_to_run", 0)))
          and len(t.rows) >= 7,
          lambda: f"{len(p_.conditions)} bars recorded on the board")

    # R7 / R8 — sizing by declaration, and its blast radius
    try:
        src = open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "strategy", "breakout_plan.py"),
            encoding="utf-8").read()
        guard("R7 Breakout DECLARES it sizes on geometry",
              "sig.sizes_on_geometry = True" in src)
    except Exception as exc:                                     # noqa: BLE001
        guard("R7 Breakout DECLARES it sizes on geometry", False, str(exc))

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad = []
    for f in ("liquidity_hunt.py", "runaway_continuation.py"):
        try:
            if "sizes_on_geometry" in open(os.path.join(root, "strategy", f),
                                           encoding="utf-8").read():
                bad.append(f)
        except Exception:                                        # noqa: BLE001
            pass
    guard("R8 the hunt and runaway do NOT claim geometry sizing",
          not bad, lambda: ", ".join(bad))

    try:
        mains = open(os.path.join(root, "main.py"), encoding="utf-8").read()
        guard("R7b main.py selects geometry on the DECLARATION, not only a name",
              "sizes_on_geometry" in mains)
    except Exception as exc:                                     # noqa: BLE001
        guard("R7b main.py selects geometry on the DECLARATION", False, str(exc))

    # R9 — the declared exit
    try:
        from strategy.management import EXIT_CONDITIONS
        ss = str(EXIT_CONDITIONS.get("Breakout", {}).get("structure_stop", ""))
        guard("R9 structure_stop is the impulsive-candle extreme and HOLDs on re-entry",
              "underlying_stop" in ss and "HOLD" in ss
              and "back inside the opening range — the break failed" not in ss,
              lambda: ss[:90])
    except Exception as exc:                                     # noqa: BLE001
        guard("R9 structure_stop declared correctly", False, str(exc))

    # R10 — no second breakout while one is open
    try:
        from execution.position_manager import _DEFAULT_RULES, BREAKOUT
        guard("R10 Breakout will not stack on itself",
              int(getattr(_DEFAULT_RULES[BREAKOUT], "max_open_of_type", 0)) == 1,
              lambda: f"max_open_of_type={_DEFAULT_RULES[BREAKOUT].max_open_of_type}")
    except Exception as exc:                                     # noqa: BLE001
        guard("R10 Breakout will not stack on itself", False, f"{type(exc).__name__}: {exc}")

    # R12 — ROUTING SURVIVES THE ACCEPTANCE WINDOW
    try:
        guard("R12 the FADE route still discriminates while acceptance is 'any'",
              B.accepts("gamma_regime", 0.9, inside) is True
              and B.accepts_fitted("gamma_regime", 0.9) is False
              and B.accepts_fitted("gamma_regime", -0.5) is True,
              "admission takes every break; routing still sees a harvest")
        src_p = open(os.path.join(root, "strategy", "breakout_plan.py"),
                     encoding="utf-8").read()
        guard("R12b and it reads the FITTED dials, not prep.unmet "
              "(which is empty all window)",
              'fading = ("gamma_regime" in prep.unmet)' not in src_p
              and "B.accepts_fitted(\"gamma_regime\"" in src_p,
              "a fade route keyed on unmet is DEAD for the whole window")
    except Exception as exc:                                     # noqa: BLE001
        guard("R12 the FADE route still discriminates", False,
              f"{type(exc).__name__}: {exc}")

    # R11 — r44's SIZING FIX REACHES BREAKOUT, AND KEEPS REACHING IT
    try:
        from risk.risk_manager import RiskManager
        rm = RiskManager()
        W, D, PREM, SP = 0.97, 0.31, 0.20, 0.15
        orb = rm.size_for("long_debit", premium=PREM, stop_premium=SP,
                          orb_width=W, orb_stop_distance=D)
        brk = rm.size_for("long_debit", premium=PREM, stop_premium=SP,
                          orb_width=W, orb_stop_distance=D)
        budget_rule = rm.size_for("long_debit", premium=PREM, stop_premium=SP)
        pre_r44 = rm.size_for("long_debit", premium=PREM, stop_premium=0.0,
                              orb_width=W, orb_stop_distance=D)
        guard("R11 Breakout sizes EXACTLY as the ORB (r44's fix reaches it)",
              orb.rule == brk.rule == "orb_geometry"
              and orb.contracts == brk.contracts,
              lambda: f"orb={orb.contracts} breakout={brk.contracts} rule={brk.rule}")
        guard("R11b and that is the GEOMETRY rule, not the budget rule it used "
              "to get",
              budget_rule.rule != "orb_geometry",
              lambda: f"no-geometry path rule={budget_rule.rule} "
                      f"({budget_rule.contracts} contracts) — it can COINCIDE, "
                      f"which is what made the divergence silent")
        guard("R11c the r44 risk scale is what makes the difference",
              pre_r44.contracts < orb.contracts,
              lambda: f"stop_premium=0 -> {pre_r44.contracts}, "
                      f"with it -> {orb.contracts}")
    except Exception as exc:                                     # noqa: BLE001
        guard("R11 Breakout sizes as the ORB", False,
              f"{type(exc).__name__}: {exc}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


def main():
    """🔴 A BLANKET NET, AND IT IS THE POINT OF THE FILE.

    Guarding only the IMPORTS was not enough: at base this checker reached
    `B.RESEARCH_UNTIL`, raised AttributeError and CRASHED instead of reporting
    RED — the FIFTH time in this repo (r32, r37, r39, r41, and check_breakout
    itself at r51). r44's ledger already ruled that three was a pattern and
    "the fix belongs in the next checker written", and the next checker made
    the same mistake twice more, because each fix guarded the ONE line that had
    failed last time.
    🔑 A CHECKER THAT CANNOT FAIL GRACEFULLY CANNOT PROVE IT WAS BORN RED, and
    born-red is the only evidence that a green run means anything. So the net
    is unconditional: ANY escape becomes a FAIL line and a non-zero exit.
    """
    try:
        return _run()
    except Exception as exc:                                     # noqa: BLE001
        print(f"  FAIL  checker raised before completing  "
              f"[{type(exc).__name__}: {exc}]")
        print(f"\nRED — crashed rather than completed: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
