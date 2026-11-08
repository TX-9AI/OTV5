#!/usr/bin/env python3
"""
tests/check_offer_fill_price.py  v5.1
v5.1  2026-11-08  OTV5 r76 (RETIRE.1) — F3 RE-POINTED (WA 38.4): the ORB standing offer and its paper filler are removed with the ORB trade, so F3 pins
      them gone; F1/F2 (resting_orders.note_fill_price on a scratch store) unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-03  OTV4TEST r210 (AUD.9) — A FILLED STANDING OFFER RECORDS THE PRICE IT FILLED AT.

  The 10-03 audit: resting_orders.fill_price was 0 on 16 of 16 FILLED rows. Only
  the live poll wrote it; every fill on this box is a paper fill, which closes
  the offer at placement and never polls. The operator, 2026-10-03: "yes I want
  those" (the recordings).

  F1  the REAL resting_orders on a scratch db: placed, closed FILLED, price
      noted -> the row carries state FILLED and the price
  F2  a note for an order that does not exist changes nothing and raises nothing
  F3  r76: the paper standing-offer filler is removed with the ORB trade; F1/F2 pin the store it wrote

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
    _t = ast.parse(open(os.path.join(_root, "execution", "entry_engine.py")).read())
    _names = {n.name for n in ast.walk(_t) if isinstance(n, ast.FunctionDef)}
    _calls = {getattr(n.func, "attr", getattr(n.func, "id", "")) for n in ast.walk(_t) if isinstance(n, ast.Call)}
    check("F3 r76: the paper standing-offer filler is removed with the ORB trade (entry_engine places no offer)",
          not ({"_place_standing_offer", "_record_offer"} & (_names | _calls)))
    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — a filled standing offer records its fill price")
    return 0


if __name__ == "__main__":
    sys.exit(main())
