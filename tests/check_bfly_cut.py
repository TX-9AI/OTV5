#!/usr/bin/env python3
"""
tests/check_bfly_cut.py  v5.0
v5.0  2026-11-08  OTV5 r97 (RETIRE.5) — born with the cut.

THE GEX PIN BUTTERFLY IS CUT FROM 2026-11-09. The operator, 2026-11-08: "I agree that our GEX fly may be on the
chopping block. In fact, I'm considering cutting it starting tomorrow" and "I concur on both, in that order" (step 1:
no new fly from 11-09; step 2: its code removed after that close). Evidence: window EV -$6,482 [-19.2k, +3.2k], lunch
entries lose, no fly since 11-03 (research r2).

  B1  config.GEX_BUTTERFLY_ENABLED is False, written in code: config reads no OT_GEX_BUTTERFLY (no env turns it on)
  B2  plan_state reads GEXPinButterfly DORMANT with OT_GEX_BUTTERFLY unset, "1", "active", "on" and "log" -
      a cut plan has no LOG state either
  B3  its TABLE default is DORMANT, so an unreadable state also reads DORMANT
  B4  main._attempt_butterfly asks nothing and writes nothing when DORMANT: no _safe_strategy, no _plan_skip,
      no one-per-session read, no chain read
  B5  the harness flip still works: with config.GEX_BUTTERFLY_ENABLED True (a checker) the plan reads ACTIVE,
      so the butterfly's own checkers keep exercising its code until step 2 removes it
  B6  exits are untouched: GEXPinButterfly is still in HOLD_TO_CLOSE_STRATEGIES and management's EXIT_CONDITIONS
  B7  the strategy module's own ENABLED reads False (its `enabled` condition is unmet even if asked)
"""
import os
import re
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def main():
    import config
    check("B1a config.GEX_BUTTERFLY_ENABLED is False", config.GEX_BUTTERFLY_ENABLED is False,
          repr(config.GEX_BUTTERFLY_ENABLED))
    src = open(os.path.join(_root, "config.py"), encoding="utf-8").read()
    check("B1b config reads no OT_GEX_BUTTERFLY (no env value turns the fly on)",
          not re.search(r"environ[^\n]*OT_GEX_BUTTERFLY", src))

    from strategy import plan_state as ps
    saved = os.environ.get("OT_GEX_BUTTERFLY")
    try:
        for v in (None, "1", "active", "on", "log"):
            if v is None:
                os.environ.pop("OT_GEX_BUTTERFLY", None)
            else:
                os.environ["OT_GEX_BUTTERFLY"] = v
            st = ps.state("GEXPinButterfly")
            check(f"B2 OT_GEX_BUTTERFLY={v!r} -> dormant", st == ps.DORMANT, st)
    finally:
        if saved is None:
            os.environ.pop("OT_GEX_BUTTERFLY", None)
        else:
            os.environ["OT_GEX_BUTTERFLY"] = saved
    check("B3 TABLE default is DORMANT", ps.default("GEXPinButterfly") == ps.DORMANT, ps.default("GEXPinButterfly"))

    import main as m
    calls = []

    class _Ctx(dict):
        def get(self, k, d=None):
            calls.append(("ctx.get", k))
            return dict.get(self, k, d)

        def __getitem__(self, k):
            calls.append(("ctx[]", k))
            return dict.__getitem__(self, k)

    orig = (m._safe_strategy, m._plan_skip, m._one_per_session_used)
    m._safe_strategy = lambda *a, **k: calls.append(("_safe_strategy", a[0] if a else None))
    m._plan_skip = lambda *a, **k: calls.append(("_plan_skip", a[0] if a else None))
    m._one_per_session_used = lambda *a, **k: calls.append(("_one_per_session_used", a[0] if a else None)) or False
    try:
        m._attempt_butterfly(_Ctx(chain=object(), price=100.0), None, None, additive=True)
    finally:
        m._safe_strategy, m._plan_skip, m._one_per_session_used = orig
    check("B4 _attempt_butterfly asks nothing and writes nothing when DORMANT", calls == [], str(calls[:4]))

    config.GEX_BUTTERFLY_ENABLED = True
    try:
        st = ps.state("GEXPinButterfly")
        check("B5 a checker's flip (GEX_BUTTERFLY_ENABLED True) still reads ACTIVE", st == ps.ACTIVE, st)
    finally:
        config.GEX_BUTTERFLY_ENABLED = False

    from strategy import management as mg
    check("B6a GEXPinButterfly still holds to the close (exits untouched)",
          "GEXPinButterfly" in tuple(getattr(config, "HOLD_TO_CLOSE_STRATEGIES", ())))
    check("B6b management keeps its GEXPinButterfly exit conditions",
          "GEXPinButterfly" in getattr(mg, "EXIT_CONDITIONS", {}))

    from strategy import gex_pin_butterfly as gb
    check("B7 gex_pin_butterfly.ENABLED is False", gb.ENABLED is False, repr(gb.ENABLED))

    print()
    if _fails:
        print(f"FAIL — {len(_fails)}: " + "; ".join(_fails))
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
