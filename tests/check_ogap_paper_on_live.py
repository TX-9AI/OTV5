#!/usr/bin/env python3
"""
tests/check_ogap_paper_on_live.py  v5.0
v5.0  2026-11-22  OTV5 r150 (OGAP.5) — new. ON A LIVE BOX OGAP KEEPS PAPER-TRADING, WALLED OFF FROM THE CASH ACCOUNT, AND THE
      CAP ON A LIVE BOX IS FOR LIVE TRADES ONLY. The operator, 2026-11-22: "I want it paper trading even on the cash boxes.
      It's under evaluation. Why the fuck would I want to stop evaluating it?"; "it should get its budget from
      configure.sh like the rest"; "The cap on a live box is for live trades only. Full stop."
      Runs as a LIVE box (OT_PAPER_TRADING=False, so BROKER_RECONCILE_ENABLED and every live default hold) against a FAKE
      BROKER: every broker-facing function of data/tasty_client (get_session, get_account, get_client, the position
      reads, the session reset, the async runner, sdk_result) is replaced, in that module and in every module that
      imported it by name, by a recorder; the fake account records every method called on it.

  P1  PLAN STATE: on the live box OGAP is ACTIVE with the flag on (no "dormant" in the [plans] line), _safe_strategy
      asks it, the Service line says "ogap=on (paper, walled from the cash account)"; on paper " · ogap=on" alone
  P2  A FULL OGAP DAY ON A LIVE BOX, ZERO BROKER CALLS: the real OGAP put of 2026-11-05 (tests/fixtures/ogap) through
      main._execute_entry_signal on a live BotState: booked at the mark 4.24 x floor(RISK_PER_TRADE_USD / (mark x 100))
      (the box's OT_RISK_USD, no OGAP budget), paper_trade = 1, order id PAPER-*, on paper_wall.book() and never on the
      live PositionManager; no freeze_contract walk, no suspect hand-off, no cap counterfactual row; managed by
      main._paper_wall_pass (lock 1.77x, trail 2.24x, hold 1.89x) and, in the hard-close window, by
      handle_hard_close + main._paper_wall_close_pass (15:41 held; 15:45:05 ogap_close_1545 at the mark 8.00, pnl
      +376.00); no risk_manager record_win / record_loss; the entry alert says [PAPER] and the exit alert's setup
      "PAPER ..."; the fake broker saw NO call from entry to close
  P3  RECONCILE AND RESTART: with that OGAP paper row OPEN, main._recover_open_position (the boot reconcile with
      BROKER_RECONCILE_ENABLED, the boot order sweep) and main._intraday_reconcile make the same broker calls and the
      same decisions as with no OGAP row (digest), never close or adopt it, the live manager never holds it, and
      paper_wall.recover() resumes it on the book (an expired walled row is closed, flagged)
  P4  THE STARTUP CANCEL: order_guard.sweep_working cancels the same leftover working order, keeps the same ids and
      makes the same account calls with and without the OGAP paper row open
  P5  THE CAP ON A LIVE BOX IS FOR LIVE TRADES ONLY: a closed OGAP paper loss of -$99,999 leaves day_realized_pnl 0.00
      and is_halted False; a cash PARK loss past the limit halts at the cash number alone; at the tripped cash cap
      attempt_new_entry asks no cash setup but still asks OGAP (no catastrophic_cap row for it), and that OGAP fires
      paper and is managed on the book. PAPER BOX unchanged (r137 CAP.10): the same OGAP loss halts, and at the cap
      OGAP is not asked
  P6  CASH UNAFFECTED (digest CASH_DIGEST): (a) a cash PARK entry (real _execute_entry_signal, live state, a live spy
      engine booking through EntryEngine._book_fill) and its exit (the real live PositionManager._manage_one /
      _execute_exit with a fake live exit engine) give the same sizing, rows, risk tally, cap reading and broker log with
      an OGAP paper position open (and a -$99,999 OGAP paper loss booked) as with none; (b) attempt_new_entry each
      minute 09:35-11:05 on the live box: Runaway / Hunt / PARK asks and plan skips byte-identical with OGAP flat and
      with OGAP open on the wall
  P7  THE HELD PAGE (dtp tools/held_contracts_page.build_page, when ~/day_trader_pro is present): the OGAP row lists
      under paper and is not in the desk message; the PARK cash row is LIVE
  P8  A PAPER BOX IS BYTE-IDENTICAL (digest PAPER_DAY_DIGEST, measured on r149 and r150): the same OGAP day on a paper
      box through the box's own paper engines books the same rows, alerts and tallies; paper_wall builds nothing
  P9  STATIC: no "dormant (live box" anywhere in the tree's code; paper_wall imports no data.tasty_client; plan_state
      reads no PAPER_TRADING
  P10 THE WIRING (main_loop cannot be run here): main_loop calls _paper_wall_pass once, after its last
      attempt_new_entry, and _paper_wall_close_pass once, after handle_hard_close; main() calls paper_wall.recover after
      _recover_open_position (the helpers themselves are driven for real in P2, P3 and P5)
Born red on r149 (eacf810; the code measured on the r149 build 18261a5, the same tree) at P1, P2, P3, P5, P9 and P10 (OGAP dormant on a live box; no paper wall). P4, P6,
P7 and P8 are green on both trees and pin what must not move: the order sweep, the cash path (CASH_DIGEST), the held
page's per-row split and the paper box (PAPER_DAY_DIGEST), each digest measured identical on r149 and r150. Revert
mutants (each wall removed in turn) red: see tests/check_ogap_paper_on_live.py's land spec (OGAP.5).
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
Run:  python3 tests/check_ogap_paper_on_live.py
"""
import hashlib
import json
import logging
import os
import sys
import tempfile
import types
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["OT_INSTRUMENT"] = "QQQ"
_TD = tempfile.mkdtemp(prefix="check_ogap_paper_on_live_")
for _k, _f in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"),
               ("OT_LOG_FILE", "bot.log"), ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_COUNTERFACTUAL_DIR", "cf"),
               ("OT_ALERT_SPOOL", "alert_spool.jsonl"), ("OT_PLAN_STATES_FILE", "plan_states.json"),
               ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT")):
    os.environ[_k] = os.path.join(_TD, _f)
os.environ.pop("OT_DAILY_LOSS_LIMIT", None)
os.environ.pop("OT_BROKER_RECONCILE", None)
os.environ["OT_PAPER_TRADING"] = "False"     # A LIVE BOX
os.environ["OT_RISK_USD"] = "500"
ET = ZoneInfo("America/New_York")
FIX = os.path.join(ROOT, "tests", "fixtures", "ogap", "replay5.json")
CASH_DIGEST = "bc4b0f6ce93d8f6a"        # P6: the same on r149 (eacf810 = 18261a5 in code) and r150
PAPER_DAY_DIGEST = "e567e6bf5c3a7577"   # P8: the same on r149 (eacf810 = 18261a5 in code) and r150
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name)


def dg(obj) -> str:
    return hashlib.sha256(json.dumps(obj, default=str, sort_keys=True).encode()).hexdigest()[:16]


class K:
    def __init__(self, strike, bid, ask, expiry, side):
        self.strike, self.bid, self.ask, self.expiry = strike, bid, ask, expiry
        self.mark = round((bid + ask) / 2, 2)
        self.delta = 0.5 if side == "C" else -0.5
        self.iv = 0.2
        self.symbol = f"QQQ  {expiry.replace('-', '')[2:]}{side}{int(strike * 1000):08d}"
        self.streamer_symbol = self.symbol


class Chain:
    def __init__(self, expiry, atm, bid, ask, n=3):
        self.expiry = expiry
        self.calls = [K(float(s), bid, ask, expiry, "C") for s in range(int(atm) - n, int(atm) + n + 1)]
        self.puts = [K(float(s), bid, ask, expiry, "P") for s in range(int(atm) - n, int(atm) + n + 1)]
        self.spot_price = float(atm)
        self.spot = float(atm)
        self.atm_iv = 0.2


# ── THE FAKE BROKER ─────────────────────────────────────────────────────────────────────────────────────────────────
CALLS = []


class FakeAccount:
    """Every method call is recorded; the answers come from RESP (default [])."""
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


def install_fake_broker():
    import data.tasty_client as TC
    acct, sess = FakeAccount(), types.SimpleNamespace(name="fake-session")
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
        for m in list(sys.modules.values()):
            try:
                if m is not None and getattr(m, name, None) is orig:
                    setattr(m, name, rec)
            except Exception:                                   # noqa: BLE001
                pass


def repatch():
    """Re-point any module imported after install_fake_broker."""
    for name, (orig, rec) in _FAKES.items():
        for m in list(sys.modules.values()):
            try:
                if m is not None and getattr(m, name, None) is orig:
                    setattr(m, name, rec)
            except Exception:                                   # noqa: BLE001
                pass


def main():
    print("check_ogap_paper_on_live")
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
        from strategy import plan_state as PS
        from strategy.ogap import Ogap
        from strategy import ogap_plan as OP
        from strategy.base_strategy import OptionsSignal
        from analysis.orb_engine import get_orb_engine
        from utils import box_flags as BF
        repatch()
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN: imports failed ({type(exc).__name__}: {exc})")
        return 2
    PW = getattr(MN, "_paper_wall", None)
    for _h in logging.getLogger().handlers:
        if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
            _h.setLevel(logging.CRITICAL + 1)
    if config.PAPER_TRADING is not False:
        print("NOT RUN: the interpreter is not a live box (config.PAPER_TRADING is not False)")
        return 2
    EE.get_exit_engine()                       # the singleton, built LIVE (as on a live box at start)

    # ── clocks, alerts, stores ──────────────────────────────────────────────
    real = {"now_et": TU.now_et, "now_utc": TU.now_utc}

    import strategy.management as MG

    def pin(dt):
        """now_et / now_utc everywhere, and datetime.now in the exit engine, the position manager, the management plan
        and main (exit_engine._evaluate_ogap reads datetime.now(_ET))."""
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
        import sqlite3
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

    fx = json.load(open(FIX))
    d = "2026-11-05"
    day = date.fromisoformat(d)
    bars = {int(k): tuple(v) for k, v in fx[d]["bars"].items()}
    fill = fx[d]["expect"]["fill"]
    spot = bars[fill][0]
    strike = float(fx[d]["expect"]["strike"])
    fill_dt = datetime(2026, 11, 5, fill // 60, fill % 60, 5, tzinfo=ET)

    def ogap_signal():
        return Ogap().generate_signal(price_now=spot, now_et=OP.hhmm(fill), chain=Chain(d, round(spot), 4.23, 4.26),
                                      day=day, symbol="QQQ", bars=bars, prior_close=fx[d]["prior_close"])

    def mchain(mark):
        return Chain(d, strike, round(mark - 0.01, 2), round(mark + 0.01, 2))

    BF.reset()

    # ── P1 plan state ───────────────────────────────────────────────────────
    ok1, d1 = False, ""
    try:
        asked = []
        s_adm = MN._admission_allows
        MN._admission_allows = lambda name: True
        try:
            MN._safe_strategy("OGAP", lambda: asked.append(1))
        finally:
            MN._admission_allows = s_adm
        b_live = MN._banner_dials()
        s_pt = MN.PAPER_TRADING
        MN.PAPER_TRADING = True
        try:
            b_paper = MN._banner_dials()
        finally:
            MN.PAPER_TRADING = s_pt
        summ = PS.summary(["OGAP"])
        ok1 = (PS.state("OGAP") == "active" and "dormant: live" not in summ and "OGAP dormant" not in summ
               and asked == [1] and " · ogap=on (paper, walled from the cash account)" in b_live
               and " · ogap=on ·" in b_paper + " ·" and "walled" not in b_paper)
        d1 = f"state={PS.state('OGAP')} asked={asked} summary={summ[-120:]} live={b_live[-160:]}"
    except Exception as exc:                                    # noqa: BLE001
        d1 = f"{type(exc).__name__}: {exc}"
    check("P1 a LIVE box: OGAP ACTIVE and asked; the Service line says paper, walled; a paper box's line unchanged", ok1, d1)

    # ── P2 the full OGAP day on a live box ──────────────────────────────────
    eng = get_orb_engine()
    eng.data.orb_high, eng.data.orb_low = spot + 1.0, spot - 1.0

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

    def ogap_day(st, manage, close_pass):
        """entry at the fill minute, three managed ticks, the hard-close window; -> notes"""
        notes = {}
        sw = pin(fill_dt)
        try:
            sig = ogap_signal()
            notes["sig"] = None if sig is None else (sig.option_side, float(sig.strike), sig.entry_premium)
            MN._execute_entry_signal(sig, {"price": spot, "macro": {}, "chain": Chain(d, round(spot), 4.23, 4.26)},
                                     None, st, None, additive=True)
        finally:
            unpin(sw)
        for hh, mm, mk in ((10, 30, 7.50), (11, 30, 9.50), (14, 30, 8.00)):
            sw = pin(datetime(2026, 11, 5, hh, mm, 5, tzinfo=ET))
            try:
                manage({"chain": mchain(mk), "price": spot, "df_1m": None, "df_5m": None})
            finally:
                unpin(sw)
        for hh, mm in ((15, 41), (15, 45)):
            sw = pin(datetime(2026, 11, 5, hh, mm, 5, tzinfo=ET))
            s_fc = MN.get_chain_fetcher
            MN.get_chain_fetcher = lambda: types.SimpleNamespace(fetch_chain=lambda: mchain(8.00))
            try:
                close_pass()
                notes["open_after_%02d%02d" % (hh, mm)] = len(rows(TL._trade_logger.db_path, "status='open'"))
            finally:
                MN.get_chain_fetcher = s_fc
                unpin(sw)
        return notes

    ok2, d2 = False, ""
    try:
        p2 = fresh("p2")
        st = live_state()
        frz, hand = [], []
        s_fz, s_hb = MN._freeze_contract, MN._hand_booked_to_manager
        MN._freeze_contract = lambda s, paper: frz.append(paper) or False
        MN._hand_booked_to_manager = lambda s: hand.append(1) or []
        live_pm = PMM.get_position_manager(False)
        live_pm._open_records = []
        CALLS.clear()
        ALERTS.clear()
        TALLY.clear()
        cfp = RM.cap_cf_path()                     # beside this world's trades.db
        cf_before = len(open(cfp).read().splitlines()) if os.path.exists(cfp) else 0
        peak_floor = {}

        def manage(c):
            MN._paper_wall_pass(c, st)
            for r in (PW.book().get_open_records() if PW else []):
                st_ = r.get("_ogap_state") or {}
                peak_floor.setdefault("seen", []).append((round(float(st_.get("peak") or 0), 2),
                                                          None if st_.get("floor") is None else round(float(st_["floor"]), 4)))

        def close_pass():
            MN.handle_hard_close(st)
            MN._paper_wall_close_pass(st, None)
        try:
            notes = ogap_day(st, manage, close_pass)
        finally:
            MN._freeze_contract, MN._hand_booked_to_manager = s_fz, s_hb
        cf_lines = open(cfp).read().splitlines() if os.path.exists(cfp) else []
        cf_after = len(cf_lines)
        cf_ogap = [ln for ln in cf_lines[cf_before:] if '"strategy": "OGAP"' in ln]
        rw = rows(p2)
        r0 = rw[0] if rw else {}
        want_n = int(float(os.environ["OT_RISK_USD"]) // (4.24 * 100))
        ok2 = (len(rw) == 1 and r0.get("strategy") == "OGAP" and r0.get("paper_trade") == 1
               and str(r0.get("order_id", "")).startswith("PAPER-") and r0.get("entry_premium") == 4.24
               and r0.get("contracts") == want_n and r0.get("status") == "closed"
               and str(r0.get("exit_reason", "")).startswith("ogap_close_1545") and r0.get("exit_premium") == 8.0
               and round(float(r0.get("pnl_usd") or 0), 2) == round((8.0 - 4.24) * 100 * want_n, 2)
               and notes.get("open_after_1541") == 1 and notes.get("open_after_1545") == 0
               and peak_floor.get("seen") == [(7.5, round(1.2 * 4.24, 4)), (9.5, round(0.6 * 9.5, 4)), (9.5, round(0.6 * 9.5, 4))]
               and not live_pm.get_open_records() and frz == [True] and not hand and not TALLY and not cf_ogap
               and ("entry", "PAPER", "OGAP") in ALERTS
               and any(a[0] == "exit" and str(a[1]).startswith("PAPER ") for a in ALERTS)
               and CALLS == [])
        d2 = (f"notes={notes} row={ {k: r0.get(k) for k in ('strategy', 'paper_trade', 'order_id', 'entry_premium', 'contracts', 'status', 'exit_reason', 'exit_premium', 'pnl_usd')} } "
              f"n={len(rw)} live={len(live_pm.get_open_records())} freeze={frz} hand={hand} tally={TALLY} "
              f"cf_ogap={len(cf_ogap)} ({cf_before}->{cf_after}) alerts={[a for a in ALERTS if a[0] in ('entry', 'exit')]} "
              f"broker={CALLS[:6]} ogap_state={peak_floor}")
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d2 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-700:]}"
    check("P2 a full OGAP day on a LIVE box books paper at the mark on the wall (entry, lock/trail, 15:45 close) with "
          "ZERO broker calls, no cash tally, no cap counterfactual, PAPER alerts", ok2, d2)

    # helpers: an OGAP paper row OPEN on the wall
    def open_walled(tid="ogap-open", expiry=d):
        from database.trade_logger import make_record
        rec = make_record(trade_id=tid, strategy="OGAP", setup_type="ogap_short", direction="short",
                          option_side="put", strike=strike, expiry=expiry, contracts=1, entry_premium=4.24,
                          total_cost=424.0, max_loss=424.0, stop_premium=0.0, underlying_entry=spot,
                          option_symbol=K(strike, 1, 1, expiry, "P").symbol, order_id="PAPER-X",
                          paper_trade=1, symbol="QQQ", status="open")
        TL._trade_logger.log_entry(rec)
        return rec

    def closed_walled_loss(tid="ogap-loss", pnl=-99999.0):
        open_walled(tid)
        TL._trade_logger.log_exit(trade_id=tid, exit_price=0.01, pnl_usd=pnl, exit_reason="ogap_test")

    # ── P3 reconcile and restart ────────────────────────────────────────────
    ok3, d3 = False, ""
    try:
        def boot(with_ogap):
            fresh("p3_%s" % with_ogap)
            if with_ogap:
                open_walled()
                open_walled("ogap-expired", expiry="2026-11-04")
            st = live_state()
            pm = PMM.PositionManager(False)
            s_gpm = MN.get_position_manager
            MN.get_position_manager = lambda *a, **k: pm
            CALLS.clear()
            ALERTS.clear()
            FakeAccount.RESP = {"_positions": []}
            sw = pin(datetime(2026, 11, 5, 9, 20, 0, tzinfo=ET))
            try:
                MN._recover_open_position(st, "service restart")
                boot_calls = list(CALLS)
                CALLS.clear()
                MN._intraday_reconcile(st, "QQQ")
                intra_calls = list(CALLS)
                resumed = PW.recover() if (with_ogap and PW is not None) else 0
            finally:
                unpin(sw)
                MN.get_position_manager = s_gpm
            rw = {r["trade_id"]: (r["status"], r["paper_trade"], r["exit_reason"]) for r in rows(TL._trade_logger.db_path)}
            alerts = [a[0] for a in ALERTS]
            return boot_calls, intra_calls, len(pm.get_open_records()), rw, alerts, resumed
        b0, b1 = boot(False), boot(True)
        book_ids = [r.get("trade_id") for r in PW.book().get_open_records()] if PW else []
        ok3 = (b0[0] == b1[0] and b0[1] == b1[1] and b0[2] == b1[2] == 0 and b0[4] == b1[4]
               and b1[3].get("ogap-open") == ("open", 1, None)
               and (b1[3].get("ogap-expired") or ("?",))[0] == "closed" and b1[5] == 1 and book_ids == ["ogap-open"]
               and len(b0[0]) > 0)
        d3 = f"flat={b0[:3]} alerts={b0[4]} | ogap={b1[:3]} rows={b1[3]} alerts={b1[4]} resumed={b1[5]} book={book_ids}"
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d3 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-700:]}"
    check("P3 the boot reconcile, the order sweep and the intraday reconcile make the same broker calls and decisions "
          "with an OGAP paper row open; they never touch it; paper_wall.recover resumes it (an expired one closed)", ok3, d3)

    # ── P4 the startup cancel ───────────────────────────────────────────────
    ok4, d4 = False, ""
    try:
        def sweep(with_ogap):
            fresh("p4_%s" % with_ogap)
            if with_ogap:
                open_walled()
            CALLS.clear()
            wo = types.SimpleNamespace(id="W1", status=types.SimpleNamespace(value="Live"), underlying_symbol="QQQ",
                                       legs=[])
            FakeAccount.RESP = {"get_live_orders": [wo],
                                "get_order": lambda *a, **k: types.SimpleNamespace(
                                    status=types.SimpleNamespace(value="Cancelled"))}
            OG.reset()
            res = OG.sweep_working(types.SimpleNamespace(), FakeAccount(), "QQQ")
            keep = OG._kept_order_ids()
            return res, sorted(keep), list(CALLS)
        s0, s1 = sweep(False), sweep(True)
        FakeAccount.RESP = {}
        ok4 = s0 == s1 and s0[0][0] is True and s0[0][1] == 1
        d4 = f"flat={s0} ogap={s1}"
    except Exception as exc:                                    # noqa: BLE001
        d4 = f"{type(exc).__name__}: {exc}"
    check("P4 the startup cancel of working orders is identical with an OGAP paper row open", ok4, d4)

    # ── P5 the cap ──────────────────────────────────────────────────────────
    ok5, d5 = False, ""
    try:
        from database.trade_logger import make_record
        res = {}
        fresh("p5a")
        closed_walled_loss()
        rm = RM.RiskManager(paper_trading=False)
        res["live_ogap_only"] = (round(rm.day_realized_pnl(), 2), rm.is_halted())
        rec = make_record(trade_id="park-loss", strategy="PARK", setup_type="park_long", direction="long",
                          option_side="call", strike=600.0, expiry=d, contracts=1, entry_premium=7.0, total_cost=700.0,
                          paper_trade=0, symbol="QQQ", status="open")
        TL._trade_logger.log_entry(rec)
        TL._trade_logger.log_exit(trade_id="park-loss", exit_price=0.5, pnl_usd=-650.0, exit_reason="t")
        rm = RM.RiskManager(paper_trading=False)
        res["live_cash_loss"] = (round(rm.day_realized_pnl(), 2), rm.is_halted())

        fresh("p5b", paper_box=True)                          # a PAPER box: the OGAP paper loss is inside its cap
        closed_walled_loss()
        rm = RM.RiskManager(paper_trading=True)
        res["paper_ogap_loss"] = (round(rm.day_realized_pnl(), 2), rm.is_halted())

        # at the tripped cash cap: who is asked (every row written on the pinned day)
        def at_cap(paper_box):
            _sw0 = pin(fill_dt)
            try:
                return _at_cap(paper_box)
            finally:
                unpin(_sw0)

        def _at_cap(paper_box):
            p = fresh("p5_cap_%s" % paper_box, paper_box=paper_box)
            TL._trade_logger.log_entry(make_record(**{**dict(rec), "paper_trade": 1 if paper_box else 0}))
            TL._trade_logger.log_exit(trade_id="park-loss", exit_price=0.5, pnl_usd=-650.0, exit_reason="t")
            RM._risk_manager = RM.RiskManager(paper_trading=paper_box)
            st = MN.BotState()
            st.paper_trading = paper_box
            asked, skips = [], []
            saved = {}
            sig = None
            for attr, nm in (("_runaway_strategy", "RunawayContinuation"), ("_liquidity_hunt", "LiquidityHunt"),
                             ("_park_strategy", "PARK"), ("_ogap_strategy", "OGAP"), ("_breakout", "Breakout")):
                obj = getattr(MN, attr)
                saved[attr] = obj.generate_signal

                def fn(_nm=nm, **kw):
                    asked.append(_nm)
                    return ogap_signal() if _nm == "OGAP" else None
                obj.generate_signal = fn
            s_skip = MN._plan_skip
            MN._plan_skip = lambda n, reason, gate="": skips.append((n, gate)) or s_skip(n, reason, gate)
            s_gpm = MN.get_position_manager
            pm = PMM.PositionManager(paper_box)
            MN.get_position_manager = lambda *a, **k: pm
            if paper_box:
                s_gee = MN.get_entry_engine
                MN.get_entry_engine = lambda *a, **k: ENE.EntryEngine(True)
            CALLS.clear()
            try:
                MN.attempt_new_entry({"price": spot, "chain": Chain(d, round(spot), 4.23, 4.26), "macro": {},
                                      "symbol": "QQQ", "gap": {"prior_close": fx[d]["prior_close"]}}, _MS(), st)
            finally:
                for attr, f in saved.items():
                    getattr(MN, attr).generate_signal = f
                MN._plan_skip = s_skip
                MN.get_position_manager = s_gpm
                if paper_box:
                    MN.get_entry_engine = s_gee
            og = [r for r in rows(p, "strategy='OGAP' AND status='open'")]
            booked = len(PW.book().get_open_records()) if (PW is not None and not paper_box) else None
            return (RM._risk_manager.is_halted(), sorted(set(asked)), sorted(set(g for n, g in skips if n == "OGAP")),
                    sorted(set(g for n, g in skips if n == "PARK")), len(og), booked, list(CALLS))
        res["live_at_cap"] = at_cap(False)
        res["paper_at_cap"] = at_cap(True)
        lc, pc = res["live_at_cap"], res["paper_at_cap"]
        ok5 = (res["live_ogap_only"] == (0.0, False) and res["live_cash_loss"] == (-650.0, True)
               and res["paper_ogap_loss"] == (-99999.0, True)
               and lc[0] is True and lc[1] == ["OGAP"] and "catastrophic_cap" not in lc[2]
               and "catastrophic_cap" in lc[3] and lc[4] == 1 and lc[5] == 1 and lc[6] == []
               and pc[0] is True and pc[1] == [] and "catastrophic_cap" in pc[2] and pc[4] == 0)
        d5 = f"{res}"
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d5 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-700:]}"
    check("P5 the cap on a LIVE box is for live trades only: an OGAP paper loss never moves or trips it; at the tripped "
          "cash cap cash is refused and OGAP still fires paper on the wall; a PAPER box keeps r137 (OGAP inside the cap)",
          ok5, d5)

    # ── P6 cash unaffected ──────────────────────────────────────────────────
    ok6, d6 = False, ""
    try:
        from execution.exit_engine import FillResult, ExitDecision

        class _LiveSpy:
            def __init__(self):
                self.calls = []
                self.eng = ENE.EntryEngine(False)

            def enter(self, signal=None, sizing=None, **kw):
                self.calls.append((signal.strategy_name, sizing.contracts, round(sizing.total_cost, 2)))
                rec = self.eng._book_fill(signal, float(signal.entry_premium), "LIVE-1", sizing.contracts,
                                          sizing.contracts)
                return rec

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

        def cash_world(with_ogap):
            p = fresh("p6_%s" % with_ogap)
            if with_ogap:
                closed_walled_loss()
                PW.book().set_open_positions([open_walled()]) if PW is not None else open_walled()
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
            sw = pin(datetime(2026, 11, 5, 10, 0, 5, tzinfo=ET))
            try:
                sg = OptionsSignal(strategy_name="PARK", setup_type="park_long", direction="long", option_side="call",
                                   underlying_entry=600.0, underlying_stop=0.0, strike=600.0, entry_premium=1.45,
                                   stop_loss_pct=1.0)
                sg.contract = K(600.0, 1.44, 1.46, d, "C")
                MN._execute_entry_signal(sg, {"price": 600.0, "macro": {}}, None, st, None, additive=True)
                after_entry = [(r.get("strategy"), r.get("contracts"), r.get("entry_premium")) for r in pm.get_open_records()]
                pm.manage_open_position(chain=Chain(d, 600, 1.79, 1.81), df_1m=None)
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

        # (b) the dispatch, a live box, OGAP flat vs open on the wall
        class _Ch:
            calls, puts, spot, expiry = [], [], 600.0, ""

        def _scalar(v):
            return v if (v is None or isinstance(v, (bool, int, float, str))) else type(v).__name__

        def world(ogap_open):
            fresh("p6b_%s" % ogap_open)
            if ogap_open:
                rec = open_walled("ogap-open-b", expiry="2026-11-20")
                if PW is not None:
                    PW.book().set_open_positions([rec])
            ev = []
            saved = {}
            for attr, nm in (("_runaway_strategy", "RunawayContinuation"), ("_liquidity_hunt", "LiquidityHunt"),
                             ("_park_strategy", "PARK"), ("_ogap_strategy", "OGAP"), ("_breakout", "Breakout")):
                obj = getattr(MN, attr)
                saved[attr] = obj.generate_signal

                def fn(_nm=nm, **kw):
                    if _nm != "OGAP":
                        ev.append(("ask", _nm, MN.now_et().strftime("%H:%M"), sorted((k, _scalar(v)) for k, v in kw.items())))
                    return None
                obj.generate_signal = fn
            s_skip = MN._plan_skip

            def skip(n, reason, gate=""):
                if n in ("RunawayContinuation", "LiquidityHunt", "PARK"):
                    ev.append(("skip", n, MN.now_et().strftime("%H:%M"), gate, reason))
                return s_skip(n, reason, gate)
            MN._plan_skip = skip
            s_gpm = MN.get_position_manager
            pm = PMM.PositionManager(False)
            MN.get_position_manager = lambda *a, **k: pm
            e2 = get_orb_engine()
            sh, sl = e2.data.orb_high, e2.data.orb_low
            e2.data.orb_high, e2.data.orb_low = 601.0, 599.0
            st = live_state()
            try:
                for i in range(0, 91):
                    tot = 9 * 60 + 35 + i
                    sw = pin(datetime(2026, 11, 20, tot // 60, tot % 60, 5, tzinfo=ET))
                    try:
                        st.tick_count = i
                        MN.attempt_new_entry({"price": 600.0, "chain": _Ch(), "macro": {}, "symbol": "QQQ",
                                              "gap": {"prior_close": 598.0}}, _MS(), st)
                    finally:
                        unpin(sw)
            finally:
                for attr, f in saved.items():
                    getattr(MN, attr).generate_signal = f
                MN._plan_skip = s_skip
                MN.get_position_manager = s_gpm
                e2.data.orb_high, e2.data.orb_low = sh, sl
            return ev
        w0, w1 = world(False), world(True)
        digest = dg([c0, w0])
        ok6 = (c0 == c1 and w0 == w1 and c0["sized"] and c0["exits"] and c0["cash_rows"]
               and sum(1 for e in w0 if e[0] == "ask") > 0
               and digest == CASH_DIGEST)
        d6 = f"digest={digest} want={CASH_DIGEST} flat={c0} ogap={c1} dispatch_equal={w0 == w1} n={len(w0)}/{len(w1)}"
        if w0 != w1:
            d6 += f" first_diff={[(a, b) for a, b in zip(w0, w1) if a != b][:2]}"
        print(f"       (P6 digest {digest})")
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d6 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-700:]}"
    check("P6 cash unaffected: a cash PARK entry and exit, the cap reading, the broker log and the Runaway / Hunt / PARK "
          "dispatch are byte-identical with an OGAP paper position open (digest pinned)", ok6, d6)

    # ── P7 the held page ────────────────────────────────────────────────────
    dtp = os.path.expanduser("~/day_trader_pro")
    hp = os.path.join(dtp, "tools", "held_contracts_page.py")
    if os.path.isfile(hp):
        ok7, d7 = False, ""
        try:
            import importlib.util
            import sqlite3
            p = fresh("p7")
            open_walled()
            from database.trade_logger import make_record
            TL._trade_logger.log_entry(make_record(trade_id="park-live", strategy="PARK", setup_type="park_long",
                                                   direction="long", option_side="call", strike=600.0, expiry=d,
                                                   contracts=2, entry_premium=1.0, total_cost=200.0, paper_trade=0,
                                                   option_symbol=K(600.0, 1, 1, d, "C").symbol, symbol="QQQ",
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
            kind, text = H.build_page(d, {"QQQ": {"ok": True, "why": "", "rows": rws}})
            og_occ = K(strike, 1, 1, d, "P").symbol.rstrip()
            lines = text.splitlines()
            desk = [ln for ln in lines if "Hi, account" in ln]
            ip = next((i for i, ln in enumerate(lines) if ln.startswith("paper (no message needed)")), len(lines))
            ok7 = (kind == "critical" and any(og_occ in ln and "(OGAP)" in ln for ln in lines[ip + 1:])
                   and not any(og_occ in ln for ln in lines[:ip])
                   and any(ln.startswith("LIVE QQQ:") and "PARK" in ln for ln in lines)
                   and desk and og_occ not in " ".join(desk))
            d7 = f"kind={kind} text={text[:600]}"
        except Exception as exc:                                # noqa: BLE001
            d7 = f"{type(exc).__name__}: {exc}"
        check("P7 the held-contracts page lists the OGAP paper row under paper and keeps it out of the desk message",
              ok7, d7)
    else:
        print("       (P7 not checked here: ~/day_trader_pro not present)")

    # ── P8 a paper box is byte-identical ────────────────────────────────────
    ok8, d8 = False, ""
    try:
        p8 = fresh("p8", paper_box=True)
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

        def manage(c):
            pm.manage_open_position(chain=c["chain"], df_1m=None, df_5m=None)

        def close_pass():
            MN.handle_hard_close(st)
            if pm.has_open_position():
                pm.manage_open_position(chain=mchain(8.00), df_1m=None, df_5m=None)
            if hasattr(MN, "_paper_wall_close_pass"):
                MN._paper_wall_close_pass(st, None)
        try:
            notes = ogap_day(st, manage, close_pass)
        finally:
            MN.get_position_manager, MN.get_entry_engine, PMM.get_exit_engine = s_gpm, s_gee, s_pme
        keep = ("strategy", "setup_type", "direction", "option_side", "strike", "expiry", "contracts", "entry_premium",
                "total_cost", "stop_premium", "status", "exit_premium", "pnl_usd", "exit_reason", "paper_trade",
                "trail_stop", "max_premium_seen", "min_premium_seen", "option_symbol")
        rw = [{k: r.get(k) for k in keep} for r in rows(p8)]
        al = [a for a in ALERTS if a[0] in ("entry", "exit")]
        digest = dg([notes, rw, al, TALLY, CALLS])      # CALLS: the paper box's own hard close reads the spot
        untouched = PW is None or (PW._BOOK is None and PW._ENTRY is None)
        ok8 = (untouched and rw and rw[0]["status"] == "closed"
               and digest == PAPER_DAY_DIGEST)
        d8 = f"digest={digest} want={PAPER_DAY_DIGEST} wall_untouched={untouched} notes={notes} rows={rw} alerts={al} tally={TALLY}"
        print(f"       (P8 digest {digest})")
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d8 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-700:]}"
    check("P8 a PAPER box's OGAP day is byte-identical to r149 (digest pinned) and builds no paper wall", ok8, d8)

    # ── P9 static ───────────────────────────────────────────────────────────
    bad9 = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [x for x in dn if x not in (".git", "__pycache__", "venv", "tests", "docs")]
        for f in fn:
            if f.endswith(".py"):
                src = open(os.path.join(dp, f), encoding="utf-8").read()
                code = src.split('"""', 2)[-1] if src.lstrip().startswith('"""') else src
                if "dormant (live box" in code:
                    bad9.append(os.path.relpath(os.path.join(dp, f), ROOT))
    pw_src = open(os.path.join(ROOT, "execution", "paper_wall.py"), encoding="utf-8").read() \
        if os.path.exists(os.path.join(ROOT, "execution", "paper_wall.py")) else None
    ps_src = open(os.path.join(ROOT, "strategy", "plan_state.py"), encoding="utf-8").read().split('"""', 2)[-1]
    check("P9 no live-box dormant rule in code; paper_wall imports no broker client; plan_state reads no PAPER_TRADING",
          not bad9 and pw_src is not None and "tasty_client" not in pw_src and "PAPER_TRADING" not in ps_src,
          f"dormant={bad9} paper_wall={'missing' if pw_src is None else 'tasty_client' in pw_src} "
          f"plan_state_reads={'PAPER_TRADING' in ps_src}")

    # ── P10 the wiring ──────────────────────────────────────────────────────
    import ast
    tree = ast.parse(open(os.path.join(ROOT, "main.py"), encoding="utf-8").read())
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

    def calls_in(fn):
        out = []
        for n in ast.walk(fns.get(fn) or ast.Module(body=[], type_ignores=[])):
            if isinstance(n, ast.Call):
                f = n.func
                out.append((getattr(f, "id", None) or getattr(f, "attr", None), n.lineno))
        return out
    ml, mn = calls_in("main_loop"), calls_in("main")
    ane = [ln for nm, ln in ml if nm == "attempt_new_entry"]
    hc = [ln for nm, ln in ml if nm == "handle_hard_close"]
    pwp = [ln for nm, ln in ml if nm == "_paper_wall_pass"]
    pwc = [ln for nm, ln in ml if nm == "_paper_wall_close_pass"]
    rop = [ln for nm, ln in mn if nm == "_recover_open_position"]
    rec = [ln for nm, ln in mn if nm == "recover"]
    ok10 = (len(pwp) == 1 and ane and pwp[0] > max(ane) and len(pwc) == 1 and hc and pwc[0] > hc[0]
            and len(rec) == 1 and rop and rec[0] > rop[0])
    check("P10 the wiring: main_loop runs _paper_wall_pass after the tick's entries and _paper_wall_close_pass after "
          "handle_hard_close; main() runs paper_wall.recover after _recover_open_position", ok10,
          f"pass={pwp} entries={ane} close={pwc} hard_close={hc} recover={rec} recover_open={rop}")

    PMM.get_risk_manager = s_pm_grm
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {' '.join(FAILED)}")
        return 1
    print("GREEN — on a LIVE box OGAP paper-trades on the wall (zero broker calls, out of reconcile, the cash cap and "
          "the order sweep), the cash path is byte-identical, and a paper box is unchanged (P1-P10)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
