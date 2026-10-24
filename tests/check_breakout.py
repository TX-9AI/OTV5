#!/usr/bin/env python3
"""
tests/check_breakout.py  v1.0
THE SPEC DECLARES, THE PLAN SEARCHES, THE STRATEGY CONFIRMS (BRK.1).

v1.0  2026-09-18  OTV4TEST r51 — born red at r50 (b7f2e41): none of the three
      files exists there.

THE OPERATOR'S CONTRACT, 2026-09-18, verbatim and load-bearing:
  *"The strategy file is the specification. It lists the bars that must be
  cleared to execute the trade. The plan file is what searches the feed every
  tick for the nearest qualifying setup that satisfies the strategy… If it
  can't satisfy every single hurdle then it doesn't put forward a plan. The
  plan exists for the sole purpose of forming the trigger the strategy executes
  on."* And: *"the strategy must determine if all the trigger components
  provided by the plan are in place to fire."*

⚠️ B4 IS THE ONE THAT MATTERS AND IT IS BEHAVIOURAL. The rule is "no plan goes
forward unless EVERY bar cleared", and that cannot be read from source — a
`ready` flag set on the wrong branch looks identical. B4 drives the real plan
with one bar failing and demands `ready is False`.
"""
import ast
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_TRADES_DB", os.path.join(tempfile.mkdtemp(), "t.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(tempfile.mkdtemp(), "d.db"))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def guard(name, fn, detail=""):
    try:
        ok = fn()
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"{type(exc).__name__}: {exc}")
        return False
    try:
        det = detail() if callable(detail) else detail
    except Exception:                                           # noqa: BLE001
        det = ""
    check(name, ok, det)
    return ok


class _ORB:
    orb_high, orb_low = 101.00, 100.00


def _df(rows):
    import pandas as pd
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c, "volume": v} for o, h, l, c, v in rows],
        index=pd.date_range("2026-09-21 09:30", periods=len(rows), freq="1min"))


# five range bars, then a bar CLOSING beyond the high, then the live bar
BROKE = [(100.2, 100.9, 100.0, 100.5, 900)] * 5 + \
        [(100.6, 101.40, 100.55, 101.30, 2400), (101.3, 101.4, 101.2, 101.35, 800)]
# the same, but the break bar only WICKS through and closes back inside
WICKED = [(100.2, 100.9, 100.0, 100.5, 900)] * 5 + \
         [(100.6, 101.40, 100.55, 100.80, 2400), (100.8, 100.9, 100.7, 100.85, 800)]


def _tail():
    print()
    print(f"RED — {len(FAILED)} of {len(RAN)} failed (BRK.1 absent at this HEAD)")
    return 1


def main():
    # 🔴 THE IMPORTS ARE GUARDED, AND THE FOURTH REPEAT IS WHY. `check_level_source`
    # (r32), `check_manifold_board` M4b (r37), `check_zones` (r39) and
    # `check_plan_status` (r41) each CRASHED at the older HEAD they were written
    # to fail at. r44's ledger says outright: *"three times is not a slip, it is
    # a pattern, and the fix belongs in the next checker written."* This is the
    # next checker, and its first cut crashed too — `ModuleNotFoundError: No
    # module named 'strategy.breakout'`. A traceback cannot say WHICH rule is
    # absent and reads identically to a broken checker, so the born-red proof it
    # exists to give is worth nothing.
    try:
        from strategy.breakout import Breakout
        from strategy.breakout_plan import BreakoutPlan
    except Exception as exc:                                    # noqa: BLE001
        why = f"{type(exc).__name__}: {exc}"
        for n in ("B1 the SPEC searches nothing",
                  "B2 every declared bar has a stated meaning",
                  "B2b the PERSISTENT bars are a SUBSET of the declared ones",
                  "B3 volume expansion is NOT a condition",
                  "B4 a bar that FAILS leaves the plan unformed",
                  "B4b and it names WHICH bars are missing",
                  "B5 a WICK through the edge is not a break",
                  "B6 outside the window the plan is DORMANT",
                  "B7 the STRATEGY re-checks the PERSISTENT bars",
                  "B7b ...and that price is still beyond the trigger"):
            check(n, False, why)
        Breakout = BreakoutPlan = None

    # ── B1/B2 — the SPEC declares and does not search ──────────────────────
    _sp = os.path.join(ROOT, "strategy", "breakout.py")
    src = open(_sp, encoding="utf-8").read() if os.path.exists(_sp) else ""
    tree = ast.parse(src)

    def spec_does_not_search():
        banned = {"board_for", "aggression", "depth", "regime", "select_contract"}
        return not any(isinstance(n, ast.Call)
                       and (getattr(n.func, "id", "") in banned
                            or getattr(n.func, "attr", "") in banned)
                       for n in ast.walk(tree))
    guard("B1 the SPEC searches nothing — no board, no flow, no chain, no strike",
          spec_does_not_search, "it lists the bars; the plan clears them")

    guard("B2 every declared bar has a stated meaning",
          lambda: (len(Breakout.CONDITIONS) >= 6
                   and all(isinstance(v, str) and len(v) > 12
                           for v in Breakout.CONDITIONS.values())),
          lambda: f"{len(Breakout.CONDITIONS)} conditions")

    guard("B2b the PERSISTENT bars are a SUBSET of the declared ones",
          lambda: set(Breakout.PERSISTENT) and set(Breakout.PERSISTENT) <= set(Breakout.CONDITIONS),
          lambda: f"persist={list(Breakout.PERSISTENT)}")

    # 🔴 VOLUME IS RECORDED, NEVER GATED — measured useless over 736 breaks
    guard("B3 volume expansion is NOT a condition — measured, n=736, lift 1.08x",
          lambda: not any("vol" in c for c in Breakout.CONDITIONS)
          and "vol_multiple" in Breakout.PLAN_CHECKS,
          "recorded as context so a study can revisit it; never a gate")

    # ── B4 — NO PLAN unless EVERY bar cleared (behavioural) ────────────────
    if Breakout is None:
        return _tail()
    plan = BreakoutPlan()

    def prep_with(rows, now="10:00", chain=None):
        return plan.prepare(spec=Breakout, orb=_ORB(), price_now=rows[-1][3],
                            now_et=now, chain=chain, df_1m=_df(rows),
                            flow_conn=None, symbol="TST")

    p_broke = prep_with(BROKE)
    guard("B4 a bar that FAILS leaves the plan unformed — ready is False",
          lambda: p_broke.ready is False and bool(p_broke.unmet),
          lambda: f"unmet={p_broke.unmet[:4]}")

    guard("B4b and it names WHICH bars are missing, never a bare refusal",
          lambda: all(u in Breakout.CONDITIONS for u in p_broke.unmet),
          lambda: f"{p_broke.unmet}")

    # ── B5 — the break is a CLOSE, not a wick (r5) ─────────────────────────
    p_wick = prep_with(WICKED)
    guard("B5 a WICK through the edge is not a break — bodies decide (r5)",
          lambda: (p_wick.conditions.get("break_close", (None, "", None))[2] is False
                   and p_broke.conditions.get("break_close", (None, "", None))[2] is True),
          "the anti-fakeout gate that costs nothing in TIME")

    # ── B6 — outside the window it is DORMANT, one row then quiet ──────────
    p_out = prep_with(BROKE, now="08:00")
    guard("B6 outside the window the plan is DORMANT, not evaluated",
          lambda: p_out.ready is False and not p_out.conditions.get("orb_range"),
          "r41: one row on the transition, then silence")

    # ── B7 — the STRATEGY confirms; it does not re-derive ──────────────────
    btree = ast.parse(src)
    gs = next((n for n in ast.walk(btree) if isinstance(n, ast.FunctionDef)
               and n.name == "generate_signal"), None)

    def confirms_persist():
        return gs is not None and any(
            isinstance(n, ast.Attribute) and n.attr == "PERSISTENT" for n in ast.walk(gs))
    guard("B7 the STRATEGY re-checks the PERSISTENT bars before firing",
          confirms_persist,
          "the operator: 'the strategy must determine if all the trigger "
          "components provided by the plan are in place to fire'")

    def confirms_trigger():
        return gs is not None and any(
            isinstance(n, ast.Attribute) and n.attr == "trigger" for n in ast.walk(gs))
    guard("B7b ...and that price is still beyond the trigger", confirms_trigger)

    # ── B8 — the exits are declared AND wired ──────────────────────────────
    from strategy.management import EXIT_CONDITIONS, COVERED
    guard("B8 Breakout is COVERED by the management plan",
          lambda: "Breakout" in COVERED)
    guard("B8b it declares an EXHAUSTION exit — it has no target",
          lambda: "exhaustion" in EXIT_CONDITIONS.get("Breakout", {}),
          "runaway exits on thesis, hunt at its target, breakout on exhaustion")

    msrc = open(os.path.join(ROOT, "strategy", "management.py"), encoding="utf-8").read()

    def exhaustion_wired():
        mt = ast.parse(msrc)
        return any(isinstance(n, ast.Call)
                   and getattr(n.func, "attr", "") == "_momentum_divergence"
                   for n in ast.walk(mt))
    guard("B8c 🔴 and the exhaustion exit is WIRED, not just declared",
          exhaustion_wired,
          "the helpers had ZERO call sites — a declared exit that cannot fire "
          "is the defect this repo keeps finding")

    # ── B9 — admission carries it, non-competing ───────────────────────────
    from execution.position_manager import rules
    r = rules().get("Breakout")
    guard("B9 admission carries Breakout, and it blocks nothing",
          lambda: r is not None and not set(r.blocks) and not set(r.blocked_by),
          lambda: f"window={r.window} cap={r.max_open_of_type}" if r else "absent")

    # ── B10 — main.py actually asks it ─────────────────────────────────────
    main_src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()

    def dispatched():
        fn = next((n for n in ast.walk(ast.parse(main_src))
                   if isinstance(n, ast.FunctionDef) and n.name == "attempt_new_entry"), None)
        return fn is not None and any(
            isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_safe_strategy"
            and n.args and isinstance(n.args[0], ast.Constant)
            and n.args[0].value == "Breakout" for n in ast.walk(fn))
    guard("B10 the dispatch ASKS Breakout — a strategy nothing calls is inert",
          dispatched)

    print()
    if Breakout is None:
        print(f"\nRED — {len(FAILED)} of {len(RAN)} failed (BRK.1 absent at this HEAD)")
        return 1
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
