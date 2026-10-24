"""
data/gex_data.py  v4.1
v4.1  2026-09-01  r215 — 🔴 THE PIN STRIKE WAS A BARE ARGMAX OVER THE WHOLE
      CHAIN, UNBOUNDED. `max(strikes_sorted, key=net_gex)` with nothing
      constraining it to strikes near spot, so when net GEX is flat or noisy
      the argmax WANDERS. Measured from the warehouse, 2026-08-31: GOOGL
      published TWENTY distinct pins spanning 245-450 in a single session,
      roughly bracketing a ~345 price, and AMZN twenty-six spanning 212-275.
      Neither name moves 30% in a day — that is an argmax jumping as one
      strike edges past another, not a magnet migrating.
      🔑 A PIN IS A CLAIM THAT GAMMA WILL PULL PRICE TO A STRIKE, and a
      strike 30% away cannot pull today's price anywhere, however large its
      net GEX. Bounded to PIN_MAX_DIST_PCT of spot.
      ⚠️ THE WALLS ARE LEFT UNBOUNDED DELIBERATELY. A wall IS allowed to be
      far away — that is what makes it a wall — and the sweep reads them for
      confluence. Only the PIN asserts something about today's price.
      ⚠️ OUT OF RANGE MEANS NO PIN, NEVER A SUBSTITUTE. `pin_strike` stays
      0.0, which every consumer already reads as absent. This deliberately
      does NOT wire `best_butterfly_center()` — a guard that has existed all
      along with ZERO callers — because its ATM fallback INVENTS a pin the
      chain never published, against r208's "the apex IS the trade; a
      nearest-strike substitute is a different one". Its `max_distance=5.0`
      is also DOLLARS, meaningless across a fleet holding SPX at 7,700 and
      NFLX at 83; this bound is relative.
      ⚠️ 3% IS A PRIOR AND SAYS SO. Sized so every plausible pin in the
      2026-08-31/09-01 sample survives (QQQ 710-724 on ~707, SPX 7675-7810 on
      ~7700) and every implausible one does not. `pin_strike_raw` and
      `pin_dist_pct` are recorded on the snapshot and written to plan_check
      so it can be FITTED rather than defended.
Gamma exposure, call/put walls, pin, from the live chain.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

data/gex_data.py — SCALE-FREE GEX ENVIRONMENT.
        The $1M absolute NEUTRAL threshold was unreachable with proxy OI
        (gross chain GEX ~$50-500K on any symbol) — gex_environment was
        permanently NEUTRAL and butterfly Gate 5 (PINNING) could never open,
        on any box, since v3.0. Environment now classifies on RATIOS —
        net/gross sign strength + pin-strike concentration of gross |GEX| —
        which are scale-invariant and therefore symbol-specific by
        construction (per operator directive 2026-07-14): QQQ at $600, MU at
        $925, CVX at $150 classify identically for identical chain SHAPE.
        Knobs: OT_GEX_PIN_CONC (0.15) · OT_GEX_SIGN_RATIO (0.20). PRIORS —
        calibrate from the signal ledger once it accumulates.
--- original header follows ---
data/gex_data.py — GEX (Gamma Exposure) calculator from live options chain.
Computed directly from the TastyTrade chain we already fetch every 15s.
No external API, no scraping, no rate limits.
GEX Formula (per strike):
    call_gex = gamma × open_interest × 100 × spot_price
    put_gex  = gamma × open_interest × 100 × spot_price × -1  (puts flip sign)
    net_gex  = call_gex + put_gex
Derived outputs:
    net_gex_total   — sum across all strikes. Positive = pinning, negative = trending
    call_wall       — strike with highest cumulative call GEX (resistance)
    put_wall        — strike with highest cumulative put GEX (support)
    pin_strike      — strike where net GEX is maximized (strongest magnet)
    flip_strike     — strike where net GEX crosses zero (trending/pinning boundary)
    gex_environment — "PINNING", "TRENDING", or "NEUTRAL"
    orb_bias        — "DAMPENING" or "AMPLIFYING" (for ORB strategy)
Strategy inputs:
    Butterfly:        center on pin_strike, only enter if gex_environment == PINNING
    Sweep Reversal:   confluence boost if sweep occurs at call_wall or put_wall
    ORB:              orb_bias — DAMPENING = require higher conviction,
                                 AMPLIFYING = lower bar, breakouts get fuel
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List
from data.options_chain import OptionsChain, OptionContract

logger = logging.getLogger(__name__)

# Minimum open interest to include a strike in GEX calculation
MIN_OI_THRESHOLD = 10

# Net GEX threshold (in millions) to classify environment
# ── v3.1 environment thresholds — SCALE-FREE RATIOS (symbol-specific by
# construction; the old $1M absolute made PINNING unreachable: with proxy OI
# gross chain GEX is ~$50-500K on ANY symbol → permanently NEUTRAL → butterfly
# Gate 5 could never open, on any box, since v3.0) ────────────────────────────
import os as _os
GEX_PIN_CONCENTRATION = float(_os.environ.get("OT_GEX_PIN_CONC", "0.15"))
# 🔴 r215 — HOW FAR FROM SPOT A STRIKE MAY BE AND STILL BE CALLED A PIN.
# ⚠️ RELATIVE, NEVER ABSOLUTE. The dead `best_butterfly_center()` used
# `max_distance=5.0` DOLLARS, which is meaningless across this fleet: $5 is
# 0.06% of SPX at 7,700 and 6% of NFLX at 83. One fleet-wide dollar figure
# would be far too loose on the index and far too tight on the cheap names.
# ⚠️ 3% IS A PRIOR AND IS LABELLED AS ONE (r208's category 1: set a baseline
# where none exists, say it is a prior, do not pretend it is a fit). Sized from
# the 2026-08-31/09-01 evidence: the pins that look right sit inside ~2.5% of
# spot (QQQ 710-724 on ~707, SPX 7675-7810 on ~7700) while the wandering ones
# are 29-30% away (GOOGL 245 and 450 against ~345). 3% keeps every plausible
# pin in the sample and excludes every implausible one — but it has NOT been
# fitted against outcomes, and `pin_dist_pct` is recorded so it can be.
PIN_MAX_DIST_PCT = float(_os.environ.get("OT_GEX_PIN_MAX_DIST_PCT", "0.03"))
#   PINNING additionally requires the pin strike to hold >= this share of gross |GEX|
GEX_SIGN_RATIO        = float(_os.environ.get("OT_GEX_SIGN_RATIO", "0.20"))
#   |net|/gross below this = NEUTRAL (no meaningful dealer-positioning signal)


@dataclass
class StrikeGEX:
    """GEX breakdown for a single strike."""
    strike:     float = 0.0
    call_gex:   float = 0.0   # USD
    put_gex:    float = 0.0   # USD (already negative)
    net_gex:    float = 0.0   # call_gex + put_gex
    call_oi:    int   = 0
    put_oi:     int   = 0


@dataclass
class GEXSnapshot:
    """
    Full GEX snapshot computed from the current options chain.
    Refreshed every 15s in sync with chain fetch.
    """
    # Raw totals
    total_call_gex:     float = 0.0       # Sum of all call GEX (USD)
    total_put_gex:      float = 0.0       # Sum of all put GEX (USD, negative)
    net_gex:            float = 0.0       # total_call + total_put

    # Key levels
    call_wall:          float = 0.0       # Strike with highest call GEX
    put_wall:           float = 0.0       # Strike with highest put GEX magnitude
    pin_strike:         float = 0.0       # Strike with highest net GEX WITHIN
                                           # PIN_MAX_DIST_PCT of spot; 0.0 = none
    pin_strike_raw:     float = 0.0       # r215: the UNBOUNDED argmax, recorded
                                           # so the bound can be fitted later
    pin_dist_pct:       float = 0.0       # r215: |raw pin - spot| / spot
    flip_strike:        float = 0.0       # Strike where net GEX crosses zero

    # Per-strike breakdown (sorted by strike)
    strikes:            List[StrikeGEX] = field(default_factory=list)

    # Environment classification
    gex_environment:    str = "NEUTRAL"   # "PINNING", "TRENDING", "NEUTRAL"

    # ── v4.0: PIN STRENGTH IS A NUMBER, NOT JUST A LABEL ────────────────────
    # `pin_conc` and `net_ratio` were computed here, used to decide the
    # PINNING/TRENDING/NEUTRAL label, and then DISCARDED as locals. A consumer
    # could ask "is it pinning?" but never "HOW STRONGLY?" - and for a butterfly
    # that is the whole question, because the wings only pay if price STAYS.
    # A pin strike holding 40% of gross |GEX| is one dominant magnet; one
    # holding 8% is gamma smeared across many strikes with nothing actually
    # pinned - and BOTH read "PINNING" once past the 0.15 threshold.
    # ⚠️ This is the same defect class as v3's `flat_angle_deg` (computed every
    # tick, landed in a dict, never attached to the object a consumer read) and
    # `direction_conf` (separated on the live book, journaled nowhere).
    # COMPUTED AND DISCARDED is the recurring failure of this codebase.
    pin_concentration:  float = 0.0   # |pin net GEX| / gross |GEX|, 0..1
    net_gex_ratio:      float = 0.0   # net/gross, signed: + pins, - trends
    orb_bias:           str = "NEUTRAL"   # "DAMPENING", "AMPLIFYING", "NEUTRAL"

    # Meta
    spot_price:         float = 0.0
    computed_at:        str   = ""
    valid:              bool  = False      # False if chain data was insufficient

    def summary(self) -> str:
        return (
            f"GEX={self.net_gex/1e6:.1f}M "
            f"env={self.gex_environment} "
            f"pin=${self.pin_strike:.0f} "
            f"call_wall=${self.call_wall:.0f} "
            f"put_wall=${self.put_wall:.0f} "
            f"flip=${self.flip_strike:.0f} "
            f"orb={self.orb_bias}"
        )


def compute_gex(chain: OptionsChain, spot_price: float) -> GEXSnapshot:
    """
    Compute full GEX snapshot from the current options chain.

    Args:
        chain:       Populated OptionsChain from get_chain_fetcher().fetch_chain()
        spot_price:  Current underlying price (for GEX scaling)

    Returns:
        GEXSnapshot with all derived levels and classifications
    """
    from datetime import datetime, timezone
    snapshot = GEXSnapshot(
        spot_price   = spot_price,
        computed_at  = datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
    )

    if not chain or not chain.calls or not chain.puts:
        logger.warning("GEX: empty chain — cannot compute")
        return snapshot

    # ── Build strike map ──────────────────────────────────────────────────────
    strike_map: dict = {}

    for call in chain.calls:
        if call.gamma == 0:
            continue
        s = call.strike
        if s not in strike_map:
            strike_map[s] = StrikeGEX(strike=s)
        # Use OI if available, otherwise gamma×mark proxy
        # Higher gamma + tighter spread = more dealer hedging at that strike
        oi_proxy = call.open_interest if call.open_interest > 0 else max(1, int(1000 * call.gamma / max(call.mark, 0.01)))
        gex = call.gamma * oi_proxy * 100 * spot_price
        strike_map[s].call_gex += gex
        strike_map[s].call_oi  += oi_proxy

    for put in chain.puts:
        if put.gamma == 0:
            continue
        s = put.strike
        if s not in strike_map:
            strike_map[s] = StrikeGEX(strike=s)
        oi_proxy = put.open_interest if put.open_interest > 0 else max(1, int(1000 * put.gamma / max(put.mark, 0.01)))
        gex = put.gamma * oi_proxy * 100 * spot_price * -1
        strike_map[s].put_gex += gex
        strike_map[s].put_oi  += oi_proxy

    if not strike_map:
        logger.warning("GEX: no strikes with gamma/OI data")
        return snapshot

    # ── Net GEX per strike ────────────────────────────────────────────────────
    for sg in strike_map.values():
        sg.net_gex = sg.call_gex + sg.put_gex

    strikes_sorted = sorted(strike_map.values(), key=lambda s: s.strike)
    snapshot.strikes = strikes_sorted

    # ── Aggregate totals ──────────────────────────────────────────────────────
    snapshot.total_call_gex = sum(s.call_gex for s in strikes_sorted)
    snapshot.total_put_gex  = sum(s.put_gex  for s in strikes_sorted)
    snapshot.net_gex        = snapshot.total_call_gex + snapshot.total_put_gex

    # ── Call wall — strike with highest positive call GEX ─────────────────────
    call_wall_strike = max(strikes_sorted, key=lambda s: s.call_gex, default=None)
    if call_wall_strike:
        snapshot.call_wall = call_wall_strike.strike

    # ── Put wall — strike with highest put GEX magnitude ─────────────────────
    put_wall_strike = min(strikes_sorted, key=lambda s: s.put_gex, default=None)
    if put_wall_strike:
        snapshot.put_wall = put_wall_strike.strike

    # ── Pin strike — highest net GEX WITHIN REACH OF SPOT ────────────────────
    # 🔴 r215 — THIS WAS A BARE ARGMAX OVER THE WHOLE CHAIN, UNBOUNDED. Nothing
    # constrained it to strikes near price, so when net GEX is flat or noisy
    # across the chain the argmax wanders: measured 2026-08-31, GOOGL published
    # TWENTY distinct pins spanning 245-450 in one session, roughly bracketing
    # a ~345 price, and AMZN twenty-six spanning 212-275. That is not a magnet
    # migrating — it is an argmax jumping as one strike edges past another.
    # 🔑 A PIN IS A CLAIM THAT GAMMA WILL PULL PRICE TO A STRIKE. A strike 30%
    # away cannot pull today's price anywhere, so it is not a pin however large
    # its net GEX. The walls are different and are deliberately left unbounded:
    # a wall IS allowed to be far away — that is what makes it a wall.
    # ⚠️ OUT OF RANGE MEANS NO PIN, NEVER A SUBSTITUTE PIN. `pin_strike` stays
    # 0.0, which every consumer already reads as "no pin" (the butterfly's
    # `pinning` condition requires pin > 0). This deliberately does NOT use
    # `best_butterfly_center()`, which falls back to ATM — inventing a pin
    # where the chain published none, against r208's ruling that "the apex IS
    # the trade; a nearest-strike substitute is a different one".
    # ⚠️ THE BOUND IS A PRIOR, NOT A FIT — nobody has measured this yet. The
    # RAW argmax and its distance are recorded alongside so the distribution
    # can be studied and the bound moved on evidence rather than on my guess.
    pin = max(strikes_sorted, key=lambda s: s.net_gex, default=None)
    if pin:
        snapshot.pin_strike_raw = pin.strike
        if spot_price and spot_price > 0:
            snapshot.pin_dist_pct = abs(pin.strike - spot_price) / spot_price
            near = [s for s in strikes_sorted
                    if abs(s.strike - spot_price) / spot_price
                    <= PIN_MAX_DIST_PCT]
            best = max(near, key=lambda s: s.net_gex, default=None)
            snapshot.pin_strike = best.strike if best else 0.0
        else:
            # ⚠️ NO SPOT MEANS THE DISTANCE IS UNKNOWABLE, and an unknowable
            # distance is not a passed check. Refuse rather than pass through.
            snapshot.pin_strike = 0.0

    # ── Flip strike — where net GEX crosses zero ──────────────────────────────
    # Walk from low to high strikes, find where net GEX goes from negative to positive
    flip = None
    for i in range(1, len(strikes_sorted)):
        prev = strikes_sorted[i - 1]
        curr = strikes_sorted[i]
        if prev.net_gex < 0 and curr.net_gex >= 0:
            # Flip point — take the strike closer to zero
            if abs(prev.net_gex) < abs(curr.net_gex):
                flip = prev.strike
            else:
                flip = curr.strike
            break
    if flip:
        snapshot.flip_strike = flip
    elif strikes_sorted:
        # No clean flip found — use pin strike as proxy
        snapshot.flip_strike = snapshot.pin_strike

    # ── Environment classification (v3.1: scale-free ratios) ──────────────────
    gross = sum(abs(sg.net_gex) for sg in snapshot.strikes) or 1.0
    net_ratio = snapshot.net_gex / gross
    pin_sg = max(snapshot.strikes, key=lambda s: abs(s.net_gex), default=None)
    pin_conc = (abs(pin_sg.net_gex) / gross) if pin_sg is not None else 0.0

    # v4.0: deliver the strength, do not merely decide on it
    snapshot.pin_concentration = round(pin_conc, 4)
    snapshot.net_gex_ratio = round(net_ratio, 4)

    if net_ratio > GEX_SIGN_RATIO and pin_conc >= GEX_PIN_CONCENTRATION:
        snapshot.gex_environment = "PINNING"
        snapshot.orb_bias        = "DAMPENING"
    elif net_ratio < -GEX_SIGN_RATIO:
        snapshot.gex_environment = "TRENDING"
        snapshot.orb_bias        = "AMPLIFYING"
    else:
        snapshot.gex_environment = "NEUTRAL"
        snapshot.orb_bias        = "NEUTRAL"

    snapshot.valid = True

    logger.info(f"GEX computed: {snapshot.summary()}")
    return snapshot


def butterfly_gex_grade(snapshot: GEXSnapshot,
                         center_strike: float,
                         tolerance: float = 2.0) -> str:
    """
    Grade a butterfly entry based on GEX confluence.

    Args:
        snapshot:       Current GEX snapshot
        center_strike:  Proposed butterfly center strike
        tolerance:      Max distance from pin strike for Grade A (default $2)

    Returns:
        "A" — pin strike within tolerance AND PINNING environment
        "B" — PINNING environment but pin strike further away
        "C" — NEUTRAL or TRENDING — skip or heavily reduce size
    """
    if not snapshot.valid:
        return "B"   # No GEX data — default to B, don't block

    if snapshot.gex_environment == "TRENDING":
        return "C"   # Dealers short gamma — butterflies will get run over

    pin_distance = abs(center_strike - snapshot.pin_strike)

    if snapshot.gex_environment == "PINNING" and pin_distance <= tolerance:
        return "A"
    elif snapshot.gex_environment == "PINNING":
        return "B"
    else:
        return "B"   # NEUTRAL — allow but don't boost


def sweep_gex_confluence(snapshot: GEXSnapshot,
                          sweep_price: float,
                          tolerance: float = 2.0) -> bool:
    """
    Check if a sweep occurred at a GEX wall — highest conviction reversal.

    Args:
        snapshot:     Current GEX snapshot
        sweep_price:  Price level where the sweep occurred
        tolerance:    Max distance from wall strike

    Returns:
        True if sweep is at call wall or put wall (strong reversal confirmation)
    """
    if not snapshot.valid:
        return False

    at_call_wall = abs(sweep_price - snapshot.call_wall) <= tolerance
    at_put_wall  = abs(sweep_price - snapshot.put_wall)  <= tolerance

    if at_call_wall or at_put_wall:
        wall = "call_wall" if at_call_wall else "put_wall"
        logger.info(
            f"GEX sweep confluence: sweep at ${sweep_price:.2f} "
            f"near {wall} (${snapshot.call_wall if at_call_wall else snapshot.put_wall:.2f})"
        )
        return True
    return False


def best_butterfly_center(snapshot: GEXSnapshot,
                           current_price: float,
                           max_distance: float = 5.0) -> float:
    """
    Return the best center strike for a butterfly.
    Uses GEX pin strike if within max_distance of current price,
    otherwise falls back to current price (ATM).

    Args:
        snapshot:       Current GEX snapshot
        current_price:  Current underlying price
        max_distance:   Max distance pin strike can be from price

    Returns:
        Optimal center strike price
    """
    if not snapshot.valid or snapshot.pin_strike == 0:
        return current_price

    pin_distance = abs(current_price - snapshot.pin_strike)

    if pin_distance <= max_distance:
        logger.info(
            f"GEX pin center: ${snapshot.pin_strike:.0f} "
            f"(price=${current_price:.2f} distance=${pin_distance:.1f})"
        )
        return snapshot.pin_strike

    logger.debug(
        f"GEX pin ${snapshot.pin_strike:.0f} too far from price "
        f"${current_price:.2f} ({pin_distance:.1f} > {max_distance}) — using ATM"
    )
    return current_price