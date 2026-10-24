#!/usr/bin/env python3
"""tests/check_exit_partial_persist.py  v1.0
B3 — A PARTIAL EXIT SURVIVES A RESTART.

v1.0  2026-10-04  r467. Found by OTV4TEST's live-readiness audit (MSG-1004-15).
      A live close that part-filled kept the filled portions and the working
      order id ONLY on the in-memory record; the row kept the full `contracts`.
      A restart mid-close forgot them, so the next pass submitted the FULL size
      against a smaller holding (a SELL_TO_CLOSE above the held quantity).

Drives the REAL ExitEngine._confirm_and_book_live_exit in LIVE mode against a
REAL TradeLogger on a temp DB. The broker is a fake account whose orders carry
real tastytrade OrderStatus values; the order's (qty, net) fill is stubbed at
_net_fill_price (its per-structure basis is pinned elsewhere). A "restart" is a
NEW ExitEngine and a record re-read from the DB — nothing carried in memory.

  P1  pass 1: 5 to close, 3 fill @1.20, the order dies -> partial, nothing booked
  P2  after a restart the next pass submits 2, not 5
  P3  the booked price is the weighted average of BOTH fills (3@1.20 + 2@1.00 = 1.12)
  P4  once booked the row's kept exit state is cleared
  P5  a kill mid-poll: the working order id is already in the row while polling,
      so the restarted engine RESUMES that order and submits nothing new
  P6  the resumed order's fill completes the close at the weighted price

Run:  python3 tests/check_exit_partial_persist.py
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "SYN")
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


class _Order:
    def __init__(self, oid, status, fill):
        self.id, self.status, self._fill = oid, status, fill
        self.reject_reason = None


class _Broker:
    """get_order returns whatever script says for that order id."""
    def __init__(self):
        self.orders, self.submitted, self.on_poll = {}, [], None

    def get_order(self, session, oid):
        if self.on_poll:
            self.on_poll(oid)
        return self.orders[oid]

    def delete_order(self, session, oid):
        return None


def main():
    print("check_exit_partial_persist")
    from tastytrade.order import OrderStatus
    import config as _cfg
    import database.trade_logger as TL
    import execution.exit_engine as EE

    _cfg.LIVE_FILL_POLL_SECONDS = 0.0
    _cfg.LIVE_FILL_DEADLINE_SECONDS = 0.0

    tmp = tempfile.mkdtemp()
    tl = TL.TradeLogger(os.path.join(tmp, "t.db"), paper_trading=False)
    TL._trade_logger = tl
    broker = _Broker()
    EE.get_session = lambda: "S"
    EE.get_account = lambda: broker

    def engine():
        e = EE.ExitEngine(paper_trading=False)
        e._net_fill_price = lambda record, placed: placed._fill

        def submit(record, contracts, mark, reason=""):
            oid = f"O{len(broker.submitted) + 1}"
            broker.submitted.append((oid, contracts))
            make = (broker.script.pop(0) if broker.script else    # unscripted: fills what was sent
                    lambda o: _Order(o, OrderStatus.FILLED, (float(contracts), float(mark or 0))))
            broker.orders[oid] = make(oid)
            return broker.orders[oid]
        e._submit_live_close = submit
        e._alert_live_exit_once = lambda *a, **k: None
        return e

    def reread(tid):
        with tl._db() as conn:
            row = conn.execute("SELECT * FROM trades WHERE trade_id=?", (tid,)).fetchone()
        return TL.make_record(**dict(row))

    def new_row(tid):
        rec = TL.make_record(trade_id=tid, symbol="SYN", strategy="ORBStrategy",
                             setup_type="ORB", option_side="call", contracts=5,
                             entry_premium=1.50, total_cost=750.0, max_loss=750.0,
                             stop_premium=0.0, option_symbol="SYN   261016C00100000",
                             expiry="2099-01-01")
        tl.log_entry(rec)
        return reread(tid)

    # ── P1-P4: partial, restart, remainder ───────────────────────────────
    rec = new_row("B3-A")
    broker.script = [lambda oid: _Order(oid, OrderStatus.CANCELLED, (3.0, 1.20))]
    r1 = engine()._confirm_and_book_live_exit(rec, "target", 1.20)
    check("P1 pass 1: 3 of 5 fill, the order dies -> partial, nothing booked",
          not r1.confirmed and r1.partial, f"confirmed={r1.confirmed} partial={r1.partial} {r1.detail}")

    rec = reread("B3-A")                       # RESTART: nothing carried in memory
    broker.submitted.clear()
    broker.script = [lambda oid: _Order(oid, OrderStatus.FILLED, (2.0, 1.00))]
    r2 = engine()._confirm_and_book_live_exit(rec, "target", 1.00)
    qty = broker.submitted[0][1] if broker.submitted else None
    check("P2 after a restart the next pass submits 2, not 5", qty == 2, f"submitted qty={qty}")
    check("P3 the booked price is the weighted average of BOTH fills (1.12)",
          r2.confirmed and r2.fill_price is not None and abs(r2.fill_price - 1.12) < 1e-9,
          f"confirmed={r2.confirmed} fill_price={r2.fill_price}")
    check("P4 once booked the row's kept exit state is cleared",
          not reread("B3-A").get("live_exit_state"), f"{reread('B3-A').get('live_exit_state')!r}")

    # ── P5-P6: killed while polling a working order ──────────────────────
    rec = new_row("B3-B")
    broker.submitted.clear()
    seen = {}

    class _Killed(BaseException):
        pass

    def die_on_poll(oid):
        seen["row"] = reread("B3-B").get("live_exit_state")
        raise _Killed()
    broker.on_poll = die_on_poll
    broker.script = [lambda oid: _Order(oid, OrderStatus.LIVE, None)]
    e = engine()
    # seen['row'] is read DURING the poll, before any finally could save
    try:
        e._confirm_and_book_live_exit(rec, "target", 1.10)
    except _Killed:
        pass
    broker.on_poll = None
    oid = broker.submitted[0][0] if broker.submitted else None
    rec = reread("B3-B")
    broker.orders[oid] = _Order(oid, OrderStatus.FILLED, (5.0, 1.10)) if oid else None
    n_before = len(broker.submitted)
    r3 = engine()._confirm_and_book_live_exit(rec, "target", 1.10)
    check("P5 the working order id was in the row while polling; the restart resumes it, no new submit",
          bool(seen.get("row")) and oid in (seen.get("row") or "") and len(broker.submitted) == n_before,
          f"row while polling={seen.get('row')!r}; submits after restart={len(broker.submitted) - n_before}")
    check("P6 the resumed order's fill completes the close",
          r3.confirmed and r3.fill_price is not None and abs(r3.fill_price - 1.10) < 1e-9,
          f"confirmed={r3.confirmed} fill_price={r3.fill_price} {r3.detail}")

    print()
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {', '.join(p.split()[0] for p in PROBLEMS)}")
        return 1
    print("GREEN — every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
