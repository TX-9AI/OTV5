#!/usr/bin/env python3
"""tests/check_no_mark_close.py  v1.0 (OTV4TEST)
F3, MIRRORED FROM otv4 r475 (5270801) - NO MARKET CLOSE FOR WANT OF A MARK BEFORE THE CROSS.

v1.0  2026-10-06  OTV4TEST r256. otv4's gate (file sha256 d530b62e7932e840..., body from
      `import datetime as dt` c0ecab09c1967b85..., verified on this side) with THREE stated
      changes, because the logic is identical and only the CLOCK differs (WA 38.9 criterion 1):
      - THE CROSS IS 15:55 HERE (EOD.1, r149: hard_close_order_mode -> "market" at
        config EOD_CROSS_AT_ET), 15:45 on mainline. N3 runs at 15:56 (was 15:46), and
        N3b and N3c are ADDED: 15:46 and 15:52 (the 15:50 ladder) with no mark post
        NOTHING here (mainline would cross at both). N3c kills the mutant "cross from
        the ladder", which survived without it.
      - N6/N7 ARE DROPPED: they pin WDOG.2, which is otv4-only (its watchdog crosses
        only for a reason containing "hard_close"); this tree crosses by the clock and
        its watchdog's 15:50 close ladders by design (r168, EOD.1). 1-REPORTER, 10-06:
        "Your tree crosses by the clock, so nothing to mirror there."
      - The header and these lines. Nothing else.

Drives the REAL ExitEngine._close_single_leg (LIVE) with a fake account and a pinned ET
clock, and the REAL live close for the page/alert path.

  N1  10:30 ET, no mark: NOTHING posted, one "nomark" page (a second try pages no more)
  N2  10:30 ET, mark 0.0: nothing posted
  N3  15:56 ET, no mark: a MARKET order (the position must close)
  N3b 15:46 ET, no mark: NOTHING posted (this tree's cross is 15:55)
  N3c 15:52 ET, no mark: NOTHING posted (the 15:50 ladder is not the cross)
  N4  UNCHANGED: 10:30 ET with a mark posts a LIMIT
  N5  the full live close at 10:30 with no mark returns unconfirmed "no mark", and the
      generic "SUBMIT FAILED" alert does NOT also fire (one message per event)

Run:  python3 tests/check_no_mark_close.py   (needs the venv's tastytrade)
"""
import datetime as dt
import os
import sys
import tempfile
import types
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "SYN")
ET = ZoneInfo("America/New_York")
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


class _Acct:
    def __init__(self):
        self.orders = []

    def place_order(self, session, order, dry_run=False):
        self.orders.append(order)
        return types.SimpleNamespace(errors=None, order=types.SimpleNamespace(id=f"O{len(self.orders)}"))

    def get_order(self, session, oid):                 # a posted order dies unfilled
        from tastytrade.order import OrderStatus
        return types.SimpleNamespace(id=oid, status=OrderStatus.CANCELLED, legs=[], reject_reason=None)

    def delete_order(self, session, oid):
        return None


def main():
    print("check_no_mark_close")
    try:
        from tastytrade.order import OrderType
    except ImportError as exc:
        print(f"NOT RUN — this interpreter cannot import tastytrade ({exc}); run under the venv")
        return 2
    import config as _cfg
    _cfg.LOG_FILE = os.path.join(tempfile.mkdtemp(), "bot.log")
    import logging
    logging.getLogger("execution.tick_size").setLevel(logging.ERROR)
    import execution.exit_engine as EE
    from execution import ladder_registry as LR

    clock = {"t": dt.datetime(2026, 10, 6, 10, 30, tzinfo=ET)}
    EE.now_et = lambda: clock["t"]
    pages = []
    eng = EE.ExitEngine.__new__(EE.ExitEngine)
    eng.paper_trading = False
    eng._alert_live_exit_once = lambda tid, kind, msg: (
        None if (tid, kind) in {(p[0], p[1]) for p in pages} else pages.append((tid, kind, msg)))

    def rec(tid):
        return {"trade_id": tid, "symbol": "QQQ", "strategy": "RunawayContinuation",
                "option_symbol": "QQQ   261006C00700000", "option_side": "call", "contracts": 2,
                "entry_premium": 1.0, "_exit_bid": 1.00, "_exit_ask": 1.20}

    def close(r, mark, reason="target", force=False):
        LR.reset_all()
        a = _Acct()
        out = eng._close_single_leg("S", a, r, r["contracts"], mark_price=mark,
                                    force_market=force, reason=reason)
        return out, a

    clock["t"] = dt.datetime(2026, 10, 6, 10, 30, tzinfo=ET)
    r1 = rec("N1")
    o1, a1 = close(r1, None)
    o1b, a1b = close(r1, None)
    n1_pages = [p for p in pages if p[0] == "N1"]
    check("N1 10:30, no mark: nothing posted, one 'nomark' page",
          o1 is None and not a1.orders and not a1b.orders and len(n1_pages) == 1
          and n1_pages[0][1] == "nomark", f"orders={len(a1.orders)}/{len(a1b.orders)} pages={n1_pages}")
    o2, a2 = close(rec("N2"), 0.0)
    check("N2 10:30, mark 0.0: nothing posted", o2 is None and not a2.orders, f"orders={len(a2.orders)}")

    clock["t"] = dt.datetime(2026, 10, 6, 15, 46, tzinfo=ET)
    o3b, a3b = close(rec("N3b"), None)
    check("N3b 15:46, no mark: nothing posted (this tree crosses at 15:55)",
          o3b is None and not a3b.orders, f"orders={len(a3b.orders)}")

    clock["t"] = dt.datetime(2026, 10, 6, 15, 52, tzinfo=ET)
    o3c, a3c = close(rec("N3c"), None)
    check("N3c 15:52 (the ladder, before the cross), no mark: nothing posted",
          o3c is None and not a3c.orders, f"orders={len(a3c.orders)}")

    clock["t"] = dt.datetime(2026, 10, 6, 15, 56, tzinfo=ET)
    o3, a3 = close(rec("N3"), None)
    check("N3 15:56, no mark: a MARKET order", len(a3.orders) == 1
          and a3.orders[0].order_type == OrderType.MARKET,
          f"orders={[getattr(o, 'order_type', None) for o in a3.orders]}")

    clock["t"] = dt.datetime(2026, 10, 6, 10, 30, tzinfo=ET)
    o4, a4 = close(rec("N4"), 1.10)
    check("N4 unchanged: 10:30 with a mark posts a LIMIT", len(a4.orders) == 1
          and a4.orders[0].order_type == OrderType.LIMIT,
          f"orders={[getattr(o, 'order_type', None) for o in a4.orders]}")

    # N5 — the full live close, through _confirm_and_book_live_exit_pass
    import database.trade_logger as TL
    tl = TL.TradeLogger(os.path.join(tempfile.mkdtemp(), "t.db"), paper_trading=False)
    TL._trade_logger = tl
    eng5 = EE.ExitEngine(paper_trading=False)
    p5 = []
    eng5._alert_live_exit_once = lambda tid, kind, msg: p5.append(kind)
    acct5 = _Acct()
    EE.get_session, EE.get_account = (lambda: "S"), (lambda: acct5)
    r5 = TL.make_record(trade_id="N5", symbol="QQQ", strategy="RunawayContinuation",
                        setup_type="runaway", option_side="call", contracts=2, entry_premium=1.0,
                        total_cost=200.0, max_loss=200.0, stop_premium=0.8,
                        option_symbol="QQQ   261006C00700000", expiry="2099-01-01")
    tl.log_entry(r5)
    with tl._db() as conn:
        row = conn.execute("SELECT * FROM trades WHERE trade_id='N5'").fetchone()
    try:
        res5 = eng5._confirm_and_book_live_exit(TL.make_record(**dict(row)), "target", None)
    except Exception as exc:                                        # noqa: BLE001
        res5 = types.SimpleNamespace(confirmed=False, detail=f"raised {type(exc).__name__}: {exc}")
    check("N5 full live close, no mark at 10:30: unconfirmed 'no mark', no SUBMIT FAILED alert",
          (not res5.confirmed) and "no mark" in (res5.detail or "") and "submit" not in p5
          and not acct5.orders, f"detail={res5.detail!r} alerts={p5} orders={len(acct5.orders)}")

    print()
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {', '.join(p.split()[0] for p in PROBLEMS)}")
        return 1
    print("GREEN — every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
