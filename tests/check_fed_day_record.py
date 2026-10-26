#!/usr/bin/env python3
"""
tests/check_fed_day_record.py  v5.0
v5.0  2026-10-25  (MEAS.3) — THE FED-DAY FLAG IS RECORDED CORRECTLY, AND CHANGES NO TRADING.
      data/macro_data._check_fed_day had always returned False: the live calendar sends ISO dates
      ("2026-09-16T14:00:00-04:00") where the parser wanted "Jun 21, 2026", and it read `currency` where the
      payload (measured 2026-09-16: title/country/date/impact/forecast/previous) says `country`. The operator's
      2026-10-03 ruling: "I don't want trading behavior to change on fed days" - so the fix is record only, and
      the readers that would have acted on a true flag (ORB's FED_DAY_ORB_BOOST, the snapshot's
      butterfly_allowed = False) are removed.

  Drives the REAL MacroManager._check_fed_day against a stubbed HTTP response and a pinned ET clock
  (2026-09-16, an FOMC day), and the REAL MacroManager._fetch with VIX and the calendar stubbed:
  F1  the live payload shape (ISO date with offset, `country`, no `currency`) on an FOMC day -> (True, title)
  F2  CONTROLS: a non-USD country, a Medium impact, another day, a non-Fed title -> False
  F3  the legacy "Sep 16, 2026" form with `currency` still reads (fallback)
  F4  the date is the event's ET day: 2026-09-17T01:00:00Z is 09-16 21:00 ET (True); 2026-09-16T03:00:00Z
      is 09-15 ET (False)
  F5  an unreadable date is not silent: on a day with no Fed event it is skipped and a WARNING names the count
  F6  NO BEHAVIOUR CHANGE: _fetch on a Fed day yields the same snapshot as on a non-Fed day in every field
      except is_fed_day / fed_event_name (butterfly_allowed included)
  F7  NO BEHAVIOUR CHANGE: FED_DAY_ORB_BOOST is gone from config and strategy.orb_strategy (both import), and
      ORB's `if is_fed_day` block only records (no assignment or augmented assignment in it)

Born red on ffe10bf at F1 F4 F5 F6 F7 (F2, F3 are controls that pass on both).
Run:  python3 tests/check_fed_day_record.py   (exit 0 green, 1 red)
"""
import ast
import glob as _glob
import logging
import os
import sys
import tempfile
from datetime import datetime

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_fed_day_record_")
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class _Resp:
    status_code = 200

    def __init__(self, events):
        self._e = events

    def json(self):
        return self._e


def _ev(date, title="FOMC Statement", impact="High", country="USD", **kw):
    e = {"title": title, "country": country, "date": date, "impact": impact, "forecast": "", "previous": ""}
    e.update(kw)
    return e


def main():
    from zoneinfo import ZoneInfo
    import data.macro_data as MD
    import utils.time_utils as TU

    ET = ZoneInfo("America/New_York")
    pinned = datetime(2026, 9, 16, 10, 0, tzinfo=ET)
    orig_now, orig_get = TU.now_et, MD.requests.get
    TU.now_et = lambda: pinned
    mm = MD.MacroManager()

    def run(events):
        MD.requests.get = lambda *a, **k: _Resp(events)
        try:
            return mm._check_fed_day()
        except Exception as exc:                              # noqa: BLE001
            return f"{type(exc).__name__}: {exc}"

    try:
        got = run([_ev("2026-09-16T14:00:00-04:00")])
        check("F1 live payload (ISO + country) on an FOMC day -> (True, 'FOMC Statement')",
              got == (True, "FOMC Statement"), f"got {got!r}")

        ctl = (run([_ev("2026-09-16T14:00:00-04:00", country="EUR")]),
               run([_ev("2026-09-16T14:00:00-04:00", impact="Medium")]),
               run([_ev("2026-09-17T14:00:00-04:00")]),
               run([_ev("2026-09-16T08:30:00-04:00", title="Retail Sales m/m")]))
        check("F2 CONTROLS: non-USD, Medium impact, another day, non-Fed title -> all False",
              all(isinstance(g, tuple) and g[0] is False for g in ctl), f"got {ctl!r}")

        legacy = {"title": "FOMC Statement", "currency": "USD", "date": "Sep 16, 2026", "impact": "High"}
        got = run([legacy])
        check("F3 legacy 'Sep 16, 2026' + currency still reads", got == (True, "FOMC Statement"), f"got {got!r}")

        g1 = run([_ev("2026-09-17T01:00:00Z")])
        g2 = run([_ev("2026-09-16T03:00:00Z")])
        check("F4 the event's ET day decides (01:00Z 09-17 is 09-16 ET; 03:00Z 09-16 is 09-15 ET)",
              g1 == (True, "FOMC Statement") and isinstance(g2, tuple) and g2[0] is False,
              f"got {g1!r} / {g2!r}")

        records = []

        class _H(logging.Handler):
            def emit(self, rec):
                records.append(rec)
        h = _H(level=logging.WARNING)
        MD.logger.addHandler(h)
        try:
            got = run([_ev("not a date"), _ev("2026-09-17T14:00:00-04:00")])
        finally:
            MD.logger.removeHandler(h)
        named = [r.getMessage() for r in records if r.levelno >= logging.WARNING and "1 of 2" in r.getMessage()]
        check("F5 an unreadable date is skipped and a WARNING names the count ('1 of 2')",
              isinstance(got, tuple) and got[0] is False and bool(named),
              f"got {got!r}, warnings={[r.getMessage() for r in records]!r}")
    finally:
        TU.now_et, MD.requests.get = orig_now, orig_get

    # F6 — the snapshot is identical on a Fed day except for the two record fields
    try:
        def snap(fed):
            m = MD.MacroManager()
            m._fetch_vix = lambda: 14.0
            m._check_fed_day = (lambda: (True, "FOMC Statement")) if fed else (lambda: (False, ""))
            s = vars(m._fetch()).copy()
            for k in ("is_fed_day", "fed_event_name", "fetched_at"):
                s.pop(k, None)
            return s
        a, b = snap(True), snap(False)
        diff = {k: (a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)}
        check("F6 a Fed day changes no snapshot field but is_fed_day / fed_event_name", not diff, f"diff {diff!r}")
    except Exception as exc:                                  # noqa: BLE001
        check("F6 (did not run)", False, f"{type(exc).__name__}: {exc}")

    # F7 — the ORB boost is gone, and the Fed-day block only records
    try:
        import config as C
        import strategy.orb_strategy as O
        gone = not hasattr(C, "FED_DAY_ORB_BOOST") and not hasattr(O, "FED_DAY_ORB_BOOST")
        tree = ast.parse(open(O.__file__, encoding="utf-8").read())
        writes = []
        for n in ast.walk(tree):
            if isinstance(n, ast.If) and "is_fed_day" in ast.unparse(n.test):
                for b in n.body:
                    for x in ast.walk(b):
                        if isinstance(x, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                            writes.append(ast.unparse(x))
        check("F7 FED_DAY_ORB_BOOST is gone and ORB's Fed-day block assigns nothing",
              gone and not writes, f"boost_present={not gone} writes={writes!r}")
    except Exception as exc:                                  # noqa: BLE001
        check("F7 (did not run)", False, f"{type(exc).__name__}: {exc}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — the Fed-day flag is recorded correctly and changes no trading")
    return 0


if __name__ == "__main__":
    sys.exit(main())
