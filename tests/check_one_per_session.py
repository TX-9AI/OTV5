#!/usr/bin/env python3
"""
tests/check_one_per_session.py  v5.2
v5.2  2026-11-15  OTV5 r126 (HYG.29) — THE CHECK NO LONGER DEPENDS ON THE HOUR IT RUNS. r0's S1b/S2 put their in-session trades at a fixed now-5min / now-90min, which lands BEFORE ET midnight during the first 90 minutes of every ET day: S2/S3 went red 00:00-01:30 ET (S1b too, 00:00-00:05) and green after, with count_today correct throughout (the 11-15 sweep ran at ~01:00 ET; reproduced at pinned clocks, red at 05:03/05:30/06:20 UTC, green at 06:40/15:00). S1-S4 now run as _db_scenario at seven pinned clocks (00:03, 00:45, 01:29, 10:00, 23:58 ET in EST; 00:20, 21:30 ET in EDT) and the real clock, every in-session time placed between ET midnight and now; S1a adds a trade 1 s before ET midnight, S2 enters 1 s after it, new S2b a trade exactly AT ET midnight (OGAP). Five count_today mutants each red: UTC midnight, `>` for `>=`, a rolling 24 h window, open-only, fail-open. S5-S6 unchanged.
v5.1  2026-11-09  OTV5 r103 (RETIRE.5 step 2) — RE-POINTED (WA 38.4): the GEX fly and _attempt_butterfly are removed, so S2-S4 count PARK (the other one-per-session trade) and S5 pins _attempt_park checking BEFORE asking PARK, with the remaining guard sites (Runaway, PARK). S1, S5b, S6 unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.1  2026-10-11  r481 / RUN.1 — S6: THE RUNAWAY CAP MUST GATE, NOT NARRATE.
      S5 counted guard CALLS and pinned the butterfly's order, and never asked
      whether the runaway's strategy call was reachable after the skip. It was:
      the skip sat in an if/elif chain and the call in a separate `if`, so for
      six weeks the box wrote "already traded today" and traded. S6 finds the
      If that holds `_runaway_strategy.generate_signal` and requires its test to
      carry `not _rc_capped`, with `_rc_capped` bound from the cap. Born red at
      4c4bd19; a mutant that drops the `not _rc_capped` is killed.
v1.0  2026-08-28  r179

ONE RUNAWAY, ONE BUTTERFLY, PER SESSION, PER BOX — DB-BACKED.

Operator, 2026-08-28, after the butterfly stacked through TWO hotfixes and
five restarts: "Only one runway debit trade aloud per session on a box.
Only one GEX Pin butterfly allowed per session on a box. Simple."

Born red at d29a9fc (r178). Why the in-process locks failed: every systemd
bounce cleared them, and 08-28 had five bounces. This cap reads trades.db.

  S1  count_today: a trade entered THIS ET session counts; yesterday's does
      not — the boundary is ET midnight expressed in UTC (entry_time is UTC)
  S2  the cap trips on OPEN and CLOSED trades alike (a closed fly still
      spends the session's one shot)
  S3  a restart cannot re-arm it: a fresh logger over the same DB reads the
      same count
  S4  FAILS CLOSED: an unreadable DB counts as traded
  S5  main guards all THREE sites — the runaway dispatch, the in-dispatch
      butterfly path, and _attempt_butterfly's entry — each BEFORE the
      strategy is asked, each writing a plan row (AST)
  S6  the runaway strategy call is UNREACHABLE once the cap is used: its If
      test carries `not _rc_capped`, bound from _one_per_session_used (AST)
"""
import ast
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def _db_scenario(now_utc, tag):
    """S1-S4 against a fresh DB with the clock pinned to NOW_UTC (None = the real clock).
    v5.2: every in-session timestamp sits BETWEEN ET midnight and now, so the check means the
    same thing at 00:03 ET as at noon (r0's fixed now-5min / now-90min offsets landed BEFORE
    ET midnight in the first 90 minutes of every ET day and went red there)."""
    import tempfile
    import datetime as _dtm
    from database.trade_logger import TradeLogger
    from utils.time_utils import ET

    real = _dtm.datetime
    if now_utc is not None:
        class _Pinned(real):
            @classmethod
            def now(cls, tz=None):
                return now_utc.astimezone(tz) if tz else now_utc.replace(tzinfo=None)
        _dtm.datetime = _Pinned
    try:
        now = real.now(timezone.utc) if now_utc is None else now_utc
        mid = now.astimezone(ET).replace(hour=0, minute=0, second=0, microsecond=0
                                         ).astimezone(timezone.utc)
        span = (now - mid).total_seconds()
        if span < 4:                       # the real clock within 4 s of ET midnight
            return None
        at = lambda frac: mid + timedelta(seconds=max(1, int(span * frac)))

        d = tempfile.mkdtemp()
        db = os.path.join(d, "trades.db")
        lg = TradeLogger(db_path=db)

        def _ins(strategy, when_utc, status):
            with sqlite3.connect(db) as c:
                c.execute("INSERT INTO trades (trade_id, strategy, entry_time, status) "
                          "VALUES (?,?,?,?)",
                          (f"t{strategy}{when_utc}{status}", strategy,
                           when_utc.strftime("%Y-%m-%d %H:%M:%S"), status))

        _ins("RunawayContinuation", mid - timedelta(seconds=1), "CLOSED")   # 1 s before ET midnight
        _ins("RunawayContinuation", mid - timedelta(hours=6), "CLOSED")     # yesterday
        check(f"S1a [{tag}] yesterday's trades, one of them 1 s before ET midnight, do not count",
              lg.count_today("RunawayContinuation") == 0,
              str(lg.count_today("RunawayContinuation")))
        _ins("RunawayContinuation", at(0.9), "OPEN")
        check(f"S1b [{tag}] a trade this session counts",
              lg.count_today("RunawayContinuation") == 1)
        _ins("PARK", mid + timedelta(seconds=1), "CLOSED")                  # 1 s after ET midnight
        check(f"S2 [{tag}] a CLOSED trade still spends the session's one shot "
              f"(entered 1 s after ET midnight)", lg.count_today("PARK") == 1)
        _ins("OGAP", mid, "CLOSED")                                         # exactly ET midnight
        check(f"S2b [{tag}] a trade entered exactly at ET midnight is this session's",
              lg.count_today("OGAP") == 1)
        lg2 = TradeLogger(db_path=db)                                       # the restart
        check(f"S3 [{tag}] a fresh logger over the same DB reads the same count - a restart "
              "cannot re-arm it", lg2.count_today("PARK") == 1
              and lg2.count_today("RunawayContinuation") == 1)
        lg4 = TradeLogger(db_path=db)
        lg4._connect = lambda: (_ for _ in ()).throw(sqlite3.OperationalError("disk gone"))
        check(f"S4 [{tag}] an unreadable DB FAILS CLOSED (counts as traded)",
              lg4.count_today("PARK") >= 1)
        return True
    finally:
        _dtm.datetime = real


# v5.2: the clocks the DB scenario runs at. 00:03 / 00:45 / 01:29 ET are inside the window r0's
# offsets broke (red 00:00-01:30 ET every day); 23:58 ET is the far edge; 10:00 ET is a session
# hour; and in EDT as well as EST, so the UTC offset of ET midnight is exercised both ways.
_CLOCKS = [
    ("00:03 ET (EST)", datetime(2026, 11, 16, 5, 3, tzinfo=timezone.utc)),
    ("00:45 ET (EST)", datetime(2026, 11, 16, 5, 45, tzinfo=timezone.utc)),
    ("01:29 ET (EST)", datetime(2026, 11, 16, 6, 29, tzinfo=timezone.utc)),
    ("10:00 ET (EST)", datetime(2026, 11, 16, 15, 0, tzinfo=timezone.utc)),
    ("23:58 ET (EST)", datetime(2026, 11, 17, 4, 58, tzinfo=timezone.utc)),
    ("00:20 ET (EDT)", datetime(2026, 7, 14, 4, 20, tzinfo=timezone.utc)),
    ("21:30 ET (EDT)", datetime(2026, 7, 14, 1, 30, tzinfo=timezone.utc)),
]


def main():
    for tag, t in _CLOCKS:
        _db_scenario(t, tag)
    _db_scenario(None, "real clock")

    src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    n_guards = src.count("_one_per_session_used(")
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
              and n.name == "_attempt_park")                       # r103: _attempt_butterfly removed
    fb = ast.unparse(fn)
    i_g = fb.find("_one_per_session_used('PARK')")
    i_a = fb.find("_safe_strategy('PARK'")
    check("S5 the guard sites stand (Runaway, PARK), and _attempt_park checks BEFORE asking "
          "the strategy (r103: the fly's site removed)",
          n_guards >= 3 and i_g != -1 and i_a != -1 and i_g < i_a,
          f"guards={n_guards} order={i_g}<{i_a}")
    check("S5b the skips are plan rows",
          'one per session on this box' in src and src.count("one per session on this box") >= 3)

    # ── S6 — the cap GATES the runaway call ─────────────────────────────
    def _calls_runaway(node):
        return any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                   and c.func.attr == "generate_signal"
                   and isinstance(c.func.value, ast.Name)
                   and c.func.value.id == "_runaway_strategy"
                   for c in ast.walk(node))
    gate_ifs = [n for n in ast.walk(tree) if isinstance(n, ast.If)
                and any(_calls_runaway(b) for b in n.body)
                and not any(isinstance(b, ast.If) and _calls_runaway(b) for b in n.body)]
    neg = lambda t: any(isinstance(x, ast.UnaryOp) and isinstance(x.op, ast.Not)
                        and isinstance(x.operand, ast.Name) and x.operand.id == "_rc_capped"
                        for x in ast.walk(t))
    bound = any(isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_rc_capped"
                                                  for t in n.targets)
                and "_one_per_session_used('RunawayContinuation')" in ast.unparse(n.value)
                for n in ast.walk(tree))
    check("S6 the runaway call sits under `not _rc_capped`, bound from the cap",
          len(gate_ifs) == 1 and neg(gate_ifs[0].test) and bound,
          f"ifs={len(gate_ifs)} test={ast.unparse(gate_ifs[0].test) if gate_ifs else None} "
          f"bound={bound}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_one_per_session: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
