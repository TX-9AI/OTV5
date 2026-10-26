#!/usr/bin/env python3
"""
tests/check_no_vartmp_scratch.py  v5.0
v5.0  2026-10-26  OTV5 r38 (HYG.18) — NO CHECKER OR TOOL PUTS ITS SCRATCH IN /var/tmp.
      HYG.14 (r30) points TMPDIR at a per-run dir that boot_sweep and land.sh remove, but 22 checkers named
      dir="/var/tmp" explicitly, so TMPDIR never applied and every sweep left a dozen dirs behind: 237 on SOFI by
      2026-10-26. /var/tmp survives a reboot; /tmp (a hand run outside the sweep) does not.

  V1  no tempfile.mkdtemp / mkstemp / TemporaryDirectory / NamedTemporaryFile call in tests/ or tools/ passes a dir=
      that names /var/tmp (AST, every call in every file)
  V2  END TO END: tests/check_handoff_entry_time.py run with TMPDIR=<scratch> leaves no new entry in /var/tmp

Born red on b8f42a3 at V1 (22 files) and V2.
Run:  python3 tests/check_no_vartmp_scratch.py
"""
import ast
import glob
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED = []
CALLS = {"mkdtemp", "mkstemp", "TemporaryDirectory", "NamedTemporaryFile"}


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def _offenders():
    bad = []
    for p in sorted(glob.glob(os.path.join(ROOT, "tests", "*.py")) + glob.glob(os.path.join(ROOT, "tools", "*.py"))):
        try:
            src = open(p, encoding="utf-8").read()
            tree = ast.parse(src)
        except (SyntaxError, UnicodeDecodeError):
            continue
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            fn = getattr(n.func, "attr", getattr(n.func, "id", ""))
            if fn not in CALLS:
                continue
            for kw in n.keywords:
                if kw.arg == "dir" and "/var/tmp" in (ast.get_source_segment(src, kw.value) or ""):
                    bad.append(f"{os.path.relpath(p, ROOT)}:{n.lineno}")
    return bad


def main():
    bad = _offenders()
    check("V1 no scratch call in tests/ or tools/ names dir=/var/tmp", not bad, f"{len(bad)}: {bad[:6]}")

    target = os.path.join(ROOT, "tests", "check_handoff_entry_time.py")
    if not os.path.isdir("/var/tmp") or not os.path.exists(target):
        check("V2 (not runnable here: no /var/tmp or no target)", True)
    else:
        before = set(os.listdir("/var/tmp"))
        td = tempfile.mkdtemp(prefix="chk_novt_")
        try:
            env = dict(os.environ, TMPDIR=td)
            subprocess.run([sys.executable, target], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        finally:
            shutil.rmtree(td, ignore_errors=True)
        new = sorted(e for e in set(os.listdir("/var/tmp")) - before if e.startswith("chk_hoet_"))   # its own prefix only
        for e in new:                                             # never leave our own red run's litter either
            shutil.rmtree(os.path.join("/var/tmp", e), ignore_errors=True)
        check("V2 a checker run under TMPDIR leaves nothing in /var/tmp", not new, f"new: {new}")

    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
