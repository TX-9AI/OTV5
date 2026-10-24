#!/usr/bin/env python3
"""tools/agent_verdict.py — v1.0
THE AGENT'S READ OF THE TAPE AFTER A LOSS, TIMESTAMPED, AND READ BY NOTHING.

v1.0 (2026-09-29) — OTV4TEST r171 (AGT.2). The operator, 2026-09-29: *"As far
      as the Trading monitor, wire it as observe and comment only. And just put
      your read on whether you'd make a recommendation not to trade a certain
      way until the situation resolves. Just put down whether you would forbid
      long entries, short entries, or both. That way we can timestamp your
      decision with whatever followed on the tape to see if it would've
      helped."* And before it: *"we would have to see if you can demonstrate
      an edge. For example ... identifying chop."*

🔴 OBSERVE ONLY, AND PINNED SO. Nothing in the bot, a plan, a strategy or a
gate reads AGENT_VERDICTS (check_agent_watch V4 greps every shipped package
for the file name and this module's name). A verdict that could refuse a trade
before it has been scored against the tape would be §31's failure: a number
never tested against P&L deciding something.

A VERDICT IS: which directions the agent WOULD forbid (long / short / both /
none), what would have to happen for the situation to count as resolved, and
why — stamped with the wall clock, the underlying's last 1m close (read-only
from the feed store), and the seconds since the loss that prompted it, so a
later scoring can line it up against the tape that followed.

Usage:
    python3 tools/agent_verdict.py --trade <trade_id> --forbid short \\
        --until "a 5m close back above 739.62" --note "stacked FVG retrace..."
    python3 tools/agent_verdict.py --list            # today's verdicts
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HOME = os.path.expanduser("~")
VERDICTS = os.environ.get("OT_AGENT_VERDICTS") or os.path.join(_root, "data", "AGENT_VERDICTS.jsonl")
TRADES_DB = os.environ.get("OT_TRADES_DB") or os.path.join(_HOME, "options-trader", "trades.db")
FEED_DB = os.environ.get("OT_FEED_DB") or os.path.join(_HOME, "options-trader", "data", "feed_store.db")
FORBID = ("long", "short", "both", "none")

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:                                               # noqa: BLE001
    _ET = timezone(timedelta(hours=-4))


def _ro(path):
    return sqlite3.connect("file:%s?mode=ro" % path, uri=True, timeout=5)


def trade(tid: str):
    """-> the prompting trade's row (symbol, strategy, direction, pnl, exit), or None."""
    if not tid or not os.path.exists(TRADES_DB):
        return None
    con = _ro(TRADES_DB)
    con.row_factory = sqlite3.Row
    try:
        r = con.execute("SELECT trade_id, symbol, strategy, direction, pnl_usd, exit_time"
                        " FROM trades WHERE trade_id = ? OR trade_id LIKE ?",
                        (tid, tid + "%")).fetchall()
    finally:
        con.close()
    return dict(r[0]) if len(r) == 1 else None


def last_close(symbol: str):
    """-> (bar epoch s, close) of the newest 1m bar, read-only, or (None, None)."""
    if not os.path.exists(FEED_DB):
        return None, None
    con = _ro(FEED_DB)
    try:
        r = con.execute("SELECT ts_epoch_ms, close FROM candles WHERE symbol = ? AND interval = '1m'"
                        " ORDER BY ts_epoch_ms DESC LIMIT 1", (symbol,)).fetchone()
    finally:
        con.close()
    return (r[0] / 1000.0, r[1]) if r else (None, None)


def record(forbid: str, note: str, until: str = "", trade_id: str = "", event: str = "",
           symbol: str = "", now: float | None = None) -> dict:
    if forbid not in FORBID:
        raise ValueError("forbid must be one of %s" % (FORBID,))
    if not note.strip():
        raise ValueError("a verdict carries its reasoning (--note)")
    now = time.time() if now is None else now
    t = trade(trade_id) if trade_id else None
    if trade_id and t is None:
        raise ValueError("trade %r not found (or ambiguous) in %s" % (trade_id, TRADES_DB))
    sym = symbol or (t or {}).get("symbol") or os.environ.get("OT_INSTRUMENT", "")
    bar_ts, px = last_close(sym) if sym else (None, None)
    v = {"ts_utc": datetime.fromtimestamp(now, timezone.utc).isoformat(),
         "ts_et": datetime.fromtimestamp(now, _ET).isoformat(),
         "forbid": forbid, "until": until.strip(), "note": note.strip(),
         "event": event or None, "trade_id": (t or {}).get("trade_id"),
         "symbol": sym or None, "px_last_1m": px,
         "bar_age_s": round(now - bar_ts, 1) if bar_ts else None}
    if t:
        v.update({"loss_strategy": t["strategy"], "loss_direction": t["direction"],
                  "loss_pnl": t["pnl_usd"]})
        xt = t.get("exit_time")
        try:
            v["s_since_loss"] = round(now - datetime.fromisoformat(xt).timestamp(), 1)
        except Exception:                                       # noqa: BLE001
            pass
    os.makedirs(os.path.dirname(VERDICTS), exist_ok=True)
    with open(VERDICTS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(v) + "\n")
    return v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="record the agent's observe-only verdict (r171)")
    ap.add_argument("--forbid", choices=FORBID)
    ap.add_argument("--note", default="")
    ap.add_argument("--until", default="", help="what would count as the situation resolved")
    ap.add_argument("--trade", default="", help="the losing trade that prompted it (id or prefix)")
    ap.add_argument("--event", default="", help="the agent_watch event id")
    ap.add_argument("--symbol", default="")
    ap.add_argument("--list", action="store_true", help="today's verdicts (ET)")
    a = ap.parse_args(argv)
    if a.list:
        today = datetime.now(_ET).date().isoformat()
        try:
            with open(VERDICTS, encoding="utf-8") as fh:
                rows = [json.loads(l) for l in fh if l.strip()]
        except OSError:
            rows = []
        for v in rows:
            if v["ts_et"][:10] == today:
                print("%s forbid=%-5s %s | until: %s"
                      % (v["ts_et"][11:16], v["forbid"], v["note"][:60], v["until"][:40]))
        return 0
    if not a.forbid:
        ap.error("--forbid is required (or --list)")
    try:
        v = record(a.forbid, a.note, a.until, a.trade, a.event, a.symbol)
    except ValueError as exc:
        print("verdict NOT recorded: %s" % exc, file=sys.stderr)
        return 2
    print("verdict recorded %s forbid=%s px=%s (%ss after the loss)"
          % (v["ts_et"][11:19], v["forbid"], v["px_last_1m"], v.get("s_since_loss")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
