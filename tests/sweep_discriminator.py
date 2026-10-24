#!/usr/bin/env python3
"""
tests/sweep_discriminator.py  v4.0
Which swept pools HELD as boundaries, and which failed? A good entry from a bad
one.

v4.0  2026-08-20  Built at the OTV4 split. ROADMAP Phase 1.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

WHY THE TAPE AND NOT THE TRADE BOOK.
v3's sweep book is **34 trades** - far too thin to fit a threshold against, and
every one of them was selected by a scorer that could not fire: SWEEP was
hard-vetoed on 95.9% of 269,027 named-pool rows, and of the 4.1% that survived
the median score was ~0.031 against its own 0.05 dispatch floor. **Fitting to 34
trades chosen by a broken gate would encode the gate's bias, not the setup's.**

The tape has every named-pool sweep that ever happened, chosen by nothing.

WHAT "GOOD" MEANS HERE, AND WHY IT IS NOT DIRECTION.
A credit spread sold against a swept pool does not need price to travel. It
needs **the boundary to HOLD** - price must stay on the profitable side through
the session. So the outcome is not "did price move the right way", it is:

    **did price close back through the pool before the bell?**

That is the thesis, stated as a measurement. A pool that held is a good entry; a
pool that gave way is a bad one, regardless of what happened in between.

⚠️ AND `MAX ADVERSE EXCURSION` IS REPORTED BESIDE IT, because a boundary that
holds by the close after being breached by 0.8% intraday would have taken the
15% stop long before. **Held-at-the-bell and never-threatened are different
facts and a spread only survives the second one.**

⚠️ ONE OUTCOME PER SWEEP, NOT PER TICK. A single sweep observed on 40
consecutive ticks is ONE event. Counting ticks would inflate n by an order of
magnitude and make every confidence interval a fiction - the same error as
counting twenty trades on one trending day as twenty observations.
"""

import argparse
import bisect
import collections
import csv
import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OHLC = os.path.expanduser("~/day_trader_pro/ohlc")
POLLUTED = {"2026-08-14"}

# Pool grades from analysis/level_grade.py - STATED PRIORS, not fitted.
POOL_GRADE = {"PDH": 1.0, "PDL": 1.0, "ONH": 0.85, "ONL": 0.85,
              "ASIA_H": 0.70, "ASIA_L": 0.70, "LONDON_H": 0.70, "LONDON_L": 0.70,
              "NYH": 0.55, "NYL": 0.55, "EQH": 0.40, "EQL": 0.40}


def _wilson(k, n):
    if n == 0:
        return (0.0, 1.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


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


def prior_levels(prev_rows):
    """PDH/PDL from yesterday's tape. The two highest-graded pools."""
    if not prev_rows:
        return {}
    rth = [r for r in prev_rows if "09:30" <= r[0] <= "16:00"]
    if len(rth) < 60:
        return {}
    return {"PDH": max(r[2] for r in rth), "PDL": min(r[3] for r in rth)}


def find_sweeps(rows, levels, reject_min_pct):
    """Every named-pool sweep-and-reclaim in this session.

    A sweep is: price trades THROUGH the level, then a bar CLOSES back inside.
    ⚠️ THE CLOSE IS THE POINT - a wick through a level is a touch, not a
    decision. That distinction is v3's own liquidity doctrine and it is what
    SWP.11 restored after the veto window and the confirmation window were found
    to be the same window.
    """
    out = []
    for name, lvl in (levels or {}).items():
        if not lvl or lvl <= 0:
            continue
        ceiling = name.endswith("H")
        i = 0
        while i < len(rows) - 5:
            _, o, h, l, c = rows[i]
            pierced = (h > lvl) if ceiling else (l < lvl)
            if not pierced:
                i += 1
                continue
            # look for the reclaim: a CLOSE back inside within 5 bars
            rc = None
            for k in range(i, min(i + 6, len(rows))):
                cc = rows[k][4]
                if (cc < lvl) if ceiling else (cc > lvl):
                    rc = k
                    break
            if rc is None:
                i += 1
                continue
            ext = (max(rows[j][2] for j in range(i, rc + 1)) - lvl) if ceiling \
                else (lvl - min(rows[j][3] for j in range(i, rc + 1)))
            rej = ext / lvl
            if rej >= reject_min_pct:
                out.append({"name": name, "level": lvl, "ceiling": ceiling,
                            "sweep_i": i, "reclaim_i": rc,
                            "rejection_pct": rej * 100.0,
                            "hhmm": rows[rc][0]})
            i = rc + 1          # one event, not one per tick
    return out


def outcome(rows, sw):
    """Did the boundary HOLD to the bell, and how hard was it tested?"""
    rc = sw["reclaim_i"]
    after = rows[rc + 1:]
    if len(after) < 10:
        return None
    lvl, ceiling = sw["level"], sw["ceiling"]
    settle = after[-1][4]
    held = (settle < lvl) if ceiling else (settle > lvl)
    # worst adverse excursion BEYOND the boundary, as % of the level
    adverse = (max(r[2] for r in after) - lvl) if ceiling \
        else (lvl - min(r[3] for r in after))
    return held, max(0.0, adverse) / lvl * 100.0, len(after)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ohlc", default=OHLC)
    ap.add_argument("--symbol", default="")
    ap.add_argument("--reject-min", type=float, default=0.0005,
                    help="minimum pierce depth as a fraction of the level")
    ap.add_argument("--stop-pct", type=float, default=0.35,
                    help="adverse excursion beyond the level that would plausibly "
                         "have taken the 15%% spread stop")
    a = ap.parse_args(argv[1:])

    days = sorted(os.path.basename(d) for d in
                  glob.glob(os.path.join(os.path.expanduser(a.ohlc), "*"))
                  if os.path.isdir(d))
    days = [d for d in days if d not in POLLUTED]
    prev_by_sym = {}
    events = []

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
            lv = prior_levels(prev_by_sym.get(sym))
            prev_by_sym[sym] = rows
            if not lv:
                continue
            for sw in find_sweeps(rows, lv, a.reject_min):
                oc = outcome(rows, sw)
                if not oc:
                    continue
                held, adverse, bars_left = oc
                sw.update({"held": held, "adverse_pct": adverse,
                           "bars_left": bars_left, "sym": sym, "day": day})
                events.append(sw)

    if not events:
        print("no sweep events found. ABSENT MEASUREMENT, not a null.")
        return 1

    n = len(events)
    k = sum(1 for e in events if e["held"])
    lo, hi = _wilson(k, n)
    print("=" * 86)
    print("SWEEP DISCRIMINATOR - which swept pools HELD as boundaries?")
    print(f"  {n:,} sweep-and-reclaim events, "
          f"{len({e['day'] for e in events})} dates, "
          f"{len({e['sym'] for e in events})} symbols")
    print("  ONE OUTCOME PER SWEEP, not per tick.")
    print("=" * 86)
    print(f"\n  BASE RATE - the boundary held to the bell: {k}/{n} = {k/n:.0%}"
          f"   95% CI [{lo:.0%}, {hi:.0%}]")
    print("  ⚠️ THIS IS THE HURDLE. Any filter below must beat it to be worth a")
    print("     gate; one that fires at 68% when the base is 67% has found")
    print("     nothing.")

    survive = sum(1 for e in events
                  if e["held"] and e["adverse_pct"] < a.stop_pct)
    print(f"\n  AND HELD *WITHOUT BEING STOPPED* (adverse < {a.stop_pct:.2f}% "
          f"of the level): {survive}/{n} = {survive/n:.0%}")
    print("     ⚠️ THE NUMBER THAT MATTERS. A boundary that holds by the close")
    print("        after being breached intraday would have taken the 15% stop")
    print("        long before. Held-at-the-bell and never-threatened are")
    print("        different facts, and a spread only survives the second.")

    def table(title, keyfn, bands):
        print(f"\n  {title}")
        print(f"    {'band':22}{'n':>7}{'held':>8}{'survived':>10}"
              f"{'p50 adverse':>13}  verdict")
        print("    " + "-" * 72)
        for lbl, test in bands:
            sel = [e for e in events if test(keyfn(e))]
            if len(sel) < 25:
                continue
            kk = sum(1 for e in sel if e["held"])
            ss = sum(1 for e in sel
                     if e["held"] and e["adverse_pct"] < a.stop_pct)
            adv = [e["adverse_pct"] for e in sel]
            l2, h2 = _wilson(ss, len(sel))
            base_s = survive / n
            v = ("BEATS base" if l2 > base_s else
                 "below base" if h2 < base_s else "same as base")
            print(f"    {lbl:22}{len(sel):>7}{kk/len(sel):>7.0%}"
                  f"{ss/len(sel):>9.0%}{_pct(adv,50):>12.2f}%  {v}")

    table("BY POOL TYPE (grade is a STATED PRIOR, not fitted)",
          lambda e: e["name"],
          [("PDH (ceiling)", lambda x: x == "PDH"),
           ("PDL (floor)", lambda x: x == "PDL")])

    table("BY REJECTION DEPTH - how far past the level price got",
          lambda e: e["rejection_pct"],
          [("shallow < 0.10%", lambda x: x < 0.10),
           ("0.10 - 0.25%", lambda x: 0.10 <= x < 0.25),
           ("0.25 - 0.50%", lambda x: 0.25 <= x < 0.50),
           ("deep > 0.50%", lambda x: x >= 0.50)])

    table("BY TIME OF THE RECLAIM",
          lambda e: e["hhmm"],
          [("before 10:30", lambda x: x < "10:30"),
           ("10:30 - 13:00", lambda x: "10:30" <= x < "13:00"),
           ("13:00 - 14:30", lambda x: "13:00" <= x < "14:30"),
           ("after 14:30", lambda x: x >= "14:30")])

    table("BY SESSION TIME REMAINING (bars after the reclaim)",
          lambda e: e["bars_left"],
          [("< 60 bars", lambda x: x < 60),
           ("60 - 150", lambda x: 60 <= x < 150),
           ("150 - 250", lambda x: 150 <= x < 250),
           ("> 250 bars", lambda x: x >= 250)])

    print("\n  ⚠️ A BAND THAT MATCHES THE BASE RATE IS NOT A DISCRIMINATOR, and")
    print("     gating on it would only reduce the number of trades. The whole")
    print("     point of this table is to find where the outcome DIFFERS.")
    print("  ⚠️ AND THIS IS PDH/PDL ONLY - the two highest-graded pools, and the")
    print("     only ones derivable from banked OHLC. Overnight and session")
    print("     levels need the liquidity mapper's own output, which was never")
    print("     archived. Their absence is a GAP IN THE MEASUREMENT, not")
    print("     evidence that they behave the same.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
