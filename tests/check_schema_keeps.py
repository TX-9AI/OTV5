#!/usr/bin/env python3
"""
tests/check_schema_keeps.py  v5.1
v5.1  2026-10-26  OTV5 r34 (SCHEMA.2) — K5-K6: is_liquidity_hunt. EntryEngine.enter wrote it into every record and
      log_entry dropped it for want of a column (all 54 trades of 2026-10-26). BORN RED on 98eded7 at K5 and K6.
v5.0  2026-10-25  OTV5 r15 (SCHEMA.1) — new. A REPOINTED BOX KEEPS EVERY COLUMN, TABLE AND VALUE IT HAD.
      trade_logger's boot migration dropped, by difference, every trades column and table outside this tree's shape,
      and this tree lacked mainline r499's tape_band: NVDA's repoint preflight (2026-10-25) found its first OTV5 start
      would have physically dropped tape_band and its values. The operator: "We don't want less columns - that would
      be a mistake." BORN RED on r14 at K1 (tape_band and the unknown column dropped, the unknown table dropped) and K2-K3.

DRIVEN through the real TradeLogger on scratch stores (OT_TRADES_DB is never the live one):
  K1  a store built in the LEGACY FLEET'S exact trades shape (LEGACY_SHAPE: NVDA, mainline otv4 r499, 99 columns, read
      2026-10-25), plus a column and a table this tree has never heard of, one row with a value in EVERY column: after
      TradeLogger boots on it, every column, every value and the unknown table's row are still there.
  K2  every legacy column is in this tree's shape (the CREATE + the migration adds), so a repoint never lacks one.
  K3  tape_band: a fresh store has the column, and log_entry persists a record's tape_band.
  K4  a second boot on the K1 store changes nothing (idempotent).
  K5  is_liquidity_hunt: a fresh store has the column, log_entry persists a hunt record's flag as 1, and no
      "[schema] ... DROPPED" warning names it.
  K6  a store WITHOUT the column (2026-10-26's shape) gains it at boot, backfilled from the strategy: the LiquidityHunt
      row reads 1, the Breakout row 0; a second boot leaves both alone.
"""
import os
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_tmp = tempfile.mkdtemp(prefix="check_schema_keeps_")
os.environ["OT_TRADES_DB"] = os.path.join(_tmp, "unused_trades.db")

FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


# The legacy fleet's trades table, in column order, as NVDA (mainline otv4 r499) holds it on 2026-10-25.
LEGACY_SHAPE = [
    ("trade_id", "TEXT"),
    ("symbol", "TEXT"),
    ("strategy", "TEXT"),
    ("setup_type", "TEXT"),
    ("setup_grade", "TEXT"),
    ("setup_score", "REAL"),
    ("direction", "TEXT"),
    ("option_side", "TEXT"),
    ("is_butterfly", "INTEGER"),
    ("strike", "REAL"),
    ("lower_strike", "REAL"),
    ("center_strike", "REAL"),
    ("upper_strike", "REAL"),
    ("expiry", "TEXT"),
    ("contracts", "INTEGER"),
    ("entry_premium", "REAL"),
    ("exit_premium", "REAL"),
    ("current_premium", "REAL"),
    ("net_debit", "REAL"),
    ("max_profit", "REAL"),
    ("total_cost", "REAL"),
    ("max_loss", "REAL"),
    ("stop_premium", "REAL"),
    ("trail_activation", "REAL"),
    ("target_premium", "REAL"),
    ("underlying_entry", "REAL"),
    ("underlying_stop", "REAL"),
    ("underlying_target", "REAL"),
    ("orb_range_high", "REAL"),
    ("orb_range_low", "REAL"),
    ("short_strike", "REAL"),
    ("long_strike", "REAL"),
    ("credit_received", "REAL"),
    ("spread_width", "REAL"),
    ("is_condor_leg", "INTEGER"),
    ("condor_leg_num", "INTEGER"),
    ("is_broken_wing", "INTEGER"),
    ("short_symbol", "TEXT"),
    ("long_symbol", "TEXT"),
    ("pnl_usd", "REAL"),
    ("pnl_pct", "REAL"),
    ("vix_at_entry", "REAL"),
    ("is_fed_day", "INTEGER"),
    ("status", "TEXT"),
    ("exit_reason", "TEXT"),
    ("order_id", "TEXT"),
    ("lower_symbol", "TEXT"),
    ("center_symbol", "TEXT"),
    ("upper_symbol", "TEXT"),
    ("option_symbol", "TEXT"),
    ("paper_trade", "INTEGER"),
    ("entry_time", "TEXT"),
    ("exit_time", "TEXT"),
    ("notes", "TEXT"),
    ("is_short_position", "INTEGER"),
    ("trail_stop", "REAL"),
    ("max_premium_seen", "REAL"),
    ("min_premium_seen", "REAL"),
    ("adx_at_entry", "REAL"),
    ("flat_angle_deg", "REAL"),
    ("swept_level_name", "TEXT"),
    ("level_strength", "REAL"),
    ("max_premium_seen_at", "TEXT"),
    ("min_premium_seen_at", "TEXT"),
    ("entry_snapshot", "TEXT"),
    ("exit_submit_ts", "TEXT"),
    ("exit_fill_ts", "TEXT"),
    ("exit_latency_ms", "INTEGER"),
    ("exit_ladder_steps", "INTEGER"),
    ("exit_escalated", "INTEGER"),
    ("exit_mark_at_trigger", "REAL"),
    ("entry_delta", "REAL"),
    ("entry_gamma", "REAL"),
    ("entry_theta", "REAL"),
    ("entry_iv", "REAL"),
    ("entry_bid", "REAL"),
    ("entry_ask", "REAL"),
    ("exit_bid", "REAL"),
    ("exit_ask", "REAL"),
    ("exit_iv", "REAL"),
    ("chain_iv_rank", "REAL"),
    ("gap_pct", "REAL"),
    ("relaxed_entry", "INTEGER"),
    ("mfe_premium", "REAL"),
    ("mfe_bars", "INTEGER"),
    ("mae_premium", "REAL"),
    ("mae_bars", "INTEGER"),
    ("condor_trigger_source", "TEXT"),
    ("stop_suppressed_ts", "TEXT"),
    ("stop_suppressed_by", "TEXT"),
    ("stop_width_pct", "REAL"),
    ("planned_r", "REAL"),
    ("tape_vol_at_level", "REAL"),
    ("tape_buy_frac_at_level", "REAL"),
    ("tape_prints_at_level", "INTEGER"),
    ("lineage", "TEXT"),
    ("live_exit_state", "TEXT"),
    ("pool_price", "REAL"),
    ("tape_band", "REAL")
]


def _val(name, typ, k):
    if typ == "INTEGER":
        return 1000 + k
    if typ == "REAL":
        return 0.5 + k
    return "v_%s" % name


from database import trade_logger as tl                         # noqa: E402

# ── K1 / K4 ──────────────────────────────────────────────────────────────────
db1 = os.path.join(_tmp, "legacy.db")
c = sqlite3.connect(db1)
cols = LEGACY_SHAPE + [("zz_unknown_col", "REAL")]
c.execute("CREATE TABLE trades (%s)" % ", ".join(
    "%s %s%s" % (n, t, " PRIMARY KEY" if n == "trade_id" else "") for n, t in cols))
row = {n: _val(n, t, k) for k, (n, t) in enumerate(cols)}
row["trade_id"] = "LEGACY-1"
c.execute("INSERT INTO trades (%s) VALUES (%s)" % (", ".join(row), ", ".join("?" * len(row))), list(row.values()))
c.execute("CREATE TABLE zz_unknown_table (a TEXT)")
c.execute("INSERT INTO zz_unknown_table VALUES ('kept')")
c.commit()
c.close()


def _snapshot(db):
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    have = [r[1] for r in c.execute("PRAGMA table_info(trades)")]
    got = dict(c.execute("SELECT * FROM trades WHERE trade_id='LEGACY-1'").fetchone() or {})
    tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    unk = [r[0] for r in c.execute("SELECT a FROM zz_unknown_table")] if "zz_unknown_table" in tables else None
    c.close()
    return have, got, tables, unk


try:
    tl.TradeLogger(db1)
    err1 = ""
except Exception as exc:                                        # noqa: BLE001
    err1 = "%s: %s" % (type(exc).__name__, exc)
have, got, tables, unk = _snapshot(db1)
lost_cols = [n for n, _ in cols if n not in have]
lost_vals = [n for n in row if got.get(n) != row[n]]
check("K1 legacy shape + unknown column/table: every column, value and the unknown table survive the boot",
      not err1 and not lost_cols and not lost_vals and unk == ["kept"],
      "err=%s lost_cols=%s lost_vals=%s unknown_table=%s" % (err1, lost_cols[:6], lost_vals[:6], unk))
tl.TradeLogger(db1)
check("K4 a second boot changes nothing", _snapshot(db1) == (have, got, tables, unk))

# ── K2 ───────────────────────────────────────────────────────────────────────
db2 = os.path.join(_tmp, "shape.db")                           # a fresh store: the CREATE + every migration add
tl.TradeLogger(db2)
_s = sqlite3.connect(db2)
canon = {r[1] for r in _s.execute("PRAGMA table_info(trades)")}
_s.close()
missing = [n for n, _ in LEGACY_SHAPE if n not in canon]
check("K2 every legacy column is in this tree's shape", not missing, "missing=%s" % missing)

# ── K3 ───────────────────────────────────────────────────────────────────────
db3 = os.path.join(_tmp, "fresh.db")
lg = tl.TradeLogger(db3)
c = sqlite3.connect(db3)
fresh = [r[1] for r in c.execute("PRAGMA table_info(trades)")]
c.close()
rec = tl.make_record(trade_id="TB-1", symbol="QQQ", strategy="Runaway", direction="long",
                     paper_trade=1, tape_band=0.25)
try:
    lg.log_entry(rec)
    c = sqlite3.connect(db3)
    tb = c.execute("SELECT tape_band FROM trades WHERE trade_id='TB-1'").fetchone()
    c.close()
except Exception as exc:                                        # noqa: BLE001
    tb = "%s: %s" % (type(exc).__name__, exc)
check("K3 tape_band is a column on a fresh store and log_entry persists it",
      "tape_band" in fresh and tb == (0.25,), "fresh_has=%s stored=%s" % ("tape_band" in fresh, tb))

# ── K5 / K6 (r34, SCHEMA.2) ─────────────────────────────────────────────────
import logging
class _Cap(logging.Handler):
    def __init__(self): super().__init__(); self.msgs = []
    def emit(self, r): self.msgs.append(r.getMessage())
_cap = _Cap(); logging.getLogger().addHandler(_cap); logging.getLogger().setLevel(logging.DEBUG)
db5 = os.path.join(_tmp, "hunt.db")
lg5 = tl.TradeLogger(db5)
c = sqlite3.connect(db5)
fresh5 = [r[1] for r in c.execute("PRAGMA table_info(trades)")]
c.close()
try:
    lg5.log_entry(tl.make_record(trade_id="LH-1", symbol="GOOGL", strategy="LiquidityHunt", direction="short",
                                 paper_trade=1, is_liquidity_hunt=True))
    c = sqlite3.connect(db5)
    lh = c.execute("SELECT is_liquidity_hunt FROM trades WHERE trade_id='LH-1'").fetchone()
    c.close()
except Exception as exc:                                        # noqa: BLE001
    lh = "%s: %s" % (type(exc).__name__, exc)
dropped = [m for m in _cap.msgs if "is_liquidity_hunt" in m and "DROPPED" in m]
check("K5 is_liquidity_hunt is a column on a fresh store, persisted as 1, never DROPPED",
      "is_liquidity_hunt" in fresh5 and lh == (1,) and not dropped,
      "fresh_has=%s stored=%s dropped=%d" % ("is_liquidity_hunt" in fresh5, lh, len(dropped)))

db6 = os.path.join(_tmp, "pre_r34.db")
c = sqlite3.connect(db6)
c.executescript(tl.TradeLogger.SCHEMA)
_cols6 = [r[1] for r in c.execute("PRAGMA table_info(trades)")]
if "is_liquidity_hunt" in _cols6:                               # build the 10-26 shape: the table without the column
    _keep = [n for n in _cols6 if n != "is_liquidity_hunt"]
    c.execute("CREATE TABLE t2 AS SELECT %s FROM trades" % ", ".join(_keep))
    c.execute("DROP TABLE trades"); c.execute("ALTER TABLE t2 RENAME TO trades")
c.execute("INSERT INTO trades (trade_id, symbol, strategy) VALUES ('H-1', 'GOOGL', 'LiquidityHunt')")
c.execute("INSERT INTO trades (trade_id, symbol, strategy) VALUES ('B-1', 'GOOGL', 'Breakout')")
c.commit(); c.close()
def _flags6():
    c = sqlite3.connect(db6)
    try:
        return dict(c.execute("SELECT trade_id, is_liquidity_hunt FROM trades ORDER BY trade_id"))
    except sqlite3.OperationalError as exc:
        return str(exc)
    finally:
        c.close()
tl.TradeLogger(db6)
f1 = _flags6()
c = sqlite3.connect(db6)
try:
    c.execute("UPDATE trades SET is_liquidity_hunt = 0 WHERE trade_id = 'H-1'"); c.commit()
except sqlite3.OperationalError:                                # no column: K6 fails below, by name
    pass
c.close()
tl.TradeLogger(db6)
f2 = _flags6()
check("K6 a store without the column gains it, backfilled once from the strategy (hunt 1, breakout 0)",
      f1 == {"B-1": 0, "H-1": 1} and f2 == {"B-1": 0, "H-1": 0}, "first boot=%s second boot=%s" % (f1, f2))

print("\n%s — %d checks, %d failed" % ("GREEN" if not FAILED else "RED", len(RAN), len(FAILED)))
if FAILED:
    print("  failed: " + ", ".join(FAILED))
sys.exit(1 if FAILED else 0)
