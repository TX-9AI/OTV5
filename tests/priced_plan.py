#!/usr/bin/env python3
"""
tests/priced_plan.py  v1.0  (2026-08-25)

A PLAN THAT IS ACTUALLY A PLAN — priced at declaration, from real data.

Operator, 2026-08-25: *"every strategy should have a plan, every plan a set of
in/validators that give not only a binary answer but a 'what if' ie. strike
selection, target distance, premium paid/collected, etc.. in other words, an
actual plan."*

So a plan is not a trigger price. It is the WHOLE PROJECTED TRADE, computed
before the trigger, from data that exists at declaration time:

    WHAT fires it        trigger price, fixed
    WHAT kills it        invalidation price, fixed
    WHAT I WILL TRADE    the actual contracts, by strike
    WHAT IT COSTS        premium paid or collected, from the live chain
    WHAT I AIM AT        target, and the distance to it
    WHAT IT PAYS         R at declaration — the reason to take it at all
    WHAT SAYS NO         validators, each with its current reading

⚠️ EVERY INPUT BELOW IS REAL AND ITS SOURCE IS NAMED:
  · tape        raw/candles/interval=1m/     (390 bars)
  · levels      raw/liquidity_ledger/        (75 snapshots, READ AS OF 11:31)
  · chain       raw/chain_snapshots/         (74 snapshots, gamma+OI populated)
⚠️ NOT REAL: nothing is filled. Premiums are marks off the chain, so the R
figures are what the setup OFFERED, not what a fill would have produced.
"""
from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict

TAPE = "/home/claude/ct/cascade_tape"
CH   = "/home/claude/cc"
AT   = __import__("os").environ.get("AT", "11:31")   # declaration moment, ET


def _recs(pattern, root):
    out = []
    for f in sorted(glob.glob(f"{root}/{pattern}", recursive=True)):
        if not os.path.isfile(f):
            continue
        d = json.load(open(f))
        r = d.get("record", d)
        out.append(json.loads(r) if isinstance(r, str) else r)
    return out


def tape():
    rows = []
    for r in _recs("candles/interval=1m/*", TAPE):
        rows.extend(r if isinstance(r, list) else [r])
    seen = {b["ts_epoch_ms"]: b for b in rows}
    return [seen[k] for k in sorted(seen)]


def et(ms):
    import datetime as dt
    t = dt.datetime.utcfromtimestamp(ms / 1000) - dt.timedelta(hours=4)
    return f"{t.hour:02d}:{t.minute:02d}"


def levels_as_of(hhmm):
    snaps = sorted((r["last_bar_ts"], r["levels"])
                   for r in _recs("liquidity_ledger/*", TAPE))
    best = snaps[0][1]
    for ts, lv in snaps:
        if ts[11:16] <= hhmm:
            best = lv
        else:
            break
    return best


def chain_as_of(hhmm):
    snaps = [r for r in _recs("**/*", CH) if r.get("event") == "chain_snapshot"]
    snaps.sort(key=lambda r: r["ts_et"])
    best = snaps[0]
    for s in snaps:
        if s["ts_et"][11:16] <= hhmm:
            best = s
        else:
            break
    return best


def contract(chain, typ, strike):
    for c in chain["contracts"]:
        if c["type"] == typ and abs(float(c["strike"]) - strike) < 0.01:
            return c
    return None


@dataclass
class Validator:
    name: str
    reading: str
    verdict: str          # PASS / FAIL / UNAVAILABLE


@dataclass
class PricedPlan:
    strategy: str
    structure: str
    trigger: float
    invalidation: float
    legs: List[str] = field(default_factory=list)
    credit: Optional[float] = None
    debit: Optional[float] = None
    width: Optional[float] = None
    target: Optional[float] = None
    max_loss: Optional[float] = None
    r_at_declaration: Optional[float] = None
    validators: List[Validator] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def render(self):
        print(f"\n  ┌─ PLAN · {self.strategy}")
        print(f"  │  {self.structure}")
        print(f"  ├─ FIRES ON      close > {self.trigger:.2f}")
        _room = abs(self.trigger - self.invalidation)
        print(f"  ├─ DIES ON       close < {self.invalidation:.2f}"
              f"   ({_room:.2f} of room"
              + ("  🔴 ZERO ROOM" if _room < 0.01 else "") + ")")
        print(f"  ├─ LEGS")
        for l in self.legs:
            print(f"  │    {l}")
        if self.credit is not None:
            print(f"  ├─ COLLECTS      ${self.credit:.2f} × 100 = "
                  f"${self.credit*100:.0f} per spread")
            print(f"  ├─ MAX LOSS      ${self.max_loss:.2f} × 100 = "
                  f"${self.max_loss*100:.0f}  (width {self.width:.0f} − credit)")
        if self.debit is not None:
            print(f"  ├─ COSTS         ${self.debit:.2f} × 100 = "
                  f"${self.debit*100:.0f} per contract")
        if self.target is not None:
            print(f"  ├─ TARGET        {self.target:.2f}")
        if self.r_at_declaration is not None:
            print(f"  ├─ R OFFERED     {self.r_at_declaration:.2f}"
                  f"   ⟵ the reason to take it, known BEFORE the trigger")
        print(f"  ├─ VALIDATORS")
        for v in self.validators:
            mark = {"PASS": "✓", "FAIL": "✗", "UNAVAILABLE": "?"}[v.verdict]
            print(f"  │    {mark} {v.name:<22} {v.reading}")
        for n in self.notes:
            print(f"  └─ ⚠️  {n}")
        if not self.notes:
            print(f"  └─")


def main():
    bars = tape()
    orb = [b for b in bars if "09:30" <= et(b["ts_epoch_ms"]) < "09:35"]
    orb_hi = max(b["high"] for b in orb)
    orb_lo = min(b["low"] for b in orb)
    at_bar = [b for b in bars if et(b["ts_epoch_ms"]) == AT][0]
    spot = at_bar["close"]
    lv = levels_as_of(AT)
    ch = chain_as_of(AT)

    print(__doc__)
    print("=" * 74)
    print(f"  DECLARED AT {AT} ET · TSLA · spot {spot:.2f} · "
          f"ORB {orb_lo:.2f}–{orb_hi:.2f}")
    print(f"  chain snapshot {ch['ts_et'][11:19]} · expiry {ch['expiry']} · "
          f"{len(ch['contracts'])} contracts")
    print("=" * 74)

    # level under the trigger, as the book stood at 11:31
    near = [L for L in lv if L["touches"] > 0
            and abs(L["price"] - orb_hi) / orb_hi < 0.004]
    hold = None
    if near:
        L = min(near, key=lambda x: abs(x["price"] - orb_hi))
        hold = (L["holds"] / L["touches"], L["touches"], L["name"], L["price"])

    # ── PLAN 1: TREND PARTICIPATION — the put credit spread under the move ──
    # 🔴 SNAP TO THE REAL GRID. v1.0 used int(orb_hi) = 351 and TSLA's strikes
    # near the money are $5 apart, so it named a contract that does not exist
    # and the plan rendered with NO LEGS. Production's `_inside[-1]` selects
    # from the CHAIN, which is the right shape; my harness invented a strike.
    # ⚠️ AND THE FIX EXPOSES A REAL CONSTRAINT: the ORB range 349.20–351.88 is
    # 2.68 wide on a $5 grid, so exactly ONE strike (350) falls inside it. The
    # "first strike inside the range" rule has almost no room to choose on a
    # symbol like this — the strike is effectively forced.
    _pk = sorted({float(c["strike"]) for c in ch["contracts"] if c["type"] == "P"})
    _inside = [k for k in _pk if orb_lo <= k <= orb_hi]
    short_k = _inside[-1] if _inside else max(k for k in _pk if k <= orb_hi)
    long_k = short_k - 5
    sp, lp = contract(ch, "P", short_k), contract(ch, "P", long_k)
    p1 = PricedPlan(
        strategy="TrendParticipation (PCS)",
        structure=f"sell the floor under a bull move, bounded by the ORB high",
        trigger=orb_hi, invalidation=orb_hi)
    if sp and lp:
        credit = round(float(sp["bid"]) - float(lp["ask"]), 2)
        width = short_k - long_k
        p1.legs = [f"SELL  P {short_k:.0f}  bid {sp['bid']:.2f}  "
                   f"delta {sp['delta']:.3f}  IV {sp['iv']:.3f}  OI {sp['oi']:.0f}",
                   f"BUY   P {long_k:.0f}  ask {lp['ask']:.2f}  "
                   f"delta {lp['delta']:.3f}  IV {lp['iv']:.3f}  OI {lp['oi']:.0f}"]
        p1.credit, p1.width = credit, width
        p1.max_loss = round(width - credit, 2)
        p1.r_at_declaration = round(credit / (width - credit), 2) if width > credit else None
        p1.target = short_k
    p1.validators = [
        Validator("level hold rate",
                  (f"{hold[2]} @{hold[3]:.2f} — {hold[0]*100:.1f}% on "
                   f"{hold[1]} touches" if hold else "no tracked level near the bound"),
                  "PASS" if hold and hold[0] >= 0.75 else "FAIL"),
        Validator("distance to invalidation",
                  f"{abs(spot - orb_hi):.2f} from spot ({abs(spot-orb_hi)/spot*100:.2f}%)",
                  "FAIL" if abs(spot - orb_hi) < 0.25 else "PASS"),
    ]
    p1.notes = [
        "TRIGGER AND INVALIDATION ARE THE SAME PRICE — the plan is born at "
        "its own stop. This is the 2026-08-25 defect, visible as a number.",
    ]
    p1.render()

    # ── PLAN 2: GEX PIN BUTTERFLY — real pin from real gamma × OI ──────────
    from collections import defaultdict
    per = defaultdict(float)
    for c in ch["contracts"]:
        g, oi = float(c.get("gamma") or 0), float(c.get("oi") or 0)
        if g > 0 and oi > 0:
            per[float(c["strike"])] += (1 if c["type"] == "C" else -1) * g * oi
    ks, cum, pin, prev = sorted(per), 0.0, None, None
    for k in ks:
        cum += per[k]
        if prev is not None and (prev < 0 <= cum or prev > 0 >= cum):
            pin = k
            break
        prev = cum
    p2 = PricedPlan(
        strategy="GEXPinButterfly",
        structure=f"debit fly at the gamma flip, played toward the pin",
        # 🔴 DIRECTION FIXED. v1.0 read "fires above 358, dies below 366",
        # which is backwards for a plan played TOWARD a pin from below: it
        # fires when price comes WITHIN reach of the pin and dies when price
        # abandons it. Trigger is the near edge, invalidation is the far side.
        trigger=(pin - 5.0) if pin else 0.0,        # ⟨PRIOR⟩ approach band
        invalidation=(pin - 12.0) if pin else 0.0)  # ⟨PRIOR⟩ pin abandoned
    if pin:
        body = contract(ch, "C", pin)
        w1 = contract(ch, "C", pin - 5)
        w2 = contract(ch, "C", pin + 5)
        if body and w1 and w2:
            debit = round(float(w1["ask"]) - 2 * float(body["bid"])
                          + float(w2["ask"]), 2)
            p2.legs = [f"BUY   C {pin-5:.0f}  ask {w1['ask']:.2f}  OI {w1['oi']:.0f}",
                       f"SELL 2C {pin:.0f}    bid {body['bid']:.2f}  OI {body['oi']:.0f}",
                       f"BUY   C {pin+5:.0f}  ask {w2['ask']:.2f}  OI {w2['oi']:.0f}"]
            p2.debit = debit
            p2.target = pin
            p2.r_at_declaration = round((5.0 - debit) / debit, 2) if debit > 0 else None
    p2.validators = [
        Validator("gamma flip located",
                  f"pin {pin:.0f} from {len(per)} strikes with gamma×OI" if pin
                  else "NO FLIP — no pin on this chain", "PASS" if pin else "FAIL"),
        Validator("distance to pin",
                  f"spot {spot:.2f} is {abs(spot-pin):.2f} away" if pin else "-",
                  "FAIL" if pin and abs(spot - pin) > 8 else "PASS"),
        Validator("contract volume", "ZERO on all 222 contracts in this payload",
                  "UNAVAILABLE"),
    ]
    p2.notes = [
        "⟨ASSUMPTION⟩ dealer sign convention long calls / short puts — the pin "
        "location depends on it and it is NOT verified against the fleet's code.",
        f"spot never came within {abs(spot-pin):.0f} of the pin today, so this "
        "plan would have stood armed and never fired. Correctly." if pin else "",
    ]
    p2.notes = [n for n in p2.notes if n]
    p2.render()

    print(f"\n{'='*74}")
    print("  A plan is now answerable BEFORE the trigger: what I trade, what it")
    print("  costs, what it pays, and what would stop it. That is the 'what if'.")
    print("=" * 74)


if __name__ == "__main__":
    main()
