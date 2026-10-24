# docs/PORT_STATE.md  v4.4  — where the project actually stands

> 🔴 **SUPERSEDED SNAPSHOT (marked 2026-10-03, OTV4TEST r226).** Kept for the record it is; it does not describe this fork as it runs. Current state: `docs/TRADES.md` §0 (roster), `docs/BACKLOG.md` (work), `docs/GENESIS-TEST.md` (ledger).

**v4.4 — 2026-10-03 — OTV4TEST r226 — bannered as a superseded snapshot; nothing below was changed.**

**Updated 2026-08-25. HEAD is r73. The fleet is 15 boxes, live and stopped
between sessions.**

## 🔴 SINCE THIS FILE LAST SAID "NOTHING HAS TRADED ON v4 YET"

**v4 has now had one live session — 2026-08-21 — and it traded ZERO.** Not from
one cause: four independent locks, each failing silently.

  1. **The feed ate the open.** The ORB range only ESTABLISHED at 10:01-10:03;
     ORB entries die at 11:00. → fixed r72 (opening-range rescue).
  2. **A dispatch gate vetoed everything.** It tested a label the engine
     hardcodes to UNKNOWN, so it returned before dispatch on EVERY tick with
     relaxed entry ON across all 15 boxes. → fixed r57.
  3. **The condor could never build rails** — a timeframe-key mismatch, then a
     missing daily frame. → fixed r59, and the anchor moved to 1h by operator
     ruling.
  4. **A 14:00 hard entry cutoff nobody specced**, inherited from v3 by a
     hygiene pass whose own changelog said "NOT a behaviour change".
     → deleted r60.

⚠️ **EVERY ONE FAILED IN THE DIRECTION THAT LOOKS LIKE CORRECT BEHAVIOUR**, and
every one was invisible because the refusal was silent. That is why r61-r73 are
almost entirely instrumentation rather than strategy.

## What was built in response (2026-08-22 → 08-25)

- **The feed manifold** (r61, r64) — ten of ten event types captured, was
  three. Nothing is dropped, overwritten or captured conditionally.
- **The derived layer** (r62, r63) — `/derived`, one engine per store. Charm
  and vanna are computable for the first time; expected move decays through the
  session instead of being one number all day.
- **The exorcism** (r65) — the retired classification system is gone from the
  tree, schema physically dropped so a query RAISES rather than returning empty.
- **The plan ledger** (r69, r70) — intent survives a restart, and plans that
  never fired are recorded for later scoring.
- **Instruments** — manifold health board with per-stream bulbs (r68),
  edge-triggered gate reporting (r73), WRITE_MAP (r71), and a devtools SENSORS
  section (dtp r201).

⚠️ **NONE OF IT HAS RUN AGAINST A LIVE TAPE.** Everything above is verified
synthetically. Monday 2026-08-24 is the first session with any of it in place,
and `tools/manifold_health.py` before the open is the thing that says whether
the capture actually works.

---

**Historical, from 2026-08-20 (HEAD `332edb8`, r50):**
**OTV3 is retired. The fleet is repointed. Nothing has traded on v4 yet.**

---

## The one-paragraph version

v3 was closed because its central premise measured false: the regime classifier
picked the correct **side** on **44.9%** of 715 directional trades, 95% CI
**[41.3%, 48.6%]** — entirely below a coin flip, and **34.2%** on puts. What made
money was regime-independent (`orb_trail_stop` 96% / 85 trades / **+$30,696**,
worst −$16); what lost it was the floors and BOS (`max_loss_floor` −$28,179,
`bos_exit` −$7,085). **v4 keeps the collection, execution and exits, and replaces
the layer in between with structure.** Every entry threshold is traceable to a
measurement. No strategy reads a regime label — `tests/check_no_regime.py`
enforces it.

---

## FLEET

**29 boxes repointed to `options_trader_v4` at `332edb8`, all stopped.**
**14 being terminated** (AAPL COST DIA GLD GS IWM JPM LLY MSFT ORCL SMCI SMH TLT
XOM). **15 keepers** = the panel: NVDA SPX PLTR MU QQQ GOOGL AMZN AVGO TSLA META
NFLX CRM UNH CVX AMD.

⚠️ **NOTHING HAS RUN v4 AGAINST A LIVE MARKET.** The LLY throwaway repoint proved
the sync is clean, all eight checkers pass in a box venv, the `.env` survives a
hard reset against a different repo's history, and the gitignore boundary holds.
**It did not prove a chain can be fetched** — that needs a TastyTrade session
against an open market, and the first genuine unknown lands at 09:30.

**Friday is the fire drill. Monday is the session that matters.**

---

## STRATEGIES — five specced, three live-capable

Full specs in `docs/TRADES.md`. Gate categories in each file's `GATES` dict.

| strategy | state | trigger |
|---|---|---|
| **ORB** | live, mechanical | break AND retest — wick back inside, body still outside |
| **RunawayContinuation** | live | ORB ran to 50% TP and HELD; disarms the retest |
| **SweepCreditSpread** | live | named pool swept + reclaimed → sell the boundary it became |
| **GEXPinButterfly** | ⏸ PARKED | apex OTM on the pin; needs ~2 weeks of real OI |
| **IronCondor** | wired, rare | daily fork rails; nice-to-have, not load-bearing |

**Deleted at r33** — `butterfly_strategy`, `continuation_strategy`,
`sweep_reversal_strategy`. Superseded, not shelved.
**Inert** — `trend_credit_spread` (TC.6): 21 trades, 28.6% direction accuracy,
and redundant against the runaway. `TREND_CREDIT_ACTIVE` now defaults **off**.

---

## THE NUMBERS EVERY THRESHOLD RESTS ON

· **ATR floor 0.05%** — below it the required move was reached on **0 of 5,517
  bars**. Not rarely. Not once.
· **ATR→delta map** — 0.20-0.35 delta reachable on 60% of 90-bar windows at
  ≥0.12% ATR, 92% above 0.20%. **ADX measured FLAT across every band** (0.69-0.74%
  median excursion from ADX 12 to ADX 45) and is used nowhere.
· **Sweep window 13:00-15:00** — 39% survival vs 26% before 10:30, on 2,169
  events.
· **Pierce ceiling 0.25%** — 33-34% survival shallow vs 19-21% deep. ⚠️ **A deep
  pierce means a WEAK level**, not a strong rejection: 1.28% median adverse
  against 0.46%.
· **Trails earn, floors lose** — the three trail exits +$62k against floors and
  BOS at −$44k across the v3 book.

---

## WHAT IS STILL UNKNOWN

⚠️ **DIRECTION.** Four independent searches found no predictor: entry conditions
(all ambient — pre-filtered by the strategies' own gates), recorded columns
(gates or empty), opening bias (a coin forward-only, 797 sessions), and the tape
harness (every surviving condition helped UP **and** DOWN). **v4's answer is to
stop predicting it** — every entry observes a move already in evidence.

**The grinder stop is unmeasured.** `mfe_bars` was added at r38 and nothing has
written to it yet. A few v4 sessions answer it directly.

**The GEX butterfly's thresholds are stated priors.** `PIN_CONC_MIN=0.25` has no
sample behind it.

**`tine_order_study` is n=15.** Suggestive, not settled.

---

## THE FAILURE CLASS THIS PROJECT KEEPS FINDING

Not bad code — **plausible silence.** Something computes, is used, and looks
right while being meaningless. Every instance found so far:

· `open_interest` — declared field, **no producer**, so GEX was
  `~100,000 × gamma² × spot` for the life of v3. The "pin" always sat at spot.
· `max_liq` — summed OI + volume, both constant, so "most liquid" resolved to
  "nearest the floor" for weeks.
· `vix_at_entry` — real default 0.0 on **58% of the book**; a probe read it as
  measured and reported "no separation."
· `peak_close` — the true excursion, tracked every tick, **discarded at close.**
· **F0 (r46)** — `_track_excursion` inserted at column 0 above a method
  **inside** the class bisected `ExitEngine`. 37 methods became nested locals of
  a telemetry helper. **Every intraday exit was dead code for seven revisions
  behind a green board**, because none of the six checkers executed an exit.
· **F2** — TC.6 live on default=1 while its own doctrine block said NOT
  DISPATCHED, written without grepping for the dispatch.
· **FEED.2** — `symbol_map` keyed on (symbol, interval) while the same symbol is
  subscribed twice; the RTH 1h route was destroyed at construction and every 1h
  bar landed under `*_EXT`. Six days, fleet-wide, nothing raised.
· **The RTH backfill** — the FEED.2 fix corrected streaming; the restart's
  backfill then wrote 24-hour bars into the plain series anyway. **Worse than
  the hole it replaced: a gap announces itself, a series that changes character
  mid-stream does not.**

**Three checkers I shipped could not fail:** a docstring word-search, one ending
in `or True`, and a grep for a variable name the code does not use. All replaced
with parsed versions, each mutation-proven in both directions.

---

## THE EIGHT CHECKS

Plain scripts with exit codes — **deliberately not pytest**, because the first
version broke the land command on a box whose venv had no pytest, and a red that
means "environment" teaches an operator to ignore reds.

`check_imports` · `check_gates` · `check_no_regime` · `check_condor_spec` ·
`check_dispatch` · `stress_entry_path` (119 hostile-input cases) ·
`check_exit_executes` (born red at `35a6ba4`) · `test_candle_routing`
Plus `gen_file_map.py --check`, which fails the land on drift.
