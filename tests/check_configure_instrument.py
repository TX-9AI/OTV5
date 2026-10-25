"""tests/check_configure_instrument.py — v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.1  2026-10-24  CD.1 - the harness stubs the managed switch's OLD-label drain and NEW-symbol guard (configure.sh
      v4.19) with clean outcomes; every expectation is unchanged. check_clean_deploy C14-C16 drive the refusals.
configure.sh ITEM 1 MOVES THE WHOLE BOX: the bot unit, the FEED's unit, the feed
itself, and on a managed box the push label.

v1.0  2026-09-25 — OTV4TEST r139. The first SOFI paper box traded SOFI while its
      candle feed streamed QQQ: item 1 rewrote only optionsbot.service, and
      candle-feed.service carries its own Environment=OT_INSTRUMENT. The operator:
      "a good lesson learned for when we migrate the fleet over".

  ⚠️ change_instrument DELETES $BOT_DIR/trades.db in paper mode, and the lander
  runs checks INSIDE THE LIVE TREE. BOT_DIR is therefore a planted fixture with
  its own trades.db; I0 proves the real one is untouched.

  I1  the bot unit gets the new OT_INSTRUMENT
  I2  the FEED unit's OT_INSTRUMENT line is rewritten - and only that line
  I3  a running feed is restarted; a stopped one is not started
  I4  a MANAGED box re-applies data_capture.sh managed with OT_INSTRUMENT UNSET
      (the stale-shell trap); a standalone box does not
  I5  a feed unit with no OT_INSTRUMENT line warns, and does not crash
  I0  the repo's real trades.db is untouched
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


FEED_UNIT = """[Service]
Environment=OT_INSTRUMENT=QQQ
Environment=TT_CLIENT_SECRET=fixture-secret
ExecStart=/x/venv/bin/python -m data.candle_feed
"""


def _run(new_sym, feed_active=True, mode="standalone", feed_unit=FEED_UNIT):
    src = open(os.path.join(ROOT, "configure.sh")).read()
    tmp = tempfile.mkdtemp(prefix="cfginstcheck_")
    try:
        bot = os.path.join(tmp, "bot")
        os.makedirs(os.path.join(bot, "deploy"))
        shutil.copy(os.path.join(ROOT, "config.py"), os.path.join(bot, "config.py"))
        open(os.path.join(bot, "trades.db"), "w").write("fixture")
        log = os.path.join(tmp, "log")
        with open(os.path.join(bot, "deploy", "data_capture.sh"), "w") as fh:
            fh.write('#!/bin/bash\nif [ "$1" = status ]; then echo "data capture: %s"; exit 0; fi\n'
                     'echo "data_capture $1 OT_INSTRUMENT=${OT_INSTRUMENT-UNSET}" >> "%s"\n' % (mode, log))
        envfile = os.path.join(tmp, "env")
        open(envfile, "w").write("OT_INSTRUMENT=QQQ\nOT_PAPER_TRADING=True\n")
        feedfile = os.path.join(tmp, "candle-feed.service")
        open(feedfile, "w").write(feed_unit)
        funcs = os.path.join(tmp, "funcs.sh")
        open(funcs, "w").write(_functions_only(src))
        # CD.1 (configure v4.19): a managed switch drains under the OLD label first and guards the NEW symbol -
        # stubbed here (a clean drain, a clean guard); tests/check_clean_deploy.py C14-C16 drive the other outcomes
        pushpy, botpy = os.path.join(tmp, "pushpy"), os.path.join(tmp, "botpy")
        open(pushpy, "w").write('#!/bin/bash\necho "DRAIN host=x sym=$OT_INSTRUMENT drained=yes pushed=0 failed=0 '
                                'prefixes=0 local=0 s3=0 short=0 OK"\n')
        open(botpy, "w").write('#!/bin/bash\nexit 0\n')
        os.chmod(pushpy, 0o755)
        os.chmod(botpy, 0o755)
        harness = f"""
RESET=""; BOLD=""; GREEN=""; YELLOW=""; CYAN=""; RED=""
BOT_DIR="{bot}"; FEED_UNIT_FILE="{feedfile}"; SERVICE_NAME=optionsbot
PUSH_PY="{pushpy}"; BOT_PY="{botpy}"; PUSH_PAUSE_FILE="{tmp}/push_paused"; FIRST_START_FILE="{funcs}"
export OT_INSTRUMENT=QQQ
source "{funcs}"
get_env() {{ sed -n "s/^$1=//p" "{envfile}"; }}
set_env() {{ grep -v "^$1=" "{envfile}" > "{envfile}.t"; mv "{envfile}.t" "{envfile}"; echo "$1=$2" >> "{envfile}"; }}
reload_daemon() {{ echo "reload" >> "{log}"; }}
systemctl() {{ if [ "$1" = is-active ]; then {'return 0' if feed_active else 'return 3'}; fi; echo "systemctl $*" >> "{log}"; }}
sudo() {{ case "$1" in grep|sed) "$@" ;; *) echo "sudo $*" >> "{log}"; "$@" ;; esac; }}
change_instrument
"""
        r = subprocess.run(["bash", "-c", harness], input=new_sym + "\n", capture_output=True,
                           text=True, timeout=120, cwd=tmp)
        env = open(envfile).read()
        feed = open(feedfile).read()
        calls = open(log).read() if os.path.exists(log) else ""
        return r, env, feed, calls, os.path.exists(os.path.join(bot, "trades.db"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_real = os.path.join(ROOT, "trades.db")
_real_before = (os.stat(_real).st_size, os.stat(_real).st_mtime_ns) if os.path.exists(_real) else None

r, env, feed, calls, _db = _run("SOFI", feed_active=True, mode="standalone")
check("I1 the bot unit gets OT_INSTRUMENT=SOFI", "OT_INSTRUMENT=SOFI" in env, env.replace("\n", " | ") + r.stderr[-120:])
check("I2 the feed unit's OT_INSTRUMENT is rewritten to SOFI",
      "Environment=OT_INSTRUMENT=SOFI\n" in feed and "OT_INSTRUMENT=QQQ" not in feed, feed.replace("\n", " | "))
check("I2 ...and every other feed-unit line is untouched",
      feed.replace("OT_INSTRUMENT=SOFI", "OT_INSTRUMENT=QQQ") == FEED_UNIT)
check("I3 a running feed is restarted", "sudo systemctl restart candle-feed" in calls, calls[-200:])
check("I4 a standalone box does not re-apply data capture", "data_capture managed" not in calls)

r, env, feed, calls, _db = _run("AAL", feed_active=False, mode="managed")
check("I3 a stopped feed is not started or restarted",
      "restart candle-feed" not in calls and "start candle-feed" not in calls, calls[-200:])
check("I4 a managed box re-applies data_capture.sh managed with OT_INSTRUMENT UNSET",
      "data_capture managed OT_INSTRUMENT=UNSET" in calls, calls[-200:])

r, env, feed, calls, _db = _run("SOFI", feed_unit="[Service]\nExecStart=/x\n")
check("I5 no OT_INSTRUMENT line in the feed unit: warns, bot unit still moves, rc 0",
      r.returncode == 0 and "feed was NOT moved" in r.stdout and "OT_INSTRUMENT=SOFI" in env,
      "rc=%s %s" % (r.returncode, r.stdout[-120:]))

_real_after = (os.stat(_real).st_size, os.stat(_real).st_mtime_ns) if os.path.exists(_real) else None
check("I0 the repo's real trades.db is untouched", _real_after == _real_before)
check("I0 no cfginstcheck_ temp dirs left behind",
      not [n for n in os.listdir(tempfile.gettempdir()) if n.startswith("cfginstcheck_")])

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
