#!/usr/bin/env bash
# deploy/install_boot_sweep.sh  v1.1
#
# v1.1  2026-09-25  OTV4TEST r138 — NO `Wants=optionsbot.service`. In systemd, Wants=
#       STARTS the wanted unit, so a boot sweep would pull a deliberately-disabled
#       bot up at every boot - defeating setup_ec2.sh v4.7's "installed, not
#       started". `After=` alone keeps the ordering. (The reference box's live
#       unit, hand-written at r86, still carries Wants=; the bot there is enabled,
#       so it changes nothing today - re-run this installer to align it.)
#
# v1.0  2026-09-24  OTV4TEST r132 — THE BOOT SWEEP GETS AN INSTALLER. The unit
#       has run on the reference box since r86 (SWEEP.1) but was written there
#       by hand, so a fresh box could not have it — HYG.15 recorded "the
#       boot-sweep unit is not in the repo". This renders THAT unit, comments
#       and all, with only the repo path and user substituted.
#       Operator, 2026-09-24, on a fresh install: "The entire Suite. The timers,
#       the diagnostics, the menus full capability out of the box."
#
# Usage:  bash deploy/install_boot_sweep.sh
#         bash deploy/install_boot_sweep.sh --rollback
set -euo pipefail

# The REPO ROOT, one level up — r21's lesson (install_midnight_halt.sh).
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$DIR/venv/bin/python"
RUN_AS="$(id -un)"
if [ ! -x "$PY" ]; then
  # ⚠️ NO PATH FALLBACK (r21). Refuse rather than bind a guessed interpreter.
  echo "no venv at $DIR/venv — refusing to install a unit with a guessed interpreter" >&2
  exit 1
fi

if [ "${1:-}" = "--rollback" ]; then
  sudo systemctl disable optbot-boot-sweep.service 2>/dev/null || true
  sudo rm -f /etc/systemd/system/optbot-boot-sweep.service
  sudo systemctl daemon-reload
  echo "rolled back."; exit 0
fi

sudo tee /etc/systemd/system/optbot-boot-sweep.service >/dev/null <<UNIT
[Unit]
# OTV4TEST r86 (SWEEP.1) — the FULL check set runs at boot so a delivery does
# not have to pay for it. Operator, 2026-09-21: "You have an AWS auto boot
# daily at 0800. Why not run the full set then & do the abbreviated when we're
# actively trying to land changes." Installer: deploy/install_boot_sweep.sh (r132).
#
# ⚠️ ORDERED AFTER THE BOT AND THE FEED, NEVER BEFORE. A sweep that delayed the
# 08:00 start would make itself load-bearing for trading (§29), and r68 bounded
# its own raiser at 45s for the same reason — this takes ~5.5 minutes.
# ⚠️ \`After=\` ORDERS, IT DOES NOT WAIT FOR READY. That is deliberate and the
# memory guard is what actually protects the bot: boot_sweep reads
# MemAvailable and SKIPS itself below OT_SWEEP_MIN_FREE_MB rather than
# competing.
Description=OTV4TEST full checker sweep (boot only, never during a delivery)
After=optionsbot.service candle-feed.service

[Service]
Type=oneshot
User=$RUN_AS
WorkingDirectory=$DIR
# ⚠️ THE INTERPRETER IS PINNED INSIDE THE TOOL (ENV.1); this line only has to
# start SOMETHING that can import argparse.
ExecStart=$PY $DIR/tools/boot_sweep.py
Nice=19
IOSchedulingClass=idle
# ⚠️ the tool ALWAYS exits 0; belt-and-braces so an interpreter crash cannot
# leave a red in \`systemctl status\` for a finding that is not an infra fault.
SuccessExitStatus=0 1
TimeoutStartSec=900

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable optbot-boot-sweep.service
echo "installed and enabled — it runs at the NEXT boot, not now."
systemctl is-enabled optbot-boot-sweep.service || true
