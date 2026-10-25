#!/usr/bin/env python3
"""
tests/check_sweep_plan.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.4  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.3  2026-09-23  OTV4TEST r120 — E6-E8: THE EXIT'S BREACH IS THE OPERATOR'S BREACHED
      (a 1m close beyond, then the next 1m open beyond), through the same
      level_rules the book uses. E1/E2 hold under both rules and so could not
      tell them apart; E6 (the forming bar opens beyond after ONE close — exit),
      E7 (two closes beyond, each next bar opening back INSIDE — hold) and E8
      (a breach since entry is not forgotten when price comes back) are red
      on r119's two-close count for exactly that reason.
v1.2  2026-09-23  OTV4TEST r113 — the r106 venv bootstrap (refused under the lander's system python3 on pandas).
v1.1  2026-09-13  OTV4TEST r24 — X1 DRIVES THE RULE, NOT THE HOOK'S SOURCE. The spent lock is
      read from trades.db now; X1 writes a breach exit and a stop-out as REAL
      rows and asserts only the breach spends (the r5 rule this check was born
      to hold).
v1.0  2026-09-09  OTV4TEST r5 — THE SWEEP VERTICAL'S EXITS, ON HYPOTHETICALS
      (PLAN_SPEC §31.4), through the REAL `ExitEngine._evaluate_condor_leg`.
      The entry side (levels from the store, the REJECTED trigger, the anchor
      on the level, freshness, depth, spent) is pinned in check_plan_prepares
      S1–S9 and T4–T7.

  E1   two closed 1m bars beyond the pool -> sweep_breach_accepted (the level is spent)
  E2   one close beyond, then back -> HOLD (a wick is a test, one close is not acceptance)
  E3   the 15%-of-risk stop fires BEFORE the breach read when the premium says so first
       (operator: "2 minutes into a dead thesis could rack up some serious losses")
  E4   the nickel close at 0.05
  E5   a TCS vertical is untouched by the sweep's breach rule (setup_type routes it)
  E6   🔴 r120: one close beyond, the FORMING bar opens beyond -> BREACHED, exit now
  E7   🔴 r120: two closes beyond, each next bar opens back inside -> NOT breached, hold
  E8   🔴 r120: breached since entry, price back inside now -> still exits (a breach is final)
  X1   trade_logger marks the level SPENT only on the breach exit, not on a stop-out

Born red at r4: E1 (no breach exit), X1 (spent on any stop-out).
Run:  python3 tests/check_sweep_plan.py
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
# r113 — the r106 venv bootstrap: the lander runs CHECKs under system python3,
# where pandas is absent; declared as a CHECK for the first time here, it was
# refused on `No module named 'pandas'`.
import glob as _glob
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


def _frame(closes, start="10:40"):
    import pandas as pd
    return pd.DataFrame([{"open": c, "high": c + 0.1, "low": c - 0.1, "close": c} for c in closes],
                        index=pd.date_range(f"2026-09-09 {start}", periods=len(closes), freq="1min"))


def _ohlc(rows, start="10:40"):
    """(open, close) pairs -> a 1m frame; high/low bracket both. The LAST row is
    the forming bar, as in the live df_1m."""
    import pandas as pd
    return pd.DataFrame([{"open": o, "high": max(o, c) + 0.05, "low": min(o, c) - 0.05, "close": c}
                         for o, c in rows],
                        index=pd.date_range(f"2026-09-09 {start}", periods=len(rows), freq="1min"))


def main():
    import datetime as _dt
    from zoneinfo import ZoneInfo
    import execution.exit_engine as XE
    ET = ZoneInfo("America/New_York")
    _real_dt, _real_hc = XE.datetime, XE.is_hard_close_time

    class _Frozen(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return _dt.datetime(2026, 9, 9, 10, 45, tzinfo=ET)
    XE.datetime = _Frozen
    XE.is_hard_close_time = lambda: False
    try:
        xe = XE.ExitEngine(paper_trading=True)
        xe._condor_sibling_open = lambda *a, **k: False
        xe._sync_stop_suppression = lambda *a, **k: None
        # a put credit spread sold against a floor at 96.00: 95/92.5, credit 1.30, width 2.5
        base = {"trade_id": "sw-1", "strategy": "SweepCreditSpread", "setup_type": "sweep_credit_spread",
                "direction": "long", "option_side": "put", "entry_premium": 1.30, "contracts": 1,
                "status": "open", "stop_premium": 1.48, "target_premium": 0.0, "trail_activation": 0.0,
                "underlying_entry": 96.6, "underlying_stop": 0.0, "pool_price": 96.0, "spread_width": 2.5,
                "is_credit_vertical": 1, "entry_time": "2026-09-09T10:32:00"}
        # E1: two closes below 96 -> breach accepted (premium still under the stop)
        d = xe._evaluate_condor_leg(dict(base), 1.40, df_1m=_frame([96.4, 95.9, 95.8, 95.85]))
        check("E1 two closes beyond the pool -> sweep_breach_accepted",
              d.should_exit and "sweep_breach_accepted" in str(d.exit_reason), str(d.exit_reason))
        # E2: one close beyond, the next back inside -> hold
        d = xe._evaluate_condor_leg(dict(base), 1.40, df_1m=_frame([96.4, 95.9, 96.2, 96.3]))
        check("E2 one close beyond, then back -> HOLD (one close is not acceptance)",
              not d.should_exit, str(d.exit_reason))
        # E3: premium through the 15%-of-risk stop first — the floor answers before the breach read
        # risk = width - credit = 1.20; stop = 1.30 + 0.15*1.20 = 1.48
        d = xe._evaluate_condor_leg(dict(base), 1.50, df_1m=_frame([96.4, 95.9, 95.8, 95.85]))
        check("E3 the 15%-of-risk stop precedes the breach read (both true; the stop names it)",
              d.should_exit and "condor_stop" in str(d.exit_reason), str(d.exit_reason))
        # E4: the nickel close
        d = xe._evaluate_condor_leg(dict(base), 0.05, df_1m=_frame([96.4, 96.5, 96.6, 96.7]))
        check("E4 spread worth 0.05 -> nickel_close", d.should_exit and "nickel_close" in str(d.exit_reason),
              str(d.exit_reason))
        # E5: a TCS vertical does not read the sweep's breach rule
        tcs = dict(base, trade_id="tc-1", strategy="TrendCreditSpread", setup_type="trend_credit_spread",
                   underlying_stop=0.0)
        d = xe._evaluate_condor_leg(tcs, 1.40, df_1m=_frame([96.4, 95.9, 95.8, 95.85]))
        check("E5 a TCS vertical is not exited by the sweep's breach rule",
              not (d.should_exit and "sweep_breach" in str(d.exit_reason)), str(d.exit_reason))
        # E6-E8 (r120) — the operator's BREACHED: a close beyond, then the next OPEN beyond
        d = xe._evaluate_condor_leg(dict(base), 1.40, df_1m=_ohlc([(96.4, 96.4), (96.3, 95.9), (95.8, 95.8)]))
        check("E6 🔴 one close beyond + the FORMING bar opens beyond -> BREACHED, exit (no second close needed)",
              d.should_exit and "sweep_breach_accepted: BREACHED" in str(d.exit_reason), str(d.exit_reason))
        d = xe._evaluate_condor_leg(dict(base), 1.40,
                                    df_1m=_ohlc([(96.4, 96.4), (96.3, 95.9), (96.2, 95.8), (96.1, 96.1)]))
        check("E7 🔴 two closes beyond, each next bar OPENS back inside -> not breached, HOLD",
              not d.should_exit, str(d.exit_reason))
        d = xe._evaluate_condor_leg(dict(base), 1.40,
                                    df_1m=_ohlc([(96.4, 96.4), (96.3, 95.9), (95.8, 96.3), (96.4, 96.5), (96.5, 96.5)]))
        check("E8 🔴 breached since entry (close 95.9, open 95.8), back inside now -> still exits",
              d.should_exit and "sweep_breach_accepted" in str(d.exit_reason), str(d.exit_reason))
        # and a bar BEFORE the entry minute is not judged: the same breach at 10:20 on an 10:32 entry
        d = xe._evaluate_condor_leg(dict(base), 1.40,
                                    df_1m=_ohlc([(96.4, 96.4), (96.3, 95.9), (95.8, 96.3), (96.4, 96.5)], start="10:20"))
        check("E8b a breach BEFORE the entry minute is not the trade's -> HOLD",
              not d.should_exit, str(d.exit_reason))
    finally:
        XE.datetime, XE.is_hard_close_time = _real_dt, _real_hc

    # X1: spent only on the breach exit — driven on REAL rows (r24: read from trades.db)
    import tempfile as _tfx
    import database.trade_logger as _TLX
    import strategy.sweep_credit_spread as _scs
    from datetime import datetime, timedelta, timezone
    _TLX._trade_logger = _TLX.TradeLogger(os.path.join(_tfx.mkdtemp(), "x.db"))
    _c = _TLX.get_trade_logger()._connect()
    _t = lambda m: (datetime.now(timezone.utc) - timedelta(minutes=m)).isoformat()
    for tid, pool, why in (("x-stop", 96.0, "premium_stop_15% pnl=-16.0%"),
                           ("x-breach", 97.0, "sweep_breach_accepted: 2 closes beyond the pool 97.00")):
        _c.execute("INSERT INTO trades (trade_id, symbol, strategy, option_side, pool_price, status,"
                   " pnl_usd, entry_time, exit_time, exit_reason) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (tid, "TST", "SweepCreditSpread", "put", pool, "closed", -25.0, _t(30), _t(20), why))
    _c.commit(); _c.close()
    check("X1 the level is SPENT only on sweep_breach_accepted — a stop-out does not spend it",
          _scs.is_spent("TST", "put", 97.0)[0] and not _scs.is_spent("TST", "put", 96.0)[0],
          f"breach={_scs.is_spent('TST', 'put', 97.0)} stop={_scs.is_spent('TST', 'put', 96.0)}")

    print()
    if FAILED:
        print(f"FAIL — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("PASS — check_sweep_plan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
