#!/usr/bin/env bash
# deploy/install_emergency_watchdog.sh — v1.0
# v1.0  2026-09-27  OTV4TEST r168 (EXP.1 item 3). Installs the out-of-process
#       emergency watchdog (tools/emergency_watchdog.py). Operator: "Page, then
#       close at 15:50"; "No, positions only".
#
# 🔑 EVERY MINUTE, WEEKDAYS 09:00-16:59 ET; THE SCRIPT ITSELF GATES 09:30-16:05
# AND THE HOLIDAY LIST (utils.market_calendar). A timer that encoded the window
# would be a second copy of it.
# 🔑 Type=oneshot: systemd never starts a second run while one is in flight, so
# the 15:50-16:00 close loop (one long run) cannot be doubled by the next tick.
# ⚠️ RUNS AS ubuntu AND USES `sudo -n systemctl stop|start <bot>` ONLY IN THE
# EMERGENCY CLOSE. It reads the bot unit's Environment at run time; nothing is
# copied into this unit, so configure.sh changes reach it with no reinstall.
#
# Run:  bash deploy/install_emergency_watchdog.sh            (from anywhere)
#       bash deploy/install_emergency_watchdog.sh --rollback
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$DIR/venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "no venv at $DIR/venv — refusing to install a unit with a guessed interpreter" >&2
  exit 1
fi
SVC="${OT_BOT_SERVICE:-optionsbot}"

if [ "${1:-}" = "--rollback" ]; then
  sudo systemctl disable --now optbot-emergency-watchdog.timer 2>/dev/null || true
  sudo rm -f /etc/systemd/system/optbot-emergency-watchdog.{service,timer}
  sudo systemctl daemon-reload
  echo "rolled back."; exit 0
fi

mkdir -p "$DIR/logs"
sudo tee /etc/systemd/system/optbot-emergency-watchdog.service >/dev/null <<UNIT
[Unit]
Description=OTV4TEST emergency watchdog - page when the bot is down or stuck with a position open; close at 15:50 (r168)
After=network-online.target

[Service]
Type=oneshot
User=ubuntu
Environment=HOME=/home/ubuntu
Environment=OT_BOT_SERVICE=$SVC
WorkingDirectory=$DIR
ExecStart=$PY $DIR/tools/emergency_watchdog.py
# ⚠️ LONG ENOUGH FOR THE 15:50-16:00 CLOSE LOOP PLUS THE STOP AND RESTART.
TimeoutStartSec=1200
StandardOutput=append:$DIR/logs/emergency_watchdog.log
StandardError=append:$DIR/logs/emergency_watchdog.log
UNIT

sudo tee /etc/systemd/system/optbot-emergency-watchdog.timer >/dev/null <<UNIT
[Unit]
Description=OTV4TEST emergency watchdog, every minute on weekdays 09:00-16:59 ET (r168)

[Timer]
OnCalendar=Mon..Fri *-*-* 09..16:*:00 America/New_York
AccuracySec=5s
Persistent=false
Unit=optbot-emergency-watchdog.service

[Install]
WantedBy=timers.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now optbot-emergency-watchdog.timer
echo
systemctl list-timers 'optbot-emergency-*' --no-pager
echo
echo "installed. Log: $DIR/logs/emergency_watchdog.log · check: $PY $DIR/tools/emergency_watchdog.py --status"
