#!/usr/bin/env python3
"""
tests/check_prime_ramp.py  v1.0
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
Run: python3 tests/check_prime_ramp.py      (OT_PRIME_TOOL=<path> points it at another copy - born-red runs)
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
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
os.environ["OT_INSTRUMENT"] = "SPX"
_SCRATCH = tempfile.mkdtemp(prefix="primechk_")
atexit.register(shutil.rmtree, _SCRATCH, True)
os.environ.setdefault("OT_LOG_FILE", os.path.join(_SCRATCH, "bot.log"))

FAILED = []
M = 60_000


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def utc(y, mo, d, h, mi):
    return int(datetime(y, mo, d, h, mi, tzinfo=timezone.utc).timestamp() * 1000)


def main() -> int:
    tool_path = os.environ.get("OT_PRIME_TOOL") or os.path.join(ROOT, "tools", "prime_ramp.py")
    try:
        spec = importlib.util.spec_from_file_location("prime_tool", tool_path)
        pr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pr)
    except Exception as exc:                                    # noqa: BLE001
        check("R0 the tool loads", False, f"{type(exc).__name__}: {exc}")
        print(f"\nRED — {sorted(set(FAILED))}")
        return 1
    import warehouse_source as ws
    import data.candle_feed as cf

    now_ms = utc(2026, 10, 5, 16, 0)            # Mon 12:00 ET; the last closed session is Fri 10-02
    D = "2026-10-02"
    o930 = utc(2026, 10, 2, 13, 30)             # 09:30 ET
    o900 = utc(2026, 10, 2, 13, 0)              # 09:00 ET
    P = f"{ws.PREFIX}/candles/dt={D}"
    late = "2026-10-02T21:00:00+00:00"          # after every bar's end and after the 16:00 ET bell

    def px(ts):                                 # a deterministic, non-flat price path
        k = (ts - o900) // M
        return 7700.0 + (k % 7) * 1.5 - (k % 3) * 0.75

    def bar(ts, sym="SPX", iv="1m", p=None):
        p = px(ts) if p is None else p
        return {"symbol": sym, "interval": iv, "ts_epoch_ms": ts, "open": p, "high": p + 2,
                "low": p - 2, "close": p + 0.5, "volume": 10.0}

    def env(rows, stamp, sym="SPX"):
        return json.dumps({"schema_version": 1, "datatype": "candles", "symbol": sym, "dt": D,
                           "pushed_at_utc": stamp, "record": rows}).encode()

    rth = [o930 + k * M for k in range(60)]                    # 09:30-10:29
    partial_ts = o930 + 60 * M                                 # 10:30, pushed mid-bar
    ext_full = [o900 + k * M for k in range(60)]               # 09:00-09:59 every minute
    ext_gap = [o900 + 60 * M + k * M for k in range(60) if k != 17]   # 10:00-10:59 missing 10:17
    d1_ok = utc(2026, 10, 1, 0, 0)                             # 10-01's session, pushed after its bell
    d1_part = utc(2026, 10, 2, 0, 0)                           # 10-02's session, pushed 14:00 ET
    objs = {
        f"{P}/sym=SPX/interval=1m/1-a.json": env([bar(t) for t in rth], late),
        f"{P}/sym=SPX/interval=1m/2-b.json": env([bar(partial_ts)], "2026-10-02T14:30:20+00:00"),
        f"{P}/sym=SPX/interval=5m/3-c.json": env([bar(o930, iv="5m", p=1.0)], late),          # forming junk
        f"{P}/sym=SPX_EXT/interval=1m/4-d.json": env([bar(t, "SPX_EXT") for t in ext_full + ext_gap], late,
                                                      sym="SPX_EXT"),
        # R13: warehouse 1h bars for an hour with NO 1m (10-01 11:00 ET): one complete, one pushed mid-bar
        f"{P}/sym=SPX/interval=1h/7-g.json": env([bar(utc(2026, 10, 1, 15, 0), iv="1h", p=7650.0)],
                                                  "2026-10-01T16:00:05+00:00"),
        f"{P}/sym=SPX/interval=1h/8-h.json": env([bar(utc(2026, 10, 1, 16, 0), iv="1h", p=7660.0)],
                                                  "2026-10-01T16:20:00+00:00"),
        f"{P}/sym=SPX/interval=1d/5-e.json": env([bar(d1_ok, iv="1d")], "2026-10-02T03:00:00+00:00"),
        f"{P}/sym=SPX/interval=1d/6-f.json": env([bar(d1_part, iv="1d")], "2026-10-02T18:00:00+00:00"),
    }
    fake = ws._FakeS3(objs)

    d = tempfile.mkdtemp(prefix="store_", dir=_SCRATCH)
    db = os.path.join(d, "feed_store.db")
    fs = cf.FeedStore(db)
    held_ts = rth[3]
    fs.conn.execute("INSERT INTO candles VALUES ('SPX','1m',?,1,1,1,1,0)", (held_ts,))
    fs.conn.execute("INSERT INTO feed_meta (symbol, interval, last_write_epoch) VALUES ('SPX','1m',123.0)")
    fs.conn.commit()
    fs.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    fs.conn.close()

    def go(*argv, s3=fake, now=now_ms, path=db):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = pr.run(list(argv) + ["--db", path], s3=s3, now_ms=now)
        return rc, buf.getvalue()

    def rows(sym, iv, path=db):
        c = sqlite3.connect(path)
        r = {t: (o, h, l, cl, v) for t, o, h, l, cl, v in c.execute(
            "SELECT ts_epoch_ms, open, high, low, close, volume FROM candles WHERE symbol=? AND interval=?", (sym, iv))}
        c.close()
        return r

    def digest(path=db):
        """The store's CONTENT (every candles and feed_meta row). Not the bytes: a read-only reader of a WAL
        database may create the -shm/-wal side files, which is not a write."""
        c = sqlite3.connect(path)
        h = hashlib.sha256()
        for t in ("candles", "feed_meta"):
            for r in c.execute(f"SELECT * FROM {t} ORDER BY 1, 2, 3"):
                h.update(repr(r).encode())
        c.close()
        return h.hexdigest()

    # R1
    before = digest()
    rc, out = go()
    check("R1 a dry run writes nothing and exits 0", rc == 0 and digest() == before and "DRY RUN" in out,
          f"rc {rc}, bytes changed {digest() != before}")

    # R2
    rc, out = go("--apply")
    r1 = rows("SPX", "1m")
    check("R2 apply: complete 1m written, partial refused, held row unchanged",
          rc == 0 and all(t in r1 for t in rth) and partial_ts not in r1 and r1[held_ts] == (1, 1, 1, 1, 0),
          f"rc {rc}, missing {[t for t in rth if t not in r1][:3]}, partial {partial_ts in r1}, "
          f"held {r1.get(held_ts)}\n{out}")

    # R3 - independent aggregation of the 1m that was written
    def agg(src, start, n):
        ms = [start + k * M for k in range(n)]
        if any(m not in src for m in ms):
            return None
        return (src[ms[0]][0], max(src[m][1] for m in ms), min(src[m][2] for m in ms), src[ms[-1]][3],
                sum(src[m][4] for m in ms))
    r5, r15 = rows("SPX", "5m"), rows("SPX", "15m")
    exp5 = {o930 + k * 5 * M: agg(r1, o930 + k * 5 * M, 5) for k in range(12)}
    exp15 = {o930 + k * 15 * M: agg(r1, o930 + k * 15 * M, 15) for k in range(4)}
    ok3 = (all(r5.get(t) == v for t, v in exp5.items()) and all(r15.get(t) == v for t, v in exp15.items())
           and r5.get(o930, (None,))[0] != 1.0 and (o930 + 60 * M) not in r5)
    check("R3 5m/15m built from the written 1m; the warehouse's forming 5m never written; incomplete not written",
          ok3, f"5m {sorted(r5)[:3]} vs {list(exp5)[:3]}; 09:30 5m {r5.get(o930)}; 10:30 5m {(o930 + 60*M) in r5}")

    # R4
    h1 = rows("SPX", "1h")
    exp_h = agg(r1, o930, 30)
    h1x = rows("SPX_EXT", "1h")
    e1 = rows("SPX_EXT", "1m")
    exp_hx = agg(e1, o900, 60)
    check("R4 SYM 09:00 hour = 09:30-09:59 only; SYM_EXT hour needs every minute (10:00 EXT hour missing 10:17 "
          "is not written)",
          h1.get(o900) == exp_h and h1x.get(o900) == exp_hx and (o900 + 60 * M) not in h1x,
          f"SPX 09:00h {h1.get(o900)} vs {exp_h}; EXT 09:00h {h1x.get(o900)} vs {exp_hx}; "
          f"EXT 10:00h written {(o900 + 60 * M) in h1x}")

    # R5
    rd = rows("SPX", "1d")
    check("R5 1d: pushed after the bell written, pushed before it refused; < 55 daily bars said",
          d1_ok in rd and d1_part not in rd and "sma50_mtf 1d stays silent" in out and "partial 1" in out,
          f"ok {d1_ok in rd}, partial {d1_part in rd}\n{out}")

    # R6
    snap = {iv: len(rows("SPX", iv)) for iv in ("1m", "5m", "15m", "1h", "1d")}
    rc, out = go("--apply")
    snap2 = {iv: len(rows("SPX", iv)) for iv in ("1m", "5m", "15m", "1h", "1d")}
    check("R6 a re-run inserts 0", rc == 0 and snap == snap2 and " 0 inserted" in out, f"{snap} -> {snap2}")

    # R7
    rc_a, _ = go("--symbol", "QQQ")
    os.environ["OT_INSTRUMENT"] = ""
    try:
        from utils import instrument as _ins
        unset = _ins.box_instrument() == _ins.UNSET
        rc_b, _ = go() if unset else (2, "")
    finally:
        os.environ["OT_INSTRUMENT"] = "SPX"
    check("R7 a disagreeing --symbol and an UNSET instrument are refused (rc 2)", rc_a == 2 and rc_b == 2,
          f"rc {rc_a} / {rc_b}")

    # R8
    d2 = tempfile.mkdtemp(prefix="store8_", dir=_SCRATCH)
    db2 = os.path.join(d2, "feed_store.db")
    cf.FeedStore(db2).conn.close()
    other = ws._FakeS3({k.replace("sym=SPX/", "sym=QQQ/").replace("sym=SPX_EXT/", "sym=QQQ_EXT/"):
                        v.replace(b'"SPX', b'"QQQ') for k, v in objs.items()})
    b2 = digest(db2)
    rc, out = go("--apply", s3=other, path=db2)
    check("R8 no objects for the symbol -> rc 3, nothing written", rc == 3 and digest(db2) == b2, f"rc {rc}\n{out}")

    # R9
    samples = [("SPX", o900, 60), ("SPX", o930, 5), ("SPX_EXT", o900, 60), ("SPX", utc(2026, 10, 3, 14, 0), 60),
               ("SPX", utc(2026, 10, 2, 19, 0), 60)]
    try:
        diff = [(s, t, sp) for s, t, sp in samples if pr.required_minutes(s, t, sp) != cf._referee_minutes(s, t, sp)]
    except Exception as exc:                                    # noqa: BLE001
        diff = [repr(exc)]
    check("R9 required_minutes == candle_feed._referee_minutes", not diff, f"{diff}")

    # R10: a store whose last closed session (10-02) has no 1m and a warehouse with only 10-01
    d3 = tempfile.mkdtemp(prefix="store10_", dir=_SCRATCH)
    db3 = os.path.join(d3, "feed_store.db")
    cf.FeedStore(db3).conn.close()
    D1 = "2026-10-01"
    o930b = utc(2026, 10, 1, 13, 30)
    old = ws._FakeS3({f"{ws.PREFIX}/candles/dt={D1}/sym=SPX/interval=1m/1.json":
                      json.dumps({"symbol": "SPX", "dt": D1, "pushed_at_utc": "2026-10-01T21:00:00+00:00",
                                  "record": [bar(o930b + k * M) for k in range(5)]}).encode()})
    rc, out = go("--apply", s3=old, path=db3)
    check("R10 the last closed session with no 1m -> rc 4, said", rc == 4 and "NOT primed" in out, f"rc {rc}\n{out}")

    # R13
    h1b = rows("SPX", "1h")
    check("R13 a COMPLETE warehouse 1h bar fills an hour with no 1m; one pushed mid-bar is refused; built wins",
          h1b.get(utc(2026, 10, 1, 15, 0), (None,))[0] == 7650.0 and utc(2026, 10, 1, 16, 0) not in h1b
          and h1b.get(o900) == exp_h,
          f"15:00Z {h1b.get(utc(2026, 10, 1, 15, 0))}, 16:00Z written {utc(2026, 10, 1, 16, 0) in h1b}")

    # R12: the study corpus first, the warehouse raw 1d for sessions after it, the forming day from neither
    d4 = tempfile.mkdtemp(prefix="store12_", dir=_SCRATCH)
    db4 = os.path.join(d4, "feed_store.db")
    cf.FeedStore(db4).conn.close()
    csv_body = ("date,open,high,low,close,volume,source,symbol,interval,pulled_at\n"
                "2026-09-29,7600,7610,7590,7605,0,dxfeed_tastytrade,SPX,1d,x\n"
                "2026-09-30,7605,7620,7600,7615,0,dxfeed_tastytrade,SPX,1d,x\n"
                "2026-10-05,7700,7710,7690,7705,0,dxfeed_tastytrade,SPX,1d,x\n").encode()   # 10-05: bell not rung
    with_study = ws._FakeS3(dict(objs, **{"study/candles_1d/sym=SPX/candles_1d.csv": csv_body}))
    rc, out = go("--apply", s3=with_study, path=db4)
    rd4 = rows("SPX", "1d", path=db4)
    s29, s30 = utc(2026, 9, 29, 0, 0), utc(2026, 9, 30, 0, 0)
    check("R12 1d: study corpus first (closed days only), raw 1d adds the later session, the source is named",
          s29 in rd4 and s30 in rd4 and d1_ok in rd4 and utc(2026, 10, 5, 0, 0) not in rd4
          and d1_part not in rd4 and rd4[s30][3] == 7615.0 and "study corpus 2 closed day(s)" in out
          and "1 row(s) refused" in out,
          f"rc {rc}, have {sorted(rd4)}\n{[ln for ln in out.splitlines() if ' 1d:' in ln]}")
    rc0, out0 = go(s3=fake)
    check("R12b no study corpus: the line says it was not read and raw stands alone",
          "candles_1d.csv not read" in out0, f"{[ln for ln in out0.splitlines() if ' 1d:' in ln]}")

    # R11
    c = sqlite3.connect(db)
    fm = c.execute("SELECT symbol, interval, last_write_epoch FROM feed_meta").fetchall()
    c.close()
    check("R11 feed_meta untouched", fm == [("SPX", "1m", 123.0)], f"{fm}")

    print(f"\n{'GREEN' if not FAILED else 'RED — ' + str(sorted(set(FAILED)))}")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
