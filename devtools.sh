#!/usr/bin/env bash
# ==========================================================================
# devtools.sh  v5.1  — OTV5 box menu
# v5.1  2026-10-25  OTV5 r13 (BOOT.12) — CLAUDE CODE gains AT BOOT: turns the boot raise ON (deploy/install_claude_boot.sh:
#       install and enable optbot-claude-boot; nothing is raised now) or OFF (disable the unit; a session running now is
#       left running). The operator, 2026-10-25: the Claude-at-boot switch belongs in devtools, not configure.sh, and
#       must be able to stop Claude coming up at every subsequent start.
# v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
# v3.12 2026-10-24  OTV5 r0 — GIT STATE reads the one ledger, docs/GENESIS.md (this tree has no second
#       ledger). Title: OTV5 box menu.
# v3.11 2026-10-23  OTV4TEST r314 (MENU.2) — HAND OFF / RESUME / RESUME [other]
#       RAISE UNDER THE BOX'S OWN NAME. All three passed `--remote-control
#       qqq-test`, so on SPX-TEST they raised under QQQ-TEST's name (2026-10-23,
#       fixed that morning by hand with /rename). The name now comes from
#       `tools/claude_boot.py --rc-name` (OT_RC_NAME, else ✨<INSTRUMENT>-TEST),
#       read BEFORE anything is purged or killed; no name -> refused. The
#       operator, 11:10 ET: "Yes to both".
# v3.10 2026-10-23  OTV4TEST r313 (MENU.1) — CLAUDE CODE gains RESTART: a fresh
#       session raised by the boot unit (`sudo systemctl restart
#       optbot-claude-boot`), so it carries the unit's OT_RC_NAME, its brief and
#       claude_boot.py's first-turn check. The operator, 2026-10-23 10:04 ET:
#       "Make the sudo systemctl restart optbot-claude-boot a devtools menu item
#       in the Claude section". WHY: that morning SPX-TEST's 08:05 boot hit an
#       expired login; the hand raise from an SSH shell had no OT_RC_NAME (it
#       lives only in the unit) and came up under QQQ-TEST's default name.
#       It ENDS the tmux session first, because bring_up() returns "already
#       running" over any live claude in it and a bare restart raises nothing.
#       Appended last in CLAUDE CODE; GIT & LAND items move down one.
# v3.9  2026-09-24  OTV4TEST r130 — R SUITE gains OPEN SCAN: today's two reports
#       from tools/open_scan.py (09:35 ready, 09:45 live), and a RUN NOW for
#       either phase. Read-only. Operator: "the scan you just ran should be done
#       every trading day". Appended after STOP VS SPREAD; nothing moves.
# v3.8  2026-09-24  OTV4TEST r129 — R SUITE gains STOP VS SPREAD, the Saturday
#       review of criteria.stop_survivable: how often a fly or vertical was
#       refused because its stop could not clear its own bid-ask, how close the
#       rest came, and whether the rule was the one that declined the tick.
#       Operator: "we can build that & review it on Saturdays with our other
#       reviews" — "Both" (flies and verticals). It reads the DERIVED store
#       (plan_check), not trades.db, so it has its own date prompt; ENTER is
#       the last 7 days — the Saturday week. Read-only. Appended after Edge
#       scan so no existing item moves.
# v3.7  2026-09-23  OTV4TEST r119 — MAINLINE'S TRADE REPORTS REPLACE ITEM 35.
#       Operator: "let's get those reports borrowed, repurposed & added to our
#       devtools menu. You can retire our current one option 35 — I hate it."
#       The raw 30-row SQL dump (UTC stamps, wrapped columns) is GONE; its
#       place in R SUITE is TRADE BREAKDOWN (mainline 47) followed by TRADES
#       TAKEN (mainline 48), both tests/trade_report.py over THIS box's
#       trades.db, read-only. Every item after it moves down one.
# v3.6  2026-09-20  OTV4TEST r70 (BOX.12/AUTH.1) — PURGE, THEN KILL, THEN
#       LAUNCH ON THE SUBSCRIPTION. HAND OFF and RESUME PURGE THE
#       tmpfs SCRATCHPADS after killing tmux. /tmp is RAM here (455 MB tmpfs of
#       908 MB physical) and session scratchpads are keyed by session id, so
#       they accumulate forever. A full tmpfs kills every Bash spawn silently —
#       which is exactly what happened on the control box. Transcripts are on
#       ext4 and unaffected, so the previous thread is still reviewable.
# v3.5  2026-09-20  OTV4TEST r67 (BOX.9) — bake() STAMPS THE SHUTDOWN CAUSE so
#       the bot's STOPPED alert says "bake" rather than the same
#       "systemctl stop/restart" a hand stop and the midnight halt both printed.
# v3.4  2026-09-18  OTV4TEST r42 — PLAN STATUS NOW: what every plan is doing at
#       this moment and since when. Operator: "can you just have each plan report
#       its last known status & a time stamp?" ⚠️ It is the TRANSITION STREAM READ
#       BACKWARDS, not a new table and not restored per-tick logging — r41 made the
#       board edge-triggered, so the newest plan_tick row for a strategy IS its last
#       known status and the moment it changed. Continuous logging would cost ~12k
#       rows a day (measured 2026-09-17) to repeat what the newest row already says.
#       It sits BESIDE the existing PLAN BOARD, which is a chosen day's history.
# v3.3  2026-09-18  OTV4TEST r37 — THE BAKE WAS HALF A BAKE. It restarted the BOT
#       only, and it never purged __pycache__ — the one thing the operating notes
#       name as "the single most common cause of I pushed the fix but it is still
#       broken". So r36's Quote subscription, which lives in candle_feed.py, could
#       not have taken from a menu bake, and any bake could serve stale bytecode
#       while printing a green line. Operator's sequence, adopted verbatim: stop
#       both, pull, purge, start the FEED first, then the bot, report both.
# v3.2  2026-09-17  OTV4TEST r34 — items 1, 2 and 3 run status.py and query.py at
#       the REPO ROOT again. r14 had moved them to tools/ and this menu followed;
#       the operator runs them by hand and the root is where he looks.
# v3.1  2026-09-17  OTV4TEST — EVERY CLAUDE SESSION THIS MENU STARTS IS A
#       REMOTE CONTROL SESSION. Operator's instruction: he drives these threads
#       from his phone, and a session started without it cannot be reached from
#       the chat thread. All four launch sites carry `--remote-control qqq-test`.
#       ⚠️ THE NAME IS PASSED EXPLICITLY AND THAT IS LOAD-BEARING, NOT TIDINESS:
#       the flag's argument is OPTIONAL (`--remote-control [name]`), so on the
#       HAND OFF site — the only one that also passes a positional prompt — a
#       bare flag could swallow the whole of docs/HANDOFF.md as the session
#       NAME and hand Claude no brief at all. Naming it removes the ambiguity.
# v3.0  2026-09-13  OTV4TEST r17 — THE MENU IS READ ON A PHONE. Reformatted to
#       control's shape: a 54-column rule, a title line, sections as " NAME:",
#       items as "  NN) label" — and every line fits 54 columns, because a label
#       that runs past the rule WRAPS in Termius and a wrapped menu is the one
#       misread at 09:35 (items 41 and 43 wrapped at v2.4). Colour is control's
#       exactly: the render prints PLAIN text and a sed pass paints the rules,
#       the title and the section headers, suppressed when stdout is not a TTY,
#       so no escape ever sits inside a label. NEW SECTION — CLAUDE CODE, adapted
#       to this box: HAND OFF (a fresh thread bootstrapped from docs/HANDOFF.md —
#       the operator's own brief, replacing the inherited v4 handoff of 2026-08-20
#       which named PORT_STATE.md and was stale by its own header),
#       REATTACH (the running session), RESUME (--continue), RESUME [other]
#       (--resume). A one-time docs/HANDOFF_NOW.md, when present, is POINTED AT
#       by one appended line rather than folded into the brief, so the brief never
#       drifts and the note expires by being deleted. Claude runs inside tmux here, always, so a dropped mobile
#       connection cannot kill a working thread; three of the four `exec`, which
#       is why the section says these items END the menu.
# v2.4  2026-09-11  OTV4TEST r14 — the operator readers live in tools/ (root cleanup);
#       REINSTALL TIMERS added under GIT & LAND for the one-time unit rewrite.
# v2.3  2026-09-09  OTV4TEST r8 — BAKE runs `systemctl daemon-reload` before the
#       restart (the unit file changed on disk and systemd said so at r7's bake).
# v2.2  2026-09-09  OTV4TEST r7 — PLAN ROWS and PLAN BOARD hush DORMANT rows
#       (recorded, not shown; add them back with the prompt).
# v2.1  2026-09-09  OTV4TEST r6 — Feed health shows OPEN INTEREST: the last `OI:`
#       lines from the bot's journal (fetched / cached / NON-ZERO), so the
#       butterfly's un-park is a menu read, not a grep.
# v2.0  2026-09-08  OTV4TEST r4 — THE BOX MENU CATCHES UP WITH CONTROL.
#       Operator: this instance is standalone; control's devtools never reaches
#       it, and the box's own menu was the otv1-era break-glass list. The
#       control menu's BOT-SPECIFIC items are ported here to run LOCALLY —
#       SENSORS (the same SQL, over this box's own derived_store.db and
#       feed_store.db, an ET date prompt where control took one), DEBUG / LOGS,
#       and the R SUITE (the fork's own tests/r_ledger.py, stop_sweep.py,
#       exit_replay.py, edge_scan.py via their `--db` escape hatch on
#       trades.db — this box is masked from S3 by construction). Everything
#       about wrangling a fleet is deliberately absent. NEW sensors: PLAN ROWS
#       (the per-tick narrative) and LEVEL EVENTS (WICKED / REJECTED /
#       ACCEPTED, derived/levels v4.1, r3).
#       🔑 THE MENU IS DATA, as on control (dtp v1.32): MENU=(SECTION|… /
#       ITEM|label|function) rendered with numbers assigned at display time,
#       so nothing here cites a number — LAND and BAKE moved; their labels did
#       not. Existing functions are kept verbatim.
#       Version numbering restarts at 2.0 by the operator's request; the
#       v4.x lineage below is the file's history, not a downgrade.
# v4.4  2026-09-08  OTV4TEST r3 — LAND auto-selects a lone archive; BAKE added.
# v4.3  2026-09-08  OTV4TEST r1 — LAND a tarball (the fork lander).
# v4.2  2026-09-08  r322 — the comment markers (this script had done nothing
#       since 2026-08-25: a changelog line written as shell aborted the parse).
# v4.1  2026-08-25  r65 EXORCISM.  v4.0  2026-08-19  ported at the OTV4 split.
# ==========================================================================
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$REPO/venv/bin/python"
export PYTHONPATH="$REPO"
BOT="optionsbot"          # systemd unit (setup_ec2.sh SERVICE_NAME)
FEED="candle-feed"        # systemd unit (single DXFeed producer)
CLAUDE_UNIT="optbot-claude-boot"  # systemd unit (tools/claude_boot.py, BOX.11)
BOTLOG="$REPO/bot.log"    # ExecStartPre touches this in the unit
DERIVED_DB="${OT_DERIVED_DB:-$REPO/data/derived_store.db}"
FEED_DB="$REPO/data/feed_store.db"
TRADES_DB="$REPO/trades.db"
cd "$REPO" 2>/dev/null || { echo "cannot cd to $REPO"; exit 1; }
[ -x "$PY" ] || echo "warn: no venv python at $PY — python items will fail"

pause()   { read -rp $'\n[enter] '; }
confirm() { read -rp "$1 [y/N] " a; case "${a:-}" in y|Y|yes|YES|Yes) return 0 ;; *) return 1 ;; esac; }
svc()     { systemctl is-active "$1" 2>/dev/null || echo "unknown"; }
_sql()    { # $1 db, $2 sql — header+column, like control
  [ -f "$1" ] || { echo "  no store at $1"; return 0; }
  sqlite3 -header -column "$1" "$2" 2>&1
}
_et_bounds() {  # $1 = YYYY-MM-DD -> ET_FROM / ET_TO epoch (ET midnight to midnight)
  local nxt; nxt=$(date -d "$1 +1 day" +%F 2>/dev/null)
  ET_FROM=$(TZ=America/New_York date -d "$1 00:00:00" +%s 2>/dev/null)
  ET_TO=$(TZ=America/New_York date -d "$nxt 00:00:00" +%s 2>/dev/null)
  [ -n "$ET_FROM" ] && [ -n "$ET_TO" ] || { echo "  bad date: $1 (YYYY-MM-DD)"; return 1; }
}
_ask_day() {    # prompts; ENTER = today in ET
  local today; today=$(TZ=America/New_York date +%F)
  read -rp "  Session date (YYYY-MM-DD, ENTER = $today): " d
  _et_bounds "${d:-$today}"
}

# ── STATUS ─────────────────────────────────────────────────────────────────
run_status()    { "$PY" status.py; pause; }
run_query()     { "$PY" query.py; pause; }
run_decisions() { "$PY" query.py --decisions; pause; }
run_debug()     { "$PY" tools/debug_status.py; pause; }
run_eod()       { "$PY" tools/eod_summary.py; pause; }

# ── SENSORS (this box's derived stores; read-only) ─────────────────────────
s_manifold() { echo; echo "  Per-stream bulbs from tools/manifold_health.py."; "$PY" tools/manifold_health.py; pause; }
s_notes() {
  echo; echo "  Source: derived_store.db -> strategy_note (what each engine SAW)"; _ask_day || { pause; return; }
  _sql "$DERIVED_DB" "SELECT strategy, SUM(fired) AS signalled, COUNT(*)-SUM(fired) AS quiet, COUNT(*) AS looks FROM strategy_note WHERE ts_epoch >= $ET_FROM AND ts_epoch < $ET_TO GROUP BY strategy ORDER BY looks DESC;"; pause; }
s_plan_board() {
  echo; echo "  Source: derived_store.db -> plan_tick + plan_check"; _ask_day || { pause; return; }
  _sql "$DERIVED_DB" "SELECT strategy, verdict, COUNT(*) n, ROUND(MIN(r_now),2) r_lo, ROUND(MAX(r_now),2) r_hi, ROUND(AVG(underlying),2) px FROM plan_tick WHERE ts_epoch >= $ET_FROM AND ts_epoch < $ET_TO AND verdict <> 'DORMANT' GROUP BY strategy, verdict ORDER BY strategy, verdict;"
  echo; echo "  WHICH CHECK FAILED, AND HOW OFTEN:"
  _sql "$DERIVED_DB" "SELECT strategy, check_name, verdict, COUNT(*) n, ROUND(MIN(value),2) lo, ROUND(MAX(value),2) hi FROM plan_check WHERE ts_epoch >= $ET_FROM AND ts_epoch < $ET_TO GROUP BY strategy, check_name, verdict ORDER BY strategy, check_name, verdict;"; pause; }
s_plan_status() {
  # r42 — WHAT EVERY PLAN IS DOING RIGHT NOW. Operator, 2026-09-18: "can you
  # just have each plan report its last known status & a time stamp?"
  # ⚠️ IT IS THE TRANSITION STREAM READ BACKWARDS, NOT A NEW TABLE. r41 made the
  # board edge-triggered, so the NEWEST plan_tick row for a strategy IS its last
  # known status and the moment it changed. Nothing is written.
  echo; "$PY" "$REPO/tools/plan_board.py" "$@"; pause; }
s_plan_status_all() { echo; "$PY" "$REPO/tools/plan_board.py" --all; pause; }
s_plan_rows() {
  echo; echo "  Source: derived_store.db -> plan_tick, the ROWS (newest last) — the per-tick narrative"; _ask_day || { pause; return; }
  read -rp "  Strategy (ENTER = all): " S; local W=""; [ -n "$S" ] && W=" AND strategy='$S'"
  read -rp "  How many rows [40]: " N; N="${N:-40}"
  read -rp "  Show DORMANT rows too? [y/N] " D; local H=" AND verdict <> 'DORMANT'"; case "${D:-}" in y|Y) H="";; esac
  _sql "$DERIVED_DB" "SELECT * FROM (SELECT datetime(ts_epoch,'unixepoch','-4 hours') AS et, strategy, verdict, substr(reason,1,150) AS reason FROM plan_tick WHERE ts_epoch >= $ET_FROM AND ts_epoch < $ET_TO$W$H ORDER BY ts_epoch DESC LIMIT $N) ORDER BY et;"; pause; }
s_plan_ledger() {
  echo; echo "  Source: derived_store.db -> plan_ledger (intent + terminal reason)"; _ask_day || { pause; return; }
  _sql "$DERIVED_DB" "SELECT strategy, state, COALESCE(terminal_reason,'(live)') AS reason, COUNT(*) AS n FROM plan_ledger WHERE created_ts >= $ET_FROM AND created_ts < $ET_TO GROUP BY strategy, state, reason ORDER BY n DESC;"; pause; }
s_exit_cf() {
  echo; echo "  Source: derived_store.db -> exit_counterfactual (flow vs the stop)"
  _sql "$DERIVED_DB" "SELECT trade_id, strategy, reason, COUNT(*) AS evals, MAX(threat) AS peak_threat, MAX(would_fire) AS would_have FROM exit_counterfactual GROUP BY trade_id, strategy, reason ORDER BY peak_threat DESC LIMIT 25;"; pause; }
s_fire_snapshot() {
  echo; echo "  Source: derived_store.db -> fire_snapshot (everything derived at the INSTANT a trade fired)"
  _sql "$DERIVED_DB" "SELECT trade_id, datetime(fired_ts,'unixepoch','-4 hours') AS fired_et, substr(payload,1,160) AS payload FROM fire_snapshot ORDER BY fired_ts DESC LIMIT 10;"; pause; }
s_surface() {
  echo; echo "  Source: derived_store.db -> surface_series (last 24h)"
  _sql "$DERIVED_DB" "SELECT strike, ROUND(AVG(charm),4) AS charm, ROUND(AVG(vanna),4) AS vanna, ROUND(MAX(gex)/1e6,2) AS gex_m, COUNT(*) AS n FROM surface_series WHERE ts_epoch > strftime('%s','now','-1 day') GROUP BY strike ORDER BY n DESC LIMIT 20;"; pause; }
s_indicators() {
  echo; echo "  Source: derived_store.db -> indicator_series (last 24h)"
  _sql "$DERIVED_DB" "SELECT interval, COUNT(*) AS n, ROUND(MIN(adx),1) AS adx_lo, ROUND(MAX(adx),1) AS adx_hi, ROUND(AVG(adx),1) AS adx_avg, ROUND(AVG(vwap),2) AS vwap FROM indicator_series WHERE ts_epoch > strftime('%s','now','-1 day') GROUP BY interval;"; pause; }
s_forks() {
  echo; echo "  Source: derived_store.db -> fork_series (built vs reject reason, last 24h)"
  _sql "$DERIVED_DB" "SELECT interval, CASE built WHEN 1 THEN 'BUILT' ELSE COALESCE(reject_reason,'?') END AS outcome, COUNT(*) AS n, ROUND(AVG(containment),3) AS contain FROM fork_series WHERE ts_epoch > strftime('%s','now','-1 day') GROUP BY interval, outcome ORDER BY n DESC;"; pause; }
s_levels() {
  echo; echo "  Source: derived_store.db -> level_ledger (touches + retirements)"
  _sql "$DERIVED_DB" "SELECT provenance, kind, COUNT(*) AS levels, SUM(touch_count) AS touches, SUM(CASE WHEN retired_ts IS NULL THEN 0 ELSE 1 END) AS retired FROM level_ledger GROUP BY provenance, kind ORDER BY touches DESC;"; pause; }
s_level_events() {
  echo; echo "  Source: derived_store.db -> level_event (WICKED / REJECTED / ACCEPTED — the rejection fact, r3)"; _ask_day || { pause; return; }
  _sql "$DERIVED_DB" "SELECT event, depth, COUNT(*) AS n FROM level_event WHERE ts_epoch >= $ET_FROM AND ts_epoch < $ET_TO GROUP BY event, depth ORDER BY event, depth;"
  echo; echo "  THE EVENTS, IN ORDER:"
  _sql "$DERIVED_DB" "SELECT bar_ts, event, kind, price, provenance, ROUND(pierce_pct*100,3) AS pierce_pct, depth, closes_back, bar_close FROM level_event WHERE ts_epoch >= $ET_FROM AND ts_epoch < $ET_TO ORDER BY ts_epoch, bar_ts LIMIT 60;"; pause; }
s_order_flow() {
  echo; echo "  Source: feed_store.db -> prints + quote_series (last 24h)"
  _sql "$FEED_DB" "SELECT COALESCE(aggressor_side,'(untagged)') AS side, COUNT(*) AS prints, ROUND(SUM(size)) AS volume FROM prints WHERE ts_epoch > strftime('%s','now','-1 day') GROUP BY side;"
  _sql "$FEED_DB" "SELECT COUNT(*) AS quote_rows, ROUND(AVG(bid_size)) AS avg_bid_sz, ROUND(AVG(ask_size)) AS avg_ask_sz FROM quote_series WHERE ts_epoch > strftime('%s','now','-1 day');"; pause; }

# ── TESTS ──────────────────────────────────────────────────────────────────
PYTEST_SUITE=(
  tests/test_entry_fill_confirmation.py
  tests/test_mode_isolation.py
  tests/test_phantom_pnl_recovery.py
  tests/test_roll_is_real.py
  tests/test_runner_refinements.py
)
run_suite() {
  if ! "$PY" -c "import pytest" 2>/dev/null; then
    echo "pytest not in this venv. Install with:"; echo "  $PY -m pip install pytest"; pause; return 1
  fi
  echo "── full regression suite (go-live gate) ─────────────────────────────"
  "$PY" -m pytest "${PYTEST_SUITE[@]}" -v; pause
}
run_standing() {
  # the lander's standing set, run by hand between landings
  echo "── standing checks (the lander runs these on every land) ─────────────"
  local rc=0
  for t in check_imports check_gates check_attr_fidelity check_plan_wiring check_orb_plan check_runaway_plan check_level_rejection check_land_tooling; do
    [ -f "tests/$t.py" ] || continue
    if "$PY" "tests/$t.py" >/tmp/dt_$t.log 2>&1; then echo "  PASS  $t"; else echo "  FAIL  $t  (see /tmp/dt_$t.log)"; rc=1; fi
  done
  [ "$rc" = 0 ] && echo "  ALL PASS" || echo "  RED — read the log before landing anything"
  pause
}
run_contract() { "$PY" -m tests.test_market_data_contract; pause; }
run_orb()      { "$PY" tests/test_orb_retest_v33.py; pause; }
run_feed_verify() {
  echo "verify_feed_v3.sh must run ON-BOX during RTH with $FEED + $BOT live (paper)."
  confirm "run it now?" || { echo "skipped"; pause; return; }
  bash tests/verify_feed_v3.sh; echo "exit=$?"; pause
}

# ── DEBUG / LOGS (this box) ────────────────────────────────────────────────
svc_status() {
  echo "── this box ─────────────────────────────────────────────────────────"
  echo "  $BOT  : $(svc "$BOT")"
  echo "  $FEED : $(svc "$FEED")"
  systemctl --no-pager -l status "$BOT" "$FEED" 2>/dev/null | grep -E "Active:|Main PID:|Loaded:" | sed 's/^/  /'; pause
}
log_journal_n() { read -rp "  How many journal lines [50]: " N; N="${N:-50}"; journalctl -u "$BOT" -n "$N" --no-pager; pause; }
log_journal()   { echo "following journal for $BOT — Ctrl-C to stop"; journalctl -u "$BOT" -n 100 -f; }
log_botfile() {
  [ -f "$BOTLOG" ] && { echo "tailing $BOTLOG — Ctrl-C to stop"; tail -n 100 -f "$BOTLOG"; } \
                   || { echo "no bot.log at $BOTLOG (is this a bot box?)"; pause; }
}
log_bot_tail() { [ -f "$BOTLOG" ] && tail -n 40 "$BOTLOG" || echo "no bot.log at $BOTLOG"; pause; }
feed_health() {
  local age; age=$(( $(date +%s) - $(stat -c %Y "${FEED_DB}-wal" 2>/dev/null || stat -c %Y "$FEED_DB" 2>/dev/null || echo 0) ))
  echo "  $FEED=$(svc "$FEED")  store_write_age_s=$age  ($FEED_DB)"
  echo; echo "  OPEN INTEREST (the bot's own fetch, today):"
  journalctl -u "$BOT" --since today --no-pager 2>/dev/null | grep "OI:" | tail -3 | sed 's/^/  /' || echo "  (no OI lines today)"
  _sql "$FEED_DB" "SELECT symbol, interval, COUNT(*) AS bars, datetime(MAX(ts_epoch_ms)/1000,'unixepoch','-4 hours') AS last_bar_et FROM candles GROUP BY symbol, interval ORDER BY interval;" 2>/dev/null | head -20; pause
}

# ── SERVICES ───────────────────────────────────────────────────────────────
restart_bot()  { confirm "restart $BOT on THIS box?"  && sudo systemctl restart "$BOT"  && echo "restarted → $(svc "$BOT")"; pause; }
restart_feed() { confirm "restart $FEED on THIS box?" && sudo systemctl restart "$FEED" && echo "restarted → $(svc "$FEED")"; pause; }
stop_bot()     { confirm "STOP $BOT (this box stops trading)?" && sudo systemctl stop "$BOT" && echo "stopped → $(svc "$BOT")"; pause; }
start_bot()    { confirm "start $BOT on THIS box?" && sudo systemctl start "$BOT" && echo "started → $(svc "$BOT")"; pause; }

# ── R SUITE (this box's own trades.db — no S3 here, by construction) ───────
_r_tool() {  # $1 = tests/<tool>.py ; the --db escape hatch is the whole point on a masked box
  local TOOL="$REPO/tests/$1"
  [ -f "$TOOL" ] || { echo "  🔴 $TOOL missing"; pause; return; }
  [ -f "$TRADES_DB" ] || { echo "  no trades.db at $TRADES_DB"; pause; return; }
  echo "    ENTER  = the engine epoch onward · a date = single session or START of a range · all = everything"
  read -rp "  Date (YYYY-MM-DD, ENTER, or 'all'): " d; local d2=""
  if [ -n "$d" ] && [ "$d" != "all" ] && [ "$d" != "ALL" ]; then read -rp "  END of range (ENTER = single day): " d2; fi
  local ARGS=(--db "$TRADES_DB")
  if [ "$d" = "all" ] || [ "$d" = "ALL" ]; then ARGS+=(--all-history)
  elif [ -n "$d" ] && [ -n "$d2" ]; then ARGS+=(--from "$d" --to "$d2")
  elif [ -n "$d" ]; then ARGS+=(--date "$d"); fi
  "$PY" "$TOOL" "${ARGS[@]}"; pause
}
r_ledger()      { echo; echo "  R, expectancy, capture + giveback per strategy/side/exit; selection vs extension."; _r_tool r_ledger.py; }
r_stop_sweep()  { echo; echo "  Bounds, not points: a cell matters only when its PESSIMISTIC net beats the book."; _r_tool stop_sweep.py; }
r_exit_replay() { echo; echo "  Trail fit on real premium paths."; _r_tool exit_replay.py; }
r_edge_scan()   { echo; echo "  Edge scan over the recorded book."; _r_tool edge_scan.py; }
# r130 — the daily open scan: show today's two reports, or run a phase now.
r_open_scan() {
  echo; echo "  Open scan: 09:35 READY (feed, engines, levels, forks) · 09:45 LIVE (plan inputs, fires, warnings)."
  [ -f "$REPO/tools/open_scan.py" ] || { echo "  🔴 tools/open_scan.py missing"; pause; return; }
  read -rp "  ENTER = show today's reports · r = run READY now · l = run LIVE now: " a
  case "$a" in
    r|R) "$PY" "$REPO/tools/open_scan.py" --phase ready ;;
    l|L) "$PY" "$REPO/tools/open_scan.py" --phase live ;;
    *)   "$PY" "$REPO/tools/open_scan.py" --phase ready --show; "$PY" "$REPO/tools/open_scan.py" --phase live --show ;;
  esac
  pause
}
# r129 — reads the DERIVED store (plan_check), so it cannot use _r_tool's --db.
r_stop_spread() {
  echo; echo "  Stop vs spread: refusals, near misses and ratios, flies + verticals."
  [ -f "$REPO/tests/stop_spread_report.py" ] || { echo "  🔴 tests/stop_spread_report.py missing"; pause; return; }
  [ -f "$DERIVED_DB" ] || { echo "  no derived store at $DERIVED_DB"; pause; return; }
  echo "    ENTER  = the last 7 days · a date = single session or START of a range · all = everything"
  read -rp "  Date (YYYY-MM-DD, ENTER, or 'all'): " d; local d2=""
  if [ -n "$d" ] && [ "$d" != "all" ] && [ "$d" != "ALL" ]; then read -rp "  END of range (ENTER = single day): " d2; fi
  local ARGS=(--derived "$DERIVED_DB")
  if [ "$d" = "all" ] || [ "$d" = "ALL" ]; then ARGS+=(--all-history)
  elif [ -n "$d" ] && [ -n "$d2" ]; then ARGS+=(--from "$d" --to "$d2")
  elif [ -n "$d" ]; then ARGS+=(--date "$d"); fi
  "$PY" "$REPO/tests/stop_spread_report.py" "${ARGS[@]}"; pause
}
# r119 — mainline's reports 47/48 (tests/trade_report.py), on this box's
# trades.db. ENTER = the engine epoch onward; a date = from that date; all =
# no floor. Display only (--no-json): nothing is written anywhere.
_trade_report() {  # $@ = extra flags
  local SD
  echo "    ENTER = day one onward · a date = from that date · all = everything"
  read -rp "  Since [ENTER / YYYY-MM-DD / all]: " SD
  case "$SD" in
    "")      "$PY" "$REPO/tests/trade_report.py" --db "$TRADES_DB" --no-json "$@" ;;
    all|ALL) "$PY" "$REPO/tests/trade_report.py" --db "$TRADES_DB" --no-json --all-history "$@" ;;
    *)       "$PY" "$REPO/tests/trade_report.py" --db "$TRADES_DB" --no-json --since "$SD" "$@" ;;
  esac
  pause
}
trade_breakdown() { echo; echo "  Cross-day breakdown: by strategy, symbol, setup, exit, hour, day."; _trade_report; }
trades_taken()    { echo; echo "  One line per trade, ET, with R and capital at risk."; _trade_report --rows-only; }

# ── GIT & LAND (this box) ──────────────────────────────────────────────────
git_pull()  { echo "[pull] git pull --ff-only"; git pull --ff-only; pause; }
git_state() { git -C "$REPO" log -3 --oneline | cut -c1-110; echo; git -C "$REPO" status -s; echo; tail -1 docs/GENESIS.md | cut -c1-120; pause; }
mi_land()   { land_tarball; pause; }
mi_reinstall_timers() { bash "$REPO/deploy/reinstall_timers.sh"; pause; }
mi_bake()   { bake; pause; }

bake() {
  # v3.3 (OTV4TEST r37) — THE BAKE IS BOTH SERVICES, AND IT PURGES THE BYTECODE.
  # Operator's sequence, 2026-09-18: stop both, pull, purge __pycache__, start the
  # FEED first, then the bot, then report both.
  # 🔴 WHAT IT WAS MISSING AND WHY EACH ONE MATTERS:
  #   (1) THE BYTECODE PURGE. The migrated operating notes open with it — "Always
  #       purge the bytecode cache before restarting. This is the single most
  #       common cause of 'I pushed the fix but it's still broken'" — and the one
  #       command whose entire job is making a landed revision LIVE never did it.
  #   (2) THE FEED. It only ever restarted $BOT. r36 put the underlying's Quote
  #       subscription in data/candle_feed.py; a bot-only bake leaves that dead
  #       and the operator reading a green "baked" line that is only half true.
  #   (3) STOP BOTH FIRST, START FEED FIRST. The bot reads what the feed writes,
  #       so bouncing them independently can leave the bot querying a store no
  #       producer is filling. Down together, up in dependency order.
  # ⚠️ check_imports IS KEPT AND STILL BLOCKS, but it now runs while the services
  # are DOWN, so a tree that cannot import leaves the box STOPPED rather than
  # running yesterday's code. That is the honest direction — a bake that silently
  # leaves the old process up is the "LANDED ≠ BAKED" confusion r3 named — but it
  # is a change: a failed bake now needs a fix, not a shrug.
  confirm "BAKE: stop $BOT + $FEED, pull, purge bytecode, start $FEED then $BOT?" || { echo "cancelled"; return; }
  # r67 (BOX.9) — SAY THAT THIS IS A BAKE, before the services are signalled.
  # Without it the bot's STOPPED alert reads "systemctl stop/restart", which is
  # also what a hand stop and the midnight backstop said. Format is
  # `<epoch>|<text>` and utils/shutdown_cause.py is the other writer of it;
  # check_shutdown_cause C5 drives THIS line and parses it with THAT reader,
  # because two writers of one format that are never compared will drift.
  mkdir -p "$REPO/data" && printf '%s|%s\n' "$(date +%s)" "bake — restarting on a new revision" > "$REPO/data/SHUTDOWN_CAUSE" 2>/dev/null
  sudo systemctl stop "$BOT" "$FEED"
  ( cd "$REPO" && git pull --ff-only ) || { echo "  pull FAILED — services are DOWN; fix the pull, then bake again"; return 0; }
  find "$REPO" -name __pycache__ -type d -not -path "*/venv/*" -exec rm -rf {} + 2>/dev/null
  echo "  bytecode purged"
  ( cd "$REPO" && "$PY" tests/check_imports.py ) || { echo "  check_imports FAILED — services left DOWN; the tree does not start"; return 0; }
  sudo systemctl daemon-reload 2>/dev/null
  sudo systemctl start "$FEED" && sleep 5 && sudo systemctl start "$BOT"
  echo "baked → $FEED=$(svc "$FEED")  $BOT=$(svc "$BOT")  $(git -C "$REPO" log -1 --oneline)"
}
land_tarball() {
  # OTV4TEST r1 — the fork lands its own archives, because it is segregated
  # from control and no fleet deploy reaches it. Same lander as day_trader_pro,
  # driven the same way: the archive carries land.sh at its root, so the
  # BOOTSTRAP case (a fresh box with no lander yet) works identically to the
  # steady state and there is no second procedure to remember.
  # ⚠️ THE ARCHIVE'S OWN land.sh IS THE ONE THAT RUNS, never the repo's copy —
  # a delivery that changes the lander must be landed BY the lander it ships,
  # or a lander fix could never be applied.
  local arc n=0 pick
  mapfile -t arcs < <(ls -1t "$HOME"/*.tar.gz 2>/dev/null)
  if [ "${#arcs[@]}" = "0" ]; then
    echo "  no .tar.gz in $HOME — download one first."; return 0
  fi
  echo
  if [ "${#arcs[@]}" = "1" ]; then
    # v4.4 — one archive, no picker; the name is still shown so the operator
    # sees what is about to land.
    arc="${arcs[0]}"
    echo "  one archive in ~: $(basename "$arc")"
  else
    for arc in "${arcs[@]}"; do n=$((n+1)); printf '  %d) %s\n' "$n" "$(basename "$arc")"; done
    read -rp $'\nwhich archive (blank = cancel): ' pick
    [ -n "$pick" ] || return 0
    case "$pick" in (*[!0-9]*|"") echo "  not a number"; return 0 ;; esac
    [ "$pick" -ge 1 ] && [ "$pick" -le "${#arcs[@]}" ] || { echo "  out of range"; return 0; }
    arc="${arcs[$((pick-1))]}"
  fi
  rm -rf /tmp/fork_land && mkdir -p /tmp/fork_land
  tar xf "$arc" -C /tmp/fork_land || { echo "  extract FAILED — check the filename"; return 0; }
  [ -f /tmp/fork_land/land.sh ] || { echo "  archive carries no land.sh at its root — refusing."; return 0; }
  local halves
  halves="$(cd /tmp/fork_land && find . -maxdepth 2 -name land.spec -printf '%h\n' | sed 's|^\./||')"
  [ -n "$halves" ] || { echo "  archive carries no land.spec — refusing."; return 0; }
  echo "  halves: $halves"
  LAND_ARCHIVE="$arc" bash /tmp/fork_land/land.sh $halves
}

# ── CLAUDE CODE (this box) ───────────────────────────────────────────────────
# Claude runs INSIDE TMUX on this box, always: the operator drives from a phone
# and a dropped mobile connection must not kill a working thread (the same rule
# that governs every long-running job here). The session name is fixed so
# REATTACH always knows where to look.
#   HAND OFF  a FRESH thread, bootstrapped with docs/HANDOFF.md so the
#             introduction is not re-typed; kills this menu and every tmux
#   REATTACH  the session that is already running; exits the menu, kills nothing
#   RESUME    `claude --continue` — the last thread on this box
#   RESUME [other]  `claude --resume` — its picker
# ⚠️ THESE ITEMS END THE MENU. Three of them `exec` into Claude, so the menu
# process is REPLACED, not suspended — there is no menu to come back to, which
# is the honest behaviour rather than a shell stacked under a shell.
CLAUDE_TMUX="${CLAUDE_TMUX:-claude}"
CLAUDE_BOOTSTRAP="$REPO/docs/HANDOFF.md"
CLAUDE_NOW="$REPO/docs/HANDOFF_NOW.md"

_claude_bin() {
  command -v claude 2>/dev/null || echo ""
}

_claude_guard() {
  local bin; bin="$(_claude_bin)"
  if [ -z "$bin" ]; then
    echo "  claude is not on PATH on this box."
    echo "  install it, or drive from control and ssh in."
    pause; return 1
  fi
  return 0
}

# 🔴 r70 — /tmp IS tmpfs, WHICH IS RAM. Measured on this box: /tmp is a 455 MB
# tmpfs (half of 908 MB physical), and ONE agent session's scratchpad reached
# 108 MB in a day — three git clones living in memory the bot could not have.
# ⚠️ AND THE SCRATCHPAD PATH IS KEYED BY SESSION ID
# (`/tmp/claude-<uid>/<project>/<session-uuid>/scratchpad`), so EVERY new
# session mints a new directory and NOTHING removes the old ones. This box has
# been protected only by its daily reboot — tmpfs is volatile — while the
# control box, which does not reboot daily, filled its tmpfs completely.
# 🔑 WHAT THAT COSTS IS NOT DISK, IT IS THE SHELL. When tmpfs fills, every Bash
# spawn needs a temp file for its shell snapshot and dies BEFORE executing:
# instant exit 1, no stdout, no stderr, Read/Write unaffected because those
# never spawn. An agent that looks brain-dead rather than out of space, with
# nothing logged anywhere — §0.5's class in the worst possible place.
# ⚠️ TRANSCRIPTS ARE NOT AT RISK AND THAT IS STRUCTURAL, NOT LUCK. They live in
# `~/.claude/projects/...` on EXT4 (measured: /dev/nvme0n1p1, 82 MB over 10
# files), a different filesystem entirely — so this purge cannot reach them and
# `tools/last_session.py` still reads the previous thread afterwards. That is
# what makes it safe to purge aggressively here.
# 🔴 r70 — LAUNCH ON THE SUBSCRIPTION, NEVER ON API CREDITS. Operator's
# instruction, 2026-09-20. Measured that day: no key is set anywhere on this
# box — shell unset, the boot unit carries none, the rc files carry none — and
# `~/.claude.json` authenticates through `oauthAccount`. So today it is already
# right BY ACCIDENT, and one stray `export ANTHROPIC_API_KEY=` in a profile
# would silently move every session onto metered credits with nothing saying
# so. This makes it right BY CONSTRUCTION: the launch strips the variables
# rather than trusting that nobody set them.
# ⚠️ IT UNSETS, IT DOES NOT READ. Nothing here prints or tests a value (§18a).
CLAUDE_ENV="env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN -u CLAUDE_API_KEY -u ANTHROPIC_BASE_URL"

_claude_purge_scratch() {
  local uid root before after
  uid="$(id -u)"; root="/tmp/claude-${uid}"
  # ⚠️ FAIL CLOSED ON THE PATH. A cleanup that globs wrong is worse than none;
  # the shape is pinned and an unexpected value REFUSES rather than deleting.
  case "$root" in
    /tmp/claude-[0-9]*) : ;;
    *) echo "  scratch purge REFUSED — unexpected path '$root'"; return 1 ;;
  esac
  if [ ! -d "$root" ]; then echo "  scratch: nothing to purge"; return 0; fi
  before="$(df -Pm /tmp 2>/dev/null | awk 'NR==2{print $4}')"
  rm -rf "${root:?}"/* 2>/dev/null
  after="$(df -Pm /tmp 2>/dev/null | awk 'NR==2{print $4}')"
  echo "  scratch purged: /tmp free ${before}M -> ${after}M"
}

_claude_kill_all_tmux() {
  # HAND OFF and RESUME start a NEW thread: anything still running belongs to
  # the old one, and a stale tmux is how two threads end up editing one tree.
  if command -v tmux >/dev/null 2>&1; then
    tmux kill-server >/dev/null 2>&1 || true
  fi
}

# r314 — THE BOX'S OWN REMOTE CONTROL NAME, from the one place that resolves it.
# A quote or space in it would break the tmux command, so either refuses.
_claude_rc_name() {
  local n; n="$("$PY" "$REPO/tools/claude_boot.py" --rc-name)" || return 1
  case "$n" in ""|*"'"*|*" "*|*'"'*) return 1 ;; esac
  printf '%s' "$n"
}

_claude_rc_or_refuse() {  # sets RC_NAME_NOW, or says why not
  RC_NAME_NOW="$(_claude_rc_name)" && return 0
  echo "  REFUSED: no Remote Control name (tools/claude_boot.py --rc-name)."
  pause; return 1
}

mi_claude_handoff() {
  _claude_guard || return
  if [ ! -f "$CLAUDE_BOOTSTRAP" ]; then
    echo "  no bootstrap at $CLAUDE_BOOTSTRAP — a fresh thread would start cold."
    confirm "start it anyway?" || { pause; return; }
  fi
  echo "  HAND OFF: a FRESH Claude thread, bootstrapped from docs/HANDOFF.md."
  echo "  This kills this menu and EVERY tmux session on the box."
  confirm "proceed?" || { pause; return; }
  _claude_rc_or_refuse || return
  echo "  session name: $RC_NAME_NOW"
  # ⚠️ ORDER IS THE OPERATOR'S AND THE REASON IS NOT COSMETIC: PURGE FIRST,
  # THEN KILL. If tmpfs is already full, the tmux kill itself may not spawn —
  # every process needs a temp file for its shell snapshot, which is the exact
  # failure being fixed. Freeing space first guarantees room for every step
  # after it. Anything still holding a scratchpad is about to be killed anyway.
  _claude_purge_scratch
  _claude_kill_all_tmux
  cd "$REPO" || exit 1
  # ⚠️ THE PROMPT IS READ BY THE INNER SHELL, NOT THIS ONE. `\$(cat ...)` is
  # escaped so tmux's shell does the substitution: the operator's text contains
  # double quotes ("Vertigo Capital", "plans"), and expanding it HERE would end
  # the argument at the first one and hand Claude a truncated brief.
  # A ONE-TIME NOTE, WHEN ONE EXISTS. `docs/HANDOFF.md` is the standing brief and
  # is passed verbatim; `docs/HANDOFF_NOW.md` is a per-handoff helper (state and
  # open items) that the fresh thread is POINTED AT rather than fed — so the
  # brief never drifts, and the note expires simply by being deleted.
  if [ -f "$CLAUDE_NOW" ]; then
    echo "  one-time note present: docs/HANDOFF_NOW.md (the thread will be pointed at it)"
  fi
  if [ -f "$CLAUDE_BOOTSTRAP" ]; then
    exec tmux new-session -s "$CLAUDE_TMUX" \
      "cd '$REPO' && $CLAUDE_ENV claude --remote-control '$RC_NAME_NOW' \"\$(cat '$CLAUDE_BOOTSTRAP')\$([ -f '$CLAUDE_NOW' ] && printf '%s' '

Also read docs/HANDOFF_NOW.md first — a one-time note for this handoff: where things stand, what to read on Monday, and the open items. Delete it once you have read it.')\"; exec bash"
  else
    exec tmux new-session -s "$CLAUDE_TMUX" "cd '$REPO' && $CLAUDE_ENV claude --remote-control '$RC_NAME_NOW'; exec bash"
  fi
}

mi_claude_reattach() {
  if ! command -v tmux >/dev/null 2>&1; then echo "  tmux is not installed"; pause; return; fi
  if ! tmux has-session -t "$CLAUDE_TMUX" 2>/dev/null; then
    echo "  no running Claude session named '$CLAUDE_TMUX'."
    echo "  HAND OFF starts a fresh one; RESUME continues the last thread."
    pause; return
  fi
  exec tmux attach -t "$CLAUDE_TMUX"
}

mi_claude_resume() {
  _claude_guard || return
  echo "  RESUME: continue the LAST Claude thread on this box."
  echo "  This kills this menu and EVERY tmux session."
  confirm "proceed?" || { pause; return; }
  _claude_rc_or_refuse || return
  echo "  session name: $RC_NAME_NOW"
  _claude_purge_scratch
  _claude_kill_all_tmux
  cd "$REPO" || exit 1
  exec tmux new-session -s "$CLAUDE_TMUX" "$CLAUDE_ENV claude --remote-control '$RC_NAME_NOW' --continue; exec bash"
}

mi_claude_resume_pick() {
  _claude_guard || return
  echo "  RESUME [other]: Claude's own thread picker."
  echo "  This kills this menu and EVERY tmux session."
  confirm "proceed?" || { pause; return; }
  _claude_rc_or_refuse || return
  echo "  session name: $RC_NAME_NOW"
  _claude_purge_scratch
  _claude_kill_all_tmux
  cd "$REPO" || exit 1
  exec tmux new-session -s "$CLAUDE_TMUX" "$CLAUDE_ENV claude --remote-control '$RC_NAME_NOW' --resume; exec bash"
}

mi_claude_restart_boot() {
  # r313 — THE SAME RAISE AS THE 08:00 BOOT, ON DEMAND. A raise typed in an SSH
  # shell has no OT_RC_NAME (only the unit sets it) and falls back to
  # claude_boot.py's default name; the unit carries the box's own name, brief
  # and first-turn check. It does NOT exec: the menu comes back.
  _claude_guard || return
  if [ -n "${TMUX:-}" ] && [ "$(tmux display-message -p '#S' 2>/dev/null)" = "$CLAUDE_TMUX" ]; then
    echo "  REFUSED: this menu is running INSIDE tmux '$CLAUDE_TMUX'."
    echo "  ending that session would end this menu before the restart."
    pause; return
  fi
  echo "  RESTART: a fresh Claude session raised by $CLAUDE_UNIT,"
  echo "  as at boot (its name, its brief, first turn checked)."
  echo "  This ENDS tmux session '$CLAUDE_TMUX'; other tmux sessions stay."
  confirm "proceed?" || { pause; return; }
  # ⚠️ END THE SESSION FIRST. bring_up() returns "already running" over ANY
  # live claude in it, and a session raised from a shell is outside the unit's
  # cgroup, so the unit's stop does not end it: a bare restart raises nothing.
  if command -v tmux >/dev/null 2>&1 && tmux has-session -t "$CLAUDE_TMUX" 2>/dev/null; then
    tmux kill-session -t "$CLAUDE_TMUX"
    echo "  ended tmux session '$CLAUDE_TMUX'"
  else
    echo "  no tmux session '$CLAUDE_TMUX' was running"
  fi
  echo "  restarting $CLAUDE_UNIT (up to 45 s; it waits for the first turn)"
  local rc
  sudo systemctl restart "$CLAUDE_UNIT"; rc=$?
  if [ "$rc" = "0" ]; then
    echo "  $CLAUDE_UNIT -> $(svc "$CLAUDE_UNIT")"
  else
    echo "  🔴 restart FAILED (rc $rc): $CLAUDE_UNIT -> $(svc "$CLAUDE_UNIT")"
  fi
  echo "  claude_boot.log, last 2 lines:"
  tail -n 2 "$REPO/logs/claude_boot.log" 2>&1 | sed 's/^/    /'
  echo "  REATTACH (above) to watch it start."
  pause
}

_claude_boot_state() {
  local s; s="$(systemctl is-enabled "$CLAUDE_UNIT.service" 2>/dev/null)"
  case "$s" in enabled|disabled) echo "$s" ;; *) echo "not installed" ;; esac
}

mi_claude_at_boot() {
  # r13 (BOOT.12) — WHETHER A CLAUDE SESSION IS RAISED AT EVERY BOOT. ON installs
  # and enables the boot unit (the same installer setup_ec2 runs for
  # OT_CLAUDE_AT_BOOT=1); it raises nothing now (RESTART or HAND OFF does).
  # OFF disables the unit and leaves a session running now alone. It does not
  # exec: the menu comes back.
  echo "  Claude at boot: $(_claude_boot_state)"
  echo "    1) ON   raise a Claude session on Remote Control at every boot"
  echo "    2) OFF  stop raising it at boot (a session running now stays up)"
  local a rc
  read -rp "  choose [1/2, blank = no change]: " a
  case "${a:-}" in
    1)
      _claude_guard || return
      bash "$REPO/deploy/install_claude_boot.sh" >/dev/null 2>&1; rc=$?
      [ "$rc" -eq 0 ] && echo "  ON: $CLAUDE_UNIT installed and enabled." \
                      || echo "  ON FAILED (rc $rc): bash deploy/install_claude_boot.sh shows why." ;;
    2)
      if [ "$(_claude_boot_state)" = "not installed" ]; then
        echo "  OFF: no $CLAUDE_UNIT unit on this box; nothing is raised at boot."
      else
        sudo systemctl disable "$CLAUDE_UNIT.service" >/dev/null 2>&1; rc=$?
        [ "$rc" -eq 0 ] && echo "  OFF: $CLAUDE_UNIT disabled; nothing is raised at the next boot." \
                        || echo "  OFF FAILED (rc $rc)."
      fi ;;
    *) echo "  no change." ;;
  esac
  echo "  Claude at boot now: $(_claude_boot_state)"
  pause
}

# ── THE MENU IS DATA — numbers are assigned at render time ─────────────────
MENU=(
  "SECTION|STATUS (this box)"
  "ITEM|status.py            live bot status snapshot|run_status"
  "ITEM|query.py             performance dashboard|run_query"
  "ITEM|DECISIONS NOW        enter on / exit on, live|run_decisions"
  "ITEM|debug_status.py      raw debug dump|run_debug"
  "ITEM|eod_summary.py       end-of-day summary|run_eod"

  "SECTION|SENSORS (this box's derived stores; read-only)"
  "ITEM|Manifold health board|s_manifold"
  "ITEM|Strategy notes       what each engine SAW|s_notes"
  "ITEM|PLAN STATUS NOW       what each plan is doing|s_plan_status"
  "ITEM|PLAN BOARD           every plan, every check|s_plan_board"
  "ITEM|PLAN ROWS            the per-tick narrative|s_plan_rows"
  "ITEM|Plan ledger          intent + terminal reason|s_plan_ledger"
  "ITEM|Exit counterfactual  flow vs the stop|s_exit_cf"
  "ITEM|Fire snapshot        derived vector at entry|s_fire_snapshot"
  "ITEM|Surface              charm / vanna / GEX|s_surface"
  "ITEM|Indicators           ADX / ATR / VWAP series|s_indicators"
  "ITEM|Forks                built vs reject reason|s_forks"
  "ITEM|Levels               touches + retirements|s_levels"
  "ITEM|LEVEL EVENTS         the rejection fact|s_level_events"
  "ITEM|Order flow           aggression + depth|s_order_flow"

  "SECTION|TESTS"
  "ITEM|STANDING CHECKS      what the lander runs|run_standing"
  "ITEM|full pytest suite    the 5 audit-defect tests|run_suite"
  "ITEM|market-data contract standalone|run_contract"
  "ITEM|ORB retest v3.3      standalone|run_orb"
  "ITEM|verify_feed_v3.sh    ON-BOX, live services, RTH|run_feed_verify"

  "SECTION|DEBUG / LOGS (this box)"
  "ITEM|Service status       bot + feed|svc_status"
  "ITEM|Journal tail         last N|log_journal_n"
  "ITEM|Journal follow       Ctrl-C to stop|log_journal"
  "ITEM|Feed health          freshness + last bar|feed_health"
  "ITEM|Bot log tail         last 40|log_bot_tail"
  "ITEM|Bot log follow       Ctrl-C to stop|log_botfile"

  "SECTION|SERVICES (this box)"
  "ITEM|restart optionsbot|restart_bot"
  "ITEM|restart candle-feed|restart_feed"
  "ITEM|stop optionsbot|stop_bot"
  "ITEM|start optionsbot|start_bot"

  "SECTION|R SUITE (this box's trades.db)"
  "ITEM|TRADE BREAKDOWN      by strategy/symbol/exit|trade_breakdown"
  "ITEM|TRADES TAKEN         one line per trade|trades_taken"
  "ITEM|R LEDGER             R, expectancy, capture|r_ledger"
  "ITEM|Stop / TP sweep      R surface over excursions|r_stop_sweep"
  "ITEM|Exit replay          trail fit on real paths|r_exit_replay"
  "ITEM|Edge scan|r_edge_scan"
  "ITEM|STOP VS SPREAD       Saturday: stop vs bid-ask|r_stop_spread"
  "ITEM|OPEN SCAN            today's 09:35 + 09:45 reports|r_open_scan"

  "SECTION|CLAUDE CODE (these items END the menu)"
  "ITEM|HAND OFF -> fresh Claude thread, bootstrapped|mi_claude_handoff"
  "ITEM|REATTACH -> the running Claude session|mi_claude_reattach"
  "ITEM|RESUME   -> the last Claude thread|mi_claude_resume"
  "ITEM|RESUME [other] -> pick a Claude thread|mi_claude_resume_pick"
  "ITEM|RESTART  -> fresh session via boot unit|mi_claude_restart_boot"
  "ITEM|AT BOOT  -> raise Claude at every boot on/off|mi_claude_at_boot"

  "SECTION|GIT & LAND (OTV5; the custodian lands from control)"
  "ITEM|show commit / status / last ledger row|git_state"
  "ITEM|git pull --ff-only|git_pull"
  "ITEM|LAND a tarball from ~|mi_land"
  "ITEM|BAKE   stop both, pull, purge, start feed+bot|mi_bake"
  "ITEM|REINSTALL TIMERS     one-time, after r14|mi_reinstall_timers"
)

# ── COLOUR, AS ON CONTROL ────────────────────────────────────────────────────
# The render prints PLAIN text and a sed pass paints it, so no escape is ever
# embedded in a label (a label with an escape in it breaks the width maths and
# leaks into a pipe). Matched structurally: a full-width rule, the title line,
# and a section header — one leading space, a capital, a trailing colon. Items
# start with two spaces and a digit, so they never match. Colour is suppressed
# when stdout is not a TTY, so piping the menu stays clean.
_BLUE=$'\033[1;34m'
_WHITE=$'\033[1;37m'
_RST=$'\033[0m'
_RULE="======================================================"

_colorize() {
  if [ -t 1 ]; then
    sed -E -e "s/^(=+)$/${_BLUE}\1${_RST}/" \
           -e "s/^(  OTV5 .*)$/${_WHITE}\1${_RST}/" \
           -e "s/^( [A-Z][^:]*:)$/${_BLUE}\1${_RST}/"
  else
    cat
  fi
}

# ⚠️ EVERY LINE FITS 54 COLUMNS. The operator reads this menu on a phone in
# Termius; a label that runs past the rule wraps, and a wrapped menu is the one
# that gets misread at 09:35. Keep labels short enough that "  NN) label" fits.
menu_render() {
  local n=0 e kind rest label
  printf '%s\n' "$_RULE"
  printf '  OTV5 — devtools  v5.0   %s\n' "$(hostname -s)"
  printf '  bot=%-8s feed=%-8s %s\n' "$(svc "$BOT")" "$(svc "$FEED")" \
         "$(git -C "$REPO" log -1 --format='%h %s' 2>/dev/null | cut -c1-22)"
  printf '%s\n' "$_RULE"
  for e in "${MENU[@]}"; do
    kind="${e%%|*}"; rest="${e#*|}"
    if [ "$kind" = "SECTION" ]; then
      printf '\n %s:\n' "$rest"
    else
      n=$((n+1)); label="${rest%%|*}"
      printf '  %2d) %s\n' "$n" "$label"
    fi
  done
  printf '\n   0) Exit\n'
  printf '%s\n' "$_RULE"
}
menu_dispatch() {  # $1 = number -> runs the function at that position
  local n=0 e kind rest fn
  for e in "${MENU[@]}"; do
    kind="${e%%|*}"; rest="${e#*|}"
    [ "$kind" = "ITEM" ] || continue
    n=$((n+1))
    if [ "$n" = "$1" ]; then fn="${rest##*|}"; "$fn"; return 0; fi
  done
  echo "unknown option: $1"
}

menu() {
  clear
  menu_render | _colorize
  read -rp "Select: " choice
  # 0 EXITS THE PROGRAM. `return` would only leave menu(); the caller loops.
  if [ "$choice" = "0" ]; then exit 0; fi
  case "${choice:-}" in
    *[!0-9]*|"") echo "not a number"; pause ;;
    *) menu_dispatch "$choice" || true ;;
  esac
}

while true; do menu; done
