#!/usr/bin/env python3
"""
tests/check_signal_kwargs.py  v1.0

r100 — A CONSTRUCTOR KWARG THAT IS NOT A FIELD IS A STRATEGY THAT NEVER FIRES.

Born RED at ea6d773 (r99) on K1, with THREE live offenders — every one of them
a credit-spread trigger that could not produce a signal at all:

    strategy/trend_credit_spread.py     OptionsSignal(ms="")            -> TypeError
    strategy/daily_fork_credit_spread.py OptionsSignal(is_iron_condor=) -> TypeError
    strategy/iron_condor_strategy.py     OptionsSignal(is_iron_condor=) -> TypeError

⚠️ THIS IS A CLASS, NOT THREE BUGS. r65 renamed the retired label kwarg at call
sites without checking the target field existed; the same rename broke
`main.py`'s `manage_open_position(ms=None)` (r99, P0: every tick with an open
position raised into the loop catch-all). `is_iron_condor` is worse than a
typo — it IS a real read/write alias, but only as an ATTRIBUTE. In a dataclass
constructor a property is not a parameter, so code that looks correct against
the docstring raises.

⚠️ AND EVERY ONE FAILED SILENTLY. `_safe_strategy` catches the TypeError and
logs it as an ordinary strategy decline, so the fleet reported "no signal" for
months while the truth was "this code cannot run". 160 such lines on NFLX on
2026-08-24 read exactly like a strategy choosing not to trade.

K1 checks every keyword at every construction of every dataclass defined in this
tree, against the real field list — not a hardcoded list of known offenders,
which would have to be updated by the person who just introduced the next one.

Plain script with an exit code, deliberately not pytest (WORKING_AGREEMENT 36).

Run:  python3 tests/check_signal_kwargs.py
"""
from __future__ import annotations
import ast, dataclasses, importlib, os, sys, glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)

SKIP_DIRS = ("tests/", "tools/", "derived/scratch")

# ── 1. every dataclass defined in the tree, by class name -> field names ──────
fields_by_name: dict = {}
defined_in: dict = {}
for path in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
    rel = os.path.relpath(path, ROOT)
    if rel.startswith(SKIP_DIRS) or rel.startswith("."):
        continue
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except Exception:
        continue
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and any(
                (getattr(d, "id", "") or getattr(getattr(d, "func", None), "id", ""))
                == "dataclass" for d in node.decorator_list):
            mod = rel[:-3].replace(os.sep, ".")
            try:
                cls = getattr(importlib.import_module(mod), node.name)
                fields_by_name[node.name] = {f.name for f in dataclasses.fields(cls)}
                defined_in[node.name] = rel
            except Exception as e:                                 # noqa: BLE001
                print(f"  ..    {node.name} ({rel}) not importable here: "
                      f"{type(e).__name__} — skipped")

check("K0 dataclasses discovered and imported", len(fields_by_name) >= 3,
      f"{len(fields_by_name)} classes")

# ── 2. every construction of one of them, checked against the real fields ────
bad: list = []
sites = 0
for path in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
    rel = os.path.relpath(path, ROOT)
    if rel.startswith(SKIP_DIRS) or rel.startswith("."):
        continue
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except Exception:
        continue
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if name not in fields_by_name:
            continue
        sites += 1
        for kw in node.keywords:
            if kw.arg is not None and kw.arg not in fields_by_name[name]:
                bad.append(f"{rel}:{node.lineno} {name}({kw.arg}=...) — "
                           f"not a field of {name} ({defined_in[name]})")

for b in bad:
    print(f"     {b}")
check("K1 no construction passes a kwarg that is not a field", not bad,
      f"{len(bad)} bad kwarg(s) across {sites} construction site(s)")

# ── 3. the three known offenders, constructed for real ──────────────────────
try:
    from strategy.base_strategy import OptionsSignal
    for kw in ({"ms": ""}, {"is_iron_condor": True}):
        try:
            OptionsSignal(**kw)
            check(f"K2 OptionsSignal({list(kw)[0]}=...) raises", False,
                  "it did NOT raise — the field list changed, update this check")
        except TypeError:
            check(f"K2 OptionsSignal({list(kw)[0]}=...) still raises TypeError",
                  True, "so K1 is testing something real")
    s = OptionsSignal()
    s.is_iron_condor = True
    check("K3 is_iron_condor works as an ATTRIBUTE (the alias is intact)",
          s.is_credit_vertical is True)
except Exception as e:                                             # noqa: BLE001
    check("K2/K3 OptionsSignal probes", False, f"{type(e).__name__}: {e}")

print(f"\n{'PASS' if not FAILURES else 'FAIL'}: {len(FAILURES)} problem(s) {FAILURES}")
sys.exit(1 if FAILURES else 0)
