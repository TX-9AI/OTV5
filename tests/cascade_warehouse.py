#!/usr/bin/env python3
"""
tests/cascade_warehouse.py  v1.0  (2026-08-25)

THE PLAN CASCADE ON REAL WAREHOUSE DATA.

INPUT (pulled from s3://vertigo-warehouse-tx9ai, TSLA dt=2026-08-25):
  · candles/interval=1m   — 79 objects, the real tape
  · liquidity_ledger/     — 75 five-minute snapshots of the LEVEL BOOK,
                            each carrying per-level touches / holds / breaches
  · trades/               — 37 CDC rows, what the fleet actually did
  · signal_journal/       — 2,580 events
  ⚠️ chains/              — ZERO OBJECTS FOR THIS SYMBOL/DATE. So there is no
                            gamma, no vega, no GEX, no charm, no vanna. Every
                            validator needing them reports UNAVAILABLE and is
                            NOT silently skipped.

⚠️ STILL NOT A BACKTEST. No option prices for this date, so nothing here
computes credit, debit or P&L. "TRIG" means PRICE REACHED THE TRIGGER.

🔑 WHAT IS NEW HERE, AND IT IS THE POINT: the validators are no longer numbers
I invented. `hold_rate` comes from the level book the fleet itself wrote.
"""
from __future__ import annotations

import json
import glob
import os
import sys
from dataclasses import dataclass
from statistics import mean
from typing import Optional, List, Dict

ROOT = os.environ.get("TAPE", "/home/claude/ct/cascade_tape")

TCS_START_ET   = (11, 31)
TCS_END_ET     = (14, 0)
CONDOR_START   = (11, 11)
BFLY_START     = (12, 0)
DEBIT_CUTOFF   = (11, 30)
ALIVE, GONE    = "ALIVE", "GONE"


def _rec(path):
    d = json.load(open(path))
    r = d.get("record", d)
    return json.loads(r) if isinstance(r, str) else r


# ── the tape ──────────────────────────────────────────────────────────
def load_candles() -> List[dict]:
    rows = []
    for f in glob.glob(f"{ROOT}/candles/interval=1m/*"):
        r = _rec(f)
        rows.extend(r if isinstance(r, list) else [r])
    out = {}
    for b in rows:                      # dedupe on epoch
        out[b["ts_epoch_ms"]] = b
    return [out[k] for k in sorted(out)]


# ── the level book, as it evolved ─────────────────────────────────────
def load_levels() -> List[tuple]:
    snaps = []
    for f in glob.glob(f"{ROOT}/liquidity_ledger/*"):
        r = _rec(f)
        snaps.append((r["last_bar_ts"], r["levels"]))
    snaps.sort()
    return snaps


def levels_at(snaps, hhmm) -> List[dict]:
    """The level book AS IT STOOD at hhmm — never the end-of-day version.
    ⚠️ Using the final book would be lookahead: a level's touch count at
    15:58 is not what was knowable at 11:31."""
    want = f"{hhmm[0]:02d}:{hhmm[1]:02d}"
    best = snaps[0][1]
    for ts, lv in snaps:
        if ts[11:16] <= want:
            best = lv
        else:
            break
    return best


def hold_rate(levels, price, tol=0.004) -> Optional[tuple]:
    """(hold_rate, touches, name) for the level nearest `price`, or None."""
    cand = [L for L in levels
            if L["touches"] > 0 and abs(L["price"] - price) / max(price, 1) < tol]
    if not cand:
        return None
    L = min(cand, key=lambda x: abs(x["price"] - price))
    t = L["touches"]
    return (L["holds"] / t if t else 0.0, t, L["name"])


@dataclass
class Plan:
    name: str
    trigger: float
    invalidation: float
    direction: str
    window: tuple
    instrument: str
    arm_reason: str
    v_hold_min: Optional[float] = None     # REAL validator, from the ledger
    v_needs: tuple = ()
    state: str = ALIVE
    gone_why: str = ""
    gone_at = None
    fired_at = None


def hm(ms) -> tuple:
    import datetime as dt
    t = dt.datetime.utcfromtimestamp(ms / 1000) - dt.timedelta(hours=4)  # ET
    return (t.hour, t.minute)


def run():
    bars = load_candles()
    snaps = load_levels()
    if not bars:
        print("no candles"); return
    orb = [b for b in bars if (9, 30) <= hm(b["ts_epoch_ms"]) < (9, 35)]
    if not orb:
        print("no ORB window in tape"); return
    orb_hi = max(b["high"] for b in orb)
    orb_lo = min(b["low"] for b in orb)

    print(__doc__)
    print("=" * 74)
    print(f"  TSLA 2026-08-25 · {len(bars)} 1m bars · {len(snaps)} level snapshots")
    print(f"  ORB {orb_lo:.2f} – {orb_hi:.2f}")
    print("=" * 74)

    # the level book at declaration time — NOT the end-of-day book
    lv = levels_at(snaps, TCS_START_ET)
    print(f"\n  LEVEL BOOK AS IT STOOD AT 11:31 (what was knowable then):")
    for L in sorted(lv, key=lambda x: -x["touches"])[:6]:
        r = f"{L['holds']/L['touches']*100:5.1f}%" if L["touches"] else "  n/a"
        print(f"    {L['price']:8.2f} {L['name'][:20]:20} "
              f"t={L['touches']:4} h={L['holds']:4} b={L['breaches']:4}  hold {r}")

    hr = hold_rate(lv, orb_hi)
    print(f"\n  The ORB high {orb_hi:.2f} sits on: "
          f"{hr[2] if hr else '(no tracked level within 0.4%)'}"
          + (f" — hold rate {hr[0]*100:.1f}% on {hr[1]} touches" if hr else ""))

    plans = [
        Plan("TrendParticipation", orb_hi, orb_hi, "up",
             (TCS_START_ET, TCS_END_ET), f"PCS {round(orb_hi)}/{round(orb_hi)-5}",
             "credit floor under a bull move",
             v_hold_min=0.75),                      # ⟨PRIOR⟩ but on REAL data
        Plan("IronCondor", orb_hi, orb_hi + 2.0, "up",
             (CONDOR_START, TCS_END_ET), "condor legs", "ranging"),
        Plan("GEXPinButterfly", 0.0, 0.0, "down", (BFLY_START, TCS_END_ET),
             "fly [NO PIN]", "⚠️ chains absent for this date",
             v_needs=("gex", "charm", "vanna")),
    ]

    print(f"\n{'='*74}\n  CASCADE\n{'='*74}")
    for p in plans:
        if p.v_needs:
            p.state, p.gone_why = GONE, f"UNAVAILABLE: needs {', '.join(p.v_needs)}"
            print(f"   --:--  ✗  {p.name:<22} OUT   {p.gone_why}")

    for b in bars:
        t = hm(b["ts_epoch_ms"])
        cur = levels_at(snaps, t)
        for p in plans:
            if p.state == GONE:
                continue
            if t < p.window[0]:
                continue
            if t >= p.window[1]:
                p.state, p.gone_why, p.gone_at = GONE, "window closed", t
                print(f"   {t[0]:02d}:{t[1]:02d}  ✗  {p.name:<22} OUT   window closed")
                continue
            if p.v_hold_min is not None:
                h = hold_rate(cur, p.trigger)
                if h and h[0] < p.v_hold_min:
                    p.state, p.gone_why, p.gone_at = GONE, (
                        f"validator: {h[2]} hold rate {h[0]*100:.1f}% "
                        f"< {p.v_hold_min*100:.0f}% ({h[1]} touches)"), t
                    print(f"   {t[0]:02d}:{t[1]:02d}  ✗  {p.name:<22} OUT   {p.gone_why}")
                    continue
            if p.fired_at is None and b["close"] > p.trigger:
                p.fired_at = t
                print(f"   {t[0]:02d}:{t[1]:02d}  🔥 {p.name:<22} TRIG  {p.instrument}")
            elif p.fired_at and b["close"] < p.invalidation:
                p.state, p.gone_why, p.gone_at = GONE, (
                    f"close {b['close']:.2f} < invalidation {p.invalidation:.2f}"), t
                print(f"   {t[0]:02d}:{t[1]:02d}  ✗  {p.name:<22} OUT   {p.gone_why}")

    print(f"\n   STANDING AT CLOSE: "
          f"{', '.join(p.name for p in plans if p.state == ALIVE) or '(nothing)'}")

    # what the fleet ACTUALLY did, from the trade records
    tr = {}
    for f in glob.glob(f"{ROOT}/trades/*"):
        r = _rec(f)
        tr[r.get("trade_id")] = r
    print(f"\n{'='*74}\n  WHAT THE FLEET ACTUALLY DID (from raw/trades)\n{'='*74}")
    for t in sorted(tr.values(), key=lambda x: str(x.get("entry_time"))):
        if str(t.get("status")) != "closed":
            continue
        print(f"   {str(t.get('entry_time'))[11:16]}  {str(t.get('strategy'))[:20]:20} "
              f"{str(t.get('setup_type'))[:22]:22} pnl={t.get('pnl_usd')}")


if __name__ == "__main__":
    run()
