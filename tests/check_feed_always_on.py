#!/usr/bin/env python3
"""
tests/check_feed_always_on.py  v4.0

The feed subscribes whenever the box is up, and the RTH series stays pure.

v4.0  2026-08-20  Written with candle_feed v4.3 (the RTH gate removal).

WHY THIS EXISTS. Removing the clock gate makes every box stream 24 hours a day
for the first time in this project's life. Exactly one thing stands between that
and a corrupted tape: the v4.2 write guard, which must route a non-RTH bar to
<SYM>_EXT for EVERY interval — not just the 1h that has an extended
subscription. If that guard were 1h-only, overnight 1m and 5m bars would land in
the plain series and the tape would CHANGE CHARACTER MID-STREAM, which v4.2's
own header calls worse than the gap it replaced.

⚠️ IT EXECUTES THE ROUTER. `_on_candle` is driven with real timestamps at real
ET hours and the resulting store key is read back from the buffer. A source-text
check would pass against a guard that never runs.

⚠️ AND IT PINS THE ONE THING THAT MUST NOT HAVE BEEN REMOVED. MAINTENANCE is a
purpose, not a time; C3 asserts it still stands the feed down, and that it does
so UNCONDITIONALLY — the old block slept only until the next open, and
seconds_until_rth_open() returns 0 during RTH, so maintenance declared inside
the session used to fall through and connect.

BORN RED, verified 2026-08-20 against pristine HEAD c1531a6:
  C1 -> "feed still stands down outside RTH - the gate was not removed"

Run:  cd ~/options-trader-v4 && python3 tests/check_feed_always_on.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ET = ZoneInfo("America/New_York")
PROBLEMS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


def _ts(y: int, mo: int, d: int, h: int, mi: int) -> int:
    """ET wall-clock -> epoch ms, the way the vendor stamps a bar."""
    return int(datetime(y, mo, d, h, mi, tzinfo=ET).timestamp() * 1000)


def main() -> int:
    print("=" * 68)
    print("CHECK FEED ALWAYS-ON: 24h subscriptions, RTH series still pure")
    print("=" * 68)

    from data import candle_feed as cf

    # ── C1 the gate is gone ──────────────────────────────────────────────
    # Executed, not read: ask the predicate itself, with maintenance clear.
    prior = os.environ.get("OT_FEED_MODE")
    os.environ["OT_FEED_MODE"] = "service"
    cf.FEED_MODE = "service"
    cf.CandleFeed._maint_said = False
    fn = getattr(cf.CandleFeed, "_feed_stood_down", None)
    check("C1 stand-down predicate exists under its v4.3 name", fn is not None,
          "_feed_stood_down missing - is this pre-v4.3 candle_feed?")
    if fn is None:
        print("  cannot continue without the predicate")
        return 1
    check("C1 feed does NOT stand down in service mode", fn() is False,
          "feed still stands down outside RTH - the gate was not removed")

    # ── C2 the dead scaffolding really is gone ───────────────────────────
    check("C2 warm-lead constant removed",
          not hasattr(cf, "FEED_WARM_LEAD_S"),
          "FEED_WARM_LEAD_S still defined - a knob nothing reads")
    check("C2 old predicate name removed",
          not hasattr(cf.CandleFeed, "_idle_outside_session"),
          "_idle_outside_session still present - two predicates, one job")

    # ── C3 MAINTENANCE survives, and is unconditional ────────────────────
    os.environ["OT_FEED_MODE"] = "maintenance"
    cf.FEED_MODE = "maintenance"
    cf.CandleFeed._maint_said = False
    check("C3 maintenance still stands the feed down", fn() is True,
          "maintenance no longer stands down - the hard-off was removed too")
    os.environ["OT_FEED_MODE"] = prior if prior is not None else "service"
    cf.FEED_MODE = (prior or "service")
    cf.CandleFeed._maint_said = False

    # ── C4 THE ONE THAT MATTERS: overnight bars segregate, EVERY interval ─
    # A 24h feed produces overnight 1m/5m/15m for the first time. If the write
    # guard were 1h-only these would land in the plain series.
    feed = cf.CandleFeed.__new__(cf.CandleFeed)
    feed.buffer = {}
    feed._rth_moved = {}
    feed.symbol_map = {}
    feed._unmapped_seen = set()

    # ⚠️ DRIVE THE REAL ROUTER. `_on_candle` takes ONLY the candle and derives
    # base/interval/ext from the echoed event_symbol via symbol_map — the exact
    # resolution FEED.2 got wrong. Constructing the echo format and registering
    # symbol_map by hand is what makes this a routing test rather than a test of
    # arguments I chose.
    class _C:                      # minimal candle the handler reads
        def __init__(self, ts, ev):
            self.event_symbol = ev
            self.time = ts
            self.open = self.high = self.low = self.close = 100.0
            self.volume = 1.0

    # v4.1 — the echoes now carry `tho=true`, because that is what the PLAIN
    # (RTH) subscription actually receives. The first draft omitted it and
    # therefore drove the EXTENDED route while claiming to test the plain one —
    # a fixture written from the same inverted assumption as the parser it sat
    # next to. Copied from the journal, NVDA 2026-08-21.
    _ECHO = {"1m": "m,tho=true", "5m": "5m,tho=true", "15m": "15m,tho=true",
             "1h": "h,tho=true", "1d": "d,tho=true"}

    def _fire(interval: str, ts: int) -> str:
        """Push one PLAIN-route bar through the handler; return where it landed."""
        ev = "TEST{=%s}" % _ECHO[interval]
        feed.symbol_map[("TEST", interval, False)] = "TEST"
        feed.buffer.clear()
        feed._on_candle(_C(ts, ev))
        keys = [k for k in feed.buffer if k[1] == interval]
        return keys[-1][0] if keys else "<nothing>"

    # Wednesday 2026-08-19: 02:00 ET is overnight, 10:00 ET is RTH.
    cases = [("1m", 2, 0, False), ("5m", 2, 0, False), ("15m", 2, 0, False),
             ("1m", 10, 0, True), ("5m", 10, 0, True), ("15m", 10, 0, True)]
    for interval, hh, mm, expect_rth in cases:
        landed = _fire(interval, _ts(2026, 8, 19, hh, mm))
        want = "TEST" if expect_rth else "TEST_EXT"
        check(f"C4 {interval} @ {hh:02d}:{mm:02d} ET -> {want}", landed == want,
              f"landed under {landed!r}, wanted {want!r} - the plain RTH series "
              f"is being contaminated by overnight bars")

    # A daily bar is stamped at midnight and must NOT be segregated.
    check("C4 1d bar is not segregated",
          _fire("1d", _ts(2026, 8, 19, 0, 0)) == "TEST",
          "a daily bar was routed to _EXT - the daily series would silently die")

    # ── C5 the weekend case ──────────────────────────────────────────────
    # A 24h feed is up on Saturday for the first time too.
    check("C5 Saturday bar segregates to _EXT",
          _fire("1m", _ts(2026, 8, 22, 12, 0)) == "TEST_EXT",
          "a weekend bar landed in the plain series")

    print("=" * 68)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        print("  A 24h feed with a leaky write guard is worse than the gate it")
        print("  replaced: a gap announces itself, a series that changes")
        print("  character mid-stream does not.")
        return 1
    print("  ALL GREEN - feed runs whenever the box is up; plain series is RTH-only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
