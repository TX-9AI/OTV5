"""
strategy/relaxed.py  v4.0
The universal relaxed-entry toggle. Paper-only, loud, and it never relaxes a
gate that makes a trade impossible to win.

v4.0  2026-08-20  Built at the OTV4 split. Operator's spec.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

════════════════════════════════════════════════════════════════════════════
WHAT IT IS FOR
════════════════════════════════════════════════════════════════════════════
Operator, 2026-08-20: *"a toggle for relaxed entry criteria ... it'll get the
trades firing so we can watch the sequence and have logs of how the trades are
firing, make sure that there's no errors, we can debug that way. And it also
gives an opportunity - presumably these won't be ideal trades - so we can watch
our stops work as intended."*

Two jobs, both real:
  1. **SURFACE PLUMBING ERRORS NO UNIT TEST FINDS.** v3's `ctx` NameError
     stopped every box trading and `import main` passed the whole time; the TCS.4
     `is_trend_credit` field crash-looped NFLX every 15 seconds. **Both were
     found by a trade attempting to fire, not by a test.** A strategy that never
     fires is a strategy whose failure modes are all still ahead of it.
  2. **EXERCISE THE STOPS ON DELIBERATELY MEDIOCRE ENTRIES.** The exits are the
     measured winners (orb_trail_stop 96% / 85 trades / +$30,696, worst -$16)
     and they deserve to be watched on trades that actually test them.

════════════════════════════════════════════════════════════════════════════
THREE RULES, AND EACH EXISTS BECAUSE OF A SPECIFIC PAST FAILURE
════════════════════════════════════════════════════════════════════════════
**1. IT IS LOUD, AND THE POPULATION STAYS SEPARABLE FOREVER.**
Every relaxed signal logs `RELAXED` and carries `relaxed_entry=1` on the trade
record. ⚠️ **DATA COLLECTED UNDER RELAXED CRITERIA MUST NEVER VALIDATE THE TIGHT
THRESHOLDS.** That is how a debug mode silently becomes a measurement - and this
project has already been bitten by a stand-in that was never labelled as one:
`oi_proxy = 1000 * gamma` made GEX a gamma-squared surface for the life of v3
because nothing ever said "this is not real data".

**2. THREE CATEGORIES OF GATE, AND THE TOGGLE ONLY EVER TOUCHES THE FIRST.**
Operator, 2026-08-20: *"some of the parts of the setups are requirements and
cannot be relaxed because they are foundational."* That is a THIRD category, not
a synonym for feasibility, and collapsing them loses the distinction that makes
this toggle safe:

  **SELECTION**    - measured preferences. The window, the depth band, the age,
                     the distance. Loosening these produces a WORSE example of
                     the same trade, which is exactly what a debug session
                     wants. **Relaxable.**
  **FOUNDATIONAL** - the conditions that define the setup's IDENTITY. Relax one
                     and it stops being this trade at all:
                       · sweep spread - a NAMED pool, RECLAIMED, NOT invalidated,
                         price already on the profitable side of the boundary
                       · runaway      - the 50% TP level HELD
                       · butterfly    - PINNING, with the apex ON the pin
                     Relax the reclaim and you are selling into a level price is
                     still through - not a loose version of the setup, **a
                     different and much worse one.** **NEVER.**
  **FEASIBILITY**  - the vetoes that make a trade unwinnable regardless of how
                     good it looks. **NEVER.**

⚠️ EVERY STRATEGY MUST DECLARE ALL THREE IN ITS HEADER. A reader - or an
adversarial audit - should see which gate is which without reverse-engineering
it from which ones happen to be wrapped in `relaxed.widen()`. A new strategy
whose author has not made the distinction is a new strategy that will relax
something foundational.

**AND ON FEASIBILITY SPECIFICALLY:**
Some gates say *"this setup is not ideal"*. Others say *"this trade CANNOT
WIN"*. Only the first kind may be relaxed.
⚠️ THE ATR FLOOR IS NOT NEGOTIABLE. `tests/magnitude_estimator.py`, 52,949 bars:
below **0.05% ATR** the required move was reached on **0%** of bars - not
rarely, **not once in 5,517 observations**. Relaxing it produces trades that
cannot pay regardless of how good the entry looks, which teaches nothing about
stops and pollutes the log with noise. Same for a crossed or missing quote.

**3. PAPER ONLY, GUARDED RATHER THAN TRUSTED.**
`is_allowed()` refuses when the box is live, whatever the config says. A
convention that relies on remembering to switch it off is a convention that will
one day not be remembered - and v3's own doctrine is blunt about this: **a manual
pre-shutdown step will never happen.**
"""

import logging
import os

logger = logging.getLogger(__name__)


def _flag(name: str, default: str = "0") -> bool:
    return str(os.environ.get(name, default)).strip().lower() in ("1", "true", "yes", "on")


def is_live() -> bool:
    """True when this box is trading real money. Fails CLOSED - unknown is live.

    ⚠️ THE DEFAULT IS THE DANGEROUS ANSWER, DELIBERATELY. If the live flag
    cannot be read, this returns True and relaxed entries are refused. A
    misconfigured box that trades relaxed setups with real money is a far worse
    outcome than one that declines to fire during a debug session.
    """
    # ⚠️ BOTH MUST AGREE, AND THE ENV VAR IS REQUIRED. A first draft returned
    # `not config.PAPER_TRADING` and passed the guard on a box that had never
    # asserted anything - the repo default satisfied it silently, which is the
    # same shape as a numeric default reading as measured data. **The operator
    # must state paper explicitly for relaxed entries to be permitted**, and the
    # config must agree.
    env_paper = _flag("OT_PAPER_TRADING")
    cfg_paper = None
    try:
        import config
        cfg_paper = getattr(config, "PAPER_TRADING", None)
    except Exception:                                          # noqa: BLE001
        cfg_paper = None
    if env_paper and cfg_paper is not False:
        return False
    return True


def is_allowed() -> bool:
    """Is relaxed entry permitted right now? Config AND paper-mode, both."""
    if not _flag("OT_RELAXED_ENTRY"):
        return False
    if is_live():
        logger.warning("RELAXED ENTRY REQUESTED BUT THIS BOX IS LIVE - refused. "
                       "Relaxed criteria exist to exercise plumbing and stops "
                       "on paper, not to loosen gates against real money.")
        return False
    return True


_ANNOUNCED = False


def announce_once():
    """Say it at startup. A mode this consequential should never be discovered."""
    global _ANNOUNCED
    if _ANNOUNCED or not is_allowed():
        return
    _ANNOUNCED = True
    logger.warning("=" * 70)
    logger.warning("RELAXED ENTRY CRITERIA ARE ACTIVE (paper only).")
    logger.warning("  Selection gates are loosened to get trades FIRING so the")
    logger.warning("  sequence can be watched, plumbing errors surfaced, and the")
    logger.warning("  stops exercised on deliberately mediocre entries.")
    logger.warning("  FEASIBILITY vetoes are NOT relaxed - a trade that cannot")
    logger.warning("  pay teaches nothing. Every signal is tagged relaxed_entry=1")
    logger.warning("  and this population must never validate a tight threshold.")
    logger.warning("=" * 70)


def widen(value: float, factor: float = 2.0, *, floor: float = None,
          cap: float = None, name: str = "") -> float:
    """Loosen a SELECTION bound. Returns it unchanged when relaxed is off.

    `floor` and `cap` are the limits past which loosening stops being selection
    and starts being feasibility - pass them and they are respected even in
    relaxed mode.
    """
    if not is_allowed():
        return value
    out = value * factor
    if floor is not None:
        out = max(out, floor)
    if cap is not None:
        out = min(out, cap)
    if name:
        logger.debug("[relaxed] %s: %.4f -> %.4f", name, value, out)
    return out


def window(earliest: str, latest: str,
           relaxed_earliest: str = "09:45",
           relaxed_latest: str = "15:30") -> tuple:
    """Widen a time window. Unchanged when relaxed is off.

    ⚠️ NOT THE WHOLE SESSION EVEN WHEN RELAXED. 09:30-09:45 is the opening
    auction's residue - quotes are wide and unstable, and a fill there measures
    the auction rather than the strategy. 15:30+ collides with the 15:40 flatten
    ladder and the 15:45 hard close, so a trade opened then is closed before it
    can be judged.
    """
    if not is_allowed():
        return earliest, latest
    return (min(earliest, relaxed_earliest), max(latest, relaxed_latest))


def tag(signal):
    """Mark a signal as relaxed. Call on EVERY signal a relaxed gate admitted.

    ⚠️ THE TAG IS THE WHOLE POINT OF RULE 1. An untagged relaxed trade is
    indistinguishable from a real one in the trade book, and six weeks later
    somebody fits a threshold to a population half of which was deliberately
    junk.
    """
    if signal is None or not is_allowed():
        return signal
    try:
        signal.relaxed_entry = 1
        st = getattr(signal, "setup_type", "") or ""
        if not st.endswith("_relaxed"):
            signal.setup_type = f"{st}_relaxed"
    except Exception:                                          # noqa: BLE001
        pass
    return signal
