"""
database/trade_logger.py  v5.3
v5.3  2026-10-26  OTV5 r34 (SCHEMA.2) — is_liquidity_hunt IS A COLUMN. EntryEngine.enter has always put it in the record
      (r12), but the trades table had no column, so log_entry dropped it from every insert with a "[schema] ... DROPPED"
      WARNING: all 54 trades of 2026-10-26 lost it (the readers fall back to strategy == "LiquidityHunt"). Now it is in
      the CREATE and the migration adds, and the boot that ADDS it to an existing store backfills it exactly as the writer
      would have (1 where strategy = 'LiquidityHunt', the only strategy that sets it), once, at the add.
v5.2  2026-10-25  OTV5 r15 (SCHEMA.1) — NO COLUMN OR TABLE IS EVER DROPPED AT BOOT, AND tape_band IS A COLUMN. The boot migration
      dropped, by difference, every trades column and every table outside this tree's shape. The legacy fleet's trades
      (mainline otv4 r499) carry tape_band, which this tree lacked, so a repoint to OTV5 (NVDA, preflight 2026-10-25) would
      have PHYSICALLY DROPPED tape_band and its values at the first start. The operator: "We don't want less columns -
      that would be a mistake." (1) tape_band REAL, no default (NULL = not recorded, never 0), after tape_prints_at_level
      in the CREATE and _MIGRATION_ADDS - mainline r499's exact shape; analysis/tape_at_level.measure already returns it.
      (2) A column or table outside this tree's shape is KEPT with its values and named once in the log
      ("[schema] kept ..."). Retiring schema is now a named, reviewed act, never a side effect of a boot.
v5.1  2026-10-25  OTV5 r8 (LIN.1) — EVERY NEW TRADE ROW IS STAMPED lineage "OTV5", THE ENGINE THAT PRODUCED IT. "TEST" named the predecessor's second engine; this tree is the third, and control's strategy_registry v1.4 (otv4 r503) knows it. Rows already in a store keep their stamp (OTV4, TEST or NULL): the boot migration adds no default and nothing relabels. The operator, 2026-10-25: "just send it".
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.23 2026-10-18  OTV4TEST r298 (CAP.4) — today_summary's docstring stops claiming it equals realized_pnl_today(): since r288
      the cap excludes PARK and the displays do not. Docstring only; no code change in this file.
v4.22 2026-10-18  OTV4TEST r288 (PARK.1) — realized_pnl_today(exclude_strategies=()) - the catastrophic cap passes
      config.CAP_EXCLUDED_STRATEGIES (PARK: its own budget, outside the cap). Unset = every closed row, so status, query,
      EOD and today_summary are unchanged.
v4.21 2026-10-04  OTV4TEST r245 (LIVE.1 B3, MIRROR OF otv4 r467 b32c73b, WA 38.2) — A PARTIAL LIVE EXIT SURVIVES A RESTART: the close's state (filled portions, the working order id) is saved to the row's new live_exit_state column after the submit and after every pass, and loaded first; a restart resumes the working order or submits only the REMAINDER, and the booked price is the weighted average of every fill. Code hunks applied verbatim; getsource sha256[:16] of _exit_state_load / _exit_state_save / _confirm_and_book_live_exit identical to b32c73b (a71ca216 / b44de96e / 1819bebc).
v4.20 2026-10-03  OTV4TEST r198 (MEAS.1, SHARED SHAPE) — pnl_pct IS SIGNED BY pnl_usd. log_exit stored (exit - entry) / entry for
      every trade, so every credit trade's loss read as a gain (11 of 11 SweepCreditSpread rows here; it corrupted a
      fleet strategy table on 2026-09-17). The magnitude is unchanged; the sign now follows the booked pnl_usd. Ruled
      2026-09-17; pinned by tests/check_pnl_pct_sign.py. No decision path reads the stored column.
v4.19 2026-09-27  OTV4TEST r165 (EXP.1) — close_expired_open_trades(settle=...) BOOKS THE
      SETTLEMENT. This is the path an overnight-expired position actually takes (boot Step 1, paper
      AND live), and it forced pnl_usd to 0.0: an exercised ITM winner booked as nothing. A caller
      may pass `settle(record) -> (exit_price, pnl_usd, label) | None`; a settled row books its
      exit_price, pnl_usd and exit_reason "<reason>_<label>". A row settle() cannot price keeps the
      old flagged 0.0, as before. With no settle, behaviour is unchanged.
      🔴 AND A DEFECT FROM THE v4 PORT (08-19): close_phantom's RECOVERED branch wrote
      `exit_price=?` - there is NO exit_price column (it is exit_premium), so the first LIVE
      phantom whose real fill was recovered from order history would have raised
      OperationalError instead of booking. Paper never runs that path. Both writes now use
      exit_premium. Shared with otv4 (same line, ported from v3).
v4.18 2026-09-25  OTV4TEST r143 — EVERY CONNECTION IS CLOSED. `with self._connect() as conn:`
      COMMITS but does NOT close a sqlite3 connection, and these sit in a
      reference cycle, so each call left its file handle open until the cyclic
      GC happened to run. MEASURED 2026-09-25: AAL 511 open handles on trades.db,
      SOFI 219, this box 137, climbing ~8/min against a 1024 soft limit; at the
      limit EVERY open fails ("unable to open database file") - on AAL three times,
      ~23 minutes blind, and the first path to fail is update_current_premium
      inside POSITION MANAGEMENT. Reproduced in isolation: 200 calls -> 200
      handles, freed only by gc.collect(). All 22 sites now use `_db()`, which
      commits/rolls back exactly as `with conn:` did and then CLOSES.
v4.17 2026-09-25  OTV4TEST r140 — EVERY NEW TRADE ROW CARRIES `lineage = 'TEST'`.
      control's r426/OPS.50 keys every per-strategy rollup on (lineage, code),
      because six strategy names exist in BOTH engines as DIFFERENT code (md5
      differs on all six), so pooling them by name pools two designs. The
      field name and the values MAIN/TEST are one contract across both repos
      (operator, 2026-09-25: "Yes to the lineage question using test").
      ⚠️ THE MIGRATION DOES NOT BACKFILL. The column has NO default: rows
      that already exist stay NULL, and only `log_entry` stamps TEST. When this
      tree supersedes mainline IN PLACE it inherits a trades.db of MAIN rows,
      and a DEFAULT 'TEST' would relabel that whole history on the first boot
      - and, because s3_push dedupes on a hash of the whole row, re-push it all
      as TEST. NULL is what control's resolver already reads as "untagged".
v4.16 2026-09-13  OTV4TEST r25 — the "[spent]" log line reads `is_breach_exit()`, the same
      label set the lock reads, so a management-plan `breach:` / `acceptance:`
      close is logged as spending its level (r24 logged only the engine labels).
v4.15 2026-09-13  OTV4TEST r24 — THE CLOSE HOOK NO LONGER WRITES DECISION STATE INTO MEMORY.
      It finished runaway breaks in a set a restart wiped, and it spent sweep
      levels through a read of `is_credit_vertical` — not a column — that raised
      on every close. Both facts are now READ by the plans from this table; the
      hook logs them. Operator's rule (DEC.1): nothing a trade decides on lives
      only in memory.
v4.14  2026-09-09  OTV4TEST r11 — three columns for the condor's final form:
      `final_form_basis`, `final_form_group`, `cumulative_credit` (migrated in
      place, like every column since v3). Written by condor_roll v4.8 on a
      risk-free roll; read by exit_engine v4.16's group floor.
v4.13  2026-09-09  OTV4TEST r5 — A SWEEP LEVEL IS SPENT ON AN ACCEPTED BREACH, NOT
      ON A STOP-OUT. Operator: "A held level remains, but an accepted breach and
      continuation means that level is spent." `mark_spent` fires only when the
      exit reason is `sweep_breach_accepted` (exit_engine v4.13); a 15% lone
      stop on a wobble leaves the level live for the next rejection.
v4.12  2026-09-08  OTV4TEST r3 — A RUNAWAY EXIT FINISHES ITS BREAK WHATEVER THE
      SIGN. r174 finished the break only on a LOSS, so a trail winner could
      re-enter on the same standing state the instant it closed. Operator:
      one per break, any exit; the next runaway on that break must re-validate
      on actual (the 50 lost on a close, then accepted again — runaway_plan
      v1.0 watches for it and re-opens the key). The credit-vertical branch is
      unchanged (still loss-only, its own rule).
v4.11  2026-09-08  r315 — `log_accretion`: a credit vertical that PARTIAL-filled
      and later fills more of the same structure is ONE position, so the row's
      size and basis move together — contracts, blended entry_premium, and the
      max_loss / total_cost / stop_premium that are arithmetic on those two.
      Before this a partial's unfilled remainder was cancelled and never
      re-offered (main.py 2332 said it "must resume" and nothing did). Written
      by `execution/credit_remainder.py` only; the exit engine reads the
      blended row exactly as it reads any other.
v4.10  2026-09-03  r223 — 🔴 THE ONE-RUNAWAY-PER-BREAK GUARD HAS NEVER FIRED.
      `direction` is a DECLARED COLUMN THAT NOTHING WRITES (line 261; the only
      other reference in this file was the losing-exit hook READING it), so
      `_dir` was always "" — which broke the guard twice: `_dir == "long"` was
      False so the hook took `orb_range_LOW` as a LONG break's boundary, and
      it keyed `("", <low>)` while `prepare()` checks `("long", <high>)`. The
      keys could never match, so no runaway break has been finished since
      r174 introduced the rule.
      🔑 MEASURED: QQQ 2026-09-03, FIVE runaway entries between 09:52 and
      10:21 with stops at -21%, -21% and -32%, net -$530 by 10:22 — every
      re-entry following an exit that should have closed the break.
      🔑 DIRECTION IS DERIVED FROM `option_side`, which the runaway DOES set
      (runaway_continuation:575): a call is a long break, a put a short one.
      `orb_range_high/low` were already set (581/582); `direction` was the one
      field the hook needed and the one nobody wrote.
      ⚠️ AND `except Exception: pass` GUARANTEED THE SILENCE. The success path
      logged; the failure path said nothing, for every stop-out for a week.
      An unkeyable exit is now NAMED and states plainly that another entry on
      that break is still possible.
v4.9  2026-09-01  r212 (chunk D) — `log_exit` CLOSES THE PLAN THAT PRODUCED
      THE TRADE. Hooked here for the same reason r154's spent lock is: this is
      the ONE choke point every close passes through, and a rule with a hole in
      it is worse than none because it fires sometimes and is trusted always.
      Never raises — a bookkeeping failure must not stop a position being
      booked closed. The symbol comes off the row via `_get_field`, the way
      every other hook in this function gets it; a first cut called a
      `self._instrument()` that does not exist on this class (§0.1).
v4.8
v4.8  2026-08-28  r179: count_today(strategy) — the DB-backed one-per-
      session count (survives restarts, which the in-process registries did
      not; five bounces on 08-28 re-armed the butterfly through two
      hotfixes). Fails CLOSED: an unreadable DB counts as 1.
v4.7  2026-08-28  r174: a losing runaway exit calls finish_break() — one
      runaway per ORB break per session; the break key is (direction, the
      broken boundary from the record's orb_range fields).
v4.6  2026-08-27  r167: the spent-level lock on a losing exit covers EVERY
      lone credit vertical (operator: "a lone credit spread stops out at a
      15% floor & the level that it sold at is marked finished"); TCS keys
      on the ORB bound it sold against (underlying_stop) when it has no pool.
v4.5  2026-08-27  r163: the spent-level lock for a stopped-out trade on a
      MOVING level (a fork tine) is keyed by the level's NAME, not its
      drifting price — the sweep plan reads the same key.
v4.4  2026-08-24  r103: orb_entry_since() — did an ORB trade actually open at or
      after a confirming bar? The adjudicator for fired-vs-missed, so a MISSED
      row is never written for a setup a prior process took and recorded.
v4.3  2026-08-24  CONDOR STOP SUPPRESSION: stop_suppressed_ts /
      stop_suppressed_by columns (schema + migration). Written by exit_engine
      v4.4 while a complementary condor leg is open, cleared on re-arm.
      While stop_suppressed_ts is set, condor_stop cannot be the exit —
      forensics should treat any contrary row as a defect. stop_premium is
      untouched and remains the immutable entry-time floor.

v4.2  2026-08-24  CONDOR REMODEL: condor_trigger_source column (schema +
      migration) — which of the four independent triggers produced the
      credit spread. BACKFILLED BUMP: this change shipped in the r89b
      archive without a version bump (base_strategy v4.2's changelog even
      pointed at a literal "trade_logger v(+1)"); recorded here so the
      header stops lying about the schema.

v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Trade schema, entry/exit logging, migrations.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

database/trade_logger.py — Options trade logging (SQLite). v3.15
SWALLOW T1: this file's silent handler(s) now announce
        themselves once. Behaviour unchanged in every case; only the silence
        was the defect.
TCS.4: log_entry FILTERS TO REAL COLUMNS AND WARNS.
        It INSERTed every key in the record, so a key with no column raised
        OperationalError and CRASH-LOOPED a live box (NFLX, 2026-08-17).
        A record key that is not a column is a BUG IN THE CALLER, but it must
        not be able to take a trading box down. Unknown keys are dropped.
        WARNED ONCE PER KEY NAME, because silently dropping a field that was
        SUPPOSED to persist is Pattern 2 - the class that produced this bug.
        Census run at the same time: `is_trend_credit` was the ONLY offender;
        this filter is a guardrail against the next one, not a fix for a
        population. PRAGMA is cached, not run per insert. FAILS OPEN if the
        schema cannot be read.
the two v3.12 setters now LOG INSIDE their except bodies.
        The 2026-08-05 swallow census flagged both as new TIER-1 silent
        handlers (87 -> 89) the morning after W.2a's lesson was written down:
        the census reads the HANDLER BODY, so a bare `return False` is silent
        no matter what the caller does. No behaviour change — the callers still
        warn once per reason and nothing gates on the result.
CONTRACT TELEMETRY (entry_delta/gamma/theta/iv,
        entry+exit bid/ask, exit_iv, chain_iv_rank) via set_entry_contract() /
        set_exit_contract(). TEN columns, not twelve: `entry_mark` and
        `chain_spot_at_entry` were dropped from the first cut because
        `entry_premium` and `underlying_entry` ALREADY HOLD THOSE FACTS. Two
        names for one value is how a report ends up quietly reading the stale
        one. Auto-migrates.
        Observability only — nothing gates on these.
        THE GAP IT CLOSES: every other instrument in this repo measures the
        labels) while the P&L is PREMIUM. Without the contract's own state,
        "wrong on direction", "right but theta ate it" and "IV crushed after
        the open" collapse into one number — and on 0DTE that is the whole game.
        NOTHING NEW IS FETCHED: OptionContract already carries bid/ask/mark/
        delta/gamma/theta/vega/iv and OptionsChain carries spot_price/iv_rank.
        They were read for strike selection and discarded.
        NULLS ARE LOAD-BEARING: rows from before this shipped must stay
        distinguishable from a capture that ran, so there are no defaults.
        See docs/MECHANICS.md "Contract telemetry" for what is collected and
        which reports read it.
EXIT LATENCY (N.5): exit_submit_ts / exit_fill_ts /
        exit_latency_ms / exit_ladder_steps / exit_escalated /
        exit_mark_at_trigger, plus set_exit_latency() (returns a bool, same
        reason as v3.10). Auto-migrated; NULL on every pre-existing row and on
        any close that was never confirmed.
        WHY IT MOVED FORWARD FROM AUG 24 TO THE AUG 10 BAKE: the dataset only
        accrues in sessions recorded AFTER it deploys, and TC.2's stop-trigger
        decision (-40% vs 35% vs 25%) is explicitly "calibrate against measured
        ladder fill-latency". At Aug 24 that is ~5 paper sessions before live
        capital; at Aug 10 it is ~15. Identical argument to v3.10's.
        `exit_mark_at_trigger` IS THE MEASUREMENT and is an addition to N.5's
        four named fields: latency in milliseconds is not a cost until it is
        priced, and the cost is (mark when the exit fired) - (price it actually
        filled at). In PAPER the two are equal by construction — that equality
        is the plumbing proof, not a result.
        TELEMETRY ONLY — nothing reads these columns in the trading path.
ENTRY SNAPSHOT: `entry_snapshot` (TEXT, JSON written by
        analysis/entry_snapshot.py) + set_entry_snapshot(), which RETURNS a
        boolean instead of discarding it. Auto-migrated; NULL on every
        pre-existing row and on any row whose capture failed.
        WHY: the TC.2 exit bake-off compares BoS / trail / 5m-FVG on IDENTICAL
        entries, and two of those three need the zone inventory the live engine
        held at entry. BoS does not — it re-derives from entry price and the
        post-entry tape — so only the FVG frame, its anchor, and the per-frame
        bar depth are stored. The 5m frame is CONTINUOUS across sessions while
        the banked tape is session-scoped RTH, so an offline reconstruction is
        a different object, not a cheaper one (same divergence class as defect
        S). Like v3.9 it pays off only in sessions recorded after it deploys,
        so its value decreases every session until the 2026-08-21 freeze.
        WHY IT RETURNS A BOOLEAN: update_fields() discards success, and
        AlertManager._send discarding an existing boolean is precisely what
        turned the blind-alert failure into a five-step hunt (item AU). A
        capture that silently no-ops would leave a column of NULLs that looks
        identical to "no trades taken".
        TELEMETRY ONLY — nothing reads this column in the trading path.
MFE/MAE TIMESTAMPS: max_premium_seen_at /
        min_premium_seen_at (TEXT, UTC ISO via ts_for_db — the SAME base as
        entry_time, deliberately, because comparing a UTC field against an
        ET-offset one has already inverted one verdict here). Auto-migrated,
        NULL on every pre-existing row.
        WHY, and why it could not wait: v3.8 stored the excursion EXTREMES as
        values with no time attached. That is enough to measure HOW MUCH a
        winner gave back and useless for asking WHETHER IT COULD HAVE BEEN
        EXTENDED — a trade that peaked at minute 2 and bled for twenty minutes
        and one that ran to the exit and reversed on the last tick produce the
        identical (MFE, realized) pair, and they call for opposite fixes: the
        first says the leash is too loose, the second says the move simply
        turned. No quantity of additional sessions resolves that; only the
        timestamp does. It pays off ONLY in sessions recorded after it
        deploys, so its value is strictly decreasing until the 2026-08-21
        freeze.
        TELEMETRY ONLY — no trade mechanics touched. The timestamp advances
        only when the extreme itself advances (CASE on the pre-update row),
        so it marks WHEN the peak/trough was set, not when it was last
        re-confirmed. SQLite evaluates every SET right-hand side against the
        ORIGINAL row regardless of clause order, so the CASE reads the old
        extreme even though it is written alongside the new one — proven by
        test_mfe_timestamp_tracks_only_new_highs rather than asserted.
        Consumers MUST treat NULL as "not recorded" and never as zero or as
        entry time: every row banked before this deploy has it.
F5 FIX (exit-reason integrity): new trail_stop column
        (schema + migration) + update_trail_stop(). The trail is now persisted
        separately; stop_premium is the immutable entry-time -25% floor.
        update_stop() removed — its only caller (position_manager) overwrote
        stop_premium with the trail, so every trail-armed exit was labeled
        'hard_stop_25pct'/'stop_hit'. Restart survivability preserved: the
        exit engine seeds its in-memory trail from trail_stop on recovery.
v3.0 — original release
add orb_range_high, orb_range_low, current_premium
        columns to schema for ORB exit logic and live P&L display
condor-leg support: spread columns (short/long strike,
        credit, width, is_condor_leg, condor_leg_num, is_broken_wing,
        short/long symbol) + get_open_trades() for concurrent condor legs.
add generic update_fields() (used by the broken-wing roll
        to flag rolled/tested legs is_broken_wing).
DEFINITIVE realized-P&L primitive: realized_pnl_today()
        (single source of truth for the daily-loss circuit breaker, status and
        query) with ET-correct session bucketing; today_summary() routed through
        it so displays and the halt can never disagree.
expiry-aware orphan handling: get_open_trades_live() (open
        rows not yet expired — 0DTE and weeklies alike, plus unknown-expiry rows
        kept for safety) and close_expired_open_trades() (auto-close ONLY rows
        whose expiry date has passed — a weekly with time left is left alone).
        Keyed on the stored expiry (YYYY-MM-DD), never on entry date, so a
        multi-day weekly is never mistaken for a same-day ghost.
broker reconciliation support: is_short_position column
        (schema + migration) so an adopted short survives a re-restart; and
        close_phantom() to close a DB row the broker no longer shows (broker is
        the source of truth for existence on live).
MFE/MAE TELEMETRY: max_premium_seen / min_premium_seen
        columns (auto-migrated), updated in the same per-tick write as
        current_premium. The evidence base for exit-threshold tuning — pairs
        with exit_engine v3.8's runner refinements so 40% floor / 5m FVGs /
        clamp / sweep runner mode can be judged on excursion data, not vibes.
MODE ISOLATION (audit defect Q). Every decision/session
        read is scoped to the current mode's rows via COALESCE(paper_trade,1):
        get_open_trade(s), close_expired_open_trades, get_session_losses,
        get_consecutive_losses, and _closed_today_rows — the DAILY_LOSS_LIMIT
        source of truth. A live bot can no longer adopt open paper positions or
        gate the real-money breaker on paper P&L (and paper stays clean of live
        rows symmetrically). Row WRITES are untouched — trade_id-keyed updates
        need no mode. Companion: configure.sh v2.0 archives trades.db on every
        mode switch so histories never mix in one file to begin with.
close_phantom() accepts recovered exit_price/pnl_usd so a
        manually-closed-at-broker phantom books its REAL fill from order history
        (broker_reconcile.match_closing_fills) instead of a flagged $0.00.
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
"""
# v3.11 (2026-08-04, N.5) — trades table also captures the exit ladder's latency: exit_submit_ts, exit_fill_ts, exit_latency_ms, exit_ladder_steps, exit_escalated and exit_mark_at_trigger. Written by exit_engine.place_exit_order() — the ONE seam both paper and live close through — via set_exit_latency(). This is the dataset TC.2's stop-trigger decision reads. Auto-migrates. Observability only.
# v3.10 (2026-08-04) — trades table also captures entry_snapshot: the FVG zones, the frame the trail would anchor to, the live StructureMap levels and the per-timeframe bar depth, all as held at the moment of the fill. Written by analysis/entry_snapshot.py via set_entry_snapshot(); the TC.2 exit bake-off is not computable without it. Auto-migrates. Observability only.
# v-obs2 (2026-07-24) — trades table also captures swept_level_name + level_strength (what KIND of liquidity level a sweep fired against — named PDH/PDL/session vs equal-H/L). Sweep postmortems: does level conviction predict outcome? Auto-migrates.



import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from config import DB_PATH, PAPER_TRADING
from utils.time_utils import ts_for_db, now_utc, now_et, ET

logger = logging.getLogger(__name__)
_WARNED_UNKNOWN_COLS: set = set()   # TCS.4: warn once per unknown key
_WARNED_SCHEMA_READ: set = set()    # SWALLOW T1: warn once if PRAGMA fails

# r140 — the PRODUCER tag control's rollups key on. One field name; the value names the ENGINE:
# OTV4 (the predecessor's production tree), TEST (the predecessor's second tree), OTV5 (this tree, from r8).
# ⚠️ A cross-repo contract, not a label: control must list a value in strategy_registry.LINEAGES before any
# box writes it, or the box map relabels the row (dtp strategy_registry v1.4 lists OTV5).
LINEAGE = "OTV5"


@dataclass
class TradeRecord(dict):
    """
    Options trade record. Inherits from dict so it works as both
    a typed object and a sqlite3.Row-compatible mapping.
    """
    pass


def make_record(**kwargs) -> TradeRecord:
    r = TradeRecord()
    r.update(kwargs)
    return r


class TradeLogger:
    """SQLite-backed trade log for options_trader."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS trades (
        trade_id          TEXT PRIMARY KEY,
        symbol            TEXT,
        strategy          TEXT,
        setup_type        TEXT,
        setup_grade       TEXT,
        -- 🔴 r154 — THE LEVEL THIS TRADE WAS SOLD AGAINST. Without it, the exit
        -- path cannot tell the sweep strategy WHICH pool just failed, and the
        -- level re-arms forever. CVX 2026-08-27: four entries on the same
        -- 198/192 pool in five minutes, -$104, because nothing connected the
        -- stop-out back to the boundary.
        pool_price        REAL,
        setup_score       REAL,
        direction         TEXT,
        option_side       TEXT,
        is_butterfly      INTEGER DEFAULT 0,
        is_liquidity_hunt INTEGER DEFAULT 0,
        strike            REAL,
        lower_strike      REAL,
        center_strike     REAL,
        upper_strike      REAL,
        expiry            TEXT,
        contracts         INTEGER,
        entry_premium     REAL,
        exit_premium      REAL,
        current_premium   REAL DEFAULT 0.0,
        net_debit         REAL,
        max_profit        REAL,
        total_cost        REAL,
        max_loss          REAL,
        stop_premium      REAL,
        trail_activation  REAL,
        trail_stop        REAL DEFAULT 0.0,
        target_premium    REAL,
        underlying_entry  REAL,
        underlying_stop   REAL,
        underlying_target REAL,
        orb_range_high    REAL DEFAULT 0.0,
        orb_range_low     REAL DEFAULT 0.0,
        -- ── r119 (2026-08-25): THE ORB SETUP'S GEOMETRY, RECORDED. ─────────
        -- Operator: "the closer to the range boundary the impulsive candle
        -- (stop location) sits, the lower the risk & higher the R-value."
        -- ⚠️ RECORDED, NOT GRADED. Operator: "observe first." Nothing reads
        -- these; no gate, no size, no score. They exist so that in a few weeks
        -- the bands can be FITTED rather than guessed, and so the question
        -- "do deep-break setups FAIL more, or merely COST more?" can be
        -- answered — those have different answers (a gate vs a size).
        -- ⚠️ NULL, NOT 0.0, and for the reason gap_pct is NULL above: a ratio
        -- of exactly zero is impossible here, but a MISSING one is common
        -- (non-ORB trades, or an ORB fire whose range never established), and
        -- a numeric default makes "not applicable" indistinguishable from
        -- "measured". That confusion is what hollowed out flat_angle_deg.
        --
        -- stop_width_pct  = |entry - stop| / ORB width
        --     How deep inside the range the invalidation sits. The operator's
        --     depth measure: small = stop hugs the boundary = cheap to be
        --     wrong; large = the impulsive candle ran far and the stop is
        --     structurally distant.
        -- planned_r       = |target - entry| / |entry - stop|
        --     The R the setup OFFERED at fire time. This is the report card's
        --     numerator: realised R can then be compared against what was
        --     available, per setup, rather than against a house average.
        stop_width_pct    REAL,
        planned_r         REAL,
        -- r120: which attempt on this ORB range fired. 0 = not an ORB trade.
        -- r120: what the TAPE did at the break level while it was contested.
        -- NULL when unmeasurable — zero volume at a level is a real reading,
        -- an unreadable store is not, and they must stay distinguishable.
        tape_vol_at_level      REAL,
        tape_buy_frac_at_level REAL,
        tape_prints_at_level   INTEGER,
        -- OTV5 r15: the price band tape_prints_at_level counted in (mainline r499's shape).
        tape_band              REAL,
        short_strike      REAL DEFAULT 0.0,
        long_strike       REAL DEFAULT 0.0,
        credit_received   REAL DEFAULT 0.0,
        spread_width      REAL DEFAULT 0.0,
        is_condor_leg     INTEGER DEFAULT 0,
        condor_leg_num    INTEGER DEFAULT 0,
        is_broken_wing    INTEGER DEFAULT 0,
        is_short_position INTEGER DEFAULT 0,
        short_symbol      TEXT,
        long_symbol       TEXT,
        pnl_usd           REAL,
        pnl_pct           REAL,
        vix_at_entry      REAL,
        adx_at_entry      REAL DEFAULT 0.0,
        flat_angle_deg    REAL DEFAULT 0.0,
        -- A2.6b (2026-08-18): the overnight gap, MEASURED. NULL default, not
        -- 0.0 -- a gap of exactly zero is a real reading (the market opened
        -- unchanged) and a numeric default would be indistinguishable from it.
        -- That confusion is what made flat_angle_deg, level_strength and
        -- vix_at_entry look like measured nulls rather than empty columns.
        gap_pct           REAL,
        -- v4.0: 1 when the trade was admitted under RELAXED entry criteria.
        -- ⚠️ THE POPULATION MUST STAY SEPARABLE FOREVER. Relaxed trades exist
        -- to exercise plumbing and stops on deliberately mediocre entries; a
        -- threshold fitted to a book half of which was knowingly junk is worse
        -- than no threshold. Defaults 0 - and unlike v3's numeric defaults this
        -- one is unambiguous, because "not relaxed" IS the meaningful zero.
        relaxed_entry     INTEGER DEFAULT 0,
        -- ── v4.0: THE EXCURSION, AND WHEN IT HAPPENED ──────────────────────
        -- ⚠️ `max_profit` IS NOT MFE. It is written ONCE at entry from
        -- `signal.max_profit`, which for a defined-risk structure is the
        -- THEORETICAL maximum (wing width minus debit). Anyone reading it as
        -- realized favourable excursion - as this project nearly did on
        -- 2026-08-20 - is reading a plan as an outcome.
        -- The real excursion WAS tracked: `exit_engine`'s `peak_close` updates
        -- every tick to drive the trailing stop, and is **discarded when the
        -- position closes.** Same defect as `pin_concentration` and
        -- `flat_angle_deg`: computed every tick, used for a decision, never
        -- recorded - so a question that needed it could not be asked of the
        -- book at all.
        -- WHAT THEY ARE FOR: the sideways-grinder stop. Operator, 2026-08-20:
        -- *"we just need one more to protect sideways grinders and bleeders."*
        -- A time stop and a decay stop behave very differently, and the number
        -- should be measured. `mfe_bars` is the question - **how long until a
        -- winner declared itself** - and nothing in the v3 book could answer it.
        mfe_premium       REAL,      -- best mark seen while the position lived
        mfe_bars          INTEGER,   -- bars from entry to that peak
        mae_premium       REAL,      -- worst mark seen
        mae_bars          INTEGER,
        swept_level_name  TEXT DEFAULT '',
        level_strength    REAL DEFAULT 0.0,
        entry_snapshot    TEXT,
        exit_submit_ts    TEXT,
        exit_fill_ts      TEXT,
        exit_latency_ms   INTEGER,
        exit_ladder_steps INTEGER,
        exit_escalated    INTEGER,
        exit_mark_at_trigger REAL,
        is_fed_day        INTEGER DEFAULT 0,
        status            TEXT DEFAULT 'open',
        exit_reason       TEXT,
        order_id          TEXT,
        lower_symbol      TEXT,
        center_symbol     TEXT,
        upper_symbol      TEXT,
        option_symbol     TEXT,
        paper_trade       INTEGER DEFAULT 1,
        entry_time        TEXT,
        exit_time         TEXT,
        notes             TEXT,
        condor_trigger_source TEXT DEFAULT '',
        stop_suppressed_ts TEXT DEFAULT '',
        stop_suppressed_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS circuit_breaker_events (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        event_time      TEXT,
        reason          TEXT,
        session_losses  INTEGER,
        notes           TEXT
    );

    """

    def __init__(self, db_path: str = DB_PATH,
                 paper_trading: bool = PAPER_TRADING):
        self.db_path = db_path
        # v3.7 (defect Q): every read that drives DECISIONS or SESSION TRUTH is
        # scoped to the CURRENT MODE's rows. Paper and live share one schema,
        # but a live bot must never manage paper positions or gate its daily
        # loss limit on paper P&L — and vice versa. paper_trade defaults to 1
        # in the schema, so legacy rows count as paper (safe: live sees none).
        self._mode_flag = 1 if paper_trading else 0
        self._ensure_db()

    def _ensure_db(self):
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.executescript(self.SCHEMA)
        # Migrate existing DBs — add columns if missing
        _MIGRATION_ADDS = [
            ("current_premium", "REAL DEFAULT 0.0"),
            ("max_premium_seen", "REAL"),
            ("min_premium_seen", "REAL"),
            # v3.9 — WHEN each extreme was set (UTC ISO). NULL = not recorded;
            # never read it as zero or as entry time.
            ("max_premium_seen_at", "TEXT"),
            ("min_premium_seen_at", "TEXT"),
            ("orb_range_high",  "REAL DEFAULT 0.0"),
            ("orb_range_low",   "REAL DEFAULT 0.0"),
            ("short_strike",    "REAL DEFAULT 0.0"),
            ("long_strike",     "REAL DEFAULT 0.0"),
            ("credit_received", "REAL DEFAULT 0.0"),
            ("spread_width",    "REAL DEFAULT 0.0"),
            ("is_condor_leg",   "INTEGER DEFAULT 0"),
            ("condor_leg_num",  "INTEGER DEFAULT 0"),
            ("is_broken_wing",  "INTEGER DEFAULT 0"),
            ("short_symbol",    "TEXT"),
            ("long_symbol",     "TEXT"),
            ("is_short_position", "INTEGER DEFAULT 0"),
            ("trail_stop",      "REAL DEFAULT 0.0"),
            ("adx_at_entry",      "REAL DEFAULT 0.0"),
            ("flat_angle_deg",    "REAL DEFAULT 0.0"),
            ("gap_pct",           "REAL"),          # A2.6b
            ("relaxed_entry",     "INTEGER DEFAULT 0"),   # v4.0
            ("mfe_premium",       "REAL"),          # v4.0
            ("mfe_bars",          "INTEGER"),       # v4.0
            ("mae_premium",       "REAL"),          # v4.0
            ("mae_bars",          "INTEGER"),       # v4.0
            ("swept_level_name",  "TEXT DEFAULT ''"),   # v-obs: swept level kind (sweep postmortems)
            ("level_strength",    "REAL DEFAULT 0.0"),
            # v3.10 — entry-time FVG/structure picture as JSON. NO DEFAULT and
            # no empty-string sentinel: NULL means "not captured", and that has
            # to stay distinguishable from a capture that ran and found nothing
            # (which writes a real payload with "anchor":null).
            ("entry_snapshot",    "TEXT"),
            # v3.11 (N.5) — exit ladder latency. NULLs are load-bearing here:
            # a close that never confirmed has no fill instant, and inventing
            # one would put a zero-latency row in the exact population the
            # trigger decision is measured on.
            ("exit_submit_ts",      "TEXT"),
            ("exit_fill_ts",        "TEXT"),
            ("exit_latency_ms",     "INTEGER"),
            ("exit_ladder_steps",   "INTEGER"),
            ("exit_escalated",      "INTEGER"),
            ("exit_mark_at_trigger", "REAL"),
            # v3.12 — CONTRACT TELEMETRY. Every one of these values was already
            # in memory at fill time (OptionContract carries bid/ask/mark/delta/
            # gamma/theta/vega/iv; OptionsChain carries spot_price/iv_rank) and
            # was read for strike selection and then DISCARDED. Nothing new is
            # fetched, subscribed or computed.
            # WHY IT MATTERS: every instrument in this repo measures the
            # UNDERLYING's path, but the P&L is PREMIUM. Without these, "wrong
            # on direction", "right but theta ate it" and "IV crushed" are one
            # number — and on 0DTE they are the whole game.
            # NULL means NOT CAPTURED and is load-bearing: rows written before
            # this shipped must stay distinguishable from a capture that ran.
            # No defaults, for the same reason entry_snapshot has none.
            ("entry_delta",       "REAL"),
            ("entry_gamma",       "REAL"),
            ("entry_theta",       "REAL"),
            ("entry_iv",          "REAL"),
            ("entry_bid",         "REAL"),
            ("entry_ask",         "REAL"),
            ("exit_bid",          "REAL"),
            ("exit_ask",          "REAL"),
            ("exit_iv",           "REAL"),
            ("chain_iv_rank",     "REAL"),
            # v4.3 condor remodel — which trigger produced this credit spread
            ("condor_trigger_source", "TEXT DEFAULT ''"),
            # v4.3 condor stop suppression (exit_engine v4.4) — set while a
            # complement is open, cleared on re-arm. SEPARATE fields, never a
            # mutation of stop_premium (see update_trail_stop's v3.1 lesson).
            ("stop_suppressed_ts", "TEXT DEFAULT ''"),
            ("stop_suppressed_by", "TEXT DEFAULT ''"),
            # r119 — ORB setup geometry. NULL, never 0.0: see the schema note.
            ("stop_width_pct",    "REAL"),
            ("planned_r",         "REAL"),
            ("tape_vol_at_level",      "REAL"),
            ("tape_buy_frac_at_level", "REAL"),
            ("tape_prints_at_level",   "INTEGER"),
            ("tape_band",              "REAL"),              # OTV5 r15 (mainline r499)
            # OTV4TEST r11 — the condor's final form (condor_roll v4.8, exit_engine v4.16)
            ("final_form_basis",       "REAL"),
            ("final_form_group",       "TEXT DEFAULT ''"),
            ("cumulative_credit",      "REAL"),
            # OTV4TEST r140 — which ENGINE wrote the row (see LINEAGE). NO
            # DEFAULT, on purpose: existing rows stay NULL rather than being
            # relabelled, because on an in-place supersede they are MAIN's.
            ("lineage",                "TEXT"),
            # r467 / B3 — a part-filled live close: {"fills": [[qty, net], ...],
            # "order_id", "last_order_id"}. NULL otherwise. Written only by
            # exit_engine._exit_state_save.
            ("live_exit_state",        "TEXT"),
            # OTV5 r34 (SCHEMA.2) — EntryEngine.enter's hunt flag; backfilled at the add, below.
            ("is_liquidity_hunt",      "INTEGER DEFAULT 0"),
        ]
        for col, definition in _MIGRATION_ADDS:
            try:
                conn.execute(f"ALTER TABLE trades ADD COLUMN {col} {definition}")
                if col == "is_liquidity_hunt":      # r34: what the writer would have put there (liquidity_hunt sets it)
                    conn.execute("UPDATE trades SET is_liquidity_hunt = 1 WHERE strategy = 'LiquidityHunt'")
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Column already exists
        # data said which engine produced a label: L2.5 vs the v1.3 fallback was
        # recoverable only from a [L2 c=..]/[v13] tag in bot.log, so on 2026-07-30
        # the question "has L2.5 ever run?" needed a fleet-wide log grep across
        # 138k-line files. It also means every session's first ~25 minutes are
        # v1.3-labelled by design (the RANGING/COMPRESSION 1m warm-up), and no fit
        # could exclude them without this column. Provenance belongs in the row.
        # ── OTV5 r15 (SCHEMA.1): NOTHING ON DISK IS DROPPED AT BOOT ──
        # Until r15 every column and table outside this tree's shape was dropped
        # BY DIFFERENCE here. Across a repoint that destroys data: the legacy
        # fleet's tape_band (mainline r499) is not in a tree that never had it.
        # A column or table this tree does not know is KEPT with its values and
        # named once; log_entry still writes only the columns it knows. Retiring
        # schema is a named, reviewed act, never a side effect of a boot.
        _scratch = sqlite3.connect(":memory:")
        _scratch.executescript(self.SCHEMA)
        _canon = {r[1] for r in _scratch.execute("PRAGMA table_info(trades)")}
        _keep_tables = {r[0] for r in _scratch.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        _scratch.close()
        _canon |= {c for c, _ in _MIGRATION_ADDS}
        _extra_cols = [r[1] for r in conn.execute("PRAGMA table_info(trades)")
                       if r[1] not in _canon]
        _extra_tables = [t for (t,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")
            if t not in _keep_tables and not t.startswith("sqlite_")]
        if _extra_cols or _extra_tables:
            logger.info("[schema] kept outside this tree's shape (never dropped): columns %s tables %s",
                        _extra_cols or "none", _extra_tables or "none")
        conn.commit()
        conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _db(self):
        """A connection for ONE block: commit on success, rollback on error -
        exactly what `with conn:` did - and then CLOSE it.
        🔴 r143: `with self._connect() as conn:` never closed. The handles
        leaked until the cyclic GC ran and, at 1024, every open on the box
        failed. Callers of the bare `_connect()` must close it themselves."""
        conn = self._connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _columns(self) -> set:
        """Real column names of `trades`, cached. PRAGMA once, not per insert."""
        if getattr(self, "_cols_cache", None) is None:
            try:
                with self._db() as conn:
                    self._cols_cache = {r[1] for r in
                                        conn.execute("PRAGMA table_info(trades)")}
            except Exception as exc:                           # noqa: BLE001
                # ⚠️ FAIL OPEN: if the schema cannot be read, insert everything
                # exactly as before rather than dropping fields on a guess.
                # ⚠️ AND SAY SO — SWALLOW T1, 2026-08-17. This handler was
                # SILENT when it shipped, which meant the crash-loop guard could
                # DISABLE ITSELF WITH NO WORD: a failed PRAGMA sends log_entry
                # straight back to inserting every record key, which is the
                # exact condition that crash-looped NFLX the day before. A guard
                # that can turn itself off quietly is not a guard.
                if not _WARNED_SCHEMA_READ:
                    _WARNED_SCHEMA_READ.add(1)
                    logger.warning(
                        "[schema] could not read the `trades` column list (%s) - "
                        "FAILING OPEN: every record key will be inserted, so an "
                        "unknown key will raise on the INSERT again. The TCS.4 "
                        "guard is NOT active on this box until this clears.", exc)
                return set(TradeRecord.__annotations__) if hasattr(
                    TradeRecord, "__annotations__") else set()
        return self._cols_cache

    def count_today(self, strategy: str) -> int:
        """How many trades this STRATEGY has entered THIS ET SESSION — open or
        closed. r179, operator 2026-08-28 after the butterfly stacked through
        two hotfixes and every restart: *"Only one runway debit trade aloud
        per session on a box. Only one GEX Pin butterfly allowed per session
        on a box. Simple."* DB-backed so it SURVIVES RESTARTS — the in-process
        registries (r174 breaks, r178 pins) cleared on every systemd bounce,
        and 08-28 had five of them. entry_time is stored UTC; the session
        boundary is the ET date, so the window is [ET-midnight in UTC, now].
        ⚠️ FAILS CLOSED: an unreadable DB counts as 1 — cannot-prove-zero
        does not trade (a missed entry is recoverable; a stack is not).
        """
        try:
            from utils.time_utils import ET
            from datetime import datetime, timezone
            _et_mid = datetime.now(ET).replace(hour=0, minute=0, second=0,
                                               microsecond=0)
            _cut = _et_mid.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            with self._db() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM trades WHERE strategy=? AND "
                    "entry_time >= ?", (strategy, _cut)).fetchone()
            return int(row[0] if row else 0)
        except Exception as exc:                                # noqa: BLE001
            logger.warning(f"count_today({strategy}) failed CLOSED: {exc}")
            return 1

    def log_entry(self, record: TradeRecord):
        """Insert a new open trade into the database."""
        record["entry_time"] = ts_for_db()
        record["status"]     = "open"
        record["lineage"]    = LINEAGE      # r140: the producer, stamped here and only here

        # ── TCS.4 (2026-08-17) — FILTER TO REAL COLUMNS, AND SAY SO ─────────
        # ⚠️ THIS FUNCTION CRASH-LOOPED A LIVE BOX. It INSERTed every key in the
        # record; `is_trend_credit` has no column, so the INSERT raised
        # OperationalError, the loop error counter hit its cap, the service shut
        # down, restarted, and did it again — every 15s for the rest of NFLX's
        # session on 2026-08-17.
        # A record key that is not a column is a BUG IN THE CALLER, but it must
        # not be able to take a trading box down. Unknown keys are dropped.
        # ⚠️ AND LOUDLY — ONCE PER KEY NAME. Silently dropping a field that was
        # SUPPOSED to persist would be the worse failure: that is Pattern 2, the
        # class that produced `is_trend_credit` in the first place. A drop is
        # visible or it is a new silent defect.
        cols         = [k for k in record.keys() if k in self._columns()]
        dropped      = [k for k in record.keys() if k not in self._columns()]
        for k in dropped:
            if k not in _WARNED_UNKNOWN_COLS:
                _WARNED_UNKNOWN_COLS.add(k)
                logger.warning(
                    "[schema] record key %r has NO COLUMN in `trades` and was "
                    "DROPPED from the insert. The trade is still logged. If this "
                    "field was meant to persist, ADD THE COLUMN - do not rely on "
                    "reading it back, it will be None on every restart.", k)
        values       = [record[k] for k in cols]
        placeholders = ", ".join(["?"] * len(cols))
        col_names    = ", ".join(cols)

        with self._db() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO trades ({col_names}) VALUES ({placeholders})",
                values
            )
        logger.info(f"Trade logged: {record.get('trade_id', '')[:8]} entry")

    def log_exit(self, trade_id: str, exit_price: float,
                  pnl_usd: float, exit_reason: str, excursion: Optional[dict] = None):
        """Update an open trade with exit details."""
        entry_prem = self._get_field(trade_id, "entry_premium") or 0
        # r198 (MEAS.1) — SIGNED BY THE OUTCOME, NOT BY THE PREMIUM'S DIRECTION. It was
        # (exit - entry) / entry for every trade, so a credit trade - where premium UP
        # is a LOSS - stored its losses as gains: 11 of 11 SweepCreditSpread rows
        # disagreed in sign with their own pnl_usd. pnl_usd arrives here already
        # direction-aware, so the sign is DERIVED from it (WA 22), never from
        # is_short_position (0 on every sweep row). SIGN ONLY: the magnitude is still
        # return on premium - for a credit spread that is return on CREDIT, not on risk.
        _mag       = abs(exit_price - entry_prem) / entry_prem if entry_prem > 0 else 0
        pnl_pct    = _mag if (pnl_usd or 0) >= 0 else -_mag

        with self._db() as conn:
            conn.execute("""
                UPDATE trades SET
                    status       = 'closed',
                    exit_premium = ?,
                    pnl_usd      = ?,
                    pnl_pct      = ?,
                    exit_reason  = ?,
                    exit_time    = ?,
                    -- v4.0: PERSIST THE EXCURSION. `_track_excursion` fills
                    -- these on the in-memory record every tick; without them
                    -- here they die at close and the book still cannot answer
                    -- "how long until a winner declared itself" - which is the
                    -- exact defect the columns were added to fix, reproduced
                    -- one layer down. COALESCE keeps any earlier value if the
                    -- caller passes nothing.
                    mfe_premium  = COALESCE(?, mfe_premium),
                    mfe_bars     = COALESCE(?, mfe_bars),
                    mae_premium  = COALESCE(?, mae_premium),
                    mae_bars     = COALESCE(?, mae_bars)
                WHERE trade_id = ?
            """, (exit_price, pnl_usd, pnl_pct,
                  exit_reason, ts_for_db(),
                  (excursion or {}).get("mfe_premium"),
                  (excursion or {}).get("mfe_bars"),
                  (excursion or {}).get("mae_premium"),
                  (excursion or {}).get("mae_bars"),
                  trade_id))
        logger.info(
            f"Trade closed: {trade_id[:8]} "
            f"exit=${exit_price:.2f} pnl=${pnl_usd:+.2f}"
        )

        # ── 🔴 r212 — THE PLAN THAT PRODUCED THIS TRADE IS NOW CLOSED ───────
        # Rows opened by `PlanTick.take()` were never closed by anything:
        # `transition()` had two callers, neither of which covered them, so
        # `closed_ts` stayed NULL and `live_plans()` returned every fired plan
        # for the rest of the session. QQQ 2026-09-01 showed SEVEN
        # `RunawayContinuation TRIGGERED` rows flagged LIVE while six of those
        # trades had closed hours earlier.
        # ⚠️ HOOKED HERE FOR THE SAME REASON r154's SPENT LOCK IS: `log_exit`
        # is the ONE choke point every close passes through. In the exit engine
        # it would miss the paths that close elsewhere, and a rule with a hole
        # in it is worse than none because it fires sometimes and is trusted
        # always.
        # ⚠️ NEVER RAISES. A bookkeeping failure must not stop a position being
        # booked closed.
        try:
            from derived.registry import plan_ledger as _pl212
            # ⚠️ THE SYMBOL COMES OFF THE ROW, the way every other hook in this
            # function gets it (`_sym = self._get_field(trade_id, "symbol")`
            # twenty lines below). A first cut called `self._instrument()`,
            # which does not exist on this class — §0.1, read the file rather
            # than assume the accessor.
            _sym212 = self._get_field(trade_id, "symbol") or ""
            _led212 = _pl212(_sym212) if _sym212 else None
            if _led212 is not None:
                _led212.close_for_trade(trade_id, exit_reason)
        except Exception as _exc212:                            # noqa: BLE001
            logger.debug("[plan] close_for_trade skipped: %s", _exc212)

        # ── 🔴 r154 — A LOSING SWEEP SPENDS ITS LEVEL FOR THE DAY ────────────
        # Operator, 2026-08-27: *"The stop isn't too tight, the level that we
        # just attempted a sweep on is finished."*
        # ⚠️ HOOKED HERE because `log_exit` is the ONE choke point every close
        # passes through. Putting it in the exit engine would miss the paths
        # that close elsewhere, and a lock with a hole in it is worse than none
        # — it would fire sometimes and be trusted always.
        # ⚠️ LOSSES ONLY. A level that PAID is not discredited by paying.
        try:
            _strat = self._get_field(trade_id, "strategy") or ""
            # 🔴 OTV4TEST r24 (DEC.1) — NOTHING IS REMEMBERED HERE ANY MORE. This hook
            # used to WRITE a finished runaway break and a spent sweep level into
            # per-process state. The runaway set was wiped by every restart
            # (2026-09-09 11:28: a spent break re-bought four seconds after a
            # bake), and the sweep write read `is_credit_vertical` — NOT A COLUMN
            # — so it raised on every close and never marked anything (2026-09-11
            # 12:04: a "SPENT" level sold again). The plans now READ both facts
            # from this very row (`break_last_exit`, `is_spent`), so the only job
            # left here is to say so in the log, where a person can see it.
            if "Runaway" in _strat:
                logger.info("[spent] runaway %s closed — its break is finished "
                            "(the plan reads it from trades.db)", trade_id[:8])
            elif ("Sweep" in _strat or "TrendCredit" in _strat):
                from strategy.sweep_credit_spread import is_breach_exit
                if is_breach_exit(exit_reason):
                    logger.info("[spent] %s %s closed (%s) — its level is SPENT for the day "
                                "(the plan reads it from trades.db)", _strat, trade_id[:8],
                                str(exit_reason or "")[:48])
        except Exception as exc:                               # noqa: BLE001
            logger.warning("[spent] could not report the spent state for %s: %s",
                           trade_id[:8], exc)

    def log_accretion(self, trade_id: str, contracts: int,
                      entry_premium: float, max_loss: float,
                      total_cost: float, stop_premium: float) -> None:
        """v4.11 — a later fill on the SAME credit structure joins the row.
        The caller (credit_remainder.accrete) does the blending and passes the
        five fields that follow from it; this method only persists them, so
        the arithmetic lives in one place and the DB never disagrees with the
        in-memory record. `entry_premium` here is the BLENDED credit."""
        with self._db() as conn:
            conn.execute(
                "UPDATE trades SET contracts=?, entry_premium=?, max_loss=?, "
                "total_cost=?, stop_premium=? WHERE trade_id=?",
                (int(contracts), float(entry_premium), float(max_loss),
                 float(total_cost), float(stop_premium), trade_id))
        logger.info("Trade accreted: %s now %d contracts @ blended %.4f",
                    trade_id[:8], int(contracts), float(entry_premium))

    def update_trail_stop(self, trade_id: str, new_trail: float):
        """v3.1 — persist the ratcheted trail SEPARATELY from stop_premium.
        stop_premium is the IMMUTABLE entry-time -25% floor; the old
        update_stop() overwrote it with the trail, which made the exit
        engine's floor checks fire at the trail level and label every
        trail-armed exit 'hard_stop_25pct'/'stop_hit' — poisoning exit_reason
        distributions. Recovery seeds the in-memory trail from this column."""
        with self._db() as conn:
            conn.execute(
                "UPDATE trades SET trail_stop=? WHERE trade_id=?",
                (new_trail, trade_id)
            )

    def update_current_premium(self, trade_id: str, premium: float,
                               ts: Optional[str] = None):
        """Update live mark price every tick — and the per-trade MFE/MAE
        telemetry: max/min premium ever seen while open, and (v3.9) WHEN each
        extreme was set. This is the evidence base for tuning every exit
        threshold (was the floor hit by trades that then recovered? how much
        did trails give back vs capture — and did the peak come early or at
        the exit?).
        SQLite scalar MAX/MIN keep it one write; COALESCE seeds on first tick.
        The _at columns use CASE on the PRE-UPDATE row, so they advance only
        when the extreme itself advances rather than on every re-confirming
        tick. SQLite evaluates all SET right-hand sides against the original
        row, so the CASE sees the old extreme even though the new one is
        assigned in the same statement.
        ts is injectable for tests; production passes None and gets ts_for_db()
        — the same UTC base as entry_time, never a local or ET clock."""
        stamp = ts or ts_for_db()
        with self._db() as conn:
            conn.execute(
                "UPDATE trades SET current_premium=?, "
                "max_premium_seen_at=CASE WHEN max_premium_seen IS NULL "
                "    OR ? > max_premium_seen THEN ? ELSE max_premium_seen_at END, "
                "min_premium_seen_at=CASE WHEN min_premium_seen IS NULL "
                "    OR ? < min_premium_seen THEN ? ELSE min_premium_seen_at END, "
                "max_premium_seen=MAX(COALESCE(max_premium_seen, ?), ?), "
                "min_premium_seen=MIN(COALESCE(min_premium_seen, ?), ?) "
                "WHERE trade_id=?",
                (premium,
                 premium, stamp,
                 premium, stamp,
                 premium, premium, premium, premium, trade_id)
            )

    def set_entry_snapshot(self, trade_id: str, payload: str) -> bool:
        """v3.10 — persist the entry-time snapshot JSON. Returns True only if a
        row was actually updated.

        It RETURNS rather than logs-and-swallows on purpose (item AU): a caller
        that cannot tell "wrote it" from "wrote nothing" produces a column of
        NULLs that reads exactly like a quiet session. rowcount is checked
        because a wrong trade_id is a silent no-op in SQLite, not an error.
        """
        if not trade_id or not payload:
            return False
        try:
            with self._db() as conn:
                cur = conn.execute(
                    "UPDATE trades SET entry_snapshot=? WHERE trade_id=?",
                    (payload, trade_id))
                return cur.rowcount > 0
        except Exception as exc:                             # noqa: BLE001
            logger.warning("entry_snapshot write failed for %s: %s: %s",
                           trade_id[:8], type(exc).__name__, exc)
            return False

    # ── v3.12 — contract telemetry ──────────────────────────────────────────
    def set_entry_contract(self, trade_id: str, c: dict) -> bool:
        """Persist the CONTRACT's own state at entry. Returns True on a write.

        `entry_delta` IS A SELECTOR OUTPUT, NOT A MARKET OBSERVATION — the
        strike chooser picked it. So "0.30-delta entries do worse" is partly a
        statement about the selector, not about the market, and any analysis
        that reads it must say so. Recorded here rather than discovered in three
        weeks.

        BID AND ASK, NOT MARK. Mark is already stored as `entry_premium`, and
        spot at entry as `underlying_entry` — both predate this. Adding them
        again would have created two names for one fact, which is how a report
        ends up silently reading the stale one. The BID/ASK PAIR is what is
        genuinely new: mark is the midpoint, fills are not, and the spread is
        the only thing that can turn the floor sweep's declared "ASSUMES: no
        slippage" into a measured quantity — and the basis for the
        paper-vs-live fill comparison once live trading starts.
        """
        if not trade_id or not isinstance(c, dict):
            return False
        cols = ("entry_delta", "entry_gamma", "entry_theta", "entry_iv",
                "entry_bid", "entry_ask", "chain_iv_rank")
        vals = [c.get(k) for k in cols]
        if all(v is None for v in vals):
            return False
        try:
            with self._db() as conn:
                cur = conn.execute(
                    "UPDATE trades SET "
                    + ", ".join(f"{k}=?" for k in cols)
                    + " WHERE trade_id=?", (*vals, trade_id))
                conn.commit()
                return cur.rowcount > 0
        except Exception as exc:                                 # noqa: BLE001
            # v3.13 — logged INLINE. The W.2 swallow census reads the HANDLER
            # BODY, so a bare `return False` here reads as a silent TIER-1
            # handler — and the 2026-08-05 census caught this one the morning
            # after the lesson was written down. The caller already warns once
            # per reason; this line exists so the census can see the handler is
            # not swallowing, and so a DB-level failure is distinguishable from
            # "the row was not there".
            logger.debug("set_entry_contract failed (%s: %s) for %s",
                         type(exc).__name__, exc, trade_id[:8])
            return False

    def set_exit_contract(self, trade_id: str, c: dict) -> bool:
        """Persist the contract's state at the CONFIRMED close.

        `exit_iv` beside `entry_iv` is the IV-crush measurement — the most
        likely explanation for the 10:00-11:00 phase being the worst on the
        board, and currently indistinguishable from being wrong on direction.
        """
        if not trade_id or not isinstance(c, dict):
            return False
        cols = ("exit_bid", "exit_ask", "exit_iv")
        vals = [c.get(k) for k in cols]
        if all(v is None for v in vals):
            return False
        try:
            with self._db() as conn:
                cur = conn.execute(
                    "UPDATE trades SET "
                    + ", ".join(f"{k}=?" for k in cols)
                    + " WHERE trade_id=?", (*vals, trade_id))
                conn.commit()
                return cur.rowcount > 0
        except Exception as exc:                                 # noqa: BLE001
            # v3.13 — inline, same reason as set_entry_contract above.
            logger.debug("set_exit_contract failed (%s: %s) for %s",
                         type(exc).__name__, exc, trade_id[:8])
            return False

    def set_exit_latency(self, trade_id: str, submit_ts: str, fill_ts: str,
                         latency_ms: int, ladder_steps: int,
                         escalated: bool, mark_at_trigger=None) -> bool:
        """v3.11 (N.5) — persist the exit ladder's latency telemetry.

        Returns True only if a row was actually updated, for the same reason
        set_entry_snapshot does (item AU): a silent no-op UPDATE would leave a
        column of NULLs that reads exactly like a session with no exits.

        Called ONLY on a confirmed close. An unconfirmed close deliberately
        writes nothing — a close that never filled has no fill instant, and a
        fabricated one would land a zero-latency row inside the very population
        the stop-trigger decision is measured on.
        """
        if not trade_id or not submit_ts or not fill_ts:
            return False
        try:
            with self._db() as conn:
                cur = conn.execute(
                    "UPDATE trades SET exit_submit_ts=?, exit_fill_ts=?, "
                    "exit_latency_ms=?, exit_ladder_steps=?, exit_escalated=?, "
                    "exit_mark_at_trigger=? WHERE trade_id=?",
                    (submit_ts, fill_ts, int(latency_ms), int(ladder_steps),
                     1 if escalated else 0,
                     None if mark_at_trigger is None else float(mark_at_trigger),
                     trade_id))
                return cur.rowcount > 0
        except Exception as exc:                             # noqa: BLE001
            logger.warning("exit_latency write failed for %s: %s: %s",
                           trade_id[:8], type(exc).__name__, exc)
            return False

    def update_fields(self, trade_id: str, **fields):
        """Generic field updater (used by the broken-wing roll to flag legs)."""
        if not fields:
            return
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [trade_id]
        with self._db() as conn:
            conn.execute(f"UPDATE trades SET {sets} WHERE trade_id=?", vals)

    def get_open_trade(self) -> Optional[TradeRecord]:
        """Return the single open trade if any."""
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM trades WHERE status='open' "
                "AND COALESCE(paper_trade,1)=? ORDER BY entry_time DESC LIMIT 1",
                (self._mode_flag,)
            ).fetchone()
        if row:
            return make_record(**dict(row))
        return None

    def get_open_trades(self) -> List[TradeRecord]:
        """Return ALL open trades (oldest first). Supports concurrent condor
        legs; every other strategy holds at most one at a time."""
        with self._db() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status='open' "
                "AND COALESCE(paper_trade,1)=? ORDER BY entry_time ASC",
                (self._mode_flag,)
            ).fetchall()
        return [make_record(**dict(r)) for r in rows]

    def orb_entry_since(self, since_ts: str) -> Optional[TradeRecord]:
        """r103 — did an ORB trade actually OPEN at or after `since_ts` today?

        🔴 THE QUESTION THE MISSED ROW COULD NOT ANSWER. Operator, 2026-08-24:
        "figure out if it fired or if we genuinely missed it before closing out
        the row." The tape reach-back sees a confirmed break+retest and calls it
        MISSED — but the tape cannot tell a setup the PROCESS never saw from one
        it saw, took, and recorded before it died. The trades table can: if a
        row exists for this session at or after the confirming bar, the trigger
        FIRED and calling it missed is a false negative in the one population
        that is supposed to be countable.

        Returns the record if found, else None. Fails toward None — an
        unreadable DB reports nothing rather than inventing a fill.
        """
        try:
            with self._db() as conn:
                row = conn.execute(
                    "SELECT * FROM trades WHERE strategy='ORBStrategy' "
                    "AND COALESCE(paper_trade,1)=? AND entry_time >= ? "
                    "ORDER BY entry_time ASC LIMIT 1",
                    (self._mode_flag, since_ts)
                ).fetchone()
            return make_record(**dict(row)) if row else None
        except Exception as exc:                               # noqa: BLE001
            logger.debug("orb_entry_since lookup failed: %s", exc)
            return None

    def get_open_trades_today(self) -> List[TradeRecord]:
        """Deprecated alias — retained for safety. Prefer get_open_trades_live().
        A 0DTE bot that also trades weeklies can hold a position across sessions
        (expiry days out), so 'entered today' is the WRONG liveness test; use
        expiry instead."""
        return self.get_open_trades_live()

    @staticmethod
    def _expiry_date(expiry) -> str:
        """Normalize a stored expiry to 'YYYY-MM-DD'. Entries store this format
        already; tolerate a stray full timestamp. Returns '' if unknown."""
        if not expiry:
            return ""
        s = str(expiry).strip()
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            return s[:10]
        try:
            return datetime.fromisoformat(s).strftime("%Y-%m-%d")
        except Exception:
            return ""

    def get_open_trades_live(self) -> List[TradeRecord]:
        """Open rows that have NOT expired — expiry today or later (0DTE AND
        weeklies), plus any row whose expiry is unknown (kept deliberately: never
        abandon a possibly-live position). These are what startup recovery
        resumes managing."""
        today_et = now_et().strftime("%Y-%m-%d")
        out = []
        for r in self.get_open_trades():
            exp = self._expiry_date(r.get("expiry", ""))
            if exp == "" or exp >= today_et:
                out.append(r)
        return out

    def close_expired_open_trades(
        self, exit_reason: str = "expired_orphan_autoclosed", settle=None
    ) -> List[TradeRecord]:
        """Reconcile TRULY EXPIRED orphans only: any status='open' row whose
        expiry date has passed (expiry < today ET). A weekly still in its life is
        left ALONE — its expiry is in the future. Rows with an unknown expiry are
        also left open (never guess a live position dead). Each closed row gets
        status='closed', an explicit exit_reason, exit_time now, and pnl_usd
        forced to 0.0 (true settlement is unknowable — flag for manual review) so
        it leaves 'open' and is never 'recovered' again. Returns the rows closed
        (for alerting)."""
        today_et = now_et().strftime("%Y-%m-%d")
        with self._db() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status='open' "
                "AND COALESCE(paper_trade,1)=?", (self._mode_flag,)
            ).fetchall()
            expired = []
            for r in rows:
                exp = self._expiry_date(r["expiry"])
                if exp != "" and exp < today_et:
                    expired.append(make_record(**dict(r)))
            # r165 (EXP.1): price what can be priced at its settlement value.
            settled = {}
            if settle is not None:
                for r in expired:
                    try:
                        got = settle(r)
                    except Exception as exc:                   # noqa: BLE001
                        logger.warning("expiry settlement failed for %s: %s - flagged 0.0",
                                       str(r.get("trade_id", ""))[:8], exc)
                        got = None
                    if got is not None:
                        settled[r["trade_id"]] = got
                for tid, (px, pnl, label) in settled.items():
                    conn.execute(
                        "UPDATE trades SET status='closed', exit_reason=?, exit_time=?, "
                        "exit_premium=?, pnl_usd=? WHERE trade_id=?",
                        (f"{exit_reason}_{label}", ts_for_db(), px, float(pnl), tid))
                    logger.warning(f"Settled EXPIRED {tid[:8]} — {label} @ {px} pnl=${pnl:+.2f}")
            unsettled = [r for r in expired if r["trade_id"] not in settled]
            if unsettled:
                ids = [r["trade_id"] for r in unsettled]
                placeholders = ",".join("?" * len(ids))
                conn.execute(
                    f"UPDATE trades SET status='closed', "
                    f"exit_reason=?, exit_time=?, "
                    f"pnl_usd=COALESCE(pnl_usd, 0.0) "
                    f"WHERE trade_id IN ({placeholders})",
                    [exit_reason, ts_for_db(), *ids]
                )
        for r in expired:
            logger.warning(
                f"Auto-closed EXPIRED orphan {r.get('trade_id','')[:8]} "
                f"(expiry {self._expiry_date(r.get('expiry',''))}, "
                f"{str(r.get('option_side','')).upper()} {r.get('strike',0)}) "
                f"— {exit_reason}"
            )
        return expired

    def close_phantom(self, trade_id: str,
                      reason: str = "phantom_closed_at_broker",
                      exit_price: float = None,
                      pnl_usd: float = None) -> None:
        """Close a DB row the broker no longer shows open. On LIVE, the broker is
        the source of truth for existence: if a row is open in our DB but absent
        at the broker, it has closed there (or never truly filled) and we must
        stop 'managing' it.

        v3.6: when the caller RECOVERED the real close from broker order history
        (see broker_reconcile.match_closing_fills), pass exit_price + pnl_usd and
        the row books the TRUTH — realized P&L the DAILY_LOSS_LIMIT breaker can
        trust. Without them, pnl_usd is forced to 0.0 (the real fill is unknown —
        flag for review) with an explicit reason, as before."""
        with self._db() as conn:
            if pnl_usd is not None:
                conn.execute(
                    "UPDATE trades SET status='closed', exit_reason=?, exit_time=?, "
                    "exit_premium=?, pnl_usd=? WHERE trade_id=?",
                    (reason, ts_for_db(), exit_price, float(pnl_usd), trade_id),
                )
                logger.warning(
                    f"Closed phantom {trade_id[:8]} — {reason} "
                    f"(RECOVERED fill @ {exit_price} pnl=${pnl_usd:+.2f})"
                )
                return
            conn.execute(
                "UPDATE trades SET status='closed', exit_reason=?, exit_time=?, "
                "pnl_usd=COALESCE(pnl_usd, 0.0) WHERE trade_id=?",
                (reason, ts_for_db(), trade_id),
            )
        logger.warning(f"Closed phantom {trade_id[:8]} — {reason} (fill unknown, pnl=0.0 FLAGGED)")

    def get_session_losses(self) -> int:
        today = now_utc().strftime("%Y-%m-%d")
        with self._db() as conn:
            row = conn.execute("""
                SELECT COUNT(*) as n FROM trades
                WHERE status='closed'
                AND pnl_usd < 0
                AND date(entry_time) = ?
                AND COALESCE(paper_trade,1) = ?
            """, (today, self._mode_flag)).fetchone()
        return row["n"] if row else 0

    def get_consecutive_losses(self) -> int:
        with self._db() as conn:
            rows = conn.execute("""
                SELECT pnl_usd FROM trades
                WHERE status='closed'
                AND COALESCE(paper_trade,1) = ?
                ORDER BY exit_time DESC
                LIMIT 10
            """, (self._mode_flag,)).fetchall()
        count = 0
        for row in rows:
            if row["pnl_usd"] < 0:
                count += 1
            else:
                break
        return count

    def log_circuit_breaker(self, reason: str, session_losses: int, notes: str = ""):
        with self._db() as conn:
            conn.execute("""
                INSERT INTO circuit_breaker_events
                (event_time, reason, session_losses, notes)
                VALUES (?, ?, ?, ?)
            """, (ts_for_db(), reason, session_losses, notes))

    def _get_field(self, trade_id: str, field: str):
        with self._db() as conn:
            row = conn.execute(
                f"SELECT {field} FROM trades WHERE trade_id=?", (trade_id,)
            ).fetchone()
        return row[field] if row else None

    # ── DEFINITIVE closed-P&L accounting ──────────────────────────────────────
    # Single source of truth for realized (closed) P&L. Every consumer — the
    # daily-loss circuit breaker, status.py, query.py, EOD — references THESE
    # methods, never an in-memory copy and never a parallel re-sum. That is what
    # lets any bot reference its definitive day P&L immediately and survive any
    # restart: the number lives in trades.db, not in process memory.
    @staticmethod
    def _et_date(iso_ts: str) -> str:
        """ET calendar date ('YYYY-MM-DD') for a stored UTC ISO timestamp.
        Bucketing by ET (not UTC) so a late-session trade never lands on the
        wrong day."""
        try:
            dt = datetime.fromisoformat(iso_ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(ET).strftime("%Y-%m-%d")
        except Exception:
            return ""

    def _closed_today_rows(self) -> List[sqlite3.Row]:
        """Closed trades whose ET session date is today. Coarse UTC prefilter
        keeps the scan tiny; the exact match is done by ET date in Python."""
        today_et = now_et().strftime("%Y-%m-%d")
        lower = (now_utc() - timedelta(days=1)).strftime("%Y-%m-%d")
        with self._db() as conn:
            rows = conn.execute("""
                SELECT * FROM trades
                WHERE status='closed' AND pnl_usd IS NOT NULL
                AND date(entry_time) >= ?
                AND COALESCE(paper_trade,1) = ?
            """, (lower, self._mode_flag)).fetchall()
        return [r for r in rows if self._et_date(r["entry_time"]) == today_et]

    def realized_pnl_today(self, exclude_strategies=()) -> float:
        """DEFINITIVE realized net closed P&L for today's ET session (wins
        offset losses). This is the number the daily loss limit gates on.
        r288: `exclude_strategies` drops those strategies' rows - the cap passes
        config.CAP_EXCLUDED_STRATEGIES; every other caller passes nothing."""
        ex = set(exclude_strategies or ())

        def _strategy(r):                 # a row without the column (a fixture) is never excluded
            try:
                return r["strategy"]
            except (KeyError, IndexError):
                return None
        return float(sum((r["pnl_usd"] or 0.0) for r in self._closed_today_rows()
                         if not ex or _strategy(r) not in ex))

    def today_summary(self) -> dict:
        """Counts + net P&L for today's ET session, EVERY strategy - the displays' figure.
        r298: NOT the circuit breaker's number since r288: the cap reads
        realized_pnl_today(exclude_strategies=config.CAP_EXCLUDED_STRATEGIES), which
        leaves PARK out; the two differ by PARK's P&L on a day PARK traded, by design
        (TRADES §9). This docstring said "identical" for ten days after that stopped
        being true (audit 2026-10-18 T3-10)."""
        rows = self._closed_today_rows()
        wins   = sum(1 for r in rows if (r["pnl_usd"] or 0) > 0)
        losses = sum(1 for r in rows if (r["pnl_usd"] or 0) < 0)
        total_pnl = float(sum((r["pnl_usd"] or 0.0) for r in rows))
        return {"total": len(rows), "wins": wins, "losses": losses,
                "total_pnl": total_pnl}


_trade_logger: Optional[TradeLogger] = None


def get_trade_logger() -> TradeLogger:
    global _trade_logger
    if _trade_logger is None:
        _trade_logger = TradeLogger()
    return _trade_logger
