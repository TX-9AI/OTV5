#!/usr/bin/env python3
"""
tests/opening_bias.py  v4.1
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Does the session OPENING expose a directional bias for the rest of the day?

v4.0  2026-08-19  Built at the OTV4 split. ROADMAP Phase 1.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

WHY THIS QUESTION IS DIFFERENT FROM EVERY OTHER ENTRY TEST SO FAR.
Every condition measured up to now was read AT THE MOMENT OF ENTRY, and every
one of them came back ambient - ADX > 30 held on 91% of good ContinuationStrategy
entries and 88% of bad ones. **That is not a weak signal; it is a PRE-FILTERED
population.** ADX > 30 is continuation's own gate, so every trade in the sample
had already cleared it. A condition cannot be measured on a population it
selected.

The opening candle cannot be pre-filtered. It is fixed by 09:45, it is a
property of the SESSION rather than of any entry, and no strategy had a say in
it. Every trade that day inherits the same value regardless of when it fired.
**It is the first genuinely independent variable in this investigation.**

AND IT IS ASKED OF THE TAPE, NOT OF THE TRADE BOOK. The trades cover 13 sessions
and 366 rows filtered by a broken engine. The tape covers every session and every
symbol collected - no strategy chose any of it.

⚠️ TWO OUTCOMES ARE MEASURED, DELIBERATELY.
  CLOSE      did the session close in the same direction. Blunt: a day that
             opens green, runs 1% and closes flat-red counts as a miss and was
             tradeable all morning.
  EXCURSION  was the day's LARGER excursion in that direction. Closer to what a
             directional bias is actually FOR - it asks whether the side was
             right, not whether the settle agreed.
Reporting only the first would understate a real bias; reporting only the second
would flatter one.

⚠️ SESSIONS ARE THE SAMPLE, NOT TRADES. Twenty trades on one trending day are
one observation, not twenty. Everything here counts (session, symbol) once.
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


def _wilson(k, n):
    if n == 0:
        return (0.0, 1.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def _verdict(k, n):
    if n < 30:
        return "n<30 - REPORTED, NOT INTERPRETED"
    lo, hi = _wilson(k, n)
    if lo > 0.50:
        return f"BIAS  [{lo:.0%},{hi:.0%}] excludes 50%"
    if hi < 0.50:
        return f"INVERSE  [{lo:.0%},{hi:.0%}] below 50%"
    return f"coin  [{lo:.0%},{hi:.0%}] spans 50%"


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


def forward_facts(rth, n_open):
    """What happened AFTER the opening window closed. The tradeable part.

    ⚠️ THE INCLUSIVE MEASURE IS PARTLY TAUTOLOGICAL AND THE FIRST VERSION OF
    THIS TOOL SHIPPED IT AS A FINDING. `up_excursion` asked whether the day's
    larger excursion was above the OPEN - but the opening candle's own range IS
    part of the day's range. A green 30m bar that runs 0.5% has already
    contributed that 0.5% to (high - open). The measure contained its own
    predictor, which is why the numbers rose monotonically with window length:
    5m 67%, 10m 72%, 15m 76%, 30m 82%. **The longer the window, the more of the
    day it physically contains.** The 89% cell was the most contaminated, not
    the best.

    ⚠️ BUT THE OPERATOR IS RIGHT THAT IT IS NOT PURE ARTIFACT. A trend day
    genuinely does begin at the open; the opening candle is the START of the
    move, not a coincidence. Two claims are tangled and only one is tradeable:
        "the opening move is PART of the day's move"  - descriptively true, and
            unactionable: by the time you know the bar was green it is spent.
        "AFTER the opening, price CONTINUES that way" - actionable, and the
            only number a trigger can use.
    Both are reported. **The GAP between them is how much of the day's move
    happens during the opening window** - worth knowing on its own, and if it
    accounts for all of it, the design consequence is that you must be in before
    10:00, which points straight at ORB.
    """
    if len(rth) <= n_open + 20:
        return None
    anchor = rth[n_open - 1][4]          # close of the opening window
    after = rth[n_open:]
    c = after[-1][4]
    hi = max(r[2] for r in after)
    lo = min(r[3] for r in after)
    return {
        "fwd_up_close": c > anchor,
        "fwd_up_excursion": (hi - anchor) >= (anchor - lo),
        "fwd_range_pct": (hi - lo) / anchor * 100.0,
        "fwd_move_pct": (c - anchor) / anchor * 100.0,
        "anchor": anchor,
    }


def indicators(rth, n_open):
    """VWAP, Bollinger, ADX and channel slope AS AT the opening window close.

    Everything is computed on bars 0..n_open-1 ONLY. A single bar of lookahead
    turns a predictor into a description of the answer, and that error is not
    visible in the output - it just looks like a strong result.
    """
    seg = rth[:n_open]
    if len(seg) < 5:
        return {}
    hs = [r[2] for r in seg]
    ls = [r[3] for r in seg]
    cs = [r[4] for r in seg]
    c = cs[-1]
    out = {}

    # VWAP proxy: typical price, unweighted (volume is not in these files).
    # An unweighted anchor is still an anchor; it is not called VWAP.
    tp = [(hs[k] + ls[k] + cs[k]) / 3.0 for k in range(len(seg))]
    anch = sum(tp) / len(tp)
    out["above_anchor"] = c > anch
    out["anchor_dist_pct"] = (c - anch) / anch * 100.0

    # Bollinger on what exists so far
    m = sum(cs) / len(cs)
    sd = (sum((x - m) ** 2 for x in cs) / len(cs)) ** 0.5 or 1e-9
    out["bb_z"] = (c - m) / sd
    out["bb_width_pct"] = (4 * sd) / m * 100.0

    # Wilder ADX needs 14+ periods; below that it is not ADX and is not reported
    if len(seg) >= 15:
        trs, pdm, ndm = [], [], []
        for k in range(1, len(seg)):
            up = hs[k] - hs[k - 1]
            dn = ls[k - 1] - ls[k]
            pdm.append(up if (up > dn and up > 0) else 0.0)
            ndm.append(dn if (dn > up and dn > 0) else 0.0)
            trs.append(max(hs[k] - ls[k], abs(hs[k] - cs[k - 1]),
                           abs(ls[k] - cs[k - 1])))
        atr = sum(trs) or 1e-9
        pdi = 100.0 * sum(pdm) / atr
        ndi = 100.0 * sum(ndm) / atr
        dx = 100.0 * abs(pdi - ndi) / max(pdi + ndi, 1e-9)
        out["adx_proxy"] = dx
        out["di_bull"] = pdi > ndi

    # channel slope over the opening window
    n = len(cs)
    mx = (n - 1) / 2.0
    my = sum(cs) / n
    den = sum((k - mx) ** 2 for k in range(n)) or 1e-9
    out["slope_up"] = (sum((k - mx) * (cs[k] - my) for k in range(n)) / den) > 0
    return out


def session_facts(rows):
    """Everything the opening can say, and what the day then did."""
    if len(rows) < 60:
        return None
    rth = [r for r in rows if "09:30" <= r[0] <= "16:00"]
    if len(rth) < 60:
        return None
    o = rth[0][1]
    close = rth[-1][4]
    hi = max(r[2] for r in rth)
    lo = min(r[3] for r in rth)

    def blk(n):
        b = rth[:n]
        return (b[0][1], max(x[2] for x in b), min(x[3] for x in b), b[-1][4])

    f = {}
    for n, name in ((5, "5m"), (10, "10m"), (15, "15m"), (30, "30m")):
        bo, bh, bl, bc = blk(n)
        f[name] = {
            "green": bc > bo,
            "body_pct": abs(bc - bo) / bo * 100.0,
            "range_pct": (bh - bl) / bo * 100.0,
            "close_in_range": (bc - bl) / max(bh - bl, 1e-9),
            "high": bh, "low": bl, "close": bc, "open": bo,
        }
    # forward-only outcomes and indicator state, per opening window
    for n, name in ((5, "5m"), (10, "10m"), (15, "15m"), (30, "30m")):
        fw = forward_facts(rth, n)
        if fw:
            f[name].update(fw)
        f[name].update(indicators(rth, n))

    # the day's answer
    f["day"] = {
        "up_close": close > o,
        "up_excursion": (hi - o) >= (o - lo),
        "close_pct": (close - o) / o * 100.0,
        "range_pct": (hi - lo) / o * 100.0,
        "open": o, "close": close, "high": hi, "low": lo,
    }
    # did the opening range hold or break, and which way first
    orb_hi, orb_lo = f["15m"]["high"], f["15m"]["low"]
    after = rth[15:]
    brk = None
    for _, _, bh, bl, _ in [(x[0], x[1], x[2], x[3], x[4]) for x in after]:
        if bh > orb_hi:
            brk = "up"
            break
        if bl < orb_lo:
            brk = "down"
            break
    f["orb"] = {"first_break": brk,
                "width_pct": (orb_hi - orb_lo) / o * 100.0}
    return f


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ohlc", default=OHLC)
    ap.add_argument("--symbol", default="", help="restrict to one symbol")
    a = ap.parse_args(argv[1:])

    facts = []
    for day_dir in sorted(glob.glob(os.path.join(os.path.expanduser(a.ohlc), "*"))):
        if not os.path.isdir(day_dir):
            continue
        day = os.path.basename(day_dir)
        for p in sorted(glob.glob(os.path.join(day_dir, "*_ohlc_*.csv"))):
            sym = os.path.basename(p).split("_ohlc_")[0].upper()
            if a.symbol and sym != a.symbol.upper():
                continue
            try:
                f = session_facts(load(p))
            except Exception:                                  # noqa: BLE001
                continue
            if f:
                f["_day"], f["_sym"] = day, sym
                facts.append(f)

    if not facts:
        print("no sessions loaded. ABSENT MEASUREMENT, not a null.")
        return 1

    print("=" * 86)
    print("OPENING BIAS - does the session opening expose direction for the day?")
    print(f"  {len(facts)} (session, symbol) observations across "
          f"{len({f['_day'] for f in facts})} dates, "
          f"{len({f['_sym'] for f in facts})} symbols")
    print("  ⚠️ SESSIONS ARE THE SAMPLE. Twenty trades on one trending day are")
    print("     ONE observation, not twenty.")
    print("=" * 86)

    # ── 1. INCLUSIVE vs FORWARD-ONLY, side by side ──────────────────────────
    print("\n  1. OPENING COLOUR -> DAY DIRECTION: inclusive vs FORWARD-ONLY")
    print("     INCLUSIVE measures from the session OPEN - the opening candle's")
    print("     own range is inside the answer, so it is partly tautological.")
    print("     FORWARD measures from the window CLOSE - the only tradeable part.")
    print("     ⚠️ THE GAP IS HOW MUCH OF THE DAY HAPPENS DURING THE OPENING.")
    print(f"    {'window':8}{'outcome':11}{'n':>6}{'incl':>7}{'fwd':>7}{'gap':>7}  forward verdict")
    print("    " + "-" * 72)
    for name in ("5m", "10m", "15m", "30m"):
        for outcome, ik, fk in (("close", "up_close", "fwd_up_close"),
                                ("excursion", "up_excursion", "fwd_up_excursion")):
            sel = [f for f in facts if fk in f[name]]
            n = len(sel)
            if not n:
                continue
            ki = sum(1 for f in sel if f[name]["green"] == f["day"][ik])
            kf = sum(1 for f in sel if f[name]["green"] == f[name][fk])
            print(f"    {name:8}{outcome:11}{n:>6}{ki/n:>6.0%}{kf/n:>7.0%}"
                  f"{(ki-kf)/n:>+7.0%}  {_verdict(kf, n)}")

    # ── 2. decisive openings, FORWARD only ──────────────────────────────────
    print("\n  2. DECISIVE OPENINGS (body >= 0.20%) - FORWARD ONLY")
    print(f"    {'window':8}{'outcome':11}{'n':>6}{'fwd':>7}  verdict")
    print("    " + "-" * 60)
    for name in ("5m", "10m", "15m", "30m"):
        for outcome, fk in (("close", "fwd_up_close"),
                            ("excursion", "fwd_up_excursion")):
            sel = [f for f in facts
                   if fk in f[name] and f[name]["body_pct"] >= 0.20]
            n = len(sel)
            if not n:
                continue
            k = sum(1 for f in sel if f[name]["green"] == f[name][fk])
            print(f"    {name:8}{outcome:11}{n:>6}{k/n:>6.0%}  {_verdict(k, n)}")

    # ── 3. closed on its highs, FORWARD only ────────────────────────────────
    print("\n  3. OPENING CLOSED IN TOP/BOTTOM THIRD OF ITS RANGE - FORWARD ONLY")
    print(f"    {'window':8}{'outcome':11}{'n':>6}{'fwd':>7}  verdict")
    print("    " + "-" * 60)
    for name in ("5m", "10m", "15m", "30m"):
        for outcome, fk in (("close", "fwd_up_close"),
                            ("excursion", "fwd_up_excursion")):
            sel = [f for f in facts if fk in f[name]
                   and (f[name]["close_in_range"] >= 0.67
                        or f[name]["close_in_range"] <= 0.33)]
            n = len(sel)
            if not n:
                continue
            k = sum(1 for f in sel
                    if (f[name]["close_in_range"] >= 0.67) == f[name][fk])
            print(f"    {name:8}{outcome:11}{n:>6}{k/n:>6.0%}  {_verdict(k, n)}")

    # ── 4. indicator state AT the 15m close -> forward direction ────────────
    print("\n  4. INDICATOR STATE AT THE 15m CLOSE -> FORWARD DIRECTION")
    print("     All computed on the opening window ONLY. A single bar of")
    print("     lookahead turns a predictor into a description of the answer,")
    print("     and it does not look wrong in the output.")
    print(f"    {'signal':34}{'n':>6}{'fwd close':>11}{'fwd exc':>9}  verdict (exc)")
    print("    " + "-" * 74)
    tests = [
        ("price above the opening anchor", lambda f: f["15m"].get("above_anchor")),
        ("anchor distance > 0.1%", lambda f: (f["15m"].get("anchor_dist_pct") or 0) > 0.1),
        ("bb z-score > +1 (upper band)", lambda f: (f["15m"].get("bb_z") or 0) > 1),
        ("bb z-score < -1 (lower band)", lambda f: (f["15m"].get("bb_z") or 0) < -1),
        ("channel slope up", lambda f: f["15m"].get("slope_up")),
        ("DI+ > DI- (directional index)", lambda f: f["15m"].get("di_bull")),
        ("ADX proxy > 25 AND DI+ > DI-",
         lambda f: (f["15m"].get("adx_proxy") or 0) > 25 and f["15m"].get("di_bull")),
        ("ADX proxy > 25 AND DI- > DI+",
         lambda f: (f["15m"].get("adx_proxy") or 0) > 25 and f["15m"].get("di_bull") is False),
    ]
    for label, fn in tests:
        sel = [f for f in facts if "fwd_up_close" in f["15m"] and fn(f) is not None]
        pos = [f for f in sel if fn(f)]
        n = len(pos)
        if n < 10:
            print(f"    {label:34}{n:>6}   (too few)")
            continue
        kc = sum(1 for f in pos if f["15m"]["fwd_up_close"])
        ke = sum(1 for f in pos if f["15m"]["fwd_up_excursion"])
        print(f"    {label:34}{n:>6}{kc/n:>10.0%}{ke/n:>9.0%}  {_verdict(ke, n)}")

    # ── 4. the ORB break: which side broke FIRST ────────────────────────────
    print("\n  4. FIRST BREAK OF THE 15m OPENING RANGE -> DAY DIRECTION")
    print("     This is ORB's own premise, asked of the tape rather than of the")
    print("     trades. ORB is the one v3 strategy with a positive record.")
    sel = [f for f in facts if f["orb"]["first_break"]]
    for outcome, key in (("close", "up_close"), ("excursion", "up_excursion")):
        n = len(sel)
        k = sum(1 for f in sel
                if (f["orb"]["first_break"] == "up") == f["day"][key])
        print(f"    {'break':8}{outcome:12}{n:>6}"
              f"{(k/n if n else 0):>7.0%}  {_verdict(k, n)}")
    nb = len(facts) - len(sel)
    if nb:
        print(f"    ({nb} session(s) never broke the 15m range at all)")

    # ── 5. does opening RANGE WIDTH change any of it? ───────────────────────
    print("\n  5. BY OPENING-RANGE WIDTH (15m range as % of price)")
    print("     A coiled morning and a 1.5% opening drive are different days;")
    print("     a bias that only holds in one of them is still worth knowing.")
    bands = [("narrow <0.4%", 0.0, 0.4), ("mid 0.4-0.8%", 0.4, 0.8),
             ("wide >0.8%", 0.8, 99.0)]
    print(f"    {'band':16}{'n':>6}{'15m->close':>12}{'15m->excursion':>16}")
    print("    " + "-" * 54)
    for label, lo_, hi_ in bands:
        sel = [f for f in facts if lo_ <= f["orb"]["width_pct"] < hi_]
        n = len(sel)
        if not n:
            continue
        k1 = sum(1 for f in sel if f["15m"]["green"] == f["day"]["up_close"])
        k2 = sum(1 for f in sel if f["15m"]["green"] == f["day"]["up_excursion"])
        print(f"    {label:16}{n:>6}{k1/n:>11.0%}{k2/n:>15.0%}")

    # ── 6. per-symbol, because a pooled bias can be one instrument ──────────
    print("\n  6. PER SYMBOL (15m -> excursion) - a pooled bias can be ONE name")
    bysym = collections.defaultdict(lambda: [0, 0])
    for f in facts:
        s = bysym[f["_sym"]]
        s[0] += 1
        if f["15m"]["green"] == f["day"]["up_excursion"]:
            s[1] += 1
    for sym, (n, k) in sorted(bysym.items(), key=lambda kv: -kv[1][1] / max(1, kv[1][0]))[:12]:
        if n >= 8:
            print(f"    {sym:8}{n:>5}{k/n:>7.0%}  {_verdict(k, n)}")

    print("\n  ⚠️ HOW TO READ THIS. A verdict of `coin` is a RESULT, not a")
    print("     failure - it says the opening does not expose direction and the")
    print("     search moves on. A `BIAS` verdict on n<30 is not a finding.")
    print("  ⚠️ AND A BIAS FOUND HERE IS STILL IN-SAMPLE. 27 sessions is one")
    print("     market character. It needs forward validation before it gates")
    print("     anything - LOG-ONLY first, as with every gate this project has")
    print("     shipped.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
