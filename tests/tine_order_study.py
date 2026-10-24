#!/usr/bin/env python3
"""
tests/tine_order_study.py  v4.0
Does the fork's slope predict which rail price taps first? And does being WRONG
matter?

v4.0  2026-08-20  Built at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

════════════════════════════════════════════════════════════════════════════
THE QUESTION, AND WHY IT IS TWO QUESTIONS
════════════════════════════════════════════════════════════════════════════
v3's PF.5 spec derived the condor's leg order from the fork's apparent slope:
an UP-sloping fork means price travels lower rail -> upper rail over the
session, so it taps the LOWER rail first and the PUT side fills first.

**That ordering is no longer used.** `v-indep-legs` (2026-07-28) made both sides
independent - each fires on its own price trigger, checked every tick - so
whichever tine price actually strikes first fills first. `_leg_order_from_slope`
survives as a helper **with no caller**, and docs/TRADES.md still described the
superseded design.

Operator, 2026-08-20: *"Is hitting the 'wrong' tine first kind of scary in that
it already is deviating from our belief in the structure?"*

**That is a better question than the ordering one**, and it splits in two:
  1. **IS THE SLOPE PREDICTIVE AT ALL?** If first-tap is an even split, order is
     noise, the helper gets deleted, and the doc gets corrected. Done.
  2. **DOES A WRONG-TINE TAP PREDICT TROUBLE?** This is the one that matters
     even if (1) is a coin. The slope is not a coin flip in principle - **it is
     a claim about where price sits in its own channel.** An up-sloping fork
     with price near the lower rail says the traverse runs upward. If price
     taps the UPPER rail first, either the fork was drawn on the wrong pivots or
     price is moving against the channel's geometry - and **the condor's first
     position would be opened by an event that contradicts the model that
     placed it.**

⚠️ **AN EVEN SPLIT ON (1) WITH A SKEW ON (2) IS THE INTERESTING RESULT**, not a
contradiction: order would predict nothing while wrong-order predicted trouble.

⚠️ AND THE OPERATOR'S OWN ACCEPTED RISK MAKES (2) SHARPER: *"If it gets
breached, then our fork may also become invalid & I can live with that."* A
wrong-tine tap is not a breach - but it is the first evidence pointing there,
and a condor is a structure where being told early beats being right late.

════════════════════════════════════════════════════════════════════════════
METHOD
════════════════════════════════════════════════════════════════════════════
Per (session, symbol) with a valid DAILY fork:
  · which rail did price reach FIRST, and did the slope call it
  · did price then TRAVERSE to the other rail  (the condor completing)
  · did the fork SURVIVE the session, or was a rail decisively breached

⚠️ ONE OBSERVATION PER SESSION, NOT PER TICK. A fork observed on 300 ticks is
one event. Counting ticks would inflate every interval into fiction.
⚠️ AND THE FORK IS BUILT FROM BARS UP TO THE DECISION POINT ONLY. A fork fitted
on the whole session would be drawn using the very moves it is meant to predict.
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


def load(path):
    rows = []
    with open(path) as fh:
        for r in csv.DictReader(fh):
            try:
                rows.append((r["timestamp"][11:16], float(r["open"]),
                             float(r["high"]), float(r["low"]), float(r["close"])))
            except Exception:                                  # noqa: BLE001
                continue
    return rows


def daily_channel(daily, lookback=20):
    """A DAILY regression channel: slope per session, rails at N-sigma.

    ⚠️ THIS REPLACES AN INTRADAY FIT THAT WAS AN ARTIFACT GENERATOR. v4.0's
    first version fitted a channel on the first 60 one-minute bars and then
    projected its slope across the remaining ~330. **A one-hour slope
    extrapolated over five and a half hours runs the channel off into space**,
    so price ends up outside whichever rail the slope is moving away from and
    the "prediction" is guaranteed by the arithmetic.
    The tell was in the output and it should have stopped the read cold:
    **breached = 100% on BOTH arms.** A measurement with a column reading 100%
    on both sides of its own split is measuring its own construction.
    It reported 81% predictive [78%, 84%] and a 73-point traverse gap. **Both
    numbers were fabricated by the extrapolation and neither should be quoted.**

    A DAILY fork is what the condor actually anchors to (`CONDOR_PITCHFORK_ANCHOR`,
    daily only - operator: *"It's a guardrail, not the road."*). Fitted over
    ~20 SESSIONS and projected across ONE, the slope moves the rails by a
    fraction of their width - which is the geometry the spec describes.
    """
    if len(daily) < lookback + 1:
        return None
    seg = daily[-(lookback + 1):-1]          # prior sessions only, never today
    cs = [d["close"] for d in seg]
    n = len(cs)
    mx = (n - 1) / 2.0
    my = sum(cs) / n
    den = sum((k - mx) ** 2 for k in range(n)) or 1e-9
    slope = sum((k - mx) * (cs[k] - my) for k in range(n)) / den
    resid = [cs[k] - (my + slope * (k - mx)) for k in range(n)]
    sd = (sum(r * r for r in resid) / n) ** 0.5 or 1e-9
    # value at "today" = one session past the end of the fit window
    mid_today = my + slope * (n - mx)
    return {"slope": slope, "sd": sd, "mid": mid_today, "n": n}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ohlc", default=OHLC)
    ap.add_argument("--lookback", type=int, default=20,
                    help="prior SESSIONS the daily channel is fitted over")
    ap.add_argument("--rail-sigma", type=float, default=2.0)
    ap.add_argument("--flat-eps", type=float, default=0.0,
                    help="|slope| below this counts as FLAT and is excluded")
    a = ap.parse_args(argv[1:])

    obs = []
    days = sorted(os.path.basename(d) for d in
                  glob.glob(os.path.join(os.path.expanduser(a.ohlc), "*"))
                  if os.path.isdir(d))
    days = [d for d in days if d not in POLLUTED]

    # ── build DAILY bars per symbol, in date order ─────────────────────────
    by_sym = {}
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
            by_sym.setdefault(sym, []).append({
                "day": day, "rows": rows,
                "high": max(r[2] for r in rows),
                "low": min(r[3] for r in rows),
                "close": rows[-1][4],
            })

    for sym, sessions in by_sym.items():
        for i in range(len(sessions)):
            ch = daily_channel(sessions[:i + 1], a.lookback)
            if not ch or abs(ch["slope"]) <= a.flat_eps:
                continue
            rows = sessions[i]["rows"]
            up_rail = ch["mid"] + a.rail_sigma * ch["sd"]
            lo_rail = ch["mid"] - a.rail_sigma * ch["sd"]
            # ⚠️ price must START INSIDE the rails, or "first tap" is decided
            # before the session opens.
            if not (lo_rail < rows[0][4] < up_rail):
                continue

            up_slope = ch["slope"] > 0
            predicted = "lower" if up_slope else "upper"
            first, traversed, breached = None, False, False
            for r in rows:
                _, _, h, l, c = r
                if first is None:
                    if h >= up_rail:
                        first = "upper"
                    elif l <= lo_rail:
                        first = "lower"
                else:
                    if (first == "upper" and l <= lo_rail) or \
                       (first == "lower" and h >= up_rail):
                        traversed = True
                    if c >= up_rail + 0.5 * ch["sd"] or \
                       c <= lo_rail - 0.5 * ch["sd"]:
                        breached = True
            if first is None:
                continue
            obs.append({"day": sessions[i]["day"], "sym": sym,
                        "predicted": predicted, "first": first,
                        "correct": first == predicted,
                        "traversed": traversed, "breached": breached,
                        "up_slope": up_slope})

    if not obs:
        print("no sessions with a rail tap. ABSENT MEASUREMENT, not a null.")
        return 1

    n = len(obs)
    k = sum(1 for o in obs if o["correct"])
    lo, hi = _wilson(k, n)
    print("=" * 80)
    print("TINE ORDER STUDY - does the slope predict which rail is tapped first?")
    print(f"  {n:,} (session, symbol) observations, "
          f"{len({o['day'] for o in obs})} dates, "
          f"{len({o['sym'] for o in obs})} symbols")
    print(f"  DAILY channel over {a.lookback} prior sessions - today is never "
          f"in its own fit")
    print("=" * 80)

    print(f"\n  1. IS THE SLOPE PREDICTIVE AT ALL?")
    print(f"     slope called the first rail: {k}/{n} = {k/n:.0%}   "
          f"95% CI [{lo:.0%}, {hi:.0%}]")
    if hi < 0.50:
        print("     ⚠️ INVERSE - price taps the rail it is moving AWAY from first.")
    elif lo > 0.50:
        print("     ✅ PREDICTIVE - the interval excludes a coin.")
    else:
        print("     ❌ A COIN - the interval spans 50%. **Order is noise**: delete")
        print("        `_leg_order_from_slope` and correct docs/TRADES.md §5,")
        print("        which still describes the superseded PF.5 ordering.")

    print(f"\n  2. DOES A WRONG-TINE TAP PREDICT TROUBLE?")
    print("     ⚠️ THE QUESTION THAT MATTERS EVEN IF (1) IS A COIN.")
    print(f"    {'first tap':16}{'n':>7}{'traversed':>12}{'breached':>11}")
    print("    " + "-" * 46)
    for lbl, sel in (("as predicted", [o for o in obs if o["correct"]]),
                     ("WRONG tine", [o for o in obs if not o["correct"]])):
        if not sel:
            continue
        t = sum(1 for o in sel if o["traversed"]) / len(sel)
        b = sum(1 for o in sel if o["breached"]) / len(sel)
        print(f"    {lbl:16}{len(sel):>7}{t:>11.0%}{b:>11.0%}")

    ct = [o for o in obs if o["correct"]]
    wt = [o for o in obs if not o["correct"]]
    if len(ct) >= 30 and len(wt) >= 30:
        tc = sum(1 for o in ct if o["traversed"]) / len(ct)
        tw = sum(1 for o in wt if o["traversed"]) / len(wt)
        bc = sum(1 for o in ct if o["breached"]) / len(ct)
        bw = sum(1 for o in wt if o["breached"]) / len(wt)
        print(f"\n     traverse gap: {tc - tw:+.0%}   breach gap: {bw - bc:+.0%}")
        print("     **A traverse is the condor COMPLETING; a breach is the")
        print("     thesis dying.** A wrong-tine tap that traverses less AND")
        print("     breaches more is the operator's instinct measured.")
        if abs(tc - tw) < 0.05 and abs(bw - bc) < 0.05:
            print("     ❌ NEITHER GAP IS MATERIAL - a wrong-tine tap is not")
            print("        informative, and order is moot in both senses.")

    print("\n  ⚠️ THIS USES A DAILY REGRESSION CHANNEL, NOT THE PITCHFORK. It shares the")
    print("     property under test - a slope and two parallel rails - which is")
    print("     enough to ask whether slope predicts first contact. **If the")
    print("     answer is interesting, the real fork is the follow-up, not the")
    print("     conclusion.**")
    print("  ⚠️ AND ONE OBSERVATION PER SESSION. A fork seen on 300 ticks is one")
    print("     event, not 300.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
