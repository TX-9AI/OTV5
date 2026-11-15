#!/usr/bin/env python3
"""
tests/check_live_stop_escalation.py  v5.2
v5.2  2026-11-15  OTV5 r123 (HYG.27) — OT_RESTING_DB leaves the scratch env (r118 deleted execution/resting_orders.py, its only reader).
v5.1  2026-11-14  OTV5 r112 (AM.2 / LIVE.6) — new. A LIVE STOP STEPS TO THE BID, THEN CROSSES. Driven through the REAL
      ExitEngine._confirm_and_book_live_exit with a stub broker whose every order dies UNFILLED (CANCELLED, no legs), so
      each pass is one unfilled close and the record carries the count to the next pass, as the live retry loop does.

  E1  a hard stop on a long single: pass 1 and pass 2 post LIMIT at the mark (1.10 here)
  E2  pass 3 (config.LIVE_STOP_AT_BID_AFTER = 2 unfilled) posts LIMIT AT THE BID (1.00)
  E3  pass 4 (config.LIVE_STOP_MARKET_AFTER = 3 unfilled) posts a MARKET order
  E4  a target close (walk policy) never escalates: four unfilled passes, no MARKET, none at the bid
  E5  an adopted SHORT's stop buys back AT THE ASK on its third pass (1.20), then MARKET
  E6  at the touch step with no fresh quote (no ask stashed) the stop crosses with MARKET
  E7  the constants are what the spec says (2 and 3) and are not env keys (no OT_ read in config for them)
Born red on r108 (6b380b2): E2 E3 E5 E6 E7 (every pass re-posted at the mark).
Run:  python3 tests/check_live_stop_escalation.py   (needs the venv's tastytrade)
"""
import datetime as D
import logging
import os
import re
import sys
import tempfile
import types
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
_s = tempfile.mkdtemp(prefix="check_live_stop_escalation.")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived_store.db"),
               ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_ALERT_SPOOL", "alert_spool.jsonl")):
    os.environ.setdefault(_k, os.path.join(_s, _f))
ET = ZoneInfo("America/New_York")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


class _Acct:
    """Records every order; every order dies unfilled."""
    def __init__(self):
        self.orders = []

    def place_order(self, session, order, dry_run=False):
        self.orders.append(order)
        return types.SimpleNamespace(errors=None, order=types.SimpleNamespace(id=f"O{len(self.orders)}"))

    def get_order(self, session, oid):
        from tastytrade.order import OrderStatus
        return types.SimpleNamespace(id=oid, status=OrderStatus.CANCELLED, legs=[], reject_reason=None)

    def delete_order(self, session, oid):
        return None


def _desc(o):
    p = getattr(o, "price", None)
    return (str(getattr(o.order_type, "value", o.order_type)), None if p is None else abs(float(p)))


def main():
    print("check_live_stop_escalation")
    try:
        from tastytrade.order import OrderType
    except ImportError as exc:
        print(f"NOT RUN — this interpreter cannot import tastytrade ({exc}); run under the venv")
        return 2
    import config as _cfg
    _cfg.LIVE_FILL_POLL_SECONDS = 0.0
    _cfg.LIVE_FILL_DEADLINE_SECONDS = 0.0
    logging.getLogger("execution.tick_size").setLevel(logging.ERROR)
    import utils.time_utils as TU
    import execution.exit_engine as EE
    import database.trade_logger as TL
    from execution import ladder_registry as LR

    now = D.datetime(2026, 11, 13, 10, 40, 5, tzinfo=ET)
    EE.now_et = lambda: now
    TU.now_et = lambda: now
    acct = {"a": _Acct()}
    EE.get_session, EE.get_account = (lambda: "S"), (lambda: acct["a"])
    tl = TL.get_trade_logger()
    live = EE.ExitEngine(paper_trading=False)
    live._alert_live_exit_once = lambda tid, kind, msg: None

    def single(tid, **kw):
        r = TL.make_record(trade_id=tid, symbol="QQQ", strategy="RunawayContinuation", setup_type="runaway",
                           direction="long", option_side="call", contracts=2, entry_premium=1.40,
                           total_cost=280.0, max_loss=280.0, stop_premium=1.12, strike=700.0,
                           option_symbol="QQQ   261113C00700000", expiry="2026-11-13")
        r.update(kw)
        tl.log_entry(r)
        return r

    def passes(rec, reason, n, mark=1.10, bid=1.00, ask=1.20):
        acct["a"] = _Acct()
        LR.reset_all()
        for _ in range(n):
            if bid is not None:
                rec["_exit_bid"], rec["_exit_ask"] = bid, ask
            else:
                rec.pop("_exit_bid", None); rec.pop("_exit_ask", None)
            live._confirm_and_book_live_exit(rec, reason, mark)
        return [_desc(o) for o in acct["a"].orders]

    got = passes(single("E1-long"), "hard_stop_20% pnl=-21.0%", 4)
    check("E1 hard stop, passes 1-2: LIMIT at the mark 1.10", got[:2] == [("Limit", 1.10), ("Limit", 1.10)], f"{got}")
    check("E2 pass 3 (after 2 unfilled): LIMIT AT THE BID 1.00", len(got) > 2 and got[2] == ("Limit", 1.00), f"{got}")
    check("E3 pass 4 (after 3 unfilled): MARKET", len(got) > 3 and got[3][0] == "Market", f"{got}")

    got = passes(single("E4-target"), "target_hit pnl=100%", 4)
    check("E4 a target close never escalates: no MARKET, never at the bid",
          len(got) == 4 and all(t == "Limit" for t, _ in got) and all(p != 1.00 for _, p in got), f"{got}")

    got = passes(single("E5-short", is_short_position=1, strategy="ADOPTED", setup_type="orphan_adopted"),
                 "adopted_stop", 4)
    check("E5 an adopted short's stop buys back AT THE ASK 1.20 on pass 3, then MARKET",
          len(got) == 4 and got[2] == ("Limit", 1.20) and got[3][0] == "Market", f"{got}")

    got = passes(single("E6-noquote"), "hard_stop_20% pnl=-22.0%", 3, bid=None)
    check("E6 at the touch step with no fresh quote: MARKET", len(got) == 3 and got[2][0] == "Market", f"{got}")

    src = open(os.path.join(ROOT, "config.py")).read()
    no_env = not re.search(r"LIVE_STOP_(AT_BID|MARKET)_AFTER\s*=.*environ", src)
    check("E7 LIVE_STOP_AT_BID_AFTER = 2, LIVE_STOP_MARKET_AFTER = 3, constants (no env key)",
          getattr(_cfg, "LIVE_STOP_AT_BID_AFTER", None) == 2 and getattr(_cfg, "LIVE_STOP_MARKET_AFTER", None) == 3
          and no_env, f"{getattr(_cfg, 'LIVE_STOP_AT_BID_AFTER', None)} {getattr(_cfg, 'LIVE_STOP_MARKET_AFTER', None)}")

    print("=" * 60)
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {FAILED}")
        return 1
    print("GREEN — a live stop steps to the bid, then crosses")
    return 0


if __name__ == "__main__":
    sys.exit(main())
