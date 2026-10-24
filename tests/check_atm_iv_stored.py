#!/usr/bin/env python3
"""tests/check_atm_iv_stored.py  v1.1
`atm_iv` REACHES ctx, AND EVERY READER TAKES THE SAME VALUE.

v1.1  2026-09-18  OTV4TEST r43 — A3b demanded EXACTLY TWO readers of the
      stored atm_iv, which was a pin on the SHAPE (two butterfly paths) rather
      than on the rule. r43 collapsed them to one; A3b now demands at least one
      and A3 still forbids recomputation.
v1.0  2026-08-31  r205 — born red at r204: `ctx["atm_iv"]` is never assigned.

🔴 MEASURED, NOT REASONED. Every one of the 31 `fire_snapshot` rows from the
fleet's first live session (2026-08-31) carried `price` and a NULL `atm_iv`,
across all 13 symbols that fired. `chain.atm_iv` is a real property
(options_chain.py:175, r177) and `chain` is a PARAMETER of `run_analysis` — but
the only two readers bound it to a LOCAL `_atm_iv` inside the butterfly
dispatch branches. A grep for any assignment to `ctx["atm_iv"]` came back
empty, so `ctx.setdefault("atm_iv", None)` was the first and last word on it.

⚠️ THE SNAPSHOT WAS THE SYMPTOM. `ctx["atm_iv"]` feeds
`volatility_measures.summarise(...)`, which produces `expected_move_iv` and
`variance_risk_premium`. Those have been derived from None since they were
written — and the comment above that call says the decay term is the whole
point of passing a live IV.

🔑 A2 IS THE CHECK THAT MATTERS, AND IT EXECUTES. `run_analysis` needs live
market data and raises in a sandbox, so the conversion is extracted as
`atm_iv_from_chain` and pinned directly — a check that can only report "could
not execute" gates nothing. A3 pins that
the butterfly branches read the STORED value rather than recomputing, because
two computations of one quantity in one tick can disagree — the bug nobody
would ever find.

⚠️ A4 pins that a MISSING chain leaves the field None rather than 0.0. Absent
and zero are different facts, and r177 exists because a `getattr(..., 0.0)`
default masked exactly this absence for months.

Run:  python3 tests/check_atm_iv_stored.py
"""
import os
import re
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
    src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()

    # ── A1: the assignment exists at all ──────────────────────────────────
    # ⚠️ Anchored to the ASSIGNMENT, whatever supplies it — not to the inline
    # form the first cut happened to use. A canary tied to one spelling of a
    # fix breaks the moment the fix is refactored (§20).
    check("A1 ctx['atm_iv'] is assigned, not merely defaulted",
          re.search(r'ctx\["atm_iv"\]\s*=', src) is not None,
          "it was setdefault(None) and nothing else")
    check("A1b the old setdefault is gone as the only word on the field",
          'ctx.setdefault("atm_iv", None)' not in src)

    # ── A3: one source — the branches read, they do not recompute ─────────
    # ⚠️ Anchored to the DEFINITION shape (an assignment from the chain inside
    # a dispatch branch), not to a mention of atm_iv (WORKING_AGREEMENT §20).
    recompute = re.findall(
        r'^\s+_atm_iv = float\(getattr\(chain, "atm_iv"', src, re.M)
    check("A3 no dispatch branch recomputes atm_iv from the chain",
          not recompute,
          f"{len(recompute)} branch(es) still recompute")
    # ⚠️ r43 — THE COUNT WAS 2 BECAUSE THERE WERE TWO BUTTERFLY PATHS. ADM.1
    # collapsed them into one (`_attempt_butterfly`), so one reader disappeared
    # with the duplicate it belonged to. An exact count is a pin on the SHAPE of
    # the code, not on the rule — the rule is "read the stored value, never
    # recompute it", and A3 above is what enforces the second half. A3b now
    # demands at least one reader and no zero.
    _n = src.count('_atm_iv = ctx.get("atm_iv")')
    check("A3b the branches read the stored value",
          _n >= 1, f"found {_n} (was 2 while two butterfly paths existed)")

    # ── A2 / A4: EXECUTED, against the extracted conversion ───────────────
    # 🔑 `run_analysis` needs live market data and raises in a sandbox, so a
    # check that only called it would report "could not execute" and gate
    # nothing. The conversion is extracted precisely so this can RUN.
    check("A2a run_analysis stores the conversion's result",
          'ctx["atm_iv"] = atm_iv_from_chain(chain)' in src,
          "the assignment must call the one helper")
    check("A2b the helper is defined once",
          src.count("def atm_iv_from_chain(") == 1)

    try:
        import main as M
        fn = M.atm_iv_from_chain
    except Exception as exc:                                    # noqa: BLE001
        check("A2 the conversion is importable and runs", False, str(exc))
        print(f"\nFAILED {len(_fails)}: " + ", ".join(_fails))
        return 1

    class _Chain:
        atm_iv = 0.4237

    class _NoIV:
        atm_iv = 0.0        # feed has not populated ivs yet

    class _Bad:
        @property
        def atm_iv(self):
            raise RuntimeError("chain is a corpse")

    check("A2 a live chain yields its IV",
          fn(_Chain()) == 0.4237, f"got {fn(_Chain())!r}")
    check("A4 a chain with no ivs yields None, never 0.0",
          fn(_NoIV()) is None, f"got {fn(_NoIV())!r}")
    check("A4b no chain yields None — absent, not zero",
          fn(None) is None, f"got {fn(None)!r}")
    check("A5 a chain that raises yields None and does not propagate",
          fn(_Bad()) is None, f"got {fn(_Bad())!r}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_atm_iv_stored: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
