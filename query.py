"""
query.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.20  2026-10-19  OTV4TEST r303 (PSTATE.1) - THE PLANS PANEL KNOWS A DORMANT PLAN FROM A BROKEN ONE. A dormant plan
      writes no heartbeat (the operator, 2026-10-19: "dormant plans should not write to the ledger"), so the panel
      read its last row as STALE and an absent one as NOT RUNNING. It now reads data/plan_states.json (written by the
      bot at start) and lists DORMANT and LOG ONLY plans by name; an absent file is said, not assumed. A /manage plan
      or CondorManagement / CreditRoll whose heartbeat is old reads IDLE (nothing to manage) unless trades.db holds an
      open position it manages - it writes no heartbeat while its condition is absent (operator, 09:54 ET: "Yes").
v4.19  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v4.18 2026-10-05  OTV4TEST r252 (BOX.18) - THE PLANS PANEL READS THIS BOX'S INSTRUMENT'S HEARTBEATS ONLY. plan_heartbeat
      is keyed (symbol, plan) and was read with no symbol, so SPX-TEST's panel listed AAL's frozen heartbeats from its AAL
      days as 15 STALE plans while every SPX heartbeat was current (operator's screenshot, 10-05 11:05 ET). UNSET reads
      every row, as before. FORK-ONLY IN EFFECT: 1-REPORTER measured otv4 335d355 - mainline's query.py is v4.11 and has
      no plan_heartbeat; v4.17's "1-REPORTER mirrors" no longer describes these two files, which have diverged.
v4.17 2026-09-26  OTV4TEST r152 — THIS FILE READS ITS OWN TREE, AND A FAILED CONFIG IMPORT SAYS SO. SHARED
      with otv4 (WA section 38.2: this tree authors, 1-REPORTER mirrors the same code and gate). Three sites,
      found when a WIN.1 worktree checker went red on the LIVE config (Q1-Q3, 2026-09-26): (1) INSTALL_DIR was
      the expanded "~/options-trader" and went FIRST on sys.path at import, so a checker importing query from
      any other tree loaded the live config.py — it is now this file's own directory, identical on a box;
      (2) get_live_price() re-inserted it on EVERY call behind an except that returns None, growing sys.path
      and turning a wrong-module bind into a silent missing price — removed; (3) the DB_PATH fallback swallowed
      a failed `from config import` and resolved to "~/options-trader/trades.db" — on control a stray directory
      whose only row is a checker fixture (orb-T1, NVDA) — it now resolves inside this tree AND prints what it
      caught to stderr. Gate tests/check_query_paths.py Q1-Q4. Operator: "Send it".
v4.16 2026-09-26  OTV4TEST r146 — the last-resort fallback is UNSET, not QQQ: the unit's own OT_INSTRUMENT is still read first.
v4.15  2026-09-21  OTV4TEST r84 — ONE WORD PER GATE: QUOTA HIT, AT CAP, HALTED,
      NO CHAIN, RETIRED, POSITION OPEN, AWAITING AUTH, WINDOW CLOSED. Operator
      on the butterflies reading a bare HELD: *"shouldn't the plan say
      something about that? Something like quota hit."* An unknown gate
      degrades to HELD, never to a blank.
v4.14  2026-09-21  OTV4TEST r83 — THE PLANS PANEL IS REBUILT ON A
      HEARTBEAT. Operator: *"I wanna see on that page if my strategies are
      actively evaluating the feed. If they're not then say that, and if they
      are tell me what they're looking at"*, and *"I don't think stale needs to
      be the same thing as window closed."* The old panel inferred liveness
      from plan_tick row AGE against a 300s cut, but r41 made those rows
      EDGE-TRIGGERED: measured 14:44, 16 of 18 flagged STALE and ALL 16 WERE
      CORRECT. It now reads `plan_heartbeat` — EVALUATING / WINDOW CLOSED /
      HELD / NO PLAN / STALE / NOT RUNNING — and every clock renders in ET.
v4.13 2026-09-17  OTV4TEST r34 — MOVED BACK TO THE REPO ROOT with status.py and
      configure.sh (operator's ruling). r14 bucketed by file type, not by role.
      No behaviour change.
v4.12 2026-09-11
v4.12  2026-09-14  OTV4TEST r26 — "ATPButterfly" abbreviates to "ATP" (was truncated to "ATPBu").
v4.11  2026-09-11  OTV4TEST r14 — moved from the repo root to tools/ (root cleanup); no behaviour change.
v4.10 2026-09-09  OTV4TEST r8 — NOT ASKED rows are hushed too. Operator: "Not asked
      is exactly what I don't want to know … until we have an open vertical
      spread, then it needs to let me know it's looking for a complementary
      partner." That case is a HOLD/PREPARED row from CondorManagement, never a
      NOT ASKED — so every NOT ASKED joins the hushed line.
v4.9  2026-09-02  OTV4TEST r7 — DECISIONS hushes plans outside their window.
      Operator, 2026-09-09: "the bot should see everything. Just don't show
      it to me on the products I actively use." DORMANT rows stay in the
      store; ENTER ON lists a dormant strategy as one line of names under
      "hushed (outside their window)" instead of a block each. Same for the
      management plans' "no open position — nothing to manage" NOT ASKED rows.
v4.8  2026-09-02  r216 — 🔴 THE P&L PERCENT COLUMN WAS OFF BY 100x SINCE r210.
      `pnl_pct` is a FRACTION — trade_logger:650 stores
      `(exit_price - entry_prem) / entry_prem` — so a doubling is 1.07. r210
      replaced `pct_str`, which is `f"{val:+.1%}"` and multiplies by 100,
      with a bare `:.0f` while narrowing the row for the phone. SPX on
      2026-09-02 showed a 9.15 -> 18.95 runaway as "+1%".
      ⚠️ THE DOLLARS WERE RIGHT THROUGHOUT, which is exactly why it survived:
      "+$1,960  +1%" reads as a strange percentage, not a broken one, and
      nothing else on the board contradicted it.
      ⚠️ AND THE UNITS WERE READABLE THE WHOLE TIME. I narrowed a column and
      swapped its formatter without checking what the old one was doing —
      `%` in a format spec multiplies, and dropping it silently changes the
      units of the number, not just its width.
v4.7  2026-09-01  r214 — 🔴 THE UNREALIZED LINE WAS SIGN-INVERTED ON EVERY
      CREDIT SPREAD, and had been since the panel was written. It applied the
      DEBIT formula `(now - cost)` to every structure. A credit vertical's
      `current_premium` is the SPREAD'S CURRENT VALUE — what it costs to buy
      back — and the position profits as that FALLS, so its P&L is
      `(credit - now)`, the mirror. A winning sweep printed as a loser and a
      losing one printed as a winner, on the one line the operator reads
      before deciding whether to intervene.
      ⚠️ DISPLAY ONLY, AND VERIFIED RATHER THAN ASSUMED. The same expression
      appears EIGHT times in exit_engine.py and every one is a DEBIT evaluator
      (`_evaluate_orb`, `_evaluate_sweep` — the retired long SweepReversal —
      `_evaluate_butterfly`, `_evaluate_adopted`), where it is correct.
      `_evaluate_condor_leg`, the credit path, already computes
      `(entry_prem - current_premium)`. So no exit decision was ever taken on
      the wrong sign and no trade was mis-managed; only the report lied. S3
      pins that, because the obvious "tidy-up" — making the eight consistent
      with this fix — would invert every debit exit in the book.
      🔑 THE CLASSIFIER IS `structure.is_credit_vertical`, the one the engine
      uses. r22's doctrine: DERIVE it, never add a column — a column fixes
      tomorrow and not today, because every position opened before the
      migration rehydrates without it and `None` reads as `False`, which is
      the exact failure, silently.
      ⚠️ `unrealized()` IS EXTRACTED so the check executes the real function.
      S2's first draft re-implemented the formula in the test and passed
      against the BROKEN version, because the copy was right — C.23.
      Found via day_trader_pro r236, which got the sign right in standings.py
      and deliberately did not copy this one (RPT.6).
v4.6
v4.6  2026-09-01  r210 (chunk B) — TODAY ONLY, AND ONE LINE PER ROW.
      Operator, 2026-09-01: PLANS "only TODAY's Plans"; GATES "only TODAY's
      gates and use abbreviations — it's spanning multi-line"; the closed
      table "get rid of the grade column & abbreviate".
      🔑 ONE DEFINITION OF TODAY. r172 inlined the 09:30 cut inside
      show_decisions; gates and plans need the same boundary now, so it is
      extracted as `session_start_epoch()` — three copies of a boundary is
      two chances for two of them to disagree about what day it is (§7). The
      cut is the OPEN, not midnight: a 06:00 maintenance wake writes real
      rows against a market that is not trading.
      ⚠️ GATES WAS ON A 24-HOUR WINDOW, which reached into YESTERDAY's
      session — a morning read mixed last afternoon's refusals with this
      morning's, separated by nothing but a bare HH:MM.
      🔴 AND THE `-4 hours` EDT HARDCODE WAS IN show_today TOO. Same class
      r125 fixed in the otv4 sensors and dtp r236 found in standings.py
      (RPT.8): right for eight months, silently wrong for four, and the
      failure is a table filtering on the WRONG DAY rather than one that
      errors. Read from the tz database now.
      ⚠️ LAST 10 CLOSED IS MERGED AWAY. Scoping both tables to today made
      them the same table — one filtered by date, one by a LIMIT that landed
      on the same rows. Two sections rendering one answer is §35's rot.
      ⚠️ `trade_row()` IS EXTRACTED SO THE WIDTH CHECK MEASURES THE REAL
      LINE. Q11's first draft rebuilt the format inside the test and measured
      its own copy — C.23, the r181 sizing checker that was green for two
      days because it re-implemented what it was pinning.
v4.5  2026-09-01  r209 (chunk A) — FOUR SECTIONS AND TWO PANELS REMOVED, on
      the operator's reading of what this dashboard is FOR. It is the PER-BOX
      report; an all-time or by-strategy rollup computed from one symbol's
      trades.db is a slice nobody acts on. His words, going bottom-up:
      Live Levels "don't care, take it out"; by setup type "just trivia in my
      opinion, useless by itself"; by setup grade "we don't have grades";
      by strategy "I don't need a per symbol snapshot of that"; all-time
      "irrelevant"; Character "keep, but not in query.py — it belongs in
      status, below the pin line."
      🔴 AND ALL-TIME WAS QUIETLY WRONG, not merely noisy. This file has no
      ENGINE EPOCH floor, so it pooled pre- and post-v4-split trades — 109 of
      them, reaching back through engines that no longer exist. r187 built
      that floor for exactly this contamination and this file never got it.
      ⚠️ BY SETUP GRADE was structurally empty: r152 deleted the scorer and
      every v4 write path hardcodes UNGRADED, so it had one bucket forever.
      ⚠️ THE CROSS-FLEET VERSIONS ALREADY EXIST AND ARE THE RIGHT HOME —
      day_trader_pro's trade breakdown (r187) groups by strategy, setup type,
      exit reason, symbol, hour and weekday across every box, epoch-floored.
      Nothing is lost; it is asked in the place that can answer it.
      ⚠️ A VIEW CHANGE, NOT A COLLECTOR CHANGE. `level_ledger` is still
      written and still read by the sweep and the fork; r81 keeps it unpurged
      in code because a recomputation cannot rebuild a biography. Q4 pins it.
      ⚠️ CHARACTER RENDERS NOWHERE UNTIL CHUNK C, and that costs nothing:
      r85 set BANDS_SET=False, so the panel has printed "No character
      recorded yet today" on every box since. Stated, not discovered.
v4.4  2026-08-31  r199 — EVERY OPEN POSITION GETS ITS OWN CARD, and a
      summed deployed figure heads them. `LIMIT 1` had been rendering one
      position as the whole book since r161 made the butterfly additive;
      CRM held a runaway and a butterfly on 2026-08-31 and showed one.
v4.3  2026-08-28  r172 — THE DECISIONS PANEL SHOWS TODAY'S SESSION, OR
      NOTHING. Operator: "Make the decision section only display today's
      decision, blank before 0930" and "If the box was up for maintenance the
      night before or even before the session open, don't display those
      decisions." It showed the newest plan_tick row per strategy WHATEVER ITS
      AGE — read at 09:16 ET it printed twelve rows from the previous evening,
      each flagged STALE, in a panel titled "the next tick, as the plans see it
      now." The cut is the OPEN (09:30 ET), not midnight, so a maintenance wake
      is excluded too; both the ENTER and EXIT halves are bounded. Asked in ET
      via ZoneInfo("US/Eastern"), which follows DST — a bare date.today() on a
      UTC box rolls the day at 20:00 ET. Pinned by tests/check_decisions_today.py
      (D2 mutation-proven).

v4.2  2026-08-27  r170 — THE DECISIONS PANEL. Operator: *"have query.py
      snapshot active trade decisions 'enter on' and 'exit on' for active
      plans. Trade log & all time performance should stay."* New
      show_decisions(): the newest plan_tick row per strategy (ENTER ON —
      the PREPARED trade and what it waits on, or the structural fault) and
      the newest <Strategy>/manage row per open position (EXIT ON — "if this
      or this, out"), each stamped and flagged ⚠️ STALE past 5 minutes.
      `--decisions` renders only the snapshot for the fleet reader in
      day_trader_pro devtools; the full dashboard (trade log, all-time,
      market) is the unchanged default.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Ad-hoc trade and store queries.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

query.py — OptionsTrader Performance Dashboard
None-guard the open-position setup_score display: condor
        legs log a NULL score (delta street-sign is NULL when Greeks are
        unavailable), which crashed the dashboard with TypeError on :.2f.
        Now renders "score=n/a" instead of raising.
v3.0 — original
Fix: read INSTRUMENT from systemd env via get_runtime_env()
W/L consistency: a $0 (scratch) trade is no longer counted
        as a loss (was pnl<=0), matching status.py (pnl<0). Reconciles the
        0W/0L vs 0W/1L mismatch between the two tools on breakeven trades.
                     config.py fallback is QQQ but live bot may be configured for SPX
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
Options-specific: strikes, premiums, delta, P&L, butterfly legs, session stats.
"""

import sqlite3
import os
import re
import sys
import subprocess
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# r152 — THIS FILE'S OWN TREE, never an assumed "~/options-trader": on a box the two are
# the same directory; from a worktree or clone the old path loaded the LIVE config.
INSTALL_DIR = os.path.dirname(os.path.abspath(__file__))
if INSTALL_DIR not in sys.path:
    sys.path.insert(0, INSTALL_DIR)

try:
    from config import DB_PATH
    SERVICE_NAME = "optionsbot"
except Exception as _cfg_exc:                                   # noqa: BLE001
    # r152 — NAMED, NOT SWALLOWED: a silent fallback bound readers to whatever trades.db sat at
    # the assumed path (on control: a checker fixture) with no sign anything had failed.
    DB_PATH            = os.path.join(INSTALL_DIR, "trades.db")
    SERVICE_NAME       = "optionsbot"
    print(f"query.py: config did not load ({type(_cfg_exc).__name__}: {_cfg_exc}) "
          f"- falling back to {DB_PATH}", file=sys.stderr)

ET  = ZoneInfo("America/New_York")
UTC = timezone.utc


def get_runtime_env(key: str, default: str = "") -> str:
    """Read a live environment variable from the systemd service — mirrors status.py."""
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


# Always read instrument and mode from live systemd environment — same as status.py
INSTRUMENT    = get_runtime_env("OT_INSTRUMENT",   "UNSET")  # r146: never QQQ by default
PAPER_TRADING = get_runtime_env("OT_PAPER_TRADING", "True") != "False"
BOT_NAME      = get_runtime_env("OT_BOT_NAME",      "OptionsTrader")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def connect():
    if not os.path.exists(DB_PATH):
        print(f"\n  Database not found at {DB_PATH}")
        print("  Has the bot entered any trades yet?")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def to_et(ts: str) -> str:
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(ET).strftime("%m/%d %H:%M ET")
    except Exception:
        return ts[:16]


def now_et():
    return datetime.now(ET)


def today_et_prefix():
    return now_et().strftime("%Y-%m-%d")


def pnl_str(val: float) -> str:
    if val is None:
        return "  N/A"
    return f"+${val:.2f}" if val >= 0 else f"-${abs(val):.2f}"


def pct_str(val: float) -> str:
    if val is None:
        return "  N/A"
    return f"{val:+.1%}"


def bar(pct: float, width: int = 20) -> str:
    filled = max(0, min(width, int(pct / 100 * width)))
    return "█" * filled + "░" * (width - filled)


def session_start_epoch() -> float:
    """Today's 09:30 ET as an epoch — THE one definition of "today" here.

    🔑 THE CUT IS THE OPEN, NOT MIDNIGHT, and r172 established why: a 06:00 ET
    maintenance wake writes real plan rows against a market that is not
    trading, and showing those in a panel about the session is the same lie as
    showing last night's, only harder to spot because the date matches.

    ⚠️ EXTRACTED AT r210 (chunk B) BECAUSE THREE PANELS NOW NEED IT. r172
    inlined this in `show_decisions`; gates and plans are being scoped to the
    same window, and three copies of a boundary is three chances for two of
    them to disagree about what day it is — WORKING_AGREEMENT 7.

    ⚠️ ET, NOT THE BOX CLOCK. The boxes run UTC and a bare `date.today()` rolls
    the day at 20:00 ET, which is the operator's own long-standing symptom.
    """
    return now_et().replace(hour=9, minute=30, second=0,
                            microsecond=0).timestamp()


# ── SHORT NAMES, BECAUSE THE READER IS A PHONE ──────────────────────────────
# 🔑 Operator, 2026-09-01: the gates and the trade table are "spanning
# multi-line". Termius on a phone wraps around 60 characters, and a row that
# wraps is a row that has to be reassembled by eye before it can be read.
# ⚠️ AN UNKNOWN NAME IS TRUNCATED, NEVER DROPPED — a blank column would
# silently hide a strategy nobody added to this table (r202's rule, same table).
_STRAT_ABBR = {
    "ORBStrategy": "ORB", "RunawayContinuation": "RUN",
    "GEXPinButterfly": "BFLY", "ATPButterfly": "ATP", "SweepCreditSpread": "SWP",
    "TrendCreditSpread": "TCS", "IronCondorStrategy": "CNDR",
    "CondorManagement": "CMGT", "CreditRoll": "ROLL",
    "SweepReversal": "SWPR", "ContinuationStrategy": "CONT",
}

# Exit reasons carry their own P&L in the string (r16), so they are long AND
# unbounded. These are the stems; anything else truncates to 8.
_EXIT_ABBR = (
    ("hard_stop", "stop"), ("orb_structure_stop", "struct"),
    ("structure_stop", "struct"), ("target_hit", "target"),
    ("orb_trail_stop", "trail"), ("trail_stop", "trail"),
    ("theta_bleed", "theta"), ("velocity", "stall"),
    ("nickel", "nickel"), ("flatten", "flat"), ("acceptance", "accept"),
)


def abbr_strategy(name) -> str:
    n = str(name or "?")
    return _STRAT_ABBR.get(n, n[:4].upper())


def trade_row(r) -> str:
    """One closed trade, one line, 60 characters or fewer.

    🔑 EXTRACTED SO THE CHECK CAN MEASURE THE REAL THING. The first cut of
    `check_query_sections` Q11 rebuilt this format string inside the test and
    measured its own copy — C.23, the r181 sizing checker that stayed green for
    two days because it re-implemented the arithmetic it was meant to pin. A
    width test that reads a reconstruction proves the reconstruction fits.

    ⚠️ WHOLE DOLLARS AND WHOLE PERCENT HERE ONLY. The row already carries entry
    and exit to the cent, so "-$82.00 -26.3%" spent eight characters restating
    precision nobody acts on — and eight characters is the difference between
    one line and two on a phone. Stored values are untouched and `pnl_str` /
    `pct_str` keep full precision everywhere else.
    """
    if bool(r["is_butterfly"]):
        contract = f"{r['center_strike']:.0f}BF"
    else:
        side = (r["option_side"] or "")[:1].upper()
        contract = f"{side}{r['strike']:.0f}" if r["strike"] else "n/a"
    pnl = r["pnl_usd"] or 0
    money = f"{'+' if pnl >= 0 else '-'}${abs(pnl):,.0f}"
    return (f"  {to_et(r['exit_time'])[6:11]:<5} "
            f"{abbr_strategy(r['strategy']):<4} "
            f"{contract:<7} "
            f"{r['contracts'] or 0:>3} "
            f"{r['entry_premium'] or 0:>5.2f} "
            f"{r['exit_premium'] or 0:>5.2f} "
            f"{money:>8} "
            # 🔴 r216 — `pnl_pct` IS A FRACTION, NOT A PERCENTAGE.
            # trade_logger:650 stores `(exit_price - entry_prem) / entry_prem`,
            # so a doubling is 1.07 and not 107. r210 replaced `pct_str`, which
            # is `f"{val:+.1%}"` and multiplies by 100, with a plain `:.0f` —
            # and every closed trade since has rendered its move as a rounding
            # error. SPX 2026-09-02: 9.15 -> 18.95 printed as "+1%".
            # ⚠️ THE P&L COLUMN WAS RIGHT THE WHOLE TIME, which is what made it
            # survive a night: a +$1,960 row beside "+1%" reads as an odd
            # percentage rather than as a broken one.
            # ⚠️ ONE SPACE, NOT TWO, BEFORE THE REASON. Correcting the units
            # widened this column: "+1%" was 3 characters and "+107%" is 5, so
            # the row went to 61 and Q11 caught it. The character comes back
            # from the gap rather than from the width rule — 60 is the phone.
            f"{(r['pnl_pct'] or 0) * 100:>+4.0f}% "
            f"{abbr_reason(r['exit_reason'])}")


def abbr_reason(reason) -> str:
    """The exit reason, short. ⚠️ The percentage is DROPPED, not the cause —
    the row already prints P&L% in its own column, so keeping it in the reason
    was the same number twice at the cost of the wrap."""
    r = str(reason or "")
    for stem, short in _EXIT_ABBR:
        if r.startswith(stem):
            return short
    return r.split()[0][:8] if r else ""


def sep(char: str = "─", width: int = 62):
    print(char * width)


def get_service_status() -> str:
    try:
        import subprocess
        result = subprocess.run(
            ["systemctl", "is-active", SERVICE_NAME],
            capture_output=True, text=True
        )
        status = result.stdout.strip()
        return "🟢 ACTIVE" if status == "active" else f"🔴 {status.upper()}"
    except Exception:
        return "UNKNOWN"


def get_live_price() -> float | None:
    try:
        from data.market_data import fetch_quote          # r152: no per-call sys.path insert
        return fetch_quote(INSTRUMENT)
    except Exception:
        return None


# ─── Sections ─────────────────────────────────────────────────────────────────

def show_header():
    mode = "📄 PAPER" if PAPER_TRADING else "🔴 LIVE"
    status = get_service_status()
    sep("═")
    print(f"  {BOT_NAME} — PERFORMANCE DASHBOARD")
    print(f"  {now_et().strftime('%Y-%m-%d %H:%M:%S ET')}")
    sep("═")
    print(f"  Service:     {status}")
    print(f"  Instrument:  {INSTRUMENT}")
    print(f"  Mode:        {mode}")
    print()


def show_open_position(conn):
    """Every open position, each with its full detail card.

    🔴 r199 — THIS ASKED FOR `LIMIT 1`. Latent since r161 made the butterfly
    additive; measured 2026-08-31 on CRM, which held a runaway AND a butterfly
    and showed one. r197 makes multi-position boxes the norm.

    ⚠️ THE SUMMED EXPOSURE IS THE POINT, not just the extra card. This function
    already splits deployed / at-risk / max-loss per position (r121, after
    "How is 2 contracts at $96 costing me $800???"). Showing one position's
    three numbers while a second sits unmentioned recreates exactly the
    confusion r121 fixed, one level up.
    """
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM trades WHERE status='open' ORDER BY entry_time ASC"
    ).fetchall()]

    sep("═")
    print(f"  OPEN POSITIONS  ({len(rows)})" if len(rows) != 1
          else "  OPEN POSITION")
    sep("═")

    if not rows:
        print("  ⏳ No open position.")
        print()
        return

    if len(rows) > 1:
        _dep = sum((r.get("total_cost") or 0) for r in rows)
        print(f"  📦 {len(rows)} positions on this box  —  "
              f"${_dep:,.2f} deployed in total")
        print()

    for _i, row in enumerate(rows, 1):
        if len(rows) > 1:
            sep("─")
            print(f"  [{_i}/{len(rows)}]  {row.get('strategy') or '?'}")
        _show_one_open(row)


def unrealized(row, entry_prem, current_prem, contracts):
    """(dollars, fraction) of open P&L, SIGNED BY STRUCTURE. (None, None) when
    the box has not stamped a mark yet.

    🔑 EXTRACTED SO THE CHECK CAN EXECUTE THE REAL THING. The first cut of
    check_unrealized_sign S2 re-implemented this formula inside the test and
    measured its own copy, which passed against the BROKEN version — C.23, the
    r181 sizing checker that stayed green for two days because it
    re-implemented the arithmetic it was meant to pin.

    ⚠️ ABSENT IS NOT ZERO. No mark returns None, never 0.00: a fabricated zero
    on a live position reads as a flat trade.
    ⚠️ AND IT FAILS CLOSED TO DEBIT — every legacy row in this book is one.
    """
    if not current_prem or not entry_prem:
        return None, None
    try:
        from strategy.structure import is_credit_vertical as _is_cv
        # ⚠️ `sqlite3.Row` has no `.get`; the classifier takes a Mapping.
        credit = _is_cv(dict(row))
    except Exception:                                           # noqa: BLE001
        credit = False
    move = (entry_prem - current_prem) if credit else (current_prem - entry_prem)
    return move * contracts * 100, move / entry_prem


def _show_one_open(row):
    is_bf      = bool(row["is_butterfly"])
    entry_prem = row["entry_premium"] or 0
    stop_prem  = row["stop_premium"]  or 0
    target_prem= row["target_premium"]or 0
    contracts  = row["contracts"]     or 0
    total_cost = row["total_cost"]    or 0

    # Try to get live option premium
    live_prem  = None
    live_pnl   = None
    live_pnl_pct = None
    try:
        from data.market_data import fetch_quote
        underlying = fetch_quote(INSTRUMENT)
    except Exception:
        underlying = None

    # Position description
    if is_bf:
        pos_desc = (
            f"BUTTERFLY {(row['option_side'] or '').upper()}  "
            f"{row['lower_strike']:.0f} / {row['center_strike']:.0f} / {row['upper_strike']:.0f}"
        )
    else:
        pos_desc = f"{(row['option_side'] or '').upper()}  Strike {row['strike']:.0f}"

    # ── 🔴 r214 — THE UNREALIZED LINE WAS SIGN-INVERTED ON EVERY CREDIT
    #    SPREAD, AND HAD BEEN SINCE THE PANEL WAS WRITTEN ──────────────────
    # It applied the DEBIT formula `(now - cost)` to every structure. A credit
    # vertical's `current_premium` is the SPREAD'S CURRENT VALUE — the cost to
    # buy it back — and the position profits as that FALLS, so its P&L is
    # `(credit - now)`, the mirror. A winning sweep printed as a loser and a
    # losing one printed as a winner, on the one line the operator reads to
    # decide whether to intervene.
    # ⚠️ DISPLAY ONLY — VERIFIED, NOT ASSUMED. The same expression appears
    # eight times in exit_engine.py and every one of them is a DEBIT evaluator
    # (`_evaluate_orb`, `_evaluate_sweep` — the retired long SweepReversal —
    # `_evaluate_butterfly`, `_evaluate_adopted`), where it is correct.
    # `_evaluate_condor_leg`, the credit path, already computes
    # `(entry_prem - current_premium)`. So no exit decision was ever taken on
    # the wrong sign and no trade was mis-managed; only the report lied.
    # 🔑 THE TEST IS `structure.is_credit_vertical`, THE ONE THE ENGINE USES.
    # r22's doctrine: DERIVE the classification, never add a column — a column
    # fixes tomorrow and not today, because every row opened before the
    # migration rehydrates without it and `None` reads as `False`, which is the
    # exact failure silently. Deriving works on rows that already exist.
    # ⚠️ `sqlite3.Row` HAS NO `.get`, so it is converted to a plain dict first;
    # passing the Row straight in would raise inside a display path.
    # ⚠️ AND IT FAILS CLOSED: an unrecognised record is treated as a DEBIT,
    # which is what every legacy row in this book is.
    current_prem = row["current_premium"] if row["current_premium"] else None
    live_pnl_usd, live_pnl_pct = unrealized(row, entry_prem, current_prem,
                                            contracts)

    print(f"  ID:            {row['trade_id'][:8]}")
    print(f"  Position:      {pos_desc}")
    print(f"  Strategy:      {row['strategy']}  |  Setup: {row['setup_type']}")
    _score = row['setup_score']
    _score_str = f"score={_score:.2f}" if _score is not None else "score=n/a"
    print(f"  Grade:         {row['setup_grade']}  ({_score_str})")
    print(f"  Expiry:        {row['expiry']}")
    print(f"  Contracts:     {contracts}")
    print()

    print(f"  Entry Premium: ${entry_prem:.2f}/share  (${entry_prem * 100:.2f}/contract)")
    # ── 🔴 r121 — THREE NUMBERS, NOT ONE ──────────────────────────────────
    # Operator, 2026-08-25, on CVX's card: "How is 2 contracts at $96 costing
    # me $800???" — and then the correction that named the confusion exactly:
    # "I do still want the cost shown, but part of that cost is ownership of
    # contracts. Dollars out, contracts that have value in."
    # "Total Cost" was collapsing three different facts into one line, and for
    # a CREDIT spread it was not a cost at all: CVX's $808 is width-minus-credit
    # margin against $192 RECEIVED, so the label was wrong by sign as well as
    # by meaning.
    #   Deployed  — dollars out, held as contracts that still have value
    #   At risk   — deployed minus what the stop hands back; the real exposure
    #   Max loss  — the whole deployment, which is what a gap through a SOFT
    #               stop actually costs
    _is_credit = bool(row["is_condor_leg"] or 0) or (row["credit_received"] or 0) > 0
    if _is_credit:
        _credit = (row["credit_received"] or 0) * contracts * 100
        print(f"  Credit rec'd:  ${_credit:.2f}  (received, not paid)")
        print(f"  Capital @risk: ${total_cost:.2f}  "
              f"(width − credit; margin held, not spent)")
    else:
        _stop_p = row["stop_premium"] or 0.0
        _risk   = ((entry_prem - _stop_p) * contracts * 100) if _stop_p else total_cost
        print(f"  Deployed:      ${total_cost:.2f}  "
              f"({contracts} contract(s) owned, still worth something)")
        print(f"  Capital @risk: ${_risk:.2f}  "
              f"(to the ${_stop_p:.2f} stop)" if _stop_p else
              f"  Capital @risk: ${_risk:.2f}")
        if _stop_p and _risk < total_cost:
            print(f"  Max loss:      ${total_cost:.2f}  "
                  f"(gap through the stop — it is soft, not resting)")
    if current_prem:
        print(f"  Current Mark:  ${current_prem:.2f}/share  (${current_prem * 100:.2f}/contract)")
    if live_pnl_usd is not None:
        pnl_label = f"+${live_pnl_usd:.2f}" if live_pnl_usd >= 0 else f"-${abs(live_pnl_usd):.2f}"
        pct_label = pct_str(live_pnl_pct)
        print(f"  Unrealized P&L:{pnl_label}  ({pct_label})")
    print(f"  Stop Premium:  ${stop_prem:.2f}  ({pct_str((stop_prem - entry_prem) / entry_prem if entry_prem else 0)} from entry)")
    print(f"  Target:        ${target_prem:.2f}  ({pct_str((target_prem - entry_prem) / entry_prem if entry_prem else 0)} from entry)")

    if row["trail_activation"]:
        print(f"  Trail Trigger: ${row['trail_activation']:.2f}")

    print()

    # Underlying price context
    if underlying:
        print(f"  Underlying:    ${underlying:,.2f}  (live)")
    if row["underlying_entry"]:
        print(f"  Entry Spot:    ${row['underlying_entry']:,.2f}")
    if row["underlying_stop"]:
        print(f"  Spot Stop:     ${row['underlying_stop']:,.2f}")
    if row["underlying_target"]:
        print(f"  Spot Target:   ${row['underlying_target']:,.2f}")

    print()
    print(f"  VIX at Entry:  {row['vix_at_entry']:.1f}" if row["vix_at_entry"] else "  VIX at Entry:  N/A")
    print(f"  Fed Day:       {'Yes ⚠️' if row['is_fed_day'] else 'No'}")
    print(f"  Paper:         {'Yes' if row['paper_trade'] else 'No'}")
    print(f"  Entered:       {to_et(row['entry_time'])}")
    print()


def show_today(conn):
    # 🔴 r210 (chunk B) — THE OFFSET WAS A HARDCODED '-4 hours'. That is EDT:
    # correct for eight months and silently wrong for four, and the failure is
    # a table filtering on the WRONG DAY rather than one that errors. r125
    # found and fixed this exact class in the otv4 sensor reports and this
    # query kept it; dtp r236 found the twin in standings.py (RPT.8). Read
    # from the tz database, so it is -4 in September and -5 in December
    # without anyone remembering.
    # ⚠️ ENTRY DATE, NOT EXIT DATE, DELIBERATELY. status.py's TODAY'S SESSION
    # and the EOD rollup both key on entry, and a table that disagreed with the
    # panel above it about which trades are "today" is worse than one that
    # misses a rare overnight close. Changing the semantics is its own call.
    today = today_et_prefix()
    off = f"{int(now_et().utcoffset().total_seconds() // 3600)} hours"
    rows = conn.execute(
        """SELECT * FROM trades
           WHERE status='closed'
           AND date(datetime(entry_time, :off)) = :day
           ORDER BY exit_time""",
        {"off": off, "day": today}
    ).fetchall()

    sep()
    print(f"  TODAY'S TRADES  ({today} ET)")
    sep()

    if not rows:
        print("  No closed trades today.")
        print()
        return

    wins      = [r for r in rows if (r["pnl_usd"] or 0) > 0]
    losses    = [r for r in rows if (r["pnl_usd"] or 0) < 0]   # v1.2: strict; $0 is a scratch, not a loss (match status.py)
    total_pnl = sum(r["pnl_usd"] or 0 for r in rows)
    win_rate  = len(wins) / len(rows) * 100 if rows else 0
    total_cost= sum(r["total_cost"] or 0 for r in rows)
    pnl_pct   = total_pnl / total_cost * 100 if total_cost else 0

    print(f"  Trades:        {len(rows)}  ({len(wins)}W / {len(losses)}L)")
    print(f"  Win Rate:      {win_rate:.0f}%  {bar(win_rate, 15)}")
    print(f"  Net P&L:       {pnl_str(total_pnl)}  ({pnl_pct:+.1f}% of capital deployed)")
    if wins:
        print(f"  Best Trade:    {pnl_str(max(r['pnl_usd'] or 0 for r in wins))}")
    if losses:
        print(f"  Worst Trade:   {pnl_str(min(r['pnl_usd'] or 0 for r in losses))}")
    print()

    # Trade detail table
    # ⚠️ SAME CHANGE, DIFFERENT FORMAT. Every row in TODAY'S TRADES is from
    # today, so the date would be noise; the exit TIME is what separates them.
    # 🔴 r210 (chunk B) — THE GRADE COLUMN IS GONE AND THE ROW FITS THE PHONE.
    # Operator, 2026-09-01: "get rid of the grade column & abbreviate though"
    # — the old row ran past 90 characters and wrapped onto a second line on
    # every trade, so a nine-trade session read as eighteen.
    # ⚠️ GRADE WAS A COLUMN THAT COULD ONLY EVER SAY ONE THING: r152 deleted
    # the setup scorer and every v4 write path hardcodes UNGRADED. Six
    # characters of "UNGRADED" per row, on every row, forever.
    # ⚠️ THE EXIT REASON KEEPS ITS CAUSE AND LOSES ITS PERCENTAGE. r16 writes
    # the trade's own P&L into the reason string, so "hard_stop_25% pnl=-26.3%"
    # was printing a number the row already has in its own column — the same
    # value twice, at the cost of the wrap.
    print(f"  {'time':<5} {'strat':<4} {'contract':<7} {'n':>3} "
          f"{'entry':>5} {'exit':>5} {'P&L':>8} {'pct':>6}  why")
    sep()
    for r in rows:
        is_bf = bool(r["is_butterfly"])
        if is_bf:
            contract = f"{r['center_strike']:.0f}BF"
        else:
            side = (r["option_side"] or "")[:1].upper()
            contract = f"{side}{r['strike']:.0f}" if r["strike"] else "n/a"

        print(trade_row(r))
    print()


def show_circuit_breakers(conn):
    rows = conn.execute(
        "SELECT * FROM circuit_breaker_events ORDER BY event_time DESC LIMIT 5"
    ).fetchall()

    if not rows:
        return

    sep()
    print("  RECENT CIRCUIT BREAKER EVENTS")
    sep()
    for r in rows:
        print(
            f"  {to_et(r['event_time'])}  "
            f"losses={r['session_losses']}  "
            f"{r['reason'] or ''}"
        )
    print()



# ═══════════════════════════════════════════════════════════════════════════
# MARKET DATA — r76. The derived layer, which query.py could not see until now.
# ═══════════════════════════════════════════════════════════════════════════
# ⚠️ EVERY SECTION BELOW READS THE DERIVED STORE, NOT trades.db. It opens
# READ-ONLY and every section degrades to a printed note rather than an
# exception: a dashboard that cannot render because one sensor is empty is
# worse than one that says which sensor is empty.
#
# ⚠️ AND ABSENCE IS PRINTED AS ABSENCE. "no rows yet" and "this box has never
# written this table" are different facts; a blank section conflates them,
# which is the habit this project has paid for repeatedly.

def _derived():
    """Read-only handle on the derived store, or None."""
    try:
        import os as _os
        import sqlite3 as _sq
        path = _os.environ.get(
            "OT_DERIVED_DB",
            _os.path.expanduser("~/options-trader/data/derived_store.db"))
        if not _os.path.exists(path):
            return None
        return _sq.connect(f"file:{path}?mode=ro", uri=True)
    except Exception:                                           # noqa: BLE001
        return None


def _q(dc, sql, args=()):
    try:
        return dc.execute(sql, args).fetchall()
    except Exception:                                           # noqa: BLE001
        return None                    # None = table absent; [] = no rows


def show_gates(dc):
    """Which rung is refusing each strategy, and for how long.

    🔴 THIS IS THE SECTION THAT WOULD HAVE ANSWERED 2026-08-21. The fleet
    declined every setup on every box all session and could not say why: the
    journal held one event type and every other refusal was a debug line. SPX
    re-confirmed at 10:46 and sat refused for 44 minutes with nothing recording
    which gate said no.
    """
    sep("═")
    print("  GATES  (why a strategy is not trading)")
    sep("═")
    # 🔴 r210 (chunk B) — TODAY ONLY, AND ONE LINE PER GATE. Operator,
    # 2026-09-01: "keep, but only want TODAY's gates and use abbreviations —
    # it's spanning multi-line."
    # ⚠️ THE 24-HOUR WINDOW WAS THE WRONG UNIT. It reached back into YESTERDAY's
    # session, so a morning read showed last afternoon's refusals mixed with
    # this morning's with nothing but a bare HH:MM to tell them apart. Same cut
    # as DECISIONS and PLANS now — `session_start_epoch()`, one definition.
    # ⚠️ THE REASON KEEPS ITS FIRST LINE, NOT ALL OF IT. Two lines per gate at
    # 78 characters was four rendered lines on a phone; twelve gates filled the
    # screen and buried the one that mattered. Truncated, never dropped: a
    # refusal with no reason is what r73 exists to prevent.
    rows = _q(dc, "SELECT strategy, gate, reason, event, held_s, ticks,"
                  " ts_epoch FROM gate_disposition"
                  " WHERE symbol=? AND ts_epoch >= ?"
                  " ORDER BY ts_epoch DESC LIMIT 12",
              (INSTRUMENT, session_start_epoch()))
    if rows is None:
        print("  (gate_disposition not present on this box)")
        print(); return
    if not rows:
        print("  No gate transitions today.")
        print(); return
    for st, gate, reason, ev, held, ticks, ts in rows:
        t = datetime.fromtimestamp(ts, ET).strftime("%H:%M")
        # ASCII only: the fleet terminal rendered these as "?" over SSH.
        mark = {"CLEARED": "ok", "CHANGED": "->"}.get(ev, "X ")
        extra = f" {held/60:.0f}m" if held else ""
        why = "" if (ev == "CLEARED" or not reason) else f"  {str(reason)[:24]}"
        print(f"  {t} {mark} {abbr_strategy(st):<4} {str(gate)[:14]:<14}"
              f"{extra}{why}")
    print()


def show_decisions(dc):
    """Is each PLAN actively evaluating the feed — and if so, what is it reading?

    🔴 REPLACED WHOLESALE AT r83 BY RULING. Operator, 2026-09-21, after 16 of
    18 rows on this panel carried ⚠️ STALE while all 16 were behaving
    correctly: *"I wanna see on that page if my strategies are actively
    evaluating the feed. If they're not then say that, and if they are tell me
    what they're looking at."* And then the distinction that shapes it: *"I
    don't think stale needs to be the same thing as window closed. Report
    stale if it really is stale and report window closed if that's the
    reason."*

    🔑 WHY THE OLD PANEL COULD NOT ANSWER THAT. It read the newest `plan_tick`
    row per strategy and flagged anything older than 300 seconds. But r41 made
    those rows EDGE-TRIGGERED by the operator's own ruling — a plan writes one
    row when its verdict changes, then goes quiet — so a plan behaving
    perfectly stops writing and turns "stale" five minutes later. MEASURED
    2026-09-21 14:44: 16 of 18 flagged, every one correct, and the only two
    that read "fresh" were `SweepCreditSpread` and `TrendCreditSpread` —
    fresh solely because their reason text embeds live prices, so every tick
    produced a new string. THE MARKER WAS MEASURING PUNCTUATION.

    Now it reads `plan_heartbeat`, which every plan UPSERTS every tick, so
    liveness is a FACT rather than an inference from row age:
      EVALUATING    — ran this tick; the line shows what it is reading
      WINDOW CLOSED — outside its window, which is WORKING, not a fault
      HELD          — ran and is quiet for a stated reason (already traded,
                      nothing to manage, waiting on a setup)
      ⚠️ NO PLAN    — ASKED and wrote nothing: a real defect
      ⚠️ STALE      — its heartbeat STOPPED. Only this is stale.
      ⚠️ NOT RUNNING— expected by the admission table and never heartbeat at
                      all. On 2026-09-21 `Breakout` sat in exactly this state,
                      absent from the board, its last row frozen at 11:30:08
                      — the same blindness that hid r77's 127 crashes.
    """
    _now = now_et()
    _open = _now.replace(hour=9, minute=30, second=0, microsecond=0)
    sep("=")
    print("  PLANS  (are they reading the feed right now?)")
    sep("=")
    if _now < _open:
        print(f"    nothing yet — the session opens at 09:30 ET "
              f"(now {_now.strftime('%H:%M')})")
        print()
        return

    _hb_all = (not INSTRUMENT) or INSTRUMENT == "UNSET"        # v4.18: this box's instrument only
    hb = _q(dc, "SELECT plan, ts_epoch, tick_id, state, gate, verdict, watching"
                " FROM plan_heartbeat" + ("" if _hb_all else " WHERE symbol=?") + " ORDER BY plan",
            () if _hb_all else (INSTRUMENT,))
    if hb is None:
        print("  (plan_heartbeat not present — bake r83 or older store)")
        print(); return

    now_ts = _now.timestamp()
    # ⚠️ EIGHT MISSED TICKS, NOT ONE. POLL_INTERVAL_SECONDS is 15; a single
    # slow tick is not a fault and a warning that fires on one is the noise
    # this panel was just rebuilt to remove (§36).
    STALE_S = 120.0
    # 🔑 r84 — ONE WORD PER GATE, FROM THE ENGINE'S OWN VOCABULARY. Operator,
    # on the butterflies reading a bare HELD after one had already fired:
    # *"shouldn't the plan say something about that? Something like quota hit."*
    # He is right, and the cause was upstream: MEASURED, 15 of 16 `_plan_skip`
    # sites in main.py passed NO GATE, so every refusal that was not the clock
    # arrived here unlabelled. r84 gates them; this maps them.
    # ⚠️ TWO SPELLINGS OF THE CLOCK, ONE FACT — `sweep_plan`/`tcs_plan` stamp
    # "entry_window", the shared dormancy path stamps "window" (r73's
    # QUIET_GATES holds exactly that name). Both mean the clock, and the
    # operator ruled the clock must never read as STALE.
    # ⚠️ AN UNKNOWN GATE FALLS BACK TO "HELD" RATHER THAN BEING DROPPED: a new
    # gate name must degrade to a vaguer word, never to an empty line.
    _LABEL = {
        "entry_window":      "WINDOW CLOSED",
        "window":            "WINDOW CLOSED",
        "tries_per_session": "QUOTA HIT",
        "max_open_of_type":  "AT CAP",
        "catastrophic_cap":  "HALTED",
        "entry_blocked":     "ENTRY BLOCKED",
        "no_chain":          "NO CHAIN",
        "retired":           "RETIRED",
        "position_open":     "POSITION OPEN",
        "condor_auth":       "AWAITING AUTH",
    }
    # ⚠️ THE BOX RUNS UTC AND EVERY TIME ON THIS PAGE IS AN EXCHANGE FACT.
    # `ts_epoch` is absolute, so it is rendered through ET here rather than
    # with a bare `fromtimestamp`, which would print the box's clock and be
    # four hours wrong all session.
    _et = lambda t: datetime.fromtimestamp(t, ET).strftime("%H:%M:%S") if t else "--:--:--"
    seen, live, quiet, broken = {}, [], [], []
    # r303 (PSTATE.1) — the bot's published plan states. A DORMANT plan writes no heartbeat by ruling, so its
    # old row (or none) is neither STALE nor NOT RUNNING.
    try:
        from strategy import plan_state as _ps
        _sdoc = _ps.read_states_file()
    except Exception:                                           # noqa: BLE001
        _sdoc = {}
    _states = {k: (v or {}).get("state", "") for k, v in ((_sdoc.get("plans") or {}).items())}
    _dormant = sorted(k for k, v in _states.items() if v == "dormant")
    _logonly = sorted(k for k, v in _states.items() if v == "log")
    def _idle_condition(plan):
        """r303 — '' unless `plan` is condition-gated AND nothing it manages is open (then the reason).
        Reads this box's trades.db read-only; an unreadable book says '' (the old STALE stands)."""
        if not (plan.endswith("/manage") or plan in ("CondorManagement", "CreditRoll")):
            return ""
        try:
            _tc = sqlite3.connect("file:%s?mode=ro" % DB_PATH, uri=True, timeout=5)
            try:
                if plan.endswith("/manage"):
                    n = _tc.execute("SELECT COUNT(*) FROM trades WHERE status='OPEN' AND strategy=?",
                                    (plan[:-len("/manage")],)).fetchone()[0]
                    return "" if n else f"no open {plan[:-len('/manage')]} position"
                n = _tc.execute("SELECT COUNT(*) FROM trades WHERE status='OPEN' AND (is_condor_leg=1 OR "
                                "COALESCE(credit_received, 0) > 0)").fetchone()[0]
                return "" if n else "no open credit position"
            finally:
                _tc.close()
        except Exception:                                       # noqa: BLE001
            return ""
    for plan, ts, tick, state, gate, verdict, watching in hb:
        seen[plan] = True
        if plan in _dormant:
            continue
        age = now_ts - (ts or 0)
        w = (watching or "").strip()
        if age > STALE_S and _idle_condition(plan):
            # r303 (PSTATE.1) — a condition-gated plan with nothing to manage writes no heartbeat by
            # ruling; its old row is not STALE. It is STALE only while a position it manages is open.
            quiet.append((plan, "IDLE", f"nothing to manage - {_idle_condition(plan)}", _et(ts)))
        elif age > STALE_S:
            broken.append((plan, f"STALE — last heartbeat {_et(ts)} ET "
                                 f"({age/60:.0f}m ago, tick #{tick})", w))
        elif state == "NO PLAN":
            broken.append((plan, f"NO PLAN — asked at {_et(ts)} ET and wrote nothing", w))
        elif state == "EVALUATING":
            live.append((plan, verdict or "", w, _et(ts)))
        else:
            quiet.append((plan, _LABEL.get(gate, "HELD"), w, _et(ts)))

    if live:
        print("  ── READING THE FEED ──")
        for plan, verdict, w, t in live:
            print(f"    {plan:<24s} {(verdict or 'EVALUATING'):<8s} {t} ET")
            for line in _wrap(w, 84):
                print(f"        {line}")
    else:
        print("  ── READING THE FEED ──")
        print("    none this tick")

    if quiet:
        print("  ── NOT EVALUATING (by design) ──")
        for plan, why, w, t in quiet:
            first = (w.split(":", 1)[1].strip() if ":" in w else w)[:64]
            print(f"    {plan:<24s} {why:<14s} {t} ET  {first}")

    # ⚠️ THE ROSTER IS THE ADMISSION TABLE, NOT THE HEARTBEAT. A plan that was
    # never CONSTRUCTED cannot heartbeat, so asking the heartbeat who exists
    # would hide exactly the failure this section is here to surface.
    try:
        from execution.position_manager import rules as _rules
        expected = set(_rules().keys())
    except Exception:                                           # noqa: BLE001
        expected = set()
    if _sdoc:
        _when = datetime.fromtimestamp(float(_sdoc.get("written_epoch") or 0), ET).strftime("%m-%d %H:%M")
        print(f"  ── PLAN STATES (bot start {_when} ET) ──")
        print(f"    DORMANT (switched off, writes nothing): {', '.join(_dormant) or 'none'}")
        print(f"    LOG ONLY (recorded, never traded):      {', '.join(_logonly) or 'none'}")
    else:
        print("  ── PLAN STATES ──")
        print("    data/plan_states.json not found - a dormant plan cannot be told from a broken one")
    missing = sorted(e for e in expected if e not in seen and e not in _dormant)
    for m in missing:
        broken.append((m, "NOT RUNNING — in the admission table, never "
                          "heartbeat today", ""))

    if broken:
        print("  ── PROBLEMS ──")
        for plan, why, w in broken:
            print(f"    !! {plan:<22s} {why}")
            if w:
                for line in _wrap(w, 84)[:2]:
                    print(f"        last said: {line}")
    print()


def _wrap(text: str, width: int):
    words, out, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            out.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out[:6] + ([f"… ({len(out) - 6} more lines)"] if len(out) > 6 else [])


def show_plans(dc):
    """Intent — including the plans that never became trades.

    🔴 A PLAN CAN PRODUCE NO TRADE AT ALL, and that is the population worth
    mining: an unfired plan still has a knowable outcome, so scoring it later
    is a free backtest on live data. It is also how the trigger itself gets
    measured — if unfired plans would have won at the same rate as fired ones,
    the trigger filters noise; if better, it costs money.
    """
    sep("═")
    print("  PLANS  (intent — fired, expired, and never triggered)")
    sep("═")
    # 🔴 r210 (chunk B) — TODAY ONLY, ONE LINE PER PLAN. Operator: "keep, but
    # I only want TODAY's Plans." The same 09:30 cut as DECISIONS and GATES.
    # ⚠️ THE DATE LEAVES THE ROW WITH THE YESTERDAYS. Every plan is now from
    # today, so "09-01" on every line is a column repeating one value —
    # r145's rule, applied where it was not.
    rows = _q(dc, "SELECT strategy, state, terminal_reason, created_ts,"
                  " closed_ts, short_strike, trigger_price, trade_ids"
                  " FROM plan_ledger WHERE symbol=? AND created_ts >= ?"
                  " ORDER BY created_ts DESC LIMIT 10",
              (INSTRUMENT, session_start_epoch()))
    if rows is None:
        print("  (plan_ledger not present on this box)")
        print(); return
    if not rows:
        print("  No plans today.")
        print(); return
    for strat, state, term, cts, clts, ss, tp, tids in rows:
        t = datetime.fromtimestamp(cts, ET).strftime("%H:%M")
        at = ss or tp
        atx = f" @{at:.2f}" if at else ""
        # ⚠️ WIPED_BY_RESTART IS ITS OWN CATEGORY, not folded into CANCELLED —
        # it is the countable cost of deploying mid-session — so it keeps a
        # mark even at this width. ASCII: the fleet terminal renders the emoji
        # as a run of question marks over SSH (r77).
        flag = "!" if term == "WIPED_BY_RESTART" else " "
        live = " LIVE" if not clts else ""
        traded = f" x{len(__import__('json').loads(tids))}" if tids else ""
        tm = f"  {str(term)[:18]}" if term else ""
        print(f"  {flag}{t} {abbr_strategy(strat):<4} {str(state)[:11]:<11}"
              f"{atx}{traded}{live}{tm}")
    print()


def show_market(dc):
    """Levels, forks and the second-order surface — the market picture."""
    sep("═")
    print("  MARKET")
    sep("═")

    # 🔴 r209 (chunk A) — LIVE LEVELS REMOVED. Operator: "Market: Live Levels —
    # don't care. Take it out." Eight rows of touch counts on every box report,
    # and nothing in the operator's workflow reads them.
    # ⚠️ THE LEDGER IS UNTOUCHED AND STILL WRITTEN. `level_ledger` is a
    # LIFECYCLE table — retention_purge excludes it in code precisely because a
    # recomputation cannot rebuild a biography (r81) — and the sweep and fork
    # paths both read it live. This deletes a VIEW, not a collector.
    fk = _q(dc, "SELECT interval, built, reject_reason, containment, span_bars"
                " FROM fork_series WHERE symbol=? ORDER BY ts_epoch DESC LIMIT 2",
            (INSTRUMENT,))
    if fk:
        print()
        print("  Pitchfork:")
        for iv, built, rr, cont, span in fk:
            if built:
                print(f"    {iv}: BUILT  containment={cont:.2f} span={span} bars")
            else:
                # ⚠️ THE REASON, NOT JUST "absent". Six distinct causes used to
                # collapse into one message, which is why a diagnosis took two
                # wrong turns.
                print(f"    {iv}: no fork — {rr}")

    sf = _q(dc, "SELECT ROUND(AVG(charm),4), ROUND(AVG(vanna),4),"
                " ROUND(MAX(gex)/1e6,2), COUNT(*) FROM surface_series"
                " WHERE symbol=? AND ts_epoch > ?",
            (INSTRUMENT, datetime.now(ET).timestamp() - 3600))
    if sf and sf[0][3]:
        c, v, g, n = sf[0]
        print()
        print(f"  Surface (1h): charm={c}  vanna={v}  GEX={g}M  ({n} samples)")
    print()


def main():
    # r170 — `--decisions` renders ONLY the snapshot (header + enter-on /
    # exit-on). This is the fleet reader's entry point: devtools calls
    # `python query.py --decisions` on every box, so there is exactly one
    # formatter. The full dashboard (trade log, all-time performance, market)
    # stays the default and is unchanged.
    if "--decisions" in sys.argv:
        print()
        show_header()
        dc = _derived()
        if dc is None:
            print("  derived store not found on this box.")
            return
        show_decisions(dc)
        dc.close()
        return
    conn = connect()
    print()
    show_header()
    # ── TRADES: what happened ────────────────────────────────────────────
    # 🔴 r209 (chunk A) — FOUR SECTIONS DELETED, on the operator's reading of
    # what this dashboard is FOR. It is the per-SYMBOL box report, and an
    # all-time or by-strategy rollup on one box is a slice nobody acts on:
    # "I don't need a per symbol snapshot of that", "that's just trivia in my
    # opinion, useless by itself", "we don't have grades", "irrelevant".
    # ⚠️ THE CROSS-FLEET VERSIONS OF THESE ALREADY EXIST AND ARE THE RIGHT
    # HOME: day_trader_pro's trade breakdown (r187) groups by strategy, setup
    # type, exit reason, symbol, hour and weekday across every box, with an
    # ENGINE EPOCH floor so pre-2026-08-25 trades cannot contaminate it. This
    # file had no epoch filter at all, so its ALL-TIME numbers pooled the old
    # engines with the new ones — 109 trades reaching back past the v4 split.
    # Removing them removes a number that was quietly wrong, not just noisy.
    # ⚠️ BY SETUP GRADE was structurally empty: r152 deleted the scorer and
    # every write path hardcodes UNGRADED, so the section had one bucket.
    show_open_position(conn)
    # 🔴 r210 (chunk B) — LAST 10 CLOSED IS GONE, MERGED INTO TODAY'S TRADES.
    # Operator asked to keep both AND to scope both to today, which makes them
    # the same table: one filtered by date, one by a LIMIT that happened to
    # land on the same rows. Two sections rendering one answer is the
    # two-documents-one-job rot (§35) in a report.
    show_today(conn)
    show_circuit_breakers(conn)

    # ── MARKET: what the tape was doing, and why nothing fired ───────────
    # ⚠️ SEPARATE CONNECTION, SEPARATE FAILURE. The derived store is a
    # different database; if it will not open, the trades dashboard above is
    # unaffected and this half says so.
    dc = _derived()
    if dc is None:
        sep("═")
        print("  MARKET DATA — derived store not found on this box.")
        print("  (expected at ~/options-trader/data/derived_store.db)")
        sep("═")
    else:
        # 🔴 r209 (chunk A) — CHARACTER MOVES TO status.py. Operator:
        # "Character — keep, but not in query.py; it belongs in status, below
        # the pin line." It is a STATE, which is what status.py is for; this
        # file is the trade log.
        # ⚠️ IT IS NOT RENDERED ANYWHERE UNTIL CHUNK C LANDS, and that costs
        # nothing today: r85 set BANDS_SET=False because the old bands were
        # calibrated against a quantity that turned out to be the wrong one, so
        # the section has printed "No character recorded yet today" on every
        # box since. Stated rather than discovered.
        show_decisions(dc)
        show_gates(dc)
        show_plans(dc)
        show_market(dc)
        dc.close()

    sep("═")
    print()
    conn.close()


if __name__ == "__main__":
    main()
