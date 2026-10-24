# OTV5 — Autonomous Day Trading Bot with Telegram Notifications and embedded Claude Code agent

**`README.md` v1.0 · 2026-10-24 (OTV5 r0) — what this repo is, how it is laid out, how work lands.**

**What this is.** One box trades one underlying (equity options, or SPX/SPXW for the
index) on the Tastytrade platform, intraday only, flat by the bell. A candle feed
writes the tape; **plans** read the tape and the chain and work out, ahead of time,
the nearest setup that would clear their strategy's bars; **strategies** fire when
price action satisfies a plan's completed vectors, and the exit engine manages the
position to its stop, its target or the close. Every decision — taken, refused, or
waiting — is recorded with the inputs it was made on, and every box pushes its
records to one warehouse (S3) for study. Telegram carries the alerts. A Claude Code
agent runs on the box with a read-only brief (`docs/FIRST_BOOT.md`) and can be
raised from the box menu.

**The layering.** Information layers off the feed (IL1 primary: candles, quotes,
prints, the chain; IL2 derived: levels, the surface, forks, anchors) → a decision
layer where each plan searches the chain and the levels for the nearest setup
that would clear the strategy's bars → an execution layer where the strategy
fires when price action satisfies the plan's completed vectors. A strategy holds
no chain and picks no strike. The specs are `docs/PLAN_SPEC.md`; the roster as
it runs is `docs/TRADES.md` §0 (pinned to `config.py` by a check).

## The trades

| trade | state | plan | strategy | spec |
|---|---|---|---|---|
| Runaway (momentum) | ON | `strategy/runaway_plan.py` | `strategy/runaway_continuation.py` | PLAN_SPEC §30 |
| Breakout | ON | `strategy/breakout_plan.py` | `strategy/breakout.py` (the spec) | TRADES §7 |
| Liquidity hunt | ON | `strategy/liquidity_hunt.py` | same file | PLAN_SPEC §37 |
| ORCS (opening range credit spread) | ON, paper only | `strategy/orcs_plan.py` | `strategy/orcs.py` | PLAN_SPEC §41 |
| GEX pin butterfly | ON | inside `strategy/gex_pin_butterfly.py` | same file | PLAN_SPEC §32 |
| ATP butterfly | off (`OT_ATP_BUTTERFLY=1`) | `strategy/atp_butterfly_plan.py` | same file | PLAN_SPEC §39 |
| VOLT | off (`OT_VOLT=1`) | `strategy/volt_plan.py` | `strategy/volt_strategy.py` | TRADES §8 |
| ORB break + retest | retired (`OT_ORB_TRADE=1`); the opening-range ENGINE stays | `strategy/orb_plan.py` | `strategy/orb_strategy.py` | PLAN_SPEC §29 |
| Sweep credit spread | retired (`OT_SWEEP_CS=1`) | `strategy/sweep_plan.py` | `strategy/sweep_credit_spread.py` | PLAN_SPEC §31 |
| Trend credit spread | retired (`OT_TCS_ACTIVE=1`) | `strategy/tcs_plan.py` | `strategy/trend_credit_spread.py` | PLAN_SPEC §34 |
| Condor (a management plan, not an entry) | moot while both credit entries are retired | `strategy/iron_condor_strategy.py::manage` + `strategy/condor_roll.py` | | PLAN_SPEC §35 |

Two primitives the plans share: **the rejection fact** (`derived/levels.py` emits
WICKED / REJECTED / ACCEPTED on closed 1m bars for every live level, the 1h tines
included; §30.1) and **the handoff grant** (`execution/handoff.py`; §37.2). Anchors —
derivatives recorded on every plan row, never decided on — are §36. Every reader of
a derived table judges a row by **market time** (the bar it closed on, the quote it
was taken at), never by the wall clock it was written at, so a store primed from
the warehouse is read exactly like one the box wrote itself.

## Installing a box

`bootstrap.example.sh` → `deploy/install.sh` → `setup_ec2.sh`, unattended. The
repository a box installs from is named in **one place**, `deploy/origin.conf`
(two pinned copies run before any clone exists; `tests/check_origin.py` keeps the
three equal and proves the URL actually cloned). The install leaves the trading
services **installed and stopped**, and the warehouse push **off**. The operator
then runs `configure.sh`: symbol, risk, the switches; **Done** primes the ramp from
the warehouse (`tools/prime_ramp.py`: the 1m tape, the higher timeframes built from
it, the daily bars from the study corpus), refuses to start if priming fails,
starts the feed and the bot, and turns the push on only if the symbol is not
already pushed by another box (`tools/capture_guard.py`, a live read of the
warehouse). A symbol switch drains the old symbol's rows under the old label before
the new one is primed.

## Layout

```
main.py            the bot (systemd: optionsbot)        config.py        every declared value
status.py  query.py  configure.sh                       the three the operator runs by hand
devtools.sh        the box menu (registry-rendered)      setup_ec2.sh     first-boot provisioning
push.sh  pull_today_ohlc.sh  bootstrap.example.sh        requirements.txt floors for a fresh venv
analysis/  data/  database/  derived/  execution/  notifications/  risk/
strategy/          plans and strategies                  utils/  warehouse/
tools/             land.sh (the lander), prime_ramp, capture_guard, boot_sweep, agent_watch,
                   last_session, readers (eod_summary, debug_status, plan_board) and probes
deploy/            systemd units and their installers, origin.conf, snapshot, the fleet push
tests/             hypotheticals — every check_*.py drives real code on hand-built ticks
docs/              PLAN_SPEC · TRADES · WORKING_AGREEMENT · GENESIS (the ledger, from r0)
                   · BACKLOG · FILE_MAP · WRITE_MAP (both generated) · ENV (generated)
                   · FEED_MANIFOLD · DERIVED_STORES · ENGINE_FEED_REQUIREMENTS · FIRST_BOOT
```

## How work lands

Every revision is a tarball with a `land.spec` (`REPO` markers, `ORIGIN`, `BASE`,
`REV`, `DESC`, `POS`/`NEG` content assertions, `CHECK` lines). The box menu's
**LAND** runs the archive's own `land.sh`: base must match HEAD, content gate, every
CHECK (on scratch stores — a checker can never reach the live DB), maps regenerated,
a ledger row appended to `docs/GENESIS.md`, the discipline gate, commit, push.
**BAKE** pulls, proves the tree imports, restarts. Revisions are numbered from r0
(the seed) and cited by prefix outside this repo: `OTV5 r14`, never a bare `r14`.

The rules are `docs/WORKING_AGREEMENT.md`. The one that governs everything else: no
claim without a source — read, queried, told, or inferred, and said which.

## Reading a session

`query.py` (menu: query.py) — trades, then DECISIONS: one row per plan saying what
it is waiting on, or which bar refused it, or that it fired; plans outside their
window are hushed on the readers but recorded. `status.py` for the live position.
The sensors in the menu read the derived stores directly (plan rows, level events,
anchors). A NO PLAN or NOT ASKED for an in-window strategy is a wiring defect, not
a market fact.

---

## Changelog

**v1.0 — 2026-10-24 — OTV5 r0.** First version.
