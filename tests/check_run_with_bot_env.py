#!/usr/bin/env python3
"""tests/check_run_with_bot_env.py — v1.0
THE CREDENTIAL WRAPPER RUNS ONLY A COMMITTED, LISTED PROBE, PASSES ONLY THE KEYS
IT NEEDS, AND PRINTS NO VALUE.

v1.0  2026-09-29 — OTV4TEST r176 (PRB.1). Drives the REAL tools/run_with_bot_env.py,
      copied into a throwaway git repo, with a stub `systemctl` on PATH that
      prints a FAKE Environment block and a fake probe that reports only key
      NAMES and whether each value arrived intact. The real bot unit is never
      read (OT_BOT_UNIT names a fake unit as a second guard) and no real probe
      runs.
  R1  an unlisted name is refused (64) and nothing runs
  R2  a path-shaped argument is refused (64) - names only, never paths
  R3  a committed listed probe runs, gets TT_* (a value with spaces intact),
      OT_INSTRUMENT and OT_FEED_DB, and NOT TELEGRAM_*/GITHUB_*/others; its
      exit code comes back unchanged
  R4  nothing the wrapper or the probe prints contains a fake value
  R5  a probe edited in the working tree is refused (65) and does not run
  R6  an untracked probe is refused (65)
  R7  a change staged but not committed is refused (65)
  R8  an unreadable unit, or one with no TT_ key, is refused (69), nothing runs
  R9  the three listed probes exist in this tree
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED, RAN = [], []
SECRET = "FAKE-SECRET-9f3a"
REFRESH = "FAKE REFRESH WITH SPACES 77"
TG = "FAKE-TG-5521"
GH = "FAKE-GH-8812"


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def guard(name, fn, detail=lambda: ""):
    try:
        ok = bool(fn())
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"raised {type(exc).__name__}: {exc}")
        return False
    try:
        d = detail()
    except Exception:                                           # noqa: BLE001
        d = ""
    check(name, ok, d)
    return ok


TMP = tempfile.mkdtemp(prefix="rwbe_")
REPO = os.path.join(TMP, "repo")
BIN = os.path.join(TMP, "bin")
MARK = os.path.join(TMP, "ran.json")
os.makedirs(os.path.join(REPO, "tools"))
os.makedirs(BIN)

_src = os.path.join(_root, "tools", "run_with_bot_env.py")
if os.path.exists(_src):
    shutil.copy(_src, os.path.join(REPO, "tools", "run_with_bot_env.py"))

PROBE = r'''
import json, os, sys
e = os.environ
json.dump({"keys": sorted(k for k in e if k.startswith(("TT_", "OT_", "TELEGRAM", "GITHUB", "OTHER"))),
           "secret_ok": e.get("TT_CLIENT_SECRET") == %r,
           "refresh_ok": e.get("TT_REFRESH_TOKEN") == %r}, open(%r, "w"))
print("probe ran")
sys.exit(7)
''' % (SECRET, REFRESH, MARK)
with open(os.path.join(REPO, "tools", "probe_aux_streams.py"), "w") as fh:
    fh.write(PROBE)
with open(os.path.join(REPO, "tools", "feed_capabilities.py"), "w") as fh:
    fh.write(PROBE)


def _git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True)


_git("init", "-q")
_git("-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
_git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "fixture")


def _stub(block, rc=0):
    with open(os.path.join(BIN, "systemctl"), "w") as fh:
        fh.write("#!/bin/sh\ncat <<'EOF'\n%s\nEOF\nexit %d\n" % (block, rc))
    os.chmod(os.path.join(BIN, "systemctl"), 0o755)


FULL = ('TT_CLIENT_SECRET=%s "TT_REFRESH_TOKEN=%s" TT_ACCOUNT_NUMBER=5WX0000 '
        'OT_INSTRUMENT=QQQ OT_FEED_DB=/x/feed.db TELEGRAM_TOKEN=%s GITHUB_TOKEN=%s '
        'OTHER_SECRET=nope' % (SECRET, REFRESH, TG, GH))


def _run(*args):
    if os.path.exists(MARK):
        os.unlink(MARK)
    env = {"PATH": BIN + os.pathsep + "/usr/bin:/bin", "HOME": TMP,
           "OT_BOT_UNIT": "fixture-unit-not-real"}
    r = subprocess.run([sys.executable, os.path.join(REPO, "tools", "run_with_bot_env.py"), *args],
                       capture_output=True, text=True, env=env, timeout=60)
    ran = json.load(open(MARK)) if os.path.exists(MARK) else None
    return r, ran


_D = {}
_stub(FULL)


def _r1():
    r, ran = _run("not_a_probe.py")
    return r.returncode == 64 and ran is None


guard("R1 an unlisted name is refused (64), nothing runs", _r1)


def _r2():
    outs = [_run(a) for a in ("tools/probe_aux_streams.py", "../repo/tools/probe_aux_streams.py",
                              os.path.join(REPO, "tools", "probe_aux_streams.py"))]
    return all(r.returncode == 64 and ran is None for r, ran in outs)


guard("R2 a path-shaped argument is refused (64)", _r2)


def _r3():
    r, ran = _run("probe_aux_streams.py")
    _D["r3"] = (r.returncode, ran, r.stderr[-200:])
    return (r.returncode == 7 and ran is not None and ran["secret_ok"] and ran["refresh_ok"]
            and ran["keys"] == ["OT_FEED_DB", "OT_INSTRUMENT", "TT_ACCOUNT_NUMBER",
                                "TT_CLIENT_SECRET", "TT_REFRESH_TOKEN"])


guard("R3 a committed probe runs with TT_*/OT_INSTRUMENT/OT_FEED_DB only; exit code kept", _r3,
      lambda: str(_D.get("r3"))[:260])


def _r4():
    r, _ = _run("probe_aux_streams.py")
    text = r.stdout + r.stderr
    return not any(v in text for v in (SECRET, REFRESH, TG, GH, "5WX0000"))


guard("R4 no fake value appears in anything printed", _r4)


def _r5():
    p = os.path.join(REPO, "tools", "probe_aux_streams.py")
    orig = open(p).read()
    open(p, "a").write("\n# edited\n")
    try:
        r, ran = _run("probe_aux_streams.py")
    finally:
        open(p, "w").write(orig)
    return r.returncode == 65 and ran is None


guard("R5 an edited probe is refused (65) and does not run", _r5)


def _r6():
    p = os.path.join(REPO, "tools", "probe_candle_depth.py")
    open(p, "w").write(PROBE)
    try:
        r, ran = _run("probe_candle_depth.py")
    finally:
        os.unlink(p)
    return r.returncode == 65 and ran is None


guard("R6 an untracked probe is refused (65)", _r6)


def _r7():
    p = os.path.join(REPO, "tools", "feed_capabilities.py")
    orig = open(p).read()
    open(p, "a").write("\n# staged\n")
    _git("add", "tools/feed_capabilities.py")
    try:
        r, ran = _run("feed_capabilities.py")
    finally:
        open(p, "w").write(orig)
        _git("add", "tools/feed_capabilities.py")
    return r.returncode == 65 and ran is None


guard("R7 a staged but uncommitted change is refused (65)", _r7)


def _r8():
    _stub("", rc=1)
    r1, ran1 = _run("probe_aux_streams.py")
    _stub("OT_INSTRUMENT=QQQ TELEGRAM_TOKEN=%s" % TG)
    r2, ran2 = _run("probe_aux_streams.py")
    _stub(FULL)
    return r1.returncode == 69 and ran1 is None and r2.returncode == 69 and ran2 is None


guard("R8 an unreadable unit or one with no TT_ key is refused (69)", _r8)

guard("R9 the three listed probes exist in this tree",
      lambda: all(os.path.isfile(os.path.join(_root, "tools", n))
                  for n in ("feed_capabilities.py", "probe_aux_streams.py", "probe_candle_depth.py")))

shutil.rmtree(TMP, ignore_errors=True)
print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
