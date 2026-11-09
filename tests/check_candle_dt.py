#!/usr/bin/env python3
"""
tests/check_candle_dt.py  v5.0
v5.0  2026-11-08  OTV5 r98 (CAP.6) — new. A daily bar is filed under its own session. dxFeed stamps a 1d candle at
      00:00 UTC of its session date; push_candles took dt from that stamp in ET (the evening before), so every daily
      bar landed one dt early: NVDA's 11-06 session close 186.68 sits in dt=2026-11-05 (measured in the warehouse 11-08).

  D1  candle_dt: a 1d stamp at 00:00 UTC of 2026-11-06 -> "2026-11-06" (was 2026-11-05); 1w and 1mo likewise UTC
  D2  candle_dt: intraday is unchanged - a 5m bar at 15:55 ET -> its ET date; 23:00 UTC (18:00 ET) stays the ET date;
      an interval it cannot read (7m) keeps the ET rule
  D3  the REAL push_candles on a scratch store files the 1d bar under dt=<session> and the 5m bar under its ET date
  BORN RED on b075b1e (r97): candle_dt did not exist and push_candles filed the 1d bar under dt=2026-11-05.

Run:  python3 tests/check_candle_dt.py
"""
import io
import os
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS = []

D1106 = 1_793_923_200_000          # 2026-11-06 00:00:00 UTC (dxFeed's stamp for the 11-06 session daily)


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


class _S3:
    def __init__(self):
        self.objs = {}

    def put_object(self, Bucket, Key, Body):
        self.objs[Key] = Body if isinstance(Body, bytes) else Body.encode()

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objs[Key])}

    def head_object(self, Bucket, Key):
        return {"ContentLength": len(self.objs[Key])}


def main():
    from warehouse import s3_push as SP
    fn = getattr(SP, "candle_dt", None)
    if fn is None:
        check("D1 candle_dt exists", False, "no candle_dt in warehouse/s3_push.py")
    else:
        d1 = (fn(D1106, "1d"), fn(D1106, "1w"), fn(D1106, "1mo"), fn(D1106, "d"))
        check("D1 a daily (and weekly/monthly) stamp files under its UTC date = the session",
              d1 == ("2026-11-06",) * 4, str(d1))
        t5 = D1106 + (20 * 3600 + 55 * 60) * 1000          # 20:55 UTC = 15:55 ET, 11-06
        t23 = D1106 + 23 * 3600 * 1000                     # 23:00 UTC = 18:00 ET, still 11-06 in ET
        t_early = D1106 + 2 * 3600 * 1000                  # 02:00 UTC 11-06 = 21:00 ET 11-05
        d2 = (fn(t5, "5m"), fn(t23, "1h"), fn(t_early, "1m"), fn(t_early, "7m"))
        check("D2 intraday keeps the ET date (and an unreadable interval keeps the ET rule)",
              d2 == ("2026-11-06", "2026-11-06", "2026-11-05", "2026-11-05"), str(d2))

    tmp = tempfile.mkdtemp(prefix="check_candle_dt_")
    db = os.path.join(tmp, "feed_store.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE candles (symbol TEXT, interval TEXT, ts_epoch_ms INTEGER,"
                " open REAL, high REAL, low REAL, close REAL, volume REAL)")
    con.execute("INSERT INTO candles VALUES ('NVDA','1d',?,191.19,194.9,185.22,186.68,1)", (D1106,))
    con.execute("INSERT INTO candles VALUES ('NVDA','5m',?,186,187,185,186.6,1)",
                (D1106 + (20 * 3600 + 50 * 60) * 1000,))
    con.commit()
    real_time = SP.time.time
    try:
        SP.time.time = lambda: (D1106 + 3 * 86_400_000) / 1000.0     # three days later: both bars long closed
        s3, ledger = _S3(), {}
        SP.push_candles(s3, "stub", db, ledger, "NVDA")
    finally:
        SP.time.time = real_time
    keys = sorted(s3.objs)
    k1d = [k for k in keys if "/interval=1d/" in k]
    k5m = [k for k in keys if "/interval=5m/" in k]
    check("D3 the real push_candles: 1d under dt=2026-11-06 (its session), 5m under its ET date 2026-11-06",
          len(k1d) == 1 and "/dt=2026-11-06/" in k1d[0] and len(k5m) == 1 and "/dt=2026-11-06/" in k5m[0], str(keys))

    print()
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {', '.join(PROBLEMS)}")
        return 1
    print("GREEN — check_candle_dt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
