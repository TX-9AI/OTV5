#!/usr/bin/env python3
"""
tests/check_legacy_gone.py  v1.5
LVL.15 STEP 5 — THE OLD LEVEL CODE LEAVES, ONE MODULE AT A TIME, AND NOTHING
STILL IMPORTS WHAT LEFT.

v1.5  2026-09-23  OTV4TEST r126 — derived/level_map.py and analysis/liquidity_mapper.py, the
      last of LVL.15 step 5, with the four legacy checkers deleted beside them.
v1.4  2026-09-23  OTV4TEST r125 — shadow/ (the package and all five modules) and
      analysis/level_grade.py (orphaned by r123). G1 now ignores importers
      INSIDE a deleted package: its own files are deleted with it, but the
      CHECKs run before the lander's DEL (r302), so they are still on disk.
v1.3  2026-09-23  OTV4TEST r124 — G3: the live board and main.py no longer use
      derived/level_map (the board's zoning moved into derived/levels; main.py's
      level_tape read is gone). level_map joins LEGACY in r125 with the legacy path.
v1.2  2026-09-23  OTV4TEST r123 — G2: main.py no longer runs the old liquidity mapper.
      The module cannot join LEGACY yet (derived/level_map still imports it
      until r124), so this pins the ONE live caller that r123 removes.
v1.1  2026-09-23  OTV4TEST r122 — analysis/liquidity_ledger.py, fed every tick from
      main.py and read back by nothing on this box.
v1.0  2026-09-23  OTV4TEST r121 — analysis/pitchfork_lifecycle.py, the first.

The operator approved step 5 on 2026-09-23 ("Yes, for sure"): delete the code
the rebuilt levels replaced. Each delivery appends its module to LEGACY below.

⚠️ WHAT THIS CAN AND CANNOT ASSERT. The lander applies `DEL` AFTER it runs the
CHECKs (r302's lesson, tools/land.sh), so a gate that asserted "the file is
absent" would fail the very delivery that removes it. What is true BEFORE the
delete, and what makes the delete safe, is that NO OTHER FILE IMPORTS IT —
statically, lazily inside a function, or through importlib/__import__ with a
literal name. That is asserted here. The absence itself is verified after the
land, by hand, and recorded in the ledger.

  G0 CONTROL — the scanner FINDS a live import (execution/exit_engine.py
     imports derived.level_rules), so an empty result below means something
  G1 nothing in the tree imports any module in LEGACY
  G3 LevelEngine.board() and main.py import nothing from derived.level_map (r124)
  G2 main.py does not import analysis.liquidity_mapper (r123 — it ran every
     tick and fed nothing that trades); r124 moves the module into LEGACY
"""
from __future__ import annotations

import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# module -> the revision that deleted it
LEGACY = {
    "analysis.pitchfork_lifecycle": "r121",
    "analysis.liquidity_ledger": "r122",
    "analysis.level_grade": "r125",
    "shadow": "r125",
    "shadow.observer": "r125",
    "shadow.primitives": "r125",
    "shadow.registry": "r125",
    "shadow.scorers": "r125",
    "shadow.trading_day": "r125",
    "derived.level_map": "r126",
    "analysis.liquidity_mapper": "r126",
}

# Files the SAME delivery deletes (by DEL) that import a LEGACY module. The CHECKs
# run before the lander's DEL (r302), so they are still on disk when this runs;
# listing them here is a statement, not a wildcard.
DELETED_WITH = {
    "tests/check_shadow_velocity.py": "r125",
    "tests/check_level_map.py": "r126",
    "tests/check_level_rejection.py": "r126",
    "tests/check_sweep_excursion.py": "r126",
    "tests/check_pool_geometry.py": "r126",
}

FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def _files():
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in ("venv", ".git", "__pycache__", "node_modules")]
        for fn in fns:
            if fn.endswith(".py"):
                yield os.path.join(dp, fn)


def imports_of(path):
    """Every module name this file imports: `import a.b`, `from a import b`
    (yields a and a.b), and importlib.import_module / __import__ with a literal."""
    try:
        tree = ast.parse(open(path, encoding="utf-8").read(), path)
    except (SyntaxError, UnicodeDecodeError, ValueError):
        return set()
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            out.add(n.module)
            out.update(f"{n.module}.{a.name}" for a in n.names)
        elif isinstance(n, ast.Call) and n.args and isinstance(n.args[0], ast.Constant) \
                and isinstance(n.args[0].value, str):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if name in ("import_module", "__import__"):
                out.add(n.args[0].value)
    return out


def main():
    found = {}
    for p in _files():
        rel = os.path.relpath(p, ROOT)
        for m in imports_of(p):
            found.setdefault(m, set()).add(rel)
    ctl = found.get("derived.level_rules", set())
    check("G0 control: the scanner finds exit_engine importing derived.level_rules",
          "execution/exit_engine.py" in ctl, f"{len(ctl)} importer(s)")
    bad = []
    for mod in LEGACY:
        own = mod.replace(".", "/") + ".py"
        pkg = mod.split(".")[0] + "/"                  # a deleted package's own files
        users = sorted(u for u in found.get(mod, set())
                       if u != own and u not in DELETED_WITH
                       and u[:-3].replace("/", ".") not in LEGACY   # itself a deleted module
                       and not (pkg.rstrip("/") in LEGACY and u.startswith(pkg)))
        bad += [f"{u} -> {mod}" for u in users]
    check("G1 nothing imports a deleted legacy module", not bad,
          "; ".join(bad) if bad else f"{len(LEGACY)} module(s): {', '.join(LEGACY)}")
    main_imports = imports_of(os.path.join(ROOT, "main.py"))
    hit = sorted(m for m in main_imports if m.startswith("analysis.liquidity_mapper"))
    check("G2 main.py no longer imports the old liquidity mapper", not hit, ", ".join(hit) or "none")
    # G3 — the board's own function body, and main.py, import nothing from level_map
    lv_src = open(os.path.join(ROOT, "derived", "levels.py"), encoding="utf-8").read()
    board_fn = next((n for n in ast.walk(ast.parse(lv_src)) if isinstance(n, ast.FunctionDef)
                     and n.name == "board"), None)
    in_board = set()
    for n in ast.walk(board_fn) if board_fn is not None else ():
        if isinstance(n, ast.ImportFrom) and n.module:
            in_board.update([n.module] + [f"{n.module}.{a.name}" for a in n.names])
        elif isinstance(n, ast.Import):
            in_board.update(a.name for a in n.names)
    hit3 = sorted(m for m in (in_board | main_imports) if "level_map" in m)
    check("G3 board() and main.py no longer use derived.level_map",
          board_fn is not None and not hit3, ", ".join(hit3) or ("none" if board_fn else "board() not found"))
    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
