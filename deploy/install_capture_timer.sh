#!/usr/bin/env bash
# deploy/install_capture_timer.sh  v5.0
# v5.0  2026-11-08  OTV5 r94 (CAP.1) — the timers that run tools/capture_all.py: everything TastyTrade serves that the
#       feed does not already keep, into the warehouse. The operator, 2026-11-08: "If they offer it, we better be
#       downloading it. Non-negotiable. It all goes to the fucking warehouse."
#   optbot-capture-metrics  09:38 and 15:52 ET  /market-metrics (box family; SPX also the context list)
#   optbot-capture-chain    09:42, 12:30, 16:15 ET  the full chain, every expiry and strike: quotes, OI, greeks, IV over REST
#   optbot-capture-events   16:25 ET            earnings + dividend history, risk-free rate
# RECORDING ONLY, REST ONLY: no DXLink stream, so the streamer-session ceiling and the per-node limit are untouched.
# Usage:  bash deploy/install_capture_timer.sh            (install + enable)
#         bash deploy/install_capture_timer.sh --rollback  (remove all three)
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$DIR/venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "no venv at $DIR/venv — refusing to install a unit with a guessed interpreter" >&2
  exit 1
fi
MODES="metrics chain events"

if [ "${1:-}" = "--rollback" ]; then
  for m in $MODES; do
    sudo systemctl disable --now "optbot-capture-$m.timer" 2>/dev/null || true
    sudo rm -f "/etc/systemd/system/optbot-capture-$m.timer" "/etc/systemd/system/optbot-capture-$m.service"
  done
  sudo systemctl daemon-reload
  echo "rolled back."; exit 0
fi

cal_for() {
  case "$1" in
    metrics) printf 'OnCalendar=Mon..Fri *-*-* 09:38:00 America/New_York\nOnCalendar=Mon..Fri *-*-* 15:52:00 America/New_York\n' ;;
    chain)   printf 'OnCalendar=Mon..Fri *-*-* 09:42:00 America/New_York\nOnCalendar=Mon..Fri *-*-* 12:30:00 America/New_York\nOnCalendar=Mon..Fri *-*-* 16:15:00 America/New_York\n' ;;
    events)  printf 'OnCalendar=Mon..Fri *-*-* 16:25:00 America/New_York\n' ;;
  esac
}

mkdir -p "$DIR/logs"
for m in $MODES; do
  sudo tee "/etc/systemd/system/optbot-capture-$m.service" >/dev/null <<UNIT
[Unit]
Description=OTV5 capture_all $m - TastyTrade data into the warehouse, recording only (r94 CAP.1)
After=optionsbot.service

[Service]
Type=oneshot
User=ubuntu
Environment=HOME=/home/ubuntu
WorkingDirectory=$DIR
ExecStart=$PY $DIR/tools/capture_all.py $m
Nice=15
IOSchedulingClass=idle
TimeoutStartSec=900
MemoryMax=600M
StandardOutput=append:$DIR/logs/capture_all.log
StandardError=append:$DIR/logs/capture_all.log
UNIT
  {
    printf '[Unit]\nDescription=OTV5 capture_all %s schedule (r94 CAP.1)\n\n[Timer]\n' "$m"
    cal_for "$m"
    printf 'Persistent=false\nUnit=optbot-capture-%s.service\n\n[Install]\nWantedBy=timers.target\n' "$m"
  } | sudo tee "/etc/systemd/system/optbot-capture-$m.timer" >/dev/null
done

sudo systemctl daemon-reload
for m in $MODES; do sudo systemctl enable --now "optbot-capture-$m.timer"; done
systemctl list-timers --all --no-pager 2>/dev/null | grep optbot-capture || true
