"""
strategy/sweep_credit_spread.py  v6.7
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
import math
from typing import Optional

import config
from strategy import relaxed
from strategy.base_strategy import OptionsSignal as Signal
from utils.math_utils import safe_float

logger = logging.getLogger(__name__)


def _gate(name: str, reason: str) -> None:
    """r73 — report this rung, edge-triggered. NEVER changes the verdict.

    v4.4 — kept as an alias for any caller outside this file; inside it the
    rungs now go through `PlanTick.refuse()`, which reports the same way AND
    writes the plan_check row the reporter never could.
    """
    try:
        from analysis.gate_report import get_gate_reporter
        from config import INSTRUMENT
        r = get_gate_reporter(INSTRUMENT)
        if r is not None:
            r.blocked("SweepCreditSpread", name, reason)
    except Exception:                                           # noqa: BLE001
        pass

# ⚠️ STATED PRIORS AWAITING MEASUREMENT. v3's sweep book is 34 trades - far too
# thin to fit anything - so these are reasoned, not calibrated, and are
# config-overridable. `tests/sweep_discriminator.py` is the tool that will
# replace them with numbers.
# 🔴 r230 — SWP.5's OWN CONSTANT, IMPORTED DIRECTLY. NOT `getattr` WITH A
# DEFAULT: a getattr default is exactly what let a name defined nowhere
# govern fifteen boxes silently. A missing constant must raise at import on
# the first box that pulls it, not fall back to a number nobody chose.
# 🔴 r241 — `MAX_AGE_BARS` IS GONE. Not raised, not pinned: REMOVED. r230
# raised it 6 -> 48 and that was the half-measure; the operator's 08-11 ruling
# was that liveness replaces the clock, and `invalidated` is the liveness test.
# ⚠️ WHAT REPLACES IT IS NOT A THRESHOLD. The 999 sentinel means `bars_ago`
# could not be read at all, which is a DATA fault and not a staleness one, so
# it refuses by its own name rather than through an age ceiling.
_AGE_UNMEASURABLE = 999
# ⚠️ WAS 0.002 (0.20%) - A PRE-MEASUREMENT GUESS THE DATA CONTRADICTS. Combined
# with the new 0.25% ceiling it left a 0.20-0.25% sliver and EXCLUDED the
# shallow bucket that measured BEST: <0.10% pierces survived on 33%, and
# 0.10-0.25% on 34%, both above the 30% base. The floor exists only to reject a
# level that was never really touched, so it belongs far lower.
MIN_REJECTION_PCT = config.SWEEP_CS_MIN_REJECTION_PCT

# ── MEASURED 2026-08-20, tests/sweep_discriminator.py ──────────────────────
# 2,169 PDH/PDL sweep-and-reclaim events across the banked tape, ONE outcome per
# sweep. Outcome = the boundary held to the bell AND was never breached far
# enough to have taken the 15% stop (adverse < 0.35% of the level).
#
#   BASE RATE, all sweeps:                    30% survived
#
#   BY TIME OF THE RECLAIM        n     survived   p50 adverse
#     before 10:30              927        26%        0.84%   below base
#     10:30 - 13:00             758        29%        0.58%   same as base
#     13:00 - 14:30             223        39%        0.30%   BEATS base
#     after 14:30               261        39%        0.32%   BEATS base
#
# **The afternoon nearly doubles survival and HALVES the adverse excursion.**
# Window moved from 10:00-15:00 to 13:00-15:00.
#
# ⚠️ THE `SESSION TIME REMAINING` TABLE IS THE SAME FINDING, NOT A SECOND ONE.
# "after 13:00" and "fewer than 150 bars left" select largely the same events;
# less session remaining means less time for the boundary to be tested. Treating
# them as independent confirmation would be double-counting one effect.
EARLIEST_ET = config.SWEEP_CS_EARLIEST_ET       # r148: no literal fallback
# 🔴 r98 (2026-08-24) — 15:00 WAS TOO LATE AND RELAXED MADE IT 15:30.
# Operator: "Close the window on sweep to 1400 also. That entry is way too
# late." A credit vertical opened at 15:00 has 45 minutes to the 15:45 hard
# close: it cannot collect the theta it exists to collect, and it is judged on
# a boundary test the session has no time to deliver. `relaxed.window` widened
# the late side to 15:30, which is worse still — 15:30 collides with the 15:40
# flatten ladder, so a relaxed sweep could open a position that is closed ten
# minutes later by the clock rather than by its thesis.
LATEST_ET = config.SWEEP_CS_LATEST_ET           # r148: no literal fallback

# ── AND A CEILING ON THE PIERCE DEPTH ──────────────────────────────────────
#   BY REJECTION DEPTH            n     survived   p50 adverse
#     shallow < 0.10%           746        33%        0.46%   BEATS base
#     0.10 - 0.25%              817        34%        0.53%   BEATS base
#     0.25 - 0.50%              368        21%        0.75%   below base
#     deep > 0.50%              238        19%        1.28%   below base
#
# ⚠️ THE MECHANISM IS IN THE ADVERSE COLUMN, and it is the opposite of the
# intuition that a big rejection is a strong rejection. A DEEP pierce means the
# level barely rejected at all - price was willing to go there, and it comes
# back: 1.28% median adverse against 0.46% for a shallow pierce. **Depth of
# pierce measures the level's WEAKNESS, not the strength of its defence.**
MAX_REJECTION_PCT = getattr(config, "SWEEP_CS_MAX_REJECTION_PCT", 0.0025)

# ⚠️ WHAT THIS DOES NOT ESTABLISH. The best cell is ~39-40% survival. A spread
# that wins when the boundary holds and loses 15% when it does not needs the
# CREDIT to exceed roughly 1.5x the loss to break even at that rate. **These are
# entry conditions, not a profitability finding** - that depends on credit
# received against the stop, which is a chain question and has not been asked.
# ⚠️ AND POOL TYPE DID NOTHING: PDH 32%, PDL 28%, both at base. The stated grade
# priors in level_grade.py get NO support from this measurement.
ATR_MAX_PCT = config.SWEEP_CS_ATR_MAX_PCT

# ── EXITS: exactly two, and no others ──────────────────────────────────────
# Operator, 2026-08-20: *"The only 2 ways I want out of this trade is a 15% loss
# (thesis invalidated) or a session hard close."*
#   · 15% stop - the thesis is that the swept pool HOLDS as a boundary. A 15%
#     loss says it did not, and there is nothing further to wait for.
#   · 15:45 hard close - held to the bell, EXEMPT from the 15:40 flatten
#     ladder like every credit vertical. `strategy/structure.py` routes it there
#     by DERIVING from persisted columns (strategy / setup_type), never a flag:
#     `is_trend_credit` was written as a field with NO COLUMN and crash-looped
#     NFLX every 15 seconds.
# ⚠️ NO TRAIL AND NO PROFIT TARGET. Measured: v3's condor backtest found a TP
# was WORSE AT EVERY LEVEL on 28 condor legs, and on 18 standalone legs TP@25%
# turned -$242.77 into -$8.43. A credit vertical is EARNING from decay; closing
# it early buys back the theta it was opened to collect.
MAX_LOSS_PCT = getattr(config, "SWEEP_CS_MAX_LOSS_PCT", 0.15)
WING_WIDTH = getattr(config, "SWEEP_CS_WING_WIDTH", 5.0)

# ── GATE CATEGORIES AS DATA (WA §36) ───────────────────────────────────────
# ⚠️ CHECKED BY `tests/check_gates.py`, WHICH READS THE CODE. The prose block in
# the header explains WHY each gate is what it is; this dict is what makes the
# rule enforceable - the checker refuses any `relaxed.widen()` or
# `relaxed.window()` call on a constant not marked SELECTION.
GATES = {
    # SELECTION - measured preferences. A looser one gives a WORSE example of
    # the same trade, which is what a debug session wants.
    "EARLIEST_ET":        "SELECTION",
    "LATEST_ET":          "SELECTION",
    "MAX_REJECTION_PCT":  "SELECTION",
    "MIN_REJECTION_PCT":  "SELECTION",
    # FOUNDATIONAL - r230, operator ruling 2026-09-03. SWP.5's own words:
    # "a level that still holds at 5 hours is a DIFFERENT trade from a fresh
    # raid" - which is the §36 definition of foundational, not selection. It
    # has NO relax call at all now, so the checker refuses any future one.
    # FEASIBILITY - above 0.20% ATR the tape produced a 0.5% move on 92% of
    # 90-bar windows. A boundary does not hold in that.
    "ATR_MAX_PCT":        "FEASIBILITY",
    # FOUNDATIONAL conditions are not constants - they are the named pool, the
    # reclaim, the non-invalidation and price being on the profitable side, all
    # tested inline. **They have no knob to relax, which is the safest form a
    # foundational gate can take.**
}


def level_rank(sw, price_now: float):
    """Sort key for choosing WHICH swept level to prepare, or None if unusable.

    🔴 r233 — DISTANCE FROM SPOT FIRST, FRESHNESS ONLY AS THE TIE-BREAK.
    Operator, 2026-09-03: *"the level in question needs to be the closest to
    the current price."* Both selection branches used recency, so a raid on a
    level three points out beat one 0.6 points out if it landed a bar sooner —
    and selling the cusp of a distant level is still distant.

    ⚠️ EXTRACTED TO MODULE LEVEL SO THE CHECKER DRIVES THIS AND NOT A COPY.
    As a closure inside `prepare()` it was unimportable, and a test that
    re-implements the ranking it pins tests itself — C.23, the r181 sizing
    checker that stayed green for two days doing exactly that.

    ⚠️ None IS UNUSABLE, NEVER A LARGE DISTANCE. A sweep with no pool price
    must drop out of the ranking rather than sort last, or a missing field
    becomes a far-away level and the caller cannot tell the two apart.
    """
    try:
        _p = float(getattr(sw, "pool_price", 0.0) or 0.0)
        _n = float(price_now or 0.0)
    except (TypeError, ValueError):
        return None
    if _p <= 0 or _n <= 0:
        return None
    return (abs(_p - _n), int(getattr(sw, "bars_ago", 999) or 0))


def strike_beyond_sweep(sweep_price: float, pool_price: float, ceiling: bool,
                        contracts=None, increment: float = 0.0) -> Optional[float]:
    """🔴 r107 — THE FIRST STRIKE BEYOND THE SWEEP EXTREME. Operator's ruling,
    2026-08-24: "It swept. That's legitimately a sweep. Sell the 7635."

    ⚠️ WHY THE OLD RULE DECLINED A GOOD TRADE. `pierced_strike` returned the
    nearest strike price actually TRADED THROUGH, and None when the pierce
    cleared none — reasonable prose that collided with the selection spec on
    every wide-strike symbol. SPX 2026-08-24: NY Low 7639.01, price traded to
    7638.17 and closed back inside — a valid sweep of a named pool by 0.84 pts.
    The strikes below are 7635 and 7630; price never reached either, so no
    strike was pierced and a fully-qualified setup was declined. 608 fires died
    that way on one box in one session.
    ⚠️ AND THE TWO RULES PULL OPPOSITE WAYS. §2 PREFERS a shallow pierce —
    ceiling 0.25%, and "a deep pierce means a WEAK level, not a strong
    rejection" (1.28% median adverse vs 0.46%). A strike rule that requires a
    DEEP pierce therefore refuses exactly the sweeps the selection rule likes,
    and it refuses them only on 5-wide symbols: seven of the fifteen boxes. A
    selection effect invisible as "no setups".
    ⚠️ THE OPERATOR'S RULE KEEPS THE INTENT AND DROPS THE PRECONDITION. The
    short strike is the first strike BEYOND the sweep extreme — the pierced one
    when the sweep cleared it, the next one out when it did not. Either way it
    sits FURTHER from spot than anything price reached, so the position is
    threatened only by price going somewhere it has not been. Never a strike
    INSIDE the pierce: that is a level that already failed, and selling it is
    the "worst version of this" §2 warns about.

    ⚠️ STRIKES COME FROM THE LIVE CHAIN, NOT FROM A CONSTANT. `STRIKE_INCREMENT`
    is one number per symbol from a hardcoded map; SPX 0DTE is 5-wide near the
    money and 25-wide in the tails, so no single number is right everywhere —
    and FRC.2's own notes call that class of list "unverified — a broker/OCC
    fact, not derivable here". The chain is the fact. `increment` remains as the
    fallback for a caller with no chain.

    Returns None only when there is genuinely no strike beyond the sweep — an
    extreme past the end of the chain, which is a missing chain, not a trade.
    """
    sweep_price = safe_float(sweep_price)
    pool_price = safe_float(pool_price)
    if not sweep_price or not pool_price:
        return None

    ks = []
    for c in (contracts or []):
        try:
            k = float(getattr(c, "strike", 0.0) or 0.0)
            if k > 0:
                ks.append(k)
        except (TypeError, ValueError):
            continue
    # THE RULE, ONE LINE: among strikes AT OR BEYOND THE POOL, take the one
    # NEAREST THE SWEEP EXTREME.
    # ⚠️ IT UNIFIES BOTH CASES AND CHANGES ONLY THE ONE THE OPERATOR RULED ON.
    # Deep pierce, pool 7639.01, extreme 7633: strikes beyond the pool are
    # 7635, 7630, ...; nearest to 7633 is 7635 — the strike price traded
    # THROUGH, which is the original rule, unchanged. Shallow pierce, extreme
    # 7638.17: nearest is still 7635, which is now the first strike BEYOND
    # rather than a decline. One expression, both readings.
    # ⚠️ "AT OR BEYOND THE POOL" IS THE GUARD THAT MATTERS. Without it the
    # nearest strike to a shallow extreme could be 7640 — INSIDE the pool, on
    # the spot side of a boundary price never broke. Selling that is selling a
    # level the sweep did not establish.
    def _pick(strikes):
        if ceiling:
            # \U0001f534 r233 - AT OR BEYOND THE **WICK EXTREME**, NOT MERELY THE POOL.
            # Operator, 2026-09-03: *"the strike cannot sit at any level that is
            # part of the testing range. I do not want to get stopped out by
            # another retest. It has to be just beyond that, if only a little
            # bit."*
            # \u26a0\ufe0f THIS CLOSES A HOLE r107 DID NOT SEE, and its own docstring
            # states BOTH sides of it three paragraphs apart: "it sits FURTHER
            # from spot than anything price reached" (the intent) and "nearest
            # is 7635 - the strike price traded THROUGH" (the deep-pierce case).
            # PROVEN AT bd6f25e on the header's own two examples: pool 7639.01,
            # shallow wick 7638.17 -> 7635, beyond the wick, correct; DEEP wick
            # 7633.00 -> 7635, which sits BETWEEN the wick and the pool. Price
            # traded clean through 7635 on its way to 7633, so a second test of
            # the same size takes the position out. The intent was right; the
            # candidate bound was the pool when it needed to be the extreme.
            # \u26a0\ufe0f THE POOL BOUND IS KEPT AND IS NOW IMPLIED - a wick is beyond
            # its pool by definition, so this can only ever narrow the set. It
            # stays because it DOCUMENTS the invariant, and check_strike_beyond
            # P3 pins that it never binds; a guard proven inert is different
            # from one deleted on the assumption that it is.
            cand = [k for k in strikes
                    if k >= pool_price - 1e-9 and k >= sweep_price - 1e-9]
        else:
            cand = [k for k in strikes
                    if k <= pool_price + 1e-9 and k <= sweep_price + 1e-9]
        if not cand:
            return None
        # "just beyond, if only a little bit" - the NEAREST of what is beyond,
        # never the nearest in absolute terms, which is what let an inside
        # strike win on a deep pierce.
        best = min(cand) if ceiling else max(cand)
        # ⚠️ A TRUNCATED CHAIN MUST NOT BECOME A WILD STRIKE. "Nearest" always
        # returns something; if the extreme lies past the end of the chain the
        # nearest strike can be hundreds of points away, and selling it would be
        # a trade nobody described. Bound it to a few grid steps of the extreme
        # and decline beyond that — a chain that does not reach the tape is a
        # DATA problem and says so.
        gaps = [b - a for a, b in zip(cand, cand[1:])] if len(cand) > 1 else []
        step = min(gaps) if gaps else (safe_float(increment) or 0.0)
        if step and abs(best - sweep_price) > 3.0 * step:
            logger.warning(
                "[sweep_cs] nearest strike %.2f is %.2f from the sweep extreme "
                "%.2f (grid ~%.2f) — the chain does not reach the tape; "
                "declining rather than selling a strike nobody chose",
                best, abs(best - sweep_price), sweep_price, step)
            return None
        return round(best, 4)

    if ks:
        return _pick(sorted(set(ks)))

    # No chain — fall back to the grid. Same rule, one assumed increment.
    increment = safe_float(increment)
    if not increment or increment <= 0:
        return None
    import math as _m
    if ceiling:
        grid = [_m.floor(sweep_price / increment) * increment,
                _m.ceil(sweep_price / increment) * increment]
    else:
        grid = [_m.floor(sweep_price / increment) * increment,
                _m.ceil(sweep_price / increment) * increment]
    return _pick(sorted(set(grid)))


def pierced_strike(sweep_price: float, pool_price: float, ceiling: bool,
                   increment: float) -> Optional[float]:
    """The NEAREST STRIKE PRICE ACTUALLY PIERCED. Operator's rule, 2026-08-20.

    Not the pool level - the nearest strike price traded THROUGH on the sweep.
    Ceiling: pool 600, price ran to 601.20, retreated to 599.50 -> sell the 601.
    Floor: mirrored downward.

    WHY THIS AND NOT THE POOL. The pierce high is FURTHER from current price
    than the pool is, so the short strike sits further out: less credit, more
    room. **With a 15% stop that is the correct side to err on** - the position
    is threatened only if price returns all the way to a level it already
    visited and failed at, rather than merely back to the boundary.

    ⚠️ ON A SHALLOW PIERCE THE STRIKE COLLAPSES TO THE POOL, and that is
    correct rather than a special case: if price ran to 600.30 with $1 strikes,
    the nearest strike it actually pierced IS the 600. The rule degrades to
    "sell the boundary" exactly when the pierce was too small to clear another
    strike, which is the same trade the boundary framing describes.

    Returns None when the sweep cleared NO strike - price poked past the pool
    without reaching a strike price. There is nothing to sell, and inventing a
    strike here would sell a level that was never tested.
    """
    # ⚠️ math.floor(nan) RAISES "cannot convert float NaN to integer". The
    # truthiness test above passes a NaN happily - `not nan` is False - so the
    # guard read as present and was not.
    sweep_price = safe_float(sweep_price)
    pool_price = safe_float(pool_price)
    increment = safe_float(increment)
    if not sweep_price or not pool_price or not increment or increment <= 0:
        return None
    if ceiling:
        # highest strike at or below the sweep extreme, and at/above the pool
        k = math.floor(sweep_price / increment) * increment
        if k < pool_price:
            return None
        return round(k, 4)
    k = math.ceil(sweep_price / increment) * increment
    if k > pool_price:
        return None
    return round(k, 4)


def boundary_from_sweep(kind: str) -> Optional[tuple]:
    """(boundary, option_side) from the sweep direction.

    `high_sweep` - highs taken and rejected DOWN - makes the pool a CEILING, so
    the trade is a CALL credit spread and price must stay below it.
    `low_sweep` makes it a FLOOR: a PUT credit spread, price stays above.
    """
    k = (kind or "").lower()
    if k.startswith("high"):
        return ("ceiling", "call")
    if k.startswith("low"):
        return ("floor", "put")
    return None


# ═══ SPENT LEVELS — A POOL THAT STOPPED US OUT IS FINISHED ════════════════
# 🔴 OPERATOR, 2026-08-27, watching CVX re-enter the SAME 198/192 pool four
# times in five minutes for -$104: *"The stop isn't too tight, the level that we
# just attempted a sweep on is finished."*
#
# ⚠️ MEASURED: entries at 11:43, 11:46, 11:47, 11:48 — all sell=198 buy=192,
# all stopped within a minute, all on the same pool. Nothing in the strategy
# remembered the previous attempt, so the level re-qualified every time price
# wandered back to the right side of it.
#
# ⚠️ THE ONLY INVALIDATION THAT EXISTED WAS PRICE-BASED. `LiquiditySweep
# .invalidated` (LIQ.3) is recomputed EVERY TICK from closes beyond the pool —
# it answers "has price accepted through this level", which is a fact about the
# TAPE. It cannot answer "did we already try this and lose", which is a fact
# about US. Both are needed and only one existed.
#
# ⚠️ THIS IS THE STRATEGY'S OWN DOCTRINE, FINALLY ENFORCED. Its docstring
# already says *"selling a boundary that has already given way is the worst
# version of this"* — a stop-out IS the boundary giving way, measured with real
# money rather than inferred from closes.
#
# KEYED BY (symbol, side, rounded pool) so the two sides of one price are
# separate levels, and cleared daily — a level that failed this morning is not
# thereby dead tomorrow.
# 🔴 OTV4TEST r24 — THE DICT IS GONE; THE LOCK IS READ FROM trades.db. `_SPENT`
# lived in the process, and its only writer (trade_logger's close hook) read
# `is_credit_vertical`, a column that does not exist, so it raised on EVERY
# close — 16 times in bot.log — and the level was never marked. 2026-09-11:
# the 11:40 spread exited "breach accepted … the level is SPENT", and at 12:04
# the sweep sold the same 717.05 level again. Operator's rule (DEC.1): a fact
# the trade log already holds is read from the trade log.


_TINE_SPENT_KEYS = {"fork1h/upper": -1.0, "fork1h/median": -2.0, "fork1h/lower": -3.0}


def tine_spent_key(provenance: str) -> float:
    """A tine's price moves; SPENT is keyed on the TINE (r5). Returns the pool
    key to pass to is_spent, or 0.0 for a non-tine."""
    return _TINE_SPENT_KEYS.get(str(provenance or ""), 0.0)


def _spent_key(symbol: str, side: str, pool: float) -> tuple:
    # ⚠️ ROUNDED TO THE CENT. The pool is recomputed per tick and drifts in the
    # last decimal; an exact-float key would never match itself and the lock
    # would silently never fire — the same class of dead gate as a name that
    # does not resolve.
    return (symbol or "", side or "", round(float(pool or 0.0), 2))


# Every label a breach/acceptance close is written under. exit_engine's own, and
# strategy/management.py's Intent names — which act first whenever the row carries
# an underlying_stop (always, for a TCS).
SPENT_EXIT_PREFIXES = ("sweep_breach_accepted", "tcs_breach", "breach:", "acceptance:")


def is_breach_exit(exit_reason) -> bool:
    """True when a credit spread closed because its level GAVE WAY (r5: acceptance only)."""
    return str(exit_reason or "").startswith(SPENT_EXIT_PREFIXES)


def is_spent(symbol: str, side: str, pool: float):
    """(spent, why) — READ FROM trades.db, day-scoped. NEVER raises.

    A level is SPENT for the session when a sweep or trend credit spread sold
    against it today and CLOSED ON ITS BREACH (`sweep_breach_accepted` /
    `tcs_breach` — the exit that itself says "the level is SPENT"). ACCEPTANCE
    ONLY, per the r5 ruling: a stop-out is not the level giving way.
    Keyed exactly as before: (symbol, side, pool rounded to the cent), with a
    tine keyed on its NAME (r5) because its price moves.
    ⚠️ FAILS CLOSED: an unreadable book reads as SPENT, never as "free to sell".
    """
    from datetime import datetime, timedelta
    try:
        from zoneinfo import ZoneInfo
        _et, _utc = ZoneInfo("America/New_York"), ZoneInfo("UTC")
        today = datetime.now(_et).date()
        lo = (datetime.combine(today, datetime.min.time(), _et)
              - timedelta(hours=1)).astimezone(_utc).isoformat()
        from database.trade_logger import get_trade_logger
        conn = get_trade_logger()._connect()
        try:
            rows = conn.execute(
                "SELECT entry_time, symbol, option_side, pool_price, underlying_stop, "
                "swept_level_name, exit_reason, pnl_usd FROM trades "
                "WHERE strategy IN ('SweepCreditSpread','TrendCreditSpread') "
                "AND exit_time IS NOT NULL AND entry_time >= ?", (lo,)).fetchall()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("sweep_cs: spent state unreadable from trades.db (%s) — the "
                       "level reads SPENT (fails closed)", exc)
        return True, f"trade book unreadable ({type(exc).__name__}) — fails closed"
    want = _spent_key(symbol, side, pool)
    for et_, sym, sd, pp, us, name, why, pnl in rows:
        try:
            if datetime.fromisoformat(str(et_)).astimezone(_et).date() != today:
                continue
        except (TypeError, ValueError):
            continue
        nm = str(name or "")
        key_pool = (tine_spent_key(nm) or (_name_key(nm) if "tine" in nm else 0.0)
                    or pp or us or 0.0)
        if _spent_key(sym, sd, key_pool) != want:
            continue
        reason = str(why or "")
        # ⚠️ ACCEPTANCE ONLY — the r5 ruling ("spent on acceptance only"). A
        # stop-out on noise does not discredit the level; the level giving way does.
        if is_breach_exit(reason):
            return True, (f"breach accepted on this level today ({reason[:50]}, "
                          f"pnl ${float(pnl or 0.0):+.0f})")
    return False, ""


def _sweep_at_level(liq_map, level: float, side: str = ""):
    """The sweep on a SUPPLIED level — an input the plan gathered, r158.

    ⚠️ `liq_map.sweeps` IS THE FULL LIST; `recent_sweep` is only the latest one.
    (Checked against LiquidityMap's own fields, not assumed — the week's other
    defects were all names that did not exist.) When a plan supplies a level,
    the strategy evaluates THAT sweep rather than whichever happens to be most
    recent.

    ⚠️ RETURNS None WHEN THE FEED HAS NO SWEEP THERE, and the caller reports it
    as STARVED rather than proceeding on the wrong level. A supplied input that
    cannot be found is missing data, not a refusal — the distinction matters
    because starvation names the absent input and a refusal blames the setup.
    """
    if not level:
        return None
    want_side = (side or "").lower()
    best = None
    for sw in (getattr(liq_map, "sweeps", None) or []):
        try:
            pool = float(getattr(sw, "pool_price", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        if not pool or abs(pool - float(level)) > 0.01:
            continue
        if want_side:
            # a swept LOW is defended with puts; a swept HIGH with calls
            kind = str(getattr(sw, "kind", "") or "")
            if want_side == "put" and kind != "low_sweep":
                continue
            if want_side == "call" and kind != "high_sweep":
                continue
        # freshest match wins — `bars_ago` is the real field (r135)
        if best is None or (getattr(sw, "bars_ago", 999)
                            < getattr(best, "bars_ago", 999)):
            best = sw
    return best


class SweepCreditSpreadStrategy:
    """THE SPEC (PLAN_SPEC §31). Fire when every bar the plan reports is met,
    with the plan's structure. Selects nothing.

    OTV4TEST r5 — the bars, read off `prep` from `strategy/sweep_plan.py`:
      1. window 09:35–14:00 (opened from 13:00 to test the handoff sync)
      2. a FRESH REJECTED event on a level in play (the derived fact)
      3. that level not spent; price on the profitable side; geometry
      4. pierce depth inside the band (a deep pierce is a weak level)
      5. ATR <= ceiling (FEASIBLE) and the wing clears R_FLOOR (ECONOMICAL)
    The condor complement (`required_side`) narrows which side may fire while
    the other vertical is open; it never selects a level.
    Exits (exit_engine v4.13): breach ACCEPTED (two closes beyond the pool)
    → 15% of risk for false starts → nickel close → 15:45 flatten.
    """
    name = "SweepCreditSpread"

    def __init__(self):
        from strategy.sweep_plan import SweepPlan          # lazy: it imports this module
        self.plan = SweepPlan()
        self.planner = self.plan.planner
        self.PLAN_CHECKS = self.plan.PLAN_CHECKS

    def prepare(self, *, price_now, now_et, atr_pct=None, chain=None,
                orb_high=None, orb_low=None, required_side: str = "", df_1m=None,
                **_ignored):
        return self.plan.prepare(price_now=price_now, now_et=now_et, atr_pct=atr_pct,
                                 chain=chain, orb_high=orb_high, orb_low=orb_low,
                                 df_1m=df_1m, required_side=required_side)

    def generate_signal(self, *, price_now: float, now_et: str, atr_pct: float = None,
                        chain=None, orb_high: float = None, orb_low: float = None,
                        required_side: str = "", df_1m=None,
                        complement_min_richness: float = 0.0, **_ignored) -> Optional[Signal]:
        prep = self.plan.prepare(price_now=price_now, now_et=now_et, atr_pct=atr_pct,
                                 chain=chain, orb_high=orb_high, orb_low=orb_low,
                                 df_1m=df_1m, required_side=required_side,
                                 complement_min_richness=complement_min_richness)
        if not prep.ready or prep.unmet or prep.structural or prep.starved:
            return prep.tick.already()
        if required_side and prep.side != required_side:
            return prep.tick.refuse("authorized_side",
                                    f"only a {required_side} sweep is authorized "
                                    f"while the other vertical is open; this is a {prep.side}")
        sig = Signal(
            strategy_name=self.name,
            setup_type="sweep_credit_spread",
            direction="short" if prep.side == "call" else "long",
            option_side=prep.side,
            underlying_entry=float(price_now),
        )
        sig.short_anchor = prep.short.strike
        sig.pierced_strike = prep.short.strike
        sig.pool_price = prep.pool
        sig.boundary = prep.boundary
        sig.swept_level_name = prep.name
        # 🔴 r105 — `sig.sweep_age_bars` IS REMOVED, NOT REPAIRED. It was a
        # hardcoded 0 that nothing decided on: its ONLY consumer was
        # `signal_journal`'s factor column, and that file's own comment calls a
        # constant here "a misleading 0" rather than the honest absence it
        # wanted. The operator's ruling, 2026-09-22: age is necessary to ORDER
        # the levels by recency — `level_map.walk` sorts on `formed_ts` and a
        # board without it is arbitrary — and *"not relevant to anything else"*.
        # ⚠️ THE OTHER `sweep_age_bars` IS UNTOUCHED AND IS A DIFFERENT
        # QUANTITY: `liquidity_mapper`'s, default 999, which gates
        # `recent_sweep` at line 1036 and feeds `market_state`. One name, two
        # meanings — the collision stays, and is why this removal was traced
        # attribute-by-attribute rather than by grepping the name.
        # 🔑 THE MEASUREMENT IS NOT LOST: the rejection's real age is computed
        # every tick and banked on the PLAN row as `rejection_age_bars`.
        sig.rejection_pct = prep.rej_pct
        sig.rejection_depth = prep.depth
        sig.richness_at_entry = prep.richness
        sig.atr_pct_at_entry = atr_pct
        sig.max_loss_pct = MAX_LOSS_PCT
        if str(prep.name or "").startswith("fork1h/"):
            sig.condor_trigger_source = "1h_fork"
            sig.touch_of_tine = True
        else:
            sig.condor_trigger_source = "sweep_reversal"
        sig.is_credit_vertical = True
        sig.net_credit = prep.credit
        if prep.side == "call":
            sig.short_call_contract, sig.long_call_contract = prep.short, prep.long
        else:
            sig.short_put_contract, sig.long_put_contract = prep.short, prep.long
        sig.strike = prep.short.strike
        sig.expiry = getattr(prep.short, "expiry", "")
        sig.entry_premium = prep.credit
        sig.contract = prep.short
        sig.stop_premium = prep.stop_prem
        relaxed.tag(sig)
        logger.info("[sweep_cs] FIRE  %s %.2f REJECTED (%s %.3f%%) -> %s  %s",
                    prep.name, prep.pool, prep.depth, (prep.rej_pct or 0) * 100.0,
                    prep.boundary, prep.trade_line())
        return prep.tick.take(sig)


def _name_key(name: str) -> float:
    """A stable numeric key for a MOVING level's spent lock: the level's price
    drifts every bar, so `is_spent` (keyed by rounded price) are
    given a hash of the NAME instead. Deterministic across restarts."""
    import zlib
    return float(zlib.crc32((name or "").encode("utf-8")) % 1_000_000)


def _symbol_of() -> str:
    try:
        from config import INSTRUMENT
        return str(INSTRUMENT)
    except Exception:                                          # noqa: BLE001
        return ""
