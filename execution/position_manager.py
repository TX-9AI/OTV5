"""
execution/position_manager.py  v5.28
v5.28 2026-10-30  OTV5 r57 (TCS.LOG1) — THE SHADOW SEAM. Two hooks, _exit_engine() (get_exit_engine, as before) and
      _management() (get_management_plan, as before), so execution/shadow_book.ShadowPositionManager manages a SHADOW
      trade through THIS _manage_one / flatten_all / _execute_exit with its own exit engine, store and management rows.
      SHADOW (False here; read as getattr(self, "SHADOW", False) is True, so a stand-in self is never a shadow)
      gates the five real-book side effects of a close: the resting stop, risk_manager
      record_win / record_loss (the daily loss cap), the Telegram exit alert, the ORB re-arm / standing-offer cancel
      and the resting-stop abandon. The P&L arithmetic, log_exit, the exit quote and trail cleanup are shared. On this
      class every path is byte-for-byte today's behaviour. Gate tests/check_tcs_shadow.py.
v5.27 2026-10-28  OTV5 r48 (LIVE.7, PARC.1 nickel) — TWO LIVE EXIT-PATH EDGES FROM THE 2026-10-27 ORDER-PATH AUDIT.
      (b) flatten_all with no live mark passed the ENTRY premium on as the mark, so live a 15:50 close could post a
      sell limit AT ENTRY (marketable when the option is above entry). LIVE now invents no mark: it passes None and
      the close routes the way a no-mark close already routes (LIVE.1 F3: nothing posted before the 15:55 cross, the
      cross handles it; exit_engine v5.6 extends the hold to a resting vertical / fly that has no best case either),
      with a WARNING naming it. PAPER keeps today's booking exactly: entry premium, "P&L approximate" WARNING.
      (c) _stash_quote is STAMPED with the pricing pass that wrote it (_exit_q_seq = the record's _px_seq, which
      _fetch_current_premium advances once per call) and its monotonic time (_exit_q_mono); exit_engine._exit_quote
      ignores a stash from an earlier pass or older than EXIT_QUOTE_MAX_AGE_S, so a tick priced by the live REST
      fallback (which stashes nothing) posts at its fresh mark instead of walking / clamping on an old quote. The
      butterfly's composite quote is stashed for the exit ladder under its OWN keys (_exit_fly_bid / _exit_fly_ask,
      same stamp; r195's _q_* stay record-only), so a fly close declared `walk` can walk (exit_engine v5.6). Paper
      books the mark it is handed and never reads the stash for a price: no booking change. Gate
      tests/check_live_exit_paths.py L1, L2, L5.
v5.26 2026-10-27  OTV5 r46 (PARC.1) — PARC JOINS THE ADMISSION TABLE, AND A CREDIT VERTICAL'S P&L SIGN IS READ FROM ITS
      STRUCTURE. The operator, 2026-10-27: "Call it PARC"; "No shadow mode. We're paper. It trades tomorrow." PARC:
      ENTRY_WINDOWS["PARC"] (11:01-11:03), one open, one try per session, cap-exempt - PARK's rule. _execute_exit's
      credit_signed adds structure.is_credit_vertical(record): PARC is a credit vertical with is_condor_leg = 0 (it pairs
      with nothing, so the pairing gate, the sibling probe and the roll never see it), and the old test read
      is_condor_leg / IronCondorStrategy / is_short_position only. Every row it already signed it still signs (each is
      is_condor_leg = 1). (credit - exit) x contracts x 100. Gate tests/check_parc.py.
v5.25 2026-10-27  OTV5 r42 (EOD.3) — THE CLOSE LINE LOGS THE BOOKED FILL. "✅ Position closed ... exit=" printed the mark it
      was handed (current_premium), not the fill that pnl was computed from: CVX 006f6eca logged exit=$4.28 while the
      ledger booked 1.25. It now prints exit=<fill> mark=<mark>. Log text only. Gate tests/check_eod_expiry_value.py E5.
v5.24 2026-10-26  OTV5 r36 (EOD.2) — AN INTENDED EOD HOLD IS ONE INFO LINE, NOT AN ERROR EVERY TICK. The paper EOD
      close (EOD.1) is held from 15:45 to the 15:55 cross by design, and every manage tick logged it as
      "Exit NOT confirmed ... will retry" at ERROR: AMD 2026-10-26 wrote 60 such lines for f819b0bd. A fill with
      held=True now logs once per trade at INFO and is quiet after; the position stays open and closes at the cross
      exactly as before. Every other unconfirmed exit keeps its ERROR line.
v5.23  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ... (v5.0 was already spent by this file's own history, so the reset lands at v5.23.)
v5.22 2026-10-20  OTV4TEST r310 (LIVE.1 F4.2, MIRROR OF otv4 r496 fcbf104, WA 38.2) — THE LIVE MARK FALLBACK
      SURVIVES THE BROKER'S RATE LIMIT. Measured by r308 tools/probe_live_mark.py (16:05 ET): QQQ priced
      3 of 6, SPX 4 of 6; every answered call priced right, every None with a cause was HTTP 429. A
      structure's legs are now priced in ONE get_market_data_by_type(options=[...]) call; a 429 is
      retried after 0.5 / 1 / 2 s (at most 4 calls, the heartbeat touched before each); any other
      failure is not retried; the warning names the HTTP status; after a spent retry, MARK_COOLDOWN_S
      (10 s) of single tries; answers matched on a normalised symbol key. Mid/mark/last rule and F9's
      ceiling unchanged. Code hunks 3-6 applied verbatim (offset only, no fuzz); header and imports
      placed by hand. Operator 2026-10-20: "Yes to both" (build + re-probe). GATE check_mark_rate_limit.
v5.21 2026-10-18  OTV4TEST r295 (LIVE.2) — flatten_all touches the heartbeat once per position (utils.heartbeat.touch).
v5.20 2026-10-18  OTV4TEST r293 (DELTA.2) — an UNREAD delta on the quoted contract is stored as None and said once
      (_delta_readable False), never as 0.0 flagged readable (audit 10-18 D2). The exits already held on None.
v5.19 2026-10-18  OTV4TEST r288 (PARK.1) — PARK joins the admission table: its window (config.ENTRY_WINDOWS["PARK"],
      11:01-11:03), one open and one try per session, and CAP-EXEMPT - its own budget, outside the morning's catastrophic
      cap (the operator, 2026-10-17: "its own budget outside the morning cap"; "Trade it").
v5.18 2026-10-11  OTV4TEST r270 (PMAP.1, RECORD ONLY) — _manage_one writes one premium-map row per position per minute
      (fill_observers.observe_map) after the mark is fetched; it decides nothing and never raises.
v5.17 2026-10-11  OTV4TEST r268 (DEP.12, mirror of otv4 r478) — _vertical_close_due reads past_close_anchor: credit verticals close at
      12:45 on a 13:00 close, 15:45 on a full day. The operator, 2026-10-11 16:51 ET: "Yes, we want those fixed here too".
v5.16 2026-10-10  OTV4TEST r266 (STOP.1) — A PREMIUM STOP THAT FIRES RESTS AT ITS OWN LEVEL BEFORE IT CHASES (execution/resting_stop.py, PAPER ONLY, OT_RESTING_STOP=trade). _execute_exit: a hard_stop / trail_stop_hit on a single-leg long, with the mark already under its level, BEGINS a rest instead of booking the mark (returns False: the row stays open). _manage_one: each later tick a resting trade is resolved FIRST - a mark back at the level books the LEVEL, a mark 5% of entry under it (emergency) or 120 s books the mark; the end-of-day close abandons the rest. Any other close of a resting trade abandons it. The operator, 2026-10-10: "post a resting order when our stop is hit, wait for price to come back to it"; "I can live with a 5% emergency stop on failed fills"; "120 seconds is fine".
v5.15 2026-10-05  OTV4TEST r254 (OBS.1) — THE PLAN ALWAYS LOOKS, THE STRATEGY IS GATED ON THE HOUR: Breakout, Runaway and the Hunt are OBSERVED from their entry end to 15:40 - asked, recorded LOG-ONLY, never executed (the operator, 2026-10-05: "the plan always looks, but the strategies are gated on the hour of the day"; "Have those blocked TRADES just to Log only"). Here: observing() - pure; the three only, refused ONLY by the window, after its end and before the entries stop, every other gate still binding.
v5.14 2026-10-04  OTV4TEST r246 (LIVE.1 F4, MIRROR OF otv4 r468 f0fd443, WA 38.2) — THE LIVE MARK FALLBACK WORKS: _get_option_mark called session.get, which tastytrade 13.x does not have, so it always raised and the bare except returned None; now get_market_data(EQUITY_OPTION) via sdk_result, mid-else-mark-else-last kept, None outside (0, 1e6), a WARNING once per symbol. The live no-chain fallback dispatches by STRUCTURE: a tent is None, a credit vertical is short minus long (both required - never the short leg's full mark, which would trip a premium stop), butterfly and single unchanged. Code hunks applied verbatim; _get_option_mark getsource identical to f0fd443 (67b546bb); _fetch_current_premium differs ONLY by this tree's r195 comment labels and r209 _delta_readable lines, read and confirmed.
v5.13 2026-10-03  OTV4TEST r209 (EXIT.4) — (1) the management intent's declared pricing is stamped on the record with its
      reason (`_exit_pricing`), and cleared on every tick the plan does not close, so exit_engine prices the
      close from the declaration. (2) A DELTA THAT CANNOT BE READ IS SAID: when the single-leg quote is
      missing or the read raises, current_delta becomes None and a Breakout position (the delta-par exit's
      only reader) WARNS once, and says once when the delta is back. It was `except Exception: pass`.
v5.12 2026-10-03  OTV4TEST r204 (PREM.2) — ORCS JOINS THE ADMISSION TABLE: window config.ENTRY_WINDOWS (09:45-10:30), two of
      the type (one put spread, one call spread), blocks nothing, NOT cap-exempt.
v5.11 2026-10-03  OTV4TEST r195 (AUD.4) — THE EXIT QUOTE AND IV ARE WRITTEN AT THE CONFIRMED CLOSE. trade_logger's
      set_exit_contract had ZERO callers: exit_bid / exit_ask / exit_iv were empty on 237 of 237 closed trades
      (10-03 audit). _fetch_current_premium now notes the structure's bid, ask and IV on the record each tick
      under its own keys (_q_bid/_q_ask/_q_iv - NOT the exit ladder's _exit_bid/_exit_ask, so pricing is
      untouched and a butterfly, which has no ladder quote, is still priced as before), and _execute_exit
      writes them after log_exit. IV = the single leg's, a credit structure's SHORT leg's, a fly's BODY's.
v5.10 2026-10-03  OTV4TEST r191 (AUD.2) — THE EOD ATM-IV FALLBACK WAS NEVER SET. flatten_all called chain.atm_iv(),
      but OptionsChain.atm_iv is a PROPERTY: "'float' object is not callable" on every EOD pass for every
      assignment-risk position since r149 (31 warnings 09-30, 78 on 10-02), so _eod_iv_atm stayed unset and a leg
      with no streamed IV had no IV for the 15:45 resting close. check_eod_schedule E11 passed because its
      fixture made atm_iv a lambda; it now builds the REAL OptionsChain. Fork-only (1-REPORTER: no mainline twin).
v5.9  2026-09-30  OTV4TEST r178 (CAP.2) — THE TWO BUTTERFLIES ARE EXEMPT FROM THE DAILY CATASTROPHIC LOSS CAP. The operator, 2026-09-30: "Allow both flies to fire even if we've hit the cap. Only one of each TYPE per session, not one butterfly per session." `AdmissionRule.cap_exempt` (default False) is True for GEXFLY and ATPFLY only; `decide()` skips the cap universal for a cap-exempt rule and for nothing else, and every other term (orb range, hard close, window, one try per session, one open of its type) still applies to them. `config.ADMISSION_RULES` can turn an exemption OFF and can never GRANT one: main.py's capped branch asks only the butterfly path, so an exemption on any other strategy would read ACTIVE on the board and never be asked.
v5.8  2026-09-26  OTV4TEST r149 (EOD.1) — flatten_all runs the operator's end of day: an ASSIGNMENT-RISK position (a short leg) closes from 15:45, everything else is HELD (and managed) until 15:50; each close carries its own derived label; the tick's spot is stamped on the record as _eod_spot for the resting best-case price; a close still resting or laddering before 15:55 is not a failure (INFO, not ERROR). The admission hard-close refusal text derives from HARD_CLOSE_ET. it also stamps each leg's chain IV (`_eod_iv`) and the chain's ATM IV (`_eod_iv_atm`) beside `_eod_spot`, so the resting price is the position's ESTIMATED VALUE BY 15:55 (operator: "Can we instead estimate their assumed BY 1555 & rest that?").
v5.7  2026-09-26  OTV4TEST r148 (WIN.1) — THE TABLE'S WINDOWS COME FROM config.ENTRY_WINDOWS, the one entry-window table; `config.ADMISSION_RULES` can still override caps and tries but NO LONGER a window (a second window source is WIN.1's defect). TrendCreditSpread's row reads 11:31, the minute its plan actually opened (it said 11:30).
v5.6  2026-09-21  OTV4TEST r78 — ONE OF EACH AT A TIME. r76 read the ruling as
      removing the per-type cap; it was about BLOCKING (strategy vs strategy,
      out by r42/r50) and not CAPPING (a strategy stacking on itself). Live
      cost: 19 Breakout positions / $78,954 in five minutes off ONE opening
      range. ORB, RUNAWAY, HUNT, BREAKOUT and VOLT return to 1; SWEEP keeps 2
      (it pairs into a condor). The operator: *"only one breakout at a time..
      only one orb a time. Only one of each at a time. Sweep is the only one
      that's allowed to have two."* ⚠️ THE Optional[int]/None MACHINERY FROM
      r76 IS KEPT AND UNUSED — the sentinel is correct and check_admission
      drives it; only the TABLE VALUES are restored.
v5.5  2026-09-21  OTV4TEST r76 — NO MAXIMUM NUMBER OF POSITIONS, WITH TWO
      EXCEPTIONS. `max_open_of_type` becomes Optional and None means UNLIMITED,
      matching `max_tries_per_session` in the same dataclass. Six strategies
      carried a silent cap of 1 that no ruling authorised and that was REFUSING
      TRADES LIVE. The operator: *"With rare exception, there are no blocking
      TRADES and no maximum number of positions."* The two exceptions are
      VERTICAL SPREADS (a condor IS two verticals) and the BUTTERFLIES (one per
      session, r178's 2026-08-28 stack of five in ninety seconds).
v5.4  2026-09-21  OTV4TEST r72 (CTRL.1) — VOLT joins the table: 09:35-11:30,
      cap 1, blocking NOTHING and blocked by NOTHING. ⚠️ ITS WINDOW MUST EQUAL
      THE ORB'S OR IT IS NOT A CONTROL — a yardstick measured over a different
      period measures the period. Pinned from both sides by check_admission and
      check_volt_plan V1b.
v5.3  2026-09-20  OTV4TEST r71 (LATE.1) — THE TWO CREDIT WINDOWS CLOSE AT
      15:40, NOT 15:00. The operator's ruling: the late institutional moves he
      has watched repeatedly were unreachable BY CONSTRUCTION — admission shut
      at 15:00, so no plan ever ran and no row records a decline.
      ⚠️ CREDITS ONLY. A debit is flattened by the 15:40 ladder, so widening a
      DEBIT to 15:40 admits a trade into its own flatten window — an entry with
      no hold time at all. `check_late_credit_window` W2/W3 pin that
      structurally, with no literal that can go stale.
v5.2  2026-09-18  OTV4TEST r51 (BRK.1) — Breakout joins the table: 09:35-11:30,
      cap 1, blocking nothing and blocked by nothing. Same window as the ORB it
      is born from and the hunt it is measured against.
v5.1  2026-09-18  OTV4TEST r42 — `logging_state()`: the BINARY AND THE GATE for
      every strategy, from ONE walk of the table. `main.py` used to ask
      `eligible_now()` for the list and `why_not()` per refused strategy for the
      reason — two calls, the same facts passed twice, and nothing making them
      agree. Pass one fact differently to the second and the board names a gate
      that did not refuse: wrong in the log and unfalsifiable from it.
      `eligible_now()` is now a thin view over it, so "eligible" and "why not"
      are two readings of one object rather than two computations.
      ⚠️ STILL PURE, AND DELIBERATELY SO. Nothing is remembered here. The
      operator's "say it once" rule lives in `strategy/plan.py` because
      deduplication is a property of the thing that WRITES ROWS — the only
      thing that knows what it already wrote. A gate that remembered would stop
      being a function of its Facts, and `check_admission.py` could no longer
      drive all 47 combinations without a tick loop or a store.
v5.0  2026-09-17  OTV4TEST r35 — THE ONE AND ONLY POSITION MANAGER: IT KNOWS WHAT
      IS OPEN AND IT DECIDES WHAT MAY OPEN. Operator, 2026-09-17: *"attempt_new_entry
      is a position manager function"*, and earlier, *"the gates for our 1 and only
      position manager"*. Admission was seven mechanisms in four files — an early
      return in main (`is_halted`), a second one (`session_guard.can_enter`), a
      TICK-LOOP BRANCH (`has_open_position`), a hardcoded exemption predicate here,
      a bare dispatch cascade whose ORDER was load-bearing, a window inside each
      plan file, and `_one_per_session_used`. Nothing enumerated them, which is why
      the TCS's 14:00 window shut for twenty-four revisions unnoticed.
      🔴 THE TABLE IS THE OPERATOR'S, AND IT INVERTS THE OLD MODEL. A single GLOBAL
      position slot used to block everything with two hardcoded exemptions.
      **Nothing blocks anything now.** *"To the greatest extent possible I do not
      want to set a maximum number of open positions, and many times this may lead
      to CONFLICTING theses at play simultaneously. That is OK! I WANT sweep to be
      able to fire while we have an active runaway in progress. We will rely on the
      runaway to exit gracefully using ITS OWN stops."* The only structural limit is
      MAX OPEN OF THIS TYPE; there is no cap on the total.
      🔑 THE CONDOR RULES FALL OUT OF THE TYPE CAPS WITH NO SPECIAL CASE: sweep = 2
      permits sweep+sweep, TCS = 1 makes TCS+TCS impossible, TCS+sweep is two types.
      Nothing here knows the word "condor".
      ⚠️ IT ANSWERS, IT DOES NOT DRIVE. `eligible_now()` returns the strategies that
      may be ASKED; `main_loop` does the asking, the plan selects, the strategy
      confirms, execution acts. A position manager that called a plan would be the
      first backwards edge in the one-way flow this repo's isolation depends on.
      ⚠️ IT DOES NOT OWN ORDER PLACEMENT. `session_guard`: *"ORDER PLACEMENT IS NOT
      GATED HERE AT ALL — it is refused at the two order choke points, which check
      `is_rth()` themselves. A gate that says 'no' is not what stops a fill; the
      choke point is."* That separation is a SAFETY PROPERTY and survives intact.
v4.9  2026-09-10  OTV4TEST r12 — has_blocking_position(): THE LIQUIDITY HUNT BLOCKS
      NOTHING (PLAN_SPEC §37), the butterfly's rule applied to a second strategy,
      so the hunt and the ORB run the same break side by side.
v4.8  2026-08-31  r197 — has_blocking_position(): A BUTTERFLY BLOCKS NOTHING.
      r161 exempted it from the single-position rule on ENTRY; nothing made
      that reciprocal, so an open butterfly still threw the box into the
      second-leg-only branch. Cost three boxes their whole credit session on
      2026-08-31. Credit remains blocked by an open ORB or runaway debit —
      that is correct and untouched.
v4.7  2026-08-30  r195 — AN ORB EXIT CANCELS THE STANDING OFFER'S
      REMAINDER BEFORE RE-ARMING THE ENGINE. A partly-filled offer left
      the rest working after ANY exit the supervisor's trigger list did
      not name. The setup ending is the trigger; the exit reason is not.
v4.6  2026-08-27  r167: manage_open_position asks strategy/management.py's
      decide() first; for a covered record its intent (CLOSE / TRAIL / HOLD)
      is executed through the same _execute_exit and trail persistence as
      before. Uncovered records (ORB, ADOPTED, tents, formed condors) go to
      exit_engine.evaluate() exactly as before.
v4.5  2026-08-27  r166: the fetched premium is stamped on the record
      (`current_premium`) so the management plan reads the same number the
      exit engine just decided on.
v4.4  2026-08-27  r161: add_open_position() — append without replacing, for
      the butterfly firing alongside an open vertical.
v4.3  2026-08-24  r99 — flatten_all HOLDS credit verticals until
      VERTICAL_HOLD_TO_ET (15:45). It ran from 15:40 over every record and
      closed them with the debits; the 15:45 hold existed only in
      _evaluate_condor_leg, which the flatten window never reached.
v4.2  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Open-position tracking, pricing and lifecycle.

v4.1  2026-08-20  AUDIT F9: mark filters gain a 1e6 ceiling - NaN was already
      excluded (NaN > 0 is False) but a finite-absurd mark closed positions
      on phantom prints. Fail direction: None -> tick skipped.
v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

execution/position_manager.py — v3.4 — AUDIT A2.2: expose the open condor-leg
SWALLOW T1: this file's silent handler(s) now announce
        themselves once. Behaviour unchanged in every case; only the silence
        was the defect.
        count for the orphan announcement. The F5 warning was wired to a call
        site that cannot run while a leg is open (attempt_new_entry sits
        behind has_open_position, which reads the same DB), so it could never
        fire. The manage branch announces instead, counting from the records
        this manager already holds - no second DB read on the hot path.
v3.2 — AUDIT F6 pairing: price a spread by
        STRUCTURE, not by is_condor_leg. main v6.9 stops stamping
        is_condor_leg=1 onto TC.6 records, and this module's premium fetch
        keyed on exactly that flag (or strategy=="IronCondorStrategy") — so
        without this change a TC.6 record would silently fall to the
        single-leg pricing path. is_credit_vertical() reads only persisted
        columns (strategy / setup_type), so condor legs, both TC.6 row
        generations, and the rolled broken wing all price as short-long.
        Ships in the SAME commit as main v6.9, deliberately.
v3.1 — VEL.1 stashes current_delta
        alongside current_theta: breakeven velocity is |theta|/(|delta|*1440),
        so theta alone cannot answer whether the position is gaining or
        bleeding. Manages the single open options position.
remove the dead PAPER_FILL_SLIPPAGE_PCT import (audit
        defect T). This module has never priced a paper fill — entry pricing
        lives in entry_engine/main and exit pricing in exit_engine, both now
        via execution/limit_ladder. The unused import falsely implied this
        file was a third friction call site. Import-only change.
thread df_5m to exit_engine.evaluate() so trails can
        anchor to 5-minute FVGs (exit_engine v3.8 runner refinements). 1m is
        untouched and remains the structure-stop/BOS timeframe.
BOOK ONLY ON CONFIRMED FILL. _execute_exit() now consumes
        the FillResult from place_exit_order(): it books P&L ONLY when
        fill.confirmed is True and uses fill.fill_price (the ACTUAL close price
        — simulated mark in paper, broker fill in live), never the mark we
        passed nor entry-as-fallback. An unconfirmed result books NOTHING and
        leaves the row OPEN (anti-orphan invariant) so flatten_all's 15:45->16:00
        retry can act. Kills the hard-close $0.00 bookings. flatten_all still
        passes a chain (now supplied by handle_hard_close) so paper has a real
        mark to simulate against.
F5 FIX: trail updates now write to the trail_stop column
        via update_trail_stop() instead of overwriting stop_premium/update_stop.
        stop_premium stays the immutable entry-time -25% floor, so the exit
        engine's floor checks and exit_reason labels are truthful again.
v3.0 — original release
pass df_1m to exit_engine.evaluate() for strategy-aware
        ORB range violation and BOS exits
use live chain marks in paper mode for accurate P&L display;
        butterfly mark computed from lower + upper - 2×center legs
notify ORB engine when an ORB trade closes so it re-arms
        and watches for the next breakout attempt this session
        exits can fire for butterfly and condor leg positions
multi-position support for legged condors: hold up to two
        verticals at once (condor ONLY; every other strategy stays single),
        manage each independently, mark a leg as short_mark - long_mark, and
        invert P&L sign for credit spreads.
add remove_record() for the broken-wing roll (drops the old
        untested vertical when it is rolled).
pass realized P&L into record_win/record_loss so the risk
        manager can track NET daily P&L for the daily loss halt.
set_open_positions(): resume a recovered SET of open rows
        wholesale (1 normally, 2 for a legged condor) so startup recovery
        manages exactly the rows that survived stale-orphan reconciliation
        without dropping a condor leg.
flatten_all(): durable, complete forced close for the 15:45
        hard cutoff. Routes EVERY open record (all condor legs) through the full
        _execute_exit accounting so the DB row is actually marked closed and P&L
        booked — replacing main.py's old direct place_exit_order() that submitted
        an order but never wrote status='closed'. Returns trade_ids that failed
        to close so the caller can retry/escalate.
_fetch_current_premium PAPER fallback fixed: on a chain miss
        it returned the ENTRY premium, so any exit taken during a chain gap booked
        exit==entry (P&L=$0) — a real loss recorded as a scratch, and the exit
        logic blinded to the true premium. Now returns the LAST-KNOWN mark
        (update_current_premium), surrendering to entry only if never priced.
_execute_exit P&L is now credit-signed for an adopted SHORT
        (is_short_position), not just condor legs — so flatten_all/normal exits
        book a broker-adopted short's realized P&L with the correct sign.
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
"""

import logging
import re
import time
from dataclasses import dataclass, field, replace as _dc_replace
from typing import Mapping, Optional, List

import pandas as pd

from database.trade_logger import TradeRecord, get_trade_logger
from strategy.structure import (is_credit_vertical as _is_credit_vertical,
                                is_tent as _is_tent,
                                has_assignment_risk as _has_assignment_risk)   # r149
from execution.exit_engine import get_exit_engine, ExitDecision
from execution import resting_stop as _rs                          # r266 (STOP.1)
from execution import fill_observers as _fo        # r270 (PMAP.1 + FILL.2): record-only observers
from data.tasty_client import get_client, TastyClientError, sdk_result
from risk.risk_manager import get_risk_manager
from notifications.alert_manager import get_alert_manager
import config
from config import PAPER_TRADING, CONTRACT_MULTIPLIER


_WARNED_ONCE: set = set()     # r195: one warning per reason per process


def _quote_stamp(record) -> None:
    """r48 (LIVE.7 c) — stamp a stash with the pricing pass that wrote it and when."""
    try:
        record["_exit_q_seq"] = int(record.get("_px_seq") or 0)
        record["_exit_q_mono"] = time.monotonic()
    except (TypeError, ValueError, AttributeError):
        pass


def _stash_quote(record, bid: float, ask: float) -> None:
    """r105 — put a two-sided quote on the record for the exit ladder.

    ⚠️ IN-MEMORY, NOT A COLUMN. It is read on the same tick it is written and
    is meaningless one tick later; persisting a stale quote would be worse than
    having none. A missing stash makes the exit post at mark, which is exactly
    the pre-r105 behaviour.
    🔴 r48 (LIVE.7 c) — AND "THE SAME TICK" IS NOW CHECKED, NOT ASSUMED. The stash
    was never cleared, and a tick priced by the live REST fallback writes none, so
    the walk and its clamp ran on whatever quote an earlier tick left. It is stamped
    here (_quote_stamp) and exit_engine._exit_quote ignores it unless it was written
    by THIS pricing pass and is under EXIT_QUOTE_MAX_AGE_S old.
    """
    try:
        if ask and ask > 0:
            record["_exit_bid"] = round(float(bid), 4)
            record["_exit_ask"] = round(float(ask), 4)
            _quote_stamp(record)
    except (TypeError, ValueError):
        pass


def _stash_fly_quote(record, bid: float, ask: float) -> None:
    """r48 (LIVE.7) — the butterfly's composite quote FOR THE EXIT LADDER, under its own
    keys (r195's _q_* stay record-only and _exit_bid/_exit_ask stay absent on a fly, so no
    other reader changes). Read only by exit_engine._close_butterfly for a close whose
    pricing is declared `walk`; same stamp and freshness rule as _stash_quote."""
    try:
        if ask and float(ask) > 0:
            record["_exit_fly_bid"] = round(float(bid), 4)
            record["_exit_fly_ask"] = round(float(ask), 4)
            _quote_stamp(record)
    except (TypeError, ValueError):
        pass


def _note_quote(record, bid, ask, iv=None) -> None:
    """r195 (AUD.4) — the structure's two-sided quote and IV at this tick, FOR THE
    RECORD ONLY: `_execute_exit` writes them to trades.exit_bid / exit_ask / exit_iv
    at the confirmed close. ⚠️ DELIBERATELY NOT `_stash_quote`'s keys: those feed the
    exit ladder's pricing (r105), and a butterfly has never had them - recording a
    fly's quote must not change how its exit is priced. In-memory; the newest tick
    wins, so at the close it is the quote the exit decision was made on."""
    try:
        if ask is not None and float(ask) > 0:
            record["_q_bid"] = round(float(bid or 0.0), 4)
            record["_q_ask"] = round(float(ask), 4)
            _iv = float(iv or 0.0)
            record["_q_iv"] = round(_iv, 6) if _iv > 0 else None
    except (TypeError, ValueError):
        pass


def _vertical_close_due() -> bool:
    """r99 — True once credit verticals are due to close. Reads config at call
    time so a test can pin the clock; fails toward FLATTEN on any error."""
    try:
        from config import VERTICAL_HOLD_TO_ET, VERTICAL_HOLD_TO_CLOSE
        from utils.time_utils import now_et, past_close_anchor
        if not VERTICAL_HOLD_TO_CLOSE:
            return True
        # r478 / DEP.12 — 12:45 on a 13:00 close.
        return past_close_anchor(VERTICAL_HOLD_TO_ET, now_et())
    except Exception:                                          # noqa: BLE001
        return True

logger = logging.getLogger(__name__)
_HELD_LOGGED: set = set()      # r36 (EOD.2): trade ids whose intended EOD hold has been named once
_WARNED_LEG_COUNT: set = set()   # SWALLOW T1: warn once on an unreadable count


# ══ ADMISSION ══════════════════════════════════════════════════════════════
# ── the strategies this box runs, by their dispatch names ───────────────────
ORB = "ORBStrategy"
RUNAWAY = "RunawayContinuation"
HUNT = "LiquidityHunt"
BREAKOUT = "Breakout"
SWEEP = "SweepCreditSpread"
TCS = "TrendCreditSpread"
GEXFLY = "GEXPinButterfly"
ATPFLY = "ATPButterfly"
ORCS = "OpeningRangeCreditSpread"     # r204
PARK = "PARK"                         # r288 (PARK.1): the 11:00 first-hour continuation
PARC = "PARC"                         # OTV5 r46 (PARC.1): PARK's entry, a credit spread on the safer side
# r72 — VOLT (VOLume Trade), THE CONTROL ARM. Two gates and nothing else, in
# the same window as the morning four, blocking nothing and blocked by nothing.
# Its purpose is to make the OTHER strategies' gates measurable: if VOLT keeps
# pace, the gates are decoration; if it does not, they are earning their keep.
VOLT = "VOLT"


def _delta_readable(record, ok: bool, why: str = "") -> None:
    """r209 (EXIT.4) — say it ONCE when a single-leg position's delta cannot be read, and once
    when it can again. Breakout's delta-par exit is the reader (management.DELTA_PAR_STRATEGIES):
    with no delta it HOLDS by design, so an unreadable delta silently switches that exit off."""
    try:
        if ok:
            if record.pop("_delta_unreadable", None):
                logger.info("[delta] %s %s: delta is readable again - the delta-par exit is live",
                            str(record.get("trade_id", ""))[:8], record.get("strategy", ""))
            return
        record["current_delta"] = None
        from strategy.management import DELTA_PAR_STRATEGIES
        if record.get("strategy") in DELTA_PAR_STRATEGIES and not record.get("_delta_unreadable"):
            record["_delta_unreadable"] = 1
            logger.warning("[delta] %s %s: delta UNREADABLE (%s) - the delta-par exit is DARK until it "
                           "returns; the structure stop and the premium floor still cover the trade",
                           str(record.get("trade_id", ""))[:8], record.get("strategy", ""), why)
    except Exception:                                           # noqa: BLE001
        pass


@dataclass(frozen=True)
class AdmissionRule:
    """One strategy's admission terms. §36: every field here is SELECTION —
    the operator toggles them as the data arrives. None of them is foundational;
    the FEASIBILITY gate is the catastrophic cap, which is universal except for
    a `cap_exempt` rule (r178: the two butterflies, by ruling)."""
    window: tuple                       # ((sh, sm), (eh, em)), half-open [start, end)
    # 🔑 r76 — `None` MEANS UNLIMITED, matching `max_tries_per_session` in this
    # same dataclass rather than inventing a sentinel. The operator, 2026-09-21:
    # *"With rare exception, there are no blocking TRADES and no maximum number
    # of positions."* Six strategies carried a silent cap of 1 that no ruling
    # ever authorised, and it was refusing trades live.
    max_open_of_type: Optional[int]     # concurrent positions OF THIS TYPE; None = unlimited
    max_tries_per_session: Optional[int] = None      # None = unlimited
    # 🔑 NAMED SETS, NOT BOOLEANS. The operator asked for the blocking gates to
    # be toggleable "to name which strategies will fill those gates", so a future
    # rule is a name added to a set rather than an edit to a conditional.
    # BOTH DIRECTIONS ARE EVALUATED, so a pairing can be expressed from either
    # end and a half-configured matrix cannot silently do nothing.
    blocks: frozenset = field(default_factory=frozenset)      # I block these from opening
    blocked_by: frozenset = field(default_factory=frozenset)  # these block me
    # r178 (CAP.2) — True: the daily catastrophic loss cap does not refuse this
    # strategy. The two butterflies (ruling 2026-09-30) and PARK (r288, 2026-10-17).
    cap_exempt: bool = False


# ── THE TABLE. Operator's specification, 2026-09-17. ────────────────────────
# ⚠️ EVERY WINDOW IS HALF-OPEN [start, end): at 11:30:00 the ORB is OUT and the
# TCS is IN — no overlap, no gap, and no tick that belongs to both or neither.
# ⚠️ EVERY `blocks` / `blocked_by` IS EMPTY BY RULING. Nothing blocks anything.
_DEFAULT_RULES = {
    # ══ r78 — ONE OF EACH AT A TIME. BLOCKING AND CAPPING ARE NOT THE SAME ══
    # r76 READ THE RULING WRONG AND IT COST 19 BREAKOUT POSITIONS / $78,954 IN
    # FIVE MINUTES. The operator's words were *"there are no blocking TRADES
    # and no maximum number of positions"*, and r76 took that to mean the
    # per-type cap. It does not. ⚠️ TWO DIFFERENT MECHANISMS LIVE IN THIS
    # DATACLASS AND r76 CONFLATED THEM:
    #   `blocks`/`blocked_by`  — strategy A refusing strategy B's trade.
    #                            OUT by r42/r50, empty everywhere, STAYS empty.
    #   `max_open_of_type`     — a strategy stacking on ITSELF. Never ruled out,
    #                            and the ruling below puts it back at ONE.
    # The operator, 2026-09-21, watching the stack land: *"I'm OK with the size
    # but it opened 15 positions — only one breakout at a time.. only one orb a
    # time. Only one of each at a time. Sweep is the only one that's allowed to
    # have two."* A second simultaneous copy of the same strategy is not a
    # second observation, it is the SAME observation charged twice: all 20
    # spawned Breakouts read one opening range, one break, one signal.
    ORB:     AdmissionRule(config.ENTRY_WINDOWS[ORB], max_open_of_type=1),
    RUNAWAY: AdmissionRule(config.ENTRY_WINDOWS[RUNAWAY], max_open_of_type=1),
    HUNT:    AdmissionRule(config.ENTRY_WINDOWS[HUNT], max_open_of_type=1),
    # r51 (BRK.1) — the 5-minute opening-range break taken WITHOUT a retest.
    # Same window as the ORB it is born from and the hunt it competes with,
    # because all three read the same opening range. ⚠️ NOTHING BLOCKS IT AND IT
    # BLOCKS NOTHING — the operator ruled the blocking paradigm out entirely
    # (r50): *"every trade to be 'right' in its own time… I don't see any reason
    # to stop it from firing if it cleared the bar, even if the thesis is the
    # opposite of an existing open trade."* The head-to-head against ORB and the
    # hunt is the POINT, and hierarchy would destroy the counterfactual that
    # makes it readable.
    BREAKOUT: AdmissionRule(config.ENTRY_WINDOWS[BREAKOUT], max_open_of_type=1),
    # the credit window was widened to 15:00 by the operator on 2026-09-17
    # 🔴 r71 — AND TO 15:40 ON 2026-09-20, FOR THE LATE-DAY MOVE. Operator:
    # *"I've seen multiple end of day moves now that I'm convinced smart money
    # is intentionally placing those orders to keep zero DTE traders out of it.
    # Well, I'll have none of that."* Evidenced on 2026-09-16: QQQ fell 11.66
    # points from 711.78 (11:47) to 700.12 (15:27); a london support was
    # REJECTED at 14:53 then ACCEPTED THROUGH at 14:57:45 with three more
    # supports wicked one second later, and chain net GEX crossed zero into
    # TRENDING at 15:00:15 with 5.2 points still to come. **The sweep — the
    # strategy that exists to trade swept levels — was DORMANT from 14:00**
    # ("entry_window: past 14:00 ET — observing only") and the box took NO
    # position in the direction of the day's defining move.
    # ⚠️ ONLY THE CREDIT PAIR IS WIDENED, AND THAT IS THE FLATTEN RULES
    # DECIDING IT RATHER THAN A PREFERENCE. `FLATTEN_WINDOW_OPEN_ET` is 15:40
    # and DEBIT positions start flattening there; credit verticals are exempt
    # and hold to `VERTICAL_HOLD_TO_ET`. Both butterflies are DEBIT structures
    # — measured on the book, `net_debit` 0.26 and 0.47 with `credit_received`
    # 0.0 on both — so a 15:40 entry would open them into their own ladder and
    # hold nothing. The operator's own reasoning arrived here first: *"in order
    # to properly harvest a late move like that we would have to use Credit
    # spreads."*
    # r72 — VOLT sits in the MORNING slot with the ORB, runaway, hunt and
    # breakout. ⚠️ THE WINDOW MUST MATCH THEIRS OR IT IS NOT A CONTROL — a
    # yardstick measured over a different period measures the period.
    # blocks/blocked_by are EMPTY by construction (r51's ruling: under a
    # cascade the losing arm's outcome is unobservable).
    VOLT:    AdmissionRule(config.ENTRY_WINDOWS[VOLT], max_open_of_type=1),
    SWEEP:   AdmissionRule(config.ENTRY_WINDOWS[SWEEP], max_open_of_type=2),  # 2: it forms a condor
    # ══ EXCEPTION 1 of 2 — VERTICAL SPREADS ════════════════════════════════
    # A condor IS two credit verticals, so the number is the STRUCTURE and not
    # a risk limit. The pairs are sweep-sweep or TCS-sweep, never TCS-TCS, which
    # is why the sweep may hold two of its own and the TCS may not.
    TCS:     AdmissionRule(config.ENTRY_WINDOWS[TCS], max_open_of_type=1), # 1: TCS+TCS is in conflict; pairs only with a sweep
    # the GEX fly's cutoff was raised from 14:00 to 15:00 by the operator
    # ══ EXCEPTION 2 of 2 — THE BUTTERFLIES, ONE PER SESSION ════════════════
    # r178: on 2026-08-28 at 15:00 a stack of FIVE BUTTERFLIES fired in NINETY
    # SECONDS on the same pin. `max_tries_per_session=1` is the admission half
    # of that guard; `mark_pin_played` is the other.
    GEXFLY:  AdmissionRule(config.ENTRY_WINDOWS[GEXFLY], max_open_of_type=1, max_tries_per_session=1, cap_exempt=True),
    ATPFLY:  AdmissionRule(config.ENTRY_WINDOWS[ATPFLY], max_open_of_type=1, max_tries_per_session=1, cap_exempt=True),
    # r204 — ORCS: one put spread and one call spread, so two of the type; it blocks nothing.
    ORCS:    AdmissionRule(config.ENTRY_WINDOWS[ORCS], max_open_of_type=2),
    # r288 (PARK.1) — one per session, and its own budget: the cap neither refuses it nor counts its P&L
    # (config.CAP_EXCLUDED_STRATEGIES).
    PARK:    AdmissionRule(config.ENTRY_WINDOWS[PARK], max_open_of_type=1, max_tries_per_session=1, cap_exempt=True),
    # OTV5 r46 (PARC.1) — PARK's rule: one per session, its own budget (CAP_EXCLUDED_STRATEGIES), cap-exempt.
    PARC:    AdmissionRule(config.ENTRY_WINDOWS[PARC], max_open_of_type=1, max_tries_per_session=1, cap_exempt=True),
}


def rules() -> dict:
    """The table, with `config.ADMISSION_RULES` overlaid when present.

    🔑 TOGGLED WITHOUT A REVISION. The operator: *"I want to be able to toggle
    those granular details LATER. For instance, after we have enough data, I will
    toggle it back to only 1 butterfly trade at a time."* An override names a
    strategy and any subset of its fields; everything unnamed keeps the default,
    so a partial override cannot blank a rule by omission."""
    out = dict(_DEFAULT_RULES)
    ov = getattr(config, "ADMISSION_RULES", None) or {}
    for name, patch in ov.items():
        base = out.get(name)
        if base is None or not isinstance(patch, dict):
            continue
        out[name] = AdmissionRule(
            window=base.window,   # r148: windows come ONLY from config.ENTRY_WINDOWS
            max_open_of_type=(None if patch.get("max_open_of_type", base.max_open_of_type) is None
                              else int(patch["max_open_of_type"])
                              if "max_open_of_type" in patch else base.max_open_of_type),
            max_tries_per_session=patch.get("max_tries_per_session", base.max_tries_per_session),
            blocks=frozenset(patch.get("blocks", base.blocks)),
            blocked_by=frozenset(patch.get("blocked_by", base.blocked_by)),
            # r178: an override can switch an exemption OFF, never grant one.
            cap_exempt=bool(base.cap_exempt and patch.get("cap_exempt", True)),
        )
    return out


@dataclass(frozen=True)
class Facts:
    """Everything admission depends on, gathered by the caller.

    ⚠️ FACTS, NOT OBJECTS — passing values rather than the risk manager and the
    position manager is what keeps this pure, and what lets a checker drive every
    combination without a tick loop or a store."""
    strategy: str
    now_et: tuple                        # (hour, minute)
    trading_day: bool = True
    orb_established: bool = False
    cap_intact: bool = True
    past_hard_close: bool = False
    open_by_strategy: Mapping[str, int] = field(default_factory=dict)
    tries_used: int = 0


@dataclass(frozen=True)
class Verdict:
    admitted: bool
    gate: str = ""
    why: str = ""

    def __bool__(self) -> bool:
        return self.admitted


def _within(now: tuple, window: tuple) -> bool:
    (sh, sm), (eh, em) = window
    t = now[0] * 60 + now[1]
    return (sh * 60 + sm) <= t < (eh * 60 + em)      # half-open, deliberately


def decide(f: Facts, table: Optional[dict] = None) -> Verdict:
    """ADMIT, or the FIRST gate that refuses.

    THE THREE UNIVERSALS ARE ASKED ONCE, FOR EVERY STRATEGY, and they are the
    operator's own list: is today a trading day, is the ORB range established,
    is the catastrophic cap unbroken (r178: a `cap_exempt` rule, the two
    butterflies, is not refused by the cap). The hard close rides with them.
    ⚠️ THE VIX CRISIS GATE IS GONE, and that is a ruling, not an omission.
    Operator, 2026-09-17: *"VIX crisis — get rid of it. That is major
    opportunity."* It previously refused every new entry on `macro`'s say-so.
    """
    table = table if table is not None else rules()

    # ── the universals ──────────────────────────────────────────────────────
    if not f.trading_day:
        return Verdict(False, "trading_day", "not a trading day")
    if not f.orb_established:
        # the universal floor for EVERY strategy: nothing trades inside the
        # opening range, and the ORB itself cannot be read before it exists.
        return Verdict(False, "orb_range", "opening range not established yet")
    # r178 (CAP.2): the cap refuses every strategy except a cap-exempt one (the
    # two butterflies). An unknown strategy has no rule and is refused here too.
    if not f.cap_intact and not getattr(table.get(f.strategy), "cap_exempt", False):
        return Verdict(False, "catastrophic_cap", "catastrophic cap reached — no new entries")
    if f.past_hard_close:
        from config import HARD_CLOSE_ET as _HCE
        return Verdict(False, "hard_close", "past the %02d:%02d ET hard close" % tuple(_HCE))

    rule = table.get(f.strategy)
    if rule is None:
        # ⚠️ FAILS CLOSED (§22). An unknown strategy is not admitted by default;
        # a new trade joins the table deliberately or it does not trade.
        return Verdict(False, "unknown_strategy", f"{f.strategy} has no admission rule")

    # ── the per-strategy terms ──────────────────────────────────────────────
    if not _within(f.now_et, rule.window):
        (sh, sm), (eh, em) = rule.window
        return Verdict(False, "window",
                       f"{f.strategy} is outside {sh:02d}:{sm:02d}-{eh:02d}:{em:02d} ET")

    if rule.max_tries_per_session is not None and f.tries_used >= rule.max_tries_per_session:
        return Verdict(False, "tries_per_session",
                       f"{f.strategy} has used its {rule.max_tries_per_session} attempt(s)")

    # r76 — None is UNLIMITED. Only the two exceptions carry a number.
    if (rule.max_open_of_type is not None
            and int(f.open_by_strategy.get(f.strategy, 0)) >= rule.max_open_of_type):
        return Verdict(False, "max_open_of_type",
                       f"{rule.max_open_of_type} {f.strategy} already open")

    # ── the blocking matrix, BOTH directions, empty by ruling ───────────────
    open_now = {s for s, n in f.open_by_strategy.items() if int(n) > 0}
    hit = open_now & set(rule.blocked_by)
    if hit:
        return Verdict(False, "blocked_by", f"{f.strategy} is blocked by {sorted(hit)[0]} being open")
    for other in sorted(open_now):
        other_rule = table.get(other)
        if other_rule is not None and f.strategy in other_rule.blocks:
            return Verdict(False, "blocks", f"{other} is open and blocks {f.strategy}")

    return Verdict(True, "", "admitted")


def gates() -> tuple:
    """Every gate this can refuse on, in order — so admission can be ENUMERATED
    by a reader, a report and a checker instead of rediscovered.
    ⚠️ The absence of this list is why the seven layers were never counted."""
    return ("trading_day", "orb_range", "catastrophic_cap", "hard_close",
            "unknown_strategy", "window", "tries_per_session",
            "max_open_of_type", "blocked_by", "blocks")


class PositionManager:
    """
    Manages the bot's single open position (one trade at a time).
    Fetches live option premium, evaluates exits, and closes when triggered.
    """

    SHADOW = False      # r57 (TCS.LOG1): True only on execution/shadow_book.ShadowPositionManager

    def __init__(self, paper_trading: bool = PAPER_TRADING):
        self.paper_trading = paper_trading
        self._open_records: List[TradeRecord] = []
        self._trade_logger = get_trade_logger()

    def _exit_engine(self):
        """r57 (TCS.LOG1) — the exit engine this manager decides and closes with (the shadow book has its own)."""
        return get_exit_engine(self.paper_trading)

    def _management(self):
        """r57 (TCS.LOG1) — the management plan this manager asks first (the shadow book's writes its own rows)."""
        from strategy.management import get_management_plan
        return get_management_plan()

    def open_condor_leg_count(self) -> int:
        """Open condor legs among the records this manager holds (A2.2).

        Counts from `_open_records` when loaded (the manage branch runs right
        after they are), falling back to the DB on a cold call. Returns 0 on
        any error: this feeds an ANNOUNCEMENT, and the occupancy guards
        elsewhere already fail closed - a missed log line costs less than a
        crashed tick."""
        try:
            recs = self._open_records or self._trade_logger.get_open_trades()
            return sum(1 for r in recs if r.get("is_condor_leg"))
        except Exception as exc:                               # noqa: BLE001
            # ⚠️ SWALLOW T1, 2026-08-17 — THIS RETURNED 0 SILENTLY, AND 0 IS THE
            # PERMISSIVE ANSWER. "No condor legs open" is what a caller checks
            # before opening another; a failed COUNT therefore reads as CLEAR TO
            # PROCEED. That is the F5 shape exactly — an unreadable input
            # granting permission it never established.
            # The count is left at 0 (callers treat a raise as fatal and this
            # runs on the tick path) but it is NO LONGER SILENT: a box that
            # cannot count its own open legs must be visible before it acts on
            # the answer.
            if not _WARNED_LEG_COUNT:
                _WARNED_LEG_COUNT.add(1)
                logger.warning(
                    "[legs] could not count open condor legs (%s) - reporting 0, "
                    "which reads as NO LEGS OPEN to every caller. If a leg IS "
                    "open, deferral and sibling checks are running blind.", exc)
            return 0

    @staticmethod
    def _is_liquidity_hunt(record) -> bool:
        """OTV4TEST r12 — the liquidity hunt runs in PARALLEL with the ORB and
        never blocks (PLAN_SPEC §37); reads the ROW, like the butterfly."""
        try:
            return bool(record.get("is_liquidity_hunt", 0)) or \
                str(record.get("strategy") or "") == "LiquidityHunt"
        except Exception:                                       # noqa: BLE001
            return False

    @staticmethod
    def _is_butterfly(record) -> bool:
        """A GEX pin butterfly. Reads the ROW, not the strategy name.

        ⚠️ The column is the fact; `strategy` is a label that has been
        rewritten before. `is_butterfly` is set at the record builder and is
        what every other consumer keys on.
        """
        try:
            return bool(record.get("is_butterfly", 0))
        except Exception:                                       # noqa: BLE001
            return False

    # ══ ADMISSION, ANSWERED FROM THE STATE THIS OBJECT ALREADY HOLDS ══════
    def open_by_strategy(self) -> dict:
        """{strategy: open count} across the records this manager holds.

        Counts from `_open_records` when loaded, falling back to the DB on a cold
        call — the same shape as `open_condor_leg_count`, deliberately.
        ⚠️ FAILS CLOSED, AND THAT IS THE OPPOSITE OF THE LEG COUNT'S CHOICE. An
        empty dict reads to `decide()` as NOTHING IS OPEN, which is the PERMISSIVE
        answer — the F5 shape that swallow T1 was written about. So a failure
        raises rather than returning {}: a box that cannot count its own open
        positions must not be told it is clear to open another."""
        recs = self._open_records
        if not recs:
            recs = self._trade_logger.get_open_trades()
        out: dict = {}
        for r in (recs or []):
            name = (r.get("strategy") if isinstance(r, dict) else getattr(r, "strategy", "")) or ""
            if name:
                out[name] = out.get(name, 0) + 1
        return out

    def logging_state(self, now_et: tuple, *, trading_day: bool = True,
                      orb_established: bool = False, cap_intact: bool = True,
                      past_hard_close: bool = False,
                      tries_used: Optional[Mapping[str, int]] = None,
                      table: Optional[dict] = None) -> dict:
        """{strategy: (active: bool, gate: str, why: str)} — ONE PASS, ONE TRUTH.

        ACTIVE   — the plan is asked this tick and logs per tick.
        INACTIVE — not asked; `gate` NAMES the rule that refused it
                   ("window", "max_open_of_type", "tries_per_session",
                   "catastrophic_cap", "orb_range", "blocked_by", …).

        🔑 WHY THIS REPLACED TWO CALLS. `main.py` used to ask `eligible_now()`
        for the LIST and then `why_not()` per refused strategy for the REASON —
        two calls, the same facts passed twice, and nothing making them agree.
        That is a seam: pass a slightly different fact to the second call and
        the board reports a gate that is not the one that actually refused,
        which is unfalsifiable from the log. One call, one object, and they
        cannot diverge.

        ⚠️ STILL PURE. This is `decide()` over the whole table and NOTHING IS
        REMEMBERED — same facts in, same map out. That purity is the reason
        `check_admission.py` can drive all 47 combinations with no tick loop and
        no store, and it is why the "say it once" half of the operator's ruling
        lives in `strategy/plan.py` and NOT here: deduplication is a property of
        the thing that WRITES ROWS, which is the only thing that knows what it
        already wrote. A gate that remembered would stop being testable.
        """
        tbl = table if table is not None else rules()
        tried = dict(tries_used or {})
        openmap = self.open_by_strategy()
        out: dict = {}
        for name in tbl:
            v = decide(Facts(strategy=name, now_et=now_et, trading_day=trading_day,
                             orb_established=orb_established, cap_intact=cap_intact,
                             past_hard_close=past_hard_close,
                             open_by_strategy=openmap,
                             tries_used=int(tried.get(name, 0))), tbl)
            out[name] = (bool(v.admitted), v.gate, v.why)
        return out

    def observing(self, now_et: tuple, state: Mapping, *, trading_day: bool = True,
                  orb_established: bool = False, cap_intact: bool = True,
                  past_hard_close: bool = False,
                  tries_used: Optional[Mapping[str, int]] = None,
                  table: Optional[dict] = None) -> list:
        """r254 (OBS.1) - the strategies to OBSERVE this tick: asked, recorded, never executed.

        The operator, 2026-10-05: "the plan always looks, but the strategies are gated on the
        hour of the day." A name qualifies only when ALL hold:
          · it is in strategy/observe.OBSERVE_AFTER_WINDOW (his scope: the three r187 cut);
          · `state` (this tick's logging_state) refused it on the gate "window" and nothing else;
          · now is AT OR AFTER its window's end and BEFORE the entries stop (15:40) - never
            before its window opens;
          · `decide()` ADMITS it when only its window's end is moved to the entries stop, so
            every other gate (cap, hard close, max open of type, tries, blocking) still binds.
        ⚠️ PURE, like logging_state: same facts in, same list out, nothing remembered.
        """
        try:
            from strategy.observe import OBSERVE_AFTER_WINDOW as _scope
            from config import EOD_SCHEDULE as _eod
            stop = tuple(_eod["entries_stop"])
        except Exception:                                       # noqa: BLE001
            return []                                           # fails closed: observe nothing
        tbl = table if table is not None else rules()
        tried = dict(tries_used or {})
        openmap = self.open_by_strategy()
        t = now_et[0] * 60 + now_et[1]
        out: list = []
        for name in _scope:
            ok, gate, _why = (state or {}).get(name, (True, "", ""))
            rule = tbl.get(name)
            if ok or gate != "window" or rule is None:
                continue
            (eh, em) = tuple(rule.window[1])
            if not ((eh * 60 + em) <= t < (stop[0] * 60 + stop[1])):
                continue
            ext = dict(tbl)
            ext[name] = _dc_replace(rule, window=(tuple(rule.window[0]), stop))
            v = decide(Facts(strategy=name, now_et=now_et, trading_day=trading_day,
                             orb_established=orb_established, cap_intact=cap_intact,
                             past_hard_close=past_hard_close, open_by_strategy=openmap,
                             tries_used=int(tried.get(name, 0))), ext)
            if v.admitted:
                out.append(name)
        return out

    def eligible_now(self, now_et: tuple, **kw) -> list:
        """The strategies that MAY BE ASKED this tick, in table order.

        🔑 IT ANSWERS, IT DOES NOT DRIVE. The caller iterates this list and asks
        each plan; this never reaches into `strategy/`. That is what keeps the
        one-way flow intact — position manager feeds the plans, the plans feed
        the strategies.
        ⚠️ A THIN VIEW OF `logging_state()` SINCE r42, deliberately: when the
        list and the reasons came from two separate walks of the table they
        could disagree about the same tick. There is one walk now and this is
        a filter over its result, so "eligible" and "why not" are two readings
        of one object rather than two computations.
        """
        return [n for n, (ok, _g, _w) in self.logging_state(now_et, **kw).items() if ok]

    def why_not(self, strategy: str, now_et: tuple, **kw):
        """The Verdict for ONE strategy — the named gate that refused it.

        For the journal and the operator, so a row can say WHICH gate rather
        than "blocked". Same inputs as `eligible_now`, one strategy."""
        kw.setdefault("open_by_strategy", self.open_by_strategy())
        return decide(Facts(strategy=strategy, now_et=now_et, **kw))

    def has_blocking_position(self) -> bool:
        """Does an open position BLOCK a new entry? A butterfly never does.

        🔑 r197 — THE RECIPROCAL OF r161, WHICH WAS ONLY EVER BUILT ONE WAY.
        r161 exempted the butterfly from the single-position rule ON ENTRY
        (operator: *"I want it to be able to fire regardless if any other open
        trades are found"*, TRADES.md §3: *"no position slot, no capital, no
        competition"*). But `has_open_position()` still counted it, so a
        butterfly took no slot going IN and occupied one once it was THERE.

        ⚠️ MEASURED COST, 2026-08-31, the first live-fleet session: three
        boxes — MU, NFLX, TSLA — held 09:45 butterflies and every one sat in
        the second-leg-only branch when the credit windows opened at 11:30.
        `CondorManagement=HOLD(no credit verticals open)` on all three, so
        nothing credit-side was open to justify it. One rare opportunistic
        trade removed three boxes from the credit side for the whole session.

        ⚠️ WHAT THIS DOES **NOT** CHANGE, and the operator was explicit: credit
        entries stay blocked while an ORB or runaway DEBIT is open. That block
        is correct and untouched. The only thing that stops counting is the
        butterfly. A box may hold a butterfly PLUS one other thing — never a
        butterfly plus a directional debit plus a credit leg.
        """
        # ⚠️ HYDRATE FIRST. On a fresh process `_open_records` is empty until
        # something reloads it, so asking this before `has_open_position()`
        # would answer "nothing blocks" on a box that restarted holding an ORB
        # position — and let a credit trade open against it.
        self.has_open_position()
        return any(not (self._is_butterfly(r) or self._is_liquidity_hunt(r))
                   for r in self._open_records)

    def has_open_position(self) -> bool:
        if self._open_records:
            return True
        # Fresh process (restart): reload any open trades from the DB.
        trades = self._trade_logger.get_open_trades()
        if trades:
            self._open_records = trades
            return True
        return False

    def set_open_position(self, record: TradeRecord):
        """Single-position strategies (ORB, sweep, butterfly): exactly one."""
        self._open_records = [record]

    def set_open_positions(self, records: List[TradeRecord]):
        """Resume managing a recovered SET of open positions (one for normal
        strategies, two for a legged condor). Replaces the active set wholesale.
        Used by startup recovery so the first tick manages exactly the rows that
        survived stale-orphan reconciliation — without dropping a condor leg."""
        self._open_records = list(records)

    def flatten_all(self, reason: str = "", chain=None, spot: Optional[float] = None) -> List[str]:
        """Force-close EVERY open record through the full exit accounting.

        Unlike a bare exit_engine.place_exit_order() (which submits/simulates an
        order but never marks the DB row closed), this routes each record through
        _execute_exit() so status='closed', P&L, the exit alert, trail cleanup
        and ORB re-arm all happen — the row is genuinely, durably closed. Closes
        ALL records (both condor legs), not just the first. If a live mark can't
        be fetched, books at entry premium as a last resort so the row still
        closes rather than surviving as an orphan (P&L approximate — logged).

        Returns the list of trade_ids that FAILED to close (empty == fully flat),
        so the 15:45 caller can retry each tick and escalate.
        """
        if not self._open_records:
            self._open_records = self._trade_logger.get_open_trades()

        # r149 (EOD.1) — the operator's schedule: assignment risk closes from
        # 15:45 (resting best case), everything else is HELD (and managed) until
        # 15:50 (ladder); before 15:55 an unfilled close is RESTING, not failed.
        from utils.time_utils import eod_close_due, now_et as _now_et
        from execution.exit_engine import _eod_label
        from execution.limit_ladder import hard_close_order_mode
        _crossing = hard_close_order_mode(_now_et()) == "market"
        failed: List[str] = []
        held: List[str] = []
        resting: List[str] = []
        from utils.heartbeat import touch as _hb_touch   # r295 (LIVE.2)
        for record in list(self._open_records):
            _hb_touch("flatten")
            trade_id = record.get("trade_id", "")
            # 🔴 r99 — CREDIT VERTICALS HOLD TO VERTICAL_HOLD_TO_ET (15:45).
            # This loop ran from 15:40 (FLATTEN_WINDOW_OPEN) over EVERY record,
            # so the operator's 2026-08-13 ruling — "5 more minutes of
            # exponentially rising profit curve" — was documented in config
            # and enforced nowhere on this path. A held vertical is still
            # MANAGED in that window (main.py runs a manage pass); it is not
            # flattened. Fail direction: a bad clock read -> flatten (the
            # pre-r99 behaviour), never an overnight orphan.
            # r149 — the r99 hold, generalised: WHICH positions are held is now
            # the operator's assignment-risk split, not "credit verticals".
            if not eod_close_due(_has_assignment_risk(record)):
                held.append(trade_id)
                continue
            if spot:
                record["_eod_spot"] = float(spot)
            # r149 — each leg's chain IV (and the chain's ATM IV as the fallback),
            # for the resting price's estimate of the position's value BY 15:55.
            if chain is not None:
                try:
                    _ivs = {c.symbol: float(c.iv or 0.0) for c in (list(chain.calls or []) + list(chain.puts or []))
                            if getattr(c, "symbol", "")}
                    _legs = [record.get(k) for k in ("option_symbol", "short_symbol", "long_symbol",
                                                     "lower_symbol", "center_symbol", "upper_symbol")]
                    record["_eod_iv"] = {s: _ivs[s] for s in _legs if s and _ivs.get(s)}
                    record["_eod_iv_atm"] = float(chain.atm_iv or 0.0)   # r191: a PROPERTY, not a call
                except Exception as _ive:                          # noqa: BLE001
                    logger.warning(f"EOD: chain IV unreadable for {trade_id[:8]} ({_ive}) — expiry value")
            reason = _eod_label(record)
            premium = self._fetch_current_premium(record, chain=chain)
            if premium is None and not self.paper_trading:
                # 🔴 r48 (LIVE.7 b) — LIVE INVENTS NO MARK. The entry premium handed on as
                # the mark made the live close post a limit AT ENTRY (a sell at entry is
                # marketable when the option trades above it). None routes it the way a
                # no-mark close already routes (LIVE.1 F3): nothing posted before the 15:55
                # cross, and the cross closes it.
                logger.warning(
                    f"Flatten {trade_id[:8]}: no live mark — LIVE: no mark invented; routed "
                    f"as a no-mark close (nothing posted before the 15:55 cross; the cross "
                    f"closes it)."
                )
            elif premium is None:
                premium = float(record.get("entry_premium", 0.0) or 0.0)
                logger.warning(
                    f"Flatten {trade_id[:8]}: no live mark — booking at entry "
                    f"premium (P&L approximate) so the row still closes."
                )
            decision = ExitDecision(should_exit=True, exit_reason=reason)
            if self._execute_exit(record, decision, premium):
                self._open_records = [r for r in self._open_records
                                      if r.get("trade_id") != trade_id]
            elif not _crossing:
                resting.append(trade_id)
                logger.info(f"EOD close {trade_id[:8]} resting/laddering ({reason}) — re-priced next tick")
            else:
                failed.append(trade_id)
                logger.error(f"Flatten FAILED for {trade_id[:8]} past the cross — will retry")
        if held:
            logger.info("EOD: %d position(s) without assignment risk HELD to the 15:50 ladder (%s)",
                        len(held), ",".join(t[:8] for t in held))
        return failed

    def add_condor_leg(self, record: TradeRecord):
        """A condor vertical: appends rather than replacing."""
        self._open_records.append(record)

    def add_open_position(self, record: TradeRecord):
        """r161 — the GEX pin butterfly is exempt from the single-position rule
        (operator, 2026-08-27: *"I want it to be able to fire regardless if
        any other open trades are found … If it can achieve all that, it's
        earned an entry."* TRADES.md §3: *"no position slot, no capital, no
        competition."*). Appends; NEVER replaces — `set_open_position` would
        silently drop the vertical already under management."""
        tid = record.get("trade_id") if hasattr(record, "get") else None
        if tid and any(r.get("trade_id") == tid for r in self._open_records):
            return
        self._open_records.append(record)

    def get_open_record(self) -> Optional[TradeRecord]:
        return self._open_records[0] if self._open_records else None

    def get_open_records(self) -> List[TradeRecord]:
        return list(self._open_records)

    def remove_record(self, trade_id: str):
        """Drop a record from active management (used by the broken-wing roll
        when it closes the old untested vertical)."""
        self._open_records = [r for r in self._open_records
                              if r.get("trade_id") != trade_id]

    def manage_open_position(self,
                              df_1m: Optional[pd.DataFrame] = None,
                              chain=None,
                              df_5m: Optional[pd.DataFrame] = None,
                              vol_state=None, trend=None) -> bool:
        """Manage every open position this tick. Normally one; for a legged
        condor there can be two verticals open at once, each managed
        independently (a tested side exits on its own; the untested side
        stays)."""
        if not self._open_records:
            self._open_records = self._trade_logger.get_open_trades()
            if not self._open_records:
                return False

        still_open: List[TradeRecord] = []
        for record in list(self._open_records):
            if self._manage_one(record, df_1m, chain, df_5m, vol_state, trend):
                still_open.append(record)
        self._open_records = still_open
        return len(self._open_records) > 0

    def _manage_one(self, record: TradeRecord,
                    df_1m: Optional[pd.DataFrame],
                    chain,
                    df_5m: Optional[pd.DataFrame] = None,
                    vol_state=None, trend=None) -> bool:
        """Manage one record. Returns True if it should remain open."""
        trade_id = record["trade_id"]

        current_premium = self._fetch_current_premium(record, chain)
        if current_premium is None:
            logger.warning(
                f"Could not fetch premium for {trade_id[:8]} — skipping tick"
            )
            return True

        self._trade_logger.update_current_premium(trade_id, current_premium)
        # r166 — the management plan reads the record, not the DB
        record["current_premium"] = current_premium
        # r270 (PMAP.1, RECORD ONLY) — one premium-map row per position per minute; decides nothing, never raises.
        _fo.observe_map(record, current_premium, getattr(chain, "spot_price", None))

        exit_eng = get_exit_engine(self.paper_trading)
        if getattr(self, "SHADOW", False) is True:                                      # r57 (TCS.LOG1): the shadow book's own engine
            exit_eng = self._exit_engine()
        # ── r266 (STOP.1) — A RESTING STOP IS RESOLVED BEFORE ANYTHING ELSE ──
        # The stop already fired; this tick only decides WHICH price paper books.
        try:
            if _rs.is_resting(trade_id):
                from execution.exit_engine import _eod_due
                if _eod_due(record):
                    _rs.abandon(trade_id, "the end-of-day close governs")
                else:
                    _act = _rs.step(trade_id, current_premium)
                    if _act is None:
                        return True                                  # still resting
                    _px, _label, _st = _act
                    _d = ExitDecision(should_exit=True,
                                      exit_reason=f"{_st['reason']} | rested: {_label}")
                    _closed = self._execute_exit(record, _d, _px, _rested=True)
                    if _closed:
                        _rs.finish(trade_id, _px, _label)
                    return not _closed
        except Exception as _rse:                                    # noqa: BLE001
            logger.error(f"resting stop for {trade_id[:8]} raised ({_rse}) - abandoning it; "
                         f"the normal exit path decides")
            try:
                _rs.abandon(trade_id, f"raised: {_rse}")
            except Exception:                                        # noqa: BLE001
                pass
        # ── r167 — THE MANAGEMENT PLAN DECIDES FIRST for the records it covers
        # (runaway, butterfly, a lone sweep/TCS vertical). It asserts the
        # declared spec conditions itself (15% floor / hard stop, the breach
        # stops, target, nickel) and reaches the engine's calculators (50%
        # trail, tightening after 100%, theta bleed, velocity stall) through
        # evaluate(); its intent is executed below by the SAME _execute_exit.
        # ORB, ADOPTED, tents and formed condors: the engine decides as ever.
        decision = None
        try:
            from strategy.management import get_management_plan
            if getattr(self, "SHADOW", False) is True:                                  # r57 (TCS.LOG1): the shadow rows' plan
                get_management_plan = self._management               # noqa: F811
            _intent = get_management_plan().decide(
                record, current_premium, df_1m=df_1m, open_records=self._open_records,
                current_price=record.get("current_price"),
                ctx={"df_5m": df_5m, "vol": vol_state, "trend": trend,
                     "derived_engines": getattr(self, "_derived_engines", None) or []},
                exit_engine=exit_eng)
            if _intent is not None:
                decision = _intent.to_exit_decision()
            # r209 — the declared pricing rides with ITS reason; any other tick clears it
            if _intent is not None and _intent.action == "CLOSE" and getattr(_intent, "pricing", None):
                record["_exit_pricing"] = (_intent.reason, _intent.pricing)
            else:
                record.pop("_exit_pricing", None)
        except Exception as _mp_err:                            # noqa: BLE001
            logger.warning(f"management plan decide() failed for {trade_id[:8]}: "
                           f"{_mp_err} — the exit engine decides")
            decision = None
        if decision is None:
            decision = exit_eng.evaluate(record, current_premium, df_1m=df_1m, df_5m=df_5m,
                                         vol_state=vol_state, trend=trend)

        if decision.new_trail_stop is not None:
            # v3.1: trail persists in its OWN column. stop_premium is the
            # immutable -25% floor — overwriting it with the trail made the
            # exit engine's floor checks fire at the trail level and mislabel
            # every trail exit as a hard stop (F5).
            self._trade_logger.update_trail_stop(trade_id, decision.new_trail_stop)
            record["trail_stop"] = decision.new_trail_stop

        if decision.should_exit:
            closed = self._execute_exit(record, decision, current_premium)
            return not closed   # drop if closed; keep (retry) if the order failed

        logger.debug(
            f"Position [{trade_id[:8]}]: "
            f"premium=${current_premium:.2f} "
            f"pnl={decision.current_pnl_pct:.1%} "
            f"(${decision.current_pnl_usd:+.2f})"
        )
        return True

    def _fetch_current_premium(self, record: TradeRecord,
                                chain=None) -> Optional[float]:
        """
        Fetch current mark price for the option(s).
        Uses chain if available — even in paper mode for accurate P&L display.
        Butterfly mark = lower + upper - 2×center.
        Falls back to entry premium in paper mode if chain unavailable.
        
        AUDIT F9 (2026-08-20): the filters were `mark > 0` — NaN was
        excluded (NaN > 0 is False) but 1e12 sailed through, and a
        finite-absurd mark CLOSES a live position on a phantom print
        (stop or target, either way a booked exit nobody chose). The
        excursion tracker already rejects > 1e6; the DECISION path now
        applies the same ceiling. Fail direction: None → tick skipped →
        no decision on garbage.
        """
        is_butterfly = bool(record.get("is_butterfly", False))
        # r48 (LIVE.7 c) — one pricing pass: a stash written below carries this number; one from an earlier pass
        # (or a pass that stashed nothing, e.g. the live REST fallback) is ignored by exit_engine._exit_quote.
        try:
            record["_px_seq"] = int(record.get("_px_seq") or 0) + 1
        except (TypeError, ValueError, AttributeError):
            pass

        if chain is not None:
            try:
                side           = record.get("option_side", "call")
                contracts_list = chain.calls if side == "call" else chain.puts

                # v3.2 (AUDIT F6): structure-derived, matching exit_engine
                # v4.21's dispatch — pricing and routing must never disagree
                # about what a record IS.
                # ── r106 — THE TENT PRICES ACROSS TWO CHAINS ────────────────
                # short + same-type wing + an OPPOSITE-type hedge, so the hedge
                # is not in `contracts_list` at all. Value = what it costs to
                # close: buy back the short, sell both longs.
                if _is_tent(record):
                    _sc = next((c for c in contracts_list
                                if c.strike == record.get("short_strike", 0)
                                and 0 < c.mark < 1e6), None)
                    _lc = next((c for c in contracts_list
                                if c.strike == record.get("long_strike", 0)
                                and 0 < c.mark < 1e6), None)
                    _other = chain.puts if side == "call" else chain.calls
                    _hc = next((c for c in _other
                                if c.strike == record.get("lower_strike", 0)
                                and 0 < c.mark < 1e6), None)
                    if None not in (_sc, _lc, _hc):
                        _stash_quote(
                            record,
                            bid=max(0.0, (getattr(_sc, "bid", 0.0) or 0.0)
                                    - (getattr(_lc, "ask", 0.0) or 0.0)
                                    - (getattr(_hc, "ask", 0.0) or 0.0)),
                            ask=max(0.0, (getattr(_sc, "ask", 0.0) or 0.0)
                                    - (getattr(_lc, "bid", 0.0) or 0.0)
                                    - (getattr(_hc, "bid", 0.0) or 0.0)))
                        _note_quote(record, record.get("_exit_bid"), record.get("_exit_ask"),
                                    getattr(_sc, "iv", None))        # r195: the SHORT leg's IV
                        return _sc.mark - _lc.mark - _hc.mark
                    return None      # a leg we cannot see is not a price

                if _is_credit_vertical(record):
                    short_s = record.get("short_strike", 0)
                    long_s  = record.get("long_strike",  0)
                    _sc = next((c for c in contracts_list if c.strike == short_s and 0 < c.mark < 1e6), None)
                    _lc = next((c for c in contracts_list if c.strike == long_s  and 0 < c.mark < 1e6), None)
                    short_m = _sc.mark if _sc is not None else None
                    long_m  = _lc.mark if _lc is not None else None
                    if short_m is not None and long_m is not None:
                        # ── r105 — STASH THE STRUCTURE'S BID/ASK FOR THE EXIT
                        # LADDER. The exit path has only ever received a MARK,
                        # so it could post at mark and nothing else; a ladder
                        # needs a two-sided quote. CLOSING a short vertical is a
                        # BUY of the spread: we pay short.ask - long.bid at the
                        # touch and receive short.bid - long.ask at the far
                        # side. Built conservatively, per leg, never from the
                        # combined mark ± a guess (limit_ladder v1.1's lesson:
                        # "the shade was guesswork about a spread we cannot
                        # see" — now we can see it).
                        _stash_quote(
                            record,
                            bid=max(0.0, (getattr(_sc, "bid", 0.0) or 0.0)
                                    - (getattr(_lc, "ask", 0.0) or 0.0)),
                            ask=max(0.0, (getattr(_sc, "ask", 0.0) or 0.0)
                                    - (getattr(_lc, "bid", 0.0) or 0.0)))
                        _note_quote(record, record.get("_exit_bid"), record.get("_exit_ask"),
                                    getattr(_sc, "iv", None))        # r195: the SHORT leg's IV
                        return short_m - long_m   # current spread value (credit basis)
                elif is_butterfly:
                    lower_s  = record.get("lower_strike",  0)
                    center_s = record.get("center_strike", 0)
                    upper_s  = record.get("upper_strike",  0)
                    lower_m  = next((c.mark for c in contracts_list if c.strike == lower_s  and 0 < c.mark < 1e6), None)
                    center_m = next((c.mark for c in contracts_list if c.strike == center_s and 0 < c.mark < 1e6), None)
                    upper_m  = next((c.mark for c in contracts_list if c.strike == upper_s  and 0 < c.mark < 1e6), None)
                    if None not in (lower_m, center_m, upper_m):
                        # r195: a composite quote FOR THE RECORD ONLY (see _note_quote) -
                        # sell the wings at their bids, buy the body back at its ask.
                        try:
                            _w = {c.strike: c for c in contracts_list}
                            _lo, _ce, _up = _w.get(lower_s), _w.get(center_s), _w.get(upper_s)
                            if None not in (_lo, _ce, _up):
                                _g = lambda c, k: float(getattr(c, k, 0.0) or 0.0)
                                _fb = max(0.0, _g(_lo, "bid") + _g(_up, "bid") - 2 * _g(_ce, "ask"))
                                _fa = max(0.0, _g(_lo, "ask") + _g(_up, "ask") - 2 * _g(_ce, "bid"))
                                _note_quote(record, _fb, _fa,
                                            getattr(_ce, "iv", None))   # the BODY's IV
                                _stash_fly_quote(record, _fb, _fa)      # r48: the walk's quote, own keys
                        except Exception as _qe:                  # noqa: BLE001
                            logger.debug("fly quote not recorded: %s", _qe)
                        return lower_m + upper_m - 2 * center_m
                else:
                    strike = record.get("strike", 0)
                    match  = next(
                        (c for c in contracts_list if c.strike == strike and 0 < c.mark < 1e6),
                        None
                    )
                    if match:
                        # r105 — the single-leg quote, for the exit ladder.
                        _stash_quote(record,
                                     bid=float(getattr(match, "bid", 0.0) or 0.0),
                                     ask=float(getattr(match, "ask", 0.0) or 0.0))
                        # stash live theta so the exit engine's theta-bleed
                        # detector can see it (single-leg longs only)
                        record["current_theta"] = float(getattr(match, "theta", 0.0) or 0.0)
                        # VEL.1 — the velocity stall check needs DELTA as well:
                        # breakeven velocity is |theta| / (|delta| * 1440), so
                        # theta alone cannot answer "is this position gaining or
                        # bleeding right now". Same stash, same guard.
                        _note_quote(record, getattr(match, "bid", 0.0), getattr(match, "ask", 0.0),
                                    getattr(match, "iv", None))       # r195
                        # r293 (DELTA.2) — an UNREAD delta is None and SAID, never 0.0. r209's
                        # `float(delta or 0.0)` then `_delta_readable(record, True)` stored 0.0 and
                        # flagged it readable, so the r209 warning could never fire and the delta-par /
                        # delta-floor exits went dark without a line (audit 10-18 D2). The chain writes
                        # 0.0 for a missing greek (options_chain.py:598), so 0.0 IS the unread sentinel.
                        try:
                            _dval = float(getattr(match, "delta", None))
                        except (TypeError, ValueError):
                            _dval = 0.0
                        if _dval == 0.0:
                            _delta_readable(record, False, "delta missing on the quoted contract")
                        else:
                            record["current_delta"] = _dval
                            _delta_readable(record, True)             # r209
                        return match.mark
                    _delta_readable(record, False, "no quoted contract at the strike")   # r209
            except Exception as _dexc:                                # noqa: BLE001
                # r209 — was `pass`: the delta-par exit went dark and nothing said so
                _delta_readable(record, False, f"{type(_dexc).__name__}: {_dexc}")

        if self.paper_trading:
            # LAST-KNOWN MARK, not entry (v2.1). Falling back to entry premium
            # here fabricated a $0 P&L on ANY exit taken while the chain was
            # momentarily unavailable — a real -$818 loss was booked as breakeven
            # at the 15:45 hard close (CRM 2026-07-09, exit recorded == entry).
            # It also blinded the exit logic (a position that "looks like entry"
            # can't trip a stop/target/trail). Use the last live mark that was
            # stored via update_current_premium every good tick; only surrender to
            # entry if we have literally never priced it, and log it so it's never
            # silent.
            last_mark = record.get("current_premium") or 0.0
            if last_mark > 0:
                return last_mark
            logger.warning(
                f"{str(record.get('trade_id',''))[:8]}: no chain and no prior "
                f"mark — falling back to entry premium (P&L may be understated)"
            )
            return record.get("entry_premium", 0.0)

        client = get_client()
        try:
            # r468 / F4 — dispatch like the chain path above: a leg we cannot
            # see is not a price, and a vertical is never priced as one leg.
            if _is_tent(record):
                logger.warning(f"{str(record.get('trade_id', ''))[:8]}: no chain - "
                               f"a tent is not priced by the quote fallback")
                return None
            if _is_credit_vertical(record):
                s_sym = record.get("short_symbol") or ""
                l_sym = record.get("long_symbol") or ""
                if not s_sym or not l_sym:
                    return None
                m = self._get_option_marks(client, [s_sym, l_sym])     # r496: one call
                short_m, long_m = m.get(s_sym), m.get(l_sym)
                if short_m is None or long_m is None:
                    return None
                return short_m - long_m           # current spread value (credit basis)
            if is_butterfly:
                lower_sym  = record.get("lower_symbol",  "")
                center_sym = record.get("center_symbol", "")
                upper_sym  = record.get("upper_symbol",  "")

                m = self._get_option_marks(client, [lower_sym, center_sym, upper_sym])   # r496
                lower_mark  = m.get(lower_sym) if lower_sym else None
                center_mark = m.get(center_sym) if center_sym else None
                upper_mark  = m.get(upper_sym) if upper_sym else None

                if None in (lower_mark, center_mark, upper_mark):
                    return None
                return lower_mark + upper_mark - 2 * center_mark
            else:
                symbol = record.get("option_symbol", "")
                return self._get_option_mark(client, symbol)

        except Exception as e:
            logger.error(f"Premium fetch error: {e}")
            return None

    _mark_fail_warned: set = set()
    MARK_RETRY_BACKOFF_S = (0.5, 1.0, 2.0)     # r496 F4.2: after each 429 -> at most 4 calls, 3.5 s
    MARK_COOLDOWN_S = 10.0                     # after a spent retry: single tries only, this long
    _mark_cool_until: float = 0.0              # class-wide: one bucket per box

    @staticmethod
    def _sym_key(sym) -> str:
        """r496 — one key for an OCC symbol however it is spaced ('SPXW  261020C07545000'
        and 'SPXW261020C07545000' are one contract)."""
        return "".join(str(sym or "").split()).upper()

    @staticmethod
    def _http_status(exc) -> Optional[int]:
        """r496 — the HTTP status behind an SDK failure. tastytrade raises TastytradeError
        "Couldn't parse response: <html><title>429 Too Many Requests</title>..." for nginx's
        page; an httpx error carries .response.status_code."""
        code = getattr(getattr(exc, "response", None), "status_code", None)
        if isinstance(code, int):
            return code
        m = re.search(r"\b([45]\d\d)\s+[A-Z][A-Za-z]", str(exc))
        return int(m.group(1)) if m else None

    def _get_option_marks(self, client, symbols) -> dict:
        """r496 / F4.2 — {symbol: mark} for a structure's legs in ONE REST call
        (get_market_data_by_type, a coroutine run through sdk_result, B0). A 429 is retried
        after MARK_RETRY_BACKOFF_S, touching the heartbeat before every call; any other
        failure is not. A symbol missing from the answer, or failing the rule, is absent."""
        syms = [x for x in dict.fromkeys(symbols or []) if x]
        if not syms:
            return {}
        from utils.heartbeat import touch as _hb_touch
        rows, exc, status, tries = None, None, None, 0
        backoff = (() if time.time() < PositionManager._mark_cool_until
                   else self.MARK_RETRY_BACKOFF_S)
        for attempt in range(len(backoff) + 1):
            _hb_touch("mark fallback")
            tries += 1
            try:
                from tastytrade.market_data import get_market_data_by_type
                rows = sdk_result(get_market_data_by_type(client, options=syms))
                break
            except Exception as e:                             # noqa: BLE001
                exc, status = e, self._http_status(e)
                if status == 429 and attempt < len(backoff):
                    time.sleep(backoff[attempt])
                    continue
                break
        if rows is None and status == 429:
            PositionManager._mark_cool_until = time.time() + self.MARK_COOLDOWN_S
        if rows is None:
            why = (f"HTTP {status}" + (f" Too Many Requests, after {tries} "
                   f"tr{'y' if tries == 1 else 'ies'}" if status == 429 else "")
                   if status else f"{type(exc).__name__}: {str(exc)[:160]}")
            for x in syms:
                if x not in self._mark_fail_warned:
                    self._mark_fail_warned.add(x)
                    logger.warning(f"live mark fallback failed for {x!r}: {why}")
            return {}
        want = {self._sym_key(x): x for x in syms}               # answer key -> the caller's symbol
        out = {}
        for md in rows or []:
            sym = want.get(self._sym_key(getattr(md, "symbol", None)))
            if sym is None:
                continue
            bid = float(getattr(md, "bid", 0) or 0)
            ask = float(getattr(md, "ask", 0) or 0)
            if bid > 0 and ask > 0:
                v = (bid + ask) / 2
            else:
                v = float(getattr(md, "mark", 0) or getattr(md, "last", 0) or 0)
            # AUDIT F9's ceiling, as the chain path applies it: a finite-absurd
            # print must not close a live position.
            if 0 < v < 1e6:
                out[sym] = v
        return out

    def _get_option_mark(self, client, symbol: str) -> Optional[float]:
        """r468 / F4 — one option's mark for a LIVE box with no chain in hand. r496: a
        one-symbol call to _get_option_marks (the batch call, with its 429 retry)."""
        if not symbol:
            return None
        return self._get_option_marks(client, [symbol]).get(symbol)

    def _execute_exit(self, record: TradeRecord,
                       decision: ExitDecision,
                       current_premium: float,
                       _rested: bool = False) -> bool:
        """Place the exit and book P&L ONLY on a confirmed fill. Returns True if
        the position genuinely closed, False if not (caller retries).

        v3.4: booking is gated on FillResult.confirmed and uses the ACTUAL fill
        price, not the mark we passed in. In paper the simulated fill price
        equals the mark; in live it is the broker's real fill. An unconfirmed
        result books NOTHING and leaves the row open — the anti-orphan invariant.
        current_premium is the last-known mark, passed to the exit engine as the
        paper fill price / live context.
        """
        trade_id = record["trade_id"]

        exit_eng = get_exit_engine(self.paper_trading)
        if getattr(self, "SHADOW", False) is True:                                      # r57 (TCS.LOG1): the shadow book's own engine
            exit_eng = self._exit_engine()
        # r266 (STOP.1) — a premium stop with the mark already under its level RESTS instead.
        if not _rested and getattr(self, "SHADOW", False) is not True:                  # r57: a shadow never rests
            try:
                if (_rs.active_mode(self.paper_trading) == "trade"
                        and _rs.eligible(record, decision.exit_reason)):
                    _lvl = _rs.level_for(record, decision.exit_reason,
                                         getattr(exit_eng, "_trail_stops", {}).get(trade_id))
                    if _lvl and current_premium is not None and float(current_premium) < _lvl:
                        _rs.begin(record, decision.exit_reason, float(current_premium), _lvl)
                        return False                                 # resting: the row stays open
            except Exception as _rse:                                # noqa: BLE001
                logger.error(f"resting stop could not start for {trade_id[:8]} ({_rse}) - "
                             f"closing as before")
        fill     = exit_eng.place_exit_order(record, decision.exit_reason,
                                             mark_price=current_premium)

        if not fill.confirmed:
            if getattr(fill, "held", False):                 # r36 (EOD.2): intended, not a failure
                if trade_id not in _HELD_LOGGED:
                    _HELD_LOGGED.add(trade_id)
                    logger.info(f"EOD close of {trade_id[:8]} held to the 15:55 cross (EOD.1) — intended; "
                                f"it closes at the cross")
                return False
            logger.error(f"Exit NOT confirmed for {trade_id[:8]} "
                         f"({fill.detail or 'no fill'}) — position stays OPEN, will retry")
            return False

        fill_price = fill.fill_price
        if fill_price is None:
            # confirmed with no price should be impossible; refuse to book fiction.
            logger.error(f"Exit for {trade_id[:8]} confirmed but no fill_price — "
                         f"refusing to book; will retry")
            return False

        entry_prem    = record["entry_premium"]
        contracts     = record["contracts"]
        # Credit/short positions profit when the premium FALLS, so the P&L sign
        # is inverted vs a debit (long) trade. This covers condor legs AND an
        # adopted short leg (is_short_position) discovered at the broker.
        credit_signed = (bool(record.get("is_condor_leg"))
                         or record.get("strategy") == "IronCondorStrategy"
                         or bool(record.get("is_short_position"))
                         or _is_credit_vertical(record))          # r46 (PARC.1): a credit vertical by structure
        if credit_signed:
            pnl_per_share = entry_prem - fill_price
        else:
            pnl_per_share = fill_price - entry_prem
        pnl_usd       = pnl_per_share * contracts * CONTRACT_MULTIPLIER

        # v4.0: carry the excursion through to the book. `_track_excursion`
        # fills these on the record every tick inside `exit_engine.evaluate`;
        # a parameter nothing passes is a column nothing fills, which is the
        # `open_interest` failure exactly - a declared field with no producer.
        _exc = {k: record.get(k) for k in
                ("mfe_premium", "mfe_bars", "mae_premium", "mae_bars")
                if record.get(k) is not None} if isinstance(record, dict) else None
        self._trade_logger.log_exit(
            trade_id    = trade_id,
            exit_price  = fill_price,
            pnl_usd     = pnl_usd,
            exit_reason = decision.exit_reason,
            excursion   = _exc or None,
        )
        # r195 (AUD.4) — THE EXIT-SIDE QUOTE, FINALLY WRITTEN. set_exit_contract existed
        # since v3.13 and NOTHING CALLED IT: exit_bid / exit_ask / exit_iv were empty on
        # 237 of 237 closed trades, so neither the exit's spread cost nor IV crush could
        # be measured. Record-only; a failure warns once and never blocks the close.
        try:
            _qp = {"exit_bid": record.get("_q_bid"), "exit_ask": record.get("_q_ask"),
                   "exit_iv": record.get("_q_iv")}
            if not self._trade_logger.set_exit_contract(trade_id, _qp) and "exit_quote" not in _WARNED_ONCE:
                _WARNED_ONCE.add("exit_quote")
                logger.warning("exit quote NOT recorded for %s (no quote seen this tick, or the "
                               "write failed) - warned once", trade_id[:8])
        except Exception as _xe:                                  # noqa: BLE001
            if "exit_quote_raised" not in _WARNED_ONCE:
                _WARNED_ONCE.add("exit_quote_raised")
                logger.warning("exit quote capture raised (%s: %s) - warned once",
                               type(_xe).__name__, _xe)

        if getattr(self, "SHADOW", False) is True:
            # r57 (TCS.LOG1) — A SHADOW CLOSE TOUCHES NOTHING OF THE REAL BOOK: no risk_manager win/loss (the daily
            # loss cap), no Telegram exit alert, no resting stop, no ORB re-arm. One distinct line, and done.
            exit_eng.clear_trail(trade_id)
            _mk = f" mark=${float(current_premium):.2f}" if current_premium is not None else ""
            logger.info(f"[shadow] Position closed: {trade_id[:15]} exit=${fill_price:.2f}{_mk} "
                        f"pnl=${pnl_usd:+.2f} reason={decision.exit_reason} (shadow - never ordered)")
            return True

        risk_mgr = get_risk_manager()
        if pnl_usd >= 0:
            risk_mgr.record_win(pnl_usd)
        else:
            risk_mgr.record_loss(pnl_usd)

        get_alert_manager().send_exit_alert(
            trade_id      = trade_id,
            setup_type    = record.get("setup_type", ""),
            exit_premium  = fill_price,
            entry_premium = entry_prem,
            pnl_usd       = pnl_usd,
            contracts     = contracts,
            reason        = decision.exit_reason,
        )

        exit_eng.clear_trail(trade_id)
        if not _rested:                                              # r266: any other close ends a rest
            try:
                _rs.abandon(trade_id, f"closed by {str(decision.exit_reason).split(' ')[0]}")
            except Exception:                                        # noqa: BLE001
                pass

        # ── Re-arm ORB engine if this was an ORB trade ─────────────────────────
        # Allows the engine to watch for another breakout attempt this session
        # rather than treating one trade as the end of the ORB opportunity.
        if "ORB" in record.get("strategy", ""):
            # 🔴 r195 — THE REMAINDER DIES WITH THE TRADE, AND IT MUST GO FIRST.
            # A standing offer can be partly filled: 4 of 10 fill, the position
            # opens, and this exit closes it. The other 6 are STILL WORKING at
            # the broker. The supervisor's triggers (fully filled / past the
            # 50% TP / structure stop / EOD) do not cover an exit on
            # theta_bleed, the velocity stall, the trail or the 15:45 flatten
            # — so those 6 would keep standing with no position behind them
            # while the engine re-armed onto a new setup with different
            # geometry. Operator: a re-arm cancels any previous offer, because
            # a new impulsive candle has a different high and low and so a
            # different offer composition.
            # ⚠️ BEFORE the re-arm, not after: once the engine re-arms it has
            # forgotten this setup, and nothing left knows which offer belonged
            # to it.
            try:
                from execution import resting_orders as _ro
                _ro.cancel_all_working(
                    f"position closed: {decision.exit_reason}",
                    paper=self.paper_trading)
            except Exception as e:                              # noqa: BLE001
                logger.error("Could not cancel the standing offer remainder "
                             "(%s) — it may still fill and would then be an "
                             "UNMANAGED position", e)
            try:
                from analysis.orb_engine import get_orb_engine
                get_orb_engine().notify_position_closed()
            except Exception as e:
                logger.warning(f"Could not re-arm ORB engine: {e}")

        # EOD.3 (r42) — exit= is the BOOKED fill, the price pnl was computed from.
        # It printed current_premium (the mark): CVX 006f6eca 2026-10-27 logged
        # exit=$4.28 while the ledger booked 1.25.
        _mk = f" mark=${float(current_premium):.2f}" if current_premium is not None else ""
        logger.info(
            f"✅ Position closed: {trade_id[:8]} "
            f"exit=${fill_price:.2f}{_mk} "
            f"pnl=${pnl_usd:+.2f} "
            f"reason={decision.exit_reason}"
        )
        return True


# Singleton
_position_manager: Optional[PositionManager] = None


def get_position_manager(paper_trading: bool = PAPER_TRADING) -> PositionManager:
    global _position_manager
    if _position_manager is None:
        _position_manager = PositionManager(paper_trading)
    return _position_manager
