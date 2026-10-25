#!/usr/bin/env python3
"""
tests/check_condor_mgmt.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.2  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.1  2026-09-09  OTV4TEST r11 — R1–R5: the widened-wing roll (the operator's picture),
      the prepared roll on the row, the group final-form floor, the rich complement,
      the tent retired. C7's tent-record pin is kept as history of the as-formed basis rule.
v1.0  2026-09-09  OTV4TEST r10 — THE CONDOR MANAGEMENT PLAN (PLAN_SPEC §35).

  C1  tested by WICK: the closed bar's high reaches the short call, close inside -> call tested
  C2  a close BEYOND the short is not "tested" (it is the tent's breach) -> None from classify
  C3  no wick to either short -> None (the proximity rule does not fire when a frame is given)
  C4  no frame -> the proximity fallback still works
  C5  a lone call vertical's management row names the complement it waits on (a sweep below)
  C6  IronCondorStrategy is not an entry: main.py's dispatch skips it with the reason
  C7  the final-form (tent) floor is 15% from the structure AS FORMED, not cumulative credit

Born red at r9 on C2 (proximity said "tested") and C5 (no complement named).
Run:  python3 tests/check_condor_mgmt.py
"""
import os
import sqlite3
import sys
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


def _frame(rows, start="13:00"):
    import pandas as pd
    return pd.DataFrame([{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in rows],
                        index=pd.date_range(f"2026-09-09 {start}", periods=len(rows), freq="1min"))


def main():
    from strategy.condor_roll import classify_tested
    legs = [{"option_side": "call", "short_strike": 720.0, "long_strike": 722.0},
            {"option_side": "put", "short_strike": 712.0, "long_strike": 710.0}]
    t, u = classify_tested(legs, 716.0, df_1m=_frame([(719.4, 720.3, 719.2, 719.8), (719.8, 720.0, 719.6, 719.9)]))
    check("C1 wick to the short call, close inside -> call TESTED", t is legs[0] and u is legs[1])
    t, u = classify_tested(legs, 720.6, df_1m=_frame([(719.4, 720.9, 719.2, 720.6), (720.6, 720.8, 720.4, 720.7)]))
    check("C2 a CLOSE beyond the short is breached, not tested -> None", t is None)
    t, u = classify_tested(legs, 719.5, df_1m=_frame([(719.0, 719.6, 718.8, 719.5), (719.5, 719.7, 719.3, 719.6)]))
    check("C3 price near but no wick to the short -> None (no proximity with a frame)", t is None)
    t, u = classify_tested(legs, 719.5)
    check("C4 no frame -> the proximity fallback still says call tested", t is legs[0])

    # C5: the lone-vertical row names the complement from the sweep plan's last preparation
    from strategy import plan as P
    class St:
        def __init__(s): s.conn = sqlite3.connect(":memory:"); s.conn.row_factory = sqlite3.Row
        def commit(s): s.conn.commit()
    st = St(); P.ensure_tables(st); P.bind_store(st)
    import strategy.sweep_plan as sp
    class _C:
        def __init__(s, k, m): s.strike, s.mark = float(k), m
    cand = sp.Candidate({"level_id": "x", "price": 713.5, "kind": "support", "provenance": "london"})
    cand.short, cand.long, cand.credit, cand.width, cand.r, cand.richness = _C(713, 0.4), _C(712, 0.21), 0.19, 1.0, 0.23, 0.19
    fake = types.SimpleNamespace(nearest_below=cand, nearest_above=None)
    sp.LAST_PREP = fake
    from strategy.iron_condor_strategy import IronCondorStrategy
    IC = IronCondorStrategy()
    class _PM:
        def get_open_records(self):
            return [{"option_side": "call", "short_strike": 720.0, "long_strike": 722.0,
                     "is_credit_vertical": 1, "status": "open", "trade_id": "c1", "strategy": "SweepCreditSpread"}]
    P.begin_tick(1.0)
    out = IC.manage(_PM(), None, 716.0)
    P.close_tick(st, "TST")
    r = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='CondorManagement' ORDER BY rowid DESC LIMIT 1").fetchone()
    check("C5 a lone call vertical's row names the complement: a sweep REJECTED below, with the structure",
          out == "LONE" and r and r["verdict"] == "HOLD" and "sweep REJECTED below" in r["reason"]
          and "713/712P" in r["reason"], str(dict(r) if r else None)[:160])

    msrc = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    check("C6 IronCondorStrategy is retired as an entry (dispatch names the reason)",
          "retired as a" in msrc and 'slot claimed by {signal.strategy_name}")\n    elif DIRECTIONAL_ONLY:\n        _plan_skip("IronCondorStrategy"' not in msrc)

    # C7 — the final-form floor is measured from the structure AS FORMED, not cumulative credit
    import datetime as _dt
    from zoneinfo import ZoneInfo
    import execution.exit_engine as XE
    _rdt, _rhc = XE.datetime, XE.is_hard_close_time
    class _F(_dt.datetime):
        @classmethod
        def now(cls, tz=None): return _dt.datetime(2026, 9, 9, 14, 0, tzinfo=ZoneInfo("America/New_York"))
    XE.datetime = _F; XE.is_hard_close_time = lambda: False
    try:
        xe = XE.ExitEngine(paper_trading=True)
        rec = {"trade_id": "t1", "strategy": "IronCondorStrategy", "setup_type": "tent", "is_tent": 1,
               "option_side": "put", "entry_premium": 1.00, "final_form_basis": 1.00, "cumulative_credit": 3.40,
               "contracts": 1, "status": "open", "stop_premium": 1.15}
        d_hold = xe._evaluate_tent(dict(rec), 1.10)
        d_exit = xe._evaluate_tent(dict(rec), 1.16)
        check("C7 the tent floor is 15% from the structure AS FORMED (basis 1.00 -> 1.15), not 15% of cumulative 3.40",
              (not d_hold.should_exit) and d_exit.should_exit and "as formed" in str(d_exit.exit_reason),
              str(d_exit.exit_reason))
        csrc = open(os.path.join(_root, "strategy", "condor_roll.py"), encoding="utf-8").read()
        check("C7b the tent record's floor basis is the as-formed cost, cumulative credit kept alongside",
              "entry_premium=form_basis" in csrc and "cumulative_credit=cum" in csrc)
    finally:
        XE.datetime, XE.is_hard_close_time = _rdt, _rhc

    # ── r11: the widened-wing roll, the prepared roll, the group floor, the rich complement ──
    from strategy.condor_roll import find_risk_free_roll
    class _K:
        def __init__(s, k, m): s.strike, s.mark, s.symbol = float(k), m, f"O{k}"
    # operator's picture: 360/370C breached at 364; put marks fall with distance
    puts = [_K(360, 6.10), _K(355, 3.60), _K(350, 2.20), _K(345, 1.40), _K(340, 0.95), _K(337.5, 0.75), _K(330, 0.35)]
    chain = types.SimpleNamespace(puts=puts, calls=[])
    tested = {"option_side": "call", "short_strike": 360.0, "long_strike": 370.0, "spread_width": 10.0}
    untested = {"option_side": "put", "short_strike": 345.0, "long_strike": 340.0, "spread_width": 5.0, "contracts": 1}
    plan = find_risk_free_roll(tested, untested, chain, 364.0, banked_credit=4.725)
    # banked 4.725 + credit - close cost 0.45 (345/340) must reach 10: 360/337.5 gives 9.63 (short),
    # 360/330 gives 10.03 -> the narrowest wing at the tested short that CLEARS
    check("R1 the roll WIDENS its wing at the tested short's own strike until the credit clears the tested width",
          plan is not None and plan.risk_free and plan.new_short_strike == 360.0 and plan.new_long_strike == 330.0,
          f"plan={plan and (plan.new_short_strike, plan.new_long_strike, round(plan.total_credit_after, 2), plan.risk_free)}")
    check("R1b ...and it is the NARROWEST wing that clears (337.5 falls 0.37 short, 330 is the first that does)",
          plan is not None and plan.new_long_strike == 330.0 and round(plan.total_credit_after, 2) == 10.03)
    thin = types.SimpleNamespace(puts=[_K(360, 1.0), _K(355, 0.9), _K(350, 0.85), _K(345, 0.84), _K(340, 0.83), _K(330, 0.8)], calls=[])
    plan2 = find_risk_free_roll(tested, untested, thin, 364.0, banked_credit=4.725)
    check("R2 no combination clears -> best-by-credit returned, NOT risk-free (rung 2: stop and page)",
          plan2 is not None and not plan2.risk_free)
    # R3 the management row prepares the roll while nothing is tested
    class _PM2:
        def get_open_records(self):
            return [dict(tested, is_condor_leg=1, trade_id="c", credit_received=4.725, entry_premium=4.725, status="open"),
                    dict(untested, is_condor_leg=1, trade_id="p", credit_received=1.0, entry_premium=1.0, status="open")]
    IC2 = IronCondorStrategy()
    P.begin_tick(2.0)
    out = IC2.manage(_PM2(), chain, 352.0, df_1m=_frame([(352.0, 352.4, 351.6, 352.1), (352.1, 352.3, 351.9, 352.0)]))
    P.close_tick(st, "TST")
    r = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='CondorManagement' ORDER BY rowid DESC LIMIT 1").fetchone()
    check("R3 formed, nothing tested -> the row carries the PREPARED roll for each side",
          out == "HOLD" and r and "Prepared:" in r["reason"] and "if the call side were tested" in r["reason"],
          (r["reason"][:160] if r else "none"))
    # R6 whipsaw: after the roll the rolled side gets tested -> the row names it and the floor governs
    class _PM3:
        def get_open_records(self):
            return [dict(tested, is_condor_leg=1, is_broken_wing=1, trade_id="c", credit_received=4.725,
                         entry_premium=4.725, current_premium=0.30, status="open", final_form_basis=6.0,
                         final_form_group="ff-c", setup_type="condor leg"),
                    {"option_side": "put", "short_strike": 360.0, "long_strike": 330.0, "spread_width": 30.0,
                     "is_condor_leg": 1, "is_broken_wing": 1, "trade_id": "p", "credit_received": 5.75,
                     "entry_premium": 5.75, "current_premium": 6.10, "status": "open", "final_form_basis": 6.0,
                     "final_form_group": "ff-c", "setup_type": "BWB rolled put vertical"}]
    IC3 = IronCondorStrategy()
    P.begin_tick(3.0)
    out = IC3.manage(_PM3(), chain, 359.0, df_1m=_frame([(361.0, 361.2, 359.6, 360.4), (360.4, 360.6, 360.1, 360.3)]))
    P.close_tick(st, "TST")
    r = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='CondorManagement' ORDER BY rowid DESC LIMIT 1").fetchone()
    check("R6 WHIPSAW: the rolled put side is tested after the roll -> FINAL FORM row names it, the floor governs",
          out == "FINAL" and r and "WHIPSAW" in r["reason"] and "floor" in r["reason"], (r["reason"][:170] if r else "none"))
    # R4 the final-form floor is one floor for the whole structure
    try:
        XE.datetime = _F; XE.is_hard_close_time = lambda: False
        xe = XE.ExitEngine(paper_trading=True)
        import database.trade_logger as TL
        _real_tl = TL.get_trade_logger
        sib = {"trade_id": "p2", "final_form_group": "ff-c", "current_premium": 4.0, "option_side": "put",
               "is_condor_leg": 1, "symbol": "TST"}
        TL.get_trade_logger = lambda: types.SimpleNamespace(get_open_trades=lambda: [sib])
        xe._condor_sibling_open = lambda *a, **k: True
        xe._sync_stop_suppression = lambda *a, **k: None
        rec = {"trade_id": "c2", "strategy": "IronCondorStrategy", "setup_type": "x", "option_side": "call",
               "entry_premium": 4.725, "contracts": 1, "status": "open", "stop_premium": 0.0, "is_condor_leg": 1,
               "is_credit_vertical": 1, "is_broken_wing": 1, "final_form_group": "ff-c", "final_form_basis": 10.0,
               "spread_width": 10.0, "symbol": "TST"}
        d_hold = xe._evaluate_condor_leg(dict(rec), 7.0, df_1m=None)      # 7.0 + 4.0 = 11.0 < 11.5
        d_exit = xe._evaluate_condor_leg(dict(rec), 7.6, df_1m=None)      # 7.6 + 4.0 = 11.6 >= 11.5
        check("R4 the final-form floor sums BOTH legs against the as-formed basis (10.0 -> 11.5)",
              (not d_hold.should_exit) and d_exit.should_exit and "final_form_floor" in str(d_exit.exit_reason),
              str(d_exit.exit_reason)[:120])
        TL.get_trade_logger = _real_tl
    finally:
        XE.datetime, XE.is_hard_close_time = _rdt, _rhc
    # R5 the complement must be at least as rich as leg one
    import strategy.sweep_plan as spm
    src = open(os.path.join(_root, "strategy", "sweep_plan.py"), encoding="utf-8").read()
    check("R5 the sweep plan refuses a thinner complement by name (complement_richness)",
          "complement_richness" in spm.SweepPlan.PLAN_CHECKS and "not rich enough to complete a condor" in src)
    msrc2 = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    check("R5b main hands the complement leg one's richness; the tent call is gone",
          "complement_min_richness=_leg1_rich" in msrc2 and "check_and_execute_tent(pos_mgr" not in msrc2)

    print()
    if FAILED:
        print(f"FAIL — {len(FAILED)} check(s): {FAILED}"); return 1
    print("PASS — check_condor_mgmt"); return 0


if __name__ == "__main__":
    sys.exit(main())
