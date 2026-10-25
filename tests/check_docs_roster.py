#!/usr/bin/env python3
"""
tests/check_docs_roster.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.1  2026-10-19  OTV4TEST r303 (PSTATE.1) — R3 reads every switch's default from strategy/plan_state.py (the one
      place that decides active / log / dormant), not from two source literals that no longer exist.
v1.0  2026-10-03  OTV4TEST r226 (DOC.31) — docs/TRADES.md §0 IS PINNED TO config.py.

  The 10-03 audit (D4) found PLAN_SPEC and TRADES disagreeing with the code in ~25
  places - windows, the close, a butterfly stop quoted at 15% while the code ran 40%.
  TRADES §0 now states the roster as it runs, and this check fails when it drifts.
  Read in a FRESH interpreter with every OT_ switch unset, so it is the defaults.

  R1  every ENTRY_WINDOWS key has exactly one row, and no row names a key that is absent
  R2  each row's window equals config.ENTRY_WINDOWS
  R3  each row's ON/OFF equals the switch's default
  R4  the close: 15:40 / 15:45 / 15:50 / 15:55 equal config.EOD_SCHEDULE
  R5  the stops quoted: 20% runaway, 25% single legs, 40% butterflies

Run:  python3 tests/check_docs_roster.py   (exit 0 green, 1 red)
"""
import json
import os
import re
import subprocess
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED = []

_PROBE = r'''
import json, os, sys
sys.path.insert(0, sys.argv[1])
import config as c
src = lambda p: open(os.path.join(sys.argv[1], p)).read()
out = {
 "windows": {k: [list(v[0]), list(v[1])] for k, v in c.ENTRY_WINDOWS.items()},
 "eod": {k: list(v) for k, v in c.EOD_SCHEDULE.items()},
 "on": {
  "OT_ORCS": bool(c.ORCS_ENABLED), "OT_GEX_BUTTERFLY": bool(c.GEX_BUTTERFLY_ENABLED),
  "OT_ATP_BUTTERFLY": bool(c.ATP_BUTTERFLY_ENABLED), "OT_SWEEP_CS": bool(c.SWEEP_CS_ENABLED),
  "OT_TCS_ACTIVE": bool(c.TREND_CREDIT_ACTIVE),
 },
 "stops": [c.RUNAWAY_MAX_LOSS_PCT, c.MAX_LOSS_PCT, c.BUTTERFLY_STOP_LOSS_PCT],
}
# r303 (PSTATE.1): every plan's switch is ON when its default state is ACTIVE - plan_state decides
from strategy import plan_state as S
out["on"].update({S.switch(n): S.state(n) == "active" for n in S.TABLE if S.switch(n)})
print("@@" + json.dumps(out))
'''


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    try:
        env = {k: v for k, v in os.environ.items() if not k.startswith("OT_")}
        env["OT_INSTRUMENT"] = "QQQ"
        r = subprocess.run([sys.executable, "-c", _PROBE, _root], env=env, capture_output=True, text=True, timeout=120)
        line = [x for x in r.stdout.splitlines() if x.startswith("@@")]
        if not line:
            raise RuntimeError("config probe printed nothing: " + r.stderr[-300:])
        cfg = json.loads(line[0][2:])
        doc = open(os.path.join(_root, "docs", "TRADES.md")).read()
        sec = doc[doc.index("## 0. AS RUNNING"):doc.index("## How to read this")]
        rows = {}
        dup = []
        for m in re.finditer(r"^\| [^|]+ \| `(\w+)` \| (ON|OFF) \| ([^|]+) \| (\d\d):(\d\d)-(\d\d):(\d\d) \|", sec, re.M):
            if m.group(1) in rows:
                dup.append(m.group(1))
            rows[m.group(1)] = (m.group(2), m.group(3), [[int(m.group(4)), int(m.group(5))], [int(m.group(6)), int(m.group(7))]])
        check("R1 every ENTRY_WINDOWS key has exactly one row and no row names an absent key",
              set(rows) == set(cfg["windows"]) and not dup,
              f"doc only {sorted(set(rows) - set(cfg['windows']))}, config only {sorted(set(cfg['windows']) - set(rows))}, twice {dup}")
        bad = {k: (v[2], cfg["windows"].get(k)) for k, v in rows.items() if v[2] != cfg["windows"].get(k)}
        check("R2 each row's window equals config.ENTRY_WINDOWS", not bad, str(bad))
        bad = {}
        for k, (state, sw, _w) in rows.items():
            m = re.match(r"`(OT_\w+)`$", sw.strip())
            want = cfg["on"][m.group(1)] if m else True          # no switch: always asked
            if m and m.group(1) not in cfg["on"]:
                bad[k] = "unknown switch"
            elif (state == "ON") != want:
                bad[k] = (state, want)
        check("R3 each row's ON/OFF equals the switch's default (a row with no switch is ON)", not bad, str(bad))
        e = cfg["eod"]
        want = [e["entries_stop"], e["resting_at"], e["ladder_at"], e["cross_at"]]
        got = [[int(a), int(b)] for a, b in re.findall(r"\*\*(\d\d):(\d\d)\*\*", sec)]
        check("R4 the close's four bold times equal config.EOD_SCHEDULE, in order", got == want, f"doc {got} config {want}")
        got = [int(x) / 100.0 for x in re.findall(r"\*\*(\d+)%\*\*", sec)]
        check("R5 the three bold stops equal RUNAWAY_MAX_LOSS_PCT, MAX_LOSS_PCT, BUTTERFLY_STOP_LOSS_PCT",
              got == [float(x) for x in cfg["stops"]], f"doc {got} config {cfg['stops']}")
    except Exception as exc:                                  # noqa: BLE001
        for n in ("R1", "R2", "R3", "R4", "R5"):
            if n not in FAILED:
                check(f"{n} (did not run)", False, f"{type(exc).__name__}: {exc}")
    if FAILED:
        print(f"\nRED — {len(set(FAILED))} check(s): {sorted(set(FAILED))}")
        return 1
    print("\nGREEN — TRADES §0 says what config.py runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
