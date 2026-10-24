#!/usr/bin/env python3
# tests/check_counterfactual_reads.py  v1.0
# v1.0  2026-10-03  OTV4TEST r190 (AUD.1) — shared with otv4 CND.10. Everything after the closing
#       docstring is byte-identical with otv4's gate; these lines and the r106 venv bootstrap sit ABOVE
#       the docstring so the body hash holds and the lander (system python3) can import the modules.
import glob as _g, os as _o, sys as _s          # OTV4TEST: r106 venv bootstrap, kept ABOVE the docstring
for _sp in _g.glob(_o.path.join(_o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))),
                                "venv", "lib", "python*", "site-packages")):
    if _sp not in _s.path:                       # so the shared body below is byte-identical with otv4's
        _s.path.insert(1, _sp)
"""
tests/check_counterfactual_reads.py  v1.0
v1.0  2026-10-03  CND.10 — THE EXIT COUNTERFACTUAL READS THE OPEN POSITIONS.

  🔴 THE DEFECT, FOUND BY OTV4TEST'S AUDIT (MSG-1003-07) AND MEASURED HERE.
  CounterfactualExitEngine.derive() read `get_trade_logger().conn`; TradeLogger
  has never had `.conn` (git log -G on trade_logger finds no assignment ever),
  so derive() raised AttributeError, logged it at DEBUG, and returned 0 on
  every tick since r66 (2026-08-22). S3 holds ZERO derived_exit_counterfactual
  objects on any day.

  Drives the REAL derive() against a SCRATCH trades.db (never the live one):
  C1  one open trade -> evaluate() is called once with that trade's id (the
      defect: called zero times)
  C2  a closed trade is not evaluated
  C3  derive() never raises, and an unreadable logger WARNS (not debug-only)

  BORN RED on otv4 2220461 at C1 C3.

Run:  python3 tests/check_counterfactual_reads.py
"""
import logging
import os
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


class _Store:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)

    def commit(self):
        self.conn.commit()


def main():
    tmp = tempfile.mkdtemp(prefix="check_cf_")
    from database import trade_logger as tl
    from derived.counterfactual import CounterfactualExitEngine

    db = os.path.join(tmp, "trades.db")
    T = tl.TradeLogger(db_path=db, paper_trading=True)   # scratch, explicit path
    T.log_entry(tl.make_record(trade_id="cf-open", symbol="QQQ",
                               strategy="SweepCreditSpread", direction="short",
                               paper_trade=1))
    T.log_entry(tl.make_record(trade_id="cf-closed", symbol="QQQ",
                               strategy="SweepCreditSpread", direction="short",
                               paper_trade=1))
    con = sqlite3.connect(db)
    con.execute("UPDATE trades SET status='closed' WHERE trade_id='cf-closed'")
    con.commit()
    con.close()

    real = tl._trade_logger
    tl._trade_logger = T
    try:
        eng = CounterfactualExitEngine(store=_Store(os.path.join(tmp, "derived.db")),
                                       symbol="QQQ")
        seen = []
        eng.evaluate = lambda trade: seen.append(trade.get("trade_id")) or None
        try:
            eng.derive({})
            raised = None
        except Exception as exc:                                  # noqa: BLE001
            raised = exc
        check("C1 one open trade is evaluated", seen == ["cf-open"], f"evaluated={seen}")
        check("C2 a closed trade is not evaluated", "cf-closed" not in seen, f"evaluated={seen}")

        class _Broken:
            def get_open_trades(self):
                raise RuntimeError("store unreadable")
            conn = property(lambda self: (_ for _ in ()).throw(RuntimeError("store unreadable")))
        tl._trade_logger = _Broken()
        eng2 = CounterfactualExitEngine(store=_Store(os.path.join(tmp, "d2.db")), symbol="QQQ")
        records = []
        h = logging.Handler()
        h.emit = lambda r: records.append(r)
        lg = logging.getLogger("derived.counterfactual")
        lg.addHandler(h)
        lg.setLevel(logging.DEBUG)
        try:
            out = eng2.derive({})
        finally:
            lg.removeHandler(h)
        warned = any(r.levelno >= logging.WARNING for r in records)
        check("C3 never raises; an unreadable logger WARNS",
              raised is None and out == 0 and warned,
              f"raised={raised!r} out={out!r} warned={warned}")
    finally:
        tl._trade_logger = real

    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — the counterfactual reads every open position, through the logger")
    return 0


if __name__ == "__main__":
    sys.exit(main())
