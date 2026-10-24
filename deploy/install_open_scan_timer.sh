#!/usr/bin/env bash
# ==========================================================================
# deploy/install_open_scan_timer.sh  v1.0
# v1.0  2026-09-24  OTV4TEST r130 — THE DAILY OPEN SCAN, ON TWO TIMERS.
#       Operator: *"the scan you just ran should be done every trading day"*,
#       then: *"let's do the early ones at 9:35 and the ones that need a few
#       minutes to warm up let's do 945. On Trading days, of course."*
#         optbot-open-scan-ready.timer  Mon..Fri 09:35 America/New_York
#             -> tools/open_scan.py --phase ready  (feed, engines, levels, forks)
#         optbot-open-scan-live.timer   Mon..Fri 09:45 America/New_York
#             -> tools/open_scan.py --phase live   (plan inputs, fires, warnings)
#       Holidays are the SCRIPT's call (utils.market_calendar, the tree's one
#       list) — a Mon..Fri timer that fires on a holiday writes one line and
#       exits 0, rather than a second holiday list living in a unit file.
#       ⚠️ THE TIMEZONE IS IN THE CALENDAR, NOT THE BOX: the box clock is UTC,
#       and "09:35" alone would fire at 05:35 ET. Verified with
#       `systemd-analyze calendar` on systemd 259.
#       ⚠️ Persistent=false: the box boots at 08:00 ET; if it ever boots LATE,
#       a catch-up run at boot would scan a pipeline that has not started.
#       ⚠️ INSTALLED BY THE OPERATOR (WORKING_AGREEMENT 38.3: systemd units are
#       his). This installer is in the repo so the unit is — unlike
#       optbot-boot-sweep.service, which exists only in /etc (BACKLOG HYG.15).
# Usage:  bash deploy/install_open_scan_timer.sh            (install + enable)
#         bash deploy/install_open_scan_timer.sh --rollback  (remove both)
# ==========================================================================
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$DIR/venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "no venv at $DIR/venv — refusing to install a unit with a guessed interpreter" >&2
  exit 1
fi

if [ "${1:-}" = "--rollback" ]; then
  for p in ready live; do
    sudo systemctl disable --now "optbot-open-scan-$p.timer" 2>/dev/null || true
    sudo rm -f "/etc/systemd/system/optbot-open-scan-$p.timer" "/etc/systemd/system/optbot-open-scan-$p.service"
  done
  sudo systemctl daemon-reload
  echo "rolled back."; exit 0
fi

mkdir -p "$DIR/logs"
for p in ready live; do
  if [ "$p" = "ready" ]; then AT="09:35:00"; WHAT="feed, engines, level book, forks"; else AT="09:45:00"; WHAT="plan inputs, fires, warnings since 09:30"; fi
  sudo tee "/etc/systemd/system/optbot-open-scan-$p.service" >/dev/null <<UNIT
[Unit]
Description=OTV4TEST daily open scan, $p phase ($WHAT) - read-only (r130)
After=optionsbot.service candle-feed.service

[Service]
Type=oneshot
User=ubuntu
Environment=HOME=/home/ubuntu
WorkingDirectory=$DIR
ExecStart=$PY $DIR/tools/open_scan.py --phase $p
Nice=10
TimeoutStartSec=300
StandardOutput=append:$DIR/logs/open_scan.log
StandardError=append:$DIR/logs/open_scan.log
UNIT
  sudo tee "/etc/systemd/system/optbot-open-scan-$p.timer" >/dev/null <<UNIT
[Unit]
Description=OTV4TEST daily open scan, $p phase, $AT ET on weekdays (r130)

[Timer]
OnCalendar=Mon..Fri *-*-* $AT America/New_York
Persistent=false
Unit=optbot-open-scan-$p.service

[Install]
WantedBy=timers.target
UNIT
done

sudo systemctl daemon-reload
sudo systemctl enable --now optbot-open-scan-ready.timer optbot-open-scan-live.timer
echo
systemctl list-timers 'optbot-open-scan-*' --no-pager
echo
echo "installed. Reports: $DIR/data/open_scan/<date>_<phase>.txt · devtools: OPEN SCAN"
