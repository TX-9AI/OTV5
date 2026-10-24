#!/usr/bin/env python3
"""tests/check_sweep_stop.py  v1.0
THE SWEEP'S PREMIUM STOP IS THE CREDIT PLUS 15% OF THE RISK (PLAN_SPEC §31).

v1.0  2026-09-13  OTV4TEST r24. `_execute_condor_leg` stamped the sweep's
      `stop_premium` as `fill_credit * 1.15` — fifteen percent of the CREDIT,
      the inverted rule r155 deleted — and the management plan acts on the row.
      Friday 2026-09-11, 12:04: a 718/719 call spread for 0.25 carried a
      0.2875 stop, was cut the same minute, and expired worthless.

🔑 HOP 0 (WORKING_AGREEMENT §21): S1-S3 DRIVE `main._execute_condor_leg`
itself, in LIVE mode with the placer faked, and read the stop off the record
the position manager holds and off the row in a TEMP trades.db — never a
formula re-derived here. The fixture is Friday's real spread.

  S1  a sweep spread's stop = credit + 15% of (width - credit)       [0.3625]
  S2  ...and it is `criteria.stop_distance`, the one shared definition
  S3  a TCS still carries NO premium stop (control, unchanged)
  S4  unmeasurable risk fails CLOSED to the credit-anchored stop, never 0.0

Born red at 21257bf on S1, S2 and S4 (S1 reproduces Friday's exact 0.2875 through
the real entry path; S4 because the helper does not exist there); S3 is the control.
Run:  python3 tests/check_sweep_stop.py
"""
import os
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")
os.environ.setdefault("OT_INSTRUMENT", "SYN")
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


class _C:
    def __init__(self, symbol, strike, bid, ask):
        self.symbol, self.strike, self.bid, self.ask = symbol, float(strike), bid, ask
        self.mark = (bid + ask) / 2
        self.delta = 0.3


class _Fill:
    def __init__(self, filled, qty=0, net=None, oid="O1"):
        self.filled, self.quantity, self.net_price = filled, qty, net
        self.order_id, self.detail, self.working_order_id = oid, "", None


def _enter(main, strategy, setup, credit, short, long_, side, qty=14):
    """One LIVE entry through the real path; returns (record, row stop)."""
    import database.trade_logger as _tl
    from database.trade_logger import TradeLogger
    import execution.position_manager as _pm
    from execution import ladder_registry as lr
    from strategy.base_strategy import OptionsSignal
    try:
        from execution import credit_remainder as cr
        cr.reset_all()
    except Exception:                                           # noqa: BLE001
        pass
    lr.reset_all()
    _tl._trade_logger = TradeLogger(os.path.join(tempfile.mkdtemp(), "t.db"))
    _pm._position_manager = None

    class _Sz:
        allowed, contracts, reject_reason = True, qty, ""
        total_cost = max_loss = 0.0

    class _RM:
        def size_for(self, *a, **k): return _Sz()

    class _AM:
        def _send(self, *a, **k): pass
        def send_entry_alert(self, *a, **k): pass

    saved = (main.get_risk_manager, main.get_alert_manager, main.entries_open,
             main._post_credit_vertical)
    main.get_risk_manager = lambda: _RM()
    main.get_alert_manager = lambda: _AM()
    main.entries_open = lambda: True
    main._post_credit_vertical = lambda *a, **k: (_Fill(True, qty, credit, "O1"), credit, "rung 1")
    try:
        sig = OptionsSignal()
        sig.strategy_name, sig.setup_type, sig.option_side = strategy, setup, side
        if side == "call":
            sig.short_call_contract, sig.long_call_contract = short, long_
        else:
            sig.short_put_contract, sig.long_put_contract = short, long_
        sig.net_credit = credit
        sig.max_loss_pct = 0.15
        sig.pool_price = 717.05
        sig.is_trend_credit = (strategy == "TrendCreditSpread")
        state = main.BotState(); state.paper_trading = False
        main._execute_condor_leg(sig, state, None)
    finally:
        (main.get_risk_manager, main.get_alert_manager, main.entries_open,
         main._post_credit_vertical) = saved
    recs = _pm.get_position_manager(False).get_open_records()
    if not recs:
        return None, None
    return recs[0], _tl._trade_logger._get_field(recs[0]["trade_id"], "stop_premium")


def main_():
    import main
    from strategy.criteria import stop_distance
    short, long_ = _C("SYN C718", 718, 0.50, 0.51), _C("SYN C719", 719, 0.24, 0.25)

    rec, row = _enter(main, "SweepCreditSpread", "sweep_credit_spread", 0.25, short, long_, "call")
    want = 0.25 + 0.15 * (1.0 - 0.25)
    got = float(rec.get("stop_premium") or 0.0) if rec else None
    check("S1 a sweep spread's stop = credit + 15% of the risk (Friday 12:04: 0.3625, not 0.2875)",
          rec is not None and abs(got - want) < 1e-9 and abs(float(row) - want) < 1e-9,
          f"record={got} row={row} want={want:.4f}")
    check("S2 ...and it is criteria.stop_distance — the one shared definition",
          rec is not None and abs(got - (0.25 + stop_distance(1.0, 0.25))) < 1e-9, f"record={got}")

    rec_t, row_t = _enter(main, "TrendCreditSpread", "TCS 50-accept", 0.75,
                          _C("SYN P99", 99, 1.00, 1.20), _C("SYN P94", 94, 0.30, 0.40), "put", qty=4)
    check("S3 a TCS still carries NO premium stop (control)",
          rec_t is not None and float(rec_t.get("stop_premium") or 0.0) == 0.0,
          f"stop={rec_t.get('stop_premium') if rec_t else None}")

    fn = getattr(main, "_sweep_stop_premium", None)
    check("S4 unmeasurable risk fails CLOSED to the credit-anchored stop, never 0.0",
          fn is not None and abs(fn(0.25, 0.0, 0.15) - 0.2875) < 1e-9,
          "helper absent" if fn is None else f"got {fn(0.25, 0.0, 0.15)}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + "; ".join(_fails))
        return 1
    print("PASS — check_sweep_stop")
    return 0


if __name__ == "__main__":
    sys.exit(main_())
