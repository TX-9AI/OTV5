#!/usr/bin/env python3
"""
tests/check_rc_name.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
EVERY CLAUDE RAISE ON THIS REPO USES THE BOX'S OWN REMOTE CONTROL NAME.

v1.0  2026-10-23  OTV4TEST r314 (MENU.2) — born red at r313, where claude_boot.py
      defaults to "qqq-test" and the menu's three launch items hard-code it.

WHY. 2026-10-23: SPX-TEST's 08:05 boot hit an expired login; the hand raise had
no OT_RC_NAME (it lives only in the boot unit) and SPX-TEST came up under
QQQ-TEST's default name until the operator typed /rename. The operator, 11:10
ET: "Yes to both" (r313's menu RESTART, and this fix).

DRIVEN (§21). claude_boot.py is run as a process with a controlled environment;
devtools.sh is copied into a throwaway directory, sourced without its menu loop,
and its launch items run with tmux / claude / id / the venv python stubbed.
`id -u` answers 99999, so the menu's scratch purge looks at /tmp/claude-99999,
which does not exist: nothing real is purged, killed or raised.

  N1  OT_RC_NAME set: that name, unchanged (the boot unit's path)
  N2  OT_RC_NAME unset: "✨<INSTRUMENT>" (SPX and QQQ) - OTV5 r7: no -TEST suffix
  N3  no instrument, an unsafe one, or the reader unloadable: "✨UNSET",
      never a guessed box
  N4  the handoff command claude_boot builds carries rc_name(), not qqq-test
  N5  HAND OFF, RESUME and RESUME [other] raise under the --rc-name answer
  N6  no name from --rc-name: each item REFUSES before any purge or kill
  N7  no non-comment devtools.sh line, and no claude_boot.py code string
      (docstrings excepted), names qqq-test
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED, RAN = [], []
PY = sys.executable


def check(name, ok, detail=""):
    RAN.append(name)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name,
                          ("  — " + detail) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


def _boot(code, **env):
    """Run python code against tools.claude_boot with a controlled env."""
    e = {k: v for k, v in os.environ.items()
         if k not in ("OT_RC_NAME", "OT_INSTRUMENT", "OT_BOT_UNIT")}
    e.update(env)
    r = subprocess.run([PY, "-c", "import sys; sys.path.insert(0, sys.argv[1]);"
                        " import tools.claude_boot as cb; " + code, ROOT],
                       capture_output=True, text=True, env=e, timeout=60)
    return (r.stdout.strip(), r.stderr.strip()[-300:])


NO_UNIT = {"OT_BOT_UNIT": "chk-rc-name-no-such-unit"}

STUBS = {
    "tmux": 'echo "tmux $*" >> "$CALLS"\nexit 0\n',
    "claude": 'echo "claude $*" >> "$CALLS"\nexit 0\n',
    "id": 'echo 99999\n',
}
# the menu's $PY: answers --rc-name with $FAKE_RC (empty = no name)
FAKE_PY = ('#!/bin/bash\necho "py $*" >> "$CALLS"\n'
           'case "$*" in *--rc-name*) [ -n "${FAKE_RC:-}" ] || exit 1;'
           ' echo "$FAKE_RC" ;; esac\nexit 0\n')


def _menu(fn, stdin, **env):
    d = tempfile.mkdtemp(prefix="chk_rc_name_")
    try:
        src = open(os.path.join(ROOT, "devtools.sh"), encoding="utf-8").read()
        lines = [ln for ln in src.splitlines()
                 if ln.strip() != "while true; do menu; done"]
        with open(os.path.join(d, "devtools.sh"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        os.makedirs(os.path.join(d, "docs"))
        with open(os.path.join(d, "docs", "HANDOFF.md"), "w") as fh:
            fh.write("fixture brief\n")
        os.makedirs(os.path.join(d, "venv", "bin"))
        with open(os.path.join(d, "venv", "bin", "python"), "w") as fh:
            fh.write(FAKE_PY)
        os.chmod(os.path.join(d, "venv", "bin", "python"), 0o755)
        stub = os.path.join(d, "stubbin")
        os.makedirs(stub)
        for name, body in STUBS.items():
            with open(os.path.join(stub, name), "w") as fh:
                fh.write("#!/bin/bash\n" + body)
            os.chmod(os.path.join(stub, name), 0o755)
        calls = os.path.join(d, "calls.txt")
        open(calls, "w").close()
        e = {"PATH": stub + ":/usr/bin:/bin", "HOME": d, "CALLS": calls,
             "TERM": "dumb"}
        e.update(env)
        r = subprocess.run(["bash", "-c", 'source "$0/devtools.sh"; ' + fn, d],
                           input=stdin, capture_output=True, text=True,
                           env=e, timeout=30)
        return r.stdout + r.stderr, open(calls).read().splitlines()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    out, err = _boot("print(cb.rc_name())", OT_RC_NAME="fixture-rc", **NO_UNIT)
    check("N1 OT_RC_NAME set: that name", out == "fixture-rc", out or err)

    spx, err1 = _boot("print(cb.rc_name())", OT_INSTRUMENT="SPX", **NO_UNIT)
    qqq, err2 = _boot("print(cb.rc_name())", OT_INSTRUMENT="QQQ", **NO_UNIT)
    check("N2 unset: ✨<INSTRUMENT> (SPX, QQQ)",
          spx == "✨SPX" and qqq == "✨QQQ",
          "%r %r %s %s" % (spx, qqq, err1, err2))

    none, e3 = _boot("print(cb.rc_name())", OT_INSTRUMENT="", **NO_UNIT)
    bad, e4 = _boot("print(cb.rc_name())", OT_INSTRUMENT="a;b", **NO_UNIT)
    # the instrument reader itself unloadable: still a named absence
    gone, e4b = _boot("sys.modules['utils.instrument'] = None;"
                      " print(cb.rc_name())", OT_INSTRUMENT="SPX", **NO_UNIT)
    check("N3 no / unsafe / unreadable instrument: ✨UNSET",
          none == "✨UNSET" and bad == "✨UNSET"
          and gone == "✨UNSET",
          "%r %r %r %s %s %s" % (none, bad, gone, e3, e4, e4b))

    cmd, e5 = _boot("print(cb._handoff_cmd('/bin/claude', '/x/brief.md'))",
                    OT_INSTRUMENT="SPX", **NO_UNIT)
    check("N4 the handoff command carries rc_name(), not qqq-test",
          "--remote-control '✨SPX'" in cmd and "qqq-test" not in cmd,
          cmd or e5)

    items = ("mi_claude_handoff", "mi_claude_resume", "mi_claude_resume_pick")
    bad5 = []
    for fn in items:
        out, calls = _menu(fn, "y\n\n", FAKE_RC="✨SPX")
        raised = [c for c in calls if c.startswith("tmux new-session")]
        if not (len(raised) == 1 and "--remote-control '✨SPX'" in raised[0]
                and "qqq-test" not in raised[0]):
            bad5.append((fn, raised, out[-200:]))
    check("N5 HAND OFF / RESUME / RESUME [other] raise under the --rc-name name",
          not bad5, "%s" % bad5)

    bad6 = []
    for fn in items:
        out, calls = _menu(fn, "y\n\n", FAKE_RC="")
        touched = [c for c in calls if c.startswith("tmux")]
        if "REFUSED" not in out or touched or "scratch" in out:
            bad6.append((fn, touched, out[-200:]))
    check("N6 no name: each item REFUSES before any purge or kill",
          not bad6, "%s" % bad6)

    hits = []
    for i, ln in enumerate(open(os.path.join(ROOT, "devtools.sh"),
                                encoding="utf-8")):
        t = ln.strip()
        if not t.startswith("#") and "qqq-test" in t:
            hits.append("devtools.sh:%d" % (i + 1))
    # claude_boot.py: CODE only - a string constant that is not a docstring
    import ast
    tree = ast.parse(open(os.path.join(ROOT, "tools/claude_boot.py"),
                          encoding="utf-8").read())
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef,
                             ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(
                    getattr(first, "value", None), ast.Constant):
                docs.add(id(first.value))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and "qqq-test" in node.value and id(node) not in docs):
            hits.append("tools/claude_boot.py:%d" % node.lineno)
    check("N7 no launch line names qqq-test", not hits, "%s" % hits)

    print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
