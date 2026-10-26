#!/usr/bin/env python3
"""
tests/check_alert_dead_method.py  v5.0
v5.0  2026-10-25  (ALRT.1) — new. THE NO-OP CIRCUIT-BREAKER ALERT IS GONE AND NOTHING REACHES FOR IT.
      AlertManager.send_circuit_breaker_alert only logged "not sent to Telegram" and had zero callers (this tree and
      day_trader_pro, measured 2026-10-25); the catastrophic cap pages through risk/risk_manager.py's own _send. Dead
      code that reads as a live alert. Born red on ffe10bf at D1 and D2 (the method is defined there).

No grep: the class is imported and asked, and every tracked .py is PARSED, so a comment or this docstring naming the
method cannot satisfy or break the check — only code can.

  D1  notifications.alert_manager.AlertManager has no attribute send_circuit_breaker_alert
  D2  no tracked .py (this gate aside) defines, calls, or names it in code: no FunctionDef, Attribute, Name or string
      constant of that name in any AST
  D3  r67's scar: the module singleton survives the deletion - get_alert_manager() returns an AlertManager, twice the same
"""
import ast
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
NAME = "send_circuit_breaker_alert"
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


def _py_files():
    r = subprocess.run(["git", "-C", ROOT, "ls-files", "*.py"], capture_output=True, text=True)
    files = r.stdout.split() if r.returncode == 0 and r.stdout.strip() else []
    if not files:
        for d, dirs, fs in os.walk(ROOT):
            dirs[:] = [x for x in dirs if x not in (".git", "venv", "__pycache__")]
            files += [os.path.relpath(os.path.join(d, f), ROOT) for f in fs if f.endswith(".py")]
    me = os.path.relpath(os.path.abspath(__file__), ROOT)
    return [f for f in files if f != me]


def _code_refs(path):
    try:
        tree = ast.parse(open(os.path.join(ROOT, path), encoding="utf-8").read())
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    hits = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == NAME:
            hits.append("%s:%d def" % (path, n.lineno))
        elif isinstance(n, ast.Attribute) and n.attr == NAME:
            hits.append("%s:%d .attr" % (path, n.lineno))
        elif isinstance(n, ast.Name) and n.id == NAME:
            hits.append("%s:%d name" % (path, n.lineno))
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value == NAME:
            hits.append("%s:%d string" % (path, n.lineno))
    return hits


def main():
    try:
        import notifications.alert_manager as am
        has = hasattr(am.AlertManager, NAME)
        check("D1 AlertManager has no attribute %s" % NAME, not has, "still defined")
    except Exception as e:                                          # noqa: BLE001
        am = None
        check("D1 AlertManager has no attribute %s" % NAME, False, "import raised %s: %s" % (type(e).__name__, e))

    files = _py_files()
    refs = [h for f in files for h in _code_refs(f)]
    check("D2 no tracked .py defines, calls or names %s in code (%d files parsed)" % (NAME, len(files)),
          not refs and len(files) > 300, "%s" % refs[:5] if refs else "only %d files parsed" % len(files))

    try:
        a, b = am.get_alert_manager(), am.get_alert_manager()
        check("D3 get_alert_manager() still returns one AlertManager (r67's singleton)",
              isinstance(a, am.AlertManager) and a is b, "a=%r b=%r" % (a, b))
    except Exception as e:                                          # noqa: BLE001
        check("D3 get_alert_manager() still returns one AlertManager (r67's singleton)", False,
              "raised %s: %s" % (type(e).__name__, e))

    print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
