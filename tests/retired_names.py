"""
tests/retired_names.py  v5.1
v5.1  2026-11-08  OTV5 r88 (RETIRE.3) — REMOVED adds the three TCS shadow modules (strategy.trend_credit_spread, strategy.tcs_plan,
      execution.shadow_book).
v5.0  2026-11-08  OTV5 r76 (RETIRE.1) — ONE ANSWER TO "IS THIS MODULE GONE FROM THE LIVE CODE?" for the checks re-pointed
      when the ORB trade, VOLT, the ATP fly, ORCS and the sweep were removed. A module is RETIRED when no live file (outside
      tests/ and docs/, and other than the module itself) imports it. That is the property that matters on a box, and it is
      true both before the lander's DEL step runs (the lander executes the CHECKs while the payload's deleted files are
      still on disk) and after it - a file-absence test would fail every land that removes a module.
      Not a check itself (no check_ prefix, so the sweep does not run it).
"""
import ast
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# the modules r76 deletes: until the lander's DEL step they are still on disk, and one may import another
# (orcs -> orcs_plan, volt_strategy -> volt_plan), so none of them counts as a live importer.
REMOVED = ("strategy.orb_strategy", "strategy.volt_strategy", "strategy.volt_plan", "strategy.atp_butterfly",
           "strategy.atp_butterfly_plan", "strategy.orcs", "strategy.orcs_plan", "strategy.sweep_plan",
           "execution.handoff",
           # r88 (RETIRE.3): the TCS shadow
           "strategy.trend_credit_spread", "strategy.tcs_plan", "execution.shadow_book")
_REMOVED_FILES = {os.path.join(ROOT, *m.split(".")) + ".py" for m in REMOVED}


def _imports(path):
    try:
        tree = ast.parse(open(path, encoding="utf-8").read(), path)
    except (SyntaxError, UnicodeDecodeError, OSError):
        return set()
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            out.add(n.module)
            out.update(f"{n.module}.{a.name}" for a in n.names)
    return out


def importers(module: str) -> list:
    """Every live file that imports `module` (dotted), excluding the module's own file."""
    own = os.path.join(ROOT, *module.split(".")) + ".py"
    found = []
    for dp, dn, fn in os.walk(ROOT):
        rel = os.path.relpath(dp, ROOT)
        top = rel.split(os.sep)[0]
        if top in ("tests", "docs", ".git", "venv") or "__pycache__" in dp:
            continue
        for f in fn:
            if not f.endswith(".py"):
                continue
            p = os.path.join(dp, f)
            if os.path.abspath(p) == os.path.abspath(own) or os.path.abspath(p) in _REMOVED_FILES:
                continue
            if module in _imports(p):
                found.append(os.path.relpath(p, ROOT))
    return sorted(found)


def retired(*modules) -> bool:
    """True when no live file imports any of `modules`."""
    return all(not importers(m) for m in modules)
