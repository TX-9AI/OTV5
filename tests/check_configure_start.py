"""tests/check_configure_start.py — v1.1
v1.1  2026-10-24 — CD.1. F1-F4 are the sessions AFTER the first start (the harness supplies the marker);
      the first start itself is tests/check_clean_deploy.py C4-C8.
configure.sh's DONE STARTS THE BOT: enable + start when stopped, restart when
running and changed, nothing when running and unchanged.

v1.0  2026-09-25 — OTV4TEST r138. The operator: the bot is "not started by
      default and then when I set all the variables in configure and exit out of
      the menu that resets everything and starts it". setup_ec2.sh v4.7 leaves
      optionsbot installed, NOT enabled, NOT started; finish_session is the Done
      path. The real function body runs under a harness (configure.sh cannot be
      sourced - it ends in the interactive menu), with sudo and bot_is_running
      stubbed; nothing touches systemd.

  F1  stopped + unchanged: ENABLE and START (the fresh-box case)
  F2  stopped + changed: ENABLE and START
  F3  running + changed: ENABLE and RESTART (the old behaviour, kept)
  F4  running + unchanged: NOTHING
  F5  the menu's Done path calls finish_session (and the old bare
      CHANGED->auto_restart block is gone)
  F6  the summary tells a stopped box that Done starts it
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIGURE = os.path.join(ROOT, "configure.sh")
FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def _functions_only(src: str) -> str:
    out, keep = [], False
    for line in src.splitlines():
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*\(\)\s*\{", line):
            keep = True
        if keep:
            out.append(line)
        if keep and line == "}":
            keep = False
    return "\n".join(out)


def _finish(running_before: bool, changed: bool):
    src = open(CONFIGURE).read()
    with tempfile.TemporaryDirectory() as tmp:
        funcs = os.path.join(tmp, "funcs.sh")
        open(funcs, "w").write(_functions_only(src))
        state = os.path.join(tmp, "running")
        if running_before:
            open(state, "w").write("1")
        log = os.path.join(tmp, "log")
        harness = f"""
RESET=""; BOLD=""; GREEN=""; YELLOW=""; CYAN=""; RED=""
SERVICE_NAME=optionsbot
FIRST_START_FILE="{funcs}"   # CD.1: an existing file = the first start has happened
source "{funcs}"
sleep() {{ :; }}
show_config() {{ echo SHOW_CONFIG >> "{log}"; }}
bot_is_running() {{ [ -f "{state}" ]; }}
sudo() {{ echo "sudo $*" >> "{log}";
          case "$*" in *"systemctl start"*|*"systemctl restart"*) echo 1 > "{state}";; esac; }}
CHANGED={"true" if changed else "false"}
finish_session
"""
        r = subprocess.run(["bash", "-c", harness], capture_output=True, text=True, timeout=60)
        calls = open(log).read().splitlines() if os.path.exists(log) else []
        return r, [c for c in calls if c.startswith("sudo")], calls


_src = open(CONFIGURE).read()
check("F0 finish_session is defined", "finish_session() {" in _src)

r, sudo, _ = _finish(False, False)
check("F1 stopped + unchanged: enable, then start",
      sudo == ["sudo systemctl enable optionsbot", "sudo systemctl start optionsbot"]
      and "Bot started" in r.stdout, str(sudo) + " " + r.stdout[-80:])
r, sudo, _ = _finish(False, True)
check("F2 stopped + changed: enable, then start",
      sudo == ["sudo systemctl enable optionsbot", "sudo systemctl start optionsbot"], str(sudo))
r, sudo, calls = _finish(True, True)
check("F3 running + changed: enable, then restart (config shown)",
      sudo == ["sudo systemctl enable optionsbot", "sudo systemctl restart optionsbot"]
      and "SHOW_CONFIG" in calls, str(calls))
r, sudo, _ = _finish(True, False)
check("F4 running + unchanged: nothing at all", sudo == [], str(sudo))

_tail = _src[_src.rfind("done\n"):]
check("F5 the Done path calls finish_session; the bare CHANGED->auto_restart block is gone",
      re.search(r"^finish_session\s*$", _src, re.M) is not None
      and not re.search(r'^if \[\[ "\$CHANGED" == "true" \]\]; then\n    echo ""\n    show_config\n    auto_restart',
                        _src, re.M))
check("F6 a stopped bot is told that Done starts it",
      "it starts (and is enabled at boot) when you choose Done" in _src)

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
