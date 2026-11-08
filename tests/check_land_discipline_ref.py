#!/usr/bin/env python3
"""
tests/check_land_discipline_ref.py  v5.0
v5.0  2026-11-08  (LAND.2) — new. A STANDALONE RUN CAN CHECK THE LAST LANDED REVISION. tools/check_land_discipline.py
      v5.2 read --rev only as a ledger label, so `--rev HEAD --against HEAD~1` asked the ledger for a row named "HEAD"
      and failed "no row for HEAD" on every OTV5 commit (the operator's attended run, 11-08). Born red on cac9e37 at D1.

DRIVEN: the target tree's own tools/check_land_discipline.py main() runs against throwaway git repos built with its own
_mkrepo() fixture (one versioned module, docs/GENESIS.md), each landed commit a bumped module plus its ledger row,
committed with the lander's subject shape "rN: ...".

  D1  --rev HEAD on a landed tip resolves to its rN label, diffs against HEAD~1, and PASSES
  D2  --rev HEAD~1 (not the tip) is refused, naming the tip rule, not reported as a missing ledger row
  D3  a tip whose subject carries no rN: label is refused, naming the subject, not "no row for HEAD"
  D4  CONTROL: a plain label (--rev r2) behaves exactly as before (PASS against HEAD~1)
  D5  a bare run (no --rev) on a clean tree prints the --rev HEAD hint
  D6  a --rev that is neither a label nor a ref is refused by name
"""
import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


_sp = importlib.util.spec_from_file_location("_cld_ref", os.path.join(ROOT, "tools", "check_land_discipline.py"))
cld = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(cld)

BUMPED = ("#!/usr/bin/env python3\n# mod.py — v1.1\n"
          "# v1.1 (2026-02-01) — the change.\n# v1.0 (2026-01-01) — born.\nX = 2\n")


def git(d, *a):
    subprocess.run(["git", *a], cwd=d, check=True, capture_output=True)


def landed(d, subject):
    cld._mkrepo(d)
    open(os.path.join(d, "mod.py"), "w").write(BUMPED)
    open(os.path.join(d, "docs", "GENESIS.md"), "a").write("| **r2** | the change |\n")
    git(d, "add", "-A")
    git(d, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", subject)


def run(d, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cld.main(["check_land_discipline.py", "--repo", d, *args])
    return rc, buf.getvalue()


with tempfile.TemporaryDirectory() as d:
    landed(d, "r2: r2: the change")
    rc, out = run(d, "--rev", "HEAD")
    check("D1 --rev HEAD resolves r2 and passes", rc == 0 and "resolved to r2" in out and "\nPASS" in out, out[-400:])
    rc, out = run(d, "--rev", "HEAD~1")
    check("D2 a non-tip ref is refused by the tip rule", rc == 1 and "not the tip" in out and "no row for" not in out,
          out[-300:])
    rc, out = run(d, "--rev", "r2", "--against", "HEAD~1")
    check("D4 CONTROL: a plain label behaves as before", rc == 0 and "GENESIS   PASS" in out, out[-300:])
    rc, out = run(d)
    check("D5 a bare run prints the --rev HEAD hint", "BUMP      hint" in out and "--rev HEAD" in out, out[-300:])
    rc, out = run(d, "--rev", "nosuchref")
    check("D6 an unknown --rev is refused by name", rc == 1 and "neither a ledger label" in out, out[-300:])

with tempfile.TemporaryDirectory() as d:
    landed(d, "a hand commit with no label")
    rc, out = run(d, "--rev", "HEAD")
    check("D3 a subject with no rN: label is refused by name", rc == 1 and "does not start with a revision label" in out
          and "no row for HEAD" not in out, out[-300:])

print("\n%s — %d/%d" % ("FAIL" if FAILED else "PASS", len(RAN) - len(FAILED), len(RAN)))
sys.exit(1 if FAILED else 0)
