"""
utils/venv_guard.py  v5.0
v5.0  2026-11-08  OTV5 r84 (VENV.1) — new. A SCRIPT RUN WITH THE WRONG INTERPRETER SAYS SO AND STOPS, INSTEAD OF A TRACEBACK.
      The Saturday brief 11-07 §5 item 9: control's /usr/bin/python3 is 3.14 with no pandas or tastytrade, and 16 OTV5
      scripts with a `#!/usr/bin/env python3` shebang imported one of them at module level, so a bare run died in a
      ModuleNotFoundError traceback. Each now calls require_venv(...) before its first third-party import.
      Stdlib only: this module is imported before any third-party package is known to be importable.

require_venv(*modules) returns None when every named module is importable by the running interpreter, so under the
bot's venv nothing changes. Otherwise it prints ONE line to stderr and exits 2:
    ModuleNotFoundError: No module named 'pandas' - tests/x.py needs a venv that has pandas, not /usr/bin/python3 (3.14.0); run it with: <path>
The line keeps the "ModuleNotFoundError: No module named" text so dtp checker_sweep still files the red as [env].
It never re-executes under another interpreter: a check passes or fails under the interpreter its caller chose.
"""
import importlib.util
import os
import sys

# Hosts this repo runs on, in the order a reader should try them: a venv inside the checkout, the box's bot venv, and
# control's tooling venv (the one dtp's checker sweep runs OTV5's checks with).
_CANDIDATES = (
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "bin", "python"),
    os.path.expanduser("~/options-trader/venv/bin/python"),
    os.path.expanduser("~/day_trader_pro/venv/bin/python"),
)


def _missing(modules):
    out = []
    for m in modules:
        try:
            if importlib.util.find_spec(m) is None:
                out.append(m)
        except (ImportError, ValueError):
            out.append(m)
    return out


def require_venv(*modules):
    """Exit 2 with one line naming the missing modules and a venv to use, unless all of `modules` import here."""
    missing = _missing(modules)
    if not missing:
        return None
    script = os.path.relpath(os.path.abspath(sys.argv[0])) if sys.argv and sys.argv[0] else "this script"
    # A venv's bin/python is a symlink to the base interpreter, so compare venv DIRECTORIES (sys.prefix), not binaries.
    here = os.path.realpath(sys.prefix)
    seen, cands = set(), []
    for c in _CANDIDATES:
        venv = os.path.realpath(os.path.dirname(os.path.dirname(c)))
        if os.path.exists(c) and venv not in seen and venv != here:
            seen.add(venv)
            cands.append(c)
    hint = ("run it with: " + " or ".join(cands)) if cands else "no known venv on this host has been found"
    ver = ".".join(str(x) for x in sys.version_info[:3])
    sys.stderr.write(
        f"ModuleNotFoundError: No module named {missing[0]!r} - {script} needs a venv that has "
        f"{', '.join(missing)}, not {sys.executable} ({ver}); {hint}\n")
    sys.stderr.flush()
    raise SystemExit(2)
