#!/usr/bin/env python3
"""
tests/entry_profile.py  v4.1
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

What did a GOOD entry look like? Profile contrast and the wants list.

v4.0  2026-08-19  Built at the OTV4 split. ROADMAP Phase 1.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

THE QUESTION, AND WHY IT IS NOT "WHICH FEATURE SEPARATES".
"Does feature X separate?" produces a ranked list of weak correlations and
invites a threshold on the best one. **That is exactly what v3 did with the
setup scorer, and it inverted**: A-grade 399 trades -$8,244 at 1.5x size against
B-grade 220 trades +$1,893.

This asks instead: what did the tape LOOK LIKE at entry on the trades that
worked? The output is a PROFILE CONTRAST plus a WANTS LIST - conditions that
hold more often on good entries than bad - because a trigger modelled on a
picture fires when the picture matches, not when one number clears a bar. A want
that is individually weak still earns its place if it shows up reliably; a
single-threshold gate would have thrown it away.

THE LABEL: DIRECTIONAL CORRECTNESS, NOT P&L.
Three different things were being blurred and the operator separated them:
  DIRECTIONALLY CORRECT  did the underlying move the way the trade pointed.
                         Pure entry quality. No option mechanics, no management.
  EVER REACHED x% (MFE)  entry quality PLUS option mechanics. A directionally
                         correct trade can still fail to reach x% if theta or
                         the spread ate the move.
  REALISED P&L           stops and management. **Those are the parts that
                         already work** (orb_trail_stop 95% / 107 / +$37,848;
                         theta_bleed 100% / 107) and measuring an ENTRY against
                         them credits or blames it for something downstream.
Primary label is DIRECTION. MFE is secondary. **Where the two disagree - right
direction, never reached x% - that is its own population**, and it is a friction
or strike-selection finding, not an entry finding.

WHY THE v3 SAMPLE IS GOOD FOR THIS, which is counter-intuitive.
The classifier that chose these entries picked the correct side on 44.9% of 715
trades (95% CI [41.3%, 48.6%]) - **worse than a coin**. A near-random sampler is
close to IDEAL for mining: the favourable trades are not "cases where the engine
was right", they are **cases where the structure was good enough to work
anyway**. The failures are an equally broad sample of what does not.

⚠️ THE RESIDUAL BIAS, STATED. The engine still chose WHEN AND WHERE to look, so
coverage is biased even though direction was noise. **A mined want needs forward
validation before it sizes anything.**

⚠️ AND AN AMBIENT CONDITION IS NOT A WANT. A condition holding on 95% of good
entries and 93% of bad ones is not characteristic of good entries - it is what
the tape usually does. The wants list reports BOTH rates and the lift, so
ambient conditions are visible rather than mistaken for signal.
"""

import argparse
import bisect
import collections
import csv
import glob
import math
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DTP = os.path.expanduser("~/day_trader_pro")
TRADES = os.path.join(DTP, "trades", "*", "*_trades_*.db")
OHLC = os.path.join(DTP, "ohlc")

EXCLUDE_STRATEGIES = {"ORBStrategy"}
NEUTRAL = ("condor", "butterfly", "iron")
POLLUTED = {"2026-08-14"}              # identity-chain artifacts


def _wilson(k, n):
    if n == 0:
        return (0.0, 1.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def load_tape(day, sym, root):
    for pat in (f"{sym}_ohlc_{day}.csv", f"{sym.upper()}_ohlc_{day}.csv"):
        p = os.path.join(root, day, pat)
        if not os.path.exists(p):
            continue
        rows = []
        with open(p) as fh:
            for r in csv.DictReader(fh):
                try:
                    rows.append((r["timestamp"][11:19], float(r["open"]),
                                 float(r["high"]), float(r["low"]),
                                 float(r["close"])))
                except Exception:                              # noqa: BLE001
                    continue
        return rows
    return None


def features(rows, i, side):
    """The structural picture at bar i. Derived from the tape, not journaled.

    ⚠️ EVERYTHING HERE IS RECOVERABLE RETROACTIVELY. None of it needed to have
    been recorded at entry time, which is the whole reason the v3 book can be
    mined at all - most of these were never columns.
    """
    if i < 20 or i >= len(rows):
        return None
    ts, o, h, l, c = rows[i]
    hs = [r[2] for r in rows[:i + 1]]
    ls = [r[3] for r in rows[:i + 1]]
    cs = [r[4] for r in rows[:i + 1]]
    day_hi, day_lo = max(hs), min(ls)
    rng = max(day_hi - day_lo, 1e-9)
    bull = side == "call"

    # where in the day's range, oriented so 1.0 always means "with the trade"
    pos = (c - day_lo) / rng
    pos_dir = pos if bull else (1.0 - pos)

    # the entry bar's own character
    body = abs(c - o)
    bar_rng = max(h - l, 1e-9)
    body_frac = body / bar_rng
    with_dir = (c > o) if bull else (c < o)

    # recent impulse: how far price has come in 20 bars, in bar-range units
    look = 20
    disp = (c - cs[-look]) / max(sum(r[2] - r[3] for r in rows[i - look:i]) / look, 1e-9)
    disp_dir = disp if bull else -disp

    # extension from the 20-bar mean, in ranges
    mean20 = sum(cs[-look:]) / look
    ext = (c - mean20) / max(rng, 1e-9)
    ext_dir = ext if bull else -ext

    # did the last 20-bar extreme in the trade's direction get taken and held?
    prior_ext = max(hs[-look:-1]) if bull else min(ls[-look:-1])
    broke = (h > prior_ext) if bull else (l < prior_ext)
    held = broke and ((c > prior_ext) if bull else (c < prior_ext))

    # session clock
    hhmm = ts[:5]
    mins = int(hhmm[:2]) * 60 + int(hhmm[3:5]) - (9 * 60 + 30)

    return {
        "in trade-direction half of day range": pos_dir > 0.5,
        "in trade-direction top quartile": pos_dir > 0.75,
        "in trade-direction bottom quartile (fading)": pos_dir < 0.25,
        "entry bar closes with the trade": bool(with_dir),
        "entry bar is decisive (body > 60% of range)": body_frac > 0.60,
        "entry bar is indecisive (body < 30%)": body_frac < 0.30,
        "20-bar displacement favours the trade": disp_dir > 0,
        "strong displacement (> 1 avg bar)": disp_dir > 1.0,
        "extended from 20-bar mean (> 20% of range)": ext_dir > 0.20,
        "stretched from mean (> 40% of range)": ext_dir > 0.40,
        "broke the 20-bar extreme": bool(broke),
        "broke AND HELD the 20-bar extreme": bool(held),
        "broke and FAILED to hold": bool(broke and not held),
        "first hour (09:30-10:30)": mins < 60,
        "midday (10:30-14:00)": 60 <= mins < 270,
        "last two hours": mins >= 270,
    }


def derived_features(rows, i, side, prior_hi=None, prior_lo=None):
    """Structure the TAPE can supply that no v3 column ever carried.

    ⚠️ WHY THESE AND NOT MORE RECORDED COLUMNS. On ContinuationStrategy's 366
    joined trades the recorded columns were either PRE-FILTERED GATES or EMPTY:
    ADX > 30 held on 91% of good entries and 88% of bad - it is continuation's
    own entry gate, so every trade in the sample had already cleared it, and a
    condition cannot be measured on a population it selected. `flat_angle_deg`
    was 98%/99% below 10 degrees. `gap_pct` and `level_strength` were 0%
    populated and `vix_at_entry` 2% - fixed on 2026-08-18/19, after this sample
    ends.
    **Everything below is computed from OHLC and needs no column to have
    existed**, which is the only reason the v3 book can be asked these
    questions at all.
    """
    if i < 30 or i >= len(rows):
        return {}
    _, o, h, l, c = rows[i]
    cs = [r[4] for r in rows[:i + 1]]
    hs = [r[2] for r in rows[:i + 1]]
    ls = [r[3] for r in rows[:i + 1]]
    bull = side == "call"
    out = {}

    # ── VWAP: a session anchor, and the closest thing to "fair" on the day ────
    # Typical price, unweighted - volume is not in these files. An unweighted
    # anchor is still an anchor; it is simply not VWAP and is not called that.
    tp = [(hs[k] + ls[k] + cs[k]) / 3.0 for k in range(i + 1)]
    anchor = sum(tp) / len(tp)
    rng = max(max(hs) - min(ls), 1e-9)
    d_anchor = (c - anchor) / rng
    d_dir = d_anchor if bull else -d_anchor
    out["above the session anchor, with the trade"] = d_dir > 0
    out["far from anchor (> 15% of range, with)"] = d_dir > 0.15
    out["far from anchor AGAINST the trade"] = d_dir < -0.15
    out["hugging the anchor (within 5% of range)"] = abs(d_anchor) < 0.05

    # ── channel position: a regression through the last 30 bars, and where
    #    price sits inside its own dispersion. This is the pitchfork question
    #    asked without a fork - slope plus containment.
    look = 30
    ys = cs[-look:]
    n = len(ys)
    mx = (n - 1) / 2.0
    my = sum(ys) / n
    den = sum((k - mx) ** 2 for k in range(n)) or 1e-9
    slope = sum((k - mx) * (ys[k] - my) for k in range(n)) / den
    resid = [ys[k] - (my + slope * (k - mx)) for k in range(n)]
    sd = (sum(r * r for r in resid) / n) ** 0.5 or 1e-9
    z = resid[-1] / sd                       # where in the channel, in sigma
    slope_dir = slope if bull else -slope
    out["channel slopes with the trade"] = slope_dir > 0
    out["at the channel edge WITH the trade (z > 1)"] = (z > 1 if bull else z < -1)
    out["at the channel edge AGAINST the trade (z < -1)"] = (z < -1 if bull else z > 1)
    out["mid-channel (|z| < 0.5)"] = abs(z) < 0.5

    # ── prior-session extremes: the levels the mapper names PDH/PDL ───────────
    if prior_hi and prior_lo and prior_hi > prior_lo:
        near = 0.0015                        # 0.15% - a level is "in play"
        out["within 0.15% of prior-day high"] = abs(c - prior_hi) / c < near
        out["within 0.15% of prior-day low"] = abs(c - prior_lo) / c < near
        beyond = (c > prior_hi) if bull else (c < prior_lo)
        out["beyond the prior-day extreme, with the trade"] = bool(beyond)
        inside = prior_lo < c < prior_hi
        out["inside yesterday's range"] = bool(inside)
    return out


def recorded_features(r):
    """Conditions from columns the bot RECORDED at entry, not derived from tape.

    Returns (conditions, populated) - `populated` marks which source columns
    actually carried data, because three of these were largely EMPTY in the v3
    book and only fixed on 2026-08-18/19:
        flat_angle_deg   100% ties on ONE value - computed every tick, never
        level_strength   94% ties on TWO - the formula collapsed because
                         touch_count is a constant, and only a hard-gated
                         strategy wrote it
        vix_at_entry     58% default-zero - the two highest-volume strategies
                         never set it
    An empty column reads as "no signal" when it is "no data", and that
    confusion has already cost this project one wrong conclusion per column.
    """
    out, pop = {}, {}

    def _f(name, default=None):
        v = r.get(name)
        try:
            return float(v) if v is not None else default
        except Exception:                                      # noqa: BLE001
            return default

    adx = _f("adx_at_entry")
    pop["adx_at_entry"] = adx is not None and adx > 0
    if pop["adx_at_entry"]:
        out["ADX > 20 (trending)"] = adx > 20
        out["ADX > 30 (strong)"] = adx > 30
        out["ADX < 15 (no trend)"] = adx < 15

    vix = _f("vix_at_entry")
    pop["vix_at_entry"] = vix is not None and vix > 0
    if pop["vix_at_entry"]:
        out["VIX < 15 (calm)"] = vix < 15
        out["VIX > 20 (elevated)"] = vix > 20

    ang = _f("flat_angle_deg", -1.0)
    pop["flat_angle_deg"] = ang is not None and ang >= 0
    if pop["flat_angle_deg"]:
        out["flat angle < 10 deg (flat tape)"] = ang < 10
        out["flat angle > 20 deg (sloped)"] = ang > 20

    lvl = _f("level_strength")
    pop["level_strength"] = lvl is not None and lvl > 0
    if pop["level_strength"]:
        out["graded level nearby (strength > 0.5)"] = lvl > 0.5
        out["premium level nearby (strength > 0.8)"] = lvl > 0.8

    gap = _f("gap_pct")
    pop["gap_pct"] = gap is not None
    if pop["gap_pct"]:
        out["gap |>| 0.5%"] = abs(gap) > 0.5
        out["gap |>| 1.5% (large)"] = abs(gap) > 1.5

    ss = _f("setup_score")
    pop["setup_score"] = ss is not None and ss > 0
    if pop["setup_score"]:
        out["setup_score > 1.0"] = ss > 1.0

    return out, pop


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", default=TRADES)
    ap.add_argument("--ohlc", default=OHLC)
    ap.add_argument("--since", default="2026-07-13")
    ap.add_argument("--strategy", default="",
                    help="REQUIRED in practice: profile ONE strategy. Pooling "
                         "continuation, sweep and credit spreads averages away "
                         "what makes each work - they trade WITH a move, "
                         "AGAINST one at a level, and for price NOT reaching "
                         "somewhere. A want decisive for one is noise in another.")
    ap.add_argument("--mfe-pct", type=float, default=25.0,
                    help="secondary label: ever reached this %% of premium")
    a = ap.parse_args(argv[1:])

    tapes, rows, prior = {}, [], {}
    for db in sorted(glob.glob(os.path.expanduser(a.trades))):
        if "_archive" in db or db.endswith(".bak"):
            continue
        m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(db))
        if not m or m.group(1) < a.since or m.group(1) in POLLUTED:
            continue
        day = m.group(1)
        try:
            con = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
            recs = con.execute("SELECT * FROM trades WHERE status='closed'").fetchall()
        except Exception:                                      # noqa: BLE001
            continue
        for r in recs:
            r = dict(r)
            strat = str(r.get("strategy") or "")
            setup = str(r.get("setup_type") or "").lower()
            if strat in EXCLUDE_STRATEGIES:
                continue
            if any(k in setup or k in strat.lower() for k in NEUTRAL):
                continue
            side = str(r.get("option_side") or "").lower()
            sym = str(r.get("symbol") or "")
            et, xt = str(r.get("entry_time") or ""), str(r.get("exit_time") or "")
            if side not in ("call", "put") or not sym or len(et) < 19 or len(xt) < 19:
                continue
            key = (day, sym)
            if key not in tapes:
                tapes[key] = load_tape(day, sym, a.ohlc)
            tape = tapes[key]
            if not tape:
                continue
            stamps = [t[0] for t in tape]
            i = bisect.bisect_right(stamps, et[11:19]) - 1
            j = bisect.bisect_right(stamps, xt[11:19]) - 1
            if i < 20 or j <= i or j >= len(tape):
                continue
            ue, ux = tape[i][4], tape[j][4]
            if ue <= 0:
                continue
            move = (ux - ue) / ue
            right = (move > 0) if side == "call" else (move < 0)
            ent = r.get("entry_premium") or 0
            mx = r.get("max_premium_seen")
            try:
                mfe = ((float(mx) - float(ent)) / float(ent) * 100.0
                       if mx is not None and float(ent) > 0 else None)
            except Exception:                                  # noqa: BLE001
                mfe = None
            f = features(tape, i, side)
            if not f:
                continue
            rf, rpop = recorded_features(r)
            f.update(rf)
            f.update(derived_features(tape, i, side,
                                      prior.get(key, (None, None))[0],
                                      prior.get(key, (None, None))[1]))
            rows.append({"day": day, "sym": sym, "side": side, "strategy": strat,
                         "right": right, "mfe": mfe, "feat": f, "pop": rpop})

    if not rows:
        print("no usable trades. ABSENT MEASUREMENT, not a null.")
        return 1

    if a.strategy:
        rows = [r for r in rows if r["strategy"] == a.strategy]
        if not rows:
            print(f"no trades for strategy={a.strategy!r}")
            print("  ABSENT MEASUREMENT, not a null.")
            return 1
    else:
        # ⚠️ POOLED IS ALMOST ALWAYS THE WRONG QUESTION. Printed so the mix is
        # visible before anyone reads a pooled number as a finding.
        mix = collections.Counter(r["strategy"] for r in rows)
        print("  ⚠️ NO --strategy GIVEN. Pooling these averages away what makes")
        print("     each work. Mix in this sample:")
        for k, v in mix.most_common():
            print(f"       {k:30} {v}")
        print("     Re-run with --strategy for anything you intend to act on.\n")

    good = [r for r in rows if r["right"]]
    bad = [r for r in rows if not r["right"]]
    print("=" * 88)
    print("ENTRY PROFILE - what did a GOOD entry look like?")
    print(f"  {len(rows)} trades, {len({r['day'] for r in rows})} sessions. "
          f"ORB and neutral structures EXCLUDED.")
    print(f"  label = DIRECTIONALLY CORRECT (underlying moved with the trade)")
    print(f"  strategy: {a.strategy or 'ALL (pooled - see warning above)'}")
    print(f"  good {len(good)}   bad {len(bad)}")
    if len(rows) < 200:
        print(f"  ⚠️ n={len(rows)} - UNDER-POWERED. Reported, NOT interpreted.")
        print("     v3's sweep_reversal had 34 trades and TC.6 had 21; a profile")
        print("     built on those describes the sample, not the setup.")
    print("=" * 88)

    # ⚠️ REPORT COVERAGE BEFORE ANY LIFT. Three recorded columns were largely
    # EMPTY in the v3 book and only fixed on 2026-08-18/19. A feature present on
    # 5% of rows cannot be judged, and its lift is noise dressed as a finding -
    # the exact error that made flat_angle_deg, level_strength and vix_at_entry
    # read as measured nulls when they were unwritten columns.
    popcount = collections.Counter()
    for r in rows:
        for k, v in (r.get("pop") or {}).items():
            if v:
                popcount[k] += 1
    if popcount or any(r.get("pop") for r in rows):
        print("\n  RECORDED-COLUMN COVERAGE (how many trades actually carry it)")
        srcs = sorted({k for r in rows for k in (r.get("pop") or {})})
        for k in srcs:
            n = popcount.get(k, 0)
            pct = 100.0 * n / len(rows)
            note = ("USABLE" if pct >= 60 else
                    "THIN - lift is not interpretable" if pct >= 15 else
                    "EMPTY - no data, NOT a null result")
            print(f"    {k:24}{n:>6}/{len(rows)}  {pct:>5.0f}%  {note}")

    # a feature only appears on rows where its source column was populated, so
    # union the keys rather than reading them off the first row
    keys = sorted({k for r in rows for k in r["feat"]})

    def rate(pop, k):
        # only count rows where the feature EXISTS - a row whose source column
        # was empty must not be scored as False
        have = [r for r in pop if k in r["feat"]]
        return (sum(1 for r in have if r["feat"][k]) / len(have)) if have else 0.0

    def nfeat(k):
        return sum(1 for r in rows if k in r["feat"])

    scored = []
    for k in keys:
        g, b = rate(good, k), rate(bad, k)
        scored.append((g - b, k, g, b))
    scored.sort(reverse=True)

    print("\n  WANTS - conditions more common on GOOD entries")
    print(f"    {'condition':46}{'good':>7}{'bad':>7}{'lift':>8}  note")
    print("    " + "-" * 78)
    for lift, k, g, b in scored:
        if lift <= 0:
            continue
        nf = nfeat(k)
        note = ("n=%d TOO THIN" % nf if nf < 60
                else "AMBIENT - true of entries generally" if g > 0.90 and b > 0.85
                else "strong" if lift >= 0.10
                else "weak - keep only in company")
        print(f"    {k:46}{g:>6.0%}{b:>7.0%}{lift:>+8.0%}  {note}")

    print("\n  ANTI-WANTS - conditions more common on BAD entries")
    print(f"    {'condition':46}{'good':>7}{'bad':>7}{'lift':>8}  note")
    print("    " + "-" * 78)
    for lift, k, g, b in reversed(scored):
        if lift >= 0:
            continue
        note = ("AMBIENT" if b > 0.90 and g > 0.85
                else "strong" if lift <= -0.10 else "weak")
        print(f"    {k:46}{g:>6.0%}{b:>7.0%}{lift:>+8.0%}  {note}")

    for sd in ("call", "put"):
        gs = [r for r in good if r["side"] == sd]
        bs = [r for r in bad if r["side"] == sd]
        if len(gs) < 30 or len(bs) < 30:
            print(f"\n  {sd.upper()}S: too few to profile "
                  f"(good {len(gs)}, bad {len(bs)}) - REPORTED, NOT INTERPRETED")
            continue
        sc = sorted(((rate(gs, k) - rate(bs, k), k) for k in keys), reverse=True)
        print(f"\n  {sd.upper()}S ONLY (good {len(gs)}, bad {len(bs)}) - top 5 wants")
        for lift, k in sc[:5]:
            print(f"    {k:46}{lift:>+8.0%}")

    dis = [r for r in rows if r["right"] and r["mfe"] is not None
           and r["mfe"] < a.mfe_pct]
    if dis:
        print(f"\n  ⚠️ RIGHT DIRECTION BUT NEVER REACHED {a.mfe_pct:.0f}% MFE: "
              f"{len(dis)} of {len(good)} correct entries ({100.0*len(dis)/max(1,len(good)):.0f}%)")
        print("     **This is NOT an entry finding.** The read was correct and the")
        print("     structure did not pay - friction, strike selection or expiry.")
        print("     Fixing it by changing the ENTRY would be treating the wrong layer.")

    print("\n  ⚠️ HOW TO USE THIS. These are WANTS, not thresholds. A trigger")
    print("     modelled on a picture counts how many hold; it does not gate on")
    print("     one number. v3 gated on one number and its A-grade lost $8,244")
    print("     at 1.5x size while B-grade made +$1,893.")
    print("  ⚠️ AMBIENT rows are what the tape usually does. They are printed so")
    print("     they can be RULED OUT, not adopted.")
    print("  ⚠️ AND NOTHING HERE IS FORWARD-VALIDATED. The v3 engine chose when")
    print("     and where to look; coverage is biased even though direction was")
    print("     noise. LOG-ONLY before any of it gates a trade.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
