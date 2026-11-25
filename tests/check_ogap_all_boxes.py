#!/usr/bin/env python3
"""
tests/check_ogap_all_boxes.py  v5.5
v5.5  2026-11-26  OTV5 r161 (LANE.1) — A2's "never walled" reads OGAP's own token: the Service line may now say
      "park=paper_only (walled on a live box)" (deploy/box_flags/QQQ, which this probe's fresh interpreters read), so A2
      refuses the r150 OGAP phrase "ogap=on (paper, walled" instead of any "walled" on the line. What A2 pins is unchanged.
v5.4  2026-11-24  OTV5 r155 (BOXF.2, M4) — RE-POINTED (WA 38.4): set_flags() built its stand-in Flags with ONLY the values
      it was handed, which with a schema key present (r155: `park`, default on) left `park` unset, so PARK read DORMANT
      (fails closed) and A4's cousin digest moved. A real load always carries every SCHEMA key at its default; the
      stand-in now does the same (the schema defaults, then the values handed). What each check pins is unchanged; A4's
      digest is the r152 one, as before.
v5.3  2026-11-23  OTV5 r153 (TRIM.2) — RE-POINTED (WA 38.4): OGAP and the Hunt are RETIRED (DORMANT, no switch; the box
      flag `ogap` is gone from utils/box_flags.SCHEMA). The operator, 2026-11-23: "The hunt & OGAP are trash. Retire them
      both after this session today." OGAP's code is KEPT until the purge, so what this gate pins turns around where it
      named OGAP running: A1 - DORMANT on every one of the 14 boxes, while the spec, driven directly, still gives the same
      11-05 put on every symbol (no symbol list); A2 - DORMANT and never asked on a live box and on paper, the Service
      line says "ogap=retired (dormant r153)"; A3 - no flag can turn it on: a box file line `ogap = on` / `off` / `of` /
      `paper_only`, an unreadable file, no file and a box_flags read that raises all leave it DORMANT, and the `on` line
      is REFUSED as an unknown key (named); plan_state.default("OGAP") is DORMANT; A4 - the cousins' dispatch digest,
      the Hunt's events filtered (it is no longer asked; the run must hold none), is REPLAY_DIGEST_EX_HUNT, measured on
      r152 c0cfcbf with the same filter, in three worlds (`ogap=off`; a forced `ogap=on` value; an OGAP position open with
      its try spent) and OGAP is asked in none. A5 and A6 unchanged (they drive the funnel and the spec directly).
v5.2  2026-11-23  OTV5 r152 (GATE.9) — A6 PINS THE EXIT ENGINE'S OWN CLOCK. ExitEngine._evaluate_ogap reads the minute
      from execution/exit_engine's module `datetime` (datetime.now(_ET), exit_engine.py _evaluate_ogap), the seam
      tests/check_ogap_mark.py and tests/check_ogap_paper_on_live.py already freeze; A6 pinned only now_et / now_utc,
      so its 15:45:05 close was decided on the WALL clock: green when it was built after 15:45 ET on 2026-11-22,
      red before 15:45 ET (the 2026-11-23 09:15 boot sweep, 14/14: exit=None). A6 now freezes exit_engine.datetime
      at 2026-11-05 15:45:05 ET beside the pin and restores it after; A1-A5 and the code under test unchanged.
v5.1  2026-11-22  OTV5 r150 (OGAP.5) — A2 TURNS AROUND: a LIVE box no longer sits OGAP out; it is ACTIVE and asked, and
      the Service line says "ogap=on (paper, walled from the cash account)" (the operator, 2026-11-22: "I want it paper
      trading even on the cash boxes. It's under evaluation."). The walls themselves are tests/check_ogap_paper_on_live.py.
      A1, A3-A6 unchanged.
v5.0  2026-11-22  OTV5 r149 (OGAP.4, M1 of the box flags) — new. OGAP ON EVERY BOX, ON PAPER; DORMANT ON A LIVE BOX; AND IT
      BLOCKS NONE OF ITS COUSINS. The operator, 2026-11-22: "If we're studying that trade, I don't understand why we're only
      testing it on one box. I honestly want it paper Trading on all of them." and "No trade set up should block or impede
      any of its cousins. Each one fires and manages on its own merits." The live rule is the before-cash audit's F2
      (2026-12-04 is QQQ live for one session): OGAP sits out when config.PAPER_TRADING is False.

  A1  OGAP EVALUATES ON EVERY BOX: for each of the 14 fleet symbols the plan state is ACTIVE on paper and the plan, on
      Park's 2026-11-05 fixture at the fill minute, gives the same OGAP put (no symbol list anywhere; config has no
      OGAP_SYMBOLS)
  A2  ACTIVE ON A LIVE BOX TOO (r150), in a fresh interpreter with OT_PAPER_TRADING=False: plan_state.state("OGAP") is
      ACTIVE with the box flag on, the [plans] summary names no dormant OGAP, main._safe_strategy("OGAP", fn) calls fn,
      and the Service line says "ogap=on (paper, walled from the cash account)"; the same interpreter on paper reads
      ACTIVE, asks fn and says "ogap=on" with no suffix (r149's A2 was DORMANT on a live box)
  A3  THE BOX FLAG DECIDES ON PAPER, FAIL CLOSED: `ogap = off` -> DORMANT (not asked, "ogap=off (box flag)"); a bad
      value (`ogap = of`), `paper_only` (refused until delivery P) and an unreadable file -> DORMANT; no file -> ACTIVE
      (the schema default on); a box_flags read that raises -> DORMANT (never ACTIVE by accident); plan_state.default
      ("OGAP") is the schema's default (ACTIVE), and plan_state's TABLE holds no ACTIVE / DORMANT literal for OGAP
  A4  INDEPENDENCE OF THE DISPATCH: main.attempt_new_entry() every minute 09:35:05-11:05:05 on a pinned clock, with the
      real admission table, plan_state, session guard, risk manager and a scratch trades.db, every strategy's
      generate_signal intercepted (returns None, records what it was asked with): Runaway's, the Hunt's and PARK's asks
      and their plan_check skips are BYTE-IDENTICAL (digest REPLAY_DIGEST) in three worlds: OGAP dormant (flag off), OGAP
      active and flat, and OGAP active with an OGAP position OPEN and its one-per-session try spent; OGAP itself is asked
      in the two active worlds and never in the dormant one (the positive control)
  A5  INDEPENDENCE OF THE FUNNEL: main._execute_entry_signal() (paper, the real RiskManager, a spy entry engine) sizes a
      Runaway, a Hunt and a PARK signal to the same contracts and reaches enter() the same way with an OGAP position open
      as with none
  A6  NO SAME-DAY EXPIRY, THE NEAREST ONE (the operator, 2026-11-22: "No to sitting out on non-expiry days. We just buy
      the nearest available expiry."): on 2026-11-05 a UNH box whose chain is the 11-06 series (fetch_chain's nearest)
      gives the same put on 11-06, the same strike and size as a same-day chain; a same-day chain still gives 11-05;
      ogap_no_0dte is nowhere in strategy/; and an OGAP record on the 11-06 series still exits at 15:45
      (ExitEngine._evaluate_ogap -> ogap_close_1545), so the position is flat the same day
Born red on r148 (the L1 build): A1 (13 of 14 boxes refused ogap_not_this_symbol), A2 (OGAP ACTIVE on a live box), A3 (no
flag key), A4 (its positive control: OGAP asked with the flag off; the cousins' digest is the same 2fd5fb3e6e3c96bb on r148).
A5 is green on both trees (the independence held before; it pins it). A6 is red on the M1 build before the
nearest-expiry change (ogap_no_0dte refused the 11-06 chain). 13 mutants red.
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
Run:  python3 tests/check_ogap_all_boxes.py
"""
import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
_TD = tempfile.mkdtemp(prefix="check_ogap_all_boxes_")
for _k, _f in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"),
               ("OT_LOG_FILE", "bot.log"), ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_COUNTERFACTUAL_DIR", "cf"),
               ("OT_ALERT_SPOOL", "alert_spool.jsonl"), ("OT_PLAN_STATES_FILE", "plan_states.json"),
               ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT")):
    os.environ[_k] = os.path.join(_TD, _f)
os.environ.pop("OT_DAILY_LOSS_LIMIT", None)
os.environ.pop("OT_PAPER_TRADING", None)
os.environ["OT_RISK_USD"] = "500"          # Park's $500, as tests/check_ogap.py: the 11-05 mark 4.24 buys 1
ET = ZoneInfo("America/New_York")
FLEET = ("SPX", "QQQ", "NVDA", "TSLA", "META", "AMZN", "GOOGL", "AMD", "AVGO", "NFLX", "CRM", "UNH", "CVX", "SMH")
FIX = os.path.join(ROOT, "tests", "fixtures", "ogap", "replay5.json")
REPLAY_DIGEST = "2fd5fb3e6e3c96bb"          # A4 to r152: Runaway / Hunt / PARK asks + skips, 09:35-11:05, identical in all three worlds
REPLAY_DIGEST_EX_HUNT = "28ffd453a0d9e360"         # A4 v5.3 (r153): the same with the Hunt's events filtered, measured on r152 c0cfcbf
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name)


class K:
    def __init__(self, strike, bid, ask, expiry, side):
        self.strike, self.bid, self.ask, self.expiry = strike, bid, ask, expiry
        self.mark = round((bid + ask) / 2, 2)
        self.delta = 0.5 if side == "C" else -0.5
        self.symbol = f"X {expiry} {side}{strike}"
        self.streamer_symbol = self.symbol


class Chain:
    def __init__(self, expiry, atm, bid, ask):
        self.expiry = expiry
        self.calls = [K(float(s), bid, ask, expiry, "C") for s in range(int(atm) - 3, int(atm) + 4)]
        self.puts = [K(float(s), bid, ask, expiry, "P") for s in range(int(atm) - 3, int(atm) + 4)]


LIVE_PROBE = r'''
import json, os, sys
sys.path.insert(0, %(root)r)
import config
from strategy import plan_state as S
import main as MN
asked = []
MN._admission_allows = lambda name: True
MN._safe_strategy("OGAP", lambda: asked.append(1))
print(json.dumps({"paper": config.PAPER_TRADING, "state": S.state("OGAP"), "summary": S.summary(["OGAP"]),
                  "asked": len(asked), "banner": MN._banner_dials()}))
'''


def probe(paper: bool):
    env = {k: v for k, v in os.environ.items()}
    env["OT_PAPER_TRADING"] = "True" if paper else "False"
    r = subprocess.run([sys.executable, "-c", LIVE_PROBE % {"root": ROOT}], capture_output=True, text=True,
                       timeout=300, env=env, cwd=ROOT)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:                                           # noqa: BLE001
        return {"err": (r.stderr or r.stdout)[-400:]}


def main():
    print("check_ogap_all_boxes")
    try:
        import pandas  # noqa: F401
        import config
        import main as MN
        import utils.time_utils as TU
        from strategy import plan_state as PS
        from strategy.ogap import Ogap
        from strategy import ogap_plan as OP
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN: imports failed ({type(exc).__name__}: {exc})")
        return 2
    try:
        from utils import box_flags as BF
    except Exception as exc:                                    # noqa: BLE001
        BF = None
        print(f"  (utils/box_flags not importable: {type(exc).__name__}: {exc})")
    for _h in logging.getLogger().handlers:
        if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
            _h.setLevel(logging.CRITICAL + 1)

    def set_flags(values, status="ok", problems=()):
        if BF is None:
            return
        vals = {k: r.default for k, r in BF.SCHEMA.items()}         # r155: a real load carries every schema key
        vals.update(values)
        BF._EFFECTIVE["flags"] = BF.Flags("QQQ", BF.FLAGS_REL + "/QQQ" if status != "missing" else "none (defaults)",
                                          "-", status, vals, tuple(problems))

    # ── A1 every box ────────────────────────────────────────────────────────
    fx = json.load(open(FIX))
    d = "2026-11-05"
    day = date.fromisoformat(d)
    bars = {int(k): tuple(v) for k, v in fx[d]["bars"].items()}
    fill = fx[d]["expect"]["fill"]
    spot = bars[fill][0]
    spec = Ogap()
    if BF is not None:
        BF.reset()
    got = {}
    for sym in FLEET:
        st = PS.state("OGAP")
        sg = spec.generate_signal(price_now=spot, now_et=OP.hhmm(fill), chain=Chain(d, round(spot), 4.23, 4.26),
                                  day=day, symbol=sym, bars=bars, prior_close=fx[d]["prior_close"])
        got[sym] = (st, None if sg is None else (sg.option_side, float(sg.strike), sg.entry_premium))
    want = ("dormant", ("put", float(fx[d]["expect"]["strike"]), 4.24))     # v5.3 (r153): retired, the code kept
    bad1 = {s: v for s, v in got.items() if v != want}
    check("A1 (r153) OGAP is DORMANT on every box; its kept spec still gives the same 11-05 put on all 14 symbols; "
          "no OGAP_SYMBOLS",
          not bad1 and not hasattr(config, "OGAP_SYMBOLS"), f"differ: {bad1}")

    # ── A2 live box ─────────────────────────────────────────────────────────
    lv, pp = probe(False), probe(True)
    ok2 = (lv.get("paper") is False and lv.get("state") == "dormant" and "OGAP (r153 TRIM.2)" in lv.get("summary", "")
           and lv.get("asked") == 0 and " · ogap=retired (dormant r153)" in lv.get("banner", "")
           and pp.get("paper") is True and pp.get("state") == "dormant" and pp.get("asked") == 0
           and " · ogap=retired (dormant r153)" in pp.get("banner", "")
           and "ogap=on (paper, walled" not in lv.get("banner", "") + pp.get("banner", ""))   # r161: OGAP's token
    check("A2 (r153) a LIVE box and a paper box: OGAP DORMANT, never asked, the Service line says retired",
          ok2, f"live={lv} paper={ {k: v for k, v in pp.items() if k != 'banner'} }")

    # ── A3 the flag, fail closed ────────────────────────────────────────────
    ok3, d3 = False, "no box_flags"
    if BF is not None:
        try:
            res = {}
            asked = []
            s_adm = MN._admission_allows
            MN._admission_allows = lambda name: True
            try:
                set_flags({"ogap": "off"})
                res["off"] = PS.state("OGAP")
                MN._safe_strategy("OGAP", lambda: asked.append("off"))
                res["off_banner"] = "ogap=retired (dormant r153)" in MN._banner_dials()
                td = tempfile.mkdtemp(prefix="a3_", dir=_TD)
                _on = os.path.join(td, "on")
                open(_on, "w").write("ogap = on\n")
                BF._EFFECTIVE["flags"] = BF.load("QQQ", path=_on)
                res["on_line"] = PS.state("OGAP")
                res["on_refused"] = (any("unknown key 'ogap'" in x for x in BF.effective().problems)
                                     and "ogap" not in BF.effective().values)
                MN._safe_strategy("OGAP", lambda: asked.append("on_line"))
                for nm, txt in (("bad", "ogap = of\n"), ("po", "ogap = paper_only\n")):
                    p = os.path.join(td, nm)
                    open(p, "w").write(txt)
                    BF._EFFECTIVE["flags"] = BF.load("QQQ", path=p)
                    res[nm] = PS.state("OGAP")
                os.mkdir(os.path.join(td, "unr"))
                BF._EFFECTIVE["flags"] = BF.load("QQQ", path=os.path.join(td, "unr"))
                res["unreadable"] = PS.state("OGAP")
                BF._EFFECTIVE["flags"] = BF.load("QQQ", path=os.path.join(td, "none"))
                res["missing"] = PS.state("OGAP")
                MN._safe_strategy("OGAP", lambda: asked.append("on"))
                s_val = BF.value
                BF.value = lambda k: (_ for _ in ()).throw(OSError("boom"))
                try:
                    res["raises"] = PS.state("OGAP")
                finally:
                    BF.value = s_val
            finally:
                MN._admission_allows = s_adm
                BF.reset()
            src = open(os.path.join(ROOT, "strategy", "plan_state.py"), encoding="utf-8").read()
            row = [ln for ln in src.splitlines() if ln.strip().startswith('"OGAP":') and "HOUR" in ln]   # v5.3: the TABLE row
            literal_free = len(row) == 1 and "DORMANT" in row[0].split("#")[0] and "ogap" not in BF.SCHEMA
            ok3 = (res == {"off": "dormant", "off_banner": True, "on_line": "dormant", "on_refused": True,
                           "bad": "dormant", "po": "dormant", "unreadable": "dormant", "missing": "dormant",
                           "raises": "dormant"}
                   and asked == [] and PS.default("OGAP") == "dormant" and literal_free)
            d3 = f"res={res} asked={asked} default={PS.default('OGAP')} row={row}"
        except Exception as exc:                                # noqa: BLE001
            d3 = f"{type(exc).__name__}: {exc}"
    check("A3 (r153) no box flag turns OGAP on: an `ogap = on` line is REFUSED (unknown key, named) and every file "
          "state (on / off / bad / paper_only / unreadable / none / a raise) reads DORMANT; plan_state's row is DORMANT, "
          "no `ogap` schema key", ok3, d3)

    # ── A4 the dispatch, three worlds ───────────────────────────────────────
    from database.trade_logger import get_trade_logger, make_record
    from analysis.orb_engine import get_orb_engine
    import execution.position_manager as PMM

    class _MS:
        adx, trend_direction, structure_sequence = 20.0, "NEUTRAL", ""

    class _Ch:
        calls, puts, spot, expiry = [], [], 600.0, ""

    real = {"now_et": TU.now_et, "now_utc": TU.now_utc}

    def pin(dt):
        fake = {"now_et": lambda: dt, "now_utc": lambda: dt.astimezone(timezone.utc)}
        sw = [(m, n) for m in list(sys.modules.values()) for n in real
              if m is not None and getattr(m, n, None) is real[n]]
        for m, n in sw:
            setattr(m, n, fake[n])
        return sw

    def unpin(sw):
        for m, n in sw:
            setattr(m, n, real[n])

    def _scalar(v):
        if v is None or isinstance(v, (bool, int, float, str)):
            return v
        return type(v).__name__

    import database.trade_logger as TL

    def fresh_db(tag):
        """A scratch trades.db of its own for each world (the logger singleton points at it)."""
        TL._trade_logger = TL.TradeLogger(db_path=os.path.join(_TD, "trades_%s.db" % tag))

    def open_ogap():
        rec = make_record(trade_id="ogap-open-a4", strategy="OGAP", setup_type="ogap_short", direction="short",
                          option_side="put", strike=600.0, expiry="2026-11-20", contracts=1, entry_premium=1.0,
                          total_cost=100.0, max_loss=100.0, stop_premium=0.0, underlying_entry=600.0,
                          paper_trade=1, symbol=os.environ.get("OT_INSTRUMENT", "QQQ"))
        get_trade_logger().log_entry(rec)
        return rec

    def world(name, flag, ogap_open):
        """attempt_new_entry each minute 09:35-11:05; -> (cousin events, ogap asks)."""
        fresh_db("w_" + name)
        set_flags({"ogap": flag})
        rec = open_ogap() if ogap_open else None
        ev, og = [], []
        saved = {}
        targets = {"_runaway_strategy": "RunawayContinuation", "_liquidity_hunt": "LiquidityHunt",
                   "_park_strategy": "PARK", "_ogap_strategy": "OGAP", "_breakout": "Breakout"}
        for attr, nm in targets.items():
            obj = getattr(MN, attr)
            saved[attr] = obj.generate_signal

            def rec_fn(_nm=nm, **kw):
                row = (_nm, MN.now_et().strftime("%H:%M"), sorted((k, _scalar(v)) for k, v in kw.items()))
                (og if _nm == "OGAP" else ev).append(("ask",) + row)
                return None
            obj.generate_signal = rec_fn
        s_skip = MN._plan_skip

        def skip(n, reason, gate=""):
            if n in ("RunawayContinuation", "LiquidityHunt", "PARK"):
                ev.append(("skip", n, MN.now_et().strftime("%H:%M"), gate, reason))
            return s_skip(n, reason, gate)
        MN._plan_skip = skip
        s_pm = MN.get_position_manager
        pm = PMM.PositionManager(paper_trading=True)
        if rec is not None:
            pm._open_records = list(get_trade_logger().get_open_trades())
        MN.get_position_manager = lambda *a, **k: pm
        eng = get_orb_engine()
        s_hi, s_lo = eng.data.orb_high, eng.data.orb_low
        eng.data.orb_high, eng.data.orb_low = 601.0, 599.0
        st = MN.BotState()
        st.paper_trading = True
        try:
            for i in range(0, 91):
                tot = 9 * 60 + 35 + i
                dt = datetime(2026, 11, 20, tot // 60, tot % 60, 5, tzinfo=ET)
                sw = pin(dt)
                try:
                    st.tick_count = i
                    MN.attempt_new_entry({"price": 600.0, "chain": _Ch(), "macro": {}, "symbol": "QQQ",
                                          "gap": {"prior_close": 598.0}}, _MS(), st)
                finally:
                    unpin(sw)
        finally:
            for attr, fn in saved.items():
                getattr(MN, attr).generate_signal = fn
            MN._plan_skip = s_skip
            MN.get_position_manager = s_pm
            eng.data.orb_high, eng.data.orb_low = s_hi, s_lo
            BF.reset() if BF is not None else None
        return ev, og

    ok4, d4 = False, ""
    try:
        e_off, o_off = world("dormant", "off", False)
        e_on, o_on = world("active", "on", False)
        e_open, o_open = world("open", "on", True)
        n_hunt = sum(1 for e in e_off + e_on + e_open if e[1] == "LiquidityHunt")      # v5.3 (r153): retired
        e_off, e_on, e_open = ([e for e in x if e[1] != "LiquidityHunt"] for x in (e_off, e_on, e_open))
        dg = [hashlib.sha256(json.dumps(e, default=str).encode()).hexdigest()[:16] for e in (e_off, e_on, e_open)]
        n_cousin = sum(1 for e in e_on if e[0] == "ask")
        print(f"       (A4 digest ex-Hunt {dg[0]})")
        ok4 = (dg[0] == dg[1] == dg[2] and dg[0] == REPLAY_DIGEST_EX_HUNT and n_cousin > 0 and not o_off
               and not o_on and not o_open and n_hunt == 0)
        d4 = (f"digests={dg} want={REPLAY_DIGEST_EX_HUNT} cousin_asks={n_cousin} hunt_events={n_hunt} ogap_asks "
              f"off/on/open={len(o_off)}/{len(o_on)}/{len(o_open)}")
        if dg[0] != dg[1] or dg[1] != dg[2]:
            for a, b, lab in ((e_off, e_on, "off->on"), (e_on, e_open, "on->open")):
                diff = [(x, y) for x, y in zip(a, b) if x != y][:3]
                d4 += f" | {lab} first diffs {diff} len {len(a)}/{len(b)}"
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        d4 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-600:]}"
    check("A4 (r153) the dispatch: Runaway / PARK asks and skips byte-identical to r152 (the Hunt filtered, and never "
          "asked) with the flag off, a forced `ogap=on` flag value, and an OGAP position open with its try spent; OGAP never asked",
          ok4, d4)

    # ── A5 the funnel ───────────────────────────────────────────────────────
    from strategy.base_strategy import OptionsSignal

    class _Spy:
        def __init__(self):
            self.sz = []

        def enter(self, signal=None, sizing=None, **kw):
            self.sz.append((getattr(signal, "strategy_name", "?"), getattr(sizing, "contracts", None)))
            return None

    class _State:
        paper_trading = True

    def funnel(ogap_open):
        fresh_db("f_%s" % ogap_open)
        if ogap_open:
            open_ogap()
        pm = PMM.PositionManager(paper_trading=True)          # sees this world's trades.db (the OGAP row open)
        pm._open_records = list(get_trade_logger().get_open_trades())
        s_pm = MN.get_position_manager
        MN.get_position_manager = lambda *a, **k: pm
        out = []
        for nm in ("RunawayContinuation", "LiquidityHunt", "PARK"):
            sg = OptionsSignal(strategy_name=nm, setup_type="x_long", direction="long", option_side="call",
                               underlying_entry=600.0, underlying_stop=0.0, strike=600.0, entry_premium=1.45,
                               stop_loss_pct=1.0)
            spy = _Spy()
            _ge = MN.get_entry_engine
            MN.get_entry_engine = lambda *a, **kw: spy
            try:
                MN._execute_entry_signal(sg, {"price": 600.0, "macro": {}}, None, _State(), None, additive=True)
            finally:
                MN.get_entry_engine = _ge
            out.append((nm, spy.sz))
        MN.get_position_manager = s_pm
        return out, len(pm.get_open_records())
    ok5, d5 = False, ""
    try:
        MN._observe.clear()                    # A4's last tick (11:05) left Runaway and the Hunt OBSERVED (log-only)
        MN._set_admission(None)
        (f0, n0), (f1, n1) = funnel(False), funnel(True)
        ok5 = f0 == f1 and all(sz for _n, sz in f0) and n0 == 0 and n1 == 1
        d5 = f"flat={f0} (open {n0}) ogap_open={f1} (open {n1})"
    except Exception as exc:                                    # noqa: BLE001
        d5 = f"{type(exc).__name__}: {exc}"
    check("A5 the funnel: Runaway, Hunt and PARK size and reach enter() the same with an OGAP position open", ok5, d5)

    # ── A6 the nearest expiry ───────────────────────────────────────────────
    ok6, d6 = False, ""
    try:
        import execution.exit_engine as EE
        same = spec.generate_signal(price_now=spot, now_et=OP.hhmm(fill), chain=Chain(d, round(spot), 4.23, 4.26),
                                    day=day, symbol="UNH", bars=bars, prior_close=fx[d]["prior_close"])
        nxt = spec.generate_signal(price_now=spot, now_et=OP.hhmm(fill), chain=Chain("2026-11-06", round(spot), 4.23, 4.26),
                                   day=day, symbol="UNH", bars=bars, prior_close=fx[d]["prior_close"])
        hits = []
        for dp, _dn, fn in os.walk(os.path.join(ROOT, "strategy")):
            for f in fn:
                if f.endswith(".py") and "ogap_no_0dte" in open(os.path.join(dp, f), encoding="utf-8").read().split('"""', 2)[-1]:
                    hits.append(f)
        rec = {"trade_id": "a6", "strategy": "OGAP", "entry_premium": 4.24, "contracts": 1, "expiry": "2026-11-06",
               "max_premium_seen": 4.30, "_exit_bid": 4.20}
        _at = datetime(2026, 11, 5, 15, 45, 5, tzinfo=ET)
        _real_ee_dt = EE.datetime

        class _EEClock(_real_ee_dt):                          # v5.2 (GATE.9): exit_engine's own `datetime` seam
            @classmethod
            def now(cls, tz=None):
                return _at.astimezone(tz) if tz is not None else _at.replace(tzinfo=None)

        sw = pin(_at)
        EE.datetime = _EEClock
        try:
            dec = EE.ExitEngine()._evaluate_ogap(rec, 4.25)
        finally:
            EE.datetime = _real_ee_dt
            unpin(sw)
        ok6 = (same is not None and nxt is not None and same.expiry == d and nxt.expiry == "2026-11-06"
               and float(nxt.strike) == float(same.strike) and nxt.ogap_contracts == same.ogap_contracts
               and nxt.entry_premium == same.entry_premium and not hits
               and dec is not None and dec.should_exit and str(dec.exit_reason).startswith("ogap_close_1545"))
        d6 = (f"same={same and (same.expiry, same.strike)} next={nxt and (nxt.expiry, nxt.strike)} hits={hits} "
              f"exit={getattr(dec, 'exit_reason', None)}")
    except Exception as exc:                                    # noqa: BLE001
        d6 = f"{type(exc).__name__}: {exc}"
    check("A6 no same-day expiry: OGAP buys the chain's nearest expiry (same strike and size), a same-day chain is "
          "unchanged, and the 11-06 position still closes at 15:45", ok6, d6)

    if FAILED:
        print(f"RED — {len(FAILED)} failed: {' '.join(FAILED)}")
        return 1
    print("GREEN — OGAP is retired on every box (r153: DORMANT, no flag turns it on); its kept code still sizes and exits "
          "as built; its cousins dispatch as on r152 (A1-A6)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
