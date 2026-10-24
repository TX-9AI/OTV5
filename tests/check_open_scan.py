#!/usr/bin/env python3
"""
tests/check_open_scan.py  v1.1

v1.1  2026-10-05  OTV4TEST r252 (BOX.18) - level_ledger in the fixture carries `symbol` as the real schema does
      (data/derived_store.py: symbol TEXT NOT NULL), and the box is pinned to the fixture's QQQ: open_scan v1.1
      counts only this box's levels. No assertion changed.

The daily open scan raises the reds it exists to raise, diffs NEW against the
previous run, ignores checker fixtures, skips non-trading days, never writes a
store, always exits 0 — and the installer schedules it at 09:35 and 09:45 ET.

v1.0  2026-09-24  OTV4TEST r130. BORN RED on the r129 build: tools/open_scan.py,
      its installer and its entry point do not exist.

O1  a stale CRITICAL stream is RED; a non-critical one is WATCH
O2  a derived engine with failures is RED
O3  zero live levels is RED; a 1h fork never built today is RED; the 1d fork is
    WATCH and labelled with its BACKLOG row
O4  a level-reading plan that sees 0 levels is RED ("blind")
O5  an empty fire-snapshot field NOT in the known list is RED; a known one is WATCH
O6  NEW: a warning absent from yesterday's run and present today is NEW; a known
    one is never NEW; one that went away is CLEARED; a same-day re-run diffs
    against the SAME baseline, not against itself
O7  checker fixture lines ([rehearsal], price 100.0000) never reach the report
O8  a non-trading day writes no report and exits 0
O9  READ-ONLY: every store is byte-identical after both phases
O10 a crash inside the scan is a RED finding, still exit 0
O11 the installer: 09:35 ready + 09:45 live, America/New_York, Mon..Fri,
    Persistent=false, ExecStart runs tools/open_scan.py; open_scan is a declared
    ENTRY_POINT (check_map_accuracy E1 reads the installer's ExecStart)

Run:  python3 tests/check_open_scan.py
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sqlite3
import sys
import tempfile
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import glob as _glob                                             # r106 venv bootstrap
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

PROBLEMS: list = []
NOW = "2026-09-24T09:52:00-04:00"        # a Thursday
YDAY = "2026-09-23T09:52:00-04:00"
T930 = 1790256600.0                       # 2026-09-24 09:30 ET


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def _derived(path, live_levels=3, fork1h_built=1, level_zero=False, empty_field=None):
    c = sqlite3.connect(path)
    c.executescript("""
      CREATE TABLE level_ledger (level_id TEXT, symbol TEXT NOT NULL, price REAL, retired_ts REAL);
      CREATE TABLE fork_series (interval TEXT, ts_epoch REAL, built INTEGER);
      CREATE TABLE plan_tick (ts_epoch REAL, strategy TEXT, verdict TEXT, reason TEXT);
      CREATE TABLE plan_check (ts_epoch REAL, strategy TEXT, check_name TEXT, value REAL, verdict TEXT);
      CREATE TABLE fire_snapshot (trade_id TEXT, symbol TEXT, fired_ts REAL, payload TEXT);
      CREATE TABLE derived_engine_status (name TEXT, runs INTEGER, failures INTEGER, last_rows INTEGER, last_error TEXT);
    """)
    for i in range(live_levels):
        c.execute("INSERT INTO level_ledger VALUES (?,'QQQ',?,NULL)", (f"L{i}", 700 + i))
    t = T930 + 600
    c.execute("INSERT INTO fork_series VALUES ('1h',?,?)", (t, fork1h_built))
    c.execute("INSERT INTO fork_series VALUES ('1d',?,0)", (t,))
    c.execute("INSERT INTO plan_tick VALUES (?,?,?,?)", (t, "SweepCreditSpread", "HOLD", "in play"))
    for k, v in (("levels_above", 0 if level_zero else 5), ("levels_below", 3), ("nearest_above", 741.0)):
        c.execute("INSERT INTO plan_check VALUES (?,?,?,?,?)", (t, "SweepCreditSpread", k, v, "n/a"))
    p = {"gex": 1.0, "vwap": 735.0, "levels": {"above": [1], "below": [1]}, "iv_slope": None}
    if empty_field:
        p[empty_field] = None
    c.execute("INSERT INTO fire_snapshot VALUES ('t1','QQQ',?,?)", (t, json.dumps(p)))
    c.commit(); c.close()


def _log(path, lines):
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def _run(argv):
    import open_scan as OS
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rc = OS.main(argv)
    except Exception as exc:                                    # noqa: BLE001
        return 99, f"UNCAUGHT {type(exc).__name__}: {exc}"     # a named failure, not a traceback
    return rc, buf.getvalue()


def main() -> int:
    os.environ["OT_INSTRUMENT"] = "QQQ"           # v1.1: the fixture is a QQQ box
    print("=" * 68)
    print("OPEN SCAN: the reds it exists for, NEW vs yesterday, read-only")
    print("=" * 68)
    if not os.path.exists(os.path.join(ROOT, "tools", "open_scan.py")):
        check("O0 tools/open_scan.py exists", False, "missing")
        print(f"  {len(PROBLEMS)} problem(s)"); return 1
    import open_scan as OS
    import manifold_health as MH

    with tempfile.TemporaryDirectory(dir="/var/tmp" if os.path.isdir("/var/tmp") else None) as td:
        # ── O1/O2 ready phase on a synthetic manifold report ─────────────
        rep = {"in_rth": True, "streams": [
            {"label": "quotes", "table": "quote_series", "rows": 5, "age_s": 999, "bulb": MH.RED, "critical": True, "after_hours": False},
            {"label": "prints", "table": "prints", "rows": 5, "age_s": 999, "bulb": MH.RED, "critical": False, "after_hours": False}],
            "candles": [{"label": "QQQ/1m", "rows": 9, "age_s": 5, "bulb": MH.GREEN, "after_hours": False}],
            "derived": [], "engines": [{"name": "levels", "runs": 9, "failures": 2, "last_rows": 0, "last_error": "boom"}]}
        real = MH.collect
        MH.collect = lambda *a, **k: rep
        d1 = os.path.join(td, "d1.db"); _derived(d1, live_levels=0, fork1h_built=0)
        s = OS.Scan()
        try:
            OS.scan_ready(s, "unused", d1, OS.dt.datetime.fromisoformat(NOW))
        finally:
            MH.collect = real
        lv = {f["sig"]: f["level"] for f in s.f}
        check("O1 a stale critical stream is RED, a non-critical one WATCH",
              lv.get("feed:quote_series:stale") == "RED" and lv.get("feed:prints:stale") == "WATCH", str(lv))
        check("O2 an engine with failures is RED", lv.get("engine:levels") == "RED", str(lv))
        known1d = [f for f in s.f if f["sig"].startswith("fork:1d")]
        check("O3 zero live levels RED; 1h fork never built RED; 1d WATCH and labelled",
              lv.get("levels:live") == "RED" and lv.get("fork:1h:never-built") == "RED"
              and known1d and known1d[0]["level"] == "WATCH" and known1d[0]["known"], str(lv))

        # ── live phase: yesterday baseline, then today ───────────────────
        out = os.path.join(td, "out")
        d_y = os.path.join(td, "dy.db"); _derived(d_y)
        log_y = os.path.join(td, "y.log")
        # the KNOWN warning is absent yesterday and present today, so only the
        # known-filter keeps it out of NEW (a first cut had it on both days and
        # the check passed with the filter deleted - mutation-caught)
        _log(log_y, ["2026-09-23 13:41:00 [WARNING] main: something that goes away 12.5"])
        rc_y, _ = _run(["--phase", "live", "--derived", d_y, "--log", log_y, "--out", out, "--now", YDAY])
        d2 = os.path.join(td, "d2.db"); _derived(d2, level_zero=True, empty_field="brand_new_input")
        log2 = os.path.join(td, "t.log")
        _log(log2, ["2026-09-24 13:40:00 [WARNING] execution.exit_engine: [exit] strategy 'Breakout' has no exit route — x",
                    "2026-09-24 13:45:00 [ERROR] strategy.plan: a brand new failure 3.14",
                    "2026-09-24 13:46:00 [WARNING] __main__: ENTRY REFUSED — ORB long price 100.0000 vs stop 101.0000",
                    "2026-09-24 13:47:00 [WARNING] __main__: [rehearsal] dispatch fixture line"])
        before = {p: _sha(p) for p in (d2, log2)}
        rc2, txt = _run(["--phase", "live", "--derived", d2, "--log", log2, "--out", out, "--now", NOW])
        check("O4 a level-reading plan that sees 0 levels is RED (blind)",
              "sees NOTHING for levels_above" in txt and "🔴 SweepCreditSpread" in txt, txt[:600])
        check("O5 an unknown empty snapshot field is RED; a known one is WATCH",
              "🔴 snapshot field 'brand_new_input'" in txt and "🟡 snapshot field 'iv_slope'" in txt, txt[:900])
        new_blk = txt.split("NEW since the last run:", 1)[1].split("\n  🟢", 1)[0].split("\n  🔴 ", 1)[0] if "NEW since" in txt else ""
        check("O6 a warning absent yesterday is NEW; a known one is never NEW",
              "a brand new failure" in new_blk and "no exit route" not in new_blk, new_blk[:400])
        check("O6 one that went away is CLEARED",
              "CLEARED" in txt and "something that goes away" in txt.split("CLEARED", 1)[1][:400], txt[:700])
        rc3, txt3 = _run(["--phase", "live", "--derived", d2, "--log", log2, "--out", out, "--now", NOW])
        blk3 = txt3.split("NEW since the last run:", 1)[1].split("\n  🟢", 1)[0].split("\n  🔴 ", 1)[0] if "NEW since the last run:" in txt3 else ""
        check("O6 a same-day re-run diffs against the SAME baseline, not itself",
              "a brand new failure" in blk3, txt3[:500])
        check("O7 fixture lines never reach the report",
              "100.0000" not in txt and "rehearsal" not in txt, txt[:800])
        check("O9 READ-ONLY: the derived store and the log are byte-identical after the scan",
              all(_sha(p) == h for p, h in before.items()))
        check("O9b both phases exit 0 even with reds", rc_y == 0 and rc2 == 0 and rc3 == 0, f"{rc_y},{rc2},{rc3}")

        # ── O8 not a trading day ──────────────────────────────────────────
        out8 = os.path.join(td, "o8")
        rc8, t8 = _run(["--phase", "live", "--derived", d2, "--log", log2, "--out", out8,
                        "--now", "2026-09-26T09:45:00-04:00"])      # a Saturday
        check("O8 a non-trading day writes no report and exits 0",
              rc8 == 0 and "not a trading day" in t8 and not os.path.exists(out8), t8[:200])

        # ── O10 a crash inside the scan ───────────────────────────────────
        bad = os.path.join(td, "bad.db")
        open(bad, "w").write("not a database")
        rc10, t10 = _run(["--phase", "live", "--derived", bad, "--log", log2, "--out", os.path.join(td, "o10"), "--now", NOW])
        check("O10 a crash inside the scan is a RED finding and still exit 0",
              rc10 == 0 and "the scan itself raised" in t10, t10[:300])

    # ── O11 the installer and the entry point ────────────────────────────
    inst = os.path.join(ROOT, "deploy", "install_open_scan_timer.sh")
    src = open(inst).read() if os.path.exists(inst) else ""
    check("O11 installer schedules ready 09:35 and live 09:45, America/New_York, Mon..Fri",
          'AT="09:35:00"' in src and 'AT="09:45:00"' in src
          and "OnCalendar=Mon..Fri *-*-* $AT America/New_York" in src, "installer missing or schedule wrong")
    check("O11 Persistent=false and ExecStart runs tools/open_scan.py --phase",
          "Persistent=false" in src and "tools/open_scan.py --phase $p" in src)
    gm = open(os.path.join(ROOT, "tests", "gen_file_map.py")).read()
    check("O11 tools/open_scan.py is a declared ENTRY_POINT", '"tools/open_scan.py"' in gm)

    print("=" * 68)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        return 1
    print("  ALL GREEN - the scan raises what it must, diffs, and writes no store")
    return 0


if __name__ == "__main__":
    sys.exit(main())
