#!/usr/bin/env python3
"""
tests/check_unrealized_sign.py  v1.0
v1.0  2026-09-01  r214 — THE UNREALIZED LINE, SIGNED BY STRUCTURE.

🔴 `query.py` applied the DEBIT formula `(now - cost)` to every open position.
A credit vertical's `current_premium` is the SPREAD'S CURRENT VALUE — what it
costs to buy back — and the position profits as that FALLS, so its P&L is
`(credit - now)`, the mirror. A winning sweep printed as a loser and a losing
one printed as a winner, on the one line the operator reads before deciding
whether to intervene. Filed as RPT.6 at dtp r236, where `standings.py` got the
sign right and deliberately did NOT copy this — making two reports agree on a
wrong number is worse than having them differ.

⚠️ DISPLAY ONLY, AND THAT WAS VERIFIED RATHER THAN ASSUMED. The same expression
appears EIGHT times in exit_engine.py and every one is a DEBIT evaluator —
`_evaluate_orb`, `_evaluate_sweep` (the retired long SweepReversal),
`_evaluate_butterfly`, `_evaluate_adopted` — where it is correct.
`_evaluate_condor_leg`, the credit path, already computes
`(entry_prem - current_premium)`. No exit decision was ever taken on the wrong
sign; only the report lied. S3 pins that, so a future "tidy-up" cannot
propagate the display fix into an engine that never needed it.

🔑 THE CLASSIFIER IS `structure.is_credit_vertical`, THE ONE THE ENGINE USES.
r22's doctrine: DERIVE it, never add a column — a column fixes tomorrow and not
today, because every position opened before the migration rehydrates without it
and `None` reads as `False`, which is the exact failure, silently.

Born red at 59b94a0 (r213), where S1 and S2 fail.
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


CREDIT = {"strategy": "SweepCreditSpread", "is_credit_vertical": 1,
          "credit_received": 1.30, "spread_width": 2.5,
          "short_strike": 95.0, "long_strike": 92.5, "option_side": "put"}
DEBIT = {"strategy": "ORBStrategy", "strike": 705.0, "option_side": "put"}


def _q():
    """query.py, imported for execution.

    🔴 THE FIRST DRAFT OF THIS FILE RE-IMPLEMENTED THE FORMULA HERE and
    measured its own copy — which passed against the broken query.py, because
    the copy was right. C.23: a test that re-implements the thing it measures
    tests itself. It now calls `query.unrealized`, the function the panel uses.
    """
    import importlib.util as u
    sp = u.spec_from_file_location("_q214", os.path.join(_root, "query.py"))
    m = u.module_from_spec(sp)
    try:
        sp.loader.exec_module(m)
    except SystemExit:
        pass
    return m


def _move(record, entry, now):
    """The move as query.py ACTUALLY computes it — dollars on one contract."""
    usd, _pct = _q().unrealized(record, entry, now, 1)
    return (usd or 0) / 100.0


def main():
    # ⚠️ DEGRADE TO A NAMED FAILURE, NEVER A TRACEBACK (r192). Against r213
    # this file died on `query.unrealized` missing and printed ONE failing line
    # before the AttributeError killed the rest — "the checker crashed" and
    # "the invariant is violated" must not look alike, and a partial run is the
    # worse of the two because it looks like a result.
    if not hasattr(_q(), "unrealized"):
        check("S0 query.unrealized exists", False, "not implemented")
        print()
        print("FAILED 1: query.py is pre-r214 (the unrealized line is inline "
              "and applies the debit formula to every structure)")
        return 1

    src = open(os.path.join(_root, "query.py"), encoding="utf-8").read()
    tree = ast.parse(src, "query.py")

    # ── S1 — query.py asks the classifier at all ─────────────────────────
    calls = {n.func.id for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    names = {n.value for n in ast.walk(tree)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    check("S1 the unrealized line consults is_credit_vertical",
          "unrealized" in {n.name for n in ast.walk(tree)
                           if isinstance(n, ast.FunctionDef)}
          and ("is_credit_vertical" in calls or "_is_cv" in calls
               or "is_credit_vertical" in names),
          "the debit formula was applied to every structure")

    # ── S1b — absent is not zero ─────────────────────────────────────────
    _u = _q().unrealized
    check("S1b no live mark returns None, never a fabricated 0.00",
          _u(DEBIT, 0.42, None, 10) == (None, None)
          and _u(DEBIT, 0.42, 0, 10) == (None, None))

    # ── S2 — EXECUTED, both directions, both structures ─────────────────
    # 🔑 The sign is the whole defect, so the check computes it rather than
    # reading it. A credit that TIGHTENS is a winner; one that WIDENS is a
    # loser; a debit is the mirror of both.
    try:
        cw = _move(CREDIT, 1.30, 0.90)      # bought back cheaper -> profit
        cl = _move(CREDIT, 1.30, 1.70)      # bought back dearer  -> loss
        dw = _move(DEBIT, 0.42, 0.55)       # sold higher         -> profit
        dl = _move(DEBIT, 0.42, 0.30)       # sold lower          -> loss
        ok = cw > 0 and cl < 0 and dw > 0 and dl < 0
        detail = f"credit {cw:+.2f}/{cl:+.2f}  debit {dw:+.2f}/{dl:+.2f}"
    except Exception as exc:                                    # noqa: BLE001
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    check("S2 a tightening credit is a WIN and a widening one is a LOSS", ok, detail)

    # ── S3 — THE ENGINE IS NOT 'FIXED' TOO ──────────────────────────────
    # 🔴 THE REGRESSION THIS EXISTS TO STOP. Eight debit evaluators use
    # `(current - entry)` CORRECTLY. A later reader who sees the display fix
    # and "makes them consistent" would invert every debit exit in the book.
    # `_evaluate_condor_leg` — the credit path — must keep the credit sign, and
    # the debit evaluators must keep theirs.
    esrc = open(os.path.join(_root, "execution", "exit_engine.py"),
                encoding="utf-8").read()
    etree = ast.parse(esrc, "exit_engine.py")
    fn = {}
    for n in ast.walk(etree):
        if isinstance(n, ast.FunctionDef):
            fn[n.name] = ast.get_source_segment(esrc, n) or ""
    credit_ok = "(entry_prem - current_premium)" in fn.get("_evaluate_condor_leg", "")
    debit_ok = all("(current_premium - entry_prem)" in fn.get(f, "")
                   for f in ("_evaluate_orb", "_evaluate_butterfly"))
    check("S3 the exit engine keeps a credit sign on credits, debit on debits",
          credit_ok and debit_ok,
          f"condor_leg={credit_ok} debit_evaluators={debit_ok}")

    # ── S4 — the classification is DERIVED, not a stored flag ───────────
    # r22: a column fixes tomorrow and not today — every position opened before
    # a migration rehydrates without it and None reads as False.
    from strategy import structure as S
    legacy = {"strategy": "SweepCreditSpread", "short_strike": 95.0,
              "long_strike": 92.5, "option_side": "put", "credit_received": 1.30,
              "spread_width": 2.5}
    check("S4 a row with no is_credit_vertical flag still classifies as credit",
          S.is_credit_vertical(legacy),
          "derived from the structure, so it works on rows that already exist")

    # ── S5 — and it FAILS CLOSED to debit ───────────────────────────────
    check("S5 an unrecognised record is treated as a debit",
          not S.is_credit_vertical({"strategy": "SomethingNew"})
          and not S.is_credit_vertical({}),
          "every legacy row in this book is a debit")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_unrealized_sign: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
