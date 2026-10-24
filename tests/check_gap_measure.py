#!/usr/bin/env python3
"""
tests/check_gap_measure.py  v1.0
v1.0  2026-10-24  CD.3 (DISC.4) — THE GAP IS MEASURED FROM THE STORE AND CLASSIFIED. Born red on OTV4TEST c825449
      (analysis/gap_class is absent; measure_gap cannot see a gap from a today-only frame; gap_class never emitted).
  G1  analysis.gap_class.classify: FLAT under flat_pct; UNDIRECTED with no prior direction; CONTINUATION with it;
      REVERSAL against it - a fixed table
  G2  bucket(): the operator's <0.25 / 0.25-0.75 / >0.75; range_gap_pct(): above the high, below the low, inside = 0.0
  G3  measure_gap with a TODAY-ONLY 5m frame and a feed store holding the prior 1d bar + today's 09:30 bar -> gap_pct
      from the STORE (source "store"), gap_class present, prior_high/low, range_gap_pct
  G4  the same frame with NO store -> None (never 0.0)
  G5  a 5m frame that DOES see yesterday, no store -> the SAME gap_pct as before (source "frame"), class present
  G6  the store prefers the NEWEST prior session before `day` (a Friday bar for a Monday), and ignores a 1d bar dated
      today or later
  G7  gap_measure imports nothing from tests.* (the one-lineage rule, §34: tests/ never ships to a box)
Run: python3 tests/check_gap_measure.py
"""
import ast
import os
import sys
import tempfile
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
FAILED = []
ET = ZoneInfo("America/New_York")


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _ms_utc(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def _ms_et(d, h, m):
    return int(datetime(d.year, d.month, d.day, h, m, tzinfo=ET).timestamp() * 1000)


def main() -> int:
    try:
        from analysis import gap_class as GC
    except Exception as exc:                                    # noqa: BLE001
        check("G1 analysis/gap_class imports", False, f"{type(exc).__name__}: {exc}")
        GC = None
    if GC is not None:
        table = [((0.10, 1), "FLAT"), ((-0.14, -1), "FLAT"), ((0.5, 0), "UNDIRECTED"), ((0.5, 1), "CONTINUATION"),
                 ((0.5, -1), "REVERSAL"), ((-0.9, -1), "CONTINUATION"), ((-0.9, 1), "REVERSAL")]
        bad = [(a, GC.classify(*a), w) for a, w in table if GC.classify(*a) != w]
        check("G1 classify: FLAT / UNDIRECTED / CONTINUATION / REVERSAL table", not bad, f"{bad}")
        ok2 = (GC.bucket(0.1) == "<0.25" and GC.bucket(0.25) == "0.25-0.75" and GC.bucket(0.75) == "0.25-0.75"
               and GC.bucket(0.76) == ">0.75" and GC.range_gap_pct(101.0, 100.0, 98.0, 99.0) == round(100.0 / 99.0, 4)
               and GC.range_gap_pct(97.0, 100.0, 98.0, 99.0) == round(-100.0 / 99.0, 4)
               and GC.range_gap_pct(99.0, 100.0, 98.0, 99.0) == 0.0 and GC.range_gap_pct(None, 1, 1, 1) is None)
        check("G2 bucket() and range_gap_pct()", ok2,
              f"{GC.bucket(0.25)} {GC.bucket(0.75)} {GC.range_gap_pct(101.0, 100.0, 98.0, 99.0)}")

    import pandas as pd
    from analysis import gap_measure as GM
    day = date(2026, 10, 19)                                    # a Monday; the prior session is Friday 10-16
    t0 = pd.Timestamp(datetime(2026, 10, 19, 9, 30, tzinfo=ET))
    today_only = pd.DataFrame({"open": [102.0, 102.3], "high": [102.5, 102.6], "low": [101.8, 102.0],
                               "close": [102.3, 102.4]}, index=[t0, t0 + pd.Timedelta(minutes=5)])

    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "feed.db")
        import data.candle_feed as cf
        fs = cf.FeedStore(db)
        for d_, o, h, l, c in ((date(2026, 10, 15), 99.0, 100.0, 98.0, 99.5),
                               (date(2026, 10, 16), 99.5, 101.0, 99.0, 100.0),       # Friday: the prior session
                               (date(2026, 10, 19), 102.0, 103.0, 101.5, 102.9)):     # today's bar: must be ignored
            fs.conn.execute("INSERT INTO candles VALUES ('QQQ','1d',?,?,?,?,?,0)", (_ms_utc(d_), o, h, l, c))
        fs.conn.execute("INSERT INTO candles VALUES ('QQQ','1m',?,102.0,102.5,101.8,102.3,0)", (_ms_et(day, 9, 30),))
        fs.conn.commit()
        fs.conn.close()
        try:
            g = GM.measure_gap(today_only, prior_dir=1, symbol="QQQ", day=day, db_path=db)
        except Exception as exc:                                # noqa: BLE001
            g = {"error": f"{type(exc).__name__}: {exc}"}
        want = round(100.0 * (102.0 - 100.0) / 100.0, 4)
        check("G3 today-only frame + store -> gap_pct from the store, class, prior high/low, range gap",
              g is not None and g.get("source") == "store" and g.get("gap_pct") == want
              and g.get("gap_class") == "CONTINUATION" and g.get("gap_bucket") == ">0.75"
              and g.get("prior_high") == 101.0 and g.get("prior_low") == 99.0
              and g.get("range_gap_pct") == round(100.0 * (102.0 - 101.0) / 100.0, 4) and g.get("prior_date") == "2026-10-16",
              f"{g}")
        g6 = getattr(GM, "prior_session_from_store", lambda *a: None)("QQQ", day, db)
        check("G6 the store's prior session is the newest bar BEFORE the day (Friday for a Monday), never today's",
              g6 is not None and g6["prior_date"] == "2026-10-16" and g6["prior_close"] == 100.0, f"{g6}")

    try:
        g4 = GM.measure_gap(today_only, prior_dir=1, symbol="QQQ", day=day, db_path=os.path.join(tempfile.gettempdir(), "nope.db"))
    except Exception as exc:                                    # noqa: BLE001
        g4 = {"error": f"{type(exc).__name__}: {exc}"}
    check("G4 today-only frame, no store -> None, never 0.0", g4 is None, f"{g4}")

    y = pd.Timestamp(datetime(2026, 10, 16, 15, 55, tzinfo=ET))
    sees = pd.DataFrame({"open": [99.9, 102.0, 102.3], "high": [100.1, 102.5, 102.6], "low": [99.7, 101.8, 102.0],
                         "close": [100.0, 102.3, 102.4]}, index=[y, t0, t0 + pd.Timedelta(minutes=5)])
    g5 = GM.measure_gap(sees, prior_dir=-1)
    check("G5 a frame that sees yesterday, no store -> the same gap_pct as before (frame), class REVERSAL",
          g5 is not None and g5.get("source") == "frame" and g5.get("gap_pct") == want
          and g5.get("gap_class") == "REVERSAL" and "range_gap_pct" not in g5, f"{g5}")

    src = open(os.path.join(ROOT, "analysis", "gap_measure.py")).read()
    tree = ast.parse(src)
    mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    mods += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    check("G7 gap_measure imports nothing from tests.*", not [m for m in mods if m.startswith("tests")], f"{mods}")

    print(f"\n{'GREEN' if not FAILED else 'RED — ' + str(sorted(set(FAILED)))}")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
