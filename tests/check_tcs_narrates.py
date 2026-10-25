#!/usr/bin/env python3
"""
tests/check_tcs_narrates.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.3  2026-10-19  OTV4TEST r303 (PSTATE.1) — its subject TrendCreditSpread is DORMANT by default and a dormant plan now writes
      nothing by ruling, so this run switches it ACTIVE (OT_TCS_ACTIVE=1); what it pins is unchanged.
v1.2  2026-09-23  OTV4TEST r112 — the r106 venv bootstrap; red under system python3 on `pytz`.
v1.1  2026-09-09  OTV4TEST r9 — re-pointed at the TCS plan (store-driven, EM input); the
      rule it pins is unchanged: a named row on every path, never NOT ASKED.
v1.0  2026-09-09  OTV4TEST r8 — TCS WRITES A ROW ON EVERY PATH. The dashboard on
      2026-09-09 showed TrendCreditSpread "NO PLAN — ASKED and returned None but
      wrote no plan row" through the whole credit window: r238's prepare()
      returned with the tick OPEN on the common path (no accepted 50), the
      retaken-50 path, and every structural refusal. Operator: "NO PLAN is
      unacceptable during the TCS window." Drives the REAL strategy on five
      ticks and asserts a named row each time. Born red at r7 on T1–T4.

Run:  python3 tests/check_tcs_narrates.py
"""
import os
import sqlite3
import sys
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ["OT_TCS_ACTIVE"] = "1"   # r303: the subject writes (check_plan_states pins dormant)
# r112 — the r106 venv bootstrap: the lander runs CHECKs under system python3,
# where `pytz` (and pandas) are absent, so this checker could never be DECLARED.
import glob as _glob
for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


class _St:
    def __init__(s):
        s.conn = sqlite3.connect(":memory:"); s.conn.row_factory = sqlite3.Row
    def commit(s): s.conn.commit()


class _C:
    def __init__(s, k, b, a):
        s.strike, s.bid, s.ask, s.mark = float(k), b, a, (a + b) / 2
        s.delta, s.gamma, s.theta, s.expiry, s.open_interest, s.symbol = 0.2, 0.01, -0.03, "x", 100, f"P{k}"


def main():
    from strategy import plan as P
    st = _St(); P.ensure_tables(st); P.bind_store(st)
    import strategy.trend_credit_spread as tcs
    import strategy.tcs_plan as tp
    import tempfile
    from data.derived_store import DerivedStore
    _ds = DerivedStore(path=os.path.join(tempfile.mkdtemp(), "derived.db"))
    tp._symbol_of = lambda: "TST"
    _end = tp.TCS_ENTRY_END_ET; tp.TCS_ENTRY_END_ET = (16, 0)
    from datetime import datetime
    now = datetime(2026, 9, 9, 13, 0, tzinfo=tcs.ET)
    T = tcs.TrendCreditSpread(); T.planner.symbol = "TST"; T.plan._store = _ds
    ms = types.SimpleNamespace(adx=25.0, trend_direction="up", structure_sequence="HH", flat_angle_deg=10.0)
    vol = types.SimpleNamespace(atr=0.5, atr_pct=0.1, price_vs_vwap="ABOVE")
    good = types.SimpleNamespace(puts=[_C(101, 1.4, 1.44), _C(100, 0.9, 0.94), _C(99, 0.5, 0.54),
                                       _C(98, 0.2, 0.24), _C(95, 0.04, 0.06)], calls=[])

    def row():
        r = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='TrendCreditSpread' "
                            "ORDER BY rowid DESC LIMIT 1").fetchone()
        return (r["verdict"], r["reason"] or "") if r else ("", "")

    def tick(n, acc, px, chain):
        orb = types.SimpleNamespace(state="ARMED_LONG", invalidation_reason="", break_direction="long",
                                    orb_high=101.0, orb_low=100.0, target_50pct=101.5,
                                    fifty_accepted=acc, bars_since_break=3)
        P.begin_tick(n)
        sig = T.generate_signal(ms=ms, vol_state=vol, chain=chain, macro=None, current_price=px, trend=None,
                                orb=orb, condor_active=False, now_et=now, atm_iv=(0.2 if acc else None))
        P.close_tick(st, "TST")
        return sig, row()

    try:
        _, r = tick(1.0, False, 101.9, good)
        check("T1 no ATM IV -> NO PLAN naming atm_iv (r9: the EM is an input), never NOT ASKED",
              r[0] == "NO PLAN" and "atm_iv" in r[1], str(r)[:120])
        _, r = tick(2.0, True, 100.9, good)
        check("T2 in window, nothing accepted -> HOLD naming the wait", r[0] == "HOLD" and "Waiting on" in r[1], str(r)[:120])
        _, r = tick(3.0, True, 101.9, None)
        check("T3 no chain -> a named NO PLAN, never NOT ASKED", r[0] in ("DECLINE", "NO PLAN"), str(r)[:120])
        _, r = tick(4.0, True, 101.9, types.SimpleNamespace(puts=[_C(100, 0.9, 0.94)], calls=[]))
        check("T4 a chain that prices no wing -> still a named row", r[0] in ("HOLD", "DECLINE"), str(r)[:120])
        check("T5 none of the five rows is NOT ASKED",
              st.conn.execute("SELECT COUNT(*) FROM plan_tick WHERE strategy='TrendCreditSpread' "
                              "AND verdict='NOT ASKED'").fetchone()[0] == 0)
    finally:
        tp.TCS_ENTRY_END_ET = _end
    print()
    if FAILED:
        print(f"FAIL — {len(FAILED)} check(s): {FAILED}"); return 1
    print("PASS — check_tcs_narrates"); return 0


if __name__ == "__main__":
    sys.exit(main())
