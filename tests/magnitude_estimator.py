#!/usr/bin/env python3
"""
tests/magnitude_estimator.py  v4.0
Does ADX (or ATR) predict HOW FAR price moves? The strike-selection question.

v4.0  2026-08-19  Built at the OTV4 split. ROADMAP Phase 1.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

THE QUESTION, AND WHY IT IS A DIFFERENT QUESTION.
Every previous test asked whether something predicts WHICH WAY price goes, and
ADX came back ambient every time - it held on 91% of good ContinuationStrategy
entries and 88% of bad ones. **That is not a failure of ADX; it is a category
error.** ADX is a magnitude measure. Asking it for direction is asking a
speedometer which way the car is pointed.

Operator, 2026-08-19: *"What about basing the strike selection on ADX too. Ask
'can the underlying even REACH the target?'"* That inverts the design. Today the
strike is a fixed delta and the required move FOLLOWS from it - 0.20 delta needs
0.72% whether or not the tape can produce 0.72%. The proposal is to read what
the tape can deliver and then pick the strike that move can reach.

**So the measure that was useless for "which way" may be the right one for
"how far."** This tests exactly that, and tests ATR beside it rather than
assuming ADX wins - ATR is the more natural magnitude estimator and if it is
better, the rule should say ATR.

WHAT "GOOD" LOOKS LIKE HERE.
Not a correlation coefficient. The usable output is a MAPPING: at this ADX, the
excursion over the next N bars was typically THIS BIG, so the deepest strike
whose required move sits inside it is THAT ONE. A monotone relationship with
separated bands is worth more than a high r with overlapping ones.

⚠️ AND THE BAR IS SET BY THE CHAIN. `tests/chain_feasibility.py` on 110,162
contract observations: 0.05-0.20 delta needs **0.72%**, 0.20-0.35 needs
**0.75%**, 0.35-0.50 needs **0.90%**, 0.50-0.70 needs **1.11%**, 0.70-0.95 needs
**1.95%** - all including the round-trip spread. Those are the thresholds each
ADX band is scored against, so the output answers the strike question directly
rather than requiring a second step.
"""

import argparse
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OHLC = os.path.expanduser("~/day_trader_pro/ohlc")
POLLUTED = {"2026-08-14"}

# required move by delta band, from chain_feasibility (p50, spread included)
STRIKE_BAR = [
    ("0.05-0.20", 0.72),
    ("0.20-0.35", 0.75),
    ("0.35-0.50", 0.90),
    ("0.50-0.70", 1.11),
    ("0.70-0.95", 1.95),
]


def _pct(v, p):
    if not v:
        return float("nan")
    s = sorted(v)
    return s[min(len(s) - 1, int(p / 100.0 * len(s)))]


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


def adx_atr(rows, i, period=14):
    """Wilder ADX and ATR at the close of bar i. Bars 0..i only - no lookahead."""
    if i < period * 2:
        return None, None
    hs = [r[2] for r in rows[:i + 1]]
    ls = [r[3] for r in rows[:i + 1]]
    cs = [r[4] for r in rows[:i + 1]]
    trs, pdm, ndm = [], [], []
    for k in range(1, len(hs)):
        up = hs[k] - hs[k - 1]
        dn = ls[k - 1] - ls[k]
        pdm.append(up if (up > dn and up > 0) else 0.0)
        ndm.append(dn if (dn > up and dn > 0) else 0.0)
        trs.append(max(hs[k] - ls[k], abs(hs[k] - cs[k - 1]),
                       abs(ls[k] - cs[k - 1])))
    # Wilder smoothing over the last `period`
    atr = sum(trs[-period:]) / period
    if atr <= 0:
        return None, None
    pdi = 100.0 * (sum(pdm[-period:]) / period) / atr
    ndi = 100.0 * (sum(ndm[-period:]) / period) / atr
    dx = 100.0 * abs(pdi - ndi) / max(pdi + ndi, 1e-9)
    # a single DX is noisy; average the last `period` DX values
    dxs = []
    for j in range(max(period, len(trs) - period), len(trs)):
        a = sum(trs[max(0, j - period):j]) / period or 1e-9
        p_ = 100.0 * (sum(pdm[max(0, j - period):j]) / period) / a
        n_ = 100.0 * (sum(ndm[max(0, j - period):j]) / period) / a
        dxs.append(100.0 * abs(p_ - n_) / max(p_ + n_, 1e-9))
    adx = sum(dxs) / len(dxs) if dxs else dx
    return adx, atr / cs[-1] * 100.0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ohlc", default=OHLC)
    ap.add_argument("--horizon", type=int, default=90)
    ap.add_argument("--symbol", default="")
    ap.add_argument("--before", default="11:30",
                    help="only sample bars before this ET time")
    a = ap.parse_args(argv[1:])

    days = sorted(os.path.basename(d) for d in
                  glob.glob(os.path.join(os.path.expanduser(a.ohlc), "*"))
                  if os.path.isdir(d))
    days = [d for d in days if d not in POLLUTED]
    obs = []
    for day in days:
        for p in sorted(glob.glob(os.path.join(
                os.path.expanduser(a.ohlc), day, "*_ohlc_*.csv"))):
            sym = os.path.basename(p).split("_ohlc_")[0].upper()
            if a.symbol and sym != a.symbol.upper():
                continue
            try:
                rows = [r for r in load(p) if "09:30" <= r[0] <= "16:00"]
            except Exception:                                  # noqa: BLE001
                continue
            if len(rows) < 150:
                continue
            for i in range(40, len(rows) - 20):
                if rows[i][0] >= a.before:
                    continue
                adx, atrp = adx_atr(rows, i)
                if adx is None:
                    continue
                seg = rows[i + 1:i + 1 + a.horizon]
                if len(seg) < a.horizon // 2:
                    continue
                c = rows[i][4]
                up = (max(r[2] for r in seg) - c) / c * 100.0
                dn = (c - min(r[3] for r in seg)) / c * 100.0
                obs.append((adx, atrp, max(up, dn), up, dn))

    if not obs:
        print("no observations. ABSENT MEASUREMENT, not a null.")
        return 1

    print("=" * 88)
    print("MAGNITUDE ESTIMATOR - can the underlying REACH the target?")
    print(f"  {len(obs):,} bars, {len(days)} dates, horizon {a.horizon} bars, "
          f"sampled before {a.before}")
    print("=" * 88)

    for label, idx, bands in (
            ("ADX", 0, [(0, 15), (15, 20), (20, 25), (25, 30), (30, 40), (40, 100)]),
            ("ATR %", 1, [(0, .03), (.03, .05), (.05, .08), (.08, .12), (.12, 9)])):
        print(f"\n  EXCURSION BY {label} - does it predict HOW FAR?")
        print(f"    {'band':12}{'n':>9}{'p25':>8}{'p50':>8}{'p75':>8}{'p90':>8}")
        print("    " + "-" * 54)
        prev = None
        mono = True
        for lo, hi in bands:
            sel = [o[2] for o in obs if lo <= o[idx] < hi]
            if len(sel) < 200:
                continue
            m = _pct(sel, 50)
            print(f"    {f'{lo}-{hi}':12}{len(sel):>9,}{_pct(sel,25):>7.2f}%"
                  f"{m:>7.2f}%{_pct(sel,75):>7.2f}%{_pct(sel,90):>7.2f}%")
            if prev is not None and m < prev - 0.01:
                mono = False
            prev = m
        print(f"    -> monotone: {'YES' if mono else 'NO'}"
              + ("" if mono else "  (a non-monotone estimator is not usable "
                                 "for strike selection)"))

    # ── ATR is the estimator; ADX measured FLAT and cannot drive this ───────
    # ⚠️ MEASURED 2026-08-19 on 52,949 bars: ADX bands 0-15 through 40-100 all
    # produced the SAME median excursion - 0.69% to 0.74%. **ADX 45 reaches no
    # further than ADX 12.** The reachability table was flat across every row,
    # which is the same non-result ADX gave for DIRECTION, now for MAGNITUDE.
    # ATR over the same bars: 0.19% -> 0.28% -> 0.43% -> 0.60% -> 1.07%,
    # monotone, a 5.6x spread. **The rule reads ATR.**
    print("\n  STRIKE REACHABILITY BY ATR BAND  <- THE USABLE MAP")
    print("     For each ATR band: what fraction of bars produced an excursion")
    print("     big enough to pay +10% on each delta band, spread included.")
    hdr2 = "".join(f"{lbl:>12}" for lbl, _ in STRIKE_BAR)
    print(f"    {'ATR %':10}{'n':>8}{hdr2}")
    print("    " + "-" * (18 + 12 * len(STRIKE_BAR)))
    for lo, hi in [(0, .03), (.03, .05), (.05, .08), (.08, .12), (.12, .20),
                   (.20, 9)]:
        sel = [o for o in obs if lo <= o[1] < hi]
        if len(sel) < 200:
            continue
        cells = ""
        for _lbl, need in STRIKE_BAR:
            hit = sum(1 for o in sel if o[2] >= need) / len(sel)
            cells += f"{hit:>11.0%} "
        print(f"    {f'{lo}-{hi}':10}{len(sel):>8,}{cells}")
    print("     -> pick the DEEPEST band the tape reaches often enough to be")
    print("        worth buying. A band reached 20% of the time is a lottery")
    print("        ticket, not a strike.")

    print("\n  STRIKE REACHABILITY BY ADX BAND  (kept to show it is FLAT)")
    print("     For each ADX band: what fraction of bars produced an excursion")
    print("     big enough to pay +10% on each delta band, spread included.")
    hdr = "".join(f"{lbl:>12}" for lbl, _ in STRIKE_BAR)
    print(f"    {'ADX':10}{'n':>8}{hdr}")
    print("    " + "-" * (18 + 12 * len(STRIKE_BAR)))
    for lo, hi in [(0, 15), (15, 20), (20, 25), (25, 30), (30, 40), (40, 100)]:
        sel = [o for o in obs if lo <= o[0] < hi]
        if len(sel) < 200:
            continue
        cells = ""
        for _lbl, need in STRIKE_BAR:
            hit = sum(1 for o in sel if o[2] >= need) / len(sel)
            cells += f"{hit:>11.0%} "
        print(f"    {f'{lo}-{hi}':10}{len(sel):>8,}{cells}")

    print("\n  ⚠️ READ THE COLUMNS, NOT THE ROWS. The usable answer is: at THIS")
    print("     ADX, which delta band does the tape reach often enough to be")
    print("     worth buying? A band the tape reaches 20% of the time is not a")
    print("     strike, it is a lottery ticket.")
    print("  ⚠️ AND THIS IS EXCURSION IN EITHER DIRECTION. It says the move was")
    print("     available, not that it went the traded way. Direction is a")
    print("     SEPARATE and still-unanswered question - four independent")
    print("     searches have now failed to find it.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
