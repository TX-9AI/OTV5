# TRADES — the specs

**`TRADES.md` v5.5 · 2026-10-31 · OTV5 r67 (PARC.4) — PARC is REMOVED: its roster row and section 10 are gone with its code. The operator: "On PARC, no. It was an idea. It failed. It's done." and "Yes" to removing its code.**

**`TRADES.md` v5.4 · 2026-10-30 · OTV5 r60 (PARK.4) — PARK is bought AT THE MARK, not the ask: paper books the mark, live ladders in from the bid to the mark and never posts above it, sized on the mark. The operator: "That's not my spec… you know park is a borrowed trade. To match my spec, we ladder in from aggressive to mark & never worse than mark".**

**`TRADES.md` v5.3 · 2026-10-30 · OTV5 r57 (TCS.LOG1) — TCS is reactivated as LOG ONLY: OT_TCS_ACTIVE unset = a SHADOW trade (the real entry and exits at the paper fill, booked to shadow_trades.db, never ordered). The operator: "Can you reactivate TCS Monday as 'log only'? But do not trade it." then "Make sure TCS logs everything an executable trade logs."**

**`TRADES.md` v5.2 · 2026-10-28 · OTV5 r50 (PARC.3) — PARC is PAUSED: OT_PARC unset = log (records, never orders) until a better stop placement. The operator: "Don't go live on the PARC tomorrow until we find a better stop placement."**

**`TRADES.md` v5.1 · 2026-10-27 · OTV5 r46 (PARC.1) — PARC: its roster row and section 10. The operator: "Call it PARC"; "No shadow mode. We're paper. It trades tomorrow."**

**`TRADES.md` v5.0 · 2026-10-25 · OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...**

**Every strategy: what it trades, what may be relaxed, and what may never be.**
**Written 2026-08-20. This is the operator-facing document; the code is the
authority and `tests/check_gates.py` enforces the categories mechanically.**

---

## 0. AS RUNNING — the roster, the windows, the close (OTV4TEST r226, 2026-10-03)

**This section is the current state and governs wherever a section below disagrees.**
`tests/check_docs_roster.py` reads this table and fails the sweep if a window, a default
or a number here stops matching `config.py`. Sections 1-6 below are the 2026-08-20 specs:
the reasoning stands, several numbers and the windows do not. Each trade's full contract
is its `docs/PLAN_SPEC.md` section.

| trade | key | default | switch | entries (ET) | spec |
|---|---|---|---|---|---|
| Runaway | `RunawayContinuation` | ON | none (`OT_RUNAWAY_END` moves its end) | 09:35-10:30 | PLAN_SPEC §30 |
| Breakout | `Breakout` | ON | none (`OT_BREAKOUT_END` moves its end) | 09:35-10:30 | section 7 below |
| Liquidity hunt | `LiquidityHunt` | ON | none | 09:35-10:30 | PLAN_SPEC §37 |
| ORCS | `OpeningRangeCreditSpread` | OFF | `OT_ORCS` | 09:45-10:30 | PLAN_SPEC §41 |
| GEX pin butterfly | `GEXPinButterfly` | ON | `OT_GEX_BUTTERFLY` | 13:00-15:00 | PLAN_SPEC §32 |
| ATP butterfly | `ATPButterfly` | OFF | `OT_ATP_BUTTERFLY` | 13:00-15:00 | PLAN_SPEC §39 |
| VOLT | `VOLT` | OFF | `OT_VOLT` | 09:35-10:30 | section 8 below |
| ORB break + retest | `ORBStrategy` | OFF | `OT_ORB_TRADE` | 09:35-15:40 | PLAN_SPEC §29 |
| Sweep credit spread | `SweepCreditSpread` | OFF | `OT_SWEEP_CS` | 09:35-15:40 | PLAN_SPEC §31 |
| Trend credit spread | `TrendCreditSpread` | OFF | `OT_TCS_ACTIVE` | 11:31-15:40 | PLAN_SPEC §34; LOG since r57: unset = `log`, a SHADOW trade (execution/shadow_book.py, never ordered); `1` trades it, `0` stops it; configure.sh item 16 |
| PARK | `PARK` | ON | none (`OT_PARK=log` records it, `off` stops it) | 11:01-11:03 | section 9 below |

A window's end is exclusive: 10:30 means the last entry is 10:29. A switch is ACTIVE at
`1` or `active` (r303 below). ORCS is RETIRED (r249, the operator 2026-10-04: "Retire it on this repo"; PLAN_SPEC §41.13) - OT_ORCS=1 restores it, PAPER ONLY (a live box refuses it); since r303 its plan is DORMANT with it and records nothing (the operator, 2026-10-19: "1. Yes"). The ORB trade is retired but
the opening-range ENGINE is not: Runaway, Breakout and the Hunt read it, and since r222 its
range is checked against the official print. The condor is a management plan with no entry
of its own; with both credit entries retired it has nothing to manage.

**Plan states (r303, PSTATE.1; `strategy/plan_state.py`).** Every plan is ACTIVE (evaluated, written, trades), LOG
(evaluated and written, every fire recorded LOG-ONLY and never executed) or DORMANT (never asked, writes nothing: no
plan_tick / plan_check / plan_ledger / plan_heartbeat row, not on the `[plans]` line). The operator, 2026-10-19: "dormant
plans should not write to the ledger, unless we are studying them as 'log only' - I would like each plan to have 3 states".
Each switch takes `active` | `log` | `off` (`1` still = active; for an OFF-by-default trade anything else stays dormant;
a value nobody recognises keeps the default and is named at start). Runaway, Breakout and the Hunt gained switches
(`OT_RUNAWAY`, `OT_BREAKOUT`, `OT_HUNT`, unset = active); PARK keeps `OT_PARK` trade/log/off. Unset, every plan is in
the state the table above shows: no decision changed. Each plan is also HOUR-gated (asked only in its window - every
row above) or CONDITION-gated (the management plans, while their own position is open; CondorManagement and
CreditRoll, while a credit position is open, and off the `[plans]` line otherwise; the condor, which has no entry). A
condition-gated plan writes NOTHING while its condition is absent - no "nothing to manage" row, no heartbeat - and writes
the moment a position of its own is open (the operator, 2026-10-19 09:54 ET: "Yes"). The
start logs one `[plans] states` line and writes `data/plan_states.json`, which the devtools plans panel reads.

**The close (`config.EOD_SCHEDULE`).** No new entry at or after **15:40**. Anything with
a short leg rests a best-case close from **15:45**. Everything else walks the mark ladder
from **15:50**. Whatever is still open CROSSES at **15:55** (r149 - this supersedes "nothing
ever crosses" and the "15:45 hard close" wherever they appear below).
On a listed EARLY CLOSE (13:00: 11-27, 12-24, ...; `utils/market_calendar.EARLY_CLOSES`) every one of these moves
three hours earlier and nothing opens at or after 11:30 (r268, DEP.12; deliberately not bold: check_docs_roster R4 reads the bold times
above as EOD_SCHEDULE).

**The stops that are one number in `config.py`.** Runaway: a **20%** premium floor
(`RUNAWAY_MAX_LOSS_PCT`). Hunt: NO premium stop - it RECORDS the same floor
(`HUNT_MAX_LOSS_PCT`, also used to pick its contract) and the exit engine HOLDS through it,
logging "would-have-floored" (r209; corrected r227 - r226 wrote this line as if it stopped).
Other single legs: **25%** (`MAX_LOSS_PCT`). Butterflies: **40%** of the debit
(`BUTTERFLY_STOP_LOSS_PCT`; section 3's 15% is stale). ORCS: the condor's rules since r230
(PLAN_SPEC §41.11) - no stop while both sides are open, a lone leg stops at credit + 15% of
its risk, a nickel closes a leg. Every other exit rule lives in `strategy/management.py` and
`execution/exit_engine.py`, not in a number that can be quoted here.

**The resting stop (r266, STOP.1, paper only).** With `OT_RESTING_STOP=trade`, a fired `hard_stop` or
`trail_stop_hit` on a single long does not close at the mark that tick: it rests a sell at its own level for
120 s, filled there if price comes back, else closed at the mark - at once if the mark falls 5% of entry
further. Unset = off: stops close at the mark as before.

**The fill observers (r270, PMAP.1 + FILL.2).** Every open single long gets a premium-map row a minute, and the
end-of-tick sleep records when its own quote crosses its premium stop (data/counterfactual/). `OT_FILL_OBSERVE=off` turns
the recording off. **The floor watch (r280, EXIT.5) WAKES THE TICK:** a Breakout or Runaway whose own quote (at most 4 s
old) is at or below its enforced premium stop ends the 15 s wait and the tick runs at once; the tick still decides (the
resting stop included). Nothing here exits or orders. `OT_FLOOR_WATCH=trade|log|off`, unset = trade.

**The re-fire, the Hunt after a losing Breakout, and the 20 s gate (r316, BRK.15 / HUNT.13 / RENT.3; the operator,
2026-10-24 13:45 and 13:56 ET, "Yes, effective Monday").** A Breakout side fires on a FRESH break: the first 1m close
beyond its edge since 09:35 or since its latest close back inside - every return to the range re-arms it, and the new
session extreme is no longer asked (`OT_BRK_REFIRE`, unset = rearm; `extreme` restores r131). No Liquidity Hunt fires on a
side for the rest of the day once a Breakout on that side has CLOSED at a loss (`OT_HUNT_AFTER_BRK` trade|log|off, unset =
trade). There is no same-side re-entry time gate: the 20 s gate is scrapped (CD.1; "It has zero value. Scrap it.").
Nothing blocks a Runaway because of another strategy's same-side entry. Each old rule's verdict is recorded beside the new
one in data/counterfactual/ (breakout_refire, hunt_after_breakout).

**The commitment state (r272, COMMIT.1/2/3).** Every closed 1m bar each side is COMMITTED, NEUTRAL or ABANDONED
(analysis/commitment.py). A directional entry whose side is ABANDONED is not placed (`OT_COMMIT_GATE`, unset = trade on
paper; a live box only logs); the caution size after the session's first directional loss is logged, never applied
(`OT_CAUTION_SIZE`). Rows in data/counterfactual/.

**The day.** New entries stop while the day's net loss is at or past the daily catastrophic
loss cap (`OT_DAILY_LOSS_LIMIT`), and it re-arms if the day recovers (r162).

---

## How to read this

Each spec declares its gates in three categories (WA §36):

| category | meaning | relaxable |
|---|---|---|
| **SELECTION** | a measured preference. Loosening gives a *worse example of the same trade* — which is what a debug session wants. | **yes** |
| **FOUNDATIONAL** | defines the setup's **identity**. Relax it and this is not that trade. **A gate can be perfectly winnable and still be foundational.** | never |
| **FEASIBILITY** | the trade cannot win, however good it looks. | never |

⚠️ **The relaxed toggle is NO LONGER ON `configure.sh` (removed r127, operator: *"we don't do
relaxed entries here"*); item 7 is now r97's pin-proximity gate.** `OT_RELAXED_ENTRY=1` in the unit
still turns it on (strategy/relaxed.py), per box, paper only, and is unset on this box. It
exists to get trades *firing* so the sequence can be watched, plumbing errors
surfaced, and the stops exercised on deliberately mediocre entries. Every relaxed
trade carries `relaxed_entry=1` and a `_relaxed` setup suffix. **Data collected
under it must never validate a tight threshold.**

---

## 1. Runaway Continuation — `runaway_continuation.py`

**The ORB ran to its 50% TP and held. Buy the direction that already proved
itself.**

It does not predict a direction; **it observes one already in evidence.** Four
independent searches found no directional predictor in this data — entry
conditions (all ambient), recorded columns (gates or empty), opening bias (a
coin, forward-only, 797 sessions) and the tape harness (every surviving
condition helped UP *and* DOWN). The live book agreed at 44.9%.

**OTV4TEST r3 — re-specced with the operator, PLAN_SPEC §30 is the spec.** What
follows is the pre-fork text, kept for its measurements; where they disagree
§30 wins: the trigger is the engine's `fifty_accepted` latch (the same event
that now invalidates the ORB), strength is measured once at acceptance and
sets the strike band, one per break on ANY exit with re-validation on actual,
the r179 session cap is retired, and there is NO premium stop — the position
HOLDS while price is beyond the 50 and exits on the rejection handoff, a close
back through the 50, the fizzle read, the trail, or a close through the
boundary. The relaxed 14:00 extension below was removed at r176.

**FOUNDATIONAL**
· the ORB reached its 50% TP and **HELD** — a 1m *close* beyond, still on the
  right side at the next tick. **This is the entire premise.**
· direction comes from the ORB state, never from a forecast.
· firing **disarms the retest**: the runaway *is* the evidence price never came
  back for it.

**SELECTION** — cutoff 11:30 (the 14:00 relaxed extension is gone).

**FEASIBILITY** — the ATR floor and the ATR→delta map. Below **0.05% ATR the
required move was reached on 0% of 5,517 measured bars.**

**Strike** — ATR-mapped: 0.20–0.35 delta at ≥0.12% ATR (60% reachable),
0.35–0.50 at ≥0.20% (85%). **ADX is not used and that is a measurement** — every
band from 0-15 to 40-100 produced the same median excursion.

**Exit** — trailing stop. `orb_trail_stop` 96% / 85 trades / **+$30,696**, worst
−$16. `bos_exit` 34% / 217 / **−$7,085** with the largest single loss in the v3
book, so **BOS is not used.**

---

## 2. Sweep Credit Spread — `sweep_credit_spread.py`

**OTV4TEST r5 — re-specced with the operator; PLAN_SPEC §31 is the spec.** The text below is the pre-fork record, kept for its measurements (the pierce-depth finding stands and is a bar). Where they disagree §31 wins: the trigger is the derived REJECTED fact, levels come from the store (3 up, 3 down, the 1h tines), the short anchors on the level, the window is 09:35–14:00, the age rule is retired, and the exits are hard close → 15% of risk → breach accepted → nickel.

> **r163 (2026-08-27) — THE FORK'S TINES ARE LEVELS THIS STRATEGY MAY USE, ON A
> TOUCH.** Operator: *"it's basically a moving level that sweep is allowed to
> use, but with a touch, not a reject. The plan would still need to select a
> strike beyond the move that caused the touch."* The liquidity mapper
> publishes every active 1h/1d tine as a MOVING named pool (price is a
> function of time — slope × minutes) and emits a TOUCH event when a 1m bar
> reaches the rail *where it was on that bar*; two closes beyond it since the
> touch invalidate it. The sweep's plan prepares the spread beyond the
> touching extreme and fires **leg one** on the touch, classed `{tf}_fork`.
> **Leg two never takes a touch** — a rejection at the site is required. The
> spent lock is keyed by the tine's NAME. The 1d fork strategy
> (`daily_fork_credit_spread.py`) is retired: its whole job is now the
> mapper's publication plus this plan. See PLAN_SPEC §12.

**A named pool was swept and rejected. Sell the boundary it just became.**

    sweep UP into a pool, rejected   -> CEILING -> CALL credit spread
    sweep DOWN into a pool, rejected -> FLOOR   -> PUT credit spread

**Credit, not long, and that is the point.** A long reversal needs price to
*travel*: 155 of 190 directionally-**correct** continuation entries — **82%** —
never reached +25% MFE, because a 0.30-0.60 delta 0DTE contract needs a 0.90%
move to pay that after the spread, and the tape delivers it in a specified
direction on 22% of windows. **A credit spread needs the level to hold**, and
two thirds of 90-minute windows produce no 0.5% move at all.

**Short strike** — the **first strike beyond the sweep extreme**: the one price
pierced when it cleared one, the next one out when it did not. Never a strike
inside the pool. Further from spot than the boundary: less credit, more room, and
the position is threatened only if price returns to a level it already failed at.

⚠️ **AMENDED r107 (operator, 2026-08-24: "It swept. That's legitimately a sweep.
Sell the 7635").** The old wording required a strike to have been TRADED
THROUGH, which collides with this section's own preference for a SHALLOW pierce:
SPX swept the NY Low by 0.84 pts on a 5-wide chain, cleared no strike, and a
fully-qualified setup was declined 608 times in one session. The collision only
bites on wide-strike symbols — seven of the fifteen boxes — so it read as "no
setups" rather than as a rule. **Strikes are read from the LIVE CHAIN**, not
`STRIKE_INCREMENT`: SPX 0DTE is 5-wide near the money and 25-wide in the tails.

**FOUNDATIONAL**
· the pool is **NAMED**. An unnamed swing high is not a liquidity pool.
· it **RECLAIMED** — a bar *closed* back inside. A wick is a touch, not a
  decision.
· it is **NOT INVALIDATED**. Reclaimed-then-accepted-through is a **breakout**,
  and selling a boundary that already gave way is the worst version of this.
· price is already on the profitable side.

**SELECTION**, all measured on **2,169 sweep events**
· window **13:00–15:00** → 09:45–15:30. *(39% survival vs 26% before 10:30)*
· pierce ceiling **0.25%** → 0.75%. *(33-34% survival vs 19-21% deeper)*
· max age **6 bars** → 18, measured from the **reclaim**.

⚠️ **A DEEP PIERCE MEANS A WEAK LEVEL, NOT A STRONG REJECTION** — 1.28% median
adverse against 0.46%. Price went that far because it was willing to.

**FEASIBILITY** — ATR ≤ 0.20%. Above it the tape produced a 0.5% move on **92%
of 90-bar windows**; a boundary does not hold in that.

**Exit — exactly two.** 15% stop, and the 15:45 hard close. **No trail, no
profit target**, exempt from the 15:40 flatten ladder as a credit vertical.

⚠️ **r99: this trade could not fire and, had it fired, would not have been
managed as written.** `is_valid` demanded four contracts (every sweep died
`Invalid signal`); a valid one would have gone down the DEBIT dispatch and
bought its own short strike; and `structure.of` filed it under TC.6, which has
no premium stop. Fixed: per-side validation, pairing gate ->
`_execute_condor_leg`, CONDOR_LEG (lone-vertical) management.

---

## 3. GEX Pin Butterfly — `gex_pin_butterfly.py`

**OTV4TEST r6 — UN-PARKED BY DATA, re-specced with the operator; PLAN_SPEC §32 is the spec.** Real open interest is arriving on the box (2026-09-09); zero OI is now a STARVED input the row states, not a park flag. Where the text below disagrees with §32 (best-R wing, smoothed persistence, firm EM 1.00), §32 wins.

**Apex on the gamma pin, out of the money. Buy the move to the magnet.**

⚠️ **PARKED until real open interest accumulates (~2 weeks from 2026-08-19).**
`open_interest` was a declared field with **no producer**, so GEX has been
`~100,000 × gamma² × spot` — a gamma-squared surface, not dealer positioning.
The "pin" therefore always sat at spot, and swung 12.4M → 0.1M → 2.0M in three
minutes.

**THE ASYMMETRY IS THE TRADE.** Apex payoff is fixed at the wing width while the
**debit collapses as the apex moves OTM.** A pin at 90% of the expected move
costs a fraction of one at 20% and pays the same. **Distance is the edge.**

**FOUNDATIONAL** — `PINNING`; the apex sits **on** the pin; the pin is **OTM**.

**SELECTION** — pin concentration 0.25 (⚠️ *relaxed with reluctance*: far out,
the trade **relies** on the magnet pulling, so a weak pin far away is the worst
cell in the matrix); window; EM ceiling 1.00 → 1.30.

**FEASIBILITY** — no ATM IV means **no trade**, not a fallback; and the EM floor
at 0.30, because nearer than that the asymmetry — the whole reason for the
structure — is gone.

**Expected move comes from the chain's ATM IV**, not VIX. v3 applied SPX 30-day
implied vol to every symbol on a 0DTE horizon.

⚠️ **RARE BY DESIGN — an opportunity-cost question, not a defect.** It needs a
strong pin far from spot, most likely near monthly expiration when real
positioning sits at a strike. **It costs nothing while it waits**: no position
slot, no capital, no competition. Its evidence will be **structural, not
statistical** — the test is *"when it fires, does the payoff justify keeping
it?"*, answerable on a small sample in a way a win rate is not.

---

## 4. Opening Range Breakout — `orb_strategy.py`

**The one strategy with a positive record, and the reason is in the spec: it
never asked permission.**

`orb_trail_stop` — **96% win / 85 trades / +$30,696, worst −$16.** ORB
consulted no regime label, so it kept working while every gated strategy
degraded on a classifier picking the wrong side 55% of the time. Operator:
*"every day where P&L was green or very green is nearly entirely based on the
ORB trade and the quality of our stops."*

**Trigger** — the opening range breaks and **retests**, confirmed by 1m
body/wick rules. Self-validating geometry.
**Direction** — from which side broke. Not forecast.
**Targets** — `tp50` and the 100% range extension.
**Exit** — `MAX_LOSS_PCT` at entry, then the trailing stop. **No BOS** —
`bos_exit` measured 34% / 217 trades / **−$7,085** with the largest single loss
in the v3 book.

**FOUNDATIONAL** — the break AND the retest. A break alone is not the setup.
**SELECTION** — the confluence notes (named level in the break, VWAP alignment,
clear liquidity path) describe the setup; **none of them gate it.**
**FEASIBILITY** — the range must exist. `_opening_range` reads today's 09:30
bar, after TCS.3 found the 60-bar 1m frame no longer reached it by 10:35.

**OTV4TEST r2 (2026-09-08) — the spec as the operator stated it, and what
came out.** Parts: range/width · impulsive candle H/L · direction · one of
three consequences (retest → fire / runaway → hand off / re-entry → thesis
over) · the sizing constraint · the stops. **Deleted by ruling:** the 12-bar
"stale retest" re-arm (*"if it doesn't retest, it's outside the range — how
would there be another break?"*) and the ATR floor (*"makes no sense"* for
this setup). **Stops:** structure stop = the impulsive candle's LOW (long) /
HIGH (short), body or wick, fired on a 1m CLOSE through it — *wicks are tests,
closes are acceptance*; every other ORB exit kept except velocity stall
(*"theta bleed should catch whatever a stall would have stood in for"*).
**Plan provides:** stop, 100%/50% levels, target strike at ±width, the
contract, floor premium, provisional size — from the impulsive candle's close,
both sides priced from 09:35. Full contract: PLAN_SPEC §29.

⚠️ **v4.0 MADE IT PURELY MECHANICAL.** Three vestigial reads went: the regime
label stamped onto the signal, a confluence note for regime agreement that could
never fire, and `signal.conviction += regime.conviction * 0.7`. All were inert —
`regime.conviction` is permanently 0.0 — **but a dead branch reads as a live one
to anyone auditing the file.** The remaining conviction additions are structural
facts (a named level in the break, a Fed day); they describe the setup and do not
authorise it.

---

## 5. Iron Condor — `iron_condor_strategy.py` + `condor_roll.py`

**The most intricate spec in the book, and the one where the overlay and the
structure agree on when the thesis died.**

### Status, 2026-08-20: a NICE-TO-HAVE anchored to a rare premise

Operator: *"Anchor to the rare fork premise and if it gets us a surprise fill
now and then we can study it."*

**The condor is not load-bearing.** It stays wired, specced and enabled; it fires
when a fork genuinely qualifies, which is seldom. **Rarity costs nothing while it
waits** - no position slot, no capital, no competition with the sweep spread -
and the same opportunity-cost logic as the GEX butterfly applies.

⚠️ **THE RIDDLE, STATED PLAINLY, BECAUSE IT IS WHY THIS TRADE IS HARD.**
Operator: *"We want to execute separate vertical spreads at a time and place
where they are premium rich & we expect price to respect them AND fire a
corresponding rich premium second leg we expect to hold & IF it doesn't, we
collected enough up front to get one leg for free."*
**Rich premium and respected boundaries are in direct opposition.** Premium is
rich exactly where the market prices a real chance of price arriving. A level
price genuinely respects earns little, because it is not in doubt. The trade
needs **a strike the chain thinks is reachable and the tape says is not** - and
that gap is the entire edge.

⚠️ **WHICH IS WHY A SIGMA BAND CANNOT BE THE ANCHOR.** A regression channel
prices dispersion the same way implied vol does, so its rails sit AT fair value
rather than off it - **no edge, because it is the chain's own estimate wearing a
different hat.** Measured, `tests/fork_respect_study.py`, 738 (session, symbol)
observations: a rail was touched on 57% of sessions and **RESPECTED on 5%**
[3%, 8%] while **54% closed beyond it.** It did not improve with span: 7%, 5%,
4% across short, medium and long-lived channels.
**A statistical envelope is not a structural level.** Named pools work as
boundaries because participants defend them; a sigma band has nobody standing
at it - and a named pool is information the option chain is not using, which is
where an edge can live at all. The sweep credit spread (§2) is that trade, and
it is the afternoon premium earner this one was hoped to be.

⚠️ **AND THE "FREE LEG" IS NOT A DESIGN GOAL.** It requires two opposite-sided
qualifying sweeps in one symbol-session inside the window. Operator's own
estimate: *"eclipse rare."* **A structure cannot be built around a
co-occurrence that happens twice a year** - if it materialises it is a bonus to
be studied, not a leg to plan and wait for.

⚠️ ONE HONEST LIMIT ON THE ABOVE: the respect study used a REGRESSION CHANNEL,
not `build_fork_contained`. The refinements - qualified pivots, the
modified-Schiff origin, the ATR significance test - are not tested by it.
**Regression is what worked and the pitchfork is its formalisation**, so the
result is hard to dismiss, but the real fork deserves the same measurement
before it is written off. That is owed work, not a blocker.

### The anchor — the daily pitchfork

Operator, verbatim: *"It's a guardrail, not the road."* → **daily fork only.**
*"Consider the condor off the table if we don't have guardrails."* →
**NO FORK, NO PLAN.**

Short **call** rides the **upper rail**, short **put** the **lower rail**.

### Leg order does NOT fall out of the slope — corrected 2026-08-20

⚠️ **THIS DOCUMENT PREVIOUSLY DESCRIBED THE SUPERSEDED PF.5 DESIGN.**
`v-indep-legs` (2026-07-28) made both sides INDEPENDENT: each fires on its own
price trigger, checked every tick, and if both hit on the same tick the tie
breaks on which is exceeded further. **Whichever tine price actually strikes
first fills first - there is no "wrong" tine to guard against.**
`_leg_order_from_slope` survives as a helper **with no caller.**

And the slope is not predictive anyway: `tests/tine_order_study.py`, daily
channel, called the first rail on **9/15 - a coin**, with the interval spanning
50%. The sample is too small to say more, and it is recorded as suggestive
rather than settled.

**Independent legs is the better design for the same reason everything else in
v4 got better: it observes rather than predicts.** A slope-derived order has to
be RIGHT about the path; independent triggers do not care.

### What the slope was for

**The slope predicts which rail ranging or condensing price taps first.**
An **up-sloping** fork means price travels lower rail → upper rail across the
session, so it reaches the **lower** rail first and the **PUT** side fills
first. A **down-sloping** fork mirrors it: upper rail first, **CALL** first.

⚠️ **This is a claim about the PATH THROUGH THE SESSION, not about where price
is now** — which is also why leg 2 *queues* rather than fires: you are waiting
for the traversal the slope told you to expect.

### Strike selection

*"The short strike should be just outside the range of the rail at the MOST
LIQUID strike WHERE PRICE HAS STILL NOT EXCEEDED."*

· **not-exceeded** — a strike price has already traded through today is one the
  market has **proven it can reach**.
· **most liquid keys on BID/ASK WIDTH.** The old `liq()` summed OI + volume and
  a factor sweep found **both constant across the whole sample**, so "most
  liquid" had silently resolved to "nearest the floor". Width is populated, and
  on a 0DTE credit spread a nickel-wide quote is what trips a stop on noise.
· **`0.80 × EM` minimum distance** survives as a floor: a rail sitting on top of
  spot must not produce a strike with no breathing room.

### Legging

Leg 1 fires on approach to the first side's short. Leg 2 queues after leg 1
**fills**, and fires on approach to the opposite short. **If leg 2 never fires,
leg 1 stands alone as a vertical and manages identically.** A filled leg is
**never** cancelled.

### The roll — integral, not an add-on

One side gets tested → close the **untested** vertical, re-open it closer, and
collect fresh credit. When

    total_credit_collected  >=  tested_side_width

**the tested side can no longer lose** and the structure is a broken-wing
butterfly. The search takes the **smallest** roll that achieves it — least new
risk assumed.

⚠️ **THE ROLL IS THE PRIMARY RISK RESPONSE TO A TESTED SIDE and should be
attempted before a stop is taken.** A silent refusal to roll is the most
consequential of all the silent declines, which is why v1.1 made it name the leg
that had no mark.

### Gates

**FOUNDATIONAL**
· a **daily fork exists**. No fork, no plan — there is no anchor, no leg order,
  and no expected path.
· short strikes sit **outside the rails**.
· the strike has **not been exceeded** today.
· leg 2 requires leg 1 **filled**.

**SELECTION** — the approach distance, the entry window, the wing width.

**FEASIBILITY** — the `0.80 × EM` floor, and no liquid strike beyond it.

⚠️ **THE `RANGING` GATE IS REPLACED BY FORK INVALIDATION.** v3 cancelled a
pending leg when the regime flipped away from RANGING — and that label is
exactly what v4 removed for picking the wrong side 55% of the time. The fork
already provides the structural equivalent, and the operator's own accepted risk
says the two are the same event: *"If it gets breached, then our fork may also
become invalid & I can live with that, because we are accepting that risk for an
asymmetric payoff if it holds."* **The structure and the overlay agree on when
the thesis died instead of arguing about it.**

### Exits — a management LADDER, not a stop

**No take-profit, no trail, no BOS, ever.** Measured: on 18 standalone legs a
TP@25% turned −$242.77 into −$8.43, and **on 28 condor legs a TP was worse at
every level.** A credit vertical is *earning* from decay; closing it early buys
back the theta it was opened to collect. The nickel close ($0.05) is always
available — that is a win, not an abandonment.

**BEFORE LEG 2 FILLS — leg 1 manages exactly like the sweep credit spread: a
15% stop.**

⚠️ **THE GEOMETRY IS WHY.** The traverse that completes the condor is the same
move that makes leg 1 profitable: an up-sloping fork fills the put at the lower
rail, and price must then travel *up* toward the upper rail to trigger leg 2 —
moving the short put spread *away* from its short strike the whole way. **So a
leg 1 that is losing is a leg 1 whose condor will never form.** Waiting out a
25% loss on it is not protecting a condor thesis; the thesis is already dead and
what remains is an unhedged vertical being held in hope.
· `condor_stop` measured 16 trades, 19% win, −$1,156, worst −$300. The 25% was
  never validated, and it was calibrated for a *complete structure collecting
  credit on both sides* — not for one naked leg.
· **The stop widens only when there is offsetting credit to justify it.** That
  is the honest reason a wider stop is ever acceptable.
· Fewer condors will complete. **That is the point, not the cost** — the ones
  declined are the ones whose traverse already failed.

**ONCE FORMED — the roll has FIRST RIGHT OF REFUSAL, and there is no competing
percentage stop.**

A stop on a formed condor is close to incoherent: it pays to exit a position the
roll could have made **risk-free**. The ladder, in order, and **each rung states
what is behind it**:

**1. ROLL TO RISK-FREE — arithmetic.**
Close the untested vertical, re-open it closer, collect fresh credit. When
`total_credit_collected >= tested_side_width` the tested side **cannot lose**.
Smallest qualifying roll wins — least new risk assumed. *Provable.*

**2. INVERT TO A BUTTERFLY — the operator's experience.**
If no roll clears the width, roll the untested side **all the way adjacent to
the tested short**: shared body, which *is* a butterfly. That is the maximum
credit a roll can produce when risk-free is out of reach.
⚠️ **It also converts the thesis honestly.** The condor said *"price stays
between the rails"* — dead, one rail is being tested. The butterfly says
*"price is here now, and I take max profit if it stays."* You trade the position
you actually have rather than the one you opened.
⚠️ **PROVENANCE, STATED: no v3 trade ever did this. It is discretionary
practice, not a measured rule** — sound mechanically, with no sample behind it.
It ships as a documented rung and is **instrumented rather than trusted**: every
inversion journals what the roll search rejected and why, the credit at
inversion, and what the position did afterward. A rare adjustment will never be
validated statistically, so **the evidence has to be a legible record of each
individual case** — the same footing as the GEX butterfly.
⚠️ **AND THE FORMERLY-UNTESTED SIDE BECOMES EXPOSED.** It was rolled to where
price is. A hard reversal now loses on that side too — capped by the wings,
which is exactly why this is acceptable where a naked roll would not be.
**EXIT THE INVERTED BUTTERFLY IF IT BLEEDS 25% OF TOTAL PREMIUM COLLECTED** —
measured against the *cumulative* credit (original condor + every roll), because
after inversion the position is one structure, not two legs.

**2b. THE TENT — operator's spec, 2026-08-24, BUILT r106.**
If we have ALREADY ROLLED and a **1-min candle CLOSES beyond a short strike**,
take the **profitable** vertical off (computed from marks, never assumed) and buy
a long of the **OPPOSITE type**, equidistant from the remaining short as its
existing wing — *"leaving price under the tent."* Worked example: condor 95/90p +
105/110c, call side tested, put side rolled to 100/95, price closes above 105 →
keep 105/110c, hedge is a **long put at 100**; the two longs bracket price.
⚠️ **PRICED BEFORE IT IS PAID.** If the hedge's debit alone puts the structure at
−15% of cumulative credit, the tent is NOT built and the whole thing closes.
⚠️ **THEN ONE ADJUSTMENT ONLY** — a 15% floor on CUMULATIVE credit (original +
every roll − the hedge debit). No TP, no trail, no nickel.
⚠️ **PROVENANCE:** the rungs and the floor are the operator's; the OPPOSITE-TYPE
hedge was one of two options surfaced by a payoff analysis (a same-type long
leaves the far tail uncapped) and the operator chose it.

**3. STOP AND PAGE — the fallback, and the page is the point.**
Reaching this means **both risk-reduction steps were unavailable**: no roll
cleared the width and no inversion was possible — an expensive buy-back, no
liquid strike, a gapped chain. ⚠️ `condor_roll` v1.1 exists because a missing
mark caused a **silent** refusal, and *"the roll IS the risk-reduction step, so
a quiet refusal is the most consequential of the three silent declines."*
**A roll declining is information wanted in the moment, not at EOD.**

**And 15:45 applies throughout** — both legs are credit verticals, exempt from
the 15:40 flatten ladder.

---

## 6. EXECUTION — ONE PRICING AUTHORITY FOR EVERY TRANSACTION

**Operator's spec, 2026-08-24, read back and confirmed. Applies to every order
this system places — entries and exits, debits and credits, every strategy.**

🔴 **THE LADDER WAS BUILT ON 2026-08-20 AND HAS NEVER BEEN CALLED.**
`execution/entry_ladder.py` is a complete 221-line implementation — 25% start,
venue-increment stepping, ratchet, reprice, mark floor — with **zero importers**.
It appeared in `gen_file_map`'s orphan report and was dismissed as noise. The
live path posts a single `limit_at_mark` and walks away
(`entry_engine.py:269`), so **every rung of price improvement since the split
has been given away.**

**Status r99 (2026-08-24): STILL UNWIRED.** Two more residual defects fixed
first — `next_price`'s rule-3 clamp returned the raw mark (0.475 on a penny
grid), and `ladder_registry.price_for` rejected a zero bid, the header's own
example. Wiring lands as r100 across the five sites below.

⚠️ **AND THIS IS THE LARGEST SINGLE ITEM ON THE BOARD.** FRC.1: gross edge
**+$2.70/trade** against **$126/trade** of round-trip friction. Capturing half
the half-spread is worth on the order of **$31/trade** — an order of magnitude
more than anything on the trade-selection list. `entry_ladder.py`'s own header
says so, and nothing read it.

### The two authorities

    PAPER   limit_ladder.paper_fill_price / paper_fill_credit   (mark-based)
    LIVE    entry_ladder.LadderState                            (the ladder)

Nothing else prices an order. A strategy proposes a structure; it does not
price it.

### The walk

· **Start 25% in from the BEST price** — the ask when selling, the bid when
  buying. Not 50%: *"always start at 25% of best price to not waste a lot of
  time on hopeless attempts."*
· **Step ONE VENUE INCREMENT toward mark.** Granularity falls out of the
  increment, not a fraction list — a nickel grid on a $1.00 spread gives six
  rungs, a dime grid three.
· **ONE RUNG PER TICK.** A refusal is *"didn't completely fill at that price"* —
  a partial counts as a refusal for the remainder.
· **RATCHET** — a refused price never returns, even if the market moves back
  through it. *"If it's not accepting 80 at the first attempt, it won't accept
  80 at the next attempt."*
· **REPRICE** each attempt from the CURRENT mark, never the entry-time one.
· **MARK FLOOR — NEVER POST WORSE THAN MARK.** *"If price moved in our favour,
  don't offer to give it back."* On a market moving our way the ladder collapses
  to mark and fills, which is correct: the rungs only ever existed to try for
  BETTER than mark.

### Per-transaction policy

| transaction | policy |
|---|---|
| every entry | full walk |
| condor roll | full walk |
| inverted butterfly | full walk |
| structural / profit-side close | full walk |
| **15% floor stop** | **escalate straight to MARK**, reprice at mark each tick |

**WIRED r104 (entries) / r105 (exits, roll).** Debit hard close KEEPS the cross:
§6's prose and its table disagreed, and the assignment argument is about SHORT
verticals — a long that does not close does not assign, it EXPIRES WORTHLESS, so
there is no assignment tradeoff to take and paying the spread beats losing the
premium. Credits take the nickel or take assignment, and never cross. The roll's
open half walks WITHIN its call: by the time it runs the old untested vertical is
already closed, so `check_and_execute_roll` sees `len(legs) != 2` next tick and
never re-enters — an unfilled rung would strand the position half-rolled.
| **debit hard close (15:40)** | the existing flatten ladder |
| **credit hard close (15:45)** | nickel close, else **ASSIGNMENT** |

⚠️ **THE 15% FLOOR DOES NOT WALK.** It is thesis-invalidated; spending six ticks
hunting a better fill while price runs is turning a stop into a negotiation. It
goes to mark and re-prices there until filled.

⚠️ **NOTHING EVER CROSSES THE SPREAD.** Operator: *"I'll take assignment over a
shitty market order fill."* This REVERSES `hard_close_order_mode`, which returns
`'market'` from 15:45 — *"the position MUST close; cross and be done."* Two call
sites act on it (`exit_engine.py:2029`, `:2364`).

⚠️ **THE TRADEOFF IS DELIBERATE, NOT A SIDE EFFECT.** Accepting assignment means
overnight exposure and margin on the underlying. On a defined-risk vertical that
is usually better than crossing a garbage 0DTE spread. It is a policy choice
made with the cost known.

⚠️ **NICKEL IS A DISPOSAL RULE, NOT A TAKE-PROFIT.** There is no TP on a credit
vertical — it is an all-or-none theta trade. `CONDOR_NICKEL_CLOSE` survives only
as the 15:45 preference; it is unreachable intraday because 15:45 arrives first.

### Ladder state

`LadderState` carries the ratchet, so it must persist ACROSS ticks — one rung
per tick means the walk IS multi-tick. Keyed per open order intent; cleared on
fill or abandon. **Lost on restart**, which costs at most one re-offer of an
already-refused price. Recorded here rather than defended: it does not ride a
column, and WORKING_AGREEMENT 22 says state that must survive a restart does.

**r315 (2026-09-08) — THREE CORRECTIONS ON THE CREDIT PATH, war-gamed first.**
· **The credit rung gets the per-rung slice**, `max(4, 20/4)` = 5s, the same
  `entry_engine._rung_deadline()` the debit walk has had since r104. It was
  taking the whole 20s budget plus cancel grace per rung.
· **A PARTIAL keeps walking.** The filled part is booked at once; the remainder
  is registered in `execution/credit_remainder.py` and offered ONE rung per
  tick from before the position split, on the SAME strikes and the SAME walk,
  until it fills, the position closes, or the strategy's entry window closes.
  Fills accrete into the one row — blended credit, recomputed max loss. In
  memory, lost on restart, like the walk itself.
· **The walk belongs to the INTENT, not the strike pair.** Key
  `cv:<sym>:<strategy>:<side>`; the strikes ride as a tag. When the strategy
  re-selects strikes mid-walk the RUNG carries and the PRICE ratchet drops —
  a refused credit on one pair is not evidence about another. Before this a
  moving tape restarted the walk at the 25% opener on every strike.
· **No positive price, no order.** An unusable structure quote posts nothing;
  it never falls to a bare mark.

---

## 7. Breakout — `breakout.py` (the spec) + `breakout_plan.py` (the plan)

**Written 2026-10-03 (OTV4TEST r227) from the code as it runs. ON.**

**What it is.** The ORB without the retest (operator, 2026-09-19: *"Make it follow the orb
structurally, but without a retest. And with better informers."*). It buys a call on a break
above the 5-minute opening range, a put on a break below, the moment a 1m bar CLOSES beyond
the edge.

**Entry, 09:35-10:30 ET (last entry 10:29).** Every condition is recorded on the plan row:

| condition | what must be true | category |
|---|---|---|
| `entry_window` | inside the window; an unreadable clock is no trade (r220) | FOUNDATIONAL |
| `break_close` | the last CLOSED 1m bar closed above the range high (long) or below the low (short) - bodies decide, wicks test | FOUNDATIONAL |
| `fresh_break` | since r316 (BRK.15, the operator 2026-10-24: "The new session high/low rule needs to be dropped"; "For now, rearm it on every reentry"): the signal bar must be the FIRST 1m close beyond the edge since 09:35 or since the side's latest close back INSIDE the edge - every return to the range re-arms the side, and a break the gates refused still spends it until a close back inside. The bar that already fired is refused (r142). Read from trades.db and the feed store; unreadable is a refusal. r131's verdict is written beside every disagreement to data/counterfactual/breakout_refire.jsonl | FOUNDATIONAL |
| `new_extreme` | ROLLBACK ONLY (`OT_BRK_REFIRE=extreme`): the first entry per side per session needs only the break. Every later entry on that side needs a 1m close beyond every prior RTH bar's high (long) / low (short) since 09:30 (r131). Read from trades.db and the feed store; unreadable is a refusal | FOUNDATIONAL, no knob |
| `orb_range`, `range_clean`, `flow_commit`, `gamma_regime`, `depth_thin`, `room_to_run`, `r` | the informers: range width, no live level inside the range, aggressor imbalance with the break, a non-pinning regime, thinning depth ahead, open air or a pool at least 1R away, R at or above the floor | **accept "any" until `OT_BRK_RESEARCH_UNTIL` (2026-10-30)** - recorded on every row, refusing nothing. ⚠️ Except an ABSENT flow reading, which `flow_commit` has always refused. **On a cash index (SPX, r251 BRK.6) `flow_commit` and `depth_thin` are n/a - "no tape" / "no book" - and MET, before and after 10-30** (the operator, 2026-10-05: "we have to get SPX Trading those breakouts") |
| `contract`, `premium` | a listed strike at the reach with a live quote above `QUOTE_FLOOR` | FEASIBILITY |

The informers' fitted dials are the `BRK_*` constants in `config.py`; they bind only after
the research window ends, and fitting them is BACKLOG BRK.5. Volume on the break bar is
recorded and never gated (measured useless, n=736).

**Geometry.** Stop: the breaking bar's low (long) or high (short). Risk: break close to that
stop. Reach: the nearer of the measured move (break close plus or minus the range width)
and the nearest named pool. The contract is chosen at the reach by the ORB's selector.
It sizes on that geometry (`sizes_on_geometry`), scaled when `OT_SCALE_BREAKOUT=1` (default).

**The strategy confirms, it does not search.** On the tick it fires, price must still be
beyond the edge and the persistent conditions must still read true, or it holds.

**One at a time** (admission: `max_open_of_type=1`). It runs beside the Hunt and the Runaway
and blocks neither.

**Exits (`strategy/management.py`, first match wins).**
1. `hard_stop` - premium at or below the record's stop premium. Priced at the mark, now.
2. `structure_stop` - a TOUCH through the breaking bar's extreme, unless the trail is nearer.
   A return INTO the range with that stop intact is a HOLD (operator, 2026-09-19).
3. `delta_par` - delta at or above `DELTA_PAR` (0.98): it is stock now, get out.
3a. `no_progress` (r265, BRK.8) - after 2 consecutive CLOSED 1m bars after the entry bar with no
   new favourable extreme, a trade whose best progress since entry is under 0.5 R is cut (decided
   once; the mark ladder). `OT_BRK_NOPROG`: `trade` cuts, `log` (the default) only records the cut
   in `data/counterfactual/breakout_no_progress.jsonl`, `off` skips. Operator, 2026-10-10: *"Yes, to
   all. Study, fit & apply."*
4. `exhaustion` - a new favourable extreme on WEAKER 5m momentum. This is the trade's
   real exit: it has no target.
5. the exit engine's trail, as a floor under the trade, and the close schedule in section 0.

**Open:** the dials are unfitted (BRK.5); no exit candidate beat this stack on 266 days.

---

## 8. VOLT — `volt_plan.py` + `volt_strategy.py`

**Written 2026-10-03 (OTV4TEST r227) from the code as it runs. OFF since r187 (operator,
2026-10-02); `OT_VOLT=1` restores it exactly as described here.**

**What it is.** A volume-expansion trade with two selection gates and nothing else, kept
deliberately short: a third gate belongs in a new strategy.

**Entry, 09:35-10:30 ET, on completed 1m bars** (it needs `VOLT_MIN_BARS` + 1 = 4 of them):
1. **Direction** - the last completed bar's close against the session's first open. Above is
   long (a call), below is short (a put). No threshold, nothing to tune.
2. **Volume** - the last completed bar's volume is at least `VOLT_VOL_MULT` (1.25x) the mean
   of the `VOLT_VOL_LOOKBACK_BARS` (5) bars before it.

The contract is the first out-of-the-money strike from the current price with a quote; the
budget (`OT_VOLT_BUDGET_USD`) must buy at least one. **One at a time.**

**The stop is the entry** (operator, 2026-09-21: *"Use a structural stop. A close beyond
where the trade opened is a dead thesis."*). `underlying_stop` equals the entry price by
design.

**Exits (`exit_engine._evaluate_volt`, first match wins).**
1. The close schedule in section 0.
2. Premium floor - premium at or below the stop premium (else `MAX_LOSS_PCT`, 25%).
3. Par delta - delta at or above 0.98.
4. Structure stop - the last COMPLETED 5m bar that POSTDATES the entry closes back through
   the entry price. With no such bar yet, it holds on the premium floor alone.
5. Trail - arms once the 5m close has travelled `VOLT_TRAIL_ARM_R` (0.50) of the
   entry-to-target distance; then exits on a 5m close through entry plus
   `VOLT_TRAIL_LOCK_FRAC` (0.50) of the peak gain. The floor is never below entry.

**Two things in the code that disagree with the above and are NOT fixed here** (VOLT is
off; BACKLOG DOC.31): the exit reason text says "1m close" while the bar read is 5m, and
`_evaluate_volt`'s docstring still describes a "3x5m structural extreme" stop.

---

**The Liquidity Hunt** is PLAN_SPEC §37 and **ORCS** is PLAN_SPEC §41; section 0 above
carries where each now differs (the Hunt's window ends 10:30, not 11:30; its premium floor
is recorded and never acted on, as §37 says: "no premium stop").

---

## 9. PARK — `park.py` (the spec) + `park_plan.py` (the plan)

**OTV4TEST r288 (PARK.1), 2026-10-18.** The operator's friend's 11:00 continuation, renamed PARK.
The operator, 2026-10-17 18:21 ET: *"Trade it, don't just log it. Paper is free. Call it PARK
(named after my friend)"*; on SPX: *"Use our actual numbers, trade it—don't log it"*; 18:30 ET:
*"Make sure when you build it it's divided properly between the strategy and the plan."*

**The split.** `strategy/park.py` says what must be true and confirms the quote on the firing
tick; it reads nothing. `strategy/park_plan.py` reads the first hour from the feed store, picks
the contract and builds the signal.

**Entry, once per session, 11:01-11:03 ET:**
- the first hour moved: the 10:30 1m close against the 09:30 1m open, |move| >= 0.20%; its sign
  is the direction;
- GATE-G: never against the opening gap (09:30 open vs the prior session's last RTH 1m close);
- the strike nearest the 11:00 1m close, today's expiry, two-sided, ask >= 0.50, bought AT THE MARK
  ((bid + ask) / 2, floored to the cent; r60 PARK.4, the operator 2026-10-30: "we ladder in from
  aggressive to mark & never worse than mark"). Paper books the mark; live walks the entry ladder from
  25% in off the bid toward the mark, one increment a tick, never above it - unfilled by 11:03 is no trade;
- sized flat on the box's own risk, floor(risk / (mark x 100)): $1,050 on QQQ-TEST, $2,500 on
  SPX-TEST. No scaling, no pin-proximity gate (PIN_EXEMPT); what the gate would have said is a
  counterfactual row on every PARK entry, `data/counterfactual/pin_gate.jsonl`.

**Its own budget.** PARK is cap-exempt (admission) and its closes are left out of the
catastrophic cap's day P&L (`config.CAP_EXCLUDED_STRATEGIES`). Displays still count it.

**Exits, first match wins (`exit_engine._evaluate_park`):** the lock - armed once the bid reaches
+60%, out when the bid falls to +20% (after a restart the persisted best MARK, `max_premium_seen`, re-arms it once - r291); the delta floor - |delta| <= 0.30 from 11:30 (unread delta
holds); the close at 15:45. No premium stop, no trail. Every exit writes
`data/counterfactual/park_exit.jsonl` so Saturday prices what holding to 15:45 would have done.

**Measured** (read-only, 2026-10-17; fit week 10-12..16 reported separately): QQQ 41 days n11
+10,550 at $1,050 (+1,590 without the fit week); SPX 39 days n14 +13,320 at $2,500. PARK.X (picks
sha 85dca420): the delta floor +11,786 on QQQ, +16,370 on SPX, every winner kept; take-profit and
time exits cut the big days. Small n: the book rests on two or three days a month.

## Not specced, deliberately

**`continuation_strategy`** — inert. The runaway handoff already *is* the
trend-participation trade, and it observes a move in evidence where this one had
to forecast persistence. Kept as a shell in case a case arises the runaway does
not cover.

**`trend_credit_spread` (TC.6)** — inert, and the record supports it: 21 trades,
28.6% direction accuracy. **The sweep spread sells a boundary that proved
itself; the ORB edge has proven nothing except that the first fifteen minutes
had a high and a low.** It is also redundant against the runaway — one trades
the ORB *breaking and holding*, the other the ORB *holding*. Between them they
cover every outcome, which is not coverage.

### DELETED 2026-08-20 — superseded, not shelved

`butterfly_strategy.py`, `continuation_strategy.py` and
`sweep_reversal_strategy.py` are **gone from the repo**, along with their imports
and dispatch blocks in `main.py`.

⚠️ **They were briefly carried as "inert shells" exempt from the tree-wide
exorcism gate (`tests/check_no_regime.py`, retired r278 once the only surviving
mentions were historical), and that was wrong.** They were not future work —
they were the v3 implementations the new specs replace, and **a permanent
exemption for superseded code is a growing blind spot an audit will ask about.**
All three were gated on `regime.primary_regime`, which v4 leaves permanently
UNKNOWN, so they were dead code that still had to be read and reasoned about.

Git has them. The replacements are sections 1, 2 and 3 above.
