#!/usr/bin/env python3
"""
tools/prime_ramp.py  v5.1
v5.1  2026-10-25  OTV5 r16 (PRIME.1) — THE RAMP IS PRIMED FROM TASTYTRADE BY THE FEED; THIS TOOL WAITS FOR IT AND SAYS
      WHAT IS THERE. IT READS NO S3 AND WRITES NOTHING. The operator, 2026-10-25: a symbol switch primes "from tasty
      trade of whatever's obtainable", never from S3 ("if we haven't traded it recently last July's data ... isn't
      relevant or useful"); "only priming missing data - there is no reason to prime stuff that's already on the box";
      priming only at a symbol switch. v5.0 read the warehouse for the whole 1m depth and the raw 1d of EVERY warehouse
      date (SOFI's first Done, 2026-10-25: ~12 minutes to insert almost nothing - SOFI already held its own tape).
      data/candle_feed.py v5.1 now primes a (store symbol, interval) the store has NEVER held PRIME_DAYS deep from
      TastyTrade and backfills a held one exactly as before. This tool, run by configure.sh after candle-feed starts
      (first start, symbol switch):
        - reads the feed store only (read-only), for the box's instrument and its _EXT twin;
        - --apply WAITS (up to --wait seconds, default 300) until the last closed session has 1m for the instrument
          AND the store's bar counts stopped changing between two reads (the backfill has landed);
        - reports, per store symbol and interval, the bars held, the first held day and the sessions covered; fewer
          than 55 closed daily bars is SAID (sma50_mtf's 1d stays silent);
        - exit 0 primed, 2 refused (named), 4 the last closed session still has no 1m (the bot is not started).
      TastyTrade's reach (QQQ-TEST MSG-QQQ-1025-14): 1m ~21 RTH sessions (8,000-bar cap), 1m EXT ~8, 5m/15m ~3 months,
      1h ~9.5 months, 1d to 2022-12-29; a 60-day 1m tape cannot be filled from TastyTrade, and that is SAID, not failed.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-24  CD.1 — THE INFORMERS' RAMP IS PRIMED FROM THE WAREHOUSE, AT FIRST START AND AT EVERY SYMBOL
      SWITCH. The operator, 2026-10-24 14:59 ET: "We need a script that primes the informers' ramp from s3 whenever we
      switch symbols. Once the deploy lands & config.sh params are all set, that should be the 1st start of options
      bot, candle service, the ramp primer & s3 push enabled (from configure.sh)".

      WHAT "THE RAMP" IS: every informer that reads the feed store's history before it can speak - the level book
      (1m), the 5m swing stop (BRK.11), the session/prior-day levels (1m, 1d), sma50 / sma50_mtf (5m, 15m, 1h,
      1d on SYM and SYM_EXT; r183/r315) - is silent or wrong on a fresh store until days of bars exist.

      WHAT IT DOES, for THE BOX'S instrument only (utils.instrument.box_instrument; a disagreeing --symbol is
      refused), for the store symbols SYM and SYM_EXT:
        1. 1m: tools/seed_candles_from_warehouse (SEED.1/SEED.2, imported, not copied) - complete bars only (a
           bar whose winning push came before its end is "partial" and refused), depth RETENTION_DAYS["1m"].
        2. 5m / 15m / 1h: BUILT FROM THE STORE'S 1m after step 1, never taken from the warehouse (mainline pushes
           the FORMING higher-timeframe bar - SEED.2). Buckets are epoch-aligned (an hour bar starts on the hour,
           DXFeed's alignment; the 09:00 ET hour holds 09:30-09:59). A bucket is written only when it is
           COMPLETE: every minute candle_feed._referee_minutes requires (SYM: the RTH minutes to the day's bell;
           SYM_EXT: every minute) is present in the store. Mirrored, not imported (candle_feed pulls the broker
           SDK); tests/check_prime_ramp.py R9 pins the two equal. Depth: RETENTION_DAYS per interval. A bucket
           whose 1m is incomplete takes the warehouse's own bar for it ONLY if that bar is complete (SEED.2: its
           winning push came at/after the bar's end) - so the level book's 1h reaches its full 60 days where the
           1m tape is patchy. A bar built from 1m always wins over the warehouse's.
        3. 1d: FIRST the daily study corpus (study/candles_1d/sym=<SYM>/candles_1d.csv - years of cleaned RTH
           daily bars, deliberately outside raw/); THEN the warehouse's raw 1d for sessions the corpus does not
           hold, each kept only when its winning push came AFTER that session's bell (the SEED.2 rule for a
           day). The forming day is never seeded, from either source. The line names how many came from each;
           fewer than 55 closed days (sma50_mtf's 1d needs 50 + slope 5) is SAID.
      Every write is INSERT OR IGNORE - a row the store already holds (the live feed's) is never changed.
      feed_meta is NOT touched (its last_write_epoch is the feed's freshness signal).

      DRY RUN BY DEFAULT (read-only). --apply writes. Names what it could not fill: per store symbol and
      interval, the sessions with no complete bar. Exit 0 ok, 2 refused (named), 3 the warehouse failed or held
      nothing for the symbol, 4 the last closed session has no complete 1m (the ramp is not primed).

Run:   python3 tools/prime_ramp.py            (one read: what the store holds now)
       python3 tools/prime_ramp.py --apply    (configure.sh: wait for the feed's backfill, then the same report)
Gate:  tests/check_prime_ramp.py
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from utils import instrument as _instr                          # noqa: E402
from utils import paths as _paths                               # noqa: E402
from utils import market_calendar as _mc                        # noqa: E402

ET = ZoneInfo("America/New_York")
INTERVALS = ("1m", "5m", "15m", "1h", "1d")
SMA_1D_NEED = 55
POLL_S = 10


class Refused(Exception):
    pass


def last_closed_session(now_ms: int):
    d = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).astimezone(ET).date()
    for _ in range(15):
        if _mc.is_trading_day(d):
            bell = _mc.close_time(d)
            if datetime(d.year, d.month, d.day, bell.hour, bell.minute, tzinfo=ET).timestamp() * 1000 <= now_ms:
                return d
        d -= timedelta(days=1)
    return None


def session_bounds_ms(day):
    lo = datetime(day.year, day.month, day.day, tzinfo=ET)
    hi = lo + timedelta(days=1)
    return int(lo.timestamp() * 1000), int(hi.timestamp() * 1000)


def read_state(db: str, sym: str, last_day):
    """{(store_symbol, interval): (bars, first_ms)} and the last closed session's 1m count, read-only."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)
    try:
        con.execute("PRAGMA busy_timeout=30000")
        out = {}
        for s in (sym, f"{sym}_EXT"):
            for iv in INTERVALS:
                n, first = con.execute("SELECT COUNT(*), MIN(ts_epoch_ms) FROM candles WHERE symbol=? AND interval=?",
                                       (s, iv)).fetchone()
                out[(s, iv)] = (int(n or 0), first)
        last1m = 0
        if last_day is not None:
            lo, hi = session_bounds_ms(last_day)
            last1m = con.execute("SELECT COUNT(*) FROM candles WHERE symbol=? AND interval='1m' "
                                 "AND ts_epoch_ms >= ? AND ts_epoch_ms < ?", (sym, lo, hi)).fetchone()[0]
        return out, int(last1m or 0)
    finally:
        con.close()


def run(argv=None, now_ms=None, sleep=time.sleep, clock=time.time) -> int:
    ap = argparse.ArgumentParser(description="Wait for the feed's TastyTrade backfill and report what the store holds.")
    ap.add_argument("--apply", action="store_true", help="wait for the backfill to land (configure.sh's start)")
    ap.add_argument("--wait", type=int, default=300, help="seconds --apply waits at most (default 300)")
    ap.add_argument("--symbol", help="must equal the box's instrument")
    ap.add_argument("--db", help="feed store path (default: utils.paths.feed_db_path())")
    a = ap.parse_args(argv)
    try:
        box = _instr.box_instrument()
        if box == _instr.UNSET:
            raise Refused("this box's instrument is UNSET (no OT_INSTRUMENT here or in the bot unit)")
        if a.symbol and a.symbol.strip().upper() != box:
            raise Refused(f"--symbol {a.symbol} is not this box's instrument ({box})")
        db = a.db or _paths.feed_db_path()
        if not os.path.isfile(db):
            raise Refused(f"feed store not found: {db} (candle-feed creates it at its first start)")
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        ok = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='candles'").fetchone()
        con.close()
        if not ok:
            raise Refused(f"no candles table in {db}")
    except Refused as exc:
        print(f"REFUSED: {exc}")
        return 2
    fixed_now = now_ms
    now = lambda: int(fixed_now if fixed_now is not None else clock() * 1000)   # noqa: E731
    last_day = last_closed_session(now())
    print(f"prime_ramp v5.1 - {box} (+{box}_EXT), store {db}: source TastyTrade (candle-feed's backfill), "
          f"{'WAITING up to %d s' % a.wait if a.apply else 'one read'}; last closed session {last_day}", flush=True)
    state, last1m = read_state(db, box, last_day)
    if a.apply:
        t0 = clock()
        prev = None
        while True:
            if last1m > 0 and state == prev:
                break
            if clock() - t0 >= a.wait:
                break
            prev = state
            sleep(POLL_S)
            state, last1m = read_state(db, box, last_day)
    for (s, iv), (n, first) in sorted(state.items(), key=lambda kv: (kv[0][0], INTERVALS.index(kv[0][1]))):
        if s.endswith("_EXT") and iv == "1d":
            continue
        fday = datetime.fromtimestamp(first / 1000, tz=timezone.utc).astimezone(ET).date() if first else None
        line = f"  {s:>10} {iv:>3}: {n} bar(s) held" + (f", from {fday}" if fday else "")
        if iv == "1d" and n < SMA_1D_NEED:
            line += f"  ⚠️ < {SMA_1D_NEED} daily bars: sma50_mtf 1d stays silent until it has them"
        print(line)
    print("  TastyTrade serves 1m only ~21 sessions back (8,000 bars); a deeper 1m tape builds with the sessions "
          "this box lives through.")
    if last_day is not None and last1m == 0:
        print(f"FAILED: the last closed session {last_day} has no 1m for {box} - the ramp is NOT primed")
        return 4
    print(f"OK: {last1m} 1m bar(s) for {box} on {last_day}; nothing was written by this tool.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
