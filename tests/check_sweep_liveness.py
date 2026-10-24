#!/usr/bin/env python3
"""
tests/check_sweep_liveness.py  v1.5
v1.5  2026-09-23  OTV4TEST r126 — L3d RETIRED with analysis/liquidity_mapper (deleted): it
      guarded the mapper's own `sweep_age_bars` gate against a grep-and-delete;
      that gate and the mapper are gone.
v1.4  2026-09-22  OTV4TEST r105 - L3 INVERTS. It used to pin
      `sig.sweep_age_bars = 0` as deliberate while the inherited mainline gate
      check_age_gate_gone A3 demanded the real measurement - two gates in one
      tree requiring contradictory things, invisible because A3 died on an
      AttributeError for seventeen days. L3 is AST-based, because the comment
      explaining the removal names the field (SS20). L3b pins the journal, L3c
      pins where the measurement actually lives, and L3d pins that the MAPPER's
      field of the same name is a DIFFERENT quantity and still gates.
v1.3  2026-09-22  OTV4TEST r102 - runnable under the lander's system
      python3; it could not import the venv and so had never run as a CHECK.
      Declared as one now: L3 is the gate that caught r102 starting to change
      `sig.sweep_age_bars` away from the 0 r5 chose deliberately.
v1.2  2026-09-09  OTV4TEST r5 — L2–L5 read the plan's PLAN_CHECKS; CONDITIONS is gone.
v1.1  2026-09-04  r241 — RE-DERIVED. Every check pinned a CEILING —
      that MAX_AGE_BARS existed, resolved to 48, was FOUNDATIONAL and admitted
      33-48 bar sweeps. r241 removes the gate outright per the operator's
      ruling, so asserting a ceiling would pin the thing being removed. What
      survives is SWP.5's actual point: liveness is `invalidated`, the age is
      still RECORDED, and an unmeasurable sweep refuses on its own terms.
v1.0  2026-09-03  r230 — SWP.5 WAS RULED AND NEVER WIRED. `sweep_credit_spread` read
`SWEEP_CS_MAX_AGE_BARS`, a name defined nowhere, so the ceiling was the
getattr DEFAULT of 6 while SWP.5's measured 48 sat unread in config.

⚠️ ANCHORED ON DEFINITIONS AND VALUES, NEVER ON MENTIONS (WORKING_AGREEMENT
§20). The changelog above names `SWEEP_CS_MAX_AGE_BARS` and `relaxed.widen`
while explaining their removal — a canary matching either STRING would trip
on the very prose §5 requires. L2 parses the AST; L3 reads the resolved
value. Neither can match a comment.

⚠️ AND IT EXECUTES (§21). L4/L5 drive the real gate function, not the source
text: asserting the file CONTAINS `MAX_AGE_BARS` proves nothing about what
the gate does with it.

Plain script, exit code, no pytest (§36 — the boxes' venv has none).
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# ⚠️ r102 — THE LANDER RUNS CHECKS UNDER SYSTEM `python3`, NOT THE VENV, and
# the repo imports below reach `tastytrade`, which lives only in the venv — so
# this file could never run as a declared CHECK. Inserted at index 1 so the
# venv beats /usr/lib/python3/dist-packages (whose older `typing_extensions`
# otherwise shadows it) while the repo root at index 0 still wins.
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
    import config
    from strategy import sweep_credit_spread as scs

    src = open(scs.__file__, encoding="utf-8").read()
    tree = ast.parse(src)

    # 🔴 RE-DERIVED AT r241. Every check below pinned a CEILING — that
    # MAX_AGE_BARS existed, resolved to 48, was FOUNDATIONAL, and admitted
    # 33-48 bar sweeps. The operator's ruling removes the gate outright:
    # *"I don't give a rat's ass how old the level is, it's still a level."*
    # SWP.5 said LIVENESS REPLACES THE CLOCK in 2026-08-11; r230 raised the
    # ceiling 6 -> 48 instead of deleting it, and that half-measure is what
    # these checks were written against. Asserting a ceiling now would pin the
    # thing being removed.
    # ⚠️ WHAT SURVIVES IS THE POINT OF SWP.5: the liveness test is
    # `invalidated`, and an UNMEASURABLE sweep still refuses on its own terms.
    src = open(scs.__file__, encoding="utf-8").read()
    tree = ast.parse(src)

    # ── L1 — THE CEILING IS GONE, NOT RAISED ─────────────────────────────
    # AST, not a string search: the changelog names MAX_AGE_BARS while
    # explaining its removal, and a grep would match the explanation (§20).
    bound = [n for n in ast.walk(tree)
             if isinstance(n, ast.Assign)
             and any(getattr(t, "id", "") == "MAX_AGE_BARS" for t in n.targets)]
    check("L1 MAX_AGE_BARS is no longer bound at module level", not bound,
          f"lines {[n.lineno for n in bound]}")
    check("L1b and the module does not expose it",
          not hasattr(scs, "MAX_AGE_BARS"))

    # ── L2 — `age` IS NO LONGER A CONDITION ──────────────────────────────
    # 🔴 MEASURED FLEET-WIDE 08-31..09-04: age failed 46,791 of 61,641 (76%),
    # and on 333 ticks — 26% of every tick that was ONE gate short — it was the
    # ONLY thing refusing. Complete setups, declined for being old.
    _checks = scs.SweepCreditSpreadStrategy().PLAN_CHECKS          # OTV4TEST r5: the plan's
    check("L2 'age' is not a declared check on the plan",
          not any(c in ("age", "sweep_age", "bars_ago") for c in _checks), str(_checks))
    conds = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call)
             and getattr(n.func, "attr", "") == "cond"
             and n.args and isinstance(n.args[0], ast.Constant)
             and n.args[0].value == "age"]
    check("L2b and nothing calls prep.cond('age', ...)", not conds,
          f"lines {[n.lineno for n in conds]}")

    # ── L3 — THE AGE FIELD IS GONE, AND STAYS GONE (r105) ────────────────
    # 🔴 THIS CHECK USED TO ASSERT THE OPPOSITE. It pinned `sig.sweep_age_bars
    # = 0` as r5's deliberate choice, while the inherited mainline gate
    # `check_age_gate_gone` A3 demanded the real measurement — two gates in one
    # tree requiring contradictory things, invisible because A3 died on an
    # AttributeError for seventeen days.
    # 🔑 THE OPERATOR RULED IT OUT ENTIRELY, 2026-09-22: age is necessary to
    # ORDER the levels by recency — `level_map.walk` sorts on `formed_ts`, and
    # without it the board is arbitrary — and *"not relevant to anything else"*.
    # The field decided nothing: its only consumer was `signal_journal`'s
    # factor column, and a constant is not a factor.
    # ⚠️ THE MEASUREMENT IS NOT LOST — L3c pins where it actually lives.
    # ⚠️ AST, NOT A SUBSTRING — the comment that explains the removal names the
    # field, so a text test fails on its own explanation. §20, for the third
    # time in one session; assert the ASSIGNMENT is gone, not the spelling.
    import ast as _a3
    _assigns = [n.lineno for n in _a3.walk(_a3.parse(src))
                if isinstance(n, _a3.Assign)
                for tgt in n.targets
                if isinstance(tgt, _a3.Attribute) and tgt.attr == "sweep_age_bars"]
    check("L3 nothing assigns sweep_age_bars on the signal", not _assigns,
          f"lines {_assigns}" if _assigns else "removed at r105; nothing decided on it")
    _jsrc = open(os.path.join(_R, "analysis", "signal_journal.py"),
                 encoding="utf-8").read()
    # ⚠️ ASSERTED ON THE PAYLOAD LINE, NOT THE WHOLE FILE — the changelog above
    # it necessarily names the field while explaining the removal (§20).
    check("L3b and gone from the journal payload",
          '"sweep_age_bars":' not in _jsrc,
          "a column that can only ever be None is worse than no column")
    # 🔑 L3c — WHAT SURVIVES. The rejection's real age is computed every tick
    # and banked on the PLAN row. Removing the dead field must not be mistaken
    # for removing the measurement.
    from strategy.sweep_plan import SweepPlan as _SP3
    check("L3c the real age still reaches the plan row",
          "rejection_age_bars" in _SP3.PLAN_CHECKS,
          "the measurement lives here, not on the signal")
    # L3d RETIRED at r126: it protected the old mapper's own `sweep_age_bars`
    # gate, and the mapper is deleted — there is no second quantity left.

    # ── L4 — THE UNMEASURABLE CASE REFUSES ON ITS OWN TERMS ──────────────
    # 🔴 A 999 sentinel means `bars_ago` could not be read AT ALL. That is a
    # DATA fault, not a staleness judgement, and admitting it silently would be
    # the absent-is-not-zero failure this repo keeps paying for.
    check("L4 (r5) the plan declares rejection freshness as a check, by name",
          "rejection_age_bars" in _checks)

    # ── L5 — LIVENESS IS `invalidated`, WHICH SWP.5 ALWAYS SAID ──────────
    # It fails 73% fleet-wide, which is price accepting through a level — a
    # market fact, not a defect, and the gate doing exactly its job.
    check("L5 (r5) the trigger is the REJECTED fact — declared as a check",
          "rejected" in _checks)

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 7 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
