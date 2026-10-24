#!/usr/bin/env python3
"""
tests/butterfly_plan.py  v1.0  (2026-08-25)

THE GEX PIN BUTTERFLY PLAN — TWO GATES, AND THE OPERATOR NAMED THEM.

Operator, 2026-08-25: *"The best gate in the butterfly trade is #1 'how strong
is the pull (charm)' and #2 'can we reach the pin from here'? That is really
all that needs to be answered, unless I'm missing something?"*

He is not missing much. This file implements exactly those two, plus one
addition argued for below, and NOTHING ELSE. Width, wing liquidity and R fall
out of the structure rather than earning their own gates.

════════════════════════════════════════════════════════════════════════════
GATE 1 — HOW STRONG IS THE PULL  →  GAMMA CONCENTRATION, NOT CHARM
════════════════════════════════════════════════════════════════════════════
🔴 **v2.0 CHANGES THE INSTRUMENT, AND IT WAS MEASURED, NOT ARGUED.**
Operator asked directly: *"Would we rather use something other than charm for
pin strength?"* Yes — and TSLA 2026-08-25 shows why in one table:

    conc = |gamma×OI| at the pin / mean |gamma×OI| of the 8 nearest strikes

    10:00  6.04   pin holds 26.9% of all near-money gamma
    11:30  6.11              29.9%
    13:00  5.94              31.7%
    15:30  6.90              30.4%

**Concentration ran 5.94–6.90 on EVERY snapshot and rose monotonically into
the close. Charm flipped SIGN on three of six readings over the same tape.**

WHY CONCENTRATION IS THE BETTER INSTRUMENT, mechanically rather than
statistically:
  · **It is a LEVEL, not a RATE.** One snapshot, no derivative, so there is no
    two-sample problem and nothing to confound. Charm needs Δdelta over Δt and
    delta also moves with SPOT, which is gamma — that is the confound that
    produced the sign flips.
  · **It is closer to the mechanism.** Dealers long gamma at strike K must sell
    rallies and buy dips near K. The force IS gamma×OI at K relative to its
    neighbours. Charm describes a consequence of that force over time; this
    measures the force.
  · **IT STILL CARRIES THE TIME SIGNAL.** The pin's share of near-money gamma
    climbed 26.9% → 32.6% through the session. That rise IS the pin
    strengthening into expiry — the thing charm was being asked for — obtained
    without a derivative.

⚠️ **THE HONEST CAVEAT, stated before anyone builds on it:** concentration is
stable partly BECAUSE it is dominated by OI at 360, which barely moves
intraday. So WITHIN a session it may discriminate weakly. Its likely power is
ACROSS symbols and days — telling a real pin from a diffuse one — and TODAY
CANNOT PROVE THAT, because there is exactly one pin in the sample. Treat the
5.94–6.90 stability as evidence the measure is well-behaved, NOT as evidence it
predicts anything.

⚠️ CHARM IS RETAINED AS A RECORDED FIELD AND GATES NOTHING. It is carried on
every plan, raw and gamma-corrected, so the fit can evaluate it against
outcomes. Operator: *"Use our best estimate in the plan & state why we chose
it... It will show up in our fit report when we get to that phase."* Demoting
it from gate to field is exactly that — the reading survives, the authority
does not.

CHARM IS ALREADY COMPUTED BY THIS FLEET. `analysis/second_order.charm()` runs
a finite difference on `greeks_series` and reports dDelta/dt per day, returning
None rather than 0.0 when unmeasurable. It did not need building; it needed
wiring, and this is the wiring.

🔴 **THE ESTIMATE WE CHOSE, AND WHY — READ THIS BEFORE TRUSTING THE NUMBER.**
`second_order.charm()` is a RAW finite difference on delta between two samples.
Between those samples delta moved for TWO reasons: time passed (charm, what we
want) and SPOT MOVED (gamma, what we do not). The function attributes all of it
to time. On 2026-08-25 TSLA's status board read `charm=0.4964` — POSITIVE — on
a session where delta at roughly constant moneyness DECAYED 0.341 -> 0.247,
which is negative charm. Measured by hand from raw/chain_snapshots; the two
readings disagree in SIGN, and sign is what this gate turns on.

**SO WE USE A GAMMA-CORRECTED ESTIMATE HERE:**

        d_delta  ≈  gamma × d_spot  +  charm × dt
    =>  charm    ≈  (d_delta − gamma × d_spot) / dt

Both `gamma` and spot are already in the series, so the correction is
arithmetic — no model, no pricing, nothing fitted. It is the same finite
difference with the term that does not belong subtracted out.

⚠️ **THIS IS AN ESTIMATE AND IT IS MARKED AS ONE.** `gamma` is itself sampled,
so the correction inherits its error; a large spot move between samples leaves
a large residue. Operator's instruction, 2026-08-25: *"Use our best estimate in
the plan & state why we chose it in the file comments. It will show up in our
fit report when we get to that phase."* Accordingly:
  · the plan carries BOTH the raw and the corrected figure, never one alone;
  · `charm_method` is stamped on every plan so the fit can split the population;
  · if the two disagree in SIGN, the plan says so out loud rather than picking.
The fit decides which is right. This file does not pretend to know.

════════════════════════════════════════════════════════════════════════════
GATE 2 — CAN WE REACH THE PIN FROM HERE
════════════════════════════════════════════════════════════════════════════
Distance to the pin, measured against the expected move REMAINING in the
session. Not against a fixed number of dollars — a $6 trip is trivial at 10:00
and impossible at 15:30, and the same gate has to know the difference.

    reach = |pin − spot| / (EM_session × sqrt(session_fraction_remaining))

⚠️ THIS GATE WAS BROKEN UNTIL r125, TODAY. `session_fraction_remaining` read
0.036 at 14:12 ET against a true ~0.42 because the boxes run UTC and the
predicate compared a UTC clock against ET market hours. EM scales with the
square root, so the denominator was ~3.5x too small and every reachability
question was answered "no" all afternoon on every box. Fixed in r125; noted
here because this gate is the main consumer of that fix.

════════════════════════════════════════════════════════════════════════════
THE ADDITION — THE SIGN OF NET GAMMA
════════════════════════════════════════════════════════════════════════════
Not a third question so much as the precondition for the first: net dealer
gamma decides whether the pin PULLS or PUSHES. Positive net gamma means
dealers hedge against moves and price is held; negative means they amplify and
the pin repels. Same pin, same distance, opposite trade.

MEASURED ON TSLA 2026-08-25 from raw/chain_snapshots — it did BOTH in one
session: **−$75.6M at 09:30 (PUSH), then +$28M to +$73M every snapshot after
(PULL).** A butterfly declared at the open was fighting dealer flow; the same
plan an hour later had it as a tailwind. That is too large a difference to
leave unstated.

⚠️ ⟨ASSUMPTION⟩ dealer sign convention: long calls / short puts. NOT verified
against this fleet's own GEX code. The pin's LOCATION barely moves under it
(360 in 72/74 snapshots either way) but the PULL/PUSH verdict flips entirely,
so this is the single most load-bearing assumption in the file.
"""
from __future__ import annotations

import glob
import json
import math
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, List

TAPE = "/home/claude/ct/cascade_tape"
CH   = "/home/claude/cc"

# ⟨PRIOR⟩ every threshold below. Stated, not fitted — they exist so the plan
# can render a verdict at all, and the fit replaces them.
CONC_MIN         = 3.00     # ⟨PRIOR⟩ pin must hold 3x its neighbours' gamma
PIN_SHARE_MIN    = 0.15     # ⟨PRIOR⟩ and 15% of all near-money gamma
CHARM_MIN_PULL   = 0.05     # RECORDED ONLY — no longer gates (v2.0)
REACH_MAX        = 1.00     # pin must sit within one remaining expected move
REACH_MIN        = 0.15     # already at the pin = nothing left to capture
EM_SESSION_PCT   = 0.020    # ⟨PRIOR⟩ session EM as a fraction of spot


def _recs(pattern, root):
    out = []
    for f in sorted(glob.glob(f"{root}/{pattern}", recursive=True)):
        if not os.path.isfile(f):
            continue
        d = json.load(open(f))
        r = d.get("record", d)
        out.append(json.loads(r) if isinstance(r, str) else r)
    return out


CHAINS = None
def chains():
    global CHAINS
    if CHAINS is None:
        CHAINS = [r for r in _recs("**/*", CH) if r.get("event") == "chain_snapshot"]
        CHAINS.sort(key=lambda r: r["ts_et"])
    return CHAINS


def at(hhmm):
    best, prev = chains()[0], None
    for s in chains():
        if s["ts_et"][11:16] <= hhmm:
            prev, best = best, s
        else:
            break
    return prev, best


def con(ch, typ, k):
    for c in ch["contracts"]:
        if c["type"] == typ and abs(float(c["strike"]) - k) < 0.01:
            return c
    return None


def net_gamma(ch):
    """Signed dealer gamma near the money. ⟨ASSUMPTION⟩ long calls/short puts."""
    spot = float(ch["underlying"])
    per = defaultdict(float)
    for c in ch["contracts"]:
        g, oi = float(c.get("gamma") or 0), float(c.get("oi") or 0)
        if g <= 0 or oi <= 0:
            continue
        k = float(c["strike"])
        if abs(k - spot) / spot > 0.15:
            continue
        per[k] += (1 if c["type"] == "C" else -1) * g * oi
    return per, sum(per.values()) * 100 * spot * spot * 0.01


def concentration(ch, pin):
    """(ratio-to-neighbours, pin's share of near-money gamma). GATE 1.

    A LEVEL, not a rate — see the module docstring. Returns (None, None) when
    the pin carries no gamma, which is the absence of a reading rather than a
    reading of zero.
    """
    per, _ = net_gamma(ch)
    if not per or pin not in per:
        return None, None
    at = abs(per[pin])
    near = sorted(per, key=lambda k: abs(k - pin))[1:9]
    m = sum(abs(per[k]) for k in near) / len(near) if near else 0.0
    tot = sum(abs(v) for v in per.values())
    return (at / m if m else None), (at / tot if tot else None)


def pin_of(ch):
    """Gamma flip nearest the money, largest |gamma×OI| when several exist."""
    per, _ = net_gamma(ch)
    if not per:
        return None
    cum, prev, flips = 0.0, None, []
    for k in sorted(per):
        cum += per[k]
        if prev is not None and (prev < 0 <= cum or prev > 0 >= cum):
            flips.append((abs(per[k]), k))
        prev = cum
    return max(flips)[1] if flips else None


def charm_pair(prev_ch, ch, strike):
    """Raw and gamma-corrected charm at `strike`, per day. None when unmeasurable.

    Returns (raw, corrected, note). See the module docstring for why both are
    carried and neither is chosen here."""
    if prev_ch is None:
        return None, None, "no prior snapshot"
    import datetime as dt
    def _t(s):
        return dt.datetime.fromisoformat(s["ts_et"]).timestamp()
    d_t = _t(ch) - _t(prev_ch)
    if d_t < 20:                     # MIN_DT_SECONDS, same guard as the fleet
        return None, None, "samples too close in time"
    a, b = con(prev_ch, "C", strike), con(ch, "C", strike)
    if not a or not b:
        return None, None, "strike absent in one snapshot"
    d_delta = float(b["delta"]) - float(a["delta"])
    d_spot = float(ch["underlying"]) - float(prev_ch["underlying"])
    gamma = (float(a.get("gamma") or 0) + float(b.get("gamma") or 0)) / 2.0
    per_day = 86400.0 / d_t
    raw = d_delta * per_day
    corrected = (d_delta - gamma * d_spot) * per_day
    note = ""
    if raw * corrected < 0:
        note = ("⚠️ RAW AND CORRECTED DISAGREE IN SIGN — the spot move dominates "
                "the delta change. The fit decides; the plan does not.")
    return raw, corrected, note


@dataclass
class ButterflyPlan:
    time: str
    spot: float
    pin: Optional[float]
    net_gex_m: float
    charm_raw: Optional[float]
    charm_corr: Optional[float]
    charm_note: str
    conc: Optional[float]
    share: Optional[float]
    reach: Optional[float]
    debit: Optional[float]
    r: Optional[float]
    verdict: str
    reasons: List[str]

    def render(self):
        print(f"\n  ── {self.time} ET · spot {self.spot:.2f} "
              f"{'─'*40}")
        if self.pin is None:
            print("     NO PIN — no gamma flip near the money. Not a plan.")
            return
        pull = "PULL" if self.net_gex_m > 0 else "PUSH"
        print(f"     pin {self.pin:.0f} · net gamma ${self.net_gex_m/1e6:+.1f}M "
              f"→ {pull}")
        cr = f"{self.charm_raw:+.4f}" if self.charm_raw is not None else "n/a"
        cc = f"{self.charm_corr:+.4f}" if self.charm_corr is not None else "n/a"
        if self.conc is not None:
            print(f"     GATE 1 pull    concentration {self.conc:.2f}x "
                  f"neighbours · {(self.share or 0)*100:.1f}% of near-money "
                  f"gamma")
        print(f"     (recorded)     charm raw {cr} · corrected {cc} "
              f"— GATES NOTHING, for the fit")
        if self.charm_note:
            print(f"                    {self.charm_note}")
        if self.reach is not None:
            print(f"     GATE 2 reach   {self.reach:.2f} of remaining EM "
                  f"({abs(self.pin-self.spot):.2f} to travel)")
        if self.debit is not None:
            print(f"     structure      fly {self.pin-5:.0f}/{self.pin:.0f}/"
                  f"{self.pin+5:.0f} · pay ${self.debit:.2f} · R {self.r:.2f}")
        print(f"     ⇒ {self.verdict}")
        for r in self.reasons:
            print(f"       · {r}")


def plan_at(hhmm) -> Optional[ButterflyPlan]:
    prev_ch, ch = at(hhmm)
    spot = float(ch["underlying"])
    pin = pin_of(ch)
    _, net = net_gamma(ch)
    if pin is None:
        return ButterflyPlan(hhmm, spot, None, net, None, None, "", None,
                             None, None, None, None, "NO PLAN — no pin", [])
    raw, corr, note = charm_pair(prev_ch, ch, pin)

    # remaining session fraction, ET — r125 made this honest
    h, m = int(hhmm[:2]), int(hhmm[3:])
    mins_left = max(0.0, (16 * 60) - (h * 60 + m))
    frac = mins_left / 390.0
    em_rem = spot * EM_SESSION_PCT * math.sqrt(frac) if frac > 0 else 0.0
    reach = abs(pin - spot) / em_rem if em_rem > 0 else None

    b_, w1, w2 = con(ch, "C", pin), con(ch, "C", pin-5), con(ch, "C", pin+5)
    debit = r = None
    if b_ and w1 and w2:
        debit = round(float(w1["ask"]) - 2*float(b_["bid"]) + float(w2["ask"]), 2)
        r = round((5.0 - debit) / debit, 2) if debit > 0 else None

    conc, share = concentration(ch, pin)
    reasons, ok = [], True

    # ── GATE 1: is dealer hedging HELPING, and is the pin STRONG ──────────
    if net <= 0:
        ok = False
        reasons.append(f"net gamma is NEGATIVE (${net/1e6:.1f}M) — the pin "
                       f"PUSHES. Dealers amplify moves; there is no pull to "
                       f"trade.")
    if conc is None:
        ok = False
        reasons.append("pin carries no measurable gamma — no reading.")
    elif conc < CONC_MIN or (share or 0) < PIN_SHARE_MIN:
        ok = False
        reasons.append(f"pin is DIFFUSE: {conc:.2f}x its neighbours "
                       f"(min ⟨PRIOR⟩ {CONC_MIN:.1f}), {(share or 0)*100:.1f}% "
                       f"of near-money gamma (min {PIN_SHARE_MIN*100:.0f}%). "
                       f"Not a pin, just a strike.")
    if reach is None:
        ok = False
        reasons.append("no session left to reach the pin.")
    elif reach > REACH_MAX:
        ok = False
        reasons.append(f"pin is {reach:.2f} remaining-EM away (max "
                       f"⟨PRIOR⟩ {REACH_MAX:.2f}) — {abs(pin-spot):.2f} to "
                       f"travel with {mins_left:.0f} min left. Not reachable.")
    elif reach < REACH_MIN:
        ok = False
        reasons.append(f"already at the pin ({reach:.2f} EM) — the move is "
                       f"spent and the fly is priced for it.")
    if ok:
        reasons.append(f"pin {conc:.2f}x neighbours ({(share or 0)*100:.0f}% of "
                       f"near-money gamma), reachable at {reach:.2f} EM, "
                       f"dealers HOLDING price (${net/1e6:+.0f}M).")
        reasons.append("⚡ FIRE NOW — operator's rule: the earliest tick at "
                       "which price COULD reach the pin and gamma is helping. "
                       "Waiting for a better number spends session, and "
                       "session is the denominator of reachability.")
    return ButterflyPlan(hhmm, spot, pin, net, raw, corr, note, conc, share,
                         reach, debit, r, "TAKE" if ok else "DECLINE", reasons)


if __name__ == "__main__":
    print(__doc__)
    print("=" * 74)
    print("  TSLA 2026-08-25 · two gates, on real chains")
    print("=" * 74)
    for t in ["09:35", "10:30", "11:31", "12:30", "13:00", "14:00", "15:00"]:
        p = plan_at(t)
        if p:
            p.render()
    print()
