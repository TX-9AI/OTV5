#!/usr/bin/env python3
"""
tools/seed_candles_from_warehouse.py  v1.1
v1.1  2026-10-04  OTV4TEST r237 (SEED.2) — A BAR PUSHED BEFORE IT CLOSED IS REFUSED ("partial"). v1.0 kept the
      latest push per bar and never asked whether that push came AFTER the bar's end. Mainline's pusher
      ships the forming bar and never re-sends it (otv4 s3_push.push_candles advances its mark over the
      newest row sent; 1-REPORTER confirmed in code, fix CNDL.1 staged there), so in raw/candles EVERY
      5m/15m/1h bar is its first ~30 s and ~1 in 5 1m bars are too (measured QQQ 09-17/10-01, SPX 10-01).
      v1.0 wrote 4,407 such bars into SPX-TEST's live feed store (found by SPX-TEST's agent; repaired on
      the operator's yes). Now: the winning push's pushed_at_utc must be >= ts + the interval's length,
      or the bar is rejected as "partial"; an interval with no known length, or a push time that cannot
      be read, is rejected too (fail closed). Until mainline's history is fixed this seeds complete 1m
      bars only - say so, never a pass. Gate: tests/check_seed_candles.py C11/C12, born red on v1.0.
v1.0  2026-10-04  OTV4TEST r233 (SEED.1) — A NEW INSTRUMENT'S CANDLE HISTORY IS SEEDED FROM THE
      WAREHOUSE, ONLY ADDING ROWS. The operator, 2026-10-04, on SPX-TEST's first days: "Do we want him
      to backfill his feed?" SPX-TEST's feed store has 43 days of hourly SPX bars and NO 1m - the feed's
      own backfill reaches one day of 1m (candle_feed.BACKFILL_DAYS, DXFeed history is same-evening), and
      the weekend's broker 1m bars were zero-price poison. The level book judges a breach on 1m, so the
      book is thin and check_level_tape T2 is red until the tape exists. Mainline's SPX box has pushed
      real 1m/5m/15m/1h candles to raw/candles for weeks (measured 2026-10-04: 79 SPX 1m objects on
      10-02, real prices, volume 0 - an index has no volume, so volume is NOT a sanity rule here).

      WHAT IT DOES. Reads raw/candles for THE BOX'S instrument (utils.instrument.box_instrument; a
      --symbol that disagrees is refused) through tests/warehouse_source.py - the one reader (WA §36a,
      §38.1) - keeping, per (interval, bar), the row from the LATEST pushed envelope (a bar is re-pushed
      as it builds; latest wins, as in every other warehouse reader). Depth per interval is
      warehouse/retention_purge.RETENTION_DAYS, imported, never copied: an older row would be deleted
      by the next nightly purge. Each bar must pass the feed's own poison rule (FeedStore.purge_poison:
      every price > 0, TS_MS_MIN <= ts <= now + 2 days). Then INSERT OR IGNORE into `candles` - a row
      the store already holds is NEVER changed, the live feed's bars always win. feed_meta is NOT
      touched: its last_write_epoch is the feed's freshness signal, and a seed of old bars is not fresh.

      DRY RUN BY DEFAULT (the store is opened read-only). --apply writes one transaction per interval
      and prints the before/after row counts.

      FAILS LOUDLY, non-zero and named: no instrument; a disagreeing --symbol; the store missing or with
      no candles table; AWS credentials not resolving (a boolean - nothing is printed, WA §38.7); the
      warehouse unreadable; zero objects listed, or none for the symbol.

Run:   python3 tools/seed_candles_from_warehouse.py                      (dry run, full depth)
       python3 tools/seed_candles_from_warehouse.py --date 2026-10-02    (one date)
       python3 tools/seed_candles_from_warehouse.py --apply              (WRITES - the operator's yes first)
Gate:  tests/check_seed_candles.py
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

import warehouse_source as ws                                   # noqa: E402  the ONE reader
from utils import instrument as _instr                          # noqa: E402
from utils import paths as _paths                               # noqa: E402
from warehouse.retention_purge import RETENTION_DAYS            # noqa: E402

DEFAULT_INTERVALS = ("1m", "5m", "15m", "1h")
DAY_MS = 86_400_000
# data/candle_feed.py's poison window. Mirrored, not imported: that module pulls in the broker SDK.
# tests/check_seed_candles.py C9 imports both and fails if they ever differ.
TS_MS_MIN = 1_262_304_000_000
TS_MAX_AHEAD_MS = 172_800_000                                   # candle_feed._ts_ms_max: now + 2 days


class Refused(Exception):
    """A named reason not to run. rc 2."""


def _dates(date: str | None, days: int) -> list:
    if date:
        return [ws._valid(date)]
    today = datetime.strptime(ws._et_today(), "%Y-%m-%d").date()
    return [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _creds_resolve() -> bool:
    try:
        import boto3
        return boto3.Session().get_credentials() is not None
    except Exception:                                           # noqa: BLE001
        return False


INTERVAL_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000, "1h": 3_600_000}


def _push_ms(stamp: str):
    from datetime import datetime
    try:
        return int(datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).timestamp() * 1000)
    except (TypeError, ValueError):
        return None


def _verdict(row: dict, cutoff_ms: int, max_ms: int, iv: str = None, stamp: str = None):
    """-> (ts, tuple) or (None, reason). r237: a bar whose winning push precedes its end is "partial"."""
    try:
        ts = int(row["ts_epoch_ms"])
        o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
        v = float(row.get("volume") or 0.0)
    except (KeyError, TypeError, ValueError):
        return None, "malformed"
    if not (TS_MS_MIN <= ts <= max_ms):
        return None, "poison_ts"
    if min(o, h, l, c) <= 0:
        return None, "nonpositive_price"
    if ts < cutoff_ms:
        return None, "beyond_retention"
    if iv is not None:
        span = INTERVAL_MS.get(iv)
        if span is None:
            return None, "unknown_interval"
        pushed = _push_ms(stamp)
        if pushed is None:
            return None, "no_push_time"
        if pushed < ts + span:
            return None, "partial"
    return ts, (o, h, l, c, v)


def collect(sym, intervals, dates, s3, now_ms):
    """Fold the warehouse into {interval: {ts: (stamp, row)}}. -> (best, meta, per_date)."""
    meta = ws.Meta(f"candles {dates[0]}..{dates[-1]} sym={sym}")
    best = {iv: {} for iv in intervals}
    per_date = []
    for d in dates:
        l0, r0 = meta.listed, meta.read
        kept = 0
        for env in ws._envelopes(s3, "candles", [d], meta, symbols={sym}):
            if env.get("symbol") not in (None, sym):
                continue
            stamp = str(env.get("pushed_at_utc") or "")
            rec = env.get("record")
            if not isinstance(rec, list):
                continue
            for r in rec:
                if not isinstance(r, dict) or r.get("symbol", sym) != sym:
                    continue
                iv = r.get("interval")
                if iv not in best:
                    continue
                try:
                    ts = int(r.get("ts_epoch_ms"))
                except (TypeError, ValueError):
                    ts = None
                key = ts if ts is not None else ("?", id(r))
                cur = best[iv].get(key)
                if cur is None or stamp >= cur[0]:
                    if cur is None:
                        kept += 1
                    best[iv][key] = (stamp, r)
        if meta.error:
            break
        per_date.append((d, meta.listed - l0, meta.read - r0, kept))
        print(f"  {d}: {meta.listed - l0} object(s) listed (all symbols), "
              f"{meta.read - r0} read for {sym}, {kept} new bar(s)", flush=True)
    return best, meta, per_date


def _present(conn, sym, iv, tss):
    if not tss:
        return set()
    lo, hi = min(tss), max(tss)
    return {r[0] for r in conn.execute(
        "SELECT ts_epoch_ms FROM candles WHERE symbol=? AND interval=? AND ts_epoch_ms BETWEEN ? AND ?",
        (sym, iv, lo, hi))}


def _count(conn, sym, iv):
    return conn.execute("SELECT COUNT(*) FROM candles WHERE symbol=? AND interval=?",
                        (sym, iv)).fetchone()[0]


def run(argv=None, s3=None, now_ms=None) -> int:
    ap = argparse.ArgumentParser(description="Seed missing candles for this box's instrument "
                                             "from the warehouse (INSERT OR IGNORE).")
    ap.add_argument("--apply", action="store_true", help="WRITE the missing rows (default: dry run)")
    ap.add_argument("--symbol", help="must equal the box's instrument")
    ap.add_argument("--intervals", default=",".join(DEFAULT_INTERVALS))
    ap.add_argument("--date", help="one date (YYYY-MM-DD) instead of the full depth")
    ap.add_argument("--days", type=int, help="fewer calendar days than the retention depth")
    ap.add_argument("--db", help="feed store path (default: utils.paths.feed_db_path())")
    a = ap.parse_args(argv)
    now_ms = int(now_ms if now_ms is not None else time.time() * 1000)
    try:
        box = _instr.box_instrument()
        if box == _instr.UNSET:
            raise Refused("this box's instrument is UNSET (no OT_INSTRUMENT here or in the bot unit)")
        sym = box
        if a.symbol and a.symbol.strip().upper() != box:
            raise Refused(f"--symbol {a.symbol} is not this box's instrument ({box})")
        intervals = [i.strip() for i in a.intervals.split(",") if i.strip()]
        for iv in intervals:
            if not RETENTION_DAYS.get(iv):
                raise Refused(f"interval {iv!r} has no finite depth in RETENTION_DAYS ({RETENTION_DAYS})")
        depth = max(RETENTION_DAYS[iv] for iv in intervals)
        if a.days:
            depth = min(depth, a.days)
        db = a.db or _paths.feed_db_path()
        if not os.path.isfile(db):
            raise Refused(f"feed store not found: {db}")
        ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)
        if not ro.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='candles'").fetchone():
            raise Refused(f"no candles table in {db}")
        if s3 is None:
            if not _creds_resolve():
                raise Refused("AWS credentials do not resolve on this box (checked as a boolean)")
            s3 = ws.client()
    except Refused as exc:
        print(f"REFUSED: {exc}")
        return 2

    dates = _dates(a.date, depth)
    print(f"seed_candles_from_warehouse v1.0 - {sym}, intervals {','.join(intervals)}, "
          f"{len(dates)} date(s) {dates[0]}..{dates[-1]}, store {db}, "
          f"{'APPLY' if a.apply else 'DRY RUN (read-only)'}", flush=True)
    best, meta, _ = collect(sym, intervals, dates, s3, now_ms)
    print(meta.banner())
    if meta.error:
        print("FAILED: the warehouse could not be read - nothing was written")
        return 3
    if meta.listed == 0:
        print("FAILED: the warehouse listed 0 candle objects for these dates - nothing to seed")
        return 3
    if meta.read == 0:
        print(f"FAILED: {meta.listed} object(s) listed but none for {sym} - nothing to seed")
        return 3

    max_ms = now_ms + TS_MAX_AHEAD_MS
    plan = {}
    for iv in intervals:
        cutoff = now_ms - RETENTION_DAYS[iv] * DAY_MS
        good, rejected = {}, {}
        for _k, (_s, r) in best[iv].items():
            ts, val = _verdict(r, cutoff, max_ms, iv, _s)
            if ts is None:
                rejected[val] = rejected.get(val, 0) + 1
            else:
                good[ts] = val
        have = _present(ro, sym, iv, list(good))
        missing = sorted(t for t in good if t not in have)
        plan[iv] = missing, good
        rj = ", ".join(f"{k} {v}" for k, v in sorted(rejected.items())) or "none"
        print(f"  {sym} {iv:>3}: {len(best[iv])} bar(s) found, {len(missing)} "
              f"{'to insert' if a.apply else 'would insert'}, {len(have)} already present, "
              f"rejected: {rj}")
    ro.close()
    if not a.apply:
        print("DRY RUN - nothing written. --apply writes the missing rows (INSERT OR IGNORE).")
        return 0

    rw = sqlite3.connect(db, timeout=30)
    rw.execute("PRAGMA busy_timeout=30000")
    for iv in intervals:
        missing, good = plan[iv]
        before = _count(rw, sym, iv)
        with rw:                                                  # one transaction per interval
            rw.executemany(
                "INSERT OR IGNORE INTO candles (symbol, interval, ts_epoch_ms, open, high, low, close, volume)"
                " VALUES (?,?,?,?,?,?,?,?)", [(sym, iv, t) + good[t] for t in missing])
        after = _count(rw, sym, iv)
        print(f"  APPLIED {sym} {iv:>3}: {after - before} row(s) inserted ({before} -> {after})")
        if after - before != len(missing):
            print(f"  ⚠️ {len(missing)} planned, {after - before} inserted - the feed wrote some meanwhile, "
                  "and its rows win (INSERT OR IGNORE)")
    rw.close()
    return 0


if __name__ == "__main__":
    sys.exit(run())
