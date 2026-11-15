#!/usr/bin/env python3
"""
tests/check_fizzle_fallbacks.py  v5.0
v5.0  2026-11-15  OTV5 r124 (AM.13 + AM.14) — FIZZLE NEVER READS THE WHOLE SESSION, AND A LOST DIAL IS SAID.
      The amnesty bucket (~/reviews/AMNESTY_BUCKET.md) found two silent fallbacks in
      ExitEngine._runaway_thesis_exits: an unreadable entry_time (or a since-entry filter that raised) graded
      fizzle on every closed bar of the day, pre-entry bars included (AM.13); a trend_strength.measure() failure
      dropped the acceptance_decay dial with no trace (AM.14).

  F1   a readable entry_time grades only the bars since entry: the pre-entry fizzle shape does NOT fire
  F2   🔴 an unreadable entry_time does NOT fire fizzle on the pre-entry bars (r123: it fired)
  F2b  ...and says so: _fizzle_read carries "SKIPPED", one WARNING per trade (two reads, one line)
  F2c  ...a missing (None) entry_time the same
  F3   🔴 a since-entry filter that raises (an untimed index) does NOT fall through to the whole session
  F4   a measure() that raises still drops only that dial (the same exit decision as a measure with no dial)
  F4b  ...and is said: one WARNING naming acceptance_decay and the exception type, and a note in _fizzle_read
  F5   the thesis line still runs when fizzle is skipped (a close back through the 50 still exits)
"""
import logging
import os
import sys
import tempfile
os.environ.setdefault("OT_COUNTERFACTUAL_DIR", tempfile.mkdtemp(prefix="cf_"))   # never the live log

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


class _Grab(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.lines = []

    def emit(self, rec):
        self.lines.append((rec.levelno, rec.getMessage()))


def _frame(rows, start="10:06", timed=True):
    import pandas as pd
    df = pd.DataFrame([{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in rows])
    if timed:   # the live frame is tz-aware ET (data/market_data.py)
        df.index = pd.date_range(f"2026-09-08 {start}", periods=len(rows), freq="1min", tz="America/New_York")
    return df


# X4's fizzle shape (tests/check_runaway_plan.py): higher-low broken + range contraction, price beyond the 50.
_FZ = [(101.6, 102.4, 101.5, 102.3), (102.3, 102.9, 102.2, 102.8),
       (102.8, 103.2, 102.6, 103.0), (103.0, 103.15, 102.95, 103.05),
       (103.05, 103.1, 102.98, 103.02), (103.02, 103.06, 102.97, 103.0),
       (103.0, 103.03, 102.5, 102.55),
       (102.55, 102.6, 102.5, 102.56)]


def main():
    import execution.exit_engine as XE
    grab = _Grab()
    XE.logger.addHandler(grab)
    XE.logger.setLevel(logging.DEBUG)
    xe = XE.ExitEngine(paper_trading=True)
    base = {"trade_id": "fz-1", "strategy": "RunawayContinuation", "direction": "long",
            "entry_premium": 1.00, "orb_range_high": 101.0, "orb_range_low": 100.0,
            "underlying_entry": 101.85}

    def run(rec, df):
        return xe._runaway_thesis_exits(rec, "long", 1.20, 1.00, 0.20, df)

    def warns(tid, needle):
        return [m for lv, m in grab.lines if lv >= logging.WARNING and tid[:8] in m and needle in m]

    fz = _frame(_FZ)
    # sanity: the shape fires when every bar is since entry
    r0 = run(dict(base, trade_id="fz-0", entry_time="2026-09-08T10:05:00-04:00"), fz)
    check("F0 (sanity) the shape fires fizzle when all its bars are since entry", "fizzle" in r0, r0)

    # entry at 10:12: only 10:12 is closed since entry (10:13 is the open bar) -> n < 4, nothing to grade
    r1 = run(dict(base, trade_id="fz-1", entry_time="2026-09-08T10:12:00-04:00"), fz)
    check("F1 a readable entry_time grades only the bars since entry (no fizzle on pre-entry bars)",
          "fizzle" not in r1, r1)

    rec2 = dict(base, trade_id="fz-2bad", entry_time="not-a-time")
    r2 = run(rec2, fz)
    check("F2 🔴 an unreadable entry_time does NOT fire fizzle on the whole session", "fizzle" not in r2, r2)
    run(rec2, fz)
    w2 = warns("fz-2bad", "fizzle SKIPPED")
    check("F2b ..._fizzle_read says SKIPPED and one WARNING per trade (two reads, one line)",
          "SKIPPED" in str(rec2.get("_fizzle_read")) and len(w2) == 1,
          f"read={rec2.get('_fizzle_read')!r} warnings={len(w2)}")

    rec2c = dict(base, trade_id="fz-2none", entry_time=None)
    r2c = run(rec2c, fz)
    check("F2c ...a missing entry_time the same", "fizzle" not in r2c and len(warns("fz-2none", "SKIPPED")) == 1,
          f"{r2c!r} read={rec2c.get('_fizzle_read')!r}")

    rec3 = dict(base, trade_id="fz-3idx", entry_time="2026-09-08T10:05:00-04:00")
    r3 = run(rec3, _frame(_FZ, timed=False))
    check("F3 🔴 a since-entry filter that raises does NOT fall through to the whole session",
          "fizzle" not in r3 and "filter failed" in str(rec3.get("_fizzle_read")) and len(warns("fz-3idx", "filter")) == 1,
          f"{r3!r} read={rec3.get('_fizzle_read')!r}")

    import analysis.trend_strength as TS
    _real = TS.measure
    try:
        class _NoDial:
            acc_delta = None
            acc_recent = None
        TS.measure = lambda *a, **k: _NoDial()
        r4a = run(dict(base, trade_id="fz-4a", entry_time="2026-09-08T10:05:00-04:00"), fz)

        def _boom(*a, **k):
            raise RuntimeError("synthetic")
        TS.measure = _boom
        rec4 = dict(base, trade_id="fz-4boom", entry_time="2026-09-08T10:05:00-04:00")
        r4 = run(rec4, fz)
        run(rec4, fz)
    finally:
        TS.measure = _real
    check("F4 a measure() that raises drops only that dial (same decision as no dial)", r4 == r4a, f"{r4!r} vs {r4a!r}")
    w4 = warns("fz-4boom", "acceptance_decay unreadable (RuntimeError")
    check("F4b ...one WARNING naming the dial and the exception, and a note in _fizzle_read",
          len(w4) == 1 and "acceptance_decay unreadable" in str(rec4.get("_fizzle_read")),
          f"warnings={len(w4)} read={rec4.get('_fizzle_read')!r}")

    dead = _frame([(101.8, 101.9, 101.2, 101.3), (101.3, 101.4, 101.2, 101.35), (101.35, 101.4, 101.3, 101.36)])
    r5 = run(dict(base, trade_id="fz-5", entry_time="garbage"), dead)
    check("F5 the thesis line still runs when fizzle is skipped", "thesis_dead" in r5, r5)


if __name__ == "__main__":
    main()
    print(f"\n{'FAIL' if FAILED else 'PASS'}: check_fizzle_fallbacks ({len(FAILED)} failed)")
    sys.exit(1 if FAILED else 0)
