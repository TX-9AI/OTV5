#!/usr/bin/env python3
"""
tests/check_hunt_ogap_retired.py  v5.1
v5.1  2026-11-25  OTV5 r160 (BOXF.5) — DEFAULT BOX FLAGS: deploy/box_flags/QQQ reads `park = off` (the
      operator 2026-11-25: QQQ is a cash box from Mon 2026-11-30, Runaway only), so this run pins utils/box_flags._EFFECTIVE
      to a missing file (DEFAULTS) at import, in T1's fresh interpreters and again after T2's BF.reset(), as
      check_park_flag does: the fixture never reads the real deploy/box_flags/<SYM> (T2's scan of the tree's files is
      unchanged). What each check pins is unchanged.
v5.0  2026-11-23  OTV5 r153 (TRIM.2) — new. THE HUNT AND OGAP ARE RETIRED: DORMANT ON EVERY BOX, PAPER OR LIVE, WITH NO
      SWITCH AND NO FLAG. The operator, 2026-11-23: "The hunt & OGAP are trash. Retire them both after this session today.
      And include them in the coming purge. I think we're going to stick with the runaway & park going forward". The
      plan-off step (Breakout's r110 pattern, TRIM.1); their code is kept until the purge (BACKLOG TRIM.2 holds the map).

  T1  NEVER ASKED, ANY BOX, ANY ENV: in fresh interpreters on a PAPER box and on a LIVE box (OT_PAPER_TRADING=False), with
      OT_HUNT unset, "1", "active", "trade" and "on": plan_state reads LiquidityHunt and OGAP DORMANT (TABLE rows
      ("", dormant, hour), default dormant, no switch key); main._safe_strategy calls neither; the [plans] summary says
      "retired (dormant, no switch): LiquidityHunt (r153 TRIM.2), OGAP (r153 TRIM.2)"; the Service line says
      " · hunt=retired (dormant r153)" and " · ogap=retired (dormant r153)", never "ogap=on" or "walled"; Runaway and
      PARK read ACTIVE; plan_state's code reads no OT_HUNT
  T2  NO FLAG TURNS OGAP ON: utils/box_flags.SCHEMA has no `ogap` key; a box file holding `ogap = on` loads with no ogap
      value and the line REFUSED as an unknown key (named on the [flags] start line); with that load frozen as the
      process's flags OGAP still reads DORMANT; no deploy/box_flags file in the tree carries an ogap line
  T3  THE DISPATCH: main.attempt_new_entry every minute 09:30:05-11:10:05 on a pinned Tue 2026-11-24, paper box and live
      box, the real admission table, plan_state, risk manager, plan board (begin_tick / close_tick on a scratch derived
      store) and a scratch trades.db, every strategy's generate_signal a recorder (no signal): the Hunt and OGAP are asked
      0 times and write 0 plan_tick and 0 plan_heartbeat rows; Runaway and PARK are asked and write rows (the positive
      control); Runaway's and PARK's asks and plan skips are BYTE-IDENTICAL to r152 c0cfcbf (digest COUSIN_DIGEST,
      measured there with the same harness)
  T4  NO DOOR LEFT OPEN: main._attempt_hunt returns before it reads the book (get_position_manager not called),
      main._attempt_ogap before its one-per-session read (_one_per_session_used not called), and at a tripped cash cap on
      a live box main._ask_walled_past_cap reads no admission row and fetches no chain for OGAP
  T5  BOOT RECOVERY STILL EXITS: an OPEN LiquidityHunt row and an OPEN OGAP row in trades.db at start on a PAPER box are
      resumed by main._recover_open_position (the box's PositionManager holds both) and closed by its hard close
      (flatten_all at 15:56 ET, paper, at the mark): both rows closed in trades.db, nothing left open; on a LIVE box an
      OPEN walled OGAP paper row is resumed by execution/paper_wall.recover() (returns 1) and closed by the wall book's
      hard close; recover() with no walled row returns 0 and main._paper_wall_pass returns quietly
Born red on r152 (c0cfcbf) at T1, T2, T3 and T4 (the Hunt and OGAP active and asked; the `ogap` schema key); T5 is green
on both trees and pins what must not move (an open row is never orphaned). Revert mutants red: see the land spec (TRIM.2).
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
Run:  python3 tests/check_hunt_ogap_retired.py
"""
import hashlib
import json
import logging
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["OT_INSTRUMENT"] = "QQQ"
import tempfile as _r160_tf  # noqa: E402
from utils import box_flags as _r160_bf  # noqa: E402  r160 (BOXF.5): DEFAULT box flags, never this box's real file
_r160_bf._EFFECTIVE["flags"] = _r160_bf.load(os.environ.get("OT_INSTRUMENT", "QQQ"),
                                             path=os.path.join(_r160_tf.mkdtemp(), "NO_FLAGS"))
_TD = tempfile.mkdtemp(prefix="check_hunt_ogap_retired_")
for _k, _f in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"),
               ("OT_LOG_FILE", "bot.log"), ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_COUNTERFACTUAL_DIR", "cf"),
               ("OT_ALERT_SPOOL", "alert_spool.jsonl"), ("OT_PLAN_STATES_FILE", "plan_states.json"),
               ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT"), ("OT_WAREHOUSE_STATE", "ws")):
    os.environ[_k] = os.path.join(_TD, _f)
for _k in ("OT_DAILY_LOSS_LIMIT", "OT_PAPER_TRADING", "OT_HUNT", "OT_RUNAWAY", "OT_PARK", "OT_BROKER_RECONCILE"):
    os.environ.pop(_k, None)
os.environ["OT_RISK_USD"] = "1050"
ET = ZoneInfo("America/New_York")
RETIRED = ("LiquidityHunt", "OGAP")
COUSINS = ("RunawayContinuation", "PARK")
COUSIN_DIGEST = "9260773992ebcca2"          # T3: Runaway / PARK asks + skips, paper and live, measured on r152 c0cfcbf
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


PROBE = r'''
import json, os, sys
sys.path.insert(0, %(root)r)
import tempfile
from utils import box_flags as BF   # r160 (BOXF.5): DEFAULT box flags, never this box's real deploy/box_flags file
BF._EFFECTIVE["flags"] = BF.load("QQQ", path=os.path.join(tempfile.mkdtemp(), "NO_FLAGS"))
import config
from strategy import plan_state as S
import main as MN
asked = []
MN._admission_allows = lambda name: True
for n in ("LiquidityHunt", "OGAP", "RunawayContinuation", "PARK"):
    MN._safe_strategy(n, lambda _n=n: asked.append(_n))
print(json.dumps({"paper": config.PAPER_TRADING,
                  "state": {n: S.state(n) for n in ("LiquidityHunt", "OGAP", "RunawayContinuation", "PARK")},
                  "rows": {n: list(S.TABLE.get(n, ())) for n in ("LiquidityHunt", "OGAP")},
                  "default": {n: S.default(n) for n in ("LiquidityHunt", "OGAP")},
                  "switch": {n: S.switch(n) for n in ("LiquidityHunt", "OGAP")},
                  "summary": S.summary(), "asked": asked, "banner": MN._banner_dials()}))
'''


def probe(paper: bool, hunt_env=None):
    env = {k: v for k, v in os.environ.items()}
    env["OT_PAPER_TRADING"] = "True" if paper else "False"
    if hunt_env is not None:
        env["OT_HUNT"] = hunt_env
    r = subprocess.run([sys.executable, "-c", PROBE % {"root": ROOT}], capture_output=True, text=True,
                       timeout=300, env=env, cwd=ROOT)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:                                           # noqa: BLE001
        return {"err": (r.stderr or r.stdout)[-400:]}


def main():
    print("check_hunt_ogap_retired")
    try:
        import pandas  # noqa: F401
        import config  # noqa: F401
        import main as MN
        import utils.time_utils as TU
        import database.trade_logger as TL
        from database.trade_logger import make_record
        import execution.position_manager as PMM
        import execution.exit_engine as EE
        import risk.risk_manager as RM
        import strategy.management as MG
        from strategy import plan as P
        from strategy import plan_state as PS
        from utils import box_flags as BF
        from data.derived_store import get_derived_store
        from analysis.orb_engine import get_orb_engine
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN: imports failed ({type(exc).__name__}: {exc})")
        return 2
    PW = getattr(MN, "_paper_wall", None)
    for _h in logging.getLogger().handlers:
        if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
            _h.setLevel(logging.CRITICAL + 1)

    # ── T1 the states, every box, every OT_HUNT ─────────────────────────────
    ok1, d1 = True, []
    want_sum = "retired (dormant, no switch): LiquidityHunt (r153 TRIM.2), OGAP (r153 TRIM.2)"
    for paper in (True, False):
        for he in (None, "1", "active", "trade", "on"):
            g = probe(paper, he)
            good = ("err" not in g and g.get("paper") is paper
                    and g["state"] == {"LiquidityHunt": "dormant", "OGAP": "dormant",
                                       "RunawayContinuation": "active", "PARK": "active"}
                    and g["rows"] == {"LiquidityHunt": ["", "dormant", "hour"], "OGAP": ["", "dormant", "hour"]}
                    and g["default"] == {"LiquidityHunt": "dormant", "OGAP": "dormant"}
                    and g["switch"] == {"LiquidityHunt": "", "OGAP": ""}
                    and want_sum in g["summary"] and sorted(g["asked"]) == sorted(COUSINS)
                    and " · hunt=retired (dormant r153)" in g["banner"]
                    and " · ogap=retired (dormant r153)" in g["banner"]
                    and "ogap=on" not in g["banner"] and "walled" not in g["banner"])
            if not good:
                ok1 = False
                d1.append({"paper": paper, "OT_HUNT": he,
                           **({k: v for k, v in g.items() if k != "banner"} if "err" not in g else g),
                           "banner_tail": g.get("banner", "")[-200:]})
    ps_code = open(os.path.join(ROOT, "strategy", "plan_state.py"), encoding="utf-8").read().split('"""', 2)[-1]
    reads_hunt = 'os.environ.get("OT_HUNT"' in ps_code
    check("T1 the Hunt and OGAP are DORMANT on a paper and a live box under every OT_HUNT value, never asked, named "
          "retired on the [plans] line and the Service line; Runaway and PARK ACTIVE; plan_state reads no OT_HUNT",
          ok1 and not reads_hunt, f"reads OT_HUNT={reads_hunt} {json.dumps(d1)[:1500]}")

    # ── T2 the flag ─────────────────────────────────────────────────────────
    ok2, d2 = False, ""
    try:
        td = tempfile.mkdtemp(prefix="t2_", dir=_TD)
        p = os.path.join(td, "QQQ")
        open(p, "w").write("ogap = on  # turn it back on\n")
        f = BF.load("QQQ", path=p)
        line = BF.start_line(f, "c0ffee0000")
        BF._EFFECTIVE["flags"] = f
        try:
            st_on = PS.state("OGAP")
        finally:
            BF.reset()
            BF._EFFECTIVE["flags"] = BF.load("QQQ", path=os.path.join(_TD, "NO_FLAGS"))   # r160: back to DEFAULTS
        lines_in_tree = []
        for sym in BF.files():
            txt = open(BF.path_for(sym), encoding="utf-8").read()
            if any(ln.split("#")[0].strip().startswith("ogap") for ln in txt.splitlines()):
                lines_in_tree.append(sym)
        ok2 = ("ogap" not in BF.SCHEMA and "ogap" not in f.values
               and any("unknown key 'ogap'" in x for x in f.problems) and " · REFUSED: " in line
               and st_on == "dormant" and not lines_in_tree)
        d2 = (f"schema={sorted(BF.SCHEMA)} values={f.values} problems={f.problems} line={line[-200:]} state={st_on} "
              f"tree_files_with_ogap={lines_in_tree}")
    except Exception as exc:                                    # noqa: BLE001
        d2 = f"{type(exc).__name__}: {exc}"
    check("T2 no flag turns OGAP on: no `ogap` schema key; an `ogap = on` line is REFUSED (unknown key, named) and OGAP "
          "stays DORMANT; no box file in the tree carries one", ok2, d2)

    # ── clocks / alerts / stores ────────────────────────────────────────────
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

    def unpin(h):
        sw, dts = h
        for m, n in sw:
            setattr(m, n, real[n])
        for m in dts:
            m.datetime = datetime

    class _Alerts:
        def __getattr__(self, name):
            if name.startswith("__"):
                raise AttributeError(name)
            return lambda *a, **kw: None
    _al = _Alerts()
    for mod in (MN, PMM):
        mod.get_alert_manager = lambda *a, **k: _al
    import notifications.alert_manager as AM
    AM.get_alert_manager = lambda *a, **k: _al

    def fresh(tag, paper_box=True):
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

    def _scalar(v):
        return v if (v is None or isinstance(v, (bool, int, float, str))) else type(v).__name__

    class _MS:
        adx, trend_direction, structure_sequence = 20.0, "NEUTRAL", ""

    class _Ch:
        calls, puts, spot, expiry = [], [], 600.0, ""

    # ── T3 the dispatch ─────────────────────────────────────────────────────
    store = get_derived_store()
    P.bind_store(store)
    P.ensure_tables(store)
    dc = store.conn

    def world(tag, paper_box):
        fresh("w_" + tag, paper_box)
        dc.execute("DELETE FROM plan_tick")
        dc.execute("DELETE FROM plan_heartbeat")
        store.commit()
        ev, ret = [], []
        saved = {}
        for attr, nm in (("_runaway_strategy", "RunawayContinuation"), ("_liquidity_hunt", "LiquidityHunt"),
                         ("_park_strategy", "PARK"), ("_ogap_strategy", "OGAP"), ("_breakout", "Breakout")):
            obj = getattr(MN, attr)
            saved[attr] = obj.generate_signal

            def fn(_nm=nm, **kw):
                row = ("ask", _nm, MN.now_et().strftime("%H:%M"), sorted((k, _scalar(v)) for k, v in kw.items()))
                (ret if _nm in RETIRED else ev).append(row)
                return None
            obj.generate_signal = fn
        s_skip = MN._plan_skip

        def skip(n, reason, gate=""):
            if n in COUSINS:
                ev.append(("skip", n, MN.now_et().strftime("%H:%M"), gate, reason))
            return s_skip(n, reason, gate)
        MN._plan_skip = skip
        s_pm = MN.get_position_manager
        pm = PMM.PositionManager(paper_trading=paper_box)
        MN.get_position_manager = lambda *a, **k: pm
        eng = get_orb_engine()
        s_hi, s_lo = eng.data.orb_high, eng.data.orb_low
        eng.data.orb_high, eng.data.orb_low = 601.0, 599.0
        st = MN.BotState()
        st.paper_trading = paper_box
        try:
            for i in range(0, 101):
                tot = 9 * 60 + 30 + i
                dt = datetime(2026, 11, 24, tot // 60, tot % 60, 5, tzinfo=ET)
                h = pin(dt)
                try:
                    st.tick_count = i
                    P.begin_tick(dt.timestamp())
                    MN.attempt_new_entry({"price": 600.0, "chain": _Ch(), "macro": {}, "symbol": "QQQ",
                                          "gap": {"prior_close": 598.0}}, _MS(), st)
                    P.close_tick(store, "QQQ")
                finally:
                    unpin(h)
        finally:
            for attr, f in saved.items():
                getattr(MN, attr).generate_signal = f
            MN._plan_skip = s_skip
            MN.get_position_manager = s_pm
            eng.data.orb_high, eng.data.orb_low = s_hi, s_lo
        cnt = {}
        for n in RETIRED + COUSINS:
            a = dc.execute("SELECT COUNT(*) FROM plan_tick WHERE strategy=?", (n,)).fetchone()[0]
            b = dc.execute("SELECT COUNT(*) FROM plan_heartbeat WHERE plan=?", (n,)).fetchone()[0]
            cnt[n] = (a, b)
        return ev, ret, cnt

    ok3, d3 = False, ""
    try:
        e_p, r_p, c_p = world("paper", True)
        e_l, r_l, c_l = world("live", False)
        dg = hashlib.sha256(json.dumps([e_p, e_l], default=str).encode()).hexdigest()[:16]
        print(f"       (T3 cousin digest {dg})")
        asks = {n: sum(1 for e in e_p + e_l if e[0] == "ask" and e[1] == n) for n in COUSINS}
        ok3 = (not r_p and not r_l
               and all(c_p[n] == (0, 0) and c_l[n] == (0, 0) for n in RETIRED)
               and all(c_p[n][0] > 0 and c_l[n][0] > 0 for n in COUSINS) and all(asks.values())
               and dg == COUSIN_DIGEST)
        d3 = (f"retired asks paper/live={len(r_p)}/{len(r_l)} rows(plan_tick, heartbeat) paper={c_p} live={c_l} "
              f"cousin asks={asks} digest={dg} want={COUSIN_DIGEST}")
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d3 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-700:]}"
    check("T3 the dispatch 09:30-11:10, paper and live: the Hunt and OGAP asked 0 times, 0 plan_tick / plan_heartbeat "
          "rows; Runaway and PARK asked and written, byte-identical to r152 (digest pinned)", ok3, d3)

    # ── T4 no door left open ────────────────────────────────────────────────
    ok4, d4 = False, ""
    try:
        fresh("t4", True)
        seen = []
        s_pm, s_one, s_gcf = MN.get_position_manager, MN._one_per_session_used, MN.get_chain_fetcher
        MN.get_position_manager = lambda *a, **k: seen.append("get_position_manager") or s_pm(*a, **k)
        MN._one_per_session_used = lambda s: seen.append("one_per_session:%s" % s) or s_one(s)
        MN.get_chain_fetcher = lambda *a, **k: seen.append("get_chain_fetcher") or s_gcf(*a, **k)

        class _PmSpy:
            def logging_state(self, *a, **k):
                seen.append("logging_state")
                return {}
        st = MN.BotState()
        st.paper_trading = False
        h = pin(datetime(2026, 11, 24, 10, 0, 5, tzinfo=ET))
        try:
            MN._attempt_hunt({"price": 600.0, "chain": _Ch()}, _MS(), st, orb=None, chain=_Ch(), now_hhmm="10:00",
                             atr_pct=0.2)
            MN._attempt_ogap({"price": 600.0, "chain": _Ch()}, _MS(), st, chain=_Ch())
            MN._ask_walled_past_cap({"price": 600.0}, _MS(), st, _PmSpy(), datetime(2026, 11, 24, 10, 0, 5, tzinfo=ET),
                                    None, {})
        finally:
            unpin(h)
            MN.get_position_manager, MN._one_per_session_used, MN.get_chain_fetcher = s_pm, s_one, s_gcf
        ok4 = seen == []
        d4 = f"reached: {seen}"
    except Exception as exc:                                    # noqa: BLE001
        d4 = f"{type(exc).__name__}: {exc}"
    check("T4 _attempt_hunt reads no book, _attempt_ogap no one-per-session row, and the capped live branch no admission "
          "row and no chain for OGAP", ok4, d4)

    # ── T5 boot recovery still exits ────────────────────────────────────────
    def chain_for(expiry, strikes, mark):
        class K:
            def __init__(self, strike, side):
                self.strike, self.expiry = float(strike), expiry
                self.bid, self.ask = round(mark - 0.01, 2), round(mark + 0.01, 2)
                self.mark = mark
                self.delta = 0.5 if side == "C" else -0.5
                self.iv = 0.2
                self.symbol = f"QQQ   {expiry.replace('-', '')[2:]}{side}{int(strike * 1000):08d}"
                self.streamer_symbol = self.symbol

        class C:
            pass
        c = C()
        c.expiry, c.spot_price, c.spot, c.atm_iv = expiry, 600.0, 600.0, 0.2
        c.calls = [K(s, "C") for s in strikes]
        c.puts = [K(s, "P") for s in strikes]
        return c

    def open_row(tid, strategy, side, strike, paper=1):
        k = chain_for("2026-11-24", [strike], 1.0).calls[0] if side == "call" else \
            chain_for("2026-11-24", [strike], 1.0).puts[0]
        rec = make_record(trade_id=tid, strategy=strategy, setup_type=f"{strategy.lower()}_x",
                          direction="long" if side == "call" else "short", option_side=side, strike=float(strike),
                          expiry="2026-11-24", contracts=1, entry_premium=1.0, total_cost=100.0, max_loss=100.0,
                          stop_premium=0.0, underlying_entry=600.0, paper_trade=paper, symbol="QQQ",
                          option_symbol=k.symbol, entry_time="2026-11-24T10:05:00-05:00", status="open")
        TL._trade_logger.log_entry(rec)
        return rec

    def status_of(p):
        c = sqlite3.connect(p)
        out = {r[0]: (r[1], r[2]) for r in c.execute("SELECT trade_id, status, exit_reason FROM trades")}
        c.close()
        return out

    ok5, d5 = False, ""
    try:
        res = {}
        # paper box
        p = fresh("t5_paper", True)
        h = pin(datetime(2026, 11, 24, 9, 31, 0, tzinfo=ET))
        try:
            open_row("hunt-open", "LiquidityHunt", "call", 601)
            open_row("ogap-open", "OGAP", "put", 599)
            PMM._position_manager = None if hasattr(PMM, "_position_manager") else None
            st = MN.BotState()
            st.paper_trading = True
            pm = PMM.PositionManager(paper_trading=True)
            s_pm = MN.get_position_manager
            MN.get_position_manager = lambda *a, **k: pm
            try:
                MN._recover_open_position(st, "test")
            finally:
                MN.get_position_manager = s_pm
            res["paper_resumed"] = sorted(str(r.get("strategy")) for r in pm.get_open_records())
        finally:
            unpin(h)
        h = pin(datetime(2026, 11, 24, 15, 56, 0, tzinfo=ET))
        try:
            failed = pm.flatten_all(reason="test hard close", chain=chain_for("2026-11-24", [599, 601], 0.40),
                                    spot=600.0)
        finally:
            unpin(h)
        res["paper_failed"] = failed
        res["paper_rows"] = status_of(p)
        res["paper_open_after"] = len(pm.get_open_records())
        # live box: the walled OGAP row on the paper wall
        if PW is not None:
            p2 = fresh("t5_live", False)
            h = pin(datetime(2026, 11, 24, 9, 31, 0, tzinfo=ET))
            try:
                res["wall_empty"] = PW.recover()
                st2 = MN.BotState()
                st2.paper_trading = False
                MN._paper_wall_pass({"price": 600.0}, st2)            # no row: returns quietly
                open_row("ogap-wall", "OGAP", "put", 599, paper=1)
                PW.reset()
                res["wall_resumed"] = PW.recover()
                b = PW.book()
            finally:
                unpin(h)
            h = pin(datetime(2026, 11, 24, 15, 56, 0, tzinfo=ET))
            try:
                wf = b.flatten_all(reason="test hard close", chain=chain_for("2026-11-24", [599], 0.40), spot=600.0)
            finally:
                unpin(h)
            res["wall_failed"] = wf
            res["wall_rows"] = status_of(p2)
            res["wall_open_after"] = len(b.get_open_records())
        pr, wr = res.get("paper_rows", {}), res.get("wall_rows", {})
        ok5 = (res["paper_resumed"] == ["LiquidityHunt", "OGAP"] and not res["paper_failed"]
               and pr.get("hunt-open", ("",))[0] == "closed" and pr.get("ogap-open", ("",))[0] == "closed"
               and res["paper_open_after"] == 0
               and (PW is None or (res["wall_empty"] == 0 and res["wall_resumed"] == 1 and not res["wall_failed"]
                                   and wr.get("ogap-wall", ("",))[0] == "closed" and res["wall_open_after"] == 0)))
        d5 = f"{res}"
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d5 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-900:]}"
    check("T5 boot recovery still exits: an open Hunt and an open OGAP row on a paper box are resumed and closed by the "
          "hard close; a walled OGAP row on a live box is resumed by paper_wall.recover and closed on the wall; an empty "
          "wall recovers 0 quietly", ok5, d5)

    if FAILED:
        print(f"RED — {len(FAILED)} failed: {' '.join(FAILED)}")
        return 1
    print("GREEN — the Hunt and OGAP are retired: never asked on any box, no flag or env turns them on, Runaway and PARK "
          "dispatch as on r152, and an open row is still managed to its exit (T1-T5)")
    return 0


if __name__ == "__main__":
    import shutil
    try:
        rc = main()
    finally:
        if _TD.startswith(tempfile.gettempdir()) and os.path.basename(_TD).startswith("check_hunt_ogap_retired_"):
            shutil.rmtree(_TD, ignore_errors=True)
    sys.exit(rc)
