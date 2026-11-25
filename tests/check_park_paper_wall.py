#!/usr/bin/env python3
"""
tests/check_park_paper_wall.py  v5.0
v5.0  2026-11-26  OTV5 r161 (LANE.1) — new. ON A LIVE BOX `park = paper_only` PAPER-TRADES PARK BEHIND THE PAPER WALL, WITH
      ZERO BROKER CALLS, AND THE CASH PATH DOES NOT MOVE. The operator, 2026-11-25: "I want park paperwalled until we
      enable it on the cash side, which is potentially January, if ever"; "The cap on a live box is for live trades only.
      Full stop." (2026-11-22); "Be deliberate. We should be able to switch between paper & live anytime we are fielding
      a new strategy for a few weeks." tests/check_ogap_paper_on_live.py's approach, for PARK: a LIVE box
      (OT_PAPER_TRADING=False, so BROKER_RECONCILE_ENABLED and every live default hold) against a FAKE BROKER - every
      broker-facing function of data/tasty_client (get_session, get_account, get_client, the position reads, the session
      reset, the async runner, sdk_result) is replaced, in that module and every module that imported it by name, by a
      recorder; the fake account records every method called on it; order_guard.clear_to_post and
      buying_power.affordable are spied. The process's box flags are FROZEN to fixture files (never this box's real
      file) except W11, which reads the real deploy/box_flags/QQQ.

  W1  THE LANE: with `park = paper_only` PARK reads ACTIVE (asked), order_router.route("PARK") is PAPER on a live box
      and on a paper box, walled on the live box only, walled_setups(live) = (OGAP, PARK); the Service line says
      " · park=paper_only (walled on a live box)"; the [flags] start line keeps its shape (" · park=paper_only · ") and
      main._announce_box_flags logs ONE "[route] QQQ LIVE box: park=paper_only -> PAPER (walled on a live box)" line
  W2  A FULL PARK DAY ON A LIVE BOX, ZERO BROKER CALLS, three trades of the real Park strategy (11:01 fire, 1.58/1.62,
      the mark 1.60) through main._execute_entry_signal: each books paper_trade = 1, order id PAPER-*, on
      paper_wall.book() and never the live PositionManager; no freeze walk, no suspect hand-off, no clear_to_post, no
      buying-power read, no cap counterfactual row, no record_win / record_loss; exits in the wall's paper ExitEngine at
      the mark: (a) park_lock (armed at 2.70, out at 1.90), (b) park_delta_floor (|delta| 0.25 at 11:30), (c) a
      RESTART mid-position (the singletons dropped, paper_wall.recover() resumes it) then park_close 15:45 at the mark
      (15:41 still open); PAPER alerts; the fake broker saw NO call from the first entry to the last close
  W3  RECONCILE, RESTART, STARTUP CANCEL: with a PARK paper row OPEN, main._recover_open_position (the boot reconcile,
      BROKER_RECONCILE_ENABLED, the boot order sweep), main._intraday_reconcile and order_guard.sweep_working make the
      same broker calls and decisions as with none (digest); the live manager never holds it; recover() resumes it (an
      expired one closed, flagged)
  W4  THE CAP IS FOR LIVE TRADES ONLY: a closed PARK paper loss of -$99,999 leaves day_realized_pnl 0.00 and is_halted
      False; a cash Runaway loss of -$650 halts; at that tripped cash cap attempt_new_entry at 11:01 asks no cash setup
      (Runaway refused at catastrophic_cap) but still asks the walled PARK (no catastrophic_cap row for it), which books
      paper on the wall with zero broker calls
  W5  CASH UNAFFECTED (digest CASH_DIGEST, measured on r160 2a8c5da): a cash Runaway entry (real _execute_entry_signal, a
      live spy engine booking through EntryEngine._book_fill) and exit (the real live PositionManager with a fake live
      exit engine) give the same sizing, rows, tally, cap and broker log with a walled PARK position open (and a -$99,999
      PARK paper loss) as with none; the live-box dispatch 09:35-11:05 asks and skips Runaway byte-identically with PARK
      flat and with PARK open on the wall
  W6  THE HELD PAGE (dtp tools/held_contracts_page.build_page, when ~/day_trader_pro is present): the PARK paper row
      lists under paper and is not in the desk message; the Runaway cash row is LIVE
  W7  A PAPER BOX: `park = paper_only` is `park = on` byte for byte (the W2(c) day through the box's own paper engines:
      rows, alerts, tally, the broker log - the paper hard close's spot reads - digest equal, run on / paper_only / on
      so both compared runs are warm) and builds no wall
  W8  `park = off` STILL DORMANT: never asked (main._attempt_park at 11:01 calls no generate_signal), route DORMANT, and a
      PARK signal handed to _execute_entry_signal anyway is refused (no row, no broker call)
  W9  AN OPEN POSITION FINISHES IN THE LANE IT OPENED IN: a walled PARK row open when the flag then reads `on` is still
      resumed by recover() on the wall (the live logger never sees it), route_close PAPER, and closes paper with zero
      broker calls; a LIVE PARK row (paper_trade 0) open when the flag reads paper_only is never taken by the wall
      (recover() 0, route_close LIVE) and the live logger holds it
  W10 THE PAPER PATH HOLDS NO BROKER OBJECT: after W2, nothing reachable from paper_wall.book() / entry_engine() (four
      levels of attributes) is the fake account or session; paper_wall.py and order_router.py import no broker client;
      main_loop runs _paper_wall_pass after its last attempt_new_entry and _paper_wall_close_pass after
      handle_hard_close, main() runs paper_wall.recover after _recover_open_position
  W11 THE REAL FILE: deploy/box_flags/QQQ reads park = paper_only with nothing refused; SPX has no file (defaults)
Born red on r160 (2a8c5da): paper_only is refused (reads off) there, so W1, W2, W4, W7 and W9 fail and W11 reads off.
Revert mutants (each wall removed in turn) red: see the land spec (LANE.1).
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
Run:  python3 tests/check_park_paper_wall.py
"""
import hashlib
import json
import logging
import os
import sqlite3
import sys
import tempfile
import types
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["OT_INSTRUMENT"] = "QQQ"
_TD = tempfile.mkdtemp(prefix="check_park_paper_wall_")
FEED = os.path.join(_TD, "f.db")
for _k, _f in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"),
               ("OT_LOG_FILE", "bot.log"), ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_COUNTERFACTUAL_DIR", "cf"),
               ("OT_ALERT_SPOOL", "alert_spool.jsonl"), ("OT_PLAN_STATES_FILE", "plan_states.json"),
               ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT"), ("OT_WAREHOUSE_STATE", "ws")):
    os.environ[_k] = os.path.join(_TD, _f)
for _k in ("OT_DAILY_LOSS_LIMIT", "OT_BROKER_RECONCILE", "OT_PARK", "OT_RUNAWAY"):
    os.environ.pop(_k, None)
os.environ["OT_PAPER_TRADING"] = "False"     # A LIVE BOX
os.environ["OT_RISK_USD"] = "500"
ET = ZoneInfo("America/New_York")
DAY, PREV = date(2026, 11, 20), date(2026, 11, 19)
D = DAY.isoformat()
CASH_DIGEST = "6bfc457bf3e7a0c2"                   # W5: measured on r160 2a8c5da with this harness (no wall, no PARK row)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def dg(obj) -> str:
    return hashlib.sha256(json.dumps(obj, default=str, sort_keys=True).encode()).hexdigest()[:16]


def _ms(d, h, m):
    return int(datetime(d.year, d.month, d.day, h, m, tzinfo=ET).timestamp() * 1000)


def _feed(o930=700.0, c1030=702.1, c1100=702.4, prev_close=699.0):
    """check_park's candle fixture: +0.30% first hour on a gap up -> PARK fires a CALL at 11:01."""
    c = sqlite3.connect(FEED)
    c.execute("CREATE TABLE IF NOT EXISTS candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, ts_epoch_ms INTEGER "
              "NOT NULL, open REAL, high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY (symbol, interval, "
              "ts_epoch_ms))")
    c.execute("DELETE FROM candles")
    c.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", [
        ("QQQ", "1m", _ms(DAY, 9, 30), o930, o930 + .1, o930 - .1, o930 + .05, 1),
        ("QQQ", "1m", _ms(DAY, 10, 30), c1030, c1030 + .1, c1030 - .1, c1030, 1),
        ("QQQ", "1m", _ms(DAY, 11, 0), c1100, c1100 + .1, c1100 - .1, c1100, 1),
        ("QQQ", "1m", _ms(PREV, 15, 59), 1, 1, 1, prev_close, 1)])
    c.commit()
    c.close()


class K:
    def __init__(self, strike, bid, ask, expiry, side, delta=None):
        self.strike, self.bid, self.ask, self.expiry = strike, bid, ask, expiry
        self.mark = round((bid + ask) / 2, 2)
        self.delta = delta if delta is not None else (0.5 if side == "C" else -0.5)
        self.iv, self.theta = 0.2, -0.05
        self.option_type = side
        self.symbol = f"QQQ   {expiry.replace('-', '')[2:]}{side}{int(strike * 1000):08d}"
        self.streamer_symbol = self.symbol


class Chain:
    def __init__(self, expiry, lo, hi, bid, ask, delta=None):
        self.expiry = expiry
        self.calls = [K(float(s), bid, ask, expiry, "C", delta) for s in range(lo, hi + 1)]
        self.puts = [K(float(s), bid, ask, expiry, "P", None if delta is None else -delta) for s in range(lo, hi + 1)]
        self.spot_price = self.spot = 702.4
        self.atm_iv = 0.2


# ── THE FAKE BROKER (check_ogap_paper_on_live's) ─────────────────────────────────────────────────────────────────────
CALLS = []


class FakeAccount:
    RESP = {}

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def call(*a, **kw):
            CALLS.append(("account." + name, len(a)))
            r = FakeAccount.RESP.get(name, [])
            return r(*a, **kw) if callable(r) else r
        return call


_FAKES = {}
FAKE_OBJS = []


def install_fake_broker():
    import data.tasty_client as TC
    acct, sess = FakeAccount(), types.SimpleNamespace(name="fake-session")
    FAKE_OBJS.extend([acct, sess])
    beh = {
        "get_session": lambda *a, **k: sess,
        "_create_session": lambda *a, **k: sess,
        "get_account": lambda *a, **k: acct,
        "get_client": lambda *a, **k: acct,
        "get_open_option_positions": lambda *a, **k: list(FakeAccount.RESP.get("_positions", [])),
        "get_open_equity_positions": lambda *a, **k: [],
        "reset_session": lambda *a, **k: None,
        "run_async": lambda coro, *a, **k: coro,
        "get_loop": lambda *a, **k: None,
        "sdk_result": lambda x: x,
    }
    for name, fn in beh.items():
        orig = getattr(TC, name)

        def rec(*a, _n=name, _f=fn, **kw):
            CALLS.append(("tasty_client." + _n, len(a)))
            return _f(*a, **kw)
        _FAKES[name] = (orig, rec)
    repatch()


def repatch():
    for name, (orig, rec) in _FAKES.items():
        for m in list(sys.modules.values()):
            try:
                if m is not None and getattr(m, name, None) is orig:
                    setattr(m, name, rec)
            except Exception:                                   # noqa: BLE001
                pass


def main():
    print("check_park_paper_wall")
    try:
        import pandas  # noqa: F401
        import config
        install_fake_broker()
        import main as MN
        repatch()
        import utils.time_utils as TU
        import database.trade_logger as TL
        import execution.position_manager as PMM
        import execution.exit_engine as EE
        import execution.entry_engine as ENE
        import risk.risk_manager as RM
        from execution import order_guard as OG
        from execution import buying_power as BP
        from strategy import plan_state as PS
        from strategy.park import Park
        from strategy.base_strategy import OptionsSignal
        from analysis.orb_engine import get_orb_engine
        from utils import box_flags as BF
        import strategy.management as MG
        repatch()
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN: imports failed ({type(exc).__name__}: {exc})")
        return 2
    PW = getattr(MN, "_paper_wall", None)
    RT = getattr(MN, "_router", None)
    for _h in logging.getLogger().handlers:
        if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
            _h.setLevel(logging.CRITICAL + 1)
    if config.PAPER_TRADING is not False:
        print("NOT RUN: the interpreter is not a live box (config.PAPER_TRADING is not False)")
        return 2
    EE.get_exit_engine()                       # the singleton, built LIVE (as on a live box at start)

    FL = tempfile.mkdtemp(prefix="flags_", dir=_TD)

    def flags(text):
        """freeze the process's box flags to a fixture file holding `text` (None: no file, the defaults)."""
        p = os.path.join(FL, "QQQ_%d" % len(os.listdir(FL)))
        if text is not None:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
        BF.reset()
        BF._EFFECTIVE["flags"] = BF.load("QQQ", path=p)
        return BF._EFFECTIVE["flags"]

    real = {"now_et": TU.now_et, "now_utc": TU.now_utc}

    def pin(dt):
        fake = {"now_et": lambda: dt, "now_utc": lambda: dt.astimezone(timezone.utc)}
        sw = [(m, n) for m in list(sys.modules.values()) for n in real
              if m is not None and getattr(m, n, None) is real[n]]
        for m, n in sw:
            setattr(m, n, fake[n])

        class _FDT(datetime):
            @classmethod
            def now(cls, tz=None):
                return dt.astimezone(tz) if tz is not None else dt.replace(tzinfo=None)
        dts = [m for m in (EE, PMM, MG, MN) if getattr(m, "datetime", None) is datetime]
        for m in dts:
            m.datetime = _FDT
        return sw, dts

    def unpin(sw):
        sw, dts = sw
        for m, n in sw:
            setattr(m, n, real[n])
        for m in dts:
            m.datetime = datetime

    ALERTS = []

    class _Alerts:
        def __getattr__(self, name):
            if name.startswith("__"):
                raise AttributeError(name)

            def f(*a, **kw):
                ALERTS.append((name, a, kw))
            return f

        def send_entry_alert(self, record):
            ALERTS.append(("entry", "PAPER" if record.get("paper_trade") else "LIVE", record.get("strategy")))

        def send_exit_alert(self, **kw):
            ALERTS.append(("exit", kw.get("setup_type"), round(float(kw.get("pnl_usd") or 0), 2), kw.get("reason")))

    _al = _Alerts()
    for mod in (MN, PMM):
        mod.get_alert_manager = lambda *a, **k: _al
    import notifications.alert_manager as AM
    AM.get_alert_manager = lambda *a, **k: _al

    SPY = []
    s_ctp, s_aff = OG.clear_to_post, BP.affordable

    def _ctp(*a, **k):
        SPY.append("order_guard.clear_to_post")
        return s_ctp(*a, **k)

    def _aff(*a, **k):
        SPY.append("buying_power.affordable")
        return s_aff(*a, **k)
    OG.clear_to_post, BP.affordable = _ctp, _aff
    for m in list(sys.modules.values()):
        try:
            if m is not None and getattr(m, "clear_to_post", None) is s_ctp:
                m.clear_to_post = _ctp
            if m is not None and getattr(m, "affordable", None) is s_aff:
                m.affordable = _aff
        except Exception:                                       # noqa: BLE001
            pass

    def fresh(tag, paper_box=False):
        p = os.path.join(_TD, "trades_%s.db" % tag)
        for x in (p, p + "-wal", p + "-shm"):
            if os.path.exists(x):
                os.remove(x)
        TL._trade_logger = TL.TradeLogger(db_path=p, paper_trading=paper_box)
        if PW is not None:
            PW.reset()
        RM._risk_manager = None
        MN._observe.clear()
        MN._set_admission(None)
        return p

    def rows(p, where="1=1"):
        c = sqlite3.connect(p)
        c.row_factory = sqlite3.Row
        out = [dict(r) for r in c.execute("SELECT * FROM trades WHERE %s ORDER BY entry_time" % where)]
        c.close()
        return out

    class _MS:
        adx, trend_direction, structure_sequence = 20.0, "NEUTRAL", ""

    def live_state():
        st = MN.BotState()
        st.paper_trading = False
        return st

    TALLY = []

    class _RiskSpy:
        def __init__(self, real_rm):
            self._r = real_rm

        def record_win(self, p):
            TALLY.append(("win", round(p, 2)))

        def record_loss(self, p):
            TALLY.append(("loss", round(p, 2)))

        def __getattr__(self, n):
            return getattr(self._r, n)

    s_pm_grm = PMM.get_risk_manager
    PMM.get_risk_manager = lambda *a, **k: _RiskSpy(RM.get_risk_manager())

    _feed()
    eng = get_orb_engine()
    eng.data.orb_high, eng.data.orb_low = 703.0, 701.0
    fire_dt = datetime(2026, 11, 20, 11, 1, 5, tzinfo=ET)

    def park_signal():
        sw = pin(fire_dt)
        try:
            return Park().generate_signal(price_now=702.4, now_et="11:01", chain=Chain(D, 700, 705, 1.58, 1.62),
                                          prior_close=699.0, day=DAY, symbol="QQQ")
        finally:
            unpin(sw)

    def mchain(mark, delta=None):
        return Chain(D, 700, 705, round(mark - 0.02, 2), round(mark + 0.02, 2), delta)

    PAPER_ONLY = "park = paper_only  # fixture\n"
    flags(PAPER_ONLY)

    # ── W1 the lane ─────────────────────────────────────────────────────────
    ok1, d1 = False, ""
    try:
        b_live = MN._banner_dials()
        s_pt = MN.PAPER_TRADING
        MN.PAPER_TRADING = True
        try:
            b_paper = MN._banner_dials()
        finally:
            MN.PAPER_TRADING = s_pt
        line = BF.start_line(BF.effective(), "c")
        caps = []

        class _Cap(logging.Handler):
            def emit(self, r):
                caps.append(r.getMessage())
        _h = _Cap(logging.DEBUG)
        MN.logger.addHandler(_h)
        s_am = MN.get_alert_manager
        MN.get_alert_manager = lambda *a, **k: types.SimpleNamespace(_send=lambda *a, **k: True)
        try:
            MN._announce_box_flags()
        finally:
            MN.logger.removeHandler(_h)
            MN.get_alert_manager = s_am
        route_lines = [c for c in caps if c.startswith("[route]")]
        ok1 = (RT is not None and PS.state("PARK") == PS.ACTIVE and RT.route("PARK", False) == RT.PAPER
               and RT.route("PARK", True) == RT.PAPER and RT.walled("PARK", False) and not RT.walled("PARK", True)
               and RT.walled_setups(False) == ("OGAP", "PARK") and RT.walled_setups(True) == ()
               and RT.route("RunawayContinuation", False) == RT.LIVE
               and " · park=paper_only (walled on a live box)" in b_live
               and " · park=paper_only · " in line
               and route_lines == ["[route] QQQ LIVE box: park=paper_only -> PAPER (walled on a live box) "
                                   "(execution/order_router; docs/ROUTING.md)"])
        d1 = f"state={PS.state('PARK')} live={b_live[-120:]} line={line[-160:]} route={route_lines}"
    except Exception as exc:                                    # noqa: BLE001
        d1 = f"{type(exc).__name__}: {exc}"
    check("W1 park = paper_only: PARK asked, routed PAPER (walled on the live box only), named on the Service and [flags] "
          "lines", ok1, d1)

    # ── W2 the full PARK day ────────────────────────────────────────────────
    def manage_at(st, hh, mm, chain):
        sw = pin(datetime(2026, 11, 20, hh, mm, 5, tzinfo=ET))
        try:
            MN._paper_wall_pass({"chain": chain, "price": 702.4, "df_1m": None, "df_5m": None}, st)
        finally:
            unpin(sw)

    def close_at(st, hh, mm, chain):
        sw = pin(datetime(2026, 11, 20, hh, mm, 5, tzinfo=ET))
        s_fc = MN.get_chain_fetcher
        MN.get_chain_fetcher = lambda: types.SimpleNamespace(fetch_chain=lambda: chain)
        try:
            MN.handle_hard_close(st)
            MN._paper_wall_close_pass(st, None)
        finally:
            MN.get_chain_fetcher = s_fc
            unpin(sw)

    def enter(st):
        sig = park_signal()
        sw = pin(fire_dt)
        try:
            MN._execute_entry_signal(sig, {"price": 702.4, "macro": {}, "chain": Chain(D, 700, 705, 1.58, 1.62)},
                                     None, st, None, additive=True)
        finally:
            unpin(sw)
        return sig

    def park_day(kind, st, restart=False):
        p = TL._trade_logger.db_path
        enter(st)
        notes = {}
        if kind == "lock":
            manage_at(st, 11, 10, mchain(2.70))
            manage_at(st, 11, 20, mchain(1.90))
        elif kind == "delta":
            manage_at(st, 11, 10, mchain(1.70))
            manage_at(st, 11, 30, mchain(1.20, delta=0.25))
        else:
            manage_at(st, 11, 10, mchain(1.70))
            if restart:
                PW.reset()                               # the process restarts: the singletons are gone
                sw = pin(datetime(2026, 11, 20, 12, 0, 0, tzinfo=ET))
                try:
                    notes["resumed"] = PW.recover()
                finally:
                    unpin(sw)
            manage_at(st, 14, 30, mchain(1.80))
            close_at(st, 15, 41, mchain(1.75))
            notes["open_1541"] = len(rows(p, "status='open'"))
            close_at(st, 15, 45, mchain(1.75))
        notes["open_end"] = len(rows(p, "status='open'"))
        return notes

    ok2, d2 = False, ""
    W2 = {}
    try:
        frz, hand = [], []
        s_fz, s_hb = MN._freeze_contract, MN._hand_booked_to_manager
        MN._freeze_contract = lambda s, paper: frz.append(paper) or False
        MN._hand_booked_to_manager = lambda s: hand.append(1) or []
        try:
            for kind in ("lock", "delta", "close"):
                p = fresh("w2_" + kind)
                st = live_state()
                live_pm = PMM.get_position_manager(False)
                live_pm._open_records = []
                CALLS.clear()
                SPY.clear()
                ALERTS.clear()
                TALLY.clear()
                cfp = RM.cap_cf_path()
                cf0 = len(open(cfp).read().splitlines()) if os.path.exists(cfp) else 0
                notes = park_day(kind, st, restart=(kind == "close"))
                cfl = open(cfp).read().splitlines() if os.path.exists(cfp) else []
                rw = rows(p)
                r0 = rw[0] if rw else {}
                W2[kind] = {"notes": notes, "n": len(rw),
                            "row": {k: r0.get(k) for k in ("strategy", "paper_trade", "order_id", "entry_premium",
                                                          "contracts", "status", "exit_reason", "exit_premium",
                                                          "pnl_usd")},
                            "live": len(live_pm.get_open_records()), "calls": list(CALLS), "spy": list(SPY),
                            "tally": list(TALLY), "cf_park": [x for x in cfl[cf0:] if '"PARK"' in x],
                            "alerts": [a for a in ALERTS if a[0] in ("entry", "exit")]}
        finally:
            MN._freeze_contract, MN._hand_booked_to_manager = s_fz, s_hb
        want = {"lock": ("park_lock", 1.90), "delta": ("park_delta_floor", 1.20), "close": ("park_close_15:45", 1.75)}
        good = {}
        for kind, w in W2.items():
            r = w["row"]
            n = int(r.get("contracts") or 0)
            good[kind] = (w["n"] == 1 and r["strategy"] == "PARK" and r["paper_trade"] == 1
                          and str(r["order_id"] or "").startswith("PAPER-") and r["entry_premium"] == 1.60 and n >= 1
                          and r["status"] == "closed" and str(r["exit_reason"] or "").startswith(want[kind][0])
                          and r["exit_premium"] == want[kind][1]
                          and round(float(r["pnl_usd"] or 0), 2) == round((want[kind][1] - 1.60) * 100 * n, 2)
                          and w["live"] == 0 and w["calls"] == [] and w["spy"] == [] and w["tally"] == []
                          and w["cf_park"] == [] and ("entry", "PAPER", "PARK") in w["alerts"]
                          and any(a[0] == "exit" and str(a[1]).startswith("PAPER ") for a in w["alerts"]))
        ok2 = (all(good.values()) and len(good) == 3 and frz == [True, True, True] and not hand
               and W2["close"]["notes"].get("resumed") == 1 and W2["close"]["notes"].get("open_1541") == 1)
        d2 = f"good={good} freeze={frz} hand={hand} days={W2}"
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d2 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-900:]}"
    check("W2 a full PARK day on a LIVE box books paper on the wall (11:01 entry at the mark; park_lock, the delta floor, "
          "a restart -> recover() -> the 15:45 close) with ZERO broker calls, no order guard, no buying power, no cash "
          "tally, no cap counterfactual, PAPER alerts", ok2, d2)

    def open_walled(tid="park-open", expiry=D, paper=1):
        from database.trade_logger import make_record
        rec = make_record(trade_id=tid, strategy="PARK", setup_type="park_long", direction="long", option_side="call",
                          strike=702.0, expiry=expiry, contracts=3, entry_premium=1.60, total_cost=480.0,
                          max_loss=480.0, stop_premium=0.0, underlying_entry=702.4,
                          option_symbol=K(702.0, 1, 1, expiry, "C").symbol,
                          order_id="PAPER-X" if paper else "LIVE-X", paper_trade=paper, symbol="QQQ", status="open")
        TL._trade_logger.log_entry(rec)
        return rec

    def closed_walled_loss(tid="park-loss", pnl=-99999.0):
        open_walled(tid)
        TL._trade_logger.log_exit(trade_id=tid, exit_price=0.01, pnl_usd=pnl, exit_reason="park_test")

    # ── W3 reconcile / restart / startup cancel ─────────────────────────────
    ok3, d3 = False, ""
    try:
        def boot(with_park):
            fresh("w3_%s" % with_park)
            if with_park:
                open_walled()
                open_walled("park-expired", expiry="2026-11-19")
            st = live_state()
            pm = PMM.PositionManager(False)
            s_gpm = MN.get_position_manager
            MN.get_position_manager = lambda *a, **k: pm
            CALLS.clear()
            ALERTS.clear()
            FakeAccount.RESP = {"_positions": []}
            sw = pin(datetime(2026, 11, 20, 9, 20, 0, tzinfo=ET))
            try:
                MN._recover_open_position(st, "service restart")
                boot_calls = list(CALLS)
                CALLS.clear()
                MN._intraday_reconcile(st, "QQQ")
                intra_calls = list(CALLS)
                resumed = PW.recover() if with_park else 0
            finally:
                unpin(sw)
                MN.get_position_manager = s_gpm
            rw = {r["trade_id"]: (r["status"], r["paper_trade"], r["exit_reason"]) for r in rows(TL._trade_logger.db_path)}
            return boot_calls, intra_calls, len(pm.get_open_records()), rw, [a[0] for a in ALERTS], resumed

        b0, b1 = boot(False), boot(True)
        book_ids = [r.get("trade_id") for r in PW.book().get_open_records()]

        def sweep(with_park):
            fresh("w3s_%s" % with_park)
            if with_park:
                open_walled()
            CALLS.clear()
            wo = types.SimpleNamespace(id="W1", status=types.SimpleNamespace(value="Live"), underlying_symbol="QQQ",
                                       legs=[])
            FakeAccount.RESP = {"get_live_orders": [wo],
                                "get_order": lambda *a, **k: types.SimpleNamespace(
                                    status=types.SimpleNamespace(value="Cancelled"))}
            OG.reset()
            res = OG.sweep_working(types.SimpleNamespace(), FakeAccount(), "QQQ")
            return res, sorted(OG._kept_order_ids()), list(CALLS)
        s0, s1 = sweep(False), sweep(True)
        FakeAccount.RESP = {}
        ok3 = (b0[0] == b1[0] and b0[1] == b1[1] and b0[2] == b1[2] == 0 and b0[4] == b1[4] and len(b0[0]) > 0
               and b1[3].get("park-open") == ("open", 1, None)
               and (b1[3].get("park-expired") or ("?",))[0] == "closed" and b1[5] == 1 and book_ids == ["park-open"]
               and s0 == s1 and s0[0][0] is True and s0[0][1] == 1)
        d3 = f"flat={b0[:3]} | park={b1[:3]} rows={b1[3]} resumed={b1[5]} book={book_ids} sweep={s0} / {s1}"
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d3 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-900:]}"
    check("W3 the boot reconcile, the intraday reconcile and the startup cancel make the same broker calls and decisions "
          "with a PARK paper row open and never touch it; recover() resumes it (an expired one closed)", ok3, d3)

    # ── W4 the cap ──────────────────────────────────────────────────────────
    ok4, d4 = False, ""
    try:
        from database.trade_logger import make_record
        res = {}
        sw0 = pin(fire_dt)
        try:
            fresh("w4a")
            closed_walled_loss()
            rm = RM.RiskManager(paper_trading=False)
            res["park_paper_loss"] = (round(rm.day_realized_pnl(), 2), rm.is_halted())
            p = fresh("w4b")
            cash = make_record(trade_id="run-loss", strategy="RunawayContinuation", setup_type="runaway_long",
                               direction="long", option_side="call", strike=702.0, expiry=D, contracts=1,
                               entry_premium=7.0, total_cost=700.0, paper_trade=0, symbol="QQQ", status="open")
            TL._trade_logger.log_entry(cash)
            TL._trade_logger.log_exit(trade_id="run-loss", exit_price=0.5, pnl_usd=-650.0, exit_reason="t")
            RM._risk_manager = RM.RiskManager(paper_trading=False)
            res["cash_loss"] = (round(RM._risk_manager.day_realized_pnl(), 2), RM._risk_manager.is_halted())
            st = live_state()
            asked, skips, saved = [], [], {}
            sig = park_signal()
            for attr, nm in (("_runaway_strategy", "RunawayContinuation"), ("_park_strategy", "PARK")):
                obj = getattr(MN, attr)
                saved[attr] = obj.generate_signal

                def fn(_nm=nm, **kw):
                    asked.append(_nm)
                    return sig if _nm == "PARK" else None
                obj.generate_signal = fn
            s_skip = MN._plan_skip
            MN._plan_skip = lambda n, reason, gate="": skips.append((n, gate)) or s_skip(n, reason, gate)
            s_gpm = MN.get_position_manager
            pm = PMM.PositionManager(False)
            MN.get_position_manager = lambda *a, **k: pm
            CALLS.clear()
            SPY.clear()
            try:
                MN.attempt_new_entry({"price": 702.4, "chain": Chain(D, 700, 705, 1.58, 1.62), "macro": {},
                                      "symbol": "QQQ", "gap": {"prior_close": 699.0}}, _MS(), st)
            finally:
                for attr, f in saved.items():
                    getattr(MN, attr).generate_signal = f
                MN._plan_skip = s_skip
                MN.get_position_manager = s_gpm
            pk = rows(p, "strategy='PARK'")
            res["at_cap"] = {"halted": RM._risk_manager.is_halted(), "asked": sorted(set(asked)),
                             "park_gates": sorted(set(g for n, g in skips if n == "PARK")),
                             "run_gates": sorted(set(g for n, g in skips if n == "RunawayContinuation")),
                             "park_rows": [(r["status"], r["paper_trade"]) for r in pk],
                             "book": len(PW.book().get_open_records()), "live": len(pm.get_open_records()),
                             "calls": list(CALLS), "spy": list(SPY)}
        finally:
            unpin(sw0)
        ac = res["at_cap"]
        ok4 = (res["park_paper_loss"] == (0.0, False) and res["cash_loss"] == (-650.0, True)
               and ac["halted"] is True and ac["asked"] == ["PARK"] and "catastrophic_cap" not in ac["park_gates"]
               and "catastrophic_cap" in ac["run_gates"] and ac["park_rows"] == [("open", 1)] and ac["book"] == 1
               and ac["live"] == 0 and ac["calls"] == [] and ac["spy"] == [])
        d4 = f"{res}"
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d4 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-900:]}"
    check("W4 the cap on a LIVE box is for live trades only: a PARK paper loss never moves it; at a tripped cash cap "
          "Runaway is refused and the walled PARK is still asked and books paper, zero broker calls", ok4, d4)

    # ── W5 cash unaffected ──────────────────────────────────────────────────
    ok5, d5 = False, ""
    try:
        from execution.exit_engine import FillResult, ExitDecision

        class _LiveSpy:
            def __init__(self):
                self.calls = []
                self.eng = ENE.EntryEngine(False)

            def enter(self, signal=None, sizing=None, **kw):
                self.calls.append((signal.strategy_name, sizing.contracts, round(sizing.total_cost, 2)))
                return self.eng._book_fill(signal, float(signal.entry_premium), "LIVE-1", sizing.contracts,
                                           sizing.contracts)

        class _FakeLiveExit:
            paper_trading = False

            def __init__(self):
                self.calls = []

            def evaluate(self, record, prem, **kw):
                return ExitDecision(should_exit=True, exit_reason="test_exit")

            def place_exit_order(self, record, reason, mark_price=None):
                self.calls.append((record.get("strategy"), reason, mark_price))
                return FillResult(confirmed=True, fill_price=float(mark_price))

            def started_close(self, record):
                return None

            def clear_trail(self, tid):
                pass

            def __getattr__(self, n):
                if n.startswith("__"):
                    raise AttributeError(n)
                return lambda *a, **k: None

        def cash_world(with_park):
            p = fresh("w5_%s" % with_park)
            if with_park and PW is not None:
                closed_walled_loss()
                PW.book().set_open_positions([open_walled()])
            st = live_state()
            pm = PMM.PositionManager(False)
            s_gpm, s_gee = MN.get_position_manager, MN.get_entry_engine
            spy, fx_exit = _LiveSpy(), _FakeLiveExit()
            MN.get_position_manager = lambda *a, **k: pm
            MN.get_entry_engine = lambda *a, **k: spy
            s_pme = PMM.get_exit_engine
            PMM.get_exit_engine = lambda *a, **k: fx_exit
            CALLS.clear()
            TALLY.clear()
            sw = pin(datetime(2026, 11, 20, 10, 0, 5, tzinfo=ET))
            try:
                sg = OptionsSignal(strategy_name="RunawayContinuation", setup_type="runaway_long", direction="long",
                                   option_side="call", underlying_entry=702.4, underlying_stop=0.0, strike=702.0,
                                   entry_premium=1.45, stop_loss_pct=1.0)
                sg.contract = K(702.0, 1.44, 1.46, D, "C")
                MN._execute_entry_signal(sg, {"price": 702.4, "macro": {}}, None, st, None, additive=True)
                after_entry = [(r.get("strategy"), r.get("contracts"), r.get("entry_premium"))
                               for r in pm.get_open_records()]
                pm.manage_open_position(chain=Chain(D, 700, 705, 1.79, 1.81), df_1m=None)
            finally:
                unpin(sw)
                MN.get_position_manager, MN.get_entry_engine = s_gpm, s_gee
                PMM.get_exit_engine = s_pme
            cash = [(r["strategy"], r["status"], r["contracts"], r["entry_premium"], r["exit_premium"],
                     round(float(r["pnl_usd"] or 0), 2), r["exit_reason"], r["paper_trade"])
                    for r in rows(p, "paper_trade=0")]
            rm = RM.RiskManager(paper_trading=False)
            return {"sized": spy.calls, "after_entry": after_entry, "open_after": len(pm.get_open_records()),
                    "exits": fx_exit.calls, "cash_rows": cash, "tally": list(TALLY),
                    "cap": (round(rm.day_realized_pnl(), 2), rm.is_halted()), "broker": list(CALLS)}
        c0, c1 = cash_world(False), cash_world(True)

        class _Ch:
            calls, puts, spot, expiry = [], [], 702.4, ""

        def _scalar(v):
            return v if (v is None or isinstance(v, (bool, int, float, str))) else type(v).__name__

        def world(park_open):
            fresh("w5b_%s" % park_open)
            if park_open and PW is not None:
                PW.book().set_open_positions([open_walled("park-open-b")])
            ev, saved = [], {}
            for attr, nm in (("_runaway_strategy", "RunawayContinuation"), ("_park_strategy", "PARK")):
                obj = getattr(MN, attr)
                saved[attr] = obj.generate_signal

                def fn(_nm=nm, **kw):
                    if _nm == "RunawayContinuation":
                        ev.append(("ask", _nm, MN.now_et().strftime("%H:%M"),
                                   sorted((k, _scalar(v)) for k, v in kw.items())))
                    return None
                obj.generate_signal = fn
            s_skip = MN._plan_skip

            def skip(n, reason, gate=""):
                if n == "RunawayContinuation":
                    ev.append(("skip", n, MN.now_et().strftime("%H:%M"), gate, reason))
                return s_skip(n, reason, gate)
            MN._plan_skip = skip
            s_gpm = MN.get_position_manager
            pm = PMM.PositionManager(False)
            MN.get_position_manager = lambda *a, **k: pm
            st = live_state()
            try:
                for i in range(0, 91):
                    tot = 9 * 60 + 35 + i
                    sw = pin(datetime(2026, 11, 20, tot // 60, tot % 60, 5, tzinfo=ET))
                    try:
                        st.tick_count = i
                        MN.attempt_new_entry({"price": 702.4, "chain": _Ch(), "macro": {}, "symbol": "QQQ",
                                              "gap": {"prior_close": 699.0}}, _MS(), st)
                    finally:
                        unpin(sw)
            finally:
                for attr, f in saved.items():
                    getattr(MN, attr).generate_signal = f
                MN._plan_skip = s_skip
                MN.get_position_manager = s_gpm
            return ev
        w0, w1 = world(False), world(True)
        digest = dg(c0)
        ok5 = (c0 == c1 and w0 == w1 and c0["sized"] and c0["exits"] and c0["cash_rows"] and c0["broker"] == []
               and sum(1 for e in w0 if e[0] == "ask") > 0 and digest == CASH_DIGEST)
        d5 = f"digest={digest} want={CASH_DIGEST} flat={c0} park={c1} dispatch_equal={w0 == w1} n={len(w0)}/{len(w1)}"
        print(f"       (W5 digest {digest})")
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d5 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-900:]}"
    check("W5 cash unaffected: a cash Runaway entry and exit, the cap, the broker log and the Runaway dispatch are "
          "byte-identical with a walled PARK position open (digest pinned on r160)", ok5, d5)

    # ── W6 the held page ────────────────────────────────────────────────────
    dtp = os.path.expanduser("~/day_trader_pro")
    hp = os.path.join(dtp, "tools", "held_contracts_page.py")
    if os.path.isfile(hp):
        ok6, d6 = False, ""
        try:
            import importlib.util
            from database.trade_logger import make_record
            p = fresh("w6")
            open_walled()
            TL._trade_logger.log_entry(make_record(trade_id="run-live", strategy="RunawayContinuation",
                                                   setup_type="runaway_long", direction="long", option_side="put",
                                                   strike=700.0, expiry=D, contracts=2, entry_premium=1.0,
                                                   total_cost=200.0, paper_trade=0,
                                                   option_symbol=K(700.0, 1, 1, D, "P").symbol, symbol="QQQ",
                                                   status="open"))
            sys.path.insert(0, os.path.join(dtp, "tools"))
            spec = importlib.util.spec_from_file_location("held_contracts_page", hp)
            H = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(H)
            c = sqlite3.connect(p)
            have = {r[1] for r in c.execute("PRAGMA table_info(trades)")}
            cols = [k for k in H.COLS if k in have]
            rws = [dict(zip(cols, r)) for r in c.execute("SELECT %s FROM trades WHERE status='open'" % ",".join(cols))]
            c.close()
            kind, text = H.build_page(D, {"QQQ": {"ok": True, "why": "", "rows": rws}})
            occ = K(702.0, 1, 1, D, "C").symbol.rstrip()
            lines = text.splitlines()
            desk = [ln for ln in lines if "Hi, account" in ln]
            ip = next((i for i, ln in enumerate(lines) if ln.startswith("paper (no message needed)")), len(lines))
            ok6 = (any(occ in ln and "(PARK)" in ln for ln in lines[ip + 1:]) and not any(occ in ln for ln in lines[:ip])
                   and any(ln.startswith("LIVE QQQ:") and "RunawayContinuation" in ln for ln in lines)
                   and occ not in " ".join(desk))
            d6 = f"kind={kind} text={text[:700]}"
        except Exception as exc:                                # noqa: BLE001
            d6 = f"{type(exc).__name__}: {exc}"
        check("W6 the held-contracts page lists the PARK paper row under paper and keeps it out of the desk message; the "
              "Runaway cash row is LIVE", ok6, d6)
    else:
        print("       (W6 not checked here: ~/day_trader_pro not present)")

    # ── W7 a paper box: paper_only == on ────────────────────────────────────
    ok7, d7 = False, ""
    try:
        def paper_day(text):
            flags(text)
            p = fresh("w7_%d" % len(os.listdir(FL)), paper_box=True)
            st = MN.BotState()
            st.paper_trading = True
            pm = PMM.PositionManager(True)
            xe = EE.ExitEngine(True)
            s_gpm, s_gee, s_pme = MN.get_position_manager, MN.get_entry_engine, PMM.get_exit_engine
            MN.get_position_manager = lambda *a, **k: pm
            MN.get_entry_engine = lambda *a, **k: ENE.EntryEngine(True)
            PMM.get_exit_engine = lambda *a, **k: xe
            ALERTS.clear()
            TALLY.clear()
            CALLS.clear()
            SPY.clear()
            try:
                enter(st)
                for hh, mm, mk in ((11, 10, 1.70), (14, 30, 1.80), (15, 41, 1.75), (15, 45, 1.75)):
                    sw = pin(datetime(2026, 11, 20, hh, mm, 5, tzinfo=ET))
                    try:
                        if (hh, mm) >= (15, 41):
                            MN.handle_hard_close(st)
                        if pm.has_open_position():
                            pm.manage_open_position(chain=mchain(mk), df_1m=None, df_5m=None)
                        MN._paper_wall_close_pass(st, None)
                    finally:
                        unpin(sw)
            finally:
                MN.get_position_manager, MN.get_entry_engine, PMM.get_exit_engine = s_gpm, s_gee, s_pme
            keep = ("strategy", "setup_type", "direction", "option_side", "strike", "expiry", "contracts",
                    "entry_premium", "total_cost", "stop_premium", "status", "exit_premium", "pnl_usd", "exit_reason",
                    "paper_trade", "max_premium_seen", "min_premium_seen", "option_symbol")
            rw = [{k: r.get(k) for k in keep} for r in rows(p)]
            untouched = PW._BOOK is None and PW._ENTRY is None
            return dg([rw, [a for a in ALERTS if a[0] in ("entry", "exit")], TALLY, CALLS, SPY]), rw, untouched
        # the paper box's own hard close reads the spot (a quote, never an order); its first run in a process warms a
        # cache, so the comparison is on / paper_only / on with paper_only between two warm runs of on
        on0 = paper_day(None)
        po = paper_day(PAPER_ONLY)
        on = paper_day(None)
        ok7 = (on[0] == po[0] and on[1] and on[1][0]["status"] == "closed" and on[1] == on0[1] and on0[2] and on[2]
               and po[2])
        d7 = f"on={on} paper_only={po} first_on={on0[0]}"
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d7 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-900:]}"
    check("W7 a PAPER box: park = paper_only books the same PARK day as park = on, byte for byte, and builds no wall",
          ok7, d7)

    # ── W8 park = off still dormant ─────────────────────────────────────────
    ok8, d8 = False, ""
    try:
        flags("park = off  # fixture\n")
        p = fresh("w8")
        asked = []
        s_gs = MN._park_strategy.generate_signal
        MN._park_strategy.generate_signal = lambda **kw: asked.append(1)
        sw = pin(fire_dt)
        try:
            MN._attempt_park({"price": 702.4, "chain": Chain(D, 700, 705, 1.58, 1.62)}, _MS(), live_state(),
                             chain=Chain(D, 700, 705, 1.58, 1.62))
        finally:
            unpin(sw)
            MN._park_strategy.generate_signal = s_gs
        sig = park_signal()
        CALLS.clear()
        SPY.clear()
        sw = pin(fire_dt)
        try:
            MN._execute_entry_signal(sig, {"price": 702.4, "macro": {}}, None, live_state(), None, additive=True)
        finally:
            unpin(sw)
        ok8 = (PS.state("PARK") == PS.DORMANT and RT.route("PARK", False) == RT.DORMANT
               and RT.route("PARK", True) == RT.DORMANT and asked == [] and rows(p) == [] and CALLS == []
               and SPY == [] and sig is not None)
        d8 = f"state={PS.state('PARK')} route={RT.route('PARK', False)} asked={asked} rows={rows(p)} calls={CALLS}"
    except Exception as exc:                                    # noqa: BLE001
        d8 = f"{type(exc).__name__}: {exc}"
    check("W8 park = off: DORMANT, never asked, routed DORMANT, and a PARK signal handed to the entry tail anyway is "
          "refused with no row and no broker call", ok8, d8)

    # ── W9 an open position keeps its lane ──────────────────────────────────
    ok9, d9 = False, ""
    try:
        res = {}
        flags(None)                                     # the flag now reads ON (cash PARK) ...
        p = fresh("w9a")
        rec = open_walled("park-walled")               # ... but this row OPENED on the wall
        st = live_state()
        CALLS.clear()
        sw = pin(datetime(2026, 11, 20, 12, 0, 0, tzinfo=ET))
        try:
            res["resumed"] = PW.recover()
        finally:
            unpin(sw)
        res["live_sees"] = [r["trade_id"] for r in TL.TradeLogger(db_path=p, paper_trading=False).get_open_trades()]
        res["route_close"] = RT.route_close(rec, False)
        res["route_open_now"] = RT.route("PARK", False)
        close_at(st, 15, 45, mchain(1.75))
        r = rows(p)[0]
        res["closed"] = (r["status"], r["paper_trade"], str(r["exit_reason"])[:16], r["exit_premium"])
        res["calls_a"] = list(CALLS)
        flags(PAPER_ONLY)                               # the flag now reads paper_only ...
        p = fresh("w9b")
        lrec = open_walled("park-live", paper=0)       # ... but this row OPENED live
        sw = pin(datetime(2026, 11, 20, 12, 0, 0, tzinfo=ET))
        try:
            res["wall_takes_live"] = PW.recover()
        finally:
            unpin(sw)
        res["live_holds"] = [r["trade_id"] for r in TL.TradeLogger(db_path=p, paper_trading=False).get_open_trades()]
        res["route_close_live"] = RT.route_close(lrec, False)
        ok9 = (res["resumed"] == 1 and res["live_sees"] == [] and res["route_close"] == RT.PAPER
               and res["route_open_now"] == RT.LIVE and res["closed"] == ("closed", 1, "park_close_15:45", 1.75)
               and res["calls_a"] == [] and res["wall_takes_live"] == 0 and res["live_holds"] == ["park-live"]
               and res["route_close_live"] == RT.LIVE)
        d9 = f"{res}"
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d9 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-900:]}"
    check("W9 an open position finishes in the lane it opened in: a walled row stays on the wall when the flag reads on "
          "(closes paper, zero broker calls); a live row is never taken by the wall when the flag reads paper_only",
          ok9, d9)

    # ── W10 the paper path holds no broker object; static; wiring ───────────
    ok10, d10 = False, ""
    try:
        flags(PAPER_ONLY)
        fresh("w10")
        st = live_state()
        CALLS.clear()
        enter(st)
        manage_at(st, 11, 10, mchain(1.70))
        seen, bad, stack = set(), [], [(PW.book(), "book", 0), (PW.entry_engine(), "entry", 0)]
        while stack:
            obj, path, depth = stack.pop()
            if id(obj) in seen:
                continue
            seen.add(id(obj))
            if any(obj is f for f in FAKE_OBJS):
                bad.append(path)
                continue
            if depth >= 4:
                continue
            vals = []
            if isinstance(obj, dict):
                vals = list(obj.items())
            elif isinstance(obj, (list, tuple, set)):
                vals = list(enumerate(obj))
            elif hasattr(obj, "__dict__") and not isinstance(obj, type) and not isinstance(obj, types.ModuleType):
                vals = list(vars(obj).items())
            for k, v in vals:
                stack.append((v, f"{path}.{k}", depth + 1))
        import ast
        imports = {}
        for rel in ("execution/paper_wall.py", "execution/order_router.py"):
            t = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())
            mods = set()
            for n in ast.walk(t):
                if isinstance(n, ast.Import):
                    mods |= {a.name for a in n.names}
                elif isinstance(n, ast.ImportFrom):
                    mods.add(n.module or "")
            imports[rel] = sorted(m for m in mods if "tasty" in m)
        tree = ast.parse(open(os.path.join(ROOT, "main.py"), encoding="utf-8").read())
        fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

        def calls_in(fn):
            return [(getattr(n.func, "id", None) or getattr(n.func, "attr", None), n.lineno)
                    for n in ast.walk(fns.get(fn) or ast.Module(body=[], type_ignores=[])) if isinstance(n, ast.Call)]
        ml, mn = calls_in("main_loop"), calls_in("main")
        ane = [ln for nm, ln in ml if nm == "attempt_new_entry"]
        hc = [ln for nm, ln in ml if nm == "handle_hard_close"]
        pwp = [ln for nm, ln in ml if nm == "_paper_wall_pass"]
        pwc = [ln for nm, ln in ml if nm == "_paper_wall_close_pass"]
        rop = [ln for nm, ln in mn if nm == "_recover_open_position"]
        rec = [ln for nm, ln in mn if nm == "recover"]
        wiring = (len(pwp) == 1 and ane and pwp[0] > max(ane) and len(pwc) == 1 and hc and pwc[0] > hc[0]
                  and len(rec) == 1 and rop and rec[0] > rop[0])
        ok10 = not bad and len(seen) > 5 and not any(imports.values()) and wiring and CALLS == []
        d10 = f"broker objects reachable={bad[:5]} walked={len(seen)} imports={imports} wiring={wiring} calls={CALLS}"
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d10 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-900:]}"
    check("W10 nothing reachable from the wall's book or entry engine is a broker object; paper_wall / order_router "
          "import no broker client; main_loop and main() wire the wall's passes and recover()", ok10, d10)

    # ── W11 the real QQQ file ───────────────────────────────────────────────
    real_q = BF.load("QQQ")
    real_s = BF.load("SPX")
    check("W11 the real QQQ box file reads park = paper_only, nothing refused; SPX runs on the defaults (park on)",
          real_q.values.get("park") == "paper_only" and not real_q.problems and real_q.status == "ok"
          and real_s.status == "missing" and real_s.values.get("park") == "on",
          f"QQQ={real_q.values} {real_q.problems} SPX={real_s.status} {real_s.values}")

    PMM.get_risk_manager = s_pm_grm
    OG.clear_to_post, BP.affordable = s_ctp, s_aff
    BF.reset()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {' '.join(FAILED)}")
        return 1
    print("GREEN — on a LIVE box park = paper_only paper-trades PARK on the wall (zero broker calls, out of reconcile, "
          "the startup cancel, the order guard, buying power and the cash cap), an open row keeps its lane, the cash "
          "Runaway path is byte-identical, and a paper box reads paper_only as on (W1-W11)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
