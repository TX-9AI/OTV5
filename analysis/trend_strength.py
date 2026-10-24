"""
analysis/trend_strength.py  v1.1
v1.1  2026-09-03  r229 — TWO NEW COMPONENT FAMILIES, RECORDED NOT WEIGHTED.
      The first calibration (182 runaway trades, 2026-08-25..09-03) put every
      component under the noise floor — best 0.63 against a 0.65 guidance —
      and ACCEPTANCE was the strongest at every window (0.63/0.62/0.58).
      🔑 OPERATOR: "a continuing degree of acceptance may be the right
      signal." The MEAN is blind to DIRECTION — 0.4 building to 0.7 and 0.7
      decaying to 0.4 average the same and are opposite tapes. Three
      expressions are now recorded: `acc_slope` (fit across the window),
      `acc_delta` (recent vs whole — "is it STILL happening"), and `acc_run`
      (consecutive closes in the upper third, closest to the doctrine).
      Measured on a fixture: a straight advance with closes drifting off the
      highs scores EFFICIENCY 1.00 while slope -0.023, delta -0.164 and run
      0.00 all say deteriorating.
      🔑 AND THE SAME MEASURE READ BACKWARD IS EXHAUSTION — one measure in two
      directions rather than two meters (MOM.1 stage 5).
      🔑 FVG CONTINUATION, operator: "whether pullbacks filled at FVG and
      continued onwards." The first component that measures WHY a pullback
      ended rather than how deep it was: filling an imbalance and continuing
      is MECHANICAL, filling it and carrying on through is DISTRIBUTION.
      ⚠️ DETECTED FROM THE WINDOW'S OWN BARS, not from `trades.entry_snapshot`
      — which does hold the gaps at every fill and would be good
      corroboration, but reading it would make `measure()` depend on a trade
      row, and its purity as a function of bars is what lets the calibrator
      score the SAME code that trades.
      🔴 BACKWARD-LOOKING BY CONSTRUCTION: whether the pullback AFTER entry
      filled and continued is a POST-ENTRY fact — it would calibrate
      beautifully and be unusable as a gate.
      ⚠️ NOTHING NEW IS IN THE COMPOSITE. Adding an unproven component to the
      score moves the gate on a guess; the calibration decides.
v1.0  2026-09-03  r224 — A TREND STRENGTH METER BUILT FROM THE PATH.

Operator, 2026-09-03: what combination of vectors defines a healthy trend from
a flaccid one — and, for the runaway, *"if it ripped to the 50, we want it. If
it creeped, we don't."*

🔴 EVERY POINT-IN-TIME INDICATOR FAILED THE SCREEN, SO NONE IS USED HERE.
`screen_entry_vectors` over 152 RunawayContinuation trades (2026-08-25..09-02),
scored on whether the entry ever went 5% green:
  · adx            AUC 0.47   green 41.7  vs never-green 41.15
  · bb_width_pct   AUC 0.50   0.98 vs 0.98
  · session_frac   AUC 0.50   0.79 vs 0.77
  · gex            AUC 0.51
The strongest separation among SIXTEEN vectors was 0.07 from chance, while a
vector of PURE NOISE reached 0.19 in the tool's own fixture. The market STATE at
the fill carries no information about direction. So this measures the PATH: how
price got here, not where it is.

🔑 FOUR COMPONENTS, ALL PATH PROPERTIES, ALL SCALE-FREE:
  1. EFFICIENCY  — net displacement / total distance travelled. A trend covers
     ground ONCE; a grind covers it five times. `character.py` already holds
     this idea (MIN_WINDOW_BARS = 20 exists because "below this an efficiency
     ratio is noise") but never emits it: BANDS_SET is False, which is why
     every board reads `Character: inactive`.
  2. ACCEPTANCE  — the fraction of each bar's range the CLOSE sits in, on the
     trade's side. This is the operator's own doctrine as a measure: "wicks are
     tests & closes are acceptance." Repeated closes near the extreme is a
     trend; long wicks with mid-range closes is distribution.
  3. SHALLOWNESS — 1 - (deepest pullback / move so far). Shallow and shallowing
     is healthy; deepening is the trend rolling over.
  4. PACE        — displacement per bar against TRUE RANGE per bar. The
     normaliser: it makes a $713 QQQ comparable to a $7,700 SPX, and it is what
     the operator's "bars to the 50%" question is a special case of.

⚠️ THE WEIGHTS ARE A PRIOR AND SAY SO. Nothing here is fitted — the components
are recorded so `calibrate_trend_strength` can score each one against outcomes
over the existing sample, and the weights move on that evidence. Shipping a
number I invented as a gate is exactly what r208's category 3 forbids.

⚠️ AND IT REFUSES RATHER THAN GUESSING. Too few bars, a flat tape or a missing
field returns a `TrendStrength` with `score=None` and a stated `reason`. A
degenerate window scoring 0.0 would read as "flaccid" and silently veto trades
on missing data, which is the opposite of a loud failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ── the prior ───────────────────────────────────────────────────────────
# ⚠️ NOT A FIT. Weighted toward EFFICIENCY and ACCEPTANCE because those two
# measure the trend's own mechanics, while SHALLOWNESS and PACE describe its
# behaviour around them. Calibration decides whether that ordering survives.
W_EFFICIENCY = 0.35
W_ACCEPTANCE = 0.30
W_SHALLOWNESS = 0.20
W_PACE = 0.15

# Below this a path measure is noise, not a reading. Same reasoning and the
# same number as character.py's MIN_WINDOW_BARS, deliberately.
MIN_BARS = 8

# PACE is a ratio of displacement-per-bar to true-range-per-bar. 1.0 means the
# move advanced one full bar's range per bar, which is already a strong tape;
# the scale saturates there rather than letting one violent bar dominate.
PACE_SATURATION = 1.0


@dataclass
class TrendStrength:
    """A graded reading, or a refusal with a reason. Never a silent zero."""
    score:        Optional[float] = None   # 0..1 composite, None = no reading
    efficiency:   Optional[float] = None
    acceptance:   Optional[float] = None
    shallowness:  Optional[float] = None
    pace:         Optional[float] = None
    # r229 — recorded, NOT weighted. The composite is unchanged until the
    # calibration says which of these carries anything; adding an unproven
    # component to the score would move the gate on a guess.
    acc_slope:    Optional[float] = None
    acc_recent:   Optional[float] = None
    acc_delta:    Optional[float] = None
    acc_run:      Optional[float] = None
    fvg_respect:  Optional[float] = None
    fvg_tested:   int = 0
    bars:         int = 0
    reason:       str = ""
    parts:        dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.score is not None

    def line(self) -> str:
        if not self.ok:
            return f"trend strength: NO READING — {self.reason}"
        return (f"trend strength {self.score:.2f} "
                f"(eff {self.efficiency:.2f} acc {self.acceptance:.2f} "
                f"shal {self.shallowness:.2f} pace {self.pace:.2f}) "
                f"over {self.bars} bars")


def _rows(bars):
    """Accept a DataFrame or a sequence of mappings, uniformly.

    ⚠️ THE LIVE CALLER HAS A pandas DataFrame (`df_1m`) AND THE CALIBRATOR HAS
    sqlite ROWS. One code path must serve both or the calibration measures a
    different function than the one that trades — which is the whole reason
    this module is a pure function of bars.
    """
    if bars is None:
        return []
    if hasattr(bars, "itertuples"):          # pandas
        out = []
        for r in bars.itertuples(index=False):
            d = r._asdict() if hasattr(r, "_asdict") else dict(r._asdict())
            out.append(d)
        return out
    return [dict(b) for b in bars]


def _f(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    # ⚠️ NaN REJECTED EXPLICITLY. Every comparison against NaN is False, so a
    # NaN high would pass a `high > low` guard and poison the mean silently.
    return None if x != x else x


def measure(bars, direction: str, *, min_bars: int = MIN_BARS) -> TrendStrength:
    """Grade the path in `bars` for a `direction` of "long" or "short".

    `bars` are CLOSED 1-minute candles, oldest first, each with open/high/low/
    close. The caller decides the window — for the runaway that is the break
    bar through the 50% acceptance; for the ORB it is the break through now.
    """
    rows = _rows(bars)
    if len(rows) < min_bars:
        return TrendStrength(bars=len(rows),
                             reason=f"{len(rows)} bars, need {min_bars}")
    long_side = str(direction).lower() == "long"

    highs, lows, closes, trs = [], [], [], []
    prev_close = None
    for r in rows:
        h, l, c = _f(r.get("high")), _f(r.get("low")), _f(r.get("close"))
        if h is None or l is None or c is None or h < l:
            return TrendStrength(bars=len(rows),
                                 reason="a bar has an unusable high/low/close")
        highs.append(h)
        lows.append(l)
        closes.append(c)
        # true range, so a gap between bars counts as distance travelled
        tr = (h - l) if prev_close is None else max(
            h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)
        prev_close = c

    # ── 1. EFFICIENCY — net displacement over distance travelled ────────
    net = (closes[-1] - closes[0]) if long_side else (closes[0] - closes[-1])
    travelled = sum(abs(closes[i] - closes[i - 1]) for i in range(1, len(closes)))
    if travelled <= 0:
        # ⚠️ A TAPE THAT NEVER MOVED IS NOT A FLACCID TREND, IT IS NO TREND.
        # Returning 0.0 here would read as a measurement.
        return TrendStrength(bars=len(rows), reason="the tape did not move")
    efficiency = max(0.0, min(1.0, net / travelled))

    # ── 2. ACCEPTANCE — where the CLOSE sits in each bar's range ────────
    # 🔑 "Wicks are tests, closes are acceptance", as a number.
    clvs = []
    for h, l, c in zip(highs, lows, closes):
        rng = h - l
        if rng <= 0:
            continue                      # a doji bar says nothing either way
        clvs.append(((c - l) / rng) if long_side else ((h - c) / rng))
    if not clvs:
        return TrendStrength(bars=len(rows), reason="every bar had zero range")
    acceptance = sum(clvs) / len(clvs)

    # ── 2b. ACCEPTANCE TRAJECTORY — is it STILL happening? ──────────────
    # 🔑 OPERATOR, 2026-09-03: "a continuing degree of acceptance may be the
    # right signal." The MEAN was the strongest component in the first
    # calibration (AUC 0.63/0.62/0.58 across windows) and it is still blind to
    # DIRECTION: 0.4 building to 0.7 and 0.7 decaying to 0.4 average the same,
    # and they are opposite tapes. That blindness is a candidate explanation
    # for why nothing cleared the noise floor.
    # ⚠️ THREE EXPRESSIONS, RECORDED SEPARATELY, because they disagree
    # informatively: a late collapse after a strong start still slopes up.
    # 🔑 AND THE SAME MEASURE READ BACKWARD IS EXHAUSTION. If continuing
    # acceptance is strength, DECAYING acceptance is the exhaustion signal —
    # one measure in two directions rather than two meters (MOM.1 stage 5).
    n_c = len(clvs)
    acc_slope = None
    if n_c >= 4:
        xm = (n_c - 1) / 2.0
        ym = acceptance
        den = sum((i - xm) ** 2 for i in range(n_c))
        if den > 0:
            acc_slope = sum((i - xm) * (v - ym)
                            for i, v in enumerate(clvs)) / den
    # recent vs whole — "is it still happening", the shape that flags a
    # reversal while the earlier bars still look good
    _tail = max(3, n_c // 4)
    acc_recent = (sum(clvs[-_tail:]) / _tail) if n_c >= 6 else None
    acc_delta = (None if acc_recent is None else acc_recent - acceptance)
    # consecutive count — closest to the doctrine: acceptance REPEATED is a
    # decision, acceptance once is a bar
    _run = 0
    for v in reversed(clvs):
        if v >= 2.0 / 3.0:
            _run += 1
        else:
            break
    acc_run = _run / n_c

    # ── 2c. FVG CONTINUATION — did pullbacks fill an imbalance and go on? ─
    # 🔑 OPERATOR: "whether pullbacks filled at FVG and continued onwards." The
    # first component that measures WHY a pullback ended rather than how deep
    # it was. A pullback that fills an imbalance and continues is MECHANICAL;
    # one that fills it and keeps going is DISTRIBUTION.
    # ⚠️ DETECTED FROM THE WINDOW'S OWN BARS, not read from
    # `trades.entry_snapshot`. entry_snapshot holds the gaps at the fill and
    # would be excellent corroboration, but reading it would make `measure()`
    # depend on a trade row — and its purity as a function of bars is exactly
    # what lets the calibrator score the SAME code that trades.
    # 🔴 BACKWARD-LOOKING BY CONSTRUCTION. Whether the pullback AFTER entry
    # filled and continued is a post-entry fact: it would calibrate beautifully
    # and be unusable as a gate. This asks only about gaps already COMPLETED
    # inside the window, which is what a decision at the fill can actually see.
    fvg_tested = fvg_held = 0
    for i in range(2, len(rows)):
        if long_side:
            gap_lo, gap_hi = highs[i - 2], lows[i]      # bullish imbalance
        else:
            gap_lo, gap_hi = highs[i], lows[i - 2]      # bearish imbalance
        if gap_hi <= gap_lo:
            continue                                    # no gap on these three
        extreme = max(highs[:i + 1]) if long_side else min(lows[:i + 1])
        for j in range(i + 1, len(rows)):
            touched = (lows[j] <= gap_hi) if long_side else (highs[j] >= gap_lo)
            if not touched:
                continue
            fvg_tested += 1
            # continuation = a LATER bar exceeded the pre-pullback extreme
            went_on = any((highs[k] > extreme) if long_side
                          else (lows[k] < extreme)
                          for k in range(j + 1, len(rows)))
            fvg_held += 1 if went_on else 0
            break
    # ⚠️ None WHEN NO GAP WAS TESTED — not 0.0. "No imbalance was retested" and
    # "every retest failed" are different facts, and scoring the first as the
    # second would read a clean trend as a broken one.
    fvg_respect = (fvg_held / fvg_tested) if fvg_tested else None

    # ── 3. SHALLOWNESS — 1 - deepest pullback / move so far ─────────────
    # ⚠️ MEASURED AGAINST THE MOVE AT THAT MOMENT, not the final move: a
    # pullback is only deep relative to what had been gained when it happened.
    # 🔴 THE RUNNING EXTREME MUST EXCLUDE THE BAR BEING MEASURED. The first
    # draft did `run = max(run, high_i)` and then measured `low_i` against it,
    # so every bar's own low was compared to its own high — on bar one the
    # "gain" is a few cents and the ratio explodes, which clamped SHALLOWNESS
    # to 0.00 for a tape with no pullback at all. The fixture caught it: a
    # ripper scored the same 0.00 as a rollover, so the component was dead
    # weight contributing nothing but noise to the composite.
    # ⚠️ A PULLBACK IS A LATER BAR'S LOW AGAINST AN EARLIER HIGH. That is what
    # makes it a pullback rather than a bar's own range.
    # 🔴 NORMALISED BY THE NET MOVE, NOT BY THE RUNNING GAIN. Two drafts got
    # this wrong and the fixture caught both: measuring a bar's low against a
    # running max that INCLUDED that bar was self-referential, and then
    # dividing by the gain SO FAR made the ratio explode early — in a rising
    # tape every bar's low sits below the previous bar's high, which is normal
    # overlap and not a pullback, but against a two-cent running gain it reads
    # as a 200% retracement. A ripper scored 0.00, identical to a rollover, so
    # the component contributed nothing but noise to the composite.
    # 🔑 THE MEANINGFUL QUANTITY IS MAXIMUM ADVERSE EXCURSION WITHIN THE LEG
    # OVER WHAT THE LEG DELIVERED: how much heat the trend took relative to
    # the ground it actually made. Stable from the first bar, and the same
    # shape as the MAE/MFE measure the excursion reports already use.
    worst = 0.0
    run = closes[0]
    for i in range(len(rows)):
        excursion = (run - lows[i]) if long_side else (highs[i] - run)
        if excursion > 0:
            worst = max(worst, excursion / net)
        # advance the extreme only AFTER this bar is measured against it
        run = max(run, highs[i]) if long_side else min(run, lows[i])
    shallowness = max(0.0, min(1.0, 1.0 - worst))

    # ── 4. PACE — displacement per bar against true range per bar ──────
    atr_bar = sum(trs) / len(trs)
    if atr_bar <= 0:
        return TrendStrength(bars=len(rows), reason="zero average true range")
    pace_raw = (net / len(rows)) / atr_bar
    pace = max(0.0, min(1.0, pace_raw / PACE_SATURATION))

    score = (W_EFFICIENCY * efficiency + W_ACCEPTANCE * acceptance
             + W_SHALLOWNESS * shallowness + W_PACE * pace)
    return TrendStrength(
        score=round(score, 4), efficiency=round(efficiency, 4),
        acceptance=round(acceptance, 4), shallowness=round(shallowness, 4),
        acc_slope=None if acc_slope is None else round(acc_slope, 5),
        acc_recent=None if acc_recent is None else round(acc_recent, 4),
        acc_delta=None if acc_delta is None else round(acc_delta, 4),
        acc_run=round(acc_run, 4),
        fvg_respect=None if fvg_respect is None else round(fvg_respect, 4),
        fvg_tested=fvg_tested,
        pace=round(pace, 4), bars=len(rows), reason="",
        parts={"net": round(net, 4), "travelled": round(travelled, 4),
               "atr_bar": round(atr_bar, 4), "worst_retrace": round(worst, 4),
               "pace_raw": round(pace_raw, 4)})
