#!/usr/bin/env python3
"""
tests/check_offer_fill_price.py  v1.0
v1.0  2026-10-03  OTV4TEST r210 (AUD.9) — A FILLED STANDING OFFER RECORDS THE PRICE IT FILLED AT.

  The 10-03 audit: resting_orders.fill_price was 0 on 16 of 16 FILLED rows. Only
  the live poll wrote it; every fill on this box is a paper fill, which closes
  the offer at placement and never polls. The operator, 2026-10-03: "yes I want
  those" (the recordings).

  F1  the REAL resting_orders on a scratch db: placed, closed FILLED, price
      noted -> the row carries state FILLED and the price
  F2  a note for an order that does not exist changes nothing and raises nothing
  F3  the paper filler notes the price right beside its close_out (a source
      check, stated as one - the live proof is the next paper ORB offer)

Run:  python3 tests/check_offer_fill_price.py   (exit 0 green, 1 red)
"""
import ast
import glob as _glob
import os
import sqlite3
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_offer_fill_price_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    try:
        from execution import resting_orders as ro
        ro.record_placement(order_id="PAPER-ORB-GATE0001", session_date="2026-10-05", strategy="ORBStrategy",
                            symbol="QQQ   261005C00754000", underlying="QQQ", side="call", strike=754.0,
                            offered_qty=9, offer_price=1.165)
        ro.note_seen_qty("PAPER-ORB-GATE0001", 9)
        ro.close_out("PAPER-ORB-GATE0001", "FILLED", "paper: filled whole at mark")
        ro.note_fill_price("PAPER-ORB-GATE0001", 1.17)
        c = sqlite3.connect(os.environ["OT_RESTING_DB"])
        row = c.execute("SELECT state, fill_price, offer_price FROM resting_orders WHERE order_id=?",
                        ("PAPER-ORB-GATE0001",)).fetchone()
        check("F1 a FILLED offer carries the price it filled at (1.17), beside its offer price (1.165)",
              row == ("FILLED", 1.17, 1.165), str(row))
        ro.note_fill_price("NO-SUCH-ORDER", 9.99)
        n = c.execute("SELECT COUNT(*), SUM(fill_price) FROM resting_orders").fetchone()
        c.close()
        check("F2 a note for an unknown order changes nothing and raises nothing", n == (1, 1.17), str(n))
    except Exception as exc:                                  # noqa: BLE001
        check("F1 (did not run)", False, f"{type(exc).__name__}: {exc}")
        check("F2 (did not run)", False, "see F1")
    try:
        src = open(os.path.join(_root, "execution", "entry_engine.py")).read()
        tree = ast.parse(src)
        ok = False
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and "paper_trading" in ast.dump(node.test):
                calls = [(n.lineno, n.func.attr) for n in ast.walk(node) if isinstance(n, ast.Call)
                         and isinstance(n.func, ast.Attribute) and n.func.attr in ("close_out", "note_fill_price")]
                co = [l for l, a in calls if a == "close_out"]; nf = [l for l, a in calls if a == "note_fill_price"]
                if co and nf and any(0 < b - a <= 3 for a in co for b in nf):
                    ok = True
        check("F3 the paper filler notes the fill price right after it closes the offer FILLED (source check)", ok)
    except Exception as exc:                                  # noqa: BLE001
        check("F3 (did not run)", False, f"{type(exc).__name__}: {exc}")
    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — a filled standing offer records its fill price")
    return 0


if __name__ == "__main__":
    sys.exit(main())
