#!/usr/bin/env bash
# deploy/install_midnight_halt.sh — v1.3
# v1.3  2026-09-22  OTV4TEST r102 — EXEC BIT. 100644 in the git INDEX, so a
#       fresh clone or a repoint got Permission denied. Now 100755; C5 pins
#       it. No content change.
# v1.2  2026-09-13  OTV4TEST r21 — DIR IS THE REPO ROOT. r14's line below says
#       "moved ... no behaviour change"; THE MOVE WAS THE BEHAVIOUR CHANGE. `DIR`
#       came from this script's own directory, so from deploy/ the unit named
#       paths under deploy/. Rendered with sudo stubbed: the python fell back to
#       PATH's python3 and the installer mkdir'd deploy/logs, but ExecStart named
#       deploy/warehouse/midnight_halt.py, which DOES NOT EXIST. Never installed on
#       this box, so it never fired broken — the first install would have made a
#       timer that fails every midnight and pages nobody. Now resolves one level
#       up, and check_midnight_halt M4 renders the unit and checks it.
# v1.1  2026-09-11  OTV4TEST r14 — moved from the repo root to deploy/ (root cleanup); no behaviour change.
# v1.0 (2026-09-06) — r289 / EOD.3. Installs the midnight ET backstop.
#
# Operator: *"I do sometimes work on them late & might forget. So I want another
# self shutdown at midnight eastern time to catch anything I accidentally left
# up. No drain, or anything else. Just stop, that's it."*
#
# 🔑 THIS SITS BELOW `optbot-self-close.timer`, NOT BESIDE IT. That one runs at
# 16:45, drains to S3, verifies, and deliberately STAYS UP IF SHORT. This one
# runs at 00:00 and only halts. Seven hours apart, so they cannot race, and the
# later one carries none of the earlier one's machinery — a backstop that can
# hang is not a backstop.
#
# ⚠️ EVERY DAY, NOT Mon-Fri. The 16:45 close is weekdays because that is when a
# session ends; this exists because a box was left up by hand, and that happens
# on a Saturday as easily as a Tuesday. A Sunday afternoon spent on the fleet is
# exactly the case the operator described.
#
# Run:  bash deploy/install_midnight_halt.sh            (from anywhere — it finds the repo)
#       bash deploy/install_midnight_halt.sh --rollback
set -euo pipefail

# 🔴 OTV4TEST r21 — THE REPO ROOT, NOT THIS SCRIPT'S OWN DIRECTORY. This line
# read `dirname` alone, which was the repo root while the installer lived there.
# r14 moved every installer into deploy/ and re-pointed three timer installers;
# THIS ONE WAS MISSED. From deploy/ every path below resolved one level too deep.
# RENDERED WITH `sudo` STUBBED, NOT REASONED (check_midnight_halt M4): two of the
# three were rescued by accident — PY falls back to `command -v python3` and the
# `mkdir -p "$DIR/logs"` below creates deploy/logs — but ExecStart named
# deploy/warehouse/midnight_halt.py, WHICH DOES NOT EXIST. The timer would fire
# every midnight, fail to find its script, and page nobody: a backstop the
# operator believes he has and does not.
# ⚠️ AND THE FALLBACK IS ITSELF A HAZARD: `command -v python3` resolves from the
# INSTALLING shell's PATH, so the unit's interpreter depended on how the operator
# happened to log in. At the root, $DIR/venv/bin/python exists and it never runs.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$DIR/venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

if [ "${1:-}" = "--rollback" ]; then
  sudo systemctl disable --now optbot-midnight-halt.timer 2>/dev/null || true
  sudo rm -f /etc/systemd/system/optbot-midnight-halt.{service,timer}
  sudo systemctl daemon-reload
  echo "rolled back."; systemctl list-timers 'optbot-*' --all --no-pager; exit 0
fi

sudo tee /etc/systemd/system/optbot-midnight-halt.service >/dev/null <<UNIT
[Unit]
Description=OPT_Trader midnight backstop — halt if this box is still up. No drain.
After=network-online.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=$DIR
ExecStart=$PY $DIR/warehouse/midnight_halt.py
StandardOutput=append:$DIR/logs/midnight_halt.log
StandardError=append:$DIR/logs/midnight_halt.log
# ⚠️ SHORT TIMEOUT. It reads one file and calls shutdown; anything slower is
# wedged, and a wedged backstop must give up rather than hold the boot.
TimeoutStartSec=120
UNIT

sudo tee /etc/systemd/system/optbot-midnight-halt.timer >/dev/null <<UNIT
[Unit]
Description=Halt at 00:00 ET if this box is somehow still up

[Timer]
OnCalendar=*-*-* 00:00:00 America/New_York
# ⚠️ Persistent=false, FOR THE SAME REASON AS THE 16:45 TIMER. A box woken at
# 09:15 must NOT immediately run a missed midnight halt and stop itself in the
# middle of the morning — which would be this backstop causing precisely the
# outage it exists to prevent.
Persistent=false

[Install]
WantedBy=timers.target
UNIT

mkdir -p "$DIR/logs"
sudo systemctl daemon-reload
sudo systemctl enable --now optbot-midnight-halt.timer
echo
echo "Installed. To keep a box up overnight deliberately:"
echo "  touch $DIR/data/NO_MIDNIGHT_HALT     # survives a bake; remove to re-arm"
echo
systemctl list-timers 'optbot-*' --all --no-pager | sed -n '1,4p'
