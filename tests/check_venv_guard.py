#!/usr/bin/env python3
"""
tests/check_venv_guard.py  v5.0
v5.0  2026-11-08  OTV5 r84 (VENV.1) — new. NO PYTHON3-SHEBANG SCRIPT IMPORTS A THIRD-PARTY PACKAGE UNGUARDED.
      The Saturday brief 11-07 §5 item 9: control's /usr/bin/python3 is 3.14 with no pandas or tastytrade, and 16
      scripts with `#!/usr/bin/env python3` imported one at module level, so a bare run died in a traceback. Each now
      calls utils.venv_guard.require_venv(...) before its first third-party import; this gate keeps it that way.
      Stdlib only, so it runs under any interpreter.

  V1  every .py in the tree whose first line is a python3 shebang: each MODULE-LEVEL `import X` / `from X import`
      of a third-party package (not stdlib, not a module or package of this repo) comes after a module-level
      require_venv(...) call that names X. Imports inside try/except, functions or `if` blocks are not module-level
  V2  the floor: at least 16 such guarded scripts are found (an empty or broken scan cannot pass)
  V3  utils/venv_guard.py and utils/__init__.py import the stdlib only (the guard runs before anything else loads)
  V4  require_venv with every module importable returns None and prints nothing
  V5  require_venv with a missing module exits 2 with ONE stderr line that keeps the text
      "ModuleNotFoundError: No module named '<mod>'" (dtp checker_sweep files that red as [env]) and names the script
  V6  the venv hint never offers the venv already running, and does offer an existing other one (compared by
      directory: a venv's bin/python is a symlink to the base interpreter)
  V7  the V1 detector itself: an unguarded import, a guard placed after the import and a guard that omits the module
      are each caught; a guarded script, a try/except import and a repo-local import are each passed

Run:  python3 tests/check_venv_guard.py      (exit 0 = all pass)
"""
import ast
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
STD = set(sys.stdlib_module_names) | {"__future__"}
SKIP_DIRS = {".git", "venv", "__pycache__", "node_modules"}
FLOOR = 16

FAIL = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(label.split()[0])


def local_names(root):
    names = set()
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        names |= {f[:-3] for f in fn if f.endswith(".py")} | set(dn)
    return names


def is_py3_shebang(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            first = fh.readline()
    except OSError:
        return False
    return first.startswith("#!") and "python3" in first


def problems(src, local):
    """[(lineno, module, why)] for module-level third-party imports not preceded by a require_venv naming them."""
    tree = ast.parse(src)
    guarded, out, third = set(), [], 0
    for node in tree.body:
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and getattr(node.value.func, "id", getattr(node.value.func, "attr", None)) == "require_venv"):
            guarded |= {a.value for a in node.value.args if isinstance(a, ast.Constant) and isinstance(a.value, str)}
            continue
        mods = []
        if isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods = [node.module]
        for m in mods:
            top = m.split(".")[0]
            if top in STD or top in local:
                continue
            third += 1
            if top not in guarded:
                out.append((node.lineno, top, "no require_venv naming it before this line"))
    return out, third


def scan(root):
    local = local_names(root)
    bad, guarded_scripts = {}, []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in sorted(fn):
            p = os.path.join(dp, f)
            if not f.endswith(".py") or not is_py3_shebang(p):
                continue
            with open(p, encoding="utf-8") as fh:
                src = fh.read()
            probs, third = problems(src, local)
            rel = os.path.relpath(p, root)
            if probs:
                bad[rel] = probs
            elif third:
                guarded_scripts.append(rel)
    return bad, guarded_scripts


print("V1-V2  the tree")
bad, ok = scan(ROOT)
check("V1 every python3-shebang script guards its module-level third-party imports", not bad,
      "; ".join(f"{k}:{v[0][0]} {v[0][1]}" for k, v in sorted(bad.items())[:6]))
check(f"V2 at least {FLOOR} guarded scripts found", len(ok) >= FLOOR, f"{len(ok)}")

print("V3  the guard loads nothing but the stdlib")
for rel in ("utils/venv_guard.py", "utils/__init__.py"):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    tops = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            tops |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            tops.add(node.module.split(".")[0])
    check(f"V3 {rel} imports stdlib only", tops <= STD, ",".join(sorted(tops - STD)))

print("V4-V6  require_venv itself")
_S = tempfile.mkdtemp(prefix="check_venv_guard_")


def run_guard(code):
    script = os.path.join(_S, "probe_script.py")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(f"import sys\nsys.path.insert(0, {ROOT!r})\n{code}\n")
    r = subprocess.run([sys.executable, script], capture_output=True, text=True, timeout=60, cwd=_S)
    return r.returncode, r.stdout, r.stderr


rc, so, se = run_guard("from utils.venv_guard import require_venv\nprint(repr(require_venv('json', 'os')))")
check("V4 every module importable: returns None, prints nothing else", rc == 0 and so.strip() == "None" and not se,
      f"rc={rc} out={so.strip()!r} err={se.strip()[:80]!r}")

rc, so, se = run_guard("from utils.venv_guard import require_venv\nrequire_venv('json', 'no_such_mod_vg1')\n"
                       "print('REACHED')")
lines = [ln for ln in se.splitlines() if ln.strip()]
check("V5 a missing module: exit 2, one stderr line, nothing after the call runs",
      rc == 2 and len(lines) == 1 and "REACHED" not in so, f"rc={rc} lines={len(lines)}")
check("V5 the line keeps checker_sweep's [env] text and names the script",
      bool(lines) and "ModuleNotFoundError: No module named 'no_such_mod_vg1'" in lines[0]
      and "probe_script.py" in lines[0], lines[0][:120] if lines else "")

fake_other = os.path.join(_S, "other_venv")
os.makedirs(os.path.join(fake_other, "bin"))
os.symlink(sys.executable, os.path.join(fake_other, "bin", "python"))
here_py = os.path.join(sys.prefix, "bin", "python")
rc, so, se = run_guard(
    "import utils.venv_guard as G\n"
    f"G._CANDIDATES = ({here_py!r}, {os.path.join(fake_other, 'bin', 'python')!r})\n"
    "G.require_venv('no_such_mod_vg2')")
check("V6 the hint offers the other venv", os.path.join(fake_other, "bin", "python") in se, se.strip()[-90:])
check("V6 the hint never offers the venv already running", here_py not in se.split("run it with:")[-1]
      if "run it with:" in se else True, se.strip()[-90:])

print("V7  the detector")
local = local_names(ROOT)
CASES = {
    "unguarded": ("import os\nimport pandas as pd\n", True),
    "guard after the import": ("import pandas\nfrom utils.venv_guard import require_venv\nrequire_venv('pandas')\n",
                               True),
    "guard omits the module": ("from utils.venv_guard import require_venv\nrequire_venv('pandas')\n"
                               "from tastytrade import X\n", True),
    "guarded": ("from utils.venv_guard import require_venv\nrequire_venv('pandas', 'tastytrade')\nimport pandas\n"
                "from tastytrade.dxfeed import Quote\n", False),
    "try/except import": ("try:\n    import pandas\nexcept ImportError:\n    pandas = None\n", False),
    "repo-local import": ("import config\nfrom execution import exit_engine\n", False),
}
for name, (src, should_flag) in CASES.items():
    probs, _ = problems(src, local)
    check(f"V7 {name}: {'caught' if should_flag else 'passed'}", bool(probs) == should_flag, str(probs[:1]))

print()
if FAIL:
    print(f"FAIL ({len(FAIL)}): {' '.join(FAIL)}")
    sys.exit(1)
print("ALL PASS")
