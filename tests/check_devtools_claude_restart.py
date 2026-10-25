#!/usr/bin/env python3
"""
tests/check_devtools_claude_restart.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
THE MENU'S CLAUDE RESTART GOES THROUGH THE BOOT UNIT, AND ENDS THE SESSION FIRST.

v1.0  2026-10-23  OTV4TEST r313 (MENU.1) — born red at r312 (5b13d7c), where the
      CLAUDE CODE section has no restart item.

WHY. The operator, 2026-10-23 10:04 ET: "Make the sudo systemctl restart
optbot-claude-boot a devtools menu item in the Claude section". That morning
SPX-TEST's 08:05 boot hit an expired login; the hand raise from an SSH shell had
no OT_RC_NAME (only the unit sets it) and came up under QQQ-TEST's default name.
⚠️ A BARE RESTART RAISES NOTHING over a hand-raised session: bring_up() returns
"already running" for ANY live claude in tmux 'claude', and a session started
from a shell is outside the unit's cgroup, so the unit's stop does not end it.

DRIVEN, NOT READ (§21): devtools.sh is copied into a throwaway directory (so its
REPO is that directory), sourced without its menu loop, and the function is run
with tmux / sudo / systemctl / claude replaced by stubs that only record their
arguments. Nothing real is restarted, killed or raised.

  R1  the item renders in CLAUDE CODE, before GIT & LAND, its line <= 54 cols
  R2  its menu number dispatches it: "y" ends tmux 'claude', THEN restarts
      optbot-claude-boot through sudo systemctl
  R3  "n" at the confirm: nothing ended, nothing restarted
  R4  no session running: nothing ended, the restart still runs
  R5  a failed restart says so with its rc (never a green line, §0.5)
  R6  run INSIDE tmux 'claude': refused, nothing ended, nothing restarted
  R7  other tmux sessions are never touched: no kill-server, ever
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED, RAN = [], []
UNIT = "optbot-claude-boot"
LABEL = "RESTART  -> fresh session via boot unit"


def check(name, ok, detail=""):
    RAN.append(name)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name,
                          ("  — " + detail) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


STUBS = {
    "tmux": 'echo "tmux $*" >> "$CALLS"\n'
            'case "$1" in\n'
            '  has-session) exit "${HAS_RC:-0}" ;;\n'
            '  display-message) echo "${TMUX_NAME:-other}" ;;\n'
            'esac\nexit 0\n',
    "sudo": 'echo "sudo $*" >> "$CALLS"\nexit "${SUDO_RC:-0}"\n',
    "systemctl": 'echo "systemctl $*" >> "$CALLS"\n'
                 '[ "$1" = "is-active" ] && echo active\nexit 0\n',
    "claude": 'echo "claude $*" >> "$CALLS"\nexit 0\n',
}


def _sandbox():
    d = tempfile.mkdtemp(prefix="chk_devtools_restart_")
    src = open(os.path.join(ROOT, "devtools.sh"), encoding="utf-8").read()
    # the menu loop is the last statement; without it the file only defines
    lines = [ln for ln in src.splitlines()
             if ln.strip() != "while true; do menu; done"]
    with open(os.path.join(d, "devtools.sh"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    os.makedirs(os.path.join(d, "logs"))
    with open(os.path.join(d, "logs", "claude_boot.log"), "w") as fh:
        fh.write("claude_boot: up (handoff), tmpfs 454M free\n")
    # a stub venv python, so the menu's "no venv" warning is not in the render
    os.makedirs(os.path.join(d, "venv", "bin"))
    vp = os.path.join(d, "venv", "bin", "python")
    with open(vp, "w") as fh:
        fh.write("#!/bin/bash\nexit 0\n")
    os.chmod(vp, 0o755)
    stub = os.path.join(d, "stubbin")
    os.makedirs(stub)
    for name, body in STUBS.items():
        p = os.path.join(stub, name)
        with open(p, "w") as fh:
            fh.write("#!/bin/bash\n" + body)
        os.chmod(p, 0o755)
    return d, stub


def _run(call, stdin="", **env):
    d, stub = _sandbox()
    calls = os.path.join(d, "calls.txt")
    open(calls, "w").close()
    e = {"PATH": stub + ":/usr/bin:/bin", "HOME": d, "CALLS": calls,
         "TERM": "dumb"}
    e.update({k: str(v) for k, v in env.items()})
    try:
        r = subprocess.run(["bash", "-c", 'source "$0/devtools.sh"; ' + call, d],
                           input=stdin, capture_output=True, text=True,
                           env=e, timeout=30)
        got = open(calls).read().splitlines()
        return r.stdout + r.stderr, got
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _idx(calls, needle):
    for i, c in enumerate(calls):
        if c == needle:
            return i
    return -1


def main():
    restart = "sudo systemctl restart %s" % UNIT
    kill = "tmux kill-session -t claude"

    # R1 — the render
    out, _ = _run("menu_render")
    lines = out.splitlines()
    sec = [i for i, l in enumerate(lines) if l.startswith(" CLAUDE CODE")]
    git = [i for i, l in enumerate(lines) if l.startswith(" GIT & LAND")]
    item = [i for i, l in enumerate(lines) if l.endswith(") " + LABEL)]
    # the NEW item's width only: an older line's width is not this gate's call
    wide = [lines[i] for i in item if len(lines[i]) > 54]
    check("R1 the item renders in CLAUDE CODE, before GIT & LAND, <= 54 cols",
          len(sec) == 1 and len(git) == 1 and len(item) == 1
          and sec[0] < item[0] < git[0] and not wide,
          "section=%s git=%s item=%s wide=%s" % (sec, git, item, wide[:2]))
    num = lines[item[0]].split(")")[0].strip() if len(item) == 1 else "0"

    # R2 — dispatched by its number, "y"
    out, calls = _run("menu_dispatch %s" % num, stdin="y\n\n")
    k, r = _idx(calls, kill), _idx(calls, restart)
    check("R2 dispatch #%s, 'y': ends tmux 'claude' THEN restarts %s"
          % (num, UNIT), k >= 0 and r > k, "calls=%s" % calls)

    # R3 — "n"
    out, calls = _run("mi_claude_restart_boot", stdin="n\n\n")
    check("R3 'n': nothing ended, nothing restarted",
          _idx(calls, kill) < 0 and _idx(calls, restart) < 0
          and "mi_claude_restart_boot: command not found" not in out,
          "calls=%s out=%s" % (calls, out[-200:]))

    # R4 — no session running
    out, calls = _run("mi_claude_restart_boot", stdin="y\n\n", HAS_RC=1)
    check("R4 no session: nothing ended, the restart still runs",
          _idx(calls, kill) < 0 and _idx(calls, restart) >= 0,
          "calls=%s" % calls)

    # R5 — a failed restart is named with its rc
    out, calls = _run("mi_claude_restart_boot", stdin="y\n\n", SUDO_RC=1)
    check("R5 a failed restart says FAILED with its rc",
          "restart FAILED (rc 1)" in out and _idx(calls, restart) >= 0,
          "out=%s" % out[-300:])

    # R6 — inside tmux 'claude'
    out, calls = _run("mi_claude_restart_boot", stdin="y\n\n",
                      TMUX="/tmp/tmux-1000/default,1,0", TMUX_NAME="claude")
    check("R6 inside tmux 'claude': refused, nothing ended or restarted",
          "REFUSED" in out and _idx(calls, kill) < 0
          and _idx(calls, restart) < 0, "calls=%s" % calls)

    # R7 — never the whole tmux server (across R2's full run)
    out, calls = _run("mi_claude_restart_boot", stdin="y\n\n")
    check("R7 no kill-server: other tmux sessions are untouched",
          not any("kill-server" in c for c in calls)
          and _idx(calls, restart) >= 0, "calls=%s" % calls)

    print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
