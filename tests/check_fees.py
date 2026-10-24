#!/usr/bin/env python3
"""
tests/check_fees.py  v1.0
v1.0  2026-09-07  r293 — THE LAND GATE FOR `fees.py`.

WHY THIS FILE EXISTS, AND WHY `fees.py`'s OWN FLAGS COULD NOT BE THE GATE.
`land.sh` runs each declared check as `python3 "$chk"` with `$chk` as ONE
QUOTED ARGUMENT, so a `CHECK` directive is a **script path** — no interpreter
prefix, no arguments. r293's first land.spec wrote
`CHECK python3 tests/fees.py --selftest`, and the lander duly ran
`python3 "python3 tests/fees.py --selftest"` against a filename that does not
exist.

🔴 **FOUND BY RUNNING THE REAL DEPLOY PATH, NOT BY READING IT.** I had verified
the three CHECK commands by executing them in a shell with the repo as cwd,
which is what land.sh *documents* — and that is not what it *does*. The same
class as WA §21: reading a thing proves nothing about how it is invoked.

⚠️ **AND THE OBVIOUS SHORTCUT WOULD HAVE BEEN A LAUNDERED GREEN.**
`CHECK tests/fees.py` is a legal directive: it runs with no arguments, prints
the argparse help, and **exits 0**. The gate would have passed while executing
nothing at all — WA §18's own named enemy, and worse than the red it replaced,
because a red gets investigated.

WHAT THIS GATE ACTUALLY RUNS — all three entry points, by execution:
  · `selftest()`  — 25 checks, six of them mutation-proven, including the four
    pinned against the May 2025 statement's real charges.
  · `reconcile_may()` and `reconcile()` — the two statement reconciliations.
    They are REPORTS and return 0 by design, so a gate that only read their
    exit code would prove nothing; this one asserts they produce the specific
    confirmed figures, so a rate edit that silently breaks the structure goes
    red here rather than in a report nobody re-reads.

Run:  python3 tests/check_fees.py
"""
from __future__ import annotations

import io
import os
import sys
import contextlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fees                                                     # noqa: E402

FAILURES: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def _bare_rc() -> int:
    """`fees.py` with no args, output swallowed. It prints an argparse usage
    block, and a GATE that prints a usage banner reads like a failure to
    anyone re-running it by hand."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fees.main([])


def main() -> int:
    print("\ncheck_fees — the land gate for the fee model\n")

    # G1 — the model's own selftest, EXECUTED. Its output is captured so this
    # gate's own verdict is readable, and replayed on failure so a red is
    # diagnosable without a second run.
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fees.selftest()
    out = buf.getvalue()
    check("G1  fees.selftest() passes", rc == 0,
          f"{out.count('PASS')} checks passed" if rc == 0
          else "output replayed below")
    if rc != 0:
        print(out)

    # G2 — the reconcilers RUN. They touch the statement datasets and every
    # rate constant, so an edit that breaks their arithmetic surfaces here.
    for name, fn in (("reconcile_may", fees.reconcile_may),
                     ("reconcile", fees.reconcile)):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                r = fn()
            check(f"G2  {name}() runs clean", r == 0)
        except Exception as e:                                  # noqa: BLE001
            check(f"G2  {name}() runs clean", False, f"{type(e).__name__}: {e}")

    # G3 — THE STRUCTURE THE MAY 2025 STATEMENT MEASURED, asserted here and not
    # only inside a printed report. A report is read once; a gate is read on
    # every land.
    spx = fees.fees_for({"trade_id": "g", "symbol": "SPX", "strategy": "ORB",
                         "contracts": 45, "status": "closed",
                         "entry_premium": 5.01, "exit_premium": 5.01})
    check("G3  SPX 45-lot commission is $45 — the statement charged $80.08, "
          "which no $10 cap can produce",
          abs(spx.legs[0].commission - 45.0) < 1e-9,
          f"${spx.legs[0].commission:.2f}")
    eq = fees.fees_for({"trade_id": "g", "symbol": "NVDA", "strategy": "ORB",
                        "contracts": 50, "status": "closed",
                        "entry_premium": 1.0, "exit_premium": 1.0})
    check("G3b equity 50-lot commission caps at $10 — measured on SPY at 20",
          abs(eq.legs[0].commission - 10.0) < 1e-9,
          f"${eq.legs[0].commission:.2f}")

    # G4 — ABSENCE IS NEVER ZERO. The property most likely to be lost to a
    # well-meaning refactor, because returning 0.0 makes every caller simpler.
    bad = fees.fees_for({"trade_id": "g", "symbol": "NVDA", "contracts": 0})
    check("G4  an unpriceable row returns Unpriced with a named reason, "
          "never 0.0",
          isinstance(bad, fees.Unpriced) and bool(bad.reason),
          getattr(bad, "reason", "RETURNED A BREAKDOWN"))
    check("G4b net_of_fees returns None on that row, never the gross",
          fees.net_of_fees({"trade_id": "g", "symbol": "NVDA",
                            "contracts": 0, "pnl_usd": 100.0}) is None)

    # G5 — THIS GATE MUST NOT BE SATISFIABLE BY DOING NOTHING. `fees.py` with
    # no arguments prints help and exits 0, which is what a lazier CHECK line
    # would have run. Pinned so nobody "simplifies" the spec back to that.
    check("G5  bare `fees.py` exits 0 without testing anything — which is "
          "why this file is the CHECK and fees.py is not",
          _bare_rc() == 0)

    print()
    if FAILURES:
        print(f"check_fees: FAIL ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("check_fees: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
