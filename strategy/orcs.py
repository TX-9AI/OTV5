"""
strategy/orcs.py  v1.3
v1.3  2026-10-03  OTV4TEST r230 (PREM.5) — EXITS ARE THE CONDOR'S, VERBATIM (the operator, 2026-10-03: "On rolling/defending the ORCS, adopt the condor logic verbatim."). This file still has no exit of its own; the 'held to the close, no stop' wording is superseded (PLAN_SPEC §41.11).
v1.2  2026-10-03  OTV4TEST r211 (PLN.2) — ledger_open(sig): ORCS opens its plan_ledger row immediately before each order
      (it fires without take()), keeping the sibling side's row, so the fill links to the right plan.
v1.1  2026-10-03  OTV4TEST r206 (PREM.3) — THE ENTRY LADDER GOVERNS THE ENTRY. The operator, 2026-10-03: "No, we have a
      ladder for entries. THAT has to govern our entry. 'One cent better' is not even a valid increment
      on most contracts". The signal is priced at the MARK credit of the spread the plan located on THIS
      tick, and the house credit entry prices the order: paper books the mark (limit_ladder.
      paper_fill_credit), live walks the entry ladder. No frozen offer, no fill test here. A side is
      signalled on every ready tick until trades.db shows it entered (an unfilled ladder re-signals -
      the ladder's own doctrine); the plan is told which sides are taken.
      THE v1.0 TEXT BELOW ABOUT AN OFFER "FILLED ON THIS TICK" AND "AT THE LIMIT" IS NO LONGER TRUE.
v1.0  2026-10-03  OTV4TEST r204 (PREM.2) — THE OPENING RANGE CREDIT SPREAD (ORCS), THE STRATEGY (PLAN_SPEC §41).
      The operator, 2026-10-03: "I want to paper trade it Monday... Call this new one the opening range
      credit spread ORCS." And: "we get better than mark or we don't trade it."

      CONFIRMATORY, like every strategy here: strategy/orcs_plan.py locates the strikes, freezes an
      offer one cent better than the mark and watches it; this class turns each offer that FILLED ON
      THIS TICK into one credit-vertical signal priced AT THE LIMIT. It selects nothing itself.
      One spread per side per session: a side with an open ORCS leg, or a session that has already
      entered two, signals nothing (read from trades.db, fails closed).
      EXITS: none of its own. Since r230 its legs are defended as condor legs (exit_engine
      _evaluate_condor_leg, condor_roll) - PLAN_SPEC §41.11. (r204 held them to the close with no stop.)
      OFF unless config.ORCS_ENABLED (OT_ORCS=0 parks the trade; the plan still records).
"""
from __future__ import annotations

import logging

import config
from strategy import orcs_plan as _op

logger = logging.getLogger(__name__)

GATES = {}
NAME = _op.NAME


class OpeningRangeCreditSpread:
    name = NAME

    def __init__(self):
        self.plan = _op.ORCSPlan()
        self.planner = self.plan.planner
        self.PLAN_CHECKS = self.plan.PLAN_CHECKS

    def _side_used(self, side: str) -> bool:
        """True when this side may not be entered: an open ORCS leg on it, or two entered today."""
        try:
            from database.trade_logger import get_trade_logger
            tl = get_trade_logger()
            if tl.count_today(NAME) >= 2:
                return True
            return any(str(r.get("strategy") or "") == NAME and str(r.get("option_side") or "") == side
                       for r in tl.get_open_trades())
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[orcs] side check failed CLOSED for %s: %s", side, exc)
            return True

    def generate_signals(self, *, price_now, now_et, chain=None, gap=None, informers=None,
                         today: str = "") -> list:
        """Zero, one or two condor-leg-shaped signals: one per ready side, priced at the mark."""
        taken = tuple(sd for sd in _op.SIDES if self._side_used(sd))
        prep = self.plan.prepare(price_now=price_now, now_et=now_et, chain=chain, gap=gap,
                                 informers=informers, today=today, taken=taken)
        out = []
        if not prep.ready:
            return out
        if not config.ORCS_ENABLED:
            logger.info("[orcs] %s ready at the mark - the trade is OFF (OT_ORCS=0), recorded only",
                        ", ".join(prep.ready))
            return out
        for side in prep.ready:
            loc = prep.sides[side]
            out.append(self._build_signal(side, loc.short, loc.long, float(loc.credit), float(price_now or 0.0)))
        return out

    def ledger_open(self, sig) -> None:
        """r211 — one plan_ledger row for THIS leg, opened right before it is executed."""
        try:
            t = self.planner.tick(getattr(sig, "underlying_entry", None), getattr(sig, "option_side", ""))
            sh = getattr(sig, "short_put_contract", None) or getattr(sig, "short_call_contract", None)
            lg = getattr(sig, "long_put_contract", None) or getattr(sig, "long_call_contract", None)
            t.short_strike = float(sh.strike) if sh is not None else None
            t.long_strike = float(lg.strike) if lg is not None else None
            t.closed = True                                  # narration only; this tick object writes no plan row
            self.planner.ledger_open(t, sig, supersede=False)
        except Exception as exc:                             # noqa: BLE001
            logger.debug("[orcs] ledger row skipped: %s", exc)

    def _build_signal(self, side, short, long_c, credit, price_now):
        from strategy.base_strategy import OptionsSignal
        sig = OptionsSignal(strategy_name=NAME, setup_type=f"orcs_{side}", direction="neutral",
                            option_side=side, underlying_entry=price_now, underlying_stop=0.0)
        sig.is_credit_vertical = True
        sig.is_orcs = True
        sig.net_credit = credit              # THE MARK; the entry ladder prices the order (r206)
        sig.entry_premium = credit
        if side == "call":
            sig.short_call_contract, sig.long_call_contract = short, long_c
        else:
            sig.short_put_contract, sig.long_put_contract = short, long_c
        sig.contract = short
        sig.conviction = 1.0
        sig.condor_trigger_source = "orcs"
        logger.info("[orcs] %s spread: short %g / long %g, mark credit %.2f, to the entry ladder - defended as a condor leg",
                    side, float(short.strike), float(long_c.strike), credit)
        return sig
