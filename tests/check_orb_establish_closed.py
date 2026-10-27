#!/usr/bin/env python3
"""
tests/check_orb_establish_closed.py  v5.0
v5.0  2026-10-27  OTV5 r40 (ORP.2) — THE OPENING RANGE IS ESTABLISHED ONLY ONCE IT IS CLOSED.
      CRM 2026-10-26: at 09:35:01 ET get_orb_range established H=250.14 from the still-forming 09:30 5m row (the
      feed store writes forming bars); the 09:34 minute closed at its high, 250.38. The fixture is CRM's real 10-26
      bars, served through a fake fetch_candles with the clock pinned.

  C1  09:35:01, the 09:34 1m bar still forming (high 250.14 so far), no 09:35 row: IN_PROGRESS, not ESTABLISHED
  C2  09:35:12, 09:34 final (250.38) and a 09:35 1m row: ESTABLISHED at the official print 250.38 / 247.76
  C3  the five bars and a 09:35 row but only 09:35:04 (inside SETTLE_S): IN_PROGRESS
  C4  no 1m frame at all: the 5m row alone is ESTABLISHED only once a later 5m row exists and it is 09:36
  C5  pre-open is EXPIRED and inside the opening window is IN_PROGRESS, both carrying the prior range (unchanged)

Born red on f3e3072 at C1 (established 250.14 at 09:35:01), C3 and C4.
Run:  python3 tests/check_orb_establish_closed.py
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
ET = ZoneInfo("America/New_York")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


# CRM 2026-10-26, real (feed_store candles); the prior day's 09:30 5m row is a stand-in for the carry
M1 = [("09:30", 247.76, 249.474, 247.76, 249.095), ("09:31", 249.095, 249.83, 248.16, 248.4115),
      ("09:32", 248.2, 249.08, 247.89, 249.08), ("09:33", 249.135, 249.96, 249.135, 249.83),
      ("09:34", 249.91, 250.38, 249.375, 250.38), ("09:35", 250.355, 250.99, 249.8, 249.8)]
PRIOR_5M = ("2026-10-23", "09:30", 245.0, 246.5, 244.2, 246.0)


def _frame(rows):
    import pandas as pd
    idx = [datetime.strptime(f"{d} {hm}", "%Y-%m-%d %H:%M").replace(tzinfo=ET) for d, hm, *_ in rows]
    return pd.DataFrame([{"open": o, "high": h, "low": l, "close": c, "volume": 1.0} for *_, o, h, l, c in rows],
                        index=pd.DatetimeIndex(idx))


def main():
    import analysis.get_orb_range as G
    day = "2026-10-26"
    forming_1m = [(day, *r) for r in M1[:4]] + [(day, "09:34", 249.91, 250.14, 249.375, 250.14)]
    final_1m = [(day, *r) for r in M1]
    forming_5m = [PRIOR_5M, (day, "09:30", 247.76, 250.14, 247.76, 250.14)]
    final_5m = [PRIOR_5M, (day, "09:30", 247.76, 250.38, 247.76, 250.38), (day, "09:35", 250.355, 250.99, 248.68, 248.92)]

    def run(m1, m5, hh, mm, ss):
        frames = {"1m": _frame(m1) if m1 else None, "5m": _frame(m5)}
        G.fetch_candles = lambda sym, iv, n: frames[iv]
        t = datetime(2026, 10, 26, hh, mm, ss, tzinfo=ET)

        class _Clock(datetime):                              # the clock pinned for code that reads datetime.now
            @classmethod
            def now(cls, tz=None):
                return t
        G.datetime = _Clock
        import inspect
        if "now" in inspect.signature(G.resolve_orb_range).parameters:
            return G.resolve_orb_range("CRM", now=t)
        return G.resolve_orb_range("CRM")

    r = run(forming_1m, forming_5m, 9, 35, 1)
    check("C1 09:35:01, 09:34 still forming, no 09:35 row: IN_PROGRESS (carrying the prior)",
          r["status"] == "IN_PROGRESS" and r["date"] == "2026-10-23", f"{r['status']} {r['date']} H={r['high']}")
    r = run(final_1m, final_5m, 9, 35, 12)
    check("C2 09:35:12 with 09:34 final and a 09:35 row: ESTABLISHED at the official print 250.38 / 247.76",
          r["status"] == "ESTABLISHED" and r["date"] == day and r["high"] == 250.38 and r["low"] == 247.76,
          f"{r['status']} {r['date']} H={r['high']} L={r['low']}")
    r = run(final_1m, final_5m, 9, 35, 4)
    check("C3 09:35:04 (inside SETTLE_S): IN_PROGRESS", r["status"] == "IN_PROGRESS", r["status"])
    r1 = run(None, final_5m, 9, 35, 30)
    r2 = run(None, final_5m, 9, 36, 5)
    r3 = run(None, forming_5m, 9, 40, 0)
    check("C4 no 1m: the 5m row is ESTABLISHED only with a later 5m row and from 09:36",
          r1["status"] == "IN_PROGRESS" and r2["status"] == "ESTABLISHED" and r2["high"] == 250.38
          and r3["status"] == "IN_PROGRESS", f"{r1['status']} {r2['status']} H={r2['high']} {r3['status']}")
    r1 = run(None, [PRIOR_5M], 9, 10, 0)                       # pre-open: only the prior day is on the feed
    r2 = run(final_1m[:2], [PRIOR_5M, forming_5m[1]], 9, 32, 0)
    check("C5 pre-open EXPIRED, inside the window IN_PROGRESS, both the prior range",
          r1["status"] == "EXPIRED" and r2["status"] == "IN_PROGRESS" and r1["date"] == r2["date"] == "2026-10-23",
          f"{r1['status']} {r2['status']}")

    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
