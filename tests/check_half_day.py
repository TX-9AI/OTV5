#!/usr/bin/env python3
"""tests/check_half_day.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
DEP.12 — ON A 13:00 CLOSE EVERY CLOSE-ANCHORED TIME MOVES TO THE BELL; THE OPEN DOES NOT.

v1.0  2026-10-11  OTV4TEST r268 (mirror of otv4 r478). Before r478 nothing modelled an early close: on 2026-11-27 the
      bots would have treated 13:00-16:00 as RTH, flattened at 15:40/15:45 (nearly three
      hours after the bell), paged "blind" all afternoon and sized strikes on a session
      three hours too long. Operator 2026-10-11: "Agree. Let's implement it."
      Critiqued by OTV4TEST (MSG-QQQ-1011-10) before it was built; mirrored there with
      this file byte-identical but its header (WA §38.9).

Every instant is pinned on 2026-11-27 (13:00 close) against 2026-11-25 (full day); that
pair kills an always-shift mutant. No close-side instant is hardcoded: H4-H8 and H10 read
each tree's own constants, so this file is byte-identical in both trees but its header.

  H1  calendar: 11-27 closes 13:00 (shift 180); 12-24 is a half day; 11-25 is not;
      Thanksgiving 11-26 is a holiday, not a half day
  H2  is_rth: 09:30 open (raw), 12:59 open, 13:00 closed, 21:30 closed (a CLOCK shift
      would wrap past midnight and read 00:30 as RTH); 07:00 closed (a shifted open);
      11-25 15:59 open
  H3  entries_open: 09:35 open, 11:29 open, 11:30 CLOSED (bell - 90); 11-25 11:30 and
      15:30 open (no global afternoon cutoff, r60)
  H4-H7 THE SHAPE TEST, tree-neutral (WA §38.9: one file runs in mainline and OTV4TEST,
      whose close-side constants differ). For every minute 12:00..bell the half day's
      is_hard_close_time, hard_close_order_mode, _vertical_close_due and reconcile wind-down
      key equal the full day's SH minutes later (keys true ET); 09:30-11:59 they are equal
      outright (the open does not move). Each tree's own constants decide the values.
      H4b/H5b/H6b: each is True / 'market' / due one minute before the half-day bell.
  H6c no site anywhere compares the raw (hour, minute) with VERTICAL_HOLD_TO_ET
  H8  watchdog at its own CLOSE_AT - SH on the half day, down with a position -> emergency
      close; idle at its WINDOW end - SH; the same instant on the full day -> no close
  H9  session_fraction_remaining: 210/390 at the open, 120/390 at 11:00, 0 at 13:00
      (denominator stays 390); 11-25 11:00 -> 300/390
  H10 condor horizon: bars_left to HARD_CLOSE_ET at 12:00 on the half day equals the full
      day's at 12:00 + SH, and is > 0
  H11 no false "blind" after 13:00: market_data gates on time_utils.is_rth, which is False
      at 13:30 on 11-27
  H12 fails toward a FULL day: with EARLY_CLOSES emptied, 11-27 behaves as 11-25

Run:  python3 tests/check_half_day.py   (under the venv: the trading stack is imported)
"""
import ast
import datetime as dt
import glob as _glob
import os
import sys
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    sys.path.insert(1, _sp)

ET = ZoneInfo("America/New_York")
HALF, FULL = dt.date(2026, 11, 27), dt.date(2026, 11, 25)
FAILS = []


def ck(name, ok, det=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {det}" if det else ""))
    if not ok:
        FAILS.append(name)


def at(day, h, m, s=0):
    return dt.datetime.combine(day, dt.time(h, m, s), tzinfo=ET)


try:
    import pandas, pytz                                           # noqa: F401,E401
except ImportError as _exc:
    print(f"NOT RUN — this interpreter cannot import the trading stack ({_exc}); run under the venv")
    sys.exit(2)

print("\ncheck_half_day\n")
from utils import market_calendar as mc                           # noqa: E402
import utils.time_utils as tu                                     # noqa: E402

# ── H1 calendar ──────────────────────────────────────────────────────────────
try:
    ck("H1a 11-27 closes 13:00, shift 180",
       mc.close_time(HALF) == dt.time(13, 0) and mc.close_shift_minutes(HALF) == 180)
    ck("H1b 12-24 is a half day", mc.is_half_day(dt.date(2026, 12, 24)))
    ck("H1c 11-25 is a full day", not mc.is_half_day(FULL) and mc.close_shift_minutes(FULL) == 0)
    ck("H1d Thanksgiving is a holiday, not a half day",
       not mc.is_trading_day(dt.date(2026, 11, 26)) and not mc.is_half_day(dt.date(2026, 11, 26)))
except AttributeError as exc:
    ck("H1  market_calendar models early closes", False, f"{exc}")

# ── H2 is_rth ────────────────────────────────────────────────────────────────
ck("H2a 09:30 on 11-27 is RTH (the open is raw)", tu.is_rth(at(HALF, 9, 30)) is True)
ck("H2b 12:59 on 11-27 is RTH", tu.is_rth(at(HALF, 12, 59)) is True)
ck("H2c 13:00 on 11-27 is NOT RTH", tu.is_rth(at(HALF, 13, 0)) is False)
ck("H2d 21:30 on 11-27 is NOT RTH (no midnight wrap)", tu.is_rth(at(HALF, 21, 30)) is False)
ck("H2e 15:59 on 11-25 is RTH", tu.is_rth(at(FULL, 15, 59)) is True)
ck("H2f 07:00 on 11-27 is NOT RTH (a shifted open would read 10:00)", tu.is_rth(at(HALF, 7, 0)) is False)

# ── H3 entries_open ──────────────────────────────────────────────────────────
ck("H3a 09:35 on 11-27 entries open", tu.entries_open(at(HALF, 9, 35)) is True)
ck("H3b 11:29 on 11-27 entries open", tu.entries_open(at(HALF, 11, 29)) is True)
ck("H3c 11:30 on 11-27 entries CLOSED (bell - 90)", tu.entries_open(at(HALF, 11, 30)) is False)
ck("H3d 12:30 on 11-27 entries CLOSED", tu.entries_open(at(HALF, 12, 30)) is False)
ck("H3e 11:30 and 15:30 on 11-25 entries open",
   tu.entries_open(at(FULL, 11, 30)) is True and tu.entries_open(at(FULL, 15, 30)) is True)

# ── H4-H7 THE SHAPE TEST: A HALF-DAY AFTERNOON IS THE FULL-DAY AFTERNOON, SH EARLIER ──
# 🔑 TREE-NEUTRAL BY CONSTRUCTION (WA §38.9, OTV4TEST's request). No close-side
# instant is written here: for every minute m from 12:00 to the half-day bell,
# f(HALF, m) must equal f(FULL, m + SH), where SH is the calendar's own shift.
# Each tree's own constants (15:40 or 15:45 flatten, 15:45 or 15:55 cross, its
# wind-down slots) decide WHAT f returns; this only demands that a 13:00 day
# runs the same schedule three hours early. And for every minute 09:30-11:59
# f(HALF, m) == f(FULL, m): the OPEN side does not move.
SH = mc.close_shift_minutes(HALF) if hasattr(mc, "close_shift_minutes") else 180
BELL = 16 * 60 - SH


def sweep(f, key=lambda v, sh: v):
    """[(minute, half, full)] where the half-day afternoon disagrees with the
    full day SH minutes later, plus any morning minute that disagrees at all."""
    bad = []
    for m in range(12 * 60, BELL):
        h = f(at(HALF, m // 60, m % 60)); g = f(at(FULL, (m + SH) // 60, (m + SH) % 60))
        if h != key(g, SH):
            bad.append((f"{m // 60:02d}:{m % 60:02d}", h, key(g, SH)))
    for m in range(9 * 60 + 30, 12 * 60):
        h = f(at(HALF, m // 60, m % 60)); g = f(at(FULL, m // 60, m % 60))
        if h != g:
            bad.append((f"{m // 60:02d}:{m % 60:02d}", h, g))
    return bad


def _hct(n):
    try:
        return tu.is_hard_close_time(n)
    except TypeError:
        return "no-clock-arg"


bad = sweep(_hct)
ck("H4  is_hard_close_time: the half-day afternoon is the full day's, SH early; morning unchanged",
   not bad, f"{len(bad)} minute(s), first {bad[:2]}")
ck("H4b is_hard_close_time takes a clock and is True one minute before the half-day bell",
   _hct(at(HALF, (BELL - 1) // 60, (BELL - 1) % 60)) is True,
   f"{_hct(at(HALF, (BELL - 1) // 60, (BELL - 1) % 60))}")

from execution.limit_ladder import hard_close_order_mode as hm   # noqa: E402
bad = sweep(hm)
ck("H5  hard_close_order_mode (none/limit/market): half-day afternoon = full day SH early",
   not bad, f"{len(bad)} minute(s), first {bad[:2]}")
ck("H5b and it reaches 'market' before the half-day bell",
   hm(at(HALF, (BELL - 1) // 60, (BELL - 1) % 60)) == "market")

# ── H6 credit hold ───────────────────────────────────────────────────────────
from config import VERTICAL_HOLD_TO_ET                            # noqa: E402
import execution.position_manager as pm                           # noqa: E402


def _vcd(n):
    _real = tu.now_et
    try:
        tu.now_et = lambda: n
        return pm._vertical_close_due()
    finally:
        tu.now_et = _real


bad = sweep(_vcd)
ck("H6a position_manager._vertical_close_due: half-day afternoon = full day SH early",
   not bad, f"{len(bad)} minute(s), first {bad[:2]}")
ck("H6b and credit verticals are due before the half-day bell",
   _vcd(at(HALF, (BELL - 1) // 60, (BELL - 1) % 60)) is True)
raw = []
for dp, _dn, fns in os.walk(ROOT):
    if "/tests" in dp or "/venv" in dp or "/." in dp:
        continue
    for fn in fns:
        if not fn.endswith(".py"):
            continue
        rel = os.path.relpath(os.path.join(dp, fn), ROOT)
        try:
            tree = ast.parse(open(os.path.join(dp, fn)).read())
        except Exception:                                          # noqa: BLE001
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                u = ast.unparse(node)
                if "VERTICAL_HOLD_TO_ET" in u and ".hour" in u:
                    raw.append(f"{rel}:{node.lineno}")
ck("H6c no site compares the raw clock's (hour, minute) with VERTICAL_HOLD_TO_ET", not raw, f"{raw}")

# ── H7 reconcile slots ───────────────────────────────────────────────────────
import main as M                                                   # noqa: E402
slot = M._intraday_reconcile_slot


def _hhmm_minus(k, sh):
    """A full-day slot key moved SH minutes earlier, dated HALF — what the half
    day must produce. Keys stay TRUE ET, so 15:45 on the full day is 12:45."""
    if k is None:
        return None
    hh, mm = int(k[-5:-3]), int(k[-2:])
    t = hh * 60 + mm - sh
    return f"{HALF:%Y-%m-%d} {t // 60:02d}:{t % 60:02d}"


def _slot_half_dated(n):
    k = slot(n)
    return None if k is None else f"{HALF:%Y-%m-%d} {k[-5:]}"


# The afternoon comparison is limited to the wind-down (from the full day's first
# slot that is not an interval slot): interval slots are keyed from the 09:30 open,
# which does not move, so they legitimately differ from a shifted full day.
_iv = max(1, int(getattr(M, "BROKER_RECONCILE_INTERVAL_MIN", 10)))
_wd = None
for m in range(12 * 60, 16 * 60):
    k = slot(at(FULL, m // 60, m % 60))
    if k is not None and (int(k[-5:-3]) * 60 + int(k[-2:]) - 570) % _iv != 0:
        _wd = m
        break
bad = []
if _wd is not None:
    for m in range(_wd - SH, BELL + 1):
        h = _slot_half_dated(at(HALF, m // 60, m % 60))
        g = _hhmm_minus(slot(at(FULL, (m + SH) // 60, (m + SH) % 60)), SH)
        if h != g:
            bad.append((f"{m // 60:02d}:{m % 60:02d}", h, g))
ck("H7a wind-down slots: half day = full day SH early, keyed TRUE ET, None at the bell",
   _wd is not None and not bad, f"wind-down from {_wd}; {len(bad)} minute(s), first {bad[:2]}")
bad = [m for m in range(9 * 60 + 30, 12 * 60)
       if _slot_half_dated(at(HALF, m // 60, m % 60))
       != (None if slot(at(FULL, m // 60, m % 60)) is None
           else f"{HALF:%Y-%m-%d} {slot(at(FULL, m // 60, m % 60))[-5:]}")]
ck("H7b morning slots identical on both days (the 09:30 base is raw)", not bad, f"{bad[:3]}")

# ── H8 watchdog ──────────────────────────────────────────────────────────────
import tools.emergency_watchdog as W                              # noqa: E402


class Fake:
    """The watchdog's World, minimal: a bot that is down with one position open."""
    def __init__(self, day, t):
        self.t = dt.datetime.combine(day, t, tzinfo=ET)
        self.st, self.calls, self.pages, self.opened = {}, [], [], ["Breakout aaaa1111"]
    def now(self): return self.t
    def advance(self, s): self.t += dt.timedelta(seconds=s)
    def trading_day(self, d): return mc.is_trading_day(d)
    def load_env(self): return {}
    def service_state(self): return "failed"
    def process_age_s(self): return 5000.0
    def heartbeat_age_s(self): return 900.0
    def paper(self): return True
    def open_positions(self): return list(self.opened)
    def outcomes(self, o): return [f"{x} -120" for x in o]
    def page(self, m): self.pages.append(m); return True
    def stop_bot(self): self.calls.append("stop"); return True
    def cancel_working(self): return 0
    def flatten_pass(self): self.calls.append("flatten"); self.opened = []; return []
    def sleep(self, s): self.advance(s)
    def load_state(self): return dict(self.st)
    def save_state(self, st): self.st = dict(st)


def _minus(t, sh):
    x = t.hour * 60 + t.minute - sh
    return dt.time(x // 60, x % 60)


def two(day, t):
    f = Fake(day, t); a = W.run_once(f); f.advance(60); b = W.run_once(f)
    return f, a, b


f, a, b = two(HALF, _minus(W.CLOSE_AT, SH))
ck("H8a half day at CLOSE_AT - SH, down with a position -> emergency close",
   b == "closed" and "stop" in f.calls, f"at {_minus(W.CLOSE_AT, SH)}: {a} {b}")
f, a, b = two(HALF, _minus(W.WINDOW[1], SH))
ck("H8b half day at WINDOW end - SH -> idle", (a, b) == ("idle", "idle"),
   f"at {_minus(W.WINDOW[1], SH)}: {a} {b}")
f, a, b = two(FULL, _minus(W.CLOSE_AT, SH))
ck("H8c full day at the same instant -> no close", "stop" not in f.calls, f"{a} {b}")

# ── H9 expected-move term ────────────────────────────────────────────────────
from analysis.volatility_measures import session_fraction_remaining as sfr   # noqa: E402
v = [sfr(at(HALF, 9, 30)), sfr(at(HALF, 11, 0)), sfr(at(HALF, 13, 0)), sfr(at(FULL, 11, 0))]
ck("H9  11-27: 210/390 open, 120/390 at 11:00, 0 at 13:00; 11-25 11:00 300/390",
   all(abs(x - y) < 1e-9 for x, y in zip(v, (210 / 390, 120 / 390, 0.0, 300 / 390))),
   f"{[round(x, 4) for x in v]}")

# ── H10 condor horizon ───────────────────────────────────────────────────────
from strategy import credit_vertical as cv                         # noqa: E402
from config import HARD_CLOSE_ET                                   # noqa: E402
bl = (cv.bars_left(at(HALF, 12, 0), 5, HARD_CLOSE_ET),
      cv.bars_left(at(FULL, (12 * 60 + SH) // 60, (12 * 60 + SH) % 60), 5, HARD_CLOSE_ET))
ck("H10 bars_left to HARD_CLOSE_ET: half day 12:00 = full day SH later, and > 0",
   bl[0] == bl[1] and bl[0] > 0, f"{bl}")

# ── H11 no false blind ───────────────────────────────────────────────────────
import data.market_data as md                                     # noqa: E402
ck("H11 market_data's RTH test is time_utils.is_rth, False at 13:30 on 11-27",
   md.is_rth is tu.is_rth and tu.is_rth(at(HALF, 13, 30)) is False)

# ── H12 fail toward a full day ───────────────────────────────────────────────
_saved = dict(getattr(mc, "EARLY_CLOSES", {}))
try:
    if hasattr(mc, "EARLY_CLOSES"):
        mc.EARLY_CLOSES.clear()
    ck("H12 unlisted: 11-27 is a full day (13:30 RTH, 11:30 entries open, no flatten at 12:45)",
       tu.is_rth(at(HALF, 13, 30)) is True and tu.entries_open(at(HALF, 11, 30)) is True
       and hm(at(HALF, 12, 45)) == "none")
finally:
    if hasattr(mc, "EARLY_CLOSES"):
        mc.EARLY_CLOSES.update(_saved)

print()
if FAILS:
    print(f"check_half_day: FAIL ({len(FAILS)}): {', '.join(FAILS)}")
    sys.exit(1)
print("check_half_day: ALL PASS")
