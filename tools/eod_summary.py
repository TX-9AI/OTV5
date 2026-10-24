"""
tools/eod_summary.py  v4.5
v4.5  2026-10-03  OTV4TEST r191 (AUD.2) — THE DAY FILTER READS THE REAL EASTERN OFFSET. Both queries used a
      literal '-4 hours' (EDT) and the fallback clock a fixed UTC-4; query.py fixed the same class at r210 and
      this file kept it. et_offset_sql() gives "-4 hours" in summer and "-5 hours" from 2026-11-01, from the tz
      database, and the fallback clock tries zoneinfo before the fixed offset.
v4.4 2026-09-26  OTV4TEST r146 — the instrument comes from box_instrument() - its timer unit carries no OT_INSTRUMENT, so it was QQQ by default on every box.
v4.3  2026-09-17  OTV4TEST r34 — `from tools.query import …` becomes `from query
      import …`: query.py moved back to the repo root. ⚠️ THIS IS THE ONE THAT
      WOULD HAVE FAILED SILENTLY. The import sits in a try/except whose fallback
      re-derives DB_PATH, INSTRUMENT and the ET date by hand — so a stale import
      would not raise at 15:50, it would quietly report against a DIFFERENT
      resolved DB path than the dashboard does.
v4.2
v4.2  2026-09-11  OTV4TEST r14 — moved from the repo root to tools/ (root cleanup); no behaviour change.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

End-of-day per-box summary.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

#!/usr/bin/env python3
# options_trader_v3/eod_summary.py — v3.0
# repo-wide v3.0 bump: Yahoo-Finance purge & data stream
#         mapping optimization (single shared TastyTrade candle feed). No
#         logic change in this file.
"""
"""
End-of-day P&L writer. Runs on EACH bot box at ~15:50 ET (own systemd timer),
AFTER the 15:45 flatten. Writes a small local JSON that the control server
SSH-pulls at 15:55 to build the unified fleet P&L message.

It intentionally does NOT send its own Telegram in the normal flow (that would
be the six-message flood we're avoiding). Pass --send to Telegram this box's
summary too — handy for testing one box in isolation.

Numbers mirror query.py's TODAY view exactly (same date filter, same pnl_usd),
so this file always agrees with your dashboard.

Decoupled from the trading loop on purpose: even if the bot process died
mid-session, the trades it logged are in the DB, so this still reports the
day's realized P&L up to the failure and flags any orphaned open position.

CLI:
    python3 eod_summary.py            # compute + write ~/eod/pnl_today.json
    python3 eod_summary.py --send      # also Telegram this box's summary
    python3 eod_summary.py --print      # write + echo the JSON to stdout
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

INSTALL_DIR = os.path.expanduser("~/options-trader")
sys.path.insert(0, INSTALL_DIR)

# Reuse query.py's resolved DB path + live instrument/mode so this matches the
# dashboard. Fall back gracefully if imported outside the install dir.
try:
    from query import DB_PATH, INSTRUMENT, PAPER_TRADING, now_et   # r34: back at the root
except Exception:  # noqa: BLE001
    # Fallback with NO tzdata dependency (fresh boxes may lack zoneinfo data).
    # ET date via fixed EDT offset — matches the '-4 hours' SQL date filter,
    # and the date is what matters for the daily rollup at 15:50.
    from datetime import timedelta
    DB_PATH = os.path.join(INSTALL_DIR, "trades.db")
    from utils.instrument import box_instrument     # r146: never QQQ by default
    INSTRUMENT = box_instrument()
    PAPER_TRADING = os.environ.get("OT_PAPER_TRADING", "True") != "False"

    def now_et():
        try:                                     # r191: the tz database first
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo("America/New_York"))
        except Exception:                                       # noqa: BLE001
            return datetime.now(timezone.utc) - timedelta(hours=4)



def et_offset_sql(now=None) -> str:
    """The Eastern UTC offset as a sqlite modifier: "-4 hours" (EDT) or "-5 hours" (EST).
    r191: read from the clock's own utcoffset (query.py r210's rule); a clock with no
    offset (the no-tzdata fallback) keeps the old -4."""
    try:
        off = (now or now_et()).utcoffset()
        if off is None:
            return "-4 hours"
        return f"{int(off.total_seconds() // 3600)} hours"
    except Exception:                                           # noqa: BLE001
        return "-4 hours"


OUT_DIR = os.path.expanduser("~/eod")
OUT_PATH = os.path.join(OUT_DIR, "pnl_today.json")
TRADES_PATH = os.path.join(OUT_DIR, "trades_today.json")


def _connect():
    # Do NOT sys.exit on a missing DB — we still want to emit a valid (empty)
    # file so the control server sees "0 trades" rather than "missing".
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def compute_summary():
    today = now_et().strftime("%Y-%m-%d")
    summary = {
        "schema": 1,
        "date_et": today,
        "instrument": INSTRUMENT,
        "paper": bool(PAPER_TRADING),
        "n_trades": 0, "wins": 0, "losses": 0,
        "gross_pnl": 0.0, "fees": 0.0, "fees_tracked": False,
        "net_pnl": 0.0, "best": 0.0, "worst": 0.0,
        "orphans": 0,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "",
    }

    conn = _connect()
    if conn is None:
        summary["note"] = "trades.db not found"
        return summary

    # Detect an optional fees column (you have fee-logging on the roadmap).
    cols = {r[1] for r in conn.execute("PRAGMA table_info(trades)").fetchall()}
    has_fees = "fees" in cols
    fee_expr = "COALESCE(fees, 0)" if has_fees else "0"

    # Mirror query.py show_today: closed trades whose ET entry date is today.
    # r191: the offset is the real Eastern one (et_offset_sql), as query.py
    # has read it since r210 - -4 in summer, -5 from November.
    rows = conn.execute(
        f"""SELECT pnl_usd, {fee_expr} AS fee
            FROM trades
            WHERE status='closed'
              AND date(datetime(entry_time, ?)) = ?""",
        (et_offset_sql(), today),
    ).fetchall()

    pnls = [(r["pnl_usd"] or 0.0) for r in rows]
    fees = sum((r["fee"] or 0.0) for r in rows)

    if pnls:
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        net = sum(pnls)
        summary.update({
            "n_trades": len(pnls),
            "wins": len(wins),
            "losses": len(losses),
            "net_pnl": round(net, 2),
            "gross_pnl": round(net + fees, 2) if has_fees else round(net, 2),
            "fees": round(fees, 2),
            "fees_tracked": has_fees,
            "best": round(max(pnls), 2),
            "worst": round(min(pnls), 2),
        })

    # Orphan check: any position still open after the 15:45 flatten.
    orphan_row = conn.execute(
        "SELECT COUNT(*) AS c FROM trades WHERE status='open'"
    ).fetchone()
    summary["orphans"] = int(orphan_row["c"] or 0)
    if summary["orphans"]:
        summary["note"] = (summary["note"] + " | " if summary["note"] else "") + \
            f"{summary['orphans']} OPEN position(s) at EOD"

    conn.close()
    return summary


def write_summary(summary):
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(summary, fh, indent=2)
    os.replace(tmp, OUT_PATH)  # atomic — control never reads a half-written file
    return OUT_PATH


def dump_trades():
    """
    Full detail for today's closed trades — every column, so the control
    server's harvest can do deep post-mortem (setup, grade, exit_reason,
    """
    today = now_et().strftime("%Y-%m-%d")
    payload = {
        "schema": 1,
        "date_et": today,
        "instrument": INSTRUMENT,
        "paper": bool(PAPER_TRADING),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "trades": [],
        "open_positions": [],
    }
    conn = _connect()
    if conn is not None:
        # SELECT * so whatever context columns exist are all captured.
        closed = conn.execute(
            """SELECT * FROM trades
               WHERE status='closed'
                 AND date(datetime(entry_time, ?)) = ?
               ORDER BY entry_time""",
            (et_offset_sql(), today),
        ).fetchall()
        payload["trades"] = [dict(r) for r in closed]
        # Any still-open positions (orphans) — useful to see what was left.
        openp = conn.execute(
            "SELECT * FROM trades WHERE status='open'"
        ).fetchall()
        payload["open_positions"] = [dict(r) for r in openp]
        conn.close()

    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = TRADES_PATH + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(payload, fh, indent=2, default=str)
    os.replace(tmp, TRADES_PATH)
    return payload["trades"]


def main(argv):
    summary = compute_summary()
    path = write_summary(summary)
    trades = dump_trades()
    print(f"[eod_summary] wrote {path}: "
          f"{summary['instrument']} net "
          f"{summary['net_pnl']:+.2f} over {summary['n_trades']} trades, "
          f"orphans={summary['orphans']}")
    print(f"[eod_summary] wrote {TRADES_PATH}: {len(trades)} full trade rows")

    if "--print" in argv:
        print(json.dumps(summary, indent=2))

    if "--send" in argv:
        try:
            sys.path.insert(0, INSTALL_DIR)
            from notifications.alert_manager import get_alert_manager
            get_alert_manager().send_daily_summary(summary)
            print("[eod_summary] Telegram summary sent.")
        except Exception as exc:  # noqa: BLE001
            print(f"[eod_summary] could not send Telegram: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
