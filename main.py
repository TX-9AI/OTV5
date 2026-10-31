"""
main.py  v5.10
v5.10 2026-10-30  OTV5 r61 (ORB.10) — THE RETIRED ORB NO LONGER HOLDS THE ENGINE OPEN, SO RUNAWAY CAN SEE THE REVERSAL.
      ORBStrategy is DORMANT (retired, OTV4TEST r187) and the ORB engine runs only for RunawayContinuation, which reads
      its direction off the engine state. The engine's only release from OPEN_* is notify_position_closed (an ORB close,
      an ORB offer release, a same-side Runaway fire), so after the first break+retest it held OPEN_LONG / OPEN_SHORT to
      15:40 (52 of 60 OPEN_* segments 2026-10-26..10-30) and Runaway could only look the first break's way (QQQ 10-30
      short ~10:25, AMD 10-26 ~10:03, SPX 10-27 ~09:51, NFLX 10-27 ~10:22 never set up). run_analysis:
      _orb_release_due(state) - ORBStrategy not active (plan_state), no ORB standing offer working, no open ORB
      position - and right after get_orb_engine().update() an OPEN_* engine is released by
      orb_engine.release_unowned() (the release an ORB close gives); the tick's `orb` is re-read from the engine. The
      tape reach-back gets the same word (rebuild_from_tape(release_open=...)), so a restart re-derives what the live
      loop holds. Not after the ORB dispatch: attempt_new_entry returns before it on a blocked session, at the loss cap
      and on a no-chain tick, and every bar read while OPEN_* is lost. OT_ORB_TRADE=1 (ORB active): unchanged. The
      operator, 2026-10-30: "investigate and fix this". Gate tests/check_orb_release.py.
v5.9  2026-10-30  OTV5 r57 (TCS.LOG1) — A LOG-ONLY TCS IS A FULL SHADOW TRADE. The operator, 2026-10-30: "Can you reactivate
      TCS Monday as 'log only'? But do not trade it." then "Make sure TCS logs everything an executable trade logs."
      TrendCreditSpread is LOG by default (strategy/plan_state v5.2). _execute_condor_leg: a TCS whose plan is LOG
      (execution/shadow_book.is_shadow_signal) is not refused at the credit door; it runs the rest of the door - the
      entry gate, its contracts, the vertical sizing, the paper fill (paper_fill_credit of the mark, the live order
      block skipped on any box), the same make_record - and at the write it is booked by shadow_book.open_entry
      (shadow_trades.db, trade_id shadow-<uuid>, order_id SHADOW) with the entry snapshot, fire snapshot and entry
      contract written to the shadow row (_capture_entry_snapshot / _capture_entry_contract take tl=; the fire snapshot
      does not link a plan_ledger row). Not written: trades.db, note_entry_risk, the real position manager, the
      remainder, the Telegram alert ("[shadow]" log line instead). A shadow TCS of the same side already open refuses
      it. main_loop: _shadow_manage(ctx) every RTH tick beside the offer / remainder supervisors (both branches);
      _shadow_eod in the hard-close branch (the same flatten_all, then the held pass until 15:50). Boot:
      _recover_open_position resumes the shadow store (expired settled, live resumed). OT_TCS_ACTIVE=0: not asked,
      nothing written; =1: the real trade path, unchanged. Gate tests/check_tcs_shadow.py.
v5.8  2026-10-29  OTV5 r54 (BRK.16) — BREAKOUT'S PIN GATE ALLOWS A PIN AHEAD OF THE TRADE. The operator, 2026-10-29: "if the
      Pin is in the direction of the break, allow it. But if the pin is on the opposite direction from our trade, forbid
      it" (the NARROW reading, concurred: same scope as today). Inside today's band (PINNING and |pin - price| / EM <
      PIN_PROXIMITY_MIN_FRAC) a Breakout whose pin is AHEAD (above price for a long, below for a short) is ALLOWED and
      logged "[pin] ALLOWED Breakout <dir> ... pin ahead"; a pin behind is refused as today; a pin exactly at price is
      refused (today's gate). pin_ahead_allows() is the decision, driven by tests/check_brk_spec_1029.py. Every other
      strategy keeps today's gate; outside the band nothing changes; the observe line says "would ALLOW (pin ahead)".
v5.7  2026-10-29  OTV5 r53 (FLY.3) — A BUTTERFLY'S ENTRY QUOTE AND GREEKS ARE THE FLY'S, NOT ITS BODY LEG'S. RECORD ONLY.
      _capture_entry_contract matched record["option_symbol"], which on a fly is the CENTER leg, so entry_bid/ask and
      entry_delta/gamma/theta were the body's (NVDA 2026-10-28: entry_premium 0.58 beside entry_bid/ask 0.21/0.22,
      delta 0.164; TSLA 0.70 vs 0.10/0.11; AMZN 0.56 vs 0.27/0.29; 10-26 AMD 1.02 vs 0.40/0.43, TSLA 0.36 vs 0.21/0.22).
      For a butterfly row it now finds all three legs (lower/center/upper_symbol, else the strike on the fly's side)
      and writes the composite position_manager builds for the exit record: bid = lower.bid + upper.bid - 2*center.ask,
      ask = lower.ask + upper.ask - 2*center.bid (each floored at 0), delta/gamma/theta = lower + upper - 2*center,
      entry_iv = the BODY's IV (as _note_quote records a fly). A missing leg writes nothing ("fly-leg-not-found:<leg>").
      Single-leg and credit-vertical rows are unchanged. Nothing reads these columns to trade. GATE
      tests/check_fly_entry_quote.py.
v5.6  2026-10-28  OTV5 r51 (BAR.2) — EACH TICK WAITS OUT THE FIRST SECONDS OF A MINUTE, WHEN THE JUST-ENDED BAR IS
      PROVISIONAL. CRM 2026-10-28 cut a Runaway at 09:49:00.84 ET on a 09:48 close of 241.78 that finished at 241.93
      (above its 241.85 line); 12 of 38 decisions logged at 0-2 s that day read a close the final bar does not have.
      main_loop sleeps utils.time_utils.bar_grace_wait() (BAR_FINAL_GRACE_S = 3 s after each minute boundary) before
      tick_start, so no tick - a floor-watch wake included - reads a bar inside that window; the loop's 15 s cadence
      then settles 3 s past the boundary. Nothing else changes. GATE tests/check_bar_final_grace.py.
v5.5  2026-10-28  OTV5 r47 (ORB.9) — NO 5m BARS OUTSIDE RTH IS THE EXPECTED STATE, NOT A WARNING. SPX logged "ORB range fetch
      failed: ERROR: no 5m data returned for SPX" at WARNING at the 09:15 wake (2026-10-27 13:15:34 UTC) and after the
      bell (2026-10-26 20:21/20:50 UTC, 10-27 00:28 UTC), when the feed store has no usable 5m bars to give
      (data.market_data.fetch_candles returned None - a freshly woken box's store or feed); the range was established
      normally both sessions (10-27 ESTABLISHED at 09:35:16 ET).
      _fetch_orb_range logs that case at INFO, naming why, whenever utils.time_utils.is_rth is False (before 09:30,
      after the day's bell - half days included -, weekends, holidays); inside RTH it stays a WARNING, and every other
      failure is a WARNING at any hour. Polling, return values and orb_range.json are unchanged. Gate
      tests/check_orb_range_quiet.py.
v5.4  2026-10-27  OTV5 r46 (PARC.1) — PARC IS ASKED BESIDE PARK AND EXECUTED THROUGH THE CREDIT-VERTICAL LADDER. The operator,
      2026-10-27: "under identical entry conditions the PARK trade sells a credit spread ATM nearest the strike on the
      safer side ..."; "Call it PARC"; "No shadow mode. We're paper. It trades tomorrow."; "I also want to make sure it
      uses the ladder entry & exit." _attempt_parc() (dormant outside 11:01-11:03, one per session on this box, DB-backed,
      fails closed; OT_PARC=0 never asked) runs right after _attempt_park in the normal dispatch AND in the capped branch
      (PARC is cap-exempt, its own budget), so both may fire the same minute. A fire goes to _execute_condor_leg - the
      one credit-vertical door: paper books limit_ladder.paper_fill_credit(the mark credit), live walks the entry ladder
      (_post_credit_vertical, intent key cv:<sym>:PARC:<side>). For a PARC signal that door sizes on the Breakout ramp
      (risk_manager size_for("parc"), rule parc_ramp), writes strategy "PARC", direction long/short, underlying_stop =
      the 5m swing, stop_premium 0 (no premium stop), target_premium the nickel, is_condor_leg 0 (it pairs with nothing)
      and PARK's signal columns (underlying_target, is_fed_day, notes, trail_activation 0, is_liquidity_hunt 0).
      _STRUCTURE_BY_NAME declares PARC "vertical"; _credit_window_end reads its window; the Service line adds
      " · parc=<mode>". Every other strategy's path through _execute_condor_leg is unchanged. Gate tests/check_parc.py.
v5.3  2026-10-27  OTV5 r44 (BAR.1) — _supervise_offers hands the resting-offer supervisor the last 1m close BY TIME
      (utils.time_utils.closed_pos), not df_1m.iloc[-2], which was one bar stale on a tick before the new minute's first
      row exists (META 2026-10-27 3f2b1372: a Breakout short fired 10:10:00 ET on the 10:08 bar while 10:09 had already closed back inside the 623.20 edge). Unchanged when the forming row is present. GATE tests/check_last_closed_bar.py.
v5.2  2026-10-25  (MEAS.3) — COMMENT ONLY: the dispatch note no longer says a Fed day boosts ORB conviction
      (FED_DAY_ORB_BOOST is removed; the Fed-day flag is record only).
v5.1  2026-10-25  (MEAS.4) — adx_at_entry IS STAMPED FOR EVERY STRATEGY. _stamp_adx copies ctx["trend"].primary_adx
      (the field assemble_market_state puts on MarketState.adx, which ORB's own stamp reads) onto the signal right
      after _stamp_vix in both executors, when the strategy did not set it. Only ORB ever did, so adx_at_entry was 0.0
      on every non-ORB row (27 of 34 at MEAS.4's count). Record only: nothing gates on the field. Gate
      tests/check_adx_stamp.py.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.118  2026-10-24  CD.3 (DISC.4) - the gap measure is given the instrument and the day, so analysis/gap_measure reads
      the prior session's 1d bar and today's 09:30 bar from the feed store instead of hoping the 5m frame reaches
      yesterday; gap_class / gap_bucket / range_gap_pct now reach ctx["gap"] (record-only readers: notes, snapshot,
      character).
v4.117  2026-10-24  CD.2 - the derived ports judge their rows by MARKET time: the charm/vanna port reads through
      anchors._surface_row (quote_ts within 120 s, today's expiry; it used to order by strike distance before time, so
      the nearest strike from ANY day won), and the fork tilt reads anchors.fork_row (the frame's newest row, only while
      its bar is the frame's latest closed bar). A stale or seeded row is recorded as absent, not as current.
v4.116  2026-10-24  CD.1 - RENT.2/RENT.3 SCRAPPED: the 20 s re-entry gate's call, its imports and the Service-line field
      " · reentry_gate=" are removed (the operator, 2026-10-24: "It has zero value. Scrap it.").
v4.115  2026-10-24  OTV4TEST r316 (BRK.15 + HUNT.13 + RENT.3) - the Service mode line names " · brk_refire=<rearm|extreme>"
      and " · hunt_after_brk=<trade|log|off>" (each with its REFUSED value), and BRK.12's re-arm record reads
      "brk:superseded" while brk_refire=rearm (the re-arm is the rule now, so nothing records it as a shadow).
      OT_REENTRY_GATE unset is log since r316: the 20 s gate records and never blocks. The operator, 2026-10-24.
v4.114  2026-10-20  OTV4TEST r309 (B4, MIRROR OF otv4 r495 81cc63c, WA 38.2) - a LIVE start cancels this instrument's
      untracked working orders (order_guard.boot_sweep) BEFORE the broker reconcile, so a part-filled leftover is
      adopted by the same start; entries stay blocked until one sweep comes back clean. Hunk verbatim from 81cc63c.
v4.113  2026-10-19  OTV4TEST r306 (RENT.2) - _execute_entry_signal: after COMMIT.2 and before the order, a directional
      entry within 20 s of a same-side PREMIUM exit (any strategy, trades.db) is not placed on a paper box
      (analysis/reentry.py; OT_REENTRY_GATE, unset = trade); the Service mode line names " · reentry_gate=<mode>".
      The operator, 2026-10-19 20:17 ET: "Yes".
v4.112  2026-10-19  OTV4TEST r304 (HUNT.12) - _attempt_hunt hands the break back (_release_unfilled_hunt) when its fire
      opened nothing: no open Hunt and no trades.db row for the break after _execute_entry_signal (the commit gate, a
      zero size, a failed order). An unreadable book keeps it spent (fails closed). The operator, 2026-10-19: "1. Yes".
v4.111  2026-10-19  OTV4TEST r303 (PSTATE.1) - every plan is ACTIVE, LOG or DORMANT (strategy/plan_state.py; the operator,
      2026-10-19 08:43 ET: "each plan to have 3 states: active, dormant or log only"). _safe_strategy never asks a DORMANT
      plan; _retired_reason lets a LOG sweep / TCS be asked; _execute_condor_leg refuses a LOG plan's signal at its top
      (_log_only, the credit door r254 never had); _log_only names which rule refused; the start names every plan's
      state and writes data/plan_states.json (_announce_plan_states). Defaults = today's roster: no decision changes.
v4.110  2026-10-18  OTV4TEST r301 (LOG.1) - the rehearsal's "Could not fetch options chain" is INFO once per ET date
      (2,428 WARNINGs in the week of 10-12, all after the bell); inside RTH it stays WARNING every tick. _chain_miss_say().
v4.109  2026-10-18  OTV4TEST r295 (LIVE.2) - _touch_heartbeat delegates to utils.heartbeat.touch (same file, same format);
      the live poll loops touch it too, so a serial close ladder never reads as a hung bot to the emergency watchdog.
v4.108  2026-10-18  OTV4TEST r293 (DIAL.2 + ADM.2) - the Service line names hunt_stop and rearm (and their REFUSED values:
      config recorded HUNT_STOP5M/BRK_REARM/HUNT_REARM refusals that nothing read - audit 10-18 G2); _admission_allows
      FAILS CLOSED with one WARNING when the rules table cannot be read (it returned True silently - audit 10-18 D1).
v4.107  2026-10-18  OTV4TEST r288 (PARK.1 + BRK.13) - PARK is asked every tick through _attempt_park() (dormant outside
      11:01-11:03): in the normal dispatch and ALSO in the capped branch beside the butterflies, because PARK is
      cap-exempt (its own budget, the operator 2026-10-17); one per session; OT_PARK=off is never asked. The pin-proximity
      gate does not refuse PARK (PIN_EXEMPT - PARK was measured without it); what the gate would have said is a
      counterfactual row on every PARK entry, data/counterfactual/pin_gate.jsonl (the operator, 2026-10-17 20:06 ET:
      "I want a counterfactual on the pin gate recorded on the entries").
      _STRUCTURE_BY_NAME declares PARK long_debit. The Service line adds " · park=<mode>" and " · brk_dfloor=<mode>".
v4.106  2026-10-14  OTV4TEST r284 (BRK.11) - the Service mode line names Breakout's stop in force: " · brk_stop=5m(trade)|1m(log)|1m(off)"
      (and a refused OT_BRK_STOP5M by name), read from config. The operator, 2026-10-14 11:47 ET: "Yes, we have to".
v4.105  2026-10-14  OTV4TEST r283 (LIVE.1 F5, mirror of otv4 r473 bfb0991) - a live credit vertical checks buying
      power before it posts: (width - credit) x contracts x 100, via execution/buying_power.affordable, right
      after B2's guard. Short or unreadable -> not posted. Code hunk verbatim from bfb0991. Paper unchanged.
v4.104  2026-10-13  OTV4TEST r281 (RUN.1, mirror of otv4 r481) - ONE RUNAWAY PER SESSION ON THIS BOX, ENFORCED: the
      dispatch binds `_rc_capped = _one_per_session_used("RunawayContinuation")`, writes the "one per session on this
      box - already traded today" plan row, and asks RunawayContinuation only `if not _rc_capped`. It was `if True:`.
v4.103  2026-10-13  OTV4TEST r280 (EXIT.5 on TEST) - the end-of-tick sleep ENDS EARLY when execution/fill_observers
      finds a Breakout/Runaway position's fresh quote (<= 4 s) at or below its enforced premium stop, and logs
      "[floor-watch] ... running the tick Ns early"; the tick then decides as before. The Service mode line names
      " · floor_watch=trade|log|off" (OT_FLOOR_WATCH, unset = trade).
v4.102  2026-10-12  OTV4TEST r272 (COMMIT.1/2/3) — each tick puts analysis/commitment.observe() on ctx["commitment"]
      (recorded per closed 1m bar); _execute_entry_signal, after sizing and before the order, does not place a
      DIRECTIONAL entry whose side is ABANDONED when OT_COMMIT_GATE=trade (unset) on a paper box, records every
      directional entry with its would-be order, and logs the caution size without changing it - BOTH candidates: S2
      (0.5x unless COMMITTED) and SCALING-OFF (the SAME size_for call with scaled=False, for ORB/Breakout/VOLT; the
      operator, 2026-10-12 11:52 ET: "Yes"). The order's size_for call goes through commitment.SizeCall, which records
      its exact arguments for that repeat (the call keeps its explicit keywords: check_volt_sizing V7). The Service
      mode line names " · commit_gate=<mode> · caution=<mode>". The operator, 2026-10-12 11:35 ET: "Yes, do it".
v4.101  2026-10-11  OTV4TEST r270 (PMAP.1 + FILL.2, RECORD ONLY) — the end-of-tick sleep is execution/fill_observers.sleep_observing:
      the SAME total, in 2 s slices, between which the quote watch records any open position whose own quote crossed its
      premium stop (never wakes, exits or orders). The Service mode line names " · fill_observe=on|off" (OT_FILL_OBSERVE).
v4.100  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v4.99 2026-10-11  OTV4TEST r268 (DEP.12, mirror of otv4 r478) — HALF DAYS. Every close-anchored instant here moves to the day's bell
      (utils/time_utils.close_anchored): _vertical_close_due (credit hold 12:45 on a 13:00 close), the tent's minutes_to_flatten,
      and _intraday_reconcile_slot's EOD_SCHEDULE wind-down slots (12:45/12:50/12:55/12:57, dormant 13:00; the 09:30 base stays
      raw and every key is true ET). The hard-close branch reads is_hard_close_time, so run_analysis goes quiet at 12:45.
v4.98 2026-10-10  OTV4TEST r266 (STOP.1) — THE SERVICE MODE LINE NAMES THE RESTING STOP IN FORCE: " · resting_stop=off|trade" (plus "(LIVE: refused)" on a live box, and a refused OT_RESTING_STOP by name).
v4.97 2026-10-10  OTV4TEST r265 (BRK.8 + BRK.9) — THE SERVICE MODE LINE NAMES BREAKOUT'S END AND ITS NO-PROGRESS MODE IN FORCE: `_banner_dials()` appends " · breakout_end=HH:MM · brk_noprog=off|log|trade" (and a refused OT_BREAKOUT_END / OT_BRK_NOPROG by name), read from config. The operator, 2026-10-10 13:37 ET: "Yes, to all. Study, fit & apply."
v4.96 2026-10-05  OTV4TEST r254 (OBS.1) — THE PLAN ALWAYS LOOKS, THE STRATEGY IS GATED ON THE HOUR: Breakout, Runaway and the Hunt are OBSERVED from their entry end to 15:40 - asked, recorded LOG-ONLY, never executed (the operator, 2026-10-05: "the plan always looks, but the strategies are gated on the hour of the day"; "Have those blocked TRADES just to Log only"). Here: admission publishes the observe set each tick (position_manager.observing) and clears it first; _log_only() refuses an observed signal at _fire, the hunt's door and the top of _execute_entry_signal (after the VIX stamp, before any sizing or order) and logs it once per setup with the pin gate's answer.
v4.95 2026-10-05  OTV4TEST r253 (RUNW.2) — THE SERVICE MODE LINE NAMES THE PIN GATE AND RUNAWAY'S END IN FORCE: `_banner_dials()` appends " · pin_gate=ON/OFF · runaway_end=HH:MM" (and a refused OT_RUNAWAY_END by name), read from config. SPX-TEST, 10-05: neither was printed anywhere, so a box's pin gate had to be inferred from silence. configure.sh item 10 now sets the end (the operator: "it needs to be a toggle inside configure").
v4.94 2026-10-04  OTV4TEST r247 (FORK-ONLY, the operator: "Fix the SPXW settlement", "Fix the ORCS ledger rows issue") — _settlement_spot reads SPX's tape for an SPXW root (_SETTLE_TAPE), so an adopted SPXW position settles at the index's 16:00 close instead of a flagged $0.00; _attempt_orcs refuses a LIVE box BEFORE ledger_open, so no orphan plan_ledger row is written (the refusal in _execute_condor_leg stays as the backstop). Both found by SPX-TEST's live-path audit.
v4.93 2026-10-04  OTV4TEST r244 (LIVE.1 B2, MIRROR OF otv4 r466 579354d, WA 38.2) — AN ERROR AFTER place_order NO LONGER FORGETS THE ORDER: execution/order_guard (after_failure cancels, records the order as suspect and pages; clear_to_post blocks the intent until the broker says CANCELLED/EXPIRED/REMOVED/PARTIALLY_REMOVED/REJECTED, pages once on FILLED, blocks when unreadable); the failed rung is refused. Code hunks applied verbatim; ONE hunk hand-placed: the butterfly guard sits after _fly_key and before this tree's r224 FLY.1 cap block (mainline's butterfly lines differ).
v4.92 2026-10-04  OTV4TEST r243 (LIVE.1 B1, MIRROR OF otv4 r465 7562317, WA 38.2) — reconcile reads ONLY this box's instrument family (SPX = SPX+SPXW; '*' = the whole account) and checks EVERY leg at its QUANTITY (summed across rows sharing a leg); a missing leg or a count off the broker is REPORTED (plan.mismatch + an alert), rows are never dropped, the phantom rule unchanged. The operator, 2026-10-04: 'multiple boxes will trade that account but never duplicate symbols ever.' Code hunks applied verbatim from 7562317.
v4.91 2026-10-04  OTV4TEST r242 (LIVE.1 B0, MIRROR OF otv4 r463 c912ce7, WA 38.2) — every Account call goes through tasty_client.sdk_result: on tastytrade 13.x the Account methods are coroutines and a bare call placed and closed NOTHING live (paper never calls them). Hunks applied verbatim from c912ce7.
v4.90 2026-10-04  OTV4TEST r235 — the Service mode line also says ORCS=on/OFF (config.ORCS_ENABLED), so whether the trade is armed is read from the log, never from the unit (WA 18a). SPX-TEST's agent could not tell.
v4.89 2026-10-04  OTV4TEST r234 (SCALE.1) — the Service mode line ends with the box's contract_scale and where it came from (SPX default / OT_CONTRACT_SCALE / default / IGNORED), so the number ORCS sizes its wing with is on the record at every start. Appended - nothing parses the line.
v4.88 2026-10-03  OTV4TEST r230 (PREM.5) — AN ORCS LEG IS BOOKED WITH THE CONDOR LEG'S STOP (credit x (1 + CONDOR_LONE_STOP_PCT)) and its alert states the condor's exits. The operator, 2026-10-03 21:21 ET: "On rolling/defending the ORCS, adopt the condor logic verbatim." Still its own strategy name, still paper only. _open_credit_legs / _open_credit_sides still leave ORCS out: they decide which OTHER entry may pair with an open leg (the sweep and the TCS, both retired), not how a pair is defended.
v4.87 2026-10-03  OTV4TEST r222 (ORP.1) — THE OPENING RANGE HAS AN OFFICIAL PRINT, AND EVERYTHING REFERS TO IT. The operator,
      2026-10-03: "On a blind start, agree. Yes, make it the official print & refer everything to it."
      _verify_official_print(state) runs each tick once the range is established: when all five 1m bars
      09:30-09:34 are on the feed it compares their high and low with the engine's range. Equal: verified,
      said once. Different (2026-09-29: a blind open froze the low at 739.62; the bars say 737.67): the
      engine is corrected and orb_range.json rewritten IF the sequence has not started; if a break is already
      on the books it WARNS and changes nothing. _opening_range(ctx) returns the engine's range first and
      recomputes from the tape only when the engine has none.
v4.86 2026-10-03  OTV4TEST r213 (REC.1) — THE RECORDERS' MISSING INPUTS ARE PUBLISHED. derived/notes, derived/snapshot and the
      plan ledger read ten ctx keys that nothing ever set (the 10-03 audit, B12), so the note and fire-snapshot
      fields built from them were NULL on every row. _publish_recorder_keys(ctx), called right after
      _apply_vol_ports and before the engines, sets each from a value the tick already holds: expected_move
      (= expected_move_iv), gex_pin and pin_concentration (the GEX snapshot), prev_close (the gap measurement),
      fork_rails and fork_state (the rail projection), swept_level_price / kind (the session's latest REJECTED
      event). setdefault only; each wrapped; a value that cannot be read stays absent. Record-only.
v4.85 2026-10-03  OTV4TEST r211 (PLN.2) — _attempt_orcs opens each leg's plan_ledger row right before executing it.
v4.84 2026-10-03  OTV4TEST r208 (CAP.4) — _execute_condor_leg hands each new credit leg to risk_manager.note_entry_risk
      after log_entry (the log-only cap counterfactual; entry_engine does the same for every other entry).
v4.83 2026-10-03  OTV4TEST r206 (PREM.3) — _attempt_orcs wording only: ORCS signals are priced at the mark and the house
      credit entry (_execute_condor_leg: paper the mark, live the entry ladder) governs the fill. No logic
      change in this file.
v4.82 2026-10-03  OTV4TEST r204 (PREM.2) — ORCS TRADES ON PAPER; THE SWEEP AND THE TCS ARE RETIRED. The operator: "I want to
      paper trade it Monday. Retire the sweep & TCS. Call this new one the opening range credit spread ORCS."
      _attempt_orcs asks strategy/orcs.py inside the entry dispatch (admission, the cap and the entry gate all
      apply) and executes each offer that filled at its limit through _execute_condor_leg, which books ORCS
      under its own name with no stop and REFUSES it in live mode (paper only until a live ruling).
      _safe_strategy skips SweepCreditSpread, SweepForLeg2 and TrendCreditSpread with a `retired` row unless
      their switch is on. r203's _ask_open_premium is replaced by _attempt_orcs.
v4.81 2026-10-03  OTV4TEST r203 (PREM.1) — THE OPENING PREMIUM SPREAD PLAN IS ASKED EVERY TICK, RECORD-ONLY.
      _ask_open_premium(ctx) runs after the entry dispatch on both branches of the loop (position open or
      flat), hands the plan the chain, the gap and two recorded informers, and never raises. No order, no
      signal, no admission rule: strategy/open_premium_plan.py only writes its plan rows. OT_OPS_PLAN=0 parks it.
v4.80 2026-10-03  OTV4TEST r200 (AUD.8, SHARED SHAPE) — vix_at_entry IS STAMPED FOR EVERY STRATEGY. _stamp_vix
      copies ctx["macro"].vix onto the signal at the top of both executors (_execute_entry_signal and
      _execute_condor_leg) when the strategy did not set it. Only ORB and VOLT ever did, and both are off, so
      vix_at_entry was 0.0 on 141 of 194 closed trades since 09-21. Record-only: nothing gates on the field.
      is_fed_day is NOT touched - its detector (macro_data._check_fed_day) has always returned False; separate.
v4.79 2026-10-03  OTV4TEST r196 (AUD.5) — THE VOLATILITY MEASURES ARE ON ctx BEFORE THE DERIVED ENGINES RUN. The
      realised-vol / VRP / expected-move summary sat in _apply_derived_ports, which runs AFTER run_all, so the
      character engine sampled realised_vol_cc and realised_vol_parkinson as None on every tick: vol_ratio,
      close_capture and both realised vols NULL on 3,580 of 3,580 character_axis_sample rows since 09-12 (the
      10-03 audit) - the data the day-type bands were to be fitted on. The block is MOVED into
      _apply_vol_ports and called before run_all (r133's fix for the chain and GEX, a third input). The fire
      snapshot and plan stamps taken inside run_all now see the same values too. Record-only: no gate reads
      a character state while BANDS_SET is False.
v4.78 2026-09-30  OTV4TEST r178 (CAP.2) — AT THE DAILY CATASTROPHIC LOSS CAP THE TWO BUTTERFLIES ARE STILL ASKED. The operator, 2026-09-30: "Allow both flies to fire even if we've hit the cap. Only one of each TYPE per session, not one butterfly per session." attempt_new_entry no longer returns at is_halted(): it runs the session gate and the admission table (position_manager v5.9 refuses every strategy but a cap-exempt one on the cap), then asks ONLY `_attempt_butterfly` and returns - no other strategy is reached. FAILS CLOSED: if the admission table cannot be computed while capped, nothing is asked. One of each type per session was already the rule (r85) and is unchanged.
v4.77 2026-09-29  OTV4TEST r175 (SYM.1) — main() REFUSES A SYMBOL THAT IS NOT ON THE LIST (config.INSTRUMENT_LISTED), exit 78 like r146's unset refusal and before any login or alert. Until now an unlisted OT_INSTRUMENT traded on a silent $1 strike step (STRIKE_INCREMENTS.get(INSTRUMENT, 1)).
v4.76 2026-09-27  OTV4TEST r168 (EXP.1 item 3) — THE HEARTBEAT. `_touch_heartbeat` writes data/BOT_HEARTBEAT at the top of every main-loop pass (never raises; a failed write warns once), read by the new out-of-process emergency watchdog as its liveness signal. Nothing that trades, sizes or exits is touched.
v4.75 2026-09-27  OTV4TEST r165 (EXP.1) — AN EXPIRED POSITION BOOKS ITS SETTLEMENT VALUE. Boot Step 1 passes close_expired_open_trades a `settle` built from broker_reconcile.settle_expired and `_settlement_spot` (the underlying's 16:00 settlement close from this box's feed store, read-only), and `_close_phantom_with_recovery` settles an expired phantom the same way before falling back to the flagged $0.00. The live broker reconcile then reads SHARE positions: any in the box's instrument is an exercise/assignment footprint and pages (send_exercise_footprint_alert). Nothing that trades or exits is touched.
v4.74 2026-09-27  OTV4TEST r162 (CAP.1) — the entry gate's halt line and the startup lines name the DAILY CATASTROPHIC LOSS CAP and say it RE-OPENS once closes bring the realized loss back under the limit (risk_manager v4.8 no longer latches). The gate itself is unchanged: it still blocks only NEW entries; open positions are managed as before.
v4.73 2026-09-27  OTV4TEST r161 (SIZE.2) — PER-TRADE SCALING SWITCHES. `_scaling_on(signal)` reads config.SCALE_ORB / SCALE_BREAKOUT / SCALE_VOLT by the strategy's own name and the entry path passes it to size_for(scaled=...); OFF sizes FLAT (the budget rule) after the r93 noise floor, and the signal's structure stop, exits and `sizes_on_geometry` are untouched. Every other strategy returns True and reaches exactly the arithmetic it reached before. The service-mode line names the three switches and the merged MIN, and a unit still carrying the retired OT_ORB_RISK_USD is WARNED at startup (it is no longer read: ORB_RISK_USD is RISK_PER_TRADE_USD by the operator's ruling, "Merge it").
v4.72 2026-09-26  OTV4TEST r149 (EOD.1) — handle_hard_close runs the operator's end of day: it passes the tick's spot (the analysis price cache) so a resting close can be priced at its best case; flatten_all labels each close itself; it pages ONLY for a position still open PAST the 15:55 cross (a resting or laddering close before then is expected, and paging on it would cry wolf every afternoon, WA section 17); it no longer logs 'complete — all positions flat' while positions are held or resting. The held-position manage pass runs until 15:50 (the ladder), for the positions without assignment risk. The intraday broker reconcile's wind-down sweeps follow EOD_SCHEDULE — 15:45, 15:50, 15:55 (NEW: before the cross, so a short the broker liquidated since 15:50 is found and its surviving long adopted before the cross fires) and 15:57 (operator: "Agree").
v4.71 2026-09-26  OTV4TEST r146 — main() REFUSES TO START WITH OT_INSTRUMENT UNSET (exit 78,
      EX_CONFIG), as its FIRST act - before logging, the broker login or any
      alert, so a misconfigured unit (Restart=always) crash-loops into the
      journal instead of paging every 10s. The operator: "defaulting the QQQ is not the answer" (2026-09-26).
v4.70 2026-09-25  OTV4TEST r141 — THE NOISE FLOOR ARMS AT THE OPEN. The r93 measurement
      is extracted into `_noise_floor_of(df_1m)` and its hard `>= 10` bars becomes
      config.NOISE_FLOOR_MIN_BARS (3). The 1m frame is session-scoped, so 10 bars
      meant the gate stood down 09:35-~09:40 every day - measured on 2026-09-25,
      three entries on 0.14/0.21/0.31 stops inside a ~0.43 floor, -$3,170, each
      logging "UNMEASURABLE". Median, multiplier and 60-bar lookback unchanged.
v4.69 2026-09-24  OTV4TEST r131 — VOLT SIZES ON THE BREAKOUT MODEL. The operator,
      2026-09-24: *"VOLT needs to adopt the breakout sizing model."* The
      geometry inputs of `_execute_entry_signal`'s sizing block are extracted
      verbatim into `_geometry_inputs(signal)` (ORB/Breakout unchanged, pinned
      by tests/check_volt_sizing.py V4), plus ONE addition: a signal carrying
      `sizing_distance` is sized on geometry with THAT distance. VOLT supplies
      its signal-bar range because its stop is its entry (entry - stop = 0 ->
      the DEGENERATE 1-lot branch). Width is 0 (no opening range), so
      `_size_geometry` takes its risk-sized WIDE STOP branch; the r93 noise
      floor applies to the distance exactly as for Breakout.
      OPTION 2 (operator, same day): VOLT takes Breakout's 1-R CURVE, not a
      flat scale-up. `_sizing_stop_premium(signal)` feeds size_for
      entry - |sizing_delta| x sizing_distance for a signal carrying
      sizing_distance (flat floor + a WARNING if no delta); SIZING ONLY - the
      recorded stop_premium and every exit are unchanged; every other signal
      gets `_sig_num(signal, "stop_premium")` exactly as before.
v4.68 2026-09-23  OTV4TEST r124 — `ctx["level_tape"]` IS NO LONGER BUILT. `_level_tape()`
      read every hourly bar the feed store holds (through derived/level_map's
      load_tape) once a minute, for two readers: the level engine's LEGACY path
      (not live under LEVEL_SOURCE="book") and `board()`'s zone width, which
      now comes from the book the engine builds every bar (levels v6.5, the
      same width - measured equal). The function and its cache are removed.
v4.67 2026-09-23  OTV4TEST r123 — THE OLD LIQUIDITY MAPPER STOPS RUNNING (LVL.15 step 5).
      `get_liquidity_mapper().analyze()` ran every tick over a deep 1h frame
      (`_named_level_frame`) and its output reached NOTHING THAT TRADES — each
      consumer measured before removal: (1) `ctx["level_near"]`, the record
      fallback for `level_strength`/`swept_level_name`, filled NOTHING on any of
      the 138 trades on this box (every non-sweep row is ''/0; the sweep sets
      its own); (2) `publish_tines` only rewrote the map object in memory —
      the rails the sweep trades come from the ForkEngine (r114-r116);
      (3) MarketState `sweep_recent`/`sweep_age_bars` have no reader; (4) the
      readiness engine's sweep track is LOG-ONLY ("Gates NOTHING") and now
      records no sweep; (5) the shadow observer is not installed here; and the
      level engine reads `liq_map` only on its legacy path, which the book
      (LEVEL_SOURCE="book") returns before. The module itself goes in r124 with
      level_map, which still imports it.
v4.66 2026-09-23  OTV4TEST r122 — THE OLD LIQUIDITY LEDGER IS UNWIRED (LVL.15 step 5).
      `_feed_liquidity_ledger` seeded analysis/liquidity_ledger from the old
      mapper's named pools and fed it every closed 1m bar, writing
      data/liquidity_ledger/<date>/QQQ.json each tick. NOTHING ON THIS BOX
      READ IT BACK: no module imports get_ledger but this function, and the
      only file reader is warehouse/s3_push.py, whose service is masked here.
      The level book (derived/level_book, r110) is the record now. The module
      is deleted in the same delivery; the _LEDGER globals go with it.
v4.65 2026-09-22  OTV4TEST r97 — the pin-proximity gate, extracted as
      `pin_proximity_verdict(ctx)` so the checker drives the REAL decision
      rather than grepping for it (section 21). Keyed on the DECLARED
      structure `long_debit`, never a strategy-name list: the butterflies WANT
      this condition and the credit spreads are not directional. PINNING only,
      because negative gamma should INVERT the effect. Fails OPEN and warns.
v4.64 2026-09-22  OTV4TEST r93 — the noise floor is MEASURED FROM THE TAPE at the sizing
      call and threaded into size_for — median 1m bar RANGE over the lookback,
      times the multiplier. Daily, not hardcoded: the floor is a property of
      today's volatility. Stands down LOUDLY when it cannot measure, because
      refusing every entry on a feed hiccup is worse than the defect it closes.
v4.63  2026-09-21  OTV4TEST r85 — ONE BUTTERFLY PER SESSION *EACH*, NOT ONE
      BETWEEN THEM. Operator: *"Two different scenarios for those to fire
      under. And on certain days, we might actually hit both."* The `or` in
      `_attempt_butterfly` generalised r179's ruling past its own words —
      *"Only one GEX Pin butterfly"* names ONE strategy — and blocked both the
      moment either fired, AHEAD of admission, whose table has always said one
      EACH. r178's pin guard is untouched; the same-TICK block stays.
v4.62  2026-09-21  OTV4TEST r84 — EVERY `_plan_skip` SITE PASSES ITS GATE.
      MEASURED: 15 of 16 passed none, so every refusal that was not the clock
      reached the board unlabelled and rendered as a bare HELD — including the
      butterflies' one-per-session quota. `_plan_skip`'s own docstring warned
      that recovering a gate by parsing the reason is how the rule stops
      working; 15 sites ignored it. `_plan_skip_all` gains the field too.
v4.61 2026-09-21  OTV4TEST r72 (CTRL.1) — VOLT dispatched ADDITIVELY beside the
      Breakout, so all five morning arms see the same setups and no arm's
      outcome is hidden by another's fill (r51's ruling, applied to the GATES
      rather than to four theses). Declared `long_debit` in _STRUCTURE_BY_NAME
      rather than left to the fallback — that map's own warning is that a
      missing name is silently long_debit, and relying on a default to be right
      is how it stops being right.
v4.60 2026-09-20  OTV4TEST r67 (BOX.9) — THE STOPPED ALERT NAMES WHICH SHUTDOWN
      IT WAS. The SIGTERM handler hardcoded "systemctl stop/restart", so a hand
      stop, a bake and the midnight backstop were one sentence on the emergency
      channel and the operator told them apart by the clock. It now reads the
      stamp the automated paths leave (`utils/shutdown_cause`), and fails
      closed onto the old wording. No trading path touched.

v4.59 2026-09-19  OTV4TEST r61 (ENT.1) — NO TRADE OPENS ALREADY THROUGH ITS OWN
      STOP. `_execute_entry_signal` refuses, STRICTLY, any signal whose live
      price is at or beyond its own protective stop. Surfaced by the mainline
      control agent (8 of 154 ORB trades, -$2,792 there; 0 of 10 measured here)
      and verified in this tree by reading: orb_strategy.py:280-281 and
      breakout_plan.py:162-163 each build entry and stop two lines apart with
      nothing comparing them, and a sweep of the entry path for such a guard
      returned empty. Placed at the ONE funnel every entry opens through, not in
      each strategy, so a new strategy inherits it. Gated on
      `underlying_stop_is_thesis` because LiquidityHunt writes a thesis line
      into the same column and entry beyond it is that setup's normal state.
v4.58 2026-09-19  OTV4TEST r55 — GEOMETRY SIZING IS SUPPLIED, NOT NAMED.
      🔴 This read `if signal.strategy_name == "ORBStrategy"`, so Breakout — the
      ORB without the retest, carrying the same geometry — fell through to
      `_size_budget`, the RESTRICTIVE rule. The operator asked for it "sized the
      same as the orb"; it was not, and nothing said so because both paths
      return a SizingResult. ⚠️ `RiskManager.size_for`'s own docstring forbids
      exactly this list: geometry is selected by the caller SUPPLYING the
      geometry, and "does not get added to a list somewhere that later rots."
      The sizer refused a name list; the caller kept one anyway.
      Now keyed on an explicit `sizes_on_geometry` flag — NOT on
      `orb_range_high`, which the hunt and runaway also carry.
v4.57 2026-09-18  OTV4TEST r51 (BRK.1) — BREAKOUT IS DISPATCHED, and
      `ctx["_flow_conn"]` FINALLY HAS A PRODUCER. The second is the larger
      find: that key is read by `derived/notes.py` and `derived/snapshot.py`
      and was set by NOTHING, so `order_flow.aggression()` on that path had
      never run — 400 sampled `strategy_note` payloads carry the `tape` key
      ZERO times. A consumer with no producer, failing quietly because absence
      and "measured as zero" look identical downstream.
      Breakout dispatches beside the hunt and the ORB, all three born from the
      same opening range and admitted in the same window, non-competing by the
      operator's ruling — the head-to-head is the point, because under a
      cascade the losing arm's outcome is unobservable.
v4.56 2026-09-18  OTV4TEST r49 — A FILL STILL ENDED THE TICK IN ONE BRANCH.
      The sweep's credit-leg branch did `_execute_condor_leg(...)` then `return`
      — the identical early return r43 deleted from the TCS block, in a branch
      it did not reach — so a sweep fill silenced every strategy below it.
      MEASURED LIVE: the sweep filled at 12:34 and `IronCondorStrategy` sat on
      the dispatch-gap default for 204 minutes, 140 lines below that return.
      Found by the operator READING THE PLAN BOARD, not the code.
v4.55 2026-09-18  OTV4TEST r43 (ADM.1) — EVERY ADMITTED STRATEGY FIRES ON ITS
      OWN. Operator: *"I want the orb, hunt, breakout & sweep all able to fire &
      non-competing… In live trading, we will revert back to hierarchy-based."*
      🔴 THE `signal` CASCADE *WAS* THE COMPETITION — one variable, five
      `if signal is None` guards, winner-take-all — so removing
      `has_blocking_position()` alone would not have delivered this. Live
      evidence, 2026-09-18: TrendCreditSpread, GEXPinButterfly and ATPButterfly
      sat on "slot claimed by RunawayContinuation" for THIRTY-FIVE MINUTES,
      never asked. Each strategy now runs through `_fire()`, on r12's proven
      `_attempt_hunt` shape. The afternoon-debit gate moved INTO `_fire`: with
      no single winner, a tail gate catches only the last signal.
      ⚠️ ALWAYS ADDITIVE — a second fire must append, never replace, or
      `set_open_position` drops the first position from management.
      ⚠️ THE POSTURE IS TEST-BOX-ONLY. The fleet reverts to hierarchy, and the
      table overlays from `config.ADMISSION_RULES`, so that is CONFIG, not a
      revision.
      🔴 AND I DELETED `_attempt_butterfly`, THEN PUT IT BACK — RECORDED RATHER
      THAN TIDIED. Inlining it destroyed a TESTABLE SEAM: `check_atp_butterfly`
      drives that function directly to prove the one-per-session cap and
      crashed on "module 'main' has no attribute '_attempt_butterfly'". A
      behaviour reachable only through a 700-line dispatch stops being tested.
      It is now THE one butterfly path. ⚠️ It also carries r178's
      `mark_pin_played` — the guard against the 2026-08-28 stack of five
      butterflies in ninety seconds — which the in-dispatch copy NEVER called,
      so that guard had only ever covered one of the two paths that could fire
      one. Keeping the function keeps it by construction.
v4.54 2026-09-18  OTV4TEST r42 — ADMISSION IS ONE PASS. `attempt_new_entry`
      asked `eligible_now()` for the LIST and then `why_not()` per refused
      strategy for the REASON — two calls, the same facts passed twice, and
      nothing making them agree. Pass one fact differently to the second call
      and the board reports a gate that is not the one that actually refused:
      wrong in the log, and unfalsifiable FROM the log. `logging_state()`
      returns both from a single walk. `_plan_skip` now carries the GATE as its
      own field, because the board keys the say-it-once rule on it.
v4.53 2026-09-18  OTV4TEST r41 — A REFUSED STRATEGY NAMES THE GATE THAT REFUSED
      IT. r40 gated the dispatch on the admission table but told the plan board
      nothing, so a strategy refused for being outside its window had no reason
      recorded and fell to `plan.py`'s default — *"no reason recorded … that is
      a dispatch gap, not a market condition"* — wording chosen deliberately to
      read as a DEFECT. An ordinary out-of-window strategy would have reported
      itself as a bug, every session. `why_not()` was built for exactly this and
      returns the FIRST gate that refused; the row now names it.
v4.52 2026-09-17  OTV4TEST r40 — THE ADMISSION TABLE IS LIVE. r35 moved every
      entry gate into `execution/position_manager.py` and left it INERT:
      *"NOTHING IS WIRED YET — attempt_new_entry still runs the old gates."*
      `attempt_new_entry` now asks `eligible_now()` ONCE a tick and
      `_safe_strategy` — the one funnel every entry dispatch already routes
      through — refuses everything not on the list. One test, seven call sites,
      and THE CASCADE ORDER IS UNTOUCHED (r35: that order is load-bearing).
      🔑 A refused strategy is NEVER ASKED, so `_plan_board.asked()` is never
      reached and there is no per-tick refusal to journal — which is what ends
      the 10,116 `NOT ASKED` rows written on 2026-09-17 alone.
      ⚠️ FAILS OPEN BOTH WAYS, DELIBERATELY: no admission computed for a tick
      means every name passes (pre-r40 behaviour exactly), and a name the table
      does not carry passes, because `IronCondorStrategy` is retired as an entry
      and management dispatches are not admission's business. A table that
      silenced an unknown name would make ADDING a strategy a silent no-op.
      ⚠️ CLEARED AS THE FIRST STATEMENT of `attempt_new_entry`, before any gate
      can return past it — `_ADMITTED` outlives the call, and a stale set would
      gate this tick on a window that has since closed (r207's class).
      🔴 `has_blocking_position()` IS STILL CONSULTED on the open branch and
      that is STATED SCOPE, not an oversight — see ADM.1. Removing it orphans
      `_attempt_butterfly` and `_attempt_sweep_on_grant`, which are NOT
      redundant with this function: the first is r161's ADDITIVE EXEMPT path,
      this function's own butterfly COMPETES for the slot behind
      `elif signal is None:`. Same strategy, two different questions.
v4.51 2026-09-18  OTV4TEST r36 — `ctx["level_tape"]` is the feed store's HOURLY
      tape, not its 1m one. Retention keeps 1m for five days and 1h for sixty, so
      the board reached nine days back and now reaches twelve weeks. Measured:
      merged 1h reproduced the merged-1m 24-hour high AND low to 0.00 on every
      day both series cover, and the mapper's sections are already hour-granular.
      The rejection fact is untouched — `_derive_events` reads `ctx["df_1m"]`.
v4.50 2026-09-14  OTV4TEST r29 — `ctx["level_tape"]`: the feed store's 1m tape (SYM and
      SYM_EXT merged) handed to the level engine, which builds the session levels
      from it (levels v5.0). Read at most once per minute; None when the store
      cannot be read, which yields no session levels and retires nothing.
v4.49 2026-09-14  OTV4TEST r26 — THE ATP BUTTERFLY IS ASKED, AND THE SESSION HAS ONE BUTTERFLY.
      Operator: "allow one butterfly or the other, whichever plan produces a
      viable trade 1st can take it." Both butterfly sites — the in-dispatch slot
      and `_attempt_butterfly` (the position-open branch) — ask GEXPinButterfly,
      then, if it did not fire, ATPButterfly (their reach bands are complements,
      0.30-1.00 vs <= 0.30 of the EM, so on one tick at most one can be viable and
      the order decides nothing). The r179 trades.db cap now counts EITHER name
      before asking either, so a butterfly of one kind ends the day for both. A
      tick where the pin fly fired writes the ATP's row as a skip rather than
      leaving it NOT ASKED. `_STRUCTURE_BY_NAME` maps it to "butterfly"; without
      that the afternoon cutoff would have treated it as a long debit.
v4.48 2026-09-13  OTV4TEST r24 — THE SWEEP'S PREMIUM STOP IS 15% OF RISK, AS SPECIFIED.
      `_execute_condor_leg` stamped the sweep's `stop_premium` as 15% of the
      CREDIT — the inverted rule r155 deleted — and the management plan acts on
      the row, so that is the stop that fired: Friday's 12:04 spread (credit
      0.25, stop 0.2875) was cut the same minute and then expired worthless.
      `_sweep_stop_premium` computes credit + `criteria.stop_distance`, the one
      definition the exit engine and entry feasibility already use; it fails
      closed to the old stop, logged, when risk cannot be measured. TCS keeps no
      stop; condor legs are unchanged. check_sweep_stop S1-S4.
v4.47 2026-09-13  OTV4TEST r20 — THE ORB IS PASSED NO LEVEL SURFACE. Operator's
      ruling: levels out of the ORB trade entirely. The `liq_map` argument is
      gone from the ORB's `generate_signal` call site; the sweep's own call
      sites are UNTOUCHED, because the sweep genuinely trades off sweeps at
      levels. Everything else reading `ctx["liq_map"]` — the ledger feed, the
      board, `publish_tines` — is unchanged.
v4.46 2026-09-10  OTV4TEST r12 — THE LIQUIDITY HUNT AND THE HANDOFF GRANT (PLAN_SPEC
      §37). The hunt is asked every tick beside the ORB — from the no-position
      chain and from the position-open branch — and executed ADDITIVE; it takes
      no slot (position_manager v4.9). On its target's wick it writes a grant;
      `_attempt_sweep_on_grant` lets the sweep enter on a live grant even while
      an ORB is open, the grant answering the slot question only.
v4.45 2026-09-09  OTV4TEST r11 — the tent call is gone (the ladder is two rungs);
      the sweep's complement is handed the open leg's richness so "the second
      leg is rich or we don't take it" is a bar the plan reports.
v4.44 2026-09-09  OTV4TEST r10 — the roll is handed the 1m frame (tested by wick,
      condor_roll v4.7); `IronCondorStrategy` is retired as an ENTRY — a condor
      forms from two credit spreads — and its row says so instead of the
      "dispatch gap" NOT ASKED. The management plan is unchanged in shape.
v4.43 2026-09-09  OTV4TEST r9 — the TCS is handed `atm_iv` (its EM band) and
      the 1m frame (the frozen reference band); its trigger is the level
      store's ACCEPTED, not the ORB latch. `_credit_window_end` reads the
      TCS and sweep windows from their PLANS (HYG.5 closed: main.py no longer
      reads the TCS end-of-window constant from config; the sweep's
      09:35–14:00 tuple is the one the remainder honours).
v4.42 2026-09-08  OTV4TEST r5 — the derived ctx carries the ORB data (`orb`) so
      derived/levels can retire every level inside the 5-minute opening range
      (operator: "NO LEVELS can exist inside the 5-minute opening range"), and
      the SWEEP is asked every tick of 09:35–14:00 with the chain and the 1m
      frame, its plan preparing both sides from the level store; the r167
      "sweep is afternoon-only" NOT ASKED row and the private wick detector are
      gone — the trigger is the REJECTED fact.
v4.41 2026-09-08  OTV4TEST r3 — THE RUNAWAY IS ASKED EVERY TICK OF ITS WINDOW,
      hands its plan the 1m frame (strength at acceptance, re-validation on
      actual), and no longer carries the r179 one-per-session cap: one per
      BREAK on any exit is the plan's rule now, and a new break is a new
      trade, as it is for the ORB. `prev_close` is no longer passed — the
      trigger is the engine's `fifty_accepted` latch. The "ORB has not run
      away" NOT ASKED row is gone; the plan says what it is waiting on.
v4.40 2026-09-08  OTV4TEST r2 — ORB IS ASKED EVERY TICK OF ITS WINDOW, NOT ONLY
      WHEN CONFIRMED. The plan (strategy/orb_plan.py) now writes the ORB row
      from 09:35 — both candidate contracts priced, then the armed side with
      its stop/strike/floor/size — so the dispatch stops gating the call on
      `orb_confirmed` and stops writing its own "not a confirmed break+retest"
      NOT ASKED row: the plan says what it is waiting on. The two facts only
      this file knows travel as kwargs: `now_hhmm` (the window) and
      `offer_working` (a standing offer resting for a confirmed setup — was a
      `_plan_skip`, now a named DECLINE on the plan row). The afternoon-debit
      block is unchanged and still precedes the call. Nothing about sizing,
      the fill, the latch or the engine re-read moved.
v4.39 2026-09-08  r315 — THE CREDIT LADDER WALKS THE WAY THE OPERATOR SPECIFIED,
      AND A PARTIAL FINISHES FILLING. War-gamed 2026-09-08 on synthetic tape,
      real entry_ladder/ladder_registry, driver reproduced from this file at
      HEAD 0498534. Three defects, one path (`_execute_condor_leg`):
      (1) `confirm_order_fill` was called with NO `deadline_s`, so every credit
      rung held the tick loop for the full 20s entry budget plus up to 6s of
      cancel grace — 4-5x the slice entry_engine gives its own rungs, ~2.5 min
      of frozen ticks for a six-rung nickel walk and ~10 min on the 24-rung
      penny table `rungs()` returns for a 0.00/1.00 book. Now the same
      `_rung_deadline()` slice (max(4, 20/4) = 5s).
      (2) A PARTIAL booked the filled size, cancelled the rest, refused the
      rung, and RETURNED; next tick `has_open_position()` sent the box to the
      manage branch where every credit strategy is `_plan_skip`'d, so the
      remainder had no order and no caller — the comment at the old 2332
      ("must resume one rung further in") described an intent nothing could
      honour. Now `execution/credit_remainder.py` registers the remainder and
      `_supervise_credit_remainders` posts one rung per tick for it from
      BEFORE the split (the r195 `_supervise_offers` shape), accreting fills
      into the existing record — one position, one row, blended basis.
      (3) The walk was keyed on the STRIKE PAIR while TCS re-selects the
      nearest OTM strike from CURRENT price every tick, so on a tape crossing
      a strike per tick every pair started a fresh walk at the 25% opener and
      never reached mark. Now keyed on the INTENT (`cv:<sym>:<strategy>:<side>`)
      with the structure passed as a tag: the rung carries across a
      re-selection, the price ratchet does not (entry_ladder v4.2).
      🔑 `_post_credit_vertical` is the ONE placer both the entry and the
      remainder use, so they cannot price differently. Injectable for tests.
      ⚠️ Paper untouched: mark, 100%, no partials.
v4.38 2026-09-06  r288 / DEV.11 — THE DISK GUARD LIVES HERE NOW. It was at the
      top of `candle_feed.run()`'s `while True`, which is the RECONNECT loop,
      not a tick loop: an `async with DXLinkStreamer` below it opens the stream
      and an INNER loop handles events for the life of that connection, so the
      check ran ONCE PER CONNECTION — at startup, then not again until the
      stream dropped. 📊 MEASURED: the feed restarted 17:24:14 UTC, a drill was
      armed a minute later, and the flag was still present.
      🔑 THIS loop ticks on POLL_INTERVAL_SECONDS, and the call sits beside
      `_apply_log_level()` — "one stat; DEBUG flips with no restart" — the same
      idiom for the same reason.
      ⚠️ ABOVE THE RTH BRANCH: a box left up over a weekend is exactly when
      nobody is watching, and the disk does not care whether the market is open.
      ⚠️ AND `optionsbot` IS THE SERVICE THE DEPLOY PATH RESTARTS, so a bake
      arms the guard without a separate candle-feed bounce — the operator's own
      point, made before the measurement confirmed it.
v4.37  2026-09-04  r239 — 🔴 `_note_evaluation` CANONICALISES THE DISPATCH
      LABEL. `DISPATCH_ALIAS` has existed since r147 and is applied by the plan
      board (plan.py:791, :833) and by `gate_report` (:118) — and NOT by the
      one writer of `strategy_note`. So the ORB's fires were stamped "ORB"
      while its plan and gate rows used "ORBStrategy", and the fit report saw
      TWO strategies: one with 78 fires and ZERO declines, one with zero fires
      and 4,260 declines. Neither arm could ever be fittable and the report
      said NOT READY for both, for opposite reasons.
      ⚠️ A LOOKUP, NOT A RENAME. Renaming the dispatch label would fix tomorrow
      and leave five sessions of history split; the alias reads both.
      ⚠️ `SweepForLeg2 -> SweepCreditSpread` comes along with it, which is
      r160's ruling — already true of the plan board, silently untrue here.
v4.36  2026-09-04  r238 — THE TCS DISPATCH NOW PASSES `orb`. Its
      trigger is the ORB engine's `fifty_accepted` and its level is
      `target_50pct`, so the strategy needs the engine it was explicitly
      built without. `generate_signal`'s old docstring said "NO `orb`
      PARAMETER... there is no morning level worth anchoring to" — true of
      the BOUNDARY, which the operator has now ruled out as an anchor, and
      untrue of the 50, which is the whole basis of the rewrite.
v4.35  2026-09-02  r220 — 🔴 CREDIT VERTICALS POSTED A STATIC LIMIT AND NEVER
       WALKED IT. Every other live entry prices through `ladder_registry` —
       `_place_single_leg` and `_place_butterfly` both call `_walk_price` —
       and only ORB is exempt BY DESIGN (`_place_standing_offer`: "ORB only:
       ONE limit at the mark, posted once, left to rest"). The credit
       verticals were not exempt, just never wired: a spread that did not
       fill at `net_credit` sat there instead of conceding.
       ⚠️ OPERATOR 2026-09-02: "everything but ORB using ladder entries", and
       on direction: "the walk for credit spreads is from the top. Best price
       that will fill."
       🔑 THE STRUCTURE QUOTE IS BUILT PER LEG, never the combined mark plus a
       shade (limit_ladder v1.1's recorded mistake). Selling the spread, the
       best credit is `short.ask - long.bid` and the worst `short.bid -
       long.ask`; their midpoint is `short.mid - long.mid`, which is EXACTLY
       what paper books — so live walks down from the best credit, stops at
       mark by the ladder's own rule, and live and paper share a floor.
       ⚠️ AND THE WALK IS ADVANCED: `refuse` on a non-fill (a PARTIAL counts,
       per the operator's definition), `clear` only on a COMPLETE fill. A
       ladder that never advances is the static limit with a new name.
v4.34  2026-09-01  r213 (chunk E) — THE FLAT BRANCH SAYS WHY THE MANAGEMENT
       PLANS ARE QUIET. `_plan_skip_management("no open position — nothing to
       manage")` on the else side of the `has_open_position()` split. Until
       now only the position-open half explained itself, so a flat session
       printed "dispatch gave no reason" against CondorManagement, CreditRoll
       and every `<Strategy>/manage` row on every tick.
       ⚠️ CONTRIBUTOR-ONLY, AS ALL BOARD CALLS ARE: wrapped, never raises, and
       cannot affect dispatch. The membership list lives in strategy/plan.py
       so a new management plan is covered by registering rather than by
       someone remembering to edit a list here.
main.py  v4.33
v4.33  2026-09-01  r207 — THE DISPATCH ASKS THE ENGINE, NOT THE TICK'S COPY.
       `orb = ctx["orb"]` bound the ORBData instance at the
       TOP of the tick and the ORB dispatch read it at the BOTTOM. On the tick
       where `manage_open_position()` closes an ORB, `notify_position_closed()`
       calls `_rearm()`, which REPLACES `self._data` — so the ctx reference
       became an orphan still reading OPEN_SHORT, `has_blocking_position()`
       was now False, and `attempt_new_entry()` ran in that same tick against
       a corpse. QQQ 2026-09-01: two ORB shorts on one confirmation, the
       second entered at the exact premium the first stopped out at. This is
       r96's orphaned-dataclass defect one level up, at the manage→entry seam.
       The dispatch now reads `get_orb_engine().data` and says so at WARNING
       when the tick's copy disagreed, because the mismatch IS the bug and
       silently papering over it would hide the next one.
       ⚠️ `_orb_d` IS UNCHANGED, AND AN INTERMEDIATE CUT OF THIS REVISION HAD
       IT WRONG. That cut sized on the boundary-to-wick distance frozen at the
       break. Operator: "the true risk is based on where we entered, not the
       range boundary. That is arbitrary. The 2 factuals are the distance from
       entry to the stop." Correct, and the frozen version was also solving a
       problem the latch above had already removed — the QQQ 2-then-24 was an
       illegitimate FIRE, not a mis-sized one. Sizing stays entry-to-stop.
main.py  v4.32
v4.32  2026-08-31  r205 — ATM IV IS STORED ON ctx. It was computed in two
       butterfly dispatch branches as a LOCAL and never assigned, so every
       fire_snapshot row carried a null atm_iv (measured: 31/31 rows across
       13 symbols) and volatility_measures.summarise has derived
       expected_move_iv and VRP from None since it was written. Both branches
       now read the one stored value, so dispatch and snapshot cannot
       disagree about the same tick.

main.py  v4.31
v4.31  2026-08-31  r201 — the ORB budget is announced at startup and in the
       banner, and says when it is the DEFAULT. An unconfigured box sizes a
       1-lot on an index name, which reads as a defect unless it is named.

main.py  v4.30
v4.30  2026-08-31  r197 — A BUTTERFLY BLOCKS NOTHING. A box holding only a
       butterfly is managed AND still asked for entries; `additive` is now
       decided by what is actually open rather than by the call site, so an
       entry alongside a butterfly cannot drop it from management. Credit
       remains blocked by an open ORB or runaway debit. See
       execution/position_manager.py has_blocking_position().

main.py  v4.29
v4.29  2026-08-30  r195 — ORB'S RE-ARM MOVES FROM SIGNAL-FIRED TO
       TRADE-RESOLVED, and one standing offer per setup. See
       analysis/orb_engine.py v4.2 for the sequence this restores.

main.py  v4.28
v4.28  2026-08-30  r195 — THE STANDING OFFER IS SUPERVISED FROM BOTH LOOP
       BRANCHES. `_supervise_offers` runs BEFORE the has_open_position()
       split, so an offer with no fills yet — which has no trade record and
       therefore no position — is still polled, adopted and cancelled. Put
       it inside the manage branch and every unfilled offer is watched by
       nothing. See execution/resting_orders.py v1.0.

main.py  v4.27
v4.27  2026-08-30  r192 — SIZING NORMALIZED, AND ORB GEOMETRY IS ACTUALLY
       ACTIVE. Every size now comes from `RiskManager.size_for(structure,...)`
       and arrives in `sizing.contracts` — the field `entry_engine.enter()`
       has always ordered. The r181 override that lived in this function is
       DELETED, not rewired: it assigned `signal.contracts`, written 4x and
       read 0x tree-wide, so ORB has sized ONE LOT since the 08-28 bake while
       logging "-> N (was M)". 🔴 A sizing rule applied by the CALLER is the
       only kind that can compute a number the order never sees; the repair
       is that this function no longer owns any sizing policy at all.

v4.26  2026-08-28  r181 — ORB RISK-NORMALIZED SIZING, PURE GEOMETRY.
      contracts = max(1, floor(orb_width / stop_distance)); the stop is the
      impulsive candle's low/high (signal.underlying_stop). Worst entry
      (stop ~ width) = 1 lot by construction; a 0.61 stop on a 6.35 range =
      10 lots. Structure-stop dollars equal on every ORB trade. No notional
      cap for ORB by ruling; the 25% floor stays as the gap backstop at
      leveraged size — operator accepted that tail explicitly. Degenerate
      geometry sizes 1, loudly. ORB only; engine and strategy untouched.
v4.25  2026-08-28  r179 — 🔴 ONE PER SESSION, DB-BACKED. Operator: "Only
      one runway debit trade aloud per session on a box. Only one GEX Pin
      butterfly allowed per session on a box. Simple." _one_per_session_used
      reads trades.db (count_today), so RESTARTS CANNOT RE-ARM IT — the
      in-process pin/break registries cleared on every systemd bounce, 08-28
      had five, and that is how the butterfly stacked through two hotfixes.
      Guarded at all three sites: the runaway's dispatch, the in-dispatch
      butterfly path, and _attempt_butterfly's entry. Skips are plan rows;
      fails closed (an unreadable DB counts as traded).
v4.24  2026-08-29  r178: a butterfly fire marks its pin PLAYED (one
      butterfly per pin per session — the 08-28 15:00 stack). Marked after
      _execute_entry_signal so a refused fire does not burn the pin.
v4.23 2026-08-28  r173 — 🔴 HOTFIX: THE FLEET-WIDE ZERO-TRADE MORNING.
      _execute_entry_signal read `signal.stop_premium` with getattr+float;
      that name is a METHOD on OptionsSignal, shadowed by strategies that
      assign the attribute — the r168 runaway leaves the method exposed, so
      the first runaway fire of the day crashed the sizing line, the loop
      catch-all ate the tick, NO strategy could enter on that box, and at 30
      loop errors the service exited and systemd restarted it (the 09:53 /
      10:01 / 10:09 STARTED spam). New _sig_num() resolves attribute or
      method, never raises; the method yields the correct 20% floor. Pinned
      by tests/check_signal_numeric_tail.py, which runs every strategy's
      signal shape through the resolver AND asserts the sizing call uses it.
v4.22 2026-08-27  r167: the narration pass receives the open records so it can
      skip the ones decide() already wrote for. Nothing else changes here —
      the decision seam lives in position_manager v4.6.
v4.21 2026-08-27  r166 — THE MANAGEMENT PLAN IS WIRED. After
      manage_open_position (the exit engine has priced and decided),
      strategy/management.py writes one row per open record — the strategy's
      declared exit conditions with their current readings, "if this or this
      -> out" — and records the r66 derived vector for the open position
      (strategy_note, outcome "manage"). The condor's manage() receives ctx
      and writes its own vector again. Nothing executes here; the exit engine
      is unchanged.
v4.20 2026-08-27  r163 — THE TINES ARE MOVING LIQUIDITY LEVELS; THE DAILY FORK
      STRATEGY IS RETIRED. Operator, 2026-08-27: a tine is *"basically a
      moving level that sweep is allowed to use, but with a touch, not a
      reject"*, and *"it's allowed to be the 1st leg of a condor too, but
      again as a touch."* At the assembly point, right after the condor
      trigger map, `publish_tines` puts every active 1h/1d tine on the
      liquidity map as a MOVING named pool and emits a TOUCH event
      (liquidity_mapper v4.2); the sweep's plan (v4.7) prepares the spread
      beyond the touching move and fires leg one on the touch; leg two never
      selects a touch (a rejection is required). The daily-fork dispatch
      (plan cache, leg triggers, its own construction) is deleted along
      with strategy/daily_fork_credit_spread.py. main no longer overwrites
      the sweep signal's `condor_trigger_source` (a tine touch is classed
      `{tf}_fork`).
v4.19 2026-08-27  r161 — THE BUTTERFLY FIRES REGARDLESS OF OPEN POSITIONS.
      Operator, 2026-08-27: *"I want it to be able to fire regardless if any
      other open trades are found. Reason: it has such a high hurdle to
      clear. GEX pinning, pin reachable, economic feasibility. If it can
      achieve all that, it's earned an entry."* (TRADES.md §3 from r33: "no
      position slot, no capital, no competition".) main_loop now asks the
      butterfly's plan every tick of its slot in BOTH branches — position
      open or not — through `_attempt_butterfly()`, and a fire APPENDS its
      record (`add_open_position`, position_manager v4.4) instead of
      replacing the vertical under management. The execution tail of
      attempt_new_entry is factored into `_execute_entry_signal()` so both
      paths run the same sizing/entry/journal code; `additive=True` is the
      only difference. The condor's authorization no longer skips it.
v4.18 2026-08-27  r160 — THE CONDOR AUTHORIZES AND MANAGES; THE SWEEP PLANS AND
      EXECUTES LEG TWO. Operator, 2026-08-27: one vertical open -> only a
      complementary-side SWEEP is authorized, everything else gated off; the
      condor selects nothing; management begins once leg two is born (roll
      if threatened, tent if breached, close if uneconomical). The second-leg
      window is now: `authorize(open_sides)` -> `required_side` -> the
      sweep's own plan prepares and its spec fires. `plan_second_leg`,
      `leg2_fired`, the pairing-class computation and `required_level` are
      gone. Before the roll/tent execute, `manage()` writes the per-tick
      management row (which rung, what the next rung costs, does it clear)
      on the same numbers condor_roll is about to act on. Rule 4's pairing
      table collapses to sweep everywhere (the fork tine is acceptable for
      leg one; leg two is universally a sweep — the operator's 08-27 ruling).
v4.17 2026-08-26  r147 — THE SECOND-LEG WINDOW ROUTES THROUGH THE CONDOR'S
      ONE-LEVEL PLAN (`plan_second_leg`, iron_condor_strategy v4.6). The four
      direct second-leg attempts (1h fork on approach, 1d fork, sweep, TC.6)
      are removed from main_loop; their levels are candidates inside the
      plan, which fires only on a CONFIRMED REJECTION and moves to the next
      level on ACCEPTANCE. The Rule 4 pairing table is applied here, from
      leg one's trigger source, as the allowed level classes.
v4.16 2026-08-26  r146 — THE PLAN BOARD IS FED FROM DISPATCH. Every point where
      a strategy is NOT asked this tick (halted, outside the session, no
      chain, position open, ORB engine not confirmed, no runaway, slot
      claimed by an earlier strategy, DIRECTIONAL_ONLY, no 1d rails) tells
      `strategy.plan.skipped()` why, and `_safe_strategy` tells
      `strategy.plan.asked()` what was called — so `derived/plans.py` v2.0
      can write a NOT ASKED row for the silent strategies and flag any
      strategy that was asked and wrote nothing. The sweep now receives
      `orb_high`/`orb_low` (the r134 assembly-point values) for its
      session-map geometry check. Dispatch ORDER and every gate are
      unchanged; this narrates the decisions the chain already makes.
v4.15 2026-08-24  r112: DEBUG is a LIVE FLAG (data/DEBUG_LOG, devtools item 69),
      applied at import and on every tick — so it overrides however a box came
      to be in DEBUG, and removing it genuinely restores LOG_LEVEL. No restart,
      survives a bake, nothing git-tracked to edit.
v4.14 2026-08-24  r108: the pre-open rehearsal has a GO-RED TOGGLE (devtools
      item 68, mirroring the feed-maintenance window at 67). data/REHEARSAL_OFF
      on the box, read LIVE every pass, survives a bake. Inverted sense — the
      file's PRESENCE disables — so a fresh or forgotten box rehearses, and the
      menu line goes RED while it is OFF.
v4.13 2026-08-24  r106: the TENT is called after the roll (rung below it, only
      on an already-rolled + breached structure). CONDOR_TP_PCT retired, the
      stop written on every credit row is now the 15% floor the engine actually
      evaluates, and condor_leg_num is always 0 — "no condor implied, merely
      permitted", so there is no leg 1 and leg 2.
v4.12 2026-08-24  r105: the SECOND-LEG WINDOW tries all four credit triggers.
      Its own header said "all four triggers are eligible to fire the
      complementary side"; the code tried the two forks, so a sweep or TC.6
      first leg could never pair and the condor could only ever form from a
      fork. "A second leg is allowed, never expected" was true by omission.
v4.11 2026-08-24  r103: orb_state.json is READ at startup, authoritative
      (operator: "if it wrote it, trust it"), and written from the engine's own
      snapshot so writer and reader cannot drift. A resumed engine still owes a
      gap-fill replay. A MISSED confirmation is ADJUDICATED against the trades
      table before the row is closed — the tape cannot tell "never seen" from
      "taken and recorded before the process died" — and is journalled as a
      disposition with the setup's full geometry, like a decline.
v4.10 2026-08-24  r102: the r101 rehearsal stopped one call short — can_enter
      short-circuited on the RTH gate at DEBUG, so the outside-RTH pass reached
      no strategy (measured fleet-wide 16:53: decided=0 chain=0). attempt_new_entry
      now rehearses outside RTH and every skip on that path is INFO; the pass
      narrates START/STOPPED/END so silence stops being a valid outcome.
v4.9  2026-08-24  r101 DECIDE ALWAYS, PLACE AFTER 09:35 (operator directive).
      The trading half of the loop was never executed until the bell, so a box
      baked at 07:40 ran clean for two hours and died on its first decision at
      09:30:01. The pre-RTH branch now runs assemble_market_state +
      attempt_new_entry with live inputs, and a dispatch failure pages on the
      FIRST occurrence instead of the thirtieth. ENTRY_OPEN_ET gates the two
      order choke points; exits are never gated.
v4.8  2026-08-24  r99 — THREE DEFECTS THAT COST TRADES OR WOULD HAVE. (1) P0:
      `manage_open_position(ms=None)` — r65 renamed the retired label kwarg
      to `ms=` while deleting the parameter, so every tick with an open position
      raised TypeError into the loop catch-all and the loop sys.exit'd after 30
      of them. No position had been managed since 08-22; unseen because no fill
      happened. (2) The sweep credit spread claimed `signal` and went down the
      DEBIT dispatch (scorer, debit sizer, `_place_single_leg` buying its own
      short strike). It now routes pairing gate -> `_execute_condor_leg` like
      TC.6, carrying its own strategy name and its own 15% stop. (3) Credit
      verticals were flattened at 15:40 with the debits — VERTICAL_HOLD_TO_ET
      lived only in an evaluator this window never reached. flatten_all holds
      them to 15:45; a manage pass keeps the 15% floor live in between.
v4.7  2026-08-24  CONDOR REMODEL (v4.3): four independent credit-spread
      triggers (1h_fork, 1d_fork, sweep_reversal, trend_orb). Each vertical is
      standalone; second leg is allowed, never expected. Pairing gate enforces
      Rule 1 (max 2 open) and Rule 3 (never same side twice). CondorTriggerMap
      recomputes fork tines live each tick so trigger levels track the moving
      rail. DailyForkCreditSpread (new) adds the 1d pitchfork as a trigger.
      condor_trigger_source stamped on every credit spread for per-source
      grading. notify_leg_filled removed (no pairing expectation).
v4.6  2026-08-23  AUDIT F9: _safe_strategy reports a FIRE to the gate
      reporter, which is the only way a block ever clears (gate_report v4.1).
v4.5  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

      measure's prior direction moves to BotState.prev_trend_direction,
      committed at the end of each analysis pass — the old carrier
      been a silent 0 and gap_class permanently UNDIRECTED since the split.
      The L1 sweep-score read is deleted for the same reason one level up:
      ctx["l1"] is set nowhere in v4, so the score was a silent 0.0 and the
      journal sections (7 sites), the chain_snapshot label pass, the
      two _L1_BREAKDOWN_FOR rows are removed; heartbeat and NO TRADE lines
      before dispatch on EVERY tick and the fleet traded NOTHING on its first
      stamp go with it. Nothing replaces them, deliberately.
Tick loop, context assembly, strategy dispatch. GATES STRIPPED - see ROADMAP Phase 2.

      the variable - v4 removed both engines it used to choose between - so the
      assert was a gate with no consumer that could only ever refuse to start.
      SMC fork's unit file. A guard outlives the thing it guarded.
v4.1  2026-08-20  AUDIT F4: relaxed_entry copied onto the condor-leg record -
      the tag was set on the signal and dropped before the insert.
v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

main.py — options_trader v6.19
ORB IS BLOCKED UNDER RANGING (operator direction; that
       cell is the conclusive loss leader). Mirrored from options_trader_smc
       so the A/B arms stay comparable. The refusal journals as
       `gate_block:orb_ranging` rather than being a silent absence. Leading
       branch with the existing ladder moved to `elif`, so RANGING is refused
       it. OT_ORB_BLOCK_RANGING=0 restores the old behaviour.
🔴 P0 HOTFIX — run_analysis raised NameError on EVERY tick.
       v6.16 (Level.1) and v6.17 (A2.6b) write ctx["gap"], ctx["gap_pct"] and
       ctx["level_near"] into `ctx`, but run_analysis did not bind that name
       until its return statement. The NameError raised inside the try; the
       except handler's own ctx["gap"] = None then re-raised it UNCAUGHT. Net
       strategy evaluation — the bot trades nothing and the failure is a
       traceback per tick, not a quiet degradation. `ctx` is now bound before
       the Level.1/A2.6b blocks, which write into it; macro/orb are added at
       the single return. NO OTHER BEHAVIOUR CHANGES in this version.
       Found 2026-08-18 during the SMC-fork salvage and reproduced
       behaviourally before the fix; same class as WA §21's
       is_trend_participation NameError — invisible to py_compile.
A2.6b: MEASURE the overnight gap instead of inheriting it
        as an anonymous ATR spike. `atr_series` uses true range with prev_close
        and the 5m tape is continuous, so a large gap spikes ATR at the open and
        decays - every consumer sees a volatility number that is partly last
        night's news and CANNOT TELL WHICH PART. Nowhere was the gap measured
        as itself.
        THE ONLY PRE-OPEN DECISION-TIME INPUT IN THE STACK: ADX, conviction,
        is fully formed at 09:30 before a single RTH bar prints.
        not bound this early in the tick, and a bare getattr would have raised
        into the except and pinned prior_dir=0 forever - making gap_class
        permanently "UNDIRECTED". A silent constant is the failure this whole
        week has been about.
        CLASSIFICATION IMPORTED from tests/gap_backfill.py, never
        reimplemented (7) - and gap_pct is a REAL column with a NULL default,
        because a gap of exactly zero is a real reading.
Level.1: GRADED LEVEL STRENGTH, FOR EVERY STRATEGY.
        `level_strength` measured 94% ties on TWO unique values. Two causes,
        both collection defects:
        (1) the formula was min(1.0, (0.6 if named else 0.2) +
            min(touch_count,4)*0.1) and TOUCH_COUNT IS A CONSTANT - named pools
            hardcode it to 1 and nothing increments it (44,450 of 44,890 ticks
            read exactly 1), so it only ever produced 0.7 or 0.3.
        (2) only `sweep_reversal` wrote it, and sweep is hard-gated with a 0.4%
            live win rate - so 94% of the book carried the column default.
            THE PROBE NEVER MEASURED LEVELS; IT MEASURED AN EMPTY COLUMN.
        Now graded by TYPE with a rung discount (analysis/level_grade.py), and
        `ctx["level_near"]` puts the nearest graded pool in front of EVERY
        strategy each tick. `swept_level_name` had no writer either and now
        does.
        GRADES ARE STATED PRIORS, NOT FITTED - ordering follows resting
        liquidity. Fitting on P&L would repeat the grade inversion (A-grade
        -$8,244 vs B +$1,893).
        UNBLOCKED BY LIQ.6 (rung in the name) AND FEED.2 (ON High/Low real).
STR.2: carry `flat_angle_deg` from the L1 breakdown onto
        attribute - so trades.flat_angle_deg came back 100% tied on ONE unique
        value and the separation probe read it as a measured zero.
        on every RANGING/COMPRESSION evaluation and lands in the breakdown as
        {"angle": ...}. COMPUTED, RECORDED IN THE EVIDENCE, NEVER DELIVERED -
        the same shape as `direction_conf`. Third instance of that class in a
        week.
        THE SENTINEL IS -1.0, NOT 0.0: zero degrees IS the flattest possible
        reading, so a 0.0 default is indistinguishable from a genuinely flat
        tape - exactly the confusion that produced the bug.
        WHY IT MATTERS MOST: the angle is a STRUCTURAL read, not a magnitude
        one - slope of the recent window in ATR units, the closest thing
        collected to "is price going anywhere or just rotating".
        L1 score vector, via `_l1_scores(ctx)` reading `ctx["l1"].scores`
        defensively. Emission only - no gate, no size, no behaviour change.
        A malformed ctx returns None and the axes are simply ABSENT, which is
        distinguishable downstream from zero; a 0.0 default would not be.
TCS.4: THE FIRST TC.6 TRADE THAT FORMED CORRECTLY DIED AT
        THE WRITE, AND CRASH-LOOPED A LIVE BOX. `_execute_condor_leg` set
        `is_trend_credit` on the record; `log_entry` INSERTs every record key;
        the field has NO COLUMN. OperationalError on the INSERT -> loop error
        cap -> service shutdown -> restart -> again, every 15s for the rest of
        NFLX's session.
        IT NEVER FIRED BEFORE because TC.6 could never REACH execution - TCS.3
        fixed the bound at noon and exposed it hours later. A latent defect
        surfaced by a fix.
        WHY THE FIELD EXISTED (checked before removing): `ed9d30a` (08-13) made
        it the EXIT ENGINE'S DISCRIMINATOR - `if bool(record.get(
        "is_trend_credit"))` routed TC.6 to breach-or-nickel. On 08-14 it was
        found not to be a column, so every restart lost it and the branch
        silently stopped firing; `structure.py` was built to replace it by
        DERIVING from persisted `strategy`/`setup_type`. The read side moved.
        The write side was never cleaned up. It is vestigial, not spurious.
        WHY REMOVED AND NOT ADDED AS A COLUMN: WORKING_AGREEMENT 22, written on
        08-14 about THIS FIELD - "PREFER DERIVING. A new column fixes tomorrow
        and not today: every position opened before the migration still
        rehydrates without it, SELECT * returns None, and None reads as False -
        the exact failure, silently."
        THE SIGNAL ATTRIBUTE `sig.is_trend_credit` IS UNTOUCHED - in-memory
        only, read via getattr to set `_is_tcs`, never persisted.
TCS.3: THE BOUND OUTLIVED ITS FRAME. `_opening_range`
        read the 60-bar 1m cache and the 09:30-09:35 bars leave that window
        at ~10:35 ET — 25 minutes before TCS_START_ET — so trend
        participation (TC.6) was structurally unable to fire: the bound was
        None for the entire credit window on every box since d12ee3e baked
        (Fri 08-14). Fleet-verified before fixing (13/15 boxes logging
        `[tcs] no opening-range`, up to 290/290 evaluated ticks). The range
        now reads TODAY'S 09:30 5m bar (exact for a 5-minute window, present
        all session on every tape), with the 1m window kept for the early
        session and non-5m window sizes; both paths date-filtered. Same
        failure class as AUDIT A2.1, one function over: a lookback written
        against history the frame does not carry.
        NOTE: FEED.2 (2026-08-15) edited this file (_EXT preference in
        _named_level_frame) without a title bump — recorded here so the
        version history stays truthful; no behaviour change beyond FEED.2's
        own.
AUDIT A2: four fixes from adversarial audit #2.
        (A2.1) named levels get a DEEP frame: `_named_level_frame()` reads the
        candle store directly (1h bars, NAMED_FRAME_1H_BARS, 300s TTL) and is
        passed to the mapper as `named_df` - the cached 5m frame is 100 bars
        (~8.3h) and was feeding the 10-day section lookback truncated tape:
        wrong pool prices, rungs mutating intraday. Store precedent is PF.2
        ("the history was never missing - the frame was"). Fails soft to the
        old behavior (mapper guards truncation on any input).
        (A2.2) the F5 orphan announcement MOVED to the manage branch. Its old
        home, `_condor_leg_open_without_plan`, is only called inside
        attempt_new_entry, which only runs when has_open_position() is False -
        and that falls back to the SAME get_open_trades(). While an orphan leg
        was open the call site was unreachable; when reachable, the count was
        by construction zero. The v6.10/v4.83 danger model (TC.6 opening a
        second spread against an orphan) was impossible for the same reason -
        the fix guarded a scenario the gate already forbids, with a guard the
        gate made unreachable, and the once-per-restart WARNING could never
        fire. It now fires from the has_open_position branch, where an open
        leg can actually be seen. The checker itself is now side-effect-free
        and stays as belt-and-braces on the TC.6 dispatch.
        (A2.4) ledger bar selection moved into the ledger: feed_frame() walks
        every closed session bar newer than the persisted last_bar_ts - the
        old iloc[-2] + one-stamp guard silently DROPPED bars on any tick
        slower than ~75s, undercounting exactly the busy tape.
        (A2.9) an empty first-tick seed no longer latches the date - the
        ledger retries seeding until the mapper produces named pools; and the
        wiring routes through get_ledger() so there is ONE singleton, not two.
AUDIT F6: A TC.6 RECORD IS NOT A CONDOR LEG.
        `_execute_condor_leg` still stamped is_condor_leg=1 and
        condor_leg_num=2 onto every trend credit spread, called
        notify_leg_filled() on its fill (advancing a condor plan state machine
        the trade has nothing to do with — a no-op today only because TC.6
        defers whenever a plan is active: a gate, not a guarantee), and sent a
        Telegram entry alert advertising a stop for a trade whose record
        deliberately carries stop_premium=0.0 — a lie on the exact channel
        that caught the last identity bug. All three now condition on _is_tcs.
        The two persisted fields were spoofing `_condor_sibling_open` (an
        opposite-side open TC.6 would make a standalone condor leg read
        "formed": ratchet and TP suppressed) and `condor_roll`'s leg discovery
        (could have closed a TC.6 leg as rolled_to_broken_wing).
        ⚠️ position_manager v3.2 lands in the SAME commit: its premium fetch
        keyed on is_condor_leg, which this change removes from TC.6 rows —
        without v3.2 the spread pricing silently falls to the single-leg path.
        That pairing is the hop this fix would have broken if shipped alone.
TC.6 IDENTITY THROUGH THE EXECUTION PATH.
        `_execute_condor_leg` hardcoded condor identity onto every record it
        built, so `is_trend_credit` and `underlying_stop` never reached the
        trade and the exit branch gated on them COULD NEVER FIRE. Every trend
        credit spread inherited the condor ratchet and the 25%% premium stop.
        is_trend_credit, and stop_premium=0 for a trend credit spread.
`_opening_range()`: the ORB high/low recomputed FROM THE
        TAPE as trend PARTICIPATION's bound. Separates the ORB ENGINE (no
        runaway gate, no slot arbitration past 11:00) from the ORB LEVEL (a
        price, not a dependency). Restart-proof and available past the cutoff.
AFD.1 MOVED TO PRE-DISPATCH. It was a POST-SELECTION veto,
        so past 11:00 a debit strategy still WON the slot: `signal` went
        non-None, TC.6 (behind `if signal is None`) never ran, and the debit
        signal was refused afterwards — **the tick produced NO trade and the
        afternoon slot was consumed by a strategy forbidden to trade in it.**
        Likely the real reason TC.6 fired zero times on 2026-08-14, independent
        of the runaway gate. ORB / Continuation / Sweep are now SKIPPED, not
        evaluated-then-refused. The post-selection gate is retained as defence
        in depth.
TC.6 v2.0 call site: no `orb`, pass `trend`. The runaway
        gate was slot arbitration, not anchoring — after 11:00 ORB owns nothing.
TC.6 WIRED. TrendCreditSpread dispatches after the condor
        and routes through `_execute_condor_leg`, deferring when a condor plan
        holds the symbol. Exit is BREACH-OR-NICKEL via `is_trend_credit`
        (exit_engine v4.17) — the measured +$0.52/spread was HELD TO EXPIRY,
        UNMANAGED, so the ratchet and 25%% stop are deliberately unreachable.
PF.5 WIRED. The condor now consults the DAILY pitchfork and
        the session extremes. `_condor_rails()` returns the rails or None, and
        **None means NO CONDOR** — operator: "consider the condor off the table
        if we don't have guardrails. That is the insurance policy that
        eliminates a bad decision in an unpredictable session." Measured cost on
        2026-08-12: 13 distinct daily forks across 7 of 15 boxes, so roughly
        half the fleet becomes condor-ineligible. Accepted.
        `_session_extremes()` takes the max across BOTH frames — each is a
        rolling window and neither is guaranteed to reach 09:30. A late window
        UNDERSTATES the extreme, which loosens the filter rather than tightening
        it, so the failure direction is a missed rejection not a wrong one; the
        strategy logs a missing extreme as a plumbing fault rather than trading
        with the filter silently off.
        This is the pitchfork overlay's FIRST CONSUMER — it has been live as a
        weight-0 observer since 2026-08-12 with one call site and nothing
        reading the rails back.
AFTERNOON DEBIT BLOCK. Operator: "The only other Long that
        can fire is either part of a butterfly or an iron condor vertical
        spread from 11 o'clock onwards." ORB/Continuation/SweepReversal are
        refused past DEBIT_DIRECTIONAL_CUTOFF_ET (11:00 ET, env-tunable).
        PLACED AFTER THE SIGNAL IS CHOSEN, not at dispatch: one gate instead of
        three, so a strategy added later cannot silently bypass the rule; the
        refused signal is fully formed so the journal records WHAT WAS REFUSED
        (a gate that vetoes invisibly can never be calibrated from its own
        rejections — the reasoning that put gates E and F after the score in
        setup_scorer); and condor legs never reach it, having routed through
        `_execute_condor_leg` above, so the credit path is exempt BY
        CONSTRUCTION rather than by a list entry that could rot.
        ENTRIES ONLY — open positions manage normally.
        ⚠️ IN A TRENDING AFTERNOON THIS LEAVES NOTHING: the condor self-gates to
        RANGING and the butterfly needs PINNING GEX. That window belongs to the
        trend credit spread (TC.6), which is NOT BUILT. Dark on purpose until
        it is — the measured cost of that window is negative.
RGM.6: THE FALLBACK RESOLVES TO A KNOWN LABEL.
        Operator: "unknown should be virtually eliminated by the time we freeze
        layer 1… there should be ways to extrapolate and resolve to a KNOWN
        label." The diary sizes it exactly: **L1 is all-zero on only 2.4-3.0% of
        ticks on EVERY session since 07-15**, while the v13 fallback emitted
        UNKNOWN on ~18-19%. A known answer existed roughly SEVEN TIMES more
        often than we were genuinely blind, and it was discarded.
        v5.0's hold covered STALE ticks. The other fall-through — the code's own
        "empty committed label on a WARM book" — went straight to v13, which
        re-derives from scratch with NO MEMORY and says UNKNOWN when nothing
        matches its ladder.
        THE LADDER IS NOW: committed L2 -> held incumbent -> **L1 ARGMAX** ->
        v13. UNKNOWN is reserved for the ~2.4% that are genuinely all-zero.
        ⚠️ CONVICTION IS CARRIED, NOT INVENTED. An L1-argmax label carries L1's
        RAW score, which is below theta_commit by construction — that is the
        point. Downstream gates that read conviction see a weak label as weak.
        ⚠️ THE ENGINE TAG IS NOW FOUR STATES: [L2 c=] committed, [L2-hold c=]
        incumbent, [L1 c=] argmax, [v13] true fallback. `grep -c '[v13]'` has
        been the fallback-rate measure all week — with the split, a DROP in it
        must not be read as a fix when it is a relabelling.
        ⚠️ EXPECT UNKNOWN TO FALL TOWARD ITS ~2.4% FLOOR and the labelled
        therefore NOT poolable across this deploy.
        Kill switch: OT_RGM6_L1_ARGMAX=0 restores the pre-RGM.6 ladder exactly.
v6.0
CNT.6: CONTINUATION IS BLOCKED IN RANGING AND COMPRESSION.
        A trend continuation is a trend RESUMING after a pullback. RANGING and
        COMPRESSION are the assertion that there is no trend to continue, so the
        entry contradicts its own premise — this is a correctness defect, not a
        permissiveness setting.
        ⚠️ THE MECHANISM WAS THE `_is_runaway` BYPASS. The gate read
        runaway ORB flag skipped the label check entirely and continuation fired
        on ANY tape at Priority 2 — ahead of Butterfly (P3, RANGING/COMPRESSION)
        and Condor (P4, RANGING), both behind `if signal is None` and therefore
        never evaluated. The operator saw it as condors and butterflies going
        extinct; the cause was a dispatch bypass, not an absence of setups.
        MEASURED, 13 sessions: RANGING → Continuation 94 vs IronCondor 27 ·
        COMPRESSION → Continuation 39 vs Butterfly 6. Continuation took 3.5x the
        strategies exist for.
        ⚠️ WHY IT IS IN DISPATCH AND NOT IN THE STRATEGY: CNT.3 already blocked
        the COMPRESSION handoff INSIDE continuation_strategy and the squeeze
        continued, because a strategy-level veto still CONSUMES THE SLOT on its
        way to returning None. Only a gate above the call frees P3/P4.
        ⚠️ EXPECT FEWER CONTINUATION TRADES AND THE RETURN OF BUTTERFLY/CONDOR.
        Do not read the drop in continuation volume as a regression — it is the
        change working. Kill switch: OT_CONT_BLOCK_PREMIUM=0.
        SEPARATE AND NOT ADDRESSED HERE: RANGING is emitted on only ~2% of L2
        ticks, so the condor is ALSO starved by the label itself. Freeing the
        slot is necessary but not sufficient for condor volume.
L1 EVIDENCE ON THE FIRED DISPOSITION. The sweep collection
        is meant to characterise what made a good ENTRY good, and the journal
        contributing term that decided the entry was computed at the fire and
        then discarded. Reconstructing them later means replaying the tape and
        hoping the replayed score matches the one that fired, which is an
        approximation sitting exactly where the analysis lives. Now records the
        six-score vector on every fire, plus the firing setup's own L1
        breakdown via `_L1_BREAKDOWN_FOR`.
        ⚠️ A WRONG MAPPING IS SILENT — it files a well-formed breakdown from the
        an unmapped strategy records no breakdown rather than a wrong one.
        Log-only: no gate, no dispatch and no sizing reads any of this.
MEM.2: in-process tracemalloc, gated by OT_MEM_TRACE.
        The standalone probe failed FOUR times in an afternoon and never once
        for a reason about memory — wrong box, un-pulled file, `tmux sh -c`
        inheriting neither .bashrc nor the unit environment (so no credentials
        and OT_INSTRUMENT defaulting to QQQ on the SPX box), and finally an
        `xargs env` workaround that echoed every secret to the terminal. All
        four are the same root cause: a second process cannot easily inherit the
        trading environment. **The bot already has it.**
        Costs one bool test per tick when off; tracemalloc is not even imported.
        ⚠️ When ON it adds ~10-30% memory overhead, which on a 951 MB box is
        itself a risk — enable on the RESIZED SPX box only, never fleet-wide.
CNT.1: CONTINUATION DISPATCH OPENED TO BREAKOUT_VOLATILE.
        Operator's call, to gather data. The bar was structural, not a quality
        judgement: continuation derives DIRECTION from the label, and
        BREAKOUT_VOLATILE asserts volatility expansion without saying which way,
        so no branch could assign one. continuation_strategy now takes direction
        from `trend.overall_direction` when the label is BREAKOUT, gated on
        `primary_adx >= CONT_BREAKOUT_MIN_ADX` (default 25) — an ADX bar rather
        than a conviction bar, because under a non-trending label continuation's
        conviction floor is skipped and BREAKOUT's conviction is not the trend's.
        Entries are tagged `trend_continuation_breakout` so the cross-day rollup
        scores this path separately from _standalone and _handoff.
        Kill switch: OT_CONT_BREAKOUT_DIRECTION=0.
        ruling — sweep is an EVENT, not a market state. The dispatch required
        of live ticks, is exactly zero on 96%, and F7's commit threshold made it
        rarer still. Dispatch now gates on the L1 `_sweep` SETUP SCORE
        (>= SWEEP_SETUP_FLOOR), captured from the confluence result this loop
        already computes. The score's three hard vetoes ARE the stated spec:
        named level, rejected back through, not accepted beyond. The PLTR
        trend-opposition guard is a soft-necessary INSIDE that score, so it
        survives the change — it never lived in this gate.
LIVE A/B ON THE EMISSION LAW (RGM.1 F7). conviction_
        integrator v2.1 closes the unprotected branch: below theta_hold the
        incumbent was replaced by bare argmax every tick, which accounted for
        96.9% of 8,345 label switches across 19 sessions at a median incumbent
        conviction of 0.08. v2.1 now runs BOTH laws on every tick and reports
        whenever the divergence CHANGES (never per tick). Nothing reads the
        shadow to trade. Kill switch: OT_L2_PROTECT_BELOW_HOLD=0 restores the
        v2.0 law exactly, and the shadow then models v2.1 — so the A/B reads
        the same in either direction and one env var runs the control.
ORB WAS BEING GATED BY THE STALE-BOOK ENTRY BLOCK, AND THAT
        WAS NEVER INTENDED. v5.0 put the block ABOVE the dispatch, so it
        provide — became unreachable on a stale tick. MEASURED, not inferred:
        the block ran 09:35:01 → 09:39-09:41 ET on ALL 15 boxes on 2026-08-04,
        which is the first four to six minutes of ORB's own entry window (ORB
        opens 09:35:00 sharp). Every session since v5.0 deployed lost that
        window fleet-wide, and the flagship is the strategy the morning belongs
        to.
        A CONFIRMED ORB (OPEN_LONG / OPEN_SHORT) is now exempt. Nothing else is:
        continuation, condor, butterfly and sweep all condition on the label and
        stay blocked, so v5.0's actual protection is intact.
        own guard, latch and pager. A confirmed ORB break on a stale book reads
        fresh price and no label at all.
W.2: _capture_entry_snapshot's handler now logs inside the
        except itself. It always warned, but the census reads the HANDLER BODY,
        so it was counted SILENT — and a census that miscounts is worse than
        none. No behaviour change.
        v5.1 blocked ENTRIES on stale and held the committed label, but a HELD
        any label that is not TRENDING in the trade's direction, so a position
        could still be closed on a classification the engine could not confirm
        at that moment. And on a COLD book — stale with nothing committed —
        main fell back to v1.3 raw argmax, which is the churn L2 exists to
        before any price stop. That is the 07-23..08-03 flicker mechanism with
        one branch left open.
        so None disables exactly those three and nothing else.
        EVERY PRICE-BASED EXIT STILL RUNS: 15:45 hard close, stop, max_loss,
        trail, FVG trail, break-of-structure, condor ratchet, nickel close,
        the price feed is down, and refusing to stop out on it would be a
        different and worse rule. A 0DTE position must still flatten at 15:45.
ENTRY SNAPSHOT HOOK (log-only, freeze-safe). Every confirmed
        fill — directional and both condor legs — now persists the entry-time
        FVG/structure picture to trades.entry_snapshot via
        analysis/entry_snapshot.py. Runs AFTER the record is written, so it
        cannot reach the entry decision, the size, the strike or any exit; the
        only thing it can do to a live position is nothing.
        WHY HERE AND NOT IN entry_engine: one call site per path, in the file
        that owns ctx, and it keeps a second lineage out of another agent's
        file (working agreement §7). The condor helper gains an optional ctx
        for the same reason — both of its callers already hold one.
        THE CAPTURE'S OWN FAILURE IS AUDIBLE. set_entry_snapshot returns a
        boolean and the payload carries `err`; a miss logs once per reason per
        process (the _log_backfill_depth idiom, §17) rather than every fill or
        never. A snapshot hook that fails silently would leave a column of
        NULLs indistinguishable from a day with no trades — which is the exact
        shape of every observability defect this repo has paid for.
DISPATCH ISOLATION. Each strategy evaluation now runs inside
        _safe_strategy(): a raise is logged at ERROR and returns None, so the
        priority cascade continues instead of aborting the tick. Before this, one
        strategy raising silently disabled every strategy BELOW it — butterfly's
        `_mult` NameError (Priority 3) suppressed the iron condor (Priority 4) on
        every RANGING/COMPRESSION tick where GEX was pinning, and nothing in any
        log said the condor had been skipped. Applies to all six dispatch call
        sites plus the Leg-2 check in the tick loop.
STOP TRADING ON THE UN-SMOOTHED CLASSIFIER. Two rules, no
        new parameter, nothing to tune.
        FALLBACK was wrong. On a stale tick the bot dropped to the v1.3
        classifier — raw L1 argmax — which is precisely the churn L2 exists to
        remove (436 committed switches vs 695 argmax flips). exit_engine checks
        median hold 0.8 min and p25 12 SECONDS, against 5-12 min for every other
        exit reason; 19% of continuation exits and 27% of iron-condor exits.
        A 12-second position has not had time to be right or wrong — only to pay
        a round trip. And the trigger is routine: v4.6's own note records that
        "a tick gap over dt_max=90s re-stales every tick".
        THE FIX: (a) on a stale tick WITH a committed label, HOLD that label
        instead of falling back; (b) take NO NEW ENTRIES while stale. Holding is
        declining to act on unknown information — the position stays protected
        by every price-based stop, none of which read the label. Entering is a
        DECISION and is refused.
        A COLD BOOK AT THE OPEN STILL FALLS BACK TO v1.3 — that path was always
        correct (no prior state exists to hold) and is unchanged.
        WHY THIS MATTERS EVEN THOUGH LOSSES ARE ACCEPTABLE RIGHT NOW: the fleet
        is deliberately permissive to collect a broad sample. A flickered exit
        does not just cost $48, it writes a row tagged
        "ContinuationStrategy / TRENDING / -$48" that will later be counted as
        evidence about an exit mechanism. The fix does not reduce firing; it
        stops premature exits, so each trade actually expresses its setup.
DECLARE THE OPENING GAP, AND STAMP THE ENGINE.
        (a) The first ~25 minutes of every session legitimately cannot produce
        RANGING or COMPRESSION: both are computed on a 25-bar 1-MINUTE window,
        and market_data deliberately scopes the 1m frame to the current session
        (OT_FEED_INTRADAY_SCOPE=session) so it can never bleed across the
        overnight gap and fabricate a slope. v4.6 announced that designed
        condition at WARNING as "NOT L2.5-grade" and fired it on 13 of 15 boxes
        at 09:30 on 2026-07-30. It now logs INFO ("warming as designed", naming
        the dims and the frame depth) when ONLY window-dependent dims are missing
        AND the frame is still filling, and keeps the WARNING — now carrying
        df_1m — for every other starve, which really is a fault. Deliberately NOT
        fixed by padding the frame (that is what the guard prevents) nor by
        fabricating a low value (synthetic data would enter the calibration set)
        nor by weakening the integrator's full-vector invariant.
        [L2 c=..]/[v13] tag in bot.log — which is why "has L2.5 ever committed?"
        took a fleet-wide grep across 138k-line logs. It also makes the designed
        v1.3 opening window excludable from L2-conditioned fits by a WHERE
        clause instead of by inference. Auto-migrates via ALTER TABLE (v-obs
        pattern); observability only, no trade-mechanics change.
**L2.5 WAS NEVER REACHABLE.** Root cause of every symptom
        and BOTH gates compared it to the uppercase literal "L2" — at the tick
        override (was line 482) and at the startup warm-load (was 1749). "l2" ==
        "L2" is False, so the L2.5 block has never executed on any box since
        v4.0 wired it, and no environment variable could have helped because the
        DEFAULT itself failed the comparison. This is why a fleet-wide grep of
        34k-138k-line bot.logs on all 29 boxes returned L2=0, FAILED=0, STALE=0
        and integrator_state.json had never been written: nothing inside the
        block — commit, save, load, even the failure handler — was ever reached.
        The v4.5 import fix and v4.6 observability were both real and both
        irrelevant to reachability. Fixed by comparing lowercase at both sites,
        plus a start-up assert that refuses to boot on an unrecognised value
        rather than silently selecting an engine nobody chose, and a start-up log
        line naming the active engine so "which engine is running?" is answerable
THE SILENT L2 GATE IS NOW AUDIBLE. v4.5 fixed the import,
        and a probe against the real classes confirmed L2 commits from tick 1
        on a full evidence vector (TRENDING_BULL, conviction 0.984). But three
        conditions must hold for L2 to override v1.3, and only two of them
        silent. Since ConvictionIntegrator clears `stale` ONLY when every
        dimension of the evidence vector is non-None, one perpetually-None
        [v13] with no warning anywhere — which is exactly why "did L2.5 land?"
        was unanswerable from the logs. The non-committing branch now reports
        the reason and names the missing dimensions, throttled to one line per
        change, and announces recovery when it starts committing again. Known
        starvation paths: closes=None (df_1m shorter than RANGE_WINDOW_BARS)
        nulls RANGING+COMPRESSION; a tick gap over dt_max=90s re-stales every
        tick. Observability only — no change to trading behaviour.
L2.5 IMPORT CONTRACT FIXED + SILENT DEGRADATION MADE LOUD.
        `RANGE_WINDOW_BARS` was imported from conviction_integrator, which does
        only ever reachable through a re-export tuple that the 07-28 excavation
        trimmed. The ImportError was swallowed by the L2 guard, so all 15 boxes
        ran the v1.3 classifier for the whole 07-29 session while logging a
        single WARNING per start. Two changes: (a) both symbols now import from
        the modules that OWN them — a re-export is not a contract; (b) the
        fallback logs at ERROR and pages via
        silent engine swap invalidates the session's conviction data for
        calibration even though trading continues unaffected. The pager is
        itself wrapped — it can never take the bot down.
READINESS STAGED PICKS (trade_readiness v1.1, LOG-ONLY):
        while ARMED, continuation/sweep now journal the contract they WOULD
        select via the live selector on SMOOTHED conviction — the calm-vs-
        spike strike experiment. Constructor passes contract_ctx. No entry
        path touched.
TRADE READINESS wired in (LOG-ONLY). New
        analysis/trade_readiness.py evaluates every strategy's pre-trigger
        confluence as a graded readiness R in [0,1] each ~15s tick, with a
        dt-aware slope (R/minute) and a DORMANT->STAGING->ARMED machine that
        journals transitions, heartbeats, and readiness_would_fire moments.
        Gates NOTHING — no fire decision changes anywhere; guarded import
        (loop byte-identical without it), assess errors swallowed. Hooked in
        the every-tick block beside the chain snapshot, deliberately BEFORE
        the has_open_position branch so observation continues while halted or
        holding. ORB exempt (mechanical by directive). This is the sight-
        picture groundwork: where the market IS (instant geometry), where
        it's BEEN (L2 conviction), where it's HEADING (slope on the lowest
        timeframe). Log-only per the pitchfork weight-0 precedent so it rides
        inside the frozen-baseline window; its journal rows calibrate the
        bars that will eventually gate.
FULL OPTION-CHAIN ARCHIVAL (analysis/chain_snapshot.py).
        The bot already fetched the complete 0DTE chain every ~15s tick — bid,
        ask, mark, delta, gamma, theta, vega, IV, OI, volume on every strike,
        ~23,000 full-chain snapshots per fleet-day — and discarded all of it
        except the one selected contract in the signal_journal `scored` event
        (which drops gamma and vega besides). Chains are NOT reconstructible
        after the session: unlike the 1-min tape or deterministic swing pivots,
        a quote for a strike nobody selected is gone permanently at 16:00.
        Now archived to data/chain_snapshots/<date>/<SYM>.jsonl.gz on a
        wall-clock cadence (OT_CHAIN_SNAPSHOT_MIN, default 5). Log-only, gates
        nothing, adds NO fetch. Makes any future strike-selection rule
        retroactively testable instead of a live experiment.
PAPER CONDOR CREDIT via the shared authority (audit
        defect T). The condor leg paper fill applied PAPER_FILL_SLIPPAGE_PCT
        inline while single-leg and butterfly entries had moved to booking the
        bare mark (entry_engine v3.8), so paper friction differed BY STRATEGY.
        It now calls execution/limit_ladder.paper_fill_credit(), the one
        paper-pricing authority, which honours the same knob for every path
        (default 0.0 = book the mark, matching the mid-credit limit live
        actually posts). No live-path change.
        integrator's committed label (Layer-1 confluence evidence → integrator),
        replacing the v1.3 boolean classifier's raw argmax as the trade gate.
        Cures the fleet-wide UNKNOWN flicker (v1.3 dropped to UNKNOWN mid-trend
        at avg ADX ~29 — a hard no-trade gate firing during the strongest
        drops (theta_hold hysteresis) and never emits UNKNOWN. Gates run WIDE
        OPEN (conviction logged, not gated — L3 tunes bars later); paper P&L is
        (data/integrator_state.json), warm-loaded at boot. Rollback:
SIGNAL JOURNAL DISPOSITIONS (ROADMAP Phase 3.1, log-only,
        zero behavior change): attempt_new_entry now emits what happened to
        every signal AFTER scoring — `disposition` events for fired /
        sizing_rejected / invalid_signal (below-B REJECTs are already emitted
        by setup_scorer v1.3's `scored` event) — plus `condor_plan` /
        condor bypasses the score path, so without these its conviction bar
        could never be calibrated). ORB dispositions carry retest_depth_px
        (orb_engine v3.7, defect G) and its ATR-relative form. All emissions
        route through analysis/signal_journal (guarded import, every failure
        swallowed) — the trading loop is byte-identical if the journal is
        absent or broken.
pass df_5m through to position management so exit trails
        anchor to 5-minute FVGs (exit_engine v3.8 runner refinements).
CONDOR ENTRY FILL-CONFIRMATION (audit defect O, part 1).
        _execute_condor_leg live path now confirms the fill before ANY record
        exists: submit the signed-credit limit → poll via
        execution/order_confirm.confirm_order_fill (bounded by
        LIVE_ENTRY_DEADLINE_SECONDS) → book ONLY confirmed contracts at the
        broker's per-leg net credit. Unfilled → cancel, walk away, no ghost;
        partial → book the filled size; uncancellable → page, reconcile adopts.
        notify_leg_filled() therefore advances the legging state machine only
        on real fills. PAPER mirrors live friction: condor credit now applies
        PAPER_FILL_SLIPPAGE_PCT (it previously ignored the knob and filled at
        exact mid). price_effect kwarg dropped (ignored by SDK; sign carries
        the credit).
PHANTOM P&L RECOVERY + denser reconcile schedule.
        (a) A phantom (DB open, broker flat — e.g. a manual close at the broker)
            now books its REAL fill: one order-history read per reconcile pass,
            match_closing_fills() finds the closing order(s), phantom_pnl()
            books credit-signed truth into the DB (which DAILY_LOSS_LIMIT
            reads). No matching order (expiry/assignment) -> flagged $0.00 as
            before. Applies to BOTH the startup reconcile (history covers back
            to each phantom's entry date) and intraday sweeps.
        (b) Intraday sweeps every BROKER_RECONCILE_INTERVAL_MIN (default 10,
            was hardcoded 30), PLUS wind-down sweeps at 15:45, 15:50, and a
            final 15:57 post-flatten truth pass (last guaranteed look before
            the loop goes dormant at 16:00).
        (c) Phantom alerts now carry the recovered P&L.
Condor legs now record |short-strike delta| as setup_score
        (a calibration "street-sign", read AFTER the BB-anchored selector
        picks the strike — it does NOT influence selection or sizing). NULL
        when the Greeks feed did not populate delta, so a stored value is
        always a genuine delta. Enables later condor threshold calibration;
        previously condor legs logged no score at all.
handle_hard_close() now fetches the options chain once and
        passes it to flatten_all(), so the 15:45 force-flatten has real marks
        (paper fill price / live context) instead of booking at entry premium
        and logging every leg at +$0.00. Reused across the 15:45->16:00 retries.
defect H rename only: NO_ENTRY_AFTER_ET -> ORB_NO_ENTRY_AFTER_ET
        (import + the orb_state.json "past_cutoff" flag). Same constant, same
        (11, 0) value, same behaviour — the name now states its ORB scope.
        SWEEP_REVERSAL — because the ORB engine's break+retest is self-validating
        and the classifier does not test for it. Two changes in run_entry_logic:
        (1) the hard UNKNOWN gate is bypassed when the engine is in a confirmed
            OPEN state (the label no longer vetoes a proven setup);
        (2) the ORB dispatch admits UNKNOWN and SWEEP_REVERSAL (ORB beats sweep;
            engine no longer defers OPEN under a sweep — see orb_engine v3.2).
        Nothing else loosens: sweep/butterfly/condor still self-gate on their own
        False to restore strict v2 gating. Every ORB fired under UNKNOWN is logged
condor leg ENTRY alert now names the instrument. The leg-
        filled Telegram alert was built with a raw _send() that omitted the
        symbol (every other entry alert routes through the structured methods
        that already include it), so condor entries read "[PAPER] Condor Leg 2
        …" with no way to tell which box fired. Added {INSTRUMENT} after the
        mode, matching the "[MODE] SYMBOL | …" form of the other alerts. DB
        logging already recorded the symbol; this was display-only.
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
INTRADAY broker reconcile (LIVE + enabled): every 30 min
        across RTH with the last sweep at 15:30, a leg-role-aware check catches
        positions the broker closed mid-session — especially a SHORT leg
        auto-closed while the long remains (loud alarm, close the broken record,
        adopt the surviving long so the 15:45 flatten handles it cleanly). Only
        inspects rows we already manage; fail-safe on a bad/empty read.
LIVE broker reconciliation wired into recovery: the broker
        is the source of truth for existence. _reconcile_with_broker() queries
        open positions, KEEPs DB-planned rows confirmed there, ADOPTs+journals
        broker positions with no DB plan (managed by the ADOPTED exit path),
        and closes PHANTOM DB rows the broker no longer shows. FAIL-SAFE: a
        failed or empty broker read never closes anything — falls back to
        DB-only recovery. Paper is unchanged (no broker query).
durable 15:45 flatten + expiry-aware recovery. handle_hard_
        close now routes through pos_mgr.flatten_all() so EVERY open record
        (both condor legs) is truly closed in the DB + P&L booked (the old path
        called place_exit_order directly and never wrote status='closed'),
        retries every tick to 16:00, and pages once on failure. Startup recovery
        keys on EXPIRY, not entry date (the bot trades weeklies): sweep only
        genuinely expired orphans, resume every still-live row, and flag a
        CARRIED-overnight position. Restart alerts self-identify (box symbol +
        fresh-boot vs service-restart from /proc/uptime).
directional-only instruments (single names): skip iron
        condor and butterfly in the dispatch; ORB + sweep only.
block new entries when the daily loss halt is active
        (day P&L <= -DAILY_LOSS_LIMIT_USD); open positions still exit.
(2a) ORB-window sweep override: when an ORB signal fires but
        a sweep reversal has higher conviction, take the sweep. (2b) pass the
        the broken-wing roll check when both condor verticals are open.
condor legs are now TRACKED positions: each vertical is
        sized at half the grade budget, written to the trade log, registered
        with the position manager (the only two-position strategy), and
        managed/exited per-side. Replaces the phantom notify-only path.
        halting: main_loop consumes RiskManager.consume_reassess_request() and
        reclassifies with trigger="loss_limit".
ORB range is now three-state (ESTABLISHED/IN_PROGRESS/
        EXPIRED) and always carries the last valid range. Startup fetch runs
        unconditionally (populates last-valid EXPIRED range pre-open); the
        open-poll runs from 9:30 ET and latches only when today's range is
        ESTABLISHED. Flag renamed orb_range_fetched_today -> _established_.
remove duplicate _execute_condor_leg (dead 2-arg def shadowed by
        a broken 3-arg def that referenced a non-existent CondorLeg class and
        mark_leg_filled method); single canonical impl on the real OptionsSignal
        API with live TastyTrade placement ported in. ORB range fetch is now
        success-keyed (retries until today's 9:30-9:35 candle is really written)
        and the startup fetch is gated to >= 9:35 ET so it never writes a
        stale prior-day range; instrument read from OT_INSTRUMENT (no systemd
        unit-file parsing).
fix missing ZoneInfo import causing loop error every tick
iron condor legged entry, BB-anchored strikes,
        fed day trading enabled, ORB cutoff 11AM, condor window 11AM-2PM
v1.0 — original release
0DTE options bot: ORB, Sweep Reversal, Butterfly
RTH only (9:30–16:00 ET), hard close 15:45 ET.
Run modes:
  python main.py            — interactive startup (prompts instrument, risk $, paper/live)
  python main.py --service  — non-interactive for systemd
"""
# v-runaway-fix (2026-07-24) — runaway ORB reroute — hands to CONTINUATION (with-trend on pullback) FIRST, not sweep; post-runaway sweep gated to NAMED levels only. Fixes afternoon-giveback: runaway momentum was being faded by sweep reversal.



import logging
import logging.handlers
import os
import signal
import sys
import time
import traceback
from datetime import datetime, time as dtime
from typing import Optional
from zoneinfo import ZoneInfo

from config import (
    POLL_INTERVAL_SECONDS, LOG_LEVEL, LOG_FILE, LOG_ROTATION_MB,
    PAPER_TRADING, RISK_PER_TRADE_USD, DAILY_LOSS_LIMIT_USD,
    ORB_BUDGET_USD, ORB_BUDGET_IS_DEFAULT,
    SCALE_ORB, SCALE_BREAKOUT, SCALE_VOLT, ORB_RISK_ENV_IGNORED,   # r161
    CONTRACT_SCALE, CONTRACT_SCALE_SOURCE,                          # r234
    ORCS_ENABLED,                                                   # r235
    RUNAWAY_CUTOFF_ET, RUNAWAY_END_ENV_REFUSED,                     # r253 (RUNW.2)
    BREAKOUT_LATEST_ET, BREAKOUT_END_ENV_REFUSED,                   # r265 (BRK.9)
    BRK_NOPROG_MODE, BRK_NOPROG_ENV_REFUSED,                        # r265 (BRK.8)
    BRK_STOP5M_MODE, BRK_STOP5M_ENV_REFUSED,                        # r284 (BRK.11)
    RESTING_STOP_MODE, RESTING_STOP_ENV_REFUSED,                    # r266 (STOP.1)
    COMMIT_GATE_MODE, COMMIT_GATE_ENV_REFUSED,                      # r272 (COMMIT.2)
    CAUTION_SIZE_MODE, CAUTION_SIZE_ENV_REFUSED,                    # r272 (COMMIT.3)
    NOISE_FLOOR_BAR_MULT, NOISE_FLOOR_LOOKBACK_BARS, NOISE_FLOOR_MIN_BARS,
    PIN_PROXIMITY_ACTIVE, PIN_PROXIMITY_MIN_FRAC,
    REASSESS_MINUTES, INSTRUMENT, INSTRUMENT_UNSET, INSTRUMENT_LISTED, SessionConfig, DIRECTIONAL_ONLY,
    DEBIT_BLOCKED_STRUCTURES,
    ORB_NO_ENTRY_AFTER_ET, BROKER_RECONCILE_ENABLED,
    ORB_REBUILD_1M_BARS,                        # r95 restart tape reach-back
    DEBIT_DIRECTIONAL_CUTOFF_ET, DEBIT_BLOCK_ACTIVE,
    CONDOR_PF_TIMEFRAME,                        # PF.5
    CONDOR_TRIGGER_APPROACH,                    # v4.3 trigger map (module-level)
    ENTRY_OPEN_ET,                              # r101 — nothing opens before 09:35
    RTH_OPEN_ET, ORB_WINDOW_MINUTES,            # TC.6 v2.1 — range from tape
    BROKER_RECONCILE_INTERVAL_MIN,
    EOD_RESTING_AT_ET, EOD_LADDER_AT_ET, EOD_CROSS_AT_ET,   # r149 — the broker check follows the schedule
)


def _setup_logging():
    import os
    root = logging.getLogger()
    if root.handlers:
        return
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=LOG_ROTATION_MB * 1024 * 1024, backupCount=5
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)
    root.setLevel(level)


# ── r112 — DEBUG IS A LIVE FLAG, NOT A RESTART ───────────────────────────────
# `data/DEBUG_LOG` on the box, read every tick like the rehearsal flag: no
# restart, survives a bake, and it OVERRIDES config.LOG_LEVEL rather than
# competing with it. Its presence means DEBUG; its absence means whatever
# LOG_LEVEL says.
# ⚠️ DEBUG IS NOT FREE. The 2026-08-24 logs were ~300k lines a box, most of it
# raw DXFeed payloads — a single Greeks frame is thousands of characters, and
# it buries exactly the decision lines a postmortem needs. That is the cost the
# toggle exists to let you pay deliberately and then stop paying.
_DEBUG_FLAG = os.path.join(os.path.dirname(LOG_FILE), "data", "DEBUG_LOG")
_debug_state = {"on": None}


def _apply_log_level() -> None:
    """Set the root level from the flag. Cheap (one stat), so it runs per tick;
    announces only on a CHANGE, at the level being left, so the transition is
    visible in whichever log you are reading."""
    try:
        want_debug = os.path.exists(_DEBUG_FLAG)
    except Exception:                                          # noqa: BLE001
        return
    if want_debug == _debug_state["on"]:
        return
    first = _debug_state["on"] is None
    _debug_state["on"] = want_debug
    root = logging.getLogger()
    # ⚠️ THE FIRST PASS ALWAYS APPLIES, AND THAT IS THE POINT. Whatever put this
    # box in DEBUG — a systemd Environment=, an edited config, a library that
    # called basicConfig — the level is SET here at import and again every tick,
    # so removing the flag genuinely restores LOG_LEVEL rather than hoping
    # nothing else got there first. The operator did not remember how the fleet
    # was put in DEBUG; this does not require anyone to.
    if want_debug:
        root.setLevel(logging.DEBUG)
        root.info("[log] DEBUG ENABLED by %s — verbose until the flag is "
                  "removed (devtools item 69)", _DEBUG_FLAG)
    else:
        if not first:
            root.info("[log] DEBUG disabled — back to %s", LOG_LEVEL)
        root.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))


_setup_logging()
_apply_log_level()
logger = logging.getLogger(__name__)

from utils.time_utils import bar_grace_wait as _bar_grace_wait   # r51 (BAR.2)
from utils.time_utils import (
    now_utc, now_et, fmt_et_short, minutes_since, is_rth,
    seconds_until_rth_open, is_hard_close_time, entries_open,
    HARD_CLOSE,                      # r40 — admission's past_hard_close fact
)
from data.data_cache import get_cache
from data import disk_watch as _disk_watch
from data.macro_data import get_macro_manager

from data.options_chain import get_chain_fetcher

from analysis.volatility_engine import get_volatility_engine
from analysis.trend_engine import get_trend_engine
from analysis.structure_analyzer import get_structure_analyzer
from analysis.entry_snapshot import to_json as _entry_snapshot_json
from analysis.market_state import MarketState
from analysis.orb_engine import get_orb_engine, ORBState

# ── L2.5 (2026-07-21): wire the Layer-1 confluence scorer + Layer-2 conviction
# trades. WHY: the v1.3 classifier flickers to UNKNOWN for a single tick at high
# ADX (fleet-wide: UNKNOWN fired at avg ADX ~29, i.e. mid-trend, up to 41 on
# AAPL) — each flicker a hard no-trade gate slamming shut during exactly the
# evidence drops (theta_hold hysteresis) and NEVER emits UNKNOWN — indecision is
# a low conviction number on a best-fit label, not a seventh label. Gates run
# WIDE OPEN this week (conviction logged, not gated — L3 tunes the bars later);
# The variable was read by NOTHING. v3 used it to choose between the L2.5 stack
# and the v1.3 classifier; v4 removed both, and the log line below already
# states the answer unconditionally. What survived the port was an assert with
# no consumer — a gate that could only ever REFUSE TO START, never change
# behaviour.
#
# from the SMC fork. On v4 that value matched neither "l2" nor "v13", so the
# assert fired at import and systemd crash-looped it — restart counter at 4,
# `activating (auto-restart)`, on a box that had nothing wrong with its code.
# The guard was doing exactly what it was written to do, for a decision that no
# longer exists.
#
# ⚠️ THE GENERAL RULE, worth more than this instance: A GUARD OUTLIVES THE
# THING IT GUARDED. When a feature is removed, its validation is not neutral
# leftovers — it is a live veto over a value nothing consumes, and stale
# environment on a repointed box is exactly how it gets triggered. Deleting the
# consumer without deleting the assert is how a clean box refuses to boot.
# previous fork, and v4 neither reads it nor cares.
# ── v4.0 — THE LAYER-2 CONVICTION STACK IS GONE ─────────────────────────────
# try/except that set _L2_OK. At the v4 split those modules were dropped and the
# except branch became permanent: _L2_OK was ALWAYS False, so _l1_scorer and
# _l2_integ were ALWAYS None and every block gated on them was dead code that
# still had to be read and reasoned about by anyone touching this file.
#
# WHY THEY WENT. Measured 2026-08-19, tests/direction_skill.py, 715 closed
# directional trades across 16 sessions with ORB and neutral structures
# excluded: the label picked the correct SIDE on 44.9%, 95% CI [41.3%, 48.6%] -
# ENTIRELY BELOW A COIN FLIP. Calls 48.7%; puts 34.2%. ContinuationStrategy,
# which depended on it most, lost $5,872 across 660 trades.
# Conviction was confirmatory by construction: a leaky integrator over argmax
# agreement is only confident once winning has already persisted.
#
# ⚠️ DO NOT REINTRODUCE A CONVICTION GATE. `MarketState.conviction` still exists
# so the remaining reads can be removed file by file with tests passing at each
# step. It must not acquire a producer. See docs/INHERITED_FINDINGS.md.
_l2_mute = {}          # retained: read by the log-throttling helpers below
# only way to answer "which engine is running?" was to infer it from [L2]/[v13]

# v3.9 — signal journal (log-only). Guarded: the loop runs identically without it.
try:
    from analysis import signal_journal as _sigj
except Exception:
    _sigj = None

# v4.3 — trade readiness engine (LOG-ONLY, gates nothing). Guarded the same
# way: the trading loop is byte-identical if the import fails. Emits through
# the signal journal; with no journal it still tracks state silently (harmless).
try:
    from analysis.trade_readiness import TradeReadinessEngine as _TRE
    _readiness = _TRE(emit=(_sigj.journal if _sigj is not None else None),
                      contract_ctx=(_sigj.contract_ctx if _sigj is not None else None))
except Exception:
    _readiness = None

from typing import TYPE_CHECKING
if TYPE_CHECKING:                     # v4.9 — resolves the quoted annotation on
    from strategy.base_strategy import OptionsSignal   # _execute_condor_leg; a
                                      # forward reference never evaluates at
                                      # runtime, so this is lint-clean at zero
                                      # cost and lets the undefined-name gate
                                      # run at ZERO tolerance instead of one.
from strategy.orb_strategy import ORBStrategy
from strategy.volt_strategy import VoltStrategy
from strategy.runaway_continuation import RunawayContinuationStrategy
from strategy import observe as _observe      # r254 (OBS.1): the plan always looks
from strategy.sweep_credit_spread import SweepCreditSpreadStrategy
from strategy.gex_pin_butterfly import GEXPinButterflyStrategy
from strategy.atp_butterfly import ATPButterflyStrategy
from strategy.liquidity_hunt import LiquidityHunt                       # OTV4TEST r12
from execution import handoff as _handoff                              # OTV4TEST r12
from config import SWEEP_SETUP_FLOOR
from utils import mem_trace          # MEM.2 — in-process tracemalloc, env-gated

# MEM.2 — start at import. Deliberately placed BELOW this import and not
# beside the engine banner higher up: `_l2_ab` and the banner both live
# above the import block, so a call there is an unbound name. The
# undefined-name gate caught exactly that on the first attempt.
# No-op unless OT_MEM_TRACE is set; tracemalloc is not imported otherwise.
mem_trace.start(logger)
from strategy.iron_condor_strategy import IronCondorStrategy
from analysis.condor_trigger_map import build as _build_condor_trigger_map
from strategy.trend_credit_spread import TrendCreditSpread

from risk.risk_manager import init_risk_manager, get_risk_manager
from risk.session_guard import get_session_guard

from execution.entry_engine import get_entry_engine
from execution.position_manager import get_position_manager

from database.trade_logger import get_trade_logger
from utils.blindness_latch import BlindnessLatch, ALERT as _BLIND_ALERT, \
    RECOVERED as _BLIND_RECOVERED
from data.market_data import last_blindness, clear_blindness
from notifications.alert_manager import get_alert_manager


def _disk_sender():
    """The box's own Telegram sender for the disk guard. -> sender | None.

    ⚠️ LAZY AND SWALLOWED. The guard needs only `send()`, and building anything
    on the import path would put a credential read where a failure costs the
    BOT rather than the alert.
    """
    if not hasattr(_disk_sender, "_s"):
        try:
            from notifications.telegram_sender import TelegramSender
            _disk_sender._s = TelegramSender()
        except Exception:                                   # noqa: BLE001
            _disk_sender._s = None
    return _disk_sender._s



# Strategy singletons
_orb_strategy     = ORBStrategy()
_volt_strategy    = VoltStrategy()   # r72 — the control arm
_runaway_strategy = RunawayContinuationStrategy()
_sweep_cs_strategy = SweepCreditSpreadStrategy()
_gex_bfly_strategy = GEXPinButterflyStrategy()
_atp_bfly_strategy = ATPButterflyStrategy()
_liquidity_hunt = LiquidityHunt()                                      # OTV4TEST r12
from strategy.park import Park as _Park                                 # r288 (PARK.1)
_park_strategy = _Park()
from strategy.parc import Parc as _Parc                                 # OTV5 r46 (PARC.1)
_parc_strategy = _Parc()
from strategy.breakout import Breakout as _BreakoutStrategy            # OTV4TEST r51
_breakout = _BreakoutStrategy()                                        # BRK.1
_iron_condor_strategy = IronCondorStrategy()
# TC.6 — trend credit spread. Sits with the other strategy instances and is
# UNGUARDED on purpose: it imports only config + IronCondorStrategy, both
# already hard dependencies here, so a guarded import would hide a real
# breakage rather than tolerate an optional one.
_trend_credit_strategy = TrendCreditSpread()


# r204 (PREM.2) — ORCS, the opening range credit spread (PLAN_SPEC §41). The
# strategy owns its plan; `_attempt_orcs` asks it inside the entry dispatch.
_orcs_strategy = None
try:
    from strategy.orcs import OpeningRangeCreditSpread
    _orcs_strategy = OpeningRangeCreditSpread()
except Exception as _orcs_exc:                                 # noqa: BLE001
    logger.warning("[orcs] strategy not built - it will not trade or record this session: %s", _orcs_exc)


def _retired_reason(name: str) -> str:
    """r204 — the sweep and the TCS are retired by ruling (2026-10-03: "Retire the sweep & TCS").
    '' when `name` may be asked. Read at call time so a checker can flip the switch."""
    import config as _c
    from strategy import plan_state as _ps                      # r303: a LOG sweep / TCS is asked (recorded only)
    if name in ("SweepCreditSpread", "SweepForLeg2") and not _c.SWEEP_CS_ENABLED and not _ps.is_log("SweepCreditSpread"):
        return "retired by the operator's ruling 2026-10-03 (OT_SWEEP_CS=1 restores it)"
    if name == "TrendCreditSpread" and not _c.TREND_CREDIT_ACTIVE and not _ps.is_log("TrendCreditSpread"):
        return "retired by the operator's ruling 2026-10-03 (OT_TCS_ACTIVE=1 restores it; unset = log, r57)"
    return ""


def _attempt_orcs(ctx: dict, state) -> None:
    """r204/r206 — ask ORCS and hand each ready side to the house credit entry. Never raises."""
    if _orcs_strategy is None:
        return
    try:
        _px = float(ctx.get("price") or 0.0)
        _hi, _lo = ctx.get("orb_high"), ctx.get("orb_low")
        _inf = {"vix": getattr(ctx.get("macro"), "vix", None),
                "or_width_pct": (100.0 * (float(_hi) - float(_lo)) / _px) if _hi and _lo and _px > 0 else None}
        _sigs = _safe_strategy(_orcs_strategy.name, lambda: _orcs_strategy.generate_signals(
            price_now=_px, now_et=now_et(), chain=ctx.get("chain"), gap=ctx.get("gap"),
            informers=_inf) or None, ctx)
        for _sig in (_sigs or []):
            # r247 — THE LIVE REFUSAL COMES FIRST. ORCS is paper-only until the operator rules it
            # live; the refusal sat in _execute_condor_leg, AFTER ledger_open, so a live box wrote a
            # plan_ledger row for every ready side that no fill would ever close (SPX-TEST's audit).
            # The refusal in _execute_condor_leg stays as the backstop.
            if not getattr(state, "paper_trading", True):
                logger.warning("[orcs] LIVE: no ledger row and no entry - ORCS is paper-only until "
                               "the operator rules it live")
                continue
            _orcs_strategy.ledger_open(_sig)                    # r211: the row the fill links to
            _execute_condor_leg(_sig, state, ctx)
    except Exception as exc:                                   # noqa: BLE001
        logger.warning("[orcs] tick failed - nothing traded or recorded this tick: %s", exc)


class BotState:
    def __init__(self):
        self.last_assess_at:   Optional[datetime] = None
        self.prev_trend_direction: str = ""   # PHASE B: prior tick, for the gap measure
        self.tick_count:       int = 0
        self.errors_this_hour: int = 0
        self.paper_trading:    bool = PAPER_TRADING
        self.session_reset_done: bool = False   # Reset once per RTH open
        self.orb_reset_done:   bool = False     # ORB reset once per session
        self.orb_range_established_today: bool = False  # today's ORB range ESTABLISHED
        self.hard_close_alerted: bool = False   # alerted once on a failed 15:45 flatten
        self.last_reconcile_slot: Optional[str] = None  # last intraday broker-reconcile slot done
        # r63 — the derived engines, built ONCE per process. [] when the
        # derived store will not open, which is a normal degraded state and
        # not an error: derivers are contributors, never gates.
        self._orb_plan_id = None
        # r70 — any plan left LIVE by a dead process is recorded at boot.
        # ⚠️ LEG1_FILLED IS DELIBERATELY NOT WIPED — a leg is live at the
        # broker, so the intent must survive for the reconciler to act on.
        try:
            from derived.registry import plan_ledger as _plg
            _led = _plg(INSTRUMENT)
            if _led is not None:
                _led.mark_restart_wipe()
        except Exception:                                      # noqa: BLE001
            pass
        try:
            from derived.registry import build_engines
            self.derived_engines = build_engines(INSTRUMENT)
        except Exception as exc:                               # noqa: BLE001
            logger.warning("derived engines unavailable: %s — trading is "
                           "unaffected", exc)
            self.derived_engines = []
        # v4.11: pages once per outage when the bot cannot see, and once when
        # sight returns. Instantiated here so the latch state survives ticks.
        self.blind_latch = BlindnessLatch()






def atm_iv_from_chain(chain):
    """The ONE conversion from a chain to a stored ATM IV. None when absent.

    🔑 EXTRACTED SO IT CAN BE TESTED. `run_analysis` needs live market data and
    cannot run in a sandbox, so a check that only exercised it would report
    "could not execute" and gate nothing — the weak-gate failure that let r201
    ship (WORKING_AGREEMENT §0.4). This function is the part worth pinning and
    it runs anywhere.

    ⚠️ NONE, NEVER 0.0. A chain whose feed has not populated ivs yet is ABSENT,
    not zero-vol, and r177 exists precisely because a `getattr(..., 0.0)`
    default masked that absence for months. Downstream must be able to tell
    "no reading" from "a reading of zero".
    """
    if chain is None:
        return None
    try:
        return float(getattr(chain, "atm_iv", 0.0) or 0.0) or None
    except Exception as exc:                                    # noqa: BLE001
        # Never silent — a chain that cannot produce an IV is a fact worth
        # seeing, not a blank (§0.5).
        logger.warning("[atm_iv] chain present but unreadable: %s", exc)
        return None


def _orb_engine_ready() -> bool:
    try:
        return get_orb_engine() is not None
    except Exception:                                          # noqa: BLE001
        return False


_FLOW_CONN = {"c": None}


def _flow_conn():
    """A read-only handle on the feed store for the order-flow readers.

    r51 — opened once and reused; `None` on any failure, because every consumer
    already treats a missing connection as "no reading" and an exception here
    would take the whole tick down for a contributor.
    """
    if _FLOW_CONN["c"] is None:
        try:
            import sqlite3
            from data.candle_feed import feed_db_path
            _FLOW_CONN["c"] = sqlite3.connect(
                f"file:{feed_db_path()}?mode=ro", uri=True, check_same_thread=False)
        except Exception as exc:                               # noqa: BLE001
            logger.warning("[flow] read-only feed handle unavailable, order-flow "
                           "readings will be absent: %s", exc)
            _FLOW_CONN["c"] = False
    return _FLOW_CONN["c"] or None


def run_analysis(state: BotState, chain=None) -> dict:
    """Fetch all market data and run analysis pipeline."""
    cache  = get_cache()
    data   = cache.get_all()
    price  = cache.get_price()
    if price is None:
        raise ValueError("Could not fetch current price")

    df_5m  = data.get("5m")
    df_1m  = data.get("1m")
    df_15m = data.get("15m")
    df_1h  = data.get("1h")

    if df_5m is None or df_5m.empty:
        raise ValueError("No 5m data available")

    df_1h_safe = df_1h if df_1h is not None else df_5m

    vol_state = get_volatility_engine().analyze(df_5m, df_1h_safe, price)
    trend     = get_trend_engine().analyze(data)
    structure = get_structure_analyzer().analyze(df_5m, df_15m, df_1h, price)

    # ── v6.18 — BIND ctx BEFORE ANYTHING WRITES INTO IT ─────────────────────
    # v6.16/v6.17 (Level.1, A2.6b) wrote ctx["gap"] / ctx["level_near"] into a
    # name that did not exist yet: run_analysis built its dict only at the
    # return statement. The NameError raised inside the try, and the except
    # handler's OWN ctx["gap"] = None re-raised it UNCAUGHT — so run_analysis
    # failed on EVERY tick: no ctx, no classification, no strategy could fire.
    # Same class as the is_trend_participation NameError (WA §21): a name
    # referenced before it exists, invisible to import and to py_compile.
    # The dict is bound HERE; the blocks below write into it; macro and orb
    # are added just before the single return.
    ctx = {
        "price":     price,
        "data":      data,
        "vol":       vol_state,
        "trend":     trend,
        "structure": structure,
        "df_1m":     df_1m,
        "df_5m":     df_5m,
        # OTV4TEST r5 — the level engine retires levels inside the opening range
        "orb":       (get_orb_engine().data if _orb_engine_ready() else None),
        # OTV4TEST r29 — the tape the session levels are built from (levels v5.0)
        # 🔴 r51 — `_flow_conn` HAD NO PRODUCER. It is READ by `derived/notes.py`
        # (tape, defence, break_tape) and by `derived/snapshot.py`, and was set
        # by NOTHING — so `analysis/order_flow.aggression()` on that path has
        # never run. PROVEN, not inferred: 400 sampled `strategy_note` payloads
        # carry the `tape` key ZERO times. Every order-flow reading those two
        # modules were written to take has been silently absent since the day
        # they landed. Same shape as the dead FOMC detector: a consumer with no
        # producer, failing quietly because absence and "measured as zero" look
        # identical from downstream.
        # ⚠️ READ-ONLY, AND ITS OWN HANDLE. The feed store is the producer's;
        # a reader opens it `mode=ro` so no consumer can ever write to the wire
        # record, and holding a separate connection keeps a slow flow query off
        # the writer's lock.
        "_flow_conn": _flow_conn(),
    }

    # ── Level.1 (2026-08-18) — WHAT IS PRICE TRADING INTO? ──────────────────
    # ⚠️ `level_strength` was written ONLY by `sweep_reversal`, which is
    # hard-gated (main.py:1325) with a 0.4% live win rate — so the column was
    # populated by a strategy that essentially does not trade, and 94% of the
    # book carried the default. The probe read that as "levels do not separate
    # outcomes." It never measured levels at all.
    # This puts the graded nearest level in ctx for EVERY strategy, every tick.
    # ⚠️ STRUCTURAL, NOT MAGNITUDE: "there is prior-day liquidity half a percent
    # above" is a statement about WHERE PRICE IS, which is the class the
    # operator reads charts with and the class nothing here has ever recorded.
    # ── A2.6b (2026-08-18) — MEASURE THE GAP, DO NOT INHERIT IT ─────────────
    # ⚠️ THE ONLY PRE-OPEN DECISION-TIME INPUT IN THE STACK. ADX, conviction,
    # the overnight gap is fully formed at 09:30 before a single RTH bar prints.
    # ⚠️ TODAY IT ENTERS ANONYMOUSLY. `atr_series` uses true range with
    # prev_close and the 5m tape is continuous, so a large gap SPIKES ATR at the
    # open and decays over the window — every consumer sees a volatility number
    # that is partly last night's news and cannot tell which part.
    # Operator, 2026-08-01: "the gaps you see overnight from previous close to
    # current open are big and meaningful, and they have to be reflected
    # somewhere."
    try:
        from analysis.gap_measure import measure_gap
        # point — classification happens further down the tick — and a bare
        # prior_dir=0 forever, making `gap_class` permanently "UNDIRECTED".
        # A silent constant is exactly the failure this whole week has been
        # about, so the prior tick's committed direction is used instead: it is
        # yesterday's trend at the open, which is precisely what CONT/REV means.
        # PHASE B (r58): the prior direction now lives on BotState directly.
        # ASSIGNED, so _pd was a silent 0 and gap_class was permanently
        # UNDIRECTED since the split: the exact failure the comment above
        # warns about, one attribute over. prev_trend_direction is committed
        # at the END of each analysis pass, so this tick reads the PRIOR one.
        _dir = getattr(state, "prev_trend_direction", "") or ""
        _pd = 1 if _dir == "BULLISH" else (-1 if _dir == "BEARISH" else 0)
        # CD.3 (DISC.4) — the feed store's prior-session daily bar and today's 09:30 bar see the gap on every tick;
        # the 5m frame (the fallback) saw it on 11 of 314 trade rows (it rarely reaches yesterday).
        ctx["gap"] = measure_gap(df_5m, prior_dir=_pd, symbol=INSTRUMENT, day=now_et().date())
    except Exception:                                          # noqa: BLE001
        ctx["gap"] = None

    macro     = get_macro_manager().get()

    # engine can gate its re-arm decision (this runs before reclassification).
    # v4.3 — the ORB engine no longer receives a label. It was handed
    # therefore never varied. Passing None makes the absence explicit rather
    # than dressing it as a measurement.
    # ── r95 — TAPE REACH-BACK BEFORE THE STATE MACHINE RUNS ─────────────────
    # 🔴 A RESTART USED TO ERASE THE SESSION. The engine reloads its RANGE from
    # orb_range.json; nothing reloaded its STATE, so a restarted engine came
    # back to WAITING_FOR_BREAK with no break latches, no attempt count, and no
    # memory of a runaway invalidation.
    #
    # ⚠️ THE POINT IS NOT TO RECOVER THE MISSED TRADE — the operator has ruled
    # that a fired trigger is not re-enterable, and the engine enforces it. The
    # payoff is that a restarted box stops taking trades it should refuse: after
    # a runaway the ORB is DORMANT by design, and a forgetful restart would arm
    # on a later break the design exists to reject.
    #
    # ⚠️ IT MUST RUN BEFORE update(), NOT AFTER. Replaying the session on top of
    # a state machine that has already advanced would hand 09:31 bars to a
    # retest check armed from the newest bar. The engine loads its own range for
    # exactly this reason.
    #
    # ⚠️ AND IT MUST NOT BE HANDED ctx["df_1m"]. That frame is capped at 60 bars
    # by TIMEFRAMES, so at 10:37 it begins at 09:37 and cannot see a 09:40 break
    # at all — the same left-edge trap that killed `_opening_range` every
    # session until TCS.3. `fetch_candles` is the one definition of a
    # session-scoped read and already filters poison bars, so the reach-back
    # uses it rather than growing a second reader.
    _orb_eng = get_orb_engine()
    # ── 🔴 r103 — THE STATE FILE IS READ, NOT JUST WRITTEN ───────────────────
    # orb_state.json has been written every tick since v3 and read by NOBODY;
    # r95 then built a tape replay to reconstruct exactly what it already held.
    # Operator, 2026-08-24: "if it HAD the orb state, but was interrupted, it
    # should have written it down. It can easily confirm orb state after any
    # restart, so a 1x look back function is grossly underpowered."
    # AUTHORITATIVE, per the operator's ruling: "If it wrote it, trust it."
    # ⚠️ ONCE PER PROCESS. `_orb_state_loaded` on BotState, not a module global,
    # so a restart is a fresh load and a live process never re-reads a file it
    # is itself writing.
    if not getattr(state, "_orb_state_loaded", False):
        state._orb_state_loaded = True
        try:
            if _orb_eng.load_state_file(
                    os.path.join(os.path.dirname(LOG_FILE), "orb_state.json")):
                # The file is truth up to its last write; the bars since then
                # are the GAP, and the reach-back exists to close it.
                _orb_eng.mark_rebuild_owed()
        except Exception as _lse:                              # noqa: BLE001
            logger.warning("ORB state resume failed (%s) — the tape reach-back "
                           "covers it", _lse)
    if _orb_eng.needs_tape_rebuild:
        try:
            from data.market_data import fetch_candles as _fetch_deep_1m
            _deep_1m = _fetch_deep_1m(INSTRUMENT, "1m", ORB_REBUILD_1M_BARS)
            if _deep_1m is not None and not _deep_1m.empty:
                # r61 (ORB.10): with no ORB owner the replay releases each OPEN_* on its bar, as below
                _orb_eng.rebuild_from_tape(_deep_1m, release_open=_orb_release_due(state))
                # ── r95 — A MISSED SETUP IS A ROW, NOT A LOG LINE ───────────
                # Operator's ruling, 2026-08-24: an interrupted firing sequence
                # is never re-entered — it is LOGGED AS MISSED. The log is not
                # where that becomes countable: PLANS is, which is where the
                # 08-24 QQQ loss was actually seen. One row per missed setup,
                # opened and closed in the same breath because it was over
                # before this process existed.
                _miss = _orb_eng.take_missed_confirmation()
                if _miss:
                    # ── 🔴 r103 — FIRED OR GENUINELY MISSED? ADJUDICATE FIRST.
                    # Operator, 2026-08-24: "figure out if it fired or if we
                    # genuinely missed it before closing out the row." The tape
                    # cannot distinguish a setup this process never saw from one
                    # a PREVIOUS process saw, took and recorded before it died —
                    # both look identical in the bars. The trades table can.
                    # ⚠️ A FALSE MISS IS WORSE THAN NO COUNT. The missed
                    # population exists to measure what the fleet is losing to
                    # outages; a row for a trade that actually filled inflates
                    # that loss and would send us hunting a defect that isn't
                    # there — the same reasoning as the r82 counter that "got
                    # worse the harder we tried to fix it".
                    try:
                        _fired = get_trade_logger().orb_entry_since(
                            _miss.get("confirmed_bar") or "")
                    except Exception:                          # noqa: BLE001
                        _fired = None
                    if _fired is not None:
                        logger.info(
                            "ORB reach-back: the tape's confirmation at %s was "
                            "TAKEN, not missed — trade %s is on the book "
                            "(entry %s). No MISSED row written.",
                            _miss.get("confirmed_bar"),
                            str(_fired.get("trade_id", ""))[:8],
                            _fired.get("entry_time"))
                        _miss = None
                if _miss:
                    # ⚠️ AND IT IS JOURNALLED LIKE A DECLINE. Operator: "missed
                    # should log the way a declined is — with all the known
                    # parameters captured with it." Same file, same shape, so
                    # missed and declined are one query apart.
                    if _sigj is not None:
                        try:
                            _sigj.journal("disposition", outcome="missed",
                                          orb=_miss,
                                          reason="TRIGGER_FIRED_WHILE_DOWN")
                        except Exception:                      # noqa: BLE001
                            pass
                    try:
                        from derived.registry import plan_ledger as _plg_m
                        _ledm = _plg_m(INSTRUMENT)
                        if _ledm is not None:
                            _mid = _ledm.open_plan(
                                "ORBStrategy", "CONFIRMED", ctx,
                                direction=_miss.get("direction"),
                                trigger_price=_miss.get("trigger_price"),
                                underlying_at_decision=price)
                            if _mid:
                                _ledm.transition(
                                    _mid, "MISSED",
                                    "TRIGGER_FIRED_WHILE_DOWN"
                                    f" bar={_miss.get('confirmed_bar')}"
                                    f" age_s={_miss.get('age_s')}")
                    except Exception as _mexc:                 # noqa: BLE001
                        logger.debug("missed-plan record: %s", _mexc)
        except Exception as _exc:                              # noqa: BLE001
            # Never let the reach-back take the tick with it: without it the
            # engine simply behaves as it did before r95.
            logger.warning("ORB tape reach-back skipped: %s", _exc)

    orb = _orb_eng.update(df_5m, df_1m, price, None)
    # ── r61 (ORB.10) — A CONFIRMATION NOBODY CAN TRADE IS RELEASED ON ITS TICK ──
    # ORBStrategy is retired; only an ORB close / offer release / same-side Runaway fire ever
    # released OPEN_*, so the engine held the first break's side to 15:40 and Runaway (which reads
    # its direction off the state) never saw the reversal. HERE, not after the ORB dispatch:
    # attempt_new_entry returns before the dispatch on blocked / capped / no-chain ticks, and every
    # bar the engine reads while OPEN_* is lost. Before the state file and the plan-ledger block, so
    # a dormant ORB writes no CONFIRMED row (r303: dormant plans do not write to the ledger).
    if (orb.state in (ORBState.OPEN_LONG, ORBState.OPEN_SHORT)
            and _orb_release_due(state)):
        _orb_eng.release_unowned()
        orb = _orb_eng.data                 # r96: the release may have replaced ORBData

    # Write ORB state to JSON file so status.py can read it directly
    # without parsing bot.log — eliminates all log-parsing timing issues.
    # Includes the disarm reason, break latches, live price and the 11:00
    # cutoff flag so status can render the true engine state (DISARMED / EXPIRED
    # / price-vs-range) rather than inferring it from the clock.
    try:
        import json as _json
        _eng = get_orb_engine()
        _now_et = now_et()
        # r103 — THE ENGINE OWNS THE SNAPSHOT. It is now read back on restart,
        # so the writer and the reader must be the same code; a dict assembled
        # here would drift from `load_state_file` on the first field either one
        # gained. Every key status.py consumes is still present.
        _orb_state = _eng.state_snapshot(price)
        _state_path = os.path.join(os.path.dirname(LOG_FILE), "orb_state.json")
        with open(_state_path, "w") as _f:
            _json.dump(_orb_state, _f)
    except Exception:
        pass

    # v6.18 — ctx was bound above; add the last two members and return it.
    ctx["macro"] = macro
    ctx["orb"]   = orb

    # ── r70 — ORB CONFIRMATION IS A PLAN, AND IT IS RECORDED ────────────────
    # 🔴 ON 2026-08-21 CRM, GOOGL, UNH AND SPX ALL CONFIRMED BREAK+RETEST
    # BETWEEN 10:20 AND 10:24 AND NONE OF THEM TRADED. The 10:39 deploy
    # erased in-process confirmation state — v3's orb_state.json write-only
    # lesson recurring — and ORB dies at 11:00, so there was no second chance.
    # A confirmed break+retest IS a plan waiting on a trigger, so it belongs in
    # the same ledger with the same lifecycle.
    # ⚠️ RECORDED, NOT RESTORED. The row makes the loss COUNTABLE; resuming a
    # stale confirmation blind after an outage is a different decision and
    # needs re-qualification against the current tape.
    try:
        _st = str(getattr(orb, "state", "") or "")
        if _st in ("ORBState.OPEN_LONG", "ORBState.OPEN_SHORT",
                   "OPEN_LONG", "OPEN_SHORT"):
            if getattr(state, "_orb_plan_id", None) is None:
                from derived.registry import plan_ledger as _plg
                _led = _plg(INSTRUMENT)
                if _led is not None:
                    state._orb_plan_id = _led.open_plan(
                        "ORBStrategy", "CONFIRMED", ctx,
                        direction=("LONG" if "LONG" in _st else "SHORT"),
                        trigger_price=getattr(orb, "orb_high", None)
                        if "LONG" in _st else getattr(orb, "orb_low", None),
                        underlying_at_decision=ctx.get("price"))
        elif getattr(state, "_orb_plan_id", None) is not None:
            # The engine left the confirmed state without a fill: the setup
            # expired or was invalidated. ⚠️ RECORDED WITH ITS REASON so
            # "confirmed but never traded" becomes a countable population.
            from derived.registry import plan_ledger as _plg
            _led = _plg(INSTRUMENT)
            if _led is not None:
                _led.transition(state._orb_plan_id, "EXPIRED",
                                str(getattr(orb, "invalidation_reason", "")
                                    or "left_confirmed_state"))
            state._orb_plan_id = None
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("orb plan ledger: %s", exc)
    # PHASE B (r58): commit THIS tick's direction for the NEXT tick's gap
    try:
        state.prev_trend_direction = getattr(ctx.get("trend"), "overall_direction", "") or ""
    except Exception:                                          # noqa: BLE001
        pass

    # ── 🔴 THE DERIVED LAYER (r63, 2026-08-22) ───────────────────────────────
    # raw port -> home -> deriver -> derived home -> ctx -> engine.
    # Every derived port is assembled HERE, once, so it is present on every
    # tick for every consumer.
    # ⚠️ THIS IS THE FIX FOR THE ctx["chain"]/ctx["gex"] SHAPE. Those are
    # written mid-dispatch at ~line 2746, so their availability depends on
    # where in the tick you stand — an input present for one consumer and
    # absent for another. No derived port may be built that way.
    # ⚠️ CONTRIBUTORS, NEVER GATES — operator's ruling. `run_all` and every
    # engine's `run()` are wrapped so nothing here can raise into the tick
    # loop, and the whole block is belt-and-braces wrapped again. A box with
    # no derived store trades EXACTLY as it does today.
    # ⚠️ EVERY KEY IS SET EVEN WHEN None. A consumer must be able to tell
    # "measured as absent" from "this port does not exist in this build".
    # r75 — character: the tape's state, with how long it has held. ⚠️ It
    # INFORMS and gates nothing, like every other derived port.
    # r78 — fork tilt, PARALLEL like ADX/ATR/gap: recorded and shown, feeding
    # no axis and gating nothing. The condor still anchors on the fork's
    # EXISTENCE, not its tilt.
    ctx.setdefault("fork_slope_ratio", None)
    ctx.setdefault("fork_slope_label", None)
    ctx.setdefault("fork_reject_reason", None)
    ctx.setdefault("character", None)
    ctx.setdefault("character_held_s", None)
    ctx.setdefault("charm", None)
    ctx.setdefault("vanna", None)
    ctx.setdefault("levels", None)
    # ── r205 — ATM IV IS COMPUTED AND WAS NEVER STORED ────────────────────
    # 🔴 MEASURED FROM THE BUCKET, NOT REASONED: every one of the 31
    # fire_snapshot rows from the fleet's first live session (2026-08-31)
    # carried `price` and a NULL `atm_iv`, across all 13 symbols that fired.
    # The value existed the whole time. `chain.atm_iv` is a real property
    # (options_chain.py:175, added by r177) and `chain` is a PARAMETER of this
    # function — but the only two readers, the butterfly dispatch branches at
    # ~3378 and ~3596, bound it to a LOCAL `_atm_iv` and passed it straight
    # into generate_signal. Nothing ever assigned `ctx["atm_iv"]`; a grep for
    # any assignment came back empty. This setdefault(None) was the first and
    # last word on the field.
    # ⚠️ THE SNAPSHOT WAS THE SYMPTOM, NOT THE INJURY. `ctx["atm_iv"]` feeds
    # `volatility_measures.summarise(...)` below, which produces
    # expected_move_iv and variance_risk_premium — both derived from None since
    # they were written. The comment above that call says "THE DECAY IS THE
    # POINT... a constant atm_iv scalar gave one expected move all day", so the
    # term it was built to supply never arrived either.
    # ⚠️ `chain` is None on the two derive-only callers (4059, 4179) by design;
    # only the trading tick (4223) passes it. A None chain leaves this None,
    # which is honest — the value is ABSENT, not zero.
    ctx["atm_iv"] = atm_iv_from_chain(chain)
    ctx.setdefault("iv_slope", None)
    ctx.setdefault("realised_vol_cc", None)
    ctx.setdefault("realised_vol_parkinson", None)
    ctx.setdefault("variance_risk_premium", None)
    ctx.setdefault("expected_move_iv", None)
    ctx.setdefault("expected_move_straddle", None)
    ctx.setdefault("session_fraction_remaining", None)
    # 🔴 r134 — THE CONDOR TRIGGER MAP ON ctx, BEFORE THE ENGINES RUN.
    # ⚠️ THE SAME DEFECT AS THE CHAIN, A SECOND INPUT. `ctx["condor_triggers"]`
    # was published mid-dispatch (main.py ~3081) while run_analysis ends at
    # 1456 — so the fork builder hit `ctm is None`, returned None, and wrote
    # NOTHING. On the fleet's first working session both ForkCreditSpread and
    # IronCondor were simply ABSENT from plan_tick while five other plans wrote
    # 80-95 rows each.
    # ⚠️ THE MAP IS CHEAP AND PURE — it reads the fork series already on ctx
    # and computes rail positions. Building it here costs no market data, and
    # the dispatch below now REUSES this one rather than rebuilding, so every
    # consumer this tick reads the SAME geometry (which was the map's whole
    # purpose when it was introduced).
    try:
        from analysis.condor_trigger_map import build as _bctm
        ctx["condor_triggers"] = _bctm(ctx, INSTRUMENT, CONDOR_TRIGGER_APPROACH)
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("condor trigger map (pre-engines): %s", exc)
        ctx.setdefault("condor_triggers", None)

    # 🔴 r134 — THE OPENING RANGE ON ctx. `_opening_range()` existed and was
    # recomputed from the tape, but its result was never PUBLISHED, so the
    # session map (which is centred on the 5-minute ORB range) had no marker
    # and could not classify a single level. Operator: *"Why don't we use the
    # five minute ORB range as the marker? Levels have to be above the ORB or
    # below to count and they have to be the right kind."*
    # ⚠️ SET EVEN WHEN None — before 09:35 ET there is genuinely no range, and
    # a consumer must be able to tell that from "this port does not exist".
    try:
        _oh, _ol = _opening_range(ctx)
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("opening range: %s", exc)
        _oh = _ol = None
    ctx["orb_high"], ctx["orb_low"] = _oh, _ol

    # 🔴 r138 — THREE MORE ctx KEYS THE PLAN BUILDERS READ AND NOBODY SET.
    # ⚠️ Each one silently DISABLED a gate rather than raising, which is the
    # quietest failure mode of the day: `ctx.get(k)` with a default never
    # errors, so the code reads a fallback and the check simply never applies.
    #   · open_trades  — _roll finds condor legs here. Absent ⇒ it reported
    #                    "0 condor leg(s) open" on EVERY tick, so the entire
    #                    roll/tent/close ladder has never once been evaluated
    #                    against a real structure.
    #   · now_et_minutes — the tent's 15:45 flatten deadline. Absent ⇒ the
    #                    fallback of 999 minutes meant the cutoff NEVER fired.
    #   · tent_floor_pct — the tent's economic floor, so it uses the declared
    #                    default rather than config.
    try:
        from database.trade_logger import get_trade_logger as _gtl
        ctx["open_trades"] = list(_gtl().get_open_trades())
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("ctx open_trades: %s", exc)
        ctx.setdefault("open_trades", [])
    # ⚠️ `now_et()` — NOT `_now_et`, which is a LOCAL VARIABLE at line 1322,
    # and TENT_FLOOR_PCT imported by name, because `config` is not imported as
    # a module here. Both checked against the file before writing this, which
    # is the discipline the whole day argued for.
    try:
        _et = now_et()
        ctx["now_et_minutes"] = _et.hour * 60 + _et.minute
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("ctx now_et_minutes: %s", exc)
        ctx.setdefault("now_et_minutes", None)
    try:
        from config import TENT_FLOOR_PCT as _TFP
    except Exception:                                          # noqa: BLE001
        _TFP = 0.15
    ctx.setdefault("tent_floor_pct", _TFP)
    # ⚠️ AND THE TENT'S OTHER TIME SOURCE. `minutes_to_flatten` is the branch
    # taken when now_et_minutes is None; leaving it unset meant that branch
    # fell to a hardcoded 999 and the deadline could never fire either way.
    # Derived from the SAME 15:45 flatten so the two can never disagree.
    try:
        from config import VERTICAL_HOLD_TO_ET as _VH
        from utils.time_utils import close_anchored as _ca
        _VHa = _ca(_VH, now_et())                     # r268 (DEP.12): the day's bell
        _fm = _VHa.hour * 60 + _VHa.minute
        _nm = ctx.get("now_et_minutes")
        ctx["minutes_to_flatten"] = (float(_fm - _nm) if _nm is not None
                                     else None)
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("ctx minutes_to_flatten: %s", exc)
        ctx.setdefault("minutes_to_flatten", None)

    # 🔴 r133 — CHAIN AND GEX ON ctx BEFORE THE ENGINES RUN, not after.
    # ⚠️ SET EVEN WHEN None, like every other port above: a consumer must be
    # able to tell "measured as absent" from "this key does not exist".
    ctx["chain"] = chain
    try:
        if chain is not None:
            from data.gex_data import compute_gex as _cg
            ctx["gex"] = _cg(chain, ctx.get("price"))
        else:
            ctx.setdefault("gex", None)
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("pre-analysis gex: %s", exc)
        ctx.setdefault("gex", None)

    _apply_vol_ports(ctx)      # r196: BEFORE the engines, so the character engine can read them
    _publish_recorder_keys(ctx)   # r213: the notes / snapshot / ledger inputs nothing ever set

    try:
        engines = getattr(state, "derived_engines", None)
        # Published on ctx so the fire-snapshot path can reach them from any
        # call site without a module global.
        ctx["derived_engines"] = engines
        if engines:
            from derived.base import run_all
            run_all(engines, ctx)
            _apply_derived_ports(ctx, state, engines)
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("derived layer skipped this tick: %s", exc)
    return ctx


def _publish_recorder_keys(ctx: dict) -> None:
    """r213 (REC.1) — set the ctx keys the RECORDERS read and nothing wrote.

    derived/notes.py, derived/snapshot.py and derived/plan_ledger.py read these by
    name; main never published them, so every field built on them was NULL (the
    10-03 audit, B12). Each comes from a value this tick already holds - nothing
    is measured here. setdefault only (a real writer, if one ever appears, wins);
    every read is wrapped; what cannot be read stays ABSENT, never 0.
    RECORD-ONLY: no strategy and no gate reads any of these keys."""
    def _put(key, fn):
        if ctx.get(key) is not None:
            return
        try:
            v = fn()
            if v is not None:
                ctx[key] = v
        except Exception as exc:                               # noqa: BLE001
            logger.debug("recorder key %s not published: %s", key, exc)

    _gx = ctx.get("gex")
    _px = ctx.get("price")
    _put("expected_move", lambda: ctx.get("expected_move_iv"))
    _put("gex_pin", lambda: (float(_gx.pin_strike) if _gx is not None and float(_gx.pin_strike or 0) > 0 else None))
    _put("pin_concentration", lambda: (float(_gx.pin_concentration) if _gx is not None
                                       and getattr(_gx, "pin_concentration", None) is not None else None))
    _put("prev_close", lambda: (ctx.get("gap") or {}).get("prior_close"))

    def _rails():
        from derived import anchors as _A
        rc = _A.rail_context(_px)
        if not rc:
            return None
        return {"upper": rc.get("rail_above_price"), "lower": rc.get("rail_below_price"),
                "built": bool(rc.get("rail_fork_built")), "slope_per_bar": rc.get("rail_slope_per_bar"),
                "reject_reason": ctx.get("fork_reject_reason")}
    _put("fork_rails", _rails)

    def _fork_state():
        from derived import anchors as _A
        st = {tf: _A.fork_dir(tf) for tf in ("15m", "1h")}
        st["reject_reason"] = ctx.get("fork_reject_reason")
        return st if any(v is not None for v in st.values()) else None
    _put("fork_state", _fork_state)

    def _swept():
        from data.derived_store import get_derived_store
        _n = now_et()
        _open = _n.replace(hour=9, minute=30, second=0, microsecond=0).timestamp()
        return get_derived_store().latest_rejection(INSTRUMENT, since_ts=_open)
    try:
        if ctx.get("swept_level_price") is None:
            _ev = _swept()
            if _ev:
                ctx["swept_level_price"] = float(_ev["price"])
                ctx.setdefault("swept_level_kind", _ev.get("kind"))
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("recorder key swept_level not published: %s", exc)


def _apply_vol_ports(ctx: dict) -> None:
    """Realised vol, VRP and the decaying expected move onto ctx. NEVER raises.

    🔴 r196 (AUD.5) — CALLED BEFORE THE DERIVED ENGINES RUN. It lived at the top
    of `_apply_derived_ports`, which runs AFTER `run_all(engines, ctx)`, so the
    character engine read ctx["realised_vol_cc"] / ["realised_vol_parkinson"]
    while they were still the setdefault(None) above: character_axis_sample's
    vol_ratio, close_capture and both realised vols were NULL on 3,580 of 3,580
    rows from 2026-09-12 to 2026-10-03 (the 10-03 audit) - the data the
    day-type bands were to be fitted on. The same order defect r133 fixed for
    the chain and GEX. Nothing here reads an engine: bars, spot and atm_iv are
    all on ctx before the engines run. The block is MOVED, not copied.
    """
    from analysis import volatility_measures as _vm

    # Volatility measures — realised, VRP and an EXPECTED MOVE THAT DECAYS.
    # ⚠️ THE DECAY IS THE POINT. A constant atm_iv scalar gave one expected
    # move all day, so an afternoon entry looked identically sized to a
    # morning one. This term is the fraction of the SESSION remaining.
    try:
        df5 = ctx.get("df_5m")
        bars = []
        if df5 is not None and not getattr(df5, "empty", True):
            bars = df5.tail(120).to_dict("records")
        summ = _vm.summarise(bars, "5m", spot=ctx.get("price"),
                             atm_iv=ctx.get("atm_iv"))
        for k, v in summ.items():
            if v is not None or ctx.get(k) is None:
                ctx[k] = v
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("vol measures unavailable: %s", exc)


def _apply_derived_ports(ctx: dict, state: "BotState", engines) -> None:
    """Lift derived values into ctx. NEVER raises — see the block above.

    ⚠️ CHARM, VANNA AND GEX ARE UNIVERSAL PORTS — operator, 2026-08-22: they
    must contribute to every strategy where they could meaningfully
    contribute. They are derived ONCE and offered to all engines rather than
    recomputed per strategy, because two consumers computing the same quantity
    at different points in a tick can legitimately disagree, and that is a bug
    nobody would ever find.
    """
    # r196 (AUD.5): the volatility measures moved to `_apply_vol_ports`, which
    # run_analysis calls BEFORE the engines run - see its docstring.
    # Fork tilt from the most recent stored row for the condor's anchor frame.
    # ⚠️ READ FROM `fork_series`, NOT REBUILT. The row already carries slope,
    # atr_at_birth and the reject reason, so this survives a restart and costs
    # one indexed lookup instead of a 60-80 bar scan.
    try:
        from derived import anchors as _AN
        _fr = _AN.fork_row(CONDOR_PF_TIMEFRAME)                # CD.2: current by market time, or None
        if _fr is not None:
            _r = (_fr["built"], _fr["reject_reason"], _fr["slope"], _fr["containment"])
            if _r:
                if _r[0]:
                    from analysis.pitchfork import SLOPE_FLAT_ATR
                    _atr = getattr(ctx.get("vol"), "atr_current", None)
                    if _atr and float(_atr) > 0 and _r[2] is not None:
                        _ratio = float(_r[2]) / float(_atr)
                        ctx["fork_slope_ratio"] = _ratio
                        ctx["fork_slope_label"] = (
                            "BULLISH" if _ratio > SLOPE_FLAT_ATR else
                            "BEARISH" if _ratio < -SLOPE_FLAT_ATR else "FLAT")
                else:
                    # ⚠️ NO FORK IS NOT A FLAT FORK. The label stays None and
                    # the REASON is carried so the display can say which.
                    ctx["fork_reject_reason"] = _r[1]
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("fork slope port unavailable: %s", exc)

    # Character — current state and its duration, read from the engine that
    # owns the ledger so status and the strategy notes see the same value.
    try:
        for e in engines:
            if getattr(e, "name", "") == "character":
                _c = e.current()
                if _c:
                    ctx["character"] = _c.get("character")
                    ctx["character_held_s"] = _c.get("held_s")
                break
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("character port unavailable: %s", exc)

    # Nearest levels each way, WITH PROVENANCE and touch score — the
    # operator's own framing of what price is trading into.
    try:
        for e in engines:
            if getattr(e, "name", "") == "levels":
                ctx["levels"] = e.walk(ctx.get("price"), limit=3)
                break
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("level walk unavailable: %s", exc)

    # Second-order greeks, ATM-nearest, from the series this box has kept.
    try:
        store = None
        for e in engines:
            store = getattr(e, "_store", None) or store
        price = ctx.get("price")
        if store is not None and price:
            # CD.2 — FRESH first, then nearest: a row whose quotes are older than SURFACE_MAX_AGE_S is not this moment,
            # whatever its strike. ORDER BY strike distance first let the nearest strike from any day win.
            from derived.anchors import SURFACE_MAX_AGE_S as _SMAX
            _exp = str(ctx.get("expiry") or "")
            row = store.conn.execute(
                "SELECT charm, vanna FROM surface_series"
                " WHERE symbol=? AND quote_ts IS NOT NULL AND quote_ts >= ?"
                " AND (expiry=? OR ?='' OR expiry IS NULL OR expiry='')"
                " ORDER BY ABS(strike-?) ASC, quote_ts DESC LIMIT 1",
                (INSTRUMENT, time.time() - _SMAX, _exp, _exp, float(price))).fetchone()
            if row:
                ctx["charm"], ctx["vanna"] = row[0], row[1]
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("second-order ports unavailable: %s", exc)


def assemble_market_state(ctx: dict, trigger: str, state: BotState) -> MarketState:
    """Gather structural facts into a MarketState. Classifies NOTHING.


    produced a six-way label and a conviction number, and Layer 2 then
    OVERRODE the label with an integrated one. Measured 2026-08-19 across 715
    closed directional trades: that label picked the correct SIDE 44.9% of the
    time, 95% CI [41.3%, 48.6%] - entirely below a coin flip, and 34.2% on
    puts. The scoring is gone.

    WHAT REPLACES IT: nothing. This assembles the SAME structural facts the
    classifier used to gather - adx, atr, bb width, trend direction, structure
    Those facts were always the useful part; the label was the part that
    failed.

    4.1, and until it exists an honest UNKNOWN is better than a number nobody
    should trust. INFORMS, NEVER AUTHORISES - no setup may require one.

    `conviction` is NOT SET HERE. It survives on the dataclass only so the 49
    remaining reads can be removed file by file; nothing should produce it.
    """
    vol = ctx.get("vol")
    trend = ctx.get("trend")
    structure = ctx.get("structure")
    macro = ctx.get("macro")

    ms = MarketState(
        macro_context=getattr(macro, "vix_band", "UNKNOWN") or "UNKNOWN",
        adx=float(getattr(trend, "primary_adx", 0.0) or 0.0),
        atr_normalized=float(getattr(vol, "atr_normalized", 0.0) or 0.0),
        bb_width_pct=float(getattr(vol, "bb_width_pct", 0.5) or 0.5),
        trend_direction=getattr(trend, "overall_direction", "NEUTRAL") or "NEUTRAL",
        structure_sequence=getattr(structure, "structure_sequence", "NEUTRAL") or "NEUTRAL",
        vix_band=getattr(macro, "vix_band", "UNKNOWN") or "UNKNOWN",
        classified_at=now_utc().isoformat(),
        trigger=trigger,
    )

    # The flat angle is produced by the RANGING/COMPRESSION evaluation and lands
    # in the L1 breakdown. NEGATIVE means NOT COMPUTED - zero degrees IS the
    # flattest possible reading, so a 0.0 default is indistinguishable from a
    # genuinely flat tape. That confusion made this column read as 100% ties on
    # ONE unique value in v3 and be scored as a measured null when it was simply
    # never written.
    try:
        _bd = (ctx.get("l1_breakdown") or {})
        # PHASE B: keyless — only the two flat-family scorers emit an angle,
        # so the first non-None wins without naming a label.
        for _v in _bd.values():
            _a = (_v or {}).get("angle")
            if _a is not None:
                ms.flat_angle_deg = float(_a)
                break
    except Exception:                                          # noqa: BLE001
        pass

    state.last_assess_at = now_utc()
    return ms


# ── 🔴 r67 (2026-08-25) — RESTORED, SAME CLASS AS THE alert_manager CRASH ────
# Both sets back these functions' "log once per reason per process" guards, and
# both were declared `global` inside the function while existing nowhere at
# module level. Unlike the alert_manager NameError — which fired on EVERY boot
# and crash-looped all 15 boxes — these fire only the FIRST TIME A CAPTURE
# FAILS, inside the trade-write path. That is strictly worse to debug: the
# failure needs another failure to reveal it, and it lands mid-fill.
# ⚠️ FOUND BY AST SWEEP, NOT BY A TEST. `import main` succeeds; the name only
# resolves at CALL time. That is why tests/check_singletons.py now EXECUTES
# accessors instead of importing modules.
_contract_warned: set = set()
_snapshot_warned: set = set()


def _capture_entry_contract(ctx: dict, record: dict, tl=None) -> bool:
    """v5.5 (N.9) — persist the CONTRACT's own state at entry.

    Every value here was ALREADY IN MEMORY: `OptionContract` carries
    bid/ask/mark/delta/gamma/theta/vega/iv and `OptionsChain` carries
    spot_price/iv_rank. They were read for strike selection and discarded.
    Nothing new is fetched, subscribed or computed.

    WHY: every other instrument in this repo reports WHAT the premium did.
    None reports WHY. A -27% floor stop is currently indistinguishable between
    "the underlying went against us", "the underlying went nowhere and theta
    ate it", and "we were right and IV collapsed" — three causes, three
    different fixes, one number. On 0DTE that distinction is the whole game.

    Matched on the OCC symbol the row was actually filled on, not on strike:
    two legs of a condor share an underlying and a session, and picking the
    wrong side would attribute one leg's greeks to the other.

    Log-only. A failure warns once per reason per process and never gates.
    """
    trade_id = (record or {}).get("trade_id", "")
    occ = (record or {}).get("option_symbol", "")
    reason = ""
    try:
        chain = (ctx or {}).get("chain")
        payload = None
        if (record or {}).get("is_butterfly"):
            # v5.7 (FLY.3) — a fly's option_symbol is its CENTER leg; matching it
            # recorded the body's quote and greeks as the fly's. The fly's own
            # values from its three legs, or nothing - never the body's.
            payload, reason = _fly_entry_contract(chain, record)
        else:
            con = None
            if chain is not None and occ:
                for c in list(getattr(chain, "calls", []) or []) + \
                         list(getattr(chain, "puts", []) or []):
                    if getattr(c, "symbol", "") == occ:
                        con = c
                        break
            if con is None:
                reason = "contract-not-found"
            else:
                payload = {
                    "entry_delta": getattr(con, "delta", None),
                    "entry_gamma": getattr(con, "gamma", None),
                    "entry_theta": getattr(con, "theta", None),
                    "entry_iv":    getattr(con, "iv", None),
                    "entry_bid":   getattr(con, "bid", None),
                    "entry_ask":   getattr(con, "ask", None),
                    "chain_iv_rank": getattr(chain, "iv_rank", None),
                }
        if payload is not None:
            if (tl or get_trade_logger()).set_entry_contract(trade_id, payload):   # r57: tl = the shadow store
                return True
            reason = "write-returned-false"
    except Exception as exc:                                 # noqa: BLE001
        # Logged INLINE so the W.2 swallow census can see this handler is not
        # silent — it reads the except body, not the code after it.
        logger.debug("entry_contract capture raised (%s: %s)",
                     type(exc).__name__, exc)
        reason = f"raised:{type(exc).__name__}"

    if reason not in _contract_warned:
        _contract_warned.add(reason)
        logger.warning(
            "entry_contract NOT captured (%s) for %s — this trade cannot enter "
            "the premium-decomposition read (direction vs theta vs IV); logged "
            "once per reason per process.", reason, trade_id[:8])
    return False


def _fly_entry_contract(chain, record: dict):
    """v5.7 (FLY.3) — the BUTTERFLY's entry quote and greeks, built from its legs.

    Returns (payload, "") or (None, reason). The same composite
    execution/position_manager builds for a fly's exit record (r195): sell the
    wings at their bids and buy the body back at its ask for the bid, the
    reverse for the ask, each floored at 0. Greeks are the position's net,
    lower + upper - 2 x center, per one fly. entry_iv is the BODY's IV, as
    _note_quote records a fly - a fly has no IV of its own and the body is
    the leg its value turns on.

    Legs are found by their OCC symbols (lower/center/upper_symbol, persisted
    since entry_engine v3.7), else by strike on the fly's side of the chain.
    A leg not found writes NOTHING: three legs or no row, never the body's
    values under the fly's name (the 2026-10-26/28 defect).
    """
    if chain is None:
        return None, "fly-no-chain"
    side = str(record.get("option_side", "") or "").lower()
    calls = list(getattr(chain, "calls", []) or [])
    puts = list(getattr(chain, "puts", []) or [])
    by_sym = {getattr(c, "symbol", ""): c for c in calls + puts if getattr(c, "symbol", "")}
    pool = calls if side == "call" else puts if side == "put" else []
    legs = {}
    for leg in ("lower", "center", "upper"):
        con = by_sym.get(record.get(f"{leg}_symbol") or "")
        if con is None:
            k = record.get(f"{leg}_strike")
            con = next((c for c in pool if k and getattr(c, "strike", None) == k), None)
        if con is None:
            return None, f"fly-leg-not-found:{leg}"
        legs[leg] = con
    lo, ce, up = legs["lower"], legs["center"], legs["upper"]

    def _f(c, k):
        v = getattr(c, k, None)
        return None if v is None else float(v)

    def _net(k):
        a, b, m = _f(lo, k), _f(up, k), _f(ce, k)
        return None if None in (a, b, m) else a + b - 2.0 * m

    g = lambda c, k: float(getattr(c, k, 0.0) or 0.0)
    return {
        "entry_delta": _net("delta"),
        "entry_gamma": _net("gamma"),
        "entry_theta": _net("theta"),
        "entry_iv":    getattr(ce, "iv", None),            # the BODY's IV
        "entry_bid":   max(0.0, g(lo, "bid") + g(up, "bid") - 2.0 * g(ce, "ask")),
        "entry_ask":   max(0.0, g(lo, "ask") + g(up, "ask") - 2.0 * g(ce, "bid")),
        "chain_iv_rank": getattr(chain, "iv_rank", None),
    }, ""


def _capture_fire_snapshot(ctx: dict, record: dict, link_plan: bool = True) -> None:
    """r63 — freeze EVERY derived value at the instant this trade fired.

    🔴 THE EDGE STUDY IS A JOIN: fire_snapshot JOIN trades ON trade_id.
    Derived indicators on one side, outcome and excursion on the other, so
    "did high charm at fire predict a larger MFE?" becomes one query. Today
    that question cannot be asked at all.

    ⚠️ EXCURSION TELEMETRY IS UNAFFECTED. mfe/mae live on `trades` because
    they are properties of the trade's LIFE; this is one frozen instant at
    entry. Different clocks, different tables — and the join makes excursion
    work BETTER than it does now.

    label plus conviction and dropped every term that decided the entry — a
    vocabulary of two for a decision made on twenty. Pre-selecting the columns
    defeats a study whose whole purpose is DISCOVERING which indicator
    separates outcomes.

    ⚠️ NEVER RAISES. A study artifact must not be able to fail a fill.
    """
    # ⚠️ THE ENGINES COME FROM ctx, NOT A MODULE GLOBAL. The first draft
    # reached for a `_bot_state` global that DOES NOT EXIST in this module —
    # so it would have found nothing on every fill and written no snapshots at
    # all, silently, forever. Exactly the shape of defect this whole weekend
    # has been about; caught by grepping for the name instead of assuming it.
    try:
        from derived.registry import snapshot_engine
        eng = snapshot_engine((ctx or {}).get("derived_engines"))
        tid = (record or {}).get("trade_id", "")
        if eng is not None and tid:
            eng.capture(tid, ctx)
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("fire snapshot skipped: %s", exc)

    # 🔴 LINK THE FILL TO THE PLAN THAT INTENDED IT (r144).
    # ⚠️ `plan_ledger.trade_ids` has existed since the file was written and
    # NOTHING EVER WROTE TO IT — 863 plans across 15 boxes, zero linked.
    # Without this, a plan records what it EXPECTED and the trade records what
    # it RETURNED, and nothing joins them: "did TAKE plans make money" — the
    # literal bottom line of docs/VISION.md — is unanswerable.
    # ⚠️ HOOKED HERE because this function already runs on EVERY fill and
    # already holds the trade record. A link that depends on each strategy
    # remembering to pass a plan id is a link the next strategy will not have.
    if not link_plan:                                           # r57 (TCS.LOG1): a shadow links no plan row
        return
    try:
        from derived.registry import plan_ledger as _pl
        _led = _pl(INSTRUMENT)
        _tid = (record or {}).get("trade_id", "")
        _strat = (record or {}).get("strategy", "") or ""
        if _led is not None and _tid:
            _led.link_trade(_strat, _tid)
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("plan link skipped: %s", exc)


def _capture_entry_snapshot(ctx: dict, record: dict, direction: str, tl=None) -> bool:
    """Persist the entry-time FVG/structure picture onto the trade row.

    Called only after a fill is confirmed and the row exists. Returns True on a
    write. A failure is logged ONCE per reason per process and then never again:
    a per-fill warning would be spam, and no warning at all is how three dead
    timeframes went unnoticed for two weeks.
    """
    trade_id = (record or {}).get("trade_id", "")
    try:
        payload = _entry_snapshot_json(ctx, direction)
        wrote = (tl or get_trade_logger()).set_entry_snapshot(trade_id, payload)   # r57: tl = the shadow store
        if not wrote:
            reason = "write-returned-false"
        elif '"err"' in payload:
            reason = "payload-error"
        else:
            return True
    except Exception as exc:                                 # noqa: BLE001
        # Logged HERE as well as in the warning below so the W.2 census can see
        # this handler is not silent — it reads the except body, not the code
        # that follows it.
        logger.debug("entry_snapshot capture raised (%s: %s)",
                     type(exc).__name__, exc)
        reason = f"raised:{type(exc).__name__}"
        payload = ""

    if reason not in _snapshot_warned:
        _snapshot_warned.add(reason)
        logger.warning(
            "entry_snapshot NOT captured (%s) for %s — this trade cannot enter "
            "the TC.2 exit counterfactual; logged once per reason per process. "
            "%s", reason, trade_id[:8], payload[:300])
    return False


def _credit_window_end(signal) -> tuple:
    """When this credit structure's ENTRY window closes — the time gate a
    remainder honours (WORKING_AGREEMENT §37: hunting stops only at the
    strategy's own time gate). TCS reads its config constant; the sweep reads
    its module's LATEST_ET; anything else falls to 14:00 and says so."""
    name = getattr(signal, "strategy_name", "") or ""
    if getattr(signal, "is_trend_credit", False) or name == "TrendCreditSpread":
        # OTV4TEST r9 (HYG.5): the PLAN owns the window; main.py reads it there
        from strategy import tcs_plan as _tp
        return _tp.window_end()
    if name == "PARC":                                          # OTV5 r46 (PARC.1): its own window
        from config import ENTRY_WINDOWS as _EW
        return tuple(_EW["PARC"][1])
    if name == "SweepCreditSpread":
        try:
            from strategy import sweep_plan as _sp          # r9: the plan's window (a tuple)
            return tuple(_sp.LATEST_ET)
        except Exception:                                      # noqa: BLE001
            pass
        try:
            from strategy import sweep_credit_spread as _scs
            hh, mm = str(_scs.LATEST_ET).split(":")
            return (int(hh), int(mm))
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[remainder] sweep LATEST_ET unreadable (%s) — 14:00", exc)
    return (14, 0)


def _post_credit_vertical(short_contract, long_contract, contracts: int,
                          lkey: str, structure: str, what: str = "condor-leg entry",
                          placer=None, confirmer=None, pricer=None,
                          mark_fallback: float = 0.0):
    """Post ONE rung of a SELL vertical for `contracts` and confirm it.

    Returns (fill, limit, why). The ladder is refused for the rung on any
    non-fill or partial (the operator's definition of a refusal) and CLEARED
    only when the whole requested quantity filled. This is the single placer
    for a credit vertical — the entry AND the remainder supervisor use it —
    so the two can never price a rung differently.

    r220's structure quote, kept verbatim: we SELL the spread, so the best
    credit is `short.ask - long.bid` and the worst is `short.bid - long.ask`;
    their midpoint is `short.mid - long.mid`, EXACTLY the credit paper books.
    Live walks DOWN from the best credit and stops at mark.

    `placer(legs, limit) -> response`, `confirmer(placed, basis, deadline_s)
    -> EntryFill` and `pricer(lkey, side, bid, ask, sym, structure)` default
    to the SDK and the registry; tests inject all three.
    """
    from config import INSTRUMENT
    from execution.entry_engine import EntryEngine
    from execution.order_confirm import EntryFill

    _sb = float(getattr(short_contract, "bid", 0.0) or 0.0)
    _sa = float(getattr(short_contract, "ask", 0.0) or 0.0)
    _lb = float(getattr(long_contract, "bid", 0.0) or 0.0)
    _la = float(getattr(long_contract, "ask", 0.0) or 0.0)
    _st_bid, _st_ask = max(0.0, _sb - _la), max(0.0, _sa - _lb)
    _mark = (_st_bid + _st_ask) / 2.0
    # ⚠️ THE FALLBACK IS THE CALLER'S CREDIT, NEVER A BARE MARK. r220 fell back
    # to `net_credit`; a first cut of this helper fell back to `_mark`, which is
    # 0.00 on an empty quote, and the war game filled a 0.00-credit sell
    # instantly. A remainder has no signal credit to fall back to, so with no
    # usable quote and no positive fallback NOTHING IS POSTED.
    _limit, _lwhy = float(mark_fallback or 0.0), "static (no usable structure quote)"
    try:
        if pricer is None:
            from execution import ladder_registry as _lr
            pricer = lambda k, sd, b, a, sym, st: _lr.price_for(   # noqa: E731
                k, sd, b, a, sym, structure=st)
        _got = pricer(lkey, "sell", _st_bid, _st_ask, INSTRUMENT, structure)
        if _got:
            _limit, _lwhy = float(_got[0]), str(_got[1])
    except Exception as _lexc:                                  # noqa: BLE001
        # ⚠️ FALLS BACK TO THE MARK CREDIT, NEVER TO A WORSE PRICE.
        logger.warning("[ladder] credit-vertical pricing failed (%s) — "
                       "posting at the mark credit", _lexc)
    if _limit <= 0.0:
        logger.warning("[ladder] %s credit vertical x%d: NO ORDER — no usable "
                       "structure quote (%.2f/%.2f) and no positive fallback",
                       INSTRUMENT, contracts, _st_bid, _st_ask)
        return (EntryFill(filled=False, detail="no usable structure quote; nothing posted"),
                0.0, "not posted")
    logger.info("[ladder] %s credit vertical x%d: posting %.2f (%s) "
                "[structure %.2f/%.2f, mark %.2f]",
                INSTRUMENT, contracts, _limit, _lwhy, _st_bid, _st_ask, _mark)

    # ⚠️ r315 — THE DEADLINE IS PER RUNG, NOT PER ENTRY. This call carried no
    # deadline_s and took the 20s default: one rung per 20-26s against a 15s
    # tick, the exact shape entry_engine's own comment warns "would never
    # reach mark inside a fill window".
    _deadline = EntryEngine._rung_deadline()

    if placer is None or confirmer is None:
        from data.tasty_client import get_session, get_account, sdk_result
        from execution.order_confirm import confirm_order_fill
        from tastytrade.order import (NewOrder, Leg, OrderAction, OrderType,
                                      OrderTimeInForce, InstrumentType)
        from decimal import Decimal
        session = get_session()
        account = get_account()
        if placer is None:
            def placer(legs, limit):
                order = NewOrder(time_in_force=OrderTimeInForce.DAY,
                                 order_type=OrderType.LIMIT,
                                 price=Decimal(str(round(limit, 2))),  # + = credit
                                 legs=[Leg(instrument_type=InstrumentType.EQUITY_OPTION,
                                           symbol=sym, action=act, quantity=q)
                                       for sym, act, q in legs])
                return sdk_result(account.place_order(session, order, dry_run=False))   # B0
        if confirmer is None:
            def confirmer(placed, basis, deadline_s):
                return confirm_order_fill(session, account, placed, basis,
                                          what=what, deadline_s=deadline_s)
        _legs = [(short_contract.symbol, OrderAction.SELL_TO_OPEN, contracts),
                 (long_contract.symbol,  OrderAction.BUY_TO_OPEN,  contracts)]
    else:
        _legs = [(short_contract.symbol, "SELL_TO_OPEN", contracts),
                 (long_contract.symbol,  "BUY_TO_OPEN",  contracts)]

    # B2 (r466) — never post an intent whose previous order is still in doubt.
    from execution import order_guard as _guard
    _sess = locals().get("session"); _acct = locals().get("account")
    if _acct is not None:
        _ok, _gwhy = _guard.clear_to_post(lkey, _sess, _acct)
        if not _ok:
            logger.warning(f"[guard] credit vertical not posted: {_gwhy}")
            return EntryFill(filled=False, detail=f"guard: {_gwhy}"), _limit, _lwhy
        # F5 (r473) — the margin a short vertical ties up is its width less the credit.
        from execution import buying_power as _bp
        _width = abs(float(getattr(short_contract, "strike", 0) or 0)
                     - float(getattr(long_contract, "strike", 0) or 0))
        _need = max(0.0, _width - float(_limit or 0.0)) * int(contracts) * 100.0
        _bok, _bwhy = _bp.affordable(_need, _sess, _acct, what)
        if not _bok:
            logger.warning(f"[bp] credit vertical not posted: {_bwhy}")
            return EntryFill(filled=False, detail=f"buying power: {_bwhy}"), _limit, _lwhy
    response = placer(_legs, _limit)
    if getattr(response, "errors", None):
        logger.error(f"Condor leg order failed: {response.errors}")
        return EntryFill(filled=False, detail=f"rejected: {response.errors}"), _limit, _lwhy
    basis = [(short_contract.symbol, 1, +1),
             (long_contract.symbol,  1, -1)]   # net = short − long (credit)
    _placed = getattr(response, "order", response)
    try:
        fill = confirmer(_placed, basis, _deadline)
    except Exception:
        # B2 — the order WAS placed; refuse the rung, cancel, remember, page.
        try:
            from execution import ladder_registry as _lr_g
            _lr_g.refuse(lkey, _limit)
        except Exception:                                       # noqa: BLE001
            pass
        if _acct is not None:
            _guard.after_failure(lkey, _placed, _sess, _acct, what)
        raise

    from execution import ladder_registry as _lr
    _filled = int(getattr(fill, "quantity", 0) or 0) if getattr(fill, "filled", False) else 0
    if _filled >= contracts:
        # A COMPLETE FILL ENDS THE WALK — never leave a walk to rot.
        try:
            _lr.clear(lkey)
        except Exception as _cexc:                              # noqa: BLE001
            logger.debug("[ladder] clear failed: %s", _cexc)
    else:
        # ⚠️ A NON-FILL MUST ADVANCE THE WALK OR THE LADDER IS DECORATION —
        # and a PARTIAL is a refusal for the remainder (operator's definition:
        # "didn't completely fill at that price").
        try:
            _lr.refuse(lkey, _limit)
        except Exception as _rexc:                              # noqa: BLE001
            logger.debug("[ladder] refuse failed: %s", _rexc)
    return fill, _limit, _lwhy


def _supervise_credit_remainders(ctx: dict, state: BotState) -> None:
    """Post the next rung for every credit vertical still short of its
    requested size. r315. CALLED FROM BEFORE THE `has_open_position()` SPLIT,
    beside `_supervise_offers`, for the same reason that one is: the position
    the remainder belongs to is exactly what puts the box on the manage
    branch, where no entry code runs. Never raises into the loop."""
    try:
        from execution import credit_remainder as _cr
        if state.paper_trading or not _cr.active():
            return
        from config import CONTRACT_MULTIPLIER
        _tl = get_trade_logger()
        try:
            _open = {t.get("trade_id") for t in _tl.get_open_trades()
                     if t.get("status") == "open"}
        except Exception as _oexc:                              # noqa: BLE001
            logger.warning("[remainder] open-trade read failed (%s) — not abandoning on it", _oexc)
            _open = None
        _now = now_et()
        _cr.supervise(chain=ctx.get("chain"), now_hm=(_now.hour, _now.minute),
                      eod=is_hard_close_time(), paper=state.paper_trading,
                      open_trade_ids=_open,
                      place=lambda sc, lc, q, k, st: _post_credit_vertical(
                          sc, lc, q, k, st, what="credit remainder"),
                      trade_logger=_tl, multiplier=CONTRACT_MULTIPLIER)
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("remainder supervision skipped this tick: %s", exc)


def _sweep_stop_premium(credit, width, pct_fallback) -> float:
    """The sweep's premium stop: the credit PLUS 15% OF THE RISK (PLAN_SPEC §31).

    🔴 OTV4TEST r24 — THE ROW CARRIED THE RULE r155 DELETED. This stamp wrote
    `fill_credit * (1 + 0.15)` — fifteen percent of the CREDIT — while the spec
    says "15% of risk", the exit engine computes `entry + risk * 0.15`
    (exit_engine:2200) and entry feasibility judges survivability with
    `criteria.stop_distance`. The management plan reads THIS number and acts
    first, so the inverted stop is the one that fired. PROVEN ON 2026-09-11:
    the 12:04 718/719 call spread, credit 0.25, row stop 0.2875, stopped the
    same minute; replayed on real quotes its worst cost-to-close was 0.33,
    under the spec's 0.3625, and it expired worthless for the full credit.
    ⚠️ ONE DEFINITION: `criteria.stop_distance` — r234's rule that a second
    spelling of 0.15 is how the first rots.
    ⚠️ FAILS CLOSED: if the risk is unmeasurable the tighter credit-anchored stop
    is kept and SAID, never a permissive 0.0 (WORKING_AGREEMENT §22).
    """
    from strategy.criteria import stop_distance
    d = stop_distance(width, credit)
    if d is None:
        logger.warning("sweep stop: risk unmeasurable (width=%r credit=%r) — "
                       "keeping the credit-anchored stop", width, credit)
        return float(credit or 0.0) * (1 + float(pct_fallback or 0.0))
    return float(credit) + float(d)


def _stamp_vix(signal, ctx) -> None:
    """r200 (AUD.8) — VIX AT ENTRY, FOR EVERY STRATEGY. Only ORBStrategy and VOLT set
    `signal.vix_at_signal` (both are off the roster since r187), so every Breakout,
    Runaway, Hunt, sweep, trend-credit and butterfly row stored vix_at_entry = 0.0:
    141 of 194 closed trades since 09-21 (the 10-03 audit). Both executors call this
    first; the two record builders read the signal's field as they always did. A
    value a strategy set itself is KEPT. No macro, or no VIX: it stays 0.0. Never raises."""
    try:
        if float(getattr(signal, "vix_at_signal", 0.0) or 0.0) > 0:
            return
        vix = float(getattr((ctx or {}).get("macro"), "vix", 0.0) or 0.0)
        if vix > 0:
            signal.vix_at_signal = vix
    except Exception as exc:                                    # noqa: BLE001
        logger.debug("vix stamp skipped: %s", exc)


def _stamp_adx(signal, ctx) -> None:
    """MEAS.4 — ADX AT ENTRY, FOR EVERY STRATEGY, BESIDE THE VIX STAMP. Only ORBStrategy set
    `signal.adx_at_signal` (from MarketState.adx), so every other row stored adx_at_entry = 0.0.
    Same source ORB used: MarketState.adx IS ctx["trend"].primary_adx (assemble_market_state),
    so this reads that one field. A value a strategy set itself is KEPT. No trend, or no ADX: it
    stays 0.0. Record only - nothing gates on the field. Never raises."""
    try:
        if float(getattr(signal, "adx_at_signal", 0.0) or 0.0) > 0:
            return
        adx = float(getattr((ctx or {}).get("trend"), "primary_adx", 0.0) or 0.0)
        if adx > 0:
            signal.adx_at_signal = adx
    except Exception as exc:                                    # noqa: BLE001
        logger.debug("adx stamp skipped: %s", exc)


def _execute_condor_leg(signal: "OptionsSignal", state: BotState,
                        ctx: dict = None):
    """
    Execute a single condor leg (one vertical credit spread) from the
    OptionsSignal produced by IronCondorStrategy.check_leg_triggers().

    Legging model (per strategy design): Leg 1 fires on the side price is
    moving toward first; Leg 2 is queued and only fires after Leg 1 fills and
    the strategy cancels Leg 2 and the filled Leg 1 vertical is managed
    standalone through normal stop/nickel exits. This function just executes
    whichever leg the strategy has decided is ready this tick.

    Paper mode: fills at mid credit. Live mode: places the 2-leg vertical as a
    single CREDIT limit order via TastyTrade (same SDK pattern as entry_engine).
    """
    _stamp_vix(signal, ctx)                                     # r200: before the record is built
    _stamp_adx(signal, ctx)                                     # MEAS.4: beside it, same rule
    # r303 (PSTATE.1) — THE CREDIT DOOR. A LOG plan's vertical is recorded and never executed; r254's three
    # doors were all on the debit side, so nothing stopped a credit signal before this line. (After the VIX
    # stamp, which only annotates the signal: check_vix_stamp V4 pins it as the first statement.)
    # OTV5 r57 (TCS.LOG1) — A LOG TCS IS NOT REFUSED HERE: it runs the rest of this door as a SHADOW trade
    # (execution/shadow_book.py) - the real gates, contracts, sizing and paper fill - and is booked to its own store
    # where a real trade is written. It never reaches the live order block below, on any box.
    from execution import shadow_book as _sbm
    _shadow = _sbm.is_shadow_signal(signal)
    if not _shadow and _log_only(signal, ctx):
        return
    from config import (CONTRACT_MULTIPLIER, CONDOR_NICKEL_CLOSE,
                        CONDOR_STOP_LOSS_PCT, INSTRUMENT)
    from database.trade_logger import make_record, get_trade_logger
    import uuid

    mode = "SHADOW" if _shadow else "PAPER" if state.paper_trading else "LIVE"

    # ── 🔴 r101 — NOTHING OPENS BEFORE ENTRY_OPEN_ET (09:35 ET) ─────────────
    # The credit half of the pair of choke points; the debit half is
    # `entry_engine.enter`. All four triggers (1h fork, 1d fork, sweep, TC.6)
    # and the second-leg window route through here, so one test covers them.
    if not entries_open():
        logger.info("[entry-gate] %s %s HELD — entries open at %02d:%02d ET "
                    "(opening range not established, or past a half day's "
                    "entry cutoff — r268)", mode,
                    getattr(signal, "strategy_name", "credit vertical"),
                    *ENTRY_OPEN_ET[:2])
        return

    # Short/long contracts for this leg live on the call- or put-side fields.
    if signal.option_side == "call":
        short_contract = signal.short_call_contract
        long_contract  = signal.long_call_contract
    else:
        short_contract = signal.short_put_contract
        long_contract  = signal.long_put_contract

    if short_contract is None or long_contract is None:
        logger.error("Condor leg: missing contracts — cannot execute")
        return

    # r57 (TCS.LOG1) — admission's TCS rule (max_open_of_type=1) on the shadow's own book: the real admission and
    # pairing gate count the real book only, so one open shadow TCS refuses the next, as one real TCS would.
    if _shadow and _sbm.get_shadow_book().tcs_open():
        logger.info("[shadow] TCS %s spread NOT booked - a shadow TCS is already open (admission: one TCS open at a "
                    "time)", signal.option_side)
        return

    net_credit   = signal.net_credit
    spread_width = abs(short_contract.strike - long_contract.strike)
    # r204 — ORCS: its own name, PAPER ONLY until a live ruling. r230: the condor leg's stop and exits.
    _is_orcs = (getattr(signal, "strategy_name", "") == "OpeningRangeCreditSpread")
    _is_parc = (getattr(signal, "strategy_name", "") == "PARC")   # OTV5 r46 (PARC.1)
    if _is_orcs and not state.paper_trading:
        logger.warning("[orcs] LIVE entry REFUSED - ORCS is paper-only until the operator rules it live")
        return

    # Size this vertical at HALF the grade budget — each side is independent,
    # so a B-grade $1000 trade becomes two ~$500 verticals.
    # r192 — through the one door; the vertical rule and its arithmetic are
    # unchanged, only its address is.
    # ⚠️ grade is NOT passed. The default is already "B" (identical arithmetic
    # to the old positional call), and writing `grade="B"` here trips
    # check_conviction_removed S4 — "no code assigns an A or B grade". The
    # grading system is retired; this call must not look like it revives it.
    if _is_parc:
        # OTV5 r46 (PARC.1) — the Breakout ramp on the credit the ladder books (paper: paper_fill_credit of the mark).
        from execution.limit_ladder import paper_fill_credit as _pfc
        sizing = get_risk_manager().size_for(
            "parc", spread_width=spread_width,
            credit=(_pfc(net_credit) if state.paper_trading else net_credit),
            value_at_stop=getattr(signal, "parc_value_at_stop", None))
    else:
        sizing = get_risk_manager().size_for("vertical", spread_width=spread_width,
                                             credit=net_credit)
    if not sizing.allowed:
        logger.info(f"Condor leg not sized: {sizing.reject_reason}")
        return
    contracts = sizing.contracts
    _partial_remaining = 0          # r315 — set by a live partial, read at registration
    _lkey = None
    _req_contracts = contracts

    if not state.paper_trading and not _shadow:                  # r57: a shadow NEVER enters the live block
        # ── LIVE 2-leg vertical credit entry — FILL-CONFIRMED (v3.7, defect O) ─
        # Submission is not a fill. The record is written ONLY for contracts
        # the broker confirms filled, at the broker's per-leg net credit —
        # never the limit price we asked for. Unfilled by the deadline →
        # cancel and walk away (the strategy re-evaluates next tick).
        # A PARTIAL fill is a real position: book the filled quantity.
        # SDK NOTE (verified v13.x): NewOrder.price is SIGNED — positive =
        # CREDIT received, which is what a short vertical collects. The old
        # price_effect kwarg is ignored by current SDKs and is gone.
        # r315 — ONE PLACER, PER-RUNG DEADLINE, INTENT-KEYED WALK. The SDK
        # order build, the r220 structure quote and the refuse/clear bookkeeping
        # all live in `_post_credit_vertical` now, shared with the remainder
        # supervisor. The key is the INTENT — strategy + side — not the strike
        # pair, so a re-selected strike inherits the rung (entry_ladder v4.2).
        # ⚠️ CAPTURED BEFORE `contracts` IS REASSIGNED to the filled size.
        try:
            _req_contracts = contracts
            _strat_name = ("TrendCreditSpread"
                           if getattr(signal, "is_trend_credit", False)
                           else (getattr(signal, "strategy_name", "") or "CreditVertical"))
            _lkey = f"cv:{INSTRUMENT}:{_strat_name}:{signal.option_side}"
            _structure = f"{short_contract.symbol}|{long_contract.symbol}"
            fill, _limit, _lwhy = _post_credit_vertical(
                short_contract, long_contract, contracts, _lkey, _structure,
                mark_fallback=net_credit)
            if not fill.filled or fill.quantity <= 0 or fill.net_price is None:
                logger.warning(f"Condor leg entry NOT filled ({fill.detail}) — "
                               f"no position recorded")
                if fill.working_order_id:
                    get_alert_manager()._send(
                        f"\U0001F6A8 {INSTRUMENT} Condor entry order "
                        f"{fill.working_order_id} could not be cancelled and may "
                        f"still fill — reconcile will adopt it. ({fill.detail})")
                return
            _partial_remaining = 0
            if fill.quantity < _req_contracts:
                _partial_remaining = _req_contracts - fill.quantity
                logger.warning(f"Condor leg entry PARTIAL: {fill.quantity}/"
                               f"{_req_contracts} filled — booking the filled size; "
                               f"the remaining {_partial_remaining} keep walking")
            contracts   = fill.quantity          # book what ACTUALLY filled
            fill_credit = fill.net_price         # broker net, not our limit
            order_id    = fill.order_id or ""
        except Exception as e:
            logger.error(f"Condor leg order failed: {e}")
            return
    else:
        # ── PAPER books what the live mid-credit limit posts (v4.1). Routed
        # through limit_ladder.paper_fill_credit — the SINGLE paper-pricing
        # authority — so condor legs, rolled verticals, singles and butterflies
        # all degrade together under one knob (PAPER_FILL_SLIPPAGE_PCT,
        # default 0.0 = the mark). Before v4.1 this haircut was applied here
        # inline while entry_engine v3.8 had stopped applying it — paper
        # friction differed by strategy, which made cross-strategy paper P&L
        # non-comparable.
        from execution.limit_ladder import paper_fill_credit
        fill_credit = paper_fill_credit(net_credit)
        order_id    = "SHADOW" if _shadow else "PAPER"          # r57: a shadow books the paper fill on any box

    is_leg1  = "Leg 1" in signal.setup_type      # r106: display only, not identity
    max_loss = (spread_width - fill_credit) * contracts * CONTRACT_MULTIPLIER

    # ── DELTA STREET-SIGN (v3.x, 2026-07-15) ──────────────────────────────────
    # The BB-anchored selector already chose short_contract; we do NOT influence
    # that. We only READ the delta off the strike it picked and record it as the
    # setup_score, purely as a calibration waypoint. abs() puts put-side (negative
    # delta) and call-side (positive) on one 0-1 scale. If the Greeks feed didn't
    # populate delta (contract default 0.0), store NULL — a real short strike is
    # never exactly 0.0 delta, so NULL unambiguously means "delta unavailable",
    # not "delta was zero". Calibration can then trust every non-null value.
    short_delta = abs(getattr(short_contract, "delta", 0.0) or 0.0)
    delta_score = short_delta if short_delta > 0 else None

    # Register the leg as a TRACKED position so it is managed, exited, and P&L'd.
    # The condor is the ONLY strategy allowed a second concurrent position.
    # One function serves two trades; the identity must come from the SIGNAL,
    # never from the function it happens to route through.
    _is_tcs = bool(getattr(signal, "is_trend_credit", False))
    # r99 — the sweep now routes here too. Its identity rides its own
    # strategy_name (structure.of routes "SweepCreditSpread" to the
    # lone-vertical management its spec names: 15% floor or 15:45) and its
    # stop is its OWN max_loss_pct (SWEEP_CS_MAX_LOSS_PCT 0.15), not the
    # condor's 25%. Stamping "IronCondorStrategy" here is the 2026-08-14
    # identity bug — 108 trades attributed to a strategy that never fired them.
    _is_sweep = (getattr(signal, "strategy_name", "") == "SweepCreditSpread")
    # r106 — ONE FLOOR, 15%, for every credit vertical. The sweep carries its
    # own (identical) number; everything else takes the lone-vertical floor.
    # The 25% that used to be written here is retired: the live arm evaluated
    # 15% while the ROW said 25%, so the record and the alert both stated a rule
    # the engine did not apply.
    from config import CONDOR_LONE_STOP_PCT as _LONE
    _stop_pct = (float(getattr(signal, "max_loss_pct", 0.0) or 0.0)
                 if _is_sweep else 0.0) or _LONE
    record = make_record(
        trade_id         = str(uuid.uuid4()),
        symbol           = INSTRUMENT,
        strategy         = ("TrendCreditSpread" if _is_tcs
                            else "PARC" if _is_parc                       # OTV5 r46 (PARC.1)
                            else "OpeningRangeCreditSpread" if _is_orcs
                            else "SweepCreditSpread" if _is_sweep
                            else "IronCondorStrategy"),
        setup_type       = signal.setup_type,
        # ⚠️ r152 — the grade is gone; UNGRADED is a marker, not a verdict.
        setup_grade      = "UNGRADED",
        # 🔴 r154 — CARRY THE LEVEL ONTO THE TRADE. `log_exit` needs it to tell
        # the sweep strategy WHICH pool just failed; without it the level
        # re-arms forever (CVX 2026-08-27: four entries, same 198/192 pool,
        # five minutes, -$104). The signal has carried `pool_price` all along
        # and it was never persisted.
        pool_price       = float(getattr(signal, "pool_price", 0.0) or 0.0),
        setup_score      = delta_score,          # street-sign: |short-strike delta|
        direction        = (signal.direction if _is_parc else "neutral"),   # r46: PARC has a side of the tape
        option_side      = signal.option_side,
        is_butterfly     = 0,
        strike           = short_contract.strike,
        short_strike     = short_contract.strike,
        long_strike      = long_contract.strike,
        spread_width     = spread_width,
        credit_received  = fill_credit,
        expiry           = getattr(short_contract, "expiry", ""),
        contracts        = contracts,
        entry_premium    = fill_credit,                # credit basis for exits
        total_cost       = max_loss,
        max_loss         = max_loss,
        # NO PREMIUM STOP ON A TREND CREDIT SPREAD. Its measured EV was HELD
        # TO EXPIRY, UNMANAGED, and its only exits are a breach of the bound or
        # the 15:45 close. Writing a stop here is what made a $0.06 credit
        # closeable on one cent of widening.
        stop_premium     = (0.0 if (_is_tcs or _is_parc)   # r230: an ORCS leg takes the condor leg's stop; r46: PARC none
                            else _sweep_stop_premium(fill_credit, spread_width, _stop_pct)
                            if _is_sweep
                            else fill_credit * (1 + _stop_pct)),
        target_premium   = CONDOR_NICKEL_CLOSE,
        underlying_entry = getattr(signal, "underlying_entry", 0.0),
        # ⚠️ TC.6 CARRIES ITS OWN IDENTITY THROUGH THIS PATH (2026-08-14).
        # This function builds the record for BOTH a condor leg and a trend
        # credit spread, and it was hardcoding condor identity onto both. The
        # consequences were total, not cosmetic:
        #   · `is_trend_credit` never reached the record, so
        #     `_evaluate_condor_leg`'s TC.6 branch — gated on
        #     `record.get("is_trend_credit")` — COULD NEVER FIRE. Every TC.6 leg
        #     fell into the condor ladder and picked up the ratchet and the 25%
        #     premium stop. That is the `stop=$0.69` on a $0.55 credit seen in
        #     Telegram at 10:02 on 2026-08-14.
        #   · `underlying_stop` was never set, so even had the branch fired the
        #     breach rule would have had NO BOUND to test and would have skipped
        #     itself silently.
        #     as IronCondorStrategy in RANGING and their P&L was attributed to
        #     the condor.
        # The strategy and the exit engine were both correct in isolation; the
        # HANDOFF between them dropped every flag they agreed on.
        # v4.3 — was `("RANGING" if not _is_tcs else ... or "TRENDING")`, which
        # STAMPED A LABEL NOTHING MEASURED onto every trade row. The column is
        # but it now records the honest answer.
        underlying_stop  = getattr(signal, "underlying_stop", 0.0),
        # ── TCS.4 (2026-08-17) — REMOVED: `is_trend_credit` IS NOT A COLUMN ──
        # ⚠️ THIS CRASH-LOOPED NFLX LIVE. `log_entry` INSERTs every key in the
        # record, so a key with no column raises OperationalError on the INSERT,
        # the loop error counter hits its cap, and the service shuts down and
        # restarts — every 15s, for the whole session.
        # It never fired before today because TC.6 could never REACH execution:
        # TCS.3 fixed the bound at noon and **the first trade that formed
        # correctly died at the write.** A latent defect exposed by a fix, which
        # is the shape audit #1 was convened over.
        # `structure.py` has said this since 08-14 — *"`is_trend_credit` IS NOT
        # A COLUMN"* — and already derives the answer from the PERSISTED
        # `strategy`/`setup_type`. Verified with the flag absent:
        # is_trend_participation -> True, is_credit_vertical -> True. The field
        # was write-only and the exit path never needed it.
        vix_at_entry     = getattr(signal, "vix_at_signal", 0.0),
        adx_at_entry      = getattr(signal, "adx_at_signal", 0.0)
                            or 0.0,
        flat_angle_deg    = getattr(signal, "flat_angle_deg", 0.0),
        # ── Level.1 (2026-08-18) — PERSIST THE GRADE OR IT IS TELEMETRY ─────
        # ⚠️ THE WHOLE POINT OF THIS WEEK: a quantity computed and not written
        # to the row cannot be tested against outcomes. `direction_conf`
        # separated on the live book and was journaled nowhere;
        # object; the pusher's SHORT lines were captured and truncated. This is
        # the same class, caught before shipping rather than after.
        # Falls back to the strategy's own value (sweep sets one directly), so
        # a strategy with a better local read is not overwritten by a generic
        # proximity grade.
        # r123 — the strategy's own value only: the old mapper's nearest-pool
        # fallback filled nothing on any of 138 trades and is gone with it.
        level_strength    = float(getattr(signal, "level_strength", 0.0) or 0.0),
        # A2.6b: persist the gap or it is telemetry. Backfillable, so historical
        # rows can be filled retroactively — unlike everything else this week.
        gap_pct           = ((ctx.get("gap") or {}).get("gap_pct")
                             if isinstance(ctx, dict) else None),
        swept_level_name  = getattr(signal, "swept_level_name", "") or "",
        # v6.9 (AUDIT F6): a TC.6 record must not claim condor-leg identity —
        # is_condor_leg is what _condor_sibling_open and condor_roll key on,
        # and condor_leg_num=2 on every TC.6 row was data pollution.
        is_condor_leg    = (0 if _is_parc else 1),   # v4.3: all credit verticals are condor-eligible; r46: PARC pairs with nothing
        # 🔴 r106 — ALWAYS 0. Operator, 2026-08-24: "There is no condor implied,
        # it is merely PERMITTED." Leg 1 / leg 2 is plan vocabulary from the
        # state machine r90 removed — it numbered verticals by FILL ORDER as if
        # a pair were being assembled to a design. Two verticals that happen to
        # coexist have no first and no second. The COLUMN stays (nothing that
        # reads it breaks on 0, and dropping it would rewrite the table); it
        # simply stops carrying a meaning nothing means.
        condor_leg_num   = 0,
        condor_trigger_source = getattr(signal, 'condor_trigger_source', ''),
        is_broken_wing   = 0,
        short_symbol     = getattr(short_contract, "symbol", ""),
        long_symbol      = getattr(long_contract, "symbol", ""),
        option_symbol    = getattr(short_contract, "symbol", ""),
        order_id         = order_id,
        paper_trade      = 1 if state.paper_trading else 0,
        relaxed_entry    = int(getattr(signal, 'relaxed_entry', 0) or 0),   # AUDIT F4 — same drop as entry_engine
        status           = "open",
    )
    if _is_parc:
        # OTV5 r46 (PARC.1) — the signal columns PARK writes (entry_engine._record_kwargs and its record) that this
        # door does not, so a PARC row drops nothing a PARK row carries.
        record.update(underlying_target=float(getattr(signal, "underlying_target", 0.0) or 0.0),
                      is_fed_day=bool(getattr(signal, "is_fed_day", False)),
                      notes=str(getattr(signal, "notes", "") or ""),
                      trail_activation=0.0, is_liquidity_hunt=0)
    if _shadow:
        # ── r57 (TCS.LOG1) — THE SHADOW WRITE: everything an executed trade writes, to the SHADOW store. Not
        # trades.db, not note_entry_risk, not the real position manager, no remainder, no Telegram alert.
        _sbk = _sbm.get_shadow_book()
        if not _sbk.open_entry(record, box_paper=state.paper_trading):
            return
        if ctx is not None:
            _capture_entry_snapshot(ctx, record, "neutral", tl=_sbk.logger)
            _capture_fire_snapshot(ctx, record, link_plan=False)
            _capture_entry_contract(ctx, record, tl=_sbk.logger)
        logger.info(
            f"[shadow] TCS SHADOW TRADE BOOKED (never ordered): {record['trade_id'][:15]} {signal.setup_type} "
            f"short={short_contract.strike:g} long={long_contract.strike:g} x{contracts} credit=${fill_credit:.2f} "
            f"exit=breach@{getattr(signal, 'underlying_stop', 0.0):.2f} or nickel or EOD | maxloss=${max_loss:.0f} "
            f"(OT_TCS_ACTIVE unset/log; =1 trades it)")
        return
    get_trade_logger().log_entry(record)
    try:                                                        # r208 (CAP.4): log-only
        get_risk_manager().note_entry_risk(record)
    except Exception as _cfe:                                   # noqa: BLE001
        logger.warning("cap counterfactual skipped: %s", _cfe)
    # v5.1 — a condor leg is "neutral": no in-favor side, so no trail anchor.
    # The zone inventory is still captured — it bounds where the underlying had
    # room to run toward either short strike. ctx is optional so a caller that
    # cannot supply one degrades to no capture rather than to a raise.
    if ctx is not None:
        _capture_entry_snapshot(ctx, record, (signal.direction if _is_parc else "neutral"))
        _capture_fire_snapshot(ctx, record)
        _capture_entry_contract(ctx, record)          # v5.5 (N.9)
    get_position_manager(state.paper_trading).add_condor_leg(record)
    # r315 — a PARTIAL leaves an open intent. Register it against the SAME
    # record object the position manager now holds, so accretion updates the
    # record under management and not a copy. Live only; paper has no partials.
    if not state.paper_trading and _partial_remaining > 0 and _lkey:
        try:
            from execution import credit_remainder as _cr
            _cr.register(_cr.Remainder(
                key=_lkey, trade_id=record["trade_id"], record=record,
                short_symbol=short_contract.symbol, long_symbol=long_contract.symbol,
                short_strike=float(short_contract.strike),
                long_strike=float(long_contract.strike),
                side=signal.option_side, strategy=record["strategy"],
                requested=_req_contracts, remaining=_partial_remaining,
                stop_pct=(0.0 if (_is_tcs or _is_parc) else _stop_pct),
                window_end_et=_credit_window_end(signal)))
        except Exception as _rexc:                              # noqa: BLE001
            logger.error("[remainder] could not register the unfilled %d: %s",
                         _partial_remaining, _rexc)

    # v4.3: notify_leg_filled removed — the strategy no longer tracks a pair.
    # Each vertical is standalone; the roll detects open pairs independently.

    # v6.9 (AUDIT F6): the alert must describe THIS trade's exits. A TC.6 leg
    # has NO premium stop and NO nickel close — breach of the bound or 15:45,
    # nothing else — and advertising a stop here is a lie on the channel that
    # caught the last identity bug.
    _exit_desc = (f"exit=breach@{getattr(signal, 'underlying_stop', 0.0):.2f} or 15:45"
                  if _is_tcs else
                  f"exit=structure@{getattr(signal, 'underlying_stop', 0.0):.2f} | "
                  f"nickel=${CONDOR_NICKEL_CLOSE:.2f} | EOD.1 (size {sizing.rule})"
                  if _is_parc else
                  f"stop=${fill_credit * (1 + _stop_pct):.2f} ({_stop_pct:.0%}) | "
                  f"nickel=${CONDOR_NICKEL_CLOSE:.2f}")
    get_alert_manager()._send(
        f"\U0001F985 [{mode}] {INSTRUMENT} | {signal.setup_type} | "
        f"sell={short_contract.strike:.0f} buy={long_contract.strike:.0f} "
        f"x{contracts} credit=${fill_credit:.2f} | "
        f"{_exit_desc} | maxloss=${max_loss:.0f} | "
        f"{fmt_et_short()}"
    )

    logger.info(
        f"[{mode}] CONDOR LEG EXECUTED (tracked): {signal.setup_type} "
        f"short={short_contract.strike:.0f} long={long_contract.strike:.0f} "
        f"x{contracts} credit=${fill_credit:.2f} max_loss=${max_loss:.0f}"
    )


def _note_evaluation(name: str, ctx, signal) -> None:
    """r66 — record what this engine SAW and what it decided. Never decides.

    🔴 THE REJECTIONS ARE THE POINT. `fire_snapshot` captures the world when a
    trade FIRES, but a fired trade is a biased sample of what an engine looked
    at. Fitting needs both arms — taken AND declined — with the same derived
    vector on each.

    ⚠️ ON 2026-08-21 THE FLEET DECLINED EVERY SETUP ON EVERY BOX ALL SESSION
    AND COULD NOT SAY WHY. The signal journal held one event type all day;
    every other refusal was a debug line. This is the fix for that class.

    ⚠️ WRITTEN AFTER THE DECISION, ALWAYS. A note that could alter an outcome
    would make the record a participant in what it is measuring.
    """
    try:
        eng = (ctx or {}).get("derived_engines")
        if not eng:
            return
        w = None
        for e in eng:
            if getattr(e, "name", "") == "notes":
                w = e
                break
        if w is None:
            return
        # 🔴 r239 — CANONICALISE THE DISPATCH LABEL. `DISPATCH_ALIAS` has
        # existed since r147 and is applied by the plan board (plan.py:791,
        # 833) and by `gate_report` (:118) — and NOT here, which is the only
        # writer of `strategy_note`. So the ORB's fires were stamped "ORB"
        # (the `_safe_strategy` label) while its plan and gate rows used
        # "ORBStrategy", and the fit report saw TWO strategies: one with 78
        # fires and ZERO declines, one with zero fires and 4,260 declines.
        # Neither arm could ever be fittable, and the report said NOT READY
        # for both, for opposite reasons.
        # ⚠️ THE SAME MAP, NOT A SECOND ONE. `SweepForLeg2 -> SweepCreditSpread`
        # comes along with it, which is r160's ruling that the second-leg
        # window "is asked under the condor's authorization and writes under
        # its own name" — it was already true of the plan board and silently
        # untrue of the notes.
        from strategy.plan import DISPATCH_ALIAS as _DA
        w.writer.write(_DA.get(name, name), ctx, fired=signal is not None)
    except Exception:                                          # noqa: BLE001
        pass


def _plan_skip(name: str, reason: str, gate: str = "") -> None:
    """r146 — tell the plan board a strategy is NOT asked this tick. Wrapped;
    the board is a contributor and can never affect dispatch.

    r42 — `gate` is the ADMISSION GATE that refused it ("window",
    "catastrophic_cap", …), passed as its own field. The board keys the
    operator's say-it-once rule on it, and recovering a gate by parsing the
    reason sentence is how that rule would quietly stop working the first time
    someone reworded a message."""
    try:
        from strategy import plan as _plan_board
        _plan_board.skipped(name, reason, gate=gate)
    except Exception:                                          # noqa: BLE001
        pass


def _plan_skip_all(reason: str, gate: str = "") -> None:
    try:
        from strategy import plan as _plan_board
        _plan_board.skipped_all(reason, gate)
    except Exception:                                          # noqa: BLE001
        pass


def _plan_skip_management(reason: str) -> None:
    """r213 — the management plans are not being asked, and here is why.

    🔑 `CondorManagement`, `CreditRoll` and every `<Strategy>/manage` row are
    driven ONLY from the `has_open_position()` branch. On a flat box nothing
    called them and nothing named them, so the panel printed the bare default
    on every tick — operator: *"Not asked? why or Why not?"*
    """
    try:
        from strategy import plan as _plan_board
        _plan_board.skipped_management(reason)
    except Exception:                                          # noqa: BLE001
        pass


# ══ r40 — ADMISSION IS ASKED ONCE A TICK AND READ AT THE ONE FUNNEL ═══════
# Operator, 2026-09-17: *"I wondered if this entire convoluted process can live
# in one file that has to drop each gate within to greenlight a plan to pass
# trigger params to the strategy?"* r35 built that file. NOTHING READ IT.
#
# 🔑 WHY THE GATE LIVES IN `_safe_strategy` AND NOT AT SEVEN CALL SITES. Every
# entry dispatch in this module already funnels through it — ORB, runaway,
# sweep, TCS, both butterflies and the hunt — so one test covers all of them and
# THE CASCADE ORDER IS UNTOUCHED. r35's own note says the order is load-bearing;
# rewriting seven `if` blocks to consult a set would have been seven chances to
# reorder it by accident.
#
# ⚠️ IT FAILS OPEN, ON PURPOSE, IN BOTH DIRECTIONS.
#   · `_ADMITTED is None` — no admission was computed for this tick, so every
#     name passes and the dispatch behaves EXACTLY as it did before r40. Any
#     call path that does not set it is therefore unchanged rather than dead.
#   · a name the table does not carry passes — `IronCondorStrategy` is retired
#     as an entry (it is the condor's second leg) and management dispatches are
#     not admission's business. A table that silences an unknown name would
#     make ADDING a strategy a silent no-op, which is the failure r35's
#     `eligible_now` was written to end, arriving from the other side.
# A strategy that is REFUSED is never asked, and `_plan_board.asked()` is never
# reached — which is the whole point: there is no per-tick refusal to journal
# because there is no refusal. The plan did not run.
_ADMITTED = None                    # frozenset[str] | None — set per tick
_ADMISSION_ALIAS = {"ORB": "ORBStrategy"}   # dispatch label -> table key


def _set_admission(names) -> None:
    """Publish this tick's admitted set. `None` restores the pre-r40 behaviour."""
    global _ADMITTED
    _ADMITTED = None if names is None else frozenset(names)


_ADMISSION_UNREADABLE_SAID = False       # r293 (ADM.2)


def _admission_allows(name: str) -> bool:
    """May `name` be ASKED this tick? Unknown names and an unset tick pass."""
    if _ADMITTED is None:
        return True
    key = _ADMISSION_ALIAS.get(name, name)
    try:
        from execution import position_manager as _pmod
        if key not in _pmod.rules():
            return True                 # admission has no opinion about it
    except Exception as _aexc:                                 # noqa: BLE001
        # r293 (ADM.2) — FAIL CLOSED, AND SAY SO ONCE. This returned True ("the table is
        # unreadable - do not gate") with no line: an admission table that cannot be read
        # silently un-gated every strategy (audit 10-18 D1). The strict side is the safe
        # side (strategy/criteria.relaxed_active); a strategy that is not asked for one
        # tick costs a tick, a strategy asked outside its table costs a trade.
        global _ADMISSION_UNREADABLE_SAID
        if not _ADMISSION_UNREADABLE_SAID:
            _ADMISSION_UNREADABLE_SAID = True
            logger.warning("[admission] the rules table is UNREADABLE (%s: %s) - nothing is asked "
                           "until it reads (said once per process)", type(_aexc).__name__, _aexc)
        return False
    return key in _ADMITTED


def _safe_strategy(name: str, fn, ctx=None):
    """v4.9 — run ONE strategy evaluation in isolation.

    THE DEFECT (2026-07-30): the dispatch in attempt_new_entry is a bare cascade
    of `if signal is None:` blocks with NO exception handling between them.
    Butterfly is Priority 3; Iron Condor is Priority 4. When butterfly raised
    NameError on `_mult`, the exception went straight to the tick loop and EVERY
    strategy below it was skipped — condor was never asked. Proven on IWM: 161
    `_mult` raises and PLAN=0, while CVX and ORCL (MULT=0, butterfly declining
    cleanly at the GEX gate) built 3 and 4 condor plans on the same tape.

    The dispatcher could not tell "this strategy DECLINED" from "this strategy
    EXPLODED" — and those mean opposite things. A decline means try the next
    priority. An explosion meant abandon the tick and silently suppress every
    strategy below, announcing nothing.

    Returns None on failure so the cascade continues exactly as for a normal
    decline, and logs at ERROR naming the strategy: a raise is a defect and must
    never be quiet, but it must not take the rest of the tick with it.
    """
    # r40 — NOT ADMITTED THIS TICK: not asked, and nothing journalled.
    if not _admission_allows(name):
        return None
    # r303 (PSTATE.1) — DORMANT: never asked, and it writes nothing (strategy/plan_state.py). The operator,
    # 2026-10-19: "dormant plans should not write to the ledger, unless we are studying them as 'log only'".
    try:
        from strategy import plan_state as _ps
        if _ps.is_dormant(name):
            return None
    except Exception as _ps_exc:                                # noqa: BLE001
        logger.warning("[plans] state of %s unreadable (%s) - asked as before", name, _ps_exc)
    # r204 — RETIRED BY RULING: not asked, and the board says why (once).
    _ret = _retired_reason(name)
    if _ret:
        _plan_skip("SweepCreditSpread" if name == "SweepForLeg2" else name, _ret, gate="retired")
        return None
    try:
        sig = fn()
        # r146 — the plan board learns this strategy was ASKED. AFTER fn().
        try:
            from strategy import plan as _plan_board
            _plan_board.asked(name, sig)
        except Exception:                                      # noqa: BLE001
            pass
        # r66 — one note per evaluation, fired or not. ⚠️ AFTER fn(), so the
        # note can never influence what it records.
        if ctx is not None:
            _note_evaluation(name, ctx, sig)
        if sig is not None:
            # v4.6 — the fire clears the block. Reporting only; wrapped.
            try:
                from analysis.gate_report import get_gate_reporter
                _r = get_gate_reporter(INSTRUMENT)
                if _r is not None:
                    _r.fired(name)
            except Exception:                                  # noqa: BLE001
                pass
        return sig
    except Exception as exc:                       # noqa: BLE001
        logger.error("%s raised during dispatch — SKIPPED, continuing to the "
                     "next priority; other strategies unaffected. %s: %s",
                     name, type(exc).__name__, exc, exc_info=True)
        return None


def _official_print(df_1m, today=None):
    """r222 (ORP.1) — (high, low) of TODAY's five 1m bars 09:30-09:34, or None unless ALL FIVE are present.

    The official opening-range print. A range read off fewer than five bars is exactly
    the blind-open defect this exists to catch, so a partial set returns None."""
    try:
        if df_1m is None or getattr(df_1m, "empty", True):
            return None
        today = today or df_1m.index[-1].date()
        h0, m0 = RTH_OPEN_ET
        start = h0 * 60 + m0
        rows = [i for i, t in enumerate(df_1m.index)
                if t.date() == today and start <= (t.hour * 60 + t.minute) < start + 5]
        if len({df_1m.index[i].minute for i in rows}) != 5:
            return None
        win = df_1m.iloc[rows]
        hi, lo = float(win["high"].max()), float(win["low"].min())
        return (hi, lo) if hi > lo > 0 else None
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("official print unavailable: %s", exc)
        return None


def _verify_official_print(state, df_1m=None) -> str:
    """r222 (ORP.1) — check the engine's range against the official print, once it can be read.

    Returns what it did: '' (nothing yet / already settled today), 'verified', 'corrected',
    'differs-frozen' or 'unverifiable'. Never raises."""
    try:
        _now = now_et()
        _day = _now.strftime("%Y-%m-%d")
        if getattr(state, "_orb_print_day", "") == _day:
            return ""
        if not getattr(state, "orb_range_established_today", False) or (_now.hour, _now.minute) < (9, 36):
            return ""
        if df_1m is None:
            from data.market_data import fetch_candles as _fc
            df_1m = _fc(INSTRUMENT, "1m", 400)
        pr = _official_print(df_1m, _now.date())
        eng = get_orb_engine()
        d = eng.data
        if pr is None:
            if (_now.hour, _now.minute) >= (10, 30):
                state._orb_print_day = _day
                logger.warning("[orb-print] the five opening 1m bars never all arrived - the range %.2f-%.2f "
                               "is UNVERIFIED today", d.orb_low, d.orb_high)
                return "unverifiable"
            return ""
        hi, lo = pr
        if abs(hi - d.orb_high) < 0.005 and abs(lo - d.orb_low) < 0.005:
            state._orb_print_day = _day
            logger.info("[orb-print] verified: the range %.2f-%.2f is the official print (five 1m bars)", lo, hi)
            return "verified"
        _old = (d.orb_low, d.orb_high)
        ok, why = eng.correct_range(hi, lo, source="five 1m bars 09:30-09:34")
        state._orb_print_day = _day
        if ok:
            try:
                import json as _json
                from analysis import orb_engine as _oe
                _payload = _json.dumps({"status": "ESTABLISHED", "date": _day, "high": round(hi, 4), "low": round(lo, 4),
                               "width": round(hi - lo, 4), "fetched_at": _now.strftime("%Y-%m-%d %H:%M:%S ET"),
                               "symbol": INSTRUMENT, "source": "official print (five 1m bars), r222"}, indent=2)
                with open(_oe.ORB_RANGE_FILE, "w") as _f:      # serialised FIRST: a failed dump must not leave an empty file
                    _f.write(_payload)
            except Exception as _wexc:                         # noqa: BLE001
                logger.warning("[orb-print] corrected in the engine but orb_range.json was not rewritten: %s", _wexc)
            logger.warning("[orb-print] UNUSUAL: the frozen range %.2f-%.2f did not match the official print "
                           "%.2f-%.2f (a blind or partial open) - CORRECTED before any break", _old[0], _old[1], lo, hi)
            return "corrected"
        logger.warning("[orb-print] UNUSUAL: the frozen range %.2f-%.2f does not match the official print %.2f-%.2f "
                       "and was NOT corrected: %s", _old[0], _old[1], lo, hi, why)
        return "differs-frozen"
    except Exception as exc:                                   # noqa: BLE001
        logger.warning("[orb-print] check failed - the range is unverified this tick: %s", exc)
        return ""


def _opening_range(ctx: dict):
    """(orb_high, orb_low): THE ENGINE'S RANGE FIRST (r222 - the official print), else recomputed
    FROM THE TAPE, or (None, None).

    ⚠️ TCS.3 (2026-08-17) — THE 1m-ONLY VERSION WAS STRUCTURALLY DEAD, and the
    fleet proved it live. v6.7 read `ctx["df_1m"]`, which the cache caps at 60
    bars, while asserting "the bars do not go anywhere." They go off the LEFT
    EDGE of a rolling window: the 09:30-09:35 bars leave a 60-bar 1m frame at
    ~10:35 ET — 25 minutes BEFORE TCS_START_ET (11:00) — so the bound was
    (None, None) for every minute of the credit window, every session, on
    every box, and trend participation could never fire. Fleet-verified
    2026-08-17: `[tcs] no opening-range` on up to 290 of 290 evaluated ticks;
    on GLD/MU/SMH/TLT/GS/SPX/NFLX the vote and ADX gates passed essentially
    ALL morning and every evaluation died here. Its own sibling
    `_session_extremes` already stated the truth this function denied: "each
    is a rolling window and neither is guaranteed to reach 09:30."

    PRIMARY SOURCE IS NOW df_5m. The old "a 5m frame cannot resolve a
    5-minute window" was false for this repo's constants:
    ORB_WINDOW_MINUTES=5 and 5m bars align to :30, so TODAY'S 09:30 bar IS
    the opening range, exactly — and the 5m frame holds it all session on
    every box (RTH-only tape spans the day with margin; SPX's 24h tape
    reaches back ~8.3h, keeping 09:30 in-frame past the close). The 1m
    window remains as the early-session supplement (before today's first 5m
    bar prints) and as the general path for any ORB_WINDOW_MINUTES not
    divisible by 5. Both paths filter to TODAY — an RTH-only 5m frame
    carries ~1.3 sessions, so yesterday's 09:30 bar is usually present too
    and must never become today's bound.

    v6.7's reasons for NOT reading the ORB engine all stand — restart-proof,
    available past the cutoff, one definition. Only the frame was wrong.
    """
    try:                                                       # r222: everything refers to the official print
        _oh, _ol = ctx.get("orb_high"), ctx.get("orb_low")
        if _oh and _ol and float(_oh) > float(_ol) > 0:
            return float(_oh), float(_ol)
    except Exception:                                          # noqa: BLE001
        pass
    try:
        h0, m0 = RTH_OPEN_ET
        start = h0 * 60 + m0
        end = start + ORB_WINDOW_MINUTES              # exclusive
        # ── 5m primary (TCS.3): today's aligned bars, available all day ──
        if ORB_WINDOW_MINUTES % 5 == 0:
            df5 = ctx.get("df_5m")
            if df5 is not None and not getattr(df5, "empty", True):
                today = df5.index[-1].date()
                rows = [i for i, t in enumerate(df5.index)
                        if t.date() == today
                        and start <= (t.hour * 60 + t.minute) < end]
                if rows:
                    win = df5.iloc[rows]
                    return (float(win["high"].max()),
                            float(win["low"].min()))
        # ── 1m supplement: pre-09:35 partial window / non-5m windows ─────
        df = ctx.get("df_1m")
        if df is None or getattr(df, "empty", True):
            return None, None
        today1 = df.index[-1].date()
        rows = [i for i, t in enumerate(df.index)
                if t.date() == today1
                and start <= (t.hour * 60 + t.minute) < end]
        if not rows:
            return None, None
        win = df.iloc[rows]
        return float(win["high"].max()), float(win["low"].min())
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("opening range unavailable: %s", exc)
        return None, None


def _session_extremes(ctx: dict):
    """(session_high, session_low) from the widest tape available, or (None, None).

    PF.5's third strike filter: a level price has ALREADY TRADED THROUGH today
    is a level the market has proven it can reach, so a short strike must sit
    beyond it. This is the input.

    Takes the max across BOTH frames rather than trusting one: each is a rolling
    window and neither is guaranteed to reach 09:30. A window that starts late
    UNDERSTATES the extreme, which makes the filter LOOSER, not tighter — so the
    failure direction is a missed rejection rather than a wrong one. Returning
    None on absence is deliberate: the strategy logs it as a plumbing fault
    instead of silently trading with the filter switched off.
    """
    hi, lo = None, None
    try:
        for key in ("df_1m", "df_5m"):
            df = ctx.get(key)
            if df is None or getattr(df, "empty", True):
                continue
            h = float(df["high"].max())
            l = float(df["low"].min())
            hi = h if hi is None else max(hi, h)
            lo = l if lo is None else min(lo, l)
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("session extremes unavailable: %s", exc)
        return None, None
    return hi, lo


def _open_credit_legs() -> list:
    """The open credit verticals themselves — Rule 4 needs leg 1's TRIGGER,
    not just its side. `condor_trigger_source` is stamped at fill (v4.2)."""
    try:
        from database.trade_logger import get_trade_logger
        return [t for t in get_trade_logger().get_open_trades()
                if t.get("is_condor_leg") and t.get("status") == "open"
                and t.get("strategy") != "OpeningRangeCreditSpread"]   # r204: ORCS pairs with nothing
    except Exception:                                          # noqa: BLE001
        return []


def _open_credit_sides() -> set:
    """Which credit-vertical sides ('call'/'put') are open right now.

    v4.3 CONDOR REMODEL. `is_condor_leg=1` is now stamped on ALL four trigger
    types (sweep, trend_orb, 1h_fork, 1d_fork) so any complementary pair is
    detectable here. The roll finds them the same way.
    """
    try:
        from database.trade_logger import get_trade_logger
        return {t.get("option_side")
                for t in get_trade_logger().get_open_trades()
                if t.get("is_condor_leg") and t.get("status") == "open"
                and t.get("strategy") != "OpeningRangeCreditSpread"}   # r204: ORCS pairs with nothing
    except Exception:                                          # noqa: BLE001
        return set()


# ═══ RULE 4 — THE TRIGGER PAIRING TABLE ═══════════════════════════════════
# 🔴 OPERATOR'S RULING, 2026-08-25. Which trigger opened LEG 1 constrains what
# may complete it. Until now the gate knew SIDES ONLY, so any trigger could
# pair with any other.
#
#   TREND CS first  → ONLY a SWEEP completes it. *"If a trend credit spread is
#                     the first leg, the only other permissible leg would be a
#                     sweep, and for a sweep there has to be a rejection or we
#                     don't sell it."*
#   SWEEP first     → a FORK TINE completes it, *"geometrically placed on the
#                     right side."*
#   FORK TINE first → *"Another (opposite) fork tine (upper, lower) or sweep
#                     will work."*
#
# 🔴 AND A TREND CS MAY NEVER FOLLOW ANYTHING. Operator, on a trend CS after a
# sweep: *"that move invalidates the whole premise of a 'trend' credit
# spread."* A sweep asserts a level REJECTED — a reversal; a trend CS asserts a
# trend RUNNING in that same tape. Both cannot be true about one session, so it
# is a premise conflict, not a slot conflict. The trend CS is therefore a
# LEG-1-ONLY trigger.
#
# ⚠️ REJECTION IS REQUIRED OF THE SWEEP CLASS, NOT OF FORKS. Operator: *"a
# qualifying PDH/PDL or other named level, but as a SWEEP — fork does not need
# a rejection, it is assumed to be stable if it's present."* A named level is
# only a level once price has REJECTED it on a CLOSE; a fork tine is trusted by
# its presence. `sweep_credit_spread` already encodes exactly this — a pool
# must be NAMED and must have RECLAIMED, "a wick through a level is a wick."
#
# ⚠️ FAIL CLOSED. Only the pairs named above are permitted. An unlisted
# combination is refused and SAID OUT LOUD, never silently allowed — r124's
# lesson, where 406 consecutive silent refusals cost five queries to explain.
_TREND_TRIGGERS = ("trend_orb",)
_SWEEP_TRIGGERS = ("sweep_reversal",)
_FORK_TRIGGERS  = ("1h_fork", "1d_fork")

# 🔴 r160 — LEG TWO IS UNIVERSALLY A SWEEP. Operator, 2026-08-27: *"the fork
# tine is acceptable for the first leg, but the second one must universally be
# a sweep because only a rejection at the site of the second vertical spread
# would inspire enough confidence to sell credit there."* Every row below now
# reads the same. The table is kept (not replaced by a constant) so an unknown
# leg-one class still FAILS CLOSED, and so the 08-25 shape is visible in the
# history: trend->sweep, sweep->fork, fork->fork|sweep.
_PAIRING_TABLE = {
    # leg-1 trigger class : the classes permitted to COMPLETE it
    "trend": ("sweep",),
    "sweep": ("sweep",),
    "fork":  ("sweep",),
}


def _trigger_class(source: str) -> str:
    """Map a condor_trigger_source to its pairing class, or '' if unknown."""
    if source in _TREND_TRIGGERS:
        return "trend"
    if source in _SWEEP_TRIGGERS:
        return "sweep"
    if source in _FORK_TRIGGERS:
        return "fork"
    return ""


def _sweep_has_rejection(ctx: dict) -> tuple:
    """(ok, reason) — is there a LIVE, close-based rejection right now?

    🔴 OPERATOR: *"for a sweep there has to be a REJECTION or we don't sell
    it."* And separately: *"a wick can be a pierce. But it takes a CLOSE to log
    a rejection."*

    ⚠️ THIS IS THE r127 / CVX FINDING AT THE PAIRING GATE. `reclaimed` is a
    LATCHED FLAG on a persisted pool object — once true it stays true for
    hours. A leg-2 sweep admitted on that flag can fire long after any actual
    rejection, which is precisely the loop observed on CVX.
    ⚠️ SO THREE CONDITIONS, NOT ONE: reclaimed (a close returned inside),
    NOT invalidated (price has not since accepted through — that is a
    BREAKOUT, and selling a boundary that already gave way is the worst
    version of this trade), and YOUNG measured from `reclaim_bar_index`, not
    from the sweep bar.
    ⚠️ FAILS CLOSED. No sweep object, or an unreadable one, is NOT a rejection.
    """
    sweep = (ctx or {}).get("sweep")
    if sweep is None:
        return False, "no sweep state available — that is not a rejection"
    try:
        if not getattr(sweep, "reclaimed", False):
            return False, ("the level was pierced but no CLOSE returned inside "
                           "it — a wick is not a rejection")
        if getattr(sweep, "invalidated", False):
            return False, ("reclaimed then INVALIDATED — price accepted "
                           "through, so this is a breakout, not a rejection")
        # 🔴 `bars_ago`, NOT `bars_since_reclaim`/`reclaim_age_bars` — NEITHER
        # OF WHICH EXISTS on LiquiditySweep. I invented both names, and because
        # `getattr` with a default NEVER RAISES, the age read -1 on every real
        # sweep and this gate refused EVERY sweep pairing with a plausible
        # reason. That is worse than the AttributeError that hid the fork: at
        # least that one crashed. This one just quietly said no forever.
        # SWP.10 already made `bars_ago` count from the RECLAIM bar rather than
        # the sweep bar, which is exactly the semantics this gate wants.
        bars = int(getattr(sweep, "bars_ago", -1) or -1)
        if bars < 0:
            return False, ("cannot measure age from the reclaim bar — an "
                           "unmeasurable rejection is not a rejection")
        if bars > _SWEEP_REJECTION_MAX_BARS:
            return False, (f"the rejection is {bars} bars old (max "
                           f"{_SWEEP_REJECTION_MAX_BARS}) — a latched flag, "
                           f"not a live event")
        return True, f"live rejection, {bars} bar(s) since the reclaim close"
    except Exception as exc:                                   # noqa: BLE001
        return False, f"sweep state unreadable ({exc}) — not a rejection"


# ⟨PRIOR⟩ — stated, not fitted. The plan tables will say what it should be.
_SWEEP_REJECTION_MAX_BARS = 5


def _pairing_allowed(leg1_source: str, leg2_source: str, ctx: dict = None) -> tuple:
    """(allowed, reason). Fails CLOSED on an unknown trigger on either side."""
    c1, c2 = _trigger_class(leg1_source), _trigger_class(leg2_source)
    if not c1 or not c2:
        return False, (f"unknown trigger class (leg1 {leg1_source or '?'} → "
                       f"leg2 {leg2_source or '?'}); refusing rather than "
                       f"guessing at a pairing")
    if c2 == "trend":
        return False, ("a TREND credit spread can only ever be the FIRST leg — "
                       "a sweep or a tine asserts a level held, a trend spread "
                       "asserts a trend running, and completing one with the "
                       "other invalidates the trend spread's own premise")
    ok = c2 in _PAIRING_TABLE.get(c1, ())
    if not ok:
        return False, (f"a {c1.upper()} first leg cannot be completed by a "
                       f"{c2.upper()} trigger; permitted: "
                       f"{', '.join(_PAIRING_TABLE.get(c1, ())) or 'nothing'}")
    # 🔴 A SWEEP COMPLETING ANYTHING NEEDS A LIVE REJECTION. The class check
    # says the TRIGGER TYPE is permitted; it says nothing about whether a
    # rejection actually happened. Operator: *"for a sweep there has to be a
    # rejection or we don't sell it."*
    # ⚠️ A FORK NEEDS NO SUCH TEST — *"fork does not need a rejection, it is
    # assumed to be stable if it's present."* The requirement rides on the
    # SWEEP CLASS, which includes a named level (PDH/PDL) traded AS a sweep.
    if c2 == "sweep":
        ok_r, why_r = _sweep_has_rejection(ctx or {})
        if not ok_r:
            return False, (f"{c1.upper()} leg 1 may be completed by a sweep, "
                           f"but {why_r}")
        return True, f"{c1.upper()} leg 1 completed by SWEEP — {why_r}"
    return True, f"{c1.upper()} leg 1 completed by {c2.upper()} — permitted"


def _can_open_credit_spread(side: str,
                             new_signal=None,
                             current_price: float = 0.0,
                             ctx: dict = None) -> bool:
    """Type gate (Rules 1+3+4) AND geometry gate (no inversion).

    Rule 1: max 2 concurrent positions.
    Rule 3: new spread must be on the COMPLEMENTARY side (never two calls,
            never two puts).
    Rule 4: the TRIGGER PAIRING TABLE above — which trigger opened leg 1
            constrains which may complete it. Order-dependent.
    Geometry: the pair must satisfy  short_put < price < short_call.
              A second spread whose short strike lands on the wrong side of
              current price — or crosses the existing short strike — produces
              an inverted condor that is born tested. Prevent it here so no
              trigger can accidentally form one.

    The geometry check only runs when `new_signal` and `current_price` are
    supplied (second-leg context). For a first leg those args are absent and
    the call falls through to True after the type check.
    """
    sides = _open_credit_sides()
    # ── 🔴 r124 — SAY WHICH STATE WE ARE IN, AND SAY IT AT INFO ────────────
    # These two refusals were SILENT, and on 2026-08-25 that cost five queries
    # to explain one afternoon: CRM logged CondorLeg2nd signalling on 406
    # CONSECUTIVE TICKS with nothing in any log, because a PUT was open and the
    # second-leg signal was also a PUT. Rule 3 refused all 406 without a word.
    # The condor's pairing refusal is the most consequential decision in this
    # path — it is the difference between a lone vertical and a structure — and
    # it was the only one that left no trace.
    # ⚠️ PHRASED THE WAY THE OPERATOR ASKED FOR IT, 2026-08-25: state what is
    # OPEN and what that BLOCKS, rather than naming a rule number. "PCS open —
    # only a CCS can pair; another PCS is blocked" is readable at 2am from a
    # phone; "Rule 3" requires opening this file.
    # ⚠️ BOTH-SIDES FIRST. `side in sides` is true in the complete-structure
    # case too, so testing it first reports "PCS open" on a finished condor —
    # a true sentence that describes the wrong situation.
    if len(sides) >= 2:
        logger.info("Credit pairing BLOCKED: both sides already open "
                    "(PCS + CCS) — the structure is complete, no third leg")
        return False
    # ── 🔴 RULE 4 — THE TRIGGER PAIRING TABLE (2026-08-25) ─────────────────
    # Runs BEFORE Rule 3's side check only in the sense that it is independent
    # of it: a complementary side is necessary but no longer sufficient.
    if sides and new_signal is not None:
        _legs = _open_credit_legs()
        _leg1 = _legs[0] if _legs else {}
        _src1 = _leg1.get("condor_trigger_source") or ""
        _src2 = getattr(new_signal, "condor_trigger_source", "") or ""
        _ok4, _why4 = _pairing_allowed(_src1, _src2, ctx=ctx or {})
        if not _ok4:
            logger.info("Credit pairing BLOCKED by Rule 4: %s", _why4)
            return False
        logger.info("Credit pairing Rule 4 OK: %s", _why4)

    if side in sides:
        _open = "PCS" if "put" in sides else "CCS"
        _want = "PCS" if side == "put" else "CCS"
        logger.info("Credit pairing BLOCKED: %s open — only a %s can pair with "
                    "it; another %s is refused (never two of a side)",
                    _open, "CCS" if _open == "PCS" else "PCS", _want)
        return False

    # First leg (nothing open yet) — type check is all we need.
    if not sides or new_signal is None or current_price <= 0:
        return True

    # ── Second-leg geometry gate ──────────────────────────────────────────
    # Confirm: short_put < current_price < short_call.
    # Pull the existing open spread's short strike from the DB.
    try:
        from database.trade_logger import get_trade_logger as _gtl
        open_legs = [t for t in _gtl().get_open_trades()
                     if t.get("is_condor_leg") and t.get("status") == "open"]
        if not open_legs:
            return True
        ex = open_legs[0]
        ex_short = float(ex.get("short_strike") or 0.0)
        ex_side  = ex.get("option_side", "")

        # New spread's short strike from the signal
        if side == "call":
            _sc = getattr(new_signal, "short_call_contract", None)
            new_short = float(getattr(_sc, "strike", 0.0) or 0.0) if _sc else 0.0
        else:
            _sp = getattr(new_signal, "short_put_contract", None)
            new_short = float(getattr(_sp, "strike", 0.0) or 0.0) if _sp else 0.0

        if ex_short <= 0 or new_short <= 0:
            return True   # can't verify — each spread already passed its own gates

        # Assign call/put short strikes for the combined check
        short_call = new_short if side == "call" else ex_short
        short_put  = new_short if side == "put"  else ex_short

        if short_put >= current_price:
            logger.info(
                "Condor geometry BLOCKED: short_put %.2f >= price %.2f "
                "(put side would open tested — inversion prevented)",
                short_put, current_price)
            return False
        if short_call <= current_price:
            logger.info(
                "Condor geometry BLOCKED: short_call %.2f <= price %.2f "
                "(call side would open tested — inversion prevented)",
                short_call, current_price)
            return False
        if short_put >= short_call:
            logger.info(
                "Condor geometry BLOCKED: short_put %.2f >= short_call %.2f "
                "(crossed strikes — inverted condor prevented)",
                short_put, short_call)
            return False
        return True
    except Exception:                                          # noqa: BLE001
        return True   # fail open — type gate already passed


def _condor_rails(ctx: dict):
    """Pitchfork rails for the condor, or None. Never raises.

    🔴 1h BY OPERATOR RULING, 2026-08-22 — "it has to be the one hour or not at
    all." A DAILY fork demands an excursion from one anchor to the next that a
    single session rarely meets; gating on it produces a permanent no-trade
    rather than a guardrail.

    ⚠️ THIS REPLACES THE PRIOR RULING, which read: "DAILY by operator ruling —
    it's a guardrail, not the road. A daily fork is invalidated only by DAILY
    closes, so an intraday session cannot move the rail a spread was sold
    against." That reasoning is sound and it is SUPERSEDED — stability is worth
    nothing if the anchor is never constructible. Recorded rather than deleted
    so the next reader knows a decision changed, not that a comment rotted.

    ⚠️ AVAILABILITY SETTLES IT INDEPENDENTLY OF THE ARGUMENT. On 2026-08-21 the
    1d frame was ABSENT FROM THE WAREHOUSE ENTIRELY (present Wed 30, Thu 16,
    Fri 0) while 1h carried 240 objects. An anchor that exists beats one that is
    theoretically more stable.

    None still means NO CONDOR, and that remains correct and expected: if the
    fork cannot be derived there is nothing to anchor to. Operator: that is the
    only legitimate condor no-go — expected behaviour, not a defect.
    """
    try:
        from analysis.pitchfork_observer import rails_for
        return rails_for(ctx, INSTRUMENT, CONDOR_PF_TIMEFRAME)
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("condor rails unavailable: %s", exc)
        return None


def _afternoon_debit_blocked(strategy_or_signal, now) -> bool:
    """True when a LONG-PREMIUM DIRECTIONAL entry is refused by the cutoff.

    Operator, 2026-08-13: *"The only other Long that can fire is either part of
    a butterfly or an iron condor vertical spread from 11 o'clock onwards."*
    Cutoff extended to **11:30** on 2026-08-20 to resolve a contradiction: ORB
    armed until 11:00 while RunawayContinuation - which fires on ORB's OWN
    state - ran to 11:30, so the engine stopped producing the state half an
    hour before the trade depending on it stopped firing.

    ⚠️ KEYED ON STRUCTURE, NOT ON A NAME LIST, AND THAT CHANGE FIXED A LIVE
    HOLE. v3 held {"ORBStrategy", "ContinuationStrategy", "SweepReversal"};
    by 2026-08-20 **two of those three had been deleted** while the new
    long-debit strategy - RunawayContinuation - was NOT in the list and would
    have been **silently EXEMPT from the cutoff**. An allow-list of names rots
    every time a strategy is added or removed, **and it rots permissively.**

    A strategy declares `STRUCTURE`; this decides from that:
      long_debit  pays premium, directional        -> blocked after the cutoff
      vertical    credit spread or condor leg      -> always permitted
      butterfly   defined-risk debit               -> the named exception, and
                  it covers BOTH the GEX pin butterfly and the synthetic
                  butterfly from an aggressive condor roll - the latter being a
                  MANAGEMENT step on a live position, not a new entry

    ⚠️ UNKNOWN IS TREATED AS `long_debit` - FAIL CLOSED. A strategy that forgets
    to declare gets the most restrictive reading, which is the opposite of the
    v3 behaviour that let an undeclared strategy through.
    """
    if not DEBIT_BLOCK_ACTIVE:
        return False
    struct = None
    if isinstance(strategy_or_signal, str):
        struct = _STRUCTURE_BY_NAME.get(strategy_or_signal)
    else:
        struct = getattr(strategy_or_signal, "structure", None) or \
                 _STRUCTURE_BY_NAME.get(
                     getattr(strategy_or_signal, "strategy_name", ""))
    if struct is None:
        struct = "long_debit"          # fail closed
    if struct not in DEBIT_BLOCKED_STRUCTURES:
        return False
    return (now.hour, now.minute) >= tuple(DEBIT_DIRECTIONAL_CUTOFF_ET)


# What each strategy BUILDS. The cutoff reads this, not a name allow-list.
# ⚠️ A NEW STRATEGY MISSING FROM HERE IS TREATED AS `long_debit` AND BLOCKED
# after the cutoff - deliberately the restrictive default.
_STRUCTURE_BY_NAME = {
    "ORBStrategy":          "long_debit",
    "ORB":                  "long_debit",
    "RunawayContinuation":  "long_debit",
    "SweepCreditSpread":    "vertical",
    "OpeningRangeCreditSpread": "vertical",     # r204 (ORCS)
    "GEXPinButterfly":      "butterfly",
    "ATPButterfly":         "butterfly",
    "IronCondorStrategy":   "vertical",
    # r51 — a long option, so the afternoon debit cutoff governs it like the ORB
    "Breakout":             "long_debit",
    # r72 — VOLT buys a single option. Its window closes at 11:30 so the
    # afternoon cutoff cannot bite, but it is DECLARED rather than defaulted:
    # this map's own warning is that a missing name is silently long_debit, and
    # relying on the fallback to be right is how it stops being right.
    "VOLT":                 "long_debit",
    # r288 (PARK.1) — a long single option bought at 11:01; declared, not defaulted.
    "PARK":                 "long_debit",
    # OTV5 r46 (PARC.1) — a credit vertical sold at 11:01; declared, not defaulted.
    "PARC":                 "vertical",
}


def _condor_leg_open_without_plan() -> bool:
    """True if a condor leg is OPEN but no in-memory plan owns it.

    ⚠️ AUDIT F5 — THE PLAN IS PROCESS-LOCAL AND A RESTART ORPHANS THE
    STRUCTURE. `IronCondorStrategy._plan` lives in memory only. On a restart
    with leg 1 filled and leg 2 pending, the plan is GONE — and the plan is the
    only thing that knew leg 2's TRIGGER PRICE, which is in no column, so the
    structure can never complete. **A restart happens on every bake.**

    THE ORPHANED LEG ITSELF IS FINE: `_condor_sibling_open()` reads the DB,
    returns False, and CND.7 correctly manages it as a STANDALONE vertical with
    the ratchet it earns. That part needs no fix.

    WHAT BREAKS IS DEFERRAL. `has_active_plan` goes False, so **TC.6 stops
    standing down and can open a SECOND credit spread on the same underlying**
    while the orphan is still open — two credit verticals on one symbol, which
    nothing sizes or manages as a pair.

    So the symbol stays OCCUPIED as long as a condor leg is open, derived from
    the same persisted fields `_condor_sibling_open` already trusts
    (`is_condor_leg`, `status='open'`) rather than from a plan that did not
    survive. FAILS CLOSED: on any error, treat the symbol as occupied — a
    missed trade costs less than an unmanaged pair.
    """
    try:
        from database.trade_logger import get_trade_logger
        n = sum(1 for t in get_trade_logger().get_open_trades()
                if t.get("is_condor_leg") and t.get("symbol") == INSTRUMENT)
        # A2.2 - the orphan ANNOUNCEMENT no longer lives here: this function is
        # only called inside attempt_new_entry, which only runs when
        # has_open_position() is False - and that falls back to the SAME
        # get_open_trades(). With a leg open this site is unreachable; when
        # reached, n is by construction 0. The warning now fires from the
        # manage branch, where an open leg can actually be seen. This checker
        # stays, side-effect-free, as belt-and-braces on the TC.6 dispatch.
        return n > 0
    except Exception as exc:                                   # noqa: BLE001
        logger.warning("[F5] could not check for an orphaned condor leg (%s) - "
                       "treating the symbol as OCCUPIED", exc)
        return True


def _l1_scores(ctx):
    """The RAW Layer-1 score vector for the axis decomposition, or None.

    ⚠️ P0.3 / AX.3 (2026-08-17). `ctx["l1"]` is the scorer result set at
    sites need no plumbing and a missing/blank L1 simply omits the axes rather
    than raising inside a journal write.
    """
    try:
        r = (ctx or {}).get("l1")
        sc = getattr(r, "scores", None)
        return sc if isinstance(sc, dict) and sc else None
    except Exception:                                          # noqa: BLE001
        return None


def _orb_offer_working() -> bool:
    """True when an ORB standing offer is live at the broker right now.

    ⚠️ FAILS CLOSED. An unreadable offer store returns True — better to skip
    one setup than to place a second order against one we cannot see.
    """
    try:
        from execution import resting_orders as _ro
        from utils.time_utils import now_et
        return bool(_ro.working(now_et().date().isoformat(), "ORBStrategy"))
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("offer check failed (%s) — treating as WORKING and "
                       "skipping ORB this tick", exc)
        return True


def _orb_release_due(state) -> bool:
    """r61 (ORB.10) — True when no ORB trade can own an ORB confirmation: ORBStrategy is not active
    (plan_state; retired since OTV4TEST r187), no ORB standing offer is working and no ORB position is
    open. Then the engine is released from OPEN_* (orb_engine.release_unowned) instead of holding it to
    15:40, which blinded RunawayContinuation to the opposite break. Fails CLOSED (False): an unreadable
    offer store or book keeps today's behaviour."""
    try:
        from strategy import plan_state as _ps
        if _ps.state("ORBStrategy") == _ps.ACTIVE:
            return False
        if _orb_offer_working():
            return False
        _recs = get_position_manager(getattr(state, "paper_trading", True)).get_open_records()
        return not any("ORB" in str(r.get("strategy") or "") for r in (_recs or []))
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[orb] release check unreadable (%s) - the engine is not released this tick", exc)
        return False


def _supervise_offers(ctx: dict, state: BotState) -> None:
    """Poll every standing ORB offer, adopt fills, fire the cancel triggers.

    🔑 CALLED FROM BOTH BRANCHES OF THE LOOP, AND THAT IS THE WHOLE POINT. An
    offer that has not filled has NO trade record, so `has_open_position()` is
    False and the manage branch never runs for it. Supervising only from the
    manage branch would leave every unfilled offer watched by nothing — the
    orphan the module exists to prevent, reintroduced one level up.

    ⚠️ NEVER RAISES INTO THE LOOP. A supervision failure must not stop the bot
    from trading or managing; it logs and the next tick tries again, with the
    10-minute broker reconcile underneath as the backstop.
    """
    try:
        from execution import resting_orders as _ro
        _df = ctx.get("df_1m")
        _last = None
        if _df is not None and len(_df) >= 2:
            from utils.time_utils import closed_pos as _closed_pos     # r44 (BAR.1): by time, was iloc[-2]
            _last = float(_df.iloc[_closed_pos(_df, now_et())]["close"])
        _ro.supervise(
            price=float(ctx.get("price") or 0.0),
            last_1m_close=_last,
            eod=is_hard_close_time(),
            paper=state.paper_trading,
            adopt=lambda row, n: _ro.adopt_fill(row, n,
                                                paper=state.paper_trading))
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("offer supervision skipped this tick: %s", exc)



_CHAIN_MISS_SAID: set = set()          # r301 (LOG.1): the rehearsal's chain miss, once per ET date per process


def _chain_miss_say(rehearsing: bool) -> str:
    """r301 (LOG.1) — how the 'no chain this tick' line is said. INSIDE RTH: WARNING every tick, as
    since v1 (a missing chain in the session is a real condition). In the REHEARSAL (outside RTH)
    the chain has no marks by nature, so it is said once per ET date per process at INFO and then
    not at all; the plan rows (gate no_chain) still record every tick. Measured 2026-10-12..16:
    2,428 of these WARNINGs, all after the bell. Returns the level used ("warning"/"info"/"")."""
    if not rehearsing:
        logger.warning("Could not fetch options chain — skipping entry attempt")
        return "warning"
    try:
        from utils.time_utils import now_et
        key = now_et().strftime("%Y-%m-%d")
    except Exception:                                           # noqa: BLE001
        key = "?"
    if key in _CHAIN_MISS_SAID:
        return ""
    _CHAIN_MISS_SAID.add(key)
    logger.info("[rehearsal] no options chain outside RTH (no live marks after the bell) — the rehearsal "
                "runs without one; said once per day, the plan rows carry every tick (gate no_chain)")
    return "info"

def attempt_new_entry(ctx: dict, ms: MarketState, state: BotState):
    """Try to generate and execute a trade signal."""
    # ⚠️ r40 — CLEARED FIRST, BEFORE ANY EARLY RETURN CAN SKIP IT. `_ADMITTED`
    # is module state that outlives the call. Every gate below returns, and a
    # return that left LAST tick's admitted set in place would gate this tick
    # on a window that has since closed — the stale-snapshot class this file
    # already carries a warning about at the ORB seam (r207). `None` is the
    # pre-r40 behaviour, so the cleared state is also the safe state.
    _set_admission(None)
    _observe.clear()                    # r254 (OBS.1): same rule - cleared before any return
    session  = get_session_guard()
    risk_mgr = get_risk_manager()
    entry_eng = get_entry_engine(state.paper_trading)

    # ── Session gate ──────────────────────────────────────────────────────────
    # Daily catastrophic loss cap: while the day's REALIZED net P&L is down by
    # the limit, take no new trades (open positions keep being managed to exit).
    # r162: it re-opens once closes bring the loss back under the limit.
    # r178 (CAP.2): the two butterflies are exempt. The operator, 2026-09-30:
    # "Allow both flies to fire even if we've hit the cap." So this no longer
    # returns here; the capped branch below (after admission) asks ONLY the
    # butterfly path and returns before any other strategy.
    _cap_hit = risk_mgr.is_halted()
    _adm_ok = False
    if _cap_hit:
        logger.info("Entry blocked: DAILY CATASTROPHIC LOSS CAP reached — no new entries "
                    "until the realized loss is back under the limit (the two "
                    "butterflies are exempt and keep their own window and quota).")

    # r102 — OUTSIDE RTH THIS IS A REHEARSAL, NOT A TRADING PASS. can_enter
    # short-circuited on the RTH gate and returned at DEBUG, so r101's
    # outside-RTH dispatch stopped one call before any strategy ran: measured
    # on all 15 boxes 2026-08-24 16:53, decided=0 chain=0.
    _rehearsing = not is_rth()
    can_enter, reason = session.can_enter(ctx["macro"], rehearsal=_rehearsing)
    if not can_enter:
        # ⚠️ A REHEARSAL THAT DECLINES SILENTLY IS THE FAILURE IT EXISTS TO
        # CATCH. Every skip on this path was DEBUG — that is why a pass that
        # proved nothing looked identical to a pass that proved everything.
        (logger.info if _rehearsing else logger.debug)(
            "%sEntry blocked: %s", "[rehearsal] " if _rehearsing else "", reason)
        _plan_skip_all(f"entry blocked: {reason}", gate="entry_blocked")
        return
    if _rehearsing:
        logger.info("[rehearsal] gates PASS (%s) — running the full dispatch; "
                    "the order choke points refuse outside RTH", reason)

    # The asymmetry is deliberate and is the other half of the hold above.
    # HOLDING a label on a stale tick is declining to act on unknown information.
    # OPENING a position is a DECISION — taking on new risk against a
    # classification the engine currently cannot confirm — which is exactly what
    # the rule prohibits. The costs are asymmetric too: a missed entry costs
    # opportunity, and with 29 boxes there is plenty of that; a wrong entry costs
    # capital.
    # Open positions are unaffected: they keep being managed to exit by every
    # price-based stop.
    # v5.4 — ORB IS EXEMPT, and this is a RESTORATION rather than a new licence.
    # v5.0's gate sat ABOVE the dispatch, so it returned before
    # this purpose, unreachable on any stale tick. Measured 2026-08-04: the
    # block ran 09:35:01 → 09:39-09:41 ET on ALL 15 boxes, i.e. the first four
    # to six minutes of ORB's own entry window, every session since v5.0.
    # WHY ORB AND NOTHING ELSE. v5.0's rule is "opening a position is a DECISION
    # against a classification the engine cannot confirm". ORB reads no
    # classification: break, retest, close back outside — price structure only,
    # graded on liquidity alone since setup_scorer v1.4. There is no label for a
    # stale label to invalidate. Continuation, condor, butterfly and sweep all
    # genuinely condition on the label and stay blocked.
    # dt_max=90s); the feed has its own guard, latch and pager (market_data v3.3
    # / blindness_latch). A confirmed ORB break on a stale book still has fresh
    # price — which is the whole reason this exemption is safe and why it must
    # NOT be widened to "ignore stale".
    _orb_ctx = ctx.get("orb")
    # the constant itself. It was hardcoded True, so it never contributed a
    # term; exemption has always meant "the ORB engine is in a confirmed OPEN
    # state", which is what remains.
    _orb_exempt = bool(
        _orb_ctx is not None
        and getattr(_orb_ctx, "state", None) in (ORBState.OPEN_LONG,
                                                 ORBState.OPEN_SHORT))
    # v4.0: the stale-book entry guard is gone with the book. There is no
    # integrator to go stale, so this can never fire. ORB was already exempt
    # through v3's stale-book stalls and is the one strategy with a positive
    # record.


    # ══ r40 — ADMISSION, ASKED ONCE, FROM THE ONE TABLE ══════════════════════
    # r35 moved every entry gate into `execution/position_manager.py` and then
    # left it INERT: *"NOTHING IS WIRED YET — attempt_new_entry still runs the
    # old gates."* This is the wiring. `eligible_now()` answers which strategies
    # MAY BE ASKED this tick; `_safe_strategy` refuses the rest at the funnel.
    #
    # 🔑 IT ANSWERS, IT DOES NOT DRIVE. The list comes back and THIS file does
    # the asking, in the same cascade order as before. The position manager
    # never reaches into `strategy/` — that is what keeps the one-way flow.
    #
    # ⚠️ THE UNIVERSALS ABOVE ARE STILL THE AUTHORITY, AND THAT IS STATED
    # RATHER THAN HIDDEN. `is_halted()` and `session.can_enter()` have already
    # run and already returned; passing `trading_day=True` here does not make
    # them decorative, it avoids a SECOND opinion on a question already
    # answered by the gate that owns it. `cap_intact` is passed as the live
    # value anyway, so the table refuses on its own terms if the two ever
    # disagree — a disagreement that would otherwise be silent.
    _adm_now = now_et()
    try:
        _orb_d = get_orb_engine().data
        _pm_adm = get_position_manager(state.paper_trading)
        from execution.position_manager import rules as _adm_rules
        _pm_adm_rules = _adm_rules()
        _tries = {}
        for _bn in ("GEXPinButterfly", "ATPButterfly"):
            _tries[_bn] = 1 if _one_per_session_used(_bn) else 0
        # r42 — ONE PASS. `logging_state()` returns the binary AND the gate for
        # every strategy in the table, from a single walk. It replaced
        # `eligible_now()` + a `why_not()` loop: two calls, the same facts
        # passed twice, and nothing making them agree. Pass one fact slightly
        # differently to the second call and the board reports a gate that is
        # not the one that actually refused — wrong in the log, and
        # unfalsifiable from the log.
        from utils.time_utils import close_anchored as _close_anchored   # r268 (DEP.12): the day's bell
        _state = _pm_adm.logging_state(
            (_adm_now.hour, _adm_now.minute),
            trading_day     = True,
            orb_established = bool(_orb_d and _orb_d.orb_high and _orb_d.orb_low),
            cap_intact      = not _cap_hit,
            past_hard_close = _adm_now.time() >= _close_anchored(HARD_CLOSE, _adm_now),   # r268 DEP.12
            tries_used      = _tries,
        )
        _eligible = [n for n, (ok, _g, _w) in _state.items() if ok]
        # r254 (OBS.1) - "the plan always looks, but the strategies are gated on the hour"
        # (operator, 2026-10-05). The three r187 cut at 10:29 are still ASKED from their end
        # to the 15:40 entries stop, refused only by their window - and what they would fire
        # is recorded LOG-ONLY at the doors below, never executed.
        _obs = _pm_adm.observing(
            (_adm_now.hour, _adm_now.minute), _state,
            trading_day     = True,
            orb_established = bool(_orb_d and _orb_d.orb_high and _orb_d.orb_low),
            cap_intact      = not _cap_hit,
            past_hard_close = _adm_now.time() >= _close_anchored(HARD_CLOSE, _adm_now),   # r268 DEP.12
            tries_used      = _tries,
        )
        _set_admission(_eligible + list(_obs))
        _observe.set_active(_obs)
        _adm_ok = True
        # 🔑 A REFUSED STRATEGY NAMES THE GATE THAT REFUSED IT, and the GATE is
        # passed as its own field rather than buried in prose — `strategy/plan.py`
        # keys the operator's "say it once" rule on it (window once per inactive
        # episode; anything else declares itself), and parsing a sentence to
        # recover a gate name is how that rule would silently stop working.
        for _nm, (_ok, _gate, _why) in _state.items():
            if not _ok and _nm not in _obs:          # r254: an observed plan writes its own rows
                _plan_skip(_nm, f"inactive — {_gate}: {_why}", gate=_gate)
    except Exception as exc:                                   # noqa: BLE001
        # ⚠️ FAILS OPEN AND SAYS SO. `open_by_strategy()` RAISES rather than
        # returning {} (r35, deliberately — an empty map reads as "nothing is
        # open", the permissive answer). So a store that cannot be counted
        # lands here. Gating everything shut on that would take the box out of
        # the session silently; the pre-r40 gates are all still in place below,
        # so falling through to them is the smaller failure — but it is LOUD.
        _set_admission(None)
        _observe.clear()                # r254: no admission, no observing - plans keep their windows
        logger.error("[admission] table unavailable this tick — falling back to "
                     "the pre-r40 gates, NOTHING is admission-filtered: %s: %s",
                     type(exc).__name__, exc)
    else:
        if state.tick_count % 20 == 0:
            logger.info("[admission] may be asked: %s",
                        ", ".join(_eligible) if _eligible else "(none)")

    # ══ r178 (CAP.2) — AT THE CAP, ONLY THE BUTTERFLIES ARE ASKED ═════════════
    # The admission table has already refused every strategy but a cap-exempt
    # one (gate catastrophic_cap, one plan row each). This branch asks the
    # butterfly path and RETURNS, so no other strategy below is reached.
    # ⚠️ FAILS CLOSED. The admission block above fails OPEN when the table
    # cannot be computed (every name passes); at the cap that would let every
    # strategy trade, so here an uncomputed table means nothing is asked.
    if _cap_hit:
        if not _adm_ok:
            _plan_skip_all("CATASTROPHIC LOSS CAP reached and the admission table is "
                           "unavailable — nothing is asked", gate="catastrophic_cap")
            return
        _attempt_park(ctx, ms, state)                    # r288 (PARK.1): cap-exempt, its own budget
        _attempt_parc(ctx, ms, state)                    # OTV5 r46 (PARC.1): cap-exempt, its own budget
        _attempt_butterfly(ctx, ms, state, additive=True)
        return

    # ── Fetch options chain (shared across strategies) ────────────────────────
    chain = ctx.get("chain") or get_chain_fetcher().fetch_chain()
    if chain is None:
        _chain_miss_say(_rehearsing)                              # r301 (LOG.1)
        _plan_skip_all("no options chain this tick", gate="no_chain")
        return

    macro = ctx["macro"]
    signal = None          # r43 — RETAINED ONLY AS A "DID ANYTHING FIRE" TALLY.
                           # It no longer arbitrates: see `_fire()` below.

    # ══ r43 — EVERY ADMITTED STRATEGY FIRES ON ITS OWN ════════════════════════
    # Operator, 2026-09-18: *"I want the orb, hunt, breakout & sweep all able to
    # fire & non-competing. We only have one session at a time so we need to
    # maximize every opportunity on these setups. In live trading, we will revert
    # back to hierarchy-based."*
    #
    # 🔴 THE `signal` CASCADE *WAS* THE COMPETITION, and that is why removing
    # `has_blocking_position()` alone would not have delivered this. One variable,
    # five `if signal is None` guards, winner-take-all: the first strategy to
    # produce a signal consumed the tick and every strategy below it was never
    # even ASKED. Non-competing means each admitted strategy is asked and
    # executed independently.
    #
    # 🔑 THE PATTERN IS r12's, NOT A NEW ONE. `_attempt_hunt` has executed
    # ADDITIVE beside the ORB since r12 — *"the hunt runs beside the ORB, never
    # in its slot"* — and has been live ever since. This extends that proven
    # shape to the rest; it does not invent a mechanism.
    #
    # ⚠️ THE AFTERNOON DEBIT GATE MOVED WITH IT, AND HAD TO. It used to sit ONCE
    # at the tail, on whichever signal won the slot. With no slot there is no
    # single winner, so a tail gate would let every strategy but the last one
    # past it. It is applied PER SIGNAL here — which is also what its own
    # docstring asked for ("ONE gate instead of three... the next strategy added
    # silently bypasses the rule"), just relocated to the one funnel that now
    # exists.
    #
    # ⚠️ ADMISSION IS STILL THE ONLY LIMIT. `_safe_strategy` refuses anything
    # outside its window, and the table's `max_open_of_type` is what stops a
    # second ORB — not this function, and not a hand-rolled "already open" check.
    # ⚠️ THIS POSTURE IS TEST-BOX-ONLY, by his ruling. The fleet reverts to
    # hierarchy, and because the table overlays from `config.ADMISSION_RULES`
    # that reversion is a CONFIG CHANGE, not a revision.
    _fired: list = []

    def _fire(sig) -> bool:
        """Execute ONE strategy's signal, on its own. Returns True if it fired."""
        nonlocal signal
        if sig is None:
            return False
        if _log_only(sig, ctx):                         # r254 (OBS.1): observed - recorded, never fired
            return False
        if _afternoon_debit_blocked(sig.strategy_name, now_et()):
            logger.info(
                "STRATEGY: BLOCKED — %s is long premium and it is past the "
                "%02d:%02d ET afternoon debit cutoff (%s). Credit verticals and "
                "the pin butterfly are unaffected.",
                sig.strategy_name, DEBIT_DIRECTIONAL_CUTOFF_ET[0],
                DEBIT_DIRECTIONAL_CUTOFF_ET[1], fmt_et_short())
            if _sigj is not None:
                try:
                    _sigj.journal("disposition",
                                  outcome="gate_block:afternoon_debit",
                                  signal=_sigj.signal_ctx(sig))
                except Exception:                              # noqa: BLE001
                    pass
            return False
        # ADDITIVE ALWAYS. r197 already made `additive` a FACT rather than a
        # caller's opinion (`if additive or _pm.has_open_position()`), so this
        # is the same decision that path already reaches — stated here because
        # non-competing entries MUST append rather than replace, or the second
        # fire would silently drop the first from management.
        _execute_entry_signal(sig, ctx, ms, state, _sigj, additive=True)
        _fired.append(sig.strategy_name)
        signal = sig
        return True

    # Memoryless pass-through of the classifier's verdict — it adds ZERO latency
    # and holds NO state. It does not debounce, confirm, or wait: the instant
    # UNKNOWN→BREAKOUT transition fires the entry immediately (no late entries).
    # It only blocks when the tape is genuinely unclassified. Leaving UNKNOWN is
    #
    # retest is self-validating — the engine has already proven the setup
    # for. When the switch is on and the engine is in a confirmed OPEN state, an
    # UNKNOWN/undefined label does not veto: it flows through to the ORB dispatch
    # ── 🔴 r207 — ASK THE ENGINE, NEVER THE TICK'S COPY ──────────────────────
    # `ctx["orb"]` was bound in run_analysis at the top of this tick. Between
    # then and here, `manage_open_position()` may have closed an ORB, which
    # calls `notify_position_closed()` -> `_rearm()`, and `_rearm()` REPLACES
    # ORBData with a new instance. The ctx reference then reads OPEN_SHORT from
    # an object nothing else is looking at any more. That is exactly how QQQ
    # took two ORB shorts off one confirmation on 2026-09-01, and it is r96's
    # stale-dataclass defect at a different seam.
    # ⚠️ THE MISMATCH IS ANNOUNCED, NOT ABSORBED. A silent re-read would fix
    # this instance and hide the next one; WORKING_AGREEMENT 0.5 — no output is
    # never tidier than an error.
    orb = get_orb_engine().data
    if orb is not ctx.get("orb"):
        logger.warning(
            "[orb] the tick's ORB snapshot is STALE (ctx=%s engine=%s) — the "
            "engine re-armed inside this tick; dispatching on the ENGINE's "
            "state, not the copy",
            getattr(ctx.get("orb"), "state", "?"), getattr(orb, "state", "?"))
        ctx["orb"] = orb        # one view of one thing, for the rest of the tick
    orb_confirmed = orb.state in (ORBState.OPEN_LONG, ORBState.OPEN_SHORT)
    # ── 🔴 v4.3 (2026-08-21) — THE DISPATCH HARD GATE IS DELETED ─────────────
    # It read:
    #         return
    #
    # (v4 deleted the classifier), so this test was TRUE ON EVERY TICK. It
    # returned before dispatch on every box, every session. The fleet's FIRST
    # live day produced ZERO TRADES across all 15 boxes with relaxed entry ON,
    # and this line is the whole reason. The only reachable path was a
    # confirmed ORB break+retest via the bypass; every other strategy was
    # unreachable code.
    #
    # ⚠️ A GUARD OUTLIVES THE THING IT GUARDED — the same rule r55 produced,
    # one layer up and far more expensive. In v3 this protected against acting
    # on an unclassified tape. v4 has no classifier, so "unclassified" is the
    # PERMANENT state and the guard became a permanent veto.
    #
    # ⚠️ NOTHING REPLACES IT, DELIBERATELY. Operator's direction 2026-08-21:
    # "structural context unbuilt" veto here would be inventing a rule nobody
    # asked for, in the exact spot that just cost a session. Strategies own
    # their own preconditions; dispatch does not second-guess them.

    # ── AFD.1 PRE-DISPATCH BLOCK (v6.6, 2026-08-14) ──────────────────────────
    # ⚠️ THIS WAS A POST-SELECTION VETO AND THAT WAS THE BUG. The gate ran AFTER
    # every strategy had been evaluated, so past 11:00 a debit strategy could
    # still WIN the slot — `signal` became non-None, TC.6 (which sits behind
    # `if signal is None`) never ran, and only THEN was the debit signal
    # refused. **The tick produced no trade at all, and the slot the spec says
    # TC.6 owns was consumed by a strategy forbidden to trade in it.**
    # Placing it after the signal was chosen was right for JOURNALLING (the
    # refused signal is fully formed) and wrong for ARBITRATION. A strategy that
    # cannot trade in this window must not be EVALUATED in it.
    # The post-selection gate below is RETAINED as defence in depth: it costs
    # nothing, it still journals a fully-formed refusal if anything slips
    # through, and it catches a future strategy added to
    # DEBIT_DIRECTIONAL_STRATEGIES that forgets this pre-gate.
    _now_disp = now_et()
    # ⚠️ THE PRE-GATE NOW COVERS BOTH LONG-DEBIT STRATEGIES. v3 checked three
    # names, two of which were deleted on 2026-08-20 - and `_afd_cont` /
    # `_afd_swp` survived here as USES with no assignment, which is a runtime
    # NameError on the first tick and invisible to `import main`. Caught by
    # `tests/check_dispatch.py`, which is the third time this exact class has
    # appeared: the `ctx` P0, `_rc_bar` in the sweep mapper, and now this.
    _afd_orb = _afternoon_debit_blocked("ORBStrategy", _now_disp)
    _afd_run = _afternoon_debit_blocked("RunawayContinuation", _now_disp)
    if _afd_orb or _afd_run:
        logger.info("[afd] pre-dispatch: long-debit blocked past %02d:%02d "
                    "(orb=%s runaway=%s) - the afternoon belongs to the credit "
                    "structures and the butterflies",
                    DEBIT_DIRECTIONAL_CUTOFF_ET[0],
                    DEBIT_DIRECTIONAL_CUTOFF_ET[1], _afd_orb, _afd_run)
        # ── AUDIT F8 (2026-08-15) — THE REFUSAL JOURNAL MOVED WITH THE GATE ──
        # Moving AFD.1 to pre-dispatch made the POST-SELECTION journal at the
        # bottom of this function STRUCTURALLY UNREACHABLE for these three
        # strategies: they are skipped, so no signal is ever formed to carry a
        # `gate_block:afternoon_debit` disposition. **The cutoff's telemetry
        # went to zero the moment the slot bug was fixed** - a silent loss, and
        # exactly the class the repo's own gate-ordering reasoning warns about.
        # ⚠️ HONEST TRADEOFF, STATED: there is no SIGNAL here, so this record
        # carries no contract, strike or score. It answers "the cutoff fired and
        # for whom", not "what would have traded". The richer post-selection
        # record is retained below for anything that still reaches it.
        if _sigj is not None:
            try:
                for _nm, _hit in (("ORBStrategy", _afd_orb),
                                  ("RunawayContinuation", _afd_run)):
                    if _hit:
                        _sigj.journal("disposition",
                                      outcome="gate_block:afternoon_debit",
                                      signal={"strategy": _nm,
                                              "stage": "pre_dispatch"},
                                      )
            except Exception:                                  # noqa: BLE001
                pass

    # Priority 1: ORB — only when the engine has a CONFIRMED break+retest.
    # UNKNOWN and SWEEP_REVERSAL (ORB beats sweep — the engine no longer defers
    # its OPEN under a sweep label; see orb_engine v3.2). The break+retest is the
    # edge; the label is not consulted for go/no-go, only for scoring.
    # test went at r57 and the tuple sat consumerless: a guard's corpse one
    # level down. The v4.3 note below records the test's deletion.
    # v6.19 (2026-08-19) — ORB IS BLOCKED UNDER RANGING (operator direction:
    # that cell is the conclusive loss leader). Mirrored from
    # options_trader_smc the same day so the two arms remain comparable.
    # The refusal is JOURNALED, not silent: without the row, "ORB did not set
    # up" and "ORB was forbidden to fire" are indistinguishable in the record,
    # and only the second is a decision we can audit or reverse.
    # OT_ORB_BLOCK_RANGING=0 restores the old behaviour exactly — RANGING is
    # RANGING block could never fire, and the ok-set test only ever passed
    # through the UNKNOWN arm of the bypass. A confirmed break+retest is
    # self-validating — the engine has proven the setup from the tape — so the
    # ORB dispatch is now gated on CONFIRMATION alone, which is what the
    # bypass's own doctrine said it was doing all along.
    # OTV4TEST r2 — ASKED EVERY TICK, INCLUDING OUTSIDE ITS WINDOW. The
    # plan narrates every state (no range / both sides priced / armed and
    # PREPARED / confirmed / spent / runaway / re-entry) and fires only on
    # OPEN_* with an unspent confirmation. Outside 09:35–11:30 the plan is
    # DORMANT — one row on the transition, then silent (operator: "observe
    # only, don't write") — which is why the `_afd_orb` NOT ASKED row that
    # used to be written EVERY TICK all afternoon is gone; the afternoon
    # debit block itself is unchanged (`_afd_orb` still guards below).
    # ⚠️ ONE STANDING OFFER PER SETUP (r195): the engine stays OPEN_* while
    # an offer rests, so the resting offer is passed in and the plan
    # refuses at a named gate instead of this file skipping.
    orb_sig = _safe_strategy("ORB", lambda: _orb_strategy.generate_signal(
        orb           = orb,
        ms            = ms,
        vol_state     = ctx["vol"],
        # r20 — the ORB is passed NO level surface. Operator's ruling; the sweep's
        # own call sites keep theirs, because the sweep genuinely trades levels.
        chain         = chain,
        macro         = macro,
        current_price = ctx["price"],
        now_hhmm      = _now_disp.strftime("%H:%M") if _now_disp else "",
        offer_working = bool(orb_confirmed and _orb_offer_working()),
    ), ctx)
    if orb_sig and _afd_orb:
        logger.warning("[afd] ORB produced a signal past the afternoon debit "
                       "cutoff — refused here; the plan's window and this "
                       "gate disagree")
        orb_sig = None
    _fire(orb_sig)                                  # r43 — fires on its own
    # OTV4TEST r12 — THE LIQUIDITY HUNT runs beside the ORB, never in its slot
    # (PLAN_SPEC §37): asked every tick, executed additive, so both can be long
    # the same break. That is the paired comparison.
    # r43 — the handoff-granted sweep moved here from main_loop's open branch.
    # It is NOT the same as the sweep dispatch below: it requires a LIVE GRANT,
    # constrains the side to the grant's, stamps the provenance and CONSUMES the
    # grant. Deleting it with the other two would have lost a behaviour.
    _attempt_sweep_on_grant(ctx, ms, state)
    _attempt_hunt(ctx, ms, state, orb=orb, chain=chain,
                  now_hhmm=(_now_disp.strftime("%H:%M") if _now_disp else ""),
                  atr_pct=float(getattr(ctx.get("vol"), "atr_pct", 0.0) or 0.0))
    # ── r51 (BRK.1) — BREAKOUT, BESIDE THE HUNT AND THE ORB ─────────────────
    # All three are born from the same opening range and all three are admitted
    # in the same window. Operator, 2026-09-18: *"I want the orb, hunt, breakout
    # & sweep all able to fire & non-competing… letting them all go at the same
    # time is gonna allow us to get the differentiation needed to rule on them
    # later."* 🔑 THE HEAD-TO-HEAD IS THE POINT — under a cascade the losing
    # arm's outcome is UNOBSERVABLE, so "the hunt is better under X" could never
    # be learned. `_fire()` executes it additively; admission's per-type cap is
    # the only limit.
    _fire(_safe_strategy("Breakout", lambda: _breakout.generate_signal(
        orb        = orb,
        price_now  = ctx["price"],
        now_et     = (_now_disp.strftime("%H:%M") if _now_disp else ""),
        chain      = chain,
        df_1m      = ctx.get("df_1m"),
        flow_conn  = ctx.get("_flow_conn"),
        symbol     = INSTRUMENT,
    ), ctx))
    # ── r72 — VOLT, THE CONTROL ARM, BESIDE ALL FOUR ──────────────────────
    # Two gates: direction (close vs the session open) and rising volume. No
    # ADX, no regime, no levels, no R floor. 🔑 ITS ONLY JOB IS TO MAKE THE
    # OTHERS' GATES MEASURABLE — r51's head-to-head reasoning applied to the
    # gates themselves rather than to four different theses. Operator,
    # 2026-09-20: *"construct 1 more trade strategy & plan… as a control
    # group… Nothing more complicated."*
    # ⚠️ ADDITIVE, exactly like the Breakout above: `_fire()` executes it on
    # its own and admission's per-type cap is the only limit, so VOLT taking a
    # trade never costs the ORB one and the comparison stays clean.
    _fire(_safe_strategy("VOLT", lambda: _volt_strategy.generate_signal(
        chain      = chain,
        price_now  = ctx["price"],
        df_1m      = ctx.get("df_1m"),
        now_et     = (_now_disp.strftime("%H:%M") if _now_disp else ""),
        vol_state  = ctx.get("vol"),
        macro      = ctx.get("macro"),
        symbol     = INSTRUMENT,
    ), ctx))
        # 🔴 r195 — THE ENGINE NO LONGER RE-ARMS HERE, AND THAT WAS THE BUG.
        # `mark_triggered()` fired the moment the SIGNAL existed, which
        # re-armed the engine and `_rearm()` WIPES ORBData — direction,
        # stop, target, confirmation — while the plan was still live. Under
        # the ladder that was ~20s of exposure. With a standing offer it is
        # the rest of the session, and a second attempt could confirm and
        # place a SECOND offer at the same strike while the first still
        # rested, giving two records for one broker position.
        # The engine now stays OPEN_* until the TRADE resolves; the offer
        # supervisor calls notify_position_closed() on a fill-and-close or
        # a cancel trigger. Operator: "there is a SEQUENCE and 'waiting for
        # the break' isn't what comes after 'enter long/short'."
        # 🔴 r195 — THE ENGINE NO LONGER RE-ARMS HERE, AND THAT WAS THE BUG.
        # `mark_triggered()` fired the moment the SIGNAL existed, which
        # re-armed the engine and `_rearm()` WIPES ORBData — direction,
        # stop, target, confirmation — while the plan was still live. Under
        # the ladder that was ~20s of exposure. With a standing offer it is
        # the rest of the session, and a second attempt could confirm and
        # place a SECOND offer at the same strike while the first still
        # rested, giving two records for one broker position.
        # The engine now stays OPEN_* until the TRADE resolves; the offer
        # supervisor calls notify_position_closed() on a fill-and-close or
        # a cancel trigger. Operator: "there is a SEQUENCE and 'waiting for
        # the break' isn't what comes after 'enter long/short'."

    # ── Post-runaway routing (v-runaway-fix 2026-07-24) ───────────────────────
    # A RUNAWAY ORB (broke the range and ran to 50% TP with no retest) is a
    # MOMENTUM/TREND event, not an exhaustion. It must hand off to CONTINUATION
    # (enter WITH the move on a pullback), NOT to sweep reversal (which fades the
    # move and gets run over — the afternoon-giveback pattern). Sweep only runs
    # AFTER continuation has no setup, and then ONLY against a NAMED level
    # (PDH/PDL/session) — a reversal off a weak equal-H/L at the end of a strong
    # push is exactly the low-quality sweep that bled last week.
    # (OTV4TEST r3: `_is_runaway` retired — the runaway's plan reads the
    #  engine's `fifty_accepted` latch itself.)

    # ═══ v4.0 DISPATCH ═══════════════════════════════════════════════════════
    # ⚠️ ORDER IS LOAD-BEARING. RunawayContinuation must get first refusal after
    # ORB, because it fires on ORB's OWN state - the range ran to its 50% TP and
    # HELD - and firing DISARMS the retest. If anything else claimed the signal
    # first, the retest arm would stay live waiting for a pullback the tape has
    # already declined to give.
    _now_et_hhmm = _now_disp.strftime("%H:%M") if _now_disp else ""
    _atr_pct = 0.0
    try:
        # 🔴 r96 — PERCENT, NOT THE FRACTION. This value is handed to
        # RunawayContinuation (ATR floor 0.08, hard veto 0.05, the ATR->delta
        # map) and to SweepCreditSpread (ATR ceiling 0.20) — every one of them a
        # PERCENT threshold. Fed the fraction, the runaway's floor refused
        # everything and the sweep's ceiling refused nothing, so the SAME defect
        # failed closed on one strategy and open on the other.
        # Fallback is ×100 of the fraction so a part-baked box gets the right
        # number rather than a falsy 0.0 that would skip the veto.
        _atr_pct = float(getattr(ctx["vol"], "atr_pct", None)
                         or (float(getattr(ctx["vol"], "atr_normalized", 0.0) or 0.0)
                             * 100.0))
    except Exception:                                          # noqa: BLE001
        _atr_pct = 0.0

    # ── Priority 2: RUNAWAY CONTINUATION ────────────────────────────────────
    # r179 — ONE PER SESSION ON THIS BOX (operator, 2026-08-28: "Only one
    # runway debit trade aloud per session on a box … Simple"). DB-backed,
    # survives restarts, fails closed.
    # 🔴 r281 / RUN.1 (mirror of otv4 r481 c839bcf) — THE CAP NOW GATES. Since
    # OTV4TEST r3 this block read `if True:` under the comment above, so the
    # cap was never applied on this tree: QQQ-TEST took 27 second-or-later
    # Runaways in 21 sessions (-$987 gross). The per-BREAK rule
    # (strategy/runaway_continuation.py, r174) stays inside the strategy.
    _rc_capped = _one_per_session_used("RunawayContinuation")
    if _rc_capped:
        _plan_skip("RunawayContinuation", "one per session on this box — already "
                   "traded today", gate="tries_per_session")
    if not _rc_capped:                              # r43 — no slot to claim
        # OTV4TEST r3 — asked EVERY tick; the plan narrates (no direction /
        # waiting on the 50 accepted / break finished, re-validating / PREPARED)
        # and is dormant outside 09:35–11:30. `_is_runaway` no longer gates
        # the call: the trigger is the engine's `fifty_accepted` latch, which
        # is ALSO what invalidates the ORB (orb_engine v4.13).
        rc_sig = _safe_strategy("RunawayContinuation",
                                lambda: _runaway_strategy.generate_signal(
                                    orb           = orb,
                                    atr_pct       = _atr_pct,
                                    price_now     = ctx["price"],
                                    now_et        = _now_et_hhmm,
                                    chain         = chain,
                                    df_1m         = ctx.get("df_1m"),
                                ), ctx)
        if _fire(rc_sig):
            # ⚠️ THE RETEST IS DISARMED BY THE FIRING ITSELF. The runaway IS the
            # evidence price never came back for it, so leaving the arm live
            # would queue a second position on a pullback that is not coming.
            try:
                get_orb_engine().mark_triggered()
            except Exception:                                  # noqa: BLE001
                pass

    # ── Priority 3: SWEEP CREDIT SPREAD ─────────────────────────────────────
    # Sells the boundary a swept named pool just became. It runs AFTER the
    # runaway because a runaway proved directional force, and fading a level
    # into that force is the low-quality reversal that bled in v3.
    if True:                                        # r43 — no slot to claim
        sc_sig = _safe_strategy("SweepCreditSpread",
                                lambda: _sweep_cs_strategy.generate_signal(
                                    price_now     = ctx["price"],
                                    now_et        = _now_et_hhmm,
                                    atr_pct       = _atr_pct,
                                    chain         = chain,
                                    orb_high      = ctx.get("orb_high"),
                                    orb_low       = ctx.get("orb_low"),
                                    df_1m         = ctx.get("df_1m"),
                                ), ctx)
        if sc_sig:
            # r163 — the strategy classes its own trigger now: a tine TOUCH is
            # `{tf}_fork`, a real sweep is `sweep_reversal`. Only fill a blank.
            if not getattr(sc_sig, "condor_trigger_source", ""):
                sc_sig.condor_trigger_source = "sweep_reversal"
            # ── 🔴 r97 — VALIDATE BEFORE CLAIMING THE SLOT ───────────────────
            # ⚠️ AN INVALID SIGNAL USED TO CONSUME THE DISPATCH ANYWAY. Setting
            # `signal` here gates the butterfly and ALL FOUR credit-vertical
            # triggers below (`if signal is None`), while validation lives ~240
            # lines further down. So a signal that could never trade still shut
            # out every strategy behind it: 231 ticks on SPX, 90 on GOOGL,
            # 2026-08-24.
            # This is AFD.1 recurring, and this file already wrote the lesson
            # down: "a strategy-level veto still consumes the dispatch slot on
            # its way to returning None" and "placing it after the signal was
            # chosen was right for JOURNALLING and wrong for ARBITRATION."
            # ⚠️ THE POST-SELECTION CHECK STAYS. It is the one that JOURNALS a
            # fully-formed refusal, and it still catches anything reaching it by
            # another path. This is defence in depth, not a replacement.
            # ── 🔴 r99 — THE SWEEP IS A CREDIT VERTICAL AND TAKES THE CREDIT
            # PATH. Setting `signal = sc_sig` sent it down the GENERIC dispatch:
            # the debit scorer, `compute_size(premium=credit)` and
            # `entry_eng.enter()`, whose only arms are single-leg and butterfly
            # — `_place_single_leg` would have BUY_TO_OPENed `signal.contract`,
            # the SHORT strike, as a long. r97 built the spread and this line
            # would have bought its short leg. Same route as TC.6 below:
            # pairing gate -> `_execute_condor_leg`, which sizes it as a credit
            # vertical, stamps is_condor_leg for the pairing gate, and books
            # the broker's net credit.
            if not sc_sig.is_valid:
                logger.warning(
                    "SweepCreditSpread produced an INVALID signal - NOT "
                    "claiming the dispatch slot, so the butterfly and the "
                    "credit verticals still get this tick")
            elif _can_open_credit_spread(sc_sig.option_side, sc_sig,
                                         ctx["price"], ctx=ctx):
                # 🔴 r49 — THE `return` HERE ENDED THE WHOLE TICK, AND r43 MISSED IT.
                # r43 removed the identical early return from the TCS block and
                # left this one, so a sweep fill still silenced every strategy
                # sequenced below it — the cascade the operator's non-compete
                # ruling removed, surviving in one branch. MEASURED LIVE
                # 2026-09-18: the sweep filled at 12:34 and `IronCondorStrategy`
                # sat on the dispatch-gap default *"no reason recorded"* for the
                # next 204 minutes, because its `_plan_skip` is 140 lines below
                # this line. The operator found it by reading the board:
                # *"I want the messaging to look intentional and not like an
                # error."* It was neither — it was unreachable.
                # ⚠️ CREDIT LEGS DO NOT GO THROUGH `_fire`, so the tally is
                # kept by hand, exactly as the TCS leg does.
                _execute_condor_leg(sc_sig, state, ctx)
                _fired.append("SweepCreditSpread")
            else:
                logger.info("SweepCreditSpread %s side blocked by the pairing "
                            "gate - tick passes to the next strategy",
                            sc_sig.option_side)

    # ── Priority 4: GEX PIN BUTTERFLY ───────────────────────────────────────
    # ⚠️ PARKED - `ENABLED` is False and generate_signal returns None on the
    # first line. Wired anyway so the plumbing is exercised and audited NOW
    # rather than on the day it is unparked, ~2 weeks after real open interest
    # starts accumulating (2026-08-19).
    # ── BUTTERFLIES — one path, called, not inlined (r43) ────────────────────
    # r179 (one per session on this box) and OTV4TEST r26 (one butterfly of
    # EITHER kind) BOTH live inside `_attempt_butterfly`, which is also what
    # `check_atp_butterfly` drives directly to prove them.
    # ⚠️ THE CAP IS NOT RE-CHECKED HERE, DELIBERATELY. My first cut of r43 had
    # it in both places — two mechanisms for one rule, which is the drift this
    # revision spent its morning removing everywhere else.
    # ⚠️ ALWAYS ADDITIVE NOW: the butterfly never took a slot (r161) and after
    # r43 there is no slot left to take.
    _attempt_park(ctx, ms, state, chain=chain)          # r288 (PARK.1)
    _attempt_parc(ctx, ms, state, chain=chain)          # OTV5 r46 (PARC.1): beside PARK, never instead of it
    _attempt_butterfly(ctx, ms, state, additive=True)


    # Priority 2 (was sweep): Trend Continuation.
    # The runaway proved directional force, so it gets FIRST refusal on the
    # flipped to SWEEP_REVERSAL/BREAKOUT (a runaway commonly flips it). The
    # standalone (stricter) path still requires a trending label.
    # CNT.1 (v5.7) — BREAKOUT_VOLATILE added. The strategy decides whether it
    # can actually take it: it fires only if the trend engine's own vote gives a
    # direction (BULLISH/BEARISH, not NEUTRAL) AND primary_adx clears
    # CONT_BREAKOUT_MIN_ADX. Widening this tuple alone would NOT open the trade —
    # the direction branch inside the strategy is what does, and it self-vetoes
    # on a directionless tape.
    # ── CNT.6 (2026-08-10) — A CONTINUATION CANNOT CONTINUE A TREND THAT THE
    # LABEL SAYS IS NOT THERE. RANGING and COMPRESSION assert the absence of a
    # trend, so continuation in them is a contradiction, not a permissive edge.
    # runaway ORB flag let continuation fire on ANY tape — at Priority 2, ahead
    # of Butterfly (P3, RANGING/COMPRESSION) and Condor (P4, RANGING), which sit
    # behind `if signal is None` and were never even evaluated. That is the
    # squeeze: 13 sessions show RANGING → Continuation 94 vs IronCondor 27, and
    # COMPRESSION → Continuation 39 vs Butterfly 6.
    # The block goes HERE rather than in the strategy because a strategy-level
    # veto still consumes the dispatch slot on its way to returning None — CNT.3
    # blocked the COMPRESSION handoff inside continuation_strategy and the
    # squeeze continued regardless.
    # COMPRESSION) so `_cont_blocked` was permanently False and the whole
    # branch was unreachable. Removed rather than rewired — a continuation's
    # precondition is that a trend exists, which the trend engine answers
    # directly; it does not need a label to be told.
    # ── v4.0: SUPERSEDED STRATEGY REMOVED ───────────────────────────────
    # Continuation, SweepReversal and Butterfly dispatched here. All three
    # UNKNOWN - so they were DEAD CODE that still had to be read and
    # reasoned about by anyone auditing this path.
    # Their replacements are written and specced in docs/TRADES.md:
    #   ContinuationStrategy  -> RunawayContinuation (observes a move in
    #                            evidence rather than forecasting one)
    #   SweepReversalStrategy -> SweepCreditSpread (a long reversal needs
    #                            price to TRAVEL; 82% of directionally-
    #                            correct entries never reached +25% MFE)
    #   ButterflyStrategy     -> GEXPinButterfly (centres on the PIN, not
    #                            spot - indistinguishable while GEX was
    #                            gamma-squared, because the pin WAS spot)
    # ⚠️ NOT YET WIRED. The new strategies exist and import; dispatch is a
    # separate deliberate step, and Fable audits the plumbing first.
    # Priority 2.5 (was 2): Sweep Reversal.
    # After a runaway, sweep is the FALLBACK (continuation had no pullback setup)
    # and is gated to NAMED levels only — a runaway that then sweeps a real pool
    # and rejects is a legitimate reversal; a runaway that pokes an equal-H/L is
    # not. Non-runaway sweeps are unchanged (fire as before on the SWEEP label).
    # committed label to be SWEEP_REVERSAL; that label wins 0.4% of live ticks
    # and is exactly zero on 96%, so the trade was effectively off, and F7's
    # commit threshold narrowed it further. It now gates on the L1 _sweep SETUP
    # SCORE, whose three HARD VETOES are precisely the operator's stated
    # condition — a NAMED level (veto_loc), REJECTED back through (veto_reclaim),
    # not accepted beyond (veto_accept). A non-zero score already means all
    # three passed.
    # THE PLTR PROTECTION TRAVELS WITH THE SCORE: `trend_opp` is a
    # soft-necessary inside _sweep, so a reversal into a strong ACCELERATING
    # opposing trend still scores 0 and still cannot fire. That guard lived in
    # the scorer, never in this gate — which is why gating on the score keeps it
    # and gating on anything else would have lost it.
    _sweep_setup = 0.0
    # PHASE B (r58): the L1 read is DELETED. `ctx["l1"]` is set NOWHERE in
    # v4 — the scorer was never ported — so _sweep_setup has been a silent
    # 0.0 since the split and this block was a guard over a value nothing
    # computes (the r55/r57 lesson at score scale). The PLTR protection the
    # comment above describes lives in the v3 scorer, not here; if it is
    # wanted in v4 it must be REBUILT from structure, not resurrected by
    # name. _sweep_setup stays 0.0 — honest about what is measured: nothing.
    # Priority 3: Butterfly (Ranging/Compression — requires GEX PINNING)
    # Fed days allowed — and since MEAS.3 a Fed day changes NO trading: the
    # flag is recorded only (the ORB conviction boost is removed; operator,
    # 2026-10-03: "I don't want trading behavior to change on fed days").
    # ── PER-TICK CONDOR TRIGGER MAP (v4.3) ──────────────────────────────────
    # Recomputes fork tine positions (1h + 1d) from the live rails this tick.
    # Fork tines move with time+slope — a plan from 11am reads the 11am rail;
    # by 2pm the tine has drifted by slope×bars. Every trigger check this tick
    # reads from this map so all four strategies see the same geometry.
    # ⚠️ r134 — REUSE, DO NOT REBUILD. run_analysis now builds this map before
    # the derived engines run. Rebuilding here would give the dispatch a map
    # computed a few hundred milliseconds later than the one the plan engine
    # recorded, so the plan's stated geometry and the trade's actual geometry
    # could disagree by a tick. One map, one tick, one truth.
    if ctx.get("condor_triggers") is None:
        try:
            ctx["condor_triggers"] = _build_condor_trigger_map(
                ctx, INSTRUMENT, CONDOR_TRIGGER_APPROACH)
        except Exception:                                      # noqa: BLE001
            logger.debug("condor trigger map failed")
            ctx.setdefault("condor_triggers", None)

    # Priority 4: Iron Condor / Vertical Credit Spreads (v4.3: all four triggers)
    # ── v4.3 CONDOR REMODEL — Four independent triggers, pairing gate ──────
    # Each credit spread is autonomous: fires from its own structural signal,
    # manages as standalone. A second leg is ALLOWED when a complementary
    # trigger fires — never expected. When both sides are open the roll detects
    # them and applies the broken-wing adjustment.
    #
    # FOUR TRIGGERS (in priority order within this block):
    #   1h_fork  — 1h pitchfork tine  (IronCondorStrategy, existing)
    #   1d_fork  — daily pitchfork tine (DailyForkCreditSpread, new)
    #   sweep_reversal — reclaimed named pool  (SweepCreditSpread, existing)
    #   trend_orb      — ORB session extreme   (TrendCreditSpread, TC.6)
    #
    # PAIRING GATE: _can_open_credit_spread(side) enforces Rule 1 (max 2 open)
    # and Rule 3 (never 2 calls or 2 puts). It reads the DB every call; cheap
    # because it's one query against open_trades which is already loaded.
    # ── 🔴 r163 — THE DAILY FORK IS RETIRED AS A STRATEGY ─────────────────
    # Operator, 2026-08-27: a tine is *"basically a moving level that sweep is
    # allowed to use, but with a touch, not a reject."* The 1d and 1h tines
    # are published to the liquidity map as MOVING named pools at the assembly
    # point (liquidity_mapper v4.2 `publish_tines`), a TOUCH is emitted as a
    # sweep-shaped event, and the SWEEP's plan above prepares the spread
    # beyond the touching move. DailyForkCreditSpread — its plan cache, its
    # leg triggers, its own vertical construction — is deleted. The condor
    # constructs nothing (r158). What remains here is the record that this
    # block once dispatched two fork strategies, and the reason it no longer
    # does.
    # OTV4TEST r10 — the condor is NOT an entry. It FORMS when a second credit
    # spread pairs with the first (sweep–sweep or TCS–sweep, 08-24); the
    # fork-anchored premise is retired as a strategy. Hushed by the readers.
    _plan_skip("IronCondorStrategy", "not an entry — a condor forms from two credit "
                                     "spreads (sweep–sweep or TCS–sweep); retired as a "
                                     "strategy, OTV4TEST r10", gate="retired")

    # ── TC.6 TREND CREDIT SPREAD ─────────────────────────────────────────────
    # v4.3: no longer deferred by condor_active. It fires when _can_open_credit_spread
    # allows its side. condor_trigger_source="trend_orb" is stamped on the record.
    if True:                                        # r43 — no slot to claim
        _tcs_hi, _tcs_lo = _session_extremes(ctx)
        _orb_hi, _orb_lo = _opening_range(ctx)
        tcs_sig = _safe_strategy("TrendCreditSpread", lambda: (
            _trend_credit_strategy.generate_signal(
                ms=ms, vol_state=ctx["vol"], chain=chain, macro=macro,
                current_price=ctx["price"], trend=ctx.get("trend"),
                orb_high=_orb_hi, orb_low=_orb_lo,
                session_high=_tcs_hi, session_low=_tcs_lo,
                atm_iv=ctx.get("atm_iv"),            # OTV4TEST r9: the EM band
                df_1m=ctx.get("df_1m"),              # OTV4TEST r9: the frozen reference
                # 🔴 r238 — TCS NOW NEEDS THE ORB ENGINE. Its trigger is
                # `fifty_accepted` and its level is `target_50pct`; the old
                # docstring said "NO `orb` PARAMETER... there is no morning
                # level worth anchoring to", which was true of the BOUNDARY
                # and is not true of the 50.
                orb=get_orb_engine().data,
                condor_active=False)), ctx)  # v4.3: gate is _can_open_credit_spread
        if tcs_sig is not None:
            tcs_sig.condor_trigger_source = "trend_orb"
            if _can_open_credit_spread(tcs_sig.option_side,
                                        tcs_sig, ctx["price"]):
                # ⚠️ r43 — NO `return` HERE ANY MORE. It ended the whole tick
                # once the TCS leg was placed, so anything sequenced after it
                # was never asked. Credit legs route through
                # `_execute_condor_leg` and do NOT go through `_fire`, so they
                # are recorded here by hand.
                _execute_condor_leg(tcs_sig, state, ctx)
                _fired.append("TrendCreditSpread")

    # ── r204 — ORCS: the opening range credit spread (PLAN_SPEC §41) ─────────
    _attempt_orcs(ctx, state)


    # ══ r43 — THE TAIL REPORTS; IT NO LONGER ARBITRATES ══════════════════════
    # Every admitted strategy has already been asked AND executed on its own by
    # `_fire()`. What used to live here — the afternoon-debit gate and one
    # `_execute_entry_signal(signal, ...)` — moved INTO `_fire`, because with no
    # slot there is no single winner for a tail gate to catch.
    if not _fired:
        logger.info(f"STRATEGY: NO TRADE — adx={ms.adx:.0f} "
                    f"dir={ms.trend_direction} seq={ms.structure_sequence}")
    else:
        logger.info("STRATEGY: FIRED %d this tick — %s (non-competing; "
                    "admission's per-type caps are the only limit)",
                    len(_fired), ", ".join(_fired))
    return
    # 🔴 r43 — THE DEAD TAIL IS DELETED, NOT LEFT AS A CORPSE. What stood here
    # was the afternoon-debit gate plus one `_execute_entry_signal(signal, ...)`:
    # the single winner's execution. With every strategy firing on its own via
    # `_fire()`, `return` above makes this unreachable, and unreachable code that
    # LOOKS like a live gate is exactly how a rule gets believed in but never
    # runs — §20's guard-that-outlived-what-it-guarded, which this file has paid
    # for twice (the v4.3 dispatch hard gate, and r55 one layer up).
    # Its reasoning is PRESERVED where the rule now lives, inside `_fire`.


def _attempt_hunt(ctx, ms, state, *, orb, chain, now_hhmm, atr_pct) -> None:
    """OTV4TEST r12 — ask the liquidity hunt's plan (dormant outside 09:35–11:30)
    and on a fire execute it ADDITIVE: it takes no slot and is not counted as
    blocking (position_manager v4.9)."""
    try:
        _handoff.tick()
        _pm = get_position_manager(state.paper_trading)
        if any(str(r.get("strategy") or "") == "LiquidityHunt" for r in _pm.get_open_records()):
            _plan_skip("LiquidityHunt", "a hunt is already open on this box",
                       gate="max_open_of_type")
            return
        sig = _safe_strategy("LiquidityHunt", lambda: _liquidity_hunt.generate_signal(
            orb=orb, price_now=ctx["price"], now_et=now_hhmm, atr_pct=atr_pct,
            chain=chain, df_1m=ctx.get("df_1m"), atm_iv=ctx.get("atm_iv")), ctx)
        if sig is not None and not _log_only(sig, ctx):     # r254 (OBS.1)
            _execute_entry_signal(sig, ctx, ms, state, None, additive=True)
            _release_unfilled_hunt(sig, state)                  # r304 (HUNT.12)
    except Exception as exc:                                   # noqa: BLE001
        logger.warning("[hunt] attempt failed: %s", exc)


def _release_unfilled_hunt(sig, state) -> None:
    """r304 (HUNT.12) — A REFUSED ENTRY DOES NOT SPEND THE BREAK. The fire put (direction, boundary) in
    liquidity_hunt.FINISHED before execution; if execution opened nothing - no open Hunt on this box AND no
    trades.db row for the break today - the break is handed back, as if the fire never happened. An
    unreadable book keeps it spent (fail closed, HUNT.11's rule). Never raises."""
    try:
        _pm = get_position_manager(state.paper_trading)
        if any(str(r.get("strategy") or "") == "LiquidityHunt" for r in _pm.get_open_records()):
            return
        from strategy import liquidity_hunt as _lh
        _d, _b = str(getattr(sig, "direction", "") or ""), getattr(sig, "underlying_stop", None)
        if not _d or _b is None:
            return
        if _lh.break_finished_in_book(_d, _b) is not False:     # True = it traded; "unreadable" = fail closed
            return
        if _lh.release_break(_d, _b):
            logger.info("[hunt] %s %s from %.2f opened nothing - the break stays open (HUNT.12)",
                        getattr(sig, "hunt_entry", "?"), _d, float(_b))
    except Exception as exc:                                   # noqa: BLE001
        logger.warning("[hunt] break release check failed (%s) - the break stays spent", exc)


def _attempt_sweep_on_grant(ctx, ms, state) -> None:
    """OTV4TEST r12 — a live handoff grant naming the sweep lets it enter while
    another position is open; every other bar the sweep has still applies."""
    try:
        g = _handoff.live("SweepCreditSpread")
        if g is None:
            return
        _pm = get_position_manager(state.paper_trading)
        if any(str(r.get("strategy") or "") == "SweepCreditSpread" for r in _pm.get_open_records()):
            return
        sig = _safe_strategy("SweepCreditSpread", lambda: _sweep_cs_strategy.generate_signal(
            price_now=ctx["price"], now_et=now_et().strftime("%H:%M"),
            atr_pct=float(getattr(ctx.get("vol"), "atr_pct", 0.0) or 0.0),
            chain=ctx.get("chain"), orb_high=ctx.get("orb_high"), orb_low=ctx.get("orb_low"),
            df_1m=ctx.get("df_1m"), required_side=g["side"]), ctx)
        if sig is not None:
            sig.handoff_grant = f"{g['from']}→{g['to']} at {g['level']:.2f}, tick {_handoff.age(g)} of {g['ttl']}"
            _handoff.consume(g)
            _execute_condor_leg(sig, state, ctx)
    except Exception as exc:                                   # noqa: BLE001
        logger.warning("[handoff] sweep on grant failed: %s", exc)


def _attempt_park(ctx, ms, state, chain=None) -> None:
    """r288 (PARK.1) — ask PARK (its plan is dormant outside 11:01-11:03) and, on a fire, execute it ADDITIVE.
    Called from the normal dispatch AND the capped branch: PARK is cap-exempt (admission) and its P&L is outside
    the cap (config.CAP_EXCLUDED_STRATEGIES). One per session on this box, DB-backed (fails closed).
    OT_PARK=off: never asked. OT_PARK=log: asked, the would-be fire recorded by the strategy, nothing executed."""
    from config import PARK_MODE
    if PARK_MODE == "off":
        return
    if _one_per_session_used("PARK"):
        _plan_skip("PARK", "one per session on this box — already traded today", gate="tries_per_session")
        return
    _ch, _hhmm = chain, ""
    try:
        _t = now_et()
        _hhmm = _t.strftime("%H:%M")
        if _ch is None and (11, 0) <= (_t.hour, _t.minute) < (11, 5):   # the capped branch has no chain
            _ch = ctx.get("chain") or get_chain_fetcher().fetch_chain()
    except Exception:                                   # noqa: BLE001
        _ch = chain
    sig = _safe_strategy("PARK",
                         lambda: _park_strategy.generate_signal(
                             price_now   = ctx.get("price"),
                             now_et      = _hhmm,
                             chain       = _ch,
                             prior_close = (ctx.get("gap") or {}).get("prior_close"),
                         ), ctx)
    if sig is not None:
        _execute_entry_signal(sig, ctx, ms, state, None, additive=True)


def _attempt_parc(ctx, ms, state, chain=None) -> None:
    """OTV5 r46 (PARC.1) — ask PARC (its plan is dormant outside 11:01-11:03) and, on a fire, execute it through the
    credit-vertical door (_execute_condor_leg: paper_fill_credit on paper, the entry ladder live). Called right after
    _attempt_park from the normal dispatch AND the capped branch: PARC is cap-exempt (admission) and its P&L is outside
    the cap (config.CAP_EXCLUDED_STRATEGIES). One per session on this box, DB-backed (fails closed).
    OT_PARC=0: never asked (plan_state DORMANT). OT_PARC=log: asked; its TAKE is LOG-ONLY and the door refuses it."""
    from config import PARC_MODE
    if PARC_MODE == "off":
        return
    if _one_per_session_used("PARC"):
        _plan_skip("PARC", "one per session on this box — already traded today", gate="tries_per_session")
        return
    _ch, _hhmm = chain, ""
    try:
        _t = now_et()
        _hhmm = _t.strftime("%H:%M")
        if _ch is None and (11, 0) <= (_t.hour, _t.minute) < (11, 5):   # the capped branch has no chain
            _ch = ctx.get("chain") or get_chain_fetcher().fetch_chain()
    except Exception:                                   # noqa: BLE001
        _ch = chain
    sig = _safe_strategy("PARC",
                         lambda: _parc_strategy.generate_signal(
                             price_now   = ctx.get("price"),
                             now_et      = _hhmm,
                             chain       = _ch,
                             prior_close = (ctx.get("gap") or {}).get("prior_close"),
                             paper       = bool(getattr(state, "paper_trading", True)),
                         ), ctx)
    if sig is not None:
        _execute_condor_leg(sig, state, ctx)


def _attempt_butterfly(ctx, ms, state, *, additive: bool) -> None:
    # r179 — ONE PER SESSION ON THIS BOX (operator: "Only one GEX Pin
    # butterfly allowed per session on a box"). Checked BEFORE the strategy
    # is asked, at the one entry point every butterfly attempt routes
    # through. DB-backed, survives restarts, fails closed.
    # 🔴 r85 — ONE PER SESSION *EACH*, NOT ONE BETWEEN THEM. Operator,
    # 2026-09-21, reading the board after a single GEX pin had fired: *"I
    # think we only hit one butterfly the other one should still be allowed
    # ... Two different scenarios for those to fire under. And on certain
    # days, we might actually hit both."*
    # ⚠️ THE `or` GENERALISED A RULING PAST ITS OWN WORDS. r179 is quoted in
    # the comment above as *"Only one GEX Pin butterfly allowed per session on
    # a box"* — it names ONE strategy. The admission table has always agreed
    # with the operator: GEXFLY and ATPFLY each carry
    # max_tries_per_session=1, one EACH. This site read them with an `or` and
    # blocked BOTH the moment either fired — and because it is checked BEFORE
    # the strategy is asked, the admission table was never consulted. That is
    # r71's shape exactly: a plan-level check running ahead of admission and
    # disagreeing with it. MEASURED 2026-09-21: GEXPinButterfly fired at
    # 12:01 ET and ATPButterfly was refused for the rest of the session having
    # never traded.
    # ⚠️ r178's GUARD IS UNTOUCHED AND STILL DOES ITS JOB. The 2026-08-28
    # 15:00 stack was FIVE BUTTERFLIES ON ONE PIN in ninety seconds; the
    # per-strategy cap plus `mark_pin_played` are its two halves, and neither
    # needs the other kind blocked to work.
    _gex_used = _one_per_session_used("GEXPinButterfly")
    _atp_used = _one_per_session_used("ATPButterfly")
    if _gex_used:
        _plan_skip("GEXPinButterfly", "one per session on this box — already "
                   "traded today", gate="tries_per_session")
    if _atp_used:
        _plan_skip("ATPButterfly", "one per session on this box — already "
                   "traded today", gate="tries_per_session")
    if _gex_used and _atp_used:
        return
    """r161 — ask the butterfly's plan (dormant outside its slot) and, on a
    fire, execute it.

    🔑 r43 — THE ONE BUTTERFLY PATH. There were two: this, called from
    main_loop's position-open branch as r161's additive/exempt route, and an
    in-dispatch copy inside `attempt_new_entry` that COMPETED for the `signal`
    slot. r43 removed the slot, which made the two genuinely redundant — and
    the right survivor is THIS one, not the inline copy.
    ⚠️ AND THE CHECKERS ARE WHY. `check_atp_butterfly` drives this function
    DIRECTLY to prove the one-per-session cap (S1/S2); inlining it destroyed
    that seam and the check crashed on `module 'main' has no attribute
    '_attempt_butterfly'`. A behaviour that can only be tested through a
    700-line dispatch is a behaviour that stops being tested.
    ⚠️ IT ALSO CARRIES r178's `mark_pin_played` — the guard against the
    2026-08-28 15:00 stack of five butterflies in ninety seconds — which the
    in-dispatch copy NEVER called. Keeping this one keeps the guard on the
    live path by construction rather than by my remembering to copy it."""
    try:
        chain = ctx.get("chain")
        if chain is None:
            _plan_skip("GEXPinButterfly", "no options chain this tick", gate="no_chain")
            _plan_skip("ATPButterfly", "no options chain this tick", gate="no_chain")
            return
        # r205 — ONE SOURCE. Computed once in run_analysis and stored on ctx.
        # Recomputing here would let the dispatch and the snapshot disagree
        # about the same tick, which is the bug nobody would ever find.
        _atm_iv = ctx.get("atm_iv")
        bf_sig = None
        if not _gex_used:
            bf_sig = _safe_strategy("GEXPinButterfly",
                                    lambda: _gex_bfly_strategy.generate_signal(
                                        gex=ctx.get("gex"), price_now=ctx["price"],
                                        now_et=now_et().strftime("%H:%M"),
                                        atm_iv=_atm_iv, chain=chain), ctx)
        if bf_sig is not None:
            _execute_entry_signal(bf_sig, ctx, ms, state, None, additive=additive)
            # r178 — the fired pin is PLAYED for the session (one butterfly
            # per pin; the 2026-08-28 15:00 five-in-ninety-seconds stack).
            # Marked AFTER execution so a refused/zero-sized fire does not
            # burn the pin.
            try:
                from strategy.gex_pin_butterfly import GEXPinButterflyStrategy as _BF
                _BF.mark_pin_played(getattr(bf_sig, "pin_strike", None)
                                    or getattr(bf_sig, "strike", None))
            except Exception as _pp_err:                        # noqa: BLE001
                logger.warning("pin-played mark failed: %s", _pp_err)
            # ⚠️ r85 — THIS TICK, NOT THIS SESSION. Two butterflies must not
            # open on the SAME tick (r178's five-in-ninety-seconds is the
            # scar), but the ATP keeps its own session quota and may still
            # fire on a later tick under its own scenario.
            _plan_skip("ATPButterfly", "the pin butterfly fired this tick — one "
                       "butterfly per tick; the ATP keeps its own session quota",
                       gate="fired_this_tick")
            return
        # OTV4TEST r26 — asked only when the pin butterfly did not fire THIS
        # TICK. r85: no longer "did not fire this session" — the two read
        # different scenarios and both may fire on the same day.
        atp_sig = None
        if not _atp_used:
            atp_sig = _safe_strategy("ATPButterfly",
                                     lambda: _atp_bfly_strategy.generate_signal(
                                         gex=ctx.get("gex"), price_now=ctx["price"],
                                         now_et=now_et().strftime("%H:%M"),
                                         atm_iv=_atm_iv, chain=chain, df_1m=ctx.get("df_1m")), ctx)
        if atp_sig is not None:
            _execute_entry_signal(atp_sig, ctx, ms, state, None, additive=additive)
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("Butterfly attempt failed: %s", exc)


def _one_per_session_used(strategy: str) -> bool:
    """r179 — the durable session cap. True when this strategy has already
    entered a trade this ET session on this box (open OR closed), read from
    trades.db so five restarts cannot re-arm it. Fails closed."""
    try:
        from database.trade_logger import get_trade_logger
        return get_trade_logger().count_today(strategy) >= 1
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("one-per-session check failed CLOSED for %s: %s",
                       strategy, exc)
        return True


def _sig_num(signal, name: str) -> float:
    """A numeric field off a signal, whether the strategy assigned it as an
    ATTRIBUTE (shadowing the class method) or left the class METHOD exposed.
    Never raises — the execution tail must not die on a bookkeeping read
    (r173; see the sizing call below for the outage this caused)."""
    try:
        v = getattr(signal, name, 0.0)
        if callable(v):
            v = v()
        return float(v or 0.0)
    except Exception:                                           # noqa: BLE001
        return 0.0



def pin_proximity_verdict(ctx) -> tuple:
    """(refuse, frac, env, pin, why) — r97's pin-proximity decision, extracted.

    🔑 EXTRACTED SO THE CHECK CAN DRIVE THE REAL THING. §21: a test that reads
    source text proves nothing about runtime, and the r201 gate asserted a
    function existed and the file parsed — both true of the broken version.
    `check_pin_proximity` calls THIS, with the same ctx shape production hands
    it, and reads the verdict.

    🔑 THE RULE. Positive net GEX means dealers are LONG gamma: they sell
    rallies and buy dips to stay hedged, so price mean-reverts toward the pin.
    A directional debit fired NEAR that pin needs follow-through from the one
    regime built to suppress it. Operator, 2026-09-22: *"don't fire
    directionals into pinning GEX with price w/in EM to the pin."*

    ⚠️ PINNING ONLY. Negative gamma should INVERT the effect — dealers amplify
    — so a refusal in a TRENDING regime would be this gate firing backwards.
    ⚠️ FAILS OPEN, AND THE CALLER SAYS SO. `frac is None` means the tape could
    not be measured, never that it passed (§0.5).
    """
    try:
        gx = ctx.get("gex")
        pin = float(getattr(gx, "pin_strike", 0) or 0) if gx else 0.0
        env = str(getattr(gx, "gex_environment", "") or "") if gx else ""
        px = float(ctx.get("price") or 0)
        from strategy.gex_pin_butterfly import expected_move as _em_fn
        em = _em_fn(px, float(ctx.get("atm_iv") or 0)) if px else None
        if not (pin and em and em > 0):
            return False, None, env, pin, f"pin={pin or None} em={em}"
        frac = abs(pin - px) / em
        refuse = (env.upper() == "PINNING" and frac < PIN_PROXIMITY_MIN_FRAC)
        return refuse, frac, env, pin, ""
    except Exception as exc:                                    # noqa: BLE001
        return False, None, "", 0.0, f"{type(exc).__name__}: {exc}"


def pin_ahead_allows(signal, ctx, verdict) -> bool:
    """r54 (BRK.16) - True when the pin-proximity gate's REFUSAL is lifted for this signal: a Breakout whose pin is
    AHEAD of the trade - above the price for a long, below it for a short.

    🔑 The operator, 2026-10-29: "if the Pin is in the direction of the break, allow it. But if the pin is on the
    opposite direction from our trade, forbid it." The NARROW reading (concurred): the scope is today's - only a
    verdict that already refuses (PINNING, inside PIN_PROXIMITY_MIN_FRAC of EM) is asked; outside it nothing changes.
    ⚠️ A pin exactly AT the price is neither side and stays refused (today's gate); an unreadable direction, price or
    pin stays refused. Every other strategy: False (today's gate). Never raises; an error reads False (refuse).
    `verdict` is pin_proximity_verdict(ctx)'s tuple."""
    try:
        if str(getattr(signal, "strategy_name", "") or "") != "Breakout":
            return False
        _r, _fr, _env, _pin, _why = verdict
        if not _r or _fr is None:
            return False
        px = float(ctx.get("price") or 0)
        pin = float(_pin or 0)
        if not (px > 0 and pin > 0):
            return False
        d = str(getattr(signal, "direction", "") or "").lower()
        if d not in ("long", "short"):
            sd = str(getattr(signal, "option_side", "") or "").lower()
            d = "long" if sd.startswith("c") else "short" if sd.startswith("p") else ""
        if d == "long":
            return pin > px
        if d == "short":
            return pin < px
        return False
    except Exception:                                           # noqa: BLE001
        return False


def _noise_floor_of(df_1m) -> float:
    """r93's stop-distance floor: NOISE_FLOOR_BAR_MULT x the median 1m bar RANGE
    over the last NOISE_FLOOR_LOOKBACK_BARS bars. 0.0 means UNMEASURABLE and the
    sizer's gate stands down (r93 N3) - the caller logs that.

    🔴 r141 — EXTRACTED SO IT CAN BE DRIVEN, AND ITS MINIMUM MOVED TO CONFIG.
    Inline it required 10 bars, and `df_1m` is scoped to TODAY'S session
    (market_data.fetch_candles), so from 09:35 until ~09:40 - the ORB and
    Breakout window's busiest minutes - it returned 0.0 every day and the gate
    that exists to refuse a stop inside one bar's noise was OFF. 2026-09-25:
    stops of 0.14, 0.21 and 0.31 against a ~0.43 floor, 96-100 contracts each,
    -$3,170 in three minutes. NOISE_FLOOR_MIN_BARS (3) is the least a median
    means; the rule, multiplier and lookback are r93's, unchanged.
    """
    if df_1m is None or len(df_1m) < NOISE_FLOOR_MIN_BARS:
        return 0.0
    _rng = (df_1m["high"] - df_1m["low"]).tail(NOISE_FLOOR_LOOKBACK_BARS).dropna()
    if len(_rng) < NOISE_FLOOR_MIN_BARS:
        return 0.0
    return float(_rng.median()) * NOISE_FLOOR_BAR_MULT


# r161 (SIZE.2) — WHICH TRADES SCALE. Keyed on the strategy's OWN name, the
# same names _STRUCTURE_BY_NAME carries; a strategy not listed here never
# supplied geometry in the first place, so True for it changes nothing.
PIN_EXEMPT = ("PARK",)          # r288 (PARK.1): measured without the pin-proximity gate; logged, never refused


def _record_pin_counterfactual(signal, ctx, verdict, error: str = "") -> None:
    """r288 (PARK.1) — one row per PIN_EXEMPT entry: what the pin-proximity gate would have said
    (would_refuse / stood_down, the EM fraction, the pin, the regime), beside the entry it did not gate:
    data/counterfactual/pin_gate.jsonl. `verdict` is pin_proximity_verdict(ctx)'s tuple; None with `error`
    when the gate could not be read. Never raises."""
    try:
        import json as _json, time as _time
        _r, _fr, _env, _pin, _why = verdict if verdict else (None, None, None, None, error or "no verdict")
        if _fr is None:
            said = "stood down (%s)" % (_why or "unmeasurable")
        else:
            said = ("REFUSED (%.3f EM from pin %g)" % (_fr, _pin)) if _r else ("passed (%.3f EM)" % _fr)
        logger.info("[pin] %s NOT gated (PIN_EXEMPT) — the gate would have %s", signal.strategy_name, said)
        d = os.environ.get("OT_COUNTERFACTUAL_DIR") or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "counterfactual")
        os.makedirs(d, exist_ok=True)
        _c = getattr(signal, "contract", None)
        row = {"ts_epoch": _time.time(), "rule": "pin_gate", "strategy": signal.strategy_name,
               "symbol": INSTRUMENT, "acted": False,
               "would_refuse": None if _fr is None else bool(_r), "stood_down": _fr is None,
               "em_frac": _fr, "min_frac": PIN_PROXIMITY_MIN_FRAC, "pin": _pin,
               "regime": None if _env is None else str(_env), "why": _why or "",
               "price": ctx.get("price") if hasattr(ctx, "get") else None,
               "direction": getattr(signal, "direction", ""), "option_side": getattr(signal, "option_side", ""),
               "strike": float(getattr(signal, "strike", 0) or 0), "entry_premium": getattr(signal, "entry_premium", None),
               "streamer_symbol": getattr(_c, "streamer_symbol", "") if _c is not None else ""}
        with open(os.path.join(d, "pin_gate.jsonl"), "a") as fh:
            fh.write(_json.dumps(row, default=str) + "\n")
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[pin] pin-gate counterfactual row NOT written: %s", exc)
_SCALING_SWITCH = {"ORBStrategy": "SCALE_ORB", "Breakout": "SCALE_BREAKOUT",
                   "VOLT": "SCALE_VOLT"}


def _scaling_on(signal) -> bool:
    """True = size on the ramp; False = FLAT. The operator, 2026-09-27: *"ORB
    Scaling OFF/ON, Breakout Scaling OFF/ON, VOLT Scaling OFF/ON"*. Read from
    this module's bindings of the config switches so a test can flip one
    without re-importing config."""
    key = _SCALING_SWITCH.get(getattr(signal, "strategy_name", "") or "")
    return True if key is None else bool(globals()[key])


def _geometry_inputs(signal):
    """(orb_width, orb_stop_distance) for `size_for` — (0.0, 0.0) means the
    signal takes the budget rule. Extracted from `_execute_entry_signal`'s
    sizing block in r131 with its behaviour for every existing signal
    unchanged (pinned by tests/check_volt_sizing.py V4 against HEAD numbers).

    🔴 r131 — VOLT ADOPTS THE BREAKOUT SIZING MODEL. The operator, 2026-09-24:
    *"VOLT needs to adopt the breakout sizing model."* A signal may carry an
    explicit `sizing_distance`; when it does, it is SIZED ON GEOMETRY and that
    number — not |underlying_entry - underlying_stop| — is the distance the
    sizer (and its r93 noise floor) sees.
    ⚠️ WHY VOLT CANNOT USE entry - stop: its stop IS its entry by the
    operator's 2026-09-21 ruling (*"A close beyond where the trade opened is a
    dead thesis"*, strategy/volt_plan.py), so the distance is 0 by design and
    `_size_geometry` would take its DEGENERATE -> 1 contract branch on every
    fire. VOLT's declared R is the signal bar's range (`prep.risk_px`), the
    same number its trail arms on, so that is what it supplies.
    ⚠️ WHY VOLT DOES NOT SET `sizes_on_geometry`: that flag is also
    `OptionsSignal.sizes_on_structure()`, which re-anchors the entry-time
    trail activation to the entry premium (base_strategy.py) — an EXIT
    change the ruling did not ask for. `sizing_distance` opts into the sizing
    rule and nothing else. ORB and Breakout, which carry no sizing_distance,
    reach exactly the arithmetic they reached before.
    """
    _sd = getattr(signal, "sizing_distance", None)
    if not (getattr(signal, "strategy_name", "") == "ORBStrategy"
            or getattr(signal, "sizes_on_geometry", False)
            or _sd is not None):
        return 0.0, 0.0
    # Geometry INPUTS only — the rule itself (floor, clamp, degenerate→1)
    # lives in the sizer, so there is exactly one place it can be wrong.
    _orb_w = abs(float(getattr(signal, "orb_range_high", 0) or 0)
                 - float(getattr(signal, "orb_range_low", 0) or 0))
    # 🔑 r207 — THE RISK IS ENTRY-TO-STOP, AND THAT IS NOT NEGOTIABLE.
    # An intermediate cut of r207 sized on `orb_stop_distance_px`, the
    # impulsive wick measured from the BOUNDARY, frozen at the break.
    # Operator, 2026-09-01: *"The true risk is based on where we entered
    # though, not the range boundary. That's arbitrary. The 2 factuals are
    # the distance from entry to the stop."* He is right and the reasoning
    # was mine: the stop is a PRICE LEVEL, so what is at stake is the gap
    # between the fill and that level. The boundary is where the CANDLE
    # started, and it stands in for the entry only while the two coincide.
    # Freezing it bought determinism and paid for it in truth, which is
    # backwards — r119 and r181 both already said actual risk.
    # ⚠️ AND IT WAS SOLVING A PROBLEM THE LATCH HAD ALREADY REMOVED. The
    # 2-then-24 on QQQ was an ILLEGITIMATE FIRE — a spent confirmation
    # re-fired off a stale ORBData — not a mis-sized one. `order_placed`
    # and the engine re-read below kill it; this arithmetic never had to
    # change, and changing it was fixing the same defect twice in two
    # places, which is how a repair becomes a second defect.
    if _sd is not None:
        # r131 — the signal's own declared R (VOLT: the signal bar's range).
        # Its entry and stop coincide by design, so entry - stop is 0.
        return _orb_w, float(_sd or 0.0)
    _orb_d = abs(float(getattr(signal, "underlying_entry", 0) or 0)
                 - float(getattr(signal, "underlying_stop", 0) or 0))
    return _orb_w, _orb_d


def _sizing_stop_premium(signal) -> float:
    """The stop premium `size_for` sizes against. SIZING ONLY — never written
    back to the signal, so the row's `stop_premium` and every exit that reads
    it are unchanged.

    🔴 r131 OPTION 2 — THE OPERATOR, 2026-09-24: VOLT adopts Breakout's 1-R
    CURVE, not a flat scale-up. Breakout's 1-R is its structure stop in
    premium (`structural_stop_premium`, r91): entry - |delta| x distance. For
    VOLT the distance is the signal candle's range (`sizing_distance`), so
    rpc = |delta| x range x 100 — tight range, big size; wide range, small.
    ⚠️ WHY NOT signal.stop_premium(): VOLT's is the flat MAX_LOSS_PCT floor
    (its stop is its entry, so the structural conversion returns None), and
    `premium - 0.25 x premium` makes the count independent of the range —
    measured 3.6-4.4x the old budget size on every trade, whatever the range.
    ⚠️ NO DELTA -> THE FLAT FLOOR, LOUDLY (§0.5). Inventing a delta would size
    real money on a number nobody measured.
    ⚠️ A move at or beyond the premium -> 0.01, the same rule as
    structural_stop_premium: the honest 1-R is then the whole premium.
    Signals without `sizing_distance` (ORB, Breakout, everything else) get
    `_sig_num(signal, "stop_premium")` exactly as before r131.
    """
    _flat = _sig_num(signal, "stop_premium")
    _sd = getattr(signal, "sizing_distance", None)
    if _sd is None:
        return _flat
    try:
        _dl = abs(float(getattr(signal, "sizing_delta", None) or 0.0))
        _pm = float(getattr(signal, "entry_premium", 0.0) or 0.0)
        _dist = float(_sd or 0.0)
    except (TypeError, ValueError):
        _dl = _pm = _dist = 0.0
    if not (_dl > 0 and _pm > 0 and _dist > 0):
        logger.warning("[size] %s: no usable delta/premium/distance for the 1-R "
                       "curve (delta=%s premium=%s distance=%s) — sizing on the "
                       "FLAT stop premium %.4f instead",
                       getattr(signal, "strategy_name", "?"),
                       getattr(signal, "sizing_delta", None),
                       getattr(signal, "entry_premium", None), _sd, _flat)
        return _flat
    _move = _dl * _dist
    if _move >= _pm:
        return 0.01
    return _pm - _move


def _banner_dials() -> str:
    """r253 (RUNW.2) — the Service mode line's tail: the pin-proximity gate and Runaway's entry end
    IN FORCE, plus a refused OT_RUNAWAY_END by name. Read from config, never from the unit."""
    end = f" · runaway_end={RUNAWAY_CUTOFF_ET}"
    if RUNAWAY_END_ENV_REFUSED:
        end += f" (OT_RUNAWAY_END={RUNAWAY_END_ENV_REFUSED!r} REFUSED)"
    brk = f" · breakout_end={BREAKOUT_LATEST_ET}"                          # r265 (BRK.9)
    if BREAKOUT_END_ENV_REFUSED:
        brk += f" (OT_BREAKOUT_END={BREAKOUT_END_ENV_REFUSED!r} REFUSED)"
    brk += f" · brk_noprog={BRK_NOPROG_MODE}"                              # r265 (BRK.8)
    if BRK_NOPROG_ENV_REFUSED:
        brk += f" (OT_BRK_NOPROG={BRK_NOPROG_ENV_REFUSED!r} REFUSED)"
    brk += f" · brk_stop={'5m' if BRK_STOP5M_MODE == 'trade' else '1m'}({BRK_STOP5M_MODE})"   # r284 (BRK.11)
    if BRK_STOP5M_ENV_REFUSED:
        brk += f" (OT_BRK_STOP5M={BRK_STOP5M_ENV_REFUSED!r} REFUSED)"
    from config import BRK_DFLOOR_MODE, BRK_DFLOOR_ENV_REFUSED, PARK_MODE, PARK_ENV_REFUSED   # r288
    brk += f" · brk_dfloor={BRK_DFLOOR_MODE}"                              # r288 (BRK.13)
    if BRK_DFLOOR_ENV_REFUSED:
        brk += f" (OT_BRK_DFLOOR={BRK_DFLOOR_ENV_REFUSED!r} REFUSED)"
    brk += f" · park={PARK_MODE}"                                          # r288 (PARK.1)
    if PARK_ENV_REFUSED:
        brk += f" (OT_PARK={PARK_ENV_REFUSED!r} REFUSED)"
    from config import PARC_MODE, PARC_ENV_REFUSED                         # OTV5 r46 (PARC.1)
    brk += f" · parc={PARC_MODE}"
    if PARC_ENV_REFUSED:
        brk += f" (OT_PARC={PARC_ENV_REFUSED!r} REFUSED)"
    # r293 (DIAL.2) — the three dials whose refusal was recorded by config and read by NOTHING: a typo on
    # OT_HUNT_STOP5M moved every Hunt back to the 1m boundary with no line anywhere (audit 10-18 G2).
    from config import (HUNT_STOP5M_MODE, HUNT_STOP5M_ENV_REFUSED, BRK_REARM_MODE, BRK_REARM_ENV_REFUSED,
                        HUNT_REARM_MODE, HUNT_REARM_ENV_REFUSED,
                        BRK_REFIRE_MODE, BRK_REFIRE_ENV_REFUSED,                  # r316 (BRK.15)
                        HUNT_AFTER_BRK_MODE, HUNT_AFTER_BRK_ENV_REFUSED)          # r316 (HUNT.13)
    brk += f" · brk_refire={BRK_REFIRE_MODE}"                              # r316 (BRK.15)
    if BRK_REFIRE_ENV_REFUSED:
        brk += f" (OT_BRK_REFIRE={BRK_REFIRE_ENV_REFUSED!r} REFUSED)"
    brk += f" · hunt_after_brk={HUNT_AFTER_BRK_MODE}"                       # r316 (HUNT.13)
    if HUNT_AFTER_BRK_ENV_REFUSED:
        brk += f" (OT_HUNT_AFTER_BRK={HUNT_AFTER_BRK_ENV_REFUSED!r} REFUSED)"
    brk += f" · hunt_stop={'5m' if HUNT_STOP5M_MODE == 'trade' else '1m'}({HUNT_STOP5M_MODE})"   # r285 (HUNT.8)
    if HUNT_STOP5M_ENV_REFUSED:
        brk += f" (OT_HUNT_STOP5M={HUNT_STOP5M_ENV_REFUSED!r} REFUSED)"
    _brk_ra = "superseded" if BRK_REFIRE_MODE == "rearm" else BRK_REARM_MODE   # r316: the re-arm IS the rule
    brk += f" · rearm=brk:{_brk_ra}/hunt:{HUNT_REARM_MODE}"                # r286 (BRK.12 / HUNT.9)
    if BRK_REARM_ENV_REFUSED:
        brk += f" (OT_BRK_REARM={BRK_REARM_ENV_REFUSED!r} REFUSED)"
    if HUNT_REARM_ENV_REFUSED:
        brk += f" (OT_HUNT_REARM={HUNT_REARM_ENV_REFUSED!r} REFUSED)"
    brk += f" · resting_stop={RESTING_STOP_MODE}"                          # r266 (STOP.1)
    if RESTING_STOP_MODE == "trade" and not PAPER_TRADING:
        brk += " (LIVE: refused - stops close as before)"
    if RESTING_STOP_ENV_REFUSED:
        brk += f" (OT_RESTING_STOP={RESTING_STOP_ENV_REFUSED!r} REFUSED)"
    brk += f" · commit_gate={COMMIT_GATE_MODE}"                            # r272 (COMMIT.2)
    if COMMIT_GATE_MODE == "trade" and not PAPER_TRADING:
        brk += " (LIVE: refused - logs only)"
    if COMMIT_GATE_ENV_REFUSED:
        brk += f" (OT_COMMIT_GATE={COMMIT_GATE_ENV_REFUSED!r} REFUSED)"
    brk += f" · caution={CAUTION_SIZE_MODE}"                               # r272 (COMMIT.3)
    if CAUTION_SIZE_ENV_REFUSED:
        brk += f" (OT_CAUTION_SIZE={CAUTION_SIZE_ENV_REFUSED!r} REFUSED)"
    try:                                                                   # r270 (PMAP.1 + FILL.2)
        from execution.fill_observers import enabled as _fo_on
        brk += f" · fill_observe={'on' if _fo_on() else 'off'}"
        from execution.fill_observers import floor_watch_mode as _fw_mode  # r280 (EXIT.5)
        brk += f" · floor_watch={_fw_mode()}"
    except Exception:                                                      # noqa: BLE001
        brk += " · fill_observe=?"
    return f" · pin_gate={'ON' if PIN_PROXIMITY_ACTIVE else 'OFF'}{end}{brk}"


def _announce_plan_states() -> None:
    """r303 (PSTATE.1) — ONE line naming every plan's state and category, and data/plan_states.json for the
    devtools plans panel, so a DORMANT plan's silence is explained rather than mistaken for a fault (WA §0.5).
    Never raises."""
    try:
        from strategy import plan as _pb, plan_state as _ps
        _names = list(_pb.REGISTRY)
        logger.info("[plans] states — %s", _ps.summary(_names))
        _ps.write_states_file(names=_names)
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[plans] plan states not announced (%s: %s)", type(exc).__name__, exc)


def _log_only(signal, ctx) -> bool:
    """r254 (OBS.1) - True when `signal` comes from a strategy OBSERVED this tick (past its
    entry end): it is RECORDED - once per setup at INFO, with what the pin-proximity gate
    would have said - and never executed. False for everything else. Never raises; an
    error here reads True for an observed name (refuse) and False otherwise (unchanged)."""
    name = str(getattr(signal, "strategy_name", "") or "")
    try:
        if not _observe.is_active(name):
            return False
    except Exception:                                           # noqa: BLE001
        return False
    try:
        pin = "pin gate OFF"
        if PIN_PROXIMITY_ACTIVE:
            _r, _frac, _env, _pin, _why = pin_proximity_verdict(ctx)
            _ahead = pin_ahead_allows(signal, ctx, (_r, _frac, _env, _pin, _why))     # r54 (BRK.16)
            pin = ("pin unmeasurable" if _frac is None else
                   (f"pin would ALLOW ({_frac:.3f} EM from {_pin:g}, pin ahead)" if _ahead else
                    f"pin would REFUSE ({_frac:.3f} EM from {_pin:g})" if _r
                    else f"pin would pass ({_frac:.3f} EM from {_pin:g})"))
        strike = getattr(signal, "strike", None)
        key = (name, str(getattr(signal, "direction", "")), strike,
               round(float(getattr(signal, "underlying_stop", 0) or 0), 2))
        if _observe.first_time(key):
            try:                                                # r303: say WHICH rule made it log-only
                from strategy import plan_state as _ps
                _rule = "its plan is switched to LOG; PSTATE.1" if _ps.is_log(name) else "past its entry end; OBS.1"
            except Exception:                                   # noqa: BLE001
                _rule = "past its entry end; OBS.1"
            logger.info("[observe] LOG-ONLY %s %s %s @ %.2f stop %.2f - %s - NOT executed "
                        "(%s)", name, getattr(signal, "direction", ""),
                        strike, float(getattr(signal, "entry_premium", 0) or 0),
                        float(getattr(signal, "underlying_stop", 0) or 0), pin, _rule)
    except Exception as exc:                                    # noqa: BLE001
        logger.debug("[observe] record failed for %s: %s", name, exc)
    return True


def _shadow_manage(ctx) -> None:
    """r57 (TCS.LOG1) — one management pass over the open SHADOW trades (execution/shadow_book.py): the same
    position_manager / management / exit-engine code as a real TCS, at the mark, paper fills, its own store and rows.
    Nothing when no shadow store exists. Never raises."""
    try:
        from execution.shadow_book import peek_shadow_book
        _b = peek_shadow_book()
        if _b is not None:
            _b.manage(ctx)
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[shadow] manage pass skipped: %s", exc)


def _shadow_eod(state, hc_ctx=None) -> None:
    """r57 (TCS.LOG1) — the shadow book's end of day: position_manager.flatten_all over the shadows (EOD.1's clock,
    paper booked at the 15:55 cross), then, before 15:50, the held pass the real branch runs. Never raises."""
    try:
        from execution.shadow_book import peek_shadow_book
        _b = peek_shadow_book()
        if _b is None or not _b.has_open():
            return
        chain = _spot = None
        try:
            chain = get_chain_fetcher().fetch_chain()
        except Exception as e:                                  # noqa: BLE001
            logger.warning("[shadow] EOD: chain fetch failed (%s) - last marks this pass", e)
        try:
            _spot = get_cache().get_price()
        except Exception:                                       # noqa: BLE001
            _spot = None
        _b.flatten(chain=chain, spot=_spot)
        from utils.time_utils import eod_close_due as _ecd
        if _b.has_open() and not _ecd(False):
            _b.manage(hc_ctx if hc_ctx is not None else run_analysis(state))
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[shadow] EOD pass skipped: %s", exc)


def _shadow_resume() -> None:
    """r57 (TCS.LOG1) — boot: the shadow store's expired rows settled, its live rows resumed (what the real paper
    boot does, minus the broker). Nothing when no shadow store exists. Never raises."""
    try:
        from execution.shadow_book import peek_shadow_book
        _b = peek_shadow_book()
        if _b is not None:
            _b.resume_at_boot(settle=_settle_expired_row)
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[shadow] boot resume skipped: %s", exc)


def _execute_entry_signal(signal, ctx, ms, state, _sigj=None, *, additive: bool = False):
    """r161 — the execution tail of attempt_new_entry, factored so the
    butterfly can fire from main_loop while another position is open.
    `additive=True` APPENDS the record (add_open_position); False replaces,
    exactly as attempt_new_entry always did."""
    _stamp_vix(signal, ctx)                                     # r200: before the record is built
    _stamp_adx(signal, ctx)                                     # MEAS.4: beside it, same rule
    # r254 (OBS.1) - THE LAST LOCK, right after the VIX stamp (which only annotates the
    # signal) and before ANY sizing, risk or order work. `_fire` and the hunt's door already
    # refuse an observed signal; this one means no path added later can carry one further.
    if _log_only(signal, ctx):
        return
    macro = ctx["macro"]
    risk_mgr = get_risk_manager()
    entry_eng = get_entry_engine(state.paper_trading)
    if not signal.is_valid:
        logger.warning(f"Invalid signal from {signal.strategy_name}")
        if _sigj is not None:
            try:
                _sigj.journal("disposition", outcome="invalid_signal",
                              signal=_sigj.signal_ctx(signal),
                              )
            except Exception:
                pass
        return

    # ── 🔴 ENT.1 (r61) — NO TRADE OPENS ALREADY THROUGH ITS OWN STOP ─────────
    # Operator's ruling, 2026-09-19: *"any strategy check on the firing tick one
    # final time that the entry is not crossing the stop before the trade even
    # opens — not that it would happen often otherwise, but that it should NEVER
    # happen."* STRICT: at or beyond the stop is through. No band, no constant,
    # nothing to relax (WORKING_AGREEMENT 36 — the best foundational gate has no
    # knob at all).
    #
    # 🔑 WHY HERE AND NOT IN EACH STRATEGY. This is the ONE function every entry
    # opens through — `_fire()` reaches it for the dispatch chain, and the two
    # butterfly sites call it directly, bypassing `_fire` entirely. A check in
    # seven signal constructors is seven chances to forget and gives a NEW
    # strategy nothing; a check here is inherited. That is r40's own finding:
    # the admission gate went at the one funnel rather than at the call sites.
    #
    # ⚠️ IT REFUSES, IT DOES NOT PARK (section 37). The firing sequence re-arms and
    # the next qualifying trigger is taken normally, so this costs no legitimate
    # entry — it removes exactly the entries that were already lost.
    #
    # ⚠️ AND IT IS NOT A SIZING FIX. `entry_engine` computes `_risk` with
    # `abs(_u_entry - _u_stop)`, which turns an inverted stop into a SMALL risk
    # and a large `planned_r` — corrupting the R ledger rather than the order.
    # Repairing that arithmetic would size off a corrupted number; refusing the
    # entry makes the path unreachable instead of wrong.
    _und_stop = _sig_num(signal, "underlying_stop")
    if _und_stop and not getattr(signal, "underlying_stop_is_thesis", False):
        # the LIVE price on this tick. `ctx["price"]` is bound once per tick in
        # run_analysis, so inside the tick this is the identical number the
        # signal was built from; the fallback is for callers outside the loop.
        try:
            _px_now = float(ctx.get("price") or 0.0)
        except Exception:                                      # noqa: BLE001
            _px_now = 0.0
        if not _px_now:
            _px_now = _sig_num(signal, "underlying_entry")
        _dir = str(getattr(signal, "direction", "") or "").lower()
        _through = ((_dir == "long" and _px_now <= _und_stop)
                    or (_dir == "short" and _px_now >= _und_stop))
        if _px_now and _through:
            logger.warning(
                "ENTRY REFUSED — %s %s would open ALREADY THROUGH its own stop: "
                "price %.4f vs stop %.4f. The sequence re-arms; the next "
                "trigger is taken normally (ENT.1).",
                signal.strategy_name, _dir or "?", _px_now, _und_stop)
            if _sigj is not None:
                try:
                    _sigj.journal("disposition",
                                  outcome="gate_block:entry_underwater",
                                  signal=_sigj.signal_ctx(signal))
                except Exception:                              # noqa: BLE001
                    pass
            return

    # ── 🔴 THE SETUP SCORER IS GONE (r152) ────────────────────────────────────
    # Operator, 2026-08-27: *"What fucking SUM are we still using??? That is
    # TRASH CODE. It's held over dumpster fodder from otv3 which was a complete
    # failure."*
    # ⚠️ WHAT IT WAS: four dimensions × weights, summed to a `total`, compared
    # against a threshold to emit an A/B letter or REFUSE the trade.
    # ⚠️ WHY IT IS GONE, MEASURED — docs/INHERITED_FINDINGS.md §4: **A-grade 399
    # trades −$8,244 · B-grade 220 trades +$1,893.** It SELECTED LOSERS. ~90% of
    # it was one column printed twice, plus two constants measuring 1.000 across
    # all 619 trades. `vwap_alignment` and `liquidity_clear` were among the
    # constants — they never varied, so the sum never measured anything.
    # ⚠️ AND ITS TWO NAMED GATES WERE BOTH DEFAULT-OFF (`MIN_RRR_ACTIVE=0`,
    # `VWAP_FILTER_ACTIVE=0`), so by 2026-08-27 the entire file contributed
    # NOTHING to a trade except the refusal that stopped the fleet at zero
    # trades through the highest-volume half hour of the day.
    # ⚠️ THE VETOES THAT REMAIN ARE THE OPERATOR'S, AND THEY LIVE IN THE
    # STRATEGIES: the R hurdle (muted under relaxed), session-map geometry,
    # entry windows, level invalidation, distance-to-pin. A setup either meets
    # its own spec or it does not — there is no second opinion summed from
    # weights nobody chose.
    # ── r192 — ONE DOOR. The rule is chosen by the strategy's declared
    # STRUCTURE inside size_for(), not by a branch here. ORB gets the geometry
    # sub-rule by SUPPLYING its width and stop distance; every other
    # long_debit supplies neither and takes the budget rule unchanged.
    # 🔑 THE CALLER NO LONGER OWNS ANY SIZING POLICY, and that is the repair.
    # r181 computed ORB's count HERE and assigned `signal.contracts`, a field
    # the order never reads, so the fleet sized 1 lot for two days while
    # logging that it had not.
    # ⚠️ `stop_premium` stays exactly as r173 left it — see the note it
    # replaced: it is a METHOD on OptionsSignal unless a strategy shadows it,
    # and `_sig_num` is what stops float() raising into the loop catch-all.
    _struct = (getattr(signal, "structure", None)
               or _STRUCTURE_BY_NAME.get(getattr(signal, "strategy_name", ""))
               or "long_debit")          # fail closed, as the debit cutoff does
    # 🔑 r55 — GEOMETRY IS SUPPLIED, NOT NAMED. `RiskManager.size_for` says so
    # itself: *"Geometry is a sub-rule of long_debit, selected by the caller
    # SUPPLYING orb_width / orb_stop_distance rather than by naming ORB. A
    # second strategy that wants risk-normalised sizing supplies the geometry;
    # it does not get added to a list somewhere that later rots."*
    # 🔴 AND THE CALLER KEPT A NAME LIST ANYWAY. Until now this read
    # `== "ORBStrategy"`, so Breakout — which is the ORB without the retest and
    # carries the same geometry — fell through to `_size_budget`, the
    # RESTRICTIVE rule. The operator asked for it "sized the same as the orb";
    # it was not, and nothing said so because both paths return a SizingResult.
    # ⚠️ KEYED ON AN EXPLICIT FLAG, NOT ON orb_range_high: the hunt and the
    # runaway both carry that field and neither asked to be re-sized.
    # 🔑 r131 — THE GEOMETRY INPUTS ARE BUILT BY `_geometry_inputs(signal)`,
    # extracted VERBATIM from this block so tests/check_volt_sizing.py drives
    # the real arithmetic rather than a copy of it (§21). The r55/r207 notes
    # moved with the code. The one addition is VOLT's explicit
    # `sizing_distance` — read the helper's docstring.
    _orb_w, _orb_d = _geometry_inputs(signal)
    # ── r97 — PIN PROXIMITY: DO NOT FIRE A DIRECTIONAL ONTO THE PIN ──────
    # 🔑 The operator's hypothesis and his ruling that it ships as a
    # PARTICIPANT rather than an observer. Positive net GEX = dealers long
    # gamma = they sell rallies and buy dips, so price mean-reverts toward the
    # pin; a directional debit fired NEAR the pin is asking for follow-through
    # from the one regime that exists to suppress it.
    # ⚠️ DIRECTIONAL DEBITS ONLY. The butterflies WANT this condition — it is
    # the trade they are built for — and the credit spreads are not directional
    # at all. Keyed on the structure the strategy DECLARES, the same key
    # `size_for` dispatches on, never a strategy-name list (§23: a name list
    # rots, and it rots PERMISSIVELY).
    # ⚠️ PINNING ONLY. Negative gamma should INVERT the effect, so a refusal in
    # a TRENDING regime would be the gate firing backwards.
    # ⚠️ FAILS OPEN AND SAYS SO. No gex, no pin, no EM -> the gate stands down
    # and logs it; "could not measure" must never look like "measured and
    # passed" (§0.5).
    if PIN_PROXIMITY_ACTIVE and _struct == "long_debit" and signal.strategy_name in PIN_EXEMPT:
        # r288 (PARK.1) — not refused: PARK was measured without this gate. What it would have said is a
        # COUNTERFACTUAL row on every entry (the operator, 2026-10-17 20:06 ET: "I want a counterfactual on the pin
        # gate recorded on the entries"): data/counterfactual/pin_gate.jsonl.
        try:
            _record_pin_counterfactual(signal, ctx, pin_proximity_verdict(ctx))
        except Exception as _pg_exc:                           # noqa: BLE001
            _record_pin_counterfactual(signal, ctx, None, error=f"{type(_pg_exc).__name__}: {_pg_exc}")
    elif PIN_PROXIMITY_ACTIVE and _struct == "long_debit":
        _refuse, _pin_frac, _pin_env, _pin, _pin_why = pin_proximity_verdict(ctx)
        if _pin_frac is None:
            logger.warning("[pin] proximity gate STOOD DOWN (%s) — this entry "
                           "is unfiltered", _pin_why or "unmeasurable")
        elif _refuse and pin_ahead_allows(signal, ctx, (_refuse, _pin_frac, _pin_env, _pin, _pin_why)):
            # r54 (BRK.16) — the operator, 2026-10-29: "if the Pin is in the direction of the break, allow it."
            logger.info("[pin] ALLOWED %s %s: price %.2f is %.3f EM from pin %g (floor %.2f) in a PINNING "
                        "regime - pin ahead, in the direction of the break (BRK.16)", signal.strategy_name,
                        getattr(signal, "direction", ""), float(ctx.get("price") or 0), _pin_frac, _pin,
                        PIN_PROXIMITY_MIN_FRAC)
        elif _refuse:
            logger.info("[pin] REFUSED %s: price %.2f is %.3f EM from pin %g "
                        "(floor %.2f) in a PINNING regime — dealers dampen the "
                        "move this trade needs", signal.strategy_name,
                        float(ctx.get("price") or 0), _pin_frac, _pin,
                        PIN_PROXIMITY_MIN_FRAC)
            if _sigj is not None:
                try:
                    _sigj.journal("disposition", outcome="pin_proximity",
                                  reason=f"{_pin_frac:.3f} EM from pin {_pin:g} "
                                         f"< {PIN_PROXIMITY_MIN_FRAC:.2f} (PINNING)",
                                  signal=_sigj.signal_ctx(signal), score=None)
                except Exception:
                    pass
            return

    # ── r93 — THE NOISE FLOOR, MEASURED FROM THE TAPE, NOT A CONSTANT ────
    # 🔑 MEASURED DAILY RATHER THAN HARDCODED, at the operator's instruction.
    # The floor is a property of TODAY'S volatility: 0.42 on 2026-09-22 and a
    # different number tomorrow. A frozen threshold would be wrong in both
    # directions within a week — too loose in a quiet tape, too strict in a
    # fast one — which is the version-pinned-canary rot §24 records.
    # ⚠️ IT IS THE FULL BAR RANGE, NOT THE WICK. Price stops the trade out by
    # TRAVELLING to the impulsive candle's extreme, so what matters is how far
    # an ordinary bar moves, high to low.
    # ⚠️ AND IT STANDS DOWN LOUDLY WHEN IT CANNOT MEASURE (§0.5): no frame, too
    # few bars, or a degenerate median yields 0.0, the sizer's gate disarms,
    # and this logs it — refusing every entry because the feed hiccuped would
    # be a far worse failure than the one being closed.
    _noise_floor = 0.0
    _nf_df = ctx.get("df_1m")
    try:
        _noise_floor = _noise_floor_of(_nf_df)      # r141: arms from 3 session bars
    except Exception as _nf_exc:                                # noqa: BLE001
        logger.warning("[size] noise floor UNMEASURABLE (%s) — the stop-distance "
                       "gate stands down for this entry", _nf_exc)
    if _orb_d and _noise_floor <= 0:
        logger.warning("[size] noise floor UNMEASURABLE (%s 1m bar(s), need %d) — "
                       "the stop-distance gate stands down for this entry",
                       0 if _nf_df is None else len(_nf_df), NOISE_FLOOR_MIN_BARS)

    # r272 (COMMIT.3) - the order's own size_for call goes through a recorder (analysis.commitment.SizeCall) so
    # the caution log's scaling-off count is THIS call repeated with scaled=False - never a re-derivation.
    from analysis import commitment as _cm
    _size_rec = _cm.SizeCall(risk_mgr)
    sizing = _size_rec.size_for(
        _struct,
        premium             = signal.entry_premium,
        # r131 option 2 — SIZING-ONLY stop premium for a signal carrying
        # `sizing_distance` (VOLT); every other signal gets exactly
        # `_sig_num(signal, "stop_premium")`, as before. The signal's own
        # stop_premium() — what the row records and exits read — is untouched.
        stop_premium        = _sizing_stop_premium(signal),
        grade               = "UNGRADED",
        net_debit           = signal.net_debit if signal.is_butterfly else 0.0,
        butterfly_half_size = macro.butterfly_half_size if signal.is_butterfly else False,
        orb_width           = _orb_w,
        orb_stop_distance   = _orb_d,
        noise_floor         = _noise_floor,
        scaled              = _scaling_on(signal),        # r161: OFF = flat
    )

    if not sizing.allowed:
        logger.info(f"Sizing rejected: {sizing.reject_reason}")
        if _sigj is not None:
            try:
                _sigj.journal("disposition", outcome="sizing_rejected",
                              reason=str(sizing.reject_reason),
                              signal=_sigj.signal_ctx(signal),
                              score=None)   # r152 — scorer removed
            except Exception:
                pass
        return

    # r192 — the sizer's answer is the ONLY answer. The r181 geometry
    # override that lived here is GONE: it wrote `signal.contracts`, which
    # `entry_engine.enter()` never reads, so it could not reach the order.
    # Geometry now runs INSIDE size_for() and arrives in sizing.contracts,
    # the field the order actually places.
    signal.contracts  = sizing.contracts
    signal.total_cost = sizing.total_cost

    # ── r272 (COMMIT.2 / COMMIT.3) — WE ENTER ON COMMITMENT ───────────────────
    # The operator, 2026-10-12 10:34 ET: "A good place to get out cannot be a good place to get in and vice
    # versa"; 10:35 ET: "we enter on commitment and we exit on abandonment. We go with the market not against
    # it." Here, after sizing (so the would-be order is whole) and before the order: a DIRECTIONAL entry whose
    # side is ABANDONED on this tick's state (ctx["commitment"], analysis/commitment.py) is not placed when
    # OT_COMMIT_GATE=trade (unset) on a PAPER box. Every directional entry is recorded with its would-be order
    # (data/counterfactual/commit_gate.jsonl) so the old rule is replayable. An unreadable state ALLOWS the
    # entry and says why. The caution size (S2) is LOGGED only - it never changes `sizing`.
    if _cm.gate(signal, ctx, mode=COMMIT_GATE_MODE, paper=PAPER_TRADING, contracts=sizing.contracts):
        if _sigj is not None:
            try:
                _sigj.journal("disposition", outcome="gate_block:commit_abandoned",
                              signal=_sigj.signal_ctx(signal))
            except Exception:                                  # noqa: BLE001
                pass
        return
    # (CD.1) the r306/r316 20 s re-entry gate (RENT.2/RENT.3) is SCRAPPED - the operator, 2026-10-24: "It has zero value."
    _cm.caution(signal, ctx, mode=CAUTION_SIZE_MODE, contracts=sizing.contracts,
                flat_size=(_size_rec.flat if getattr(signal, "strategy_name", "") in _SCALING_SWITCH else None))

    # ── Enter trade ───────────────────────────────────────────────────────────
    # ⚠️ r152 — no score argument; the scorer is gone.
    record = entry_eng.enter(signal=signal, sizing=sizing)
    if record:
        # v5.1 — capture BEFORE anything else touches the row, but AFTER the
        # fill: the picture we want is the one that produced this entry.
        _capture_entry_snapshot(ctx, record, signal.direction)
        _capture_fire_snapshot(ctx, record)
        _capture_entry_contract(ctx, record)          # v5.5 (N.9)
        _pm = get_position_manager(state.paper_trading)
        # 🔴 r197 — ADDITIVE IS DECIDED BY WHAT IS OPEN, NOT BY THE CALL SITE.
        # `set_open_position` REPLACES `_open_records`, so an ORB entry landing
        # on a box that already holds a butterfly would silently drop the
        # butterfly from management — the hazard `add_open_position`'s own
        # docstring warns about, arriving from the other direction. Now that a
        # butterfly no longer blocks entries, that collision is reachable, so
        # the flag stops being a caller's opinion and becomes a fact: if
        # anything is open, append.
        if additive or _pm.has_open_position():
            _pm.add_open_position(record)
        else:
            _pm.set_open_position(record)
        get_alert_manager().send_entry_alert(record)
        logger.info(
            f"✅ Entry: {signal.setup_type} "

            f"contracts={sizing.contracts} "
            f"total=${sizing.total_cost:.2f}"
        )
        if _sigj is not None:
            try:
                _orb_ctx = None
                if signal.strategy_name == "ORBStrategy":
                    _depth = float(getattr(ctx["orb"], "retest_depth_px", 0.0))
                    _atr   = float(getattr(ctx["vol"], "atr_current", 0.0))
                    _orb_ctx = {"retest_depth_px": round(_depth, 4),
                                "retest_depth_atr": (round(_depth / _atr, 4)
                                                     if _atr > 0 else None)}
                # v5.9 — L1 EVIDENCE AT THE MOMENT OF THE FIRE.
                # that DECIDED the entry — the sweep's spent_val, ambient,
                # rejq_val, exh_val, trend_opp, touch_count, depth_val,
                # opp_adx, momentum — was computed here and then dropped.
                # Characterising entries afterwards would have meant REPLAYING
                # the tape and hoping the replayed score matched the one that
                # actually fired. The values exist at this line; recording them
                # costs one payload and no computation.
                # Always: the six-score VECTOR — cheap, and it is the ambient
                # context for ANY entry, not only sweeps.
                # Additionally: the firing setup's OWN breakdown, keyed by
                # strategy, so a fire does not carry five unused breakdowns.
                _l1_ctx = None
                try:
                    _l1r = ctx.get("l1")
                    if _l1r is not None:
                        _l1_ctx = {"scores": {str(k): _rnd4(v)
                                              for k, v in (_l1r.scores or {}).items()}}
                        _bdkey = _L1_BREAKDOWN_FOR.get(signal.strategy_name)
                        if _bdkey:
                            _bd = (_l1r.breakdown or {}).get(_bdkey)
                            if _bd:
                                _l1_ctx["breakdown"] = _bd
                                _l1_ctx["breakdown_of"] = str(_bdkey)
                except Exception:
                    _l1_ctx = None
                _sigj.journal("disposition", outcome="fired",
                              signal=_sigj.signal_ctx(signal),
                              l1=_l1_ctx,
                              score=None,   # r152 — scorer removed
                              fill={"contracts": sizing.contracts,
                                    "total_cost": round(sizing.total_cost, 2)},
                              orb=_orb_ctx)
            except Exception:
                pass



def _rnd4(v):
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None


# v5.9 — which L1 breakdown belongs to a firing strategy. A WRONG entry here
# does not raise: it files a well-formed breakdown from the wrong scorer under a
# correct-looking key, and a week of collection would be characterised against
# features that decided nothing. ORB and Butterfly are deliberately ABSENT —
# breakdown to it would imply a dependency the engine does not have. An unmapped
# strategy records the score vector and NO breakdown, never a wrong one.
_L1_BREAKDOWN_FOR = {
    "ContinuationStrategy":   "TRENDING",   # score() files BOTH trend scorers'
                                            # shared breakdown under this key,
                                            # not under the BULL/BEAR labels
    # PHASE B (r58): SweepReversal and IronCondor rows removed — the first
    # names a strategy deleted at r33; the second filed a label-keyed
    # breakdown nothing computes. An unmapped strategy records NO breakdown,
    # never a wrong one — the map's own rule.
}


def handle_session_reset(state: BotState):
    """Reset session-level state at the start of each RTH day."""
    if not state.session_reset_done:
        logger.info("RTH open — resetting session state")
        get_risk_manager().reset_session()
        state.session_reset_done = True
        state.orb_reset_done     = False
        state.orb_range_established_today = False

    if not state.orb_reset_done:
        get_orb_engine().reset_for_session()
        state.orb_reset_done = True
        logger.info("ORB engine reset for new session")

    # Fetch the ORB range only AFTER 9:35 ET when the 9:30-9:35 candle
    # is fully closed and baked. Fetching at 9:30 returns a degenerate
    # candle (high == low == 0 width) because the candle is still forming.
    if not state.orb_range_established_today:
        now_et_dt = datetime.now(ZoneInfo("America/New_York"))
        if (now_et_dt.hour, now_et_dt.minute) >= (9, 30):
            # Poll from the open: 9:30-9:35 writes IN_PROGRESS, then ESTABLISHED
            # once the candle closes. Latch ONLY on ESTABLISHED (returns True) so
            # we keep polling across IN_PROGRESS/EXPIRED instead of locking in a
            # carried-over range for the session.
            state.orb_range_established_today = _fetch_orb_range()

    _verify_official_print(state)          # r222 (ORP.1): the official print, once all five bars are in


def _vertical_close_due() -> bool:
    """r99 — True once credit verticals are due to close (VERTICAL_HOLD_TO_ET,
    15:45). Before it, from 15:40, debits flatten and verticals are managed."""
    from config import VERTICAL_HOLD_TO_ET, VERTICAL_HOLD_TO_CLOSE
    if not VERTICAL_HOLD_TO_CLOSE:
        return True
    # r268 (DEP.12, mirror of otv4 r478) — 12:45 on a 13:00 close.
    from utils.time_utils import past_close_anchor
    return past_close_anchor(VERTICAL_HOLD_TO_ET, now_et())


def handle_hard_close(state: BotState):
    """Force-close every open position at 15:45 ET — durably.

    Routes through pos_mgr.flatten_all(), which closes ALL open records (both
    condor legs) via the full exit accounting so each DB row is actually marked
    closed and booked — not just an order submitted. The main loop calls this
    every tick from 15:45 to 16:00, so an incomplete close is retried
    automatically; a persistent failure pages once (before the 16:00 stop turns
    it into an overnight orphan).
    """
    pos_mgr = get_position_manager(state.paper_trading)
    if not pos_mgr.has_open_position():
        state.hard_close_alerted = False   # nothing open — clear any prior page
        return

    instrument = os.environ.get("OT_INSTRUMENT", INSTRUMENT)
    # v3.4: fetch the chain ONCE for the hard-close so flatten_all can get real
    # marks (paper: simulated fill price; live: context). Without it, marks were
    # None and paper booked at entry premium -> every leg logged $0.00, poisoning
    # calibration. Fetched once here and reused across the 15:45->16:00 retries.
    chain = None
    try:
        chain = get_chain_fetcher().fetch_chain()
    except Exception as e:
        logger.warning(f"Hard close: chain fetch failed ({e}); "
                       f"paper marks may be unavailable this pass — will retry")
    # r149 (EOD.1) — the tick's spot, for the resting best-case price.
    _spot = None
    try:
        _spot = get_cache().get_price()
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"Hard close: spot unreadable ({e}) — resting closes price at the mark this pass")
    failed = pos_mgr.flatten_all(chain=chain, spot=_spot)

    if not failed:
        if pos_mgr.has_open_position():
            logger.info("EOD in progress — %d open (held to the ladder, resting, or laddering) until the cross",
                        len(pos_mgr.get_open_records()))
        else:
            logger.info("HARD CLOSE complete — all positions flat.")
        state.hard_close_alerted = False
        return

    logger.error(
        f"HARD CLOSE INCOMPLETE [{instrument}]: {len(failed)} still open "
        f"{[t[:8] for t in failed]} — retrying every tick until 16:00"
    )
    if not state.hard_close_alerted:
        get_alert_manager().send_hard_close_failure_alert(instrument, failed)
        state.hard_close_alerted = True


def _check_blindness(state: BotState):
    """Page the operator when the bot cannot see, and again when it can.

    Requirement (2026-08-01): ANY blinding condition — the feed down, stale data,
    a dead heartbeat, or anything else — notifies immediately AND logs the exact
    conditions, so the outage can be troubleshot rather than guessed at.

    This COMPLEMENTS the existing bot/service-down notification rather than
    duplicating it: that one fires when the bot STOPS, this one fires when the
    bot KEEPS RUNNING on data it cannot trust. Process alive, service green,
    trading blind was the uncovered middle.

    The snapshot reported is the one the latch captured at the FIRST blind tick,
    not the current state — by the time the latch trips, a feed that reconnected
    mid-outage would otherwise report healthy fields alongside the alert.
    """
    verdict = state.blind_latch.update(last_blindness())
    clear_blindness()          # this tick's fetches record fresh evidence

    if verdict == _BLIND_ALERT:
        instrument = os.environ.get("OT_INSTRUMENT", INSTRUMENT)
        snap = state.blind_latch.snapshot or {}
        try:
            open_rows = get_trade_logger().get_open_trades_live()
            descs = [getattr(r, "position_desc", None) or str(r) for r in open_rows]
        except Exception as e:                                    # noqa: BLE001
            # Never let the position read swallow the alert — a DB problem while
            # blind is more reason to page, not less.
            logger.error(f"blind alert: open-position read failed: {e}")
            descs = ["position read FAILED — check manually"]   # v4.12: no angle brackets; see alert_manager v1.10
        get_alert_manager().send_blind_alert(
            instrument, snap, open_positions=descs,
            paper=state.paper_trading,
            blind_for_s=state.blind_latch.blind_for_s())

    elif verdict == _BLIND_RECOVERED:
        instrument = os.environ.get("OT_INSTRUMENT", INSTRUMENT)
        # duration/cause come from the preserved fields — the latch has already
        # reset its live state by the time RECOVERED is returned.
        get_alert_manager().send_sight_restored_alert(
            instrument, state.blind_latch.last_outage_s,
            state.blind_latch.last_outage_cause)


_REHEARSAL_FLAG = os.path.join(os.path.dirname(LOG_FILE), "data", "REHEARSAL_OFF")


def _rehearsal_disabled() -> bool:
    """r108 — True when the operator has turned the pre-open rehearsal OFF.

    Read on EVERY pass, never cached: the flag is a live control (devtools item
    68 fans it out to the fleet with no restart), and a cached read would make
    the menu lie about what the boxes are doing — the failure `_MAINT_MARK`'s
    own comment calls out ("the marker is a HINT, not the truth").
    ⚠️ FAILS TOWARD RUNNING. An unreadable path leaves the rehearsal ON: the
    cost of rehearsing when you meant not to is some log noise; the cost of
    NOT rehearsing when you meant to is finding a broken build at 09:30:01.
    """
    try:
        return os.path.exists(_REHEARSAL_FLAG)
    except Exception:                                          # noqa: BLE001
        return False


def _rehearsal_note(state) -> None:
    """Say it once per process, then stay quiet. A disabled safety net is worth
    one line at INFO; it is not worth a line a minute for two hours."""
    if getattr(state, "_rehearsal_noted", False):
        return
    state._rehearsal_noted = True
    logger.info("[rehearsal] DISABLED by %s — the trading path will not be "
                "executed until 09:30. Re-enable with devtools 'Pre-open "
                "rehearsal'.", _REHEARSAL_FLAG)


_DISPATCH_PAGED: set = set()


def _page_dispatch_failure(state, err: Exception, where: str) -> None:
    """r101 — a tick that cannot complete is a BLINDING CONDITION and it pages
    on the first occurrence, once per process per error signature.

    ⚠️ THE STANDING RULE ALREADY COVERED THIS AND NOTHING IMPLEMENTED IT. The
    2026-08-01 requirement is that ANY blinding condition notifies immediately.
    On 2026-08-24 the loop raised on EVERY tick for fourteen minutes across all
    fifteen boxes and no page went out: the error counter only acts at thirty
    (shutdown), and `_check_blindness` watches the DATA, not the loop. Process
    alive, feed green, decisions impossible — an uncovered middle inside the
    uncovered middle.
    """
    sig = f"{where}:{type(err).__name__}:{err}"[:200]
    logger.error("DISPATCH FAILED (%s): %s", where, err, exc_info=True)
    if sig in _DISPATCH_PAGED:
        return
    _DISPATCH_PAGED.add(sig)
    try:
        get_alert_manager()._send(
            f"\U0001F6A8 {os.environ.get('OT_INSTRUMENT', INSTRUMENT)} "
            f"DISPATCH FAILED ({where}) — the bot cannot reach a trading "
            f"decision this tick: {type(err).__name__}: {err}. Feed and "
            f"process are fine; DECISIONS ARE NOT HAPPENING. {fmt_et_short()}")
    except Exception as _alert_err:                            # noqa: BLE001
        logger.error("dispatch-failure page could not be sent: %s", _alert_err)


_HEARTBEAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "BOT_HEARTBEAT")
_heartbeat_warned = False


def _touch_heartbeat(tick: int) -> None:
    """r168 (EXP.1 item 3) — one small write per main-loop pass. The emergency
    watchdog (tools/emergency_watchdog.py) reads its AGE: a loop that stops
    passing stops touching it, however quiet or noisy bot.log is (bot.log went
    silent 703-1208s at 15:40 ET on three flat days, so its age cannot say
    stuck). ⚠️ NEVER RAISES: a heartbeat that could stop the loop would be the
    hang it exists to catch. A failed write warns once and the watchdog, seeing
    the file age, pages - the loud direction."""
    # r295 (LIVE.2): one writer, utils.heartbeat.touch, shared with the live poll loops; this
    # keeps the tick number and the _HEARTBEAT seam the watchdog checker pins (W12).
    from utils.heartbeat import touch as _hb_touch
    _hb_touch(str(tick), _HEARTBEAT)


def main_loop(state: BotState):
    pos_mgr = get_position_manager(state.paper_trading)

    while True:
        # r51 (BAR.2) — never tick in the first BAR_FINAL_GRACE_S of a minute: the just-ended bar is still provisional.
        _grace = _bar_grace_wait(time.time())
        if _grace > 0:
            time.sleep(_grace)
        tick_start  = time.time()
        _obs_chain  = None              # r270 (FILL.2) — the chain the observing sleep reads
        state.tick_count += 1
        _touch_heartbeat(state.tick_count)   # r168 — the emergency watchdog's liveness read

        try:
            _apply_log_level()      # r112 — one stat; DEBUG flips with no restart
            # ── 🔴 r288 / DEV.11 — DISK GUARD MOVED HERE FROM candle_feed ───
            # It was at the top of the feed's `while True`, which is the
            # RECONNECT loop, not a tick loop: below it an `async with
            # DXLinkStreamer` opens the stream and an INNER loop handles events
            # for the life of that connection, so the check ran ONCE PER
            # CONNECTION — at startup, then not again until the stream dropped.
            # 📊 MEASURED: the feed restarted 17:24:14 UTC, a drill was armed a
            # minute later, and the flag was still sitting there.
            # 🔑 THIS LOOP GENUINELY TICKS, on POLL_INTERVAL_SECONDS, and it
            # sits beside `_apply_log_level()` — the same one-stat-per-tick
            # idiom, for the same reason.
            # ⚠️ ABOVE THE RTH BRANCH ON PURPOSE: a box left up over a weekend
            # is exactly when nobody is watching, and the disk does not care
            # whether the market is open.
            # ⚠️ AND `optionsbot` IS THE SERVICE THE DEPLOY PATH RESTARTS, so a
            # bake arms this without a separate candle-feed bounce.
            try:
                _disk_watch.check(sender=_disk_sender(), instrument=INSTRUMENT)
            except Exception:                               # noqa: BLE001
                logger.debug("disk_watch: skipped", exc_info=True)
            # ── OUTSIDE RTH: OBSERVE, DO NOT TRADE ─────────────────────────
            # 🔴 v4.7, 2026-08-24 — TRADING AND OBSERVATION WERE THE SAME GATE.
            # Operator: "TRADING can only occur during RTH, the feed should be
            # ALWAYS." The feed gate was lifted in r53 and the raw streams have
            # been healthy ever since — but the DERIVED LAYER runs at the end
            # of `run_analysis`, and this branch `continue`d before ever
            # reaching it. So every deriver inherited a gate that belongs only
            # to trading.
            # ⚠️ MEASURED 2026-08-24 07:42: greeks 3024 rows age=676s, quotes
            # 3024, prints age=1s — the inputs were abundant and fresh — while
            # indicators / pitchfork / levels / surface all read rows=0 on all
            # fifteen boxes. The operator's read was exactly right: "there is
            # enough information there to derive those artifacts."
            # 🔑 THE PRINCIPLE THIS RESTORES: derivers are CONTRIBUTORS and
            # never gate trading — so nothing about them should be gated BY
            # trading. `run_analysis` IS the observation pass; everything after
            # it in this tick is the trading pass. The gate belongs between
            # them, not in front of both.
            # ⚠️ AND IT FAILS SOFT. A pre-market pass that raises is logged at
            # DEBUG and skipped — thin frames outside RTH are arithmetic, not
            # faults (the 08-01 warnings-are-RTH-only rule), and an observation
            # failure must never keep a box from opening for business.
            if not is_rth():
                if state.session_reset_done:
                    # Day ended — reset flag so it fires again tomorrow
                    state.session_reset_done = False
                try:
                    _ctx = run_analysis(state)   # derives; trades nothing
                except Exception as _obs_err:                   # noqa: BLE001
                    logger.debug("pre-RTH observation pass skipped: %s",
                                 _obs_err)
                    _ctx = None
                # ── 🔴 r101 — RUN THE DECIDING PATH OUTSIDE RTH TOO ─────────
                # Operator, 2026-08-24: "I want the executing logic running as
                # long as the service is up. But one gate that blocks it from
                # placing orders until 0935."
                # ⚠️ WHY: THE TRADING HALF OF THIS PROGRAM WAS NEVER EXECUTED
                # UNTIL THE BELL. A box baked at 07:40 ran clean for two hours
                # and then died on its FIRST decision at 09:30:01 —
                # `MarketState() takes no arguments`, every tick for fourteen
                # minutes, through the ORB definition window. QQQ confirmed a
                # short at 09:40:03 and the same tick raised. A green pre-open
                # box proved nothing about the code that runs at the open, and
                # four defects of the same class (a call never made) survived
                # two code audits precisely because reading cannot find them
                # and calling finds them instantly.
                # ⚠️ THE CHAIN IS AVAILABLE HERE. Verified on the manifold board
                # 2026-08-24 08:57 and 09:19: chain marks / greeks / quotes all
                # green at age 22s. The log shows no pre-open chain builds
                # because the LOOP NEVER ASKED, not because the data was
                # missing — so this pass exercises the strategies for real,
                # from boot, rather than only from 09:30.
                # ⚠️ IT PLACES NOTHING. `entries_open()` refuses at both order
                # choke points, so this is a rehearsal with live inputs. Exits
                # are not reached: management runs only in the RTH branch, and
                # a position cannot exist before entries open.
                # ⚠️ AND IT FAILS LOUD, unlike the observation pass above. A
                # failure HERE is the failure that costs the session, so it
                # pages on the FIRST occurrence — see `_page_dispatch_failure`.
                # ── r108 — THE GO-RED TOGGLE (devtools item 68) ─────────────
                # The flag lives on the BOX and is read LIVE, like
                # FEED_MAINTENANCE: no restart, and it survives a bake. Its
                # PRESENCE turns the rehearsal OFF — inverted on purpose, so a
                # fresh, rebuilt or forgotten box rehearses. A flag you must
                # create to ENABLE a safety-adjacent behaviour is one that ends
                # up unset exactly when nobody was paying attention, which is
                # the morning this exists for.
                if _rehearsal_disabled():
                    _rehearsal_note(state)
                    secs = seconds_until_rth_open()
                    time.sleep(60 if secs > 120 else max(secs - 5, 5))
                    continue
                # r102 — SILENCE IS NOT A VALID OUTCOME HERE. Each branch says
                # how far the pass got, at INFO, so "the rehearsal ran" and
                # "the rehearsal proved something" stop looking alike.
                if _ctx is None:
                    logger.info("[rehearsal] SKIPPED — run_analysis produced no "
                                "context this pass (see the DEBUG above for why)")
                else:
                    try:
                        _pms = assemble_market_state(_ctx, "pre_open", state)
                        if _pms is None:
                            logger.info("[rehearsal] STOPPED at market state — "
                                        "assemble_market_state returned None")
                        else:
                            logger.info("[rehearsal] dispatch START (price=%.2f)",
                                        float(_ctx.get("price") or 0.0))
                            attempt_new_entry(_ctx, _pms, state)
                            logger.info("[rehearsal] dispatch END — the trading "
                                        "path completed without raising")
                    except Exception as _dry_err:               # noqa: BLE001
                        _page_dispatch_failure(state, _dry_err, "pre-open")
                secs = seconds_until_rth_open()
                if secs > 120:
                    logger.info(
                        f"Market closed (observing, not trading). Next RTH "
                        f"open in {secs/60:.0f} min. Sleeping 60s."
                    )
                    time.sleep(60)
                    continue
                else:
                    logger.info(f"RTH opens in {secs:.0f}s — standing by")
                    time.sleep(max(secs - 5, 5))
                    continue

            # ── RTH session reset ──────────────────────────────────────────
            handle_session_reset(state)

            # ── BLINDNESS WATCH (v4.11) ────────────────────────────────────
            # Evaluates the record left by the PREVIOUS tick's data fetches,
            # then clears it so this tick starts with a clean slate. The one-
            # tick lag is immaterial — the latch waits several ticks and 45s
            # before paging anyway — and reading it here means EVERY blind
            # path is covered, including the ones that raise out of
            # run_analysis before any later code could check.
            #
            # Deliberately keyed on the SYMPTOM (market_data could not serve
            # current data) rather than an enumerated list of causes: a cause
            # list only ever covers the failures already thought of, and the
            # requirement is "anything else that is blinding it".
            _check_blindness(state)

            # ── Intraday broker reconcile (LIVE + enabled) ─────────────────
            # Every 30 min across RTH, last sweep at 15:30 — catches a broker-
            # side leg closure (e.g. shorts auto-closed) before the 15:45
            # flatten acts. Fires once per slot; fail-safe on a bad/empty read.
            if not state.paper_trading and BROKER_RECONCILE_ENABLED:
                slot = _intraday_reconcile_slot(now_et())
                if slot and slot != state.last_reconcile_slot:
                    state.last_reconcile_slot = slot
                    _intraday_reconcile(
                        state, os.environ.get("OT_INSTRUMENT", INSTRUMENT)
                    )

            # ── Hard close check ──────────────────────────────────────────
            if is_hard_close_time():
                handle_hard_close(state)
                _hc_ctx = None
                # 🔴 r99 — CREDIT VERTICALS HOLD TO 15:45 (config
                # VERTICAL_HOLD_TO_ET, operator ruling 2026-08-13) BUT NOTHING
                # ENFORCED IT ON THIS PATH. flatten_all closed every record
                # from 15:40 and this `continue` skipped the manage branch, so
                # the exemption in _evaluate_condor_leg never ran. flatten_all
                # now holds the verticals until 15:45; this block keeps them
                # MANAGED in between — the lone 15% floor still applies to a
                # vertical at 15:41.
                from utils.time_utils import eod_close_due as _ecd     # r149
                if pos_mgr.has_open_position() and not _ecd(False):  # held debits managed until 15:50
                    try:
                        _hc_ctx = run_analysis(state)
                        pos_mgr.manage_open_position(
                            chain=_hc_ctx.get("chain"),
                            df_1m=_hc_ctx.get("df_1m"),
                            df_5m=_hc_ctx.get("df_5m"),
                            vol_state=_hc_ctx.get("vol"),
                            trend=_hc_ctx.get("trend"),
                        )
                    except Exception as _hc_err:                # noqa: BLE001
                        logger.warning("15:40-15:45 vertical manage pass "
                                       "failed: %s", _hc_err)
                _shadow_eod(state, _hc_ctx)          # r57 (TCS.LOG1): the shadow book's end of day
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            # ── 🔴 CHAIN AND GEX ARE FETCHED *BEFORE* run_analysis (r133) ──
            # They used to be fetched ~20 lines BELOW this call, which meant
            # the derived engines — which run INSIDE run_analysis — saw no
            # chain and no gex, while the strategies further down the tick saw
            # both. The code already named the smell at line ~1385: *"written
            # mid-dispatch ... their availability depends on where in the tick
            # you stand — an input present for one consumer and absent for
            # another. No derived port may be built that way."*
            #
            # ⚠️ WHAT IT COST: every plan builder guards on `chain is None` and
            # returned None, so `plans` was empty EVERY tick, `_write_tick`
            # was never reached, and `plan_tick`/`plan_check` were never
            # CREATED. From outside, "the engine never ran" and "the engine ran
            # and found nothing" looked identical — it took three rounds of
            # queries on the morning of 2026-08-26 to tell them apart.
            # ⚠️ AND IT WAS NOT ONLY THE PLANS. surface/snapshot/notes/
            # plan_ledger all read ctx["gex"] and coerce it, so they recorded
            # NULL rather than branching — a silent hole in four tables.
            #
            # ⚠️ THIS ADDS NO MARKET-DATA LOAD. The fetch was ALREADY every
            # tick and unconditional ("Compute GEX every tick — used by all
            # strategies + position mgr"); only its POSITION moves.
            _gex_chain = None
            try:
                from data.options_chain import get_chain_fetcher
                _gex_chain = get_chain_fetcher().fetch_chain()
            except Exception as exc:                           # noqa: BLE001
                logger.debug("pre-analysis chain fetch: %s", exc)

            # ── Main analysis ─────────────────────────────────────────────
            ctx = run_analysis(state, chain=_gex_chain)
            _obs_chain = ctx.get("chain")    # r270 (FILL.2)
            # r272 (COMMIT.1) — the commitment state, once per tick, on ctx (the entry gate reads THIS, never the
            # store); one row per side per new closed 1m bar to data/counterfactual/commitment.jsonl. Never raises.
            from analysis import commitment as _cm
            ctx["commitment"] = _cm.observe(time.time())

            # cheap (threshold checks over the ctx run_analysis already computed),
            # so we reclassify every tick — no throttle. Verified safe: the only
            # (butterfly/condor), which are event-driven and WANT to fire the
            # off-schedule reassessment tag for the logs.
            loss_reassess = get_risk_manager().consume_reassess_request()
            trigger = "loss_limit" if loss_reassess else "scheduled"
            ms = assemble_market_state(ctx, trigger, state)

            if ms is None:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            # ── Compute GEX every tick (used by all strategies + position mgr)
            try:
                from data.gex_data import compute_gex as _compute_gex
                # ⚠️ r133 — NO SECOND FETCH. `_gex_chain` was fetched above
                # and is already on ctx; re-fetching here would double the
                # market-data calls and could disagree with what the derived
                # engines just recorded from the FIRST chain. Same object, one
                # tick, one truth.
                if _gex_chain:
                    ctx["gex"]   = _compute_gex(_gex_chain, ctx["price"])
                    ctx["chain"] = _gex_chain
                    # v4.2: archive the FULL chain on a wall-clock cadence.
                    # LOG-ONLY and NO extra market-data load — it serializes the
                    # object we already hold. Hooked here rather than in
                    # attempt_new_entry because this block runs EVERY tick
                    # regardless of entry eligibility, so snapshots continue
                    # while halted, while a position is open, and outside the
                    # condor window. Option chains are unrecoverable after
                    # 16:00; nothing else in the system archives them.
                    # ── PF.2 (2026-08-11) — PITCHFORK OBSERVATION, WEIGHT 0 ──
                    # Builds the daily + hourly forks from THIS BOX's own frames
                    # and journals where price sits in each channel. Gates
                    # nothing, is read by no strategy, and never raises.
                    # Hooked HERE for the same reason chain_snapshot is: the
                    # entry path is skipped when entries are blocked, so a hook
                    # there would silently lose observations during halts, while
                    # a position is open, and outside every strategy's window.
                    # The point is the CONTINUATION JOIN — when continuation
                    # fires, where was price relative to the rail? That is one
                    # observation per trade at 13-76 trades a session, unlike
                    # the touch study which needed n~600 and was unreachable.
                    try:
                        from analysis.pitchfork_observer import snapshot as _pf_snap
                        _pf_snap(ctx, INSTRUMENT,
                                 journal=(_sigj.journal if _sigj is not None
                                          else None))
                    except Exception:
                        pass
                    try:
                        from analysis.chain_snapshot import snapshot as _chain_snap
                        _chain_snap(
                            _gex_chain,
                            underlying_price=ctx.get("price"),
                            # passed — the label was permanently UNKNOWN.
                            # snapshot() keeps the parameter (default None)
                            # so the field stops being WRITTEN while the
                            # schema question stays the operator's (B3).
                        )
                    except Exception:
                        pass          # never let archival touch the loop
            except Exception as _gex_err:
                logger.warning(f"GEX tick fetch failed: {_gex_err}")

            # ── v4.3: TRADE READINESS (log-only) — every tick, like the chain
            # snapshot: it must keep observing while halted, while a position
            # is open, and outside any entry window, because the record of the
            # confluence RISING AND FALLING is the point. Gates nothing; the
            # engine swallows its own failures; the loop cannot be touched.
            if _readiness is not None:
                _readiness.assess_all(ctx, ms)

            # ── Manage open position ──────────────────────────────────────
            _supervise_offers(ctx, state)   # r195 — BOTH branches
            _supervise_credit_remainders(ctx, state)   # r315 — BOTH branches
            _shadow_manage(ctx)             # r57 (TCS.LOG1) — BOTH branches; the shadow book only
            if pos_mgr.has_open_position():
                # ── Broken-wing roll: FIRST REFUSAL ───────────────────────
                # The roll must run BEFORE manage_open_position. The per-leg
                # 25% condor stop lives in manage_open_position; if it runs
                # first it closes the tested leg, and the roll needs BOTH
                # verticals open — so the stop used to guillotine the tested
                # side before the roll could ever act. check_and_execute_roll
                # self-gates: it executes ONLY when a risk-free roll exists,
                # so when no roll is viable the stop still fires exactly as
                # before (same 25% downside, no new risk). When a roll IS
                # viable, it converts the untested side and the tested side
                # goes risk-free instead of stopping at a loss.
                # r160 — the MANAGEMENT PLAN's row first: which rung, what
                # the next rung costs right now, does it clear. Narrates only;
                # the two calls below act on the same numbers.
                try:
                    _iron_condor_strategy.manage(pos_mgr, ctx.get("chain"),
                                                 ctx["price"], ctx.get("df_1m"), ctx=ctx)
                except Exception as _mg_err:                    # noqa: BLE001
                    logger.warning(f"Condor management row failed: {_mg_err}")
                try:
                    from strategy.condor_roll import check_and_execute_roll
                    check_and_execute_roll(pos_mgr, ctx.get("chain"), ctx["price"], state,
                                           df_1m=ctx.get("df_1m"))          # r10: tested by wick
                except Exception as _roll_err:
                    logger.warning(f"Roll check failed: {_roll_err}")

                # ── r106 — THE TENT, THE RUNG BELOW THE ROLL ─────────────────
                # Runs AFTER the roll and only bites on an ALREADY-ROLLED
                # structure that has since been breached, so the two can never
                # compete for the same tick: the roll collects credit, the tent
                # pays a debit, and paying when collecting was available would
                # be strictly worse. Same first-refusal ordering, one rung down.
                # OTV4TEST r11 — the tent rung is RETIRED (PLAN_SPEC §35 v2): the
                # widened-wing roll is rung 1 at its limit; after it the only
                # exit is the 15%-from-formation floor (exit_engine v4.16).

                # classification the engine cannot currently confirm. None is
                # those three branches already honours; price-based exits are
                # untouched and keep protecting the position.
                # v4.0: no integrator, no book, never stale.
                _rgm_stale = False
                pos_mgr.manage_open_position(
                    chain=ctx.get("chain"),
                    df_1m=ctx.get("df_1m"),
                    # 🔴 r99 — `ms=None` REMOVED. r65 renamed the retired
                    # label kwarg here to `ms=` while DELETING the parameter
                    # from position_manager, so every tick with an open position
                    # raised TypeError into the loop catch-all; after 30 errors
                    # (~7.5 min) the loop sys.exit(1)'d. No position had been
                    # managed since 2026-08-22. Pinned by tests/check_manage_call.py
                    # against the real signature, not a string.
                    df_5m=ctx.get("df_5m"),   # v3.8: 5m FVG trail anchor
                    vol_state=ctx.get("vol"),
                    trend=ctx.get("trend"),   # continuation exhaustion exit
                )
                # r166 — THE MANAGEMENT PLAN: after the exit engine has priced
                # and decided, one row per open record saying what would take
                # it out on the NEXT tick, plus the r66 vector for the open
                # position. Narrates only; the exit engine executes.
                try:
                    from strategy.management import get_management_plan
                    ctx["_open_records"] = pos_mgr.get_open_records()
                    get_management_plan().tick(ctx, ctx["_open_records"], ctx["price"])
                except Exception as _mp_err:                    # noqa: BLE001
                    logger.debug("management plan row skipped: %s", _mp_err)
                # ── A2.2 — the orphan announces itself HERE, once ─────────
                # This branch is the only code that runs while a condor leg is
                # open, so it is the only place the "plan did not survive the
                # restart" warning can actually fire. report_orphaned_plan
                # keeps its own once-latch.
                try:
                    _iron_condor_strategy.report_orphaned_plan(
                        pos_mgr.open_condor_leg_count())
                except Exception:                              # noqa: BLE001
                    pass

                # ── Condor Leg 2 check ────────────────────────────────────
                # If Leg 1 is the open position and Leg 2 is still queued,
                # check_leg_triggers() must run here — not in attempt_new_entry()
                # which is blocked by has_open_position(). This is the only
                # path that allows Leg 2 to fire while Leg 1 is already live.
                # Once both legs are filled the condor is a complete 4-leg
                # position and no further leg firing occurs.
                # ── v4.3: SECOND-LEG WINDOW ──────────────────────────────────
                # When exactly one credit-spread side is open, all four triggers
                # are eligible to fire the complementary side. This is the path
                # that forms the condor — not by plan, but by two independent
                # triggers both becoming active. The gate: _can_open_credit_spread.
                # "A second leg is allowed, never expected." Each vertical already
                # manages as a standalone; if the complement fires, the roll
                # will detect the pair on subsequent ticks and offer the
                # broken-wing adjustment.
                _open_sides = _open_credit_sides()
                # 🔴 r84 — THE LABEL IS STALE AND IT IS NOW GATED SO THE BOARD
                # CAN SAY SO. r42/r43 made `attempt_new_entry` run in BOTH
                # branches of has_open_position(), so "only the second-leg
                # window asks the credit strategies" has been FALSE since;
                # r77 recorded it after the board reported a MARKET CONDITION
                # where there was a crash. Gated here rather than reworded,
                # because the wording is a separate ruling and an unlabelled
                # refusal is the defect in front of us.
                _plan_skip_all("position open — managing; only the second-leg "
                               "window asks the credit strategies", gate="position_open")
                # ── 🔴 r160 — ONE VERTICAL OPEN: ONLY ITS COMPLEMENT, ONLY A SWEEP
                # Operator, 2026-08-27: *"If there is already an active
                # vertical spread of type (call/put) then only a complementary
                # vertical (call/put) SWEEP trade is authorized to fire.
                # Everything else is gated off. The condor doesn't select
                # anything."* The condor AUTHORIZES a side; the sweep's own
                # plan prepares its own level and the sweep's spec fires.
                # `_can_open_credit_spread` still gates the fire (Rules 1/3/4
                # + geometry); Rule 4 reads sweep everywhere now.
                _auth_side, _auth_why = _iron_condor_strategy.authorize(_open_sides)
                if _auth_side:
                    _plan_skip("RunawayContinuation", _auth_why, gate="condor_auth")
                    _plan_skip("TrendCreditSpread", _auth_why, gate="condor_auth")
                    _sl_chain = ctx.get("chain")
                    # OTV4TEST r11 — "the second leg is rich or we don't take it":
                    # the complement must be at least as rich (credit / width) as
                    # the leg already on. No number invented — a comparison.
                    _leg1_rich = 0.0
                    try:
                        for _r in pos_mgr.get_open_records():
                            if _r.get("is_credit_vertical") or _r.get("is_condor_leg"):
                                _w = float(_r.get("spread_width") or 0.0)
                                _c = float(_r.get("credit_received") or _r.get("entry_premium") or 0.0)
                                if _w > 0:
                                    _leg1_rich = max(_leg1_rich, _c / _w)
                    except Exception:                          # noqa: BLE001
                        _leg1_rich = 0.0
                    _sl2 = _safe_strategy("SweepForLeg2",
                        lambda: _sweep_cs_strategy.generate_signal(
                            price_now=ctx["price"],
                            now_et=now_et().strftime("%H:%M"),
                            atr_pct=float(getattr(ctx.get("vol"), "atr_pct", 0.0) or 0.0),
                            chain=_sl_chain,
                            orb_high=ctx.get("orb_high"),
                            orb_low=ctx.get("orb_low"),
                            df_1m=ctx.get("df_1m"),
                            required_side=_auth_side,
                            complement_min_richness=_leg1_rich), ctx)
                    if (_sl2 is not None
                            and _can_open_credit_spread(_sl2.option_side,
                                                        _sl2, ctx["price"], ctx=ctx)):
                        _execute_condor_leg(_sl2, state, ctx)
                elif _auth_why:
                    _plan_skip_all(_auth_why, gate="condor_auth")
                # ══ r43 — ADM.1 CLOSED: ENTRY RUNS WITH A POSITION OPEN ═══
                # Operator, 2026-09-18: *"I want the orb, hunt, breakout &
                # sweep all able to fire & non-competing. We only have one
                # session at a time so we need to maximize every opportunity
                # on these setups. In live trading, we will revert back to
                # hierarchy-based."*
                #
                # 🔴 `has_blocking_position()` IS GONE FROM HERE. It was the
                # last of r35's seven mechanisms still deciding what may open,
                # and on 2026-09-18 it was visibly costing setups: at 10:06:32
                # the board read "slot claimed by RunawayContinuation" for
                # TrendCreditSpread, GEXPinButterfly and ATPButterfly — three
                # strategies not refused on their merits, just crowded out.
                # The admission table's per-type caps replace it (sweep 2,
                # every other type 1), and `blocks`/`blocked_by` are named
                # sets, empty by his ruling.
                #
                # 🔑 THE THREE DIRECT CALLS THAT STOOD HERE ARE GONE, AND r40
                # WAS RIGHT TO REFUSE TO DELETE THEM THEN. They were NOT
                # redundant while `attempt_new_entry` ran a winner-take-all
                # cascade: `_attempt_butterfly` was r161's ADDITIVE EXEMPT path
                # while the in-dispatch butterfly sat behind `elif signal is
                # None:` and COMPETED. r43 removed the cascade, so the
                # in-dispatch path IS the additive path now and the duplication
                # is real rather than apparent. `_attempt_hunt` was being asked
                # TWICE a tick once this gate came out — here and inside
                # `attempt_new_entry` — which is the double-ask r40 named.
                # `_attempt_sweep_on_grant` is NOT redundant (it needs a live
                # handoff grant, constrains the side, and consumes the grant),
                # so it MOVED into `attempt_new_entry` rather than being cut.
                #
                # ⚠️ MANAGEMENT ALREADY RAN ABOVE and is untouched. This branch
                # still manages first; what changed is that it no longer
                # REFUSES to also enter.
                attempt_new_entry(ctx, ms, state)
            else:
                # 🔴 r213 (chunk E) — SAY WHY THE MANAGEMENT PLANS ARE QUIET.
                # They run only in the branch above; with nothing open they are
                # never called and, until now, nothing named them — so
                # CondorManagement, CreditRoll and every `<Strategy>/manage`
                # row reported "dispatch gave no reason" for the whole of a
                # flat session.
                # ⚠️ THIS IS THE SAME FACT THE OTHER BRANCH ALREADY STATES in
                # reverse ("position open — managing; only the second-leg
                # window asks the credit strategies"). One of the two halves
                # had a sentence and the other did not.
                _plan_skip_management("no open position — nothing to manage")
                attempt_new_entry(ctx, ms, state)

            # ── Periodic heartbeat log ────────────────────────────────────
            if state.tick_count % 20 == 0:
                summary = get_trade_logger().today_summary()
                logger.info(
                    f"Tick #{state.tick_count} | "
                    f"{fmt_et_short()} | "
                    f"price=${ctx['price']:,.2f} | "
                    f"adx={ms.adx:.0f} dir={ms.trend_direction} | "
                    f"orb={ctx['orb'].state} | "
                    f"session: {summary.get('wins',0)}W/"
                    f"{summary.get('losses',0)}L "
                    f"pnl=${summary.get('total_pnl',0):+.2f} | "
                    f"{get_risk_manager().status_report()}"
                )

            state.errors_this_hour = max(0, state.errors_this_hour - 1)

        except Exception as e:
            state.errors_this_hour += 1
            logger.error(f"Loop error (#{state.errors_this_hour}): {e}")
            logger.error(traceback.format_exc())
            if state.errors_this_hour > 30:
                logger.critical("Too many errors — shutting down")
                sys.exit(1)

        elapsed = time.time() - tick_start
        # r270 (FILL.2) — the SAME sleep, in 2 s slices: between them the quote watch reads each open position's own
        # quote against its premium stop. r280 (EXIT.5, OT_FLOOR_WATCH=trade, the default): a fresh cross on a Breakout
        # or Runaway ENDS the sleep so the tick runs now; the tick still decides. It never exits or orders; never raises.
        from execution import fill_observers as _fo
        _woke = _fo.sleep_observing(max(0, POLL_INTERVAL_SECONDS - elapsed),
                                    lambda: get_position_manager(state.paper_trading).get_open_records(),
                                    lambda: _obs_chain)
        if _woke:
            logger.info("[floor-watch] %s %s mid %.3f <= stop %.4f (quote %.1fs old) - running the tick %.1fs early",
                        str(_woke.get("trade_id"))[:8], _woke.get("strategy"), _woke.get("mid") or 0.0,
                        _woke.get("level") or 0.0, _woke.get("quote_age_s") or 0.0, _woke.get("early_s") or 0.0)


# Below this many seconds of system uptime, a startup is treated as a fresh
# instance boot (EC2 stop/start or reboot); above it, a service-only restart
# (systemctl restart / crash / deploy while the box was already up).
BOOT_UPTIME_THRESHOLD_S = 180


def _boot_kind() -> str:
    """Classify why the bot just started, for restart self-identification.
    Fresh instance boot vs service-only restart, read from /proc/uptime.
    Best-effort: returns a generic 'restart' if uptime can't be read."""
    try:
        with open("/proc/uptime") as fh:
            uptime_s = float(fh.read().split()[0])
        return "fresh boot" if uptime_s < BOOT_UPTIME_THRESHOLD_S else "service restart"
    except Exception:
        return "restart"


def _describe_position(record: dict) -> str:
    """One-line, self-identifying description of an open row (used by both the
    recovery alert and the stale-orphan sweep alert)."""
    side = str(record.get("option_side", "")).upper()
    if bool(record.get("is_butterfly", 0)):
        return (
            f"BUTTERFLY {side} "
            f"{record.get('lower_strike',0):.0f}/"
            f"{record.get('center_strike',0):.0f}/"
            f"{record.get('upper_strike',0):.0f}"
        )
    if record.get("is_condor_leg") or record.get("strategy") == "IronCondorStrategy":
        return (f"CONDOR {side} "
                f"{record.get('short_strike',0):.0f}/{record.get('long_strike',0):.0f}")
    return f"{side} {record.get('strike',0):.0f}"


def _intraday_reconcile_slot(now):
    """Intraday reconcile slot key, or None outside the window. v3.6: interval
    slots every BROKER_RECONCILE_INTERVAL_MIN minutes (default 10, was a
    hardcoded 30) from 09:30 to 15:45, PLUS dedicated wind-down sweeps at
    r149's EOD_SCHEDULE: 15:45 (resting starts), 15:50 (the ladder), 15:55 (the
    cross — found and adopted before it fires), and 15:57 (the post-cross truth pass; the
    reconcile block runs before the hard-close branch each tick, and the loop
    goes dormant at 16:00, so this is the last guaranteed look of the day)."""
    if now.weekday() >= 5:
        return None
    t = now.time()
    # r268 (DEP.12, mirror of otv4 r478) — the OPEN side stays raw (09:30); every
    # CLOSE-side instant moves to the day's bell: 12:45 / 12:50 / 12:55 / 12:57,
    # dormant at 13:00 on a 13:00 close. The KEY is the moved instant (true ET).
    from utils.time_utils import close_anchored as _ca
    if t < dtime(9, 30) or t >= _ca(dtime(16, 0), now):
        return None
    # r149 (EOD.1) — THE WIND-DOWN SWEEPS FOLLOW THE OPERATOR'S SCHEDULE: one as
    # assignment risk starts resting, one as the debit ladder opens, one AS THE
    # CROSS FIRES (this block runs before the hard-close branch in the same tick,
    # so a short the broker liquidated since 15:50 is found and its surviving long
    # ADOPTED before the cross sends a two-leg order against a leg that no longer
    # exists), and the 15:57 post-cross truth pass. Operator, 2026-09-26: "Agree"
    # (was fixed at 15:45 / 15:50 / 15:57, blind from 15:50 to the cross).
    _eod = sorted({tuple(EOD_RESTING_AT_ET), tuple(EOD_LADDER_AT_ET), tuple(EOD_CROSS_AT_ET), (15, 57)})
    _eod = [(a.hour, a.minute) for a in (_ca(x, now) for x in _eod)]   # r268: the day's bell
    if (t.hour, t.minute) >= _eod[0]:
        hh, mm = max(x for x in _eod if (t.hour, t.minute) >= x)
        return f"{now:%Y-%m-%d} {hh:02d}:{mm:02d}"
    interval = max(1, int(BROKER_RECONCILE_INTERVAL_MIN))
    mins_since_open = (now.hour - 9) * 60 + now.minute - 30
    slot_min = (mins_since_open // interval) * interval
    hh, mm = 9 + (30 + slot_min) // 60, (30 + slot_min) % 60
    return f"{now:%Y-%m-%d} {hh:02d}:{mm:02d}"


def _fetch_close_order_history(records: list) -> list:
    """One order-history read per reconcile pass (never per phantom), covering
    the earliest entry date among the phantom candidates. Fail-safe: any error
    returns [] and the caller books the flagged $0.00 fallback as before."""
    try:
        from data.tasty_client import get_session, get_account, sdk_result
        from datetime import date as _date
        from utils.time_utils import now_et as _net
        start = _net().date()      # r125 — ET date, not the box's UTC one
        for rec in records:
            et = str(rec.get("entry_time", "") or "")[:10]
            try:
                y, m, d = int(et[0:4]), int(et[5:7]), int(et[8:10])
                start = min(start, _date(y, m, d))
            except Exception:
                pass
        session = get_session()
        account = get_account()
        return sdk_result(account.get_order_history(session, page_offset=None,
                                                    start_date=start)) or []   # B0
    except Exception as e:
        logger.error(f"Phantom P&L recovery: order-history read failed ({e}) — "
                     f"phantoms will book flagged $0.00 this pass.")
        return []


# r247 — the option ROOT -> the symbol whose tape holds its settlement price. Only roots measured
# on this account are listed (SPXW, 10-04 dry-run probe); anything else reads its own symbol.
_SETTLE_TAPE = {"SPXW": "SPX"}


def _settlement_spot(symbol: str, expiry: str):
    """r165 (EXP.1): the underlying's 16:00 ET settlement close on `expiry` - the close of the
    last 1m bar that opens before 16:00 that day - from the feed store, read-only. None if the
    store has no bar for that day (the caller then keeps the flagged $0.00)."""
    try:
        import sqlite3
        from datetime import datetime as _dt
        from zoneinfo import ZoneInfo as _Z
        from data.candle_feed import feed_db_path
        # r247 — SPXW (PM-settled weeklies/dailies) settles on the SPX INDEX's 16:00 close: the
        # store keeps the index's tape under "SPX", so an adopted position whose broker underlying
        # is "SPXW" found no bars and booked a flagged $0.00 (SPX-TEST's audit, 2026-10-04).
        symbol = _SETTLE_TAPE.get(str(symbol or "").upper(), symbol)
        y, m, d = (int(x) for x in expiry[:10].split("-"))
        t16 = _dt(y, m, d, 16, 0, tzinfo=_Z("America/New_York")).timestamp() * 1000
        t_open = t16 - 390 * 60 * 1000
        c = sqlite3.connect(f"file:{feed_db_path()}?mode=ro", uri=True)
        try:
            row = c.execute("SELECT close FROM candles WHERE symbol=? AND interval='1m' "
                            "AND ts_epoch_ms>=? AND ts_epoch_ms<? ORDER BY ts_epoch_ms DESC LIMIT 1",
                            (symbol, int(t_open), int(t16))).fetchone()
        finally:
            c.close()
        return float(row[0]) if row and row[0] else None
    except Exception as exc:                                   # noqa: BLE001
        logger.warning("settlement spot unavailable for %s %s: %s", symbol, expiry, exc)
        return None


def _settle_expired_row(rec):
    """r165: (exit_price, pnl_usd, label) for an expired record, or None (keep flagged 0.0)."""
    from execution.broker_reconcile import settle_expired, phantom_pnl
    from utils.time_utils import now_et as _net
    got = settle_expired(rec, _net(), _settlement_spot)
    if got is None:
        return None
    net, label = got
    return net, phantom_pnl(rec, net), label


def _close_phantom_with_recovery(trade_logger, rec, orders, reason: str) -> str:
    """Close one phantom row, booking the REAL fill recovered from broker order
    history when a matching closing order exists (manual close), else the
    flagged $0.00 (expiry/assignment leave no closing order). Returns a short
    description for the alert."""
    from execution.broker_reconcile import match_closing_fills, phantom_pnl
    rid = rec.get("trade_id", "")
    match = match_closing_fills(rec, orders) if orders else None
    if match is not None:
        qty, net = match
        pnl = phantom_pnl(rec, net, closed_qty=min(qty, float(rec.get("contracts", 0) or 0)))
        full = qty >= float(rec.get("contracts", 0) or 0)
        trade_logger.close_phantom(
            rid,
            reason     = f"{reason}_pnl_recovered" + ("" if full else "_partial"),
            exit_price = net,
            pnl_usd    = pnl,
        )
        return f"{rid[:8]} pnl=${pnl:+.2f}@{net}" + ("" if full else f" ({qty:g} of {rec.get('contracts')})")
    # r165 (EXP.1): an EXPIRED position leaves no closing order - settle it at its value.
    settled = _settle_expired_row(rec)
    if settled is not None:
        net, pnl, label = settled
        trade_logger.close_phantom(rid, reason=f"{reason}_{label}", exit_price=net, pnl_usd=pnl)
        return f"{rid[:8]} {label} pnl=${pnl:+.2f}@{net}"
    trade_logger.close_phantom(rid, reason=reason)
    return f"{rid[:8]} pnl=UNKNOWN($0 flagged)"


def _intraday_reconcile(state: BotState, instrument: str):
    """
    LIVE intraday broker-truth check (gated by BROKER_RECONCILE_ENABLED). Detects
    positions the broker closed out from under us DURING the session — especially
    a SHORT leg auto-closed while the long remains — and reacts before the 15:45
    flatten. It only inspects rows WE already manage (it does not adopt brand-new
    broker positions intraday, so a manual trade you place is left alone).

    FAIL-SAFE: a failed or empty broker read changes nothing.
    """
    trade_logger = get_trade_logger()
    try:
        from data.tasty_client import get_open_option_positions
        broker = get_open_option_positions()
    except Exception as e:
        logger.error(f"Intraday reconcile: broker read failed ({e}) — no action.")
        return

    open_rows = trade_logger.get_open_trades_live()
    if not open_rows:
        return
    if not broker:
        logger.warning(
            "Intraday reconcile: broker empty while DB shows open rows — "
            "inconclusive, no action (fail-safe)."
        )
        get_alert_manager().send_reconcile_unavailable_alert(instrument, "empty read (intraday)")
        return

    from execution.broker_reconcile import leg_roles, _adopt_record
    broker_by_sym = {p["symbol"]: p for p in broker if p.get("symbol")}
    broker_syms   = set(broker_by_sym)

    changed  = False
    phantoms = []
    # v3.6: find ALL whole-position phantoms first, then ONE order-history read
    # recovers their real fills (manual closes) — see _close_phantom_with_recovery.
    gone = [rec for rec in open_rows
            if (leg_roles(rec)[0] | leg_roles(rec)[1])
            and not ((leg_roles(rec)[0] | leg_roles(rec)[1]) & broker_syms)]
    history = _fetch_close_order_history(gone) if gone else []
    for rec in open_rows:
        rid = rec.get("trade_id", "")
        short_syms, long_syms = leg_roles(rec)
        all_syms = short_syms | long_syms
        if not all_syms:
            continue

        # whole position gone at the broker -> phantom (real fill recovered
        # from order history when a matching manual close exists)
        if not (all_syms & broker_syms):
            desc = _close_phantom_with_recovery(trade_logger, rec, history,
                                                reason="phantom_intraday")
            phantoms.append(desc)
            changed = True
            continue

        # SHORT gone while a LONG remains -> broker closed our protection
        short_present = bool(short_syms & broker_syms)
        long_present  = bool(long_syms & broker_syms)
        if short_syms and not short_present and long_present:
            trade_logger.close_phantom(rid, reason="short_closed_by_broker")
            surviving = []
            for sym in (long_syms & broker_syms):
                adopted = _adopt_record(broker_by_sym[sym])
                if adopted:
                    trade_logger.log_entry(adopted)
                    surviving.append(_describe_position(adopted))
            changed = True
            get_alert_manager().send_short_leg_closed_alert(
                instrument  = instrument,
                closed_desc = _describe_position(rec),
                surviving   = ", ".join(surviving) or "(long leg)",
            )
            logger.error(
                f"SHORT LEG CLOSED BY BROKER [{instrument}] {_describe_position(rec)} "
                f"-> adopted surviving long(s): {surviving}"
            )

    if phantoms:
        get_alert_manager().send_phantom_closed_alert(instrument, phantoms)
    if changed:
        # re-sync in-memory management to the corrected DB truth
        get_position_manager(state.paper_trading).set_open_positions(
            trade_logger.get_open_trades_live()
        )


def _reconcile_with_broker(state: BotState, live_rows: list,
                           restart_type: str, instrument: str) -> list:
    """
    LIVE-only: reconcile the DB's live rows against the broker, which is the
    source of truth for whether a position EXISTS. Returns the final list of
    records to manage (kept DB rows + adopted broker positions). Journals adopts,
    closes phantoms, and alerts.

    FAIL-SAFE: on ANY broker read failure — or an empty read while the DB still
    shows live rows — return the DB rows unchanged and close NOTHING. A bad or
    empty read must never be interpreted as "the broker is flat", which would
    close real positions.
    """
    trade_logger = get_trade_logger()
    try:
        from data.tasty_client import get_open_option_positions
        broker = get_open_option_positions()
    except Exception as e:
        logger.error(f"Broker reconcile unavailable ({e}) — DB-only recovery, closed nothing.")
        get_alert_manager().send_reconcile_unavailable_alert(instrument, "read failed")
        return live_rows

    if not broker:
        if live_rows:
            logger.warning(
                "Broker returned NO option positions while the DB shows live rows — "
                "inconclusive; DB-only recovery, closed nothing."
            )
            get_alert_manager().send_reconcile_unavailable_alert(instrument, "empty read")
        return live_rows

    from execution.broker_reconcile import build_plan
    plan = build_plan(broker, live_rows)

    # Phantoms: open in our DB but absent at the broker -> close (broker wins).
    # v3.6: recover the REAL fill from order history (covering back to each
    # phantom's entry date — a manual close from a prior day is still found).
    if plan.close_phantom:
        by_id   = {r.get("trade_id", ""): r for r in live_rows}
        gone    = [by_id[t] for t in plan.close_phantom if t in by_id]
        history = _fetch_close_order_history(gone)
        descs   = []
        for tid in plan.close_phantom:
            rec = by_id.get(tid)
            if rec is None:
                trade_logger.close_phantom(tid)
                descs.append(f"{tid[:8]} pnl=UNKNOWN($0 flagged)")
                continue
            descs.append(_close_phantom_with_recovery(
                trade_logger, rec, history, reason="phantom_closed_at_broker"))
        get_alert_manager().send_phantom_closed_alert(instrument, descs)

    # B1 (r465): kept rows whose legs or quantities disagree with the broker.
    for mm in getattr(plan, "mismatch", []) or []:
        _desc = (f"{mm.get('trade_id','')[:8]} missing={mm.get('missing')} "
                 f"qty={mm.get('quantity')}")
        logger.warning(f"RECONCILE MISMATCH [{instrument}] {_desc} — kept and managed; check the broker")
        try:
            get_alert_manager()._send(f"⚠️ {instrument} RECONCILE MISMATCH — {_desc}. "
                                      f"Kept and managed; the DB and the broker disagree.")
        except Exception:                                      # noqa: BLE001
            pass

    # Adopts: journal into our system of record + alert (loud for a lone short).
    anomaly_ids = set(plan.anomalies)
    for rec in plan.adopt:
        trade_logger.log_entry(rec)
        get_alert_manager().send_adopted_alert(
            instrument    = instrument,
            position_desc = _describe_position(rec),
            contracts     = int(rec.get("contracts", 0) or 0),
            entry_premium = float(rec.get("entry_premium", 0) or 0),
            is_short      = bool(rec.get("is_short_position")),
            anomaly       = rec.get("trade_id") in anomaly_ids,
            restart_type  = restart_type,
        )
        logger.warning(
            f"ADOPTED [{instrument}] {_describe_position(rec)} "
            f"({'short' if rec.get('is_short_position') else 'long'}) "
            f"id={rec.get('trade_id','')[:8]}"
        )

    _check_exercise_footprint(instrument)                     # r165 (EXP.1)
    return list(plan.keep) + list(plan.adopt)


def _check_exercise_footprint(instrument: str) -> list:
    """r165 (EXP.1): LIVE share positions in the box's instrument are what an exercise or
    assignment leaves behind - page them. Fail-safe: a failed read logs and pages nothing."""
    try:
        from data.tasty_client import get_open_equity_positions
        eq = [e for e in get_open_equity_positions()
              if str(e.get("symbol", "")).upper() == str(instrument).upper()]
    except Exception as exc:                                   # noqa: BLE001
        logger.error("exercise footprint check: share read failed (%s) - could not look", exc)
        return []
    if eq:
        px = None
        try:
            from data.market_data import fetch_quote
            px = fetch_quote(instrument)
        except Exception:                                      # noqa: BLE001
            px = None
        notional = sum(float(e.get("quantity", 0)) for e in eq) * float(px or 0)
        logger.error("SHARES IN THE ACCOUNT %s: %s", instrument, eq)
        get_alert_manager().send_exercise_footprint_alert(instrument, eq, notional)
    return eq


def _recover_open_position(state: BotState, restart_type: str = ""):
    """
    Called immediately on every start, restart, and reboot, before the main loop.

    Step 1 — reconcile only TRULY EXPIRED orphans. A position's liveness is its
    EXPIRY, not its entry date: this bot also trades weeklies (nearest expiry can
    be days out), so a row entered on a prior session may still be a live
    contract today. Only rows whose expiry has actually passed are dead; those
    are closed in the DB up front so nothing manages a ghost.

    Step 2 — resume EVERY still-live open row (0DTE or weekly). If a position
    survived overnight (a weekly held, or one that leaked past the 15:45 flatten
    / a hard kill), it is identified and managed immediately, and flagged as
    CARRIED so it can't be missed.
    """
    pos_mgr = get_position_manager(state.paper_trading)
    trade_logger = get_trade_logger()
    instrument = os.environ.get("OT_INSTRUMENT", INSTRUMENT)

    # ── Step 1: sweep only genuinely EXPIRED orphans ─────────────────────────
    expired = trade_logger.close_expired_open_trades(settle=_settle_expired_row)   # r165
    if expired:
        descs = [_describe_position(r) for r in expired]
        logger.warning(
            f"Startup: auto-closed {len(expired)} EXPIRED orphan(s) [{instrument}]: "
            f"{', '.join(descs)}"
        )
        get_alert_manager().send_orphan_cleared_alert(
            instrument=instrument, descs=descs, restart_type=restart_type
        )

    # ── Step 2: resume every still-live (unexpired) position ─────────────────
    live = trade_logger.get_open_trades_live()
    _shadow_resume()                                    # r57 (TCS.LOG1): the shadow store, Steps 1-2, no broker

    # LIVE ONLY, and only when explicitly enabled: the broker is the source of
    # truth for what's actually open. (Paper has no broker to query; and even on
    # live this stays OFF until OT_BROKER_RECONCILE=True, so it can't fire before
    # get_open_option_positions() has been verified on a live box.)
    # r495 / B4 — a working order left by the previous process is invisible to it (order_guard is
    # in memory; B1 adopts positions, not orders). Cancel this instrument's untracked ones FIRST,
    # so a part-fill is adopted by the reconcile below; a failed sweep blocks entries, never exits.
    if not state.paper_trading:
        from execution import order_guard as _guard
        _guard.boot_sweep()

    if not state.paper_trading and BROKER_RECONCILE_ENABLED:
        live = _reconcile_with_broker(state, live, restart_type, instrument)

    if not live:
        logger.info("Startup position check: no live positions to resume.")
        return

    pos_mgr.set_open_positions(live)

    # The recovery/carried alert covers DB-PLANNED rows only; adopted positions
    # already got their own adopted alerts inside the reconcile.
    db_planned = [r for r in live if r.get("strategy") != "ADOPTED"]
    if not db_planned:
        logger.info("Recovery: only adopted positions to manage (already alerted).")
        return

    # A position whose entry ET date is before today survived a session boundary.
    today_et = now_et().strftime("%Y-%m-%d")
    carried  = any(
        trade_logger._et_date(r.get("entry_time", "")) not in ("", today_et)
        for r in db_planned
    )

    descs         = [_describe_position(r) for r in db_planned]
    position_desc = " + ".join(descs)
    contracts     = sum(int(r.get("contracts", 0) or 0) for r in db_planned)
    total_cost    = sum(float(r.get("total_cost", 0) or 0) for r in db_planned)
    lead          = db_planned[0]
    entry_prem    = float(lead.get("entry_premium", 0) or 0)
    strategy      = lead.get("strategy", "")
    trade_ids     = ",".join(r.get("trade_id", "")[:8] for r in db_planned)

    logger.warning(
        f"⚠️  {'CARRIED' if carried else 'LIVE'} POSITION RECOVERED ON STARTUP "
        f"[{instrument}]: {position_desc} x{contracts} "
        f"entry=${entry_prem:.2f} total=${total_cost:.2f} "
        f"strategy={strategy} id={trade_ids} ({restart_type or 'restart'})"
    )
    get_alert_manager().send_recovery_alert(
        instrument   = instrument,
        position_desc = position_desc,
        contracts    = contracts,
        entry_premium = entry_prem,
        total_cost   = total_cost,
        strategy     = strategy,
        restart_type = restart_type,
        carried      = carried,
    )
    logger.info(
        f"Position recovery complete — main loop will manage "
        f"{position_desc} from first tick."
    )



def _fetch_orb_range(instrument: str = "") -> bool:
    """Fetch and write orb_range.json via the standalone get_orb_range.py.

    get_orb_range.py is the single source of truth. It ALWAYS writes the last
    valid range, tagged with one of three states, and returns it via exit code:
        0 = ESTABLISHED (today's, closed) -> return True
        2 = IN_PROGRESS (opening candle forming) -> return False (retry)
        3 = EXPIRED (carrying last RTH range)    -> return False (retry)
        1 = hard error                            -> return False

    Returns True ONLY when today's range is ESTABLISHED, so callers keep polling
    across IN_PROGRESS/EXPIRED until today's candle closes — while status.py and
    the engine always have the last valid range to read in the meantime.

    r47 (ORB.9): "no 5m data returned" OUTSIDE RTH (before 09:30, after the day's bell, a weekend or holiday -
    utils.time_utils.is_rth, the calendar and the bell) is the expected state, not a fault: it logs at INFO.
    Inside RTH it stays a WARNING; any other failure is a WARNING at any hour.
    """
    try:
        import subprocess as _sp
        _symbol = instrument or os.environ.get("OT_INSTRUMENT", INSTRUMENT)
        # main.py lives in the install root; the script is a sibling package.
        _install_dir = os.path.dirname(os.path.abspath(__file__))
        _orb_script = os.path.join(_install_dir, "analysis", "get_orb_range.py")
        _result = _sp.run(
            [sys.executable, _orb_script, _symbol],
            capture_output=True, text=True, timeout=30
        )
        if _result.returncode == 0:
            _line = _result.stdout.splitlines()[0] if _result.stdout.strip() else ""
            logger.info(f"ORB range: {_line}")
            return True
        if _result.returncode == 2:
            logger.debug("ORB range: IN_PROGRESS — today's opening candle forming")
        elif _result.returncode == 3:
            logger.debug("ORB range: EXPIRED — carrying last RTH range, awaiting today's")
        else:
            _err = _result.stderr.strip()
            if "no 5m data returned" in _err and not is_rth():    # r47 (ORB.9)
                logger.info(f"ORB range: no 5m bars outside RTH (expected before the open and after "
                            f"the bell; retried from the next 09:30): {_err}")
            else:
                logger.warning(f"ORB range fetch failed: {_err}")
        return False
    except Exception as e:
        logger.warning(f"ORB range fetch skipped: {e}")
        return False


def main():
    # 🔴 r146 — NO GUESSED SYMBOL. config.INSTRUMENT is "UNSET" when OT_INSTRUMENT is
    # absent; trading a made-up symbol - or quietly QQQ, as before - is refused
    # here, FIRST, before any login or alert (Restart=always must not page).
    if INSTRUMENT == INSTRUMENT_UNSET:
        sys.stderr.write("CRITICAL: OT_INSTRUMENT is not set for this process - refusing to "
                         "start. Set Environment=OT_INSTRUMENT=<SYMBOL> on the unit "
                         "(configure.sh item 1).\n")
        sys.exit(78)
    # 🔴 r175 (SYM.1) — NOR A SYMBOL OFF THE LIST: its strike step would be a
    # silent $1 default. The list is config.STRIKE_INCREMENTS (configure.sh item 1).
    if not INSTRUMENT_LISTED:
        sys.stderr.write("CRITICAL: OT_INSTRUMENT=%s is not in config.STRIKE_INCREMENTS - "
                         "refusing to start. Pick a listed symbol (configure.sh item 1) or "
                         "add it with its measured strike step.\n" % INSTRUMENT)
        sys.exit(78)
    service_mode = "--service" in sys.argv

    if service_mode:
        session_config = SessionConfig(
            paper_trading      = PAPER_TRADING,
            instrument         = INSTRUMENT,
            risk_per_trade_usd = RISK_PER_TRADE_USD,
            notes              = "systemd auto-start"
        )
        logger.info(
            f"Service mode: {'PAPER' if PAPER_TRADING else 'LIVE'} | "
            f"{INSTRUMENT} | "
            f"risk=${RISK_PER_TRADE_USD:.0f}/trade | "
            f"catastrophic_loss_cap=${DAILY_LOSS_LIMIT_USD:.0f} realized net"
            # r201 — WHICH BUDGET, AND WHETHER ANYBODY CHOSE IT. An
            # unconfigured box trades 1-lot on an index name, which reads as a
            # defect rather than a config gap unless the banner says otherwise.
            f" · orb_budget=${ORB_BUDGET_USD:.0f}"
            f"{' (DEFAULT — not set for this box)' if ORB_BUDGET_IS_DEFAULT else ''}"
            # r161 — the ramp is MIN (risk per trade) to MAX (orb_budget), and
            # each switch says whether that trade rides it or sizes flat.
            f" · scaling ORB={'on' if SCALE_ORB else 'OFF'}"
            f" BRK={'on' if SCALE_BREAKOUT else 'OFF'}"
            f" VOLT={'on' if SCALE_VOLT else 'OFF'}"
            # r234 — the contract-price scale ORCS's wing and credit floor ride.
            f" · contract_scale={CONTRACT_SCALE:g} ({CONTRACT_SCALE_SOURCE})"
            # r235 — whether ORCS is armed, so no one has to read the unit.
            f" · ORCS={'on' if ORCS_ENABLED else 'OFF'}"
            # r253 (RUNW.2) — the pin gate and Runaway's end in force, READ here rather than
            # inferred from silence (SPX-TEST, 10-05: neither was printed anywhere).
            f"{_banner_dials()}"
        )
        if ORB_RISK_ENV_IGNORED:
            logger.warning(
                "OT_ORB_RISK_USD=%s is set on this unit and is NO LONGER READ "
                "(r161: the ramp START is risk per trade, $%.0f). Remove it with "
                "configure.sh item 2.", ORB_RISK_ENV_IGNORED, RISK_PER_TRADE_USD)
    else:
        session_config = _interactive_startup()
    _announce_plan_states()                                     # r303 (PSTATE.1)

    # Initialize TastyTrade client
    # TastyTrade session initializes lazily on first use via get_session()

    # Initialize risk manager with session params
    risk_mgr = init_risk_manager(
        risk_per_trade = session_config.risk_per_trade_usd,
        paper_trading  = session_config.paper_trading
    )

    state = BotState()
    state.paper_trading = session_config.paper_trading

    # L2.5: warm-start the conviction integrator from its last snapshot so a
    # mid-session restart doesn't reset the book to zero (the NVDA-restart
    # lesson). If the snapshot is stale/absent, load() returns False and the
    # book stays cold — the first few ticks re-warm it, and stale=True keeps it
    # v4.0: no integrator book to reload at startup. v3 persisted conviction
    # across restarts so a mid-session bake did not reset it; there is nothing
    # to persist now.

    # Pre-fetch macro data
    logger.info("Fetching macro data...")
    get_macro_manager().get(force=True)

    # Classify this start (fresh instance boot vs service restart) so every
    # alert below can self-identify what kind of restart just happened.
    restart_type = _boot_kind()

    get_alert_manager().send_startup_alert(
        paper      = session_config.paper_trading,
        instrument = session_config.instrument,
        risk_usd   = session_config.risk_per_trade_usd,
        restart_type = restart_type,
    )

    # ── Graceful shutdown alert on SIGTERM/SIGINT ────────────────────────────
    # systemctl stop/restart sends SIGTERM. Without this handler the bot
    # just dies silently with no Telegram notification.
    def _handle_shutdown(signum, frame):
        reason = "systemctl stop/restart" if signum == signal.SIGTERM else "manual interrupt"
        # 🔴 r67 / BOX.9 — THAT STRING WAS EVERY ROUTE DOWN. A hand stop, a bake
        # and the midnight backstop all arrive as SIGTERM, so the emergency
        # channel printed one sentence for three causes and the operator had to
        # infer which from the timestamp (§0.5). The automated paths now STAMP
        # themselves — `warehouse/midnight_halt.py` and `devtools.sh` bake() —
        # and a stop with no stamp is a HAND stop, which is the honest default
        # and needs no new machinery on the path a human drives.
        # ⚠️ FAILS CLOSED ONTO THE OLD WORDING: absent, stale, malformed or
        # unreadable all yield None, and a mislabelled shutdown would be worse
        # than an unlabelled one.
        if signum == signal.SIGTERM:
            try:
                from utils.shutdown_cause import label
                reason = label(reason)
            except Exception:                                   # noqa: BLE001
                pass
        logger.info(f"Shutdown signal received ({reason}) — sending alert and exiting")
        try:
            get_alert_manager().send_shutdown_alert(
                instrument = session_config.instrument,
                reason     = reason
            )
        except Exception as e:
            logger.error(f"Failed to send shutdown alert: {e}")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT,  _handle_shutdown)

    # ── CRITICAL: Recover any open position immediately ─────────────────────
    # Runs before the main loop on every start, restart, or reboot.
    # If the bot went down with money on the line, we resume managing
    # that position within seconds — not waiting for the first loop cycle.
    _recover_open_position(state, restart_type)

    # ── Fetch ORB range on start/restart ─────────────────────────────────────
    # Runs unconditionally: get_orb_range.py always writes the last valid range
    # tagged ESTABLISHED / IN_PROGRESS / EXPIRED, so status.py and the ORB engine
    # always have a range to read (e.g. Friday's EXPIRED range on a Monday
    # pre-open restart). It is safe pre-open because the engine only ARMS on an
    # ESTABLISHED/today range. We latch only when today's range is ESTABLISHED;
    # otherwise handle_session_reset() keeps polling from the open.
    state.orb_range_established_today = _fetch_orb_range(
        os.environ.get("OT_INSTRUMENT", INSTRUMENT)
    )

    logger.info(
        f"OptionsBot ready | "
        f"{'PAPER' if state.paper_trading else 'LIVE'} | "
        f"{session_config.instrument} | "
        f"risk=${session_config.risk_per_trade_usd:.0f}/trade | "
        f"poll={POLL_INTERVAL_SECONDS}s"
    )

    main_loop(state)


def _interactive_startup() -> SessionConfig:
    """Interactive startup prompt for manual launch."""
    print("\n" + "="*50)
    print("  options_trader v1.0 — Startup Configuration")
    print("="*50)

    # Instrument
    print("\nInstrument:")
    print("  1. QQQ  (Nasdaq ETF, $1 strikes)")
    print("  2. SPY  (S&P 500 ETF, $1 strikes)")
    print("  3. SPX  (S&P 500 Index, $5 strikes)")
    choice = input("Select [1/2/3, default=1]: ").strip() or "1"
    instrument = {"1": "QQQ", "2": "SPY", "3": "SPX"}.get(choice, "QQQ")

    # Risk per trade
    risk_input = input(f"\nRisk per trade in $ [default=200]: ").strip() or "200"
    try:
        risk_usd = float(risk_input)
    except ValueError:
        risk_usd = 200.0

    # Paper vs live
    mode_input = input("\nTrading mode [P=Paper/L=Live, default=P]: ").strip().upper() or "P"
    paper = mode_input != "L"

    print(f"\n{'─'*50}")
    print(f"  Instrument:    {instrument}")
    print(f"  Risk/trade:    ${risk_usd:.0f}")
    print(f"  Mode:          {'PAPER' if paper else '⚠️  LIVE'}")
    print(f"  Loss cap:      ${DAILY_LOSS_LIMIT_USD:.0f} realized → no new entries until back under")
    print(f"  ORB budget:    ${ORB_BUDGET_USD:.0f} per setup"
          f"{'  (DEFAULT — not set for this box)' if ORB_BUDGET_IS_DEFAULT else ''}")
    print(f"{'─'*50}")

    if not paper:
        confirm = input("\n⚠️  LIVE TRADING — type YES to confirm: ").strip()
        if confirm != "YES":
            print("Defaulting to paper trading.")
            paper = True

    from utils.time_utils import fmt_et_full
    return SessionConfig(
        paper_trading      = paper,
        instrument         = instrument,
        risk_per_trade_usd = risk_usd,
        confirmed_at       = fmt_et_full()
    )


if __name__ == "__main__":
    main()