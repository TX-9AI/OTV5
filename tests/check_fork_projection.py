#!/usr/bin/env python3
"""
tests/check_fork_projection.py  v1.1

v1.1  2026-09-23  OTV4TEST r110 — the r106 venv bootstrap: under system python3 (the
      lander's interpreter) 8 of 9 failed on a missing numpy, so the first
      step-1 spec would have been refused at its own CHECK stage.
THE FORK PROJECTION, ON A REAL `Fork` WITH HAND-COMPUTED GEOMETRY.

v1.0  2026-09-23  OTV4TEST LVL.15 step 3 (unlanded WIP). Born RED where
      `derived/fork_projection.py` does not exist — NAMED failures.

The fixture is a bullish fork built from real `Pivot`s: median = 100 + 0.2 per
1h bar from index 0; the upper rail through P1 (104 @ 5) sits +3 above it, the
lower through P2 (100 @ 10) sits -2 below. At index 20: upper 107, median 104,
lower 102 — arithmetic, not the code's own output (§0.4).

  F1  no fork -> an EXPLICIT absence (present False), never an empty list
  F2  the rails at "now" are where the geometry says
  F3  the TINE RULE at price 105: upper = resistance, lower = support, the
      median below price = support; all three oriented
  F3b price ABOVE the upper rail: the upper is NOT a candidate and is NOT
      relabelled support — r5/r103's rule
  F4  the forward projection walks each rail along its own slope (+0.2 / 60 min)
  F5  nearest oriented rail each side, with hours-to-contact at a standing price
      (None when the rail moves AWAY)
  F6  identity is the three anchors — a redrawn fork with new anchors is a NEW
      projection
  F7  a rail is judged at each candle's OWN MINUTE by `level_rules`: a wick that
      reaches the rail as it stood at 09:00 but not as it stands at 09:30 is
      no test at 09:30
  F8  the projection imports nothing from the old level files
"""
from __future__ import annotations

import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# r106 IDIOM — THE LANDER RUNS CHECKS UNDER SYSTEM `python3`, NOT THE VENV, and
# this file reaches pandas/numpy, which live only in the venv (3.14, the same
# ABI as system python3 on this box — measured 2026-09-23). Index 1: the venv
# beats /usr/lib/python3/dist-packages while the repo root still wins. Without
# it this checker could not be DECLARED as a CHECK — it failed under the lander
# on `No module named 'pandas'` while passing by hand.
import glob as _glob
for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def guard(name, fn):
    try:
        ok, detail = fn()
    except Exception as exc:                                    # noqa: BLE001
        ok, detail = False, f"raised {type(exc).__name__}: {exc}"
    check(name, ok, detail)


try:
    from derived import fork_projection as P
    from derived import level_rules as R
    from analysis.pitchfork import Fork, Pivot
except Exception as exc:                                        # noqa: BLE001
    _why = f"fork_projection / level_rules / pitchfork unimportable: {type(exc).__name__}: {exc}"

    class _Absent:
        def __getattr__(self, n):
            raise RuntimeError(_why)
    P = R = _Absent()
    Fork = Pivot = None


def mk(p1_price=104.0):
    return Fork(symbol="QQQ", timeframe="1h", direction="bullish", variant="standard",
                p0=Pivot(0, 100.0, "low", 3, "1h"), p1=Pivot(5, p1_price, "high", 3, "1h"),
                p2=Pivot(10, 100.0, "low", 3, "1h"),
                origin_idx=0.0, origin_price=100.0, slope=0.2, born_idx=13, k=3,
                atr_at_birth=1.0)


close = lambda a, b: abs(a - b) < 1e-9

guard("F1 no fork -> an EXPLICIT absence, never an empty list",
      lambda: ((pr := P.projection(None, None, 105.0))["present"] is False
               and pr["above"] is None and pr["below"] is None, str(pr)))


def _f2():
    pr = P.projection(mk(), 20.0, 105.0)
    r = pr["rails"]
    return (close(r["upper"]["price"], 107.0) and close(r["median"]["price"], 104.0)
            and close(r["lower"]["price"], 102.0)), {k: v["price"] for k, v in r.items()}


guard("F2 the rails at now are where the geometry says (107 / 104 / 102)", _f2)


def _f3():
    r = P.projection(mk(), 20.0, 105.0)["rails"]
    got = {k: (v["role"], v["oriented"]) for k, v in r.items()}
    return got == {"upper": ("resistance", True), "median": ("support", True),
                   "lower": ("support", True)}, str(got)


guard("F3 the tine rule at price 105", _f3)


def _f3b():
    pr = P.projection(mk(), 20.0, 108.0)
    u = pr["rails"]["upper"]
    ok = (u["role"] == "resistance" and u["oriented"] is False
          and pr["above"] is None and pr["below"]["rail"] == "median")
    return ok, f"upper {u['role']}/oriented={u['oriented']}, above {pr['above']}, below {pr['below']['rail']}"


guard("F3b price ABOVE the upper rail: it is not a candidate and NOT relabelled support", _f3b)


def _f4():
    at = P.projection(mk(), 20.0, 105.0)["rails"]["upper"]["at"]
    return (close(at[0], 107.0) and close(at[30], 107.1) and close(at[60], 107.2)), str(at)


guard("F4 the forward projection walks each rail along its own slope", _f4)


def _f5():
    pr = P.projection(mk(), 20.0, 105.0)
    a, b = pr["above"], pr["below"]
    return (a["rail"] == "upper" and close(a["dist_pts"], 2.0) and a["hours_to_contact"] is None
            and b["rail"] == "median" and close(b["dist_pts"], 1.0)
            and close(b["hours_to_contact"], 5.0)), f"above {a} below {b}"


guard("F5 nearest oriented rail each side, hours-to-contact None when it moves away", _f5)

guard("F6 identity is the three anchors — new anchors, new projection",
      lambda: (P.fork_key(mk()) == P.fork_key(mk()) and P.fork_key(mk()) != P.fork_key(mk(104.5)),
               f"{P.fork_key(mk())} vs {P.fork_key(mk(104.5))}"))


def _f7():
    t0 = 1_790_000_000_000                       # "now": the rail is 107.000 here
    edges = P.rail_edges(mk(), "upper", 20.0, t0)
    half = t0 + 30 * 60_000                      # 30 min later the rail is 107.100
    miss = R.judge([(half, 106.9, 107.05, 106.8, 106.95)], edges, R.RESISTANCE)
    hit = R.judge([(half, 106.9, 107.10, 106.8, 106.95)], edges, R.RESISTANCE)
    return (miss == [] and hit == [("TESTED", half), ("HELD", half)]), f"107.05 -> {miss}; 107.10 -> {hit}"


guard("F7 a rail is judged at each candle's OWN minute (107.05 misses the 09:30 rail at 107.10)", _f7)


def _f8():
    tree = ast.parse(open(os.path.join(ROOT, "derived", "fork_projection.py"), encoding="utf-8").read())
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
            bad += [m for m in mods if any(x in m for x in ("liquidity_mapper", "level_map",
                                                            "derived.levels", "pitchfork_lifecycle"))]
    return not bad, f"forbidden imports: {bad}"


guard("F8 the projection imports nothing from the old level files", _f8)

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
