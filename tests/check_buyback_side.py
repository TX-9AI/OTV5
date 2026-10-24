#!/usr/bin/env python3
"""tests/check_buyback_side.py  v1.1
BBK.1 — A SINGLE-LEG BUY-BACK IS PRICED AS A BUY.

v1.1  2026-10-07  OTV4TEST r260, MIRRORED FROM otv4 r476 (29efd7e) — B5 WAS TIME-OF-DAY
      DEPENDENT SINCE r256 (F3, otv4 r475). B5 sends a no-mark close and expects MARKET; since
      F3 that is true only at/after the cross (15:55 here, 15:45 on mainline), so before it B5
      crashed (AttributeError on a __new__-built engine's page) and the check went red — every
      sweep after r256 ran in the evening. Found by this tree's 08:00 sweep 2026-10-07
      (MSG-1007-01; SPX-TEST's sweep found it independently); 1-REPORTER authored the fix. B5
      now PINS exit_engine.now_et to limit_ladder.HARD_CLOSE_MARKET_AT_ET (read from this
      tree's module) and restores it; new B5b pins 10:00 and asserts a no-mark close posts
      NOTHING (F3). Body byte-identical to otv4 r476 from the first `import` line. Test-only.

v1.0  2026-10-04  r470. Operator (via OTV4TEST, 19:39 ET): "Have reporter do the
      buy-back & run the fix by you for a sanity check." _close_single_leg sent
      BUY_TO_CLOSE for a short single but asked _exit_limit for the "sell" side,
      so the walk started near the ask and stepped down, and the floor snap
      rounded up: a live buy-back paying above its mark.

Drives the REAL ExitEngine._close_single_leg (LIVE path, fake account recording
every order) with the REAL _exit_limit, ladder_registry and tick_size. The short
fixture sets BOTH is_short_position and credit_received, so either tree's
BUY_TO_CLOSE predicate (OTV4TEST's flag, otv4's is_credit_position) selects it.
The side under test is read off the posted order's ACTION, not off a predicate.

  B1  short single, walk (QQQ 1.00/1.20, mark 1.10): BUY_TO_CLOSE, first limit
      at or below mark
  B2  ... and after a refusal the next limit walks UP, still at or below mark
  B3  short single, floor stop on a nickel grid (XYZ 1.10/1.15, mark 1.125):
      the limit is at or below mark (1.10, never 1.15)
  B4  UNCHANGED: long single, walk: SELL_TO_CLOSE, first limit at or above mark,
      next limit walks DOWN
  B5  UNCHANGED: no mark AT THE CROSS (clock pinned to HARD_CLOSE_MARKET_AT_ET) -> MARKET
      order, BUY_TO_CLOSE for the short
  B5b no mark at 10:00 (clock pinned) -> nothing posted (F3, r475)
  B6  the posted price is signed as a debit for a buy-back (negative)

Run:  python3 tests/check_buyback_side.py   (needs the venv's tastytrade)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "SYN")
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


class _Resp:
    def __init__(self, oid):
        self.errors = None
        self.order = type("P", (), {"id": oid})()


class _Account:
    def __init__(self):
        self.orders = []

    def place_order(self, session, order, dry_run=False):
        self.orders.append(order)
        return _Resp(f"O{len(self.orders)}")


def main():
    print("check_buyback_side")
    try:
        from tastytrade.order import OrderAction, OrderType
    except ImportError as exc:
        print(f"NOT RUN — this interpreter cannot import tastytrade ({exc}); run under the venv")
        return 2
    import logging
    logging.getLogger("execution.tick_size").setLevel(logging.ERROR)
    import execution.exit_engine as EE
    from execution import ladder_registry as LR

    eng = EE.ExitEngine.__new__(EE.ExitEngine)
    eng.paper_trading = False

    def rec(tid, symbol, bid, ask, short):
        r = {"trade_id": tid, "symbol": symbol, "strategy": "ORBStrategy",
             "option_symbol": f"{symbol}   261016C00100000", "option_side": "call",
             "contracts": 2, "entry_premium": 1.0, "_exit_bid": bid, "_exit_ask": ask}
        if short:
            r.update(is_short_position=1, credit_received=1.0)
        return r

    def post(r, mark, reason, acct):
        n = len(acct.orders)
        placed = eng._close_single_leg("S", acct, r, r["contracts"], mark_price=mark, reason=reason)
        o = acct.orders[n] if len(acct.orders) > n else None
        leg = o.legs[0] if o is not None else None
        px = getattr(o, "price", None)
        return placed, o, leg, (float(px) if px is not None else None)

    # B1/B2/B6 — short single, walk
    LR.reset_all()
    acct = _Account()
    r = rec("BBK-S1", "QQQ", 1.00, 1.20, short=True)
    _, o1, leg1, p1 = post(r, 1.10, "target", acct)
    lim1 = r.get("_exit_last_limit")
    check("B1 short single, walk: BUY_TO_CLOSE and first limit <= mark 1.10",
          leg1 is not None and leg1.action == OrderAction.BUY_TO_CLOSE
          and lim1 is not None and lim1 <= 1.10 + 1e-9,
          f"action={getattr(leg1, 'action', None)} limit={lim1}")
    check("B6 a buy-back posts a debit (negative signed price)",
          p1 is not None and p1 < 0, f"signed price={p1}")
    eng._exit_walk_refused(r, lim1)
    post(r, 1.10, "target", acct)
    lim2 = r.get("_exit_last_limit")
    check("B2 after a refusal the buy-back walks UP, still <= mark",
          lim1 is not None and lim2 is not None and lim2 > lim1 and lim2 <= 1.10 + 1e-9,
          f"first={lim1} next={lim2}")

    # B3 — short single, floor stop on a nickel grid
    LR.reset_all()
    r = rec("BBK-S2", "XYZ", 1.10, 1.15, short=True)
    post(r, 1.125, "hard_stop", _Account())
    lim = r.get("_exit_last_limit")
    check("B3 floor stop, nickel grid: buy-back limit <= mark 1.125 (1.10, never 1.15)",
          lim is not None and lim <= 1.125 + 1e-9, f"limit={lim}")

    # B4 — long single unchanged
    LR.reset_all()
    acct = _Account()
    r = rec("BBK-L1", "QQQ", 1.00, 1.20, short=False)
    _, _, legL, _ = post(r, 1.10, "target", acct)
    l1 = r.get("_exit_last_limit")
    eng._exit_walk_refused(r, l1)
    post(r, 1.10, "target", acct)
    l2 = r.get("_exit_last_limit")
    check("B4 long single unchanged: SELL_TO_CLOSE, first >= mark, then walks DOWN",
          legL is not None and legL.action == OrderAction.SELL_TO_CLOSE
          and l1 is not None and l1 >= 1.10 - 1e-9 and l2 is not None and l2 < l1,
          f"action={getattr(legL, 'action', None)} first={l1} next={l2}")

    # B5 / B5b — the no-mark branch, with the clock PINNED (r476): since F3 (r475) the answer
    # depends on the time of day, so an unpinned check was green only after 15:45.
    import datetime as _dt
    from zoneinfo import ZoneInfo as _ZI
    from execution.limit_ladder import HARD_CLOSE_MARKET_AT_ET as _CROSS
    _real_now = EE.now_et
    _alerted = []
    eng._alert_live_exit_once = lambda *a, **k: _alerted.append(a[1] if len(a) > 1 else None)
    try:
        EE.now_et = lambda: _dt.datetime.combine(_dt.date(2026, 10, 7), _CROSS, tzinfo=_ZI("America/New_York"))
        LR.reset_all()
        r = rec("BBK-S3", "QQQ", 1.00, 1.20, short=True)
        _, o, leg, _ = post(r, None, "target", _Account())
        check("B5 no mark AT THE CROSS -> MARKET, BUY_TO_CLOSE",
              o is not None and o.order_type == OrderType.MARKET
              and leg.action == OrderAction.BUY_TO_CLOSE,
              f"type={getattr(o, 'order_type', None)} action={getattr(leg, 'action', None)}")
        EE.now_et = lambda: _dt.datetime(2026, 10, 7, 10, 0, tzinfo=_ZI("America/New_York"))
        LR.reset_all()
        r = rec("BBK-S4", "QQQ", 1.00, 1.20, short=True)
        _, o, leg, _ = post(r, None, "target", _Account())
        check("B5b no mark at 10:00 -> nothing posted (F3)",
              o is None and "nomark" in _alerted, f"order={getattr(o, 'order_type', None)} alerts={_alerted}")
    finally:
        EE.now_et = _real_now

    print()
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {', '.join(p.split()[0] for p in PROBLEMS)}")
        return 1
    print("GREEN — every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
