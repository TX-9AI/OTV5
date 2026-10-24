#!/usr/bin/env python3
"""
tools/open_scan.py  v1.1 — THE DAILY OPEN SCAN: IS THE PIPELINE READY, AND ARE THE
PLANS SEEING WHAT THEY SHOULD?

v1.1  2026-10-05  OTV4TEST r252 (BOX.18) - the level book's live/retired counts are this box's instrument only
      (SPX-TEST's 09:35 scan read 68 live = 20 SPX + 48 AAL left from the box's AAL days); n/a streams are skipped.
v1.0  2026-09-24  OTV4TEST r130. Operator, after a by-hand scan of the live box
      found five things no gate had: *"the scan you just ran should be done every
      trading day ... What you found was insightful"*, then the timing: *"let's do
      the early ones at 9:35 and the ones that need a few minutes to warm up let's
      do 945. On Trading days, of course."*

TWO PHASES, BECAUSE THE PLANS ARE DORMANT UNTIL 09:35:
  --phase ready  (09:35 ET) — the feed and candles (manifold_health.collect, the
                  same judgement the health board uses), the derived engines'
                  own failure counts, the level book, the forks.
  --phase live   (09:45 ET) — what each level-reading plan sees on its latest
                  tick, the plan board, every fire's snapshot (empty inputs),
                  and every WARNING/ERROR/traceback since 09:30, grouped.

🔑 THE SIGNAL IS NEW, NOT THE COUNT — THE BOOT SWEEP'S RULE (r86). Every finding
carries a stable signature (numbers stripped). Each run is diffed against the
same phase's previous run: a signature that was not there before is NEW, one
that went away is CLEARED. A finding already in the BACKLOG is LABELLED with
its row id, never hidden — a known red is still red, it is just not news.

⚠️ READ-ONLY, EVERYWHERE. Every store is opened mode=ro; bot.log is read. The
only files written are the report and this phase's state, under data/open_scan/.
⚠️ ALWAYS EXITS 0 (the boot sweep's reason): a non-zero exit marks the systemd
unit failed, and a scan's red is a REPORT, not a service failure.
⚠️ FIXTURE LINES ARE NOT THE BOT. Checkers that drive the entry path write into
the live bot.log (BACKLOG HYG.15); lines tagged [rehearsal] or carrying the
fixture price 100.0000 are dropped before grouping.
⚠️ NOT A TRADING DAY -> one line, no report, exit 0 (utils.market_calendar, the
tree's single holiday list).

Run:  venv/bin/python tools/open_scan.py --phase ready|live [--show]
      overrides for tests: --feed --derived --log --out --now ISO8601
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from zoneinfo import ZoneInfo                                    # noqa: E402

ET = ZoneInfo("America/New_York")
RED, WATCH, OK = "RED", "WATCH", "ok"

# Findings the BACKLOG already records: labelled, still reported, never NEW-worthy
# on their own. Keyed by signature PREFIX.
KNOWN = {
    "feed:underlying_series": "FEED.3",
    "feed:theo_series": "FEED.3",
    "warn:execution.exit_engine: [exit] strategy 'Breakout' has no exit route": "EXIT.3",
    "warn:execution.tick_size: [tick] NO VENUE RULE": "HYG.15",
    "warn:__main__: [size] noise floor UNMEASURABLE": "HYG.15",
    "warn:analysis.trend_engine: trend vote STARVED 1d": "HYG.15",
    "warn:database.trade_logger: [schema] record key": "HYG.15",
    "fork:1d": "HYG.15",
    "snapshot-empty:iv_slope": "HYG.15", "snapshot-empty:expected_move_straddle": "HYG.15",
    "snapshot-empty:character": "HYG.15", "snapshot-empty:character_held_s": "HYG.15",
    "snapshot-empty:gap_class": "HYG.15", "snapshot-empty:fork": "HYG.15",
}
LEVEL_PLANS = ("SweepCreditSpread", "LiquidityHunt", "Breakout")
LEVEL_INPUTS = ("levels_above", "levels_below", "nearest_above", "nearest_below",
                "rails_in_play", "fork_built", "pool_price")
FIXTURE = re.compile(r"\[rehearsal\]|price 100\.0000")
LOGLINE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \[(WARNING|ERROR|CRITICAL)\s*\] (.*)$")


def _known(sig: str) -> str:
    return next((v for k, v in KNOWN.items() if sig.startswith(k)), "")


def _ro(path: str):
    if not path or not os.path.exists(path):
        return None
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def _day_bounds(now: dt.datetime):
    d0 = now.astimezone(ET).replace(hour=0, minute=0, second=0, microsecond=0)
    return d0.timestamp(), d0.replace(hour=9, minute=30).timestamp()


class Scan:
    def __init__(self):
        self.f: list = []

    def add(self, level: str, sig: str, text: str):
        self.f.append({"level": level, "sig": sig, "text": text, "known": _known(sig)})


# ── READY ────────────────────────────────────────────────────────────────
def scan_ready(s: Scan, feed: str, derived: str, now: dt.datetime):
    import manifold_health as MH
    rep = MH.collect(feed, derived, in_rth=True)
    if rep.get("fatal"):
        s.add(RED, "feed:fatal", rep["fatal"])
        return
    s.add(OK if MH.rollup(rep) == MH.GREEN else RED, "feed:rollup",
          f"manifold rollup {MH.rollup(rep)}")
    for st in rep["streams"]:
        if st.get("after_hours") or st["bulb"] == MH.NA:   # BOX.18: n/a (an index's tape) is no question
            continue
        if not st["rows"]:
            s.add(RED if st["critical"] else WATCH, f"feed:{st['table']}",
                  f"{st['label']}: NO ROWS — the series home is not filling")
        elif st["bulb"] == MH.RED:
            s.add(RED if st["critical"] else WATCH, f"feed:{st['table']}:stale",
                  f"{st['label']}: stale ({st['age_s']}s)")
    for cd in rep["candles"]:
        if not cd.get("after_hours") and cd["bulb"] == MH.RED:
            s.add(RED, f"candles:{cd['label']}:stale", f"{cd['label']}: stale ({cd['age_s']}s)")
    for e in rep.get("engines") or []:
        if (e["failures"] or 0) > 0 or e.get("last_error"):
            s.add(RED, f"engine:{e['name']}",
                  f"engine {e['name']}: {e['failures']} failure(s) in {e['runs']} runs; "
                  f"last error {str(e.get('last_error') or '')[:80]}")
    if rep.get("engines") is None:
        s.add(RED, "engine:status-unreadable", "derived_engine_status unreadable")
    dc = _ro(derived)
    if dc is None:
        s.add(RED, "derived:missing", f"no derived store at {derived}")
        return
    t0, _ = _day_bounds(now)
    try:
        # BOX.18 - this box's instrument only: SPX-TEST's book counted AAL's 48 old levels
        # as live (68 = 20 SPX + 48 AAL, 10-05). UNSET counts every row, as before.
        from utils.instrument import box_instrument, UNSET
        _sym = (box_instrument() or "").strip().upper()
        _w, _p = ("", ()) if (not _sym or _sym == UNSET) else (" AND symbol = ?", (_sym,))
        live = dc.execute("SELECT COUNT(*) FROM level_ledger WHERE (retired_ts IS NULL OR retired_ts = '')" + _w,
                          _p).fetchone()[0]
        ret = dc.execute("SELECT COUNT(*) FROM level_ledger WHERE retired_ts >= ?" + _w,
                         (t0,) + _p).fetchone()[0]
        s.add(OK if live else RED, "levels:live", f"level book: {live} live level(s), {ret} retired today")
    except sqlite3.Error as exc:
        s.add(RED, "levels:unreadable", f"level_ledger unreadable: {exc}")
    try:
        for iv, built, n in dc.execute(
                "SELECT interval, SUM(built), COUNT(*) FROM fork_series WHERE ts_epoch >= ? GROUP BY 1", (t0,)):
            lvl = OK if built else (RED if iv == "1h" else WATCH)
            s.add(lvl, f"fork:{iv}" + ("" if built else ":never-built"),
                  f"{iv} fork built {built or 0} of {n} run(s) today")
    except sqlite3.Error as exc:
        s.add(RED, "fork:unreadable", f"fork_series unreadable: {exc}")


# ── LIVE ─────────────────────────────────────────────────────────────────
def scan_live(s: Scan, derived: str, log: str, now: dt.datetime):
    dc = _ro(derived)
    t0, t930 = _day_bounds(now)
    if dc is None:
        s.add(RED, "derived:missing", f"no derived store at {derived}")
    else:
        rows = dc.execute(
            "SELECT strategy, verdict, reason, ts_epoch FROM plan_tick p WHERE ts_epoch = "
            "(SELECT MAX(ts_epoch) FROM plan_tick q WHERE q.strategy = p.strategy) "
            "AND strategy NOT LIKE '%/manage' GROUP BY strategy").fetchall()
        for name, verdict, reason, ts in rows:
            r = (reason or "")
            if verdict == "NO PLAN":
                s.add(RED, f"plan:{name}:no-plan", f"{name}: asked, returned, wrote no plan row")
            elif ts < t0:
                s.add(WATCH, f"plan:{name}:not-asked-today",
                      f"{name}: last status is from a previous day ({verdict})")
            elif "absent" in r or "starved" in r.lower() or "unreadable" in r:
                s.add(RED, f"plan:{name}:starved", f"{name}: {verdict} — {r[:110]}")
        for p in LEVEL_PLANS:
            t = dc.execute("SELECT MAX(ts_epoch) FROM plan_check WHERE strategy = ? AND ts_epoch >= ?",
                           (p, t930)).fetchone()[0]
            if not t:
                s.add(WATCH, f"inputs:{p}:no-tick", f"{p}: no plan checks since 09:30")
                continue
            vals = dict(dc.execute("SELECT check_name, value FROM plan_check WHERE strategy = ? AND ts_epoch = ?",
                                   (p, t)).fetchall())
            seen = {k: vals[k] for k in LEVEL_INPUTS if k in vals}
            blind = [k for k, v in seen.items() if v in (None, 0, 0.0)]
            hhmm = dt.datetime.fromtimestamp(t, ET).strftime("%H:%M")
            if not seen:
                s.add(WATCH, f"inputs:{p}:none-recorded", f"{p} @ {hhmm}: records none of the level inputs")
            elif blind:
                s.add(RED, f"inputs:{p}:blind:{','.join(sorted(blind))}",
                      f"{p} @ {hhmm}: sees NOTHING for {', '.join(sorted(blind))}")
            else:
                s.add(OK, f"inputs:{p}", f"{p} @ {hhmm}: " + ", ".join(f"{k}={v:g}" for k, v in seen.items()))
        empties = collections.Counter()
        fires = dc.execute("SELECT payload FROM fire_snapshot WHERE fired_ts >= ?", (t0,)).fetchall()
        for (pl,) in fires:
            try:
                p = json.loads(pl)
            except ValueError:
                s.add(RED, "snapshot:unparseable", "a fire snapshot is not valid JSON")
                continue
            for k, v in p.items():
                if v in (None, "", {}, []):
                    empties[k] += 1
            lv = p.get("levels") or {}
            if not (lv.get("above") or lv.get("below")):
                empties["levels(both sides)"] += 1
        s.add(OK, "fires:count", f"{len(fires)} fire snapshot(s) today")
        for k, n in sorted(empties.items()):
            sig = f"snapshot-empty:{k}"
            s.add(WATCH if _known(sig) else RED, sig, f"snapshot field '{k}' empty on {n} of {len(fires)} fire(s)")
    groups, examples, tb = collections.Counter(), {}, 0
    if log and os.path.exists(log):
        day = now.astimezone(ET).strftime("%Y-%m-%d")
        t930_utc = dt.datetime.fromtimestamp(t930, dt.timezone.utc)
        with open(log, errors="replace") as fh:
            for line in fh:
                if not line.startswith(t930_utc.strftime("%Y-%m-%d")) and not line.startswith(day):
                    continue
                if "Traceback" in line:
                    tb += 1
                m = LOGLINE.match(line)
                if not m or FIXTURE.search(line):
                    continue
                ts = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)
                if ts < t930_utc or ts > now:
                    continue
                body = re.sub(r"\d+(\.\d+)?", "N", m.group(3))[:90]
                groups[(m.group(2), body)] += 1
                examples.setdefault((m.group(2), body), m.group(3)[:140])
    else:
        s.add(RED, "log:missing", f"no bot log at {log}")
    if tb:
        s.add(RED, "log:traceback", f"{tb} traceback line(s) in today's bot.log")
    for (lvl, body), n in groups.most_common():
        sig = f"warn:{body}"
        level = RED if lvl in ("ERROR", "CRITICAL") else WATCH
        s.add(level, sig, f"{lvl} x{n}: {examples[(lvl, body)]}")


# ── report + diff ────────────────────────────────────────────────────────
def render(s: Scan, phase: str, now: dt.datetime, prev: dict) -> tuple:
    sigs = {f["sig"] for f in s.f if f["level"] != OK}
    psigs = set(prev.get("sigs", []))
    new = sorted(x for x in sigs - psigs if not _known(x)) if prev else []
    cleared = sorted(psigs - sigs) if prev else []
    reds = [f for f in s.f if f["level"] == RED]
    lines = ["=" * 68,
             f" OPEN SCAN — {phase.upper()}   {now.astimezone(ET):%Y-%m-%d %H:%M} ET",
             "=" * 68,
             f"  {len(reds)} red · {sum(f['level'] == WATCH for f in s.f)} watch · "
             f"{sum(f['level'] == OK for f in s.f)} ok"
             + (f"   vs {prev.get('at_et', '?')}" if prev else "   (first run — this becomes the baseline)")]
    if new:
        lines.append("  🔴 NEW since the last run:")
        lines += [f"     + {x}" for x in new]
    if cleared:
        lines.append("  🟢 CLEARED since the last run:")
        lines += [f"     - {x}" for x in cleared]
    for lvl, mark in ((RED, "🔴"), (WATCH, "🟡"), (OK, "🟢")):
        for f in s.f:
            if f["level"] == lvl:
                tag = f"  [{f['known']}]" if f["known"] else ""
                lines.append(f"  {mark} {f['text']}{tag}")
    state = {"at_et": f"{now.astimezone(ET):%Y-%m-%d %H:%M}", "sigs": sorted(sigs),
             "red": len(reds), "new": new, "cleared": cleared}
    return "\n".join(lines) + "\n", state


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Daily open scan (read-only)")
    ap.add_argument("--phase", choices=("ready", "live"), required=True)
    ap.add_argument("--feed", default=os.path.join(ROOT, "data", "feed_store.db"))
    ap.add_argument("--derived", default=os.environ.get("OT_DERIVED_DB") or os.path.join(ROOT, "data", "derived_store.db"))
    ap.add_argument("--log", default=os.path.join(ROOT, "bot.log"))
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "open_scan"))
    ap.add_argument("--now", help="ISO8601 override (tests)")
    ap.add_argument("--show", action="store_true", help="print today's report for this phase and exit")
    a = ap.parse_args(argv)
    now = dt.datetime.fromisoformat(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=ET)
    day = now.astimezone(ET).strftime("%Y-%m-%d")
    path = os.path.join(a.out, f"{day}_{a.phase}.txt")
    if a.show:
        print(open(path).read() if os.path.exists(path) else f"no {a.phase} scan for {day} at {path}")
        return 0
    try:
        from utils.market_calendar import is_trading_day
        if not is_trading_day(now.astimezone(ET).date()):
            print(f"open_scan {a.phase}: {day} is not a trading day — nothing to scan")
            return 0
    except Exception as exc:                                    # noqa: BLE001
        print(f"open_scan: trading-day check failed ({exc}) — scanning anyway")
    s = Scan()
    try:
        (scan_ready(s, a.feed, a.derived, now) if a.phase == "ready"
         else scan_live(s, a.derived, a.log, now))
    except Exception as exc:                                    # noqa: BLE001
        s.add(RED, "scan:crashed", f"the scan itself raised {type(exc).__name__}: {exc}")
    os.makedirs(a.out, exist_ok=True)
    spath = os.path.join(a.out, f"{a.phase}_last.json")
    try:
        prev = json.load(open(spath))
    except (OSError, ValueError):
        prev = {}
    text, state = render(s, a.phase, now, prev if prev.get("at_et", "")[:10] != day else prev.get("prev", {}))
    if prev.get("at_et", "")[:10] == day:
        state["prev"] = prev.get("prev", {})          # a re-run today diffs against the SAME baseline
    else:
        state["prev"] = {k: prev[k] for k in ("at_et", "sigs") if k in prev}
    with open(path, "w") as fh:
        fh.write(text)
    with open(spath, "w") as fh:
        json.dump(state, fh)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
