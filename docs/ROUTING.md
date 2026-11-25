# ROUTING.md — which engine takes every order: paper or live

**`ROUTING.md` v5.0 · 2026-11-26 · r161 (LANE.1) — new. The operator, 2026-11-25: "There should be a clean routing map between paper orders & live orders that is cleanly separated"; "I want park paperwalled until we enable it on the cash side, which is potentially January, if ever"; "Be deliberate. We should be able to switch between paper & live anytime we are fielding a new strategy for a few weeks." The decision lives in ONE function, `execution/order_router.py`; this page is its map, and `tests/check_order_routing.py` holds the code to the table in section 1.**

## 0. Two facts, one decision

| fact | where it is set | how it changes |
|---|---|---|
| **box mode** — which account this box trades: the paper account or the cash account | `config.PAPER_TRADING` (configure.sh item 1, the operator's own) | the operator, at configure.sh, then a restart |
| **lane** — per setup, per box: `on`, `off` or `paper_only` | `deploy/box_flags/<SYM>` (`utils/box_flags.SCHEMA`, default `on`) | one flag line + a land + a fleet bake (section 4) |

`order_router.route(setup, paper_box, flag)` turns the two facts into one answer for an **opening** order:
`LIVE` (the broker), `PAPER` (a paper fill at the mark) or `DORMANT` (never asked).
`order_router.route_close(record, paper_box)` answers for a **closing** order from the ROW alone (`paper_trade`): **an open position finishes in the lane it opened in**.

No other module decides paper versus live for a setup. Box-mode reads that remain elsewhere (the boot and intraday reconcile, the startup cancel, the order guard, the live entry walk, buying power, the 15:55 live cross) are the LIVE engine's own work on a live box: a PAPER-lane order never reaches any of them, because it is booked on a different book (the paper wall) and stored as `paper_trade = 1`, which the live logger never reads.

## 1. The opening table (`order_router.TABLE`)

| ROUTE | flag | box | route |
|---|---|---|---|
| ROUTE | on | paper | PAPER |
| ROUTE | on | live | LIVE |
| ROUTE | paper_only | paper | PAPER |
| ROUTE | paper_only | live | PAPER |
| ROUTE | off | paper | DORMANT |
| ROUTE | off | live | DORMANT |

- Anything else (a typo, a duplicate, an unreadable file) is **DORMANT**: a bad flag can never send a live order (`utils/box_flags` reads it `off` and names it on the `[flags]` line).
- On a **paper box** `PAPER` is the box's own paper engines, and `paper_only` is `on` byte for byte (`tests/check_park_paper_wall.py` W7).
- On a **live box** `PAPER` is **the paper wall** (`execution/paper_wall.py`): `PaperWallEntry` (a paper `EntryEngine`) and `PaperWallBook` (a paper `PositionManager` with its own paper `ExitEngine`).
- `order_router.PAPER_ALWAYS` = `OGAP` (no flag key; retired r153, never asked; an open OGAP row still closes paper).
- A setup with no schema key reads `on` (Runaway today).

## 2. Every order type: engine, and what sees it

Columns: **paper box** (any flag but off) · **live box, `on`** · **live box, `paper_only`** (the wall). `off` on any box: never asked, no order; an OPEN row from before still closes in its own lane (section 3).

| order | paper box | live box, flag on (cash) | live box, flag paper_only (wall) |
|---|---|---|---|
| entry rungs (the mark ladder, the 5 s live walk) | box paper engine: one fill at the mark | broker: `order_guard.clear_to_post`, `buying_power.affordable`, the live walk, `freeze_contract`, the suspect hand-off | wall: `PaperWallEntry`, one fill at the mark, `PAPER-*` order id; none of the live column runs |
| floor / premium-stop exits (Runaway 20%, a single leg's 25%; the MARKET step) | box paper exit engine, at the mark | broker: the r139 stop escalation | wall paper exit engine, at the mark |
| walk exits (profit locks, PARK `park_lock`, `park_delta_floor`, the fizzle, theta bleed, decay, target) | box paper exit engine, at the mark | broker: the exit walk (r144) | wall paper exit engine, at the mark |
| PARK's 15:45 close (`park_close_15:45_ET`) | box paper exit engine, at the mark | broker: the exit walk | wall paper exit engine, at the mark (`main._paper_wall_pass` / `_paper_wall_close_pass`) |
| 15:45 resting close (assignment risk) | paper EOD rule | broker: resting best-case close | paper EOD rule on the wall book |
| 15:50 debit ladder | paper EOD rule | broker: the mark ladder | never: the wall holds to 15:55 and books at the mark |
| 15:55 cross | paper EOD rule, at the mark | broker: the live cross (`handle_hard_close`) | wall `flatten_all`, at the mark (never the live cross) |
| recovery closes (an expired row at start) | box recovery (paper settlement) | broker reconcile: `main._recover_open_position` (reads `paper_trade = 0` rows only) | `paper_wall.recover()`: closed pnl 0, flagged `expired_orphan_autoclosed_paper_wall`, no broker read |

What else sees each lane:

| reader | paper box | live box, cash row (`paper_trade = 0`) | live box, walled row (`paper_trade = 1`) |
|---|---|---|---|
| daily catastrophic cap (`trade_logger.realized_pnl_today`, by box mode) | counts it (record only, r151) | counts it, governs cash | **never counts it; a tripped cash cap does not stop it** (`main._ask_walled_past_cap`) |
| `risk_manager.record_win / record_loss` | yes | yes | no (`order_router.is_wall`) |
| cap counterfactual (`note_entry_risk`) | yes | yes | no |
| boot reconcile, intraday reconcile and adoption | no (paper) | yes | no (the live logger reads `paper_trade = 0`) |
| startup cancel of working orders, order guard | no | yes | no (no order ever exists) |
| admission table, `has_blocking_position`, floor watch, blind REST marks | the box's book | the live book | no (the wall's own book; `blind_rest_marks` False) |
| one-per-session (`count_today`) | yes | yes | yes (every row counts; a walled PARK still trades once a day) |
| held-contracts page (dtp, per row) | paper | LIVE | paper |
| alerts | `[PAPER]` | live | `[PAPER]` entry, `PAPER <setup>` exit |
| reports, warehouse, S3 | `paper_trade = 1` | `paper_trade = 0` | `paper_trade = 1` (dtp r578 splits by Service mode) |

## 3. An open position never changes lane

`route_close` reads the row, never the flag. A flag changed by a land and a restart re-routes **new** entries only:

- a row booked on the wall (`paper_trade = 1`) is resumed by `paper_wall.recover()` and closes paper, even if the flag now reads `on`;
- a cash row (`paper_trade = 0`) is resumed by the live reconcile and closes live, even if the flag now reads `paper_only` or `off`.

Gate: `tests/check_park_paper_wall.py` W9.

## 4. Switching a setup between paper and live

1. **One line** in `deploy/box_flags/<SYM>`: `park = paper_only` (walled on a live box), `park = on` (the box's account; cash on a live box), or `park = off`. A comment line quotes the operator's words. Default `on` needs no line (a line restating the default is refused, `check_box_flags` F6).
2. **A land** (the lander, with the operator's yes): git is the audit trail; `tests/check_box_flags.py` refuses a bad value, a duplicate or an unknown key.
3. **A fleet bake**: the box reads its file **once at start** (`[flags]` line: the value, the file's sha256, the commit); the change takes effect at the next start (the 09:15 wake or a restart). An open position finishes in its own lane (section 3).

Never an interactive toggle: no menu item, no env key, no prompt. A setup joins this mechanism by its `utils/box_flags.SCHEMA` key alone; the router needs no change. (Asking a walled setup past a tripped cash cap also needs its door in `main._PAST_CAP_DOORS`.)

## 5. What is where

| piece | file |
|---|---|
| the decision (`route`, `route_close`, `walled`, `walled_setups`, `asked_past_cap`, `is_wall`) | `execution/order_router.py` |
| the lanes (`on`, `off`, `paper_only`) and the files | `utils/box_flags.py`, `deploy/box_flags/` |
| asked or not (ACTIVE / DORMANT) | `strategy/plan_state.py` (a flagged plan is ACTIVE on `on` and `paper_only`) |
| the paper wall (W1-W6) | `execution/paper_wall.py`; `main._execute_entry_signal`, `_ask_walled_past_cap`, `_paper_wall_pass`, `_paper_wall_close_pass`, `paper_wall.recover` |
| the gates | `tests/check_order_routing.py`, `tests/check_park_paper_wall.py`, `tests/check_ogap_paper_on_live.py`, `tests/check_box_flags.py` |

The paper path holds no broker object and `paper_wall.py` / `order_router.py` import no broker client (gated statically and at runtime). The paper engines are the shared `EntryEngine` / `PositionManager` / `ExitEngine` classes constructed `paper_trading=True`; their modules still import the broker client for their live branch, which a paper instance never calls (zero broker calls through a full walled day, `check_park_paper_wall` W2). A physical module split of the paper engine is not part of r161.
