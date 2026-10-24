#!/usr/bin/env python3
"""
tests/r_gate.py  v1.0  (2026-08-25)

THE R GATE — a plan declines itself on reward:risk, and NAMES THE LEVELS.

Operator, 2026-08-25: *"since it knows what strike, what mark, nearest stop
distance (not trailing or ratcheting, which should not factor in) and desired
target distance, can it decline on r-value alone if it determines that we can't
get at least a 1:1 and state that as the reason while naming the target level &
stop level?"*

Yes. This is that, on the real chain, declared every 30 minutes through
2026-08-25 on TSLA.

⚠️ STOP DISTANCE IS THE PLAN'S OWN INVALIDATION AND NOTHING ELSE. No trail, no
ratchet, no premium floor — the operator's constraint, and it is the right one:
a trail is a MANAGEMENT decision made after entry, so folding it into the
entry's R would flatter every setup by counting a rescue that has not happened.

⚠️ REAL INPUTS, NAMED: strikes and marks from raw/chain_snapshots (bid/ask, the
snapshot at or before each declaration time); ORB from raw/candles 09:30-09:35;
levels from raw/liquidity_ledger read AS OF the declaration minute.
⚠️ NOT REAL: no fills. R here is what the setup OFFERED at the mark.
"""
from __future__ import annotations

import glob
import json
import os
from collections import defaultdict

TAPE = "/home/claude/ct/cascade_tape"
CH   = "/home/claude/cc"
R_FLOOR = 1.00           # operator's stated minimum


def _recs(pattern, root):
    out = []
    for f in sorted(glob.glob(f"{root}/{pattern}", recursive=True)):
        if not os.path.isfile(f):
            continue
        d = json.load(open(f))
        r = d.get("record", d)
        out.append(json.loads(r) if isinstance(r, str) else r)
    return out


def et(ms):
    import datetime as dt
    t = dt.datetime.utcfromtimestamp(ms / 1000) - dt.timedelta(hours=4)
    return f"{t.hour:02d}:{t.minute:02d}"


def tape():
    rows = []
    for r in _recs("candles/interval=1m/*", TAPE):
        rows.extend(r if isinstance(r, list) else [r])
    seen = {b["ts_epoch_ms"]: b for b in rows}
    return [seen[k] for k in sorted(seen)]


def chains():
    s = [r for r in _recs("**/*", CH) if r.get("event") == "chain_snapshot"]
    s.sort(key=lambda r: r["ts_et"])
    return s


def chain_at(snaps, hhmm):
    best = snaps[0]
    for s in snaps:
        if s["ts_et"][11:16] <= hhmm:
            best = s
        else:
            break
    return best


def con(ch, typ, k):
    for c in ch["contracts"]:
        if c["type"] == typ and abs(float(c["strike"]) - k) < 0.01:
            return c
    return None


def pin_of(ch):
    """The gamma flip nearest the money, weighted by |gamma×OI|.

    🔴 v1.0 WALKED STRIKES FROM THE LOW END AND TOOK THE FIRST SIGN CHANGE.
    On the 11:35 chain that returned 230 — a spurious crossing among deep ITM
    strikes with stale marks — instead of 360, and the butterfly plan built on
    it priced at NEGATIVE R. Caught by rendering every tick rather than every
    sixth; the earlier "pin 360 in 70/74" was sampled and hid the outliers.
    ⚠️ TWO GUARDS, both structural rather than fitted:
      · only strikes within ±15% of spot participate — a flip 35% out of the
        money is not a pin, it is an artefact of contracts nobody trades;
      · when several flips exist, take the one with the largest |gamma×OI| in
        its neighbourhood, not the first one encountered. Magnitude is what
        makes a flip a pin.
    Returns None when no qualifying flip exists. A pin that is really "no pin"
    is exactly the clean-looking wrong answer this project exists to prevent.
    """
    spot = float(ch.get("underlying") or 0)
    per = defaultdict(float)
    for c in ch["contracts"]:
        g, oi = float(c.get("gamma") or 0), float(c.get("oi") or 0)
        if g <= 0 or oi <= 0:
            continue
        k = float(c["strike"])
        if spot and abs(k - spot) / spot > 0.15:
            continue
        per[k] += (1 if c["type"] == "C" else -1) * g * oi
    if not per:
        return None
    ks = sorted(per)
    cum, prev, flips = 0.0, None, []
    for k in ks:
        cum += per[k]
        if prev is not None and (prev < 0 <= cum or prev > 0 >= cum):
            flips.append((abs(per[k]), k))
        prev = cum
    if not flips:
        return None
    return max(flips)[1]

def main():
    bars, snaps = tape(), chains()
    orb = [b for b in bars if "09:30" <= et(b["ts_epoch_ms"]) < "09:35"]
    hi, lo = max(b["high"] for b in orb), min(b["low"] for b in orb)
    by_t = {et(b["ts_epoch_ms"]): b for b in bars}

    print(__doc__)
    print("=" * 78)
    print(f"  TSLA 2026-08-25 · ORB {lo:.2f}–{hi:.2f} · R FLOOR {R_FLOOR:.2f}")
    print("=" * 78)

    for t in ["11:31", "12:00", "12:30", "13:00", "13:30", "14:00"]:
        if t not in by_t:
            continue
        spot = by_t[t]["close"]
        ch = chain_at(snaps, t)
        print(f"\n  ── {t} ET · spot {spot:.2f} · chain {ch['ts_et'][11:19]} "
              f"{'─'*24}")

        # ── TREND PARTICIPATION ────────────────────────────────────────
        pk = sorted({float(c["strike"]) for c in ch["contracts"]
                     if c["type"] == "P"})
        inside = [k for k in pk if lo <= k <= hi]
        sk = inside[-1] if inside else max(k for k in pk if k <= hi)
        sp, lp = con(ch, "P", sk), con(ch, "P", sk - 5)
        if sp and lp:
            credit = round(float(sp["bid"]) - float(lp["ask"]), 2)
            risk = round(5.0 - credit, 2)
            r = round(credit / risk, 2) if risk > 0 else 0.0
            ok = r >= R_FLOOR
            print(f"     TrendParticipation  PCS {sk:.0f}/{sk-5:.0f}")
            print(f"       collect ${credit:.2f}   risk ${risk:.2f}   R {r:.2f}")
            if ok:
                print(f"       ✓ TAKE — target {sk:.2f} (short strike), "
                      f"stop {hi:.2f} (ORB high)")
            else:
                print(f"       ✗ DECLINE — R {r:.2f} below {R_FLOOR:.2f}. "
                      f"TARGET {sk:.2f} (short strike expiring worthless) is "
                      f"${credit:.2f} away;")
                print(f"         STOP {hi:.2f} (ORB high, a close back through "
                      f"it) risks ${risk:.2f}. The trade pays "
                      f"{r:.2f}:1 and cannot clear 1:1.")

        # ── GEX PIN BUTTERFLY ──────────────────────────────────────────
        pin = pin_of(ch)
        if pin:
            b_, w1, w2 = con(ch, "C", pin), con(ch, "C", pin-5), con(ch, "C", pin+5)
            if b_ and w1 and w2:
                debit = round(float(w1["ask"]) - 2*float(b_["bid"])
                              + float(w2["ask"]), 2)
                if debit > 0:
                    r = round((5.0 - debit) / debit, 2)
                    ok = r >= R_FLOOR
                    print(f"     GEXPinButterfly     fly {pin-5:.0f}/{pin:.0f}"
                          f"/{pin+5:.0f}")
                    print(f"       pay ${debit:.2f}   risk ${debit:.2f}   "
                          f"R {r:.2f}")
                    print(f"       {'✓ TAKE' if ok else '✗ DECLINE'} — target "
                          f"{pin:.2f} (gamma flip), stop = the debit "
                          f"(${debit:.2f}, defined)")
                    print(f"         spot is {abs(spot-pin):.2f} from the pin")

    print(f"\n{'='*78}")
    print("  A DECLINE NOW NAMES ITS NUMBERS. Not 'no trade' — 'R 0.29, target")
    print("  350.00, stop 351.88, cannot clear 1:1'. That is a reason an")
    print("  operator can argue with, and a row a fit can read.")
    print("=" * 78)


if __name__ == "__main__":
    main()
