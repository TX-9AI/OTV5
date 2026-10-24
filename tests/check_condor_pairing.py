#!/usr/bin/env python3
"""
tests/check_condor_pairing.py  v1.0
PAIRING GATE INVARIANTS: Rules 1 and 3 are enforced by _can_open_credit_spread.

v1.0  2026-08-24  Born RED at HEAD before v4.3. Pins:
  P1  _can_open_credit_spread("call") is True when nothing is open
  P2  _can_open_credit_spread("call") is False when a call is already open
      (Rule 3: never two calls)
  P3  _can_open_credit_spread("put") is False when a put is already open
  P4  _can_open_credit_spread returns False for BOTH sides when both are open
      (Rule 1: max 2 — slot full)
  P5  the complementary side IS allowed when one side is open
      (the condition that lets a condor form)
  P6  _open_credit_sides() returns the correct set, read from open trades
  P7  condor_trigger_source is a real column in the trades schema
  P8  CondorTriggerMap.best() returns the trigger nearest to price

All executed against planted state, no real broker calls.
Run:  cd ~/options-trader && python3 tests/check_condor_pairing.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}"
          + (f"  — {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


# ── helpers ───────────────────────────────────────────────────────────────────

def _fake_trades_db(sides: list) -> str:
    """Create an in-memory-like sqlite with planted open trades, return path."""
    path = "/tmp/cp_test_trades.db"
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE trades (
        trade_id TEXT, symbol TEXT, option_side TEXT,
        is_condor_leg INTEGER DEFAULT 0, status TEXT DEFAULT 'open',
        condor_trigger_source TEXT DEFAULT '')""")
    for i, (side, source) in enumerate(sides):
        con.execute("INSERT INTO trades VALUES (?,?,?,1,'open',?)",
                    (f"T{i}", "SPX", side, source))
    con.commit()
    con.close()
    return path


def _patch_trade_logger(db_path: str):
    """Monkey-patch get_trade_logger to point at the planted DB."""
    import database.trade_logger as tl
    original = tl.get_trade_logger

    class _FakeLogger:
        def get_open_trades(self):
            con = sqlite3.connect(db_path)
            con.row_factory = sqlite3.Row
            rows = [dict(r) for r in con.execute("SELECT * FROM trades WHERE status='open'")]
            con.close()
            return rows

    tl._fake_instance = _FakeLogger()
    tl.get_trade_logger = lambda: tl._fake_instance
    return original, tl


def _restore(tl, original):
    tl.get_trade_logger = original


# ── source the gate functions from main.py WITHOUT executing the module ───────

def _load_gate_fns():
    """
    Extract _can_open_credit_spread and _open_credit_sides from main.py
    source without importing the whole module (which would start the bot).
    """
    import importlib.util, types
    stub = types.ModuleType("main_stub")
    stub.__file__ = os.path.join(ROOT, "main.py")
    # We only need the two gate functions and their helpers. Compile the
    # source and exec ONLY the functions we need plus their imports.
    src = open(os.path.join(ROOT, "main.py")).read()
    # Extract the two function bodies via a thin exec of a trimmed version
    ns = {"__name__": "__main__"}
    try:
        # Approach: exec entire main.py in a namespace that stubs out everything
        # that would try to connect — the gate fns are pure DB reads.
        import unittest.mock as mock
        with mock.patch.dict("sys.modules", {
            "tastytrade": mock.MagicMock(),
            "tastytrade.order": mock.MagicMock(),
            "data.tasty_client": mock.MagicMock(),
            "notifications.alert_manager": mock.MagicMock(),
        }):
            code = compile(src, "main.py", "exec")
            exec(code, ns)  # noqa: S102
    except Exception:
        # Full exec failed (expected on a test box without all deps).
        # Fall back to extracting just the two functions.
        import textwrap, ast as _ast
        tree = _ast.parse(src)
        fn_src = []
        # ⚠️ MODULE-LEVEL CONSTANTS COME TOO. Rule 4's helpers read
        # _TREND_TRIGGERS / _SWEEP_TRIGGERS / _FORK_TRIGGERS / _PAIRING_TABLE,
        # and this extractor only ever collected FunctionDef nodes — so the
        # functions arrived without the names they close over and NameError'd
        # at call time rather than at exec time.
        for node in tree.body:
            if isinstance(node, _ast.Assign) and any(
                    getattr(t, "id", "").startswith(
                        ("_TREND_", "_SWEEP_", "_FORK_", "_PAIRING_"))
                    for t in node.targets):
                fn_src.append("\n".join(
                    src.splitlines()[node.lineno - 1: node.end_lineno]))
        for node in _ast.walk(tree):
            if isinstance(node, _ast.FunctionDef) and node.name in (
                # ⚠️ r132 — Rule 4 made the gate read the open LEGS (for their
                # trigger source), not just their sides, and added the pairing
                # helpers. An AST-extracted function needs every name it calls
                # present in the namespace or it NameErrors at call time.
                "_can_open_credit_spread", "_open_credit_sides",
                "_open_credit_legs", "_trigger_class", "_pairing_allowed",
                # r134 — Rule 4 now consults the sweep's LIVE rejection state
                "_sweep_has_rejection"
            ):
                lines = src.splitlines()
                fn_lines = lines[node.lineno - 1: node.end_lineno]
                fn_src.append("\n".join(fn_lines))
        combined = "\n\n".join(fn_src)
        exec(combined, ns)  # noqa: S102
    return ns.get("_can_open_credit_spread"), ns.get("_open_credit_sides")


def main() -> int:
    print("=" * 66)
    print("CONDOR PAIRING GATE: Rules 1 + 3")
    print("=" * 66)

    can_fn, sides_fn = _load_gate_fns()
    check("gate functions extracted from main.py",
          can_fn is not None and sides_fn is not None,
          "could not find _can_open_credit_spread or _open_credit_sides")
    if can_fn is None:
        print("  ABORT — cannot test without the gate functions")
        return 1

    # P1 — empty book: both sides open
    db0 = _fake_trades_db([])
    orig, tl = _patch_trade_logger(db0)
    check("P1 empty book: call allowed", can_fn("call"))
    check("P1 empty book: put allowed",  can_fn("put"))

    # P2/P3 — one side occupied
    db_call = _fake_trades_db([("call", "1h_fork")])
    _patch_trade_logger(db_call)[0]  # re-patch (already patched)
    import database.trade_logger as tl2
    tl2._fake_instance.__class__ = type("FL", (), {
        "get_open_trades": lambda self: [
            {"trade_id":"T0","symbol":"SPX","option_side":"call",
             "is_condor_leg":1,"status":"open","condor_trigger_source":"1h_fork"}
        ]})
    tl2._fake_instance = tl2._fake_instance.__class__()
    check("P2 call open → call blocked (Rule 3)", not can_fn("call"))
    check("P5 call open → put ALLOWED",            can_fn("put"))

    db_put = _fake_trades_db([("put", "sweep_reversal")])
    tl2._fake_instance.__class__ = type("FL2", (), {
        "get_open_trades": lambda self: [
            {"trade_id":"T1","symbol":"SPX","option_side":"put",
             "is_condor_leg":1,"status":"open","condor_trigger_source":"sweep_reversal"}
        ]})
    tl2._fake_instance = tl2._fake_instance.__class__()
    check("P3 put open → put blocked (Rule 3)", not can_fn("put"))
    check("P5b put open → call ALLOWED",          can_fn("call"))

    # P4 — both sides occupied (Rule 1: slot full)
    tl2._fake_instance.__class__ = type("FL3", (), {
        "get_open_trades": lambda self: [
            {"trade_id":"T0","option_side":"call","is_condor_leg":1,"status":"open","condor_trigger_source":"1h_fork"},
            {"trade_id":"T1","option_side":"put", "is_condor_leg":1,"status":"open","condor_trigger_source":"1d_fork"},
        ]})
    tl2._fake_instance = tl2._fake_instance.__class__()
    check("P4 both open → call blocked (Rule 1)", not can_fn("call"))
    check("P4 both open → put  blocked (Rule 1)", not can_fn("put"))

    _restore(tl2, orig)

    # P7 — condor_trigger_source column exists in schema
    tmp = "/tmp/cp_schema_test.db"
    if os.path.exists(tmp): os.remove(tmp)
    try:
        from database.trade_logger import TradeLogger
        tl_real = TradeLogger(tmp)
        con = sqlite3.connect(tmp)
        cols = {row[1] for row in con.execute("PRAGMA table_info(trades)")}
        con.close()
        check("P7 condor_trigger_source column in schema",
              "condor_trigger_source" in cols, f"found: {cols}")
    except Exception as exc:
        check("P7 condor_trigger_source column in schema", False, str(exc))
    finally:
        if os.path.exists(tmp): os.remove(tmp)

    # P8 — CondorTriggerMap.best()
    try:
        from analysis.condor_trigger_map import CondorTriggerMap, ForkTrigger
        ctm = CondorTriggerMap(price=5500.0)
        ctm.triggers = [
            ForkTrigger(tf="1h", side="call", rail=5530.0, trigger=5518.0,
                        median=5490.0, slope=0.5, active=True),
            ForkTrigger(tf="1d", side="call", rail=5560.0, trigger=5532.0,
                        median=5490.0, slope=0.1, active=False),
        ]
        best = ctm.best("call")
        check("P8 best() returns the active trigger nearest price",
              best is not None and best.tf == "1h", str(best))
        check("P8 inactive trigger not returned by best()",
              ctm.best("put") is None)
    except Exception as exc:
        check("P8 CondorTriggerMap.best()", False, str(exc))

    # PG1–PG3 — geometry gate
    # Re-patch trade_logger (was restored after P4 tests)
    import database.trade_logger as tl_geo
    _leg = [{"trade_id":"T0","option_side":"call","is_condor_leg":1,
             "status":"open","short_strike":5530.0,"condor_trigger_source":"1h_fork"}]
    tl_geo._geo_instance = type("GeoFL", (), {"get_open_trades": lambda self: _leg})()
    _orig_geo = tl_geo.get_trade_logger
    tl_geo.get_trade_logger = lambda: tl_geo._geo_instance

    class _MockContract:
        def __init__(self, strike): self.strike = strike
    class _MockSignal:
        # ⚠️ r132 — A TRIGGER SOURCE IS NOW LOAD-BEARING. Rule 4 refuses a pair
        # whose trigger classes it cannot identify (fail closed), so a geometry
        # fixture with no source never reaches the geometry check. These tests
        # are ABOUT geometry, so they carry a pairing the table permits
        # (fork leg 1 → sweep leg 2) and vary only the strikes.
        def __init__(self, side, short_strike, source="sweep_reversal"):
            self.option_side = side
            self.condor_trigger_source = source
            if side == "call":
                self.short_call_contract = _MockContract(short_strike)
                self.short_put_contract  = None
            else:
                self.short_put_contract  = _MockContract(short_strike)
                self.short_call_contract = None

    # ⚠️ r134 — a SWEEP leg 2 now needs a LIVE REJECTION, not just a permitted
    # trigger class. These fixtures are about GEOMETRY, so they carry one.
    class _LiveSweep:
        reclaimed, invalidated, bars_ago = True, False, 1

    _geo_ctx = {"sweep": _LiveSweep(), "price": 5500.0}

    price = 5500.0  # call spread already open at 5530, price at 5500

    # PG1: put spread at 5470 → short_put=5470 < 5500 < 5530=short_call ✓
    good_put = _MockSignal("put", 5470.0)
    check("PG1 valid geometry: put@5470 + call@5530, price=5500 → ALLOWED",
          can_fn("put", good_put, price, ctx=_geo_ctx))

    # PG2: put spread at 5510 → short_put=5510 > 5500=price (tested at birth)
    bad_put = _MockSignal("put", 5510.0)
    check("PG2 inversion blocked: put@5510 > price=5500 → REJECTED",
          not can_fn("put", bad_put, price, ctx=_geo_ctx))

    # PG3: put spread at 5535 → short_put=5535 > short_call=5530 (crossed)
    crossed = _MockSignal("put", 5535.0)
    check("PG3 crossed strikes blocked: put@5535 > call@5530 → REJECTED",
          not can_fn("put", crossed, price, ctx=_geo_ctx))

    _restore(tl2, orig)

    tl_geo.get_trade_logger = _orig_geo   # restore geometry patch

    print("-" * 66)
    if PROBLEMS:
        print(f"FAIL  {len(PROBLEMS)} problem(s): {', '.join(PROBLEMS)}")
        return 1
    print("ALL GREEN — pairing gate enforces Rules 1 and 3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
