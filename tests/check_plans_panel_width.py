#!/usr/bin/env python3
"""
tests/check_plans_panel_width.py  v5.0
v5.0  2026-10-25  OTV5 r18 (VIEW.1) — new. THE PLANS PANEL FITS THE PAGE. The operator, 2026-10-25, from a phone
      screenshot of SOFI's query.py: "I don't like the plan rows spanning multiple lines. Have it respect the character
      limit." query.show_decisions is DRIVEN on a scratch store holding SOFI's 10-25 16:49 ET plan set (five HELD plans
      waiting on the opening range, six /manage and condor plans IDLE, one plan reading the feed with a long watching
      line, one STALE plan) and seven dormant plans, as that screenshot showed them. BORN RED on r17 at W1.
  W1  every line of the panel is at most query.PANEL_W (62) characters - the width of the page's own separators
  W2  every plan appears by its FULL name, and each NOT EVALUATING row carries its plan and its state on ONE line
  W3  each dormant plan's line says DORMANT (a grep for a plan finds its state)
  W4  the reasons survive shortened, not lost: "no opening range yet" and "no open position" are shown
"""
import io
import os
import sqlite3
import sys
import tempfile
from contextlib import redirect_stdout
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_panel_width_")
os.environ["OT_TRADES_DB"] = os.path.join(_TD, "trades.db")
os.environ.setdefault("OT_LOG_FILE", os.path.join(_TD, "bot.log"))
ET = ZoneInfo("America/New_York")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


HELD = ["Breakout", "GEXPinButterfly", "LiquidityHunt", "PARK", "RunawayContinuation"]
IDLE = ["Breakout/manage", "CondorManagement", "CreditRoll", "LiquidityHunt/manage", "ORBStrategy/manage",
        "RunawayContinuation/manage", "VOLT/manage"]
DORMANT = ["ATPButterfly", "IronCondorStrategy", "ORBStrategy", "OpeningRangeCreditSpread", "SweepCreditSpread",
           "TrendCreditSpread", "VOLT"]


def main():
    import query as Q
    from strategy import plan_state as _ps
    sym = Q.INSTRUMENT if Q.INSTRUMENT and Q.INSTRUMENT != "UNSET" else "QQQ"
    now = datetime(2026, 10, 26, 10, 49, 10, tzinfo=ET)
    t = now.timestamp()
    tc = sqlite3.connect(Q.DB_PATH)
    tc.execute("CREATE TABLE IF NOT EXISTS trades (trade_id TEXT PRIMARY KEY, strategy TEXT, status TEXT, "
               "is_condor_leg INTEGER DEFAULT 0, credit_received REAL)")
    tc.commit()
    tc.close()
    pc = sqlite3.connect(os.path.join(_TD, "panel.db"))
    pc.execute("CREATE TABLE plan_heartbeat (symbol TEXT, plan TEXT, ts_epoch REAL, tick_id INTEGER, state TEXT,"
               " gate TEXT, verdict TEXT, watching TEXT, PRIMARY KEY (symbol, plan))")
    for p in HELD:
        pc.execute("INSERT INTO plan_heartbeat VALUES (?,?,?,1,'HELD','','HOLD',?)",
                   (sym, p, t - 5, "%s: opening range not established yet" % p))
    for p in IDLE:
        pc.execute("INSERT INTO plan_heartbeat VALUES (?,?,?,1,'IDLE','','INACTIVE','old')", (sym, p, t - 4 * 3600))
    pc.execute("INSERT INTO plan_heartbeat VALUES (?,?,?,1,'EVALUATING','','DECLINE',?)",
               (sym, "ParkAlongsideEvaluatingPlan", t - 5, "watching the 1h tine at 14.62 for a rejection close "
                "with the 5m swing stop under the prior day low and the tape band confirming " * 2))
    pc.execute("INSERT INTO plan_heartbeat VALUES (?,?,?,7,'EVALUATING','','',?)",
               (sym, "SomeVeryLongStalePlanName", t - 3 * 3600, "it said something long " * 6))
    pc.commit()
    doc = {"written_epoch": t - 3 * 3600, "plans": {p: {"state": "dormant"} for p in DORMANT}}
    _ps.read_states_file = lambda *a, **k: doc
    Q.now_et = lambda: now
    buf = io.StringIO()
    with redirect_stdout(buf):
        Q.show_decisions(pc)
    out = buf.getvalue().splitlines()
    wide = [ln for ln in out if len(ln) > getattr(Q, "PANEL_W", 62)]
    check("W1 every line of the plans panel is at most %d characters" % getattr(Q, "PANEL_W", 62), not wide,
          "%d wide, e.g. %r" % (len(wide), wide[:2]))
    rows = {p: [ln for ln in out if (" %s " % p) in (ln + " ")] for p in HELD + IDLE}
    one_line = all(any(("HELD" if p in HELD else "IDLE") in ln for ln in rows[p]) for p in HELD + IDLE)
    check("W2 every plan by its full name, each NOT EVALUATING row with its state on one line",
          one_line and all(any(p in ln for ln in out) for p in HELD + IDLE + DORMANT),
          str({p: rows[p][:1] for p in HELD + IDLE if not rows[p]}))
    dorm = [p for p in DORMANT if not any(p in ln and "DORMANT" in ln for ln in out)]
    check("W3 each dormant plan's line says DORMANT", not dorm, str(dorm))
    check("W4 the reasons survive shortened: 'no opening range yet', 'no open position'",
          any("no opening range yet" in ln for ln in out) and any("no open position" in ln for ln in out),
          "\n".join(out[:30]))
    print("\n".join(out))
    print()
    if FAILED:
        print(f"RED — {sorted(set(FAILED))}")
        return 1
    print("GREEN — W1-W4")
    return 0


if __name__ == "__main__":
    sys.exit(main())
