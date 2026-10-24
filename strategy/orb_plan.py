"""
strategy/orb_plan.py  v1.12
v1.12  2026-10-19  OTV4TEST r303 (PSTATE.1) — the ORB trade's state is strategy/plan_state.py's: OT_ORB_TRADE=active|log|off
      ("1" still = active). LOG evaluates and records the fire LOG-ONLY. The opening-range ENGINE is not this plan.
v1.11  2026-10-06  OTV4TEST r259 (STRK.2) — select_contract gains keyword `inside` (default False: every
       existing caller is unchanged, and the default rule still mirrors select_orb_strike, check_orb_plan
       P4). inside=True considers only strikes AT or INSIDE the reach - at/below it for a long call,
       at/above it for a short put - then the nearest of those, same tie rule. Breakout passes it on a
       cash index: the operator, 2026-10-06 20:41 ET, "at or inside target" (SPX-TEST's 10:08 long bought
       the 7845C for a 7842.79 reach). tests/check_brk_strike_inside.py.
v1.10  2026-10-03  OTV4TEST r220 (TIME.1) — its private HH:MM parser is utils.time_utils.parse_hm (eight plans carried the same copy), and an UNREADABLE clock is DORMANT - no trade - instead of skipping the window check.
v1.9  2026-10-02  OTV4TEST r187 (ROSTER.1) — THE ORB TRADE IS RETIRED BY DEFAULT.
      prepare() still narrates the engine every tick, then goes DORMANT at gate
      `enabled` unless OT_ORB_TRADE is the literal "1" (read at CALL time).
      BRT.1 (10-01): "retire the orb ... The five minute opening range will
      always serve as our session reference point" - the ENGINE is untouched
      and select_contract (Breakout's selector) is untouched. The operator,
      2026-10-02 21:05 ET: "2. CONCUR". Pinned by check_trade_switches.
v1.8  2026-10-02  OTV4TEST r186 (ZBID.1) — `select_contract` (ORB and Breakout) refuses a contract
      with no bid: data.options_chain.two_sided beside the QUOTE_FLOOR, whose
      FEASIBILITY reason - "a contract with no live quote cannot fill" - a
      no-bid contract met only because its mark IS its ask. The AAL chain
      of 2026-10-02 (P11.5 0.00/0.22) is pinned by check_zero_bid_refused Z6.
v1.7  2026-10-02  OTV4TEST r185 (LADR.1) — BOTH CANDIDATES TARGET THE RAW 100%
      PROJECTION and `select_contract` takes the nearest LISTED strike; the
      pre-round on config.STRIKE_INCREMENT (one table number per symbol, 18
      of them wrong) is gone, and so is the constant, which nothing else
      read. On a $1 ladder that equals the snapped value except at an exact
      half-dollar target, where the tie now breaks by DELTA_BIAS as the
      docstring always said instead of by Python's round-half-even.
v1.6  2026-09-26  OTV4TEST r148 (WIN.1) — reads its entry window from config with NO literal fallback (one table, config.ENTRY_WINDOWS); a missing name now fails at import instead of silently defaulting. Value unchanged.
v1.5  2026-09-24  OTV4TEST r131b — A REFUSED BREAK IS NAMED ON THE ROW. Operator,
      2026-09-24: "The stop should be inside the opening range to be a valid
      set up." analysis/orb_engine.py v4.15 refuses a break candle whose
      range-side extreme printed outside the range and records why in
      `break_refusal`; the WAITING HOLD row now carries it ("last candidate
      REFUSED: ..."). No decision here changes. Pinned by check_orb_reentry V3.
v1.4  2026-09-24  OTV4TEST r131 — THE RUNAWAY REFUSAL NAMES WHAT RE-OPENS IT.
      Operator, 2026-09-24: *"A close back into the range is a new opportunity
      full stop."* analysis/orb_engine.py v4.14 re-arms a runaway on the first
      1m close back inside the range, so the `consequence` refusal ("ORB is
      finished on THIS break") now lasts only while price is out there, and
      its text says what ends it. The plan still reads the engine's answer and
      decides nothing itself; after the re-arm it HOLDs on "impulsive candle"
      like any WAITING_FOR_BREAK tick. Pinned by check_orb_reentry R5.
v1.3  2026-09-23  OTV4TEST r118 — THE PITCHFORK LEAVES THE ORB TRADE. The operator,
      2026-09-23: "nothing about the pitchfork needs to be addressed inside the
      ORB trade." The three fork stamps on the prepared row are removed:
      `tine_to_target`, the r103 `rail_context` block and `fork15`. All were
      record-only (verdict None), so no ORB decision changes. MEASURED on this
      box's plan_check before removal: anchor_fork15 0 of 114 rows ever held a
      value (the ForkEngine builds no 15m frame); anchor_tine_to_target 8 of
      114; the ten anchor_rail_* fields 36 rows, only `rail_fork_built`
      populated. VWAP distance and the boundary's aggressor share stay.
v1.2  2026-09-22  OTV4TEST r103 - records the rail projection beside
      `tine_to_target`, which has banked None on every row because
      `nearest_tine` read the ledger r19 empties.
v1.1  2026-09-09  OTV4TEST r12 — anchors stamped on the prepared row (record only):
      VWAP distance, aggressor share at the boundary, nearest tine to the target, 15m fork.
v1.0  2026-09-08  OTV4TEST r2 — THE ORB PLAN. Agreed with the operator on
      2026-09-08, one part at a time (PLAN_SPEC §29). The plan holds the
      chain and selects; the strategy holds nothing but its bars and fires.

      WHAT THE PLAN PROVIDES, AND WHEN:
      · from the first tick after the 09:30 five-minute bar closes — BOTH
        candidate contracts: the call at the long 100% target
        (orb_high + width) and the put at the short one (orb_low - width),
        each the nearest listed strike with a live quote, re-priced every
        tick. Everything but direction.
      · from the first tick after the impulsive candle closes — one side:
        the stop (that candle's LOW for a long / HIGH for a short, body or
        wick), the 100% and 50% levels, the one contract, its premium, the
        25% floor premium, and the PROVISIONAL size off boundary-to-stop.
        The strategy is holding a ready-to-fire trade at least one full 1m
        bar before a retest can exist.
      · the strategy fires the tick after the retest bar closes; the only
        thing computed at that instant is the size restated off the FILL
        (main.py's sizer, unchanged — operator 2026-09-01: the risk is
        entry-to-stop).

      DECONFLICTION IS THE PLAN'S. A high break and a low break are both
      candidates until the impulsive candle prints; only one 1m bar can open
      inside the range and close outside it on one side, so the candle
      resolves it and the plan hands the strategy exactly one prepared trade
      or nothing. After a close back inside the range both sides re-open.

      AFTER A TRADE RESOLVES (PLAN_SPEC §29.6) the ENGINE already decides —
      r221/r228 — and the plan reads its answer: 50% accepted -> runaway owns
      it; past 11:30 -> expired; last close inside -> re-entry, fresh candle
      needed; otherwise the ORIGINAL impulsive candle stands and the plan
      re-issues the same stop, strike and floor for the next retest.

      THE FOUR ROW STATES (docs/FORK_BRIEF.md §3.5):
        NO PLAN  — starved: no opening range, no chain
        HOLD     — "none available" is a DECLINE at gate `contract`; a
                   range with both sides priced holds "waiting on: impulsive
                   candle"; an armed side holds "PREPARED — … waiting on:
                   retest" (= setup selected, only the trigger remains)
        DECLINE  — a bar refused, named, with the gap: confirmation spent,
                   standing offer working, no contract at the strike
        DORMANT  — past the 11:30 cutoff / engine EXPIRED

      CARRIED FROM `select_orb_strike`, NOT RULED: the `mark > 0.05` quote
      floor and the lower-|delta| tie-break (`config.ORB_STRIKE_DELTA_BIAS`).
      Both are declared here as values so the search can read them and a
      later ruling changes one number. `check_orb_plan.py` P4 pins parity
      with `select_orb_strike` on the same chain, so what this selects is
      what e955020 selected.

      ⚠️ ZERO HURDLES STANDS. No R hurdle, no geometry, no ATR, no window
      beyond the engine's own cutoff is applied. `executable()` is never
      called. The plan narrates and selects; it refuses only on the bars the
      strategy declares.
"""
from __future__ import annotations

import logging
import os

import config
from analysis.orb_engine import ORBState
from strategy.plan import Plan, _n
from data.options_chain import two_sided                       # ZBID.1 (r186)

logger = logging.getLogger(__name__)

# ── GATE CATEGORIES AS DATA (WA §36) — the plan refuses on the STRATEGY's bars
#    only; nothing here is relaxable and `relaxed` is not imported.
GATES = {
    "QUOTE_FLOOR": "FEASIBILITY",     # a contract with no live quote cannot fill
    "CUTOFF_ET":   "FOUNDATIONAL",    # the engine's own window; r176: never relaxed
}

# ── declared values the search reads (PLAN_SPEC §29.3) ─────────────────────
CUTOFF_ET          = config.ORB_NO_ENTRY_AFTER_ET     # r148: no literal fallback
WINDOW_OPEN_ET     = config.ENTRY_OPEN_ET   # r148: no literal fallback      # the range exists from here
MAX_LOSS_PCT       = float(getattr(config, "MAX_LOSS_PCT", 0.25))       # the 25% floor
QUOTE_FLOOR        = 0.05          # carried from select_orb_strike — NOT RULED
DELTA_BIAS         = getattr(config, "ORB_STRIKE_DELTA_BIAS", "lower")   # carried — NOT RULED
BUDGET_USD         = float(getattr(config, "ORB_BUDGET_USD", 0.0) or 0.0)
CONTRACT_MULT      = int(getattr(config, "CONTRACT_MULTIPLIER", 100))


from utils.time_utils import parse_hm as _hhmm    # r220 (TIME.1): the one parser


def select_contract(chain, direction: str, target_strike: float, *, inside: bool = False):
    """Nearest listed strike to the target with a live quote; equidistant
    strikes break toward the lower |delta| (DELTA_BIAS="lower") or higher.
    ⚠️ SAME RULE AS `OptionsChainFetcher.select_orb_strike` (data/options_chain.py)
    — pinned by check_orb_plan P4. Reads only fields on OptionContract:
    strike, mark, delta (check_attr_fidelity)."""
    if chain is None or target_strike is None:
        return None
    contracts = chain.calls if direction == "long" else chain.puts
    cands = [c for c in (contracts or []) if float(getattr(c, "mark", 0) or 0) > QUOTE_FLOOR
             and two_sided(c)]                                  # ZBID.1 (r186)
    if inside:
        # r259 (STRK.2) — never a strike PAST the reach: at/below it for a call, at/above for a put.
        _t = float(target_strike) + (1e-6 if direction == "long" else -1e-6)
        cands = [c for c in cands if (float(c.strike) <= _t if direction == "long" else float(c.strike) >= _t)]
    if not cands:
        return None
    dist = min(abs(float(c.strike) - float(target_strike)) for c in cands)
    nearest = [c for c in cands if abs(float(c.strike) - float(target_strike)) <= dist + 1e-6]
    if len(nearest) == 1:
        return nearest[0]
    key = lambda c: abs(float(getattr(c, "delta", 0) or 0))          # noqa: E731
    return min(nearest, key=key) if DELTA_BIAS == "lower" else max(nearest, key=key)


def provisional_size(width: float, distance: float, premium: float,
                     budget_usd: float = BUDGET_USD) -> int:
    """floor(width / distance), min 1, degenerate -> 1, capped by the ORB
    budget. MIRRORS `RiskManager._size_geometry` (risk/risk_manager.py) —
    pinned by check_orb_plan P9 — so the row shows the count the sizer will
    produce for a fill at the boundary. The sizer re-runs it off the FILL."""
    cost = float(premium or 0.0) * CONTRACT_MULT
    if cost <= 0:
        return 0
    by_budget = int(budget_usd // cost) if budget_usd > 0 else 10 ** 9
    if by_budget < 1:
        return 0
    if width > 0 and 0 < distance <= width * 1.0001:
        return min(max(1, int(width // distance)), by_budget)
    return 1


class ORBPreparation:
    """What the plan hands the strategy each tick — never executable by itself."""
    __slots__ = ("tick", "state", "direction", "side", "orb_high", "orb_low", "width",
                 "target_100", "target_50", "stop", "boundary", "target_strike",
                 "contract", "premium", "floor_premium", "size_provisional",
                 "candidates", "waiting_on", "consequence", "structural", "starved",
                 "ready")

    def __init__(self, tick):
        self.tick = tick
        self.state = ""
        self.direction = self.side = ""
        self.orb_high = self.orb_low = self.width = 0.0
        self.target_100 = self.target_50 = self.stop = self.boundary = None
        self.target_strike = None
        self.contract = None
        self.premium = self.floor_premium = None
        self.size_provisional = 0
        self.candidates = {}          # "long"/"short" -> (target_strike, contract)
        self.waiting_on = ""
        self.consequence = ""
        self.structural, self.starved = [], []
        self.ready = False

    def trade_line(self) -> str:
        c = self.contract
        if c is None:
            return "no trade prepared"
        return (f"buy {float(c.strike):g}{self.side[0].upper()} @ {_n(self.premium)}  "
                f"stop {_n(self.stop)} (impulsive candle "
                f"{'low' if self.direction == 'long' else 'high'})  "
                f"floor {_n(self.floor_premium)} (-{MAX_LOSS_PCT:.0%} premium)  "
                f"100% {_n(self.target_100)}  50% {_n(self.target_50)}  "
                f"size {self.size_provisional} provisional "
                f"(width {self.width:.2f} / boundary-to-stop "
                f"{_n(abs((self.boundary or 0) - (self.stop or 0)))}; restated at the fill)")


class ORBPlan:
    """Owns the chain search and the row. Registered as "ORBStrategy" so the
    board, the readers and the ledger see one strategy, as before."""
    name = "ORBStrategy"

    PLAN_CHECKS = ("engine_state", "entry_window", "orb_high", "orb_low", "orb_width",
                   "break_direction", "break_close", "bars_since_break",
                   "retest_depth_px", "attempt_number", "stop_level",
                   "target_50pct", "target_100pct", "stop_distance_px",
                   "order_already_placed", "offer_working", "consequence",
                   "long_strike", "long_premium", "short_strike", "short_premium",
                   "target_strike", "contract", "premium", "floor_premium",
                   "size_provisional")

    def __init__(self):
        self.planner = Plan(self.name, self.PLAN_CHECKS,
                            record_only=True, self_ledgers=True)

    # ══════════════════════════════════════════════════════════════════════
    def prepare(self, *, orb, chain, price_now, now_hhmm: str = "",
                offer_working: bool = False) -> ORBPreparation:
        t = self.planner.tick(price_now)
        prep = ORBPreparation(t)
        state = str(getattr(orb, "state", "") or "")
        prep.state = state
        bd = str(getattr(orb, "break_direction", "") or "")

        # ── narrate the sequence first, every tick, whatever the state ──
        t.check("orb_high", getattr(orb, "orb_high", None))
        t.check("orb_low", getattr(orb, "orb_low", None))
        t.check("orb_width", getattr(orb, "orb_width", None))
        t.check("break_direction", 1.0 if bd == "long" else -1.0 if bd == "short" else None)
        t.check("break_close", getattr(orb, "break_candle_close", None))
        t.check("bars_since_break", getattr(orb, "bars_since_break", None))
        t.check("retest_depth_px", getattr(orb, "retest_depth_px", None))
        t.check("attempt_number", getattr(orb, "attempt_number", None))
        t.check("stop_level", getattr(orb, "stop_level", None))
        t.check("stop_distance_px", getattr(orb, "stop_distance_px", None))
        t.check("target_50pct", getattr(orb, "target_50pct", None))
        t.check("target_100pct", getattr(orb, "target_100pct", None))

        # r187 (ROSTER.1): the ORB TRADE is retired by default; r303 (PSTATE.1): plan_state decides, read now
        from strategy import plan_state as _ps
        if _ps.is_dormant("ORBStrategy"):
            t.dormant("enabled", "the ORB trade is RETIRED by the operator's ruling "
                                 "2026-10-02 (BRT.1); OT_ORB_TRADE=active restores it, =log records it")
            return prep

        # ── window: OUTSIDE IT THE PLAN OBSERVES AND DOES NOT WRITE ────
        # Operator, 2026-09-08: *"plans that are outside of their trading
        # window 'observe only, don't write' to keep it from getting cluttered
        # with noise."* `dormant()` writes ONE row on the transition and is
        # silent on every identical tick after it; the engine state above is
        # still read every tick, so the plan is watching, not sleeping.
        hm = _hhmm(now_hhmm)
        if hm is None:                                           # r220: a window that cannot be checked is not open
            t.dormant("entry_window", "the clock could not be read — no trade")
            return prep
        if state == ORBState.EXPIRED or (hm is not None and hm >= tuple(CUTOFF_ET)):
            t.dormant("entry_window",
                      f"past the {CUTOFF_ET[0]:02d}:{CUTOFF_ET[1]:02d} ET ORB cutoff "
                      f"— observing only, no further ORB entries today")
            return prep
        if hm is not None and hm < tuple(WINDOW_OPEN_ET):
            t.dormant("entry_window",
                      f"before {WINDOW_OPEN_ET[0]:02d}:{WINDOW_OPEN_ET[1]:02d} ET — the "
                      f"opening range is forming; observing only")
            return prep
        t.check("entry_window", None, True)

        # ── the range (IL1) ─────────────────────────────────────────────
        hi = float(getattr(orb, "orb_high", 0.0) or 0.0)
        lo = float(getattr(orb, "orb_low", 0.0) or 0.0)
        if state == ORBState.NO_RANGE or hi <= 0 or lo <= 0 or hi <= lo:
            prep.starved.append("opening_range")
            t.starved("opening_range")
            return prep
        prep.orb_high, prep.orb_low = hi, lo
        prep.width = float(getattr(orb, "orb_width", 0.0) or 0.0) or (hi - lo)

        # ── consequences the engine already decided (§29.1 / §29.6) ────
        if state == ORBState.INVALIDATED:
            why = str(getattr(orb, "invalidation_reason", "") or "")
            prep.consequence = why or "invalidated"
            t.check("consequence", None, False)
            if why == "runaway":
                t.refuse("consequence",
                         f"RUNAWAY — a close beyond the 50% {_n(getattr(orb, 'target_50pct', None))} "
                         f"before any retest; ORB is finished on THIS break (hand-off) — "
                         f"a 1m close back inside {lo:.2f}-{hi:.2f} restarts the cycle")
            else:
                t.refuse("consequence",
                         f"RE-ENTRY — a 1m close back inside {lo:.2f}-{hi:.2f}; the "
                         f"impulsive candle is dead, waiting for a fresh one")
            return prep

        # ── one side first (ARMED_* / OPEN_*): direction, anchors, bookkeeping.
        #    A spent confirmation never reaches the chain (r207), so these
        #    bars are read BEFORE any selection and before the chain is needed.
        armed = state in (ORBState.ARMED_LONG, ORBState.ARMED_SHORT)
        confirmed = state in (ORBState.OPEN_LONG, ORBState.OPEN_SHORT)
        if armed or confirmed:
            if not bd:
                prep.starved.append("break_direction")
                t.starved("break_direction")
                return prep
            prep.direction = bd
            prep.side = "call" if bd == "long" else "put"
            t.direction = bd
            prep.boundary = hi if bd == "long" else lo
            prep.stop = float(getattr(orb, "stop_level", 0.0) or 0.0) or None
            prep.target_100 = float(getattr(orb, "target_100pct", 0.0) or 0.0) or None
            prep.target_50 = float(getattr(orb, "target_50pct", 0.0) or 0.0) or None
            if not prep.stop or not prep.target_100:
                miss = [n for n, v in (("stop_level", prep.stop),
                                       ("target_100pct", prep.target_100)) if not v]
                prep.starved.extend(miss)
                t.starved(*miss)
                return prep
            t.anchor(trigger=prep.boundary, invalidation=prep.stop)
            t.check("engine_state", None, confirmed)
            if confirmed:
                from strategy.orb_strategy import confirmation_spent
                cseq = int(getattr(orb, "confirmation_seq", 0) or 0)
                if confirmation_spent(orb):
                    t.refuse("order_already_placed",
                             f"attempt #{getattr(orb, 'attempt_number', '?')}, confirmation "
                             f"#{cseq} has already produced an order — THIS confirmation is "
                             f"SPENT; the next order needs a fresh qualifying retest")
                    return prep
                t.check("order_already_placed", None, True)
                if offer_working:
                    t.refuse("offer_working",
                             "a standing offer is already working for this setup")
                    return prep
                t.check("offer_working", None, True)
        else:
            t.check("engine_state", None, False)

        # ── both candidates, from the range alone (09:35 onward) ───────
        if chain is None:
            prep.starved.append("chain")
            t.starved("chain")
            return prep
        long_k  = round(hi + prep.width, 2)     # LADR.1: raw target; the chain snaps
        short_k = round(lo - prep.width, 2)
        cl = select_contract(chain, "long", long_k)
        cs = select_contract(chain, "short", short_k)
        prep.candidates = {"long": (long_k, cl), "short": (short_k, cs)}
        t.check("long_strike", float(cl.strike) if cl else None, None if cl is None else True)
        t.check("long_premium", float(cl.mark) if cl else None, None if cl is None else True)
        t.check("short_strike", float(cs.strike) if cs else None, None if cs is None else True)
        t.check("short_premium", float(cs.mark) if cs else None, None if cs is None else True)

        if not (armed or confirmed):
            # WAITING_FOR_BREAK / AWAITING_RANGE_REENTRY (and anything unforeseen)
            if cl is None and cs is None:
                t.refuse("contract",
                         f"NONE AVAILABLE — no listed strike with a live quote at "
                         f"{long_k:g}C or {short_k:g}P on this chain (range {lo:.2f}-{hi:.2f}, "
                         f"width {prep.width:.2f})")
                return prep
            re = " (price is outside the range; a fresh candle needs to open inside)" \
                 if state == ORBState.AWAITING_RANGE_REENTRY else ""
            # r131b — a candidate the engine REFUSED (its range-side extreme
            # printed outside the range) is named on the row, not silent.
            _rf = str(getattr(orb, "break_refusal", "") or "")
            if _rf:
                re += f" — last candidate REFUSED: {_rf}"
            prep.waiting_on = "impulsive candle"
            t.hold(f"range {lo:.2f}-{hi:.2f} (width {prep.width:.2f}) — long candidate "
                   f"{_n(cl.strike if cl else None, 'g')}C @ {_n(cl.mark if cl else None)}, "
                   f"short candidate {_n(cs.strike if cs else None, 'g')}P @ "
                   f"{_n(cs.mark if cs else None)}. Waiting on: impulsive candle{re}")
            return prep

        prep.target_strike, prep.contract = prep.candidates[bd]
        t.check("target_strike", prep.target_strike, True)
        if prep.contract is None:
            t.refuse("contract",
                     f"NONE AVAILABLE — no {prep.side} with a live quote at the 100% target "
                     f"strike {prep.target_strike:g} (100% {prep.target_100:.2f})")
            return prep
        c = prep.contract
        prep.premium = float(getattr(c, "mark", 0.0) or 0.0)
        prep.floor_premium = round(prep.premium * (1 - MAX_LOSS_PCT), 4)
        prep.size_provisional = provisional_size(prep.width, abs(prep.boundary - prep.stop),
                                                 prep.premium)
        t.check("contract", float(c.strike), True)
        t.check("premium", prep.premium, prep.premium > 0)
        t.check("floor_premium", prep.floor_premium, None)
        t.check("size_provisional", prep.size_provisional, prep.size_provisional > 0)
        t.debit = prep.premium
        # r12 — ANCHORS, record only (derived/anchors.py): does the boundary's
        # tape lean the break's way. r118 — no pitchfork field here, by ruling.
        from derived import anchors as _A
        _A.stamp(t, vwap_minus_price=(lambda v: None if v is None else v - price_now)(_A.vwap()),
                 aggressor_at_boundary=_A.aggressor_share(prep.boundary))

        if armed:
            prep.waiting_on = "retest"
            t.hold(f"broke {bd} at {prep.boundary:.2f} (attempt "
                   f"#{getattr(orb, 'attempt_number', '?')}, close "
                   f"{_n(getattr(orb, 'break_candle_close', None))}, "
                   f"{getattr(orb, 'bars_since_break', 0)} bars since): PREPARED — "
                   f"{prep.trade_line()}. Waiting on: retest (wick into "
                   f"{lo:.2f}-{hi:.2f}, body outside)")
            return prep
        # every bar clears; the tick stays OPEN for the strategy to take()
        prep.ready = True
        t.note(f"retest confirmed {bd} (attempt #{getattr(orb, 'attempt_number', '?')}, "
               f"confirmation #{int(getattr(orb, 'confirmation_seq', 0) or 0)}): "
               f"{prep.trade_line()}")
        return prep
