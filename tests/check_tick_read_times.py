#!/usr/bin/env python3
"""
tests/check_tick_read_times.py  v5.0
v5.0  2026-11-22  OTV5 r147 (QTIME.1; record only) — new. EVERY TICK RECORDS WHEN IT READ ITS QUOTES, ON THE ROWS THAT
      ALREADY FLOW TO S3. The operator, 2026-11-22: "Yes to both" (the WS.15 pricer's one unrecorded input: the bot reads
      bid/ask from the feed store's chain_marks, refreshed every FLUSH_INTERVAL_S = 2 s, so a tick's mark is 0-4 s old
      and before r147 neither the read time nor the store's refresh time was recorded).

  T1  the real chain read (OptionsChainFetcher.fetch_chain over a scratch feed store, the REST structure and OI stubbed):
      the chain carries marks_read_epoch (inside the call's wall-clock window) and marks_store_epoch = the newest
      updated_epoch of the rows that SELECT returned (a stale row past OT_CHAIN_STALE_S excluded); read >= store, read -
      store <= OT_CHAIN_STALE_S; every contract's quote_epoch <= store
  T2  main_loop wiring (AST): tick_reads.begin(tick_start) right after `tick_start = time.time()` and before the tick's
      first chain fetch; tick_reads.chain_read(_gex_chain) after the pre-analysis fetch and before
      run_analysis(state, chain=_gex_chain)
  T3  plan_tick (strategy/plan): the four trailing columns exist and the r146 columns are an unchanged prefix (no column
      dropped); a DECLINE row carries the tick's three times and a NULL quote_epoch; a TAKE row carries the fired
      contract's quote_epoch; an INACTIVE row close_tick writes at the NEXT board tick keeps the tick it belongs to; a
      pre-r147 store migrates in place (old rows NULL)
  T4  the /manage row (real PositionManager, paper, on a chain built by the T1 path): RunawayContinuation/manage's
      plan_tick row carries the priced contract's quote_epoch and the tick's read times, with sane values
  T5  signal_journal: through main._execute_entry_signal, the refusals invalid_signal and sizing_rejected and the
      fired disposition each carry tick_reads (the tick in progress) and signal.contract.quote_epoch
  T6  sane values on every T3-T5 row that carries them: tick_start <= read, store <= read, read - store <=
      OT_CHAIN_STALE_S, quote <= store
  T7  zero broker calls, no knob: utils/tick_reads imports nothing but typing, reads no env/config/file; config.py
      names no TICK_READ key; data/options_chain.py runs the same number of SQL statements as r146 (no second read)
  T8  DECISIONS BYTE-IDENTICAL: one digest over (a) the chain the real fetcher builds from six store snapshots
      (every contract's bid, ask, mark, greeks, quote age), (b) attempt_new_entry every minute 09:30-15:44 and
      EntryEngine.enter() every minute 09:30-15:59 (r146 R8's harness), (c) a paper Runaway managed by the real
      PositionManager over a 44-tick mark path read from the store (every trail, exit and its price) and (d) the
      pre-r147 columns of every plan_tick row those wrote. REPLAY_DIGEST is r146's (df51252), identical on r147.
Born red on r146 (df51252) at T1 T2 T3 T4 T5 T6 T7 (T8 green on both trees: the digest is r146's).
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas / tastytrade).
Run:  python3 tests/check_tick_read_times.py
"""
import ast
import glob
import hashlib
import json
import logging
import os
import sqlite3
import sys
import tempfile
import time
import types
from datetime import datetime, timezone, date
from decimal import Decimal
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
_TD = tempfile.mkdtemp(prefix="check_tick_read_times_")
for _k, _f in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"),
               ("OT_LOG_FILE", "bot.log"), ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_COUNTERFACTUAL_DIR", "cf"),
               ("OT_ALERT_SPOOL", "alert_spool.jsonl"), ("OT_PLAN_STATES_FILE", "plan_states.json"),
               ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT")):
    os.environ[_k] = os.path.join(_TD, _f)
os.environ.pop("OT_DAILY_LOSS_LIMIT", None)
ET = ZoneInfo("America/New_York")
FAILED = []
REPLAY_DIGEST = "2af7101925b14427"   # T8: r146 df51252 == r147
R146_PLAN_TICK = ["ts_epoch", "symbol", "strategy", "verdict", "reason", "trigger_price", "invalidation",
                  "underlying", "dist_to_trigger", "r_now", "direction", "tick_id"]
NEW_COLS = ["tick_start_epoch", "marks_read_epoch", "marks_store_epoch", "quote_epoch"]
R146_SQL_EXECUTES = 3       # T7: `.execute(` calls in data/options_chain.py at r146 (chain_subs DDL, upsert; marks)


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class _Pin:
    """Pin now_et / now_utc in every loaded module that holds the real function (check_blind_reacquire's sweep)."""
    def __init__(self, TU):
        self.TU, self.real = TU, {"now_et": TU.now_et, "now_utc": TU.now_utc}
        self.sw = []

    def set(self, dt):
        self.unset()
        fake = {"now_et": lambda: dt, "now_utc": lambda: dt.astimezone(timezone.utc)}
        self.sw = [(m, n) for m in list(sys.modules.values()) for n in self.real
                   if m is not None and getattr(m, n, None) is self.real[n]]
        for m, n in self.sw:
            setattr(m, n, fake[n])

    def unset(self):
        for m, n in self.sw:
            setattr(m, n, self.real[n])
        self.sw = []


DAY = date(2026, 11, 5)
STRIKES = [598.0, 599.0, 600.0, 601.0, 602.0]


def _sym(cp, k):
    return f".QQQ261105{cp}{int(k)}"


def _feed_reset(path):
    c = sqlite3.connect(path)
    c.execute("DROP TABLE IF EXISTS chain_marks")
    c.execute("CREATE TABLE chain_marks (streamer_symbol TEXT PRIMARY KEY, bid REAL, ask REAL, delta REAL, gamma REAL,"
              " theta REAL, vega REAL, iv REAL, updated_epoch REAL)")
    c.commit()
    c.close()


def _feed_write(path, rows):
    """rows: (sym, bid, ask, delta, epoch)"""
    c = sqlite3.connect(path)
    c.executemany("INSERT OR REPLACE INTO chain_marks (streamer_symbol, bid, ask, delta, gamma, theta, vega, iv,"
                  " updated_epoch) VALUES (?,?,?,?,0.05,-0.1,0.02,0.2,?)", rows)
    c.commit()
    c.close()


def _snapshot(base, now, call_mid):
    """One store state: five calls and five puts around 600, ages 0.3-3.5 s, plus an aux-tenor row (newest) and a
    row older than the staleness floor. call_mid shifts the 601 call's mark (the exit path)."""
    rows = []
    for i, k in enumerate(STRIKES):
        cm = call_mid if k == 601.0 else round(max(0.05, 2.0 + (600.0 - k) * 0.6), 2)
        pm = round(max(0.05, 2.0 + (k - 600.0) * 0.6), 2)
        d = round(0.5 + (600.0 - k) * 0.1, 3)
        rows.append((_sym("C", k), round(cm - 0.02, 2), round(cm + 0.02, 2), d, now - 0.3 - 0.4 * i))
        rows.append((_sym("P", k), round(pm - 0.02, 2), round(pm + 0.02, 2), -round(1 - d, 3), now - 0.5 - 0.6 * i))
    rows.append((".QQQ261112C600", 3.0, 3.1, 0.5, now - 0.1))          # an aux tenor row: the newest event flushed
    rows.append((_sym("C", 597.0), 4.0, 4.1, 0.8, now - 600.0))        # past OT_CHAIN_STALE_S: not read
    return rows


def main():
    print("check_tick_read_times")
    try:
        import pandas  # noqa: F401
        import main as MN
        import utils.time_utils as TU
        import execution.entry_engine as EE
        import execution.position_manager as PM
        import execution.exit_engine as XE
        import data.options_chain as OC
        from strategy import plan as P
        from analysis import signal_journal as SJ
        from data.derived_store import get_derived_store
        from strategy.base_strategy import OptionsSignal
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN: imports failed ({type(exc).__name__}: {exc})")
        return 2
    try:
        from utils import tick_reads as TR
    except Exception as exc:                                    # noqa: BLE001
        TR = None
        print(f"  (utils/tick_reads not importable: {type(exc).__name__}: {exc})")

    for _h in logging.getLogger().handlers:
        if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
            _h.setLevel(logging.CRITICAL + 1)
    pin = _Pin(TU)
    MN.time.sleep = lambda s: None
    FEED = os.environ["OT_FEED_DB"]
    STALE = float(OC.OT_CHAIN_STALE_S)

    # ── the real fetcher on a scratch store (REST structure, OI and the aux publish stubbed; no broker call) ──
    opts = []
    for k in STRIKES:
        for cp, ot in (("C", OC.OptionType.CALL), ("P", OC.OptionType.PUT)):
            opts.append(types.SimpleNamespace(symbol=f"QQQ   261105{cp}00{int(k)}000", option_type=ot,
                                              strike_price=Decimal(str(k)), streamer_symbol=_sym(cp, k),
                                              settlement_type="PM"))
    OC.get_session = lambda *a, **k: None
    import data.open_interest as _OI
    _OI.fetch_open_interest = lambda *a, **k: {}
    try:
        import analysis.tenor_publish as _TP
        _TP.publish_aux_tenors = lambda *a, **k: {}
    except Exception:                                           # noqa: BLE001
        pass
    fetcher = OC.OptionsChainFetcher()
    fetcher._get_chain_structure = lambda session, symbol: {DAY: list(opts)}
    fetcher._published_at = 0.0
    OC._chain_fetcher = fetcher
    for _n in ("_fetcher", "_FETCHER", "_instance"):
        if hasattr(OC, _n):
            setattr(OC, _n, fetcher)
    _real_gcf = OC.get_chain_fetcher
    OC.get_chain_fetcher = lambda: fetcher

    def build(call_mid=None, at=None):
        """(chain, t_before, t_after, rows) — a fresh store snapshot then the real fetch_chain."""
        now = time.time()
        rows = _snapshot(0.0, now, 2.0 if call_mid is None else call_mid)
        _feed_reset(FEED)
        _feed_write(FEED, rows)
        fetcher._db_ro = None
        if at is not None:
            pin.set(at)
        try:
            t0 = time.time()
            ch = fetcher.fetch_chain("QQQ")
            t1 = time.time()
        finally:
            if at is not None:
                pin.unset()
        return ch, t0, t1, rows, now

    # ── T1 the chain read ────────────────────────────────────────────────────
    ok1, d1 = False, ""
    try:
        ch, t0, t1, rows, now = build(at=datetime(2026, 11, 5, 10, 0, 5, tzinfo=ET))
        rd = float(getattr(ch, "marks_read_epoch", 0.0) or 0.0)
        sd = float(getattr(ch, "marks_store_epoch", 0.0) or 0.0)
        fresh = [r[4] for r in rows if r[4] >= now - STALE]
        qs = [float(c.quote_epoch) for c in ch.calls + ch.puts]
        ok1 = (ch is not None and t0 <= rd <= t1 and abs(sd - max(fresh)) < 1e-6 and rd >= sd
               and rd - sd <= STALE and all(0 < q <= sd for q in qs) and len(qs) == 10)
        d1 = f"read={rd - now:+.3f} store={sd - now:+.3f} want_store={max(fresh) - now:+.3f} n={len(qs)}"
    except Exception as exc:                                    # noqa: BLE001
        d1 = f"{type(exc).__name__}: {exc}"
    check("T1 the real chain read: marks_read_epoch inside the call, marks_store_epoch = the newest updated_epoch the "
          "SELECT returned (stale excluded); read >= store, within OT_CHAIN_STALE_S; every quote_epoch <= store", ok1, d1)

    # ── T2 main_loop wiring (AST) ────────────────────────────────────────────
    ok2, d2 = False, ""
    try:
        src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
        fn = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef) and n.name == "main_loop")
        lines = src.splitlines()
        body = lines[fn.lineno - 1:fn.end_lineno]

        def first(pred, start=0):
            for i in range(start, len(body)):
                if pred(body[i].strip()):
                    return i
            return -1
        i_ts = first(lambda s: s.startswith("tick_start") and "= time.time()" in s)
        i_beg = first(lambda s: "tick_reads.begin(tick_start)" in s)
        i_fetch = first(lambda s: "fetch_chain()" in s)
        i_gex = first(lambda s: s.startswith("_gex_chain = get_chain_fetcher().fetch_chain()"))
        i_rd = first(lambda s: "tick_reads.chain_read(_gex_chain)" in s)
        i_ra = first(lambda s: "run_analysis(state, chain=_gex_chain)" in s)
        ok2 = (0 <= i_ts < i_beg < i_fetch and i_beg - i_ts <= 8 and 0 <= i_gex < i_rd < i_ra)
        d2 = f"tick_start={i_ts} begin={i_beg} first_fetch={i_fetch} gex={i_gex} chain_read={i_rd} run_analysis={i_ra}"
    except Exception as exc:                                    # noqa: BLE001
        d2 = f"{type(exc).__name__}: {exc}"
    check("T2 main_loop: tick_reads.begin(tick_start) at the top of the tick (before any chain fetch); "
          "tick_reads.chain_read(_gex_chain) after the pre-analysis fetch, before run_analysis", ok2, d2)

    # ── T3 plan_tick rows ────────────────────────────────────────────────────
    st = get_derived_store()
    P.bind_store(st)
    P.ensure_tables(st)
    from data.options_chain import OptionContract

    def cols(store, table="plan_tick"):
        return [r[1] for r in store.conn.execute(f"PRAGMA table_info({table})").fetchall()]

    def row(strategy, store=None):
        store = store or st
        c = cols(store)
        r = store.conn.execute(f"SELECT * FROM plan_tick WHERE strategy=? ORDER BY rowid DESC LIMIT 1",
                               (strategy,)).fetchone()
        return dict(zip(c, r)) if r else {}

    sane_rows = []
    ok3, d3 = False, ""
    try:
        c0 = cols(st)
        T_A = (1_800_000_000.0, 1_800_000_000.4, 1_800_000_000.1)   # tick A: start, read, store
        T_B = (1_800_000_015.0, 1_800_000_015.3, 1_800_000_014.9)
        if TR is not None:
            TR.begin(T_A[0])
            TR.chain_read(types.SimpleNamespace(marks_read_epoch=T_A[1], marks_store_epoch=T_A[2]))
        P.begin_tick(T_A[1] + 0.2)
        pa, pb, pc = P.Plan("TickProbeA", ("x",)), P.Plan("TickProbeB", ("x",)), P.Plan("TickProbeC", ("x",))
        ta = pa.tick(600.0)
        ta.check("x", 1.0, False)
        ta.refuse("x", "probe decline")
        sig = OptionsSignal(strategy_name="TickProbeB", setup_type="orb_long", option_side="call", strike=601.0,
                            entry_premium=2.0, underlying_entry=600.0,
                            contract=OptionContract(symbol="QQQ   261105C00601000", strike=601.0, mark=2.0,
                                                    bid=1.98, ask=2.02, quote_epoch=T_A[2] - 0.6))
        tb = pb.tick(600.0)
        tb.check("x", 1.0, True)
        tb.take(sig)
        P.skipped("TickProbeC", "probe inactive", gate="window")
        if TR is not None:                                       # tick B: close_tick writes C's row for tick A
            TR.begin(T_B[0])
            TR.chain_read(types.SimpleNamespace(marks_read_epoch=T_B[1], marks_store_epoch=T_B[2]))
        P.close_tick(st, P._symbol())
        P.begin_tick(T_B[1] + 0.2)
        ra, rb, rc = row("TickProbeA"), row("TickProbeB"), row("TickProbeC")
        c1 = cols(st)

        def tt(r):
            return (r.get("tick_start_epoch"), r.get("marks_read_epoch"), r.get("marks_store_epoch"))
        # a pre-r147 store (the r177/r197 shape) migrates in place
        old = types.SimpleNamespace(conn=sqlite3.connect(":memory:"))
        old.commit = old.conn.commit
        old.conn.execute("CREATE TABLE plan_tick (ts_epoch REAL NOT NULL, symbol TEXT NOT NULL, strategy TEXT NOT NULL,"
                         " verdict TEXT NOT NULL, reason TEXT, trigger_price REAL, invalidation REAL, underlying REAL,"
                         " dist_to_trigger REAL, r_now REAL, direction TEXT NOT NULL DEFAULT '', tick_id INTEGER"
                         " DEFAULT 0, PRIMARY KEY (ts_epoch, symbol, strategy, direction))")
        old.conn.execute("INSERT INTO plan_tick (ts_epoch, symbol, strategy, verdict) VALUES (1.0,'QQQ','Old','HOLD')")
        old.commit()
        P.bind_store(old)
        to = P.Plan("TickProbeMig", ("x",)).tick(600.0)
        to.hold("migrated")
        P.bind_store(st)
        rm_old, rm_new = row("Old", old), row("TickProbeMig", old)
        ok3 = (c1[:len(R146_PLAN_TICK)] == R146_PLAN_TICK and c1[len(R146_PLAN_TICK):] == NEW_COLS
               and tt(ra) == T_A and ra.get("quote_epoch") is None
               and tt(rb) == T_A and rb.get("verdict") == "TAKE" and abs((rb.get("quote_epoch") or 0) - (T_A[2] - 0.6)) < 1e-6
               and tt(rc) == T_A and rc.get("verdict") == "INACTIVE"
               and all(k in rm_old and rm_old[k] is None for k in NEW_COLS) and tt(rm_new) == T_B)
        d3 = (f"cols={c1[len(R146_PLAN_TICK) - 1:]} A={tt(ra)},{ra.get('quote_epoch')} B={tt(rb)},{rb.get('verdict')},"
              f"{rb.get('quote_epoch')} C={tt(rc)},{rc.get('verdict')} old={ {k: rm_old.get(k, '-') for k in NEW_COLS} } "
              f"mig={tt(rm_new)}")
        sane_rows += [r for r in (ra, rb, rc) if r]
    except Exception as exc:                                    # noqa: BLE001
        d3 = f"{type(exc).__name__}: {exc}"
        P.bind_store(st)
    check("T3 plan_tick: four trailing columns after the unchanged r146 columns; DECLINE / TAKE / a close_tick INACTIVE "
          "row carry their own tick's times; TAKE carries the fired contract's quote_epoch; a pre-r147 store migrates "
          "(old rows NULL)", ok3, d3)

    # ── T4 the /manage row (real PositionManager, paper) ─────────────────────
    XE.is_hard_close_time = lambda *a, **k: False

    class _TL:
        def __init__(self, recs):
            self.exits, self.trails, self.recs = [], [], recs

        def update_current_premium(self, *a, **k): pass
        def update_trail_stop(self, tid, v, *a, **k): self.trails.append(round(float(v), 4))
        def set_exit_contract(self, *a, **k): return True
        def get_open_trades(self): return list(self.recs)
        def get_open_trades_live(self): return list(self.recs)

        def log_exit(self, **k):
            self.exits.append((k.get("trade_id"), round(float(k.get("exit_price") or 0), 4), k.get("exit_reason")))
            self.recs[:] = [x for x in self.recs if x.get("trade_id") != k.get("trade_id")]

    class _Alert:
        def __getattr__(self, n):
            return lambda *a, **k: True
    PM.get_alert_manager = lambda: _Alert()
    PM.get_client = lambda: object()

    def runaway(tid, strategy="RunawayContinuation"):
        return {"trade_id": tid, "strategy": strategy, "symbol": "QQQ", "direction": "long",
                "option_side": "call", "strike": 601.0, "entry_premium": 2.00, "stop_premium": 1.60,
                "target_premium": 0.0, "trail_stop": 0.0, "trail_activation": 2.50, "underlying_entry": 600.0,
                "underlying_stop": 0.0,
                "contracts": 3, "is_butterfly": 0, "option_symbol": "QQQ   261105C00601000",
                "expiry": "2026-11-05", "current_premium": 2.0, "entry_time": "2026-11-05T15:00:00+00:00",
                "status": "open"}

    def manage_path(tid, mids, h0=10, m0=1, strategy="RunawayContinuation"):
        """Manage one record over `mids` (one tick each, 15 s apart from h0:m0:05). Returns (tl, ticks)."""
        rec = runaway(tid, strategy)
        tl = _TL([rec])
        p = PM.PositionManager(paper_trading=True)
        p._trade_logger = tl
        p._open_records = [rec]
        ticks = []
        for i, mid in enumerate(mids):
            if not tl.recs:
                break
            sec = (m0 * 60 + 5 + 15 * i)
            at = datetime(2026, 11, 5, h0 + sec // 3600, (sec // 60) % 60, sec % 60, tzinfo=ET)
            ts0 = time.time()
            if TR is not None:
                TR.begin(ts0)
            ch, _a, _b, _rows, _now = build(mid, at)
            if TR is not None:
                TR.chain_read(ch)
            P.begin_tick(time.time())
            pin.set(at)
            try:
                p.manage_open_position(chain=ch)
            finally:
                pin.unset()
            c601 = next((c for c in ch.calls if c.strike == 601.0), None)
            ticks.append((ts0, ch, c601))
        return tl, ticks

    ok4, d4 = False, ""
    try:
        tl4, ticks4 = manage_path("tick-t4", [2.10, 2.20])
        r4 = row("RunawayContinuation/manage")
        ts0, ch4, c4 = ticks4[-1]
        ok4 = (bool(r4) and c4 is not None and r4.get("quote_epoch") is not None
               and abs(r4["quote_epoch"] - float(c4.quote_epoch)) < 1e-6
               and abs((r4.get("marks_read_epoch") or 0) - float(ch4.marks_read_epoch)) < 1e-6
               and abs((r4.get("marks_store_epoch") or 0) - float(ch4.marks_store_epoch)) < 1e-6
               and abs((r4.get("tick_start_epoch") or 0) - ts0) < 1e-6)
        d4 = f"row={ {k: r4.get(k) for k in NEW_COLS + ['verdict']} } contract_q={getattr(c4, 'quote_epoch', None)}"
        if r4:
            sane_rows.append(r4)
    except Exception as exc:                                    # noqa: BLE001
        d4 = f"{type(exc).__name__}: {exc}"
    check("T4 /manage: the real PositionManager's RunawayContinuation/manage row carries the priced contract's "
          "quote_epoch and the tick's start, read and store times", ok4, d4)

    # ── T5 signal_journal through main._execute_entry_signal ─────────────────
    ok5, d5 = False, ""
    sj_rows = []
    try:
        SJ._OUT_ROOT = os.environ["OT_SIGNAL_JOURNAL_DIR"]
        ch5, _a, _b, _r, _n = build(2.0, datetime(2026, 11, 5, 10, 5, 0, tzinfo=ET))
        if TR is not None:
            TR.begin(time.time() - 0.5)
            TR.chain_read(ch5)
        c5 = next(c for c in ch5.calls if c.strike == 601.0)

        def sig5(prem=2.0, valid=True):
            s = OptionsSignal(strategy_name="RunawayContinuation", setup_type="orb_long", direction="long",
                              option_side="call", strike=601.0, entry_premium=prem, underlying_entry=600.0,
                              underlying_stop=598.0, stop_loss_pct=0.2, contract=c5)
            if not valid:
                s.entry_premium = 0.0
            return s

        class _Spy:
            def __init__(self, rec=None):
                self.rec = rec

            def enter(self, signal=None, sizing=None, **kw):
                return self.rec

        class _State:
            paper_trading = True
            tick_count = 1

        saved = {n: getattr(MN, n) for n in ("get_entry_engine", "get_position_manager", "get_alert_manager",
                                              "_capture_entry_snapshot", "_capture_fire_snapshot",
                                              "_capture_entry_contract", "get_risk_manager")}

        def funnel(sg, rec=None, risk=None):
            MN.get_entry_engine = lambda *a, **kw: _Spy(rec)
            MN.get_position_manager = lambda *a, **kw: types.SimpleNamespace(
                has_open_position=lambda: False, add_open_position=lambda r: None, set_open_position=lambda r: None)
            MN.get_alert_manager = lambda: _Alert()
            MN._capture_entry_snapshot = lambda *a, **k: True
            MN._capture_fire_snapshot = lambda *a, **k: None
            MN._capture_entry_contract = lambda *a, **k: None
            if risk is not None:
                MN.get_risk_manager = lambda: risk
            pin.set(datetime(2026, 11, 5, 10, 5, 5, tzinfo=ET))
            try:
                MN._execute_entry_signal(sg, {"price": 600.0, "chain": ch5,
                                              "macro": types.SimpleNamespace(butterfly_half_size=False)},
                                         None, _State(), SJ, additive=True)
            finally:
                pin.unset()
                for n, v in saved.items():
                    setattr(MN, n, v)

        funnel(sig5(valid=False))                                # invalid_signal
        funnel(sig5(prem=900.0))                                 # sizing_rejected (one contract is past the budget)
        funnel(sig5(), rec={"trade_id": "tick-t5", "strategy": "RunawayContinuation"})   # fired
        for f in sorted(glob.glob(os.path.join(os.environ["OT_SIGNAL_JOURNAL_DIR"], "*", "*.jsonl"))):
            for ln in open(f, encoding="utf-8"):
                try:
                    j = json.loads(ln)
                except ValueError:
                    continue
                if j.get("event") == "disposition":
                    sj_rows.append(j)
        want = TR.latest() if TR is not None else {"x": 1}
        by = {}
        for j in sj_rows:
            by.setdefault(j.get("outcome"), j)
        got = {}
        for oc in ("invalid_signal", "sizing_rejected", "fired"):
            j = by.get(oc) or {}
            cq = (((j.get("signal") or {}).get("contract")) or {}).get("quote_epoch")
            got[oc] = (j.get("tick_reads") == want, cq is not None and abs(cq - round(float(c5.quote_epoch), 3)) < 1e-6)
        ok5 = all(a and b for a, b in got.values())
        d5 = f"outcomes={sorted(by)} got={got}"
    except Exception as exc:                                    # noqa: BLE001
        d5 = f"{type(exc).__name__}: {exc}"
    check("T5 signal_journal: invalid_signal, sizing_rejected and fired dispositions (through _execute_entry_signal) "
          "carry tick_reads and signal.contract.quote_epoch", ok5, d5)

    # ── T6 sane values ───────────────────────────────────────────────────────
    ok6, bad, n6 = True, [], 0
    for r in sane_rows + [dict(j.get("tick_reads") or {}, quote_epoch=(((j.get("signal") or {}).get("contract"))
                                                                      or {}).get("quote_epoch")) for j in sj_rows]:
        s, rd, sd, q = (r.get("tick_start_epoch"), r.get("marks_read_epoch"), r.get("marks_store_epoch"),
                        r.get("quote_epoch"))
        if None in (s, rd, sd):
            bad.append(("missing", s, rd, sd))
            continue
        n6 += 1
        if not (s <= rd and sd <= rd and rd - sd <= STALE and (q is None or q <= sd + 1e-3)):
            bad.append((s, rd, sd, q))
    ok6 = not bad and n6 >= 6
    check("T6 sane values on every row carrying them: start <= read, store <= read, read - store within "
          "OT_CHAIN_STALE_S, quote <= store", ok6, f"n={n6} bad={bad[:3]}")

    # ── T7 zero broker calls, no knob ────────────────────────────────────────
    ok7, d7 = False, ""
    try:
        trs = open(os.path.join(ROOT, "utils", "tick_reads.py"), encoding="utf-8").read()
        tree = ast.parse(trs)
        imps = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imps |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                imps.add((n.module or "").split(".")[0])
        code = ast.unparse(tree)
        cfg = open(os.path.join(ROOT, "config.py"), encoding="utf-8").read()
        oc = open(os.path.join(ROOT, "data", "options_chain.py"), encoding="utf-8").read()
        n_exec = oc.count(".execute(")
        ok7 = (imps <= {"__future__", "typing"} and "environ" not in code and "open(" not in code
               and "TICK_READ" not in cfg and "tick_reads" not in cfg and n_exec == R146_SQL_EXECUTES)
        d7 = f"imports={sorted(imps)} cfg_key={'TICK_READ' in cfg} options_chain .execute( count={n_exec}"
    except Exception as exc:                                    # noqa: BLE001
        d7 = f"{type(exc).__name__}: {exc}"
    check("T7 zero broker calls, no knob: utils/tick_reads imports only typing (no env, no file, no config); no config "
          "key; data/options_chain.py's SQL statement count is r146's (no second read)", ok7, d7)

    # ── T8 decisions byte-identical ──────────────────────────────────────────
    h = hashlib.sha256()
    parts = {}
    try:
        # (a) the chain the real fetcher builds, six snapshots
        ha = hashlib.sha256()
        for i, mid in enumerate((2.0, 2.3, 1.7, 0.04, 3.1, 2.0)):
            ch, _a, _b, _r, now = build(mid, datetime(2026, 11, 5, 10, 10 + i, 5, tzinfo=ET))
            ha.update(repr((None if ch is None else
                            (ch.expiry, ch.spot_price,
                             [(c.option_type, c.strike, c.bid, c.ask, round(c.mark, 6), c.delta, c.gamma, c.theta,
                               c.vega, c.iv, round(float(c.quote_epoch) - now, 3)) for c in ch.calls + ch.puts]))
                           ).encode())
        parts["chain"] = ha.hexdigest()[:16]

        # (b) attempt_new_entry + enter() every minute (r146 R8's harness)
        class _MS:
            adx, trend_direction, structure_sequence = 20.0, "NEUTRAL", ""

        class _Ch:
            calls, puts, spot = [], [], 600.0

        def drive(dt):
            asked, skips = [], []
            saved = {n: getattr(MN, n) for n in ("_attempt_park", "_attempt_ogap", "_attempt_hunt",
                                                 "_safe_strategy", "_plan_skip_all", "_plan_skip",
                                                 "get_chain_fetcher")}
            MN._attempt_park = lambda ctx, ms, state, chain=None: asked.append(("PARK", chain is not None))
            MN._attempt_ogap = lambda ctx, ms, state, chain=None: asked.append(("OGAP", chain is not None))
            MN._attempt_hunt = lambda ctx, ms, state, **k: asked.append(("LiquidityHunt", k.get("chain") is not None))
            MN._safe_strategy = lambda name, fn, ctx=None: (asked.append((name, True)), None)[1]
            MN._plan_skip_all = lambda reason, gate="": skips.append(("*", gate))
            MN._plan_skip = lambda name, reason, gate="": skips.append((name, gate))

            def _no_fetch():
                raise AssertionError("a chain fetch")
            MN.get_chain_fetcher = _no_fetch
            stt = MN.BotState()
            stt.paper_trading = True
            err = ""
            pin.set(dt)
            try:
                MN.attempt_new_entry({"price": 600.0, "chain": _Ch(), "macro": {}, "symbol": "QQQ"}, _MS(), stt)
            except Exception as e:                              # noqa: BLE001
                err = f"{type(e).__name__}: {e}"
            finally:
                pin.unset()
                for n, v in saved.items():
                    setattr(MN, n, v)
            return asked, sorted(set(skips)), err

        class _Trip(Exception):
            pass

        class _Boom:
            def __getattr__(self, k):
                raise _Trip(k)

        class _Sizing:
            allowed, contracts, total_cost = True, 1, 85.0
        esig = OptionsSignal(strategy_name="RunawayContinuation", setup_type="orb_long", option_side="call",
                             strike=601.0, entry_premium=0.85, underlying_entry=600.0,
                             contract=OptionContract(symbol="QQQ   261105C00601000", strike=601.0, mark=0.85))
        eng = EE.EntryEngine(paper_trading=True)
        eng._trade_logger = _Boom()
        s_gs, s_ga = EE.get_session, EE.get_account
        EE.get_session = lambda *a, **k: (_ for _ in ()).throw(_Trip("session"))
        EE.get_account = lambda *a, **k: (_ for _ in ()).throw(_Trip("account"))
        hb = hashlib.sha256()
        n_asked = 0
        try:
            for mins in range(9 * 60 + 30, 15 * 60 + 45):
                dt = datetime(2026, 11, 5, mins // 60, mins % 60, 5, tzinfo=ET)
                a, s, e = drive(dt)
                n_asked += len(a)
                hb.update(repr((dt.strftime("%H:%M"), a, s, e)).encode())
            for mins in range(9 * 60 + 30, 16 * 60):
                dt = datetime(2026, 11, 5, mins // 60, mins % 60, 30, tzinfo=ET)
                pin.set(dt)
                try:
                    out = "refused" if eng.enter(esig, _Sizing()) is None else "booked"
                except _Trip as t:
                    out = f"reached:{t}"
                except Exception as e:                          # noqa: BLE001
                    out = f"err:{type(e).__name__}"
                finally:
                    pin.unset()
                hb.update(repr((dt.strftime("%H:%M"), out)).encode())
        finally:
            EE.get_session, EE.get_account = s_gs, s_ga
        parts["entry"] = hb.hexdigest()[:16] if n_asked > 0 else "none-asked"

        # (c) a paper Runaway managed over a 44-tick mark path read from the store
        path = [2.0 + 0.08 * i for i in range(20)] + [3.52 - 0.1 * i for i in range(24)]
        tl8, ticks8 = manage_path("tick-t8", path, h0=10, m0=20)
        tl8h, ticks8h = manage_path("tick-t8h", path, h0=11, m0=20, strategy="LiquidityHunt")
        parts["exit"] = hashlib.sha256(repr((tl8.trails, tl8.exits, len(ticks8), tl8h.trails, tl8h.exits,
                                             len(ticks8h))).encode()).hexdigest()[:16]

        # (d) the pre-r147 columns of every plan_tick row written above (the probes and the /manage rows)
        q = ("SELECT strategy, verdict, reason, trigger_price, invalidation, underlying, dist_to_trigger, r_now,"
             " direction FROM plan_tick WHERE strategy LIKE 'TickProbe%' OR strategy LIKE '%/manage' ORDER BY rowid")
        parts["rows"] = hashlib.sha256(repr(st.conn.execute(q).fetchall()).encode()).hexdigest()[:16]
        for k in ("chain", "entry", "exit", "rows"):
            h.update(parts[k].encode())
        dg = h.hexdigest()[:16]
        ok8 = dg == REPLAY_DIGEST and "none" not in parts["entry"] and bool(tl8.exits) and bool(tl8h.exits)
        d8 = f"digest={dg} want={REPLAY_DIGEST} parts={parts} exits={tl8.exits + tl8h.exits} trails={len(tl8h.trails)}"
    except Exception as exc:                                    # noqa: BLE001
        ok8, d8 = False, f"{type(exc).__name__}: {exc} parts={parts}"
    print(f"       ({d8})")
    check("T8 DECISIONS BYTE-IDENTICAL: the chain, entry, exit and plan-row replay digest is r146's", ok8, d8)

    OC.get_chain_fetcher = _real_gcf
    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
