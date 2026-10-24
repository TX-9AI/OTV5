"""
analysis/character.py  v4.1
The tape's CHARACTER — two measured axes, a state, and a duration.

v4.1  2026-08-23  F4: `persistence()` computed an INTRABAR WICK RATIO, not
directional persistence — rv_cc/rv_parkinson are both per-bar volatility
estimators. Replaced by `efficiency()` (net travel / total travel across the
window); the old ratio survives as `close_capture()`, a corroborator. And
BANDS_SET=False: the axes are recorded, NO STATE is emitted, because the old
bands were calibrated against the wrong quantity.

v4.0  2026-08-25  Operator's design. Named CHARACTER deliberately: if the idea
of describing the tape is revived it does so under a word that cannot be
mistaken for the retired artifact.

    trending · ranging · compressing · volatile

🔴 CHARACTER IS A STATE WITH DURATION. AN EVENT IS A MOMENT.
Operator, 2026-08-25: "a sweep is an event, not a character. Breakouts are
events, not character. Volatile is the character."

⚠️ THE OLD SYSTEM COLLAPSED THIS AND IT COST REAL ANALYSIS. SWEEP_REVERSAL and
BREAKOUT_VOLATILE sat in the same six-way argmax as RANGING and COMPRESSION, so
an EVENT and a STATE competed for one slot — SWEEP ended at 0.4% of live ticks,
effectively not participating. And the acceptance work hit the same wall from
the other side: comparing a single-event tag to a session-modal label is a
category error.

**They coexist, and that is informative.** A sweep happens DURING a ranging
tape; a breakout happens OUT OF a compressed one. Events already have homes
(level_ledger, plan_ledger, prints). Character gets its own and displaces
nothing.

🔴 NO SCORING. NO CONVICTION. NO CONSENSUS.
Operator's explicit boundary. **The specific temptation to refuse: combining
the two axes into one strength number is `_combine()` reappearing under a new
name.** The axes stay separate and are reported separately. Scoring comes
later, fitted on derivatives with an honest discretionary split, and even then
it will address POSITION SIZE — not gates.

⚠️ TWO AXES, NOT FOUR BUCKETS. A market can be trending AND compressing (an
orderly grind) or ranging AND volatile (a violent chop). Four exclusive labels
cannot express that; the state name below is a CONVENIENCE READING of the two
axes, never the primitive.

⚠️ NEVER A BOOLEAN VETO. The v3 grammar was multiplicative, so one veto at zero
annihilated a score and DESTROYED THE ORDERING — 41.9% of ticks had nothing to
rank. Everything here is continuous.

🔑 ADX AND ATR RUN PARALLEL, NOT FEEDING — operator's ruling.
They map naturally onto the axes (ADX to persistence, ATR to volatility) and
are RECORDED ALONGSIDE so a study can ask whether they agree. **Blending them
in would make agreement true by construction**, which is the circularity WA §31
exists to prevent. There is also a live reason for caution: ADX swung 16 → 48
on the same symbols across ticks on 2026-08-21, and whether that is market or
Wilder-window artifact is UNSETTLED. Feeding an unresolved wobble into
character would manufacture the churn the acceptance gate exists to catch.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Axis boundaries. Provisional and flagged as such. ────────────────────────
# ⚠️ THESE ARE STARTING POINTS FOR A MEASUREMENT, NOT FITTED PARAMETERS. The
# acceptance gate (1-3 changes per symbol-day, the operator's 20-year prior) is
# what says whether they are right. Do NOT tune them to produce a pleasing
# number — that is fitting, and it is what the old system did.
# 🔴 BANDS_SET = False — THE AXES ARE RECORDED, NO STATE IS EMITTED.
# Operator's ruling 2026-08-23, after the r75 measure was found to compute the
# wrong quantity: **the old bands were calibrated against that wrong quantity,
# so they carry no information about this one.** Setting new ones now would be
# inventing numbers; the discipline is the same one that governs strategy
# ramps — a baseline where none exists is judgment, but a fit needs data.
# ⚠️ SO `read_character` RETURNS None UNTIL A SESSION OF REAL EFFICIENCY VALUES
# EXISTS TO SET BANDS FROM. The ledger still records both axes on every tick
# the engine runs, which is exactly the sample needed. Flip this to True in the
# same commit that replaces the four numbers below with measured ones.
BANDS_SET = False

MIN_WINDOW_BARS = 20      # below this an efficiency ratio is noise

PERSIST_TREND = 0.62      # PROVISIONAL — calibrated against the WRONG measure
PERSIST_RANGE = 0.38      # PROVISIONAL — same
VOL_EXPAND = 1.25         # short-window vol vs its own baseline
VOL_COMPRESS = 0.80

# Hysteresis. From the v3 F7 result: protect-below-hold ALONE landed 3.3
# switches/symbol-day with NO dwell and NO tuning, validated 20.8 -> 4.2 on
# real tape. ⚠️ DWELL IS DELIBERATELY ABSENT — dwell 8+ started deleting real
# genuine state changes, and adding it is fitting.
DISPLACE_MARGIN = 0.10    # a challenger must clear the incumbent's band by this


def efficiency(closes) -> Optional[float]:
    """Directional persistence in [0, 1]: NET travel over TOTAL travel.

    Kaufman efficiency: |last - first| / Σ|closeᵢ - closeᵢ₋₁| across the window.
    A clean one-way move approaches 1.0; a path that returns to where it began
    approaches 0.0 no matter how far it wandered.

    🔴 THIS REPLACES A MEASURE THAT COMPUTED A DIFFERENT QUANTITY ENTIRELY.
    The r75 version divided realised_vol_cc by realised_vol_parkinson and
    called it net-travel-over-total-travel. **Both are per-bar VOLATILITY
    ESTIMATORS** — their ratio says how much of each BAR'S RANGE the close
    captured, i.e. an intrabar wick ratio, which is silent about direction
    across bars. Fable's audit demonstrated it: a +0.05%/bar trend scored 1.00,
    a random walk 0.91, and **perfectly alternating chop also scored 1.00 and
    read as "trending"**, where true efficiency is 0.30 / 0.42 / 0.00.

    🔑 THE LESSON, and it is mine: I described the right quantity in the
    docstring and implemented a different one, then built an acceptance gate on
    top of it. **A comment asserting a measurement is not a measurement** — the
    ratio was plausible, dimensionally innocent, and wrong.

    ⚠️ rv_cc/rv_parkinson ARE STILL RECORDED, as a corroborator. They measure
    something real (close capture within the bar); they do not measure this.

    ⚠️ None, NEVER 0.5, when the window is too short. A midpoint would assert
    "equally trending and ranging" — a real reading, and a completely different
    claim from "we could not measure".
    """
    try:
        xs = [float(c) for c in closes if c is not None]
    except (TypeError, ValueError):
        return None
    if len(xs) < MIN_WINDOW_BARS:
        return None
    total = sum(abs(xs[i] - xs[i - 1]) for i in range(1, len(xs)))
    if total <= 0:
        return None                       # a flat window has no direction
    return max(0.0, min(1.0, abs(xs[-1] - xs[0]) / total))


def close_capture(rv_cc: Optional[float],
                  rv_parkinson: Optional[float]) -> Optional[float]:
    """How much of each bar's RANGE the close captured. A CORROBORATOR.

    ⚠️ THIS WAS `persistence()` UNTIL r85 AND IT IS NOT PERSISTENCE. Kept
    because it measures something real and is cheap, and recorded beside the
    axes so a study can ask whether it agrees. It must never be read as
    direction.
    """
    if rv_cc is None or rv_parkinson is None:
        return None
    if rv_parkinson <= 0:
        return None
    r = float(rv_cc) / float(rv_parkinson)
    return max(0.0, min(1.0, r))


def volatility_state(rv_now: Optional[float],
                     rv_baseline: Optional[float]) -> Optional[float]:
    """Volatility RELATIVE TO ITS OWN RECENT BASELINE. None if unmeasurable.

    ⚠️ RELATIVE, NOT ABSOLUTE, AND THAT IS THE POINT. TSLA at 45% annualised is
    calm for TSLA; UNH at 45% is a crisis. An absolute threshold would label
    every high-beta name permanently volatile and every index permanently
    compressed, which is a statement about the symbol, not the tape.
    """
    if rv_now is None or rv_baseline is None or rv_baseline <= 0:
        return None
    return float(rv_now) / float(rv_baseline)


def read_character(persist: Optional[float],
                   vol_ratio: Optional[float]) -> Optional[str]:
    """A convenience NAME for the two axes. NEVER the primitive.

    ⚠️ THE AXES ARE THE MEASUREMENT; THIS IS A READING OF THEM. Anything that
    needs nuance reads the axes. The name exists so a human glancing at
    status.py gets one word.

    ⚠️ VOLATILE OUTRANKS THE PERSISTENCE READ, deliberately: a violently
    expanding tape is volatile whether or not it is going anywhere, and that is
    the operator's own usage — "volatile is the character".
    """
    # 🔴 NO STATE UNTIL THE BANDS ARE DERIVED. See BANDS_SET above.
    if not BANDS_SET:
        return None
    if persist is None and vol_ratio is None:
        return None
    if vol_ratio is not None and vol_ratio >= VOL_EXPAND:
        return "volatile"
    if vol_ratio is not None and vol_ratio <= VOL_COMPRESS:
        return "compressing"
    if persist is None:
        return None
    if persist >= PERSIST_TREND:
        return "trending"
    if persist <= PERSIST_RANGE:
        return "ranging"
    # Between the bands is a real, nameless middle. ⚠️ IT IS NOT FORCED INTO A
    # BUCKET — the old grammar's argmax always produced a winner even when
    # there was nothing to choose between, and that is how a near-random label
    # got traded.
    return None


def qualifies_to_displace(incumbent: Optional[str], challenger: Optional[str],
                          persist: Optional[float],
                          vol_ratio: Optional[float]) -> bool:
    """Hold the incumbent unless the challenger CLEARLY qualifies.

    🔴 THE v3 F7 LESSON, TRANSPLANTED. That engine had a protected branch and
    an UNPROTECTED one: below the hold threshold it took bare argmax every
    tick, no commit, no margin, no dwell — and that path produced **96.9% of
    all label switches**, with the median switch handing off between two
    near-zero beliefs. Applying protect-below-hold in BOTH branches landed
    3.3 switches/symbol-day, inside the operator's stated prior, from REMOVING
    A DEFECT rather than tuning a parameter.

    ⚠️ THE MARGIN IS ON THE AXIS, NOT ON A SCORE. There is no score here to
    compare. A challenger qualifies when the underlying measurement has moved
    clear of the boundary that produced the incumbent — so a value hovering ON
    a boundary cannot flip the state back and forth.
    """
    if challenger is None:
        return False
    if incumbent is None:
        return True
    if challenger == incumbent:
        return False
    if challenger == "volatile":
        return vol_ratio is not None and vol_ratio >= VOL_EXPAND + DISPLACE_MARGIN
    if challenger == "compressing":
        return vol_ratio is not None and vol_ratio <= VOL_COMPRESS - DISPLACE_MARGIN
    if challenger == "trending":
        return persist is not None and persist >= PERSIST_TREND + DISPLACE_MARGIN
    if challenger == "ranging":
        return persist is not None and persist <= PERSIST_RANGE - DISPLACE_MARGIN
    return False
