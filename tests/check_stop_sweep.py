#!/usr/bin/env python3
"""tests/check_stop_sweep.py — v1.0
THE STOP SWEEP REFUSES THIN SAMPLES, OUT LOUD (RPL.3).

v1.0  2026-09-19  OTV4TEST r63 — `stop_sweep` is one of the instruments the
      operator drives from the R SUITE to size a decision, and NOTHING GATED IT.
      Measured: 32 of this tree's 166 `tests/` modules are outside the sweep
      (it globs `check_*.py`), and of the analysis tools only `r_ledger` and
      — since r62 — `exit_replay` had any gate at all.

⚠️ THIS GATE IS GREEN ON BOTH SIDES AND THAT IS STATED RATHER THAN DRESSED UP.
`stop_sweep` is NOT broken: driven against the real book it read all ten
strategy/side groups and correctly declined to produce a surface, citing §12 by
name. There is no defect here to be born red against. Its value is that the
next change to this file cannot go unnoticed — so it is MUTATION-PROVEN instead
(drop MIN_N, or make the refusal silent, and it goes red by name).

🔑 THE FAILURE IT IS BUILT AGAINST IS `exit_replay`'S: an instrument that reads
nothing and reports a clean-looking result. S4 therefore asserts the sweep
CONSUMES its rows rather than merely returning without error.

  S1  the tool's own selftest passes
  S2  MIN_N binds — a thin sample yields NO surface (§12)
  S3  ...and the refusal is NAMED, never a silent empty render
  S4  a sufficient sample DOES produce cells (it reads rows, it does not just not-crash)
  S5  both bounds are swept — pessimistic and optimistic, never one (bounds, not points)
  S6  the grids are unchanged (not widened to manufacture a winner)

Run:  python3 tests/check_stop_sweep.py
"""
import io
import contextlib
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "tests"))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def guard(name, fn):
    try:
        ok, detail = fn()
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"{type(exc).__name__}: {exc}")
        return
    check(name, bool(ok), detail)


import stop_sweep as ss                                         # noqa: E402


def _rows(n):
    """Rows in the shape `r_ledger.position_dollars` actually reads —
    `mfe_premium` / `mae_premium`, NOT percentage columns. My first fixture
    invented `mfe_pct`/`mae_pct`, every row returned None, and S4/S5 went red
    on CORRECT code: a fixture built from the assistant's belief about the
    schema rather than from the schema (§0.4)."""
    out = []
    for i in range(n):
        winner = i % 2 == 0
        out.append({"entry_premium": 1.00,
                    "mfe_premium": 1.60 if winner else 1.05,
                    "mae_premium": 0.90 if winner else 0.55,
                    "pnl_usd": 50.0 if winner else -40.0,
                    "contracts": 1})
    return out


guard("S1 stop_sweep's own selftest passes", lambda: (ss.selftest() == 0, ""))
guard("S2 MIN_N binds — a thin sample yields NO surface",
      lambda: (ss.sweep(_rows(ss.MIN_N - 1)) == [], f"MIN_N={ss.MIN_N}"))


def _named():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ss.render(_rows(ss.MIN_N - 1), "FIXTURE")
    out = buf.getvalue()
    return ("FIXTURE" in out and str(ss.MIN_N) in out and out.strip() != ""), out.strip()[:60]


guard("S3 ...and the refusal is NAMED, never silent", _named)
guard("S4 a sufficient sample DOES produce cells (it reads rows)",
      lambda: (len(ss.sweep(_rows(ss.MIN_N * 3))) > 0,
               f"{len(ss.sweep(_rows(ss.MIN_N * 3)))} cells"))
guard("S5 both bounds are swept, never one",
      lambda: ({c["bound"] for c in ss.sweep(_rows(ss.MIN_N * 3))} == {"pess", "opt"}, ""))
guard("S6 the grids are unchanged",
      lambda: (ss.STOP_GRID == [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
               and ss.TP_GRID == [None, 0.25, 0.50, 0.75, 1.00, 1.50]
               and ss.MIN_N == 20, ""))

print()
if FAILED:
    print(f"  RED — {len(FAILED)} of {len(RAN)} failed: " + ", ".join(FAILED))
    sys.exit(1)
print(f"  GREEN — {len(RAN)} checks")
