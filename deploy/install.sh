#!/bin/bash
# ==========================================================================
# deploy/install.sh  v5.0
# v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
# v4.7  2026-10-24  OTV5 r0 — OT_DEFAULT_REPO is TX-9AI/OTV5 (== deploy/origin.conf v1.1).
# v4.6  2026-10-24  CD.1 — the default repository is OT_DEFAULT_REPO, a pinned copy of deploy/origin.conf
#       (this file runs before any clone, so it cannot read it); tests/check_origin.py pins them equal and drives
#       OT_PLAN_ONLY to prove the URL cloned. OT_REPO_URL still overrides.
# v4.5  2026-09-24  OTV4TEST r133 — the banner's right border is padded by printf
#       to one width (it was hand-padded and overshot). No behaviour change.
# v4.4  2026-09-24  OTV4TEST r132 — IT INSTALLS THIS REPO. REPO still named
#       options_trader_v3, the r3.1 'repo pointer' defect inherited a second time:
#       every fresh install from this fork would have deployed v3. Now
#       TX-9AI/OTV4TEST (public — no token needed to clone), overridable with
#       OT_REPO_URL, and OT_GIT_REF (default main) picks what is checked out; the
#       installed commit is printed. Run it through bootstrap.sh (OT_ROLE=control
#       there: this fork's box needs tests/ for the sweep and docs/ for the agent's
#       brief, which the trader-role sparse list excludes).
# v4.3  2026-09-23  OTV4TEST r125 — `shadow` leaves TRADER_DIRS: shadow/ is deleted
#       (LVL.15 step 5, operator "Yep, delete"). A MISSING declared directory is
#       fatal here, so leaving it listed would fail the next install outright.
# v4.2  2026-09-11  OTV4TEST r14 — moved from the repo root to deploy/ (root cleanup); no behaviour change.
# v4.1 (2026-09-07) - r303 / DEP.8. WHAT SHIPS IS DECLARED, WHAT LANDED IS
#   VERIFIED. `docs/` joins `tests/` as control-only. New TRADER_DIRS and
#   _verify_trader: a SHORT checkout is fatal at install time rather than at
#   09:30, and DUPLICATE BASENAMES across levels are reported - the r288
#   signature, and the one thing a sparse allow-list cannot catch, since
#   `data/main.py` lives under a directory that must ship.
#   tools/ is on the list because status.py SHELLS OUT to
#   tools/manifold_health.py by path; no import graph would have found it.
# Installs the bot service on a box.
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
#!/bin/bash
# install.sh — options_trader v3.0 Web Installer
# v1.0 — original release
# updated repo URL to options_trader_v2
# repo-wide v3.0 bump: Yahoo-Finance purge & data stream
#         mapping optimization (single shared TastyTrade candle feed). No
#         logic change in this file.
# REPO POINTER FIX: the clone URL and the documented
#         one-liner still targeted options_trader_v2, so every fresh install
#         from this repo silently deployed v2 code (caught on the QQQ-TEST
#         rebuild, whose banner printed v2.5 — v2's setup_ec2.sh). Now clones
#         options_trader_v3. Display banner v2.0 -> v3.1 (was never bumped).
# Run on a fresh EC2:
#   curl -fsSL https://raw.githubusercontent.com/TX-9AI/OTV5/main/deploy/install.sh -o install.sh && bash install.sh
#   (normally via bootstrap.sh — see bootstrap.example.sh)
# ==========================================================================
set -e

OT_DEFAULT_REPO="TX-9AI/OTV5"              # == deploy/origin.conf OT_ORIGIN_REPO (tests/check_origin.py)
REPO="${OT_REPO_URL:-https://github.com/${OT_DEFAULT_REPO}.git}"
REF="${OT_GIT_REF:-main}"
DEPLOY_DIR="$HOME/options-trader-deploy"

echo ""
# r133 — padded to one width; keep the text ASCII (see setup_ec2.sh box()).
_rule="$(printf '═%.0s' $(seq 1 54))"
echo "╔${_rule}╗"
printf "║ %-52s ║\n" "   OTV5  |  Web Installer  |  install.sh 5.0"
echo "╚${_rule}╝"
echo ""

# r132 — OT_PLAN_ONLY=1: preview what setup_ec2.sh would do, change nothing.
# The clone goes to a throwaway directory and is removed; no apt, no units.
if [ -n "${OT_PLAN_ONLY:-}" ]; then
    command -v git >/dev/null 2>&1 || { echo "  plan needs git on the box (sudo apt-get install -y git)"; exit 1; }
    _plan="$(mktemp -d)"
    git clone -q "$REPO" "$_plan/r" && git -C "$_plan/r" checkout -q "$REF" \
        && bash "$_plan/r/setup_ec2.sh" --plan
    _rc=$?
    rm -rf "$_plan"
    exit $_rc
fi

# Install git if needed
sudo apt-get update -qq
sudo apt-get install -y -qq git

# ---------------------------------------------------------------------------
# DEPLOYMENT BOUNDARY: a TRADER carries only what it needs to trade and collect.
#
#   ships to a box   analysis/ data/ execution/ strategy/ risk/ database/
#                    notifications/ utils/ warehouse/ shadow/ deploy/ main.py
#                    config.py + the install scripts
#   CONTROL ONLY     tests/  - every harness, probe and replay tool
#
# WHY: harnesses read banked tape and trade databases. They never run on a box
# mid-session, and a t2.micro that has already been OOM-KILLED once (SPX, 419 MB)
# should not carry code it cannot use. Observers are the exception and DO ship:
# `shadow/` collects in-session, which is the data a future scorer is earned
# from.
#
# SPARSE CHECKOUT, not a post-pull `rm`. The setting persists in the clone's own
# config, so a box configured once stays correct through every later `git pull`
# in a bake. A cleanup step would have to be remembered by every future deploy
# path - and a manual step that must be remembered never happens.
# ---------------------------------------------------------------------------
# r303 / DEP.8 - WHAT SHIPS IS NOW DECLARED, AND WHAT LANDED IS VERIFIED.
#
# THE SPARSE RULE ALONE WOULD NOT HAVE PREVENTED r288, AND THAT IS THE WHOLE
# REASON THIS FUNCTION GAINED A SIBLING. r288 created TWO strays: a root
# `candle_feed.py` and a `data/main.py`. An allow-list refuses the first,
# because root files are enumerated - and ALLOWS the second, because `data/`
# has to ship. Tightening sparse catches one of two. So the protection that
# matters is `_verify_trader` below, which compares what is ON DISK against
# what is DECLARED.
#
# `docs/` joins `tests/` as control-only: 1.5 MB of prose no box reads, and
# `gen_file_map.py` runs on control.
_sparse_trader() {
    git -C "$1" sparse-checkout init --no-cone 2>/dev/null || return 1
    git -C "$1" sparse-checkout set --no-cone \
        '/*' '!/tests/' '!/docs/' 2>/dev/null || return 1
    return 0
}

# ── THE DECLARED SURFACE ────────────────────────────────────────────────────
# Directories a trader runs from. Derived from the ACTUAL import closure of the
# five box entry points (main.py, data/candle_feed.py, data/candle_logger.py,
# warehouse/s3_push.py, shadow/observer.py) plus the operator CLIs the fleet
# menu invokes (status.py, query.py, debug_status.py).
#
# 🔴 `tools/` IS ON THIS LIST AND NO IMPORT GRAPH WOULD HAVE PUT IT THERE.
# `status.py:491` SHELLS OUT to `tools/manifold_health.py` by path. A closure
# computed from imports alone omits it, and the manifold rollup breaks on every
# box - quietly, because the box still trades. Subprocess edges are invisible
# to the thing that would otherwise generate this list, which is exactly why it
# is written down rather than derived.
TRADER_DIRS="analysis data database deploy derived execution notifications risk strategy tools utils warehouse"

# ── VERIFY WHAT LANDED, NOT WHAT WE ASKED FOR ───────────────────────────────
# ⚠️ THE FAILURE MODES ARE ASYMMETRIC AND ONLY ONE OF THEM IS LOUD. Shipping
# something extra wastes disk. Shipping something SHORT means a box cannot
# trade, and it does not surface until 09:30. So this refuses to be silent in
# either direction: a MISSING declared directory is fatal, and an UNEXPECTED
# top-level file or a DUPLICATE BASENAME is reported.
#
# 🔴 THE DUPLICATE-BASENAME TEST IS THE r288 DETECTOR. `data/main.py` beside
# `main.py` is the signature of an archive whose paths were built at the wrong
# level, and it is the one an allow-list cannot catch. It is also what the
# file map's orphan report missed, because `gen_file_map.py` falls back to
# matching a BASENAME against its entry-point list (DEP.10).
_verify_trader() {
    local d="$1" missing="" rc=0
    for p in $TRADER_DIRS; do
        [ -d "$d/$p" ] || missing="$missing $p"
    done
    [ -f "$d/main.py" ]   || missing="$missing main.py"
    [ -f "$d/config.py" ] || missing="$missing config.py"
    if [ -n "$missing" ]; then
        echo "  🔴 CHECKOUT IS SHORT - missing:$missing"
        echo "     This box CANNOT TRADE. Do not start it."
        rc=1
    fi
    # Duplicate basenames across levels - the r288 signature.
    # ⚠️ `__init__.py` IS EXCLUDED BY CONSTRUCTION, NOT BY TUNING. It is a
    # package marker - every package has one, so "duplicate basename" is
    # meaningless for it and a check that flags it fires on EVERY tree. These
    # markers have been in place since otv1 and are integral; nothing here
    # proposes touching them.
    # ⚠️ `registry.py` IS A DECLARED, LEGITIMATE DUPLICATE: `derived/registry.py`
    # and `shadow/registry.py` are two different modules that happen to share a
    # name. It is NAMED here rather than the check being loosened, so a THIRD
    # copy appearing still trips - and so the next reader can see which
    # duplicates were examined and accepted rather than guessing.
    # 🔑 A NEW ENTRY HERE IS A DECISION, NOT A CHORE. If this list grows without
    # anyone looking, the check has quietly become decorative - which is the
    # CV.1 failure it exists to avoid.
    local KNOWN_DUPES="registry.py"
    local dupes
    dupes="$(cd "$d" && find . -name '*.py' -not -path './.git/*' \
             -not -path './tests/*' -not -name '__init__.py' \
             -printf '%f\n' 2>/dev/null | sort | uniq -d \
             | grep -vxF "$KNOWN_DUPES" | tr '\n' ' ')"
    if [ -n "$dupes" ]; then
        echo "  ⚠️  DUPLICATE FILENAMES AT DIFFERENT LEVELS: $dupes"
        echo "     This is the r288 signature - an archive built at the wrong"
        echo "     level creates a copy beside the real file. Investigate"
        echo "     before baking; one of them is not the file being run."
    fi
    return $rc
}

if [ -d "$DEPLOY_DIR/.git" ]; then
    echo "  Updating existing repo..."
    cd "$DEPLOY_DIR" && git pull
else
    echo "  Cloning repository..."
    git clone "$REPO" "$DEPLOY_DIR"
fi
# r132 — the ref the operator asked for, and say which commit that is.
git -C "$DEPLOY_DIR" checkout -q "$REF"
export OT_GIT_REF="$REF" OT_REPO_URL="$REPO"
echo "  Installing $(git -C "$DEPLOY_DIR" log -1 --format='%h %ad' --date=short) ($REF) from $REPO"

if [ "${OT_ROLE:-trader}" = "trader" ]; then
    if _sparse_trader "$DEPLOY_DIR"; then
        echo "  Sparse checkout: tests/ and docs/ excluded (trader role)."
        _verify_trader "$DEPLOY_DIR" || exit 1
    else
        # ⚠️ FAIL LOUD, NOT SILENT. A box that quietly keeps tests/ is only
        # wasting disk - but a box whose sparse config half-applied may be
        # MISSING RUNTIME PATHS, and that does not surface until it tries to
        # trade. Say so at install time rather than at 09:30.
        echo "  WARNING: sparse checkout FAILED - this box carries the full repo."
        echo "           Verify runtime paths are present before it trades."
    fi
else
    echo "  Role=${OT_ROLE}: full checkout (control keeps tests/)."
fi

echo "  Repository ready."
echo ""

# Run setup from the deploy dir
chmod +x "$DEPLOY_DIR/setup_ec2.sh"
bash "$DEPLOY_DIR/setup_ec2.sh"
