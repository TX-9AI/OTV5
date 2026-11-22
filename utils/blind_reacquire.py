"""
utils/blind_reacquire.py  v5.0
v5.0  2026-11-22  OTV5 r146 (BLND.1, partial; the before-cash audit 2026-11-22 F3) — new. AFTER A BLIND EPISODE, NO
      OPENING ORDER ON THE TICK THAT FIRST SEES AGAIN; ENTRIES ARE ELIGIBLE FROM THE NEXT TICK, ON CURRENT 1m BARS. The
      operator, 2026-09-30: "On blind, I agree. The plan should have to reacquire a valid trigger after sight restored."
      Approved 2026-11-22 ("Yes, we need that."), then the timing, 2026-11-22: "Does it really need a full minute if the
      plans refresh every 15 second tick? I think 1 full tick after a restore should be eligible for a fire if the entry
      still qualifies."
      2026-09-29: the feed was dead 09:30:10-09:37:52 and a Breakout entered 09:38:04, on the first tick that saw again,
      on a trigger that formed on the 09:30 bar while the bot was blind. Before r146 entries were held only WHILE blind
      (main._blind_tick ends the tick), so the first tick with sight could open on a frame it had never watched.

      THE EPISODE is main's FeedBlind episode (r74 BLIND.1): _blind_tick calls note_blind(now) on every blind tick;
      _blind_clear calls note_sight(now, tick) on the first tick that sees again (main_loop's tick number).
      THE HOLD (hold(now, tick, df_1m), asked once a tick by main.attempt_new_entry):
        · still blind (an episode with no sight yet)                       -> held;
        · the sighted tick itself (tick <= the sight tick)                 -> held: one full tick with sight first;
        · a later tick whose 1m frame (ctx["df_1m"], the frame the plans read) does not yet hold the LAST COMPLETED
          MINUTE as its newest closed bar                                  -> held until it does (the feed's
          reconnect replay normally lands within a flush or two, so this is normally no extra tick);
        · otherwise the episode ends: ONE "entries eligible" line, and the plans are asked on current data - a fire
          only if the plan still qualifies there (its normal evaluation; no new rule).
      Example (15 s ticks): sight on the 09:38:04 tick -> held that tick; the 09:38:19 tick with the 09:37 bar in the
      frame -> eligible. Both order choke points (entry_engine.enter, main._execute_condor_leg) call hold(now) with no
      tick: they refuse while an episode stands (attempt_new_entry ends it first on the tick it releases). Exits never
      read it. Paper and live alike. ZERO broker calls: the state is this module's memory and the frame is the one the
      tick already read. No config key, no env read. A new blind episode inside the hold starts over.

      RESTART (WORKING_AGREEMENT 37 composes, not duplicated): the state is in memory, so a process that restarts
      mid-episode starts clean; if it is still blind its first RTH tick raises FeedBlind and opens a NEW episode here,
      held again on sight. A process that restarts inside the hold (one tick, normally) loses it; what it keeps is WA 37:
      the ORB engine's tape reach-back replays the session from 09:30 and CONSUMES any trigger that completed while the
      process was down, which covers every ORB trigger (Runaway and the Hunt read the engine). OGAP's own stale rule
      (ogap_plan: a signal first seen after its fill minute is refused) and PARK's 11:01-11:03 window are clock rules.

      KNOWN LIMIT (recorded in BACKLOG BLND.1, not built here): this resets no plan's latch. A plan that latched an
      armed state before or during the episode can still fire on the first eligible tick if it still qualifies; resetting
      each plan's latch is the separate delivery the ruling also asked for.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from utils.time_utils import _epoch_s

logger = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")
BAR_S = 60.0
GATE = "blind_reacquire"      # the plan-board gate name (query.py labels it REACQUIRING)

# One episode at a time: began / last_blind (first and last blind tick), sight (when the first tick saw again) and
# sight_tick (its tick number). None = no episode, or its hold has ended.
_EP: Optional[dict] = None


def _hms(t) -> str:
    try:
        return datetime.fromtimestamp(float(t), ET).strftime("%H:%M:%S")
    except Exception:                                          # noqa: BLE001
        return "?"


def _hm(t) -> str:
    try:
        return datetime.fromtimestamp(float(t), ET).strftime("%H:%M")
    except Exception:                                          # noqa: BLE001
        return "?"


def last_completed_minute(now: float) -> float:
    """Epoch of the START of the last 1m bar that has ended by `now` (09:38:19 -> 09:37:00)."""
    t = float(now)
    return (t // BAR_S) * BAR_S - BAR_S


def newest_closed_start(df_1m, now: float) -> Optional[float]:
    """Epoch start of the newest row of `df_1m` that has closed by `now` (start + 60 <= now); None when there is none
    or the frame is unreadable. Reads the last few rows only. Never raises."""
    try:
        if df_1m is None or len(df_1m) == 0:
            return None
        t = float(now)
        for ts in reversed(list(df_1m.index[-5:])):
            s = _epoch_s(ts)
            if s is not None and s + BAR_S <= t:
                return s
        return None
    except Exception:                                          # noqa: BLE001
        return None


def bars_current(df_1m, now: float) -> bool:
    """True when the frame's newest closed 1m bar is the last completed minute: the blind gap is filled up to now."""
    s = newest_closed_start(df_1m, now)
    return s is not None and s >= last_completed_minute(now) - 1e-6


def note_blind(now: float) -> None:
    """A blind tick. Opens an episode (or a new one, if the last one's sight had already returned). Never raises."""
    global _EP
    try:
        t = float(now)
        if _EP is None or _EP.get("sight") is not None:
            _EP = {"began": t, "last_blind": t, "sight": None, "sight_tick": None}
        else:
            _EP["last_blind"] = max(float(_EP["last_blind"]), t)
    except Exception:                                          # noqa: BLE001
        pass


def note_sight(now: float, tick: Optional[int] = None) -> None:
    """The first tick that sees again. Arms the hold and says so once. Never raises."""
    try:
        if _EP is None or _EP.get("sight") is not None:
            return
        _EP["sight"] = float(now)
        _EP["sight_tick"] = tick
        logger.warning("[entry-gate] BLND.1: blind episode %s-%s ET ended (sight at %s); no opening order on any setup "
                       "this tick - entries are eligible from the next tick once the 1m bars are current",
                       _hms(_EP["began"]), _hms(_EP["last_blind"]), _hms(_EP["sight"]))
    except Exception:                                          # noqa: BLE001
        pass


def hold(now: float, tick: Optional[int] = None, df_1m=None) -> str:
    """'' when an opening order may be placed at `now`; otherwise the reason (one sentence naming the episode).

    attempt_new_entry passes the tick number and the tick's 1m frame and is the only caller that can END the hold;
    the order choke points pass neither and refuse while an episode stands. Never raises: an internal fault -> ''
    (the blind tick itself already holds every entry while blind)."""
    global _EP
    try:
        ep = _EP
        if ep is None:
            return ""
        t = float(now)
        epi = "the blind episode %s-%s ET" % (_hms(ep["began"]), _hms(ep["last_blind"]))
        if ep.get("sight") is None:
            return ("blind since %s ET - no opening order until sight returns and one full tick has seen (BLND.1)"
                    % _hms(ep["began"]))
        if tick is None:
            return "reacquiring after %s (sight %s): the next tick decides (BLND.1)" % (epi, _hms(ep["sight"]))
        st = ep.get("sight_tick")
        if st is None or int(tick) <= int(st):
            return ("reacquiring after %s (sight %s): this is the tick that first sees again; entries are eligible "
                    "from the next tick (BLND.1)" % (epi, _hms(ep["sight"])))
        if not bars_current(df_1m, t):
            s = newest_closed_start(df_1m, t)
            return ("reacquiring after %s (sight %s): the 1m frame's newest closed bar is %s, not the last completed "
                    "minute %s - held until the feed has filled the gap (BLND.1)"
                    % (epi, _hms(ep["sight"]), _hm(s) if s is not None else "none",
                       _hm(last_completed_minute(t))))
        _EP = None
        logger.info("[entry-gate] BLND.1: entries eligible at %s ET - one full tick has seen since %s and the 1m bars "
                    "are current (newest closed bar %s)", _hms(t), epi, _hm(last_completed_minute(t)))
        return ""
    except Exception:                                          # noqa: BLE001
        return ""


def state() -> Optional[dict]:
    """A copy of the episode (tests, status). None when nothing holds."""
    return dict(_EP) if _EP is not None else None


def reset() -> None:
    """Tests only."""
    global _EP
    _EP = None
