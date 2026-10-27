"""
execution/exit_engine.py  v5.4
v5.4  2026-10-27  OTV5 r44 (BAR.1) — EVERY CLOSED-CANDLE READ FINDS THE LAST BAR CLOSED BY TIME. BOSTracker.update, the
      ORB/Breakout structure stop, the hunt's target wick, the runaway/hunt thesis line and its fizzle bars, and VOLT's
      5m structure stop (bar_s 300) read iloc[-2] / iloc[:-1], one bar stale on a tick before the new bar's first row
      exists (META 2026-10-27 3f2b1372: a Breakout short fired 10:10:00 ET on the 10:08 bar while 10:09 had already closed back inside the 623.20 edge). They read utils.time_utils.closed_pos / closed_part on this module's now_et(); unchanged when the
      forming row is present. The fizzle's pull (lows/highs.iloc[:-1] inside the closed bars) is not a forming-bar read
      and is untouched. GATE tests/check_last_closed_bar.py C4.
v5.3  2026-10-27  OTV5 r42 (EOD.3) — THE 15:55 ESTIMATE PRICES EACH LEG TO ITS OWN EXPIRY. _eod_best_case gave every leg
      the 5 minutes left to TODAY's 16:00, so a leg expiring on a later day was priced at its intrinsic value. CVX
      2026-10-27 (006f6eca, Breakout long 8 x 10-30 230P): valued 1.26 at spot 228.74, _eod_determined called that
      "settled", and paper booked 1.25 against a 3.70 / 4.85 quote: -$1,448 instead of about +$976 at the mark. Each
      leg now gets the days to its own expiry plus those 5 minutes, so a multi-day long keeps its time value, is not
      "settled", and books at the mark (EOD.1's rule). 0DTE pricing is unchanged. The bug was born at OTV4TEST r149
      (2509cc7, 2026-09-26). Gate tests/check_eod_expiry_value.py E1-E5.
v5.2  2026-10-26  OTV5 r36 (EOD.2) — FillResult.held: the paper EOD close HELD to the 15:55 cross says so (held=True), so
      the position manager can tell an intended hold from a failed exit. The hold itself is unchanged.
v5.1  2026-10-25  (DOC.31) — VOLT'S EXIT TEXT NAMES THE FRAME IT READ, AND _evaluate_volt'S DOCSTRING DESCRIBES THE STOP
      AND R IT USES. Both VOLT reasons said "1m close" while the close is frame.iloc[-2] of df_5m (the operator's
      2026-09-21 frame ruling): volt_structure_stop and volt_trail_stop now say "5m close". The docstring still described
      `underlying_stop` as "the 3x5m structural extreme" and R as |entry-stop|; since OTV4TEST r72 the stop IS the entry
      (a 5m close back through it) and R is the signal bar's range, read from underlying_target. Strings only; no logic
      changes. Gate tests/check_volt_exit_text.py T1-T4.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.45 2026-10-24  OTV4TEST r317 (STALE.1, D1) — NO HANDOFF EXIT WHEN THE ENTRY TIME IS UNKNOWN. _entry_epoch() returns 0.0
      for a record whose entry_time is missing or unreadable, and _rejected_handoff() then asked latest_rejection(sym,
      0.0): ANY REJECTED ever written (any day, or a seeded row) could close a live ORB/Runaway/Hunt. Found by
      1-REPORTER's staleness inventory (MSG-1REP-1024-35), verified here; the operator, 2026-10-24 16:04 ET: "Yes to
      all, on the latent question". Now an unknown entry time hands off nothing and says so once per trade.
      tests/check_handoff_entry_time.py.
v4.44 2026-10-18  OTV4TEST r295 (LIVE.2) — the live close's broker poll touches the heartbeat on every iteration
      (utils.heartbeat.touch); with LIVE_FILL_DEADLINE_SECONDS at 8 (config v4.69) a five-position ladder is ~70 s
      and never silent, where 5 x 36 s was >180 s = the watchdog's SIGKILL at ~15:53. Audit 2026-10-18 C2.
v4.43 2026-10-18  OTV4TEST r294 (EXIT.6; MIRROR OF otv4 r493 1c60b69, hunks VERBATIM) — A RESTART KEEPS THE LOCKED TRAIL.
      _seed_trail_from_record re-armed _trail_active only for ADOPTED, so for every other strategy the first tick at or
      above the activation level took _update_trail's first-activation branch and wrote the activation seed (here: the
      structure floor for Breakout, entry x 1.25 otherwise) over the recovered level, which position_manager then
      persisted. Reproduced 10-18: Breakout 1.00, peak 2.00, trail 1.50 persisted; a fresh engine at 1.45 HELD at
      1.0875. The seed now arms the flag wherever the uninterrupted engine would be armed (_trail_was_armed); the
      uninterrupted path is unchanged. Audit 10-18 A2; the operator, 2026-10-18 16:25 ET: "Yes to both".
v4.42 2026-10-18  OTV4TEST r291 (PARK.2) — THE PARK LOCK ARMS ON THE BID, AND A RESTART RE-ARMS FROM A COLUMN THAT EXISTS.
      r288's _evaluate_park read `mfe_premium` for the restart re-arm; trade_logger writes it only in log_exit, so a
      rehydrated open PARK had NULL and the +60%/+20% lock was forgotten (audit 10-18 A3). And `or mfe >= arm` ran every
      tick on the in-memory mark MFE, arming half a spread early vs the study's bid rule. Now: one seed per process from
      max_premium_seen (per-tick, SELECT * rehydrates it), then bid-only. check_park K10a2/K10b drive both through
      get_open_trades() on a scratch trades.db.
v4.41 2026-10-18  OTV4TEST r290 (HUNT.10) — THE HUNT'S STRUCTURE BACKSTOP JUDGES r285's LINE. _evaluate_orb step 2 read
      `underlying_stop` (the Hunt's ENTRY BOUNDARY) with no band, after _runaway_thesis_exits had already held the trade
      on the farther 5m line: QQQ 2026-10-15 ddeb0fab, line 721.15, exited "orb_structure_stop 717.03 > 717.01", -148.
      Found by the 2026-10-18 audit (A1). Step 2 now asks _hunt_line() for a LiquidityHunt record (log/off keep the
      boundary, as before). tests/check_hunt_stop5m H9a-c drive evaluate() - the front door - incl. the 10-15 replay.
v4.40 2026-10-18  OTV4TEST r288 (PARK.1) — PARK GETS ITS OWN EVALUATOR. The operator, 2026-10-17 18:21 ET: "Trade it ...
      Call it PARK"; "Are you sure we want to hold decaying zero DTE so long ...? Consider or study a delta based exit."
      _evaluate_park(), FIRST MATCH WINS: (1) the +60% / +20% LOCK on the BID (armed once bid >= entry x 1.60 - or, after a
      restart, the persisted mfe_premium mark - then out when bid <= entry x 1.20); (2) the DELTA FLOOR |delta| <= 0.30
      from 11:30 ET (PARK.X, picks sha 85dca420: QQQ +10,550 -> +11,786, SPX +13,320 -> +16,370, every winner kept); an
      unreadable delta (None or 0.0) HOLDS; (3) the 15:45 close; (4) the EOD schedule as a backstop. NO premium stop and
      NO trail - none applies to PARK. Every PARK exit writes data/counterfactual/park_exit.jsonl (bid, mark, delta, the
      contract) so Saturday can price what holding to 15:45 would have done.
v4.39 2026-10-14  OTV4TEST r285 (HUNT.8) — THE HUNT'S THESIS LINE IS THE 5m SWING, NOT ONLY ITS BOUNDARY. A 1m close back
      through the entry boundary killed right-way hunts inside one minute of noise (10-14 09:58 short: dead 10:03 on 737.28
      vs 736.90; QQQ fell to 732.4). _hunt_line() makes the line the FARTHER of underlying_stop (the boundary, unchanged for
      ENT.1) and strategy.breakout_plan.swing_5m_stop as of the ENTRY time (last 3 closed RTH 5m bars), read from the feed
      store each time (a restart decides the same); unreadable -> the boundary. OT_HUNT_STOP5M=trade|log|off (unset = trade).
      COUNTERFACTUAL data/counterfactual/hunt_stop.jsonl: the line chosen per trade, and the tick the OLD boundary would have
      ended it (mark, underlying). MEASURED /var/tmp/structure_hold_1014/v2_hunt.txt (n21, 1m close): -16.3 R -> -5.5 R, the
      1m-losing days -36.0 R -> -15.1 R. The operator, 2026-10-14 11:47 ET: "Yes, we have to". tests/check_hunt_stop5m.py.
v4.38 2026-10-06  OTV4TEST r256 (F3, MIRROR OF otv4 r475 5270801, WA 38.9) — NO MARKET CLOSE FOR WANT OF A MARK BEFORE THE CROSS. A single-leg close with no mark (None or <= 0) sent a MARKET order at any hour - on a thin 0DTE contract that fills at whatever the bid is. Now, before the cross (hard_close_order_mode != "market"), it posts NOTHING, pages once per trade ("nomark"), and the caller retries next tick; at/after the cross it still crosses. force_market is unchanged. Live-only (reached only through _submit_live_close). The logic and decision points are otv4's verbatim; THE ONE DIFFERENCE IS THE CLOCK, read from this tree's limit_ladder: the cross is 15:55 here (EOD.1, r149), 15:45 on mainline - so the messages say "before the cross". _confirm_and_book_live_exit_pass returns unconfirmed "no mark before the cross; nothing posted" so the generic SUBMIT FAILED page does not also fire. Pinned by tests/check_no_mark_close.py (N1 N2 N3b N5 born red on cd613cb).
v4.37 2026-10-04  OTV4TEST r248 (LIVE.1 BBK.1, MIRROR OF otv4 r470 b457102, WA 38.2) — a single-leg BUY_TO_CLOSE is priced as a BUY: _close_single_leg passed the literal "sell" to _exit_limit, so an adopted short's buy-back walked down from the ask and snapped up - paying above its mark (measured: 1.15 then 1.14 against a 1.10 mark; floor 1.15 vs 1.10). The side now follows the action. Diff verbatim; reviewed here BEFORE mainline landed it (the operator: "Have reporter do the buy-back & run the fix by you for a sanity check").
v4.36 2026-10-04  OTV4TEST r245 (LIVE.1 B3, MIRROR OF otv4 r467 b32c73b, WA 38.2) — A PARTIAL LIVE EXIT SURVIVES A RESTART: the close's state (filled portions, the working order id) is saved to the row's new live_exit_state column after the submit and after every pass, and loaded first; a restart resumes the working order or submits only the REMAINDER, and the booked price is the weighted average of every fill. Code hunks applied verbatim; getsource sha256[:16] of _exit_state_load / _exit_state_save / _confirm_and_book_live_exit identical to b32c73b (a71ca216 / b44de96e / 1819bebc).
v4.35 2026-10-04  OTV4TEST r242 (LIVE.1 B0, MIRROR OF otv4 r463 c912ce7, WA 38.2) — every Account call goes through tasty_client.sdk_result: on tastytrade 13.x the Account methods are coroutines and a bare call placed and closed NOTHING live (paper never calls them). Hunks applied verbatim from c912ce7.
v4.34 2026-10-03  OTV4TEST r230 (PREM.5) — ORCS LEGS TAKE THE CONDOR'S EXITS, VERBATIM. The operator, 2026-10-03 21:21 ET: "On rolling/defending the ORCS, adopt the condor logic verbatim." _evaluate_condor_leg no longer returns early for an ORCS leg: the stop is suppressed while its other side is open, a LONE leg stops at credit + 15% of risk, the nickel closes it, the final-form floor applies after a roll. r204's 'held to the close and nothing else' is superseded.
v4.33 2026-10-03  OTV4TEST r221 (UTIL.1) — _find_1m_fvgs calls utils.math_utils.find_fvgs (its own copy of the loop is gone; same
      gaps, same order). The runaway's vwap_recross event names its number honestly in the code (entry_vwap: a
      since-entry mean, NOT the session VWAP); the event label and the arithmetic are unchanged.
v4.32 2026-10-03  OTV4TEST r219 (TICK.2, SHARED - MIRROR OF otv4 r461 a407323) — A SINGLE-LEG CLOSE POSTED AT THE MARK LANDS ON THE
      VENUE GRID. _exit_limit priced a floor-policy close and the walk's fallback with limit_at_mark(mark,
      floor=tick) and NO symbol, so the limit was only rounded to cents: an invalid increment LIVE on a
      nickel or dime grid. For structure "single" it now passes the symbol, side and quote, so limit_at_mark
      snaps through execution/tick_size exactly as the walk path and the entry ladder already do. Spreads,
      flies and the end-of-day resting close are unchanged. Found here (MSG-1003-23), narrowed and authored
      on mainline by 1-REPORTER; the operator's yes 2026-10-03. Gate tests/check_exit_single_grid.py G1-G4.
v4.31 2026-10-03  OTV4TEST r209 (EXIT.4) — (1) _exit_policy READS THE DECLARED PRICING a management intent stamped on the
      record (floor / walk) when it belongs to THIS reason; the substring table remains only for exits this
      engine decides itself. No price changes: management.EXIT_PRICING is the old outcome written down.
      (2) RUN.10: the "would-have-floored (HELD)" branch is the HUNT's alone. For the Runaway it was dead code -
      its management plan closes at the same 20% floor first - and the operator, 2026-10-03, on the replay
      (holding cost 499 more on the 9 stopped trades, none recovered): "runaway, concur". The Hunt still holds.
v4.30 2026-10-03  OTV4TEST r204 (PREM.2) — ORCS IS HELD TO THE END-OF-DAY CLOSE AND NOTHING ELSE. _evaluate_condor_leg returns
      HOLD for strategy OpeningRangeCreditSpread right after the scheduled-close check: no lone stop, no breach,
      no nickel. The operator, 2026-10-03: "I want to paper trade it Monday"; the spec (PLAN_SPEC §41.1) is
      hold to the close - a stop at the short strike was measured and was worse in every cell.
v4.29 2026-10-03  OTV4TEST r190 (AUD.1, SHARED WITH otv4 CND.11 + TICK.1) — TWO FIXES FROM THE 10-03 AUDIT.
      (1) _condor_sibling_open's except returns `default`, not True. Both stop paths (TCS and the credit
      vertical) ask default=False so a probe error keeps the stop ARMED on a lone vertical; they got True,
      read "hedged", and the stop was SUPPRESSED. Function text verbatim with otv4 (getsource 2df83d77...).
      (2) An SPX/SPXW SINGLE-LEG close limit at or above $3.00 rounds to $0.10 (_round_to_tick(...,
      single_leg=True), only at _close_single_leg). Spreads, flies, XSP and every other symbol unchanged;
      nothing changes on a QQQ box. Pinned by tests/check_condor_sibling_default.py and tests/check_spx_tick.py.
v4.28 2026-09-30  OTV4TEST r182 (EXIT.3) — MESSAGE ONLY: A BREAKOUT NO LONGER LOGS "has no exit route
      ... Add a branch." That line is false for Breakout and has been since 2026-09-21: the operator
      ruled its exit stays as it is ("That exit is fucking solid. I actually don't want to change
      whatever it was using") and its management plan acts on it before this dispatch (EXIT.3). It
      logged 118 times and, since r171, woke the agent as UNUSUAL every day a Breakout traded. For
      Breakout the fall-through now logs, once per trade at INFO, that there is no branch here BY
      RULING. The routing is unchanged: a Breakout still falls through to the same evaluator. Any
      OTHER unrouted strategy still WARNS "has no exit route", so a real one still wakes the agent.
      The operator: "Agree on all", 2026-09-30.
v4.27 2026-09-26  OTV4TEST r149 (EOD.1) — THE OPERATOR'S END OF DAY. Every hard-close decision now reads ONE clock per position: ASSIGNMENT RISK (a short leg: verticals, condor/trend legs, the tent, butterflies, an adopted short) closes from 15:45 on a RESTING BEST-CASE limit — the structure's ESTIMATED VALUE AT 15:55 if spot holds (each leg priced with the 5 minutes then left to expiry at its own chain IV; no IV -> expiry value), a nickel floor on a buy-back, one tick under on a sale (operator: "Best case on the trajectory (nickel close, 1 delta, etc)", then "Can we instead estimate their assumed BY 1555 & rest that?"), re-priced each tick; everything else LADDERS from 15:50 (a long single never below parity - tick); at 15:55 EVERY structure crosses, credits included. 🔴 r105's "credit hard close takes the nickel or takes assignment and never crosses" is SUPERSEDED by the operator's 2026-09-26 ruling. Labels derive from the schedule: hard_close_resting_15:45_ET / hard_close_ladder_15:50_ET (the "hard_close" substring every reader keys on is kept). PAPER (operator: "use latest possible close allowed by code ... or best-case available when deep ITM (par, nickel)"; "I want to be accustomed to seeing late closing orders"): EVERY end-of-day close books at the 15:55 cross — at the mark (the ladder's last rung), or at its best case (nickel / parity less a tick) when the outcome is already SETTLED (_eod_determined: with IV, the 15:55 estimate prices to the same tick as the expiry value). Other paper exits are unchanged.
v4.26 2026-09-23  OTV4TEST r120 — THE SWEEP'S BREACH EXIT RUNS ON THE OPERATOR'S
      BREACHED (LVL.15 step 4). *"Price was accepted beyond the level ... as
      evidenced by the closure of a 1-min candle beyond the level [and the]
      start of a one minute candle formation on the pierced side."* The exit
      counted TWO CLOSED BARS beyond the pool (`ACCEPT_CLOSES`) — the third
      breach definition in the tree, beside the book's and `is_spent`'s. It now
      judges the bars since entry with `derived/level_rules.judge`, the same
      function the level book uses: a 1m close beyond the pool, then the next
      1m OPEN beyond. Live, that next bar is the forming one, whose open is
      known the moment it starts. REPLAYED on all 11 sweep trades on this box:
      on the 8 that exited on the 2-close rule the replay reproduces every exit
      minute, and BREACHED fires 1 minute earlier on 7 and the same minute on
      1; on two that bled to the premium stop it fires EARLIER (09-14 PDL
      10:20 vs the 11:06 -$306 stop, 09-22 asia 09:49 vs the 09:51 -$160
      stop). Two closes whose next bars OPEN BACK INSIDE are no longer a breach
      (the book agrees they are not). The exit label `sweep_breach_accepted`
      is kept: `is_spent` and the reports read it.
v4.25 2026-09-22  OTV4TEST r91 — THE STRUCTURE-ANCHORED TRAIL, for ORB and
      Breakout only. Operator: *"I don't want the 25% premium stop anymore.
      Put a 25% trailing stop on it that follows the move... I want it from
      the start."* Armed at entry, seeded on the STRUCTURE stop rather than
      `entry x 1.25`, ratcheting `current x 0.75` which with an upward-only
      ratchet IS `peak x 0.75`. 🔴 THE STRUCTURE FLOOR IS LOAD-BEARING: r44
      removed exactly this formula because a fraction of PREMIUM can sit BELOW
      ENTRY — 10 of 210 trail-exited fleet trades finished NEGATIVE with the
      trail armed. Seeding on the structure stop makes that impossible here.
      ⚠️ EVERY OTHER STRATEGY KEEPS `_gain_floor` and the +50% arm.
v4.24  2026-09-21  OTV4TEST r82 — DELTA ONLY. The extrinsic limb is REMOVED:
      measured over the whole trade, extrinsic-from-mid reaches zero at DELTA
      0.82, so it is not a proxy for par and r80's peer-promotion would have
      cost $2,500 on 81b1afae. r79 never needed widening either — delta
      crossed 0.98 at 13:44 and I sampled it in a trough at 14:08.
v4.23  2026-09-21  OTV4TEST r80 — r79's PAR RUNG DID NOT FIRE AND THE DEFECT
      WAS MINE. Extrinsic was gated behind "only if delta is absent", so
      81b1afae sailed past it live: feed delta 0.9675 under the 0.98 bar while
      the same contract priced at 99.3% intrinsic. A 0DTE deep-ITM delta print
      LAGS WHAT THE PRICE ALREADY SAYS. The two are complementary — EITHER
      reaching par is par.
v4.22  2026-09-21  OTV4TEST r79 (EXT.1) — PAR DELTA IS AN EXIT. Operator,
      live on a VOLT call at +468% with FOUR CENTS of extrinsic left: *"We
      need an extrinsic/intrinsic metered exit"*, then *"When Delta reaches
      PAR, we need to get the fuck out."* At par delta the position is stock
      carrying an expiry — no convexity left to absorb a pullback — so a
      run-fraction trail costs full dollars exactly when the trade has already
      won: 81b1afae held $4,630 with a leash worth $2,880 and $45 of theta
      risk. `_evaluate_volt` gains rung 2b, above the structure stop and the
      trail. Reads `current_delta`; falls back to extrinsic/mark off the same
      frames when the feed hands us none, because delta->1 and extrinsic->0
      are ONE condition in two instruments and a missing field must not
      silently disable a ruling.
v4.21  2026-09-21  OTV4TEST r75 — THE STRUCTURE STOP MUST READ A BAR THAT
      POSTDATES THE ENTRY. Found live: VOLT took 7 trades in 90 seconds, each
      stopped in ~14s against the 09:45 close while entering at 09:52. The
      replay had this guard; the shipped code did not, so every measurement
      that authorised the design was blind to it.
v4.20  2026-09-21  OTV4TEST r72 (CTRL.1) — `_evaluate_volt`, the control arm's
      OWN exit path: hard close, the universal catastrophic floor, a STRUCTURE
      stop and an R-trail. Four rules, deliberately not `_evaluate_orb` — that
      path carries theta bleed, the FVG trail and the 100%-TP ladder, and
      routing VOLT through it would make the yardstick a variant of the thing
      it measures.
      🔑 TWO OPERATOR RULINGS LIVE HERE. The stop is read on the **5-MINUTE**
      frame (15s/1m/5m give win 3.7/6.8/18.8% — at 1m, 93% of trades die on the
      stop and the trail never arms), and R comes from `underlying_target`, NOT
      from |entry-stop|, because the stop EQUALS the entry and a trail scaled on
      zero would never arm. The hard-close label is DERIVED from HARD_CLOSE_ET
      so it does not become a sixth stale literal (r71's W7 caught exactly that).
v4.19  2026-09-20  OTV4TEST r71 (LATE.1) — THE VERTICAL'S CLOSE LABEL IS
      DERIVED FROM `VERTICAL_HOLD_TO_ET` INSTEAD OF SPELLED. The operator moved
      the credit hold to 15:50; the branch still wrote `hard_close_15:45_ET`,
      which would have put a FALSE TIME on every late credit exit in the book.
      The superseded "held to 15:45 and not past it" doctrine is STRUCK, not
      deleted (r240). ⚠️ THE FIVE GENUINE `hard_close_15:45_ET` SITES ARE
      UNTOUCHED — they are the real hard close and W7 pins the count at 5.
v4.18  2026-09-18  OTV4TEST r44 — TWO EXIT CONSTANTS RE-ANCHORED.
      (1) THE THESIS LINE HAS A WIDTH. It was asserted to the cent: the hunt's
      line was 718.50, a bar closed 718.57 — SEVEN CENTS — and price then fell
      2.68 points. The band is the median 1m wick from the live tape (the
      level's own precision), measured per instrument as r39 ruled for the zone
      width. And a LiquidityHunt exit now says `hunt_thesis_dead`, not
      `runaway_thesis_dead` — that label cost a wrong diagnosis.
      (2) THE TRAIL FLOOR IS A FRACTION OF THE GAIN. Both paths used a fraction
      of PREMIUM (0.75 / 0.80), which can sit BELOW ENTRY — at the +20% arm
      threshold an 80% lock floors at 0.96 of entry, so ARMING THE TRAIL COULD
      GUARANTEE A LOSS. Measured on S3, 210 trail-exited fleet trades: median
      capture 42.9%, and 10 of 210 (5%) finished NEGATIVE with the trail armed.
      `entry + L x (peak - entry)` is >= entry by construction.
v4.17 2026-09-10  OTV4TEST r12 — THE LIQUIDITY HUNT'S EXITS (PLAN_SPEC §37): routed to
      the runaway's family (thesis-dead on a close back through the entry
      boundary, fizzle, backstop, no premium stop) with one exit of its own
      in front: the target level WICKED with the close short of it takes the
      hunt off and writes a HANDOFF GRANT to the sweep (execution/handoff.py).
      A close beyond the target is acceptance — over-delivered — and the
      runaway's hold logic keeps it.
v4.16 2026-09-09  OTV4TEST r11 — THE FINAL-FORM FLOOR ON A ROLLED STRUCTURE. After
      a risk-free roll both legs carry `final_form_group` and `final_form_basis`
      (condor_roll v4.8: the cost to close the structure as formed). A hedged
      leg with a group now exits when the GROUP's cost to close — the sum of
      both legs' current premiums — has grown 15% (TENT_FLOOR_PCT) from the
      basis: "final_form_floor". Both legs read the same numbers on the same
      tick, so both leave together. Operator: "we're out at 15% … unless no
      available strikes will make us whole again." The nickel and 15:45 stand.
      The tent evaluator is no longer reached (its rung is retired).
v4.15 2026-09-09  OTV4TEST r10 — the tent floor's reason names its basis: 15% from
      the structure AS FORMED (condor_roll v4.7 sets `entry_premium` to the
      as-formed cost and keeps `cumulative_credit` alongside). Operator: "15%
      of wherever our credit is from that point, not including the previous
      rolls and other transactions."
v4.14 2026-09-09  OTV4TEST r9 — THE TCS 15%-OF-CREDIT STOP IS LONE-ONLY: a hedged
      leg's sibling suppresses it (operator 2026-09-09), the same mechanism the
      sweep leg uses. Order for the TCS: hard close → 15% (lone) → the level
      lost (`tcs_breach`, a close back through the accepted extreme the spread
      was sold against — `underlying_stop` carries it). ⚠️ NO NICKEL CLOSE
      STANDS: the 2026-08-14 ruling ("no closing it short of a breach or the
      hard close") was MEASURED — EV held to expiry — and today's untangle
      listed a nickel in passing without revisiting that measurement. Left as
      ruled; flagged in the r9 report for an explicit decision.
v4.13 2026-09-09  OTV4TEST r5 — THE SWEEP VERTICAL'S STRUCTURAL EXIT. Operator:
      *"we exit quickly if the breach is accepted, otherwise hold to flatten
      or if it runs hard, we take the nickel close."* In `_evaluate_condor_leg`
      a SWEEP vertical (setup_type sweep_credit_spread) now exits on BREACH
      ACCEPTED — ACCEPT_CLOSES (2) consecutive closed 1m bars beyond the pool
      it sold against (`pool_price` on the record) — placed AFTER the
      15%-of-risk lone stop (operator: two minutes into a dead thesis can
      rack up serious losses; the floor answers first, the breach names the
      reason) and before the nickel close (0.05, CONDOR_NICKEL_CLOSE), which
      was already there. The level is marked SPENT on THIS exit only
      (trade_logger v4.13), not on a stop-out: a 15% wobble leaves a held
      level live. Hedged (condor) legs keep their stop suppression unchanged.
v4.12 2026-09-08  OTV4TEST r3 — THE HANDOFF, THE THESIS, THE FIZZLE, THE BACKSTOP.
      Operator 2026-09-08. In `_evaluate_orb`, for BOTH families:
      · REJECTED HANDOFF (position 2, after the hard close, before any floor):
        `DerivedStore.latest_rejection()` reports a pool on the trade's side,
        beyond the entry, REJECTED on a close since entry → exit "handoff:
        pool X rejected on close — sweep owns it". The reversal is where the
        ORB historically gave its gains back; the fact is emitted once, in
        derived/levels v4.1, and read here rather than re-detected.
      For RUNAWAY records only:
      · NO PREMIUM STOP. *"If we're going to immediately open another momentum
        trade the second the preceding one stops out, then why not just
        HOLD?"* The exit is the negation of the entry: THESIS DEAD = a 1m
        CLOSE back through the 50% level (boundary ± width/2 from the record's
        own range). While price holds beyond it, premium wobbles do not exit.
        What a 20% floor WOULD have done is recorded on the decision
        (`would_have_floored`) so the first sessions show whether a percent
        under the structure is needed — a question, not a bar.
      · FIZZLE — the entry's evidence decaying, measured on the bars since
        entry: EVENTS (no threshold) higher-low broken, VWAP recrossed (when
        the frame carries volume); DIALS (self-referenced) acceptance decaying
        (trend_strength acc_delta < 0 with acc_recent < 0.5), range
        contracting (< 0.5x the first bars), premium diverging (a new
        underlying high in the last 3 bars without a new premium high). Exit
        on two events, or one event plus one dial. Priors, recorded per tick.
      · STRUCTURE BACKSTOP — a 1m close back through the ORB boundary itself
        (beneath the 50; the air-pocket case). Replaces the 20% floor.
      Order for the runaway: hard close → handoff → thesis dead → fizzle →
      trail (unchanged) → theta bleed (kept) → backstop.
      ORB records keep their own list (§29) plus the handoff.
v4.11 2026-09-08  OTV4TEST r2 — VELOCITY STALL IS OUT OF THE ORB PATH. Operator,
      2026-09-08, on the seven ORB exits read back to him: *"Keep all but 5.
      Theta bleed should catch whatever a stall would have stood in for."*
      `_evaluate_orb` skips `_velocity_stall` for `ORBStrategy` records. The
      RunawayContinuation shares this evaluator and is NOT changed here — the
      runaway's exits are its own conversation, and this fork takes one trade
      at a time. Pinned by check_orb_plan P13 with the stall forced to fire.
v4.10 2026-09-05  r269 — 🔴 THE FORMED CONDOR'S LOSS BOUNDARY IS SETTLED: there
      is NONE, deliberately. Operator: *"The current architecture covers all
      condor management. It's a settled issue."* The 15:45 close, the nickel
      close and the roll ARE the management. This replaces a citation to
      `docs/HANDOFF_CONDOR_STOP_20260824.md`, deleted this revision — that
      document held the only statement of the open question, so the answer is
      recorded AT THE SITE that would otherwise invent a boundary. No code
      change.
v4.9  2026-09-04  r238 — 🔴 THE TREND-CREDIT BRANCH GAINS A
      15%-OF-CREDIT STOP, and it runs FIRST. Before this the branch checked the
      boundary breach and returned, so a trend credit had no premium stop at
      all. Operator, 2026-09-04: the 15% *"is doing the heavy lifting, flatten
      is last resort, nickel closes on a nice move."* NOT the lone stop's 15%
      OF RISK — 4x different, and chosen. On a $2.50 credit it is $0.375
      against a $2.45 win to the nickel: a realized 6.5:1, breakeven near 13%.
      `stop_survivable` at ENTRY is what stops it being the r155-inverted stop
      that fires on noise, so the entry gate is load-bearing for this exit.
v4.8  2026-08-27  r169: the butterfly's TARGET (20% of max profit) and MAX
      HOLD (150 min) are retired — operator: "1545 flatten or 25% loss,
      whichever comes first." Its exits are exactly two now, like the
      credits: the 25% floor and the 15:45 hard close.
v4.7  2026-08-27  r167: BOS EXIT RETIRED from the decision path (operator:
      "overall a loser"; measured 34% / 217 / -$7,085). The only live site was
      step 4 of _evaluate_sweep, the default route for every non-ORB debit.
      Everything else — the 50% trail, the post-target tightening off the
      peak, theta bleed, velocity stall — STAYS, and for the non-ORB
      strategies is now reached through strategy/management.py's decide(),
      which owns the decision and writes the row; this engine remains the
      calculator and the executor. ORB is untouched end to end.
v4.6  2026-08-24  r105 THE EXIT LADDER, per TRADES.md §6. Structural and
      profit-side closes WALK (25% in from best, one increment toward mark,
      ratcheted, never worse than mark); the 15% FLOOR goes straight to MARK and
      re-prices there (a thesis-invalidated stop is not a negotiation); the
      CREDIT hard close takes the nickel or takes ASSIGNMENT and never crosses,
      reversing hard_close_order_mode for credits only; DEBITS keep the cross
      because a long that does not close expires worthless rather than assigning.
      A refused rung advances; a booked fill clears the walk. Quote comes from
      position_manager's per-tick structure stash — the exit path had only ever
      been handed a mark.
v4.5  2026-08-24  (title corrected — the body carried r90's v4.5 content while
      the header still read v4.4)
v4.4  2026-08-24  CONDOR STOP SUPPRESSION (operator ruling: "The 25% stop
      should only apply to a lone vertical spread — never the condor").
      _evaluate_condor_leg: the per-leg premium stop and ratchet now run ONLY
      when no complement is open; while the condor is formed they are
      SUPPRESSED and RE-ARM the moment the leg is alone again (one-way
      suppression = naked full-sized position). Suppress/re-arm persist as
      NEW row fields stop_suppressed_ts / stop_suppressed_by (trade_logger
      v4.3) — stop_premium stays the immutable entry-time floor per the v3.1
      trail lesson — and are announced edge-triggered at INFO. Lone
      calibration unchanged at 15% (TRADES.md §5 / F6). The formed structure
      keeps 15:45 close, nickel close, and the roll. 🔴 SETTLED 2026-09-05
      (r269): THE FORMED CONDOR HAS NO FURTHER LOSS BOUNDARY, DELIBERATELY -
      operator, "the current architecture covers all condor management."
      Those three ARE the management. Stale CONDOR_STOP_LOSS_PCT import removed (unused here
      now; main.py still stamps the row floor with it). exit_reason gains
      "(lone 15%)".

v4.3  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).


v4.2  2026-08-21  PHASE B (r58): still_trending label arms deleted — dead by
      construction since the split; the trend vote alone decides, per the
      block's own doctrine.
      the condor-leg adverse exit DELETED - both tested trending LABELS v4
      never assigns, so neither had run once since the port. Two more exits
      that were dead for a quieter reason than F0.
Exit decisions: trails, structure stops, theta bleed, time.

v4.1  2026-08-20  AUDIT F0/F6/F7/F10. F0: the class was BISECTED - r38 landed
      _track_excursion at column 0 inside the class region, so evaluate and
      all 33 evaluators were nested locals of a telemetry function and EVERY
      intraday exit was dead code (AttributeError into the loop catch-all,
      every tick, every open position). Relocated below the class; the
      doctrine block above it carries the full mechanism. F6: the condor leg
      stop derives from hedge state - 15% unhedged / 25% hedged (TRADES.md 5,
      condor_stop 16 trades 19% win -$1,156 calibrated for a complete
      structure). F7: *_bars columns received 15s TICK counts; now poll-
      derived minutes - still COUNTED not timed, only the unit is honest.
      F10: RunawayContinuation routed to the ORB exit family its spec cites;
      the else-branch names its default out loud instead of absorbing
      strategies silently.
v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

execution/exit_engine.py — AUDIT F7: the BREAKOUT_VOLATILE exemption was scoped to
        `_breakout` records only, so a standalone/handoff continuation that
        ACCELERATED into a breakout IN ITS OWN DIRECTION was closed as a
        Now ANY continuation survives, gated on the TREND VOTE agreeing -
        which is what v4.19's own comment already said should decide, and
        which the label cannot supply because BREAKOUT_VOLATILE has no
        direction. A long no longer survives a violent move DOWN.
v4.21 — Strategy-aware exit logic for all options positions.
🔴 AUDIT F1+F2+F4: THE v4.20 FIX NEVER BOUND, AND THE
        DISPATCH NEVER ROUTED. Two defects of the exact species v4.20 fixed,
        one hop away each, found by the adversarial audit and REPRODUCED AT
        RUNTIME (every failure below executed against 3d9e82e, not inferred):
        (F1) `is_trend_participation` was called at the top of
        `_evaluate_condor_leg` and NEVER IMPORTED into this module — NameError
        on every condor-leg tick and every legacy TC.6 row. The exception
        escapes _manage_one into the tick loop's error counter: 30 errors at
        15s ticks = sys.exit(1) about 7.5 min after any condor leg opens, then
        a systemd crash-loop until the 15:45 branch (which sits ABOVE the
        call) flattens it. The chain test asserted the STRING existed in this
        file — a mention, not a binding (WORKING_AGREEMENT section 20, at the
        import level). Import added, module level.
        (F2) `_execute_condor_leg` now writes strategy="TrendCreditSpread"
        (main v6.8) but evaluate() only routed "IronCondorStrategy" to the
        condor evaluator — every NEW TC.6 record fell to `_evaluate_sweep`,
        the DEBIT evaluator: KeyError 'trail_activation' on the first tick of
        a fresh record; after the crash-restart, target_premium=$0.05 (the
        nickel) read as a debit TP satisfied from tick one, so the position
        lived in the ORB post-target trail with SIGN-INVERTED P&L labels and
        lost the VERTICAL_HOLD_TO_ET exemption; TypeError once value decayed
        below the nickel. The dispatch now routes any record structure.py
        recognises as a credit vertical — both strategy names, legacy rows,
        and the rolled broken wing — to `_evaluate_condor_leg`.
        (F4, HISTORICAL — the condor ratchet was deleted in v4.5) the
        every bake reset an earned breakeven/+20% lock to the base -25% and
        re-opened the round-trip v4.1 exists to close. The earned level now
        rides the SAME persistence the directional trails use: emitted via
        decision.new_trail_stop (position_manager writes the trail_stop
        column) on the STANDALONE branch only — v4.17's formed branch
        deliberately neither applies nor updates it — and re-seeded from the
        column on restart. Only a value below base_stop can be a real condor
        ratchet; anything else is stale/foreign and ignored.
        Ships with tests/test_exit_dispatch_runtime.py — the first suite on
        this path that EXECUTES evaluate() with real record shapes (fresh AND
        rehydrated) instead of grepping source. Verified to fail against
        3d9e82e before this fix.
🔴 THE TC.6 BRANCH DIED ON RESTART. `is_trend_credit` IS
        NOT A COLUMN in the trades table — it lives only in the in-memory
        record. `get_open_trades_live()` does SELECT *, so **any restart
        rehydrated an open trend-participation position WITHOUT the flag**, this
        branch stopped firing, and the leg dropped into the condor ladder with
        the ratchet and the 25% premium stop. Same bug as the 08-14 identity fix,
        one level down: fixed for the process that OPENED the trade, still broken
        for any process that INHERITS it — and the hop that dropped it is a
        systemctl restart, which happens on every bake.
        Now DERIVED from `strategy` / `setup_type`, which are REAL COLUMNS and
        already round-trip. No new column, no migration — a column would fix
        tomorrow and not today, because rows opened before it would still
        rehydrate as None and read as False. The old flag is still honoured when
        present; only its ABSENCE stopped meaning "not a trend credit".
        See strategy/structure.py.
🔴 CNT.1 SHIPPED HALF A FEATURE AND THIS IS THE OTHER HALF.
        The entry branch (continuation_strategy, CNT.1, 2026-08-07) lets
        continuation OPEN on BREAKOUT_VOLATILE, taking direction from the trend
        vote and gating on ADX. `still_trending` here only ever accepted
        TRENDING_BULL / TRENDING_BEAR. So every `trend_continuation_breakout`
        trade was **BORN ALREADY FAILING ITS OWN EXIT TEST** — opened on tick N,
        closed on tick N+1 by reading the SAME UNCHANGED LABEL. THE LABEL NEVER
        Measured live 2026-08-14: 15-second holds, exactly one tick, repeating
        while the setup held. P&L symmetric noise — one tick of random walk minus
        the spread. **This has been true for every breakout continuation since
        2026-08-07.** Sits BEFORE bos_exit, so nothing else got a look.
🔴 LIVE FIX: THE TC.6 BRANCH HAD NO TERMINAL RETURN.
        When NEITHER breach NOR nickel fired it fell straight through to the
        ratchet and the 25% condor stop. `_execute_condor_leg` writes
        stop_premium = credit x 1.25 at entry, so a $0.06 credit put the stop at
        $0.07 — ONE CENT of widening closed the trade. Every TC.6 leg on the
        fleet stopped out within seconds of opening on 2026-08-14.
        THE MEASURED EV WAS HELD TO EXPIRY, UNMANAGED. A premium stop is a
        different trade, which is the entire reason the branch exists.
        ⚠️ THE TEST THAT MISSED IT asserted the branch CONTAINED two
        `return decision` statements. It did. Neither covered the path where
        neither condition fires — the path that was broken. **Counting returns
        proves nothing about the path that has none.** Now asserted on the
        branch's LAST STATEMENT via AST, and verified to FAIL against the
        shipped version.
THE RATCHET WAS CLOSING UNTESTED CONDOR LEGS. Operator:
        "the ratchet is inappropriate for this trade if the condor is fully
        formed. It should only be in effect if there's one side open" and
        "don't close a leg if it hasn't been tested - that's what the roll is
        for."
        MECHANISM: the base -25% stop only ever fires on the TESTED side,
        because a credit spread's value RISES as price approaches your short.
        The RATCHET does the opposite — it tightens the UNTESTED side's stop to
        breakeven at +20% and +20%-locked at +40% PRECISELY BECAUSE that side is
        winning. On the reversal the tested leg stops at -25% and the untested
        leg hits its ratcheted stop too. **A leg price never went near, closed
        by a stop that exists only because it was profitable.** That is the
        double-stop — 5 of 14 condor symbol-days had BOTH sides stopped — and it
        fires BEFORE the roll can be used, because the roll needs a tested side.
        FIX: while `_condor_sibling_open()` is true, the base floor is the ONLY
        stop; no tier, and the stored high-water is neither applied nor updated,
        so a leg returning to standalone resumes from a level it genuinely
        earned. Same interlock the take-profit already used, and it FAILS CLOSED
        (True on error) — treating a leg as part of a structure is the safe
        error.
        direction-aware — a call spread exits only on TRENDING_BULL, which IS
        price rising toward that short strike — so it already fires only on the
        threatened side and is a tested-side exit.
        PRESERVED: `condor_stop` went 0% -> 19% win after the ratchet shipped,
        but that evidence came mostly from STANDALONES (18 of 46 legs never got
        a second side). Scoping keeps the gain where it was measured.
        ⚠️ ACCEPTED COST: an untested leg that runs to +40% and reverses now
        gives it back rather than locking +20%.
VEL.1: THE VELOCITY STALL, ladder step 2c. THE THIRD
        QUESTION, and until now nobody asked it. `orb_structure_stop` asks "did
        the thesis break?"; `_theta_bleed` asks "is my GAIN about to evaporate?"
        — its gate 1 is a gain floor, so a LOSING position is invisible to it.
        **A losing position that has STOPPED MOVING answers no to both** and
        falls to the -40% percentage floor, which is the ABSENCE of a mechanism
        rather than one. 2026-08-12 QQQ: 50 minutes and -42.2% with the
        underlying sitting BELOW the short entry the entire hold — directionally
        right, bleeding anyway, and nothing watching.
        STATISTIC — and it needs NO TARGET, which is why it generalises to every
        long-premium strategy: bev = |theta| / (|delta| * 1440) is the pts/min
        at which delta gains exactly offset decay; ratio = delivered / bev, and
        1.0 IS THE FLAT LINE.
        MEASURED, 15 sessions / 145 ORB trades against the chain archive
        (tests/velocity_feasibility.py — the FIRST tool to ever read it), among
        trades STILL OPEN at each mark:
              mark   winners p10   losers p50   losers p90
               5m       -21.1        -37.3         91.3   <- NO SEPARATION
              10m         3.9         -6.7         20.5
              15m        18.0          0.3         26.7
              20m        29.8          0.9         18.5   <- barely overlap
        The median surviving LOSER treads water at ~1.0 — exactly breakeven —
        while the bottom decile of WINNERS runs at 30x it.
        ⚠️ ORDER IS DELIBERATE: theta_bleed evaluates FIRST so a trade up 10-20%
        and stalled exits GREEN via that path. INDEPENDENT gates, never a
        combined score — the QQQ failure was two mechanisms each correctly
        saying "not my problem" with nothing aggregating that into "then NOBODY
        is watching."
        ⚠️ GRACE IS FORCED BY DATA: winners p10 at 5 min is -21.1, so the bottom
        decile of eventual WINNERS was moving AWAY. No check before 10 minutes.
        ⚠️ SHIPS OBSERVE-ONLY (OT_VELOCITY_ENFORCE=0). Floors rest on n=22 at the
        20-minute mark and are ORB-derived; other strategies are logged, never
        cut, whatever ENFORCE says.
        ⚠️⚠️ EVALUATION DATE: **FRI 2026-08-14**, and it carries a DELETE
        CRITERION — **zero firings across 08-13 and 08-14 means REMOVE THIS
        CODE.** A mechanism that never triggers is not cautious; it is dead code
        that still has to be read, tested and maintained. Standing rule agreed
        with the operator 2026-08-12 after three observers shipped in two days
        with no dates: an observer ships with an evaluation date and a delete
        criterion, or it does not ship. The cautionary case is the chain archive
        — written 07-23, first read 08-12, twenty days later.
        ⚠️ THE ENTRY-FILTER FORM OF THIS IDEA WAS MEASURED AND REJECTED:
        feasibility ratio at entry ran HIGHER for losers than winners at every
        percentile (losers p50 5.05 vs winners 3.87, n=145) — a wide range gives
        a distant target AND a big required move, so feasibility and difficulty
        are the same axis pointing opposite ways. Recorded so it is not rebuilt.
BOS PROTECTED LEVEL GETS A MINIMUM DISTANCE. The level is
        seeded from the LOW of the first bar closing above entry. On a pullback
        entry that bar is the smallest, earliest part of the resumption, so its
        low sits a hair under entry — the level lands INSIDE the symbol's own
        noise band and the next ordinary wiggle fires it.
        OBSERVED LIVE, not inferred: JPM in $1.26 12:49 -> out **$0.00** 12:50
        -> back in $1.26 the same minute. A null round trip — the exit condition
        was already true at entry. QQQ the same session fragmented ONE move into
        four scratches (+$30/+$45.50/+$35/+$7), same strike, three minutes, each
        exit immediately followed by re-entry because the setup was still valid.
        The re-entry loop is a SYMPTOM: it cannot happen unless the position
        closes, so a cooldown would suppress the symptom and leave the premature
        exit intact.
        Fix: floor the level at BOS_MIN_DIST_ATR * ATR from entry, ATR-scaled so
        it widens on NVDA and tightens on GLD automatically. Applied ONLY on the
        continuation path, which seeds with `underlying_entry`.
        ⚠️ min_dist=0 IS BYTE-IDENTICAL to pre-v4.15, ratchet included — a test
        pins that, because otherwise the kill switch is not a kill switch and
        there is no A/B control.
        ⚠️ `low - min_dist` IS NOT MONOTONE: a widening ATR can produce a new
        candidate BELOW the old level, silently slackening the stop exactly when
        volatility rises. Longs max(), shorts min().
        ⚠️ PRE-EXISTING DEFECT FOUND AND DELIBERATELY NOT PATCHED HERE: the
        generic/ORB caller (~966) seeds the tracker with `entry_prem` — the
        OPTION premium — while BOSTracker compares against df_1m UNDERLYING
        closes. A ~$1.26 premium against ~$352 closes means the first bar always
        beats peak_close, so that path seeds a level on bar one regardless of
        structure. Recorded rather than silently fixed; an ATR distance in
        premium units would be meaningless anyway.
CNT.2 INSURANCE GATE (2c), continuation only. BOS (2b) is
        the thesis invalidator and is deliberately ungated on P&L, but
        `BOSTracker.protected_level` is None until the trade makes a new closing
        high past entry — so BOS is structurally BLIND on a trade that goes
        wrong from the first tick, and that is exactly the population running to
        the floor at −29% with MFE +1% (45 trades, 11 sessions). 2c arms the
        already-stamped `underlying_stop` ONLY while `protected_level is None`
        and disarms the instant BOS has a level, so the handoff is exact and
        needs no time window. Structural, not premium-percent: a tighter premium
        floor was measured to net ~zero because it cuts winners that merely dip.
        Exits tag `insurance_stop` so the rollup scores it apart from
        max_loss_floor and bos_exit. `_bos` construction moved OUT of the df_1m
        guard so 2c cannot reference an unbound name. OT_CONT_INSURANCE=0 to
        disable. The level has never been read by anything that trades — treat
        it as an untested prior.
W.2 follow-on: the v4.12 throttle reused the ALERT set,
        so the census classified a debug-only handler as "pages". Own set now.
W.2: the v4.11 escalation guard was a bare `except: pass`
        inside place_exit_order — a SILENT swallow in the census's tier 1. Now
        DEBUG, once per process. No behaviour change.
EXIT LADDER LATENCY (N.5, log-only). place_exit_order() —
        the ONE seam every close routes through, paper and live — now stamps
        submit and fill instants, counts the passes the close took, flags
        escalation, and records the MARK AT TRIGGER. Written to the trade row
        via trade_logger v3.11 set_exit_latency() on a CONFIRMED close only.
        WHY THE MARK MATTERS MORE THAN THE MILLISECONDS: TC.2 has to choose a
        stop trigger (-40% vs 35% vs 25%) "calibrated against measured ladder
        fill-latency", and latency is not a cost until it is priced. The cost
        is (mark when the exit fired) - (price it actually filled at). Paper
        books the mark, so the two are equal by construction there — that
        equality is the PLUMBING PROOF that the capture is wired, not a result.
        The real distribution only exists in the live week.
        STATE LIVES ON THE RECORD, NOT ON THE ENGINE, because a live close is
        MULTI-TICK: the deadline can expire and the next tick RESUMES the same
        broker order. Keying off the record means submit_ts is the FIRST submit
        of that close attempt and the pass count spans the whole sequence; an
        engine-level counter would reset on restart and undercount exactly the
        slow closes the study is about.
        NOTHING IN THE TRADING PATH READS ANY OF IT. No exit decision, no
        price, no size changes — the capture runs after the FillResult exists.
CREDIT VERTICAL MANAGEMENT — the measurements, kept; the encodings, retired.
        The RATCHET (r90) and the TIME-GATED TP (r106) are both GONE. What the
        study actually established survives and is the reason they went:
        on 18 lone verticals a TP@25% turned -$242.77 into -$8.43, and on 28
        paired legs a TP was WORSE AT EVERY LEVEL — a credit vertical must never
        be closed on profit. The v2 text drew the opposite conclusion from its
        own numbers and shipped a TP anyway.
        WHAT MANAGES A CREDIT VERTICAL NOW: a 15% floor while it is alone,
        suppressed while a complement is open (closing one end of an offset pair
        leaves a full-sized naked position), the nickel as a DISPOSAL preference,
        the 15:45 close, and the roll. Nothing else.
CONTINUATION EXIT REWORK (user directive). Three changes,
        all scoped to _evaluate_continuation — no other strategy touched:
        (a) TRAIL ANCHORS TO 5m FVGs. It was passing df_1m straight into
            _update_fvg_trail, bypassing the _fvg_frame() helper that ORB and
            sweep have used since v3.8. 1m gaps on a trend-continuation runner
            are noise-tight tripwires; 5m gaps are structurally meaningful and
            naturally wider. Now routed through _fvg_frame(df_1m, df_5m), so
            it also inherits the graceful 1m fallback when 5m is thin.
        (b) THETA-BLEED ENABLED. _theta_bleed had exactly ONE call site
            (_evaluate_orb) — continuation had NO theta protection at all, so
            a stalled winner decayed untouched toward the floor. Now called,
            with its existing four gates unchanged: >=THETA_MIN_GAIN_PCT gain,
            below the FVG_TRAIL_ARM_PCT trail ceiling, past the
            THETA_MIN_HOLD_MIN 20-minute blackout, and projected calendar-day
            decay >= the gain. Placed AFTER exhaustion so the smarter signal
            (momentum divergence) gets first refusal in the narrow overlap;
            theta only catches the genuinely STALLED case.
        (c) BACKSTOP 40%% -> 25%% via CONTINUATION_STOP_LOSS_PCT. The floor
            fallback no longer borrows the blanket MAX_LOSS_PCT.
RUNNER REFINEMENTS (all config/env-tunable; see config
        v2.0). Goals: let winners run harder, keep the loss unit deliberate,
        give 0DTE gamma room to breathe.
        (a) FLOOR 25%→40% for directionals: the -25% premium floor front-ran
            the impulsive-origin structure stop on normal gamma retests,
            stopping intact theses on noise. Floor fallbacks now read
            MAX_LOSS_PCT; the hard-stop label carries the record's ACTUAL
            floor pct (old records keep 25%, truthfully). Sizing is
            full-premium based, so at $1000 positions a floored trade now
            costs ~$400 — the daily cap should be set accordingly.
            Butterflies stay at 25% (BUTTERFLY_STOP_LOSS_PCT); condors
            unchanged.
        (b) 5-MINUTE FVG TRAILS (USE_5M_FVG_TRAIL): trails anchor to 5m gaps
            — structurally meaningful, naturally wider. 1m remains
            authoritative for the structure stop and BOS (speed-critical).
            evaluate()/_evaluate_orb/_evaluate_sweep accept df_5m; graceful
            1m fallback when 5m is absent.
        (c) FVG FLOOR CLAMP (FVG_FLOOR_MAX_LOCK_PCT=0.90): an FVG hugging
            price can no longer set a floor tighter than 90% of current —
            both the armed FVG trail and the post-target trail are clamped.
        (d) LEASH UN-INVERTED: post-target no-FVG fallback 0.85→0.75
            (POST_TARGET_TRAIL_LOCK_PCT, now in config) — proven runners no
            longer get a shorter leash than unproven ones.
        (e) SWEEP RUNNER MODE (SWEEP_POST_TARGET_TRAIL, default on): the +100%
            target_hit — the one hard TP among directionals — is replaced by
            the ORB post-target trail; env False restores it for A/B.
        Telemetry companion: trade_logger v3.8 records per-trade MFE/MAE
        (max/min premium seen) so every threshold above is tunable from
        evidence.
LIVE FILL-CONFIRMATION IMPLEMENTED (closes the Fable spec).
        _confirm_and_book_live_exit() is no longer a stub: it submits the close,
        captures the broker order id, polls to a bounded deadline
        (LIVE_FILL_POLL_SECONDS / LIVE_FILL_DEADLINE_SECONDS in config), and
        returns confirmed=True ONLY on a broker-confirmed fill at the broker's
        actual net fill price read back from per-leg fills — never the mark,
        never entry, never $0.00. Unfilled-at-deadline → cancel, resolve the
        cancel/fill race, return confirmed=False (position STAYS OPEN; the
        15:45→16:00 retry loop re-attempts and it pages once per trade/kind).
        PARTIALS: filled portion stashed on the record, remainder resubmitted
        next tick at a fresh mark; books once, at the quantity-weighted net
        price — never a partial as whole. IDEMPOTENT: a working order id is
        stashed on the record and RESUMED on re-entry, so retry ticks can never
        double-submit a close. Also fixed on the way (all live-only):
        (a) condor-leg verticals now close as ONE 2-leg spread order
            (BUY_TO_CLOSE short / SELL_TO_CLOSE long) — they previously routed
            to _close_single_leg, which sold the short symbol (wrong action)
            and orphaned the long leg at the broker;
        (b) spread closes are marketable LIMITs (tastytrade rejects MARKET on
            multi-leg): vertical debit capped at spread width, butterfly credit
            floored at one tick — the old MARKET butterfly close would have
            been rejected every tick;
        (c) SDK signed-price convention verified (v13.x): NewOrder.price is
            negative=debit / positive=credit and price_effect is IGNORED — a
            positive-priced buy-to-close would never fill;
        (d) adopted short single legs BUY_TO_CLOSE instead of selling more.
        PAPER PATH UNTOUCHED. Acceptance tests A–E:
        tests/test_live_fill_confirmation.py. Spec:
        FABLE_SPEC_live_exit_fill_confirmation.md.
FILL-CONFIRMED EXIT CONTRACT. place_exit_order() now returns
        a FillResult (confirmed / fill_price / order_id / partial), not a bare
        bool — the SHARED seam between paper and live so the two can't fight.
        PAPER: simulate the fill at the last-known mark (passed in) and confirm
        it in one pass; if no mark, decline (confirmed=False) rather than invent
        a price. LIVE: routes to _confirm_and_book_live_exit(), which MUST book
        only on a broker-confirmed fill at the ACTUAL fill price — currently a
        fail-loud stub (raises NotImplementedError) so flipping to cash before
        it exists can NEVER book an unconfirmed close at a fabricated $0.00.
        _submit_live_close() retained (submission != fill) for Fable to call.
        See FABLE_SPEC_live_exit_fill_confirmation.md. Fixes the 15:45 hard-close
        batch that logged every leg at +$0.00 (booked at entry premium).
F5 FIX (exit-reason integrity; behaviorally neutral).
        position_manager used to overwrite record['stop_premium'] (+DB) with
        every trail update, so the floor checks here (ORB #1b, sweep #2,
        adopted #2) fired AT THE TRAIL LEVEL and labeled every trail-armed
        exit 'hard_stop_25pct'/'stop_hit'/'adopted_stop_long' — including
        post-target exits at +100%+. Exit LEVEL was always correct (it was
        the trail); the LABEL lied, poisoning exit_reason distributions for
        Phase-3 calibration. Now: stop_premium is immutable (the true entry
        -25% floor), trails persist in the new trail_stop column, and
        _seed_trail_from_record() re-arms the in-memory trail on restart so
        recovery survivability is preserved. Same exit ticks, same exit
        prices — only the labels change to the truth.
DOC SYNC (no logic change). Three docstrings in this file
        contradicted the code beneath them and were actively dangerous: an agent
        or engineer reading them would "correct" working code back into a fixed
        bug.
        (a) `_evaluate_orb`'s docstring still described the PRE-v3.1 stop ("1-min
            candle closes back inside ORB range") — precisely the behaviour v3.1
            replaced. Rewritten to the actual, ordered trigger list, and it now
            states explicitly that the -25% floor and the structure stop are an
            AND, that there is NO BOS on ORB, NO max-hold, and that the 11:00 ET
            cutoff expires the ENGINE and not an open position.
        (b) The v1.1 changelog line describing that same old stop is now marked
            [HISTORICAL — do not restore].
        (c) `_evaluate_butterfly`'s docstring claimed a 25% profit target; the
            live value is BUTTERFLY_TP_PCT = 20%.
        Zero executable lines changed — verified by diff.
ORB STRUCTURE STOP now keys off the IMPULSIVE candle's
        origin, not the range boundary. The old rule (v1.1) exited on a 1-min
        close back inside the ORB range (close < orb_high for a long). That is
        "just entering the range," which by the strategy's definition is NOT an
        invalidation — the trade is allowed to breathe inside the range as long
        as it holds the impulsive (break) candle's origin. The stop now fires
        only on a 1-min CLOSE beyond that origin: below the impulsive candle's
        low for a long, above its high for a short, read from record
        `underlying_stop` (set correctly by orb_engine v3.1). Companion to the
        engine fix; the two ship together. The unconditional -25% premium floor
        (v1.6) is UNCHANGED and still evaluated first every tick — structure
        stop and dollar floor are an AND (either exits), catching thesis-death
        and total-premium-loss independently. Contained to _evaluate_orb.
v3.0 — original release
strategy-aware exit routing:
        ORB:     stop on 1-min close back inside range, trail at 50% TP, no BOS
                 [HISTORICAL — the range-boundary stop was REPLACED in v3.1 by
                  the impulsive-origin stop. Do not restore. See v3.1 above.]
        Sweep:   BOS on 1-min structure, hard stop 25%
        Butterfly: time/premium exits only, no BOS, no trail
ORB no longer hard-exits at 100% TP. Past 100%, the trail
        tightens to track the nearest unfilled 1-minute Fair Value Gap on the
        underlying (in the trade\'s favor), giving the position room to wick
        back and fill the gap without exiting on every dip, while still
        protecting the bulk of gains if the move actually reverses. FVG
        detection is scoped to 1m data only, matching ORB entry/exit logic
        which is always evaluated on the 1-minute timeframe.
long-option THETA PROTECTION + generalized FVG trail:
        (a) theta-bleed exit — a profitable long is closed when projected time
            decay over THETA_LOOKAHEAD_MIN would erase the current gain (the
            clock, not price, is the threat). Uses live per-contract theta.
        (b) FVG-anchored trailing stop for ALL longs (ORB + Sweep), armed at
            +FVG_TRAIL_ARM_PCT: parks at the far edge of the nearest unfilled
            in-favor 1m FVG (room to continue), runs with the % trail (max wins).
ADOPTED-position exit path: manages a position discovered
        open at the broker on a LIVE restart with no DB plan (see
        broker_reconcile) by the universal core of our rules — sign-correct
        max-loss stop (long/short), long-side profit trail, 15:45 hard close.
        No strategy-specific context required.
theta-bleed REWORK (merged onto the v1.4 adopted-position
        path; supersedes the v1.3 theta logic that shipped inside v1.4). The
        v1.3 check fired on the first green tick: on 07-07 and 07-08, ~50-58 of
        ~77-87 exits were theta_bleed at a median ~60s hold, capping trends
        while the day's P&L came from the trades that reached the trail.
        _theta_bleed is now bounded by four gates: (1) a minimum gain floor,
        (2) a trail ceiling (once armed, the trail owns the trade — theta goes
        silent so trends run), (3) a MIN-HOLD blackout after entry, and (4) a
        corrected per-CALENDAR-day decay projection (v1.3/v1.4 divided by
        RTH_MINUTES=390, overstating projected decay ~3.7x). No call sites
        change; the adopted-position exit path (_evaluate_adopted) is untouched.
ORB UNCONDITIONAL -25% HARD FLOOR (critical risk fix). The
        -25% dollar failsafe is universal by design and sweep/butterfly/adopted
        all enforce it directly (if current_premium <= stop_prem). ORB was the
        lone exception: it routed its floor through _update_trail, which returns
        None below the +50% trail activation — so any ORB trade that never armed
        the trail ran with NO dollar-loss stop and could bleed toward zero while
        the structure stop held (CRM 2026-07-09: -83%, underlying still above the
        range, trail never armed). _evaluate_orb now checks the floor DIRECTLY and
        UNCONDITIONALLY right after the hard-close check, mirroring the other
        three paths. _update_trail is unchanged (its de-arm is correct for the
        TRAIL; the floor no longer depends on it). Known failure mode — the
        adopted path's own comment already flagged _update_trail's de-arm.
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
Exit triggers by strategy:
  ORB
    1. HARD CLOSE: EOD_SCHEDULE (r149) — assignment risk rests 15:45, others ladder 15:50, all cross 15:55
    2. STRUCTURE STOP: 1-min close beyond the impulsive candle's origin
       (close < impulsive low for longs, close > impulsive high for shorts).
       Closing back inside the range alone does NOT stop — only a close past
       the impulsive origin does. Runs beside the unconditional -25% floor.
    3. TRAIL (below 100% TP): activates at 50% TP, trails at 75% of current premium
    4. TRAIL (at/past 100% TP): tightens to track the nearest unfilled 1m FVG
       in the trade\'s favor — no hard exit at target, position can keep running
  SWEEP REVERSAL
    1. HARD CLOSE: EOD_SCHEDULE (r149) — assignment risk rests 15:45, others ladder 15:50, all cross 15:55
    2. HARD STOP: current premium <= 25% loss
    3. TARGET HIT: 100% TP
    4. BOS EXIT: 1-min break of structure against position
    5. TRAIL: activates at 50% TP
  BUTTERFLY
    1. HARD CLOSE: EOD_SCHEDULE (r149) — assignment risk rests 15:45, others ladder 15:50, all cross 15:55
    2. MAX HOLD: 2.5 hours
    3. HARD STOP: net value <= 25% loss
    4. TARGET HIT: 25% of max profit
  ADOPTED (broker-discovered, no DB plan)
    1. HARD CLOSE: EOD_SCHEDULE (r149) — assignment risk rests 15:45, others ladder 15:50, all cross 15:55
    2. MAX-LOSS STOP: sign-correct (long: premium <= stop; short: premium >= stop)
    3. LONG PROFIT TRAIL: standard trail to lock gains; short rides to hard close
"""

import json
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, List, Tuple
from datetime import date, datetime

import pandas as pd

from tastytrade.order import (
    NewOrder, Leg, OrderAction, OrderType, OrderTimeInForce,
    PriceEffect, InstrumentType, OrderStatus
)

import config as _cfg   # live fill knobs read at CALL time (test/env tunable)
from utils.heartbeat import touch as _hb_touch   # r295 (LIVE.2): never raises

from database.trade_logger import TradeRecord, get_trade_logger
from data.tasty_client import get_session, get_account, TastyClientError, sdk_result
from config import (
    BOS_MIN_DIST_ATR,                          # v4.15
    PAPER_TRADING, CONTRACT_MULTIPLIER,
    BUTTERFLY_MAX_HOLD_MIN, TRAIL_LOCK_PCT, TRAIL_ACTIVATION_PCT, FVG_MIN_SIZE_PCT,
    THETA_LOOKAHEAD_MIN, RTH_MINUTES, FVG_TRAIL_ARM_PCT, FVG_TRAIL_LOCK_PCT,
    THESIS_BAND_WICKS, THESIS_BAND_LOOKBACK, TRAIL_GAIN_LOCK,
    VOLT_TRAIL_ARM_R, VOLT_TRAIL_LOCK_FRAC, HARD_CLOSE_ET,
    VOLT_DELTA_PAR,                                         # r79/r82 EXT.1
    CONT_INSURANCE_STOP,
    MAX_LOSS_PCT, POST_TARGET_TRAIL_LOCK_PCT, FVG_FLOOR_MAX_LOCK_PCT,
    USE_5M_FVG_TRAIL, SWEEP_POST_TARGET_TRAIL,
    CONTINUATION_EXHAUST_EXT_ATR, CONTINUATION_EXHAUST_MIN_GAIN,
    CONTINUATION_EXHAUST_TRAIL_LOCK, CONTINUATION_STOP_LOSS_PCT
)
from utils.time_utils import (is_hard_close_time, minutes_since, now_utc,
                              fmt_et_short, now_et, ts_for_db)
from utils.time_utils import closed_pos as _closed_pos, closed_part as _closed_part   # r44 (BAR.1)
from execution.limit_ladder import limit_at_mark, hard_close_order_mode
# v4.21 (AUDIT F1): the binding v4.20 forgot. `is_trend_participation` was
# called in _evaluate_condor_leg and never imported — NameError on every condor
# leg evaluation. `is_credit_vertical` routes the dispatch (F2).
from config import TCS_STOP_PCT_OF_CREDIT                    # r238
from strategy.structure import (is_trend_participation, is_credit_vertical,
                                is_tent, has_assignment_risk)
from utils.time_utils import eod_close_due                      # r149 (EOD.1)
from config import EOD_RESTING_AT_ET, EOD_LADDER_AT_ET          # r149 (EOD.1)


def _eod_due(record) -> bool:
    """r149 — has THIS position's end-of-day close begun (15:45 assignment risk, else 15:50)?

    ⚠️ GATED THROUGH is_hard_close_time() FIRST, deliberately. That function is
    the ONE seam every checker pins the clock through (`XE.is_hard_close_time =
    lambda: False`); an evaluator that asks the wall clock another way makes
    eleven checkers pass before 15:45 and fail after it — measured on the r149
    build at 15:55 ET. It opens at FLATTEN_WINDOW_OPEN_ET = EOD resting_at, the
    earliest end-of-day minute, so in production the conjunction is exactly
    eod_close_due(). ⚠️ AND THE MINUTE COMES FROM THIS MODULE'S `datetime`,
    the SECOND seam: the condor-leg branch read `datetime.now(ET)` here before
    r149, and three checkers freeze `XE.datetime` to pin it."""
    from utils.time_utils import ET as _ET
    return bool(is_hard_close_time()) and eod_close_due(has_assignment_risk(record),
                                                        now=datetime.now(_ET))


def _eod_label(record) -> str:
    """r149 — the reason string, DERIVED from the schedule (r71: a label never names a time that did not fire)."""
    if has_assignment_risk(record):
        return "hard_close_resting_%02d:%02d_ET" % tuple(EOD_RESTING_AT_ET)
    return "hard_close_ladder_%02d:%02d_ET" % tuple(EOD_LADDER_AT_ET)

logger = logging.getLogger(__name__)

# POST_TARGET_TRAIL_LOCK_PCT now lives in config (v3.8): 0.85→0.75 default —
# the old value made the leash TIGHTER past target than before it (inverted),
# harvesting proven runners on a single gamma wick. Env: OT_POST_TARGET_TRAIL_LOCK_PCT.

# ─── Theta-bleed gates (v1.5) ─────────────────────────────────────────────────
# Bound the theta-bleed exit to its legitimate job — a small, stalled winner
# that has had time to develop and still won't reach the trail. Without these
# the check fires on the first green tick (see v1.5 header note).
THETA_MIN_HOLD_MIN       = 20      # blackout: no theta exit in the first N min after entry
from config import (VELOCITY_STALL_ENABLED, VELOCITY_STALL_ENFORCE,   # VEL.1
                    VELOCITY_GRACE_MIN, VELOCITY_STRICTNESS,
                    VELOCITY_CONFIRM_TICKS, VELOCITY_FLOOR_BY_MIN,
                    VELOCITY_MEASURED_STRATEGIES)
# r155 — the lone-vertical stop, anchored to RISK rather than credit.
from config import LONE_STOP_PCT_OF_RISK
THETA_MIN_GAIN_PCT       = 0.10    # gain floor: don't protect a gain smaller than this
MINUTES_PER_CALENDAR_DAY = 1440    # theta greek is $/share/CALENDAR day (not the 390 RTH min)


# W.2 — throttle keys for TELEMETRY-only debug lines. Deliberately NOT the
# alert set: swallow_audit classifies a handler by what its body names, and
# reusing `_live_exit_alerted` made a debug-only handler read as "pages". A
# census you can mislead by choosing a variable name is not a census.
_telemetry_logged: set = set()


@dataclass
class FillResult:
    """The outcome of a close order — the SHARED CONTRACT between paper and live.

    Both place_exit_order() modes return one of these; _execute_exit() books P&L
    from it and NEVER inspects paper_trading itself. This is the seam that lets
    the paper implementation (here, now) and the live broker-confirmation
    implementation (Fable — see FABLE_SPEC_live_exit_fill_confirmation.md)
    coexist without either re-tooling the other:

        - confirmed=True  → the close is REAL. Book P&L at fill_price. Only a
                            confirmed result may ever mark a DB row closed.
        - confirmed=False → NOT filled. Book NOTHING, mark NOTHING closed. The
                            position stays open and the caller retries/escalates.
                            This is the anti-orphan invariant: an unconfirmed
                            live close must never become a $0.00 (or any) row.

    fill_price is the price the position ACTUALLY closed at — a simulated mark in
    paper, the broker's real fill in live. It is never entry-as-a-fallback and
    never a fabricated 0.0; if there is no real price, confirmed must be False.
    """
    confirmed:   bool
    fill_price:  Optional[float] = None      # actual close price; None iff not confirmed
    order_id:    Optional[str]   = None       # broker order id (live); None in paper
    partial:     bool            = False      # live: partially filled, remainder working
    detail:      str             = ""         # human-readable status for logs/alerts
    held:        bool            = False      # r36: an INTENDED hold (paper EOD close held to the 15:55 cross)


@dataclass
class ExitDecision:
    should_exit:        bool  = False
    exit_reason:        str   = ""
    new_trail_stop:     Optional[float] = None
    current_pnl_pct:    float = 0.0
    current_pnl_usd:    float = 0.0


@dataclass
class _SimpleFVG:
    """Minimal 1-minute FVG used only for the post-target ORB trail."""
    top:       float
    bottom:    float
    direction: str   # "bullish" or "bearish"
    index:     int


def _find_1m_fvgs(df_1m: pd.DataFrame) -> List["_SimpleFVG"]:
    """
    Detect Fair Value Gaps on the 1-minute timeframe only.
    Same 3-candle imbalance logic as structure_analyzer.py, scoped to 1m
    since ORB entry/exit conditions are always evaluated on 1m.
    Returns most-recent-first.
    """
    gaps: List[_SimpleFVG] = []
    if df_1m is None or len(df_1m) < 3:
        return gaps

    from utils.math_utils import find_fvgs                      # r221: the one finder
    for top, bottom, _size, direction, i in find_fvgs(df_1m, FVG_MIN_SIZE_PCT):
        gaps.append(_SimpleFVG(top=top, bottom=bottom, direction=direction, index=i))

    return sorted(gaps, key=lambda g: g.index, reverse=True)


def _nearest_unfilled_fvg_in_favor(df_1m: pd.DataFrame, current_price: float,
                                    direction: str) -> Optional["_SimpleFVG"]:
    """
    Find the nearest unfilled 1m FVG below current price for a long
    (bullish gap, price hasn\'t traded back down through it) or above
    current price for a short (bearish gap, price hasn\'t traded back
    up through it). This is the gap the trail should give the trade
    room to wick back into without exiting.
    """
    gaps = _find_1m_fvgs(df_1m)
    if not gaps:
        return None

    candidates = []
    for g in gaps:
        if direction == "long" and g.direction == "bullish" and g.top < current_price:
            candidates.append(g)
        elif direction == "short" and g.direction == "bearish" and g.bottom > current_price:
            candidates.append(g)

    if not candidates:
        return None

    if direction == "long":
        return max(candidates, key=lambda g: g.top)
    else:
        return min(candidates, key=lambda g: g.bottom)


class BOSTracker:
    """
    Tracks 1-minute Break of Structure for sweep reversal trades.
    Long:  tracks highest closing high \u2192 protected HL = low of that candle
           BOS = 1m close below protected HL
    Short: tracks lowest closing low \u2192 protected LH = high of that candle
           BOS = 1m close above protected LH
    """
    def __init__(self, direction: str, entry_price: float,
                 min_dist: float = 0.0):
        self.direction       = direction
        self.entry_price     = entry_price
        self.peak_close      = entry_price
        self.protected_level = None   # HL for longs, LH for shorts
        # v4.15 — MINIMUM DISTANCE. The protected level is seeded from the LOW
        # of the first bar that closes above entry, and on a pullback entry that
        # bar is the smallest, earliest part of the resumption — its low sits a
        # hair under entry. The level therefore lands INSIDE the symbol's own
        # noise band, and the next ordinary wiggle fires BOS.
        # Observed live 2026-08-10: JPM in at $1.26 12:49, out at EXACTLY $0.00
        # 12:50, back in at $1.26 the same minute. A null round trip — the exit
        # condition was already true at entry. QQQ the same session fragmented
        # ONE move into four scratches (+$30/+$45.50/+$35/+$7) by the same
        # mechanism: exit, setup still valid, re-enter, repeat.
        # `min_dist` is passed in ATR terms by the caller so it scales with the
        # symbol; a raw price gap never could.
        self.min_dist        = max(0.0, float(min_dist or 0.0))

    def update(self, df_1m: pd.DataFrame) -> bool:
        """
        Update structure tracking. Returns True if BOS triggered.
        Uses the last fully closed candle - by time since r44 (BAR.1), was iloc[-2].
        """
        if df_1m is None or len(df_1m) < 3:
            return False

        candle = df_1m.iloc[_closed_pos(df_1m, now_et())]   # last closed candle (r44 BAR.1: by time)
        close  = float(candle["close"])
        high   = float(candle["high"])
        low    = float(candle["low"])

        if self.direction == "long":
            if close > self.peak_close:
                self.peak_close      = close
                # v4.15 — never seed INSIDE the noise band, and never LOOSEN.
                # `low - min_dist` is not monotone: if the caller's ATR widens,
                # a new candidate can come out BELOW the old level, which would
                # silently slacken the stop exactly when volatility is rising.
                # max() makes the level ratchet in one direction only.
                if self.min_dist > 0:
                    _cand = min(low, self.entry_price - self.min_dist)
                    self.protected_level = (
                        _cand if self.protected_level is None
                        else max(self.protected_level, _cand))
                else:
                    # min_dist == 0 must be BYTE-IDENTICAL to pre-v4.15,
                    # ratchet included — otherwise the kill switch is not a
                    # kill switch and there is no A/B control. Caught by
                    # test_min_dist_zero_is_byte_identical_to_the_old_behaviour.
                    self.protected_level = low
                logger.debug(
                    f"BOS long: new HH close={close:.2f} "
                    f"protected_HL={self.protected_level:.2f}"
                )
            if self.protected_level and close < self.protected_level:
                logger.info(
                    f"BOS TRIGGERED (long): close={close:.2f} < "
                    f"protected_HL={self.protected_level:.2f}"
                )
                return True

        else:  # short
            if close < self.peak_close:
                self.peak_close      = close
                if self.min_dist > 0:
                    _cand = max(high, self.entry_price + self.min_dist)
                    self.protected_level = (
                        _cand if self.protected_level is None
                        else min(self.protected_level, _cand))
                else:
                    self.protected_level = high
                logger.debug(
                    f"BOS short: new LL close={close:.2f} "
                    f"protected_LH={self.protected_level:.2f}"
                )
            if self.protected_level and close > self.protected_level:
                logger.info(
                    f"BOS TRIGGERED (short): close={close:.2f} > "
                    f"protected_LH={self.protected_level:.2f}"
                )
                return True

        return False



# ══ r44 — A TRAIL FLOOR IS A FRACTION OF THE GAIN, NOT OF THE PREMIUM ═══════
# 🔴 MEASURED ON S3, 210 TRAIL-EXITED FLEET TRADES 2026-08-01..2026-09-18:
#    MFE gain    median +34.0%
#    realised    median +14.0%
#    CAPTURE     median 42.9%   — the trail gave back 57% of every good move
#    NEGATIVE    10 of 210 (5%) finished IN THE RED with the trail ARMED
# 🔴 THAT LAST ROW IS THE DEFECT, NOT THE FIRST. `floor = LOCK x current` is a
# fraction of PREMIUM, so at the +20% arm threshold an 80% lock puts the floor
# at 0.8 x 1.2 = 0.96 of entry — BELOW IT. Arming the trail could guarantee a
# loss. A gain-based floor cannot: `entry + L x (peak - entry)` is >= entry by
# construction, so those ten become structurally impossible rather than rarer.
# ⚠️ L=0.50 IS THE CONSERVATIVE END OF THE STUDY, DELIBERATELY. The simulated
# table favoured 0.60-0.70, but a higher floor exits EARLIER and can cut off
# MFE the trade only reached later — so those rows are an UPPER BOUND, not a
# promise. 0.50 beats the current median (17.0% vs 14.0%), matches its mean,
# and takes the negatives to zero without leaning on the optimistic end.
# 🔴 r91 — THE STRATEGIES WHOSE TRAIL IS STRUCTURE-ANCHORED, IN ONE PLACE.
# These are exactly the geometry-sized debits: their `stop_premium` is the
# impulsive candle's extreme rather than a flat percentage, so their trail can
# be floored on it and armed from entry (see `_update_trail`).
# ⚠️ A NAME LIST ROTS, AND IT ROTS PERMISSIVELY — §23's v3 cutoff held one, two
# of its three entries were deleted, and a new long-debit strategy was silently
# EXEMPT. It is keyed on `strategy`, which IS a trades column and therefore
# survives the rehydrate that killed `is_trend_credit` (§22); and
# `tests/check_structure_trail.py` pins this set against the strategies that
# actually declare geometry sizing, so adding one cannot silently miss here.
STRUCTURE_TRAIL_STRATEGIES = ("ORBStrategy", "Breakout")


def _is_structure_trail(record) -> bool:
    """True when this trade's stop_premium is structural, not a percentage."""
    try:
        return str(record.get("strategy") or "") in STRUCTURE_TRAIL_STRATEGIES
    except AttributeError:
        return False


def _gain_floor(entry: float, peak: float, lock: float) -> float:
    """The trail floor: keep `lock` of the gain, never give back the entry."""
    e = float(entry or 0.0)
    p = float(peak or 0.0)
    if e <= 0 or p <= e:
        return e                      # no gain yet — the floor is breakeven
    return e + (p - e) * float(lock)



_HANDOFF_NO_ENTRY_SAID: set = set()          # r317 (STALE.1): trade_ids already warned about

class ExitEngine:
    """Evaluates every open options trade on each tick."""

    def __init__(self, paper_trading: bool = PAPER_TRADING):
        self.paper_trading  = paper_trading
        self._trail_stops:  dict = {}
        # v4.5: `self._condor_ratchet` deleted with the ratchet itself.
        self._exhaust_state: dict = {}   # per-trade {ext, mom} for continuation divergence
        self._trail_active: dict = {}
        self._bos_trackers: dict = {}   # trade_id \u2192 BOSTracker (sweep only)
        self._post_target_trail: dict = {}   # trade_id \u2192 bool (ORB only)
        # VEL.1 - consecutive velocity breaches per trade. WITHOUT THIS the
        # check AttributeErrors on first call and the except swallows it,
        # leaving a permanent silent no-op.
        self._vel_breaches: dict = {}          # trade_id -> consecutive breaches
        self._trade_logger  = get_trade_logger()
        self._live_exit_alerted: set = set()  # (trade_id, kind) — one page per failure kind

    @staticmethod
    def _fvg_frame(df_1m: Optional[pd.DataFrame],
                   df_5m: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
        """v3.8: trails anchor to 5-MINUTE FVGs (structurally meaningful gaps,
        natural gamma room) when enabled and available; 1m remains the
        fallback — and stays authoritative for the structure stop and BOS,
        which are speed-critical and unchanged."""
        if USE_5M_FVG_TRAIL and df_5m is not None and len(df_5m) >= 3:
            return df_5m
        return df_1m

    def _seed_trail_from_record(self, record: TradeRecord) -> None:
        """v3.3 — recovery seed. If this trade has a persisted trail level
        (record['trail_stop'], written by position_manager v3.1) and this
        engine instance has no in-memory trail for it yet (i.e. we restarted
        mid-position), adopt the persisted level so the locked profit floor
        survives the restart. r493: any strategy whose trail was armed re-arms
        the flag (it was ADOPTED only, so the shared _update_trail re-seeded
        below the recovered level on its first armed tick)."""
        trade_id = record.get("trade_id", "")
        if not trade_id or trade_id in self._trail_stops:
            return
        try:
            persisted = float(record.get("trail_stop", 0.0) or 0.0)
        except (TypeError, ValueError):
            return
        if persisted > 0:
            self._trail_stops[trade_id] = persisted
            # r493 / EXIT.6 — re-arm wherever the uninterrupted engine WOULD be
            # armed, not only for ADOPTED: an un-armed flag sent _update_trail
            # down its first-activation branch, which wrote entry x (1 +
            # TRAIL_LOCK_PCT) over the recovered level. Armed = the persisted
            # peak reached trail_activation; with no peak on the row, a level
            # at or above the activation seed can only be an armed trail's.
            if record.get("strategy", "") == "ADOPTED" or _trail_was_armed(record, persisted):
                self._trail_active[trade_id] = True
            logger.info(
                f"Trail recovered from DB: {trade_id[:8]} trail=${persisted:.2f}"
            )




    def evaluate(self,
                 record: TradeRecord,
                 current_premium: float,
                 df_1m: Optional[pd.DataFrame] = None,
                 df_5m: Optional[pd.DataFrame] = None,
                 vol_state=None,
                 trend=None) -> ExitDecision:
        """
        Strategy-aware exit evaluation.
        Routes to the appropriate exit logic based on strategy_name.
                neutral strategies (butterfly, condor) that depend on RANGING.
        """
        strategy = record.get("strategy", "")

        # v3.3: restart recovery — re-arm the in-memory trail from the persisted
        # trail_stop column (position_manager writes it there as of v3.1;
        # stop_premium is the immutable -25% floor and is never overwritten).
        # Without this seed, a mid-trail restart would forget the locked level
        # until the trail re-armed on its own.
        self._seed_trail_from_record(record)
        _track_excursion(record, current_premium)

        # r106 — TENT FIRST: it is a credit structure and would otherwise be
        # claimed by the condor arm below, which would apply a nickel close and
        # a sibling probe to a structure that has neither.
        if is_tent(record):
            return self._evaluate_tent(record, current_premium)

        if record.get("is_butterfly"):
            return self._evaluate_butterfly(record, current_premium)
        elif strategy == "IronCondorStrategy" or is_credit_vertical(record):
            # v4.21 (AUDIT F2): route on the STRUCTURE, not one strategy string.
            # main v6.8 writes strategy="TrendCreditSpread"; the old test sent
            # every new TC.6 record to _evaluate_sweep (the DEBIT evaluator) —
            # the TC.6 branch inside the condor evaluator was unreachable for
            # every record opened after the identity fix. is_credit_vertical()
            # reads only persisted columns, so legacy rows and the rolled
            # broken wing route here too.
            return self._evaluate_condor_leg(record, current_premium, df_1m=df_1m)
        elif strategy == "ADOPTED":
            return self._evaluate_adopted(record, current_premium)
        elif strategy == "ORBStrategy":
            return self._evaluate_orb(record, current_premium, df_1m, df_5m)
        elif strategy == "RunawayContinuation":
            # ⚠️ AUDIT F10 (2026-08-20): the flagship fell into the else below —
            # a fall-through whose comment still named SweepReversal, DELETED at
            # r33. The runaway's spec (TRADES.md §1, r17) cites orb_trail_stop
            # 96%/85/+$30,696 as its exit; the sweep evaluator is a cousin, not
            # the measured family. It routes to the ORB evaluator: hard close,
            # −25% floor, theta bleed, the trail. The structure stop reads
            # `underlying_stop`, which the runaway does not set — the ORB path
            # already treats 0.0 as INERT and refuses to let an inert stop look
            # like a passing check.
            return self._evaluate_orb(record, current_premium, df_1m, df_5m)
        elif strategy == "LiquidityHunt":                       # r12: the runaway's family
            return self._evaluate_orb(record, current_premium, df_1m, df_5m)
        elif strategy == "PARK":
            # r288 (PARK.1) — its own exits; none of the sweep defaults (25% stop, trail) apply.
            return self._evaluate_park(record, current_premium)
        elif strategy == "VOLT":
            # r72 — THE CONTROL ARM GETS ITS OWN EVALUATOR, AND THAT IS THE
            # POINT. Routing it to `_evaluate_orb` would hand it theta bleed,
            # the FVG trail and the 100%-TP ladder — ORB-specific machinery
            # that would make VOLT a variant of the ORB instead of a yardstick
            # for it. Four rules, matching the operator's spec verbatim:
            # a STRUCTURE stop and a trail that arms on STOP DISTANCE.
            return self._evaluate_volt(record, current_premium, df_1m, df_5m)
        else:
            # Unknown directional strategies take the sweep rules (25% stop,
            # hard close — survivable defaults), but NEVER silently: an
            # unrouted strategy is a routing decision nobody made (F10's whole
            # mechanism). Once per trade.
            if not record.get("_unrouted_said"):
                record["_unrouted_said"] = 1
                if strategy == "Breakout":
                    # r182 (EXIT.3): no branch here BY RULING, not by omission.
                    logger.info("[exit] Breakout: no exit branch here by ruling (EXIT.3) - its "
                                "management plan acts first; this falls through to the sweep "
                                "rules as before.")
                else:
                    logger.warning("[exit] strategy %r has no exit route — "
                                   "defaulting to sweep rules. Add a branch.",
                                   strategy)
            return self._evaluate_sweep(record, current_premium, df_1m, df_5m)

    # \u2500\u2500\u2500 ORB Exit \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    _PARK_CF_SAID: set = set()

    def _evaluate_park(self, record: TradeRecord, current_premium: float) -> ExitDecision:
        """PARK exits (r288). FIRST MATCH WINS:
          1. LOCK        - armed once the BID reaches entry x (1 + PARK_LOCK_ARM); armed, out when the bid falls
                           to entry x (1 + PARK_LOCK_FLOOR). After a restart the persisted best MARK
                           (max_premium_seen, written every tick) re-arms it once - slightly looser than the
                           bid, stated (r291; r288 read mfe_premium, a column written only at the close).
          2. DELTA FLOOR - |delta| <= PARK_DELTA_FLOOR from PARK_DELTA_FROM_ET. None or 0.0 is UNREAD: hold.
          3. THE CLOSE   - at PARK_CLOSE_ET.
          4. EOD         - the schedule's own close, a backstop only.
        The bid is the r105 stash (_exit_bid); without one the mark stands in."""
        from config import (PARK_LOCK_ARM, PARK_LOCK_FLOOR, PARK_DELTA_FLOOR, PARK_DELTA_FROM_ET,
                            PARK_CLOSE_ET)
        from utils.time_utils import ET as _ET
        decision = ExitDecision()
        e = float(record.get("entry_premium", 0.0) or 0.0)
        n = float(record.get("contracts", 0) or 0)
        if e > 0:
            decision.current_pnl_pct = (current_premium - e) / e
            decision.current_pnl_usd = (current_premium - e) * n * CONTRACT_MULTIPLIER
        bid = record.get("_exit_bid")
        bid = float(bid) if bid not in (None, 0, 0.0) else float(current_premium or 0.0)
        hm = datetime.now(_ET)
        hm = (hm.hour, hm.minute)
        why = ""
        if e > 0:
            arm = e * (1 + PARK_LOCK_ARM)
            if not record.get("_park_seeded"):
                # r291 (PARK.2) — THE RESTART SEED, ONCE PER PROCESS, FROM THE COLUMN THAT IS
                # ACTUALLY WRITTEN. r288 read `mfe_premium` here, but trade_logger writes that
                # column only in log_exit (the CLOSE); the per-tick best mark lives in
                # `max_premium_seen` (update_current_premium), which SELECT * rehydrates. And
                # r288's `or mfe >= arm` ran on EVERY tick with the in-memory mark MFE, so the
                # lock armed on the mark's best print, not the bid the frozen study armed on.
                # Now: the persisted best mark is consulted once (a rehydrated record), stated
                # as a mark; afterwards only the BID arms.
                # ⚠️ max_premium_seen ONLY. The in-memory record carries mfe_premium from
                # _track_excursion (the mark, this very tick), so reading it here would arm
                # on the mark again; max_premium_seen is never set in memory, only read back.
                record["_park_seeded"] = 1
                try:
                    best = float(record.get("max_premium_seen") or 0.0)
                except (TypeError, ValueError):
                    best = 0.0
                if not record.get("_park_armed") and best >= arm:
                    record["_park_armed"] = 1
                    logger.info("[park] %s lock RE-ARMED after a restart: persisted best mark %.2f >= %.2f",
                                str(record.get("trade_id", ""))[:8], best, arm)
            if not record.get("_park_armed") and bid >= arm:
                record["_park_armed"] = 1
                logger.info("[park] %s lock ARMED: bid %.2f >= %.2f",
                            str(record.get("trade_id", ""))[:8], bid, arm)
            if record.get("_park_armed") and bid <= e * (1 + PARK_LOCK_FLOOR):
                why = f"park_lock: bid {bid:.2f} <= {e * (1 + PARK_LOCK_FLOOR):.2f} after +{PARK_LOCK_ARM:.0%}"
        d = record.get("current_delta")
        d = abs(float(d)) if d not in (None, "") else None
        if not why and hm >= tuple(PARK_DELTA_FROM_ET) and d and d <= PARK_DELTA_FLOOR:
            why = f"park_delta_floor: |delta| {d:.3f} <= {PARK_DELTA_FLOOR:.2f}"
        if not why and hm >= tuple(PARK_CLOSE_ET):
            why = "park_close_%02d:%02d_ET" % tuple(PARK_CLOSE_ET)
        if not why and _eod_due(record):
            why = _eod_label(record)
        if why:
            decision.should_exit = True
            decision.exit_reason = why
            self._park_cf(record, why, bid, current_premium, d)
            logger.info("[park] %s EXIT %s", str(record.get("trade_id", ""))[:8], why)
        return decision

    def _park_cf(self, record, why, bid, mark, delta) -> None:
        """Once per trade per process: data/counterfactual/park_exit.jsonl. Never raises."""
        tid = str(record.get("trade_id", "") or "")
        if not tid or tid in ExitEngine._PARK_CF_SAID:
            return
        ExitEngine._PARK_CF_SAID.add(tid)
        try:
            import json as _json, os as _os, time as _time
            d = _os.environ.get("OT_COUNTERFACTUAL_DIR") or _os.path.join(
                _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "data", "counterfactual")
            _os.makedirs(d, exist_ok=True)
            out = {"ts_epoch": _time.time(), "trade_id": tid, "symbol": record.get("symbol"), "rule": "park_exit",
                   "reason": why, "bid": bid, "mark": mark, "delta": delta,
                   "entry_premium": record.get("entry_premium"), "contracts": record.get("contracts"),
                   "option_symbol": record.get("option_symbol"), "streamer_symbol": record.get("streamer_symbol"),
                   "mfe_premium": record.get("mfe_premium")}
            with open(_os.path.join(d, "park_exit.jsonl"), "a") as fh:
                fh.write(_json.dumps(out) + "\n")
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[park] exit counterfactual row NOT written for %s: %s", tid[:8], exc)

    def _evaluate_volt(self, record: TradeRecord,
                       current_premium: float,
                       df_1m: Optional[pd.DataFrame],
                       df_5m: Optional[pd.DataFrame] = None) -> ExitDecision:
        """VOLT exits. FIRST MATCH WINS, and there are only four:
          1. HARD CLOSE     — the universal 15:45 flatten.
          2. CATASTROPHIC FLOOR — premium <= entry*(1-MAX_LOSS_PCT). §36 calls
                              the catastrophic cap UNIVERSAL and FOUNDATIONAL,
                              so it is not a VOLT gate and is not up for
                              simplification.
          3. STRUCTURE STOP — last CLOSED 5m candle closes through
                              `underlying_stop`, which IS THE ENTRY (OTV4TEST
                              r72: "a close beyond where the trade opened is a
                              dead thesis"), and only a bar newer than the
                              entry counts (r75). Close-based on iloc[-2] so an
                              intrabar wick survives.
          4. R-TRAIL        — arms when the UNDERLYING has travelled
                              VOLT_TRAIL_ARM_R x R in favour on 5m closes. R is
                              the signal bar's range, read back as
                              |underlying_target - entry| (|entry - stop| is 0
                              by design). Once armed the floor is
                              `entry + L x (peak - entry)` on the UNDERLYING.

        🔑 WHY THE TRAIL IS ON DISTANCE AND NOT PREMIUM — the operator's spec
        ("arms at 50% based on stop distance") and r44's scar. The old trail
        floor was a fraction of PREMIUM and could sit BELOW ENTRY: at a +20%
        arm an 80% lock floors at 0.96 of entry, so ARMING THE TRAIL COULD
        GUARANTEE A LOSS. `entry + L x (peak - entry)` is >= entry by
        construction, and measuring it on the underlying means option decay
        cannot arm or disarm it.
        """
        decision = ExitDecision()
        trade_id = str(record.get("trade_id", ""))
        entry_prem = float(record.get("entry_premium", 0.0) or 0.0)
        direction = record.get("direction", "long")
        if entry_prem > 0:
            decision.current_pnl_pct = (current_premium - entry_prem) / entry_prem
            decision.current_pnl_usd = ((current_premium - entry_prem)
                                        * float(record.get("contracts", 0) or 0)
                                        * CONTRACT_MULTIPLIER)

        # 1 ── HARD CLOSE
        # ⚠️ DERIVED from HARD_CLOSE_ET, not spelled. r71 established the rule:
        # a label reading 15:45 on a trade that closed at another minute is a
        # FALSE RECORD of what happened. The five pre-existing literals are the
        # older sites check_late_credit_window W7 pins; a NEW one would make
        # six and would go stale the day that constant moves.
        if _eod_due(record):                                   # r149: per-position EOD clock
            decision.should_exit = True
            decision.exit_reason = _eod_label(record)
            return decision

        # 2 ── CATASTROPHIC FLOOR (universal, never a VOLT decision)
        stop_prem = float(record.get("stop_premium", 0.0) or 0.0) or (
            entry_prem * (1 - MAX_LOSS_PCT))
        if stop_prem > 0 and current_premium <= stop_prem:
            decision.should_exit = True
            decision.exit_reason = (f"volt_premium_floor: {current_premium:.2f} "
                                    f"<= {stop_prem:.2f}")
            logger.info("VOLT FLOOR: %s %s", trade_id[:8], decision.exit_reason)
            return decision

        # 2b ── PAR DELTA (r79/r80/r82, EXT.1) — THE OPERATOR'S RULING,
        #    2026-09-21: *"When Delta reaches PAR, we need to get the fuck out."*
        # 🔑 AT PAR DELTA THIS IS NO LONGER AN OPTION. It is stock carrying an
        # expiry: convexity, the cheap tail and defined risk have all been
        # spent, and what remains is a 1.0-delta directional bet whose
        # give-back is dollar-for-dollar with the underlying. MEASURED LIVE on
        # 81b1afae: $45 of theta risk left against $2,880 of trail leash.
        # 🔴 r82 — DELTA ONLY. THE EXTRINSIC LIMB IS REMOVED AND THE REASON IS
        # A MEASUREMENT, NOT A PREFERENCE. r79 read extrinsic as a proxy for
        # delta and r80 promoted it to a peer; measured over the whole trade,
        # EXTRINSIC-FROM-MID REACHES ZERO AT DELTA 0.82 — 11:39 ET, mark 3.11 —
        # because an ITM 0DTE bid sits at parity and the mid carries no
        # extrinsic long before the option is actually stock. Had r80 been
        # live from entry it would have exited at 3.11 instead of 5.83,
        # costing $2,500 on this trade. Using the ask does not repair it: the
        # extrinsic is genuinely small while real optionality remains.
        # ⚠️ AND r79 NEVER NEEDED THE WIDENING. Delta crossed 0.98 at 13:44,
        # fell back to 0.9675, and crossed again at 14:11. I sampled it once in
        # the trough and concluded the rule was broken; it was about to fire.
        # ⚠️ NO DELTA MEANS HOLD, NOT GUESS (§0.5 cuts both ways). The
        # catastrophic floor and the structure stop still cover the trade, and
        # a silent proxy that fires two hours early is worse than a rung that
        # waits for its instrument.
        _delta = abs(float(record.get("current_delta", 0.0) or 0.0))
        if _delta >= VOLT_DELTA_PAR:
            decision.should_exit = True
            decision.exit_reason = (f"volt_delta_par: delta {_delta:.3f} "
                                    f">= par {VOLT_DELTA_PAR:.2f}")
            logger.info("VOLT PAR DELTA: %s %s", trade_id[:8], decision.exit_reason)
            return decision

        # 🔑 THE FRAME IS THE OPERATOR'S RULING, 2026-09-21, AND IT IS NOT A
        # DETAIL. VOLT enters off a 5-MINUTE volume bar, so its invalidation is
        # read on the frame it fires on. MEASURED over 19 sessions x 4 symbols
        # with the real plan, the SAME rule on three frames:
        #     15s closes   134 trades  win  3.7%  meanR -0.055  trail exits  4
        #     1m closes    117 trades  win  6.8%  meanR -0.030  trail exits  5
        #     5m closes     96 trades  win 18.8%  meanR +0.067  trail exits 13
        # At 1m, 93% of trades die on the stop and almost none live long enough
        # to arm the trail — the thesis never gets to express itself.
        # ⚠️ FAILS CLOSED-ISH: without the 5m frame the structure stop cannot be
        # read at all, so the trade is held on the catastrophic premium floor
        # alone. Said once per trade rather than silently.
        frame = df_5m
        _cp5 = _closed_pos(frame, now_et(), 300.0)     # r44 (BAR.1): the newest CLOSED 5m bar, by time
        # 🔴 r75 — THE BAR MUST POSTDATE THE ENTRY. Found LIVE on 2026-09-21:
        # VOLT took SEVEN trades in 90 seconds, every one stopped in ~14s by
        # `1m close 731.22 below structure` — and 731.22 was the close of the
        # 09:45 bar, which had already happened when the 09:52 trade opened.
        # The stop EQUALS the entry (r72's ruling), so any completed bar whose
        # close sits the wrong side of entry kills the trade instantly, and a
        # STALE bar does it before the trade has existed for one tick.
        # ⚠️ THE REPLAY HAD THIS GUARD AND THE SHIPPED CODE DID NOT — the
        # harness skipped closes at or before the entry, so the defect was
        # invisible in every measurement that authorised the design.
        # ⚠️ IT FAILS CLOSED: with no bar NEWER than the entry there is nothing
        # to test the thesis against yet, so the trade is held on the
        # catastrophic premium floor alone rather than exited on stale data.
        if frame is not None and len(frame) >= 2:
            try:
                _entry_ts = record.get("entry_time")
                if _entry_ts:
                    _et = pd.Timestamp(_entry_ts)
                    if _et.tzinfo is not None:
                        _et = _et.tz_convert(None)
                    _bar_ts = pd.Timestamp(frame.index[_cp5])
                    if _bar_ts.tzinfo is not None:
                        _bar_ts = _bar_ts.tz_convert(None)
                    if _bar_ts <= _et:
                        if not record.get("_volt_stale_said"):
                            record["_volt_stale_said"] = 1
                            logger.info("[exit] VOLT %s: newest completed 5m bar "
                                        "(%s) predates the entry (%s) — holding "
                                        "until a bar exists that can test it.",
                                        trade_id[:8], _bar_ts, _et)
                        return decision
            except (ValueError, TypeError, AttributeError, IndexError) as _exc:
                logger.debug("volt: entry/bar timestamp compare skipped: %s", _exc)
        if frame is None or len(frame) < 2:
            if not record.get("_volt_no5m"):
                record["_volt_no5m"] = 1
                logger.warning("[exit] VOLT %s has no 5m frame — structure stop "
                               "cannot be evaluated; premium floor is the only "
                               "stop this tick.", trade_id[:8])
            return decision
        last_close = float(frame.iloc[_cp5]["close"])
        entry_px = float(record.get("underlying_entry", 0.0) or 0.0)
        stop_px = float(record.get("underlying_stop", 0.0) or 0.0)

        # 3 ── STRUCTURE STOP — a close THROUGH the structural extreme
        if stop_px > 0:
            through = (last_close < stop_px) if direction == "long" else (last_close > stop_px)
            if through:
                decision.should_exit = True
                decision.exit_reason = (
                    f"volt_structure_stop: 5m close {last_close:.2f} "
                    f"{'below' if direction == 'long' else 'above'} "
                    f"structure {stop_px:.2f}")
                logger.info("VOLT STOP: %s %s", trade_id[:8], decision.exit_reason)
                return decision

        # 4 ── THE R-TRAIL, on the UNDERLYING
        # 🔴 R DOES NOT COME FROM THE STOP. Under r72's ruling the stop IS the
        # entry, so `abs(entry - stop)` is ZERO and a trail scaled on it would
        # NEVER ARM — the trade would hold to the structure stop or the hard
        # close with no lock, every time. R is the signal bar's range, carried
        # on the record as `underlying_target` (the plan sets target = entry +
        # 1R), so this reads it back out of a persisted column rather than
        # recomputing anything.
        target_px = float(record.get("underlying_target", 0.0) or 0.0)
        if entry_px <= 0 or target_px <= 0:
            return decision                      # inert without both ends
        risk = abs(target_px - entry_px)
        if risk <= 0:
            return decision
        gain = (last_close - entry_px) if direction == "long" else (entry_px - last_close)
        peak = float(record.get("_volt_peak", entry_px) or entry_px)
        peak = max(peak, last_close) if direction == "long" else min(peak, last_close)
        record["_volt_peak"] = peak
        if gain < VOLT_TRAIL_ARM_R * risk:
            return decision                      # not armed yet
        floor = (entry_px + VOLT_TRAIL_LOCK_FRAC * (peak - entry_px) if direction == "long"
                 else entry_px - VOLT_TRAIL_LOCK_FRAC * (entry_px - peak))
        decision.new_trail_stop = floor
        breached = (last_close < floor) if direction == "long" else (last_close > floor)
        if breached:
            decision.should_exit = True
            decision.exit_reason = (
                f"volt_trail_stop: 5m close {last_close:.2f} through the "
                f"{VOLT_TRAIL_LOCK_FRAC:.0%} lock {floor:.2f} "
                f"(armed at {VOLT_TRAIL_ARM_R:g}R, peak {peak:.2f})")
            logger.info("VOLT TRAIL: %s %s", trade_id[:8], decision.exit_reason)
        return decision

    def _evaluate_orb(self, record: TradeRecord,
                       current_premium: float,
                       df_1m: Optional[pd.DataFrame],
                       df_5m: Optional[pd.DataFrame] = None) -> ExitDecision:
        """
        ORB exit logic (v3.2 doc sync \u2014 this now matches the code below).
        Evaluated every tick, FIRST MATCH WINS:
          1. HARD CLOSE      \u2014 15:45 ET.
          2. HARD STOP       \u2014 premium <= entry * 0.75 (\u221225% floor).
                               UNCONDITIONAL, every tick, independent of trail state.
          3. STRUCTURE STOP  \u2014 last CLOSED 1m candle closes BEYOND the impulsive
                               (break) candle's wick: close < impulsive low (long) /
                               close > impulsive high (short), read from record
                               `underlying_stop`. NOT the ORB range boundary:
                               closing back INSIDE the range does NOT stop the trade.
                               (2) and (3) are an AND \u2014 premium death and thesis
                               death are caught independently, whichever fires first.
          4. THETA BLEED     \u2014 gated: held >= 20 min AND gain in [10%, 20%) AND
                               projected decay over the lookahead erases the gain.
             (velocity stall: RUNAWAY records only \u2014 OTV4TEST r2, by ruling)
          5. PAST 100% TP    \u2014 no hard exit. Trail tightens to the nearest unfilled
                               in-favor 1m FVG, floored at 85% of current premium.
          6. BELOW 100% TP   \u2014 FVG trail arms at +20%; % trail arms at +50% and
                               ratchets to 75% of current premium. Higher governs.
        NO break-of-structure exit (BOS is sweep-only). NO max-hold. The 11:00 ET
        cutoff expires the ENGINE, not an open position \u2014 a filled ORB runs to its
        own exits, up to the 15:45 hard close.
        """
        decision   = ExitDecision()
        trade_id   = record["trade_id"]
        entry_prem = record["entry_premium"]
        target     = record["target_premium"]
        trail_act  = record["trail_activation"]
        direction  = record.get("direction", "long")

        # P&L
        pnl_pct = (current_premium - entry_prem) / entry_prem if entry_prem > 0 else 0
        pnl_usd = (current_premium - entry_prem) * record["contracts"] * CONTRACT_MULTIPLIER
        decision.current_pnl_pct = pnl_pct
        decision.current_pnl_usd = pnl_usd

        # 1. HARD CLOSE
        if _eod_due(record):                                   # r149: per-position EOD clock
            decision.should_exit = True
            decision.exit_reason = _eod_label(record)
            return decision

        # 1b. HARD STOP — unconditional -25% dollar floor (v1.6). Mirrors the
        #     sweep/butterfly/adopted paths, which check the floor DIRECTLY. ORB
        #     previously relied on _update_trail for this, but that returns None
        #     below the +50% trail activation — so a trade that never armed the
        #     trail had NO floor and could bleed toward zero while the structure
        #     stop held (CRM 2026-07-09: -83%). The floor must fire every tick,
        #     regardless of trail state. As of v3.3, record['stop_premium'] is
        #     IMMUTABLE (set once at entry; trails persist in trail_stop), so
        #     this check is truthful: it fires only at the real -25% floor.
        _is_runaway = record.get("strategy") in ("RunawayContinuation", "LiquidityHunt")
        _is_hunt = record.get("strategy") == "LiquidityHunt"
        # r12 — THE HUNT TAKES OFF AT ITS TARGET'S WICK, and hands off on its rejection
        if _is_hunt:
            _ht = self._hunt_at_target(record, df_1m)
            if _ht:
                decision.should_exit = True
                decision.exit_reason = _ht
                logger.info("HUNT: %s %s", trade_id[:8], _ht)
                return decision
        # ── v4.12: REJECTED HANDOFF — a pool on our side rejected on a close ──
        _ho = self._rejected_handoff(record, direction)
        if _ho:
            decision.should_exit = True
            decision.exit_reason = _ho
            logger.info("HANDOFF: %s %s", trade_id[:8], _ho)
            return decision
        # ── v4.12: the runaway HOLDS while its thesis is true — no premium stop
        if _is_runaway:
            _rw = self._runaway_thesis_exits(record, direction, current_premium,
                                             entry_prem, pnl_pct, df_1m)
            if _rw:
                decision.should_exit = True
                decision.exit_reason = _rw
                logger.info("RUNAWAY EXIT: %s %s", trade_id[:8], _rw)
                return decision
        stop_prem = record.get("stop_premium", 0.0) or (entry_prem * (1 - MAX_LOSS_PCT))
        if _is_hunt and stop_prem > 0 and current_premium <= stop_prem:      # r209 (RUN.10): the Hunt ALONE holds
            # recorded, never acted on (operator: HOLD)
            if not record.get("_would_have_floored"):
                record["_would_have_floored"] = f"{current_premium:.2f} <= {stop_prem:.2f} pnl={pnl_pct:.1%}"
                logger.info("HUNT would-have-floored (HELD): %s %s", trade_id[:8],
                            record["_would_have_floored"])
            stop_prem = 0.0
        if stop_prem > 0 and current_premium <= stop_prem:
            decision.should_exit = True
            # label carries the record's ACTUAL floor pct (older records keep
            # their entry-time 25%; new ones carry MAX_LOSS_PCT) — truthful
            # either way for the exit_reason distributions.
            floor_pct = 1 - (stop_prem / entry_prem) if entry_prem > 0 else MAX_LOSS_PCT
            decision.exit_reason = f"hard_stop_{floor_pct:.0%} pnl={pnl_pct:.1%}"
            logger.info(
                f"ORB HARD STOP: {trade_id[:8]} prem={current_premium:.2f} "
                f"<= floor={stop_prem:.2f} (pnl={pnl_pct:.1%})"
            )
            return decision

        # 2. STRUCTURE STOP \u2014 1-min CLOSE beyond the IMPULSIVE candle's origin
        #    (v3.1). The invalidation level is the impulsive (break) candle's wick
        #    \u2014 its low for a long, its high for a short \u2014 carried on the record as
        #    `underlying_stop`, NOT the ORB range boundary. Merely closing back
        #    inside the range does NOT stop the trade: price is allowed to breathe
        #    inside the range as long as it holds the impulsive origin. Only a
        #    close PAST that origin invalidates the thesis. This is close-based on
        #    the last CLOSED candle (iloc[-2]) so an intrabar wick into the range
        #    survives; only a confirmed close beyond the origin exits. The \u201325%
        #    premium floor above is independent and still fires first if the
        #    dollars are gone (theta, retracement, or the two combined) even when
        #    this structure level is still intact \u2014 the two are an AND, not an OR.
        if df_1m is not None and len(df_1m) >= 2:
            stop_level = float(record.get("underlying_stop", 0.0) or 0.0)
            if _is_hunt and stop_level > 0:
                # r290 (HUNT.10) — THE HUNT'S BACKSTOP JUDGES ITS LINE, NOT THE BARE BOUNDARY.
                # r285 moved thesis-dead to _hunt_line (the FARTHER of the boundary and the 5m
                # swing) and said the backstop followed; it did not - this block still read
                # `underlying_stop`, the entry boundary, with no band. QQQ 2026-10-15 ddeb0fab:
                # line 721.15 logged 09:54, exited here 10:00 on a 1m close of 717.03 vs 717.01
                # (-148) with _runaway_thesis_exits having HELD it the same tick. Same line,
                # same mode rule (log/off = the boundary), read from the store each call.
                stop_level = float(self._hunt_line(record, direction, stop_level) or stop_level)
            if stop_level > 0:
                last_close = float(df_1m.iloc[_closed_pos(df_1m, now_et())]["close"])   # r44 (BAR.1)
                if direction == "long" and last_close < stop_level:
                    decision.should_exit = True
                    decision.exit_reason = (
                        f"orb_structure_stop: 1m close {last_close:.2f} "
                        f"below impulsive-candle low {stop_level:.2f}"
                    )
                    logger.info(
                        f"ORB STOP: {trade_id[:8]} 1m close={last_close:.2f} "
                        f"< impulsive_low={stop_level:.2f} \u2014 origin violated"
                    )
                    return decision
                elif direction == "short" and last_close > stop_level:
                    decision.should_exit = True
                    decision.exit_reason = (
                        f"orb_structure_stop: 1m close {last_close:.2f} "
                        f"above impulsive-candle high {stop_level:.2f}"
                    )
                    logger.info(
                        f"ORB STOP: {trade_id[:8]} 1m close={last_close:.2f} "
                        f"> impulsive_high={stop_level:.2f} \u2014 origin violated"
                    )
                    return decision

        # 2b. THETA BLEED \u2014 profitable but time is about to eat the gain
        if self._theta_bleed(record, current_premium, pnl_pct):
            decision.should_exit = True
            decision.exit_reason = f"theta_bleed pnl={pnl_pct:.1%}"
            return decision
        # 2c. VELOCITY STALL - "is this thing MOVING at all?"
        # ORDER IS DELIBERATE AND MUST NOT BE SWAPPED: theta_bleed evaluates
        # FIRST so a trade that is up 10-20% and stalled exits GREEN via that
        # path, rather than falling through to a velocity check that would
        # let it drift back toward flat before firing.
        # These are INDEPENDENT gates, never a combined score. The 2026-08-12
        # QQQ failure was two mechanisms each correctly answering "not my
        # problem" while nothing aggregated that into "then NOBODY is
        # watching." A blended score would have averaged three healthy-ish
        # signals into inaction; separate gates, any one of which can fire,
        # fails safe.
        # v4.11 (OTV4TEST r2) — no velocity stall on ORB, by ruling; the
        # runaway (same evaluator) keeps it until its own spec is untangled.
        if record.get("strategy") != "ORBStrategy":
            _vel = self._velocity_stall(record, pnl_pct, df_1m)
            if _vel is not None:
                decision.should_exit = True
                decision.exit_reason = _vel
                return decision

        # 3. PAST 100% TP \u2014 switch to tightened FVG-aware trail, no hard exit
        if current_premium >= target:
            if not self._post_target_trail.get(trade_id, False):
                self._post_target_trail[trade_id] = True
                logger.info(
                    f"ORB TARGET REACHED (no hard exit): {trade_id[:8]} "
                    f"pnl={pnl_pct:.1%} \u2014 switching to tightened FVG trail"
                )

            trail_stop = self._update_post_target_trail(
                trade_id, current_premium, record,
                self._fvg_frame(df_1m, df_5m), direction
            )
            if trail_stop is not None:
                if current_premium <= trail_stop:
                    decision.should_exit = True
                    decision.exit_reason = f"orb_fvg_trail_stop pnl={pnl_pct:.1%}"
                    return decision
                decision.new_trail_stop = trail_stop
            return decision

        # 4. TRAIL \u2014 below 100% TP: FVG-anchored once armed (+20%), plus the
        #    50% % trail; the higher of the two governs.
        if pnl_pct >= FVG_TRAIL_ARM_PCT:
            self._update_fvg_trail(trade_id, current_premium, record,
                                   self._fvg_frame(df_1m, df_5m), direction)
        trail_stop = self._update_trail(
            trade_id, current_premium, entry_prem, trail_act,
            record.get("stop_premium", 0.0) or entry_prem * (1 - MAX_LOSS_PCT),
            structure_trail=_is_structure_trail(record)
        )
        trail_stop = self._trail_stops.get(trade_id, trail_stop)
        if trail_stop is not None:
            if current_premium <= trail_stop:
                decision.should_exit = True
                decision.exit_reason = f"orb_trail_stop pnl={pnl_pct:.1%}"
                return decision
            decision.new_trail_stop = trail_stop

        return decision

    def _update_post_target_trail(self, trade_id: str, current_premium: float,
                                   record: TradeRecord,
                                   df_1m: Optional[pd.DataFrame],
                                   direction: str) -> Optional[float]:
        """
        Past 100% TP: trail tightens to track the nearest unfilled 1m FVG
        in the trade\'s favor, converted to an equivalent premium floor.
        Falls back to a tightened percentage trail (85% of current premium)
        if no usable FVG is found in the 1m data.
        """
        underlying_entry  = record.get("underlying_entry", 0.0)
        underlying_target = record.get("underlying_target", 0.0)
        entry_prem        = record["entry_premium"]

        fvg_floor_premium = None

        if df_1m is not None and underlying_entry > 0 and underlying_target > 0:
            current_underlying_move = abs(underlying_target - underlying_entry)
            fvg = _nearest_unfilled_fvg_in_favor(
                df_1m,
                current_price=underlying_target,
                direction=direction
            )
            if fvg is not None and current_underlying_move > 0:
                premium_per_point = (current_premium - entry_prem) / current_underlying_move \
                                    if current_underlying_move > 0 else 0
                if direction == "long":
                    underlying_floor = fvg.top
                else:
                    underlying_floor = fvg.bottom

                underlying_distance_from_entry = abs(underlying_floor - underlying_entry)
                fvg_floor_premium = entry_prem + (underlying_distance_from_entry * premium_per_point)

        pct_trail = current_premium * POST_TARGET_TRAIL_LOCK_PCT

        if fvg_floor_premium is not None:
            new_trail = max(fvg_floor_premium, pct_trail)
        else:
            new_trail = pct_trail
        # v3.8 CLAMP (same as _update_fvg_trail): the floor may never sit
        # tighter than FVG_FLOOR_MAX_LOCK_PCT of current premium.
        new_trail = min(new_trail, current_premium * FVG_FLOOR_MAX_LOCK_PCT)

        current_trail = self._trail_stops.get(trade_id, entry_prem)
        if new_trail > current_trail:
            self._trail_stops[trade_id] = new_trail
            logger.debug(
                f"ORB post-target trail updated: {trade_id[:8]} "
                f"trail=${self._trail_stops[trade_id]:.2f} "
                f"(fvg_based={fvg_floor_premium is not None})"
            )

        return self._trail_stops.get(trade_id)

    # ─── Long-option theta protection + general FVG trail ─────────────────────
    # ── v4.12 (OTV4TEST r3) helpers ─────────────────────────────────────
    @staticmethod
    def _entry_epoch(record) -> float:
        try:
            from datetime import datetime as _dt
            raw = record.get("entry_time")
            if isinstance(raw, (int, float)):
                return float(raw)
            if raw:
                return _dt.fromisoformat(str(raw)).timestamp()
        except Exception:                                       # noqa: BLE001
            pass
        return 0.0

    _HUNT_CF_SAID: set = set()

    def _hunt_line(self, record, direction, boundary: float) -> float:
        """r285 (HUNT.8) — the Hunt's thesis line: the FARTHER of its entry boundary and
        the 5m swing (last 3 closed RTH 5m bars ended by the entry time). Read from the
        feed store each call, so a restart decides the same; anything unreadable or
        absent keeps the boundary. OT_HUNT_STOP5M=log records and keeps the boundary."""
        mode = getattr(_cfg, "HUNT_STOP5M_MODE", "trade")
        if mode == "off" or not boundary or direction not in ("long", "short"):
            return boundary
        sw = None
        try:
            from datetime import datetime as _dt
            from zoneinfo import ZoneInfo as _Z
            from strategy.breakout_plan import swing_5m_stop
            t0 = self._entry_epoch(record)
            if t0 > 0:
                day = _dt.fromtimestamp(t0, _Z("America/New_York")).date()
                sw = swing_5m_stop(str(record.get("symbol") or getattr(_cfg, "INSTRUMENT", "") or ""), day, int(t0 * 1000),
                                   "short" if direction == "short" else "long",
                                   int(getattr(_cfg, "BRK_STOP5M_BARS", 3)))
        except Exception as exc:                                # noqa: BLE001
            sw = f"unreadable ({type(exc).__name__}: {exc})"
        line = boundary
        if isinstance(sw, float):
            line = max(boundary, sw) if direction == "short" else min(boundary, sw)
        used = line if mode == "trade" else boundary
        self._hunt_cf(record, {"event": "line", "mode": mode, "boundary": boundary,
                               "stop_5m": sw if isinstance(sw, float) else None,
                               "note": sw if isinstance(sw, str) else "", "line_used": used})
        return used

    def _hunt_cf(self, record, row: dict) -> None:
        """Once per (trade, event) per process: data/counterfactual/hunt_stop.jsonl."""
        tid = str(record.get("trade_id", "") or "")
        key = (tid, row.get("event"))
        if not tid or key in ExitEngine._HUNT_CF_SAID:
            return
        ExitEngine._HUNT_CF_SAID.add(key)
        try:
            import json as _json, os as _os, time as _time
            d = _os.environ.get("OT_COUNTERFACTUAL_DIR") or _os.path.join(
                _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "data", "counterfactual")
            _os.makedirs(d, exist_ok=True)
            out = {"ts_epoch": _time.time(), "trade_id": tid, "symbol": record.get("symbol"),
                   "rule": "hunt_stop_5m", "direction": record.get("direction"), **row}
            with open(_os.path.join(d, "hunt_stop.jsonl"), "a") as fh:
                fh.write(_json.dumps(out) + "\n")
            if row.get("event") == "line":
                logger.info("[hunt] %s thesis line %.2f (boundary %.2f, 5m %s, OT_HUNT_STOP5M=%s)",
                            tid[:8], row["line_used"], row["boundary"],
                            "-" if row.get("stop_5m") is None else f"{row['stop_5m']:.2f}", row.get("mode"))
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[hunt] stop counterfactual row NOT written for %s: %s", tid[:8], exc)

    def _hunt_at_target(self, record, df_1m) -> str:
        """The hunt's own take-off: the closed bar WICKED its target level with
        the close short of it -> off (the reversal is the sweep's trade, and
        the grant is written). A close BEYOND the target = accepted: hold on
        the runaway's exits (nothing returned here)."""
        try:
            tgt = float(record.get("underlying_target") or 0.0)
            if tgt <= 0 or df_1m is None or len(df_1m) < 2:
                return ""
            bar = df_1m.iloc[_closed_pos(df_1m, now_et())]     # r44 (BAR.1): by time, was iloc[-2]
            hi, lo, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
            d = str(record.get("direction") or "")
            wicked = (hi >= tgt and close < tgt) if d == "long" else (lo <= tgt and close > tgt)
            if wicked:
                from execution import handoff as _H
                _H.grant("LiquidityHunt", "SweepCreditSpread", tgt,
                         "call" if d == "long" else "put",
                         why=f"target {tgt:.2f} wicked (close {close:.2f}) — the reversal is the sweep's")
                return (f"hunt_target_wicked: target {tgt:.2f} reached on a wick, close {close:.2f} "
                        f"— off; handoff granted to the sweep")
        except Exception as exc:                                # noqa: BLE001
            logger.debug("hunt target read failed: %s", exc)
        return ""

    def _rejected_handoff(self, record, direction) -> str:
        """A pool on the trade's side, beyond the entry, REJECTED on a close
        since entry (derived/levels v4.1). Returns the exit reason or ""."""
        try:
            from data.derived_store import get_derived_store
            store = get_derived_store()
            if store is None:
                return ""
            import config as _cfg
            sym = str(getattr(_cfg, "INSTRUMENT", "") or "")   # the level engine's symbol
            kind = "resistance" if direction == "long" else "support"
            # 🔴 r317 (STALE.1, D1) — "since entry" needs an entry. 0.0 would ask for EVERY rejection ever written.
            since = self._entry_epoch(record)
            if since <= 0:
                _tid = record.get("trade_id")
                if _tid not in _HANDOFF_NO_ENTRY_SAID:
                    _HANDOFF_NO_ENTRY_SAID.add(_tid)
                    logger.warning("[exit] %s: entry_time %r unreadable - no rejected-pool handoff for this "
                                   "trade (STALE.1)", _tid, record.get("entry_time"))
                return ""
            r = store.latest_rejection(sym, since, kind=kind)
            if not r:
                return ""
            entry = float(record.get("underlying_entry") or 0.0)
            lvl = float(r.get("price") or 0.0)
            beyond = (lvl > entry) if direction == "long" else (lvl < entry)
            if not beyond:
                return ""
            return (f"handoff: pool {lvl:.2f} ({r.get('provenance')}) REJECTED on close "
                    f"({r.get('depth')} pierce {float(r.get('pierce_pct') or 0) * 100:.2f}%, "
                    f"bar {r.get('bar_ts')}) — sweep owns it")
        except Exception as exc:                                # noqa: BLE001
            logger.debug("handoff read failed: %s", exc)
            return ""

    def _runaway_thesis_exits(self, record, direction, current_premium, entry_prem,
                              pnl_pct, df_1m) -> str:
        """THESIS DEAD → FIZZLE, in that order. Returns the reason or ""."""
        if df_1m is None or len(df_1m) < 2:
            return ""
        try:
            hi = float(record.get("orb_range_high") or 0.0)
            lo = float(record.get("orb_range_low") or 0.0)
            if hi <= 0 or lo <= 0 or hi <= lo:
                return ""
            width = hi - lo
            tp50 = hi + width / 2 if direction == "long" else lo - width / 2
            _hunt_old = None
            if record.get("strategy") == "LiquidityHunt":
                # r12 — the hunt's thesis line is its ENTRY BOUNDARY (A1: the range
                # edge it broke; A2: the far boundary it re-entered), carried in
                # underlying_stop. The 50% level means nothing to it.
                tp50 = float(record.get("underlying_stop") or 0.0) or tp50
                # r285 (HUNT.8) — and no nearer than the 5m swing as of entry.
                _hunt_old = tp50
                tp50 = self._hunt_line(record, direction, tp50)
            _now_c = now_et()                                   # r44 (BAR.1): one clock for both reads
            last_close = float(df_1m.iloc[_closed_pos(df_1m, _now_c)]["close"])
            # ══ r44 — THE LINE HAS A WIDTH, BECAUSE THE LEVEL DOES ═══════════
            # 🔴 THIS TEST HAD ZERO TOLERANCE AND IT COST A 2.68 POINT MOVE.
            # 2026-09-18: the hunt's line was 718.50, the 09:52 bar closed
            # 718.57 — SEVEN CENTS — and the thesis was declared dead at
            # 09:53:31. Price then fell to 715.89. The trade was directionally
            # right and was stopped by an overshoot SMALLER THAN ONE TYPICAL
            # BAR'S WICK (median 1m wick on this instrument: 0.078).
            # 🔑 THE BAND IS THE LEVEL'S OWN PRECISION, NOT A FUDGE. A line
            # derived from a session extreme is exact to about one bar of
            # noise; asserting it to the cent asserts a precision the level
            # never had. This is r39's zone reasoning one timeframe down — and
            # like the zone width it is MEASURED from the instrument's own
            # tape, never a fixed cent amount, because a constant that suits
            # QQQ is wrong on MU by four-fold.
            band = 0.0
            try:
                _w = df_1m.tail(THESIS_BAND_LOOKBACK)
                _bh = _w[["open", "close"]].max(axis=1)
                _bl = _w[["open", "close"]].min(axis=1)
                _wick = (_w["high"] - _bh).combine(_bl - _w["low"], max)
                band = float(_wick.median()) * THESIS_BAND_WICKS
            except Exception as exc:                            # noqa: BLE001
                # ⚠️ NO BAND IS THE OLD BEHAVIOUR, and it FAILS TIGHT rather
                # than wide: an unmeasurable tape exits sooner, never later.
                logger.debug("thesis band unmeasurable, using 0: %s", exc)
                band = 0.0
            lost = (last_close < tp50 - band if direction == "long"
                    else last_close > tp50 + band)
            if _hunt_old is not None and not lost and _hunt_old != tp50:
                _old_lost = (last_close < _hunt_old - band if direction == "long"
                             else last_close > _hunt_old + band)
                if _old_lost:
                    self._hunt_cf(record, {"event": "old_line_would_exit", "line_old": _hunt_old,
                                           "line_used": tp50, "last_close": last_close, "band": band,
                                           "mark": current_premium, "entry_premium": entry_prem})
            if lost:
                # ⚠️ THE LABEL NAMES THE STRATEGY IT FIRED FOR. "runaway_thesis_dead"
                # on a LiquidityHunt row cost a wrong diagnosis on 2026-09-18:
                # the line used IS the hunt's own boundary (above), but the
                # reason string said another strategy had killed it.
                _who = ("hunt_thesis_dead" if record.get("strategy") == "LiquidityHunt"
                        else "runaway_thesis_dead")
                return (f"{_who}: 1m close {last_close:.2f} back through "
                        f"{tp50:.2f} (band {band:.3f})")
            # ── fizzle, on the bars since entry ──
            t0 = self._entry_epoch(record)
            bars = _closed_part(df_1m, _now_c)                  # r44 (BAR.1): by time, was iloc[:-1]
            if t0 > 0:
                try:
                    bars = bars[bars.index.map(lambda x: x.timestamp()) >= t0]
                except Exception:                               # noqa: BLE001
                    pass
            n = len(bars)
            events, dials = [], []
            if n >= 4:
                highs = bars["high"].astype(float); lows = bars["low"].astype(float)
                closes = bars["close"].astype(float)
                # EVENT: higher-low broken (short: lower-high broken)
                if direction == "long":
                    pull = lows.iloc[:-1].rolling(3).min().dropna()
                    if len(pull) and closes.iloc[-1] < float(pull.iloc[-1]):
                        events.append(f"higher_low_broken {closes.iloc[-1]:.2f}<{float(pull.iloc[-1]):.2f}")
                else:
                    pull = highs.iloc[:-1].rolling(3).max().dropna()
                    if len(pull) and closes.iloc[-1] > float(pull.iloc[-1]):
                        events.append(f"lower_high_broken {closes.iloc[-1]:.2f}>{float(pull.iloc[-1]):.2f}")
                # EVENT: VWAP recrossed (only when the frame carries volume)
                if "volume" in bars.columns:
                    v = bars["volume"].astype(float)
                    if float(v.sum()) > 0:
                        # r221 — NOT the session VWAP. This is a volume-weighted mean of the
                        # closes in the bars handed to this evaluator (since entry). The session
                        # VWAP is derived.anchors.vwap_now(). The event label is unchanged.
                        entry_vwap = float((closes * v).sum() / v.sum())
                        if (direction == "long" and closes.iloc[-1] < entry_vwap) or \
                           (direction == "short" and closes.iloc[-1] > entry_vwap):
                            events.append(f"vwap_recross {closes.iloc[-1]:.2f} vs {entry_vwap:.2f}")
                # DIAL: acceptance decaying
                try:
                    from analysis.trend_strength import measure
                    ts = measure(bars, direction, min_bars=4)
                    ad, ar = getattr(ts, "acc_delta", None), getattr(ts, "acc_recent", None)
                    if ad is not None and ar is not None and ad < 0 and ar < 0.5:
                        dials.append(f"acceptance_decay delta={ad:.2f} recent={ar:.2f}")
                except Exception:                               # noqa: BLE001
                    pass
                # DIAL: range contracting against the first bars since entry
                rng = (highs - lows)
                k = min(3, n // 2)
                if k >= 2 and float(rng.iloc[:k].mean()) > 0:
                    ratio = float(rng.iloc[-k:].mean()) / float(rng.iloc[:k].mean())
                    if ratio < 0.5:
                        dials.append(f"range_contraction {ratio:.2f}x")
                # DIAL: premium diverging from the underlying
                peak = max(float(record.get("_rw_peak_premium") or 0.0), float(current_premium))
                record["_rw_peak_premium"] = peak
                recent_hi = float(highs.iloc[-3:].max()) if direction == "long" else float(lows.iloc[-3:].min())
                prior = float(highs.iloc[:-3].max()) if direction == "long" else float(lows.iloc[:-3].min())
                new_underlying_extreme = (recent_hi > prior) if direction == "long" else (recent_hi < prior)
                if peak > 0 and new_underlying_extreme and current_premium < peak * 0.9:
                    dials.append(f"premium_divergence {current_premium:.2f} vs peak {peak:.2f}")
            record["_fizzle_read"] = f"events={events} dials={dials}"
            if len(events) >= 2 or (len(events) >= 1 and len(dials) >= 1):
                # r285 (HUNT.8) — a Hunt held on its 5m line is not cut by a 1m fizzle read
                # (10-14: the fizzle fires on the same 1m bounce the 5m line holds through).
                # Recorded once as what the old rule would have done.
                if (_hunt_old is not None and getattr(_cfg, "HUNT_STOP5M_MODE", "trade") == "trade"
                        and tp50 != _hunt_old):
                    self._hunt_cf(record, {"event": "fizzle_would_exit", "why": "; ".join(events + dials),
                                           "last_close": last_close, "line_used": tp50,
                                           "mark": current_premium, "entry_premium": entry_prem})
                else:
                    return f"runaway_fizzle: {'; '.join(events + dials)}"
            # ── structure backstop: a close back through the boundary ──
            boundary = hi if direction == "long" else lo
            if record.get("strategy") == "LiquidityHunt":
                boundary = float(record.get("underlying_stop") or 0.0) or boundary   # r12: its entry boundary
                if _hunt_old is not None:
                    boundary = tp50          # r285 (HUNT.8): the same line the thesis test used
            crossed = last_close < boundary if direction == "long" else last_close > boundary
            if crossed:
                return (f"runaway_backstop: 1m close {last_close:.2f} through the ORB boundary "
                        f"{boundary:.2f}")
        except Exception as exc:                                # noqa: BLE001
            logger.warning("runaway thesis read failed: %s", exc)
        return ""

    def _final_form_floor(self, record, current_premium) -> str:
        """Rolled structure: exit when the GROUP's cost to close has grown
        TENT_FLOOR_PCT from the as-formed basis. Returns the reason or ""."""
        try:
            grp = record.get("final_form_group")
            basis = float(record.get("final_form_basis") or 0.0)
            if not grp or basis <= 0:
                return ""
            from config import TENT_FLOOR_PCT
            from database.trade_logger import get_trade_logger
            tl = get_trade_logger()
            total = float(current_premium or 0.0)
            if tl is not None:
                for t in tl.get_open_trades():
                    if t.get("final_form_group") == grp and t.get("trade_id") != record.get("trade_id"):
                        total += float(t.get("current_premium") or t.get("entry_premium") or 0.0)
            if total >= basis * (1.0 + TENT_FLOOR_PCT):
                return (f"final_form_floor: structure costs {total:.2f} to close vs basis "
                        f"{basis:.2f} as formed (+{TENT_FLOOR_PCT:.0%}) — the premise has gone "
                        f"wrong; out together")
        except Exception as exc:                                # noqa: BLE001
            logger.debug("final-form read failed: %s", exc)
        return ""

    def _sweep_breach_accepted(self, record, df_1m) -> str:
        """SWEEP verticals only. The pool BREACHED since entry, on the operator's
        definition -> the exit reason, else "".

        r120 — `derived/level_rules.judge` over the 1m bars since the entry
        minute, INCLUDING the forming bar: a close beyond the pool, then the next
        bar's OPEN beyond it. The forming bar contributes only its open to that
        verdict (judge() reads the open first and stops at the breach); its
        partial high/low/close can at most open a pending that nothing yet
        follows. Judging every bar since entry, not the last pair, means a
        breach is not forgotten because one poll missed its minute — a breached
        level is dead (the book retires it for good)."""
        try:
            if str(record.get("setup_type") or "") != "sweep_credit_spread":
                return ""
            pool = float(record.get("pool_price") or 0.0)
            if pool <= 0 or df_1m is None or len(df_1m) < 2:
                return ""
            import pandas as pd
            from derived import level_rules as LR
            side = LR.RESISTANCE if str(record.get("option_side") or "") == "call" else LR.SUPPORT
            idx = df_1m.index
            since = None
            try:
                et = pd.Timestamp(str(record.get("entry_time") or ""))
                tz = getattr(idx, "tz", None)
                if tz is not None:
                    et = (et.tz_localize("UTC") if et.tzinfo is None else et).tz_convert(tz)
                elif et.tzinfo is not None:
                    et = et.tz_convert("America/New_York").tz_localize(None)
                since = et.floor("min")
            except Exception:                                   # noqa: BLE001
                since = None
            if since is None:
                return ""                                       # no entry minute, no judgement
            frame = df_1m[idx >= since]
            if len(frame) < 2:
                return ""
            bars = [(i, float(r.open), float(r.high), float(r.low), float(r.close))
                    for i, r in enumerate(frame.itertuples())]
            events = LR.judge(bars, (pool, pool), side)
            at = LR.first(events, LR.BREACHED)
            if at is None:
                return ""
            c_prev, o_now = bars[at - 1][4], bars[at][1]
            when = frame.index[at]
            return (f"sweep_breach_accepted: BREACHED — 1m close {c_prev:.2f} beyond the pool "
                    f"{pool:.2f}, next open {o_now:.2f} beyond ({when:%H:%M}) — the level is SPENT")
        except Exception as exc:                                # noqa: BLE001
            logger.debug("sweep breach read failed: %s", exc)
        return ""

    def _velocity_stall(self, record: TradeRecord, pnl_pct: float,
                        df_1m) -> Optional[str]:
        """Is the underlying still delivering fast enough to beat decay?

        Returns an exit_reason when the position should be cut, else None.
        NEVER RAISES - an exit path that can throw is worse than one that
        occasionally declines to act.

        THE QUESTION NOTHING ELSE ASKS. `orb_structure_stop` asks whether the
        thesis broke; `_theta_bleed` asks whether a GAIN is about to evaporate
        (its gate 1 is a gain floor, so a LOSING position is invisible to it).
        A losing position that has STOPPED MOVING answers no to both, and the
        -40% percentage floor eventually catching it is the ABSENCE of a
        mechanism rather than one. On 2026-08-12 that cost a QQQ trade 50
        minutes and -42.2% while the underlying sat BELOW the short entry the
        entire time - directionally right, and bleeding anyway.

        NO TARGET IS USED. bev = |theta| / (|delta| * 1440) is the option's own
        physics, so this generalises to EVERY long-premium strategy rather than
        only ORB. The target-based form of the same idea was MEASURED AND
        REJECTED: feasibility ratio at entry ran HIGHER for losers than winners
        at every percentile (losers p50 5.05 vs winners 3.87, n=145) - a wide
        range gives a distant target AND a big required move, so feasibility and
        difficulty turn out to be the same axis pointing opposite ways. Do not
        reintroduce it.

        FOUR GATES:
          (1) GRACE    - no evaluation before VELOCITY_GRACE_MIN. Forced by the
                         data, not chosen: winners p10 at 5 minutes is -21.1,
                         i.e. the bottom decile of eventual WINNERS was moving
                         AWAY. Any earlier check kills those trades.
          (2) MEASURED - a strategy with no measured floor is evaluated and
                         LOGGED but never cut, whatever ENFORCE says.
          (3) FLOOR    - ratio must hold above winners-p10 * STRICTNESS at the
                         largest mark <= held.
          (4) CONFIRM  - VELOCITY_CONFIRM_TICKS consecutive breaches. QQQ crossed
                         back ABOVE breakeven at minutes 41-61 before dying at
                         70; a single-tick rule oscillates.
        """
        try:
            if not VELOCITY_STALL_ENABLED:
                return None
            trade_id = str(record.get("trade_id", ""))
            entry_time = record.get("entry_time")
            if not entry_time:
                return None
            entry_dt = entry_time if isinstance(entry_time, datetime) else None
            if entry_dt is None:
                try:
                    entry_dt = datetime.fromisoformat(str(entry_time))
                except ValueError:
                    return None
            held = minutes_since(entry_dt)
            if held < VELOCITY_GRACE_MIN:                      # (1) grace
                self._vel_breaches.pop(trade_id, None)
                return None
            delta = abs(float(record.get("current_delta", 0.0) or 0.0))
            theta = abs(float(record.get("current_theta", 0.0) or 0.0))
            if delta <= 1e-6 or theta <= 0.0:
                return None                    # no live Greeks -> do not guess
            und_entry = float(record.get("underlying_entry", 0.0) or 0.0)
            if und_entry <= 0 or df_1m is None or len(df_1m) == 0:
                return None
            und_now = float(df_1m["close"].iloc[-1])
            short = str(record.get("direction", "")) == "short"
            travelled = (und_entry - und_now) if short else (und_now - und_entry)
            delivered = travelled / max(held, 1e-9)
            bev = theta / (delta * 1440.0)
            if bev <= 0:
                return None
            ratio = delivered / bev
            marks = [m for m in sorted(VELOCITY_FLOOR_BY_MIN) if m <= held]
            if not marks:
                return None
            floor = VELOCITY_FLOOR_BY_MIN[marks[-1]] * VELOCITY_STRICTNESS
            if ratio >= floor:                                 # (3) floor
                self._vel_breaches.pop(trade_id, None)
                return None
            n = self._vel_breaches.get(trade_id, 0) + 1
            self._vel_breaches[trade_id] = n
            if n < VELOCITY_CONFIRM_TICKS:                     # (4) confirm
                return None
            strategy = str(record.get("strategy", ""))
            measured = strategy in VELOCITY_MEASURED_STRATEGIES
            if not (VELOCITY_STALL_ENFORCE and measured):      # (2) measured
                logger.info(
                    "VELOCITY STALL (observe-only%s): %s %s held=%.1fm "
                    "ratio=%.1f floor=%.1f delivered=%.4f bev=%.4f pnl=%.1f%%",
                    "" if measured else ", UNMEASURED strategy",
                    trade_id[:8], strategy, held, ratio, floor,
                    delivered, bev, pnl_pct * 100.0)
                return None
            logger.info(
                "VELOCITY STALL EXIT: %s held=%.1fm ratio=%.1f < floor=%.1f "
                "(delivered %.4f pts/min vs breakeven %.4f) pnl=%.1f%%",
                trade_id[:8], held, ratio, floor, delivered, bev,
                pnl_pct * 100.0)
            return (f"velocity_stall ratio={ratio:.1f}<{floor:.1f} "
                    f"held={held:.0f}m")
        except Exception as exc:                                # noqa: BLE001
            logger.debug("velocity stall check failed: %s", exc)
            return None

    def _theta_bleed(self, record: TradeRecord, current_premium: float,
                     pnl_pct: float) -> bool:
        """True only when a long has EARNED a real, sub-trail gain that time
        decay is now projected to erase — AND has been given room to develop
        first. Four gates (see v1.5 header) bound what was previously a
        first-green-tick guillotine:
          (1) GAIN FLOOR    — skip a trivial winner (< THETA_MIN_GAIN_PCT).
          (2) TRAIL CEILING — once up >= FVG_TRAIL_ARM_PCT the trail owns the
                              trade; theta stays silent so trends run.
          (3) MIN HOLD      — a THETA_MIN_HOLD_MIN blackout after entry lets the
                              move develop before the clock can cut it.
          (4) DECAY vs GAIN — only then, if projected decay over the lookahead
                              erases the gain, exit. Theta is $/share/CALENDAR
                              day, so scale the lookahead by 1440 min/day.
        Active window: held >= THETA_MIN_HOLD_MIN AND gain in
        [THETA_MIN_GAIN_PCT, FVG_TRAIL_ARM_PCT) AND stalling to theta."""
        # (1) gain floor — a tiny green is not worth protecting
        if pnl_pct < THETA_MIN_GAIN_PCT:
            return False
        # (2) trail ceiling — a running trade belongs to the trail, not theta
        if pnl_pct >= FVG_TRAIL_ARM_PCT:
            return False
        # (3) min-hold blackout — give the move room before the clock can cut it
        entry_time = record.get("entry_time")
        if not entry_time:
            return False                       # can't verify hold ⇒ don't cut
        entry_dt = entry_time if isinstance(entry_time, datetime) else None
        if entry_dt is None:
            try:
                entry_dt = datetime.fromisoformat(str(entry_time))
            except ValueError:
                return False
        if minutes_since(entry_dt) < THETA_MIN_HOLD_MIN:
            return False
        # (4) projected decay vs current gain
        theta = abs(float(record.get("current_theta", 0.0) or 0.0))  # $/share/CAL day
        if theta <= 0:
            return False
        gain_per_share = current_premium - record["entry_premium"]
        if gain_per_share <= 0:
            return False
        proj_decay = theta * (THETA_LOOKAHEAD_MIN / MINUTES_PER_CALENDAR_DAY)
        return proj_decay >= gain_per_share

    def _update_fvg_trail(self, trade_id: str, current_premium: float,
                          record: TradeRecord, df_1m: Optional[pd.DataFrame],
                          direction: str) -> Optional[float]:
        """FVG-anchored trailing stop for a long, armed once profitable. The
        stop parks at the FAR edge of the nearest unfilled in-favor 1m FVG
        (converted to an equivalent premium floor) so the trade has room to pull
        back INTO the gap for continuation; only a move beyond the gap exits.
        Falls back to a % lock of current premium when no usable FVG exists.
        Writes to the shared _trail_stops (highest trail wins)."""
        entry_prem       = record["entry_premium"]
        underlying_entry = record.get("underlying_entry", 0.0)
        fvg_floor_premium = None

        if df_1m is not None and len(df_1m) > 0 and underlying_entry > 0:
            cur_under = float(df_1m["close"].iloc[-1])
            move_from_entry = abs(cur_under - underlying_entry)
            fvg = _nearest_unfilled_fvg_in_favor(df_1m, current_price=cur_under,
                                                 direction=direction)
            if fvg is not None and move_from_entry > 0:
                premium_per_point = (current_premium - entry_prem) / move_from_entry
                # FAR edge → room to wick INTO the gap before exiting
                underlying_floor = fvg.bottom if direction == "long" else fvg.top
                dist = abs(underlying_floor - underlying_entry)
                fvg_floor_premium = entry_prem + dist * premium_per_point

        # r44 — was `current_premium * FVG_TRAIL_LOCK_PCT`. Same defect, same fix:
        # a fraction of the GAIN, floored at entry.
        pct_trail = _gain_floor(entry_prem, current_premium, TRAIL_GAIN_LOCK)
        new_trail = max(fvg_floor_premium, pct_trail) if fvg_floor_premium is not None else pct_trail
        # v3.8 CLAMP: an FVG hugging price must not turn the leash into a
        # tripwire — the floor may never sit tighter than
        # FVG_FLOOR_MAX_LOCK_PCT of current premium.
        new_trail = min(new_trail, current_premium * FVG_FLOOR_MAX_LOCK_PCT)

        current_trail = self._trail_stops.get(trade_id, entry_prem)
        if new_trail > current_trail:
            self._trail_stops[trade_id] = new_trail
            logger.debug(
                f"FVG trail: {trade_id[:8]} trail=${self._trail_stops[trade_id]:.2f} "
                f"(fvg_based={fvg_floor_premium is not None})"
            )
        return self._trail_stops.get(trade_id)

    # ─── Sweep Reversal Exit ──────────────────────────────────────────────────

    def _evaluate_sweep(self, record: TradeRecord,
                         current_premium: float,
                         df_1m: Optional[pd.DataFrame],
                         df_5m: Optional[pd.DataFrame] = None) -> ExitDecision:
        """
        Sweep reversal exit logic:
        - Hard stop: 25% premium loss
        - BOS: 1-min break of structure against position
        - TP: 100% of premium
        - Trail: activates at 50% TP
        """
        decision   = ExitDecision()
        trade_id   = record["trade_id"]
        entry_prem = record["entry_premium"]
        stop_prem  = record["stop_premium"]
        target     = record["target_premium"]
        trail_act  = record["trail_activation"]
        direction  = record.get("direction", "long")

        pnl_pct = (current_premium - entry_prem) / entry_prem if entry_prem > 0 else 0
        pnl_usd = (current_premium - entry_prem) * record["contracts"] * CONTRACT_MULTIPLIER
        decision.current_pnl_pct = pnl_pct
        decision.current_pnl_usd = pnl_usd

        # 1. HARD CLOSE
        if _eod_due(record):                                   # r149: per-position EOD clock
            decision.should_exit = True
            decision.exit_reason = _eod_label(record)
            return decision

        # 2. HARD STOP
        if current_premium <= stop_prem:
            decision.should_exit = True
            decision.exit_reason = f"stop_hit pnl={pnl_pct:.1%}"
            return decision

        # 3. TARGET — v3.8 RUNNER MODE (SWEEP_POST_TARGET_TRAIL, default on):
        #    sweeps get the same post-target treatment as ORB — no hard TP,
        #    the trade switches to the tightened FVG-aware trail and runs
        #    until the market takes some back. This was the ONE hard
        #    take-profit among directionals; env OT_SWEEP_POST_TARGET_TRAIL=
        #    False restores the +100% target_hit for A/B.
        if current_premium >= target:
            if not SWEEP_POST_TARGET_TRAIL:
                decision.should_exit = True
                decision.exit_reason = f"target_hit pnl={pnl_pct:.1%}"
                return decision
            if not self._post_target_trail.get(trade_id, False):
                self._post_target_trail[trade_id] = True
                logger.info(f"SWEEP TARGET REACHED (runner mode, no hard exit): "
                            f"{trade_id[:8]} pnl={pnl_pct:.1%}")
            trail_stop = self._update_post_target_trail(
                trade_id, current_premium, record,
                self._fvg_frame(df_1m, df_5m), direction
            )
            if trail_stop is not None:
                if current_premium <= trail_stop:
                    decision.should_exit = True
                    decision.exit_reason = f"post_target_trail pnl={pnl_pct:.1%}"
                    return decision
                decision.new_trail_stop = trail_stop
            return decision

        # 4. BOS EXIT \u2014 RETIRED (r167). Operator, 2026-08-27: *"The other
        #    variables for the other strategies were all good except for the
        #    BOS. I believe that one was overall a loser."* Measured: 34% /
        #    217 trades / -$7,085 with the largest single loss in the v3 book
        #    (TRADES.md). The tracker class stays for the counterfactual
        #    recorder; nothing here may close a trade on it.

        # 4b. THETA BLEED \u2014 profitable but time is about to eat the gain
        if self._theta_bleed(record, current_premium, pnl_pct):
            decision.should_exit = True
            decision.exit_reason = f"theta_bleed pnl={pnl_pct:.1%}"
            return decision

        # 5. TRAIL \u2014 FVG-anchored once armed (+20%), plus the 50% % trail; the
        #    higher of the two governs (both write to _trail_stops).
        if pnl_pct >= FVG_TRAIL_ARM_PCT:
            self._update_fvg_trail(trade_id, current_premium, record,
                                   self._fvg_frame(df_1m, df_5m), direction)
        trail_stop = self._update_trail(
            trade_id, current_premium, entry_prem, trail_act, stop_prem,
            structure_trail=_is_structure_trail(record)
        )
        trail_stop = self._trail_stops.get(trade_id, trail_stop)
        if trail_stop is not None:
            if current_premium <= trail_stop:
                decision.should_exit = True
                decision.exit_reason = f"trail_stop_hit pnl={pnl_pct:.1%}"
                return decision
            decision.new_trail_stop = trail_stop

        return decision

    # \u2500\u2500\u2500 Butterfly Exit \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def _evaluate_butterfly(self, record: TradeRecord,
                             current_premium: float) -> ExitDecision:
        """
        Butterfly exit logic:
        - Max hold: 2.5 hours
        - Hard stop: net value <= 25% loss   (SL: 25% of net debit)
        - Target: BUTTERFLY_TP_PCT = 20% of max profit  (was documented as 25%)
        - No BOS, no trail
        """
        decision     = ExitDecision()
        trade_id     = record["trade_id"]
        entry_prem   = record["entry_premium"]
        stop_prem    = record["stop_premium"]
        target       = record["target_premium"]
        entry_time   = record["entry_time"]

        pnl_pct = (current_premium - entry_prem) / entry_prem if entry_prem > 0 else 0
        pnl_usd = (current_premium - entry_prem) * record["contracts"] * CONTRACT_MULTIPLIER
        decision.current_pnl_pct = pnl_pct
        decision.current_pnl_usd = pnl_usd

        # 1. HARD CLOSE
        if _eod_due(record):                                   # r149: per-position EOD clock
            decision.should_exit = True
            decision.exit_reason = _eod_label(record)
            return decision

        # "BREAKOUT_VOLATILE"}`. v4 hardcodes the label to UNKNOWN, so this
        # butterfly exit HAS NEVER RUN — not once since the port.
        #
        # ⚠️ THIS IS AN EXIT, NOT AN ENTRY, AND THAT IS WHY IT MATTERS. F0 was
        # "every intraday exit was dead code" because the class was bisected;
        # these were dead for a quieter reason — a label nothing computes — and
        # so they were not in F0's blast radius and nobody looked. A butterfly
        # whose neutral assumption breaks now holds to its stop or its clock.
        #
        # ⚠️ IF THIS PROTECTION IS WANTED BACK it must be rebuilt on something
        # v4 MEASURES — the trend engine's direction and ADX are right there in
        # the context. Do NOT resurrect it on a label. Operator's direction:
        # if the idea returns it returns under a different name.

        # 3. MAX HOLD — RETIRED (r169). Operator, 2026-08-27, on the butterfly:
        #    "I want both adjusted for best case. 1545 flatten or 25% loss.
        #    Whichever comes first." A pin play pays as the wings die into the
        #    close; a 150-minute clock sold the thesis before it finished.
        # 3. HARD STOP
        if current_premium <= stop_prem:
            decision.should_exit = True
            decision.exit_reason = f"stop_hit pnl={pnl_pct:.1%}"
            return decision

        # 4. TARGET — RETIRED (r169), same ruling. A perfectly pinned fly is
        #    worth the full width at the apex at the close; the 20%-of-max
        #    target (0.34 on a 1.00-wide fly bought for 0.18) left four
        #    fifths of that on the table. The fly rides to the 15:45 flatten
        #    or the 25% floor, whichever comes first. `target` stays on the
        #    record for the plan's row; nothing acts on it.

        return decision

    # \u2500\u2500\u2500 Shared Helpers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def _condor_sibling_open(self, record, default: bool = True) -> bool:
        """True if the OPPOSITE side of this symbol's condor is also open.

        The user's deconfliction rule used as a STATE CHECK: one leg open =
        standalone (take-profit applies); both open = a real condor (hold for
        the roll — the only reason to close one is the roll). Needs no
        look-ahead; structure state is knowable at every instant.
        On any error, returns `default`. 🔴 CND.11 — the except returned True
        UNCONDITIONALLY and ignored `default`, so the stop path, which passes
        default=False precisely so an error leaves the 15% stop ARMED, got
        True instead: the stop was SUPPRESSED on a lone vertical whenever the
        probe failed — the stopless ride its own comment calls the worse loss.
        Found by OTV4TEST's audit (shared). True stays the default for a TP
        caller, where wrongly TPing a condor leg is the costlier mistake.
        """
        try:
            from database.trade_logger import get_trade_logger
            tl = get_trade_logger()
            if tl is None:
                return False
            me = record.get("option_side", "")
            for t in tl.get_open_trades():
                if (t.get("is_condor_leg")
                        and t.get("symbol") == record.get("symbol")
                        and t.get("trade_id") != record.get("trade_id")
                        and t.get("option_side") and t.get("option_side") != me):
                    return True
            return False
        except Exception:
            return default

    def _condor_sibling_id(self, record) -> str:
        """v4.4 — trade_id of the open complementary leg, '' if none/unknown.
        Forensics only; never raises, never drives the suppression decision
        (that is `_condor_sibling_open`)."""
        try:
            from database.trade_logger import get_trade_logger
            tl = get_trade_logger()
            if tl is None:
                return ""
            me = record.get("option_side", "")
            for t in tl.get_open_trades():
                if (t.get("is_condor_leg")
                        and t.get("symbol") == record.get("symbol")
                        and t.get("trade_id") != record.get("trade_id")
                        and t.get("option_side") and t.get("option_side") != me):
                    return str(t.get("trade_id") or "")
            return ""
        except Exception:                                       # noqa: BLE001
            return ""

    def _sync_stop_suppression(self, record, hedged: bool) -> None:
        """v4.4 — edge-triggered bookkeeping for the condor stop suppression.

        Writes stop_suppressed_ts / stop_suppressed_by on the SUPPRESS edge
        and clears them on the RE-ARM edge. NEW FIELDS, not a mutation of
        stop_premium — trade_logger v3.1 records why overwriting the floor
        mislabels exits, and this must not re-create that bug in a new
        disguise. Edge detection reads the persisted field itself, so it is
        restart-safe with no in-memory state (same reasoning as F4). A
        suppression and a re-arm are decisions with money attached: both are
        announced at INFO, once per flip. Bookkeeping failure must never kill
        the exit evaluation — everything here is best-effort."""
        try:
            suppressed = bool(record.get("stop_suppressed_ts"))
            if hedged and not suppressed:
                from utils.time_utils import ET
                ts  = datetime.now(ET).isoformat(timespec="seconds")
                sib = self._condor_sibling_id(record)
                record["stop_suppressed_ts"] = ts
                record["stop_suppressed_by"] = sib
                if self._trade_logger:
                    self._trade_logger.update_fields(
                        record["trade_id"],
                        stop_suppressed_ts=ts, stop_suppressed_by=sib)
                logger.info(
                    "CONDOR STOP SUPPRESSED %s: complement %s open — per-leg "
                    "premium stop off (operator ruling 2026-08-24); structure "
                    "managed by roll / nickel / 15:45 close",
                    str(record.get("trade_id", ""))[:8], (sib or "?")[:8])
            elif (not hedged) and suppressed:
                record["stop_suppressed_ts"] = ""
                record["stop_suppressed_by"] = ""
                if self._trade_logger:
                    self._trade_logger.update_fields(
                        record["trade_id"],
                        stop_suppressed_ts="", stop_suppressed_by="")
                logger.info(
                    "CONDOR STOP RE-ARMED %s: leg is alone again — lone stop "
                    "floor active", str(record.get("trade_id", ""))[:8])
        except Exception as exc:                                # noqa: BLE001
            logger.debug("stop-suppression bookkeeping: %s", exc)

    @staticmethod
    def _held_minutes(record) -> float:
        try:
            et = record.get("entry_time")
            if not et:
                return 0.0
            t = datetime.fromisoformat(str(et).replace("Z", "+00:00"))
            # r125 — the NAIVE fallback compared a UTC box clock against an
            # entry_time with no zone, so a mixed pair silently measured hold
            # time in the wrong frame. Records carry +00:00 today, making this
            # unreachable — fixed anyway, because "unreachable" is what the
            # 15:40 flatten branch was too.
            from utils.time_utils import ET as _ET
            now = datetime.now(t.tzinfo) if t.tzinfo else datetime.now(_ET)
            return (now - t).total_seconds() / 60.0
        except Exception:
            return 0.0

    def _evaluate_condor_leg(self, record: TradeRecord,
                              current_premium: float,
                              df_1m=None) -> ExitDecision:
        """
        Iron condor leg exit logic.
        Each leg is a credit spread — rising spread value = losing money.

          - Call spread: only exit on TRENDING_BULL or BREAKOUT_VOLATILE
            (price moving toward short calls). TRENDING_BEAR is favorable — hold.
          - Put spread: only exit on TRENDING_BEAR or BREAKOUT_VOLATILE
            (price moving toward short puts). TRENDING_BULL is favorable — hold.
          - Leg 2 cancellation on favorable flips handled by check_leg_triggers().

        """
        # v4.5: the CONDOR_RATCHET_* imports are gone with the ratchet. A dead
        # import is this repo's most-repeated bug shape — a guard outliving the
        # thing it guarded — so it goes in the same commit, not the next one.
        from config import (CONDOR_NICKEL_CLOSE,
                            VERTICAL_HOLD_TO_ET, VERTICAL_HOLD_TO_CLOSE)
        from utils.time_utils import ET

        decision    = ExitDecision()
        trade_id    = record["trade_id"]
        entry_prem  = record["entry_premium"]
        option_side = record.get("option_side", "")

        pnl_pct = (entry_prem - current_premium) / entry_prem if entry_prem > 0 else 0
        pnl_usd = (entry_prem - current_premium) * record["contracts"] * CONTRACT_MULTIPLIER
        decision.current_pnl_pct = pnl_pct
        decision.current_pnl_usd = pnl_usd

        # v4.17 — CREDIT VERTICALS ARE EXEMPT FROM THE 15:40 LADDER.
        # `is_hard_close_time()` opens at FLATTEN_WINDOW_OPEN (15:40) so a DEBIT
        # position gets a mark-limit phase before the 15:45 cross — and that
        # ladder is why it is NOT moved globally: opening it at 15:45 would
        # force every EOD exit marketable, the exact failure time_utils v3.8
        # fixed. A SHORT VERTICAL HAS THE OPPOSITE SIGN. It decays TOWARD the
        # holder, so 15:40-15:45 is the steepest part of its curve.
        # 🔴 r149 — SUPERSEDED BY EOD.1: a credit vertical is assignment risk, so it
        # RESTS at its best case from 15:45 and crosses at 15:55 (_eod_due).
        # 🔴 r71 — THIS BOUND MOVED TO 15:50 BY THE OPERATOR'S RULING, and the
        # original reasoning is STRUCK RATHER THAN DELETED (r240: a line a later
        # ruling contradicts is a wrong answer, not history).
        # ⚠️ ~~HELD TO 15:45 AND NOT PAST IT.~~ Every instrument except SPX is
        # American-style and physically settled, so a spread finishing BETWEEN
        # the strikes assigns the short and leaves an unhedged overnight stock
        # position — "defined risk" is true at settlement, not through
        # assignment. The paper engine has no assignment model and would show a
        # clean result that does not survive going live.
        # 🔑 HE WAS SHOWN THAT PARAGRAPH VERBATIM BEFORE THE CHANGE AND
        # REAFFIRMED. His counter-argument is the substance of the ruling:
        # *"It's still defined risk, even on assignment."* He is right about the
        # OPTION legs — a vertical through both strikes loses the width and no
        # more. What he is accepting is the STOCK left behind on a
        # between-strikes finish.
        # ⚠️ AND THE EXPOSURE IS A FAILED FLATTEN, NOT A HELD POSITION: 15:50
        # still exits before the 16:00 expiry, so what this spends is MARGIN —
        # the final reconcile sweep is 15:57, so 7 minutes after the close
        # attempt instead of 12, in the thinnest liquidity of the day.
        _vnow = datetime.now(ET)
        _vert_close = _eod_due(record)                         # r149: 15:45, resting best case
        if _vert_close:
            decision.should_exit = True
            # 🔴 r71 — THE LABEL IS DERIVED FROM THE CONSTANT, NEVER TYPED. It
            # read "hard_close_15:45_ET" on a branch whose bound is
            # VERTICAL_HOLD_TO_ET, so the moment that constant moved the reason
            # string would have named a time that did not fire. That is what
            # r44 paid for when a hunt exit carried the runaway's label and
            # cost a wrong diagnosis inside the same session.
            # r149 — EVERY end-of-day label in this file now derives from the
            # EOD schedule via _eod_label(); none is typed any more.
            decision.exit_reason = _eod_label(record)          # r149: hard_close_resting_15:45_ET
            return decision

        # r230 — ORCS legs are condor legs here, VERBATIM (the operator, 2026-10-03; PLAN_SPEC §41.11).
        # r204's early return for them is gone.

        # ── TC.6 TREND CREDIT SPREAD — BREACH OR NICKEL, NOTHING ELSE ────
        # Operator's spec: "Exit should be breached (loss) or nickel close
        # (profit)." NO premium stop and NO ratchet, and that is not a
        # simplification — THE MEASURED EV WAS HELD TO EXPIRY, UNMANAGED
        # (+$0.52/spread, 90% terminal OK, 79% recovered on the ORB-anchored
        # runaway arm). A stop bolted on afterwards is a DIFFERENT TRADE with a
        # different expectancy, and paper results from it would not transfer.
        # BREACH is structural, not a premium percentage: a CLOSED BAR beyond
        # the broken ORB boundary. That is the same event `orb_structure_stop`
        # already calls thesis death, and the level the short strike was
        # anchored to — so structure and invalidation agree instead of arguing.
        # CLOSED bars only: an intraday wick through the boundary is a touch,
        # and the operator's own rule is that only a close decides acceptance.
        if is_trend_participation(record):
            # 🔴 r238 — THE 15%-OF-CREDIT STOP, AND IT RUNS FIRST. Operator,
            # 2026-09-04: *"stop out at 15% of credit collected... the 15% is
            # doing the heavy lifting, flatten is last resort, nickel closes on
            # a nice move in our favor."* Before this the branch checked the
            # boundary breach and RETURNED, so a trend credit had no premium
            # stop at all — it rode to breach, nickel or the flatten.
            # ⚠️ 15% OF CREDIT IS NOT THE LONE STOP'S 15% OF RISK, and the
            # difference is 4x. It is chosen, not inherited: on a $2.50 credit
            # this is $0.375 against a $2.45 win to the nickel, a realized
            # 6.5:1. `stop_survivable` at entry (2x the short quote) is what
            # stops it being the r155-inverted stop that fires on noise — the
            # entry gate is load-bearing for this exit.
            try:
                _entry_cr = float(record.get("entry_premium") or 0.0)
            except (TypeError, ValueError):
                _entry_cr = 0.0
            # OTV4TEST r9 — the 15%-of-credit stop applies to a LONE vertical only
            # (operator 2026-09-09); a hedged leg's sibling suppresses it.
            _tcs_hedged = self._condor_sibling_open(record, default=False)
            if _entry_cr > 0 and current_premium is not None and not _tcs_hedged:
                _stop_at = _entry_cr * (1.0 + TCS_STOP_PCT_OF_CREDIT)
                if float(current_premium) >= _stop_at:
                    decision.should_exit = True
                    decision.exit_reason = (
                        f"tcs_stop_{TCS_STOP_PCT_OF_CREDIT:.0%}_of_credit: "
                        f"{float(current_premium):.2f} >= {_stop_at:.2f} "
                        f"(credit {_entry_cr:.2f})")
                    return decision
            # ⚠️ THE BREACH SURVIVES AS A BACKSTOP and is expected to be INERT:
            # a close through the level moves a near-money spread far more than
            # 15%, so the stop above fires first. Kept because "expected inert"
            # and "proven inert" are different, and it costs nothing.
            _b = float(record.get("underlying_stop") or 0.0)
            _side = record.get("option_side", "")
            _last = None
            try:
                if df_1m is not None and not df_1m.empty:
                    _last = float(df_1m["close"].iloc[-1])
            except Exception:                                  # noqa: BLE001
                _last = None
            if _b > 0 and _last is not None:
                # put spread sits BELOW the boundary -> a close below breaches;
                # call spread sits ABOVE -> a close above breaches.
                _breached = (_last < _b) if _side == "put" else (_last > _b)
                if _breached:
                    decision.should_exit = True
                    decision.exit_reason = (
                        f"tcs_breach: close {_last:.2f} beyond boundary {_b:.2f}")
                    return decision
            elif _b > 0:
                # No tape: report it. A breach rule that cannot see price is
                # inert, and an inert stop must never look like a passing check.
                logger.warning("[tcs] no 1m tape — the breach rule is INERT "
                               "this tick (boundary %.2f)", _b)
            # ⚠️ NO NICKEL CLOSE. Operator, 2026-08-14: "There should be no
            # closing it short of a BREACH of that level or the SESSION HARD
            # CLOSE cutoff." This revises the earlier breach-or-nickel spec.
            # A nickel close is a PROFIT exit, and taking it caps a position
            # whose measured EV was HELD TO EXPIRY, UNMANAGED. The 15:45 close
            # above is the only other way out.
            # ⚠️ TERMINAL RETURN — THE WHOLE POINT OF THE BRANCH.
            # Without this the branch FALLS THROUGH to the ratchet and the 25%
            # condor stop below. Observed live 2026-08-14: a $0.06 credit sets
            # stop_premium at $0.07 (credit x 1.25), so ONE CENT of widening
            # closed the trade — every TC.6 leg on the fleet stopped out within
            # seconds. The measured EV was HELD TO EXPIRY, UNMANAGED; a premium
            # stop is a different trade.
            # The v1.0 test asserted the branch contained two `return decision`
            # statements. It did. It never exercised the path where NEITHER
            # breach NOR nickel fires — which is the path that was broken.
            return decision
            # No other exit applies: the 15:45 close is handled ABOVE, and
            # the ratchet / 25% stop / TP below are deliberately unreachable
            # for a trend credit spread.


        # ── 🔴 v4.1 (2026-08-21) — CONDOR-LEG ADVERSE EXIT DELETED (3/3) ─────
        # Same shape as the butterfly exit above: a membership test against
        # trending LABELS, which v4 never assigns. The adverse-move exit for a
        # short call spread into a bull trend, and for a short put spread into
        # a bear trend, has never fired. The leg rode to its stop instead.
        # Rebuild on measured direction if it is wanted, never on a label.

        # ── RATCHETING STOP (v4.1) ────────────────────────────────────────
        # Every stopped leg in the 07-07..07-22 sample was GREEN FIRST (median
        # peak +24% pre-fix / +31% post) then round-tripped into the -25% stop.
        # Nothing existed between entry and the $0.05 nickel close to keep any
        # of it. This moves the STOP and never closes the leg, so the position
        # stays alive to reach the far band and complete the structure.
        # ⚠️ AUDIT F6 (2026-08-20): the stop was FLAT 25% from birth. TRADES.md
        # §5 is explicit — "BEFORE LEG 2 FILLS — leg 1 manages exactly like the
        # sweep credit spread: a 15% stop" — and names the 25% as "never
        # validated... calibrated for a complete structure collecting credit on
        # both sides — not for one naked leg" (condor_stop measured 16 trades,
        # 19% win, −$1,156). check_condor_spec stayed green because it asserted
        # a stub of its own (see its v4.1 entry). The threshold is derived at
        # EVALUATE time from hedge state; stop_premium in the row remains the
        # widest bound and is not rewritten. Fail direction: sibling probe
        # error → default False → the TIGHTER stop on a lone leg — less loss,
        # stated per AUDIT.md 5.2.
        # ── v4.4 (2026-08-24) — PER-LEG PREMIUM STOP: LONE VERTICAL ONLY ──
        # Operator ruling: "The 25% stop should only apply to a lone vertical
        # spread — never the condor." The offset is the whole reason
        # full-sizing is safe (risk_manager.compute_condor_leg_size): the pair
        # cannot lose max on both ends, and a stop that closes one end
        # converts the structure back into a single full-sized directional
        # position with the hedge gone — 5 of 14 condor symbol-days had BOTH
        # sides stopped on a whipsaw. So while a complement is open the
        # per-leg premium stop (and its ratchet) is SUPPRESSED, and it RE-ARMS
        # the moment the leg is alone again — one-way suppression would leave
        # a naked full-sized position with no premium stop.
        # ⚠️ SUPPRESSED IS NOT UNMANAGED: the formed structure keeps the 15:45
        # close above, the nickel close below, and the roll.
        # 🔴 SETTLED 2026-09-05 (r269) — DO NOT RE-OPEN. There is NO further
        # loss boundary on a formed condor, and that is a decision rather than
        # an omission. Operator: *"The current architecture covers all condor
        # management. It's a settled issue."* The reasoning is `risk_manager
        # .compute_condor_leg_size`'s own: the two verticals CANNOT both reach
        # max loss at expiry because price can only be at one extreme, so a
        # stop on the tested side converts a structurally hedged position into
        # a directional one at the worst possible moment. Precedent: the trend
        # credit spread carries `stop_premium=0.0` for the same reason.
        # ⚠️ NOTHING HERE INVENTS ONE, and nothing should ADD one without a new
        # ruling — this comment is the record that it was asked and answered.
        # Suppress/re-arm persist on the row as stop_suppressed_ts /
        # stop_suppressed_by (NEW FIELDS, trade_logger v4.3 — stop_premium
        # stays the immutable entry-time floor, per the v3.1 trail lesson) and
        # are announced edge-triggered in the log. Fail direction: sibling
        # probe error → default False → treated as LONE → the 15% stop stays
        # armed; a spurious stop on a formed leg loses less than a stopless
        # ride toward max loss (AUDIT.md 5.2: state the fail direction).
        _hedged = self._condor_sibling_open(record, default=False)
        self._sync_stop_suppression(record, _hedged)
        # r11 — final form: one floor for the whole structure, from where it stands
        _ff = self._final_form_floor(record, current_premium)
        if _ff:
            decision.should_exit = True
            decision.exit_reason = _ff
            return decision
        if not _hedged:
          # Lone calibration is 15%, UNCHANGED — TRADES.md §5 ("leg 1 manages
          # exactly like the sweep credit spread: a 15% stop"), applied by
          # AUDIT F6. The ruling removes the stop from the CONDOR; it does not
          # re-litigate the lone number.
          # 🔴 THE RATCHET IS GONE — v4.5, 2026-08-24, operator: "I didn't
          # request any ratchet... the standalone vertical spread had a stop
          # Floor, but I don't recall anything about spec'ing a ratchet in
          # there."
          # ⚠️ SPEC.1 CLASS: AN ENCODING NOBODY CHOSE. Traced before removing —
          # `CONDOR_RATCHET_*` dates to "Condor leg management, v2"
          # (2026-07-23) and its comment justifies a ratchet OVER a take-profit,
          # which answers a question the operator never asked. No directive is
          # cited anywhere. It is not a TC.6 remnant either: TC.6 postdates it
          # and explicitly carries NO premium stop and NO ratchet.
          # ⚠️ AND IT WAS THE MECHANISM BEHIND THE DOUBLE-STOP. The ratchet
          # tightens the UNTESTED leg precisely BECAUSE it is winning, so a
          # reversal stopped the tested leg on the floor and the untested leg on
          # its ratchet — "a leg price never went near, closed by a stop that
          # exists only because it was profitable." Scoping it to standalones
          # narrowed that; deleting it ends it.
          # THE SPEC, in full: a STANDALONE vertical has a stop FLOOR and
          # nothing else. A FORMED condor has no premium stop at all — it rolls
          # the untested side, failing that inverts, failing that closes.
          # ── 🔴 r155 — THE STOP IS A FRACTION OF THE RISK, NOT THE CREDIT ──
          # Operator, 2026-08-27, after CVX entered the same 197.5/192.5 spread
          # SEVENTEEN times in twelve minutes, each dead inside a minute:
          # *"We need to fix the structure that that loop was exploiting."*
          #
          # ⚠️ WHAT IT WAS: `entry_prem * 1.15` — fifteen percent of the CREDIT.
          # That is INVERTED. The less credit collected, the TIGHTER the stop in
          # dollars, so the structures with the least premium got the least room:
          #     credit $0.58 -> stop distance $0.087   <- the CVX loop
          #     credit $1.50 -> stop distance $0.225
          #     credit $3.00 -> stop distance $0.450
          # A thin credit means the short strike is FAR OUT and the position is
          # LESS threatened, and it was handed a stop a single tick clears.
          # Eight cents of tolerance against $442 of risk.
          #
          # ⚠️ THE RISK IS WHAT IS ACTUALLY AT STAKE, and it does not shrink as
          # the credit shrinks: `width - credit`. Same 15%, anchored to that:
          #     5-wide, $0.58 credit -> risk $4.42 -> $0.66 of room
          #     5-wide, $3.00 credit -> risk $2.00 -> $0.30 of room
          # Room now scales with exposure instead of inversely to it.
          #
          # ⚠️ THIS IS NOT THE R HURDLE AND IS NOT MUTED BY RELAXED. R is a
          # RATIO judged at entry (economics — relaxed mutes it deliberately, to
          # collect the population it would refuse). This uses only R's
          # DENOMINATOR as a DISTANCE, continuously, to decide when to leave. A
          # relaxed R-0.11 trade is still taken; it simply lives long enough to
          # produce an outcome. **A trade stopped by noise is not an
          # observation** — today's sixteen CVX rows said nothing about whether
          # selling that level works, because none survived to find out.
          #
          # ⚠️ FALLS BACK TO THE OLD RULE IF THE WIDTH IS MISSING, and says so.
          # A stop that cannot be computed must not silently become no stop.
          _w = 0.0
          try:
              _w = float(record.get("spread_width") or 0.0)
          except (TypeError, ValueError):
              _w = 0.0
          _risk = _w - entry_prem if _w > 0 else 0.0
          if _risk > 0:
              stop_level = entry_prem + _risk * LONE_STOP_PCT_OF_RISK
              tier = ""
          else:
              stop_level = entry_prem * (1 + LONE_STOP_PCT_OF_RISK)
              tier = " [no width — credit-anchored fallback]"
              logger.warning(
                  "[exit] %s has no spread_width; the lone stop fell back to "
                  "%.0f%% OF CREDIT, which is the inverted rule r155 replaced. "
                  "The trade will stop on noise.",
                  str(record.get("trade_id", ""))[:8],
                  LONE_STOP_PCT_OF_RISK * 100)

          if current_premium >= stop_level:
              decision.should_exit = True
              decision.exit_reason = (
                  f"condor_stop pnl={pnl_pct:.1%}{tier} "
                  f"(lone {LONE_STOP_PCT_OF_RISK:.0%} of risk, "
                  f"stop {stop_level:.2f})")
              return decision

        # ── 🔴 r106 — THE TAKE-PROFIT IS RETIRED ─────────────────────────
        # TRADES.md §5: "No take-profit, no trail, no BOS, ever." Measured: on
        # 18 lone verticals a TP@25% turned −$242.77 into −$8.43, and on 28
        # paired legs a TP was worse AT EVERY LEVEL. A credit vertical is
        # EARNING from decay; closing it early buys back the theta it was
        # opened to collect. The nickel close is always available — that is a
        # win, not an abandonment.
        # ⚠️ AND ITS GATE WAS THE GIVEAWAY. `not _condor_sibling_open(record)`
        # read as "only on a standalone", written when a lone vertical was
        # understood as HALF OF A PLANNED CONDOR waiting for its partner.
        # Operator, 2026-08-24: "There is no longer a 'standalone leg' — we
        # manage the 1st leg as an individual vertical spread now. There is no
        # condor implied, it is merely PERMITTED." Under that reading the gate
        # is true for essentially every vertical, so this was not a rare arm
        # for an unusual case — it was the ordinary exit for the ordinary trade,
        # and it contradicted the measurement it sat next to.
        # CONDOR_TP_PCT / CONDOR_ENTRY_CUTOFF_ET / CONDOR_TP_MIN_HOLD_MIN are no
        # longer read here; the import is trimmed with the arm, in the same
        # commit, because a guard outliving the thing it guarded is this repo's
        # most-repeated bug shape.

        # v4.13 (OTV4TEST r5) — the sweep's thesis is the level HOLDS; its
        # BREACH (r120: the operator's close-then-open, level_rules) is the negation. AFTER the 15%-of-risk stop by the
        # operator's ruling: "2 minutes into a dead thesis could rack up some
        # serious losses" — the floor answers first, the breach names the reason.
        _sb = self._sweep_breach_accepted(record, df_1m)
        if _sb:
            decision.should_exit = True
            decision.exit_reason = _sb
            return decision
        if current_premium <= CONDOR_NICKEL_CLOSE:
            decision.should_exit = True
            decision.exit_reason = f"nickel_close pnl={pnl_pct:.1%}"
            return decision

        return decision

    def _evaluate_tent(self, record: TradeRecord,
                       current_premium: float) -> ExitDecision:
        """r106 — THE TENT HAS EXACTLY ONE ADJUSTMENT LEFT.

        Operator, 2026-08-24: "The only remaining adjustment after that should be
        a 15% floor of the total credit collected. If we can't achieve that,
        close the entire structure."

        ⚠️ NO TP, NO TRAIL, NO NICKEL. Those belong to a vertical still
        collecting decay. This structure has already been rolled once and
        adjusted again; it is being held to a floor, not farmed.
        ⚠️ THE BASIS IS CUMULATIVE CREDIT — original credit + every roll − the
        hedge debit — which `entry_premium` carries (condor_roll writes it that
        way). Measuring the floor against the ORIGINAL condor credit would move
        the stop every time a roll added credit, which is the opposite of what a
        floor is.
        ⚠️ AND 15:45 STILL APPLIES. It is a credit structure: it decays toward
        the holder and is held to the bell, then closed.
        """
        from config import (TENT_FLOOR_PCT, VERTICAL_HOLD_TO_ET,
                            VERTICAL_HOLD_TO_CLOSE)
        from utils.time_utils import ET as _ET

        decision   = ExitDecision()
        entry_prem = float(record.get("entry_premium", 0.0) or 0.0)
        pnl_pct = ((entry_prem - current_premium) / entry_prem
                   if entry_prem > 0 else 0.0)
        decision.current_pnl_pct = pnl_pct
        decision.current_pnl_usd = ((entry_prem - current_premium)
                                    * record["contracts"] * CONTRACT_MULTIPLIER)

        _n = datetime.now(_ET)
        if _eod_due(record):                                   # r149: 15:45, resting best case
            decision.should_exit = True
            decision.exit_reason = _eod_label(record)
            return decision

        if entry_prem > 0 and current_premium >= entry_prem * (1 + TENT_FLOOR_PCT):
            decision.should_exit = True
            decision.exit_reason = (
                f"tent_floor pnl={pnl_pct:.1%} "
                f"({TENT_FLOOR_PCT:.0%} from the structure as formed, basis "
                f"{entry_prem:.2f}; cumulative credit {float(record.get('cumulative_credit') or 0.0):.2f})")
            return decision

        return decision

    def _evaluate_adopted(self, record: TradeRecord,
                          current_premium: float) -> ExitDecision:
        """
        Exit logic for an ADOPTED position — one discovered open at the broker on
        a LIVE restart with no DB plan (see broker_reconcile). The original setup
        is unknown, so it is managed by the universal core of our rules:
          - sign-correct max-loss stop (already on the record as stop_premium:
            long = entry*(1-ADOPTED_STOP_PCT); short = entry*(1+ADOPTED_STOP_PCT)),
          - long positions also trail to lock gains (standard trail helper),
          - the 15:45 hard close applies like everything else.
        A position already past its stop when adopted exits on the first tick; a
        healthy one rides. That is the "if red exit, if green manage" behaviour,
        via the normal exit path — no strategy-specific context required.

        A lone adopted SHORT (an anomaly per the account's margin reality) is
        held on a fixed protective stop + hard close only; no ratcheting trail.
        """
        decision   = ExitDecision()
        trade_id   = record["trade_id"]
        entry_prem = record.get("entry_premium", 0) or 0
        stop_prem  = record.get("stop_premium", 0) or 0
        contracts  = record.get("contracts", 0) or 0
        is_short   = bool(record.get("is_short_position", 0))

        # sign-correct P&L: a long gains as premium rises, a short as it falls
        if is_short:
            pnl_pct = (entry_prem - current_premium) / entry_prem if entry_prem > 0 else 0
            pnl_usd = (entry_prem - current_premium) * contracts * CONTRACT_MULTIPLIER
        else:
            pnl_pct = (current_premium - entry_prem) / entry_prem if entry_prem > 0 else 0
            pnl_usd = (current_premium - entry_prem) * contracts * CONTRACT_MULTIPLIER
        decision.current_pnl_pct = pnl_pct
        decision.current_pnl_usd = pnl_usd

        # 1. HARD CLOSE (also enforced by the 15:45 flatten — belt & suspenders)
        if _eod_due(record):                                   # r149: per-position EOD clock
            decision.should_exit = True
            decision.exit_reason = _eod_label(record)
            return decision

        # 2. MAX-LOSS STOP (sign-correct)
        if is_short:
            if stop_prem > 0 and current_premium >= stop_prem:
                decision.should_exit = True
                decision.exit_reason = f"adopted_stop_short pnl={pnl_pct:.1%}"
            # anomalous short: fixed stop + hard close only, no ratcheting trail
            return decision

        if stop_prem > 0 and current_premium <= stop_prem:
            decision.should_exit = True
            decision.exit_reason = f"adopted_stop_long pnl={pnl_pct:.1%}"
            return decision

        # 3. LONG PROFIT TRAIL — once up TRAIL_ACTIVATION_PCT, arm a ratcheting
        #    stop that locks gains and PERSISTS: a pullback to the locked level
        #    exits (unlike the shared _update_trail, which de-arms below the
        #    activation threshold). Ratchets to TRAIL_LOCK_PCT below the high.
        if (not self._trail_active.get(trade_id, False)
                and pnl_pct >= TRAIL_ACTIVATION_PCT):
            self._trail_active[trade_id] = True
            self._trail_stops[trade_id] = entry_prem * (1 + TRAIL_LOCK_PCT)

        if self._trail_active.get(trade_id, False):
            ratchet = current_premium * (1 - TRAIL_LOCK_PCT)
            trail   = max(self._trail_stops.get(trade_id, stop_prem), ratchet)
            self._trail_stops[trade_id] = trail
            decision.new_trail_stop = trail
            if current_premium <= trail:
                decision.should_exit = True
                decision.exit_reason = f"adopted_trail pnl={pnl_pct:.1%}"

        return decision

    def _get_bos_tracker(self, trade_id: str,
                          direction: str,
                          entry_price: float,
                          min_dist: float = 0.0) -> BOSTracker:
        """v4.15 — `min_dist` defaults to 0.0 so every existing caller is
        byte-identical in behaviour. It is supplied ONLY by the continuation
        path, which seeds with `underlying_entry` and can therefore express a
        distance in ATR (underlying) units.

        ⚠️ DO NOT PASS min_dist FROM THE GENERIC/ORB CALLER AT ~966 WITHOUT
        FIXING IT FIRST: that site seeds with `entry_prem` — the OPTION premium
        — and BOSTracker compares against df_1m UNDERLYING closes. A ~$1.26
        premium against ~$352 closes means the very first bar always beats
        `peak_close`, so that path seeds a protected level immediately on bar
        one regardless of structure. Pre-existing, out of scope here, and
        recorded rather than silently patched — an ATR distance in premium
        units would be meaningless anyway."""
        if trade_id not in self._bos_trackers:
            self._bos_trackers[trade_id] = BOSTracker(direction, entry_price,
                                                      min_dist=min_dist)
        return self._bos_trackers[trade_id]

    def _update_trail(self, trade_id: str,
                       current: float, entry: float,
                       trail_activation: float,
                       hard_stop: float,
                       structure_trail: bool = False) -> Optional[float]:
        """The premium trail. `structure_trail` selects the r91 variant.

        🔴 r91 — THE GEOMETRY-SIZED DEBITS TRAIL FROM ENTRY, NOT FROM +50%.
        Operator, 2026-09-22: *"I don't want the 25% premium stop anymore. Put
        a 25% trailing stop on it that follows the move. If it doesn't move the
        structure stop will catch it and if it does move the 25% trailing stop
        will lock it in."* And on the arm point: *"currently the trail
        activation is at the 50. But I want it from the start."*

        Two things change, and ONLY for ORB and Breakout:
          · the initial trail is the STRUCTURE STOP, not `entry x 1.25`. Arming
            from entry with the old initial would lock +25% before the trade
            had made +25% and stop it out instantly.
          · the ratchet is `current x (1 - TRAIL_LOCK_PCT)` — 25% behind the
            move. Because it only ever moves UP, the effective value is
            `peak x 0.75` without needing to store a peak.

        🔴 WHY THE STRUCTURE FLOOR IS LOAD-BEARING AND NOT A DETAIL. r44
        replaced exactly this `current * 0.75` formula because a fraction of
        PREMIUM can sit BELOW ENTRY: measured on S3 over 210 trail-exited fleet
        trades, TEN finished NEGATIVE with the trail armed — arming it could
        guarantee a loss. Seeding `_trail_stops` with the structure stop and
        only ever raising it makes that arithmetically impossible here, which
        is the only reason this formula is safe to bring back.
        ⚠️ EVERY OTHER STRATEGY IS UNTOUCHED — `_gain_floor` still governs them
        and r44's finding still protects them. The flag is passed by the two
        call sites from the RECORD, never inferred inside this method.
        """
        if current < trail_activation:
            return None

        if not self._trail_active.get(trade_id, False):
            self._trail_active[trade_id] = True
            if structure_trail:
                # the entry-time structural floor; the move has to earn its way
                # above this before the trail means anything
                initial_trail = hard_stop
            else:
                initial_trail = max(entry * (1 + TRAIL_LOCK_PCT), entry)
            self._trail_stops[trade_id] = initial_trail
            logger.info(
                f"TRAIL ACTIVATED: {trade_id[:8]} "
                f"initial_trail=${initial_trail:.2f}"
                f"{' (structure floor)' if structure_trail else ''}"
            )

        current_trail = self._trail_stops.get(trade_id, hard_stop)
        if structure_trail:
            # 25% behind the move; the ratchet below makes this `peak x 0.75`
            new_trail = current * (1.0 - TRAIL_LOCK_PCT)
        else:
            # r44 — was `current * 0.75`: a fraction of PREMIUM, which can sit
            # below entry. See `_gain_floor` for the S3 measurement behind this.
            new_trail = _gain_floor(entry, current, TRAIL_GAIN_LOCK)
        if new_trail > current_trail:
            self._trail_stops[trade_id] = new_trail

        return self._trail_stops[trade_id]

    # ─── Continuation (trend-pullback) Exit — EXHAUSTION-BASED ────────────────
    #
    # This is where the continuation trade lives or dies. Entry is deliberately a
    # low bar; the intelligence is here. The move is ridden while it has energy
    # and cut when it's SPENT — which is a different question than "was I proven
    #
    #   (1) EXTENSION-FROM-MIDLINE  — price stretched an abnormal distance from
    #       the BB midline (its mean). Cheap, early, stateless. FIRST TIER:
    #       tightens the trail hard (protect the stretched gain) but does NOT
    #       exit — a strong trend can stay extended.
    #   (2) MOMENTUM DIVERGENCE     — price prints a new run-favorable extreme
    #       while momentum (5m rate-of-change) is WEAKER than at the prior
    #       extreme: the move is continuing on fumes. CONFIRMATION: exits.
    #
    # COMBINE MODE (v1 = two-stage): extension tightens, divergence exits.
    #   ── NOTE TO FUTURE-SELF ─────────────────────────────────────────────
    #   A stricter "mode 3" was discussed and intentionally deferred: require
    #   BOTH signals to agree before exiting (divergence AND extension), which
    #   maps closer to how the operator actually trades — you don't bail on
    #   divergence alone if the move isn't also stretched. v1 ships the safer
    #   two-stage form (divergence-alone can exit). If you're reading this
    #   because you're reconsidering exits: the hook is the `_exhausted` combine
    #   step below — gate the exit on (divergence and extended) instead of
    #   (divergence) to become mode 3. Left as a code change, not a live flag,
    #   by the operator's request (they don't expect to touch it).
    #   ────────────────────────────────────────────────────────────────────
    #
    # ENGINE STATE: prefers the live vol_state/trend threaded from main.py (exact
    # — same midline/momentum the entry judged against). Falls back to values
    # RECOMPUTED from df_5m when the state isn't available (restart recovery,
    # adopted positions) so this NEVER raises — it only degrades precision.
    def _underlying_from_5m(self, df_5m: Optional[pd.DataFrame]) -> Optional[float]:
        if df_5m is None or len(df_5m) == 0:
            return None
        try:
            return float(df_5m["close"].iloc[-1])
        except Exception:
            return None

    def _midline_atr(self, vol_state, df_5m):
        """Prefer live vol_state; else recompute midline (20-SMA 5m close) + ATR."""
        midline = None
        atr = None
        if vol_state is not None:
            midline = getattr(vol_state, "bb_middle", None) or None
            atr = getattr(vol_state, "atr_current", None) or None
        if (midline is None or atr is None) and df_5m is not None and len(df_5m) >= 20:
            try:
                midline = float(df_5m["close"].tail(20).mean())
                tr = (df_5m["high"] - df_5m["low"]).tail(14)
                atr = float(tr.mean())
            except Exception:
                pass
        return midline, atr

    def _momentum_divergence(self, trade_id, record, underlying, direction,
                             trend, df_5m) -> bool:
        """
        True when price makes a NEW run-favorable extreme but momentum is weaker
        than it was at the prior extreme. Momentum = live trend reading if given,
        else 5m rate-of-change. State (last extreme + its momentum) is carried in
        self._exhaust_state per trade_id.
        """
        if underlying is None:
            return False
        # momentum reading: prefer a numeric from df_5m ROC (comparable across
        # extremes); the live `trend` object gives a categorical we can't diff.
        mom = None
        if df_5m is not None and len(df_5m) >= 6:
            try:
                c = df_5m["close"]
                mom = float(c.iloc[-1] - c.iloc[-6])  # 5-bar ROC
            except Exception:
                mom = None
        if mom is None:
            return False

        st = self._exhaust_state.setdefault(trade_id, {"ext": None, "mom": None})
        favorable_new_extreme = (
            st["ext"] is None or
            (direction == "long"  and underlying > st["ext"]) or
            (direction == "short" and underlying < st["ext"])
        )
        diverged = False
        if favorable_new_extreme:
            # new extreme: does momentum confirm or diverge vs the prior extreme?
            if st["mom"] is not None:
                if direction == "long":
                    diverged = mom < st["mom"] and mom <= 0
                else:
                    diverged = mom > st["mom"] and mom >= 0
            st["ext"] = underlying
            st["mom"] = mom
        return diverged

    def place_exit_order(self, record: TradeRecord, reason: str,
                         mark_price: Optional[float] = None) -> FillResult:
        """Place a closing order and return a FillResult (the shared paper/live
        contract). NEVER returns a bare success bool anymore: a close is only
        'done' when FillResult.confirmed is True AND fill_price is a real price.

        mark_price is the last-known mark for this position (spread value for a
        condor leg, net debit for a butterfly, single mark otherwise), supplied
        by position_manager. In PAPER it becomes the simulated fill price. In
        LIVE it is context only — the booked price MUST be the broker's actual
        fill, never this mark.
        """
        mode      = "PAPER" if self.paper_trading else "LIVE"
        trade_id  = record["trade_id"]
        contracts = record["contracts"]

        logger.info(f"[{mode}] CLOSING {trade_id[:8]}: {reason} contracts={contracts}")

        # ── N.5 (v4.11) — latency telemetry, log-only ────────────────────────
        # Stamped BEFORE dispatch so the submit instant is the submit instant,
        # not a value reconstructed after the fact. Set once per close attempt
        # and kept on the RECORD: a live close is multi-tick and the next tick
        # resumes the same order, so this must survive the pass boundary.
        if not record.get("_exit_submit_ts"):
            record["_exit_submit_ts"] = ts_for_db()
            record["_exit_submit_mono"] = time.monotonic()
            # The mark at TRIGGER — the price the exit decision saw. This is
            # the number the ladder's cost is measured against; None when no
            # mark was available, which is honest and must not become 0.0.
            record["_exit_mark_at_trigger"] = (
                float(mark_price) if mark_price is not None and mark_price >= 0
                else None)
        record["_exit_passes"] = int(record.get("_exit_passes", 0)) + 1
        # ESCALATED means the close needed more than a plain limit-at-mark post.
        # Two disjoint causes, either sufficient: the 15:45 hard-close market
        # cross, or the live loop hitting its deadline and cancelling (set at
        # that branch). Both are "the ladder did not simply fill".
        try:
            if hard_close_order_mode(now_et()) == "market":
                record["_exit_escalated"] = 1
        except Exception as exc:                             # noqa: BLE001
            # W.2: this sat in TIER 1 (risk/orders/record) as a bare `pass` —
            # the census's whole purpose. DEBUG, once per process, so a broken
            # escalation flag is findable without ever touching the close.
            if "n5-escalation" not in _telemetry_logged:
                _telemetry_logged.add("n5-escalation")
                logger.debug("N.5 escalation flag failed (%s: %s) — telemetry "
                             "only, the close is unaffected",
                             type(exc).__name__, exc)

        # ── PAPER: simulate the fill at the last-known mark and CONFIRM it ──────
        # A simulated close always succeeds on the first pass — there is no
        # broker, nothing to poll, nothing to reuse. If we have no mark we cannot
        # invent a price, so we decline (confirmed=False) rather than book a fake
        # one; the caller will try again next tick with a fresh mark.
        if self.paper_trading:
            if mark_price is None or mark_price < 0:
                logger.warning(f"[PAPER] {trade_id[:8]}: no mark available — "
                               f"cannot simulate a fill this pass, will retry")
                return FillResult(confirmed=False, detail="paper: no mark yet")
            # r149 (EOD.1) — THE OPERATOR'S PAPER RULE, 2026-09-26: "On paper exits,
            # use latest possible close allowed by code. Ie, the 'end of the ladder'
            # when we walk it (worst-case) or best-case available when deep ITM
            # (par, nickel)", and "I want to be accustomed to seeing late closing
            # orders". Paper cannot see whether a resting or laddered order would
            # have filled, so EVERY end-of-day close is booked as late as the code
            # allows — the 15:55 cross. The PRICE there is the mark (the ladder's
            # last rung), unless the outcome is already settled (_eod_determined),
            # which books its best case (nickel / parity - tick). Other exits are
            # unchanged: their walk already ends at the mark, where paper fills them.
            if "hard_close" in (reason or "").lower():
                if hard_close_order_mode(now_et()) != "market":
                    return FillResult(confirmed=False, held=True,
                                      detail="paper: EOD close held to the 15:55 cross (latest possible close)")
                det = self._eod_determined(record)
                if det is not None:
                    lim, side, _w = det
                    logger.info(f"[PAPER] EOD settled close {trade_id[:8]} @ {lim:.2f} at the cross ({_w})")
                    return self._stamp_exit_latency(record, FillResult(
                        confirmed=True, fill_price=float(lim), detail="paper eod settled best case"))
            logger.info(f"[PAPER] Simulated fill {trade_id[:8]} @ {mark_price:.2f}")
            return self._stamp_exit_latency(
                record,
                FillResult(confirmed=True, fill_price=float(mark_price),
                           detail="paper simulated fill"))

        # ── LIVE: submit, then book ONLY on broker-confirmed fill ──────────────
        # v3.5: implemented. Places the order, captures its id, polls the broker
        # to a bounded deadline, and returns confirmed=True with the REAL net
        # fill price — or confirmed=False (position stays open, retries and
        # escalates). See _confirm_and_book_live_exit and the Fable spec.
        return self._stamp_exit_latency(
            record, self._confirm_and_book_live_exit(record, reason, mark_price))

    def _stamp_exit_latency(self, record: TradeRecord,
                            result: FillResult) -> FillResult:
        """N.5 (v4.11) — write the ladder telemetry, then return the result
        UNCHANGED. Log-only: it is a pass-through by construction, so no exit
        path can be altered by it even if it fails.

        Writes ONLY on a confirmed close. An unconfirmed pass leaves the state
        on the record so the NEXT pass keeps accumulating against the same
        submit instant — that is the whole point of a ladder measurement, and
        booking a row per unconfirmed pass would report the fast half of every
        slow close.
        """
        try:
            if not result or not result.confirmed:
                return result
            submit_ts = record.get("_exit_submit_ts")
            if not submit_ts:
                return result
            mono = record.get("_exit_submit_mono")
            latency_ms = int(max(0.0, (time.monotonic() - mono)) * 1000) if mono else 0
            wrote = self._trade_logger.set_exit_latency(
                trade_id       = record.get("trade_id", ""),
                submit_ts      = submit_ts,
                fill_ts        = ts_for_db(),
                latency_ms     = latency_ms,
                ladder_steps   = int(record.get("_exit_passes", 1)),
                escalated      = bool(record.get("_exit_escalated", 0)),
                mark_at_trigger= record.get("_exit_mark_at_trigger"),
            )
            if not wrote and "latency-write" not in self._live_exit_alerted:
                # Once per process, not once per close: a per-exit warning is
                # spam and gets filtered, which is how a dead capture hides.
                self._live_exit_alerted.add("latency-write")
                logger.warning(
                    "N.5 exit-latency row NOT written for %s — these closes "
                    "cannot enter the TC.2 stop-trigger dataset (logged once "
                    "per process)", record.get("trade_id", "")[:8])
        except Exception as exc:                             # noqa: BLE001
            logger.warning("N.5 exit-latency capture failed (%s: %s) — the "
                           "close itself is unaffected",
                           type(exc).__name__, exc)
        return result

    # ── LIVE FILL-CONFIRMATION (v3.5) ────────────────────────────────────────
    # States in which an order is still working at the broker.
    _WORKING_STATES = {
        OrderStatus.RECEIVED, OrderStatus.ROUTED, OrderStatus.IN_FLIGHT,
        OrderStatus.LIVE, OrderStatus.CONTINGENT,
        OrderStatus.CANCEL_REQUESTED, OrderStatus.REPLACE_REQUESTED,
    }
    # Terminal states that are NOT a full fill (may still carry partial fills).
    _DEAD_STATES = {
        OrderStatus.CANCELLED, OrderStatus.EXPIRED,
        OrderStatus.REMOVED, OrderStatus.PARTIALLY_REMOVED,
    }

    # ── B3 (r467) — PARTIAL-EXIT MEMORY LIVES IN THE ROW ────────────────────
    def _exit_state_load(self, record: TradeRecord) -> None:
        """After a restart the record has no in-memory exit state; adopt what the
        row kept: the filled portions and the order that may still be working."""
        if "_live_exit_fills" in record or "_live_exit_order_id" in record:
            return
        raw = record.get("live_exit_state")
        if not raw:
            return
        try:
            st = json.loads(raw)
            fills = [(float(q), float(p)) for q, p in (st.get("fills") or [])]
        except Exception as exc:                               # noqa: BLE001
            self._alert_live_exit_once(
                record.get("trade_id", ""), "state-unreadable",
                f"LIVE exit {str(record.get('trade_id', ''))[:8]}: kept partial-exit "
                f"state unreadable ({exc}) — check the broker before the next close")
            return
        if fills:
            record["_live_exit_fills"] = fills
        for k in ("order_id", "last_order_id"):
            if st.get(k):
                record[f"_live_exit_{k}"] = st[k]
        logger.warning(f"LIVE exit {record['trade_id'][:8]}: restored partial-exit "
                       f"state from the row — {sum(q for q, _ in fills):g} already "
                       f"closed, order {st.get('order_id')}")

    def _exit_state_save(self, record: TradeRecord) -> None:
        """Write the in-memory exit state to the row; NULL once nothing is left."""
        fills = [[q, p] for q, p in (record.get("_live_exit_fills") or [])]
        oid = record.get("_live_exit_order_id")
        st = None
        if fills or oid is not None:
            st = json.dumps({"fills": fills,
                             "order_id": str(oid) if oid is not None else None,
                             "last_order_id": (str(record["_live_exit_last_order_id"])
                                               if record.get("_live_exit_last_order_id")
                                               is not None else None)})
        if record.get("live_exit_state") == st:
            return
        record["live_exit_state"] = st
        try:
            self._trade_logger.update_fields(record["trade_id"], live_exit_state=st)
        except Exception as exc:                               # noqa: BLE001
            self._alert_live_exit_once(
                record.get("trade_id", ""), "state-write",
                f"LIVE exit {str(record.get('trade_id', ''))[:8]}: partial-exit state "
                f"NOT saved ({exc}) — a restart now would forget it")

    def _confirm_and_book_live_exit(self, record: TradeRecord, reason: str,
                                    mark_price: Optional[float]) -> FillResult:
        """B3 (r467) — the live close, with its partial-exit memory loaded from
        and saved to the trade row around every pass."""
        self._exit_state_load(record)
        try:
            return self._confirm_and_book_live_exit_pass(record, reason, mark_price)
        finally:
            self._exit_state_save(record)

    def _confirm_and_book_live_exit_pass(self, record: TradeRecord, reason: str,
                                         mark_price: Optional[float]) -> FillResult:
        """LIVE close with broker fill-confirmation.

        Books ONLY on a broker-confirmed fill at the broker's actual fill price.
        An unconfirmed close returns confirmed=False and the position STAYS
        OPEN — the caller (flatten_all 15:45→16:00 loop / _manage_one next
        tick) retries, and failures page once per trade per failure kind.

        PARTIAL-FILL POLICY (spec §4 — documented hybrid of (a)+(b)):
        a partial that completes within the deadline books as one fill. A
        partial still working at the deadline is cancelled; the filled portion
        is stashed on the record (in-memory: `_live_exit_fills`) and
        confirmed=False, partial=True is returned. The NEXT retry tick
        resubmits ONLY the remaining quantity at a fresh mark, and booking
        happens once — when cumulative fills cover the full position — at the
        quantity-weighted average net price. A partial is never booked as
        whole. 🔴 B3 (r467): the stash and the working order id are KEPT IN
        THE TRADE ROW (`live_exit_state`), so a restart mid-close resumes
        with the remainder, never the full size — see _confirm_and_book_live_exit.

        IDEMPOTENCY / anti-double-submit: the working order id is stashed on
        the record (`_live_exit_order_id`). If a retry tick re-enters while a
        prior order is still working (e.g. cancel failed, or a prior pass
        errored mid-poll), we RESUME polling that order instead of submitting
        a second close against the same position.
        """
        trade_id = record["trade_id"]
        total    = int(record["contracts"])
        prior: List[Tuple[float, float]] = list(record.get("_live_exit_fills") or [])
        done_qty  = sum(q for q, _ in prior)
        remaining = total - int(done_qty)
        if remaining <= 0:
            # Everything already filled across prior partials — book it.
            return self._book_from_fills(record, prior, total,
                                         record.get("_live_exit_last_order_id"))

        try:
            session = get_session()
            account = get_account()
        except Exception as e:
            logger.error(f"LIVE exit {trade_id[:8]}: broker session unavailable: {e}")
            return FillResult(confirmed=False, detail=f"broker session unavailable: {e}")

        # ── 1. Resume a still-working prior order, else submit fresh ─────────
        order_id = record.get("_live_exit_order_id")
        placed   = None
        if order_id is not None:
            try:
                placed = sdk_result(account.get_order(session, order_id))   # B0
                logger.info(f"LIVE exit {trade_id[:8]}: resuming order {order_id} "
                            f"(status={placed.status})")
            except Exception as e:
                logger.error(f"LIVE exit {trade_id[:8]}: cannot fetch prior order "
                             f"{order_id}: {e} — will submit fresh")
                record.pop("_live_exit_order_id", None)
                order_id, placed = None, None

        if placed is not None and placed.status in self._DEAD_STATES:
            # Prior order died between passes — harvest any partial it made.
            fill = self._net_fill_price(record, placed)
            record.pop("_live_exit_order_id", None)
            order_id, placed = None, None
            if fill is not None and fill[0] > 0:
                prior.append(fill)
                record["_live_exit_fills"] = prior
                done_qty  = sum(q for q, _ in prior)
                remaining = total - int(done_qty)
                if remaining <= 0:
                    return self._book_from_fills(record, prior, total,
                                                 record.get("_live_exit_last_order_id"))

        if placed is None:
            placed = self._submit_live_close(record, remaining, mark_price,
                                             reason=reason)
            if placed is None and record.pop("_exit_nomark_hold", None):
                return FillResult(confirmed=False, detail="no mark before the cross; nothing posted")   # F3
            if placed is None:
                self._alert_live_exit_once(
                    trade_id, "submit",
                    f"LIVE close SUBMIT FAILED {trade_id[:8]} — position stays "
                    f"OPEN; retry loop engaged")
                return FillResult(confirmed=False, detail="submit failed")
            order_id = placed.id
            record["_live_exit_order_id"]      = order_id
            record["_live_exit_last_order_id"] = order_id
            self._exit_state_save(record)    # B3: a kill mid-poll resumes THIS order
            logger.info(f"LIVE exit {trade_id[:8]}: close submitted, order "
                        f"{order_id}, qty={remaining} — awaiting broker fill")

        # ── 2. Poll to a bounded deadline; cancel-and-resolve on timeout ─────
        poll     = max(0.0, float(getattr(_cfg, "LIVE_FILL_POLL_SECONDS", 2.0)))
        deadline = time.monotonic() + float(getattr(_cfg, "LIVE_FILL_DEADLINE_SECONDS", 30.0))
        cancel_requested = False
        while True:
            _hb_touch("live-exit poll")      # r295 (LIVE.2): the watchdog must not read a laddering bot as hung
            try:
                placed = sdk_result(account.get_order(session, order_id))   # B0
            except Exception as e:
                logger.warning(f"LIVE exit {trade_id[:8]}: poll error ({e}) — retrying")
            status = placed.status

            if status == OrderStatus.FILLED:
                fill = self._net_fill_price(record, placed)
                record.pop("_live_exit_order_id", None)
                if fill is None or fill[0] <= 0:
                    # Broker says filled but fills unreadable — refuse to book
                    # fiction; reconcile/retry will resolve against the broker.
                    logger.error(f"LIVE exit {trade_id[:8]}: order {order_id} "
                                 f"FILLED but fills unreadable — NOT booking")
                    return FillResult(confirmed=False, order_id=str(order_id),
                                      detail="filled but fills unreadable; refusing to book")
                prior.append(fill)
                record["_live_exit_fills"] = prior
                if sum(q for q, _ in prior) >= total:
                    return self._book_from_fills(record, prior, total, order_id)
                # Defensive: FILLED for less than requested → treat as partial.
                return self._partial_result(record, prior, total, order_id, trade_id)

            if status == OrderStatus.REJECTED:
                record.pop("_live_exit_order_id", None)
                why = getattr(placed, "reject_reason", None) or "unknown"
                self._alert_live_exit_once(
                    trade_id, "reject",
                    f"LIVE close REJECTED {trade_id[:8]} order {order_id}: {why} "
                    f"— position stays OPEN; retry loop engaged")
                return FillResult(confirmed=False, order_id=str(order_id),
                                  detail=f"rejected: {why}")

            if status in self._DEAD_STATES:
                return self._resolve_dead_order(record, placed, prior, total,
                                                order_id, trade_id)

            # Still working.
            if time.monotonic() >= deadline:
                if not cancel_requested:
                    try:
                        sdk_result(account.delete_order(session, order_id))   # B0
                        cancel_requested = True
                        record["_exit_escalated"] = 1        # N.5: ladder did not simply fill
                        # Short grace window to resolve the cancel/fill race:
                        # the order may have filled while the cancel was in
                        # flight — the next polls tell us which won.
                        deadline = time.monotonic() + max(3 * poll, 6.0)
                        logger.warning(f"LIVE exit {trade_id[:8]}: deadline hit — "
                                       f"cancel requested for order {order_id}; "
                                       f"resolving race")
                        continue
                    except Exception as e:
                        # Cancel failed — the order may still be working. Keep
                        # the order id on the record so the NEXT tick RESUMES
                        # this order rather than double-submitting.
                        self._alert_live_exit_once(
                            trade_id, "deadline",
                            f"LIVE close UNFILLED at deadline {trade_id[:8]} "
                            f"order {order_id}; cancel failed ({e}) — resuming "
                            f"same order next tick, position stays OPEN")
                        return FillResult(confirmed=False, partial=done_qty > 0,
                                          order_id=str(order_id),
                                          detail="deadline; cancel failed; resuming next tick")
                else:
                    # Cancel didn't resolve within the grace window either.
                    self._alert_live_exit_once(
                        trade_id, "deadline",
                        f"LIVE close UNRESOLVED {trade_id[:8]} order {order_id} "
                        f"(cancel pending) — resuming next tick, position OPEN")
                    return FillResult(confirmed=False, partial=done_qty > 0,
                                      order_id=str(order_id),
                                      detail="deadline; cancel unresolved; resuming next tick")
            time.sleep(poll)

    def _resolve_dead_order(self, record, placed, prior, total,
                            order_id, trade_id) -> FillResult:
        """A close order reached a terminal non-FILLED state. Harvest whatever
        partial fills it made, then either book (if cumulative fills now cover
        the position — the cancel/fill race can end here), report a partial, or
        report a clean miss. Never books a partial as whole."""
        record.pop("_live_exit_order_id", None)
        fill = self._net_fill_price(record, placed)
        if fill is not None and fill[0] > 0:
            prior.append(fill)
            record["_live_exit_fills"] = prior
            if sum(q for q, _ in prior) >= total:
                return self._book_from_fills(record, prior, total, order_id)
            return self._partial_result(record, prior, total, order_id, trade_id)
        # r105 — the rung did not fill: refuse it so the next tick posts the
        # NEXT rung rather than re-offering a price the book already declined.
        try:
            self._exit_walk_refused(record, float(record.get("_exit_last_limit") or 0.0))
        except Exception:                                      # noqa: BLE001
            pass
        self._alert_live_exit_once(
            trade_id, "unfilled",
            f"LIVE close NOT FILLED by deadline {trade_id[:8]} (order {order_id} "
            f"ended {placed.status}, zero fills) — position stays OPEN; "
            f"re-pricing and retrying")
        return FillResult(confirmed=False, order_id=str(order_id),
                          detail=f"not filled ({placed.status}); re-price and retry")

    def _partial_result(self, record, prior, total, order_id, trade_id) -> FillResult:
        done = sum(q for q, _ in prior)
        record["_live_exit_fills"] = prior
        self._alert_live_exit_once(
            trade_id, "partial",
            f"LIVE close PARTIAL {trade_id[:8]}: {done:g}/{total} filled — "
            f"remainder resubmits next tick; booking deferred until fully closed")
        return FillResult(confirmed=False, partial=True, order_id=str(order_id),
                          detail=f"partial {done:g}/{total}; remainder resubmits next tick")

    def _book_from_fills(self, record, fills, total, order_id) -> FillResult:
        """All contracts confirmed closed — return the quantity-weighted net
        fill price (the broker's, never the mark) and clear the exit state."""
        qty = sum(q for q, _ in fills)
        wavg = sum(q * p for q, p in fills) / qty
        for k in ("_live_exit_fills", "_live_exit_order_id", "_live_exit_last_order_id",
                  "_exit_last_limit"):
            record.pop(k, None)
        self._exit_walk_done(record)      # r105 — no stale ratchet outlives a fill
        logger.info(f"LIVE exit {record['trade_id'][:8]}: CONFIRMED fill "
                    f"{qty:g}/{total} @ net {wavg:.4f} (order {order_id})")
        return FillResult(confirmed=True, fill_price=round(float(wavg), 4),
                          order_id=str(order_id) if order_id is not None else None,
                          detail=f"broker-confirmed fill, {len(fills)} order(s)")

    def _alert_live_exit_once(self, trade_id: str, kind: str, msg: str):
        logger.error(msg)
        if (trade_id, kind) in self._live_exit_alerted:
            return
        self._live_exit_alerted.add((trade_id, kind))
        try:
            from notifications.alert_manager import get_alert_manager
            get_alert_manager()._send(f"\U0001F6A8 {msg}")
        except Exception as e:
            logger.warning(f"Live-exit alert failed to send: {e}")

    # ── Order construction / submission (live only) ──────────────────────────

    # ═══════════════════════════════════════════════════════════════════════
    # r105 — THE EXIT LADDER. TRADES.md §6, per-transaction policy.
    # ═══════════════════════════════════════════════════════════════════════
    # Every close has posted a single limit at mark since v3.8 and re-priced it
    # each tick. That is right for SOME exits and wrong for others, and §6 says
    # which is which:
    #
    #   structural / profit-side close   FULL WALK
    #   15% floor stop                   STRAIGHT TO MARK, re-priced at mark
    #   debit hard close (15:50)         the flatten ladder, crosses at 15:55   (r149)
    #   assignment-risk close (15:45)    RESTS at its best case, crosses at 15:55 (r149)
    #   ~~credit hard close (15:45)      NICKEL, else ASSIGNMENT — never cross~~  (r105, superseded)
    #
    # ⚠️ THE FLOOR DOES NOT WALK, AND THAT IS A RISK RULING NOT AN OPTIMISATION.
    # Operator: a thesis-invalidated stop that spends six ticks hunting a better
    # fill has turned a floor into a negotiation.
    # 🔴 r149 — THE PARAGRAPH BELOW IS SUPERSEDED BY THE OPERATOR'S END OF DAY
    # (2026-09-26): assignment risk rests at its best case from 15:45 and
    # CROSSES at 15:55 like everything else. Kept as the record of r105.
    # ⚠️ AND THE CREDIT CROSS IS REVERSED. `hard_close_order_mode` returns
    # 'market' from 15:45 — "the position MUST close; cross and be done". For a
    # CREDIT vertical the operator's ruling replaces that: "I'll take assignment
    # over a shitty market order fill." The overnight/margin cost is accepted
    # with the price known. DEBITS KEEP THE CROSS: a long that does not close
    # does not assign, it EXPIRES WORTHLESS — there is no assignment tradeoff
    # to take, so paying the spread beats losing the premium.
    _FLOOR_REASONS = ("condor_stop", "hard_stop", "stop_hit", "adopted_stop",
                      "structure_stop", "tcs_breach", "orb_structure_stop")

    @classmethod
    def _exit_policy(cls, record: TradeRecord, reason: str) -> str:
        """'floor' | 'eod_resting' | 'eod_cross' | 'debit_hard_close' | 'walk'.

        r149: an assignment-risk close RESTS at its best case until 15:55, then
        CROSSES like everything else (r105's never-cross is superseded)."""
        r = (reason or "").lower()
        if "hard_close" in r:
            if has_assignment_risk(record):
                return ("eod_cross" if hard_close_order_mode(now_et()) == "market"
                        else "eod_resting")
            return "debit_hard_close"
        # r209 — a management intent DECLARES its pricing; honoured only for its own reason
        _decl = record.get("_exit_pricing") if hasattr(record, "get") else None
        if (isinstance(_decl, tuple) and len(_decl) == 2 and _decl[0] == reason
                and _decl[1] in ("floor", "walk")):
            return _decl[1]
        if any(k in r for k in cls._FLOOR_REASONS):
            return "floor"
        return "walk"

    @classmethod
    def _eod_legs(cls, record: TradeRecord):
        """r149 — [(occ_symbol, signed qty per unit)], +1 long / -1 short, or None."""
        g = record.get
        if record.get("is_butterfly"):
            return [(g("lower_symbol"), 1), (g("center_symbol"), -2), (g("upper_symbol"), 1)]
        if is_tent(record):
            return [(g("short_symbol"), -1), (g("long_symbol"), 1), (g("lower_symbol"), 1)]
        if g("short_symbol") and g("long_symbol"):
            return [(g("short_symbol"), -1), (g("long_symbol"), 1)]
        if g("option_symbol"):
            return [(g("option_symbol"), -1 if g("is_short_position") else 1)]
        return None

    @classmethod
    def _eod_best_case(cls, record: TradeRecord):
        """r149 (EOD.1) — the operator's "best case on the trajectory", estimated
        BY 15:55 (his refinement): what the position should be worth at the cross
        if spot holds where it is now — each leg priced by Black-Scholes (r = 0)
        with the minutes then left to the 16:00 expiry, at its own chain IV
        (`_eod_iv`, stamped by position_manager; the chain's ATM IV when a leg has
        none). No IV at all -> the leg's intrinsic value (the expiry value), so
        the estimate degrades toward the old rule, never toward an invented
        number. -> (limit, side, why) or None.

        A structure we are SHORT (credit vertical, tent, short single) is bought
        back: limit = max(expiry cost, a nickel) — the nickel close when it is
        worthless. A structure we are LONG (butterfly, long single) is sold:
        limit = max(expiry value - one tick, one tick) — at a pin a fly rests
        near its width; deep ITM (~1 delta) a single rests at parity. Spot is
        the `_eod_spot` position_manager stamps each EOD tick; absent -> None,
        and the caller falls back to the mark rather than invent a price."""
        try:
            spot = float(record.get("_eod_spot") or 0.0)
            legs = cls._eod_legs(record)
            if spot <= 0 or not legs:
                return None
            from execution.broker_reconcile import parse_occ
            from config import EOD_CROSS_AT_ET as _X
            import math
            mins_left = max(0.0, 16 * 60 - (_X[0] * 60 + _X[1]))          # 5 at 15:55
            # 🔴 EOD.3 (r42) — EACH LEG IS PRICED TO ITS OWN EXPIRY, not to today's 16:00.
            # The 5 minutes above are only the time left on a 0DTE leg. A leg expiring
            # on a later day keeps those days of time value: CVX 2026-10-27, a 10-30
            # 230P priced with 5 minutes left came out at its intrinsic 1.26, was judged
            # "settled", and paper booked it at 1.25 against a 3.70 bid (-$1,448
            # instead of about +$976 at the mark).
            _today = now_et().date()
            def _t_yrs(exp_iso):
                try:
                    days = (date.fromisoformat(str(exp_iso)[:10]) - _today).days
                except (TypeError, ValueError):
                    days = 0
                return (max(0, days) * 24 * 60 + mins_left) / (365.0 * 24 * 60)
            ivs = record.get("_eod_iv") or {}
            iv_default = float(record.get("_eod_iv_atm") or 0.0)
            def _n(x):
                return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
            def _px(k, call, iv, t_yrs):
                intrinsic = max(spot - k, 0.0) if call else max(k - spot, 0.0)
                if iv <= 0 or t_yrs <= 0:
                    return intrinsic
                sd = iv * math.sqrt(t_yrs)
                d1 = (math.log(spot / k) + 0.5 * sd * sd) / sd
                d2 = d1 - sd
                c = spot * _n(d1) - k * _n(d2)
                return max(c if call else c - spot + k, intrinsic)
            val = 0.0; used_iv = []
            for sym, q in legs:
                o = parse_occ(sym or "")
                if not o:
                    return None
                iv = float(ivs.get(sym, 0.0) or 0.0) or iv_default
                used_iv.append(iv)
                val += q * _px(float(o["strike"]), o["option_side"] == "call", iv,
                               _t_yrs(o.get("expiry")))
            tick = cls._tick_for(record)
            if val <= 0:          # we are net SHORT: buy it back
                cost = -val
                limit = cls._round_to_tick(max(cost, 0.05), record)
                return limit, "buy", f"15:55 cost {cost:.2f} at spot {spot:.2f} (iv {max(used_iv):.2f}), nickel floor"
            limit = cls._round_to_tick(max(val - tick, tick), record)
            return limit, "sell", f"15:55 value {val:.2f} at spot {spot:.2f} (iv {max(used_iv):.2f}), less a tick"
        except Exception as exc:                               # noqa: BLE001
            logger.warning("[eod] best-case price failed for %s (%s) — mark",
                           str(record.get("trade_id", ""))[:8], exc)
            return None

    @classmethod
    def _eod_determined(cls, record: TradeRecord):
        """r149 (EOD.1) — the operator's paper rule: "best-case available when deep
        ITM (par, nickel)". A position whose outcome is already SETTLED — its
        15:55 estimate (with IV) prices to the same tick as its expiry value, so
        no time value is left to lose — gets its best case: a worthless short at
        the nickel, a deep-ITM long at parity less a tick. -> (limit, side, why)
        or None. WITHOUT IV nothing can show the outcome is settled (the estimate
        IS the expiry value), so None: the position waits for the cross."""
        if not ((record.get("_eod_iv") or {}) or float(record.get("_eod_iv_atm") or 0.0) > 0):
            return None
        est = cls._eod_best_case(record)
        if est is None:
            return None
        bare = dict(record); bare["_eod_iv"] = {}; bare["_eod_iv_atm"] = 0.0
        exp = cls._eod_best_case(bare)
        if exp is None or (exp[0], exp[1]) != (est[0], est[1]):
            return None
        return est[0], est[1], f"settled — {est[2]}"

    @staticmethod
    def _exit_quote(record: TradeRecord) -> Tuple[float, float]:
        """The two-sided quote position_manager stashed this tick, or (0,0)."""
        try:
            return (float(record.get("_exit_bid") or 0.0),
                    float(record.get("_exit_ask") or 0.0))
        except (TypeError, ValueError):
            return (0.0, 0.0)

    def _exit_limit(self, record: TradeRecord, reason: str, mark: float,
                    side: str, structure: str) -> Tuple[float, str]:
        """The price to post for THIS close attempt, and why.

        `side` is what we are doing to the STRUCTURE: closing a short vertical
        or a long single is a 'buy' of it back / a 'sell' of it out.
        """
        policy = self._exit_policy(record, reason)
        if policy == "eod_resting":
            best = self._eod_best_case(record)
            if best is not None:
                return best[0], f"eod resting — best case {best[0]:.2f} ({best[2]})"
            return limit_at_mark(mark, floor=self._tick_for(record)), "eod resting — no spot/legs, mark"
        bid, ask = self._exit_quote(record)
        # 🔴 TICK.2 — a SINGLE-LEG mark limit goes through the venue grid
        # (tick_size.snap via limit_at_mark's symbol), exactly as the walk path
        # and the entry side already do. Without the symbol, limit_at_mark only
        # rounded to cents, so a floor stop on a nickel/dime-grid name posted an
        # invalid increment LIVE. Spreads and flies keep the old rounding until
        # the complex-order increment rule is measured.
        _grid = dict(symbol=str(record.get("symbol", "") or ""), side=side,
                     bid=bid or 0.0, ask=ask or 0.0) if structure == "single" else {}
        if policy == "floor" or ask <= 0:
            # No walk: mark, re-priced at mark every tick until it fills.
            return limit_at_mark(mark, floor=self._tick_for(record), **_grid),                 f"{policy} — mark, no walk"
        try:
            from execution import ladder_registry as _lr
            key = _lr.intent_key(str(record.get("trade_id", ""))[:12],
                                 "close", structure)
            got = _lr.price_for(key, side, bid, ask,
                                str(record.get("symbol", "")))
            if got:
                record["_exit_walk_key"] = key
                return float(got[0]), f"{policy} — {got[1]}"
        except Exception as exc:                               # noqa: BLE001
            logger.warning("[ladder] exit pricing failed (%s) — mark", exc)
        return limit_at_mark(mark, floor=self._tick_for(record), **_grid), f"{policy} — mark"

    def _exit_walk_refused(self, record: TradeRecord, price: float) -> None:
        key = record.get("_exit_walk_key")
        if not key:
            return
        try:
            from execution import ladder_registry as _lr
            _lr.refuse(key, price)
        except Exception as exc:                               # noqa: BLE001
            logger.debug("[ladder] exit refuse failed: %s", exc)

    def _exit_walk_done(self, record: TradeRecord) -> None:
        key = record.pop("_exit_walk_key", None)
        if not key:
            return
        try:
            from execution import ladder_registry as _lr
            _lr.clear(key)
        except Exception as exc:                               # noqa: BLE001
            logger.debug("[ladder] exit clear failed: %s", exc)

    def _submit_live_close(self, record: TradeRecord, contracts: int,
                           mark_price: Optional[float],
                           reason: str = "") -> Optional["object"]:
        """Order SUBMISSION only (no fill confirmation) — returns the broker
        PlacedOrder (carrying .id for polling) on submit success, else None.
        Submission is not a fill; only _confirm_and_book_live_exit may book.

        Routing (v3.5): condor legs are two-legged VERTICALS and now close as
        a single 2-leg spread order via _close_vertical — previously they fell
        through to _close_single_leg, which SELL_TO_CLOSEd only the short
        symbol (wrong action for a short, long leg orphaned at the broker).
        """
        # v3.8: MARK-LIMIT policy. Closes post AT THE MARK and are re-priced to
        # a fresh mark on every retry tick — we never pay the spread. The ONE
        # exception is the end-of-day close: from the 15:55 cross (config
        # EOD_SCHEDULE) the position MUST close (an unfilled 0DTE at the bell is
        # an expiry / assignment, not an overnight hold), so force_market crosses.
        # Before it, assignment risk RESTS at its best case (from 15:45) and
        # debits ladder (from 15:50). See execution/limit_ladder.py.
        # r149 — r105's "the cross is for debits only" is SUPERSEDED: every
        # structure crosses at 15:55. See _exit_policy.
        force_market = ("hard_close" in (reason or "").lower()
                        and hard_close_order_mode(now_et()) == "market")   # r149: credits cross too
        try:
            session = get_session()
            account = get_account()
            if is_tent(record):
                return self._close_tent(session, account, record, contracts,
                                        mark_price, reason=reason)
            if bool(record.get("is_butterfly", False)):
                return self._close_butterfly(session, account, record,
                                             contracts, mark_price, force_market,
                                             reason=reason)
            is_vertical = (bool(record.get("is_condor_leg"))
                           or record.get("strategy") == "IronCondorStrategy"
                           or (record.get("short_symbol") and record.get("long_symbol")))
            if is_vertical:
                return self._close_vertical(session, account, record,
                                            contracts, mark_price, force_market,
                                            reason=reason)
            return self._close_single_leg(session, account, record, contracts,
                                          mark_price, force_market, reason=reason)
        except Exception as e:
            logger.error(f"Live close submit failed for {record['trade_id'][:8]}: {e}")
            return None

    @staticmethod
    def _tick_for(record: TradeRecord) -> float:
        """Price increment for close limits: SPX-family trades in nickels."""
        sym = str(record.get("symbol", "") or "").upper()
        return 0.05 if sym in ("SPX", "SPXW", "XSP") else 0.01

    @classmethod
    def _round_to_tick(cls, price: float, record: TradeRecord,
                       single_leg: bool = False) -> float:
        tick = cls._tick_for(record)
        # 🔴 TICK.1 — Cboe SPX/SPXW series trade in $0.05 below $3.00 and in
        # $0.10 AT OR ABOVE it. A single-leg close limit like 12.35 is an
        # invalid price LIVE (paper fills at the mark and never shows it).
        # Scoped to the SINGLE-LEG close, the case measured; spreads, flies and
        # XSP are unchanged until their own increment rules are measured.
        sym = str(record.get("symbol", "") or "").upper()
        if single_leg and sym in ("SPX", "SPXW") and price >= 3.0:
            tick = 0.10
        return max(tick, round(round(price / tick) * tick, 2))

    def _place(self, session, account, order, what: str) -> Optional["object"]:
        response = sdk_result(account.place_order(session, order, dry_run=False))   # B0
        if getattr(response, "errors", None):
            logger.error(f"{what} order errors: {response.errors}")
            return None
        placed = getattr(response, "order", None)
        if placed is None or getattr(placed, "id", None) is None:
            logger.error(f"{what} order: no order id in response — cannot poll; "
                         f"treating as submit failure")
            return None
        return placed

    def _close_single_leg(self, session, account, record, contracts,
                          mark_price: Optional[float] = None,
                          force_market: bool = False, reason: str = ""):
        """v3.8: posts a LIMIT AT THE MARK, not a market order.

        A single-leg market order paid the touch on every exit — combined with
        the market-order ENTRY that was ~25% of premium round-trip on a $0.20
        0DTE with a $0.05 spread, larger than the edge being traded. We now post
        at the mark and let the retry loop re-price against a fresh mark each
        tick, which chases a falling contract instead of parking at a stale
        price. force_market crosses, and is set ONLY by the end-of-day cross (15:55)."""
        symbol = record.get("option_symbol", "")
        if not symbol:
            logger.error("Cannot close: no option_symbol in record")
            return None
        # v3.5: an adopted SHORT leg must BUY to close, not sell more short.
        action = (OrderAction.BUY_TO_CLOSE if record.get("is_short_position")
                  else OrderAction.SELL_TO_CLOSE)
        leg = Leg(
            instrument_type = InstrumentType.EQUITY_OPTION,
            symbol          = symbol,
            action          = action,
            quantity        = contracts,
        )
        _no_mark = mark_price is None or mark_price <= 0
        if _no_mark and not force_market and hard_close_order_mode(now_et()) != "market":
            # 🔴 r256 / F3 (otv4 r475) — no mark before the cross: post NOTHING, page once, retry next tick.
            record["_exit_nomark_hold"] = 1
            self._alert_live_exit_once(
                record.get("trade_id", ""), "nomark",
                f"LIVE close {str(record.get('trade_id', ''))[:8]}: NO MARK for {symbol} — "
                f"nothing posted before the cross (no market order into an unknown book); "
                f"retrying each tick, position stays OPEN")
            return None
        record.pop("_exit_nomark_hold", None)
        if force_market or _no_mark:
            # the end-of-day cross, or no mark at/after it — cross and be done.
            order = NewOrder(
                time_in_force = OrderTimeInForce.DAY,
                order_type    = OrderType.MARKET,   # single-leg market is accepted
                legs          = [leg],
            )
            why = "hard-close cross" if force_market else "no mark, at/after the cross"
            return self._place(session, account, order,
                               f"Single-leg close (MARKET — {why})")
        tick  = self._tick_for(record)
        # r105 — selling a long OUT is the ladder's "sell" side: start 25% in
        # from the ask, walk down toward mark, never accept below mark. A FLOOR
        # stop skips the walk and goes to mark (see _exit_limit).
        # 🔴 r470 / BBK.1 — the side FOLLOWS THE ACTION. This was the literal
        # "sell", so an adopted short's BUY_TO_CLOSE walked down from the ask and
        # snapped up: a buy-back paying above its mark.
        _side = "buy" if action == OrderAction.BUY_TO_CLOSE else "sell"
        _lim, _why = self._exit_limit(record, reason, mark_price, _side, "single")
        limit = self._round_to_tick(_lim, record, single_leg=True)   # TICK.1
        record["_exit_last_limit"] = limit
        logger.info("[ladder] single CLOSE %s @ %.2f — %s",
                    str(record.get("trade_id", ""))[:8], limit, _why)
        # SDK signed convention: SELL_TO_CLOSE receives a CREDIT (positive);
        # BUY_TO_CLOSE on an adopted short PAYS a debit (negative).
        signed = limit if action == OrderAction.SELL_TO_CLOSE else -limit
        order = NewOrder(
            time_in_force = OrderTimeInForce.DAY,
            order_type    = OrderType.LIMIT,
            price         = Decimal(str(signed)),
            legs          = [leg],
        )
        return self._place(session, account, order,
                           f"Single-leg close (LIMIT @ mark {limit:.2f})")

    def _close_vertical(self, session, account, record, contracts,
                        mark_price: Optional[float],
                        force_market: bool = False, reason: str = ""):
        """Close a condor-leg vertical as ONE 2-leg spread order: BUY_TO_CLOSE
        the short strike, SELL_TO_CLOSE the long strike. tastytrade rejects
        MARKET on spreads, so this is a marketable LIMIT: debit capped at the
        spread width (a vertical can never be worth more than its width), so
        even with no mark the order is bounded and safe.

        SDK NOTE (verified v13.x): NewOrder.price is SIGNED — negative=debit,
        positive=credit. price_effect on NewOrder is ignored by current SDKs.
        Closing a short vertical PAYS a debit → price must be NEGATIVE.
        """
        short_sym = record.get("short_symbol", "")
        long_sym  = record.get("long_symbol", "")
        if not short_sym or not long_sym:
            logger.error("Cannot close vertical: missing short/long symbols")
            return None
        width  = float(record.get("spread_width") or 0.0)
        # v3.8: post AT THE MARK (was mark + a fixed $0.10 buffer, i.e. paying
        # up on every close). tastytrade rejects MARKET on spreads, so the
        # 15:45 "market order" for a vertical is a maximally-marketable limit:
        # the debit capped at the spread WIDTH, which a vertical can never
        # exceed — guaranteed to fill, bounded, and safe.
        _policy = self._exit_policy(record, reason)
        _why = _policy
        if _policy == "eod_resting":
            # r149 (EOD.1) — RESTING BEST CASE, re-priced each tick, until 15:55
            # crosses (force_market). Supersedes r105's nickel-or-assignment.
            limit, _why = self._exit_limit(record, reason, float(mark_price or 0.0), "buy", "vertical")
            if width > 0:
                limit = min(limit, width)
        # r149 — r105's credit branch ("nickel, else assignment, never cross") is
        # SUPERSEDED by the operator's 2026-09-26 schedule: rest at the best case
        # (above) until 15:55, then cross like every structure (below).
        elif force_market:
            if width <= 0:
                logger.error("Hard-close vertical: no spread_width to bound the "
                             "cross — cannot price")
                return None
            limit = width
            _why = "debit hard close — bounded cross"
        elif mark_price is not None and mark_price >= 0:
            # r105 — closing a short vertical BUYS it back: the ladder's "buy"
            # side, starting 25% in from the bid and never paying above mark.
            limit, _why = self._exit_limit(record, reason, mark_price,
                                           "buy", "vertical")
            if width > 0:
                limit = min(limit, width)      # a vertical cannot exceed its width
        elif width > 0:
            limit = width   # max possible value of the vertical — bounded marketable
            _why = "no mark — bounded marketable"
        else:
            logger.error("Cannot price vertical close: no mark and no spread_width")
            return None
        limit = self._round_to_tick(limit, record)
        record["_exit_last_limit"] = limit
        logger.info("[ladder] vertical CLOSE %s @ %.2f — %s",
                    str(record.get("trade_id", ""))[:8], limit, _why)
        legs = [
            Leg(instrument_type=InstrumentType.EQUITY_OPTION,
                symbol=short_sym, action=OrderAction.BUY_TO_CLOSE,  quantity=contracts),
            Leg(instrument_type=InstrumentType.EQUITY_OPTION,
                symbol=long_sym,  action=OrderAction.SELL_TO_CLOSE, quantity=contracts),
        ]
        order = NewOrder(
            time_in_force = OrderTimeInForce.DAY,
            order_type    = OrderType.LIMIT,
            price         = Decimal(str(-limit)),   # negative = DEBIT paid to close
            legs          = legs,
        )
        return self._place(session, account, order,
                           f"Vertical close ({'MARKET-equiv @ width' if force_market else 'LIMIT @ mark'} "
                           f"{limit:.2f})")

    def _close_tent(self, session, account, record, contracts,
                    mark_price: Optional[float], reason: str = ""):
        """r106 — close all three legs as ONE order: buy back the short, sell
        the same-type wing, sell the opposite-type hedge.

        ⚠️ ONE ORDER, NOT THREE. Legging out of a hedged structure re-opens the
        risk it was built to cap: sell the hedge first and the short is bare on
        the breached side for however long the rest takes.
        ⚠️ AND IT NEVER CROSSES. Closing the tent PAYS a debit (we buy back a
        short worth more than the two longs we sell, or we collect — either way
        the sign is carried by the price). The ladder walks it; the floor stop
        goes to mark. tastytrade rejects MARKET on spreads regardless.
        """
        short_sym = record.get("short_symbol", "")
        long_sym  = record.get("long_symbol", "")
        hedge_sym = record.get("lower_symbol", "")     # r106: the hedge leg
        if not all([short_sym, long_sym, hedge_sym]):
            logger.error("Cannot close tent: missing leg symbols "
                         "(short=%s long=%s hedge=%s)",
                         short_sym, long_sym, hedge_sym)
            return None
        if mark_price is None:
            logger.warning("Tent close: no mark this pass — declining, will "
                           "retry with a fresh mark")
            return None
        limit, _why = self._exit_limit(record, reason, float(mark_price),
                                       "buy", "tent")
        limit = self._round_to_tick(limit, record)
        record["_exit_last_limit"] = limit
        logger.info("[ladder] TENT CLOSE %s @ %.2f — %s",
                    str(record.get("trade_id", ""))[:8], limit, _why)
        legs = [
            Leg(instrument_type=InstrumentType.EQUITY_OPTION,
                symbol=short_sym, action=OrderAction.BUY_TO_CLOSE,  quantity=contracts),
            Leg(instrument_type=InstrumentType.EQUITY_OPTION,
                symbol=long_sym,  action=OrderAction.SELL_TO_CLOSE, quantity=contracts),
            Leg(instrument_type=InstrumentType.EQUITY_OPTION,
                symbol=hedge_sym, action=OrderAction.SELL_TO_CLOSE, quantity=contracts),
        ]
        order = NewOrder(
            time_in_force = OrderTimeInForce.DAY,
            order_type    = OrderType.LIMIT,
            price         = Decimal(str(-limit)),   # negative = DEBIT paid to close
            legs          = legs,
        )
        return self._place(session, account, order,
                           f"Tent close (LIMIT {limit:.2f})")

    def _close_butterfly(self, session, account, record, contracts,
                         mark_price: Optional[float],
                         force_market: bool = False, reason: str = ""):
        """Close a long butterfly (sell wings, buy back the 2x short body) as
        one 3-leg order. v3.5: MARKET → marketable LIMIT (tastytrade rejects
        MARKET on spreads — the old market order would have failed every tick).
        Selling the fly RECEIVES a credit → price is POSITIVE (signed SDK
        convention), floored at one tick below mark; no mark → decline this
        pass rather than guess (retry tick brings a fresh mark)."""
        lower_sym  = record.get("lower_symbol", "")
        center_sym = record.get("center_symbol", "")
        upper_sym  = record.get("upper_symbol", "")
        if not all([lower_sym, center_sym, upper_sym]):
            logger.error("Cannot close butterfly: missing leg symbols")
            return None
        tick = self._tick_for(record)
        # v3.8: post AT THE MARK (was mark - a fixed $0.10 buffer — selling the
        # fly cheap on every close). At 15:45 the flatten must complete and
        # tastytrade rejects MARKET on spreads, so the cross is a limit at ONE
        # TICK of credit: the lowest price we can ask, hence maximally
        # marketable for a sale.
        if force_market:
            limit = self._round_to_tick(tick, record)
        elif self._exit_policy(record, reason) == "eod_resting":
            # r149 (EOD.1) — rest at the fly's value at expiry at current spot, less a tick.
            limit, _why = self._exit_limit(record, reason, float(mark_price or 0.0), "sell", "butterfly")
            limit = self._round_to_tick(limit, record)
        elif mark_price is None or mark_price < 0:
            logger.warning("Butterfly close: no mark to price the limit — "
                           "declining this pass, will retry with a fresh mark")
            return None
        else:
            limit = self._round_to_tick(limit_at_mark(mark_price, floor=tick), record)
        legs = [
            Leg(instrument_type=InstrumentType.EQUITY_OPTION,
                symbol=lower_sym,  action=OrderAction.SELL_TO_CLOSE, quantity=contracts),
            Leg(instrument_type=InstrumentType.EQUITY_OPTION,
                symbol=center_sym, action=OrderAction.BUY_TO_CLOSE,  quantity=contracts * 2),
            Leg(instrument_type=InstrumentType.EQUITY_OPTION,
                symbol=upper_sym,  action=OrderAction.SELL_TO_CLOSE, quantity=contracts),
        ]
        order = NewOrder(
            time_in_force = OrderTimeInForce.DAY,
            order_type    = OrderType.LIMIT,
            price         = Decimal(str(limit)),   # positive = CREDIT received
            legs          = legs,
        )
        return self._place(session, account, order,
                           f"Butterfly close ({'MARKET-equiv @ 1 tick' if force_market else 'LIMIT @ mark'} "
                           f"{limit:.2f})")

    # ── Fill readback ─────────────────────────────────────────────────────────

    def _net_fill_price(self, record: TradeRecord,
                        placed) -> Optional[Tuple[float, float]]:
        """Read (closed_quantity, net_fill_price) from a PlacedOrder's per-leg
        fills. The net is on the SAME basis as the marks _fetch_current_premium
        produces, so _execute_exit's P&L math is untouched:
          vertical:   short_avg - long_avg          (mark: short_mark - long_mark)
          butterfly:  lower + upper - 2*center      (mark: same combination)
          single leg: the leg's weighted avg fill
        closed_quantity is the min across legs of (filled / leg ratio) — legs of
        a complex order fill together, min() is the safe floor. Returns None if
        nothing readable filled."""
        def leg_stats(sym: str) -> Tuple[float, Optional[float]]:
            for leg in (getattr(placed, "legs", None) or []):
                if getattr(leg, "symbol", None) == sym:
                    fills = getattr(leg, "fills", None) or []
                    q = sum(float(f.quantity) for f in fills)
                    if q <= 0:
                        return 0.0, None
                    p = sum(float(f.quantity) * float(f.fill_price) for f in fills) / q
                    return q, p
            return 0.0, None

        # 🔴 r106 — TENT FIRST, and on the SAME basis its mark uses:
        # short − wing − hedge. It would otherwise be claimed by the vertical
        # branch below (it has short_symbol and long_symbol), which would read
        # only two of its three legs and book a net that never existed.
        if is_tent(record):
            qs, ps = leg_stats(record.get("short_symbol", ""))
            ql, pl = leg_stats(record.get("long_symbol", ""))
            qh, ph = leg_stats(record.get("lower_symbol", ""))
            qty = min(qs, ql, qh)
            if qty <= 0 or None in (ps, pl, ph):
                return None
            return qty, round(ps - pl - ph, 4)

        if bool(record.get("is_butterfly", False)):
            ql, pl = leg_stats(record.get("lower_symbol", ""))
            qc, pc = leg_stats(record.get("center_symbol", ""))
            qu, pu = leg_stats(record.get("upper_symbol", ""))
            qty = min(ql, qu, qc / 2.0)
            if qty <= 0 or None in (pl, pc, pu):
                return None
            return qty, round(pl + pu - 2.0 * pc, 4)

        if (record.get("is_condor_leg")
                or record.get("strategy") == "IronCondorStrategy"
                or (record.get("short_symbol") and record.get("long_symbol"))):
            qs, ps = leg_stats(record.get("short_symbol", ""))
            ql, pl = leg_stats(record.get("long_symbol", ""))
            qty = min(qs, ql)
            if qty <= 0 or None in (ps, pl):
                return None
            return qty, round(ps - pl, 4)

        q, p = leg_stats(record.get("option_symbol", ""))
        if q <= 0 or p is None:
            return None
        return q, round(p, 4)

    def clear_trail(self, trade_id: str):
        self._trail_stops.pop(trade_id, None)
        self._trail_active.pop(trade_id, None)
        self._bos_trackers.pop(trade_id, None)
        self._post_target_trail.pop(trade_id, None)


# Singleton
_exit_engine: Optional[ExitEngine] = None


# ⚠️ AUDIT F0 (2026-08-20) — THE CLASS WAS CUT IN HALF AND EVERY EXIT WAS DEAD.
# r38 landed `_track_excursion` as a module-level function PHYSICALLY INSIDE the
# class body region (column 0 at what was line 782). Python read it as the end
# of `class ExitEngine`; the ~2,000 lines below it — `evaluate` and all 33
# exit evaluators, indented as methods — silently became NESTED LOCAL FUNCTIONS
# of `_track_excursion`, created and discarded on each call, bound to nothing.
# The file compiled. `import main` passed. check_imports passed. Every checker
# passed, because NO CHECK EXECUTED AN EXIT. At runtime, the first
# `exit_eng.evaluate(...)` on any open position raised AttributeError into the
# loop's catch-all, every tick: no premium stop, no trail, no theta bleed, no
# nickel close, no condor ladder could ever fire — only the independent 15:45
# flatten_all() stood between an open position and the close. Found by the
# rewritten check_condor_spec (AUDIT F5), whose EXECUTING replacement raised
# the AttributeError its stub predecessor could never see. This function now
# lives where a module-level function belongs: BELOW the class it must not
# bisect. tests/check_exit_executes.py drives evaluate() so this class cannot
# fall apart silently again.
def _trail_was_armed(record, persisted: float) -> bool:
    """r493 / EXIT.6 — would an engine that never restarted hold this trade's
    percentage trail ARMED? _update_trail arms it the first tick the mark is at
    or above `trail_activation`, so the persisted peak (mfe_premium /
    max_premium_seen, both written while the position lives) answers it. A
    level below the activation seed with no peak is the FVG trail's alone
    (it arms earlier, at +20%), and the uninterrupted engine would still seed
    entry x (1 + TRAIL_LOCK_PCT) at activation, so it is left un-armed."""
    def _f(v):
        try:
            v = float(v)
            return v if v == v and v > 0 else None
        except (TypeError, ValueError):
            return None
    act = _f(record.get("trail_activation"))
    peaks = [p for p in (_f(record.get("mfe_premium")), _f(record.get("max_premium_seen")))
             if p is not None]
    if act is not None and peaks:
        return max(peaks) >= act
    entry = _f(record.get("entry_premium"))
    return entry is not None and persisted >= entry * (1 + TRAIL_LOCK_PCT)


def _track_excursion(record, current_premium: float) -> None:
    """Record the best and worst mark this position has seen, and WHEN.

    v4.0. ⚠️ THE DATA EXISTED AND WAS THROWN AWAY. `TrailState.peak_close`
    updates every tick to drive the trailing stop and dies with the process, so
    the book could not answer **"how long until a winner declared itself"** -
    which is the number the sideways-grinder stop is made of. Same defect as
    `pin_concentration` and `flat_angle_deg`: computed every tick, used for a
    decision, never recorded.

    ⚠️ AND IT IS NOT `max_profit`. That column is written ONCE at entry from
    `signal.max_profit` - the THEORETICAL maximum of a defined-risk structure,
    not a realized excursion. Reading it as MFE reads a plan as an outcome.

    ⚠️ BARS ARE COUNTED, NOT TIMED. A wall-clock delta would be wrong across a
    halt or a feed gap; the tick count is what the position actually saw.
    Failure here must never reach the exit decision - a telemetry write is not
    worth a missed stop - so everything is guarded.
    """
    try:
        # ⚠️ A NaN MARK BECAME THE PEAK. `px > best` is False for NaN, but the
        # FIRST call has no best, so `best is None` admitted it unconditionally
        # and mfe_premium was recorded as nan for the life of the position.
        from utils.math_utils import safe_float
        px = safe_float(current_premium)
        if px is None or px <= 0 or px > 1e6:
            return
        n = int(record.get("excursion_ticks") or 0) + 1
        record["excursion_ticks"] = n
        # ⚠️ AUDIT F7 (2026-08-20): `n` is a 15-second TICK count and it was
        # being written into columns named *_bars — every consumer reading
        # "bars from entry to that peak" (the column's own comment) would have
        # mis-timed r38's question ("how long until a winner declares itself")
        # by 4×. A wrong number is worse than a crash. Bars ≈ minutes derived
        # from the poll cadence; tick-vs-wall drift on slow ticks is bounded
        # and preferable to a silent unit lie.
        from config import POLL_INTERVAL_SECONDS as _POLL_S
        bars = max(1, int(round(n * _POLL_S / 60.0)))
        best = record.get("mfe_premium")
        if best is None or px > float(best):
            record["mfe_premium"] = round(px, 4)
            record["mfe_bars"] = bars
        worst = record.get("mae_premium")
        if worst is None or px < float(worst):
            record["mae_premium"] = round(px, 4)
            record["mae_bars"] = bars
    except Exception:                                          # noqa: BLE001
        return


def get_exit_engine(paper_trading: bool = PAPER_TRADING) -> ExitEngine:
    global _exit_engine
    if _exit_engine is None:
        _exit_engine = ExitEngine(paper_trading)
    return _exit_engine
