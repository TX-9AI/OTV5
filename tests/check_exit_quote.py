#!/usr/bin/env python3
"""
tests/check_exit_quote.py  v1.0
v1.0  2026-10-03  OTV4TEST r195 (AUD.4) — THE EXIT QUOTE AND IV REACH THE TRADE ROW.

  Found by the 10-03 audit: trades.exit_bid / exit_ask / exit_iv were empty on
  237 of 237 closed trades. TradeLogger.set_exit_contract had ZERO callers.

  Drives the REAL PositionManager._fetch_current_premium on the REAL
  OptionsChain / OptionContract, then the REAL _execute_exit (paper fill)
  against a scratch trades.db written by the REAL TradeLogger:
  Q1  single leg: the row carries the contract's bid, ask and IV
  Q2  credit vertical: the row carries the spread's bid/ask (short bid - long
      ask, short ask - long bid) and the SHORT leg's IV
  Q3  butterfly: the row carries the composite quote and the BODY's IV
  Q4  UNCHANGED: the butterfly record still has NO _exit_bid/_exit_ask - the
      exit ladder's pricing keys are not what this writes
  Q5  no quote seen this tick -> the close still books; the columns stay NULL

Run:  python3 tests/check_exit_quote.py   (exit 0 green, 1 red)
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
_S = tempfile.mkdtemp(prefix="check_exit_quote_")
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


class _Alerts:
    def __getattr__(self, _name):
        return lambda *a, **k: None


def main():
    from data.options_chain import OptionContract as OC, OptionsChain
    from database import trade_logger as tl
    from execution import position_manager as PM
    from execution.exit_engine import ExitDecision

    db = os.path.join(_S, "gate_trades.db")
    T = tl.TradeLogger(db_path=db, paper_trading=True)
    PM.get_alert_manager = lambda: _Alerts()                 # nothing pages from a gate

    def C(strike, bid, ask, iv):
        return OC(symbol=f"QQQ   261003C{int(strike * 1000):08d}", strike=strike, option_type="C",
                  bid=bid, ask=ask, mark=round((bid + ask) / 2, 4), iv=iv, delta=0.4)

    chain = OptionsChain(underlying="QQQ", spot_price=745.0,
                         calls=[C(740.0, 5.10, 5.30, 0.21), C(742.0, 3.40, 3.60, 0.20),
                                C(744.0, 2.00, 2.20, 0.19), C(750.0, 0.40, 0.50, 0.18),
                                C(751.0, 0.25, 0.35, 0.17)], puts=[])

    pm = PM.PositionManager.__new__(PM.PositionManager)
    pm.paper_trading = True
    pm._trade_logger = T
    pm._open_records = []

    def run(tid, **fields):
        rec = tl.make_record(trade_id=tid, symbol="QQQ", contracts=1, paper_trade=1,
                             option_side="call", **fields)
        T.log_entry(rec)
        return rec

    def close(rec, with_chain=True):
        prem = pm._fetch_current_premium(rec, chain=chain if with_chain else None)
        if prem is None:
            prem = float(rec.get("entry_premium") or 1.0)
        ok = pm._execute_exit(rec, ExitDecision(should_exit=True, exit_reason="gate_close"), prem)
        con = sqlite3.connect(db)
        row = con.execute("SELECT status, exit_bid, exit_ask, exit_iv FROM trades WHERE trade_id=?",
                          (rec["trade_id"],)).fetchone()
        con.close()
        return ok, row

    def near(a, b):
        return a is not None and abs(float(a) - b) < 1e-6

    # Q1 — single leg
    try:
        rec = run("q1-single", strategy="Breakout", direction="long", strike=744.0, entry_premium=2.00)
        ok, row = close(rec)
        check("Q1 single leg: exit_bid 2.00, exit_ask 2.20, exit_iv 0.19 on the closed row",
              ok and row and row[0] == "closed" and near(row[1], 2.00) and near(row[2], 2.20) and near(row[3], 0.19),
              f"closed={ok} row={row}")
    except Exception as exc:                                  # noqa: BLE001
        check("Q1 (did not run)", False, f"{type(exc).__name__}: {exc}")

    # Q2 — credit vertical: short 750 / long 751
    try:
        rec = run("q2-vert", strategy="SweepCreditSpread", direction="short", is_condor_leg=1,
                  short_strike=750.0, long_strike=751.0, spread_width=1.0, entry_premium=0.20)
        ok, row = close(rec)
        check("Q2 credit vertical: bid 0.05 (0.40-0.35), ask 0.25 (0.50-0.25), the SHORT leg's IV 0.18",
              ok and row and row[0] == "closed" and near(row[1], 0.05) and near(row[2], 0.25) and near(row[3], 0.18),
              f"closed={ok} row={row}")
    except Exception as exc:                                  # noqa: BLE001
        check("Q2 (did not run)", False, f"{type(exc).__name__}: {exc}")

    # Q3 / Q4 — butterfly 740 / 742 / 744
    try:
        rec = run("q3-fly", strategy="GEXPinButterfly", direction="neutral", is_butterfly=1,
                  lower_strike=740.0, center_strike=742.0, upper_strike=744.0, entry_premium=0.40)
        ok, row = close(rec)
        # bid = 5.10 + 2.00 - 2*3.60 = -0.10 -> 0.0 ; ask = 5.30 + 2.20 - 2*3.40 = 0.70 ; body IV 0.20
        check("Q3 butterfly: composite bid 0.00, ask 0.70, the BODY's IV 0.20",
              ok and row and row[0] == "closed" and near(row[1], 0.0) and near(row[2], 0.70) and near(row[3], 0.20),
              f"closed={ok} row={row}")
        check("Q4 UNCHANGED: the butterfly record has no _exit_bid/_exit_ask (ladder pricing keys untouched)",
              "_exit_bid" not in rec and "_exit_ask" not in rec,
              f"_exit_bid={rec.get('_exit_bid')!r} _exit_ask={rec.get('_exit_ask')!r}")
    except Exception as exc:                                  # noqa: BLE001
        check("Q3 (did not run)", False, f"{type(exc).__name__}: {exc}")

    # Q5 — no chain this tick: the close books, the columns stay NULL
    try:
        rec = run("q5-noquote", strategy="Breakout", direction="long", strike=744.0, entry_premium=2.00)
        ok, row = close(rec, with_chain=False)
        check("Q5 no quote this tick: the close still books and the columns stay NULL",
              ok and row and row[0] == "closed" and row[1] is None and row[2] is None and row[3] is None,
              f"closed={ok} row={row}")
    except Exception as exc:                                  # noqa: BLE001
        check("Q5 (did not run)", False, f"{type(exc).__name__}: {exc}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — the exit quote and IV are written at the confirmed close")
    return 0


if __name__ == "__main__":
    sys.exit(main())
