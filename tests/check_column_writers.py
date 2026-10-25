#!/usr/bin/env python3
"""
tests/check_column_writers.py  v5.0
v5.0  2026-10-25  OTV5 r15 (SCHEMA.1) — new. EVERY trades COLUMN HAS A NAMED, DEDICATED WRITER. The operator, 2026-10-25,
      approving r15 (no column is ever dropped at boot): "make sure every column has a dedicated writer". A read-only
      audit of r14 found a production write site for all 102 columns (tape_band's value is produced by
      analysis/tape_at_level.measure and reached log_entry, where it was dropped for want of the column). WRITERS below
      names, for each column, the function that puts its value into the row. 17 columns are written only on the
      credit / condor paths, which are OFF by default (OT_ORCS, OT_SWEEP_CS, OT_TCS_ACTIVE); they are marked "off".
      BORN RED on r14 at W1 (tape_band is not a column there).

  W1  the store's columns (a fresh TradeLogger: the CREATE + every migration add) and WRITERS name EXACTLY the same set:
      a new column with no writer, or a writer for a column that does not exist, is red.
  W2  every named writer exists (file, then function or Class.method, by AST) and its own source names the column.
"""
import ast
import os
import re
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_tmp = tempfile.mkdtemp(prefix="check_column_writers_")
os.environ["OT_TRADES_DB"] = os.path.join(_tmp, "unused.db")

FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


EE, TL, MAIN = "execution/entry_engine.py", "database/trade_logger.py", "main.py"
XE, CR = "execution/exit_engine.py", "strategy/condor_roll.py"
_ENTER = (EE, "EntryEngine.enter")
_RKW = (EE, "EntryEngine._record_kwargs")
_TAPE = ("analysis/tape_at_level.py", "measure")
_EXIT = (TL, "TradeLogger.log_exit")
_PREM = (TL, "TradeLogger.update_current_premium")
_ECON = (TL, "TradeLogger.set_entry_contract")
_XCON = (TL, "TradeLogger.set_exit_contract")
_XLAT = (TL, "TradeLogger.set_exit_latency")
_LOG = (TL, "TradeLogger.log_entry")
_LEG = (MAIN, "_execute_condor_leg")                # off: OT_ORCS / OT_SWEEP_CS / OT_TCS_ACTIVE
_ROLL = (CR, "_execute_roll")                       # off: needs condor legs
_SUPP = (XE, "ExitEngine._sync_stop_suppression")   # off: needs condor legs

WRITERS = {
    "trade_id": _ENTER, "symbol": _RKW, "option_symbol": _RKW, "strategy": _RKW, "setup_type": _RKW,
    "direction": _RKW, "underlying_entry": _RKW, "underlying_stop": _RKW, "underlying_target": _RKW,
    "vix_at_entry": _RKW, "is_fed_day": _RKW,
    "setup_grade": _ENTER, "setup_score": _ENTER, "option_side": _ENTER, "is_butterfly": _ENTER, "strike": _ENTER,
    "expiry": _ENTER, "contracts": _ENTER, "entry_premium": _ENTER, "total_cost": _ENTER, "max_loss": _ENTER,
    "stop_premium": _ENTER, "trail_activation": _ENTER, "target_premium": _ENTER, "adx_at_entry": _ENTER,
    "flat_angle_deg": _ENTER, "swept_level_name": _ENTER, "level_strength": _ENTER, "order_id": _ENTER,
    "paper_trade": _ENTER, "relaxed_entry": _ENTER, "notes": _ENTER, "lower_strike": _ENTER,
    "center_strike": _ENTER, "upper_strike": _ENTER, "net_debit": _ENTER, "max_profit": _ENTER,
    "lower_symbol": _ENTER, "center_symbol": _ENTER, "upper_symbol": _ENTER, "orb_range_high": _ENTER,
    "orb_range_low": _ENTER, "stop_width_pct": _ENTER, "planned_r": _ENTER,
    "tape_vol_at_level": _TAPE, "tape_prints_at_level": _TAPE, "tape_band": _TAPE, "tape_buy_frac_at_level": _TAPE,
    "entry_time": _LOG, "status": _LOG, "lineage": _LOG,
    "exit_premium": _EXIT, "pnl_usd": _EXIT, "pnl_pct": _EXIT, "exit_reason": _EXIT, "exit_time": _EXIT,
    "mfe_premium": _EXIT, "mfe_bars": _EXIT, "mae_premium": _EXIT, "mae_bars": _EXIT,
    "current_premium": _PREM, "max_premium_seen": _PREM, "min_premium_seen": _PREM,
    "max_premium_seen_at": _PREM, "min_premium_seen_at": _PREM,
    "trail_stop": (TL, "TradeLogger.update_trail_stop"),
    "entry_snapshot": (TL, "TradeLogger.set_entry_snapshot"),
    "entry_delta": _ECON, "entry_gamma": _ECON, "entry_theta": _ECON, "entry_iv": _ECON, "entry_bid": _ECON,
    "entry_ask": _ECON, "chain_iv_rank": _ECON,
    "exit_bid": _XCON, "exit_ask": _XCON, "exit_iv": _XCON,
    "exit_submit_ts": _XLAT, "exit_fill_ts": _XLAT, "exit_latency_ms": _XLAT, "exit_ladder_steps": _XLAT,
    "exit_escalated": _XLAT, "exit_mark_at_trigger": _XLAT,
    "live_exit_state": (XE, "ExitEngine._exit_state_save"),
    "is_short_position": ("execution/broker_reconcile.py", "_adopt_record"),
    # ── off by default: the credit / condor paths ──
    "pool_price": _LEG, "short_strike": _LEG, "long_strike": _LEG, "spread_width": _LEG, "credit_received": _LEG,
    "is_condor_leg": _LEG, "condor_leg_num": _LEG, "condor_trigger_source": _LEG, "is_broken_wing": _LEG,
    "short_symbol": _LEG, "long_symbol": _LEG, "gap_pct": _LEG,
    "final_form_basis": _ROLL, "final_form_group": _ROLL, "cumulative_credit": _ROLL,
    "stop_suppressed_ts": _SUPP, "stop_suppressed_by": _SUPP,
}

from database import trade_logger as tl                         # noqa: E402

db = os.path.join(_tmp, "fresh.db")
tl.TradeLogger(db)
c = sqlite3.connect(db)
cols = {r[1] for r in c.execute("PRAGMA table_info(trades)")}
c.close()
check("W1 every column has a named writer, and every named writer's column exists",
      cols == set(WRITERS), "no writer: %s; no column: %s" % (sorted(cols - set(WRITERS)), sorted(set(WRITERS) - cols)))

_src_cache = {}


def _func_src(path, qual):
    if path not in _src_cache:
        txt = open(os.path.join(ROOT, path), encoding="utf-8").read()
        _src_cache[path] = (txt, ast.parse(txt))
    txt, tree = _src_cache[path]
    parts = qual.split(".")
    nodes = tree.body
    node = None
    for p in parts:
        node = next((n for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                     and n.name == p), None)
        if node is None:
            return None
        nodes = node.body
    return ast.get_source_segment(txt, node)


bad = []
for col, (path, qual) in sorted(WRITERS.items()):
    src = _func_src(path, qual)
    if src is None:
        bad.append("%s: %s:%s not found" % (col, path, qual))
    elif not re.search(r"\b%s\b" % re.escape(col), src):
        bad.append("%s: not named in %s:%s" % (col, path, qual))
check("W2 every named writer exists and its own source names its column", not bad, "; ".join(bad[:8]))

print("\n%s — %d checks, %d failed" % ("GREEN" if not FAILED else "RED", len(RAN), len(FAILED)))
if FAILED:
    print("  failed: " + ", ".join(FAILED))
sys.exit(1 if FAILED else 0)
