#!/usr/bin/env bash
# ==========================================================================
# configure.sh  v5.6
# v5.6  2026-10-31  OTV5 r67 (PARC.4) — ITEM 15 (PARC) IS REMOVED: TCS moves 16 -> 15, Done 17 -> 16, the
#       prompt names 1-16; parc_label / change_parc and the summary's PARC line are gone. The operator, 2026-10-31:
#       "On PARC, no. It was an idea. It failed. It's done." and "Yes" to removing its code. A box's stale OT_PARC
#       line is read by nothing. Gate tests/check_no_parc.py.
# v5.5  2026-10-30  OTV5 r57 (TCS.LOG1) — ITEM 16 IS TCS (OT_TCS_ACTIVE 1|log|0, UNSET = log); Done moves to 17. The
#       operator, 2026-10-30: "Can you reactivate TCS Monday as 'log only'? But do not trade it." then "Make sure TCS
#       logs everything an executable trade logs." The label reads config.TCS_MODE (the consumer), as item 15 reads
#       PARC_MODE; log books a SHADOW trade (execution/shadow_book.py: shadow_trades.db, never ordered).
# v5.4  2026-10-28  OTV5 r50 (PARC.3) — PARC's code default is now log (paused until a better stop): item 15's help
#       says so. The operator: "Don't go live on the PARC tomorrow until we find a better stop placement."
# v5.3  2026-10-27  OTV5 r46 (PARC.1) — ITEM 15 IS PARC (OT_PARC 1|log|0, UNSET = 1, trade); Done moves to 16. The
#       operator, 2026-10-27: "Call it PARC"; "I want 1050 to be the floor & use the same ramp in configure.sh (most are
#       set to $2500)"; "No shadow mode. We're paper. It trades tomorrow." PARC sizes on items 2 (ramp MIN) and 8 (ramp
#       TOP), the Breakout ramp; this item only switches it. The label reads config.PARC_MODE (the consumer), never a
#       copy of its rule; a value config would not take is refused, nothing written. The summary shows it.
# v5.2  2026-10-25  OTV5 r16 (PRIME.1) — THE HISTORY COMES FROM TASTYTRADE THROUGH THE FEED, NOT FROM S3. candle-feed v5.1
#       primes a symbol the store has never held PRIME_DAYS deep and backfills a held one as before; tools/prime_ramp.py
#       v5.1 waits for that backfill and reports it (no S3, no writes). The first start's and item 1's messages say so.
# v5.1  2026-10-25  OTV5 r13 (BOOT.12) — THE FIRST-START MARKER AND THE CAPTURE CHOICE CREATE THEIR DIRECTORY. Only
#       setup_ec2.sh makes ~/.optbot, so on a box repointed to OTV5 (SOFI, 2026-10-25) Done started the bot but could not
#       write ~/.optbot/first_start_done: first start stayed PENDING and the next Done would run it again. Every write
#       of either file is now preceded by mkdir -p of its directory.
# v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
# v4.19 2026-10-24  CD.1 — DONE IS THE FIRST START, IN ORDER, AND MANAGED IS THE WAREHOUSE SWITCH. The operator,
#       2026-10-24: "Once the deploy lands & config.sh params are all set, that should be the 1st start of options
#       bot, candle service, the ramp primer & s3 push enabled (from configure.sh)"; "I'm good with the managed tag
#       being the s3 switch". setup_ec2.sh v4.11 starts nothing, so the FIRST Done (no ~/.optbot/first_start_done)
#       runs first_start(): enable + start candle-feed -> tools/prime_ramp.py --apply (the informers' history from
#       the warehouse) -> enable + start the bot -> data capture as item 14 chose (standalone unless MANAGED) ->
#       the marker. The banner says "First start: PENDING" until it has run. Item 14 on a box that has not had its
#       first start RECORDS the choice (~/.optbot/capture.choice) for Done; a primer that cannot prime REFUSES the first
#       start (the operator: "Don't allow this situation to happen in the 1st place. We have s3"), the bot is not
#       started cold; on a running box it applies at once,
#       as before. MANAGED is refused while tools/capture_guard.py finds another host pushing this symbol in the
#       last 14 days, or cannot read the warehouse (fail closed), unless the operator types OVERRIDE. Item 1 runs
#       the primer for the new symbol on a box that has had its first start. On a MANAGED box item 1 first drains the
#       OLD symbol under its own label (a drain that is not OK refuses the switch, nothing changed), then runs the
#       guard on the NEW symbol: another pusher or an unreadable warehouse PAUSES the push (~/.optbot/push_paused,
#       read by s3_push v4.12 from every entrypoint) until item 14 + OVERRIDE. Managed itself stays. Gate: tests/check_clean_deploy.py.
# v4.18 2026-10-10  OTV4TEST r266 (STOP.1) — ITEM 13 IS THE RESTING STOP (OT_RESTING_STOP off|trade, paper
#       only); data capture moves to 14, Done to 15. The operator, 2026-10-10: "post a resting order when our
#       stop is hit, wait for price to come back to it"; "120 seconds is fine".
# v4.17 2026-10-10  OTV4TEST r265 (BRK.8 + BRK.9) — ITEM 11 IS BREAKOUT'S ENTRY END (OT_BREAKOUT_END),
#       ITEM 12 ITS NO-PROGRESS EXIT (OT_BRK_NOPROG off|log|trade); data capture moves to 13, Done to 14.
#       Both read their answer from config.py (the consumer), never a copy of its rule. The operator,
#       2026-10-05: "If we're gonna allow a per box setting then it needs to be a toggle inside configure";
#       2026-10-10 13:37 ET: "Yes, to all. Study, fit & apply."
# v4.16 2026-10-05  OTV4TEST r253 (RUNW.2) — ITEM 10 IS RUNAWAY'S ENTRY END (OT_RUNAWAY_END).
#       r189 built the per-box switch and the operator approved 11:30 for SPX-TEST on
#       10-03, but nothing here could set it, so it was never set: SPX-TEST measured its
#       Runaway going INACTIVE at 10:30:00 ET on 10-05. The operator, 11:33 ET: "If
#       we're gonna allow a per box setting then it needs to be a toggle inside
#       configure." HH:MM sets it, blank clears it (the code's 10:30). The value is
#       checked BY config.py before it is written - a value config would refuse is
#       never stored. Data capture moves to 11 and Done to 12; the summary names the end.
# v4.15 2026-10-03  OTV4TEST r228 (CFG.4) — THE ORB AND VOLT SCALING ITEMS LEAVE THE
#       MENU; THE RAMP STAYS. Both trades are off (r187) and each switch is read
#       only when its own trade fires. The operator, 2026-10-03: "Is it safe to
#       remove the orb and volt from configure, but keep the sizing ramp?" - then
#       "Yes to the configure change". Item 9 is Breakout scaling, 10 Data capture,
#       11 Done; the summary's Scaling line shows Breakout alone. NOTHING IS
#       WRITTEN OR REMOVED in the unit: a stored OT_SCALE_ORB / OT_SCALE_VOLT
#       stays as it is, and change_scaling still works for any key.
# v4.14 2026-09-29  OTV4TEST r175 (SYM.1) — ITEM 1's SYMBOL LIST WRAPS AT 72
#       COLUMNS. It is 82 symbols since r175 and printed as one line, which
#       the phone (Termius, 76 columns) broke mid-ticker.
# v4.13 2026-09-27  OTV4TEST r162 (CAP.1) — ITEM 6 IS THE DAILY CATASTROPHIC LOSS CAP.
#       The operator's name for it, and his rule: "Manage what's open but no new
#       entries. If the open TRADES put us back under the limit again after they
#       close, it can open trades again." Same key (OT_DAILY_LOSS_LIMIT); the
#       labels and the item's explanation now say it re-opens (risk_manager v4.8).
# v4.12 2026-09-27  OTV4TEST r161 (SIZE.2) — ONE MIN, ONE MAX, A SCALING SWITCH PER
#       TRADE. The operator: "Risk per trade/Ramp Start (MIN)", "Scaling Position
#       Ramp TOP (MAX)", "ORB Scaling OFF/ON", "Breakout Scaling OFF/ON", "VOLT
#       Scaling OFF/ON", and on the merge "that was always the intent". Item 2 is
#       Risk per trade / ramp START (MIN) and REMOVES a leftover OT_ORB_RISK_USD
#       line (config.py no longer reads it); item 9 "ORB ramp START" is gone; 8 is
#       Scaling ramp TOP (MAX), the same OT_ORB_BUDGET_USD key; 9/10/11 switch
#       OT_SCALE_ORB / OT_SCALE_BREAKOUT / OT_SCALE_VOLT ("1" on, "0" OFF = flat
#       size, structure stop kept); Data capture moves to 12 and Done to 13. The
#       summary shows the three switches and names a leftover OT_ORB_RISK_USD.
# v4.11 2026-09-25  OTV4TEST r139 — ITEM 1 MOVES THE WHOLE BOX, NOT JUST THE BOT. The
#       instrument lives in THREE places: optionsbot.service, candle-feed.service
#       (its own Environment=OT_INSTRUMENT, written by setup_ec2.sh) and, on a
#       managed box, the s3-push drop-in. change_instrument wrote only the first,
#       so the first SOFI paper box traded SOFI while its FEED streamed QQQ
#       (manifold: QQQ_EXT/1m 56s fresh, SOFI_EXT stale) and its store filled with
#       QQQ candles the pusher would have sent to sym=QQQ. Now item 1 rewrites the
#       feed's unit, restarts the feed, and on a managed box re-applies
#       data_capture.sh so the push label follows. The operator: "a good lesson
#       learned for when we migrate the fleet over".
# v4.10 2026-09-25  OTV4TEST r138 — DONE STARTS THE BOT. Operator: the bot is "not
#       started by default and then when I set all the variables in configure and
#       exit out of the menu that resets everything and starts it". setup_ec2.sh
#       v4.7 installs optionsbot NOT enabled and NOT started; `finish_session`
#       (the Done path) now ENABLES it (so it survives reboots and wakes) and
#       STARTS it when it is not running, or RESTARTS it when it is running and
#       something changed. Running and unchanged: nothing happens, as before.
# v4.9  2026-09-24  OTV4TEST r136 — ITEM 10 IS DATA CAPTURE: MANAGED OR STANDALONE.
#       Operator: *"a toggle in configure.sh call it 'managed' or 'standalone'
#       data capture"*. `change_data_capture` runs deploy/data_capture.sh - the
#       ONE implementation setup_ec2.sh also calls - and the label is read from
#       the UNITS (data_capture.sh status), never from a flag file. It does not
#       touch the bot unit, so it does not set CHANGED and the bot is not
#       restarted for it. "Done" moves to 11; the prompt names 1-11.
# v4.8  2026-09-24  OTV4TEST r127 — ITEM 7 IS THE PIN-PROXIMITY GATE; THE RELAXED
#       ENTRY TOGGLE IS REMOVED. Operator: *"make it replace the relaxed entry
#       toggle. Since we don't do relaxed entries here."* and, turning r97's gate
#       off pending data: *"I would prefer to interact with it there."*
#       `change_pin_gate` writes OT_PIN_PROXIMITY_ACTIVE (1 on / 0 off) with the
#       same set_env + reload_daemon every item uses. `pin_gate_label` shows what
#       the operator SET, or "not set" plus the default read from config.py — the
#       r91 rule: nothing is displayed that he did not choose, and the default is
#       never hardcoded here, where it would rot the day config.py moves.
#       ⚠️ RELAXED ENTRY IS NOT DELETED FROM THE CODE: strategy/relaxed.py still
#       honours OT_RELAXED_ENTRY if a unit sets it; this box does not (measured
#       2026-09-24: unset), and unset is OFF. Only the menu item is gone.
#       ⚠️ THE GEX PIN BUTTERFLY DOES NOT READ THIS KEY — its PINNING condition is
#       foundational in strategy/gex_pin_butterfly.py. The gate is main.py:4802,
#       long_debit entries only.
#       Also fixes the out-of-range prompt, which said 1-9 on a 10-item menu.
# v4.7  2026-09-22  r91 — A DECLARATION SURFACE PRINTS DECLARATIONS. Operator:
#       *"Configure.sh is where I enter env variables. The only thing it
#       displays is the current variables that the operator has chosen... The
#       per trade differences due to stop width should never be displayed
#       there."* The r201 ORB "spot hint" READ orb_state.json and printed the
#       live price into this script — machine state on a declaration screen —
#       and is DELETED. `fmt_declared` prints what was set or "not set", never
#       another key's value dressed as a default. ORB ramp TOP
#       (OT_ORB_BUDGET_USD) and ORB ramp START (OT_ORB_RISK_USD) are now a
#       settable pair: the START governed the whole ORB sizing ramp from r44
#       and was never once declared or displayed.
# v4.6  2026-09-17  OTV4TEST r34 — MOVED BACK TO THE REPO ROOT (operator's ruling).
#   r14 moved it to deploy/ because it is a .sh, but it installs no unit, touches
#   no systemd and runs on no timer — it is the sixth operator reader and belongs
#   beside status.py and query.py. No behaviour change.
# v4.5  2026-09-11  OTV4TEST r14 — moved from the repo root to deploy/ (root cleanup); no behaviour change.
#
# v4.4  2026-08-31  r203 — THE r201 SPOT HINT WAS BROKEN AND BAKED. It read a
#   `data/` subdirectory that does not exist, and `2>/dev/null` made the
#   failure look like a deliberate blank. Paths now come from config.py;
#   stderr is visible; the land gate RUNS the function and requires output.
#   🔴 r201's gate checked that the function existed and that this file
#   parsed. Presence and a clean parse are not evidence that a display
#   displays.
#
# v4.3  2026-08-31  r201 — menu item 8: ORB BUDGET (OT_ORB_BUDGET_USD), set
#   PER UNDERLYING. Shows SPOT as the reference — live from orb_state.json,
#   or derived from the last trade's underlying_entry, labelled either way.
#   ⚠️ The default fails closed at one trade's risk, so an unconfigured box
#   trades SMALL; r91 — the menu now reads "not set" rather than borrowing
#   another key's value, because a declaration surface prints declarations.
#   ⚠️ Fixed in passing: the prompt said "between 1 and 7" on an 8-item menu.
# Per-box configuration.
#
# v4.2  2026-08-20  change_relaxed now calls reload_daemon after set_env, like
#       every other change_*. set_env edits the UNIT FILE; without the reload
#       systemd restarts from its cached copy, so the bot runs the OLD value
#       while the menu reports the new one. Pinned by check_configure_relaxed
#       C6: any function that calls set_env must also call reload_daemon.
#
# v4.1  2026-08-20  Option 7 (relaxed entry) called an undefined `confirm`,
#       so it always took the else branch: it could never be switched ON, and
#       opening the item wrote OT_RELAXED_ENTRY=0. Now calls ask_yn, the
#       helper the rest of the file uses. Both branches are executed by
#       tests/check_configure_relaxed.py, which also traps
#       command-not-found so a future undefined helper cannot fail quietly.
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
#!/usr/bin/env bash
# repo-wide v3.0 bump: Yahoo-Finance purge & data stream
#         mapping optimization (single shared TastyTrade candle feed). No
#         logic change in this file.
#  options_trader v2.0  —  Live Configuration Manager
#  v1.0 — original release
#  replaced SMS/Twilio with Telegram
#  swapped menu order: Telegram now 4, TT credentials now 5
#  fixed menu display lines to match handler order
#  auto restart on exit if changes made, no prompt
#  wipe trades.db on instrument change (paper mode only);
#          ORB range auto-fetched for new instrument via get_orb_range.py
#  add Daily loss cap override menu (OT_DAILY_LOSS_LIMIT)
#  add single-name instruments (directional-only) to the
#          instrument menu for wider paper-trading coverage
#  archive trades.db (+WAL sidecars) on EVERY mode switch,
#          labeled by the outgoing mode (trades_paper_*.db / trades_live_*.db).
#          Paper and live histories never share a file (audit defect Q);
#          companion to trade_logger v3.7 mode-scoped queries.
#  going LIVE now reports that broker reconciliation
#          auto-enables with the mode (config.py v1.8 default follows
#          OT_PAPER_TRADING); show_config gains a "Broker reconcile" status
#          line; warns loudly if OT_BROKER_RECONCILE=False pins it off.
#  instrument picker now types the ticker (validated against
#          config.STRIKE_INCREMENTS) instead of a numbered menu — scales to the
#          full screener universe
#  Run this anytime to view or change bot settings.
#  Changes take effect on the NEXT bot start — the bot is
#  never restarted automatically to avoid mid-session surprises.
#  Usage:
#    ./configure.sh          — interactive menu
#    ./configure.sh --show   — print current config and exit
# ==========================================================================
SERVICE_NAME="optionsbot"
BOT_DIR="$HOME/options-trader"
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
FEED_UNIT_FILE="/etc/systemd/system/candle-feed.service"   # r139: the feed carries its own OT_INSTRUMENT
FEED_SERVICE="candle-feed"
# CD.1 — the first start's marker and item 14's recorded choice (setup_ec2 v4.11 writes capture.requested)
FIRST_START_FILE="${OT_FIRST_START_FILE:-$HOME/.optbot/first_start_done}"
CAPTURE_CHOICE_FILE="${OT_CAPTURE_CHOICE_FILE:-$HOME/.optbot/capture.choice}"
CAPTURE_REQUESTED_FILE="${OT_CAPTURE_REQUESTED_FILE:-$HOME/.optbot/capture.requested}"
BOT_PY="${OT_BOT_PY:-$BOT_DIR/venv/bin/python}"
PUSH_PY="${OT_PUSH_PY:-/usr/bin/python3}"                         # s3_push runs under the system python (boto3)
PUSH_PAUSE_FILE="${OT_PUSH_PAUSE_FLAG:-$HOME/.optbot/push_paused}" # read by warehouse/s3_push.py v4.12

# ── Colours ──────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

print_banner() {
    echo ""
    echo -e "${BOLD}${CYAN}============================================================${RESET}"
    echo -e "${BOLD}${CYAN}  options_trader  —  Configuration Manager${RESET}"
    echo -e "${BOLD}${CYAN}============================================================${RESET}"
    echo -e "  First start: $(first_start_label)"
    echo ""
}

# ── CD.1 — the first start ────────────────────────────────────────────────────
first_start_pending() { [[ ! -f "$FIRST_START_FILE" ]]; }

first_start_label() {
    if first_start_pending; then
        echo -e "${YELLOW}PENDING${RESET} - Done starts candle-feed, primes the history, starts the bot, applies data capture"
    else
        echo -e "${GREEN}done${RESET} $(cat "$FIRST_START_FILE" 2>/dev/null)"
    fi
}

capture_choice() { cat "$CAPTURE_CHOICE_FILE" 2>/dev/null || echo standalone; }

run_primer() {
    # r16 — candle-feed primes THIS box's instrument from TastyTrade (deep only for a symbol the store never held);
    # tools/prime_ramp.py waits for that backfill and reports what the store holds. No S3, no writes.
    ( cd "$BOT_DIR" && "$BOT_PY" tools/prime_ramp.py --apply )
}

first_start() {
    echo ""
    echo "  FIRST START (CD.1): candle-feed -> history primer -> bot -> data capture"
    sudo systemctl enable "$FEED_SERVICE" >/dev/null 2>&1
    sudo systemctl start "$FEED_SERVICE"
    local i
    for i in 1 2 3 4 5 6 7 8 9 10; do
        systemctl is-active --quiet "$FEED_SERVICE" && break
        sleep 3
    done
    if ! systemctl is-active --quiet "$FEED_SERVICE"; then
        print_warn "candle-feed did not start - the first start STOPS here (nothing else was started)."
        print_warn "Check: journalctl -u ${FEED_SERVICE} -n 30, then choose Done again."
        return 1
    fi
    print_ok "candle-feed running."
    local rc=0
    run_primer || rc=$?
    # The operator, 2026-10-24: "Don't allow this situation to happen in the 1st place. We have s3." A first start
    # whose history cannot be primed is REFUSED - the bot does not start cold. candle-feed stays up; Done again.
    case "$rc" in
        0) print_ok "History in place (TastyTrade, through candle-feed's backfill)." ;;
        4) print_warn "FIRST START REFUSED: candle-feed has not backfilled the last session's 1m from TastyTrade - the bot is NOT started." ;;
        *) print_warn "FIRST START REFUSED: the primer exited $rc (see the lines above) - the bot is NOT started." ;;
    esac
    if [[ "$rc" != 0 ]]; then
        print_warn "Fix what the primer named, then choose Done again. candle-feed is left running."
        return 1
    fi
    sudo systemctl enable "$SERVICE_NAME" >/dev/null 2>&1
    sudo systemctl start "$SERVICE_NAME"
    sleep 4
    if ! bot_is_running; then
        print_warn "Bot failed to start - check: journalctl -u ${SERVICE_NAME} -n 20. Data capture left standalone."
        return 1
    fi
    print_ok "Bot started."
    if [[ "$(capture_choice)" == "managed" ]]; then
        bash "$BOT_DIR/deploy/data_capture.sh" managed && print_ok "Data capture: MANAGED (the warehouse push is ON)."
    else
        print_ok "Data capture: $(data_capture_label) (item 14 turns the warehouse push on)."
    fi
    mkdir -p "$(dirname "$FIRST_START_FILE")"
    date -u +%Y-%m-%dT%H:%M:%SZ > "$FIRST_START_FILE"
    return 0
}

print_ok()   { echo -e "  ${GREEN}✓${RESET}   $1"; }
print_warn() { echo -e "  ${YELLOW}⚠${RESET}   $1"; }
print_info() { echo -e "  ${CYAN}→${RESET}  $1"; }
ask()        { read -p "    $1: " "$2"; }
ask_secret() { read -s -p "    $1: " "$2"; echo ""; }
ask_yn()     {
    while true; do
        read -p "    $1 [y/n]: " yn
        case "$yn" in [Yy]) return 0;; [Nn]) return 1;; esac
    done
}

# ── Read a single Environment= value from the unit file ──────
get_env() {
    sudo grep -oP "(?<=Environment=${1}=).*" "$UNIT_FILE" 2>/dev/null | tail -1 || echo ""
}

# ── r91 — WHAT A DECLARATION SURFACE IS ALLOWED TO PRINT ─────
# 🔴 THE OPERATOR'S RULING, 2026-09-22: *"Configure.sh is where I enter env
# variables. The only thing it displays is the current variables that the
# operator has chosen... The per trade differences due to stop width should
# never be displayed there."* And: *"they are STATIC. They never change unless
# I change them."*
# So a value shows as the operator SET it, or it shows as unset. It never
# borrows another key's value and dresses it as a default — that prints a
# number he did not choose on the line where he chooses it, which is how
# `OT_ORB_RISK_USD` governed the whole ORB sizing ramp for four days while
# being invisible here (r91). This also cost a live-state reader: the r201 ORB
# "spot hint" read `orb_state.json` and printed the running price INTO this
# script, which is machine state, not a declaration.
fmt_declared() {
    if [[ -n "$1" ]]; then
        printf '$%s' "$1"
    else
        printf 'not set'
    fi
}

# ── Update or add an Environment= line in the unit file ──────
set_env() {
    local key="$1" val="$2"
    if sudo grep -q "Environment=${key}=" "$UNIT_FILE" 2>/dev/null; then
        sudo sed -i "s|Environment=${key}=.*|Environment=${key}=${val}|" "$UNIT_FILE"
    else
        sudo sed -i "/ExecStartPre=/i Environment=${key}=${val}" "$UNIT_FILE"
    fi
}

# r161 — remove an Environment= line (a retired key), silently if absent.
drop_env() {
    sudo sed -i "/^Environment=${1}=/d" "$UNIT_FILE"
}

reload_daemon() {
    sudo systemctl daemon-reload
}

# v2.0 (audit defect Q): archive the trade DB on EVERY mode switch so paper and
# live histories never share a file. mv on the same filesystem keeps the inode,
# so a still-running bot finishes its session writing into the archive; the
# restarted bot creates a fresh trades.db in the new mode. WAL sidecars move
# with the DB so no unflushed rows are lost.
archive_trades_db() {
    local from_mode="$1"   # outgoing mode: "paper" or "live"
    local db="$BOT_DIR/trades.db"
    if [[ ! -f "$db" ]]; then
        print_info "No trades.db to archive — starting the new mode fresh."
        return
    fi
    local stamp dest
    stamp=$(date +%Y%m%d_%H%M%S)
    dest="$BOT_DIR/trades_${from_mode}_${stamp}.db"
    mv "$db" "$dest"
    [[ -f "${db}-wal" ]] && mv "${db}-wal" "${dest}-wal"
    [[ -f "${db}-shm" ]] && mv "${db}-shm" "${dest}-shm"
    print_ok "Archived ${from_mode} trade history → $(basename "$dest")"
    print_info "A fresh trades.db is created on next start — ${from_mode} P&L can never leak into the new mode."
}

bot_is_running() {
    systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null
}

# ──────────────────────────────────────────────────────────────
# SHOW CURRENT CONFIG
# ──────────────────────────────────────────────────────────────
show_config() {
    local instrument risk paper account

    if [[ ! -f "$UNIT_FILE" ]]; then
        echo -e "  ${RED}Service unit not found.${RESET}"
        echo -e "  Run setup_ec2.sh first to install the bot."
        return 1
    fi

    instrument=$(get_env "OT_INSTRUMENT")
    risk=$(get_env "OT_RISK_USD")
    paper=$(get_env "OT_PAPER_TRADING")
    account=$(get_env "TT_ACCOUNT_NUMBER")
    telegram_token=$(get_env "TELEGRAM_TOKEN")
    telegram_chat=$(get_env "TELEGRAM_CHAT_ID")

    local mode_label
    if [[ "$paper" == "False" ]]; then
        mode_label="${RED}${BOLD}🔴 LIVE — real money${RESET}"
    else
        mode_label="${GREEN}📄 PAPER — simulated fills${RESET}"
    fi

    local status_label
    if bot_is_running; then
        status_label="${GREEN}● running${RESET}"
    else
        status_label="${YELLOW}○ stopped${RESET}"
    fi

    echo -e "  ${BOLD}Current Configuration${RESET}"
    echo -e "  ─────────────────────────────────────────"
    echo -e "  Bot status:     $(echo -e $status_label)"
    echo -e "  Instrument:     ${BOLD}${instrument:-not set}${RESET}"
    echo -e "  Risk per trade: ${BOLD}\$${risk:-not set}${RESET}"
    local dll=$(get_env "OT_DAILY_LOSS_LIMIT")
    echo -e "  Loss cap:       ${BOLD}$(fmt_declared "$dll")${RESET} (daily catastrophic)"
    echo -e "  Pin gate:       ${BOLD}$(pin_gate_label)${RESET}"
    echo -e "  Scaling:        ${BOLD}Breakout $(scaling_short OT_SCALE_BREAKOUT SCALE_BREAKOUT)${RESET}"
    local old_start=$(get_env "OT_ORB_RISK_USD")
    [[ -n "$old_start" ]] && print_warn "OT_ORB_RISK_USD=${old_start} is NOT read (merged into risk per trade) - item 2 removes it."
    echo -e "  Runaway end:    ${BOLD}$(runaway_end_label)${RESET}"
    echo -e "  Breakout end:   ${BOLD}$(breakout_end_label)${RESET}"
    echo -e "  BRK no-progress:${BOLD}$(brk_noprog_label)${RESET}"
    echo -e "  Resting stop:   ${BOLD}$(resting_stop_label)${RESET}"
    echo -e "  TCS:            ${BOLD}$(tcs_label)${RESET}"
    echo -e "  Data capture:   ${BOLD}$(data_capture_label)${RESET}"
    echo -e "  Trading mode:   $(echo -e $mode_label)"
    local rec_pin rec_label
    rec_pin=$(get_env "OT_BROKER_RECONCILE")
    if [[ "$rec_pin" == "True" ]]; then rec_label="on (pinned)"
    elif [[ "$rec_pin" == "False" ]]; then rec_label="OFF (pinned)"
    elif [[ "$paper" == "False" ]]; then rec_label="on (auto, follows LIVE)"
    else rec_label="off (auto, follows PAPER)"; fi
    echo -e "  Broker reconcile: ${BOLD}${rec_label}${RESET}"
    echo -e "  TT Account:     ${BOLD}${account:-not set}${RESET}"
    local tg_status
    if [[ -n "$telegram_token" ]]; then
        tg_status="✓ enabled (chat ${telegram_chat})"
    else
        tg_status="— disabled"
    fi
    echo -e "  Telegram:       ${BOLD}${tg_status}${RESET}"
    echo -e "  ─────────────────────────────────────────"
    echo ""

    if bot_is_running; then
        print_warn "Bot is currently running. Changes take effect on next start."
    else
        print_warn "Bot is NOT running - it starts (and is enabled at boot) when you choose Done."
    fi
}

# ──────────────────────────────────────────────────────────────
# MENU ACTIONS
# ──────────────────────────────────────────────────────────────

change_instrument() {
    local current allowed full choice
    current=$(get_env "OT_INSTRUMENT")
    # Pull the tradeable universe straight from config.py — single source of truth.
    allowed=$(cd "$BOT_DIR" && python3 -c "import config; print(' '.join(sorted(config.STRIKE_INCREMENTS)))" 2>/dev/null)
    full=$(cd "$BOT_DIR" && python3 -c "import config; print(' '.join(sorted(config.FULL_STRATEGY_INSTRUMENTS)))" 2>/dev/null)
    if [ -z "$allowed" ]; then
        print_warn "Could not read the symbol list from config.py."
        return
    fi
    echo ""
    echo -e "  Current instrument: ${BOLD}${current}${RESET}"
    echo ""
    echo -e "  ${BOLD}Full strategy${RESET} (condor/butterfly):  ${full}"
    echo -e "  ${BOLD}Directional only${RESET} (ORB + sweep):    everything else"
    echo ""
    echo -e "  Tradeable symbols:"
    echo "${allowed}" | fold -s -w 68 | sed 's/^/    /'
    echo ""
    while true; do
        read -p "    Enter ticker [ENTER to keep ${current}]: " choice
        choice=$(echo "${choice:-$current}" | tr '[:lower:]' '[:upper:]')
        if [[ "$choice" == "$current" ]]; then
            print_info "Unchanged: ${current}"; return
        fi
        if echo "$allowed" | tr ' ' '\n' | grep -qxF "$choice"; then
            NEW_INST="$choice"; break
        fi
        print_warn "Unknown ticker '${choice}'. Pick one from the list above."
    done
    # CD.1 — A MANAGED BOX DRAINS UNDER THE OLD LABEL BEFORE ANYTHING CHANGES (the operator, 2026-10-24: "Agreed
    # entirely"). Every row written as ${current} is pushed as ${current}; a drain that is not OK refuses the switch.
    local was_managed=0 drain
    if bash "$BOT_DIR/deploy/data_capture.sh" status 2>/dev/null | head -1 | grep -q "managed$"; then
        was_managed=1
        print_info "Managed box: draining ${current}'s data under its own label before the switch..."
        drain=$( cd "$BOT_DIR" && env OT_INSTRUMENT="$current" "$PUSH_PY" warehouse/s3_push.py --verify 2>&1 )
        echo "$drain" | grep -E "^DRAIN |SHORT|PAUSED" | sed 's/^/    /'
        if ! echo "$drain" | grep -qE "^DRAIN .* OK$"; then
            print_warn "SWITCH REFUSED: ${current}'s drain did not report OK - nothing was changed. Fix it, then try again."
            return
        fi
        print_ok "${current} drained OK."
    fi
    set_env "OT_INSTRUMENT"  "$NEW_INST"
    set_env "OT_BOT_NAME"    "OptionsTrader-${NEW_INST}"
    # r139 — the FEED has its own OT_INSTRUMENT; move it with the bot.
    if sudo grep -q "^Environment=OT_INSTRUMENT=" "$FEED_UNIT_FILE" 2>/dev/null; then
        sudo sed -i "s|^Environment=OT_INSTRUMENT=.*|Environment=OT_INSTRUMENT=${NEW_INST}|" "$FEED_UNIT_FILE"
    else
        print_warn "No OT_INSTRUMENT line in ${FEED_UNIT_FILE} - the feed was NOT moved; check it."
    fi
    reload_daemon
    if systemctl is-active --quiet candle-feed 2>/dev/null; then
        sudo systemctl restart candle-feed
        print_ok "Candle feed restarted on ${BOLD}${NEW_INST}${RESET}."
    fi
    # r139 — a MANAGED box's push label follows the instrument (data_capture.sh
    # reads it from the bot unit just written; a stale shell value is dropped).
    if [[ "$was_managed" == 1 ]]; then
        env -u OT_INSTRUMENT bash "$BOT_DIR/deploy/data_capture.sh" managed
        # CD.1 — WHO ELSE PUSHES ${NEW_INST}? Another host, or a warehouse that cannot be read, PAUSES this box's push
        # (the flag every s3_push entrypoint reads) until a typed OVERRIDE. Managed stays: self-close stays on.
        if capture_guard_ok; then
            rm -f "$PUSH_PAUSE_FILE"
        else
            mkdir -p "$(dirname "$PUSH_PAUSE_FILE")"
            echo "sym=${NEW_INST}: another pusher or an unreadable warehouse at the switch, $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
                > "$PUSH_PAUSE_FILE"
            print_warn "Push PAUSED for ${NEW_INST} - nothing is uploaded until item 14 (managed + OVERRIDE) resumes it."
        fi
    fi
    print_ok "Instrument updated to ${BOLD}${NEW_INST}${RESET}."
    # Wipe trades.db in paper mode — old trades from a different instrument
    # are meaningless and pollute the P&L dashboard
    local paper
    paper=$(get_env "OT_PAPER_TRADING")
    if [[ "$paper" != "False" ]]; then
        rm -f "$BOT_DIR/trades.db"
        print_ok "Paper trade history cleared (instrument changed)."
    fi
    # CD.1 — the new symbol's history. Before the first start Done primes it; after, prime it now.
    if ! first_start_pending; then
        run_primer || print_warn "Primer for ${NEW_INST} did not complete - see the lines above."
    fi
}

change_risk() {
    local current
    current=$(get_env "OT_RISK_USD")
    echo ""
    echo -e "  ${BOLD}Risk per trade / ramp START (MIN)${RESET}  (OT_RISK_USD)"
    echo -e "  What every trade risks, and where the scaling ramp starts."
    echo -e "  Current: ${BOLD}\$${current}${RESET}"
    echo ""
    while true; do
        read -p "    New risk per trade in \$ [ENTER to keep \$${current}]: " input
        if [[ -z "$input" ]]; then
            print_info "Unchanged: \$${current}"
            return
        fi
        if [[ "$input" =~ ^[0-9]+(\.[0-9]+)?$ ]] && (( $(echo "$input > 0" | bc -l) )); then
            set_env "OT_RISK_USD" "$input"
            # r161 — the old ramp-START key is merged into this one. Remove it
            # so the unit cannot show a number config.py no longer reads.
            drop_env "OT_ORB_RISK_USD"
            reload_daemon
            print_ok "Risk per trade / ramp MIN updated to ${BOLD}\$$input${RESET}."
            return
        fi
        print_warn "Please enter a positive number (e.g. 200 or 150.50)."
    done
}

# ── r127 — THE PIN-PROXIMITY GATE (r97), ON OR OFF ─────────────────────────
# r97 refuses a DIRECTIONAL DEBIT (ORB, Breakout, Runaway, VOLT, the hunt) when
# GEX reads PINNING and price sits within 0.32 of an expected move of the pin.
# Operator, 2026-09-24, after it replayed to -$739 net across every fire and cut
# 18 of 24 trades on 09-21's trend day: *"Turn it off. We need to collect more
# data before ruling on it."* The data keeps collecting with the gate OFF:
# every fire_snapshot records pin_em_fraction, pin_strike and gex_environment.
pin_gate_label() {
    local v dflt
    v=$(get_env "OT_PIN_PROXIMITY_ACTIVE")
    if [[ "$v" == "1" ]]; then printf 'ON'; return; fi
    if [[ "$v" == "0" ]]; then printf 'OFF'; return; fi
    if [[ -n "$v" ]]; then printf 'OFF (set to %s; only 1 is on)' "$v"; return; fi
    # Unset: say so, and name the default from config.py rather than from memory.
    # The key is removed from THIS shell's env first so the answer is the code's.
    dflt=$(cd "$BOT_DIR" && env -u OT_PIN_PROXIMITY_ACTIVE python3 -c \
        "import config; print('ON' if config.PIN_PROXIMITY_ACTIVE else 'OFF')")
    printf 'not set (code default: %s)' "${dflt:-UNREADABLE - config.py did not import}"
}

# ── r253 (RUNW.2) — RUNAWAY'S ENTRY END, PER BOX ───────────────────────────
# Shows what the operator SET, or "not set" with the code's default READ FROM
# config.py (r91). A set value config.py would refuse is named as refused.
runaway_end_label() {
    local v got
    v=$(get_env "OT_RUNAWAY_END")
    if [[ -z "$v" ]]; then
        got=$(cd "$BOT_DIR" && env -u OT_RUNAWAY_END python3 -c \
            "import config; print(config.RUNAWAY_CUTOFF_ET)")
        printf 'not set (code default: %s)' "${got:-UNREADABLE - config.py did not import}"
        return
    fi
    got=$(cd "$BOT_DIR" && OT_RUNAWAY_END="$v" python3 -c \
        "import config; print('REFUSED' if config.RUNAWAY_END_ENV_REFUSED else config.RUNAWAY_CUTOFF_ET)")
    if [[ "$got" == "REFUSED" ]]; then
        printf '%s REFUSED by config - Runaway holds the code default' "$v"
    else
        printf '%s' "${got:-UNREADABLE - config.py did not import}"
    fi
}

change_runaway_end() {
    local val got
    echo ""
    echo "  Runaway entry end: $(runaway_end_label)"
    echo ""
    echo "  The LAST entry is one minute before this time (11:30 = last at 11:29)."
    echo "  HH:MM between 09:36 and the 15:40 entries stop. Blank = clear it"
    echo "  (the code's default). Only Runaway moves; every exit is unchanged."
    echo ""
    read -p "    Runaway entry end (HH:MM, blank to clear): " val
    val="${val// /}"
    if [[ -z "$val" ]]; then
        drop_env "OT_RUNAWAY_END"
        reload_daemon
        echo "  Runaway entry end cleared - $(runaway_end_label)."
        return
    fi
    # Ask the CONSUMER, never a copy of its rule: config.py refuses what it would refuse.
    got=$(cd "$BOT_DIR" && OT_RUNAWAY_END="$val" python3 -c \
        "import config; print('REFUSED' if config.RUNAWAY_END_ENV_REFUSED else config.RUNAWAY_CUTOFF_ET)")
    if [[ -z "$got" ]]; then
        print_warn "REFUSED - config.py did not import, so '$val' could not be checked. Nothing written."
        return
    fi
    if [[ "$got" == "REFUSED" ]]; then
        print_warn "REFUSED - '$val' is not HH:MM between 09:36 and 15:40. Nothing written."
        return
    fi
    set_env "OT_RUNAWAY_END" "$val"
    reload_daemon
    echo "  Runaway entry end set to $got (last entry one minute before)."
}

# ── r265 (BRK.9) — BREAKOUT'S ENTRY END, PER BOX (the mirror of item 10) ────
breakout_end_label() {
    local v got
    v=$(get_env "OT_BREAKOUT_END")
    if [[ -z "$v" ]]; then
        got=$(cd "$BOT_DIR" && env -u OT_BREAKOUT_END python3 -c \
            "import config; print(config.BREAKOUT_LATEST_ET)")
        printf 'not set (code default: %s)' "${got:-UNREADABLE - config.py did not import}"
        return
    fi
    got=$(cd "$BOT_DIR" && OT_BREAKOUT_END="$v" python3 -c \
        "import config; print('REFUSED' if config.BREAKOUT_END_ENV_REFUSED else config.BREAKOUT_LATEST_ET)")
    if [[ "$got" == "REFUSED" ]]; then
        printf '%s REFUSED by config - Breakout holds the code default' "$v"
    else
        printf '%s' "${got:-UNREADABLE - config.py did not import}"
    fi
}

change_breakout_end() {
    local val got
    echo ""
    echo "  Breakout entry end: $(breakout_end_label)"
    echo ""
    echo "  The LAST entry is one minute before this time (15:40 = last at 15:39)."
    echo "  HH:MM between 09:36 and the 15:40 entries stop. Blank = clear it"
    echo "  (the code's default). Only Breakout moves; every exit is unchanged."
    echo ""
    read -p "    Breakout entry end (HH:MM, blank to clear): " val
    val="${val// /}"
    if [[ -z "$val" ]]; then
        drop_env "OT_BREAKOUT_END"
        reload_daemon
        echo "  Breakout entry end cleared - $(breakout_end_label)."
        return
    fi
    got=$(cd "$BOT_DIR" && OT_BREAKOUT_END="$val" python3 -c \
        "import config; print('REFUSED' if config.BREAKOUT_END_ENV_REFUSED else config.BREAKOUT_LATEST_ET)")
    if [[ -z "$got" ]]; then
        print_warn "REFUSED - config.py did not import, so '$val' could not be checked. Nothing written."
        return
    fi
    if [[ "$got" == "REFUSED" ]]; then
        print_warn "REFUSED - '$val' is not HH:MM between 09:36 and 15:40. Nothing written."
        return
    fi
    set_env "OT_BREAKOUT_END" "$val"
    reload_daemon
    echo "  Breakout entry end set to $got (last entry one minute before)."
}

# ── r265 (BRK.8) — BREAKOUT'S NO-PROGRESS EXIT: off | log | trade ───────────
brk_noprog_label() {
    local v got
    v=$(get_env "OT_BRK_NOPROG")
    got=$(cd "$BOT_DIR" && OT_BRK_NOPROG="$v" python3 -c \
        "import config; print(config.BRK_NOPROG_MODE + (' (set to ' + config.BRK_NOPROG_ENV_REFUSED + ' - REFUSED)' if config.BRK_NOPROG_ENV_REFUSED else ''))")
    if [[ -z "$v" ]]; then
        printf 'not set (code default: %s)' "${got:-UNREADABLE - config.py did not import}"
    else
        printf '%s' "${got:-UNREADABLE - config.py did not import}"
    fi
}

change_brk_noprog() {
    local val
    echo ""
    echo "  Breakout no-progress exit: $(brk_noprog_label)"
    echo ""
    echo "  After 2 closed 1m bars with no new extreme in the trade's direction,"
    echo "  a Breakout that has made less than 0.5 R of progress is CUT."
    echo "  trade - cut it (the mark ladder), and record the cut."
    echo "  log   - record what the cut would do; trade as before."
    echo "  off   - neither."
    echo ""
    read -p "    Mode (trade / log / off, blank to clear): " val
    val="${val// /}"; val="${val,,}"
    if [[ -z "$val" ]]; then
        drop_env "OT_BRK_NOPROG"
        reload_daemon
        echo "  No-progress mode cleared - $(brk_noprog_label)."
        return
    fi
    if [[ "$val" != "trade" && "$val" != "log" && "$val" != "off" ]]; then
        print_warn "REFUSED - '$val' is not trade, log or off. Nothing written."
        return
    fi
    set_env "OT_BRK_NOPROG" "$val"
    reload_daemon
    echo "  Breakout no-progress exit set to $val."
}

# ── r266 (STOP.1) — THE RESTING STOP: off | trade (paper only) ─────────────
resting_stop_label() {
    local v got
    v=$(get_env "OT_RESTING_STOP")
    got=$(cd "$BOT_DIR" && OT_RESTING_STOP="$v" python3 -c \
        "import config; print(config.RESTING_STOP_MODE + (' (set to ' + config.RESTING_STOP_ENV_REFUSED + ' - REFUSED)' if config.RESTING_STOP_ENV_REFUSED else ''))")
    if [[ -z "$v" ]]; then
        printf 'not set (code default: %s)' "${got:-UNREADABLE - config.py did not import}"
    else
        printf '%s' "${got:-UNREADABLE - config.py did not import}"
    fi
}

change_resting_stop() {
    local val
    echo ""
    echo "  Resting stop: $(resting_stop_label)"
    echo ""
    echo "  trade - a fired hard stop / trail stop RESTS a sell at its own level for"
    echo "          120 s; filled there if price comes back, else closed at the mark"
    echo "          (at once if it falls 5% of entry further). PAPER ONLY."
    echo "  off   - stops close at the mark as before."
    echo ""
    read -p "    Mode (trade / off, blank to clear): " val
    val="${val// /}"; val="${val,,}"
    if [[ -z "$val" ]]; then
        drop_env "OT_RESTING_STOP"
        reload_daemon
        echo "  Resting stop cleared - $(resting_stop_label)."
        return
    fi
    if [[ "$val" != "trade" && "$val" != "off" ]]; then
        print_warn "REFUSED - '$val' is not trade or off. Nothing written."
        return
    fi
    set_env "OT_RESTING_STOP" "$val"
    reload_daemon
    echo "  Resting stop set to $val."
}

# ── OTV5 r57 (TCS.LOG1) — TCS: 1 (trade) | log (a shadow trade) | 0 (off), UNSET = log ─────────────
tcs_label() {
    local v got
    v=$(get_env "OT_TCS_ACTIVE")
    got=$(cd "$BOT_DIR" && OT_TCS_ACTIVE="$v" python3 -c \
        "import config; print(config.TCS_MODE + (' (set to ' + config.TCS_ENV_REFUSED + ' - REFUSED)' if config.TCS_ENV_REFUSED else ''))")
    if [[ -z "$v" ]]; then
        printf 'not set (code default: %s)' "${got:-UNREADABLE - config.py did not import}"
    else
        printf '%s' "${got:-UNREADABLE - config.py did not import}"
    fi
}

change_tcs() {
    local val
    echo ""
    echo "  TCS: $(tcs_label)"
    echo ""
    echo "  The trend credit spread (11:31-15:40): a credit spread on the side"
    echo "  the trend leaves behind; exits: breach of its bound, the nickel, else"
    echo "  the end-of-day close."
    echo "  1   - trade it (retired by ruling 2026-10-03; 1 restores it)."
    echo "  log - a SHADOW trade: the real entry and exits at the paper fill,"
    echo "        booked to shadow_trades.db, NEVER ordered (the default since r57)."
    echo "  0   - off: not asked, nothing written."
    echo ""
    read -p "    Mode (1 / log / 0, blank to clear): " val
    val="${val// /}"; val="${val,,}"
    if [[ -z "$val" ]]; then
        drop_env "OT_TCS_ACTIVE"
        reload_daemon
        echo "  TCS cleared - $(tcs_label)."
        return
    fi
    if [[ "$val" != "1" && "$val" != "log" && "$val" != "0" ]]; then
        print_warn "REFUSED - '$val' is not 1, log or 0. Nothing written."
        return
    fi
    set_env "OT_TCS_ACTIVE" "$val"
    reload_daemon
    echo "  TCS set to $val - $(tcs_label)."
}

# ── r136 — DATA CAPTURE: managed (the conductor owns this box's data) or
# standalone (nothing is pushed). One implementation: deploy/data_capture.sh.
data_capture_label() {
    bash "$BOT_DIR/deploy/data_capture.sh" status 2>/dev/null | head -1 | sed 's/^data capture: //'
}

change_data_capture() {
    echo ""
    echo "  Data capture: $(data_capture_label)"
    echo ""
    echo "  MANAGED    - the day_trader_pro conductor owns this box's data: S3 push,"
    echo "               candle-logger and the 16:45 self-close ON; this box's own"
    echo "               16:05 purge OFF (the conductor runs it). Pushes as its own"
    echo "               symbol; never the VIX family."
    echo "  STANDALONE - nothing is pushed (s3-push masked); this box purges itself"
    echo "               at 16:05. The reference QQQ box is standalone."
    echo ""
    [[ -f "$CAPTURE_REQUESTED_FILE" ]] && echo "  (the install's bootstrap asked for: $(cat "$CAPTURE_REQUESTED_FILE"))"
    if ask_yn "Make this box MANAGED (push to the warehouse)?"; then
        if ! capture_guard_ok; then
            print_warn "Left as it was - not MANAGED."
            return
        fi
        mkdir -p "$(dirname "$CAPTURE_CHOICE_FILE")"
        echo managed > "$CAPTURE_CHOICE_FILE"
        rm -f "$PUSH_PAUSE_FILE"
        if first_start_pending; then
            print_ok "MANAGED recorded - Done applies it after the bot's first start."
        else
            bash "$BOT_DIR/deploy/data_capture.sh" managed
        fi
    else
        mkdir -p "$(dirname "$CAPTURE_CHOICE_FILE")"
        echo standalone > "$CAPTURE_CHOICE_FILE"
        rm -f "$PUSH_PAUSE_FILE"
        bash "$BOT_DIR/deploy/data_capture.sh" standalone
    fi
}

capture_guard_ok() {
    # CD.1 — a live read of the warehouse: who else pushed this symbol in the last 14 days? rc 0 clean,
    # 1 another host (named), 2 unreadable -> fail closed. Only a typed OVERRIDE goes past 1 or 2.
    local sym out rc=0 ans
    sym=$(get_env "OT_INSTRUMENT")
    out=$( cd "$BOT_DIR" && "$BOT_PY" tools/capture_guard.py "$sym" 2>&1 ) || rc=$?
    echo "$out" | sed 's/^/    /'
    [[ "$rc" == 0 ]] && return 0
    if [[ "$rc" == 1 ]]; then
        print_warn "Another box pushes ${sym}: a second pusher silently overwrites its rows in every report."
    else
        print_warn "The warehouse could not be read - MANAGED is refused rather than guessed."
    fi
    read -p "    Type OVERRIDE to make this box MANAGED anyway (anything else cancels): " ans
    [[ "$ans" == "OVERRIDE" ]]
}

change_pin_gate() {
    echo ""
    echo "  Pin-proximity gate: $(pin_gate_label)"
    echo ""
    echo "  ON  - a directional debit (ORB, Breakout, Runaway, VOLT, hunt) is"
    echo "        REFUSED when GEX is PINNING and price is within 0.32 EM of"
    echo "        the pin. (r97)"
    echo "  OFF - no refusal. Pin distance is still recorded on every fire."
    echo "  The GEX pin butterfly is NOT affected either way."
    echo ""
    if ask_yn "Turn the pin-proximity gate ON?"; then
        set_env "OT_PIN_PROXIMITY_ACTIVE" "1"
        reload_daemon
        echo "  Pin-proximity gate ON."
    else
        set_env "OT_PIN_PROXIMITY_ACTIVE" "0"
        reload_daemon
        echo "  Pin-proximity gate OFF."
    fi
}



# ── r203 — SPOT, FOR SIZING THE ORB BUDGET AGAINST ────────────────────────
# 🔴 THIS FUNCTION SHIPPED BROKEN IN r201 AND THE FLEET BAKED IT. It read
# `<install>/data/orb_state.json` and `<install>/data/trades.db`. Neither
# exists: both files sit at the install root, and both paths were already in
# config.py — DB_PATH at 1604, LOG_FILE at 1613 — with orb_state.json written
# beside the log (main.py ~1358). I invented a subdirectory instead of reading
# two lines I had edited an hour earlier.
# 🔴 AND `2>/dev/null` TURNED THE FAILURE INTO A BLANK LINE. That was a
# deliberate choice, made to keep this screen tidy, on a feature whose entire
# job is to display a number. Silence over noise is the failure class this
# project exists to hunt, committed inside a display.
# 🔴 THE TEST COULD NOT FAIL. I built a fixture directory matching my own guess
# and verified against it. It passed, and it proved only that the guess was
# consistent with itself. The r201 land gate asserted the function EXISTED and
# that configure.sh PARSED — neither asks whether it produces output.
# 🔑 THE FIX, AND WHY IT IS SHAPED THIS WAY:
#   · paths are IMPORTED from config, never spelled here, so a future move of
#     either file cannot silently blank this display;
#   · stderr is NOT suppressed — every failure names itself and its path;
#   · the r203 land gate RUNS this body against a planted repo and REQUIRES a
#     Spot line back, and refuses both a literal `data/` path and any
#     re-suppression of stderr on this call.
# ── r161 (SIZE.2) — POSITION SCALING PER TRADE, ON OR OFF ──────────────────
# ON  = the ramp: risk the MIN at the structure stop, up to the TOP deployed.
# OFF = flat: about the MIN in premium, whatever the stop distance. The
#       structure stop, the exits and the noise floor do not change.
# Only the literal "1" is ON in config.py, so a bad value reads as OFF (the
# smaller position). Unset shows the code default read from config.py (r91).
scaling_label() {
    local key="$1" attr="$2" v dflt
    v=$(get_env "$key")
    if [[ "$v" == "1" ]]; then printf 'ON'; return; fi
    if [[ "$v" == "0" ]]; then printf 'OFF'; return; fi
    if [[ -n "$v" ]]; then printf 'OFF (set to %s; only 1 is on)' "$v"; return; fi
    dflt=$(cd "$BOT_DIR" && env -u "$key" python3 -c \
        "import config; print('ON' if config.${attr} else 'OFF')")
    printf 'not set (code default: %s)' "${dflt:-UNREADABLE - config.py did not import}"
}

# The summary line's short form: ON / OFF as set, or "unset=ON" naming the
# code default — still never a value the operator did not choose (r91).
scaling_short() {
    local l; l=$(scaling_label "$1" "$2")
    case "$l" in
        ON|OFF) printf '%s' "$l" ;;
        OFF*)   printf 'OFF' ;;
        "not set (code default: "*) l=${l#not set (code default: }; printf 'unset=%s' "${l%)}" ;;
        *)      printf '%s' "$l" ;;
    esac
}

change_scaling() {
    local key="$1" attr="$2" name="$3"
    echo ""
    echo "  ${name} scaling: $(scaling_label "$key" "$attr")"
    echo ""
    echo "  ON  - size on the ramp: risk the MIN at the structure stop,"
    echo "        up to the ramp TOP deployed (tight stop = bigger size)."
    echo "  OFF - flat: about the MIN in premium, whatever the stop."
    echo "  Either way the structure stop and exits are unchanged."
    echo ""
    if ask_yn "Turn ${name} scaling ON?"; then
        set_env "$key" "1"
        reload_daemon
        echo "  ${name} scaling ON."
    else
        set_env "$key" "0"
        reload_daemon
        echo "  ${name} scaling OFF (flat size)."
    fi
}

change_orb_budget() {
    local current risk
    current=$(get_env "OT_ORB_BUDGET_USD")
    risk=$(get_env "OT_RISK_USD")
    echo ""
    echo -e "  ${BOLD}Scaling ramp TOP (MAX)${RESET}  (OT_ORB_BUDGET_USD)"
    echo -e "  The most premium one scaled trade (ORB/Breakout/VOLT) may deploy."
    echo ""
    echo -e "  Current: ${BOLD}$(fmt_declared "$current")${RESET}"
    echo ""
    while true; do
        read -p "    New ramp TOP in \$, 'r' to reset to default, ENTER to keep: " input
        if [[ -z "$input" ]]; then
            print_info "Unchanged."
            return
        fi
        if [[ "$input" == "r" ]]; then
            set_env "OT_ORB_BUDGET_USD" "$risk"
            reload_daemon
            print_ok "Ramp TOP reset to the per-trade risk default (\$${risk})."
            return
        fi
        if [[ "$input" =~ ^[0-9]+(\.[0-9]+)?$ ]] && (( $(echo "$input > 0" | bc -l) )); then
            set_env "OT_ORB_BUDGET_USD" "$input"
            reload_daemon
            print_ok "Ramp TOP updated to ${BOLD}\$$input${RESET}."
            return
        fi
        print_warn "Enter a positive number, 'r' to reset, or ENTER to keep."
    done
}

change_daily_loss() {
    local current risk
    current=$(get_env "OT_DAILY_LOSS_LIMIT")
    risk=$(get_env "OT_RISK_USD")
    echo ""
    echo -e "  ${BOLD}Daily catastrophic loss cap${RESET} — no NEW entries while the"
    echo -e "  day's REALIZED net is down by this amount. Open trades are still"
    echo -e "  managed; entries re-open once closes bring it back under."
    echo -e "  Current: ${BOLD}$(fmt_declared "$current")${RESET}"
    echo ""
    while true; do
        read -p "    New cap in \$, 'r' to reset to risk default, ENTER to keep: " input
        if [[ -z "$input" ]]; then
            print_info "Unchanged."
            return
        fi
        if [[ "$input" == "r" ]]; then
            set_env "OT_DAILY_LOSS_LIMIT" "$risk"
            reload_daemon
            print_ok "Catastrophic loss cap reset to per-trade risk (\$${risk})."
            return
        fi
        if [[ "$input" =~ ^[0-9]+(\.[0-9]+)?$ ]] && (( $(echo "$input > 0" | bc -l) )); then
            set_env "OT_DAILY_LOSS_LIMIT" "$input"
            reload_daemon
            print_ok "Catastrophic loss cap updated to ${BOLD}\$$input${RESET}."
            return
        fi
        print_warn "Enter a positive number, 'r' to reset, or ENTER to keep."
    done
}

change_mode() {
    local current
    current=$(get_env "OT_PAPER_TRADING")
    echo ""
    if [[ "$current" == "False" ]]; then
        echo -e "  Current mode: ${RED}${BOLD}🔴 LIVE${RESET}"
        echo ""
        if ask_yn "Switch to PAPER mode?"; then
            set_env "OT_PAPER_TRADING" "True"
            reload_daemon
            archive_trades_db "live"
            print_ok "Switched to ${BOLD}📄 PAPER mode${RESET}."
        else
            print_info "Unchanged: LIVE."
        fi
    else
        echo -e "  Current mode: ${GREEN}📄 PAPER${RESET}"
        echo ""
        print_warn "You are about to enable LIVE TRADING."
        print_warn "Real orders will be placed with real money."
        echo ""
        read -p "    Type  LIVE  to confirm: " confirm
        if [[ "$confirm" == "LIVE" ]]; then
            set_env "OT_PAPER_TRADING" "False"
            reload_daemon
            archive_trades_db "paper"
            print_ok "Switched to ${RED}${BOLD}🔴 LIVE mode${RESET}."
            # v1.9: broker reconciliation follows the mode (config.py default) —
            # LIVE turns it on automatically unless OT_BROKER_RECONCILE pins it.
            local rec_pin
            rec_pin=$(get_env "OT_BROKER_RECONCILE")
            if [[ "$rec_pin" == "False" ]]; then
                print_warn "Broker reconciliation is PINNED OFF (OT_BROKER_RECONCILE=False in the unit file) — phantoms and manual closes will NOT be reconciled."
            else
                print_ok "Broker reconciliation: auto-enabled with LIVE mode."
            fi
        else
            print_info "Confirmation not received — mode unchanged."
        fi
    fi
}

change_tt_credentials() {
    echo ""
    echo -e "  Update your TastyTrade OAuth credentials."
    echo -e "  ${CYAN}Leave blank and press ENTER to keep the current value.${RESET}"
    echo ""

    local current_secret current_token current_account
    current_secret=$(get_env "TT_CLIENT_SECRET")
    current_token=$(get_env "TT_REFRESH_TOKEN")
    current_account=$(get_env "TT_ACCOUNT_NUMBER")

    read -s -p "    New Client Secret  [ENTER to keep current]: " new_secret; echo ""
    read -s -p "    New Refresh Token  [ENTER to keep current]: " new_token;  echo ""
    read -p    "    Account Number     [ENTER to keep ${current_account}]: " new_account

    local changed=false
    if [[ -n "$new_secret" ]]; then
        set_env "TT_CLIENT_SECRET"  "$new_secret";  changed=true; fi
    if [[ -n "$new_token" ]]; then
        set_env "TT_REFRESH_TOKEN"  "$new_token";   changed=true; fi
    if [[ -n "$new_account" ]]; then
        set_env "TT_ACCOUNT_NUMBER" "$new_account"; changed=true; fi

    if [[ "$changed" == "true" ]]; then
        reload_daemon
        print_ok "TastyTrade credentials updated."
    else
        print_info "No credentials changed."
    fi
}

change_telegram() {
    local current_token current_chat
    current_token=$(get_env "TELEGRAM_TOKEN")
    current_chat=$(get_env "TELEGRAM_CHAT_ID")
    echo ""

    if [[ -n "$current_token" ]]; then
        echo -e "  Telegram alerts are currently ${GREEN}enabled${RESET}."
        echo -e "  Chat ID: ${BOLD}${current_chat}${RESET}"
    else
        echo -e "  Telegram alerts are currently ${YELLOW}disabled${RESET}."
    fi

    echo ""
    echo -e "  ${CYAN}Press ENTER on any field to keep the current value.${RESET}"
    echo ""

    read -p "    Bot Token [ENTER = no change]: " new_token
    read -p "    Chat ID   [ENTER = no change, current: ${current_chat}]: " new_chat

    local changed=false
    if [[ -n "$new_token" ]]; then
        set_env "TELEGRAM_TOKEN" "$new_token"
        changed=true
    fi
    if [[ -n "$new_chat" ]]; then
        set_env "TELEGRAM_CHAT_ID" "$new_chat"
        changed=true
    fi

    if [[ "$changed" == "true" ]]; then
        reload_daemon
        print_ok "Telegram settings updated."
    else
        print_info "No changes made."
    fi
}

# ── r138 — THE DONE PATH: enable + start a stopped bot, restart a changed one ─
finish_session() {
    if first_start_pending && bot_is_running; then
        # a box that was already running before CD.1 has had its start: mark it, change nothing about it
        mkdir -p "$(dirname "$FIRST_START_FILE")"
        echo "already running before CD.1 ($(date -u +%Y-%m-%dT%H:%M:%SZ))" > "$FIRST_START_FILE"
    fi
    if first_start_pending; then
        first_start
        return
    fi
    if ! bot_is_running; then
        echo ""
        echo "  Starting the bot (and enabling it at boot)..."
        sudo systemctl enable "$SERVICE_NAME" >/dev/null 2>&1
        sudo systemctl start "$SERVICE_NAME"
        sleep 4
        if bot_is_running; then
            print_ok "Bot started with these settings."
        else
            print_warn "Bot failed to start — check: journalctl -u ${SERVICE_NAME} -n 20"
        fi
    elif [[ "$CHANGED" == "true" ]]; then
        echo ""
        show_config
        sudo systemctl enable "$SERVICE_NAME" >/dev/null 2>&1
        auto_restart
    fi
}

auto_restart() {
    echo ""
    echo "  Applying changes and restarting bot..."
    sudo systemctl restart "$SERVICE_NAME"
    sleep 4
    if bot_is_running; then
        print_ok "Bot restarted successfully with new settings."
    else
        print_warn "Bot failed to start — check: journalctl -u ${SERVICE_NAME} -n 20"
    fi
}

# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

if [[ "${1:-}" == "--show" ]]; then
    print_banner
    show_config
    exit 0
fi

if [[ ! -f "$UNIT_FILE" ]]; then
    print_banner
    echo -e "  ${RED}No service unit found at ${UNIT_FILE}${RESET}"
    echo -e "  Run setup_ec2.sh first to install and configure the bot."
    echo ""
    exit 1
fi

print_banner
show_config

CHANGED=false
while true; do
    echo -e "  ${BOLD}What would you like to change?${RESET}"
    echo ""
    echo -e "  ${BOLD}1.${RESET}  Instrument          (currently: $(get_env OT_INSTRUMENT))"
    echo -e "  ${BOLD}2.${RESET}  Risk/trade, ramp MIN (currently: \$$(get_env OT_RISK_USD))"
    echo -e "  ${BOLD}3.${RESET}  Paper / Live mode   (currently: $([ "$(get_env OT_PAPER_TRADING)" = "False" ] && echo "🔴 LIVE" || echo "📄 PAPER"))"
    echo -e "  ${BOLD}4.${RESET}  Telegram alerts     (chat: $(get_env TELEGRAM_CHAT_ID))"
    echo -e "  ${BOLD}5.${RESET}  TastyTrade credentials"
    echo -e "  ${BOLD}6.${RESET}  Catastrophic cap    (currently: \$$(dll=$(get_env OT_DAILY_LOSS_LIMIT); echo ${dll:-$(get_env OT_RISK_USD)}))"
    echo -e "  ${BOLD}7.${RESET}  Pin-proximity gate  (currently: $(pin_gate_label))"
    echo -e "  ${BOLD}8.${RESET}  Ramp TOP (MAX)      (currently: $(fmt_declared "$(get_env OT_ORB_BUDGET_USD)"))"
    echo -e "  ${BOLD}9.${RESET}  Breakout scaling    (currently: $(scaling_label OT_SCALE_BREAKOUT SCALE_BREAKOUT))"
    echo -e "  ${BOLD}10.${RESET} Runaway entry end   (currently: $(runaway_end_label))"
    echo -e "  ${BOLD}11.${RESET} Breakout entry end  (currently: $(breakout_end_label))"
    echo -e "  ${BOLD}12.${RESET} Breakout no-progress (currently: $(brk_noprog_label))"
    echo -e "  ${BOLD}13.${RESET} Resting stop        (currently: $(resting_stop_label))"
    echo -e "  ${BOLD}14.${RESET} Data capture        (currently: $(data_capture_label))"
    echo -e "  ${BOLD}15.${RESET} TCS                 (currently: $(tcs_label))"
    echo -e "  ${BOLD}16.${RESET} Done"
    echo ""
    read -p "    Select [1-16]: " menu_choice

    case "$menu_choice" in
        1) change_instrument; CHANGED=true ;;
        2) change_risk;       CHANGED=true ;;
        3) change_mode;       CHANGED=true ;;
        4) change_telegram;       CHANGED=true ;;
        5) change_tt_credentials; CHANGED=true ;;
        6) change_daily_loss;     CHANGED=true ;;
        7) change_pin_gate;       CHANGED=true ;;
        8) change_orb_budget;     CHANGED=true ;;
        9) change_scaling OT_SCALE_BREAKOUT SCALE_BREAKOUT "Breakout"; CHANGED=true ;;
        10) change_runaway_end;   CHANGED=true ;;
        11) change_breakout_end;  CHANGED=true ;;
        12) change_brk_noprog;    CHANGED=true ;;
        13) change_resting_stop;  CHANGED=true ;;
        14) change_data_capture ;;
        15) change_tcs;           CHANGED=true ;;
        16) break ;;
        *) print_warn "Please enter a number between 1 and 16." ;;
    esac
    echo ""
done

finish_session

echo ""
