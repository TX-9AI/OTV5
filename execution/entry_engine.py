"""
execution/entry_engine.py  v5.11
v5.11 2026-11-22  OTV5 r151 (CAP.11) — _book_fill writes after_cap = 1 on a PAPER entry (this engine's paper_trading True, not the walled PaperWallEntry) when risk_manager.after_cap_tag() says the daily catastrophic cap, counted as cash would count it, stands tripped: on a paper box the cap is record only (the operator, 2026-11-22: "there's no harm in letting paper run & we can just note if the breaker would have popped"), so paper keeps trading and the row says cash would not have opened it. Nothing else in the record changes; an untagged row carries no after_cap key at all (NULL), so every entry before a would-be trip is the r150 row. A live entry and a walled entry never read it. Never raises (a failed read leaves the row untagged).
v5.10  2026-11-22  OTV5 r150 (OGAP.5) — _book_fill skips the cap counterfactual (risk_manager.note_entry_risk, a study of
      the CASH cap) when the engine is execution/paper_wall's PaperWallEntry (PAPER_WALL True: OGAP on a live box, booked
      paper at the mark). Read as getattr(self, "PAPER_WALL", False) is True, so this engine and any stand-in behave as
      before; every paper and live entry books exactly as at r149.
v5.9  2026-11-22  OTV5 r146 (BLND.1, partial) — enter() refuses an opening order while utils/blind_reacquire holds (after a blind episode: the tick that first sees again, and until main.attempt_new_entry has had one full tick with sight on current 1m bars), after the entries_open gate, before any broker call: one "[entry-gate] ... HELD - reacquiring ..." line, None returned. With no blind episode the hold is '' and enter() is unchanged. No broker call, no config key. Gate tests/check_blind_reacquire.py.
v5.8  2026-11-21  OTV5 r136 (OGAP.3) — freeze_contract no longer re-stamps signal.ogap_ask: OGAP carries none (it sizes and exits on the mark, entry_premium, which the freeze already re-reads). The operator, 2026-11-20: "never pay the spread". Nothing else changes.
v5.7  2026-11-20  OTV5 r135 (GUARD.1; the live-readiness audit 2026-11-20 C3 + I3, live only) — A SUSPECT ENTRY ORDER IS
      BOOKED AS ITS OWN STRATEGY'S TRADE. enter()'s record-building tail moves, unchanged, into _book_fill (the one place a
      confirmed entry fill becomes a row), and _place_single_leg hands order_guard a booking (_suspect_booking: the
      single-leg basis and a closure over the firing signal) at each of its three suspect sites: the unconfirmed cancel
      or unreadable fills (after_failure), an error after placement (after_failure) and a lost reply (after_lost_post).
      When the guard reads that order's fill (whole, or a partial left by an unconfirmed cancel), the closure ends the
      walk and its pin and books it through _book_fill at the broker's fills, notes "entry fill confirmed by the order
      guard after the walk". While any suspect exists the guard refuses every opening post on the instrument, so a
      re-picked strike no longer posts beside it. The ladder, the walk loop, exits and paper are unchanged.
v5.6  2026-11-20  OTV5 r133 (D2 + D3; the forward-edge study 2026-11-20) — THE LIVE ENTRY WALK POSTS ITS NEXT RUNG AS SOON AS
      THE LAST ONE IS READ DEAD, NOT ON THE NEXT 15 s TICK, AND THE CONTRACT IS FROZEN FOR THE WALK'S LIFE. At r132 each rung
      rested ~5 s (_rung_deadline) and nothing was working for ~10 s until the next tick. _place_single_leg now loops, live
      only: rest (confirm_order_fill, 2 s polls, unchanged) -> cancel and read dead (the same call) -> refuse -> re-read the
      STREAMED quote (chain_marks via OptionsChainFetcher._read_marks, no broker call) -> next_price on the same LadderState
      and key -> post. It stops on a fill (a fill in the cancel race included, booked once), the mark rung refused (the
      terminal rung, which the next tick re-offers as before), a rejection, the strategy's window ending
      (config.ENTRY_WINDOWS; the walk is cleared), no fresh quote, an unconfirmed cancel (now held by order_guard
      .after_failure, so the next tick cannot post beside it), or one tick's budget (POLL_INTERVAL_SECONDS: no rung starts
      whose rest would end past it). Cancel-confirm-post, never replace. D3: module freeze_contract(), called by main
      before sizing, puts a signal that re-picked its strike back on the contract its walk is on (_PINS, per strategy /
      side / direction, idle after PIN_IDLE_S = 45 s). The ladder's rules (25% start, ratchet, mark cap after it, never
      worse than mark, the underlying's grid) are entry_ladder's, untouched; paper unchanged; exits untouched. In memory:
      a restart loses the ratchet and the pin; the boot sweep still cancels a working rung. Gate tests/check_entry_ladder_5s.py.
v5.5  2026-11-20  OTV5 r132 (TICK.3; the forward-edge study 2026-11-20, D1) — THE ENTRY LADDER'S TICK GRID IS LOOKED UP
      UNDER THE UNDERLYING (INSTRUMENT), AS EXITS DO, NOT UNDER THE OCC SYMBOL. _place_single_leg passed
      signal.contract.symbol to _walk_price -> ladder_registry.price_for -> entry_ladder._increment -> tick_size.resolve,
      and the venue rule is cached under the underlying (PENNY_CLASSES lists underlyings), so every live entry missed and
      priced on the non-penny grid: QQQ bid 3.40 / ask 3.50 walked [3.40] instead of [3.42, 3.43, 3.44, 3.45]. Only the
      grid symbol changes; the walk key (intent_key on the contract), the 25% start, the ratchet, the mark cap and the
      rounding in our favour are untouched. Paper unchanged (books the mark). Gate tests/check_entry_tick_grid.py.
v5.4  2026-11-16  OTV5 r127 (LOP.1, FA.1; the cold audit 2026-11-15, critical) — A single-leg place_order THAT RAISES now
      registers the intent with order_guard.after_lost_post (the order may be live at the broker with no id here), so the
      next tick cancels or blocks on what the broker's book shows instead of posting the next rung beside it. Before,
      the except ran after_failure only when a response had come back (_placed), and a lost reply left nothing behind.
      Live only (paper returns before this code). Gate tests/check_lost_post.py.
v5.3  2026-11-14  OTV5 r118 (HYG.23) — DOCSTRING ONLY: _record_kwargs no longer describes the standing-offer supervisor as a
      second caller (removed r76; its store and supervisor deleted r118). AST identical to r117.
v5.2  2026-11-11  OTV5 r107 (RETIRE.5 follow-up) — THE GENERIC BUTTERFLY ENTRY GOES with the fly strategy removed at r103: the enter() butterfly branch, the fly record fields (lower/center/upper strike and symbol, net_debit, max_profit), _place_butterfly, _paper_fill_butterfly and the fly-only _mark_cap. No live strategy emits a butterfly signal since r103; every entry takes the single-leg path, unchanged. The trades schema keeps its fly columns (history). The operator, 2026-11-07: "Running dead code and logging dead code activity is unnecessary drag."
v5.1  2026-11-08  OTV5 r76 (RETIRE.1) — THE ORB STANDING OFFER IS REMOVED with the ORB trade: _is_standing_offer, _place_standing_offer, _record_offer, _mark_orb_confirmation_spent, _session_date and the ORB latch after _place_single_leg. Every live single-leg entry already took the default path (paper fill / the ladder), unchanged. The operator, 2026-11-07: "Running dead code and logging dead code activity is unnecessary drag. Yes, I want all of those things fixed."
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.16 2026-10-14  OTV4TEST r283 (LIVE.1 F5, MIRROR OF otv4 r473 bfb0991, WA 38.2) — every live entry checks
      buying power before it posts (execution/buying_power.affordable, right after B2's clear_to_post):
      single leg at its limit, the standing ORB offer at its price, the butterfly at its mark cap, each
      x contracts x 100. Short or unreadable -> not posted. Code hunks verbatim from bfb0991. Paper unchanged.
v4.15 2026-10-04  OTV4TEST r244 (LIVE.1 B2, MIRROR OF otv4 r466 579354d, WA 38.2) — AN ERROR AFTER place_order NO LONGER FORGETS THE ORDER: execution/order_guard (after_failure cancels, records the order as suspect and pages; clear_to_post blocks the intent until the broker says CANCELLED/EXPIRED/REMOVED/PARTIALLY_REMOVED/REJECTED, pages once on FILLED, blocks when unreadable); the failed rung is refused. Code hunks applied verbatim; ONE hunk hand-placed: the butterfly guard sits after _fly_key and before this tree's r224 FLY.1 cap block (mainline's butterfly lines differ).
v4.14 2026-10-04  OTV4TEST r242 (LIVE.1 B0, MIRROR OF otv4 r463 c912ce7, WA 38.2) — every Account call goes through tasty_client.sdk_result: on tastytrade 13.x the Account methods are coroutines and a bare call placed and closed NOTHING live (paper never calls them). Hunks applied verbatim from c912ce7.
v4.13 2026-10-03  OTV4TEST r224 (FLY.1) — A BUTTERFLY ENTRY NEVER POSTS ABOVE ITS MARK. The operator, 2026-10-03: "They should still
      not exceed mark on ladder entries, even no bid quotes" and "We won't accept a disadvantaged entry just
      because there is low interest". Two live paths could: (1) the retry was posted at mid + LIMIT_IMPROVE_TICKS
      (one cent over, by design since v3.7); (2) the walk is priced on the structure's quote with its bid
      floored at zero, so when the true structure bid is negative (wide legs, no-bid wings) the ladder's own
      midpoint sits above the true mark. Now every attempt is capped at the mark (net_debit, floored to the
      cent), the retry re-posts at the cap, and a mark under one cent posts nothing. Paper is unchanged (it
      books the mark). Single-leg entries were measured: the ladder never passes the mark, bid or no bid.
v4.12 2026-10-03  OTV4TEST r210 (AUD.9) — the paper standing offer records the price it filled at (resting_orders.fill_price
      was 0 on every row: 16 of 16). One call beside close_out; nothing else moves.
v4.11 2026-10-03  OTV4TEST r208 (CAP.4) — after log_entry the record is handed to risk_manager.note_entry_risk: one
      log-only cap-counterfactual row per entry. Wrapped; it cannot affect the entry.
v4.10 2026-09-13  OTV4TEST r17 — PRE.1: `_record_kwargs` writes `option_symbol` from
      the signal's contract. The shared factory never has; 19 of 21 rows on this
      box carry NULL and no premium-path study can join them. Same one-line fix
      as mainline r340, in the same ONE LINEAGE factory, so both paths get it.
v4.9  2026-09-10  OTV4TEST r12 — the record carries `is_liquidity_hunt` (the slot rule
      reads the row, like `is_butterfly`).
v4.8  2026-09-04  r240 — 🔴 THE ORB BOUNDS ARE WRITTEN BY CAPABILITY,
      NOT BY NAME — rebuilding r226, which was cut on 2026-09-03 and NEVER
      LANDED (no commit on any branch; its BACKLOG entry reached git only
      because the backlog ships in every archive and r227 carried it).
      This read `if signal.is_orb`, literally `strategy_name == "ORBStrategy"`.
      The RUNAWAY populates `orb_range_high/low` too — it is a continuation of
      the same break — and the name check discarded them on every runaway fill.
      🔑 MEASURED: `calibrate_trend_strength` reported "no ORB boundary on the
      row : 182" — ALL 182 runaway trades unmeasurable, on the largest strategy
      in the book by count and by net. It blocks MOM.1 Stage 1, which r225
      filed as the stage every other stage anchors on.
      ⚠️ AND IT IS WHY THE STRUCTURE STOP LOOKS ABSENT ON THE RUNAWAY:
      `exit_engine`'s structure stop needs a bound on the record and skips
      silently without one, so ORB.7's "the -25% floor fires first" is, for the
      runaway, "the structure stop had nothing to fire against."
      ⚠️ BOTH BOUNDS REQUIRED, never one — a single bound is not geometry.
      ⚠️ r235's CONFIRMATION LATCH STILL KEYS ON `is_orb`, deliberately: only
      the ORB engine has a confirmation to spend, so that one IS an identity
      question. B3 pins it, because removing `is_orb` wholesale would have
      broken the fix that stopped one retest firing three orders.
v4.7  2026-09-04  r235 — 🔴 THE ORB LATCH WAS ONLY EVER SET ON THE
      STANDING-OFFER PATH. r207 installed `_mark_orb_confirmation_spent()`
      inside `_place_standing_offer` and its note says the latch is "a property
      of the CONFIRMATION, so it is mode-independent" — true of the FLAG, false
      of the CALL SITE. `_place_single_leg` is the DEFAULT placer and never
      called it, so `order_placed` stayed False for the life of the session,
      the engine sat in OPEN_* after the retest, and BOTH fire gates passed on
      every tick. C.40 A THIRD TIME: r195's `_orb_offer_working()` read a table
      paper never writes; this read a call site only one of two paths runs.
      Keyed on `order_id` (the placement) and `signal.is_orb`, matching r207's
      own rule that a placed-but-unfilled order still spends the confirmation.
v4.6  2026-09-01  r207 — PAPER GOES THROUGH THE SAME DOOR, AND THE
      CONFIRMATION IS SPENT AT PLACEMENT. `_place_single_leg` tested
      `self.paper_trading` ABOVE `_is_standing_offer`, so on a paper box the
      whole of r195 was unreachable: no offer was ever placed, no row was ever
      written, and `_orb_offer_working()` — the guard r195 installed when it
      removed `mark_triggered()` from the ORB dispatch — returned False on
      every tick of every session. Paper ran pre-r195 behaviour behind a green
      board, and on 2026-09-01 QQQ took two ORB shorts off one confirmation.
      ORB is now tested FIRST and reaches `_place_standing_offer` in both
      modes; paper records the offer, fills it WHOLE at the mark and closes it
      out FILLED, per the operator: "on a live order it places the number of
      contracts as a limit order at mark and in paper mode, they ALL fill."
      🔑 AND THE LATCH IS SET AT PLACEMENT, NOT AT FILL, because a live offer
      that has not filled is still an order against that confirmation — and
      because `enter()` returns None for BOTH a working offer and a sizing
      refusal, so main.py cannot tell them apart and this is the only site
      that can. `_record_offer` is shared by both modes so the frozen row
      cannot describe two different things.
v4.5  2026-08-30  r195 — ORB LEAVES THE LADDER AND POSTS A STANDING OFFER.
      Backlog ORB.2. One DAY limit at the mark for the geometry count, posted
      ONCE on the tick the setup fires, never re-priced. Every other strategy
      keeps the r104 walk untouched.
      🔑 WHY ONLY ORB. The ladder exists because of FRC.1 — gross edge
      +$2.70/trade against $126/trade of round-trip friction, so half the
      half-spread is worth ~$31/trade. Right for the credit spreads, the
      butterfly and the runaway. Wrong for ORB, because the walk buys that $31
      by SPENDING TICKS and a missed retest window costs the whole setup.
      Operator, verbatim: "I don't want to blow an entry trying to save $25 by
      dicking around over pennies." The edge is in being IN the break.
      🔴 THIS IS NOT "LET THE ORDER SIT" RESTORED. Before r195 an ORB entry
      posted ONE RUNG PER TICK on a ~5s per-rung deadline, was cancelled, and
      re-signalled next tick against a fresh quote — an active walk. The v3.8
      note below still describes the PRE-LADDER behaviour r104 superseded; it
      is history, not current, and reading it as current made me under-size
      this change once already.
      ⚠️ NO RECORD IS BORN HERE. A resting offer returns filled_qty=0 and
      enter() records NOTHING — the anti-orphan invariant is untouched. The
      position is created later by the supervisor from the BROKER's positions,
      the only thing the operator allows to declare an open trade.
v4.4  2026-08-24  r104 THE LADDER IS WIRED FOR ENTRIES. entry_ladder.py has
      been complete and UNCALLED since 2026-08-20 while every live fill posted a
      single limit at mark — by FRC.1 that is ~$31/trade given away against a
      +$2.70 gross edge. Single-leg and butterfly entries now post ONE RUNG per
      tick through ladder_registry (25% in from best, one venue increment toward
      mark, ratcheted, never worse than mark), with the walk keyed to the intent
      so the next tick resumes it. A refusal advances the rung; a fill clears
      the walk. Paper is untouched — limit_ladder stays the one paper authority.
v4.3  2026-08-24  r101: enter() refuses before ENTRY_OPEN_ET — the debit choke
      point for the 09:35 gate (single leg and butterfly). No broker call, no
      record; the strategy re-signals next tick.
v4.2  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Entry dispatch and slot assignment.

v4.1  2026-08-20  AUDIT F4: relaxed_entry copied signal -> record. Without it
      the column was DEFAULT 0 on every row while the schema claimed the
      relaxed population was separable.
v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

execution/entry_engine.py — Options order placement via TastyTrade SDK.
DOC TRUTH + shared paper authority (audit defect T).
        v3.8 said paper "books the MARK", which was true only because the
        knob was being ignored here while condor legs still applied it. Paper
        debit fills still route through limit_ladder.paper_fill_price — no
        call-site change — but that helper (v1.3) now honours
        PAPER_FILL_SLIPPAGE_PCT for every path uniformly, default 0.0 = the
        mark. So the v3.8 behaviour is the DEFAULT, not a hardcode, and the
        knob is a fleet-wide stress lever again.
MARK-LIMIT ENTRIES. Single-leg entry was a MARKET order
        (paid the ask while the signal was scored on the mark). It now posts a
        LIMIT at the mark and lets it sit; unfilled orders are cancelled by
        confirm_order_fill and the strategy re-signals next tick against a
        fresh mark. Paper fills book the MARK for both single-leg and
        butterfly (was mark * (1 + PAPER_FILL_SLIPPAGE_PCT)) so paper and live
        trade on the same principle — the residual gap is no-fill risk, not
        slippage.
ENTRY FILL-CONFIRMATION (audit defect O, parts 2+3).
        Records are written ONLY for broker-confirmed fills at the broker's
        actual fill price, for the quantity that actually filled — never on
        submission, never at the signal mark, never at our limit.
        SINGLE LEG: still a MARKET order, but the fill price is now READ BACK
        from the order's fills via order_confirm (the old code booked
        `placed.price or signal.entry_premium` — a market order has no
        .price, so live entries were ALWAYS recorded at the signal mark).
        BUTTERFLY: rebuilt. (a) debit priced NEGATIVE per the SDK's signed
        convention (the old positive price demanded a CREDIT to open a debit
        fly — could never fill; price_effect is ignored by current SDKs and
        is gone); (b) fill detection is a bounded poll via
        confirm_order_fill, not an instant status peek (which always saw
        Received/Routed and churned place→cancel→place); (c) the
        double-position race is closed: a second attempt is placed ONLY after
        the first is confirmed dead with zero fills — an uncancellable order
        stops the ladder, pages, and is adopted by reconcile if it fills;
        (d) a PARTIAL fill is booked at its weighted net for the filled size.
        Butterfly records now persist lower/center/upper leg SYMBOLS —
        without them the v3.5 live close and reconcile leg-matching both fail.
        enter() sizes the record from the CONFIRMED quantity. Paper is
        unchanged in shape (fills at mark ± PAPER_FILL_SLIPPAGE_PCT in one
        pass) and returns the requested quantity — mirroring live as closely
        as a simulator without a book can.
v3.0 — original release
store orb_range_high/low in TradeRecord so exit_engine
        can detect ORB range violations on 1-min candle closes
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
Order types:
  - Single-leg (ORB, SweepReversal): MARKET order, fill price read back from
    the broker's fills (bounded confirmation poll).
Paper mode: books limit_ladder.paper_fill_price (the mark by default;
mark ± PAPER_FILL_SLIPPAGE_PCT when the stress knob is set). No real order.
"""
# v-obs2 (2026-07-24) — entry record now also stores swept_level_name + level_strength.



import copy
import logging
import time
import uuid
from decimal import Decimal
from typing import Optional, Tuple

from tastytrade.order import (
    NewOrder, Leg, OrderAction, OrderType, OrderTimeInForce,
    InstrumentType
)

from execution.order_confirm import confirm_order_fill
from execution.limit_ladder import limit_at_mark, paper_fill_price

from strategy.base_strategy import OptionsSignal
# ⚠️ r152 — the setup scorer is REMOVED. `score` is accepted as None so the
# call shape is unchanged for any caller not yet updated; the trade record
# keeps its setup_grade/setup_score columns and writes the constants below.
from risk.risk_manager import SizingResult
from database.trade_logger import TradeRecord, make_record, get_trade_logger
from data.tasty_client import get_session, get_account, TastyClientError, sdk_result
from execution import order_guard as _guard                          # B2
from execution import buying_power as _bp                            # F5
from config import (
    PAPER_TRADING, PAPER_FILL_SLIPPAGE_PCT,
    CONTRACT_MULTIPLIER, INSTRUMENT,
    LIMIT_IMPROVE_TICKS
)
from utils.time_utils import ts_for_db, fmt_et_short, entries_open, now_et
from utils.heartbeat import touch as _hb_touch                     # r133 D2: never raises


def _cfg_entry_open():
    """The configured entry-open time, read at CALL time so an env change needs
    no restart of this module and a test can move the clock."""
    try:
        import config as _c
        return tuple(getattr(_c, "ENTRY_OPEN_ET", (9, 35)))[:2]
    except Exception:                                          # noqa: BLE001
        return (9, 35)

logger = logging.getLogger(__name__)

# r133 D3 — the contract each strategy is walking, live only, in memory (lost on a restart, like the walk itself).
# (strategy_name, option_side, direction) -> {"contract", "key", "seen" (monotonic, the last rung posted)}.
_PINS: dict = {}
# A pin with no rung posted for three ticks (3 x POLL_INTERVAL_SECONDS) is a walk the strategy stopped asking for.
PIN_IDLE_S = 45.0


def _pin_id(signal) -> tuple:
    return (str(getattr(signal, "strategy_name", "") or ""),
            str(getattr(signal, "option_side", "") or "").lower(),
            str(getattr(signal, "direction", "") or "").lower())


class EntryEngine:
    """Places orders for all strategy types and returns a populated TradeRecord."""

    def __init__(self, paper_trading: bool = PAPER_TRADING):
        self.paper_trading = paper_trading
        self._trade_logger = get_trade_logger()

    def enter(self,
              signal:  OptionsSignal,
              sizing:  SizingResult,
              score=None) -> Optional[TradeRecord]:
        """
        Place entry order and record the trade.
        Returns TradeRecord on success, None on failure.
        """
        mode = "PAPER" if self.paper_trading else "LIVE"

        # ── 🔴 r101 — NOTHING OPENS BEFORE ENTRY_OPEN_ET (09:35 ET) ─────────
        # Operator, 2026-08-24: the deciding logic runs as long as the service
        # is up; ONE gate stops it placing until the opening range exists.
        # ⚠️ IT SITS HERE, AT THE ORDER, AND NOT IN THE STRATEGIES. A gate per
        # strategy is a gate the NEXT strategy does not have — the AFD.1 shape,
        # twice over. Two choke points cover every opening in the system: this
        # one (single leg + butterfly) and `main._execute_condor_leg` (all four
        # credit verticals).
        # ⚠️ AND IT REFUSES BEFORE THE ORDER, NOT AFTER THE FILL. Returning None
        # here means no broker call, no record, no position — the caller logs a
        # no-trade and the strategy re-signals next tick.
        if not entries_open():
            _h, _m = _cfg_entry_open()
            logger.info(
                "[entry-gate] %s %s HELD — entries open at %02d:%02d ET "
                "(opening range not established). The setup was fully formed; "
                "it re-signals next tick.", mode, signal.strategy_name, _h, _m)
            return None
        # r146 (BLND.1) — AFTER A BLIND EPISODE, nothing opens while the episode stands: the tick that first sees again,
        # and any later tick until main.attempt_new_entry has seen one full tick on current 1m bars and ended it. That
        # call already holds every setup (nothing is asked); this is the belt at the debit order for any other caller.
        # '' = no episode: nothing changes. Zero broker calls.
        from utils import blind_reacquire as _blind_reacq
        _reacq = _blind_reacq.hold(now_et().timestamp())
        if _reacq:
            logger.info("[entry-gate] %s %s HELD - %s", mode, signal.strategy_name, _reacq)
            return None

        logger.info(
            f"[{mode}] DIRECTIONAL ENTRY: "
            f"{signal.option_side.upper()} {signal.strike} "
            f"{sizing.contracts} contract(s) "
            f"mark=${signal.entry_premium:.2f} "
            ""
        )
        fill_premium, order_id, filled_qty = self._place_single_leg(
            signal, sizing.contracts)

        if fill_premium is None or filled_qty <= 0:
            logger.error("Entry order failed — no confirmed fill, no position recorded")
            return None
        return self._book_fill(signal, fill_premium, order_id, filled_qty, sizing.contracts)

    def _book_fill(self, signal: OptionsSignal, fill_premium: float, order_id: str,
                   filled_qty: int, planned: int, how: str = "") -> TradeRecord:
        """THE ONE PLACE A CONFIRMED ENTRY FILL BECOMES A ROW. r135 (GUARD.1): enter() books here as it always did,
        and so does order_guard's resolution of a suspect (an unconfirmed cancel, a lost reply, unreadable fills),
        through the booking handed to it by _place_single_leg, so a late fill carries its own strategy's plan
        (stop, trail, target, setup) instead of becoming ADOPTED. `how` is appended to the row's notes."""
        mode = "PAPER" if self.paper_trading else "LIVE"
        if filled_qty < planned:
            logger.warning(
                f"[{mode}] Entry PARTIAL: {filled_qty}/{planned} "
                f"filled — recording the filled size")

        total_cost = fill_premium * filled_qty * CONTRACT_MULTIPLIER

        record = make_record(
            **self._record_kwargs(signal),
            trade_id          = str(uuid.uuid4()),
            # ⚠️ r152 — columns retained (the DB schema and every dashboard
            # read them); the SELECTOR that filled them is gone. UNGRADED is a
            # marker, not a verdict.
            setup_grade       = "UNGRADED",
            setup_score       = None,
            option_side       = signal.option_side,
            is_liquidity_hunt = bool(getattr(signal, "is_liquidity_hunt", False)),   # r12 (hunt)
            strike            = signal.strike,
            expiry            = signal.expiry,
            contracts         = filled_qty,
            entry_premium     = fill_premium,
            total_cost        = total_cost,
            max_loss          = total_cost,
            stop_premium      = signal.stop_premium(),
            trail_activation  = signal.trail_activation_premium(),
            target_premium    = signal.target_premium(),
            adx_at_entry      = getattr(signal, 'adx_at_signal', 0.0),
            flat_angle_deg    = getattr(signal, 'flat_angle_deg', 0.0),
            swept_level_name  = getattr(signal, 'swept_level_name', ''),
            level_strength    = getattr(signal, 'level_strength', 0.0),
            order_id          = order_id,
            paper_trade       = 1 if self.paper_trading else 0,
            # ⚠️ AUDIT F4 (2026-08-20): relaxed.tag() sets this on the SIGNAL
            # and this kwarg list is the only bridge to the row — without the
            # line below, `relaxed_entry` was DEFAULT 0 on every trade ever
            # written while the schema, the migration and the doctrine all
            # claimed the population was separable. Exactly the failure the
            # audit handoff predicted: tag set on the signal, dropped before
            # the insert. The `_relaxed` setup suffix survived only by riding
            # setup_type. Copy the tag, always.
            relaxed_entry     = int(getattr(signal, "relaxed_entry", 0) or 0),
            status            = "open",
            notes             = (f"{signal.notes} | {how}" if signal.notes else how) if how else signal.notes,
        )

        # ── ORB range boundaries — persisted for exit_engine range violation ──
        # exit_engine checks if 1-min close goes back inside the ORB range
        # 🔴 r240 (rebuilding r226, which was cut and NEVER LANDED) — A
        # CAPABILITY CHECK, NOT AN IDENTITY CHECK. This read `signal.is_orb`,
        # which is literally `strategy_name == "ORBStrategy"`. The RUNAWAY
        # populates `orb_range_high/low` too — it is a continuation of the same
        # break — and the name check discarded them on every runaway fill.
        # 🔴 MEASURED: `calibrate_trend_strength` reported "no ORB boundary on
        # the row : 182" — ALL 182 runaway trades unmeasurable, on the largest
        # strategy in the book by both count and net.
        # ⚠️ IT BLOCKS MOM.1 STAGE 1, which r225 filed as the stage every other
        # stage anchors on: strength calibrates against the break-to-50 path,
        # and the boundary is exactly what was being thrown away.
        # ⚠️ AND IT IS WHY THE ORB STRUCTURE STOP LOOKS ABSENT ON THE RUNAWAY.
        # `exit_engine`'s structure stop needs a bound on the record and skips
        # silently without one, so ORB.7's "the -25% floor fires first" is, for
        # the runaway, "the structure stop had nothing to fire against."
        # 🔑 THE TEST IS WHETHER THE SIGNAL CARRIES THE GEOMETRY, not what it is
        # called. A name check is a list, and r35's allow-list rot is what
        # happens to lists: the next strategy that computes an ORB boundary is
        # covered by HAVING one, not by being remembered here.
        _orb_hi = getattr(signal, "orb_range_high", None)
        _orb_lo = getattr(signal, "orb_range_low", None)
        if _orb_hi and _orb_lo:
            record["orb_range_high"] = _orb_hi
            record["orb_range_low"]  = _orb_lo
            # ── r119 — THE SETUP'S GEOMETRY, MEASURED AT FIRE ──────────────
            # Operator, 2026-08-25, watching TSLA and PLTR stop out structurally
            # within five minutes: "the closer to the range boundary the
            # impulsive candle (stop location) sits, the lower the risk & higher
            # the R-value." Both ratios are knowable HERE and nowhere later —
            # the ORB range is the one this fire confirmed against, and by the
            # time a postmortem runs the engine has moved on.
            # ⚠️ RECORDED, NOT GRADED. Operator: "observe first." Nothing reads
            # these. They exist so the bands can be FITTED in a few weeks, and
            # so the real question is answerable: do deep-break setups FAIL more
            # often, or merely COST more when they fail? A gate answers the
            # first; a size answers the second, and guessing picks wrong.
            # ⚠️ WHY GRADING WOULD NOT HAVE WORKED ANYWAY: the operator's point
            # that ORB survivors are "all structurally A unless we start grading
            # how deep the impulsive candle sits inside the range" is visible in
            # the data — PLTR 51 A-grades, TSLA 30, AVGO 29. The letter carries
            # no information for this strategy today, so this ratio is not AN
            # input to the grade, it is the ONLY discriminator ORB has left.
            _u_entry = float(record.get("underlying_entry") or 0.0)
            _u_stop  = float(record.get("underlying_stop")   or 0.0)
            _u_tgt   = float(record.get("underlying_target") or 0.0)
            _width   = abs(float(signal.orb_range_high or 0.0)
                           - float(signal.orb_range_low or 0.0))
            _risk    = abs(_u_entry - _u_stop)
            # Left NULL when a leg is missing — see the schema note. A ratio of
            # zero is impossible; a MISSING one is ordinary, and the two must
            # stay distinguishable.
            if _width > 0 and _risk > 0:
                record["stop_width_pct"] = round(_risk / _width, 4)
            if _risk > 0 and _u_tgt and _u_entry:
                record["planned_r"] = round(abs(_u_tgt - _u_entry) / _risk, 3)
            # ── r120 — THE TAPE AT THE LEVEL, while it was contested ───────
            # Wrapped whole: this is an observation, and an observation must
            # never be the reason a confirmed fill fails to record.
            try:
                from analysis.tape_at_level import measure as _tape
                _lvl = (float(signal.orb_range_high or 0.0)
                        if (signal.direction or "").upper() in ("LONG", "BULLISH")
                        else float(signal.orb_range_low or 0.0))
                _since = float(getattr(signal, "orb_break_ts", 0.0) or 0.0)
                record.update(_tape(
                    symbol=str(record.get("symbol") or ""),
                    level=_lvl,
                    since_epoch=_since or (time.time() - 900),
                    until_epoch=time.time(),
                    atr=float(getattr(signal, "atr_at_signal", 0.0) or 0.0) or None))
            except Exception as exc:                            # noqa: BLE001
                logger.debug("tape-at-level skipped: %s", exc)
            logger.info("[orb-geom] stop_width=%s of range  planned_r=%s "
                        "tape_vol=%s buy_frac=%s",
                        f"{record.get('stop_width_pct'):.1%}"
                        if record.get("stop_width_pct") is not None else "n/a",
                        f"{record.get('planned_r'):.2f}"
                        if record.get("planned_r") is not None else "n/a",
                        record.get("tape_vol_at_level", "n/a"),
                        record.get("tape_buy_frac_at_level", "n/a"))

        # r151 (CAP.11): a PAPER box's cap is record only. A paper entry opened while it stands tripped (counted as cash
        # would count it) is tagged after_cap = 1; any other row carries no key (NULL), exactly the r150 record.
        if self.paper_trading is True and getattr(self, "PAPER_WALL", False) is not True:
            try:
                from risk.risk_manager import get_risk_manager as _grm_ac
                if _grm_ac().after_cap_tag() is True:
                    record["after_cap"] = 1
            except Exception as _ace:                           # noqa: BLE001
                logger.warning("after_cap tag skipped: %s", _ace)
        self._trade_logger.log_entry(record)
        try:                                                    # r208 (CAP.4): log-only, never affects the entry
            if getattr(self, "PAPER_WALL", False) is not True:  # r150 (OGAP.5): a walled paper row is not the cash cap's
                from risk.risk_manager import get_risk_manager as _grm
                _grm().note_entry_risk(record)
        except Exception as _cfe:                               # noqa: BLE001
            logger.warning("cap counterfactual skipped: %s", _cfe)

        logger.info(
            f"✅ Entry confirmed [{mode}]: "
            f"ID={record['trade_id'][:8]} "
            f"fill=${fill_premium:.2f}/share "
            f"total=${total_cost:.2f}"
        )
        return record

    # ─── THE LADDER (r104) ────────────────────────────────────────────────────
    # 🔴 `execution/entry_ladder.py` HAS BEEN COMPLETE AND UNCALLED SINCE
    # 2026-08-20. Every live fill has posted a single limit at mark and walked
    # away. By FRC.1 the fleet's gross edge is +$2.70/trade against $126/trade
    # of round-trip friction; capturing half the half-spread is worth on the
    # order of $31/trade — an order of magnitude more than anything on the
    # trade-selection list. The file's own header says so and nothing read it.
    #
    # ⚠️ ONE RUNG PER TICK, AND THAT IS WHY A REGISTRY EXISTS. The walk is
    # multi-tick by construction: this method posts ONE price, gives it a short
    # deadline, and returns unfilled. The strategy re-signals next tick and the
    # walk RESUMES at the next rung against a FRESH quote — repricing (rule 2)
    # and ratcheting (rule 1) both come out of that. A ladder that restarted
    # every tick would re-offer rung 1 forever, which is v3's exact defect.
    #
    # ⚠️ THE DEADLINE IS PER RUNG, NOT PER ENTRY. LIVE_ENTRY_DEADLINE_SECONDS
    # (20s) was sized for a single mark-limit that either fills or is abandoned.
    # Spending all of it on rung 1 would mean one rung per 20s against a 15s
    # tick — the walk would never reach mark inside a fill window. Each rung
    # gets a slice; the ladder collapses to mark on its own when the market
    # moves our way (rule 3), so the terminal rung is reached by price, not by
    # waiting.
    #
    # ⚠️ PAPER NEVER TOUCHES THIS. Paper pricing stays limit_ladder.paper_fill_*
    # — one paper authority. A ladder in paper would model fills we have no
    # evidence for, and the ladder's value is measured in LIVE fills or not at
    # all (ladder_registry's header).
    @staticmethod
    def _rung_deadline() -> float:
        """Seconds to give ONE rung. A slice of the entry deadline, floored so a
        rung is never so short that a fillable price is abandoned unseen."""
        try:
            import config as _c
            total = float(getattr(_c, "LIVE_ENTRY_DEADLINE_SECONDS", 20.0))
        except Exception:                                      # noqa: BLE001
            total = 20.0
        return max(4.0, total / 4.0)

    @staticmethod
    def _quote_of(contract) -> Tuple[float, float]:
        """(bid, ask) off a contract, 0.0 when absent. A zero BID is a real,
        routine 0DTE quote and the ladder handles it (r98/r99); a missing ASK
        is what makes a quote unusable."""
        try:
            return (float(getattr(contract, "bid", 0.0) or 0.0),
                    float(getattr(contract, "ask", 0.0) or 0.0))
        except (TypeError, ValueError):
            return (0.0, 0.0)

    def _walk_price(self, key: str, side: str, bid: float, ask: float,
                    symbol: str, mark_fallback: float) -> Tuple[float, str]:
        """The price to post THIS attempt, and why. Falls back to the mark when
        the quote is unusable — never to a guess, and never worse than mark.

        `symbol` is the GRID symbol — the UNDERLYING (INSTRUMENT), the name the
        venue rule is cached under — never the OCC contract (r132 TICK.3)."""
        try:
            from execution import ladder_registry as _lr
            got = _lr.price_for(key, side, bid, ask, symbol)
            if got:
                return float(got[0]), str(got[1])
        except Exception as exc:                               # noqa: BLE001
            logger.warning("[ladder] pricing failed (%s) — posting at mark", exc)
        return limit_at_mark(mark_fallback, floor=0.01), "mark (no usable quote)"

    @staticmethod
    def _walk_refused(key: str, price: float) -> None:
        """Record that this rung did not COMPLETELY fill. The next tick resumes
        one rung further in and never re-offers this price."""
        try:
            from execution import ladder_registry as _lr
            _lr.refuse(key, price)
        except Exception as exc:                               # noqa: BLE001
            logger.debug("[ladder] refuse failed: %s", exc)

    @staticmethod
    def _walk_done(key: str) -> None:
        """Filled or abandoned — never leave a walk to rot (stale ratchet)."""
        try:
            from execution import ladder_registry as _lr
            _lr.clear(key)
        except Exception as exc:                               # noqa: BLE001
            logger.debug("[ladder] clear failed: %s", exc)

    # ─── r133 D2 / D3 — THE 5-SECOND WALK, ON A CONTRACT FROZEN FOR ITS LIFE ──
    # 🔴 THE DUTY CYCLE WAS A THIRD. Each rung rested ~5 s (_rung_deadline) and
    # then NOTHING was working until the next 15 s tick: the forward-edge study
    # 2026-11-20 (D2, ~/reviews/studies/forward_edge_20261120/REPORT.md) measured
    # strict-touch fills 79% at 36 s mean, and 89% at 21 s with the gap removed.
    # The operator, 2026-11-20: "If the ladder was fast enough to update every 5
    # seconds, I would prefer that" and "Yes to both".
    # 🔑 THE LOOP, live only: post a rung, rest it on the 2 s poll grid
    # (confirm_order_fill, unchanged), CANCEL it and READ IT DEAD (the same call:
    # it returns only on a broker status of Filled, Rejected or dead, or with
    # working_order_id set when the cancel could not be confirmed), refuse it,
    # re-read the STREAMED quote (feed_store.db chain_marks — the store the tick's
    # chain is built from; a local read, no broker quote call), price the next
    # rung with the SAME LadderState under the SAME key, and post it.
    # ⚠️ NO LADDER RULE CHANGES. next_price is called exactly as a tick calls it;
    # the 25% start, the ratchet, the mark cap after the ratchet, never worse than
    # mark and the venue grid are entry_ladder's, untouched. Only WHEN the next
    # rung is asked for changes: now, instead of in ~10 s.
    # ⚠️ IT STOPS, AND HANDS THE WALK BACK TO THE TICK, on: a fill (any quantity —
    # a partial is booked, as before); the MARK RUNG REFUSED (the walk's terminal
    # rung: the rung a tick re-offers forever, so the next tick resumes it exactly
    # as before); a rejection or no order id; the strategy's entry window ending
    # (config.ENTRY_WINDOWS, the admission table's own source; the walk is then
    # cleared); no fresh streamed quote; an unconfirmed cancel (the order guard
    # then holds the intent until the broker reads it dead); or the TICK BUDGET.
    # ⚠️ THE BUDGET IS ONE TICK. No rung starts unless its rest ends inside
    # POLL_INTERVAL_SECONDS (15 s) of the call's start, so one call posts at most
    # two rungs (~6-7 s apart on the 2 s poll grid) and an open position's next
    # manage pass is late by at most one tick. The heartbeat is touched on every
    # poll (confirm_order_fill) and between rungs; the watchdog's floor is 180 s.
    # ⚠️ ORDER RATE: per rung one place, one balance read, ~5 status reads and
    # one cancel — about 1.2 requests a second for a walking box. tastytrade
    # publishes no limit; a raising place_order ends the loop through the r127
    # lost-post guard (the intent is held at least LOST_GRACE_S, 10 s), a raising
    # poll retries on the 2 s grid, a raising cancel at most three times.
    # ⚠️ A RESTART MID-WALK LOSES THE RATCHET AND THE FREEZE (both in memory, as
    # ladder_registry's header records); the boot sweep (r495 B4) still cancels
    # any working rung before anything posts.

    @staticmethod
    def _walk_budget_s() -> float:
        """Wall seconds one call may walk: one main-loop tick (config.POLL_INTERVAL_SECONDS)."""
        try:
            import config as _c
            return float(getattr(_c, "POLL_INTERVAL_SECONDS", 15) or 15)
        except Exception:                                      # noqa: BLE001
            return 15.0

    @staticmethod
    def _fresh_quote(contract) -> Optional[Tuple[float, float]]:
        """(bid, ask) re-read from the streamed store the tick's chain comes from (chain_marks through
        OptionsChainFetcher._read_marks, its OT_CHAIN_STALE_S floor unchanged). None when the contract has no
        streamer symbol, the row is missing or stale, the book is unusable, or the read fails."""
        sym = str(getattr(contract, "streamer_symbol", "") or "")
        if not sym:
            return None
        try:
            from data.options_chain import get_chain_fetcher
            _greeks, quotes = get_chain_fetcher()._read_marks([sym])
            q = quotes.get(sym)
            if q is None:
                return None
            b, a = float(q.bid_price or 0.0), float(q.ask_price or 0.0)
        except Exception as exc:                               # noqa: BLE001
            logger.debug("[ladder] streamed quote unreadable for %s: %s", sym, exc)
            return None
        if a <= 0 or b < 0 or a < b:
            return None
        return b, a

    @staticmethod
    def _window_open(strategy_name) -> Tuple[bool, str]:
        """(open, why). The strategy's entry window from config.ENTRY_WINDOWS (half-open, the admission table's
        own source) and entries_open(). A strategy with no row there has no window to read: closed, so its
        walk keeps one rung per call."""
        try:
            import config as _c
            win = (getattr(_c, "ENTRY_WINDOWS", None) or {}).get(str(strategy_name or ""))
            if not win:
                return False, f"no entry window on record for {strategy_name!r}"
            if not entries_open():
                return False, "entries are closed"
            n = now_et()
            (sh, sm), (eh, em) = win
            t = n.hour * 60 + n.minute
            if not (sh * 60 + sm <= t < eh * 60 + em):
                return False, f"its entry window {sh}:{sm:02d}-{eh}:{em:02d} ET has ended"
            return True, ""
        except Exception as exc:                               # noqa: BLE001
            return False, f"entry window unreadable ({type(exc).__name__})"

    @staticmethod
    def _is_mark_rung(price: float, why: str, bid: float, ask: float) -> bool:
        """True when `price` was the walk's TERMINAL rung on its quote: the mark snapped in our favour (the
        table's last rung, or next_price's mark clamp), or the one-increment $0.00 exception. Unreadable: True."""
        if str(why or "").startswith("mark"):
            return True
        try:
            from execution.entry_ladder import rungs
            table = rungs(bid, ask, "buy", INSTRUMENT)
        except Exception:                                      # noqa: BLE001
            return True
        return (not table) or float(price) >= float(table[-1]) - 1e-9

    # ─── Order Placement ──────────────────────────────────────────────────────

    def _place_single_leg(self, signal: OptionsSignal,
                           contracts: int) -> Tuple[Optional[float], str, int]:
        """Returns (fill_price, order_id, filled_qty). Live fill price is READ
        BACK from the broker's fills — a market order has no .price, so the
        old `placed.price or signal.entry_premium` always booked the signal
        mark. filled_qty==0 means record NOTHING.

        r133 (D2): live, it walks rung after rung inside this call until a stop
        (see the block above); paper is unchanged and returns first."""
        if self.paper_trading:
            return self._paper_fill_single(signal, contracts)

        _placed = _key = limit = _booking = None                        # B2 (r135: + the suspect booking)
        _posting = False                                                # r127 LOP.1
        try:
            session  = get_session()
            account  = get_account()
            symbol   = signal.contract.symbol

            leg = Leg(
                instrument_type = InstrumentType.EQUITY_OPTION,
                symbol          = symbol,
                action          = OrderAction.BUY_TO_OPEN,
                quantity        = contracts,
            )
            # v3.8: MARK-LIMIT ENTRY (was MARKET). A market entry paid the ask
            # while the signal that justified the trade was scored on the mark —
            # on a $0.20 0DTE with a $0.05 spread that is ~12% of premium before
            # the position even moves. We post AT THE MARK and let it sit. An
            # entry that does not fill costs NOTHING: confirm_order_fill cancels
            # and we walk away, and the strategy re-signals next tick against a
            # FRESH mark (that re-anchoring is what tracks a moving market —
            # there is no stale resting order). Debit paid -> price NEGATIVE per
            # the SDK signed convention.
            mid = float(signal.entry_premium or 0.0)
            if mid <= 0:
                logger.warning("Single-leg entry: no mark to price the limit — "
                               "skipping this pass")
                return None, "", 0
            # r104 — THE RUNG, NOT THE MARK. Buying a debit: start 25% in from
            # the BID, step one venue increment toward mark, never pay worse
            # than mark. The walk is keyed to the INTENT (this contract, opened)
            # so the next tick resumes it rather than restarting at rung 1.
            from execution import ladder_registry as _lr
            _bid, _ask = self._quote_of(signal.contract)
            _key = _lr.intent_key(symbol, "open", "single")
            _pid = _pin_id(signal)                                      # r133 D3
            _booking = self._suspect_booking(signal, contracts, symbol, _key, _pid)   # r135 GUARD.1
            _t0 = time.monotonic()                                      # r133 D2: the call's budget clock
            _budget = self._walk_budget_s()
            _n = 0
            while True:                                                 # r133 D2: rung after rung, bounded
                _n += 1
                _ok, _gwhy = _guard.clear_to_post(_key, session, account)   # B2
                if not _ok:
                    logger.warning("[guard] single-leg %s not posted: %s", symbol, _gwhy)
                    return None, "", 0
                # 🔴 r132 TICK.3 — THE GRID IS THE UNDERLYING'S, NOT THE CONTRACT'S. The venue
                # rule is cached under the underlying (options_chain._get_chain_structure) and
                # PENNY_CLASSES lists underlyings, so the OCC symbol always missed and priced
                # every entry on the non-penny grid (QQQ 3.40/3.50: [3.40], not [3.42..3.45]).
                # Exits pass record["symbol"] = INSTRUMENT; the entry now does too. The walk
                # KEY above stays the contract's.
                limit, _why = self._walk_price(_key, "buy", _bid, _ask, INSTRUMENT, mid)
                _bok, _bwhy = _bp.affordable(float(limit) * int(contracts) * 100.0,
                                             session, account, f"single-leg {symbol}")   # F5
                if not _bok:
                    logger.warning("[bp] single-leg %s not posted: %s", symbol, _bwhy)
                    return None, "", 0
                logger.info("[ladder] %s BUY %s @ %.2f — %s (bid %.2f / ask %.2f)%s",
                            symbol, "single", limit, _why, _bid, _ask,
                            f" [rung {_n} of this tick]" if _n > 1 else "")
                order = NewOrder(
                    time_in_force = OrderTimeInForce.DAY,
                    order_type    = OrderType.LIMIT,
                    price         = Decimal(str(-limit)),   # - = DEBIT paid to open
                    legs          = [leg],
                )
                _posting = True                                         # r127 LOP.1
                response = sdk_result(account.place_order(session, order, dry_run=False))   # B0
                _posting = False
                if response.errors:
                    logger.error(f"Order errors: {response.errors}")
                    return None, "", 0
                _placed = response.order                                # B2
                _PINS[_pid] = {"contract": signal.contract, "key": _key,
                               "seen": time.monotonic()}                # r133 D3: the walk's contract

                fill = confirm_order_fill(session, account, response.order,
                                          [(symbol, 1, +1)],
                                          what=f"single-leg entry (LADDER {limit:.2f} — {_why})",
                                          deadline_s=self._rung_deadline())
                if fill.filled and fill.net_price is not None:
                    # A fill — during the rest OR during the cancel race — is the
                    # walk's end: booked once, at the broker's own fills.
                    self._walk_done(_key)
                    _PINS.pop(_pid, None)
                    return fill.net_price, fill.order_id or "", fill.quantity
                self._page_if_working(fill, "single-leg entry")
                # ⚠️ A REFUSAL, NOT AN ABANDONMENT. The rung did not fill, so
                # it is off the table for good (rule 1) and the next rung is
                # priced against a fresh quote (rule 2). An entry that never
                # fills still costs nothing.
                self._walk_refused(_key, limit)
                _dead, _placed = _placed, None
                if fill.working_order_id:
                    # r133 — THE CANCEL WAS NOT CONFIRMED (or the fills were unreadable):
                    # the order may still be live or filled. Nothing posts beside it —
                    # not in this call, and not next tick: the order guard holds the
                    # intent until the broker reads that order dead (B2).
                    _guard.after_failure(_key, _dead, session, account,
                                         "single-leg entry (cancel unconfirmed)", booking=_booking)
                    logger.info("[ladder] %s rung %.2f REFUSED (%s) — cancel unconfirmed; "
                                "the instrument is held by the order guard", symbol, limit, fill.detail)
                    return None, "", 0
                _stop, _end = self._walk_stop(signal, limit, _why, _bid, _ask, fill, _t0, _budget)
                if _stop:
                    if _end:
                        self._walk_done(_key)
                        _PINS.pop(_pid, None)
                    logger.info("[ladder] %s rung %.2f REFUSED (%s) — %s; %s", symbol, limit,
                                fill.detail, _stop,
                                "the walk is over" if _end else "next rung on the next tick")
                    return None, "", 0
                _hb_touch("entry ladder")
                _q = self._fresh_quote(signal.contract)
                if _q is None:
                    logger.info("[ladder] %s rung %.2f REFUSED (%s) — no fresh streamed quote; "
                                "next rung on the next tick", symbol, limit, fill.detail)
                    return None, "", 0
                logger.info("[ladder] %s rung %.2f REFUSED (%s) — next rung now, on the streamed "
                            "quote %.2f / %.2f", symbol, limit, fill.detail, _q[0], _q[1])
                _bid, _ask = _q
                mid = round((_bid + _ask) / 2.0, 4)

        except Exception as e:
            logger.error(f"Single-leg order failed: {e}")
            if _placed is not None:                                     # B2
                self._walk_refused(_key, limit)
                _guard.after_failure(_key, _placed, session, account, "single-leg entry",
                                     booking=_booking)                  # r135 GUARD.1
            elif _posting:                                              # r127 LOP.1
                _guard.after_lost_post(_key, [symbol], session, account, "single-leg entry", e,
                                       booking=_booking)                # r135 GUARD.1
            return None, "", 0

    def _suspect_booking(self, signal, contracts: int, symbol: str, key: str, pid: tuple) -> dict:
        """r135 (GUARD.1) — what order_guard needs to book a suspect order's fill as THIS entry: the single-leg
        basis and a closure over the signal that fired it. The closure ends the walk and its pin, then books
        through _book_fill exactly as a confirmed entry is booked."""
        sig = copy.copy(signal)

        def _fn(price: float, qty: int, oid: str):
            self._walk_done(key)
            _PINS.pop(pid, None)
            return self._book_fill(sig, float(price), str(oid or ""), int(qty), int(contracts),
                                   how="entry fill confirmed by the order guard after the walk")
        return {"fn": _fn, "basis": [(symbol, 1, +1)],
                "strategy": str(getattr(signal, "strategy_name", "") or "")}

    def _walk_stop(self, signal, limit, why, bid, ask, fill, t0, budget) -> Tuple[str, bool]:
        """(why the walk hands back to the tick, or "", and whether the walk is OVER). r133 D2."""
        detail = str(getattr(fill, "detail", "") or "")
        if detail.startswith("rejected"):
            return "the broker rejected the rung", False
        if not getattr(fill, "order_id", None):
            return "no order id came back", False
        if self._is_mark_rung(limit, why, bid, ask):
            return "the mark rung was refused (the terminal rung; the next tick re-offers it)", False
        ok, w = self._window_open(getattr(signal, "strategy_name", ""))
        if not ok:
            return w, w.startswith("its entry window")
        used = time.monotonic() - t0
        if used + self._rung_deadline() > budget:
            return f"the tick budget ({used:.0f} s of {budget:.0f} s used)", False
        return "", False

    def _record_kwargs(self, signal) -> dict:
        """The record fields that come from the SIGNAL, not from the fill.

        🔑 ONE LINEAGE. `enter()` builds a record the moment a fill confirms.
        (The standing-offer path that also built one when its SUPERVISOR found
        a fill was removed at r76; its store and supervisor went at r118.) Any
        new construction site must call this too. A second
        construction site is WORKING_AGREEMENT 7's exact failure — two versions
        that look correct in isolation and drift on the field nobody compares.
        """
        return dict(
            symbol            = INSTRUMENT,
            # 🔴 PRE.1 (r17) — THE ROW NAMED NO OPTION. `symbol` is the UNDERLYING;
            # nothing here wrote the CONTRACT, so 19 of 21 rows in this box's
            # trades.db carry a NULL `option_symbol` (every ORB, every runaway,
            # all three hunts; only the credit path, which writes it on its own,
            # carried one). A row with no option symbol joins to no quote_series,
            # so every premium-path study REFUSES it — mainline measured
            # exit_replay refusing 301 of 337 and fixed it at r340. FORWARD-ONLY:
            # rows already in the book stay unreplayable. HUNT.1's first week
            # opens Monday and every hunt fill would land unjoinable without this.
            option_symbol     = str(getattr(getattr(signal, "contract", None), "symbol", "") or ""),
            strategy          = signal.strategy_name,
            setup_type        = signal.setup_type,
            direction         = signal.direction,
            underlying_entry  = signal.underlying_entry,
            underlying_stop   = signal.underlying_stop,
            underlying_target = signal.underlying_target,
            vix_at_entry      = signal.vix_at_signal,
            is_fed_day        = signal.is_fed_day,
        )

    @staticmethod
    def _page_if_working(fill, what: str):
        """An entry order that could not be cancelled may still fill — page
        once so it's watched. r135 (GUARD.1): the order guard books a late fill
        under its strategy; reconcile adopts it only after the guard gives up."""
        if not fill.working_order_id:
            return
        try:
            from notifications.alert_manager import get_alert_manager
            get_alert_manager()._send(
                f"\U0001F6A8 {what}: order {fill.working_order_id} could not "
                f"be cancelled (or its fills read) and may still fill. No new entry posts on "
                f"{INSTRUMENT} until the order guard resolves it: a fill is booked under its "
                f"strategy with its plan; reconcile adopts it only if the guard gives up "
                f"({_guard.RESOLVE_GIVEUP_S:.0f} s unresolved, or past the day's last entry window). ({fill.detail})")
        except Exception as e:
            logger.warning(f"Working-order page failed to send: {e}")

    def _paper_fill_single(self, signal: OptionsSignal,
                           contracts: int) -> Tuple[float, str, int]:
        """v3.8: books the MARK, matching the live mark-limit entry.

        Was mark * (1 + PAPER_FILL_SLIPPAGE_PCT) — modelling the market order
        that live no longer sends. Under the mark-limit policy live either
        fills AT the mark or does not fill at all, so a slippage markup would
        now make paper PESSIMISTIC on price while still being optimistic on
        fill rate. The honest residual gap is no-fill risk, not slippage; see
        execution/limit_ladder.paper_fill_price."""
        fill_price = paper_fill_price(float(signal.entry_premium or 0.0), floor=0.01)
        return fill_price, f"PAPER-{uuid.uuid4().hex[:8].upper()}", contracts


def freeze_contract(signal, paper_trading: bool = PAPER_TRADING) -> bool:
    """r133 D3 — A WALK IN FLIGHT KEEPS ITS CONTRACT. Runaway and the Hunt re-pick the strike every tick
    (gamma_leverage_pick over the live spot and run), and the walk key is the contract's, so a new strike
    started a fresh walk at the 25% opener and dropped the old one's ratchet. main._execute_entry_signal calls it
    before sizing: when this strategy (same side, same direction) has a walk posted inside PIN_IDLE_S and the signal names a
    different contract, the signal is put back on the walking one, re-quoted from the stream, so sizing, the
    order and the record all name it. True when it swapped. Paper never walks: a no-op there. Never raises."""
    if paper_trading:
        return False
    try:
        pid = _pin_id(signal)
        pin = _PINS.get(pid)
        if pin is None:
            return False
        if time.monotonic() - pin["seen"] > PIN_IDLE_S:
            _PINS.pop(pid, None)
            return False
        pc = pin["contract"]
        occ = str(getattr(pc, "symbol", "") or "")
        cur = str(getattr(getattr(signal, "contract", None), "symbol", "") or "")
        if not occ or cur == occ:
            return False
        q = EntryEngine._fresh_quote(pc)
        if q is None:
            _PINS.pop(pid, None)
            logger.warning("[ladder] D3 the walk on %s is abandoned - no fresh streamed quote for it; the "
                           "re-pick %s starts its own walk", occ, cur)
            return False
        b, a = q
        c = copy.copy(pc)
        c.bid, c.ask = b, a
        mark = (b + a) / 2.0 if b > 0 and a > 0 else (b or a)
        if hasattr(c, "mark"):
            c.mark = mark
        signal.contract = c
        signal.strike = getattr(c, "strike", getattr(signal, "strike", None))
        signal.expiry = getattr(c, "expiry", getattr(signal, "expiry", ""))
        signal.entry_premium = mark                        # r136 OGAP.3: OGAP sizes on this mark too
        logger.warning("[ladder] D3 %s re-picked %s mid-walk - the walk stays on %s (bid %.2f / ask %.2f); the "
                       "contract is frozen until it fills, its window ends or it goes idle %.0f s",
                       pid[0], cur, occ, b, a, PIN_IDLE_S)
        return True
    except Exception as exc:                               # noqa: BLE001
        logger.warning("[ladder] D3 freeze skipped (%s: %s)", type(exc).__name__, exc)
        return False


_entry_engine: Optional[EntryEngine] = None


def get_entry_engine(paper_trading: bool = PAPER_TRADING) -> EntryEngine:
    global _entry_engine
    if _entry_engine is None:
        _entry_engine = EntryEngine(paper_trading)
    return _entry_engine
