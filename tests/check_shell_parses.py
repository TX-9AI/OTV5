#!/usr/bin/env python3
"""
tests/check_shell_parses.py  v1.0
v1.0  2026-09-08  r322 / SH.1 — EVERY SHELL SCRIPT IN THE TREE MUST PARSE.

🔴 THE FAILURE THIS EXISTS FOR. r65 (2026-08-25) wrote its changelog entry into
four shell headers WITHOUT the leading `#`, so three lines of prose became
three lines of shell:

    v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
          system removed - identifiers, comments, docstrings, schema. The word
          does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Bash reported `v4.1: command not found`, then `syntax error near unexpected
token '('` on the parenthesis in "(delivery)". **A syntax error aborts the
parse**, so `devtools.sh`, `check_versions.sh`, `push.sh` and
`install_tooling.sh` did NOTHING AT ALL for fourteen days — on every box, at
every revision. It surfaced only because the operator ran `./devtools.sh` on
the AMD box on 2026-09-08 and read the error.

⚠️ WHY NOTHING CAUGHT IT, AND THE ANSWER IS "NOTHING WAS LOOKING". Python is
covered several ways over — `check_imports` imports 105 modules, and a Python
syntax error would fail every one of them. Shell had NO equivalent: the land
gate reads headers and changelogs, `gen_file_map` inventories files, and none
of them ask whether a `.sh` file is valid shell. A whole language in the tree
was outside every gate.

⚠️ AND THE HEADER DISCIPLINE IS WHAT BROKE IT, which is worth stating plainly:
§5 requires a changelog entry in every edited file, and in a `.sh` file that
entry IS executable unless every line is commented. The rule is right; the
mechanical hazard it carries in shell had never been named.

WHAT THIS CHECKS: `bash -n` (parse, do not execute) over every `*.sh` in the
tree. It cannot catch a script that parses and misbehaves — that is what the
callers' own checks are for — but "did not parse at all" is the whole of this
class and it is cheap to make impossible.

Run:  python3 tests/check_shell_parses.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "venv", "__pycache__", "node_modules"}

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


def scripts():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for n in sorted(files):
            if n.endswith(".sh"):
                yield os.path.join(base, n)


def main():
    found = list(scripts())
    # ⚠️ AN EMPTY SWEEP MUST NOT READ AS GREEN. If the walk stops finding
    # scripts — a moved tree, a renamed extension — "0 checked, all pass" is
    # the laundered green this file exists to prevent.
    check("S0 the sweep actually found shell scripts", len(found) > 0,
          f"{len(found)} found")

    bad = []
    for path in found:
        r = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
        if r.returncode != 0:
            first = (r.stderr.strip().splitlines() or ["(no stderr)"])[0]
            bad.append(f"{os.path.relpath(path, ROOT)}: {first.strip()}")

    check("S1 every shell script parses (bash -n)", not bad,
          f"{len(found)} checked" if not bad else "; ".join(bad))

    # S2 — the specific shape that caused it: a header line that is neither a
    # comment, a shebang, nor blank, ABOVE the first real statement. This is a
    # narrower, faster signal than a parse error and names the actual mistake.
    shape = []
    for path in found:
        try:
            lines = open(path, encoding="utf-8").read().splitlines()[:20]
        except Exception:                                        # noqa: BLE001
            continue
        for i, ln in enumerate(lines[:12], 1):
            s = ln.strip()
            if not s or s.startswith("#") or s.startswith("set ") or i == 1:
                continue
            # a version/changelog line that lost its marker
            if s[:1] == "v" and len(s) > 3 and s[1].isdigit():
                shape.append(f"{os.path.relpath(path, ROOT)}:{i}: {s[:48]}")
            break
    check("S2 no uncommented changelog line in a shell header", not shape,
          "; ".join(shape) if shape else "")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(found)} shell script(s) parse")
    return 0


if __name__ == "__main__":
    sys.exit(main())
