#!/usr/bin/env python3
"""tests/check_vwap_closed_bars.py  v1.0
v1.0  2026-10-12  OTV4TEST r274 (VWAP.2) — THE SESSION VWAP FOLDS ONLY CLOSED 1m BARS.
      Measured 2026-10-12 14:52 ET on QQQ-TEST: the bot's VWAP summed 940,524 shares where the
      session's closed 1m bars held 7,138,959 (13%); over 25 sessions its value sat a median
      0.097 and up to 1.729 (09-28) away from the closed-bar VWAP. derived/indicators.py
      folded each bar the FIRST time it saw it - seconds into the minute, while it was still
      forming - then skipped it as already folded, so every minute counted only its first
      seconds. The operator, 2026-10-12 14:52 ET: "I want this to be the ATP butterfly and based
      on correct VWAP plus ranging. I know we've struggled a little bit with our VWAP formulas."

  V1  a forming bar is NOT folded; when it closes it IS, complete: after the two ticks the
      VWAP and the summed volume equal the closed-bar reference exactly
  V2  a bar whose minute ended less than the grace ago is still treated as forming
  V3  nothing before the 09:30 anchor is folded, and no bar is folded twice
Drives the REAL IndicatorEngine._accumulate_vwap; the cold-start deep fetch is stubbed to
return the same frame (no network).
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pandas as pd

FAILED, RAN = [], []
def check(name, ok, detail=""):
    RAN.append(name); print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  [{detail}]"))
    if not ok: FAILED.append(name.split()[0])

def frame(rows):
    idx = pd.DatetimeIndex([pd.Timestamp(t, tz="America/New_York") for t, *_ in rows])
    return pd.DataFrame([dict(open=o, high=h, low=l, close=c, volume=v) for _, o, h, l, c, v in rows], index=idx)

def ref(rows):
    pv = sum((h + l + c) / 3 * v for _, o, h, l, c, v in rows); vv = sum(v for *_, v in rows)
    return pv / vv, vv

def main():
    import data.market_data as _md
    import derived.indicators as _ind
    from derived.indicators import IndicatorEngine
    _clock = [0.0]
    _real_time = _ind.time.time
    class _T:
        @staticmethod
        def time(): return _clock[0]
    _ind.time = _T                        # the engine reads ITS module clock; nothing else is patched
    def acc(e, df, now):
        _clock[0] = now
        return e._accumulate_vwap(df, "QQQ")
    pre = ("2026-10-08 09:29", 99.0, 99.5, 98.5, 99.0, 50000.0)
    b0 = ("2026-10-08 09:30", 100.0, 101.0, 99.5, 100.5, 1000.0)
    b1 = ("2026-10-08 09:31", 100.5, 101.5, 100.0, 101.0, 2000.0)
    b2_part = ("2026-10-08 09:32", 101.0, 101.2, 100.9, 101.1, 100.0)
    b2_full = ("2026-10-08 09:32", 101.0, 103.0, 100.5, 102.5, 3000.0)
    b3_part = ("2026-10-08 09:33", 102.5, 102.6, 102.4, 102.5, 50.0)
    t = lambda s: pd.Timestamp(s, tz="America/New_York").timestamp()

    tick1 = frame([pre, b0, b1, b2_part])
    tick2 = frame([pre, b0, b1, b2_full, b3_part])
    keep = getattr(_md, "fetch_candles", None)
    _md.fetch_candles = lambda *a, **k: tick1
    try:
        e = IndicatorEngine(store=None, symbol="QQQ")
        acc(e, tick1, t("2026-10-08 09:32:20"))
        v2, pv2, sv2, _ = acc(e, tick2, t("2026-10-08 09:33:10"))
        r, rv = ref([b0, b1, b2_full])
        check("V1 a forming bar waits; once closed it is folded complete (VWAP and volume = reference)",
              v2 is not None and abs(v2 - r) < 1e-9 and abs(sv2 - rv) < 1e-6,
              f"vwap={v2} ref={r:.6f} vol={sv2} refvol={rv}")

        e2 = IndicatorEngine(store=None, symbol="QQQ")
        _md.fetch_candles = lambda *a, **k: tick2
        v, pv, sv, _ = acc(e2, tick2, t("2026-10-08 09:33:02"))
        r3, rv3 = ref([b0, b1, b2_full])
        check("V2 a minute that ended under the grace ago is still forming (09:32 at 09:33:02 waits)",
              v is not None and abs(sv - ref([b0, b1])[1]) < 1e-6,
              f"vol={sv} want {ref([b0, b1])[1]}")
        v3, _, sv3, _ = acc(e2, tick2, t("2026-10-08 09:33:30"))
        v4, _, sv4, _ = acc(e2, tick2, t("2026-10-08 09:33:40"))
        check("V3 nothing before 09:30 is folded and no bar twice",
              abs(sv3 - rv3) < 1e-6 and abs(sv4 - rv3) < 1e-6 and abs(v4 - r3) < 1e-9,
              f"vol3={sv3} vol4={sv4} want {rv3}")
    finally:
        _md.fetch_candles = keep
        import time as _time
        _ind.time = _time
    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}"); return 1
    print(f"GREEN — {len(RAN)} checks"); return 0

if __name__ == "__main__":
    sys.exit(main())
