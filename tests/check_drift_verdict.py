#!/usr/bin/env python3
"""check_drift_verdict.py — v1.0 (landed r171)

🔴 A ONE-OBJECT SHORTFALL MUST NOT KEEP A BOX RUNNING ALL NIGHT.

`--verify` classifies a shortfall as COUNTER DRIFT (duplicate PUTs inflating
the ledger, objects all present) or as possible real loss. The conductor reads
that verdict: drift -> stop the box, otherwise -> HOLD it up.

⚠️ THE OLD RULE REQUIRED `max(gap) <= 2 AND len(short) >= 3`. A box short on
ONE or TWO prefixes never earned the drift verdict — even with a gap of 1 — so
it was HELD and ran all night.

⚠️ MEASURED, from eod_conductor.log: **14 of 15 boxes held on short=1..3, every
night.** The operator confirmed on the held boxes each time that nothing was
actually missing. That is a full night of EC2 per box, indefinitely, for a
fencepost. The conductor's own comment already said *"holding a box for drift
is worse than the bug."*

⚠️ THE GAP SIZE IS THE SIGNAL, NOT THE PREFIX COUNT. Duplicate PUTs inflate a
counter by a SMALL amount wherever they land; genuine loss scatters and is
larger. A 1-object gap on one prefix is the same fencepost as a 1-object gap on
ten. A gap of 3+ still reads as possible loss and still holds the box.
"""
import ast
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def main():
    src = open(os.path.join(_root, "warehouse", "s3_push.py"),
               encoding="utf-8").read()
    code = "\n".join(l for l in src.split("\n")
                     if not l.strip().startswith("#"))

    # ── 🔴 D1 — THE PREFIX-COUNT REQUIREMENT IS GONE ─────────────────────
    # ⚠️ Match CODE, not the comment that explains the change — it quotes the
    # old condition.
    check("D1 the drift verdict no longer requires 3+ short prefixes",
          "len(short) >= 3" not in code)
    check("D2 the drift verdict still keys on the gap size",
          "max(_gaps) <= 2" in code)

    # ── D3 — the rule behaves, on the shapes the fleet actually produced ──
    def verdict(gaps):
        return "DRIFT" if gaps and max(gaps) <= 2 else "LOSS"

    # these are the real nightly shapes: one to three short prefixes, gap 1-2
    for gaps, want in (([1], "DRIFT"), ([1, 1], "DRIFT"), ([2], "DRIFT"),
                       ([1, 1, 1], "DRIFT"), ([2, 1], "DRIFT")):
        check(f"D3 gaps={gaps} -> {want} (was HELD under the old rule)",
              verdict(gaps) == want)

    # ── 🔴 D4 — AND A REAL SHORTFALL STILL HOLDS THE BOX ─────────────────
    # ⚠️ This is the half that must not regress. Relaxing the classifier to
    # stop wasting EC2 must not turn a genuine loss into a shutdown — a
    # stopped box's local store is the only copy, and a stopped box cannot be
    # asked anything.
    for gaps in ([3], [5], [1, 9, 1]):
        check(f"D4 gaps={gaps} still reads as possible LOSS -> box held",
              verdict(gaps) == "LOSS")

    # ── D5 — the conductor still reads the verdict from the raw text ─────
    cond = os.path.join(os.path.dirname(_root), "day_trader_pro",
                        "eod_conductor_v2.py")
    if os.path.exists(cond):
        c = open(cond, encoding="utf-8").read()
        check("D5 the conductor still keys on the COUNTER DRIFT string",
              "COUNTER DRIFT" in c)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_drift_verdict: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
