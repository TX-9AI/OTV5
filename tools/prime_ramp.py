#!/usr/bin/env python3
"""
tools/prime_ramp.py  v5.0
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

Run:   python3 tools/prime_ramp.py            (dry run)
       python3 tools/prime_ramp.py --apply    (WRITES; configure.sh's first start and item 1 run this)
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
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import warehouse_source as ws                                   # noqa: E402  the ONE reader
import seed_candles_from_warehouse as seed                      # noqa: E402  SEED.1/SEED.2, not copied
from utils import instrument as _instr                          # noqa: E402
from utils import paths as _paths                               # noqa: E402
from utils import market_calendar as _mc                        # noqa: E402
from warehouse.retention_purge import RETENTION_DAYS            # noqa: E402

ET = ZoneInfo("America/New_York")
BUILT = (("5m", 5), ("15m", 15), ("1h", 60))
DAY_MS = 86_400_000
SMA_1D_NEED = 55


def is_ext(store_symbol: str) -> bool:
    return str(store_symbol or "").endswith("_EXT")


def required_minutes(store_symbol: str, ts_ms: int, span: int) -> list:
    """The 1m starts a COMPLETE bar must hold - candle_feed._referee_minutes, mirrored (R9 pins it)."""
    mins = [int(ts_ms) + k * 60_000 for k in range(span)]
    if is_ext(store_symbol):
        return mins
    d = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).astimezone(ET).date()
    if not _mc.is_trading_day(d):
        return []
    bell = _mc.close_time(d)
    lo, hi = 9 * 60 + 30, bell.hour * 60 + bell.minute
    out = []
    for m in mins:
        et = datetime.fromtimestamp(m / 1000.0, tz=timezone.utc).astimezone(ET)
        if lo <= et.hour * 60 + et.minute < hi:
            out.append(m)
    return out


def build_from_1m(store_symbol: str, rows1m: dict, span: int) -> dict:
    """{ts: (o,h,l,c,v)} of COMPLETE `span`-minute bars from {ts: (o,h,l,c,v)} 1m rows."""
    span_ms = span * 60_000
    buckets = {}
    for ts in rows1m:
        buckets.setdefault(ts - ts % span_ms, []).append(ts)
    out = {}
    for k in sorted(buckets):
        need = required_minutes(store_symbol, k, span)
        if not need or any(m not in rows1m for m in need):
            continue
        ms = sorted(need)
        o = rows1m[ms[0]][0]
        h = max(rows1m[m][1] for m in ms)
        lo = min(rows1m[m][2] for m in ms)
        c = rows1m[ms[-1]][3]
        v = sum(float(rows1m[m][4] or 0.0) for m in ms)
        out[k] = (o, h, lo, c, v)
    return out


def store_rows(conn, store_symbol: str, iv: str, since_ms: int) -> dict:
    return {r[0]: tuple(r[1:]) for r in conn.execute(
        "SELECT ts_epoch_ms, open, high, low, close, volume FROM candles WHERE symbol=? AND interval=? "
        "AND ts_epoch_ms >= ? AND open > 0 AND high > 0 AND low > 0 AND close > 0",
        (store_symbol, iv, int(since_ms)))}


def session_bell_ms(day) -> int:
    bell = _mc.close_time(day)
    return int(datetime(day.year, day.month, day.day, bell.hour, bell.minute, tzinfo=ET).timestamp() * 1000)


def daily_verdict(row: dict, stamp: str, now_ms: int):
    """-> (ts, tuple) or (None, reason). A daily bar is stamped 00:00 UTC of its session."""
    try:
        ts = int(row["ts_epoch_ms"])
        o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
        v = float(row.get("volume") or 0.0)
    except (KeyError, TypeError, ValueError):
        return None, "malformed"
    if not (seed.TS_MS_MIN <= ts <= now_ms + seed.TS_MAX_AHEAD_MS):
        return None, "poison_ts"
    if min(o, h, l, c) <= 0:
        return None, "nonpositive_price"
    day = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc).date()
    if not _mc.is_trading_day(day):
        return None, "not_a_session"
    pushed = seed._push_ms(stamp)
    if pushed is None:
        return None, "no_push_time"
    if pushed < session_bell_ms(day):
        return None, "partial"                 # pushed before that session's bell: the forming day
    return ts, (o, h, l, c, v)


STUDY_1D_KEY = "study/candles_1d/sym={sym}/candles_1d.csv"     # the daily study corpus (operator 10-23: not under raw/)


def read_study_1d(s3, sym: str, now_ms: int):
    """{ts: (o,h,l,c,v)} of CLOSED sessions from the study corpus, and a line saying what was read.
    A daily bar is stamped 00:00 UTC of its session. A session whose bell has not rung is never taken.
    Absent / unreadable -> ({}, reason): the warehouse's raw 1d then stands alone, and the line says so."""
    import csv
    import io as _io
    key = STUDY_1D_KEY.format(sym=sym)
    try:
        body = s3.get_object(Bucket=ws.BUCKET, Key=key)["Body"].read().decode()
    except Exception as exc:                                   # noqa: BLE001
        return {}, f"s3://{ws.BUCKET}/{key} not read: {type(exc).__name__}"
    out, bad = {}, 0
    for r in csv.DictReader(_io.StringIO(body)):
        try:
            day = datetime.strptime(r["date"], "%Y-%m-%d").date()
            o, h, l, c = (float(r[k]) for k in ("open", "high", "low", "close"))
            v = float(r.get("volume") or 0.0)
        except (KeyError, TypeError, ValueError):
            bad += 1
            continue
        if min(o, h, l, c) <= 0 or not _mc.is_trading_day(day) or session_bell_ms(day) > now_ms:
            bad += 1
            continue
        ts = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1000)
        out[ts] = (o, h, l, c, v)
    first = min(out) if out else None
    return out, (f"s3://{ws.BUCKET}/{key}: {len(out)} closed day(s)"
                 + (f" from {datetime.fromtimestamp(first / 1000, tz=timezone.utc).date()}" if first else "")
                 + (f", {bad} row(s) refused" if bad else ""))


def all_dates(s3) -> list:
    pre = f"{ws.PREFIX}/candles/"
    out = set()
    pg = s3.get_paginator("list_objects_v2")
    try:
        pages = list(pg.paginate(Bucket=ws.BUCKET, Prefix=pre, Delimiter="/"))
    except TypeError:                                    # warehouse_source._FakeS3 takes no Delimiter
        pages = list(pg.paginate(Bucket=ws.BUCKET, Prefix=pre))
    for page in pages:
        for p in page.get("CommonPrefixes", []) or []:
            d = p["Prefix"][len(pre):].strip("/")
            if d.startswith("dt="):
                out.add(d[3:])
        for o in page.get("Contents", []) or []:          # a store that ignores Delimiter (the test double)
            part = o["Key"][len(pre):].split("/", 1)[0]
            if part.startswith("dt="):
                out.add(part[3:])
    return sorted(out)


def sessions_between(lo_ms: int, hi_ms: int) -> list:
    d = datetime.fromtimestamp(lo_ms / 1000, tz=timezone.utc).astimezone(ET).date()
    end = datetime.fromtimestamp(hi_ms / 1000, tz=timezone.utc).astimezone(ET).date()
    out = []
    while d <= end:
        if _mc.is_trading_day(d):
            out.append(d)
        d += timedelta(days=1)
    return out


def session_of(ts_ms: int):
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).astimezone(ET).date()


def run(argv=None, s3=None, now_ms=None) -> int:
    ap = argparse.ArgumentParser(description="Prime the informers' ramp for this box's instrument from the warehouse.")
    ap.add_argument("--apply", action="store_true", help="WRITE (default: dry run)")
    ap.add_argument("--symbol", help="must equal the box's instrument")
    ap.add_argument("--db", help="feed store path (default: utils.paths.feed_db_path())")
    ap.add_argument("--days", type=int, help="fewer calendar days of 1m than the retention depth")
    a = ap.parse_args(argv)
    now_ms = int(now_ms if now_ms is not None else time.time() * 1000)
    try:
        box = _instr.box_instrument()
        if box == _instr.UNSET:
            raise seed.Refused("this box's instrument is UNSET (no OT_INSTRUMENT here or in the bot unit)")
        if a.symbol and a.symbol.strip().upper() != box:
            raise seed.Refused(f"--symbol {a.symbol} is not this box's instrument ({box})")
        db = a.db or _paths.feed_db_path()
        if not os.path.isfile(db):
            raise seed.Refused(f"feed store not found: {db}")
        ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)
        if not ro.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='candles'").fetchone():
            raise seed.Refused(f"no candles table in {db}")
        ro.close()
        if s3 is None:
            if not seed._creds_resolve():
                raise seed.Refused("AWS credentials do not resolve on this box (checked as a boolean)")
            s3 = ws.client()
    except seed.Refused as exc:
        print(f"REFUSED: {exc}")
        return 2
    mode = "APPLY" if a.apply else "DRY RUN (read-only)"
    print(f"prime_ramp v1.0 - {box} (+{box}_EXT), store {db}, {mode}", flush=True)
    depth1m = min(RETENTION_DAYS["1m"], a.days) if a.days else RETENTION_DAYS["1m"]
    today = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).astimezone(ET).date()
    dates = [(today - timedelta(days=i)).isoformat() for i in range(depth1m - 1, -1, -1)]
    rc = 0
    for sym in (box, f"{box}_EXT"):
        # ── 1. 1m from the warehouse (SEED.1/SEED.2) ────────────────────────────────────────────────
        best, meta, _ = seed.collect(sym, ["1m"] + [iv for iv, _ in BUILT], dates, s3, now_ms)
        if meta.error:
            print(f"FAILED: the warehouse could not be read ({meta.error}) - nothing written for {sym}")
            return 3
        if meta.read == 0:
            msg = f"{meta.listed} object(s) listed, none for {sym}"
            if sym == box:
                print(f"FAILED: {msg} - nothing to prime")
                return 3
            print(f"  {sym}: {msg} - EXT not primed (said, not a failure)")
            continue
        cutoff = now_ms - RETENTION_DAYS["1m"] * DAY_MS
        good1, rej1 = {}, {}
        for _k, (st, r) in best["1m"].items():
            ts, val = seed._verdict(r, cutoff, now_ms + seed.TS_MAX_AHEAD_MS, "1m", st)
            if ts is None:
                rej1[val] = rej1.get(val, 0) + 1
            else:
                good1[ts] = val
        conn = sqlite3.connect(db, timeout=30) if a.apply else sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)
        conn.execute("PRAGMA busy_timeout=30000")
        have1 = store_rows(conn, sym, "1m", cutoff)
        new1 = {t: v for t, v in good1.items() if t not in have1}
        print(f"  {sym} 1m: {len(good1)} complete in the warehouse, {len(new1)} "
              f"{'inserted' if a.apply else 'would insert'}, {len(have1)} already held, rejected "
              f"{', '.join(f'{k} {v}' for k, v in sorted(rej1.items())) or 'none'}")
        if a.apply and new1:
            with conn:
                conn.executemany("INSERT OR IGNORE INTO candles (symbol, interval, ts_epoch_ms, open, high, low, "
                                 "close, volume) VALUES (?,?,?,?,?,?,?,?)", [(sym, "1m", t) + new1[t] for t in new1])
        rows1 = dict(have1)
        for t, v in new1.items():
            rows1.setdefault(t, v)
        # ── 2. 5m / 15m / 1h built from the 1m ──────────────────────────────────────────────────────
        for iv, span in BUILT:
            since = now_ms - RETENTION_DAYS[iv] * DAY_MS
            built = {t: v for t, v in build_from_1m(sym, rows1, span).items() if t >= since}
            # the warehouse's own COMPLETE bars (SEED.2: pushed at/after the bar's end) fill a bucket whose 1m is
            # incomplete; a bar built from 1m always wins
            wh, rjw = {}, {}
            for _k, (st, r) in best[iv].items():
                ts, val = seed._verdict(r, since, now_ms + seed.TS_MAX_AHEAD_MS, iv, st)
                if ts is None:
                    rjw[val] = rjw.get(val, 0) + 1
                elif ts not in built:
                    wh[ts] = val
            have = store_rows(conn, sym, iv, since)
            new = {t: v for t, v in {**wh, **built}.items() if t not in have}
            print(f"  {sym} {iv:>3}: {len(built)} complete bar(s) built from 1m + {len(wh)} complete warehouse "
                  f"bar(s) where the 1m is incomplete; {len(new)} {'inserted' if a.apply else 'would insert'}, "
                  f"{len(have)} already held; warehouse rejected "
                  f"{', '.join(f'{k} {v}' for k, v in sorted(rjw.items())) or 'none'}")
            if a.apply and new:
                with conn:
                    conn.executemany("INSERT OR IGNORE INTO candles (symbol, interval, ts_epoch_ms, open, high, low, "
                                     "close, volume) VALUES (?,?,?,?,?,?,?,?)", [(sym, iv, t) + new[t] for t in new])
        # ── 3. 1d (the box symbol only: the EXT route has no daily) ──────────────────────────────────
        # The study corpus first (STUDY_1D_KEY: years of RTH daily bars, cleaned, never under raw/), then the
        # warehouse's raw 1d for any session after the corpus ends. Each bar says where it came from.
        if sym == box:
            gd, src, rjd = {}, {}, {}
            study, why = read_study_1d(s3, sym, now_ms)
            for ts, val in study.items():
                gd[ts], src[ts] = val, "study"
            alld = all_dates(s3)
            bestd, metad, _ = seed.collect(sym, ["1d"], alld, s3, now_ms) if alld else ({"1d": {}}, None, None)
            for _k, (st, r) in bestd["1d"].items():
                ts, val = daily_verdict(r, st, now_ms)
                if ts is None:
                    rjd[val] = rjd.get(val, 0) + 1
                elif ts not in gd:
                    gd[ts], src[ts] = val, "raw"
            haved = store_rows(conn, sym, "1d", 0)
            newd = {t: v for t, v in gd.items() if t not in haved}
            tot = len(set(gd) | set(haved))
            ns = sum(1 for t in newd if src[t] == "study")
            print(f"  {sym}  1d: study corpus {len(study)} closed day(s) ({why}); warehouse raw 1d adds "
                  f"{sum(1 for v in src.values() if v == 'raw')}; {len(newd)} {'inserted' if a.apply else 'would insert'} "
                  f"({ns} study, {len(newd) - ns} raw), {len(haved)} already held, raw rejected "
                  f"{', '.join(f'{k} {v}' for k, v in sorted(rjd.items())) or 'none'}"
                  + (f"  ⚠️ {tot} daily bar(s) < {SMA_1D_NEED}: sma50_mtf 1d stays silent" if tot < SMA_1D_NEED else ""))
            if a.apply and newd:
                with conn:
                    conn.executemany("INSERT OR IGNORE INTO candles (symbol, interval, ts_epoch_ms, open, high, low, "
                                     "close, volume) VALUES (?,?,?,?,?,?,?,?)", [(sym, "1d", t) + newd[t] for t in newd])
        # ── what could not be filled: sessions with no complete 1m ───────────────────────────────────
        sess = sessions_between(cutoff, now_ms)
        held = {session_of(t) for t in rows1}
        closed = [d for d in sess if session_bell_ms(d) <= now_ms]
        gaps = [d.isoformat() for d in closed if d not in held]
        print(f"  {sym}: sessions in the 1m depth {len(closed)}, with no 1m {len(gaps)}"
              + (f" ({', '.join(gaps[:10])}{' ...' if len(gaps) > 10 else ''})" if gaps else ""))
        if sym == box and closed and closed[-1] not in held:
            print(f"FAILED: the last closed session {closed[-1]} has no 1m for {sym} - the ramp is NOT primed")
            rc = 4
        conn.close()
    if not a.apply:
        print("DRY RUN - nothing written. --apply writes the missing rows (INSERT OR IGNORE).")
    return rc


if __name__ == "__main__":
    sys.exit(run())
