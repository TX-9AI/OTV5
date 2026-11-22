# TRADES — the specs

**`TRADES.md` v5.27 · 2026-11-21 · r141 (the Saturday brief 2026-11-21 §4 item 12) — section 0's plan-states paragraph: Runaway and the Hunt have switches (`OT_RUNAWAY`, `OT_HUNT`); Breakout's `OT_BREAKOUT` is no longer read (dormant r110).**

**`TRADES.md` v5.26 · 2026-11-21 · OTV5 r139 (EXIT.15 + EXIT.16 + EXIT.17 + EXIT.18; the live exit polling audit 2026-11-21 S1-S4, live only) — section 6, the live close does what the spec says: a stop counts ITS OWN attempts (refused and rejected ones included, a lock exit's walk never; a different exit reason starts again; a restart continues), so it posts at the mark, the mark, then the bid, then MARKET; every close is priced off the feed store's mark re-read just before it posts (the freshest stored mark, its age logged; an unchanged quote is the current quote, since the feed sends a quote only when it changes), and only a quote past the feed's own 120 s staleness rule goes as a close with no mark; a broker refusal is a refusal (the reason paged), not a lost reply; and a cancel refused because the order just filled books in the same pass. The operator, 2026-11-21: "Yes, in that order". The order itself (the mark, 2 s polls, 8 s deadline, cancel-confirm-dead, the stop steps 2 and 3, the 15:55 cross) is unchanged.**

**`TRADES.md` v5.25 · 2026-11-21 · OTV5 r138 (EXIT.11 + EXIT.12 + EXIT.13 + EXIT.14; the live exit polling audit 2026-11-21 M1-M3, live only) — section 6, a live close that has started: an unreadable read of the kept close order posts nothing (the id is kept and re-read next pass) until the end-of-day close, when the broker's own book and positions decide (every working order on the contract cancelled and confirmed dead, the broker-held remainder closed, the 15:55 cross intact); an order FILLED whose fills cannot be read keeps its id and books once when they read; and while a position holds partial-close fills or a kept close order it keeps closing under its last exit reason until flat, even when the trigger flips back, a restart included. The operator, 2026-11-21: "Yes, in that order" / "I don't want partial opens or partial closes to be the norm". The exit order itself (the mark, 2 s polls, 8 s deadline, cancel-confirm-dead, the stop escalation, the 15:55 cross) is unchanged.**

**`TRADES.md` v5.24 · 2026-11-21 · OTV5 r137 (CAP.10 + LOCK.1) — the day and sections 9-10: PARK and OGAP fall under the daily catastrophic cap both ways (their closes count toward it; at the cap their entries are refused like every other strategy's), and PARK's +60% / +20% lock arms and exits on the MARK, not the bid. The operator, 2026-11-21: "both trades should fall under the catastrophic cap & any profit locks need to be on mark". Every number unchanged; the exit order (exit-at-mark, the stop escalation, the 15:55 cross) unchanged.**

**`TRADES.md` v5.23 · 2026-11-21 · OTV5 r136 (OGAP.3) — section 10: OGAP reads the MARK wherever Park's spec reads the ask or the bid: the $0.50 floor, the size floor(`RISK_PER_TRADE_USD` / (mark x 100)), the band, the booked fill, the peak, the 1.6x / 2.0x lines, the 1.2x and 0.60 x peak floors, the 14:00 sweep under 0.75x; his numbers unchanged. The operator, 2026-11-20: "Ours needs the modification to account for how I would trade it, never pay the spread." / "Mark is the worst buy or sell we accept."**

**`TRADES.md` v5.22 · 2026-11-20 · OTV5 r135 (GUARD.1; the live-readiness audit C3 + I3) — section 6: while ANY opening order's fate is unknown (an unconfirmed cancel, a lost reply, a fill whose fills cannot be read) no opening order posts on the instrument (any strategy, any strike; exits never wait); the unknown is read from the broker every tick, a fill (or the partial an unconfirmed cancel leaves) is booked once as the ORIGINATING strategy's trade at the broker's fills, a dead order clears; unresolved after 120 s (or at all once the day's last entry window, PARK's 11:03, is 120 s behind) it pages once and reconcile adopts it. The ladder's rules are unchanged. The operator, 2026-11-20: "Yes, let's fix it smartly."**

**`TRADES.md` v5.21 · 2026-11-20 · OTV5 r133 (LADDER.1, D2 + D3) — section 6: the live entry walk posts rung after rung inside one tick (~6 s apart, cancel-confirm-post, bounded by one 15 s tick, back to the tick on a fill, the mark rung refused, the window's end, no fresh quote, an unconfirmed cancel), and the contract is frozen for the walk's life. The ladder's rules are unchanged. The operator, 2026-11-20: "Yes to both".**

**`TRADES.md` v5.20 · 2026-11-20 · OTV5 r132 (TICK.3) — section 6: the entry walk steps one VENUE increment of the UNDERLYING's grid (the rule cached under INSTRUMENT, as exits use), never the OCC symbol's; at r131 every live entry fell back to the non-penny grid (QQQ 3.40/3.50 posted 3.40 every tick; now 3.42 -> 3.45). The ladder's rules are unchanged. The operator, 2026-11-20: "Yes to both".**

**`TRADES.md` v5.19 · 2026-11-16 · OTV5 r131 (OGAP.2) — section 10: OGAP sizes on the ramp MIN, floor(`RISK_PER_TRADE_USD` / (ask x 100)) (`OT_RISK_USD`), not a flat $500; `OGAP_BUDGET_USD` is deleted. The operator, 2026-11-16: "Do me a favor and size the OGAP to whatever the ramp minimum (risk per trade) is set at instead of a flat $500. That $500 is Park's (my friend) preferred position size. I like 1050 for most trades."**

**`TRADES.md` v5.18 · 2026-11-14 · OTV5 r115 (HYG §5.1) — §0's stops line drops the butterfly stop constant (deleted from config.py; nothing read it since r107); two bold stops remain (`check_docs_roster` R5). Docs only in this file.**

**`TRADES.md` v5.17 · 2026-11-14 · OTV5 (OGAP.1) — OGAP joins the roster: Park's friend's ORB-GAP, a faithful paper copy on the QQQ box only (section 10; docs/OGAP_SPEC.md). The operator, 2026-11-14: "let's design & paper trade the OGAP on QQQ".**

**`TRADES.md` v5.16 · 2026-11-14 · OTV5 r110 (WS.3 TRIM) — Breakout is DORMANT from 2026-11-16 and leaves the roster: its §0 row goes (three trades and PARK remain), section 7 is marked DORMANT. Its code is kept for a revisit (strategy/breakout.py, its plan and exits), with no switch: no env value turns it back on (strategy/plan_state v5.8). The operator, 2026-11-14: "Concur" (WS.3: the fitted gates failed blind; window EV -$11.73/trade [-59.33, +41.68], n=120, fees $1,572.62 beside).**

**`TRADES.md` v5.15 · 2026-11-14 · OTV5 r109 (the Saturday brief 2026-11-14 §4, items 3 and 10) — §5 opens with the condor's ENTRY DORMANT state (r249: management and the roll only; the sweep and fly comparisons are gone with those trades), and the stops line says `BUTTERFLY_STOP_LOSS_PCT` is read by nothing since r107. Docs only.**

**`TRADES.md` v5.14 · 2026-11-09 · OTV5 r103 (RETIRE.5 step 2) — the GEX pin butterfly is REMOVED with its code: its roster row and section 3 are gone, OT_GEX_BUTTERFLY is read by nothing. The operator, 2026-11-08: "I concur on both, in that order" (cut 11-09, code removed after that close).**

**`TRADES.md` v5.13 · 2026-11-08 · OTV5 r97 (RETIRE.5) — the GEX pin butterfly is CUT from 2026-11-09: OFF in code (config.GEX_BUTTERFLY_ENABLED False; OT_GEX_BUTTERFLY no longer turns it on), never asked, writes nothing; exits untouched. Its code is removed after the 11-09 close. The operator, 2026-11-08: "I concur on both, in that order". Evidence: window EV −$6,482 [−19.2k, +3.2k], lunch entries lose, no fly since 11-03.**

**`TRADES.md` v5.12 · 2026-11-08 · OTV5 r90 (SHADOW.1) — two LOG-ONLY rules, never deciding: the Hunt records each fire's opening-range / EM verdict (S5 R1, skip below 0.927) and PARK records the daily SMA 50 slope verdict on every tick with a direction (S4). See section 9; rows plan_check shadow_hunt_or_em / shadow_park_sma50.**

**`TRADES.md` v5.11 · 2026-11-08 · OTV5 r88 (RETIRE.3) — the trend credit spread (TrendCreditSpread) and its r57 log-only SHADOW are REMOVED with their code: its roster row goes, OT_TCS_ACTIVE is read by nothing, raw/shadow_trades is no longer pushed. It never fired: its own entry gates declined every candidate 11-02..11-06. The operator, 2026-11-08: "Delete".**

**`TRADES.md` v5.10 · 2026-11-08 · OTV5 r81 (DOC.36) — section 9: PARK sizes on each box's own `OT_RISK_USD` (configure item 2); the QQQ-TEST and SPX-TEST figures went with those boxes (retired 2026-10-25). The Saturday brief 2026-11-07 section 4 item 4.**

**`TRADES.md` v5.9 · 2026-11-08 · OTV5 r76 (RETIRE.1) — the retired trades are REMOVED with their code: the ORB break + retest, VOLT, the sweep credit spread, the ATP butterfly and ORCS leave the roster, and sections 2, 4 and 8 are gone. The opening-range ENGINE stays (Runaway, Breakout and the Hunt read it). The operator, 2026-11-07: "Running dead code and logging dead code activity is unnecessary drag. Yes, I want all of those things fixed."**

**`TRADES.md` v5.8 · 2026-11-03 · OTV5 r73 (BFLY.17) — section 3: the GEX pin butterfly holds to the close (no premium stop, no decay stop), is never opened at VIX 20 or above, and asks two more things at the door: the 09:30 open inside yesterday's range, and a debit of at least 15.5% of the width. The operator, 2026-11-03: "For the GEX fly, I want no stop except hold to close, I want the VIX rule enforced & I want more discriminatory entries."**

**`TRADES.md` v5.7 · 2026-11-03 · OTV5 r72 (PARK.5) — section 9: on an equity PARK also needs QQQ to agree and the market's commitment (fewer than 2 of 3 leans against on the name and on QQQ); an index (SPX, QQQ) never asks; a tape too thin to read is no trade. The operator, 2026-11-03: "Let's modify the park trade on equities using the new filters —add a gate in the code "is an index=false" and start trading it Monday."**
**`TRADES.md` v5.6 · 2026-10-31 · OTV5 r68 (CFG.5) — the pin gate, Breakout scaling, Runaway's and Breakout's entry ends and Breakout no-progress are fixed in code (gate ON, scaled, 10:30, the cut trades), with no env key and no configure.sh item; the resting stop section is deleted with the feature. The operator, 2026-10-31: "Resting stop was a study. It failed. Get this the fuck out of here"; "Do NOT add anything else to my config following a study or test".**
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
| Runaway | `RunawayContinuation` | ON | none (its end is fixed; r68) | 09:35-10:30 | PLAN_SPEC §30 |
| Liquidity hunt | `LiquidityHunt` | ON | none | 09:35-10:30 | PLAN_SPEC §37 |
| PARK | `PARK` | ON | none (`OT_PARK=log` records it, `off` stops it) | 11:01-11:03 | section 9 below |
| OGAP | `OGAP` | ON | none (QQQ only, `config.OGAP_SYMBOLS`; no study toggle) | 09:46-10:32 | section 10 below |

A window's end is exclusive: 10:30 means the last entry is 10:29. A switch is ACTIVE at
`1` or `active` (r303 below). The ORB trade, VOLT, the sweep credit spread, the ATP butterfly and ORCS are REMOVED (r76,
RETIRE.1), the trend credit spread with its shadow (r88, RETIRE.3) and the GEX pin butterfly (r103, RETIRE.5); Breakout is DORMANT from 2026-11-16 (r110, WS.3 TRIM; its code kept, section 7); the opening-range ENGINE is not removed: Runaway and the Hunt read it, and since r222 its
range is checked against the official print. The condor is a management plan with no entry
of its own; with every credit entry removed it has nothing to manage.

**Plan states (r303, PSTATE.1; `strategy/plan_state.py`).** Every plan is ACTIVE (evaluated, written, trades), LOG
(evaluated and written, every fire recorded LOG-ONLY and never executed) or DORMANT (never asked, writes nothing: no
plan_tick / plan_check / plan_ledger / plan_heartbeat row, not on the `[plans]` line). The operator, 2026-10-19: "dormant
plans should not write to the ledger, unless we are studying them as 'log only' - I would like each plan to have 3 states".
Each switch takes `active` | `log` | `off` (`1` still = active; for an OFF-by-default trade anything else stays dormant;
a value nobody recognises keeps the default and is named at start). Runaway and the Hunt gained switches
(`OT_RUNAWAY`, `OT_HUNT`, unset = active; Breakout's `OT_BREAKOUT` is no longer read, dormant r110); PARK keeps `OT_PARK` trade/log/off. Unset, every plan is in
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
Other single legs: **25%** (`MAX_LOSS_PCT`). (The butterfly stop constant was deleted at r115; nothing had read it
since r107 removed the butterfly exits.) Every other exit rule lives in `strategy/management.py` and
`execution/exit_engine.py`, not in a number that can be quoted here.

**The fill observers (r270, PMAP.1 + FILL.2).** Every open single long gets a premium-map row a minute, and the
end-of-tick sleep records when its own quote crosses its premium stop (data/counterfactual/). `OT_FILL_OBSERVE=off` turns
the recording off. **The floor watch (r280, EXIT.5) WAKES THE TICK:** a Breakout or Runaway whose own quote (at most 4 s
old) is at or below its enforced premium stop ends the 15 s wait and the tick runs at once; the tick still decides. Nothing here exits or orders. `OT_FLOOR_WATCH=trade|log|off`, unset = trade.

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
loss cap (`OT_DAILY_LOSS_LIMIT`, else the box's `OT_RISK_USD`), and it re-arms if the day recovers (r162).
Every strategy counts and every strategy is refused, PARK and OGAP included (r137 CAP.10; they sat outside
the cap from r288 / OGAP.1 to r136).

---

## How to read this

Each spec declares its gates in three categories (WA §36):

| category | meaning | relaxable |
|---|---|---|
| **SELECTION** | a measured preference. Loosening gives a *worse example of the same trade* — which is what a debug session wants. | **yes** |
| **FOUNDATIONAL** | defines the setup's **identity**. Relax it and this is not that trade. **A gate can be perfectly winnable and still be foundational.** | never |
| **FEASIBILITY** | the trade cannot win, however good it looks. | never |

⚠️ **The relaxed toggle is NO LONGER ON `configure.sh` (removed r127, operator: *"we don't do
relaxed entries here"*). Item 7 was r97's pin-proximity gate until r68, which fixed the gate ON
with no item (the operator, 2026-10-31: *"7. Pin gate, default "on" —remove from the menu"*).** `OT_RELAXED_ENTRY=1` in the unit
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

## 5. Iron Condor — `iron_condor_strategy.py` + `condor_roll.py`

**The most intricate spec in the book, and the one where the overlay and the
structure agree on when the thesis died.**

### Status, 2026-08-20: a NICE-TO-HAVE anchored to a rare premise

Operator: *"Anchor to the rare fork premise and if it gets us a surprise fill
now and then we can study it."*

**ENTRY DORMANT since OTV4TEST r249: condor management and the roll only; no condor is opened.**
`strategy/plan_state.py` marks IronCondorStrategy DORMANT ("no entry of its own (r249)"), `config.ENTRY_WINDOWS`
has no condor key, and `main.py` instantiates it for `manage` / `authorize` only. The text below is the trade's
design, kept for the record; nothing in it fires.

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
  **The grid is the UNDERLYING's** (r132 TICK.3): the venue rule is cached
  under the underlying, so entries and exits both resolve it with INSTRUMENT;
  the walk's KEY may still name the contract.
· **RUNG AFTER RUNG, ~6 s APART, INSIDE ONE TICK** (r133 D2; the operator,
  2026-11-20: *"If the ladder was fast enough to update every 5 seconds, I would
  prefer that"*). Live, a rung rests ~5 s (2 s polls), is cancelled and READ
  DEAD, and the next rung is priced on the re-read streamed quote and posted at
  once — cancel-confirm-post, never a replace. The call hands back to the tick on
  a fill (a fill in the cancel race is booked once), the mark rung refused (the
  next tick re-offers it), a rejection, the strategy's entry window ending (the
  walk is cleared), no fresh quote, an unconfirmed cancel (the order guard holds
  the intent), or one tick's budget (15 s: no rung starts whose rest would end
  past it). Paper is unchanged (it books the mark at once).
· **THE CONTRACT IS FROZEN FOR THE WALK** (r133 D3): a strategy that re-picks its
  strike mid-walk is put back on the contract it is walking before sizing; the
  freeze lapses on a fill, the window's end, or 45 s with no rung posted. A
  restart loses the walk and the freeze (in memory); the boot sweep still
  cancels a working rung.
· **ONE UNKNOWN ORDER HOLDS THE WHOLE INSTRUMENT** (r135 GUARD.1; the operator,
  2026-11-20: *"Yes, let's fix it smartly."*). An opening order whose fate is
  unknown — a cancel that could not be confirmed, a place_order whose reply was
  lost, or an order FILLED whose fills could not be read — refuses EVERY opening
  post on the box (any strategy, any strike) until it is resolved; closes, stops
  and the 15:55 flatten never wait on it. It is read from the broker on every
  tick (and before every rung): dead with no fill clears it; a fill, whole or the
  PARTIAL an unconfirmed cancel leaves, is booked ONCE as the originating
  strategy's trade (its stop, trail and target) at the broker's fills and
  quantity, then clears; still working, the cancel is re-sent (at most 3, 5 s
  apart). An order already on a trade row is never booked again, and the
  intraday adopt waits for the booking. Unresolved after 120 s (or at all once
  the day's last entry window, PARK's 11:03, is 120 s behind) it pages once,
  the block stays, and reconcile adopts the position (ADOPTED) for the stop and
  the flatten. A restart forgets it; the boot sweep then cancels every untracked
  working order and blocks entries until each reads dead, and the boot reconcile
  adopts any fill.
· A refusal is *"didn't completely fill at that price"* —
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

### A live close that has started finishes (r138, EXIT.11-13)

The operator, 2026-11-21: *"I don't want partial opens or partial closes to be the norm."*
· **An unreadable read posts nothing.** A pass that resumes a kept close order and
  cannot read it (429, timeout, 5xx, any error) keeps the order id, posts nothing,
  pages once and re-reads it next pass. Before r138 it dropped the id and posted a
  second full close beside the live one.
· **…but never past the end-of-day close (EXIT.14).** Once the EOD close drives the
  position (15:45 assignment risk, 15:50 everything else, the 15:55 cross) the
  unreadable order no longer decides: the broker's book is read, every working
  order on the contract is cancelled and confirmed dead, the kept order's fills are
  taken from the book (filled there: booked once, nothing posted), and the
  broker-held remainder is closed on the EOD path, so the 15:55 cross still happens
  (an unclosed ITM long would auto-exercise). Never more than the broker holds;
  holding none, nothing posts and it pages. Book unreadable too: nothing posts, page.
· **FILLED with unreadable fills is not a miss.** The order id is kept (in the row
  too); each later pass re-reads that order's fills and books them once when they
  read, paging once. Before r138 the next pass sold again on a closed position.
· **A started close finishes.** While a position holds partial-close fills or a kept
  close order (working, a lost reply, unread fills), it keeps closing under its LAST
  exit reason, with that reason's ladder and stop escalation, until flat, even when
  the trigger that started it flips back (PARK's mark back above the lock floor, the
  delta back above its floor). The reason is kept in the row's `live_exit_state`
  beside the fills, so a restart mid-close finishes it the same way. A trigger that
  still says exit decides as before. Live only; paper fills whole at the mark.

### The live close does what the spec says (r139, EXIT.15-18)

· **The stop counts its own attempts (EXIT.15).** The spec: the mark, the mark, then
  the bid (`LIVE_STOP_AT_BID_AFTER` = 2), then MARKET (`LIVE_STOP_MARKET_AFTER` = 3).
  An attempt counts when it did not close the position (unfilled, partial, rejected,
  refused by the broker) and only under a floor-policy reason (a stop). A lock exit's
  or a target's walk never counts toward a stop. A different exit reason starts the
  count again (the P&L a reason carries each tick does not make it a different
  reason); the same reason continues it, a restart included (`live_exit_state`).
· **The price is the store's newest (EXIT.17).** Just before a close posts, its legs
  are re-read from the feed store (local, no broker call) and it posts at that mark,
  not at a copy taken earlier in the tick; the quote's own age is logged on the post
  line. The feed sends a quote only when it changes, so a quiet quote is still the
  current quote and is used. Only a quote past the feed's own staleness rule
  (`OT_CHAIN_STALE_S`, 120 s, the rule the chain already applies) goes as a close
  with no mark does (before the 15:55 cross nothing posts, one page, it retries each
  tick; at the cross it crosses).
· **A refusal is a refusal (EXIT.16).** A broker error the SDK could read (a 4xx
  "code: message") means nothing is working: the reason pages once, the rung is
  refused, the next pass re-prices. A timeout, a connection error, a 5xx or an
  unreadable reply is still a lost reply (the broker's book is read before anything
  posts). Entries keep their own rule: any raise there is an unknown order.
· **A cancel that lost to a fill books at once (EXIT.18).** When the deadline cancel
  raises, the order is read once; filled (or dead) it is settled in that pass, with no
  "UNFILLED" page.

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

**DORMANT from 2026-11-16 (OTV5 r110, WS.3 TRIM; the operator, 2026-11-14: "Concur").** Never asked, writes nothing,
no switch; the code below is kept for a revisit, and its trades to 2026-11-13 are window history.

**Written 2026-10-03 (OTV4TEST r227) from the code as it runs. ON until r110.**

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
It sizes on that geometry (`sizes_on_geometry`), always scaled (the ramp; r68 fixed it ON, no key).

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
   once; the mark ladder), and every cut is recorded in `data/counterfactual/breakout_no_progress.jsonl`.
   It always trades (r68: no key; the operator, 2026-10-31: *"Trade it—I don't want this toggled"*).
   Operator, 2026-10-10: *"Yes, to all. Study, fit & apply."*
4. `exhaustion` - a new favourable extreme on WEAKER 5m momentum. This is the trade's
   real exit: it has no target.
5. the exit engine's trail, as a floor under the trade, and the close schedule in section 0.

**Open:** the dials are unfitted (BRK.5); no exit candidate beat this stack on 266 days.

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
- **on an equity only** (not `config.PARK_INDEXES`, SPX and QQQ - an index never asks; r72 PARK.5, the
  operator 2026-11-03: "add a gate in the code 'is an index=false' and start trading it Monday"): the
  PAIR - QQQ's own first hour moved >= 0.20% the same way - and the COMMITMENT - fewer than 2 of three
  leans against on the name AND on QQQ, read in the name's direction: the 09:30 open not beyond
  yesterday's high (a long) / low (a short); the 10:00-10:59 bar's wick against the move >= 0.50 of its
  range; 09:30-10:59 volume below the prior 5 sessions' median (a ratio outside 1/3..3 is unknown, not
  against). A tape too thin to read on either name is no trade (STARVED, fails closed). Each equity box
  subscribes QQQ's 1m bars on its own feed session. Measured on PARK's 197 real-quote equity fires
  08-25..11-02: kept 27 +$13,596, skipped 170 -$11,668, both halves; on the indexes it would have skipped
  3 of the top-5 runners, so it is not applied there. From 10:00 the box watches both tapes: the first
  gap is paged (once), the candle feed re-pulls a short tape on its own session (and once more after the
  10:59 bar closes), and the 11:01-11:03 window re-reads every tick - only a tape still short then is no
  trade, paged as FAILED CLOSED. QQQ's 1m bars are a health row on the equity box's manifold (RED in RTH
  from 09:31 when missing or stale), and never leave the box (the warehouse push ships only the box's own
  symbol);
- the strike nearest the 11:00 1m close, today's expiry, two-sided, ask >= 0.50, bought AT THE MARK
  ((bid + ask) / 2, floored to the cent; r60 PARK.4, the operator 2026-10-30: "we ladder in from
  aggressive to mark & never worse than mark"). Paper books the mark; live walks the entry ladder from
  25% in off the bid toward the mark, one increment a tick, never above it - unfilled by 11:03 is no trade;
- sized flat on the box's own risk, floor(OT_RISK_USD / (mark x 100)) - `config.RISK_PER_TRADE_USD`, set per box
  by configure item 2 (an unaffordable contract is no trade: AMD 11-03/11-05 at $1,050). No scaling, no pin-proximity gate (PIN_EXEMPT); what the gate would have said is a
  counterfactual row on every PARK entry, `data/counterfactual/pin_gate.jsonl`.

**Under the cap (r137 CAP.10).** PARK's closes count toward the daily catastrophic cap and, once it is hit,
the 11:01 entry is refused like any other (it was cap-exempt and outside the cap's day P&L from r288 to
r136). So a morning loss at or past the limit means no PARK that day unless closes bring the day back under.

**Exits, first match wins (`exit_engine._evaluate_park`):** the lock, on the MARK (r137 LOCK.1; r288-r136 it
walked the bid) - armed once the mark reaches +60% of the booked entry, out when the mark falls to +20% (after
a restart the persisted best mark, `max_premium_seen`, re-arms it once - r291, now the same basis); the delta floor - |delta| <= 0.30 from 11:30 (unread delta
holds); the close at 15:45. No premium stop, no trail. Every exit writes
`data/counterfactual/park_exit.jsonl` so Saturday prices what holding to 15:45 would have done.

**LOG ONLY, never deciding (OTV5 r90, SHADOW.1).** Every PARK tick that reached a direction records the daily SMA 50
slope's verdict (keep / would_skip / unknown) as plan_check `shadow_park_sma50` - the S4 equity pick, logged by the
operator's order (2026-11-08) though it failed blind. The Hunt records the opening-range / EM verdict on each fire as
`shadow_hunt_or_em`. `tools/shadow_rule_status.py --fleet` proves both are writing.

**Measured** (read-only, 2026-10-17; fit week 10-12..16 reported separately): QQQ 41 days n11
+10,550 at $1,050 (+1,590 without the fit week); SPX 39 days n14 +13,320 at $2,500. PARK.X (picks
sha 85dca420): the delta floor +11,786 on QQQ, +16,370 on SPX, every winner kept; take-profit and
time exits cut the big days. Small n: the book rests on two or three days a month.

## 10. OGAP — `ogap.py` (the spec) + `ogap_plan.py` (the plan)

**OTV5 OGAP.1, 2026-11-14.** Park's friend's ORB-GAP (his spec of record 2026-11-13), a faithful PAPER copy: his
signal, sizing and exits, unchanged; only the plumbing is ours (`docs/OGAP_SPEC.md`). The operator, 2026-11-14: *"let's
design & paper trade the OGAP on QQQ"*. **QQQ only** (`config.OGAP_SYMBOLS`): his rule run unchanged on every fleet
symbol failed the sealed bar on the equities (`~/reviews/studies/ogap_equities_20261113`: T1 −$96/row [−160, −22]) and
SPX is refused by his $5.00 ask band on every row; every other box writes one `ogap_not_this_symbol` row a day.

**Entry, once per session, 09:46-10:32 ET:**
- the range: the 09:30-09:44 1m bars, at least 10 of them, W = high − low > 0;
- gate-G: gap = (09:30 open − the prior RTH close) / W; |gap| >= 0.25: only the gap's side (up = calls, down = puts),
  else both; an unreadable gap fails open. A retest on the refused side is a SHADOW (`ogap_shadow.jsonl`, the
  `ogap_gateg_shadow` check row), never traded, never blocking, never in EV;
- the break: per side, the first 1m CLOSE strictly beyond the range, 09:45-10:30; it never re-arms;
- the retest: within the 20 bars after the break (and by 10:30): a call's low <= high + 0.10W closing above the high
  (a put mirrored). The earliest allowed retest is the signal bar; the fill is the NEXT minute or never (`ogap_stale`);
- the contract: today's expiry only (`ogap_no_0dte`), the strike nearest the fill-minute open (a tie goes lower), a
  two-sided quote; **every price below is the MARK** (the mid, floored to the cent) since r136 (OGAP.3; Park's book
  reads the ask): mark >= $0.50 (`ogap_ask_floor`, the name kept), contracts = floor(`RISK_PER_TRADE_USD` / (mark x
  100)), the ramp MIN (r131; a mark over `RISK_PER_TRADE_USD` / 100, $10.50 at $1,050, buys none: `ogap_ask_band`).
  The mark is booked (paper fills at it; live goes through the entry ladder, never worse than the mark); the ask and
  the bid stay on the row and in notes as record only. The operator, 2026-11-20: *"Ours needs the modification to
  account for how I would trade it, never pay the spread."*

**Exits (`exit_engine._evaluate_ogap`), on the MARK against the booked fill (`entry_premium`; r136, Park's book reads
the bid against the ask), first match wins:** peak (the best mark) >= 2.0x -> floor 0.60 x peak (ratchets); peak >=
1.6x -> floor 1.2x; mark <= floor sells (`ogap_trail` / `ogap_lock`); the first tick at or after 14:00, if the peak
never reached 1.6x and the mark is under 0.75x, sells (`ogap_sweep_1400`); 15:45 sells (`ogap_close_1545`); the EOD
schedule is only a backstop. The close goes out through the normal path (paper at the mark, live exit-at-mark). No
stop before 1.6x, no take-profit, no decay stop, no management plan, no pin gate (PIN_EXEMPT, the counterfactual row
still written). Under the daily catastrophic cap both ways (r137 CAP.10; cap-exempt and out of the cap's day P&L
from OGAP.1 to r136). One look per tick (his book looks once a minute): every exit
is written to `ogap_exit.jsonl` with the deciding mark, the tick bid beside it, the fill, the floor and the peak. A
restart seeds the peak from the persisted best mark once (now the walk's own basis).

**Measured** (`~/reviews/studies/park_orbgap_20261113`): QQQ T1 real quotes n=7 +$148/row [−124, +454]; T2 n=32
+$137 [−87, +421]. Gate `tests/check_ogap.py` (O1-O11 and the five-day replay R1-R5, which reproduces his backtest's
QQQ rows on 10-30, 11-02, 11-04, 11-05 and 11-09 to the dollar, fed his ask / bid series through the pure walk);
`tests/check_ogap_mark.py` (M1-M14, r136) pins every mark-basis read.

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
