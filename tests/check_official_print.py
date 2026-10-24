#!/usr/bin/env python3
"""
tests/check_official_print.py  v1.0
v1.0  2026-10-03  OTV4TEST r222 (ORP.1) — THE OPENING RANGE HAS AN OFFICIAL PRINT; A BLIND OPEN IS CORRECTED BEFORE ANY BREAK.

  Measured 2026-10-03 over 14 sessions: the bot's recorded range equalled the
  feed's first five 1m bars on 13; on 2026-09-29 (the feed blind at the open)
  the range was frozen at 740.58 / 739.62 while the bars say 740.58 / 737.67.
  The operator: "On a blind start, agree. Yes, make it the official print &
  refer everything to it."

  Drives the REAL main._official_print, main._verify_official_print and
  ORBEngine.correct_range. The 09-29 numbers are the fixture.
  P1  the print is the high and low of the five 1m bars 09:30-09:34; with a
      bar missing there is NO print (a partial open is the defect)
  P2  the engine range equals the print -> verified, nothing written
  P3  THE 09-29 CASE, before any break: the engine is corrected to 737.67 and
      orb_range.json is rewritten with the print
  P4  the same difference AFTER a break is latched: nothing changes, it warns
  P5  bars still missing at 09:40 -> nothing settled; at 10:30 -> unverifiable,
      said once
  P6  _opening_range(ctx) returns the engine's range when it has one

Run:  python3 tests/check_official_print.py   (exit 0 green, 1 red)
"""
import datetime as _dt
import glob as _glob
import json
import logging
import os
import sys
import tempfile
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_official_print_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ["OT_PAPER_TRADING"] = "1"

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class _Logs(logging.Handler):
    def __init__(self):
        super().__init__(); self.lines = []

    def emit(self, record):
        self.lines.append((record.levelname, record.getMessage()))


def _bars(drop=()):
    import pandas as pd
    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/New_York")
    rows = {30: (740.10, 740.58, 739.62, 740.00), 31: (740.00, 740.20, 738.90, 739.10), 32: (739.10, 739.40, 737.67, 738.20),
            33: (738.20, 739.00, 738.00, 738.80), 34: (738.80, 739.50, 738.60, 739.30), 35: (739.30, 739.60, 739.00, 739.20),
            36: (739.20, 739.50, 739.00, 739.40)}
    idx, data = [], []
    for m, r in rows.items():
        if m in drop:
            continue
        idx.append(_dt.datetime(2026, 9, 29, 9, m, tzinfo=et)); data.append(r)
    return pd.DataFrame(data, columns=["open", "high", "low", "close"], index=pd.DatetimeIndex(idx))


def main():
    try:
        import main as M
        import analysis.orb_engine as OE
        if not hasattr(M, "_verify_official_print") or not hasattr(OE.ORBEngine, "correct_range"):
            raise AttributeError("the official-print functions are absent")
    except Exception as exc:                                  # noqa: BLE001
        for n in ("P1", "P2", "P3", "P4", "P5", "P6"):
            check(f"{n} (did not run)", False, f"{type(exc).__name__}: {exc}")
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1

    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/New_York")
    h = _Logs(); logging.getLogger("__main__").addHandler(h); logging.getLogger("main").addHandler(h)
    sv = (M.now_et, M.get_orb_engine, OE.ORB_RANGE_FILE)
    OE.ORB_RANGE_FILE = os.path.join(_S, "orb_range.json")

    def engine(hi, lo, state=None, broke=False):
        e = OE.ORBEngine()
        e._data.orb_high, e._data.orb_low, e._data.orb_width = hi, lo, hi - lo
        e._data.state = state or OE.ORBState.WAITING_FOR_BREAK
        e._broke_low = broke
        M.get_orb_engine = lambda: e
        return e

    def at(hh, mm):
        M.now_et = lambda: _dt.datetime(2026, 9, 29, hh, mm, 5, tzinfo=et)

    def st():
        return types.SimpleNamespace(orb_range_established_today=True)
    try:
        d = _dt.date(2026, 9, 29)
        check("P1 the print is 740.58 / 737.67 from five bars; with the 09:32 bar missing there is no print",
              M._official_print(_bars(), d) == (740.58, 737.67) and M._official_print(_bars(drop=(32,)), d) is None,
              f"{M._official_print(_bars(), d)} / {M._official_print(_bars(drop=(32,)), d)}")

        at(9, 36); e = engine(740.58, 737.67); s = st()
        if os.path.exists(OE.ORB_RANGE_FILE):
            os.remove(OE.ORB_RANGE_FILE)
        r = M._verify_official_print(s, _bars())
        again = M._verify_official_print(s, _bars())
        check("P2 an equal range is verified once, and nothing is written",
              r == "verified" and again == "" and not os.path.exists(OE.ORB_RANGE_FILE)
              and (e._data.orb_high, e._data.orb_low) == (740.58, 737.67), f"{r!r} then {again!r}")

        at(9, 36); e = engine(740.58, 739.62); s = st()
        r = M._verify_official_print(s, _bars())
        js = json.load(open(OE.ORB_RANGE_FILE)) if os.path.exists(OE.ORB_RANGE_FILE) else {}
        check("P3 09-29 before any break: the engine low goes 739.62 -> 737.67 and orb_range.json carries the print",
              r == "corrected" and (e._data.orb_high, e._data.orb_low) == (740.58, 737.67)
              and abs(e._data.orb_width - 2.91) < 1e-6 and js.get("low") == 737.67 and js.get("high") == 740.58
              and js.get("status") == "ESTABLISHED" and js.get("date") == "2026-09-29",
              f"{r!r} engine {(e._data.orb_high, e._data.orb_low)} file {js}")

        os.remove(OE.ORB_RANGE_FILE)
        at(9, 37); e = engine(740.58, 739.62, broke=True); s = st(); n0 = len(h.lines)
        r = M._verify_official_print(s, _bars())
        warned = [m for lv, m in h.lines[n0:] if lv == "WARNING" and "NOT corrected" in m]
        e2 = engine(740.58, 739.62, state=OE.ORBState.ARMED_SHORT); s2 = st()
        r2 = M._verify_official_print(s2, _bars())
        check("P4 after a break is latched (or the engine is armed) nothing changes and it WARNS",
              r == "differs-frozen" and r2 == "differs-frozen" and (e._data.orb_low, e2._data.orb_low) == (739.62, 739.62)
              and len(warned) == 1 and not os.path.exists(OE.ORB_RANGE_FILE), f"{r!r}/{r2!r} warned {len(warned)}")

        at(9, 40); e = engine(740.58, 739.62); s = st()
        early = M._verify_official_print(s, _bars(drop=(31, 32)))
        at(10, 30); n0 = len(h.lines)
        late = M._verify_official_print(s, _bars(drop=(31, 32)))
        late2 = M._verify_official_print(s, _bars(drop=(31, 32)))
        check("P5 bars still missing: nothing settled at 09:40; at 10:30 it is UNVERIFIED, said once, range untouched",
              early == "" and late == "unverifiable" and late2 == "" and e._data.orb_low == 739.62
              and sum(1 for lv, m in h.lines[n0:] if "UNVERIFIED" in m) == 1, f"{early!r} {late!r} {late2!r}")

        got = M._opening_range({"orb_high": 740.58, "orb_low": 737.67, "df_5m": None, "df_1m": None})
        none = M._opening_range({"df_5m": None, "df_1m": None})
        check("P6 _opening_range returns the engine's range when it has one, and (None, None) with nothing at all",
              got == (740.58, 737.67) and none == (None, None), f"{got} / {none}")
    except Exception as exc:                                  # noqa: BLE001
        check("P2 (did not run)", False, f"{type(exc).__name__}: {exc}")
    finally:
        M.now_et, M.get_orb_engine, OE.ORB_RANGE_FILE = sv

    if FAILED:
        print(f"\nRED — {len(set(FAILED))} check(s): {sorted(set(FAILED))}")
        return 1
    print("\nGREEN — the official print verifies the range, corrects a blind open before any break, and never after")
    return 0


if __name__ == "__main__":
    sys.exit(main())
