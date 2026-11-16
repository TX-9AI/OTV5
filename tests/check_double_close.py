#!/usr/bin/env python3
"""
tests/check_double_close.py  v5.0
v5.0  2026-11-16  OTV5 r128 (ERC.1 / FA.2 with MC.1 / FA.4; the cold audit 2026-11-15, critical) — NEW. ONE POSITION
      NEVER GETS A SECOND CLOSE: NOT AFTER A LOST close REPLY, NOT AFTER A BOOKING WRITE THAT RAISED.

  🔴 THE DEFECTS (OTV5 r127 3db1001):
  ERC.1  exit_engine._submit_live_close swallowed a place_order that RAISED (the reply lost: run_async's 30 s timeout,
         a reset mid-read) and returned None with no order id stored, so the next pass posted a fresh full-size close
         beside one working at the broker (at 15:55 two MARKET orders). Two closes for one contract: a short if the
         broker takes both.
  MC.1   position_manager._execute_exit called log_exit unwrapped AFTER a confirmed close fill (the fills already popped,
         live_exit_state NULL). A raise (sqlite I/O error, full disk) left the record managed with nothing remembered,
         so the next pass posted a fresh close for contracts the account no longer held.

  OFFLINE, on the shared misbehaving broker (tests/broker_harness.py; no network, no credentials). The real
  ExitEngine (live) and the real PositionManager._execute_exit, on a temp trades.db. The broker holds 1 contract.
  D1  reply lost, the close FILLED at the broker -> the next pass ADOPTS it and books its fill; one order, flat, not short
  D2  reply lost, the close rests LIVE -> the next pass adopts and tracks it (cancelled at the deadline, then a new
      rung); never two working closes, flat at the end, not short
  D3  reply lost, the order still in flight (not in the book) -> nothing posts inside the grace; once visible it is
      adopted, still one order
  D4  place_order raised and NOTHING was accepted -> nothing inside the grace; then, the book empty and the position
      still held, ONE fresh close posts and fills (a held position is never blocked forever)
  D5  reply lost and the book UNREADABLE -> nothing posts (fail closed)
  D6  nothing in the book and the broker NO LONGER holds the position -> nothing posts (no short), position 0
  D7  a restart after a lost reply (new engine, record re-read from the row) -> adopts, posts nothing new
  D8  the 15:55 cross: a lost MARKET close -> no second MARKET order; flat, not short
  D9  a credit vertical's lost close (2 legs) -> adopted and booked, one order
  D10 an earlier rung of the same close that died part-filled is never adopted as the lost one (no double-counted fill)
  B1  the close FILLED and log_exit RAISED once -> no new order; the next pass writes the row (closed, the broker's fill)
  B2  log_exit keeps raising for 3 passes, and the records are re-read from the DB -> still ONE order, flat, not short
  B3  paper: log_exit raised once -> the next pass re-writes the SAME fill (place_exit_order is not called again)
  B4  a step after the booking (the exit alert) raises -> the close stands (returns True), no second order
  B5  paper normal path: one clean exit books once at the mark (unchanged)
  B6  the next manage pass writes the pending row first, even with no mark this tick, and drops the record
  BORN RED on r127 3db1001 (see docs/BACKLOG.md ERC.1 for the list).

Run:  python3 tests/check_double_close.py
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
import config                                                         # noqa: E402
_TMP = tempfile.mkdtemp(prefix="check_double_close_")
config.LOG_FILE = os.path.join(_TMP, "bot.log")
config.LIVE_FILL_POLL_SECONDS = 0.0
config.LIVE_FILL_DEADLINE_SECONDS = 0.0
from broker_harness import MisbehavingBroker, bind                    # noqa: E402

PROBLEMS = []
SYM = "QQQ   261116C00500000"
SHORT = "QQQ   261116P00495000"
LONG = "QQQ   261116P00490000"


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


import database.trade_logger as TL                                    # noqa: E402
import execution.exit_engine as EE                                    # noqa: E402
import execution.position_manager as PM                               # noqa: E402

TLOG = TL.TradeLogger(os.path.join(_TMP, "t.db"), paper_trading=False)
TL._trade_logger = TLOG
_N = [0]


def _row(vertical=False):
    _N[0] += 1
    tid = f"DC-{_N[0]:03d}-0000"
    kw = dict(trade_id=tid, symbol="QQQ", strategy="RunawayContinuation", setup_type="RUNAWAY",
              option_side="call", contracts=1, entry_premium=1.00, total_cost=100.0, max_loss=100.0,
              stop_premium=0.0, option_symbol=SYM, expiry="2099-01-01")
    if vertical:
        kw.update(strategy="CreditVertical", option_side="put", option_symbol=SHORT,
                  short_symbol=SHORT, long_symbol=LONG, entry_premium=0.30)
    TLOG.log_entry(TL.make_record(**kw))
    return _reread(tid)


def _reread(tid):
    with TLOG._db() as conn:
        row = conn.execute("SELECT * FROM trades WHERE trade_id=?", (tid,)).fetchone()
    return TL.make_record(**dict(row))


def _status(tid):
    with TLOG._db() as conn:
        r = conn.execute("SELECT status, exit_premium FROM trades WHERE trade_id=?", (tid,)).fetchone()
    return (r[0], r[1]) if r else (None, None)


def _engine():
    e = EE.ExitEngine(paper_trading=False)
    e._alert_live_exit_once = lambda tid, kind, msg: e.__dict__.setdefault("pages", []).append(kind)
    return e


def _age_lost(rec, secs=None):
    """Make a LOST stamp older than the grace (absent on a tree without the fix: nothing to change)."""
    oid = rec.get("_live_exit_order_id")
    tag = getattr(EE, "LOST_CLOSE_TAG", None)
    if tag and isinstance(oid, str) and oid.startswith(tag):
        t0 = float(oid[len(tag):]) - (secs if secs is not None else getattr(EE, "LOST_CLOSE_GRACE_S", 0.0) + 1)
        rec["_live_exit_order_id"] = f"{tag}{t0:.3f}"


def _broker(hold=True, vertical=False):
    b = MisbehavingBroker()
    if hold:
        if vertical:
            b.hold(SHORT, -1, 0.50); b.hold(LONG, +1, 0.20)
        else:
            b.hold(SYM, +1, 1.00)
    return b


def close_cases():
    WHY = "target_hit pnl=+20%"

    # D1 — lost reply, the close FILLED at the broker
    b = _broker(); b.fill_on_accept = 1.20; b.script_place("lost")
    rec = _row(); e = _engine()
    with bind(b, EE):
        r1 = e._confirm_and_book_live_exit(rec, WHY, 1.20)
        r2 = e._confirm_and_book_live_exit(rec, WHY, 1.20)
    check("D1 lost reply + FILLED close: the next pass adopts and books it; ONE order, flat, not short",
          not r1.confirmed and r2.confirmed and abs((r2.fill_price or 0) - 1.20) < 1e-9
          and b.place_calls == 1 and b.position(SYM) == 0,
          f"r1={r1.detail} r2={r2.confirmed}/{r2.fill_price}/{r2.detail} place_calls={b.place_calls} "
          f"positions={b.positions()}")

    # D2 — lost reply, the close rests LIVE
    b = _broker(); b.script_place("lost")
    rec = _row(); e = _engine()
    max_working = 0
    with bind(b, EE):
        e._confirm_and_book_live_exit(rec, WHY, 1.20)
        max_working = max(max_working, len(b.working()))
        r2 = e._confirm_and_book_live_exit(rec, WHY, 1.20)    # adopts O1: polled, cancelled at the 0 s deadline
        calls_after_adopt = b.place_calls
        max_working = max(max_working, len(b.working()))
        b.fill_on_accept = 1.15
        r3 = e._confirm_and_book_live_exit(rec, WHY, 1.15)    # O1 dead with nothing filled -> the next rung posts
        max_working = max(max_working, len(b.working()))
    check("D2 lost reply + LIVE close: adopted and tracked (cancelled, then ONE new rung); never two working, not short",
          calls_after_adopt == 1 and "O1" in b.deleted and b.place_calls == 2 and r3.confirmed
          and max_working <= 1 and b.position(SYM) == 0,
          f"calls_after_adopt={calls_after_adopt} deleted={b.deleted} place_calls={b.place_calls} "
          f"r2={r2.detail} r3={r3.confirmed}/{r3.detail} max_working={max_working} positions={b.positions()}")

    # D3 — still in flight: not in the book for one read
    b = _broker(); b.script_place("lost", hidden_reads=1)
    rec = _row(); e = _engine()
    with bind(b, EE):
        e._confirm_and_book_live_exit(rec, WHY, 1.20)
        r2 = e._confirm_and_book_live_exit(rec, WHY, 1.20)    # read 1: not visible, inside the grace
        calls_in_grace = b.place_calls
        b.fill("O1", 1.20)
        r3 = e._confirm_and_book_live_exit(rec, WHY, 1.20)    # read 2: visible (FILLED) -> adopted, booked
    check("D3 in-flight lost close: nothing posts inside the grace; once visible it is adopted, one order",
          calls_in_grace == 1 and not r2.confirmed and r3.confirmed and b.place_calls == 1 and b.position(SYM) == 0,
          f"in_grace={calls_in_grace} r2={r2.detail} r3={r3.confirmed}/{r3.detail} place_calls={b.place_calls} "
          f"positions={b.positions()}")

    # D4 — raised, nothing accepted: grace, then ONE fresh close
    b = _broker(); b.fill_on_accept = 1.20; b.script_place("raise")
    rec = _row(); e = _engine()
    with bind(b, EE):
        e._confirm_and_book_live_exit(rec, WHY, 1.20)
        r2 = e._confirm_and_book_live_exit(rec, WHY, 1.20)
        calls_in_grace = b.place_calls
        _age_lost(rec)
        r3 = e._confirm_and_book_live_exit(rec, WHY, 1.20)
    check("D4 nothing accepted: blocked inside the grace, then (book empty, position held) ONE close posts and fills",
          calls_in_grace == 1 and not r2.confirmed and r3.confirmed and b.place_calls == 2
          and len(b.accepted) == 1 and b.position(SYM) == 0,
          f"in_grace={calls_in_grace} r2={r2.detail} r3={r3.confirmed}/{r3.detail} place_calls={b.place_calls} "
          f"positions={b.positions()}")

    # D5 — the book is unreadable
    b = _broker(); b.script_place("lost")
    rec = _row(); e = _engine()
    with bind(b, EE):
        e._confirm_and_book_live_exit(rec, WHY, 1.20)
        b.live_orders_raise = True
        _age_lost(rec)
        r2 = e._confirm_and_book_live_exit(rec, WHY, 1.20)
        r3 = e._confirm_and_book_live_exit(rec, WHY, 1.20)
    check("D5 lost reply + unreadable book: nothing posts (fail closed)",
          b.place_calls == 1 and not r2.confirmed and not r3.confirmed and len(b.working()) == 1,
          f"place_calls={b.place_calls} r2={r2.detail} working={b.working()}")

    # D6 — nothing in the book, and the broker no longer holds the position
    b = _broker(hold=False); b.script_place("raise")
    rec = _row(); e = _engine()
    with bind(b, EE):
        e._confirm_and_book_live_exit(rec, WHY, 1.20)
        _age_lost(rec)
        r2 = e._confirm_and_book_live_exit(rec, WHY, 1.20)
        r3 = e._confirm_and_book_live_exit(rec, WHY, 1.20)
    check("D6 book empty and the position NOT held: nothing posts, no short",
          b.place_calls == 1 and not r2.confirmed and not r3.confirmed and b.position(SYM) == 0,
          f"place_calls={b.place_calls} r2={r2.detail} positions={b.positions()}")

    # D7 — a restart after the lost reply
    b = _broker(); b.script_place("lost")
    rec = _row(); e = _engine()
    with bind(b, EE):
        e._confirm_and_book_live_exit(rec, WHY, 1.20)
        b.fill("O1", 1.20)
        rec2 = _reread(rec["trade_id"])                       # RESTART: nothing carried in memory
        r2 = _engine()._confirm_and_book_live_exit(rec2, WHY, 1.20)
    check("D7 restart after a lost reply: the new engine adopts the filled close, posts nothing new",
          r2.confirmed and b.place_calls == 1 and b.position(SYM) == 0,
          f"r2={r2.confirmed}/{r2.detail} place_calls={b.place_calls} positions={b.positions()} "
          f"state={rec2.get('live_exit_state')!r}")

    # D8 — the 15:55 cross: a lost MARKET close
    b = _broker(); b.script_place("lost")
    rec = _row(); e = _engine()
    _hm = EE.hard_close_order_mode
    EE.hard_close_order_mode = lambda t: "market"
    try:
        with bind(b, EE):
            e._confirm_and_book_live_exit(rec, "hard_close 15:55", 1.20)
            b.fill("O1", 1.18)
            r2 = e._confirm_and_book_live_exit(rec, "hard_close 15:55", 1.20)
            r3 = e._confirm_and_book_live_exit(rec, "hard_close 15:55", 1.20) if not r2.confirmed else r2
    finally:
        EE.hard_close_order_mode = _hm
    check("D8 15:55 cross, a lost MARKET close: no second MARKET order; flat, not short",
          b.place_calls == 1 and b.position(SYM) == 0 and r2.confirmed,
          f"place_calls={b.place_calls} positions={b.positions()} r2={r2.detail} r3={r3.detail}")

    # D9 — a credit vertical's lost close
    b = _broker(vertical=True); b.script_place("lost")
    rec = _row(vertical=True); e = _engine()
    with bind(b, EE):
        e._confirm_and_book_live_exit(rec, WHY, 0.10)
        b.fill_leg("O1", SHORT, 0.12); b.fill_leg("O1", LONG, 0.02)
        r2 = e._confirm_and_book_live_exit(rec, WHY, 0.10)
    check("D9 credit vertical, lost close: adopted and booked at its net, one order, both legs flat",
          r2.confirmed and abs((r2.fill_price or 0) - 0.10) < 1e-9 and b.place_calls == 1
          and b.position(SHORT) == 0 and b.position(LONG) == 0,
          f"r2={r2.confirmed}/{r2.fill_price}/{r2.detail} place_calls={b.place_calls} positions={b.positions()}")


def prior_rung_case():
    # D10 — an earlier rung of the same close died PART-filled (its fill already harvested); then a post raised with
    # nothing accepted. The earlier rung must not be adopted as the lost close (its fill would count twice and the row
    # would book while a contract is still held).
    WHY = "target_hit pnl=+20%"
    b = MisbehavingBroker(); b.hold(SYM, +2, 1.00)
    _del = b.delete_order

    async def _part_then_cancel(session, oid):
        if oid == "O1" and b.order("O1").status.value == "Live":
            b.fill("O1", 1.20, qty=1)
        return await _del(session, oid)
    b.delete_order = _part_then_cancel
    rec = _row()
    rec["contracts"] = 2
    e = _engine()
    with bind(b, EE):
        r1 = e._confirm_and_book_live_exit(rec, WHY, 1.20)      # O1: 1 of 2 fills, then cancelled -> partial
        b.script_place("raise")
        e._confirm_and_book_live_exit(rec, WHY, 1.10)           # the post raises, nothing accepted
        _age_lost(rec)
        b.fill_on_accept = 1.10
        r3 = e._confirm_and_book_live_exit(rec, WHY, 1.10)      # book: only O1 (dead, part-filled) -> post the 1 left
    check("D10 an earlier part-filled rung is never adopted as the lost close: the remaining 1 posts, books 2 @ 1.15",
          r1.partial and r3.confirmed and abs((r3.fill_price or 0) - 1.15) < 1e-9 and b.place_calls == 3
          and b.position(SYM) == 0,
          f"r1={r1.detail} r3={r3.confirmed}/{r3.fill_price}/{r3.detail} place_calls={b.place_calls} "
          f"positions={b.positions()}")


class _FlakyLogger:
    """The real TradeLogger, with log_exit raising for the first `fails` calls (a sqlite I/O error)."""
    def __init__(self, real, fails):
        self._real, self.fails, self.calls = real, fails, 0

    def log_exit(self, *a, **k):
        self.calls += 1
        if self.calls <= self.fails:
            import sqlite3
            raise sqlite3.OperationalError("disk I/O error")
        return self._real.log_exit(*a, **k)

    def __getattr__(self, name):
        return getattr(self._real, name)


def _pm(paper, fails):
    pm = PM.PositionManager(paper_trading=paper)
    pm._trade_logger = _FlakyLogger(TLOG, fails)
    return pm


def _pending_reset():
    if hasattr(PM, "_BOOK_PENDING"):
        PM._BOOK_PENDING.clear()


def _try(fn):
    try:
        return fn()
    except Exception as exc:                                          # noqa: BLE001
        return exc


def booking_cases():
    DEC = EE.ExitDecision(should_exit=True, exit_reason="stop_hit")
    _gee = PM.get_exit_engine
    _ram, _rrm = PM.get_alert_manager, PM.get_risk_manager

    class _Quiet:
        def __getattr__(self, name):
            return lambda *a, **k: True
    PM.get_alert_manager = lambda: _Quiet()
    PM.get_risk_manager = lambda: _Quiet()
    try:
        # B1 — live: the close FILLED, log_exit raised once
        _pending_reset()
        b = _broker(); b.fill_on_accept = 0.80
        live = _engine()
        PM.get_exit_engine = lambda paper=False: live
        rec = _row(); pm = _pm(False, fails=1); pm._open_records = [rec]
        with bind(b, EE):
            c1 = _try(lambda: pm._execute_exit(rec, DEC, 0.80))
            c2 = _try(lambda: pm._execute_exit(rec, DEC, 0.75))
        st = _status(rec["trade_id"])
        check("B1 close FILLED, log_exit raised once: no new order; the next pass writes the row at the broker's fill",
              c1 is False and c2 is True and b.place_calls == 1 and b.position(SYM) == 0
              and st[0] == "closed" and abs(float(st[1] or 0) - 0.80) < 1e-9,
              f"c1={c1!r} c2={c2!r} place_calls={b.place_calls} positions={b.positions()} row={st}")

        # B2 — log_exit keeps raising; the manager re-reads its records from the DB between passes
        _pending_reset()
        b = _broker(); b.fill_on_accept = 0.80
        live = _engine()
        PM.get_exit_engine = lambda paper=False: live
        rec = _row(); pm = _pm(False, fails=3)
        with bind(b, EE):
            for _ in range(3):
                fresh = _reread(rec["trade_id"])                 # still 'open' in the DB, nothing in memory
                _try(lambda: pm._execute_exit(fresh, DEC, 0.80))
            last = _try(lambda: pm._execute_exit(_reread(rec["trade_id"]), DEC, 0.80))
        st = _status(rec["trade_id"])
        check("B2 log_exit raises for 3 passes over re-read records: still ONE order, flat, not short; then booked",
              b.place_calls == 1 and b.position(SYM) == 0 and last is True and st[0] == "closed",
              f"place_calls={b.place_calls} positions={b.positions()} last={last!r} row={st}")

        # B3 — paper: log_exit raised once; the next pass re-writes the SAME fill
        _pending_reset()
        paper = EE.ExitEngine(paper_trading=True)
        calls = []
        _real_peo = paper.place_exit_order

        def _peo(record, reason, mark_price=None):
            calls.append(mark_price)
            return _real_peo(record, reason, mark_price=mark_price)
        paper.place_exit_order = _peo
        PM.get_exit_engine = lambda paper_=True: paper
        rec = _row(); pm = _pm(True, fails=1)
        c1 = _try(lambda: pm._execute_exit(rec, DEC, 0.70))
        c2 = _try(lambda: pm._execute_exit(rec, DEC, 0.55))
        st = _status(rec["trade_id"])
        check("B3 paper, log_exit raised once: the next pass writes the SAME fill (0.70), no second simulated close",
              c1 is False and c2 is True and calls == [0.70] and st[0] == "closed"
              and abs(float(st[1] or 0) - 0.70) < 1e-9,
              f"c1={c1!r} c2={c2!r} place_exit_order calls={calls} row={st}")

        # B4 — a step after the booking raises: the close stands
        _pending_reset()
        b = _broker(); b.fill_on_accept = 0.80
        live = _engine()
        PM.get_exit_engine = lambda paper=False: live

        class _Boom:
            def send_exit_alert(self, **k):
                raise RuntimeError("notifier down")

            def __getattr__(self, name):
                return lambda *a, **k: True
        PM.get_alert_manager = lambda: _Boom()
        rec = _row(); pm = _pm(False, fails=0); pm._open_records = [rec]
        with bind(b, EE):
            c1 = _try(lambda: pm._execute_exit(rec, DEC, 0.80))
            # what the next tick would do with whatever is still managed
            for r in list(pm._open_records):
                if c1 is not True:
                    _try(lambda: pm._execute_exit(r, DEC, 0.80))
        PM.get_alert_manager = lambda: _Quiet()
        check("B4 the exit alert raises after the booking: the close stands (True), no second order, flat",
              c1 is True and b.place_calls == 1 and b.position(SYM) == 0 and _status(rec["trade_id"])[0] == "closed",
              f"c1={c1!r} place_calls={b.place_calls} positions={b.positions()}")

        # B6 — the manage pass retries the pending write first (no mark needed, no plan, no order)
        _pending_reset()
        b = _broker(); b.fill_on_accept = 0.80
        live = _engine()
        PM.get_exit_engine = lambda paper=False: live
        rec = _row(); pm = _pm(False, fails=1)
        pm._fetch_current_premium = lambda record, chain=None: None     # no mark this tick
        with bind(b, EE):
            c1 = _try(lambda: pm._execute_exit(rec, DEC, 0.80))
            keep = _try(lambda: pm._manage_one(_reread(rec["trade_id"]), None, None))
        check("B6 the next manage pass writes the pending row first (even with no mark) and drops the record",
              c1 is False and keep is False and b.place_calls == 1 and _status(rec["trade_id"])[0] == "closed",
              f"c1={c1!r} keep={keep!r} place_calls={b.place_calls} row={_status(rec['trade_id'])}")

        # B5 — paper normal path, unchanged
        _pending_reset()
        paper = EE.ExitEngine(paper_trading=True)
        PM.get_exit_engine = lambda paper_=True: paper
        rec = _row(); pm = _pm(True, fails=0)
        c1 = _try(lambda: pm._execute_exit(rec, DEC, 0.65))
        st = _status(rec["trade_id"])
        check("B5 paper normal exit: books once at the mark",
              c1 is True and st[0] == "closed" and abs(float(st[1] or 0) - 0.65) < 1e-9
              and not getattr(PM, "_BOOK_PENDING", {}),
              f"c1={c1!r} row={st}")
    finally:
        PM.get_exit_engine = _gee
        PM.get_alert_manager, PM.get_risk_manager = _ram, _rrm
        _pending_reset()


def main():
    print("check_double_close")
    close_cases()
    prior_rung_case()
    booking_cases()
    print(f"\n{'ALL PASS' if not PROBLEMS else 'FAILED: ' + ', '.join(PROBLEMS)}")
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
