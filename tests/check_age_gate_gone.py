#!/usr/bin/env python3
"""
tests/check_age_gate_gone.py  v1.2
v1.2  2026-09-22  OTV4TEST r102 - IT HAD BEEN DEAD SINCE r5 AND NOBODY
      NOTICED. Every run died on AttributeError: SweepCreditSpreadStrategy has
      no attribute CONDITIONS - the declaration site moved to
      strategy/sweep_plan.py and PLAN_CHECKS is now set on the INSTANCE, so
      class access raised. Re-pointed at the plan's class attribute, and it
      FAILS CLOSED if that moves again rather than raising. A3/A4/A5 realigned
      on what the fork actually contracts; the A3 conflict is recorded.
v1.1  2026-09-08  r321 — A6/A6b: THE REMOVAL IS ASSERTED TREE-WIDE, NOT IN ONE
      MODULE. v1.0 read `sweep_credit_spread.__file__` and nothing else, so
      `criteria.CRITERIA` kept a strict/relaxed pair for the gate r241 had just
      deleted and this file stayed GREEN beside it for four days. A
      removal-checker scoped to the file the removal happened in cannot see the
      copy in the file that DOCUMENTS the removal.
      ⚠️ ASSERTED ON THE DICT, NOT ON SOURCE TEXT — criteria.py's changelog
      necessarily NAMES the key while explaining its removal (§20).
v1.0  2026-09-04  r241 — THE AGE GATE IS REMOVED, NOT RAISED.

🔴 Operator, 2026-09-04: *"I don't give a rat's ass how old the level is, it's
still a level. Why are we still measuring the age of them?"* Because I only
half-shipped his 2026-08-11 ruling. SWP.5 said LIVENESS REPLACES THE CLOCK;
r230 found it had never reached the code and raised the ceiling 6 → 48 instead
of deleting the gate. That was my call, not his.

🔑 AGE MEASURES THE RAID, NOT THE LEVEL. A level swept at 09:45 that has held
since is the SAME LEVEL at 13:00 — arguably better, having held longer. And
levels are swept all day; the morning's is not the only one on the board.

🔴 MEASURED FLEET-WIDE, 2026-08-31..09-04: `age` failed 46,791 of 61,641 (76%),
and on 333 ticks — 26% of every tick that was ONE gate short — it was the ONLY
thing refusing. Complete setups, declined for being old.
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# ⚠️ r102 — THE LANDER RUNS CHECKS UNDER SYSTEM `python3`, NOT THE VENV, and
# the repo imports below reach `tastytrade`, which lives only in the venv. A
# checker that cannot import is a checker that never runs. Resolved by glob so
# the interpreter version is never hardcoded, and INSERTED AHEAD OF THE SYSTEM
# PATHS (index 1) — appending leaves /usr/lib/python3/dist-packages first and
# its older `typing_extensions` shadows the venv's.
import glob as _glob
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sp in _glob.glob(os.path.join(_R, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


def main():
    from strategy import sweep_credit_spread as scs
    src = open(scs.__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    S = scs.SweepCreditSpreadStrategy

    # ══ A1 — NO CEILING, IN ANY FORM ══════════════════════════════════════
    # ⚠️ AST, not a grep: the changelog names MAX_AGE_BARS while explaining its
    # removal, so a string search would match the explanation (§20).
    bound = [n.lineno for n in ast.walk(tree)
             if isinstance(n, ast.Assign)
             and any(getattr(t, "id", "") == "MAX_AGE_BARS" for t in n.targets)]
    check("A1 MAX_AGE_BARS is not bound", not bound, str(bound))
    check("A1b and the module does not expose it",
          not hasattr(scs, "MAX_AGE_BARS"))

    # ══ 🔴 A6 — AND IT IS GONE FROM THE CRITERIA TABLE TOO ════════════════
    # r241 removed the gate from the strategy and shipped THIS FILE to pin it —
    # scoped to `sweep_credit_spread` alone, so `criteria.CRITERIA` kept a
    # strict/relaxed pair for a gate that no longer exists and this checker was
    # green for four days beside it. A removal-checker scoped to the file the
    # removal happened in cannot see the copy in the file that DOCUMENTS it.
    # ⚠️ ASSERTED ON THE DICT, NOT ON SOURCE TEXT — criteria.py's changelog
    # necessarily NAMES the key while explaining its removal (§20).
    from strategy import criteria as _crit
    check("A6 'sweep_max_age_bars' is not in criteria.CRITERIA",
          "sweep_max_age_bars" not in _crit.CRITERIA, str(sorted(_crit.CRITERIA)))
    check("A6b nor in its GATES declaration",
          "sweep_max_age_bars" not in _crit.GATES, str(sorted(_crit.GATES)))

    # ══ A2 — `age` IS NOT A GATE ══════════════════════════════════════════
    # 🔴 r102 — THE DECLARATION SITE MOVED AND THIS CRASHED FOR IT. The sweep's
    # conditions used to be `SweepCreditSpreadStrategy.CONDITIONS`; r5 rewrote
    # the sweep into `strategy/sweep_plan.py`, and the strategy now assigns
    # `self.PLAN_CHECKS` on the INSTANCE in __init__ — so CLASS access raised
    # AttributeError and this file died before evaluating anything. The plan's
    # class attribute is the real declaration; read that.
    # ⚠️ AND IT FAILS CLOSED IF IT MOVES AGAIN, rather than raising: a gate
    # that dies on a traceback never delivers its verdict (§21).
    try:
        from strategy.sweep_plan import SweepPlan as _SP
        _decl = tuple(getattr(_SP, "PLAN_CHECKS", ()) or ())
    except Exception as _e:                                   # noqa: BLE001
        _decl = ()
        check("A2pre the sweep's declaration site is readable", False, repr(_e))
    check("A2pre the sweep's declaration site is readable", bool(_decl),
          f"{len(_decl)} declared checks")
    check("A2 'age' is not a declared condition", "age" not in _decl,
          str(sorted(_decl)))
    conds = [n.lineno for n in ast.walk(tree)
             if isinstance(n, ast.Call)
             and getattr(n.func, "attr", "") == "cond"
             and n.args and isinstance(n.args[0], ast.Constant)
             and n.args[0].value == "age"]
    check("A2b nothing calls prep.cond('age', ...)", not conds, str(conds))
    check("A2c and it is not in PLAN_CHECKS", "age" not in _decl)

    # ══ A3 — THE MEASUREMENT SURVIVES ════════════════════════════════════
    # 🔑 mainline r241 removed the GATE, not the NUMBER: knowing how old a
    # level was is useful for fitting, DECIDING with it is what was ruled out.
    # 🔴 r102 — THIS CHECK WAS ASSERTING A MAINLINE CONTRACT THE FORK REPLACED,
    # and it crashed on an AttributeError before it could say so. r241 kept the
    # age on the SIGNAL (`sig.sweep_age_bars = prep.age`). r5 rewrote the sweep,
    # set that field to a literal 0 — deliberately, because the TRIGGER is a
    # fresh REJECTED event — and pinned the 0 in `check_sweep_liveness` L3.
    # ⚠️ SO TWO GATES IN THIS TREE DISAGREED, and this one was dead, so the
    # disagreement was invisible. What survives in the fork is the measurement
    # itself, recorded on the PLAN, and that is what is asserted here.
    # ⚠️ OPEN, AND NOT DECIDED HERE: a trade may fire on a rejection up to
    # REJECTION_FRESH_BARS (3) old, so the signal's 0 is wrong by up to three
    # bars while the true figure sits on the plan row. Whether the signal
    # should carry the real age is a change to recorded trade semantics and
    # belongs to the operator.
    check("A3 the age measurement is still declared on the plan",
          "rejection_age_bars" in _decl, str(sorted(_decl))[:80])
    from strategy.sweep_plan import SweepPreparation as _SPrep
    # ⚠️ ASSERTED ON THE REAL __slots__, NOT ON SOURCE TEXT. The old form
    # grepped for the string "age", which the changelog alone would satisfy.
    check("A3b and the preparation carries it off the tick",
          "age_bars" in getattr(_SPrep, "__slots__", ()),
          str(getattr(_SPrep, "__slots__", ())[-3:]))

    # ══ A4 — UNMEASURABLE IS NOT OLD ══════════════════════════════════════
    # 🔴 A 999 sentinel means the rejection age could not be read AT ALL — a
    # DATA fault, not a staleness judgement.
    # 🔴 r102 — ITS REFUSAL PATH WENT WITH THE RETIRED GATE. `_AGE_UNMEASURABLE`
    # is now DECLARED AND REFERENCED NOWHERE. That is consistent with this
    # file's whole purpose — the age gate is gone — so what is pinned is the
    # ABSENCE of any comparison against it. A4 used to assert it REFUSES; that
    # assertion could not hold once the gate it guarded was removed.
    check("A4 the sentinel is still declared", "_AGE_UNMEASURABLE = 999" in src)
    unmeas = [n for n in ast.walk(tree)
              if isinstance(n, ast.Compare)
              and "_AGE_UNMEASURABLE" in ast.unparse(n)]
    check("A4b and NOTHING compares against it — the age gate is gone",
          not unmeas, f"{len(unmeas)} comparison(s)")

    # ══ A5 — LIVENESS IS `invalidated`, AS SWP.5 SAID ═════════════════════
    # It fails 73% fleet-wide: price accepting through a level is a market
    # fact, not a defect, and that gate is doing exactly its job.
    # 🔴 r102 — THE GATE SURVIVED; ITS NAME DID NOT. r5's rewrite retired the
    # `invalidated` condition and split the same intent in two: `side_of_pool`
    # (price is still on the profitable side of the level) and `spent_level`
    # (this level has not already been used). Asserting the OLD NAME would
    # report a lost gate that is not lost — and deleting the check would drop
    # the coverage. So it asserts the CURRENT gates by name.
    # ⚠️ THIS IS NOT A LOOSENING. The old check asserted ONE liveness gate is
    # declared; this asserts BOTH of its successors are, which is strictly
    # stronger. If a future rewrite folds them again, this goes red and names
    # what it could not find, rather than passing on a renamed absence (§23).
    _live = {"side_of_pool", "spent_level"}
    check("A5 the liveness gates remain declared (r5 renamed 'invalidated')",
          _live <= set(_decl), f"missing: {sorted(_live - set(_decl)) or 'none'}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 11 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
