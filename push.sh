#!/bin/bash
# push.sh — v1.0 (repo root)
# v1.0 (2026-10-03) — OTV4TEST r201 (CTL.1). A ROOT SHIM FOR CONTROL. day_trader_pro calls
#   `bash ~/options-trader/push.sh` (fleet.py / eod_backfill.py); r14 moved the script to
#   deploy/ and nothing was left at the path control uses, so the call would fail on any box
#   running this tree (latent: never yet run against SOFI or AAL). This forwards every
#   argument to deploy/push.sh, which finds the checkout by itself. The script's logic stays
#   in ONE place; do not add any here.
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/deploy/push.sh" "$@"
