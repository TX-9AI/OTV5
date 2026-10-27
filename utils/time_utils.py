"""
utils/time_utils.py  v5.1
v5.1  2026-10-27  OTV5 r44 (BAR.1) — THE LAST CLOSED BAR IS FOUND BY TIME, NOT BY POSITION. closed_pos(df, now, bar_s) /
      closed_part(df, now, bar_s): every strategy, engine and exit read "the last CLOSED 1m bar" as iloc[-2], assuming
      the frame's newest row is the still-forming minute. On a tick in the first instant of a minute, before that
      minute's first row exists, the newest row IS the just-closed bar and iloc[-2] is one minute stale. META 2026-10-27
      (3f2b1372): Breakout short fired 10:10:00 ET on the 10:08 bar (close 623.01, "1m stop 623.57" = its high 623.5659)
      while 10:09 had already closed back inside the 623.20 edge (623.21). The newest row is closed when its start +
      bar_s <= now; then it is the answer (-1), else the row before it (-2, today's reading). A frame that is not live
      (its newest row started LIVE_FRAME_BARS = 3 bar-lengths or more before now: a stalled feed, a replay, a fixture -
      the width market_data already calls stale) and anything unreadable keep -2. GATE tests/check_last_closed_bar.py.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.8  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v4.7  2026-10-11  OTV4TEST r268 (DEP.12, MIRROR OF otv4 r478 044d837) - HALF DAYS. close_shift()/close_anchored()/past_close_anchor(): every
      close-anchored constant (written against a 16:00 bell) moves to the day's real bell, CLOSE SIDE ONLY. is_rth's close,
      is_hard_close_time (now takes an optional clock), current_session_label AND (fork-only) eod_close_due read it.
      entries_open closes at the bell minus config.HALF_DAY_ENTRY_LEAD_MIN (90 -> 11:30) on a listed early close; a full
      day is unchanged. The added functions are byte-identical to otv4's (WA 38.9 criterion 1).
v4.6  2026-10-03  OTV4TEST r220 (TIME.1) — parse_hm: the one HH:MM parser (a datetime-like or a string; None when unreadable or out of range). Eight plans carried private copies.
v4.5  2026-09-26  OTV4TEST r149 (EOD.1): HARD_CLOSE reads config.HARD_CLOSE_ET (was a literal 15:45 beside the config value); is_hard_close_time() opens at the first EOD action (15:45); eod_close_due() says when a given position's close begins — assignment risk 15:45, everything else 15:50.
v4.4  2026-09-07  r304 / DEP.9 - is_rth consults utils/market_calendar; a market holiday is no longer RTH. It failed toward TRADING on holidays, and entries_open wraps it.
v4.3  2026-08-24  r102: entries_open() defers to is_orb_complete() — the floor
      session_guard has enforced since v3 — instead of carrying a rival
      constant, and now carries the RTH test (a bare time floor is True all
      evening). is_rth/is_orb_complete take an optional clock.
v4.2  2026-08-24  r101: entries_open() — the 09:35 order gate (config
      ENTRY_OPEN_ET), fail-closed. Openings only; no exit path reads it.

v4.1  2026-08-21  r60: is_past_entry_cutoff + NO_ENTRY deleted with the
      unauthorized global cutoff.
Timezone, RTH session helpers, market-clock utilities.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

utils/time_utils.py — Timezone, RTH session helpers, and time utilities.
All bot logic operates in US/Eastern time to match market hours.
NO_ENTRY is READ FROM CONFIG (defect H). It was hardcoded
        as dtime(14, 0), so editing config could not move the global cutoff.
        It now derives from config.ORB_NO_ENTRY_AFTER_ET.
        NOT a behaviour change: ORB_NO_ENTRY_AFTER_ET is (14, 0), the same value
        that was hardcoded. Note the config constant this does NOT read is
        ORB_NO_ENTRY_AFTER_ET (11:00) — that is the ORB-scoped cutoff, a
        different rule. Wiring NO_ENTRY to it would silently move the global
        0DTE cutoff three hours earlier.
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
"""

import logging
from datetime import datetime, timezone, timedelta, time as dtime
from typing import Optional, Tuple
import pytz

from config import ORB_NO_ENTRY_AFTER_ET

logger = logging.getLogger(__name__)

ET = pytz.timezone("America/New_York")

# RTH boundaries (ET)
RTH_OPEN    = dtime(9, 30)
RTH_CLOSE   = dtime(16, 0)
from config import HARD_CLOSE_ET as _HCE, EOD_RESTING_AT_ET as _EOD_REST, EOD_LADDER_AT_ET as _EOD_LAD
HARD_CLOSE  = dtime(*_HCE)      # r149: the final cross, from config (was a literal 15:45)
ORB_END     = dtime(9, 35)   # ORB defined by 9:30–9:35 candle


# v3.8 — 2026-07-22 — is_hard_close_time() now opens the flatten window at
# FLATTEN_WINDOW_OPEN (15:40 ET), five minutes before the 15:45 cross, so the
# mark-limit phase has time to fill before the order is forced marketable.

from utils import market_calendar   # r304 — the ONE holiday source


def parse_hm(value):
    """(hour, minute) from a datetime-like or an 'HH:MM[:SS]' string; None when unreadable.

    r220 (TIME.1) — THE ONE PARSER. Eight plans each carried a private copy of
    this (`_hm` / `_hhmm`). A caller that gets None must treat the clock as
    unreadable and NOT trade: a window that cannot be checked is not open."""
    try:
        if hasattr(value, "hour") and hasattr(value, "minute"):
            return int(value.hour), int(value.minute)
        h, m = str(value).split(":")[:2]
        h, m = int(h), int(m)
        return (h, m) if (0 <= h <= 23 and 0 <= m <= 59) else None
    except (ValueError, AttributeError, TypeError):
        return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_et() -> datetime:
    return datetime.now(ET)


# ══ r44 (BAR.1) — THE LAST CLOSED BAR, BY TIME ══════════════════════════════
# A frame's index is each bar's START. The feed writes the forming minute as a
# row, so the newest row is USUALLY still forming and iloc[-2] is the last closed
# bar - but not in the first instant of a minute, before the new minute's first
# row exists: then the newest row has closed and iloc[-2] is a minute stale
# (META 2026-10-27 10:10:00 ET fired a Breakout on 10:08 while 10:09 had closed
# back inside the range). The newest row is closed once start + bar_s <= now.
# ⚠️ A FRAME THAT IS NOT LIVE KEEPS TODAY'S READING. When the newest row started
# LIVE_FRAME_BARS bar-lengths or more before `now` (the width data/market_data
# calls a stale frame: a stalled feed, a replay, a fixture) the boundary race
# this fixes cannot be told from a dead tape, so -2 stands, exactly as before.
LIVE_FRAME_BARS = 3.0


def _epoch_s(v) -> Optional[float]:
    """Epoch seconds of a datetime/Timestamp (naive is read as ET) or a number;
    None for anything else (a "HH:MM" string, None, NaT)."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, datetime):
        try:
            if v.tzinfo is None:
                v = ET.localize(v)
            out = v.timestamp()
            return None if out != out else float(out)
        except Exception:                                       # noqa: BLE001
            return None
    return None


def closed_pos(df, now=None, bar_s: float = 60.0) -> int:
    """r44 (BAR.1) — the position (-1 or -2) of the frame's newest CLOSED bar.

    -1 when the newest row has closed by `now` (start + bar_s <= now) on a live
    frame; -2 otherwise - the reading every caller made before r44. `now` is a
    datetime / Timestamp / epoch seconds; anything else (None, a "HH:MM" string)
    reads the clock, now_et(). bar_s is the frame's bar length (300 for 5m).
    Never raises; an empty, short or untimed frame answers -2, so each caller's
    own length guard behaves exactly as it did."""
    try:
        if df is None or len(df) == 0:
            return -2
        start = df.index[-1]
        if not isinstance(start, datetime):
            return -2
        s0 = _epoch_s(start)
        t = _epoch_s(now)
        if t is None:
            t = _epoch_s(now_et())
        if s0 is None or t is None:
            return -2
        b = float(bar_s)
        return -1 if (s0 + b <= t < s0 + LIVE_FRAME_BARS * b) else -2
    except Exception:                                           # noqa: BLE001
        return -2


def closed_part(df, now=None, bar_s: float = 60.0):
    """r44 (BAR.1) — the frame's CLOSED bars: `df` itself when its newest row has
    closed (closed_pos -1), else df.iloc[:-1] (the reading before r44)."""
    if df is None:
        return df
    return df if closed_pos(df, now, bar_s) == -1 else df.iloc[:-1]


def fmt_et_short(dt: Optional[datetime] = None) -> str:
    dt = dt or now_et()
    if dt.tzinfo is None:
        dt = ET.localize(dt)
    return dt.strftime("%m/%d %H:%M ET")


def fmt_et_full(dt: Optional[datetime] = None) -> str:
    dt = dt or now_et()
    if dt.tzinfo is None:
        dt = ET.localize(dt)
    return dt.strftime("%Y-%m-%d %H:%M:%S ET")


def ts_for_db(dt: Optional[datetime] = None) -> str:
    dt = dt or now_utc()
    return dt.isoformat()


def is_rth(now: Optional[datetime] = None) -> bool:
    """True if ET time is within RTH (9:30–16:00 ET, weekdays).

    r102: takes an OPTIONAL clock so a caller (and a check) can ask about a
    specific moment. No argument = now, which is every existing call site.
    """
    now = now or now_et()
    # 🔴 r304 / DEP.9 — THE CALENDAR, NOT JUST THE WEEKDAY. Until now this
    # tested `weekday() >= 5` and nothing else, so on a market holiday it
    # returned True and `entries_open()` — the universal floor every order site
    # sits behind (r102) — said the market was open. Surfaced 2026-09-07,
    # Labor Day, when the orchestrator correctly kept the bots down while
    # devtools 35 refused a bake as "inside RTH".
    # ⚠️ ONE CALENDAR, NOT A SECOND IMPLEMENTATION. Adding a holiday set here
    # would have been a THIRD copy beside shadow/trading_day.py and
    # day_trader_pro's market_calendar.
    # ⚠️ IT FAILS TOWARD TRADING: an unlisted date is a session, including one
    # past the list's coverage. A wrong holiday costs a silent dark fleet; a
    # missed one costs an armed morning on a dead tape.
    if not market_calendar.is_trading_day(now.date()):
        return False
    t = now.time()
    # r478 / DEP.12 — the OPEN side is raw; the CLOSE side is the day's bell.
    return RTH_OPEN <= t < close_anchored(RTH_CLOSE, now)


# ── r478 / DEP.12 — THE DAY'S BELL ──────────────────────────────────────────
# Every close-anchored time in this tree (15:40 flatten, 15:45 cross and credit
# hold, 15:50/15:57 reconciles, the watchdog's 15:50-16:00, the 16:00 bell) is
# written against a 16:00 close. On an early close (market_calendar
# .EARLY_CLOSES) each moves earlier by the same number of minutes, so the
# constants stay the one source and nothing grows a half-day twin.
# ⚠️ CLOSE SIDE ONLY. Never shift an OPEN-side boundary (09:30, 09:35, the
# reconcile slots' 09:30 base): on 11-27 the market still opens at 09:30.
# ⚠️ THE CONSTANT MOVES, NOT THE CLOCK. Shifting `now` forward by 3 h wraps past
# midnight after 21:00 and reads "00:30 < 16:00" as RTH; moving the anchor
# cannot. Log lines and slot keys therefore stay in true ET.
def close_shift(now: Optional[datetime] = None) -> timedelta:
    """How much earlier than 16:00 the session at `now` closes (0 on a full day)."""
    now = now or now_et()
    try:
        return timedelta(minutes=market_calendar.close_shift_minutes(now.date()))
    except Exception:                                          # noqa: BLE001
        return timedelta(0)        # fails toward a FULL day: the pre-r478 clock


def close_anchored(t, now: Optional[datetime] = None) -> dtime:
    """A 16:00-bell constant (dtime or (h, m)) moved to the bell of `now`'s day.

    15:40 -> 12:40 on a 13:00 close; unchanged on a full day.
    """
    if not isinstance(t, dtime):
        h, m = tuple(t)[:2]
        t = dtime(int(h), int(m))
    mins = t.hour * 60 + t.minute - int(close_shift(now).total_seconds() // 60)
    mins = max(0, mins)
    return dtime(mins // 60, mins % 60, t.second)


def past_close_anchor(t, now: Optional[datetime] = None) -> bool:
    """True once the clock is at or past `t` moved to the day's bell (minute grain)."""
    now = now or now_et()
    a = close_anchored(t, now)
    return (now.hour, now.minute) >= (a.hour, a.minute)


# v3.8: flatten window opens 5 min before the hard cross so the mark-limit
# phase has time to work. Falls back to HARD_CLOSE if config is older.
try:
    from config import FLATTEN_WINDOW_OPEN_ET as _FWO
    FLATTEN_WINDOW_OPEN = dtime(*_FWO)
except Exception:
    FLATTEN_WINDOW_OPEN = HARD_CLOSE


def entries_open(now: Optional[datetime] = None) -> bool:
    """r101 — True once ORDERS MAY BE PLACED (config.ENTRY_OPEN_ET, 09:35 ET).

    The deciding logic runs whenever the service is up; this is the only thing
    that stops it from placing. OPENINGS ONLY — every exit path ignores it.

    ⚠️ FAILS CLOSED. A bad clock read or a malformed override returns False:
    a missed entry costs a trade, an entry placed against a range that does not
    exist costs a position nobody anchored.
    """
    # 🔴 r102 — DEFERS TO is_orb_complete(), WHICH IS THE RULE THAT ALREADY
    # EXISTED. r101 added ENTRY_OPEN_ET without grepping first; session_guard
    # line ~98 has enforced the same floor since v3 and its comment already
    # calls it "the universal floor for EVERY strategy". Two constants for one
    # rule is how two gates come to disagree, so this one is now a WRAPPER: the
    # ORB close decides, and ENTRY_OPEN_ET only survives as an override for a
    # caller passing an explicit clock (tests) or an operator moving the floor.
    # ⚠️ AND IT CARRIES THE RTH TEST. A time-of-day floor is TRUE at 16:53, so
    # on its own it would have permitted an outside-RTH fill the moment the RTH
    # short-circuit above was loosened. The floor answers "is it late enough";
    # it must also answer "is the market open".
    try:
        n = now or now_et()
        if not is_rth(n):
            return False
        # 🔴 r478 / DEP.12 — ON AN EARLY CLOSE, NOTHING OPENS IN THE LAST
        # HALF_DAY_ENTRY_LEAD_MIN (90) MINUTES: 11:30 on a 13:00 day. Operator
        # 2026-10-11. ORB (to 11:00) and Runaway (to 11:30) keep their windows;
        # the sweep (11:31), butterfly (12:00) and TCS never open. A judgement,
        # not a measurement: no box has traded a half day. Full days: no change
        # (the r60 ruling stands — there is no global afternoon cutoff).
        if market_calendar.is_half_day(n.date()):
            # Imported, not getattr'd (C.44): a missing key fails CLOSED here.
            from config import HALF_DAY_ENTRY_LEAD_MIN as _lead
            _c = market_calendar.close_time(n.date())
            _cut = max(0, _c.hour * 60 + _c.minute - _lead)
            if (n.hour * 60 + n.minute) >= _cut:
                return False
        import config as _cfg
        _override = getattr(_cfg, "ENTRY_OPEN_ET", None)
        if _override is not None and now is not None:
            h, m = tuple(_override)[:2]
            return (n.hour, n.minute) >= (int(h), int(m))
        return is_orb_complete(n)
    except Exception:                                          # noqa: BLE001
        return False


def eod_close_due(assignment_risk: bool, now: Optional[datetime] = None) -> bool:
    """r149 (EOD.1) — has THIS position's end-of-day close begun? Assignment
    risk (a short leg) from 15:45, on a resting best-case limit; everything
    else from 15:50, on the ladder. Both cross at 15:55 (HARD_CLOSE)."""
    # r268 (DEP.12, fork-only site) — anchored to the day's bell: 12:45 / 12:50 on a 13:00 close.
    n = now or now_et()
    return n.time() >= close_anchored(_EOD_REST if assignment_risk else _EOD_LAD, n)


def is_hard_close_time(now: Optional[datetime] = None) -> bool:
    """True if the end-of-day flatten window is open (≥ 15:40 ET).

    v3.8: the window now OPENS FIVE MINUTES EARLIER than the hard close itself.
    15:40-15:44 the flatten posts mark-limits (re-priced each tick) so a
    position can close without paying the spread; at 15:45 it crosses and the
    position closes unconditionally. Opening at 15:45 would have left zero time
    for the limit phase — the escalation would never fire before the bell. The
    cross-over instant is still HARD_CLOSE (15:45); see
    execution/limit_ladder.hard_close_order_mode.
    r478 / DEP.12: 12:40 on a 13:00 close (close_anchored)."""
    now = now or now_et()
    return now.time() >= close_anchored(FLATTEN_WINDOW_OPEN, now)


# r60 (2026-08-21): is_past_entry_cutoff() DELETED with ORB_NO_ENTRY_AFTER_ET —
# the 14:00 number was never an operator decision (provenance in config.py).
# Callers rerouted: session_guard's global block is deleted outright;
# orb_engine's re-arm check now reads ORB's OWN specced cutoff (11:00), which
# is what actually bounds an ORB re-entry and always did.


def is_orb_window() -> bool:
    """True if we're in the 9:30–9:35 ORB definition window."""
    now = now_et()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return RTH_OPEN <= t < ORB_END


def is_orb_complete(now: Optional[datetime] = None) -> bool:
    """True if the ORB window has closed and we can look for setups.

    r102: THIS IS THE AUTHORITY FOR THE 09:35 ENTRY FLOOR. `entries_open()`
    wraps it rather than carrying a second constant — session_guard has
    enforced this same floor since v3 and calls it "the universal floor for
    EVERY strategy". Optional clock, as is_rth.
    """
    now = now or now_et()
    return now.time() >= ORB_END


def minutes_since(dt: datetime) -> float:
    """Minutes elapsed since dt (handles timezone-aware and naive)."""
    now = now_utc()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() / 60


def is_within_minutes(dt: datetime, minutes: float) -> bool:
    return minutes_since(dt) < minutes


def today_et() -> datetime:
    """Today's date at midnight ET."""
    return now_et().replace(hour=0, minute=0, second=0, microsecond=0)


def seconds_until_hard_close() -> float:
    """Seconds until 15:45 ET today."""
    now = now_et()
    hc = now.replace(hour=15, minute=45, second=0, microsecond=0)
    if now >= hc:
        return 0
    return (hc - now).total_seconds()


def seconds_until_rth_open() -> float:
    """Seconds until next RTH open (9:30 ET). Returns 0 if already open."""
    now = now_et()
    if is_rth():
        return 0
    open_today = now.replace(hour=9, minute=30, second=0, microsecond=0)
    if now < open_today and now.weekday() < 5:
        return (open_today - now).total_seconds()
    # Next weekday
    days_ahead = 1
    while (now + timedelta(days=days_ahead)).weekday() >= 5:
        days_ahead += 1
    next_open = (now + timedelta(days=days_ahead)).replace(
        hour=9, minute=30, second=0, microsecond=0
    )
    return (next_open - now).total_seconds()


def current_session_label() -> str:
    """Human-readable session label."""
    now = now_et()
    t = now.time()
    if t < RTH_OPEN:
        return "pre_market"
    if RTH_OPEN <= t < ORB_END:
        return "orb_window"
    if ORB_END <= t < dtime(11, 0):
        return "early_session"
    if dtime(11, 0) <= t < dtime(14, 0):
        return "mid_session"
    if dtime(14, 0) <= t < close_anchored(HARD_CLOSE, now):
        return "late_session"
    return "closed"
