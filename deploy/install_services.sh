#!/usr/bin/env bash
# deploy/install_services.sh  v5.0
# v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
#
# v1.0  2026-10-24  CD.1 — AN INSTALL LEAVES EVERY SERVICE STOPPED AND THE WAREHOUSE PUSH OFF. The operator,
#       2026-10-24 14:59 ET: "optionsbot and the services need to ship stopped for an install. S3 writing needs to be
#       off until manually turned on"; 15:21 ET, on a start-at-install switch: "starting the bot should be
#       transparent & intuitive, not hidden by some cryptic or occult tag somewhere". So there is no such switch:
#       setup_ec2.sh writes the units and this file leaves them DISABLED and STOPPED (candle-feed included - it
#       used to be enabled and started at install), and applies data capture STANDALONE whatever the bootstrap
#       asked for. A bootstrap's OT_DATA_CAPTURE=managed is RECORDED (~/.optbot/capture.requested) for configure.sh
#       to offer, never applied here. The ONE start is configure.sh's Done (first start: candle-feed, the ramp
#       primer, optionsbot, then data capture as chosen).
#       Sourced by setup_ec2.sh; driven by tests/check_clean_deploy.py through a PATH shim (WA §21: the behaviour,
#       not the source text).
#
# Functions (each prints one line per action, never raises the install):
#   ot_services_installed_stopped SERVICE...   daemon-reload; every SERVICE disabled and stopped
#   ot_capture_install INSTALL_DIR INSTRUMENT REQUESTED
#                                              standalone applied; REQUESTED recorded for configure.sh

OT_CAPTURE_REQUESTED_FILE="${OT_CAPTURE_REQUESTED_FILE:-$HOME/.optbot/capture.requested}"

ot_services_installed_stopped() {
    sudo systemctl daemon-reload
    local s
    for s in "$@"; do
        # a fresh unit is not enabled; a re-install over a running box must not leave it running
        sudo systemctl disable "$s" >/dev/null 2>&1 || true
        if [ "$(systemctl is-active "$s" 2>/dev/null)" = "active" ]; then
            sudo systemctl stop "$s"
        fi
        echo "  service $s: installed, disabled, stopped"
    done
}

ot_capture_install() {
    local install_dir="$1" instrument="$2" requested="${3:-standalone}"
    mkdir -p "$(dirname "$OT_CAPTURE_REQUESTED_FILE")"
    printf '%s\n' "$requested" > "$OT_CAPTURE_REQUESTED_FILE"
    if OT_INSTRUMENT="$instrument" bash "$install_dir/deploy/data_capture.sh" standalone; then
        echo "  data capture: standalone (the warehouse push is OFF until configure.sh turns it on)"
        [ "$requested" = managed ] && \
            echo "  data capture: the bootstrap asked for MANAGED - recorded; configure.sh item 14 + Done applies it"
        return 0
    fi
    echo "  data capture: standalone did NOT fully apply"
    return 1
}
