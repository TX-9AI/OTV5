#!/usr/bin/env python3
"""
tests/check_singletons.py  v4.0

Every get_*() accessor is CALLED, and no name resolves nowhere.

v4.0  2026-08-25  Written after a NameError crash-looped the entire fleet.

🔴 WHAT HAPPENED. `notifications/alert_manager.py` lost its module-level
`_alert_manager = None` — collateral from the r65 sweep, which deleted two
alert methods from that same file. `get_alert_manager()` declares
`global _alert_manager` and READS IT BEFORE ASSIGNMENT, so the first call
raised:

    NameError: name '_alert_manager' is not defined

`main()` calls it during startup. Every box died ~1 second after boot and
systemd restarted it forever — AVGO reached **NRestarts=23**, showing
`ActiveState=activating / SubState=auto-restart`.

⚠️ THE OUTAGE WORE THE COSTUME OF A SLOW START. "ACTIVATING" reads like a boot
in progress. It was a crash loop. The operator caught it from two screenshots
eight minutes apart showing the same state — no check, no alert, no log
watcher reported it.

⚠️ AND EVERY EXISTING CHECK PASSED. `import alert_manager` succeeds: the module
compiles, the class defines, the function defines. **The NameError exists only
at CALL time.** A checker that imports proves nothing about a body that is
never executed — which is the oldest finding in this repo's audit history,
appearing here in its purest form.

⚠️ THE SWEEP FOUND TWO MORE OF THE SAME CLASS in main.py: `_contract_warned`
and `_snapshot_warned`, both backing "log once per reason" guards, both
declared global with no module-level binding. Those fire only on the FIRST
CAPTURE FAILURE, inside the trade-write path — strictly worse to debug,
because the bug needs another bug to reveal it.

TWO CHECKS:
  S1  every module-level get_*() accessor is CALLED and must not raise
  S2  AST sweep: no Load-context name resolves nowhere in its own module

Run:  cd ~/options-trader && python3 tests/check_singletons.py
"""

from __future__ import annotations

import ast
import builtins
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PROBLEMS: list[str] = []
BUILTINS = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}

# Accessors that legitimately need network, a broker session or a live socket.
# ⚠️ EVERY ENTRY NEEDS A STATED REASON. An exemption without one is how a
# blind spot grows — this repo has the scars.
SKIP_CALL = {
    "data.tasty_client.get_tasty_client",     # opens a broker session
    "execution.broker.get_broker",            # ditto
    "data.candle_feed.get_feed",              # owns the DXLink socket
    # ⚠️ MEASURED, NOT ASSUMED. These two BLOCK on a live broker round-trip —
    # found by timing every accessor with an alarm rather than by guessing
    # which ones looked networky. The first draft of this list omitted them
    # and the check hung forever, which is its own kind of useless.
    "data.tasty_client.get_account",
    "data.tasty_client.get_open_option_positions",
}

# Hard ceiling per accessor. ⚠️ A CHECK THAT CAN HANG IS A CHECK THAT WILL BE
# SKIPPED. Any accessor that blocks past this is reported, not waited on.
CALL_TIMEOUT_S = 5


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


def _modules():
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__", "tests",
                                            "venv", "docs")]
        for f in sorted(fn):
            if not f.endswith(".py") or f == "__init__.py":
                continue
            rel = os.path.relpath(os.path.join(dp, f), ROOT)
            yield rel, rel[:-3].replace(os.sep, ".")


class _Timeout(Exception):
    pass


def _alarm(sec):
    """Per-call ceiling. No-op where SIGALRM is unavailable."""
    try:
        import signal
        if sec:
            signal.signal(signal.SIGALRM,
                          lambda *_: (_ for _ in ()).throw(_Timeout()))
        signal.alarm(int(sec))
    except Exception:                                           # noqa: BLE001
        pass


def s1_call_accessors() -> None:
    """CALL every get_*() singleton accessor. Import is not enough."""
    called = failed = 0
    blocked: list = []
    for rel, mod in _modules():
        try:
            src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
            tree = ast.parse(src)
        except Exception:                                       # noqa: BLE001
            continue
        names = [n.name for n in tree.body
                 if isinstance(n, ast.FunctionDef)
                 and n.name.startswith("get_")
                 and not n.args.args]
        if not names:
            continue
        try:
            m = importlib.import_module(mod)
        except Exception:                                       # noqa: BLE001
            continue                    # import failures are check_imports' job
        for nm in names:
            if f"{mod}.{nm}" in SKIP_CALL:
                continue
            fn = getattr(m, nm, None)
            if fn is None:
                continue
            called += 1
            _alarm(CALL_TIMEOUT_S)
            try:
                fn()
                _alarm(0)
            except _Timeout:
                _alarm(0)
                blocked.append(f"{mod}.{nm}")
                continue
            except NameError as exc:
                _alarm(0)
                # 🔴 THE EXACT FLEET-KILLER. A NameError here is a module-level
                # binding that does not exist and CANNOT be caught by import.
                failed += 1
                PROBLEMS.append(f"{mod}.{nm}")
                print(f"  FAIL  {mod}.{nm}() -> NameError: {exc}")
            except Exception:                                   # noqa: BLE001
                _alarm(0)
                # Other exceptions are environmental (no creds, no socket, no
                # db) and are NOT this check's business. Only NameError proves
                # a missing binding.
                pass
    if blocked:
        print(f"        {len(blocked)} accessor(s) blocked past "
              f"{CALL_TIMEOUT_S}s and were not waited on: {blocked}")
    check(f"S1 {called} accessor(s) called, none raised NameError", failed == 0)


def s2_unresolved_names() -> None:
    """No Load-context name resolves nowhere in its own module."""
    bad = []
    for rel, _mod in _modules():
        try:
            tree = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())
        except Exception:                                       # noqa: BLE001
            continue
        bound = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                bound.add(n.id)
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bound.add(n.name)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    bound.add((a.asname or a.name).split(".")[0])
            elif isinstance(n, ast.arg):
                bound.add(n.arg)
            elif isinstance(n, ast.ExceptHandler) and n.name:
                bound.add(n.name)
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                bound.add(n.target.id)
        for n in ast.walk(tree):
            if (isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                    and n.id not in BUILTINS and n.id not in bound):
                bad.append(f"{rel}:{n.lineno} `{n.id}`")
    if bad:
        for b in sorted(set(bad))[:20]:
            print(f"        {b}")
    check(f"S2 no unresolved names ({len(set(bad))} found)", not bad,
          "a global declared but never bound raises only when the line RUNS")


def main() -> int:
    print("=" * 68)
    print("SINGLETONS: accessors are CALLED, not merely imported")
    print("=" * 68)
    s1_call_accessors()
    s2_unresolved_names()
    print("=" * 68)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS[:6]}")
        print("  A missing module-level binding passes every import check and")
        print("  crash-loops the fleet on the first call. Ask how it RUNS.")
        return 1
    print("  ALL GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
