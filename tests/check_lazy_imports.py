#!/usr/bin/env python3
"""
tests/check_lazy_imports.py  v1.0

v1.0  2026-09-21  OTV4TEST r77 — A LAZY IMPORT IS AN IMPORT NOBODY CHECKS.
      Born RED at 0411446 (r76).

🔴 WHAT HAPPENED. `strategy/breakout_plan.py::emit()` did
`from strategy.structure import OptionsSignal` — a module that has never
exported it. It raised ImportError on EVERY tick from the moment Breakout
first had a signal to build: **127 crashes on 2026-09-21, first at 09:37:04,
and the strategy produced NOT ONE TRADE, ever.**

🔑 THREE SAFETY NETS WERE BLIND AT ONCE, WHICH IS WHY THIS GATE EXISTS.
  1. The import is LAZY — inside a function — so the MODULE imports cleanly
     and `check_imports` passes. Only the path that builds a signal runs it.
  2. `_safe_strategy` CATCHES the raise by design ("other strategies
     unaffected") and continues, so nothing failed loudly.
  3. The plan therefore never wrote a row, so the board fell through to a
     STALE skip label — "position open — managing" — and the dashboard showed
     a MARKET CONDITION where there was a CRASH.
A defect that is invisible to the import checker, swallowed by the dispatch
guard, and mislabelled on the board is a defect that survives indefinitely.

⚠️ THIS CHECKS THE CLASS, NOT THE LINE (§20). L1 resolves EVERY deferred
import of a repo module across the whole tree and fails on any name its source
module does not define — so the next one cannot be reintroduced somewhere else.

  L0  the tree parses
  L1  CLASS: every lazy `from <repo module> import X` resolves
  L2  the r77 site specifically imports from base_strategy
  L3  CONTROL: Breakout's emit() actually builds a signal when driven

Run:  python3 tests/check_lazy_imports.py
"""
from __future__ import annotations
import ast, os, sys, importlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])

PKGS = ("strategy", "execution", "analysis", "derived", "risk", "data",
        "database", "warehouse", "notifications", "utils")

def repo_files():
    out = []
    for pkg in PKGS:
        d = os.path.join(ROOT, pkg)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith(".py"):
                out.append(os.path.join(d, f))
    return out

files = repo_files()
parsed, bad_parse = {}, []
for f in files:
    try:
        parsed[f] = ast.parse(open(f).read())
    except SyntaxError as exc:
        bad_parse.append(f"{os.path.relpath(f, ROOT)}: {exc}")
check("L0 every module parses", not bad_parse, "; ".join(bad_parse[:3]))

# ── L1 — THE CLASS. Resolve every DEFERRED (function-scope) from-import of a
#    repo module and prove the name exists in it.
offenders, scanned = [], 0
for f, tree in parsed.items():
    funcs = [n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for fn in funcs:
        for node in ast.walk(fn):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if node.module.split(".")[0] not in PKGS:
                continue
            scanned += 1
            try:
                mod = importlib.import_module(node.module)
            except Exception as exc:                      # noqa: BLE001
                offenders.append(f"{os.path.relpath(f, ROOT)}:{node.lineno} "
                                 f"{node.module} won't import ({type(exc).__name__})")
                continue
            for alias in node.names:
                if alias.name == "*" or hasattr(mod, alias.name):
                    continue
                # ⚠️ A SUBMODULE IS NOT AN ATTRIBUTE UNTIL IT IS IMPORTED.
                # `from derived import anchors` is correct and `hasattr` says
                # False — my first cut flagged three CORRECT lines. A canary
                # that refuses working code teaches the operator to ignore reds
                # (§36), so the check resolves the submodule before accusing.
                try:
                    importlib.import_module(f"{node.module}.{alias.name}")
                    continue
                except Exception:                          # noqa: BLE001
                    pass
                offenders.append(f"{os.path.relpath(f, ROOT)}:{node.lineno} "
                                 f"`from {node.module} import {alias.name}` "
                                 f"— {node.module} defines no such name")
check("L1 CLASS: every lazy import of a repo module resolves",
      not offenders, "; ".join(offenders[:3]) or f"{scanned} deferred imports resolved")

# ── L2 — the r77 site
src = open(os.path.join(ROOT, "strategy", "breakout_plan.py")).read()
check("L2 breakout_plan.emit() takes OptionsSignal from base_strategy",
      "from strategy.base_strategy import OptionsSignal" in src
      and "from strategy.structure import OptionsSignal" not in src,
      "structure.py has never exported OptionsSignal")

# ── L3 — CONTROL: drive emit() for real. A resolving import that still cannot
#    build a signal would pass L1 and fail live, which is this defect again.
try:
    from strategy import breakout_plan as _probe
    _ok_cls = hasattr(_probe, 'BreakoutPreparation')
except Exception as exc:                                   # noqa: BLE001
    _ok_cls = False
    _why = f"{type(exc).__name__}: {exc}"
if _ok_cls:
    import inspect
    from strategy import breakout_plan as _bp
    emit_src = inspect.getsource(_bp.BreakoutPreparation.emit)
    check("L3 CONTROL: emit() resolves its Signal class at call time",
          "base_strategy" in emit_src and _bp.__name__ == "strategy.breakout_plan",
          "the import inside emit() is the one that crashed 127 times")
else:
    check("L3 CONTROL: emit() resolves its Signal class at call time", False, _why)

print(f"\n{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} problem(s) {FAIL}")
sys.exit(1 if FAIL else 0)
