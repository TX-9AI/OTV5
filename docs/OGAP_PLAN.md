# OGAP — build, land and scoring plan (DESIGN)

The spec is `docs/OGAP_SPEC.md`. **BUILT 2026-11-14 on the operator's yes** ("let's design & paper trade the OGAP on QQQ"); decisions D2-D5 taken as recommended. The trading freeze
is lifted for OGAP by the operator's order (11-13).

## 1. Which symbols: the sealed equities test

`~/reviews/studies/ogap_equities_20261113/` (SEAL.txt 2026-11-13T22:04:46Z, FROZEN.json, REPORT.md, score.out,
rows.json). Park's rule was run unchanged on all 14 fleet symbols, 07-09..11-13.

| Cut | Tier | Rows | W-L | Net $ | Fees $ | EV/row [95%] | Net w/o best 3 |
|---|---|---|---|---|---|---|---|
| Equities pooled | T1 real 1m quotes | 19 | 9-10 | −1,827 | 52 | −96 [−160, −22] | −2,809 |
| Equities pooled | T2 modelled from 5-min chains | 126 | 59-67 | −7,459 | 407 | −59 [−112, −7] | −11,525 |
| QQQ | T1 | 7 | 5-2 | +1,035 | 10 | +148 [−124, +454] | −520 |
| QQQ | T2 | 32 | 15-17 | +4,397 | 87 | +137 [−87, +421] | −1,839 |
| SPX | — | 0 | — | — | — | all 38 refused: the ask is over $5 | — |

**The sealed bar (E9) failed on every leg**, so OGAP runs on QQQ only.

SPX at a price-scaled band and budget (labelled sensitivity, not the rule): T2 +$193/row [−80, +545], n=31. That is a
separate idea and would need its own sealed test. It is not OGAP.

SPY is not in scope for Monday (spec §9). A 15th TastyTrade session would sit at the ceiling with no headroom, and
the alternative, a second underlying on the QQQ box, is a new build.

## 2. Build steps (in `~/otv5_builds/ogap`, `git clone --shared` of OTV5 at r108 6b380b2)

1. **config.py:** add the §12 constants and `OGAP_SYMBOLS = ("QQQ",)`. Add OGAP to `ENTRY_WINDOWS`,
   `_DECAY_EXEMPT_DEFAULT` and `CAP_EXCLUDED_STRATEGIES`. No env keys.
2. **strategy/ogap_plan.py:** a pure function, `ogap_read(bars_1m, prior_close, now_minute) ->` the range, gap,
   allowed sides, break, retest, signal, stale flag and shadow. The plan wraps it with the tape read and the contract
   pick: today's expiry only (else `ogap_no_0dte`), the strike nearest the fill-minute open with ties going lower,
   the ask band, and sizing. It is written so the backtest's `day_signal` and the plan's function can be compared
   directly.
3. **strategy/ogap.py:** CONDITIONS, PLAN_CHECKS and `generate_signal`, as park.py. The plan checks are `range_w`,
   `gap`, `allowed`, `break_*`, `signal_*`, `ask`, `bid`, `mark`, `contracts`, and the `ogap_gateg_shadow` row.
4. **risk/risk_manager.py:** `_size_budget(budget_usd=None)`. `size_for` passes it through on the budget rule, and
   every existing caller is unchanged (a test pins this).
5. **execution/exit_engine.py:** the `OGAP` route and `_evaluate_ogap` (spec §5), with the peak persisted in
   `max_bid_seen` and a restart re-seed, plus the `ogap_exit.jsonl` counterfactual.
6. **execution/position_manager.py:** the admission row. **execution/entry_engine.py:** the OGAP paper fill stamps
   entry_ask and entry_bid.
7. **database/trade_logger.py:** `pnl_ask_bid_usd` and `max_bid_seen`, with a migration that adds columns only.
   Then `warehouse/s3_push.py` and `tests/warehouse_source.py` (the new columns, nothing dropped).
8. **main.py:** `_attempt_ogap`, called beside `_attempt_park` in both branches; `_STRUCTURE_BY_NAME["OGAP"] =
   "long_debit"`; the service line `ogap=on|not this symbol`. **strategy/plan_state.py:** the OGAP row.
9. **dtp (its own land):**
   - `strategy_registry.py`: `"OGAP": ("OGAP", LIVE, (OTV5,), None)`.
   - `tools/review_kit.py` and the nightly prompt: an OGAP line on Park's basis and the mark basis, plus the bar
     status (spec §11).
   - `~/reviews/scripts/theories.py`: OGAP handled per decision D3.
   - The Saturday brief prompt §1: an OGAP section with its shadow rows.
   - The nightly shadow pricer: `tools/ogap_shadow_price.py`, reading the CAP.7 candles.
10. **Docs:** BACKLOG row OGAP.1, a HANDOFF line, and this spec moved to `docs/OGAP_SPEC.md` in the land.

## 3. Tests, as the gate `tests/check_ogap.py` and wired into the lander's checks

Fixtures are real bars from backtest days with known results (`park_orbgap_20261113/rows.json`):

| Test | Fixture | Expectation |
|---|---|---|
| range | QQQ 11-05 | W and range high/low equal the backtest's; 9 range bars mean no range |
| gate-G | QQQ 11-05 (gap down) and a synthetic \|gap\| = 0.24 / 0.25 | 0.25 binds, 0.24 doesn't; an unreadable gap fails open |
| break and retest | QQQ 11-05 PUT 09:48 signal; 10-30 PUT 10:22 | signal minute equal; a close on the edge isn't a break; the 21st bar after the break isn't a retest |
| one row a day | a day with both sides signalling | the earliest allowed side; a refused-side signal writes a shadow and doesn't block |
| stale skip | a tick first seen at signal + 2 | `ogap_stale`, no order |
| sizing | asks 0.49 / 0.50 / 2.27 / 5.00 / 5.01 | refused / 10 / 2 / 1 / refused (0 contracts), on `OGAP_BUDGET_USD`, not RISK_PER_TRADE |
| exits | the QQQ 11-05 trail; 11-02 1.2× lock; 11-04 14:00 sweep; a 15:45 bell row | reason and exit bid equal the backtest's when fed the same minute bids |
| restart | an open OGAP rehydrated with max_bid_seen at 1.7× | the lock floor 1.2× is re-armed |
| isolation | the decay stop, management.decide, the cap | none acts on OGAP; the cap total excludes it |
| other symbols | a META box | one `ogap_not_this_symbol` row, no signal |

**Replay check (before the land):** run `ogap_read` plus `_evaluate_ogap` over the stored QQQ 1m bars and T1
quote candles for **10-30, 11-02, 11-04, 11-05 and 11-09**. Each row's signal minute, strike, contracts, exit reason
and P&L must match `park_orbgap_20261113/rows.json`. A P&L within $1 counts as a match. Tick-versus-minute timing can
move the exit inside a minute, so the replay feeds minute bids, as the backtest did. Any mismatch blocks the land.

## 4. Land and bake timing (live at 09:15 Monday 11-16)

| When (ET) | What |
|---|---|
| Fri 17:15 → Sat 02:30 | the study dispatch uses the boxes: no land |
| Sat 03:00 → ~07:30 | the Saturday brief does its box reads and closes the fleet: no land |
| **Sat after the brief's CLOSE, or Sun 11-15 daytime** | after the operator's yes: build, run check_ogap and the replay, land through the lander (the standing heavy-lock form), wake, bake 13/13 plus CRM, verify `ogap=on` on QQQ and `not this symbol` on the rest, then stop the fleet (CRM stays up) |
| Mon 09:15 | the fleet wakes itself on the new rev |

The fallback, if the yes comes later than Sunday 18:00 ET, is to land Monday after the close. The first OGAP day is
then Tue 11-17. No land is ever squeezed in before the open (the boot sweep runs 09:15–09:26).

## 5. Monday verification (11-16)

| When (ET) | Check |
|---|---|
| 09:46 | On the QQQ box, the plan rows exist: `ogap_range`, `gap`, `allowed`. Count them per box with `derived_plan_check`, where `check_name LIKE 'ogap_%'`. Every other box has exactly one `ogap_not_this_symbol` row. |
| 10:32 | Every QQQ day ends with exactly one of: a trade row (`strategy='OGAP'`); `ogap_no_signal` with a reason (no break, or break without retest); `ogap_refused` with the ask band; or `ogap_stale`. A gate-G shadow, if any, has its row. |
| 15:46 | Any OGAP trade is closed with an `ogap_*` reason, and `pnl_ask_bid_usd` is filled. |
| After the close | Re-score the day with the backtest script on the day's T1 candles. The live row must match the replayed row's signal minute, strike, contracts and exit reason. A mismatch is a bug, and it gets a fix, not a note. |

## 6. Scoring cadence and decisions

- **Nightly:** the OGAP line in the review, on both bases, with fees beside them, plus the bar status (spec §11).
- **Saturday brief:** the OGAP section, covering rows to date, EV/row on a day bootstrap, before and after 10:00,
  calls and puts, and the shadow rows.
- **After 12 rows** (Park's bar; at about 0.5 rows a day on QQQ that is roughly 5 weeks, near 12-18):
  - **keep** if the net on Park's basis is ≥ 0 and there is no 4-loser streak;
  - **study a fix** if the clock tag trips (spec §11);
  - **operator decision** if net < 0.
- **After 30 rows:** keep, tune (blind) or retire, judged on the window EV and its interval (the edge-over-horizon
  rule). Retire only if the EV interval's upper bound is below 0, or if the 12- and 30-row bars both fail.
- **Cash:** OGAP stays paper. Any cash use is a separate operator decision and a separate spec.

## 7. Decisions for the operator

| # | Decision | My recommendation |
|---|---|---|
| D1 | Build and land OGAP (QQQ only), aiming for Monday | Yes. Land Sunday after the brief, with check_ogap and the 5-day replay as the gate. |
| D2 | Allowed beside Runaway, Breakout and Hunt on the same day, and cap-exempt with its own $500 | Allowed and cap-exempt, as PARK, so its record compares with Park's |
| D3 | Does OGAP count in the 10-26..11-27 EV benchmark and theories, or get its own line? | Its own line, outside the benchmark, so the window stays comparable |
| D4 | Which basis is the headline | Park's ask in / bid out is the headline. The mark is shown beside it for the fleet comparison. |
| D5 | SPY | Not Monday. Revisit after 2+ weeks of rows (a 15th session or a second-underlying build) |

Not asked: equities (they failed the sealed bar) and SPX under Park's band (every row is refused).
