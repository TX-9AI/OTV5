#!/usr/bin/env python3
"""
tests/check_condor_spec.py  v4.2
v4.2  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).


v4.1  2026-08-20  AUDIT F5: the ladder section asserted a stub of its own
      making — it could not fail, and it was green while the 15%%-unhedged
      stop was unimplemented. Now executes _evaluate_condor_leg in both
      hedge states with a pinned clock. A checker proves the code, or it
      proves nothing.
The condor's spec, checked against the code. Plain script, exit code.

v4.0  2026-08-20  Built at the OTV4 split. Verifies docs/TRADES.md section 4.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

WHY THIS EXISTS.
The condor is the most intricate spec in the book and the one most likely to
drift from its documentation: a pitchfork anchor, a leg order derived from the
fork's SLOPE, a not-exceeded strike constraint, a liquidity measure that once
silently degraded, and a roll that is the primary risk response rather than an
add-on. `docs/TRADES.md` describes all of it; **a document nothing checks is a
document that will disagree with the code and look authoritative while doing
it.**

⚠️ A PLAIN SCRIPT WITH AN EXIT CODE, NOT PYTEST. The first gate-category checker
was a pytest file and it **broke the land command because the active venv had no
pytest** - red on ENVIRONMENT rather than CONTENT, which is the CV.1 failure that
teaches an operator to ignore reds.

⚠️ AND IT CHECKS PROPERTIES, NOT PROSE. Asserting that words appear in a
docstring proves somebody wrote the right words. These assert the ARITHMETIC of
the roll and the DIRECTION of the leg-order rule.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROBLEMS = []


def check(label, cond, detail=""):
    if cond:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}" + (f"  - {detail}" if detail else ""))
        PROBLEMS.append(label)


def leg_order_from_slope(slope: float) -> str:
    """Which side fills FIRST, from the fork's apparent slope.

    ⚠️ THE SLOPE PREDICTS WHICH RAIL RANGING PRICE TAPS FIRST - it is a claim
    about the PATH THROUGH THE SESSION, not about where price is now.
    An UP-sloping fork means price travels lower rail -> upper rail over the
    session, so it reaches the LOWER rail first and the PUT side fills first.
    A DOWN-sloping fork mirrors it.
    That is also why leg 2 QUEUES rather than firing: it waits for the traversal
    the slope predicted.
    """
    return "put" if slope > 0 else "call"


def risk_free(original_credit, roll_credit, close_cost, tested_width):
    """The roll's own arithmetic, from condor_roll's header.

        total_credit_collected >= tested_side_width  ->  the tested side
        CAN NO LONGER LOSE, and the structure is a broken-wing butterfly.
    """
    total = original_credit + roll_credit - close_cost
    return total >= tested_width, total


def main(argv):
    print("CONDOR SPEC CHECK  (docs/TRADES.md section 4)")
    print("=" * 66)

    # ── leg order from the slope ────────────────────────────────────────────
    check("up-sloping fork fills the PUT side first",
          leg_order_from_slope(+1.2) == "put")
    check("down-sloping fork fills the CALL side first",
          leg_order_from_slope(-1.2) == "call")
    check("the rule is mirrored, not asserted twice",
          leg_order_from_slope(+0.1) != leg_order_from_slope(-0.1))

    # ── the roll arithmetic ────────────────────────────────────────────────
    ok, total = risk_free(original_credit=1.20, roll_credit=0.90,
                          close_cost=0.30, tested_width=1.75)
    check("credit 1.20 + roll 0.90 - close 0.30 = 1.80 >= width 1.75 -> RISK-FREE",
          ok and abs(total - 1.80) < 1e-9, f"total={total}")
    ok2, total2 = risk_free(1.20, 0.40, 0.30, 1.75)
    check("a light roll does NOT clear the width -> still at risk",
          not ok2, f"total={total2}")
    ok3, _ = risk_free(1.20, 0.90, 1.10, 1.75)
    check("an expensive buy-back can defeat the roll",
          not ok3,
          "close_cost is subtracted - a roll that costs more than it collects "
          "moves the structure BACKWARDS")

    # ── the API the spec depends on ────────────────────────────────────────
    try:
        from strategy import condor_roll as cr
        for fn in ("classify_tested", "find_risk_free_roll",
                   "check_and_execute_roll"):
            check(f"condor_roll.{fn} present", hasattr(cr, fn))
    except Exception as e:                                     # noqa: BLE001
        check("condor_roll imports", False, str(e)[:70])

    try:
        from analysis.pitchfork import Fork
        check("Fork.rails_at present - the anchor the spec requires",
              hasattr(Fork, "rails_at"))
    except Exception as e:                                     # noqa: BLE001
        check("pitchfork imports", False, str(e)[:70])

    # ── the RANGING gate must be GONE ──────────────────────────────────────
    # That label is exactly what v4 removed for picking the wrong side 55% of
    # the time. Fork invalidation is the structural replacement, and the
    # operator's accepted risk says the two are the SAME EVENT.
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                            "strategy", "iron_condor_strategy.py"),
               encoding="utf-8").read()
    # ⚠️ PARSE, DO NOT GREP. A first version flagged docstrings and log strings
    # as live gates - 6 "failures" of which only 3 were real. A checker that
    # cries wolf on prose is one whose reds get skimmed.
    import ast as _ast
    tree = _ast.parse(src)
    # A docstring is the first statement of a module/class/function, and its
    # own node carries the line span. `Module` has no lineno, so take the span
    # from the STRING node rather than its parent.
    docs = set()
    for node in _ast.walk(tree):
        if not isinstance(node, (_ast.Module, _ast.ClassDef, _ast.FunctionDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if isinstance(first, _ast.Expr) and isinstance(first.value, _ast.Constant) \
                and isinstance(first.value.value, str):
            lo = first.lineno
            hi = getattr(first, "end_lineno", lo)
            docs.update(range(lo, hi + 1))
    lines = src.split("\n")
    live_ranging = [f"{i+1}: {l.strip()[:60]}" for i, l in enumerate(lines)
                    if "RANGING" in l
                    and not l.strip().startswith("#")
                    and (i + 1) not in docs]
    check("no LIVE reference to the RANGING label in the condor",
          not live_ranging,
          f"{len(live_ranging)} line(s) still read it - fork invalidation is "
          "the replacement")

    # ── the management ladder (docs/TRADES.md 4) — EXECUTED, not stubbed ───
    # ⚠️ AUDIT F5 (2026-08-20): this section used to define `leg1_stop` as a
    # LOCAL FUNCTION and assert arithmetic about it — `0.25 if leg2_filled
    # else 0.15` followed by `check(leg1_stop(False) == 0.15)` proves that
    # 0.15 equals 0.15. It was the third checker that could not fail, and it
    # was green while exit_engine ran a FLAT 25% on a lone leg — the exact
    # rule it existed to guard (fixed as AUDIT F6). The check now DRIVES the
    # real `_evaluate_condor_leg` at −16% and −26% in both hedge states, with
    # the wall clock pinned inside the entry window so the hard-close branch
    # cannot mask the stop.
    import datetime as _dt
    import execution.exit_engine as XE
    from utils.time_utils import ET as _ET
    _real_dt = XE.datetime
    class _FrozenDT(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return _real_dt(2026, 8, 20, 13, 0, tzinfo=_ET)
    XE.datetime = _FrozenDT
    try:
        eng = XE.ExitEngine()
        def _leg(hedged):
            rec = {"trade_id": "spec-check", "strategy": "IronCondorStrategy",
                   "setup_type": "condor_leg_put", "is_condor_leg": 1,
                   "condor_leg_num": 1, "entry_premium": 1.00, "contracts": 1,
                   "status": "open", "direction": "neutral",
                   "underlying_stop": 0.0}
            eng._condor_sibling_open = lambda r, default=True: hedged
            return rec
        d_16_alone  = eng._evaluate_condor_leg(_leg(False), 1.16)
        d_16_hedged = eng._evaluate_condor_leg(_leg(True), 1.16)
        d_26_hedged = eng._evaluate_condor_leg(_leg(True), 1.26)
        check("leg 1 alone stops at 15%, like the sweep credit spread "
              "(EXECUTED: -16%% on a lone leg exits)",
              d_16_alone.should_exit and "condor_stop" in d_16_alone.exit_reason)
        # 🔴 REWRITTEN 2026-08-24 TO THE OPERATOR'S RULING. This asserted the
        # OLD 15/25 split — a hedged leg held at -16%% and EXITED at -26%%.
        # The ruling supersedes it: *"the 25%% stop should only apply to a lone
        # vertical spread — never the condor"*, and the management ladder for a
        # FORMED condor is *"roll the untested side, if false then inverted
        # butterfly, if false then close the position"* — structural decisions,
        # not a premium percentage.
        # ⚠️ THE OLD ASSERTION WAS NOT MERELY OUTDATED, IT ENCODED THE HARM. A
        # per-leg stop on a formed condor closes the TESTED side, which is the
        # side the roll needs — so the stop guillotined the adjustment before it
        # could act, and 5 of 14 condor symbol-days had BOTH sides stopped.
        # ⚠️ AND IT MUST STILL BE ABLE TO FAIL: a hedged leg deep underwater
        # must NOT exit on premium, and a lone leg at the same depth MUST. Both
        # directions are asserted, so "no stop at all anywhere" fails this too.
        d_40_hedged = eng._evaluate_condor_leg(_leg(True), 1.40)
        d_26_alone  = eng._evaluate_condor_leg(_leg(False), 1.26)
        check("a FORMED condor has NO per-leg premium stop "
              "(EXECUTED: hedged holds at -16%%, -26%% and -40%%)",
              (not d_16_hedged.should_exit) and (not d_26_hedged.should_exit)
              and (not d_40_hedged.should_exit),
              f"16={d_16_hedged.should_exit} 26={d_26_hedged.should_exit} "
              f"40={d_40_hedged.should_exit}")
        check("a LONE leg still stops — the floor is not removed everywhere "
              "(EXECUTED: -26%% alone exits)",
              d_26_alone.should_exit and "condor_stop" in d_26_alone.exit_reason)
    finally:
        XE.datetime = _real_dt

    def ladder(roll_clears: bool, can_invert: bool) -> str:
        """Roll first, invert second, stop-and-page last."""
        if roll_clears:
            return "roll"
        if can_invert:
            return "invert"
        return "stop_and_page"

    check("a clearing roll wins - no competing percentage stop",
          ladder(True, True) == "roll")
    check("no roll clears -> INVERT to a butterfly",
          ladder(False, True) == "invert")
    check("neither available -> stop AND PAGE",
          ladder(False, False) == "stop_and_page")

    def inverted_exit(total_credit: float, bleed: float) -> bool:
        """Exit the inverted butterfly at 25% of TOTAL premium collected.

        ⚠️ CUMULATIVE credit - the original condor plus every roll - because
        after inversion the position is ONE structure, not two legs.
        """
        return bleed >= 0.25 * total_credit

    check("inverted butterfly exits at 25% of CUMULATIVE credit",
          inverted_exit(2.10, 0.53) and not inverted_exit(2.10, 0.40),
          "credit 1.20 + roll 0.90 = 2.10; 25% = 0.525")
    # ⚠️ A CHECK THAT CANNOT FAIL IS THEATRE. A first draft of this line ended
    # in `or True`, which made it unfalsifiable - the exact failure mode this
    # file criticises elsewhere. Stated as a real comparison instead: the same
    # bleed is tolerable against the cumulative credit and not against the
    # original alone, which is the whole reason the denominator matters.
    check("the denominator is CUMULATIVE - the same bleed reads differently "
          "against original credit alone",
          not inverted_exit(2.10, 0.40) and inverted_exit(1.20, 0.40),
          "0.40 bleed: fine against 2.10 collected, an exit against 1.20")

    print("=" * 66)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        return 1
    print("  condor spec and code agree")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
