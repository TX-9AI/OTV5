#!/usr/bin/env python3
"""
tools/manifold_status.py  v4.0

Every port, its home, its depth and its freshness — on THIS box.

v4.0  2026-08-22  Built with the manifold. See docs/FEED_MANIFOLD.md.

WHY IT EXISTS. On 2026-08-21 the intraday tape was dead from 09:30 and nothing
said so. The operator found it by hand at 09:31; the single blind alert then
went quiet because the latch pages once per outage, and the fleet traded zero.
**"Is the fire hose connected" has to be answerable in five seconds.**

⚠️ IT READS THE STORE, NOT THE CODE. A subscription list proves what we ASKED
for. This proves what ARRIVED. Every failure this week lived in the gap between
those two.

⚠️ ABSENCE IS REPORTED AS ABSENCE. A port with no rows prints MISSING, not 0 —
a stream that never started and a stream that measured nothing are different
facts, and conflating them is the single most expensive habit in this repo's
history.

Run:  cd ~/options-trader && python3 tools/manifold_status.py
      python3 tools/manifold_status.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Freshness budgets in seconds. A tenor is STALE if its newest row is older
# than this DURING RTH. Generous by design: this is a "did the pipe break"
# instrument, not a latency monitor.
BUDGET = {"1m": 180, "5m": 900, "15m": 2700, "1h": 9000, "1d": 200000}


def _db():
    return os.path.expanduser("~/options-trader/data/feed_store.db")


def _q(con, sql, args=()):
    try:
        return con.execute(sql, args).fetchall()
    except sqlite3.Error:
        return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    path = _db()
    if not os.path.exists(path):
        print(f"MISSING: no feed store at {path}")
        return 1
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    now = time.time()
    report, problems = {}, []

    # ── candle ports: every (store_symbol, interval) that exists ─────────
    rows = _q(con, "SELECT symbol, interval, COUNT(*), MAX(ts_epoch_ms)"
                   " FROM candles GROUP BY symbol, interval")
    cand = {}
    for sym, iv, n, newest in rows:
        age = now - (newest or 0) / 1000.0
        cand[f"{sym}/{iv}"] = {"rows": n, "age_s": round(age),
                               "stale": age > BUDGET.get(iv, 3600)}
    report["candles"] = cand

    # ── series ports: the full-fidelity homes ───────────────────────────
    # MANIFOLD PART 2 — the five event types added 2026-08-22 are checked the
    # same way. ⚠️ MISSING IS REPORTED, NOT INFERRED: a port with no rows may
    # mean the entitlement does not cover it, and that is a fact worth seeing
    # rather than a silence to interpret.
    for tbl in ("greeks_series", "quote_series", "prints", "last_trade",
                "session_summary", "underlying_series", "theo_series"):
        r = _q(con, f"SELECT COUNT(*), MAX(ts_epoch) FROM {tbl}")
        if not r or r[0][0] is None or r[0][0] == 0:
            report[tbl] = "MISSING"
            problems.append(f"{tbl}: no rows — the series home is not filling")
        else:
            n, newest = r[0]
            report[tbl] = {"rows": n, "age_s": round(now - (newest or 0))}

    # ── current-value port ──────────────────────────────────────────────
    r = _q(con, "SELECT COUNT(*), MAX(updated_epoch) FROM chain_marks")
    if r and r[0][0]:
        report["chain_marks"] = {"rows": r[0][0],
                                 "age_s": round(now - (r[0][1] or 0))}
    else:
        report["chain_marks"] = "MISSING"
        problems.append("chain_marks: empty — no live greeks/quotes")

    # ── heartbeat ───────────────────────────────────────────────────────
    r = _q(con, "SELECT MAX(last_write_epoch) FROM feed_meta")
    hb = (r[0][0] if r and r[0][0] else 0)
    report["feed_heartbeat_age_s"] = round(now - hb) if hb else None
    if not hb or now - hb > 300:
        problems.append("feed heartbeat stale — the writer is not writing")

    if args.json:
        print(json.dumps({"report": report, "problems": problems}, indent=2))
        return 1 if problems else 0

    print("=" * 68)
    print("MANIFOLD STATUS — what actually ARRIVED in this box's store")
    print("=" * 68)
    if not cand:
        print("  MISSING: no candle rows at all")
        problems.append("no candles")
    for k in sorted(cand):
        d = cand[k]
        flag = "STALE" if d["stale"] else "ok"
        print(f"  {k:16} rows={d['rows']:<7} age={d['age_s']:<7}s  {flag}")
        if d["stale"]:
            problems.append(f"{k}: stale by {d['age_s']}s")
    for k in ("greeks_series", "quote_series", "prints", "last_trade",
              "session_summary", "underlying_series", "theo_series",
              "chain_marks"):
        v = report[k]
        print(f"  {k:16} {v if v == 'MISSING' else str(v)}")
    print(f"  {'heartbeat':16} age={report['feed_heartbeat_age_s']}s")
    print("=" * 68)
    if problems:
        print(f"  {len(problems)} problem(s):")
        for p in problems:
            print(f"    {p}")
        return 1
    print("  every port fed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
