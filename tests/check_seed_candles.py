#!/usr/bin/env python3
"""
tests/check_seed_candles.py  v1.1
v1.1  2026-10-04  OTV4TEST r237 (SEED.2) — C11/C12: partial bars and unreadable push times are refused. Born red on
      seed v1.0, which wrote 4,407 mid-bar warehouse bars into SPX-TEST's feed store.
v1.0  2026-10-04  OTV4TEST r233 (SEED.1) — the gate for tools/seed_candles_from_warehouse.py.
      No network: a fake bucket (warehouse_source's own _FakeS3) and a scratch feed store built by the
      REAL data/candle_feed.FeedStore, so the schema is the feed's and not a belief about it (WA §0.4).
  C1  a dry run writes nothing (the store's bytes are identical) and counts would-insert / already-present
  C2  --apply inserts only the missing rows; a row the store already held is NOT changed
  C3  zero / negative prices and a poison timestamp are rejected, never written
  C4  depth: a bar older than RETENTION_DAYS is rejected; the default window is the deepest interval's
  C5  a --symbol other than the box's instrument is refused (rc 2), and UNSET is refused
  C6  zero objects listed -> rc 3 with a reason; objects for other symbols only -> rc 3
  C7  a re-run inserts 0
  C8  a bar pushed twice: the LATER envelope's values are the ones written
  C9  the poison window is the feed's own (imported from data/candle_feed at runtime)
  C10 a missing store is refused (rc 2) and feed_meta is never touched
  C11 r237: a bar whose winning push came BEFORE its end is refused as "partial" (the mid-bar 5m bar mainline
      ships); a push exactly AT the bar's end is accepted
  C12 r237: a bar with an unreadable push time is refused ("no_push_time") - fail closed
Run: python3 tests/check_seed_candles.py      (OT_SEED_TOOL=<path> points it at another copy - the
     born-red runs use that)
"""
import atexit
import contextlib
import glob as _glob
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
os.environ["OT_INSTRUMENT"] = "SPX"
_SCRATCH = tempfile.mkdtemp(prefix="seedchk_")
atexit.register(shutil.rmtree, _SCRATCH, True)
os.environ.setdefault("OT_LOG_FILE", os.path.join(_SCRATCH, "bot.log"))

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def main() -> int:
    tool_path = os.environ.get("OT_SEED_TOOL") or os.path.join(ROOT, "tools", "seed_candles_from_warehouse.py")
    try:
        spec = importlib.util.spec_from_file_location("seed_tool", tool_path)
        seed = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(seed)
    except Exception as exc:                                    # noqa: BLE001
        check("C0 the tool loads", False, f"{type(exc).__name__}: {exc}")
        print(f"\nRED — {sorted(set(FAILED))}")
        return 1
    import warehouse_source as ws
    from warehouse.retention_purge import RETENTION_DAYS
    import data.candle_feed as cf

    now_ms = int(datetime(2026, 10, 4, 16, 0, tzinfo=timezone.utc).timestamp() * 1000)
    D = "2026-10-02"
    t0 = int(datetime(2026, 10, 2, 13, 30, tzinfo=timezone.utc).timestamp() * 1000)   # 09:30 ET
    M = 60_000

    def bar(ts, px, iv="1m", sym="SPX"):
        return {"symbol": sym, "interval": iv, "ts_epoch_ms": ts, "open": px, "high": px + 1,
                "low": px - 1, "close": px, "volume": 0.0}

    def env(rows, stamp, sym="SPX"):
        return json.dumps({"schema_version": 1, "datatype": "candles", "symbol": sym, "dt": D,
                           "pushed_at_utc": stamp, "record": rows}).encode()

    P = f"{ws.PREFIX}/candles/dt={D}"
    objs = {
        f"{P}/sym=SPX/interval=1m/1-a.json": env([bar(t0, 7700.0), bar(t0 + M, 7701.0),
                                                   bar(t0 + 2 * M, 7702.0)], "2026-10-02T14:00:00+00:00"),
        # C8: the same 09:32 bar pushed later with its final values
        f"{P}/sym=SPX/interval=1m/2-b.json": env([bar(t0 + 2 * M, 7750.0), bar(t0 + 3 * M, 7703.0)],
                                                  "2026-10-02T15:00:00+00:00"),
        # C3: poison
        f"{P}/sym=SPX/interval=1m/3-c.json": env([bar(t0 + 4 * M, 0.0), bar(t0 + 5 * M, -3.0),
                                                   bar(4_000_000_000_000, 7710.0)], "2026-10-02T15:01:00+00:00"),
        # C4: a 1m bar older than RETENTION_DAYS['1m'] (filed under this date's key on purpose)
        f"{P}/sym=SPX/interval=1m/4-d.json": env([bar(now_ms - (RETENTION_DAYS["1m"] + 2) * 86_400_000, 7000.0)],
                                                  "2026-10-02T15:02:00+00:00"),
        f"{P}/sym=SPX/interval=5m/5-e.json": env([bar(t0, 7700.0, "5m"), bar(t0 + 5 * M, 7705.0, "5m")],
                                                  "2026-10-02T15:03:00+00:00"),
        # another symbol on the same date - must never reach the SPX store
        f"{P}/sym=QQQ/interval=1m/6-f.json": env([bar(t0 + 9 * M, 600.0, sym="QQQ")],
                                                  "2026-10-02T15:04:00+00:00", sym="QQQ"),
    }
    fake = ws._FakeS3(objs)

    d = tempfile.mkdtemp(prefix="store_", dir=_SCRATCH)
    db = os.path.join(d, "feed_store.db")
    fs = cf.FeedStore(db)                                       # the REAL schema
    # one row the store already holds, with a value the warehouse disagrees with (09:31 = 7701 there)
    fs.conn.execute("INSERT INTO candles VALUES ('SPX','1m',?,1,1,1,1,0)", (t0 + M,))
    fs.conn.execute("INSERT INTO feed_meta (symbol, interval, last_write_epoch) VALUES ('SPX','1m',123.0)")
    fs.conn.commit()
    fs.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    fs.conn.close()

    def go(*argv, s3=fake):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = seed.run(list(argv), s3=s3, now_ms=now_ms)
        return rc, buf.getvalue()

    def md5():
        h = hashlib.md5()
        for f in sorted(glob_db()):
            h.update(open(f, "rb").read())
        return h.hexdigest()

    def glob_db():
        return [p for p in (db, db + "-wal") if os.path.exists(p)]

    def rows(iv="1m"):
        c = sqlite3.connect(db)
        out = dict(c.execute("SELECT ts_epoch_ms, close FROM candles WHERE symbol='SPX' AND interval=?",
                             (iv,)).fetchall())
        c.close()
        return out

    # C1
    h0 = md5()
    rc, out = go("--date", D, "--db", db)
    check("C1 dry run rc 0 and writes nothing", rc == 0 and md5() == h0, f"rc={rc} {out[-300:]}")
    check("C1 dry run counts: 1m 3 would insert, 1 present; 5m 2 would insert",
          "SPX  1m: 8 bar(s) found, 3 would insert, 1 already present" in out
          and "SPX  5m: 2 bar(s) found, 2 would insert, 0 already present" in out, out[-600:])

    # C2 + C3 + C4 + C8
    rc, out = go("--date", D, "--db", db, "--apply")
    r1 = rows()
    check("C2 apply rc 0, 3 x 1m and 2 x 5m inserted", rc == 0 and "APPLIED SPX  1m: 3 row(s) inserted" in out
          and "APPLIED SPX  5m: 2 row(s) inserted" in out, out[-500:])
    check("C2 the row the store already held is unchanged (close 1, not the warehouse's 7701)",
          r1.get(t0 + M) == 1.0, r1)
    check("C3 zero / negative price and a poison timestamp are not written",
          (t0 + 4 * M) not in r1 and (t0 + 5 * M) not in r1 and 4_000_000_000_000 not in r1
          and "nonpositive_price 2" in out and "poison_ts 1" in out, out[-500:])
    old = now_ms - (RETENTION_DAYS["1m"] + 2) * 86_400_000
    check("C4 a bar older than RETENTION_DAYS['1m'] is rejected", old not in r1 and "beyond_retention 1" in out,
          out[-500:])
    check("C4 the default window is the deepest interval's retention, in calendar days",
          len(seed._dates(None, max(RETENTION_DAYS[i] for i in seed.DEFAULT_INTERVALS)))
          == max(RETENTION_DAYS[i] for i in seed.DEFAULT_INTERVALS))
    check("C8 a bar pushed twice is written with the LATER push's values", r1.get(t0 + 2 * M) == 7750.0, r1)
    c = sqlite3.connect(db)
    other = c.execute("SELECT COUNT(*) FROM candles WHERE symbol<>'SPX'").fetchone()[0]
    meta_row = c.execute("SELECT last_write_epoch FROM feed_meta WHERE symbol='SPX' AND interval='1m'").fetchone()
    c.close()
    check("C2 another symbol's objects never reach the store", other == 0, other)

    # C7
    rc, out = go("--date", D, "--db", db, "--apply")
    check("C7 a re-run inserts 0", rc == 0 and "APPLIED SPX  1m: 0 row(s) inserted" in out
          and "APPLIED SPX  5m: 0 row(s) inserted" in out, out[-400:])

    # C2b — the feed writes a bar AFTER the seed read the store and BEFORE it writes: the feed's row wins
    d2 = tempfile.mkdtemp(prefix="race_", dir=_SCRATCH)
    db2 = os.path.join(d2, "feed_store.db")
    fs2 = cf.FeedStore(db2)
    fs2.conn.execute("INSERT INTO candles VALUES ('SPX','1m',?,2,2,2,2,0)", (t0,))
    fs2.conn.commit()
    fs2.conn.close()
    saved_present = seed._present
    seed._present = lambda conn, sym, iv, tss: set()          # the read saw an empty store
    try:
        rc, out = go("--date", D, "--db", db2, "--apply")
    finally:
        seed._present = saved_present
    c = sqlite3.connect(db2)
    raced = c.execute("SELECT close FROM candles WHERE symbol='SPX' AND interval='1m' AND ts_epoch_ms=?",
                      (t0,)).fetchone()
    c.close()
    check("C2b a row the feed wrote after the read is NOT overwritten (INSERT OR IGNORE)",
          rc == 0 and raced == (2.0,), (rc, raced, out[-300:]))

    # C5
    rc, out = go("--date", D, "--db", db, "--symbol", "QQQ")
    check("C5 a --symbol other than the box's is refused, rc 2", rc == 2 and "REFUSED" in out, out)
    os.environ["OT_INSTRUMENT"] = ""
    try:
        import utils.instrument as ui
        saved = ui._from_bot_unit
        ui._from_bot_unit = lambda key="OT_INSTRUMENT": ""
        rc, out = go("--date", D, "--db", db)
        ui._from_bot_unit = saved
    finally:
        os.environ["OT_INSTRUMENT"] = "SPX"
    check("C5 an UNSET instrument is refused, rc 2", rc == 2 and "UNSET" in out, out)

    # C6
    rc, out = go("--date", "2026-10-03", "--db", db)
    check("C6 zero objects listed -> rc 3 and says so", rc == 3 and "listed 0 candle objects" in out, out[-300:])
    only_qqq = ws._FakeS3({k: v for k, v in objs.items() if "sym=QQQ" in k})
    rc, out = go("--date", D, "--db", db, s3=only_qqq)
    check("C6 objects for other symbols only -> rc 3 and says so", rc == 3 and "none for SPX" in out, out[-300:])

    # C9
    ahead = cf._ts_ms_max() - int(time.time() * 1000)
    check("C9 the poison window is the feed's own", seed.TS_MS_MIN == cf.TS_MS_MIN
          and abs(ahead - seed.TS_MAX_AHEAD_MS) < 5_000, (seed.TS_MS_MIN, cf.TS_MS_MIN, ahead))

    # C11 / C12 — r237: a bar pushed before it closed is "partial"; an unreadable push time fails closed
    objs2 = {
        f"{P}/sym=SPX/interval=5m/7-g.json": env([bar(t0 + 30 * M, 7720.0, "5m")], "2026-10-02T14:00:32+00:00"),
        f"{P}/sym=SPX/interval=1m/8-h.json": env([bar(t0 + 40 * M, 7730.0)], "2026-10-02T14:11:00+00:00"),
        f"{P}/sym=SPX/interval=1m/9-i.json": env([bar(t0 + 50 * M, 7740.0)], "not-a-time"),
    }
    rc, out = go("--date", D, "--db", db, s3=ws._FakeS3(objs2))
    l5 = next((l for l in out.splitlines() if " 5m:" in l), "")
    l1 = next((l for l in out.splitlines() if " 1m:" in l), "")
    check("C11 a 5m bar pushed 32 s after it opened is refused as partial; a 1m bar pushed AT its end is kept",
          rc == 0 and "partial 1" in l5 and "1 would insert" in l1.replace("would-insert", "would insert"), out[-500:])
    check("C12 an unreadable push time is refused (no_push_time)", "no_push_time 1" in l1, l1)

    # C10
    rc, out = go("--date", D, "--db", os.path.join(d, "nope.db"))
    check("C10 a missing store is refused, rc 2", rc == 2 and "not found" in out, out)
    check("C10 feed_meta is never touched", meta_row is not None and meta_row[0] == 123.0, meta_row)

    if FAILED:
        print(f"\nRED — {sorted(set(FAILED))}")
        return 1
    print("\nGREEN — the seed only adds, only sane bars, only this box's instrument, only within retention")
    return 0


if __name__ == "__main__":
    sys.exit(main())
