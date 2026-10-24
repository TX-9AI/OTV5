#!/usr/bin/env python3
"""
tools/plan_board.py  v1.1 — WHAT EVERY PLAN IS DOING RIGHT NOW.
v1.1  2026-10-03  OTV4TEST r191 (AUD.2) — Eastern time from zoneinfo, not a fixed UTC-4 (wrong from 11-01).

v1.0  2026-09-18  OTV4TEST r42. Operator: *"can you just have each plan report
      its last known status & a time stamp? For example, Active plan in progress
      or Active plan selected or inactive outside of window."*

🔑 IT WRITES NOTHING AND IT ADDS NO ROWS. The status board IS the transition
stream, read backwards: the newest `plan_tick` row for a strategy is, by
definition, its last known status and the moment it changed. r41 made the board
edge-triggered — one row per state change — so "what is it doing now" and "since
when" are the same question answered by the same row.

⚠️ THAT IS WHY CONTINUOUS LOGGING WAS NOT RESTORED. Writing a row every tick
would cost ~12,000 rows a day (measured 2026-09-17: 11,931 of 17,585 were the
idle restatement) to report a status the newest row already carries. The
repetition adds no information; it only makes the change harder to find.

⚠️ AGE IS SHOWN AND IS NOT DECORATION. A plan whose last known status is two
days old has not been asked since — which is a real fact about the box, and one
a per-tick log buries under today's noise rather than surfacing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sqlite3
import sys

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")        # r191: was a fixed UTC-4, an hour wrong from 11-01
except Exception:                                               # noqa: BLE001
    ET = dt.timezone(dt.timedelta(hours=-4))
DB = os.environ.get("OT_DERIVED_DB",
                    os.path.expanduser("~/options-trader/data/derived_store.db"))

# the verdicts a WORKING plan writes for itself, in rough order of progress.
# anything not here is treated as not-working.
ACTIVE_VERDICTS = {
    "ARMED": "active — armed, waiting on the trigger",
    "PREPARED": "active — prepared, trigger priced",
    "FIRED": "active — FIRED this tick",
    "CONFIRMED": "active — confirmed",
    "SELECTED": "active — selected",
    "WORKING": "active — working",
}
NOT_WORKING = {
    "INACTIVE": "inactive",
    "NOT ASKED": "inactive (pre-r41 wording)",
    "NO PLAN": "⚠️ DEFECT — asked, returned, wrote no plan row",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB)
    ap.add_argument("--all", action="store_true",
                    help="include /manage plans and anything stale")
    ap.add_argument("--stale-mins", type=float, default=1440.0)
    a = ap.parse_args()

    if not os.path.exists(a.db):
        print(f"no derived store at {a.db}")
        return 1
    c = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    try:
        rows = c.execute("""
            SELECT strategy, verdict, reason, ts_epoch FROM plan_tick p
            WHERE ts_epoch = (SELECT MAX(ts_epoch) FROM plan_tick q
                              WHERE q.strategy = p.strategy)
            GROUP BY strategy ORDER BY strategy""").fetchall()
    except sqlite3.OperationalError as exc:
        print(f"plan_tick unreadable: {exc}")
        return 1
    if not rows:
        print("plan_tick is empty — the board has not written yet")
        return 0

    now = dt.datetime.now(dt.timezone.utc)
    print(f"PLAN BOARD — last known status per plan   ({dt.datetime.now(ET):%Y-%m-%d %H:%M:%S ET})")
    print(f"{'plan':24s} {'status':62s} {'since':10s} {'age':>8s}")
    print("-" * 106)
    shown = 0
    for name, verdict, reason, ts in rows:
        et = dt.datetime.fromtimestamp(ts, ET)
        age_m = (now - et.astimezone(dt.timezone.utc)).total_seconds() / 60.0
        if not a.all and (name.endswith("/manage") or age_m > a.stale_mins):
            continue
        shown += 1
        if verdict in ACTIVE_VERDICTS:
            label = ACTIVE_VERDICTS[verdict]
        elif verdict in NOT_WORKING:
            label = NOT_WORKING[verdict]
            # the gate is the part he reads — r41 writes "inactive — <gate>: …"
            r = (reason or "")
            tail = r.split("inactive — ", 1)[-1] if "inactive — " in r else r
            # "entry blocked: " restates the verdict; the GATE is the content.
            for noise in ("entry blocked: ", "Entry blocked: "):
                if tail.startswith(noise):
                    tail = tail[len(noise):]
            label = f"{label} — {tail}" if tail else label
        else:
            label = f"active — {verdict.lower()}"
        age = (f"{age_m:.0f}m" if age_m < 600 else f"{age_m/60:.1f}h")
        print(f"{name[:24]:24s} {label[:62]:62s} {et:%H:%M:%S}   {age:>8s}")
    if not a.all:
        print(f"\n({shown} entry plan(s); --all adds /manage plans and anything "
              f"older than {a.stale_mins:.0f}m)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
