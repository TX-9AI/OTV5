#!/usr/bin/env python3
"""
tests/check_imports.py  v4.2
v4.2  2026-09-11  OTV4TEST r14 — tools.debug_status joins NOISY (it shells out at import; was skipped as a root file).
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Imports every runtime module and reports what fails. Called by the land gate.

v4.0  2026-08-19  Built at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

WHY THIS IS A TOOL AND NOT A LINE IN THE GATE.
It was inlined into the land command three times and was unusable each time:
WORKING_AGREEMENT 19 requires a single pasteable line, and a multi-line embedded
Python block is not one. A check that cannot be pasted does not get run.

WHY IMPORTING IS NOT THE SAME AS PARSING.
`tests/gen_file_map.py` PARSES - deliberately, so a module that crashes on
import still maps. This one EXECUTES the import, which is the only way to catch:
  - a circular import
  - a top-level statement that raises
None of those show up in an AST walk, and none of them showed up in `ast.parse`
across 79 files that all "passed" while the repo could not start.

⚠️ AND AN IMPORT CHECK IS NOT A RUNTIME CHECK. On 2026-08-18 a `ctx` NameError
inside `run_analysis` stopped boxes trading entirely, and `import main` passed
the whole time - the name resolves at RUNTIME, inside the function. **Passing
here means the module LOADS, not that it WORKS** (WORKING_AGREEMENT 21: tests
must execute the path).

⚠️ SOME ENTRY POINTS DO WORK AT IMPORT. `stress_theta_bleed` runs its harness and
`check_sdk` dumps the SDK surface merely by being imported. They are skipped by
default - not because their output is unwelcome, but because a check that prints
900 lines of SDK dump is a check whose real result nobody sees.
"""

import argparse
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SKIP_DIRS = {".git", "__pycache__", "tests", "deploy", "reports",
             "blind_tapes", "venv"}

# Modules that DO WORK at import time - a diagnostic dump, a harness run, or a
# shell-out. Importing them is not a useful signal and their output drowns the
# report. Listed explicitly so the skip is visible rather than a silent filter.
NOISY = {
    "tools.stress_theta_bleed",   # runs its theta-bleed harness on import (tools/ since r14)
    "utils.check_sdk",            # dumps the entire TastyTrade SDK surface
    "tools.debug_status",         # shells out to `sudo` at import (tools/ since r14)
    # the pre-r14 root copies: the lander runs CHECKs BEFORE its DEL lines, so on
    # the landing that moves them both copies exist for one run. Harmless after.
    "stress_theta_bleed", "debug_status",
}


def modules(root):
    for r, d, f in os.walk(root):
        d[:] = [x for x in d if x not in SKIP_DIRS and not x.startswith(".")]
        for x in f:
            if x.endswith(".py") and x != "__init__.py":
                rel = os.path.relpath(os.path.join(r, x), root)
                yield rel[:-3].replace(os.sep, ".")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--include-noisy", action="store_true",
                    help="also import the modules that do work at import time")
    a = ap.parse_args(argv[1:])

    ok, skipped, fails = 0, [], []
    for m in sorted(modules(a.root)):
        if m in NOISY and not a.include_noisy:
            skipped.append(m)
            continue
        try:
            importlib.import_module(m)
            ok += 1
        except SystemExit:
            # a module that calls sys.exit() at import is an entry point doing
            # its job, not a broken import
            ok += 1
        except Exception as exc:                               # noqa: BLE001
            fails.append((m, type(exc).__name__ + ": " + str(exc)[:70]))

    print(f"  imported {ok}/{ok + len(fails)}"
          + (f"   ({len(skipped)} skipped as noisy)" if skipped else ""))
    for m, e in fails:
        print(f"    FAIL {m}: {e}")
    if fails:
        print("  ⚠️ A MODULE THAT DOES NOT IMPORT IS A REPO THAT DOES NOT START.")
        print("     Fix before shipping.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
