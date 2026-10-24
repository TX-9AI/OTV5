"""
strategy/orb_strategy.py  v4.9
v4.9  2026-09-24  OTV4TEST r131 — COMMENT ONLY. The GATES note described the retest body as
      `body_low >= orb_high`; analysis/orb_engine.py v4.15 makes it STRICT (operator:
      "if the very next candle opens on the range and moves away that's not a retest")
      and never lets the break bar be its own retest. No code here changes.
v4.8  2026-09-22  OTV4TEST r91 — the signal carries `entry_delta` from
      `contract.delta`, the sizing input the structural stop needs to convert
      |entry - impulsive candle extreme| into premium. Read from the contract,
      never re-derived; the same attribute main.py already writes to the row.
v4.7  2026-09-13  OTV4TEST r20 — THE ORB KNOWS NOTHING ABOUT LEVELS. Operator:
      "I want levels taken out of the orb trade entirely — that was to prevent
      fake-outs, but proved ineffective for the task." The same ruling he gave
      mainline at r365. SIX EXCISIONS: the `LiquidityMap` import, the `liq_map`
      parameter, the `_analyze_liquidity` call and the 88-line method, every
      consumer of its result (the pool-in-path note, the named-level confluence
      and the `conviction += 0.15` riding on it, the path-clear and unnamed-
      cluster notes, the target-adjusted note), and `break_level`, whose only
      consumer was that method. 407 lines to 305; pyflakes reports zero
      undefined names and no new warning.
      🔑 MEASURED BEFORE REMOVAL, AND INERT HERE WHERE IT WAS NOT ON MAINLINE.
      There a pool just beyond the TP re-derived the CONTRACT through the global
      strike increment, firing on 10 of 115 ORB trades (8.7%%). Here OTV4TEST r2
      had already moved strike selection into `orb_plan`, so `contract` comes
      from `prep` and no pool has touched it since; Rule 3's target adjustment
      was explicitly RECORDED, NOT APPLIED since r193; and `signal.conviction`
      has NO READER in the decision path (main.py: "DO NOT REINTRODUCE A
      CONVICTION GATE", pinned by tests/check_conviction_removed.py). What
      changes is notes and one log line.
      ⚠️ THE PARAMETER IS REMOVED, NOT IGNORED, so a caller still passing
      `liq_map` raises rather than being silently disregarded — mainline's r365
      found exactly that hiding in a test harness that DRIVES the function while
      three source-shape gates stayed green.
v4.6  2026-09-08  OTV4TEST r2 — THE STRATEGY IS THE SPEC; THE PLAN SELECTS.
      Agreed with the operator part by part on 2026-09-08 (PLAN_SPEC §29).
      `generate_signal()` no longer touches the chain, picks a strike, prices
      a contract or reads ATR: it asks `strategy/orb_plan.py` for this tick's
      preparation and fires ONLY when every declared bar is met, with the
      plan's stop, strike, contract, premium and floor. What moved out:
      `get_chain_fetcher().select_orb_strike(...)` (now `orb_plan.select_contract`,
      parity-pinned), the target/50% arithmetic (the engine's own numbers are
      read, never recomputed), and the plan row (the plan writes it every tick
      from 09:35, both sides priced, so "why did ORB not fire" has an answer
      before the retest rather than after). DELETED BY RULING: the ATR floor
      (`ORB_ATR_FLOOR_PCT`) — "makes no sense" for this setup; ORB has no ATR
      read. The liquidity/VWAP/Fed-day items stay as NOTES on the signal (r193:
      recorded, never gating). New kwargs `now_hhmm` and `offer_working` are
      the two facts only main.py knows. `self.planner` is still the same Plan
      object, now owned by the ORBPlan, so W2 and the board see no change.
v4.5  2026-09-04  r235 — 🔴 THE GATE ASKS "HAS THIS CONFIRMATION
      FIRED", NOT "HAS ANY". `confirmation_spent()` is EXTRACTED to module
      level so the checker drives it rather than a copy (C.23). `>=` not `==`,
      so an out-of-order restore fails SHUT; and the `_c > 0` guard means the
      latch does not depend on the state gate for its correctness.
v4.4  2026-09-01  r207 — ONE CONFIRMATION, ONE ORDER, AND THE GEOMETRY COMES
      FROM THE ENGINE. This file gated on `orb.state` ALONE, so anything
      holding an OPEN_* object fired every tick it was asked. On 2026-09-01
      QQQ took two ORB shorts off one confirmation because main.py held a
      stale ORBData across the manage→entry seam and this gate had nothing
      else to say no with. It now refuses a confirmation whose
      `order_placed` latch is set, which is true in paper and live alike.
      The signal also carries `orb_stop_distance_px` — the boundary-to-wick
      distance frozen at the break — so the sizer stops recomputing it from
      the live price at the entry seam.
v4.3  2026-08-30  r193 — POOL IN PATH IS RECORD-ONLY. A named pool within
      BEYOND_TP_ADJUSTMENT_WIDTHS past the 100% target used to PULL the
      target to that pool. Operator's ruling: record it, do not let it move
      the trade. Detection, the counted clusters and the notes all stay, so
      the effect can be studied later; the target is now the pure measured
      move. ⚠️ The pull was a grading-era survivor that CHANGED WHAT THE
      TRADE DOES while reading like an annotation.
v4.2  2026-08-26  r146 — RECORDED THROUGH THE PLAN, ZERO HURDLES. Operator,
      2026-08-26: *"Include orb in that, zero hurdles."* The three refusals
      this file makes AFTER the engine confirms (no contract, zero premium,
      ATR below the reachable floor) and the fire itself now write a
      plan_tick row through `self.planner` (strategy/plan.py, `record_only`).
      ⚠️ NOTHING GATES. `executable()` is never called on this plan; no R
      hurdle, no geometry, no window is applied to ORB. The 2026-08-25 ruling
      — *"leave orb alone. That one can't get encumbered with extra hurdles"*
      — stands; this is narration of decisions the file already made, so
      "why did ORB not fire this morning" has an answer in the table. The
      engine-state-not-confirmed case is recorded by main.py, which is the
      only place that knows the engine was not asked.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).


v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

strategy/orb_strategy.py — ORB break-and-retest signal generation.
v3.0 — original release
populate orb_range_high/low on signal so exit_engine
        can apply strategy-aware ORB stop logic
update state check for orb_engine v1.1 rename:
        CONFIRMED_LONG/SHORT -> OPEN_LONG/SHORT
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
⬛ SUPERSEDED 2026-09-13 (OTV4TEST r20) — THE THREE RULES BELOW ARE GONE AND
THIS FILE READS NO LEVELS AT ALL. Operator: "I want levels taken out of the orb
trade entirely — that was to prevent fake-outs, but proved ineffective for the
task." Kept, struck, per the r240 precedent: a rule a later ruling contradicts
is a wrong answer rather than history, and this is WHY the ORB looked as it did
for the whole of v3 and v4. Rule 2 was already record-only from r193; Rule 3's
target adjustment was recorded and never applied here; Rule 1's confluence
carried a conviction bump that nothing in the decision path read.
Liquidity-aware ORB logic:
RULE 1 — Named level IS the break level (catalyst, not obstacle):
  If the ORB high/low sits within 0.15% of a named pool (PDH, PDL, session H/L),
  and the break direction is THROUGH that level, this is a high-quality setup.
  The sweep of that level IS the ORB catalyst. Add confluence, don't penalize.
RULE 2 — Named level in path between entry and 50% TP (hard reduce):
  A named pool sitting between entry and the trail-activation level is a known
  reversal zone. Require at least one extra confluence factor, OR block.
RULE 3 — Named level just beyond 100% TP (adjust target, don't block):
  If a named pool sits within 0.5 ORB-widths past the 100% TP, move the target
  to that pool price rather than projecting past it.
v-namelevels (2026-07-28) — the liquidity gate NAMES the levels it blocks on.
        Was: "Named pool in fakeout zone (entry->50%TP): 1 named level(s)." — a bare
        count, unauditable. On 2026-07-28 this gate held the AVGO ORB short for SIX
        consecutive ticks (13:42:15 -> 13:43:30, 90s) starting the same tick the
        retest confirmed; the trade finally filled at 372.11 — 1.4pt below the
        confirmation and 0.5pt off the absolute low — then reversed and stopped out
        (-$135.50). The block never said WHAT it blocked on. Now logs name@price for
        every pool in the fakeout zone plus entry/50%TP/direction, and carries
        named_in_path_detail / unnamed_in_path_detail on the result for callers.
        NOTE: this is OBSERVABILITY ONLY — the gate behaviour is unchanged. What the
        block SHOULD do (skip / trade-to-pool / enter reduced) is still open.
"""

import logging
from typing import Optional

from strategy.base_strategy import BaseOptionsStrategy, OptionsSignal
# ⚠️ `_n` renders an absent value as "n/a" and never raises — the ORB sequence
# below prints levels that can legitimately be None before the range forms.
from strategy.orb_plan import ORBPlan
from analysis.orb_engine import ORBData
from analysis.market_state import MarketState
from analysis.volatility_engine import VolatilityState
from data.options_chain import OptionsChain
from data.macro_data import MacroSnapshot
from config import FED_DAY_ORB_BOOST, MAX_LOSS_PCT

logger = logging.getLogger(__name__)

# OTV4TEST r2 — `ORB_ATR_FLOOR_PCT` IS DELETED BY RULING (operator, 2026-09-08:
# the ATR floor "makes no sense" for this setup). It was the runaway's
# reachability study (0.05% ATR) glued onto ORB as a feasibility veto at r36;
# the range width and the impulsive candle already say what the tape is doing.
# The runaway keeps its own floor; this strategy has no ATR read at all.

# ── GATE CATEGORIES AS DATA (WA §36) ───────────────────────────────────────
# ⚠️ ORB HAS NO SELECTION GATES AND THEREFORE NOTHING TO RELAX. Every condition
# is either the setup itself or a veto. That is why it does not import
# `relaxed` - and why the relaxed toggle cannot loosen the one strategy with a
# positive record. **The break and retest are the trade; there is no worse
# version of them to fire on.**
GATES = {
    # OTV4TEST r2 — no FEASIBILITY entry: the ATR floor is deleted (above).
    # FOUNDATIONAL, all tested inline with no knob:
    #   the ORB engine armed (a break AND a retest: a LATER bar's wick touches or
    #     enters the range, body STRICTLY outside - `low <= orb_high and
    #     body_low > orb_high` (r131); the break bar is never its own retest)
    #   direction from the ORB state
    #   this confirmation has not already produced an order (r207/r235)
    #   the liquidity path to target is a NOTE, not a gate (r193)
}

BREAK_LEVEL_PROXIMITY_PCT   = 0.0015
NAMED_IN_PATH_ORB_WIDTHS    = 1.5
BEYOND_TP_ADJUSTMENT_WIDTHS = 0.5


def confirmation_spent(orb) -> bool:
    """Has THIS confirmation already produced an order?

    🔴 r235 — EXTRACTED SO THE CHECKER DRIVES IT AND NOT A COPY (C.23). As
    an inline comparison it was untestable, and a test that re-implements the
    arithmetic it pins tests itself — the r181 sizing checker stayed green for
    two days doing exactly that.
    ⚠️ `>=`, NOT `==`. If a seq were ever restored out of order from a
    persisted snapshot, `==` would fail OPEN and re-fire; `>=` fails shut.
    ⚠️ AND `_c > 0` MATTERS: before any confirmation both are 0, and 0 >= 0
    would refuse a setup that has never fired. The state gate already blocks
    that case, but a latch that depends on ANOTHER gate for its correctness is
    one refactor away from being wrong.
    """
    _c = int(getattr(orb, "confirmation_seq", 0) or 0)
    _o = int(getattr(orb, "order_placed_seq", 0) or 0)
    return _c > 0 and _o >= _c


def _confirmed_epoch(orb) -> float:
    """`confirmed_at` as an epoch, or 0.0. Never raises: this feeds an
    observation, and an observation must not break an entry."""
    raw = str(getattr(orb, "confirmed_at", "") or "").strip()
    if not raw:
        return 0.0
    try:
        from datetime import datetime as _dt
        return _dt.fromisoformat(raw).timestamp()
    except Exception:                                          # noqa: BLE001
        return 0.0


class ORBStrategy(BaseOptionsStrategy):
    """
    Opening Range Breakout strategy.
    ⚠️ KNOWS NOTHING ABOUT LEVELS (r20, operator's ruling). It reads no pool, no
    ladder and no fork rail; the break, the retest and the plan's contract are
    the whole trade.
    """

    # RECORD ONLY. ORB opens its own plan_ledger rows (main.py's open_plan
    # calls stand), so `self_ledgers=True`; `record_only=True` documents that
    # its verdict is never consulted.
    # 🔴 THE WHOLE ORB SEQUENCE IS RECORDED, NOT JUST THE STATE LABEL (r153).
    # Operator, 2026-08-27: *"I want the entire ORB sequence writing to the per
    # tick log."*
    # ⚠️ WHAT WAS WRONG: the plan wrote one line — "ORB engine is
    # WAITING_FOR_BREAK/ARMED_SHORT/EXPIRED" — and nothing about the GEOMETRY
    # that produced it. UNH on 2026-08-27 logged 70 ticks ARMED_SHORT and one
    # TAKE, with no record of where the break was, how deep the retest went, or
    # what the engine was waiting for. When the operator sees a qualifying
    # break+retest on the chart and the bot does not take it, the table could
    # not say why. Every field below already exists on ORBData and was simply
    # never read.
    PLAN_CHECKS = ORBPlan.PLAN_CHECKS      # declared once, on the plan (r2)

    def __init__(self):
        # OTV4TEST r2 — the plan owns the row, the chain and the selection.
        # `self.planner` is kept as the same object so every reader that
        # asks a strategy for its Plan (check_plan_wiring W2, the board)
        # finds it where it always was.
        self.plan = ORBPlan()
        self.planner = self.plan.planner

    @property
    def name(self) -> str:
        return "ORBStrategy"

    def generate_signal(self,
                        orb: ORBData,
                        ms: MarketState,
                        vol_state: VolatilityState,
                        chain: OptionsChain,
                        macro: MacroSnapshot,
                        current_price: float,
                        now_hhmm: str = "",
                        offer_working: bool = False) -> Optional[OptionsSignal]:
        """THE SPEC. Fire when every bar the plan reports is met — and only
        with the plan's variables. This function selects nothing.

        OTV4TEST r2 — the bars (PLAN_SPEC §29.2), all read off `prep`:
          1. an impulsive candle exists and is not invalidated (ARMED_*)
          2. a retest bar has closed (OPEN_*)
          3. this confirmation has not already produced an order
          4. a contract with a live quote exists at the 100% target strike
        Nothing else. No R hurdle, no geometry, no ATR, no confluence gate.
        `ms`, `vol_state` and `macro` are read for NOTES on the signal only
        (they gate nothing and may be None). ⚠️ `liq_map` IS GONE (r20) — not
        ignored, REMOVED from the signature, so a caller still passing it fails
        loudly instead of being silently disregarded.
        """
        prep = self.plan.prepare(orb=orb, chain=chain, price_now=current_price,
                                 now_hhmm=now_hhmm, offer_working=offer_working)
        if not prep.ready or prep.structural or prep.starved:
            return prep.tick.already()

        t = prep.tick
        direction, option_side, contract = prep.direction, prep.side, prep.contract
        target_100, target_50 = prep.target_100, prep.target_50

        signal = OptionsSignal(
            strategy_name     = self.name,
            setup_type        = f"ORB {direction.title()}",
            direction         = direction,
            option_side       = option_side,
            underlying_entry  = current_price,
            underlying_stop   = prep.stop,          # the impulsive candle's extreme
            underlying_target = target_100,
            underlying_tp50   = target_50,
            orb_range_high    = prep.orb_high,
            orb_range_low     = prep.orb_low,
            # r207 — FROZEN AT THE BREAK, not recomputed at the fill; record only.
            orb_stop_distance_px = float(getattr(orb, "stop_distance_px", 0.0) or 0.0),
            orb_break_ts      = _confirmed_epoch(orb),
            atr_at_signal     = float(getattr(vol_state, "atr", 0.0) or 0.0),
            vix_at_signal     = float(getattr(macro, "vix", 0.0) or 0.0),
            is_fed_day        = bool(getattr(macro, "is_fed_day", False)),
            stop_loss_pct     = MAX_LOSS_PCT,
            tp_pct            = 1.0,
            # 🔴 r91 — THE SIZING INPUT THE 1-R RULE NEEDS. `underlying_stop`
            # above is the impulsive candle's extreme in POINTS; this converts
            # it to PREMIUM so `stop_premium()` can be the structure stop
            # rather than a flat 25%. Same attribute `main.py` already reads
            # when it writes `entry_delta` to the row — read here, not
            # re-derived. Missing -> None -> the percentage stop, never a guess.
            entry_delta       = getattr(contract, "delta", None),
            strike            = contract.strike,
            expiry            = getattr(contract, "expiry", ""),
            entry_premium     = prep.premium,
            contract          = contract,
        )

        # ── NOTES — describe the setup; none of them authorises it ─────────
        self._add_confluence(signal, f"ORB break confirmed ({direction})")
        self._add_confluence(signal, "Break+retest pattern (1m body/wick rules)")
        # 🔴 r20 — THE ORB KNOWS NOTHING ABOUT LEVELS. Operator, 2026-09-13:
        # "I want levels taken out of the orb trade entirely — that was to
        # prevent fake-outs, but proved ineffective for the task." Same ruling
        # he gave mainline at r365. What stood here: the `_analyze_liquidity`
        # call, the pool-in-path note, the named-level confluence and the
        # `conviction += 0.15` that rode on it, the path-clear and unnamed-
        # cluster notes, and the target-adjusted note.
        # 🔑 MEASURED BEFORE REMOVAL, AND IT IS INERT ON THIS FORK, WHICH IS NOT
        # TRUE OF MAINLINE: there, a pool just beyond the TP re-derived the
        # CONTRACT and that branch fired on 10 of 115 ORB trades (8.7%). Here
        # OTV4TEST r2 already moved strike selection into `orb_plan`, so
        # `contract` comes from `prep` and no pool has touched it since; and the
        # only other effect, `signal.conviction`, has NO READER in the decision
        # path (main.py: "DO NOT REINTRODUCE A CONVICTION GATE", pinned by
        # tests/check_conviction_removed.py). Notes and one log line change.
        _vwap = getattr(vol_state, "price_vs_vwap", "") if vol_state is not None else ""
        if direction == "long" and _vwap == "ABOVE":
            self._add_confluence(signal, "Above VWAP — bullish bias")
        elif direction == "short" and _vwap == "BELOW":
            self._add_confluence(signal, "Below VWAP — bearish bias")
        if getattr(macro, "is_fed_day", False):
            self._add_confluence(signal, f"Fed day: {getattr(macro, 'fed_event_name', '')} "
                                         f"(+confluence)")
            signal.conviction += FED_DAY_ORB_BOOST
        signal.adx_at_signal = float(getattr(ms, "adx", 0.0) or 0.0) if ms is not None else 0.0
        signal.flat_angle_deg = float(getattr(ms, "flat_angle_deg", 0.0) or 0.0) if ms is not None else 0.0

        logger.info(
            f"🎯 ORB SIGNAL {direction.upper()}: underlying={current_price:.2f} "
            f"orb={prep.orb_low:.2f}–{prep.orb_high:.2f} width={prep.width:.2f} "
            f"option={option_side.upper()} {contract.strike} mark=${prep.premium:.2f} "
            f"delta={float(getattr(contract, 'delta', 0.0) or 0.0):.3f} "
            f"stop={prep.stop:.2f} floor={prep.floor_premium:.2f} target={target_100:.2f} "
            f"size~{prep.size_provisional} (restated at the fill) "
            f"confluence={signal.confluence_factors}"
        )
        return t.take(signal)

