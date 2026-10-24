# FORK BRIEF — implement PLAN_SPEC §10 on an isolated instance

> 🔴 **SUPERSEDED SNAPSHOT (marked 2026-10-03, OTV4TEST r226).** Kept for the record it is; it does not describe this fork as it runs. Current state: `docs/TRADES.md` §0 (roster), `docs/BACKLOG.md` (work), `docs/GENESIS-TEST.md` (ledger).

**For:** Fable
**From:** the 2026-09-08 session, options_trader_v4 @ `ac3f1d8` (r321)
**Status of every claim here:** read from the repo at that revision, or quoted
from the operator in this session. Nothing is inferred from behaviour.

---

## 0. THE ONE-LINE VERSION

`PLAN_SPEC.md` §10 already specifies the architecture the operator wants. The
code does not implement it. **This is not a design task — it is an
implementation task against a spec written on 2026-08-27 and confirmed then.**
Your job is to rewire the strategies to §10 one at a time, on a segregated box,
and prove each one can fire.

---

## 1. WHAT §10 SAYS, VERBATIM

> Operator, 2026-08-27, read back and confirmed: the plan *"evaluates the
> current tick what would need to be true on the next tick for the active
> strategies to execute. That means strike selection, wing width, stop
> placement (for r-value), minimum r-value acceptable for entry."* The strategy
> *"execute[s] the transaction with the variables selected by the plan."*
>
> **The strategy holds no chain and picks no strike.**

## 2. WHAT THE CODE ACTUALLY DOES — MEASURED, NOT ASSUMED

The direction is inverted at every step. Evidence at `ac3f1d8`:

| claim | reality |
|---|---|
| plan selects strikes | `strategy/plan.py::credit_spread()` docstring: *"A credit vertical the strategy has already selected."* It computes R from a structure handed to it. |
| plan searches the chain | `search_wing()` is called from exactly ONE place in shipping code — `strategy/sweep_credit_spread.py:1137`. A strategy. |
| strategy holds no chain | every strategy takes `chain=` and picks its own short strike |
| plan passes trigger variables | no such mechanism exists; each strategy holds its own trigger |

**What the plan does own today:** the R verdict (`plan.py:108` →
`criteria.r_verdict()`), the invalidation anchor, and the row. Evaluation and
evidence — not construction.

⚠️ **The failure that motivated §10 is in PLAN_SPEC §0 and is worth reading
before you start.** 2026-08-25, TSLA: price ran 351.4 → 356.86 between ~11:35
and 13:00 ET. `TrendCreditSpread` evaluated 182 times and produced one signal;
`TrendCS2nd` signalled on 207 of 218 looks and traded nothing. Cause: **only
`ORBStrategy` ever called `open_plan`.** Everything else was deciding without
declaring. That is the class of failure this fork exists to make impossible.

## 3. THE TARGET, INCLUDING WHAT THE OPERATOR ADDED ON 2026-09-08

§10 plus five clarifications given this session. Quotes are his.

**3.1 The strategy is a spec, not a procedure.**
> *"The strategy is simply do this when the nexus of x, y, z are 'this' and the
> purpose of the plan is to identify and pass to it the strikes and geometry
> that would satisfy the strategy's basic requirements."*

**3.2 The plan SEARCHES; it does not validate.**
> *"The plan's job is to 'find' a working setup on the incoming chain that would
> clear the bars set by the strategy."*

This is the largest single change. `search_wing` already searches — but
downstream of a short strike the strategy fixed, with the bar (`R_FLOOR`)
embedded in the search. Under §10 the search runs across the whole structure,
from the plan, over strikes the strategy never names.

**3.3 EVERY BAR LIVES IN THE STRATEGY.**
> *"Any bar to fire should live in strategy & the plan should be searching for
> opportunities where the bar 'could' clear."*

Consequence: the plan returns **candidates plus their measurements** (structure,
R, wing width, stop distance, geometry). The strategy compares those to its
bars. The search may READ the bars to prune — a search with no acceptance
criterion is unbounded — but it may not HOLD one. One owner, one copy.

⚠️ This means bars must be **declared values the search can read**, not code the
strategy runs. That is the single most important design consequence in this
document.

**3.4 The plan tracks the NEAREST candidate.**
> *"The plan should be tracking its 'nearest' potential opportunity to clear the
> bars."*

A maintained best-candidate-so-far with **per-bar distance**, updated as the
chain moves. ⚠️ **"Nearest" is only well-defined per bar.** If R is short 0.13,
the wing is two strikes narrow and the stop sits inside the spread, collapsing
that into one scalar requires a weighting nobody chose — that is exactly the
silent-default class this repo has been burned by repeatedly (`relaxed_earliest`
09:45, three times). Keep it a vector: per bar, measured value and gap.

**3.5 Observe continuously, plan inside the window.**
> *"Observe the entire session… But actively 'plan' when its own session window
> opens up."*

Windows at `ac3f1d8` (measured):

| book | window |
|---|---|
| debit (ORB, runaway) | to 11:30 |
| credit (sweep, TCS, condor) | 11:31 – 14:00 |
| butterfly | 12:00 – 15:00 |

Only 12:00–14:00 has real overlap, so at most two chain searches are live at
once. Some specs need state built long before their window — ORB's range from
the open, the butterfly's pin development, the runaway's impulsive candle — so
**observation is continuous from the open; chain search and candidate tracking
start when the window opens.** A window bounds acting, not watching.

**3.6 Character.**
Operator: character is being turned on soon. Under 3.3 it can only enter as **a
bar a spec declares** — never as private acceptance logic inside the search.
Machinery already exists: `character_ledger` is in `NEVER_PURGE`,
`character_axis_sample` got a 20-day horizon at r270. The consumer is what is
missing. Do not build it in this fork; do not design the search in a way that
forecloses it.

## 4. THE PLAN LEDGER VOCABULARY

Operator: *"I'm ok with a plan ledger stating plainly 'none available' or
'decline' or 'setup selected'."* Map onto §10's existing row types:

| state | means | carries |
|---|---|---|
| **none available** | the plan searched, the chain could not produce a candidate | nothing further needed — this is a fact about the market |
| **decline** | a candidate existed, a bar refused it | **the bar's name and the measured gap** — without these the row is as opaque as today's refusal |
| **setup selected** | a structure clears every bar; only the trigger remains | the exact structure and the trigger being waited on |

⚠️ **Keep `starved` as a fourth state.** "No chain arrived" and "the chain had
nothing" look identical in a report and mean opposite things about whether the
box is healthy. On 2026-09-08 the fleet's whole shadow corpus was empty and it
took an hour to establish that the difference was *nothing was looking*, not
*nothing was there*.

## 5. HOW IT RUNS — ISOLATED, OFF CONTROL

Decided by the operator this session. **The fork is invisible to control by
construction, not by convention.**

- **No EC2 `Name` tag.** `day_trader_pro/instance_registry.py` maps symbol →
  instance by the `Name` tag and has an explicit AMBIGUOUS path when two share
  one. Untagged means no `fleet run`, no deploy fan-out, no EOD conductor, no
  parity check, no shadow guard ever reaches it.
- **S3 push timer disabled.** Nothing enters the warehouse. The fleet's
  `dt=/sym=` prefixes and the push ledger's per-prefix counters stay coherent —
  two writers into one `sym=QQQ` prefix would corrupt `--verify` itself.
- **Retention purge left ON.** ⚠️ Purge is **time-based and does not check
  whether anything was ever pushed** — its header states the assumption plainly
  (*"S3 is the durable home"*), which is false on this box. `plan_tick` and
  `plan_check` age out at 7 days. **The operator has accepted this:** he is
  watching daily and keeping nothing. Do not build an export job.
- **Its own Telegram channel, or none.** The fleet channel is an emergency
  services channel; fork noise there trains him to ignore it.
- **Relaxed entry may be ON here.** It is paper-only by construction and the box
  is segregated, so it contaminates nothing — and it gets you fires quickly,
  which is the point. Note the fleet retires relaxed after 2026-09-11; that
  decision does not bind this box.
- **Same symbol as a fleet box (QQQ).** This is deliberate: identical tape makes
  the mainline box a matched control. A unique symbol would destroy that.

⚠️ **What isolation costs, stated once:** excluded from the fleet means excluded
from the bake and the EOD chain. Check whether purge on that box runs from the
conductor or a local timer — untagging removes the conductor's reach, so if
purge is conductor-driven you get unbounded growth on a ~6.7 G volume instead of
the purge the operator asked for. Disk is the binding constraint fleet-wide.

⚠️ **And expect mainline fixes to land twice.** The SMC fork precedent: it found
a P0 `ctx` NameError present at mainline HEAD, so segregation isolated the
experiment *and* delayed a fix the fleet needed. Budget for a re-port at merge.

## 6. THE PURPOSE, AND THEREFORE THE ACCEPTANCE TEST

Operator: *"The only purpose for the isolated instance is to confirm that the
TRADES are capable of firing."*

Not P&L. Not fitting. **Can it fire, on what plan, and if never — which bar.**

⚠️ **The cheap false positive to guard against:** the rewired trade fires
because the rewiring dropped a gate, not because the plan found a valid
structure. So the daily read is the fire **plus its plan row** — same bars
cleared, same terminal — never the Telegram entry alert alone.
`plan_ledger` and `gate_disposition` are in `NEVER_PURGE`, so that evidence
survives on the box regardless of the 7-day horizons.

**A null result is a real result.** Defect W in the continuation strategy could
never fire, structurally, and nobody noticed. Two weeks of `none available`
under relaxed is a finding — the bars are unreachable on real chains — and it is
readable from the ledger without a single trade.

**Before P&L, prove mechanism parity.** For each rewired trade: given the same
recorded tick, does the plan-driven version select the structure the
strategy-driven version chose? That needs a harness and zero trades. Divergences
are then either defects or deliberate improvements you can name. With a capped
strategy like the butterfly (one per session, r179), P&L alone would take months
to say anything.

## 7. ORDER OF WORK

⚠️ **AMENDED 2026-09-08 (OTV4TEST r2), operator's ruling: ORB FIRST, ONE
TRADE AT A TIME.** *"Slow down. Start with 1 trade spec at a time. We will
sort through it and the associated plan to untangle it together, and discuss
no other plans/strategies until we reach a point where they must interact. The
ORB trade is almost purely mechanical, so that is a good place to start."* The
spec and its plan are AGREED WITH THE OPERATOR BEFORE ANY CODE (PLAN_SPEC §29
is the first). The vocabulary in item 1 is written per trade as each is
untangled, not up front. Items 2–3 below record the brief's original proposal
and are superseded by that ruling; item 4 stands.

1. **Write the spec vocabulary first.** What a spec may declare: level roles,
   structure shapes, trigger events, economic floors, and (later) character
   axes. This is the contract the plan implements against. Get it wrong and each
   strategy grows its own dialect, which is how the current duplication
   happened. `docs/PLAN_SPEC.md` is at v1.23 / 28 sections — extend it, do not
   start a new document. Read §10, §27 (ORB firing sequence as gate) and §28
   (butterfly wing is searched) first; `tests/cascade_harness.py` already exists.
2. **Runaway first.** Simplest geometry, and the only strategy left with a
   muteable R hurdle (`runaway_continuation.py:533` is the sole live
   `t.executable()` call).
3. **Sweep last of the credit book.** It is the one carrying `search_wing`
   inside itself — the hardest boundary to move and the best final proof.
4. One at a time. Each proves "capable of firing" in isolation before the next
   begins.

## 8. WHAT NOT TO DO

- **Do not touch mainline.** This fork does not land to `TX-9AI/options_trader_v4`.
- **Do not tag the box, enable the pusher, or point it at the fleet bucket.**
- **Do not invent a bar.** If the search needs a bound the spec does not
  declare, that is a question for the operator, not a default. This repo's
  recurring defect is the unchosen default: `relaxed_earliest` 09:45 fired four
  butterflies at 09:45 on 08-31 (r196), survived in the sweep until r321, and
  `SWEEP_CS_LATEST_ET` was a `getattr` default with no config key until r317.
- **Do not let a decline be opaque.** A refusal with no named bar and no gap is
  the thing being replaced.
- **Do not reason from code to what happened.** Code says what should happen;
  the ledger and the tape say what did. When they disagree, the record wins.

---

## APPENDIX — verified facts this brief rests on

All at `ac3f1d8` unless noted.

- `strategy/plan.py::credit_spread()` — *"a credit vertical the strategy has
  already selected"*
- `search_wing()` called from `strategy/sweep_credit_spread.py:1137` only
- `plan.py:108` — `t.executable()`, the R hurdle, strict/relaxed aware
- `runaway_continuation.py:533` — the only other live `executable()` call
- windows: debit → 11:30; credit 11:31–14:00 (`CREDIT_ENTRY_START_ET` /
  `CREDIT_ENTRY_END_ET`); butterfly 12:00–15:00
- `retention_purge.py` — `plan_tick` 7 days, `plan_check` 7 days; `NEVER_PURGE`
  holds `plan_ledger`, `gate_disposition`, `strategy_note`, `fire_snapshot`,
  `character_ledger`, `level_ledger`; no push-confirmation gate anywhere in
  `purge()`
- `instance_registry.py` — symbol → instance by `Name` tag, with an AMBIGUOUS
  path for duplicates
- `warehouse/s3_push.py` — `dt=/sym=` prefixes; `own_symbol()` reads the OHLC
  basename off disk, not `OT_INSTRUMENT`
- relaxed at `ac3f1d8`: R hurdle muted (runaway only); sweep pierce ceiling
  0.25 % → 0.75 %; sweep window pinned strict at r321; butterfly moves
  `LATEST_ET` only
- `criteria.get()` has **no production callers** — the table is documentation,
  not a router (DOC.22, open)
