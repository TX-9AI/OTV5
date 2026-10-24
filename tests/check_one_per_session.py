#!/usr/bin/env python3
"""
tests/check_one_per_session.py  v1.1
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


def main():
    import tempfile
    from database.trade_logger import TradeLogger

    d = tempfile.mkdtemp()
    db = os.path.join(d, "trades.db")
    lg = TradeLogger(db_path=db)

    def _ins(strategy, when_utc, status):
        with sqlite3.connect(db) as c:
            c.execute("INSERT INTO trades (trade_id, strategy, entry_time, status) "
                      "VALUES (?,?,?,?)",
                      (f"t{strategy}{when_utc}{status}", strategy,
                       when_utc.strftime("%Y-%m-%d %H:%M:%S"), status))

    now = datetime.now(timezone.utc)
    _ins("RunawayContinuation", now - timedelta(hours=30), "CLOSED")   # yesterday
    check("S1a yesterday's trade does not count",
          lg.count_today("RunawayContinuation") == 0,
          str(lg.count_today("RunawayContinuation")))
    _ins("RunawayContinuation", now - timedelta(minutes=5), "OPEN")
    check("S1b a trade this session counts", lg.count_today("RunawayContinuation") == 1)
    _ins("GEXPinButterfly", now - timedelta(minutes=90), "CLOSED")
    check("S2 a CLOSED trade still spends the session's one shot",
          lg.count_today("GEXPinButterfly") == 1)
    lg2 = TradeLogger(db_path=db)                       # the restart
    check("S3 a fresh logger over the same DB reads the same count — a restart "
          "cannot re-arm it", lg2.count_today("GEXPinButterfly") == 1
          and lg2.count_today("RunawayContinuation") == 1)
    lg4 = TradeLogger(db_path=db)
    lg4._connect = lambda: (_ for _ in ()).throw(sqlite3.OperationalError("disk gone"))
    check("S4 an unreadable DB FAILS CLOSED (counts as traded)",
          lg4.count_today("GEXPinButterfly") >= 1)

    src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    n_guards = src.count("_one_per_session_used(")
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
              and n.name == "_attempt_butterfly")
    fb = ast.unparse(fn)
    i_g = fb.find("_one_per_session_used('GEXPinButterfly')")
    i_a = fb.find("_safe_strategy('GEXPinButterfly'")
    check("S5 all three sites guarded, and _attempt_butterfly checks BEFORE asking "
          "the strategy",
          n_guards >= 4 and i_g != -1 and (i_a == -1 or i_g < i_a),
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
