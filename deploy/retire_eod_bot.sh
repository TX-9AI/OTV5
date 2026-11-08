#!/usr/bin/env bash
# deploy/retire_eod_bot.sh  v5.0
# v5.0  2026-11-08  OTV5 r96 (TIMER.2) — REMOVES THE DEAD eod-bot UNIT FROM A BOX. Idempotent: a box without it is a no-op.
#   eod-bot.service ran /home/ubuntu/options-trader/eod_bot.sh, a root path the OTV4TEST r14 root cleanup moved to
#   deploy/; the unit was never rewritten, so it has exited 127 every session since (journal on CVX: "eod_bot.sh: No such
#   file or directory", 10-27 .. 11-06). Its two jobs are covered elsewhere: P&L comes from the warehouse (conductor
#   pnl_s3), and the full-session OHLC is candle-logger.timer's (16:05, pull_today_ohlc.sh __work). raw/eod has no object
#   after 10-23 from any box. The OTV5 clean setup (setup_ec2.sh) never installed it, which is why SOFI alone lacked it.
#   The operator, 2026-11-08: "On the timers, yes consolidate, clean up and optimize".
# Usage:  bash deploy/retire_eod_bot.sh        (on a box; run by the fleet update for TIMER.2)
# Prints one line: "eod-bot: removed" or "eod-bot: not installed".
set -uo pipefail
UNITDIR="${OT_SYSTEMD_DIR:-/etc/systemd/system}"
SUDO="${OT_SUDO-sudo}"
found=0
for u in eod-bot.timer eod-bot.service; do
  if [ -e "$UNITDIR/$u" ] || systemctl list-unit-files "$u" --no-legend 2>/dev/null | grep -q "^$u"; then
    found=1
    $SUDO systemctl disable --now "$u" >/dev/null 2>&1 || true
    $SUDO rm -f -- "$UNITDIR/$u" "$UNITDIR/timers.target.wants/$u" "$UNITDIR/multi-user.target.wants/$u"
  fi
done
if [ "$found" = 1 ]; then
  $SUDO systemctl daemon-reload >/dev/null 2>&1 || true
  $SUDO systemctl reset-failed eod-bot.service >/dev/null 2>&1 || true
  echo "eod-bot: removed"
else
  echo "eod-bot: not installed"
fi
exit 0
