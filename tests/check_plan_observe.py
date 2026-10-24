#!/usr/bin/env python3
"""
tests/check_plan_observe.py  v1.0
THE PLAN ALWAYS LOOKS; THE STRATEGY IS GATED ON THE HOUR - AND AN OBSERVED FIRE IS NEVER EXECUTED (OBS.1).

v1.0  2026-10-05  OTV4TEST r254. The operator, 2026-10-05: "the plan always looks, but the strategies
      are gated on the hour of the day" (09:34 ET); scope "A for sure" - Breakout, Runaway and the
      Hunt (09:36 ET); "Have those blocked TRADES just to Log only" (09:32 ET). Before: at 10:30 each
      of the three plans returned DORMANT 'entry_window' and admission never asked its strategy, so
      nothing recorded what r187's cutoff blocked.

ADMISSION (the REAL PositionManager.observing over the REAL logging_state and rules()):
  A1  10:45, flat, cap intact: Breakout, RunawayContinuation and LiquidityHunt are OBSERVED
  A2  10:15 (inside the window): nothing observed - they are admitted for real
  A3  15:40 (the entries stop) and 09:31: nothing observed
  A4  10:45 with the catastrophic cap hit: nothing observed (only the window is lifted)
  A5  10:45 with a Breakout open (max_open_of_type 1): Breakout NOT observed, the other two are
  A6  nothing outside the three is ever observed (VOLT, ORB, the flies, ORCS)
PLANS (the REAL prepare of each, at 10:45):
  P1  NOT observed: each of the three goes DORMANT on entry_window, exactly as before
  P2  observed: none of the three goes dormant on entry_window - the plan keeps looking
TAKE (the REAL PlanTick.take):
  T1  observed: the row is LOG-ONLY, no plan_ledger row is opened, the gate report is not told
  T2  CONTROL - not observed: TAKE, the ledger row opens, the gate report is told
THE DOORS (the REAL main.py):
  D1  _log_only is True for an observed strategy's signal and False for any other
  D2  _execute_entry_signal returns BEFORE any work for an observed signal (the last lock)
  D3  one INFO line per setup, not per tick, naming the pin gate's answer
  D4  the Hunt's real one-per-break set (FINISHED) is untouched by an observed fire
  D5  CONTROL: a non-observed Hunt fire still adds to FINISHED

Every store is a tempdir; nothing on the box is opened for writing.
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3).
"""
import os
import sys
import tempfile
import logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_plan_observe_")
os.environ["OT_TRADES_DB"] = os.path.join(_TD, "trades.db")
os.environ["OT_DERIVED_DB"] = os.path.join(_TD, "derived_store.db")
os.environ["OT_FEED_DB"] = os.path.join(_TD, "feed_store.db")
os.environ.setdefault("OT_LOG_FILE", os.path.join(_TD, "bot.log"))
os.environ["OT_INSTRUMENT"] = "QQQ"
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


class _ORB:
    orb_high, orb_low = 101.00, 100.00
    state = None
    fifty_accepted = False


def main():
    try:
        import pandas  # noqa: F401
        from execution import position_manager as PM
        from strategy import plan as PL
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2
    try:
        from strategy import observe as OB
    except Exception as exc:                                    # noqa: BLE001
        check("P0 strategy/observe.py exists (the observe set)", False, f"{type(exc).__name__}: {exc}")
        print(f"RED - {len(FAILED)} of {len(RAN)} failed: {' '.join(FAILED)}")
        return 1
    THREE = {"Breakout", "RunawayContinuation", "LiquidityHunt"}

    # ── ADMISSION ────────────────────────────────────────────────────────────
    pm = PM.PositionManager(paper_trading=True)

    def obs(hm, cap_intact=True, open_map=None):
        pm.open_by_strategy = (lambda: dict(open_map or {}))
        kw = dict(trading_day=True, orb_established=True, cap_intact=cap_intact,
                  past_hard_close=False, tries_used={})
        st = pm.logging_state(hm, **kw)
        return set(pm.observing(hm, st, **kw)) if hasattr(pm, "observing") else None

    o = obs((10, 45))
    check("A1 10:45 flat: the three are OBSERVED", o == THREE, f"{o}")
    check("A2 10:15: nothing observed (admitted for real)", obs((10, 15)) == set(), f"{obs((10, 15))}")
    a3 = (obs((15, 40)), obs((9, 31)))
    check("A3 15:40 and 09:31: nothing observed", a3 == (set(), set()), f"{a3}")
    a4 = obs((10, 45), cap_intact=False)
    check("A4 cap hit: nothing observed (only the window is lifted)", a4 == set(), f"{a4}")
    a5 = obs((10, 45), open_map={"Breakout": 1})
    check("A5 a Breakout open: Breakout NOT observed, the other two are",
          a5 == {"RunawayContinuation", "LiquidityHunt"}, f"{a5}")
    many = set()
    for hm in ((10, 31), (11, 30), (12, 30), (14, 0), (15, 39)):
        many |= (obs(hm) or set())
    check("A6 nothing outside the three is ever observed", many <= THREE, f"{many - THREE}")

    # ── PLANS ────────────────────────────────────────────────────────────────
    from strategy.breakout import Breakout
    from strategy.breakout_plan import BreakoutPlan
    from strategy.runaway_plan import RunawayPlan
    from strategy.liquidity_hunt import LiquidityHunt

    def entry_window_passed(name):
        """True when the plan's tick recorded entry_window as passed (it kept looking)."""
        if name == "Breakout":
            p = BreakoutPlan().prepare(spec=Breakout, orb=_ORB(), price_now=101.35, now_et="10:45",
                                       chain=None, df_1m=None, flow_conn=None, symbol="QQQ")
            return bool((p.conditions.get("entry_window") or (None, "", False))[2])
        if name == "RunawayContinuation":
            p = RunawayPlan().prepare(orb=_ORB(), atr_pct=0.2, price_now=101.35, now_et="10:45",
                                      chain=None, df_1m=None)
        else:
            p = LiquidityHunt().prepare(orb=_ORB(), price_now=101.35, now_et="10:45")
        return (p.tick.checks.get("entry_window") or (None, False))[1] is True

    OB.clear()
    p1 = {n: entry_window_passed(n) for n in sorted(THREE)}
    check("P1 NOT observed: each plan is DORMANT on entry_window at 10:45, as before",
          not any(p1.values()), f"{p1}")
    OB.set_active(THREE)
    p2 = {n: entry_window_passed(n) for n in sorted(THREE)}
    OB.clear()
    check("P2 observed: no plan goes dormant on entry_window - it keeps looking",
          all(p2.values()), f"{p2}")

    # ── TAKE ─────────────────────────────────────────────────────────────────
    def take(observed):
        plan = PL.Plan("Breakout", ("x",))
        calls = []
        plan._ledger_open = lambda *a, **k: calls.append("ledger")
        plan._report_fired = lambda *a, **k: calls.append("report")
        OB.set_active({"Breakout"} if observed else ())
        t = plan.tick(101.35)
        t.take(object())
        OB.clear()
        return t.verdict, calls

    v1, c1 = take(True)
    check("T1 observed: LOG-ONLY, no ledger row, the gate report not told",
          v1 == "LOG-ONLY" and not c1, f"verdict={v1} calls={c1}")
    v2, c2 = take(False)
    check("T2 CONTROL not observed: TAKE, the ledger row opens, the gate report is told",
          v2 == "TAKE" and "ledger" in c2 and "report" in c2, f"verdict={v2} calls={c2}")

    # ── THE DOORS ────────────────────────────────────────────────────────────
    import main as M

    class _Sig:
        def __init__(self, name, strike=753.0):
            self.strategy_name, self.direction, self.strike = name, "long", strike
            self.entry_premium, self.underlying_stop, self.is_valid = 1.15, 752.01, True

    OB.set_active({"Breakout"})
    _lo = getattr(M, "_log_only", None)
    if _lo is None:                      # the unfixed tree: a FAIL, never a crash (§40.1)
        def _lo(*_a, **_k):
            return "absent"
    d1 = (_lo(_Sig("Breakout"), {}), _lo(_Sig("GEXPinButterfly"), {}),
          _lo(_Sig("RunawayContinuation"), {}))
    check("D1 _log_only: True for the observed Breakout, False for anything else",
          d1 == (True, False, False), f"{d1}")

    seen = []
    orig = (M._stamp_vix, M.get_risk_manager, M.get_entry_engine)
    M._stamp_vix = lambda *a, **k: None                  # annotates the signal only (r200)
    M.get_risk_manager = lambda *a, **k: seen.append("risk") or (_ for _ in ()).throw(RuntimeError("stop"))
    M.get_entry_engine = lambda *a, **k: seen.append("entry") or (_ for _ in ()).throw(RuntimeError("stop"))
    try:
        M._execute_entry_signal(_Sig("Breakout"), {"macro": None}, None, None)
    except Exception as exc:                                    # noqa: BLE001
        seen.append(f"raised {type(exc).__name__}")
    M._stamp_vix, M.get_risk_manager, M.get_entry_engine = orig
    check("D2 _execute_entry_signal returns before any sizing, risk or entry work for an observed signal",
          seen == [], f"{seen}")

    records = []

    class _H(logging.Handler):
        def emit(self, r):
            if "[observe] LOG-ONLY" in r.getMessage():
                records.append(r.getMessage())
    h = _H()
    M.logger.addHandler(h)
    for _ in range(3):
        _lo(_Sig("Breakout", strike=754.0), {})
    M.logger.removeHandler(h)
    OB.clear()
    check("D3 one INFO line per setup (3 ticks -> 1 line), naming the pin gate's answer",
          len(records) == 1 and "pin" in records[0], f"{len(records)} line(s): {records[:1]}")

    import strategy.liquidity_hunt as LH
    from types import SimpleNamespace as NS

    def hunt_fire(observed):
        h = LH.LiquidityHunt()
        c = NS(strike=103.0, expiry="2026-10-05", mark=1.0)
        prep = NS(ready=True, unmet=[], structural=[], starved=[], contract=c, direction="long",
                  side="call", boundary=101.0, target=103.0, entry="A1", target_name="pdh",
                  em_frac=0.3, runway=2.0, leverage=1.0, tick=h.planner.tick(101.35),
                  trade_line=lambda: "test")
        h.prepare = lambda **kw: prep
        before = set(LH.FINISHED)
        OB.set_active({"LiquidityHunt"} if observed else ())
        try:
            h.generate_signal(orb=_ORB(), price_now=101.35, now_et="10:45")
        finally:
            OB.clear()
        added = set(LH.FINISHED) - before
        LH.FINISHED.difference_update(added)
        return added

    check("D4 an observed Hunt fire leaves FINISHED untouched", hunt_fire(True) == set())
    check("D5 CONTROL: a non-observed Hunt fire still adds its break to FINISHED",
          hunt_fire(False) == {("long", 101.0)})

    print(("RED - " + f"{len(FAILED)} of {len(RAN)} failed: " + " ".join(FAILED)) if FAILED
          else f"GREEN - {len(RAN)} of {len(RAN)} passed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
