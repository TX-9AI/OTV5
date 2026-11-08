#!/usr/bin/env python3
"""
tests/check_eod_bot_gone.py  v5.0
v5.0  2026-11-08  OTV5 r96 (TIMER.2) — new. The dead eod-bot unit and its installers are removed, and a fleet update
      removes the unit from a box. The operator, 2026-11-08: "On the timers, yes consolidate, clean up and optimize".

  G1  deploy/eod_bot.sh, deploy/install_eod_bot.sh, deploy/install_eod_timer.sh, deploy/reinstall_timers.sh are gone
  G2  no live code line names them (comments, docs/, history manifests and this gate excepted), and devtools has no REINSTALL TIMERS item
  G3  setup_ec2.sh installs no eod-bot or ot-eod unit (a fresh box never gets it back)
  G4  what eod-bot did is still done: candle-logger's installer runs pull_today_ohlc.sh __work, and the manual
      tools/eod_summary.py stays reachable from devtools
  R1  retire_eod_bot.sh on a box WITH the unit: disables both units, removes the files, reloads, prints "removed", exits 0
  R2  run again (and on a box WITHOUT the unit): touches nothing, prints "not installed", exits 0 (idempotent)
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAN, FAILED = [], []
GONE = ["deploy/eod_bot.sh", "deploy/install_eod_bot.sh", "deploy/install_eod_timer.sh", "deploy/reinstall_timers.sh"]
NAMES = ["eod_bot.sh", "install_eod_bot.sh", "install_eod_timer.sh", "reinstall_timers.sh"]
# History, not wiring: the port manifest's description table and the generated docs.
EXEMPT = {"tests/check_eod_bot_gone.py", "tests/scrub_headers.py", "deploy/retire_eod_bot.sh"}


def check(name, ok, detail=""):
    RAN.append(name)
    print(("PASS " if ok else "FAIL ") + name + ("" if ok or not detail else f"  -- {detail}"))
    if not ok:
        FAILED.append(name)


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as fh:
        return fh.read()


def code(txt):
    """The lines that run: shell/python comment lines and header history do not wire anything."""
    return "\n".join(l for l in txt.splitlines() if not l.lstrip().startswith("#"))


def live_files():
    for d, dirs, files in os.walk(ROOT):
        rel_d = os.path.relpath(d, ROOT)
        if rel_d.split(os.sep)[0] in (".git", "docs", "data", "logs", "venv", "__pycache__"):
            dirs[:] = []
            continue
        for f in files:
            if f.endswith((".py", ".sh", ".service", ".timer", ".conf")):
                rel = os.path.normpath(os.path.join(rel_d, f))
                if rel not in EXEMPT:
                    yield rel


def run_retire(unitdir, bindir, log):
    env = dict(os.environ, OT_SYSTEMD_DIR=unitdir, OT_SUDO="", PATH=bindir + os.pathsep + os.environ.get("PATH", ""),
               STUB_LOG=log, STUB_UNITDIR=unitdir)
    p = subprocess.run(["bash", os.path.join(ROOT, "deploy/retire_eod_bot.sh")], env=env,
                       capture_output=True, text=True, timeout=30)
    return p.returncode, p.stdout.strip()


def main():
    check("G1 the four eod-bot files are deleted", all(not os.path.exists(os.path.join(ROOT, g)) for g in GONE),
          ", ".join(g for g in GONE if os.path.exists(os.path.join(ROOT, g))))

    hits = []
    for rel in live_files():
        txt = code(read(rel))
        for n in NAMES:
            if n in txt:
                hits.append(f"{rel}:{n}")
    dv = code(read("devtools.sh"))
    check("G2 no live file names them; devtools has no REINSTALL TIMERS",
          not hits and "REINSTALL TIMERS" not in dv and "mi_reinstall_timers" not in dv, ", ".join(hits[:6]))

    se = read("setup_ec2.sh")
    check("G3 setup_ec2.sh installs no eod-bot / ot-eod unit", "eod-bot" not in se and "ot-eod" not in se
          and "install_eod" not in se)

    cl = read("deploy/install_candle_logger_timer.sh")
    check("G4 candle-logger still runs pull_today_ohlc __work; eod_summary still on the devtools menu",
          "pull_today_ohlc.sh" in cl and "__work" in cl and "tools/eod_summary.py" in dv
          and os.path.exists(os.path.join(ROOT, "tools/eod_summary.py")))

    with tempfile.TemporaryDirectory() as td:
        unitdir, bindir, log = os.path.join(td, "units"), os.path.join(td, "bin"), os.path.join(td, "calls.log")
        os.makedirs(os.path.join(unitdir, "timers.target.wants"))
        os.makedirs(bindir)
        stub = os.path.join(bindir, "systemctl")
        with open(stub, "w") as fh:
            fh.write('#!/usr/bin/env bash\necho "$*" >> "$STUB_LOG"\n'
                     'if [ "$1" = list-unit-files ]; then [ -e "$STUB_UNITDIR/$2" ] && echo "$2 enabled enabled"; fi\n'
                     'exit 0\n')
        os.chmod(stub, os.stat(stub).st_mode | stat.S_IEXEC)
        for u in ("eod-bot.timer", "eod-bot.service"):
            open(os.path.join(unitdir, u), "w").close()
        open(os.path.join(unitdir, "timers.target.wants", "eod-bot.timer"), "w").close()
        open(os.path.join(unitdir, "candle-logger.timer"), "w").close()

        rc, out = run_retire(unitdir, bindir, log)
        calls = open(log).read() if os.path.exists(log) else ""
        left = sorted(os.listdir(unitdir)) + sorted(os.listdir(os.path.join(unitdir, "timers.target.wants")))
        check("R1 with the unit: both disabled, files removed, reload, 'removed', rc 0",
              rc == 0 and out == "eod-bot: removed" and "disable --now eod-bot.timer" in calls
              and "disable --now eod-bot.service" in calls and "daemon-reload" in calls
              and not any(x.startswith("eod-bot") for x in left) and "candle-logger.timer" in left,
              f"rc={rc} out={out!r} left={left}")

        open(log, "w").close()
        rc2, out2 = run_retire(unitdir, bindir, log)
        calls2 = open(log).read()
        check("R2 again: no disable, no reload, 'not installed', rc 0, other units untouched",
              rc2 == 0 and out2 == "eod-bot: not installed" and "disable" not in calls2 and "daemon-reload" not in calls2
              and os.path.exists(os.path.join(unitdir, "candle-logger.timer")), f"rc={rc2} out={out2!r}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} of {len(RAN)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
