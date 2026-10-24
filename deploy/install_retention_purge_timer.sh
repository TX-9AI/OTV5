#!/usr/bin/env bash
# deploy/install_retention_purge_timer.sh — v1.2
# v1.2  2026-10-12  OTV4TEST r275 (OPS.23). THE PURGE STOPS THE CANDLE-FEED AROUND ITSELF.
#       ExecStartPre=+deploy/purge_feed_guard.sh stop / ExecStopPost=+... start (root, past
#       User=ubuntu; ExecStopPost runs even when the purge fails, so the feed always comes
#       back). Since 10-08 the VACUUM out-waited the feed's 5 s sqlite timeout and the feed
#       crash-looped 7-18 times at 16:05-16:09 ET, replaying history on every restart. The
#       midnight halt shuts the machine down, so there is no overnight slot: one deliberate
#       ~4 min gap after the close replaces the loop. The guard stops only an ACTIVE feed and
#       restarts only one it stopped. The operator, 2026-10-12 16:15 ET: "Yes, fix it all."
# v1.1  2026-09-19  OTV4TEST r53. THE PURGE GOES NIGHTLY, 16:05 ET, BY INSTRUCTION.
#       Operator: "You can make it a nightly purge, but have it run at 1605."
#       🔴 AND THE CADENCE WAS FIRST CHANGED BY HAND ON THE LIVE UNIT, WHICH IS
#       DRIFT AND NOT A FIX. check_retention_timer reads THIS FILE, not the running
#       unit, so it stayed green while the box disagreed with it and the next
#       install would have reverted the instruction silently. Same shape as r52's
#       per-connection WAL pragma: applied to the running instance instead of to
#       the thing that recreates it. THE INSTALLER IS THE SOURCE OF TRUTH.
# v1.0  2026-09-14  OTV4TEST r27 (BOX.4). THE RETENTION PURGE, WEEKLY, SATURDAY 08:30 ET.
#
# 🔑 NIGHTLY 16:05 ET SINCE r53. Operator, 2026-09-18: *"You can make it a nightly
# purge, but have it run at 1605."* ⚠️ AND HE GATED IT — *"BEFORE YOU INSTALL ANY
# TIMERS, YOU NEED TO DEAL WITH [the WAL] FIRST"* — because a nightly purge against
# an unbounded WAL just purges more often into a file that still grows. r52 pinned
# journal_size_limit at 128 MB; this cadence is installed after that, not before.
# 🔴 THE WEEKLY CADENCE WAS THE BUG, NOT A PREFERENCE (BOX.7): retention policy here
# is THREE DAYS and the timer ran ONCE A WEEK. The fleet has no purge timer at all —
# it trims as step 4 of self_close.py's 16:45 EOD takedown — so when this box was cut
# off from the warehouse and lost self_close, it silently lost the nightly purge
# riding in the same chain. 16:05 is after the cash close, inside the 08:00-00:00 up
# window, and keeps each night's delta small: the purge COSTS DISK BEFORE IT FREES
# ANY (measured 3.4 -> 2.0 GB free mid-run), so a box that has fallen behind cannot
# purge its way out.
#
# Operator, 2026-09-14 (the original ruling, superseded on cadence only): *"I want
# the purge put on a timer. Let's try Saturday after
# the automatic 8AM wake."* And on what it is: *"The retention purge is safe to run
# anytime any day because its intent is designed to flush out everything except
# the minimum necessary to preserve ramps that serve tenors. Trades should be
# excluded from that purge entirely."* — verified in warehouse/retention_purge.py:
# `trades` and every ledger are in NEVER_PURGE; trades.db only gets the reclaim's
# WAL checkpoint and gated vacuum, never a DELETE.
#
# 🔑 WHY THIS BOX NEEDS ITS OWN. On the fleet the purge rides `self_close` at 16:45
# after an S3 drain. This box does not drain (BOX.1, by ruling) and self_close is
# not installed, so NOTHING trimmed its stores — the only purges it ever had were
# a checker's side effect (HYG.10). This runs the purge ALONE: no drain, no stop,
# no shutdown. The midnight halt stays the box's only way down.
#
# ⚠️ 08:30, NOT 08:00. The EventBridge wake starts the instance at 08:00 ET; the
# bot and the feed come up behind it. Thirty minutes lets boot settle so the purge
# is not competing with a cold start for the disk. The purge's own lock and
# 120 s busy timeout (r256) already make a busy store a report, not a failure.
#
# ⚠️ Persistent=true, THE OPPOSITE OF THE MIDNIGHT HALT, ON PURPOSE. A missed
# midnight halt must never replay at the next boot — it would stop a morning box.
# A missed purge replaying at the next boot is harmless by the operator's ruling
# ("safe to run anytime any day"), and without it one failed Saturday wake would
# silently skip a week.
#
# ⚠️ --apply AT THE CALL SITE (r162): a purge without it is a dry run that deletes
# nothing and logs the same line forever.
#
# ⚠️ OnCalendar CARRIES THE ZONE. The box clock is UTC; `America/New_York` makes
# systemd track DST (verified with systemd-analyze on systemd 259: 12:30 UTC on
# 2026-10-31, 13:30 UTC on 2026-11-07 — 08:30 ET both).
#
# Run:  bash deploy/install_retention_purge_timer.sh            (from anywhere — it finds the repo)
#       bash deploy/install_retention_purge_timer.sh --rollback
set -euo pipefail

# The REPO ROOT, one level up — r21's lesson from install_midnight_halt.sh.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$DIR/venv/bin/python"
if [ ! -x "$PY" ]; then
  # ⚠️ NO PATH FALLBACK. The purge imports the repo's modules; a unit bound to
  # whatever python3 the installing shell had is r21's hazard. Refuse instead.
  echo "no venv at $DIR/venv — refusing to install a unit with a guessed interpreter" >&2
  exit 1
fi

if [ "${1:-}" = "--rollback" ]; then
  sudo systemctl disable --now optbot-retention-purge.timer 2>/dev/null || true
  sudo rm -f /etc/systemd/system/optbot-retention-purge.service /etc/systemd/system/optbot-retention-purge.timer
  sudo systemctl daemon-reload
  echo "rolled back."; systemctl list-timers 'optbot-*' --all --no-pager; exit 0
fi

sudo tee /etc/systemd/system/optbot-retention-purge.service >/dev/null <<UNIT
[Unit]
Description=OPT_Trader nightly retention purge — trim stores to the retention windows. No drain, no halt.
After=network-online.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=$DIR
# r275 (OPS.23): the feed is stopped for the purge and started after it ('+' = root).
ExecStartPre=+/bin/bash $DIR/deploy/purge_feed_guard.sh stop
ExecStart=$PY $DIR/warehouse/retention_purge.py --apply
ExecStopPost=+/bin/bash $DIR/deploy/purge_feed_guard.sh start
StandardOutput=append:$DIR/logs/retention_purge.log
StandardError=append:$DIR/logs/retention_purge.log
# The deletes and a gated vacuum of a ~600 MB feed store; an hour is generous.
TimeoutStartSec=3600
# Out of the bot's way if it is up: lowest CPU and I/O priority.
Nice=15
IOSchedulingClass=idle
UNIT

sudo tee /etc/systemd/system/optbot-retention-purge.timer >/dev/null <<UNIT
[Unit]
Description=Retention purge, nightly 16:05 ET (after the close)

[Timer]
OnCalendar=*-*-* 16:05:00 America/New_York
Persistent=true

[Install]
WantedBy=timers.target
UNIT

mkdir -p "$DIR/logs"
sudo systemctl daemon-reload
sudo systemctl enable --now optbot-retention-purge.timer
echo
systemctl list-timers 'optbot-*' --all --no-pager | sed -n '1,4p'
