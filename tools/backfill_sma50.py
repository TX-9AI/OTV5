#!/usr/bin/env python3
"""
tools/backfill_sma50.py  v1.0
v1.0  2026-09-30  OTV4TEST r183 (SMA.1) — new: backfills the entry snapshot's "sma50_5m" key onto past trades.

Adds the entry snapshot's "sma50_5m" key (r183, SMA.1) to trades that were
entered before r183 recorded it. The operator, 2026-09-30: "yes" to backfilling
the past trades.

It computes with the SAME function the bot now calls at entry
(analysis.entry_snapshot.sma50_context), from the feed store's 1m bars at each
trade's own entry time and underlying price, so a backfilled row and a live row
are the same measurement. It adds ONE key to each row's entry_snapshot JSON and
touches nothing else in the row; every other key is preserved, and the row is
marked "sma50_backfilled". A row that already carries the key is left alone, so
a second run changes nothing.

DRY RUN BY DEFAULT: it prints what it would write. --apply writes. It reads
config.DB_PATH (OT_TRADES_DB overrides) and the feed store (OT_FEED_DB).

Run:  venv/bin/python tools/backfill_sma50.py [--apply]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


def _epoch(entry_time: str) -> float:
    t = dt.datetime.fromisoformat(str(entry_time).replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.timestamp()


def run(apply: bool, db_path: str, feed_db: str, symbol: str, stamp: str) -> dict:
    from analysis.entry_snapshot import sma50_context
    conn = sqlite3.connect(db_path, timeout=10)
    try:
        rows = conn.execute("SELECT trade_id, direction, entry_time, underlying_entry, entry_snapshot "
                            "FROM trades WHERE entry_time IS NOT NULL ORDER BY entry_time").fetchall()
        n = {"rows": len(rows), "already": 0, "written": 0, "would_write": 0, "no_price": 0, "sma_none": 0}
        for tid, d, et, ue, snap in rows:
            try:
                payload = json.loads(snap) if snap else {}
                if not isinstance(payload, dict):
                    payload = {"prior": payload}
            except ValueError:
                payload = {"prior_unparsed": str(snap)[:200]}
            if "sma50_5m" in payload:
                n["already"] += 1
                continue
            price = float(ue or payload.get("px") or 0.0)
            if not price:
                n["no_price"] += 1
            ctx = sma50_context(_epoch(et), price, (d or "").lower(), db_path=feed_db, symbol=symbol)
            if not (ctx.get("rth") or {}).get("sma"):
                n["sma_none"] += 1
            payload["sma50_5m"] = ctx
            payload["sma50_backfilled"] = stamp
            if apply:
                conn.execute("UPDATE trades SET entry_snapshot=? WHERE trade_id=?",
                             (json.dumps(payload, separators=(",", ":")), tid))
                n["written"] += 1
            else:
                n["would_write"] += 1
        if apply:
            conn.commit()
        return n
    finally:
        conn.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--apply", action="store_true", help="write (default: dry run)")
    a = ap.parse_args(argv)
    import config
    feed = os.path.expanduser(os.environ.get("OT_FEED_DB", "").strip()
                              or os.path.join(_root, "data", "feed_store.db"))
    sym = str(getattr(config, "INSTRUMENT", "") or "")
    if not sym:
        print("refused: OT_INSTRUMENT is not set", file=sys.stderr)
        return 2
    n = run(a.apply, config.DB_PATH, feed, sym, dt.datetime.now(dt.timezone.utc).isoformat())
    print(("APPLIED" if a.apply else "DRY RUN") + f" on {config.DB_PATH}: " + json.dumps(n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
