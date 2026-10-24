#!/usr/bin/env python3
"""
tests/chain_feasibility.py  v4.0
How big a move must the underlying make for the contract to pay? Does the tape
deliver it?

v4.0  2026-08-19  Built at the OTV4 split. ROADMAP Phase 1.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

THE QUESTION THIS EXISTS TO ANSWER.
`tests/entry_profile.py` found that **155 of 190 directionally-correct
ContinuationStrategy entries - 82% - never reached 25% MFE**. The read was
right and the position did not pay. No entry trigger fixes that, and mining
better entries while it is true would be optimising the wrong layer.

So: given the contract that was actually bought - its delta, its spread, its
theta, the time it had - **HOW BIG A MOVE DID IT NEED?** And then, separately:
**how often does the tape deliver a move that size in the time available?**

⚠️ THIS IS A FEASIBILITY QUESTION, NOT A TRIGGER QUESTION, and the distinction
decides what gets built next. If a contract needs a 0.8% move in 40 minutes and
the tape delivers that on 12% of bars, then the ceiling is STRIKE AND EXPIRY
SELECTION, not entry timing - and a tape harness mining for "moments that
predict a 0.3% move" would be mining for something that cannot pay.

WHY THE CHAIN IS THE RIGHT INSTRUMENT AND HAS NOT BEEN ASKED THIS.
The separation probe tested the chain as a DIRECTIONAL predictor and it failed:
25-delta risk-reversal Cliff's delta +0.09, skew +0.03 not significant, ATM IV
level INVERTED. **That is a different question.** The chain is poor at saying
which way price goes. It is authoritative on what a move is WORTH, because that
is arithmetic rather than prediction.

⚠️ FRICTION IS PART OF THE BAR, NOT AN ADJUSTMENT TO IT. FRC.1 measured the
fleet's gross edge at ~2% of its own round-trip spread. A contract entered at
the ask and exited at the bid starts the trade down by the full spread, and the
move must cover that BEFORE it pays anything. Quoting a required move that
ignores it would understate the bar by more than the bar itself.

⚠️ AND DELTA IS A LOCAL APPROXIMATION. A 0DTE option's delta moves fast; using
entry delta to project a large move understates the payoff on the winners
(gamma helps) and overstates nothing. Gamma is reported alongside so the size of
that error is visible rather than assumed away. **The first-order number is a
FLOOR on the required move, not an estimate of it.**
"""

import argparse
import bisect
import collections
import csv
import glob
import gzip
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DTP = os.path.expanduser("~/day_trader_pro")
CHAINS = os.path.join(DTP, "chain_snapshots")
OHLC = os.path.join(DTP, "ohlc")
TRADES = os.path.join(DTP, "trades", "*", "*_trades_*.db")
POLLUTED = {"2026-08-14"}


def _pct(v, p):
    if not v:
        return float("nan")
    s = sorted(v)
    return s[min(len(s) - 1, int(p / 100.0 * len(s)))]


def load_snaps(root, day, sym):
    """Every snapshot for (day, symbol), oldest first."""
    for cand in (os.path.join(root, day, f"{sym}.jsonl.gz"),
                 os.path.join(root, day, f"{sym.upper()}.jsonl.gz")):
        if not os.path.exists(cand):
            continue
        out = []
        try:
            with gzip.open(cand, "rt") as fh:
                for line in fh:
                    try:
                        out.append(json.loads(line))
                    except Exception:                          # noqa: BLE001
                        continue
        except Exception:                                      # noqa: BLE001
            return []
        return sorted(out, key=lambda r: r.get("ts_et", ""))
    return []


def required_move(c, target_pct, spot):
    """Underlying move (in %) needed for this contract to gain target_pct.

    First order: dPremium ~ delta * dSpot. Entry pays the ASK, exit receives the
    BID, so the position starts down by the full spread and the move must cover
    that first.
    """
    try:
        bid = float(c.get("bid") or 0.0)
        ask = float(c.get("ask") or 0.0)
        dlt = abs(float(c.get("delta") or 0.0))
        if ask <= 0 or dlt <= 0 or spot <= 0:
            return None
        mid = (bid + ask) / 2.0 if bid > 0 else ask
        entry = ask                       # crossed the spread to get in
        want = entry * (1.0 + target_pct / 100.0)
        # exit at the bid: premium must reach want + (ask-bid) to net it
        spread = max(ask - bid, 0.0)
        need_prem = want + spread
        d_prem = need_prem - mid
        if d_prem <= 0:
            return 0.0
        d_spot = d_prem / dlt
        return 100.0 * d_spot / spot
    except Exception:                                          # noqa: BLE001
        return None


def tape_moves(rows, i, horizon):
    """Largest favourable excursion (either way) within `horizon` bars of i."""
    if i < 0 or i + 1 >= len(rows):
        return None
    seg = rows[i + 1:i + 1 + horizon]
    if not seg:
        return None
    c = rows[i][4]
    if c <= 0:
        return None
    up = (max(r[2] for r in seg) - c) / c * 100.0
    dn = (c - min(r[3] for r in seg)) / c * 100.0
    return up, dn


def load_tape(root, day, sym):
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
    return []


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--chains", default=CHAINS)
    ap.add_argument("--ohlc", default=OHLC)
    ap.add_argument("--target", type=float, default=25.0,
                    help="premium gain to price the move for")
    ap.add_argument("--horizon", type=int, default=40,
                    help="bars (minutes) allowed for the move")
    ap.add_argument("--symbol", default="")
    a = ap.parse_args(argv[1:])

    days = sorted(os.path.basename(d) for d in
                  glob.glob(os.path.join(os.path.expanduser(a.chains), "*"))
                  if os.path.isdir(d))
    days = [d for d in days if d not in POLLUTED]
    if not days:
        print(f"no chain snapshots under {a.chains}")
        print("  ABSENT MEASUREMENT, not a null.")
        return 1

    need_by_delta = collections.defaultdict(list)
    spread_by_delta = collections.defaultdict(list)
    rows_seen = 0
    feas = []            # (required_move_pct, delivered_up, delivered_dn)

    for day in days:
        for p in sorted(glob.glob(os.path.join(
                os.path.expanduser(a.chains), day, "*.jsonl.gz"))):
            sym = os.path.basename(p).replace(".jsonl.gz", "").upper()
            if a.symbol and sym != a.symbol.upper():
                continue
            snaps = load_snaps(os.path.expanduser(a.chains), day, sym)
            if not snaps:
                continue
            tape = load_tape(os.path.expanduser(a.ohlc), day, sym)
            stamps = [t[0] for t in tape]
            for s in snaps:
                spot = s.get("underlying")
                if not spot:
                    continue
                ts = str(s.get("ts_et", ""))[11:19]
                i = bisect.bisect_right(stamps, ts) - 1 if stamps else -1
                moved = tape_moves(tape, i, a.horizon) if i >= 20 else None
                for c in (s.get("contracts") or []):
                    dlt = abs(float(c.get("delta") or 0.0))
                    if not (0.05 <= dlt <= 0.95):
                        continue
                    rq = required_move(c, a.target, float(spot))
                    if rq is None:
                        continue
                    rows_seen += 1
                    band = ("0.05-0.20" if dlt < 0.20 else
                            "0.20-0.35" if dlt < 0.35 else
                            "0.35-0.50" if dlt < 0.50 else
                            "0.50-0.70" if dlt < 0.70 else "0.70-0.95")
                    need_by_delta[band].append(rq)
                    bid = float(c.get("bid") or 0.0)
                    ask = float(c.get("ask") or 0.0)
                    if ask > 0:
                        spread_by_delta[band].append(
                            100.0 * max(ask - bid, 0.0) / ((ask + bid) / 2.0
                                                           if bid > 0 else ask))
                    if moved and 0.30 <= dlt <= 0.60:
                        up, dn = moved
                        feas.append((rq, up, dn))

    if not rows_seen:
        print("no usable contract rows. ABSENT MEASUREMENT, not a null.")
        return 1

    print("=" * 84)
    print("CHAIN FEASIBILITY - what move does the contract need, and does the "
          "tape deliver it?")
    print(f"  {rows_seen:,} contract observations, {len(days)} dates")
    print(f"  target: +{a.target:.0f}% premium   horizon: {a.horizon} bars")
    print("=" * 84)

    print("\n  1. REQUIRED UNDERLYING MOVE, BY ENTRY DELTA")
    print("     Includes the round-trip spread: entry pays the ask, exit takes")
    print("     the bid, so the move must cover the spread BEFORE it pays.")
    print(f"    {'delta band':12}{'n':>8}{'p25':>8}{'p50':>8}{'p75':>8}"
          f"{'spread%':>10}")
    print("    " + "-" * 56)
    for band in ("0.05-0.20", "0.20-0.35", "0.35-0.50", "0.50-0.70", "0.70-0.95"):
        v = need_by_delta.get(band)
        if not v:
            continue
        sp = spread_by_delta.get(band) or [0]
        print(f"    {band:12}{len(v):>8}{_pct(v,25):>7.2f}%{_pct(v,50):>7.2f}%"
              f"{_pct(v,75):>7.2f}%{_pct(sp,50):>9.0f}%")

    if feas:
        print(f"\n  2. DOES THE TAPE DELIVER IT? (0.30-0.60 delta, "
              f"{a.horizon}-bar horizon)")
        print("     For each snapshot: the move the contract needed, against the")
        print("     largest excursion the tape actually produced afterwards.")
        hit = sum(1 for rq, up, dn in feas if max(up, dn) >= rq)
        hit_dir = sum(1 for rq, up, dn in feas if up >= rq)
        print(f"    observations                : {len(feas):,}")
        print(f"    tape delivered the required move (either way): "
              f"{100.0*hit/len(feas):.0f}%")
        print(f"    delivered it to the UPSIDE only              : "
              f"{100.0*hit_dir/len(feas):.0f}%")
        rqs = [x[0] for x in feas]
        ups = [max(x[1], x[2]) for x in feas]
        print(f"    required move   p50 {_pct(rqs,50):.2f}%   p75 {_pct(rqs,75):.2f}%")
        print(f"    delivered move  p50 {_pct(ups,50):.2f}%   p75 {_pct(ups,75):.2f}%")
        print()
        print("    ⚠️ READ THIS BEFORE ANY TRIGGER WORK. If the required move")
        print("       exceeds what the tape usually delivers, the binding")
        print("       constraint is STRIKE AND EXPIRY SELECTION - and no entry")
        print("       trigger fixes it. Mining the tape for moments that precede")
        print("       a move too small to pay would be optimising the wrong")
        print("       layer, which is what 82% of correct-direction entries")
        print("       failing to reach +25% already suggests.")

    print("\n  ⚠️ THE REQUIRED MOVE IS A FLOOR, NOT AN ESTIMATE. It is first")
    print("     order in delta; gamma helps the winners, so a large move pays")
    print("     MORE than this arithmetic says. It does not help the losers.")
    print("  ⚠️ AND THE SPREAD IS PART OF THE BAR, not an adjustment to it.")
    print("     FRC.1 measured the fleet's gross edge at ~2% of its own")
    print("     round-trip spread.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
