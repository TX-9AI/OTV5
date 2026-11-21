#!/usr/bin/env python3
"""
tests/check_exit_resume_safety.py  v5.0
v5.0  2026-11-21  OTV5 r138 (EXIT.11 + EXIT.12 + EXIT.13 + EXIT.14; the live exit polling audit 2026-11-21 M1 M2 M3) — NEW. A LIVE CLOSE
      NEVER POSTS BESIDE ITSELF WHEN A READ FAILS, NEVER SELLS TWICE WHEN ITS FILLS ARE LATE, AND A CLOSE THAT HAS
      STARTED FINISHES. The operator, 2026-11-21: "Yes, in that order" (all three), and "I don't want partial opens or
      partial closes to be the norm".

  🔴 THE DEFECTS (OTV5 r137 c87d668; reproduced by the audit's fake-broker scenarios S2 and S3,
     reviews/audit/POLLING_20261121/scenarios.py, rebuilt here on the shared tests/broker_harness.py so the broker's
     TRUE book - what is working, what is held - is asserted, not what the bot was told):
  M1  exit_engine._confirm_and_book_live_exit_pass, resuming a kept close-order id: a failed read (429, timeout, 5xx,
      any exception) DROPPED the id and posted a fresh full close while the first was still live.
  M2  an order that read FILLED but whose fills could not be read DROPPED its id; the next pass posted a new
      sell-to-close on a position the broker had already closed.
  M3  position_manager._manage_one ran the exit only while the plan's trigger said exit, so after a partial (1 of 3)
      a trigger flipping back left the remainder open with no working order.

  OFFLINE: the real ExitEngine (live) and the real PositionManager._manage_one / _execute_exit on a temp trades.db,
  against tests/broker_harness.MisbehavingBroker (no network, no credentials). The broker holds 3 contracts.
  R1  M1: the kept order cannot be read on resume -> nothing posts, the id is kept (memory and row), one page
  R2  M1: the read keeps failing for two more passes -> still one order at the broker, never two working, one page
  R3  M1: the read recovers -> the same order resumes, fills, books once at its fill; one order, flat, not short
  R4  M2: the order FILLS at the broker but its fills do not read -> nothing booked, nothing posts, id kept, one page
  R5  M2: a restart while the fills are unreadable (new engine, record re-read) -> the id is in the row, nothing posts
  R6  M2: the fills read -> booked ONCE at the broker's fill; one order in all; one page in all; not short
  R7  M3: partial (1 of 3) on tick 1 under park_lock_exit; tick 2 the trigger says HOLD -> the remainder (2) posts on
      tick 2 under park_lock_exit, books at the weighted average, the row's exit_reason is park_lock_exit
  R8  M3: restart mid-close (new engine + manager, record re-read) with the trigger false -> the remainder posts
      under the LAST reason, and the declared pricing that reason had rides with it
  R9  M3: a kept close-order id (cancel failed on tick 1), trigger false on tick 2 -> the same order resumes, no new
      post, it books when it fills
  R10 M3: a fully-closed record is never re-posted: after the booking, ticks with the trigger false post nothing,
      and the row's live_exit_state is NULL
  R11 no started close and the trigger false -> no exit, ZERO broker calls (started_close reads no broker)
  R12 paper: a paper record (even one carrying a stray live_exit_state) with the trigger false is never closed
  R13 EXIT.14: the kept id stays unreadable all day; before the EOD close nothing posts; at the 15:50 ladder the
      give-up reads the broker's book, cancels the kept order, confirms it dead and closes the broker-held 3 -> flat,
      never two working closes, booked once
  R14 EXIT.14: the same at the 15:55 cross -> the give-up's close is a MARKET order (the cross still happens), flat
  R15 EXIT.14: the kept id is unreadable but FILLED at the broker -> at the give-up it books once from the book's
      fills, posts nothing
  R16 EXIT.14: the book is unreadable too at the give-up -> nothing posts, one page (today's behaviour)
  R17 EXIT.14: at the give-up the broker holds none (closed elsewhere) -> nothing posts on this or later passes,
      never a short, one page
  BORN RED on r137 c87d668 (R1-R10, R13-R17; R11 R12 hold there too), and on the r138 build before EXIT.14 (R13-R15,
  R17; R16 is that build's behaviour). The clock is pinned through the
  seams every exit checker uses (XE.is_hard_close_time, XE.now_et), so the gate reads the same at any hour.

Run:  python3 tests/check_exit_resume_safety.py   (exit 0 green, 1 red)
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
import config                                                         # noqa: E402
_TMP = tempfile.mkdtemp(prefix="check_exit_resume_safety_")
config.LOG_FILE = os.path.join(_TMP, "bot.log")
config.LIVE_FILL_POLL_SECONDS = 0.0
config.LIVE_FILL_DEADLINE_SECONDS = 0.0
from broker_harness import MisbehavingBroker, bind                    # noqa: E402

PROBLEMS = []
SYM = "QQQ   261123C00500000"


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


import database.trade_logger as TL                                    # noqa: E402
import execution.exit_engine as EE                                    # noqa: E402
import execution.position_manager as PM                               # noqa: E402
import strategy.management as MG                                      # noqa: E402
import datetime as _D                                                 # noqa: E402
from zoneinfo import ZoneInfo                                         # noqa: E402

_ETZ = ZoneInfo("America/New_York")
EE.is_hard_close_time = lambda *a, **k: False                         # the seam: no EOD by the wall clock
_AT = [_D.datetime(2026, 11, 23, 11, 0, tzinfo=_ETZ)]
EE.now_et = lambda: _AT[0]

TLOG = TL.TradeLogger(os.path.join(_TMP, "t.db"), paper_trading=False)
TL._trade_logger = TLOG
_N = [0]


def _row(paper=False):
    _N[0] += 1
    tid = f"RS-{_N[0]:03d}-0000"
    TLOG.log_entry(TL.make_record(
        trade_id=tid, symbol="QQQ", strategy="PARK", setup_type="PARK", option_side="call", contracts=3,
        entry_premium=1.00, total_cost=300.0, max_loss=300.0, stop_premium=0.0, option_symbol=SYM,
        expiry="2099-01-01"))
    return _reread(tid)


def _reread(tid):
    with TLOG._db() as conn:
        row = conn.execute("SELECT * FROM trades WHERE trade_id=?", (tid,)).fetchone()
    return TL.make_record(**dict(row))


def _status(tid):
    r = _reread(tid)
    return r.get("status"), r.get("exit_premium"), r.get("exit_reason"), r.get("live_exit_state")


class _Broker(MisbehavingBroker):
    """The shared misbehaving broker, plus: part-fill the next accepted order, count every Account call, and the most
    orders ever working at once."""
    def __init__(self):
        super().__init__()
        self.partial_next = None          # (qty, price): the next accepted order part-fills at once
        self.calls = 0
        self.max_working = 0
        self.unreadable_ids = set()       # get_order raises for these ids only

    async def place_order(self, session, order, dry_run=False):
        self.calls += 1
        r = await super().place_order(session, order, dry_run)
        if self.partial_next and r.order is not None:
            q, p = self.partial_next
            self.partial_next = None
            self.fill(r.order.id, p, qty=q)
        self.max_working = max(self.max_working, len(self.working()))
        return r

    async def get_order(self, session, oid):
        self.calls += 1
        if str(oid) in self.unreadable_ids:
            raise RuntimeError("Couldn't parse response: 429 Too Many Requests")
        return await super().get_order(session, oid)

    async def get_live_orders(self, session):
        self.calls += 1
        return await super().get_live_orders(session)

    async def delete_order(self, session, oid):
        self.calls += 1
        return await super().delete_order(session, oid)

    async def get_positions(self, session, **kw):
        self.calls += 1
        return await super().get_positions(session, **kw)


def _broker():
    b = _Broker()
    b.hold(SYM, +3, 1.00)
    return b


def _engine(paper=False, unreadable=None):
    """The real engine. pages: every (kind) the engine asked to page; the once-per-kind rule is the engine's own
    (_live_exit_alerted), so the list holds what would really have been SENT. unreadable[0] True -> the order's
    fills do not read (_net_fill_price None), whatever the broker holds."""
    e = EE.ExitEngine(paper_trading=paper)
    e.pages = []
    e.reasons = []

    def _alert(tid, kind, msg):
        if (tid, kind) in e._live_exit_alerted:
            return
        e._live_exit_alerted.add((tid, kind))
        e.pages.append(kind)
    e._alert_live_exit_once = _alert
    if unreadable is not None:
        _real_nfp = e._net_fill_price
        e._net_fill_price = lambda record, placed: None if unreadable[0] else _real_nfp(record, placed)
    _real_submit = e._submit_live_close

    def _submit(record, contracts, mark_price, reason=""):
        e.reasons.append((reason, contracts, e._exit_policy(record, reason)))
        return _real_submit(record, contracts, mark_price, reason=reason)
    e._submit_live_close = _submit
    return e


class _Quiet:
    def __getattr__(self, name):
        return lambda *a, **k: True


class _Plan:
    """The management plan, scripted: intent[0] is what decide() returns this tick (None -> the engine decides)."""
    def __init__(self):
        self.intent = [None]

    def decide(self, *a, **k):
        return self.intent[0]


def _manager(engine, plan, trigger, paper=False):
    """A real PositionManager whose tick sees mark 1.10, the scripted plan, and the engine's evaluate() answering
    trigger[0] = (should_exit, reason)."""
    pm = PM.PositionManager(paper_trading=paper)
    pm._trade_logger = TLOG
    pm._fetch_current_premium = lambda record, chain=None: 1.10

    def _evaluate(record, prem, **k):
        se, why = trigger[0]
        return EE.ExitDecision(should_exit=se, exit_reason=why if se else "")
    engine.evaluate = _evaluate
    return pm


def _close_intent(reason, pricing):
    it = MG.Intent("CLOSE", reason=reason)
    it.pricing = pricing
    return it


def _try(fn):
    try:
        return fn()
    except Exception as exc:                                          # noqa: BLE001
        return exc


def m1_cases():
    # R1-R3 — a kept order (its cancel failed) cannot be read on resume
    b = _broker()
    e = _engine()
    rec = _row()
    with bind(b, EE):
        b.cancel_mode = "raise"
        r1 = _try(lambda: e._confirm_and_book_live_exit(rec, "hard_stop: -40%", 1.10))
        kept1 = rec.get("_live_exit_order_id")
        b.cancel_mode = "ok"
        b.get_order_raises = True
        r2 = _try(lambda: e._confirm_and_book_live_exit(rec, "hard_stop: -40%", 1.10))
        st = _status(rec["trade_id"])[3]
        row_oid = (json.loads(st) or {}).get("order_id") if st else None
        check("R1 M1: the kept order cannot be read on resume -> nothing posts, id kept (memory and row), one page",
              b.place_calls == 1 and kept1 == "O1" and rec.get("_live_exit_order_id") == "O1" and row_oid == "O1"
              and getattr(r2, "confirmed", True) is False and e.pages.count("resume-read") == 1,
              f"r1={getattr(r1, 'detail', r1)!r} r2={getattr(r2, 'detail', r2)!r} place_calls={b.place_calls} "
              f"id={rec.get('_live_exit_order_id')!r} row_oid={row_oid!r} pages={e.pages}")
        for _ in range(2):
            _try(lambda: e._confirm_and_book_live_exit(rec, "hard_stop: -40%", 1.10))
        check("R2 M1: two more unreadable passes -> still ONE order, never two working, still one page",
              b.place_calls == 1 and b.max_working <= 1 and len(b.working()) == 1
              and e.pages.count("resume-read") == 1,
              f"place_calls={b.place_calls} max_working={b.max_working} working={b.working()} pages={e.pages}")
        b.get_order_raises = False
        b.fill("O1", 0.95)
        r3 = _try(lambda: e._confirm_and_book_live_exit(rec, "hard_stop: -40%", 1.10))
        check("R3 M1: the read recovers -> the same order resumes and books once at its fill; flat, not short",
              getattr(r3, "confirmed", False) is True and abs(float(r3.fill_price or 0) - 0.95) < 1e-9
              and b.place_calls == 1 and b.position(SYM) == 0,
              f"r3={getattr(r3, 'detail', r3)!r} place_calls={b.place_calls} positions={b.positions()}")


def m2_cases():
    # R4-R6 — the order FILLS at the broker; its fills do not read for a while
    b = _broker()
    b.fill_on_accept = 0.90
    unreadable = [True]
    e = _engine(unreadable=unreadable)
    rec = _row()
    with bind(b, EE):
        r1 = _try(lambda: e._confirm_and_book_live_exit(rec, "park_lock_exit", 0.90))
        b.fill_on_accept = None
        r2 = _try(lambda: e._confirm_and_book_live_exit(rec, "park_lock_exit", 0.90))
        check("R4 M2: FILLED at the broker, fills unreadable -> nothing booked, nothing posts, id kept, one page",
              getattr(r1, "confirmed", True) is False and getattr(r2, "confirmed", True) is False
              and b.place_calls == 1 and rec.get("_live_exit_order_id") == "O1"
              and e.pages.count("fills-unreadable") == 1 and _status(rec["trade_id"])[0] == "open",
              f"r1={getattr(r1, 'detail', r1)!r} r2={getattr(r2, 'detail', r2)!r} place_calls={b.place_calls} "
              f"id={rec.get('_live_exit_order_id')!r} pages={e.pages} positions={b.positions()}")
        # a restart: new engine, the record re-read from the row (nothing in memory); its page is the new process's one
        e2 = _engine(unreadable=unreadable)
        rec2 = _reread(rec["trade_id"])
        r3 = _try(lambda: e2._confirm_and_book_live_exit(rec2, "park_lock_exit", 0.90))
        check("R5 M2: a restart while the fills are unreadable -> the id is in the row, nothing posts",
              getattr(r3, "confirmed", True) is False and b.place_calls == 1
              and rec2.get("_live_exit_order_id") == "O1" and b.position(SYM) == 0,
              f"r3={getattr(r3, 'detail', r3)!r} place_calls={b.place_calls} id={rec2.get('_live_exit_order_id')!r} "
              f"positions={b.positions()}")
        unreadable[0] = False
        r4 = _try(lambda: e2._confirm_and_book_live_exit(rec2, "park_lock_exit", 0.90))
        check("R6 M2: the fills read -> booked ONCE at the broker's fill; one order; one page per process; not short",
              getattr(r4, "confirmed", False) is True and abs(float(r4.fill_price or 0) - 0.90) < 1e-9
              and b.place_calls == 1 and b.position(SYM) == 0 and e.pages.count("fills-unreadable") == 1
              and e2.pages.count("fills-unreadable") == 1 and not rec2.get("_live_exit_order_id"),
              f"r4={getattr(r4, 'detail', r4)!r} place_calls={b.place_calls} "
              f"positions={b.positions()} pages={e.pages}/{e2.pages}")


def m3_cases():
    _gee = PM.get_exit_engine
    _ram, _rrm = PM.get_alert_manager, PM.get_risk_manager
    _gmp = MG.get_management_plan
    PM.get_alert_manager = lambda: _Quiet()
    PM.get_risk_manager = lambda: _Quiet()
    plan = _Plan()
    MG.get_management_plan = lambda: plan
    try:
        # R7 — partial on tick 1 (1 of 3), the trigger false on tick 2
        b = _broker()
        e = _engine()
        PM.get_exit_engine = lambda paper=False: e
        trig = [(True, "park_lock_exit")]
        pm = _manager(e, plan, trig)
        rec = _row()
        tid = rec["trade_id"]
        with bind(b, EE):
            b.partial_next = (1, 1.20)
            k1 = _try(lambda: pm._manage_one(rec, None, None))
            trig[0] = (False, "")
            b.fill_on_accept = 1.10
            k2 = _try(lambda: pm._manage_one(rec, None, None))
        st = _status(tid)
        qtys = [c for (_, c, _) in e.reasons]
        check("R7 M3: partial 1/3 on tick 1, the trigger false on tick 2 -> the remainder (2) posts on tick 2 under "
              "park_lock_exit and books at the weighted average",
              k1 is True and k2 is False and qtys == [3, 2] and [r for (r, _, _) in e.reasons] == ["park_lock_exit"] * 2
              and st[0] == "closed" and st[2] == "park_lock_exit"
              and abs(float(st[1] or 0) - (1.20 + 2 * 1.10) / 3) < 1e-3 and b.position(SYM) == 0,
              f"k1={k1!r} k2={k2!r} posts={e.reasons} row={st[:3]} positions={b.positions()}")

        # R8 — restart mid-close: partial on tick 1 under a declared-pricing close; restart; the trigger false
        b = _broker()
        e = _engine()
        PM.get_exit_engine = lambda paper=False: e
        trig = [(False, "")]
        pm = _manager(e, plan, trig)
        rec = _row()
        tid = rec["trade_id"]
        with bind(b, EE):
            plan.intent[0] = _close_intent("thesis_break", "floor")       # a walk reason the plan declares floor
            b.partial_next = (1, 1.20)
            k1 = _try(lambda: pm._manage_one(rec, None, None))
            plan.intent[0] = None
            e2 = _engine()                                              # RESTART: nothing carried in memory
            PM.get_exit_engine = lambda paper=False: e2
            pm2 = _manager(e2, plan, trig)
            rec2 = _reread(tid)
            b.fill_on_accept = 1.05
            k2 = _try(lambda: pm2._manage_one(rec2, None, None))
        st = _status(tid)
        check("R8 M3: restart mid-close, the trigger false -> the remainder (2) posts under the LAST reason with the "
              "pricing it declared (floor), and books",
              k1 is True and k2 is False and e.reasons == [("thesis_break", 3, "floor")]
              and e2.reasons == [("thesis_break", 2, "floor")] and st[0] == "closed" and st[2] == "thesis_break"
              and b.position(SYM) == 0,
              f"k1={k1!r} k2={k2!r} before={e.reasons} after={e2.reasons} row={st[:3]} positions={b.positions()}")

        # R9 — a kept close-order id (its cancel failed on tick 1), the trigger false on tick 2
        b = _broker()
        e = _engine()
        PM.get_exit_engine = lambda paper=False: e
        trig = [(True, "hard_stop: -40%")]
        pm = _manager(e, plan, trig)
        rec = _row()
        tid = rec["trade_id"]
        with bind(b, EE):
            b.cancel_mode = "raise"
            k1 = _try(lambda: pm._manage_one(rec, None, None))
            b.cancel_mode = "ok"
            trig[0] = (False, "")
            b.fill("O1", 0.70)
            k2 = _try(lambda: pm._manage_one(rec, None, None))
        st = _status(tid)
        check("R9 M3: a kept close-order id, the trigger false -> the same order resumes (no new post) and books",
              k1 is True and k2 is False and b.place_calls == 1 and st[0] == "closed"
              and st[2] == "hard_stop: -40%" and abs(float(st[1] or 0) - 0.70) < 1e-9 and b.position(SYM) == 0,
              f"k1={k1!r} k2={k2!r} place_calls={b.place_calls} row={st[:3]} positions={b.positions()}")

        # R10 — a fully-closed record is never re-posted (the R9 record, in memory and re-read)
        n0 = b.place_calls
        with bind(b, EE):
            k3 = _try(lambda: pm._manage_one(rec, None, None))
            k4 = _try(lambda: pm._manage_one(_reread(tid), None, None))
        check("R10 M3: after the booking, ticks with the trigger false post nothing; the row's exit state is NULL",
              b.place_calls == n0 and k3 is True and k4 is True and not _status(tid)[3]
              and not rec.get("_live_exit_order_id") and not rec.get("_live_exit_fills"),
              f"place_calls {n0}->{b.place_calls} k3={k3!r} k4={k4!r} state={_status(tid)[3]!r}")

        # R11 — no started close, the trigger false: no exit, zero broker calls
        b = _broker()
        e = _engine()
        PM.get_exit_engine = lambda paper=False: e
        trig = [(False, "")]
        pm = _manager(e, plan, trig)
        rec = _row()
        with bind(b, EE):
            ks = [_try(lambda: pm._manage_one(rec, None, None)) for _ in range(3)]
        check("R11 no started close, the trigger false -> no exit and ZERO broker calls",
              ks == [True, True, True] and b.calls == 0 and not e.reasons,
              f"keeps={ks} broker calls={b.calls} posts={e.reasons}")

        # R12 — paper: never continued, even with a stray live_exit_state on the row
        paper = _engine(paper=True)
        PM.get_exit_engine = lambda paper_=True: paper
        pm = _manager(paper, plan, [(False, "")], paper=True)
        rec = _row()
        rec["live_exit_state"] = json.dumps({"fills": [[1, 1.2]], "order_id": "O9", "reason": "park_lock_exit"})
        calls = []
        _peo = paper.place_exit_order
        paper.place_exit_order = lambda r, why, mark_price=None: (calls.append(why), _peo(r, why, mark_price))[1]
        k = _try(lambda: pm._manage_one(rec, None, None))
        check("R12 paper: a paper record with the trigger false is never closed (a stray live_exit_state ignored)",
              k is True and calls == [] and _status(rec["trade_id"])[0] == "open",
              f"keep={k!r} place_exit_order calls={calls}")
    finally:
        PM.get_exit_engine = _gee
        PM.get_alert_manager, PM.get_risk_manager = _ram, _rrm
        MG.get_management_plan = _gmp


EOD = "hard_close_ladder_15:50_ET"


def _kept_unreadable(b, e, rec):
    """Tick 1 (11:00): a stop posts O1, its cancel fails, O1 is kept and from then on can never be read."""
    _AT[0] = _D.datetime(2026, 11, 23, 11, 0, tzinfo=_ETZ)
    b.cancel_mode = "raise"
    e._confirm_and_book_live_exit(rec, "hard_stop: -40%", 1.10)
    b.cancel_mode = "ok"
    b.unreadable_ids.add("O1")
    for _ in range(2):
        e._confirm_and_book_live_exit(rec, "hard_stop: -40%", 1.10)


def giveup_cases():
    try:
        for name, at, label in (("R13", (15, 51), "the 15:50 ladder"), ("R14", (15, 56), "the 15:55 cross")):
            b = _broker()
            e = _engine()
            rec = _row()
            with bind(b, EE):
                _kept_unreadable(b, e, rec)
                before = b.place_calls
                _AT[0] = _D.datetime(2026, 11, 23, at[0], at[1], tzinfo=_ETZ)
                b.fill_on_accept = 0.80
                r = _try(lambda: e._confirm_and_book_live_exit(rec, EOD, 0.80))
            mkt = b.placed_prices[-1] is None if b.placed_prices else False
            extra = (" and the close is a MARKET order" if name == "R14" else "")
            check(f"{name} EXIT.14: the kept id unreadable all day; at {label} the give-up cancels it, confirms it dead "
                  f"and closes the broker-held 3{extra} -> flat, never two working, booked once",
                  before == 1 and getattr(r, "confirmed", False) is True and b.place_calls == 2
                  and b.max_working <= 1 and b.position(SYM) == 0 and b.deleted.count("O1") == 2
                  and b.working() == []
                  and (mkt if name == "R14" else True),
                  f"posts before EOD={before} r={getattr(r, 'detail', r)!r} place_calls={b.place_calls} "
                  f"max_working={b.max_working} working={b.working()} positions={b.positions()} deleted={b.deleted} "
                  f"prices={b.placed_prices}")

        # R15 — unreadable, but FILLED at the broker
        b = _broker()
        e = _engine()
        rec = _row()
        with bind(b, EE):
            _kept_unreadable(b, e, rec)
            b.fill("O1", 0.85)
            _AT[0] = _D.datetime(2026, 11, 23, 15, 51, tzinfo=_ETZ)
            r = _try(lambda: e._confirm_and_book_live_exit(rec, EOD, 0.80))
        check("R15 EXIT.14: the kept id unreadable but FILLED at the broker -> the give-up books once from the book, "
              "posts nothing",
              getattr(r, "confirmed", False) is True and abs(float(r.fill_price or 0) - 0.85) < 1e-9
              and b.place_calls == 1 and b.position(SYM) == 0,
              f"r={getattr(r, 'detail', r)!r} place_calls={b.place_calls} positions={b.positions()}")

        # R16 — the book unreadable too
        b = _broker()
        e = _engine()
        rec = _row()
        with bind(b, EE):
            _kept_unreadable(b, e, rec)
            b.live_orders_raise = True
            _AT[0] = _D.datetime(2026, 11, 23, 15, 51, tzinfo=_ETZ)
            rs = [_try(lambda: e._confirm_and_book_live_exit(rec, EOD, 0.80)) for _ in range(2)]
        check("R16 EXIT.14: the book unreadable too at the give-up -> nothing posts, the id is kept, one page",
              all(getattr(x, "confirmed", True) is False for x in rs) and b.place_calls == 1
              and rec.get("_live_exit_order_id") == "O1" and e.pages.count("giveup-book") <= 1
              and len(b.working()) == 1,
              f"rs={[getattr(x, 'detail', x) for x in rs]} place_calls={b.place_calls} pages={e.pages}")

        # R17 — the broker holds none at the give-up
        b = _broker()
        e = _engine()
        rec = _row()
        with bind(b, EE):
            _kept_unreadable(b, e, rec)
            b.hold(SYM, -3, 1.00)                                       # closed elsewhere: flat at the broker
            _AT[0] = _D.datetime(2026, 11, 23, 15, 56, tzinfo=_ETZ)
            rs = [_try(lambda: e._confirm_and_book_live_exit(rec, EOD, 0.80)) for _ in range(3)]
            e2 = _engine()                                              # and after a restart
            rs.append(_try(lambda: e2._confirm_and_book_live_exit(_reread(rec["trade_id"]), EOD, 0.80)))
        check("R17 EXIT.14: the broker holds none at the give-up -> nothing posts (this pass, later, after a "
              "restart), never a short, one page",
              all(getattr(x, "confirmed", True) is False for x in rs) and b.place_calls == 1
              and b.position(SYM) == 0 and e.pages.count("giveup-gone") == 1,
              f"rs={[getattr(x, 'detail', x) for x in rs]} place_calls={b.place_calls} positions={b.positions()} "
              f"pages={e.pages}")
    finally:
        _AT[0] = _D.datetime(2026, 11, 23, 11, 0, tzinfo=_ETZ)


def main():
    print("check_exit_resume_safety")
    for fn in (m1_cases, m2_cases, m3_cases, giveup_cases):
        try:
            fn()
        except Exception as exc:                                      # noqa: BLE001
            import traceback
            traceback.print_exc()
            check(f"{fn.__name__} ran", False, f"{type(exc).__name__}: {exc}")
    if PROBLEMS:
        print(f"\nRED — {len(PROBLEMS)} failed: {', '.join(p.split(':')[0].split()[0] for p in PROBLEMS)}")
        return 1
    print("\nGREEN — a live close never posts beside itself on an unreadable read, never sells twice on late fills, "
          "and a started close finishes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
