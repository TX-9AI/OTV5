#!/usr/bin/env python3
"""
tests/check_orb_range_quiet.py  v5.0
v5.0  2026-10-28  OTV5 r47 (ORB.9) — NO 5m BARS OUTSIDE RTH IS NOT A WARNING; INSIDE RTH IT STILL IS.
      SPX logged "ORB range fetch failed: ERROR: no 5m data returned for SPX" at WARNING at the 09:15 wake
      (2026-10-27 13:15:34 UTC) and after the bell (2026-10-26 20:21 / 20:50 UTC), when no 5m bars are expected.
      Driven through the REAL main._fetch_orb_range, which runs the REAL analysis/get_orb_range.py as a
      subprocess against an empty scratch feed store (its real "no 5m data" exit 1); only the clock is pinned,
      through main's own is_rth (utils.time_utils.is_rth, the calendar and the day's bell, at a fixed moment).

  Q1  09:15 ET Tue 2026-10-27 (the wake): no WARNING; one INFO line naming the case
  Q2  16:10 ET Tue 2026-10-27 (after the bell): no WARNING
  Q3  10:00 ET Tue 2026-10-27 (inside RTH): the WARNING "ORB range fetch failed: ... no 5m data" is kept
  Q4  13:30 ET Fri 2026-11-27 (after a half day's 13:00 bell): no WARNING
  Q5  any OTHER failure (stderr "ERROR writing ...") outside RTH is still a WARNING
  Q6  every case returns False (never latches) - polling is unchanged

Born red on b78fc8f at Q1, Q2 and Q4.
Run:  python3 tests/check_orb_range_quiet.py
"""
import datetime as D
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["OT_INSTRUMENT"] = "SPX"
_s = tempfile.mkdtemp(prefix="check_orb_range_quiet.")
os.environ["OT_FEED_DB"] = os.path.join(_s, "feed.db")       # never created: the store holds no 5m bars
os.environ.setdefault("OT_TRADES_DB", os.path.join(_s, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_s, "bot.log"))
ET = ZoneInfo("America/New_York")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(); self.recs = []

    def emit(self, record):
        self.recs.append((record.levelno, record.getMessage()))


def main():
    import main as M
    from utils.time_utils import is_rth as real_is_rth
    cap = _Cap(); lg = M.logger; lg.addHandler(cap); lg.setLevel(logging.DEBUG)
    real_run = subprocess.run

    def at(when, run=None):
        cap.recs.clear()
        _is = M.is_rth
        M.is_rth = lambda now=None: real_is_rth(when)
        if run is not None:
            subprocess.run = run
        try:
            ret = M._fetch_orb_range("SPX")
        finally:
            M.is_rth, subprocess.run = _is, real_run
        orb = [(lv, m) for lv, m in cap.recs if "ORB range" in m]
        warns = [m for lv, m in orb if lv >= logging.WARNING]
        return ret, orb, warns

    rets = []
    r1, o1, w1 = at(D.datetime(2026, 10, 27, 9, 15, 34, tzinfo=ET)); rets.append(r1)
    info1 = [m for lv, m in o1 if lv == logging.INFO and "no 5m" in m]
    check("Q1 09:15 wake: no WARNING, one INFO line naming the case", not w1 and len(info1) == 1,
          f"warn={w1} info={info1}")
    r2, o2, w2 = at(D.datetime(2026, 10, 27, 16, 10, tzinfo=ET)); rets.append(r2)
    check("Q2 16:10 after the bell: no WARNING", not w2 and len(o2) == 1, f"{o2}")
    r3, o3, w3 = at(D.datetime(2026, 10, 27, 10, 0, tzinfo=ET)); rets.append(r3)
    check("Q3 10:00 inside RTH: the 'no 5m data' WARNING is kept",
          len(w3) == 1 and "ORB range fetch failed" in w3[0] and "no 5m data returned for SPX" in w3[0], f"{o3}")
    r4, o4, w4 = at(D.datetime(2026, 11, 27, 13, 30, tzinfo=ET)); rets.append(r4)
    check("Q4 13:30 after a half day's 13:00 bell: no WARNING", not w4 and len(o4) == 1, f"{o4}")

    def other(*a, **k):
        return SimpleNamespace(returncode=1, stdout="", stderr="ERROR writing /x/orb_range.json: disk full")
    r5, o5, w5 = at(D.datetime(2026, 10, 27, 9, 15, tzinfo=ET), run=other); rets.append(r5)
    check("Q5 any other failure outside RTH is still a WARNING", len(w5) == 1 and "ERROR writing" in w5[0], f"{o5}")
    check("Q6 every case returns False (never latches)", rets == [False] * 5, f"{rets}")

    lg.removeHandler(cap)
    shutil.rmtree(_s, ignore_errors=True)
    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
