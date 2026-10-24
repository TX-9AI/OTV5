#!/usr/bin/env python3
"""
tests/check_pin_bounded.py  v1.0
v1.0  2026-09-01  r215 — A PIN IS A CLAIM ABOUT TODAY'S PRICE.

🔴 `pin_strike` WAS A BARE ARGMAX OVER THE WHOLE CHAIN. Nothing bounded it to
strikes near spot, so when net GEX is flat or noisy the argmax wanders. Measured
from the warehouse, 2026-08-31: GOOGL published TWENTY distinct pins spanning
245-450 in a single session — roughly bracketing a ~345 price — and AMZN
twenty-six spanning 212-275. Neither name moves 30% in a day. That is not a
magnet migrating; it is an argmax jumping as one strike edges past another.

🔑 A STRIKE 30% AWAY CANNOT PULL TODAY'S PRICE ANYWHERE, so it is not a pin
however large its net GEX. B3 keeps the WALLS unbounded on purpose: a wall is
allowed to be far away — that is what makes it a wall — and bounding those
would break the sweep's confluence read.

🔴 AND THE GUARD ALREADY EXISTED, WIRED TO NOTHING. `best_butterfly_center()`
documents "uses GEX pin strike if within max_distance of current price,
otherwise falls back to ATM" and has ZERO callers. It is deliberately still not
used: its ATM fallback INVENTS a pin where the chain published none, against
r208's ruling that "the apex IS the trade; a nearest-strike substitute is a
different one". B2 pins that out-of-range yields NO pin, never another one.

⚠️ AND ITS max_distance WAS 5.0 DOLLARS — meaningless across this fleet: $5 is
0.06% of SPX at 7,700 and 6% of NFLX at 83. The bound here is RELATIVE.

⚠️ 3% IS A PRIOR, NOT A FIT, and B5 requires the evidence to be recorded so it
can become one: `pin_dist_pct` and `pin_strike_raw` ride every evaluation.

Born red at 081ba60 (r214), where B1, B2 and B5 fail.
"""
from __future__ import annotations

import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

_fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


class _C:
    def __init__(self, k, g, oi, side):
        self.strike, self.gamma = float(k), g
        self.open_interest, self.option_type = oi, side


class _Ch:
    def __init__(self, calls, puts, spot):
        self.calls, self.puts, self.underlying_price = calls, puts, spot


def main():
    from data import gex_data as G

    if not hasattr(G, "PIN_MAX_DIST_PCT"):
        check("B0 PIN_MAX_DIST_PCT exists", False, "not implemented")
        print()
        print("FAILED 1: gex_data is pre-r215 (the pin argmax is unbounded)")
        return 1

    # ── B1 — THE 2026-08-31 GOOGL SHAPE: a huge net GEX 30% away ─────────
    spot = 345.0
    calls = [_C(345, 0.05, 5000, "call"), _C(450, 0.09, 9000, "call"),
             _C(347, 0.03, 3000, "call")]
    puts = [_C(345, 0.04, 4000, "put"), _C(245, 0.02, 1000, "put")]
    snap = G.compute_gex(_Ch(calls, puts, spot), spot)
    check("B1 a strike 30% from spot is not published as the pin",
          snap.pin_strike_raw == 450.0 and snap.pin_strike != 450.0,
          f"raw={snap.pin_strike_raw} pin={snap.pin_strike} "
          f"dist={snap.pin_dist_pct:.1%}")
    check("B1b and the pin that IS published is inside the bound",
          snap.pin_strike > 0
          and abs(snap.pin_strike - spot) / spot <= G.PIN_MAX_DIST_PCT,
          str(snap.pin_strike))

    # ── B2 — NOTHING IN RANGE MEANS NO PIN, NEVER A SUBSTITUTE ──────────
    # 🔴 THE CHECK THAT PROTECTS r208's RULING. An ATM fallback would fabricate
    # a pin the chain never published, and the butterfly centres its apex on it.
    far = [_C(500, 0.09, 9000, "call"), _C(520, 0.08, 8000, "call")]
    fp = [_C(500, 0.02, 500, "put")]
    s2 = G.compute_gex(_Ch(far, fp, spot), spot)
    check("B2 no strike within the bound yields NO pin, not an ATM fallback",
          s2.pin_strike == 0.0 and s2.pin_strike_raw > 0,
          f"pin={s2.pin_strike} raw={s2.pin_strike_raw}")

    # ── B3 — THE WALLS STAY UNBOUNDED, DELIBERATELY ─────────────────────
    check("B3 call_wall is still allowed to be far away",
          s2.call_wall > 0,
          "a wall IS distant — that is what makes it a wall (sweep reads it)")

    # ── B4 — THE BOUND IS RELATIVE, so one figure fits SPX and NFLX ─────
    # ⚠️ The dead helper's 5.0 DOLLARS is 0.06% of SPX and 6% of NFLX.
    for spot_v, near_k, far_k in ((7700.0, 7750.0, 9000.0), (83.0, 84.0, 120.0)):
        c = [_C(near_k, 0.05, 5000, "call"), _C(far_k, 0.09, 9000, "call")]
        p = [_C(near_k, 0.04, 4000, "put")]
        sn = G.compute_gex(_Ch(c, p, spot_v), spot_v)
        ok = sn.pin_strike == near_k
        check(f"B4 the bound scales: spot {spot_v:g} picks {near_k:g} not {far_k:g}",
              ok, f"got {sn.pin_strike}")

    # ── B5 — THE PRIOR IS RECORDED SO IT CAN BE FITTED ──────────────────
    # r208's discipline: a carried constant that nobody measured stays visible
    # in the data until somebody does.
    src = open(os.path.join(_root, "strategy", "gex_pin_butterfly.py"),
               encoding="utf-8").read()
    check("B5 pin_dist_pct and the raw argmax ride every evaluation",
          '"pin_dist_pct"' in src and '"pin_strike_raw"' in src
          and "pin_dist_pct" in src.split("PLAN_CHECKS")[1][:400],
          "so 3% can become a fit instead of staying a guess")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_pin_bounded: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
