#!/usr/bin/env python3
"""
tests/check_park_flag.py  v5.1
v5.1  2026-11-26  OTV5 r161 (LANE.1) — P1's roster row follows the lanes: SCHEMA["park"] allows on / off / paper_only
      (utils/box_flags.LANES; the operator, 2026-11-25: "I want park paperwalled until we enable it on the cash side").
      Every other check unchanged; paper_only's own behaviour is tests/check_park_paper_wall.py's.
v5.0  2026-11-24  OTV5 r155 (BOXF.2, M4) — new. PARK IS ON OR OFF PER BOX BY ITS BOX FLAG `park`, DECIDED IN ONE PLACE. The
      operator, 2026-11-24: "Yes" (the box-flags design's M4, ~/reviews/design/BOX_FLAGS_20261122/DESIGN.md), so that a
      C5 equity box (Runaway only) can carry `park = off` before it goes live. Default on: with no file line, nothing on
      any box changes.

  P1  THE ROSTER: utils/box_flags.SCHEMA["park"] is (park, PARK, (on, off), default on); strategy/plan_state's PARK row is
      ("", flag, hour) with no switch key, default("PARK") active; config has no PARK_MODE / PARK_ENV_REFUSED; plan_state
      has no PARK special case and main._attempt_park reads no PARK_MODE (one decision point: plan_state)
  P2  OT_PARK IS INERT: in fresh interpreters with no box file (frozen missing), OT_PARK unset, "off", "log", "trade" and
      "yes": PARK reads ACTIVE, main._safe_strategy asks it, the Service line says " · park=trade" with no OT_PARK tail;
      when OT_PARK is set the [flags] start line names "OT_PARK in the unit is IGNORED (deploy/box_flags decides park)"
      (unset: no REFUSED part); no production module (tests/ aside) reads OT_PARK (os.environ.get / getenv / [] / "in")
  P3  `park = off` (a fixture file, frozen as the process's flags): PARK reads DORMANT, the [plans] summary says
      "PARK dormant: box flag park=off", the Service line says " · park=off (box flag)", main._safe_strategy does not ask
      it, Runaway stays ACTIVE; FAIL CLOSED: `park = of`, a duplicate `park` and an unreadable file read DORMANT, each
      named; `park = on` restates the default and reads ACTIVE
  P4  THE DISPATCH (tests/check_hunt_ogap_retired.py T3's harness, unchanged): main.attempt_new_entry every minute
      09:30:05-11:10:05 on a pinned Tue 2026-11-24, paper box and live box. With NO flag file the Runaway / PARK asks and
      skips are BYTE-IDENTICAL to r154 b8f21c1 (digest NOFILE_DIGEST, measured there with this harness); with
      `park = off` PARK is asked 0 times and writes 0 plan_tick / plan_heartbeat rows (the admission loop's refusals
      reach main._plan_skip and the plan board drops them, strategy/plan r303), and Runaway's asks and skips are
      byte-identical to its own events with no file (digest RUNAWAY_DIGEST, also measured on r154)
  P5  NO DOOR LEFT OPEN: with `park = off`, main._attempt_park at 11:01 with no chain reads no one-per-session row, fetches
      no chain and never calls PARK's generate_signal
  P6  AN OPEN PARK ROW STILL EXITS: with `park = off`, an OPEN PARK row in trades.db at start on a paper box is resumed by
      main._recover_open_position and closed by its hard close (flatten_all at 15:56 ET, paper, at the mark)
Born red on r154 (b8f21c1) at P1, P2, P3, P4 (its park = off half) and P5; P6 and P4's no-file digest are green on both
trees and pin what must not move. Revert mutants red: see the land spec (BOXF.2).
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
Run:  python3 tests/check_park_flag.py
"""
import ast
import hashlib
import json
import logging
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["OT_INSTRUMENT"] = "QQQ"
_TD = tempfile.mkdtemp(prefix="check_park_flag_")
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
NOFILE_DIGEST = "9260773992ebcca2"          # P4: Runaway / PARK asks + skips, paper and live, no file; r154 b8f21c1
RUNAWAY_DIGEST = "f55b99f29ce137d9"         # P4: Runaway's asks + skips alone, paper and live, no file; r154 b8f21c1
MISSING = os.path.join(_TD, "no_such_box_file")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _put(name, text):
    p = os.path.join(_TD, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


PROBE = r'''
import json, os, sys
sys.path.insert(0, %(root)r)
from utils import box_flags as BF
BF._EFFECTIVE["flags"] = BF.load("QQQ", path=%(missing)r)
import config
from strategy import plan_state as S
import main as MN
asked = []
MN._admission_allows = lambda name: True
for n in ("RunawayContinuation", "PARK"):
    MN._safe_strategy(n, lambda _n=n: asked.append(_n))
print(json.dumps({"state": S.state("PARK"), "asked": asked, "banner": MN._banner_dials(),
                  "mode": hasattr(config, "PARK_MODE") or hasattr(config, "PARK_ENV_REFUSED"),
                  "flags": BF.start_line(BF.effective(), "c0ffee0000", BF.stale_env()) if hasattr(BF, "stale_env")
                           else BF.start_line(BF.effective(), "c0ffee0000")}))
'''


def probe(park_env=None):
    env = dict(os.environ)
    env.pop("OT_PARK", None)
    if park_env is not None:
        env["OT_PARK"] = park_env
    r = subprocess.run([sys.executable, "-c", PROBE % {"root": ROOT, "missing": MISSING}], capture_output=True,
                       text=True, timeout=300, env=env, cwd=ROOT)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:                                           # noqa: BLE001
        return {"err": (r.stderr or r.stdout)[-400:]}


def _reads_ot_park(src: str) -> list:
    """Line numbers where a module READS OT_PARK: os.environ.get / os.getenv / os.environ[...] / "OT_PARK" in os.environ."""
    out = []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out

    def lit(n):
        return isinstance(n, ast.Constant) and n.value == "OT_PARK"
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and n.args and lit(n.args[0]):
            f = n.func
            if isinstance(f, ast.Attribute) and f.attr in ("get", "getenv", "pop", "setdefault"):
                out.append(n.lineno)
        elif isinstance(n, ast.Subscript) and lit(getattr(n, "slice", None)):
            out.append(n.lineno)
        elif isinstance(n, ast.Compare) and lit(n.left):
            out.append(n.lineno)
    return out


def main():
    print("check_park_flag")
    try:
        import pandas  # noqa: F401
        import config
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
    OFF_FILE = _put("PARK_OFF", "# C5: Runaway only on this box\npark = off  # fixture\n")

    def freeze(path):
        BF.reset()
        BF._EFFECTIVE["flags"] = BF.load("QQQ", path=path)
        return BF._EFFECTIVE["flags"]

    # ── P1 the roster ───────────────────────────────────────────────────────
    k = BF.SCHEMA.get("park")
    ps_src = open(os.path.join(ROOT, "strategy", "plan_state.py"), encoding="utf-8").read().split('"""', 2)[-1]
    mn_src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    ap = mn_src[mn_src.index("def _attempt_park("):]
    ap = ap[:ap.index("\ndef ", 1)]
    freeze(MISSING)
    try:
        dflt = PS.default("PARK")
    finally:
        BF.reset()
    p1 = {"key": k is not None and (k.key, k.setup, tuple(k.allowed), k.default) == ("park", "PARK", ("on", "off", "paper_only"), "on"),
          "row": list(PS.TABLE.get("PARK", ())) == ["", getattr(PS, "FLAG", "flag"), PS.HOUR],
          "default": dflt == PS.ACTIVE, "switch": PS.switch("PARK") == "",
          "config": not hasattr(config, "PARK_MODE") and not hasattr(config, "PARK_ENV_REFUSED"),
          "plan_state": "PARK_MODE" not in ps_src and 'n == "PARK"' not in ps_src,
          "attempt_park": "PARK_MODE" not in ap}
    check("P1 the roster: SCHEMA park (PARK, on/off/paper_only, default on); plan_state PARK row ('', flag, hour), no switch; no "
          "config.PARK_MODE; no second decision point in plan_state or main._attempt_park",
          all(p1.values()), f"{p1} key={k} row={PS.TABLE.get('PARK')}")

    # ── P2 OT_PARK is inert ─────────────────────────────────────────────────
    ok2, d2 = True, []
    for pe in (None, "off", "log", "trade", "yes"):
        g = probe(pe)
        named = "OT_PARK in the unit is IGNORED (deploy/box_flags decides park)" in g.get("flags", "")
        good = ("err" not in g and g["state"] == "active" and g["asked"] == list(COUSINS) and not g["mode"]
                and " · park=trade" in g["banner"] and "OT_PARK=" not in g["banner"]
                and (named if pe is not None else " · REFUSED: " not in g["flags"]))
        if not good:
            ok2 = False
            d2.append({"OT_PARK": pe, **{kk: (v[-160:] if isinstance(v, str) else v) for kk, v in g.items()}})
    readers = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__", "venv", ".venv", "node_modules", "tests")]
        for f in fn:
            if f.endswith(".py"):
                pth = os.path.join(dp, f)
                for ln in _reads_ot_park(open(pth, encoding="utf-8", errors="replace").read()):
                    readers.append(f"{os.path.relpath(pth, ROOT)}:{ln}")
    check("P2 OT_PARK is inert: unset / off / log / trade / yes all read PARK ACTIVE and asked, Service line park=trade, "
          "a set OT_PARK named IGNORED on the [flags] line; no production module reads OT_PARK",
          ok2 and not readers, f"readers={readers} {json.dumps(d2)[:1500]}")

    # ── P3 park = off, and fail closed ──────────────────────────────────────
    ok3, d3 = False, ""
    try:
        res = {}
        for tag, path in (("off", OFF_FILE), ("typo", _put("TYPO", "park = of\n")),
                          ("dup", _put("DUP", "park = on\npark = on\n")), ("on", _put("ON", "park = on\n"))):
            f = freeze(path)
            asked = []
            s_adm = MN._admission_allows
            MN._admission_allows = lambda name: True
            try:
                for n in COUSINS:
                    MN._safe_strategy(n, lambda _n=n: asked.append(_n))
                res[tag] = {"state": PS.state("PARK"), "run": PS.state("RunawayContinuation"), "asked": asked,
                            "summary": PS.summary(), "banner": MN._banner_dials(), "problems": list(f.problems)}
            finally:
                MN._admission_allows = s_adm
                BF.reset()
        os.mkdir(os.path.join(_TD, "UNREAD"))
        f = freeze(os.path.join(_TD, "UNREAD"))
        try:
            res["unreadable"] = {"state": PS.state("PARK"), "problems": list(f.problems)}
        finally:
            BF.reset()
        o = res["off"]
        ok3 = (o["state"] == "dormant" and o["run"] == "active" and o["asked"] == ["RunawayContinuation"]
               and "PARK dormant: box flag park=off" in o["summary"] and " · park=off (box flag)" in o["banner"]
               and " · park=trade" not in o["banner"] and not o["problems"]
               and res["typo"]["state"] == "dormant" and any("'of'" in x for x in res["typo"]["problems"])
               and res["dup"]["state"] == "dormant" and any("duplicate" in x for x in res["dup"]["problems"])
               and res["unreadable"]["state"] == "dormant" and any("UNREADABLE" in x for x in res["unreadable"]["problems"])
               and res["on"]["state"] == "active" and res["on"]["asked"] == list(COUSINS))
        d3 = json.dumps({kk: {a: (b[-160:] if isinstance(b, str) else b) for a, b in v.items()} for kk, v in res.items()})[:1800]
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d3 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-600:]}"
    check("P3 park = off: PARK DORMANT, not asked, named on the [plans] and Service lines, Runaway ACTIVE; a typo, a "
          "duplicate and an unreadable file fail CLOSED (dormant, named); park = on reads ACTIVE", ok3, d3)

    # ── clocks / alerts / stores (tests/check_hunt_ogap_retired.py T3's harness, unchanged) ──
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

    # ── P4 the dispatch ─────────────────────────────────────────────────────
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

    def dig(x):
        return hashlib.sha256(json.dumps(x, default=str).encode()).hexdigest()[:16]

    ok4, d4 = False, ""
    try:
        freeze(MISSING)
        try:
            e_p, r_p, c_p = world("paper", True)
            e_l, r_l, c_l = world("live", False)
        finally:
            BF.reset()
        dg = dig([e_p, e_l])
        run_only = [[e for e in e_p if e[1] == "RunawayContinuation"], [e for e in e_l if e[1] == "RunawayContinuation"]]
        dr = dig(run_only)
        print(f"       (P4 no-file digest {dg}, Runaway-alone digest {dr})")
        f_off = freeze(OFF_FILE)
        try:
            off_ok = f_off.values.get("park") == "off"
            o_p, or_p, oc_p = world("paper_off", True)
            o_l, or_l, oc_l = world("live_off", False)
        finally:
            BF.reset()
        o_run = [[e for e in o_p if e[1] == "RunawayContinuation"], [e for e in o_l if e[1] == "RunawayContinuation"]]
        park_off = sum(1 for e in o_p + o_l if e[0] == "ask" and e[1] == "PARK")
        # the admission loop still hands a refused PARK to main._plan_skip; the plan board writes nothing for a DORMANT
        # plan (strategy/plan r303), which the 0 plan_tick / plan_heartbeat rows below prove
        park_skip_calls = sum(1 for e in o_p + o_l if e[0] == "skip" and e[1] == "PARK")
        park_on = sum(1 for e in e_p + e_l if e[0] == "ask" and e[1] == "PARK")
        ok4 = (dg == NOFILE_DIGEST and dr == RUNAWAY_DIGEST and park_on > 0 and c_p["PARK"][0] > 0
               and off_ok and park_off == 0 and oc_p["PARK"] == (0, 0) and oc_l["PARK"] == (0, 0)
               and oc_p["RunawayContinuation"][0] > 0 and o_run == run_only and dig(o_run) == RUNAWAY_DIGEST
               and not (r_p or r_l or or_p or or_l))
        d4 = (f"no-file digest={dg} want={NOFILE_DIGEST}; runaway digest={dr} want={RUNAWAY_DIGEST}; PARK asks on={park_on} "
              f"rows on={c_p['PARK']}; off flag read={off_ok} PARK events off={park_off} rows off paper/live="
              f"{oc_p['PARK']}/{oc_l['PARK']} (skip calls dropped by the board: {park_skip_calls}); Runaway identical off={o_run == run_only} (digest {dig(o_run)})")
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d4 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-700:]}"
    check("P4 the dispatch 09:30-11:10, paper and live: no file = r154 byte for byte (Runaway and PARK); park = off = "
          "PARK asked 0 times with 0 plan_tick / plan_heartbeat rows and Runaway byte-identical", ok4, d4)

    # ── P5 no door left open ────────────────────────────────────────────────
    ok5, d5 = False, ""
    try:
        fresh("p5", True)
        seen = []
        s_one, s_gcf, s_gen = MN._one_per_session_used, MN.get_chain_fetcher, MN._park_strategy.generate_signal
        MN._one_per_session_used = lambda s: seen.append("one_per_session:%s" % s) or s_one(s)
        MN.get_chain_fetcher = lambda *a, **k: seen.append("get_chain_fetcher") or s_gcf(*a, **k)
        MN._park_strategy.generate_signal = lambda **kw: seen.append("generate_signal") or None
        freeze(OFF_FILE)
        st = MN.BotState()
        st.paper_trading = True
        h = pin(datetime(2026, 11, 24, 11, 1, 5, tzinfo=ET))
        try:
            MN._set_admission(None)
            MN._attempt_park({"price": 600.0, "gap": {"prior_close": 598.0}}, _MS(), st, chain=None)
        finally:
            unpin(h)
            BF.reset()
            MN._one_per_session_used, MN.get_chain_fetcher = s_one, s_gcf
            MN._park_strategy.generate_signal = s_gen
        ok5 = seen == []
        d5 = f"reached: {seen}"
    except Exception as exc:                                    # noqa: BLE001
        d5 = f"{type(exc).__name__}: {exc}"
    check("P5 park = off: _attempt_park at 11:01 with no chain reads no one-per-session row, fetches no chain, asks "
          "nothing", ok5, d5)

    # ── P6 an open PARK row still exits ─────────────────────────────────────
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

    ok6, d6 = False, ""
    try:
        res = {}
        p = fresh("p6", True)
        freeze(OFF_FILE)
        try:
            h = pin(datetime(2026, 11, 24, 11, 5, 0, tzinfo=ET))
            try:
                kk = chain_for("2026-11-24", [601], 1.0).calls[0]
                rec = make_record(trade_id="park-open", strategy="PARK", setup_type="park_x", direction="long",
                                  option_side="call", strike=601.0, expiry="2026-11-24", contracts=1, entry_premium=1.0,
                                  total_cost=100.0, max_loss=100.0, stop_premium=0.0, underlying_entry=600.0,
                                  paper_trade=1, symbol="QQQ", option_symbol=kk.symbol,
                                  entry_time="2026-11-24T11:02:00-05:00", status="open")
                TL._trade_logger.log_entry(rec)
                res["state"] = PS.state("PARK")
                st = MN.BotState()
                st.paper_trading = True
                pm = PMM.PositionManager(paper_trading=True)
                s_pm = MN.get_position_manager
                MN.get_position_manager = lambda *a, **k: pm
                try:
                    MN._recover_open_position(st, "test")
                finally:
                    MN.get_position_manager = s_pm
                res["resumed"] = sorted(str(r.get("strategy")) for r in pm.get_open_records())
            finally:
                unpin(h)
            h = pin(datetime(2026, 11, 24, 15, 56, 0, tzinfo=ET))
            try:
                res["failed"] = pm.flatten_all(reason="test hard close", chain=chain_for("2026-11-24", [601], 0.40),
                                               spot=600.0)
            finally:
                unpin(h)
        finally:
            BF.reset()
        c = sqlite3.connect(p)
        res["rows"] = {r[0]: r[1] for r in c.execute("SELECT trade_id, status FROM trades")}
        c.close()
        res["open_after"] = len(pm.get_open_records())
        # the state is P3's; here it is required only where the key exists, so P6 pins the exit on r154 too
        ok6 = (res["state"] == ("dormant" if "park" in BF.SCHEMA else "active") and res["resumed"] == ["PARK"] and not res["failed"]
               and res["rows"].get("park-open") == "closed" and res["open_after"] == 0)
        d6 = f"{res}"
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d6 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-900:]}"
    check("P6 park = off: an open PARK row at start is resumed and closed by the hard close (an exit is never flagged)",
          ok6, d6)

    if FAILED:
        print(f"RED — {len(FAILED)} failed: {' '.join(FAILED)}")
        return 1
    print("GREEN — PARK is on or off per box by its box flag alone: default on is r154 byte for byte, park = off is never "
          "asked and writes nothing, Runaway is untouched, OT_PARK is inert and named, and an open PARK still exits (P1-P6)")
    return 0


if __name__ == "__main__":
    import shutil
    try:
        rc = main()
    finally:
        if _TD.startswith(tempfile.gettempdir()) and os.path.basename(_TD).startswith("check_park_flag_"):
            shutil.rmtree(_TD, ignore_errors=True)
    sys.exit(rc)
