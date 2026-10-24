#!/usr/bin/env python3
"""tests/check_shutdown_cause.py — v1.0
WHY THE BOT WENT DOWN IS NAMED, AND A STALE STAMP NEVER SPEAKS FOR A LATER STOP.

v1.0  2026-09-20 — OTV4TEST r67 (BOX.9). `main.py`'s SIGTERM handler hardcoded
      `reason = "systemctl stop/restart"`, so the emergency channel printed ONE
      sentence for three different causes. From the operator's own Telegram:
      a fleet stop at 09/19 21:31 ET, the r66 bake at 22:49, and the MIDNIGHT
      BACKSTOP at 09/20 00:00 — identical text. He could only tell them apart
      by the clock, which is inference, not a report (§0.5).

  C0  THE GUARD, RUNS FIRST: every case is redirected to a scratch stamp and
      the REAL data/SHUTDOWN_CAUSE is never created (r13's class — a fixture
      that reaches live state; r26's check ran the real purge on live rows)
  C1  a freshly written stamp is read back VERBATIM
  C2  consume() deletes it — one shutdown, one stamp
  C3  a STALE stamp yields nothing (the guard that stops last week's halt
      speaking for tonight's hand stop)
  C4  absent / malformed / empty all yield nothing — it FAILS CLOSED
  C5  the SHELL writer in devtools.sh bake() is DRIVEN and parsed by the
      PYTHON reader (two writers of one format that are never compared drift)
  C6  the REAL midnight_halt stamps its own HALT_CAUSE, sudo stubbed
  C6b ...and exits NON-ZERO when the shutdown is refused (it used to discard
      the result and return 0, so a refused halt "Finished successfully")
  C7  label() returns the stamped cause, C7b the default when stale,
      C7c the default when absent
  C8  main.py's SIGTERM branch actually calls it

⚠️ C8 IS STRUCTURAL AND SAYS SO. The handler is a closure defined inside
`main()` and cannot be reached without running the bot, so the DECISION was
moved into `label()` where C7/C7b/C7c drive it for real (r43: a behaviour
reachable only through a 700-line dispatch stops being tested). C8 asserts only
the remaining one-line wiring, on the AST rather than on source text, because
a comment naming the call is not the call (§21).
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
import time

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def guard(name, fn, detail=lambda: ""):
    """Any escape becomes a RED LINE, never a traceback (r39: a checker that
    dies on AttributeError cannot say WHICH behaviour is absent)."""
    try:
        ok = bool(fn())
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"raised {type(exc).__name__}: {exc}")
        return False
    try:
        d = detail() if ok is not None else ""
    except Exception:                                           # noqa: BLE001
        d = ""
    check(name, ok, d)
    return ok


REAL = os.path.join(_root, "data", "SHUTDOWN_CAUSE")
_real_existed = os.path.exists(REAL)
TMP = tempfile.mkdtemp(prefix="sdc_")
os.environ["OT_SHUTDOWN_CAUSE"] = os.path.join(TMP, "SHUTDOWN_CAUSE")

# 🔴 THE IMPORT CANNOT BE ALLOWED TO KILL THE RUN. At the previous HEAD this
# module does not exist, and a checker that dies on ImportError reports NOTHING
# — it reads identically to a checker that is simply broken, so the born-red
# proof it exists to give is worthless. This repo has paid for that five times
# (r32, r37, r39, r41, r51) and r44's ledger already called it a pattern rather
# than a slip. An absent module now yields a RED LINE PER CHECK.
try:
    from utils import shutdown_cause as sc                      # noqa: E402
except Exception as exc:                                        # noqa: BLE001
    # ⚠️ THE MESSAGE IS CAPTURED AS A STRING HERE, NOT CLOSED OVER. Python
    # unbinds the `except` variable when the block ends, so a closure that
    # referenced it raised `NameError: _imp_exc is not defined` — the checker
    # went red for a reason unrelated to what it checks, which is r49's
    # "the diagnostic contradicting the diagnosis" and §0.5's whole subject.
    # Caught by reading this checker's OWN born-red output rather than by
    # assuming the hardening worked.
    _WHY = "utils/shutdown_cause.py absent or unimportable: %s: %s" % (
        type(exc).__name__, exc)

    class _Absent:                                              # noqa: D401
        def __getattr__(self, name):
            raise RuntimeError(_WHY)

    sc = _Absent()

# ── C0 — the guard, and it runs before anything writes ───────────────────────
# ⚠️ IT DOES NOT GO THROUGH `sc`, deliberately: the guard that decides whether
# it is safe to run must not itself depend on the thing under test.
guard("C0 the scratch stamp is in use and the real one is not this checker's",
      lambda: os.environ["OT_SHUTDOWN_CAUSE"].startswith(TMP),
      lambda: os.environ["OT_SHUTDOWN_CAUSE"])
if FAILED:
    print("\nREFUSING TO RUN — a case could reach the box's own sentinel.")
    sys.exit(1)


def _reset():
    try:
        os.unlink(sc.path())
    except Exception:                                           # noqa: BLE001
        pass


CAUSE = "midnight backstop — no drain"

def _c1():
    _reset(); sc.record(CAUSE); return sc.consume() == CAUSE


guard("C1 a fresh stamp reads back verbatim", _c1)


def _c2():
    _reset(); sc.record(CAUSE); sc.consume()
    return not os.path.exists(sc.path()) and sc.consume() is None


guard("C2 consume() deletes the stamp — one shutdown, one stamp", _c2)


def _c3():
    _reset(); sc.record(CAUSE)
    return sc.consume(now=time.time() + sc.MAX_AGE_S + 5) is None


guard("C3 a stale stamp yields nothing", _c3)


def _c4():
    _reset()
    absent = sc.consume() is None
    open(sc.path(), "w").write("not-a-stamp\n")
    malformed = sc.consume() is None
    open(sc.path(), "w").write("")
    empty = sc.consume() is None
    return absent and malformed and empty


guard("C4 absent, malformed and empty all fail closed", _c4)

# ── C5 — DRIVE THE SHELL WRITER, do not paraphrase it ────────────────────────
# The line is lifted from devtools.sh bake() by reading the file, so a change
# to the shell that breaks the format fails HERE rather than on the next bake.


def _shell_writer():
    _reset()
    src = open(os.path.join(_root, "devtools.sh"), encoding="utf-8").read()
    line = [ln for ln in src.splitlines()
            if "SHUTDOWN_CAUSE" in ln and "printf" in ln]
    if not line:
        return False
    cmd = line[0].strip().replace('"$REPO/data/SHUTDOWN_CAUSE"', '"$OT_SHUTDOWN_CAUSE"')
    cmd = cmd.replace('mkdir -p "$REPO/data" && ', "")
    subprocess.run(["bash", "-c", cmd], check=False,
                   env={**os.environ, "OT_SHUTDOWN_CAUSE": sc.path()})
    got = sc.consume()
    return bool(got) and "bake" in got.lower()


guard("C5 the shell writer in bake() is read by the python parser", _shell_writer)

# ── C6 — the real halt, with sudo stubbed ────────────────────────────────────
def _run_halt(sudo_rc):
    d = tempfile.mkdtemp(prefix="halt_")
    stub = os.path.join(d, "sudo")
    with open(stub, "w") as fh:
        fh.write("#!/bin/sh\necho 'stub sudo' >&2\nexit %d\n" % sudo_rc)
    os.chmod(stub, 0o755)
    stamp = os.path.join(d, "SHUTDOWN_CAUSE")
    env = {**os.environ, "PATH": d + os.pathsep + os.environ.get("PATH", ""),
           "OT_SHUTDOWN_CAUSE": stamp,
           "OT_NO_MIDNIGHT_HALT": os.path.join(d, "definitely-absent")}
    r = subprocess.run([sys.executable,
                        os.path.join(_root, "warehouse", "midnight_halt.py")],
                       capture_output=True, env=env, cwd=_root)
    txt = ""
    if os.path.exists(stamp):
        txt = open(stamp, encoding="utf-8").read()
    return r.returncode, txt


_C6 = {}


def _c6():
    rc, stamp = _run_halt(0)
    _C6["ok"] = (rc, stamp)
    return "backstop" in stamp and rc == 0


guard("C6 the real midnight_halt stamps its own cause", _c6,
      lambda: "rc=%s stamp=%r" % (_C6.get("ok", ("?", ""))[0],
                                  _C6.get("ok", ("?", ""))[1].strip()))


def _c6b():
    rc, _ = _run_halt(1)
    _C6["bad"] = rc
    return rc != 0


guard("C6b a refused shutdown exits NON-ZERO instead of 'Finished successfully'",
      _c6b, lambda: "rc=%s" % _C6.get("bad"))

# ── C7 — the decision itself, driven ─────────────────────────────────────────
def _c7():
    _reset(); sc.record(CAUSE)
    return sc.label("systemctl stop/restart") == CAUSE


guard("C7 label() returns the stamped cause", _c7)


def _c7b():
    _reset(); sc.record(CAUSE)
    return sc.label("systemctl stop/restart",
                    now=time.time() + sc.MAX_AGE_S + 5) == "systemctl stop/restart"


guard("C7b label() returns the DEFAULT when the stamp is stale", _c7b)


def _c7c():
    _reset()
    return sc.label("systemctl stop/restart") == "systemctl stop/restart"


guard("C7c label() returns the DEFAULT when there is no stamp", _c7c)


# ── C8 — the one-line wiring in main.py, on the AST ──────────────────────────
def _main_wired():
    tree = ast.parse(open(os.path.join(_root, "main.py"), encoding="utf-8").read())
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == "_handle_shutdown"):
            continue
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                    and sub.func.id == "label"):
                return True
    return False


guard("C8 main.py's shutdown handler calls label()", _main_wired)

# ── the real sentinel was never touched ──────────────────────────────────────
guard("C0b the box's own data/SHUTDOWN_CAUSE is untouched",
      lambda: os.path.exists(REAL) == _real_existed,
      lambda: f"existed={_real_existed} now={os.path.exists(REAL)}")

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
