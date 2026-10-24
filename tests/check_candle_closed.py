#!/usr/bin/env python3
"""
tests/check_candle_closed.py  v1.0
v1.0  2026-10-04  CNDL.1 — A CANDLE REACHES THE WAREHOUSE ONLY AFTER IT CLOSES.

  push_candles advanced its high-water mark to the newest bar it sent, and the
  next run selected only bars AFTER it, so a bar still forming when it was sent
  never had its final version pushed. Measured on S3: QQQ 2026-10-01, 78 of 78
  5m bars disagree with their own 1m bars (range understated $0.92 on average).
  Found by OTV4TEST's SPX-TEST agent (MSG-1004-03).

  Drives the REAL push_candles on a SCRATCH feed store through a stub S3 (no
  network, no ledger file) with the clock pinned:
  K1  a 5m bar still forming at push time is NOT pushed; the earlier, closed
      bars are, and the mark stops at the last CLOSED bar (the defect: the
      forming bar is shipped and the mark passes it)
  K2  the next run, after that bar closes, pushes it WITH ITS FINAL VALUES
  K3  1m: the same rule — the forming minute waits for the next run
  K4  an interval the table does not know is passed through unchanged
  BORN RED on otv4 0f852ee at K1 K2 K3.

Run:  python3 tests/check_candle_closed.py
"""
import io
import json
import os
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS = []


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


def _pushed_bars(s3, iv):
    out = {}
    for k, body in s3.objs.items():
        if f"/interval={iv}/" in k:
            for r in json.loads(body)["record"]:
                out[int(r["ts_epoch_ms"])] = r
    return out


def main():
    from warehouse import s3_push as SP
    tmp = tempfile.mkdtemp(prefix="check_candle_closed_")
    db = os.path.join(tmp, "feed_store.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE candles (symbol TEXT, interval TEXT, ts_epoch_ms INTEGER,"
                " open REAL, high REAL, low REAL, close REAL, volume REAL)")
    T0 = 1_790_870_400_000                       # a 5m boundary
    for i, (h, l) in enumerate([(101, 99), (102, 100), (103, 101)]):
        con.execute("INSERT INTO candles VALUES ('QQQ','5m',?,100,?,?,100,1)", (T0 + i * 300_000, h, l))
    for i in range(3):
        con.execute("INSERT INTO candles VALUES ('QQQ','1m',?,100,101,99,100,1)", (T0 + 600_000 + i * 60_000,))
    con.execute("INSERT INTO candles VALUES ('QQQ','7m',?,100,101,99,100,1)", (T0,))
    con.commit()

    real_time = SP.time.time
    try:
        # clock: 30 s into the THIRD 5m bar (and into the third 1m bar)
        now1 = (T0 + 600_000 + 120_000 + 30_000) / 1000.0
        SP.time.time = lambda: now1
        s3, ledger = _S3(), {}
        SP.push_candles(s3, "stub", db, ledger, "QQQ")
        got5 = _pushed_bars(s3, "5m")
        forming = T0 + 600_000
        check("K1 the forming 5m bar is withheld; the mark stops at the last closed bar",
              forming not in got5 and sorted(got5) == [T0, T0 + 300_000]
              and int(ledger.get("QQQ|5m", 0)) == T0 + 300_000,
              f"pushed={sorted(got5)} mark={ledger.get('QQQ|5m')}")
        got1 = _pushed_bars(s3, "1m")
        check("K3 1m: the forming minute waits for the next run",
              (T0 + 600_000 + 120_000) not in got1, f"pushed 1m={sorted(got1)}")
        got7 = _pushed_bars(s3, "7m")
        check("K4 an unknown interval passes through unchanged", T0 in got7, f"pushed 7m={sorted(got7)}")

        # the forming bar finishes with a new high, then the next run
        con.execute("UPDATE candles SET high=109 WHERE interval='5m' AND ts_epoch_ms=?", (forming,))
        con.commit()
        SP.time.time = lambda: (forming + 300_000 + 30_000) / 1000.0
        s3b = _S3()
        SP.push_candles(s3b, "stub", db, ledger, "QQQ")
        got5b = _pushed_bars(s3b, "5m")
        check("K2 after it closes, the bar is pushed with its FINAL high (109)",
              forming in got5b and float(got5b[forming]["high"]) == 109.0,
              f"pushed={ {k: v['high'] for k, v in got5b.items()} }")
    finally:
        SP.time.time = real_time
        con.close()
    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — every candle in the warehouse is a closed candle")
    return 0


if __name__ == "__main__":
    sys.exit(main())
