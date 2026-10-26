"""
data/candle_feed.py  v5.2
v5.2  2026-10-25  (LVL.20) — A HALF DAY'S RTH ENDS AT ITS BELL. _within_rth ended every intraday window at a FIXED
      16:00 (1h 16:30), so on 2026-11-27 and 12-24 (13:00 close) the 13:00-16:00 bars would be written to the plain RTH
      series and every RTH reader (opening range, session extremes, the level book) would read three after-hours hours
      as the session. The window's end moves earlier by utils.market_calendar.close_shift_minutes (180 on a 13:00 day,
      else 0); a calendar fault keeps the 16:00 window and never drops the write. Port of otv4 r494 (FEED.11), the
      shared half OTV4TEST r300 left open. Gate tests/check_half_day_rth.py H1-H8.
v5.1  2026-10-25  OTV5 r16 (PRIME.1) — A SYMBOL THIS STORE HAS NEVER HELD IS PRIMED FROM TASTYTRADE, DEEP; ANYTHING ELSE
      BACKFILLS AS BEFORE. The operator, 2026-10-25: prime "from tasty trade of whatever's obtainable", never from S3 ("if
      we haven't traded it recently last July's data ... isn't relevant"), "only priming missing data - there is no reason
      to prime stuff that's already on the box", and only at a symbol switch. _backfill_start takes the store's newest
      held bar for that (store symbol, interval): NONE held (a fresh box, or the symbol just switched to) -> PRIME_DAYS
      deep; held -> the old start (BACKFILL_DAYS / today's open), reaching back to the newest held bar if the box was down
      longer, never deeper than PRIME_DAYS. Recomputed at EVERY (re)subscribe from the store, so a reconnect replays only
      what a restart would. TastyTrade's reach, MEASURED 2026-10-25 by QQQ-TEST (MSG-QQQ-1025-14, every ask 20 years back):
      8,000 bars per subscription from the newest back (1m RTH ~21 sessions, 1m EXT ~8, 5m EXT ~34 sessions), else time
      windows (5m/15m ~3 months, 1h ~9.5 months, 1d to 2022-12-29). PRIME_DAYS stays inside RETENTION_DAYS (1m 60, 5m/15m
      30, 1h 60) so the nightly purge never deletes what was just primed; 1d (no retention) 400 days, which clears
      sma50_mtf's 55. A held bar is rewritten only under FEED.9b / FEED.10, unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.21 2026-10-12  OTV4TEST r277 (FEED.10b) — THE REFEREE WAITS 60 s, NOT 5, AND AN IDENTICAL REPLAY IS SILENT. From
      1-REPORTER's critique (MSG-1REP-1012-12): the feed writes in flush batches, so a bar's FINAL live update can
      land a few seconds after its close while its last 1m is still partial in the store; r276 (5 s) refereed it
      against that short 1m sum and KEPT the stale bar (pinned: check_bar_referee R11, red on r276). Only a bar
      closed REFEREE_CLOSE_GRACE_S = 60 s ago is refereed; every live final update takes the FEED.9b rule. An
      identical replay returns before any decision (r276 logged it as an 'override - KEPT': 103 15m / 156 5m
      lines on one restart; R12). The operator, 2026-10-12 19:14 ET: "We need to fix this problem before it
      starts polluting more days than just today"; 19:16 ET: "Yes".
v4.20 2026-10-12  OTV4TEST r276 (FEED.9b MIRROR OF otv4 r486 556bc2c + FEED.10, FORK-FIRST) — (1) FEED.9b: the upsert's
      WHERE is otv4 v4.14's _UPSERT_CANDLE_SQL byte-for-byte (a stored NULL yields; 1d is last-write-wins; a bar with
      volume yields unless the new version lost more than 5% of it; a 0-volume index keeps r271's range/open rule),
      rows run one by one, and the refusal log carries the kept and refused OHLCV. (2) FEED.10, THE 1m REFEREE: a
      CLOSED 5m/15m/1h bar whose every minute this store holds keeps whichever version is closer to its own 1m
      aggregate - an INFLATED replay is caught as well as a shrunken one (10-12: this box's own replays stored every
      complete QQQ 1h bar at exactly 2.0x its 1m volume; FEED.9b passes any version with more volume). Forming bars,
      incomplete minutes, stored NULLs and any referee error take the FEED.9b rule with no extra read. ⚠️ The 1m set
      is the same vendor's and completeness is by count (an open limitation, BACKLOG FEED.10). The operator,
      2026-10-12 19:14 ET: "We need to fix this problem before it starts polluting more days than just today".
      GATES check_replay_overwrite v1.1 U1-U13 (byte-identical with otv4's but its version line), check_bar_referee R1-R9.
v4.19 2026-10-12  OTV4TEST r271 (FEED.9, SHARED; MIRROR OF otv4 r485 eed0069) — A HISTORY REPLAY CANNOT SHRINK A BAR WE
      ALREADY HOLD. upsert_candles was INSERT OR REPLACE (last write wins); every (re)subscribe replays history, and
      the vendor's 2026-10-08 11:50-11:55 history held only the last ~2 minutes, so the live QQQ 5m 11:55 bar
      (S3 V 107877 L 752.39 = the 1m sum) became V 33808 L 752.57, with the 15m 11:45 and 1h 11:00 bars and SPX's
      08-31/09-04 09:00 1h bars (no 09:30 opening print) damaged the same way (found here, MSG-QQQ-1012-01/02).
      The write now keeps the version with more tape: volume no lower, range no narrower, and the same open or
      strictly more of something; a stored NULL price always yields; refusals log per (symbol, interval) only when
      > 0. The poison guard rejects a non-finite price (NaN passed `<= 0` and landed as NULL). Body byte-identical
      to otv4 dce9431's. ⚠️ A vendor correction that LOWERS a high or a volume is refused too (the accepted cost).
      GATE tests/check_replay_overwrite.py U1-U10.
v4.18 2026-09-29  OTV4TEST r175 (SYM.1) — main() refuses a symbol that is not on the list (config.INSTRUMENT_LISTED), exit 78, beside r146's unset refusal: never stream a symbol the bot will not trade.
v4.17 2026-09-26  OTV4TEST r146 — main() refuses to start with OT_INSTRUMENT unset (exit 78), first,
      before logging: the feed would otherwise subscribe a symbol named UNSET.
v4.16 2026-09-24  OTV4TEST r135 — A FRESH BOX BACKFILLS 45 DAYS OF HOURLY BARS, NOT 16.
      The first fresh box's agent found check_level_tape T7 red (it needs more than
      30 days of hourly tape; 16 were backfilled), so every new box ran a shallow
      level book for about two weeks. The operator preferred fixing it with no
      extra provisioning steps over seeding from the warehouse. MEASURED 2026-09-24
      (/var/tmp/probe_1h_depth.py, its own stream): asked 90 days of QQQ{=1h} RTH,
      TastyTrade returned 435 bars over 63 trading days, the full 90 calendar days.
      45 because it clears T7's 30 with holiday margin and stays inside
      RETENTION_DAYS['1h'] = 60 (warehouse/retention_purge.py), so the nightly
      purge never deletes what the next restart would re-fetch. SIDE EFFECT, and a
      correction: 16 calendar days is ~11 sessions x 7 = ~77 bars, UNDER the bot's
      80-bar 1h frame (config.py TIMEFRAMES["1h"]; its comment's "~112" multiplied
      calendar days by 7) - so a fresh box's 1h trend vote also started short.
      45 days is ~220 bars. A box that already holds the history reads the same
      last 80 bars as before; INSERT OR REPLACE rewrites held bars with the
      vendor's own values.
v4.15 2026-09-24  OTV4TEST r134 — THE JOURNAL WAS 97% SOMEONE ELSE'S DEBUG. The
      tastytrade SDK (13.2.3, tastytrade/__init__.py:13) hard-sets its own logger
      to DEBUG, so every websocket frame reached the journal past this file's
      INFO basicConfig: MEASURED 2,895 of 2,988 candle-feed lines in five minutes,
      ~600/min, found by the first fresh box's agent. `_tt_noise_filter` on the
      root handlers drops the SDK's DEBUG records EXCEPT "Failed to parse event",
      because those are DATA BEING DROPPED, not chatter: 173 in 30 minutes, every
      one a TimeAndSale whose `size` was FRACTIONAL (0.27, 0.0013 shares) and the
      SDK's model demands an integer - fractional-share prints never reach
      `prints`. Kept visible; recorded as FEED.4, not fixed here. Our own
      loggers are untouched; the SDK's INFO and above are untouched.
v4.14 2026-09-18  OTV4TEST r52 — THE WAL HAD NO CEILING. `journal_size_limit`
      defaulted to -1 and SQLite reuses the WAL in place rather than shrinking
      it, so the file sits at its high-water mark forever: MEASURED
      `feed_store.db-wal` at 1,581 MB beside a 1.63 GB database, on a box with
      3.4 GB free. Truncating by hand reclaimed 1.5 GB and the limit REVERTED on
      the next open, because the pragma is per connection. Pinned at 128 MB on
      the connection every writer uses.
v4.13  2026-09-18  OTV4TEST r36 — THE UNDERLYING'S OWN QUOTE IS SUBSCRIBED
      (FEED.2, open since 2026-09-13). r64's manifold took FOUR of the five
      streams for the ticker — Trade, TimeAndSale, Summary, Underlying — and left
      Quote, because Quote WAS subscribed: per CONTRACT, in
      `_reconcile_chain_subs`, where the bot needs it to price a spread. So the
      underlying's own bid/ask was never asked for. MEASURED 2026-09-17: **0 of
      22,846,560 `quote_series` rows are a non-option symbol.**
      🔑 IT IS THE ONLY SOURCE OF RESTING DEPTH. The operator's thesis is that
      size parks at coarse levels and is not worried about minute granularity;
      `prints` says what TRADED and cannot answer it. Measured the same day,
      volume within ±$0.25 of a session extreme carries a lift of **1.02x**
      against a random price in the traded band — i.e. none — and a level that
      HELD is one price turned away from, so volume AT it conflates absorption
      with traversal. `bid_size`/`ask_size` do not.
      ⚠️ COLLECTION ONLY (§31). Nothing reads it; it is banked until there is
      enough to answer the question with numbers rather than an argument.
      ⚠️ NO HANDLER CHANGED: `_on_quote` already keys on `event_symbol` and
      writes `bid_size`/`ask_size`, so it is symbol-agnostic — one line.
      ⚠️ AND IT RIDES THE WRAPPED, INDEPENDENT SUBSCRIBE, NOT THE CHAIN'S CHUNKED
      ONE. r118 is why: adding a stream to the per-CONTRACT subscription cost SPX
      its ENTIRE chain subscription mid-session on 2026-08-25. Each stream here
      fails alone and names itself in the log.
      ⚠️ PURGE: it lands in `quote_series`, already `ARTIFACT_DAYS` at 3 days, so
      the new stream inherits the policy — a subscriber cannot create an unpurged
      table by accident.
v4.12 2026-09-06  r288 / DEV.11 — THE DISK GUARD MOVES OUT, to main.py's tick
      loop. v4.11 put it at the top of `run()`'s `while True`, which is the
      RECONNECT loop rather than a tick loop, so the check ran ONCE PER
      CONNECTION — at startup, then not again until the stream dropped.
      📊 MEASURED, NOT INFERRED: the feed restarted 17:24:14 UTC, a drill was
      armed a minute later, and the flag was still sitting there.
      🔑 `main.py` ticks on POLL_INTERVAL_SECONDS and is the service the deploy
      path restarts, so a bake arms the guard without a separate feed bounce.
v4.11 2026-09-06  r285 / DEV.7 — THE BOX SAYS IT IS FULL. NOBODY ASKS IT.
      Operator: *"it should be a statement, not the answer to a question that
      we're constantly asking."* A control-side poller would ask fifteen boxes
      every few minutes, almost always to hear "no", and would inherit S3.19:
      `ssh_run` gives 22s, returns `rc=255 ssh timeout`, and LEAVES THE REMOTE
      PROCESS RUNNING — and a `find /` on a nearly-full box is exactly the walk
      that outlasts 22s, so the poller would abandon scans that then compete
      for the disk it was worried about.
      🔑 AND THE EC2 API CANNOT ANSWER IT ANYWAY: it knows a volume's SIZE,
      never how full it is. Something must run ON the box, and this process
      already is — it writes the candles, holds the WAL open, and fills the
      disk. The thing consuming the space notices.
      ⚠️ ONE `os.statvfs` PER CYCLE, rate-limited to OT_DISK_CHECK_S. The walk
      for the five largest files runs only on the CROSSING, once per episode.
      ⚠️ TOTALLY GUARDED, because this is the feed's loop on fifteen live boxes:
      a bug here does not cost an alert, it costs the TAPE. `disk_watch.check()`
      is written never to raise and the call site catches anyway.
      ⚠️ PLACED ABOVE THE STAND-DOWN GATE ON PURPOSE — a box parked for
      maintenance still has a disk, and a maintenance window is exactly when
      nobody is watching it.
v4.10 2026-08-25  r118 REVERT of r116's TheoPrice subscription. SPX lost its
      whole per-contract subscription this morning at 13:27 UTC — greeks,
      quotes, marks and theo frozen together while ticker events kept flowing —
      and could not build a chain, so it evaluated nothing through the ORB
      window. QQQ, identical code, narrower chain, was fine. The writer and the
      table stay; only the subscribe is withdrawn.
v4.9  2026-08-24  r116: TheoPrice moves to the PER-CONTRACT subscription beside
      Greeks/Quote. It was asked of the plain ticker, which has no publisher for
      it, so theo_series has been empty since the stream was added on 08-22 —
      proven on QQQ by tools/probe_aux_streams.py (12 events on 12 option
      symbols, 0 on the ticker, Greeks/Quote as controls). _on_theo now keeps
      the FULL streamer symbol: _base_symbol collapsed every contract to "QQQ"
      and theo_series is keyed (symbol, ts_epoch), so ~250 strikes would have
      overwritten each other and the table would have looked populated while
      holding one arbitrary contract. Underlying stays on the ticker — that IS
      its symbol space; retest during RTH before calling it uncarried.
v4.8  2026-08-23  AUDIT F3: the rescue tested for ANY 5m bar at or after
    09:30, not for THE 09:30 bar. A feed that came up late (first bar
    09:45) passed the check, the opening bar stayed missing, and
    get_orb_range carried yesterday's range as EXPIRED - the exact
    failure the rescue was built for. The query is now bounded to the
    09:30 bar's own five-minute slot.
v4.7  2026-08-25  OPENING-RANGE RESCUE. If today's 09:30 5m bar is
    missing between 09:36 and the 11:00 ORB cutoff, UNSUBSCRIBE 5m and
    resubscribe it from the open — once per session, guarded by date.
    On 2026-08-21 the feed ate the open and the range only established
    at 10:01; get_orb_range fails SOFT in that case, carrying
    YESTERDAY'S range as EXPIRED, which is why it took an hour to
    notice. Unsubscribe-first is deliberate: two live subscriptions on
    one tenor would race to write the same rows.
v4.6  2026-08-22  MANIFOLD PART 2 — the five event types this feed
    never asked for are subscribed and housed: TimeAndSale (prints,
    WITH aggressor_side — buy vs sell initiated, real order flow),
    Trade (last_trade), Summary (session_summary, carrying
    prev_day_close_price), Underlying (put_call_ratio, front/back
    volatility term structure) and TheoPrice. Ten of ten event types
    are now captured. Each subscribes INDEPENDENTLY and fails open
    per port; the drain is wrapped so no aux stream can stop the
    candle loop.
v4.5  2026-08-22  THE MANIFOLD. Capture everything, give it a home.
    (a) greeks_series + quote_series — ALL 13 Greeks fields and ALL 12 Quote
        fields incl. bid_size/ask_size, append-only, PK (symbol, ts).
        chain_marks is UNCHANGED and stays the fast current-value read.
        CHARM and VANNA are second-order derivatives of delta OVER A SERIES,
        so a last-write-wins row made both uncomputable.
    (b) extended candles on ALL FIVE tenors, not just 1h. Four fifths of the
        overnight tape was never requested.
    (c) VIX at full tenor parity (was 1m+1d). Capture on all 15 boxes,
        publish to S3 from SPX only.
    Series writes are wrapped: they can never stall the raw tape.
v4.4  2026-08-21  `_is_ext_of` polarity INVERTED and fixed. `tho=true` marks the
    RTH echo, not the extended one. 1m/5m/15m/1d were dropped outright (no
    (sym,tf,True) key exists for them) and the two 1h streams were swapped.
    Live fleet-wide outage of the entire intraday tape on the first v4 session.
v4.3  2026-08-20  THE RTH FEED GATE IS REMOVED. Subscriptions are held whenever
    the box is up; MAINTENANCE (OT_FEED_MODE) is the only stand-down left and it
    is now UNCONDITIONAL — the old block slept only until the next open and
    seconds_until_rth_open() returns 0 during RTH, so a maintenance window
    declared inside the session was silently defeated. The gate existed to stop
    a maintenance wake putting 29 boxes on the wire at once; the fleet is now
    15, the same 15 daily, and a normal session already carried ~20 without
    strain. Operator's call, 2026-08-20. The v4.2 write guard below is what
    makes this safe: every non-RTH bar still routes to <SYM>_EXT, for EVERY
    interval, so the plain series stays RTH-pure while the box streams 24h.
v4.2  2026-08-20  RTH GUARD AT THE WRITE — ported from the SMC thread's v3.17.
    The FEED.2 fix corrected STREAMING routes, and the restart's BACKFILL then
    wrote 24-HOUR bars into the plain series anyway. Measured on the fleet
    2026-08-20 after the v3.16 bake: plain-symbol 1h carried hours 00-23 on
    equities from 08-05 forward — ~12 bars/hour overnight against 38-39 in RTH.
    **SPX was clean (hours 13-20 only), and that control is the proof**: an
    index has no overnight session, so it had nothing to be contaminated with.

    ⚠️ THIS IS WORSE THAN THE HOLE IT REPLACED. A gap announces itself; a series
    that silently CHANGES CHARACTER mid-stream does not. 07-31 was RTH-only and
    08-19 was 24-hour, with nothing marking the seam — and structure_analyzer
    (weight 2.0), the pitchfork's 1h fractals, trend_engine's 0.20 context vote
    and entry_snapshot all read plain 1h expecting RTH.

    ⚠️ SEGREGATED, NEVER DROPPED, and that is the SMC thread's improvement on
    what I first proposed. I suggested deleting the non-RTH rows. **EXT_INTERVAL
    is 1h ONLY, so an overnight 5m or 15m bar has no other home anywhere** — and
    DXFeed history is use-it-or-lose-it. A non-RTH bar arriving on a plain route
    is RE-ROUTED to <SYM>_EXT; `tools/segregate_nonrth_bars.py` does the same for
    rows already written (moves, dry-run by default, backs up first, and reports
    destination collisions rather than silently merging them).

v4.1  2026-08-20  FEED.2 — EVERY 1h CANDLE ROUTED TO THE WRONG SYMBOL FOR SIX
    DAYS, FLEET-WIDE. Ported verbatim from the v3/SMC fix (v3.16); the body
    below the header was BYTE-IDENTICAL across all three repos, so this is one
    defect with one fix in three places.

    `symbol_map` was keyed on (dx_symbol, interval), and FEED.2 subscribes the
    SAME symbol at the SAME interval TWICE — RTH and extended. The second
    registration overwrote the first, so **the RTH 1h route was destroyed at
    construction** and every 1h bar landed under the EXT store symbol. Measured
    2026-08-20: plain QQQ and SPX 1h frozen at 2026-08-14 while *_EXT 1h was
    current.

    ⚠️ NOTHING RAISED. BARS_STALE warned every five minutes with
    `refused=False` and the bots traded on 08-14 bars regardless. **Six days of
    stale higher-timeframe structure** fed structure_analyzer's swings and S/R,
    the pitchfork and its observer, and entry_snapshot.

    ⚠️ AND IT LANDS ON WORK DONE THIS WEEK. r183 raised TIMEFRAMES["1h"] from
    50 to 80 because trend_engine needs EMA_SLOW+5=55, and that diagnosis —
    "the 1h vote never fired" — was correct about the DEPTH and blind to the
    STORE BEING FROZEN. **I tuned an instrument's configuration without
    checking whether its input was arriving**, which is the same failure as
    `oi_proxy`, `max_liq` and `vix_at_entry`: a plausible silence, fixed at the
    wrong layer.

    ⚠️ WHAT IS *NOT* AFFECTED: every study run on 2026-08-20 —
    fork_respect_study, tine_order_study, sweep_discriminator,
    magnitude_estimator, chain_feasibility — builds its own bars from the 1m
    OHLC CSVs and never reads the candle store. **Those numbers stand.**

    FIX: the map key carries the extended-hours flag, and the ingest router
    reads `tho=true` off the echoed symbol — the attribute `_interval_of`
    deliberately discards is exactly the one the router needed.
    GUARD: the feed REFUSES TO START if two subscriptions share a route key, if
    a subscription has no route, or if two subscriptions write the same
    (store_symbol, interval). **The defect was not a typo; it was a route table
    that could silently lose an entry, and that must be impossible rather than
    merely fixed.**

    ⚠️ EXISTING ROWS ARE NOT REPAIRED. Plain-symbol 1h history between 08-14 and
    the deploy is simply absent, and DXFeed history is use-it-or-lose-it.
    Backfill on restart refills what the API still serves.
"""
import argparse
import asyncio
import logging
import os
import json
import math
import sqlite3
import traceback
import threading
import time as _time
from datetime import datetime, time as dtime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from tastytrade import DXLinkStreamer           # module-level so tests can patch
from tastytrade.dxfeed import (Candle, Greeks, Quote, Trade,
                               Summary, TimeAndSale, Underlying,
                               TheoPrice)

from config import INSTRUMENT, TIMEFRAMES
from data.tasty_client import get_session, get_loop

logger = logging.getLogger(__name__)

# ── Poison-candle sanity window (v3.2) ────────────────────────────────────────
# Any candle timestamp outside this window is junk. The observed failure is the
# signed-32-bit rollover (2**31 * 1000 = 2147483648000 ms => 2038-01-19), which
# is far in the future; a 0 / negative ts is equally invalid. Upper bound is
# computed at call time (now + 2 days) so a legitimately-fresh bar is never
# rejected for clock skew, while a 2038 bar always is.
TS_MS_MIN = 1_262_304_000_000        # 2010-01-01 — older than any bar we'd want


def _ts_ms_max() -> int:
    """Newest acceptable candle ts: now + 2 days (tolerates clock skew, kills 2038)."""
    return int((_time.time() + 172_800) * 1000)
ET = ZoneInfo("America/New_York")

# ─── Store location — single definition, imported by every reader ─────────────

def feed_db_path() -> str:
    """Resolve the shared store path. $OT_FEED_DB overrides; default is
    self-locating inside the repo's data/ dir so producer and consumers on the
    same checkout always agree."""
    env = os.environ.get("OT_FEED_DB", "").strip()
    if env:
        return env
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "feed_store.db")


# ─── Tunables ──────────────────────────────────────────────────────────────────

SESSION_OPEN_HM   = (9, 30)          # ET

FLUSH_INTERVAL_S  = 2.0              # buffer -> SQLite cadence (also heartbeat)
PRUNE_FACTOR      = 4                # legacy; unused while PRUNE_KEEP_ROWS is 0
# FEED.3: 0 = NO PRUNING (default). Set OT_PRUNE_KEEP_ROWS to a positive row
# count to re-enable a flat per-(symbol,interval) cap. Kept as a mechanism
# rather than deleted so it is one env var to reverse, not a code change.
PRUNE_KEEP_ROWS   = int(os.environ.get("OT_PRUNE_KEEP_ROWS", "0"))
# TERM.1: an auxiliary-tenor subscription older than this is ignored. Stale
# strikes burn socket budget against a measured ~40-session cap for contracts
# nothing reads.
AUX_MAX_AGE_S     = 6 * 3600
PRUNE_EVERY_S     = 300
RECONNECT_MIN_S   = 3

# v4.3 — FEED_WARM_LEAD_S and the is_rth/seconds_until_rth_open imports are
# GONE with the RTH gate. There is no longer an open to warm up to: the feed
# holds its subscriptions continuously while the box is up, so the frames are
# never cold. `OT_FEED_WARM_LEAD_S` is now INERT — if it is still set in a
# box .env it does nothing, which is stated here so a future reader does not
# spend an evening looking for the code that reads it.

# ── FEED MODE (FEED.1, 2026-08-15) — THE THIRD PURPOSE ───────────────────────
# `_feed_stood_down` (v4.3, formerly `_idle_outside_session`) already says the
# right thing: **"THE DISTINCTION IS
# PURPOSE, NOT TIME."** It only had TWO purposes — service (hold a socket for a
# live session) and one-shot (`--once`, pull history and exit). A `--once` run
# is therefore allowed at ANY hour, which is correct for the EOD pull and wrong
# for the thing v3.9 was actually protecting: **a maintenance wake that brings
# all 29 boxes up for work needing no market data.**
#
# Operator's requirement: a dedicated MAINTENANCE window where the whole fleet
# can be up for fleet updates "without involving the feed or using api
# resources". That cannot be expressed as a clock rule — maintenance and the
# overnight capture pass happen at the same hours and want opposite behaviour.
#
#   service      today's behaviour, unchanged. The default, so nothing moves.
#   capture      a scoped one-shot pull. Same as service for gating; the name
#                exists so a capture wake is DISTINGUISHABLE in the logs from a
#                trader wake, and so a future window argument has somewhere to
#                live.
#   maintenance  HARD OFF. No socket, no subscription, not even `--once`.
#
# ⚠️ AND IT MUST ANNOUNCE ITSELF. On 2026-08-03/04 the gate silently blocked the
# EOD pull: the log read `Feed idle — outside RTH` at INFO four times, then
# `0 bars`, and fourteen 38-byte header-only CSVs were written. Nothing raised,
# and DXFeed history is same-evening only, so BOTH SESSIONS ARE PERMANENTLY
# LOST. A maintenance-suppressed run must never look like a failed fetch: it
# logs at WARNING and says the mode by name.
# ⚠️ A SENTINEL FILE, NOT ONLY AN ENV VAR. `Environment=` in the unit is read
# ONCE AT IMPORT, so flipping the mode on a RUNNING feed would need a restart —
# and the restart window is precisely when the box is on the wire during the
# maintenance it is supposed to be excused from. The file is checked on every
# gate evaluation, so `touch`/`rm` takes effect on the next loop with nothing
# to restart and no race to lose.
MAINT_FLAG = os.environ.get(
    "OT_FEED_MAINT_FLAG",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "data", "FEED_MAINTENANCE"))


def _maintenance_now() -> bool:
    """True if this box is in a maintenance window RIGHT NOW.

    Sentinel file first (live, no restart), env second (set at wake time).
    ⚠️ FAILS OPEN TO service ON AN UNREADABLE PATH: a box that cannot stat the
    flag must keep FEEDING, because the alternative is a silent tape loss that
    DXFeed's same-evening history makes permanent. A stray socket during
    maintenance is recoverable; a missing session is not.
    """
    try:
        if os.path.exists(MAINT_FLAG):
            return True
    except Exception:                                          # noqa: BLE001
        pass
    return FEED_MODE == "maintenance"


FEED_MODE = os.environ.get("OT_FEED_MODE", "service").strip().lower()
_VALID_FEED_MODES = ("service", "capture", "maintenance")
if FEED_MODE not in _VALID_FEED_MODES:
    # An unknown mode must not silently become "maintenance" (a box that never
    # feeds) NOR silently become "service" (a box on the wire during
    # maintenance). Fail to the DEFAULT and say so loudly.
    logging.getLogger(__name__).warning(
        "[feed-mode] OT_FEED_MODE=%r is not one of %s - falling back to "
        "'service'. Fix the unit/env; do not rely on this default.",
        FEED_MODE, ", ".join(_VALID_FEED_MODES))
    FEED_MODE = "service"
RECONNECT_MAX_S   = 60
def _is_ext_route(store_symbol: str) -> bool:
    """v3.17 — is this store symbol the extended-hours stream?"""
    return str(store_symbol or "").endswith("_EXT")


# v3.17 — RTH windows by interval, in ET, as (start, end) inclusive of start
# and exclusive of end. Interval-aware because DXFeed aligns hour bars to the
# HOUR: the 09:00 ET hour bar contains the 09:30 open and is legitimate RTH
# data, while a 09:00 ET *minute* bar is pre-market. Getting this wrong in the
# permissive direction leaves contamination; getting it wrong in the strict
# direction deletes real bars, so the hour case is deliberately generous.
_RTH_BY_INTERVAL = {
    "1m":  ((9, 30), (16, 0)),
    "5m":  ((9, 30), (16, 0)),
    "15m": ((9, 30), (16, 0)),
    "1h":  ((9, 0),  (16, 30)),
}


def _within_rth(ts_ms: int, interval: str) -> bool:
    """Does this bar START inside the regular session, in ET?

    Daily and coarser are always accepted — a 1d bar is stamped at midnight
    and would fail every intraday test, which would silently delete the daily
    series. That mistake is one line away and would be invisible until
    something asked for a daily level.
    """
    win = _RTH_BY_INTERVAL.get(interval)
    if win is None:                      # 1d, 1w, anything coarser
        return True
    try:
        et = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).astimezone(ET)
    except (OverflowError, OSError, ValueError):
        return True                      # unparseable: let the poison guard rule
    if et.weekday() >= 5:                # weekend bars are never RTH
        return False
    (sh, sm), (eh, em) = win
    minutes = et.hour * 60 + et.minute
    # LVL.20 (otv4 r494): the table is written against a 16:00 bell; a half day's ends earlier
    try:
        from utils import market_calendar as _mc
        shift = _mc.close_shift_minutes(et.date())
    except Exception:                    # noqa: BLE001 - a calendar fault keeps the 16:00 window, never drops the write
        shift = 0
    return (sh * 60 + sm) <= minutes < (eh * 60 + em) - shift


# ── v4.20 FEED.10 — the 1m referee's spans, grace and helpers ───────────────────
_REFEREE_SPAN_MIN = {"5m": 5, "15m": 15, "1h": 60}
REFEREE_CLOSE_GRACE_S = 60.0    # r277: a bar is refereed only once its span + this has passed - the final live
                                # update and the bar's last 1m both land well inside it (was 5.0 in r276)


def _referee_minutes(store_symbol: str, ts_ms: int, span: int) -> List[int]:
    """The 1m starts a COMPLETE bar must hold. *_EXT: every minute of the span. A
    plain (RTH) route: only the minutes inside 09:30 to the day's bell (half days
    included), so the 09:00 hour bar needs its 30. [] = not refereeable (no
    trading day / no RTH minute)."""
    mins = [int(ts_ms) + k * 60_000 for k in range(span)]
    if _is_ext_route(store_symbol):
        return mins
    from utils import market_calendar as _mc
    d = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).astimezone(ET).date()
    if not _mc.is_trading_day(d):
        return []
    bell = _mc.close_time(d)
    lo, hi = 9 * 60 + 30, bell.hour * 60 + bell.minute
    out = []
    for m in mins:
        et = datetime.fromtimestamp(m / 1000.0, tz=timezone.utc).astimezone(ET)
        if lo <= et.hour * 60 + et.minute < hi:
            out.append(m)
    return out


def _referee_dist(v: Tuple, agg: Tuple) -> Tuple:
    """Distance of one OHLCV version from the 1m aggregate, compared as a tuple:
    with volume, relative volume error first, then |high|+|low|; a 0-volume index,
    |high|+|low| first, then |open|+|close|. Rounded so float noise is a tie."""
    o, h, l, c = (float(x) for x in v[:4])
    vol = float(v[4] or 0.0)
    ao, ah, al, ac, av = (float(x or 0.0) for x in agg)
    hl = abs(h - ah) + abs(l - al)
    if av > 0:
        return (round(abs(vol - av) / av, 9), round(hl, 9))
    return (round(hl, 9), round(abs(o - ao) + abs(c - ac), 9))


VIX_SYMBOL        = os.environ.get("OT_DXFEED_VIX", "VIX")
VIX_INTERVALS     = ("1m", "1d")

# Backfill depth per interval: calendar days back from now that comfortably
# cover TIMEFRAMES count (RTH ~6.5h/day, ~78 5m bars, ~26 15m bars, ~7 1h bars).
# ── FEED.2 — the overnight (extended-hours) 1h stream ────────────────────────
# Stored under its OWN symbol so nothing that reads plain "1h" changes.
EXT_INTERVAL     = os.environ.get("OT_EXT_INTERVAL", "1h").strip()
EXT_STORE_SYMBOL = f"{INSTRUMENT}_EXT"
EXT_1H_ENABLED   = os.environ.get("OT_EXT_1H", "1").strip() not in ("0", "false", "")

BACKFILL_DAYS = {
    "1m":  1,      # today's session (plus yesterday if pre-open)
    "5m":  4,      # 100 bars ≈ 1.3 sessions -> 4 cal days covers weekends
    "15m": 6,      # 50 bars ≈ 2 sessions
    "1h":  45,     # r135: ~31 sessions ≈ 220 bars; > T7's 30 days, < 60-day retention
    "1d":  30,     # 10 bars ≈ 2 weeks + margin
}


def _dxfeed_symbol() -> str:
    return os.environ.get("OT_DXFEED_SYMBOL", "").strip() or INSTRUMENT


def _explain_exc(e, _depth=0):
    """Flatten an exception (incl. ExceptionGroup / __cause__) to a readable line.
    v3.8 — asyncio TaskGroup wraps the real failure in an ExceptionGroup whose
    str() is just 'unhandled errors in a TaskGroup (1 sub-exception)', which hid
    XOM's actual stream-reject cause for two days."""
    if _depth > 5:
        return repr(e)
    parts = ["%s: %s" % (type(e).__name__, e)]
    subs = getattr(e, "exceptions", None)
    if subs:
        parts.append("[" + " | ".join(_explain_exc(x, _depth + 1) for x in subs) + "]")
    cause = getattr(e, "__cause__", None) or getattr(e, "__context__", None)
    if cause is not None and cause is not e:
        parts.append("<- caused by " + _explain_exc(cause, _depth + 1))
    return " ".join(parts)


def _base_symbol(event_symbol: str) -> str:
    """'QQQ{=5m}' -> 'QQQ'."""
    return (event_symbol or "").split("{")[0]


# OTV5 r16 (PRIME.1) — how deep a symbol the store has NEVER held is primed, per interval, from TastyTrade.
# Inside RETENTION_DAYS (warehouse/retention_purge.py) for every purged interval; TastyTrade caps 1m at its newest
# 8,000 bars (~21 RTH sessions), so the 1m ask returns what it can.
PRIME_DAYS = {
    "1m":  60,
    "5m":  30,
    "15m": 30,
    "1h":  60,
    "1d":  400,
}


def _backfill_start(interval: str, now_et: Optional[datetime] = None,
                    newest_held_ms: Optional[int] = None, held: bool = True) -> datetime:
    """Where a subscription's history starts. held=False: the store has NO bar for this (store symbol, interval) -
    a fresh box or a symbol just switched to - so prime PRIME_DAYS deep. held=True: the old start (BACKFILL_DAYS, or
    today's open for 1m), reaching back to the newest held bar when that is older, never deeper than PRIME_DAYS."""
    now_et = now_et or datetime.now(ET)
    deep = now_et - timedelta(days=PRIME_DAYS.get(interval, BACKFILL_DAYS.get(interval, 4)))
    if not held:
        return deep
    days = BACKFILL_DAYS.get(interval, 4)
    if interval == "1m":
        # Today's session open; if pre-open, previous calendar day's open so the
        # most recent session is available (readers scope to one session).
        d = now_et.date()
        if now_et.time() < dtime(*SESSION_OPEN_HM):
            d = d - timedelta(days=1)
        start = datetime.combine(d, dtime(*SESSION_OPEN_HM), tzinfo=ET)
    else:
        start = now_et - timedelta(days=days)
    if newest_held_ms is not None:
        start = min(start, datetime.fromtimestamp(newest_held_ms / 1000.0, tz=ET))
    return max(deep, start)


# ─── SQLite store (WAL, one writer — this process) ────────────────────────────

class FeedStore:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # check_same_thread=False + an explicit lock (v3.3).
        # The store is constructed on the MAIN thread but every write
        # (_flush -> upsert_candles/heartbeat/commit) is driven from the asyncio
        # event-loop thread created by get_loop(). Python's sqlite3 rejects that
        # by default:
        #   ProgrammingError: SQLite objects created in a thread can only be
        #   used in that same thread.
        # which killed candle-feed on its first flush, every start (GOOGL,
        # 2026-07-13). We remain a SINGLE writer — the lock serializes access so
        # allowing cross-thread use is safe.
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        # 🔴 r52 — THE WAL HAD NO CEILING AND GREW TO 1.58 GB. `journal_size_limit`
        # defaults to -1 (unbounded), and SQLite REUSES the WAL in place rather
        # than shrinking it — so the file sits at its own high-water mark
        # forever. MEASURED 2026-09-18: `feed_store.db-wal` at 1,581 MB beside a
        # 1.63 GB database on a box with 3.4 GB free. The repo had already paid
        # for this once — `warehouse/retention_purge.py`'s own notes record
        # "1.6 GB feed_store.db-wal beside a 2.3 GB database" on the fleet.
        # ⚠️ A CHECKPOINT DOES NOT FIX IT AND THAT IS THE TRAP. Truncating by
        # hand reclaimed 1.5 GB and the limit reverted to -1 on the next open,
        # because the pragma is PER CONNECTION. The only durable fix is here, on
        # the connection every writer uses.
        # ⚠️ IT COSTS NOTHING IN SAFETY: the limit caps the file AFTER a
        # checkpoint, it does not force checkpoints or weaken durability.
        # `synchronous=NORMAL` above is unchanged.
        self.conn.execute("PRAGMA journal_size_limit=134217728;")   # 128 MB
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                symbol      TEXT NOT NULL,
                interval    TEXT NOT NULL,
                ts_epoch_ms INTEGER NOT NULL,
                open REAL, high REAL, low REAL, close REAL, volume REAL,
                PRIMARY KEY (symbol, interval, ts_epoch_ms)
            );""")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS feed_meta (
                symbol   TEXT NOT NULL,
                interval TEXT NOT NULL,
                last_write_epoch REAL NOT NULL,
                PRIMARY KEY (symbol, interval)
            );""")
        # ── v3.4: chain-marks transport (Option 1b) ──────────────────────────
        # chain_subs: single row WRITTEN BY THE BOT (options_chain v3.2) naming
        # the streamer symbols + expiry it wants live marks for. chain_marks:
        # latest-value Greeks/Quote per option symbol, WRITTEN BY THE FEED.
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chain_subs (
                id            INTEGER PRIMARY KEY CHECK (id = 1),
                expiry        TEXT NOT NULL,
                symbols       TEXT NOT NULL,          -- JSON list
                updated_epoch REAL NOT NULL
            );""")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chain_marks (
                streamer_symbol TEXT PRIMARY KEY,
                bid REAL, ask REAL,
                delta REAL, gamma REAL, theta REAL, vega REAL, iv REAL,
                updated_epoch REAL NOT NULL
            );""")

        # ── 🔴 THE MANIFOLD (2026-08-22) — FULL-FIDELITY SERIES HOMES ────────
        # Operator's governing rule: **STOP DISCARDING INFORMATION.** See
        # docs/FEED_MANIFOLD.md. `chain_marks` above is PRIMARY KEY
        # (streamer_symbol) — last-write-wins — so ~250 chain symbols ticking
        # all session each overwrote ONE row. The entire intraday evolution of
        # the greek surface was captured and then destroyed.
        #
        # ⚠️ chain_marks IS UNCHANGED AND STAYS. It is the tick loop's fast
        # current-value read; every existing consumer keeps working untouched.
        # These tables are ADDITIVE. That is FEED.2's lesson applied on purpose
        # instead of after the fact.
        #
        # ⚠️ EVERY FIELD THE EVENT CARRIES IS STORED. Greeks has 13 and we kept
        # 7; Quote has 12 and we kept 2 — losing bid_size/ask_size, which is
        # depth at the touch and the signal FRC.1 needed and never had.
        #
        # 🔴 CHARM AND VANNA LIVE HERE. Both are second-order derivatives of
        # delta OVER A SERIES — charm = dDelta/dt, vanna = dDelta/dVol — so
        # NEITHER was computable from a single overwritten row. For 0DTE charm
        # is the mechanism behind pin; a 0DTE book that cannot compute it is
        # asserting pin risk rather than measuring it. Storing `delta`,
        # `volatility` and `time` per strike per tick makes both a finite
        # difference over this table.
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS greeks_series (
                streamer_symbol TEXT NOT NULL,
                ts_epoch        REAL NOT NULL,
                event_time      REAL, event_flags INTEGER, idx REAL,
                ev_time         REAL, sequence INTEGER,
                price REAL, volatility REAL,
                delta REAL, gamma REAL, theta REAL, rho REAL, vega REAL,
                PRIMARY KEY (streamer_symbol, ts_epoch)
            );""")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_greeks_series_ts "
            "ON greeks_series(ts_epoch)")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS quote_series (
                streamer_symbol TEXT NOT NULL,
                ts_epoch        REAL NOT NULL,
                event_time      REAL, sequence INTEGER, time_nano_part INTEGER,
                bid_time REAL, bid_exchange_code TEXT,
                ask_time REAL, ask_exchange_code TEXT,
                bid_price REAL, ask_price REAL,
                bid_size REAL, ask_size REAL,
                PRIMARY KEY (streamer_symbol, ts_epoch)
            );""")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_quote_series_ts "
            "ON quote_series(ts_epoch)")

        # ── 🔴 MANIFOLD PART 2 (2026-08-22) — THE FIVE UNSUBSCRIBED EVENTS ───
        # The SDK offers TEN event types. Until now this feed subscribed THREE.
        # These five were never asked for, so no consumer could ever starve on
        # them loudly — they simply did not exist. Operator's rule: capture
        # everything the wire offers, give it a home, let consumers subscribe.
        #
        # ⚠️ TWO OF THESE CARRY THINGS THIS REPO HAS BEEN MISSING BY NAME:
        #   · TimeAndSale.aggressor_side — BUY vs SELL initiated, per print.
        #     Real order flow. Nothing here has ever seen who lifted the offer
        #     versus hit the bid, and FRC.1's friction work was blind to it.
        #   · Underlying.put_call_ratio / front_volatility / back_volatility —
        #     term structure and flow skew from the VENDOR, no derivation.
        #   · Summary.prev_day_close_price — `runaway_continuation` takes
        #     prev_close as a BARE SCALAR whose 1d dependency is invisible at
        #     the call site, and 1d was absent from the warehouse on
        #     2026-08-21. This is a second, independent source for it.
        #
        # ⚠️ ALL APPEND-ONLY, PK (symbol, ts). Nothing overwrites.
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS prints (
                symbol TEXT NOT NULL, ts_epoch REAL NOT NULL,
                event_time REAL, idx REAL, ev_time REAL, sequence INTEGER,
                exchange_code TEXT, price REAL, size REAL,
                bid_price REAL, ask_price REAL,
                aggressor_side TEXT, spread_leg INTEGER,
                extended_trading_hours INTEGER, valid_tick INTEGER,
                type TEXT, buyer TEXT, seller TEXT,
                exchange_sale_conditions TEXT,
                PRIMARY KEY (symbol, ts_epoch, sequence)
            );""")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_prints_ts ON prints(ts_epoch)")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS last_trade (
                symbol TEXT NOT NULL, ts_epoch REAL NOT NULL,
                event_time REAL, ev_time REAL, sequence INTEGER,
                exchange_code TEXT, day_id INTEGER, tick_direction TEXT,
                extended_trading_hours INTEGER,
                price REAL, change REAL, size REAL,
                day_volume REAL, day_turnover REAL,
                PRIMARY KEY (symbol, ts_epoch)
            );""")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS session_summary (
                symbol TEXT NOT NULL, ts_epoch REAL NOT NULL,
                event_time REAL, day_id INTEGER, prev_day_id INTEGER,
                open_interest REAL,
                day_open_price REAL, day_high_price REAL,
                day_low_price REAL, day_close_price REAL,
                prev_day_close_price REAL, prev_day_volume REAL,
                PRIMARY KEY (symbol, ts_epoch)
            );""")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS underlying_series (
                symbol TEXT NOT NULL, ts_epoch REAL NOT NULL,
                event_time REAL, idx REAL, ev_time REAL, sequence INTEGER,
                volatility REAL, front_volatility REAL, back_volatility REAL,
                call_volume REAL, put_volume REAL, option_volume REAL,
                put_call_ratio REAL,
                PRIMARY KEY (symbol, ts_epoch)
            );""")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS theo_series (
                symbol TEXT NOT NULL, ts_epoch REAL NOT NULL,
                event_time REAL, idx REAL, ev_time REAL, sequence INTEGER,
                price REAL, underlying_price REAL,
                delta REAL, gamma REAL, dividend REAL, interest REAL,
                PRIMARY KEY (symbol, ts_epoch)
            );""")
        self.conn.commit()

    def newest_held_ms(self, symbol: str, interval: str) -> Optional[int]:
        """OTV5 r16 — the newest stored bar's ts for (symbol, interval), or None when the store holds none."""
        with self._lock:
            row = self.conn.execute("SELECT MAX(ts_epoch_ms) FROM candles WHERE symbol=? AND interval=?",
                                    (symbol, interval)).fetchone()
        return int(row[0]) if row and row[0] is not None else None

    def upsert_candles(self, rows: List[Tuple]):
        """rows: (symbol, interval, ts_ms, o, h, l, c, v). Last write wins."""
        if not rows:
            return
        with self._lock:
            self._upsert_candles_locked(rows)

    # v4.14 FEED.9b — when a stored bar yields. Three cases, in this order:
    #   · a stored NULL price always yields;
    #   · 1d is last-write-wins, as before v4.13: the vendor's daily is its
    #     official bar and a replay CORRECTS it (CVX 2026-10-12 stored an
    #     off-tape low of 211.02 against a 1m low of 213.75; v4.13 refused the
    #     vendor's correction twice, and that bar becomes tomorrow's prior-day
    #     low);
    #   · a bar WITH volume yields unless the new version lost more than 5% of
    #     it. The 10-08 slices lost 14-90%; a correction that removes a bad
    #     print loses almost none and is now taken, narrower range or not;
    #   · a 0-volume bar (index: SPX, VIX; SQLite stores NaN as NULL, hence
    #     the coalesce) keeps v4.13's rule: range no narrower, and the same
    #     open or a wider range.
    _UPSERT_CANDLE_SQL = (
        "INSERT INTO candles "
        "(symbol, interval, ts_epoch_ms, open, high, low, close, volume) "
        "VALUES (?,?,?,?,?,?,?,?) "
        "ON CONFLICT(symbol, interval, ts_epoch_ms) DO UPDATE SET "
        "open=excluded.open, high=excluded.high, low=excluded.low, "
        "close=excluded.close, volume=excluded.volume "
        "WHERE candles.open IS NULL OR candles.high IS NULL "
        "OR candles.low IS NULL OR candles.close IS NULL "
        "OR excluded.interval = '1d' "
        "OR (coalesce(candles.volume,0) > 0 AND "
        "coalesce(excluded.volume,0) >= 0.95 * candles.volume) "
        "OR (coalesce(candles.volume,0) = 0 "
        "AND excluded.high >= candles.high AND excluded.low <= candles.low "
        "AND (excluded.open = candles.open "
        "OR excluded.high > candles.high OR excluded.low < candles.low))")

    # v4.20 FEED.10 (fork-first) — THE 1m REFEREE. FEED.9/9b decide from the two
    # versions alone, so they can catch a SHRUNKEN replay (10-08: the vendor's
    # slice) but never an INFLATED one: on 2026-10-12 this box's own 16:11/16:17
    # replays stored every complete QQQ 1h bar at EXACTLY 2.0x the volume of its
    # 60 minutes (mainline's live-pushed 15:00 bar: 1,629,246 = the 1m sum; ours:
    # 3,258,492), and a version with MORE volume always passes the 9b rule. For a
    # CLOSED 5m/15m/1h bar whose every minute this store holds, the referee keeps
    # whichever version (stored or replayed) is closer to the 1m aggregate
    # (first open, max high, min low, last close, volume sum): volume first, then
    # high/low; a 0-volume index compares high/low, then open/close. A tie keeps
    # the stored row. Anything else - a forming bar, a minute missing, a stored
    # NULL, any error - takes the FEED.9b rule unchanged, with NO extra read on
    # a forming bar (every live update of the forming bar conflicts with its own
    # stored row). ⚠️ THE REFEREE'S SOURCE IS THE SAME VENDOR: the 1m rows are
    # themselves guarded only by FEED.9/9b and are never refereed, and
    # completeness is by minute COUNT - a 1m slice (thin minutes) would pass as
    # complete and mislead it. Named as an open limitation (BACKLOG FEED.10).
    def _upsert_candles_locked(self, rows: List[Tuple]):
        # Refusals are reported per (symbol, interval) with the stored and the
        # refused values: *_EXT has two sources (the RTH guard's re-key and the
        # EXT subscription), and a refusal has to be judgeable after the fact.
        refused: Dict[Tuple[str, str], List[Tuple]] = {}
        overrode: Dict[Tuple[str, str], List[Tuple]] = {}
        now_ms = _time.time() * 1000.0
        for r in rows:
            span = _REFEREE_SPAN_MIN.get(r[1])
            if span is not None and r[2] + span * 60_000 + REFEREE_CLOSE_GRACE_S * 1000.0 <= now_ms:
                done = self._referee_one_locked(r, span, refused, overrode)
                if done:
                    continue
            if self.conn.execute(self._UPSERT_CANDLE_SQL, r).rowcount == 0:
                refused.setdefault((r[0], r[1]), []).append(r)
        for (sym, iv), rr in refused.items():
            first = rr[0]
            kept = self.conn.execute(
                "SELECT open, high, low, close, volume FROM candles WHERE "
                "symbol=? AND interval=? AND ts_epoch_ms=?",
                (sym, iv, first[2])).fetchone()
            logger.info("FEED.9: kept %d stored %s %s bar(s) a smaller "
                        "version would have overwritten; first ts=%d kept "
                        "OHLCV=%s refused OHLCV=%s", len(rr), sym, iv,
                        first[2], kept, tuple(first[3:8]))
        for (sym, iv), oo in overrode.items():
            r, stored, agg, take = oo[0]
            logger.info("FEED.10: the 1m referee overrode the FEED.9b rule on %d %s %s bar(s); "
                        "first ts=%d %s stored OHLCV=%s replay OHLCV=%s 1m aggregate OHLCV=%s",
                        len(oo), sym, iv, r[2], "TOOK the replay" if take else "KEPT the stored bar",
                        stored, tuple(r[3:8]), agg)
        now = _time.time()
        touched = {(r[0], r[1]) for r in rows}
        self.conn.executemany(
            "INSERT OR REPLACE INTO feed_meta (symbol, interval, last_write_epoch) "
            "VALUES (?,?,?)", [(s, i, now) for (s, i) in touched])

    def _referee_one_locked(self, r: Tuple, span: int, refused, overrode) -> bool:
        """FEED.10 for ONE closed 5m/15m/1h row. True when it handled the row; False
        sends the row to the FEED.9b rule unchanged. Never raises."""
        try:
            if self.conn.execute(
                    "INSERT OR IGNORE INTO candles "
                    "(symbol, interval, ts_epoch_ms, open, high, low, close, volume) "
                    "VALUES (?,?,?,?,?,?,?,?)", r).rowcount == 1:
                return True                          # a new bar: nothing to referee
            stored = self.conn.execute(
                "SELECT open, high, low, close, volume FROM candles WHERE "
                "symbol=? AND interval=? AND ts_epoch_ms=?", (r[0], r[1], r[2])).fetchone()
            if stored is None or any(x is None for x in stored[:4]):
                return False                         # a stored NULL yields: FEED.9b's case
            if tuple(r[3:8]) == tuple(stored):
                return True                          # r277: an identical replay - nothing to decide or log
            want = _referee_minutes(r[0], r[2], span)
            if not want:
                return False
            mins = self.conn.execute(
                "SELECT ts_epoch_ms, open, high, low, close, volume FROM candles WHERE "
                "symbol=? AND interval='1m' AND ts_epoch_ms>=? AND ts_epoch_ms<? "
                "ORDER BY ts_epoch_ms", (r[0], want[0], want[-1] + 60_000)).fetchall()
            got = [m for m in mins if m[0] in set(want)]
            if len(got) != len(want) or any(x is None for m in got for x in m[1:5]):
                return False                         # incomplete: the 9b rule decides
            agg = (got[0][1], max(m[2] for m in got), min(m[3] for m in got), got[-1][4],
                   sum((m[5] or 0.0) for m in got))
            take = _referee_dist(tuple(r[3:8]), agg) < _referee_dist(stored, agg)
            self.conn.execute("SAVEPOINT feed10")
            took = self.conn.execute(self._UPSERT_CANDLE_SQL, r).rowcount > 0
            if took and not take:
                self.conn.execute("ROLLBACK TO feed10")
            elif take and not took:
                self.conn.execute(
                    "UPDATE candles SET open=?, high=?, low=?, close=?, volume=? WHERE "
                    "symbol=? AND interval=? AND ts_epoch_ms=?", tuple(r[3:8]) + tuple(r[0:3]))
            self.conn.execute("RELEASE feed10")
            if took != take:
                overrode.setdefault((r[0], r[1]), []).append((r, tuple(stored), agg, take))
            elif not take:
                refused.setdefault((r[0], r[1]), []).append(r)
            return True
        except Exception as exc:                     # noqa: BLE001 — fall back, never raise
            try:                                     # undo anything half-done, then close the savepoint
                self.conn.execute("ROLLBACK TO feed10")
                self.conn.execute("RELEASE feed10")
            except Exception:                        # noqa: BLE001 — no savepoint was open
                pass
            if not getattr(self, "_referee_err_logged", False):
                self._referee_err_logged = True
                logger.warning("FEED.10: the 1m referee failed (%s) - falling back to the "
                               "FEED.9b rule; said once", exc)
            return False

    def purge_poison(self) -> int:
        """Delete any poison rows already in the store (v3.2). Runs at feed
        startup so a box whose DB was poisoned before this guard existed
        self-heals on restart — no manual sqlite surgery across the fleet."""
        with self._lock:
            cur = self.conn.execute(
                "DELETE FROM candles WHERE open <= 0 OR high <= 0 OR low <= 0 "
                "OR close <= 0 OR ts_epoch_ms < ? OR ts_epoch_ms > ?",
                (TS_MS_MIN, _ts_ms_max()))
            self.conn.commit()
            n = cur.rowcount or 0
        if n:
            logger.warning("purged %d poison candle row(s) from the store", n)
        return n

    def heartbeat(self):
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO feed_meta (symbol, interval, last_write_epoch) "
                "VALUES ('__feed__','heartbeat',?)", (_time.time(),))

    def commit(self):
        with self._lock:
            self.conn.commit()

    # ── v3.4: chain-marks transport ───────────────────────────────────────────
    def read_chain_subs(self):
        """(expiry, [streamer_symbols]) requested by the bot, or ("", []).

        ⚠️ TERM.1 (2026-08-18): the returned symbol list is the FRONT expiry
        UNIONED with any auxiliary tenors. `chain_subs` is `CHECK (id = 1)` — a
        single row by design — so extra expiries ride in a SEPARATE table and
        the front-expiry contract is untouched. The returned `expiry` string
        still names the FRONT expiry only: every existing caller reads it that
        way and none of them changes.

        ⚠️ FAILS OPEN, DELIBERATELY. A missing, empty or malformed aux table
        returns the front expiry exactly as before. **This function decides what
        a live trading box subscribes to** — the auxiliary tenors are archival
        enrichment and must never be able to cost the bot its own chain.
        """
        with self._lock:
            row = self.conn.execute(
                "SELECT expiry, symbols FROM chain_subs WHERE id=1").fetchone()
        if not row:
            return "", []
        try:
            expiry = row[0] or ""
            syms = json.loads(row[1] or "[]")
        except (ValueError, TypeError):
            return "", []
        try:
            aux = self._read_chain_subs_aux()
            if aux:
                seen = set(syms)
                for s in aux:
                    if s not in seen:
                        seen.add(s)
                        syms.append(s)
        except Exception:                                      # noqa: BLE001
            pass          # archival enrichment never costs the bot its chain
        return expiry, syms

    def _read_chain_subs_aux(self):
        """Extra-tenor streamer symbols, or [] if the table is absent/stale.

        ⚠️ STALENESS BOUND. An aux row older than the front expiry's own update
        is a leftover from a previous session — subscribing to last week's
        strikes wastes socket budget against a measured ~40-session cap and
        pollutes `chain_marks` with contracts nothing reads.
        """
        cur = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='chain_subs_aux'")
        if not cur.fetchone():
            return []
        cutoff = _time.time() - AUX_MAX_AGE_S
        rows = self.conn.execute(
            "SELECT symbols FROM chain_subs_aux WHERE updated_epoch >= ?",
            (cutoff,)).fetchall()
        out = []
        for r in rows:
            try:
                out.extend(json.loads(r[0] or "[]"))
            except (ValueError, TypeError):
                continue
        return out

    def upsert_chain_quotes(self, rows):
        """rows: (streamer_symbol, bid, ask, epoch) — preserves greeks columns."""
        if not rows:
            return
        with self._lock:
            self.conn.executemany(
                "INSERT INTO chain_marks (streamer_symbol, bid, ask, updated_epoch) "
                "VALUES (?,?,?,?) ON CONFLICT(streamer_symbol) DO UPDATE SET "
                "bid=excluded.bid, ask=excluded.ask, "
                "updated_epoch=excluded.updated_epoch", rows)

    def upsert_chain_greeks(self, rows):
        """rows: (streamer_symbol, delta, gamma, theta, vega, iv, epoch) —
        preserves quote columns."""
        if not rows:
            return
        with self._lock:
            self.conn.executemany(
                "INSERT INTO chain_marks (streamer_symbol, delta, gamma, theta, "
                "vega, iv, updated_epoch) VALUES (?,?,?,?,?,?,?) "
                "ON CONFLICT(streamer_symbol) DO UPDATE SET "
                "delta=excluded.delta, gamma=excluded.gamma, theta=excluded.theta, "
                "vega=excluded.vega, iv=excluded.iv, "
                "updated_epoch=excluded.updated_epoch", rows)

    # ── MANIFOLD WRITERS (2026-08-22) — append-only, every field ────────────
    # ⚠️ INSERT OR IGNORE, not UPSERT. The PK is (symbol, ts) so a duplicate
    # tick is a no-op rather than a silent overwrite — the whole point of these
    # tables is that nothing is ever destroyed.
    def append_greeks_series(self, rows):
        """rows: 13-tuples, full Greeks fidelity. See docs/FEED_MANIFOLD.md."""
        if not rows:
            return
        with self._lock:
            self.conn.executemany(
                "INSERT OR IGNORE INTO greeks_series (streamer_symbol, ts_epoch,"
                " event_time, event_flags, idx, ev_time, sequence, price,"
                " volatility, delta, gamma, theta, rho, vega)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    def append_quote_series(self, rows):
        """rows: 13-tuples, full Quote fidelity INCLUDING bid_size/ask_size."""
        if not rows:
            return
        with self._lock:
            self.conn.executemany(
                "INSERT OR IGNORE INTO quote_series (streamer_symbol, ts_epoch,"
                " event_time, sequence, time_nano_part, bid_time,"
                " bid_exchange_code, ask_time, ask_exchange_code, bid_price,"
                " ask_price, bid_size, ask_size)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    # ── MANIFOLD PART 2 WRITERS — append-only, every field ──────────────
    def append_prints(self, rows):
        return self._append_many(
            "INSERT OR IGNORE INTO prints (symbol, ts_epoch, event_time, idx,"
            " ev_time, sequence, exchange_code, price, size, bid_price,"
            " ask_price, aggressor_side, spread_leg, extended_trading_hours,"
            " valid_tick, type, buyer, seller, exchange_sale_conditions)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    def append_last_trade(self, rows):
        return self._append_many(
            "INSERT OR IGNORE INTO last_trade (symbol, ts_epoch, event_time,"
            " ev_time, sequence, exchange_code, day_id, tick_direction,"
            " extended_trading_hours, price, change, size, day_volume,"
            " day_turnover) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    def append_session_summary(self, rows):
        return self._append_many(
            "INSERT OR IGNORE INTO session_summary (symbol, ts_epoch,"
            " event_time, day_id, prev_day_id, open_interest, day_open_price,"
            " day_high_price, day_low_price, day_close_price,"
            " prev_day_close_price, prev_day_volume)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    def append_underlying(self, rows):
        return self._append_many(
            "INSERT OR IGNORE INTO underlying_series (symbol, ts_epoch,"
            " event_time, idx, ev_time, sequence, volatility,"
            " front_volatility, back_volatility, call_volume, put_volume,"
            " option_volume, put_call_ratio)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    def append_theo(self, rows):
        return self._append_many(
            "INSERT OR IGNORE INTO theo_series (symbol, ts_epoch, event_time,"
            " idx, ev_time, sequence, price, underlying_price, delta, gamma,"
            " dividend, interest) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    def _append_many(self, sql, rows) -> int:
        """Shared append. Never raises — a lost observation must not stall
        the tape (same rule as the series writes)."""
        if not rows:
            return 0
        try:
            with self._lock:
                self.conn.executemany(sql, rows)
            return len(rows)
        except Exception as exc:                                # noqa: BLE001
            logger.warning("append failed (%d rows): %s — raw candles "
                           "unaffected", len(rows), exc)
            return 0

    def clear_chain_marks(self):
        with self._lock:
            self.conn.execute("DELETE FROM chain_marks")
            self.conn.commit()

    def prune(self, symbol: str, interval: str, keep: int):
        with self._lock:
            self._prune_locked(symbol, interval, keep)

    def _prune_locked(self, symbol: str, interval: str, keep: int):
        self.conn.execute("""
            DELETE FROM candles WHERE symbol=? AND interval=? AND ts_epoch_ms NOT IN
            (SELECT ts_epoch_ms FROM candles WHERE symbol=? AND interval=?
             ORDER BY ts_epoch_ms DESC LIMIT ?)""",
            (symbol, interval, symbol, interval, keep))

    def bar_count(self, symbol: str, interval: str) -> int:
        with self._lock:
            cur = self.conn.execute(
                "SELECT COUNT(*) FROM candles WHERE symbol=? AND interval=?",
                (symbol, interval))
            return int(cur.fetchone()[0])

    def close(self):
        try:
            self.conn.commit()
            self.conn.close()
        except Exception:
            pass


# ─── The producer ──────────────────────────────────────────────────────────────

class CandleFeed:
    """Persistent single subscription -> in-memory last-write-wins buffer ->
    periodic flush to the shared store."""

    def __init__(self, store: FeedStore):
        self.store = store
        self.dx_symbol = _dxfeed_symbol()
        # (dxfeed_symbol, interval) -> store symbol name
        self.symbol_map: Dict[Tuple[str, str], str] = {}
        # (dx_sym, interval, start, extended_trading_hours)
        self.subs: List[Tuple[str, str, datetime, bool]] = []
        for tf in TIMEFRAMES.keys():
            self.subs.append((self.dx_symbol, tf, _backfill_start(tf), False))
            # v3.16 — the key now carries the EXTENDED-HOURS FLAG, because
            # (dx_symbol, interval) is NOT unique: FEED.2 subscribes the same
            # symbol+interval twice and the second registration used to
            # overwrite the first. Three-tuple, one entry per subscription.
            self.symbol_map[(self.dx_symbol, tf, False)] = INSTRUMENT
        # ── 🔴 MANIFOLD (2026-08-22) — VIX AT FULL TENOR PARITY ──────────────
        # Was `VIX_INTERVALS = ("1m","1d")` — 2 of 5. VIX feeds macro,
        # vol_state and SessionGuard's crisis lockout, and none of them could
        # ever see a 5m/15m/1h VIX because it was never requested.
        # ⚠️ CAPTURE ON ALL 15 BOXES, PUBLISH FROM SPX ONLY. VIX is the one
        # fleet-wide duplicate (traced: each box subscribes its own instrument
        # plus VIX, nothing else). It is needed locally everywhere and is
        # identical everywhere, so the S3 push is SPX's job — operator's call,
        # 2026-08-22. See docs/FEED_MANIFOLD.md.
        for tf in TIMEFRAMES.keys():
            self.subs.append((VIX_SYMBOL, tf, _backfill_start(tf), False))
            self.symbol_map[(VIX_SYMBOL, tf, False)] = "VIX"

        # ── FEED.2 (2026-08-15) — THE OVERNIGHT STREAM ───────────────────────
        # ⚠️ THE TAPE WAS NEVER UNAVAILABLE. WE WERE ASKING DXFEED TO EXCLUDE IT.
        # `subscribe_candle(..., extended_trading_hours=False)` is the SDK
        # DEFAULT, and when it is False the SDK appends **`tho=true`**
        # (trading-hours-only) to the symbol: `QQQ{=1h,tho=true}`. Every
        # subscription this feed has ever made carried it.
        #
        # That single default is what produced `ext=0` on 28 of 29 boxes, an
        # RTH-only 1h store (252 bars = 36 sessions x 7), and LIQ.6's Asia and
        # London sections having nothing to build from. It is NOT the session
        # guard, NOT the warm lead, NOT S3, NOT an entitlement tier.
        #
        # ⚠️ A SEPARATE STREAM, NOT A FLAG ON THE EXISTING 1h. `1h` is read by
        # structure_analyzer's swings and S/R, by the pitchfork and its observer,
        # and by entry_snapshot. Flipping it in place would silently rebuild all
        # of them on 24h bars — the pitchfork is a v4.0 milestone and its forks
        # would change shape overnight with nothing announcing it. This lands
        # under its OWN store symbol so **no existing consumer moves at all**;
        # only the named-level frame reads it.
        # ── 🔴 MANIFOLD (2026-08-22) — EXTENDED ON EVERY TENOR, NOT JUST 1h ──
        # The block above is the FEED.2 finding and it is still correct; what
        # was wrong is that it was applied to ONE tenor. 1h got an extended
        # twin because LIQ.6 starved and noticed. 1m/5m/15m/1d never had one —
        # so four fifths of the overnight tape had no home and was simply not
        # requested.
        # ⚠️ THIS IS THE CAPTURE-ON-DEMAND PATTERN ITSELF. Operator, 2026-08-22:
        # every fix in this repo "had to do with unlocking one feed store
        # artifact at a time until something started working, where we should
        # have started with subscribe to everything, find a place for it, and
        # then if we need it, it's there." A consumer cannot starve on data
        # that was never conditional.
        # ⚠️ STILL SEPARATE STORE SYMBOLS — the reasoning above holds for all
        # five: extended bars land under SYM_EXT/interval, so NO existing
        # consumer moves. The RTH series stay byte-identical.
        # ⚠️ FAILS OPEN PER TENOR. If an entitlement does not cover extended on
        # some tenor, that ONE subscription logs SUBSCRIBE FAILED and the rest
        # continue — the loop that opens these already guarantees it.
        if EXT_1H_ENABLED:
            for tf in TIMEFRAMES.keys():
                self.subs.append((self.dx_symbol, tf,
                                  _backfill_start(tf), True))
                self.symbol_map[(self.dx_symbol, tf, True)] = EXT_STORE_SYMBOL
        # ── v3.16 — COLLISION GUARD. REFUSE TO START ON A DUPLICATE ROUTE ───
        # The FEED.2 defect was not that someone wrote a wrong key; it was that
        # TWO subscriptions could legally resolve to the SAME store target and
        # nothing said so. Six days of stale 1h structure followed, fleet-wide,
        # with no error. A route table that can silently lose an entry must not
        # be allowed to start.
        # Two invariants, both cheap and both checked before a socket opens:
        #   1. no two SUBSCRIPTIONS share a map key (one would overwrite the
        #      other, which is exactly what happened)
        #   2. no two map keys point at the SAME (store_symbol, interval) —
        #      two live streams writing one table is a silent merge
        _seen_keys, _seen_targets = set(), {}
        for (_ds, _tf, _st, _ex) in self.subs:
            _k = (_ds, _tf, bool(_ex))
            if _k in _seen_keys:
                raise RuntimeError(
                    f"candle_feed: DUPLICATE SUBSCRIPTION KEY {_k} — two "
                    f"subscriptions resolve to one route and one would "
                    f"silently overwrite the other (the FEED.2 defect, "
                    f"2026-08-14..20). Refusing to start.")
            _seen_keys.add(_k)
            _tgt = (self.symbol_map.get(_k), _tf)
            if _tgt[0] is None:
                raise RuntimeError(
                    f"candle_feed: SUBSCRIPTION {_k} HAS NO ROUTE in "
                    f"symbol_map — its candles would be dropped. Refusing "
                    f"to start.")
            if _tgt in _seen_targets:
                raise RuntimeError(
                    f"candle_feed: TWO SUBSCRIPTIONS WRITE {_tgt} — "
                    f"{_seen_targets[_tgt]} and {_k}. One stream would "
                    f"silently merge into the other's table. Refusing to "
                    f"start.")
            _seen_targets[_tgt] = _k
        logger.info("candle_feed routes verified: %d subscription(s), "
                    "%d distinct store target(s)",
                    len(_seen_keys), len(_seen_targets))

        # buffer[(store_symbol, interval)][ts_ms] = row tuple
        self.buffer: Dict[Tuple[str, str], Dict[int, Tuple]] = {}
        self._unmapped_seen: set = set()   # v3.7: warn-once on unmapped candles
        # v3.17 — non-RTH bars SEGREGATED per (symbol, interval). Warn ONCE
        # then count: a per-bar warning during a 15-day backfill buries the log.
        self._rth_moved: Dict[Tuple[str, str], int] = {}
        self.backfill_logged: Dict[Tuple[str, str], bool] = {}
        # ── v3.4 chain-marks state (reset on every socket (re)connect) ────────
        self._chain_expiry: str = ""
        self._chain_subscribed: set = set()
        self._quotes_buf: Dict[str, tuple] = {}    # sym -> (sym,bid,ask,epoch)
        self._greeks_buf: Dict[str, tuple] = {}    # sym -> (sym,d,g,t,v,iv,epoch)
        # MANIFOLD (2026-08-22) — LISTS, not dicts. The two buffers above are
        # keyed by symbol precisely so the newest tick REPLACES the previous
        # one; that is correct for a current-value cache and fatal for history.
        # These append, so every tick survives to the flush.
        self._greeks_series_buf: List[tuple] = []
        self._quote_series_buf: List[tuple] = []
        # MANIFOLD PART 2 — one append-buffer per new event type.
        # r72 — the opening-range rescue fires AT MOST ONCE per session.
        # ⚠️ A RETRY LOOP HERE WOULD BE WORSE THAN THE BUG. Fifteen boxes
        # re-subscribing 5m every tick during an outage is a self-inflicted
        # stampede on the same socket that is already struggling.
        self._orb_rescue_done_for: str = ""
        self._prints_buf: List[tuple] = []
        self._trade_buf: List[tuple] = []
        self._summary_buf: List[tuple] = []
        self._underlying_buf: List[tuple] = []
        self._theo_buf: List[tuple] = []


    def _start_for(self, dx_sym: str, tf: str, ext: bool, fallback: datetime) -> datetime:
        """OTV5 r16 (PRIME.1) — this subscription's history start, read from the store NOW: a (store symbol, interval)
        the store has never held is primed PRIME_DAYS deep; a held one backfills as before. A store read error keeps
        the start computed at construction (named, never silent)."""
        sym = self.symbol_map.get((dx_sym, tf, ext))
        if not sym:
            return fallback
        try:
            newest = self.store.newest_held_ms(sym, tf)
        except Exception as exc:                                    # noqa: BLE001
            logger.warning("backfill start for %s %s: store read failed (%s) - using %s",
                           sym, tf, _explain_exc(exc), fallback.isoformat())
            return fallback
        start = _backfill_start(tf, newest_held_ms=newest, held=newest is not None)
        if newest is None:
            logger.info("PRIME %s %s: the store holds none - priming %d days from TastyTrade (from %s)",
                        sym, tf, PRIME_DAYS.get(tf, 0), start.isoformat())
        return start
    def _interval_of(self, event_symbol: str) -> Optional[str]:
        """Map DXFeed's echoed candle symbol back to OUR config timeframe key.

        'AAPL{=5m}'            -> '5m'
        'AAPL{=5m,tho=true}'   -> '5m'    (attributes stripped)
        'AAPL{=m,tho=true}'    -> '1m'    (DXFeed canonicalizes 1m -> m)
        'AAPL{=h,tho=true}'    -> '1h'
        'AAPL{=d,tho=true}'    -> '1d'

        v3.7 — TWO bugs that each SILENTLY DROP EVERY CANDLE (feed stays 'active',
        authenticated, streaming, store takes ZERO writes; bots read yesterday's
        bars; no ORB range for today; fleet EXPIRED/UNKNOWN; not one error logged
        — recurred every morning 07-13/14/15):
        (1) DXFeed echoes the symbol back WITH ATTRIBUTES ('...,tho=true'); the
            old parser returned '5m,tho=true' and never matched symbol_map.
        (2) DXFeed CANONICALIZES a leading 1: we subscribe '1m'/'1h'/'1d', it
            echoes 'm'/'h'/'d'. 1m is what fetch_quote() reads (the bot's price).
        """
        if "{=" not in (event_symbol or ""):
            return None
        token = event_symbol.split("{=", 1)[1].rstrip("}")
        token = token.split(",", 1)[0].strip()      # drop ',tho=true' etc.
        return {"m": "1m", "h": "1h", "d": "1d", "s": "1s"}.get(token, token)

    @staticmethod
    def _is_ext_of(event_symbol: str) -> bool:
        """v3.16 — IS THIS ECHO FROM THE EXTENDED-HOURS SUBSCRIPTION?

        🔴 THE BUG THIS EXISTS FOR. FEED.2 subscribes the SAME dx symbol at the
        SAME interval twice — once RTH-only, once with extended_trading_hours —
        and registered both in `symbol_map` under `(dx_symbol, interval)`. The
        keys are identical, so the second assignment silently overwrote the
        first and EVERY 1h candle was routed to the EXT store symbol. Measured
        2026-08-20 across the fleet: plain `QQQ`/`SPX` 1h frozen at 2026-08-14
        while `*_EXT` 1h was current — SIX DAYS of stale higher-timeframe
        structure feeding structure_analyzer's swings and S/R, the pitchfork
        and its observer, and entry_snapshot. Nothing raised; BARS_STALE warned
        every five minutes with `refused=False` and the bots kept trading on
        08-14 bars.
        `tho=true` is the ONLY thing that distinguishes the two echoes, and
        `_interval_of` deliberately discards it. So read it here instead: the
        attribute the parser drops is exactly the attribute the router needs.
        """
        if "{=" not in (event_symbol or ""):
            return False
        attrs = event_symbol.split("{=", 1)[1].rstrip("}")
        # 🔴 v4.4 (2026-08-21) — THE POLARITY WAS BACKWARDS. This read
        #     return "tho=true" in attrs
        # but `tho` is TRADING-HOURS-ONLY: `tho=true` marks the RTH echo, and
        # its ABSENCE marks the extended one. v3.16 named the right attribute
        # and inverted its meaning.
        #
        # WHAT IT COST, measured live 2026-08-21 09:31-09:52:
        # · 1m/5m/15m/1d register ONLY (sym, tf, False). Every RTH echo looked
        #   up True, missed, and was DROPPED — the whole intraday tape, fleet
        #   wide, for a full session. The bots priced off the previous day's
        #   close because fetch_quote reads the newest 1m bar.
        # · 1h registers BOTH keys, so nothing missed — the two streams simply
        #   SWAPPED. Plain `SYM` 1h received the EXTENDED tape and `SYM_EXT`
        #   received RTH. Both looked current. That is why 1h alone appeared
        #   healthy and hid the rest.
        #
        # ⚠️ THE WRITE GUARD PARTLY MASKED IT, which is why it survived a day.
        # v3.17 re-segregates non-RTH bars off the plain route, so the misrouted
        # extended 1h bars were caught and moved — leaving plain 1h roughly
        # right BY ACCIDENT while the log said "RTH GUARD ... SEGREGATING" every
        # session and was read as the guard doing its job. A correct-looking
        # output produced by two errors cancelling is this project's failure
        # class in its purest form.
        return "tho=true" not in attrs.replace(" ", "").lower()

    def _on_candle(self, c: Candle):
        ev_sym = getattr(c, "event_symbol", "")
        base = _base_symbol(ev_sym)
        interval = self._interval_of(ev_sym) or ""
        is_ext = self._is_ext_of(ev_sym)
        key_sym = self.symbol_map.get((base, interval, is_ext))
        if key_sym is None:
            # v3.7: NEVER drop a candle silently. This branch swallowed the whole
            # feed on 07-13/14/15 (unparsed interval) with no log anywhere. Warn
            # once per distinct unmapped key so a future echo-format change is
            # visible within one line instead of a wasted session.
            if ev_sym and (base, interval, is_ext) not in self._unmapped_seen:
                self._unmapped_seen.add((base, interval, is_ext))
                logger.warning(
                    "DROPPING candles: event_symbol=%r -> (base=%r, interval=%r, "
                    "ext=%r) NOT in symbol_map %r — storing nothing for it",
                    ev_sym, base, interval, is_ext,
                    sorted(self.symbol_map.keys()))
            return
        if c.time is None or c.open is None:
            return

        # ── POISON GUARD (v3.2) ───────────────────────────────────────────────
        # DXFeed intermittently emits a junk candle: timestamp at the signed
        # 32-bit rollover (2147483648xxx ms => year 2038) with all prices 0.0.
        # Observed live on GOOGL 2026-07-13 (1m, then 15m). It is fatal
        # downstream: fetch_quote() sorts by ts DESC, so the 2038 row wins, its
        # age computes NEGATIVE (passes the freshness check), and it returns
        # close=0.0. run_analysis() treats 0.0 as falsy -> "Could not fetch
        # current price" -> the tick loop dies EVERY TICK while the unit still
        # reports ACTIVE. Silent, total. Reject it at the door: bad data must
        # never enter the store.
        try:
            ts_ms = int(c.time)
            o, h, l, cl = float(c.open), float(c.high), float(c.low), float(c.close)
        except (TypeError, ValueError):
            return

        if not (TS_MS_MIN <= ts_ms <= _ts_ms_max()):
            logger.warning(
                "REJECTED poison candle %s %s: insane ts=%d (%.1f) — outside sane window",
                key_sym, interval, ts_ms, ts_ms / 1000.0)
            return
        # v4.13 FEED.9: NaN slipped past `<= 0` and landed as NULL, which no
        # later version of the bar could ever replace.
        if not all(math.isfinite(x) and x > 0 for x in (o, h, l, cl)):
            logger.warning(
                "REJECTED poison candle %s %s ts=%d: non-positive or "
                "non-finite price "
                "(o=%.4f h=%.4f l=%.4f c=%.4f)", key_sym, interval, ts_ms, o, h, l, cl)
            return

        # ── RTH GUARD (v3.17) ────────────────────────────────────────────────
        # 🔴 THE SECOND HALF OF THE FEED.2 DEFECT. Streaming routes correctly
        # after v3.16, but a RESTART's backfill asked DXFeed for plain-symbol
        # history and got 24-HOUR BARS back — ~12 bars/hour overnight against
        # 38–39 in RTH, reaching ~15 days back (the 08-05 boundary). SPX proves
        # it is real extended-hours data and not a timezone artifact: an index
        # has no overnight session, so it shows hours 13–20 UTC only and had
        # nothing to contaminate.
        # ⚠️ WORSE THAN THE ORIGINAL HOLE. A gap announces itself; this does
        # not. The series CHANGES CHARACTER MID-STREAM — 07-31 is RTH-only,
        # 08-19 is 24-hour — with nothing marking the seam, so swings, S/R and
        # the hourly pitchfork read a discontinuity they cannot detect.
        # THE FLAG IS NOT ENOUGH. `extended_trading_hours=False` is passed on
        # the subscription and the vendor returned 24h history anyway, so the
        # guarantee has to live HERE, at the write, where it is ours to
        # enforce: a PLAIN-symbol route accepts only RTH bars. `*_EXT` routes
        # are untouched — carrying overnight is their entire purpose.
        if not _is_ext_route(key_sym) and not _within_rth(ts_ms, interval):
            # SEGREGATE, DO NOT DROP. For 5m/15m/1m there is NO extended
            # stream — EXT_INTERVAL is 1h only — so an overnight bar arriving
            # here is the ONLY copy that will ever exist, and DXFeed history is
            # use-it-or-lose-it. Discarding it to protect the RTH series would
            # trade one irreversible loss for another.
            # The plain series stays RTH-pure (which is what structure_analyzer
            # at weight 2.0, the pitchfork's 1h fractals, trend_engine's 0.20
            # context vote and entry_snapshot were all built to read), and the
            # bar is still stored — under the symbol that means "this carries
            # overnight". Nothing RTH-scoped reads it; everything can query it.
            alt = f"{key_sym}_EXT"
            self._rth_moved[(key_sym, interval)] = \
                self._rth_moved.get((key_sym, interval), 0) + 1
            if self._rth_moved[(key_sym, interval)] == 1:
                logger.warning(
                    "RTH GUARD: non-RTH bars on the plain route for %s %s "
                    "(first ts=%d) — SEGREGATING to %s so the RTH series stays "
                    "pure and no bar is lost. Counting silently from here.",
                    key_sym, interval, ts_ms, alt)
            key_sym = alt

        row = (key_sym, interval, ts_ms, o, h, l, cl,
               float(getattr(c, "volume", 0) or 0))
        self.buffer[(key_sym, interval)] = self.buffer.get((key_sym, interval), {})
        self.buffer[(key_sym, interval)][ts_ms] = row

    # ── v3.4: chain-marks handlers ─────────────────────────────────────────
    def _on_quote(self, q: Quote):
        sym = getattr(q, "event_symbol", "") or ""
        if not sym:
            return
        try:
            bid = float(q.bid_price or 0)
            ask = float(q.ask_price or 0)
        except (TypeError, ValueError):
            return
        now = _time.time()
        self._quotes_buf[sym] = (sym, bid, ask, now)
        # MANIFOLD — full fidelity alongside the fast path. Nothing dropped.
        def _f(v):
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None
        self._quote_series_buf.append((
            sym, now, _f(getattr(q, "event_time", None)),
            getattr(q, "sequence", None), getattr(q, "time_nano_part", None),
            _f(getattr(q, "bid_time", None)),
            getattr(q, "bid_exchange_code", None),
            _f(getattr(q, "ask_time", None)),
            getattr(q, "ask_exchange_code", None),
            bid, ask,
            _f(getattr(q, "bid_size", None)), _f(getattr(q, "ask_size", None)),
        ))

    def _on_greeks(self, g: Greeks):
        sym = getattr(g, "event_symbol", "") or ""
        if not sym:
            return
        try:
            row = (sym, float(g.delta or 0), float(g.gamma or 0),
                   float(g.theta or 0), float(g.vega or 0),
                   float(g.volatility or 0), _time.time())
        except (TypeError, ValueError):
            return
        self._greeks_buf[sym] = row
        # MANIFOLD — all 13 fields. `volatility`, `rho` and `price` were being
        # thrown away; volatility is the smile and rho is simply free here.
        def _g(v):
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None
        self._greeks_series_buf.append((
            sym, _time.time(), _g(getattr(g, "event_time", None)),
            getattr(g, "event_flags", None), _g(getattr(g, "index", None)),
            _g(getattr(g, "time", None)), getattr(g, "sequence", None),
            _g(getattr(g, "price", None)), _g(getattr(g, "volatility", None)),
            _g(getattr(g, "delta", None)), _g(getattr(g, "gamma", None)),
            _g(getattr(g, "theta", None)), _g(getattr(g, "rho", None)),
            _g(getattr(g, "vega", None)),
        ))

    # ── 🔴 r72 — OPENING-RANGE RESCUE ───────────────────────────────────
    # WHY THIS EXISTS. On 2026-08-21 the feed ate the open: overnight "no 5m
    # data returned" warnings, and the ORB range only ESTABLISHED at 10:01-10:03
    # ET after a manual fix. ORB entries die at 11:00, so losing the open costs
    # the WHOLE ORB DAY — and ORB is the flagship trade (96% win, +$30,696,
    # worst loss -$16). Nothing in code prevented a repeat.
    #
    # ⚠️ `get_orb_range` FAILS SOFT AND THAT IS THE TRAP. With today's 09:30 bar
    # absent it falls through to EXPIRED carrying YESTERDAY'S RANGE — a
    # plausible-looking range for the wrong day. It does not raise, it does not
    # warn loudly. That is why the outage took until 10:01 to notice.
    #
    # ⚠️ UNSUBSCRIBE FIRST, THEN RESUBSCRIBE — operator's requirement, and it
    # matters: leaving the original 5m subscription warm while adding a second
    # for the same tenor means two live subscriptions racing to write the same
    # rows. One in, one out.
    #
    # ⚠️ ONCE PER SESSION, GUARDED BY DATE. Worst case is all 15 boxes doing
    # this at the same moment during an unusual event; one extra subscribe each
    # is survivable, a retry loop is not.
    async def _maybe_rescue_opening_range(self, streamer) -> bool:
        """If today's 09:30 5m bar is missing after the window, re-pull it.

        Returns True if a rescue was attempted. Never raises.
        """
        try:
            now = datetime.now(ET)
            today = now.date().isoformat()
            if self._orb_rescue_done_for == today:
                return False
            # Only between 09:36 (the bar has had a minute to arrive) and the
            # 11:00 ORB cutoff — after that the rescue cannot help anything.
            if not (now.weekday() < 5
                    and ((now.hour == 9 and now.minute >= 36)
                         or (10 <= now.hour < 11))):
                return False
            # v4.8 — THE 09:30 BAR ITSELF, not "anything since the open".
            _open_ms = int(datetime.combine(
                now.date(), dtime(9, 30), tzinfo=ET).timestamp() * 1000)
            row = self.store.conn.execute(
                "SELECT COUNT(*) FROM candles WHERE symbol=? AND interval='5m'"
                " AND ts_epoch_ms >= ? AND ts_epoch_ms < ?",
                (INSTRUMENT, _open_ms, _open_ms + 300_000)
            ).fetchone()
            if row and row[0]:
                return False                    # the bar is there; nothing to do

            self._orb_rescue_done_for = today   # set BEFORE the attempt
            logger.warning("ORB RESCUE: today's 09:30 5m bar is MISSING at %s "
                           "— resubscribing 5m from the open. get_orb_range "
                           "would otherwise carry YESTERDAY's range as EXPIRED.",
                           now.strftime("%H:%M:%S"))
            start = datetime.combine(now.date(), dtime(9, 30), tzinfo=ET)
            try:
                await streamer.unsubscribe_candle(self.dx_symbol, "5m")
                logger.info("ORB RESCUE: unsubscribed %s 5m", self.dx_symbol)
            except Exception as exc:                            # noqa: BLE001
                # ⚠️ NOT FATAL, BUT NAMED. If the unsubscribe fails the
                # resubscribe below may leave two live subscriptions for one
                # tenor, so the operator needs to see it rather than have it
                # swallowed.
                logger.warning("ORB RESCUE: unsubscribe failed (%s) — "
                               "resubscribing anyway; watch for duplicate 5m",
                               _explain_exc(exc))
            await streamer.subscribe_candle(
                [self.dx_symbol], "5m", start_time=start,
                extended_trading_hours=False)
            logger.warning("ORB RESCUE: resubscribed %s 5m from %s",
                           self.dx_symbol, start.isoformat())
            return True
        except Exception as exc:                                # noqa: BLE001
            logger.error("ORB RESCUE failed: %s — the feed is unaffected",
                         _explain_exc(exc))
            return False

    # ── MANIFOLD PART 2 HANDLERS ────────────────────────────────────────
    # ⚠️ EVERY FIELD THE EVENT CARRIES IS BUFFERED. No selection at capture:
    # the feed's job is to make analysis possible, not to decide what will
    # turn out to be interesting.
    @staticmethod
    def _n(v):
        """Number or None — NEVER 0.0 as a fallback."""
        if v is None:
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return None if f != f else f

    @staticmethod
    def _s(v):
        return None if v is None else str(v)

    def _on_trade(self, t):
        sym = _base_symbol(getattr(t, "event_symbol", "") or "")
        if not sym:
            return
        n, ss = self._n, self._s
        self._trade_buf.append((
            sym, _time.time(), n(getattr(t, "event_time", None)),
            n(getattr(t, "time", None)), getattr(t, "sequence", None),
            ss(getattr(t, "exchange_code", None)), getattr(t, "day_id", None),
            ss(getattr(t, "tick_direction", None)),
            1 if getattr(t, "extended_trading_hours", False) else 0,
            n(getattr(t, "price", None)), n(getattr(t, "change", None)),
            n(getattr(t, "size", None)), n(getattr(t, "day_volume", None)),
            n(getattr(t, "day_turnover", None))))

    def _on_time_and_sale(self, ts_ev):
        """Every print. ⚠️ `aggressor_side` IS THE PRIZE — buy vs sell
        initiated, per print. Nothing in this repo has ever seen who lifted
        the offer versus hit the bid."""
        sym = _base_symbol(getattr(ts_ev, "event_symbol", "") or "")
        if not sym:
            return
        n, ss = self._n, self._s
        self._prints_buf.append((
            sym, _time.time(), n(getattr(ts_ev, "event_time", None)),
            n(getattr(ts_ev, "index", None)), n(getattr(ts_ev, "time", None)),
            getattr(ts_ev, "sequence", None),
            ss(getattr(ts_ev, "exchange_code", None)),
            n(getattr(ts_ev, "price", None)), n(getattr(ts_ev, "size", None)),
            n(getattr(ts_ev, "bid_price", None)),
            n(getattr(ts_ev, "ask_price", None)),
            ss(getattr(ts_ev, "aggressor_side", None)),
            1 if getattr(ts_ev, "spread_leg", False) else 0,
            1 if getattr(ts_ev, "extended_trading_hours", False) else 0,
            1 if getattr(ts_ev, "valid_tick", False) else 0,
            ss(getattr(ts_ev, "type", None)), ss(getattr(ts_ev, "buyer", None)),
            ss(getattr(ts_ev, "seller", None)),
            ss(getattr(ts_ev, "exchange_sale_conditions", None))))

    def _on_summary(self, sm):
        """⚠️ CARRIES prev_day_close_price — a SECOND, independent source for
        the scalar `runaway_continuation` takes as `prev_close`, whose 1d
        dependency is invisible at its call site and which was missing from the
        warehouse entirely on 2026-08-21."""
        sym = _base_symbol(getattr(sm, "event_symbol", "") or "")
        if not sym:
            return
        n = self._n
        self._summary_buf.append((
            sym, _time.time(), n(getattr(sm, "event_time", None)),
            getattr(sm, "day_id", None), getattr(sm, "prev_day_id", None),
            n(getattr(sm, "open_interest", None)),
            n(getattr(sm, "day_open_price", None)),
            n(getattr(sm, "day_high_price", None)),
            n(getattr(sm, "day_low_price", None)),
            n(getattr(sm, "day_close_price", None)),
            n(getattr(sm, "prev_day_close_price", None)),
            n(getattr(sm, "prev_day_volume", None))))

    def _on_underlying(self, u):
        """⚠️ put_call_ratio, front/back volatility — TERM STRUCTURE AND FLOW
        SKEW FROM THE VENDOR, no derivation needed."""
        sym = _base_symbol(getattr(u, "event_symbol", "") or "")
        if not sym:
            return
        n = self._n
        self._underlying_buf.append((
            sym, _time.time(), n(getattr(u, "event_time", None)),
            n(getattr(u, "index", None)), n(getattr(u, "time", None)),
            getattr(u, "sequence", None), n(getattr(u, "volatility", None)),
            n(getattr(u, "front_volatility", None)),
            n(getattr(u, "back_volatility", None)),
            n(getattr(u, "call_volume", None)), n(getattr(u, "put_volume", None)),
            n(getattr(u, "option_volume", None)),
            n(getattr(u, "put_call_ratio", None))))

    def _on_theo(self, tp):
        # 🔴 r116 — THE FULL STREAMER SYMBOL, NOT THE BASE. TheoPrice is a
        # PER-CONTRACT analytic: `.QQQ260825C495`, `.QQQ260825C500`, ... and
        # `theo_series` is keyed PRIMARY KEY (symbol, ts_epoch). Collapsing to
        # "QQQ" via _base_symbol would land every contract on the SAME key at
        # the same second, so ~250 strikes would overwrite one another and the
        # table would look populated while holding one arbitrary contract.
        # That is worse than the empty table it replaces: an empty table is
        # visibly empty, and this would have been silently wrong.
        sym = str(getattr(tp, "event_symbol", "") or "").strip()
        if not sym:
            return
        n = self._n
        self._theo_buf.append((
            sym, _time.time(), n(getattr(tp, "event_time", None)),
            n(getattr(tp, "index", None)), n(getattr(tp, "time", None)),
            getattr(tp, "sequence", None), n(getattr(tp, "price", None)),
            n(getattr(tp, "underlying_price", None)),
            n(getattr(tp, "delta", None)), n(getattr(tp, "gamma", None)),
            n(getattr(tp, "dividend", None)), n(getattr(tp, "interest", None))))

    async def _reconcile_chain_subs(self, streamer):
        """Every flush cycle: make the socket's Greeks/Quote subscriptions match
        what the bot requested via chain_subs. Expiry rollover unsubscribes all
        and clears the marks table (yesterday's 0DTE symbols are dead air)."""
        expiry, symbols = self.store.read_chain_subs()
        if not symbols:
            return
        if expiry != self._chain_expiry:
            if self._chain_subscribed:
                logger.info("chain marks: expiry rollover %s -> %s — resubscribing",
                            self._chain_expiry or "(none)", expiry)
                await streamer.unsubscribe_all(Greeks)
                await streamer.unsubscribe_all(Quote)
                # r118 — nothing to unsubscribe; TheoPrice is no longer
                # subscribed. Left as a comment so the next reader does not
                # re-add an unsubscribe for a stream that has no subscription.
            self._chain_subscribed.clear()
            self._quotes_buf.clear()
            self._greeks_buf.clear()
            self.store.clear_chain_marks()
            self._chain_expiry = expiry
        new = [s for s in symbols if s not in self._chain_subscribed]
        if new:
            # v3.5: CHUNKED subscribes. An SPX 0DTE chain is hundreds of
            # strikes; one giant subscribe frame risks a websocket 1009
            # (message too long) that would bounce the ENTIRE socket —
            # candles included. 75 symbols per frame is comfortably small.
            for i in range(0, len(new), 75):
                chunk = new[i:i + 75]
                await streamer.subscribe(Greeks, chunk)
                await streamer.subscribe(Quote,  chunk)
                # r116 — TheoPrice rides the SAME per-contract subscription.
                # It was subscribed to the plain ticker with the four
                # underlying-level aux events, where nothing publishes it:
                # accepted, then silent since 2026-08-22. Proven on QQQ
                # 2026-08-24 by tools/probe_aux_streams.py — 12 events on 12
                # option symbols, 0 on the ticker, with Greeks/Quote as
                # controls. Wrapped alone so an entitlement gap costs THIS
                # stream and not the chain marks everything trades on.
                # 🔴 r118 — REVERTED, 2026-08-25 09:40 ET, MID-SESSION.
                # r116 added TheoPrice here and it landed on the fleet last
                # night. This morning SPX lost its ENTIRE per-contract
                # subscription at 13:27 UTC — greeks, quotes, chain marks and
                # theo all stopped at the SAME instant (age 688-698s) while
                # ticker-level events kept arriving, so options_chain returned
                # None every tick and SPX could not evaluate a single strategy
                # during the ORB window. QQQ on identical code stayed healthy.
                # ⚠️ THE ASYMMETRY IS WIDTH: SPX is 500 contracts (7 chunks),
                # QQQ 372 (5). Adding a THIRD event type to each chunk is the
                # only change, and SPX is where it first crossed whatever the
                # limit is. The per-chunk try/except did NOT save it — the
                # subscribe succeeded (theo had 5026 rows) and the connection
                # degraded later, which is a failure mode a wrapper cannot see.
                # ⚠️ THE COST OF KEEPING IT IS A TRADING DAY; the cost of
                # dropping it is a stream NOTHING READS YET. Not a close call.
                # theo_series and _on_theo stay — the writer is correct and the
                # probe proved the symbol space. Re-enable only behind a
                # per-symbol opt-in, tested on ONE narrow box, never fleet-wide
                # on a session morning.
            self._chain_subscribed.update(new)
            logger.info("chain marks: subscribed %d new symbols (%d total, expiry %s)",
                        len(new), len(self._chain_subscribed), expiry)

    def _flush(self):
        rows: List[Tuple] = []
        for bucket in self.buffer.values():
            rows.extend(bucket.values())
        self.buffer = {}
        self.store.upsert_candles(rows)
        # v3.4: chain marks ride the same flush cadence
        q, g = list(self._quotes_buf.values()), list(self._greeks_buf.values())
        self._quotes_buf.clear()
        self._greeks_buf.clear()
        self.store.upsert_chain_quotes(q)
        self.store.upsert_chain_greeks(g)
        # ── MANIFOLD (2026-08-22) — the full-fidelity series ride the same
        # flush. Taken and cleared BEFORE the write so a raising writer cannot
        # make the buffer grow without bound across cycles.
        # ⚠️ WRAPPED SO A SERIES WRITE CAN NEVER STALL CAPTURE. Operator's
        # rule: derived/observational data INFORMS, it never blocks. The raw
        # candle and chain_marks writes above have already committed; if these
        # fail the tape is still intact and the gap shows up as a short series
        # rather than as a dead feed.
        gs, qs = self._greeks_series_buf, self._quote_series_buf
        self._greeks_series_buf, self._quote_series_buf = [], []
        pr, tr = self._prints_buf, self._trade_buf
        sm, un, th = self._summary_buf, self._underlying_buf, self._theo_buf
        self._prints_buf, self._trade_buf = [], []
        self._summary_buf, self._underlying_buf, self._theo_buf = [], [], []
        try:
            self.store.append_greeks_series(gs)
            self.store.append_quote_series(qs)
            self.store.append_prints(pr)
            self.store.append_last_trade(tr)
            self.store.append_session_summary(sm)
            self.store.append_underlying(un)
            self.store.append_theo(th)
        except Exception as exc:                                # noqa: BLE001
            logger.warning("series append failed (%d greeks, %d quotes): %s "
                           "— raw tape unaffected", len(gs), len(qs), exc)
        self.store.heartbeat()
        self.store.commit()
        return len(rows) + len(q) + len(g)

    def _log_backfill_depth(self):
        """One-time per (symbol, interval): report depth vs required count so
        entitlement gaps surface in the journal (FIRST-RUN CHECKLIST #1)."""
        for (dx_sym, tf, _start, _ext) in self.subs:
            sym = self.symbol_map[(dx_sym, tf, bool(_ext))]
            if self.backfill_logged.get((sym, tf)):
                continue
            n = self.store.bar_count(sym, tf)
            need = TIMEFRAMES.get(tf, {}).get("candles", 0) if sym == INSTRUMENT else 1
            level = logging.INFO if n >= need else logging.WARNING
            logger.log(level, "backfill %s %s: %d bars in store (need %d)%s",
                       sym, tf, n, need, "" if n >= need else "  << SHORT — check entitlement")
            self.backfill_logged[(sym, tf)] = True

    @staticmethod
    def _feed_stood_down() -> bool:
        """Should this run stand down? v4.3: MAINTENANCE, and nothing else.

        ONE predicate, TWO call sites (the reconnect gate and the RTH-over
        break). v3.9 wrote the same condition inline in both places and v3.10
        had to patch both; a third caller would have had to remember a third
        time. It is a method so the two can never disagree again.

        THE DISTINCTION IS PURPOSE, NOT TIME — which is the whole lesson of
        2026-08-01..08-04. What the gate protects against is a box HOLDING a
        live DXLink subscription when there is no session to serve it: the
        maintenance wake that put 29 boxes on the wire for work needing no
        market data. A `--once` run holds nothing. It connects, pulls HISTORY
        from 09:30, flushes and exits, and history does not stop existing at
        16:00 — so gating it on the clock blocked the ONLY path the EOD candle
        retrieval has, silently, for two sessions.

        SERVICE MODE (once=False) is unchanged from v3.9 in every respect.

        ── FEED.1 (2026-08-15) — THE THIRD PURPOSE ────────────────────────────
        MAINTENANCE is HARD OFF and overrides everything, `--once` included.
        It exists because the operator needs a window where all 29 boxes can be
        up for fleet updates with nothing on the wire — and that CANNOT be a
        clock rule, because the overnight capture pass runs at the same hours
        and wants the opposite.

        ⚠️ IT ANNOUNCES ITSELF AT WARNING. The 2026-08-03/04 loss was a silent
        gate: `Feed idle — outside RTH` at INFO, then `0 bars`, then fourteen
        38-byte header-only CSVs, and DXFeed history is same-evening only so
        both sessions are gone. **A suppressed run must never be mistakable for
        a failed fetch**, so this says the mode by name and says the data is
        NOT being collected.
        """
        if _maintenance_now():
            if not getattr(CandleFeed, "_maint_said", False):
                CandleFeed._maint_said = True
                # v4.3 — the trailing "%s" arg used to read
                # `"including this --once run" if once else "service mode"`.
                # `once` is no longer a parameter, so that line raised
                # NameError the first time maintenance was declared — and
                # `import candle_feed` could not see it, because the name is
                # only resolved when this branch RUNS. Found by
                # tests/check_feed_always_on.py driving the predicate, which is
                # the whole argument for executing checks rather than reading
                # source (WORKING_AGREEMENT 21).
                logger.warning(
                    "[feed-mode] MAINTENANCE - standing down completely. NO "
                    "candles will be collected on this box until OT_FEED_MODE "
                    "is cleared. This is DELIBERATE, not a fetch failure; if "
                    "you expected tape, the mode is wrong.")
            return True
        # v4.3 — THE RTH CLAUSE IS GONE. It used to read
        #     `return not is_rth() and not once`
        # and its own rationale above is what retired it: the gate existed so a
        # MAINTENANCE wake could not put 29 BOXES on the wire at once. The fleet
        # is 15 and they are the same 15 every day; a normal session already
        # carried ~20 boxes on this feed without strain, so the crowd the gate
        # was sized for no longer exists. Operator, 2026-08-20: boxes subscribe
        # whenever they are up.
        #
        # ⚠️ MAINTENANCE SURVIVES, AND IT IS NOW THE ONLY REASON TO STAND DOWN.
        # It was never the clock rule — it is the window where the fleet can be
        # up with nothing on the wire, and it must stay expressible.
        # ⚠️ `once` IS NO LONGER A PARAMETER. It existed to exempt the one-shot
        # EOD pull from a CLOCK rule; with no clock rule there is nothing to be
        # exempt from, and maintenance overrode it anyway. A parameter that can
        # no longer change the answer is a parameter that misleads the reader.
        return False

    async def run(self, once: bool = False):
        session = get_session()
        backoff = RECONNECT_MIN_S
        while True:
            # ── FEED STAND-DOWN GATE ─────────────────────────────────────────
            # HISTORY, kept because it is the reasoning and not the rule.
            # 2026-08-01 this became an RTH gate: the loop had no time gate at
            # all (`Restart=always`, no timer), so while a box was UP the feed
            # subscribed continuously — invisible on a normal day because
            # phase_report stopped the instances at EOD, but it meant every
            # MAINTENANCE wake put 29 boxes back on the wire at once for work
            # needing no market data. FEED.1 then added maintenance as a third
            # purpose, and v3.9/v3.10 had to exempt `--once` from the clock rule
            # after two sessions of tape were lost to header-only CSVs.
            #
            # v4.3 (2026-08-20) RETIRES THE CLOCK RULE ENTIRELY. The crowd it
            # was sized for is gone: 15 boxes, the same 15 daily. What remains
            # is MAINTENANCE — a purpose, not a time — which is exactly what
            # `_feed_stood_down`'s own doctrine said the distinction always was.
            #
            # ⚠️ WHAT HOLDING THE SOCKET 24h DOES AND DOES NOT DO.
            # It does NOT contaminate the RTH series: the v4.2 write guard
            # routes every non-RTH bar to <SYM>_EXT, for EVERY interval, so
            # overnight 1m/5m/15m are stored and segregated rather than dropped
            # or merged. It does NOT add chain snapshots outside RTH:
            # `analysis.chain_snapshot.snapshot()` takes the chain as an
            # ARGUMENT and is called from main.py's tick loop, which returns
            # early on `not is_rth()` — so chain archival is still RTH-only and
            # this change cannot alter it in either direction.
            # ⚠️ SPX HAS NO OVERNIGHT SESSION. An index producing nothing
            # between 16:00 and 09:30 is correct, not a fetch failure — it is
            # the same control that proved the v4.2 contamination was real.
            # v4.3 — MAINTENANCE ONLY. The sleep-until-open block that lived
            # here is deleted rather than left dead: a branch that can no longer
            # run still reads as live to anyone auditing the file.
            #
            # ⚠️ AND IT FIXES A LATENT DEFECT ON THE WAY OUT, stated because it
            # is a behaviour change and not merely a deletion. The old block
            # slept only while `seconds_until_rth_open() > FEED_WARM_LEAD_S`,
            # and that function RETURNS 0 DURING RTH — so maintenance declared
            # inside the session fell straight through and connected anyway.
            # The hard-off was silently defeated in exactly the hours a fleet
            # update is most disruptive. Standing down is now unconditional.
            # ⚠️ r288 — THE DISK GUARD WAS HERE AND HAS MOVED TO main.py's TICK
            # LOOP. This `while True` is the RECONNECT loop, not a tick loop: an
            # `async with DXLinkStreamer` below opens the stream and an inner
            # loop handles events for the life of that connection, so a check
            # here ran ONCE PER CONNECTION.
            if self._feed_stood_down():
                await asyncio.sleep(60)
                continue
            try:
                async with DXLinkStreamer(session) as streamer:
                    # v3.4: fresh socket — chain subscriptions must be rebuilt
                    self._chain_expiry = ""
                    self._chain_subscribed.clear()
                    # v3.8: subscribe each (symbol, tf) INDEPENDENTLY. A single
                    # failing subscribe_candle used to throw out of the whole
                    # `async with`, killing the ENTIRE stream — so one bad symbol
                    # or timeframe (e.g. an entitlement gap on XOM) took down all
                    # candles, for two days, with only a wrapped "unhandled errors
                    # in a TaskGroup" to show for it. Now a failure is logged with
                    # its REAL cause (see _explain_exc) and skipped.
                    ok_subs = 0
                    for (dx_sym, tf, start, ext) in self.subs:
                        start = self._start_for(dx_sym, tf, ext, start)   # r16: from the store, every (re)subscribe
                        try:
                            await streamer.subscribe_candle(
                                [dx_sym], tf, start_time=start,
                                extended_trading_hours=ext)
                            logger.info("subscribed %s %s from %s%s", dx_sym, tf,
                                        start.isoformat(),
                                        "  [EXTENDED HOURS]" if ext else "")
                            ok_subs += 1
                        except Exception as sub_e:
                            logger.error("SUBSCRIBE FAILED %s %s: %s — continuing without it",
                                         dx_sym, tf, _explain_exc(sub_e))
                    if ok_subs == 0:
                        raise RuntimeError("no candle subscriptions succeeded")
                    logger.info("%d/%d candle subscriptions live", ok_subs, len(self.subs))
                    await self._reconcile_chain_subs(streamer)
                    backoff = RECONNECT_MIN_S
                    last_flush = 0.0
                    last_prune = _time.time()
                    # ── 🔴 MANIFOLD PART 2 (2026-08-22) — SUBSCRIBE THE REST ─
                    # Five event types the SDK offers that this feed never
                    # asked for. Each is subscribed INDEPENDENTLY and wrapped,
                    # so an entitlement gap costs THAT ONE PORT on THIS ONE BOX
                    # and is named in the log — never the whole socket.
                    # r116 — TheoPrice is NOT here any more: it is per-CONTRACT
                    # and now rides the chain subscription in
                    # _reconcile_chain_subs. Underlying stays: it IS an
                    # underlying-level event and the ticker is the right space
                    # for it, though it has never published either — retest
                    # during RTH before calling it uncarried, since the 45s
                    # after-hours probe saw only 1 Trade on this arm.
                    # 🔴 r36 — QUOTE JOINS THE UNDERLYING SET (FEED.2). r64 took
                    # FOUR of the five streams for the ticker and left Quote,
                    # because Quote WAS subscribed — per CONTRACT, in
                    # `_reconcile_chain_subs`, where the bot needs it to price a
                    # spread. So the underlying's own bid/ask was never asked
                    # for: measured 2026-09-17, **0 of 22,846,560 `quote_series`
                    # rows are a non-option symbol**.
                    # ⚠️ IT IS THE ONLY SOURCE OF RESTING DEPTH. `prints` says
                    # what TRADED; `bid_size`/`ask_size` say what is WAITING —
                    # and the operator's question is where size parks, which
                    # traded volume cannot answer. Measured the same day:
                    # volume within ±$0.25 of a session extreme carries a lift of
                    # 1.02x against a random price in the traded band, i.e. none.
                    # A level that HELD is one price turned away from, so volume
                    # AT it conflates absorption with traversal. Depth does not.
                    # ⚠️ COLLECTION ONLY, AND NOTHING READS IT (§31). It is
                    # subscribed here, stored by `_on_quote` — which already keys
                    # on `event_symbol` and is symbol-agnostic, so no handler
                    # changes — and read by no decision. It is banked until there
                    # is enough of it to answer the question with numbers.
                    # ⚠️ AND IT RIDES THE WRAPPED, INDEPENDENT SUBSCRIBE BELOW,
                    # NOT THE CHAIN'S CHUNKED ONE. r118 is why that distinction
                    # matters: adding a stream to the per-CONTRACT subscription
                    # cost SPX its ENTIRE chain subscription mid-session on
                    # 2026-08-25 — greeks, quotes and marks all stopped at the
                    # same instant. Each stream here fails alone and says so.
                    for _ev, _label in ((Trade, "Trade"),
                                        (TimeAndSale, "TimeAndSale"),
                                        (Summary, "Summary"),
                                        (Underlying, "Underlying"),
                                        (Quote, "Quote")):
                        try:
                            await streamer.subscribe(_ev, [self.dx_symbol])
                            logger.info("subscribed %s %s", self.dx_symbol, _label)
                        except Exception as exc:                # noqa: BLE001
                            logger.warning("SUBSCRIBE FAILED %s %s: %s — "
                                           "continuing without it",
                                           self.dx_symbol, _label, exc)
                    quiet_since: Optional[float] = None
                    while True:
                        try:
                            c = await asyncio.wait_for(streamer.get_event(Candle), timeout=1.0)
                            self._on_candle(c)
                            quiet_since = None
                        except asyncio.TimeoutError:
                            if quiet_since is None:
                                quiet_since = _time.monotonic()
                        # v3.4: drain any queued Greeks/Quote events, non-blocking
                        while True:
                            g = streamer.get_event_nowait(Greeks)
                            if g is None:
                                break
                            self._on_greeks(g)
                        while True:
                            q = streamer.get_event_nowait(Quote)
                            if q is None:
                                break
                            self._on_quote(q)
                        # MANIFOLD PART 2 — drain the five new streams the
                        # same way. Wrapped as a group: an unexpected payload
                        # shape from any one of them must not stop the candle
                        # loop, which is the tape everything else depends on.
                        try:
                            for _ev, _fn in ((Trade, self._on_trade),
                                             (TimeAndSale, self._on_time_and_sale),
                                             (Summary, self._on_summary),
                                             (Underlying, self._on_underlying),
                                             (TheoPrice, self._on_theo)):
                                while True:
                                    _e = streamer.get_event_nowait(_ev)
                                    if _e is None:
                                        break
                                    _fn(_e)
                        except Exception as exc:                # noqa: BLE001
                            logger.debug("aux stream drain: %s", exc)
                        now = _time.monotonic()
                        if now - last_flush >= FLUSH_INTERVAL_S:
                            await self._reconcile_chain_subs(streamer)
                            # r72 — rides the flush cadence, so the check costs
                            # one indexed COUNT every ~15s and only inside the
                            # 09:36-11:00 window. Self-disarming after one
                            # attempt per date.
                            await self._maybe_rescue_opening_range(streamer)
                            n = self._flush()
                            last_flush = now
                            if n:
                                logger.debug("flushed %d bars", n)

                            # v3.9 — SESSION IS OVER: drop the socket. The gate at
                            # the top of the reconnect loop only decides whether
                            # to CONNECT; without this the feed would stream on
                            # past 16:00 for as long as the box happened to stay
                            # up. That is the case that matters — the operator
                            # must be able to FORGET a box is up and have it not
                            # be a problem, which is this project's standing rule
                            # about anything depending on someone remembering.
                            # Rides the existing flush cadence rather than adding
                            # a timer: we are already here, once per cycle.
                            # Flushed first (above), so no buffered bar is lost.
                            # v3.9 — `and not once` here too, and this one is the
                            # blocker a naive fix would have missed. This break
                            # sits ABOVE the --once drain-exit, so a one-shot run
                            # outside RTH would connect, break out on its first
                            # flush cycle, return to the outer loop, hit the gate
                            # again and sleep — the same hang, one layer down,
                            # with the backfill still undrained. Both sites had
                            # to move together or neither works.
                            # v4.3 — no longer an "RTH over" break: the socket
                            # is held through the close. This fires only when
                            # MAINTENANCE is declared mid-run, which must take
                            # effect without waiting for a restart.
                            if self._feed_stood_down():
                                logger.warning(
                                    "MAINTENANCE declared — closing DXLink "
                                    "socket and releasing all subscriptions. "
                                    "NO candles collected until OT_FEED_MODE "
                                    "is cleared."
                                )
                                break
                            self._log_backfill_depth()
                            if once and quiet_since is not None and (now - quiet_since) > 8.0:
                                logger.info("--once: backfill drained, exiting")
                                return
                        # ── FEED.3 (2026-08-15) — PRUNING IS OFF BY DEFAULT ──
                        # ⚠️ THE BOUND WAS SIZED FOR THE LIVE LOOP AND KEPT
                        # SILENTLY CONSTRAINING ANALYTICAL CONSUMERS THAT
                        # ARRIVED LATER. It has now bitten twice: PF.2 found the
                        # boxes held 84 daily bars while the engine was handed
                        # 10 ("the history was never missing - the frame was"),
                        # and LIQ.6's 10-day section lookback landed on exactly
                        # the 240-row 1h ceiling with ZERO margin.
                        #
                        # AND IT WAS NEVER BUYING ANYTHING. Measured: a FULL
                        # YEAR of every interval, extended hours, is **54 MB per
                        # box** - on an 8 GB root. Ten days is 1.5 MB. The
                        # pruner was tidiness, not capacity.
                        #
                        # Operator's call: no pruning. The local store keeps
                        # what it collects; S3 is the archive and the weekend
                        # reporting reads the bucket, so the box no longer has
                        # to be the deep copy of anything.
                        # ⚠️ THE POISON PURGE IS UNTOUCHED AND MUST STAY - it
                        # deletes BAD rows (non-positive prices, 2038-stamped
                        # DXFeed rollover junk), not OLD ones. Different method,
                        # different purpose.
                        if PRUNE_KEEP_ROWS and _time.time() - last_prune >= PRUNE_EVERY_S:
                            for (dx_sym, tf, _s, _e) in self.subs:
                                sym = self.symbol_map[(dx_sym, tf, bool(_e))]
                                self.store.prune(sym, tf, PRUNE_KEEP_ROWS)
                            self.store.commit()
                            last_prune = _time.time()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._flush()
                # v3.8: UNWRAP. asyncio TaskGroup raises an ExceptionGroup whose
                # str() is only "unhandled errors in a TaskGroup (1 sub-exception)"
                # — the real DXFeed cause is in .exceptions and was thrown away,
                # leaving XOM in a 60s reconnect loop with NO diagnosable reason
                # for two days (07-13 -> 07-15).
                logger.error("feed stream error: %s — reconnecting in %ds",
                             _explain_exc(e), backoff)
                logger.debug("feed stream traceback:\n%s",
                             "".join(traceback.format_exception(type(e), e, e.__traceback__)))
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, RECONNECT_MAX_S)


class _TTNoiseFilter(logging.Filter):
    """r134 — drop the tastytrade SDK's DEBUG chatter, keep its parse failures.
    A HANDLER filter, not a logger level: the SDK logs from child loggers
    (tastytrade.streamer), and a filter on the parent never sees their records."""

    KEEP = ("Failed to parse event",)

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno > logging.DEBUG or not record.name.startswith("tastytrade"):
            return True
        return record.getMessage().startswith(self.KEEP)


def _install_tt_noise_filter() -> None:
    for h in logging.getLogger().handlers:
        if not any(isinstance(f, _TTNoiseFilter) for f in h.filters):
            h.addFilter(_TTNoiseFilter())


def main():
    # r146 — never stream a guessed symbol (see config.INSTRUMENT_UNSET).
    import sys
    from config import INSTRUMENT_UNSET
    if INSTRUMENT == INSTRUMENT_UNSET:
        sys.stderr.write("CRITICAL: OT_INSTRUMENT is not set - candle feed refusing to start.\n")
        sys.exit(78)
    from config import INSTRUMENT_LISTED          # r175 (SYM.1)
    if not INSTRUMENT_LISTED:
        sys.stderr.write("CRITICAL: OT_INSTRUMENT=%s is not in config.STRIKE_INCREMENTS - "
                         "candle feed refusing to start.\n" % INSTRUMENT)
        sys.exit(78)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    _install_tt_noise_filter()
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true",
                    help="backfill, flush, exit (smoke test)")
    ap.add_argument("--db", default=None, help="override store path")
    args = ap.parse_args()

    if args.db:
        os.environ["OT_FEED_DB"] = args.db
    store = FeedStore(feed_db_path())
    logger.info("candle_feed v3.8 — store=%s symbol=%s (dxfeed=%s) vix=%s",
                feed_db_path(), INSTRUMENT, _dxfeed_symbol(), VIX_SYMBOL)
    store.purge_poison()   # v3.2: self-heal any pre-existing poison rows

    feed = CandleFeed(store)
    loop = get_loop()
    fut = asyncio.run_coroutine_threadsafe(feed.run(once=args.once), loop)
    try:
        fut.result()          # blocks for service lifetime
    except KeyboardInterrupt:
        fut.cancel()
    finally:
        store.close()


if __name__ == "__main__":
    main()
