#!/usr/bin/env bash
# ==========================================================================
# tools/strip_retired_env.sh  v5.2
# v5.2  2026-11-08  OTV5 r88 (RETIRE.3) - THE TCS SHADOW'S KEYS JOIN THE LIST, AND A BACKUP IS NEVER OVERWRITTEN. The operator,
#       2026-11-08: "Delete" (the TCS shadow). OT_TCS_* , OT_TR_TCS_* , OT_TR_W_TCS_* and OT_SHADOW_TRADES_DB are read by
#       nothing after r88. A unit that already has .bak-retire1 (r76/r78, the hand strip of 11-08) keeps it; the next
#       strip writes .bak-retire2, and so on.
# v5.1  2026-11-08  OTV5 r78 (RETIRE.2) - MATCHES THE UNITS AS setup_ec2.sh / configure.sh ACTUALLY WRITE THEM.
#       v5.0 matched only `Environment=KEY=` and the fleet's units carry `Environment="KEY=value"`: on 2026-11-08
#       it reported "0 retired line(s)" on 14/14 while every box still held OT_SCALE_ORB / OT_SCALE_VOLT (removed by
#       hand, backup .bak-retire1). The line is now parsed the way systemd reads it - one or more assignments,
#       each bare, "double"- or 'single'-quoted - and each assignment is judged by its KEY: a line of only retired
#       assignments goes; a line mixing retired and live ones keeps the live ones verbatim (their original quoting);
#       a line that cannot be parsed is left as it was and makes the run exit 1. Still names and counts only.
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
# ⚠️ ONE EXACT KEY LIST (or KEY_... for the families), JUDGED PER ASSIGNMENT ON `Environment=` LINES ONLY,
#   quoted or bare. A credential or live assignment is never removed, never rewritten, never printed.
# ⚠️ IDEMPOTENT: a second run finds nothing and changes nothing. A changed unit keeps a backup beside it
#   (<unit>.bak-retire1) and is followed by `systemctl daemon-reload`; the bot is NOT restarted here.
# ==========================================================================
set -u

EXACT="OT_SCALE_ORB OT_SCALE_VOLT OT_VOLT OT_ORB_TRADE OT_ATP_BUTTERFLY OT_ORCS OT_SWEEP_CS OT_CONTRACT_SCALE OT_SHADOW_TRADES_DB"
FAMILIES="OT_VOLT_ OT_SWEEP_CS_ OT_VELOCITY_ OT_TCS_ OT_TR_TCS_ OT_TR_W_TCS_"
# r88 (RETIRE.3): the TCS shadow - OT_TCS_ACTIVE and every OT_TCS_* dial, its readiness knobs (OT_TR_TCS_*, OT_TR_W_TCS_*)
# and the shadow store path (OT_SHADOW_TRADES_DB) - are read by nothing once the TCS is removed.
# OT_VELOCITY_STALL / _ENFORCE / _GRACE_MIN / _STRICTNESS / _CONFIRM: the velocity stall measured only the ORB trade
# and never cut anything else; it is removed with it.

CHECK=0
if [ "${1:-}" = "--check" ]; then CHECK=1; shift; fi
[ "$#" -eq 0 ] && set -- /etc/systemd/system/optionsbot.service

_sudo() { if [ -w "$1" ] && [ -w "$(dirname "$1")" ]; then shift; "$@"; else shift; sudo -n "$@"; fi; }

# _plan UNIT OUT: write the stripped unit to OUT; print "N KEYS..." (count of retired assignments, their names);
# exit 2 when a line could not be parsed (that line is copied unchanged). Never prints a value.
_plan() {
    EXACT="$EXACT" FAMILIES="$FAMILIES" python3 -I - "$1" "$2" <<'PY'
import os, shlex, sys
exact = set(os.environ["EXACT"].split()); fam = tuple(os.environ["FAMILIES"].split())
def retired(k): return k in exact or k.startswith(fam)
def tokens(rest):
    out, cur, q = [], "", None
    for ch in rest:
        if q:
            cur += ch
            if ch == q: q = None
        elif ch in "\"'":
            q = ch; cur += ch
        elif ch in " \t":
            if cur: out.append(cur); cur = ""
        else:
            cur += ch
    if q: raise ValueError("unbalanced quote")
    if cur: out.append(cur)
    return out
src, dst = sys.argv[1], sys.argv[2]
lines = open(src).read().split("\n")
keep, names, bad = [], [], 0
for ln in lines:
    if not ln.startswith("Environment="):
        keep.append(ln); continue
    try:
        raw = tokens(ln[len("Environment="):])
        keys = []
        for t in raw:
            v = shlex.split(t)
            if len(v) != 1 or "=" not in v[0]: raise ValueError("not an assignment")
            keys.append(v[0].split("=", 1)[0])
    except ValueError:
        keep.append(ln); bad += 1; continue
    gone = [k for k in keys if retired(k)]
    if not gone:
        keep.append(ln); continue
    names += gone
    live = [t for t, k in zip(raw, keys) if not retired(k)]
    if live: keep.append("Environment=" + " ".join(live))
open(dst, "w").write("\n".join(keep))
print(len(names), " ".join(sorted(names)))
sys.exit(2 if bad else 0)
PY
}

rc=0
changed=0
for unit in "$@"; do
    if [ ! -f "$unit" ]; then
        echo "STRIP $unit: not present - nothing to do"
        continue
    fi
    tmp="$(mktemp)"
    res="$(_plan "$unit" "$tmp")"; prc=$?
    n="${res%% *}"; keys="${res#* }"; [ "$n" = "$res" ] && keys=""
    n="${n:-0}"
    if [ "$prc" = "2" ]; then echo "STRIP $unit: a line could not be parsed - left as it was"; rc=1; fi
    if [ "$prc" != "0" ] && [ "$prc" != "2" ]; then echo "STRIP $unit: parse FAILED - unit left as it was"; rm -f "$tmp"; rc=1; continue; fi
    if [ "$n" = "0" ]; then
        echo "STRIP $unit: 0 retired line(s) - clean"; rm -f "$tmp"
        continue
    fi
    if [ "$CHECK" = "1" ]; then
        echo "STRIP $unit: $n retired line(s) would go: $keys"; rm -f "$tmp"
        continue
    fi
    # r88: a backup is NEVER overwritten - the first strip's .bak-retire1 (the unit before RETIRE.1) is kept, and a
    # later strip writes the next free .bak-retireN.
    bk="$unit.bak-retire1"; i=1
    while [ -e "$bk" ]; do i=$((i + 1)); bk="$unit.bak-retire$i"; done
    if ! _sudo "$unit" cp -p "$unit" "$bk"; then
        echo "STRIP $unit: backup FAILED - unit left as it was"; rm -f "$tmp"; rc=1; continue
    fi
    if ! _sudo "$unit" cp "$tmp" "$unit"; then
        echo "STRIP $unit: edit FAILED - restore from $bk"; rm -f "$tmp"; rc=1; continue
    fi
    rm -f "$tmp"
    left="$(_plan "$unit" /dev/null)"; left="${left%% *}"
    echo "STRIP $unit: removed $n retired line(s): $keys (left ${left:-0}; backup $bk)"
    changed=1
done

if [ "$changed" = "1" ] && [ "$CHECK" = "0" ] && [ -z "${OT_STRIP_NO_RELOAD:-}" ]; then
    sudo -n systemctl daemon-reload && echo "STRIP daemon-reload done" || { echo "STRIP daemon-reload FAILED"; rc=1; }
fi
exit "$rc"
