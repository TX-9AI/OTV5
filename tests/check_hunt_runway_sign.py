#!/usr/bin/env python3
"""
tests/check_hunt_runway_sign.py  v5.0
v5.0  2026-10-26  OTV5 r33 (HUNT.14) — A HUNT WHOSE PRICE IS AT OR THROUGH ITS TARGET IS REFUSED, ON BOTH SIDES.
      GOOGL 2026-10-26 (33dc832f) entered short 0.20 through its target because the runway was abs(target - price).
      Real plan, real LiquidityHunt, a DerivedStore fixture for the levels (as check_liquidity_hunt).

  R1  _runway: long = target - price, short = price - target (signed; negative past the target)
  R2  LONG A1 with price short of the target fires (unchanged)
  R3  LONG A1 with price THROUGH the target does not fire; the plan names "already at/through the target"
  R4  SHORT A1 with price short of the target fires (unchanged)
  R5  SHORT A1 with price THROUGH the target does not fire (the GOOGL case); named the same
  R6  price exactly AT the target does not fire

Born red on df95c04: R1 (no _runway), R3 and R5 (abs() gave a positive runway, so each fired). R6 was already
refused at zero and pins that edge.
Run:  python3 tests/check_hunt_runway_sign.py
"""
import os
import sqlite3
import sys
import tempfile
_DIR = tempfile.mkdtemp(prefix="chk_hunt_runway_")
os.environ.setdefault("OT_COUNTERFACTUAL_DIR", os.path.join(_DIR, "cf"))
os.environ.setdefault("OT_TRADES_DB", os.path.join(_DIR, "trades.db"))
import time
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


def _frame(rows, start="09:40"):
    import pandas as pd
    return pd.DataFrame([{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in rows],
                        index=pd.date_range(f"2026-09-10 {start}", periods=len(rows), freq="1min"))


class _G:
    def __init__(s, k, prem, delta, gamma):
        s.strike, s.mark, s.ask, s.bid = float(k), prem, prem + 0.02, prem - 0.02
        s.delta, s.gamma, s.theta, s.expiry, s.open_interest, s.symbol = delta, gamma, -0.04, "x", 100, f"O{k}"


def main():
    import shutil
    from strategy import plan as P
    class St:
        def __init__(s): s.conn = sqlite3.connect(":memory:"); s.conn.row_factory = sqlite3.Row
        def commit(s): s.conn.commit()
    st = St(); P.ensure_tables(st); P.bind_store(st)
    from data.derived_store import DerivedStore
    import strategy.liquidity_hunt as LH
    from execution import handoff as H
    LH._symbol_of = lambda: "TST"

    rw = getattr(LH, "_runway", None)
    check("R1 _runway is signed: long 102.5-101.3=1.2, long past -0.2, short 100-99.2=0.8, short past -0.2",
          rw is not None and abs(rw("long", 102.5, 101.3) - 1.2) < 1e-9 and abs(rw("long", 102.5, 102.7) + 0.2) < 1e-9
          and abs(rw("short", 99.2, 100.0) - 0.8) < 1e-9 and abs(rw("short", 318.27, 318.07) + 0.2) < 1e-9,
          "missing" if rw is None else "")

    orb = types.SimpleNamespace(orb_high=101.0, orb_low=100.0)
    calls = [_G(101, 0.95, 0.46, 0.05), _G(102, 0.48, 0.30, 0.058), _G(103, 0.20, 0.17, 0.04), _G(104, 0.10, 0.08, 0.02)]
    puts = [_G(100, 0.95, -0.46, 0.05), _G(99, 0.48, -0.30, 0.058), _G(98, 0.20, -0.17, 0.04), _G(97, 0.10, -0.08, 0.02)]
    chain = types.SimpleNamespace(calls=calls, puts=puts)

    def run(levels, px, bar, hhmm="09:42"):
        """A fresh hunt over its own store; one tick on a closed bar `bar` with price_now `px`."""
        ds = DerivedStore(path=os.path.join(tempfile.mkdtemp(dir=_DIR), "derived.db"))
        ds.mark_level_sync("TST", time.time())
        now = time.time()
        for lv in levels:
            ds.upsert_level(lv + (now - 3600, 0, None, 0, None, None, 1))
        hunt = LH.LiquidityHunt(); hunt._store = ds; hunt.planner.symbol = "TST"
        LH.FINISHED.clear(); H.reset()
        P.begin_tick(time.time())
        sig = hunt.generate_signal(orb=orb, price_now=px, now_et=hhmm, atr_pct=0.14, chain=chain,
                                   df_1m=_frame([bar, bar], hhmm), atm_iv=0.25)
        P.close_tick(st, "TST")
        r = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='LiquidityHunt' "
                            "ORDER BY rowid DESC LIMIT 1").fetchone()
        return sig, ((r["verdict"], r["reason"] or "") if r else ("", ""))

    # LONG: PDH 102.50 is 1.50 above the edge, the london low 97.00 3.00 below -> bias LONG, target 102.50
    LONG = [("TST:prev_day:102.50", "TST", 102.5, "resistance", "prev_day", "day"),
            ("TST:london:97.00", "TST", 97.0, "support", "london", "session")]
    up = (100.9, 101.4, 100.8, 101.3)
    sig, r = run(LONG, 101.3, up)
    check("R2 LONG A1, price 101.30 short of the 102.50 target -> fires", sig is not None and sig.direction == "long",
          f"{r[0]} {r[1][-90:]}")
    sig, r = run(LONG, 102.7, up)
    check("R3 LONG A1, price 102.70 THROUGH the 102.50 target -> no signal, named",
          sig is None and "already at/through the target" in r[1], f"sig={sig is not None} {r[0]} {r[1][-90:]}")

    # SHORT: london low 99.20 is 0.80 below the edge, PDH 104.00 3.00 above -> bias SHORT, target 99.20
    SHORT = [("TST:prev_day:104.00", "TST", 104.0, "resistance", "prev_day", "day"),
             ("TST:london:99.20", "TST", 99.2, "support", "london", "session")]
    dn = (100.1, 100.2, 99.6, 99.7)
    sig, r = run(SHORT, 99.7, dn)
    check("R4 SHORT A1, price 99.70 short of the 99.20 target -> fires", sig is not None and sig.direction == "short",
          f"{r[0]} {r[1][-90:]}")
    sig, r = run(SHORT, 99.0, dn)
    check("R5 SHORT A1, price 99.00 THROUGH the 99.20 target (GOOGL 10-26) -> no signal, named",
          sig is None and "already at/through the target" in r[1], f"sig={sig is not None} {r[0]} {r[1][-90:]}")
    sig, r = run(SHORT, 99.2, dn)
    check("R6 SHORT A1, price exactly AT the target -> no signal", sig is None, f"{r[0]} {r[1][-90:]}")

    shutil.rmtree(_DIR, ignore_errors=True)
    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
