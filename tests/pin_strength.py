#!/usr/bin/env python3
"""
tests/pin_strength.py  v4.0
Does PIN CONCENTRATION predict that price actually holds the pin?

v4.0  2026-08-19  Built at the OTV4 split. ROADMAP Phase 1.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

THE QUESTION, AND WHY IT IS THE ONLY ONE LEFT FOR THE BUTTERFLY.
Two of the three things a pin butterfly needs are already answered:
  IS IT PINNING?   `gex_data` classifies the environment from net/gross sign.
  CAN PRICE REACH? `tests/magnitude_estimator.py` maps ATR -> reachable move.
What was missing is **HOW STRONGLY** - because a butterfly's wings only pay if
price STAYS at the pin, not if it merely arrives.

`pin_conc` = |pin strike net GEX| / gross |GEX| already existed inside
`gex_data.classify`, was used to decide the PINNING label, and was then
**DISCARDED as a local.** A strike holding 40% of gross gamma is one dominant
magnet; one holding 8% is gamma smeared across many strikes with nothing
actually pinned - **and both read "PINNING"** once past the 0.15 threshold.
v4 exposes it as `snapshot.pin_concentration`.

⚠️ EXPOSING A NUMBER IS NOT VALIDATING IT. This asks whether the number
predicts anything: bin snapshots by concentration, then measure how close price
ended up to the pin. **If high-concentration pins land within a strike and
low-concentration ones scatter, the measure is real and the threshold falls out
of the data rather than out of a preference.**

⚠️ AND TIME MATTERS FOR 0DTE. Concentration read at 10:00 predicting a 16:00
settle is a different claim from concentration read at 14:00, because gamma
sharpens as expiry approaches. Both are reported; if only the late reading
works, the butterfly is an afternoon trade and the rule must say so.

⚠️ THE HONEST NULL: if every concentration band lands the same distance from
the pin, concentration does not measure pin strength and the butterfly has no
edge from it. That is a result, and it is cheaper to find here than live.
"""

import argparse
import bisect
import collections
import csv
import glob
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DTP = os.path.expanduser("~/day_trader_pro")
CHAINS = os.path.join(DTP, "chain_snapshots")
OHLC = os.path.join(DTP, "ohlc")
POLLUTED = {"2026-08-14"}


def _pct(v, p):
    if not v:
        return float("nan")
    s = sorted(v)
    return s[min(len(s) - 1, int(p / 100.0 * len(s)))]


def gex_from_contracts(contracts, spot):
    """net GEX per strike, gross, and the pin. Formula from data/gex_data.py.

    call_gex = gamma * oi * 100 * spot ; put_gex = same * -1 (puts flip sign).
    Reimplemented here ONLY because the archived snapshots predate the exposed
    field - live code must read `snapshot.pin_concentration`, never this.
    """
    per = collections.defaultdict(float)
    for c in contracts or []:
        try:
            g = float(c.get("gamma") or 0.0)
            oi = float(c.get("oi") or 0.0)
            k = float(c.get("strike") or 0.0)
            t = str(c.get("type") or "").lower()
        except Exception:                                      # noqa: BLE001
            continue
        if not g or not oi or not k:
            continue
        v = g * oi * 100.0 * spot
        per[k] += v if t.startswith("c") else -v
    if not per:
        return None
    gross = sum(abs(v) for v in per.values()) or 1.0
    net = sum(per.values())
    pin_k = max(per.items(), key=lambda kv: abs(kv[1]))[0]
    pin_v = per[pin_k]
    return {
        "pin_strike": pin_k,
        "pin_conc": abs(pin_v) / gross,
        "net_ratio": net / gross,
        "n_strikes": len(per),
    }


def load_tape(root, day, sym):
    for pat in (f"{sym}_ohlc_{day}.csv", f"{sym.upper()}_ohlc_{day}.csv"):
        p = os.path.join(root, day, pat)
        if not os.path.exists(p):
            continue
        rows = []
        with open(p) as fh:
            for r in csv.DictReader(fh):
                try:
                    rows.append((r["timestamp"][11:19], float(r["high"]),
                                 float(r["low"]), float(r["close"])))
                except Exception:                              # noqa: BLE001
                    continue
        return rows
    return []


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--chains", default=CHAINS)
    ap.add_argument("--ohlc", default=OHLC)
    ap.add_argument("--symbol", default="")
    a = ap.parse_args(argv[1:])

    obs = []
    days = sorted(os.path.basename(d) for d in
                  glob.glob(os.path.join(os.path.expanduser(a.chains), "*"))
                  if os.path.isdir(d))
    days = [d for d in days if d not in POLLUTED]
    for day in days:
        for p in sorted(glob.glob(os.path.join(
                os.path.expanduser(a.chains), day, "*.jsonl.gz"))):
            sym = os.path.basename(p).replace(".jsonl.gz", "").upper()
            if a.symbol and sym != a.symbol.upper():
                continue
            tape = load_tape(os.path.expanduser(a.ohlc), day, sym)
            if not tape:
                continue
            stamps = [t[0] for t in tape]
            settle = tape[-1][3]
            try:
                with gzip.open(p, "rt") as fh:
                    lines = fh.readlines()
            except Exception:                                  # noqa: BLE001
                continue
            for line in lines:
                try:
                    s = json.loads(line)
                except Exception:                              # noqa: BLE001
                    continue
                spot = s.get("underlying")
                if not spot:
                    continue
                g = gex_from_contracts(s.get("contracts"), float(spot))
                if not g or g["pin_strike"] <= 0:
                    continue
                ts = str(s.get("ts_et", ""))[11:19]
                i = bisect.bisect_right(stamps, ts) - 1
                if i < 0:
                    continue
                pin = g["pin_strike"]
                # distance from settle to the pin, and from spot NOW to the pin
                d_settle = abs(settle - pin) / pin * 100.0
                d_now = abs(float(spot) - pin) / pin * 100.0
                hh = ts[:5]
                obs.append({
                    "hhmm": hh, "conc": g["pin_conc"], "net": g["net_ratio"],
                    "d_settle": d_settle, "d_now": d_now,
                    "converged": d_settle < d_now, "sym": sym, "day": day,
                })

    if not obs:
        print("no snapshots joined to tape. ABSENT MEASUREMENT, not a null.")
        return 1

    print("=" * 84)
    print("PIN STRENGTH - does concentration predict that price HOLDS the pin?")
    print(f"  {len(obs):,} snapshots, {len({o['day'] for o in obs})} dates, "
          f"{len({o['sym'] for o in obs})} symbols")
    print("=" * 84)

    print("\n  1. DISTANCE FROM SETTLE TO PIN, BY CONCENTRATION")
    print("     If concentration measures pin strength, high bands land CLOSER.")
    print(f"    {'concentration':16}{'n':>8}{'p25':>8}{'p50':>8}{'p75':>8}"
          f"{'converged':>11}")
    print("    " + "-" * 60)
    bands = [(0, .10), (.10, .15), (.15, .25), (.25, .40), (.40, 1.01)]
    med = []
    for lo, hi in bands:
        sel = [o for o in obs if lo <= o["conc"] < hi]
        if len(sel) < 50:
            continue
        d = [o["d_settle"] for o in sel]
        conv = sum(1 for o in sel if o["converged"]) / len(sel)
        med.append(_pct(d, 50))
        print(f"    {f'{lo:.2f}-{hi:.2f}':16}{len(sel):>8,}{_pct(d,25):>7.2f}%"
              f"{_pct(d,50):>7.2f}%{_pct(d,75):>7.2f}%{conv:>10.0%}")
    if len(med) >= 3:
        mono = all(med[i] >= med[i + 1] - 0.01 for i in range(len(med) - 1))
        print(f"    -> distance falls as concentration rises: "
              f"{'YES' if mono else 'NO'}")
        if not mono:
            print("       ⚠️ NOT MONOTONE. Concentration is not measuring pin")
            print("          strength on this data, and a butterfly gated on it")
            print("          would be gated on noise.")

    print("\n  2. BY TIME OF DAY (concentration >= 0.15, the PINNING threshold)")
    print("     0DTE gamma sharpens toward expiry. If only the afternoon")
    print("     reading works, the butterfly is an AFTERNOON trade.")
    print(f"    {'window':12}{'n':>8}{'p50 dist':>11}{'converged':>11}")
    print("    " + "-" * 42)
    for lo, hi, lbl in (("09:30", "11:00", "morning"),
                        ("11:00", "13:00", "midday"),
                        ("13:00", "14:30", "early pm"),
                        ("14:30", "16:00", "late pm")):
        sel = [o for o in obs if lo <= o["hhmm"] < hi and o["conc"] >= 0.15]
        if len(sel) < 50:
            continue
        d = [o["d_settle"] for o in sel]
        conv = sum(1 for o in sel if o["converged"]) / len(sel)
        print(f"    {lbl:12}{len(sel):>8,}{_pct(d,50):>10.2f}%{conv:>10.0%}")

    print("\n  3. THE CONTROL - low concentration, same windows")
    print("     Without this the numbers above are unreadable: if a LOW-conc")
    print("     pin lands just as close, the pin is not doing the work and")
    print("     price simply ends up near the biggest strike by construction.")
    print(f"    {'window':12}{'n':>8}{'p50 dist':>11}{'converged':>11}")
    print("    " + "-" * 42)
    for lo, hi, lbl in (("09:30", "11:00", "morning"),
                        ("11:00", "13:00", "midday"),
                        ("13:00", "14:30", "early pm"),
                        ("14:30", "16:00", "late pm")):
        sel = [o for o in obs if lo <= o["hhmm"] < hi and o["conc"] < 0.10]
        if len(sel) < 50:
            continue
        d = [o["d_settle"] for o in sel]
        conv = sum(1 for o in sel if o["converged"]) / len(sel)
        print(f"    {lbl:12}{len(sel):>8,}{_pct(d,50):>10.2f}%{conv:>10.0%}")

    print("\n  ⚠️ READ TABLE 3 AGAINST TABLE 2 BEFORE CONCLUDING ANYTHING. A")
    print("     high-concentration pin landing 0.3% from settle means nothing")
    print("     if a low-concentration one lands 0.3% too.")
    print("  ⚠️ AND `converged` IS THE HONEST OUTCOME. Distance alone rewards")
    print("     a pin that happened to sit where price already was; converged")
    print("     asks whether price MOVED TOWARD it.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
