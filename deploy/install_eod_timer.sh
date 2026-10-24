#!/usr/bin/env bash
# ==========================================================================
# deploy/install_eod_timer.sh  v4.1
# v4.1  2026-09-11  OTV4TEST r14 — moved from the repo root to deploy/ (root cleanup); no behaviour change.
# Installs the EOD timer.
#
# v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.
#
# INHERITED DOCTRINE
# MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
# Dated release framing and trivia are stripped; what remains is the
# reasoning behind the thresholds, the design guarantees, and the
# defects that recur when forgotten. WORKING_AGREEMENT 32 requires
# this block be read before the file is edited.
#
#!/usr/bin/env bash
# repo-wide v3.0 bump: Yahoo-Finance purge & data stream
#         mapping optimization (single shared TastyTrade candle feed). No
#         logic change in this file.
# options_trader_v3/install_eod_timer.sh — v1.0
# Installs the bot-side EOD P&L writer as a systemd timer: 15:50 ET, weekdays.
# Runs eod_summary.py so ~/eod/pnl_today.json is written 5 min before the
# control server's 16:00 sweep pulls it. Timezone-aware (no DST drift).
# Deploy to every running box from the control server:
#   python fleet.py run "cd ~/options-trader && git pull && sudo bash install_eod_timer.sh"
# ==========================================================================
set -euo pipefail

DIR=/home/ubuntu/options-trader
PY=$DIR/venv/bin/python
[ -x "$PY" ] || PY=/usr/bin/python3

sudo tee /etc/systemd/system/ot-eod.service >/dev/null <<UNIT
[Unit]
Description=options_trader EOD P&L writer (writes ~/eod/pnl_today.json)
After=network-online.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=$DIR
ExecStart=$PY $DIR/tools/eod_summary.py
UNIT

sudo tee /etc/systemd/system/ot-eod.timer >/dev/null <<UNIT
[Unit]
Description=options_trader EOD P&L writer timer (15:50 ET, weekdays)

[Timer]
OnCalendar=Mon-Fri 15:50:00 America/New_York
Persistent=false

[Install]
WantedBy=timers.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now ot-eod.timer

echo "ot-eod.timer installed on $(hostname). Next run:"
systemctl list-timers ot-eod.timer --no-pager | head -3
