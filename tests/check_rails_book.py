#!/usr/bin/env python3
"""
tests/check_rails_book.py  v1.3
v1.3  CD.2 (2026-10-24) - the engine's clock follows the fixture's bars (derived.levels.time is shimmed to the
      stepped bar's close + 5 s): the rail path now refuses a bar that closed more than BOOK_FRESH_S ago (levels v6.10),
      and the fixture's bars are dated 2026-09-23. Every expectation is unchanged.
v1.2  2026-09-23  OTV4TEST r126 — R8/R9 MOVED HERE from check_plan_prepares T1/T2
      (§38.4), which tested the same property on the old mapper's
      `publish_tines` — deleted with the mapper. A SLOPED rail is judged where it
      STOOD at the closed bar's own minute (`tines_now(..., minutes_back=1)`):
      R8 a bar that reached the rail as it stood then is a touch though it is
      below the rail's value now; R9 a bar that reaches the rail's value NOW but
      not where it stood then is not. Both pass on r125 too — a moved property,
      not a new behaviour.
v1.1  2026-09-23  OTV4TEST r115 — THE FORK'S DEATH MOVED TO ITS BUILDER, SO ITS CHECKS
      MOVED WITH IT (moved, not removed — §38.4). R3/R4/R5/R7 asserted that the
      LEVEL engine invalidates a fork; the operator ruled "it's gone when the
      engine says it's gone, not when a strategy says it's gone". They are now
      check_fork_invalidation F1 (breach), F3 (restart), F4 (new identity), F6
      (identity by price) and F7 (the level engine does NOT withdraw). This file
      keeps what the level engine still owns: the TOUCHES (R1, R2, R6).
THE FORK'S RAILS ON THE OPERATOR'S DEFINITIONS — driven through derive().

v1.0  2026-09-23  OTV4TEST r114. Born RED at the r113 engine, whose rails still
      ran the old tine branch (0.15% close tolerance, depth-graded WICKED/REJECTED,
      no notion of a fork being invalidated).

The operator, 2026-09-23: "Any interaction that doesn't cause the fork object to
destruct is a touch. A breech is an event that invalidates the fork."

  R1 a wick that REACHES a rail exactly and closes back inside is a touch ->
     REJECTED on the rail's id (the old path needed the wick strictly beyond)
  R2 a wick past the rail that closes back inside is a touch, pierce recorded
  R3 a 1m close beyond the rail by 0.05% (inside the OLD 0.15% tolerance) and the
     next open beyond -> the fork is INVALIDATED: an INVALIDATED row, no rails from
     tines_now, and the board reads fork "absent"
  R4 §22: a restarted engine on the same store does not resurrect that fork
  R5 a fork with a NEW identity (new anchors) serves rails again
  R8 a sloped rail is judged where it stood on the bar's minute (moved from
     check_plan_prepares T1 at r126); R9 its mirror (T2)
  R6 no WICKED rows are written for rails (the old branch does not run)
  R7 identity survives the rolling frame: the same fork one bar later (every
     anchor idx - 1, prices unchanged) is still invalidated — r19 keyed on idx
"""
from __future__ import annotations

import os
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# the r106 venv bootstrap: the lander runs CHECKs under system python3 (no pandas)
import glob as _glob
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

FAILED, RAN = [], []
WORK = tempfile.mkdtemp(prefix="chk_rails-")
os.environ["OT_FEED_DB"] = os.path.join(WORK, "empty_feed.db")      # no tape: the book stays quiet


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def guard(name, fn):
    try:
        ok, detail = fn()
    except Exception as exc:                                    # noqa: BLE001
        ok, detail = False, f"raised {type(exc).__name__}: {exc}"
    check(name, ok, detail)


def fake_forks(anchor=100.0):
    """A flat 1h fork: upper 102, median 100, lower 98 (slope 0), identity by anchor."""
    fork = types.SimpleNamespace(
        slope=0.0, direction="up",
        p0=types.SimpleNamespace(idx=1.0, price=anchor - 2), p1=types.SimpleNamespace(idx=5.0, price=anchor + 2),
        p2=types.SimpleNamespace(idx=9.0, price=anchor - 2),
        upper_at=lambda i: 102.0, median_at=lambda i: 100.0, lower_at=lambda i: 98.0)
    return types.SimpleNamespace(last_forks={"1h": fork}, last_idx={"1h": 20.0})


_MIN = [0]


def step(eng, o, h, l, c, price=None):
    """One closed 1m bar through derive(): df_1m[-2] is the bar, [-1] is the forming one."""
    import pandas as pd
    _MIN[0] += 1
    t0 = pd.Timestamp("2026-09-23 12:00", tz="America/New_York") + pd.Timedelta(minutes=_MIN[0])
    df = pd.DataFrame({"open": [o, c], "high": [h, c], "low": [l, c], "close": [c, c]},
                      index=[t0, t0 + pd.Timedelta(minutes=1)])
    _CLOCK[0] = float(t0.timestamp()) + 65.0                 # CD.2: "now" is 5 s after the closed bar's close
    eng.derive({"symbol": "QQQ", "price": price or c, "df_1m": df})


_CLOCK = [0.0]


class _BarClock:
    """derived.levels reads time.time(); the fixture's bars are dated, so the clock follows them."""
    def __getattr__(self, k):
        import time as _t
        return getattr(_t, k)

    @staticmethod
    def time():
        return _CLOCK[0]


def rows(store, ev=None):
    q = "SELECT level_id, event, round(pierce_pct, 6), depth FROM level_event"
    return store.conn.execute(q + (" WHERE event=?" if ev else ""), ((ev,) if ev else ())).fetchall()


def new_engine(store=None, anchor=100.0):
    from data.derived_store import DerivedStore
    import derived.levels as L
    L.time = _BarClock()                                       # CD.2
    store = store or DerivedStore(tempfile.mktemp(dir=WORK, prefix="d-", suffix=".db"))
    return L.LevelEngine(store, "QQQ", forks=fake_forks(anchor)), store


def _r1():
    eng, st = new_engine()
    step(eng, 101.5, 102.00, 101.4, 101.6)                  # the wick REACHES 102 exactly, closes inside
    rj = [r for r in rows(st, "REJECTED") if r[0] == "QQQ:fork1h/upper:0.00"]
    return (len(rj) == 1 and rj[0][2] == 0.0), f"upper-rail REJECTED rows {rj}"


def _r2():
    eng, st = new_engine()
    step(eng, 101.5, 102.10, 101.4, 101.8)                  # past the rail by 0.10, closes back inside
    rj = [r for r in rows(st, "REJECTED") if r[0] == "QQQ:fork1h/upper:0.00"]
    want = round(0.10 / 102.0, 6)
    return (len(rj) == 1 and abs(rj[0][2] - want) < 1e-6), f"{rj} (want pierce {want})"











def _r6():
    eng, st = new_engine()
    step(eng, 101.5, 102.10, 101.4, 101.8)
    step(eng, 98.5, 98.6, 97.9, 98.3)                      # a lower-rail touch too
    w = [r for r in rows(st, "WICKED") if "fork1h" in r[0]]
    return (not w and len(rows(st, "REJECTED")) == 2), f"WICKED rail rows {w}; REJECTED {len(rows(st, 'REJECTED'))}"


guard("R1 a wick that REACHES a rail and closes inside is a touch -> REJECTED", _r1)
guard("R2 a wick past the rail that closes back inside is a touch, pierce recorded", _r2)
guard("R6 no WICKED rows for rails — the old tine branch does not run", _r6)


def sloped_forks(slope):
    """A 1h fork whose upper rail is 100.00 at the current bar index (20) and moves
    `slope` per bar (hour); no last_bar_start, so the read is at the bar index."""
    fork = types.SimpleNamespace(
        slope=slope, direction="up",
        p0=types.SimpleNamespace(idx=1.0, price=90.0), p1=types.SimpleNamespace(idx=5.0, price=110.0),
        p2=types.SimpleNamespace(idx=9.0, price=91.0),
        upper_at=lambda i: 100.0 + slope * (i - 20.0), median_at=lambda i: 95.0 + slope * (i - 20.0),
        lower_at=lambda i: 90.0 + slope * (i - 20.0))
    return types.SimpleNamespace(last_forks={"1h": fork}, last_idx={"1h": 20.0})


def _upper_rejected(slope, o, h, l, c):
    from data.derived_store import DerivedStore
    import derived.levels as L
    st = DerivedStore(tempfile.mktemp(dir=WORK, prefix="d-", suffix=".db"))
    eng = L.LevelEngine(st, "QQQ", forks=sloped_forks(slope))
    step(eng, o, h, l, c)
    return [r for r in rows(st, "REJECTED") if r[0] == "QQQ:fork1h/upper:0.00"]


def _r8():
    # rising $6/hour = $0.10/min: the rail reads 100.00 now and stood at 99.90 on the bar's minute
    rj = _upper_rejected(6.0, 99.80, 99.92, 99.75, 99.85)
    return (len(rj) == 1), f"upper-rail REJECTED rows {rj} (bar high 99.92: reaches 99.90, not 100.00)"


def _r9():
    # falling $6/hour: the rail reads 100.00 now and stood at 100.10 on the bar's minute
    rj = _upper_rejected(-6.0, 99.90, 100.05, 99.85, 99.95)
    return (not rj), f"upper-rail REJECTED rows {rj} (bar high 100.05: reaches 100.00 now, not 100.10 then)"


guard("R8 a SLOPED rail is judged where it STOOD on the bar's minute: reached then -> touch", _r8)
guard("R9 ...and a bar reaching only the rail's value NOW, not then, is no touch", _r9)






import shutil
shutil.rmtree(WORK, ignore_errors=True)
print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
