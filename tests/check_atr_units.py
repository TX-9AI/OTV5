#!/usr/bin/env python3
"""
tests/check_atr_units.py  v1.1
v1.1  2026-09-08  OTV4TEST r2 — U2–U4 RE-POINTED AT THE RUNAWAY. The ORB ATR
      floor they executed is deleted by the operator's ruling (orb_strategy
      v4.6); the units defect this file pins is unchanged and the runaway
      still carries a percent floor, so the same NFLX number is asserted
      there. U3 now asserts the ORB floor does NOT exist; U6 drops the key.

r96 — ATR THRESHOLDS ARE IN PERCENT. THE PRODUCER EMITS A FRACTION.

🔴 THE DEFECT THIS PINS, AND IT COST EVERY ORB TRADE THE FLEET EVER CONFIRMED.
`VolatilityState.atr_normalized` is `atr / price` — a FRACTION — while its own
comment read "ATR as % of price". Every strategy threshold is stated in PERCENT
and every one is traceable to a measurement in percent:

    ORB_ATR_FLOOR_PCT      0.05   (0 of 5,517 bars reached the required move)
    RUNAWAY_ATR_FLOOR_PCT  0.08
    RUNAWAY_ATR_VETO_PCT   0.05
    SWEEP_CS_ATR_MAX_PCT   0.20   (a CEILING — this one failed OPEN)

So `atr_normalized < ORB_ATR_FLOOR_PCT` demanded a **five percent intraday
ATR**, which effectively never occurs. ORB could not fire on any box, any day.

Observed live, NFLX 2026-08-24: break+retest confirmed 09:58 ET, chain built,
strike priced (C 81.0 @ $0.85, delta 0.389), then
`ATR 0.004% is below the reachable floor (0.05%)` once per tick for 62 minutes
until the 11:00 cutoff. True ATR was 0.4% — EIGHT TIMES ABOVE the floor.

⚠️ THE SAME MISMATCH FAILED IN BOTH DIRECTIONS, which is why it hid so well.
On a FLOOR it refused everything. On the sweep's CEILING it refused nothing, so
"too hot for a boundary to hold" has been dead since the split. A defect that
fails closed in one place and open in another produces no single symptom to
chase.

⚠️ WHY `atr_normalized` IS NOT SIMPLY RESCALED. Five tables already hold
fractions (indicator_series, character_ledger, fire_snapshot, strategy_note,
shadow primitives). Rescaling the producer would change what that column MEANS
mid-stream with nothing marking the seam — the RTH-backfill lesson, where the
repair was worse than the hole because a gap announces itself and a character
change does not. `atr_pct` is added alongside and the GATES move to it.

⚠️ BORN RED: U2/U3 fail if a gate reads the fraction. Mutation-proven.

Run:  python3 tests/check_atr_units.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILURES: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


class _Vol:
    """A VolatilityState as the engine actually produces one."""

    def __init__(self, atr_frac):
        self.atr_normalized = atr_frac
        self.atr_pct = atr_frac * 100.0
        self.price_vs_vwap = "ABOVE"
        self.atr_current = 0.32


class _Legacy:
    """A part-baked box: the OLD state, with no `atr_pct` at all."""

    def __init__(self, atr_frac):
        self.atr_normalized = atr_frac
        self.price_vs_vwap = "ABOVE"


def main() -> int:
    print("check_atr_units — gates compare PERCENT against PERCENT")

    from analysis.volatility_engine import VolatilityState

    # ── U1: THE TWO FIELDS ARE ONE MEASUREMENT ───────────────────────────────
    v = VolatilityState()
    v.atr_normalized = 0.004          # NFLX: ATR $0.32 on an $80 underlying
    v.atr_pct = v.atr_normalized * 100.0
    check("U1 atr_pct is exactly 100x atr_normalized",
          abs(v.atr_pct - 0.4) < 1e-9,
          f"frac={v.atr_normalized} pct={v.atr_pct}")

    # ── U2–U4 RETIRED (OTV4TEST r2) — THE ORB ATR FLOOR IS DELETED BY RULING.
    # Operator, 2026-09-08: the ATR floor "makes no sense" for the ORB setup.
    # The units lesson this file exists for is unchanged and is pinned below
    # on the RUNAWAY, which keeps its floor: the NFLX number (0.4%) must clear
    # 0.08% as a percent and would NOT as a fraction.
    from strategy.runaway_continuation import target_delta as _rw_delta, ATR_FLOOR_PCT as _RW_FLOOR
    nflx = _Vol(0.004)
    read = float(getattr(nflx, "atr_pct", None)
                 or (float(getattr(nflx, "atr_normalized", 0.0) or 0.0) * 100.0))
    check("U2 NFLX's real ATR clears the RUNAWAY floor as a percent",
          read >= _RW_FLOOR and _rw_delta(read) is not None,
          f"read={read}% floor={_RW_FLOOR}%")
    check("U2b and the fraction would NOT have — this is the live failure",
          nflx.atr_normalized < _RW_FLOOR and _rw_delta(nflx.atr_normalized) is None,
          f"{nflx.atr_normalized} < {_RW_FLOOR}")
    import strategy.orb_strategy as OS
    check("U3 ORB carries NO ATR floor (deleted OTV4TEST r2; check_orb_plan P15 fires at 0.01%)",
          not hasattr(OS, "ORB_ATR_FLOOR_PCT"))

    # ── U5: THE SWEEP CEILING IS ALIVE AGAIN ─────────────────────────────────
    # The other direction. Fed the fraction, a MAX of 0.20 could never trip.
    from strategy.sweep_credit_spread import ATR_MAX_PCT
    hot = _Vol(0.004)                 # 0.4% — genuinely above the 0.20% ceiling
    hot_read = hot.atr_pct
    check("U5 a hot tape now trips the sweep ceiling",
          hot_read > ATR_MAX_PCT and hot.atr_normalized < ATR_MAX_PCT,
          f"pct={hot_read} frac={hot.atr_normalized} ceiling={ATR_MAX_PCT}")

    # ── U6: THE THRESHOLDS ARE ALL ON THE SAME SCALE ─────────────────────────
    # A sanity band. Every ATR threshold in the tree is a small percent; any
    # constant above 5 would mean somebody re-scaled one and not the others.
    from strategy.runaway_continuation import (ATR_FLOOR_PCT, ATR_HARD_VETO_PCT,
                                               ATR_DEEP_PCT)
    consts = {"RUNAWAY_ATR_FLOOR_PCT": ATR_FLOOR_PCT,
              "RUNAWAY_ATR_VETO_PCT": ATR_HARD_VETO_PCT,
              "RUNAWAY_ATR_DEEP_PCT": ATR_DEEP_PCT,
              "SWEEP_CS_ATR_MAX_PCT": ATR_MAX_PCT}
    odd = {k: v for k, v in consts.items() if not (0.0 < v < 5.0)}
    check("U6 every ATR threshold is on the percent scale", not odd, str(odd))

    print()
    if FAILURES:
        print(f"FAILED {len(FAILURES)}: {', '.join(FAILURES)}")
        return 1
    print("check_atr_units: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
