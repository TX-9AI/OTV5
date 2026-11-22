#!/usr/bin/env python3
"""
tests/check_blind_reacquire.py  v5.0
v5.0  2026-11-22  OTV5 r146 (BLND.1, partial; the before-cash audit 2026-11-22 F3) — new. AFTER A BLIND EPISODE, NO
      OPENING ORDER ON THE TICK THAT FIRST SEES AGAIN; ENTRIES ARE ELIGIBLE FROM THE NEXT TICK, ON CURRENT 1m BARS. The
      operator, 2026-09-30: "The plan should have to reacquire a valid trigger after sight restored"; 2026-11-22: "I think
      1 full tick after a restore should be eligible for a fire if the entry still qualifies." The 2026-09-29 shape on a
      fixed ET clock, 15 s ticks: FeedBlind ticks 09:32:04 .. 09:37:49 (the feed dead since 09:30:10), sight on tick 100
      at 09:38:04. A CURRENT frame holds 1m bars 09:30-09:38 (09:38 forming); a STALE one stops at the frozen 09:30 bar.

  R1  utils/blind_reacquire: held on the sighted tick (100, 09:38:04); eligible on tick 101 (09:38:19) with a current
      frame (the newest closed bar is 09:37, the last completed minute); with a stale frame held on 101 and 102 (the line
      names 09:30 and 09:37) and eligible on 103 once current; a choke-point read (no tick) holds while the episode stands
      and is '' after it ends; last_completed_minute / bars_current at the edges
  R2  DRIVEN through main: _blind_tick x 24 then _blind_clear(now=09:38:04) on tick 100; attempt_new_entry() on tick 100
      asks NOTHING (Runaway, the Hunt, PARK, OGAP and Breakout intercepted), writes the plan_check skip at gate
      blind_reacquire and ONE "[entry-gate] ... entries HELD" line naming the episode (09:32:04-09:37:49); on tick 101
      (current frame) it asks Runaway, the Hunt, PARK and OGAP exactly as the no-episode call does; with a stale frame on
      tick 101 it asks nothing (the line names the stale bar) and on tick 102, current, it asks them
  R3  the DEBIT choke point: EntryEngine.enter() (paper) refuses while the episode stands, touching nothing (no logger,
      no broker session or account); after tick 101 released it, it reaches the trade logger (the tripwire)
  R4  the CREDIT choke point: main._execute_condor_leg() returns before it sizes while the episode stands; sizes after
  R5  EXITS ARE NOT GATED: during the hold the real PositionManager (paper) closes an open Runaway on its 1.00 premium
      stop from a 0.80 chain mark, the same exit it books with no episode; no exit module reads blind_reacquire
  R6  ZERO broker calls and NO knob: utils/blind_reacquire.py imports no broker/data/config/os module, reads no env and
      no config key; config.py names no blind-reacquire key
  R7  a new blind episode inside the hold starts over (held on its own sighted tick, eligible the tick after); a restart
      (fresh module state) holds nothing until its own first blind tick (WA 37 is the restart rule; nothing persisted)
  R8  NO EPISODE, NO CHANGE: attempt_new_entry() every minute 09:30:05-15:44:05 (strategies intercepted) and
      EntryEngine.enter() every minute 09:30:30-15:59:30 on a pinned clock produce the r144 digest REPLAY_DIGEST
      (identical on r145 7f73a6d and r146)
  R9  OGAP's own stale refusal is still there (strategy/ogap_plan: a signal first seen after its fill minute is refused
      as ogap_stale): the hold does not replace it
Born red on r145 (7f73a6d) at R1 R2 R3 R4 R5 R6 R7 (R8 R9 green on both trees).
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas / tastytrade).
Run:  python3 tests/check_blind_reacquire.py
"""
import ast
import hashlib
import logging
import os
import sys
import tempfile
import types
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
_TD = tempfile.mkdtemp(prefix="check_blind_reacquire_")
for _k, _f in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"),
               ("OT_LOG_FILE", "bot.log"), ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_COUNTERFACTUAL_DIR", "cf"),
               ("OT_ALERT_SPOOL", "alert_spool.jsonl"), ("OT_PLAN_STATES_FILE", "plan_states.json"),
               ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT")):
    os.environ.setdefault(_k, os.path.join(_TD, _f))
os.environ.pop("OT_DAILY_LOSS_LIMIT", None)
ET = ZoneInfo("America/New_York")
FAILED = []
REPLAY_DIGEST = "8bfe7724a77ca08d"   # R8: attempt_new_entry + enter() on a pinned day, no episode; r145 7f73a6d == r146


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def at(h, m, s=0.0, day=(2026, 9, 29)):
    return datetime(*day, h, m, int(s), int(round((s - int(s)) * 1e6)), tzinfo=ET)


def ep(h, m, s=0.0, day=(2026, 9, 29)):
    return at(h, m, s, day).timestamp()


class _Pin:
    """Pin now_et / now_utc in every loaded module that holds the real function (check_cap_all's sweep)."""
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


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines = []

    def emit(self, r):
        try:
            self.lines.append(r.getMessage())
        except Exception:                                       # noqa: BLE001
            pass


def main():
    print("check_blind_reacquire")
    try:
        import pandas  # noqa: F401
        import main as MN
        import utils.time_utils as TU
        import execution.entry_engine as EE
        import execution.position_manager as PM
        import execution.exit_engine as XE
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN: imports failed ({type(exc).__name__}: {exc})")
        return 2
    try:
        from utils import blind_reacquire as BR
    except Exception as exc:                                    # noqa: BLE001
        BR = None
        print(f"  (utils/blind_reacquire not importable: {type(exc).__name__}: {exc})")

    pin = _Pin(TU)
    for _h in logging.getLogger().handlers:                    # the console stays readable; _Cap still sees INFO
        if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
            _h.setLevel(logging.CRITICAL + 1)
    cap = _Cap()
    logging.getLogger().addHandler(cap)
    MN.time.sleep = lambda s: None
    BLIND = [ep(9, 32, 4) + 15.0 * i for i in range(24)]       # 09:32:04 .. 09:37:49
    SIGHT = ep(9, 38, 4)

    # ── R1 the module ───────────────────────────────────────────────────────
    import pandas as pd

    def frame(last_hm):
        """1m bars from 09:30 to last_hm (inclusive) on 2026-09-29, ET index."""
        h, m = last_hm
        idx = pd.date_range(at(9, 30), at(h, m), freq="1min")
        return pd.DataFrame({"open": 600.0, "high": 601.0, "low": 599.0, "close": 600.5, "volume": 1000.0}, index=idx)
    CUR, STALE = frame((9, 38)), frame((9, 30))                # current (09:38 forming) / frozen at the 09:30 bar
    ok1, d1 = False, "no module"
    if BR is not None:
        try:
            BR.reset()
            for t in BLIND:
                BR.note_blind(t)
            BR.note_sight(SIGHT, 100)
            h100 = BR.hold(SIGHT, 100, CUR)
            choke = BR.hold(ep(9, 38, 10))
            h101 = BR.hold(ep(9, 38, 19), 101, CUR)
            gone = BR.state() is None
            choke_after = BR.hold(ep(9, 38, 20))
            BR.reset()
            for t in BLIND:
                BR.note_blind(t)
            BR.note_sight(SIGHT, 100)
            s101 = BR.hold(ep(9, 38, 19), 101, STALE)
            s102 = BR.hold(ep(9, 38, 34), 102, STALE)
            s103 = BR.hold(ep(9, 38, 49), 103, CUR)
            edges = (abs(BR.last_completed_minute(ep(9, 38, 19)) - ep(9, 37)) < 1e-6
                     and BR.bars_current(frame((9, 37)), ep(9, 38, 3)) and not BR.bars_current(frame((9, 36)), ep(9, 38, 3))
                     and not BR.bars_current(None, ep(9, 38, 3)))
            ok1 = (bool(h100) and "first sees again" in h100 and "09:32:04-09:37:49" in h100 and bool(choke)
                   and h101 == "" and gone and choke_after == ""
                   and bool(s101) and "09:30" in s101 and "09:37" in s101 and bool(s102) and s103 == "" and edges)
            d1 = f"h100={h100!r} choke={bool(choke)} h101={h101!r} gone={gone} s101={s101!r} s102={bool(s102)} s103={s103!r} edges={edges}"
            BR.reset()
        except Exception as exc:                                # noqa: BLE001
            d1 = f"{type(exc).__name__}: {exc}"
    check("R1 held on the sighted tick; eligible on the next tick with current bars; a stale frame holds until the last "
          "completed minute is in it; a choke-point read holds while the episode stands", ok1, d1)

    # ── shared harness for R2 / R8 ──────────────────────────────────────────
    class _MS:
        adx, trend_direction, structure_sequence = 20.0, "NEUTRAL", ""

    class _Ch:
        calls, puts, spot = [], [], 600.0

    def drive(dt, tick=None, df=None):
        """attempt_new_entry at dt with every strategy intercepted; returns (asked, skips, held_lines, err)."""
        asked, skips = [], []
        saved = {n: getattr(MN, n) for n in ("_attempt_park", "_attempt_ogap", "_attempt_hunt", "_safe_strategy",
                                             "_plan_skip_all", "_plan_skip", "get_chain_fetcher")}
        MN._attempt_park = lambda ctx, ms, state, chain=None: asked.append(("PARK", chain is not None))
        MN._attempt_ogap = lambda ctx, ms, state, chain=None: asked.append(("OGAP", chain is not None))
        MN._attempt_hunt = lambda ctx, ms, state, **k: asked.append(("LiquidityHunt", k.get("chain") is not None))
        MN._safe_strategy = lambda name, fn, ctx=None: (asked.append((name, True)), None)[1]
        MN._plan_skip_all = lambda reason, gate="": skips.append(("*", gate, reason))
        MN._plan_skip = lambda name, reason, gate="": skips.append((name, gate, reason))

        def _no_fetch():
            raise AssertionError("a chain fetch (broker data call) while held")
        MN.get_chain_fetcher = _no_fetch
        st = MN.BotState()
        st.paper_trading = True
        if tick is not None:
            st.tick_count = tick
        n0 = len(cap.lines)
        err = ""
        ctx = {"price": 600.0, "chain": _Ch(), "macro": {}, "symbol": "QQQ"}
        if df is not None:
            ctx["df_1m"] = df
        pin.set(dt)
        try:
            MN.attempt_new_entry(ctx, _MS(), st)
        except Exception as e:                                  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        finally:
            pin.unset()
            for n, v in saved.items():
                setattr(MN, n, v)
        held = [ln for ln in cap.lines[n0:] if "[entry-gate]" in ln and "entries HELD" in ln]
        return asked, skips, held, err

    # ── R2 driven through main ──────────────────────────────────────────────
    ok2, d2 = False, ""
    try:
        pm = types.SimpleNamespace(blind_rest_marks=False, has_open_position=lambda: False,
                                   get_open_records=lambda: [])

        def episode_through_main():
            if BR is not None:
                BR.reset()
            stb = types.SimpleNamespace(blind_since=None, blind_paged=True, blind_last_line=0.0, blind_managing=0,
                                        errors_this_hour=0, paper_trading=True, tick_count=76)
            for t in BLIND:
                MN._blind_tick(stb, pm, MN.FeedBlind("No 5m data available"), now=t)
            stb.tick_count = 100
            MN._blind_clear(stb, pm, now=SIGHT)
        episode_through_main()
        a1, s1, h1, e1 = drive(at(9, 38, 4), 100, CUR)
        a2, s2, h2, e2 = drive(at(9, 38, 19), 101, CUR)
        episode_through_main()
        a3, s3, h3, e3 = drive(at(9, 38, 19), 101, STALE)
        a4, s4, h4, e4 = drive(at(9, 38, 34), 102, CUR)
        if BR is not None:
            BR.reset()
        a0, s0, h0, e0 = drive(at(9, 38, 19), 101, CUR)
        gates1 = {g for (_n, g, _r) in s1}
        want = {("RunawayContinuation", True), ("LiquidityHunt", True), ("PARK", True), ("OGAP", True)}
        ok2 = (not (e1 or e2 or e3 or e4 or e0)
               and a1 == [] and gates1 == {"blind_reacquire"} and ("*", "blind_reacquire") in {(n, g) for (n, g, _r) in s1}
               and len(h1) == 1 and "09:32:04-09:37:49" in h1[0] and "first sees again" in h1[0]
               and want <= set(a2) and a2 == a0 and h2 == [] and h0 == []
               and a3 == [] and len(h3) == 1 and "newest closed bar is 09:30" in h3[0]
               and a4 == a0 and h4 == [])
        d2 = (f"t100 asked={a1} skips={s1[:2]} held={h1} err={e1}; t101 asked={a2} err={e2}; stale t101 asked={a3} "
              f"held={h3} err={e3}; t102 asked={a4} err={e4}; no-episode asked={a0} err={e0}")
    except Exception as exc:                                    # noqa: BLE001
        d2 = f"{type(exc).__name__}: {exc}"
    check("R2 DRIVEN: after _blind_tick x24 + _blind_clear on tick 100, attempt_new_entry asks nothing on tick 100 (one "
          "plan_check skip at gate blind_reacquire, ONE held line naming the episode); tick 101 on current bars asks "
          "Runaway, the Hunt, PARK and OGAP exactly as with no episode; a stale frame holds tick 101, tick 102 asks", ok2, d2)

    # ── R3 the debit choke point ────────────────────────────────────────────
    from strategy.base_strategy import OptionsSignal
    from data.options_chain import OptionContract

    class _Trip(Exception):
        pass

    class _Boom:
        def __getattr__(self, k):
            raise _Trip(k)

    class _Sizing:
        allowed, contracts, total_cost = True, 1, 85.0

    sig = OptionsSignal(strategy_name="RunawayContinuation", setup_type="orb_long", option_side="call", strike=601.0,
                        entry_premium=0.85, underlying_entry=600.0,
                        contract=OptionContract(symbol="QQQ   260929C00601000", strike=601.0, mark=0.85))
    eng = EE.EntryEngine(paper_trading=True)
    eng._trade_logger = _Boom()
    touched = []
    s_get_session, s_get_account = EE.get_session, EE.get_account
    EE.get_session = lambda *a, **k: touched.append("session") or (_ for _ in ()).throw(_Trip("session"))
    EE.get_account = lambda *a, **k: touched.append("account") or (_ for _ in ()).throw(_Trip("account"))

    def enter_at(dt):
        pin.set(dt)
        try:
            return "refused" if eng.enter(sig, _Sizing()) is None else "booked"
        except _Trip as t:
            return f"reached:{t}"
        except Exception as e:                                  # noqa: BLE001
            return f"err:{type(e).__name__}"
        finally:
            pin.unset()

    ok3, d3 = False, ""
    try:
        if BR is not None:
            BR.reset()
            for t in BLIND:
                BR.note_blind(t)
            BR.note_sight(SIGHT, 100)
        r_hold = enter_at(at(9, 38, 10))
        t_hold = list(touched)
        if BR is not None:
            BR.hold(ep(9, 38, 19), 101, CUR)                    # tick 101 releases
        r_open = enter_at(at(9, 38, 20))
        ok3 = BR is not None and r_hold == "refused" and t_hold == [] and r_open.startswith("reached")
        d3 = f"held={r_hold} touched={t_hold}; released={r_open}"
    except Exception as exc:                                    # noqa: BLE001
        d3 = f"{type(exc).__name__}: {exc}"
    check("R3 enter() (paper) refuses while the episode stands, touching nothing (no logger, session or account); after "
          "tick 101 released it, it reaches the trade logger", ok3, d3)

    # ── R4 the credit choke point ───────────────────────────────────────────
    ok4, d4 = False, ""
    try:
        sized = []

        class _RMStop(Exception):
            pass

        def _rm(*a, **k):
            sized.append(1)
            raise _RMStop()
        s_rm, s_lo = MN.get_risk_manager, MN._log_only
        MN.get_risk_manager, MN._log_only = _rm, (lambda s, c: False)
        csig = types.SimpleNamespace(strategy_name="IronCondorStrategy", option_side="put",
                                     short_put_contract=OptionContract(symbol="P1", strike=595.0, mark=1.0),
                                     long_put_contract=OptionContract(symbol="P2", strike=594.0, mark=0.6),
                                     net_credit=0.4)

        def leg_at(dt):
            pin.set(dt)
            try:
                MN._execute_condor_leg(csig, types.SimpleNamespace(paper_trading=True), {})
                return "returned"
            except _RMStop:
                return "sized"
            except Exception as e:                              # noqa: BLE001
                return f"err:{type(e).__name__}:{e}"
            finally:
                pin.unset()
        try:
            if BR is not None:
                BR.reset()
                for t in BLIND:
                    BR.note_blind(t)
                BR.note_sight(SIGHT, 100)
            c_hold = leg_at(at(9, 38, 10))
            n_hold = len(sized)
            if BR is not None:
                BR.hold(ep(9, 38, 19), 101, CUR)
            c_open = leg_at(at(9, 38, 20))
        finally:
            MN.get_risk_manager, MN._log_only = s_rm, s_lo
        ok4 = BR is not None and c_hold == "returned" and n_hold == 0 and c_open == "sized"
        d4 = f"held={c_hold} sized={n_hold}; released={c_open}"
    except Exception as exc:                                    # noqa: BLE001
        d4 = f"{type(exc).__name__}: {exc}"
    check("R4 _execute_condor_leg() returns before sizing while the episode stands; sizes after tick 101 released it",
          ok4, d4)

    # ── R5 exits are not gated ──────────────────────────────────────────────
    ok5, d5 = False, ""
    try:
        XE.is_hard_close_time = lambda *a, **k: False

        class _TL:
            def __init__(self, recs):
                self.exits, self.recs = [], recs

            def update_current_premium(self, *a, **k): pass
            def update_trail_stop(self, *a, **k): pass
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

        def one_exit(dt):
            rec = {"trade_id": "r5", "strategy": "RunawayContinuation", "symbol": "QQQ", "direction": "long",
                   "option_side": "call", "strike": 601.0, "entry_premium": 2.00, "stop_premium": 1.00,
                   "target_premium": 0.0, "trail_stop": 0.0, "underlying_entry": 0.0, "underlying_stop": 0.0,
                   "contracts": 5, "is_butterfly": 0, "option_symbol": "QQQ   260929C00601000",
                   "expiry": "2026-09-29", "current_premium": 1.80, "entry_time": "2026-09-29T13:36:00+00:00",
                   "status": "open"}
            tl = _TL([rec])
            p = PM.PositionManager(paper_trading=True)
            p._trade_logger = tl
            p._open_records = [rec]
            ch = types.SimpleNamespace(calls=[types.SimpleNamespace(symbol="QQQ   260929C00601000", strike=601.0,
                                                                    mark=0.80, bid=0.79, ask=0.81, theta=-0.1,
                                                                    delta=0.40, iv=0.2)],
                                       puts=[], spot_price=600.0, expiry="2026-09-29")
            pin.set(dt)
            try:
                p.manage_open_position(chain=ch)
            finally:
                pin.unset()
            return tl.exits
        if BR is not None:
            BR.reset()
            for t in BLIND:
                BR.note_blind(t)
            BR.note_sight(SIGHT, 100)
        held_now = bool(BR.hold(ep(9, 38, 30))) if BR is not None else False
        x_hold = one_exit(at(9, 38, 30))
        if BR is not None:
            BR.reset()
        x_free = one_exit(at(9, 38, 30))
        leaks = []
        for rel in ("execution/exit_engine.py", "execution/position_manager.py", "strategy/management.py",
                    "strategy/condor_roll.py", "execution/credit_remainder.py"):
            p_ = os.path.join(ROOT, rel)
            if os.path.exists(p_) and "blind_reacquire" in open(p_, encoding="utf-8").read():
                leaks.append(rel)
        ok5 = (held_now and len(x_hold) == 1 and x_hold[0][1] == 0.80 and x_hold == x_free and not leaks)
        d5 = f"held={held_now} exits_held={x_hold} exits_free={x_free} leaks={leaks}"
    except Exception as exc:                                    # noqa: BLE001
        d5 = f"{type(exc).__name__}: {exc}"
    check("R5 exits are not gated: during the hold the paper PositionManager closes a Runaway at 0.80 on its 1.00 stop, "
          "identical to no episode; no exit module reads blind_reacquire", ok5, d5)

    # ── R6 zero broker calls, no knob ───────────────────────────────────────
    p6 = os.path.join(ROOT, "utils", "blind_reacquire.py")
    ok6, d6 = False, "missing"
    if os.path.exists(p6):
        src6 = open(p6, encoding="utf-8").read()
        tree = ast.parse(src6)
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                mods.add(n.module or "")
        bad = [m for m in mods if m.startswith(("data", "execution", "tastytrade", "config", "os"))]
        cfg = open(os.path.join(ROOT, "config.py"), encoding="utf-8").read()
        ok6 = (not bad and "environ" not in src6 and "getenv" not in src6
               and "BLIND_REACQ" not in cfg.upper() and "OT_REACQ" not in cfg.upper())
        d6 = f"imports={sorted(mods)} bad={bad}"
    check("R6 utils/blind_reacquire.py imports no broker/data/config/os module, reads no env; config names no key",
          ok6, d6)

    # ── R7 new episode inside the hold; restart ─────────────────────────────
    ok7, d7 = False, "no module"
    if BR is not None:
        try:
            BR.reset()
            for t in BLIND:
                BR.note_blind(t)
            BR.note_sight(SIGHT, 100)
            BR.note_blind(ep(9, 38, 19))                        # tick 101 is blind again
            still = bool(BR.hold(ep(9, 38, 19), 101, CUR))
            BR.note_sight(ep(9, 38, 34), 102)
            h102 = bool(BR.hold(ep(9, 38, 34), 102, CUR))      # its own sighted tick
            h103 = BR.hold(ep(9, 38, 49), 103, CUR)
            BR.reset()                                          # a restart: nothing in memory
            fresh = BR.hold(ep(9, 38, 30), 5, CUR)
            BR.note_blind(ep(9, 41, 4))
            blind_now = bool(BR.hold(ep(9, 41, 4), 6, CUR))    # still blind (no sight yet): held
            ok7 = still and h102 and h103 == "" and fresh == "" and blind_now
            d7 = f"still={still} t102={h102} t103={h103!r} restart={fresh!r} blind={blind_now}"
            BR.reset()
        except Exception as exc:                                # noqa: BLE001
            d7 = f"{type(exc).__name__}: {exc}"
    check("R7 a second episode inside the hold is held on its own sighted tick and eligible the tick after; a restart "
          "holds nothing until its own first blind tick", ok7, d7)

    # ── R8 no episode, no change (digest) ───────────────────────────────────
    if BR is not None:
        BR.reset()
    h = hashlib.sha256()
    n_asked = 0
    try:
        day = (2026, 11, 5)
        for mins in range(9 * 60 + 30, 15 * 60 + 45):
            dt = datetime(*day, mins // 60, mins % 60, 5, tzinfo=ET)
            a, s, hl, e = drive(dt)
            n_asked += len(a)
            h.update(repr((dt.strftime("%H:%M"), a, sorted({(n, g) for (n, g, _r) in s}), len(hl), e)).encode())
        for mins in range(9 * 60 + 30, 16 * 60):
            dt = datetime(*day, mins // 60, mins % 60, 30, tzinfo=ET)
            h.update(repr((dt.strftime("%H:%M"), enter_at(dt))).encode())
        dg = h.hexdigest()[:16]
        d8 = f"digest={dg} want={REPLAY_DIGEST} asked={n_asked}"
        ok8 = dg == REPLAY_DIGEST and n_asked > 0
    except Exception as exc:                                    # noqa: BLE001
        ok8, d8 = False, f"{type(exc).__name__}: {exc}"
    EE.get_session, EE.get_account = s_get_session, s_get_account
    print(f"       ({d8})")
    check("R8 NO EPISODE, NO CHANGE: the minute-by-minute attempt_new_entry + enter() replay digest is the pre-BLND.1 tree's (r144 = r145)", ok8, d8)

    # ── R9 OGAP's own stale refusal stands ──────────────────────────────────
    og = open(os.path.join(ROOT, "strategy", "ogap_plan.py"), encoding="utf-8").read()
    check("R9 strategy/ogap_plan still refuses a stale signal (ogap_stale, never filled late)",
          'if r.get("stale"):' in og and 't.refuse("ogap_stale"' in og and "never filled late" in og)

    logging.getLogger().removeHandler(cap)
    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
