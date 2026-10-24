"""
strategy/orcs_plan.py  v1.9
v1.9  2026-10-19  OTV4TEST r303 (PSTATE.1) — A READY ORCS THAT WILL NOT TRADE IS NOT A TAKE. The READY row was verdict
      TAKE whether or not the trade was on (strategy/orcs.py returns no signal when ORCS_ENABLED is off), so the
      'off' ORCS wrote TAKE rows all window. Now TAKE only when the plan is ACTIVE, LOG-ONLY when it is switched to
      log (OT_ORCS=log); DORMANT (the default, reversing r249's "the plan keeps recording" by the operator's
      2026-10-19 "1. Yes") is never asked.
v1.8  2026-10-04  OTV4TEST r234 (SCALE.1) — THE WING AND THE CREDIT FLOOR SCALE WITH THE BOX'S CONTRACT PRICE. ORCS_WING_USD and ORCS_MIN_CREDIT here are config's QQQ dollars x config.CONTRACT_SCALE (QQQ 1.0 - unchanged; SPX 7.5 - a 22.50 target wing, so the listed strike nearest it, 20 or 25 on a 5-dollar chain, and a 0.75 floor). The operator, 2026-10-04: "SPX cap, ramp & wing search CANNOT be the same as QQQ ... It needs to scale with the contract price differences."
v1.7  2026-10-03  OTV4TEST r230 (PREM.5) — the HOLD row's text says 'defended as a condor' (was 'held to the close'); nothing else.
v1.6  2026-10-03  OTV4TEST r229 (EM.2) — THE IMPLIED MOVE IS THE TASTYTRADE PLATFORM'S EXPECTED MOVE (analysis.volatility_measures.expected_move_platform: 60% ATM straddle + 30% first strangle + 10% second), no longer the bare ATM straddle. The operator, 2026-10-03: "Use the one that's built into the tasty trade platform." Measured 10-01/10-02 at 09:45-10:29: 0.87-0.91 of the straddle, so the 1.0x distance floor sits 9-13% nearer; the delta cap is unchanged. The straddle is still recorded (atm_straddle).
v1.5  2026-10-03  OTV4TEST r223 (EM.1) — mark_of and implied_move are analysis.volatility_measures.quote_mark / straddle_same_strike (moved verbatim; the names here are aliases).
v1.4  2026-10-03  OTV4TEST r220 (TIME.1) — its private HH:MM parser is utils.time_utils.parse_hm (eight plans carried the same copy), and an UNREADABLE clock is DORMANT - no trade - instead of skipping the window check.
v1.3  2026-10-03  OTV4TEST r207 (PREM.4) — THE WING IS A DOLLAR WIDTH (ORCS_WING_USD), not 1% of spot. The operator: "why the
      fuck would I risk $1000 for $25???" - the 1% wing was my harness's constant, never varied, and it made
      the credit 4% of the risk. The long is the listed strike nearest ORCS_WING_USD beyond the short. The
      delta cap and the implied-move floor are config's (0.20 and 1.0 as of r207).
v1.2  2026-10-03  OTV4TEST r206 (PREM.3) — THE ENTRY LADDER GOVERNS THE ENTRY; THE PLAN'S OWN OFFER IS REMOVED.
      The operator, 2026-10-03, on r204's "freezes an offer one cent better than the mark": "No, we have a
      ladder for entries. THAT has to govern our entry. 'One cent better' is not even a valid increment
      on most contracts". REMOVED: the frozen offer, its limit (mark + ORCS_LIMIT_IMPROVE), the ten-minute
      rest (ORCS_REST_MIN), the offer_* checks, the restart read of them, and the last-offer cutoff. NOW:
      a side whose gates pass is READY at the MARK credit and the strategy hands it to the house credit
      entry (_execute_condor_leg): paper books the mark through limit_ladder.paper_fill_credit; live
      walks the entry ladder down from the best credit and stops at the mark, on valid increments. A
      side already entered this session (the strategy reads trades.db) is recorded `taken`, not ready.
      EVERYTHING BELOW ABOUT AN "OFFER" DESCRIBES r203/r204 AND IS NO LONGER TRUE.
v1.1  2026-10-03  OTV4TEST r204 (PREM.2) — THE OPENING RANGE CREDIT SPREAD (ORCS): THE PLAN NOW FEEDS A TRADE.
      The operator, 2026-10-03: "No, keep going. I want to paper trade it Monday. Retire the sweep & TCS.
      Call this new one the opening range credit spread ORCS." Renamed from open_premium_plan.py (r203);
      the plan name is OpeningRangeCreditSpread and the dials are ORCS_*. WHAT CHANGED IN THE PLAN:
      (1) `prep.fills` names the sides whose frozen offer FILLED ON THIS TICK (the mark reached the
      limit) - the strategy trades exactly those, at the limit; (2) a new offer is frozen only while a
      full rest still fits inside the window (the last offer is at END minus ORCS_REST_MIN), so every
      offer resolves inside the admission window; (3) the window comes from config.ENTRY_WINDOWS;
      (4) the plan's row is TAKE on a fill tick. Location, pricing, gates and the restart read are r203's.
v1.0  2026-10-03  OTV4TEST r203 (PREM.1) — THE OPENING PREMIUM SPREAD PLAN, RECORD-ONLY (PLAN_SPEC §41).
      The operator, 2026-10-03: "Build this spec, use it to draft the strategy's trigger components
      Incorporating derivative informers if it enhances the edge further. After the trigger components
      are selected, set preliminary dials, then build the plan that searches the chain for our trigger
      components' location on the chain." And on fills: "we get better than mark or we don't trade it."

      THE TRADE: on a 0DTE session, from 09:45 ET, sell one put spread and one call spread far out of
      the money and hold them to the close. The studies behind it (X5-X8, /var/tmp/levels_1003/
      RESULT.md): QQQ 0DTE, 28 priced sessions, short strike at |delta| <= 0.15 entered 09:45, mid
      fills - 96% winners, R +0.036 / +0.029 by half. NOT PROVEN: those 28 sessions were calm.

      WHAT IT SEARCHES THE CHAIN FOR, each side, every tick of the window:
        the SHORT strike - the nearest-to-spot OTM strike whose |delta| <= ORCS_SHORT_DELTA_MAX and
          whose distance from spot is >= ORCS_MIN_IM_MULT x the implied move (the ATM straddle's mark);
        the LONG strike  - the listed strike nearest ORCS_WING_PCT of spot further out;
        the CREDIT at the mark, and the same credit at bid/ask (recorded beside it);
        the OFFER - a limit ORCS_LIMIT_IMPROVE better than the mark, frozen at the first ready tick and
          watched for ORCS_REST_MIN minutes: filled_mark when the frozen spread's mark reaches the limit,
          filled_natural when its bid/ask does. Unfilled at the end = NO TRADE (the ruling above).
      DAY GATES: the chain expires today (0DTE); |overnight gap| <= ORCS_MAX_GAP_PCT (the one informer
      that agreed on both samples - large-gap days paid out more on the 56-day sample).
      RECORDED, GATING NOTHING: implied move, opening-range width, VIX, each short's distance.

      The frozen offer is re-read from this plan's own rows at the first look, so a restart inside the
      window continues the offer instead of re-freezing it (nothing lives only in memory).
"""
from __future__ import annotations

import logging

import config
from strategy.plan import Plan
from utils.math_utils import safe_float

logger = logging.getLogger(__name__)

# ── GATE CATEGORIES AS DATA (WA §36) ────────────────────────────────────────
GATES = {
    "ORCS_START_ET":         "FOUNDATIONAL",   # the edge is gone from 11:00 (X6)
    "ORCS_END_ET":           "FOUNDATIONAL",
    "ORCS_SHORT_DELTA_MAX":  "SELECTION",
    "ORCS_MIN_IM_MULT":      "SELECTION",
    "ORCS_MIN_CREDIT":       "FEASIBILITY",
    "ORCS_MAX_GAP_PCT":      "SELECTION",
}

NAME = "OpeningRangeCreditSpread"
ORCS_START_ET        = tuple(config.ENTRY_WINDOWS[NAME][0])     # one window table (r148)
ORCS_END_ET          = tuple(config.ENTRY_WINDOWS[NAME][1])
ORCS_SHORT_DELTA_MAX = float(config.ORCS_SHORT_DELTA_MAX)
ORCS_MIN_IM_MULT     = float(config.ORCS_MIN_IM_MULT)
ORCS_CONTRACT_SCALE  = float(getattr(config, "CONTRACT_SCALE", 1.0))      # r234: QQQ = 1.0
ORCS_WING_USD        = float(config.ORCS_WING_USD) * ORCS_CONTRACT_SCALE    # this box's dollars
ORCS_MIN_CREDIT      = float(config.ORCS_MIN_CREDIT) * ORCS_CONTRACT_SCALE
ORCS_MAX_GAP_PCT     = float(config.ORCS_MAX_GAP_PCT)

SIDES = ("put", "call")


from utils.time_utils import parse_hm as _hm      # r220 (TIME.1): the one parser


from analysis.volatility_measures import quote_mark as mark_of            # r223 (EM.1): moved verbatim
from analysis.volatility_measures import expected_move_platform as implied_move   # r229 (EM.2): the platform's expected move, by ruling
from analysis.volatility_measures import straddle_same_strike                       # r229: still RECORDED beside it


class Located:
    """One side's location on the chain."""
    __slots__ = ("side", "short", "long", "delta", "dist", "dist_pct", "im_mult", "width",
                 "credit", "natural", "why", "why_key")

    def __init__(self, side):
        self.side = side
        self.short = self.long = None
        self.delta = self.dist = self.dist_pct = self.im_mult = None
        self.width = self.credit = self.natural = None
        self.why = self.why_key = ""

    @property
    def priced(self):
        return self.short is not None and self.long is not None and self.credit is not None

    def line(self):
        if not self.priced:
            return f"{self.side}: {self.why or 'not located'}"
        return (f"{self.side} {float(self.short.strike):g}/{float(self.long.strike):g} "
                f"delta {self.delta:.2f}, {self.dist_pct:.2f}% out, credit {self.credit:.2f} at mark")


def locate(side: str, chain, spot: float, im: float) -> Located:
    """Search one side of the chain for the short and long strikes. Pure: reads the chain, decides nothing."""
    loc = Located(side)
    contracts = list(getattr(chain, "puts" if side == "put" else "calls", None) or [])
    otm = []
    for c in contracts:
        k = safe_float(getattr(c, "strike", None))
        if not k or k <= 0 or (k >= spot if side == "put" else k <= spot):
            continue
        otm.append((abs(k - spot), k, c))
    if not otm:
        loc.why, loc.why_key = "no out-of-the-money strike on this side", f"{side}_short"
        return loc
    otm.sort(key=lambda x: x[0])
    with_delta = [(d, k, c) for d, k, c in otm if abs(safe_float(getattr(c, "delta", 0)) or 0.0) > 0]
    if not with_delta:
        loc.why, loc.why_key = "no delta on any out-of-the-money strike", f"{side}_delta"
        return loc
    floor = ORCS_MIN_IM_MULT * im
    pick = next(((d, k, c) for d, k, c in with_delta
                 if abs(float(c.delta)) <= ORCS_SHORT_DELTA_MAX and d >= floor), None)
    if pick is None:
        loc.why = (f"no strike with delta <= {ORCS_SHORT_DELTA_MAX:g} at least "
                   f"{ORCS_MIN_IM_MULT:g} implied moves ({floor:.2f}) out")
        loc.why_key = f"{side}_short"
        return loc
    d, k, short = pick
    loc.short, loc.delta, loc.dist = short, abs(float(short.delta)), round(d, 4)
    loc.dist_pct = round(100.0 * d / spot, 4)
    loc.im_mult = round(d / im, 4) if im else None
    want = ORCS_WING_USD                       # r207: dollars, not a fraction of spot; r234: x CONTRACT_SCALE
    wings = [(abs(abs(kk - k) - want), kk, c) for _d, kk, c in otm
             if (kk < k if side == "put" else kk > k) and mark_of(c) is not None]
    if not wings:
        loc.why, loc.why_key = f"no quoted strike beyond {k:g} for the long leg", f"{side}_long"
        return loc
    _x, kk, long_c = min(wings, key=lambda x: (x[0], abs(x[1] - k)))   # r234: a tie goes to the NARROWER wing, both sides
    ms, ml = mark_of(short), mark_of(long_c)
    if ms is None:
        loc.why, loc.why_key = f"short {k:g} has no quote", f"{side}_credit"
        return loc
    loc.long, loc.width = long_c, round(abs(kk - k), 4)
    loc.credit = round(ms - ml, 4)
    sb, la = safe_float(getattr(short, "bid", None)), safe_float(getattr(long_c, "ask", None))
    loc.natural = round(sb - la, 4) if sb is not None and la is not None and la > 0 else None
    return loc


class ORCSPreparation:
    __slots__ = ("tick", "im", "atm", "sides", "ready", "why")

    def __init__(self, tick):
        self.tick = tick
        self.im = self.atm = None
        self.sides = {}
        self.ready = []           # sides whose every gate passed this tick and are not yet taken
        self.why = ""


def _checks():
    per = ("short", "long", "delta", "dist_pct", "im_mult", "width", "credit", "credit_natural",
           "credit_pct_width", "ready", "taken")
    return tuple(f"{s}_{p}" for s in SIDES for p in per)


class ORCSPlan:
    name = NAME
    PLAN_CHECKS = ("entry_window", "price", "zero_dte", "gap_abs_pct", "implied_move", "im_pct", "atm_straddle", "atm_strike",
                   "or_width_pct", "vix") + _checks()

    def __init__(self, store=None):
        self.planner = Plan(self.name, self.PLAN_CHECKS, self_ledgers=True)
        self._store = store

    def prepare(self, *, price_now, now_et, chain=None, gap=None, informers=None,
                today: str = "", taken=()) -> ORCSPreparation:
        """Locate both spreads. `taken` names the sides already entered this session (the strategy's
        read of trades.db); a taken side is recorded and is not ready again."""
        t = self.planner.tick(price_now)
        prep = ORCSPreparation(t)
        hm = _hm(now_et)
        if hm is None:                                           # r220: a window that cannot be checked is not open
            t.dormant("entry_window", "the clock could not be read — no trade")
            return prep
        if hm is not None and hm < ORCS_START_ET:
            t.dormant("entry_window", f"before {ORCS_START_ET[0]:02d}:{ORCS_START_ET[1]:02d} ET - dormant")
            return prep
        if hm is not None and hm >= ORCS_END_ET:
            t.dormant("entry_window", f"past {ORCS_END_ET[0]:02d}:{ORCS_END_ET[1]:02d} ET - observing only")
            return prep
        t.check("entry_window", None, True)
        spot = safe_float(price_now)
        if not spot or spot <= 0:
            t.starved("price"); return prep
        t.check("price", spot, True)
        if chain is None:
            t.starved("chain"); return prep

        # ── day gates ────────────────────────────────────────────────────────
        unmet = []
        if not today:
            try:
                today = now_et.strftime("%Y-%m-%d")
            except Exception:                                   # noqa: BLE001
                today = ""
        expiry = str(getattr(chain, "expiry", "") or "")
        zero = bool(today) and expiry == today
        t.check("zero_dte", None, zero, note=f"chain expiry {expiry or 'unknown'}, today {today or 'unknown'}")
        if not zero:
            unmet.append(("zero_dte", f"the chain expires {expiry or 'unknown'}, not today - not a 0DTE session"))
        g = None
        try:
            g = gap.get("gap_abs_pct") if isinstance(gap, dict) else getattr(gap, "gap_abs_pct", None)
            g = safe_float(g)
        except Exception:                                       # noqa: BLE001
            g = None
        t.check("gap_abs_pct", g, None if g is None else g <= ORCS_MAX_GAP_PCT)
        if g is None:
            unmet.append(("gap_abs_pct", "the overnight gap is unmeasured - a gate with no input does not pass"))
        elif g > ORCS_MAX_GAP_PCT:
            unmet.append(("gap_abs_pct", f"overnight gap {g:.2f}% above the {ORCS_MAX_GAP_PCT:.2f}% limit"))
        for k in ("or_width_pct", "vix"):                      # recorded, gating nothing
            t.check(k, safe_float((informers or {}).get(k)), None)

        im, atm = implied_move(chain, spot)
        t.check("implied_move", im, im is not None)
        if im is None:
            t.starved("implied_move"); return prep
        prep.im, prep.atm = im, atm
        t.check("im_pct", round(100.0 * im / spot, 4), None)
        t.check("atm_straddle", straddle_same_strike(chain, spot)[0], None)   # r229: what it read before, recorded
        t.check("atm_strike", atm, None)

        # ── the search, each side ────────────────────────────────────────────
        lines = []
        taken = set(taken or ())
        for side in SIDES:
            loc = locate(side, chain, spot, im)
            prep.sides[side] = loc
            lines.append(loc.line() + (" [taken]" if side in taken else ""))
            t.check(f"{side}_taken", None, None if side not in taken else True)
            if loc.short is not None:
                t.check(f"{side}_short", float(loc.short.strike), True)
                t.check(f"{side}_delta", round(loc.delta, 4), True)
                t.check(f"{side}_dist_pct", loc.dist_pct, None)
                t.check(f"{side}_im_mult", loc.im_mult, True)
            ok = False
            if loc.priced:
                t.check(f"{side}_long", float(loc.long.strike), True)
                t.check(f"{side}_width", loc.width, True)
                rich = loc.credit >= ORCS_MIN_CREDIT and loc.credit < loc.width
                t.check(f"{side}_credit", loc.credit, rich)
                t.check(f"{side}_credit_natural", loc.natural, None)
                t.check(f"{side}_credit_pct_width", round(loc.credit / loc.width, 4) if loc.width else None, None)
                if not rich:
                    loc.why = f"credit {loc.credit:.2f} at mark below the {ORCS_MIN_CREDIT:.2f} floor"
                    loc.why_key = f"{side}_credit"
                ok = rich and not unmet and side not in taken
            elif loc.why_key:
                t.check(loc.why_key, None, False, note=loc.why)
            t.check(f"{side}_ready", None, ok)
            if ok:
                prep.ready.append(side)

        head = "; ".join(lines) + f" (implied move {im:.2f})"
        if unmet:
            gate, why = unmet[0]
            prep.why = why
            t.refuse(gate, f"{why}. Located: {head}")
            return prep
        if not prep.ready:
            first = next((l for s_, l in prep.sides.items() if l.why_key and s_ not in taken), None)
            if first:
                prep.why = first.why
                t.refuse(first.why_key, f"{first.why}. Located: {head}")
            else:
                prep.why = "both sides taken" if taken else "no side ready"
                t.hold(f"{prep.why} - defended as a condor. {head}")
            return prep
        t.direction = "neutral"
        from strategy import plan_state as _ps, observe as _obs   # r303: TAKE only when it will trade
        t.hold(f"READY at the mark, to the entry ladder: {', '.join(prep.ready)}. {head}",
               verdict=("TAKE" if _ps.state("OpeningRangeCreditSpread") == _ps.ACTIVE else _obs.LOG_ONLY))
        return prep
