"""
strategy/atp_butterfly.py  v1.0
v1.0  2026-09-14  OTV4TEST r26 — THE ATP (AT-THE-PIN) BUTTERFLY: THE STRATEGY (PLAN_SPEC §39).
      THE SPEC. Fire when every condition the plan reports is met, with the plan's
      three legs. Selects nothing — the plan (`strategy/atp_butterfly_plan.py`)
      owns the conditions and the structure, one owner (WA C.1), the untangle's
      shape (ORB, runaway).

      A different thesis from GEXPinButterfly, by the operator's ruling: that trade
      buys a fly for price to TRAVEL to the pin; this one builds it where price
      already SITS on the pin on a settled tape. Same instrument, same exits (the
      40% floor and the 15:45 flatten, strategy/management.py), same exemption
      from the slot rule (is_butterfly) — and ONE BUTTERFLY PER SESSION ACROSS
      BOTH: main.py's trades.db cap counts either name, so whichever plan produces
      a viable trade first takes the day's butterfly.
"""
from __future__ import annotations

import logging
from typing import Optional

import config
from strategy.atp_butterfly_plan import ATPButterflyPlan, NAME
from strategy.base_strategy import OptionsSignal as Signal

logger = logging.getLogger(__name__)

# WA 36 — this file selects nothing and gates nothing; the plan declares its gates
# (strategy/atp_butterfly_plan.py GATES), the untangle's one-owner rule.
GATES = {}


class ATPButterflyStrategy:
    name = NAME

    def __init__(self):
        self.plan = ATPButterflyPlan()
        self.planner = self.plan.planner
        self.CONDITIONS = self.plan.CONDITIONS
        self.PLAN_CHECKS = self.plan.PLAN_CHECKS

    def prepare(self, **kw):
        return self.plan.prepare(**kw)

    def generate_signal(self, *, gex, price_now: float, now_et: str, atm_iv: float = None,
                        chain=None, df_1m=None, **_ignored) -> Optional[Signal]:
        prep = self.plan.prepare(gex=gex, price_now=price_now, now_et=now_et,
                                 atm_iv=atm_iv, chain=chain, df_1m=df_1m)
        if not prep.ready or prep.unmet or prep.structural or prep.starved:
            return prep.tick.already()
        sig = Signal(
            strategy_name=self.name,
            setup_type="atp_butterfly",
            direction="neutral",
            option_side=prep.side,
            underlying_entry=float(price_now),
            underlying_target=prep.pin,
            is_butterfly=True,
            lower_contract=prep.lower,
            center_contract=prep.center,
            upper_contract=prep.upper,
            butterfly_direction=prep.side,
            net_debit=round(prep.debit, 4),
            max_profit=round(prep.width - prep.debit, 4),
            strike=float(prep.center.strike),
            expiry=getattr(prep.center, "expiry", ""),
            entry_premium=round(prep.debit, 4),
            contract=prep.center,
            stop_loss_pct=float(getattr(config, "BUTTERFLY_STOP_LOSS_PCT", 0.40)),
        )
        sig.center_strike = prep.pin
        sig.pin_strike = prep.pin
        sig.pin_concentration = prep.conc
        sig.expected_move = round(prep.em, 4)
        sig.pin_distance = round(prep.dist, 4)
        sig.pin_em_fraction = round(prep.dist / prep.em, 4) if prep.em else 0.0
        sig.settled_bars = prep.settled
        sig.wing_actual = prep.wing
        logger.info("[atp_bfly] FIRE  %s  pin %.2f  spot %.2f  settled %s bars",
                    prep.trade_line(), prep.pin, float(price_now), prep.settled)
        return prep.tick.take(sig)
