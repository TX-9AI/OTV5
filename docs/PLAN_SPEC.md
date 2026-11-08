# PLAN_SPEC.md — every strategy declares its intent BEFORE the trigger

**`PLAN_SPEC.md` v5.3 · 2026-11-08 · OTV5 r88 (RETIRE.3) — §34 (the trend credit spread, and its r57 log-only shadow) is REMOVED from the code; the section keeps its heading and points to the history. The operator, 2026-11-08: "Delete".**

**`PLAN_SPEC.md` v5.2 · 2026-11-08 · OTV5 r81 (DOC.36) — §32.3: the GEX pin butterfly has NO stop since OTV5 r73 (BFLY.17); its one exit is the 15:45 flatten, and its door adds VIX ≥ 20 no-fire, an open inside yesterday's range and the 15.5%-of-width debit floor. The Saturday brief 2026-11-07 section 4 item 3.**

**`PLAN_SPEC.md` v5.1 · 2026-11-08 · OTV5 r76 (RETIRE.1) — §29 (the ORB trade), §31 (the sweep credit spread), §39 (the ATP butterfly) and §41 (ORCS) are REMOVED with their code; their headings stay so older references resolve. §37: the Hunt no longer grants a handoff (its only taker was the sweep); its exits are unchanged. The opening-range ENGINE that §29 described is untouched. The operator, 2026-11-07: "Running dead code and logging dead code activity is unnecessary drag. Yes, I want all of those things fixed."**

**`PLAN_SPEC.md` v5.0 · 2026-10-25 · OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...**

**v1.41 · 2026-10-24 · OTV4TEST r316 — BRK.15 / HUNT.13 / RENT.3: a Breakout side re-arms on every return to the range (the new-extreme re-fire rule dropped); no Hunt on a side after a losing Breakout on it that day; the 20 s re-entry gate records only (§43).**

**v1.40 · 2026-10-19 · OTV4TEST r303 — PSTATE.1: every plan is ACTIVE, LOG or DORMANT (§42); a dormant plan writes nothing, ORCS's included (§41.13 amended).**

**v1.39 · 2026-10-04 · OTV4TEST r249 — PREM.6: ORCS IS RETIRED by ruling (§41.13); the plan keeps recording.**

**v1.35 · 2026-10-03 · OTV4TEST r229 — EM.2: ORCS's implied move is the tastytrade platform's expected move (§41.10); the butterflies keep theirs by ruling.**

**v1.34 · 2026-10-03 · OTV4TEST r207 — PREM.4: ORCS reshaped by ruling (§41.9): short delta 0.20, a 3-dollar wing, one implied move. Where §41.1-§41.7 say delta 0.15, 1.25 implied moves or a 1% wing, §41.9 governs.**
**v1.33 · 2026-10-03 · OTV4TEST r206 — PREM.3: ORCS entries are governed by the house entry ladder (§41.8); the plan's own offer (mark + one cent, ten-minute rest) is REMOVED by ruling. Where §41.1-§41.7 say 'offer', 'limit' or 'one cent better', §41.8 governs.**
**v1.32 · 2026-10-03 · OTV4TEST r204 — PREM.2: §41 is now ORCS, the opening range credit spread, and it TRADES ON PAPER (§41.7); the sweep (§31) and the TCS (§34) are RETIRED by ruling, off behind OT_SWEEP_CS / OT_TCS_ACTIVE.**
**v1.31 · 2026-10-03 · OTV4TEST r203 — PREM.1: §41, the opening premium spread - the spec, the trigger components, the preliminary dials, and a RECORD-ONLY plan that searches the chain for them. No order is placed.**
**v1.30 · 2026-09-30 · OTV4TEST r179 — BFLY.9: the ATP fly qualifies on route A (PINNING, concentration ≥ 0.15; the pin fly keeps 0.25) or, only when A fails, route B (NOT TRENDING and the pin within ±0.05 × EM of VWAP), and its window is 12:00–15:00 in the table as well as in the plan (§39.1).**
**v1.29 · 2026-09-30 · OTV4TEST r178 — CAP.2: both butterflies are exempt from the daily catastrophic loss cap; §39.1's "one per session" row corrected to one of EACH type (true since r85) and its slot to the configured window.**
**v1.28 · 2026-09-24 · OTV4TEST r131 — §29 amended by ruling: a close back inside is a new opportunity after a runaway; the break is a close AT or beyond the line; the break bar is never its own retest; the stop is the break candle's extreme inside the range. Breakout re-fires only at a new session extreme; VOLT sizes on Breakout's 1-R curve.**
**v1.27 · 2026-09-14 · OTV4TEST r30 — §40: a confirmed level carries its dated timeframe so it outlives the tape; stale VWAP ids retire.**
**v1.26 · 2026-09-14 · OTV4TEST r29 — the levels are built from the tape: held session extremes, walked from spot, spent only on acceptance (§40).**
**v1.25 · 2026-09-14 · OTV4TEST r26 — the ATP (at-the-pin) butterfly, a second butterfly thesis; one butterfly per session across both (§39).**
**v1.24 · 2026-09-08 · OTV4TEST r2 — the ORB spec and its plan contract, agreed part by part; observe-only outside the window (§29).**
**v1.23 · 2026-09-01 · r208 — the butterfly wing is searched, not computed (§28).**
**v1.22 · 2026-09-01 · r207 — the ORB firing sequence is the gate (§27).**
**v1.21 · 2026-08-28 · r181 — ORB risk-normalized sizing, pure geometry (§26).**
**v1.20 · 2026-08-28 · r179 — 🔴 one per session, DB-backed (§25).**
**v1.19 · 2026-08-29 · r178 — 🔴 one butterfly per pin per session (§24).**
**v1.18 · 2026-08-29 · r177 — the butterfly's starved atm_iv; the tick_id join key (§23).**
**v1.17 · 2026-08-29 · r176 — the cutoff does not relax; the drift reads the vote's clock (§22).**
**v1.16 · 2026-08-28 · r175 — TCS prices its premise: pop_drift (§21).**
**v1.15 · 2026-08-28 · r174 — the teenie lesson: floor-clears-spread; one runaway per break (§20).**
**v1.14 · 2026-08-28 · r170 — the readers (§19).**
**v1.13 · 2026-08-27 · r169 — the butterfly rides to the close (§18); the exit map, complete.**
**v1.12 · 2026-08-27 · r168 — the runaway's 20% floor; the structure stop is ORB's (§17).**
**v1.11 · 2026-08-27 · r167 — managed exits: the plan decides (§16).**
**v1.10 · 2026-08-27 · r166 — the management plan (§15).**
**v1.9 · 2026-08-27 · r165 — the runaway: gamma leverage over the run (§14). The inversion is complete.**
**v1.8 · 2026-08-27 · r164 — TCS in the §10 shape (§13).**
**v1.7 · 2026-08-27 · r163 — a tine is a moving liquidity level; a touch is its event (§12).**
**v1.6 · 2026-08-27 · r161 — the butterfly earns its entry (§11).**
**v1.5 · 2026-08-27 · r160 — the plan is anticipatory, the strategy confirmatory; the condor authorizes and manages. §10 supersedes §8 where they differ.**
**v1.3 · 2026-08-26 · r147 — leg two and the butterfly, §9.**
**v1.2 · 2026-08-26 · r146 — AS BUILT. See §8 before reading anything below.**
**v1.0 · 2026-08-25 · FIRST PASS, EXPLICITLY UNFITTED.**
Operator: *"every strategy SPEC now needs a plan — use your best judgement on the
1st pass. We will fit later. Allow for relaxed and tight entry conditions."*

Every number in this document that is not read from an existing constant is a
**STATED PRIOR**, not a measurement. They are marked `⟨PRIOR⟩`. Nothing here is
validated against a tape.

---

## 0. WHY — the failure this exists to end

**2026-08-25, TSLA.** Price ran 351.4 → 356.86 between roughly 11:35 and 13:00
ET. Verified from `strategy_note`: `TrendCreditSpread` evaluated 182 times in
that window and produced one signal; `TrendCS2nd` signalled on 207 of 218 looks
and traded nothing. Verified from `main.py`: **only `ORBStrategy` ever calls
`open_plan`.** The PLANS panel on that box therefore showed six ORB rows, all
`EXPIRED / left_confirmed_state`, the newest at 10:38 — and nothing whatsoever
about the largest directional move of the session.

Operator: *"Right now it's looking like nothing was watching it & that's where
my aggravation lies."*

The old engine's flaw, in his words: *"it was watching EVERYTHING, the flaw was
that it was circular logic, making it regressive and late."* A score computed
per tick from data that already contains the move can only ever report the move
after it happens.

---

## 1. THE GOVERNING RULE

> **Evidence decides whether a plan is WRITTEN.
> Price decides whether it FIRES.**

The instant a score, label, or conviction is consulted at fire time, the loop is
back. A plan's trigger is a **number fixed at declaration** and compared against
the tape. Nothing more.

**The anchor test — apply to every plan input:**
*Would this number be the same if I asked ten minutes from now, absent a
structural event?*

| Admissible anchors (fixed) | Inadmissible (re-derived) |
|---|---|
| ORB high / low | a rolling N-bar high |
| named levels (`levels` store) | "current support" |
| pitchfork rails at a stamped index | a rail re-projected each tick |
| session high / low | a moving average |
| GEX pin | ADX / conviction / any score |
| prior-day high / low / close | anything with `_now` in its name |

Scores may appear ONLY in `justification` — the frozen evidence vector — and in
the decision to declare. Never in the trigger.

---

## 2. THE PLAN RECORD

`derived/plan_ledger.py` already carries `trigger_price`, the four strike
fields, `underlying_at_decision`, `expected_move`, and `justification`
(the frozen vector: price, adx, atm_iv, expected_move_iv, VRP, realised vol,
charm, vanna, gex, session fraction, levels, fork rails).

**FIELDS TO ADD:**

| field | why |
|---|---|
| `invalidation_price` | the plan's own death line. Today the exit re-derives it. |
| `expires_ts` | a plan with no expiry is a standing order nobody placed. |
| `mode` | `tight` \| `relaxed` — see §5. Keeps the populations separable forever. |
| `distance_to_trigger` | updated on transition only, never per tick. Makes "how close did we get" answerable. |
| `arm_reason` | one line: what structure justified declaring. |

**STATES:** `DECLARED → ARMED → TRIGGERED → FILLED` with terminal
`EXPIRED` / `INVALIDATED` / `SUPERSEDED` / `WIPED_BY_RESTART`.

`DECLARED` = structure exists, evidence gathered, trigger set.
`ARMED` = still valid, still inside its window, trigger not yet crossed.
The split matters because a plan can be declared and then fall out of its
window without ever being wrong.

---

## 3. THE INVERSION — what each strategy asks per tick

Not *"is this a breakout?"* but ***"what price, from here, would constitute
one — and what would I sell or buy when it comes?"***

Each strategy gains one method:

```
declare_plan(ctx) -> Plan | None
```

It runs on ticks where **no plan of its type stands**. It answers the forward
question, prices the contract, stamps the evidence, and returns. Once a plan
stands, the tick loop does one thing: compare price to `trigger_price`.

---

## 4. THE PLANS, ONE PER STRATEGY

Each carries: **trigger** (fixed price), **invalidation** (fixed price),
**instrument** (pre-selected contract), **window**, **declare-when**.

### 4.1 ORB — `ORBStrategy` — 🔴 **LEAVE IT ALONE**
Operator, 2026-08-25: *"leave orb alone. That one can't get encumbered with
extra hurdles & it already pretty much plans."*
**NO CHANGES. ORB IS THE MODEL, NOT A CANDIDATE.** It already declares a range
at 09:35, fixes a trigger, names an invalidation, and fires on a price
comparison — which is exactly why it has never been late, and why every other
plan in this document is written in its shape. It opens plans today
(`main.py` 1291/1353) and those calls stand unchanged.
⚠️ The temptation to "formalise" it into the new interface is the hurdle he is
refusing. A working thing does not get rewritten to match a document.
Strike selection is a **later, separate** fine-tune and is out of scope here.

### 4.2 RUNAWAY CONTINUATION — `RunawayContinuation` (DEBIT)
- **declare when** ORB has broken and gone `runaway` (no retest)
- **trigger** ⟨PRIOR⟩ close beyond `orb_break_price + 0.25 × ATR` — the
  continuation confirming, not the break itself
- **invalidation** close back below the ORB boundary
- **instrument** the staged call/put at `CONT_TARGET_DELTA`
- **window** break → `DEBIT_DIRECTIONAL_CUTOFF_ET` (11:30)

### 4.3 TREND PARTICIPATION — `TrendCreditSpread` (CREDIT)
**This is the one that failed on 2026-08-25 and the changes are the point.**
- **declare when** 11:31, ORB range known, trend vote directional
- **trigger** close beyond the ORB boundary (`orb_high` for a PCS)
- **invalidation** close back through that boundary
- **instrument** — 🔴 **CHANGED. THE STRIKE MUST BE ABLE TO FOLLOW THE MOVE.**
  Today `_inside[-1]` pins the short strike inside the opening range for the
  whole session, so as price advances the strike goes deeper OTM, the credit
  collapses, and the trade refuses *the harder it rips.* Verified in source at
  `strategy/trend_credit_spread.py` lines 341-352 and confirmed by the two
  fires being the only two moments price sat near the boundary.
  **NEW RULE: the floor is re-anchored per plan, not per session.**
  A plan declares its short strike as the first strike at or below
  `max(orb_high, session_low_since_break)` ⟨PRIOR⟩ — so a second plan declared
  at 12:30 sits under the 12:30 structure, while the FIRST plan keeps the strike
  it was born with. Plans do not move; new plans get new strikes.
- **window** `TCS_START_ET` (11:31) → `TCS_ENTRY_END_ET` (14:00)
- **re-declaration** ⟨PRIOR⟩ a new plan may be declared when price has advanced
  ≥ 0.5 × ATR beyond the last plan's trigger. This is what "participate in a
  move that keeps going" requires, and it is bounded so it cannot become the
  CVX loop.

### 4.4 SWEEP CREDIT SPREAD — `SweepCreditSpread`
🔴 Carries the 2026-08-25 CVX finding, still open and NOT yet built.
- **declare when** a named level is pierced AND a bar **closes** back on the
  rejected side. Operator: *"a wick can be a pierce. But it takes a close to log
  a rejection."* The plan's identity is `(pool, reclaim_bar_ts)`.
- **trigger** the close itself — so the plan is declared and triggered by one
  event, and **that event is consumed.** One plan per reclaim bar. Re-firing
  requires a NEW closing bar. This is the operator's *"you tried once, you lost,
  it should be gone"* falling out of the definition rather than bolted on.
- **invalidation** close beyond the pierce extreme (acceptance)
- **instrument** short strike beyond the pool, existing selector
- ⟨PRIOR⟩ **pierce depth becomes a plan attribute**, not a pass/fail ceiling.
  Operator: *"the depth of the pierce is what's going to discriminate on what
  constitutes a pierce."* Recorded now, fitted later; a deep pierce may warrant
  a wider stop or no plan at all.

### 4.5 IRON CONDOR — `IronCondorStrategy`
- **declare when** RANGING, both boundaries identified
- **trigger** per side, price travels `CONDOR_TRIGGER_APPROACH` of the way from
  `bb_middle` toward that short strike
- **invalidation** close beyond the short strike
- **one plan, two triggers.** This is what makes the second leg legible: the
  plan stands with `leg2_pending`, so the PLANS panel shows a half-built condor
  waiting rather than 406 silent refusals (verified on CRM today).

### 4.6 GEX PIN BUTTERFLY — `GEXPinButterfly`
- **declare when** a firm pin exists and price is away from it
- **trigger** ⟨PRIOR⟩ price crosses within `0.5 × EM` of the pin, moving toward it
- **invalidation** close beyond `1.5 × EM` from the pin
- **window** `BUTTERFLY_ENTRY_START_ET` (12:00) → 14:00

### 4.7 DAILY FORK — `DailyForkCreditSpread`
- **declare when** a 1d fork is BUILT with containment
- **trigger** price touches the projected tine (rail at the plan's stamped index —
  **the rail is frozen at declaration**, never re-projected)
- **invalidation** close beyond the tine by ⟨PRIOR⟩ `0.25 × ATR`

### 4.8 CONDOR ROLL — `condor_roll`
Management, not entry: a roll is a plan whose trigger is the tested short strike
and whose instrument is the replacement leg. Declared when a leg is tested,
not when it is breached.

---

## 5. TIGHT AND RELAXED

`strategy/relaxed.py` already exists and is already loud
(`relaxed_entry=1`, populations separable forever). Plans inherit it with one
addition: **`mode` is stamped on the plan at DECLARATION and never changes.**

- **TIGHT** — the specified trigger, unwidened.
- **RELAXED** — `relaxed.widen()` may loosen the **declare-when** conditions and
  the instrument constraints (credit floors, POP, distance).
  🔴 **RELAXED MAY NEVER MOVE A TRIGGER OR AN INVALIDATION.** Those are
  structural prices. Widening the evidence bar produces more plans; widening the
  trigger produces a different trade wearing the same name — which is how the
  relaxed population would silently contaminate the tight fit.

A plan declared relaxed that fires is a relaxed trade, permanently.

---

## 6. THE TICK — AN ELIMINATION CASCADE, NOT A PRIORITY QUEUE

Operator, 2026-08-25, and this is the architecture:

> *"The primal question at every tick is 'are one of my available plans
> executable from HERE' not 'would any strategy FIRE here' — that is a TRIGGER
> not a PLAN. Every tick should be able to assign a binary to each available
> plan until it gets invalidated somewhere in the chain until only one strategy
> remains. Often that remaining strategy might be a GEX pin butterfly, other
> times it might be leg 2 of a condor, followed by GEX pin butterfly."*

**THIS REPLACES `if signal is None`.** Today dispatch is a priority chain: the
first strategy to produce a signal wins the slot and everything behind it is
never evaluated. That is why CRM's second condor leg re-signalled on 406
consecutive ticks with nothing in any log, and why the shape of a tick is
invisible after the fact.

**THE NEW TICK:**

1. Every standing plan is asked ONE question: **executable from here?** — a
   binary, answered by comparing the tape to prices fixed at declaration.
   Not a score. Not a ranking. Yes or no.
2. Plans that answer NO are **eliminated with a reason**, and the reason is
   recorded. A plan is not silently skipped; it drops out of the chain
   somewhere, and where it dropped is the finding.
3. **What survives is what trades.** The residual is not a fallback — it is the
   correct read of a tape on which everything else has been ruled out.

⚠️ **THE RESIDUAL IS MEANINGFUL, AND THIS IS THE PART THAT IS NOT OBVIOUS.**
When the directional plans have all been eliminated, a GEX pin butterfly is not
a consolation prize; it is the trade the tape is describing. The operator's own
sequence — *"leg 2 of a condor, followed by GEX pin butterfly"* — is an
ordering that FALLS OUT of what remains executable, not a hard-coded priority.
Elimination is what produces it.

⚠️ **AND THE ELIMINATION RECORD IS THE INSTRUMENT.** A tick that produces no
trade currently produces one line: `STRATEGY: NO TRADE`. Under the cascade it
produces a full account — six plans stood, five were eliminated, here is where
each one dropped, and the survivor was declined for this reason. That is the
visibility that was missing on TSLA today.

**INVARIANT:** every elimination test is a comparison against a fixed price or
a stamped structural fact. The moment a test re-derives a score, the cascade
becomes the old confluence engine with new vocabulary.

---

## 6b. STALENESS AND CONCURRENCY — still open, operator's call

Not settled by this pass, flagged rather than guessed:

1. **Staleness.** A plan declared at 11:00 on 10:55 evidence may be stale by
   11:40. Options: clock expiry ⟨PRIOR: 45 min⟩, structural expiry (the anchor
   itself moves), or invalidation-only. **Re-scoring is not an option — it
   reintroduces the loop.**
2. **Concurrency.** How many plans may stand at once, and if two survive the
   cascade on the same tick, what breaks the tie? Note the cascade makes this
   rarer than the old chain did — most ticks eliminate down to one or zero —
   but "two survivors" needs an answer before it happens live.

---

## 7. WHAT THIS BUYS

The PLANS panel becomes the primary instrument: every standing intent, its
trigger, its distance from firing, and the evidence that justified it —
**including every plan that never fired.** Today that population is invisible;
`strategy_note` records 182 evaluations and cannot say what any of them wanted.

⚠️ **AND IT IS A MAJOR BUILD.** Operator acknowledged it up front: *"It will be
a major build and it will likely set us back."* Eight strategies, a schema
change, a dispatch rewrite, and the tick loop inverted from evaluate-and-fire to
declare-then-compare.

---

## 8. AS BUILT — r146 (2026-08-26). This section governs where it disagrees with §3-§6.

**What r126-r145 delivered was not this document.** It was a second
implementation of every strategy inside `derived/plans.py` that guessed at what
the real one would do and recorded the guess (zero calls into `strategy/`; see
the r146 rebuild; its handoff was deleted at r269 once §8 held the
as-built record). Operator, 2026-08-26: *"The
strategy is the spec, the specification. The plan is how it executes according
to the spec … I don't need two strategies for every strategy."* r146 tears the
mirror out and builds the plan as he described it.

**THE SHAPE.** `strategy/plan.py` — one `Plan` per strategy, held as
`self.planner`. The strategy detects the setup, fixes the trigger and the
invalidation, selects the contracts and EXECUTES. The plan is the informer it
consults on the way: it prices the what-if off the contracts the strategy
chose (credit/debit, risk, **R**), runs the antagonistic checks — the
**session-map geometry** (`analysis/session_map.py`, the 2026-08-25 ruling)
and the **R hurdle** (`strategy/criteria.py`) — records every check every
tick into `plan_tick`/`plan_check` (schema unchanged from r126b), feeds the
edge-triggered gate reporter, and hands back a verdict the strategy honours.

```
t = self.planner.tick(price)
…  return t.refuse("gate", "why")          # every spec refusal — writes the row
…  return t.starved("chain")               # a missing input — NO PLAN row naming it
…  t.level(level, role, name, orb_hi, orb_lo)   # geometry; False = eliminated
…  t.credit_spread(short, long, credit)     # the what-if, REAL width
…  ok, why = t.executable()                 # R hurdle: STRICT refuses, RELAXED records
…  return t.take(signal)                    # the fire — clears the gate, opens the ledger row
```

**THE PLAN NEVER DETECTS A SETUP AND NEVER SELECTS A STRIKE.** `§3
declare_plan()` is NOT built and will not be: a plan that declares is a plan
that decides. The inversion §3 asks for — *"what price from here …"* — is
answered by the strategies that already fix a trigger (ORB, the condor's tine,
the sweep's pool, TC.6's bound) and recorded as `trigger_price` /
`invalidation` / `dist_to_trigger` on every row.

**THE CASCADE (§6) IS NOT BUILT.** Dispatch is still the priority chain.
What §6 wanted from it — *"everything that was still on the table at each
tick"* — is delivered by the board instead: `derived/plans.py` v2.0 writes a
**NOT ASKED** row, carrying the dispatcher's reason (`main.py` v4.16 states
it at every skip point), for every strategy the chain never called. So every
tick has one row per strategy: TAKE / DECLINE / NO PLAN / NOT ASKED / HOLD /
ROLL. Replacing `if signal is None` is a separate decision.

**STRICT / RELAXED (§5).** Under STRICT a plan below `R_FLOOR` (1.00,
`OT_PLAN_R_FLOOR`) REFUSES and the strategy returns None — **this changes what
trades on a strict box**, deliberately; it is the "gating on 1:1" the operator
asked for. Under RELAXED the R value is recorded, the row carries the
`r_muted` check, and the trade proceeds. The R floor can therefore only ever be
fitted from strict sessions. Triggers and invalidations are never widened.

**ORB — zero hurdles, recorded.** Operator, 2026-08-26: *"Include orb in
that, zero hurdles."* ORB's three post-confirmation refusals and its fire
write rows; `executable()` is never called on it; main.py records the
engine-not-confirmed state. The 2026-08-25 ruling stands.

**R DEFINITIONS.** Credit vertical: `credit / (width − credit)`, real width
(the builders assumed $5 everywhere). Debit directional (runaway): stop = the
ORB boundary, target = the stop distance mirrored, `gain = δ·d + ½γd²`,
`loss = δ·d − ½γd²`. Butterfly: `(width − debit)/debit` — NOT YET PRICED,
because the butterfly spec never selects its legs (its signal cannot be valid
today; parked anyway).

**FOUND WHILE WIRING.** `RunawayContinuation`'s signal was ALWAYS invalid —
`target_delta` had one writer and zero readers, no strike/premium/contract,
`is_valid` False on every fire (`main.py`: "Invalid signal from
RunawayContinuation"). Fixed in r146: the strategy resolves its contract off
the chain the dispatcher already passes. The flagship v4 entry rule could not
have placed a trade before this revision.

**NOTED, NOT CHANGED (operator's call):** the condor and daily fork select
strikes ONCE at plan-build; they do not follow the sloped tine to the trigger,
which the fork thesis ("that's the level, but sloped") implies they should.

---

## 9. r147 — leg two is a ONE-LEVEL plan; the butterfly is unparked

**The condor is opportunistic, not a structure.** Operator, 2026-08-26: *"If
the complementary vertical spread becomes available on mapper, the plan
should account for it and confirm a rejection of the level before deploying
the second leg. Acceptance of the level invalidates it and the plan should
start looking at the next available level … it cannot pre-select strikes
beyond the next available one until it's invalidated by acceptance … We would
not sell a complementary spread on a level that's getting breached."*

- **Leg one is unchanged** — its own trigger, no thought of a second.
- **Leg two** (`IronCondorStrategy.plan_second_leg`, plan name `CondorLeg2`)
  runs only while exactly one credit side is open. Each tick it takes the
  **next available level** of the complementary role from the shared session
  map — fork tines (both timeframes) and the mapper's named pools, geometry-
  valid, not finished today, of a class the Rule 4 pairing table permits —
  ONE level, and prices the what-if for that level only (first strike beyond
  it, condor wing, credit off the live chain, R at real width).
- **Four states at the level** (`analysis/level_test.py`, the sweep detector's
  own definitions): UNTESTED → hold · BREACHED (through it, no close back, not
  yet accepted) → hold, **no fire** · REJECTED (tested, last 1m close back
  inside) → fire, R hurdle strict/relaxed as everywhere · ACCEPTED
  (`ACCEPT_CLOSES` closes beyond) → the level is **finished for the session**
  and the plan moves to the next. Finished levels persist in `plan_ledger`
  (strategy `CondorLeg2`, EXPIRED/accepted) and are reloaded after a restart.
- **Consequence:** the sweep and TC.6 no longer fire a second leg directly;
  a named pool completes a condor only as a rejected level inside this plan,
  which is the rejection the operator always required of the sweep class.
  `_can_open_credit_spread` still gates the fire (Rules 1/3/4 + geometry).

**GEX pin butterfly — ON** (`GEX_BUTTERFLY_ENABLED`, `OT_GEX_BUTTERFLY=0`
parks it). Apex on the pin; wings at ⟨PRIOR⟩ 0.25 × expected move rounded to
the increment, floor one increment, ceiling the pin distance; call fly below
the pin, put fly above it; exact strikes or no trade; net debit off marks;
R = (width − debit)/debit — strict vetoes below 1:1, relaxed records.
Its signal is valid for the first time (three contracts, `is_butterfly`).

---

## 10. r160 — the plan is ANTICIPATORY, the strategy is CONFIRMATORY (supersedes §8 where they differ)

Operator, 2026-08-27, read back and confirmed: the plan *"evaluates the
current tick what would need to be true on the next tick for the active
strategies to execute. That means strike selection, wing width, stop
placement (for r-value), minimum r-value acceptable for entry."* The strategy
*"execute[s] the transaction with the variables selected by the plan."*

**The split.** On tick *t*, in the strategy's slot, the plan reads the feed,
evaluates every condition the strategy DECLARES (`CONDITIONS`, name → what
"true" means), selects every variable of the trade — level, side, short
strike beyond it, wing searched to `R_FLOOR`, credit on bid/ask, stop and its
survivability, R and its minimum — and writes the row. On *t+1* the strategy
checks the declared conditions against the tick and, if all are true,
executes THAT trade. The strategy holds no chain and picks no strike. Which
layer decides? The declared conditions do; the plan reads them and reports.

**The rows, per tick, per active strategy:** DORMANT (outside the slot, one
row, no narration) · NO PLAN naming a missing input · DECLINE on a
STRUCTURAL fault the trigger cannot cure (spent level, geometry, no wing
clears R, no credit, stop inside the spread — never muted by relaxed) ·
HOLD "PREPARED — sell 95P / buy 92.5P credit 1.30 stop 1.50 R 1.08 (min
1.00). Waiting on: reclaimed" · TAKE with those exact variables.

**Built in r160: the sweep** (`SweepCreditSpreadStrategy.prepare()` is the
plan, `generate_signal()` the spec). The r146 informer shape — strategy
selects, then asks the plan to price — is inverted for it. TCS, runaway,
daily fork and butterfly still carry the r146 shape and are next, one at a
time. ORB excluded by ruling.

**The condor is a management plan, not a strategy** (operator, 2026-08-27):
*"If there is already an active vertical spread of type (call/put) then only
a complementary vertical (call/put) SWEEP trade is authorized to fire.
Everything else is gated off. The condor doesn't select anything, but it
starts managing once leg 2 is born … a roll if threatened, and the inverted
hedge butterfly if breached, in order of escalation and closed entirely if
uneconomical to save it."*
- `authorize(open_sides)` → the complementary side, only as a sweep; the
  sweep's own plan prepares its own level. `plan_second_leg` and all level
  selection (r147/r158/r159) are deleted. Rule 4's table reads sweep
  everywhere (the fork tine is fine for leg one; leg two is universally a
  sweep — *"only a rejection at the site of the second vertical spread would
  inspire enough confidence to sell credit there"*).
- `manage()` writes the per-tick management row for a formed condor: which
  rung (1 ROLL to risk-free / 2b TENT / 3 CLOSE — TRADES.md "Exits — a
  management LADDER"), what the next rung costs right now, does it clear.
  Execution stays in `condor_roll`. The tent's hedge is the OPPOSITE type of
  the surviving vertical (call vertical → buy a put; put vertical → buy a
  call), equidistant, boxing price in.
- 🔴 **Found in source, named on every such tick:** rung 1 executes only a
  risk-free roll and the tent arms only after a roll, so a formed condor
  with no risk-free roll available is on NO RUNG while price walks through
  a short. The row says "NO RUNG — the ladder says never do nothing on a
  tested structure." Whether rung 2 (invert: roll the untested side
  adjacent to the tested short, TRADES.md) should execute when risk-free is
  unreachable is the operator's call; today it is documented, not built.

**Audit of r148–r158 (r159, folded in):** the layering held at HEAD —
`permit()` carried no contracts, the condor constructed nothing. Three
defects fixed: the land gate had been red since r152 (the exorcism gate
tripped on r152's own test); three files changed without a version bump or
changelog entry (recorded retroactively); leg two was dead whenever the
nearest complementary level was a tine — moot now that the condor selects
no level. On the r158 handoff's "plan-side gatherer that
searches the feed": correct in its goal, dangerous in its wording — the plan
gathers measurements and selects variables; it never decides that a setup
exists. Starvation by name is the part of that handoff that is built.

**Tested on hypotheticals** (`tests/check_plan_prepares.py`, 16 scenarios):
a sweep not yet reclaimed holds with the trade fully prepared; reclaimed
fires with the plan's numbers; no wing clears R → declined even with the
trigger true, relaxed included; no chain → starved; outside the slot →
dormant; a call vertical open → the plan prepares the LOW sweep, not the
fresher HIGH; a spent pool → declined. The condor: nothing open → no
restriction; one open → its complement, sweep only; both → nothing. Formed:
untested → hold; tested with a risk-free roll → ROLL with the numbers;
tested without one → NO RUNG; rolled and breached → TENT, opposite type,
floor stated. One hypothetical was wrong before the code was — a wing
priced at 0.30 on a 2.5-wide spread gives R 0.79 and the plan refused it.

---

## 11. r161 — the butterfly earns its entry, and is exempt from the slot rule

Operator, 2026-08-27: *"I want it to be able to fire regardless if any other
open trades are found. Reason: it has such a high hurdle to clear. GEX
pinning, pin reachable, economic feasibility. If it can achieve all that,
it's earned an entry."* TRADES.md §3 has said since r33: *"no position slot,
no capital, no competition."*

- `GEXPinButterflyStrategy.prepare()` is its plan (the §10 shape): dormant
  outside the slot; each declared condition with its reading — enabled,
  pinning, pin concentration, window, expected move, pin reachable
  (30–100% of EM); the three legs SELECTED around the pin (exact strikes,
  wing from the expected move); R = (width−debit)/debit against `R_FLOOR`
  as a STRUCTURAL check — feasibility is the third hurdle, so relaxed does
  not waive it. `generate_signal()` executes the prepared legs.
- `main.py` v4.19 asks it every tick of its slot in both branches of
  `main_loop`, position open or not, and a fire APPENDS its record
  (`add_open_position`, position_manager v4.4) — never replacing the
  vertical under management. The execution tail is one function
  (`_execute_entry_signal`) for both paths. The condor's authorization no
  longer gates it.
- Hypotheticals (B1–B7): a weak pin holds with the fly prepared, naming
  the wait; strong, reachable, R≥1 fires with the plan's legs; R 0.47 is
  declined, relaxed included; NEUTRAL with a published pin strike holds
  with the fly prepared, waiting on pinning; no exact apex strike is
  declined, never substituted; the open-position branch asks it; the
  append does not drop the vertical.

---

## 12. r163 — a tine is a moving liquidity level; a touch is its event

Operator, 2026-08-27: the daily fork is *"essentially a moving target
liquidity mapper but with the elements of slope and time"* — *"basically a
moving level that sweep is allowed to use, but with a touch, not a reject.
The plan would still need to select a strike beyond the move that caused the
touch."* And: *"it's allowed to be the 1st leg of a condor too, but again as a
touch not identical to sweep which requires rejection."*

- **The mapper owns the level** (`liquidity_mapper` v4.2). `publish_tines`
  runs at the assembly point right after the condor trigger map: each active
  rail becomes a moving named pool ("1h upper tine", "1d lower tine") with
  `price_at(t)` = price − slope·(minutes back). `_detect_touch` walks the
  last 30 one-minute bars and compares each bar to the rail **where it was
  on that bar** — a bar that reaches today's value but not the rail as it
  stood then is not a touch. The event is emitted as a sweep-shaped
  `LiquiditySweep` (`touch=True`, `moving=True`, born `reclaimed`,
  `sweep_price` = the extreme of the touching move); `ACCEPT_CLOSES` closes
  beyond `rail(t)` since the first touch invalidate it.
- **The sweep's plan uses it** (v4.7) exactly as a pool, with three
  differences: under the condor's authorization a touch is never selected
  (leg two requires a rejection); the spent lock is keyed by the tine's
  name, since its price drifts; the signal is classed `{tf}_fork` under
  Rule 4. The strike is selected beyond the touching extreme, as for any
  sweep.
- **The daily-fork strategy is deleted** (373 lines + its dispatch). The
  1h and 1d tines reach the trade through one detector, one plan and one
  construction path.
- **Hypotheticals T1–T7:** a rising rail is touched by a bar that reached
  it where it was (99.95 vs 99.90 then, 100.00 now); the same bar against a
  falling rail is no touch; two closes beyond invalidate; the touch fires
  leg one with the short beyond the high, classed `1h_fork`; as leg two the
  touch is never selected; an invalidated tine holds naming `invalidated`; a
  stopped-out tine stays spent by name after its price has moved. Two
  hypotheticals were wrong before the code was — both pricing a wing that
  could not clear R≥1 — and the plan refused them.

---

## 13. r164 — TCS in the §10 shape

`TrendCreditSpread.prepare()` is the plan: dormant outside TCS_START_ET–
TCS_ENTRY_END_ET; each declared condition with its reading (active, window,
no condor plan, directional vote, ADX floor, price still outside the range
on the trend side); the spread SELECTED — short at the first strike inside
the opening range from the trend side, wing searched to `R_FLOOR`, bid/ask
credit, POP, EV margin, nickel floor; exit stays BREACH-or-nickel (no premium
stop, so `stop_survivable` does not apply). `generate_signal()` executes it.
The muteable R hurdle is gone from TCS — `wing_r_best` refuses structurally.
When the vote is not directional there is no side to prepare, and the row
says so. When a structural fault and an unmet condition coincide, the
structural fault is reported first (a trade the plan could not build
outranks a trigger that has not fired); the condition is still recorded.
Hypotheticals C1–C6.

---

## 14. r165 — the runaway: the plan holds the contract, gamma does the lifting

Operator, 2026-08-27: *"the symbol did not even entertain coming back for a
retest, it just broke out & ran. We want in on the move, but it needs to be
over quickly … purchase and wait for our trailing stop"* and *"Make gamma do
the heavy lifting. Try to get just enough OTM to really leverage gamma based
on the intensity of the move."* Stops are deliberately not in this cut.

- `prepare()` is the plan: dormant past the cutoff; each declared condition
  with its reading (ATR reachable, ORB broken with a direction — including
  the handoff after the engine invalidates on "runaway" — a 1m close beyond
  the 50% TP still holding); the CONTRACT selected before the confirmation,
  so the fire is a purchase.
- **Selection is gamma leverage over the move's own run.** The distance
  price has already travelled from the ORB boundary is the intensity, taken
  as the expected continuation (mirrored, no fitted multiple). For every
  liquid OTM contract on the move's side: gain = δ·run + ½γ·run², scored per
  dollar of premium. Raw leverage-per-dollar always crowns the cheapest
  far-OTM ticket; "just enough OTM" is the **reachability band** — the
  highest leverage among strikes within the run, else the first OTM. On a
  0.90 run the plan picks the 102; on a 1.90 run the 103. The ATR delta band
  (DELTA_NEAR/DEEP) no longer selects; ATR keeps its one job, the
  reachability floor.
- The R hurdle stays muteable for this debit (strict vetoes, relaxed
  records) — there is no wing to search to a floor.
- Hypotheticals R1–R8. One was wrong before the code was: the test assumed
  the raw leverage ranking would crown the 103; it crowns the 105, which is
  exactly why the band exists.
- Also fixed on the way: `ensure_tables` guarded on `id(store)`, and recycled
  ids let a fresh store skip CREATE TABLE (plan.py v1.4).

**The inversion is complete for every strategy except ORB (excluded by
ruling).** Sweep, butterfly, TCS, runaway all prepare then execute; the
condor authorizes and manages; the tines ride the mapper.

---

## 15. r166 — the management plan: one watcher per open position

Operator, 2026-08-27, on where stops live: *"The plan seems like the right
place for them … I like the thought of it watching & thinking if it does
'this' or 'this' we're out!"* And: *"if there is a way to incorporate those
vectors back into the management (and stop functions) I think that is the
logical next step."*

The same split as entries, per open record:
- **The strategy declares its exit conditions** as data
  (`strategy/management.py` `EXIT_CONDITIONS`) — the runaway's hard stop,
  structure stop, trail and target; the sweep's premium stop, acceptance
  through the pool and nickel; TCS's breach-or-nickel; the condor's ladder;
  the butterfly's stop and target.
- **The management plan watches.** After `manage_open_position` has priced
  and decided, it reads each condition's current value off the record and
  the exit engine's own state (premium now, stop premium, trail stop, target,
  underlying stop, MFE/MAE, ticks held) and writes one row under
  `<Strategy>/manage`: *"RunawayContinuation call 1.00 → now 1.30 (+30%),
  MFE 1.34, 12 ticks: premium <= 0.75 → out (hard_stop); 1m close < 101.00
  → out (structure_stop); trail not armed yet; premium >= 2.00 → out
  (target)."* Credit spreads read with credit semantics (value falling is
  profit; the stop reads ≥). It holds no threshold of its own — M9 refuses a
  literal compared to a premium.
- **The r66 vector is recorded for the open position** every tick
  (`strategy_note`, outcome "manage", trade_id attached) — aggression at the
  level, tape, VRP, charm — so a stop can later be fitted against what the
  tape was doing while the position lived, not only at entry. Two gaps
  closed: TCS now has a vector (vote, ADX, ORB width over EM, tape); the
  condor's vector, silent since r158, is written from its `manage()`.
- **The exit engine executes, unchanged.** Nothing in this cut moves a stop.
  When the stop conversation happens, this row is where it lands: the plan
  will *compute* the trail instead of reading it, and the exit engine will
  act on the plan's number.

Hypotheticals M1–M11. One caught a defect before it shipped: a SHORT runaway
is hurt by a close *above* its stop, and the first draft's direction logic
would have narrated "<".

---

## 16. r167 — managed exits: the plan decides, the engine calculates and executes

Operator, 2026-08-27: *"I'm ready for the managed exits build, if on the next
tick is this, cut it loose, or roll, or whatever the management is."* With
the rulings: *"Everything tied to the orb stays. Even the trailing stop armed
at 50% and the tightening after 100% on the peak. The other variables for the
other strategies were all good except for the BOS"*; *"We still have the 15%
floor & the 'breach' stops"*; *"the condor doesn't start managing until both
legs are in the table. Prior to that a lone credit spread stops out at a 15%
floor & the level that it sold at is marked 'finished'."*

- **`ManagementPlan.decide()`** returns the intent for the next tick —
  CLOSE / TRAIL / HOLD — for the records it covers: the runaway, the
  butterfly, and a sweep or TCS vertical while it stands alone. Order, and it
  matters: (1) the declared spec conditions read off the record — the 15%
  floor / hard stop, the breach stops (a 1m close through the ORB boundary,
  the bound, the pool), the target, the nickel — never outranked; (2) the
  engine's calculators — the 50% trail, the tightening after 100% on the
  peak, theta bleed, velocity stall — reached through `evaluate()` and
  adopted as the plan's own. Every intent is a row before it is an act.
- **`position_manager` asks the plan first** and executes the intent through
  the same `_execute_exit` and trail persistence as before. Records the plan
  does not cover — ORB, ADOPTED, tents, a formed condor — go to the engine
  exactly as before. **ORB is untouched end to end.**
- **BOS is retired** from the decision path (measured 34% / 217 / −$7,085).
  Nothing else the engine did is lost.
- **A lone credit vertical that stops out finishes its level** for the
  session — the spent lock now covers every credit vertical (TCS keys on the
  ORB bound it sold against).
- Hypotheticals D1–D15: floor → CUT with the calculator never consulted; a
  close through the boundary → structure stop; the engine's trail adopted;
  theta bleed adopted; the 15% floor on a lone sweep; acceptance through the
  pool; the nickel; TCS at +38% against with no premium floor holds, and the
  breach closes it; two legs → not the plan's; ORB/ADOPTED/tent → never the
  plan's; the butterfly's target; BOS gone; the seam order; ORB's path intact.

---

## 17. r168 — the runaway's stop is a 20% premium floor; the structure stop is ORB's alone

Operator, 2026-08-27: *"the orb structure stop only applies to the orb. The
runaway stop is the orb boundary — but I think that's a terrible stop
location. I would prefer (since it's a debit), a decay or adverse movement
amounting to a 20% loss — I know that is an odd choice, but I still want the
15% on credit spreads. The runaway needs room to breathe. A few pullbacks in
an uptrend are ok."*

Read back from `orb_engine.py` / `exit_engine.py` for the record: the ORB's
**impulsive candle** opens inside the opening range and closes outside it —
definitional, no tolerances; its **structure stop** anchors to that candle's
wick (low for a long, high for a short) and fires only on a 1m close beyond
it; closing back inside the range is not an invalidation. **That rule is
ORB's and only ORB's.**

The runaway (`RUNAWAY_MAX_LOSS_PCT` 0.20): no `underlying_stop` on the
signal, so neither the plan's breach check nor the engine's structure stop
can fire on price; `stop_loss_pct` 0.20 becomes the record's immutable
floor; the trail at +50% and the tightening past 100% still apply through
the calculator. The plan's R prices the risk as 20% of premium against the
modelled gain over the run. r146–r167 had carried the ORB boundary as the
runaway's invalidation — retired.

Hypotheticals: D1 the 20% floor cuts; **D2 a 1m close back through the ORB
boundary with the premium above the floor HOLDS** — the test that would have
caught the earlier mistake; D2b/D16 pin the split; R2b the signal's shape.

---

## 18. r169 — the butterfly rides to the close

Operator, 2026-08-27: *"I want both adjusted for best case. 1545 flatten or
25% loss. Whichever comes first."* The 20%-of-max-profit target and the
150-minute max hold were v3 inheritances chosen for no premise of this
trade: a 1.00-wide fly bought for 0.18 is worth 1.00 at the apex at the
close and the target closed it at 0.34. Both are retired from the decision
path (exit_engine v4.8; the constants stay informational). The butterfly's
exits are exactly two, like the credits: the 25% floor and the 15:45 hard
close. The management row reads *"premium <= 0.14 → out (floor); 15:45 →
flatten (rides to the close)."* Hypotheticals D12/D12a/D12c, M5.

**The exit map, complete (r168 + r169):**
ORB — 25% floor, impulsive-origin structure stop, trail +50%, tightening past
100% · Runaway — 20% floor, trail +50%, tightening past 100%, no price stop ·
Sweep / TCS / lone condor leg — hold to the close, 15% floor, a close through
the level, the nickel; a stop-out finishes the level · Formed condor — the
ladder · Butterfly — 25% floor, 15:45 flatten. Nothing else closes a trade.

---

## 19. r170 — the readers

Operator, 2026-08-28: *"I need a reader outfitted in devtools and have
query.py snapshot active trade decisions 'enter on' and 'exit on' for active
plans. Trade log & all time performance should stay."*

- **On the box** (`query.py` v4.2): a DECISIONS panel at the top of the
  derived half — ENTER ON: the newest `plan_tick` row per strategy (the
  PREPARED trade and what it waits on, the structural fault, the missing
  input, or the slot); EXIT ON: the newest `<Strategy>/manage` row per open
  position. Rows older than five minutes are flagged STALE by the box
  itself. `python query.py --decisions` renders only the snapshot; the full
  dashboard — trade log, all-time performance, market — is the unchanged
  default.
- **On control** (day_trader_pro devtools v1.56): SENSORS item **DECISIONS
  NOW** runs the box's own `--decisions` across the chosen scope. The
  formatter lives on the box, so the fleet reader and a shell on any box
  always show the same thing.
- Order of landing matters: otv4 r170 to the boxes first, then the dtp
  menu — the item is transport for a flag the boxes must understand.

---

## 20. r174 — the teenie lesson: two structural gates on the runaway

2026-08-28, first live session of the gamma pick, relaxed collection: every
runaway fill was ~$1,000 of far-band teenies (AMZN 270C ×63 @ $0.17, GOOGL
352.5C ×77 @ $0.14), each dead in minutes at −20 %/−35 %, some twice on the
same break. Three mechanisms stacked: a 20 % floor on a $0.15 option is
three cents — inside its own bid/ask, so the stop was the next mark wobble
and it gapped; gain-per-dollar rises with distance, so the leverage score
crowned exactly those contracts at the band's far edge, and R against a
pennies denominator looked spectacular to the sizer; and a stopped runaway
re-armed on the same still-true conditions. Operator: *"Yes to both, even on
relaxed."*

- **The floor must clear the spread** (`gamma_leverage_pick`): a contract
  qualifies only if `RUNAWAY_MAX_LOSS_PCT × premium` exceeds its own
  bid/ask spread; no candidate clears → structural DECLINE naming the count
  rejected. No new knob — the spread is the tape's own number. This is what
  keeps the leverage score off the teenies and lands the pick on
  real-premium strikes.
- **One runaway per break**: a floor stop-out finishes that (direction,
  boundary) for the session — `finish_break()` called from trade_logger's
  losing-exit hook, refused structurally in `prepare()`. A NEW break at a
  new boundary is a new trade. In-process registry; a restart clears it,
  recorded as acceptable.

Hypotheticals R9–R13. Both gates are structural: relaxed waives neither.

---

## 21. r175 — TCS prices its own premise: POP with the session's measured drift

2026-08-28, the strongest trend day of the week: TCS declined ~193 ticks per
box fleet-wide on one gate — `pop < 0.70` at ADX 21–53. The driftless model
(deliberate: "a drift term would be a forecast") priced an ADX-50 uptrend as
a random walk, so a with-trend spread near the bound read 0.55–0.65 forever.
The strategy believed the trend at the door and disbelieved it at the till.
Operator: *"You have to get it firing in ESPECIALLY this type of day … A
trend day we should be killing it & on chop we stay out. Fix it to behave
like that."*

- `pop_drift(d, σ, n, μ, h)` = Φ((d + μ·min(n, h)) / (σ√n)) — `credit_vertical`
  v4.2. μ is MEASURED: the session's realized per-5m-bar drift since the RTH
  open, from the same df_5m the ATR reads (VolatilityState carries the frame,
  v4.3). SIGNED toward safety: a put spread under a rising tape gains; under
  a falling tape it reads WORSE than driftless — chop stays out with teeth.
  μ=0 or h=0 reduce exactly to the old model. h = TCS_DRIFT_HORIZON_BARS
  (24 × 5m = two hours) — a stated baseline prior, not a fit.
- On today's MU shape (3.2 under spot, σ 2.7, 45 bars): driftless 0.57
  refused; with the measured 0.59/bar drift, 0.83 — fires. Chop (μ 0.02):
  0.58 — stays out. Reversal (μ −0.40): 0.36 — harder out.
- TCS only. The sweep's and condor's `pop()` stays driftless — their premise
  is reversion, not drift.

Hypotheticals T1–T7 (r175 block). The floor stays 0.70 — the operator's
70–80 % band; what changed is that the number being floored now includes the
premise the entry already required.

---

## 22. r176 — the debit cutoff does not relax; the drift reads the vote's clock

Operator, 2026-08-29: *"Debit entries are finished at 1130, period. Do not
extend it for relaxed. We are burning theta."* And: *"Runaway and orb are
done at 1130. Credit takes over once any open orb or runaways conclude &
close out."*

- **Runaway v4.7 / criteria**: the relaxed 14:00 extension is deleted; the
  cutoff is `CUTOFF_ET` under every posture. This also ends the afternoon
  slot starvation the extension caused — the runaway's evaluation had been
  claiming the dispatch slot until 14:00 on trend boxes (AMZN 695 NOT-ASKED
  rows in one afternoon), so after 11:30 the box now belongs to the credit
  book and the butterfly. ORB was already hard-cut (engine expiry 11:00,
  structure-keyed afternoon-debit gate 11:30, no relaxed path). An open
  debit position still rides its trail and still holds the slot until it
  closes — that is the ruling's second sentence, and it is the existing
  single-position behaviour.
- **TCS v4.9 (drift window)**: μ is measured over the LAST
  `TCS_DRIFT_HORIZON_BARS` (two hours), not since the open. Since-open
  zeroed on V-shapes and late trends — MU read drift +0.18 while the vote
  saw BEARISH ADX 52. The vote and the drift now read the same clock,
  symmetric with the projection horizon.
- Hypotheticals R14/R14b (the cutoff holds under relaxed; the extension is
  gone from source) and T8 (a net-flat V-shape reads −0.48/bar over the
  window instead of the flat zero).

Next gate to watch after this lands: `wing_r_best` / `wing` — CRM passed pop
594 times and died there; it eases as pop rises (the EV hurdle divides by
pop), and if TSLA-at-ADX-64 still can't find a wing after a session of r176
data, that dial gets the same evidence-first treatment.

---

## 23. r177 — the butterfly's starved input, and the fit's join key

Operator, 2026-08-29: *"No GEX butterfly trades were initiated either …
ensure nothing is blocking those … and if nothing is blocking, decide if
the criteria is even possible to satisfy or if it's just too strict."*

- **Something was blocking, and it was total.** main's butterfly dispatch
  read `getattr(chain, "atm_iv", 0.0)` — **OptionsChain never had that
  field.** The default masked the absence (invisible to
  check_attr_fidelity), expected_move starved on every box on every tick,
  and the butterfly was structurally unable to fire from the inversion
  (r160) until now — while pinning and concentration were passing on ~10
  boxes. `OptionsChain.atm_iv` (v4.2) now assembles the scalar from the
  streamed per-contract ivs the chain already carried: median of the 3
  nearest-to-spot per side, decimal. When the feed has no ivs it reads 0.0
  and the no-fallback starvation stays loud — the supply was fixed, not the
  standard.
- **Satisfiability, from Thursday's own panel against real EMs:** AMD pin
  480 / spot ~475 ≈ 68% of EM; AMZN ≈ 71%; CVX ≈ 90% — inside the 30–100%
  band. Several boxes would have been armed. The bar is high but not
  eclipse-rare; it was the dead input.
- **tick_id** (plan v1.5, notes v4.2): begin_tick's monotonic counter
  persisted on plan_tick, plan_check and strategy_note; in-place ALTER for
  existing stores; pre-r177 rows read 0. The vector↔plan join is by key
  before the first fit.

check_tick_join.py, born red at 7f60245: A1–A3b, J1–J2.

---

## 24. r178 — 🔴 hotfix: one butterfly per pin per session

2026-08-28 15:00–15:01: the hour r177 unblocked the starved atm_iv, every
condition was genuinely true on UNH's pin and the strategy fired the SAME
397.5 fly five times in ninety seconds. The additive exemption (r161) let
it stack ITSELF, and it had no self-lock — it had never once fired to need
one. Same failure class as the runaway re-arm; same doctrine as that fix.

- `PLAYED_PINS` registry on the strategy: the dispatch marks the pin AFTER
  `_execute_entry_signal` (a refused fire does not burn the pin), keyed by
  the `pin_strike` the signal now carries — the same key `prepare()`
  checks. A played pin is a **structural DECLINE**, checked before the
  conditions; relaxed does not waive it. A NEW pin (the magnet migrates) is
  a new trade. In-process; a restart clears it, recorded as acceptable.
- Hypotheticals B10–B13 — the **tick after the TAKE**, which is now a
  standard question for every strategy: identical conditions next tick →
  DECLINE `pin_played`; the migrated pin prepares; the fire site marks
  after execution.

---

## 25. r179 — 🔴 one runaway, one butterfly, per session, per box — DB-backed

Operator, 2026-08-28, after the butterfly stacked through two hotfixes and
five restarts: *"Only one runway debit trade aloud per session on a box.
Only one GEX Pin butterfly allowed per session on a box. Simple."*

Why the earlier locks failed: r174's break registry and r178's pin registry
were in-process, and every systemd bounce cleared them — 08-28 had five.
This cap reads **trades.db**: `count_today(strategy)` counts entries this
ET session, open or closed; a restart reads the same number. Guarded at all
three dispatch sites BEFORE the strategy is asked, each skip a plan row:
`one per session on this box — already traded today`. **Fails closed** — an
unreadable DB counts as traded; a missed entry is recoverable, a stack is
not. The pin/break registries stay underneath as belt-and-suspenders.

check_one_per_session.py, born red at d29a9fc: S1–S5b (session boundary in
ET over UTC storage; closed trades spend the shot; the restart test; fail-
closed; the three guards and their order).

---

## 26. r181 — ORB sizes on actual risk: pure geometry off the impulsive candle

Operator, 2026-08-28: *"adjust the position size based on 'actual' risk …
using the impulsive candle as our sizing criteria … normalize it to 1
contract minimum under the worst possible entry"* — and on the tail: *"I'm
actually good, even with the worst case taking the 25% floor on a leveraged
position with a tight stop."*

`contracts = max(1, floor(orb_width / stop_distance))` at the sizer seam in
`_execute_entry_signal`, ORB only. The stop is the impulsive candle's LOW
(long) / HIGH (short) — `signal.underlying_stop`, which the engine already
carries. Worst entry (stop ≈ width) = 1 lot by construction; the operator's
example: 6.35 range, 0.61 stop → 10 lots, 6.05 stop → 1 lot; the structure
stop costs ~the same dollars at every geometry (~−$275 on the example, both
extremes). **No notional cap for ORB by ruling**; the 25% premium floor
stays underneath as the gap backstop at whatever size results. Degenerate
geometry (distance ≤ 0 or > width) sizes 1, loudly. Engine and strategy
untouched — ORB keeps its no-plan exemption; this is one gated override
after `compute_size`.

check_orb_geometry_size.py, born red at 14869dc: G1a/G1b the operator's two
extremes, G2 worst-entry 1-lot, G3 degenerate guard, G4/G5 the seam (one
sizing assign, one override, after compute_size, ORB-gated).

---

## 27. r207 — ONE CONFIRMATION, ONE ORDER; THE GEOMETRY IS FROZEN AT THE BREAK

Operator, 2026-09-01, after QQQ took two ORB shorts off one confirmation:
*"The only way it should be allowed to fire an order is a very specific
sequence."* His sequence, and it is now the gate rather than a description:

1. **BREAK** — a 1-min candle CLOSES outside the range. The candle must also
   OPEN INSIDE it (v3.5, kept by ruling: a candle already outside never broke
   out of anything).
2. **RETEST** — a 1-min candle TOUCHES or re-enters the range and still CLOSES
   outside it. The BODY test is kept by ruling, so open *and* close stay
   outside; the touch is `<=` / `>=` (r207), because *"a touch is acceptable as
   a re-enter, we are just making sure the level is respected before
   committing."*
3. **SIZE** — `orb_width / |entry - stop|`, unchanged from r181/r192. The
   stop is the impulsive candle's wick; the distance is measured **from the
   fill**, because that is what is actually at stake.
4. **ORDER** — the contract count as one limit at the mark. Live: a standing
   DAY offer (r195). Paper: the same path, filled whole, immediately.
5. **EXIT** — a 1-min close through the impulsive candle's high/low, or one of
   the capital-preservation stops. The 25% premium floor keeps its precedence
   over the structure test by ruling: *"if the floor fires on a retest and
   breathe, it's because we lost the edge."*

**Any break in that sequence blocks construction**, and the enforcement is a
latch on the CONFIRMATION (`ORBData.order_placed`), not on the order plumbing.
r195 used `_orb_offer_working()`, which reads a table paper never writes,
because `_place_single_leg` short-circuited to the paper filler above the
standing-offer branch — so paper had no duplicate suppressor at all while the
board stayed green. A latch on the confirmation is mode-independent, and
`_rearm()` replaces ORBData wholesale so the next genuine attempt is clean by
construction rather than by anyone remembering to clear it.

🔴 **THE SIZING RULE DID NOT CHANGE, AND AN INTERMEDIATE CUT OF r207 CHANGED
IT WRONGLY.** That cut sized on the boundary-to-wick distance frozen at the
break, on the theory that a fire priced against its own stop should not size
up. Operator, 2026-09-01: *"The true risk is based on where we entered though,
not the range boundary. That's arbitrary. The 2 factuals are the distance from
entry to the stop."* Correct. The stop is a **price level**, so what is at
stake is the gap between the **fill** and it; the boundary is where the candle
started and stands in for the entry only while the two coincide. Freezing it
bought determinism and paid for it in truth, which is the wrong trade — r119
and r181 both already said actual risk.

⚠️ **AND IT WAS THE SAME DEFECT FIXED TWICE.** The 2-then-24 was an
**illegitimate fire** — a spent confirmation re-fired off a stale ORBData — not
a mis-sized one. The latch and the engine re-read remove it on their own. A
second repair aimed at a symptom the first had already deleted is how a fix
becomes a defect; it is recorded here rather than quietly dropped.

`stop_distance_px` survives as a **recorded field only** — how deep inside the
range the invalidation sits, which is r119's own open question and r119's own
ruling on it, *"observe first. Obviously."* `check_orb_sequence` S8/S8b fail if
anything ever sizes off it, the same shape as r119's G4.

⚠️ **THE 15-SECOND DRIFT IS RULED A WASH, NOT A GAP.** The fire lands on the
tick after the retest bar closes, so price can move before the fill. Operator,
2026-09-01: *"I'm ok with fast tape because sometimes it works in our favor and
sometimes it doesn't. It's a wash."* Symmetric, so there is no floor, no
refusal and nothing to tune. Recorded so it is not re-opened as a finding.

⚠️ **A NEW ATTEMPT IS STILL PERMITTED AND STILL WANTED.** After any exit before
`ORB_NO_ENTRY_AFTER_ET` (11:30), a closed bar back inside the range, a fresh
impulsive candle and a fresh retest construct a new order with new geometry.
Nothing caps ORB attempts; `_one_per_session_used` is wired to the runaway and
the butterfly only.

Pinned by `tests/check_orb_sequence.py`: 16 checks, **10 born red at f74818b**.
S8/S8b pass there by design — HEAD already sized entry-to-stop, and they exist
to keep it that way — so they are mutation-proven instead: restoring the frozen
field to the sizer turns both red.

---

## 28. r208 — THE BUTTERFLY: SEARCHED WINGS, A SURVIVABLE FLOOR, NO RELAXATION

Operator, 2026-09-01: *"from noon onwards, upon finding that we have a (strong)
pin, and it's reachable, we as early as feasible construct a narrow OTM debit
fly with the pin at the apex. The wings should be a 1-R or better (that's the
widest allowed) but prefer narrower if available."*

**The three conditions relaxation may never waive**, and they are now the only
gates: *is price pinning right now*, *can the pin even be reached*, *can the
floor clear the spread*. His framing: **"reachability and pin strength are
synonymous with 'possible'. If either is a 'no' it's much less possible."**

🔴 **R AND SURVIVABILITY PULL OPPOSITE WAYS, AND ONLY R WAS WIRED.**
`R = (width − debit)/debit` RISES as the wing narrows. Survivability FALLS,
because a fly's quote is **four leg-spreads wide** — `(la−lb) + (ua−ub) +
2·(ca−cb)` — while its debit shrinks. With only R in the code the selector
steered to the least survivable structure available and called it the best one.
On 2026-09-01 five flies fired at 12:00:00 with R 8.5 to 16.9 and three were
stopped out inside the same minute on floors of 4.3¢, 5.3¢ and 7.0¢. **META at
R 10.8 was not a fly that happened to be fragile; it was the most fragile
constructible fly, chosen because it was.**

**So the wing is SEARCHED and bracketed from both ends.** Candidates come from
the chain's own listed strikes — never a stride of `_chain_increment`'s median
gap, which on a mixed ladder would step past real wings (r198's C.29 in a new
costume). `R_FLOOR` caps the wide side, `stop_survivable` (r154) floors the
narrow side, the near wing may not cross spot, and among what survives the
**narrowest wins**. No qualifying wing is a definite answer and says which
bound refused it, with the best available R and stop-to-spread ratio recorded.

⚠️ **THE TWO BOUNDS TOGETHER REQUIRE `width ≥ 64 × leg-spread`** — 2¢ legs need
$1.28 of wing, 3¢ $1.92, a nickel $3.20. On a wide-spread symbol no fly will
ever qualify. That is the arithmetic of the two rules meeting, not a defect,
and it is filed as BFLY.9 to be settled from S3 chain data rather than argued.

⚠️ **`WING_EM_FRAC` IS DELETED, NOT RE-TUNED.** At 0.25 of the expected move it
was setting whether a survivable fly existed at all, and nobody ever fitted it.

⚠️ **RELAXED IS REMOVED FROM THIS STRATEGY ENTIRELY** — no widen, no window, no
`tag()`. The butterfly is ONE PER SESSION (r179), so relaxing a dial does not
collect a marginal trade, it **spends the day's only slot** on one; r196 made
that argument about the noon floor and it holds for every dial on a capped
strategy. `EM_MAX_FRAC`, `PIN_CONC_MIN` and `LATEST_ET` all move SELECTION →
FOUNDATIONAL, the last reversing r196. **The sweep's three dials are untouched
and deliberately still loose** — operator: *"the sweep is going to get tightened
later. Right now we're getting bad TRADES and that's to collect some
parameters."*

⚠️ **CHARM NEEDS NO BUILD.** `derived/snapshot.py` already writes it onto the
fire snapshot and that runs on every fill (r144), so *"what was charm doing for
our winners and losers"* is a join whenever it is wanted (BFLY.10).

Pinned by `tests/check_butterfly_foundational.py` (11 checks, 8 born red at
f74818b) plus re-derived `check_butterfly_legs` v2.2, `check_butterfly_wing_grid`
v1.1 and `check_plan_prepares` v1.5 — each born red 2 at HEAD.

---

## 29. OTV4TEST r2 — THE ORB SPEC AND ITS PLAN CONTRACT (agreed with the operator 2026-09-08, part by part)

**REMOVED, OTV5 r76 (RETIRE.1), 2026-11-08** — the trade and its plan are deleted from the code; this section's contract is history (see git history before r76).

## 30. OTV4TEST r3 — THE RUNAWAY SPEC AND ITS PLAN CONTRACT (agreed with the operator 2026-09-08)

Intent, his words: *"catch an early high velocity move from the market open where there's a lot of participation and a lot of volume and we just wanna participate in it and when it fizzles out … we want out of it."* Starting at the 50.

### 30.1 The rejection fact — one primitive, four consumers

Before r3 the only thing that could see a wick through a pool was the sweep strategy's private rule; `derived/levels.py` read the 5m close and never a high or a low. Now the level engine, on every CLOSED 1m bar, for every live support/resistance level:

| event | rule |
|---|---|
| WICKED | a wick through the level with the close inside. Depth: **shallow** ≤ 0.25% of price (the sweep's strict ceiling), **deep** ≤ 0.75% (the relaxed ceiling, 3×), **beyond** deeper — the level is being taken, not swept; recorded, never rejected |
| REJECTED | closes back inside reach the doctrine's count — **one on a shallow pierce, two on a deep one** (the wicking bar's own close counts). A close beyond in between clears it |
| ACCEPTED | two closes beyond (measured, r63) — the level retires |

Written to `level_event` (never purged), read by `DerivedStore.latest_rejection()`. Consumers: the runaway (exit → handoff), the ORB (exit → handoff, §29 amendment), the sweep (trigger, next spec), the condor (pairing, after that). Nobody re-detects it.

### 30.2 The spec

| part | definition |
|---|---|
| setup | the ORB's range and impulsive candle; the third consequence — the 50 reached with no retest |
| **arm** | the 50% level **ACCEPTED**: a 1m close beyond it, held at the next close. The engine's own latch (`fifty_accepted`), which is now also what invalidates the ORB (orb_engine v4.13). A wick to the 50 arms nothing, ends nothing |
| direction | the break's |
| window | 09:35–11:30, no relaxed extension; outside it the plan observes and does not write |
| feasibility | the ATR floor (0.08%, veto 0.05%) — kept by ruling |
| limits | **one per break, any exit**, keyed (direction, boundary). The r179 session cap is retired: a new break is a new trade. **Re-validation on actual:** after any exit the standing state never re-fires; the break trades again only when the 50 was LOST on a close and then ACCEPTED again |

### 30.3 What the plan provides — before the accepting close

- **strength, measured once at acceptance and frozen** — the move from the boundary to the 50 is a complete sample. `analysis/trend_strength.measure()` over the bars since the impulsive candle: **pace** (displacement per bar against true range) and **acceptance** (where the closes sat in their bars). **Participation** (aggressor share from the prints) is not yet wired — recorded None, RUN.6. Composite = mean of what is available. A **dial**, never a gate.
- **band from strength** — grind (< 0.40) 0.5× the run, normal 1.0×, rip (≥ 0.70) 1.5×. `gamma_leverage_pick` runs unchanged inside the band; the teenie gate still bounds the cheap end. **Category 1 prior** — a baseline, unfitted, recorded on every row and fire.
- the contract, premium, floor premium (recorded), R (muteable through 09-11), the 50 level (the thesis) and the boundary (the backstop), both on the signal.

### 30.4 Exits — the negation of the entry, in order

1. 15:45 hard close
2. **REJECTED handoff** — a pool on the trade's side rejected on a close → "sweep owns it"
3. **thesis dead** — a 1m close back through the 50
4. **fizzle** — the entry's evidence decaying on the bars since entry. EVENTS (no threshold): higher-low broken (short: lower-high), VWAP recrossed (when the frame carries volume). DIALS (self-referenced): acceptance decaying (`acc_delta` < 0 with `acc_recent` < 0.5), range contracting (< 0.5× the first bars), premium diverging (a new underlying extreme without a new premium high). **Exit on two events, or one event plus one dial.** Every read lands on the record.
5. trail (unchanged)
6. theta bleed (kept)
7. **structure backstop** — a 1m close through the ORB boundary itself
- **No premium stop.** *"If we're going to immediately open another momentum trade the second the preceding one stops out, then why not just HOLD?"* What a 20% floor would have done is recorded (`would_have_floored`) — a question for the first sessions, not a bar. Velocity stall is off the runaway too (ORB.3 closed).

### 30.5 The interaction, named

The momentum exit and the sweep entry are the same event seen from two sides. The loop runs exits before the entry attempt within one tick, so in paper the handoff is same-tick; live it is bounded by the close fill. The sweep's afternoon-only gate is a clock standing in for this handoff; it stays until the handoff has fired on real tape.

**As built (OTV4TEST r3):** `derived/levels.py` v4.1 (the emitter), `data/derived_store.py` v4.2 (`level_event`, `latest_rejection`), `strategy/runaway_plan.py` v1.0, `strategy/runaway_continuation.py` v5.0, `execution/exit_engine.py` v4.12, `analysis/orb_engine.py` v4.13, `database/trade_logger.py` v4.12, `main.py` v4.41. Hypotheticals: `tests/check_level_rejection.py`, `tests/check_runaway_plan.py`.

## 31. OTV4TEST r5 — THE SWEEP CREDIT SPREAD SPEC AND ITS PLAN CONTRACT (agreed with the operator 2026-09-08/09)

**REMOVED, OTV5 r76 (RETIRE.1), 2026-11-08** — the trade and its plan are deleted from the code; this section's contract is history (see git history before r76).

## 32. OTV4TEST r6 — THE GEX PIN BUTTERFLY SPEC AND ITS PLAN CONTRACT (agreed with the operator 2026-09-09)

*"Only the pin strength, during GEX pinning behavior and pin is reachable, with economic performance planned to best available payoff asymmetry, earliest possible no less than 1-R, taken as a debit. EM at 1.0 firm, no relaxed conditions."*

### 32.1 The spec
| part | definition |
|---|---|
| anchor | the pin, only — no level, no tine strengthens it |
| regime | PINNING |
| reachable | pin at 0.30–1.00 of the expected move, FIRM — no relaxed dial anywhere in this trade (confirmed by reading: none was live after r321) |
| pin strength | concentration ≥ 0.25, firm |
| **persistence, smoothed** | the acting pin is the MODE of the last `SMOOTH_WINDOW` (12) instant pins — chatter between adjacent strikes does not move it, a migration does — and it must have held `PERSIST_TICKS` (8). Both are declared priors, recorded every tick (`pin_raw`, `pin_persist_ticks`) |
| structure | every listed wing width priced per side; **the pick is the MAX R** (payoff ÷ debit) among those that clear R_FLOOR (≥ 1R) and the stop-vs-spread floor. "Narrowest first" is superseded |
| fire | the earliest tick the best structure clears 1R; a debit; the whole position through the §6 ladder walk |
| one per session | main.py's r179 DB-backed cap; no additional attempts. One structure per pin (PLAYED_PINS) stays underneath it |

### 32.2 Starved inputs — the park as a state, not a flag
No ATM IV · no chain · **open interest summing to zero across the chain** → `NO PLAN: starved open_interest`. GEX without OI is gamma² × spot and the pin sits at spot; that was the reason for the 08-19 park. The row now states it every tick, and the trade un-parks itself the day real OI arrives — which it did: 2026-09-09, 226 non-zero strikes by 15:43, once `data/open_interest.py` stopped losing the first batch of every cycle to a closed event loop (v4.2).

### 32.2b The slot — permitted, not expected
The butterfly is opportunistic like the condor: it is neither blocked by any open position nor blocks one (r161 asks it from the position-open branch; r197 stops `has_blocking_position()` counting it). A box may hold a butterfly plus one other thing.

### 32.3 Exits — hold to the close, by ruling (OTV5 r73, BFLY.17)
**No stop of any kind.** The operator, 2026-11-03: *"For the GEX fly, I want no stop except hold to close, I want the VIX rule enforced & I want more discriminatory entries."* `config.HOLD_TO_CLOSE_STRATEGIES = ("GEXPinButterfly",)`: exit_engine skips the fly's hard stop and never asks the decay read; its one exit is the 15:45 flatten (the 15:55 resting close untouched). No target: a pinned fly pays as the wings die into the close. (Before r73 the fly carried a 15% dead-thesis stop, 40% before that.)
**The door, since r73:** `vix` — VIX below `VIX_BUTTERFLY_DISABLE` (20); at or above, no fly (half size at 15-20 is unchanged); `open_in_prior_range` — today's 09:30 1m open inside yesterday's RTH high-low; and the wing search takes the best R only among widths whose debit is at least `BUTTERFLY_MIN_DEBIT_PCT_WIDTH` (15.5%) of the width. Both entry cuts were chosen after looking (~/gex_study) and are forward-scored from 2026-11-09.

### 32.4 Recorded, not barred
Three-leg stop-vs-spread ratio (`stop_vs_spread`, already a floor via `STOP_VS_SPREAD_MIN`), pin distance in EM at the fire, persistence in ticks. The first real pins say what the priors should be.

**As built (OTV4TEST r6):** `strategy/gex_pin_butterfly.py` v5.0 (the plan lives in its `prepare()`, as the engine does for the ORB — the split into a `butterfly_plan.py` is a later tidy, not a behaviour), `data/open_interest.py` v4.2, `strategy/plan.py` (HYG.4), `devtools.sh` v2.1. Hypotheticals: `check_plan_prepares` B1–B14 (B12 on the smoothed pin, B14 the persistence bar), `check_butterfly_foundational`, `check_butterfly_legs`, `check_butterfly_wing_grid`.

## 33. OTV4TEST r7 — THE JOURNAL: RECORDED WHOLE, READ HUSHED (operator 2026-09-09)

*"The bot should see everything. Just don't show it to me on the products I actively use."* The plan_tick record is unchanged — a plan outside its window still writes its dormant transition row and the GATES reporter its edge line, so the corpus says when each window opened and closed. The READERS hush: `query.py` DECISIONS lists dormant strategies (and the management plans' "nothing to manage") as one line of names; the devtools PLAN ROWS and PLAN BOARD sensors exclude DORMANT rows unless asked. The verdict vocabulary stays (NO PLAN = none available; DECLINE = rejected for a named bar; HOLD-prepared / TAKE = plan accepted) — it does the same work as the operator's words.

**§33 addendum (r8):** NOT ASKED joins the hushed line. The one case the operator wants to see — a vertical is open and the condor plan is looking for its complement — is a HOLD/PREPARED row from CondorManagement, never a NOT ASKED. And "NO PLAN during the TCS window" was not the market: r238's `prepare()` returned with the tick open on its common path; `trend_credit_spread` v4.13 gives every path a terminal (`check_tcs_narrates`). If a NO PLAN / NOT ASKED ever shows for an in-window strategy again, that IS a wiring defect — treat it as one.

## 34. OTV4TEST r9 — THE TREND CREDIT SPREAD SPEC AND ITS PLAN CONTRACT (agreed with the operator 2026-09-09)

**REMOVED, OTV5 r88 (RETIRE.3), 2026-11-08** — the trade, its plan and its log-only shadow (r57) are deleted from the code (the operator, 2026-11-08: "Delete"); this section's contract is history (see git history before r88).

## 35. OTV4TEST r10 — THE CONDOR MANAGEMENT PLAN (agreed with the operator 2026-09-09)

*"Permissive, opportunistic and resilient — with a final trick if more mundane defense (roll for a free leg) isn't possible: go inverted and buy a hedge leg on the other side."* **It is a management plan, not a strategy.** A condor is never entered; it FORMS when a second credit vertical pairs with the first — sweep–sweep or TCS–sweep, the complement always a sweep on the other side (TCS may be leg one, never leg two). The fork-anchored condor entry (`IronCondorStrategy` as a strategy) is retired; the 1h fork stays a legitimate level through the tines in the store, which the sweep reads.

### 35.1 States and rows
| state | the row says |
|---|---|
| nothing open | hushed |
| one credit vertical open | *"lone call vertical — managed on its 15% stop; waiting on: a sweep REJECTED below — london 713.50: would sell 713/712P for 0.19 (R 0.23)"* — the complement read from the sweep plan's last preparation on the authorized side |
| two verticals paired | the ladder, every rung disposed every tick: tested? rolled? breached? roll searched / best candidate / why not; invert available / not; tent priced / affordable / not |

### 35.2 Tested, breached, accepted — fact events, not distances
A side is **tested** when the closed 1m bar's wick reached its short strike with the close still inside (wicks are tests); **breached** when a 1m close lands beyond it; **accepted** on the second close. The roll runs on tested; the tent on breached; nothing on a wick alone. The old one-strike proximity rule survives only when no tape is passed.

### 35.3 The ladder — TWO rungs (v2, operator 2026-09-09, superseding r10's four)
The operator's own picture: **360/370C breached, price at 364 → take the profitable put vertical off and SELL 360/337.5P** — the short at the tested short's own strike, the wing widened until the credit clears the tested width. Any further upside cannot lose; the downside taken on is capped by the new wing. That is rung 1 at its limit, not a separate mechanism.

1. **Roll to risk-free.** The untested side is re-sold nearer — up to and including the tested short's own strike (shared body, an iron butterfly) — with **the wing widened only as far as the credit needs**: `total_credit ≥ tested_width`. Nearest short, narrowest wing that clears — least new risk. **No cap on the widening:** the 15%-from-formation floor is the protection. **Prepared every tick** while a condor is on: *"if the call side were tested now: roll put to 360/330 for +5.75, cumulative 10.03 vs width 10 — RISK-FREE."* The test fires a roll that was already priced.
2. **Stop and page** — no strike combination clears. *"Unless no available strikes will make us whole again."*

**Retired:** the adjacent-shorts "invert" rung (it *is* rung 1 at its limit) and the opposite-type-long "tent" — one situation, one mechanism.

### 35.4 Final form, the floor, and the whipsaw
After the roll the structure is **final form** and the only exit is a **15% loss from the structure as formed** — the cost to close both verticals at formation, grown 15% — evaluated on the **group**, both legs together, both leave together (`final_form_floor`). Cumulative credit stays on the record as the account of what was collected. Nickel and 15:45 stand. *"We're out at 15% of our present positive P&L unless no available strikes will make us whole again."*

**Whipsaw:** if the *rolled* side is the one tested next, no further roll exists — the other side is already at the body and cannot add credit. The row names it (*"WHIPSAW: the rolled put side is now tested; no further roll exists; the floor governs"*) and shows the cost to close against the floor every tick, so the exit is never a surprise.

### 35.5 The complement is rich or it is not taken
As a condor's second leg the sweep must be **at least as rich (credit ÷ width) as leg one** — a comparison, not an invented number — or it is REJECTED by name (`complement_richness`). Leg one is either fine or stopped; nothing else about it enters the authorization.

**As built (OTV4TEST r10 + r11):** `strategy/condor_roll.py` v4.8, `strategy/iron_condor_strategy.py` v4.11, `strategy/sweep_plan.py` v1.2, `strategy/sweep_credit_spread.py` v6.1, `execution/exit_engine.py` v4.16, `database/trade_logger.py` v4.14, `main.py` v4.45. Hypotheticals: `check_condor_mgmt` C1–C7, R1–R6.

## 36. OTV4TEST r12 — ANCHORS: RECORDED, NEVER DECIDED ON (operator 2026-09-09)

*"Record in our newly crafted plans, not to decide, but to see if they offer fitting anchors we can tie to later."* `derived/anchors.py` reads the stores that already exist — surface (charm, vanna, GEX per strike), indicators (VWAP), forks (direction), levels (the 1h tines), the prints (aggressor share of size at a level), the chain in hand (OI) — and every plan stamps 3–5 of them on its row as record-only checks (`anchor_*`, verdict None). Scored later against fires, DECLINEs and HOLDs alike; `fire_snapshot` alone could only ever see the fires. A None is a coverage fact, never a failure; nothing here reaches a refuse, a hold or an unmet (`check_anchors` A5).

| plan | anchors | the question they will answer |
|---|---|---|
| ORB | VWAP distance, aggressor share at the boundary, nearest 1h tine to the 100% target, 15m fork | does a target under a tine get reached; does the boundary's tape lean the break's way |
| runaway | **participation** (aggressor share at the boundary — RUN.6, read now, recorded only), charm and vanna at the target strike, 15m fork, VWAP distance | do runs into positive charm fizzle earlier |
| sweep | GEX at the rejected level, OI at the short, aggressor share at the level, charm at the short, nearest tine | is the pool a gamma wall; who traded the rejection; does charm's sign into the close agree with "holds to the close" |
| TCS | vanna at the accepted extreme, charm at the short, aggressor share through the extreme, 15m fork | |
| butterfly | GEX at the pin, VWAP distance to the pin, OI at the pin | |
| condor | GEX between the shorts, VWAP distance | pinning support for "stays between" |

## 37. OTV4TEST r12 — THE LIQUIDITY HUNT AND THE HANDOFF GRANT (operator 2026-09-10)

**r76 (RETIRE.1):** the HANDOFF GRANT below is removed - its only taker, the sweep credit spread, is removed. The Hunt's `hunt_target_wicked` exit is unchanged; its reason no longer says "handoff granted to the sweep".

From the predecessor's own ledger: the ORB break-and-retest risks $71 to make $37; the momentum trade pays ~2:1 with the least give-back over ~300 trades. *"Under most circumstances price is going to go towards where the liquidity is."* So the hunt trades the break TOWARD the nearest liquidity level instead of waiting for a retest — and runs **beside** the ORB, never in its slot, so the two are compared on the same range, the same levels, the same fills.

### 37.1 The spec
| part | definition |
|---|---|
| bias | at 09:35, the nearest live named level OUTSIDE the range — measured from the range edge — above vs below. The nearer side is the market's intent. *"Some of the earliest moves of the session are fake-outs and do not represent the intent."* |
| A1 | a 1m close outside the range on the bias side → long/short toward the level |
| A2 | a far-side break that closes back INSIDE the range → entered on that close, from the far boundary, direction = bias. *"Taking out a previous session high from the lower bound of the opening range."* The whole range is runway |
| not traded | a far-side break that does not fail — recorded as "broke away from the liquidity" |
| target | the level. Runway known at entry → the strike is the gamma pick over that runway (the runaway's search with `run` = distance to the level), teenie gate |
| exits | the target WICKED with the close short of it → off, **handoff granted to the sweep** · the target ACCEPTED → over-delivered, hold on the runaway's exits · thesis dead = a close back through the ENTRY boundary (A1: the range edge; A2: the far boundary) · fizzle · 15:45 · no premium stop |
| limits | one hunt per break key; morning 09:35–11:30; env sizing |
| slot | exempt on entry and not counted as blocking (the butterfly's rule) — an ORB and a hunt may both be long the same break |

### 37.2 The handoff grant (`execution/handoff.py`)
The slot rule is binary; instead of more exceptions the handing-off strategy writes an explicit token — *from LiquidityHunt, to SweepCreditSpread, at level L, side S, good for N ticks* (`HANDOFF_TTL_TICKS` = 8, a prior). The sweep's entry consults it: with a live grant naming it the slot yields — an open ORB does not block — and every other bar the sweep has still applies. Grants expire on their own; **an expired grant is a finding.** The sweep's fill carries the grant it fired on.

### 37.3 What the week answers
Per box per morning: was the bias right (reached the level / didn't), which entry paid (A1 vs A2), how many hunts handed off and what the sweep did with the grant. The ORB beside it is the control. Read in R and reached-the-level counts first; the sweep P&L after granted handoffs will need more than a week.

**As built (OTV4TEST r12):** `strategy/liquidity_hunt.py` v1.0, `execution/handoff.py` v1.0, `execution/position_manager.py` v4.9, `execution/entry_engine.py` v4.9, `execution/exit_engine.py` v4.17, `main.py` v4.46. Hypotheticals: `check_liquidity_hunt` H1–H10.

## 38. OTV4TEST r15 — THE LEVEL BOARD, AND THE TWO DEFECTS UNDER IT (from the OTV4 thread, 2026-09-12, mainline r364)

Found on mainline's warehouse and verified here by reading: **(1) pools were written with the detector's word** — `high`/`low` — and `live_levels()` filters `support`/`resistance`, so PDH, PDL and the whole R1/R2/R3 ladder were invisible to the hunt, the sweep and the TCS; **(2) a tine row went stale the moment a fork died** — nothing retired a level that stopped being sourced. Both fixed in mainline r364's shape so otv5 gets one implementation:

- **a pool is classified by side at write** — above the live price is resistance, below is support; with no price, the formation. The biography still retires it (ACCEPTED_THROUGH, TRAVERSED).
- **a tine is never stored.** `tines_now(price)` computes the rails from the fork the ForkEngine holds *right now* — with a rate, `bars_to_contact`, None when diverging — and a failed build clears the held fork, so a dead structure yields nothing on the next read. *"As long as there's a fork present, there should be a map of its points. And if the fork stops emitting, then the map has to go with it."* The fork's emitter reads the rails beside the ledger's levels and drops their pierce state when the fork goes.
- **`board(price, orb_high, orb_low, limit=3)`** — the levels beyond the opening range, up to three each side ordered outward (monotone by construction), the rails, four distinct empty answers (`no_store`, `no_range`, no fork, no level that side), `count` never padded. The hunt reads it for its bias; the sweep reads the rails through it. VWAP is not a level a trade contends with.

**What this changes on the tape:** from r15 the hunt and the sweep can see the ladder. Every row before r15 that said *"NO live level outside the range"* or chose a generic zone level was reading a door the ladder could not pass. HUNT.1's first week starts here, not at r12.

**Predecessor status (correction to the manifest):** mainline is no longer frozen — 37 commits, r325→r364, under Claude Code on the controller. The back-port is a merge now, and the level engine is the first file where both sides changed the same thing on purpose.

## 39. OTV4TEST r26 — THE ATP (AT-THE-PIN) BUTTERFLY SPEC AND ITS PLAN CONTRACT (operator 2026-09-13)

**REMOVED, OTV5 r76 (RETIRE.1), 2026-11-08** — the trade and its plan are deleted from the code; this section's contract is history (see git history before r76).

## 40. OTV4TEST r29 — THE LEVELS ARE BUILT FROM THE TAPE (operator 2026-09-14)

*"Levels are session extremes that held. Starting from spot, map the most recent up/down levels going backwards in time and further up/down from the recent ones. A level is spent if it didn't hold & price accepted through it."* And: *"Straight from the tape I want you to properly construct the levels."* On prints: *"The highest high of the session that held, or the lowest low."*

These restate rulings already on record, and the build implements those, not a new reading: §31.1 here (*"Age does not matter. A previously held extreme is enough"*; spent = the breach accepted) and mainline §38 / LVL.3 / LVL.17 (one board every plan parses; newest first, each rung further out; *"we go back as far as we go and we map the levels with what we have"*; nothing in memory; tines never stored; history seeds durability, never an event).

### 40.1 The definition, as values
| part | definition |
|---|---|
| a level | the high or the low of a CLOSED session — Asia 00–08 UTC, London 08–13 UTC, NY = RTH at hour granularity by the ET date — the mapper's own clock, imported (`derived/level_map.closed_sections`) |
| the tape | the feed store's 1m bars, `SYM` and `SYM_EXT` merged on the stamp (identical on overlap, measured) |
| provable | a section the tape does not fully cover is not a level (mapper A2.1) |
| a print | no filter, by ruling — the session's highest high / lowest low, whatever printed it |
| held / spent | spent at the bar that completes `LEVEL_ACCEPT_CLOSES` (2) consecutive closed 1m closes beyond it, past the engine's 0.15% close tolerance, after the bar it formed on. A wick does not spend it |
| the map | `level_map.walk(held, spot)`: the newest held level each side of spot, then each older one only if further out; equal formation times go nearest first. A view, computed at read |
| who reads it | the hunt's `board()` (then beyond each opening-range edge), `walk()` (the snapshot/notes record), and the sweep plan's levels in play. The TCS reads its `ny` levels unwalked (TCS.3) |
| stored | `level_ledger` holds the biography: `created_ts` = the bar the extreme printed on, `timeframe` = `session:YYYY-MM-DD`, provenance `asia`/`london`/`ny`, kind by formation (high → resistance) |
| retired | every closed tape bar the ledger is reconciled: a live row that is not a held tape level and not formed before the tape begins retires `ACCEPTED_THROUGH` (at the tape's bar) or `NOT_A_LEVEL`; every VWAP id but the current one retires `STALE_VWAP` (r30). A kept row is stamped with its formation bar AND its `session:YYYY-MM-DD` timeframe (r30), which is what lets it stay once the tape no longer reaches it. An `ACCEPTED` event is written only when that bar is fresh — history never fires a trade. `TRAVERSED` inside the opening range is unchanged (§31.1) |
| reach | the ledger (NEVER_PURGE) beyond the tape: a `session:` row formed before the tape's first bar is kept and still judged on live closes |

### 40.2 Measured on this box, 2026-09-14
At 09:10 ET 619 of 624 ledger rows were live, back to 09-08: three `fork1h/*` rails frozen at Wednesday's prices, 52 pre-r19 tine rows, and the mapper's `(R1)`/`(R2)` pools beside the same prices under bare session names. On the tape at 09:46 (spot 705.33) nine levels held and the walk read up **715.42** (London 09-14 — a single 08:26 print on 885 contracts, kept by ruling), **717.68** (NY 09-11), **719.70** (NY 09-09), **720.06** (London 09-09); down **701.16** (London 09-14). Every older low had been accepted through.

**As built (OTV4TEST r29):** `derived/level_map.py` v1.0, `derived/levels.py` v5.0, `data/derived_store.py` v4.5, `strategy/sweep_plan.py` v1.5, `main.py` v4.50. Hypotheticals: `check_level_map` M0–M9 on the box's own tape. **Not in this revision:** the S3 seed (SEED.1, awaiting read access) and moving `check_level_rejection`'s fixtures onto a tape (LVL.10).

## 41. OTV4TEST r203/r204 — ORCS, THE OPENING RANGE CREDIT SPREAD: SPEC, TRIGGER COMPONENTS, PRELIMINARY DIALS (operator 2026-10-03)

**REMOVED, OTV5 r76 (RETIRE.1), 2026-11-08** — the trade and its plan are deleted from the code; this section's contract is history (see git history before r76).

## 42. OTV4TEST r303 — PLAN STATES: ACTIVE, LOG ONLY, DORMANT; HOUR- OR CONDITION-GATED (operator 2026-10-19)
The operator, 2026-10-19 08:34 ET: "Going forward, I want all the trades that are turned off to stop writing to the plan
Log"; 08:43 ET: "The intent is dormant plans should not write to the ledger, unless we are studying them as 'log only' - I
would like each plan to have 3 states: active, dormant or log only, they can be further categorized as hour-gated or
conditional gated"; 08:45 ET: "That looks right to me".
- **One authority:** `strategy/plan_state.py` TABLE - per plan its switch, default state and category. `state(name)` is
  read at call time; the config flags still decide ACTIVE for the switches config reads.
- **ACTIVE:** as before. **LOG:** the plan is observed every tick it is asked (`strategy/observe.is_active`): `take()`
  writes LOG-ONLY and opens no plan_ledger row; `main._log_only` refuses the signal at `_fire`, the hunt, 
  `_execute_entry_signal` and (new) `_execute_condor_leg`. **DORMANT:** `main._safe_strategy` never asks it; `write_row`,
  `close_tick`, `_write_heartbeats`, `board_line` and `PlanLedger.open_plan` write nothing for it.
- **Categories:** HOUR (asked only in its `config.ENTRY_WINDOWS` slot) or CONDITION (the `/manage` plans, CondorManagement
  and CreditRoll, the condor). CondorManagement and CreditRoll are on the `[plans]` line only while their "legs" check
  reads one or more. A CONDITION-gated plan writes nothing while its condition is absent (09:54 ET: "Yes"): not run this
  tick = no INACTIVE row, no dispatch-gap default, no heartbeat; a condor plan's legs < 1 HOLD is not written. NO PLAN
  (asked and silent) still reports. The plans panel reads such a plan's old heartbeat as IDLE unless trades.db holds an
  open position it manages.
- **Explained silence:** the start logs `[plans] states — active: ... · log: ... · dormant: ...` and writes
  `data/plan_states.json`; `query.py`'s plans panel lists DORMANT and LOG ONLY plans from it instead of STALE / NOT RUNNING.
- **Gate:** `tests/check_plan_states.py` (S1-S3 states, D1-D10 driven on scratch stores; every check but the D5 control RED on f07f7a4).

---

## 43. OTV4TEST r316 — THE RE-FIRE IS A RETURN TO THE RANGE; A LOSING BREAKOUT CLOSES ITS SIDE TO THE HUNT (operator 2026-10-24)

**The rulings, verbatim.** 13:45 ET: *"The new session high/low rule needs to be dropped. You established that the move
was mostly done if we waited for a new extreme. The 20 second rule also was proven unnecessary after today's reentry
study. Question: since 'breakout' is a breakout of the 5 minute orb, we should only have 1 per day, unless it reenters
the range, right? So the only other 'same side' entries should be runaway (which should not be blocked) and liquidity
hunt, which I agree should not fire on a failed breakout attempt. So my proposal: on a losing breakout trade, forbid a
liquidity hunt on the same side for the day."* 13:56 ET: *"1. For now, rearm it on every reentry. 2. No more 20 second
blocks—it's arbitrary & conflicts with today's studies. 3. Yes, if a breakout on one side fails, don't allow a hunt to
fire on that side for the rest of the day. 4. That is correct. Yes, effective Monday"*.

**43.1 Breakout — `fresh_break` replaces `new_extreme` (FOUNDATIONAL).** The break trigger is a state (the last closed
1m bar beyond the edge), so the side needs a latch. It fires only when the signal bar is the FIRST close beyond the edge
since 09:35 or since the side's latest close back inside (strictly: a close AT the edge is inside). Every return re-arms
it. A break the gates refused spends the break until a close back inside, which keeps r282's lesson without the
session extreme. r142 stays: a bar that started before the side's latest entry already fired it. Facts are read from
trades.db and the feed store; unreadable is a refusal. `OT_BRK_REFIRE=extreme` restores r131/r282 unchanged.
BRK.12's record-only re-arm row is superseded while `rearm` decides (the Service line reads `rearm=brk:superseded`).

**43.2 Liquidity Hunt — no Hunt on a side after a losing Breakout on that side, for the day.** "Fails" is a Breakout
on that side that CLOSED today with pnl_usd < 0 (an open loser has not failed yet). The Hunt HOLDS, named HUNT.13;
an unreadable book holds. `OT_HUNT_AFTER_BRK` trade|log|off (unset = trade).

**43.3 There is no re-entry time gate (CD.1).** The 20 s gate (r306/r316) is scrapped, not logged: the operator,
2026-10-24, "The 20 seconds is arbitrary, just like 45 seconds, or 145 seconds. It has zero value. Scrap it."
`OT_REENTRY_GATE` is not read.

**43.4 Runaway.** Nothing blocks a Runaway because of another strategy's same-side entry (r306 was the only rule that
did). Its own limits (one per break, any exit; r179/r281) are unchanged.

**43.5 Counterfactuals (the operator, 2026-10-10: the evidence of what would have happened had we NOT made the
adjustment).** data/counterfactual/breakout_refire.jsonl (every signal bar where the two re-fire rules disagree, both
verdicts, which decided, whether it fired), hunt_after_breakout.jsonl (every held or would-be-held Hunt with the losing
Breakout). Scored on Saturdays. (reentry_gate.jsonl is no longer written: 43.3.)
