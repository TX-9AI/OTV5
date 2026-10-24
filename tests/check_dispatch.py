#!/usr/bin/env python3
"""
tests/check_dispatch.py  v4.3
v4.3  2026-09-24  OTV4TEST r128 — TWO STANDING REDS, BOTH THE CHECKER'S, NEITHER THE
      CODE'S. (1) "no dispatch-local name is used before it is assigned" flagged
      `_fire` (a NESTED `def`, main.py:3849) and `_adm_rules` (a LOCAL import,
      main.py:3758): the scan counted only `Name` stores as bindings, so a def or
      an import could never bind — it cried wolf on every run. AND IT NEVER
      CHECKED "BEFORE": ast.walk is breadth-first and the bound set grew in walk
      order, not line order. Now bindings of every kind (assignment, nested
      def/class, import, argument, loop/with/except/comprehension target, walrus)
      carry their LINE, and a load is flagged only if no binding of that name sits
      on an earlier line — what (3) below always claimed to do. Mutation-proven:
      a use moved above its assignment goes red. (2) The Runaway fixture predates
      r24's rule that the 50% must be ACCEPTED on the latch AND HELD NOW
      (runaway_plan.py:325, :353): its ORB double carried no `fifty_accepted` and
      no 1m frame, so the plan correctly held and the check read "does not fire".
      The fixture now supplies both; the pin is unchanged (fires, and VALID).
      Plus the r106 venv bootstrap (the lander runs CHECKs under system python3).
v4.2  2026-08-26  r146: the runaway fixture supplies a chain and the pin is that
      the signal is VALID (strike, premium, contract resolved) — it never was
      before r146; without a chain the strategy is starved, not fired.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Every v4 strategy is wired, in the right order, and its call site EXECUTES.

v4.0  2026-08-20  Built at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

WHY: IMPORT-CLEAN IS NOT RUNTIME-CLEAN, AND IT HAS FOOLED US TWICE.
  · 2026-08-18 - a `ctx` NameError inside `run_analysis` stopped every box
    trading. `import main` passed the entire time, because the name resolves at
    RUNTIME inside the function.
  · 2026-08-19 - `main.py` imported cleanly while calling
  · 2026-08-20 - `closes_beyond` consumed `_rc_bar` fourteen lines before it was
    assigned. Caught only by reading the line numbers.
**All three are the same defect: a name that is fine at parse time and absent at
call time.** WA 21 exists for this and an import check cannot satisfy it.

WHAT THIS CHECKS
  1. every v4 strategy is imported, instantiated and dispatched
  2. the dispatch ORDER is right - runaway before sweep before butterfly
  3. every name the dispatch block uses is BOUND EARLIER IN THE SAME FUNCTION
  4. each strategy's `generate_signal` actually RUNS against a synthetic ctx
     and returns without raising

⚠️ (3) IS THE ONE THAT CATCHES THE REAL BUG. It is a scope check, not a syntax
check: it asks whether the name exists at the point of use, which is precisely
what all three incidents above got wrong.
"""

import ast
import os
import sys
import glob as _glob                                             # r106 venv bootstrap
for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)

PROBLEMS = []
EXPECTED_ORDER = ["RunawayContinuation", "SweepCreditSpread", "GEXPinButterfly"]


def check(label, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + label
          + (f"  - {detail}" if detail and not cond else ""))
    if not cond:
        PROBLEMS.append(label)


def main(argv):
    print("DISPATCH CHECK")
    print("=" * 68)
    src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    tree = ast.parse(src)

    # ── 1. wired at all ────────────────────────────────────────────────────
    for cls, inst in (("RunawayContinuationStrategy", "_runaway_strategy"),
                      ("SweepCreditSpreadStrategy", "_sweep_cs_strategy"),
                      ("GEXPinButterflyStrategy", "_gex_bfly_strategy")):
        check(f"{cls} imported", f"import {cls}" in src)
        check(f"{inst} instantiated", f"{inst} = {cls}()" in src)
        check(f"{inst} dispatched", f"{inst}.generate_signal" in src)

    # ── 2. order ───────────────────────────────────────────────────────────
    pos = [(src.index(f'_safe_strategy("{n}"'), n) for n in EXPECTED_ORDER
           if f'_safe_strategy("{n}"' in src]
    check("dispatch order: runaway -> sweep -> butterfly",
          [n for _, n in sorted(pos)] == EXPECTED_ORDER,
          f"found {[n for _, n in sorted(pos)]}")
    orb = src.index('_safe_strategy("ORB"')
    check("ORB dispatches BEFORE the runaway - the runaway reads ORB's own state",
          orb < min(p for p, _ in pos))

    # ── 3. every name used is bound earlier in the same function ───────────
    fn = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "attempt_new_entry":
            fn = node
            break
    if fn is None:
        check("attempt_new_entry found", False)
    else:
        # ⚠️ MODULE-LEVEL `def`s AND ASSIGNMENTS ARE BOUND TOO. A first version
        # scanned only for assignments and flagged `_afternoon_debit_blocked`
        # and `_sigj` - both module-level FUNCTIONS - as used-before-assigned.
        # **A checker that cries wolf is worse than no checker**, and this one
        # would have trained the operator to skim its output on the first run.
        module_bound = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                module_bound.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        module_bound.add(t.id)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    module_bound.add((a.asname or a.name).split(".")[0])
            elif isinstance(node, (ast.Try, ast.If)):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Assign):
                        for t in sub.targets:
                            if isinstance(t, ast.Name):
                                module_bound.add(t.id)
                    elif isinstance(sub, (ast.Import, ast.ImportFrom)):
                        for a in sub.names:
                            module_bound.add((a.asname or a.name).split(".")[0])

        # r128 — BINDINGS OF EVERY KIND, BY LINE. A load is unbound if no binding
        # of that name sits at or before its line. Module-level names and the
        # function's own arguments are bound from the start.
        first_bind = {}
        def _bind(name, line):
            if name not in first_bind or line < first_bind[name]:
                first_bind[name] = line
        for a in fn.args.args + fn.args.kwonlyargs:
            _bind(a.arg, 0)
        for node in ast.walk(fn):
            if node is fn:
                continue
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                _bind(node.id, node.lineno)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                _bind(node.name, node.lineno)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    _bind((a.asname or a.name).split(".")[0], node.lineno)
            elif isinstance(node, ast.ExceptHandler) and node.name:
                _bind(node.name, node.lineno)
            elif isinstance(node, ast.arg):
                _bind(node.arg, node.lineno)     # lambda / nested-def parameters
        unbound = []
        for node in ast.walk(fn):
            if (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                    and node.id.startswith("_") and node.id not in module_bound):
                b = first_bind.get(node.id)
                if b is None or b > node.lineno:
                    unbound.append(f"{node.id}@{node.lineno}")
        unbound.sort(key=lambda x: int(x.split("@")[1]))
        check("no dispatch-local name is used before it is assigned",
              not unbound, f"{unbound[:5]}")

    # ── 4. the strategies actually RUN ─────────────────────────────────────
    try:
        from strategy.runaway_continuation import RunawayContinuationStrategy
        from strategy.sweep_credit_spread import SweepCreditSpreadStrategy
        from strategy.gex_pin_butterfly import GEXPinButterflyStrategy

        class _ORB:
            state = "OPEN_LONG"
            # ⚠️ `target_50pct` — the field the REAL ORBData declares. This
            # double carried `tp50`, a name that exists on nothing, and the
            # strategy read the same ghost — so this check was GREEN while the
            # gate it exercises refused every runaway on the fleet. A fixture
            # must match the real class, not the caller's assumption.
            orb_high, orb_low, target_50pct = 101.0, 100.0, 101.5
            invalidation_reason = "runaway"
            # r128 — r24's trigger: the 50 ACCEPTED on the engine's latch
            # (runaway_plan.py:325). Without it the plan HOLDS, correctly.
            fifty_accepted = True

        class _LM:
            recent_sweep = None

        # r146 — the runaway now resolves its own contract off the chain the
        # dispatcher passes (its signal was ALWAYS invalid before: strike 0,
        # premium 0, `target_delta` had no reader). So the fixture supplies a
        # chain, and the pin is that the signal is VALID, not merely non-None.
        class _C:
            def __init__(s, k, mark, delta, gamma=0.01):
                s.strike, s.mark, s.ask, s.bid = k, mark, mark + 0.02, mark - 0.02
                s.delta, s.gamma, s.theta = delta, gamma, -0.05
                s.expiry, s.option_type, s.symbol = "2026-08-26", "call", f"C{k}"
                s.open_interest = 100

        class _Chain:
            calls = [_C(102.0, 0.90, 0.40), _C(103.0, 0.45, 0.25), _C(104.0, 0.20, 0.12)]
            puts = []

        r0 = RunawayContinuationStrategy().generate_signal(
            orb=_ORB(), atr_pct=0.14, price_now=101.6, prev_close=101.55,
            now_et="10:15")
        check("RunawayContinuation without a chain is starved, not fired",
              r0 is None)
        import os as _os
        _os.environ["OT_RELAXED_ENTRY"] = "1"      # mute the R hurdle for the pin
        # r128 — and HELD NOW (runaway_plan.py:353): the last CLOSED 1m bar
        # beyond the 50 as well as the live price. Two bars, both beyond 101.5.
        import pandas as _pd
        _df1 = _pd.DataFrame({"open": [101.52, 101.55], "high": [101.58, 101.62],
                              "low": [101.51, 101.54], "close": [101.55, 101.60],
                              "volume": [1000.0, 1000.0]},
                             index=_pd.to_datetime(["2026-08-26 14:14",
                                                    "2026-08-26 14:15"], utc=True))
        r = RunawayContinuationStrategy().generate_signal(
            orb=_ORB(), atr_pct=0.14, price_now=101.6, prev_close=101.55,
            now_et="10:15", chain=_Chain(), df_1m=_df1)
        check("RunawayContinuation.generate_signal RUNS and fires", r is not None)
        check("RunawayContinuation signal is VALID (strike+premium+contract "
              "resolved — r146 P0)", r is not None and r.is_valid,
              f"strike={getattr(r, 'strike', None)} prem={getattr(r, 'entry_premium', None)}")

        s2 = SweepCreditSpreadStrategy().generate_signal(
            liq_map=_LM(), price_now=600.0, now_et="13:30", atr_pct=0.10)
        check("SweepCreditSpread.generate_signal RUNS (no sweep -> None)",
              s2 is None)

        b = GEXPinButterflyStrategy().generate_signal(
            gex=None, price_now=600.0, now_et="13:30", atm_iv=0.35)
        check("GEXPinButterfly.generate_signal RUNS and is PARKED", b is None)
    except Exception as e:                                     # noqa: BLE001
        check("strategies execute", False, f"{type(e).__name__}: {e}")

    print("=" * 68)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        return 1
    print("  dispatch is wired, ordered, in scope, and executes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
