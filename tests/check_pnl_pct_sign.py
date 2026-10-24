#!/usr/bin/env python3
"""
tests/check_pnl_pct_sign.py  v1.0
v1.0  2026-10-03  OTV4TEST r198 (MEAS.1) — THE STORED pnl_pct AGREES IN SIGN WITH pnl_usd.

  TradeLogger.log_exit stored (exit - entry) / entry for every trade. For a
  credit trade premium UP is a LOSS, so its losses were stored as gains: 11 of
  11 SweepCreditSpread rows on QQQ-TEST disagreed in sign with their own
  pnl_usd (the 10-03 audit; first measured 2026-09-17).

  Drives the REAL TradeLogger.log_entry / log_exit on a scratch trades.db:
  S1  credit LOSS  (entry 0.20, exit 0.35, pnl_usd -15) -> pnl_pct -0.75
  S2  credit WIN   (entry 0.20, exit 0.05, pnl_usd +15) -> pnl_pct +0.75
  S3  UNCHANGED: debit WIN  (entry 2.00, exit 3.00, pnl_usd +100) -> +0.50
  S4  UNCHANGED: debit LOSS (entry 2.00, exit 1.50, pnl_usd -50)  -> -0.25
  S5  a zero-premium row stores 0 and does not raise

Run:  python3 tests/check_pnl_pct_sign.py   (exit 0 green, 1 red)
"""
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
_S = tempfile.mkdtemp(prefix="check_pnl_pct_sign_")
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
    from database import trade_logger as tl
    db = os.path.join(_S, "gate_trades.db")
    T = tl.TradeLogger(db_path=db, paper_trading=True)

    def booked(tid, entry, exit_px, pnl_usd, **f):
        T.log_entry(tl.make_record(trade_id=tid, symbol="QQQ", contracts=1, paper_trade=1,
                                   entry_premium=entry, **f))
        T.log_exit(trade_id=tid, exit_price=exit_px, pnl_usd=pnl_usd, exit_reason="gate")
        con = sqlite3.connect(db)
        row = con.execute("SELECT status, pnl_usd, pnl_pct FROM trades WHERE trade_id=?", (tid,)).fetchone()
        con.close()
        return row

    def case(tag, label, tid, entry, exit_px, pnl_usd, want, **f):
        try:
            row = booked(tid, entry, exit_px, pnl_usd, **f)
            ok = row is not None and row[0] == "closed" and row[2] is not None and abs(row[2] - want) < 1e-9
            check(f"{tag} {label}", ok, f"row={row} want pnl_pct {want:+.2f}")
        except Exception as exc:                              # noqa: BLE001
            check(f"{tag} (did not run)", False, f"{type(exc).__name__}: {exc}")

    case("S1", "credit LOSS: entry 0.20 -> 0.35, pnl_usd -15 stores pnl_pct -0.75", "s1", 0.20, 0.35, -15.0, -0.75,
         strategy="SweepCreditSpread", direction="short", is_condor_leg=1)
    case("S2", "credit WIN: entry 0.20 -> 0.05, pnl_usd +15 stores pnl_pct +0.75", "s2", 0.20, 0.05, 15.0, 0.75,
         strategy="SweepCreditSpread", direction="short", is_condor_leg=1)
    case("S3", "UNCHANGED debit WIN: 2.00 -> 3.00, +100 stores +0.50", "s3", 2.00, 3.00, 100.0, 0.50,
         strategy="Breakout", direction="long")
    case("S4", "UNCHANGED debit LOSS: 2.00 -> 1.50, -50 stores -0.25", "s4", 2.00, 1.50, -50.0, -0.25,
         strategy="Breakout", direction="long")
    case("S5", "a zero-premium row stores 0 and does not raise", "s5", 0.0, 0.10, 0.0, 0.0,
         strategy="Breakout", direction="long")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — the stored pnl_pct carries the sign of the booked pnl_usd")
    return 0


if __name__ == "__main__":
    sys.exit(main())
