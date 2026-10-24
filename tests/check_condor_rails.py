#!/usr/bin/env python3
"""
tests/check_condor_rails.py  v4.0

The condor's guardrail can actually be built, and asked for by its real name.

v4.0  2026-08-21  Written after the condor was found to have NEVER been
      plannable in v4 — two independent defects, both silent, both presenting
      as the operator's own insurance policy working correctly.

WHAT WAS WRONG, and it took two faults stacked:

  1. `config.CONDOR_PF_TIMEFRAME` defaulted to **"daily"** while
     `pitchfork_observer.refresh()` caches under the FRAME keys "1d"/"1h"
     (taken straight from ctx["data"]). `rails_for` did `forks.get("daily")`,
     got nothing, returned None — and CONDOR_REQUIRE_FORK reads None as
     "no guardrail, stand down".

  2. `build_fork_contained` failed on a large minority of frames.
     `_epoch_triple` chose P2 as the RUNNING EXTREME of the tail after P1 —
     not a confirmed fractal — so on any frame still making new highs/lows
     into the close it landed on or within k of the final bar, and §4.4's
     confirmation-lag guard (`p2.idx + k > n - 1`) then correctly rejected the
     window. Where the tail extreme is recent, EVERY candidate window is
     discarded. Measured across 40 synthetic frames: built 23/40 before,
     28/40 after.

⚠️ ONLY THE FIRST DEFECT WAS UNIVERSAL, and the distinction is worth keeping:
fault 1 meant rails were never even fetched, on any box, ever. Fault 2 lowered
the build rate. An early draft of this file said the fork "never" built — the
measurement says otherwise, and a doctrine block that overstates its own
evidence is the thing this repo distrusts most.

⚠️ NEITHER FAULT PRODUCED AN ERROR. "no usable daily pitchfork (rails=absent)"
is the CORRECT message for a genuinely absent fork, so the log read as the
guardrail policy doing its job — on every box, every session. The operator's
rule ("consider the condor off the table if we don't have guardrails") was
being honoured against a fork that could not exist.

⚠️ THIS CHECK EXECUTES THE WHOLE PATH. It builds a frame, runs the real
`refresh` → `rails_for` chain, and asserts rails come back. A source-text check
would have passed against both defects — and the second one is invisible to
anything short of running the selector, since every individual function was
behaving exactly as written.

BORN RED, verified 2026-08-21 against HEAD 9d458c7:
  C1 -> build_fork_contained returns None on the seed-7 frame
  C3 -> rails_for(..., "daily") returns None

Run:  cd ~/options-trader-v4 && python3 tests/check_condor_rails.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROBLEMS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


def _frame(n=90, seed=42):
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(seed)
    base = np.cumsum(rng.normal(0.15, 1.2, n)) + 100.0
    idx = pd.date_range("2026-04-01", periods=n, freq="D")
    return pd.DataFrame({"open": base,
                         "high": base + rng.uniform(0.5, 2.0, n),
                         "low": base - rng.uniform(0.5, 2.0, n),
                         "close": base,
                         "volume": np.full(n, 1e6)}, index=idx)


def main() -> int:
    print("=" * 68)
    print("CONDOR RAILS: the fork builds, and answers to the configured name")
    print("=" * 68)

    import numpy as np
    import config
    from analysis.pitchfork import build_fork_contained
    from analysis import pitchfork_observer as po

    # ⚠️ SEED 7 IS DELIBERATE. Seed 42 builds a contained fork even with the
    # P2 defect present, so C1 on that frame is green either way and proves
    # nothing. A fixture that cannot fail is the failure class this repo hunts;
    # 7 is a frame whose tail extreme is recent, which is the case that broke.
    df = _frame(seed=7)
    atr = float(np.mean(df["high"].values - df["low"].values))

    # ── C1 the contained fork builds at all ──────────────────────────────
    f = build_fork_contained("TEST", df, "1d", atr)
    check("C1 build_fork_contained returns a Fork", f is not None,
          "returned None on 90 clean daily bars - P2 is being proposed where "
          "it can never be confirmed")

    # ── C2 P2 is confirmable BY CONSTRUCTION, not by luck ────────────────
    # The invariant the two rules disagreed about: a proposed P2 must leave k
    # bars of room after it, or §4.4 is obliged to throw the window away.
    import analysis.pitchfork as pf
    k = pf.FRACTAL_K["1d"]
    n = len(df)
    bad = []
    for start in range(0, n - (3 * k + 3) + 1):
        t = pf._epoch_triple(df, start, k)
        if t is None:
            continue
        if t[3].idx + k > n - 1:
            bad.append((start, t[3].idx))
    check("C2 no proposed P2 violates the confirmation lag", not bad,
          f"{len(bad)} window(s) propose a P2 the §4.4 guard must reject, "
          f"e.g. {bad[:3]} with n-1={n-1}")

    # ── C3 the configured spelling actually resolves ─────────────────────
    ctx = {"data": {"1d": df, "1h": df}}
    for spelling in ("1d", "daily", "Daily", "1h", "hourly"):
        po._cache["ts"] = 0
        r = po.rails_for(ctx, "TEST", spelling)
        check(f"C3 rails_for({spelling!r}) returns rails", r is not None,
              "None - the condor stands down and calls it a guardrail policy")

    # ── C4 a genuine typo still refuses ──────────────────────────────────
    po._cache["ts"] = 0
    check("C4 an unknown timeframe still returns None",
          po.rails_for(ctx, "TEST", "bogus") is None,
          "an alias table that GUESSES is worse than one that refuses")

    # ── C5 the configured default is a key the cache can serve ───────────
    po._cache["ts"] = 0
    cfg_tf = config.CONDOR_PF_TIMEFRAME
    check(f"C5 CONDOR_PF_TIMEFRAME={cfg_tf!r} resolves to a live frame",
          po.rails_for(ctx, "TEST", cfg_tf) is not None,
          f"{cfg_tf!r} does not map to any key refresh() caches - this is the "
          f"exact mismatch that disabled the condor")

    print("=" * 68)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        print("  An absent guardrail and a broken one produce the SAME log line.")
        return 1
    print("  ALL GREEN - the fork builds and the condor can ask for it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
