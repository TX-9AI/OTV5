#!/usr/bin/env python3
"""
tests/check_exit_correctness.py  v5.0
v5.0  2026-11-21  OTV5 r139 (EXIT.15 + EXIT.16 + EXIT.17 + EXIT.18; the live exit polling audit 2026-11-21 S1-S4) — NEW.
      THE LIVE CLOSE DOES WHAT THE OPERATOR'S SPEC SAYS: the stop counts its own attempts (mark, mark, the bid, then
      MARKET), it prices off a quote that is really fresh, a broker refusal is a refusal, and a cancel refused because
      the order just filled books at once. The operator, 2026-11-21: "Yes, in that order" (the second build).

  🔴 THE DEFECTS (OTV5 r138 f53c2e0; the audit's fake-broker scenarios S5-S8, reviews/audit/POLLING_20261121/scenarios.py,
     rebuilt here on the shared tests/broker_harness.py):
  S2  exit_engine._stop_unfilled counted the wrong attempts: refused / rejected stop attempts never escalated (4 rejected
      stayed limit-at-mark), unfilled NON-stop attempts (a lock exit's walk) counted, so the first hard-stop attempt
      could go straight to MARKET, and a restart reset the count.
  S3  the 10 s quote-freshness rule timed the copy onto the record: the k-th close of a tick (or of the 15:50 loop)
      priced off copies (k-1) x 10-14 s old. The fix re-reads the store before each post; a quiet quote is still the
      current quote (dxFeed sends one only on a change), and only a quote past the feed's 120 s rule is missing.
  S1  a broker REFUSAL (the SDK raises on every non-2xx) was handled as a lost reply: LOST tag, a 10 s wait, a book read.
  S4  a cancel refused because the order had just filled paged "UNFILLED ... cancel failed" and booked a tick late.

  OFFLINE: the real ExitEngine (live) on a temp trades.db and a temp feed store, against tests/broker_harness. 3 lots.
  S2  C1  three unfilled lock-exit (walk) attempts, then a hard stop -> the stop's FIRST attempt posts at the mark
      C2  four stop attempts the broker REFUSES (a parsed 4xx) -> mark, mark, the bid, MARKET
      C3  four stop attempts the broker REJECTS -> mark, mark, the bid, MARKET
      C4  two unfilled stop attempts, then a DIFFERENT reason (a structure stop) -> its first attempt posts at the mark
      C4b the same stop whose P&L text changes every tick is the same reason -> it escalates on its third attempt
      C5  two unfilled stop attempts, a restart (new engine, the record re-read from the row) -> the bid, then MARKET
      C6  four unfilled stop attempts -> exactly mark, mark, the bid, MARKET (the constants 2 and 3 unchanged)
  S3  C7  a QUIET quote 45 s old (dxFeed sends a quote only when it changes) still posts at its mark, its age logged
      C7b a quote older than the feed's own staleness rule (OT_CHAIN_STALE_S, 120 s) -> nothing posts (the no-mark
          close), one page
      C8  the re-read re-stashes the quiet quote for the walk / the touch step: an unfilled stop's third attempt posts
          AT THE BID off a 45 s old quote, not MARKET
      C9  the store's mark moves after the tick priced it -> the close posts at the store's mark as it stands NOW
      C10 the k-th close of a loop re-reads the store before it posts (its own fresh mark, not the tick's); a loop
          whose quotes are past 120 s posts nothing
      C11 no broker call added: a fresh stamped close makes exactly the calls an unstamped one makes
      C11b the real chain read (OptionsChainFetcher._read_marks + _apply_market_data) puts chain_marks.updated_epoch
          on the contract, so the quote's own age reaches the record
  S1  C12 a parsed refusal -> "refused", no LOST tag, nothing waits, the broker's reason pages once per distinct reason
      C13 the real SDK raise path: a 422 with an error body -> refused; a 500 with an error body -> the lost path
      C14 a timeout, a connection error and an unparseable reply (nginx's 429 page) -> the lost path, as at r128
      C15 an ENTRY whose place_order raised (even a parsed refusal) still becomes a suspect (r135 GUARD.1 intact)
  S4  C16 the deadline cancel raises because the order just FILLED -> booked in the same pass, no UNFILLED page
      C17 the deadline cancel raises and the order is still working -> as before: kept, "deadline" page, nothing booked
  BORN RED on r138 f53c2e0 at C1-C5, C7, C7b, C9, C10, C11b, C12, C13, C16 (13 of 20); C4b, C6, C8, C11, C14, C15, C17 hold there
  too (they pin what must not change). 17 mutants red (one per rule). The clock is pinned through the seams every
  exit checker uses (XE.is_hard_close_time, XE.now_et).

Run:  python3 tests/check_exit_correctness.py   (exit 0 green, 1 red; needs the venv's tastytrade)
"""
import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
_TMP = tempfile.mkdtemp(prefix="check_exit_correctness_")
FEED = os.path.join(_TMP, "feed_store.db")
os.environ["OT_FEED_DB"] = FEED
import config                                                         # noqa: E402
config.LOG_FILE = os.path.join(_TMP, "bot.log")
config.LIVE_FILL_POLL_SECONDS = 0.0
config.LIVE_FILL_DEADLINE_SECONDS = 0.0
from broker_harness import MisbehavingBroker, bind                    # noqa: E402

PROBLEMS = []
SYM = "QQQ   261123C00500000"
STREAMER = ".QQQ261123C500"


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


try:
    from tastytrade.utils import TastytradeError, validate_response   # noqa: E402
except ImportError as _exc:                                           # pragma: no cover
    print(f"NOT RUN — this interpreter cannot import tastytrade ({_exc}); run under the venv")
    sys.exit(2)
import database.trade_logger as TL                                    # noqa: E402
import execution.exit_engine as EE                                    # noqa: E402
import execution.position_manager as PM                               # noqa: E402
from execution import ladder_registry as LR                           # noqa: E402
import datetime as _D                                                 # noqa: E402
from zoneinfo import ZoneInfo                                         # noqa: E402

_ETZ = ZoneInfo("America/New_York")
EE.is_hard_close_time = lambda *a, **k: False
EE.now_et = lambda: _D.datetime(2026, 11, 23, 11, 0, tzinfo=_ETZ)
import utils.time_utils as TU                                         # noqa: E402
TU.now_et = EE.now_et

TLOG = TL.TradeLogger(os.path.join(_TMP, "t.db"), paper_trading=False)
TL._trade_logger = TLOG
_N = [0]
STOP = "hard_stop_20% pnl=-21.0%"


def _row():
    _N[0] += 1
    tid = f"EC-{_N[0]:03d}-0000"
    TLOG.log_entry(TL.make_record(
        trade_id=tid, symbol="QQQ", strategy="PARK", setup_type="PARK", option_side="call", contracts=3,
        entry_premium=1.40, total_cost=420.0, max_loss=420.0, stop_premium=0.0, option_symbol=SYM, strike=500.0,
        expiry="2099-01-01"))
    return _reread(tid)


def _reread(tid):
    with TLOG._db() as conn:
        row = conn.execute("SELECT * FROM trades WHERE trade_id=?", (tid,)).fetchone()
    return TL.make_record(**dict(row))


class _Broker(MisbehavingBroker):
    """The shared broker, plus: reject the next N accepted orders, fill an order the instant its cancel arrives (the
    cancel then refused, as the real broker refuses a Filled order), and count every Account call."""
    def __init__(self):
        super().__init__()
        self.reject_next = 0
        self.fill_on_cancel = None
        self.calls = []
        self.hold(SYM, +3, 1.40)

    async def place_order(self, session, order, dry_run=False):
        self.calls.append("place")
        r = await super().place_order(session, order, dry_run)
        if self.reject_next and r.order is not None:
            self.reject_next -= 1
            self.set_status(r.order.id, "Rejected")
            r.order.reject_reason = "test reject"
        return r

    async def get_order(self, session, oid):
        self.calls.append("get")
        return await super().get_order(session, oid)

    async def get_live_orders(self, session):
        self.calls.append("live_orders")
        return await super().get_live_orders(session)

    async def get_positions(self, session, **kw):
        self.calls.append("positions")
        return await super().get_positions(session, **kw)

    async def delete_order(self, session, oid):
        self.calls.append("delete")
        if self.fill_on_cancel is not None:
            self.fill(oid, self.fill_on_cancel)
        return await super().delete_order(session, oid)


def _engine():
    e = EE.ExitEngine(paper_trading=False)
    e.pages = []
    e.msgs = []

    def _alert(tid, kind, msg):
        if (tid, kind) in e._live_exit_alerted:
            return
        e._live_exit_alerted.add((tid, kind))
        e.pages.append(kind)
        e.msgs.append(msg)
    e._alert_live_exit_once = _alert
    return e


def _desc(b, i):
    p = b.placed_prices[i]
    return ("Market", None) if p is None else ("Limit", round(abs(p), 2))


def _orders(b):
    return [_desc(b, i) for i in range(len(b.placed_prices))]


def _quote(rec, bid=1.00, ask=1.20):
    rec["_exit_bid"], rec["_exit_ask"] = bid, ask          # unstamped: read as before (r48)


def _run(e, rec, reason, mark=1.10):
    _quote(rec)
    try:
        return e._confirm_and_book_live_exit(rec, reason, mark)
    except Exception as exc:                                          # noqa: BLE001
        return exc


MARK, MARK2, BID, MKT = ("Limit", 1.10), ("Limit", 1.10), ("Limit", 1.00), ("Market", None)
SPEC = [MARK, MARK2, BID, MKT]


def s2_cases():
    LR.reset_all()
    # C1 — lock walks never count toward a stop
    b, e, rec = _Broker(), _engine(), _row()
    with bind(b, EE):
        for _ in range(3):
            _run(e, rec, "park_lock_exit")
        n_after_walks = int(rec.get("_stop_unfilled") or 0)
        _run(e, rec, STOP)
    got = _orders(b)
    check("C1 three unfilled lock-exit walks, then a hard stop -> the stop's first attempt posts at the mark",
          len(got) == 4 and got[3] == MARK and n_after_walks == 0,
          f"orders={got} count after the walks={n_after_walks}")

    # C2 — refused stop attempts count
    LR.reset_all()
    b, e, rec = _Broker(), _engine(), _row()
    with bind(b, EE):
        for _ in range(4):
            b.script_place("raise", exc=TastytradeError("invalid_price_increment: Price must be in increments of "
                                                        "0.01\n"))
            _run(e, rec, STOP)
    got = _orders(b)
    check("C2 four stop attempts the broker REFUSES -> mark, mark, the bid, MARKET",
          got == SPEC and not b.accepted, f"orders={got} accepted={b.accepted} count={rec.get('_stop_unfilled')}")

    # C3 — rejected stop attempts count
    LR.reset_all()
    b, e, rec = _Broker(), _engine(), _row()
    b.reject_next = 4
    with bind(b, EE):
        for _ in range(4):
            _run(e, rec, STOP)
    got = _orders(b)
    check("C3 four stop attempts the broker REJECTS -> mark, mark, the bid, MARKET", got == SPEC,
          f"orders={got} count={rec.get('_stop_unfilled')}")

    # C4 — a different reason starts again
    LR.reset_all()
    b, e, rec = _Broker(), _engine(), _row()
    with bind(b, EE):
        _run(e, rec, STOP)
        _run(e, rec, STOP)
        _run(e, rec, "structure_stop: 5m close 512.30 below the swing 512.50")
        _run(e, rec, "structure_stop: 5m close 512.10 below the swing 512.50")
    got = _orders(b)
    check("C4 two unfilled hard-stop attempts, then a structure stop -> its attempts start at the mark again",
          got == [MARK, MARK, MARK, MARK], f"orders={got}")

    # C4b — the same stop with a changing P&L text continues its count
    LR.reset_all()
    b, e, rec = _Broker(), _engine(), _row()
    with bind(b, EE):
        for pnl in ("-21.0", "-22.4", "-23.9", "-25.1"):
            _run(e, rec, f"hard_stop_20% pnl={pnl}%")
    got = _orders(b)
    check("C4b the same hard stop whose P&L text changes each tick is one reason -> mark, mark, the bid, MARKET",
          got == SPEC, f"orders={got}")

    # C5 — a restart continues the count
    LR.reset_all()
    b, e, rec = _Broker(), _engine(), _row()
    with bind(b, EE):
        _run(e, rec, STOP)
        _run(e, rec, STOP)
        st = _reread(rec["trade_id"]).get("live_exit_state")
        e2 = _engine()
        rec2 = _reread(rec["trade_id"])
        _run(e2, rec2, STOP)
        _run(e2, rec2, STOP)
    got = _orders(b)
    check("C5 two unfilled stop attempts, a restart -> the third posts at the bid, the fourth MARKET",
          got == SPEC and '"stop_unfilled": 2' in str(st), f"orders={got} row state={st!r}")

    # C6 — the exact sequence on plain unfilled attempts, and the constants
    LR.reset_all()
    b, e, rec = _Broker(), _engine(), _row()
    with bind(b, EE):
        for _ in range(4):
            _run(e, rec, STOP)
    got = _orders(b)
    check("C6 four unfilled stop attempts -> exactly mark, mark, the bid, MARKET (constants 2 and 3)",
          got == SPEC and config.LIVE_STOP_AT_BID_AFTER == 2 and config.LIVE_STOP_MARKET_AFTER == 3,
          f"orders={got} constants={config.LIVE_STOP_AT_BID_AFTER},{config.LIVE_STOP_MARKET_AFTER}")


# ── S3 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _store(bid, ask, age_s, sym=STREAMER):
    c = sqlite3.connect(FEED)
    c.execute("CREATE TABLE IF NOT EXISTS chain_marks (streamer_symbol TEXT PRIMARY KEY, bid REAL, ask REAL, "
              "delta REAL, gamma REAL, theta REAL, vega REAL, iv REAL, updated_epoch REAL NOT NULL)")
    c.execute("INSERT INTO chain_marks (streamer_symbol, bid, ask, updated_epoch) VALUES (?,?,?,?) "
              "ON CONFLICT(streamer_symbol) DO UPDATE SET bid=excluded.bid, ask=excluded.ask, "
              "updated_epoch=excluded.updated_epoch", (sym, bid, ask, time.time() - age_s))
    c.commit()
    c.close()


def _chain(bid, ask, age_s, sym=STREAMER):
    from data.options_chain import OptionContract, OptionsChain
    oc = OptionContract(symbol=SYM, underlying="QQQ", expiry="2026-11-23", option_type="C", strike=500.0,
                        bid=bid, ask=ask, mark=(bid + ask) / 2, delta=0.5, streamer_symbol=sym)
    oc.quote_epoch = time.time() - age_s                              # the store's own time for this quote
    return OptionsChain(underlying="QQQ", expiry="2026-11-23", spot_price=500.0, calls=[oc], puts=[])


def _priced(pm, rec, chain):
    """The real position_manager pricing pass: the mark, the stash and the stamps."""
    return pm._fetch_current_premium(rec, chain=chain)


def s3_cases():
    LR.reset_all()
    pm = PM.PositionManager(paper_trading=False)
    # C7 — a quiet stored quote 45 s old: still the current quote; posts at its mark, its age logged
    import logging as _lg
    seen = []

    class _H(_lg.Handler):
        def emit(self, rec_):
            seen.append(rec_.getMessage())
    _h = _H()
    _lvl = EE.logger.level
    EE.logger.setLevel(_lg.INFO)
    EE.logger.addHandler(_h)
    LR.reset_all()
    _store(1.00, 1.20, 45)
    b, e, rec = _Broker(), _engine(), _row()
    b.fill_on_accept = 1.10
    mark = _priced(pm, rec, _chain(1.00, 1.20, 45))
    with bind(b, EE):
        r = e._confirm_and_book_live_exit(rec, STOP, mark)
    EE.logger.removeHandler(_h)
    EE.logger.setLevel(_lvl)
    aged = [m for m in seen if "single CLOSE" in m and "quote age 45" in m]
    check("C7 a quiet quote 45 s old still posts at its mark (1.10), the post line logs its age",
          _orders(b) == [("Limit", 1.10)] and getattr(r, "confirmed", False) is True and len(aged) == 1,
          f"orders={_orders(b)} r={getattr(r, 'detail', r)!r} age lines={aged}")

    # C7b — past the feed's staleness rule (120 s): the no-mark close
    _store(1.00, 1.20, 125)                                           # the store's newest row, still past 120 s
    b, e, rec = _Broker(), _engine(), _row()
    mark = _priced(pm, rec, _chain(1.00, 1.20, 130))
    with bind(b, EE):
        r = e._confirm_and_book_live_exit(rec, STOP, mark)
    check("C7b a quote 125 s old (over OT_CHAIN_STALE_S 120) -> nothing posts (the no-mark close), one page",
          b.place_calls == 0 and getattr(r, "confirmed", True) is False and "no mark" in str(getattr(r, "detail", ""))
          and e.pages.count("nomark") == 1,
          f"mark={mark} r={getattr(r, 'detail', r)!r} place_calls={b.place_calls} pages={e.pages}")

    # C8 — the re-read re-stashes the quiet quote: the stop's touch step posts at the bid, not MARKET
    LR.reset_all()
    _store(1.00, 1.20, 45)
    b, e, rec = _Broker(), _engine(), _row()
    with bind(b, EE):
        for _ in range(3):
            m = _priced(pm, rec, _chain(1.00, 1.20, 45))
            e._confirm_and_book_live_exit(rec, STOP, m)
    check("C8 three unfilled stop attempts off a quiet 45 s quote -> mark, mark, then AT THE BID (not MARKET)",
          _orders(b) == [MARK, MARK, BID], f"orders={_orders(b)}")

    # C9 — the store's mark moves after the tick priced it: the close posts at the store's mark now
    LR.reset_all()
    _store(1.00, 1.20, 1)
    b, e, rec = _Broker(), _engine(), _row()
    b.fill_on_accept = 0.95
    mark = _priced(pm, rec, _chain(1.00, 1.20, 1))
    _store(0.90, 1.00, 0.5)                                          # the market moved; the feed wrote it
    with bind(b, EE):
        r = e._confirm_and_book_live_exit(rec, STOP, mark)
    got = _orders(b)
    check("C9 the stored mark moved from 1.10 to 0.95 after the tick -> the close posts at 0.95",
          mark == 1.10 and got == [("Limit", 0.95)] and getattr(r, "confirmed", False) is True,
          f"tick mark={mark} orders={got} r={getattr(r, 'detail', r)!r}")

    # C10 — two closes in one loop, priced at the loop's start; the second re-reads before it posts
    LR.reset_all()
    s2 = ".QQQ261123C501"
    _store(1.00, 1.20, 1)
    _store(2.00, 2.20, 1, sym=s2)
    b, e = _Broker(), _engine()
    ra, rb = _row(), _row()
    ma = _priced(pm, ra, _chain(1.00, 1.20, 1))
    mb = _priced(pm, rb, _chain(2.00, 2.20, 1, sym=s2))
    with bind(b, EE):
        b.fill_on_accept = 1.10
        e._confirm_and_book_live_exit(ra, STOP, ma)
        _store(1.80, 2.00, 0.2, sym=s2)                               # moved while the first close ran
        b.fill_on_accept = 1.90
        e._confirm_and_book_live_exit(rb, STOP, mb)
    got = _orders(b)
    _store(2.00, 2.20, 130, sym=s2)                                   # and a loop whose feed went dead
    b2, e2, rc = _Broker(), _engine(), _row()
    mc = _priced(pm, rc, _chain(2.00, 2.20, 1, sym=s2))
    rc["_mark_epoch"] = time.time() - 130                             # the tick's own quote is that old too
    with bind(b2, EE):
        e2._confirm_and_book_live_exit(rc, STOP, mc)
    check("C10 the second close of a loop posts at its store mark as it stands when it posts (1.90, not 2.10); a "
          "loop whose quotes are 130 s old (past the feed's 120 s rule) posts nothing",
          got == [("Limit", 1.10), ("Limit", 1.90)] and b2.place_calls == 0,
          f"orders={got} quiet loop place_calls={b2.place_calls}")

    # C11 — no broker call added
    LR.reset_all()
    _store(1.00, 1.20, 1)
    b, e, rec = _Broker(), _engine(), _row()
    b.fill_on_accept = 1.10
    mark = _priced(pm, rec, _chain(1.00, 1.20, 1))
    with bind(b, EE):
        e._confirm_and_book_live_exit(rec, STOP, mark)
    stamped = list(b.calls)
    b, e, rec = _Broker(), _engine(), _row()
    b.fill_on_accept = 1.10
    with bind(b, EE):
        _run(e, rec, STOP)
    check("C11 a fresh stamped close makes exactly the broker calls an unstamped one makes (place, get)",
          stamped == b.calls == ["place", "get"], f"stamped={stamped} unstamped={b.calls}")

    # C11b — the real chain read carries the store's quote time onto the contract
    from data.options_chain import OptionsChainFetcher, OptionContract
    _store(1.00, 1.20, 42)
    f = OptionsChainFetcher()
    gm, qm = f._read_marks([STREAMER])
    oc = OptionContract(symbol=SYM, strike=500.0, streamer_symbol=STREAMER)
    f._apply_market_data([oc], gm, qm)
    age = time.time() - float(getattr(oc, "quote_epoch", 0.0) or 0.0)
    check("C11b the chain read puts chain_marks.updated_epoch on the contract (a 42 s old quote reads 42 s old)",
          abs(age - 42) < 5 and abs(oc.mark - 1.10) < 1e-9, f"age={age:.1f} mark={oc.mark}")


# ── S1 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _sdk_raise(code, body):
    """Raise exactly as the SDK does: validate_response on an HTTP reply (so the frame's `response` is the real one)."""
    import httpx
    validate_response(httpx.Response(code, content=body.encode(), headers={"content-type": "application/json"}))


def s1_cases():
    LR.reset_all()
    b, e, rec = _Broker(), _engine(), _row()
    with bind(b, EE):
        b.script_place("raise", exc=TastytradeError("invalid_price_increment: Price must be in increments of 0.01\n"))
        r1 = _run(e, rec, "park_lock_exit")
        oid1 = rec.get("_live_exit_order_id")
        b.script_place("raise", exc=TastytradeError("invalid_price_increment: Price must be in increments of 0.01\n"))
        r2 = _run(e, rec, "park_lock_exit")
        b.script_place("raise", exc=TastytradeError("insufficient_quantity: Not enough position to close\n"))
        r3 = _run(e, rec, "park_lock_exit")
    refused = [k for k in e.pages if k.startswith("refused:")]
    check("C12 a parsed refusal -> refused, no LOST tag, the next pass posts at once, the broker's reason pages once "
          "per distinct reason",
          str(getattr(r1, "detail", "")).startswith("refused:") and not EE._is_lost_close_id(oid1)
          and b.place_calls == 3 and "lost-close" not in e.pages and len(refused) == 2
          and any("invalid_price_increment" in m for m in e.msgs) and "submit" not in e.pages
          and str(getattr(r3, "detail", "")).startswith("refused:"),
          f"r1={getattr(r1, 'detail', r1)!r} r2={getattr(r2, 'detail', r2)!r} id={oid1!r} "
          f"place_calls={b.place_calls} pages={e.pages}")

    def _real(code, body):
        bb, ee, rr = _Broker(), _engine(), _row()

        async def _place(session, order, dry_run=False):
            bb.place_calls += 1
            bb.placed_prices.append(None)
            _sdk_raise(code, body)
        bb.place_order = _place
        with bind(bb, EE):
            res = _run(ee, rr, STOP)
        return res, rr.get("_live_exit_order_id"), ee.pages
    r422, id422, p422 = _real(422, '{"error": {"code": "invalid_price", "message": "Price is invalid"}}')
    r500, id500, p500 = _real(500, '{"error": {"code": "internal_error", "message": "Something went wrong"}}')
    check("C13 the SDK's own raise: a 422 with an error body -> refused; a 500 with an error body -> the lost path",
          str(getattr(r422, "detail", "")).startswith("refused:") and not EE._is_lost_close_id(id422)
          and EE._is_lost_close_id(id500) and "lost-close" in p500,
          f"422 -> {getattr(r422, 'detail', r422)!r} id={id422!r}; 500 -> {getattr(r500, 'detail', r500)!r} "
          f"id={id500!r} pages={p500}")

    lost = []
    import concurrent.futures
    for exc in (concurrent.futures.TimeoutError("reply lost"), ConnectionResetError("reset"),
                TastytradeError("Couldn't parse response: <html><title>429 Too Many Requests</title>")):
        bb, ee, rr = _Broker(), _engine(), _row()
        with bind(bb, EE):
            bb.script_place("raise", exc=exc)
            res = _run(ee, rr, STOP)
        lost.append((type(exc).__name__, EE._is_lost_close_id(rr.get("_live_exit_order_id")),
                     "lost-close" in ee.pages, getattr(res, "detail", res)))
    check("C14 a timeout, a connection reset and nginx's 429 page -> the lost-reply path (LOST tag, one page)",
          all(t and p for _, t, p, _ in lost), f"{lost}")

    # C15 — entries: any raise at place_order is still an unknown outcome (r127 LOP.1 / r135 GUARD.1)
    from execution import order_guard as OG
    src = open(os.path.join(ROOT, "execution", "entry_engine.py")).read()
    bb = _Broker()
    OG._SUSPECT.clear()
    key = "EC15-entry"
    with bind(bb, EE, OG):
        OG.after_lost_post(key, [SYM], "S", bb, "single-leg entry",
                           TastytradeError("invalid_price: Price is invalid\n"))
        ok, why = OG.clear_to_post(key, "S", bb)
    check("C15 an entry whose place_order raised a parsed refusal is still a suspect: the intent is blocked",
          OG.has_suspects() and ok is False and "_guard.after_lost_post(_key" in src,
          f"suspects={list(OG._SUSPECT)} clear_to_post={ok} ({why})")
    OG._SUSPECT.clear()


# ── S4 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def s4_cases():
    LR.reset_all()
    b, e, rec = _Broker(), _engine(), _row()
    b.fill_on_cancel = 1.05
    with bind(b, EE):
        r = _run(e, rec, STOP)
    st = _reread(rec["trade_id"]).get("live_exit_state")
    check("C16 the deadline cancel raises because the order just FILLED -> booked in the same pass at its fill, no "
          "UNFILLED page, one extra read only",
          getattr(r, "confirmed", False) is True and abs(float(r.fill_price or 0) - 1.05) < 1e-9
          and "deadline" not in e.pages and b.place_calls == 1 and b.position(SYM) == 0
          and b.calls == ["place", "get", "delete", "get"] and not st,
          f"r={getattr(r, 'detail', r)!r} pages={e.pages} calls={b.calls} state={st!r}")

    LR.reset_all()
    b, e, rec = _Broker(), _engine(), _row()
    b.cancel_mode = "raise"
    with bind(b, EE):
        r = _run(e, rec, STOP)
    check("C17 the deadline cancel raises and the order is still working -> kept, 'deadline' page, nothing booked",
          getattr(r, "confirmed", True) is False and rec.get("_live_exit_order_id") == "O1"
          and "deadline" in e.pages and len(b.working()) == 1,
          f"r={getattr(r, 'detail', r)!r} id={rec.get('_live_exit_order_id')!r} pages={e.pages}")


def main():
    print("check_exit_correctness")
    for fn in (s2_cases, s3_cases, s1_cases, s4_cases):
        try:
            fn()
        except Exception as exc:                                      # noqa: BLE001
            import traceback
            traceback.print_exc()
            check(f"{fn.__name__} ran", False, f"{type(exc).__name__}: {exc}")
    if PROBLEMS:
        print(f"\nRED — {len(PROBLEMS)} failed: {', '.join(p.split()[0] for p in PROBLEMS)}")
        return 1
    print("\nGREEN — the stop counts its own attempts (mark, mark, the bid, MARKET), the close prices off a fresh "
          "quote, a refusal is a refusal, and a cancel that lost to a fill books at once")
    return 0


if __name__ == "__main__":
    sys.exit(main())
