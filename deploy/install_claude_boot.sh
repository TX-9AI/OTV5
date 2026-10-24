#!/usr/bin/env bash
# deploy/install_claude_boot.sh  v1.4
#
# v1.4  2026-10-03  OTV4TEST r231 (BOOT.7) — OT_BRIEF, when set at install, rides into the
#       unit beside OT_RC_NAME so a box reads its own brief (SPX-TEST: docs/HANDOFF_SPX.md).
#       Unset writes nothing; the brief stays docs/HANDOFF.md.
# v1.3  2026-09-24  OTV4TEST r133 — the closing message said "NOT started ... start
#       it deliberately" one line before setup_ec2.sh started it on a fresh box.
#       It now says what is true in both cases: enabled for every boot, and how to
#       raise it now by hand. No behaviour change.
# v1.2  2026-09-24  OTV4TEST r132 — OT_RC_NAME, when set at install, rides into
#       the unit so tools/claude_boot.py names the Remote Control session with
#       it; unset writes nothing and the name stays qqq-test.
# v1.1  2026-09-22  OTV4TEST r102 — EXEC BIT. 100644 in the git INDEX, so a
#       fresh clone or a repoint got Permission denied. Now 100755; C5 pins
#       it. No content change.
# v1.0  2026-09-20  OTV4TEST r68 (BOX.11) — RAISE AN AGENT SESSION AT BOOT.
#       Operator: "Can we have a tmux session Claude --continue added to the
#       boot sequence on this box so that an agent is available from the moment
#       the box auto wakes?" The box is woken at 08:00 ET every day by an
#       EventBridge schedule that lives outside this repo (§3), so "boot" is a
#       daily event here, not a rare one.
#
# 🔑 ORDERED *BEFORE* THE BOT, AND THE REASON IS MEASURED. The bot sends its
#    STARTED alert — the one carrying the IP, and now the agent's status —
#    ELEVEN SECONDS after boot (measured 2026-09-20: boot 12:00:10 UTC, alert
#    12:00:21). Raising and VERIFYING a session takes longer than that, so
#    without ordering the alert would say "status unknown" on essentially every
#    boot, which is the field being useless rather than absent.
# ⚠️ ORDERING IS NOT A DEPENDENCY, AND THAT IS DELIBERATE (§29 — nothing on
#    this box may be load-bearing for trading). There is NO `Requires=` and no
#    `Wants=` on the bot's side; `claude_boot.py` exits 0 even when it fails;
#    and `TimeoutStartSec` bounds the worst case at 45 s. So the very worst
#    this can do to trading is delay the 08:00 start by 45 seconds, ninety
#    minutes before the open. It can never prevent it.
#
# ⚠️ THE ONE PROPERTY THIS SCRIPT CANNOT PROVE, STATED RATHER THAN IMPLIED.
#    Whether the tmux SERVER survives after the unit's own process exits is a
#    runtime property of systemd's cgroup handling, not of this file, and no
#    gate that reads the unit text can establish it. `Type=oneshot` with
#    `RemainAfterExit=yes` keeps the unit ACTIVE so its cgroup is not torn
#    down, which is the shape chosen for exactly that reason — but it is
#    VERIFIED ON THE FIRST INSTALL, in session, and not before (the BOX.2 and
#    BOX.4 precedent: a revision cannot attest to a step that happens after its
#    own commit). After installing, confirm with:
#        systemctl start optbot-claude-boot.service
#        tmux ls && python3 tools/claude_boot.py --status-only
#
# Usage:
#       bash deploy/install_claude_boot.sh
#       bash deploy/install_claude_boot.sh --rollback
set -euo pipefail

# The REPO ROOT, one level up — r21's lesson from install_midnight_halt.sh,
# whose own changelog said "no behaviour change" about the move that broke it.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$DIR/venv/bin/python"
if [ ! -x "$PY" ]; then
  # ⚠️ NO PATH FALLBACK (r21). Refuse rather than bind a guessed interpreter.
  echo "no venv at $DIR/venv — refusing to install a unit with a guessed interpreter" >&2
  exit 1
fi

if [ "${1:-}" = "--rollback" ]; then
  sudo systemctl disable --now optbot-claude-boot.service 2>/dev/null || true
  sudo rm -f /etc/systemd/system/optbot-claude-boot.service
  sudo systemctl daemon-reload
  echo "rolled back."; exit 0
fi

sudo tee /etc/systemd/system/optbot-claude-boot.service >/dev/null <<UNIT
[Unit]
Description=Raise a Claude agent session in tmux at boot (OTV4TEST r68, BOX.11)
After=network-online.target
# ORDERING ONLY — no Requires/Wants. See the header: the bot must never depend
# on the agent, and its STARTED alert fires ~11s after boot.
Before=optionsbot.service

[Service]
Type=oneshot
# Keeps the unit ACTIVE so its cgroup is not torn down under the tmux server.
RemainAfterExit=yes
User=ubuntu
# ⚠️ HOME IS EXPLICIT. Claude's credentials live in ~/.claude and ~/.claude.json;
# a unit with no HOME finds neither and fails looking like an auth problem.
Environment=HOME=/home/ubuntu
${OT_RC_NAME:+Environment=OT_RC_NAME=$OT_RC_NAME}
${OT_BRIEF:+Environment=OT_BRIEF=$OT_BRIEF}
WorkingDirectory=$DIR
ExecStart=$PY $DIR/tools/claude_boot.py
# Bounds the delay this can add to the bot. The script's own settle budget
# sits well under it.
TimeoutStartSec=45
StandardOutput=append:$DIR/logs/claude_boot.log
StandardError=append:$DIR/logs/claude_boot.log

[Install]
WantedBy=multi-user.target
UNIT

mkdir -p "$DIR/logs"
sudo systemctl daemon-reload
sudo systemctl enable optbot-claude-boot.service
echo
echo "installed and enabled: a Claude session is raised at every boot. To raise one now by hand:"
echo "  sudo systemctl start optbot-claude-boot.service"
echo "  python3 $DIR/tools/claude_boot.py --status-only"
# ⚠️ `|| true`, AND THE GATE IS WHY. Under `set -euo pipefail` this REPORTING
# line failed the whole install: `systemctl is-enabled` exits 4 for a unit the
# real systemd does not have, which is precisely the case inside the checker's
# stubbed run. An install that succeeded and then reported rc=4 would have been
# indistinguishable from one that genuinely failed — caught by B0 rather than
# on the box.
systemctl is-enabled optbot-claude-boot.service || true
