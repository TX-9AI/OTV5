#!/usr/bin/env python3
"""
tests/check_half_day_rth.py  v5.0
v5.0  2026-10-25  (LVL.20) — PORTED FROM otv4 (its v1.0, r494 / FEED.11) WITH NO CHECK CHANGED: the shared half of
      LVL.20. Born red on f006eed at H1 H2 H3 H4 (H5-H8 are controls, green on both).
v1.0  2026-10-20  otv4 r494 / FEED.11 — A HALF DAY'S RTH ENDS AT ITS BELL.

  data/candle_feed._within_rth ended every intraday window at a fixed 16:00
  (1h: 16:30), so on 2026-11-27 and 12-24 (13:00 close) the 13:00-16:00 bars
  went to the plain RTH series. Found by OTV4TEST's 10-18 audit H6
  (MSG-QQQ-1018-18); its gate shape, plus the unchanged cases pinned.

  Drives the REAL candle_feed._within_rth:
  H1  2026-11-27 1m 12:59 -> RTH; 13:00 -> not
  H2  2026-11-27 1h 13:00 -> RTH (the hour row keeps +30: ends 13:30); 14:00 -> not
  H3  2026-11-27 5m 12:55 / 15m 12:45 -> RTH; 5m 13:00 / 15m 13:00 -> not
  H4  2026-12-24 1m 12:59 -> RTH; 13:00 -> not
  H5  UNCHANGED full day 2026-11-25: 1m 15:59 -> RTH, 16:00 -> not; 1h 16:00 -> RTH
  H6  UNCHANGED: 09:29 is not RTH and 09:30 is (11-27 and 11-25); 1h 09:00 is
  H7  UNCHANGED: a weekend is never RTH; a 1d bar always is; a non-trading
      weekday (2026-12-25) reads like a full day (a separate ruling)
  H8  a market_calendar fault inside _within_rth keeps the 16:00 window (the
      bar is still written; QQQ-TEST critique MSG-QQQ-1020-11)

Run:  python3 tests/check_half_day_rth.py   (exit 0 green, 1 red)
"""
import glob as _glob
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

ET = ZoneInfo("America/New_York")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def ms(day, hm):
    h, m = (int(x) for x in hm.split(":"))
    y, mo, d = (int(x) for x in day.split("-"))
    return int(datetime(y, mo, d, h, m, tzinfo=ET).timestamp() * 1000)


def main():
    from data import candle_feed as cf
    w = cf._within_rth

    def cases(name, rows):
        bad = [f"{d} {iv} {hm} -> {w(ms(d, hm), iv)} (want {want})"
               for d, iv, hm, want in rows if w(ms(d, hm), iv) is not want]
        check(name, not bad, "; ".join(bad))

    H = "2026-11-27"
    cases("H1 11-27 1m: 12:59 is RTH, 13:00 is not",
          [(H, "1m", "12:59", True), (H, "1m", "13:00", False), (H, "1m", "15:30", False)])
    cases("H2 11-27 1h: 13:00 is RTH (ends 13:30), 14:00 is not",
          [(H, "1h", "13:00", True), (H, "1h", "14:00", False), (H, "1h", "15:00", False)])
    cases("H3 11-27 5m/15m: the last bar before the bell is RTH, the bell is not",
          [(H, "5m", "12:55", True), (H, "5m", "13:00", False),
           (H, "15m", "12:45", True), (H, "15m", "13:00", False)])
    cases("H4 12-24 1m: 12:59 is RTH, 13:00 is not",
          [("2026-12-24", "1m", "12:59", True), ("2026-12-24", "1m", "13:00", False)])
    F = "2026-11-25"
    cases("H5 unchanged full day 11-25: 15:59 RTH, 16:00 not; 1h 16:00 RTH",
          [(F, "1m", "15:59", True), (F, "1m", "16:00", False), (F, "5m", "15:55", True),
           (F, "1h", "16:00", True), (F, "1h", "16:30", False)])
    cases("H6 unchanged open: 09:29 not, 09:30 RTH; 1h 09:00 RTH",
          [(H, "1m", "09:29", False), (H, "1m", "09:30", True), (F, "1m", "09:29", False),
           (F, "1m", "09:30", True), (H, "1h", "09:00", True), (F, "1h", "08:00", False)])
    cases("H7 unchanged: weekend never, 1d always, 12-25 reads like a full day",
          [("2026-11-28", "1m", "10:00", False), ("2026-11-28", "1d", "00:00", True),
           (H, "1d", "00:00", True), ("2026-12-25", "1m", "15:59", True),
           ("2026-12-25", "1m", "16:00", False)])
    from utils import market_calendar as mc
    real = mc.close_shift_minutes

    def boom(d=None):
        raise RuntimeError("calendar fault")
    mc.close_shift_minutes = boom
    try:
        cases("H8 calendar fault: 11-27 reads the 16:00 window, never raises",
              [(H, "1m", "15:59", True), (H, "1m", "16:00", False), (H, "1h", "16:00", True)])
    except Exception as exc:                                 # noqa: BLE001
        check("H8 calendar fault: _within_rth must not raise", False, repr(exc))
    finally:
        mc.close_shift_minutes = real

    print()
    if FAILED:
        print(f"RED: {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
