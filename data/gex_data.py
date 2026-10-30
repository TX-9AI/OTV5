"""
data/gex_data.py  v5.1
v5.1  2026-10-30  OTV5 r56 (GEX.4) — THE FLIP AND THE WALLS SAY SOMETHING ABOUT TODAY'S PRICE. TELEMETRY ONLY: NO DECISION READS
      flip_strike, call_wall or put_wall (main, strategy/, derived/, status.py, dtp: none; sweep_gex_confluence has zero
      callers), and pin / pin_strike_raw / pin_dist_pct / pin_concentration / net_gex_ratio / gex_environment / orb_bias /
      net_gex / strikes are untouched. The flip walked the front expiry from its LOWEST strike with no distance bound and took
      the first per-strike net sign change (a strike netting exactly 0 counted; zero-gamma strikes are dropped so the strike
      set moved every tick), so it landed on junk: TSLA 2026-10-29 logged flips of $50-$390 on a ~$404 stock (09:30:19 ET:
      215, a strike whose put gamma the feed gave as 0.00000 on 633 OI), SPX 10-26 5000-7555 on ~7670; with no crossing it
      COPIED THE PIN. The walls were unbounded argmaxes of call / put GEX on one 1-DTE expiry, so both fell on the big-OI
      strike nearest spot (call_wall == put_wall on 96% of TSLA 10-29 readings). The operator, 2026-10-29: "I'm curious
      about the gex flip you described. Have an agent look into it." then "I agree on the gex fix for flip & walls, yes now."
      FLIP: the zero of the CUMULATIVE net-GEX profile (summed upward from the band's low edge), built from contracts within
      GEX_FLIP_BAND_PCT (0.15) of spot that carry real open interest (>= MIN_OI_THRESHOLD, no oi_proxy) and gamma >=
      GEX_FLIP_GAMMA_FLOOR (0.01) x the band's peak contract gamma; linearly interpolated between strikes; the crossing
      nearest spot when there are several (flip_crossings counts them); none in band -> flip_strike 0.0 and "flip=none",
      NEVER the pin. Chosen over re-pricing total GEX at hypothetical spots because that needs a time-to-expiry clock inside
      this function and the per-contract IV, which is junk exactly where the tails are (deep-ITM IV 2.66): the cumulative
      profile is deterministic, uses only what the strike map already reads, and is the report's primary method (TSLA
      10-26..10-29 report: 363-393 on every 10-29 snapshot). WALLS: call_wall = the max call-GEX strike AT OR ABOVE spot,
      put_wall = the max |put GEX| strike AT OR BELOW spot (no distance band: r215's "a wall may be far away" stands); each
      records its runner-up strike and runner/wall ratio (call_wall_runner / _ratio, put_wall_runner / _ratio; 1.0 = a tie)
      so a near-tie that will flip-flop is visible (TSLA 10-29 09:30: 420 16.2M vs 400 15.1M). No spot or no candidate on a
      side -> 0.0 / "none". The GEX computed line keeps its fields and order (status.py parses pin=$ and env=) and appends
      cw2= / pw2=. No DB column: nothing persists flip or walls (derived/snapshot writes net_gex only). Gate
      tests/check_gex_flip_walls.py.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
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
    call_wall       — strike with highest call GEX at or above spot (r56)
    put_wall        — strike with highest |put GEX| at or below spot (r56)
    pin_strike      — strike where net GEX is maximized (strongest magnet)
    flip_strike     — zero of the cumulative net-GEX profile near spot (r56; 0 = none)
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
# 🔴 r56 (GEX.4) — THE FLIP IS SEARCHED ONLY NEAR SPOT, ON CONTRACTS WITH REAL GAMMA AND REAL OI.
# ⚠️ BOTH ARE PRIORS AND SAY SO. 15%: the TSLA 2026-10-29 junk sat 8-50% from spot (372.5 on ~404 from a
# deep-ITM call's 0.0025 gamma, 215 from a put gamma fed as 0.00000), and every cumulative crossing the report
# found sat 3-10% away; 15% keeps those and drops the tails that set the old reading. The floor is RELATIVE (a
# fraction of the band's peak contract gamma) so one figure fits SPX at 7,700 and SOFI at 17 — r215's lesson.
# Recorded, not traded: no decision reads flip_strike.
GEX_FLIP_BAND_PCT = float(_os.environ.get("OT_GEX_FLIP_BAND_PCT", "0.15"))
GEX_FLIP_GAMMA_FLOOR = float(_os.environ.get("OT_GEX_FLIP_GAMMA_FLOOR", "0.01"))
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
    call_wall:          float = 0.0       # r56: highest call GEX AT OR ABOVE spot; 0.0 = none
    put_wall:           float = 0.0       # r56: highest |put GEX| AT OR BELOW spot; 0.0 = none
    call_wall_runner:   float = 0.0       # r56: the runner-up call-wall strike (0.0 = none)
    call_wall_runner_ratio: float = 0.0   # r56: runner call GEX / wall call GEX (1.0 = a tie)
    put_wall_runner:    float = 0.0       # r56: the runner-up put-wall strike (0.0 = none)
    put_wall_runner_ratio:  float = 0.0   # r56: runner |put GEX| / wall |put GEX|
    pin_strike:         float = 0.0       # Strike with highest net GEX WITHIN
                                           # PIN_MAX_DIST_PCT of spot; 0.0 = none
    pin_strike_raw:     float = 0.0       # r215: the UNBOUNDED argmax, recorded
                                           # so the bound can be fitted later
    pin_dist_pct:       float = 0.0       # r215: |raw pin - spot| / spot
    flip_strike:        float = 0.0       # r56: zero of the cumulative net-GEX profile
                                           # within GEX_FLIP_BAND_PCT of spot, nearest
                                           # spot, interpolated; 0.0 = none (never the pin)
    flip_crossings:     int   = 0         # r56: how many crossings the band held

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
        # ⚠️ r56: fields and order kept (status.py parses "pin=$" and "env="); a level
        # that does not exist prints "none", never "$0"; the runner-ups are appended.
        def _lvl(v, fmt=".0f"):
            return f"${v:{fmt}}" if v and v > 0 else "none"

        def _run(k, r):
            return f"${k:.0f}@{r:.2f}" if k and k > 0 else "none"
        return (
            f"GEX={self.net_gex/1e6:.1f}M "
            f"env={self.gex_environment} "
            f"pin=${self.pin_strike:.0f} "
            f"call_wall={_lvl(self.call_wall)} "
            f"put_wall={_lvl(self.put_wall)} "
            f"flip={_lvl(self.flip_strike, '.1f')} "
            f"orb={self.orb_bias} "
            f"cw2={_run(self.call_wall_runner, self.call_wall_runner_ratio)} "
            f"pw2={_run(self.put_wall_runner, self.put_wall_runner_ratio)}"
        )


def _wall(strikes_sorted, spot_price, side):
    """r56 (GEX.4): (wall, runner-up, runner/wall ratio) on the spot side of a
    call (at or above) or put (at or below) wall; zeros when there is none."""
    if not spot_price or spot_price <= 0:
        return 0.0, 0.0, 0.0
    if side == "call":
        cand = [s for s in strikes_sorted
                if s.strike >= spot_price and s.call_gex > 0]
        cand.sort(key=lambda s: (-s.call_gex, s.strike))
        mag = [s.call_gex for s in cand]
    else:
        cand = [s for s in strikes_sorted
                if s.strike <= spot_price and s.put_gex < 0]
        cand.sort(key=lambda s: (s.put_gex, -s.strike))
        mag = [-s.put_gex for s in cand]
    if not cand:
        return 0.0, 0.0, 0.0
    if len(cand) == 1:
        return cand[0].strike, 0.0, 0.0
    return cand[0].strike, cand[1].strike, round(mag[1] / mag[0], 4)


def _flip_level(chain, spot_price):
    """r56 (GEX.4): (flip or None, crossings) — the zero of the cumulative
    net-GEX profile within GEX_FLIP_BAND_PCT of spot, from contracts with real
    OI (>= MIN_OI_THRESHOLD; the oi_proxy is not used here) and gamma >=
    GEX_FLIP_GAMMA_FLOOR x the band's peak contract gamma; linear between
    strikes; the crossing nearest spot. Reads its own contracts: the strike map
    the pin and environment use is not touched."""
    if not spot_price or spot_price <= 0:
        return None, 0
    lo = spot_price * (1.0 - GEX_FLIP_BAND_PCT)
    hi = spot_price * (1.0 + GEX_FLIP_BAND_PCT)
    rows = []
    for sign, side in ((1.0, getattr(chain, "calls", None) or []),
                       (-1.0, getattr(chain, "puts", None) or [])):
        for c in side:
            try:
                k, g = float(c.strike), float(c.gamma)
                oi = float(c.open_interest or 0)
            except (TypeError, ValueError):
                continue
            if lo <= k <= hi and g > 0 and oi >= MIN_OI_THRESHOLD:
                rows.append((k, g, oi, sign))
    if not rows:
        return None, 0
    floor = GEX_FLIP_GAMMA_FLOOR * max(r[1] for r in rows)
    per: dict = {}
    for k, g, oi, sign in rows:
        if g >= floor:
            per[k] = per.get(k, 0.0) + sign * g * oi * 100 * spot_price
    pts, cum = [], 0.0
    for k in sorted(per):
        cum += per[k]
        pts.append((k, cum))
    best, n = None, 0
    for (k0, c0), (k1, c1) in zip(pts, pts[1:]):
        if (c0 < 0) != (c1 < 0):
            n += 1
            x = k0 + (k1 - k0) * (-c0) / (c1 - c0) if c1 != c0 else k1
            if best is None or abs(x - spot_price) < abs(best - spot_price):
                best = x
    return (round(best, 2) if best is not None else None), n


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

    # ── Walls — r56 (GEX.4): a call wall ABOVE spot, a put wall BELOW it ─────
    # 🔴 THESE WERE UNBOUNDED ARGMAXES with no side-of-spot rule. On one 1-DTE
    # expiry gamma peaks at the money, so both landed on the big-OI strike
    # nearest spot (call_wall == put_wall on 96% of TSLA 2026-10-29 readings).
    # A wall is resistance above / support below or it is not a wall. Still no
    # distance band (r215: a wall may be far away). The runner-up and its ratio
    # make a near-tie visible (TSLA 09:30: 420 16.2M vs 400 15.1M).
    _cw, _cwr, _cwq = _wall(strikes_sorted, spot_price, "call")
    _pw, _pwr, _pwq = _wall(strikes_sorted, spot_price, "put")
    snapshot.call_wall, snapshot.call_wall_runner = _cw, _cwr
    snapshot.call_wall_runner_ratio = _cwq
    snapshot.put_wall, snapshot.put_wall_runner = _pw, _pwr
    snapshot.put_wall_runner_ratio = _pwq

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

    # ── Flip — r56 (GEX.4): the cumulative profile's zero NEAR SPOT, or none ──
    # 🔴 THIS WALKED FROM THE LOWEST STRIKE, UNBOUNDED, and took the first
    # per-strike sign change (a strike netting exactly 0 counted), so a far tail
    # strike with a zero or junk greek set it: TSLA 2026-10-29 flips of $50-$390
    # on ~$404, SPX 10-26 5000-7555 on ~7670. With no crossing it COPIED THE PIN,
    # a clean-looking wrong answer. Now: _flip_level (header v5.1); none -> 0.0.
    _flip, _ncross = _flip_level(chain, spot_price)
    snapshot.flip_strike = _flip if _flip is not None else 0.0
    snapshot.flip_crossings = _ncross

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