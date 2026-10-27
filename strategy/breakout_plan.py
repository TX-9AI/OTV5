"""
strategy/breakout_plan.py  v5.1
v5.1  2026-10-27  OTV5 r44 (BAR.1) — THE BREAK BAR IS THE LAST BAR CLOSED BY TIME, NOT df_1m.iloc[-2]. "THE BREAK: a CLOSED
      bar's CLOSE beyond the edge (r5)" read iloc[-2], which on a tick in the first instant of a minute (before that
      minute's first row exists) is one bar stale. META 2026-10-27 3f2b1372: Breakout short fired 10:10:00 ET on the
      10:08 bar (close 623.01 < edge 623.20; plan line "1m stop 623.57" = 10:08's high 623.5659) while 10:09 had already
      closed back inside at 623.21 - a break the market had undone. The break bar, its stop, the 5m-swing bound, and the
      signal-bar stamp the fresh-break / re-fire / shadow gates read now all use utils.time_utils.closed_pos(df_1m,
      now_et): the newest row when it has closed, else the row before it (unchanged when the forming row is present).
      GATE tests/check_last_closed_bar.py C2/C3.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.18 2026-10-24  OTV4TEST r316 (BRK.15) — A SIDE RE-ARMS ON EVERY RETURN TO THE RANGE; THE NEW-EXTREME RULE IS DROPPED.
      The operator, 2026-10-24 13:45 ET: "The new session high/low rule needs to be dropped. You established that the
      move was mostly done if we waited for a new extreme"; 13:56 ET: "For now, rearm it on every reentry" ... "Yes,
      effective Monday". _refire() replaces the _new_extreme() call: the signal bar must be the FIRST RTH 1m close
      beyond the edge since 09:35 or since the latest close back inside it (break_run_start(), feed store, fails
      closed). r142's latch (no bar that already fired) is kept; r282's lesson holds by construction (a refused break
      spends the break until a close back inside). COUNTERFACTUAL: wherever r131's verdict differs, both are written to
      data/counterfactual/breakout_refire.jsonl. OT_BRK_REFIRE=extreme runs _new_extreme() unchanged (rollback) and
      records the re-arm verdict instead. tests/check_breakout_rearm.py.
v1.17 2026-10-18  OTV4TEST r299 (BRK.14) — AN UNREADABLE LEVEL BOARD IS NOT A CLEAN RANGE. _board() returned {} on any
      failure (logged at debug, invisible), range_clean then counted 0 levels inside and room_to_run read "open air":
      harmless while ACCEPTANCE=any (to BRK_RESEARCH_UNTIL), two informers silently disabled by a store hiccup after
      it. Now the board carries its state, a non-"ok" board makes both readings None (admitted by "any", refused by a
      numbered dial - accepts()' own rule), and the failure is said once per state per process. Audit 2026-10-18 D3.
v1.16 2026-10-15  BRK.12 (FORK-ONLY) — A RETURN TO THE RANGE RE-ARMS THE SIDE, ONCE - RECORD-ONLY. The operator,
      2026-10-14 11:38 ET: "I want a return of the range to enable another breakout in either direction" ("Breakout
      only", "One re-arm per side"); 2026-10-15 10:16 ET: "Concur on all" (to "BRK.12 / HUNT.9: record-only").
      range_rearm() reads the feed store: after the side's first break, a 1m close back inside the edge, and the
      signal bar is the first close beyond it since. _new_extreme() writes that would-be fire, with the
      new-extreme verdict beside it, to data/counterfactual/breakout_rearm.jsonl (once per side per signal bar)
      and changes no decision. OT_BRK_REARM=log|off (unset = log). check_breakout_new_extreme N11.
v1.15 2026-10-14  OTV4TEST r284 (BRK.11) — THE STOP IS THE 5m SWING, NOT THE 1m BREAK BAR. The 1m break bar's extreme
      put the stop inside one minute of noise (median 0.36 pt on QQQ-TEST's 98 Breakouts; 10-14 10:53: 0.76 pt, 46
      contracts, out in 2 min on a 1-pt bounce in a 5-pt trend). swing_5m_stop() reads the feed store (read-only) for
      the last BRK_STOP5M_BARS CLOSED 5m bars of TODAY'S RTH that ended by the signal bar's close; the stop is the
      FARTHER of that extreme and the break bar's (never tighter than before). Size and the structural premium stop
      follow underlying_stop unchanged (r91). OT_BRK_STOP5M=trade|log|off (unset = trade); an unreadable store keeps
      the 1m stop and says so. COUNTERFACTUAL: every FIRE writes both stops to data/counterfactual/breakout_stop.jsonl.
      The operator, 2026-10-14 11:47 ET: "Yes, we have to". tests/check_brk_stop5m.py.
v1.14 2026-10-13  OTV4TEST r282 (BRK.10) — THE FIRST ENTRY IS THE TAPE'S FIRST BREAK, NOT THE BOOK'S FIRST FILL.
      r131's "first entry per side fires on the break close" counted FILLED trades only, so a break the gates
      refused (SPX-TEST 10-13: commit x2, pin x45, ENT.1 x12, 09:38-09:52) left the side "unfired" and the next close
      beyond the edge fired 15 min later mid-range under the session high (-$927). first_break_before() reads the feed
      store: when an EARLIER closed RTH 1m bar today already closed beyond the edge, this entry must also close beyond
      the session extreme (r131's re-fire rule); an unreadable tape fails closed. The operator, 2026-10-13 17:17 ET:
      "This is a fucking real problem"; 18:10 ET: "yes" (to building it tonight). tests/check_breakout_new_extreme.py.
v1.13 2026-10-08  OTV4TEST r263 (BRK.7, found on SPX-TEST) — A ZERO-RISK BREAK IS REFUSED, NEVER RAISED. A break bar
      that CLOSED AT ITS OWN EXTREME (a short at its high, a long at its low) puts the stop on the close: risk 0,
      r None, and while `r` accepts "any" nothing refused it - prepare reached TAKE and trade_line raised
      TypeError formatting R (SPX-TEST 56x, QQQ-TEST 77x, 10-07/10-08, all in r254 LOG-ONLY hours, none in the
      entry window). The operator, 2026-10-08 16:40 ET: "Yes, to all". After the r check, risk <= 0 refuses at
      stop_survivable ("zero risk: the break bar closed at its own extreme"). tests/check_brk_zero_risk.py.
v1.12 2026-10-06  OTV4TEST r259 (STRK.2) — ON A CASH INDEX THE CONTRACT IS THE NEAREST STRIKE AT OR INSIDE
      THE REACH. The operator, 2026-10-06 20:41 ET: "at or inside target". SPX-TEST's 10:08 long bought the
      7845C for a 7842.79 reach (nearest by 2.21 vs 2.79); on SPX's 5-wide grid a strike could sit up to 2.5
      points past the reach. select_contract(..., inside=prep.cash_index); every other symbol is unchanged.
      No inside strike is a refusal ("no listed strike at or inside the reach"). tests/check_brk_strike_inside.py.
v1.11 2026-10-05  OTV4TEST r254 (OBS.1) — THE PLAN ALWAYS LOOKS, THE STRATEGY IS GATED ON THE HOUR: Breakout, Runaway and the Hunt are OBSERVED from their entry end to 15:40 - asked, recorded LOG-ONLY, never executed (the operator, 2026-10-05: "the plan always looks, but the strategies are gated on the hour of the day"; "Have those blocked TRADES just to Log only"). Here: past LATEST_ET the plan keeps looking only while observed (the r220 window line is unchanged).
v1.10 2026-10-05  OTV4TEST r251 (BRK.6) — ON A CASH INDEX THE TAPE AND THE BOOK ARE NOT APPLICABLE, NEVER A REFUSAL.
      SPX has no time-and-sale and no resting size: on 2026-10-05 flow_imbalance and depth_ratio were None on 220 of 220
      SPX ticks (every print in SPX-TEST's store was AAL's; SPX's 6,046 Quote rows carried bid/ask size 0), so
      flow_commit FAILED every tick and Breakout could not trade SPX by construction (mainline's SPX book: 0 Breakout
      in 192 trades). The operator, 11:09 ET: "I agree and we have to get SPX Trading those breakouts"; 11:28 ET, on
      depth too: "Yes, do it." On config.is_cash_index(symbol), flow_commit (with its flow_tagged half) and depth_thin
      record "n/a - cash index, no tape" / "no book" and are MET - before acceptance is asked, so it holds after the
      research window closes (10-30). The raw readings are still recorded. _route's `fading` no longer counts an
      index's absent book as a failing one (it routed SPX's 10:16-10:18 break as a HARVEST on that alone). Found and
      authored on SPX-TEST. Anything that is not a cash index: unchanged, a missing reading still refuses.
v1.9  2026-10-03  OTV4TEST r220 (TIME.1) — the private parser is utils.time_utils.parse_hm; an unreadable window BOUND now closes the window (it read as 00:00, i.e. open since midnight).
v1.8  2026-10-03  OTV4TEST r218 (PATH.1) — QUOTE_FLOOR is read from config with no getattr fallback (config now defines it, value unchanged 0.01).
v1.7  2026-10-03  OTV4TEST r188 (BRK.5) — depth_thin FINALLY HAS A READING. `_depth` read
      `depth_now` / `depth_before`, keys `analysis/order_flow.depth()` has never
      returned (it returns bid/ask sizes and bid_depth_ratio / ask_depth_ratio), so
      the reading was None on 2,153 of 2,153 plan_check rows 09-21..10-02 and the
      informer recorded nothing for the whole research window. Now the depletion
      is read off the side AHEAD of price - the ask for a long, the bid for a
      short - as 1 - <side>_depth_ratio (positive = thinning, as documented).
      The operator, 2026-10-03: "on the very next session that it TRADES make
      sure that we're getting the right data." RECORD-ONLY BY MEASUREMENT on
      QQQ: acceptance is "any" until 2026-10-30 (config v4.46), and the one
      fitted-dial reader, `_route`'s `fading`, runs only when a bar is unmet -
      flow_imbalance was present on 2,153 of 2,153 ticks and 0 DEFER lines are in
      bot.log since 09-08. On a box whose flow goes missing, a pooled break's
      routing could now differ (depth no longer reads as failing).
v1.6  2026-09-25  OTV4TEST r142 — A RE-FIRE IS JUDGED ON A BAR THAT CLOSED AFTER THE
      LAST ENTRY. r131's gate compared the signal bar (df_1m[-2], the last CLOSED
      bar) with every RTH bar BEFORE it - and the signal bar can be the SAME bar
      that fired the previous entry. 2026-09-25: a long fired at 09:36:16 on the
      09:35 close (743.87 over the 09:30-09:34 high 743.68) and stopped out 33s
      later; at 09:36:51 the 09:35 bar was STILL the last closed bar, so the
      re-fire passed the same test on the same close while the session high was
      the 09:35 bar's own 744.10. -$1,250. Operator: "A new high for a long".
      Now a re-fire also needs its signal bar to START at or after the minute of
      the side's latest entry, so it closed after that entry; the session extreme
      then includes the bar that fired before. `side_entries_today` is the one
      trades.db read; `side_fired_today` is its count, unchanged for its callers.
v1.5  2026-09-24  OTV4TEST r131 — A RE-FIRE NEEDS A NEW EXTREME (gate
      `new_extreme`, FOUNDATIONAL, declared in breakout.py GATES). THE
      OPERATOR, 2026-09-24: *"A new reclaimed level has to happen before it
      can fire again? A new high for a long, a new low for a short."* The
      trigger below was a STATE (the last closed bar still beyond the edge)
      with no latch, so on 09-24 it fired 18 times into one range. Now the
      FIRST entry per side per session keeps that trigger unchanged; EVERY
      LATER entry on that side needs the last closed 1m bar to CLOSE above
      the highest HIGH of every prior RTH bar since 09:30 (long) / below the
      lowest LOW (short). Strictly beyond, no tolerance — closes are
      acceptance. Tape simulation, QQQ 38 sessions, +2R/-1R
      (/var/tmp/compression_study/results_refire_sim.txt): +24.0R against
      -8.0R as built; trend days +44R vs +22R; chop -9R vs -24R. (13 symbols
      08-24..09-18: -70.2R vs -125.8R — less bad, not positive.)
      🔑 "ALREADY FIRED" IS READ FROM trades.db (DEC.1, the runaway's
      `break_last_exit` path): any Breakout row entered this session on this
      side, win or loss, open or closed. A restart cannot reset it.
      🔑 THE SESSION EXTREME IS READ FROM THE FEED STORE, NOT df_1m: the
      frame main.py passes is TIMEFRAMES["1m"] = 60 bars ROLLING (config.py
      r95 block), so by 10:37 it no longer holds 09:30-09:36 and its high
      would silently shrink. Both reads FAIL CLOSED with the gate named.
      Placed AFTER the router and BEFORE the contract: routing (DEFER/PERMIT)
      is untouched; only a TAKE that re-fires without a new extreme is refused.
v1.4  2026-09-22  OTV4TEST r91 — carries `entry_delta`, same as the ORB.
      ⚠️ PARITY IS THE POINT: Breakout exists to be the ORB without the
      retest, so a sizing input one supplies and the other does not would make
      the operator's A/B a comparison of two sizers instead of two entries.
THE SEARCH. Every tick, for the setup that satisfies `strategy/breakout.py`.

v1.3  2026-09-21  OTV4TEST r77 — emit() imported OptionsSignal from
      `strategy.structure`, which does not export it. ImportError on EVERY tick
      from 09:37:04; 127 crashes in one session and NOT ONE Breakout trade,
      ever. Lazy import, so check_imports passed; _safe_strategy caught the
      raise, so the board showed a stale skip label instead of a crash.
v1.2  2026-09-19  OTV4TEST r59 — the FADE route read `prep.unmet`, which is
      EMPTY while acceptance is "any", so DEFER->HUNT / DEFER->SWEEP could not
      fire for the whole research window. Reads the FITTED dials, like `pooled`.
v1.1  2026-09-19  OTV4TEST r55 — THE INFORMERS ARE DIALS, NOT A BYPASS.
      Operator: "I still want the informer set as triggers in the strategy
      package, but set the acceptance to 'any'." An earlier cut made them SKIP
      `cond()`; he ruled against it and he was right — a bypass has to be
      un-bypassed later, and that code is code nobody has run. Every bar is a
      real trigger again; `B.accepts(bar, value)` carries the acceptance.
      ⚠️ The FADE route reads the FITTED dial, not the live acceptance: while
      acceptance is "any" every pool distance clears room_to_run, so asking
      "did room_to_run fail?" would never route a harvest to the sweep.
      Declares `sizes_on_geometry` so it sizes as the ORB does.
v1.0  2026-09-18  OTV4TEST r51 (BRK.1).

🔑 WHAT THIS FILE IS FOR, IN THE OPERATOR'S WORDS (2026-09-18): *"The plan file
is what searches the feed every tick for the nearest qualifying setup that
satisfies the strategy. The plan knows exactly what bars must be cleared in
order to deliver a working plan to the strategy. If it can't satisfy every
single hurdle then it doesn't put forward a plan. The plan exists for the sole
purpose of forming the trigger the strategy executes on. Literally A, B, C was
satisfied at X strike, execute if/when it reaches."*

So the OUTPUT of this file is a TRIGGER and nothing else: every declared bar
already TRUE, a strike selected, a stop and an R that clear the floor — and one
thing left pending, which the strategy confirms on the next tick.

🔑 AND IT ROUTES RATHER THAN MERELY REFUSING. Operator: *"if we identify that
it's a fakeout before it happens, maybe we can tip off the appropriate trade to
take that."* When the bars fail in the shape that says HARVEST — a pool sitting
where the stops are, a pinning regime, depth refilling after the sweep — this
plan does not go quiet. It `permit()`s, which `strategy/plan.py` defines as
*"a PERMISSION, not a signal… the plan's terminal for an informer"*, and writes
a PERMIT row so the account separates "informed another strategy" from "took a
trade". **The breakout and the fade are ONE SETUP READ TWO WAYS**, which is why
one search can decide both.

⚠️ THE BREAK IS A CLOSE, NEVER A WICK (r5). That single bar is the anti-fakeout
gate that costs nothing in TIME — which is the whole reason this trade can skip
the retest the ORB waits for.
"""
from __future__ import annotations

import logging
from typing import Optional

import config
from strategy.plan import Plan
from strategy import observe as _observe   # r254 (OBS.1)

logger = logging.getLogger(__name__)

# ── WA §36 ──────────────────────────────────────────────────────────────────
# ⚠️ THE PLAN OWNS NO THRESHOLDS. Every bar it clears is declared in
# `strategy/breakout.py` and read from there, which is the whole point of the
# split: a gate that lived here could be tuned without the specification
# changing, and then the spec would describe a trade the box no longer takes.
# `QUOTE_FLOOR` is the one constant here and it is FEASIBILITY — a contract
# with no live quote cannot be bought at any price.
GATES = {
    "QUOTE_FLOOR": "FEASIBILITY",
}

QUOTE_FLOOR = float(config.QUOTE_FLOOR)      # r218: the name now exists in config; no silent fallback


def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


from utils.time_utils import parse_hm as _hm      # r220 (TIME.1): the one parser
from utils.time_utils import closed_pos as _closed_pos   # r44 (BAR.1): the last CLOSED bar, by time


def _et(s: str):
    """A window bound. r220: None when unreadable (it was (0, 0), which read an unreadable START as
    'open since midnight'); the window check treats None as closed."""
    return _hm(s)


# ── r131 readers: the two books the re-fire gate decides on ────────────────
_ET_ZONE = "America/New_York"


def _today_et():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo(_ET_ZONE)).date()


def _bar_stamp(df, i):
    """The bar's START as a tz-aware ET Timestamp, or None. A naive index is
    read as ET (the feed frame is tz-aware ET; fixtures may be naive)."""
    try:
        import pandas as pd
        ts = pd.Timestamp(df.index[i])
        if ts is pd.NaT or not isinstance(ts, pd.Timestamp):
            return None
        return ts.tz_localize(_ET_ZONE) if ts.tzinfo is None else ts.tz_convert(_ET_ZONE)
    except Exception:                                           # noqa: BLE001
        return None


def side_fired_today(direction: str, day) -> Optional[int]:
    """How many Breakout entries on this side today (see side_entries_today).
    None = unreadable, and the caller FAILS CLOSED."""
    ents = side_entries_today(direction, day)
    return None if ents is None else len(ents)


def side_entries_today(direction: str, day):
    """How many Breakout entries `trades.db` holds for `day` (ET) on this side.
    NEVER raises; None = unreadable, and the caller FAILS CLOSED.

    🔑 DEC.1: *"I don't want anything that our trades decide on to only live in
    memory."* The runaway's `break_last_exit` path, reused: the side from
    `option_side` (a call is long, a put short; `direction` is the fallback),
    scoped to the current mode's rows. ANY entry counts, win or loss, open or
    closed. ⚠️ A Breakout row whose side cannot be read counts on BOTH sides —
    an unkeyable entry must not re-open the unlatched trigger.
    """
    from datetime import datetime, timedelta
    try:
        from zoneinfo import ZoneInfo
        _et, _utc = ZoneInfo(_ET_ZONE), ZoneInfo("UTC")
        lo = (datetime.combine(day, datetime.min.time(), _et)
              - timedelta(hours=1)).astimezone(_utc).isoformat()
        hi = (datetime.combine(day, datetime.min.time(), _et)
              + timedelta(days=1, hours=1)).astimezone(_utc).isoformat()
        from database.trade_logger import get_trade_logger
        tl = get_trade_logger()
        conn = tl._connect()
        try:
            rows = conn.execute(
                "SELECT entry_time, option_side, direction FROM trades "
                "WHERE strategy='Breakout' AND entry_time >= ? AND entry_time < ? "
                "AND COALESCE(paper_trade,1)=?",
                (lo, hi, int(getattr(tl, "_mode_flag", 1)))).fetchall()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[breakout] side history unreadable from trades.db (%s) — "
                       "failing closed", exc)
        return None
    out = []
    for et_, side, dirn in rows:
        try:
            _t = datetime.fromisoformat(str(et_))
            if _t.tzinfo is None:
                _t = _t.replace(tzinfo=_utc)
            _t = _t.astimezone(_et)
            if _t.date() != day:
                continue
        except (TypeError, ValueError):
            continue
        sd = str(side or "").lower()
        d = ("long" if sd.startswith("c") else "short" if sd.startswith("p")
             else str(dirn or "").lower())
        if d not in ("long", "short"):
            logger.warning("[breakout] a Breakout row at %s has option_side=%r "
                           "direction=%r — counted as fired on BOTH sides", et_, side, dirn)
            out.append(_t)
        elif d == direction:
            out.append(_t)
    return sorted(out)


def session_extreme(symbol: str, day, before_ms: int, direction: str):
    """(extreme, n_bars) over EVERY RTH 1m bar of `day` from 09:30 up to (not
    including) `before_ms`, read-only from the feed store — or a string naming
    why it could not be read. NEVER raises.

    ⚠️ NOT df_1m: that frame is 60 bars ROLLING, so from 10:31 it no longer
    reaches 09:30 and its high would quietly shrink (config.py, the r95
    reach-back block). ⚠️ AND THE SESSION MUST START AT 09:30 IN THE STORE: a
    tape missing its open would understate the high and let a re-fire through.
    """
    from datetime import datetime
    try:
        import sqlite3
        from zoneinfo import ZoneInfo
        from data.candle_feed import feed_db_path
        open_ms = int(datetime(day.year, day.month, day.day, 9, 30,
                               tzinfo=ZoneInfo(_ET_ZONE)).timestamp() * 1000)
        conn = sqlite3.connect(f"file:{feed_db_path()}?mode=ro", uri=True, timeout=5.0)
        try:
            rows = conn.execute(
                "SELECT ts_epoch_ms, high, low FROM candles WHERE symbol=? AND interval='1m' "
                "AND ts_epoch_ms >= ? AND ts_epoch_ms < ? AND open > 0 AND close > 0 "
                "ORDER BY ts_epoch_ms", (symbol, open_ms, int(before_ms))).fetchall()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        return f"session tape unreadable ({type(exc).__name__}: {exc})"
    if not rows:
        return "no session bars in the feed store before the signal bar"
    if int(rows[0][0]) != open_ms:
        return "the feed store's session does not start at 09:30"
    vals = [_f(r[1] if direction == "long" else r[2]) for r in rows]
    vals = [v for v in vals if v is not None]
    if not vals:
        return "session bars carry no extremes"
    return (max(vals) if direction == "long" else min(vals)), len(rows)


def first_break_before(symbol: str, day, before_ms: int, direction: str, edge):
    """The ts_ms of the FIRST RTH 1m bar of `day` (from the opening range's close, 09:35, up to, not including,
    `before_ms`) whose CLOSE was beyond `edge` in `direction` - None when no
    bar did - or a string naming why it could not be read. NEVER raises.

    🔴 r282 (BRK.10) - THE BREAK IS READ FROM THE BOOK, NOT FROM A FILL. r131
    let the first entry per side fire on any close beyond the edge because it
    counted only FILLED trades. A break the gates refused (SPX 10-13: commit x2,
    pin x45, ENT.1 x12, 09:38-09:52) left the side "unfired", and the next close
    beyond the edge fired as a FIRST entry 15 min later, mid-range under the
    session high (-$927). The day's first break is a fact of the tape.
    """
    from datetime import datetime
    try:
        import sqlite3
        from zoneinfo import ZoneInfo
        from data.candle_feed import feed_db_path
        # ⚠️ FROM THE RANGE'S CLOSE, NOT 09:30: a bar INSIDE the opening range cannot break it,
        # and the edge on the row need not contain every 09:30-09:34 1m close (QQQ 09-29: closes
        # beyond the stored edge at 09:30 and 09:34) - counting them would call a TRUE first
        # break "stale".
        try:
            from config import ORB_WINDOW_MINUTES as _orbm
        except Exception:                                       # noqa: BLE001
            _orbm = 5
        open_ms = int(datetime(day.year, day.month, day.day, 9, 30,
                               tzinfo=ZoneInfo(_ET_ZONE)).timestamp() * 1000) + int(_orbm) * 60_000
        e = float(edge)
        conn = sqlite3.connect(f"file:{feed_db_path()}?mode=ro", uri=True, timeout=5.0)
        try:
            q = ("SELECT ts_epoch_ms FROM candles WHERE symbol=? AND interval='1m' "
                 "AND ts_epoch_ms >= ? AND ts_epoch_ms < ? AND close > 0 AND close "
                 + (">" if direction == "long" else "<") + " ? ORDER BY ts_epoch_ms LIMIT 1")
            row = conn.execute(q, (symbol, open_ms, int(before_ms), e)).fetchone()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        return f"session tape unreadable ({type(exc).__name__}: {exc})"
    return int(row[0]) if row else None


def swing_5m_stop(symbol: str, day, sig_end_ms: int, direction: str, bars: int = 3):
    """The extreme (short: highest high, long: lowest low) of the last `bars` CLOSED 5m
    candles of `day`'s RTH (start >= 09:30 ET) that ENDED at or before `sig_end_ms`
    (the signal bar's close) - None when there is none yet, or a string naming why
    the store could not be read. NEVER raises.

    🔴 r284 (BRK.11) - the 1m break bar's extreme is a stop inside one minute of
    noise. Measured on QQQ-TEST's Breakouts 09-09..10-14 (underlying R, held to the
    stop or 15:55, /var/tmp/structure_hold_1014/v2_brk.txt): winners 12 -> 33, full
    stops 86 -> 59, the 1m-losing days -51.2 R -> -31.8 R; total +91.1 R -> +40.8 R
    (09-21's few-cent stops carry the 1m total).
    """
    from datetime import datetime
    try:
        import sqlite3
        from zoneinfo import ZoneInfo
        from data.candle_feed import feed_db_path
        open_ms = int(datetime(day.year, day.month, day.day, 9, 30,
                               tzinfo=ZoneInfo(_ET_ZONE)).timestamp() * 1000)
        conn = sqlite3.connect(f"file:{feed_db_path()}?mode=ro", uri=True, timeout=5.0)
        try:
            rows = conn.execute(
                "SELECT high, low FROM candles WHERE symbol=? AND interval='5m' AND ts_epoch_ms >= ? "
                "AND ts_epoch_ms + 300000 <= ? AND high > 0 AND low > 0 ORDER BY ts_epoch_ms DESC LIMIT ?",
                (symbol, open_ms, int(sig_end_ms), int(bars))).fetchall()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        return f"5m bars unreadable ({type(exc).__name__}: {exc})"
    if not rows:
        return None
    return float(max(h for h, _ in rows)) if direction == "short" else float(min(l for _, l in rows))


def range_rearm(symbol: str, day, before_ms: int, direction: str, edge):
    """BRK.12 - (first_break_ms, return_ms) when the signal bar is this side's ONE re-armed break: an earlier
    RTH 1m close beyond `edge` (from the range's close, 09:35), then a close back inside it, and NO close beyond
    it since, up to (not including) `before_ms`. None when that is not so; a string when the tape is unreadable.
    NEVER raises.

    🔑 The operator, 2026-10-14 11:38 ET: *"I want a return of the range to enable another breakout in either
    direction"* - scope "Breakout only", cap "One re-arm per side". RECORD-ONLY (the operator, 2026-10-15 10:16 ET:
    "Concur on all", to "BRK.12 / HUNT.9: record-only"): the plan writes the would-be fire to
    data/counterfactual/breakout_rearm.jsonl and the new-extreme rule alone decides.
    """
    from datetime import datetime
    try:
        import sqlite3
        from zoneinfo import ZoneInfo
        from data.candle_feed import feed_db_path
        try:
            from config import ORB_WINDOW_MINUTES as _orbm
        except Exception:                                       # noqa: BLE001
            _orbm = 5
        open_ms = int(datetime(day.year, day.month, day.day, 9, 30,
                               tzinfo=ZoneInfo(_ET_ZONE)).timestamp() * 1000) + int(_orbm) * 60_000
        e = float(edge)
        conn = sqlite3.connect(f"file:{feed_db_path()}?mode=ro", uri=True, timeout=5.0)
        try:
            rows = conn.execute(
                "SELECT ts_epoch_ms, close FROM candles WHERE symbol=? AND interval='1m' "
                "AND ts_epoch_ms >= ? AND ts_epoch_ms < ? AND close > 0 ORDER BY ts_epoch_ms",
                (symbol, open_ms, int(before_ms))).fetchall()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        return f"session tape unreadable ({type(exc).__name__}: {exc})"
    fb = ret = None
    for ts, close in rows:
        beyond = (float(close) > e) if direction == "long" else (float(close) < e)
        if fb is None:
            if beyond:
                fb = int(ts)
        elif ret is None:
            if not beyond:
                ret = int(ts)
        elif beyond:
            return None                                         # the side's one re-arm is already spent
    return (fb, ret) if (fb is not None and ret is not None) else None


def break_run_start(symbol: str, day, before_ms: int, direction: str, edge):
    """r316 (BRK.15) - is the signal bar a FRESH break? Reads today's RTH 1m closes from the opening range's close
    (09:35) up to, not including, `before_ms` (the signal bar's start) and returns:

      None   - the latest of those closes is NOT beyond `edge` (or there are none): the signal bar is the first
               close beyond it since the side was inside - a fresh break, the side may fire;
      int    - the ts_ms of the first close of the UNBROKEN run beyond `edge` that the signal bar continues: the
               break already happened and price has not closed back inside since - not a fresh break;
      str    - why the tape could not be read; the caller FAILS CLOSED.

    "Beyond" is strict (a close AT the edge is inside), as r131 and range_rearm(). NEVER raises.
    🔑 The operator, 2026-10-24 13:56 ET: "For now, rearm it on every reentry" - every close back inside re-arms.
    """
    from datetime import datetime
    try:
        import sqlite3
        from zoneinfo import ZoneInfo
        from data.candle_feed import feed_db_path
        try:
            from config import ORB_WINDOW_MINUTES as _orbm
        except Exception:                                       # noqa: BLE001
            _orbm = 5
        open_ms = int(datetime(day.year, day.month, day.day, 9, 30,
                               tzinfo=ZoneInfo(_ET_ZONE)).timestamp() * 1000) + int(_orbm) * 60_000
        e = float(edge)
        conn = sqlite3.connect(f"file:{feed_db_path()}?mode=ro", uri=True, timeout=5.0)
        try:
            rows = conn.execute(
                "SELECT ts_epoch_ms, close FROM candles WHERE symbol=? AND interval='1m' "
                "AND ts_epoch_ms >= ? AND ts_epoch_ms < ? AND close > 0 ORDER BY ts_epoch_ms",
                (symbol, open_ms, int(before_ms))).fetchall()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        return f"session tape unreadable ({type(exc).__name__}: {exc})"
    run = None
    for ts, close in rows:
        beyond = (float(close) > e) if direction == "long" else (float(close) < e)
        if beyond:
            if run is None:
                run = int(ts)
        else:
            run = None                                          # a close back inside re-arms the side
    return run


_REFIRE_SAID: set = set()


def _record_refire(row: dict) -> None:
    """r316 (BRK.15) COUNTERFACTUAL: once per (symbol, side, signal bar) per process, a signal bar where the re-arm
    rule and r131's new-extreme rule DISAGREE, both verdicts and which one decided, to
    data/counterfactual/breakout_refire.jsonl. Never raises; a failed write is logged."""
    key = (row.get("symbol"), row.get("direction"), row.get("signal_bar_ms"))
    if key in _REFIRE_SAID:
        return
    _REFIRE_SAID.add(key)
    try:
        import json, os, time
        d = os.environ.get("OT_COUNTERFACTUAL_DIR") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "counterfactual")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "breakout_refire.jsonl"), "a") as fh:
            fh.write(json.dumps({"ts_epoch": time.time(), "rule": "breakout_refire",
                                 "mode": getattr(config, "BRK_REFIRE_MODE", "rearm"), **row}) + "\n")
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[breakout] re-fire counterfactual row NOT written: %s", exc)


_REARM_SAID: set = set()


def _record_rearm(row: dict) -> None:
    """BRK.12 COUNTERFACTUAL: once per (symbol, side, signal bar) per process, the re-armed break the plan did
    NOT trade, to data/counterfactual/breakout_rearm.jsonl. Never raises; a failed write is logged."""
    key = (row.get("symbol"), row.get("direction"), row.get("signal_bar_ms"))
    if key in _REARM_SAID:
        return
    _REARM_SAID.add(key)
    try:
        import json, os, time
        d = os.environ.get("OT_COUNTERFACTUAL_DIR") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "counterfactual")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "breakout_rearm.jsonl"), "a") as fh:
            fh.write(json.dumps({"ts_epoch": time.time(), "rule": "breakout_rearm",
                                 "mode": getattr(config, "BRK_REARM_MODE", "log"), **row}) + "\n")
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[breakout] re-arm counterfactual row NOT written: %s", exc)


# v1.10 (BRK.6) - what an index records in place of a tape or a book it cannot have.
NA_NO_TAPE = "n/a - cash index, no tape"
NA_NO_BOOK = "n/a - cash index, no book"


def _cash_index(symbol: str) -> bool:
    """config.is_cash_index on the symbol being traded; False if it cannot be asked."""
    try:
        return bool(symbol) and bool(config.is_cash_index(symbol))
    except Exception:                                           # noqa: BLE001
        return False


def _record_stop_choice(prep) -> None:
    """r284 (BRK.11) COUNTERFACTUAL: every FIRE records the 1m stop the old rule
    would have used beside the 5m swing and the stop that traded, so Saturday can
    replay both roads. Never raises; a failed write is logged, never fatal."""
    try:
        import json, os, time
        d = os.environ.get("OT_COUNTERFACTUAL_DIR") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "counterfactual")
        os.makedirs(d, exist_ok=True)
        row = {"ts_epoch": time.time(), "rule": "breakout_stop_5m",
               "mode": getattr(config, "BRK_STOP5M_MODE", "trade"), "direction": prep.direction,
               "entry": prep.price_now, "break_close": prep.break_close, "stop_1m": prep.stop_1m,
               "stop_5m": prep.stop_5m, "stop_used": prep.stop, "premium": prep.premium,
               "strike": float(getattr(prep.contract, "strike", 0) or 0)}
        with open(os.path.join(d, "breakout_stop.jsonl"), "a") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[breakout] stop counterfactual row NOT written: %s", exc)


class BreakoutPreparation:
    """What the search found. `ready` is True ONLY when every bar cleared."""

    __slots__ = ("tick", "spec", "conditions", "unmet", "ready", "direction", "side",
                 "edge", "break_close", "stop", "stop_1m", "stop_5m", "risk", "target", "target_src",
                 "contract", "premium", "r", "trigger", "invalidation",
                 "pool_price", "pool_name", "pool_dist_r", "verdict", "defer_to",
                 "defer_side", "defer_level", "defer_why", "price_now", "orb",
                 "persist", "cash_index")

    def __init__(self, tick, spec):
        self.tick, self.spec = tick, spec
        self.conditions, self.unmet = {}, []
        self.ready = False
        self.direction = self.side = ""
        self.edge = self.break_close = self.stop = self.risk = None
        self.stop_1m = self.stop_5m = None
        self.target = self.target_src = None
        self.contract = self.premium = self.r = None
        self.trigger = self.invalidation = None
        self.pool_price = self.pool_name = self.pool_dist_r = None
        self.verdict, self.defer_to = "WAIT", ""
        self.defer_side = self.defer_level = self.defer_why = None
        self.price_now = self.orb = None
        self.persist = ()
        self.cash_index = False

    def cond(self, name, current, met, note: str = ""):
        """Record one declared bar: its value now, and whether it cleared.

        🔑 EVERY BAR IS A REAL TRIGGER. r55 briefly made the informers BYPASS
        this method during the research window; the operator ruled otherwise —
        *"I still want the informer set as triggers in the strategy package, but
        set the acceptance to 'all'."* That is the better shape: the plan still
        refuses to form unless EVERY bar clears, and what changed is the
        ACCEPTANCE BAND, declared on the spec beside the bar it belongs to.
        Nothing here is special-cased, so nothing here has to be un-special-cased
        when the window closes.
        ⚠️ AND THE FIT DOES NOT NEED A BYPASS TO BE POSSIBLE: each informer's
        CONTINUOUS value is recorded every tick (`flow_imbalance`, `regime`,
        `depth_ratio`, `pool_dist_r`, `range_width_pct`), so any threshold can be
        fitted afterwards from the values themselves — which is strictly more
        than a stored would-have boolean could ever have told us.
        """
        required = self.spec.CONDITIONS.get(name, "")
        self.conditions[name] = (current, required, bool(met))
        if not met:
            self.unmet.append(name)
        self.tick.check(name, current if isinstance(current, (int, float)) else None,
                        bool(met), note=note)

    def trade_line(self) -> str:
        if not self.ready:
            return "no trade prepared"
        still = ", ".join(self.persist) or "nothing"
        return (f"buy {float(self.contract.strike):g}{self.side[0].upper()} @ "
                f"{self.premium:.2f}  stop {self.stop:.2f} ({self.risk:.2f} risk)  "
                f"target {self.target:.2f} via {self.target_src}  R {self.r:.2f}  "
                f"— execute IF {still} are STILL true AND price holds beyond "
                f"{self.trigger:.2f}")

    def emit(self, strategy_name: str):
        """Build the signal from what the PLAN selected. The strategy picks nothing."""
        # 🔴 r77 — `OptionsSignal` LIVES IN base_strategy, NOT structure.
        # This raised ImportError on EVERY tick from the moment Breakout first
        # had a signal to build: 127 crashes on 2026-09-21, first at 09:37:04,
        # and the strategy has NEVER ONCE produced a trade.
        # ⚠️ WHY NOTHING CAUGHT IT. The import is LAZY — inside emit() — so the
        # module imports cleanly and `check_imports` passes; the path only runs
        # when a breakout actually forms. And `_safe_strategy` CATCHES the
        # raise, logs it and continues, so the board showed a stale skip label
        # ("position open — managing") instead of a crash. A gate that reads
        # source text, a checker that imports the module, and a dashboard that
        # reads plan rows were ALL blind to it simultaneously.
        from strategy.base_strategy import OptionsSignal as Signal
        c = self.contract
        sig = Signal(
            strategy_name=strategy_name,
            setup_type=f"breakout_{self.direction}",
            direction=self.direction,
            option_side=self.side,
            underlying_entry=float(self.price_now),
            underlying_stop=float(self.stop),
            underlying_target=float(self.target),
            orb_range_high=float(getattr(self.orb, "orb_high", 0.0) or 0.0),
            orb_range_low=float(getattr(self.orb, "orb_low", 0.0) or 0.0),
            strike=c.strike, expiry=getattr(c, "expiry", ""),
            entry_premium=c.mark, contract=c,
            # 🔴 r91 — THE SIZING INPUT THE 1-R RULE NEEDS, same as the ORB's.
            # `underlying_stop` is the break candle's extreme in POINTS; this
            # converts it to PREMIUM so `stop_premium()` is the structure stop.
            # ⚠️ PARITY IS THE POINT HERE: Breakout exists to be the ORB
            # without the retest, so a sizing input the ORB supplies and this
            # does not would make the A/B a comparison of two sizers.
            entry_delta=getattr(c, "delta", None),
        )
        sig.is_breakout = True
        # 🔑 THE ORB'S SIZING, BY SUPPLYING THE GEOMETRY RATHER THAN BY BEING
        # NAMED. RiskManager.size_for's own docstring: *"Geometry is a sub-rule
        # of long_debit, selected by the caller SUPPLYING orb_width /
        # orb_stop_distance rather than by naming ORB. A second strategy that
        # wants risk-normalised sizing supplies the geometry; it does not get
        # added to a list somewhere that later rots."* Breakout is that second
        # strategy. ⚠️ The flag is explicit because the hunt and the runaway
        # ALSO carry orb_range_high/low — keying on the field would silently
        # re-size two strategies that never asked for it.
        sig.sizes_on_geometry = True
        sig.breakout_edge = self.edge
        sig.breakout_target_src = self.target_src
        sig.disarms_retest = False          # the ORB keeps its own arm
        logger.info("[breakout] FIRE %s — %s", self.direction, self.trade_line())
        _record_stop_choice(self)                                         # r284 (BRK.11)
        return self.tick.take(sig)


class BreakoutPlan:
    name = "Breakout"

    def __init__(self, store=None):
        from strategy.breakout import Breakout as _Spec
        self.planner = Plan(self.name, _Spec.PLAN_CHECKS, self_ledgers=True)
        self._store = store

    def _store_(self):
        if self._store is not None:
            return self._store
        try:
            from data.derived_store import get_derived_store
            return get_derived_store()
        except Exception:                                       # noqa: BLE001
            return None

    # ── the search ────────────────────────────────────────────────────────
    def prepare(self, *, spec, orb, price_now, now_et, chain=None, df_1m=None,
                flow_conn=None, symbol: str = "", **_ignored) -> BreakoutPreparation:
        from strategy import breakout as B

        t = self.planner.tick(price_now)
        prep = BreakoutPreparation(t, spec)
        prep.price_now, prep.orb = _f(price_now), orb

        # ── the window. DORMANT writes one row and goes quiet (r41) ─────────
        hm = _hm(now_et)
        _lo, _hi = _et(B.EARLIEST_ET), _et(B.LATEST_ET)
        # r254 (OBS.1) - past the END only, and only when main.py published this name as
        # observed THIS tick: the plan keeps looking; nothing it fires is executed.
        _obs = bool(hm is not None and _lo is not None and _hi is not None and hm >= _hi
                    and _observe.is_active("Breakout"))
        if hm is None or _lo is None or _hi is None or not (_lo <= hm < _hi):
            if not _obs:
                t.dormant("entry_window",
                          f"outside {B.EARLIEST_ET}-{B.LATEST_ET} ET — observing only")
                return prep
        prep.cond("entry_window", None, True)
        if _obs:
            t.note(f"LOG-ONLY - past the {B.LATEST_ET} ET entry end: observed, recorded, never executed (OBS.1)")

        px = prep.price_now
        if px is None or df_1m is None or len(df_1m) < 2:
            t.starved("price" if px is None else "df_1m")
            return prep

        # ── the range, and whether it is one ───────────────────────────────
        hi, lo = _f(getattr(orb, "orb_high", None)), _f(getattr(orb, "orb_low", None))
        width = (hi - lo) if (hi and lo and hi > lo) else None
        wpct = (width / px) if (width and px) else None
        t.check("range_width_pct", wpct, None)
        prep.cond("orb_range", wpct, B.accepts("orb_range", wpct))

        # ── nothing live inside it (r39 retires them TRAVERSED) ────────────
        board = self._board(px, hi, lo)
        board_ok = str(board.get("state") or "") == "ok"          # r299 (BRK.14)
        inside = [l for l in (board.get("above", []) + board.get("below", []))
                  if hi and lo and lo <= float(l.get("price") or 0) <= hi]
        _rc = float(len(inside)) if board_ok else None            # an unreadable board is not a clean range
        prep.cond("range_clean", _rc, B.accepts("range_clean", _rc))

        # ── THE BREAK: a CLOSED bar's CLOSE beyond the edge (r5) ───────────
        # r44 (BAR.1) - the last bar CLOSED BY TIME; iloc[-2] was a minute stale on a
        # tick before the new minute's first row (META 10-27 10:10:00 fired on 10:08)
        cp = _closed_pos(df_1m, now_et)
        bar = df_1m.iloc[cp]
        bc = _f(bar.get("close") if hasattr(bar, "get") else bar["close"])
        direction = ("long" if (hi and bc and bc > hi)
                     else "short" if (lo and bc and bc < lo) else "")
        prep.direction = direction
        prep.side = "call" if direction == "long" else "put" if direction == "short" else ""
        prep.edge = hi if direction == "long" else lo if direction == "short" else None
        prep.break_close = bc
        t.check("break_dir", None, None, note=direction or "none")
        t.check("break_close_px", bc, None)
        prep.cond("break_close", bc, bool(direction))

        # volume multiple — RECORDED, NEVER GATED (measured useless, n=736)
        try:
            ob = df_1m.iloc[:5]
            base = float(ob["volume"].mean()) if "volume" in ob else 0.0
            bv = _f(bar.get("volume") if hasattr(bar, "get") else bar["volume"]) or 0.0
            t.check("vol_multiple", (bv / base) if base > 0 else None, None)
        except Exception:                                       # noqa: BLE001
            t.check("vol_multiple", None, None)

        # ── the three a stop run cannot manufacture ────────────────────────
        # v1.10 (BRK.6) - a cash index has no tape and no book: n/a, MET, never a refusal.
        prep.cash_index = _cash_index(symbol or self._symbol())
        imb, tag = self._flow(flow_conn, symbol)
        t.check("flow_imbalance", imb, None)
        t.check("flow_tagged", tag, None)
        signed = (imb if direction == "long" else -imb) if imb is not None else None
        if prep.cash_index:
            prep.cond("flow_commit", signed, True, note=NA_NO_TAPE)
        else:
            prep.cond("flow_commit", signed,
                      bool(signed is not None and tag is not None
                           and B.accepts("flow_commit", signed)
                           and B.accepts("flow_tagged", tag)))

        reg = self._regime()
        t.check("regime", reg, None)
        prep.cond("gamma_regime", reg, B.accepts("gamma_regime", reg))

        dep = self._depth(flow_conn, symbol, direction)
        t.check("depth_ratio", dep, None)
        if prep.cash_index:
            prep.cond("depth_thin", dep, True, note=NA_NO_BOOK)
        else:
            prep.cond("depth_thin", dep, B.accepts("depth_thin", dep))

        # ── the structure: stop, risk, reach, room ─────────────────────────
        bhi = _f(bar.get("high") if hasattr(bar, "get") else bar["high"])
        blo = _f(bar.get("low") if hasattr(bar, "get") else bar["low"])
        prep.stop = blo if direction == "long" else bhi
        prep.stop_1m = prep.stop
        # r284 (BRK.11) - THE STOP IS THE 5m SWING: the farther of the break bar's
        # extreme and the last closed 5m bars' (never tighter than the 1m stop).
        _mode = getattr(config, "BRK_STOP5M_MODE", "trade")
        if direction and prep.stop and _mode != "off":
            _sts = _bar_stamp(df_1m, cp)
            sw = (swing_5m_stop(symbol or self._symbol(), _sts.date(),
                                int(_sts.timestamp() * 1000) + 60_000, direction,
                                int(getattr(config, "BRK_STOP5M_BARS", 3)))
                  if _sts is not None else "signal bar has no timestamp")
            if isinstance(sw, str):
                t.check("stop_5m", None, None, note=f"{sw} - the 1m stop stands")
            elif sw is not None:
                prep.stop_5m = (max(sw, prep.stop) if direction == "short" else min(sw, prep.stop))
                t.check("stop_5m", prep.stop_5m, None,
                        note=f"1m stop {prep.stop_1m:.2f}; OT_BRK_STOP5M={_mode}")
                if _mode == "trade":
                    prep.stop = prep.stop_5m
        t.check("stop_1m", prep.stop_1m, None)
        prep.risk = abs(bc - prep.stop) if (bc and prep.stop) else None

        pool = self._pool(board, px, direction)
        prep.pool_price = pool[0] if pool else None
        prep.pool_name = pool[1] if pool else None
        prep.pool_dist_r = ((abs(prep.pool_price - bc) / prep.risk)
                            if (pool and prep.risk and prep.risk > 0 and bc) else None)
        t.check("pool_price", prep.pool_price, None)
        t.check("pool_name", None, None, note=str(prep.pool_name or "open air"))
        t.check("pool_dist_r", prep.pool_dist_r, None)
        # r299 (BRK.14): "no pool" is open air only when the board was READ; an unreadable board is None
        prep.cond("room_to_run", prep.pool_dist_r if board_ok else None,
                  bool((board_ok and pool is None)
                       or B.accepts("room_to_run", (prep.pool_dist_r or 0) if board_ok else None)))

        # the reach: the NEARER of the measured move and the pool's near edge
        measured = (bc + width) if (direction == "long" and bc and width) else \
                   (bc - width) if (direction == "short" and bc and width) else None
        t.check("reach_measured", measured, None)
        t.check("reach_pool", prep.pool_price, None)
        prep.target, prep.target_src = self._reach(direction, measured, prep.pool_price)

        # ── EVERY BAR MUST CLEAR, OR NO PLAN GOES FORWARD ──────────────────
        if prep.unmet:
            return self._route(prep, t, B)

        # ══ r316 (BRK.15) — A SIDE FIRES ON A FRESH BREAK; EVERY RETURN TO THE RANGE RE-ARMS IT ═══
        # The operator, 2026-10-24: *"The new session high/low rule needs to be dropped"*; *"For now, rearm
        # it on every reentry"*. OT_BRK_REFIRE=extreme restores r131 (the block below it, unchanged).
        if getattr(config, "BRK_REFIRE_MODE", "rearm") == "extreme":
            if not self._new_extreme(t, B, direction, df_1m, bc, symbol, edge=prep.edge, cp=cp):
                self._refire_shadow(direction, df_1m, bc, symbol, prep.edge, decided=False, cp=cp)
                return prep
            self._refire_shadow(direction, df_1m, bc, symbol, prep.edge, decided=True, cp=cp)
        elif not self._refire(t, B, direction, df_1m, bc, symbol, edge=prep.edge, cp=cp):
            return prep
        # ══ r131 — A RE-FIRE ON A SIDE NEEDS A NEW SESSION EXTREME (OT_BRK_REFIRE=extreme only, since r316) ══
        # Operator, 2026-09-24: *"A new reclaimed level has to happen before it
        # can fire again? A new high for a long, a new low for a short."* The
        # FIRST entry per side keeps the break trigger above untouched; every
        # later one must CLOSE beyond every prior RTH bar's extreme.

        # ── the structural bars: a contract, an R that clears the floor ────
        from strategy.orb_plan import select_contract
        prep.contract = (select_contract(chain, direction, prep.target, inside=bool(prep.cash_index))
                         if chain else None)                            # r259 (STRK.2)
        t.check("contract", None, prep.contract is not None)
        if prep.contract is None:
            t.refuse("contract", "no listed strike with a live quote at or inside the reach"
                     if prep.cash_index else "no listed strike with a live quote at the reach")
            return prep
        prep.premium = _f(getattr(prep.contract, "mark", None))
        t.check("premium", prep.premium, bool(prep.premium and prep.premium > QUOTE_FLOOR))
        if not prep.premium or prep.premium <= QUOTE_FLOOR:
            t.refuse("premium", "the contract has no live quote")
            return prep
        reach = abs((prep.target or bc) - bc)
        prep.r = (reach / prep.risk) if (prep.risk and prep.risk > 0) else None
        t.check("r", prep.r, B.accepts("r", prep.r))
        t.check("stop_survivable", prep.risk, bool(prep.risk and prep.risk > 0))
        t.check("target", prep.target, prep.target is not None)
        if not B.accepts("r", prep.r):
            t.refuse("r", f"R {prep.r:.2f} outside acceptance "
                          f"{B.acceptance('r')}" if prep.r else "R unmeasurable")
            return prep
        # r263 (BRK.7) — A BREAK BAR THAT CLOSED AT ITS OWN EXTREME HAS NO RISK: the stop IS the close, so R
        # is unmeasurable and nothing can be sized. While `r` accepts "any" (research) an absent R passed
        # here and trade_line crashed formatting it (TypeError, 133 times 10-07/10-08 across both boxes, all
        # in LOG-ONLY hours). FEASIBILITY: refused, recorded, never raised.
        if not (prep.risk and prep.risk > 0):
            t.refuse("stop_survivable", "zero risk: the break bar closed at its own extreme")
            return prep

        # ══ THE TRIGGER, AND IT IS COMPOUND ═══════════════════════════════
        # Operator, 2026-09-18: *"the plan will say IF ALL OF THOSE CONDITIONS
        # ARE STILL TRUE and price reaches X, then everything is satisfied."*
        # The settled bars are facts and stay decided. The PERSISTENT ones are
        # live state and are re-read on the tick that fires — a regime can flip
        # and a book can refill between the plan and the fill, and a trade taken
        # on expired evidence is the fakeout this strategy exists to avoid.
        prep.persist = tuple(spec.PERSISTENT)
        t.check("persist_ok", float(len(prep.persist)), True,
                note="must still hold at execution: " + ", ".join(prep.persist))
        prep.trigger, prep.invalidation = prep.edge, prep.edge
        t.anchor(trigger=prep.trigger, invalidation=prep.invalidation)
        t.debit_directional(prep.premium, getattr(prep.contract, "delta", None),
                            getattr(prep.contract, "gamma", None),
                            prep.risk, reach,
                            invalidation=prep.invalidation, trigger=prep.trigger)
        prep.ready, prep.verdict = True, "TAKE"
        t.check("verdict", None, None, note="TAKE")
        t.note(f"all {len(spec.CONDITIONS)} conditions true — {prep.trade_line()}")
        return prep

    # ── r131: the re-fire gate ─────────────────────────────────────────────
    def _refire(self, t, B, direction, df_1m, bc, symbol, edge=None, cp: int = -2) -> bool:
        """r316 (BRK.15) - True when this side may fire: the signal bar is a FRESH break (the first 1m close
        beyond the edge since 09:35 or since the side's latest close back inside it) and it is not a bar that
        already fired. Refuses at `B.FRESH_BREAK` otherwise. r131's new-extreme verdict is computed beside it,
        decides nothing, and is written to breakout_refire.jsonl wherever the two disagree.

        ⚠️ EVERY FACT IT DECIDES ON IS READ FROM A BOOK (DEC.1): the side's entries from trades.db, the
        session's closes from the feed store. Either unreadable FAILS CLOSED.
        """
        gate = B.FRESH_BREAK
        sig_ts = _bar_stamp(df_1m, cp)                          # r44 (BAR.1): prepare's closed bar
        if sig_ts is None or edge is None:
            t.refuse(gate, "the signal bar carries no timestamp or the side no edge, so the session's "
                           "closes cannot be bounded - failing closed")
            return False
        day = sig_ts.date()
        ents = side_entries_today(direction, day)
        t.check("side_fired_today", None if ents is None else float(len(ents)), None)
        if ents is None:
            t.refuse(gate, f"cannot tell whether {direction} already fired on this bar - "
                           f"trades.db unreadable, failing closed")
            return False
        # 🔴 r142, KEPT: a bar that started before the side's latest entry already fired it.
        if ents:
            _last = ents[-1]
            if sig_ts < _last.replace(second=0, microsecond=0):
                t.refuse(gate, f"no bar has closed since the last {direction} entry at "
                               f"{_last.strftime('%H:%M:%S')} - the signal bar "
                               f"{sig_ts.strftime('%H:%M')} already fired it")
                return False
        sym = symbol or self._symbol()
        sig_ms = int(sig_ts.timestamp() * 1000)
        run = break_run_start(sym, day, sig_ms, direction, edge)
        if isinstance(run, str):
            t.check("break_run_from", None, None)
            t.refuse(gate, f"{run} - cannot tell whether this {direction} break is fresh, failing closed")
            return False
        ok = run is None
        if ok:
            t.check(gate, bc, True, note=f"a fresh {direction} break: the first close beyond "
                                         f"{float(edge):.2f} since the side was inside")
        else:
            from datetime import datetime as _dt
            from zoneinfo import ZoneInfo as _Z
            _rt = _dt.fromtimestamp(run / 1000, _Z(_ET_ZONE)).strftime("%H:%M")
            t.check("break_run_from", float(run), None)
            t.check(gate, bc, False)
            t.refuse(gate, f"the {direction} break began at {_rt} and has not closed back inside "
                           f"{float(edge):.2f} since - a close back inside re-arms the side")
        self._refire_shadow(direction, df_1m, bc, symbol, edge, decided=ok, rearm=(ok, run),
                            fired=len(ents), cp=cp)
        return ok

    def _refire_shadow(self, direction, df_1m, bc, symbol, edge, *, decided, rearm=None, fired=None,
                       cp: int = -2) -> None:
        """r316 (BRK.15) - the OTHER rule's verdict on this signal bar, written to breakout_refire.jsonl when it
        disagrees with the one that decided. NEVER raises and touches no tick record."""
        try:
            sig_ts = _bar_stamp(df_1m, cp)                      # r44 (BAR.1)
            if sig_ts is None or edge is None or bc is None:
                return
            day, sym, sig_ms = sig_ts.date(), (symbol or self._symbol()), int(sig_ts.timestamp() * 1000)
            if fired is None:
                ents = side_entries_today(direction, day)
                fired = None if ents is None else len(ents)
            if rearm is None:
                run = break_run_start(sym, day, sig_ms, direction, edge)
                rearm = (None if isinstance(run, str) else run is None, None if isinstance(run, str) else run)
            # r131's verdict, as _new_extreme() would reach it, without its tick record
            ext_ok, level = None, None
            first = fired == 0 and first_break_before(sym, day, sig_ms, direction, edge) is None
            if first:
                ext_ok = True
            else:
                ext = session_extreme(sym, day, sig_ms, direction)
                if not isinstance(ext, str):
                    level = ext[0]
                    ext_ok = bool(bc > level if direction == "long" else bc < level)
            mode = getattr(config, "BRK_REFIRE_MODE", "rearm")
            if rearm[0] is None or ext_ok is None or rearm[0] == ext_ok:
                return
            _record_refire({"symbol": sym, "direction": direction, "signal_bar_ms": sig_ms,
                            "edge": float(edge), "break_close": float(bc),
                            "rearm_ok": rearm[0], "break_run_from_ms": rearm[1],
                            "new_extreme_ok": ext_ok, "session_extreme": level,
                            "fired_on_side": fired, "decided_by": mode, "fired": bool(decided)})
        except Exception as exc:                                # noqa: BLE001
            logger.debug("[breakout] re-fire shadow not computed: %s", exc)

    def _new_extreme(self, t, B, direction, df_1m, bc, symbol, edge=None, cp: int = -2) -> bool:
        """True when this side may fire. Refuses at `B.NEW_EXTREME` otherwise.

        ⚠️ EVERY FACT IT DECIDES ON IS READ FROM A BOOK, NEVER HELD HERE: the
        side's entries from trades.db, the session's bars from the feed store.
        A fresh plan object (a restart, a bake) reaches the same verdict.
        """
        gate = B.NEW_EXTREME
        sig_ts = _bar_stamp(df_1m, cp)                          # r44 (BAR.1)
        day = sig_ts.date() if sig_ts is not None else _today_et()
        ents = side_entries_today(direction, day)
        fired = None if ents is None else len(ents)
        t.check("side_fired_today", None if fired is None else float(fired), None)
        if fired is None:
            t.refuse(gate, f"cannot tell whether {direction} already fired today — "
                           f"trades.db unreadable, failing closed")
            return False
        if fired == 0:
            # 🔴 r282 (BRK.10) — "FIRST" MEANS THE TAPE'S FIRST BREAK, NOT THE BOOK'S
            # FIRST FILL. An earlier closed bar beyond the edge (a break the gates
            # refused) makes this a re-fire: it needs a new session extreme too.
            if edge is None or sig_ts is None:
                t.check(gate, bc, True, note=f"first {direction} entry today — "
                                             f"the break close is the trigger")
                return True
            fb = first_break_before(symbol or self._symbol(), day,
                                    int(sig_ts.timestamp() * 1000), direction, edge)
            if isinstance(fb, str):
                t.check("first_break", None, None)
                t.refuse(gate, f"{fb} — cannot tell whether the {direction} break "
                               f"already happened, failing closed")
                return False
            if fb is None:
                t.check(gate, bc, True, note=f"first {direction} entry today — "
                                             f"the break close is the trigger")
                return True
            from datetime import datetime as _dt
            from zoneinfo import ZoneInfo as _Z
            _fbt = _dt.fromtimestamp(fb / 1000, _Z(_ET_ZONE)).strftime("%H:%M")
            t.check("first_break", float(fb), None,
                    note=f"the {direction} break first closed at {_fbt} with no "
                         f"{direction} filled since — this needs a new session extreme")
        if sig_ts is None:
            t.refuse(gate, "the signal bar carries no timestamp, so the prior "
                           "session bars cannot be bounded — failing closed")
            return False
        # 🔴 r142 — THE SIGNAL BAR MUST HAVE CLOSED AFTER THE LAST ENTRY. The
        # latest same-side entry's MINUTE is the earliest a fresh signal bar
        # may start: a bar starting before it had already closed when that
        # entry fired, so it cannot be "a new high" relative to it.
        if ents:
            _last = ents[-1]
            _fresh_from = _last.replace(second=0, microsecond=0)
            if sig_ts < _fresh_from:
                t.refuse(gate, f"no bar has closed since the last {direction} entry at "
                               f"{_last.strftime('%H:%M:%S')} — the signal bar "
                               f"{sig_ts.strftime('%H:%M')} already fired it "
                               f"(fired {fired} on this side today)")
                return False
        # 🔴 BRK.12 — A RETURN TO THE RANGE RE-ARMS THE SIDE, ONCE - RECORDED, NEVER TRADED. The operator,
        # 2026-10-14 11:38 ET: "I want a return of the range to enable another breakout in either direction";
        # 2026-10-15 10:16 ET: "Concur on all" (to "record-only"). The would-be fire is written below, after the
        # new-extreme verdict it is set beside; that verdict alone decides.
        ra = None
        if edge is not None and getattr(config, "BRK_REARM_MODE", "log") == "log":
            ra = range_rearm(symbol or self._symbol(), day, int(sig_ts.timestamp() * 1000), direction, edge)
            if isinstance(ra, str):
                t.check("range_rearm", None, None, note=f"{ra} — nothing recorded")
                ra = None
            elif ra:
                from datetime import datetime as _dt
                from zoneinfo import ZoneInfo as _Z
                _rt = _dt.fromtimestamp(ra[1] / 1000, _Z(_ET_ZONE)).strftime("%H:%M")
                t.check("range_rearm", float(ra[1]), None,
                        note=f"the {direction} side returned into the range at {_rt} — a re-armed break, "
                             f"RECORDED ONLY (BRK.12); the new-extreme rule decides")
        ext = session_extreme(symbol or self._symbol(), day,
                              int(sig_ts.timestamp() * 1000), direction)
        if ra:
            _record_rearm({"symbol": symbol or self._symbol(), "direction": direction,
                           "signal_bar_ms": int(sig_ts.timestamp() * 1000), "edge": float(edge),
                           "first_break_ms": ra[0], "return_ms": ra[1], "break_close": bc,
                           "session_extreme": None if isinstance(ext, str) else ext[0],
                           "new_extreme_ok": (None if isinstance(ext, str) or bc is None else
                                              bool(bc > ext[0] if direction == "long" else bc < ext[0])),
                           "fired_on_side": fired})
        if isinstance(ext, str):
            t.check("session_extreme", None, None)
            t.refuse(gate, f"{ext} — failing closed (fired {fired} {direction} today)")
            return False
        level, nbars = ext
        t.check("session_extreme", level, None,
                note=f"session {'high' if direction == 'long' else 'low'} "
                     f"{level:.2f} over {nbars} RTH bars since 09:30")
        ok = bool(bc is not None and (bc > level if direction == "long" else bc < level))
        t.check(gate, bc, ok)
        if not ok:
            t.refuse(gate, f"last close {bc:.2f} not "
                           f"{'above session high' if direction == 'long' else 'below session low'} "
                           f"{level:.2f} (fired {fired} on this side today)")
            return False
        return True

    # ── the router: a refusal that names the trade that SHOULD take it ─────
    def _route(self, prep, t, B):
        """Not every failure is the same failure.

        🔑 THE HARVEST SHAPE IS SPECIFIC: a pool sitting where the stops are,
        and the tape or the book saying the level is being defended rather than
        given up. That is not "no trade" — it is the SWEEP's trade, or the
        HUNT's, and the plan says so with `permit()` rather than going quiet.
        ⚠️ WAIT IS THE DEFAULT. Only the named shape defers; anything else is
        an ordinary DECLINE, because a permission issued on a shrug is worse
        than silence.
        """
        # ⚠️ THE FADE ROUTE READS THE FITTED DIAL, NOT THE LIVE ACCEPTANCE.
        # While acceptance is "any" every pool distance clears room_to_run, so
        # asking "did room_to_run fail?" would never route a harvest to the
        # sweep. The ROUTING question is "is a pool sitting in the path?", which
        # is a fact about the tape and not an acceptance band.
        pooled = (prep.pool_dist_r is not None
                  and prep.pool_dist_r < B.FITTED_ROOM_MIN_R)
        # 🔴 THIS READ `prep.unmet` UNTIL r59, WHICH MADE THE FADE ROUTE DEAD
        # FOR THE WHOLE RESEARCH WINDOW. With acceptance at "any" NOTHING is
        # ever unmet, so `fading` was permanently False and DEFER->HUNT /
        # DEFER->SWEEP could not fire — the twin of the `pooled` bug fixed
        # beside it, caught only because the operator said he wanted the
        # breakout and the hunt tailored for BOTH a real break and a fakeout
        # grab. Routing reads the FITTED dials, like `pooled` does.
        _reg = (prep.conditions.get("gamma_regime") or (None,))[0]
        _dep = (prep.conditions.get("depth_thin") or (None,))[0]
        # v1.10: an index's absent book is n/a, not a book being defended
        fading = (not B.accepts_fitted("gamma_regime", _reg)
                  or (not prep.cash_index and not B.accepts_fitted("depth_thin", _dep)))
        if pooled and fading and prep.direction and prep.pool_price:
            # price will REACH the pool and stop there -> the hunt has a target
            # it never gives way at all -> the sweep fades the level
            reached = "flow_commit" not in prep.unmet
            prep.defer_to = "LiquidityHunt" if reached else "SweepCreditSpread"
            prep.defer_side = ("put" if prep.direction == "long" else "call") \
                if not reached else prep.side
            prep.defer_level = prep.pool_price
            prep.verdict = "DEFER"
            prep.defer_why = (f"breakout bars failed as a HARVEST: pool "
                              f"{prep.pool_name} at {prep.pool_price:.2f} "
                              f"({prep.pool_dist_r:.2f}R), unmet={','.join(prep.unmet)}")
            t.check("verdict", None, None, note=f"DEFER->{prep.defer_to}")
            t.check("defer_to", None, None, note=prep.defer_to)
            logger.info("[breakout] DEFER -> %s  %s", prep.defer_to, prep.defer_why)
            t.permit(prep.defer_side, prep.defer_level, source=self.name,
                     why=prep.defer_why)
            return prep
        t.check("verdict", None, None, note="WAIT")
        t.hold(f"waiting on: {', '.join(prep.unmet)}")
        return prep

    # ── readers, each failing to None rather than raising ─────────────────
    _BOARD_SAID: set = set()      # r299: the board's failure state is said ONCE per state per process

    def _board(self, px, hi, lo) -> dict:
        """The level board, with its STATE. r299 (BRK.14): a failed read is no longer an empty dict
        that range_clean counted as "nothing inside" and room_to_run as "open air" - after the
        research window that was two informers silently disabled by a store hiccup (audit
        2026-10-18 D3). The callers read `state`; anything but "ok" makes their readings None."""
        try:
            from derived.levels import board_for
            b = board_for(self._store_(), self._symbol(), px, hi, lo) or {}
        except Exception as exc:                                # noqa: BLE001
            b = {"state": f"unavailable ({type(exc).__name__}: {exc})", "above": [], "below": []}
        st = str(b.get("state") or "unavailable (no state)")
        if st != "ok" and st not in BreakoutPlan._BOARD_SAID:
            BreakoutPlan._BOARD_SAID.add(st)
            from strategy import breakout as _B               # this module imports the spec per method
            logger.warning("[breakout] level board %s — range_clean and room_to_run read as UNREADABLE "
                           "(admitted while ACCEPTANCE=any, refused once the dials get numbers on %s)",
                           st, _B.RESEARCH_UNTIL)
        return b

    @staticmethod
    def _symbol() -> str:
        try:
            return str(getattr(config, "INSTRUMENT", "") or "")
        except Exception:                                       # noqa: BLE001
            return ""

    @staticmethod
    def _flow(conn, symbol):
        if conn is None:
            return None, None
        try:
            from analysis.order_flow import aggression
            a = aggression(conn, symbol or BreakoutPlan._symbol())
            return (_f((a or {}).get("imbalance")), _f((a or {}).get("tagged_frac")))
        except Exception as exc:                                # noqa: BLE001
            logger.debug("[breakout] aggression unavailable: %s", exc)
            return None, None

    @staticmethod
    def _regime():
        try:
            from derived.gamma_regime import regime
            return _f(regime())
        except Exception as exc:                                # noqa: BLE001
            logger.debug("[breakout] regime unavailable: %s", exc)
            return None

    @staticmethod
    def _depth(conn, symbol, direction=None):
        """Depletion as a signed ratio: positive = thinning ahead of price.

        r188: AHEAD OF PRICE is the ask for a long and the bid for a short.
        `order_flow.depth()` gives each side's size now over its size at the
        start of the window (`ask_depth_ratio`, `bid_depth_ratio`), so the
        depletion is 1 - that ratio. Until r188 this read `depth_now` /
        `depth_before`, which depth() never returned: None on every tick.
        """
        if conn is None or direction not in ("long", "short"):
            return None
        try:
            from analysis.order_flow import depth
            d = depth(conn, symbol or BreakoutPlan._symbol()) or {}
            ratio = _f(d.get("ask_depth_ratio" if direction == "long"
                             else "bid_depth_ratio"))
            if ratio is None:
                return None
            return 1.0 - ratio
        except Exception as exc:                                # noqa: BLE001
            logger.debug("[breakout] depth unavailable: %s", exc)
            return None

    @staticmethod
    def _pool(board, px, direction):
        """The nearest NAMED level ahead of the break, or None for open air."""
        side = board.get("above" if direction == "long" else "below", []) or []
        for l in side:
            p = _f(l.get("near_edge") if "near_edge" in l else l.get("price"))
            if p is None:
                continue
            return p, str(l.get("provenance") or "level")
        return None

    @staticmethod
    def _reach(direction, measured, pool):
        """The NEARER of the measured move and the pool — the operator's ruling.

        *"even a fakeout eventually has to go where the orders are resting"* — a
        measured move projecting THROUGH a resting shelf projects through the
        orders that will stop it.
        """
        if measured is None:
            return (pool, "pool") if pool is not None else (None, "")
        if pool is None:
            return measured, "measured_move"
        nearer = min(measured, pool) if direction == "long" else max(measured, pool)
        return nearer, ("pool" if nearer == pool else "measured_move")
