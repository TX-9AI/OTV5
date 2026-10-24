"""
analysis/orb_engine.py  v4.17
v4.17  2026-10-03  OTV4TEST r222 (ORP.1) — correct_range(): THE OFFICIAL PRINT CAN REPLACE A RANGE FROZEN FROM AN INCOMPLETE OPEN.
      On 2026-09-29 the feed was blind at the open and the range was frozen from a partial candle (low
      739.62; the backfilled bars say 737.67), and nothing ever re-read it. The operator, 2026-10-03: "On a
      blind start, agree. Yes, make it the official print & refer everything to it." correct_range replaces
      the range ONLY while the sequence has not started (WAITING_FOR_BREAK and neither break latch set);
      once a break is on the books the geometry is frozen (PLAN_SPEC 27) and it refuses, saying why.
v4.16  2026-10-02  OTV4TEST r185 (LADR.1) — THE ORB CARRIES THE RAW 100% TARGET AS ITS
      `target_strike`; THE CHAIN SNAP PICKS THE CONTRACT. It was
      orb_strike_selection(..., STRIKE_INCREMENT): pre-rounded on one table
      number per symbol, so on a $2.50 ladder held as 5 mainline bought a
      5-multiple on 109 of 111 trades - a moneyness bias, never a phantom
      strike (the snap always found a real one). Now
      round(orb_breakout_target(...), 2) and select_orb_strike / the plan's
      select_contract take the nearest LISTED strike. The ORBData field is
      a float and the state-file reload reads float(): it was int(), so a
      SOFI 16.5 target came back as 16 after a restart. Shared with otv4
      (their :832/:1458/:1482). Pinned by tests/check_strike_ladder.py.
v4.15  2026-09-24  OTV4TEST r131b — THE LINE IS OUTSIDE; THE BREAK BAR ONLY ARMS;
      THE STOP MUST SIT IN THE RANGE. Operator rulings, same day:
      (a) *"the candle that started inside the range and closed at the very
      top of the range, but did not go past. It is the break"* — the break is
      a close AT OR BEYOND the boundary (`>=`/`<=`). ONE CONVENTION FOR THE
      FILE: at-or-beyond = OUTSIDE, strictly between = INSIDE, applied to the
      break, the origin test (own open / previous close), `_closed_inside`
      (runaway re-arm), `last_close_inside`, AWAITING_RANGE_REENTRY and the
      session latches (`broke_high`/`broke_low` now latch on a close ON the
      line — the sweep gate reads them). This SUPERSEDES v4.14's "a close at
      the boundary is inside". The ARMED close-inside test (`close < orb_high`
      / `close > orb_low`) already treated the line as outside; unchanged.
      Bars before 09:34 ET are not judged (a restart replay walks 09:30-09:33,
      which the live loop never reads; r95 parity).
      (2) *"No, never. If this happens, we wait for a valid retest."* — the
      break bar is NEVER its own retest, in every case (identity guard made
      unconditional; HEAD's open-exactly-on-the-line allowance removed — 09-22
      09:35 fired that way live).
      (c) *"if the very next candle opens on the range and moves away that's
      not a retest"* — the retest body must be STRICTLY outside (`>`/`<`);
      the wick still touches or enters (`<=`/`>=`).
      (b) *"The stop should be inside the opening range to be a valid set up,
      and the sizing is based on the depth of that candles, extreme."* — the
      stop stays the break candle's range-side extreme (long: its low); a
      candle whose extreme is OUTSIDE the range (only possible via the
      previous-close origin) is NOT an impulsive candle: nothing arms,
      `break_refusal` names it, and the engine keeps waiting. On the line
      counts as inside. `stop_level`/`stop_distance_px` formulas unchanged, so
      the plan's provisional size and main.py's |fill - stop| sizing read the
      same stop as before. Pinned by tests/check_orb_reentry.py V1-V4, S1-S3.
v4.14  2026-09-24  OTV4TEST r131 — A RUNAWAY ENDS THIS BREAK, NOT THE SESSION;
      "OPENS INSIDE" IS THE PREVIOUS CLOSE. Three operator rulings, 2026-09-24:
      (1) *"A close back into the range is a new opportunity full stop."* A
      runaway invalidation was TERMINAL for the session (v1.x "Do NOT re-arm
      after an (a) runaway"), contrary to PLAN_SPEC §29.1 ("ORB is finished on
      THIS break") and §29.6 ("No limit on qualifying setups per session").
      `_advance_state` now re-arms a runaway exactly like a close-inside
      invalidation — `_rearm(reentered=True)`, the impulsive candle is dead —
      on the first closed 1m bar that CLOSES inside the range, under the same
      cutoff (past it the engine is EXPIRED before this branch runs). Price
      still out there keeps the runaway dormant.
      (2) *"It obviously opened inside because the previous candle closed
      inside."* `_check_for_break`'s origin gate now also accepts a bar whose
      PREVIOUS 1m close (iloc[-3]) was inside the range (09-24 09:58 opened
      736.06, 4c above 736.02, after 09:57 closed 735.97). The bar's own open
      test is KEPT beside it (an OR), so nothing that armed before stops arming.
      (3) *"keep it pegged to what the tape actually does"* — NO TOLERANCE.
      `_closed_inside` is inclusive at both boundaries (the `last_close_inside`
      / AWAITING_RANGE_REENTRY convention) and the break stays strict `>`/`<`,
      so a close AT a boundary is inside and never beyond.
      ⚠️ ONE CONSEQUENCE GUARDED: `_advance_state` reads the break and the
      retest on the same closed bar, so a bar admitted ONLY by (2) — own open
      outside, wick back in, body outside — would have confirmed itself on the
      tick it broke (09-24 09:58 did, in the first cut's replay). That bar, by
      identity (ts + frozen high/low/close), is not read as its own retest.
      The own-open-AT-the-boundary self-confirm HEAD already allowed (09-22
      09:35, a live trade) is deliberately left as it was — unruled.
      The retest rule, the stop, sizing, targets and exits are otherwise
      untouched. Pinned by tests/check_orb_reentry.py (born red on b1b6594).
v4.13  2026-09-08  OTV4TEST r3 — THE RUNAWAY INVALIDATION IS A CLOSE, NOT A WICK.
      Operator: *"a wick isn't confirmation."* (a) in `_check_for_retest` read
      `high >= target_50pct` / `low <= target_50pct` — a WICK to the 50 ended
      the ORB thesis while the runaway (close + hold) never armed, so a wick
      that touched and pulled back left the band owned by nobody. r221 fixed
      this for the post-trade path only. Now (a) reads `fifty_accepted` — the
      SAME two-part test the runaway arms on, tracked by
      `_track_fifty_acceptance` on the closed bar — so ORB stands until the 50
      is ACCEPTED and the runaway arms on the same event. `_track_fifty_
      acceptance` now runs BEFORE `_check_for_retest` so the acceptance is
      seen on the bar that produced it, not one tick later. Pinned by
      check_runaway_plan R1/R2.
v4.12  2026-09-08  OTV4TEST r2 — THE 12-BAR "STALE RETEST" RE-ARM IS DELETED.
      Operator, 2026-09-08: *"'Stale' doesn't make any sense to me. If it
      doesn't retest, then it's outside the range and if it's outside the
      range, how would there be another break?"* While price sits outside the
      range only three things can happen next — a retest, a runaway to the
      50%, or a close back inside — and the engine already handles all three.
      A retest on bar 13 is a retest. The v3.9 timeout dropped a live armed
      setup into AWAITING_RANGE_REENTRY after `ORB_MAX_RETEST_BARS` (12) and
      then IGNORED the very retest the setup was waiting for until price
      closed back inside. `bars_since_break` is still counted and recorded
      (the plan row shows it); it no longer acts. `ORB_MAX_RETEST_BARS` is
      removed from config in the same revision. Pinned by check_orb_plan P12:
      the real engine, armed 20 bars, confirms the 21st-bar retest.
v4.11  2026-09-04  r235 — 🔴 THE LATCH IS PER-CONFIRMATION NOW.
      `order_placed` was a bare boolean that could only say "an order happened
      at some point", so `notify_position_closed` had to CLEAR it (r227) for a
      surviving setup to fire again — and a global clear is indistinguishable
      from never having been set, which is exactly what was happening.
      `confirmation_seq` bumps at every qualifying retest; `order_placed_seq`
      records which one produced an order. Staleness is answered by COMPARISON,
      so the armed path clears NEITHER and the gate re-opens only on a genuinely
      new retest. Measured: META 2026-09-04 entered 09:39, 09:40 and 09:43 off
      a SINGLE 09:38 retest.
      ⚠️ RESTORE FAILS SHUT. A pre-r235 snapshot has `order_placed` and no seqs,
      so a naive restore would let a SPENT confirmation fire on the first tick
      after a restart; a legacy True with no seq is read as "confirmation 1,
      already spent". Both seqs persist.
      ⚠️ AND THE CLOSE-INSIDE PATH IS UNTOUCHED — still `_rearm(reentered=True)`,
      still square one waiting for a fresh break.
v4.10 2026-09-03  r228 — 🔴 r221 ARMED UNCONDITIONALLY: IT NEVER CHECKED WHERE
      PRICE WAS. Operator: "just making sure that a close in that area between
      the boundary & the 50 changes the state to armed, and nothing other
      than that." It did not — the path had three branches (50% accepted,
      past cutoff, else ARMED) and consulted price in none of them, because
      `notify_position_closed` has no price in scope and I shipped it anyway
      after noting exactly that.
      🔑 `last_close_inside` IS NOW RECORDED PER TICK from the last CLOSED
      bar, like every other latch here — wicks are tests, closes are
      acceptance. A close back INSIDE the range is a RE-ENTRY: the thesis
      ends, `_rearm(reentered=True)` runs and the impulsive candle dies.
      ⚠️ WITHOUT IT, ARMED WOULD HAVE OVERWRITTEN a `close_inside`
      invalidation the tick machinery had already applied — resurrecting a
      thesis the tape had just killed.
      🔴 AND `fifty_accepted` WAS ONLY CONSULTED AT TRADE CLOSE, so an engine
      already ARMED when acceptance landed STAYED armed and would still fire
      on a retest of a boundary the move had left behind. It now stands down
      at the moment of acceptance — but ONLY from ARMED. OPEN_LONG/SHORT are
      untouched: a live position belongs to the exit engine.
      Verified on BOTH sides: in-zone -> ARMED with the candle kept; inside ->
      WAITING_FOR_BREAK with the candle gone; accepted -> INVALIDATED.
v4.9  2026-09-03  r227 — 🔴 r221 WOULD HAVE MADE THE ORB GO QUIET, NOT WRONG.
      Operator caught it: "you didn't brick my ORB trade with bad follow-up
      retest logic, did you?" `order_placed` is r207's
      one-confirmation-one-order latch and its own comment reads "`_rearm()`
      builds a fresh ORBData, so the next attempt starts clean WITHOUT ANYONE
      CLEARING IT" — true until r221 deliberately STOPPED calling `_rearm()`
      on the armed path in order to keep the impulsive candle. The flag then
      survived the trade, and `orb_strategy` refuses on it with "this
      confirmation is SPENT", so the engine would return to ARMED_LONG and
      DECLINE EVERY RETEST for the rest of the session.
      ⚠️ QUIET, NOT LOUD — an armed engine that never fires is
      indistinguishable from a market with no setups, which is why it would
      have taken days to notice.
      🔑 THE GENERAL RULE, RECORDED: NOT rebuilding ORBData means every field
      scoped to ONE CONFIRMATION must be cleared BY NAME — `order_placed`,
      `confirmed_at`, `retest_depth_px`. `_rearm()` cleared them by
      construction; this path cannot. The impulsive candle, stop_distance_px,
      the targets and the 50% latches are KEPT deliberately, which is the
      entire point of the armed path. Z1d/Z1e/Z1f pin both halves.
v4.8  2026-09-03  r222 — SHORT SIDE CONFIRMED MIRRORED, and one shortcut
      tightened. `break_direction` is exactly "long"/"short" (set at
      1275/1301) and the rest of this file compares it with `== "long"`;
      r221's `long_side` used `.upper().startswith("L")`, which works today
      and would silently flip the WHOLE test to the SHORT branch the day
      anyone writes "up"/"down" or "LONG_BREAK". Now matches the file's own
      convention.
      🔑 THE GEOMETRY WAS ALREADY SYMMETRIC — target_50pct = orb_low -
      width/2, stop = break_candle_high, distance = |break_candle_high -
      orb_low| — but symmetry in the ENGINE does not prove symmetry in r221's
      ADDITIONS: `long_side` decides the direction of the `beyond`
      comparison, and a flipped comparison would accept a short's 50% the
      instant price ROSE, handing every short to the runaway at once.
      Verified by flipping it: S2, S4, S4b, S4c and S5 all go red.
v4.7  2026-09-03  r221 — 🔴 THE BAND BETWEEN THE BOUNDARY AND THE 50% HAD
      NO OWNER. `notify_position_closed` always called `_rearm()`, which WIPES
      ORBData — so the impulsive candle went with it and the engine sat in
      AWAITING_RANGE_REENTRY, where a second retest of the boundary FROM
      OUTSIDE could arm nothing. The runaway meanwhile will not take the move
      until a 1m close beyond `target_50pct` HOLDS. Measured on NVDA
      2026-09-03: broke 227.43, retested, entered, exited in profit, and
      227.43 -> 228.77 was owned by NO strategy.
      🔑 A RETEST AND A RE-ENTRY ARE DIFFERENT EVENTS — the operator's
      correction, and the distinction everything here rests on:
        · RETEST   = wick into the range, close back OUTSIDE. A TEST. Fires a
                     trade and leaves the impulsive candle INTACT.
        · RE-ENTRY = a CLOSE back INSIDE. ACCEPTANCE. Terminates the thesis;
                     a fresh break must set a new impulsive candle.
      So a resolved trade with price still outside keeps ARMED_LONG/SHORT and
      the ORIGINAL break candle, firing again on each qualifying retest — "as
      many times as the setup remains valid within the ORB trade window".
      ⚠️ THE 50% HANDOFF USES THE RUNAWAY'S OWN TWO-PART TEST: a 1m CLOSE
      beyond that still holds one tick later. Standing down on a mere TOUCH
      would end the ORB thesis while the runaway never armed, re-opening the
      same gap one level higher. Operator's doctrine: "wicks are tests &
      closes are acceptance."
      ⚠️ AND `_rearm()` IS NOT CALLED ON THE ARMED PATH. Calling it is what
      destroyed the setup; the close-inside invalidation still re-arms
      normally through the existing machinery.
v4.6  2026-09-01  r207 — THE SEQUENCE IS THE GATE, AND THE GEOMETRY IS FROZEN
      AT THE BREAK. Three additions, all of them operator spec.

      (1) `order_placed` — ONE CONFIRMATION, ONE ORDER, IN EITHER MODE. r195
      moved the re-arm from signal-fired to trade-resolved and made
      `_orb_offer_working()` the thing that stops a second order. That is a
      property of the ORDER PLUMBING, and the plumbing does not exist in
      paper, so the guard could never fire there. On 2026-09-01 QQQ took TWO
      ORB shorts off ONE confirmation (2 lots @ 1.56 stopped on the 25%
      floor, then 24 lots @ 1.15 on the same tick) because the dispatch held
      a stale ORBData reference across the manage→entry seam. The latch is a
      property of the CONFIRMATION, so it is mode-independent. It rides
      state_snapshot/load_state_file, because r103 makes the file
      authoritative and a bake mid-setup would otherwise re-fire the same
      trigger — WORKING_AGREEMENT 37, "a completed entry trigger is NOT
      re-enterable", broken by restart.
      🔑 `_rearm()` REPLACES ORBData wholesale, so a genuine next attempt
      gets a clean latch BY CONSTRUCTION rather than by anyone remembering
      to clear it. That is why the latch lives here and not on the engine.

      (2) `stop_distance_px` — RECORDED, NEVER READ IN A DECISION. How deep
      inside the range the invalidation sits: the impulsive wick measured from
      the boundary it broke. This is r119's question — "the closer to the
      range boundary the impulsive candle sits, the lower the risk and higher
      the R-value" — and r119's own ruling on it was *"observe first.
      Obviously."*
      🔴 AN INTERMEDIATE CUT OF r207 SIZED ON IT. Operator, same day: *"The
      true risk is based on where we entered though, not the range boundary.
      That's arbitrary. The 2 factuals are the distance from entry to the
      stop."* He is right. The stop is a PRICE LEVEL, so what is at stake is
      the gap between the FILL and that level; the boundary is where the
      candle started and stands in for the entry only while the two coincide.
      Freezing it bought determinism and paid for it in truth. Worse, it was
      solving a problem (1) had already removed: the 2→24 was an ILLEGITIMATE
      FIRE, not a mis-sized one. `main.py` sizes on |entry - stop| exactly as
      r181 and r192 left it. `tests/check_orb_sequence.py` S8 now FAILS if
      anything ever sizes off this field, the same shape as r119's own G4.

      (3) THE RETEST ACCEPTS A TOUCH. `low < orb_high` / `high > orb_low`
      became `<=` / `>=`. Operator: "a touch is acceptable as a re-enter, we
      are just making sure the level is respected before committing." The
      BODY test is unchanged and still requires open AND close outside —
      kept deliberately, it is stricter than the spec's "close outside" and
      the operator ruled to keep it. `opens_inside` on the break is likewise
      unchanged.
v4.5  2026-08-30  r195 — AWAITING_RANGE_REENTRY: the sequence after a trade.
      The engine returned to WAITING_FOR_BREAK the moment a position closed
      — or, worse, the moment the SIGNAL fired — while price sat outside the
      range with the break behind it. "Range set; no break yet" was false,
      and `_rearm()` WIPES ORBData, so firing it early erased a live plan's
      direction, stop, target and confirmation while the plan was still live.
      🔑 A break can only register from a candle that OPENS INSIDE, so the
      honest intermediate state is "price is out there"; it flips to
      WAITING_FOR_BREAK on the first closed bar back in range. Only a
      `close_inside` invalidation re-arms straight to WAITING_FOR_BREAK,
      because that one PROVES re-entry.
v4.4  2026-08-24  r103 STATE IS WRITTEN DOWN AND TRUSTED. state_snapshot() /
      load_state_file() make orb_state.json resumable and AUTHORITATIVE — the
      file has been written every tick since v3 and read by nobody, while r95
      built a tape replay to reconstruct what it already held. The one-shot
      rebuild latch becomes a gap test: a thin fetch no longer spends the
      session's only attempt (the path that made a crash loop unrecoverable),
      and a resumed engine owes a gap-fill replay. The missed payload carries
      the setup's full geometry so a MISS records like a DECLINE.
v4.3  2026-08-24  r95 TAPE REACH-BACK ON RESTART. The engine reloaded its
      RANGE from orb_range.json after a restart but never its STATE. A restart
      therefore returned to WAITING_FOR_BREAK carrying none of the session's
      history: no break latches, no attempt count, and no memory of a runaway.
      rebuild_from_tape() replays the session's closed 1m bars through the SAME
      _advance_state() the live loop uses, so the reconstruction cannot diverge
      from the live path. It is RE-QUALIFICATION AGAINST THE TAPE, not
      restoration of a stale file — the distinction r70 asked for. One-shot per
      session, date-guarded, self-disarming.

      ⚠️ WHAT IT DOES **NOT** DO — operator's ruling, 2026-08-24: a completed
      entry trigger is NOT re-enterable. A reconstructed OPEN_LONG/OPEN_SHORT is
      RECORDED and then CONSUMED (_rearm), never fired. ARMED and a runaway
      INVALIDATION are kept, because in those the trigger is still ahead of us
      or the point is to REFUSE a trade. See rebuild_from_tape().

      ⚠️ AND THE ORIGINAL DIAGNOSIS WAS OVERSTATED — corrected here so the next
      reader is not misled. It is NOT true that the pre-r95 engine could never
      re-arm "on any tape". _check_for_break requires a candle that OPENS INSIDE
      the range and CLOSES OUTSIDE it, so a restart is blind only for as long as
      price stays OUTSIDE the range; if price re-enters and breaks again, a
      restarted engine detects it normally. The real costs are narrower and both
      survive scrutiny: (1) a runaway invalidation is forgotten, so a restarted
      engine will arm on a break the design deliberately refuses — a WRONG trade,
      not a missed one; and (2) broke_high/broke_low, which are session-level
      facts the sweep gate reads, come back False.
v4.2  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).


v4.1  2026-08-21  r60: re-arm check reads ORB_NO_ENTRY_AFTER_ET, not the
      deleted global cutoff.
      deleted - doubly dead (label never assigned, and the constant that
      negated them is gone).
Opening range: establish, latch, arm, expire.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

analysis/orb_engine.py — Opening Range Breakout state machine.
STALE-RETEST TIMEOUT RESTORED, CORRECTED (supersedes v3.8's
        removal; per user spec same day). The window's only job: after a break,
        call the retest STALE once ORB_MAX_RETEST_BARS real 1-minute bars pass
        with no confirm (not far enough to be a runaway). Fixes vs pre-v3.8:
        (1) TICK-COUNTING BUG — the old counter incremented every 15-second
        engine tick, not per bar (journal: one candle logged 4x), so 12 "bars"
        expired in ~3 minutes; now dedupes on the candle timestamp
        (last_retest_bar_ts) and counts true bars. (2) NON-TERMINAL — expiry
        now calls _rearm() (WAITING_FOR_BREAK) instead of a dormant
        INVALIDATED; a fresh close beyond either level starts a new attempt
        with a fresh window. Timing: the break candle is excluded from the
        count, so with ORB_MAX_RETEST_BARS=12 the stale signal fires on the
        13th post-break bar — a 13-minute window. Runaway stays terminal;
        close_inside re-arm
        unchanged. Day-zero SMH replay under these rules: pre-10:00 attempt
        goes stale ~10:12 OR dies close_inside, either way 10:06's fresh break
        re-arms and 10:07's confirm FIRES the short.
RETEST TIMEOUT REMOVED (structural defect, user spec): the
        ORB_MAX_RETEST_BARS=12 timeout invalidation retired an armed side on a
        CLOCK, not a market event — and because 'timeout' was terminal (never
        re-armed), a stale expired attempt left the engine blind to a FRESH
        valid break. Day-zero cost: SMH 10:06 break + 10:07 textbook confirm
        (H 566.99 wick-in, body-high 566.59 out, close 566.50 out vs ORB low
        566.71) went untaken; journal retest_check proved the armed window
        ended 10:03:15 and never re-armed. Fix: timeout deleted from the state
        machine. ARMED now persists until one of three REAL outcomes: retest
        confirm (trade), 1m close back inside (re-arm via close_inside), or
        runaway to the 50% TP (terminal, hands to sweep). bars_since_break
        kept as journal telemetry only. ORB_MAX_RETEST_BARS no longer imported.
DEFECT G MEASUREMENT (log-only, zero gating change): the
        near-miss retest is now MEASURED, never gated, exactly as the defect
        prescribes. (1) ORBData.retest_depth_px records the confirming retest
        candle's penetration into the range (long: orb_high - low; short:
        high - orb_low) so the fired setup carries its own retest depth.
        (2) every 1-min candle examined while ARMED emits a `retest_check`
        event to analysis/signal_journal with the raw px depth (NEGATIVE =
        near-miss: the wick approached but never entered) + orb_width +
        outcome, building the depth distribution the Phase-3 ROI buckets
        need before anyone decides whether a "B-grade almost-retest" is
        worth grading. Depth is logged in PX and divided by tape ATR offline
        (ATR-relative per defect G — never a percentage; percentages scale
        into holes on high-priced instruments). Confirm/invalidate logic is
        byte-identical; the journal import is guarded and every emission is
        swallowed on failure.
defect H rename only: NO_ENTRY_AFTER_ET -> ORB_NO_ENTRY_AFTER_ET
        (import + the past_orb_cutoff test). Same constant, same (11, 0) value,
        same behaviour. NOTE the two cutoffs in this file are DIFFERENT rules and
        always were: past_orb_cutoff uses the 11:00 ORB-scoped constant, while
        is_past_entry_cutoff() (from utils.time_utils, used in notify_position_closed
        to decide EXPIRED vs re-arm) uses the 14:00 GLOBAL cutoff. The rename makes
        that distinction legible at the call site.
THE BREAK IS NOW DEFINITIONAL. Two changes, one principle:
        the setup is mechanical, so every tolerance is removed and the rule is
        stated exactly.
        (1) ORIGIN GATE now keys on the OPEN, not the wick. The impulsive candle
            must OPEN INSIDE the opening range (orb_low <= open <= orb_high) and
            CLOSE OUTSIDE it. v3.1 approximated "originates inside" as
            `low_ < orb_high` — the wick merely reaching back into the range —
            which still admitted a candle that OPENED ABOVE the range, dipped a
            wick in, and closed higher. That candle never broke out of the range;
            it was already outside it. It is late continuation, and it is not an
            OPENING-RANGE break by definition.
        (2) ORB_BREAK_BUFFER REMOVED (both the break test and the session latch).
            The buffer required the close to clear the range by 0.05% OF PRICE
            before a break registered. It filtered nothing the retest does not
            already filter — a marginal break that means nothing simply FAILS its
            retest — and, being a percentage, it scaled into a hole: $0.49 on MU,
            ~$3.00 on SPX. Price could close three full points beyond the opening
            range and the engine would not call it a break. A break is a close
            beyond the level. Full stop.
        The latch (_update_break_latches, which arms the SWEEP gate) drops the
        buffer as well, preserving its documented invariant that it uses the SAME
        threshold as _check_for_break(). The latch remains CLOSE-ONLY by design and
        does NOT take the origin gate — it records a session fact, not a setup.
        Net effect on the ORB: FEWER breaks (origin gate is strictly tighter) and
        EARLIER breaks (no buffer to clear). On the sweep gate: marginally MORE
        breaks latch, since the buffer no longer suppresses a small close-out.
        Together with v3.3 the whole setup is now free of tolerances:
            BREAK  = opens inside the range, closes outside it.
            RETEST = wick into the range, body outside it.
            STOP   = a close beyond the impulsive candle's wick.
STATE VOCABULARY CORRECTED. The state names described the
        mechanism, not the trade, and one of them collided with an unrelated
        meaning completely different things ("the ORB has no break yet" vs "the
        tape is oscillating") — a latent trap for any reader, human or model,
        holding both in view. Renamed to the operator's own vocabulary:
            WAITING                    -> NO_RANGE           (range not established)
            RANGING                    -> WAITING_FOR_BREAK  (range set, no break)
            BREAK_HIGH_AWAITING_RETEST -> ARMED_LONG         (break done, awaiting retest)
            BREAK_LOW_AWAITING_RETEST  -> ARMED_SHORT
            OPEN_LONG / OPEN_SHORT     -> unchanged (a position is live)
        ARMED means a break has occurred and the next event is FIRE or INVALIDATE.
        Before a break there is nothing armed — the engine is merely WAITING.
        Rename only: no state transition, threshold, or condition changed. The
        strings surface in orb_state.json, which main.py rewrites every tick, so
        a stale file self-heals within one poll interval (15s) — no migration.
RETEST GRACE BAND REMOVED (correctness fix, both sides).
        The retest confirm carried a percentage tolerance on the BODY test:
        long  `body_low  >= orb_high * 0.999`
        short `body_high <= orb_low  * 1.001`
        Intent was to admit a "near-miss" retest (wick approaches the range but
        does not enter) as a lower-grade setup. The code did the OPPOSITE. The
        first clause of the same condition (`low < orb_high`) ALREADY requires
        the wick to enter the range, so a true near-miss was never admitted and
        never fired. What the 0.999 actually admitted was a candle whose BODY
        CLOSED BACK INSIDE THE RANGE — by up to 0.1% — as a CONFIRMED retest.
        That is the DISARM condition, bought as an entry. And because the confirm
        branch is evaluated before the (b) close-inside branch, it won.
        Scale of the hole (percentage of price, so it grows with the instrument):
          MU  @ 971.50 range high → admitted closes down to 970.53 (~$0.97 inside)
          SPX @ 6000.00           → admitted closes ~6.0 POINTS inside the range
        The retest is the FALSIFICATION step of the break hypothesis ("this level
        is now support"). A level that was not actually tested produced no
        evidence, and a level whose retest closed back inside was tested and
        FAILED. Neither is a graded setup; both are no-trade. The test is now
        exact: wick INTO the range, body OUTSIDE it. No tolerance.
        Behavioural effect: strictly FEWER entries. Every entry removed was one
        taken on a candle that had already invalidated the setup. Verified against
        the MU 2026-07-10 reference (09:49 break / 09:50 retest / 09:55 stop):
        sequence reproduces unchanged — the reference retest's body sits fully
        outside the range and never depended on the grace.
        NOTE (future, NOT in this change): if the near-miss is to be evaluated as
        a genuine B-grade variant, it must be MEASURED, not gated — log an
        ATR-relative `retest_depth = (orb_high - candle_low) / ATR` on every setup
        (negative = near-miss) and let the Phase-3 ROI buckets decide. It belongs
        in orb_quality inside setup_scorer, never as a tolerance in the state
        machine. See ROADMAP Phase 3.
        SWEEP_REVERSAL, so a sweep label suppressed a valid ORB. Guarded by
        under a sweep label and the dispatch fires ORB (ORB wins). When off,
        behaviour is unchanged (defers to sweep). Pairs with main.py v3.2, which
        admits UNKNOWN/SWEEP_REVERSAL to the ORB dispatch. No change to the v3.1
        stop logic.
STOP PLACEMENT FIX + impulsive-candle origin gate.
        (1) The protective stop now anchors to the impulsive (break) candle's
            actual WICK — its LOW for a long, its HIGH for a short — not the
            body (min/max of open,close) it used before. When the impulsive
            candle opened outside the range, the body edge sat OUTSIDE the
            level, so the retest entry (which returns to the level) printed a
            stop on the wrong side of entry — inverted/degenerate risk. The
            wick is the true origin of the breakout move and sits inside the
            range where invalidation actually lives.
        (2) A valid impulsive candle must ORIGINATE INSIDE the range: its low
            must reach into the range for a long (low < orb_high), its high for
            a short (high > orb_low). A candle sitting entirely beyond the range
            is late continuation, not an ORB break; taking its "retest" was the
            source of the remaining inverted stops (fast/gap breaks and re-arms
            while price was extended). Gating on origin removes them.
        Verified on candle-logger tape (2026-07-09/10, 44 symbol-sessions):
        inverted-risk entries fell to 0 and the MU 2026-07-10 09:49/09:50
        reference setup reproduces exactly (stop 971.14 = impulsive low).
        Stop-LEVEL fix only; the exit TRIGGER is unchanged (see note below).
FIX (grave): break latches broke_high/broke_low are now
        maintained UNCONDITIONALLY every tick by _update_break_latches(),
        decoupled from the RANGING-only _check_for_break() path. Previously the
        latches were set solely inside _check_for_break(), which runs ONLY in
        RANGING state — so once the engine left RANGING without re-arming
        (runaway, retest-timeout, or a confirmed OPEN), it never re-checked for
        a break and the OPPOSITE-side latch could never be set. A genuine
        opposite-side 1-min CLOSE breakout after a one-sided runaway was
        therefore invisible to the sweep-reversal gate (_sweep_broke_orb),
        BLOCKING the highest-conviction failed-breakout reversals pre-11:00 —
        and the surviving same-side latch could be leaned on while stale. The
        latch is now a pure session fact ("did a 1-min candle CLOSE beyond this
        boundary this session"), independent of ORB entry state. Preserved:
        it stays CLOSE-based (a wick that pokes and closes back inside still
        does NOT arm a sweep — the AVGO-trap protection) and latch-only (set
        True; cleared solely by reset_for_session()). Fix is contained to this
        file; downstream (sweep gate + orb_state.json) reads the properties
        unchanged.
(a) session break latches broke_high/broke_low set on a
        1-min CLOSE beyond the range — these arm the sweep reversal (same break
        the ORB retest uses), so a wick poke that closes back inside no longer
        (sweeps take priority) so the engine can't get stuck in a phantom OPEN.
        (c) re-arm rule tightened to: 1-min close back inside AND before 11:00
        (runaway/timeout never re-arm).
v1.0 — original release
full state model rewrite
fix cutoff check running before range-setting
ORB range now read from orb_range.json (written by
        analysis/get_orb_range.py). Single source of truth — no external feed
        calls inside the engine, no log parsing, no circular logic.
fix _range_date comparison: now stored as string from
        JSON date field so today check works correctly and engine stops
        reloading orb_range.json every tick after range is set.
        ORB-friendly (RANGING/COMPRESSION). Do NOT re-arm after an (a) runaway
        breakout. Tracks invalidation_reason to distinguish the two.
11:00 ET HARD cutoff (expire even awaiting-retest, so the
        rules: (a) price runs to the 50% TP with no retest (runaway breakout,
        favors sweep reversal); (b) a 1m candle closes back inside the ORB
        range. Replaces the 2PM/exempt-retest behavior.
honor the orb_range.json "status" field. Only an
        ESTABLISHED range dated today is loaded and armed (WAITING->RANGING).
        EXPIRED (last RTH) and IN_PROGRESS (opening candle still forming)
        ranges are ignored for trading, so the engine can never break out on
        a carried-over prior-day range.
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import pandas as pd

from utils.time_utils import now_et
from zoneinfo import ZoneInfo as _ZoneInfo
_ET = _ZoneInfo("America/New_York")
_RANGE_END_ET = __import__("datetime").time(9, 34)   # r131b: first bar the live loop reads
from datetime import time as _dtime
from config import ORB_NO_ENTRY_AFTER_ET as _ORB_CUT
from utils.math_utils import orb_breakout_target   # LADR.1: raw target, chain snaps
from config import (
    STRIKE_INCREMENT, INSTRUMENT,
    ORB_NO_ENTRY_AFTER_ET
)

# v3.7 — defect-G measurement. Guarded: engine runs identically without it.
try:
    from analysis.signal_journal import journal as _sig_journal
except Exception:
    _sig_journal = None

logger = logging.getLogger(__name__)

ORB_RANGE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "orb_range.json")


class ORBState:
    NO_RANGE                   = "NO_RANGE"          # opening range not established yet
    WAITING_FOR_BREAK          = "WAITING_FOR_BREAK" # range set; no break yet
    ARMED_LONG                 = "ARMED_LONG"        # broke HIGH; awaiting retest
    ARMED_SHORT                = "ARMED_SHORT"       # broke LOW; awaiting retest
    INVALIDATED                = "INVALIDATED"
    OPEN_LONG                  = "OPEN_LONG"
    OPEN_SHORT                 = "OPEN_SHORT"
    # 🔴 r195 — THE SEQUENCE HAD A HOLE AND THE LABEL LIED. After a trade the
    # engine went straight back to WAITING_FOR_BREAK — "range set; no break
    # yet" — while price sat OUTSIDE the range with the break already behind
    # it. Operator: "why would it be waiting for the break when it's in an
    # active plan & sitting OUTSIDE the range? There is a SEQUENCE and
    # 'waiting for the break' isn't what comes after 'enter long/short'."
    # A break can only register from a candle that OPENS INSIDE, so the honest
    # state between a finished trade and the next attempt is "price is out
    # there; nothing can arm until it comes back".
    AWAITING_RANGE_REENTRY     = "AWAITING_RANGE_REENTRY"
    EXPIRED                    = "EXPIRED"


@dataclass
class ORBData:
    state:              str   = ORBState.NO_RANGE
    orb_high:           float = 0.0
    orb_low:            float = 0.0
    orb_width:          float = 0.0
    break_candle_high:  float = 0.0
    break_candle_low:   float = 0.0
    break_candle_close: float = 0.0
    break_direction:    str   = ""
    bars_since_break:   int   = 0
    last_retest_bar_ts: str   = ""   # v3.9: dedupe 15s ticks -> count real 1m bars
    target_100pct:      float = 0.0
    target_50pct:       float = 0.0
    stop_level:         float = 0.0
    target_strike:      float = 0.0   # LADR.1: the raw 100% target, not a rounded strike
    confirmed_at:       str   = ""
    # 🔴 r235 - THE CONFIRMATION'S IDENTITY, NOT A TIMESTAMP. `confirmed_at`
    # is `str(now_et())` and is CLEARED on the armed path, so it cannot answer
    # "did THIS retest already fire" - a cleared field and a fresh one look
    # alike, and two retests inside one second would collide. A monotone
    # counter bumped at each confirmation answers it unambiguously and
    # survives persistence.
    confirmation_seq:   int   = 0
    # The `confirmation_seq` that produced an order. Spent means THIS
    # confirmation, never "any confirmation ever" - which is what let a
    # resolved trade re-fire, and what made r227's global clear necessary.
    order_placed_seq:   int   = 0
    attempt_number:     int   = 0
    entries_expired:    bool  = False
    invalidation_reason: str  = ""   # 'runaway' | 'close_inside' (v3.8: 'timeout' removed)
    # r207 — THE SIZING GEOMETRY, FROZEN AT THE BREAK. |impulsive wick - the
    # boundary it broke|: break_candle_low vs orb_high for a long,
    # break_candle_high vs orb_low for a short. Set once in _check_for_break
    # and never recomputed, so a fill priced closer to the stop cannot inflate
    # the position. 0.0 means UNKNOWN, and the sizer's degenerate branch takes
    # it to a 1-lot loudly rather than guessing.
    stop_distance_px:   float = 0.0
    # r131b — the last candidate break REFUSED because its range-side extreme
    # printed outside the range ("<bar ts>: <reason>"). Record only; a fresh
    # ORBData (`_rearm`) starts without it.
    break_refusal:      str   = ""
    # 🔴 r221 — THE 50% HANDOFF, ON ACCEPTANCE NOT ON A TOUCH. Operator's
    # doctrine, 2026-09-03: "wicks are tests & closes are acceptance." The
    # runaway arms on a 1m CLOSE beyond target_50pct that still holds one tick
    # later; if the ORB stood down on a mere TOUCH of 50%, a wick through it
    # would kill the ORB thesis while the runaway never armed — leaving the
    # zone owned by nobody, which is the gap this revision closes.
    # `fifty_pending` is a close awaiting its hold; `fifty_accepted` is the
    # confirmed handoff. Same two-part test the runaway uses, so the boundary
    # between them is exact.
    fifty_pending:      bool  = False
    fifty_accepted:     bool  = False
    # 🔴 r228 — WHERE PRICE CLOSED, RECORDED PER TICK. `notify_position_closed`
    # has no price in scope (its two callers — position_manager:719 and
    # resting_orders:571 — pass none), and the operator's rule is explicit:
    # stay ARMED **only if price is in that zone when the trade closes**. A
    # CLOSE back inside the range is a RE-ENTRY and terminates the thesis.
    # ⚠️ FROM THE LAST CLOSED BAR, like every other latch in this file — not
    # from a tick price, because "wicks are tests, closes are acceptance".
    last_close_inside:  bool  = False
    # r207 — ONE CONFIRMATION, ONE ORDER. Set the moment an order is
    # CONSTRUCTED for this confirmation, in paper and live alike. `_rearm()`
    # builds a fresh ORBData, so the next attempt starts clean without anyone
    # clearing it.
    order_placed:       bool  = False
    retest_depth_px:    float = 0.0  # v3.7 (defect G): confirming retest wick's
                                     # penetration into the range, in PX
                                     # (long: orb_high - low; short: high - orb_low).
                                     # Measured only — gates nothing.


class ORBEngine:

    def __init__(self):
        self._data = ORBData()
        self._range_date = None
        # Session-level latches: did a 1-min candle CLOSE beyond the range this
        # session? These arm the sweep reversal (a sweep needs the SAME
        # registered break as the ORB retest). They survive _rearm() and are
        # only cleared by reset_for_session().
        self._broke_high = False
        self._broke_low  = False
        # r95 — the date this engine last reconstructed its state from the
        # tape. One rebuild per session; a continuously-live process sets it on
        # its first pass and never replays again.
        self._rebuilt_date = None
        # r103 — the newest closed bar this engine has actually consumed, and
        # whether a rebuild is still owed. Together they replace the one-shot
        # date latch: knowledge is owed until it reaches the present.
        self._last_bar_ts = None
        self._rebuild_owed = False
        self._resumed_from_file = False
        # r95 — the confirmation the reach-back found ALREADY FIRED while this
        # process was down, consumed rather than taken. Read ONCE by main.py to
        # write the plan-ledger row, then cleared: a missed setup that only
        # exists in bot.log is not a countable population, and the operator
        # reads PLANS, not the log.
        self._last_missed = None

    @property
    def data(self) -> ORBData:
        return self._data

    @property
    def broke_high(self) -> bool:
        """True once a 1-min candle CLOSED above the ORB high this session."""
        return self._broke_high

    @property
    def broke_low(self) -> bool:
        """True once a 1-min candle CLOSED below the ORB low this session."""
        return self._broke_low

    def reset_for_session(self):
        self._data = ORBData()
        self._range_date = None
        self._broke_high = False
        self._broke_low  = False
        self._rebuilt_date = None
        self._last_bar_ts = None
        self._rebuild_owed = False
        self._resumed_from_file = False
        logger.info("ORB engine reset for new session")

    def _rearm(self, *, reentered: bool = False):
        """Re-arm for the next attempt.

        ⚠️ `reentered` says whether price is KNOWN to be back inside the range.
        A `close_inside` invalidation proves it — that bar closed in there. A
        finished trade or a stale retest proves nothing, and claiming
        WAITING_FOR_BREAK then is a statement about the tape nobody checked.
        """
        d = self._data
        orb_high, orb_low, orb_width_val = d.orb_high, d.orb_low, d.orb_width
        attempt = d.attempt_number
        self._data = ORBData()
        self._data.orb_high       = orb_high
        self._data.orb_low        = orb_low
        self._data.orb_width      = orb_width_val
        self._data.state          = (ORBState.WAITING_FOR_BREAK if reentered
                                     else ORBState.AWAITING_RANGE_REENTRY)
        self._data.attempt_number = attempt
        logger.info(
            f"ORB re-armed for next attempt (#{attempt + 1}) in state "
            f"{self._data.state}: range {orb_low:.2f}-{orb_high:.2f}"
        )

    def correct_range(self, high: float, low: float, source: str = "") -> tuple:
        """r222 (ORP.1) — replace the range with the OFFICIAL PRINT. -> (corrected, why).

        Only before the sequence starts: state WAITING_FOR_BREAK and no break latched.
        After that the geometry is frozen by rule (one confirmation, one order; the
        range a break was judged against is the range the trade stands on), so this
        refuses and the caller records the difference instead."""
        d = self._data
        try:
            high, low = float(high), float(low)
        except (TypeError, ValueError):
            return False, "unreadable print"
        if not (high > low > 0):
            return False, "degenerate print"
        if d.state != ORBState.WAITING_FOR_BREAK or self._broke_high or self._broke_low:
            return False, (f"the sequence has started (state {d.state}, broke_high={self._broke_high}, "
                           f"broke_low={self._broke_low}) - the geometry is frozen")
        old = (d.orb_high, d.orb_low)
        d.orb_high, d.orb_low, d.orb_width = high, low, round(high - low, 4)
        logger.warning("ORB range CORRECTED to the official print (%s): %.2f-%.2f -> %.2f-%.2f",
                       source or "feed", old[1], old[0], low, high)
        return True, "corrected"

    def _load_range_from_file(self):
        """Load the ORB range from orb_range.json — single source of truth.

        Only an ESTABLISHED range dated today is armed for trading. EXPIRED
        (last RTH) and IN_PROGRESS (opening candle forming) states are ignored
        so the engine never breaks out on a carried-over prior-day range.
        """
        d = self._data
        try:
            with open(ORB_RANGE_FILE) as f:
                data = json.load(f)
            status = str(data.get("status", "")).upper()
            date   = data.get("date")
            today  = now_et().strftime("%Y-%m-%d")

            if status != "ESTABLISHED" or date != today:
                logger.debug(
                    f"ORB range not established for today "
                    f"(status={status or 'NONE'} date={date}) — engine waits"
                )
                return

            high  = float(data["high"])
            low   = float(data["low"])
            width = float(data["width"])
            if high > 0 and low > 0:
                d.orb_high  = high
                d.orb_low   = low
                d.orb_width = width
                self._range_date = today
                if d.state == ORBState.NO_RANGE:
                    d.state = ORBState.WAITING_FOR_BREAK
                logger.info(
                    f"ORB range ESTABLISHED: high={high:.2f} low={low:.2f} "
                    f"width={width:.2f} date={date}"
                )
        except Exception as e:
            logger.debug(f"ORB range file not ready: {e}")

    def update(self, df_5m: pd.DataFrame, df_1m: pd.DataFrame,
               current_price: float, ms: Optional[str] = None) -> ORBData:
        d = self._data

        # Load range from file if not yet set for today
        today = now_et().strftime("%Y-%m-%d")
        if self._range_date != today or d.orb_high == 0.0:
            self._load_range_from_file()

        now = now_et()
        past_orb_cutoff = (now.hour, now.minute) >= ORB_NO_ENTRY_AFTER_ET
        d.entries_expired = past_orb_cutoff

        # Maintain the session break latches on EVERY tick, in EVERY state, the
        # moment the range is established — a break is a session-level fact, not
        # a property of the ORB entry state machine. This must run BEFORE the
        # cutoff/OPEN/INVALIDATED early-returns below so that a genuine 1-min
        # CLOSE beyond a boundary is recorded even when the ORB itself is
        # dormant (e.g. after a one-sided runaway), which is exactly when the
        # opposite-side sweep reversal needs the latch. (v1.9)
        self._update_break_latches(df_1m)

        # 11:00 ET HARD cutoff — the ORB window is over. Expire from ANY state,
        # including OPEN_LONG/OPEN_SHORT, so the engine stops watching and can
        # never hold a phantom OPEN past the window. (A real live position is
        # managed by the position manager and exits on its own rules; expiring
        # the ENGINE state here does not touch the position.)
        if past_orb_cutoff:
            if d.state != ORBState.EXPIRED:
                d.state = ORBState.EXPIRED
                logger.info(
                    f"ORB: past 11:00 ET cutoff — EXPIRED "
                    f"(range: {d.orb_low:.2f}-{d.orb_high:.2f})"
                )
            return d

        self._advance_state(df_1m, ms)
        return d

    # ── r95 — ONE DEFINITION OF THE STATE MACHINE ─────────────────────────────
    def _advance_state(self, df_1m: pd.DataFrame, ms: Optional[str] = None):
        """Advance the state machine by the newest CLOSED bar in `df_1m`.

        ⚠️ EXTRACTED VERBATIM FROM update() AT r95 AND CALLED FROM BOTH PATHS.
        The live loop and `rebuild_from_tape()` must not be able to disagree
        about what a break or a retest IS — a second lineage of this logic is
        exactly the failure WORKING_AGREEMENT 7 exists to prevent, and it would
        be invisible because both versions would look correct in isolation.

        The LATCH is deliberately NOT called here: update() maintains it above
        the 11:00 early-return because a break is a session-level fact that
        outlives the ORB entry window (v1.9). `rebuild_from_tape()` calls it
        per bar in the same order update() does.
        """
        d = self._data

        # Before the cutoff, a confirmed OPEN is left untouched (a live ORB
        # trade is being managed elsewhere; the engine doesn't re-fire).
        if d.state in (ORBState.OPEN_LONG, ORBState.OPEN_SHORT):
            return

        if d.state == ORBState.AWAITING_RANGE_REENTRY:
            # 🔑 THE ONLY WAY BACK IN. `_check_for_break` already requires a
            # candle that OPENS INSIDE, so nothing could arm from out here
            # anyway — this state stops the engine CLAIMING otherwise, and
            # flips the moment a closed bar is back inside the range.
            if df_1m is not None and len(df_1m) >= 2:
                _c = float(df_1m.iloc[-2]["close"])
                if d.orb_low < _c < d.orb_high:     # r131b: strictly between
                    d.state = ORBState.WAITING_FOR_BREAK
                    logger.info("ORB: price back inside %.2f-%.2f — watching "
                                "for the next break", d.orb_low, d.orb_high)
        if d.state == ORBState.WAITING_FOR_BREAK:
            self._check_for_break(df_1m)

        if d.state in (ORBState.ARMED_LONG, ORBState.ARMED_SHORT):
            self._track_fifty_acceptance(df_1m)      # v4.13: BEFORE the retest read
            self._check_for_retest(df_1m, ms)

        if d.state == ORBState.INVALIDATED:
            # Re-arm after a (b) close-inside invalidation. Past the cutoff the
            # engine already EXPIRED above, so this branch is inherently
            # before-cutoff — i.e. the rule is exactly "1-min close back inside
            # the range AND before the cutoff". v3.8: 'timeout' no longer
            # exists — the retest clock was removed per spec; armed persists
            # until a market event resolves it.
            if d.invalidation_reason == "close_inside":
                # The bar CLOSED inside the range — re-entry is proven, not
                # assumed, so this is the one re-arm that may claim
                # WAITING_FOR_BREAK.
                self._rearm(reentered=True)
            elif (d.invalidation_reason == "runaway"
                  and self._closed_inside(df_1m)):
                # 🔴 r131 — A RUNAWAY ENDS THIS BREAK, NOT THE SESSION.
                # Operator, 2026-09-24: "A close back into the range is a new
                # opportunity full stop." (PLAN_SPEC §29.1 "ORB is finished on
                # THIS break"; §29.6 "No limit on qualifying setups per
                # session".) The runaway stays dormant while price is out
                # there; the first 1m CLOSE back inside the range (inclusive,
                # no tolerance) is the same re-entry the close-inside path
                # proves, so it re-arms the same way and under the same
                # cutoff: the impulsive candle is dead, a fresh one must print.
                logger.info("ORB: 1m close back inside %.2f-%.2f after the "
                            "runaway — a new opportunity; watching for a "
                            "fresh impulsive candle", d.orb_low, d.orb_high)
                self._rearm(reentered=True)
            else:
                logger.debug(
                    f"ORB dormant after '{d.invalidation_reason}' invalidation "
                    f"(ms={ms}) — price has not closed back inside the range"
                )

    def _closed_inside(self, df_1m: pd.DataFrame, back: int = 2) -> bool:
        """r131 — did the closed 1m bar `iloc[-back]` CLOSE inside the range?

        STRICTLY BETWEEN the boundaries, NO TOLERANCE. Operator, 2026-09-24:
        "keep it pegged to what the tape actually does", and (r131b) a close
        exactly ON the line is a BREAK, so it is never "back inside". The one
        convention for this file: at-or-beyond = OUTSIDE, strictly between =
        INSIDE — shared with `last_close_inside`, AWAITING_RANGE_REENTRY, the
        session latches and the `>=`/`<=` break test.
        """
        d = self._data
        if (df_1m is None or len(df_1m) < back
                or d.orb_high <= 0 or d.orb_low <= 0):
            return False
        c = float(df_1m.iloc[-back]["close"])
        return d.orb_low < c < d.orb_high

    # ── r103 — THE STATE FILE IS AUTHORITATIVE ───────────────────────────────
    def state_snapshot(self, price: float = 0.0) -> dict:
        """Everything needed to resume this engine, for orb_state.json.

        🔴 THE FILE ALREADY EXISTED AND WAS WRITE-ONLY. main.py has written
        orb_state.json every tick since v3 — state, attempt, latches, reason —
        and NOTHING has ever read it back. r95 then built a tape REPLAY to
        reconstruct what the file was already recording. Operator, 2026-08-24:
        "if it HAD the orb state, but was interrupted, it should have written it
        down. It can easily confirm orb state after any restart, so a 1x look
        back function is grossly underpowered."
        """
        d = self._data
        n = now_et()
        return {
            "high": d.orb_high if d.orb_high > 0 else None,
            "low": d.orb_low if d.orb_low > 0 else None,
            "width": d.orb_width,
            "state": str(d.state),
            "attempt": d.attempt_number,
            "reason": d.invalidation_reason,
            "broke_high": self._broke_high,
            "broke_low": self._broke_low,
            "price": price,
            "past_cutoff": (n.hour, n.minute) >= _ORB_CUT,
            "updated_at": n.strftime("%Y-%m-%d %H:%M:%S ET"),
            # ── r103 additions: the parts that make it RESUMABLE ─────────────
            "date": n.strftime("%Y-%m-%d"),
            "break_direction": d.break_direction,
            "break_candle_high": d.break_candle_high,
            "break_candle_low": d.break_candle_low,
            "break_candle_close": d.break_candle_close,
            "bars_since_break": d.bars_since_break,
            "last_retest_bar_ts": d.last_retest_bar_ts,
            "confirmed_at": d.confirmed_at,
            "stop_level": d.stop_level,
            "target_50pct": d.target_50pct,
            "target_100pct": d.target_100pct,
            "target_strike": d.target_strike,
            "retest_depth_px": d.retest_depth_px,
            # r207 — both RESUMABLE. The latch especially: without it a bake
            # mid-setup re-fires a trigger that already produced an order.
            "stop_distance_px": d.stop_distance_px,
            "order_placed": d.order_placed,
            "confirmation_seq": d.confirmation_seq,
            "order_placed_seq": d.order_placed_seq,
            "last_bar_ts": self._last_bar_ts or "",
        }

    def load_state_file(self, path: str) -> bool:
        """Resume from orb_state.json. AUTHORITATIVE — operator's ruling,
        2026-08-24: "If it wrote it, trust it and act accordingly."

        ⚠️ TODAY'S FILE ONLY. A dated file from a prior session is ignored
        outright rather than half-trusted; yesterday's break latches on today's
        range is the failure `_load_range_from_file` already guards against.
        ⚠️ AND IT DOES NOT SUPPRESS THE REACH-BACK. The file says what the
        engine knew at its last write; the tape covers the gap from there to
        now. Trusting the file is what makes that gap SMALL — the replay stops
        being the mechanism and becomes the patch.
        """
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:                                 # noqa: BLE001
            logger.debug("ORB state file not readable: %s", e)
            return False
        today = now_et().strftime("%Y-%m-%d")
        if str(data.get("date")) != today:
            logger.info("ORB state file is not today's (%s) — ignored",
                        data.get("date"))
            return False
        d = self._data
        try:
            _st = str(data.get("state") or "")
            if not _st:
                return False
            d.state = _st.replace("ORBState.", "")
            for _k, _attr in (("high", "orb_high"), ("low", "orb_low"),
                              ("width", "orb_width"),
                              ("break_candle_high", "break_candle_high"),
                              ("break_candle_low", "break_candle_low"),
                              ("break_candle_close", "break_candle_close"),
                              ("stop_level", "stop_level"),
                              ("target_50pct", "target_50pct"),
                              ("target_100pct", "target_100pct"),
                              ("retest_depth_px", "retest_depth_px"),
                              ("stop_distance_px", "stop_distance_px")):
                _v = data.get(_k)
                if _v is not None:
                    setattr(d, _attr, float(_v))
            d.attempt_number     = int(data.get("attempt") or 0)
            d.bars_since_break   = int(data.get("bars_since_break") or 0)
            d.target_strike      = float(data.get("target_strike") or 0.0)
            d.break_direction    = str(data.get("break_direction") or "")
            d.last_retest_bar_ts = str(data.get("last_retest_bar_ts") or "")
            d.confirmed_at       = str(data.get("confirmed_at") or "")
            d.invalidation_reason = str(data.get("reason") or "")
            d.order_placed       = bool(data.get("order_placed"))
            # \U0001f534 r235 - RESTORE THE SEQS, AND FAIL SHUT ON A PRE-r235 SNAPSHOT.
            # A file written before this revision has `order_placed` and no
            # seqs, so a naive restore would give confirmation_seq=0 and
            # order_placed_seq=0 - and the gate would let a SPENT confirmation
            # fire again on the first tick after a restart. A legacy True with
            # no seq is treated as "confirmation 1, already spent", which is
            # the safe reading: a real fresh retest bumps the seq past it.
            d.confirmation_seq   = int(data.get("confirmation_seq") or 0)
            d.order_placed_seq   = int(data.get("order_placed_seq") or 0)
            if d.order_placed and d.confirmation_seq == 0:
                d.confirmation_seq = d.order_placed_seq = 1
                logger.info("ORB STATE: pre-r235 snapshot with order_placed set "
                            "\u2014 treating the restored confirmation as SPENT")
            self._broke_high = bool(data.get("broke_high"))
            self._broke_low  = bool(data.get("broke_low"))
            self._range_date = today if d.orb_high > 0 else None
            self._last_bar_ts = str(data.get("last_bar_ts") or "") or None
            self._resumed_from_file = True
            logger.info(
                "ORB STATE RESUMED from file: state=%s attempt=%d "
                "latches(H/L)=%s/%s range=%.2f-%.2f last_bar=%s (written %s)",
                d.state, d.attempt_number, self._broke_high, self._broke_low,
                d.orb_low, d.orb_high, self._last_bar_ts or "-",
                data.get("updated_at"))
            return True
        except Exception as e:                                 # noqa: BLE001
            logger.warning("ORB state file unusable (%s) — falling back to the "
                           "tape reach-back", e)
            return False

    def mark_rebuild_owed(self) -> None:
        """r103 — a resumed engine owes a gap-fill replay. The state file is
        authoritative for what it RECORDED; the bars written since are not in
        it, and that window is exactly what the reach-back is for."""
        self._rebuild_owed = True

    @property
    def needs_tape_rebuild(self) -> bool:
        """True while this session's tape reach-back is still owed.

        Exists so the caller can skip fetching a DEEP 1m frame on every tick —
        the reach-back needs the whole session, which `ctx["df_1m"]` (60 bars)
        cannot supply.

        🔴 r103 — WAS A ONE-SHOT DATE LATCH, AND THAT WAS THE UNDERPOWERED
        PART. `_rebuilt_date = today` was set by the FIRST replay AND by a
        replay that found fewer than three session bars, so a single thin or
        failed fetch spent the session's only attempt and nothing retried. The
        rebuild is now owed until the engine's knowledge REACHES THE PRESENT:
        it is idempotent (replaying the same tape onto the same state is a
        no-op), so there is no reason to ration it.
        ⚠️ AND A RESUMED ENGINE STILL OWES ONE. The file is authoritative for
        what it recorded; the bars since it was written are the gap, and the
        gap is exactly what the reach-back is for.
        """
        if self._rebuild_owed:
            return True
        return self._rebuilt_date != now_et().strftime("%Y-%m-%d")

    # ── r95 — THE RESTART REACH-BACK ─────────────────────────────────────────
    def rebuild_from_tape(self, df_1m: pd.DataFrame,
                          ms: Optional[str] = None) -> bool:
        """Reconstruct this session's ORB state by replaying the closed 1m tape.

        🔴 WHY THIS EXISTS. `_load_range_from_file()` restores the RANGE across a
        restart. Nothing restored the STATE, so a restarted engine came back to
        WAITING_FOR_BREAK with the whole session's history erased.

        ⚠️ THE COST IS NOT MAINLY THE MISSED SETUP — and that matters, because
        the operator has ruled the missed setup is not to be recovered anyway.
        The costs that survive that ruling are:

          1. **A FORGOTTEN RUNAWAY BECOMES A WRONG TRADE.** After a runaway
             invalidation the engine is deliberately DORMANT until a 1m close
             back inside the range (r131). A restart forgets that, sits in
             WAITING_FOR_BREAK, and would arm on a bar that merely OPENS inside
             while the continuous engine waits for a CLOSE inside. This is the reach-back earning its place: it REMOVES a
             trade, it does not add one.
          2. **THE SESSION BREAK LATCHES COME BACK FALSE.** `broke_high` /
             `broke_low` are session-level facts (v1.9) that the sweep gate
             reads, and a restart silently reset them to False.
          3. **THE RECORD LIES.** `attempt_number` restarts at 0, so the diary
             and the plan ledger disagree with the tape about what the session
             actually did.

        Measured 2026-08-24 (QQQ): the ORB plan was recorded CANCELLED /
        WIPED_BY_RESTART @ 706.00 at 09:40 by the crash-loop. Proven in
        `tests/check_orb_restart.py`, which is born red against the pre-r95
        engine.

        ⚠️ WHAT IT WILL NOT DO. See the ruling block in the body: a reconstructed
        OPEN_* is recorded and consumed, never fired. There is no path from this
        function to a late entry.

        ⚠️ THIS IS RE-QUALIFICATION AGAINST THE TAPE, NOT RESTORATION OF A FILE.
        r70 declined to restore a confirmation from `orb_state.json` and it was
        right to: "resuming a stale confirmation blind after an outage is a
        different decision and needs re-qualification against the current tape."
        Nothing is read from a state file here. Every transition is RE-DERIVED
        from bars, by `_advance_state()` — the same function the live loop calls,
        in the same order, with the same latch. A continuously-running process
        and a restarted one therefore reach an IDENTICAL state from an identical
        tape, which is the whole property that was missing.

        ⚠️ `orb_reentry_age_s` IS STILL MEASURED AND LOGGED even though nothing
        acts on it. It is the age of the CONFIRMING BAR, not of the replay, and
        it is how "how much ORB did restarts actually cost us" becomes a
        countable number rather than an argument.

        ⚠️ THE CALLER MUST SUPPLY A DEEP FRAME. `ctx["df_1m"]` is capped at 60
        bars by `TIMEFRAMES` — at 10:37 it starts at 09:37 and cannot see a 09:40
        break at all. This is the same left-edge trap that killed `_opening_range`
        for every session until TCS.3. Pass a frame fetched for the session, not
        the cached trigger frame.

        One-shot per session, date-guarded and self-disarming: a process that has
        been live all morning rebuilds on its first pass (a no-op, because its
        state already matches the tape) and never replays again.

        Returns True if a replay ran, False if it was skipped or not possible.
        """
        d = self._data
        today = now_et().strftime("%Y-%m-%d")
        if self._rebuilt_date == today:
            return False
        # ⚠️ THE REBUILD LOADS ITS OWN RANGE AND THAT ORDERING IS LOAD-BEARING.
        # It must run BEFORE update() has advanced the state machine by even one
        # bar. Replaying the session on top of a state that has already moved
        # would feed 09:31 bars to a retest check that is ARMED from 10:15 —
        # instant close_inside, instant re-arm, and a fabricated attempt count.
        # So it cannot wait for update() to populate the range for it.
        if d.orb_high <= 0 or d.orb_low <= 0:
            self._load_range_from_file()
        if d.orb_high <= 0 or d.orb_low <= 0:
            # No established range yet — nothing to replay against. NOT marked
            # done, so the rebuild still runs on the tick the range establishes.
            return False
        if df_1m is None or len(df_1m) < 3:
            return False

        try:
            # Replay only TODAY'S bars. A frame that reaches into yesterday would
            # break out of today's range on yesterday's tape.
            try:
                sess = df_1m[df_1m.index.date == df_1m.index[-1].date()]
            except Exception:                                  # noqa: BLE001
                sess = df_1m
            if len(sess) < 3:
                # 🔴 r103 — WAS `self._rebuilt_date = today`. A thin frame is a
                # FETCH that came up short, not a session that has been
                # replayed, and marking it done spent the only attempt on it.
                # This is the path that made "a crash loop never recovers"
                # true: one bad fetch and nothing retried for the rest of the
                # day. Owed stays owed.
                logger.info("ORB reach-back: only %d session bar(s) in the "
                            "fetch — NOT marking the rebuild done; it retries "
                            "next tick", len(sess))
                return False

            # ⚠️ r96 — `d` IS NOT SAFE TO HOLD ACROSS THIS LOOP. `_rearm()` does
            # `self._data = ORBData()` — it REPLACES the dataclass rather than
            # mutating it — so a local binding taken before a re-arm becomes an
            # orphan pointing at the discarded object. This replay re-arms on
            # every close-inside invalidation, and NFLX did so twice on
            # 2026-08-24: the summary reported `state=INVALIDATED attempt=1` one
            # line after logging `CONFIRMED LONG (attempt #3)`, because it was
            # reading the corpse of the first attempt.
            # 🔴 AND IT WAS NOT COSMETIC. The consume check read the stale
            # object, never saw OPEN, wrote NO MISSED ROW, and left the LIVE
            # engine CONFIRMED — which before 11:00 would have offered a
            # reconstructed setup to the dispatch as tradeable, the exact thing
            # the operator's ruling forbids. It was past the cutoff on the day
            # this was found, so nothing was taken.
            before = self._data.state
            # Walk the tape one closed bar at a time. `_check_for_break` and
            # `_check_for_retest` both read `iloc[-2]`, so slicing to i+1 makes
            # bar i-1 the "newest closed bar" — exactly what the live loop hands
            # them, one tick at a time.
            replayed = 0
            confirm_ts = None
            for i in range(2, len(sess) + 1):
                sub = sess.iloc[:i]
                self._update_break_latches(sub)      # same order as update()
                was = self._data.state
                self._advance_state(sub, ms)
                if (was not in (ORBState.OPEN_LONG, ORBState.OPEN_SHORT)
                        and self._data.state in (ORBState.OPEN_LONG,
                                                 ORBState.OPEN_SHORT)):
                    # The CONFIRMING bar is the one the state machine just read,
                    # i.e. iloc[-2] — not the newest bar in the frame. Measuring
                    # from the frame's end would report the age of the REPLAY
                    # rather than the age of the SETUP, which is the number that
                    # matters and the one that would quietly read ~0 forever.
                    confirm_ts = sub.index[-2]
                replayed += 1

            self._rebuilt_date = today
            self._rebuild_owed = False
            try:
                self._last_bar_ts = str(sess.index[-1])
            except Exception:                                  # noqa: BLE001
                pass

            # ── 🔴 THE OPERATOR'S RULING, 2026-08-24 ─────────────────────────
            # **"DO NOT TAKE A MISSED ENTRY as permission to enter LATE. If we
            # missed it due to an unexpected crash loop or restart, it's fine.
            # The edge lies in the entry & invalidation logic. Jumping in after
            # it has left the station is not a remedy for missing it."**
            #
            # So the reach-back restores state UP TO BUT NOT INCLUDING A
            # COMPLETED ENTRY TRIGGER, and the line falls exactly where the
            # edge does:
            #
            #   ARMED_LONG / ARMED_SHORT  → KEPT. The break happened while we
            #       were down, but the RETEST — the trigger — is still ahead of
            #       us and will be observed LIVE, on our own tape, by the same
            #       code that would have judged it anyway. That is not a chase.
            #   INVALIDATED (runaway)     → KEPT, and this is the case that
            #       prevents a WRONG trade rather than recovering a missed one.
            #       A runaway is dormant until a 1m close back inside the range
            #       (r131: that close re-arms, replayed here like any other). A
            #       restart that forgot the runaway would sit in
            #       WAITING_FOR_BREAK and arm while the runaway owns the move.
            #   OPEN_LONG / OPEN_SHORT    → RECORDED, THEN CONSUMED. The
            #       trigger already fired while the process was down. Price has
            #       left the station. Entering now would be an ORB in name only:
            #       the entry price is stale, while `stop_level` still anchors
            #       to the break candle's wick — so the risk leg silently widens
            #       by exactly the distance we chased.
            #
            # ⚠️ CONSUMED MEANS RE-ARMED, NOT KILLED. `_rearm()` is what the
            # engine already does after a real ORB position closes: the attempt
            # is spent, the range and attempt count are preserved, and the
            # engine goes back to watching for a FRESH break. A genuinely new
            # break+retest later in the window is still tradeable, and it is
            # tradeable on its own merits rather than on a memory.
            # ⚠️ SCOPED TO WHAT THE REPLAY PRODUCED, NOT TO WHATEVER IS OPEN.
            # Operator, 2026-08-24: the no-late-entry ruling is "for a recovered
            # orb state only. It does not apply to normal entries. Those should
            # keep trying." A LIVE confirmation that has not been filled yet —
            # chain fetch failed, thin liquidity, the dispatch slot taken — must
            # stay OPEN and keep being offered until the 11:00 cutoff.
            # `before` is the state this engine held when the reach-back
            # started; if it was already OPEN, the confirmation is THIS
            # process's own and the reach-back has no business touching it.
            # ⚠️ NOT LEFT TO THE ONE-SHOT GUARD. In production the guard makes
            # this unreachable (the rebuild runs at boot, before anything is
            # live), but a guard is exactly the kind of thing a later edit
            # moves. `tests/check_orb_restart.py` C5/C9b caught this leak on its
            # first run, which is the only reason the scoping can be trusted.
            _missed = None
            d = self._data          # r96 — RE-BIND: the loop may have re-armed
            if (before not in (ORBState.OPEN_LONG, ORBState.OPEN_SHORT)
                    and d.state in (ORBState.OPEN_LONG, ORBState.OPEN_SHORT)):
                _missed = d.state
                if now_et().time() >= _dtime(*_ORB_CUT):
                    # Past ORB's own 11:00 window. EXPIRED is the LEGITIMATE
                    # TIME GATE, not a consequence of the miss — the same state
                    # a healthy engine reaches at 11:00 having done nothing.
                    d.state = ORBState.EXPIRED
                    d.invalidation_reason = "missed_while_down"
                else:
                    # ⚠️ THE REASON IS DELIBERATELY NOT SET HERE. `_rearm()`
                    # rebuilds ORBData from scratch and would discard it
                    # anyway, and a stale "missed_while_down" hanging off a
                    # WAITING_FOR_BREAK engine would surface in orb_state.json
                    # and status.py as though the CURRENT attempt were tainted.
                    # It is not: this engine is hunting a fresh break on equal
                    # terms. The miss lives in the log and in the plan-ledger
                    # row, which are the records that should carry it.
                    self._rearm()

            d = self._data          # r96 — _rearm() replaced it again
            after = d.state

            age_s = None
            if confirm_ts is not None:
                try:
                    _now = pd.Timestamp(now_et())
                    _cts = pd.Timestamp(confirm_ts)
                    if _now.tzinfo is None and _cts.tzinfo is not None:
                        _cts = _cts.tz_localize(None)
                    elif _now.tzinfo is not None and _cts.tzinfo is None:
                        _cts = _cts.tz_localize(_now.tzinfo)
                    age_s = int((_now - _cts).total_seconds())
                except Exception:                              # noqa: BLE001
                    age_s = None

            if after != before or replayed:
                logger.info(
                    "ORB TAPE REACH-BACK: replayed %d closed 1m bars %s..%s -> "
                    "state=%s (was %s) attempt=%d broke_high=%s broke_low=%s "
                    "orb_reentry_age_s=%s",
                    replayed, sess.index[0], sess.index[-1], after, before,
                    d.attempt_number, self._broke_high, self._broke_low, age_s)
            if _missed is not None:
                # ── 🔴 r103 — A MISS IS RECORDED LIKE A DECLINE ─────────────
                # Operator, 2026-08-24: "'missed' should log the way a
                # 'declined' is — with all the known parameters captured with
                # it." A disposition carries the signal context, the score and
                # the reason; a miss carried a timestamp and a direction. Both
                # are refusals to trade and both are only worth having if they
                # can be compared to each other later. Everything the engine
                # knew at the confirming bar goes in the payload, so the
                # question "what did the ones we MISSED look like next to the
                # ones we DECLINED" is one query rather than a forensic pass
                # over bot.log.
                self._last_missed = {
                    "state": _missed,
                    "direction": "LONG" if "LONG" in _missed else "SHORT",
                    "confirmed_bar": str(confirm_ts) if confirm_ts else "",
                    "age_s": age_s,
                    "attempt": d.attempt_number,
                    "trigger_price": (d.orb_high if "LONG" in _missed
                                      else d.orb_low),
                    # the setup's own geometry, as the strategy would have seen it
                    "orb_high": d.orb_high,
                    "orb_low": d.orb_low,
                    "orb_width": d.orb_width,
                    "break_direction": d.break_direction,
                    "break_candle_high": d.break_candle_high,
                    "break_candle_low": d.break_candle_low,
                    "break_candle_close": d.break_candle_close,
                    "bars_since_break": d.bars_since_break,
                    "retest_depth_px": d.retest_depth_px,
                    "stop_level": d.stop_level,
                    "target_50pct": d.target_50pct,
                    "target_100pct": d.target_100pct,
                    "target_strike": d.target_strike,
                    "confirmed_at": d.confirmed_at,
                    "broke_high": self._broke_high,
                    "broke_low": self._broke_low,
                    "resumed_from_file": self._resumed_from_file,
                    "replayed_bars": replayed,
                }
                logger.warning(
                    "ORB MISSED WHILE DOWN: the tape shows a confirmed "
                    "break+retest (%s) at %s that this process never saw live "
                    "(orb_reentry_age_s=%s). NOT TAKEN — a fired trigger is not "
                    "re-enterable. Attempt #%d consumed; engine now %s and "
                    "watching for a fresh break in %.2f-%.2f.",
                    _missed, confirm_ts, age_s, d.attempt_number, after,
                    d.orb_low, d.orb_high)
            return True
        except Exception as exc:                                # noqa: BLE001
            # A reach-back that raises must never take the tick with it: the
            # engine simply continues from WAITING_FOR_BREAK, which is exactly
            # the pre-r95 behaviour. Not marked done, so it retries next tick.
            logger.warning("ORB tape reach-back failed (continuing live): %s", exc)
            return False

    def take_missed_confirmation(self):
        """Return-and-clear the confirmation the reach-back consumed, if any.

        ⚠️ TAKE, NOT PEEK. The caller writes ONE plan-ledger row per missed
        setup; leaving the value in place would write a duplicate row on every
        tick for the rest of the session, and a count that inflates is worse
        than no count at all.
        """
        m, self._last_missed = self._last_missed, None
        return m

    def notify_position_closed(self):
        """A trade resolved. Stay ARMED if the setup is still alive.

        🔴 r221 — THIS ALWAYS DEMANDED RANGE RE-ENTRY, AND THAT LOST THE SETUP.
        `_rearm()` wipes ORBData, so the impulsive candle went with it and the
        engine sat in AWAITING_RANGE_REENTRY: a second retest of the boundary
        from outside could not arm anything. Meanwhile the runaway will not
        take the move until a 1m close beyond target_50pct holds — so the band
        between the boundary and the 50% was owned by NO strategy. Measured on
        NVDA 2026-09-03: broke 227.43, retested, entered, exited in profit, and
        227.43 -> 228.77 had no owner.

        🔑 A RETEST AND A RE-ENTRY ARE DIFFERENT EVENTS — the operator's
        correction, and the distinction the whole change rests on:
          · RETEST   = wick into the range, close back OUTSIDE. A TEST. It can
                       fire a trade and it leaves the impulsive candle intact.
          · RE-ENTRY = a CLOSE back INSIDE the range. ACCEPTANCE. It terminates
                       the thesis; the impulsive candle is dead and a fresh
                       break must set a new one.
        So a resolved trade with price still outside the range keeps
        ARMED_LONG / ARMED_SHORT and the ORIGINAL break candle, and fires again
        on the next qualifying retest — "as many times as the setup remains
        valid within the ORB trade window."

        ⚠️ THREE OUTCOMES, IN PRECEDENCE ORDER:
          1. 50% ACCEPTED -> the runaway owns the move unequivocally, and that
             move itself invalidates the ORB. Stand down.
          2. past the ORB entry cutoff -> EXPIRED, as before.
          3. otherwise -> stay ARMED with the original impulse; `_rearm()` is
             NOT called, because calling it is what destroys the setup.
        ⚠️ AND THE CLOSE-INSIDE PATH IS UNTOUCHED. Re-entry still invalidates
        through the normal machinery and still re-arms; this only changes what
        happens when a TRADE ends while the structure is still standing.
        """
        d = self._data
        if d.state not in (ORBState.OPEN_LONG, ORBState.OPEN_SHORT):
            return
        was_long = d.state == ORBState.OPEN_LONG
        if d.fifty_accepted:
            # ⚠️ NOT `_rearm()`. The runaway owns this move; re-arming would
            # leave the ORB hunting a break it has been told to stand off.
            d.state = ORBState.INVALIDATED
            d.invalidation_reason = "runaway"
            logger.info("ORB position closed — 50%% TP ACCEPTED (1m close held) "
                        "so the runaway owns this move; ORB stands down")
            return
        if now_et().time() >= _dtime(*_ORB_CUT):
            d.state = ORBState.EXPIRED
            return
        # 🔴 r228 — THE ZONE TEST, WHICH r221 SHIPPED WITHOUT. The operator's
        # rule is that the setup survives a resolved trade ONLY IF PRICE IS
        # STILL OUTSIDE THE RANGE. A 1m CLOSE back inside is a RE-ENTRY —
        # acceptance, not a test — and it terminates the thesis: the impulsive
        # candle is dead and a fresh break must set a new one.
        # ⚠️ WITHOUT THIS, ARMED WAS UNCONDITIONAL and would have OVERWRITTEN
        # a `close_inside` invalidation the tick machinery had already applied
        # — resurrecting a thesis the tape had just killed.
        if d.last_close_inside:
            logger.info("ORB position closed with price back INSIDE "
                        "%.2f-%.2f — that close is a RE-ENTRY and ends this "
                        "thesis; awaiting a fresh break",
                        d.orb_low, d.orb_high)
            self._rearm(reentered=True)
            return
        # 🔑 STAY ARMED. The impulsive candle, stop_distance_px and the targets
        # all live on ORBData and survive precisely because nothing wipes them.
        d.state = (ORBState.ARMED_LONG if was_long else ORBState.ARMED_SHORT)
        d.attempt_number += 1
        d.bars_since_break = 0
        d.last_retest_bar_ts = ""
        # 🔴 r227 — `order_placed` MUST BE CLEARED HERE OR THE ENGINE GOES
        # QUIET. It is r207's one-confirmation-one-order latch, and its own
        # comment says "`_rearm()` builds a fresh ORBData, so the next attempt
        # starts clean WITHOUT ANYONE CLEARING IT" — which was true until r221
        # deliberately stopped calling `_rearm()` on this path in order to keep
        # the impulsive candle. The flag then survived the trade, and
        # `orb_strategy` refuses on it with "this confirmation is SPENT", so
        # the engine would sit in ARMED_LONG and decline EVERY retest for the
        # rest of the session.
        # ⚠️ NOT BROKEN LOUDLY — BROKEN QUIETLY, which is worse. An armed
        # engine that never fires looks like a market with no setups.
        # 🔑 THIS IS THE COST OF NOT REBUILDING ORBData: `_rearm()` cleared
        # these by construction, so every field a NEW ATTEMPT needs fresh now
        # has to be cleared BY NAME. The impulsive candle, stop_distance_px,
        # the targets and the 50% latches are deliberately KEPT — that is the
        # whole point — but anything scoped to ONE CONFIRMATION goes.
        # 🔴 r235 - `order_placed` IS NO LONGER CLEARED HERE. r227 cleared it
        # to stop the engine going quiet, which was the right call against a
        # GLOBAL latch. With `order_placed_seq` the staleness is answered by
        # COMPARISON instead: the state returns to ARMED, `confirmation_seq`
        # is unchanged, and the next qualifying retest bumps it - so the gate
        # re-opens on a NEW retest and stays shut without one. Clearing it
        # here would restore exactly the behaviour this revision removes.
        d.confirmed_at = ""
        d.retest_depth_px = 0.0
        logger.info(
            "ORB position closed — STILL ARMED (%s, attempt %d): impulsive "
            "candle held at %.2f, stop distance %.2f, 50%% TP %.2f not yet "
            "accepted. A qualifying retest fires again; a CLOSE inside "
            "%.2f-%.2f terminates the thesis.",
            d.state, d.attempt_number,
            d.break_candle_low if was_long else d.break_candle_high,
            d.stop_distance_px, d.target_50pct, d.orb_low, d.orb_high)

    def _update_break_latches(self, df_1m: pd.DataFrame):
        """Record, as a session-level fact, whether a 1-min candle has CLOSED
        beyond the ORB range in each direction (broke_high / broke_low).

        Deliberately independent of the ORB entry state machine: the sweep
        reversal gate must know a genuine breakout occurred even when the ORB
        is dormant (post-runaway / OPEN / EXPIRED), which _before_
        v1.9 was impossible because the latches were only set inside
        _check_for_break() (RANGING-only). Uses the SAME closed candle
        (iloc[-2]) and the SAME break threshold as _check_for_break(), so the
        latch and the ORB retest arm on identical conditions. Latch-only: sets
        True and never clears (reset_for_session() is the sole reset). Purely
        CLOSE-based, so a wick that pokes a boundary and closes back inside
        does NOT arm a sweep (AVGO-trap protection preserved).
        """
        d = self._data
        if d.orb_high <= 0 or d.orb_low <= 0:
            return                      # range not established — nothing to latch
        if df_1m is None or len(df_1m) < 2:
            return
        close  = float(df_1m.iloc[-2]["close"])
        # (v3.5) Buffer removed here too, to preserve this method's stated invariant:
        # the latch must use the SAME break threshold as _check_for_break(). The latch
        # is deliberately CLOSE-ONLY and does NOT apply the opens_inside origin gate —
        # it records a session FACT ("a 1m candle closed beyond this boundary"), which
        # is what the sweep gate needs, not an ORB entry setup.
        if close >= d.orb_high:           # r131b: a close ON the line is a break
            if not self._broke_high:
                self._broke_high = True
                logger.info(
                    f"ORB latch: 1-min CLOSE {close:.2f} above high "
                    f"{d.orb_high:.2f} — broke_high armed (session-level)"
                )
        elif close <= d.orb_low:
            if not self._broke_low:
                self._broke_low = True
                logger.info(
                    f"ORB latch: 1-min CLOSE {close:.2f} below low "
                    f"{d.orb_low:.2f} — broke_low armed (session-level)"
                )
        # r228 — the same closed bar answers "is price still out there?"
        if d.orb_low > 0 and d.orb_high > 0:
            d.last_close_inside = bool(d.orb_low < close < d.orb_high)   # r131b: strict
        self._track_fifty_acceptance(df_1m)

    def _track_fifty_acceptance(self, df_1m):
        """Has the 50% TP been ACCEPTED — a 1m close beyond, still holding?

        🔴 r221 — THE SAME TWO-PART TEST THE RUNAWAY ARMS ON, deliberately.
        `runaway_continuation._closed_beyond_and_held` requires a 1m CLOSE
        beyond `target_50pct` and price still on the right side at the next
        tick. If the ORB stood down on a mere TOUCH of the 50%, a wick through
        it would end the ORB thesis while the runaway never armed — and the
        band would be owned by nobody, which is the whole defect r221 closes.
        Reproducing the condition here rather than importing it keeps
        `analysis` from depending on `strategy`; C-note if the runaway's rule
        ever moves, this must move with it.

        ⚠️ WICKS ARE TESTS, CLOSES ARE ACCEPTANCE — operator's doctrine,
        2026-09-03. This reads the CLOSED candle (iloc[-2]) like every other
        latch in this file, so a wick through 50% arms nothing.
        ⚠️ LATCH-ONLY. Once accepted it stays accepted for the session: the
        runaway owns that move even if price falls back, and `reset_for_session`
        is the sole reset — the same discipline as broke_high/broke_low.
        """
        d = self._data
        if d.fifty_accepted or d.target_50pct <= 0 or not d.break_direction:
            return
        if df_1m is None or len(df_1m) < 2:
            return
        close = float(df_1m.iloc[-2]["close"])
        # ⚠️ `break_direction` IS EXACTLY "long"/"short" (set at 1275/1301) and
        # the rest of this file compares it with `== "long"`. Matching that
        # convention rather than a `startswith("L")` shortcut: the shortcut
        # works today and silently flips the whole test to the SHORT branch the
        # day anyone writes "up"/"down" or "LONG_BREAK".
        long_side = (d.break_direction == "long"
                     or d.state in (ORBState.ARMED_LONG, ORBState.OPEN_LONG))
        beyond = (close > d.target_50pct) if long_side else (close < d.target_50pct)
        if not beyond:
            # ⚠️ A PENDING CLOSE THAT DOES NOT HOLD IS DISCARDED, not carried.
            # The runaway requires the hold at the NEXT tick; a close that
            # reverses immediately is a wick with extra steps.
            if d.fifty_pending:
                logger.info("ORB: 50%% TP close did NOT hold (%.2f vs %.2f) — "
                            "pending cleared, ORB setup stands", close,
                            d.target_50pct)
                d.fifty_pending = False
            return
        if not d.fifty_pending:
            d.fifty_pending = True
            logger.info("ORB: 1-min CLOSE %.2f beyond the 50%% TP %.2f — "
                        "pending the hold", close, d.target_50pct)
            return
        d.fifty_accepted = True
        logger.info("ORB: 50%% TP %.2f ACCEPTED (close beyond, held) — the "
                    "runaway owns this move", d.target_50pct)
        # 🔴 r228 — AND AN ALREADY-ARMED ENGINE MUST STAND DOWN HERE. The latch
        # was only ever consulted in `notify_position_closed`, so an engine
        # that was ARMED when acceptance landed stayed armed — and would still
        # fire on a retest of a boundary the move had long since left behind.
        # Operator's rule: "if it reaches the 50, then the runaway owns it
        # unequivocally — that move in itself invalidates an ORB trade."
        # ⚠️ OPEN_LONG/OPEN_SHORT ARE LEFT ALONE. A live position is managed by
        # the exit engine; standing the ENGINE down must never touch a trade
        # that is still running, and `notify_position_closed` handles it when
        # the trade actually resolves.
        if d.state in (ORBState.ARMED_LONG, ORBState.ARMED_SHORT):
            d.state = ORBState.INVALIDATED
            d.invalidation_reason = "runaway"
            logger.info("ORB: was ARMED when the 50%% was accepted — standing "
                        "down, the runaway owns this move")

    def _check_for_break(self, df_1m: pd.DataFrame):
        d = self._data
        if df_1m is None or len(df_1m) < 2:
            return
        candle = df_1m.iloc[-2]
        close  = float(candle["close"])
        open_  = float(candle["open"])
        high_  = float(candle["high"])
        low_   = float(candle["low"])

        # THE BREAK (v3.5). Definitional, no tolerances:
        #   the impulsive candle OPENS INSIDE the opening range and CLOSES OUTSIDE it.
        # `opens_inside` is the whole premise of the setup — it is an OPENING-RANGE
        # break; a candle that began life outside the range never broke out of it,
        # it was already out. (v3.1 approximated this with `low_ < orb_high`, i.e.
        # the wick merely reaching back in, which admitted candles that opened above
        # the range, dipped, and closed higher — late continuation, not a break.)
        # The percentage break buffer is GONE (v3.5): the retest IS the noise filter
        # — a marginal break that means nothing simply fails its retest. The buffer
        # only cost real setups, and being a % of price it scaled into a hole
        # (0.05% = $0.49 on MU, ~$3.00 on SPX: price could close three points clear
        # of the range and not register).
        # 🔴 r131 — "OPENS INSIDE" IS THE PREVIOUS 1m CLOSE. Operator,
        # 2026-09-24, on 09:58 (open 736.06, 4c above the 736.02 high, after
        # 09:57 closed 735.97 inside): "It obviously opened inside because the
        # previous candle closed inside." A 1m bar's first print can sit a few
        # cents from the prior close; the candle STARTED where the last one
        # closed. No tolerance (`_closed_inside`, iloc[-3]; strict since r131b).
        # ⚠️ THE OWN-OPEN TEST IS KEPT beside it (an OR), so nothing that armed
        # before stops arming: with no previous bar in the frame the bar's own
        # open is the only evidence, and while WAITING_FOR_BREAK the previous
        # close is inside anyway on every path that reaches this state except
        # a mid-session start with price already outside.
        # r131b — "inside" is STRICTLY between (at-the-line = outside), both
        # for the bar's own open and for the previous close.
        opens_inside = (d.orb_low < open_ < d.orb_high
                        or self._closed_inside(df_1m, back=3))

        # r131b — ONLY BARS THE LIVE LOOP CAN READ. With a close ON the line
        # now a break, the range's 09:34 bar closing at the extreme it set is
        # a break — the operator's own description, 2026-09-24: "the candle
        # that started inside the range and closed at the very top of the
        # range, but did not go past. It is the break" (09-22: 09:34 closed
        # 743.45 = the high; 09:35 opened on it and moved away). The live
        # engine first reads 09:34 (iloc[-2] on the 09:35 tick), but a
        # restart's tape replay also walks 09:30-09:33, where a bar closing at
        # the eventual 5m high would "break" a range that did not yet exist.
        # Bars before 09:34 ET are therefore not judged, which keeps the
        # replay equal to the live loop (r95). Untimed frames are not judged.
        try:
            _ts = df_1m.index[-2]
            if getattr(_ts, "tzinfo", None) is not None:
                _ts = _ts.tz_convert(_ET)
            if hasattr(_ts, "time") and _ts.time() < _RANGE_END_ET:
                return
        except Exception:                                  # noqa: BLE001
            pass

        # 🔴 r131b — THE STOP MUST SIT INSIDE THE RANGE FOR A VALID SETUP.
        # Operator, 2026-09-24: "The stop should be inside the opening range to
        # be a valid set up, and the sizing is based on the depth of that
        # candles, extreme." The stop is the break candle's range-side extreme
        # (long: its low; short: its high) and it must lie within the range —
        # ON the line counts, the range includes its own high/low. Only a bar
        # admitted by the previous-close origin can print wholly beyond; it is
        # NOT an impulsive candle: nothing arms, the reason is recorded, and
        # the engine keeps waiting for a bar that starts inside again.
        _refuse = None
        if opens_inside and close >= d.orb_high and low_ > d.orb_high:
            _refuse = (f"break candle's low {low_:.2f} is outside the range "
                       f"(above {d.orb_high:.2f}) — not a valid setup")
        elif opens_inside and close <= d.orb_low and high_ < d.orb_low:
            _refuse = (f"break candle's high {high_:.2f} is outside the range "
                       f"(below {d.orb_low:.2f}) — not a valid setup")
        if _refuse:
            d.break_refusal = f"{df_1m.index[-2]}: {_refuse}"
            logger.info("ORB break REFUSED: %s", d.break_refusal)
            return

        # 🔴 r131b — A CLOSE ON THE LINE IS A BREAK. Operator, 2026-09-24: "the
        # candle that started inside the range and closed at the very top of
        # the range, but did not go past. It is the break". `>=` / `<=`.
        if opens_inside and close >= d.orb_high:
            d.break_direction    = "long"
            d.break_refusal      = ""          # r131b: a valid break supersedes it
            d.break_candle_close = close
            # Stop anchors to the IMPULSIVE candle's WICK, not its body: the low of
            # the candle that caused the breakout (v3.1). Using min(open,close)
            # (the body low) placed the stop ABOVE the level whenever the impulsive
            # candle opened outside the range, inverting risk on the retest entry.
            d.break_candle_high  = high_
            d.break_candle_low   = low_
            d.bars_since_break   = 0
            d.last_retest_bar_ts = str(df_1m.index[-2])  # break candle excluded from stale count
            d.target_100pct      = d.orb_high + d.orb_width
            d.target_50pct       = d.orb_high + d.orb_width * 0.5
            d.stop_level         = d.break_candle_low
            # r207 — the sizing distance, measured from the boundary this
            # candle broke, frozen here and never recomputed downstream.
            d.stop_distance_px   = abs(d.orb_high - d.stop_level)
            d.target_strike      = round(orb_breakout_target(d.orb_high, d.orb_low, "long"), 2)
            d.attempt_number    += 1
            d.state              = ORBState.ARMED_LONG
            # (v1.9) broke_high is now latched by _update_break_latches() every
            # tick, independent of state — not set here.
            logger.info(
                f"ORB BREAK HIGH (attempt #{d.attempt_number}): close={close:.2f} "
                f"above {d.orb_high:.2f} target={d.target_100pct:.2f} strike={d.target_strike}"
            )
        elif opens_inside and close <= d.orb_low:
            d.break_direction    = "short"
            d.break_refusal      = ""          # r131b: a valid break supersedes it
            d.break_candle_close = close
            # Stop anchors to the IMPULSIVE candle's WICK (its HIGH for a short) —
            # the high of the candle that caused the breakout (v3.1).
            d.break_candle_high  = high_
            d.break_candle_low   = low_
            d.bars_since_break   = 0
            d.last_retest_bar_ts = str(df_1m.index[-2])  # break candle excluded from stale count
            d.target_100pct      = d.orb_low - d.orb_width
            d.target_50pct       = d.orb_low - d.orb_width * 0.5
            d.stop_level         = d.break_candle_high
            # r207 — the sizing distance, measured from the boundary this
            # candle broke, frozen here and never recomputed downstream.
            d.stop_distance_px   = abs(d.stop_level - d.orb_low)
            d.target_strike      = round(orb_breakout_target(d.orb_high, d.orb_low, "short"), 2)
            d.attempt_number    += 1
            d.state              = ORBState.ARMED_SHORT
            # (v1.9) broke_low is now latched by _update_break_latches() every
            # tick, independent of state — not set here.
            logger.info(
                f"ORB BREAK LOW (attempt #{d.attempt_number}): close={close:.2f} "
                f"below {d.orb_low:.2f} target={d.target_100pct:.2f} strike={d.target_strike}"
            )

    def _check_for_retest(self, df_1m: pd.DataFrame, ms: Optional[str] = None):
        d = self._data
        if df_1m is None or len(df_1m) < 2:
            return
        # v3.9 STALE-RETEST TIMEOUT, per spec 2026-07-20: the window applies
        # ONLY while ARMED (i.e. after the break, which is the only place this
        # method runs) and its sole purpose is to declare a retest STALE after
        # ORB_MAX_RETEST_BARS 1-minute bars pass without one — too slow to be a
        # retest, not far enough to be a runaway. On expiry the engine goes
        # straight back to WAITING_FOR_BREAK (non-terminal): a fresh 1m close
        # beyond either level starts a new attempt with a fresh window.
        #   Two defects in the pre-v3.8 timeout, both fixed here:
        #   (1) it counted 15-SECOND LOOP TICKS as "bars" (journal 2026-07-20:
        #       one candle logged 4x, each tick incrementing), so "12 bars"
        #       actually expired in ~3 minutes;
        #   (2) it was TERMINAL (never re-armed), so an expired stale attempt
        #       left the engine blind to SMH's fresh 10:06 break + 10:07
        #       textbook confirm. Now: real bars, and expiry re-arms.
        candle_ts = str(df_1m.index[-2])
        if candle_ts != d.last_retest_bar_ts:
            d.last_retest_bar_ts = candle_ts
            d.bars_since_break += 1
        # v4.12 (OTV4TEST r2) — NO STALE TIMEOUT. The count above is a record;
        # the armed setup lives until a retest, a runaway or a close inside.

        candle    = df_1m.iloc[-2]
        close     = float(candle["close"])
        open_     = float(candle["open"])
        high      = float(candle["high"])
        low       = float(candle["low"])
        body_high = max(open_, close)
        body_low  = min(open_, close)

        # v3.7 (defect G) — MEASURE the retest depth on every examined candle,
        # near-misses included (negative depth = wick approached but never
        # entered the range). Log-only; gates nothing; failures swallowed.
        if _sig_journal is not None:
            try:
                depth_px = ((d.orb_high - low) if d.break_direction == "long"
                            else (high - d.orb_low))
                _sig_journal("retest_check", orb={
                    "direction":        d.break_direction,
                    "attempt":          d.attempt_number,
                    "bars_since_break": d.bars_since_break,
                    "retest_depth_px":  round(depth_px, 4),
                    "orb_width":        round(d.orb_width, 4),
                    "candle": {"open": open_, "high": high,
                               "low": low, "close": close},
                })
            except Exception:
                pass

        # 🔴 r131b — THE BREAK BAR IS NEVER ITS OWN RETEST. Operator,
        # 2026-09-24: "No, never. If this happens, we wait for a valid
        # retest." PLAN_SPEC §29.1: the retest is a LATER 1m bar. `_advance_
        # state` reads the break and then the retest on the SAME closed bar,
        # and every 15s tick re-reads it until the next bar closes, so the
        # break bar is recognised by IDENTITY (the ts the count excluded, the
        # high/low/close frozen at the break) and only arms. This removes the
        # allowance HEAD had for a break bar opening exactly on the line (09-22
        # 09:35 fired that way).
        if (d.bars_since_break == 0
                and candle_ts == d.last_retest_bar_ts
                and high == d.break_candle_high and low == d.break_candle_low
                and close == d.break_candle_close):
            return

        if d.break_direction == "long":
            # (a) Runaway breakout — ran to the 50% TP with no retest → invalidate.
            # This is the setup that most favors a sweep reversal instead.
            if d.fifty_accepted:                       # v4.13: a CLOSE, held
                d.state = ORBState.INVALIDATED
                d.invalidation_reason = "runaway"
                logger.info(
                    f"ORB INVALIDATED: 50% TP ({d.target_50pct:.2f}) ACCEPTED "
                    f"(close beyond, held) with no retest — the runaway owns it"
                )
                return
            # RETEST (v3.3): the wick must ENTER the range (low < orb_high) and the
            # BODY must stay OUTSIDE it (body_low >= orb_high). No grace band. The
            # retest is the falsification step — the level either held or it did
            # not. A body that closes back inside the range is a DISARM, not a
            # near-miss, and falls through to the (b) branch below.
            # r207 — a TOUCH of the boundary counts as the re-entry (`<=`).
            # The BODY test is unchanged: open AND close must stay outside.
            # r131b — BODY STRICTLY OUTSIDE: a bar that opens ON the line and
            # moves away is not a retest (operator: "We still have to wait").
            if low <= d.orb_high and body_low > d.orb_high:
                # phantom OPEN the dispatch will override — leave it awaiting
                # retest so the engine can't get stuck OPEN with no position.
                # sweep: confirm OPEN and let the dispatch fire it.
                # is DELETED. Doubly dead: v4 never assigns the label, and
                # anyway. A confirmed break+retest is self-validating.
                d.state           = ORBState.OPEN_LONG
                d.confirmed_at    = str(now_et())
                d.confirmation_seq += 1          # r235 - a NEW retest
                d.retest_depth_px = round(d.orb_high - low, 4)   # v3.7 defect G
                logger.info(f"ORB CONFIRMED LONG (attempt #{d.attempt_number}): wick={low:.2f} body_low={body_low:.2f}")
            # (b) Retrace into range — 1m candle closes back inside the ORB range.
            elif close < d.orb_high:
                d.state = ORBState.INVALIDATED
                d.invalidation_reason = "close_inside"
                logger.info(f"ORB INVALIDATED: 1m close={close:.2f} back inside range")
        else:
            # (a) Runaway breakout (short) — ran to the 50% TP with no retest.
            if d.fifty_accepted:                       # v4.13: a CLOSE, held
                d.state = ORBState.INVALIDATED
                d.invalidation_reason = "runaway"
                logger.info(
                    f"ORB INVALIDATED: 50% TP ({d.target_50pct:.2f}) ACCEPTED "
                    f"(close beyond, held) with no retest — the runaway owns it"
                )
                return
            # RETEST (v3.3) — mirror of the long side. Wick enters the range
            # (high > orb_low), body stays outside (body_high <= orb_low). No grace.
            # r207 — a TOUCH of the boundary counts as the re-entry (`>=`).
            # The BODY test is unchanged: open AND close must stay outside.
            # r131b — mirror: body strictly below the low.
            if high >= d.orb_low and body_high < d.orb_low:
                # v4.1 — mirror of the long side; same deletion.
                d.state           = ORBState.OPEN_SHORT
                d.confirmed_at    = str(now_et())
                d.confirmation_seq += 1          # r235 - a NEW retest
                d.retest_depth_px = round(high - d.orb_low, 4)   # v3.7 defect G
                logger.info(f"ORB CONFIRMED SHORT (attempt #{d.attempt_number}): wick={high:.2f} body_high={body_high:.2f}")
            # (b) Retrace into range — 1m candle closes back inside the ORB range.
            elif close > d.orb_low:
                d.state = ORBState.INVALIDATED
                d.invalidation_reason = "close_inside"
                logger.info(f"ORB INVALIDATED: 1m close={close:.2f} back inside range")

    def mark_triggered(self):
        self.notify_position_closed()

    def mark_order_placed(self) -> None:
        """r207 — an order has been CONSTRUCTED for this confirmation.

        🔑 CALLED FROM THE PLACEMENT SITE, NOT THE FILL SITE, and in both
        modes. A live standing offer that has not filled yet is still an order
        against this setup; waiting for a fill would leave the window in which
        r195's `_orb_offer_working()` was the only guard — the window that does
        not exist in paper at all.

        ⚠️ NEVER RAISES and never asserts a state. A latch that refuses to set
        because the engine has moved on would leave the confirmation
        re-fireable, which is the failure it exists to prevent.
        """
        self._data.order_placed = True
        # 🔴 r235 - RECORD WHICH CONFIRMATION IS SPENT. The bare boolean could
        # only say "an order happened", so `notify_position_closed` had to
        # clear it globally (r227) to let the setup fire again - and clearing
        # it is what let ONE retest fire repeatedly once the flag was never
        # set in the first place.
        self._data.order_placed_seq = self._data.confirmation_seq
        logger.info("ORB order placed for attempt #%d, confirmation #%d — THIS "
                    "confirmation is SPENT; the next order needs a fresh "
                    "qualifying retest",
                    self._data.attempt_number, self._data.confirmation_seq)

    @property
    def order_already_placed(self) -> bool:
        """True when this confirmation has already produced an order."""
        return bool(self._data.order_placed)

    @property
    def is_confirmed(self) -> bool:
        return self._data.state in (ORBState.OPEN_LONG, ORBState.OPEN_SHORT)

    @property
    def direction(self) -> str:
        if self._data.state == ORBState.OPEN_LONG:  return "long"
        if self._data.state == ORBState.OPEN_SHORT: return "short"
        return ""


_orb_engine: Optional[ORBEngine] = None

def get_orb_engine() -> ORBEngine:
    global _orb_engine
    if _orb_engine is None:
        _orb_engine = ORBEngine()
    return _orb_engine
