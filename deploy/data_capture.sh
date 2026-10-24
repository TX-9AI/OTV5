#!/usr/bin/env bash
# deploy/data_capture.sh  v1.3
#
# v1.3  2026-10-24  CD.1 — comment only: the VIX note now says what s3_push.py does (SPX owns the VIX push).
#
# v1.2  2026-10-04  OTV4TEST r233 (BOX.17, first half) — A FAILED MASK IS SAID, AND
#       STANDALONE WRITES THE NEVER-PUSH DROP-IN. On SPX-TEST (2026-10-03) s3-push
#       had been installed as real unit files, `systemctl mask` failed, the error
#       went to /dev/null, and this script still printed "standalone". Now
#       standalone ALSO writes s3-push.service.d/never-push.conf
#       (Environment=OT_S3_PUSH=0 - s3_push.py exits before pushing), checks the
#       mask afterwards and names a failed one; managed REMOVES the drop-in before
#       it installs the pusher; status prints the push guard (masked / never-push
#       drop-in / NONE) and a standalone box with NO guard is flagged red. The
#       purge reads the same two facts (retention_purge v1.11). Gate:
#       tests/check_data_capture.py D1b/D3b/D3c.
#
# v1.1  2026-09-25  OTV4TEST r138 — THE BOT UNIT'S INSTRUMENT WINS, AND A MISMATCH
#       REFUSES. v1.0 preferred $OT_INSTRUMENT over the unit. On the first SOFI
#       box the operator ran this from the bootstrap's [deploy] tmux shell, which
#       still exported OT_INSTRUMENT=QQQ after configure item 1 had moved the
#       unit to SOFI, and it printed "managed: pushing as sym=QQQ" - a SOFI box
#       about to push into the mainline QQQ partition. Measured: nothing reached
#       S3 (0 objects from that host, any symbol). Now the unit is the source of
#       truth; the environment is used ONLY when no unit exists yet, and when both
#       are set and DISAGREE nothing is changed and the conflict is named.
#
# v1.0  2026-09-24  OTV4TEST r136 — ONE SWITCH: "managed" OR "standalone" DATA
#       CAPTURE. The operator, 2026-09-24, on bringing up OTV4TEST boxes under
#       the day_trader_pro conductor: "Make the s3 push compatible with the
#       conductor through a toggle in configure.sh call it 'managed' or
#       'standalone' data capture", "Have the same toggle switch off the cleanup
#       for 'managed'", "Have the same toggle switch off the VIX logging".
#
#   managed     the conductor owns this box's data. Enables what it drives, by
#               the EXACT names its quiesce/rearm and close use (1-REPORTER,
#               dtp 3003ac4: eod_conductor_v2.py:215/:227/:251):
#                 s3-push.timer (unmasked, installed, OT_INSTRUMENT given to the
#                 unit so the box pushes under its OWN symbol from minute one -
#                 own_symbol() otherwise falls back to sym=UNKNOWN until the
#                 first OHLC file, and the conductor's sweep culls unknown
#                 symbols), candle-logger.timer, optbot-self-close.timer (the
#                 16:45 backstop for a night control never arrives).
#               DISABLES optbot-retention-purge.timer - the conductor runs the
#               same purge at 16:05 on every box (eod_conductor_v2.py:493); two
#               schedulers for one job is r256's founding shape. The shared flock
#               (data/retention_purge.lock) would serialize them anyway.
#               Needs /usr/bin/python3 + boto3: s3-push and the conductor's
#               `--verify` run under the SYSTEM interpreter, not the venv.
#   standalone  this box pushes nothing: s3-push disabled and MASKED (the
#               reference QQQ box must never write into sym=QQQ, §38.3),
#               candle-logger and self-close off, our own 16:05 purge on.
#   status      which mode the UNITS are in - read from systemd, never from a
#               flag file, so the answer cannot drift from what actually runs.
#
# VIX: the SPX box owns the VIX push - s3_push.py pushes the VIX family only when this box's symbol is SPX
# (r139). Every box still collects and reads VIX to trade; none but SPX uploads it. (The operator, 2026-10-24:
# "SPX owns the VIX push, but all of the boxes get VIX to trade, just not upload." v1.3 corrects this comment,
# which said no box uploads it; the code was right.)
#
# Usage:  bash deploy/data_capture.sh managed|standalone|status
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-status}"
UNIT_FILE="/etc/systemd/system/optionsbot.service"
NEVER_PUSH_CONF="/etc/systemd/system/s3-push.service.d/never-push.conf"

_state() {
    # is-enabled PRINTS "not-found" AND exits non-zero for a missing unit, so the
    # output is the answer and the exit code is ignored; empty means absent.
    local s; s="$(systemctl is-enabled "$1" 2>/dev/null)"; echo "${s:-absent}"
}

status() {
    local s3 cl sc rp mode
    s3="$(_state s3-push.timer)"; cl="$(_state candle-logger.timer)"
    sc="$(_state optbot-self-close.timer)"; rp="$(_state optbot-retention-purge.timer)"
    if [ "$s3" = "enabled" ] && [ "$cl" = "enabled" ] && [ "$sc" = "enabled" ] && [ "$rp" != "enabled" ]; then
        mode="managed"
    elif [ "$s3" != "enabled" ] && [ "$cl" != "enabled" ] && [ "$sc" != "enabled" ] && [ "$rp" = "enabled" ]; then
        mode="standalone"
    else
        mode="MIXED"
    fi
    echo "data capture: $mode"
    echo "  s3-push.timer=$s3  candle-logger.timer=$cl  optbot-self-close.timer=$sc  optbot-retention-purge.timer=$rp"
    [ "$mode" = "MIXED" ] && echo "  ⚠️ neither mode is fully in effect - run: bash deploy/data_capture.sh managed|standalone"
    local g=""
    [ "$(_state s3-push.service)" = "masked" ] && g="masked"
    grep -qx 'Environment=OT_S3_PUSH=0' "$NEVER_PUSH_CONF" 2>/dev/null && g="${g:+$g + }never-push drop-in (OT_S3_PUSH=0)"
    echo "  push guard: ${g:-NONE}"
    [ "$mode" = "standalone" ] && [ -z "$g" ] && echo "  🔴 standalone, but NOTHING stops a manual s3-push start - run: bash deploy/data_capture.sh standalone"
    return 0
}

_instrument() {
    # r138 — the bot unit's OT_INSTRUMENT is the truth (configure.sh item 1 writes
    # it). The environment is used only when there is no unit value, and a
    # disagreement is refused: prints nothing and returns 1.
    local unit_sym
    unit_sym="$(sudo grep -oP '(?<=^Environment=OT_INSTRUMENT=).*' "$UNIT_FILE" 2>/dev/null | tail -1)"
    if [ -n "$unit_sym" ] && [ -n "${OT_INSTRUMENT:-}" ] && [ "$unit_sym" != "$OT_INSTRUMENT" ]; then
        echo "🔴 instrument CONFLICT: the bot unit says $unit_sym, this shell says OT_INSTRUMENT=$OT_INSTRUMENT." >&2
        echo "   Nothing changed. Use a fresh shell, or: env -u OT_INSTRUMENT bash deploy/data_capture.sh managed" >&2
        return 1
    fi
    echo "${unit_sym:-${OT_INSTRUMENT:-}}"
}

managed() {
    local sym rc=0
    sym="$(_instrument)" || return 1
    if [ -z "$sym" ]; then
        echo "🔴 no OT_INSTRUMENT (not in the environment, not in $UNIT_FILE) - refusing:"
        echo "   a managed box must push under its own symbol."; return 1
    fi
    if ! /usr/bin/python3 -c "import boto3" 2>/dev/null; then
        echo "  installing python3-boto3 (s3-push and the conductor's --verify run under /usr/bin/python3)"
        sudo apt-get install -y -qq python3-boto3 >/dev/null || { echo "🔴 python3-boto3 install failed"; return 1; }
    fi
    sudo rm -f "$NEVER_PUSH_CONF"
    sudo systemctl unmask s3-push.service s3-push.timer >/dev/null 2>&1 || true
    sudo mkdir -p /etc/systemd/system/s3-push.service.d
    printf '[Service]\nEnvironment=OT_INSTRUMENT=%s\n' "$sym" \
        | sudo tee /etc/systemd/system/s3-push.service.d/instrument.conf >/dev/null
    bash "$DIR/deploy/install_s3_push_timer.sh"       || { echo "🔴 s3-push install failed"; rc=1; }
    bash "$DIR/deploy/install_candle_logger_timer.sh" || { echo "🔴 candle-logger install failed"; rc=1; }
    bash "$DIR/deploy/install_self_close.sh"          || { echo "🔴 self-close install failed"; rc=1; }
    sudo systemctl disable --now optbot-retention-purge.timer >/dev/null 2>&1 || true
    sudo systemctl daemon-reload
    echo "managed: pushing as sym=$sym; the conductor owns the 16:05 purge."
    return $rc
}

standalone() {
    local rc=0 st
    sudo systemctl disable --now s3-push.timer >/dev/null 2>&1 || true
    sudo systemctl mask s3-push.service s3-push.timer >/dev/null 2>&1 || true
    sudo mkdir -p "$(dirname "$NEVER_PUSH_CONF")"
    printf '[Service]\nEnvironment=OT_S3_PUSH=0\n' | sudo tee "$NEVER_PUSH_CONF" >/dev/null \
        || { echo "🔴 could not write the never-push drop-in $NEVER_PUSH_CONF"; rc=1; }
    sudo systemctl disable --now candle-logger.timer optbot-self-close.timer >/dev/null 2>&1 || true
    if [ -f /etc/systemd/system/optbot-retention-purge.timer ]; then
        sudo systemctl enable --now optbot-retention-purge.timer >/dev/null 2>&1 || true
    else
        bash "$DIR/deploy/install_retention_purge_timer.sh" || { echo "🔴 retention-purge install failed"; return 1; }
    fi
    sudo systemctl daemon-reload
    st="$(_state s3-push.service)"
    if [ "$st" != "masked" ] && [ "$st" != "not-found" ]; then
        echo "  ⚠️ s3-push.service could NOT be masked (state: $st - installed as real unit files?);"
        echo "     the never-push drop-in is the guard on this box."
    fi
    echo "standalone: nothing is pushed; this box's own 16:05 purge is on."
    return $rc
}

case "$MODE" in
    managed)    managed;    rc=$?; status; exit $rc ;;
    standalone) standalone; rc=$?; status; exit $rc ;;
    status)     status ;;
    *) echo "usage: bash deploy/data_capture.sh managed|standalone|status"; exit 2 ;;
esac
