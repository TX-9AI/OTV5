#!/usr/bin/env python3
"""
tests/check_tcs_plan.py  v1.4
v1.4  CD.2 (2026-10-24) - seeded ACCEPTED rows carry their market time; the session open is pinned (no pre-open
      fallback remains in tcs_plan); the fixture marks the level book SYNCED (store.mark_level_sync) after seeding the ledger:
      LevelEngine.board() now fails closed as not_synced until a book sync against a recent closed 1m bar has been
      recorded (derived/levels v6.10). Every expectation is unchanged.
v1.3  2026-10-19  OTV4TEST r303 (PSTATE.1) — its subject TrendCreditSpread is DORMANT by default and a dormant plan now writes
      nothing by ruling, so this run switches it ACTIVE (OT_TCS_ACTIVE=1); what it pins is unchanged.
v1.2  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.1  2026-09-23  OTV4TEST r112 — T9/T10/T11, each red at 0b2833b: the ACCEPTED
      level comes from the EVENT when the board no longer holds it (the engine
      retires it in the same step), a breach before the window never fires
      when the plan wakes, and an event that existed at the first look is
      never fired after a restart (§37). The 3-bar freshness gate is gone.
v1.0  2026-09-09  OTV4TEST r9 — THE TREND CREDIT SPREAD ON HYPOTHETICALS
      (PLAN_SPEC §34). Real plan, real strategy, real exit engine, a
      DerivedStore fixture for the session extremes and their ACCEPTED events.

  T1  in window, no acceptance -> HOLD naming the EM band and both sides prepared
  T2  a session HIGH accepted, price OUTSIDE the frozen reference band
      -> fires a PUT spread with the short at the first strike at/below THE LEVEL
  T2b the wing is the WIDEST clearing 1R (the most credit the floor allows)
  T3  accepted but price INSIDE the frozen band -> REJECTED outside_em
  T4  the frozen reference is the band that stood BEFORE the first close beyond
  T5  a low accepted -> the CALL spread above it
  T6  POP below the floor -> REJECTED pop
  T7  the same ACCEPTED event fires once
  T8  outside 11:31–14:00 -> DORMANT
  T9  r112: the accepted level is RETIRED (off the board) -> it still fires,
      built from the event (the r9..r111 trigger could never match this)
  T10 r112: a breach whose own bar is BEFORE the window never fires later
  T11 r112: §37 — an ACCEPTED that existed at a fresh process's first look
      is never fired
  X1  15% of credit fires on a LONE TCS and is SUPPRESSED when hedged
  X2  the level lost (a close back through the accepted extreme) -> tcs_breach
  X3  NO nickel close on the TCS (the 2026-08-14 measured ruling stands)

Born red at r8: T2/T3/T4 (no plan module), X1 (the stop fired hedged).
Run:  python3 tests/check_tcs_plan.py
"""
import os
import sqlite3
import sys
import tempfile
import time
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ["OT_TCS_ACTIVE"] = "1"   # r303: the subject writes (check_plan_states pins dormant)
# r112 — the r106 venv bootstrap: the lander runs CHECKs under system python3,
# where pandas is absent and this checker died before printing a line.
import glob as _glob
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
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
    def __init__(s, k, b, a, delta=0.20):
        s.strike, s.bid, s.ask, s.mark = float(k), b, a, round((a + b) / 2, 4)
        s.delta, s.gamma, s.theta, s.expiry, s.open_interest = delta, 0.01, -0.03, "x", 100
        s.symbol = f"O{k}"


def _frame(closes, start="12:00"):
    import pandas as pd
    return pd.DataFrame([{"open": c, "high": c + 0.1, "low": c - 0.1, "close": c} for c in closes],
                        index=pd.date_range(f"2026-09-09 {start}", periods=len(closes), freq="1min"))


def main():
    from strategy import plan as P
    st = _St(); P.ensure_tables(st); P.bind_store(st)
    from data.derived_store import DerivedStore
    import strategy.tcs_plan as tp
    import strategy.trend_credit_spread as tcs
    ds = DerivedStore(path=os.path.join(tempfile.mkdtemp(), "derived.db"))
    ds.mark_level_sync("TST", time.time())        # CD.2: the book is synced "now"
    tp._symbol_of = lambda: "TST"
    now = time.time()
    hi_id, lo_id = "TST:ny:102.00", "TST:ny:98.00"
    ds.upsert_level((hi_id, "TST", 102.0, "resistance", "ny", "session", now - 3600, 0, None, 0, None, None, 1))
    ds.upsert_level((lo_id, "TST", 98.0, "support", "ny", "session", now - 3600, 0, None, 0, None, None, 1))
    # price has moved ~1 pt beyond the extreme, so the short AT the level is OTM (POP ~0.72)
    # and rich: 102/99 (3 wide) is the widest wing clearing 1R; 102/97 (5 wide) does not.
    puts = [_C(102, 2.60, 2.66, 0.28), _C(101, 1.10, 1.14, 0.22), _C(100, 0.70, 0.74, 0.16),
            _C(99, 0.42, 0.46, 0.12), _C(97, 0.16, 0.20, 0.06), _C(95, 0.05, 0.07, 0.03)]
    calls = [_C(98, 2.60, 2.66, -0.28), _C(99, 1.10, 1.14, -0.22), _C(100, 0.70, 0.74, -0.16),
             _C(101, 0.42, 0.46, -0.12), _C(103, 0.16, 0.20, -0.06), _C(105, 0.05, 0.07, -0.03)]
    chain = types.SimpleNamespace(puts=puts, calls=calls)
    from datetime import datetime
    ET = tcs.ET
    T = tcs.TrendCreditSpread(); T.planner.symbol = "TST"; T.plan._store = ds

    def row():
        r = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='TrendCreditSpread' "
                            "ORDER BY rowid DESC LIMIT 1").fetchone()
        return (r["verdict"], r["reason"] or "") if r else ("", "")

    def tick(n, px, iv=0.20, hhmm=(12, 30), frame=None):
        P.begin_tick(n)
        sig = T.generate_signal(ms=types.SimpleNamespace(adx=12.0), vol_state=None, chain=chain, macro=None,
                                current_price=px, now_et=datetime(2026, 9, 9, hhmm[0], hhmm[1], tzinfo=ET),
                                atm_iv=iv, df_1m=frame,
                                session_open_epoch=now - 7200.0)   # CD.2: pinned, no clock dependence
        P.close_tick(st, "TST")
        return sig, row()

    def accept(lid, price, kind, bar="12:31", age=20.0):
        ds.insert_level_event(("TST", lid, f"2026-09-09 {bar}:00", now - age, "ACCEPTED", price, kind, "ny",
                               0.0, "accepted", 0, price + (0.3 if kind == "resistance" else -0.3),
                               now - age))                      # CD.2: the bar's close (market time)

    # T1
    _, r = tick(1.0, 100.0)
    check("T1 in window, nothing accepted -> HOLD naming the EM band and both sides",
          r[0] == "HOLD" and "EM ±" in r[1] and "nearest above" in r[1] and "would sell" in r[1], r[1][:140])

    # T4/T2: build the frozen reference. Tick at 100.0 sets prev band; then bars close beyond 102.
    _, _ = tick(2.0, 100.0, frame=_frame([99.8, 100.0, 100.1], "12:10"))          # prev band from spot 100
    band_before = T.plan._prev_band
    _, _ = tick(2.5, 102.4, frame=_frame([100.1, 102.3, 102.4], "12:12"))         # first close beyond 102 -> freeze
    check("T4 the reference band is the one that stood BEFORE the first close beyond",
          T.plan._ref.get(hi_id) == band_before, f"ref={T.plan._ref.get(hi_id)} before={band_before}")
    accept(hi_id, 102.0, "resistance")
    em = tp.__dict__.get("expected_move") or __import__("strategy.gex_pin_butterfly", fromlist=["expected_move"]).expected_move
    sig, r = tick(3.0, 103.2, frame=_frame([102.3, 102.4, 103.2], "12:14"))
    check("T2 a HIGH accepted with price outside the frozen band -> fires a PUT spread, short at/below THE LEVEL (102)",
          sig is not None and sig.option_side == "put" and float(sig.short_put_contract.strike) == 102.0
          and r[0] == "TAKE", f"sig={sig is not None} {r[0]} {r[1][:100]}")
    check("T2b the wing is the WIDEST clearing 1R (long at 99: 3 wide clears, 5 wide does not)",
          sig is not None and float(sig.long_put_contract.strike) == 99.0
          and sig.richness_at_entry is not None and sig.em_ref_band == band_before,
          f"long={sig and sig.long_put_contract.strike} rich={sig and sig.richness_at_entry}")

    # T3: a fresh ACCEPTED but price INSIDE the reference band
    T.plan._fired.clear(); T.plan._ref[hi_id] = (95.0, 110.0)
    accept(hi_id, 102.0, "resistance", bar="12:40")
    sig, r = tick(4.0, 102.3, frame=_frame([102.2, 102.3, 102.3], "12:20"))
    check("T3 accepted but price INSIDE the reference band -> REJECTED outside_em",
          sig is None and r[0] == "DECLINE" and r[1].startswith("outside_em"), r[1][:120])

    # T5: a LOW accepted -> the call spread
    T.plan._fired.clear(); T.plan._ref[lo_id] = (99.0, 101.0)
    accept(lo_id, 98.0, "support", bar="12:45")
    sig, r = tick(5.0, 96.8, frame=_frame([97.8, 97.6, 96.8], "12:25"))
    check("T5 a LOW accepted outside the band -> the CALL spread above it, short at/above 98",
          sig is not None and sig.option_side == "call" and float(sig.short_call_contract.strike) == 98.0,
          f"sig={sig and (sig.option_side, sig.strike)} {r[1][:80]}")

    # T6: POP below the floor
    T.plan._fired.clear(); T.plan._ref[hi_id] = (95.0, 99.0)
    _p = tp.TCS_MIN_POP; tp.TCS_MIN_POP = 0.95
    accept(hi_id, 102.0, "resistance", bar="12:50")
    sig, r = tick(6.0, 103.2, frame=_frame([102.8, 102.9, 103.2], "12:30"))
    tp.TCS_MIN_POP = _p
    check("T6 POP below the floor -> REJECTED pop", sig is None and r[0] == "DECLINE" and r[1].startswith("pop"), r[1][:100])

    # T7: fires once per ACCEPTED
    T.plan._fired.clear(); T.plan._ref[hi_id] = (95.0, 99.0)
    accept(hi_id, 102.0, "resistance", bar="12:55")
    s1, _ = tick(7.0, 103.2, frame=_frame([102.8, 102.9, 103.2], "12:35"))
    s2, r2 = tick(7.5, 103.2, frame=_frame([102.9, 103.2, 103.2], "12:37"))
    check("T7 the same ACCEPTED event fires once", s1 is not None and s2 is None and r2[0] == "HOLD")

    # T9: the level is gone from the board (the engine retired it BREACHED) — it still fires
    T.plan._fired.clear(); T.plan._ref[hi_id] = (95.0, 99.0)
    ds.retire_level(hi_id, now, "BREACHED")
    accept(hi_id, 102.0, "resistance", bar="13:00")
    sig, r = tick(7.8, 103.2, frame=_frame([102.8, 102.9, 103.2], "12:40"))
    check("T9 accepted level RETIRED from the board -> still fires, built from the event (short at 102)",
          sig is not None and sig.option_side == "put" and float(sig.short_put_contract.strike) == 102.0,
          f"sig={sig is not None} {r[0]} {r[1][:100]}")

    # T10: a breach BEFORE the window never fires when the plan wakes
    T.plan._fired.clear(); T.plan._ref[lo_id] = (99.0, 101.0)
    accept(lo_id, 98.0, "support", bar="10:11")
    sig, r = tick(7.9, 96.8, frame=_frame([97.8, 97.6, 96.8], "12:45"))
    check("T10 a breach at 10:11 does not fire at 12:30 — not an afternoon move, a chase",
          sig is None and r[0] == "HOLD", f"sig={sig is not None} {r[0]} {r[1][:100]}")

    # T11: §37 — a fresh process never fires the ACCEPTED that already existed
    accept(lo_id, 98.0, "support", bar="13:05")
    T2 = tcs.TrendCreditSpread(); T2.planner.symbol = "TST"; T2.plan._store = ds; T2.plan._ref[lo_id] = (99.0, 101.0)
    P.begin_tick(7.95)
    sig2 = T2.generate_signal(ms=types.SimpleNamespace(adx=12.0), vol_state=None, chain=chain, macro=None,
                              current_price=96.8, now_et=datetime(2026, 9, 9, 13, 6, tzinfo=ET),
                              atm_iv=0.20, df_1m=_frame([97.8, 97.6, 96.8], "12:50"))
    P.close_tick(st, "TST")
    check("T11 §37: a restarted process does not fire the ACCEPTED that existed at its first look",
          sig2 is None, f"sig={sig2 is not None}")

    # T8: dormant outside the window
    n0 = st.conn.execute("SELECT COUNT(*) FROM plan_tick WHERE strategy='TrendCreditSpread' AND verdict='DORMANT'").fetchone()[0]
    tick(8.0, 100.0, hhmm=(14, 5)); tick(8.5, 100.0, hhmm=(10, 0))
    n1 = st.conn.execute("SELECT COUNT(*) FROM plan_tick WHERE strategy='TrendCreditSpread' AND verdict='DORMANT'").fetchone()[0]
    check("T8 outside 11:31-14:00 -> DORMANT", n1 >= n0 + 1)

    # ── exits ──
    import datetime as _dt
    from zoneinfo import ZoneInfo
    import execution.exit_engine as XE
    _real_dt, _real_hc = XE.datetime, XE.is_hard_close_time
    class _Frozen(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return _dt.datetime(2026, 9, 9, 13, 0, tzinfo=ZoneInfo("America/New_York"))
    XE.datetime = _Frozen; XE.is_hard_close_time = lambda: False
    try:
        xe = XE.ExitEngine(paper_trading=True)
        base = {"trade_id": "tc-1", "strategy": "TrendCreditSpread", "setup_type": "trend_credit_long",
                "direction": "neutral", "option_side": "put", "entry_premium": 1.00, "contracts": 1,
                "status": "open", "stop_premium": 1.15, "target_premium": 0.0, "trail_activation": 0.0,
                "underlying_entry": 102.5, "underlying_stop": 102.0, "spread_width": 5.0,
                "is_credit_vertical": 1, "is_trend_credit": 1, "entry_time": "2026-09-09T12:35:00"}
        xe._condor_sibling_open = lambda *a, **k: False
        d = xe._evaluate_condor_leg(dict(base), 1.20, df_1m=_frame([102.6, 102.7, 102.8]))
        check("X1 15% of credit fires on a LONE TCS", d.should_exit and "tcs_stop" in str(d.exit_reason), str(d.exit_reason))
        xe._condor_sibling_open = lambda *a, **k: True
        xe._sync_stop_suppression = lambda *a, **k: None
        d = xe._evaluate_condor_leg(dict(base), 1.20, df_1m=_frame([102.6, 102.7, 102.8]))
        check("X1b ...and is SUPPRESSED when hedged", not (d.should_exit and "tcs_stop" in str(d.exit_reason)), str(d.exit_reason))
        xe._condor_sibling_open = lambda *a, **k: False
        d = xe._evaluate_condor_leg(dict(base), 1.05, df_1m=_frame([102.6, 101.9, 101.8]))
        check("X2 a close back through the accepted extreme -> tcs_breach", d.should_exit and "tcs_breach" in str(d.exit_reason), str(d.exit_reason))
        d = xe._evaluate_condor_leg(dict(base), 0.05, df_1m=_frame([102.6, 102.7, 102.8]))
        check("X3 NO nickel close on the TCS (2026-08-14 ruling stands)", not d.should_exit, str(d.exit_reason))
    finally:
        XE.datetime, XE.is_hard_close_time = _real_dt, _real_hc

    print()
    if FAILED:
        print(f"FAIL — {len(FAILED)} check(s): {FAILED}"); return 1
    print("PASS — check_tcs_plan"); return 0


if __name__ == "__main__":
    sys.exit(main())
