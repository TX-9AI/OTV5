#!/usr/bin/env python3
"""
tests/check_query_sections.py  v1.6
v1.6  2026-09-23  OTV4TEST r126 — Q4 no longer opens analysis/liquidity_mapper.py (deleted):
      it read the file into a variable nothing used. Q4's assertion is unchanged.
v1.5  2026-09-22  OTV4TEST r92 — Q7 covers the two panels that still range-query; Q7b pins
      what replaced the third. r83 replaced show_decisions WHOLESALE by
      ruling and it reads plan_heartbeat — current state, one row per plan,
      with no "today" to cut. Asserting a session cut demanded a design that
      was deliberately removed.
v1.4  2026-09-17  OTV4TEST r35 — reads query.py at the REPO ROOT.
      ⚠️ r34 MOVED IT AND MISSED THIS FILE. Thirteen callers were re-pointed by
      reading; this one and check_plan_signal spell the path differently and were
      not in that grep, and r34 declared only three CHECK lines — so nothing at the
      gate caught it. A delivery that names its own checks gets to choose what it
      is judged on; the full sweep is what finds the rest.
v1.3  2026-09-11  OTV4TEST r14 — reads the operator readers under tools/ (root cleanup).
v1.2  2026-09-02  r216 — Q12/Q12b: the percent column is in PERCENT. It was off
      by 100x from r210 to r216 because `pnl_pct` is a fraction and the row
      formatter dropped the `%` spec that multiplies by 100. Q11 measured the
      row's WIDTH and never its VALUES, which is precisely how a units bug rode
      along inside a formatting change.
v1.1  2026-09-01  r210 (chunk B) — TODAY-SCOPING AND WIDTH. Operator: PLANS,
      GATES and the closed-trade table to TODAY only, abbreviated, "it's
      spanning multi-line". Q7-Q11 added.
      🔑 ONE DEFINITION OF TODAY. r172 inlined the 09:30 cut inside
      show_decisions; gates and plans now need the same boundary, and three
      copies is three chances for two to disagree about what day it is.
      `session_start_epoch()` is extracted and Q7 pins that all three call it.
      🔴 AND THE `-4 hours` EDT HARDCODE WAS IN HERE TOO — the same class r125
      fixed in the otv4 sensors and dtp r236 found in standings.py (RPT.8).
      Q8 refuses its return.
v1.0  2026-09-01  r209 (chunk A) — WHAT THE BOX DASHBOARD IS FOR.

Operator, 2026-09-01, going through `query.py` from the bottom up: Live Levels
"don't care, take it out"; Performance by setup type "that's just trivia in my
opinion, useless by itself"; by setup grade "we don't have grades"; by strategy
"I don't need a per symbol snapshot of that"; all-time "irrelevant"; Character
"keep, but not in query.py — it belongs in status, below the pin line."

🔑 THE THROUGH-LINE IS SCOPE, NOT CLUTTER. This file is the PER-BOX report. An
all-time or by-strategy rollup computed from one symbol's trades.db is a slice
nobody acts on, and day_trader_pro's trade breakdown (r187) already does the
cross-fleet version properly — grouped by strategy, setup type, exit reason,
symbol, hour and weekday, with an ENGINE EPOCH floor.

🔴 AND ONE OF THEM WAS QUIETLY WRONG. `query.py` had no epoch filter at all, so
ALL-TIME PERFORMANCE pooled pre- and post-v4-split trades — 109 trades reaching
back through engines that no longer exist. r187 built the epoch floor for
exactly this contamination and this file never got it. Deleting the section
removes a wrong number, not merely a noisy one.

⚠️ BY SETUP GRADE WAS STRUCTURALLY EMPTY. r152 deleted the setup scorer and
every v4 write path hardcodes `UNGRADED`, so the section had one bucket and
could never have another.

⚠️ THIS IS A VIEW CHANGE, NOT A COLLECTOR CHANGE, and Q4 is what pins that.
`level_ledger` is a LIFECYCLE table — retention_purge excludes it in code
because a recomputation cannot rebuild a biography (r81) — and the sweep and
fork paths read it live. Removing the Live Levels PANEL must not remove a row.

Born red at 7722827 (r207), where Q1, Q2 and Q3 all fail.
"""
from __future__ import annotations

import ast
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

_fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


def main():
    src = open(os.path.join(_root, "query.py"), encoding="utf-8").read()
    tree = ast.parse(src, "query.py")
    fns = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}

    # ── Q1 — the four sections are GONE, definition-shaped ───────────────
    # ⚠️ Tests for a DEFINITION, never a mention (§20): the changelog above
    # names every one of these while explaining why it was removed, so a plain
    # string search would trip on the honest prose the version rule requires.
    dead = [f for f in ("show_alltime", "show_by_strategy", "show_by_grade",
                        "show_by_setup_type") if f in fns]
    check("Q1 the four per-box performance rollups are deleted",
          not dead, f"still defined: {dead}")

    # ── Q2 — and nothing still calls them ────────────────────────────────
    # 🔑 DELETING A DEFINITION AND LEAVING THE CALL is a NameError at runtime
    # that no import test catches — r67's singletons, r100's dead constructors.
    # Every `show_*` call in main() must resolve to a function that exists.
    main_fn = next((n for n in tree.body
                    if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    calls = {c.func.id for c in ast.walk(main_fn)
             if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)} if main_fn else set()
    unresolved = sorted(c for c in calls if c.startswith("show_") and c not in fns)
    check("Q2 every show_* call in main() resolves to a live function",
          main_fn is not None and not unresolved, f"unresolved: {unresolved}")

    # ── Q3 — CHARACTER has left this file ────────────────────────────────
    check("Q3 CHARACTER is no longer rendered by query.py",
          "show_character" not in fns and "show_character(dc)" not in src,
          "it belongs in status.py, below the pin line")

    # ── Q4 — THE LEDGER IS UNTOUCHED. A view change, not a collector one ──
    # ⚠️ THE CHECK THAT MATTERS MOST HERE. "Take Live Levels out" is a request
    # about a PANEL. If it were read as a request about the DATA it would blind
    # the sweep and the fork, and r81 keeps this table unpurged on purpose.
    writers = [f for f in os.listdir(os.path.join(_root, "derived"))
               if f.endswith(".py")]
    lev = any("level_ledger" in open(os.path.join(_root, "derived", f),
                                     encoding="utf-8").read() for f in writers)
    check("Q4 level_ledger is still written and still read elsewhere",
          lev, "the panel went; the collector must not have")

    # ── Q5 — the surviving MARKET half is intact ─────────────────────────
    # A deletion that took its neighbours with it is the other way this goes
    # wrong. Pitchfork and Surface were explicitly kept.
    check("Q5 MARKET keeps the pitchfork and the surface",
          "Pitchfork:" in src and "Surface (1h)" in src
          and "fork_series" in src and "surface_series" in src)

    # ── Q6 — what the operator kept is still here ────────────────────────
    # ⚠️ `show_recent` LEFT THIS SET AT r210 — chunk B merged it into
    # show_today, and Q9 pins that merge. Leaving it here would have made Q6
    # demand a section Q9 demands be absent.
    kept = {"show_open_position": "open positions",
            "show_today": "today's trades",
            "show_decisions": "decisions",
            "show_gates": "gates",
            "show_plans": "plans",
            "show_market": "market"}
    missing = sorted(k for k in kept if k not in fns)
    check("Q6 nothing the operator kept was removed with them",
          not missing, f"missing: {missing}")

    # ── Q7 — ONE definition of "today", used by all three panels ─────────
    # 🔑 r172 established the cut (09:30 ET, not midnight: a 06:00 maintenance
    # wake writes real rows against a market that is not trading). It was
    # inlined in one function; three panels need it now, and a boundary copied
    # three times is two chances to disagree about what day it is (§7).
    fn_src = {}
    for n in tree.body:
        if isinstance(n, ast.FunctionDef):
            fn_src[n.name] = ast.get_source_segment(src, n) or ""
    # 🔴 r92 — `show_decisions` NO LONGER HAS A SESSION CUT, BY RULING, AND
    # THAT IS NOT DRIFT. r83 REPLACED THAT PANEL WHOLESALE at the operator's
    # instruction — *"That whole section should be replaced with code that's
    # accurate"* — and it now reads `plan_heartbeat`, which is UPSERTED one row
    # per plan. Current state has no "today" to cut: a row is either fresh or
    # its heartbeat has stopped, and the panel says which. Asserting a session
    # cut here would demand the design r83 deliberately removed.
    # ⚠️ THE GUARANTEE SURVIVES FOR THE TWO PANELS THAT STILL READ TIME-RANGED
    # TABLES, and that is what Q7 now pins.
    users = [f for f in ("show_gates", "show_plans")
             if "session_start_epoch()" in fn_src.get(f, "")]
    check("Q7 gates and plans share ONE session cut",
          "session_start_epoch" in fns and len(users) == 2,
          f"callers: {users}")
    # 🔑 Q7b — AND WHAT REPLACED IT IN THE DECISIONS PANEL IS PINNED, so this
    # is a MOVED guarantee rather than a dropped one: the panel gates on the
    # 09:30 open and judges liveness by HEARTBEAT AGE, never by row age — the
    # inference r83 removed because r41's edge-triggered rows made a healthy
    # plan look stale after five minutes.
    _dec = fn_src.get("show_decisions", "")
    check("Q7b the decisions panel gates on the open and reads heartbeat AGE",
          ("hour=9, minute=30" in _dec) and ("STALE_S" in _dec)
          and ("plan_heartbeat" in _dec),
          f"open_guard={'hour=9, minute=30' in _dec} stale_s={'STALE_S' in _dec} "
          f"heartbeat={'plan_heartbeat' in _dec}")

    # ── Q8 — the EDT hardcode is gone ────────────────────────────────────
    # 🔴 ANCHORED ON THE AST, NOT THE TEXT, AND THE FIRST DRAFT WAS NOT.
    # A plain string search matched the CHANGELOG SENTENCE that names the bug
    # while explaining its removal — §20 exactly: rule 5 requires the entry to
    # say what changed, so the honest entry contains the token, and the canary
    # is guaranteed to trip on the documentation the version discipline
    # demands. `#` comments are not AST nodes, so scanning string CONSTANTS
    # sees the code and not the prose about it.
    _lits = {n.value for n in ast.walk(tree)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    check("Q8 no hardcoded -4 hours offset survives",
          "-4 hours" not in _lits,
          "EDT is right for eight months and wrong for four")

    # ── Q9 — LAST 10 CLOSED merged away ──────────────────────────────────
    check("Q9 the duplicate closed-trade table is gone",
          "show_recent" not in fns,
          "today-scoping made it the same table as TODAY'S TRADES")

    # ── Q10 — the grade column is gone ───────────────────────────────────
    # r152 deleted the scorer; every write path hardcodes UNGRADED, so the
    # column could only ever print one value.
    check("Q10 the trade table no longer prints a grade column",
          "setup_grade" not in fn_src.get("show_today", ""),
          "one bucket, forever")

    # ── Q11 — A REAL ROW FITS THE PHONE, executed ────────────────────────
    # ⚠️ NOT A SOURCE MATCH — the format string is BUILT and measured, using
    # the operator's own 2026-09-01 trades. A width assertion that reads the
    # f-string proves nothing about what renders.
    import importlib.util as _u
    _sp = _u.spec_from_file_location("_q210", os.path.join(_root, "query.py"))
    _m = _u.module_from_spec(_sp)
    try:
        _sp.loader.exec_module(_m)
    except SystemExit:
        pass
    # ⚠️ THE REAL BUILDER, NOT A COPY OF IT (C.23). `trade_row` is what the
    # table prints; measuring a reconstruction would only prove the
    # reconstruction fits.
    class _R(dict):
        def __getitem__(self, k): return self.get(k)
    widest = 0
    for t, st, side, k, n, e, x, p, pc, w in [
            ("2026-09-01 09:44:00", "ORBStrategy", "put", 705, 2, 1.56, 1.15,
             -82.0, -26.3, "hard_stop_25% pnl=-26.3%"),
            ("2026-09-01 09:46:00", "ORBStrategy", "put", 705, 24, 1.15, 0.94,
             -516.0, -18.7, "orb_structure_stop: 1m close"),
            ("2026-09-01 10:48:00", "RunawayContinuation", "call", 709, 8,
             1.21, 2.56, 1080.0, 111.6, "target_hit pnl=111.6%")]:
        row = _R(exit_time=t, strategy=st, option_side=side, strike=k,
                 contracts=n, entry_premium=e, exit_premium=x, pnl_usd=p,
                 pnl_pct=pc, exit_reason=w, is_butterfly=0, center_strike=0)
        widest = max(widest, len(_m.trade_row(row)))
    # ── Q12 — THE PERCENT COLUMN IS IN PERCENT ──────────────────────────
    # 🔴 OFF BY 100x FROM r210 TO r216. `pnl_pct` is a FRACTION
    # (trade_logger:650 stores (exit - entry)/entry), so a doubling is 1.07.
    # r210 replaced `pct_str` — `f"{val:+.1%}"`, which multiplies by 100 —
    # with a bare `:.0f` while narrowing the row for the phone, and every
    # closed trade since rendered its move as a rounding error. SPX on
    # 2026-09-02 showed 9.15 -> 18.95 as "+1%".
    # ⚠️ Q11 MEASURED THE WIDTH AND NEVER THE VALUE, which is how a units bug
    # rode along inside a formatting change. Width and meaning are different
    # properties and a row check needs both.
    _dbl = _R(exit_time="2026-09-02 10:19:00", strategy="RunawayContinuation",
              option_side="call", strike=7650, contracts=2, entry_premium=9.15,
              exit_premium=18.95, pnl_usd=1960.0, pnl_pct=(18.95 - 9.15) / 9.15,
              exit_reason="target_hit", is_butterfly=0, center_strike=0)
    _row_dbl = _m.trade_row(_dbl)
    check("Q12 a 107% move prints as +107%, not +1%",
          "+107%" in _row_dbl, _row_dbl.strip())

    _loss = _R(exit_time="2026-09-02 10:29:00", strategy="RunawayContinuation",
               option_side="call", strike=7700, contracts=10,
               entry_premium=2.02, exit_premium=1.50, pnl_usd=-520.0,
               pnl_pct=(1.50 - 2.02) / 2.02, exit_reason="hard_stop_20%",
               is_butterfly=0, center_strike=0)
    check("Q12b and a -26% move prints as -26%, not -0%",
          "-26%" in _m.trade_row(_loss), _m.trade_row(_loss).strip())

    check("Q11 a real trade row fits on one line (<= 60 chars)",
          widest <= 60, f"widest {widest}")

    # ⚠️ AND THE REASON KEEPS ITS CAUSE. Abbreviating must not turn four
    # distinct exits into one blank — that would hide WHY a trade ended, which
    # is the column the operator reads first.
    causes = {_m.abbr_reason(r) for r in
              ("hard_stop_25% pnl=-26.3%", "orb_structure_stop: 1m close",
               "target_hit pnl=111.6%", "orb_trail_stop pnl=14.9%")}
    check("Q11b four distinct exits abbreviate to four distinct causes",
          len(causes) == 4 and "" not in causes, str(sorted(causes)))

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_query_sections: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
