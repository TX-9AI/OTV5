#!/usr/bin/env python3
"""
tests/check_bar_final_grace.py  v5.0
v5.0  2026-10-28  OTV5 r51 (BAR.2) — NO TICK READS A BAR IN THE FIRST SECONDS AFTER ITS MINUTE ENDS.
      CRM 2026-10-28, trade 98806a54: at 09:49:00.84 ET the Runaway was cut on runaway_thesis_dead, "1m close 241.78
      back through 242.15 (band 0.300)" (line 241.85); the feed store's final 09:48 bar closed 241.93, above the line,
      and CRM ran to 243.75. r44's closed_pos had (rightly, by time) taken the just-ended 09:48 row, which the feed had
      not finished. Across 14 boxes that day, 12 of 38 logged 1m-close decisions in the first 2 s of a minute read a
      close the final bar does not have; 0 of 14 at 2 s or later. utils.time_utils.bar_grace_wait() says how long to
      wait (BAR_FINAL_GRACE_S = 3 s past each minute boundary) and main_loop sleeps it before every tick.

  G1  the helper: CRM's tick at 09:49:00.84 waits 2.16 s; at the boundary itself 3.0 s (each + a 1 ms margin); at :02.999 a hair; at
      :03.0, :15, :45.2 and :59.9 nothing; a datetime and an epoch agree; junk never raises and an unreadable
      clock answers 0.0 (it can never stall the loop)
  G2  main_loop sleeps bar_grace_wait() BEFORE tick_start is taken, as the first act of every pass of its loop
      (read from main.py's source: the loop body, not a comment)
  G3  the loop's cadence under the helper: a simulated RTH session (15 s poll, tick work 0.05-6 s, floor-watch
      wakes ending the sleep early at random) never starts a tick inside the grace window, and settles 3 s past
      the boundary; the same simulation without the helper starts ticks inside it (the 2026-10-28 state)
  G4  closed_pos is unchanged at r44's cases: at 09:49:03.0 with the 09:48 row newest it is -1 (the final bar),
      with a 09:49 forming row it is -2

Born red on ce32c3c at G1, G2, G3a and G3c.
Run:  python3 tests/check_bar_final_grace.py
"""
import ast
import datetime as D
import os
import random
import sys
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "CRM")
ET = ZoneInfo("America/New_York")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def at(h, m, s=0.0):
    return D.datetime(2026, 10, 28, h, m, int(s), int(round((s % 1) * 1e6)), tzinfo=ET)


print("check_bar_final_grace (BAR.2)")
try:
    from utils import time_utils as TU
    wait = getattr(TU, "bar_grace_wait", None)
except Exception as exc:                                        # noqa: BLE001
    TU, wait = None, None
    print("  import failed:", exc)

# ── G1 the helper ─────────────────────────────────────────────────────────────
if wait is None:
    check("G1 bar_grace_wait exists in utils.time_utils", False, "missing")
else:
    w = wait(at(9, 49, 0.84))
    check("G1a CRM's 09:49:00.84 tick waits 2.16 s (+1 ms margin)", abs(w - 2.161) < 1e-6, f"{w}")
    check("G1b at the boundary 09:49:00.0 it waits the full 3.0 s (+1 ms)", abs(wait(at(9, 49, 0.0)) - 3.001) < 1e-9)
    w2 = wait(at(9, 49, 2.999))
    check("G1c at :02.999 a hair (0 < w <= 0.003)", 0 < w2 <= 0.003, f"{w2}")
    zeros = [wait(at(9, 49, s)) for s in (3.0, 15.0, 45.2, 59.9)]
    check("G1d at :03.0, :15, :45.2, :59.9 no wait", zeros == [0.0] * 4, f"{zeros}")
    check("G1e a datetime and its epoch agree", wait(at(10, 5, 1.5)) == wait(at(10, 5, 1.5).timestamp()))
    try:
        junk = [wait(x) for x in ("09:49", object(), float("nan"))]
        ok = all(isinstance(v, float) and 0.0 <= v <= 3.001 for v in junk)
    except Exception as exc:                                    # noqa: BLE001
        ok, junk = False, exc
    check("G1f junk never raises and never waits past the grace", ok, f"{junk}")
    orig = TU.now_et
    TU.now_et = lambda: None
    try:
        check("G1g an unreadable clock answers 0.0", wait("junk") == 0.0)
    finally:
        TU.now_et = orig
    check("G1h BAR_FINAL_GRACE_S is 3.0", getattr(TU, "BAR_FINAL_GRACE_S", None) == 3.0)

# ── G2 main_loop sleeps it before tick_start ──────────────────────────────────
src = open(os.path.join(ROOT, "main.py")).read()
tree = ast.parse(src)
loop_fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main_loop"), None)
g2 = False
detail = "main_loop not found"
if loop_fn is not None:
    wl = next((n for n in ast.walk(loop_fn) if isinstance(n, ast.While)), None)
    body = wl.body if wl is not None else []
    seg = ast.get_source_segment
    idx_ts = next((i for i, n in enumerate(body) if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "tick_start" for t in n.targets)), None)
    before = body[:idx_ts] if idx_ts is not None else []
    text = "\n".join(seg(src, n) or "" for n in before)
    g2 = idx_ts is not None and "bar_grace_wait" in text and "time.sleep(" in text
    detail = f"statements before tick_start: {len(before)}"
check("G2 main_loop sleeps bar_grace_wait() before tick_start, first in each pass", g2, detail)


# ── G3 cadence ────────────────────────────────────────────────────────────────
def simulate(use_helper, seed=7):
    rnd = random.Random(seed)
    t = at(9, 30, 0.4).timestamp()
    end = at(16, 0).timestamp()
    starts = []
    while t < end:
        if use_helper and wait is not None:
            t += wait(t)
        starts.append(t)
        t += rnd.uniform(0.05, 6.0)                             # the tick's own work
        left = max(0.0, 15.0 - (t - starts[-1]))
        if rnd.random() < 0.08:                                 # a floor-watch wake ends the sleep early
            left = rnd.uniform(0.0, left)
        t += left
    return starts


inside = lambda ts: [s for s in ts if (s % 60.0) < 3.0]
new = simulate(True)
old = simulate(False)
check("G3a with the helper no tick starts inside the grace window", wait is not None and not inside(new),
      f"{len(inside(new))} of {len(new)} ticks inside")
check("G3b without it (the 2026-10-28 loop) ticks do start inside it", len(inside(old)) > 0,
      f"{len(inside(old))} of {len(old)} ticks inside")
steady = [round(s % 15.0, 1) for s in new[-40:]]
check("G3c the steady cadence sits at or past 3 s after a boundary", all((s % 60.0) >= 3.0 for s in new[-40:]),
      f"phases {sorted(set(steady))[:6]}")

# ── G4 closed_pos unchanged ───────────────────────────────────────────────────
try:
    import pandas as pd
    idx = pd.DatetimeIndex([at(9, 46), at(9, 47), at(9, 48)])
    df = pd.DataFrame({"close": [242.18, 242.44, 241.93]}, index=idx)
    p1 = TU.closed_pos(df, at(9, 49, 3.0))
    df2 = pd.DataFrame({"close": [242.18, 242.44, 241.93, 242.16]},
                       index=pd.DatetimeIndex([at(9, 46), at(9, 47), at(9, 48), at(9, 49)]))
    p2 = TU.closed_pos(df2, at(9, 49, 3.0))
    check("G4 closed_pos at 09:49:03: 09:48 newest -> -1 (241.93), 09:49 forming -> -2 (241.93)",
          p1 == -1 and p2 == -2 and df.iloc[p1]["close"] == df2.iloc[p2]["close"] == 241.93, f"{p1} {p2}")
except Exception as exc:                                        # noqa: BLE001
    check("G4 closed_pos unchanged", False, f"{type(exc).__name__}: {exc}")

print("RESULT:", "FAIL " + ",".join(FAILED) if FAILED else "PASS")
sys.exit(1 if FAILED else 0)
