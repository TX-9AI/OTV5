#!/bin/bash
# ==========================================================================
# setup_ec2.sh  v4.12
# v4.12 2026-10-24  OTV5 r0 — the interactive repository prompt's format hint shows the deploy/origin.conf
#       repository, not a literal of one repository's name.
# v4.11 2026-10-24  CD.1 — AN INSTALL STARTS NOTHING AND PUSHES NOTHING. The operator, 2026-10-24: "optionsbot
#       and the services need to ship stopped for an install. S3 writing needs to be off until manually turned
#       on"; on a start-at-install switch: "starting the bot should be transparent & intuitive, not hidden by
#       some cryptic or occult tag". candle-feed is no longer enabled or started here and OT_START_BOT is GONE:
#       deploy/install_services.sh leaves candle-feed and the bot installed, DISABLED and STOPPED, and applies
#       data capture STANDALONE whatever OT_DATA_CAPTURE says (a managed request is recorded in
#       ~/.optbot/capture.requested for configure.sh). The one start is configure.sh's Done: candle-feed, the
#       ramp primer (tools/prime_ramp.py), the bot, then data capture as chosen. --plan prints
#       data_capture=standalone, data_capture_requested=<bootstrap> and first_start. Gate:
#       tests/check_clean_deploy.py (drives install_services.sh under a PATH shim).
# v4.10 2026-09-29  OTV4TEST r175 (SYM.1) — AN UNLISTED OT_INSTRUMENT STOPS THE
#       INSTALL AT STEP 1, NAMED. The bootstrap's symbol used to install and
#       run on a silent $1 strike step; now it must be a key of
#       config.STRIKE_INCREMENTS (read from this repo's config.py with the
#       system python3 and NO import - a fresh box has no venv yet).
# v4.9  2026-09-27  OTV4TEST r168 (EXP.1 item 3) — THE SUITE INSTALLS THE EMERGENCY
#       WATCHDOG (deploy/install_emergency_watchdog.sh), so a fresh box has it
#       as this one does. It copies nothing from the bot unit: it reads it live.
# v4.8  2026-09-27  OTV4TEST r161 (SIZE.2) — THE RAMP START IS RISK PER TRADE, AND
#       THE THREE SCALING SWITCHES ARE PRIMED. The operator: "Merge it. that was
#       always the intent." OT_ORB_RISK_USD is no longer written (config.py no
#       longer reads it); OT_SCALE_ORB / OT_SCALE_BREAKOUT / OT_SCALE_VOLT are,
#       default 1 (on) as config.py defaults them, so a fresh box sizes exactly as
#       this one does until the operator switches one off in configure.sh.
# v4.7  2026-09-25  OTV4TEST r138 — THE BOT IS INSTALLED, NOT STARTED. Operator: "the
#       options bot service should be defaulted to not started", "when I set all
#       the variables in configure and exit out of the menu that resets everything
#       and starts it". optionsbot is written and daemon-reloaded but neither
#       ENABLED nor STARTED; configure.sh's Done enables and starts it. The candle
#       feed still starts, so the tape warms up meanwhile. OT_START_BOT=1 restores
#       the old start-at-install for a fully unattended box. Found the same night:
#       the SOFI box went managed from a shell still carrying the bootstrap's
#       OT_INSTRUMENT=QQQ after item 1 moved the unit to SOFI - the bot must not
#       run on a box whose setup is not finished.
# v4.6  2026-09-24  OTV4TEST r136 — DATA CAPTURE IS A MODE, NOT A HARD-CODED MASK.
#       OT_DATA_CAPTURE=standalone (default, the reference box's shape) or
#       managed (the day_trader_pro conductor owns the box's data), applied by
#       deploy/data_capture.sh - the same script configure.sh item 10 runs.
#       This used to mask s3-push unconditionally. Two system packages join the
#       apt list, both found testing the conductor's menu against this fork:
#       python3-boto3 (s3-push and the conductor's `--verify` run under
#       /usr/bin/python3, which had no boto3 on a fresh box) and tzdata-legacy
#       (Ubuntu 26.04 moved `US/Eastern` out of tzdata; the conductor runs
#       `python status.py` / `python query.py --decisions` with the SYSTEM
#       python, and both died with ZoneInfoNotFoundError - measured on the
#       reference box; the venv never noticed because it ships its own tzdata).
# v4.5  2026-09-24  OTV4TEST r134 — EVERY FRESH BOX STARTED WITH A DIRTY TREE. The
#       install chmod'ed analysis/get_orb_range.py, which git tracks as 100644, so
#       `git status` read ` M analysis/get_orb_range.py` from minute one (found by
#       the first fresh box's agent). The chmod was also dead: main.py runs the
#       script as `sys.executable <script>`, so its exec bit is never used.
#       Removed. Every *.sh is 100755 in the index, so the *.sh chmod stays clean.
# v4.4  2026-09-24  OTV4TEST r133 — COSMETIC, FROM THE FIRST PROVING RUN'S SCREEN.
#       The operator, on the banner: "can you also fix that little alignment thing".
#       Banners are drawn by box(), which pads every line to one width (the right
#       border was hand-padded and landed wherever the text ended; the Setup
#       Complete box also carried a double-width emoji). The banner said
#       "options_trader v3.0" - VERSION now tracks this file (4.4) and the name is
#       OTV4TEST; Vertigo Capital stays. The instrument is the configured one, not
#       a hardcoded "QQQ/SPX". Step 4's "Enter the GitHub repo ... Press ENTER to
#       skip" is printed only when it will actually ask. No behaviour change.
# v4.3  2026-09-24  OTV4TEST r132 — THE UNATTENDED INSTALL BUILDS THE WHOLE BOX.
#       Operator: "make sure that I can do a boot strap install of this repo onto
#       a fresh instance using unattended install with pre-seeded boot strap file",
#       "The entire Suite. The timers, the diagnostics, the menus full capability
#       out of the box", "freeze every software version", "we want a swap file as
#       part of the installer", and a toggle for whether Claude comes up at first
#       boot. WHAT CHANGED, each measured against the reference box (qqq-test):
#       (1) NO TTY IS NOT FATAL. `exec < /dev/tty` ran unconditionally under
#       `set -e`, so any caller without a terminal (cloud-init user-data, a CI
#       runner, this file's own gate) died on line 61. It reattaches a terminal
#       only when one exists, and refuses clearly when there is neither a
#       terminal nor pre-seeded credentials. (2) `--plan` resolves every setting
#       and every step, prints them as `PLAN key=value`, and exits BEFORE ANY
#       SYSTEM CHANGE — the operator's preview and the gate's handle.
#       (3) SWAP: a /swapfile of OT_SWAP_GB (default 2) when the box has none —
#       the reference box has run on a 2G swapfile made by hand. (4) PINNED:
#       requirements.lock (the reference venv, 41 packages, Python 3.14) is
#       installed when present, with no pip upgrade and no silent fallback to the
#       floors; a pin that fails stops the install. (5) THE FOUR KEYS configure.sh
#       grew after v3 are PRIMED: OT_ORB_RISK_USD, OT_ORB_BUDGET_USD,
#       OT_DAILY_LOSS_LIMIT (all default to the base risk, as config.py does) and
#       OT_PIN_PROXIMITY_ACTIVE=0 — config.py defaults the gate ON, and the
#       operator turned it OFF 2026-09-24 pending data (PIN.1), so an unprimed box
#       would have run the gate he switched off. (6) GIT: fetch failures were
#       `|| true` — silent. Now OT_GIT_REF is fetched and checked out or the
#       install says loudly that the tree is not a checkout. OT_GIT_PUSH (default
#       0) decides whether the box can push: 1 stores GITHUB_TOKEN for git over
#       HTTPS; 0 sets a push URL that fails by name. (7) THE SUITE: midnight-halt,
#       retention-purge, open-scan, boot-sweep, s3-push MASKED (the mainline box
#       owns that prefix), Claude pinned with its own login (deploy/install_claude.sh),
#       and the claude-boot unit only when OT_CLAUDE_AT_BOOT=1 — "Installed yes but
#       running on first boot not necessarily." (8) Every secret variable is unset
#       before the final login shell, which used to inherit them all.
# v4.2  2026-09-17  OTV4TEST r34 — the three operator scripts moved back to the repo root (configure.sh, status.py, query.py); this file's reference re-pointed. No behaviour change. The printed hints name the root paths again.
# v4.1
# v4.1  2026-09-11  OTV4TEST r14 — the helper scripts it names live in deploy/ and the
#       readers in tools/ (root cleanup); harden_hosts.sh is called from deploy/.
# EC2 instance provisioning for a fleet box.
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
# setup_ec2.sh — options_trader v3.0 EC2 Setup
# v1.0 — original release
# QQQ/SPX banner, Telegram only, VERSION=2.0
# auto git init on fresh install
# git branch -M main on init
# GitHub token prompt, added to systemd service
# cleanup deploy dir + install.sh before dropping to shell
# unattended install: if credentials are already in the env
#          (from bootstrap.sh) skip all prompts; shred the bootstrap in cleanup;
#          set git author to the repo owner instead of the ubuntu system user
# remove the paper-trading and risk prompts entirely. Installs
#          are ALWAYS paper; risk defaults to \$200. Both set later via configure.sh
# fix unattended installs wiping GITHUB_REPO/GITHUB_TOKEN
#          before git-init, which left the repo with no 'origin' remote
# GitHub repo prompt, token only required if repo provided
# strip full URL/protocol from GITHUB_REPO input to prevent
#         doubled "https://github.com/https://github.com/..." remote URLs
#         if the operator pastes a full URL instead of "owner/repo"
# chmod +x moved to after git reset --hard so git never
#         strips execute bits; now covers all .sh files recursively
# call harden_hosts.sh during setup: block needrestart from
#         auto-restarting optionsbot after package upgrades, and move the
#         apt-daily/apt-daily-upgrade timers out of RTH (Persistent=false).
#         Fixes mid-session restarts caused by unattended-upgrades -> needrestart.
# YAHOO-FINANCE PURGE / data stream mapping optimization
#         (repo v3.0): drop the legacy Yahoo data dep from pip installs; install + enable the new
#         candle-feed.service (data/candle_feed.py — the box's ONLY DXFeed
#         subscription); order optionsbot After=/Wants= candle-feed.service and
#         start the feed first so the store is warm before the bot reads it.
# QQQ/SPX 0DTE | TastyTrade OAuth | Telegram alerts
# ==========================================================================
set -e
export DEBIAN_FRONTEND=noninteractive
export TERM=xterm-256color

INSTALL_DIR="$HOME/options-trader"
DEPLOY_DIR="$HOME/options-trader-deploy"
SERVICE_NAME="optionsbot"
VENV="$INSTALL_DIR/venv"
VERSION="4.4"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAN=0
[ "${1:-}" = "--plan" ] && PLAN=1

# 🔴 r132 — REATTACH A TERMINAL ONLY WHEN ONE EXISTS. The probe opens /dev/tty in a
# subshell: with no controlling terminal it fails there, not in this shell, where
# a failed `exec` redirection under `set -e` would end the install.
HAVE_TTY=0
if [ -t 0 ]; then
    HAVE_TTY=1
elif [ "$PLAN" = 0 ] && ( : < /dev/tty ) 2>/dev/null; then
    exec < /dev/tty
    HAVE_TTY=1
fi

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
RED='\033[0;31m'; BOLD='\033[1m'; RESET='\033[0m'

print_step() { echo -e "\n${BOLD}${GREEN}[ $1 ]${RESET} $2"; }
print_ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
print_info() { echo -e "  ${CYAN}→${RESET}  $1"; }
print_warn() { echo -e "  ${YELLOW}⚠${RESET}  $1"; }
# r133 — every banner line is padded to ONE width by printf, so the right border
# lines up. ⚠️ KEEP THE TEXT INSIDE A BOX ASCII: a multibyte or double-width glyph
# (✅, —, →) pads by bytes in some locales and by cells in others.
BOX_W=52
box() {
    local color="$1"; shift
    local rule ln
    rule="$(printf '═%.0s' $(seq 1 $((BOX_W + 2))))"
    echo -e "${BOLD}${color}╔${rule}╗${RESET}"
    for ln in "$@"; do
        printf "${BOLD}${color}║ %-${BOX_W}s ║${RESET}\n" "$ln"
    done
    echo -e "${BOLD}${color}╚${rule}╝${RESET}"
}
ask()        { local -n __v="$2"; [ -n "$__v" ] || read -rp "    $1: " "$2"; }
ask_secret() { local -n __v="$2"; [ -n "$__v" ] || { read -rsp "    $1 (paste, then ENTER): " "$2"; echo ""; }; }
ask_yn()     {
    while true; do
        read -rp "    $1 [y/n]: " yn
        case "$yn" in [Yy]) return 0;; [Nn]) return 1;; esac
    done
}

echo ""
box "$CYAN" "   OTV4TEST v${VERSION}  |  Vertigo Capital" \
           "   ${OT_INSTRUMENT:-QQQ} 0DTE  |  TastyTrade  |  Telegram"
echo ""
echo "  Have ready:"
echo "    - TastyTrade Client Secret"
echo "    - TastyTrade Refresh Token"
echo "    - TastyTrade Account Number (e.g. 5WT12345)"
echo "    - Telegram Bot Token & Chat ID"
echo "    - GitHub Personal Access Token"
echo ""
# ── Unattended install detection ──────────────────────────────────────────────
# If a bootstrap.sh already exported the credentials into the environment, skip
# every interactive prompt and install hands-free.
UNATTENDED=false
if [ -n "$TT_CLIENT_SECRET" ] && [ -n "$TT_REFRESH_TOKEN" ] && [ -n "$TT_ACCOUNT_NUMBER" ]; then
    UNATTENDED=true
    print_ok "Credentials found in environment — unattended install, prompts skipped."
fi
if [ "$UNATTENDED" = false ] && [ "$HAVE_TTY" = 0 ] && [ "$PLAN" = 0 ]; then
    echo "  🔴 No credentials in the environment and no terminal to ask for them."
    echo "     Run through bootstrap.sh (see bootstrap.example.sh), or from an SSH session."
    exit 1
fi

[ "$UNATTENDED" = true ] || [ "$PLAN" = 1 ] || read -rp "  Press ENTER to continue or Ctrl+C to cancel..."

# ─── STEP 1: TRADING MODE ────────────────────────────────────────────────────
print_step "1/8" "Trading Mode"
echo ""
# No prompts here. Installs are ALWAYS paper with sane defaults; risk, mode
# (paper/live), and instrument are set afterward via configure.sh.
INSTRUMENT="${OT_INSTRUMENT:-QQQ}"
RISK_USD="${OT_RISK_USD:-200}"
PAPER_TRADING="True"
# r132 — the keys configure.sh grew after v3, primed so a fresh box shows values
# the operator chose. Defaults match config.py's, EXCEPT the pin gate: config.py
# defaults it ON and the operator ruled it OFF on 2026-09-24 (PIN.1).
SCALE_ORB="${OT_SCALE_ORB:-1}"                  # r161 — configure.sh items 9-11
SCALE_BREAKOUT="${OT_SCALE_BREAKOUT:-1}"
SCALE_VOLT="${OT_SCALE_VOLT:-1}"
ORB_BUDGET_USD="${OT_ORB_BUDGET_USD:-$RISK_USD}"
DAILY_LOSS_LIMIT="${OT_DAILY_LOSS_LIMIT:-$RISK_USD}"
PIN_GATE="${OT_PIN_PROXIMITY_ACTIVE:-0}"
SWAP_GB="${OT_SWAP_GB:-2}"
CLAUDE_AT_BOOT="${OT_CLAUDE_AT_BOOT:-0}"
DATA_CAPTURE="${OT_DATA_CAPTURE:-standalone}"
case "$DATA_CAPTURE" in managed|standalone) ;; *)
    echo "  🔴 OT_DATA_CAPTURE must be 'managed' or 'standalone', got '$DATA_CAPTURE'."; exit 1 ;; esac
GIT_PUSH="${OT_GIT_PUSH:-0}"
GIT_REF="${OT_GIT_REF:-main}"

# r175 (SYM.1) — the symbol must be on the list. Parsed, never imported.
if ! python3 - "$SRC_DIR/config.py" "$INSTRUMENT" <<'PYEOF'
import ast, re, sys
src = open(sys.argv[1]).read()
m = re.search(r"^STRIKE_INCREMENTS = (\{.*?\n\})", src, re.S | re.M)
sys.exit(0 if m and sys.argv[2] in ast.literal_eval(m.group(1)) else 1)
PYEOF
then
    echo "  🔴 OT_INSTRUMENT=${INSTRUMENT} is not a listed symbol (config.STRIKE_INCREMENTS)."
    echo "     Set a listed one in bootstrap.sh, or add it with its measured strike step."
    exit 1
fi
print_ok "Defaults: ${INSTRUMENT} | \$${RISK_USD}/trade | PAPER"
print_info "Change risk, mode (paper/live), and instrument anytime via configure.sh"

# ─── STEP 2: TASTYTRADE CREDENTIALS ─────────────────────────────────────────
print_step "2/8" "TastyTrade OAuth Credentials"
echo ""
echo -e "  ${BOLD}How to get credentials (2 min):${RESET}"
echo -e "  1. my.tastytrade.com → Manage → API → OAuth Applications"
echo -e "  2. New OAuth Application → all scopes → Create → ${BOLD}save Client Secret${RESET}"
echo -e "  3. Inside app → New Personal OAuth Grant → all scopes → ${BOLD}save Refresh Token${RESET}"
echo -e "  4. Account Number is on the main account page (e.g. 5WT12345)"
echo ""
[ "$UNATTENDED" = true ] || read -rp "    Press ENTER when ready..."
echo ""

while true; do
    ask_secret "Client Secret" TT_CLIENT_SECRET
    [[ -n "$TT_CLIENT_SECRET" ]] && break
    print_warn "Cannot be empty."
done
while true; do
    ask_secret "Refresh Token" TT_REFRESH_TOKEN
    [[ -n "$TT_REFRESH_TOKEN" ]] && break
    print_warn "Cannot be empty."
done
while true; do
    ask "Account Number (e.g. 5WT12345)" TT_ACCOUNT_NUMBER
    [[ -n "$TT_ACCOUNT_NUMBER" ]] && break
    print_warn "Cannot be empty."
done
print_ok "TastyTrade credentials accepted."

# ─── STEP 3: TELEGRAM ────────────────────────────────────────────────────────
print_step "3/8" "Telegram Alerts"
echo ""
while true; do
    ask_secret "Telegram Bot Token" TELEGRAM_TOKEN
    [[ -n "$TELEGRAM_TOKEN" ]] && break
    print_warn "Cannot be empty."
done
while true; do
    ask "Telegram Chat ID" TELEGRAM_CHAT_ID
    [[ -n "$TELEGRAM_CHAT_ID" ]] && break
    print_warn "Cannot be empty."
done
print_ok "Telegram configured."

# ─── STEP 4: GITHUB REPO & TOKEN ────────────────────────────────────────────
print_step "4/8" "GitHub Repository (optional)"
if [ "$UNATTENDED" = false ]; then
    echo ""
    echo -e "  Enter the GitHub repo to link this server to for push.sh."
    echo -e "  Format: $( . "$SRC_DIR/deploy/origin.conf" && echo "$OT_ORIGIN_REPO" )   (the deploy/origin.conf repository)"
    echo -e "  (Full URLs are also accepted and will be normalized automatically)"
    echo -e "  Press ENTER to skip."
    echo ""
fi
# In unattended mode, KEEP the GITHUB_REPO / GITHUB_TOKEN the bootstrap exported.
# Only blank + prompt for them in an interactive install (otherwise we'd wipe the
# env values and skip `git remote add origin`, leaving the repo with no remote).
if [ "$UNATTENDED" = false ]; then
    GITHUB_REPO=""
    GITHUB_TOKEN=""
    printf "    GitHub repo [ENTER to skip]: "; read -r GITHUB_REPO
fi

# ── Normalize GITHUB_REPO: strip protocol, host, trailing .git/slash ─────────
# Accepts any of:
#   TX-9AI/options_trader_v3
#   https://github.com/TX-9AI/options_trader_v3
#   https://github.com/TX-9AI/options_trader_v3.git
#   github.com/TX-9AI/options_trader_v3
# Always normalizes to: TX-9AI/options_trader_v3
if [[ -n "$GITHUB_REPO" ]]; then
    GITHUB_REPO="${GITHUB_REPO#https://}"
    GITHUB_REPO="${GITHUB_REPO#http://}"
    GITHUB_REPO="${GITHUB_REPO#github.com/}"
    GITHUB_REPO="${GITHUB_REPO%.git}"
    GITHUB_REPO="${GITHUB_REPO%/}"
fi

# r132 — the repo is public: an UNATTENDED install never stops for a token. With
# none, push.sh has nothing to use and OT_GIT_PUSH cannot enable pushing.
if [[ -n "$GITHUB_REPO" ]] && [ "$UNATTENDED" = true ]; then
    [[ -n "$GITHUB_TOKEN" ]] && print_ok "GitHub token provided." || print_ok "No GitHub token — clone/pull only."
elif [[ -n "$GITHUB_REPO" ]]; then
    echo ""
    echo -e "  Get token from: github.com → Settings → Developer settings → Tokens (classic)"
    echo ""
    while true; do
        ask_secret "GitHub Personal Access Token" GITHUB_TOKEN
        [[ -n "$GITHUB_TOKEN" ]] && break
        print_warn "Cannot be empty."
    done
    print_ok "GitHub repo: https://github.com/${GITHUB_REPO}"
    print_ok "GitHub token accepted."
else
    print_ok "Skipping GitHub — push.sh will prompt for token when needed."
fi
# r132 — every box is a checkout of SOME repo; this fork unless told otherwise.
# CD.1 — the default is deploy/origin.conf, the one place this tree names its repository
[ -n "${GITHUB_REPO:-}" ] || GITHUB_REPO="$( . "$SRC_DIR/deploy/origin.conf" && echo "$OT_ORIGIN_REPO" )"

# The suite, in install order. Each is run with `bash`, so a lost exec bit
# cannot stop it, and one failure is reported rather than ending the install.
SUITE="deploy/harden_hosts.sh deploy/install_midnight_halt.sh deploy/install_retention_purge_timer.sh deploy/install_open_scan_timer.sh deploy/install_boot_sweep.sh deploy/install_emergency_watchdog.sh deploy/install_claude.sh"
[ "$CLAUDE_AT_BOOT" = 1 ] && SUITE="$SUITE deploy/install_claude_boot.sh"
REQ_FILE="requirements.lock"
[ -f "$SRC_DIR/$REQ_FILE" ] || REQ_FILE="requirements.txt"

# ─── r132 — --plan: EVERYTHING RESOLVED, NOTHING CHANGED ────────────────────
if [ "$PLAN" = 1 ]; then
    echo "PLAN unattended=$UNATTENDED"
    echo "PLAN tty=$HAVE_TTY"
    echo "PLAN instrument=$INSTRUMENT"
    echo "PLAN paper=$PAPER_TRADING"
    echo "PLAN risk_usd=$RISK_USD"
    echo "PLAN scale_orb=$SCALE_ORB"
    echo "PLAN scale_breakout=$SCALE_BREAKOUT"
    echo "PLAN scale_volt=$SCALE_VOLT"
    echo "PLAN orb_budget_usd=$ORB_BUDGET_USD"
    echo "PLAN daily_loss_limit=$DAILY_LOSS_LIMIT"
    echo "PLAN pin_gate=$PIN_GATE"
    echo "PLAN swap_gb=$SWAP_GB"
    echo "PLAN requirements=$REQ_FILE"
    echo "PLAN git_repo=$GITHUB_REPO"
    echo "PLAN git_ref=$GIT_REF"
    echo "PLAN git_push=$GIT_PUSH"
    echo "PLAN claude_at_boot=$CLAUDE_AT_BOOT"
    echo "PLAN first_start=configure.sh Done (candle-feed, ramp primer, optionsbot, then data capture)"
    echo "PLAN claude_login=$([ -n "${CLAUDE_LOGIN_B64:-}" ] && echo provided || echo absent)"
    echo "PLAN units=candle-feed optionsbot"
    echo "PLAN data_capture=standalone"
    echo "PLAN data_capture_requested=$DATA_CAPTURE"
    for f in $SUITE; do
        echo "PLAN suite=$f present=$([ -f "$SRC_DIR/$f" ] && echo yes || echo NO)"
    done
    exit 0
fi

# ─── STEP 5: SYSTEM PACKAGES ─────────────────────────────────────────────────
print_step "5/8" "System packages"
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv python-is-python3 git rsync bc sqlite3 tmux curl ca-certificates python3-boto3 tzdata-legacy
print_ok "System packages ready."
# r132 — the lock was frozen on the reference box; say so when this one differs.
. /etc/os-release 2>/dev/null || true
PYV="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if [ "${VERSION_ID:-}" != "26.04" ] || [ "$PYV" != "3.14" ]; then
    print_warn "Reference box is Ubuntu 26.04 / Python 3.14; this is ${VERSION_ID:-?} / $PYV — pins may not resolve."
fi

# ── r132 — SWAP ─────────────────────────────────────────────────────────────
if [ "$SWAP_GB" -gt 0 ] 2>/dev/null && [ -z "$(swapon --show --noheadings)" ]; then
    sudo fallocate -l "${SWAP_GB}G" /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile >/dev/null
    sudo swapon /swapfile
    grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
    print_ok "Swap: ${SWAP_GB}G /swapfile, on and in fstab."
else
    print_ok "Swap: $(swapon --show --noheadings | awk '{print $1" "$3}' | head -1 || true) (left as is)"
fi

# ─── STEP 6: INSTALL FILES ───────────────────────────────────────────────────
print_step "6/8" "Installing bot files"
mkdir -p "$INSTALL_DIR"
rsync -a \
    --exclude='.git' \
    --exclude='*.pem' \
    --exclude='*.bat' \
    --exclude='credentials.py' \
    --exclude='venv' \
    --exclude='trades.db' \
    --exclude='trades.db-shm' \
    --exclude='trades.db-wal' \
    --exclude='bot.log' \
    --exclude='__pycache__' \
    "$DEPLOY_DIR/" "$INSTALL_DIR/"

for f in main.py config.py requirements.txt; do
    [ -f "$INSTALL_DIR/$f" ] || { echo "ERROR: $f missing. Aborting."; exit 1; }
done
print_ok "Files installed to ${INSTALL_DIR}"

# ─── STEP 7: PYTHON ENVIRONMENT ──────────────────────────────────────────────
print_step "7/8" "Python environment"
python3 -m venv "$VENV"
source "$VENV/bin/activate"
# r132 — PINNED. No pip upgrade (that is a version change too) and no fallback to
# the floors when a pin fails: a box that differs from the reference is the
# "weird one-off problem" the freeze exists to prevent.
if ! pip install -r "$INSTALL_DIR/$REQ_FILE" -q; then
    echo "  🔴 pip could not install $REQ_FILE — stopping. Nothing is running yet."
    exit 1
fi
print_ok "Dependencies installed from $REQ_FILE."

grep -q "options-trader/venv" ~/.bashrc || echo "source $VENV/bin/activate" >> ~/.bashrc
grep -q "cd ~/options-trader"  ~/.bashrc || echo "cd $INSTALL_DIR"           >> ~/.bashrc

# ─── STEP 8: SYSTEMD SERVICES ────────────────────────────────────────────────
print_step "8/8" "Configuring systemd services (candle-feed + bot)"

# The candle feed owns the box's ONLY DXFeed subscription. Every other process
# (bot, shadow observer, candle logger) reads its SQLite store. It must be up
# before the bot, and it must restart independently.
sudo tee /etc/systemd/system/candle-feed.service > /dev/null << FEEDEOF
[Unit]
Description=options_trader v${VERSION} — single TastyTrade candle feed (DXFeed producer)
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${INSTALL_DIR}
Environment=OT_INSTRUMENT=${INSTRUMENT}
Environment=TT_CLIENT_SECRET=${TT_CLIENT_SECRET}
Environment=TT_REFRESH_TOKEN=${TT_REFRESH_TOKEN}
Environment=TT_ACCOUNT_NUMBER=${TT_ACCOUNT_NUMBER}
ExecStart=${VENV}/bin/python -m data.candle_feed
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=candle-feed

[Install]
WantedBy=multi-user.target
FEEDEOF
sudo chmod 600 /etc/systemd/system/candle-feed.service

sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << SVCEOF
[Unit]
Description=options_trader v${VERSION} — QQQ/SPX 0DTE | Vertigo Capital
After=network.target candle-feed.service
Wants=candle-feed.service

[Service]
Type=simple
User=${USER}
WorkingDirectory=${INSTALL_DIR}
Environment=OT_INSTRUMENT=${INSTRUMENT}
Environment=OT_RISK_USD=${RISK_USD}
Environment=OT_PAPER_TRADING=${PAPER_TRADING}
Environment=OT_BOT_NAME=OptionsTrader-${INSTRUMENT}
Environment=TT_CLIENT_SECRET=${TT_CLIENT_SECRET}
Environment=TT_REFRESH_TOKEN=${TT_REFRESH_TOKEN}
Environment=TT_ACCOUNT_NUMBER=${TT_ACCOUNT_NUMBER}
Environment=TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
Environment=TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
Environment=GITHUB_TOKEN=${GITHUB_TOKEN}
Environment=GITHUB_REPO=${GITHUB_REPO}
Environment=OT_SCALE_ORB=${SCALE_ORB}
Environment=OT_SCALE_BREAKOUT=${SCALE_BREAKOUT}
Environment=OT_SCALE_VOLT=${SCALE_VOLT}
Environment=OT_ORB_BUDGET_USD=${ORB_BUDGET_USD}
Environment=OT_DAILY_LOSS_LIMIT=${DAILY_LOSS_LIMIT}
Environment=OT_PIN_PROXIMITY_ACTIVE=${PIN_GATE}
ExecStartPre=/bin/bash -c 'touch ${INSTALL_DIR}/bot.log ${INSTALL_DIR}/trades.db && chown ${USER}:${USER} ${INSTALL_DIR}/bot.log ${INSTALL_DIR}/trades.db'
ExecStart=${VENV}/bin/python main.py --service
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

[Install]
WantedBy=multi-user.target
SVCEOF

sudo chmod 600 /etc/systemd/system/${SERVICE_NAME}.service
# CD.1 — every service ships DISABLED and STOPPED (candle-feed too). The one start is configure.sh's Done.
. "$INSTALL_DIR/deploy/install_services.sh"
ot_services_installed_stopped candle-feed ${SERVICE_NAME}

touch "$INSTALL_DIR/bot.log" "$INSTALL_DIR/trades.db"
chown "${USER}:${USER}" "$INSTALL_DIR/bot.log" "$INSTALL_DIR/trades.db"
INSTALL_FAILED=""

# ── Git init — repo-ready on every fresh install ─────────────────────────────
cd "$INSTALL_DIR"
if [ ! -d ".git" ]; then
    git init -q
    git branch -M main 2>/dev/null || git checkout -b main 2>/dev/null || true
    git remote add origin "https://github.com/${GITHUB_REPO}.git"
    # Author commits as the repo owner (e.g. TX-9AI), not the ubuntu user
    GH_OWNER="${GITHUB_REPO%%/*}"
    git config user.name  "$GH_OWNER"
    git config user.email "${GH_OWNER}@users.noreply.github.com"
    # 🔴 r132 — NOT `|| true`. A tree that is not a checkout cannot be baked.
    if git fetch -q origin && { git reset -q --hard "origin/$GIT_REF" 2>/dev/null || git reset -q --hard "$GIT_REF"; }; then
        git branch -q -u origin/main main 2>/dev/null || true
        print_ok "Git: $(git log -1 --format='%h %s' | cut -c1-70)"
    else
        print_warn "🔴 GIT FETCH/CHECKOUT FAILED — ${INSTALL_DIR} is NOT a checkout of ${GITHUB_REPO} ${GIT_REF}."
        INSTALL_FAILED="$INSTALL_FAILED git"
    fi
fi
# r132 — push is a toggle. 1: GITHUB_TOKEN is stored for git over HTTPS.
# 0: a push URL that fails BY NAME, so nobody mistakes it for a network fault.
if [ "$GIT_PUSH" = 1 ] && [ -n "${GITHUB_TOKEN:-}" ]; then
    git config credential.helper store
    ( umask 077; printf 'https://x-access-token:%s@github.com\n' "$GITHUB_TOKEN" > "$HOME/.git-credentials" )
    print_ok "Git push: ENABLED (token stored for HTTPS, 0600)"
else
    git remote set-url --push origin "PUSH-DISABLED-set-OT_GIT_PUSH=1-in-bootstrap.sh"
    print_ok "Git push: disabled (pull only)"
fi

# Set execute permissions on ALL shell scripts after git operations.
# Must run after git reset --hard which can strip permissions set during rsync.
find "$INSTALL_DIR" -name "*.sh" -exec chmod +x {} \;

# ── r132 — THE SUITE ────────────────────────────────────────────────────────
# harden_hosts (needrestart shield + apt timers off-RTH) runs first, as before.
# ⚠️ midnight-halt POWERS THE BOX OFF at 00:00 ET; the reference box is woken at
# 08:00 by an EventBridge schedule that lives OUTSIDE this repo. A box without
# one stays off until started by hand.
print_step "suite" "Timers, diagnostics, Claude"
mkdir -p "$INSTALL_DIR/logs"
for f in $SUITE; do
    if [ ! -f "$INSTALL_DIR/$f" ]; then
        print_warn "$f missing — SKIPPED"; INSTALL_FAILED="$INSTALL_FAILED $f"; continue
    fi
    if bash "$INSTALL_DIR/$f"; then
        print_ok "$f"
    else
        print_warn "$f FAILED"; INSTALL_FAILED="$INSTALL_FAILED $f"
    fi
done
# CD.1 — an install ALWAYS lands standalone (the warehouse push off); a bootstrap's managed is recorded for
# configure.sh, never applied here.
if ! ot_capture_install "$INSTALL_DIR" "$INSTRUMENT" "$DATA_CAPTURE"; then
    print_warn "data capture (standalone) did not fully apply"; INSTALL_FAILED="$INSTALL_FAILED data_capture"
fi
if [ "$CLAUDE_AT_BOOT" = 1 ]; then
    # consumed by tools/claude_boot.py once a FIRST_BOOT-briefed session is up
    mkdir -p "$HOME/.optbot" && touch "$HOME/.optbot/first_boot"
else
    print_info "Claude installed, NOT raised at boot (OT_CLAUDE_AT_BOOT=0). Later: bash deploy/install_claude_boot.sh"
fi

# ── Nothing is started here (CD.1) ───────────────────────────────────────────
print_info "candle-feed and ${SERVICE_NAME} are installed and STOPPED. Next: ./configure.sh, set everything, choose Done:"
print_info "  Done starts candle-feed, primes the informers' history from the warehouse, starts ${SERVICE_NAME},"
print_info "  then applies data capture (standalone unless item 14 chose managed)."
if [ "$CLAUDE_AT_BOOT" = 1 ]; then
    print_info "Raising the Claude session (first boot)..."
    sudo systemctl start optbot-claude-boot.service || true
    print_info "Claude: $(cat "$INSTALL_DIR/data/AGENT_STATUS" 2>/dev/null | tail -1 || echo 'status unknown')"
fi

echo ""
box "$GREEN" "   Setup Complete - every service installed and STOPPED" \
             "   Next: ./configure.sh -> set everything -> Done (the first start)"
echo ""
echo -e "  Instrument:  ${INSTRUMENT} 0DTE (TastyTrade)"
echo -e "  Mode:        $([ "$PAPER_TRADING" = "True" ] && echo "📄 PAPER" || echo "🔴 LIVE")"
echo -e "  Risk:        \$${RISK_USD}/trade"
echo -e "  TT Account:  ${TT_ACCOUNT_NUMBER}"
echo -e "  Telegram:    chat ${TELEGRAM_CHAT_ID}"
echo -e "  Commit:      $(git -C "$INSTALL_DIR" log -1 --format='%h' 2>/dev/null) (${GIT_REF})"
echo -e "  Swap:        $(swapon --show --noheadings | awk '{print $3}' | head -1)"
echo -e "  Timers:      $(systemctl list-timers 'optbot-*' --all --no-legend 2>/dev/null | wc -l) optbot timers"
echo ""
echo -e "  Commands:"
echo -e "    python status.py             — live status"
echo -e "    python query.py              — performance dashboard"
echo -e "    journalctl -u ${SERVICE_NAME} -f   — live logs"
echo -e "    journalctl -u candle-feed -f       — feed logs"
echo -e "    bash configure.sh           — change settings"
echo -e "    bash deploy/push.sh                — push changes to GitHub"
echo -e "    bash deploy/snapshot.sh            — snapshot bot state"
echo ""
echo -e "${GREEN}  Run './configure.sh' and choose Done to start it.${RESET}"
echo ""

# ── Cleanup ───────────────────────────────────────────────────────────────────
print_info "Cleaning up installation files..."

rm -rf "$DEPLOY_DIR"
rm -f "$HOME/install.sh"
# Destroy the one-shot secrets bootstrap now that credentials are baked into the
# systemd unit. shred first so the plaintext is not trivially recoverable.
for _secret_file in "$HOME/bootstrap.sh" "$HOME/cred.txt"; do
    if [ -f "$_secret_file" ]; then
        command -v shred >/dev/null 2>&1 && shred -u "$_secret_file" 2>/dev/null || rm -f "$_secret_file"
    fi
done

print_ok "Cleanup complete."
if [ -n "$INSTALL_FAILED" ]; then
    echo -e "${BOLD}${RED}  🔴 INSTALL INCOMPLETE:${INSTALL_FAILED}${RESET}"
else
    print_ok "Every step completed."
fi
# r132 — the final shell must not inherit the secrets this install was given.
unset TT_CLIENT_SECRET TT_REFRESH_TOKEN TELEGRAM_TOKEN GITHUB_TOKEN CLAUDE_LOGIN_B64

# Always end in the install dir with venv active
export PATH="$VENV/bin:$PATH"
cd "$INSTALL_DIR"
exec bash --login
