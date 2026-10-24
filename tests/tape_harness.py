#!/usr/bin/env python3
"""
tests/tape_harness.py  v4.0
What precedes a PAYABLE move? Every bar of every session, mined with holdout.

v4.0  2026-08-19  Built at the OTV4 split. ROADMAP Phase 1, the escalation.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

WHY THE TRADE BOOK COULD NOT ANSWER THIS.
The v3 book contains only moments the v3 engine CHOSE TO LOOK AT. Every
condition measured on it came back ambient because the strategies' own gates had
already selected the population - ContinuationStrategy's ADX > 30 held on 91% of
good entries and 88% of bad ones, which is not a weak signal but a pre-filtered
one. **A condition cannot be measured on a population it selected.**
The tape was never filtered by anything. ~28 dates x 29 symbols x 390 bars is
~300,000 candidate moments against 366 usable trades.

THE BAR IS SET BY THE CHAIN, NOT CHOSEN.
`tests/chain_feasibility.py` on 110,162 contract observations: a 0.30-0.60 delta
0DTE contract needs a **0.50% underlying move to pay +10%** including the
round-trip spread, and the tape delivers that **in a specified direction on 47%
of bars within 90 minutes**. At +25%/40m - v3's actual setting - it was 22%.
**So the search is for 0.5% in 90 minutes.** Mining for anything smaller finds
patterns that cannot pay; mining for anything larger searches for something the
tape rarely does.

⚠️ HOLDOUT IS NOT OPTIONAL HERE. Searching 300,000 bars across ~30 conditions
WILL produce impressive-looking rules whether or not any signal exists. Sessions
are split by DATE - early dates mine, late dates verify - and **a rule that does
not survive the holdout is reported as FAILED, not quietly dropped.** Splitting
by date rather than at random matters: bars within a session are heavily
correlated, so a random split would leak the answer across the boundary.

⚠️ AND THE BASELINE IS THE HURDLE, NOT ZERO. If 47% of all bars clear the bar
upward, a rule firing on 49% of its selections has found nothing. Every rule is
reported as LIFT OVER BASE, and the base is printed first so it cannot be
forgotten.
"""

import argparse
import collections
import csv
import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OHLC = os.path.expanduser("~/day_trader_pro/ohlc")
POLLUTED = {"2026-08-14"}


def _wilson(k, n):
    if n == 0:
        return (0.0, 1.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def load(path):
    rows = []
    with open(path) as fh:
        for r in csv.DictReader(fh):
            try:
                rows.append((r["timestamp"][11:16], float(r["open"]),
                             float(r["high"]), float(r["low"]),
                             float(r["close"])))
            except Exception:                                  # noqa: BLE001
                continue
    return rows


def conditions(rows, i):
    """Everything true at the CLOSE of bar i. No lookahead, ever.

    ⚠️ ONE BAR OF LOOKAHEAD TURNS A PREDICTOR INTO A DESCRIPTION OF THE ANSWER,
    and it does not look wrong in the output - it just looks like a strong
    result. Every slice below ends at i inclusive.
    """
    if i < 40 or i + 1 >= len(rows):
        return None
    hs = [r[2] for r in rows[:i + 1]]
    ls = [r[3] for r in rows[:i + 1]]
    cs = [r[4] for r in rows[:i + 1]]
    os_ = [r[1] for r in rows[:i + 1]]
    c = cs[-1]
    hhmm = rows[i][0]
    mins = int(hhmm[:2]) * 60 + int(hhmm[3:]) - (9 * 60 + 30)

    day_hi, day_lo = max(hs), min(ls)
    rng = max(day_hi - day_lo, 1e-9)
    pos = (c - day_lo) / rng

    # session anchor (typical price, unweighted - no volume in these files)
    tp = [(hs[k] + ls[k] + cs[k]) / 3.0 for k in range(i + 1)]
    anchor = sum(tp) / len(tp)
    d_anchor = (c - anchor) / c * 100.0

    # 20-bar realised range as a volatility proxy
    r20 = [hs[k] - ls[k] for k in range(i - 19, i + 1)]
    atr20 = sum(r20) / 20.0
    atr_pct = atr20 / c * 100.0

    # 40-bar vs 10-bar range: is volatility expanding?
    r10 = sum(hs[k] - ls[k] for k in range(i - 9, i + 1)) / 10.0
    r40 = sum(hs[k] - ls[k] for k in range(i - 39, i + 1)) / 40.0
    expanding = r10 > r40 * 1.2
    contracting = r10 < r40 * 0.8

    # channel: slope and position within dispersion, 30 bars
    look = 30
    ys = cs[-look:]
    n = len(ys)
    mx = (n - 1) / 2.0
    my = sum(ys) / n
    den = sum((k - mx) ** 2 for k in range(n)) or 1e-9
    slope = sum((k - mx) * (ys[k] - my) for k in range(n)) / den
    resid = [ys[k] - (my + slope * (k - mx)) for k in range(n)]
    sd = (sum(x * x for x in resid) / n) ** 0.5 or 1e-9
    z = resid[-1] / sd
    slope_pct = slope / c * 100.0 * 30      # 30-bar slope as % of price

    # compression: 20-bar range unusually small vs the day
    coil = (max(hs[-20:]) - min(ls[-20:])) / rng

    # recent extreme taken?
    prior_hi20 = max(hs[-21:-1])
    prior_lo20 = min(ls[-21:-1])
    broke_up = hs[-1] > prior_hi20
    broke_dn = ls[-1] < prior_lo20
    held_up = broke_up and c > prior_hi20
    held_dn = broke_dn and c < prior_lo20

    # the bar itself
    o, h, l = os_[-1], hs[-1], ls[-1]
    bar_rng = max(h - l, 1e-9)
    body = abs(c - o) / bar_rng

    return {
        "_atr_pct": atr_pct,
        "vol EXPANDING (10b > 1.2x 40b)": expanding,
        "vol CONTRACTING (10b < 0.8x 40b)": contracting,
        "coiled (20b range < 25% of day)": coil < 0.25,
        "wide 20b range (> 60% of day)": coil > 0.60,
        "in top quartile of day range": pos > 0.75,
        "in bottom quartile of day range": pos < 0.25,
        "mid-range (25-75%)": 0.25 <= pos <= 0.75,
        "above session anchor": d_anchor > 0,
        "far above anchor (> 0.25%)": d_anchor > 0.25,
        "far below anchor (< -0.25%)": d_anchor < -0.25,
        "near anchor (|d| < 0.05%)": abs(d_anchor) < 0.05,
        "channel sloping up (> 0.2%/30b)": slope_pct > 0.2,
        "channel sloping down (< -0.2%/30b)": slope_pct < -0.2,
        "channel flat (|slope| < 0.1%)": abs(slope_pct) < 0.1,
        "at upper channel edge (z > 1)": z > 1,
        "at lower channel edge (z < -1)": z < -1,
        "mid-channel (|z| < 0.5)": abs(z) < 0.5,
        "broke 20b high": broke_up,
        "broke 20b low": broke_dn,
        "broke AND HELD 20b high": held_up,
        "broke AND HELD 20b low": held_dn,
        "decisive bar (body > 60%)": body > 0.60,
        "indecisive bar (body < 30%)": body < 0.30,
        "elevated vol (atr > 0.08%)": atr_pct > 0.08,
        "quiet vol (atr < 0.04%)": atr_pct < 0.04,
        "first hour": mins < 60,
        "midday (10:30-14:00)": 60 <= mins < 270,
        "power hour (15:00+)": mins >= 330,
    }


def outcome(rows, i, horizon, need_pct):
    """Did price move `need_pct` UP, and did it move DOWN, within `horizon`?"""
    seg = rows[i + 1:i + 1 + horizon]
    if len(seg) < horizon // 2:
        return None
    c = rows[i][4]
    if c <= 0:
        return None
    up = (max(r[2] for r in seg) - c) / c * 100.0
    dn = (c - min(r[3] for r in seg)) / c * 100.0
    return up >= need_pct, dn >= need_pct


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ohlc", default=OHLC)
    ap.add_argument("--need", type=float, default=0.50,
                    help="required move %% - set by chain_feasibility, not chosen")
    ap.add_argument("--horizon", type=int, default=90)
    ap.add_argument("--symbol", default="")
    ap.add_argument("--holdout-from", default="",
                    help="dates >= this verify; earlier dates mine. "
                         "Default: last third of dates.")
    ap.add_argument("--min-n", type=int, default=300)
    a = ap.parse_args(argv[1:])

    days = sorted(os.path.basename(d) for d in
                  glob.glob(os.path.join(os.path.expanduser(a.ohlc), "*"))
                  if os.path.isdir(d))
    days = [d for d in days if d not in POLLUTED]
    if not days:
        print("no sessions. ABSENT MEASUREMENT, not a null.")
        return 1
    cut = a.holdout_from or days[int(len(days) * 2 / 3)]

    mine, hold = [], []
    for day in days:
        for p in sorted(glob.glob(os.path.join(
                os.path.expanduser(a.ohlc), day, "*_ohlc_*.csv"))):
            sym = os.path.basename(p).split("_ohlc_")[0].upper()
            if a.symbol and sym != a.symbol.upper():
                continue
            try:
                rows = load(p)
            except Exception:                                  # noqa: BLE001
                continue
            rows = [r for r in rows if "09:30" <= r[0] <= "16:00"]
            if len(rows) < 120:
                continue
            bucket = hold if day >= cut else mine
            for i in range(40, len(rows) - 10):
                oc = outcome(rows, i, a.horizon, a.need)
                if oc is None:
                    continue
                cond = conditions(rows, i)
                if cond is None:
                    continue
                bucket.append((cond, oc[0], oc[1]))

    if not mine or not hold:
        print(f"insufficient data (mine={len(mine)} hold={len(hold)})")
        return 1

    def base(pop, up=True):
        k = sum(1 for _, u, d in pop if (u if up else d))
        return k / len(pop)

    print("=" * 88)
    print("TAPE HARNESS - what precedes a PAYABLE move?")
    print(f"  need {a.need:.2f}% within {a.horizon} bars "
          f"(set by chain_feasibility: a 0.30-0.60 delta 0DTE contract needs")
    print(f"  {a.need:.2f}% to pay +10% after the round-trip spread)")
    print(f"  MINE: dates < {cut}  ({len(mine):,} bars)")
    print(f"  HOLD: dates >= {cut}  ({len(hold):,} bars)")
    print("=" * 88)

    bu_m, bd_m = base(mine, True), base(mine, False)
    bu_h, bd_h = base(hold, True), base(hold, False)
    print(f"\n  BASELINE - the hurdle every rule must clear")
    print(f"    mine: UP {bu_m:.1%}   DOWN {bd_m:.1%}")
    print(f"    hold: UP {bu_h:.1%}   DOWN {bd_h:.1%}")
    print("    ⚠️ A rule firing at 49% when the base is 47% has found NOTHING.")

    keys = [k for k in mine[0][0] if not k.startswith("_")]

    for direction, idx, bm, bh in (("UP", 1, bu_m, bu_h), ("DOWN", 2, bd_m, bd_h)):
        found = []
        for k in keys:
            sel = [t for t in mine if t[0][k]]
            if len(sel) < a.min_n:
                continue
            hit = sum(1 for t in sel if t[idx])
            r = hit / len(sel)
            found.append((r - bm, k, r, len(sel)))
        found.sort(reverse=True)

        print(f"\n  {direction} MOVE - top conditions on the MINING set")
        print(f"    {'condition':40}{'n':>8}{'rate':>8}{'lift':>8}   HOLDOUT")
        print("    " + "-" * 78)
        for lift, k, r, n in found[:8]:
            hs = [t for t in hold if t[0][k]]
            if len(hs) < 100:
                ver = "n<100 - UNVERIFIED"
            else:
                hh = sum(1 for t in hs if t[idx])
                hr = hh / len(hs)
                hl = hr - bh
                lo, _ = _wilson(hh, len(hs))
                ver = (f"{hr:.0%} lift {hl:+.0%}  "
                       + ("HOLDS" if hl >= 0.02 and lo > bh - 0.01
                          else "FAILED"))
            print(f"    {k:40}{n:>8,}{r:>7.0%}{lift:>+8.0%}   {ver}")

    print("\n  ⚠️ A RULE THAT FAILS THE HOLDOUT IS REPORTED, NOT DROPPED.")
    print("     Searching ~300,000 bars across 30 conditions produces")
    print("     impressive-looking rules whether or not signal exists. The")
    print("     holdout is the only thing separating the two, and dates - not")
    print("     random bars - are the split, because bars inside one session")
    print("     are heavily correlated and a random split leaks the answer.")
    print("  ⚠️ AND A SURVIVING RULE IS STILL NOT AN EDGE. It says the move")
    print("     happened, not that a contract captured it. Spread, theta and")
    print("     fill quality all sit between this number and a dollar.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
