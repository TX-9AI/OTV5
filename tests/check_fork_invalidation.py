#!/usr/bin/env python3
"""
tests/check_fork_invalidation.py  v1.1
A FORK LIVES WHILE ITS BUILDER CAN BUILD IT — driven through ForkEngine.run().

v1.1  2026-09-23  OTV4TEST r116 — THE RULE MOVED AND THIS FILE MOVED WITH IT. r115
      killed a fork on a 1m rail breach and refused the builder's rebuild of it.
      The operator, 2026-09-23: "I agree. If the channel gets disrespected briefly
      but persists it still serving us somewhat of a guide." The builder's
      containment test is now the ONLY judge, so F1/F2/F3/F8 INVERT (the same
      scenarios, the opposite assertion), F4 now asserts the other half of the
      rule (a fork the builder cannot build is gone), F6 is replaced (identity by
      price no longer decides anything) by the rail-timing fix, and F5/F7 stand.
v1.0  2026-09-23  OTV4TEST r115 (born red at r114).

  F1 a 1m rail breach does NOT stop the ForkEngine serving the fork, and no
     INVALIDATED row is written
  F2 the builder's rebuild of the same fork is served
  F3 a restart over r115's INVALIDATED rows serves the fork (they are ignored)
  F4 when the BUILDER cannot build a fork, it is not served — the builder judges
  F5 a touch changes nothing
  F6 r116 — rails are read at the CURRENT minute: 30 minutes into the forming
     hour a rail with slope $1/bar sits $0.50 past its value at the hour's start
  F7 the LEVEL engine seeing a breach does not withdraw the rails
  F8 r114's level_event INVALIDATED row is ignored — the fork is served
"""
from __future__ import annotations

import os
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import glob as _glob                                             # r106 venv bootstrap
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

FAILED, RAN = [], []
WORK = tempfile.mkdtemp(prefix="chk_forkinv-")
os.environ["OT_FEED_DB"] = os.path.join(WORK, "empty_feed.db")


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


def a_fork(anchor=100.0, shift=0.0):
    """Flat rails: upper 102, median 100, lower 98; identity from the anchor prices."""
    P = lambda i, p: types.SimpleNamespace(idx=i - shift, price=p, kind="low")   # noqa: E731
    return types.SimpleNamespace(slope=0.0, direction="up", filters_passed=(),
                                 p0=P(10.0, anchor - 2), p1=P(30.0, anchor + 2), p2=P(50.0, anchor - 1),
                                 upper_at=lambda i: 102.0, median_at=lambda i: 100.0, lower_at=lambda i: 98.0)


CURRENT = {"fork": a_fork()}


def install_builder():
    """The builder returns CURRENT['fork'] for 1h and nothing for 1d."""
    from analysis import pitchfork as pf
    pf.build_fork_contained = lambda sym, df, tf, atr: CURRENT["fork"] if tf == "1h" else None
    pf.last_reject_reason = lambda: None
    pf.last_scan_depth = lambda: 0


_MIN = [0]


def run(eng, o, h, l, c):
    """One ForkEngine run with ONE newly closed 1m bar (df_1m[-2]); the frames exist."""
    import pandas as pd
    _MIN[0] += 1
    t0 = pd.Timestamp("2026-09-23 12:00", tz="America/New_York") + pd.Timedelta(minutes=_MIN[0])
    df1 = pd.DataFrame({"open": [o, c], "high": [h, c], "low": [l, c], "close": [c, c]},
                       index=[t0, t0 + pd.Timedelta(minutes=1)])
    frame = pd.DataFrame({"open": [100.0] * 30, "high": [101.0] * 30, "low": [99.0] * 30, "close": [100.0] * 30})
    eng._last_run = 0.0                                         # the 60s interval is not under test
    eng.run({"symbol": "QQQ", "data": {"1h": frame, "1d": frame}, "df_1m": df1})


def new_engine(store=None):
    from data.derived_store import DerivedStore
    from derived.forks import ForkEngine
    store = store or DerivedStore(tempfile.mktemp(dir=WORK, prefix="d-", suffix=".db"))
    return ForkEngine(store, "QQQ"), store


def breach(eng):
    run(eng, 99.0, 99.1, 97.9, 97.95)                           # closes beyond the lower rail (98)
    run(eng, 97.94, 98.0, 97.9, 97.93)                          # and opens beyond -> BREACHED


def inv_rows(st):
    return st.conn.execute("SELECT reject_reason FROM fork_series WHERE reject_reason LIKE 'INVALIDATED%'").fetchall()


def _f1():
    CURRENT["fork"] = a_fork(); eng, st = new_engine()
    run(eng, 100.0, 100.2, 99.8, 100.0)                         # served
    served_before = "1h" in eng.last_forks
    breach(eng)
    rows = inv_rows(st)
    return (served_before and "1h" in eng.last_forks and not rows), \
        f"served before {served_before}; after {'1h' in eng.last_forks}; INVALIDATED rows {rows}"


def _f2():
    CURRENT["fork"] = a_fork(); eng, st = new_engine()
    run(eng, 100.0, 100.2, 99.8, 100.0); breach(eng)
    run(eng, 97.9, 98.0, 97.8, 97.9)                            # the builder rebuilds the SAME fork
    return ("1h" in eng.last_forks), f"served: {'1h' in eng.last_forks}"


def _f3():
    CURRENT["fork"] = a_fork(); eng, st = new_engine()
    run(eng, 100.0, 100.2, 99.8, 100.0); breach(eng)
    ident = tuple(round(p_.price, 4) for p_ in (CURRENT["fork"].p0, CURRENT["fork"].p1, CURRENT["fork"].p2))
    st.append_forks([("QQQ", "1h", 1.0, 0, "INVALIDATED: lower rail breached at 0", 0, "up",
                      None, ident[0], None, ident[1], None, ident[2], None, None, 0.0, None, None, None, None, None)])
    eng2, _ = new_engine(store=st)                              # a restart over r115's rows
    run(eng2, 100.0, 100.2, 99.8, 100.0)
    return ("1h" in eng2.last_forks), f"served after restart: {'1h' in eng2.last_forks}"


def _f4():
    CURRENT["fork"] = a_fork(); eng, st = new_engine()
    run(eng, 100.0, 100.2, 99.8, 100.0); breach(eng)
    CURRENT["fork"] = None                                      # the BUILDER cannot build one
    run(eng, 100.0, 100.2, 99.8, 100.0)
    CURRENT["fork"] = a_fork()
    return ("1h" not in eng.last_forks), f"served with no build: {'1h' in eng.last_forks}"


def _f5():
    CURRENT["fork"] = a_fork(); eng, st = new_engine()
    run(eng, 99.0, 99.2, 98.0, 98.6)                            # wick reaches 98, closes inside
    run(eng, 98.6, 98.9, 97.95, 98.4)                           # wick past 98, closes back inside
    return ("1h" in eng.last_forks and not inv_rows(st)), f"served {'1h' in eng.last_forks}; rows {inv_rows(st)}"


def _f6():
    """30 minutes into the forming hour, a rail of slope $1/bar is read $0.50
    past its value at the hour's start (r116). The fork stand-in carries a
    real slope here; the level engine reads it through tines_now."""
    import time as _t
    import derived.levels as L
    from data.derived_store import DerivedStore
    f = a_fork()
    f.slope = 1.0
    f.upper_at = lambda i: 102.0 + 1.0 * (i - 20.0)
    fe = types.SimpleNamespace(last_forks={"1h": f}, last_idx={"1h": 20.0},
                               last_bar_start={"1h": _t.time() - 1800.0})
    lv = L.LevelEngine(DerivedStore(tempfile.mktemp(dir=WORK, prefix="d6-", suffix=".db")), "QQQ", forks=fe)
    up = [x for x in lv.tines_now(101.0) if x["provenance"] == "fork1h/upper"]
    got = up[0]["price"] if up else None
    return (got is not None and abs(got - 102.5) < 0.02), f"upper rail read at {got} (want ~102.50, hour start 102.00)"

def _f7():
    """The level engine sees the same breach on a fork the ForkEngine still holds
    (its interval had not come round): the rails are NOT withdrawn by it."""
    from data.derived_store import DerivedStore
    import derived.levels as L
    import pandas as pd
    fe = types.SimpleNamespace(last_forks={"1h": a_fork()}, last_idx={"1h": 20.0})
    st = DerivedStore(tempfile.mktemp(dir=WORK, prefix="dl-", suffix=".db"))
    lv = L.LevelEngine(st, "QQQ", forks=fe)
    for o, h, l, c in ((99.0, 99.1, 97.9, 97.95), (97.94, 98.0, 97.9, 97.93)):
        _MIN[0] += 1
        t0 = pd.Timestamp("2026-09-23 12:00", tz="America/New_York") + pd.Timedelta(minutes=_MIN[0])
        df = pd.DataFrame({"open": [o, c], "high": [h, c], "low": [l, c], "close": [c, c]},
                          index=[t0, t0 + pd.Timedelta(minutes=1)])
        lv.derive({"symbol": "QQQ", "price": c, "df_1m": df})
    n = len(lv.tines_now(97.9))
    ev = st.conn.execute("SELECT count(*) FROM level_event WHERE event='INVALIDATED'").fetchone()[0]
    return (n == 3 and ev == 0), f"rails still served by the level engine: {n}; INVALIDATED rows it wrote: {ev}"



def _f8():
    """The r114 -> r115 handover: r114 recorded its invalidation in level_event
    with the identity as ((price, kind), ...). That fork is still refused."""
    CURRENT["fork"] = a_fork()
    eng, st = new_engine()
    import time as _t
    key = tuple((round(p_.price, 4), "low") for p_ in (CURRENT["fork"].p0, CURRENT["fork"].p1, CURRENT["fork"].p2))
    st.insert_level_event(("QQQ", "QQQ:fork1h/lower:0.00", "2026-09-23 14:42:00-04:00", _t.time(), "INVALIDATED",
                           98.0, "support", "fork1h/lower", 0.0, repr(key), 0, 97.9))
    run(eng, 100.0, 100.2, 99.8, 100.0)
    return ("1h" in eng.last_forks), f"served despite r114's row: {'1h' in eng.last_forks}"


install_builder()
guard("F1 a 1m rail breach does NOT stop the ForkEngine serving the fork; no INVALIDATED row", _f1)
guard("F2 the builder's rebuild of the same fork is served", _f2)
guard("F3 a restart over r115's INVALIDATED rows serves the fork (ignored)", _f3)
guard("F4 when the BUILDER cannot build, the fork is not served — the builder judges", _f4)
guard("F5 a touch changes nothing (served, no INVALIDATED row)", _f5)
guard("F6 rails are read at the CURRENT minute, not the forming hour's start", _f6)
guard("F7 the LEVEL engine seeing a breach does not withdraw the rails — not its call", _f7)
guard("F8 r114's level_event INVALIDATED row is ignored — the fork is served", _f8)

import shutil
shutil.rmtree(WORK, ignore_errors=True)
print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
