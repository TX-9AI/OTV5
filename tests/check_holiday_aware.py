#!/usr/bin/env python3
"""
tests/check_holiday_aware.py  v1.3
v1.3  2026-09-23  OTV4TEST r125 — shadow/ IS DELETED (LVL.15 step 5), so H5 is
      RETARGETED, NOT REMOVED (§38.4): its property was "one holiday list, not
      three", and it now scans EVERY .py in the tree for a second
      `US_MARKET_HOLIDAYS = {` outside utils/market_calendar.py — stronger than
      reading one file. H5c/H5d RETIRE WITH THE THING THEY RAN: they executed
      shadow-start.service's ExecCondition (shadow/trading_day.py), and that unit
      and script are deleted in the same delivery; there is no condition left.
      And the r106 venv bootstrap: under system python3 it died on pytz.
v1.2  2026-09-08  r319 / SHD.3 — H5c RUNS THE ExecCondition, BECAUSE H5 READ
      SOURCE TEXT AND WATCHED THE FLEET GO DARK. H5 asserts that
      `shadow/trading_day.py` contains the string `from utils.market_calendar
      import`. That string is precisely what broke it: an absolute package
      import in a module systemd invokes as a PLAIN SCRIPT, where `sys.path`
      carries the script's own directory and not the repo root. The import
      raised, the ExecCondition exited 1, systemd SKIPPED `shadow-start`
      (a non-zero condition is a skip, not a failure, so nothing entered a
      failed state), and all fifteen boxes wrote ZERO shadow rows on the first
      session after r304 landed. H5 was green the whole time.
      WORKING_AGREEMENT §21 one layer up — H5 asserted the MENTION of the
      import whose RESOLUTION was the defect. H5c executes the real
      ExecCondition line with the SYSTEM python from a directory OUTSIDE the
      repo and reads the exit code; H5d proves it fails for the right reason
      by checking stderr carries no traceback.
v1.1  2026-09-07  r307 - H4 DERIVES ITS out-of-coverage YEAR from coverage()
instead of hardcoding 2035. It went red the moment the list was extended to
2035 - a second copy of a constant, the same failure this session hit in a menu
prompt and a help string. Now it survives every future extension.
v1.0  2026-09-07  r304 / DEP.9 — THE TRADING CLOCK CONSULTS THE CALENDAR, AND
IT FAILS TOWARD TRADING.

Surfaced 2026-09-07, Labor Day: `is_rth()` tested `weekday() >= 5` and a time
window, nothing else, so on a market holiday it returned True and
`entries_open()` — the universal floor every order site sits behind (r102) —
said the market was open. The orchestrator and the morning brief knew better;
the trading path did not.

🔴 H4 IS THE CHECK THAT MATTERS AND IT IS NOT THE OBVIOUS ONE. The asymmetry
is: a WRONG holiday (a real session listed) means the fleet does not trade —
silent, total, and indistinguishable from a quiet tape. A MISSED holiday means
it is armed on a dead market and does nothing. So a date BEYOND the list's
coverage must read as a TRADING day. Anyone later "hardening" this by refusing
outside coverage turns a forgotten annual refresh into a dark fleet, and H4
goes red on them.

⚠️ AND IT EXECUTES `is_rth`, not the calendar. `market_calendar` has its own
selftest; what this pins is that the trading clock actually CALLS it — the
r150 lesson, where a gate read a name off an object that did not have it and
failed silently for the life of a strategy.

Run:  python3 tests/check_holiday_aware.py
"""
from __future__ import annotations

import datetime as _dt
import os
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import glob as _glob                                             # r106 venv bootstrap (r125:
for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "venv", "lib", "python*", "site-packages")):  # it died on pytz
    if _sp not in sys.path:                                      # under system python3)
        sys.path.insert(1, _sp)
ET = ZoneInfo("America/New_York")
F: list = []


def check(n: str, ok: bool, d: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f"  — {d}" if d else ""))
    if not ok:
        F.append(n)


def main() -> int:
    print("\ncheck_holiday_aware\n")
    from utils.time_utils import is_rth, entries_open
    from utils import market_calendar as mc

    def at(y, m, d, hh=12, mm=0):
        return _dt.datetime(y, m, d, hh, mm, tzinfo=ET)

    check("H1  Labor Day 2026-09-07 midday is NOT RTH", not is_rth(at(2026, 9, 7)))
    check("H1b and entries are CLOSED on it", not entries_open(at(2026, 9, 7)))
    check("H2  the next weekday IS RTH", is_rth(at(2026, 9, 8)))
    check("H2b Thanksgiving 2026-11-26 is NOT RTH", not is_rth(at(2026, 11, 26)))
    check("H3  a weekend is still not RTH", not is_rth(at(2026, 9, 5)))

    # 🔴 THE ONE THAT MATTERS.
    # ⚠️ DERIVED FROM coverage(), NOT A HARDCODED YEAR. The first version used
    # 2035 and went red the moment r307 extended the list to 2035 — a second
    # copy of a constant, which is the failure this session has now hit in a
    # menu prompt, a help string and here. Pick the first weekday after the
    # last covered year and the check survives every future extension.
    _far_year = mc.coverage()[1] + 5
    far = at(_far_year, 3, 14)
    while far.weekday() >= 5:
        far += _dt.timedelta(days=1)
    check("H4  a weekday BEYOND the list's coverage IS RTH — fails toward "
          "trading",
          is_rth(far) and not mc.is_covered(far.date()),
          "a forgotten refresh must cost armed mornings, never a dark fleet")
    _sat = far
    while _sat.weekday() != 5:
        _sat += _dt.timedelta(days=1)
    check("H4b a weekend beyond coverage is still closed", not is_rth(_sat))

    # H5 — one list, not three (r125: retargeted from shadow/trading_day.py,
    # deleted, to the whole tree). Only utils/market_calendar.py defines it.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _defs = []
    for _dp, _dns, _fns in os.walk(root):
        _dns[:] = [d for d in _dns if d not in ("venv", ".git", "__pycache__", "tests")]  # runtime code only
        for _fn in _fns:
            if _fn.endswith(".py"):
                _p = os.path.join(_dp, _fn)
                try:
                    if "US_MARKET_HOLIDAYS = {" in open(_p, encoding="utf-8").read():
                        _defs.append(os.path.relpath(_p, root))
                except (OSError, UnicodeDecodeError):
                    pass
    check("H5  ONE holiday list: only utils/market_calendar.py defines US_MARKET_HOLIDAYS",
          _defs == [os.path.join("utils", "market_calendar.py")], str(sorted(_defs)))
    # H5c/H5d RETIRED at r125 with shadow-start.service and shadow/trading_day.py
    # (the ExecCondition they executed no longer exists). See the v1.3 note.

    tu = open(os.path.join(root, "utils", "time_utils.py")).read()
    check("H5b time_utils does not define a holiday set of its own",
          "US_MARKET_HOLIDAYS = {" not in tu)

    # H6 — a half day is a TRADING day; sessions are not modelled (DEP.12).
    check("H6  a half day (2026-11-27) is RTH — shortened sessions unmodelled",
          is_rth(at(2026, 11, 27)), "DEP.12")

    print()
    if F:
        print(f"check_holiday_aware: FAIL ({len(F)}): {', '.join(F)}")
        return 1
    print("check_holiday_aware: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
