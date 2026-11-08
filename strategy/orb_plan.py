"""
strategy/orb_plan.py  v5.1
v5.1  2026-11-08  OTV5 r76 (RETIRE.1) — ONLY BREAKOUT'S CONTRACT SELECTOR IS LEFT. The retired ORB trade's plan
      (ORBPlan, ORBPreparation, provisional_size, its gates and window) is removed with the trade; select_contract
      (Breakout's selector, strategy/breakout_plan.py) and the two values it reads are unchanged byte for byte.
      The opening-range ENGINE (analysis/orb_engine.py) was never this plan and is untouched. The operator,
      2026-11-07: "Running dead code and logging dead code activity is unnecessary drag. Yes, I want all of those
      things fixed."
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
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

      THE FOUR ROW STATES (the predecessor's FORK_BRIEF §3.5, not carried in this tree):
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

import config
from data.options_chain import two_sided                       # ZBID.1 (r186)

logger = logging.getLogger(__name__)

# ── GATE CATEGORIES AS DATA (WA §36) — the selector refuses on feasibility only.
GATES = {
    "QUOTE_FLOOR": "FEASIBILITY",     # a contract with no live quote cannot fill
}

# ── declared values the search reads (PLAN_SPEC §29.3) ─────────────────────
QUOTE_FLOOR        = 0.05          # carried from select_orb_strike — NOT RULED
DELTA_BIAS         = getattr(config, "ORB_STRIKE_DELTA_BIAS", "lower")   # carried — NOT RULED


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
