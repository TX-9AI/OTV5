#!/usr/bin/env bash
# deploy/install_self_close.sh — v1.1
# v1.1  2026-09-11  OTV4TEST r14 — moved from the repo root to deploy/ (root cleanup); no behaviour change.
# v1.0 (2026-08-25) — THE BOX CLOSES ITSELF IF NOBODY ELSE DID.
#
# 🔑 TWO MODES, ONE OUTCOME. With control enabled the conductor closes the fleet
# at 16:05 and this timer fires at 16:45 on a machine that is already off —
# NOTHING HAPPENS, and that is correct, not a missed run. With control disabled
# or broken, this is the ONLY thing that closes the box, and it does the same
# work: drain, verify, halt.
#
# 🔴 IT INVERTS THE FAILURE MODE. Before, a disabled control server meant
# fifteen boxes ran all night and the operator learned it from the bill.
#
# ⚠️ IT ALSO RETIRES THE TWO BOX-SIDE EOD UNITS IT REPLACES:
#     optbot-eod-summary (15:50) — wrote pnl_today.json, which nothing reads
#                                  now that P&L comes from the warehouse
#     optbot-eod         (16:01) — the unified winddown, superseded
#
# ⚠️ candle-logger (16:05) IS LEFT ALONE deliberately: it collides with the
# conductor's start minute and the conductor QUIESCES it, but changing its
# schedule is a separate decision from this one.
#
# Run:  bash install_self_close.sh
#       bash install_self_close.sh --rollback
set -euo pipefail

DIR="$HOME/options-trader"
PY="$DIR/venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

if [ "${1:-}" = "--rollback" ]; then
  sudo systemctl disable --now optbot-self-close.timer 2>/dev/null || true
  sudo systemctl enable --now optbot-eod.timer optbot-eod-summary.timer 2>/dev/null || true
  sudo systemctl daemon-reload
  echo "rolled back."; systemctl list-timers 'optbot-*' --all --no-pager; exit 0
fi

sudo tee /etc/systemd/system/optbot-self-close.service >/dev/null <<UNIT
[Unit]
Description=OPT_Trader self-close (drain to S3, verify, halt) — fallback when control did not
After=network-online.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=$DIR
ExecStart=$PY $DIR/warehouse/self_close.py
StandardOutput=append:$DIR/logs/self_close.log
StandardError=append:$DIR/logs/self_close.log
TimeoutStartSec=2400
UNIT

sudo tee /etc/systemd/system/optbot-self-close.timer >/dev/null <<UNIT
[Unit]
Description=Self-close at 16:45 ET if this box is still up

[Timer]
OnCalendar=Mon-Fri 16:45:00 America/New_York
# ⚠️ Persistent=false ON PURPOSE. A box woken at 09:15 must NOT immediately run
# a missed 16:45 close from a previous day and shut itself down mid-morning.
Persistent=false

[Install]
WantedBy=timers.target
UNIT

# retire what this replaces
sudo systemctl disable --now optbot-eod.timer 2>/dev/null || true
sudo systemctl disable --now optbot-eod-summary.timer 2>/dev/null || true

mkdir -p "$DIR/logs"
sudo systemctl daemon-reload
sudo systemctl enable --now optbot-self-close.timer
echo
systemctl list-timers 'optbot-*' 'candle-*' 's3-*' --all --no-pager
echo
echo "  16:45  self-close — drain, verify, halt. Fires into silence if the"
echo "         conductor already closed this box. That is the correct outcome."
echo "  undo:  bash install_self_close.sh --rollback"
