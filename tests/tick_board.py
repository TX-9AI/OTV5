#!/usr/bin/env python3
"""
tests/tick_board.py  v1.0  (2026-08-25)

THE SIGHT PICTURE — every plan, as it stands AT THIS TICK.

Operator, 2026-08-25: *"the question wasn't 'what does x plan look like from
11:31?' It's 'what does each plan look like RIGHT NOW at this tick?'"*

So this is not a ladder of separate declarations. It is ONE BOARD, rendered at
a single instant, showing every standing plan side by side.

════════════════════════════════════════════════════════════════════════════
WHAT IS FROZEN AND WHAT IS LIVE — the whole discipline in one table
════════════════════════════════════════════════════════════════════════════
  FROZEN AT DECLARATION          LIVE AT THIS TICK
  ─────────────────────          ─────────────────
  trigger price                  mark of the named contracts
  invalidation price             credit / debit available now
  the contracts, by strike       R offered now
  the reason it was declared     distance to trigger
                                 validator readings

⚠️ RE-PRICING A NAMED CONTRACT IS NOT THE CIRCULAR LOOP. The loop was a SCORE
recomputed from data containing the move, then used to FIRE. Here the trigger
never moves; only the cost of a fixed instrument changes, which is a fact about
the market, not a signal derived from it. A plan may DIE on R going bad. It may
never FIRE on R going good — firing is price crossing the frozen trigger.

⚠️ REAL DATA, SOURCES NAMED: raw/candles/interval=1m (390 bars) ·
raw/chain_snapshots (74 snapshots, gamma+OI populated, vol ZERO) ·
raw/liquidity_ledger (75 snapshots, read AS OF the tick, never end-of-day).
⚠️ NOT REAL: no fills. Marks only, so R is what the setup OFFERS, not what a
fill would produce.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import defaultdict

TAPE = "/home/claude/ct/cascade_tape"
CH   = "/home/claude/cc"
R_FLOOR = 1.00


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


CHAINS = None
def chain_at(hhmm):
    global CHAINS
    if CHAINS is None:
        CHAINS = [r for r in _recs("**/*", CH) if r.get("event") == "chain_snapshot"]
        CHAINS.sort(key=lambda r: r["ts_et"])
    best = CHAINS[0]
    for s in CHAINS:
        if s["ts_et"][11:16] <= hhmm:
            best = s
        else:
            break
    return best


LV = None
def levels_at(hhmm):
    global LV
    if LV is None:
        LV = sorted((r["last_bar_ts"], r["levels"])
                    for r in _recs("liquidity_ledger/*", TAPE))
    best = LV[0][1]
    for ts, lv in LV:
        if ts[11:16] <= hhmm:
            best = lv
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

def board(hhmm, bars, orb_hi, orb_lo):
    by_t = {et(b["ts_epoch_ms"]): b for b in bars}
    if hhmm not in by_t:
        return
    spot = by_t[hhmm]["close"]
    ch = chain_at(hhmm)
    lv = levels_at(hhmm)

    print(f"\n╔{'═'*76}╗")
    print(f"║  TICK {hhmm} ET · TSLA {spot:8.2f}"
          f"{'':>20}chain {ch['ts_et'][11:19]}  {'':>7}║")
    print(f"╠{'═'*76}╣")
    print(f"║ {'PLAN':<20}{'STATE':<9}{'TRIGGER':>9}{'DIST':>7}"
          f"{'MARK':>7}{'R NOW':>7}{'VERDICT':>16} ║")
    print(f"╟{'─'*76}╢")

    rows = []

    # ── TREND PARTICIPATION ────────────────────────────────────────────
    pk = sorted({float(c["strike"]) for c in ch["contracts"] if c["type"] == "P"})
    inside = [k for k in pk if orb_lo <= k <= orb_hi]
    sk = inside[-1] if inside else max(k for k in pk if k <= orb_hi)
    sp, lp = con(ch, "P", sk), con(ch, "P", sk - 5)
    if sp and lp:
        credit = round(float(sp["bid"]) - float(lp["ask"]), 2)
        risk = round(5.0 - credit, 2)
        r = round(credit / risk, 2) if risk > 0 else 0.0
        state = "ARMED" if spot <= orb_hi else "LIVE"
        v = "TAKE" if r >= R_FLOOR else f"DECLINE r{r:.2f}"
        rows.append(("TrendParticip PCS", state, orb_hi, spot - orb_hi,
                     credit, r, v,
                     f"PCS {sk:.0f}/{sk-5:.0f} · target {sk:.0f} · stop {orb_hi:.2f}"))

    # ── GEX PIN BUTTERFLY ──────────────────────────────────────────────
    pin = pin_of(ch)
    if pin:
        b_, w1, w2 = con(ch, "C", pin), con(ch, "C", pin-5), con(ch, "C", pin+5)
        if b_ and w1 and w2:
            debit = round(float(w1["ask"]) - 2*float(b_["bid"]) + float(w2["ask"]), 2)
            r = round((5.0 - debit) / debit, 2) if debit > 0 else 0.0
            trig = pin - 5.0
            state = "LIVE" if spot >= trig else "ARMED"
            v = "TAKE" if r >= R_FLOOR else f"DECLINE r{r:.2f}"
            rows.append(("GEXPinButterfly", state, trig, spot - trig,
                         debit, r, v,
                         f"fly {pin-5:.0f}/{pin:.0f}/{pin+5:.0f} · "
                         f"target {pin:.0f} · stop = debit"))

    # ── IRON CONDOR (call side shown) ──────────────────────────────────
    hi_lv = [L for L in lv if L["touches"] > 0 and L["price"] > spot]
    if hi_lv:
        L = min(hi_lv, key=lambda x: x["price"])
        ck = min((k for k in sorted({float(c["strike"]) for c in ch["contracts"]
                                     if c["type"] == "C"}) if k >= L["price"]),
                 default=None)
        if ck:
            sc, lc = con(ch, "C", ck), con(ch, "C", ck + 5)
            if sc and lc:
                credit = round(float(sc["bid"]) - float(lc["ask"]), 2)
                risk = round(5.0 - credit, 2)
                r = round(credit / risk, 2) if risk > 0 else 0.0
                hold = L["holds"] / L["touches"]
                v = "TAKE" if r >= R_FLOOR else f"DECLINE r{r:.2f}"
                rows.append(("IronCondor CCS", "ARMED", L["price"],
                             spot - L["price"], credit, r, v,
                             f"CCS {ck:.0f}/{ck+5:.0f} · {L['name'][:14]} "
                             f"hold {hold*100:.0f}% ({L['touches']}t)"))

    for name, state, trig, dist, mark, r, v, detail in rows:
        print(f"║ {name:<20}{state:<9}{trig:>9.2f}{dist:>+7.2f}"
              f"{mark:>7.2f}{r:>7.2f}{v:>16} ║")
        print(f"║   └ {detail:<70} ║")
    print(f"╚{'═'*76}╝")


if __name__ == "__main__":
    bars = tape()
    orb = [b for b in bars if "09:30" <= et(b["ts_epoch_ms"]) < "09:35"]
    hi, lo = max(b["high"] for b in orb), min(b["low"] for b in orb)
    print(__doc__)
    print(f"  TSLA 2026-08-25 · ORB {lo:.2f}–{hi:.2f} · R floor {R_FLOOR:.2f}")
    ticks = sys.argv[1:] or ["11:35", "12:00", "13:00", "13:45"]
    for t in ticks:
        board(t, bars, hi, lo)
    print("\n  Each board above is ONE INSTANT. Triggers are frozen; marks, R and")
    print("  distance are what that tick actually offered.\n")
