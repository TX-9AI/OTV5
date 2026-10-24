#!/usr/bin/env python3
"""
tests/check_engine_status.py  v4.0
Every engine's self-report reaches disk — including the zeros.

v4.0  2026-08-24  Written after an hour of blind diagnosis. `indicator_series`
and `surface_series` sat at ZERO ROWS on all fifteen boxes: no exception
logged, no write failure logged, engines built, and the same code that wrote a
row on a workstation wrote none on a box.

🔴 THE ENGINES KNEW THE ANSWER AND HAD NO WAY TO SAY IT. `base.status()` has
tracked runs / failures / last_rows / last_error since r62 and nothing ever
persisted or displayed any of it, so the question "did it run and write
nothing, or never run at all?" — three different faults with three different
fixes — could only be guessed at from row counts.

🔑 A COUNTER THAT NEVER LEAVES THE PROCESS IS NOT OBSERVABILITY.

⚠️ S2 IS THE ONE THAT MATTERS. An engine returning 0 WITHOUT raising is exactly
the case that was invisible; a status row written only on failure would have
been just as silent, so the zero must be recorded as a fact.

Run:  cd ~/options-trader && python3 tests/check_engine_status.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


def main() -> int:
    print("=" * 62)
    print("ENGINE STATUS: the derived layer accounts for itself, on disk")
    print("=" * 62)

    db = os.path.join(tempfile.mkdtemp(), "derived_store.db")
    os.environ["OT_DERIVED_DB"] = db
    from data.derived_store import DerivedStore
    from derived.base import run_all, DerivedEngine, STATUS_TABLE

    store = DerivedStore()

    class Silent(DerivedEngine):
        """Returns 0 and never raises — the invisible case."""
        name = "silent"
        table = "none"
        min_interval_s = 0.0

        def derive(self, ctx):
            return 0

    class Angry(DerivedEngine):
        name = "angry"
        table = "none"
        min_interval_s = 0.0

        def derive(self, ctx):
            raise ValueError("boom")

    engines = [Silent(store), Angry(store)]
    run_all(engines, {})

    con = sqlite3.connect(db)
    rows = {r[0]: r for r in con.execute(
        f"SELECT name, runs, failures, last_rows, last_error FROM {STATUS_TABLE}")}

    check("S1 the status table exists and is written after a pass",
          len(rows) == 2, f"rows={list(rows)}")

    # ⚠️ THE ZERO IS THE POINT.
    s = rows.get("silent")
    check("S2 an engine that returns 0 WITHOUT raising is still recorded",
          bool(s) and s[1] == 1 and s[2] == 0 and s[3] == 0 and not s[4],
          f"silent={s}")

    a = rows.get("angry")
    check("S3 a raising engine records the failure AND the exception text",
          bool(a) and a[2] == 1 and a[4] and "boom" in a[4], f"angry={a}")

    # ⚠️ IT MUST SURVIVE REPEATED PASSES, not just the first — the live symptom
    # was a counter that stopped advancing, which only a second pass can show.
    run_all(engines, {})
    con2 = sqlite3.connect(db)
    r2 = {r[0]: r[1] for r in con2.execute(f"SELECT name, runs FROM {STATUS_TABLE}")}
    check("S4 the run counter advances on a second pass",
          r2.get("silent") == 2, f"runs={r2}")

    print("=" * 62)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        return 1
    print("  ALL GREEN — 'ran and wrote nothing' is now a fact, not a guess")
    return 0


if __name__ == "__main__":
    sys.exit(main())
