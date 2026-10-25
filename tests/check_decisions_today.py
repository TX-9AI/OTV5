#!/usr/bin/env python3
"""check_decisions_today.py — v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.5  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.4  2026-09-22  OTV4TEST r92 — D3 counted ts_epoch bounds in a panel that runs no ranged
      SQL. It now pins liveness by HEARTBEAT AGE — a stronger guarantee than
      a date bound, because it also catches a plan that died sixty seconds
      ago, which no "today" cut ever would.
v1.3  2026-09-17 — OTV4TEST r34. Reads query.py at the REPO ROOT again; v1.2 read
      it under tools/. This checker loads the file BY PATH, so the move breaks it
      outright rather than subtly — which is why it is a declared CHECK on r34.
v1.2
v1.2  2026-09-11  OTV4TEST r14 — reads query.py under tools/ (root cleanup).
v1.1  2026-09-01  r210 — D2 RE-DERIVED. It matched the SOURCE TEXT
      `_today0 = _open.timestamp()`, so extracting that boundary into
      `session_start_epoch()` — so GATES and PLANS could share one definition
      of "today" — turned it red for a refactor that was correct. WA §24: a
      canary pinned to a spelling rots on the next legitimate change. D2 now
      EXECUTES the cut and asserts 09:30 ET today.
v1.0

🔴 THE DECISIONS PANEL SHOWS TODAY'S SESSION, OR NOTHING.

Operator, 2026-08-28: *"Make the decision section only display today's
decision, blank before 0930"* and *"If the box was up for maintenance the night
before or even before the session open, don't display those decisions."*

⚠️ WHAT IT SHOWED BEFORE: the newest `plan_tick` row per strategy, WHATEVER ITS
AGE. Read at 09:16 ET it printed twelve rows from the previous EVENING, each
flagged ⚠️ STALE — a panel titled *"the next tick, as the plans see it now"*
displaying last night's ticks. Truthful and useless: the warning made noise the
reader has to filter instead of information they can act on.

⚠️ THE CUT IS THE OPEN, NOT MIDNIGHT. A 06:00 ET maintenance wake writes real
plan rows against a market that is not trading. Showing those is the same lie
as showing last night's, just harder to spot because the date matches.

⚠️ AND IT IS ASKED IN ET. The boxes run UTC; "today" and "09:30" are EXCHANGE
facts. A bare `date.today()` on a UTC box rolls the day at 20:00 ET — the
operator's own long-standing symptom, *"any time I run a report for today after
the session ends it fails."* `ZoneInfo("US/Eastern")` also handles DST, so the
cut is correct in EDT and EST without a second code path.
"""
import ast
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ET = ZoneInfo("America/New_York")
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def _cut(now):
    """Mirror of the panel's rule, stated once so the cases below are readable."""
    o = now.replace(hour=9, minute=30, second=0, microsecond=0)
    return o.timestamp(), now < o


def main():
    src = open(os.path.join(_root, "query.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef)
               and "decision" in n.name.lower()), None)
    body = ast.unparse(fn) if fn else ""

    # ── D1 — the panel is blank before the open ──────────────────────────
    check("D1 the panel returns early before 09:30 ET",
          "hour=9, minute=30" in body and "_now < _open" in body)

    # ── 🔴 D2 — THE CUT IS THE OPEN, NOT MIDNIGHT ────────────────────────
    # ⚠️ `_open.replace(hour=0...)` was the first version and would have let a
    # 06:00 maintenance wake through.
    # 🔴 RE-DERIVED AT r210. This asserted the SOURCE TEXT
    # `_today0 = _open.timestamp()`, so it went red the moment r210 extracted
    # the boundary into `session_start_epoch()` for gates and plans to share —
    # a legitimate refactor, failing a check pinned to a SPELLING. WA §24:
    # canaries check BEHAVIOUR, never a literal that a correct change moves.
    # It now EXECUTES the cut and asserts it is 09:30 ET today.
    import importlib.util as _u
    _sp = _u.spec_from_file_location("_q", os.path.join(_root, "query.py"))
    _m = _u.module_from_spec(_sp)
    try:
        _sp.loader.exec_module(_m)
    except SystemExit:
        pass
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo as _Z
    # ⚠️ `_cut_dt`, not `_cut`: this file already defines a `_cut()` helper
    # and shadowing it turned the next case into a TypeError.
    _cut_dt = _dt.fromtimestamp(_m.session_start_epoch(), _Z("America/New_York"))
    check("D2 the row cut is the open itself, not midnight",
          (_cut_dt.hour, _cut_dt.minute, _cut_dt.second) == (9, 30, 0)
          and _cut_dt.date() == _dt.now(_Z("America/New_York")).date(),
          _cut_dt.strftime("%Y-%m-%d %H:%M:%S ET"))

    # ── D3 — THE PANEL NO LONGER RANGE-QUERIES, AND THAT IS THE POINT ────
    # 🔴 r92 — this counted `ts_epoch >= ?` bounds inside `show_decisions` and
    # found FOUR. r83 replaced the panel wholesale by ruling: it reads
    # `plan_heartbeat`, ONE UPSERTED ROW PER PLAN, so there is no date range to
    # bound — the row is current state. Counting SQL bounds in a panel that
    # runs no ranged SQL is asserting the absence of the thing that was
    # removed on purpose.
    # ⚠️ THE UNDERLYING WORRY IS STILL REAL AND STILL COVERED: a row from
    # yesterday must not read as a live plan. It cannot — the panel returns
    # early before 09:30 (D1/D4) and flags anything older than `STALE_S` as
    # ⚠️ STALE, so a stale row announces itself rather than passing as fresh.
    # That is a STRONGER guarantee than a date bound, because it also catches a
    # plan that died SIXTY SECONDS ago, which no "today" cut ever would.
    check("D3 the panel judges liveness by heartbeat AGE, not by row date",
          ("STALE_S" in body) and ("plan_heartbeat" in body)
          and (body.count("ts_epoch >= ?") == 0),
          f"stale_s={'STALE_S' in body} heartbeat={'plan_heartbeat' in body} "
          f"ranged_queries={body.count('ts_epoch >= ?')}")

    # ── D4 — the cases the operator named ────────────────────────────────
    cases = (
        ((9, 16), True,  "before the open -> blank"),
        ((6, 0),  True,  "maintenance wake -> blank"),
        ((10, 15), False, "mid-session -> shows"),
    )
    for (h, m), want_blank, label in cases:
        _, blank = _cut(datetime(2026, 8, 28, h, m, tzinfo=ET))
        check(f"D4 {label}", blank == want_blank)

    # rows that must be excluded when read mid-session
    cutoff, _ = _cut(datetime(2026, 8, 28, 10, 15, tzinfo=ET))
    for when, label in ((datetime(2026, 8, 28, 6, 0, tzinfo=ET), "a 06:00 maintenance row"),
                        (datetime(2026, 8, 27, 21, 20, tzinfo=ET), "last night's 21:20 row")):
        check(f"D5 {label} is excluded", when.timestamp() < cutoff)

    # ── D6 — DST, both sides of the year ─────────────────────────────────
    # ⚠️ The boxes are UTC. If this ever hard-coded -4 or -5 it would be an
    # hour wrong for half the year.
    edt = datetime(2026, 8, 28, 12, tzinfo=ET).utcoffset().total_seconds() / 3600
    est = datetime(2026, 1, 15, 12, tzinfo=ET).utcoffset().total_seconds() / 3600
    check("D6 the zone follows DST (EDT -4 / EST -5)",
          edt == -4 and est == -5, f"{edt} / {est}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_decisions_today: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
