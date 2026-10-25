#!/usr/bin/env python3
"""tests/check_eod_schedule.py — v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
THE OPERATOR'S END OF DAY, DRIVEN THROUGH THE REAL CODE UNDER A FROZEN CLOCK.

v1.3  2026-10-11 — OTV4TEST r268 (DEP.12) — E2b: THE FORK-ONLY eod_close_due ON A HALF DAY. check_half_day (byte-identical
      with otv4) pins every SHARED close site; eod_close_due is this tree's own (r149), so it is pinned here: on 2026-11-27
      (13:00 close) assignment risk is due at 12:45 (not 12:44), everything else at 12:50 (not 12:49); 11-25 at 12:50 is not due.

v1.2  2026-10-03 — OTV4TEST r191 (AUD.2) — E11 BUILDS THE REAL OptionsChain. Its fixture gave the chain
      `atm_iv=lambda: 0.14`, a METHOD, while the real OptionsChain.atm_iv is a PROPERTY - so
      position_manager's `chain.atm_iv()` passed here and raised "'float' object is not callable" on
      every live EOD pass since r149. A fixture built from the code's own belief (WA 0.4). E11 now
      stamps through the real class and expects the property's own median (0.16).

v1.1  2026-10-02 — OTV4TEST r187 (ROSTER.1) — E1 RE-POINTED BY THE RULING: "let's impose a 1029
      debit cutoff rule, but exempts the GEX pin fly". Runaway, Hunt, Breakout and VOLT end 10:30;
      the ORB row, SweepCreditSpread and TrendCreditSpread still end 15:40, and so does
      DEBIT_DIRECTIONAL_CUTOFF_ET (main's structure-keyed afternoon gate, now a later backstop).
      MOVED, NOT DROPPED: every row and the not-env-movable cutoff are still pinned.

v1.0  2026-09-26 — OTV4TEST r149 (EOD.1). Operator, 2026-09-26: debit window "A" (all day);
      "Stop entries at 1540"; "Resting limit orders at 1545, ladder exits at 1550 if they're
      not the assignment risk type"; cross at 15:55 ("Agree"); resting price "Best case on
      the trajectory (nickel close, 1 delta, etc)".

  E1  EOD_SCHEDULE holds 15:40 / 15:45 / 15:50 / 15:55; the seven directional + credit entry
      windows end at 15:40; the debit cutoff is 15:40 and OT_DEBIT_CUTOFF_ET no longer moves it
  E2  the clocks: assignment risk due at 15:45 (not 15:44); everything else at 15:50 (not 15:49);
      the ladder posts limits from 15:50 and crosses from 15:55
  E3  the classifier: vertical, trend leg, tent, butterfly, adopted short = assignment risk;
      so is any record with a short leg / fly body / condor-leg flag under an UNKNOWN strategy
      (fails toward risk); ORB / VOLT / Breakout singles are not
  E4  best-case prices: a worthless credit vertical rests at a NICKEL; an ITM one at its expiry
      cost; a pinned fly one tick under its value; a deep-ITM long at parity less a tick;
      no spot -> None (the caller falls back to the mark, never invents a price)
  E5  the policy: an assignment-risk hard close RESTS before 15:55 and CROSSES at 15:55 - a
      credit vertical included (r105's never-cross is superseded); a debit takes the ladder
  E6  the evaluators: a debit ORB record is NOT closed at 15:47 and IS at 15:50 with the ladder
      label; a credit vertical IS at 15:45 with the resting label
  E7  PAPER, the operator's rule ("latest possible close allowed by code ... or best-case available
      when deep ITM (par, nickel)"; "I want to be accustomed to seeing late closing orders"): NO
      end-of-day close fills before 15:55 — not when the mark touches its resting price, not when it
      is settled; at the 15:55 cross an unsettled close fills at the MARK and a SETTLED one (worthless
      vertical, deep-ITM long, IV present) at its best case (nickel / parity - tick); without IV
      nothing is settled, so it takes the mark
  E8  flatten_all at 15:46 closes the assignment-risk record and HOLDS the debit, and reports
      nothing FAILED before the cross; at 15:56 an unfilled close IS failed (so it pages)
  E9  no end-of-day label is typed as a literal in exit_engine / position_manager / main
  E10 the LIVE order path (a recording fake broker): at 15:46 a credit vertical posts its resting
      best case (a 0.05 debit) and a fly its best case (1.99 credit); at 15:55 the vertical CROSSES
      at its width (r105's never-cross superseded), the fly at one tick, and a debit single MARKET
  E12 THE CLOCK SEAMS: every evaluator's "is this close due" goes through
      exit_engine.is_hard_close_time AND reads the minute from exit_engine's own datetime —
      the two names eleven checkers pin the clock through; a third path to the wall clock
      made them pass before 15:45 and fail after it (measured on the r149 build, 15:55 ET)
  E13 THE BROKER CHECK FOLLOWS THE SCHEDULE (operator: "Agree"): main._intraday_reconcile_slot
      has wind-down slots at 15:45, 15:50, 15:55 (NEW — the pre-cross look) and 15:57; 15:54 is
      still the 15:50 slot, 15:55 is its own, and the day ends at 16:00
  E11 the resting price is the ESTIMATED VALUE BY 15:55 (operator 2026-09-26: "Can we instead
      estimate their assumed BY 1555 & rest that?"): with IV a pinned fly rests BELOW its expiry
      value (1.72, not 1.99) and a near-the-money vertical's buy-back ABOVE the nickel (0.09); a
      leg's own IV wins over the chain's ATM IV; flatten_all stamps each leg's chain IV and the
      ATM IV onto the record (E4 and E10 run WITHOUT IV and so pin the expiry-value fallback)

Run:  python3 tests/check_eod_schedule.py
"""
from __future__ import annotations

import ast
import datetime as D
import logging
import os
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
_s = tempfile.mkdtemp(prefix="check_eod_schedule.")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_s, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))
logging.disable(logging.CRITICAL)
ET = ZoneInfo("America/New_York")
PROBLEMS: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if detail and not ok else ""))
    if not ok:
        PROBLEMS.append(name.split()[0])


def at(h, m):
    return D.datetime(2026, 9, 28, h, m, 5, tzinfo=ET)          # a Monday


VERT = {"trade_id": "VERT0001", "strategy": "TrendCreditSpread", "short_symbol": "QQQ   260928C00750000",
        "long_symbol": "QQQ   260928C00751000", "spread_width": 1.0, "entry_premium": 0.40, "contracts": 1,
        "symbol": "QQQ"}
FLY = {"trade_id": "FLY00001", "strategy": "GEXPinButterfly", "is_butterfly": 1, "lower_symbol": "QQQ   260928C00740000",
       "center_symbol": "QQQ   260928C00742000", "upper_symbol": "QQQ   260928C00744000", "entry_premium": 0.40,
       "contracts": 1, "symbol": "QQQ"}
ORB = {"trade_id": "ORB00001", "strategy": "ORBStrategy", "option_symbol": "QQQ   260928C00730000",
       "entry_premium": 1.0, "contracts": 1, "symbol": "QQQ", "underlying_entry": 744.0}
SHORT = {"trade_id": "ADPT0001", "strategy": "ADOPTED", "option_symbol": "QQQ   260928P00740000",
         "is_short_position": 1, "entry_premium": 0.30, "contracts": 1, "symbol": "QQQ"}


def main() -> int:
    print("the operator's end of day (EOD.1)")
    import config
    from utils import time_utils as T
    from execution import limit_ladder as L
    from strategy import structure as S
    import execution.exit_engine as EE
    _real, _real_t = EE.now_et, T.now_et

    # E1
    try:
        EW, ES = config.ENTRY_WINDOWS, getattr(config, "EOD_SCHEDULE", {})
        six = ("ORBStrategy", "RunawayContinuation", "LiquidityHunt", "Breakout", "VOLT", "SweepCreditSpread", "TrendCreditSpread")
        env = dict(os.environ, OT_DEBIT_CUTOFF_ET="11:30")
        r = subprocess.run([sys.executable, "-c", "import config; print(tuple(config.DEBIT_DIRECTIONAL_CUTOFF_ET))"],
                           cwd=ROOT, env=env, capture_output=True, text=True)
        check("E1 schedule 15:40/15:45/15:50/15:55, ORB/credit windows end 15:40, the four directional debits 10:30 (r187), afternoon cutoff 15:40 and not env-movable",
              ES == {"entries_stop": (15, 40), "resting_at": (15, 45), "ladder_at": (15, 50), "cross_at": (15, 55)}
              and all(tuple(EW[n][1]) == ((10, 30) if n in ("RunawayContinuation", "LiquidityHunt", "Breakout", "VOLT")
                                          else (15, 40)) for n in six)
              and tuple(config.DEBIT_DIRECTIONAL_CUTOFF_ET) == (15, 40) and r.stdout.strip() == "(15, 40)",
              f"ES={ES} ends={[EW[n][1] for n in six]} cutoff={config.DEBIT_DIRECTIONAL_CUTOFF_ET} env-run={r.stdout.strip() or r.stderr[-120:]}")
    except Exception as exc:                                  # noqa: BLE001
        check("E1 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    # E2
    try:
        e2 = (not T.eod_close_due(True, at(15, 44)) and T.eod_close_due(True, at(15, 45))
              and not T.eod_close_due(False, at(15, 49)) and T.eod_close_due(False, at(15, 50))
              and L.hard_close_order_mode(at(15, 49)) == "none" and L.hard_close_order_mode(at(15, 50)) == "limit"
              and L.hard_close_order_mode(at(15, 54)) == "limit" and L.hard_close_order_mode(at(15, 55)) == "market")
        check("E2 clocks: risk 15:45, others 15:50, ladder limits 15:50, cross 15:55", e2)
    except Exception as exc:                                  # noqa: BLE001
        check("E2 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    # E2b (r268, DEP.12) — the fork-only eod_close_due moves to a half day's bell
    try:
        def _hd(day, h, m):
            return D.datetime(2026, 11, day, h, m, 5, tzinfo=ET)
        e2b = (not T.eod_close_due(True, _hd(27, 12, 44)) and T.eod_close_due(True, _hd(27, 12, 45))
               and not T.eod_close_due(False, _hd(27, 12, 49)) and T.eod_close_due(False, _hd(27, 12, 50))
               and not T.eod_close_due(False, _hd(25, 12, 50)) and not T.eod_close_due(True, _hd(25, 15, 44)))
        check("E2b half day 11-27: risk due 12:45, others 12:50; full day 11-25 unchanged", e2b)
    except Exception as exc:                                  # noqa: BLE001
        check("E2b (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    # E3
    try:
        trend_leg = dict(VERT)
        tent = {"strategy": "TrendCreditSpread", "setup_type": "tent_hedge", "short_symbol": "a", "long_symbol": "b", "lower_symbol": "c"}
        risk = [S.has_assignment_risk(x) for x in (VERT, trend_leg, FLY, SHORT, tent)]
        none = [S.has_assignment_risk(x) for x in (ORB, {"strategy": "VOLT", "option_symbol": "x"},
                                                    {"strategy": "Breakout", "option_symbol": "x"})]
        _struct = [S.has_assignment_risk(r) for r in ({"strategy": "SomethingNew", "short_symbol": "x", "long_symbol": "y"},
                                                      {"strategy": "SomethingNew", "center_symbol": "x"},
                                                      {"is_condor_leg": 1})]
        risk = list(risk) + _struct
        check("E3 classifier: short legs are assignment risk (by STRUCTURE even under an unknown strategy), long singles are not",
              all(risk) and not any(none) and S.is_tent(tent),
              f"risk={risk} none={none}")
    except Exception as exc:                                  # noqa: BLE001
        check("E3 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    # E4
    try:
        B = EE.ExitEngine._eod_best_case
        def bc(rec, spot):
            rr = dict(rec); rr["_eod_spot"] = spot
            got = B(rr)
            return None if got is None else (got[0], got[1])
        got = [bc(VERT, 745.0), bc(VERT, 750.60), bc(FLY, 742.0), bc(ORB, 745.0), bc(SHORT, 738.0), bc(VERT, 0)]
        want = [(0.05, "buy"), (0.60, "buy"), (1.99, "sell"), (14.99, "sell"), (2.00, "buy"), None]
        check("E4 best case: nickel, expiry cost, fly-1 tick, parity-1 tick, short buy-back, no spot->None",
              got == want, f"got {got} want {want}")
    except Exception as exc:                                  # noqa: BLE001
        check("E4 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    # E5
    try:
        pol = EE.ExitEngine._exit_policy
        _real = EE.now_et
        try:
            EE.now_et = lambda: at(15, 46)
            p1 = (pol(VERT, "hard_close_resting_15:45_ET"), pol(FLY, "hard_close_resting_15:45_ET"),
                  pol(ORB, "hard_close_ladder_15:50_ET"))
            EE.now_et = lambda: at(15, 55)
            p2 = (pol(VERT, "hard_close_resting_15:45_ET"), pol(FLY, "hard_close_resting_15:45_ET"))
        finally:
            EE.now_et = _real
        check("E5 policy: resting before 15:55, cross at 15:55 (credits too), debits ladder",
              p1 == ("eod_resting", "eod_resting", "debit_hard_close") and p2 == ("eod_cross", "eod_cross"), f"{p1} {p2}")
    except Exception as exc:                                  # noqa: BLE001
        check("E5 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    # E6
    try:
        _real_t, _real_dt = T.now_et, EE.datetime
        def _freeze(h, m):
            T.now_et = lambda: at(h, m)
            class _F(D.datetime):
                @classmethod
                def now(cls, tz=None):
                    return at(h, m) if tz is None else at(h, m).astimezone(tz)
            EE.datetime = _F
        try:
            _freeze(15, 47)
            d_orb_47 = EE._eod_due(ORB); d_v_47 = EE._eod_due(VERT)
            _freeze(15, 50)
            d_orb_50 = EE._eod_due(ORB)
        finally:
            T.now_et, EE.datetime = _real_t, _real_dt
        check("E6 evaluators: debit held at 15:47, due at 15:50 (ladder label); vertical due at 15:45 (resting label)",
              (not d_orb_47) and d_orb_50 and d_v_47 and EE._eod_label(ORB) == "hard_close_ladder_15:50_ET"
              and EE._eod_label(VERT) == "hard_close_resting_15:45_ET",
              f"orb47={d_orb_47} orb50={d_orb_50} v47={d_v_47} labels={EE._eod_label(ORB)},{EE._eod_label(VERT)}")
    except Exception as exc:                                  # noqa: BLE001
        check("E6 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    # E7
    try:
        eng = EE.ExitEngine(paper_trading=True) if "paper_trading" in EE.ExitEngine.__init__.__code__.co_varnames else EE.get_exit_engine(True)
        out = []
        vivs = {VERT["short_symbol"]: 0.15, VERT["long_symbol"]: 0.15}
        cases = (((15, 46), VERT, 749.90, vivs, 0.0, 0.05, "hard_close_resting_15:45_ET"),   # unsettled, mark touches -> held
                 ((15, 46), VERT, 745.00, vivs, 0.0, 0.20, "hard_close_resting_15:45_ET"),   # settled -> STILL held (late)
                 ((15, 54), ORB, 745.00, {}, 0.15, 15.20, "hard_close_ladder_15:50_ET"),     # settled debit -> held (late)
                 ((15, 55), VERT, 749.90, vivs, 0.0, 0.12, "hard_close_resting_15:45_ET"),   # cross, unsettled -> the mark
                 ((15, 55), VERT, 745.00, vivs, 0.0, 0.20, "hard_close_resting_15:45_ET"),   # cross, settled worthless -> nickel
                 ((15, 55), ORB, 745.00, {}, 0.15, 15.20, "hard_close_ladder_15:50_ET"),     # cross, settled deep ITM -> parity - tick
                 ((15, 55), ORB, 730.40, {}, 0.15, 0.60, "hard_close_ladder_15:50_ET"),      # cross, near the money -> the mark
                 ((15, 55), VERT, 745.00, {}, 0.0, 0.20, "hard_close_resting_15:45_ET"))     # cross, no IV -> the mark
        try:
            for hm, base, spot, legiv, atm, mark, why in cases:
                EE.now_et = (lambda h=hm: at(*h))
                rec = dict(base); rec["_eod_spot"] = spot; rec["_eod_iv"] = legiv; rec["_eod_iv_atm"] = atm
                fr = eng.place_exit_order(rec, why, mark_price=mark)
                out.append((bool(fr.confirmed), None if fr.fill_price is None else round(float(fr.fill_price), 2)))
        finally:
            EE.now_et = _real
        want = [(False, None), (False, None), (False, None), (True, 0.12), (True, 0.05), (True, 14.99), (True, 0.60), (True, 0.20)]
        check("E7 paper: nothing fills before 15:55; at the cross unsettled -> mark, settled -> nickel / parity-tick, no IV -> mark",
              out == want, f"got {out} want {want}")
    except Exception as exc:                                  # noqa: BLE001
        check("E7 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    # E8
    try:
        from execution import position_manager as PM
        pm = PM.PositionManager.__new__(PM.PositionManager)
        called: list = []
        pm._open_records = [dict(VERT), dict(ORB)]
        pm._trade_logger = None
        pm._fetch_current_premium = lambda rec, chain=None: 0.20
        pm._execute_exit = lambda rec, dec, prem: (called.append((rec["trade_id"], dec.exit_reason, rec.get("_eod_spot"))) or False)
        try:
            T.now_et = lambda: at(15, 46)
            f46 = pm.flatten_all(spot=745.0)
            c46 = list(called); called.clear()
            T.now_et = lambda: at(15, 56)
            f56 = pm.flatten_all(spot=745.0)
            c56 = list(called)
        finally:
            T.now_et = _real_t
        check("E8 flatten 15:46: vertical closing (resting label, spot stamped), debit HELD, nothing failed; 15:56: unfilled FAILED",
              c46 == [("VERT0001", "hard_close_resting_15:45_ET", 745.0)] and f46 == []
              and sorted(t for t, _r, _s in c56) == ["ORB00001", "VERT0001"] and sorted(f56) == ["ORB00001", "VERT0001"],
              f"c46={c46} f46={f46} c56={c56} f56={f56}")
    except Exception as exc:                                  # noqa: BLE001
        check("E8 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    # E9
    try:
        typed = []
        for f in ("execution/exit_engine.py", "execution/position_manager.py", "main.py"):
            tree = ast.parse(open(os.path.join(ROOT, f)).read())
            for n in ast.walk(tree):
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) < 40:
                    import re
                    if re.fullmatch(r"hard_close(_\w+)?_\d\d:\d\d_ET", n.value):
                        typed.append(f"{f}:{n.lineno} {n.value}")
        check("E9 no end-of-day label typed as a literal", not typed, "; ".join(typed))
    except Exception as exc:                                  # noqa: BLE001
        check("E9 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    # E10
    try:
        import types as _ty
        placed = []
        class _Acct:
            def place_order(self, session, order, dry_run=False):
                placed.append(order)
                return _ty.SimpleNamespace(errors=None, order=_ty.SimpleNamespace(id=1))
        _gs, _ga = EE.get_session, EE.get_account
        EE.get_session, EE.get_account = (lambda: object()), (lambda: _Acct())
        live = EE.ExitEngine(paper_trading=False)
        got = []
        try:
            for hm, rec, spot, mark, why in (((15, 46), VERT, 745.0, 0.20, "hard_close_resting_15:45_ET"),
                                             ((15, 46), FLY, 742.0, 1.50, "hard_close_resting_15:45_ET"),
                                             ((15, 55), VERT, 745.0, 0.20, "hard_close_resting_15:45_ET"),
                                             ((15, 55), FLY, 742.0, 1.50, "hard_close_resting_15:45_ET"),
                                             ((15, 55), ORB, 745.0, 15.0, "hard_close_ladder_15:50_ET")):
                EE.now_et = (lambda h=hm: at(*h))
                r = dict(rec); r["_eod_spot"] = spot
                placed.clear()
                live._submit_live_close(r, 1, mark, reason=why)
                o = placed[-1] if placed else None
                got.append(None if o is None else (str(getattr(o, "order_type", "")).split(".")[-1].upper(),
                                                   None if getattr(o, "price", None) is None else float(o.price)))
        finally:
            EE.get_session, EE.get_account, EE.now_et = _gs, _ga, _real
        want = [("LIMIT", -0.05), ("LIMIT", 1.99), ("LIMIT", -1.0), ("LIMIT", 0.01), ("MARKET", None)]
        check("E10 live orders: resting best case at 15:46, every structure crosses at 15:55", got == want,
              f"got {got} want {want}")
    except Exception as exc:                                  # noqa: BLE001
        check("E10 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    # E11
    try:
        B = EE.ExitEngine._eod_best_case
        def bc2(rec, spot, legiv=None, atm=0.0):
            rr = dict(rec); rr["_eod_spot"] = spot; rr["_eod_iv_atm"] = atm
            if legiv is not None:
                rr["_eod_iv"] = legiv
            got = B(rr)
            return None if got is None else (got[0], got[1])
        vlegs = {VERT["short_symbol"]: 0.15, VERT["long_symbol"]: 0.15}
        got = [bc2(FLY, 742.0, atm=0.15), bc2(VERT, 749.90, legiv=vlegs), bc2(VERT, 749.90, legiv=vlegs, atm=0.60),
               bc2(VERT, 749.90, atm=0.60)]
        want = [(1.72, "sell"), (0.09, "buy"), (0.09, "buy")]
        ok_px = got[:3] == want and got[3] is not None and got[3][0] > 0.09
        import types as _ty
        from execution import position_manager as PM
        pm = PM.PositionManager.__new__(PM.PositionManager)
        seen: list = []
        pm._open_records = [dict(VERT)]
        pm._trade_logger = None
        pm._fetch_current_premium = lambda rec, chain=None: 0.20
        pm._execute_exit = lambda rec, dec, prem: (seen.append((rec.get("_eod_iv"), rec.get("_eod_iv_atm"))) or False)
        # r191: the REAL chain classes. The old fixture made atm_iv a lambda, so flatten_all's
        # `chain.atm_iv()` passed here while the real property raised on every live EOD pass.
        from data.options_chain import OptionContract as _OC, OptionsChain as _OCh
        C = lambda sym, k, iv: _OC(symbol=sym, strike=k, iv=iv)
        chain = _OCh(underlying="QQQ", spot_price=749.9,
                     calls=[C(VERT["short_symbol"], 750.0, 0.15), C(VERT["long_symbol"], 751.0, 0.16),
                            C("QQQ   260928C00760000", 760.0, 0.3)], puts=[])
        try:
            T.now_et = lambda: at(15, 46)
            pm.flatten_all(chain=chain, spot=749.9)
        finally:
            T.now_et = _real_t
        want_stamp = [({VERT["short_symbol"]: 0.15, VERT["long_symbol"]: 0.16}, 0.16)]   # ATM = the real property's median
        check("E11 rest at the 15:55 estimate: fly 1.72 < 1.99, vertical 0.09 > nickel, leg IV wins, flatten_all stamps IVs",
              ok_px and seen == want_stamp, f"prices {got} want {want} (+4th > 0.09); stamp {seen} want {want_stamp}")
    except Exception as exc:                                  # noqa: BLE001
        check("E11 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    # E12
    try:
        _hc = EE.is_hard_close_time
        _freeze(15, 50)
        try:
            EE.is_hard_close_time = lambda: False
            off = [EE._eod_due(dict(r)) for r in (VERT, FLY, ORB, SHORT)]
            EE.is_hard_close_time = lambda: True
            on = [EE._eod_due(dict(r)) for r in (VERT, FLY, ORB, SHORT)]
            class _F1030(D.datetime):          # the second seam ALONE: exit_engine's datetime at 10:30,
                @classmethod                   # while time_utils' clock stays at 15:50
                def now(cls, tz=None):
                    return at(10, 30) if tz is None else at(10, 30).astimezone(tz)
            EE.datetime = _F1030
            EE.is_hard_close_time = lambda: True
            early = [EE._eod_due(dict(r)) for r in (VERT, FLY, ORB, SHORT)]
        finally:
            EE.is_hard_close_time = _hc
            T.now_et, EE.datetime = _real_t, _real_dt
        check("E12 clock seams: 15:50 + is_hard_close_time False -> nothing due; True -> all due; exit_engine's datetime at 10:30 -> nothing due",
              not any(off) and all(on) and not any(early), f"off={off} on={on} early={early}")
    except Exception as exc:                                  # noqa: BLE001
        check("E12 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    # E13
    try:
        import importlib
        M = importlib.import_module("main")
        f = M._intraday_reconcile_slot
        slots = {hm: (f(at(*hm)) or "")[-5:] for hm in ((15, 44), (15, 45), (15, 49), (15, 50), (15, 54), (15, 55), (15, 56), (15, 57), (15, 59), (16, 0))}
        want = {(15, 44): "15:40", (15, 45): "15:45", (15, 49): "15:45", (15, 50): "15:50", (15, 54): "15:50",
                (15, 55): "15:55", (15, 56): "15:55", (15, 57): "15:57", (15, 59): "15:57", (16, 0): ""}
        check("E13 broker check at 15:45 / 15:50 / 15:55 (pre-cross) / 15:57", slots == want,
              f"got {slots}")
    except Exception as exc:                                  # noqa: BLE001
        check("E13 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    print("GREEN" if not PROBLEMS else f"RED — {len(PROBLEMS)} failed: {', '.join(PROBLEMS)}")
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
