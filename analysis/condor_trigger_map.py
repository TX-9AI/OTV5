"""
analysis/condor_trigger_map.py  v1.0
v1.0  2026-08-24  CONDOR TRIGGER MAP: the fork rails are a LINEAR FUNCTION
      OF TIME+SLOPE, not a stored snapshot. A trigger level cached at 11am
      from IronCondorStrategy.decide() is wrong at 2pm — the rail has moved
      by slope × bars_elapsed. This map recomputes rails_for() every tick so
      every trigger check uses the rail where it actually sits now.

      Sweep and TC.6 triggers are self-reporting (their strategies detect
      their own conditions). This mapper handles the fork triggers — the ones
      with a continuously moving geometry.

THE FORMULA (unchanged from IronCondorStrategy v4.2, now live each tick):
    trigger_call = median + APPROACH × (upper_rail − median)
    trigger_put  = median − APPROACH × (median − lower_rail)
    active       = price >= trigger_call  (call side)
                   price <= trigger_put   (put side)

Two timeframes, two sides = up to four ForkTrigger entries per tick.
A missing or unborn fork produces no entry for that timeframe.
Never raises — a failed map is an empty one.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ForkTrigger:
    """One trigger opportunity from one fork tine at the current tick."""
    tf:      str    # "1h" or "1d"
    side:    str    # "call" (upper rail) or "put" (lower rail)
    rail:    float  # current rail position (recomputed this tick)
    trigger: float  # price level that fires this trigger
    median:  float  # channel midline at this tick
    slope:   float  # rail drift per bar of the timeframe
    active:  bool   # True when price has reached the trigger level

    @property
    def condor_trigger_source(self) -> str:
        return f"{self.tf}_fork"


@dataclass
class CondorTriggerMap:
    """Per-tick snapshot of all fork-based condor trigger levels.

    Build once per tick via build(); store in ctx["condor_triggers"].
    """
    triggers: List[ForkTrigger] = field(default_factory=list)
    price:    float = 0.0
    ts:       float = 0.0

    def active_for(self, side: str) -> List[ForkTrigger]:
        """Active triggers on one side, inner (narrower rail) first."""
        hits = [t for t in self.triggers if t.side == side and t.active]
        return sorted(hits, key=lambda t: abs(t.rail - self.price))

    def any_active(self, side: str) -> bool:
        return any(t.side == side and t.active for t in self.triggers)

    def best(self, side: str) -> Optional[ForkTrigger]:
        """The closest active trigger for one side, or None."""
        hits = self.active_for(side)
        return hits[0] if hits else None

    def all_rails(self) -> List[ForkTrigger]:
        """All triggers (active or not) — used for approach telemetry."""
        return list(self.triggers)


def build(ctx: dict, instrument: str,
          approach_frac: float = 0.65,
          timeframes: tuple = ("1h", "1d")) -> CondorTriggerMap:
    """Compute the current trigger map. Never raises.

    Called once per tick, result stored in ctx["condor_triggers"].
    Typically called just before the credit-spread dispatch so every
    strategy evaluation in this tick sees the same rail positions.
    """
    price = float(ctx.get("price") or 0.0)
    result = CondorTriggerMap(price=price)
    if price <= 0:
        return result

    try:
        from analysis.pitchfork_observer import rails_for
    except Exception as exc:                                    # noqa: BLE001
        logger.debug("condor_trigger_map: pitchfork_observer unavailable: %s", exc)
        return result

    for tf in timeframes:
        try:
            rails = rails_for(ctx, instrument, tf)
            if not rails:
                continue
            upper  = float(rails["upper"])
            lower  = float(rails["lower"])
            median = float(rails["median"])
            slope  = float(rails.get("slope", 0.0))

            if upper <= lower or median <= 0:
                continue

            # Trigger level: APPROACH fraction of the way from midline to rail.
            # ⚠️ RECOMPUTED FROM THE CURRENT RAIL POSITION — not cached from
            # plan time. A 1h fork with slope $1/bar shifts the trigger $6
            # between 11am and 5pm bars. Using the stale level means the condor
            # fires when price is NOT at the rail, selling premium not rich.
            trig_call = median + approach_frac * (upper - median)
            trig_put  = median - approach_frac * (median - lower)

            result.triggers.append(ForkTrigger(
                tf=tf, side="call",
                rail=upper, trigger=trig_call, median=median, slope=slope,
                active=(price >= trig_call),
            ))
            result.triggers.append(ForkTrigger(
                tf=tf, side="put",
                rail=lower, trigger=trig_put, median=median, slope=slope,
                active=(price <= trig_put),
            ))
        except Exception as exc:                                # noqa: BLE001
            logger.debug("condor_trigger_map: %s frame failed: %s", tf, exc)

    return result
