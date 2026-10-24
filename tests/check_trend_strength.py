#!/usr/bin/env python3
"""
tests/check_trend_strength.py  v1.1
v1.1  2026-09-03  r229 — T10-T12: the acceptance TRAJECTORY separates a tape
      the mean cannot (efficiency 1.00, closes fading), the FVG component
      counts respected pullbacks and returns None when no gap was tested, and
      the composite is UNCHANGED — nothing unproven earns weight.
v1.0  2026-09-03  r224 — THE METER SEPARATES A RIP FROM A CREEP, OR IT IS DEAD
      WEIGHT.

Operator, 2026-09-03: gate the runaway so *"if it ripped to the 50, we want it.
If it creeped, we don't"* — which also ends the re-fires (RUN.1) without a
counter, because a creeping tape cannot re-qualify.

🔴 EVERY POINT-IN-TIME VECTOR FAILED THE SCREEN, WHICH IS WHY THIS MEASURES THE
PATH. `screen_entry_vectors` over 152 RunawayContinuation trades scored on
whether the entry ever went 5% green: adx AUC 0.47 (green 41.7 vs 41.15),
bb_width_pct 0.50, session_fraction 0.50, gex 0.51. Strongest of SIXTEEN was
0.07 from chance, against a pure-noise floor of 0.19 in that tool's own
fixture. The state at the fill says nothing; the path might.

🔑 T4 IS THE CHECK THAT JUSTIFIES FOUR COMPONENTS INSTEAD OF ONE. A tape that
advances in a straight line while every close sits at the BOTTOM of a long
upper wick has EFFICIENCY 1.00 — efficiency alone calls it a healthy trend.
Acceptance catches it, and that is the operator's own doctrine doing work:
wicks are tests, closes are acceptance.

⚠️ T6 GUARDS A BUG THE FIXTURE FOUND TWICE. Shallowness first measured each
bar's low against a running max that INCLUDED that bar's own high —
self-referential — and then against the running gain, which is a few cents
early on, so normal bar overlap read as a 200% retracement. Both drafts
clamped a RIPPER to 0.00, identical to a rollover, making the component pure
noise in the composite. It is maximum adverse excursion over net delivery now.
"""
from __future__ import annotations

import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


def _bars(closes, hi_off, lo_off):
    return [{"open": c, "high": c + hi_off, "low": c - lo_off, "close": c}
            for c in closes]


def main():
    from analysis.trend_strength import measure, MIN_BARS

    rip = [100 + i * 0.20 for i in range(24)]
    creep = [100.0]
    for i in range(23):
        creep.append(creep[-1] + (0.40 if i % 3 else -0.40))
    chop = [100 + (0.3 if i % 2 else -0.3) for i in range(24)]
    dist = [100 + i * 0.18 for i in range(24)]

    r_rip = measure(_bars(rip, 0.03, 0.15), "long")
    r_creep = measure(_bars(creep, 0.10, 0.10), "long")
    r_chop = measure(_bars(chop, 0.10, 0.10), "long")
    r_dist = measure(_bars(dist, 0.35, 0.05), "long")

    # ── T1 — the ordering the whole meter exists to produce ─────────────
    check("T1 rip > creep > chop, strictly",
          r_rip.score > r_creep.score > r_chop.score,
          f"{r_rip.score} / {r_creep.score} / {r_chop.score}")
    check("T1b and the rip clears 0.80 while the chop stays under 0.30",
          r_rip.score >= 0.80 and r_chop.score <= 0.30,
          f"rip {r_rip.score} chop {r_chop.score}")

    # ── T2 — EFFICIENCY is what separates a rip from a creep ────────────
    # ⚠️ Same net move, twice the travel. This is the component that makes a
    # grind measurable at all.
    check("T2 efficiency separates equal net moves by their travel",
          r_rip.efficiency > 0.9 and r_creep.efficiency < 0.5,
          f"rip {r_rip.efficiency} creep {r_creep.efficiency}")

    # ── T3 — PACE is scale-free ─────────────────────────────────────────
    # 🔑 THE NORMALISER. The identical shape on a $7,700 underlying must score
    # the same as on a $100 one, or the meter cannot be one number across a
    # fleet holding both SPX and NFLX.
    big = [7700 + i * 15.4 for i in range(24)]
    r_big = measure(_bars(big, 2.31, 11.55), "long")
    check("T3 the same shape at 77x the price scores the same",
          abs(r_big.score - r_rip.score) < 0.02,
          f"{r_big.score} vs {r_rip.score}")

    # ── T4 — ACCEPTANCE catches distribution efficiency cannot ──────────
    # 🔴 THE CASE FOR FOUR COMPONENTS. Straight-line advance, every close at
    # the bottom of a long upper wick: efficiency 1.00, acceptance ~0.12.
    check("T4 a straight advance on weak closes is NOT scored as a rip",
          r_dist.efficiency > 0.95 and r_dist.acceptance < 0.30
          and r_dist.score < r_rip.score - 0.15,
          f"eff {r_dist.efficiency} acc {r_dist.acceptance} "
          f"score {r_dist.score} vs rip {r_rip.score}")

    # ── T5 — SHORT SIDE MIRRORED ────────────────────────────────────────
    # ⚠️ Not assumed. Every measure is directional and a flipped comparison
    # would score a falling tape as flaccid and a rising one as strong.
    fall = [100 - i * 0.20 for i in range(24)]
    r_short = measure(_bars(fall, 0.15, 0.03), "short")
    check("T5 the mirrored short tape scores like the long rip",
          abs(r_short.score - r_rip.score) < 0.02,
          f"short {r_short.score} vs long {r_rip.score}")
    check("T5b and that same falling tape read as a LONG is weak",
          measure(_bars(fall, 0.15, 0.03), "long").score < 0.30,
          str(measure(_bars(fall, 0.15, 0.03), "long").score))

    # ── T6 — SHALLOWNESS IS NOT DEAD WEIGHT ─────────────────────────────
    # 🔴 TWO DRAFTS CLAMPED IT TO 0.00 FOR EVERY TAPE. A ripper with no
    # pullback must score high and a rollover must score low, or the component
    # contributes only noise to the composite.
    roll = [100 + i * 0.30 for i in range(12)] + \
           [103.3 - i * 0.22 for i in range(12)]
    r_roll = measure(_bars(roll, 0.10, 0.10), "long")
    check("T6 a no-pullback ripper scores HIGH on shallowness",
          r_rip.shallowness >= 0.80, str(r_rip.shallowness))
    check("T6b and a rollover scores LOWER",
          r_roll.shallowness < r_rip.shallowness,
          f"roll {r_roll.shallowness} vs rip {r_rip.shallowness}")

    # ── T7 — A DEGENERATE WINDOW REFUSES, NEVER SCORES 0.0 ──────────────
    # 🔴 A 0.0 ON MISSING DATA READS AS "FLACCID" AND VETOES A GOOD TRADE.
    short_win = measure(_bars(rip[:MIN_BARS - 1], 0.03, 0.15), "long")
    check("T7 too few bars yields NO READING with a reason",
          short_win.score is None and not short_win.ok
          and str(MIN_BARS) in short_win.reason,
          short_win.reason)
    flat = measure(_bars([100.0] * 24, 0.0, 0.0), "long")
    check("T7b a flat tape yields NO READING, not 0.0",
          flat.score is None, f"score={flat.score} reason={flat.reason}")
    check("T7c a bad direction string refuses",
          measure(_bars(rip, 0.03, 0.15), "up").score is None
          or measure(_bars(rip, 0.03, 0.15), "up").score
          != r_rip.score)

    # ── T8 — NaN IS NOT A PRICE ─────────────────────────────────────────
    # ⚠️ Every comparison against NaN is False, so a NaN high would pass a
    # `high > low` guard and poison the mean silently.
    nanb = _bars(rip, 0.03, 0.15)
    nanb[5]["high"] = float("nan")
    r_nan = measure(nanb, "long")
    check("T8 a NaN bar does not silently poison the reading",
          r_nan.score is None or abs(r_nan.score - r_rip.score) < 0.15,
          f"score={r_nan.score} reason={r_nan.reason!r}")

    # ── T9 — the line() summary states a refusal as a refusal ───────────
    check("T9 line() names a no-reading rather than printing a number",
          "NO READING" in short_win.line(), short_win.line())

    # ── T10 — THE ACCEPTANCE TRAJECTORY SEES WHAT THE MEAN CANNOT ───────
    # 🔴 THE MEAN WAS THE STRONGEST COMPONENT IN THE FIRST CALIBRATION AND
    # STILL DID NOT CLEAR THE NOISE FLOOR. It is blind to DIRECTION: 0.4
    # building to 0.7 and 0.7 decaying to 0.4 average the same, and they are
    # opposite tapes. This plants a straight advance whose closes drift off
    # the highs — EFFICIENCY 1.00, a textbook "healthy trend" — and requires
    # the trajectory to call it deteriorating.
    n = 24
    dec = [{"open": 100 + i * .20, "high": 100 + i * .20 + .03 + .02 * i,
            "low": 100 + i * .20 - .15, "close": 100 + i * .20}
           for i in range(n)]
    r_dec = measure(dec, "long")
    check("T10 a straight advance with fading closes reads as deteriorating",
          r_dec.efficiency > 0.95 and r_dec.acc_slope < 0
          and r_dec.acc_delta < 0 and r_dec.acc_run == 0.0,
          f"eff {r_dec.efficiency} slope {r_dec.acc_slope} "
          f"delta {r_dec.acc_delta} run {r_dec.acc_run}")
    check("T10b while a genuine rip trajectories UP or holds",
          r_rip.acc_run > 0.5 and (r_rip.acc_delta or 0) >= -0.05,
          f"run {r_rip.acc_run} delta {r_rip.acc_delta}")

    # ── T11 — FVG: A PULLBACK THAT FILLS AND CONTINUES ──────────────────
    # 🔑 The first component measuring WHY a pullback ended. Mechanical fill
    # and continuation vs a fill that keeps going through.
    up = [100 + i * .20 for i in range(12)]
    held = _bars(up + [102.0, 101.6] + [101.8 + i * .22 for i in range(10)],
                 .03, .15)
    r_held = measure(held, "long")
    check("T11 gaps tested and respected are counted",
          r_held.fvg_tested > 0 and r_held.fvg_respect == 1.0,
          f"tested {r_held.fvg_tested} respect {r_held.fvg_respect}")

    # ⚠️ NO GAP TESTED IS None, NOT 0.0. "No imbalance was retested" and
    # "every retest failed" are different facts; scoring the first as the
    # second would read a clean, gapless trend as a broken one.
    flatish = _bars([100 + i * .02 for i in range(24)], .30, .30)
    check("T11b an untested imbalance yields None, not 0.0",
          measure(flatish, "long").fvg_respect is None,
          str(measure(flatish, "long").fvg_respect))

    # ── T12 — THE COMPOSITE IS UNCHANGED ────────────────────────────────
    # 🔴 NOTHING NEW IS WEIGHTED. Adding an unproven component to the score
    # moves the gate on a guess; the calibration decides what earns weight.
    check("T12 the new components are recorded but NOT in the score",
          abs(r_rip.score - 0.9196) < 0.02,
          f"score {r_rip.score} — unchanged from v1.0's fixture")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_trend_strength: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
