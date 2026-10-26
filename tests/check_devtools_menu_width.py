#!/usr/bin/env python3
"""
tests/check_devtools_menu_width.py  v5.0
v5.0  2026-10-25  (MENU.1) — new. EVERY DEVTOOLS MENU LINE FITS 54 COLUMNS. The operator reads the menu on a phone in
      Termius and a line past the 54-column rule wraps; "OPEN SCAN  today's 09:35 + 09:45 reports" rendered 56. The
      existing menu checkers each measured only their own item (check_devtools_claude_at_boot A1), so nothing measured
      the rest. Born red on ffe10bf at W1 (the OPEN SCAN line, 56 columns).

DRIVEN, NOT READ: devtools.sh is copied into a throwaway directory (so REPO is that directory), sourced without its menu
loop, and the REAL menu_render prints the menu; widths are counted in characters (a label may carry an em dash or an
arrow). The status line under the title (service states + the last commit) depends on the box and is not a label, so it
is the one line not measured.

  W1  every rendered rule, title, section and item line is <= 54 columns
  W2  NOT VACUOUS: more than 40 items and at least 8 sections were rendered and measured
  W3  CONTROL: an item appended to MENU with a 49-character label (55 columns rendered) is reported by the same scan
"""
import os
import subprocess
import sys
import tempfile
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMIT = 54
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


def render(extra=""):
    d = tempfile.mkdtemp(prefix="chk_menu_width_")
    try:
        src = open(os.path.join(ROOT, "devtools.sh"), encoding="utf-8").read()
        lines = [ln for ln in src.splitlines() if ln.strip() != "while true; do menu; done"]
        with open(os.path.join(d, "devtools.sh"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        env = {"PATH": "/usr/bin:/bin", "HOME": d, "TERM": "dumb", "LC_ALL": "C.UTF-8"}
        r = subprocess.run(["bash", "-c", 'source "$0/devtools.sh" >/dev/null 2>&1; ' + extra + "menu_render", d],
                           capture_output=True, env=env, timeout=30)
        return r.stdout.decode("utf-8", "replace").splitlines()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def wide(lines):
    out = []
    for i, ln in enumerate(lines):
        if ln.startswith("  bot="):          # the box-dependent status line, not a label
            continue
        if len(ln) > LIMIT:
            out.append("%d cols: %r" % (len(ln), ln))
    return out


def main():
    lines = render()
    bad = wide(lines)
    check("W1 every rendered menu line is <= %d columns" % LIMIT, not bad, "; ".join(bad[:4]))

    items = [l for l in lines if l[:6].strip().endswith(")") and l.startswith("  ")]
    sections = [l for l in lines if l.startswith(" ") and not l.startswith("  ") and l.endswith(":")]
    check("W2 not vacuous: >40 items and >=8 sections rendered", len(items) > 40 and len(sections) >= 8,
          "items=%d sections=%d" % (len(items), len(sections)))

    label = "X" * 49
    ctl = wide(render('MENU+=("ITEM|%s|true"); ' % label))
    check("W3 CONTROL: a 49-char label (55 cols) is reported by the same scan",
          any(label in c for c in ctl), "scan reported %s" % ctl[:2])

    print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
