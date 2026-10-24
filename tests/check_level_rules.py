#!/usr/bin/env python3
"""
tests/check_level_rules.py  v1.0
THE OPERATOR'S HELD / BREACHED DEFINITIONS, DRIVEN CASE BY CASE.

v1.0  2026-09-23  OTV4TEST LVL.15 step 1 (unlanded WIP). Born RED where
      `derived/level_rules.py` does not exist — every check below becomes a
      NAMED failure, never a traceback (r39's rule for new checkers).

Each case is a hand-built run of 1m candles with the exact event list the
ruling requires. The fixtures are built from the operator's WORDS, not from
the code under test (§0.4): each carries the ruling it encodes.

  D1  a wick that REACHES a resistance and closes back under it is HELD
  D1b a wick that falls one cent SHORT of the level is nothing — no test
  D2  close beyond, next candle opens beyond -> BREACHED, stamped at the open
  D3  close beyond, next opens back inside and closes inside -> HELD at that
      close (the 09-23 "Correct")
  D4  close beyond, next opens inside but closes beyond AGAIN -> still
      pending; the open after that decides
  D5  a DEEP raid that reclaims is HELD — no depth tiers (the old code called
      a >0.75% pierce "beyond" and never a rejection)
  D6  ZONE: the near edge takes the test, a close INSIDE is NOT held (ruling
      b), the close back out is HELD
  D7  ZONE: a close beyond the NEAR edge but not the far one never breaches
      — the zone "stays live until the far edge is accepted"
  D8  ZONE: close beyond the FAR edge + next open beyond -> BREACHED
  D9  SUPPORT mirrors every rule (D1, D2, D3 on the low side)
  D10 a breach ENDS judgement — nothing after it is reported
  D11 RAIL: edges as a function of time — judged at each candle's own minute
  D12 RAIL gone (None) drops an open episode rather than inheriting it
  D13 one episode, one HELD: repeated closes on the held side do not re-fire
      until the wick tests again
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


try:
    from derived import level_rules as R
    _WHY = None
except Exception as exc:                                        # noqa: BLE001
    R, _WHY = None, f"derived/level_rules.py absent or unimportable: {type(exc).__name__}: {exc}"


def run(name, bars, edges, side, want):
    if R is None:
        check(name, False, _WHY)
        return
    try:
        got = R.judge(bars, edges, side)
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"raised {type(exc).__name__}: {exc}")
        return
    check(name, got == want, f"got {got} want {want}")


RES, SUP = "resistance", "support"
L = 100.00                                    # a single level: near == far
ZONE_RES = (100.00, 100.50)                   # resistance zone: near 100.00, far 100.50
ZONE_SUP = (99.50, 99.00)                     # support zone: near 99.50, far 99.00

# (ts, open, high, low, close)
run("D1 a wick that REACHES the level and closes under it is HELD",
    [(1, 99.80, 100.00, 99.70, 99.90)], (L, L), RES,
    [("TESTED", 1), ("HELD", 1)])
run("D1b one cent SHORT of the level is not a test",
    [(1, 99.80, 99.99, 99.70, 99.90)], (L, L), RES, [])
run("D2 close beyond, next opens beyond -> BREACHED at that open",
    [(1, 99.90, 100.20, 99.85, 100.10), (2, 100.12, 100.30, 100.05, 100.25)], (L, L), RES,
    [("TESTED", 1), ("BREACHED", 2)])
run("D3 close beyond, next opens back inside and closes inside -> HELD there",
    [(1, 99.90, 100.20, 99.85, 100.10), (2, 99.95, 100.02, 99.80, 99.85)], (L, L), RES,
    [("TESTED", 1), ("HELD", 2)])
run("D4 close beyond, open inside, close beyond again -> the NEXT open decides",
    [(1, 99.90, 100.20, 99.85, 100.10), (2, 99.98, 100.30, 99.95, 100.20),
     (3, 100.25, 100.40, 100.20, 100.35)], (L, L), RES,
    [("TESTED", 1), ("BREACHED", 3)])
run("D5 a DEEP raid (2% through) that reclaims is HELD — no depth tiers",
    [(1, 99.90, 102.00, 99.80, 99.95)], (L, L), RES,
    [("TESTED", 1), ("HELD", 1)])
run("D6 ZONE: close INSIDE is not held (ruling b); the close back out is HELD",
    [(1, 99.80, 100.30, 99.75, 100.20), (2, 100.20, 100.25, 99.85, 99.90)],
    ZONE_RES, RES,
    [("TESTED", 1), ("HELD", 2)])
run("D7 ZONE: closes past the NEAR edge but never the far one do not breach",
    [(1, 99.80, 100.30, 99.75, 100.20), (2, 100.22, 100.45, 100.10, 100.40),
     (3, 100.41, 100.48, 100.30, 100.35)], ZONE_RES, RES,
    [("TESTED", 1)])
run("D8 ZONE: close beyond the FAR edge + next open beyond -> BREACHED",
    [(1, 100.20, 100.70, 100.10, 100.60), (2, 100.62, 100.80, 100.55, 100.75)],
    ZONE_RES, RES,
    [("TESTED", 1), ("BREACHED", 2)])
run("D9 SUPPORT: a wick down to the level that closes above is HELD",
    [(1, 100.20, 100.30, 100.00, 100.10)], (L, L), SUP,
    [("TESTED", 1), ("HELD", 1)])
run("D9b SUPPORT: close below + next open below -> BREACHED",
    [(1, 100.10, 100.15, 99.80, 99.90), (2, 99.88, 99.95, 99.70, 99.75)], (L, L), SUP,
    [("TESTED", 1), ("BREACHED", 2)])
run("D9c SUPPORT zone: close inside is not held; close back above the near edge is",
    [(1, 99.80, 99.85, 99.20, 99.30), (2, 99.30, 99.70, 99.25, 99.60)], ZONE_SUP, SUP,
    [("TESTED", 1), ("HELD", 2)])
run("D10 a breach ENDS judgement — nothing after it is reported",
    [(1, 99.90, 100.20, 99.85, 100.10), (2, 100.12, 100.30, 100.05, 100.25),
     (3, 100.20, 100.22, 99.50, 99.60)], (L, L), RES,
    [("TESTED", 1), ("BREACHED", 2)])
# a rising rail: 100.00 at ts 1, +0.10 a minute
rail = (lambda ts: (100.00 + 0.10 * (ts - 1),) * 2)
run("D11 RAIL: each candle is judged against the rail AT ITS OWN MINUTE",
    [(1, 99.80, 99.95, 99.70, 99.90),          # misses 100.00
     (2, 99.95, 100.10, 99.90, 100.00),        # reaches 100.10 at ts 2, closes under -> HELD
     (3, 100.05, 100.15, 99.95, 100.10)],      # 100.15 < 100.20 at ts 3: no test
    rail, RES,
    [("TESTED", 2), ("HELD", 2)])
# the rail dies at ts 2 and a NEW fork's rail exists at ts 3. The old rail's
# pending breach (close beyond at ts 1) must NOT be completed by ts 3's open.
# ⚠️ The first cut had no ts 3, so a mutant that KEPT the stale state passed —
# a check with nothing after the gap cannot see what the gap should drop.
gone = (lambda ts: None if ts == 2 else (L, L))
run("D12 RAIL gone drops the open episode instead of inheriting it",
    [(1, 99.90, 100.20, 99.85, 100.10), (2, 100.12, 100.30, 100.05, 100.25),
     (3, 100.12, 100.30, 100.05, 100.25)], gone, RES,
    [("TESTED", 1), ("TESTED", 3)])
run("D13 one episode, one HELD — closes under without a new test do not re-fire",
    [(1, 99.80, 100.00, 99.70, 99.90), (2, 99.85, 99.95, 99.60, 99.70),
     (3, 99.70, 100.05, 99.65, 99.80)], (L, L), RES,
    [("TESTED", 1), ("HELD", 1), ("TESTED", 3), ("HELD", 3)])

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
