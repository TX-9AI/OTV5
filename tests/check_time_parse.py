#!/usr/bin/env python3
"""
tests/check_time_parse.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.1  2026-10-19  OTV4TEST r303 (PSTATE.1) — its subject ORCS / SweepCreditSpread / TrendCreditSpread (T3) is DORMANT by default and a dormant plan now
      writes nothing by ruling, so this run switches it ACTIVE (OT_ORCS=1, OT_SWEEP_CS=1, OT_TCS_ACTIVE=1); what it pins is unchanged.
v1.0  2026-10-03  OTV4TEST r220 (TIME.1) — ONE HH:MM PARSER, AND AN UNREADABLE CLOCK IS NO TRADE.

  The 10-03 audit (C3): eight plans each carried a private copy of the same
  'HH:MM' parser, and seven of them skipped their window check when the clock
  could not be read (`if hm is not None and ...`). The operator, 2026-10-03:
  "yes I want the centralized modules"; an unreadable time meaning no trade for
  every plan was in the list he said yes to.

  T1  utils.time_utils.parse_hm: a datetime, 'HH:MM', 'HH:MM:SS' -> (h, m);
      garbage, None, '' and an out-of-range time -> None
  T2  every plan's parser IS that function (no private copy left)
  T3  the REAL Runaway, Hunt, ORCS, sweep and TCS plans go DORMANT on an
      unreadable clock and name it; a readable in-window clock is not stopped
      by this rule
  T4  Breakout: an unreadable window BOUND is None, and its window check
      closes on it (a source check, stated as one)

Run:  python3 tests/check_time_parse.py   (exit 0 green, 1 red)
"""
import datetime as _dt
import glob as _glob
import os
import sqlite3
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ["OT_ORCS"] = "1"   # r303: the subject writes (check_plan_states pins dormant)
os.environ["OT_SWEEP_CS"] = "1"   # r303: the subject writes (check_plan_states pins dormant)
os.environ["OT_TCS_ACTIVE"] = "1"   # r303: the subject writes (check_plan_states pins dormant)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_time_parse_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ.setdefault("OT_FEED_DB", os.path.join(_S, "empty_feed.db"))

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class _Store:
    def __init__(self):
        self.conn = sqlite3.connect(os.path.join(_S, "plan.db"))
        self.conn.row_factory = sqlite3.Row

    def commit(self):
        self.conn.commit()


def main():
    try:
        from utils import time_utils as TU
        p = TU.parse_hm
        got = (p(_dt.datetime(2026, 10, 5, 9, 45)), p("09:45"), p("10:30:15"), p("garbage"), p(None), p(""), p("25:00"), p("9:75"))
        check("T1 a datetime, 'HH:MM' and 'HH:MM:SS' parse; garbage, None, '' and out-of-range are None",
              got == ((9, 45), (9, 45), (10, 30), None, None, None, None, None), str(got))
    except Exception as exc:                                  # noqa: BLE001
        check("T1 (did not run)", False, f"{type(exc).__name__}: {exc}")
        TU = None

    try:
        import strategy.sweep_plan as SP, strategy.liquidity_hunt as LH, strategy.runaway_plan as RP
        import strategy.tcs_plan as TP, strategy.orcs_plan as OP, strategy.orb_plan as OB
        import strategy.volt_plan as VP, strategy.breakout_plan as BP
        mods = {"sweep_plan": SP._hm, "liquidity_hunt": LH._hm, "runaway_plan": RP._hm, "tcs_plan": TP._hm,
                "orcs_plan": OP._hm, "orb_plan": OB._hhmm, "volt_plan": VP._hhmm, "breakout_plan": BP._hm}
        own = sorted(k for k, f in mods.items() if TU is None or f is not TU.parse_hm)
        check("T2 all eight plans use utils.time_utils.parse_hm - no private copy left", not own, f"still private: {own}")
    except Exception as exc:                                  # noqa: BLE001
        check("T2 (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        from strategy import plan as P
        st = _Store(); P.bind_store(st)

        def last(name):
            r = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy=? ORDER BY ts_epoch DESC LIMIT 1",
                                (name,)).fetchone()
            return (r["verdict"], r["reason"]) if r else (None, None)
        res = {}
        try:
            P._DORMANT.clear()
            P.begin_tick(1000.0)
            RP.RunawayPlan().prepare(orb=None, atr_pct=0.1, price_now=750.0, now_et="garbage")
            res["Runaway"] = last("RunawayContinuation")
            LH.LiquidityHunt().prepare(orb=None, price_now=750.0, now_et="garbage")
            res["Hunt"] = last("LiquidityHunt")
            OP.ORCSPlan().prepare(price_now=750.0, now_et="garbage")
            res["ORCS"] = last("OpeningRangeCreditSpread")
            SP.SweepPlan().prepare(price_now=750.0, now_et="garbage")
            res["Sweep"] = last("SweepCreditSpread")
            TP.TCSPlan().prepare(price_now=750.0, now_et="garbage")
            res["TCS"] = last("TrendCreditSpread")
            bad = {k: v for k, v in res.items() if not (v[0] == "DORMANT" and "clock could not be read" in (v[1] or ""))}
            P._DORMANT.clear()
            P.begin_tick(2000.0)
            OP.ORCSPlan().prepare(price_now=750.0, now_et="09:50", chain=None)
            ok_clock = last("OpeningRangeCreditSpread")
        finally:
            P.bind_store(None)
        check("T3 Runaway, Hunt, ORCS, sweep and TCS are DORMANT on an unreadable clock; a readable one passes this rule",
              not bad and "clock could not be read" not in (ok_clock[1] or ""), f"not dormant: {bad}; readable -> {ok_clock}")
    except Exception as exc:                                  # noqa: BLE001
        check("T3 (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        src = open(os.path.join(_root, "strategy", "breakout_plan.py")).read()
        check("T4 Breakout: an unreadable bound is None and the window check closes on it",
              BP._et("garbage") is None and BP._et("09:35") == (9, 35)
              and "if hm is None or _lo is None or _hi is None or not (_lo <= hm < _hi):" in src,
              f"_et('garbage') = {BP._et('garbage')}")
    except Exception as exc:                                  # noqa: BLE001
        check("T4 (did not run)", False, f"{type(exc).__name__}: {exc}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — one parser; an unreadable clock is no trade")
    return 0


if __name__ == "__main__":
    sys.exit(main())
