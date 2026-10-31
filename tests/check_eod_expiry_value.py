#!/usr/bin/env python3
"""
tests/check_eod_expiry_value.py  v5.1
v5.1  2026-10-31  OTV5 r68 (CFG.5) — the PM._rs.active_mode stub is gone with the resting stop (deleted; the operator, 2026-10-31:
      "Resting stop was a study. It failed. Get this the fuck out of here"): it pinned the rest OFF, which is now the only path. No check changed.
v5.0  2026-10-27  OTV5 r42 (EOD.3) — THE 15:55 ESTIMATE PRICES EACH LEG TO ITS OWN EXPIRY.
      CVX 2026-10-27, trade 006f6eca: a Breakout long 8 x 230P expiring Fri 10-30, entry 3.06. At the 15:55 cross
      the quote was 3.70 / 4.85 (mark 4.225-4.28), but _eod_best_case priced the put with 5 minutes left - its
      intrinsic 1.26 at spot 228.74 - _eod_determined called that "settled", and paper booked 1.25: -$1,448 instead
      of about +$976. The same close logged "Position closed ... exit=$4.28" while the ledger held 1.25.
      Driven through the REAL paper ExitEngine.place_exit_order and the REAL PositionManager._execute_exit.

  E1  the CVX record at the 15:55 cross books at the MARK (4.28), not at intrinsic less a tick
  E2  _eod_best_case for that record keeps its three days of time value (estimate > 2.50)
  E3  0DTE unchanged: a deep-ITM long expiring today is still SETTLED at parity less a tick (EOD.1)
  E4  0DTE unchanged: an OTM long expiring today is still settled (its 15:55 value is the expiry value)
  E5  the close line logs the BOOKED fill (exit=$1.25 when the engine fills 1.25) and the mark beside it

Born red on 2f7f4c8 at E1, E2 and E5.
Run:  python3 tests/check_eod_expiry_value.py
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
os.environ.setdefault("OT_INSTRUMENT", "CVX")
_s = tempfile.mkdtemp(prefix="check_eod_expiry_value.")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_s, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))
ET = ZoneInfo("America/New_York")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


CROSS = D.datetime(2026, 10, 27, 15, 55, 4, tzinfo=ET)          # the real trade's cross, a Tuesday
WHY = "hard_close_ladder_15:50_ET"
CVX = {"trade_id": "006f6eca-replay", "strategy": "Breakout", "symbol": "CVX", "direction": "short",
       "option_symbol": "CVX   261030P00230000", "entry_premium": 3.06, "contracts": 8,
       "underlying_entry": 230.775, "_eod_spot": 228.74,
       "_eod_iv": {"CVX   261030P00230000": 0.40}, "_eod_iv_atm": 0.40}


def odte(strike_spot, sym):
    return dict(CVX, trade_id="odte-" + sym[-9:], option_symbol=sym, _eod_spot=strike_spot,
                _eod_iv={sym: 0.40}, _eod_iv_atm=0.40)


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
        EE.now_et = lambda: CROSS
        f1 = eng.place_exit_order(dict(CVX), WHY, mark_price=4.28)
        est = EE.ExitEngine._eod_best_case(dict(CVX))
        itm = odte(220.0, "CVX   261027P00230000")             # 0DTE, 10 points ITM
        f3 = eng.place_exit_order(dict(itm), WHY, mark_price=9.80)
        otm = odte(235.0, "CVX   261027P00230000")             # 0DTE, 5 points OTM
        d4 = EE.ExitEngine._eod_determined(dict(otm))
    finally:
        EE.now_et = _real
    check("E1 CVX 10-30 230P at the 15:55 cross books at the mark 4.28, not intrinsic less a tick",
          f1.confirmed and f1.fill_price is not None and abs(f1.fill_price - 4.28) < 1e-9,
          f"fill={f1.fill_price} ({f1.detail})")
    check("E2 its 15:55 estimate keeps three days of time value (> 2.50)",
          est is not None and est[0] > 2.50, f"estimate={est}")
    check("E3 0DTE deep-ITM long is still settled at parity less a tick",
          f3.confirmed and f3.fill_price is not None and 9.90 <= f3.fill_price < 10.0 and "settled" in f3.detail,
          f"fill={f3.fill_price} ({f3.detail})")
    check("E4 0DTE OTM long is still settled (expiry value)", d4 is not None, f"determined={d4}")

    cap = _Cap(); lg = logging.getLogger("execution.position_manager"); lg.addHandler(cap); lg.setLevel(logging.DEBUG)
    from unittest import mock
    self_ = mock.MagicMock(paper_trading=True)          # the ledger, risk and notifier calls are not under test

    class _Fill(EE.ExitEngine):                           # the real engine, its fill pinned to the ledger's 1.25
        def place_exit_order(self, record, reason, mark_price=None):
            return EE.FillResult(confirmed=True, fill_price=1.25, detail="replay")
    _gee = PM.get_exit_engine
    try:
        _fe = _Fill(True)
        PM.get_exit_engine = lambda paper=True: _fe
        try:
            PM.PositionManager._execute_exit(self_, dict(CVX), EE.ExitDecision(True, WHY), 4.28)
        except Exception as exc:                                   # noqa: BLE001
            print(f"      (_execute_exit raised after the fill: {type(exc).__name__}: {exc})")
    finally:
        PM.get_exit_engine = _gee
    lines = [m for lv, m in cap.recs if "Position closed" in m]
    check("E5 the close line logs the booked fill and the mark beside it",
          len(lines) == 1 and "exit=$1.25" in lines[0] and "mark=$4.28" in lines[0],
          lines[0] if lines else "no close line")

    shutil.rmtree(_s, ignore_errors=True)
    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
