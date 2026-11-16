# OGAP — Park's ORB-GAP on the OTV5 paper fleet (spec, DESIGN)

**Status:** BUILT (OTV5 OGAP.1, 2026-11-14). The operator, 2026-11-14: "let's design & paper trade the OGAP on QQQ" (decision D1) and, on D2-D5, the recommendations below. The code is the authority: `strategy/ogap.py`, `strategy/ogap_plan.py`, `execution/exit_engine._evaluate_ogap` / `ogap_exit_step`; gate `tests/check_ogap.py`.

**As built, where it differs from this design (the code wins):**
- **The size is the ramp MIN (r131, OGAP.2).** The operator, 2026-11-16: "Do me a favor and size the OGAP to whatever the ramp minimum (risk per trade) is set at instead of a flat $500. That $500 is Park's (my friend) preferred position size. I like 1050 for most trades." `OGAP_BUDGET_USD` is deleted; contracts = floor(`RISK_PER_TRADE_USD` / (ask × 100)) on the ask (`OT_RISK_USD`, the configure.sh "Risk per trade / ramp START (MIN)" key, set per box). Still its own `budget_usd` line, cap-exempt, one a session, QQQ only; the $500 below is the design as built at OGAP.1. Gate `tests/check_ogap_size.py`.
- **No new trade columns.** Park's basis is the AM.1 executable columns every row carries (ask in, bid out), with the mark (`pnl_usd`) beside it; `pnl_ask_bid_usd` and `max_bid_seen` were NOT added (decision 4: "use AM.1's exec columns, don't invent a parallel set").
- **The restart re-seed** reads the persisted best MARK (`max_premium_seen`) once, as PARK's r291 does: slightly looser than the bid, stated. The in-process peak is the best bid seen.
- **The decision basis** (`fill`) is the entry ask: `entry_ask` on the row, else the `ask=` the plan writes into `notes`, else the mark (`exit_engine.ogap_fill_of`). The sizer is asked on the ask with `RISK_PER_TRADE_USD` (`size_for(..., budget_usd=)`; r131, was `OGAP_BUDGET_USD`).
- **Plan check rows** are all named `ogap_*` (TRADES section 10, PLAN_SPEC §44); the gate-G shadow is the `ogap_gateg_shadow` check row plus one line in `data/counterfactual/ogap_shadow.jsonl`.
- **PIN_EXEMPT** names OGAP (Park's book was measured without the pin gate); the pin counterfactual row is still written on every OGAP entry.
- **No nightly shadow pricer yet:** the shadow rows are recorded; pricing them is the Saturday brief's §1.9 read.

**Source rule:** Park's "ORB-GAP — spec of record", 2026-11-13. It is copied into
`~/reviews/studies/park_orbgap_20261113/SPEC.md`.

**Backtests:**
- `~/reviews/studies/park_orbgap_20261113/`: SPY and QQQ.
- `~/reviews/studies/ogap_equities_20261113/`: every fleet symbol, sealed 2026-11-13 22:04 UTC.

**Name:** the strategy name is `OGAP`, in trade rows, plan rows, the registry and every report. The operator named it, 11-13.

## 0. What this is

OGAP is a **faithful paper copy** of a borrowed trade. Its signal, sizing and exits are Park's, unchanged. Only the
plumbing is ours. A rule that Park changes is changed here only when the operator says so, by a new version of this
spec.

## 1. Instruments

- **Symbols:** QQQ, plus the symbols in §9. Each box trades its own symbol.
- **Option:** the same-day expiry only (0DTE). A box whose symbol has no same-day expiry that day has no OGAP that
  day. The plan writes one row saying so (`ogap_no_0dte`). It is not a refusal, and it never borrows a later expiry.
- **Side:** long calls or long puts only.
- **Strike:** the listed strike nearest the underlying at the fill minute (the open of the fill-minute 1m bar). A tie
  goes to the lower strike.

## 2. Setup

**Opening range:**
- The high and low of the 1m bars labelled 09:30 through 09:44 ET.
- W = high − low.
- It needs at least 10 of those 15 bars, and W > 0. Otherwise there is no trade; the plan row is `ogap_no_range`.

**Gap:**
- gap = (the 09:30 1m bar's open − the prior session's last RTH 1m close) / W.
- The prior close is the box's `ctx.gap.prior_close`, the same one PARK reads.

**Gate-G:**
- |gap| ≥ 0.25: only the gap's side may trade (gap up allows calls, gap down allows puts).
- |gap| < 0.25: either side may trade.
- An unreadable gap fails open: both sides may trade.
- The refused side is a **shadow** (§7). It never trades, never blocks the allowed side, and is never in EV.

## 3. Signal

1. **Break:** for each side, the FIRST 1m bar labelled 09:45 to 10:30 whose CLOSE is strictly beyond the range.
   - Above the high sets a CALL level at the high.
   - Below the low sets a PUT level at the low.
   - Each side breaks once and never re-arms.
2. **Retest:** within the 20 bars after the break bar (the break bar not counted), labelled 10:30 or earlier.
   - CALL: low ≤ level + 0.10W and close > level.
   - PUT: high ≥ level − 0.10W and close < level.
   - The first such bar is the **signal bar**.
3. **One real row per symbol per day:** the earliest signal on an allowed side wins.
4. **Stale skip:** the entry must happen in the minute right after the signal bar closes (signal bar labelled HH:MM,
   fill inside minute HH:MM+1). A tick that first sees the signal later skips it as stale (`ogap_stale`). It is never
   filled late.

## 4. Entry and sizing

| Item | Rule |
|---|---|
| Window | `ENTRY_WINDOWS["OGAP"] = ((9, 46), (10, 32))`, half-open. The last signal bar is 10:30 and the last fill 10:31. |
| Fill price (decision basis) | **The ask** at the fill minute. Sizing and every exit threshold are computed from it, as in Park's book. |
| Minimum premium | ask ≥ $0.50, else no trade (`ogap_ask_floor`) |
| Size | contracts = floor(`RISK_PER_TRADE_USD` / (ask × 100)): the box's ramp MIN (`OT_RISK_USD`), since r131 (OGAP.2; at OGAP.1 it was its own `OGAP_BUDGET_USD` = 500, now deleted). Not `BREAKOUT_BUDGET_USD` or the ramp top. No grade multiplier, and no deploy cap. |
| Too expensive | 0 contracts (ask > `RISK_PER_TRADE_USD` / 100, e.g. $10.50 at $1,050) means no trade (`ogap_ask_band`). It is never rounded up to 1. |
| Booking | Paper books **both** fills, so neither is lost (§6). |

The sizing routes through `risk_manager.size_for("long_debit", premium=ask, budget_usd=RISK_PER_TRADE_USD)` on the
budget rule. That needs a `budget_usd` pass-through added to `_size_budget`. It is a single argument, and every other
caller keeps `self._risk_per_trade`.

## 5. Exits (`execution/exit_engine._evaluate_ogap`, its own route, FIRST MATCH WINS)

These are checked on the **bid**, once per evaluate tick. `fill` = the entry ask, and `peak` = the highest bid seen
since entry. `peak` is persisted every tick (`max_bid_seen`), so a restart re-seeds it from the column, as PARK does
after r291.

| # | Condition | Action |
|---|---|---|
| 1 | peak ≥ 2.0 × fill | floor = max(floor, 0.60 × peak), ratcheting with the peak |
| 2 | peak ≥ 1.6 × fill | floor = max(floor, 1.2 × fill) for the rest of the day |
| 3 | bid ≤ active floor | sell: `ogap_trail` (step 1 armed) or `ogap_lock` |
| 4 | the first tick at or after 14:00 (checked once), with peak never ≥ 1.6 × fill and bid < 0.75 × fill | sell: `ogap_sweep_1400` |
| 5 | 15:45 ET | sell: `ogap_close_1545` |
| 6 | EOD schedule | the backstop only (15:50 ladder, 15:55 cross) |

What does not apply:
- No stop before 1.6×, no take-profit, and none of the sweep or ORB defaults (25% floor, theta, FVG trail).
- The peak-decay stop: OGAP joins `_DECAY_EXEMPT_DEFAULT`.
- `management.decide`: the signal declares `stop_premium = 0` and `target_premium = 0` (inert), and a test pins that
  management takes no OGAP action.

**One look per tick:** Park's book checks once a minute, and ours checks every evaluate tick (a few seconds). Our
floor fires sooner and closer to the floor than his. The difference is recorded, not hidden: every OGAP exit writes
`data/counterfactual/ogap_exit.jsonl` with the tick bid, the minute-boundary bid and the floor.

## 6. What a trade row carries

- `strategy = "OGAP"`. The structure is `long_debit` in `_STRUCTURE_BY_NAME`.
- **The fleet's mark basis:** `entry_premium` = the mark at the fill (paper books the mark, like every setup), and
  `exit_premium` = the mark at the exit. `pnl_usd` is mark-based, comparable with the rest of the fleet.
- **Park's basis, recorded beside it:** `entry_ask` and `exit_bid` (both columns already exist), plus one new column,
  `pnl_ask_bid_usd` = contracts × 100 × (exit_bid − entry_ask). It is computed at the close in the trade logger. The
  warehouse schema gains the column (the "no columns dropped" rule holds), and `load_trades` exposes it.
- **Notes columns:** `notes` carries `ogap gap=<g> W=<W> brk=<HH:MM> sig=<HH:MM> side=<C/P> allowed=<C,P>`.
  `underlying_target` = 0, `trail_activation` = 0, `is_liquidity_hunt` = 0.
- **Fees:** `tests/fees.py`'s card, beside P&L and never in EV, as for every setup.

## 7. Gate-G shadow rows (never in EV)

When the refused side produces a signal bar:
- the plan writes one `derived_plan_check` row, `check_name = "ogap_gateg_shadow"`, carrying the side, signal minute,
  strike and the ask and bid at the fill minute.
- it writes one line to `data/counterfactual/ogap_shadow.jsonl`.

The shadow is **priced after the close, not tracked live.** The nightly review scorer walks the same §5 exits over
that contract's captured 1m bid candles (CAP.7 option candles), and writes `ogap_shadow_pnl` beside it. It appears
only in the Saturday brief's OGAP section, labelled as a shadow, and never in window EV or theories.

## 8. Admission and interactions

`position_manager._DEFAULT_RULES` gains:
```
OGAP: AdmissionRule(config.ENTRY_WINDOWS[OGAP], max_open_of_type=1, max_tries_per_session=1, cap_exempt=True)
```

**Recommendation: ALLOWED beside Runaway, Breakout and Hunt on the same symbol and day.** Nothing blocks it, and it
blocks nothing.
- **Why:** this is the standing ruling (r42/r50: "every trade to be 'right' in its own time"), and the admission table
  keeps `blocks` empty by rule.
- **A real overlap:** OGAP reads a different range (09:30–09:44, against the 5m range the others read), so it
  overlaps but isn't the same observation. Blocking would also break the comparison with Park's own book, which
  trades it alone.
- **The cost:** on a day Breakout and OGAP both take the same direction on QQQ, the paper book is doubly exposed.
  That is paper, and each row is scored separately.

**Cap:** OGAP is cap-exempt and joins `CAP_EXCLUDED_STRATEGIES`, like PARK. It has its own budget, so a fleet loss
day never stops it, and its P&L never buys the others room. This keeps its record comparable with Park's.

**One per session:** `_one_per_session_used("OGAP")` is DB-backed and fails closed, as for PARK.

**Dispatch:** `_attempt_ogap(ctx, ms, state, chain)` is called beside `_attempt_park`, in the normal dispatch and in
the capped branch. It is dormant outside its window.

## 9. Symbols

This was decided by `ogap_equities_20261113`, sealed 22:04 UTC 11-13 and run once (see OGAP_PLAN.md §1).

**The equities FAILED the sealed bar on both price tiers:**

| Cut | Tier | Rows | EV/row [95%] |
|---|---|---|---|
| Equities pooled | T1 | 19 | −$96 [−160, −22] |
| Equities pooled | T2 | 126 | −$59 [−112, −7] |
| QQQ | T1 | 7 | +$148 [−124, +454] |
| QQQ | T2 | 32 | +$137 [−87, +421] |

- **OGAP runs on the QQQ box only.** The symbol set is a config constant, `OGAP_SYMBOLS = ("QQQ",)`. Every other box's
  plan writes one `ogap_not_this_symbol` row a day and does nothing else.
- **SPX:** stays out under Park's band. The ATM 0DTE ask is far above $5.00, so every row is refused.
- **SPY:** not a fleet symbol.
  - It can't be added on Monday without a 15th TastyTrade session (the ceiling is 15 on one login, leaving no
    headroom) or a second-symbol trading path on the QQQ box (a new build: chain, quotes and positions for a second
    underlying).
  - **Recommendation:** QQQ-only to start, and SPY as a separate build after 2+ weeks of OGAP rows.

## 10. Not translated, and why

- **Cash-path refusals (FOMC day-after, early close, the 2-opens / $1,000 day cap, the kill and flatten files):**
  these are Park's cash executor's safety rules, not part of the signal. His paper leg trades through them, and so
  does ours. A half day is still clipped by our own `entries_open()` lead, and the 15:45 close is close-anchored.
- **His executor's order ladder (ask then ask+$0.01, a 30 s wait):** paper doesn't place orders. If OGAP ever goes to
  cash, the live path uses the fleet's r104 ladder with the ask as the ceiling. That is a separate spec.
- **Notifications:** none of his cards. Fleet alerts follow §17 (emergencies only). OGAP opens and closes appear in
  standings and the nightly review.

## 11. Bars (from Park's §7, adapted to paper)

The nightly review prints each bar's status. A tripped bar is an **operator decision item**, not an automatic stop
(paper costs nothing, and the rule is "fix, not log-only").

| Bar | Trigger | Consequence |
|---|---|---|
| Paper review | net (Park basis) < 0 at 12 rows, or 4 straight losers, counted from 11-16 | flagged for the operator: keep, tune (blind) or retire |
| Clock tag | rows with a signal after 10:00 net < 0 at 12 rows AND rows at or before 10:00 net > 0 at 12 rows | a blind 10:00 cut-off study is earned (WEEKEND_STUDIES) |
| 14:00 sweep check | over 10 sweep exits, the 15:45 bell would have beaten the sweep | flagged: a sweep study is earned |

## 12. Constants (config.py, no env keys, per "no study toggles")

```
ENTRY_WINDOWS["OGAP"] = ((9, 46), (10, 32))
OGAP_RANGE_ET = ((9, 30), (9, 44)); OGAP_RANGE_MIN_BARS = 10
OGAP_BREAK_ET = ((9, 45), (10, 30)); OGAP_RETEST_BARS = 20; OGAP_RETEST_W = 0.10
OGAP_GATE_G_W = 0.25
OGAP_MIN_ASK = 0.50   (r131: the budget is RISK_PER_TRADE_USD; OGAP_BUDGET_USD deleted)
OGAP_LOCK_ARM = 1.6; OGAP_LOCK_FLOOR = 1.2; OGAP_TRAIL_ARM = 2.0; OGAP_TRAIL_KEEP = 0.60
OGAP_SWEEP_ET = (14, 0); OGAP_SWEEP_BELOW = 0.75; OGAP_CLOSE_ET = (15, 45)
```
OGAP is added to `_DECAY_EXEMPT_DEFAULT` and to `CAP_EXCLUDED_STRATEGIES`.

## 13. Files

| File | Change |
|---|---|
| strategy/ogap.py (new) | the specification (CONDITIONS, PLAN_CHECKS, generate_signal), as park.py |
| strategy/ogap_plan.py (new) | reads the 1m tape and the gap, finds break, retest and signal, picks the contract, emits |
| execution/exit_engine.py | an `OGAP` route and `_evaluate_ogap` (§5); the ogap_exit counterfactual |
| execution/position_manager.py | the admission row (§8) |
| risk/risk_manager.py | the `_size_budget(budget_usd=)` pass-through |
| execution/entry_engine.py | the OGAP paper fill also stamps entry_ask and entry_bid (the mark is still booked) |
| database/trade_logger.py | `pnl_ask_bid_usd` and `max_bid_seen` |
| warehouse/s3_push.py, tests/warehouse_source.py | the new columns |
| main.py | `_attempt_ogap`, `_STRUCTURE_BY_NAME`, the service line `ogap=on` |
| strategy/plan_state.py | the OGAP plan row (ACTIVE) |
| config.py | §12 |
| tests/check_ogap.py (new) | the gate (PLAN §2) |
| dtp: strategy_registry.py, tools/review_kit.py, ~/reviews/scripts/theories.py, the Saturday brief prompt §1 | `OGAP` registered as "OGAP"; its own line in the review; the benchmark decision (PLAN §6) |
