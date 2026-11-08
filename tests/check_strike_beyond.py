#!/usr/bin/env python3
"""
tests/check_strike_beyond.py  v5.1
v5.1  2026-11-08  OTV5 r76 (RETIRE.1) — S0-S4 (the sweep's level ranker and plan telemetry) go with the sweep; P1-P5 drive strike_beyond_sweep, which the
      TCS shadow still reads, unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.1  2026-09-22  OTV4TEST r102 - S3 RE-POINTED AT THE PLAN, AND IT WAS
      HIDING A REAL LOSS. The AttributeError killed the run before S3, and
      behind it the three telemetry fields were GENUINELY ABSENT - dropped by
      r5's rewrite while its header went on promising them. Born red at
      1104492 on both faults.
v1.0  2026-09-03  r233 — THE STRIKE MUST CLEAR THE TESTED RANGE, AND THE
      NEAREST LIVE LEVEL WINS. Operator, 2026-09-03: *"the strike cannot sit
      at any level that is part of the testing range... it has to be just
      beyond that, if only a little bit"*, and *"the level in question needs
      to be the closest to the current price."*

⚠️ EXECUTED, NEVER READ (WA §21). Every check drives `strike_beyond_sweep`
or the real selector and asserts on the returned strike. Asserting the source
contains `sweep_price` would have passed against the broken version, which
also contained it.

⚠️ THE DEEP-PIERCE FIXTURE IS THE HEADER'S OWN EXAMPLE, not one I invented
(WA §0.4): pool 7639.01 / extreme 7633 is the case `strike_beyond_sweep`
documents while contradicting its own stated intent one paragraph earlier.

Plain script, exit code, no pytest (§36 — the boxes' venv has none).
"""
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


class K:
    def __init__(self, k):
        self.strike = k


class SW:
    def __init__(self, pool, kind="low_sweep", bars=1, touch=False, sx=None):
        self.pool_price, self.kind, self.bars_ago = pool, kind, bars
        self.touch, self.sweep_price = touch, (sx if sx is not None else pool)


def main():
    from strategy.sweep_credit_spread import strike_beyond_sweep as f

    ks = [K(k) for k in (7630, 7635, 7640, 7645)]

    # ══ P1 — THE DEEP PIERCE. The header's own example, and the whole point.
    # pool 7639.01, wick 7633: 7635 sits BETWEEN them. Price traded clean
    # through it on the way down, so a second test of the same size takes the
    # position out.
    k = f(7633.0, 7639.01, False, contracts=ks)
    check("P1 a DEEP pierce does not sell inside the tested range",
          k is not None and k <= 7633.0, f"got {k}")

    # ══ P1b — and it is the NEAREST of what is beyond, not the furthest
    check("P1b it takes the nearest strike beyond the wick", k == 7630.0, f"got {k}")

    # ══ P2 — the SHALLOW pierce is unchanged. This is the median case
    # (pierce_depth 0.0032 vs a 0.5685 max), so the change must not reprice it.
    check("P2 a shallow pierce is unchanged at 7635",
          f(7638.17, 7639.01, False, contracts=ks) == 7635.0)

    # ══ P3 — MIRRORED ON THE CEILING. A flipped comparison here would sell
    # INSIDE the pierce on every call spread, silently.
    kc = f(7643.0, 7630.0, True, contracts=ks)
    check("P3 a DEEP ceiling pierce clears the wick upward",
          kc is not None and kc >= 7643.0, f"got {kc}")
    check("P3b ceiling takes the nearest above, not the furthest",
          kc == 7645.0, f"got {kc}")

    # ══ P4 — THE POOL BOUND IS NOW IMPLIED AND PROVEN INERT. A wick is beyond
    # its pool by definition, so the pool filter can only ever narrow the set.
    # Kept because it documents the invariant; pinned so it is known inert
    # rather than assumed so.
    for ex, pool, ceil in ((7633.0, 7639.01, False), (7643.0, 7630.0, True)):
        a = f(ex, pool, ceil, contracts=ks)
        b = f(ex, ex, ceil, contracts=ks)          # pool bound made vacuous
        if a != b:
            check("P4 the pool bound never binds once the wick bound applies",
                  False, f"{a} vs {b}")
            break
    else:
        check("P4 the pool bound never binds once the wick bound applies", True)

    # ══ P5 — NO STRIKE BEYOND THE WICK IS A DECLINE, NEVER A SUBSTITUTE.
    # r215 doctrine: out of range means no level, never an invented one.
    check("P5 a wick past the end of the chain declines",
          f(7000.0, 7639.01, False, contracts=ks) is None)

    # ══ S0-S4 r76: the sweep's level ranker (level_rank) and its plan are removed with the sweep; the strike
    # helper above (P1-P5) is what the TCS shadow still reads.
    import strategy.sweep_credit_spread as S
    check("S0 r76: the sweep's level ranker is gone; strike_beyond_sweep stays", not hasattr(S, "level_rank")
          and callable(getattr(S, "strike_beyond_sweep", None)))

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
