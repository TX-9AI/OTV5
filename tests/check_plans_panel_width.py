#!/usr/bin/env python3
"""
tests/check_plans_panel_width.py  v5.1
v5.1  2026-10-25  OTV5 r19 (VIEW.2) — RE-POINTED (WA section 38.4) AND WIDENED: THE SAME SWITCHED-ON PLANS ON EVERY BOX, AT
      ANY HOUR, NOTHING SWITCHED OFF. The operator, 2026-10-25: "Why aren't they showing the same lines?"; "Can we suppress
      retired or paused plans from displaying here?"; "I want to see active plans that would trade during RTH that are
      switched on, even outside of RTH because we have rehearsal mode enabled". W3 pinned the dormant listing r19 removes;
      it now pins the opposite. W5-W7 new. BORN RED on r18 at W3, W5, W6.
v5.0  2026-10-25  OTV5 r18 (VIEW.1) — new: every panel line at most 62 characters (the operator: "Have it respect the
      character limit").
  W1  every line of the panel is at most query.PANEL_W (62) characters
  W2  every switched-on entry plan and its /manage appear by full name, each with its state on one line
  W3  no switched-off plan appears anywhere in the panel; one line says how many are hidden
  W4  the reasons survive shortened: "no opening range yet", "no open position"
  W5  SAME LINES: SOFI's heartbeat history (old /manage rows of 10-02..10-23, two for dormant entries, the condor rows)
      and NVDA's (the five entries only) render the SAME (plan, state) lines; CondorManagement / CreditRoll are not shown
      while every credit entry is switched off
  W6  outside RTH with the rehearsal ON (Sunday 17:04 ET, and 08:00 ET before the open) the roster is shown - not
      "nothing yet"
  W7  outside RTH with the rehearsal OFF, an old heartbeat or no heartbeat reads OFF HOURS - never STALE or NOT RUNNING
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
os.environ["OT_REHEARSAL_OFF_FILE"] = os.path.join(_TD, "REHEARSAL_OFF")
ET = ZoneInfo("America/New_York")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


ACTIVE = ["Breakout", "GEXPinButterfly", "LiquidityHunt", "PARK", "RunawayContinuation"]
DORMANT = ["ATPButterfly", "IronCondorStrategy", "ORBStrategy", "OpeningRangeCreditSpread", "SweepCreditSpread",
           "TrendCreditSpread", "VOLT"]
SOFI_OLD = ["Breakout/manage", "CondorManagement", "CreditRoll", "LiquidityHunt/manage", "ORBStrategy/manage",
            "RunawayContinuation/manage", "VOLT/manage"]
DOC = {"plans": dict({p: {"state": "active", "category": "hour"} for p in ACTIVE},
                     CondorManagement={"state": "active", "category": "condition"},
                     CreditRoll={"state": "active", "category": "condition"},
                     **{p: {"state": "dormant", "category": "hour"} for p in DORMANT})}


def render(Q, now, history, rehearsal=True):
    sym = Q.INSTRUMENT if Q.INSTRUMENT and Q.INSTRUMENT != "UNSET" else "QQQ"
    t = now.timestamp()
    path = os.path.join(_TD, "panel_%s.db" % history)
    if os.path.exists(path):
        os.remove(path)
    pc = sqlite3.connect(path)
    pc.execute("CREATE TABLE plan_heartbeat (symbol TEXT, plan TEXT, ts_epoch REAL, tick_id INTEGER, state TEXT,"
               " gate TEXT, verdict TEXT, watching TEXT, PRIMARY KEY (symbol, plan))")
    for p in ACTIVE:
        pc.execute("INSERT INTO plan_heartbeat VALUES (?,?,?,1,'HELD','','HOLD',?)",
                   (sym, p, t - 5, "%s: opening range not established yet" % p))
    if history == "sofi":
        for p in SOFI_OLD:
            pc.execute("INSERT INTO plan_heartbeat VALUES (?,?,?,1,'IDLE','','INACTIVE','old')", (sym, p, t - 3 * 86400))
    pc.commit()
    flag = os.environ["OT_REHEARSAL_OFF_FILE"]
    if rehearsal and os.path.exists(flag):
        os.remove(flag)
    if not rehearsal:
        open(flag, "w").close()
    Q.now_et = lambda: now
    buf = io.StringIO()
    with redirect_stdout(buf):
        Q.show_decisions(pc)
    pc.close()
    return buf.getvalue().splitlines()


def plan_lines(out):
    rows = []
    for ln in out:
        parts = ln.split()
        if len(parts) >= 2 and ln.startswith("    ") and not ln.startswith("     ") and parts[0] != "!!":
            rows.append((parts[0], parts[1]))
    return sorted(rows)


def main():
    import query as Q
    from strategy import plan_state as _ps
    doc = dict(DOC, written_epoch=datetime(2026, 10, 26, 7, 0, tzinfo=ET).timestamp())
    _ps.read_states_file = lambda *a, **k: doc
    tc = sqlite3.connect(Q.DB_PATH)
    tc.execute("CREATE TABLE IF NOT EXISTS trades (trade_id TEXT PRIMARY KEY, strategy TEXT, status TEXT, "
               "is_condor_leg INTEGER DEFAULT 0, credit_received REAL)")
    tc.commit()
    tc.close()
    W = getattr(Q, "PANEL_W", 62)
    mon = datetime(2026, 10, 26, 10, 49, 10, tzinfo=ET)
    out = render(Q, mon, "sofi")
    print("\n".join(out))
    wide = [ln for ln in out if len(ln) > W]
    check("W1 every line of the plans panel is at most %d characters" % W, not wide, str(wide[:2]))
    want = ACTIVE + ["%s/manage" % p for p in ACTIVE]
    got = dict(plan_lines(out))
    check("W2 every switched-on entry and its /manage, by full name, with its state on one line",
          all(got.get(p) in ("HELD", "IDLE") for p in want), str({p: got.get(p) for p in want}))
    leaked = [p for p in DORMANT + ["ORBStrategy/manage", "VOLT/manage"] if any((" %s " % p) in (ln + " ") for ln in out)]
    check("W3 no switched-off plan appears; the hidden count is said",
          not leaked and any("7 switched-off plan(s) hidden" in ln for ln in out), str(leaked))
    check("W4 the reasons survive shortened: 'no opening range yet', 'no open position'",
          any("no opening range yet" in ln for ln in out) and any("no open position" in ln for ln in out))
    nv = render(Q, mon, "nvda")
    check("W5 SOFI's history and NVDA's render the SAME plan lines; no condor management while credit is off",
          plan_lines(out) == plan_lines(nv) and "CondorManagement" not in "\n".join(out),
          "sofi=%s\nnvda=%s" % (plan_lines(out), plan_lines(nv)))
    sun = render(Q, datetime(2026, 10, 25, 17, 4, 0, tzinfo=ET), "sofi")
    pre = render(Q, datetime(2026, 10, 26, 8, 0, 0, tzinfo=ET), "nvda")
    check("W6 rehearsal ON outside RTH (Sunday 17:04, Monday 08:00): the roster is shown, not 'nothing yet'",
          all(dict(plan_lines(o)).get(p) for o in (sun, pre) for p in want)
          and not any("nothing yet" in ln for ln in sun + pre), "\n".join(pre[:12]))
    off = render(Q, datetime(2026, 10, 25, 17, 4, 0, tzinfo=ET), "nvda", rehearsal=False)
    off_s = "\n".join(off)
    check("W7 rehearsal OFF outside RTH: OFF HOURS or IDLE, never STALE or NOT RUNNING",
          "STALE" not in off_s and "NOT RUNNING" not in off_s, off_s[-600:])
    print()
    if FAILED:
        print(f"RED — {sorted(set(FAILED))}")
        return 1
    print("GREEN — W1-W7")
    return 0


if __name__ == "__main__":
    sys.exit(main())
