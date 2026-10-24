# PORT_MANIFEST.md — OTV4TEST → options_trader_v4 — v0.8
v0.8  2026-09-12  OTV4TEST r16 — THE DIRECTION OF TRAVEL INVERTS, AND THE RANGE LABEL WAS
      WRONG. (1) v0.7 said the predecessor moved `r325→r364`; the first commit past the
      fork point is **r324**. The count of 37 is right. (2) **THE BACK-PORT IS LARGELY
      DONE AND THIS FILE DID NOT KNOW.** Mainline r324 is titled *"PORT.1: FIXES-ONLY
      PARITY WITH OTV4TEST"* and carried FIVE of the twelve defects below into the
      predecessor on 2026-09-09, with an explicit ruling naming the five it would NOT
      take so the control arm keeps behaving as it did at r322. (3) **ELEVEN of the 37
      touch the execution path**, and one of those (r364) this fork already absorbed at
      r15 — so the surface is ten, not thirty-seven. The CND commits r346/r348/r361 are
      docs-only and do NOT collide with the fork's condor rewrite; that was read off
      commit-subject prefixes on a first pass and is corrected here. (4) The traffic that
      matters now runs the OTHER WAY: mainline r340 is a defect this fork still carries
      (BACKLOG PRE.1). (5) Under the operator's 2026-09-12 ruling the supersede is IN
      PLACE — this box perfects the EXECUTION, mainline protects the INFRASTRUCTURE — so
      a fork-only store with no push stage on mainline is a handover item (PRE.3), not a
      job for this box.
v0.7  2026-09-12  OTV4TEST r15 — CORRECTION: the predecessor is NOT frozen (r325→r364, 37
      commits, under Claude Code on the controller). The back-port is a merge now;
      `derived/levels.py` is the first file both sides changed on purpose, and the
      fork took mainline's shape for it (levels v4.3 / forks v4.2) so otv5 inherits one.
v0.6  2026-09-11  OTV4TEST r14 — the root cleanup is LAYOUT, for otv5, not for the
      predecessor's fixes port: it moves 21 files and changes no behaviour.
v0.5  2026-09-10  OTV4TEST r13 — defect #12 (a checker's fixture landed as a live open
      position) and the structural fix: the lander's CHECKs run on scratch stores.
v0.4  2026-09-09  OTV4TEST r12 — anchors (record only) and HYG.1 closed; defect #8 fixed.
v0.3  2026-09-09  OTV4TEST r11 — the r11 rows (two-rung ladder, widened-wing roll, group floor).
v0.2  2026-09-09  OTV4TEST r10 — the r10 rows and the DEFECTS FOUND IN THE PREDECESSOR
      section (eleven, one still open) — port these whether or not the rulings port.
v0.1  2026-09-09  OTV4TEST r9 — opened. One line per file per revision, with the
      ruling it carries, so the back-port is a checklist and not archaeology.
      The predecessor is FROZEN at e955020 (r322) — checked 2026-09-09, zero
      commits since the fork — so the port is the fork's revisions applied
      forward in ledger order, not a three-way merge. Tests are half the port:
      every checker re-pointed here needs the same re-pointing on mainline.

Legend: **N** new file · **M** modified · **T** test (new or re-pointed) · **D** docs

| rev | file | kind | ruling / change |
|---|---|---|---|
| r2 | strategy/orb_plan.py | N | the ORB plan: both candidates from 09:35, stop = impulsive candle's extreme, strike at ±width, provisional size, four-state row |
| r2 | strategy/orb_strategy.py | M | the strategy is the spec; ATR floor deleted; fires with the plan's variables |
| r2 | analysis/orb_engine.py | M | stale 12-bar re-arm deleted |
| r2 | config.py | M | ORB_MAX_RETEST_BARS removed |
| r2 | execution/exit_engine.py | M | velocity stall off the ORB path |
| r2 | main.py | M | ORB asked every tick; afternoon NOT ASKED row gone |
| r2 | tests/check_orb_plan.py, check_atr_units, check_plan_signal, check_plan_wiring | T | new / re-pointed |
| r3 | derived/levels.py, data/derived_store.py, warehouse/retention_purge.py | M | the rejection fact: WICKED / REJECTED / ACCEPTED, level_event (never purged) |
| r3 | analysis/orb_engine.py | M | runaway invalidation is a close (fifty_accepted), acceptance tracked before the retest read |
| r3 | strategy/runaway_plan.py | N | arm on the accepted 50, strength once, band by strength, one per break any exit, re-validation on actual |
| r3 | strategy/runaway_continuation.py, database/trade_logger.py, main.py | M | strategy = bars + fire; any runaway exit finishes the break; session cap retired |
| r3 | execution/exit_engine.py | M | REJECTED handoff (ORB + runaway); runaway thesis-dead / fizzle / backstop; no premium stop |
| r3 | tests/check_level_rejection.py, check_runaway_plan.py, check_plan_prepares R-cases, check_runaway_handoff, check_signal_numeric_tail, check_orb_sequence | T | new / re-pointed |
| r4 | devtools.sh | M | box menu 2.0 (registry-rendered; sensors, R suite, land, bake) |
| r5 | derived/levels.py, derived/forks.py, derived/registry.py, data/derived_store.py | M | tines as levels (keyed on the tine, the tine rule), TRAVERSED inside the opening range, held-side close, live_levels() |
| r5 | strategy/sweep_plan.py | N | both sides from 09:35, short anchored on the level, fires on a fresh REJECTED |
| r5 | strategy/sweep_credit_spread.py, execution/exit_engine.py, database/trade_logger.py, main.py | M | strategy = bars + fire; breach accepted after the 15% stop; spent on acceptance only |
| r5 | tests/check_sweep_plan.py, check_plan_prepares S/T-cases, check_sweep_liveness, check_sweep_spread, check_level_rejection | T | new / re-pointed |
| r6 | strategy/gex_pin_butterfly.py, data/open_interest.py, strategy/plan.py, devtools.sh | M | best-R wing, smoothed persistence, OI starved input; OI fetch one loop; HYG.4 bound store; OI on Feed health |
| r6 | tests/check_plan_prepares B-cases, check_butterfly_* | T | re-pointed |
| r7 | query.py, devtools.sh | M | readers hush DORMANT (record whole) |
| r8 | strategy/trend_credit_spread.py, query.py, devtools.sh | M | TCS terminals on every path; NOT ASKED hushed; BAKE daemon-reload |
| r8 | tests/check_tcs_narrates.py | T | new |
| r9 | strategy/tcs_plan.py | N | session extreme ACCEPTED outside the frozen EM band; anchored on the level; widest wing clearing 1R; POP applied |
| r9 | strategy/trend_credit_spread.py, data/derived_store.py, execution/exit_engine.py, main.py | M | strategy = bars + fire; latest_event(); 15% lone-only; windows read from the plans (HYG.5) |
| r9 | tests/check_tcs_plan.py, check_tcs_fifty (retired into it), check_tcs_narrates, check_tcs_parked, check_plan_prepares | T | new / re-pointed |
| r2–r9 | docs/PLAN_SPEC.md §29–§34, docs/TRADES.md, docs/BACKLOG.md | D | the specs; the fork's own backlog |
| r10 | strategy/condor_roll.py, strategy/iron_condor_strategy.py, strategy/sweep_plan.py, execution/exit_engine.py, main.py | M | condor = management plan; tested by wick; the LONE row names its complement; entry retired; final-form floor from the structure as formed |
| r10 | tests/check_condor_mgmt.py | T | new |
| r11 | strategy/condor_roll.py, strategy/iron_condor_strategy.py, execution/exit_engine.py, database/trade_logger.py, strategy/sweep_plan.py, strategy/sweep_credit_spread.py, main.py | M | two-rung ladder: the roll widens its wing (iron fly at the limit), prepared every tick; tent and invert retired; group final-form floor (3 new trade columns); complement at least as rich as leg one; whipsaw named |
| r11 | tests/check_condor_mgmt.py R1–R6, check_plan_prepares M5 | T | new / re-derived |
| r12 | derived/anchors.py | N | record-only anchor reads (surface, VWAP, forks, tines, prints, OI) |
| r12 | strategy/orb_plan.py, runaway_plan.py, sweep_plan.py, tcs_plan.py, gex_pin_butterfly.py, iron_condor_strategy.py | M | anchors stamped on the row; runaway reads participation |
| r12 | analysis/trade_readiness.py | M | **FIX** — `_combine`/`momentum_val` dedented (defect #8) |
| r12 | tests/check_anchors.py | T | new |
| r12 | strategy/liquidity_hunt.py, execution/handoff.py | N | the hunt (bias from liquidity, A1/A2, known-runway strike) and the grant |
| r12 | execution/position_manager.py, execution/entry_engine.py, execution/exit_engine.py, main.py | M | the hunt never blocks; target-wick exit + grant; the sweep on a grant |
| r12 | tests/check_liquidity_hunt.py | T | new |
| r13 | config.py, tools/land.sh, tests/check_standing_offer.py | M | **FIX** — defect #12; CHECKs on scratch stores |
| r14 | 21 root files → tools/ and deploy/; requirements.txt; README.md; deploy/reinstall_timers.sh; devtools.sh | M/N | **LAYOUT** (otv5) — no behaviour change; not part of the fixes port |
| r15 | derived/levels.py, derived/forks.py, derived/registry.py, strategy/liquidity_hunt.py, strategy/sweep_plan.py | M | **PORTED FROM MAINLINE r364** (pools by side, tines at read, the board) — already on the predecessor; no back-port needed |

## DEFECTS FOUND IN THE PREDECESSOR (port these whether or not the rulings port)

| # | defect | where | fixed |
|---|---|---|---|
| 1 | TCS wrote no plan row on its common path — bare returns with the tick open; NOT ASKED all afternoon, every credit window (r238) | strategy/trend_credit_spread.py | r8 · ✅ **ON MAINLINE at r324** |
| 2 | TCS `POP ≥ 0.70` was a config constant nothing read | strategy/trend_credit_spread.py | r9 (applied in tcs_plan) |
| 3 | OI fetch lost the first batch of every cycle — "Event loop is closed", one `asyncio.run` per batch | data/open_interest.py | r6 · ✅ **ON MAINLINE at r324** |
| 4 | ORB invalidated on a WICK to the 50 while the runaway armed on a close+hold — the band owned by nobody | analysis/orb_engine.py | r3 |
| 5 | `finish_break` only on a LOSING runaway exit — a trail winner re-entered on the same standing state | database/trade_logger.py | r3 |
| 6 | the lander's checks wrote `TestStrat` rows into the box's live plan_ledger (`_ledger_open` ignored a bound store) | strategy/plan.py | r6 · ✅ **ON MAINLINE at r324** |
| 7 | main.py read the sweep's window from a module string ("14:00") and the TCS's from config — the remainder honoured a stale window | main.py | r9 |
| 8 | `analysis/trade_readiness.py::_combine` defined nested, called at module level — NameError on every readiness path, masked by an import guard | analysis/trade_readiness.py | r12 · ✅ **ON MAINLINE at r324** |
| 9 | `check_tcs_parked` P5b red before the fork touched TCS; outside the lander's set | tests/ | r9 |
| 10 | the level engine never read a high or a low — a rejection was invisible to the derived layer | derived/levels.py | r3 (built) |
| 11 | the condor management plan only recognised legs already flagged `is_condor_leg` — a lone sweep/TCS vertical read as "no credit verticals open" | strategy/iron_condor_strategy.py | r10 · ✅ **ON MAINLINE at r324** |
| 12 | `check_standing_offer` S5 adopts a fixture fill into the LIVE trade logger — run by the lander on the QQQ TEST box it wrote `orb-T1` (CALL 196 ×10, spot 197.15) as an open trade and the bot RESUMED a phantom position on restart. Same class as #6. Fix: the checker binds a temp logger; structurally, the lander runs every CHECK with `OT_TRADES_DB`/`OT_DERIVED_DB` on scratch files (config v4.18 honours `OT_TRADES_DB`). **Port both halves; the fixture is identical on mainline.** | tests/check_standing_offer.py, tools/land.sh (control's twin), config.py | r13 |

## WHAT THE PREDECESSOR DID AFTER THE SPLIT — r324 → r364 (read 2026-09-12, OTV4TEST r16)

37 commits, `e955020..upstream/main` (`6e193b98`). **Eleven touch the execution path**
(`strategy/ execution/ analysis/ derived/ risk/ main.py config.py`); the other 26 are
reporting, S3, shadow, ops and docs — mainline's infrastructure, which is mainline's to
protect.

| mainline | what it did | collides with | verdict here |
|---|---|---|---|
| **r324** | PORT.1 — fixes-only parity: took five fork defects (TCS narration, OI event loop, bound test store, `trade_readiness` dedent, lone-vertical recognition) and **named the five it refuses** — the ORB's close-based runaway invalidation, `finish_break` on any exit, the rejection fact, windows read from plans, and `TCS_MIN_POP` — so the predecessor keeps trading as it did at r322 and stays a valid control arm | the fork's r6/r8/r10/r12 | ✅ nothing owed — this is the fork's own work arriving there |
| **r340** | RPT.24 — a single-leg entry recorded `symbol = INSTRUMENT` and nothing naming the option, so ORB and Runaway were never replayable | `execution/entry_engine.py::_record_kwargs`, shared | 🔴 **THE FORK CARRIES IT** — BACKLOG **PRE.1** |
| **r341** | PLN.1 — the condor slipped r213's net; the panel accuses a dispatch bug that does not exist | `strategy/plan.py`, shared | ⬜ unassessed — PRE.2 |
| **r344** | RPT.26 — `is_short_position` had no writer; credit MFE/MAE swapped in every report | reporting layer | ⬜ unassessed, likely mainline-only — PRE.2 |
| **r345** | RPT.27 — the exit path resolved every credit spread as a LONG (SELL_TO_CLOSE instead of buying back) | `execution/exit_engine.py` | ✅ **does not apply** — `_close_vertical` hardcodes the actions; the fork's bare flag reads are both on the adopted path, which has a writer |
| **r351 / r353** | TCS.1 — the wing floor was never recorded, then moved 1.00 → 0.75 on a measured study | mainline's r238-era TCS | ⬜ the CONSTANT does not port (the fork rewrote TCS at r9 with `TCS_R_FLOOR_EXPIRY`); the **evidence** does — "the wing floor is the most common last refusal in the book" is worth testing against this fork's TCS |
| **r352** | BFLY.15 — the pin was chosen in percent of spot and judged in expected moves, so the selector handed the strategy candidates it was required to refuse | `strategy/gex_pin_butterfly.py` | ⬜ unassessed — the fork's fly is still one file (BFLY.2) |
| **r355 / r356** | CHR.1 / CHR.2 — the character engine turned on; half of it had never measured anything | `analysis/character.py`, `derived/character_engine.py` | ⬜ unassessed — character is not wired into any fork trade |
| **r364** | LVL — pools by side, tines computed at read, the board | `derived/levels.py` etc. | ✅ **already absorbed** at OTV4TEST r15, in mainline's own shape |

⚠️ **THE CONDOR COLLISION WAS OVERSTATED ON FIRST READING AND IS NOT ONE.** r346, r348
and r361 carry `CND` subjects and touch `docs/BACKLOG.md` and `docs/GENESIS.md` ONLY.
Reading a collision off a commit-subject prefix is the same class of error as reading a
backlog state off its prose (BACKLOG HYG.7) — the diff is the evidence, the subject line
is commentary.
