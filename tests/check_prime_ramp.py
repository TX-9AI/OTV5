#!/usr/bin/env python3
"""
tests/check_prime_ramp.py  v5.1
v5.1  2026-10-25  OTV5 r16 (PRIME.1) — RE-POINTED (WA section 38.4): THE RAMP IS PRIMED FROM TASTYTRADE BY candle-feed, AND
      ONLY WHERE THE STORE HOLDS NOTHING. The operator, 2026-10-25: prime from TastyTrade only, never S3; only what is
      missing; only at a symbol switch. R1-R13 pinned the warehouse primer that is gone; P1-P9 pin its replacement, driven
      on scratch stores built by the REAL data/candle_feed.FeedStore, with no network and a fake clock. BORN RED on r15
      (the tool read the warehouse, PRIME_DAYS and newest_held_ms did not exist).
  P1  a one-read run on a store whose last closed session holds 1m: rc 0, nothing written, the source named TastyTrade
  P2  --apply on a store with NO 1m for the last session, the feed's backfill landing at the 2nd poll: it waits, then
      rc 0 once two reads agree; nothing written by the tool
  P3  --apply, the backfill never lands: rc 4 "NOT primed" after --wait, said
  P4  refusals (rc 2): a disagreeing --symbol, an UNSET instrument, no store
  P5  the tool reads no S3: its source imports none of warehouse_source / boto3 / seed_candles_from_warehouse
  P6  fewer than 55 daily bars is SAID
  P7  candle_feed._backfill_start: a (store symbol, interval) the store has NEVER held starts PRIME_DAYS deep; a held one
      starts exactly where it did before r16 when its newest bar is recent, reaches back to an older newest bar, and
      never deeper than PRIME_DAYS
  P8  PRIME_DAYS stays inside RETENTION_DAYS for every purged interval (the purge never deletes what was just primed),
      and 1d is deep enough for sma50_mtf (>= 55 sessions)
  P9  CandleFeed._start_for reads the store at subscribe time: a symbol switched to (none held) primes deep; the same
      store after bars land backfills as before
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-24  CD.1 — the gate for tools/prime_ramp.py. No network: warehouse_source's own _FakeS3 and a scratch
      feed store built by the REAL data/candle_feed.FeedStore (the schema is the feed's, WA §0.4). The tool is driven
      through its run(); every expectation is computed here independently of the tool's own aggregation.
  R1  a dry run writes nothing (every candles / feed_meta row identical) and exits 0
  R2  --apply inserts complete 1m bars only: a bar pushed before its end ("partial") is refused, a row the store
      already held is NOT changed
  R3  5m / 15m / 1h are BUILT FROM 1m: values equal an independent aggregation of the 1m written; the warehouse's
      own (forming) 5m bar is never written; an incomplete bucket is not written
  R4  completeness: SYM's 09:00 hour bar is built from 09:30-09:59 only (the RTH minutes); SYM_EXT's hour needs every
      minute, so an EXT hour missing one minute is not written
  R5  1d: a daily bar whose winning push came before that session's bell is refused ("partial"); one pushed after
      is written; fewer than 55 daily bars is SAID
  R6  a re-run inserts 0 rows
  R7  a --symbol other than the box's instrument is refused (rc 2); UNSET is refused (rc 2)
  R8  no objects for the symbol -> rc 3, nothing written
  R9  required_minutes() equals data/candle_feed._referee_minutes (the mirror is pinned)
  R10 the last closed session with no 1m -> rc 4 ("NOT primed"), said
  R11 feed_meta is never touched
  R13 a complete warehouse 5m/15m/1h bar (SEED.2) fills a bucket whose 1m is incomplete; built-from-1m wins
  R12 1d: the study corpus (study/candles_1d) is read first - closed sessions only - and the warehouse raw 1d adds
      the sessions after it; the source is named; with no corpus the line says so (R12b)
Run: python3 tests/check_prime_ramp.py
"""
import atexit
import contextlib
import glob as _glob
import hashlib
import io
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
os.environ["OT_INSTRUMENT"] = "SPX"
_SCRATCH = tempfile.mkdtemp(prefix="primechk_")
atexit.register(shutil.rmtree, _SCRATCH, True)
os.environ.setdefault("OT_LOG_FILE", os.path.join(_SCRATCH, "bot.log"))
ET = ZoneInfo("America/New_York")
M = 60_000
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def utc(y, mo, d, h, mi):
    return int(datetime(y, mo, d, h, mi, tzinfo=timezone.utc).timestamp() * 1000)


def main() -> int:
    import prime_ramp as pr
    import data.candle_feed as cf
    from warehouse.retention_purge import RETENTION_DAYS

    now_ms = utc(2026, 10, 5, 16, 0)            # Mon 12:00 ET; the last closed session is Fri 10-02
    o930 = utc(2026, 10, 2, 13, 30)

    def store(with_last=True, daily=0):
        d = tempfile.mkdtemp(prefix="store_", dir=_SCRATCH)
        db = os.path.join(d, "feed_store.db")
        fs = cf.FeedStore(db)
        if with_last:
            fs.conn.executemany("INSERT INTO candles VALUES ('SPX','1m',?,1,2,0.5,1.5,10)",
                                [(o930 + k * M,) for k in range(30)])
        for k in range(daily):
            fs.conn.execute("INSERT INTO candles VALUES ('SPX','1d',?,1,2,0.5,1.5,10)",
                            (utc(2026, 1, 1, 0, 0) + k * 86_400_000,))
        fs.conn.commit()
        fs.conn.close()
        return db

    def digest(path):
        c = sqlite3.connect(path)
        h = hashlib.sha256()
        for t in ("candles", "feed_meta"):
            for r in c.execute(f"SELECT * FROM {t} ORDER BY 1, 2, 3"):
                h.update(repr(r).encode())
        c.close()
        return h.hexdigest()

    class Clock:
        def __init__(self, on_sleep=None):
            self.t, self.n, self.on_sleep = 1000.0, 0, on_sleep

        def __call__(self):
            return self.t

        def sleep(self, s):
            self.t += s
            self.n += 1
            if self.on_sleep:
                self.on_sleep(self.n)

    def go(argv, db, clock=None):
        clock = clock or Clock()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = pr.run(list(argv) + ["--db", db], now_ms=now_ms, sleep=clock.sleep, clock=clock)
        return rc, buf.getvalue(), clock

    # P1
    db = store(daily=60)
    before = digest(db)
    rc, out, _ = go([], db)
    check("P1 one read, the last session held: rc 0, nothing written, source TastyTrade",
          rc == 0 and digest(db) == before and "TastyTrade" in out and "2026-10-02" in out, f"rc {rc}\n{out}")

    # P2 — the backfill lands at the 2nd poll
    db2 = store(with_last=False, daily=60)

    def land(n):
        if n == 2:
            c = sqlite3.connect(db2)
            c.executemany("INSERT INTO candles VALUES ('SPX','1m',?,1,2,0.5,1.5,10)", [(o930 + k * M,) for k in range(30)])
            c.commit()
            c.close()
    rc, out, clk = go(["--apply", "--wait", "300"], db2, Clock(land))
    check("P2 --apply waits for the feed's backfill, then rc 0 once two reads agree",
          rc == 0 and clk.n >= 3 and "OK: 30 1m bar(s)" in out, f"rc {rc} polls {clk.n}\n{out}")

    # P3 — never lands
    db3 = store(with_last=False, daily=60)
    rc, out, clk = go(["--apply", "--wait", "60"], db3)
    check("P3 the backfill never lands: rc 4 NOT primed after the wait",
          rc == 4 and "NOT primed" in out and clk.t - 1000.0 >= 60, f"rc {rc}\n{out}")

    # P4 — refusals
    rc_a, _, _ = go(["--symbol", "QQQ"], db)
    old = os.environ["OT_INSTRUMENT"]
    os.environ["OT_INSTRUMENT"] = "UNSET"
    try:
        rc_b, _, _ = go([], db)
    finally:
        os.environ["OT_INSTRUMENT"] = old
    rc_c, out_c, _ = go([], os.path.join(_SCRATCH, "nope", "feed_store.db"))
    check("P4 a disagreeing --symbol, UNSET and no store are refused (rc 2)",
          rc_a == 2 and rc_b == 2 and rc_c == 2 and "not found" in out_c, f"{rc_a} {rc_b} {rc_c}")

    # P5 — no S3
    src = open(os.path.join(ROOT, "tools", "prime_ramp.py"), encoding="utf-8").read()
    code = src.split('"""', 2)[2]
    banned = [b for b in ("warehouse_source", "boto3", "seed_candles_from_warehouse", "s3") if b in code]
    check("P5 the tool's code reads no S3", not banned, f"found {banned}")

    # P6 — < 55 daily bars said
    db6 = store(daily=10)
    rc, out, _ = go([], db6)
    check("P6 fewer than 55 daily bars is SAID", rc == 0 and "< 55 daily bars" in out, out)

    # P7 — _backfill_start
    now = datetime(2026, 10, 5, 12, 0, tzinfo=ET)
    bad = []
    for iv, days in cf.PRIME_DAYS.items():
        if cf._backfill_start(iv, now, None, held=False) != now - timedelta(days=days):
            bad.append(f"{iv} unheld")
    legacy_1m = datetime(2026, 10, 5, 9, 30, tzinfo=ET)
    recent = int(datetime(2026, 10, 5, 11, 59, tzinfo=ET).timestamp() * 1000)
    if cf._backfill_start("1m", now, recent, held=True) != legacy_1m:
        bad.append("1m held recent")
    if cf._backfill_start("1h", now, recent, held=True) != now - timedelta(days=cf.BACKFILL_DAYS["1h"]):
        bad.append("1h held recent")
    older = int(datetime(2026, 9, 20, 15, 0, tzinfo=ET).timestamp() * 1000)
    if cf._backfill_start("5m", now, older, held=True) != datetime(2026, 9, 20, 15, 0, tzinfo=ET):
        bad.append("5m held older")
    ancient = int(datetime(2025, 1, 1, tzinfo=ET).timestamp() * 1000)
    if cf._backfill_start("1m", now, ancient, held=True) != now - timedelta(days=cf.PRIME_DAYS["1m"]):
        bad.append("1m held ancient")
    check("P7 never held -> PRIME_DAYS deep; held -> the pre-r16 start, back to an older newest bar, never past PRIME_DAYS",
          not bad, str(bad))

    # P8 — inside retention; 1d deep enough
    over = [iv for iv, d in cf.PRIME_DAYS.items() if RETENTION_DAYS.get(iv) is not None and d > RETENTION_DAYS[iv]]
    check("P8 PRIME_DAYS inside RETENTION_DAYS; 1d >= 55 sessions",
          not over and cf.PRIME_DAYS["1d"] * 5 // 7 - 10 >= 55, f"over={over} 1d={cf.PRIME_DAYS['1d']}")

    # P9 — _start_for reads the store at subscribe time
    db9 = store(with_last=False)
    fs9 = cf.FeedStore(db9)
    feed = cf.CandleFeed.__new__(cf.CandleFeed)
    feed.store = fs9
    feed.symbol_map = {("NEWSYM", "1h", False): "NEWSYM"}
    fb = datetime(2000, 1, 1, tzinfo=ET)
    s_none = feed._start_for("NEWSYM", "1h", False, fb)
    deep_ok = abs((datetime.now(ET) - s_none) - timedelta(days=cf.PRIME_DAYS["1h"])) < timedelta(minutes=5)
    fs9.conn.execute("INSERT INTO candles VALUES ('NEWSYM','1h',?,1,2,0.5,1.5,10)",
                     (int(datetime.now(timezone.utc).timestamp() * 1000) - 3_600_000,))
    fs9.conn.commit()
    s_held = feed._start_for("NEWSYM", "1h", False, fb)
    held_ok = abs((datetime.now(ET) - s_held) - timedelta(days=cf.BACKFILL_DAYS["1h"])) < timedelta(minutes=5)
    fs9.conn.close()
    check("P9 _start_for: a symbol switched to primes PRIME_DAYS deep; once bars land it backfills as before",
          deep_ok and held_ok, f"none->{s_none} held->{s_held}")

    print()
    if FAILED:
        print(f"RED — {sorted(set(FAILED))}")
        return 1
    print("GREEN — P1-P9")
    return 0


if __name__ == "__main__":
    sys.exit(main())
