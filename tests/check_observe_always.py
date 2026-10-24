#!/usr/bin/env python3
"""
tests/check_observe_always.py  v4.0
Observation runs ALWAYS. Trading runs only in RTH. Two gates, not one.

v4.0  2026-08-24  Operator: **"TRADING can only occur during RTH, the feed
should be ALWAYS."**

🔴 THEY WERE THE SAME GATE. `run_analysis` ends by running the derived layer,
and the pre-RTH branch of the main loop `continue`d before reaching it — so
every deriver inherited a gate that belongs only to trading. Measured
2026-08-24 07:42 across all fifteen boxes: greeks 3024 rows age=676s, quotes
3024, prints age=1s, and indicators / pitchfork / levels / surface all rows=0.
The inputs were abundant and fresh; nothing was consuming them.

🔑 THE PRINCIPLE: derivers are CONTRIBUTORS and never gate trading — so nothing
about them may be gated BY trading. `run_analysis` is the observation pass;
everything after it in a tick is the trading pass. The gate goes BETWEEN them.

⚠️ BOTH HALVES OR NEITHER. A check that only asserted "observes outside RTH"
would pass a loop that also TRADED outside RTH, which is a far worse bug than
the one being fixed. O2 pins the trading half explicitly.

Run:  cd ~/options-trader && python3 tests/check_observe_always.py
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
PROBLEMS: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


def _pre_rth_block() -> str:
    """The `if not is_rth():` branch of the main loop, to its `continue`s."""
    i = SRC.find("if not is_rth():", SRC.find("while True:"))
    return SRC[i:i + 1800] if i >= 0 else ""


def main() -> int:
    print("=" * 62)
    print("OBSERVE ALWAYS, TRADE IN RTH — two gates, not one")
    print("=" * 62)
    blk = _pre_rth_block()

    check("O0 the pre-RTH branch exists", bool(blk))

    # O1 — the observation pass is REACHED outside RTH.
    check("O1 run_analysis is called in the pre-RTH branch (derivers run)",
          "run_analysis(state)" in blk,
          "the branch continues before reaching the derived layer")

    # O2 — and NOTHING that trades is reached there.
    # ⚠️ THIS IS THE HALF THAT MATTERS MOST. Observing outside RTH is an
    # improvement; TRADING outside RTH would be a catastrophe, and a one-sided
    # check would not tell them apart.
    forbidden = [f for f in ("attempt_new_entry", "manage_open_position",
                             "entry_eng.enter", "check_and_execute_roll")
                 if f in blk]
    check("O2 NOTHING that trades is reachable outside RTH",
          not forbidden, f"trading calls in the pre-RTH branch: {forbidden}")

    # O3 — the observation pass cannot stop the box opening for business.
    seg = blk[blk.find("run_analysis(state)") - 200:
              blk.find("run_analysis(state)") + 300] if "run_analysis(state)" in blk else ""
    check("O3 the pre-RTH pass is wrapped — an observation failure never "
          "blocks the open",
          "try:" in seg and "except" in seg,
          "an unwrapped pre-market raise would kill the loop before RTH")

    # O4 — the derived layer really is the tail of run_analysis, which is what
    # makes calling it sufficient. If someone moves run_all elsewhere, O1 keeps
    # passing while deriving nothing — so pin the coupling, not just the call.
    i = SRC.find("def run_analysis")
    j = SRC.find("\ndef ", i + 1)
    check("O4 the derived layer runs inside run_analysis",
          "run_all(" in SRC[i:j],
          "run_all moved out of run_analysis — O1 no longer implies deriving")

    print("=" * 62)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        return 1
    print("  ALL GREEN — the feed observes always; only trading waits for RTH")
    return 0


if __name__ == "__main__":
    sys.exit(main())
