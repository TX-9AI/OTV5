#!/usr/bin/env python3
"""
tests/check_entry_suspect_block.py  v5.0
v5.0  2026-11-20  OTV5 r135 (GUARD.1; the live-readiness audit 2026-11-20 C3 + I3, live only) — NEW. NO SECOND OPENING
      ORDER WHILE AN EARLIER ONE'S FATE IS UNKNOWN, AND THE UNKNOWN IS RESOLVED ON THE NEXT TICK UNDER ITS OWN STRATEGY.
      The operator, 2026-11-20: "Yes, let's fix it smartly."

  🔴 THE DEFECT (OTV5 r134 57f7d6d): order_guard held a suspect per INTENT (one contract). Three cases leave a real
  broker order the DB does not know: (a) a cancel that cannot be confirmed, (b) a lost place_order reply, (c) an order
  FILLED whose fills cannot be read. Runaway and the Hunt re-pick the strike every tick and r133's freeze lapses after
  45 s idle, so a DIFFERENT contract passed clear_to_post and posted beside it; the fill was adopted only at the next
  10-minute slot, as ADOPTED, without its plan. I3: a partial entry whose cancel could not be confirmed booked nothing.

  OFFLINE, on the shared misbehaving broker (tests/broker_harness.py; no network, no credentials), through the REAL
  EntryEngine.enter / _place_single_leg, order_guard, order_confirm, buying_power, ladder_registry, main's tick hook
  (_resolve_entry_suspects), _intraday_reconcile / _intraday_adopt, _reconcile_with_broker, a live PositionManager and
  ExitEngine, on a temp trades.db. Time in order_confirm / entry_engine is a fake clock that moves when the code sleeps.
  S1  (a) cancel unconfirmed: a Runaway re-pick (another strike) AND a Hunt entry are refused (one order at the broker);
      the order is re-cancelled by the tick hook and, once dead with no fill, the block clears and the next entry posts
  S2  (a) then the order FILLS: the tick books ONE row under RunawayContinuation (its stop, broker qty and price, the
      order id), managed and alerted; the block clears; the intraday reconcile and the boot reconcile adopt nothing
  S3  (b) lost reply, order resting: the re-pick is refused; the order is cancelled; nothing is booked
  S4  (b) lost reply, order FILLED at once: booked under its strategy in the same call (one row, broker qty/price)
  S5  (c) FILLED with fills unreadable: the re-pick is refused; while unreadable the intraday adopt DEFERS (no ADOPTED
      row); once readable the tick books it under RunawayContinuation; adopt afterwards adopts nothing (one row)
  S6  I3: 3 ordered, 1 filled, cancel unconfirmed -> the detail names the PARTIAL; once dead, ONE row of 1 contract at the
      broker's fill price under its strategy; the block clears
  S7  bounded: fills never readable -> after RESOLVE_GIVEUP_S ONE page, the block stays; adopt then adopts it; the guard
      clears on the ADOPTED row and books nothing (one row on the leg)
  S8  an order id already on a trades row is never booked twice (a lost-post candidate that another entry booked)
  S9  exits are never blocked: with a suspect holding entries, a stop on an open row posts its close and closes the row
  S10 paper untouched: a paper entry books the mark (PAPER- id), no broker call, no suspect; the tick hook makes no
      broker call in paper
  S12 the booking pass posts nothing: the suspect resolves (and books) inside a re-pick's own clear_to_post -> that
      call posts NOTHING (its admission ran before the row existed); the row is booked once
  S13 after the day's last entry window: a suspect born 11:02 ET (PARK's window, the latest) whose fill never reads is
      given up once 11:03 + RESOLVE_GIVEUP_S has passed (whatever its age), the next reconcile slot ADOPTS it, and the
      15:55 hard close (flatten_all, which closes the position manager's records) closes it: flat, ONE row, closed
  S11 restart: the memory is gone but the boot sweep cancels the live order and blocks every entry until it reads dead;
      a fill made before the restart is adopted ONCE by the boot reconcile; a fill BOOKED before the restart is kept
  Born red on r134 57f7d6d at S1-S9, S11, S12 (S10 pins paper) and on the pre-window build at S13; 10 mutants red (see docs/BACKLOG.md GUARD.1).

Run:  python3 tests/check_entry_suspect_block.py
"""
import copy
import os
import sys
import tempfile
import time as _real_time
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
_TD = tempfile.mkdtemp(prefix="check_entry_suspect_block_")
for _k, _v in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"),
               ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"), ("OT_SIGNAL_JOURNAL_DIR", "sj"),
               ("OT_PLAN_STATES_FILE", "ps.json"), ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT")):
    os.environ[_k] = os.path.join(_TD, _v)
os.environ["OT_INSTRUMENT"] = "QQQ"
import logging                                                        # noqa: E402
logging.disable(logging.CRITICAL)
try:
    import config                                                     # noqa: E402
    config.LOG_FILE = os.path.join(_TD, "bot.log")
    import database.trade_logger as TL                                # noqa: E402
    import execution.entry_engine as EN                               # noqa: E402
    import execution.exit_engine as XE                                # noqa: E402
    import execution.position_manager as PM                           # noqa: E402
    from execution import order_confirm as OC                         # noqa: E402
    from execution import order_guard as OG                           # noqa: E402
    from execution import ladder_registry as LR                       # noqa: E402
    from execution import buying_power as BP                          # noqa: E402
    from execution import tick_size as TS                             # noqa: E402
    from strategy.base_strategy import OptionsSignal                  # noqa: E402
    from data.options_chain import OptionContract                     # noqa: E402
    import main as M                                                  # noqa: E402
    from broker_harness import MisbehavingBroker, bind, OrderStatus   # noqa: E402
except Exception as exc:                                              # noqa: BLE001
    print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
    sys.exit(2)

PROBLEMS = []
X = "QQQ   991231C00600000"      # Runaway's first pick
Y = "QQQ   991231C00601000"      # its re-pick a tick later
Z = "QQQ   991231P00590000"      # the Hunt's contract
W = "QQQ   991231C00610000"      # an unrelated open row (S9)


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name.split()[0])


# ── the fake clock (order_confirm / entry_engine only; order_guard keeps the real clock) ──────────────────
class Clock:
    def __init__(self):
        self.t = 0.0

    def monotonic(self):
        return self.t

    def time(self):
        return _real_time.time()

    def sleep(self, s):
        self.t += max(0.0, float(s))
        if self.t > 1e6:
            raise RuntimeError("fake clock: runaway sleep loop")


CLOCK = Clock()


class Broker(MisbehavingBroker):
    """+ hide_fill_reads: that many get_order reads of a FILLED order show it with no fills (case c);
       + partial_on_accept: (qty, price) filled the moment an order is accepted (I3)."""

    def __init__(self):
        super().__init__()
        self.hide_fill_reads = 0
        self.partial_on_accept = None

    async def place_order(self, session, order, dry_run=False):
        r = await super().place_order(session, order, dry_run)
        if self.partial_on_accept and getattr(r, "order", None) is not None:
            q, p = self.partial_on_accept
            self.fill(r.order.id, p, qty=q)
        return r

    async def get_order(self, session, oid):
        o = await super().get_order(session, oid)
        if (self.hide_fill_reads > 0 and o.status == OrderStatus.FILLED
                and all("OPEN" in str(getattr(lg.action, "value", lg.action)).upper().replace(" ", "_")
                        for lg in o.legs)):                            # entries only: a close's fills always read
            self.hide_fill_reads -= 1
            c = copy.copy(o)
            c.legs = [copy.copy(lg) for lg in o.legs]
            for lg in c.legs:
                lg.fills = []
            return c
        return o


class _Pages:
    def __init__(self):
        self.adopted, self.text, self.entries = [], [], []

    def send_adopted_alert(self, **k):
        self.adopted.append(k)

    def send_entry_alert(self, rec, *a, **k):
        self.entries.append(rec)

    def _send(self, text, *a, **k):
        self.text.append(text)

    def __getattr__(self, name):
        return lambda *a, **k: True


class _Quiet:
    def __getattr__(self, name):
        return lambda *a, **k: True


LIVE = SimpleNamespace(paper_trading=False, last_reconcile_slot=None)
PAPER = SimpleNamespace(paper_trading=True, last_reconcile_slot=None)
GPAGES = []
_N = [0]


def _fresh():
    """A temp trades.db, a live PositionManager + ExitEngine, page recorders, a clean guard / ladder / bp cache."""
    _N[0] += 1
    tlog = TL.TradeLogger(os.path.join(_TD, f"t{_N[0]}.db"), paper_trading=False)
    TL._trade_logger = tlog
    pages = _Pages()
    xe = XE.ExitEngine(paper_trading=False)
    xe._alert_live_exit_once = lambda tid, kind, msg: None
    PM.get_exit_engine = lambda paper=False: xe
    PM.get_alert_manager = lambda: _Quiet()
    PM.get_risk_manager = lambda: _Quiet()
    pm = PM.PositionManager(paper_trading=False)
    pm._trade_logger = tlog
    M.get_trade_logger = lambda: tlog
    M.get_position_manager = lambda paper=False: pm
    M.get_alert_manager = lambda: pages
    M.now_et = lambda: _at(10, 0)                                      # mid-session (S13 moves it)
    import utils.time_utils as _TU
    _TU.now_et = lambda: _at(10, 0)                                    # order_guard's clock (the window give-up)
    if hasattr(M, "_ADOPT_DEFER_PAGED"):
        M._ADOPT_DEFER_PAGED.clear()
    OG.reset(boot_clean=True)
    OG._page = lambda text: GPAGES.append(text)
    BP.reset()
    LR.reset_all()
    if hasattr(EN, "_PINS"):
        EN._PINS.clear()
    GPAGES.clear()
    CLOCK.t = 0.0
    OC.time = CLOCK
    EN.time = CLOCK
    EN.entries_open = lambda: True
    EN.EntryEngine._page_if_working = staticmethod(lambda fill, what: None)
    TS.cache_venue_rule("QQQ", [SimpleNamespace(threshold=None, value=0.01)])
    eng = EN.EntryEngine(paper_trading=False)
    eng._trade_logger = tlog
    return tlog, pm, pages, eng


def _sig(occ=X, strike=600.0, strategy="RunawayContinuation", side="call", direction="long", bid=3.40, ask=3.50):
    c = OptionContract(symbol=occ, underlying="QQQ", expiry="2099-12-31", option_type=side[0].upper(),
                       strike=strike, bid=bid, ask=ask, mark=round((bid + ask) / 2, 4))   # no streamer: one rung a call
    return OptionsSignal(strategy_name=strategy, setup_type="fixture", direction=direction, option_side=side,
                         underlying_entry=600.0, underlying_stop=598.0, underlying_target=604.0,
                         strike=strike, expiry="2099-12-31", entry_premium=c.mark, contract=c, notes="fixture")


def _sz(n=1):
    return SimpleNamespace(contracts=n, total_cost=3.45 * 100 * n, allowed=True)


def _rows(tlog, sym=None):
    out = [r for r in tlog.get_open_trades()]
    return [r for r in out if sym is None or r.get("option_symbol") == sym]


def _tick(b, state=LIVE):
    with bind(b, EN, OG, M):
        return M._resolve_entry_suspects(state) if hasattr(M, "_resolve_entry_suspects") else []


def _enter(b, eng, sig, n=1):
    with bind(b, EN, OG, M):
        rec = eng.enter(sig, _sz(n))
        if hasattr(M, "_hand_booked_to_manager"):
            M._hand_booked_to_manager(LIVE)
        return rec


def _recon(b):
    with bind(b, EN, OG, M):
        M._intraday_reconcile(LIVE, "QQQ")


def _held(rec, keys=("strategy", "option_symbol", "contracts", "entry_premium", "stop_premium", "order_id")):
    return {k: rec.get(k) for k in keys} if rec else None


def _is_runaway_row(r, qty, px, oid):
    return (r.get("strategy") == "RunawayContinuation" and int(r.get("contracts") or 0) == qty
            and abs(float(r.get("entry_premium") or 0) - px) < 1e-9 and str(r.get("order_id")) == oid
            and float(r.get("stop_premium") or 0) > 0 and r.get("setup_type") == "fixture")


def cases():
    # S1 — (a) cancel unconfirmed; re-pick and another strategy refused; dead -> clears
    tlog, pm, pages, eng = _fresh()
    b = Broker(); b.cancel_mode = "raise"
    r1 = _enter(b, eng, _sig(X))
    r2 = _enter(b, eng, _sig(Y, 601.0))                                # the re-pick, another strike
    r3 = _enter(b, eng, _sig(Z, 590.0, "LiquidityHunt", "put", "short"))
    calls_blocked = b.place_calls
    b.cancel_mode = "ok"
    _saved = OG.RECANCEL_EVERY_S if hasattr(OG, "RECANCEL_EVERY_S") else None
    if _saved is not None:
        OG.RECANCEL_EVERY_S = 0.0
    try:
        _tick(b); _tick(b)
    finally:
        if _saved is not None:
            OG.RECANCEL_EVERY_S = _saved
    dead = b.order("O1").status == OrderStatus.CANCELLED
    r4 = _enter(b, eng, _sig(Y, 601.0))
    check("S1 (a) cancel unconfirmed: the re-pick AND a Hunt entry are refused (1 order); the tick re-cancels it, "
          "and once dead the block clears and the next entry posts",
          r1 is None and r2 is None and r3 is None and calls_blocked == 1 and dead and b.place_calls == 2
          and not _rows(tlog, X),
          f"r1={r1 is not None} r2={r2 is not None} r3={r3 is not None} calls_while_blocked={calls_blocked} "
          f"O1={b.order('O1').status} calls_after={b.place_calls} rows={[_held(r) for r in _rows(tlog)]}")

    # S2 — (a) then the order fills: booked under its strategy, once; adopt + boot reconcile adopt nothing
    tlog, pm, pages, eng = _fresh()
    b = Broker(); b.cancel_mode = "raise"
    _enter(b, eng, _sig(X))
    _enter(b, eng, _sig(Y, 601.0))
    calls_blocked = b.place_calls
    b.fill("O1", 3.43)
    booked = _tick(b)
    rows = _rows(tlog, X)
    managed = [r for r in pm.get_open_records() if r.get("option_symbol") == X]
    _recon(b); _recon(b)
    with bind(b, EN, OG, M):
        live_rows = M._reconcile_with_broker(LIVE, tlog.get_open_trades_live(), "restart", "QQQ")
    rows2 = _rows(tlog)
    with bind(b, EN, OG):
        ok_after, _w = OG.clear_to_post("probe", SimpleNamespace(fake=True), b)
    check("S2 (a) then FILLED: the tick books ONE row under RunawayContinuation (1 @ 3.43, its stop, order O1), "
          "managed and alerted; the block clears; intraday adopt and the boot reconcile adopt nothing",
          calls_blocked == 1 and len(booked) == 1 and len(rows) == 1 and _is_runaway_row(rows[0], 1, 3.43, "O1")
          and len(managed) == 1 and len(pages.entries) == 1 and not pages.adopted and len(rows2) == 1
          and len(live_rows) == 1 and ok_after,
          f"calls={calls_blocked} booked={len(booked)} rows={[_held(r) for r in rows]} managed={len(managed)} "
          f"entry_alerts={len(pages.entries)} adopted={len(pages.adopted)} rows_after={len(rows2)} "
          f"boot_live={len(live_rows)} clear_after={ok_after}")

    # S3 — (b) lost reply, order resting
    tlog, pm, pages, eng = _fresh()
    b = Broker(); b.script_place("lost")
    r1 = _enter(b, eng, _sig(X))
    r2 = _enter(b, eng, _sig(Y, 601.0))
    calls_blocked = b.place_calls
    _sg = getattr(OG, "LOST_GRACE_S", None)
    OG.LOST_GRACE_S = 0.0
    try:
        _tick(b)
        r3 = _enter(b, eng, _sig(Y, 601.0))
    finally:
        OG.LOST_GRACE_S = _sg
    check("S3 (b) lost reply, order resting: the re-pick is refused; the order is cancelled; nothing booked; "
          "the block clears once the book shows nothing live",
          r1 is None and r2 is None and calls_blocked == 1 and b.order("O1").status == OrderStatus.CANCELLED
          and not _rows(tlog, X) and b.place_calls == 2,
          f"calls_while_blocked={calls_blocked} O1={b.order('O1').status} rows={[_held(r) for r in _rows(tlog)]} "
          f"calls_after={b.place_calls}")

    # S4 — (b) lost reply, FILLED at once
    tlog, pm, pages, eng = _fresh()
    b = Broker(); b.script_place("lost"); b.fill_on_accept = 3.42
    r1 = _enter(b, eng, _sig(X))
    rows = _rows(tlog, X)
    managed = [r for r in pm.get_open_records() if r.get("option_symbol") == X]
    _recon(b)
    check("S4 (b) lost reply, FILLED: booked under its strategy in the same call (ONE row, 1 @ 3.42, order O1), "
          "managed; the next adopt slot adopts nothing",
          r1 is None and len(rows) == 1 and _is_runaway_row(rows[0], 1, 3.42, "O1") and len(managed) == 1
          and not pages.adopted and len(_rows(tlog)) == 1 and b.position(X) == 1,
          f"rows={[_held(r) for r in _rows(tlog)]} managed={len(managed)} adopted={len(pages.adopted)} "
          f"broker={b.positions()}")

    # S5 — (c) FILLED, fills unreadable; adopt defers; then booked under its strategy
    tlog, pm, pages, eng = _fresh()
    b = Broker(); b.fill_on_accept = 3.44; b.hide_fill_reads = 100
    r1 = _enter(b, eng, _sig(X))
    r2 = _enter(b, eng, _sig(Y, 601.0))
    calls_blocked = b.place_calls
    _recon(b)
    adopted_while = [r for r in _rows(tlog) if r.get("strategy") == "ADOPTED"]
    b.hide_fill_reads = 0
    _tick(b)
    _recon(b)
    rows = _rows(tlog, X)
    check("S5 (c) FILLED, fills unreadable: the re-pick is refused, the adopt slot DEFERS (no ADOPTED row); once the "
          "fills read, the tick books ONE row under RunawayContinuation (1 @ 3.44); adopt then adopts nothing",
          r1 is None and r2 is None and calls_blocked == 1 and not adopted_while and len(rows) == 1
          and _is_runaway_row(rows[0], 1, 3.44, "O1") and len(_rows(tlog)) == 1 and not pages.adopted,
          f"calls_while_blocked={calls_blocked} adopted_while={len(adopted_while)} rows={[_held(r) for r in _rows(tlog)]}"
          f" adopted_pages={len(pages.adopted)}")

    # S6 — I3: partial + unconfirmed cancel
    tlog, pm, pages, eng = _fresh()
    b = Broker(); b.partial_on_accept = (1, 3.41); b.cancel_mode = "raise"
    details = []
    _real_confirm = EN.confirm_order_fill

    def _spy(*a, **k):
        f = _real_confirm(*a, **k)
        details.append(str(f.detail))
        return f
    EN.confirm_order_fill = _spy
    try:
        r1 = _enter(b, eng, _sig(X), n=3)
    finally:
        EN.confirm_order_fill = _real_confirm
    r2 = _enter(b, eng, _sig(Y, 601.0))
    calls_blocked = b.place_calls
    none_yet = not _rows(tlog, X)
    b.cancel_mode = "ok"
    _saved = getattr(OG, "RECANCEL_EVERY_S", None)
    if _saved is not None:
        OG.RECANCEL_EVERY_S = 0.0
    try:
        _tick(b); _tick(b)
    finally:
        if _saved is not None:
            OG.RECANCEL_EVERY_S = _saved
    rows = _rows(tlog, X)
    with bind(b, EN, OG):
        ok_after, _w = OG.clear_to_post("probe", SimpleNamespace(fake=True), b)
    check("S6 I3 partial (1 of 3) + cancel unconfirmed: the detail names the PARTIAL, the re-pick is refused; once "
          "dead, ONE row of 1 contract @ 3.41 under RunawayContinuation; the block clears",
          r1 is None and r2 is None and calls_blocked == 1 and none_yet and any("PARTIAL 1" in d for d in details)
          and len(rows) == 1 and _is_runaway_row(rows[0], 1, 3.41, "O1") and b.position(X) == 1 and ok_after,
          f"details={details} calls={calls_blocked} rows={[_held(r) for r in _rows(tlog)]} broker={b.positions()} "
          f"clear_after={ok_after}")

    # S7 — bounded: never readable -> one give-up page, block stays, adopt takes it, guard clears on the ADOPTED row
    tlog, pm, pages, eng = _fresh()
    b = Broker(); b.fill_on_accept = 3.44; b.hide_fill_reads = 10 ** 6
    _enter(b, eng, _sig(X))
    _sv = getattr(OG, "RESOLVE_GIVEUP_S", None)
    if _sv is not None:
        OG.RESOLVE_GIVEUP_S = 0.0
    try:
        _tick(b); _tick(b); _tick(b)
        giveups = [t for t in GPAGES if "unresolved" in t]
        r2 = _enter(b, eng, _sig(Y, 601.0))
        calls_blocked = b.place_calls
        _recon(b)
        _tick(b)
        with bind(b, EN, OG):
            ok_after, w_after = OG.clear_to_post("probe", SimpleNamespace(fake=True), b)
    finally:
        if _sv is not None:
            OG.RESOLVE_GIVEUP_S = _sv
    on_x = _rows(tlog, X)
    check("S7 bounded: fills never readable -> ONE give-up page, entries stay blocked; adopt then adopts it and the "
          "guard clears on the ADOPTED row without booking (one row on the leg)",
          len(giveups) == 1 and r2 is None and calls_blocked == 1 and len(on_x) == 1
          and on_x[0].get("strategy") == "ADOPTED" and ok_after,
          f"giveup_pages={len(giveups)} calls_while_blocked={calls_blocked} rows={[_held(r) for r in on_x]} "
          f"clear_after={ok_after} ({w_after})")

    # S8 — an order already on a row is never booked twice
    tlog, pm, pages, eng = _fresh()
    b = Broker(); b.fill_on_accept = 3.43
    h = _enter(b, eng, _sig(X, 600.0, "LiquidityHunt"))                 # O1, booked by the normal path
    b.fill_on_accept = None
    b.script_place("lost", hidden_reads=1)
    _enter(b, eng, _sig(X))                                            # Runaway on the same OCC: O2, reply lost
    b.fill("O2", 3.45)
    _tick(b)
    on_x = _rows(tlog, X)
    by = sorted((r.get("strategy"), str(r.get("order_id"))) for r in on_x)
    check("S8 an order id already on a row is never booked twice: O1 (the Hunt's, booked) and O2 (the lost Runaway "
          "post, booked once by the guard) -> two rows, one per order",
          h is not None and by == [("LiquidityHunt", "O1"), ("RunawayContinuation", "O2")] and b.position(X) == 2,
          f"rows={by} broker={b.positions()}")

    # S9 — exits never blocked while a suspect holds entries
    tlog, pm, pages, eng = _fresh()
    tlog.log_entry(TL.make_record(trade_id="EXIT-0001", symbol="QQQ", strategy="RunawayContinuation",
                                  setup_type="fixture", option_side="call", contracts=1, entry_premium=1.00,
                                  total_cost=100.0, max_loss=100.0, stop_premium=0.5, option_symbol=W,
                                  paper_trade=0, expiry="2099-12-31"))
    b = Broker(); b.hold(W, +1, 1.00); b.cancel_mode = "raise"
    _enter(b, eng, _sig(X))                                            # leaves a suspect
    with bind(b, EN, OG):
        held, _w = OG.clear_to_post("probe", SimpleNamespace(fake=True), b)
    b.cancel_mode = "ok"
    b.fill_on_accept = 0.40
    pm.has_open_position()
    recw = [r for r in pm.get_open_records() if r.get("trade_id") == "EXIT-0001"]
    with bind(b, EN, OG, XE, PM):
        done = pm._execute_exit(recw[0], XE.ExitDecision(should_exit=True, exit_reason="stop_hit"), 0.40) \
            if recw else None
    with tlog._db() as conn:
        st = conn.execute("SELECT status FROM trades WHERE trade_id='EXIT-0001'").fetchone()
    check("S9 exits never blocked: with a suspect holding entries, a stop on an open row posts its close; flat; closed",
          held is False and done is True and b.position(W) == 0 and st and st[0] == "closed",
          f"entries_held={not held} done={done} broker={b.positions()} row={st[0] if st else None}")

    # S10 — paper untouched
    tlog, pm, pages, eng = _fresh()
    peng = EN.EntryEngine(paper_trading=True)
    peng._trade_logger = tlog

    class _NoBroker:
        def __getattr__(self, n):
            raise AssertionError(f"paper reached the broker ({n})")
    nb = _NoBroker()
    try:
        with bind(nb, EN, OG, M):
            prec = peng.enter(_sig(X), _sz(1))
            hook = M._resolve_entry_suspects(PAPER) if hasattr(M, "_resolve_entry_suspects") else []
        perr = ""
    except Exception as exc:                                           # noqa: BLE001
        prec, hook, perr = None, None, f"{type(exc).__name__}: {exc}"
    check("S10 paper untouched: books the mark 3.45 with a PAPER- id, no broker call, no suspect; the tick hook "
          "makes no broker call",
          prec is not None and str(prec.get("order_id", "")).startswith("PAPER-")
          and abs(float(prec.get("entry_premium") or 0) - 3.45) < 1e-9 and not OG._SUSPECT and hook == [] and not perr,
          f"rec={_held(prec)} suspects={list(OG._SUSPECT)} hook={hook} err={perr}")

    # S11 — restart
    tlog, pm, pages, eng = _fresh()
    b = Broker(); b.cancel_mode = "raise"
    _enter(b, eng, _sig(X))                                            # O1 live, cancel unconfirmed
    OG.reset(boot_clean=False)                                         # a restart: the memory is gone
    OG._page = lambda text: GPAGES.append(text)
    b.cancel_mode = "pending"
    _cc = OG.CANCEL_CONFIRM_S
    OG.CANCEL_CONFIRM_S = 0.0
    try:
        r_boot = _enter(b, eng, _sig(Y, 601.0))
        calls_boot = b.place_calls
        b.set_status("O1", "Cancelled")
        r_after = _enter(b, eng, _sig(Y, 601.0))                      # the sweep comes back clean: posts
    finally:
        OG.CANCEL_CONFIRM_S = _cc
    ok_a = r_boot is None and calls_boot == 1 and b.place_calls == 2
    # a fill made before the restart, never recorded -> boot reconcile adopts it once
    tlog, pm, pages, eng = _fresh()
    b = Broker(); b.fill_on_accept = 3.44; b.hide_fill_reads = 10 ** 6
    _enter(b, eng, _sig(X))
    OG.reset(boot_clean=False)
    with bind(b, EN, OG, M):
        OG.boot_sweep()
        live1 = M._reconcile_with_broker(LIVE, tlog.get_open_trades_live(), "restart", "QQQ")
        live2 = M._reconcile_with_broker(LIVE, tlog.get_open_trades_live(), "restart", "QQQ")
    ad = [r for r in _rows(tlog, X) if r.get("strategy") == "ADOPTED"]
    ok_b = len(ad) == 1 and len(_rows(tlog, X)) == 1 and len(live2) == 1
    # a fill BOOKED before the restart -> kept, nothing adopted
    tlog, pm, pages, eng = _fresh()
    b = Broker(); b.script_place("lost"); b.fill_on_accept = 3.42
    _enter(b, eng, _sig(X))
    OG.reset(boot_clean=False)
    with bind(b, EN, OG, M):
        OG.boot_sweep()
        live3 = M._reconcile_with_broker(LIVE, tlog.get_open_trades_live(), "restart", "QQQ")
    ok_c = (len(live3) == 1 and live3[0].get("strategy") == "RunawayContinuation"
            and not [r for r in _rows(tlog) if r.get("strategy") == "ADOPTED"])
    check("S11 restart: the boot sweep cancels the live order and blocks every entry until it reads dead; a fill made "
          "before the restart is adopted ONCE; a fill booked before the restart is kept (nothing adopted)",
          ok_a and ok_b and ok_c,
          f"a: boot_refused={r_boot is None} calls_boot={calls_boot} calls_after={b.place_calls if False else '-'}; "
          f"b: adopted={len(ad)} rows={len(_rows(tlog, X))}; c: kept={[_held(r) for r in live3]}")


def case_s12():
    tlog, pm, pages, eng = _fresh()
    b = Broker(); b.cancel_mode = "raise"
    _enter(b, eng, _sig(X))
    b.fill("O1", 3.43)
    r = _enter(b, eng, _sig(Y, 601.0))                                 # no tick in between: resolved inside this call
    rows = _rows(tlog)
    check("S12 the suspect resolves inside a re-pick's own clear_to_post: that call posts NOTHING; ONE row booked "
          "under RunawayContinuation and managed",
          r is None and b.place_calls == 1 and len(rows) == 1 and _is_runaway_row(rows[0], 1, 3.43, "O1")
          and len([x for x in pm.get_open_records() if x.get("option_symbol") == X]) == 1,
          f"r={r is not None} place_calls={b.place_calls} rows={[_held(x) for x in rows]}")


def _at(hh, mm, ss=0):
    import datetime as _dt
    from utils.time_utils import ET
    n = _dt.datetime.now(ET)
    return n.replace(hour=hh, minute=mm, second=ss, microsecond=0)


class _EodClock:
    """main.now_et, the flatten's time reads and the cross mode, all pinned to one ET instant."""

    def __init__(self):
        import utils.time_utils as TU
        import execution.limit_ladder as LL
        self.TU, self.LL = TU, LL
        self.saved = None

    def set(self, t):
        TU, LL = self.TU, self.LL
        if self.saved is None:
            self.saved = (M.now_et, TU.eod_close_due, LL.hard_close_order_mode, XE.hard_close_order_mode,
                          getattr(M, "get_chain_fetcher", None), getattr(M, "get_cache", None))
        M.now_et = lambda: t
        TU.eod_close_due = lambda *a, **k: (t.hour, t.minute) >= (15, 55)
        LL.hard_close_order_mode = lambda *a, **k: "market" if (t.hour, t.minute) >= (15, 55) else "limit"
        XE.hard_close_order_mode = LL.hard_close_order_mode
        M.get_chain_fetcher = lambda: SimpleNamespace(fetch_chain=lambda: None)
        M.get_cache = lambda: SimpleNamespace(get_price=lambda: 600.0)

    def restore(self):
        if self.saved is not None:
            (M.now_et, self.TU.eod_close_due, self.LL.hard_close_order_mode, XE.hard_close_order_mode,
             M.get_chain_fetcher, M.get_cache) = self.saved
            self.saved = None


def _eod_tick(b, pm, clock, t):
    """One live RTH tick at ET instant t: the suspect hook, the reconcile slot, the hard close."""
    clock.set(t)
    pm._fetch_current_premium = lambda record, chain=None: 0.30
    st = SimpleNamespace(paper_trading=False, last_reconcile_slot=None, hard_close_alerted=False)
    with bind(b, EN, OG, M, XE, PM):
        if hasattr(M, "_resolve_entry_suspects"):
            M._resolve_entry_suspects(st)
        M._intraday_reconcile(st, "QQQ")
        M.handle_hard_close(st)


def _closed_rows(tlog, sym):
    with tlog._db() as conn:
        return [tuple(r) for r in conn.execute(
            "SELECT strategy, status, contracts FROM trades WHERE option_symbol=?", (sym,)).fetchall()]


def case_eod():
    import utils.time_utils as TU
    clock = _EodClock()
    try:
        tlog, pm, pages, eng = _fresh()
        b = Broker(); b.fill_on_accept = 3.44; b.hide_fill_reads = 10 ** 6
        t0 = _at(11, 2, 0)
        clock.set(t0); TU.now_et = lambda: t0
        _enter(b, eng, _sig(X, 600.0, "PARK"))
        b.fill_on_accept = 0.30
        _eod_tick(b, pm, clock, _at(11, 2, 15))                       # inside the window + 120 s: held back
        held = [r for r in _rows(tlog) if r.get("strategy") == "ADOPTED"]
        t1 = _at(11, 5, 1)
        TU.now_et = lambda: t1
        _eod_tick(b, pm, clock, t1)                                     # past 11:03 + 120 s: given up, adopted
        adopted = [r for r in _rows(tlog) if r.get("strategy") == "ADOPTED"]
        t2 = _at(15, 55, 0)
        TU.now_et = lambda: t2
        _eod_tick(b, pm, clock, t2)
        _eod_tick(b, pm, clock, _at(15, 55, 15))
        rows = _closed_rows(tlog, X)
        check("S13 after the last entry window (PARK 11:03) + RESOLVE_GIVEUP_S an unresolved suspect is given up, the "
              "next slot ADOPTS its fill, and the 15:55 flatten closes it: flat, ONE row on the leg, closed",
              not held and len(adopted) == 1 and b.position(X) == 0 and rows == [("ADOPTED", "closed", 1)],
              f"held_back={not held} adopted={len(adopted)} broker={b.position(X)} rows={rows}")
    finally:
        clock.restore()


def main():
    try:
        cases()
        case_s12()
        case_eod()
    except Exception as exc:                                           # noqa: BLE001
        import traceback
        traceback.print_exc()
        check("RUN the gate ran to the end", False, f"{type(exc).__name__}: {exc}")
    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — no opening order beside one whose fate is unknown; the unknown is booked under its strategy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
