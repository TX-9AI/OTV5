"""
strategy/sweep_credit_spread.py  v5.8
v5.8  2026-11-08  OTV5 r88 (RETIRE.3) — strike_beyond_sweep() is deleted: its last reader was strategy/tcs_plan.py. _symbol_of (the Hunt) and is_breach_exit with SPENT_EXIT_PREFIXES (trade_logger) stay. The operator, 2026-11-08: "Delete" (the TCS shadow, which never fired: its own gates declined every candidate 11-02..11-06).
v5.7  2026-11-08  OTV5 r76 (RETIRE.1) — THE RETIRED SWEEP TRADE IS REMOVED; FOUR HELPERS STAY. SweepCreditSpreadStrategy,
      its gates, window, level ranking, spent-level keys and pierce logic leave with strategy/sweep_plan.py. Kept,
      byte for byte, because live code reads them: strike_beyond_sweep and _symbol_of (strategy/tcs_plan.py, the TCS
      shadow; strategy/liquidity_hunt.py) and is_breach_exit with SPENT_EXIT_PREFIXES (database/trade_logger.py). The
      operator, 2026-11-07: "Running dead code and logging dead code activity is unnecessary drag. Yes, I want all
      of those things fixed."
v5.6  2026-10-25  OTV5 r9 (GATE.7) — the session-open pin reaches the plan. prepare() and generate_signal() take session_open_epoch (default 0.0) and forward it to plan.prepare; they swallowed it in **_ignored, so a checker's pin never arrived and before 09:30 ET CD.2's bound was a future epoch (QQQ-TEST MSG-QQQ-1025-04). The live path passes no pin, so it reads today's 09:30 ET exactly as before: no behaviour change.
v5.5  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ... (v5.0 was already spent by this file's own history, so the reset lands at v5.5.)
v6.7  2026-10-03  OTV4TEST r193 (CFG.1) — its config dials are read as config.NAME with NO literal fallback; config v4.48 now defines them (they were getattr defaults on names config never had). Values unchanged.
v6.6  2026-09-26  OTV4TEST r148 (WIN.1) — reads its entry window from config with NO literal fallback (one table, config.ENTRY_WINDOWS); a missing name now fails at import instead of silently defaulting. Value unchanged.
v6.5  2026-09-22  OTV4TEST r105 - `sig.sweep_age_bars` REMOVED, not repaired.
      A hardcoded 0 that nothing decided on: its ONLY consumer was
      signal_journal's factor column, and that file's own note calls a constant
      there "a misleading 0". Operator's ruling: age is necessary to ORDER the
      levels by recency and "not relevant to anything else". The measurement is
      NOT lost - the rejection's real age is banked on the PLAN row as
      `rejection_age_bars`. r241's claim that the measurement rides the trade
      row is STRUCK in place per SS35: there was never such a column.
v6.4  2026-09-22  OTV4TEST r102 - NO BEHAVIOUR CHANGE. Records, in the one
      place a reader will look, that `sig.sweep_age_bars = 0` is r5's
      DELIBERATE decision (the trigger IS a fresh rejection, pinned by
      check_sweep_liveness L3) and that the inherited mainline gate
      check_age_gate_gone A3 asserted the opposite. Both gates were in this
      tree and the disagreement was invisible because A3 crashed first.
v6.3  2026-09-13  OTV4TEST r25 — THE SPENT LOCK KNOWS BOTH LABELS A BREACH CLOSES UNDER.
      r24 matched only exit_engine's `sweep_breach_accepted` / `tcs_breach`. But
      strategy/management.py acts FIRST, and when the row carries an
      underlying_stop it closes a breach as `breach: 1m close … through …` (TCS)
      or `acceptance: …` (sweep) — and a TCS row ALWAYS carries its bound, so a
      live TCS breach would have closed under a label the lock never read, and
      its level would have been sold again. Friday's one breach row carried the
      engine label only because that sweep had no underlying_stop. One tuple,
      `SPENT_EXIT_PREFIXES`, read by `is_breach_exit()` here and in trade_logger's
      log line, so the lock and the log cannot disagree.
v6.2  2026-09-13  OTV4TEST r24 — THE SPENT LOCK IS READ FROM trades.db. `_SPENT`, `_SPENT_DAY`
      and `mark_spent` are DELETED: the dict's only writer raised "no such column:
      is_credit_vertical" on every close, so no level was ever marked, and on
      2026-09-11 the 12:04 spread re-sold the 717.05 level the 11:40 spread had
      just exited as SPENT. `is_spent` now derives the lock from today's closed
      sweep/TCS rows that exited on their BREACH (acceptance only, r5), same key,
      and fails closed.
v6.1  2026-09-09  OTV4TEST r11 — `complement_min_richness` passes through to the plan:
      as a condor's second leg the sweep must be at least as rich as leg one.
v6.0  2026-09-09  OTV4TEST r5 — THE STRATEGY IS THE SPEC; THE PLAN SELECTS
      (PLAN_SPEC §31, agreed with the operator 2026-09-08/09). `prepare()` —
      the private wick detector over `liq_map.sweeps`, the level ranking, the
      age rule, the selection against the wick's extreme and `search_wing`
      — moved to `strategy/sweep_plan.py`, where it reads its levels in play
      from the derived level store (3 named up, 3 down, the 1h tines) and
      fires on the REJECTED fact (derived/levels v4.1/4.2) — the same event
      that ends an ORB or runaway position, so the handoff is one tick. The
      short strike anchors on THE LEVEL (the held extreme), not the wick.
      Window 09:35–14:00 (the afternoon gate was a clock standing in for the
      handoff). The age rule is retired (a previously held extreme is enough).
      `strike_beyond_sweep`, `boundary_from_sweep`, `mark_spent`/`is_spent`,
      `level_rank`, `_sweep_at_level`, `pierced_strike` and the doctrine header
      stay here — the plan and the trade logger import what they use.
v5.4  2026-09-08  r321 — 🔴 THE ENTRY WINDOW NO LONGER RELAXES AT EITHER END.
      Operator: *"The sweep window cannot be relaxed. It needs to remain strict
      at all times at 11:31."* The END was pinned already; the START fell to
      `relaxed.window`'s `relaxed_earliest` default of 09:45, so under relaxed
      this strategy opened 106 minutes before `CREDIT_ENTRY_START_ET` — the
      SAME unchosen default r196 hardened out of the butterfly, never swept
      from here. `check_entry_windows` W5 was green throughout because it reads
      the module constant and never the value `prepare()` computes; W9 now
      asserts the RELAXED-APPLIED window.
v5.3  2026-09-04  r241 — 🔴 THE AGE GATE IS REMOVED, NOT RAISED.
      Operator, 2026-09-04: *"I don't give a rat's ass how old the level is,
      it's still a level. Why are we still measuring the age of them?"* Because
      I only half-shipped his 2026-08-11 ruling — SWP.5 said LIVENESS REPLACES
      THE CLOCK, r230 found it had never reached the code, and I raised the
      ceiling 6 → 48 instead of deleting the gate. My call, not his.
      🔑 AGE MEASURES THE RAID, NOT THE LEVEL. A level swept at 09:45 that has
      held since is the SAME LEVEL at 13:00, arguably better for having held
      longer — and levels are swept all day; the morning's is not the only one
      on the board.
      🔴 MEASURED FLEET-WIDE 08-31..09-04: `age` failed 46,791 of 61,641 (76%)
      and on 333 ticks — 26% of every tick that was ONE gate short — it was the
      ONLY thing refusing. Complete setups, declined for being old.
      ⚠️ `invalidated` ALREADY ANSWERS THIS CORRECTLY: has price ACCEPTED back
      through the level. It fails 73%, a market fact rather than a defect.
      `age` was a second, worse proxy for a question that gate settles — two
      rules for one thing, §35's rot.
      ~~⚠️ THE MEASUREMENT SURVIVES. `sig.sweep_age_bars` still carries it to
      the row.~~ STRUCK 2026-09-22 at r105 — it never reached the trade row (no
      such column) and carried a hardcoded 0 to the journal. The measurement
      that DOES survive is `rejection_age_bars`, on the plan row. Struck rather
      than deleted, per §35 and the r240 precedent.
      ⚠️ AND UNMEASURABLE IS NOT OLD. `bars_ago` absent yields the 999 sentinel
      and refuses under its own name — a data fault, not a staleness judgement,
      and admitting it silently would be absent-is-not-zero again.
v5.2  2026-09-03  r234 — GATED ON THE STOP BASIS, AND THE
      SURVIVABILITY DENOMINATOR WAS 4.15x WRONG. This computed
      `credit * MAX_LOSS_PCT` — 15% OF CREDIT, the inverted rule r155 deleted —
      and fed it to `stop_survivable`, while `exit_engine:1818` fires at 15%
      OF RISK. 0.1455 against 0.6045 on the measured median, and the
      forensics' own "risk-anchored room: median $0.605" matches the ENGINE.
      Survivability was judged against a stop four times tighter than the one
      that exists. Both now read `criteria.stop_distance`. `r_expiry` rides
      record-only and the narration names BOTH bases (r219's lesson: printing
      one and labelling it the other is how it stays invisible).
v5.1  2026-09-03  r233 — 🔴 THE STRIKE MUST CLEAR THE TESTED RANGE, AND THE
      NEAREST LIVE LEVEL WINS. Operator, 2026-09-03: *"the strike cannot sit
      at any level that is part of the testing range... I don't want to get
      stopped out by another retest. It has to be just beyond that, if only a
      little bit"*, and *"the level in question needs to be the closest to the
      current price."*
      🔴 THE HOLE r107 DID NOT SEE, AND ITS OWN DOCSTRING STATES BOTH SIDES OF
      IT three paragraphs apart: *"it sits FURTHER from spot than anything
      price reached"* (the intent) and *"nearest is 7635 — the strike price
      traded THROUGH"* (the deep-pierce case, documented without noticing the
      contradiction). PROVEN AT bd6f25e on the header's own example: pool
      7639.01, wick 7633 gave 7635, which sits BETWEEN them. The candidate
      bound was the POOL when it needed to be the WICK EXTREME; the intent was
      right all along.
      ⚠️ AND IT IS THE NEAREST OF WHAT IS BEYOND — `min(cand)` / `max(cand)`,
      never `min(abs(k - sweep_price))`, which is precisely what let an inside
      strike win. "Just beyond, if only a little bit."
      ⚠️ THE POOL BOUND IS KEPT AND IS NOW IMPLIED — a wick is beyond its pool
      by definition — because it DOCUMENTS the invariant. P4 pins that it never
      binds, so it is known inert rather than assumed so.
      🔑 SELECTION MOVES FROM RECENCY TO DISTANCE. Both branches picked the
      freshest raid — this one by `min(bars_ago)`, the fallback by the map's
      `recent_sweep` — so a level three points out beat one 0.6 points out if
      it landed a bar sooner, and selling the cusp of a distant level is still
      distant. Freshness survives as the TIE-BREAK, which is the only question
      distance cannot answer. `level_rank` is EXTRACTED to module level so the
      checker drives it and not a copy (C.23).
      ⚠️ THE FALLBACK IS NO LONGER `recent_sweep`: leaving it would have put
      leg two on distance and the primary entry on recency — one rule with two
      answers. It survives only when NO candidate carries a usable pool price,
      and says so at INFO.
      ⚠️ THIS RETIRES THE CROSS-TIMEFRAME UNIT BUG AT THIS SITE rather than
      fixing it; SWEEP.6 stays OPEN for the other selector and the mapper.
      ⚠️ MEASURED SCOPE, STATED UP FRONT: `pierce_depth` ran a 0.0032 median
      against a 0.5685 max, so shallow pierces dominate and this re-prices only
      the deep tail. `pierce_pts`, `level_dist_pts` and `level_dist_pct` ride
      the plan RECORD-ONLY so how often it fires is a query, not an argument.
      ⚠️ AND IT DOES NOT FIX THE MEASURED LOSSES. Panel 1 of the 08-25..09-03
      forensics: price never reached the strike on 22 of 22, and the stops were
      mark-driven (r219). A real hole, correctly closed, on a failure mode this
      sample never showed.
v5.0  2026-09-03  r231 — 🔴 `or 999` MADE THE FRESHEST SWEEP THE STALEST.
      `bars_ago` is an int field defaulting to 0 and SWP.10 counts it from the
      RECLAIM bar, so a sweep that reclaimed on the CURRENT bar is 0 — and
      `0 or 999` is 999. Twenty-six lines above, the selection loop takes
      `min(bars_ago)`: it hunts the freshest sweep on the board and this line
      converted exactly that winner into the stale sentinel and refused it.
      One function contradicting itself, invisibly — 999 reads as missing data
      rather than as the best setup there was. Absent stays 999; ZERO stays 0.
      Also: the geometry call now passes `price_now`, so a pool price has
      already traversed is invalidated rather than merely failing a soft
      condition. `side_of_pool` is UNTOUCHED and now tests the same fact
      twice — recorded as SWEEP.7, not folded in unruled.
v4.9  2026-09-03  r230 — 🔴 SWP.5 WAS RULED ON 2026-08-11 AND NEVER REACHED
      THIS FILE. Its ruling: "LIVENESS REPLACES THE CLOCK", measured over 90
      symbol-days — of the stale sweeps the age gate refused, 32.9% still had
      a LIVE thesis (price had never accepted back through the raided level),
      ~9.5 valid setups discarded per symbol-day on a clock. It set a
      deliberate 48-bar backstop and landed `SWEEP_STALE_HARD_BARS` in
      config. This file never read it. It read `SWEEP_CS_MAX_AGE_BARS`, a
      name defined NOWHERE in the tree, so the ceiling was the getattr
      DEFAULT of 6 — a quarter of the old constant and an eighth of the ruled
      one — for three weeks.
      ⚠️ THE OPERATIVE CEILING WAS 18, NOT 6, AND THE DISTINCTION MATTERS.
      The whole fleet is running RELAXED by operator decision (2026-09-03,
      to observe tick-by-tick progression), so `widen(6, 3.0)` gave 18. Ages
      of 33-48 refused ANYWAY. Recording 6 alone would have understated the
      gate and left the next reader unable to reproduce the refusal.
      🔑 NET EFFECT ON A RELAXED FLEET: 18 -> 48, a LOOSENING of 2.7x even
      though relaxed no longer applies here. The alternative (keeping x3 on
      48) gives 144 bars against a 78-bar RTH session - unreachable, which
      is not a backstop at all.
      🔑 MEASURED 2026-09-03 from plan_check: `age` FAILED 761/761 on QQQ
      (33-48 bars) and 934/934 on SPX. Every QQQ evaluation clears at 48.
      ⚠️ OPERATOR RULING 2026-09-03: eliminate `relaxed` entirely from the age
      question. The widen call is GONE, not pinned to factor 1.0: the pinned
      idiom `check_gates` recognises (r196) is implemented for `window()`
      ONLY and would have gone red on a pinned `widen()`. Removing the call
      and declaring MAX_AGE_BARS FOUNDATIONAL is STRONGER — the checker now
      refuses any future relax call on it rather than tolerating a pinned
      one. Matches r208, which removed relaxed from the butterfly outright.
      ⚠️ THE LIVENESS TEST IS `invalidated`, ALREADY WIRED AND ALREADY
      CORRECT — it fired 934/934 on SPX today. Age stops being the primary
      filter and becomes the backstop SWP.5 intended. Nothing else moves;
      the sweep's other dials stay loose per the r208 ruling.
v4.8  2026-09-02  r219 — 🔴 THE ENTRY AND THE MARK WERE ON DIFFERENT SIDES OF THE QUOTE.
      `search_wing` priced the credit as short.BID - long.ASK and that number
      became `sig.entry_premium` — the position's entry of record — while
      `position_manager._fetch_current_premium` marks a credit vertical at
      short.MARK - long.MARK. The gap is BOTH HALF-SPREADS, present the
      instant the position opens, and for a credit vertical a higher mark is a
      LOSS. Measured on the fleet's shape: judged $0.37, booked $0.97, gap
      $0.60 — against a lone stop carrying 60.5 cents of room. The position
      was born at its stop.
      🔑 SWEEP FORENSICS 2026-08-25..09-02 SAYS THE UNDERLYING NEVER DID IT:
      38 of 41 stopped, price NEVER reached the short strike on any of 22
      measurable trades, and moved 0.63 points toward it — implying a spread
      delta of 0.96, which a 5-wide cannot carry.
      ⚠️ OPERATOR RULING 2026-09-02: "I have a ladder for live offers, all
      paper needs to fill at mark, period." The MARK is booked. The BID/ASK
      credit is kept for the R hurdle — deciding on the conservative number
      and booking the mark refuses trades that only clear R when priced
      optimistically, so the error runs in the safe direction.
      ⚠️ AND THE OLD BEHAVIOUR HAD A PASSING TEST: check_plan_prepares S2
      asserted net_credit == 1.30, the bid/ask figure, so the suite certified
      the mismatch. Re-derived to 1.33.
v4.7  2026-08-27  r163 — A FORK TINE IS A MOVING LEVEL THIS STRATEGY MAY USE,
      ON A TOUCH. Operator, 2026-08-27: *"it's basically a moving level that
      sweep is allowed to use, but with a touch, not a reject. The plan would
      still need to select a strike beyond the move that caused the touch."*
      And: *"it's allowed to be the 1st leg of a condor too, but again as a
      touch not identical to sweep which requires rejection."*
      The mapper (liquidity_mapper v4.2) publishes each tine as a moving
      named pool and emits a TOUCH event shaped like a sweep (born ready,
      `touch=True`, `sweep_price` = the extreme of the touching move). This
      plan treats it as any other sweep EXCEPT: (1) under the condor's
      AUTHORIZATION (leg two) a touch is NEVER selected — leg two requires a
      rejection at the site; (2) the spent-level lock is keyed by NAME for a
      moving level, since its price drifts every bar; (3) the signal's
      `condor_trigger_source` is `{tf}_fork`, so a tine-touch leg one is
      classed as a fork under Rule 4. The daily-fork strategy is retired —
      its whole job is now the mapper's publication plus this plan.
v4.6  2026-08-27  r160 — THE PLAN PREPARES, THE STRATEGY EXECUTES WITH THE
      PLAN'S VARIABLES. Operator, 2026-08-27, read back and confirmed: the
      plan "evaluates the current tick what would need to be true on the
      next tick for the active strategies to execute — strike selection,
      wing width, stop placement, minimum R"; the strategy declares its
      conditions and executes. `prepare()` is the plan: in the slot, every
      tick, it picks the sweep this spec would trade (the freshest of the
      AUTHORIZED side when the condor narrows it, else the map's most
      recent), evaluates each declared CONDITION with its current reading,
      SELECTS the short beyond the sweep, the wing to R_FLOOR (search_wing),
      the bid/ask credit, the stop and its survivability, and writes the
      row: DORMANT outside the slot · NO PLAN naming a missing input ·
      DECLINE on a STRUCTURAL fault (spent, geometry, no wing clears R, no
      credit, stop inside the spread) · HOLD "PREPARED — <trade>. Waiting
      on: <conditions>" · and on all-true the strategy `generate_signal()`
      executes THAT trade. The strategy no longer touches the chain.
      `required_level` is gone — an authorization narrows the SIDE, it never
      hands this strategy a level (operator: the condor selects nothing).
v4.5  2026-08-27  r154-r158 (RECORDED RETROACTIVELY in r160 — 254 lines
      changed with no title bump and no entry): the spent-level lock
      (mark_spent/is_spent), stop_survivable before entry, the wing searched
      to R_FLOOR via credit_vertical.search_wing (R no longer muted for credit
      spreads), `_sweep_at_level` and the required_side/required_level
      inputs from the condor's permission.
v4.4  2026-08-26  r146 — THE PLAN IS WIRED. Six `_gate()` rungs and fifteen
      bare `return None`s (window, ATR, boundary side, chain, wing, credit …)
      all go through `self.planner` (strategy/plan.py) and write a DECLINE row
      naming the gate; `_gate()` is retained as a thin alias into the plan's
      edge-triggered reporter so nothing that called it breaks. NEW: the
      reclaimed pool is checked against the SHARED SESSION MAP
      (analysis/session_map.py) — a ceiling below the 5-minute opening range,
      or a floor above it, is INVALIDATED BY GEOMETRY per the operator's
      2026-08-25 ruling, before any strike is priced. `orb_high`/`orb_low`
      are new optional kwargs; absent, geometry records n/a and the spec
      proceeds. The what-if is priced off the REAL spread (short at the first
      strike beyond the sweep, wing at WING_WIDTH, credit from bid-ask):
      R = credit / (width - credit). The R hurdle is consulted: STRICT refuses
      below the floor, RELAXED records and proceeds.
v4.3  2026-08-24  r107 THE SHORT STRIKE IS THE FIRST STRIKE BEYOND THE SWEEP
      EXTREME — pierced if there is one, the next one out if there is not, never
      one inside. Operator, 2026-08-24: "It swept. That's legitimately a sweep.
      Sell the 7635." The old rule required a strike to have been TRADED
      THROUGH, which collides with §2's preference for a SHALLOW pierce and
      silently disabled the sweep on the seven 5-wide symbols. Strikes now come
      from the LIVE CHAIN, not STRIKE_INCREMENT: SPX 0DTE is 5-wide near the
      money and 25-wide in the tails, so one constant cannot be right.
v4.2  2026-08-24  r100 — the short-strike anchor no longer falls back to the
      POOL when the pierce cleared no strike. The pool is a price level, so the
      anchor could not resolve against the chain and every SPX fire died at
      "no priced put contract at the pierced strike 7639.01" — a strike that
      does not exist. pierced_strike's own contract says None means there is
      nothing to sell; now that is what happens, with its own log line.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

A named pool was swept and rejected. Sell the boundary it just became.

v4.0  2026-08-19  Built at the OTV4 split. The second v4 entry rule.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

════════════════════════════════════════════════════════════════════════════
THE STRUCTURE, AND WHY IT IS A CREDIT SPREAD AND NOT A LONG CONTRACT
════════════════════════════════════════════════════════════════════════════
    sweep UP into a pool, rejected   -> that pool is now a CEILING
                                     -> CALL credit spread, short at/beyond it
                                     -> price must stay BELOW the ceiling
    sweep DOWN into a pool, rejected -> that pool is now a FLOOR
                                     -> PUT credit spread, short at/beyond it
                                     -> price must stay ABOVE the floor

**The sweep direction decides which kind of boundary the pool became**, and the
spread follows from that. `LiquiditySweep.kind` already records it -
`high_sweep` means highs were taken and rejected DOWN, so the pool is a ceiling.
Nothing needs inferring.

⚠️ WHY CREDIT AND NOT LONG - THIS IS THE POINT OF THE WHOLE STRUCTURE.
A long reversal contract needs price to TRAVEL. `tests/entry_profile.py`
measured that **155 of 190 directionally-CORRECT ContinuationStrategy entries -
82% - never reached +25% MFE.** The read was right and the position did not pay.
`tests/chain_feasibility.py` explains it from the other side: a 0.30-0.60 delta
0DTE contract needs a **0.90% underlying move** to pay +25% after the round-trip
spread, and the tape delivers that in a specified direction on **22%** of
90-bar windows.

**A credit spread does not need magnitude. It needs the level to hold.** That is
a far weaker ask, and the tape agrees: the base rate for a 0.5% move in 90
minutes is only **24-35%**, so roughly two thirds of windows stay put.
**The swept pool is the natural short strike because it is the level that just
FAILED to hold price** - it rejected once, in evidence, not in forecast.

════════════════════════════════════════════════════════════════════════════
WHY v3's SWEEP NEVER FIRED, AND WHAT WAS FIXED
════════════════════════════════════════════════════════════════════════════
`tests/sweep_term_census.py`, 269,027 named-pool rows across 27 sessions:
  · **95.9% HARD-VETOED to 0.000** before scoring - 67% of those by
    `veto_accept`, the `closes_beyond >= 2` rule. Of 25,792 vetoed ticks
    post-08-11, **100% were RECLAIMED and 0% were genuine acceptance**: the veto
    window and the confirmation window were the SAME WINDOW, so the sweep bar's
    own close counted as acceptance. SWP.11 fixed it.
  · Of the 4.1% that survived, `age_decay` median **0.062** - about **12 bars,
    ~60 MINUTES** - while `trend_opp` sat at 1.000. Age was the sole binding
    damper, and it counted from the SWEEP bar rather than the RECLAIM, charging
    the signal for confirmation latency it could not act inside. SWP.10 fixed it.
  · Median surviving score ~0.031 against a 0.05 dispatch floor: **the survivors
    did not clear their own gate.**

⚠️ THIS FILE READS NEITHER. No `age_decay`, no multiplicative damper chain, no
setup score. The sweep either reclaimed and is young, or it is not a setup.
v3's grammar - a product of two soft-necessaries and a weighted corroborator sum
- capped SWEEP at 0.171 out of 1.0 while TRENDING pinned at 1.00, so it could
never win an argmax regardless of evidence.

directional predictor in this data. This rule does not predict a direction; it
sells a boundary that has already rejected price once.

════════════════════════════════════════════════════════════════════════════
GATE CATEGORIES — required by WA §36. Only SELECTION is ever relaxed.
════════════════════════════════════════════════════════════════════════════
**FOUNDATIONAL — never relaxed. Relax one and this stops being the trade.**
  · the pool is NAMED. An unnamed swing high is not a liquidity pool; the name
    is what makes it a level other participants are watching.
  · it RECLAIMED - a bar CLOSED back inside. **A wick through a level is a
    touch, not a decision.** Without the reclaim there is no boundary, only a
    level price is currently through.
  · it is NOT INVALIDATED. Reclaimed-then-accepted-through is a BREAKOUT, and
    selling a boundary that has already given way is the worst version of this.
  · price is ALREADY on the profitable side. Otherwise the spread opens tested.

**SELECTION — relaxed, and each was measured on 2,169 sweep events.**
  · window 13:00-15:00  -> 09:45-15:30   (39% survival vs 26% before 10:30)
  · pierce ceiling 0.25% -> 0.75%        (33-34% survival vs 19-21% deeper)
  · max age 6 bars      -> 18 bars       (age is measured from the RECLAIM)

**FEASIBILITY — never relaxed.**
  · ATR <= 0.20%. Above 0.20% the tape produced a 0.5% move on **92% of 90-bar
    windows** - a boundary does not hold in that, so the trade cannot win no
    matter how clean the setup looks.
"""
import logging

logger = logging.getLogger(__name__)

# ── GATE CATEGORIES AS DATA (WA §36) — none: these helpers locate a strike and read an exit reason; they refuse
#    nothing (r76: the sweep trade, and every gate it declared, is removed).
GATES = {}


# RETIRE.3 (r88): strike_beyond_sweep() is deleted - its last reader was strategy/tcs_plan.py (the TCS shadow).


# Every label a breach/acceptance close is written under. exit_engine's own, and
# strategy/management.py's Intent names — which act first whenever the row carries
# an underlying_stop (always, for a TCS).
SPENT_EXIT_PREFIXES = ("sweep_breach_accepted", "tcs_breach", "breach:", "acceptance:")


def is_breach_exit(exit_reason) -> bool:
    """True when a credit spread closed because its level GAVE WAY (r5: acceptance only)."""
    return str(exit_reason or "").startswith(SPENT_EXIT_PREFIXES)


def _symbol_of() -> str:
    try:
        from config import INSTRUMENT
        return str(INSTRUMENT)
    except Exception:                                          # noqa: BLE001
        return ""
