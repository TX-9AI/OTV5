"""
status.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.10  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v4.9 2026-09-27  OTV4TEST r162 (CAP.1) — the halt line names the DAILY CATASTROPHIC LOSS CAP and says entries re-open once the realized loss is back under it (risk_manager v4.8). This reader already recomputed from the day's P&L on every run, so its logic is unchanged.
v4.8 2026-09-26  OTV4TEST r146 — the last-resort fallback is UNSET, not QQQ: the unit's own OT_INSTRUMENT is still read first.
v4.7  2026-09-17  OTV4TEST r34 — MOVED BACK TO THE REPO ROOT. Operator's ruling,
      2026-09-17. r14 sorted the root by FILE TYPE rather than by ROLE: every
      operator reader written in Python went to tools/ and every shell script to
      deploy/, so the three things he actually runs by hand ended up in two
      different folders and one of them (configure.sh) in the deploy drawer. The
      three he drives — status, query, configure — are back at the root where he
      looks for them. No behaviour change.
v4.6  2026-09-11
v4.6  2026-09-11  OTV4TEST r14 — moved from the repo root to tools/ (root cleanup); no behaviour change.
v4.5  2026-09-01  r212 (chunk D) — THE PLAN COLLAPSE GOES WITH ITS PREMISE.
      r199 saw two rows for one strategy at one trigger, called them
      duplicates and merged them for display; r211 kept the merge while the
      writer was unfixed. They were never duplicates — `PlanTick.take()`
      opens a row per FIRE and nothing closed them, so every fired plan
      stayed live all session. QQQ 2026-09-01: SEVEN RunawayContinuation
      TRIGGERED rows at one trigger, all flagged LIVE, while six of those
      trades had closed hours earlier — seven real plans, not one six times.
      ⚠️ SO THE MERGE WAS HIDING DISTINCT PLANS, and (strategy, state,
      trigger) can never tell two runaway fires at one boundary apart. Fixed
      at the WRITER (derived/plan_ledger.py v4.1), so `live_plans()` now
      returns what is actually live and this panel simply prints it.
v4.4  2026-09-01  r211 (chunk C) — THE MIDDLE OF THE BOARD. Operator,
      2026-09-01: open positions "just list the number (nothing else)"; the
      duplicate-plan warning "what do I need this for — get rid of that";
      ORB "on expired, just say that without all the other qualifiers"; and
      "add a line for Character... put 'inactive' until it is" activated.
      ⚠️ THE COUNT REPLACES THE CARDS, AND THE DETAIL IS NOT LOST. Menu 15
      runs status.py and query.py in the SAME fan-out, and query.py still
      renders every position with its own card and the summed at-risk line
      (r199). What goes is the DUPLICATE of that figure, not the figure.
      🔴 THE CHARACTER LINE WAS ALREADY HERE AND HAS NEVER PRINTED. r75 gated
      it on `current()` returning a state; r85 then set BANDS_SET=False,
      because the old bands were calibrated against a per-bar volatility
      RATIO that is silent about direction — a trend scored 1.00 and
      ALTERNATING CHOP scored 1.00 too. So the engine emits nothing and the
      line was invisible on every box. ABSENT AND INACTIVE ARE DIFFERENT
      FACTS, and an unreadable engine is a THIRD one: it now prints
      inactive / unavailable / the state, and sits below the pin line.
      🔴 AND THE EXPIRED LABEL WAS STALE IN TWO PLACES. Both the live branch
      and `ORB_STATE_LABELS` read "past 11:00 ET cutoff"; r193 moved
      ORB_NO_ENTRY_AFTER_ET to 11:30 on 2026-08-30 and neither was updated.
      Two spellings of one constant is how the first rots unnoticed (§35) —
      and a line nobody reads is a line nobody notices going stale, which is
      the argument for deleting it rather than correcting it.
      ⚠️ THE PLAN COLLAPSE STAYS. r199 printed the collapsed COUNT so the
      ledger duplication remained visible and RPT.5 records the write side
      was never examined; chunk D repairs the writer, after which the
      collapse has nothing to do. Removing the collapse WITH the warning
      would render two identical plans as two rows — the defect inverted.
v4.3  2026-08-31  r199 — EVERY OPEN POSITION, NOT JUST THE NEWEST. The
      query asked for LIMIT 1 and the panel rendered it as the whole book,
      so a box holding a butterfly AND a directional trade under-reported
      both the positions and the capital at risk. Latent since r161 made
      the butterfly additive; r197 makes it the norm. Plan rows are also
      deduped FOR DISPLAY, with the collapsed count shown, because the
      duplication in the ledger is real and hiding it would be worse.
v4.2  2026-08-24  r111: the PRE-OPEN REHEARSAL state is on the status board, RED
      with a flag emoji while it is running. The box reads its OWN flag off its
      OWN disk — three revisions were spent on a control-side marker standing in
      for this fact, and it disagreed with the boxes the first time it mattered.
      ANSI is emitted unconditionally: this output is read THROUGH `fleet.py
      run`, so stdout is a pipe, and an isatty gate would strip the colour in
      exactly the place the operator reads it.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Box status summary.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

status.py — Live bot status snapshot. v1.13
daily-loss banner (relabeled in the 2026-07-23 header
        audit — this entry duplicated the existing v1.12 of 2026-07-06)
        reads the limit from the LIVE unit env
        (get_runtime_env, same as Risk) instead of `from config import
        DAILY_LOSS_LIMIT_USD`, which resolved in the status process's own env
        where OT_RISK_USD is absent — so it fell back to $200 and printed a
        FALSE "DAILY LOSS LIMIT HIT / new entries halted" banner while the bot
        (systemd env) was correctly enforcing the risk-coupled limit. Same
        class of bug as v1.1's original fix; this closes the last config
        import that was env-sensitive.
v3.0 — original release
read INSTRUMENT and PAPER_TRADING from systemd env
        so status.py reflects live config, not config.py defaults
fix systemd env parsing with regex to handle long token values
remove lookahead from regex, Environment= prefix was blocking match
fix ORB state display: read structured ORB data (high/low/width/
        state/attempt) from bot.log instead of fragile string matching against
        state names that no longer exist (CONFIRMED_LONG -> OPEN_LONG, etc).
        Always show ORB H/L/width once range is set, regardless of state.
        found regardless of log line order.
        of log parsing — reliable across restarts and outside RTH.
consume the orb_range.json "status" field (ESTABLISHED/
        IN_PROGRESS/EXPIRED) instead of inventing ORB state from the clock.
        Only an ESTABLISHED range dated today is shown as live; EXPIRED and
        IN_PROGRESS ranges are labeled as such with their date, so a carried
        prior-session range can never be shown as "watching for break".
        reassessment (session continues), not a halt.
banner reflects the NET daily loss halt (day P&L <= -limit).
read authoritative orb_state.json (live engine state:
        disarm reason, break latches, price, 11:00 cutoff) instead of clock
        inference/log-scraping. Adds a live Price line, shows DISARMED (runaway
        past 50% TP) and EXPIRED truthfully, and reports price vs
        range instead of always saying "inside range, waiting".
show live Risk per trade ($ from OT_RISK_USD) under Mode.
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
Run: python status.py
open position (with current premium & P&L), and session summary.
Read-only — never modifies anything.
"""

import os
import re
import sys
import sqlite3
import subprocess
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ET  = ZoneInfo("America/New_York")
UTC = timezone.utc

INSTALL_DIR  = os.path.expanduser("~/options-trader")
SERVICE_NAME = "optionsbot"
sys.path.insert(0, INSTALL_DIR)


def get_runtime_env(key: str, default: str = "") -> str:
    """Read a live environment variable from the systemd service."""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "show", SERVICE_NAME, "--property=Environment"],
            capture_output=True, text=True
        )
        match = re.search(rf'{re.escape(key)}=([^ ]+)', result.stdout)
        if match:
            return match.group(1)
    except Exception:
        pass
    return os.environ.get(key, default)


try:
    from config import DB_PATH, BOT_NAME
except Exception:
    DB_PATH            = os.path.join(INSTALL_DIR, "trades.db")
    BOT_NAME           = "OptionsTrader"

INSTRUMENT    = get_runtime_env("OT_INSTRUMENT", "UNSET")  # r146: never QQQ by default
PAPER_TRADING = get_runtime_env("OT_PAPER_TRADING", "True") != "False"
RISK_PER_TRADE = get_runtime_env("OT_RISK_USD", "200")

# Daily loss limit, resolved the same way config.py resolves it — but against
# the LIVE unit environment (like RISK_PER_TRADE above), NOT this SSH process's
# os.environ. v1.13 fix (2026-07-20): `from config import DAILY_LOSS_LIMIT_USD` resolved in
# the status process, where OT_RISK_USD is absent, so it silently fell back to
# $200 and printed a false "DAILY LOSS LIMIT HIT" banner while the bot itself
# (systemd env) was correctly enforcing the risk-coupled limit. Fallback chain
# mirrors config.py:184: explicit OT_DAILY_LOSS_LIMIT, else one trade's risk.
DAILY_LOSS_LIMIT = float(get_runtime_env("OT_DAILY_LOSS_LIMIT",
                                         RISK_PER_TRADE or "200"))


def now_et():
    return datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S ET")

def to_et(ts):
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(ET).strftime("%Y-%m-%d %H:%M ET")
    except Exception:
        return ts[:16]

def sep(char="─", w=54):
    print(char * w)

def pct(val):
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1%}"

def usd(val):
    if val >= 0:
        return f"+${val:,.2f}"
    else:
        return f"-${abs(val):,.2f}"


def check_service():
    try:
        r = subprocess.run(
            ["systemctl", "is-active", SERVICE_NAME],
            capture_output=True, text=True
        )
        active = r.stdout.strip() == "active"
        return active, r.stdout.strip()
    except Exception:
        return False, "unknown"


ORB_STATE_LABELS = {
    "NO_RANGE":                    "Waiting for 9:35 ET range",
    "WAITING_FOR_BREAK":           "Inside range, watching for break",
    "ARMED_LONG":                  "ARMED LONG — broke HIGH, awaiting retest",
    "ARMED_SHORT":                 "ARMED SHORT — broke LOW, awaiting retest",
    "INVALIDATED":                 "Invalidated, re-arming",
    "OPEN_LONG":                   "OPEN LONG (confirmed)",
    "OPEN_SHORT":                  "OPEN SHORT (confirmed)",
    # 🔴 r211 — A SECOND SPELLING OF THE SAME FACT, AND IT WAS STALE TOO.
    # The live branch in main() carried "past 11:00 ET cutoff" and so did this
    # fallback; r193 moved ORB_NO_ENTRY_AFTER_ET to 11:30 on 2026-08-30 and
    # neither was updated. Two places holding one constant is exactly how the
    # first one rots unnoticed (§35). Now it states the state and nothing else,
    # which is also the operator's ruling: "it's just expired."
    "EXPIRED":                     "EXPIRED",
    "IN_PROGRESS":                 "Opening range forming (9:30-9:35 ET)",
    "EXPIRED_RANGE":               "Last session's range - today NOT established",
    "NOT_ESTABLISHED":             "Today's range not established",
    "UNKNOWN":                     "Unknown",
}


def get_strategy_and_orb():
    log_path = os.path.join(INSTALL_DIR, "bot.log")
    strategy  = "UNKNOWN"
    gex_pin   = None
    gex_env   = None

    # ── ORB state: prefer orb_state.json (authoritative LIVE engine state) ────
    # Written every tick by run_analysis(); carries the true state incl. disarm
    # reason, break latches, live price and the 11:00 cutoff — no clock guessing,
    # no log parsing. Falls back to orb_range.json (+11:00 clock) only if the
    # state file isn't present yet.
    orb = {
        "high": None, "low": None, "width": None, "state": "UNKNOWN",
        "attempt": 0, "reason": "", "broke_high": False, "broke_low": False,
        "price": None, "past_cutoff": False,
    }
    import json
    orb_state_file = os.path.join(INSTALL_DIR, "orb_state.json")
    orb_range_file = os.path.join(INSTALL_DIR, "orb_range.json")

    _have_state = False
    if os.path.exists(orb_state_file):
        try:
            with open(orb_state_file) as f:
                sd = json.load(f)
            orb.update({
                "high": sd.get("high"), "low": sd.get("low"), "width": sd.get("width"),
                "state": sd.get("state", "UNKNOWN"), "attempt": sd.get("attempt", 0),
                "reason": sd.get("reason", "") or "", "broke_high": sd.get("broke_high", False),
                "broke_low": sd.get("broke_low", False), "price": sd.get("price"),
                "past_cutoff": sd.get("past_cutoff", False),
            })
            _have_state = True
        except Exception:
            pass

    if os.path.exists(orb_range_file):
        try:
            with open(orb_range_file) as f:
                rd = json.load(f)
            orb["range_status"] = str(rd.get("status", "")).upper()
            orb["range_date"]   = rd.get("date")
            if orb["high"]  is None: orb["high"]  = rd.get("high")
            if orb["low"]   is None: orb["low"]   = rd.get("low")
            if orb["width"] is None: orb["width"] = rd.get("width")

            if not _have_state:
                # Fallback only — infer from the clock using the REAL 11:00 cutoff
                today = datetime.now(ET).strftime("%Y-%m-%d")
                if orb["range_status"] == "ESTABLISHED" and orb["range_date"] == today:
                    now = datetime.now(ET); hm = (now.hour, now.minute)
                    if not (9 <= now.hour < 16) or hm >= (11, 0):
                        orb["state"] = "EXPIRED"; orb["past_cutoff"] = hm >= (11, 0)
                    elif hm >= (9, 35):
                        orb["state"] = "WAITING_FOR_BREAK"
                    else:
                        orb["state"] = "NO_RANGE"
                elif orb["range_status"] == "IN_PROGRESS":
                    orb["state"] = "IN_PROGRESS"
                elif orb["range_status"] == "EXPIRED":
                    orb["state"] = "EXPIRED_RANGE"
                else:
                    orb["state"] = "NOT_ESTABLISHED"
        except Exception:
            pass

    if not os.path.exists(log_path):
        return strategy, orb, gex_pin, gex_env

    try:
        result = subprocess.run(
            ["tail", "-1000", log_path],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split("\n")

        for line in reversed(lines):

            if "STRATEGY TRANSITION:" in line and strategy == "UNKNOWN":
                parts = line.split("\u2192")
                if len(parts) > 1:
                    strategy = parts[1].strip().split()[0].rstrip(")")

            if "STRATEGY: NO TRADE" in line and strategy == "UNKNOWN":
                strategy = "No Trade"

            # ORB state is taken from orb_state.json (authoritative) above — no
            # log-scan refinement needed.

            if "GEX computed:" in line and gex_pin is None:
                try:
                    if "pin=$" in line:
                        gex_pin = line.split("pin=$")[1].split()[0].rstrip(")")
                    if "env=" in line:
                        gex_env = line.split("env=")[1].split()[0]
                except Exception:
                    pass

            # even when it appears near the bottom of the log

    except Exception:
        pass

    return strategy, orb, gex_pin, gex_env


def get_open_trades():
    """EVERY open position on this box, oldest first.

    🔴 r199 — THIS ASKED FOR `LIMIT 1` AND RENDERED IT AS THE WHOLE BOOK.
    Latent since r161 made the butterfly additive: before that, one position
    per box was true and the limit was correct. Nothing swept the readers when
    the rule changed, so a box holding a butterfly AND a directional trade
    showed only the most recent — and `at risk` understated the box's real
    exposure on the one line you would check it on. Measured 2026-08-31 on CRM,
    which held a runaway and a butterfly and reported one.

    ⚠️ r197 makes multi-position boxes the norm rather than the exception, so
    this stops being latent tomorrow.

    Oldest first, deliberately: DESC put the newest on top and hid the one that
    had been running longest, which is usually the one worth seeing.
    """
    if not os.path.exists(DB_PATH):
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM trades WHERE status='open' ORDER BY entry_time ASC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_session_summary():
    if not os.path.exists(DB_PATH):
        return None
    today = datetime.now(ET).strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl_usd < 0 THEN 1 ELSE 0 END) as losses,
                COALESCE(SUM(pnl_usd), 0)                     as net_pnl,
                COALESCE(MAX(pnl_usd), 0)                     as best,
                COALESCE(MIN(pnl_usd), 0)                     as worst
            FROM trades
            WHERE status='closed' AND date(entry_time) = ?
        """, (today,)).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


_RED = "\033[1;31m"
_RST = "\033[0m"


def _rehearsal_line() -> str:
    """r111 — the pre-open rehearsal's state, read from THIS box's own flag.

    ON  (flag absent)  -> RED, with a flag emoji. The trading path runs outside
                          RTH against live inputs. It cannot place — entries_open()
                          requires is_rth() AND is_orb_complete(), in paper and
                          in live alike — but it is a mode that is running, and
                          a running mode should be visible.
    OFF (flag present) -> plain. The trading path is dormant until 09:30.

    ⚠️ FAILS TOWARD SAYING "ON". An unreadable path reports the rehearsal as
    running, because the flag's ABSENCE is what enables it: if we cannot read
    the disk we cannot claim the thing is disabled, and the honest default is
    the louder one.
    """
    try:
        _off = os.path.exists(os.path.join(INSTALL_DIR, "data", "REHEARSAL_OFF"))
    except Exception:                                          # noqa: BLE001
        _off = False
    if _off:
        return "\U0001F4A4 Rehearsal:    OFF (trading path dormant until 09:30)"
    return (f"{_RED}\U0001F6A9 Rehearsal:    ON - the trading path runs outside "
            f"RTH (places nothing){_RST}")


def _log_level_line() -> str:
    """r112 — the EFFECTIVE log level, in caps, red while it is DEBUG.

    ⚠️ THE FLAG WINS, AND THAT IS WHAT MAKES THIS TRUTHFUL. main.py applies
    `data/DEBUG_LOG` over config.LOG_LEVEL on every tick, so reading the config
    constant alone would report INFO on a box that is writing DEBUG. The flag is
    checked first, exactly as the bot checks it.
    ⚠️ RED BECAUSE IT IS A COST, NOT A FAULT. DEBUG buries the decision lines a
    postmortem needs under raw feed payloads — 2026-08-24 ran ~300k lines a box.
    It is a mode you choose and should be reminded you are still in.
    """
    try:
        if os.path.exists(os.path.join(INSTALL_DIR, "data", "DEBUG_LOG")):
            return (f"{_RED}\U0001F41E Log level:    DEBUG - verbose, and it "
                    f"buries the decision lines{_RST}")
    except Exception:                                          # noqa: BLE001
        pass
    try:
        from config import LOG_LEVEL as _LL
    except Exception:                                          # noqa: BLE001
        _LL = "INFO"
    return f"\U0001F41E Log level:    {str(_LL).upper()}"


def main():
    print()
    sep("\u2550")
    mode_label = "PAPER" if PAPER_TRADING else "LIVE"
    print(f"  {BOT_NAME} \u2014 STATUS")
    print(f"  {now_et()}")
    sep("\u2550")
    print()

    running, svc_status = check_service()
    svc_icon = "\U0001F7E2" if running else "\U0001F534"
    print(f"  {svc_icon} Service:      {svc_status.upper()}")
    print(f"  \U0001F4CD Instrument:  {INSTRUMENT}")
    mode_icon = "\U0001F4C4" if PAPER_TRADING else "\U0001F534"
    print(f"  {mode_icon} Mode:         {mode_label}")
    try:
        _risk_disp = f"{float(RISK_PER_TRADE):.0f}"
    except Exception:
        _risk_disp = RISK_PER_TRADE
    print(f"  \U0001F4B5 Risk:         ${_risk_disp}")
    # ── 🔴 r111 — THE REHEARSAL SAYS SO HERE, IN RED ─────────────────────────
    # Operator, 2026-08-24: "the same problem I originally pointed out was that
    # I'm going to forget about it in 3 weeks." A devtools row cannot solve that
    # — you have to remember to go look, which is the same problem. status.py
    # is read constantly and per box, so the state is re-asserted in front of
    # the operator as a side effect of ordinary work rather than as an errand.
    # ⚠️ THE BOX IS THE ONLY HONEST REPORTER. It reads its OWN flag off its OWN
    # disk. Three revisions were spent on a control-side marker that stood in
    # for this fact and disagreed with it the first time it mattered.
    # ⚠️ ANSI IS EMITTED UNCONDITIONALLY — NO isatty GATE, DELIBERATELY. This
    # output is normally read THROUGH `fleet.py run`, which captures stdout, so
    # stdout is a PIPE and not a terminal. A conventional `if sys.stdout.isatty()`
    # would strip the colour in exactly the place the operator reads it and
    # leave it only when running on the box by hand — precisely backwards.
    print(f"  {_rehearsal_line()}")
    print(f"  {_log_level_line()}")
    # ── 🔴 r68 — MANIFOLD ROLLUP. One bulb; the board is tools/manifold_health.py
    # ⚠️ THIS IS THE LINE THAT WOULD HAVE CAUGHT 2026-08-21. The intraday tape
    # was dead from 09:30, the blind latch paged ONCE so the silence afterwards
    # meant nothing, and the fleet traded zero. A bulb here is checkable in one
    # glance before the open.
    # ⚠️ NEVER FATAL TO THE DISPLAY. status.py must render even if the health
    # tool cannot — a broken instrument must not hide the instrument panel.
    try:
        import subprocess as _sp
        _r = _sp.run([sys.executable,
                      os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "tools", "manifold_health.py"), "--bulb"],
                     capture_output=True, text=True, timeout=10)
        _line = (_r.stdout or "").strip()
        if _line:
            print(f"  {_line}")
    except Exception:                                          # noqa: BLE001
        print("  \u26aa Manifold:    unavailable")
    print()
    sep()

    # ── r68 — WHAT THE BOX IS DOING RIGHT NOW ────────────────────────────
    # ⚠️ THE OLD "Strategy: UNKNOWN" LINE IS DELETED. It printed a label from
    # the retired system on every box on every call — an artifact reporting a
    # world that no longer exists. Operator: the only honest thing to show
    # here is an ACTIVE PLAN waiting on conditions; otherwise the line should
    # not exist at all.
    strategy, orb, gex_pin, gex_env = get_strategy_and_orb()
    # ── r69 — ACTIVE PLANS COME FROM THE LEDGER, NOT FROM PROCESS STATE ──
    # ⚠️ `orb_state.json` is written by a RUNNING bot, so after a restart it
    # shows whatever the NEW process has rebuilt — a condor sitting at
    # LEG1_FILLED with a live leg at the broker would display as NOTHING AT
    # ALL, and the box would look idle while holding half a structure. The
    # ledger is on disk, independent of who is running.
    try:
        from derived.registry import plan_ledger as _pl
        _led = _pl(INSTRUMENT)
        _live = _led.live_plans() if _led else []
    except Exception:                                          # noqa: BLE001
        _live = []
    if _live:
        # 🔴 r212 — THE COLLAPSE IS GONE, BECAUSE ITS PREMISE WAS WRONG.
        # r199 saw two rows for one strategy at one trigger, called them
        # duplicates and merged them for display. They were not duplicates:
        # `PlanTick.take()` opens a ledger row per FIRE and NOTHING closed
        # them, so every fired plan stayed live for the session. QQQ on
        # 2026-09-01 showed SEVEN RunawayContinuation TRIGGERED rows at one
        # trigger price, all flagged LIVE, while six of those trades had
        # closed hours earlier — seven real plans, not one plan six times.
        # ⚠️ SO COLLAPSING THEM WAS HIDING DISTINCT PLANS. Two runaway fires
        # at the same boundary are two trades with two outcomes, and the key
        # (strategy, state, trigger) cannot tell them apart. The defect is
        # fixed at the WRITER — r212 closes a plan when its trade closes, and
        # supersedes one that never filled — so `live_plans()` now returns
        # what is actually live and there is nothing to merge.
        for _p in _live:
            _what = _p.get("short_strike") or _p.get("trigger_price")
            _at = f" @ {_what:.2f}" if _what else ""
            print(f"  \U0001F3AF Active plan: {_p['strategy']} "
                  f"[{_p['state']}]{_at}")
    elif strategy and str(strategy).upper() not in ("", "UNKNOWN", "NONE"):
        print(f"  \U0001F3AF Active plan: {strategy}")

    # Live underlying price (from orb_state.json, written each tick)
    _price = orb.get("price")
    if _price:
        print(f"  \U0001F4B2 Price:       {_price:.2f}")

    if orb["high"] is not None and orb["low"] is not None:
        print(f"  \u23F1  ORB High:    {orb['high']:.2f}")
        print(f"      ORB Low:     {orb['low']:.2f}")
        print(f"      ORB Width:   {orb['width']:.2f}")

        # Truthful state label straight from the engine (orb_state.json).
        st = orb["state"]
        reason = orb.get("reason", "")
        # 🔴 r211 (chunk C) — EXPIRED JUST SAYS EXPIRED. Operator: "on expired,
        # just say that without all the other qualifiers. It's unimportant.
        # It's just expired."
        # ⚠️ AND THE QUALIFIER WAS WRONG BESIDES. It read "past 11:00 ET
        # cutoff" — r193 moved ORB_NO_ENTRY_AFTER_ET to 11:30 on 2026-08-30
        # and this label kept the old number, so the panel has been printing a
        # stale constant for two days. A line nobody reads is a line nobody
        # notices going stale, which is the argument for deleting it rather
        # than correcting it.
        if st == "EXPIRED" or orb.get("past_cutoff"):
            state_label = "EXPIRED"
        elif st == "INVALIDATED" and reason == "runaway":
            state_label = "\U0001F6D1 DISARMED — ran past 50% TP, no retest (favors sweep)"
        elif st == "INVALIDATED" and reason == "close_inside":
            state_label = "Invalidated (closed back inside) — re-arming"
        elif st == "INVALIDATED" and reason == "timeout":
            state_label = "Invalidated (retest timeout) — dormant"
        elif st in ("OPEN_LONG", "OPEN_SHORT"):
            state_label = ORB_STATE_LABELS.get(st, st)
        elif st in ("ARMED_LONG", "ARMED_SHORT"):
            state_label = ORB_STATE_LABELS.get(st, st)
        elif st == "WAITING_FOR_BREAK":
            # show where price sits vs the range so "inside/broke out" is honest
            if _price is not None and _price > orb["high"]:
                state_label = "Broke ABOVE range — awaiting retest/close"
            elif _price is not None and _price < orb["low"]:
                state_label = "Broke BELOW range — awaiting retest/close"
            else:
                state_label = "Inside range, awaiting break"
        else:
            state_label = ORB_STATE_LABELS.get(st, st)

        # break latches (which side has registered a 1m close-out)
        bh, bl = orb.get("broke_high"), orb.get("broke_low")
        brk = []
        if bh: brk.append("H")
        if bl: brk.append("L")
        brk_note = f"  [broke: {'/'.join(brk)}]" if brk else ""

        attempt_str = f"  (attempt #{orb['attempt']})" if orb["attempt"] > 0 else ""
        if orb.get("range_status"):
            rs = orb["range_status"]
            date_note = f"  [{orb.get('range_date')}]" if rs != "ESTABLISHED" else ""
            print(f"      Range:       {rs}{date_note}")
        # ⚠️ r211 — THE QUALIFIERS ARE SUPPRESSED ON EXPIRED ONLY. Attempt
        # count and break latches are exactly what you want while the engine is
        # live; on a finished session they are trivia after a terminal word.
        _expired = (st == "EXPIRED" or orb.get("past_cutoff"))
        _quals = "" if _expired else f"{attempt_str}{brk_note}"
        print(f"      State:       {state_label}{_quals}")
    else:
        print(f"  \u23F1  ORB:         Waiting for 9:35 ET range to be set")

    if gex_pin:
        # ── r77 — SAY WHAT THE GAMMA DOES TO A MOVE, NOT A STATE WORD ───────
        # ⚠️ THIS LINE USED TO PRINT "TRENDING" NEXT TO THE CHARACTER LINE, AND
        # THEY MEAN COMPLETELY DIFFERENT THINGS. Character is what PRICE is
        # doing; this is what dealer gamma will do TO price. Character can read
        # RANGING while this reads TRENDING and both are correct — but as two
        # bare state words stacked in one panel they look like a contradiction.
        # ⚠️ PINNING KEEPS ITS OWN NAME because it IS the thing itself: gamma
        # pulling price to the strike. The other two are renamed to their
        # EFFECT, which is also the vocabulary `orb_bias` already uses, so this
        # is the repo's own language rather than a new one.
        _gex_label = {"PINNING": "PINNING",
                      "TRENDING": "AMPLIFYING",
                      "NEUTRAL": "DAMPENING"}.get(gex_env, gex_env)
        gex_icon = ("\U0001F4CC" if gex_env == "PINNING"
                    else "\U0001F4C8" if gex_env == "TRENDING" else "\u2796")
        print(f"  {gex_icon} GEX pin:     ${gex_pin}  ({_gex_label})")

    # ── r75 / r211 (chunk C) — CHARACTER, BELOW THE PIN LINE, ALWAYS ────────
    # Operator, 2026-09-01: "Add a line for Character. I know it's not
    # activated yet, so put 'inactive' until it is."
    # ⚠️ IT WAS ALREADY HERE AND HAS NEVER PRINTED. The r75 block sat ABOVE the
    # active plan and rendered only when `current()` returned a character —
    # and r85 set BANDS_SET=False, because the old bands were calibrated
    # against a quantity that turned out to be the wrong one (a per-bar
    # volatility RATIO, silent about direction: a trend scored 1.00 and
    # ALTERNATING CHOP also scored 1.00). So the engine emits no state at all
    # and the line has been invisible on every box since.
    # 🔑 ABSENT AND INACTIVE ARE DIFFERENT FACTS, and printing nothing said
    # neither. "inactive" says the engine is running and deliberately not
    # emitting; a missing line says nothing and reads as an oversight.
    # ⚠️ A DESCRIPTION, NOT A SIGNAL — it gates nothing and carries no score.
    # A character that has held all session is a different session from one
    # that has flipped six times, which is why the duration rides the line.
    _char = "inactive"
    try:
        from derived.registry import build_engines as _be
        _ce = None
        for _e in (_be(INSTRUMENT) or []):
            if getattr(_e, "name", "") == "character":
                _ce = _e
                break
        _cur = _ce.current() if _ce else {}
        if _cur.get("character"):
            _mins = (_cur.get("held_s") or 0) / 60.0
            _char = f"{_cur['character'].upper()}  (held {_mins:.0f} min)"
    except Exception:                                          # noqa: BLE001
        # ⚠️ AN UNREADABLE ENGINE IS NOT AN INACTIVE ONE. Say which it is.
        _char = "unavailable"
    print(f"  \U0001F30A Character:   {_char}")

    # ── r78 — FORK TILT. Relative, never literal, and None is not FLAT. ─────
    # ⚠️ "FLAT" MEANS FLAT-ISH: a band around zero, because a channel tilting a
    # tenth of an ATR per bar has no meaningful heading and calling it BULLISH
    # would manufacture one out of noise.
    # ⚠️ NORMALISED BY THE SYMBOL'S OWN ATR. A raw slope is not comparable
    # across the fleet — +0.20/bar is FLAT on a $700 QQQ and BULLISH on a $180
    # PLTR, and a single raw threshold would get one of them wrong every time.
    # 🔴 NO FORK PRINTS "None" WITH ITS REASON, NEVER "FLAT". Those are
    # different states and conflating them is the silent-zero habit this repo
    # has paid for repeatedly.
    try:
        from derived.registry import build_engines as _be2
        from config import CONDOR_PF_TIMEFRAME as _PFTF
        from analysis.pitchfork import SLOPE_FLAT_ATR as _FLAT
        _st2 = None
        for _e2 in (_be2(INSTRUMENT) or []):
            _st2 = getattr(_e2, "_store", None) or _st2
        if _st2 is not None:
            _row = _st2.conn.execute(
                "SELECT built, reject_reason, slope FROM fork_series"
                " WHERE symbol=? AND interval=? ORDER BY ts_epoch DESC LIMIT 1",
                (INSTRUMENT, _PFTF)).fetchone()
            if _row and _row[0] and _row[2] is not None and orb.get("atr"):
                _rt = float(_row[2]) / float(orb["atr"])
                _lab = ("BULLISH" if _rt > _FLAT else
                        "BEARISH" if _rt < -_FLAT else "FLAT")
                print(f"  \U0001F4D0 Fork ({_PFTF}):  {_lab}"
                      f"   ({_rt:+.2f} ATR/bar)")
            elif _row and not _row[0]:
                _why = f"  ({_row[1]})" if _row[1] else ""
                print(f"  \U0001F4D0 Fork ({_PFTF}):  None{_why}")
    except Exception:                                          # noqa: BLE001
        pass
    print()
    sep()

    # 🔴 r211 (chunk C) — THE COUNT, AND NOTHING ELSE. Operator, 2026-09-01:
    # "Open positions — keep, but just list the number of open positions
    # (nothing else)."
    # ⚠️ THIS UNDOES HALF OF r199 DELIBERATELY, AND THE DETAIL IS NOT LOST.
    # r199 added the per-position cards AND the summed exposure here because
    # ONE card was being rendered as the whole book — "the number you check
    # before adding risk". Menu item 15 runs `status.py` and then `query.py` in
    # the same fan-out, and query.py still renders every position with its own
    # card and the summed at-risk line (r199, kept through chunks A and B). So
    # the exposure figure is one screen down, not gone; what goes is the
    # DUPLICATE of it, which is why this is safe and why it would not be if
    # status were read alone.
    _open = get_open_trades()
    print(f"  \U0001F4E6 Open positions: {len(_open)}")

    print()
    sep()

    s = get_session_summary()
    today_label = datetime.now(ET).strftime("%Y-%m-%d")
    print(f"  TODAY'S SESSION  ({today_label} ET)")
    print()
    if s and s["total"] > 0:
        wins   = s["wins"]   or 0
        losses = s["losses"] or 0
        total  = s["total"]  or 0
        pnl    = s["net_pnl"] or 0
        best   = s["best"]   or 0
        worst  = s["worst"]  or 0
        wr     = wins / total * 100 if total else 0
        cb_warning = ""
        # v1.13: use DAILY_LOSS_LIMIT (live unit env, top of file) — NOT
        # `from config import DAILY_LOSS_LIMIT_USD`, which resolved against this
        # process's env and falsely reported $200 / a phantom halt.
        if pnl <= -DAILY_LOSS_LIMIT:
            cb_warning = (f"  \U0001F6D1  CATASTROPHIC LOSS CAP HIT "
                          f"(${pnl:+.0f} <= -${DAILY_LOSS_LIMIT:.0f})\n"
                          f"      no new entries until the loss is back under")
        print(f"  Trades:       {total}  ({wins}W / {losses}L)")
        print(f"  Win rate:     {wr:.0f}%")
        print(f"  Net P&L:      {usd(pnl)}")
        print(f"  Best trade:   {usd(best)}")
        print(f"  Worst trade:  {usd(worst)}")
        if cb_warning:
            print()
            print(f"  {cb_warning}")
    else:
        print("  No closed trades yet today.")

    print()
    sep("\u2550")
    print()


if __name__ == "__main__":
    main()
