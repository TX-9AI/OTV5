"""
config.py  v5.5
v5.5  2026-10-30  OTV5 r57 (TCS.LOG1) — TCS IS REACTIVATED AS LOG ONLY: OT_TCS_ACTIVE unset = log. The operator, 2026-10-30: "Can
      you reactivate TCS Monday as 'log only'? But do not trade it." then "Make sure TCS logs everything an executable
      trade logs." TREND_CREDIT_ACTIVE (the TRADE switch) is unchanged and stays False unless OT_TCS_ACTIVE=1. TCS_MODE
      (trade / log / off) and TCS_ENV_REFUSED are what configure.sh's TCS item reads, as PARC_MODE is for PARC (r50);
      strategy/plan_state.py decides the state. In log a fire is booked as a SHADOW trade (execution/shadow_book.py):
      the real entry pipeline at the paper fill, its own store, never an order. Gate tests/check_tcs_shadow.py.
v5.4  2026-10-29  OTV5 r54 (BRK.16) — BREAKOUT'S TARGET AND TRAIL ARM ARE MULTIPLES OF THE OPENING RANGE WIDTH W. The operator,
      2026-10-29: "the target will be from the boundary of the opening range a distance of 1W"; "I want the trailing stop
      activation to occur at 1/2 W." BRK_TARGET_W = 1.0 (target = orb_high + 1W long / orb_low - 1W short; planning only:
      R, the strike, underlying_target) and BRK_TRAIL_ARM_W = 0.5 (the trail arms once the underlying reaches the edge
      +/- 0.5W). BRK_ENTRY_MAX_W = 0.5: "It should honestly refuse if it's already crossed 1/2W" - no Breakout plan on a
      break close at or beyond edge +/- 0.5W, and no fire on a live price there ("that is runaway's domain"). No env
      toggle. BRK_RESEARCH_UNTIL and the FITTED dials are unchanged.
v5.3  2026-10-28  OTV5 r50 (PARC.3) — PARC IS PAUSED: OT_PARC UNSET = log, NOT trade. The operator, after the 10-28 backtest
      (PARC +$47.57 gross per trade vs PARK +$155.26; 68 percent of PARC trades ended on the 5m structure stop, a median
      0.227 percent from the 11:00 close): "Don't go live on the PARC tomorrow until we find a better stop placement." An unset (or empty, or unknown) OT_PARC now
      means log - the plan runs and a would-be PARC is recorded, never ordered; OT_PARC=1 still trades it on a box that
      asks. Gate tests/check_parc.py P13 (v5.1).
v5.2  2026-10-27  OTV5 r46 (PARC.1) — PARC, THE 11:00 CREDIT SPREAD ON THE SAFER SIDE. The operator: "under identical entry
      conditions the PARK trade sells a credit spread ATM nearest the strike on the safer side (1st mark below the current
      price for a long: put spread, or 1st mark above current price for a short: call spread) ... adopt the same scaling
      model we use for breakout, meaning the stop distance will determine our position size. Get rid of the delta stop.
      This will be a hold to 1550 or stop on structure ... also add a nickel close"; "Call it PARC"; "I want 1050 to be
      the floor & use the same ramp in configure.sh (most are set to $2500)"; "No shadow mode. We're paper. It trades
      tomorrow." OT_PARC 1|log|0 (UNSET = 1, trade; PARC_MODE trade|log|off; an unknown value keeps the default and is
      named in PARC_ENV_REFUSED), PARC_MIN_CREDIT 0.20 (4 x CONDOR_NICKEL_CLOSE), ENTRY_WINDOWS["PARC"] = 11:01-11:03,
      CAP_EXCLUDED_STRATEGIES = ("PARK", "PARC"). Gate tests/check_parc.py.
v5.1  2026-10-25  (MEAS.3) — FED_DAY_ORB_BOOST IS REMOVED. macro_data's Fed-day detector is fixed (it had always
      returned False), and its one behavioural reader was ORB's conviction boost; the operator's 2026-10-03 ruling is
      that trading must not change on Fed days, so the flag is record only. Gate tests/check_fed_day_record.py.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.72  2026-10-24  CD.1 - RENT.2/RENT.3 SCRAPPED: OT_REENTRY_GATE / REENTRY_GATE_MODE / REENTRY_GATE_ENV_REFUSED removed (the operator,
      2026-10-24: "The 20 seconds is arbitrary ... It has zero value. Scrap it."). analysis/reentry.py is deleted.
v4.71  2026-10-24  OTV4TEST r316 (BRK.15 + HUNT.13 + RENT.3) - OT_BRK_REFIRE rearm|extreme (UNSET = rearm: a Breakout side
      re-arms on EVERY 1m close back inside its edge; extreme = r131's new session extreme, the old rule); OT_HUNT_AFTER_BRK
      trade|log|off (UNSET = trade: no Hunt on a side after a LOSING Breakout on that side that day); OT_REENTRY_GATE
      UNSET = log (was trade: the 20 s gate records, never blocks). The operator, 2026-10-24 13:45/13:56 ET. A refused
      value reads the default and is named.
v4.70  2026-10-19  OTV4TEST r306 (RENT.2) - OT_REENTRY_GATE off|log|trade (unset = trade; LIVE reads log; a bogus value
      reads log and is named): REENTRY_GATE_MODE / REENTRY_GATE_ENV_REFUSED for analysis/reentry.py's 20 s gate after a
      same-side PREMIUM exit. The operator, 2026-10-19 20:17 ET: "Yes".
v4.69  2026-10-18  OTV4TEST r295 (LIVE.2; the deadline half is a MIRROR of otv4 r474 674e0cc) - LIVE_FILL_DEADLINE_SECONDS
      30 -> 8: a live close waited up to 30 s per position for a fill (+6 s cancel grace), serially, with the main loop
      frozen; five unfilled positions at the 15:50 ladder = >180 s without a heartbeat = the emergency watchdog's kill.
      Audit 2026-10-18 C2; LIVE.1 F1 (never mirrored on 10-05).
v4.68  2026-10-18  OTV4TEST r288 (PARK.1 + BRK.13) - (1) PARK, the operator's friend's 11:00 continuation, TRADED on
       every box (the operator, 2026-10-17 18:21 ET: "Trade it, don't just log it. Paper is free. Call it PARK"; on
       SPX "Use our actual numbers, trade it"): OT_PARK trade|log|off (UNSET = trade), its dials PARK_* and its entry
       window ENTRY_WINDOWS["PARK"] = 11:01-11:03; CAP_EXCLUDED_STRATEGIES = ("PARK",) - its own budget, outside the
       catastrophic cap. (2) OT_BRK_DFLOOR trade|log|off (UNSET = trade): Breakout exits when |delta| <= 0.30 from 10
       min after entry (the operator, 2026-10-17 19:12 ET: "A is fine").
v4.67  2026-10-15  BRK.12 + HUNT.9 (FORK-ONLY) - OT_BRK_REARM and OT_HUNT_REARM log|off (UNSET = log, no trade value): a
       return to the range is evaluated and recorded for Breakout and the Hunt, never traded. The operator, 2026-10-15
       10:16 ET: "Concur on all" (to "BRK.12 / HUNT.9: record-only").
v4.66  2026-10-14  OTV4TEST r285 (HUNT.8) - OT_HUNT_STOP5M off|log|trade (UNSET = trade): the Hunt's thesis-dead line is
       the farther of its entry boundary and the 5m swing as of entry (execution/exit_engine). The operator, 2026-10-14
       11:47 ET: "Yes, we have to".
v4.65  2026-10-14  OTV4TEST r284 (BRK.11) - OT_BRK_STOP5M off|log|trade (UNSET = trade) and BRK_STOP5M_BARS = 3: Breakout's
       stop is the farther of the 1m break bar's extreme and the last 3 CLOSED 5m RTH bars' extreme (strategy/
       breakout_plan.swing_5m_stop). A refused value reads as log and is named in BRK_STOP5M_ENV_REFUSED. The operator,
       2026-10-14 11:47 ET: "Yes, we have to".
v4.64  2026-10-12  OTV4TEST r273 (BFLY.10) - ENTRY_WINDOWS["GEXPinButterfly"] and ["ATPButterfly"] START 12:00 -> 13:00
       (end 15:00 unchanged); BUTTERFLY_ENTRY_START_ET and GEX_BFLY_EARLIEST_ET follow (derived). The operator, 2026-10-12 12:26 ET: "For TEST repo, I want to reduce the fly window to 1300 or later starting tomorrow"; 12:31 ET: "Yes".
       Mainline made the same move at otv4 r484 (FEE.4). Stated to him first: this box's 7 GEX flies made
       +$4,603 before 13:00 (one +$4,334 at 12:54) - he ruled 13:00 anyway.
v4.63  2026-10-12  OTV4TEST r272 (COMMIT.2 / COMMIT.3) - OT_COMMIT_GATE off|log|trade (UNSET = trade; a live box reads it
      as log; a refused value reads log, named) and OT_CAUTION_SIZE off|log (unset = log; trade refused, named) for
      analysis/commitment.py. The operator, 2026-10-12 11:35 ET: "Yes, do it".
v4.62  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v4.61 2026-10-11  OTV4TEST r268 (DEP.12, mirror of otv4 r478) — HALF_DAY_ENTRY_LEAD_MIN = 90: on a listed early close
      (utils/market_calendar.EARLY_CLOSES) entries_open() closes 90 min before the bell, 11:30 on a 13:00 day. Every
      close-anchored time here (EOD_SCHEDULE and the names derived from it, RTH_CLOSE_ET) keeps its 16:00-bell value and is
      moved to the day's bell by utils/time_utils.close_anchored(). Full days unchanged. The operator, 2026-10-11 16:51 ET:
      "Yes, we want those fixed here too" (told 13:06 ET that the 11:30 floor clips SPX-TEST's Runaway 12:00 and QQQ-TEST's
      Breakout 15:40 on a half day).
v4.60 2026-10-10  OTV4TEST r266 (STOP.1) — OT_RESTING_STOP off|trade (unset = off; a refused value reads off and is named
      in RESTING_STOP_ENV_REFUSED): a fired hard_stop / trail_stop_hit RESTS at its level for RESTING_STOP_WAIT_S (120,
      "120 seconds is fine") unless the mark falls RESTING_STOP_EMERGENCY_FRAC (0.05 of entry, "I can live with a 5%
      emergency stop") under it. PAPER ONLY (execution/resting_stop.py).
v4.59 2026-10-10  OTV4TEST r265 (BRK.8 + BRK.9) — TWO PER-BOX BREAKOUT SWITCHES. (1) OT_BREAKOUT_END "HH:MM" moves ONLY
      Breakout's entry end (09:36 .. 15:40; unset = r187's 10:30; a refused value keeps 10:30 and is named in
      BREAKOUT_END_ENV_REFUSED), the mirror of r189's OT_RUNAWAY_END. (2) OT_BRK_NOPROG off|log|trade (unset = log):
      Breakout's NO-PROGRESS exit (management.breakout_no_progress) - after 2 consecutive CLOSED 1m bars with no new
      favourable extreme, with less than BRK_NOPROG_MIN_R (0.5 R) of progress, the trade is cut (trade) or the cut is
      only recorded (log). A refused value reads as log and is named in BRK_NOPROG_ENV_REFUSED. The operator,
      2026-10-10 13:37 ET: "Yes, to all. Study, fit & apply." EVIDENCE /var/tmp/sat_1010/PREREG_MONDAY.md (N3).
v4.58 2026-10-04  OTV4TEST r249 (PREM.6) — ORCS IS RETIRED: ORCS_ENABLED defaults OFF (OT_ORCS=1 restores it, paper only as before; the plan keeps recording). The operator, 2026-10-04 20:12 ET: "Retire it on this repo."
v4.57 2026-10-04  OTV4TEST r234 (SCALE.1) — CONTRACT_SCALE: ONE NUMBER PER BOX FOR WHAT ITS CONTRACTS COST AGAINST QQQ'S. The operator,
      2026-10-04: "SPX cap, ramp & wing search CANNOT be the same as QQQ. The math doesn't work. It needs to scale with the contract
      price differences"; on the measured proposal: "Perfect." MEASURED (/var/tmp/spx_scale_1004, mainline chain_snapshots, 14 sessions
      09-14..10-02, 09:45/10:00/10:29): SPX/QQQ platform expected move median 7.57 (6.2-9.1), ATM straddle 7.30, the 0.20-delta short
      7.4-7.7; spot 10.44 OVERSTATES it (SPX implied vol is lower). SPX = 7.5, every other instrument 1.0; OT_CONTRACT_SCALE overrides
      (a positive number; anything else is ignored and SAID). ORCS reads it (wing and minimum credit); the box's dollar dials (risk,
      TOP, cap) stay literal dollars set per box. QQQ unchanged.
v4.56 2026-10-03  OTV4TEST r218 (PATH.1) — DATA_DIR and QUOTE_FLOOR are DEFINED. resting_orders imported DATA_DIR and breakout_plan
      read QUOTE_FLOOR by getattr; neither name existed, so both silently took fallbacks (the 10-03 audit, D4).
      DATA_DIR is this file's own data/ directory, spelled here and NOT imported (configure.sh imports config standalone);
      QUOTE_FLOOR = 0.01, the value the fallback produced.
v4.55 2026-10-03  OTV4TEST r216 (HYG.14) — comment only: execution/fill_model.py is deleted (never wired; the operator: "That's
      useless"); the entry-ladder note keeps its rule - paper never books a fill from an inside-the-spread rung.
v4.54 2026-10-03  OTV4TEST r209 (EXIT.4) — BUTTERFLY_ENTRY_CUTOFF_ET GATES NOTHING: the session_guard branch that read
      it could never run and is deleted. Value unchanged (check_one_window_table pins it and the guard's constant).
v4.53 2026-10-03  OTV4TEST r207 (PREM.4) — ORCS RESHAPED BY RULING: delta 0.20, a 3-dollar wing, implied-move floor 1.0. The
      operator: "why the fuck would I risk $1000 for $25???", then "I want the worst day adjusted for $1050, so
      use the delta and wing based on that" and "To achieve an over 80% win rate". ORCS_SHORT_DELTA_MAX 0.15 ->
      0.20; ORCS_WING_PCT (1% of spot) is REPLACED by ORCS_WING_USD = 3.0; ORCS_MIN_IM_MULT 1.25 -> 1.0.
v4.52 2026-10-03  OTV4TEST r206 (PREM.3) — ORCS_LIMIT_IMPROVE and ORCS_REST_MIN are REMOVED. The operator: "we have a ladder
      for entries. THAT has to govern our entry." ORCS no longer prices or rests its own offer; the house credit
      entry does (paper: the mark; live: the entry ladder).
v4.51 2026-10-03  OTV4TEST r204 (PREM.2) — ORCS IS A TRADE; THE SWEEP AND THE TCS ARE RETIRED. The operator, 2026-10-03: "I want
      to paper trade it Monday. Retire the sweep & TCS. Call this new one the opening range credit spread ORCS."
      ENTRY_WINDOWS gains OpeningRangeCreditSpread 09:45-10:30; the r203 OPS_* dials are renamed ORCS_* (values
      unchanged; the two window dials moved into the table); ORCS_ENABLED (OT_ORCS, default ON). SWEEP_CS_ENABLED is
      new and OFF (OT_SWEEP_CS=1 restores the sweep); TREND_CREDIT_ACTIVE now defaults OFF (OT_TCS_ACTIVE=1 restores
      it) and is read by main for the first time.
v4.50 2026-10-03  OTV4TEST r203 (PREM.1) — THE OPENING PREMIUM SPREAD PLAN'S DIALS (OPS_*), PRELIMINARY. A record-only
      plan (strategy/open_premium_plan.py, PLAN_SPEC §41) reads them; no order is placed and no entry window or
      admission rule is added. OT_OPS_PLAN=0 parks the plan. Values come from the 10-03 studies X5-X8.
v4.49 2026-10-03  OTV4TEST r194 (BOX.16, SHARED SHAPE) — OT_LOG_FILE. LOG_FILE honours it; unset it is
      ~/options-trader/bot.log exactly as before. main._setup_logging attaches a file handler to LOG_FILE at
      IMPORT, so every checker that imports main logged into the live bot.log (the 10-03 audit counted about
      4,000 fixture lines this week and could not trust a warning without the sweep times). tools/land.sh
      v1.18 and tools/boot_sweep.py v1.4 set it to each checker's scratch. Approved 2026-09-26 as "r147".
v4.48 2026-10-03  OTV4TEST r193 (CFG.1) — 29 DIALS THE CODE ALREADY READ FROM config ARE NOW DEFINED IN IT. The
      10-03 audit found BRK_* (9), GEX_BFLY_* (5), RUNAWAY_* (9), SWEEP_CS_* (3), HANDOFF_TTL_TICKS,
      HUNT_MAX_LOSS_PCT and ADMISSION_RULES read as getattr(config, name, literal) with no such key here, so
      every one silently took its module's literal. Each is defined once with that same value and its module
      reads config.NAME with no fallback (ADMISSION_RULES alone keeps its getattr: checkers stub config). NO VALUE CHANGES (check_attr_fidelity A4 pins all of them; A3 fails
      any new getattr(config, ...) on a name config does not define). Fork-only block in a shared file.
v4.47 2026-10-03  OTV4TEST r189 (RUNW.1) — OT_RUNAWAY_END: RUNAWAY'S ENTRY END IS A PER-BOX SWITCH. Unset, it is
      r187's (10, 30) exactly. "HH:MM" between 09:36 and the 15:40 entries stop moves the end of
      ENTRY_WINDOWS["RunawayContinuation"], and with it every reader (admission, RUNAWAY_CUTOFF_ET,
      runaway_continuation.CUTOFF_ET, runaway_plan). Anything else is REFUSED and named in
      RUNAWAY_END_ENV_REFUSED, which runaway_plan logs at WARNING - never silently dropped (WA 0.5). The operator,
      2026-10-03, for a standalone SPX-TEST compared against mainline SPX: "Yes" to the switch. MEASURED that
      morning: mainline SPX Runaway made +7,894 of its +11,945 on entries at or after 10:30 (X1), and the 10:29
      cutoff failed for Runaway on 15 unseen symbols (X3). Hunt, Breakout and VOLT keep 10:30.
v4.46 2026-10-03  OTV4TEST r188 (BRK.5) — BRK_RESEARCH_UNTIL 2026-10-03 -> 2026-10-30. Breakout's informers stay
      at "accept any". The operator, 2026-10-03 09:51 ET: "extend the window for it to accept any and on the
      very next session that it TRADES make sure that we're getting the right data. And then prior to our next
      attempt to fit it make sure that it's part of the conversation." MEASURED that morning: the dials were
      never fitted, and depth_thin's reading was None on 2,153 of 2,153 plan_check rows (strategy/breakout_plan
      v1.7 fixes the read), so at the old date 0 of the 89 Breakout fills 09-21..10-02 would have cleared the
      placeholder dials and Breakout would never have planned again. Fork-only constant (Breakout is not a
      mainline strategy) in a file both trees carry.
v4.45 2026-10-02  OTV4TEST r187 (ROSTER.1) — DIRECTIONAL DEBIT ENTRIES STOP AT 10:29 ET. ENTRY_WINDOWS ends
      RunawayContinuation, LiquidityHunt, Breakout and VOLT at (10, 30) (every window end is exclusive, so the
      last entry is 10:29). The operator, 2026-10-02 21:24 ET: "let's impose a 1029 debit cutoff rule, but
      exempts the GEX pin fly". MEASURED (QQQ 09-09..10-02): late entries lost on 7 of 18 days, made money on
      3; the cutoff passed UNSEEN SOFI/AAL at every cutoff 10:15-11:00 (-41.3 -> -15.6 R at 10:30) and QQQ's
      09-28 week (-15,784 -> -10,177); it fails only the strict best-day term on 09-21 (-24%). UNCHANGED: the
      ORBStrategy row (its end also drives the ORB ENGINE's expiry, which Runaway/Breakout/latches read; the
      ORB TRADE is off by switch instead), both butterflies, both credit spreads. Fork-only value change in a
      file both trees carry: mainline keeps its windows (announced to 1-REPORTER).
      AND ATP_BUTTERFLY_ENABLED defaults OFF (OT_ATP_BUTTERFLY=1 restores it). The operator, 2026-10-02 21:39 ET:
      "Turn off the ATP", after reading that both flies buy the same fly on the same pin (GEX 6 trades +5,350,
      ATP 4 trades -327, two ATP losses stacked on pins the pin fly had played). The pin fly is unchanged.
v4.44 2026-09-30  OTV4TEST r179 (BFLY.9) — `ATP_BFLY_PIN_CONC_MIN = 0.15`: THE ATP BUTTERFLY HAS ITS OWN PIN-CONCENTRATION FLOOR. The operator, 2026-09-30, reading the ATP fly HOLD all afternoon on a PINNING tape at the pin: "The ATP fly should be accepting the plan for the EXACT reason GEX pin fly is declining (price too close to pin)", then "Drop the ATP to .19" and, minutes later, "Actually .15 sounds better". The pin (travel) butterfly keeps GEX_BFLY_PIN_CONC_MIN (0.25); only the ATP reads the new key. AND `ATP_BFLY_VWAP_STRICT_EM_FRAC = 0.05`, the ATP's ROUTE B: when route A (PINNING and concentration >= 0.15) fails, a NOT-TRENDING regime qualifies if the pin is within ±0.05 x EM of today's VWAP. The operator, 2026-09-30: "Allow a non-pinning ATP if it qualifies on STRICT VWAP & NOT TRENDING", "Route B for VWAP if A fails", and yes to NEUTRAL and to ±0.05 x EM. ALSO: ENTRY_WINDOWS["ATPButterfly"] 11:30 -> 12:00. The table said 11:30 while the plan used the pin fly's slot and stayed DORMANT until 12:00 (measured 2026-09-30: DORMANT at 11:29:57, first asked 12:00:06), so the table now says what happens; the operator: "12:00 is fine". No entry is gained or lost by it.
v4.43 2026-09-29  OTV4TEST r177 — COMMENT ONLY: v4.42 below calls the strike-ladder fix "STRK.1"; it is LADR.1. STRK.1 was already the 2026-09-21 row (strike selection scaling with the implied move). No value or behaviour changes.
v4.42 2026-09-29  OTV4TEST r175 (SYM.1) — THE TRADEABLE UNIVERSE IS THE TOP 75 OPTIONS NAMES, AND A SYMBOL OFF THE LIST IS REFUSED. The operator, 2026-09-29: "probably the 50 most liquid names ... bump it up to 75. Any list that would include AAL and Sofi would be the right number", then "Yes to all" to: rank by options volume, keep only an ATM spread <= 10%, keep every symbol already listed. MEASURED 2026-09-29 ~13:40 ET on Cboe's public delayed chains (181 candidates, 180 read; /var/tmp/option_liquidity_2026-09-29.jsonl on the reference box): 71 pass the spread filter (SOFI #22, AAL #73 by volume); with SPY/QQQ/IWM/SPX that is 75. 50 are new: STRIKE_INCREMENTS gains each at its MEASURED near-money step (the mode of the listed-strike gaps within ~6% of spot on the nearest expiry, four spot-checked against the raw ladder), PENNY_CLASSES gains the 48 measured penny-quoted (APP and ASML quote on the nickel grid and stay out). Existing entries are NOT re-stepped here: 18 disagree with the real ladder (NVDA/AMZN/AAPL... trade 2.5, SMCI 0.5) and that is STRK.1, the shared fix that reads the ladder from the chain. INSTRUMENT_LISTED is new: a symbol not in STRIKE_INCREMENTS used to get a silent $1 step from .get(INSTRUMENT, 1); main.py and data/candle_feed.py now refuse it at startup. The declared (inert) RETENTION_DAYS copy moves 5m 10 -> 30 and 15m 20 -> 30 with warehouse/retention_purge.py, for the 30-day first-boot backfill.
v4.41 2026-09-27  OTV4TEST r162 (CAP.1) — DAILY_LOSS_LIMIT_USD is the DAILY CATASTROPHIC LOSS CAP, and it RE-ARMS. Value and key (OT_DAILY_LOSS_LIMIT) unchanged; the comment now says what risk_manager v4.8 does: no new entries while realized net is at or beyond -limit, entries re-open once closes bring it back under.
v4.40 2026-09-27  OTV4TEST r161 (SIZE.2) — ONE MIN, ONE MAX, AND A SCALING SWITCH PER TRADE. The operator, 2026-09-27: "Risk per trade/Ramp Start (MIN)", "Merge it. that was always the intent." ORB_RISK_USD no longer reads OT_ORB_RISK_USD: it IS RISK_PER_TRADE_USD, and a unit still carrying the old key is named at startup (ORB_RISK_ENV_IGNORED) rather than silently obeyed or silently dropped. SCALE_ORB / SCALE_BREAKOUT / SCALE_VOLT (OT_SCALE_ORB / OT_SCALE_BREAKOUT / OT_SCALE_VOLT, "1" = on, default on): OFF sizes that strategy FLAT on the budget rule (about RISK_PER_TRADE_USD of premium) while its structure stop, exits and the r93 noise floor stay exactly as they are - "retain the original structure stop ... but just use a flat dollar amount for the entry".
v4.39 2026-09-26  OTV4TEST r149 (EOD.1) — THE END OF DAY IS ONE TABLE, AND THE OPERATOR RESET IT. `EOD_SCHEDULE`: entries stop 15:40; positions with ASSIGNMENT RISK (a short leg) post RESTING best-case closes at 15:45; everything else LADDERS from 15:50; anything unfilled CROSSES at 15:55. Directional debit entries run ALL DAY to 15:40 (ORB, Runaway, Hunt, Breakout, VOLT; was 11:30). HARD_CLOSE_ET, FLATTEN_WINDOW_OPEN_ET, VERTICAL_HOLD_TO_ET and DEBIT_DIRECTIONAL_CUTOFF_ET now DERIVE from it; the debit cutoff's OT_DEBIT_CUTOFF_ET override is REMOVED (a second window source).
v4.38 2026-09-26  OTV4TEST r148 (WIN.1) — ONE ENTRY-WINDOW TABLE. `ENTRY_WINDOWS` is the single source of every strategy's entry window; the admission table and every plan read it, and each older name (ORB_NO_ENTRY_AFTER_ET, RUNAWAY_CUTOFF_ET, VOLT_WINDOW_*, TCS_*, CREDIT_*, CONDOR_ENTRY_CUTOFF_ET, SWEEP_CS_*_FORK, BUTTERFLY_ENTRY_START_ET) is DERIVED from it. HUNT_CUTOFF_ET, BREAKOUT_LATEST_ET and GEX_BFLY_LATEST_ET are added: three strategies read those names with a literal fallback and the names never existed. Every value is UNCHANGED (tests/check_one_window_table.py pins all 47 resolved values).
v4.37 2026-09-26  OTV4TEST r146 — OT_INSTRUMENT HAS NO "QQQ" FALLBACK: unset reads "UNSET".
      The operator: "defaulting the QQQ is not the answer" (2026-09-26). A process without the variable
      was silently QQQ - right on this box by luck, wrong on every other (r144's
      fixture events, SOFI's self-close labels). The bot and the feed now REFUSE
      to start on UNSET; standalone tools resolve the box's instrument through
      utils/instrument.box_instrument(). Both of this box's units carry
      OT_INSTRUMENT=QQQ (the operator's read, 2026-09-26).
v4.36 2026-09-25  OTV4TEST r141 — NOISE_FLOOR_MIN_BARS = 3. The r93 floor needed 10
      one-minute bars and the frame it reads is scoped to TODAY'S session, so it
      stood down from 09:35 to ~09:40 EVERY day - the window ORB and Breakout fire in.
      On 2026-09-25 it let 96-100 contracts ride stops of 0.14/0.21/0.31 against a
      session floor of ~0.43 (-$3,170). Operator: "Yes" (2026-09-25).
v4.35 2026-09-25  OTV4TEST r137 — SOFI AND AAL ARE TRADEABLE SYMBOLS. Operator: "I need
      AAL & SOFI to be selectable from configure.sh" - for the paper boxes that
      will test live mechanics on cheap, weekly-option names (FLEET.1). Both join
      STRIKE_INCREMENTS (configure.sh's tradeable list IS its keys) at 0.5 and
      PENNY_CLASSES, each MEASURED from Cboe's public delayed chain 2026-09-24:
      SOFI (16.67) and AAL (13.38) list $0.50 strikes on every strike within $3 of
      spot on the 09-25 and 10-02 weeklies, and 81% / 74% of their option quotes
      under $3 sit off the nickel grid (0.01, 0.02, 0.03 ...), i.e. penny class.
      The FIRST fractional increment in this table - utils/math_utils.py v4.1
      stops truncating it.
v4.34 2026-09-24  OTV4TEST r131 — the "VOLT SIZES OFF RISK_PER_TRADE_USD, NOT ORB_BUDGET_USD"
      note is SUPERSEDED BY RULING and kept, struck, as history (r240 precedent).
      Operator, 2026-09-24: *"VOLT needs to adopt the breakout sizing model"*,
      then option 2, the 1-R curve. VOLT now sizes through RiskManager
      _size_geometry off its signal candle (main._geometry_inputs); VOLT_BUDGET_USD
      remains only as the plan's provisional feasibility size. No value changes here.
v4.33 2026-09-23  OTV4TEST r108 — the declared retention policy's "1m" goes
      5 -> 60, equal to "1h". The level book builds levels from the hourly tape
      and judges the operator's BREACHED rule on 1m, so 1m must be kept as long
      as 1h. warehouse/retention_purge.py v1.7 carries the measurement. Comment
      block only; nothing here is read at runtime.
v4.32 2026-09-22  OTV4TEST r97 — PIN_PROXIMITY_ACTIVE / _MIN_FRAC. Do not fire a
      DIRECTIONAL DEBIT onto a pin you are standing on. Dealers long gamma sell
      rallies and buy dips, so price mean-reverts toward the pin and a debit
      fired near it needs follow-through from the regime built to suppress it.
      MEASURED on 36 directional fires: winners a median 0.414 EM from the pin,
      losers 0.342; refusing below 0.32 turns the day from -$904 to +$4,606.
      Section 36 SELECTION, env-switchable, shipped REFUSING by the operator's
      ruling - section 31's log-only default overridden deliberately.
v4.31 2026-09-22  OTV4TEST r93 — NOISE_FLOOR_BAR_MULT / _LOOKBACK_BARS. The 1-R rule
      normalises the SIZE of a loss and is blind to its FREQUENCY, so a stop
      inside one ordinary bar buys MAXIMUM size on a coin flip. Measured
      2026-09-22 10:14-10:25 ET: five Breakouts with stops of 0.075/0.050/
      0.190/0.225/0.010 against a median 1m range of 0.4188, ~$10,000 each,
      -$3,089. 0.5x is argued from the mechanism; the day's P&L peak was 0.60x
      and is deliberately NOT used (n=11, section 12).
v4.30  2026-09-21  OTV4TEST r82 — ONE `DELTA_PAR`; VOLT and BREAKOUT both
      derive from it, an hour after r81 landed on four literals for one credit
      window. BREAKOUT_DELTA_PAR added: par delta replaces its +100% target.
v4.29  2026-09-21  OTV4TEST r81 (LATE.2) — r71'S 15:40 CREDIT WINDOW NEVER
      REACHED THE CODE. The admission table moved and FOUR literals stayed at
      14:00, and THE PLAN RUNS BEFORE ADMISSION, so the credit plans went
      dormant at 14:00 for a full session while the table said 15:40. Every
      credit END now DERIVES from `CREDIT_ENTRY_END_ET`; two `*_FORK` keys the
      fork's plans read were added, having never existed — the r317 defect
      reintroduced under new names.
v4.28  2026-09-21  OTV4TEST r79 (EXT.1) — VOLT_DELTA_PAR, VOLT_EXT_STOCKLIKE
      and VOLT_STOCKLIKE_ATR_MULT. Operator, live on a call at +468% holding
      four cents of extrinsic: *"When Delta reaches PAR, we need to get the
      fuck out."* At par delta the position is stock with an expiry and the
      trail's give-back is dollar-for-dollar with the underlying.
v4.27  2026-09-21  OTV4TEST r74 — VOLT's entry frame drops to ONE MINUTE and
      its warm-up to THREE bars, so it fires from 09:37 instead of 10:15. The
      operator's spec: *"It should be able to fire immediately… move on the
      first sense that volume is expanding."* The exit frame stays five minutes.
v4.26  2026-09-20  OTV4TEST r72 — the VOLT_* block: the control arm's declared
      priors in ONE place, read by both volt_plan.py and exit_engine.py.
v4.25  2026-09-20  OTV4TEST r71 (LATE.1) — VERTICAL_HOLD_TO_ET 15:45 -> 15:50
      by the operator's ruling, so credit verticals entered in the new 15:40
      window have a hold time at all. The INHERITED DOCTRINE entry below is
      amended in place rather than left reading the old bound, because §32
      makes that block the thing you read before changing this constant.
      ⚠️ THE EXPOSURE IS A FAILED FLATTEN, NOT A HELD POSITION — both 15:45
      and 15:50 exit before the 16:00 expiry. What is spent is the margin
      between the close attempt and the last reconcile sweep at 15:57.
v4.24  2026-09-19  OTV4TEST r55 — BRK_RESEARCH_UNTIL. One date is the whole
      switch: until it passes, every Breakout informer's acceptance reads "any"
      — each is still a DECLARED TRIGGER the plan must clear, and the BAND is
      what is wide. After it, each dial takes the number the data gives.
      ⚠️ FAILS CLOSED: an unreadable or absent date means the fitted dials bind.
      🔴 AND NO DIAL IS PINNED HERE. An earlier cut set BRK_R_FLOOR=0.0 to force
      acceptance, which would have left Breakout with NO R floor FOREVER — the
      research posture leaking into the fitted value it exists to restore. The
      window widens acceptance; it never edits a dial.
v4.23  2026-09-18  OTV4TEST r44 — THREE CONSTANTS RE-ANCHORED TO THE RIGHT
      QUANTITY. ORB_RISK_USD (the geometry rule normalised to the OPENING RANGE,
      not the budget: every stop distance on a 0.97 range risked $26-32, 3% of a
      $1,050 budget). THESIS_BAND_* (a level asserted to the cent; a 7c close
      overshoot killed a hunt one bar before a 2.68pt move). TRAIL_GAIN_LOCK
      (a floor that was a fraction of PREMIUM and could sit BELOW ENTRY).
v4.22  2026-09-14  OTV4TEST r26 — THE ATP BUTTERFLY'S KEYS (BFLY.6, PLAN_SPEC §39):
       `ATP_BUTTERFLY_ENABLED` (OT_ATP_BUTTERFLY=0 parks it), and two declared
       priors — `ATP_BFLY_AT_PIN_EM_FRAC = 0.30` (spot within 0.30 x EM of the pin:
       the complement of the travel fly's 0.30-1.00 reach) and
       `ATP_BFLY_SETTLED_BARS = 15` (closed 1m bars all inside that band).
v4.21  2026-09-13  OTV4TEST r25 — `GEX_BFLY_VWAP_BAND_EM_FRAC = 0.10` (BFLY.5): a pin within
       ±0.10 x EM of today's VWAP meets the butterfly's concentration condition
       without the floor. Operator: "W/in 20% of the expected move, expressed as
       10% above, 10% below."
v4.20  2026-09-13  OTV4TEST r24 — `BUTTERFLY_STOP_LOSS_PCT` 0.25 -> 0.40, THE OPERATOR'S
       RULING. A fly's maximum loss is already its debit, and on 2026-09-11 the
       25% floor came within 2 cents of cutting a fly that was worth +182% at
       the 15:45 flatten (713/715/717P, entry 0.39, floor 0.29, worst 0.31 two
       minutes in — mostly the three-leg bid/ask). Operator: "Widen it to 40%."
       One key, read by the butterfly's signal AND by its wing-search
       feasibility check, so the entry gate and the exit agree.
v4.19  2026-09-13  OTV4TEST r18 — TWO KEYS THAT WERE BEING READ AND WERE NEVER
       DEFINED, PLUS A LABEL ON THE ORPHAN BESIDE THEM (CFG.1).
       `derived/levels.py` read `getattr(_cfg, "SWEEP_CS_MAX_REJECTION_PCT",
       0.0025)` and THAT KEY DID NOT EXIST HERE, so every pierce band on the box
       ran on the literal default — while `SWEEP_MIN_REJECTION_PCT = 0.003` sat
       in this file with ZERO READERS. The predecessor shipped the same shape at
       15x; ours was 1.20x, which is exactly why nobody saw it. Both keys are
       DEFINED AT THE VALUE THAT WAS ALREADY RUNNING, so this changes no
       behaviour and makes the knobs real; the orphan is labelled in place
       rather than deleted (the r231 precedent: a stated prior, not a policy).
       `LEVEL_ACCEPT_CLOSES` is new and carries the operator's ruling — closed
       1m bars beyond a level before it retires ACCEPTED_THROUGH, so acceptance
       can be loosened to 1 without a redeploy.
v4.18  2026-09-10  OTV4TEST r13 — `DB_PATH` honours `OT_TRADES_DB` so the lander's CHECK
      phase can point every checker at a scratch trades.db (defect #12: a test
      fixture landed as a live open position on the QQQ TEST box).
v4.17  2026-09-08  OTV4TEST r2 — `ORB_MAX_RETEST_BARS` REMOVED with the stale
      re-arm it fed (orb_engine v4.12, operator's ruling 2026-09-08: while
      price is outside the range only a retest, a runaway or a close inside
      can come next; a timeout is a fourth outcome nobody specified).
v4.16  2026-09-08  r317 — `SWEEP_CS_LATEST_ET` EXISTS. The sweep read its END
      from `getattr(config, "SWEEP_CS_LATEST_ET", "14:00")` and that key was
      DEFINED NOWHERE, so the default was the only source — the third time
      this exact shape has appeared in this file (`SWEEP_CS_EARLIEST_ET` kept
      11:11 while the other three credit paths moved to 11:31, r146;
      `GEX_BFLY_EARLIEST_ET` opened an hour before the noon rule, r142). Both
      of those were fixed on the START side and the END side was never swept.
      It bites the day the credit cutoff moves: the sweep silently stays at
      14:00 while everything else follows. New `CREDIT_ENTRY_END_ET` is the
      one number, `SWEEP_CS_LATEST_ET` is derived from it, and
      `check_entry_windows` W8 asserts the four credit paths agree on the END
      exactly as W1 does on the START.
v4.15  2026-09-05  r269 — WHY THIS REPO EXISTS IS NOW IN THE DOCTRINE BLOCK.
      The v3 direction-skill measurement (715 trades, 44.9% correct side, CI
      entirely below a coin flip) and the P&L attribution that followed it were
      lifted out of `docs/AUDIT_HANDOFF.md`, which was DELETED along with seven
      sibling thread contracts — 89 KB of spent handoffs and one durable fact.
      ⚠️ IT DID NOT GO TO THE BACKLOG: that file is DEFERRED WORK, and this is
      a settled measurement. It did not go to an archive either, because an
      archive is where documents go to stop being read. It is in the block
      WA §32 requires be read before this file is edited.

v4.14  2026-09-04  r238 — TCS REBUILT. `TCS_ENTRY_END_ET` (14,0) spec'd
      not inherited; `TCS_R_FLOOR_EXPIRY` and `TCS_STOP_PCT_OF_CREDIT` added.
v4.13 2026-09-04  r237 — 🔴 TCS_ENTRY_END_ET SET OUT OF REACH: (14, 0) -> (0, 0).
      Operator, mid-session 2026-09-04, after UNH fired three times in three
      minutes on identical strikes: *"set the impossible variable and comment
      it in the changelog. We're doing a rewrite tomorrow anyways."*
      🔑 WHY THIS CONSTANT: it is TCS-ONLY, and it fires at the FIRST gate so
      nothing downstream is even priced. A quality bar would also have stopped
      it and would have LIED about why — `wing_r_best FAIL` forever, and a
      future reader losing a session to "why does UNH never clear R".
      `TCS_START_ET` was not touched because `check_entry_windows` pins it
      equal to `CREDIT_ENTRY_START_ET`, so moving it would have moved the
      SWEEP.
      ⚠️ It cleared the bar HONESTLY under r234's stop basis — UNH 398/402 for
      $0.84 is credit/width 21.0% against a 13.04% bar. The gate was right.
      ⚠️ Belt and braces with `OT_TCS_ACTIVE=0`, already in a systemd drop-in
      on all 15 boxes; the env flag dies with the file, this survives in the
      repo. BACKLOG TCS.7 holds the rewrite.
v4.12  2026-08-31  r201 — ORB_BUDGET_USD: the ceiling on what one ORB setup
      may deploy, defaulting to RISK_PER_TRADE_USD and overridable by
      OT_ORB_BUDGET_USD. ORB was the only strategy with no budget at all — an
      SPX setup opened $34,750 of premium on 2026-08-31. Applies in paper as
      well as live, because an unconstrained paper sizer overstates every P&L
      number against live.
v4.10  2026-08-30  r193 — ORB_NO_ENTRY_AFTER_ET 11:00 -> 11:30. The window
      gates PLACING an ORB order, not an offer already resting. 🔑 It now
      EQUALS DEBIT_DIRECTIONAL_CUTOFF_ET, deliberately: both tests are `>=`
      and ORB declares long_debit, so entries run to 11:29:59 and the debit
      block takes over at 11:30:00 with no gap and no overlap. ⚠️ The
      constant also expires the ORB engine from any state and feeds the
      re-arm check, so this buys 30 more minutes of breaks and retests, not
      only a later last entry. See the note at the constant itself.
v4.9  2026-08-28  r175: TCS_DRIFT_HORIZON_BARS (24 x 5m) — the bounded horizon
      pop_drift may credit the session's measured drift over; baseline prior,
      stated, env-tunable.
v4.8  2026-08-27  r169: BUTTERFLY_TP_PCT and BUTTERFLY_MAX_HOLD_MIN retired from
      the decision path — the butterfly rides to the 15:45 flatten or the 25%
      floor.
v4.7  2026-08-27  r168: RUNAWAY_MAX_LOSS_PCT 0.20 — the runaway's floor is a
      20% premium loss (decay or adverse move), no underlying stop; the ORB
      structure stop is ORB's alone; credit spreads keep 15%.
v4.6  2026-08-26  r147: GEX_BUTTERFLY_ENABLED (default ON, OT_GEX_BUTTERFLY=0
      parks it) and GEX_BFLY_WING_EM_FRAC ⟨PRIOR⟩ 0.25 — the pin butterfly is
      unparked by operator instruction; wing width as a fraction of the
      expected move, floor one strike increment.
v4.5  2026-08-24  r101: ENTRY_OPEN_ET (09:35) — nothing OPENS before the opening
      range exists. Operator directive, dated, with its reason recorded beside
      the GLOBAL_NO_ENTRY_ET tombstone so the two are distinguishable.
v4.4  2026-08-25  LOCAL RETENTION POLICY DECLARED, NOT ENFORCED. Per-tenor day
    counts written down in config BEFORE any purge exists to read them, and
    COMMENTED OUT so nothing acts on them yet. The binding consumer is
    EMA_ANCHOR=200, which inverts the intuition: every tenor needs the same
    BARS, so 1m needs 5 days and 1h needs 60. A flat row cap — which is what
    candle_feed.PRUNE_KEEP_ROWS is — cannot express that. Pruning stays OFF.

v4.3  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

v4.3  2026-08-22  CONDOR_PF_TIMEFRAME -> "1h" per operator ruling. See the
    site comment; supersedes the daily anchor.

v4.2  2026-08-21  r60: GLOBAL_NO_ENTRY_ET deleted (unauthorized 14:00
      all-strategy cutoff - see the block at its former site); TCS_ENTRY_END_ET
      added as an inert, flagged placeholder for the parked TC.6.
Every constant, threshold and env override.

v4.1  2026-08-20  AUDIT F2: TREND_CREDIT_ACTIVE default OFF - the sixth
      strategy traded live on the 34.2%-measured trend vote while its own
      doctrine said NOT DISPATCHED. See the block at the constant.
v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.

🔴 WHY THIS REPO EXISTS, AND IT IS A MEASUREMENT, NOT A PREFERENCE.
v3's central premise was measured FALSE. `tests/direction_skill.py`,
715 closed directional trades over 16 sessions: the regime classifier
picked the correct SIDE on 44.9%, 95% CI [41.3%, 48.6%] - the interval
sits ENTIRELY BELOW A COIN FLIP. Puts were 34.2%. The strategy most
dependent on it lost $5,872 across 660 trades.
What made money was REGIME-INDEPENDENT: `orb_trail_stop` 96% / 85 trades
/ +$30,696, worst case -$16. What lost it was the floors and BOS:
`max_loss_floor` 76 trades / -$28,179, and `bos_exit` 217 trades /
-$7,085 carrying the single largest loss in the book.
🔑 THE THESIS THAT REPLACED IT: entries decided by STRUCTURE, not by
labels; exits kept because they were MEASURED; every threshold traceable
to a number.
⚠️ LIFTED HERE 2026-09-05 (r269) FROM `docs/AUDIT_HANDOFF.md`, WHICH WAS
DELETED. It sat in an 89 KB set of spent thread contracts nobody reads,
and it is the one fact in them that must not be re-derived: without it,
a future reader rebuilds the regime classifier because it sounds
reasonable. It belongs in the block WA 32 requires be read before this
file is edited - not in a backlog, which is DEFERRED WORK, and not in an
archive, which is a place documents go to stop being read.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

config.py — options_trader v4.20
# L1.9a: TIMEFRAMES["1h"] 50 -> 80 candles. `trend_engine`
#   refuses to vote below EMA_SLOW+5 = 55 bars and this asked for exactly 50,
#   so the 1h trend vote COULD NEVER FIRE - and 1h carries 0.20 weight, second
#   only to 15m. Its "declared weight contributes nothing" warning has been
#   firing on every box since the engine shipped and was read as transient.
#   THIS IS WHY L1.6/L1.7 WERE STUCK: the TRENDING row needs RANGING vetoed
#   through a dominant session, and a permanently missing structure vote
#   depresses TRENDING and inflates RANGING. TSLA 08-04 had 99% dominance with
#   RANGING still scoring 64% of ticks. 26 TREND sessions labeled, row still
#   open. The roadmap called it "habit, not code". It was code.
#   80 not 55: the minimum is a cliff, not a target. Store holds ~112 RTH 1h
#   bars (16d x ~7/day) and pruning is OFF.
#   BLAST RADIUS: df_1h also feeds structure_analyzer (swings + S/R), the
#   pitchfork, entry_snapshot and the named-level frame. A POPULATION BOUNDARY.
OPERATOR DIRECTION, mirrored from options_trader_smc so
        the two arms stay comparable: (1) MAX_LOSS_PCT 0.40 -> 0.25, which
        tightens `stop_hit` (sweep), `hard_stop` (ORB) and the ADOPTED stops
        via ADOPTED_STOP_PCT. Butterfly (own 0.25), condor
        (CONDOR_STOP_LOSS_PCT) and continuation (0.15) never read this
        constant and are unchanged. (2) ORB_BLOCK_RANGING — ORB no longer
        fires under RANGING.
TCS_COOLDOWN_MIN retired to 0 (TC.6 no longer reads it);
        TCS_MIN_CREDIT_PCT_WIDTH superseded by the joint EV test.
TCS_LOSS_GIVEN_BREACH: the credit and POP floors are
        now ONE joint EV test rather than two independent ones.
TC.6 HOTFIX: TCS_START_ET (11:00), TCS_MIN_CREDIT_PCT_WIDTH
        (0.10), TCS_MIN_CREDIT_NICKEL_MULT (4.0), TCS_COOLDOWN_MIN (30). It
        rapid-fired the fleet selling $0.06 credits on $5 wides at 10:02 ET.
TREND_CREDIT_ACTIVE. TC.6 was the only new firing
        strategy with no env kill switch.
ENTRY_LIMIT_LADDER [0.50, 0.25, 0.00] @ 15s.
        DEFAULTS OFF (ENTRY_LADDER_ACTIVE=0) — the pricing primitive and the
        fill model land together, but nothing changes behaviour until the fill
        model is proven against live quotes.
PENNY_CLASSES + PRICE_INCREMENT_BOUNDARY. Option quote
        increments are class- AND level-dependent; `round(px, 2)` posts invalid
        limits on nickel/dime classes.
VERTICAL_HOLD_TO_ET (15:45 -> 15:50, OTV4TEST r71).
        Credit verticals are exempt from the 15:40 flatten ladder; debit
        positions keep it, because the mark-limit phase is what stops every
        EOD exit paying the full spread.
        🔴 THE 15:45 IN THIS ENTRY IS SUPERSEDED — struck, not deleted (r240).
        The operator raised the credit hold to 15:50 on 2026-09-20 to reach
        the late institutional moves. This block is what WA §32 requires be
        read BEFORE a bound is changed, so it is the one place that must not
        still say 15:45 after the bound moved. THE EXEMPTION IS WHAT THIS
        ENTRY IS ABOUT AND THE EXEMPTION IS UNCHANGED — only its end moved.
CONDOR_RATCHET_STANDALONE_ONLY. The ratchet closed
        UNTESTED legs on a reversal; scoped to standalone only.
CONDOR_MAX_QUOTE_WIDTH (0.25 of mid). A ranking never
        refuses; a floor does.
CONDOR_MIN_POP / CONDOR_POP_BAR_MIN. Probability-of-profit
        floor on every short leg, defaulting to 0.70 — the BOTTOM of the
        operator's 70-80%% band, because he asked explicitly not to be
        restrictive on a trade he already knows is risky.
CONDOR PITCHFORK ANCHOR (PF.5). CONDOR_PITCHFORK_ANCHOR /
        CONDOR_REQUIRE_FORK / CONDOR_PF_TIMEFRAME / CONDOR_PF_FLAT_SLOPE.
        The pitchfork has been BUILT AND LIVE as a weight-0 observer since
        2026-08-12 with exactly ONE call site (main.py:2091, `_pf_snap`) and
        NOTHING has ever read the rails back. This is its first consumer — the
        one the white paper pre-registered, because strike placement produces a
        CREDIT that is directly comparable on identical tape.
        DAILY fork by operator ruling. A daily fork is invalidated only by DAILY
        closes, so an intraday session cannot kill it; the hourly one has a
        measured p50 lifetime of 5 bars plus a k=3 confirmation lag and would
        re-anchor mid-position. `CONDOR_PF_FLAT_SLOPE` exists because a SIGN is
        not a SLOPE — a fork drifting 0.001%% a bar is noise, and ordering legs
        off its sign would be reading a coin flip as structure.
CONTINUATION_STOP_LOSS_PCT default 0.25 -> 0.15. THE REPO
        DEFAULT IS THE FLEET LEVER, not the env var: every box receives
        config.py through git pull + bake, so this reaches all 15 on the bake
        already scheduled — no systemd edit, no rotate_tokens change (its FIELDS
        table is hardcoded to seven credentials and has no arbitrary-var path),
        no extra restart. `OT_CONT_STOP_PCT` remains the PER-BOX OVERRIDE, which
        is what a modular fleet wants. It is also the only path that
        participates in the version discipline — a systemd `Environment=` line
        is invisible to check_versions, absent from the changelog and outside
        git entirely.
        EVIDENCE: excursion_report floor sweep, `max_loss_floor /
        ContinuationStrategy`, n=66 across 9 sessions at a **0%% win rate** — a
        15%% floor stops all 66 with **ZERO WINNERS CUT**, NET DELTA +8.85 units
        of entry premium against +2.25 at the current 25%%. Meets the
        pre-registered cheapest-threshold-catching-zero-winners rule rather than
        an in-sample argmax.
        ⚠️ WHAT THIS COHORT IS, and why tightening it is not the same as
        tightening a thesis stop: these are BY DEFINITION the trades where NO
        insurance_stop. The thesis was still technically intact and the premium
        died anyway. Zero winners cut over 9 sessions is evidence it did not
        cost anything; it is not proof that it cannot.
DEBIT_DIRECTIONAL_CUTOFF_ET / _STRATEGIES / DEBIT_BLOCK_ACTIVE
        for main v6.2's afternoon debit block. Env: OT_DEBIT_CUTOFF_ET ("HH:MM")
        and OT_DEBIT_BLOCK_ACTIVE, so the hour moves and the rule dies without a
        deploy. ⚠️ ONE DEFINITION ONLY — a parallel AFTERNOON_NO_DEBIT_* block
        was drafted and removed before shipping; two names for one rule, with
        the later assignment silently winning, is the exact failure class the
        version discipline exists to catch.
SWP.2 + CNT.3, the two Tier-1 tuning priors.
        SWEEP_SETUP_FLOOR_SHORT (default 0.20) separates short sweeps from
        longs — three measures agree and the PLTR mechanism backs it, but n=6
        and a 0.20 floor against a ~0.265 score ceiling is a NEAR-DISABLE, not
        a dial. CONT_HANDOFF_BLOCK_COMPRESSION stops the runaway handoff firing
        under COMPRESSION (39 trades, 28% WR, and the worst never-favourable
        cell at 80%) — a runaway asserts expansion while the label asserts
        coiling.
CNT.2: CONT_INSURANCE_STOP (OT_CONT_INSURANCE, default on).
        Arms the already-stamped `underlying_stop` as a structural early
        invalidator for continuation, ONLY while BOSTracker.protected_level is
        None — i.e. only in the window BOS cannot cover — then hands off.
        Exits tag `insurance_stop`.
CNT.1: CONT_BREAKOUT_DIRECTION + CONT_BREAKOUT_MIN_ADX.
        Standalone continuation may now fire under BREAKOUT_VOLATILE, taking
        direction from the trend engine's `overall_direction` instead of from
        the label (which carries none). Gated on ADX rather than on
        floor is skipped and BREAKOUT's conviction is not the trend's. Tagged
        `trend_continuation_breakout` so it scores separately.
SWP.1: SWEEP_SETUP_FLOOR (OT_SWEEP_SETUP_FLOOR, default
        _sweep SETUP SCORE. The label wins 0.4% of live ticks and is exactly
        zero on 96%, so the trade was effectively off. A PRIOR for the
        collection phase, to be tightened on live fires.
15m FETCH DEPTH 50 -> 150, waking a vote that has never
        fired. trend_engine._analyze_single bails to NEUTRAL below EMA_SLOW+5=55
        bars, and 15m fetched 50 — so the 0.30 direction weight v3.1 moved ONTO
        15m on 07-16 (to route around starved 1d/1h) was itself dead on arrival.
        Only 5m (100 bars) has ever been able to vote.
        WHY 150 AND NOT 60: clearing 55 wakes the vote but not usefully. The
        engine re-seeds the EMA on whatever tail it is handed, so measured
        against a fully-warm EMA-50 the error is 69% of a 0.30 bar at 55 bars and
        49% at 60 — a confident vote on a number dominated by its seed, which is
        worse than an honest NEUTRAL. At 80 bars the error is 2.5%, at 150 it is
        0.3%. 150 15m bars is ~5.8 sessions.
        COSTS NOTHING IN DATA: candle_feed prunes to max(need,60)*PRUNE_FACTOR,
        so the store already retained 240 15m bars — only the fetch cap hid them.
        Raising need to 150 raises retention to 600 automatically.
        1h DELIBERATELY LEFT AT 50 (asleep). Operator's call: the market responds
        more to developments since the close than to the prior session's range,
        which is a reference point rather than a discriminator. A live 1h vote in
        the morning is dominated by the PRIOR session and would oppose the
        opening drive, suppressing TRENDING in exactly the 09:30-10:40 window
        under study. 15m carries more weight and has no such lag pathology.
        WATCH ON FIRST BAKE: TastyTrade's backfill reach is limited and the exact
        cutoff is unknown, so a cold store may not be served 150 immediately. It
        accumulates ~26 15m bars/session and the vote stays NEUTRAL until it
        fills — no worse than today. trend_engine v3.3's STARVED warning reports
        the real per-box depth from the first RTH session.
SWEEP STRIKE FLOOR. SWEEP_DELTA_STRONG 0.08 -> 0.12,
        paired unchanged with SWEEP_DELTA_WEAK 0.30. The inverse-delta
        scaling in strategy/sweep_reversal_strategy.py:_sweep_target_delta
        maps max conviction to the STRONG endpoint, so the highest-conviction
        sweeps were buying the FURTHEST-OTM contracts. On 2026-07-27 a 0.62
        conviction resolved to a 0.16 delta and bought a PLTR $122 put ~6%
        OTM, where gamma could not reach it inside the holding window. The
        endpoints now read: max conviction -> 0.12 delta (leveraged but
        REACHABLE), low conviction -> 0.30 (near-ATM), linear between.
        SEPARATE DEFECT, SEPARATE FIX: the same trade also had a bad ENTRY
        bundled — bundling them would make post-freeze sweep P&L
        unattributable between strike selection and entry quality.
PAPER FRICTION UNIFIED (audit defect T). Default
        PAPER_FILL_SLIPPAGE_PCT 0.01 -> 0.0, and the knob is now applied by
        ONE authority (execution/limit_ladder) across every paper path —
        single, butterfly, condor leg, and rolled vertical. Rationale: under
        the mark-limit policy (limit_ladder v1.2) live posts AT the mark and
        either fills there or does not fill, so a markup made paper
        PESSIMISTIC on price while still optimistic on fill rate. Booking the
        mark everywhere is the honest default; the residual paper->live gap is
        no-fill risk. The knob survives as a UNIFORM stress lever: set
        OT_PAPER_SLIPPAGE_PCT to the fill quality measured in the live
        shakedown and every paper path degrades together.
        Also folds in the un-bumped changes that shipped under the stale v3.3
        header (audit defect U): FLATTEN_WINDOW_OPEN_ET (15,40) 2026-07-22,
        CONDOR_TRIGGER_APPROACH 2026-07-17, runner-refinement knobs v2.0.
CUTOFF DISAMBIGUATION (defect H). Two constants named so
        similarly they were confused for one rule are now named for their scope,
        and the global cutoff is no longer hardcoded outside config.
        (a) NO_ENTRY_AFTER_ET -> ORB_NO_ENTRY_AFTER_ET. Unchanged at (11, 0).
            It is, and always was, the ORB-scoped cutoff (orb_engine v3.6) and
            the arm condition for sweep reversal (sweep_reversal_strategy v3.1).
        (b) NEW: GLOBAL_NO_ENTRY_ET = (14, 0) — the global 0DTE entry cutoff for
            ALL strategies. utils/time_utils v3.1 now READS this instead of
            hardcoding dtime(14, 0), so config is finally the single source of
            truth for both cutoffs.
        NOT a behaviour change: both cutoffs keep their exact prior values.
v1.0 — original release
remove Twilio, fix SWEEP_TARGET_DELTA to 0.08,
        remove Grade C, add BUTTERFLY_ENTRY_CUTOFF_ET
butterfly overhaul: fixed wings by instrument,
        GEX pin proximity gate (1x expected move), noon-2PM entry window,
        one-per-session limit, TP reduced to 20%
narrow SPX condor wings 25->5 so each vertical is
        affordable (max loss ~$235/contract), enabling half-budget-per-side
        condor sizing.
add DAILY_LOSS_LIMIT_USD (default = per-trade risk): halts
        new entries when the day's NET P&L is down by that amount.
add single-name instruments (NFLX/META/MU/MSFT/TSLA/AAPL/
        NVDA/SMCI/ORCL) as DIRECTIONAL-ONLY: ORB + sweep only, no condor/
        butterfly. Widens paper-trading coverage for data collection.
expand the tradeable universe to the full screener list.
live fill-confirmation knobs (LIVE_FILL_*, v3.5) and
        reconcile cadence (BROKER_RECONCILE_INTERVAL_MIN, v3.6); and
        BROKER_RECONCILE_ENABLED now defaults to the trading mode (LIVE=on,
        PAPER=off) so going live via configure.sh auto-enables reconciliation —
        explicit OT_BROKER_RECONCILE=True/False still overrides.
RUNNER REFINEMENTS (all env-tunable): MAX_LOSS_PCT
        25%→40% for directionals (butterfly pinned at 25% via
        BUTTERFLY_STOP_LOSS_PCT); USE_5M_FVG_TRAIL (5-minute FVGs anchor
        trails); FVG_FLOOR_MAX_LOCK_PCT=0.90 clamp; POST_TARGET_TRAIL_LOCK_PCT
        0.85→0.75 (leash no longer inverts past target);
        SWEEP_POST_TARGET_TRAIL=True (sweep runners trail past +100% instead
        of the hard TP).
LIVE_ENTRY_DEADLINE_SECONDS (entry fill-confirmation
        window, defect O) and PAPER_FILL_SLIPPAGE_PCT now env-tunable with an
        honest 1% default applied against the trade (defect R).
        Neutral strategies run ONLY on true-0DTE index products (SPY/QQQ/SPX/
        IWM); every other symbol (single names + weekly-only ETFs) is
        directional-only, derived automatically from FULL_STRATEGY_INSTRUMENTS.
sweep strike delta now scales with reversal strength
        (strong->far-OTM, weak->near-ATM); ORB strike snapping breaks toward
        higher/lower delta; paper fills at the exact bid/ask midpoint (no
        slippage) — all orders priced at the mark.
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
TOLERANCES REMOVED + SESSION_LOSS_LIMIT deleted.
        (a) ORB_BREAK_BUFFER (0.05% of price) REMOVED. It gated the break on the
            close clearing the range by a PERCENTAGE — $0.49 on MU, ~$3.00 on SPX.
            The retest is already the noise filter (a meaningless break fails it),
            so the buffer only cost real setups while scaling into a hole on
            high-priced instruments. See orb_engine v3.5.
        (b) SESSION_LOSS_LIMIT (the integer 2) DELETED. It was a COUNT of losing
            trades from the v1.x count-based circuit breaker, and it is NOT the
            daily loss halt. It has been vestigial since risk_manager v1.4, which
            gates nothing. It survived only in dashboards, which printed
            "Session CB: 2 losses -> halt" for a halt that could never occur.
            The REAL halt is DAILY_LOSS_LIMIT_USD (below): dollars, net for the
            day, so a green day keeps trading no matter how many losses stack up.
DEAD-CONSTANT PURGE + honest comments.
        (a) BUTTERFLY_ENTRY_CUTOFF_ET 15:00 -> 14:00. The 15:00 value was
            UNREACHABLE: main.py calls session_guard.can_enter() WITHOUT
            is_butterfly=True, so the generic 14:00 cutoff always fired first.
            14:00 is also the intended rule (post-14:00 tape gets erratic on
            dealer hedging). This makes config agree with live behaviour; it is
            NOT a behaviour change.
        (b) REMOVED, never imported by any module (verified by grep across the
            tree and by git log -S back to the initial commit):
              ORB_TRAIL_ACTIVATION   — duplicate of TRAIL_ACTIVATION_PCT
              CONDOR_SHORT_DELTA     — from iron_condor v1.0 (delta selection),
              CONDOR_DELTA_TOLERANCE   dead since v1.1 made strikes BB-anchored
                                       a HARDCODED `aligned_timeframes < 2`; the
                                       config value (1) was LOOSER and unwired
              ENTRY_COOLDOWN_MINUTES — ORB's state machine IS the cooldown
                                       (waiting / armed / open are exclusive)
        (c) The Iron Condor comment claiming "Delta-based strike selection is
            primary" was false since v1.1 — strikes are Bollinger-Band anchored
            with NO delta anywhere. Corrected.
        (d) MIN_RRR and VWAP_FILTER_ACTIVE are RETAINED but explicitly marked
            UNWIRED. Both are genesis constants (present at the initial commit,
            never referenced, never mentioned in any changelog). They are kept
            because each names an intended feature that was never built — see
            the notes at their definitions. Deleting them would erase the only
            evidence the intent existed.
All secrets come from environment variables — never from hardcoded values
or editable files. The setup_ec2.sh script writes them into the systemd
unit so the bot has them at runtime without any manual file editing.
Tunable strategy parameters live here and are safe to commit.
"""

import os
from dataclasses import dataclass
from typing import Optional


# ─── ENVIRONMENT HELPERS ──────────────────────────────────────────────────────

def _require(key: str) -> str:
    val = os.environ.get(key, "")
    if not val:
        raise EnvironmentError(
            f"\n\n  ❌  Missing required environment variable: {key}\n"
            f"      Run setup_ec2.sh to configure this bot properly.\n"
            f"      For local dev, export {key}='...' in your shell.\n"
        )
    return val

def _optional(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# ─── TASTYTRADE CREDENTIALS (from environment) ────────────────────────────────

def get_tt_client_secret()  -> str: return _require("TT_CLIENT_SECRET")
def get_tt_refresh_token()  -> str: return _require("TT_REFRESH_TOKEN")
def get_tt_account_number() -> str: return _require("TT_ACCOUNT_NUMBER")


# ─── TELEGRAM ALERTS (from environment) ──────────────────────────────────────

def get_telegram_token()    -> str: return _optional("TELEGRAM_TOKEN")
def get_telegram_chat_id()  -> str: return _optional("TELEGRAM_CHAT_ID")

def telegram_configured() -> bool:
    return bool(get_telegram_token() and get_telegram_chat_id())


# ─── INSTRUMENT SELECTION ─────────────────────────────────────────────────────

INSTRUMENT_UNSET    = "UNSET"      # r146: never a guessed symbol
INSTRUMENT          = (os.environ.get("OT_INSTRUMENT") or "").strip() or INSTRUMENT_UNSET

# Tradeable universe. Strike increments are a per-price-band starting point;
# the options chain resolves to the nearest liquid strike, so a slightly-off
# value is not fatal — tune a name here only if its fills consistently miss.
# ── OPTION PRICE INCREMENTS (2026-08-13, operator: "some contracts allow one
# cent increments others are five cents and even a few other are $.10") ───────
# TWO DIMENSIONS, not one: the CLASS decides whether it quotes in pennies, and
# the PRICE LEVEL decides the increment above the $3.00 boundary.
#   PENNY class      : $0.01 below $3.00, $0.05 at/above
#   NON-PENNY class  : $0.05 below $3.00, $0.10 at/above
# ⚠️ `PENNY_CLASSES` BELOW IS A STARTING LIST, NOT A VERIFIED ONE. Membership of
# the Penny Interval Program changes and is a BROKER/OCC fact, not something
# derivable from anything on this box. Verify against TastyTrade's contract
# metadata before trusting it — a wrong entry here posts an INVALID LIMIT that
# the venue rejects or silently adjusts, and a silently adjusted limit is a fill
# at a price nobody chose. Treated conservatively: anything NOT listed is
# assumed NON-PENNY, so an unknown symbol posts a coarser (valid) price rather
# than a finer (possibly rejected) one.
# ── ENTRY LIMIT LADDER (2026-08-13, operator's manual technique) ─────────────
# His worked example: bid 1.95 / ask 2.35 -> mark 2.15, spread 0.40.
# "I would try 2.05, 2.10 and then 2.15" — every ENTRY_LADDER_STEP_SEC, walking
# from aggressive toward the mark. Expressed as fractions of the HALF-spread out
# from the mark, so it self-scales: 0.50 -> 2.05, 0.25 -> 2.10, 0.00 -> 2.15.
# Terminal rung SITS AT MARK and re-anchors on a fresh quote each tick — his
# words: "let it sit at Mark in case price comes back and the plan can activate."
# ⚠️ PRICING ONLY. Posting an aggressive limit and ASSUMING it fills manufactures
# edge — the better the rung, the larger the fake gain. PAPER NEVER BOOKS A FILL
# FROM THESE PRICES - it books the mark. (The unwired fill model that was meant
# to gate such fills was deleted in r216.)
# ── TC.6 KILL SWITCH (2026-08-13) ────────────────────────────────────────────
# TC.6 is the ONLY brand-new FIRING strategy shipped today and was the only one
# with no env-level off switch — stopping it would have needed a code change and
# a re-bake, on a strategy that has never executed a live order. Every other
# change today has one. This closes that gap.
# ── TC.6 OWNS ITS OWN CONSTANTS (TCS.1, 2026-08-14) ──────────────────────────
# ⚠️ TREND PARTICIPATION BORROWED SIX `CONDOR_*` KNOBS, so changing one for the
# CONDOR silently retuned a DIFFERENT TRADE and nothing said so. These are the
# same numbers under names that mean what they govern.
# **VALUES ARE IDENTICAL TO THE CONDOR DEFAULTS THEY REPLACE** — this is a
# de-coupling, not a re-tune, and `tests/test_tcs_decoupling.py` asserts the
# equality so a future divergence is a DECISION rather than a drift.
TCS_MIN_POP                 = float(os.environ.get("OT_TCS_MIN_POP", "0.70"))
# r175 — SELECTION, a stated baseline prior (not a fit): how many bars of the
# session's MEASURED drift the POP model may credit. 24 x 5m = two hours of
# the trend it can already see; beyond that is extrapolation. Operator ruling
# 2026-08-28: TCS must fire on trend days and stay out on chop; the drift is
# signed, so a reversal reads WORSE than driftless.
TCS_DRIFT_HORIZON_BARS      = float(os.environ.get("OT_TCS_DRIFT_HORIZON_BARS", "24"))
TCS_MAX_QUOTE_WIDTH         = float(os.environ.get("OT_TCS_MAX_QUOTE_WIDTH", "0.25"))
TCS_POP_BAR_MIN             = float(os.environ.get("OT_TCS_POP_BAR_MIN", "5"))
TCS_NICKEL_REF              = float(os.environ.get("OT_TCS_NICKEL_REF", "0.05"))
TCS_WING_WIDTH_SPX          = float(os.environ.get("OT_TCS_WING_SPX", "5"))
TCS_WING_WIDTH_QQQ          = float(os.environ.get("OT_TCS_WING_QQQ", "5"))

# ⚠️ AUDIT F2 (2026-08-20): DEFAULT WAS "1" — a LIVE sixth strategy. TCS's own
# GATES block says "NOT SPECCED, DELIBERATELY, AND NOT DISPATCHED... 21 trades,
# 28.6% direction accuracy", TRADES.md specs five strategies without it, and
# check_dispatch does not cover it — yet main.py dispatched it on every
# afternoon tick with direction from the trend vote (measured 34.2% on puts,
# the quantity v4 exists to retire). Five guards missed it because each read a
# different document. Default now matches the stated design: OFF. Turning it
# on requires the env var AND a v4 spec in TRADES.md — the flag is not the gap;
# the missing spec is.
# 🔴 DEFAULT IS ON. Operator has authorised TC.6 three separate times; the
# default of "0" was a SILENT ENCODING nobody chose — the strategy returned
# None on its FIRST line, before any logging, so it was invisible in the log
# and looked like "evaluated and declined" rather than "switched off".
# ⚠️ SPEC.1 CLASS. An operator decision must not live in an env-var default
# that no surface reports. If TC.6 is ever to be disabled again it is an
# explicit OT_TCS_ACTIVE=0, not an absence.
TREND_CREDIT_ACTIVE         = os.environ.get("OT_TCS_ACTIVE", "") == "1"    # r204: RETIRED by ruling 2026-10-03 ("Retire the sweep & TCS"); =1 restores it
# OTV5 r57 (TCS.LOG1) — unset = LOG: the plan runs and a fire books a SHADOW trade (execution/shadow_book.py), never
# an order. "0"/"off"/"dormant" = off (not asked); "1" = trade (TREND_CREDIT_ACTIVE). An unknown value keeps the
# default (log) and is named. The label configure.sh shows; strategy/plan_state.py makes the same reading.
TCS_ENV_REFUSED = ""
_tcs_raw = os.environ.get("OT_TCS_ACTIVE", "").strip().lower()
if _tcs_raw in ("1", "trade", "active", "on") and TREND_CREDIT_ACTIVE:
    TCS_MODE = "trade"
elif _tcs_raw in ("0", "off", "dormant"):
    TCS_MODE = "off"
else:
    TCS_MODE = "log"
    if _tcs_raw not in ("", "log", "1"):
        TCS_ENV_REFUSED = _tcs_raw
SWEEP_CS_ENABLED            = os.environ.get("OT_SWEEP_CS", "0") == "1"     # r204: RETIRED by the same ruling; =1 restores it
# ── TC.6 ENTRY GATES (2026-08-14 HOTFIX — it rapid-fired the whole fleet) ─────
# Observed 10:02 ET on 08-14: NVDA sold a $5-wide for $0.06, PLTR a $6-wide for
# $0.08, and every box re-entered seconds after a nickel close.
# THREE THINGS WERE MISSING AND EACH ONE ALONE WOULD HAVE STOPPED IT:
#  (1) NO AFTERNOON GATE. Designed as afternoon trend participation, coded
#      against GLOBAL_NO_ENTRY_ET (14:00). It fired at 10:02.
#  (2) NO MINIMUM CREDIT — and the POP floor CAUSES this. POP rises with
#      distance, so requiring POP >= 0.70 selects for FAR strikes, and far
#      strikes collect almost nothing. The probability half of the gate shipped
#      without the payoff half. A gate that only demands SAFETY systematically
#      finds the worst-paid trade that clears it.
#  (3) NO RE-ENTRY COOLDOWN. With credit $0.06 and the nickel close at $0.05,
#      total profit potential is ONE CENT — the trade closes on the tick it
#      opens, then reopens. "No per-session limit" was the operator's call and
#      is respected; a LOOP is a defect, not a limit question.
# 🔴 r98 (2026-08-24) — 11:00 COLLIDED WITH THE RUNAWAY, WHICH FIRES ON THE
# SAME TRIGGER. The handoff credit spread and RunawayContinuation are two
# expressions of ONE event: an ORB that ran without retesting. AFD.1 blocks long
# debits from DEBIT_DIRECTIONAL_CUTOFF_ET = 11:30, so between 11:00 and 11:30
# BOTH were armed on the same runaway — and dispatch order decides, not design:
# RunawayContinuation gets first refusal (it must, because firing DISARMS the
# retest), sets `signal`, and TC.6 sits behind `if signal is None` and never
# runs. The handoff was therefore SHADOWED for the entire half hour it was
# nominally open, and only reachable after 11:30 by accident of the debit
# cutoff rather than by intent.
# ⚠️ 11:31, NOT 11:30. The cutoff test is `>= (11, 30)`, so the debit is already
# blocked AT 11:30; starting the credit at 11:30 would hand both strategies the
# same minute and reproduce the collision in miniature. One minute of daylight
# makes the handover unambiguous in the log and in the record.
# Operator, 2026-08-24: "Handoff (credit) needs to start at 1131 - it's
# colliding with runaway (same trigger)."
# ⚠️ THE WINDOW IS NOW 11:31 -> TCS_ENTRY_END_ET (14:00). The debit owns the
# runaway until 11:30; the credit owns it after.
# ══ r148 (WIN.1) — ONE ENTRY-WINDOW TABLE ═══════════════════════════════════
# Operator, 2026-09-22: *"Why are there multiple places for the trade windows? Why
# isn't there 1 universal table?"* — and 2026-09-26: *"I agree to all of that."*
# ONE (start, end) per strategy, ET. The admission table (execution/position_manager)
# and every plan read THIS; every older name below derives from it. A plan that
# needs a window reads a config name with NO literal fallback, so a missing name
# fails at import instead of silently becoming 14:00 (r81's defect, which sat
# pre-armed in tcs_plan and sweep_plan until this revision).
# ⚠️ Values are the EFFECTIVE windows measured 2026-09-26. TrendCreditSpread
# starts 11:31 (its plan refused 11:30 while the admission row said 11:30).
# ══ r149 (EOD.1) — THE END-OF-DAY SCHEDULE ══════════════════════════════════
# Operator, 2026-09-26: *"Stop entries at 1540"*; *"Resting limit orders at 1545,
# ladder exits at 1550 if they're not the assignment risk type"*; unfilled cross
# at 15:55 (*"Agree"*); resting price *"Best case on the trajectory (nickel close,
# 1 delta, etc)"*. ASSIGNMENT RISK = a short leg (credit verticals, condor/trend
# legs, the tent, butterflies, an adopted short). Every EOD time reads THIS table.
# 🔴 SUPERSEDES r105's "a credit at the hard close takes the nickel or takes
# assignment and NEVER crosses": an unfilled resting close now crosses at 15:55.
EOD_SCHEDULE = {
    "entries_stop": (15, 40),   # no new entries at or after
    "resting_at":   (15, 45),   # assignment-risk: resting best-case close
    "ladder_at":    (15, 50),   # everything else: the mark ladder
    "cross_at":     (15, 55),   # anything still open crosses
}

# ── r189 (RUNW.1) — RUNAWAY'S END IS A PER-BOX SWITCH ────────────────────────
# Unset = r187's 10:30. OT_RUNAWAY_END="HH:MM" (09:36 .. the entries stop)
# moves ONLY Runaway's end. A malformed or out-of-range value keeps 10:30 - the
# stricter end - and is named in RUNAWAY_END_ENV_REFUSED for the WARNING
# runaway_plan logs at import: "refused" must never look like "applied".
_RUNAWAY_END_DEFAULT = (10, 30)
RUNAWAY_END_ENV_REFUSED = ""


def _runaway_end():
    global RUNAWAY_END_ENV_REFUSED
    raw = os.environ.get("OT_RUNAWAY_END", "").strip()
    if not raw:
        return _RUNAWAY_END_DEFAULT
    try:
        parts = raw.split(":")
        if len(parts) != 2:
            raise ValueError(raw)
        hm = (int(parts[0]), int(parts[1]))
        if not (0 <= hm[1] < 60 and (9, 36) <= hm <= tuple(EOD_SCHEDULE["entries_stop"])):
            raise ValueError(raw)
        return hm
    except ValueError:
        RUNAWAY_END_ENV_REFUSED = raw
        return _RUNAWAY_END_DEFAULT


RUNAWAY_END = _runaway_end()

# ── r265 (BRK.9) — BREAKOUT'S END IS A PER-BOX SWITCH, THE MIRROR OF r189 ─────
# Unset = r187's 10:30. OT_BREAKOUT_END="HH:MM" (09:36 .. the entries stop)
# moves ONLY Breakout's end. A malformed or out-of-range value keeps 10:30 and
# is named in BREAKOUT_END_ENV_REFUSED (main's Service mode line prints it).
# The operator, 2026-10-10 13:37 ET: "Yes, to all" - re-open Breakout after
# 10:29 on QQQ; the cutoff's counterfactual is every Breakout trade entered at
# or after 10:30 (that trade would not exist under r187).
_BREAKOUT_END_DEFAULT = (10, 30)
BREAKOUT_END_ENV_REFUSED = ""


def _breakout_end():
    global BREAKOUT_END_ENV_REFUSED
    raw = os.environ.get("OT_BREAKOUT_END", "").strip()
    if not raw:
        return _BREAKOUT_END_DEFAULT
    try:
        parts = raw.split(":")
        if len(parts) != 2:
            raise ValueError(raw)
        hm = (int(parts[0]), int(parts[1]))
        if not (0 <= hm[1] < 60 and (9, 36) <= hm <= tuple(EOD_SCHEDULE["entries_stop"])):
            raise ValueError(raw)
        return hm
    except ValueError:
        BREAKOUT_END_ENV_REFUSED = raw
        return _BREAKOUT_END_DEFAULT


BREAKOUT_END = _breakout_end()

# ── r265 (BRK.8) — BREAKOUT'S NO-PROGRESS EXIT ──────────────────────────────
# off | log | trade. Unset = log: every box RECORDS what the cut would do; only
# a box set to trade acts on it (QQQ-TEST; SPX-TEST stays log until its own
# threshold is fitted - its 9 Breakouts moved 1, -910, 10-10).
BRK_NOPROG_ENV_REFUSED = ""
_np_raw = os.environ.get("OT_BRK_NOPROG", "").strip().lower()
if _np_raw in ("off", "log", "trade"):
    BRK_NOPROG_MODE = _np_raw
else:
    BRK_NOPROG_MODE = "log"
    if _np_raw:
        BRK_NOPROG_ENV_REFUSED = _np_raw
# ── r284 (BRK.11) — BREAKOUT'S STOP IS THE 5m SWING, NOT THE 1m BREAK BAR ──────
# off | log | trade. UNSET = trade (the operator, 2026-10-14 11:47 ET: "Yes, we have
# to"). trade: the stop is the farther of the break bar's extreme and the extreme
# of the last BRK_STOP5M_BARS CLOSED 5m bars of today's RTH, so size and the
# structural premium stop follow it; log: the 1m stop trades and the 5m stop is only
# recorded; off: neither. A refused value reads as log and is named.
BRK_STOP5M_ENV_REFUSED = ""
_s5_raw = os.environ.get("OT_BRK_STOP5M", "").strip().lower()
if _s5_raw in ("off", "log", "trade"):
    BRK_STOP5M_MODE = _s5_raw
else:
    BRK_STOP5M_MODE = "log" if _s5_raw else "trade"
    if _s5_raw:
        BRK_STOP5M_ENV_REFUSED = _s5_raw
BRK_STOP5M_BARS = 3
# ── r285 (HUNT.8) — THE HUNT'S THESIS LINE IS THE FARTHER OF ITS BOUNDARY AND THE
# 5m SWING AS OF ENTRY (the same swing_5m_stop as BRK.11). off | log | trade, UNSET =
# trade (the operator, 2026-10-14 11:47 ET: "Yes, we have to"). log: the boundary
# decides and the 5m line is only recorded. A refused value reads as log, named.
HUNT_STOP5M_ENV_REFUSED = ""
_h5_raw = os.environ.get("OT_HUNT_STOP5M", "").strip().lower()
if _h5_raw in ("off", "log", "trade"):
    HUNT_STOP5M_MODE = _h5_raw
else:
    HUNT_STOP5M_MODE = "log" if _h5_raw else "trade"
    if _h5_raw:
        HUNT_STOP5M_ENV_REFUSED = _h5_raw
# ── BRK.12 / HUNT.9 — A RETURN TO THE RANGE RE-ARMS, RECORD-ONLY ──────────────
# log | off. UNSET = log (the operator, 2026-10-15 10:16 ET, to QQQ-TEST's
# "BRK.12 / HUNT.9: record-only": "Concur on all"). log: the re-arm is evaluated and
# written to data/counterfactual/ (breakout_rearm.jsonl, hunt_rearm.jsonl) and NEVER
# places an order - the existing rules alone decide; off: not evaluated. There is no
# trade value. A refused value reads as log and is named.
BRK_REARM_ENV_REFUSED = ""
_br_raw = os.environ.get("OT_BRK_REARM", "").strip().lower()
if _br_raw in ("off", "log"):
    BRK_REARM_MODE = _br_raw
else:
    BRK_REARM_MODE = "log"
    if _br_raw:
        BRK_REARM_ENV_REFUSED = _br_raw
# ── r316 BRK.15 — A BREAKOUT SIDE RE-ARMS ON EVERY RETURN TO THE RANGE ───────
# rearm | extreme. UNSET = rearm (the operator, 2026-10-24 13:45 ET: "The new session high/low rule needs to be
# dropped. You established that the move was mostly done if we waited for a new extreme"; 13:56 ET: "For now, rearm
# it on every reentry"). rearm: a Breakout fires only on a FRESH break - the first 1m close beyond the edge since
# 09:35 or since the latest close back inside it; the old new-extreme verdict is written beside it to
# data/counterfactual/breakout_refire.jsonl wherever the two disagree. extreme: r131/r282's rule decides (rollback)
# and the re-arm verdict is the one recorded. A refused value reads rearm and is named.
BRK_REFIRE_ENV_REFUSED = ""
_bf_raw = os.environ.get("OT_BRK_REFIRE", "").strip().lower()
if _bf_raw in ("rearm", "extreme"):
    BRK_REFIRE_MODE = _bf_raw
else:
    BRK_REFIRE_MODE = "rearm"
    if _bf_raw:
        BRK_REFIRE_ENV_REFUSED = _bf_raw
# ── r316 HUNT.13 — NO HUNT ON A SIDE AFTER A LOSING BREAKOUT ON THAT SIDE ─────
# trade | log | off. UNSET = trade (the operator, 2026-10-24 13:45 ET: "on a losing breakout trade, forbid a liquidity
# hunt on the same side for the day"; 13:56 ET: "if a breakout on one side fails, don't allow a hunt to fire on that
# side for the rest of the day"). trade: the Hunt HOLDS, named; log: it fires and the would-be hold is written; off:
# not evaluated. Every hold or would-be hold is written to data/counterfactual/hunt_after_breakout.jsonl.
HUNT_AFTER_BRK_ENV_REFUSED = ""
_hb_raw = os.environ.get("OT_HUNT_AFTER_BRK", "").strip().lower()
if _hb_raw in ("trade", "log", "off"):
    HUNT_AFTER_BRK_MODE = _hb_raw
else:
    HUNT_AFTER_BRK_MODE = "trade"
    if _hb_raw:
        HUNT_AFTER_BRK_ENV_REFUSED = _hb_raw
HUNT_REARM_ENV_REFUSED = ""
_hr_raw = os.environ.get("OT_HUNT_REARM", "").strip().lower()
if _hr_raw in ("off", "log"):
    HUNT_REARM_MODE = _hr_raw
else:
    HUNT_REARM_MODE = "log"
    if _hr_raw:
        HUNT_REARM_ENV_REFUSED = _hr_raw
# ── r288 (PARK.1) — PARK: THE 11:00 FIRST-HOUR CONTINUATION ──────────────────
# The operator's friend's strategy (CONT11), renamed PARK. The operator, 2026-10-17
# 18:21 ET: "Trade it, don't just log it. Paper is free. Call it PARK (named after my
# friend)"; on SPX: "Use our actual numbers, trade it—don't log it". trade | log |
# off, UNSET = trade. log: the plan runs and a would-be fire is written to
# data/counterfactual/park_signal.jsonl, never ordered; off: not asked. A refused
# value reads as log and is named.
PARK_ENV_REFUSED = ""
_pk_raw = os.environ.get("OT_PARK", "").strip().lower()
if _pk_raw in ("off", "log", "trade"):
    PARK_MODE = _pk_raw
else:
    PARK_MODE = "log" if _pk_raw else "trade"
    if _pk_raw:
        PARK_ENV_REFUSED = _pk_raw
# The read, frozen from /var/tmp/sat_1017/cont11/PREREG_CONT11.md (C0) and PARK.X
# (/var/tmp/sat_1017/park, picks sha 85dca420): first-hour move = the 10:30 1m bar's
# close against the 09:30 1m bar's open, |move| >= 0.20%; GATE-G - never against the
# opening gap (09:30 open vs the prior close); the strike nearest the 11:00 1m close.
PARK_MOVE_PCT = 0.20
PARK_SIGNAL_BAR_ET = (10, 30)        # the first hour's last 1m bar (its CLOSE)
PARK_SPOT_BAR_ET = (11, 0)           # the 1m bar whose close picks the strike
PARK_MIN_ASK = 0.50                  # the study's floor: a cheaper ask is no trade
# Exits (FIRST MATCH WINS, execution/exit_engine._evaluate_park): the lock - armed
# once the bid reaches entry x (1 + ARM), then out when the bid falls to entry x (1 +
# FLOOR); the delta floor - |delta| <= PARK_DELTA_FLOOR from PARK_DELTA_FROM_ET; else
# the close at PARK_CLOSE_ET. No premium stop, no trail (the 25% trail was the worst
# PARK exit on both symbols, 10-17).
PARK_LOCK_ARM = 0.60
PARK_LOCK_FLOOR = 0.20
PARK_DELTA_FLOOR = 0.30
PARK_DELTA_FROM_ET = (11, 30)
PARK_CLOSE_ET = (15, 45)
# Its own budget, outside the morning's catastrophic cap (the operator, 2026-10-17):
# a PARK close never counts toward the cap's realized P&L, and the cap never refuses
# PARK (position_manager: cap_exempt). Sizing is the box's own RISK_PER_TRADE_USD,
# flat: floor(risk / (ask x 100)).
CAP_EXCLUDED_STRATEGIES = ("PARK", "PARC")     # r46 (PARC.1): PARC has its own budget too
# ── OTV5 r46 (PARC.1) — PARC: PARK'S ENTRY, A CREDIT SPREAD ON THE SAFER SIDE ──────
# The operator, 2026-10-27: "under identical entry conditions the PARK trade sells a
# credit spread ATM nearest the strike on the safer side ... Call it PARC"; "No shadow
# mode. We're paper. It trades tomorrow." The read is PARK's (PARK_MOVE_PCT, the bars,
# GATE-G); the spread, its 5m structure stop, the Breakout ramp and the exits are
# strategy/parc.py's. OT_PARC 1 | log | 0 (also trade/active/on, off/dormant), UNSET =
# 1 (trade). log: the plan runs and a would-be fire is recorded, never ordered; 0: not
# asked. An unknown value keeps the default (trade) and is named (PSTATE.1's rule).
PARC_ENV_REFUSED = ""
_pc_raw = os.environ.get("OT_PARC", "log").strip().lower()   # r50 (PARC.3): unset = log - paused until a better stop
if _pc_raw in ("1", "trade", "active", "on"):
    PARC_MODE = "trade"
elif _pc_raw in ("log", ""):
    PARC_MODE = "log"
elif _pc_raw in ("0", "off", "dormant"):
    PARC_MODE = "off"
else:
    PARC_MODE = "log"                  # r50: an unknown value keeps the default, now log
    PARC_ENV_REFUSED = _pc_raw
PARC_MIN_CREDIT = 0.20               # = 4 x CONDOR_NICKEL_CLOSE (0.05): a thinner credit is no trade
# ── r288 (BRK.13) — BREAKOUT'S DELTA FLOOR ──────────────────────────────────────
# trade | log | off, UNSET = trade (the operator, 2026-10-17 19:12 ET: "A is fine", to
# "trade it on QQQ-TEST with a counterfactual"). Breakout exits when |delta| <=
# BRK_DELTA_FLOOR, checked from BRK_DFLOOR_AFTER_S after entry; log records the would-
# be exit only. Every evaluation that fires (either mode) writes
# data/counterfactual/breakout_delta_floor.jsonl. MEASURED /var/tmp/sat_1017/bdelta
# (prereg 0c21a4b1, unseen QQQ 08-24..10-09 +1,363, 13 stocks +2,406, 7/13).
BRK_DFLOOR_ENV_REFUSED = ""
_bd_raw = os.environ.get("OT_BRK_DFLOOR", "").strip().lower()
if _bd_raw in ("off", "log", "trade"):
    BRK_DFLOOR_MODE = _bd_raw
else:
    BRK_DFLOOR_MODE = "log" if _bd_raw else "trade"
    if _bd_raw:
        BRK_DFLOOR_ENV_REFUSED = _bd_raw
BRK_DELTA_FLOOR = 0.30
BRK_DFLOOR_AFTER_S = 600
# ── r266 (STOP.1) — THE RESTING STOP (execution/resting_stop.py) ─────────────
RESTING_STOP_ENV_REFUSED = ""
_rs_raw = os.environ.get("OT_RESTING_STOP", "").strip().lower()
if _rs_raw in ("off", "trade"):
    RESTING_STOP_MODE = _rs_raw
else:
    RESTING_STOP_MODE = "off"
    if _rs_raw:
        RESTING_STOP_ENV_REFUSED = _rs_raw
# ── r272 (COMMIT.2 / COMMIT.3) — ENTER ON COMMITMENT (analysis/commitment.py) ───
# OT_COMMIT_GATE off | log | trade. UNSET = trade: a directional entry whose side is
# ABANDONED is not placed (the operator, 2026-10-12 11:35 ET: trading on both paper
# boxes). A LIVE box never acts on it: trade reads as log there and the Service mode
# line says so. A refused value reads log (records, changes nothing) and is named.
# OT_CAUTION_SIZE off | log. UNSET = log; "trade" is REFUSED in this revision (log only,
# by ruling) and named.
COMMIT_GATE_ENV_REFUSED = ""
_cg_raw = os.environ.get("OT_COMMIT_GATE", "").strip().lower()
if _cg_raw in ("off", "log", "trade"):
    COMMIT_GATE_MODE = _cg_raw
elif not _cg_raw:
    COMMIT_GATE_MODE = "trade"
else:
    COMMIT_GATE_MODE = "log"
    COMMIT_GATE_ENV_REFUSED = _cg_raw
CAUTION_SIZE_ENV_REFUSED = ""
_cz_raw = os.environ.get("OT_CAUTION_SIZE", "").strip().lower()
if _cz_raw in ("off", "log"):
    CAUTION_SIZE_MODE = _cz_raw
else:
    CAUTION_SIZE_MODE = "log"
    if _cz_raw:
        CAUTION_SIZE_ENV_REFUSED = _cz_raw
# (CD.1) r306/r316 RENT.2/RENT.3 - the 20 s re-entry gate - is SCRAPPED. The operator, 2026-10-24: "The 20 seconds is
# arbitrary, just like 45 seconds, or 145 seconds. It has zero value. Scrap it." OT_REENTRY_GATE is no longer read.
RESTING_STOP_WAIT_S = 120.0
RESTING_STOP_EMERGENCY_FRAC = 0.05
BRK_NOPROG_STALL_BARS = 2      # consecutive closed 1m bars without a new favourable extreme
BRK_NOPROG_MIN_R = 0.5         # best progress since entry, in R = |underlying_entry - underlying_stop|
# ── r54 (BRK.16) — BREAKOUT'S TARGET AND TRAIL ARM, IN MULTIPLES OF THE OPENING RANGE WIDTH W ──────────────────
# The operator, 2026-10-29: "For any opening range width, let's call it W — the target will be from the boundary of the
# opening range a distance of 1W. For a long it's from the top of the opening range and for a short, it's from the
# bottom"; "I want the trailing stop activation to occur at 1/2 W." The target is PLANNING ONLY (R, the strike,
# underlying_target) - Breakout has no target exit ("how far it gets is determined by the trailing stop").
BRK_TARGET_W = 1.0             # strategy/breakout_plan.py: target = edge +/- BRK_TARGET_W x W
BRK_TRAIL_ARM_W = 0.5          # execution/exit_engine.py: the trail arms once the underlying reaches edge +/- this x W
# The operator, 2026-10-29, on a break already well under way: "if we haven't entered before it reaches 1W, absolutely
# refuse it — that is runaway's domain. It should honestly refuse if it's already crossed 1/2W." The plan refuses a break
# CLOSE at or beyond edge +/- BRK_ENTRY_MAX_W x W, and the strategy will not fire on a live price at or beyond it.
BRK_ENTRY_MAX_W = 0.5          # strategy/breakout_plan.py + strategy/breakout.py: no entry at/beyond edge +/- this x W

ENTRY_WINDOWS = {
    # r149: directional debits run ALL DAY to the entries stop (operator: "A").
    # Supersedes criteria.py's 2026-08-29 "Debit entries are finished at 1130".
    "ORBStrategy":          ((9, 35),  EOD_SCHEDULE["entries_stop"]),
    "RunawayContinuation":  ((9, 35),  RUNAWAY_END),   # r187: 10:29 last entry; r189: OT_RUNAWAY_END per box
    "LiquidityHunt":        ((9, 35),  (10, 30)),   # r187
    "Breakout":             ((9, 35),  BREAKOUT_END),   # r187: 10:29 last entry; r265: OT_BREAKOUT_END per box
    "VOLT":                 ((9, 35),  (10, 30)),   # r187 (VOLT is also OFF by default)
    "SweepCreditSpread":    ((9, 35),  EOD_SCHEDULE["entries_stop"]),
    "TrendCreditSpread":    ((11, 31), EOD_SCHEDULE["entries_stop"]),
    "GEXPinButterfly":      ((13, 0),  (15, 0)),   # r273 (BFLY.10): was 12:00; the operator, 2026-10-12: "reduce the fly window to 1300"
    "ATPButterfly":         ((13, 0),  (15, 0)),   # r273 (BFLY.10): was 12:00. r179: was 11:30 here while the plan itself stayed dormant until 12:00; the operator, 2026-09-30: "12:00 is fine"
    "OpeningRangeCreditSpread": ((9, 45), (10, 30)),  # r204 (ORCS): 09:45 beat 09:36; positive to 10:30, gone from 11:00 (X6/X7)
    "PARK":                 ((11, 1),  (11, 3)),   # r288 (PARK.1): the ask 11:01-11:02 after the 11:00 bar closes
    "PARC":                 ((11, 1),  (11, 3)),   # OTV5 r46 (PARC.1): PARK's window, the credit side
}


def _hhmm(t) -> str:
    return f"{t[0]}:{t[1]:02d}"


TCS_START_ET                = ENTRY_WINDOWS["TrendCreditSpread"][0]    # afternoon only; 11:31 clears AFD.1
# ⚠️ r141 — kept as a literal because CREDIT_ENTRY_START_ET is defined further
# down this file; the two MUST stay equal and check_entry_windows pins it.
# Credit must clear BOTH floors. Width-relative keeps risk/reward sane;
# nickel-relative guarantees the trade has room to exist at all.
# 0.10 is a STATED PRIOR inside the measured band: credit_edge ran 8-19% of
# width at sellable offsets, and TC.7's ORB-anchored 0.00% cell was ~17%.
TCS_MIN_CREDIT_PCT_WIDTH    = float(os.environ.get("OT_TCS_MIN_CREDIT_PCT", "0.10"))
# ── THE JOINT EV TEST (2026-08-14) ───────────────────────────────────────────
# Operator: "The trade should at least enter on some expectation of profit, not
# all willy nilly like this."
# A flat credit floor and a flat POP floor are INDEPENDENT tests, and independent
# is the bug: POP >= 0.70 selects FAR strikes, far strikes pay little, and the
# two floors never talk to each other. The correct condition is a single
# inequality:
#       EV = credit * POP - L * width * (1 - POP) > 0
#   =>  credit / width  >  L * (1 - POP) / POP
# so a LOW-POP strike must pay RICHLY and a HIGH-POP strike may be thin. That is
# the shape a credit spread actually has.
# `L` is loss-given-breach as a fraction of width. **NOT 1.0**: a breach rarely
# runs the full width by the bell — TC.7's ORB-anchored cell measured E[loss]
# 0.35 on a $5 wide (7% of width) at 90% terminal-OK, and credit_edge put real
# credits at 8-19% of width. At L=1.0 a POP-0.70 strike would need 30% of width,
# which essentially never occurs, and the gate would silence TC.6 entirely —
# over-correcting into silence is its own failure.
# L=0.5 is a STATED PRIOR: it requires 21% of width at POP 0.70, 5.6% at POP
# 0.90, 2.6% at POP 0.95. Conservative against the measured 7%, and it produces
# the right ORDERING regardless of the exact value.
TCS_LOSS_GIVEN_BREACH       = float(os.environ.get("OT_TCS_LGB", "0.5"))
TCS_MIN_CREDIT_NICKEL_MULT  = float(os.environ.get("OT_TCS_NICKEL_MULT", "4.0"))

# ── r238 — THE TWO NUMBERS THE NEW TCS TURNS ON ───────────────────────────────
# 🔴 1:1 ON THE EXPIRY BASIS, NOT THE STOP BASIS, and the distinction is
# arithmetic rather than taste. With the stop at 15% OF CREDIT,
# `credit / stop` is 1/0.15 = 6.67 for EVERY credit and EVERY wing — R on the
# stop basis is a CONSTANT, so "set the protective wing to achieve 1:1" would
# have nothing to solve for. Only `credit / (width - credit)` is a function of
# the wing, and 1.0 there means CREDIT >= 50% OF WIDTH.
# ⚠️ IT IS DELIBERATELY SEPARATE FROM `criteria.R_FLOOR_STOP`, which the SWEEP
# uses on the stop basis (r234). One constant with two bases is the rot §35
# names; each names its own.
TCS_R_FLOOR_EXPIRY  = float(os.environ.get("OT_TCS_R_FLOOR_EXPIRY", "1.00"))

# 🔴 15% OF CREDIT, which is NOT what exit_engine's lone stop does (15% of
# RISK) and not an oversight. Operator, 2026-09-04: *"stop out at 15% of credit
# collected"*, choosing the most aggressive option *"because it's available,
# not expected."* On a $2.50 credit that is a $0.375 stop against a $2.45 win
# to the nickel — a realized 6.5:1, breakeven near a 13% hit rate.
# ⚠️ THE FLOOR THAT KEEPS IT HONEST is `stop_survivable`: the stop must clear
# 2x the short leg's quote or it fires on a quote update rather than on the
# trade being wrong. That is why the 1:1 rule and this one PULL THE SAME WAY —
# a thin far-OTM sale fails both, a rich near-money sale clears both.
TCS_STOP_PCT_OF_CREDIT = float(os.environ.get("OT_TCS_STOP_PCT_CREDIT", "0.15"))
# ⚠️ RETIRED 2026-08-14, NOT DELETED. TC.6 no longer reads this. It was an
# emergency brake during the rapid-fire incident and was the wrong instrument
# for the right worry — the loop came from a $0.06 credit sitting one cent from
# a nickel close and one cent from a mis-set stop, all fixed at the source. The
# constant survives so a future re-add needs no config change; nothing consults
# it today.
TCS_COOLDOWN_MIN            = float(os.environ.get("OT_TCS_COOLDOWN_MIN", "0"))

ENTRY_LIMIT_LADDER          = [0.50, 0.25, 0.00]
ENTRY_LADDER_STEP_SEC       = float(os.environ.get("OT_ENTRY_LADDER_STEP_SEC", "15"))
ENTRY_LADDER_ACTIVE         = os.environ.get("OT_ENTRY_LADDER", "0") == "1"

PENNY_CLASSES = {
    "SPY", "QQQ", "IWM", "DIA", "GLD", "TLT",
    "AAPL", "AMD", "AMZN", "AVGO", "COST", "CRM", "CVX", "GOOGL", "GS",
    "JPM", "LLY", "META", "MSFT", "MU", "NFLX", "NVDA", "ORCL", "PLTR",
    "SMCI", "SMH", "TSLA", "UNH", "XOM",
    "SOFI", "AAL",                                  # r137: measured penny-quoted
    # r175 — measured penny-quoted 2026-09-29 (>= half of sub-$3 quotes off the nickel grid)
    "INTC", "NU", "IBIT", "MSTR", "SOXL", "SLV", "CCL", "TQQQ", "USO",
    "AMC", "GME", "BAC", "RIVN", "WMT", "NKE", "BA", "HOOD", "GOOG",
    "MRVL", "UBER", "QCOM", "TSM", "ARM", "BABA", "XLE", "MARA", "NOW",
    "GDX", "CVNA", "CRWD", "COIN", "SQQQ", "IONQ", "MCD", "DKNG", "SOXS",
    "ACHR", "RIOT", "KO", "C", "RGTI", "TNA", "MS", "JNJ", "MRK",
    "OKTA", "AA", "DASH",
}
# SPX is DELIBERATELY ABSENT — index options are not in the penny program.
PRICE_INCREMENT_BOUNDARY    = 3.00

STRIKE_INCREMENTS = {
    # Index products with true 0DTE — full strategy set (condor/butterfly OK)
    "SPY": 1, "QQQ": 1, "SPX": 5, "IWM": 1,
    # Weekly-only ETFs — directional only
    "DIA": 1, "SMH": 1, "TLT": 1, "GLD": 1,
    # Single names — directional only
    "AAPL": 5, "MSFT": 5, "META": 5, "MU": 5, "TSLA": 5, "NVDA": 1,
    "NFLX": 1, "ORCL": 1, "SMCI": 1, "PLTR": 1, "AMD": 1, "AMZN": 1,
    "GOOGL": 1, "XOM": 1, "CVX": 1, "JPM": 5, "GS": 5, "LLY": 5,
    "UNH": 5, "AVGO": 5, "CRM": 5, "COST": 5,
    # r137 — low-priced names for the live-mechanics paper boxes (FLEET.1).
    # $0.50 strikes near the money, weeklies - measured on Cboe's chain 09-24.
    "SOFI": 0.5, "AAL": 0.5,
    # r175 (SYM.1) — the top-75 options names, ATM spread <= 10%, measured on
    # Cboe's delayed chains 2026-09-29 (near-money step, nearest expiry).
    "INTC": 1, "NU": 0.5, "IBIT": 0.5, "MSTR": 1, "SOXL": 1, "SLV": 0.5,
    "CCL": 0.5, "TQQQ": 1, "USO": 1, "AMC": 0.5, "GME": 0.5, "BAC": 1,
    "RIVN": 0.5, "WMT": 1, "NKE": 0.5, "BA": 2.5, "HOOD": 1, "GOOG": 2.5,
    "MRVL": 2.5, "UBER": 1, "QCOM": 2.5, "TSM": 2.5, "ARM": 2.5, "BABA": 1,
    "XLE": 1, "MARA": 0.5, "NOW": 1, "GDX": 0.5, "CVNA": 1, "CRWD": 2.5,
    "COIN": 2.5, "SQQQ": 0.5, "IONQ": 0.5, "MCD": 2.5, "DKNG": 0.5, "SOXS": 0.5,
    "ACHR": 0.5, "RIOT": 0.5, "KO": 1, "APP": 2.5, "C": 1, "RGTI": 0.5,
    "ASML": 5, "TNA": 1, "MS": 2.5, "JNJ": 2.5, "MRK": 1, "OKTA": 2.5,
    "AA": 0.5, "DASH": 2.5,
}
STRIKE_INCREMENT    = STRIKE_INCREMENTS.get(INSTRUMENT, 1)
# r175 (SYM.1) — a symbol off the list got the $1 default above in silence.
# main.py and data/candle_feed.py refuse to start unless this is True.
INSTRUMENT_LISTED   = INSTRUMENT in STRIKE_INCREMENTS

# Neutral strategies (iron condor, butterfly) require true-0DTE decay and strike
# density, so they run ONLY on these. Every other tradeable symbol is
# directional-only (ORB + Sweep Reversal), derived automatically — add a symbol
# to STRIKE_INCREMENTS and it's directional unless it's listed here.
# 2026-07-14 (operator directive): neutral strategies enabled FLEET-WIDE for
# data collection — every configured symbol runs butterfly/condor eligibility.
# Was {"SPY","QQQ","SPX","IWM"}, which silently excluded 26 of 29 live boxes.
FULL_STRATEGY_INSTRUMENTS    = set(STRIKE_INCREMENTS)

# ── Butterfly discount gate (2026-07-14, operator directive) ──────────────────
# The fly's edge is buying the tent at a DISCOUNT while price still has to walk
# into it: require net_debit <= this fraction of wing width (0.33 => min ~2:1
# reward:risk). Self-normalizing across symbols; needs only marks. PRIOR —
# calibrate from logged debit-ratio vs outcome once fleet-wide entries accrue.
BUTTERFLY_MAX_DEBIT_PCT_WIDTH = 0.33
# ── Conviction-scaled DISCOUNT gate (v-convdiscount 2026-07-28) ─────────────
# MEASURED on QQQ's full log: debit ratios 0.41-0.64 (min 0.41, cluster
# 0.47-0.53) against a flat 0.33 ceiling -> the gate rejected 100% of setups that
# reached it. Three butterflies exist in the entire fleet archive. Proximity was
# NOT the constraint: zero "too far from pin" rejections were ever logged.
# The tent is expensive because price sits near the pin. With high conviction it
# STAYS pinned, paying more is justified; with low conviction, demand the cheap
# tent. So the ceiling scales from the strict floor to a high-conviction ceiling.
# Bounds are set against the OBSERVED conviction range (0.000-0.582), NOT 0-1.
# ALL PRIOR -- refit from the debit-ratio ledger, which logs every evaluation.
BUTTERFLY_MAX_DEBIT_PCT_WIDTH_HICONV = float(os.environ.get("OT_BFLY_DEBIT_HICONV", "0.50"))

# ── BFLY.3 (2026-08-15) — THE FLAT DEBIT CEILING ─────────────────────────────
# Max profit is `wing - debit`, so at ratio 0.50 you risk exactly what you can
# win. **0.50 IS THE STRUCTURE'S OWN BREAK-EVEN**, not a fitted threshold — it
# needs no holdout and cannot be overfit. Above it the payoff is upside-down.
# Replaces the conviction-scaled ceiling: measured fleet-wide across 29 boxes,
# the conv->ratio slope is POSITIVE on 5 of 7 sampled symbols, so scaling up
# with conviction paid MORE exactly where the trade was WORSE. It also cost real
# trades — SMH had 46 setups at mean ratio 0.379 and fired 3.
BUTTERFLY_DEBIT_CEILING = float(os.environ.get("OT_BFLY_DEBIT_CEILING", "0.50"))
BUTTERFLY_DISC_CONV_LO = float(os.environ.get("OT_BFLY_DISC_CONV_LO", "0.30"))
BUTTERFLY_DISC_CONV_HI = float(os.environ.get("OT_BFLY_DISC_CONV_HI", "0.55"))
DIRECTIONAL_ONLY_INSTRUMENTS = set(STRIKE_INCREMENTS) - FULL_STRATEGY_INSTRUMENTS
DIRECTIONAL_ONLY             = INSTRUMENT in DIRECTIONAL_ONLY_INSTRUMENTS
CONTRACT_MULTIPLIER = 100

# ─── ACCOUNT & RISK ───────────────────────────────────────────────────────────

RISK_PER_TRADE_USD  = float(os.environ.get("OT_RISK_USD", "200"))

# ─── ORB BUDGET (r201) ─────────────────────────────────────────────────────
# 🔴 THE CEILING ON WHAT ONE ORB SETUP MAY DEPLOY. Operator, 2026-08-31, after
# an SPX ORB opened 50 contracts at $6.95 for $34,750 of premium on paper:
# *"Knowing that we can end up with a nominal position size in the 10s of
# thousands of dollars was eye opening. We are going to rein that in."*
# ⚠️ ORB IS THE ONLY UNSCALED STRATEGY. Every other rule already knows its
# budget from RISK_PER_TRADE_USD; the r181/r192 geometry was deliberately
# cap-exempt, so `max(1, floor(width / stop_distance))` grew without bound as
# the stop tightened. This is the bound.
# 🔑 THE SCALING CURVE IS NOT A NEW RAMP — it falls out of two clamps meeting.
#   contracts = min( floor(width / stop_distance),      # geometry
#                    floor(budget / cost_per_contract) ) # budget
# A tight stop makes geometry large, so the BUDGET binds and the position is
# the biggest the budget allows. A wide stop makes geometry small, so GEOMETRY
# binds and you get 1 lot. Operator's rule exactly: smallest stops get the
# maximum budget, biggest stops get a 1-lot maximum, everything else in
# between.
# ⚠️ THIS APPLIES IN PAPER TOO, DELIBERATELY. Paper's "unlimited" is the
# ACCOUNT, not the trade: an unconstrained paper sizer would overstate every
# P&L number against live and make the two incomparable.
# ⚠️ NOT read from the broker. Operator: *"I would prefer setting the orb's
# budget locally vs the dealer because I have more control over my exposure
# that way. A dealer offering available capital is a license for the bot to use
# it."* Consequence: sizing is deterministic and does not depend on what other
# boxes committed seconds earlier, and the reject-vs-reduce-to-fit question at
# the broker is never approached (still unverified — see backlog).
# ⚠️ PER BOX. Fifteen boxes each hold this much, so fleet exposure is 15x.
ORB_BUDGET_USD     = float(os.environ.get("OT_ORB_BUDGET_USD",
                                          str(RISK_PER_TRADE_USD)))


# ── r44 — WHAT ONE ORB SETUP MAY RISK ──────────────────────────────────────
# 🔑 ORB_BUDGET_USD is a CEILING ON DEPLOYED CAPITAL; this is the TARGET RISK
# at the structure stop, and they are different questions. The geometry rule
# (`width // distance`) is exactly risk-normalised — the operator's own model,
# tight stop big / wide stop small — but it normalises to `width x delta x 100`,
# a constant set by the OPENING RANGE. Measured 2026-09-18 on a 0.97 range:
# every stop distance from 0.54 to 0.01 risked $26-$32 while the contract count
# swung 1 to 80. That is 3% of a $1,050 per-trade budget.
# ⚠️ DEFAULTS TO THE SAME RISK EVERY OTHER STRATEGY TAKES, which on this box is
# roughly a 33x increase in ORB size. The operator's own read, 2026-09-18: the
# ORB *"is typically a loser… but when it does win it usually pretty good"* —
# so this scales the losses too, and it is deliberately ONE ENV VAR so it can be
# dialled to a fraction while it proves itself, without a revision.
# 🔴 r161 (SIZE.2) — MERGED INTO RISK_PER_TRADE_USD BY RULING. The operator,
# 2026-09-27: *"Risk per trade/Ramp Start (MIN)"* and *"Merge it. that was
# always the intent."* The ramp's START and the per-trade risk were two keys
# for one intent, and they had drifted apart on this box ($1,001 vs $1,050).
# ⚠️ THE NAME IS KEPT so every reader (risk_manager, the checkers) reads one
# value under the name it already uses; the ENV KEY is what is retired.
# ⚠️ A UNIT STILL CARRYING OT_ORB_RISK_USD IS NOT OBEYED AND NOT SILENT:
# ORB_RISK_ENV_IGNORED holds what it said, and main.py names it at startup
# (§0.5 — "ignored" must never look like "applied").
ORB_RISK_USD = RISK_PER_TRADE_USD
ORB_RISK_ENV_IGNORED = os.environ.get("OT_ORB_RISK_USD", "")

# ── r161 (SIZE.2) — POSITION SCALING, ON OR OFF, PER TRADE ─────────────────
# 🔑 THE OPERATOR, 2026-09-27: *"some of the other positions have benefited
# from the scaling sizes, but ultimately the orb has only gotten worse"*, and
# *"retain the original structure stop responsible for scaling the sizes but
# just use a flat dollar amount for the entry"*.
# ON  = the ramp: risk RISK_PER_TRADE_USD at the structure stop, capped at
#       ORB_BUDGET_USD deployed (RiskManager._size_geometry).
# OFF = FLAT: the budget rule every unscaled debit uses — about
#       RISK_PER_TRADE_USD of premium, whatever the stop distance.
# ⚠️ OFF CHANGES THE CONTRACT COUNT AND NOTHING ELSE. The structure stop is
# set by the strategy before sizing and the exits read it from the trade; the
# r93 noise floor is §36 FEASIBILITY and refuses a stop inside one bar either
# way; `sizes_on_geometry` (which also anchors the trail) is untouched.
# ⚠️ ONLY THE LITERAL "1" IS ON, as OT_PIN_PROXIMITY_ACTIVE — so a typo reads
# as OFF, the smaller position, never as the larger one.
SCALE_ORB      = os.environ.get("OT_SCALE_ORB", "1") == "1"
SCALE_BREAKOUT = os.environ.get("OT_SCALE_BREAKOUT", "1") == "1"
SCALE_VOLT     = os.environ.get("OT_SCALE_VOLT", "1") == "1"

# ── r93 — THE NOISE FLOOR: A STOP INSIDE ONE BAR IS NOT A STOP ────────────
# 🔴 THE INVERSION THIS CLOSES, MEASURED LIVE 2026-09-22. The 1-R rule
# normalises the SIZE of a loss and is blind to its FREQUENCY: risk per
# contract falls as the stop tightens, so size rises — while the probability
# of being hit rises too. In the limit stop -> 0, size -> the budget cap and
# P(hit) -> 1, so EXPECTED LOSS CONVERGES ON THE WHOLE RISK BUDGET WITH
# CERTAINTY. Between 10:14 and 10:25 ET the Breakout took five setups whose
# structural stop sat INSIDE a single 1-minute bar (0.075, 0.050, 0.190,
# 0.225, 0.010 against a MEASURED median 1m range of 0.4188) at 55-235
# contracts and about $10,000 each, for -$3,089.
# 🔑 THE OPERATOR'S MODEL IS RIGHT AND THIS IS ITS MISSING PRECONDITION:
# *"the extreme of the impulsive candle is close to the boundary, it creates a
# very small risk to the operator so we scale up"* — true ONLY while the stop
# is outside the noise. Inside it, tighter is not safer; it is a coin flip at
# maximum size.
# ⚠️ §36 FEASIBILITY, NOT SELECTION. Same shape as the ATR floor: a setup
# whose stop the tape crosses routinely within one bar cannot pay, however
# good it looks. NEVER RELAXED.
# ⚠️ 0.5x IS ARGUED FROM THE MECHANISM, NOT FITTED TO P&L. Price must travel
# back to the impulsive candle's extreme to stop the trade out; below half a
# typical bar's range one ordinary bar does it. The P&L-optimal value on
# 2026-09-22 was 0.60x, and it is DELIBERATELY NOT USED — that is eleven
# closed trades, and §12 says one session finds a mechanism, never a number.
# ── r97 — DO NOT FIRE DIRECTIONALS INTO A PIN YOU ARE STANDING ON ─────────
# 🔑 THE OPERATOR'S HYPOTHESIS, IN HIS WORDS 2026-09-22: *"don't fire
# directionals into pinning GEX with price w/in EM to the pin"*, and his
# ruling on how it ships: *"I want my idea implemented on trial, not as an
# observer, but as a participant."*
# 🔑 THE MECHANISM IS DEALER GAMMA. Positive net GEX means dealers are LONG
# gamma: they sell rallies and buy dips to stay hedged, so price mean-reverts
# toward the pin. That dampening is strongest NEAR the pin — which is exactly
# where a directional debit needs follow-through and cannot get it.
# 📊 MEASURED on 36 directional fires, 2026-09-22: winners sat a median 0.414
# of an EM from the pin, losers 0.342. Refusing below 0.32 turns the day from
# -$904 to +$4,606 by declining 9 trades worth -$5,511.
# ⚠️ AND IT IS A PLATEAU, NOT A POINT — 0.30/0.32/0.34/0.36 all improve the
# day (+1,222 / +4,606 / +2,250 / +2,898). A gate that works at one threshold
# only is a curve fit; one that works across a band is a mechanism.
# 🔴 THE HONEST LIMIT, STATED BEFORE IT SHIPS: THE PIN WAS 748 ON ALL 36
# TRADES. It never moved, so on this session `|pin-px|/EM` is price rescaled —
# n=1 on the quantity doing the work, not n=36. §12 says one session finds a
# MECHANISM and never a NUMBER. This ships REFUSING anyway, by the operator's
# ruling and the fork's charter; §31's log-only default is overridden
# deliberately and knowingly, not by omission.
# ⚠️ GATED ON `PINNING` ONLY. Negative gamma should INVERT this — dealers
# amplify instead of dampening — so the refusal must never fire in a TRENDING
# regime. That inversion is the corpus test worth more than the filter.
# ⚠️ §36 SELECTION, not FOUNDATIONAL: it is a measured preference about when a
# break pays, so it is relaxable and dial-able by env without a revision.
PIN_PROXIMITY_ACTIVE   = os.environ.get("OT_PIN_PROXIMITY_ACTIVE", "1") == "1"
PIN_PROXIMITY_MIN_FRAC = float(os.environ.get("OT_PIN_PROXIMITY_MIN_FRAC", "0.32"))

NOISE_FLOOR_BAR_MULT      = float(os.environ.get("OT_NOISE_FLOOR_BAR_MULT", "0.5"))
NOISE_FLOOR_LOOKBACK_BARS = int(os.environ.get("OT_NOISE_FLOOR_LOOKBACK_BARS", "60"))
# r141 — the fewest SESSION bars the floor is measured from. Was a hard 10 in
# main.py, which disarmed the gate for the first ~5 minutes of every ORB window.
# 3 bars (09:33) is the least a median means anything; below it the gate still
# stands down loudly, exactly as r93 specified for "cannot measure".
NOISE_FLOOR_MIN_BARS      = int(os.environ.get("OT_NOISE_FLOOR_MIN_BARS", "3"))

# ── BREAKOUT RESEARCH POSTURE (OTV4TEST r55, operator 2026-09-19) ────────────
# *"Have it trade every break that gets a 1-minute candle acceptance beyond the
# boundary, stop distance is the extreme of the impulsive candle that registered
# the break, sized the same as the orb, informers are just observers for 2
# weeks."*  And: *"Make it follow the orb structurally, but without a retest."*
# 🔑 THE BARS LISTED HERE ARE EVALUATED AND RECORDED BUT DO NOT BLOCK. Each one
# still writes the verdict it WOULD have given, beside the trade's outcome —
# that counterfactual arm is the only thing that makes a later fit possible,
# because a gate you never let refuse can never be shown to have been right.
# 🔑 WHY THIS EXACT SET: the operator's invariant is that *"if we do get an orb
# trade a breakout trade should've preceded it, because it's the same trade but
# without the retest."* That holds only while Breakout's binding bars are a
# SUBSET of the ORB's. The ORB has no width band, no level-cleanliness rule, no
# pool rule and no R floor — so every one of those must observe, or an ORB trade
# could fire that Breakout had refused, and the two would have silently diverged.
# What is left binding is the window, the 1m acceptance, and whether the trade
# can physically be placed — which IS the ORB, minus the retest.
# 🔑 ONE DATE IS THE WHOLE SWITCH. Until it passes, every informer's acceptance
# reads "any" — each is still a DECLARED TRIGGER the plan must clear, and the
# band is what is wide. After it, each dial takes the number the data gives.
# ⚠️ THE CODE FAILS CLOSED: an unreadable or absent date means the fitted dials
# bind, never that everything is accepted. A research posture that quietly
# becomes permanent is this repo's oldest failure shape; this one cannot.
# ⚠️ AND NO DIAL IS PINNED HERE. An earlier cut of r55 set BRK_R_FLOOR=0.0 to
# force acceptance, which would have left Breakout with NO R floor FOREVER —
# the research posture leaking into the fitted value it is supposed to restore.
# The window widens acceptance; it never edits a dial.
# r188 (2026-10-03): EXTENDED from 2026-10-03 by the operator's ruling - the dials were never fitted and
# depth_thin had no data. The dials are fitted only after a conversation with him that opens with each
# informer's data coverage (BACKLOG BRK.5).
BRK_RESEARCH_UNTIL = os.environ.get("OT_BRK_RESEARCH_UNTIL", "2026-10-30")

# ── r44 — HOW WIDE THE THESIS LINE IS ──────────────────────────────────────
# 🔑 A LEVEL IS PRECISE TO ABOUT ONE BAR OF NOISE, and the thesis test used to
# assert it to the cent. 2026-09-18: the hunt's line was 718.50, a bar closed
# 718.57 — SEVEN CENTS — the thesis was declared dead, and price then fell 2.68
# points. The median 1m wick on this instrument is 0.078, so the trade was
# stopped by an overshoot smaller than one typical bar's wick.
# ⚠️ MEASURED FROM THE TAPE, never a fixed cent amount — the same ruling r39
# reached for the zone width, where percent-of-spot spanned four-fold across
# instruments while the wick ratio held.
THESIS_BAND_WICKS    = float(os.environ.get("OT_THESIS_BAND_WICKS", "1.0"))
THESIS_BAND_LOOKBACK = int(os.environ.get("OT_THESIS_BAND_LOOKBACK", "60"))

# ── r44 — HOW MUCH OF THE GAIN THE TRAIL KEEPS ─────────────────────────────
# 🔴 THE OLD FLOORS WERE FRACTIONS OF PREMIUM (0.75 and 0.80), WHICH CAN SIT
# BELOW ENTRY. At the +20% arm threshold an 80% lock floors at 0.96 of entry:
# arming the trail could guarantee a loss.
# MEASURED ON S3, 210 trail-exited fleet trades 2026-08-01..2026-09-18:
#   MFE gain median +34.0% · realised median +14.0% · CAPTURE median 42.9%
#   and 10 of 210 (5%) finished NEGATIVE with the trail armed.
# A gain floor — entry + L x (peak - entry) — is >= entry by construction, so
# those ten become impossible rather than rare.
# ⚠️ 0.50 IS THE CONSERVATIVE END. The simulation favoured 0.60-0.70, but a
# higher floor exits EARLIER and can cut off MFE the trade only reached later,
# so those rows are an upper bound. 0.50 beats the current median (17.0% vs
# 14.0%), matches its mean, and zeroes the negatives.
TRAIL_GAIN_LOCK = float(os.environ.get("OT_TRAIL_GAIN_LOCK", "0.50"))

# 🔑 WHETHER IT WAS SET, NOT JUST WHAT IT IS. The default FAILS CLOSED, so a box
# nobody configured trades small rather than large — right, but it makes an
# unconfigured box look like a BROKEN one: 1-lot SPX reads as a defect, not as
# a config gap. Operator sets this per underlying ($3–5k), so the common case
# is explicit and the default is the exception that needs announcing. main.py
# logs it at startup and status.py prints it; this flag is how they tell.
ORB_BUDGET_IS_DEFAULT = "OT_ORB_BUDGET_USD" not in os.environ
# DAILY CATASTROPHIC LOSS CAP (r162 name): no NEW entries while the day's NET
# REALIZED P&L is down by this much; open positions are still managed, and
# entries RE-OPEN once closes bring the loss back under it (the operator,
# 2026-09-27). Defaults to one trade's risk; override via OT_DAILY_LOSS_LIMIT.
DAILY_LOSS_LIMIT_USD = float(os.environ.get("OT_DAILY_LOSS_LIMIT", str(RISK_PER_TRADE_USD)))
# v2.0 (runner refinement): the universal directional premium floor, now 40%
# by default. On 0DTE, gamma routinely wicks a healthy trade -25% while the
# thesis (impulsive origin) is intact — the old floor front-ran the structure
# stop and stopped winners on noise. Sizing is FULL-PREMIUM based (risk unit =
# position size), so at $1000 positions a floored trade now costs ~$400 (was
# ~$250) — set OT_DAILY_LOSS_LIMIT with that in mind. Butterflies keep their
# own 25% (their 20%-of-max TP can't carry a 40% stop); condors keep
# CONDOR_STOP_LOSS_PCT. Env-tunable for A/B: OT_MAX_LOSS_PCT=0.25 restores.
# v4.19 (2026-08-19) — TIGHTENED 0.40 -> 0.25 BY OPERATOR DIRECTION. The same
# change ships to options_trader_smc on the same day: the SMC box and this
# fleet are an A/B, and moving the floor on one arm only would make every
# subsequent P&L difference between them unattributable.
# ⚠️ Supersedes the v2.0 reasoning below, which is left intact because it is
# the argument this overrules rather than an error.
# One floored $1000 position now costs ~$250 (was ~$400) — revisit
# OT_DAILY_LOSS_LIMIT with that in mind.
MAX_LOSS_PCT        = float(os.environ.get("OT_MAX_LOSS_PCT", "0.25"))
# r168 — THE RUNAWAY'S FLOOR. Operator, 2026-08-27: the ORB boundary is "a
# terrible stop location … I would prefer (since it's a debit), a decay or
# adverse movement amounting to a 20% loss … The runaway needs room to breathe.
# A few pullbacks in an uptrend are ok." No underlying stop on the runaway.
RUNAWAY_MAX_LOSS_PCT = float(os.environ.get("OT_RUNAWAY_MAX_LOSS_PCT", "0.20"))

# ══ r193 (CFG.1) — THE DIALS THE CODE ALREADY READ FROM HERE, NOW DEFINED HERE ══
# Found by the 2026-10-03 audit: 29 names were read as getattr(config, "NAME",
# <literal>) while config defined none of them, so "retune via config" silently
# took each module's own literal and a typo'd name could never fail. Each is
# defined ONCE here with the value its module was using, and the module reads
# config.NAME with no fallback (r148's rule for the window table). NO VALUE
# CHANGED: tests/check_attr_fidelity.py A4 pins every one.
# Breakout's dials (strategy/breakout.py) - they BIND only after
# BRK_RESEARCH_UNTIL; fitting them is BACKLOG BRK.5 and starts with a
# conversation about each informer's data coverage.
BRK_FLOW_IMBALANCE_MIN      = 0.10
BRK_FLOW_TAGGED_MIN         = 0.60
BRK_REGIME_MAX              = 0.0
BRK_DEPTH_DEPLETION_MIN     = 0.0
BRK_ROOM_MIN_R              = 1.0
BRK_R_FLOOR                 = 1.0
BRK_RANGE_MIN_PCT           = 0.0023
BRK_RANGE_MAX_PCT           = 0.0350
BRK_RANGE_CLEAN_MAX         = 0.0
# The GEX pin butterfly (strategy/gex_pin_butterfly.py). The ATP fly's own
# floor is ATP_BFLY_PIN_CONC_MIN below; this is the pin fly's 0.25.
GEX_BFLY_PIN_CONC_MIN       = 0.25
GEX_BFLY_EM_MIN_FRAC        = 0.30
GEX_BFLY_EM_MAX_FRAC        = 1.00
GEX_BFLY_SMOOTH_WINDOW      = 12       # ticks (~3 min)
GEX_BFLY_PERSIST_TICKS      = 8        # ticks (~2 min)
HANDOFF_TTL_TICKS           = 8        # execution/handoff.py
# Runaway (strategy/runaway_continuation.py, strategy/runaway_plan.py)
RUNAWAY_ATR_FLOOR_PCT       = 0.08
RUNAWAY_ATR_VETO_PCT        = 0.05
RUNAWAY_ATR_DEEP_PCT        = 0.20
RUNAWAY_DELTA_NEAR          = 0.25
RUNAWAY_DELTA_DEEP          = 0.40
RUNAWAY_STRENGTH_GRIND      = 0.40
RUNAWAY_STRENGTH_RIP        = 0.70
RUNAWAY_BAND_GRIND          = 0.5
RUNAWAY_BAND_RIP            = 1.5
# The sweep (strategy/sweep_credit_spread.py, strategy/sweep_plan.py)
SWEEP_CS_MIN_REJECTION_PCT  = 0.0002
SWEEP_CS_ATR_MAX_PCT        = 0.20
SWEEP_CS_LEVELS_EACH_SIDE   = 3
# LiquidityHunt's premium floor. It FOLLOWED Runaway's key through a getattr
# chain nobody could see; it still follows it unless OT_HUNT_MAX_LOSS_PCT is set.
HUNT_MAX_LOSS_PCT = float(os.environ.get("OT_HUNT_MAX_LOSS_PCT", str(RUNAWAY_MAX_LOSS_PCT)))
# execution/position_manager's admission overlay: caps and tries per strategy,
# never a window (r148). None = the table as written. position_manager KEEPS
# its getattr default for this one name: two checkers hand it a stub config
# with no such attribute (the r193 sweep caught my first cut removing it).
ADMISSION_RULES = None

# ── 🔴 r121 — SIZE ON RISK-TO-STOP, NOT ON PREMIUM ───────────────────────────
# Operator, 2026-08-25, reading CVX's card: "it's not 'risking' the correct
# amount. I don't account for max loss on every trade!!!"
# He is right, and the note above admits it in passing: "Sizing is FULL-PREMIUM
# based (risk unit = position size)". So RISK_PER_TRADE_USD has never been a
# risk budget — it is a POSITION-SIZE budget wearing a risk name, and the two
# diverge by exactly the stop.
# ⚠️ MEASURED ON TODAY'S OWN FIRES. Every ORB trade this morning was sized to
# deploy ~$1050 of premium while the -25% floor caps the actual loss near $260:
#   NVDA  $1206 deployed -> stop $4.52 ->  $302 at risk
#   TSLA  $1280 deployed -> stop $2.40 ->  $320 at risk
#   PLTR  $1400 deployed -> stop $3.50 ->  $350 at risk  (it lost $310)
# A $1050 budget was buying ~$300 of exposure. The CREDIT path never had this
# problem — compute_condor_leg_size divides by (width - credit), which is the
# true max loss because a credit spread genuinely CAN go to full width.
# ⚠️ WHY IT IS OPT-IN, DEFAULT OFF. The stop is SOFT — a premium threshold or a
# 1-min close, evaluated on a 15s tick, not a resting order with the venue. A
# gap or a halt can print through it, and on that path the full premium really
# is gone. Sizing to the stop assumes the stop holds. Turning this on roughly
# 4x's every debit position, which is correct by intent and still a large
# change to make silently: it also interacts with DAILY_LOSS_LIMIT_USD, since
# the same floored trade now costs the full budget rather than a quarter of it.
# Set OT_SIZE_ON_RISK=1 deliberately, with the loss limit re-read first.
SIZE_ON_RISK_TO_STOP = os.environ.get("OT_SIZE_ON_RISK", "0") == "1"

# ⚠️ AND A CEILING ON WHAT MAY BE DEPLOYED TO REACH THAT RISK. Risk-based
# sizing has no natural bound: the tighter the stop, the larger the position it
# justifies, and a stop 10% away mathematically licenses a 10x position. NVDA's
# own 2026-08-25 fire, sized on risk, wanted 10 contracts — $6,030 of premium
# to put $1,510 at risk, and the stop is SOFT, so a gap through it costs the
# $6,030 rather than the $1,510. That is 6x the intended risk on one trade.
# This caps deployment at a multiple of the risk budget: size on risk, but
# never own more than the operator would accept losing outright.
DEPLOY_CAP_MULT = float(os.environ.get("OT_DEPLOY_CAP_MULT", "2.0"))

# ── OPENING RANGE CREDIT SPREAD - ORCS (r203 dials, r204 trade) — PRELIMINARY ──
# The operator, 2026-10-03: "set preliminary dials, then build the plan that
# searches the chain for our trigger components' location on the chain"; "we get
# better than mark or we don't trade it"; then "I want to paper trade it Monday
# ... Call this new one the opening range credit spread ORCS." Each value is
# where the 10-03 studies (X5-X8, QQQ 0DTE, 28 priced sessions) were positive
# in BOTH halves at mid fills. NOT PROVEN - those sessions were calm. ENTRY
# PRICING IS THE HOUSE ENTRY LADDER'S (r206, his ruling), not a dial here. The
# window is ENTRY_WINDOWS["OpeningRangeCreditSpread"] (09:45-10:30).
ORCS_ENABLED         = os.environ.get("OT_ORCS", "0") == "1"   # r249: RETIRED (default OFF); =1 restores the trade; the plan still records
ORCS_SHORT_DELTA_MAX = 0.20       # r207, his ruling: worst day sized to 1,050 and over 80% winning days (X10: 80.4% of 56)
ORCS_MIN_IM_MULT     = 1.0        # r207: at least ONE implied move (ATM straddle) out; 1.25 would push delta 0.20 further than measured
ORCS_WING_USD        = 3.0        # r207: the long leg 3 dollars further out - 3 contracts a side at 1,050, max-loss day about -744
ORCS_MIN_CREDIT      = 0.10       # at the mark; below a dime one cent of slip is over 10%
ORCS_MAX_GAP_PCT     = 0.90       # |overnight gap| %, the one informer that agreed on both samples

# ── SCALE.1 (r234) — WHAT THIS BOX'S CONTRACTS COST AGAINST QQQ'S ─────────────
# The ORCS dials above are QQQ dollars (r207 was priced on QQQ). Measured
# 2026-10-04: an SPX 0DTE contract costs ~7.5x the matching QQQ one (platform
# expected move 7.57 median, 6.2-9.1 across 14 sessions); spot (10.4x) would
# overstate it. One number per box; QQQ is the unit. Re-measured on Saturdays.
CONTRACT_SCALE_BY_INSTRUMENT = {"SPX": 7.5}


def _contract_scale():
    base = CONTRACT_SCALE_BY_INSTRUMENT.get(INSTRUMENT, 1.0)
    raw = (os.environ.get("OT_CONTRACT_SCALE") or "").strip()
    if not raw:
        return base, ("%s default" % INSTRUMENT) if INSTRUMENT in CONTRACT_SCALE_BY_INSTRUMENT else "default"
    try:
        v = float(raw)
    except ValueError:
        v = 0.0
    if v > 0 and v == v and v != float("inf"):
        return v, "OT_CONTRACT_SCALE"
    return base, "OT_CONTRACT_SCALE=%r IGNORED (not a positive number)" % raw


CONTRACT_SCALE, CONTRACT_SCALE_SOURCE = _contract_scale()

# ── SWEEP CREDIT SPREAD (v4.0) ─────────────────────────────────────────────
# Operator's spec, 2026-08-20: *"The only 2 ways I want out of this trade is a
# 15% loss (thesis invalidated) or a session hard close."*
# TIGHTER than the fleet's 0.25, and strategy-scoped rather than a fleet change.
# The thesis is that the swept pool HOLDS as a boundary; a 15% loss on the
# spread means it did not, and there is nothing further to wait for.
SWEEP_CS_MAX_LOSS_PCT = float(os.environ.get("OT_SWEEP_CS_MAX_LOSS_PCT", "0.15"))

# ─── r97 (2026-08-24) — THE SWEEP'S PROTECTIVE WING ──────────────────────────
# ⚠️ AN ENCODING NOBODY CHOSE, AND IT IS FLAGGED RATHER THAN BURIED (SPEC.1).
# `docs/TRADES.md` specifies the sweep's SHORT strike precisely — the nearest
# strike actually pierced — and says NOTHING about the long leg. The strategy
# never built one, so no width was ever needed and none was ever argued for.
# 5 is taken from the rest of the fleet, where every credit vertical uses it:
# TCS_WING_WIDTH_SPX/QQQ = 5, CONDOR_WING_WIDTH_SPX/QQQ = 5. It is a CONVENTION
# I inherited, not a measurement — no study sized the sweep's wing, and the
# operator has not ruled on it.
# ⚠️ IT SETS THE RISK, SO IT IS WORTH ARGUING WITH. Width minus credit is the
# max loss per contract; the 15% stop fires long before that, but the wing is
# what makes the risk DEFINED and what the sizer reads.
SWEEP_CS_WING_WIDTH = float(os.environ.get("OT_SWEEP_CS_WING", "5"))

# ⚠️ NO PROFIT TARGET, DELIBERATELY, AND THIS IS MEASURED. v3's condor
# backtest: on 18 standalone legs a TP@25% turned -$242.77 into -$8.43, and on
# 28 condor legs a TP was WORSE AT EVERY LEVEL. A credit vertical is EARNING
# from decay - closing it early buys back the theta you were paid to hold.
# The exits for this strategy are exactly two: the 15% stop, and 15:45.
SWEEP_CS_TAKE_PROFIT_PCT = None

# ⚠️ AND IT HOLDS TO 15:45, exempt from the 15:40 flatten ladder like every
# credit vertical - `strategy/structure.py` classifies it TREND_PARTICIPATION so
# that routing happens by DERIVATION from persisted columns, not a flag.
# Debit positions keep the ladder because they decay; verticals do not.
BUTTERFLY_STOP_LOSS_PCT = 0.40   # OTV4TEST r24, operator: "Widen it to 40%." (was 0.25)
ATP_BUTTERFLY_ENABLED = os.environ.get("OT_ATP_BUTTERFLY", "0") == "1"   # OTV4TEST r26 (BFLY.6); r187 (ROSTER.1): OFF by default - the operator, 2026-10-02: "Turn off the ATP" (OT_ATP_BUTTERFLY=1 restores it)
ATP_BFLY_AT_PIN_EM_FRAC = 0.30   # ⟨PRIOR⟩ r26: at the pin = spot within this x EM of it
ATP_BFLY_SETTLED_BARS = 15       # ⟨PRIOR⟩ r26: closed 1m bars all within that band
ATP_BFLY_VWAP_STRICT_EM_FRAC = 0.05   # r179 (BFLY.9) route B: NOT TRENDING and the pin within ±this x EM of VWAP, only when route A fails. The operator, 2026-09-30: "Allow a non-pinning ATP if it qualifies on STRICT VWAP & NOT TRENDING", "Route B for VWAP if A fails", and yes to NEUTRAL and to ±0.05 x EM.
ATP_BFLY_PIN_CONC_MIN = 0.15     # r179 (BFLY.9), operator 2026-09-30: "Drop the ATP to .19", then "Actually .15 sounds better". The pin fly keeps 0.25. 0.15 is also the floor data/gex_data.py needs to call the regime PINNING.
GEX_BFLY_VWAP_BAND_EM_FRAC = 0.10   # OTV4TEST r25 (BFLY.5): pin within ±this x EM of today's VWAP waives the conc floor
# Max-loss stop applied to an ADOPTED position (one discovered open at the
# broker on a LIVE restart with no DB plan). Defaults to the same threshold
# every strategy already respects, so an adopted position exits at the same
# "degree of red" our normal stops would have. Long: stop = entry*(1-pct);
# short: stop = entry*(1+pct).
ADOPTED_STOP_PCT    = float(os.environ.get("OT_ADOPTED_STOP_PCT", str(MAX_LOSS_PCT)))
# Master switch for LIVE broker<->DB position reconciliation (adopt / keep /
# phantom-close + v3.6 phantom P&L recovery).
# v1.8: FOLLOWS TRADING MODE by default — flipping to LIVE via configure.sh
# (or any other way OT_PAPER_TRADING=False is set) enables reconciliation
# automatically; nothing extra to remember on go-live. Paper stays OFF (paper
# never reconciles; the DB is truth there). An explicit OT_BROKER_RECONCILE
# =True/False still overrides in either direction — the escape hatch if
# get_open_option_positions() ever needs re-verifying on a live box.
_reconcile_env = os.environ.get("OT_BROKER_RECONCILE", "")
if _reconcile_env in ("True", "False"):
    BROKER_RECONCILE_ENABLED = _reconcile_env == "True"
else:
    BROKER_RECONCILE_ENABLED = os.environ.get("OT_PAPER_TRADING", "True") == "False"
# v3.6: minutes between intraday reconcile sweeps (was hardcoded 30). On top of
# these interval slots, dedicated wind-down sweeps fire at 15:45, 15:50, and a
# final 15:57 pass — the post-flatten truth check (the main loop goes dormant
# at 16:00, so the last sweep must land inside the hard-close window).
BROKER_RECONCILE_INTERVAL_MIN = int(os.environ.get("OT_BROKER_RECONCILE_INTERVAL_MIN", "10"))

# ─── PAPER TRADING ────────────────────────────────────────────────────────────

PAPER_TRADING       = os.environ.get("OT_PAPER_TRADING", "True") != "False"

# ─── VIX / IV THRESHOLDS ──────────────────────────────────────────────────────

VIX_LOW_THRESHOLD           = 15
VIX_ELEVATED_THRESHOLD      = 20
VIX_CRISIS_THRESHOLD        = 30
VIX_BUTTERFLY_DISABLE       = 20
VIX_BUTTERFLY_HALF_SIZE     = 15
VIX_NO_ENTRY_THRESHOLD      = 30
IV_RANK_HIGH                = 50

# ─── SESSION / TIME RULES ─────────────────────────────────────────────────────

TIMEZONE                    = "America/New_York"
RTH_OPEN_ET                 = (9, 30)
RTH_CLOSE_ET                = (16, 0)
HARD_CLOSE_ET               = EOD_SCHEDULE["cross_at"]      # r149: the final cross (was 15:45)
# v3.8: the end-of-day flatten OPENS here and posts mark-limits (re-priced each
# ~15s tick) so positions can close without paying the spread; at HARD_CLOSE_ET
# it crosses unconditionally. An unfilled 0DTE at the bell is an expiry (and an
# assignment on a short leg), not an overnight hold — so the cross is absolute.
FLATTEN_WINDOW_OPEN_ET      = EOD_SCHEDULE["resting_at"]    # r149: the first EOD action (was 15:40)
EOD_RESTING_AT_ET           = EOD_SCHEDULE["resting_at"]
EOD_LADDER_AT_ET            = EOD_SCHEDULE["ladder_at"]
EOD_CROSS_AT_ET             = EOD_SCHEDULE["cross_at"]
ORB_NO_ENTRY_AFTER_ET       = ENTRY_WINDOWS["ORBStrategy"][1]  # ORB-SCOPED: ORB entries valid until 11:30 ET.
                                        #   Also the ARM condition for sweep reversal.
# 🔴 r193 — 11:00 -> 11:30, operator 2026-08-30: "1130 is the cutoff for new
# orb entries or a single attempt runaway that has not yet fired during the
# session." It gates PLACING an order, not an offer already resting.
# 🔑 IT LANDS EXACTLY ON THE DEBIT BLOCK, and that is deliberate rather than a
# coincidence to be tidied later. `_afternoon_debit_blocked` fires at
# `>= DEBIT_DIRECTIONAL_CUTOFF_ET` (11:30) for `long_debit`, ORB declares
# long_debit, and the ORB test is also `>=`. So entries run to 11:29:59 and the
# block takes over at 11:30:00 — no gap, no overlap. If one test were `>` and
# the other `>=` there would be a one-minute hole that only ever showed up as a
# rare fill nobody could explain.
# ⚠️ NOT ONLY A LATER DEADLINE. This constant also sets `entries_expired` and
# EXPIRES the ORB engine from ANY state (orb_engine ~441), and r60 made the
# re-arm check read it too. So the change buys 30 more minutes of breaks,
# retests and RE-ARMS — more attempts per session, not just a later last entry.
# ── AFTERNOON DEBIT BLOCK (2026-08-13, operator's directive) ─────────────────
# "no long contracts in the afternoon unless they're part of a vertical spread
# or a butterfly."  MECHANISM: on 0DTE, an afternoon debit needs a large move
# just to clear decay, and the payability ratio (available move / breakeven)
# falls monotonically from the open in EVERY symbol. Measured cost of the window
# it closes: 10:00 -$8,715 · 11:00-14:00 -$1,539.50 · 13:00 -$4,138 against a
# whole-book +$463 (843 trades, 15 sessions).
# EXEMPT BY DESIGN: IronCondorStrategy (credit verticals) and ButterflyStrategy
# (a debit, but deliberately crafted OTM at a deep discount toward a GEX pin —
# it is the operator's named exception, and its own window already starts 12:00).
# NOT A CUTOFF ON MANAGEMENT: open positions are unaffected, this blocks ENTRIES.
# OPERATOR, 2026-08-13, verbatim: "The only other Long that can fire is either
# part of a butterfly or an iron condor vertical spread from 11 o'clock onwards."
# MEASURED, 843 trades / 15 sessions: open 09:30-10:00 +$10,717.50 against
# 10:00-11:00 -$8,715 and 11:00-14:00 -$1,539.50, on a whole book of +$463.
# ⚠️ THE HOLE THIS LEAVES IS DELIBERATE AND NAMED: in a TRENDING afternoon the
# condor is correctly blocked (it self-gates to RANGING at main.py:1607 and
# cancels Leg 1 on a directional flip) and the butterfly needs PINNING GEX, so
# NOTHING fires. That window belongs to the trend credit spread (TC.6), which is
# NOT BUILT. Until it is, a trending afternoon is dark ON PURPOSE — which is the
# point: the measured cost of that window is negative.
# ── LONG-DEBIT CUTOFF (v4.0) ───────────────────────────────────────────────
# Operator, 2026-08-13: *"The only other Long that can fire is either part of a
# butterfly or an iron condor vertical spread from 11 o'clock onwards."*
# Extended to 11:30 on 2026-08-20 to resolve a contradiction: ORB armed until
# 11:00 while RunawayContinuation - which fires on ORB's OWN state - ran to
# 11:30, so the engine stopped producing the state half an hour before the
# trade depending on it stopped firing.
DEBIT_DIRECTIONAL_CUTOFF_ET = EOD_SCHEDULE["entries_stop"]   # r149: all day; the OT_DEBIT_CUTOFF_ET override is removed

# ⚠️ KEYED ON STRUCTURE, NOT ON A NAME LIST. The v3 version held
# {"ORBStrategy", "ContinuationStrategy", "SweepReversal"} - and by 2026-08-20
# TWO OF THOSE THREE HAD BEEN DELETED while a new long-debit strategy
# (RunawayContinuation) was NOT in the list and would have been silently
# EXEMPT. **An allow-list of names is a policy that rots every time a strategy
# is added or removed, and it rots in the permissive direction.**
# A strategy declares what it BUILDS; the cutoff decides from that.
#   "long_debit"  pays premium and is directional -> BLOCKED after the cutoff
#   "vertical"    credit spread or condor leg     -> always permitted
#   "butterfly"   defined-risk debit              -> the operator's exception,
#                 and it covers BOTH the GEX pin butterfly and the synthetic
#                 butterfly that arises from an aggressive condor roll, which
#                 is a MANAGEMENT step on a live position rather than a new
#                 entry at all
# ── ENTRY OPEN — NO ORDER IS PLACED BEFORE 09:35 ET (r101, 2026-08-24) ──────
# OPERATOR DIRECTIVE, VERBATIM, 2026-08-24: "I want the executing logic running
# as long as the service is up. But one gate that blocks it from placing orders
# until 0935 (orb range established)."
# ⚠️ THE PROVENANCE IS THE POINT, and it is written here because the section
# below is the tombstone of the last global entry gate. GLOBAL_NO_ENTRY_ET was
# an encoding NOBODY CHOSE — a bare dtime hardcoded in v3, promoted to a
# constant by a pass whose own changelog said "NOT a behaviour change", and it
# cost a 15-box session. This one is a dated instruction with a stated reason
# (the opening range is not established until 09:35, so nothing before it can
# be anchored to a range that does not yet exist). A future audit should be
# able to tell the two apart WITHOUT asking.
# ⚠️ IT GATES OPENINGS ONLY. Exits, rolls, inversions and the flatten are NEVER
# gated: a blocked exit is a stuck position, and a restart holding an adopted
# leg must be able to close it at 09:31.
# ⚠️ AND IT IS A FLOOR, NOT A WINDOW. Each structure keeps its own cutoffs
# (ORB 11:00, sweep 14:00, TCS 11:31, the afternoon debit block); this only
# says nothing opens before it.
ENTRY_OPEN_ET = tuple(int(x) for x in
                      os.environ.get("OT_ENTRY_OPEN_ET", "9,35").split(","))

# r478 / DEP.12 — ON AN EARLY CLOSE (13:00), NOTHING OPENS IN THE LAST 90 MINUTES.
# Mainline's operator 2026-10-11 (otv4 r478); THIS repo's, 16:51 ET: "Yes, we want
# those fixed here too". Entries close at the bell minus
# this lead — 11:30 on 13:00 — so ORB (to 11:00) and Runaway (to 11:30) keep
# their windows and the sweep, butterfly and TCS do not open. It also clips the
# TEST boxes' later per-box dials (SPX-TEST Runaway 12:00, QQQ-TEST Breakout
# 15:40) when mirrored. ⚠️ A JUDGEMENT, NOT A MEASUREMENT: no box has ever
# traded a half day. Read ONLY on a listed early close; full days have no
# global entry cutoff (r60).
HALF_DAY_ENTRY_LEAD_MIN = 90

DEBIT_BLOCKED_STRUCTURES = {"long_debit"}
DEBIT_BLOCK_ACTIVE          = os.environ.get("OT_DEBIT_BLOCK_ACTIVE", "1") == "1"

# ⚠️ r60 (2026-08-21): GLOBAL_NO_ENTRY_ET IS DELETED — AN ENCODING NOBODY
# CHOSE. It began as a bare dtime(14, 0) hardcoded in v3's utils/time_utils,
# was promoted to a named constant by the "cutoff disambiguation" pass whose
# own changelog says "NOT a behaviour change", and was ported to v4 intact. It
# vetoed EVERY strategy's entries after 14:00 ET — including the afternoon
# credit window TC.6 exists for — logging only at DEBUG. On 2026-08-21 it was
# one of four stacked locks behind a 15-box zero-trade session. Operator,
# verbatim: "I did not spec any hard 1400 blocks ever." Each structure's own
# operator-set window (ORB 11:00, butterfly cutoff, TCS below, the
# 15:40/15:45 flatten ladder) bounds the day; a redundant global veto is the
# guard-outlives-decision shape this repo keeps finding.
# 🔴 r237 — SET OUT OF REACH ON PURPOSE. OPERATOR, 2026-09-04: *"I don't
# know how TCS has cleared the bar to fire. It looks like I do need it
# disabled."* (00, 00) makes `(now.hour, now.minute) >= TCS_ENTRY_END_ET` true
# at every tick of every session, so TCS goes DORMANT at its FIRST gate —
# before a chain is read, before a strike is chosen, before anything is priced.
#
# 🔑 WHY THIS CONSTANT AND NOT A QUALITY BAR. Raising `R_FLOOR_STOP` or
# `TCS_MIN_POP` would also stop it, and would LIE about why: the plan board
# would read `wing_r_best FAIL` forever and the next reader would spend a
# session working out why UNH never clears R. A closed window is the truth —
# the strategy is parked, not out-priced. And this constant is TCS-ONLY;
# `TCS_START_ET` is pinned equal to `CREDIT_ENTRY_START_ET` by
# `check_entry_windows`, so touching THAT would have moved the sweep too.
#
# ⚠️ BELT AND BRACES WITH `OT_TCS_ACTIVE=0`, which is already in a systemd
# drop-in on all 15 boxes (verified 2026-09-04 11:47, 15/15). The env flag
# dies with the drop-in file; this survives in the repo.
#
# ⚠️ WHY IT FIRED AT ALL, so the rewrite does not re-derive it: r234 moved R
# to the stop basis and TCS cleared it HONESTLY. UNH sold 398/402 for $0.84 —
# credit/width 21.0% against a 13.04% bar, r_stop 1.77. My "TCS still fails"
# note was measured on SPX and QQQ at 0.04-0.09 and I let it stand for the
# fleet; UNH is a different chain and sails through. The gate was right; the
# trade behind it should not have been taking the offer.
#
# ⚠️ AND IT CHURNED: 11:40, 11:42 and 11:42 on identical strikes, closing at
# -$2.00, -$2.00, -$0.00. TCS has NO re-entry latch of any kind — no
# `order_placed`, no confirmation sequence — the same shape r235 fixed for the
# ORB, which TCS never had. And `exit=breach@397.07` is the ORB LOW, the very
# bound it anchors its short strike to, so price sitting ON the boundary makes
# it enter and exit on alternating ticks. TCS.7 in BACKLOG holds the rewrite.
#
# The original note, still true and now acted on:
# 🔴 r238 — SPEC'D AT LAST. Same number it always held, DIFFERENT STATUS:
# (14, 0) was inherited verbatim from a deleted global cutoff and config called
# it PROVISIONAL and INERT, "operator specs TC.6's real v4 window before any
# activation". Operator, 2026-09-04: *"No new positions after 1400, but condor
# management is allowed until the flatten."* Chosen, not inherited.
# ⚠️ MANAGEMENT IS NOT GATED BY THIS AND NEVER WAS — `condor_roll` and
# `management.py` reference no window constant at all; they gate on having legs
# and run to the 15:45 flatten. Verified, not assumed.
# ⚠️ AND THE STRATEGY IS STILL HELD BY `OT_TCS_ACTIVE=0` in the systemd
# drop-in on all 15 boxes. Restoring the window does NOT unpark it; clearing
# that flag is a separate, deliberate act.
# 🔴 r81 — DERIVED FROM THE ONE CREDIT END (was a literal (14, 0)). The TCS is
# a CREDIT vertical and r71's ruling covers it; tcs_plan.py:285 was stamping
# "past TCS_ENTRY_END_ET 14:00 — observing only" while admission said 15:40.
# ⚠️ DEFINED BELOW, BESIDE `CREDIT_ENTRY_END_ET`, because it is DERIVED from it
# and that constant does not exist yet at this point in the file. Left here as
# a pointer rather than as a second literal — repeating the number is the
# defect r81 exists to remove. See "THE ONE CREDIT END" further down.
_TCS_ENTRY_END_ET_NOTE      = "derived below from CREDIT_ENTRY_END_ET (r81)"  # was
                                        #   end, inherited verbatim from the
                                        #   deleted global cutoff so behaviour
                                        #   is unchanged while TCS is OFF.
                                        #   Operator specs TC.6's real v4
                                        #   window before any activation.
BUTTERFLY_ENTRY_CUTOFF_ET   = (14, 0)   # gates NOTHING since r209 (its session_guard branch could never run and is deleted); ENTRY_WINDOWS bounds the flies
# 🔴 NOON, AND IT IS NOW ACTUALLY IN FORCE (r142). Operator, 2026-08-26:
# *"Butterfly is debit & any sooner than noon to reach a pin is unlikely to
# hold all the way to the closing bell."*
# ⚠️ THIS CONSTANT WAS READ BY NOTHING IN PRODUCTION — only by a test harness.
# The live gate was `gex_pin_butterfly.EARLIEST_ET`, a getattr DEFAULT of
# "11:00" whose key did not exist in this file, so the butterfly would have
# opened a full HOUR before the rule the operator just stated. Same shape as
# SWEEP_CS_EARLIEST_ET: a default is the only source, and the config value
# everyone reads is decorative.
BUTTERFLY_ENTRY_START_ET    = ENTRY_WINDOWS["GEXPinButterfly"][0]   # No butterfly entries before noon
GEX_BFLY_EARLIEST_ET        = f"{BUTTERFLY_ENTRY_START_ET[0]}:{BUTTERFLY_ENTRY_START_ET[1]:02d}"
# r147 — UNPARKED. Operator, 2026-08-26: "I want it active. It already has to
# clear a high bar to fire." OT_GEX_BUTTERFLY=0 parks it again.
GEX_BUTTERFLY_ENABLED       = os.environ.get("OT_GEX_BUTTERFLY", "1") == "1"
GEX_BFLY_WING_EM_FRAC       = float(os.environ.get("OT_GEX_BFLY_WING_EM_FRAC", "0.25"))  # ⟨PRIOR⟩
# ⚠️ THE DEBIT CUTOFF, ALSO A DEFAULT-ONLY VALUE UNTIL NOW. 11:30 is correct
# and load-bearing: the credit start is 11:31, so this is the one minute of
# daylight between the two. Defined here so the pair cannot drift apart.
RUNAWAY_CUTOFF_ET           = _hhmm(ENTRY_WINDOWS["RunawayContinuation"][1])
HUNT_CUTOFF_ET              = ENTRY_WINDOWS["LiquidityHunt"][1]        # r148: read by liquidity_hunt; never existed before
BREAKOUT_LATEST_ET          = _hhmm(ENTRY_WINDOWS["Breakout"][1])      # r148: read by breakout; never existed before
BREAKOUT_EARLIEST_ET        = "%02d:%02d" % ENTRY_WINDOWS["Breakout"][0]  # r148: never existed; zero-padded "09:35" exactly as the literal was
GEX_BFLY_LATEST_ET          = _hhmm(ENTRY_WINDOWS["GEXPinButterfly"][1])  # r148: read by gex_pin_butterfly; never existed before
ORB_WINDOW_MINUTES          = 5

# ─── ORB STRATEGY ─────────────────────────────────────────────────────────────

# OTV4TEST r2 — ORB_MAX_RETEST_BARS deleted; the stale-retest timeout is gone.
ORB_TP_MULTIPLIER           = 1.0

# ─── r95 (2026-08-24) — THE RESTART TAPE REACH-BACK ──────────────────────────
# How many 1-minute bars `orb_engine.rebuild_from_tape()` asks for when it
# replays the session after a restart.
#
# ⚠️ IT CANNOT USE ctx["df_1m"], AND THAT IS THE WHOLE REASON THIS CONSTANT
# EXISTS. `TIMEFRAMES["1m"]["candles"]` is 60, so the cached trigger frame is a
# 60-bar ROLLING WINDOW: at 10:37 it begins at 09:37 and cannot see a 09:40
# break at all. That left edge is the same trap that made `_opening_range`
# structurally dead every session until TCS.3, and it would have made this
# reach-back look like it worked while quietly failing on exactly the late
# restarts it exists for.
#
# 420 = an RTH session (390 minutes) with margin, so the frame reaches 09:30
# from any point in the day. `fetch_candles` scopes intraday frames to the most
# recent session, so a larger number cannot drag in yesterday's tape — it only
# costs a slightly wider read on the ONE tick per session that replays.
ORB_REBUILD_1M_BARS         = 420


# ─── r95 (2026-08-24) — CASH INDICES HAVE NO TIME-AND-SALE TAPE ──────────────
# A cash index is a CALCULATED VALUE, not a traded instrument: there is no
# order flow in SPX itself, so DXFeed has no TimeAndSale to send and the
# `prints` table on an index box is empty BY CONSTRUCTION. That is not an
# outage and it is not an entitlement gap — it is the instrument.
#
# 🔴 THIS IS A DISPLAY FACT, NOT A SUBSCRIPTION RULE. Operator's standing
# instruction, 2026-08-24: **"DO NOT unsubscribe to ANYTHING. You can choose
# not to write it or not to display it, but we subscribe to EVERYTHING,
# period."** That is `docs/FEED_MANIFOLD.md`'s governing rule — capture
# everything the wire offers, give it a home, let consumers subscribe — and an
# unsubscribe is unrecoverable in a way a suppressed bulb is not: DXFeed
# history is same-evening only, so a stream nobody wanted today cannot be
# fetched back tomorrow. `candle_feed` still subscribes TimeAndSale on every
# symbol including indices. This constant is read ONLY by the health board.
#
# ⚠️ WHY THE BOARD NEEDS IT. Before this, SPX's manifold board painted
# `prints (T&S)` RED every session, forever, for a reason no operator action
# could ever clear. A board carrying a permanent red teaches the reader to skim
# past reds — precisely the failure the board was built to prevent
# (WORKING_AGREEMENT 17). A permanent red is worse than no bulb at all.
#
# ⚠️ THIS SET IS ABOUT THE TAPE ONLY. It says nothing about `Underlying` or
# `TheoPrice` on an index — those are option-chain events an index legitimately
# has, and whether they arrive is an ENTITLEMENT question this constant has no
# business answering. Conflating "cannot exist" with "did not arrive" is the
# exact error the manifold board exists to avoid.
CASH_INDEX_SYMBOLS = {"SPX", "XSP", "VIX", "NDX", "RUT", "DJX", "SPXW"}


def is_cash_index(symbol: str = None) -> bool:
    """True when `symbol` is a cash index with no time-and-sale tape.

    Read by `tools/manifold_health.py` to render `prints` as n/a rather than
    RED. NEVER used to skip a subscription — see the block above.
    """
    sym = (symbol if symbol is not None else INSTRUMENT) or ""
    return sym.strip().upper().lstrip("$") in CASH_INDEX_SYMBOLS

# MEAS.3 — FED_DAY_ORB_BOOST (0.20) REMOVED: a Fed day changes no trading (operator, 2026-10-03).

# including UNKNOWN and SWEEP_REVERSAL. The ORB engine's break+retest is self-
# validating (the classifier does not even test for it), so the label is not
# consulted for the go/no-go; only the setup scorer's B-threshold and the ORB
# simply contributes 0 to the score. Under SWEEP_REVERSAL, ORB wins (the engine
# no longer defers its OPEN to the sweep). Set False to restore strict v2 gating
# (UNKNOWN/sweep block ORB). Every ORB that fires under UNKNOWN is logged with
# v4.19 (2026-08-19) — ORB IS BLOCKED UNDER RANGING (operator: the conclusive
# decision stays readable, is reversible by env, and the refusal can be
# JOURNALED — "ORB did not set up" and "ORB was forbidden" must not look the
# same in the record.
# assigns: the RANGING block could never fire, and the second was hardcoded
# True so it never contributed a term to anything. OT_ORB_BLOCK_RANGING is now
# INERT — stated here so nobody spends an evening looking for its reader.
# When snapping an ORB strike target to the nearest available strike, break
# toward the "higher" (more ITM / participation) or "lower" (further OTM) delta.
ORB_STRIKE_DELTA_BIAS       = "lower"

# ─── SWEEP REVERSAL STRATEGY ──────────────────────────────────────────────────

# Sweep OTM strike delta scales INVERSELY with reversal strength (conviction):
# a strong snap-back can carry a far-OTM (low-delta) strike ITM for max leverage;
# a weak move needs a nearer, higher-delta strike to actually participate.
SWEEP_DELTA_STRONG          = 0.12   # conviction -> 1.0 : leveraged but REACHABLE
SWEEP_DELTA_WEAK            = 0.30   # conviction -> 0.0 : near-ATM, participation
SWEEP_DELTA_TOLERANCE       = 0.04   # acceptable band around the target delta

# The trade required the committed L2 label to be SWEEP_REVERSAL, a label that
# wins 0.4% of live ticks and is exactly 0 on 96% of them, so the trade was
# effectively off. It now gates on the L1 _sweep SETUP SCORE instead.
#
# WHY A LOW FLOOR IS THE CORRECT READING OF THE SPEC, not laziness: _sweep's
# THREE HARD VETOES are veto_loc (a NAMED level), veto_reclaim (rejected back
# through it) and veto_accept (not accepted beyond). All three must pass for the
# score to be non-zero at all — which is precisely "a move into a named
# liquidity pool accompanied by a rejection". Every non-zero tick therefore
# ALREADY qualifies; magnitude above zero is quality grading, not qualification.
#
# Corpus, 19 sessions / 523 symbol-days: non-zero on 4.0% of ticks; of those
# p50=0.016, p90=0.154, max=0.717. This floor admits the top ~29% of non-zero
# ticks (78 symbol-days, ~28 ticks/symbol-day before the strategy's own cooldown
# and position checks collapse them into far fewer entries).
#
# A PRIOR, NOT A FIT — deliberately permissive for the collection phase and
# meant to be TIGHTENED once live fires exist. The corpus can say how OFTEN a
# floor admits; it cannot say whether those are good trades.
# Permissiveness cannot steal from other setups: sweep is Priority 2.5 behind
# `if signal is None`, so ORB and Continuation always get first refusal.
SWEEP_SETUP_FLOOR = float(os.environ.get("OT_SWEEP_SETUP_FLOOR", "0.05"))

# ── SWP.2 — SWEEP SHORTS GET THEIR OWN, HIGHER FLOOR (2026-08-07) ─────────────
# Long and short sweeps are not the same trade and the data says so on THREE
# independent measures over 12 sessions:
#   Sweep Reversal Long   27 trades · 81% WR · +$2,844 · 4% never-favourable ·
#                         forward drift BUILDING +0.001 → +0.081 → +0.314 with
#                         52% → 56% → 67% of trades positive
#   Sweep Reversal Short   6 trades · 33% WR · −$1,403.50 · 33% never-favourable ·
#                         drift −0.148 → −0.215 → −0.290, 33% positive
# n=6 is THIN and this is NOT a fit — it is a PRIOR, and what earns it is that
# the MECHANISM agrees: the 2026-07-27 PLTR incident was exactly a short
# reversal into a +7.2% up-trending tape, which is why `trend_opp` exists.
#
# ⚠️ SAY THE HONEST THING ABOUT THIS NUMBER: SWEEP's score is CAPPED near 0.265
# (measured max on the 08-07 replay; it is the only scorer with an age-decay
# soft-necessary, half-life 3 bars). A short floor of 0.20 therefore fires only
# in the top sliver of sweep scores and NEAR-DISABLES shorts. That may well be
# correct at −$233/trade — but it is a near-disable wearing a threshold, and it
# should be read that way rather than as a tuning dial.
# Longs are untouched at 0.05. Set equal to SWEEP_SETUP_FLOOR to restore the
# single-floor behaviour.
SWEEP_SETUP_FLOOR_SHORT = float(
    os.environ.get("OT_SWEEP_SETUP_FLOOR_SHORT", "0.20"))

# ── CNT.3 — THE HANDOFF DOES NOT FIRE UNDER COMPRESSION (2026-08-07) ──────────
# COMPRESSION/Continuation is 39 trades, 28% WR, −$454, and COMPRESSION is the
# WORST never-favourable cell in the book: 80% (LIFT 1.98, n=45).
# Continuation cannot enter on a compression LABEL — the direction branches
# require TRENDING_BULL/BEAR or BREAKOUT — so all 39 of those are RUNAWAY
# HANDOFFS, which ignore the label by design.
# THE MECHANISM IS A CONTRADICTION: a runaway asserts EXPANSION while the label
# asserts COILING. The handoff's licence to ignore the label is what makes it
# valuable after a real runaway; this is the one place it clearly costs.
# OT_CONT_HANDOFF_IN_COMPRESSION=1 restores the old behaviour.
CONT_HANDOFF_BLOCK_COMPRESSION = os.environ.get(
    "OT_CONT_HANDOFF_IN_COMPRESSION", "0").strip().lower() in ("0", "false", "no", "off")
# ⚠️ OTV4TEST r18 — THIS CONSTANT HAS NO READERS IN THE TREE. Verified
# 2026-09-13: the live pierce bands come from SWEEP_CS_MAX_REJECTION_PCT below,
# which until r18 was NOT DEFINED ANYWHERE and therefore ran on the getattr
# default in derived/levels.py. Two similarly-named values, one live and unnamed
# and one named and dead, is how the predecessor shipped a threshold 15x off.
# Left in place as a stated prior, NOT a policy (the r231 precedent) — but it is
# labelled now, so the next reader does not tune the one nothing reads.
SWEEP_MIN_REJECTION_PCT     = 0.003
# OTV4TEST r18 — DEFINED AT THE VALUE THAT WAS ALREADY RUNNING, so this
# changes no behaviour; it makes the knob real. derived/levels.py reads it for
# the shallow band and takes 3x for the deep band.
SWEEP_CS_MAX_REJECTION_PCT  = 0.0025
# OTV4TEST r18 — CLOSED 1m BARS beyond a level before it retires
# ACCEPTED_THROUGH. Operator ruled two 5m bars out ("10 minutes leaves us
# nothing actionable"); on 1m closes the same 2 is TWO MINUTES. Drop to 1 for a
# faster, looser acceptance without a redeploy.
LEVEL_ACCEPT_CLOSES         = 2
SWEEP_MAX_AGE_BARS          = 8
# Entry-window tuning (separate pass from detection). The recovery window is now
# ATR-aware: a fast reversal on a volatile name that has already moved isn't
# rejected as "too far" — the window is the LARGER of a floor % or a multiple of
# ATR%. BOS lookback is configurable and also accepts a BOS that printed on the
# just-closed candle (so a 1-tick-late evaluation doesn't miss it).
SWEEP_MAX_RECOVERY_PCT      = 0.02   # floor recovery window (fraction of sweep price)
SWEEP_RECOVERY_ATR_MULT     = 1.5    # ...or this × ATR%, whichever is larger
SWEEP_BOS_LOOKBACK          = 5      # 1m candles used as the BOS structure reference

# ─── BUTTERFLY STRATEGY ───────────────────────────────────────────────────────

# r169 — RETIRED FROM THE DECISION PATH (exit_engine v4.8). Operator: "1545
# flatten or 25% loss. Whichever comes first." Kept so target_premium() still
# prices the record's informational target; nothing acts on them.
BUTTERFLY_TP_PCT            = 0.20   # informational only (r169)
BUTTERFLY_MAX_HOLD_MIN      = 150    # not read by any exit (r169)

# Fixed wing widths by instrument
BUTTERFLY_WING_SPX          = 25     # 25-point wings on SPX
BUTTERFLY_WING_QQQ          = 5      # $5 wings on QQQ/SPY

# GEX pin proximity gate: price must be within 1x expected move of pin
# Formula: underlying × VIX% × sqrt(hours_remaining/6.5) / sqrt(252)
# Computed at runtime in butterfly_strategy.py
BUTTERFLY_GEX_PIN_PROXIMITY_MULT = 1.0  # Multiplier on expected move

# ─── IRON CONDOR STRATEGY ─────────────────────────────────────────────────────
# Strike selection is BOLLINGER-BAND ANCHORED — there is NO delta anywhere in the
# condor path (short call = lowest liquid strike at/above the BB upper band; short
# put = highest liquid strike at/below the BB lower band). Delta is deliberately
# excluded: it is relative to where price sits, not to the actual range boundary.
# The expected-move guardrail is a sanity check only, not a parallel sizing method.

CONDOR_WING_WIDTH_SPX       = 5      # Narrow wings — affordable verticals (was 25)
CONDOR_WING_WIDTH_QQQ       = 5      # Fixed wing width in points on QQQ/SPY
CONDOR_EXPECTED_MOVE_GUARDRAIL_MULT = 1.2  # Short strikes must be within this x EM
CONDOR_EM_FLOOR_FRAC = 0.80   # short strike must sit >= this * expected_move from spot
CONDOR_PROXIMITY_STRIKES    = 2      # (legacy) strikes inside the short — superseded by CONDOR_TRIGGER_APPROACH
# Fraction of the distance from the BB midline to each short strike that price
# must travel before that side's spread fires. Higher = price must get closer
# to the band before selling (richer premium, fewer fills). Env-tunable for A/B.
CONDOR_TRIGGER_APPROACH     = float(os.environ.get("OT_CONDOR_TRIGGER_APPROACH", "0.65"))
                                     # (2 strikes = 10pt on SPX, $2 on QQQ — scales naturally)
# 🔴 r106 — THE LONE-VERTICAL FLOOR IS 15%, AND IT IS THE ONLY NUMBER WRITTEN.
# TRADES.md §5: a vertical alone "manages exactly like the sweep credit spread:
# a 15% stop", and names the 25% as "never validated ... calibrated for a
# complete structure collecting credit on both sides — not for one naked leg"
# (condor_stop measured 16 trades, 19% win, −$1,156, worst −$300).
# ⚠️ THE 25% WAS STILL BEING WRITTEN ONTO EVERY ROW as stop_premium while the
# LIVE arm evaluated 15% — so the row, the entry alert and any audit reading
# either of them stated a rule the engine no longer applied.
CONDOR_LONE_STOP_PCT        = float(os.environ.get("OT_CONDOR_LONE_STOP_PCT", "0.15"))

# ── THE TENT (r106, operator 2026-08-24) ────────────────────────────────────
# After a roll, a 1-min candle CLOSE beyond a short strike takes the PROFITABLE
# vertical off and buys a long of the OPPOSITE type, equidistant from the
# remaining short as its existing wing — "boxing in" the new price. Operator's
# words: "leaving price under the tent."
# ⚠️ PRICED BEFORE IT IS PAID. If the hedge's debit alone would put the position
# at −TENT_FLOOR_PCT of cumulative credit, the tent is NOT bought and the whole
# structure closes. A tent that cannot be afforded is a close.
# ⚠️ AND THEN ONE EXIT. A 15% floor on CUMULATIVE credit — the original credit
# plus every roll, minus the hedge debit — and nothing else. No TP, no trail,
# no nickel: those belong to a vertical that is still collecting decay, and this
# structure has already been adjusted twice.
TENT_ENABLED                = os.environ.get("OT_TENT_ENABLED", "1") == "1"
TENT_FLOOR_PCT              = float(os.environ.get("OT_TENT_FLOOR_PCT", "0.15"))
CONDOR_STOP_LOSS_PCT        = CONDOR_LONE_STOP_PCT   # retired alias — one number
# ── Condor leg management, v2 (2026-07-23) ────────────────────────────────
# A RATCHET IS NOT A TAKE-PROFIT. A TP closes the position and so structurally
# guarantees the condor never forms: the move that makes side one profitable IS
# the move that carries price to the far band and triggers side two. So before
# the entry cutoff we only ever move the STOP and leave the leg open.
CONDOR_RATCHET_BE_AT        = float(os.environ.get("OT_CONDOR_RATCHET_BE", "0.20"))   # +20% -> stop to breakeven
CONDOR_RATCHET_LOCK_AT      = float(os.environ.get("OT_CONDOR_RATCHET_LOCK_AT", "0.40"))
CONDOR_RATCHET_LOCK_PCT     = float(os.environ.get("OT_CONDOR_RATCHET_LOCK_PCT", "0.20"))
# Hard TP applies ONLY after CONDOR_ENTRY_CUTOFF_ET, when no second leg can
# fire and the structure is definitively dead. Backtest on 18 standalone legs:
# TP@25% turned -$242.77 into -$8.43; 30% was +$14 better = noise; 40%/50% worse.
CONDOR_TP_PCT               = float(os.environ.get("OT_CONDOR_TP_PCT", "0.25"))
# Min hold before the TP is even evaluated — a QUOTE-NOISE filter, not a
# structure mechanism. On a 0DTE spread with a nickel-wide bid/ask a +25% mark
# move can be one tick of noise. Kept modest (10m, not theta's 20m) because
# price moving away from the short strike is a legitimate fast gain (delta).
CONDOR_TP_MIN_HOLD_MIN      = float(os.environ.get("OT_CONDOR_TP_MIN_HOLD", "10"))
CONDOR_NICKEL_CLOSE         = 0.05   # Close leg when spread value decays to $0.05
# 2026-07-23: 11:00 -> 11:11. Bollinger needs BB_PERIOD(20) 5-minute bars, so
# the first valid bb_middle is ~11:05 ET (verified on the 07-22 tape). The old
# 11:00 open meant the first ten minutes of the condor window ran with
# bb_middle == 0, and decide() falls back to `mid = current_price` in that case
# — i.e. strikes and triggers computed with NO volatility reference at all.
# 11:11 clears 11:05 with margin and removes that fallback path entirely.
# ── CONDOR PITCHFORK ANCHOR (2026-08-13, operator directive) ─────────────────
# "The tine should be the trigger for 'rich premium' and the short strike should
#  be just outside the range of the rail at the most liquid strike where price
#  has still not exceeded... consider the condor off the table if we don't have
#  guardrails. That is the insurance policy that eliminates a bad decision in an
#  unpredictable session."
# DAILY fork, deliberately: "It's a guardrail, not the road." A daily fork is
# invalidated only by DAILY closes, so an intraday session cannot kill it — the
# rail a spread was sold against is still there while the spread is open. The
# hourly fork has a measured p50 lifetime of 5 bars and a k=3 confirmation lag,
# so it can be born mid-window and dead before the close: that re-anchors
# intraday, which is another indicator, not a guardrail.
# NO FORK -> NO CONDOR. Accepted volume cost, operator's call: "I'm ok with not
# getting the condor if the fork isn't there."
CONDOR_PITCHFORK_ANCHOR     = os.environ.get("OT_CONDOR_PF_ANCHOR", "1") == "1"
CONDOR_REQUIRE_FORK         = os.environ.get("OT_CONDOR_REQUIRE_FORK", "1") == "1"
# v4.1 (2026-08-21) — default was "daily", but the fork cache is keyed on the
# FRAME names "1d"/"1h". `rails_for` got None for every lookup and the condor
# stood down on every box, every session, reading as the guardrail policy
# working. Default is now the frame key; legacy spellings are normalised in
# pitchfork_observer._norm_tf so a stale env var cannot re-break it.
# 🔴 OPERATOR RULING 2026-08-22 — **1h, OR NO CONDOR.**
# The daily fork demands an excursion from one anchor to the next that a single
# session rarely meets — "too extreme of a measurement" — so a daily anchor
# produces a PERMANENT no-trade rather than a guardrail.
# ⚠️ THIS SUPERSEDES the earlier "DAILY by operator ruling" recorded at
# main.py::_condor_rails, which is rewritten in this same commit. Do not
# restore "daily" from that block: it is the older decision.
# ⚠️ AND r59 SET THIS TO "1d", WHICH WAS ALSO WRONG. The original "daily"
# never resolved (the cache keys on "1d"/"1h"), so r59 fixed the resolution and
# guessed the frame. Availability settles it independently: 1h is populated
# continuously all session while 1d appears ~once a day and was ABSENT ENTIRELY
# from the warehouse on 2026-08-21.
CONDOR_PF_TIMEFRAME         = os.environ.get("OT_CONDOR_PF_TF", "1h")
# Slope magnitude (fraction of price per bar) below which the fork is treated as
# FLAT and leg order falls back to proximity. A sign alone is not a slope: a
# fork drifting 0.001% a bar is noise, and ordering legs off its sign would be
# reading a coin flip as structure.
CONDOR_PF_FLAT_SLOPE        = float(os.environ.get("OT_CONDOR_PF_FLAT", "0.00002"))

# ── POP FLOOR (2026-08-13, operator directive) ───────────────────────────────
# "Selling late afternoon premium on zero DTE is incredibly risky so just make
#  sure that the factors appear favorable before executing. There should be a
#  reasonable expectation of trade success better than 50-50... somewhere near
#  the 70 to 80% range."  And, on tone: "this approach is already inherently
#  risky. I'm aware of that and I'm comfortable with it so don't be too
#  restrictive."  Hence a FLOOR at the bottom of his band, not the top.
# POP = P(terminal close on the safe side of the short strike)
#     = Phi(z),  z = distance_to_strike / (sigma_per_bar * sqrt(bars_left))
# TIME IS THE POINT: the same distance is a LARGER z late in the session, so a
# strike that fails at 11:15 can pass at 14:30 on identical geometry. A
# fixed-percent rule cannot express that and this is why the offset tables were
# time-blind.
# ⚠️ VALIDATED OUT-OF-SAMPLE, not fitted: on TC.7's handoff arm every offset
# with terminal-OK BELOW 70% had NEGATIVE EV (58%/-0.23, 54%/-0.33, 63%/-0.24,
# 67%/-0.09) and every offset at/above 76% was POSITIVE (+0.33/+0.32/+0.35).
# The sign flips inside the operator's stated band.
CONDOR_MIN_POP              = float(os.environ.get("OT_CONDOR_MIN_POP", "0.70"))
# Reject a short leg quoted wider than this fraction of its mid. A RANKING never
# refuses — it returns the least-bad strike even when every candidate is broken.
# On 0DTE a nickel of noise on a wide quote trips the 25%% stop on the QUOTE
# rather than on price. 0.25 is a stated PRIOR reasoned from an ADJACENT
# population (factor_sweep's worst continuation quintile ran spread_pct_of_mid
# 0.13-0.88 at -$37/trade; the two best bands sat under 0.043) — debit entries,
# not condor shorts. The rejected-leg log is what would fit it properly.
CONDOR_MAX_QUOTE_WIDTH      = float(os.environ.get("OT_CONDOR_MAX_QUOTE_WIDTH", "0.25"))

# ── RATCHET SCOPE (2026-08-13, operator ruling) ──────────────────────────────
# "the ratchet is inappropriate for this trade if the condor is fully formed.
#  It should only be in effect if there's one side open."  And:
# "don't close a leg if it hasn't been tested - that's what the roll is for."
# THE DEFECT IT FIXES: the base -25% stop only ever fires on the TESTED side
# (spread value rises as price approaches your short). But the ratchet tightens
# the UNTESTED side's stop to breakeven at +20% and +20% locked at +40% —
# precisely because it is WINNING. On the reversal the tested side stops at -25%
# AND the untested side hits its ratcheted stop, so a leg price never went near
# is closed by a stop that exists only because it was profitable. That is the
# double-stop: 5 of 14 condor symbol-days had BOTH sides stopped. It also fires
# BEFORE the roll can ever be used, because the roll needs a tested side.
# WHAT IS PRESERVED: `condor_stop` went 0% -> 19% win after the ratchet shipped,
# but that evidence came mostly from STANDALONES (18 of 46 legs never got a
# second side). Scoping to standalone keeps the gain where it was measured and
# removes it where it disassembles a working structure.
# ⚠️ ACCEPTED CONSEQUENCE: an untested leg that runs to +40% and reverses now
# gives it back rather than locking +20%. That is the price of not taking apart
# a formed condor.
CONDOR_RATCHET_STANDALONE_ONLY = os.environ.get(
    "OT_CONDOR_RATCHET_STANDALONE_ONLY", "1") == "1"

# ── CREDIT VERTICALS HOLD TO 15:45 (2026-08-13, operator ruling) ─────────────
# The flatten ladder opens at FLATTEN_WINDOW_OPEN (15:40) and posts mark-limits
# until the 15:45 cross, so a DEBIT position can close without paying the
# spread. That ladder is why it is not moved: opening it at 15:45 would leave
# zero time for the limit phase and force EVERY end-of-day exit marketable —
# the exact failure time_utils v3.8 was written to fix, and expensive on a book
# whose widest spread quintile already costs -$37/trade.
# BUT THE SIGN IS OPPOSITE FOR A CREDIT VERTICAL. A long debit sitting at 15:40
# is decaying to ZERO, so five more minutes cost the holder and the limit phase
# is pure upside. A SHORT vertical is decaying TOWARD the holder, and 15:40-15:45
# is the steepest part of that curve. Operator: "It's 5 more minutes of
# exponentially rising profit curve."
# ⚠️ NOT held past 15:45, deliberately. Every instrument here except SPX is
# AMERICAN-STYLE and PHYSICALLY SETTLED, so a spread finishing BETWEEN the
# strikes assigns the short and leaves an unhedged overnight stock position —
# "defined risk" is true at settlement, not through assignment. The paper engine
# has no assignment model and would never show it, which is the worst kind of
# clean result.
# ⚠️ COST, stated rather than hidden: verticals then close AT 15:45 with no
# limit phase of their own, so they pay the crossing. A few cents on a spread
# that has already decayed; a worse fill on one still near its short strike.
# 🔴 r71 — 15:45 -> 15:50 BY THE OPERATOR'S RULING, 2026-09-20. *"Widen the
# credit trade window to 1540 for entries & make the credit window flatten at
# 1550. Extreme? Maybe, but manually trading I would hold until the closing
# bell."* The doctrine below was put to him verbatim BEFORE the change and he
# reaffirmed it, with the counter-argument recorded here because it is the
# substance of the ruling: *"It's still defined risk, even on assignment."*
# ⚠️ WHAT HE IS RIGHT ABOUT, AND WHAT THE RESIDUAL IS. The OPTION legs are
# bounded — a vertical finishing through both strikes loses the width, full
# stop. What is NOT bounded by the structure is the position left behind when
# the spread finishes BETWEEN the strikes: the short assigns, the long expires
# worthless, and an unhedged stock position carries overnight. That is why the
# original bound was 15:45.
# 🔑 AND THE EXPOSURE IS A FAILED FLATTEN, NOT A HELD POSITION. Both 15:45 and
# 15:50 exit before the 16:00 expiry, so assignment requires the flatten NOT TO
# FILL. What this change actually spends is MARGIN: the wind-down reconcile
# sweeps fire at 15:45, 15:50 and 15:57, so the final truth-check is now 7
# minutes after the close attempt instead of 12, in the thinnest liquidity of
# the day.
# ⚠️ AND PAPER CANNOT FALSIFY IT. This engine has NO assignment model, so the
# result will look clean on this box whether the reasoning holds or not. Stated
# on the record rather than discovered live.
VERTICAL_HOLD_TO_ET         = EOD_SCHEDULE["resting_at"]   # r149: assignment-risk closes start at 15:45 (was 15:50)

# ══ VOLT (VOLume Trade) — THE CONTROL ARM, OTV4TEST r72 ════════════════════
# 🔑 EVERY ONE OF THESE IS A DECLARED PRIOR (WA §31) AND NONE IS PROVEN ON A
# TRADE. They live HERE, once, because volt_plan.py and exit_engine.py both
# read them and two constants in two modules meaning one thing is the drift
# this codebase keeps finding.
#
# VOLT exists to be the NULL HYPOTHESIS MADE TRADEABLE: two gates, same window
# as the morning four, blocking nothing. If it keeps pace with the gated
# strategies the gates are decoration; if it does not, they are earning their
# keep. ⚠️ A THIRD GATE DESTROYS THE MEASUREMENT — put it in a new strategy.
#
# THE TWO NUMBERS THAT COULD HAVE BEEN GUESSED WERE MEASURED INSTEAD, on 247
# symbol-sessions of 15-second tape (13 names x 19 sessions, 08-24..09-18),
# asking: from a signal bar does price reach +0.5 ATR before -1.0 ATR within 30
# minutes? That geometry breaks even at 66.7%.
#   DIRECTION: close vs the SESSION OPEN won at EVERY volume threshold
#     (68.8% / 66.7% / 72.0% at 1.25x / 1.5x / 2.0x), beating bar-direction,
#     close-vs-EMA20 and a two-close trend. It is also the simplest read
#     available — one comparison, nothing to fit.
#   VOLUME 1.25x: fires on ~9% of in-window bars (n=445), which is what makes
#     the control measurable at all. 2.0x reads higher on n=50; 3.0x gave n=2.
# ⚠️ HONEST LIMIT: the winning cell was chosen from 12, so +2.1pp over
# breakeven is INSIDE that search's noise. The cross-threshold consistency is
# the evidence, not the margin — and the study measured the UNDERLYING with an
# ATR stop while VOLT trades an OPTION against a STRUCTURE stop.
VOLT_VOL_MULT           = float(os.environ.get("OT_VOLT_VOL_MULT", "1.25"))
# 🔴 r74 — THE ENTRY FRAME IS ONE MINUTE, NOT FIVE, AND IT IS A SPECIFICATION.
# The operator, 2026-09-21, watching VOLT sit dead through the open: *"No,
# that's unacceptable. It should be able to fire immediately. I want to move on
# the first sense that volume is expanding and It needs to jump on."*
# WHAT r72 SHIPPED WAS UNREACHABLE FOR A THIRD OF ITS OWN WINDOW. The volume
# gate read COMPLETED 5-MINUTE bars and demanded eight of them, which is 40
# minutes of session — so a window opening at 09:35 could not fire before
# 10:15. MEASURED over 18 replayed sessions: earliest first entry 10:15, median
# 10:35, latest 11:10. NOT ONCE in the first 40 minutes.
# ⚠️ AND THE SHIPPED GATE WAS STRICTER THAN THE ONE THAT WAS MEASURED. The
# study behind the 1.25x number used `mean(vols[max(0,i-6):i])` and required
# only THREE prior bars — it tolerated a short baseline early in the session.
# The plan then demanded eight. The number was justified by one rule and
# enforced by another.
# MEASURED AFTER THE CHANGE, same 19 QQQ sessions: 24.2 trades per session
# against 2.0, first fire 09:37 against 10:15.
# ⚠️ THE EXIT FRAME IS UNCHANGED AND STAYS FIVE MINUTES — the operator's
# earlier ruling that a close beyond the entry is the dead thesis. Entry frame
# and exit frame are independent, and conflating them is what produced the
# unreachable window in the first place.
VOLT_VOL_LOOKBACK_BARS  = int(os.environ.get("OT_VOLT_VOL_LOOKBACK_BARS", "5"))
# the fewest completed 1m bars before the gate may be evaluated at all. THREE,
# matching the study exactly rather than exceeding it.
VOLT_MIN_BARS           = int(os.environ.get("OT_VOLT_MIN_BARS", "3"))
# 🔑 THE STOP IS THE ENTRY — operator's ruling 2026-09-21: "Use a structural
# stop. A close beyond where the trade opened is a dead thesis." There is no
# lookback and no floor because there is no stop DISTANCE to degenerate. The two
# designs it replaced both blew up on exactly that: a 3-bar structural extreme
# scored WORST -120R and the signal bar's own extreme -749R, both because a
# tight structure put the stop at the entry and R exploded. Measured over 19
# sessions x 4 symbols with the real plan: the ruling gives worst -1.49R.
# the trail arms on DISTANCE, not premium — the operator's spec, and r44's scar:
# a premium-fraction floor could sit BELOW entry, so arming could guarantee a loss.
VOLT_TRAIL_ARM_R        = float(os.environ.get("OT_VOLT_TRAIL_ARM_R", "0.50"))
VOLT_TRAIL_LOCK_FRAC    = float(os.environ.get("OT_VOLT_TRAIL_LOCK_FRAC", "0.50"))
# ══ r79 (EXT.1) — THE EXTRINSIC METER ══════════════════════════════════════
# Operator, 2026-09-21, on a VOLT call at +468% with FOUR CENTS of extrinsic
# left: *"We need an extrinsic/intrinsic metered exit."*
# 🔑 INTRINSIC IS EARNED; EXTRINSIC IS WHAT YOU ARE STILL PAYING FOR. When the
# extrinsic has decayed away the position is NOT AN OPTION any more — it is
# stock with an expiry: delta ~1.0 and NO CONVEXITY LEFT TO ABSORB A PULLBACK.
# A give-back expressed as a FRACTION OF THE RUN therefore costs full dollars
# exactly when the trade has already won. MEASURED LIVE on 81b1afae: mark 5.63
# against 5.59 intrinsic — 0.8% extrinsic, $45 of total remaining theta risk —
# while the 50%-of-run trail sat 2.88 points away, which at delta 0.983 is
# $2,880 of the $4,630 held. The same leash on a delta-0.30 position costs
# about $860, because the curvature eats the move. THE SAME RULE IS THREE
# TIMES MORE EXPENSIVE ON THE POSITION THAT HAS ALREADY WON.
# 🔴 THE RULING IS AN EXIT, NOT A LEASH. Operator, same session, after seeing
# the meter: *"When Delta reaches PAR, we need to get the fuck out."* A
# position at par delta is no longer a trade thesis expressed as an option —
# it is stock carrying an expiry, and every argument for holding an option
# (convexity, defined risk, the cheap tail) has already been spent.
# 🔑 r82 — ONE PAR NUMBER FOR EVERY STRATEGY THAT USES IT. r81 landed an hour
# ago on exactly this defect: four literals for one credit window, three of
# which never moved. A second strategy is adopting par delta in the same
# session, so it DERIVES rather than repeating the number.
DELTA_PAR               = float(os.environ.get("OT_DELTA_PAR", "0.98"))
VOLT_DELTA_PAR          = DELTA_PAR
# 🔴 r82 — BREAKOUT TRADES PAR DELTA INSTEAD OF THE +100% TARGET, by the
# operator's ruling: *"the breakout needs the delta stop not the 100% stop."*
# Its target was never written for it — `management.py` documents that rule as
# *"a debit exit for the RUNAWAY only"* and implements it as
# `strategy not in BUTTERFLIES`, so Breakout inherited a guillotine by
# predicate breadth. MEASURED: its 8 target exits fired at delta 0.619-0.650,
# capping every winner long before convexity was spent.
BREAKOUT_DELTA_PAR      = DELTA_PAR
# The FALLBACK when the feed hands us no delta — the SAME fact read off price
# instead of off the greeks, so the rule cannot be silently disabled by a
# missing field (§0.5: absent is not the same as false).
VOLT_EXT_STOCKLIKE      = float(os.environ.get("OT_VOLT_EXT_STOCKLIKE", "0.02"))
# The leash once stock-like, in ATR(5m) units. NOT a fitted number: today's
# worst 5m close-pullback was 0.295 pts against an ATR of 0.571, so 1.0x ATR
# is ~2x the deepest retrace the move actually made. ⚠️ AN UNFITTED PRIOR
# (§31) — arm E of PREREG_TRAIL.md measures it; until then it is a PRIOR and
# the header says so rather than letting it read as evidence.
VOLT_STOCKLIKE_ATR_MULT = float(os.environ.get("OT_VOLT_STOCKLIKE_ATR_MULT", "1.0"))
VOLT_WINDOW_OPEN_ET     = ENTRY_WINDOWS["VOLT"][0]
VOLT_WINDOW_CLOSE_ET    = ENTRY_WINDOWS["VOLT"][1]
# ⬛ SUPERSEDED 2026-09-24 (OTV4TEST r131) — the operator ruled VOLT onto the Breakout
# sizing model (1-R = the signal candle's extreme in premium, ORB_RISK_USD at risk,
# capped at ORB_BUDGET_USD, r93 noise floor). The control-arm argument below was
# measured and lost: VOLT is a participant now, not a control. Kept as history.
# ~~🔴 VOLT SIZES OFF RISK_PER_TRADE_USD, **NOT** ORB_BUDGET_USD, AND THE
# DIFFERENCE IS THE WHOLE COMPARISON. Live (configure.sh): OT_RISK_USD=1050 and
# OT_ORB_BUDGET_USD=10000. VOLT uses ONLY the budget rule — it deliberately does
# not import the ORB's `min(geometry, budget/cost)` clamp, because that clamp is
# an ORB prior and importing it would smuggle a third rule into a two-gate
# control. So inheriting the $10,000 CEILING would have sized VOLT at ~73
# contracts on a $1.36 premium against the handful the ORB's geometry actually
# takes — and a control that trades 10-50x the size of the arm it measures
# produces a P&L comparison that means nothing.
# ⚠️ FOUND BY REPLAY, and only because the operator caught that the replay was
# reading the $200 DEFAULT rather than the live environment (ENV.1's family: a
# measurement taken outside the environment it describes).~~
VOLT_BUDGET_USD         = float(os.environ.get("OT_VOLT_BUDGET_USD",
                                               str(RISK_PER_TRADE_USD)))

VERTICAL_HOLD_TO_CLOSE      = os.environ.get("OT_VERTICAL_HOLD_1545", "1") == "1"
# Minutes per bar of the ATR feeding sigma. 5m frame by default; wrong here
# scales sqrt(T) and silently moves every POP.
CONDOR_POP_BAR_MIN          = float(os.environ.get("OT_CONDOR_POP_BAR_MIN", "5"))

# 🔴 ONE START TIME FOR EVERY CREDIT SPREAD (r141). Operator, 2026-08-26:
# *"I would just as soon make a universal 'all credit spreads on at 1130' to
# keep things tidy"*, then, on being shown the 08-24 ruling: *"Ok then 1130 &
# 1131 are just as fine."*
# ⚠️ 11:31, NOT 11:30, AND THE REASON IS THE OPERATOR'S OWN 08-24 RULING:
# *"Handoff (credit) needs to start at 1131 - it's colliding with runaway
# (same trigger)."* The debit cutoff test is `>= (11, 30)`, so debit is blocked
# AT 11:30; a credit start of 11:30 hands both the same minute and reproduces
# that collision. One minute of daylight makes the handover unambiguous.
# ⚠️ AND SECONDS CANNOT EXPRESS IT ANYWAY — every gate compares
# `(now.hour, now.minute)`, so 11:30:01 is indistinguishable from 11:30:59.
# The tick is 30s besides, so a sub-minute boundary would land wherever each
# box's restart drift put it.
# ⚠️ THIS MOVES CONDOR LEGS LATER, 11:11 -> 11:31. The old 11:11 came from
# otv3 and was an ADX-ramp argument for waiting LONGER after the opening gap,
# so 11:31 is consistent with its intent. It costs the condor window 20
# minutes against the 14:00 cutoff: 169 -> 149.
CREDIT_ENTRY_START_ET       = ENTRY_WINDOWS["TrendCreditSpread"][0]  # every credit spread, one number
CONDOR_ENTRY_START_ET       = CREDIT_ENTRY_START_ET   # was (11, 11)
# ⚠️ THE FOURTH CREDIT PATH, AND IT WAS NOT IN THIS FILE AT ALL.
# `sweep_credit_spread.py` read `getattr(config, "SWEEP_CS_EARLIEST_ET",
# "11:11")` — the DEFAULT was the only source, so the sweep kept 11:11 while
# the other three moved. check_sweep_spread's S8a caught it; I had not.
SWEEP_CS_EARLIEST_ET        = f"{CREDIT_ENTRY_START_ET[0]}:{CREDIT_ENTRY_START_ET[1]:02d}"
# 🔴 r81 (LATE.2) — 15:40 BY THE OPERATOR'S r71 RULING, WHICH NEVER REACHED
# THIS NUMBER. r71 widened the ADMISSION TABLE to 15:40 and moved
# VERTICAL_HOLD_TO_ET to 15:50, and the credit plans went on refusing at 14:00
# for a full session, because THE PLAN RUNS BEFORE ADMISSION: sweep_plan and
# tcs_plan stamp DORMANT and never emit a signal, so the widened window is
# never consulted. Measured on the board 2026-09-21 14:11 ET — "past 14:00 ET
# — observing only" and "past TCS_ENTRY_END_ET 14" — with admission reading
# (15,40) at the same instant. The r317 block BELOW PREDICTED THIS EXACT
# FAILURE and it still happened, which is why r81 derives every credit END
# from this one constant rather than repeating the number.
CONDOR_ENTRY_CUTOFF_ET      = ENTRY_WINDOWS["TrendCreditSpread"][1]  # r81: was (14,0); r71's ruling
# 🔴 r317 — THE END SIDE, WHICH THE TWO EARLIER FIXES BOTH MISSED.
# `sweep_credit_spread.LATEST_ET` read `getattr(config, "SWEEP_CS_LATEST_ET",
# "14:00")` and THE KEY DID NOT EXIST, so the default was the only source —
# the same shape as `SWEEP_CS_EARLIEST_ET` above (which kept 11:11 while the
# other three credit paths moved) and as `GEX_BFLY_EARLIEST_ET`. Both of those
# were repaired on the START side; nobody swept the END.
# ⚠️ IT COSTS NOTHING TODAY AND EVERYTHING ON THE DAY THE CUTOFF MOVES: all
# four credit paths read 14:00 right now, so the defect is invisible until
# someone changes the number — and then three paths move and the sweep does
# not, silently, which is exactly how the 11:11 sweep survived r146.
# ⚠️ MANAGEMENT IS NOT GATED BY THIS. Same as `TCS_ENTRY_END_ET`: the roll and
# `management.py` reference no window constant and run to the 15:45 flatten.
CREDIT_ENTRY_END_ET         = CONDOR_ENTRY_CUTOFF_ET   # one END for every credit path
SWEEP_CS_LATEST_ET          = f"{CREDIT_ENTRY_END_ET[0]}:{CREDIT_ENTRY_END_ET[1]:02d}"
# 🔴 r81 — THE FIFTH CREDIT PATH, AND IT IS THE r317 DEFECT REINTRODUCED UNDER
# A NEW NAME. r317 repaired `SWEEP_CS_LATEST_ET` above after the key-did-not-
# exist defect bit twice; this fork then wrote `strategy/sweep_plan.py` reading
# `SWEEP_CS_LATEST_ET_FORK`, WHICH HAS NEVER EXISTED IN THIS FILE, so its
# `getattr(..., (14, 0))` default was the only source and the sweep sat at
# 14:00 while r71 moved everything else. Derived, never repeated — a literal
# here would be the same bug with a different number.
# ⚠️ THE START SIDE WAS ON A SILENT DEFAULT TOO. `sweep_plan.py:97` reads
# `SWEEP_CS_EARLIEST_ET_FORK` and that key has never existed either; its
# (9, 35) default merely HAPPENS to match the admission table today, which is
# r317's warning word for word — invisible until someone moves the number.
SWEEP_CS_EARLIEST_ET_FORK   = ENTRY_WINDOWS["SweepCreditSpread"][0]   # r81: matches admission SWEEP start
SWEEP_CS_LATEST_ET_FORK     = ENTRY_WINDOWS["SweepCreditSpread"][1]
# 🔑 THE ONE CREDIT END. Every credit path resolves to this single constant and
# none of them carries its own number: the sweep (both key spellings), the TCS,
# and the condor that forms from two of their legs. r71's ruling moved the
# admission window and FOUR separate literals stayed at 14:00; deriving them is
# what makes the next ruling reach the code instead of half of it.
TCS_ENTRY_END_ET            = CREDIT_ENTRY_END_ET

# ─── EXIT MANAGEMENT ──────────────────────────────────────────────────────────

TRAIL_ACTIVATION_PCT        = 0.50
TRAIL_LOCK_PCT              = 0.25

# ─── LONG-OPTION THETA PROTECTION + FVG PROFIT TRAIL ──────────────────────────
# Theta bleed: exit a PROFITABLE long when the projected time decay over the next
# THETA_LOOKAHEAD_MIN minutes would erase the current unrealized gain (direction
# hasn't gone against us — the option is just handing the profit back to time).
THETA_LOOKAHEAD_MIN         = 20     # minutes of decay to project
RTH_MINUTES                 = 390    # 6.5h session, to convert daily theta → per-min
# FVG-anchored trailing stop for longs: once armed, the stop parks at the FAR
# edge of the nearest unfilled in-favor 1m FVG (room to pull back INTO the gap
# for continuation); a close beyond the gap exits. Falls back to a % lock.
FVG_TRAIL_ARM_PCT           = 0.20   # arm once the trade is up this much
FVG_TRAIL_LOCK_PCT          = 0.80   # premium floor = 80% of current when no FVG
# v2.0 runner refinements (all env-tunable for paper A/B):
# 5-minute FVGs anchor the trails instead of 1-minute — structurally
# meaningful gaps, natural gamma room; 1m stays for structure stop and BOS.
USE_5M_FVG_TRAIL            = os.environ.get("OT_USE_5M_FVG_TRAIL", "True") != "False"
# An FVG-derived floor may never sit tighter than this fraction of current
# premium — a gap hugging price can't turn the runner leash into a tripwire.
FVG_FLOOR_MAX_LOCK_PCT      = float(os.environ.get("OT_FVG_FLOOR_MAX_LOCK_PCT", "0.90"))
# Post-target no-FVG fallback lock. Was 0.85 — TIGHTER than the pre-target
# 75% ratchet, an inverted leash that harvested proven runners on one gamma
# wick. Now matches the pre-target trail.
POST_TARGET_TRAIL_LOCK_PCT  = float(os.environ.get("OT_POST_TARGET_TRAIL_LOCK_PCT", "0.75"))
# Sweep reversals get the ORB post-target trail instead of the +100%
# guillotine (the one hard TP among directionals). False restores target_hit.
SWEEP_POST_TARGET_TRAIL     = os.environ.get("OT_SWEEP_POST_TARGET_TRAIL", "True") != "False"

POLL_INTERVAL_SECONDS       = 15


ADX_TREND_THRESHOLD         = 25

# ── CNT.1 — continuation under BREAKOUT_VOLATILE (2026-08-07, operator's call) ─
# Standalone continuation was barred under BREAKOUT for a structural reason, not
# a quality one: `continuation_strategy` derives DIRECTION FROM THE LABEL
# (TRENDING_BULL -> long, TRENDING_BEAR -> short) and BREAKOUT_VOLATILE asserts
# volatility EXPANSION without saying which way, so no branch could assign one.
# The runaway handoff already solves this by taking direction from the ORB.
# This does the same thing from the trend engine's own vote.
#
# WHY A SEPARATE ADX FLOOR RATHER THAN THE CONVICTION FLOOR: under a non-trending
# label `_label_trending` is False, so continuation's `CONTINUATION_CONV_FLOOR`
# check is SKIPPED ENTIRELY — the same hole the handoff path has. Reusing
# BREAKOUT's conviction, not the trend's. The direction is coming from the trend
# engine, so the quality bar must come from there too.
#
# DEFAULT = ADX_TREND_THRESHOLD (25), the same bar the rest of the system uses to
# call a trend a trend. A PRIOR, not a fit — deliberately permissive for the
# collection phase per the operator ("to gather data").
# Entries take setup_type `trend_continuation_breakout` so the rollup can score
# this path SEPARATELY from _standalone and _handoff. Without that split the
# data this is being turned on to collect would be unreadable.
# ── CNT.2 — the INSURANCE gate for continuation (2026-08-07, operator's call) ─
# BOS (exit_engine 2b) is continuation's thesis invalidator and it is
# deliberately UNGATED on P&L — but `BOSTracker.protected_level` starts None and
# is only set once the trade makes a new CLOSING HIGH past entry. So BOS is
# structurally BLIND until the trade goes favourable in the underlying, and that
# blind window is exactly where the 45 max_loss_floor trades die at −29% with
# MFE +1%.
#
# THE LEVEL IS ALREADY COMPUTED AND STORED, and until now was dead in the
# decision path: continuation_strategy:447/450 stamps
# `underlying_stop = gap.bottom - 0.5*atr` (long) / `gap.top + 0.5*atr` (short)
# on every entry, trade_logger:206 persists it, and the ONLY reader was
# query.py:233 — for display.
#
# WHY STRUCTURAL AND NOT A TIGHTER PREMIUM FLOOR: a premium-percent stop on 0DTE
# measures gamma, not thesis. The floor sweep proved a tighter one nets ~zero
# because it cuts winners that merely dip (peak is late, drawdown is early).
# This level is the ENTRY PREMISE INVERTED — continuation enters on a pullback
# INTO an unfilled 5m FVG expecting resumption, so price closing beyond the far
# edge plus a half-ATR buffer means the pullback was the reversal continuing.
#
# WHY IT DOES NOT REOPEN THE JULY DECISION: `underlying_stop` was rejected as
# THE exit for two reasons — "a gap fill is NOT trend failure" and "the FVG
# level is STATIC so it protects nothing once the trade works". Neither applies
# to a gate that lives ONLY while BOS has no protected level and yields the
# instant it does. It fills the hole that decision knowingly left; it does not
# overturn it.
#
# ⚠️ THE LEVEL HAS NEVER BEEN READ BY ANYTHING THAT TRADES, so it has no track
# record. Exits are tagged `insurance_stop` so the cross-day rollup scores this
# path separately from max_loss_floor and bos_exit — without that split the data
# this exists to collect is unreadable. Kill switch: OT_CONT_INSURANCE=0.
CONT_INSURANCE_STOP = os.environ.get(
    "OT_CONT_INSURANCE", "1").strip().lower() not in ("0", "false", "no", "off")

CONT_BREAKOUT_DIRECTION = os.environ.get(
    "OT_CONT_BREAKOUT_DIRECTION", "1").strip().lower() not in ("0", "false", "no", "off")
CONT_BREAKOUT_MIN_ADX   = float(os.environ.get("OT_CONT_BREAKOUT_MIN_ADX",
                                               str(ADX_TREND_THRESHOLD)))
ADX_RANGE_THRESHOLD         = 25   # v3.3 (2026-07-14): was 20 — closed the ADX
                                   # DEAD ZONE. _is_ranging required adx<20 while
                                   # _is_trending requires adx>=25, so ordinary
                                   # and fell to UNKNOWN (hard no-trade). Measured
                                   # live: AAPL sat at ADX 19.26 — 0.74 under the
                                   # cliff — flickering RANGING<->UNKNOWN all session;
                                   # ~85% of fleet ticks were UNKNOWN on 07-13/07-14
                                   # and the fleet took ZERO trades for two days.
                                   # A range does not stop being a range because ADX
                                   # LOWER CONVICTION. _ranging_conviction already
                                   # ramps on 1 - adx/ADX_RANGE_THRESHOLD, so raising
                                   # the gate to the trend line extends that ramp
                                   # across the gap: ADX 12 -> ~0.52, ADX 24 -> ~0.16.
                                   # for RANGING as "any (allowed)" and strength as a
                                   # SOFT-NECESSARY ramp, never a cliff.
                                   # PRIOR — recalibrate from multi-day tape.
ATR_EXPANSION_MULTIPLIER    = 1.5
BB_WIDTH_COMPRESSION_PCT    = 0.20
SWEEP_REJECTION_CANDLES     = 3
EQUAL_LEVEL_PCT             = 0.001
REASSESS_MINUTES     = 5

# ─── SETUP SCORING ────────────────────────────────────────────────────────────

GRADE_A_MIN_SCORE           = 0.78
GRADE_B_MIN_SCORE           = 0.55

# ── Brief nudge (2026-07-15) ─────────────────────────────────────────────────
# Signed pre-market move-probability prior applied post-sum in setup_scorer:
# +w·strength for ORB, -w·strength for neutrals, 0 for sweep reversal. This
# value is the hard cap (strength is 0..1). Small on purpose — a tie-breaker,
# never an override. Calibrate from the signal ledger once entries accrue.
BRIEF_CONVICTION_WEIGHT     = 0.05
# ── 🔴 r122 — FLAT 1.0. THE GRADE NO LONGER SIZES THE TRADE. ─────────────────
# Operator, 2026-08-25: "right now sizing has to be a 1.0 across all trades...
# In the future, we may fit based on indicators but we are not there right now."
# ⚠️ IT WAS SIZING ON A LETTER THAT CARRIES NO INFORMATION. The operator's own
# reading of the ORB setup: survivors are "all structurally A unless we start
# grading how deep the impulsive candle sits inside the range" — and the data
# agrees, PLTR 51 A-grades, TSLA 30, AVGO 29. Worse, where the letter DID vary
# it pointed the wrong way: TSLA Grade A 30 trades net -$2,237 against Grade B
# 11 trades net +$125. A 1.5x multiplier on A was therefore betting MORE on the
# band that lost MORE, on at least one box.
# ⚠️ AND IT SILENTLY BROKE THE RISK BUDGET. A 1.5x multiplier means an A-grade
# trade risks $1,575 against a $1,050 setting — NVDA this morning sized 2
# contracts at $603 = $1,206 deployed, over budget, because of this line. A
# risk number that the grade can inflate by half is not a risk number.
# The dict stays (callers read it, and .get defaults are how the C-grade
# rejection reads) — only the values are flattened, so restoring a multiplier
# later is a one-line change rather than a re-wiring.
# 🔴 r155 — THE LONE-VERTICAL STOP, AS A FRACTION OF THE RISK.
# Was `entry_prem * 1.15` — fifteen percent of the CREDIT, which is INVERTED:
# the less credit collected, the tighter the stop in DOLLARS, so the structures
# with the least premium got the least room. CVX 2026-08-27 collected $0.58 on
# a 5-wide and was handed an 8.7-CENT stop against $442 of risk; it entered the
# same spread seventeen times in twelve minutes, each dead inside a minute.
# ⚠️ ANCHORED TO `width - credit` — what is actually at stake, which does not
# shrink as the credit shrinks. Same 15%: a $0.58 credit on a 5-wide now gets
# $0.66 of room instead of $0.087.
# ⚠️ 15% IS CARRIED OVER, NOT RE-FITTED. It meant "15% of credit" and now means
# "15% of risk" — a different quantity, so the number deserves its own
# evidence. It is a ⟨PRIOR⟩ until the plan table says otherwise.
LONE_STOP_PCT_OF_RISK       = float(os.environ.get("OT_LONE_STOP_PCT_RISK", "0.15"))

GRADE_SIZE_MULTIPLIER       = {"A": 1.0, "B": 1.0}

# ─── VOLATILITY / TREND ───────────────────────────────────────────────────────

ATR_PERIOD                  = 14
ATR_STOP_MULTIPLIER         = 1.5
BB_PERIOD                   = 20
BB_STD                      = 2.0
EMA_FAST                    = 9
EMA_MID                     = 21
EMA_SLOW                    = 50
EMA_ANCHOR                  = 200

# ─── LIQUIDITY MAPPING ────────────────────────────────────────────────────────

EQUAL_HIGH_LOW_LOOKBACK     = 50
IMBALANCE_MIN_SIZE_PCT      = 0.002
LIQUIDITY_BUFFER_PCT        = 0.003

# ─── SIGNAL VALIDATION ────────────────────────────────────────────────────────

# ⚠️ UNWIRED — neither constant is imported anywhere. Both date to the initial
# commit and appear in no changelog. Retained deliberately as a record of intent:
#   MIN_RRR            — no risk/reward floor exists in the codebase. ORB's RRR is
#                        structural (stop = impulsive origin, target = 100% of range
#                        width), so it varies per setup and is currently ungated.
#   VWAP_FILTER_ACTIVE — implies a HARD VWAP gate. None exists. What is live is a
#                        SOFT score in setup_scorer (vwap_alignment, weight 0.15;
#                        a misaligned trade scores 0.25 on that dimension and can
#                        still clear the 0.55 B-threshold). NOTE: crypto_trader
#                        learned the opposite lesson the hard way — shorts above
#                        VWAP / longs below VWAP had to become HARD blocks. That
#                        lesson is NOT ported here. Open decision.
# E + F (2026-07-31) — WIRED AT LAST. Both were declared here at genesis and
# never read by anything; `VWAP_FILTER_ACTIVE = True` in particular sat as a
# hardcoded True that nothing consulted, so "the filter is on" was true in the
# config and false in the code for months.
#
# Both now ship env-tunable and DEFAULT OFF, which is a deliberate downgrade from
# the True above: house rule is evidence-decides, and neither has yet been
# convicted on collected data. They run as log-only counters until the retro
# ledger (signal_journal has carried vwap + price_vs_vwap since 07-18, and rrr
# since 07-31 via N.2) shows the blocked trades are net-negative. If they are
# not, these stay off and the counter IS the finding.
#
# A duplicate VWAP_FILTER_ACTIVE was briefly added higher in this file on 07-31
# and was silently overridden by this line — later assignment wins. Caught by a
# test asserting the default was False when it read True. One definition only.
MIN_RRR                     = float(os.environ.get("OT_MIN_RRR", "1.3"))
MIN_RRR_ACTIVE              = os.environ.get("OT_MIN_RRR_ACTIVE", "0") == "1"
VWAP_FILTER_ACTIVE          = os.environ.get("OT_VWAP_FILTER_ACTIVE", "0") == "1"

# ─── STRUCTURE ANALYSIS ───────────────────────────────────────────────────────

SWING_LOOKBACK              = 10
MIN_SWING_SIZE_ATR          = 0.5
FVG_MIN_SIZE_PCT            = 0.001
SR_TOUCH_MIN                = 2
SR_ZONE_PCT                 = 0.002
ORDER_BLOCK_LOOKBACK        = 20

# ─── ORDER EXECUTION ──────────────────────────────────────────────────────────

LIMIT_RETRY_SECONDS         = 30
LIMIT_IMPROVE_TICKS         = 1
# PAPER FILL FRICTION — v3.9 (2026-07-22), default 0.0.
# Applied AGAINST the trade, uniformly, by execution/limit_ladder (the single
# paper-pricing authority): debits pay (1+pct)·mark, credits receive
# (1−pct)·mark. Every paper path honours it — single leg, butterfly, condor
# leg, rolled vertical.
#
# WHY THE DEFAULT IS ZERO: live no longer sends market orders. Under the
# mark-limit policy (limit_ladder v1.2) live posts AT the mark and either
# fills there or does not fill at all, so a markup would make paper
# PESSIMISTIC on price while remaining optimistic on FILL RATE. The honest
# residual gap is no-fill risk, not slippage — and no-fill risk cannot be
# modelled as a price haircut.
#
# WHEN TO RAISE IT: after the tiny-account live shakedown measures real
# mark-limit fill quality, set OT_PAPER_SLIPPAGE_PCT to that number and every
# paper path degrades together — one lever, fleet-wide, no code change.
# (Pre-2026-07-22 paper history was booked at 0.01; set that value to compare
# like for like.)
PAPER_FILL_SLIPPAGE_PCT     = float(os.environ.get("OT_PAPER_SLIPPAGE_PCT", "0.0"))

# ─── TASTYTRADE API ───────────────────────────────────────────────────────────

TT_BASE_URL                 = "https://api.tastytrade.com"
TT_PAPER_BASE_URL           = "https://api.cert.tastyworks.com"

# ─── MACRO / FED CALENDAR ─────────────────────────────────────────────────────

FOREX_FACTORY_URL           = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
MACRO_FETCH_INTERVAL_MIN    = 60
FED_EVENT_KEYWORDS          = ["FOMC", "Fed", "Federal Funds Rate", "Powell"]

# ─── TIMEFRAMES ───────────────────────────────────────────────────────────────

TIMEFRAMES = {
    # PF.2 (2026-08-11) — RAISED 10 -> 60. The boxes were VERIFIED to already
    # hold 84 daily bars (2026-06-11 -> 08-11, checked on SPX and GLD); this
    # number was clipping the frame handed to the engines to 10, which is below
    # the pitchfork anchor rule's minimum and made RECENCY=40 unsatisfiable.
    # The history was never missing — the frame was. No new fetch, no new
    # timing, nothing for session_guard to collide with.
    "1d":  {"candles": 60,  "role": "bias"},
    # ── L1.9a (2026-08-19) — 50 WAS BELOW THE ENGINE'S OWN REQUIREMENT ──────
    # ⚠️ `trend_engine` refuses to vote on a timeframe with fewer than
    # `EMA_SLOW + 5` = **55** bars. This asked for exactly **50**, so the 1h
    # trend vote could NEVER FIRE — not on a thin day, not after a restart,
    # NEVER. It is the second-heaviest timeframe in the blend (`tf_weights`
    # 1d 0.15 · **1h 0.20** · 15m 0.30), and its "declared weight contributes
    # nothing" warning has been firing on every box since the engine shipped.
    #
    # ⚠️ THIS IS WHY L1.6/L1.7 HAVE BEEN STUCK. The TRENDING row needs a session
    # "dominant ~50% with RANGING vetoed through it". A permanently absent
    # structure-timeframe vote depresses TRENDING and inflates RANGING — TSLA
    # 08-04 showed 99% TRENDING dominance with RANGING STILL SCORING ON 64% OF
    # TICKS and A2 failing at 14%. **26 TREND sessions are already labeled and
    # the row is still open**: the blocker was never labeling habit, it was that
    # no session could show the veto while a 0.20-weight vote was missing.
    #
    # 80 rather than 55: the minimum is a cliff, not a target — a frame that
    # only just clears it starves again on any short session. The store holds
    # ~112 RTH 1h bars (BACKFILL_DAYS 16d x 7/day) and pruning is OFF, so 80 is
    # comfortably inside supply.
    #
    # ⚠️ BLAST RADIUS, STATED: `df_1h` is also read by `structure_analyzer`
    # (swings + S/R), `pitchfork`, `entry_snapshot` and the named-level frame.
    # A deeper frame changes what all of them see — more history, arguably more
    # correct, but DIFFERENT. This is a population boundary; measurements
    # spanning it are not comparable.
    "1h":  {"candles": 80,  "role": "structure"},
    # v4.1: 150, not 50. Below EMA_SLOW+5=55 the vote is NEUTRAL; below ~80 the
    # EMA-50 is re-seeded on the tail and materially wrong. See the header.
    "15m": {"candles": 150, "role": "trend"},
    "5m":  {"candles": 100, "role": "entry_context"},
    "1m":  {"candles": 60,  "role": "trigger"},
}

# ─── LOCAL RETENTION POLICY — DECLARED, NOT YET ENFORCED ─────────────────────
# v4.0 (2026-08-25). The policy is written down HERE, in config, BEFORE anything
# acts on it — operator's instruction: "we need to write the per tenor retain
# before writing any kind of per-tenor purge." A purge that carries its own
# numbers inline is a purge whose policy can only be found by reading deletion
# code.
#
# 🔴 EVERYTHING BELOW IS COMMENTED OUT AND NOTHING READS IT. Pruning on the
# boxes is OFF (candle_feed.PRUNE_KEEP_ROWS = 0) and stays off until this is
# deliberately enabled. Declaring it inert is the point: the numbers can be
# argued with before a single row is at risk.
#
# 🔑 THE BINDING CONSUMER IS EMA_ANCHOR = 200, and it inverts the intuition.
# Every tenor needs the SAME NUMBER OF BARS, so the DAYS differ by how fast that
# tenor accumulates them:
#
#     tenor   bars/session   200 bars =      keep      why
#     1m           390       0.5 sessions    5 days    days are for RE-PUSH,
#                                                      not warm-up
#     5m            78       2.6 sessions   10 days
#     15m           26       7.7 sessions   20 days
#     1h             7      28.6 sessions   60 days    ← THE BINDING ONE
#     1d             1     200   sessions   keep all   one row a day
#
# ⚠️ A FLAT ROW CAP IS WRONG, AND THAT IS WHAT EXISTS TODAY. PRUNE_KEEP_ROWS is
# one number for every tenor: at 200 it would hold half a session of 1m and 29
# sessions of 1h. A naive "keep 30 days of everything" fails the other way — it
# wastes space on the bulkiest tenor while STARVING THE 1h FORK, which is the
# condor's anchor and the thing already failing to build.
#
# ⚠️ THE FORK ITSELF NEEDS FAR LESS THAN THE EMA: (2k+1)*3 bars, k=3 on 1h = 21
# bars = 3 sessions. If EMA_ANCHOR is ever confirmed NOT to be consumed on 1h,
# the 60 days below drops to about 5.
#
# ⚠️ PADDED ~1.5x OVER THE MINIMUM ON PURPOSE. A warm-up sitting exactly at its
# boundary breaks on the first holiday week.
#
# RETENTION_DAYS = {
#     "1m":  60,          # r108 — was 5; must equal "1h" (breaches judged on 1m)
#     "5m":  30,
#     "15m": 30,
#     "1h":  60,
#     "1d":  None,        # None = keep everything; it is one row per session
# }
#
# Non-candle artifacts. ⚠️ VERIFIED IN SOURCE 2026-08-25, NOT ASSUMED: the
# surface engine reads a 15-MINUTE WINDOW and a 120-second slice, so NOTHING
# reaches across sessions. These days are a RE-PUSH WINDOW, not a warm-up
# requirement — and 3 rather than 1 because a Friday push that fails silently
# is not noticed until Monday, and a 2-day window expires over the weekend.
# RETENTION_DAYS_ARTIFACTS = {
#     "chain_snapshots": 3,
#     "greeks_series":   3,
#     "quote_series":    3,
# }
#
# 🔴 NEVER PURGED ON THE BOX, AT ANY AGE: character_ledger, plan_ledger,
# gate_disposition, strategy_note, fire_snapshot. These are LIFECYCLE records —
# they capture state transitions as they happened, and a recomputation cannot
# reconstruct a biography. Indicators, forks and surface ARE recomputable from
# the candles and are the safe ones to trim.
#
# 🔴 AND THE PURGE MUST KEY OFF VERIFICATION, NEVER OFF AGE ALONE. A box whose
# last push failed still holds the ONLY copy. Land, verify, then maintain.

CACHE_STALENESS_SECONDS = {
    "1d":  3600,
    "1h":  300,
    "15m": 120,
    "5m":  30,
    "1m":  10,
}

# ─── NOTIFICATIONS ────────────────────────────────────────────────────────────

NOTIFY_ON_ENTRY             = True
NOTIFY_ON_EXIT              = True
NOTIFY_ON_CIRCUIT_BREAK     = True

# ─── DATABASE & LOGGING ───────────────────────────────────────────────────────

# r218 (PATH.1) — the store DIRECTORY and the quote floor, defined at last. The three store PATHS are
# resolved at call time by utils/paths.py (each honours its OT_* variable); do not snapshot them here.
# ⚠️ NO PROJECT IMPORT HERE: configure.sh runs `python3 -c "import config"` beside a bare copy of this file,
# so config must import with nothing of ours on the path (check_configure_instrument I1-I5 went red on that).
DATA_DIR                    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")   # == utils.paths.data_dir(), pinned by check_store_paths S5
QUOTE_FLOOR                 = 0.01     # a contract quoted under a penny cannot be bought; breakout_plan reads this (was a getattr fallback of the same value)
DB_PATH                     = os.environ.get("OT_TRADES_DB") or os.path.expanduser("~/options-trader/trades.db")   # r13: OT_TRADES_DB for checks
# 🔴 r112 — ENV-OVERRIDABLE, AND THE FLAG BEATS BOTH. This was a bare literal,
# so the only way to get DEBUG was to EDIT A TRACKED FILE on the box — and the
# hotfix launcher runs `git checkout -- config.py` before every pull, which
# reverts it. A setting that a bake silently undoes is a setting nobody can
# rely on. `data/DEBUG_LOG` (devtools item 69) is read LIVE by main and wins
# over this, so the level can be changed on a running fleet with no restart
# and no edit to anything git tracks.
LOG_LEVEL                   = os.environ.get("OT_LOG_LEVEL", "INFO").upper()
# r194 (BOX.16): OT_LOG_FILE moves the log for ONE process - the lander and the boot
# sweep point every checker's at scratch, because main attaches its file handler to
# this path AT IMPORT and every checker that imports main was writing into the box's
# live bot.log. Unset (the bot, always) it is the path it always was.
LOG_FILE                    = os.environ.get("OT_LOG_FILE") or os.path.expanduser("~/options-trader/bot.log")
LOG_ROTATION_MB             = 50

# ─── BOT IDENTITY ─────────────────────────────────────────────────────────────

BOT_NAME                    = os.environ.get("OT_BOT_NAME", "OptionsTrader")

# ─── LIVE EXIT FILL-CONFIRMATION (v3.5) ──────────────────────────────────────
# Governs ExitEngine._confirm_and_book_live_exit (live/cash mode ONLY — the
# paper path never reads these). See FABLE_SPEC_live_exit_fill_confirmation.md.

# Seconds between broker order-status polls while a close order is working.
LIVE_FILL_POLL_SECONDS      = float(os.environ.get("OT_LIVE_FILL_POLL_SECONDS", "2"))
# Total seconds to wait for a fill before cancelling and handing the position
# back to the caller's retry loop (15:45→16:00 hard-close retries + paging).
LIVE_FILL_DEADLINE_SECONDS  = float(os.environ.get("OT_LIVE_FILL_DEADLINE_SECONDS", "8"))   # r295: 30 -> 8, mirror of otv4 r474 (F1); the operator, 10-05: "get it down to eight seconds"
# Marketable-limit buffer ($/share THROUGH the mark) for multi-leg closes.
# tastytrade rejects MARKET orders on spreads, so closes go out as aggressive
# limits: vertical debit = min(mark + buffer, spread width); butterfly credit
# = max(mark - buffer, one tick). Retry ticks re-price at a fresh mark.
LIVE_CLOSE_LIMIT_BUFFER     = float(os.environ.get("OT_LIVE_CLOSE_LIMIT_BUFFER", "0.10"))
# v1.9 (audit defect O): bounded fill-confirmation window for ENTRY orders.
# Entries are optional (unlike exits): unfilled at the deadline -> cancel and
# walk away; the strategy re-evaluates next tick. Whatever DID fill is booked.
LIVE_ENTRY_DEADLINE_SECONDS = float(os.environ.get("OT_LIVE_ENTRY_DEADLINE_SECONDS", "20"))


@dataclass
class SessionConfig:
    """Runtime session config — populated at startup."""
    paper_trading:      bool    = True
    # r146 — no guessed symbol. The field cannot be REQUIRED (it follows a
    # defaulted field), so its default is UNSET and __post_init__ REFUSES it:
    # a SessionConfig built without instrument= fails loudly, never trades QQQ.
    instrument:         str     = INSTRUMENT_UNSET
    risk_per_trade_usd: float   = 200.0
    notes:              str     = ""
    confirmed_at:       Optional[str] = None

    def __post_init__(self):
        if not self.instrument or self.instrument == INSTRUMENT_UNSET:
            raise ValueError("SessionConfig built without an instrument - OT_INSTRUMENT "
                             "is not set; refusing to guess a symbol (r146)")

# ─── CONTINUATION (trend-pullback) exhaustion exit ────────────────────────────
# Exhaustion detection for the trend-continuation runner. Extension tightens the
# trail; momentum divergence exits. All env-tunable for paper-phase calibration.
# Continuation stop. 2026-07-22: 0.40 -> 0.25 per user directive. The 40%
# blanket floor (MAX_LOSS_PCT) is a DISASTER backstop sized for trades whose
# primary stop is structural; the continuation trade's primary stop is the
# therefore dead weight that only ever paid out on a gap. 25% keeps the
# backstop meaningful without letting a dead thesis bleed.
CONTINUATION_STOP_LOSS_PCT      = float(os.environ.get("OT_CONT_STOP_PCT", "0.15"))
CONTINUATION_EXHAUST_EXT_ATR    = float(os.environ.get("OT_CONT_EXT_ATR", "2.0"))   # ATRs from midline = "stretched"
CONTINUATION_EXHAUST_MIN_GAIN   = float(os.environ.get("OT_CONT_MIN_GAIN", "0.15")) # only manage exhaustion past +15%
CONTINUATION_EXHAUST_TRAIL_LOCK = float(os.environ.get("OT_CONT_TRAIL_LOCK", "0.85"))# extension tightens trail to 85% of premium

# ── CONTINUATION 1-BAR CONFIRMATION (v1.5, 2026-08-10) ───────────────────────
# The FVG tag alone commits while price is still moving AGAINST the trend —
# a bet on a resumption that has not happened. With this ON, the bar AFTER the
# tag must close BEYOND the tagging bar's extreme in the trend direction before
# an entry is taken. Fewer trades, later entries, and the ones that never
# confirm are simply never taken.
# OT_CONT_REQUIRE_CONFIRM=0 restores the pre-v1.5 behaviour exactly, which
# makes this knob its own A/B control rather than a one-way door.
CONTINUATION_REQUIRE_CONFIRM = os.getenv("OT_CONT_REQUIRE_CONFIRM", "1") == "1"

# ── BOS MINIMUM DISTANCE (exit_engine v4.15, 2026-08-10) ─────────────────────
# BOS seeds its protected level from the LOW of the first bar closing above
# entry. On a pullback entry that bar is the smallest, earliest part of the
# resumption, so the level lands inside the symbol's own noise band and the next
# ordinary wiggle fires it. Observed live 2026-08-10: JPM in $1.26 12:49, out
# $0.00 12:50, back in $1.26 the same minute — the exit condition was already
# true at entry. QQQ fragmented one move into four scratches the same session.
# Expressed in ATR so it scales with the symbol; a raw price gap could not.
# 0.0 restores the pre-v4.15 behaviour exactly (kill switch and A/B control).
BOS_MIN_DIST_ATR = float(os.getenv("OT_BOS_MIN_DIST_ATR", "0.35"))

# A trend continuation is, definitionally, a trend resuming after a pullback.
# RANGING and COMPRESSION are the assertion that there is NO trend to continue,
# so a continuation entry there is not a marginal call — it is a contradiction.
# It happened anyway because the dispatch gate reads
# and `_is_runaway` BYPASSES THE LABEL ENTIRELY. So an ORB runaway flag let
# continuation fire on any tape at Priority 2 — ahead of Butterfly (P3, needs
# RANGING/COMPRESSION) and Condor (P4, needs RANGING), both of which sit behind
# `if signal is None` and were therefore never evaluated.
# MEASURED over 13 sessions: RANGING → Continuation 94 trades vs IronCondor 27;
# COMPRESSION → Continuation 39 vs Butterfly 6. Continuation took 3.5x the
# strategies exist for.
# CNT.3 already blocked the handoff in COMPRESSION, but only INSIDE the strategy
# and only for the handoff path — RANGING was never covered, and a strategy-level
# check cannot stop the slot being consumed before P3/P4 are reached.
# Set to 0 to restore the pre-CNT.6 behaviour exactly (kill switch and A/B).
# that branch was unreachable. OT_CONT_BLOCK_PREMIUM is now INERT.

# ── CONTINUATION CONFIRMATION TOLERANCE (v1.6, 2026-08-11) ───────────────────
# v1.5 required the confirmation bar to close STRICTLY beyond the tagging bar's
# extreme. Measured on the first live session, that failed BY PENNIES:
#   QQQ  need < 720.26  got 720.34   (8c, 0.011%)
#   PLTR need < 175.18  got 175.22   (4c, 0.023%)
#   CVX  need > 194.94  got 194.91   (3c)
#   TSLA need > 334.39  got 334.35   (4c)
#   SPX  need < 7735.58 got 7737.13  (1.55, 0.02%)
# Those are TIES, not failed resumptions — the bar closed essentially AT the
# extreme and was rejected on a rounding-level margin. The thesis is right; the
# comparison was too literal.
# Expressed in ATR so it scales with the symbol: an 8c miss is nothing on QQQ
# and everything on GLD, and a fixed cent value could never serve both.
# 0.40 IS DERIVED FROM THE SESSION, NOT PREFERRED. Expressing every logged miss
# in ATR units produces a CLEAN GAP with nothing in it:
#   near-misses (ties):  0.073 · 0.229 · 0.300 · 0.318 · 0.333 · 0.344 · 0.360
#   genuine failures:    1.133 · 1.442 · 1.694 · 1.743 · 3.355
# The two populations separate at better than 3x, so any value between 0.36 and
# 1.13 splits them and 0.40 sits just past the near-miss tail with a wide margin
# before the nearest real failure. My first draft used 0.05 and would have
# rejected EVERY case above — a no-op wearing the name of a fix, caught only by
# testing the constant against the actual logged misses instead of shipping it.
# ⚠️ ONE SESSION. The gap is wide and the classes are unambiguous, but this is
# a single day's evidence — re-derive it once a week of post-deploy misses
# exists rather than treating 0.40 as settled.
# 0.0 restores the strict v1.5 comparison exactly (kill switch and A/B control).
CONT_CONFIRM_TOL_ATR = float(os.getenv("OT_CONT_CONFIRM_TOL_ATR", "0.40"))

# ── SWP.4 (2026-08-11) — RECOVERY MEASURED FROM THE SWEPT LEVEL ──────────────
# The entry-distance gate measured recovery from `sweep.sweep_price` (the wick
# extreme of the raid), so a DEEPER rejection made the entry look FARTHER away
# and the gate refused the best setups. On a fabricated textbook PDL raid a
# 2.36% rejection produced a 2.4% "recovery" against the 2.0% cap and was
# rejected outright. Measured from the POOL (the level reclaimed — the thesis
# actually being traded) the same setup reads 0.11%.
# Wick depth is rejection QUALITY and `rejq_val` already scores it; it has no
# business inflating a distance-from-entry measure.
# 0 restores the pre-SWP.4 anchor exactly (kill switch and A/B control).
SWEEP_RECOVERY_FROM_POOL = os.environ.get("OT_SWEEP_RECOVERY_FROM_POOL", "1") == "1"

# ── SWP.5 (2026-08-11) — LIVENESS REPLACES THE CLOCK ────────────────────────
# `SWEEP_MAX_AGE_BARS = 8` was standing in for an invalidation test the code did
# not have. MEASURED over 90 real symbol-days: of the stale sweeps it refused,
# **32.9% still had a LIVE thesis** — price had never accepted back through the
# raided level and was still on the correct side. ~9.5 valid setups discarded
# per symbol-day, on a clock.
# The right test already exists in spirit: `veto_accept` asks whether price
# accepted beyond the level — it is just a BIRTH-TIME snapshot. LIQ.3 makes it
# a running check, and this gate reads it.
# ⚠️ THE BACKSTOP IS DELIBERATE. A level that still holds at 5 hours is a
# different trade from a fresh raid, and this is a collection phase. 48 bars
# (5m-equivalent) = 4 hours: generous enough to keep the 32.9%, bounded enough
# that "still holding" cannot mean "all week".
SWEEP_LIVENESS_GATE   = os.environ.get("OT_SWEEP_LIVENESS_GATE", "1") == "1"
SWEEP_STALE_HARD_BARS = int(os.environ.get("OT_SWEEP_STALE_HARD_BARS", "48"))

# ── VEL.1 (2026-08-12) — VELOCITY STALL: "is this thing MOVING at all?" ──────
# The third question, and until now nobody asked it. `orb_structure_stop` asks
# "did the thesis break?"; `_theta_bleed` asks "is my GAIN about to evaporate?"
# (gate 1 is a gain floor, so it never looks at a losing position). A LOSING
# POSITION THAT HAS STOPPED MOVING answers NO to both and falls to the -40%
# percentage floor, which is the ABSENCE of a mechanism rather than one.
#
# THE STATISTIC, and note it needs NO TARGET — which is why it generalises to
# every long-premium strategy, not just ORB:
#     breakeven velocity  bev = |theta| / (|delta| * 1440)     underlying pts/min
#                               at which delta gains exactly offset decay.
#     delivered velocity        cumulative underlying travel toward the trade's
#                               direction, per minute since entry.
#     ratio = delivered / bev.  1.0 is the FLAT LINE. Below it the position
#                               bleeds even while the thesis is intact.
#
# MEASURED over 15 sessions / 145 ORB trades against the chain archive
# (tests/velocity_feasibility.py), among trades STILL OPEN at each mark:
#            mark   winners p10   losers p50   losers p90
#             5m       -21.1         -37.3        91.3     <- NO SEPARATION
#            10m         3.9          -6.7        20.5
#            15m        18.0           0.3        26.7
#            20m        29.8           0.9        18.5     <- barely overlap
# The median surviving LOSER sits at ~1.0 — treading water exactly at breakeven
# marginal difference.
#
# ⚠️ THE 5-MINUTE ROW IS WHY GRACE EXISTS: winners p10 of -21.1 means the bottom
# decile of eventual WINNERS was moving AWAY at five minutes. Any evaluation
# before 10 minutes kills those trades. GRACE is forced by data, not chosen.
#
# ⚠️ THE FLOOR IS DERIVED, NOT PICKED. Each value is the winners' p10 at that
# mark, so a floor at STRICTNESS=1.0 admits 90% of historical winners BY
# CONSTRUCTION. Re-run the study to refresh it; do not hand-tune it.
VELOCITY_STALL_ENABLED  = os.environ.get("OT_VELOCITY_STALL", "1") == "1"
# ⚠️ SHIPS OBSERVE-ONLY. The floors rest on n=22 at the 20-minute mark and were
# derived from ORB alone. Log the breach, collect a session, THEN enforce.
VELOCITY_STALL_ENFORCE  = os.environ.get("OT_VELOCITY_ENFORCE", "0") == "1"
VELOCITY_GRACE_MIN      = float(os.environ.get("OT_VELOCITY_GRACE_MIN", "10"))
VELOCITY_STRICTNESS     = float(os.environ.get("OT_VELOCITY_STRICTNESS", "1.0"))
# consecutive breaches before cutting. ⚠️ NOT COSMETIC: the 2026-08-12 QQQ trade
# crossed back ABOVE breakeven at minutes 41-61 before dying at 70. A single-tick
# rule oscillates; confirmation is what makes the cumulative form usable.
VELOCITY_CONFIRM_TICKS  = int(os.environ.get("OT_VELOCITY_CONFIRM", "3"))
# minutes -> winners p10 ratio. Largest mark <= held wins; under the first mark
# no check runs at all.
VELOCITY_FLOOR_BY_MIN   = {10: 3.9, 15: 18.0, 20: 29.8}
# ⚠️ Strategies whose floor has been MEASURED. Others are evaluated and LOGGED
# but never cut, whatever ENFORCE says — the floors above are ORB-derived and
# applying them blind to continuation or sweep would be an untested extrapolation
# wearing a measured number.
VELOCITY_MEASURED_STRATEGIES = ("ORBStrategy",)
