#!/usr/bin/env bash
# ==========================================================================
# tools/strip_retired_env.sh  v5.0
# v5.0  2026-11-08  OTV5 r76 (RETIRE.1) — TAKES THE REMOVED TRADES' STORED SWITCHES OFF A UNIT, ONCE.
#       r76 removes the ORB trade, VOLT, the ATP butterfly, ORCS and the sweep credit spread, and with them every
#       key below: config.py reads none of them, so a stored line is inert but misleading (a reader of the unit sees
#       a switch that does nothing). The operator, 2026-11-07: "Running dead code and logging dead code activity is
#       unnecessary drag. Yes, I want all of those things fixed." Run once per box after the land (fleet.py run), the
#       r68 pattern: configure.sh never removes a stored line itself.
#
# Usage:  tools/strip_retired_env.sh [--check] [UNIT_FILE ...]
#         default UNIT_FILE: /etc/systemd/system/optionsbot.service
#   --check   count only; change nothing (exit 0 either way)
#
# ⚠️ PRINTS KEY NAMES AND COUNTS, NEVER A VALUE: a unit holds credentials, and nothing here may echo a line of it.
# ⚠️ ONE EXACT KEY LIST, MATCHED AS `Environment=KEY=` AT THE START OF A LINE (or `Environment=KEY_...=` for the
#   three families). No other line can match, so a credential line or a live key is never touched.
# ⚠️ IDEMPOTENT: a second run finds nothing and changes nothing. A changed unit keeps a backup beside it
#   (<unit>.bak-retire1) and is followed by `systemctl daemon-reload`; the bot is NOT restarted here.
# ==========================================================================
set -u

EXACT="OT_SCALE_ORB OT_SCALE_VOLT OT_VOLT OT_ORB_TRADE OT_ATP_BUTTERFLY OT_ORCS OT_SWEEP_CS OT_CONTRACT_SCALE"
FAMILIES="OT_VOLT_ OT_SWEEP_CS_ OT_VELOCITY_"
# OT_VELOCITY_STALL / _ENFORCE / _GRACE_MIN / _STRICTNESS / _CONFIRM: the velocity stall measured only the ORB trade
# and never cut anything else; it is removed with it.

CHECK=0
if [ "${1:-}" = "--check" ]; then CHECK=1; shift; fi
[ "$#" -eq 0 ] && set -- /etc/systemd/system/optionsbot.service

_pattern() {
    local p="" k
    for k in $EXACT;    do p="${p:+$p|}${k}="; done
    for k in $FAMILIES; do p="${p:+$p|}${k}[A-Z0-9_]*="; done
    printf '^Environment=(%s)' "$p"
}
PAT="$(_pattern)"

_sudo() { if [ -w "$1" ] && [ -w "$(dirname "$1")" ]; then shift; "$@"; else shift; sudo -n "$@"; fi; }

rc=0
changed=0
for unit in "$@"; do
    if [ ! -f "$unit" ]; then
        echo "STRIP $unit: not present - nothing to do"
        continue
    fi
    keys="$(grep -E "$PAT" "$unit" 2>/dev/null | sed -E 's/^Environment=([A-Z0-9_]+)=.*/\1/' | sort | tr '\n' ' ')"
    n="$(grep -cE "$PAT" "$unit" 2>/dev/null)"
    n="${n:-0}"
    if [ "$n" = "0" ]; then
        echo "STRIP $unit: 0 retired line(s) - clean"
        continue
    fi
    if [ "$CHECK" = "1" ]; then
        echo "STRIP $unit: $n retired line(s) would go: ${keys% }"
        continue
    fi
    if ! _sudo "$unit" cp -p "$unit" "$unit.bak-retire1"; then
        echo "STRIP $unit: backup FAILED - unit left as it was"; rc=1; continue
    fi
    if ! _sudo "$unit" sed -i -E "/$PAT/d" "$unit"; then
        echo "STRIP $unit: edit FAILED - restore from $unit.bak-retire1"; rc=1; continue
    fi
    left="$(grep -cE "$PAT" "$unit" 2>/dev/null)"
    echo "STRIP $unit: removed $n retired line(s): ${keys% } (left ${left:-0}; backup $unit.bak-retire1)"
    changed=1
done

if [ "$changed" = "1" ] && [ "$CHECK" = "0" ] && [ -z "${OT_STRIP_NO_RELOAD:-}" ]; then
    sudo -n systemctl daemon-reload && echo "STRIP daemon-reload done" || { echo "STRIP daemon-reload FAILED"; rc=1; }
fi
exit "$rc"
