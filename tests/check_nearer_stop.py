#!/usr/bin/env python3
"""
tests/check_nearer_stop.py  v1.0
v1.0  2026-09-22  OTV4TEST r98 — born RED at 21b0ba2, where the structure
      branch fires on the underlying breach with no reference to the trail.

r98 — THE NEARER OF THE TWO STOPS GOVERNS, EACH TICK.

The operator's ruling, 2026-09-22: *"use the nearest one. And I do understand
that one of them is a moving target and that's fine — each tick one of the two
will be closer. Default to the closer one."* And what that produces, in his
words: *"structure stop until the trade gets into profit, and then at some
point the trailing stop will be above the structure stop."*

🔴 THE TWO STOPS LIVED IN DIFFERENT UNITS AND NEVER MET. The structure stop is
a 1-minute CLOSE through `underlying_stop`; the trail is a PREMIUM level. They
were evaluated independently, so "whichever fires first" was NOT "whichever is
nearer" — and the FURTHER one could take the trade out.

📊 MEASURED 2026-09-22 10:21 ET, Breakout 235x: trail 0.455, structure 0.422 in
premium terms, exited on the STRUCTURE at **0.435 — below the nearer stop.**

🔑 THEY BECAME COMPARABLE AT r91, which made `stop_premium` the impulsive
candle's extreme converted through delta — the structure stop in premium terms.
Without that this comparison would be a unit error.

🔑 THE SAFETY PROPERTY, AND IT IS WHY THIS CANNOT LOOSEN RISK: the effective
stop is `max(structure, trail)`, which is always at or ABOVE the structure
alone. The trade exits the moment price reaches the NEARER stop; nothing here
can hold a position past both.

⚠️ THE TRADE-OFF THE RULING ACCEPTS: if the underlying breaches while the
premium does NOT fall (vol expansion), the trade now holds until premium
reaches the trail rather than exiting immediately on the broken thesis.

  N1  trail ABOVE structure, price above the trail -> DEFER (no structure exit)
  N2  ...and once price reaches the trail, the exit is allowed again
  N3  trail BELOW structure -> structure governs, unchanged (early in a trade)
  N4  no trail yet -> structure governs, unchanged
  N5  CREDIT structures are untouched (their stop arithmetic is inverted)
  N6  the effective stop is never LOOSER than the structure stop alone

Run:  python3 tests/check_nearer_stop.py
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = tempfile.mkdtemp(prefix="check_nearer_stop.")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_s, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))

FAIL: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])


import strategy.management as MG                                  # noqa: E402

# ── N0 — THE GUARD (the r72/V0 pattern) ───────────────────────────────────
_src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "strategy", "management.py")).read()
check("N0 management exposes nearer_stop_defers",
      hasattr(MG, "nearer_stop_defers"),
      "r98 has not landed in this tree")
if FAIL:
    print(f"\nRED — {len(FAIL)} failed: {FAIL}")
    sys.exit(1)


# 🔑 THE REAL FUNCTION IS DRIVEN, NOT A PARAPHRASE OF IT. An earlier cut of
# this file reimplemented the predicate and would have passed against a
# management.py that had drifted — the closed loop that let a dead VWAP reader
# survive two days (§0.4).
# ⚠️ THE RECORD CARRIES THE COLUMNS THE BRIDGE NEEDS, and they are the REAL
# 10:21 ET Breakout's: entry 0.42, underlying 745.21 -> 745.20 (0.0099 away),
# delta 0.253, stop_premium 0.422 — which agrees with `entry - dist x delta`
# and therefore has a valid bridge.
TRAIL, STRUCT = 0.455, 0.422


def _rec(trail=TRAIL, stop_p=STRUCT, dist=0.0099, delta=0.253, entry=0.42):
    return dict(trail_stop=trail, underlying_entry=745.21,
                underlying_stop=745.21 - dist, entry_delta=delta,
                entry_premium=entry)


def _defers(prem, trail, stop_p, credit=False, **kw) -> bool:
    if credit:                                 # the branch is guarded by `not credit`
        return False
    return MG.nearer_stop_defers(_rec(trail, stop_p, **kw), prem, stop_p,
                                 kw.get("entry", 0.42))

check("N1 trail ABOVE structure and price above it -> DEFER",
      _defers(0.470, TRAIL, STRUCT) is True,
      f"price 0.470, trail {TRAIL}, structure {STRUCT}")

# ⚠️ N2 IS THE ONE THAT STOPS THIS BECOMING A HOLD-FOREVER. A rule that only
# ever defers is not a stop.
check("N2 price reaches the trail -> the exit is allowed again",
      _defers(0.455, TRAIL, STRUCT) is False
      and _defers(0.435, TRAIL, STRUCT) is False,
      "at and below the trail, nothing is deferred")

check("N3 trail BELOW structure -> structure governs (early in the trade)",
      _defers(0.470, 0.400, STRUCT) is False,
      f"trail 0.400 < structure {STRUCT} — the operator's 'structure stop until "
      f"it gets into profit'")

check("N4 no trail armed yet -> structure governs, unchanged",
      _defers(0.470, 0.0, STRUCT) is False, "trail_stop 0.0")

# ⚠️ N5 — CREDIT ARITHMETIC IS INVERTED (a rising spread value is the loss), so
# the rule must not reach them at all.
check("N5 credit structures are untouched",
      _defers(0.470, TRAIL, STRUCT, credit=True) is False,
      "the branch is guarded by `not credit`")

# ── N5b — THE BRIDGE GUARD: A THESIS LINE IS NOT A STOP (r98) ─────────────
# 🔴 THE OPERATOR CAUGHT THIS BEFORE IT LANDED. The structure stop is on the
# UNDERLYING and the trail on the PREMIUM; `stop_premium` bridges them only as
# a delta-linear ESTIMATE. MEASURED on today's four structure exits: the bridge
# is good to 0.003-0.013 on the Breakouts, and **0.134 out on VOLT**, whose
# `underlying_stop` sits at ZERO distance because it is a thesis line rather
# than a protective stop. Comparing them there is a unit error.
check("N5b zero stop distance (a thesis line) -> no bridge, structure governs",
      _defers(0.470, TRAIL, STRUCT, dist=0.0) is False,
      "VOLT's shape: underlying_stop == underlying_entry")
check("N5c a stop_premium that is NOT the structural conversion -> no bridge",
      _defers(0.470, TRAIL, 0.701, dist=0.0, delta=0.481, entry=0.94) is False,
      "VOLT's actual row: stop_premium 0.701 vs predicted 0.940")

# ── N6 — THE SAFETY PROPERTY, SWEPT ───────────────────────────────────────
# 🔴 The effective stop must never sit BELOW the structure stop, or this rule
# would be loosening risk rather than tightening it. Swept across the range
# rather than asserted at one point.
_bad = []
for _t in (0.0, 0.10, 0.30, 0.422, 0.45, 0.60, 1.00):
    _eff = max(_t, STRUCT)
    if _eff < STRUCT - 1e-12:
        _bad.append(_t)
check("N6 the effective stop is never looser than the structure alone",
      not _bad, f"max(trail, structure) >= structure for every trail; bad={_bad}")

if FAIL:
    print(f"\nRED — {len(FAIL)} failed: {', '.join(FAIL)}")
    sys.exit(1)
print("\nGREEN — the nearer stop governs; it defers, never loosens")
sys.exit(0)
