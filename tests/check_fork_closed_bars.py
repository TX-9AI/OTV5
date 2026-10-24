#!/usr/bin/env python3
"""
tests/check_fork_closed_bars.py  v1.0
THE 1h FORK IS BUILT FROM CLOSED HOURLY BARS ONLY — driven through ForkEngine.run.

v1.0  2026-09-23  OTV4TEST r117. Born RED at r116, whose builder was handed the
      1h frame WITH its still-forming bar.

The operator, 2026-09-23: "Closed hourly. I like that." The forming bar's close
moves every minute; the builder read it, and the 1h fork flipped between two
first anchors inside one hour (fork_series 09-23: 14:05 -> 14:10).

  C1 while the newest 1h bar is forming, the builder is NOT handed it
  C2 once that bar has closed (now >= start + 60 min) it IS handed it
  C3 last_idx / last_bar_start still name the forming bar (the rail walk of
     r116 reads the current minute, not the last closed bar)
  C4 the forming bar's close moving inside the hour cannot change the fork:
     a builder whose answer depends on the newest bar's close serves ONE fork
     across two runs in the same hour
  C5 the 1d frame is handed through unchanged — not ruled
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import glob as _glob                                             # r106 venv bootstrap
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

FAILED, RAN = [], []
WORK = tempfile.mkdtemp(prefix="chk_forkclosed-")
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


SEEN = {}                                                        # tf -> frame the builder was handed


def a_fork(anchor):
    P = lambda i, p: types.SimpleNamespace(idx=i, price=p, kind="low")   # noqa: E731
    return types.SimpleNamespace(slope=0.0, direction="up", filters_passed=(),
                                 p0=P(1.0, anchor), p1=P(5.0, anchor + 4), p2=P(9.0, anchor + 1),
                                 upper_at=lambda i: 102.0, median_at=lambda i: 100.0, lower_at=lambda i: 98.0)


def install_builder():
    """A spy: records the frame, and answers from the NEWEST bar it was handed
    (anchor = that bar's close), so a moving forming bar moves the fork."""
    from analysis import pitchfork as pf

    def build(sym, df, tf, atr):
        SEEN[tf] = df
        return a_fork(float(df["close"].iloc[-1])) if tf == "1h" else None
    pf.build_fork_contained = build
    pf.last_reject_reason = lambda: None
    pf.last_scan_depth = lambda: 0


def frame(newest_start, n=30, last_close=100.0, minutes=60):
    """n bars ending with one that STARTS at newest_start (epoch s), ET index."""
    import pandas as pd
    idx = pd.to_datetime([newest_start - (n - 1 - i) * minutes * 60 for i in range(n)], unit="s", utc=True)
    idx = idx.tz_convert("America/New_York")
    close = [100.0] * (n - 1) + [last_close]
    return pd.DataFrame({"open": close, "high": [c + 1 for c in close], "low": [c - 1 for c in close],
                         "close": close}, index=idx)


def new_engine():
    from data.derived_store import DerivedStore
    from derived.forks import ForkEngine
    return ForkEngine(DerivedStore(tempfile.mktemp(dir=WORK, prefix="d-", suffix=".db")), "QQQ")


def run(eng, f1h, f1d=None):
    SEEN.clear()
    eng._last_run = 0.0                                         # the 60s interval is not under test
    eng.run({"symbol": "QQQ", "data": {"1h": f1h, "1d": f1d if f1d is not None else f1h}})


def _c1():
    eng = new_engine(); f = frame(time.time() - 20 * 60)       # newest bar started 20 min ago
    run(eng, f)
    got = SEEN.get("1h")
    return (got is not None and len(got) == len(f) - 1 and got.index[-1] == f.index[-2]), \
        f"frame {len(f)} bars; builder handed {None if got is None else len(got)}"


def _c2():
    eng = new_engine(); f = frame(time.time() - 61 * 60)       # newest bar closed a minute ago
    run(eng, f)
    got = SEEN.get("1h")
    return (got is not None and len(got) == len(f)), f"frame {len(f)} bars; builder handed {None if got is None else len(got)}"


def _c3():
    eng = new_engine(); start = time.time() - 20 * 60; f = frame(start)
    run(eng, f)
    li, bs = eng.last_idx.get("1h"), eng.last_bar_start.get("1h")
    return (li == len(f) - 1 and bs is not None and abs(bs - float(f.index[-1].timestamp())) < 1e-6), \
        f"last_idx {li} (want {len(f) - 1}); last_bar_start {bs} (want {f.index[-1].timestamp()})"


def _c4():
    eng = new_engine(); start = time.time() - 20 * 60
    run(eng, frame(start, last_close=100.0)); a = eng.last_forks["1h"].p0.price
    run(eng, frame(start, last_close=103.0)); b = eng.last_forks["1h"].p0.price
    return (a == b), f"first anchor across two runs in one hour: {a} then {b}"


def _c5():
    eng = new_engine(); fd = frame(time.time() - 20 * 60, minutes=390)
    run(eng, frame(time.time() - 20 * 60), fd)
    got = SEEN.get("1d")
    return (got is not None and len(got) == len(fd)), f"1d frame {len(fd)} bars; builder handed {None if got is None else len(got)}"


install_builder()
guard("C1 while the newest 1h bar is forming, the builder is not handed it", _c1)
guard("C2 once it has closed, the builder is handed it", _c2)
guard("C3 last_idx / last_bar_start still name the forming bar", _c3)
guard("C4 the forming bar moving inside the hour cannot change the fork", _c4)
guard("C5 the 1d frame is handed through unchanged", _c5)

import shutil
shutil.rmtree(WORK, ignore_errors=True)
print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
