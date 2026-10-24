# docs/INHERITED_FINDINGS.md — v4.0

**What OTV3 measured. Carried so OTV4 does not rebuild any of it.**
**Every number here is from the live book or banked tape, not from reasoning.**

---

## 1. THE CLASSIFIER WAS WORSE THAN A COIN AT PICKING SIDE

`direction_skill.py`, 2026-08-19. **715 closed directional trades, 16 sessions**,
ORB and neutral structures excluded (ORB never consulted the classifier, so
including it would have credited the regime engine with ORB's record).

| | n | correct side | 95% CI |
|---|---|---|---|
| **all** | **715** | **44.9%** | **[41.3%, 48.6%]** |
| calls | 528 | 48.7% | [44%, 53%] |
| **puts** | **187** | **34.2%** | **[28%, 41%]** |
| ContinuationStrategy | 660 | 46.1% | net **−$5,872** |

**The interval sits entirely below 50%.** The engine was roughly random when it
said up and **reliably wrong when it said down**.

⚠️ **THE PUT NUMBER IS THE ONE TO REMEMBER.** Any successor that inherits a
bearish read from OTV3 logic inherits an anti-signal.

---

## 2. A BLIND READ OF SIX RANDOM TAPES AGREED

Six sessions read from OHLC alone, segments written **before** seeing any score.

· **Aggregate range-share matched the engine closely** — it is not uniformly
  broken.
· **Two of six were directionally BACKWARDS**, both on the largest moves in the
  sample: one closing **+2.47%** scored TRENDING_BEAR; one that fell **8.6% in
  the first hour** scored TRENDING_BULL.
· **`SWEEP_REVERSAL` read 0% on all six**, including a textbook
  low-sweep-and-reclaim (−8.6% then +27 points in fifteen minutes).

⚠️ Both direction errors were on sessions whose decisive move was in the FIRST
HOUR. Consistent with warm-up: the engine scores the retrace because it had no
opinion during the move.

---

## 3. NOTHING COLLECTED SEPARATED OUTCOMES AT DECISION TIME

`separation_probe.py` against the never-favourable split, pre-registered
criterion (nf below ok · Mann-Whitney p<0.05 · |Cliff's delta| ≥ 0.147 · n ≥ 200
across ≥ 10 sessions · sign stable).

**Dead:** `direction_conf` (delta **+0.09** at 28% ties — the median gap of
+0.257 was an artifact of overlapping distributions) · the entire **0DTE IV
surface** (25d risk-reversal +0.09, skew +0.03, ATM level inverted) · the
**backfilled overnight gap** (delta −0.07) · L1 dominance (inverted) · RANGING
score (inverted).

**Survived:** only `SETUP` (+0.19) and `ADX at entry` (+0.17) — **both
confirmatory-class**, the late-reading measures the retool set out to escape.

⚠️ **AND THREE COLUMNS WERE SCORED AS NULLS WHEN THEY WERE MERELY EMPTY.**
`flat_angle_deg` 100% ties on ONE value (computed every tick, never attached to
the regime object) · `level_strength` 94% on TWO (formula collapsed because
`touch_count` is a constant; only a hard-gated strategy wrote it) ·
`vix_at_entry` 58% default-zero (the two highest-volume strategies never set
it). **A column with a numeric DEFAULT cannot distinguish "measured zero" from
"never written."**

---

## 4. THE SCORER INVERTED, AND WHY

`setup_scorer.py`: **A-grade 399 trades −$8,244** at 1.5× size ·
**B-grade 220 trades +$1,893**.

~90% of the grade was **one column printed twice** — `regime_conviction` and
`signal_quality` had identical medians AND identical spreads (0.913/0.636 over
619 trades) — plus two constants that measured **1.000 across all 619**.

Its own conclusion: *"High conviction means the trend is already obvious, which
means LATE."*

⚠️ **THE SAME DEFECT EXISTED ONE LAYER DOWN.** TRENDING's corroborator was
`max(align_frac, ramp(adx, adx_trend, 35))` while its soft-necessary was
`ramp(adx, adx_trend − 5, 35)` — same input, same upper bound, lower bounds 5
apart. Measured on AMD 2026-08-13: removing the mask moved the score on **110 of
390 ticks by a constant 0.2167**.

---

## 5. WHAT ACTUALLY MADE MONEY

| exit | n | win | net |
|---|---|---|---|
| `orb_trail_stop` | 107 | **95%** | **+$37,848** |
| `theta_bleed` | 107 | **100%** | — |
| `continuation_trail` | 149 | 85% | +$27,884 |

**None consults the regime engine.** ORB fires on break-and-retest geometry it
validates itself and is deliberately regime-agnostic.

Operator, 2026-08-19: *"every day where P&L was green or very green is nearly
entirely based on the ORB trade and the quality of our stops."*

---

## 6. DEFECT PATTERNS THAT RECURRED — WATCH FOR THESE

**COMPUTED AND DISCARDED.** A quantity is calculated, lands in a dict or a
local, and never reaches its consumer. Three instances in one week:
`direction_conf` separated on the live book and was journaled nowhere;
`flat_angle_deg` was computed every tick and never attached to the regime
object; the S3 pusher's `SHORT` diagnostics were captured and truncated at the
log boundary.

**A CONFIG BELOW ITS CONSUMER'S THRESHOLD IS A PERMANENT SILENT FAILURE.**
`TIMEFRAMES["1h"]` asked for 50 bars; `trend_engine` requires `EMA_SLOW + 5` =
55. **The 1h vote — 0.20 weight, second-heaviest — could never fire**, and the
warning looked transient.

**ABSENT MEASUREMENT REPORTED AS A NULL.** An under-powered probe row, a
hardcoded status string, a sub-noise value printing as `0.000`. **All three
happened.** Distinguish "we measured nothing" from "we measured zero."

**A NUMERIC DEFAULT MASQUERADING AS DATA.** See §3.

**A FIX THAT BREAKS ITS OWN SAFETY NET.** A `ctx` NameError raised inside a
`try`, whose `except` handler touched the same unbound name and re-raised —
**boxes traded nothing and an import check could not catch it.** §21: tests must
EXECUTE the path.

---

## 7. WHAT IS EXPLICITLY UNRESOLVED

· **The structural class was never tested.** The columns that would have shown
  it were empty until 2026-08-19. That is a standing option, not a closed door.
· **Term structure was never measurable** — every chain snapshot before
  2026-08-18 carried a single 0DTE expiry.
· **Warm-up as the cause of the two backwards tapes** is a hypothesis, not a
  measurement. The timestamps would settle it.
