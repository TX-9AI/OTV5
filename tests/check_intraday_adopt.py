#!/usr/bin/env python3
"""
tests/check_intraday_adopt.py  v5.0
v5.0  2026-11-16  OTV5 r129 (LOP.2 / FA.3; the cold audit 2026-11-15, critical, live-only) — NEW. A BROKER POSITION
      NO ROW EXPLAINS IS ADOPTED INTRADAY, THEN STOPPED, EXITED AND FLATTENED, AND NEVER CLOSED TWICE.

  🔴 THE DEFECT (OTV5 r128 a0a9f6f): main._intraday_reconcile returned at once when no open row existed and otherwise
  only inspected the rows it had ("it does not adopt brand-new broker positions intraday"); the only adoption was the
  boot reconcile (_reconcile_with_broker, called from _recover_open_position). A fill the bot never recorded (r127's
  lost reply that FILLED, a fill after the confirm deadline, order_guard's FILLED-after-error) had no stop, no exit and
  no EOD flatten until the next restart.

  OFFLINE, on the shared misbehaving broker (tests/broker_harness.py; no network, no credentials). The real
  main._intraday_reconcile, the real get_open_option_positions, the real PositionManager and live ExitEngine, on a
  temp trades.db.
  A1  an unrecorded long, nothing open in the DB -> ONE ADOPTED row (broker qty and average, a stop), managed, paged
  A2  the next slot -> still ONE adopted row, no second page
  A3  the adopted position's stop -> ONE close order, flat, row closed; the next slot adopts nothing
  A4  adopted at 15:55 -> flatten_all closes it with ONE order, flat; a second flatten posts nothing
  A5  a leg an open DB row carries -> never adopted; the managed record object is untouched (its state kept)
  A6  a leg only a managed in-memory record carries -> never adopted
  A7  a WORKING order touches the leg -> nothing adopted this pass (paged once); once the order is dead, adopted
  A8  the order book unreadable -> nothing adopted (fail closed); readable at the next slot -> adopted
  A9  r127's lost entry that FILLED -> adopted once (1 row = the broker's 1 contract); the intent stays blocked
  A10 an unrecorded credit vertical -> both legs adopted (paired, no anomaly) in one pass, both managed
  A11 another family's position (SPY on the QQQ box) -> never adopted
  A12 paper -> no broker read, nothing adopted; the main-loop call stays behind `not state.paper_trading`
  A13 an open row of ours on one leg and an unrecorded position on another -> only the unrecorded one is adopted
  A14 the same with nothing loaded in memory yet -> our row is loaded before the adopted one joins (both managed)
  A5b a leg only an open DB row carries while the manager holds some other record -> never adopted
  BORN RED on r128 a0a9f6f at A1-A4, A7-A10, A13, A14 (see docs/BACKLOG.md LOP.2).

Run:  python3 tests/check_intraday_adopt.py
"""
import ast
import asyncio
import os
import sys
import tempfile
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ["OT_INSTRUMENT"] = "QQQ"
_TMP = tempfile.mkdtemp(prefix="check_intraday_adopt_")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_TMP, "t.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_TMP, "d.db"))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_TMP, "sj"))
import logging                                                        # noqa: E402
logging.disable(logging.CRITICAL)
import config                                                         # noqa: E402
config.LOG_FILE = os.path.join(_TMP, "bot.log")
config.LIVE_FILL_POLL_SECONDS = 0.0
config.LIVE_FILL_DEADLINE_SECONDS = 0.0
from broker_harness import MisbehavingBroker, bind                    # noqa: E402

PROBLEMS = []
SYM = "QQQ   991231C00500000"
SHORT = "QQQ   991231P00495000"
LONG = "QQQ   991231P00490000"
SPY = "SPY   991231C00600000"


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name.split()[0])


import database.trade_logger as TL                                    # noqa: E402
import execution.exit_engine as EE                                    # noqa: E402
import execution.position_manager as PM                               # noqa: E402
import execution.limit_ladder as LL                                   # noqa: E402
import utils.time_utils as TU                                         # noqa: E402
from execution import order_guard as OG                               # noqa: E402
import main as M                                                      # noqa: E402

_N = [0]


class _Pages:
    def __init__(self):
        self.adopted, self.text = [], []

    def send_adopted_alert(self, **k):
        self.adopted.append(k)

    def _send(self, text, *a, **k):
        self.text.append(text)

    def __getattr__(self, name):
        return lambda *a, **k: True


class _Quiet:
    def __getattr__(self, name):
        return lambda *a, **k: True


LIVE = SimpleNamespace(paper_trading=False, last_reconcile_slot=None)
PAPER = SimpleNamespace(paper_trading=True, last_reconcile_slot=None)


def _fresh():
    """A new temp trades.db, a fresh live PositionManager + ExitEngine, and a page recorder."""
    _N[0] += 1
    tlog = TL.TradeLogger(os.path.join(_TMP, f"t{_N[0]}.db"), paper_trading=False)
    TL._trade_logger = tlog
    pages = _Pages()
    eng = EE.ExitEngine(paper_trading=False)
    eng._alert_live_exit_once = lambda tid, kind, msg: None
    PM.get_exit_engine = lambda paper=False: eng
    PM.get_alert_manager = lambda: _Quiet()
    PM.get_risk_manager = lambda: _Quiet()
    pm = PM.PositionManager(paper_trading=False)
    pm._trade_logger = tlog
    M.get_trade_logger = lambda: tlog
    M.get_position_manager = lambda paper=False: pm
    M.get_alert_manager = lambda: pages
    if hasattr(M, "_ADOPT_DEFER_PAGED"):
        M._ADOPT_DEFER_PAGED.clear()
    OG.reset()
    return tlog, pm, pages


def _open_rows(tlog):
    return tlog.get_open_trades()


def _adopted(tlog):
    return [r for r in _open_rows(tlog) if r.get("strategy") == "ADOPTED"]


def _status(tlog, tid):
    with tlog._db() as conn:
        r = conn.execute("SELECT status FROM trades WHERE trade_id=?", (tid,)).fetchone()
    return r[0] if r else None


def _recon(b, state=LIVE):
    with bind(b, EE, OG):
        M._intraday_reconcile(state, "QQQ")


def _row(tlog, sym=SYM):
    _N[0] += 1
    tid = f"IA-{_N[0]:03d}-0000"
    tlog.log_entry(TL.make_record(trade_id=tid, symbol="QQQ", strategy="RunawayContinuation",
                                  setup_type="RUNAWAY", option_side="call", contracts=1, entry_premium=1.00,
                                  total_cost=100.0, max_loss=100.0, stop_premium=0.5, option_symbol=sym, paper_trade=0,
                                  expiry="2099-01-01"))
    return tid


def _place(b, sym, action, mode="ok"):
    """Post one order straight at the fake broker (as a bot path or the operator would)."""
    b.script_place(mode)
    order = SimpleNamespace(price=-0.95, legs=[SimpleNamespace(symbol=sym, action=action, quantity=1)])
    try:
        asyncio.run(b.place_order(None, order))
    except Exception:                                                 # noqa: BLE001
        pass
    return b.accepted[-1]


STOP = EE.ExitDecision(should_exit=True, exit_reason="stop_hit")


def cases():
    # A1 / A2 / A3 — an unrecorded long, adopted, then stopped once
    tlog, pm, pages = _fresh()
    b = MisbehavingBroker(); b.hold(SYM, +1, 0.95)
    _recon(b)
    ad = _adopted(tlog)
    rec = ad[0] if ad else {}
    managed = [r for r in pm.get_open_records() if r.get("strategy") == "ADOPTED"]
    check("A1 unrecorded long, nothing open: ONE ADOPTED row (broker qty 1 @ 0.95, a stop), managed, paged once",
          len(ad) == 1 and rec.get("option_symbol") == SYM and int(rec.get("contracts") or 0) == 1
          and abs(float(rec.get("entry_premium") or 0) - 0.95) < 1e-9 and 0 < float(rec.get("stop_premium") or 0) < 0.95
          and len(managed) == 1 and len(pages.adopted) == 1,
          f"adopted={len(ad)} rec={ {k: rec.get(k) for k in ('option_symbol', 'contracts', 'entry_premium', 'stop_premium')} } "
          f"managed={len(managed)} pages={len(pages.adopted)}")
    _recon(b)
    check("A2 the next slot: still ONE adopted row and ONE page (never adopted twice)",
          len(_adopted(tlog)) == 1 and len(pages.adopted) == 1
          and len([r for r in pm.get_open_records() if r.get("strategy") == "ADOPTED"]) == 1,
          f"adopted={len(_adopted(tlog))} pages={len(pages.adopted)} managed={len(pm.get_open_records())}")
    ok3, d3 = False, "nothing adopted"
    if managed:
        b.fill_on_accept = 0.40
        with bind(b, EE, OG):
            done = pm._execute_exit(managed[0], STOP, 0.40)
        _recon(b)
        ok3 = (done is True and b.place_calls == 1 and b.position(SYM) == 0
               and _status(tlog, managed[0]["trade_id"]) == "closed" and not _adopted(tlog)
               and len(pages.adopted) == 1)
        d3 = (f"done={done} place_calls={b.place_calls} positions={b.positions()} "
              f"row={_status(tlog, managed[0]['trade_id'])} open_adopted={len(_adopted(tlog))}")
    check("A3 the adopted position's stop: ONE close order, flat, row closed; the next slot adopts nothing", ok3, d3)

    # A4 — adopted at the 15:55 cross, flattened once
    tlog, pm, pages = _fresh()
    b = MisbehavingBroker(); b.hold(SYM, +1, 0.95); b.fill_on_accept = 0.30
    _recon(b)
    _saved = (TU.eod_close_due, LL.hard_close_order_mode, EE.hard_close_order_mode)
    TU.eod_close_due = lambda *a, **k: True
    LL.hard_close_order_mode = lambda *a, **k: "market"
    EE.hard_close_order_mode = lambda *a, **k: "market"
    pm._fetch_current_premium = lambda record, chain=None: 0.30
    try:
        with bind(b, EE, OG):
            f1 = pm.flatten_all(reason="hard_close")
            calls1 = b.place_calls
            f2 = pm.flatten_all(reason="hard_close")
    finally:
        TU.eod_close_due, LL.hard_close_order_mode, EE.hard_close_order_mode = _saved
    check("A4 adopted before the 15:55 cross: flatten_all closes it with ONE order, flat; a second flatten posts nothing",
          calls1 == 1 and b.place_calls == 1 and b.position(SYM) == 0 and f1 == [] and f2 == []
          and not _adopted(tlog),
          f"calls1={calls1} place_calls={b.place_calls} positions={b.positions()} f1={f1} f2={f2} "
          f"open_adopted={len(_adopted(tlog))}")

    # A5 — a leg an open row carries
    tlog, pm, pages = _fresh()
    tid = _row(tlog)
    mine = TL.make_record(**dict(tlog.get_open_trades()[0]))
    mine["_live_exit_order_id"] = "LOST:1.000"                         # a close in flight (r128) lives on the record
    pm.set_open_positions([mine])
    b = MisbehavingBroker(); b.hold(SYM, +1, 1.00)
    _recon(b)
    check("A5 a leg an open row carries: never adopted; the managed record object (and its state) untouched",
          not _adopted(tlog) and len(pm.get_open_records()) == 1 and pm.get_open_records()[0] is mine
          and mine.get("_live_exit_order_id") == "LOST:1.000" and not pages.adopted,
          f"adopted={len(_adopted(tlog))} managed={[r.get('trade_id') for r in pm.get_open_records()]} "
          f"same={pm.get_open_records()[0] is mine if pm.get_open_records() else None}")

    # A13 — an open row of ours on one leg, an unrecorded position on another
    tlog, pm, pages = _fresh()
    tid13 = _row(tlog, sym=SYM)
    pm.set_open_positions([TL.make_record(**dict(tlog.get_open_trades()[0]))])
    b = MisbehavingBroker(); b.hold(SYM, +1, 1.00); b.hold(SHORT, -1, 0.50)
    _recon(b)
    ad = _adopted(tlog)
    check("A13 our row on one leg, an unrecorded position on another: only the unrecorded one is adopted, both managed",
          [r.get("option_symbol") for r in ad] == [SHORT] and len(pm.get_open_records()) == 2
          and _status(tlog, tid13) == "open",
          f"adopted={[r.get('option_symbol') for r in ad]} managed={len(pm.get_open_records())}")

    # A14 — the same, on a fresh process whose manager has not loaded its rows yet
    tlog, pm, pages = _fresh()
    tid14 = _row(tlog, sym=SYM)
    b = MisbehavingBroker(); b.hold(SYM, +1, 1.00); b.hold(SHORT, -1, 0.50)
    _recon(b)
    ids = sorted(str(r.get("trade_id", ""))[:5] for r in pm.get_open_records())
    check("A14 nothing loaded in memory yet: the manager loads our open row BEFORE the adopted one joins (both managed)",
          len(_adopted(tlog)) == 1 and len(ids) == 2 and any(r.get("trade_id") == tid14 for r in pm.get_open_records()),
          f"managed={ids}")

    # A5b — a leg an open DB row carries, while the manager holds only some OTHER record
    tlog, pm, pages = _fresh()
    _row(tlog, sym=SYM)
    other = TL.make_record(trade_id="IA-OTH-0000", symbol="QQQ", strategy="RunawayContinuation", option_side="put",
                           contracts=1, entry_premium=1.0, option_symbol=LONG, expiry="2099-01-01", paper_trade=0)
    pm.set_open_positions([other])
    b = MisbehavingBroker(); b.hold(SYM, +1, 1.00); b.hold(LONG, +1, 0.20)
    _recon(b)
    check("A5b a leg only the DB row carries (the manager holds another record): never adopted",
          not _adopted(tlog) and not pages.adopted, f"adopted={[r.get('option_symbol') for r in _adopted(tlog)]}")

    # A6 — a leg only an in-memory managed record carries (no open DB row)
    tlog, pm, pages = _fresh()
    ghost = TL.make_record(trade_id="IA-MEM-0000", symbol="QQQ", strategy="RunawayContinuation", option_side="call",
                           contracts=1, entry_premium=1.0, option_symbol=SYM, expiry="2099-01-01", paper_trade=0)
    pm.set_open_positions([ghost])
    b = MisbehavingBroker(); b.hold(SYM, +1, 1.00)
    _recon(b)
    check("A6 a leg only a managed in-memory record carries: never adopted",
          not _adopted(tlog) and not pages.adopted and len(pm.get_open_records()) == 1,
          f"adopted={len(_adopted(tlog))} pages={len(pages.adopted)}")

    # A7 — a working order touches the leg
    tlog, pm, pages = _fresh()
    b = MisbehavingBroker(); b.hold(SYM, +1, 0.95)
    oid = _place(b, SYM, "SELL_TO_CLOSE")                            # a close working at the broker, no row
    _recon(b)
    n_working = len(_adopted(tlog))
    _recon(b)
    defer_pages = [t for t in pages.text if "UNRECORDED POSITION" in t]
    b.set_status(oid, "Cancelled")
    _recon(b)
    check("A7 a WORKING order touches the leg: nothing adopted (paged once); once it is dead, adopted at the next slot",
          n_working == 0 and len(defer_pages) == 1 and len(_adopted(tlog)) == 1 and len(pages.adopted) == 1
          and b.place_calls == 1,
          f"while_working={n_working} defer_pages={len(defer_pages)} after={len(_adopted(tlog))} "
          f"place_calls={b.place_calls}")

    # A8 — the order book unreadable
    tlog, pm, pages = _fresh()
    b = MisbehavingBroker(); b.hold(SYM, +1, 0.95); b.live_orders_raise = True
    _recon(b)
    n_unread = len(_adopted(tlog))
    b.live_orders_raise = False
    _recon(b)
    check("A8 order book unreadable: nothing adopted (fail closed); readable at the next slot -> adopted",
          n_unread == 0 and len(_adopted(tlog)) == 1 and any("UNRECORDED POSITION" in t for t in pages.text),
          f"while_unread={n_unread} after={len(_adopted(tlog))} pages={pages.text}")

    # A9 — r127's lost entry that FILLED
    tlog, pm, pages = _fresh()
    b = MisbehavingBroker(); b.fill_on_accept = 0.95
    _place(b, SYM, "BUY_TO_OPEN", mode="lost")                        # accepted and filled, the reply lost
    from execution.ladder_registry import intent_key
    key = intent_key(SYM, "open", "single")
    with bind(b, EE, OG):
        OG.after_lost_post(key, [SYM], SimpleNamespace(fake=True), b, "A9 entry")
        ok_before, _w = OG.clear_to_post(key, SimpleNamespace(fake=True), b)
    _recon(b)
    _recon(b)
    with bind(b, EE, OG):
        ok_after, why_after = OG.clear_to_post(key, SimpleNamespace(fake=True), b)
    ad = _adopted(tlog)
    check("A9 r127's lost entry that FILLED: adopted ONCE (1 row, 1 contract = the broker's); the intent stays blocked",
          ok_before is False and len(ad) == 1 and int(ad[0].get("contracts") or 0) == 1 and b.position(SYM) == 1
          and ok_after is False and b.place_calls == 1,
          f"blocked_before={not ok_before} adopted={len(ad)} broker={b.positions()} blocked_after={not ok_after} "
          f"({why_after}) place_calls={b.place_calls}")

    # A10 — an unrecorded credit vertical
    tlog, pm, pages = _fresh()
    b = MisbehavingBroker(); b.hold(SHORT, -1, 0.50); b.hold(LONG, +1, 0.20)
    _recon(b)
    ad = _adopted(tlog)
    by = {r.get("option_symbol"): r for r in ad}
    check("A10 an unrecorded credit vertical: both legs adopted in one pass (short + long, no anomaly), both managed",
          set(by) == {SHORT, LONG} and int(by[SHORT].get("is_short_position") or 0) == 1
          and not any(p.get("anomaly") for p in pages.adopted) and len(pages.adopted) == 2
          and len([r for r in pm.get_open_records() if r.get("strategy") == "ADOPTED"]) == 2,
          f"adopted={sorted(by)} pages={[(p.get('position_desc'), p.get('anomaly')) for p in pages.adopted]}")

    # A11 — another family
    tlog, pm, pages = _fresh()
    b = MisbehavingBroker(); b.hold(SPY, +1, 2.00)
    _recon(b)
    check("A11 another family's position (SPY on the QQQ box): never adopted",
          not _adopted(tlog) and not pages.adopted, f"adopted={[r.get('option_symbol') for r in _adopted(tlog)]}")

    # A12 — paper
    tlog, pm, pages = _fresh()
    b = MisbehavingBroker(); b.hold(SYM, +1, 0.95)
    reads = []
    _gp, _gl = b.get_positions, b.get_live_orders

    async def _gp2(session, **kw):
        reads.append("positions"); return await _gp(session, **kw)

    async def _gl2(session):
        reads.append("orders"); return await _gl(session)
    b.get_positions, b.get_live_orders = _gp2, _gl2
    got = []
    if hasattr(M, "_intraday_adopt"):
        with bind(b, EE, OG):
            got = M._intraday_adopt(PAPER, "QQQ", [{"symbol": SYM, "underlying": "QQQ", "quantity": 1,
                                                    "direction": "Long", "average_open_price": 0.95}])
    src = open(os.path.join(ROOT, "main.py")).read()
    gated = False
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.If) and "paper_trading" in ast.unparse(node.test) \
                and ast.unparse(node.test).startswith("not state.paper_trading"):
            if any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_intraday_reconcile"
                   for n in ast.walk(node)):
                gated = True
    check("A12 paper: no broker read, nothing adopted; the main-loop call stays behind `not state.paper_trading`",
          got == [] and reads == [] and not _adopted(tlog) and gated,
          f"got={got} reads={reads} gated={gated}")


def main():
    print("check_intraday_adopt")
    _saved = (PM.get_exit_engine, PM.get_alert_manager, PM.get_risk_manager, TL._trade_logger,
              M.get_trade_logger, M.get_position_manager, M.get_alert_manager)
    try:
        cases()
    finally:
        (PM.get_exit_engine, PM.get_alert_manager, PM.get_risk_manager, TL._trade_logger,
         M.get_trade_logger, M.get_position_manager, M.get_alert_manager) = _saved
    print(f"\n{'ALL PASS' if not PROBLEMS else 'FAILED: ' + ', '.join(PROBLEMS)}")
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
