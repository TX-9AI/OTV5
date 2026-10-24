#!/usr/bin/env python3
"""
tests/fork_respect_study.py  v4.0
Does price RESPECT an hourly contained fork's extended boundaries for the rest
of the session?

v4.0  2026-08-20  Built at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

════════════════════════════════════════════════════════════════════════════
THE CONSTRUCTION, AND WHY IT IS NOT HINDSIGHT FITTING
════════════════════════════════════════════════════════════════════════════
Operator, 2026-08-20: *"The hourly fork on retrofitted price action can
reasonably exclude data that falls out of the beginning of the channel & make an
assumption about price that either does or does not respect the extended
boundaries for the remainder of the session."*

**The exclusion is a rule about which bars QUALIFY, applied to data already in
the past - not a selection made knowing what price did afterwards.** The fork is
built from bars up to a decision point, walking backwards until price leaves the
channel; it is then PROJECTED FORWARD into bars it has never seen, and the
measurement lives entirely in that forward segment.

That is honest, and it is `build_fork_contained` - already the operator's own
construction from 2026-08-11: *"start at the present date and go backwards, and
anything that falls out of the channel is not included in this pitchfork."*

⚠️ EARLY-BAR EXCLUSION IS DOING REAL WORK, NOT COSMETICS. The opening bars are
the auction's residue - wide, unstable, and often no part of the structure that
develops. **A channel forced to contain them describes noise it should have
discarded**, which is the same reasoning that makes the ORB range a distinct
object rather than trend data.

════════════════════════════════════════════════════════════════════════════
WHY HOURLY AND NOT DAILY
════════════════════════════════════════════════════════════════════════════
`tests/tine_order_study.py` on a DAILY channel produced **n=15** - the fit needs
20 prior sessions and the archive holds ~27 dates - and **0% traverse in both
arms**, because crossing a 4-sigma daily span inside one session essentially
does not happen. Daily rails are a guardrail, and the condor is right to use
them that way, but they are the wrong instrument for asking whether price
respects a boundary intraday.

⚠️ AND PERSISTENCE IS AN OUTPUT HERE, NOT A PARAMETER. `build_fork_contained`
removes the RECENCY_BARS=40 assumption - the operator's objection was *"some
forks are gonna be shorter than other ones... they're going to vary."* Measured
on the same tapes: **NVDA 1h span 12 bars, SPX 1h 32, SMCI 1h 139.** The span
this study reports IS the fork's persistence, per symbol, per session.

════════════════════════════════════════════════════════════════════════════
WHAT IS MEASURED
════════════════════════════════════════════════════════════════════════════
For each (session, symbol) with a qualifying hourly contained fork at the
decision bar:
  · **containment**  - share of forward CLOSES inside the rails
  · **respect**      - a rail touched and rejected (wick out, close back in)
  · **break**        - a rail decisively lost (a CLOSE beyond it, held)
  · **span**         - how far back the fork reached, i.e. its persistence

⚠️ A WICK OUT AND A CLOSE OUT ARE DIFFERENT EVENTS and the whole study depends
on the distinction - the same wicks-and-bodies rule the ORB retest and the sweep
reclaim are built on. **A wick through a boundary is a touch; a close beyond it
is a decision.**
"""

import argparse
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
                rows.append([r["timestamp"][11:16], float(r["open"]),
                             float(r["high"]), float(r["low"]), float(r["close"])])
            except Exception:                                  # noqa: BLE001
                continue
    return rows


def to_hourly(rows):
    """1m bars -> hourly OHLC. The fork's own timeframe."""
    out, cur, hr = [], None, None
    for t, o, h, l, c in rows:
        this = t[:2]
        if this != hr:
            if cur:
                out.append(cur)
            cur, hr = [t, o, h, l, c], this
        else:
            cur[2] = max(cur[2], h)
            cur[3] = min(cur[3], l)
            cur[4] = c
    if cur:
        out.append(cur)
    return out


def contained_channel(bars, tol_frac=0.0):
    """Walk BACKWARDS from the last bar while closes stay inside the channel.

    ⚠️ A STAND-IN FOR `build_fork_contained`, AND NAMED AS ONE. The real
    function needs a pandas frame, an ATR and its pivot qualification. This
    reproduces the PROPERTY under test - a channel extended backwards only as
    far as price stayed inside it, so the SPAN is an output rather than a
    parameter. If the answer is interesting, the real fork is the follow-up.
    """
    # ⚠️ OFF BY ONE, AND IT RETURNED None ON EVERY CALL. `range(n-4, -1, -1)`
    # with n=3 is `range(-1,-1,-1)` - EMPTY - so `best` never bound and the
    # study reported "no qualifying hourly forks" against the whole archive.
    # **An absent measurement caused by the tool, wearing the costume of a
    # null.** It printed the honest-looking message and was wrong.
    best = None
    n = len(bars)
    if n < 3:
        return None
    for start in range(n - 3, -1, -1):
        seg = bars[start:]
        cs = [b[4] for b in seg]
        m = len(cs)
        mx = (m - 1) / 2.0
        my = sum(cs) / m
        den = sum((k - mx) ** 2 for k in range(m)) or 1e-9
        slope = sum((k - mx) * (cs[k] - my) for k in range(m)) / den
        resid = [cs[k] - (my + slope * (k - mx)) for k in range(m)]
        sd = (sum(r * r for r in resid) / m) ** 0.5 or 1e-9
        inside = sum(1 for r in resid if abs(r) <= 2.0 * sd) / m
        if inside < 0.95:
            break                    # price left the channel - stop extending
        best = {"start": start, "slope": slope, "sd": sd, "my": my,
                "mx": mx, "m": m, "span": m}
    return best


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ohlc", default=OHLC)
    ap.add_argument("--decide-hour", type=int, default=2,
                    help="hourly bars into the session before projecting")
    ap.add_argument("--rail-sigma", type=float, default=2.0)
    a = ap.parse_args(argv[1:])

    obs = []
    hourly_by_sym = {}          # carries the fork back across sessions
    days = sorted(os.path.basename(d) for d in
                  glob.glob(os.path.join(os.path.expanduser(a.ohlc), "*"))
                  if os.path.isdir(d))
    days = [d for d in days if d not in POLLUTED]
    for day in days:
        for p in sorted(glob.glob(os.path.join(
                os.path.expanduser(a.ohlc), day, "*_ohlc_*.csv"))):
            sym = os.path.basename(p).split("_ohlc_")[0].upper()
            try:
                rows = [r for r in load(p) if "09:30" <= r[0] <= "16:00"]
            except Exception:                                  # noqa: BLE001
                continue
            if len(rows) < 200:
                continue
            # ⚠️ AN HOURLY FORK SPANS MULTIPLE SESSIONS. v4.0's first version
            # fitted inside ONE session - 3 hourly bars, which is not a channel.
            # `pitchfork.py`'s own header records measured hourly spans of
            # **NVDA 12 bars, SPX 32, SMCI 139**: all of them reach back past
            # the open. A fork that cannot see yesterday is not the instrument
            # the condor anchors to.
            hourly = to_hourly(rows)
            if len(hourly) < a.decide_hour + 2:
                continue
            prior = hourly_by_sym.get(sym, [])
            fit = prior + hourly[:a.decide_hour + 1]
            hourly_by_sym[sym] = (prior + hourly)[-120:]
            if len(fit) < 6:
                continue
            ch = contained_channel(fit)
            if not ch:
                continue

            # project forward over the remaining 1m bars
            cut_hr = fit[-1][0][:2]
            fwd = [r for r in rows if r[0][:2] > cut_hr]
            if len(fwd) < 60:
                continue

            # rails at the projection point, held flat across the forward
            # segment (the hourly slope over 1m bars is the extrapolation
            # error the daily study was killed by - so it is NOT extended)
            mid = ch["my"] + ch["slope"] * (ch["m"] - 1 - ch["mx"])
            up = mid + a.rail_sigma * ch["sd"]
            lo = mid - a.rail_sigma * ch["sd"]

            closes_in = sum(1 for r in fwd if lo <= r[4] <= up) / len(fwd)
            touched_up = any(r[2] >= up for r in fwd)
            touched_lo = any(r[3] <= lo for r in fwd)
            broke = any(r[4] > up or r[4] < lo for r in fwd)
            # respect = a rail was TOUCHED (wick) but never CLOSED beyond
            respected = (touched_up or touched_lo) and not broke

            obs.append({"day": day, "sym": sym, "span": ch["span"],
                        "closes_in": closes_in, "touched": touched_up or touched_lo,
                        "respected": respected, "broke": broke,
                        "width_pct": (up - lo) / mid * 100.0 if mid else 0.0})

    if not obs:
        print("no qualifying hourly forks. ABSENT MEASUREMENT, not a null.")
        return 1

    n = len(obs)
    print("=" * 82)
    print("FORK RESPECT STUDY - does price respect an hourly contained fork?")
    print(f"  {n:,} (session, symbol) observations, "
          f"{len({o['day'] for o in obs})} dates, "
          f"{len({o['sym'] for o in obs})} symbols")
    print(f"  fitted on the first {a.decide_hour + 1} hourly bars, projected "
          f"forward only")
    print("=" * 82)

    ci = [o["closes_in"] for o in obs]
    print(f"\n  1. CONTAINMENT of forward closes")
    print(f"     p25 {_pct(ci,25):.0%}   p50 {_pct(ci,50):.0%}   "
          f"p75 {_pct(ci,75):.0%}   p90 {_pct(ci,90):.0%}")
    print("     ⚠️ A CHANNEL THAT CONTAINS EVERYTHING IS TOO WIDE TO BE A")
    print("        BOUNDARY. 100% containment is not a good result - it means")
    print("        the rails were never in play.")

    t = sum(1 for o in obs if o["touched"])
    r = sum(1 for o in obs if o["respected"])
    b = sum(1 for o in obs if o["broke"])
    lo_, hi_ = _wilson(r, max(t, 1))
    print(f"\n  2. WHAT HAPPENED AT THE RAIL")
    print(f"     rail TOUCHED at all      : {t}/{n} = {t/n:.0%}")
    print(f"     of those, RESPECTED      : {r}/{t} = {r/max(t,1):.0%}"
          f"   95% CI [{lo_:.0%}, {hi_:.0%}]")
    print(f"     CLOSED beyond (broke)    : {b}/{n} = {b/n:.0%}")
    print("     ⚠️ RESPECTED means a wick through and a close back inside -")
    print("        **a wick is a touch, a close is a decision**, the same rule")
    print("        the ORB retest and the sweep reclaim are built on.")

    sp = [o["span"] for o in obs]
    wd = [o["width_pct"] for o in obs]
    print(f"\n  3. PERSISTENCE AND WIDTH - both OUTPUTS, not parameters")
    print(f"     span (hourly bars)  p25 {_pct(sp,25):.0f}   p50 {_pct(sp,50):.0f}"
          f"   p90 {_pct(sp,90):.0f}")
    print(f"     channel width %     p25 {_pct(wd,25):.2f}   p50 {_pct(wd,50):.2f}"
          f"   p90 {_pct(wd,90):.2f}")

    print(f"\n  4. DOES A LONGER-LIVED FORK GET MORE RESPECT?")
    print(f"    {'span':14}{'n':>7}{'touched':>10}{'respected':>12}{'broke':>8}")
    print("    " + "-" * 51)
    for lo2, hi2, lbl in ((0, 4, "short (<4)"), (4, 8, "4-8"),
                          (8, 16, "8-16"), (16, 999, "long (16+)")):
        sel = [o for o in obs if lo2 <= o["span"] < hi2]
        if len(sel) < 10:
            continue
        tt = sum(1 for o in sel if o["touched"])
        rr = sum(1 for o in sel if o["respected"])
        bb = sum(1 for o in sel if o["broke"])
        print(f"    {lbl:14}{len(sel):>7}{tt/len(sel):>9.0%}"
              f"{rr/max(tt,1):>11.0%}{bb/len(sel):>8.0%}")

    print("\n  ⚠️ RAILS ARE HELD FLAT ACROSS THE FORWARD SEGMENT, DELIBERATELY.")
    print("     Extending an hourly slope across ~4 hours of 1m bars is the")
    print("     exact extrapolation that made the first tine study fabricate an")
    print("     81% result with breached=100% on BOTH arms. A flat projection")
    print("     understates a real trend and cannot manufacture a finding.")
    print("  ⚠️ AND THIS IS A STAND-IN FOR `build_fork_contained`, not the fork")
    print("     itself. It reproduces the property under test - span as an")
    print("     OUTPUT - so an interesting answer earns the real fork next.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
