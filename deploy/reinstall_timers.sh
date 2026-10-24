#!/usr/bin/env bash
# deploy/reinstall_timers.sh  v1.0
# v1.0  2026-09-11  OTV4TEST r14 — after the root cleanup the timers whose ExecStart
#       pointed at a root path (eod_summary.py, pull_today_ohlc.sh, eod_bot.sh) must be
#       re-installed once on the box; a BAKE does not rewrite systemd units. Re-runs
#       each installer ONLY if its unit is already present, so nothing new is added.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for pair in "ot-eod.timer:install_eod_timer.sh" "candle-logger.timer:install_candle_logger_timer.sh" "eod-bot.timer:install_eod_bot.sh"; do
  unit="${pair%%:*}"; inst="${pair##*:}"
  if systemctl list-unit-files 2>/dev/null | grep -q "^$unit"; then
    echo "reinstalling $unit via deploy/$inst"
    bash "$HERE/$inst" || echo "  ⚠️ $inst reported an issue"
  else
    echo "skip: $unit not installed on this box"
  fi
done
sudo systemctl daemon-reload 2>/dev/null
systemctl list-timers --all 2>/dev/null | grep -E "eod|candle-logger" || true
