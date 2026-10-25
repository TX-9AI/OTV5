#!/usr/bin/env python3
"""
tests/check_devtools_claude_at_boot.py  v5.0
v5.0  2026-10-25  OTV5 r13 (BOOT.12) — new. THE MENU TURNS CLAUDE-AT-BOOT ON AND OFF.
      The operator, 2026-10-25: the switch that raises Claude at boot belongs in devtools, not configure.sh, and must be
      able to stop Claude coming up at every subsequent start. Born red on r12, where CLAUDE CODE has no such item.

DRIVEN, NOT READ: devtools.sh and deploy/install_claude_boot.sh are copied into a throwaway directory (so REPO is that
directory), devtools.sh is sourced without its menu loop, and the function runs with sudo / systemctl / tmux / claude
replaced by stubs that only record their arguments. Nothing real is installed, enabled, disabled or raised.

  A1  the item renders in CLAUDE CODE, before GIT & LAND, its line <= 54 cols
  A2  its menu number dispatches it: "1" (ON) runs install_claude_boot.sh, which enables optbot-claude-boot
  A3  "2" (OFF) on an enabled unit disables it WITHOUT --now (a running session stays up) and stops nothing
  A4  "2" with no unit installed: says so, disables nothing
  A5  blank: no change, nothing installed, enabled or disabled
  A6  ON with no claude on PATH: refused by the guard, nothing installed
  A7  neither choice ever kills a tmux session or starts / restarts the unit (the toggle raises nothing)
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED, RAN = [], []
UNIT = "optbot-claude-boot"
LABEL = "AT BOOT  -> raise Claude at every boot on/off"


def check(name, ok, detail=""):
    RAN.append(name)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name,
                          ("  — " + detail) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


STUBS = {
    "tmux": 'echo "tmux $*" >> "$CALLS"\nexit 0\n',
    "sudo": 'echo "sudo $*" >> "$CALLS"\n[ "$1" = tee ] && cat > /dev/null\nexit 0\n',
    "systemctl": 'echo "systemctl $*" >> "$CALLS"\n'
                 '[ "$1" = "is-enabled" ] && { [ -n "${STATE:-}" ] && echo "$STATE" && exit 0; exit 1; }\nexit 0\n',
    "claude": 'echo "claude $*" >> "$CALLS"\nexit 0\n',
}


def _sandbox(with_claude=True):
    d = tempfile.mkdtemp(prefix="chk_devtools_atboot_")
    src = open(os.path.join(ROOT, "devtools.sh"), encoding="utf-8").read()
    lines = [ln for ln in src.splitlines() if ln.strip() != "while true; do menu; done"]
    with open(os.path.join(d, "devtools.sh"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    os.makedirs(os.path.join(d, "deploy"))
    shutil.copy(os.path.join(ROOT, "deploy", "install_claude_boot.sh"), os.path.join(d, "deploy"))
    os.makedirs(os.path.join(d, "logs"))
    os.makedirs(os.path.join(d, "venv", "bin"))
    vp = os.path.join(d, "venv", "bin", "python")
    with open(vp, "w") as fh:
        fh.write("#!/bin/bash\nexit 0\n")
    os.chmod(vp, 0o755)
    stub = os.path.join(d, "stubbin")
    os.makedirs(stub)
    for name, body in STUBS.items():
        if name == "claude" and not with_claude:
            continue
        p = os.path.join(stub, name)
        with open(p, "w") as fh:
            fh.write("#!/bin/bash\n" + body)
        os.chmod(p, 0o755)
    return d, stub


def _run(call, stdin="", with_claude=True, **env):
    d, stub = _sandbox(with_claude)
    calls = os.path.join(d, "calls.txt")
    open(calls, "w").close()
    e = {"PATH": stub + ":/usr/bin:/bin", "HOME": d, "CALLS": calls, "TERM": "dumb"}
    e.update({k: str(v) for k, v in env.items()})
    try:
        r = subprocess.run(["bash", "-c", 'source "$0/devtools.sh"; ' + call, d],
                           input=stdin, capture_output=True, text=True, env=e, timeout=30)
        return r.stdout + r.stderr, open(calls).read().splitlines()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _has(calls, needle):
    return any(c == needle for c in calls)


def _mutations(calls):
    return [c for c in calls if c.startswith("sudo ")]


def main():
    enable = "sudo systemctl enable %s.service" % UNIT
    disable = "sudo systemctl disable %s.service" % UNIT

    out, _ = _run("menu_render")
    lines = out.splitlines()
    sec = [i for i, l in enumerate(lines) if l.startswith(" CLAUDE CODE")]
    git = [i for i, l in enumerate(lines) if l.startswith(" GIT & LAND")]
    item = [i for i, l in enumerate(lines) if l.endswith(") " + LABEL)]
    wide = [lines[i] for i in item if len(lines[i]) > 54]
    check("A1 the item renders in CLAUDE CODE, before GIT & LAND, <= 54 cols",
          len(sec) == 1 and len(git) == 1 and len(item) == 1 and sec[0] < item[0] < git[0] and not wide,
          "section=%s git=%s item=%s wide=%s" % (sec, git, item, wide[:2]))
    num = lines[item[0]].split(")")[0].strip() if len(item) == 1 else "0"

    out, c2 = _run("menu_dispatch %s" % num, stdin="1\n\n")
    check("A2 dispatch #%s, '1' (ON): install_claude_boot.sh enables %s" % (num, UNIT),
          _has(c2, enable) and "ON: %s installed and enabled." % UNIT in out, "calls=%s out=%s" % (c2, out[-300:]))

    out, c3 = _run("mi_claude_at_boot", stdin="2\n\n", STATE="enabled")
    check("A3 '2' (OFF) on an enabled unit: disabled without --now, nothing stopped",
          _has(c3, disable) and not [c for c in c3 if "--now" in c or " stop " in c]
          and "OFF: %s disabled" % UNIT in out, "calls=%s out=%s" % (c3, out[-300:]))

    out, c4 = _run("mi_claude_at_boot", stdin="2\n\n")
    check("A4 '2' with no unit installed: says so, disables nothing",
          not _mutations(c4) and "no %s unit on this box" % UNIT in out, "calls=%s" % c4)

    out, c5 = _run("mi_claude_at_boot", stdin="\n\n", STATE="enabled")
    check("A5 blank: no change, nothing installed, enabled or disabled",
          not _mutations(c5) and "no change." in out, "calls=%s" % c5)

    out, c6 = _run("mi_claude_at_boot", stdin="1\n\n", with_claude=False)
    check("A6 ON with no claude on PATH: refused, nothing installed",
          not _mutations(c6) and "claude is not on PATH" in out, "calls=%s" % c6)

    allc = c2 + c3 + c4 + c5 + c6
    bad = [c for c in allc if c.startswith("tmux kill") or
           (c.startswith("sudo systemctl") and (" start " in c or " restart " in c))]
    check("A7 neither choice kills a tmux session or starts / restarts the unit", not bad, "calls=%s" % bad)

    print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
