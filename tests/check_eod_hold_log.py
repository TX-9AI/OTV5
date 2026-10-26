#!/usr/bin/env python3
"""
tests/check_eod_hold_log.py  v5.0
v5.0  2026-10-26  OTV5 r36 (EOD.2) — AN INTENDED EOD HOLD IS ONE INFO LINE, NOT AN ERROR EVERY TICK.
      AMD 2026-10-26: the paper EOD close of f819b0bd was held from 15:45 to the 15:55 cross by design (EOD.1), and
      every manage tick logged "Exit NOT confirmed ... will retry" at ERROR - 60 lines. Driven through the REAL paper
      ExitEngine.place_exit_order and the REAL PositionManager._execute_exit (the clock pinned; resting stops off).

  H1  paper, 15:46, a debit hard close: place_exit_order holds it - confirmed False, held True
  H2  at the 15:55 cross the same close fills (confirmed True, held False) - the hold is unchanged
  H3  _execute_exit on that held close, 20 ticks: False every time (the row stays open), ZERO ERROR lines from
      execution.position_manager, exactly ONE INFO line naming the trade
  H4  any other unconfirmed exit (no fill) still logs ERROR on every tick

Born red on 18cac1b at H1 (no held field) and H3 (20 ERROR lines).
Run:  python3 tests/check_eod_hold_log.py
"""
import datetime as D
import logging
import os
import shutil
import sys
import tempfile
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
_s = tempfile.mkdtemp(prefix="check_eod_hold_log.")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_s, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))
ET = ZoneInfo("America/New_York")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def at(h, m):
    return D.datetime(2026, 10, 26, h, m, 5, tzinfo=ET)          # a Monday


ORB = {"trade_id": "f819b0bd-hold", "strategy": "Breakout", "option_symbol": "AMD   261030C00250000",
       "entry_premium": 1.0, "contracts": 5, "symbol": "AMD", "underlying_entry": 250.0}
WHY = "hard_close_ladder_15:50_ET"


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(); self.recs = []

    def emit(self, r):
        if r.name == "execution.position_manager":
            self.recs.append((r.levelno, r.getMessage()))


def main():
    import execution.exit_engine as EE
    import execution.position_manager as PM
    _real = EE.now_et
    eng = EE.ExitEngine(True)
    try:
        EE.now_et = lambda: at(15, 46)
        f1 = eng.place_exit_order(dict(ORB), WHY, mark_price=1.40)
        EE.now_et = lambda: at(15, 55)
        f2 = eng.place_exit_order(dict(ORB), WHY, mark_price=1.40)
    finally:
        EE.now_et = _real
    check("H1 15:46 paper debit hard close is HELD: confirmed False, held True",
          f1.confirmed is False and getattr(f1, "held", None) is True, f"confirmed={f1.confirmed} held={getattr(f1, 'held', 'absent')}")
    check("H2 15:55 the same close fills at the cross (held False)",
          f2.confirmed is True and not getattr(f2, "held", False) and f2.fill_price is not None,
          f"confirmed={f2.confirmed} price={f2.fill_price}")

    cap = _Cap(); lg = logging.getLogger("execution.position_manager"); lg.addHandler(cap); lg.setLevel(logging.DEBUG)
    self_ = type("PMStub", (), {"paper_trading": True})()
    dec = EE.ExitDecision(should_exit=True, exit_reason=WHY)
    _gee, _am = PM.get_exit_engine, PM._rs.active_mode
    try:
        PM._rs.active_mode = lambda paper: "off"
        PM.get_exit_engine = lambda paper=True: eng
        EE.now_et = lambda: at(15, 46)
        rets = [PM.PositionManager._execute_exit(self_, dict(ORB), dec, 1.40) for _ in range(20)]
        errs = [m for lv, m in cap.recs if lv >= logging.ERROR]
        infos = [m for lv, m in cap.recs if lv == logging.INFO and ORB["trade_id"][:8] in m]
        check("H3 20 ticks of the held close: open every time, 0 ERROR lines, exactly 1 INFO naming the trade",
              rets == [False] * 20 and not errs and len(infos) == 1,
              f"returns={sorted(set(rets))} errors={len(errs)} infos={len(infos)}")

        cap.recs.clear()

        class _NoFill:
            def place_exit_order(self, record, reason, mark_price=None):
                return EE.FillResult(confirmed=False, detail="paper: no mark")
        PM.get_exit_engine = lambda paper=True: _NoFill()
        rec = dict(ORB, trade_id="nofill-0001", strategy="Breakout")
        rets = [PM.PositionManager._execute_exit(self_, rec, EE.ExitDecision(True, "stop_loss"), 0.5) for _ in range(3)]
        errs = [m for lv, m in cap.recs if lv >= logging.ERROR and "NOT confirmed" in m]
        check("H4 any other unconfirmed exit still logs ERROR every tick", rets == [False] * 3 and len(errs) == 3,
              f"errors={len(errs)}")
    finally:
        PM.get_exit_engine, PM._rs.active_mode, EE.now_et = _gee, _am, _real

    shutil.rmtree(_s, ignore_errors=True)
    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
