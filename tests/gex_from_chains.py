#!/usr/bin/env python3
"""
tests/gex_from_chains.py  v1.0  (2026-08-25)

REAL GEX FROM THE WAREHOUSE CHAINS — no stub, no proxy.

Input: raw/chain_snapshots/dt=2026-08-25/sym=TSLA/ (74 five-minute snapshots).

⚠️ WHAT IS AND IS NOT REAL HERE
  · `gamma` and `oi` ARE POPULATED — verified: 123/222 contracts carry
    non-zero gamma, 159/222 carry non-zero OI (max 7,326). So dealer gamma
    is computable from this data rather than assumed.
  · ⚠️ `vol` IS ZERO ON ALL 222 CONTRACTS. Anything keyed on contract volume
    is DEAD on this payload and must not be silently substituted.
  · ⚠️ THE DEALER SIGN CONVENTION IS AN ASSUMPTION, NOT A MEASUREMENT.
    Standard practice is dealers long calls / short puts, so
    GEX = gamma*OI*(+1 for calls, -1 for puts). That convention is NOT
    verified against this fleet's own definition and the pin location
    depends on it. Marked ⟨ASSUMPTION⟩ everywhere it matters.

GEX per strike = gamma × OI × 100 × spot² × 0.01, signed by the convention
above. The PIN is the strike where cumulative signed gamma flips — the level
dealer hedging pushes price toward.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import defaultdict

ROOT = os.environ.get("CHAINS", "/home/claude/cc")


def snapshots():
    out = []
    for f in sorted(glob.glob(f"{ROOT}/**/*", recursive=True)):
        if not os.path.isfile(f):
            continue
        d = json.load(open(f))
        r = d.get("record", d)
        r = json.loads(r) if isinstance(r, str) else r
        if r.get("event") == "chain_snapshot":
            out.append(r)
    out.sort(key=lambda r: r["ts_et"])
    return out


def gex_profile(snap):
    """Signed dealer gamma per strike. ⟨ASSUMPTION⟩ long calls / short puts."""
    spot = float(snap["underlying"])
    per = defaultdict(float)
    for c in snap["contracts"]:
        g, oi = float(c.get("gamma") or 0), float(c.get("oi") or 0)
        if g <= 0 or oi <= 0:
            continue
        sign = 1.0 if c["type"] == "C" else -1.0
        per[float(c["strike"])] += sign * g * oi * 100 * spot * spot * 0.01
    return spot, dict(per)


def pin_from(per, spot):
    """The strike where cumulative signed gamma crosses zero — the flip.

    ⚠️ If gamma never changes sign the flip does not exist and this returns
    None rather than the nearest strike. A pin that is really 'no pin' is
    exactly the kind of clean-looking wrong answer this project exists to
    prevent."""
    if not per:
        return None, 0.0
    ks = sorted(per)
    cum, prev = 0.0, None
    for k in ks:
        cum += per[k]
        if prev is not None and (prev < 0 <= cum or prev > 0 >= cum):
            return k, cum
        prev = cum
    return None, cum


if __name__ == "__main__":
    snaps = snapshots()
    print(__doc__)
    print("=" * 74)
    print(f"  TSLA 2026-08-25 · {len(snaps)} chain snapshots · expiry "
          f"{snaps[0]['expiry'] if snaps else '?'}")
    print("=" * 74)
    print(f"\n  {'TIME':>8}  {'SPOT':>8}  {'PIN':>8}  {'NET GEX ($M)':>13}  "
          f"{'|GEX| TOP STRIKE':>16}")
    rows = []
    for s in snaps:
        spot, per = gex_profile(s)
        pin, cum = pin_from(per, spot)
        net = sum(per.values()) / 1e6
        top = max(per, key=lambda k: abs(per[k])) if per else None
        t = s["ts_et"][11:16]
        rows.append((t, spot, pin, net, top))
    for t, spot, pin, net, top in rows[::6]:      # every ~30 min
        print(f"  {t:>8}  {spot:8.2f}  {(f'{pin:.0f}' if pin else '   none'):>8}  "
              f"{net:13.1f}  {(f'{top:.0f}' if top else '-'):>16}")

    print(f"\n{'='*74}\n  WHAT THIS SAYS\n{'='*74}")
    pins = [p for _, _, p, _, _ in rows if p]
    if pins:
        from collections import Counter
        c = Counter(pins)
        print(f"  Pin located in {len(pins)}/{len(rows)} snapshots.")
        print(f"  Most common pin strikes: "
              f"{', '.join(f'{k:.0f} ({v}x)' for k, v in c.most_common(4))}")
    else:
        print("  NO GAMMA FLIP FOUND IN ANY SNAPSHOT — there is no pin on this")
        print("  tape by this definition. A butterfly plan declared here would")
        print("  have no anchor, and that is a REAL answer, not a missing one.")
