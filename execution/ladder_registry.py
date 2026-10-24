"""
execution/ladder_registry.py  v1.2
v1.2  2026-09-08  r315 — `price_for` takes an optional `structure` tag and
      passes it to `LadderState.next_price` (entry_ladder v4.2). Callers that
      key the walk on the INTENT (strategy + side) rather than on the strike
      pair use it so a re-selected strike inherits the rung and sheds the
      ratchet. Callers that pass nothing are unchanged.
v1.1  2026-08-24  r99 — price_for accepts a zero bid (was rejecting the
      header's own example) and the stop escalation returns mark snapped to
      the venue grid in our favour, never a raw half-cent. Still uncalled.

THE OWNER OF `LadderState` BETWEEN TICKS. One rung per tick means the walk IS
multi-tick, so somebody has to hold the ratchet — and nobody did.

v1.0  2026-08-24  r98. Built because `execution/entry_ladder.py` has been a
complete, correct, UNCALLED implementation since 2026-08-20.

════════════════════════════════════════════════════════════════════════════
WHY THIS FILE EXISTS AND WHY IT IS SEPARATE FROM `entry_ladder`
════════════════════════════════════════════════════════════════════════════
`entry_ladder.LadderState` is a pure state machine: give it a quote, it gives
you a price; tell it a price was refused, it advances. It is correct and it is
stateless about WHICH order it belongs to.

The wiring needs the other half — a walk that persists across ticks, keyed to
the intent it is walking for. Put that inside `LadderState` and the state
machine grows a lifetime it should not own; leave it out and every call site
invents its own registry, which is the divergent-lineage failure
`credit_vertical.py`'s header describes.

⚠️ **A LADDER THAT RESETS EVERY TICK IS NOT A LADDER.** It re-offers rung 1
forever, which is v3's exact defect: *"`entry_ladder_prices` recomputed every
rung from the LIVE quote each cycle, so a mark that drifted up could place rung
2 at or above rung 1 — re-offering a level already refused and burning the fill
window on it."* The ratchet only means anything if the state outlives the tick.

════════════════════════════════════════════════════════════════════════════
THE KEY, AND WHY IT IS NOT THE ORDER ID
════════════════════════════════════════════════════════════════════════════
There is no order id yet when the price is being chosen — that is the whole
point. So the key is the INTENT: what we are trying to do, stable across the
attempts that make up one walk.

    <symbol>|<action>|<structure>      e.g.  "NFLX 260828C81|open|single"
                                             "QQQ|close|condor_leg:put"

Two different intents never share a ratchet; the same intent re-attempted on
the next tick resumes its own.

⚠️ **CLEARED ON FILL OR ABANDON, NEVER LEFT TO ROT.** A stale walk would apply
yesterday's refusals to today's order and open at a price the ratchet has
already ruled out — the walk would start mid-ladder against a quote that has
nothing to do with it. `clear()` on fill; `sweep_stale()` drops anything
untouched for longer than one session leg.

⚠️ **LOST ON RESTART, AND THAT IS RECORDED RATHER THAN DEFENDED.** This does not
ride a column, so a bake mid-walk forgets the ratchet and may re-offer one
already-refused price. WORKING_AGREEMENT 22 says state that must survive a
restart rides a column; the judgement here is that one duplicate rung is cheaper
than a schema migration, and it is written down so the next reader can disagree
with a fact rather than rediscover it.

⚠️ **PAPER NEVER TOUCHES THIS.** Paper pricing is `limit_ladder.paper_fill_*`
and stays the single paper authority. A ladder in paper would model fills we
have no evidence for — the ladder's value is measured in LIVE fills or not at
all.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional, Tuple

from execution.entry_ladder import LadderState

logger = logging.getLogger(__name__)

# A walk untouched for this long is dead. One session leg — long enough that a
# quiet symbol mid-walk is not discarded, short enough that nothing crosses a
# session boundary.
STALE_AFTER_S = 3600.0

_WALKS: Dict[str, Tuple[LadderState, float]] = {}


def intent_key(symbol: str, action: str, structure: str = "single") -> str:
    """The stable identity of one walk. See the header for the format."""
    return f"{str(symbol).strip()}|{str(action).strip().lower()}|{str(structure).strip().lower()}"


def get(key: str, side: str, symbol: str = "") -> LadderState:
    """The walk for this intent, resuming its ratchet, or a new one."""
    sweep_stale()
    st = _WALKS.get(key)
    if st is not None:
        _WALKS[key] = (st[0], time.time())
        return st[0]
    walk = LadderState(side=side, symbol=symbol)
    _WALKS[key] = (walk, time.time())
    logger.debug("[ladder] new walk %s side=%s", key, side)
    return walk


def clear(key: str) -> None:
    """Done with this intent — filled, or abandoned. Never leave a walk to rot."""
    if _WALKS.pop(key, None) is not None:
        logger.debug("[ladder] cleared walk %s", key)


def sweep_stale(now: Optional[float] = None) -> int:
    """Drop walks nothing has touched. Returns how many went."""
    t = now if now is not None else time.time()
    dead = [k for k, (_, seen) in _WALKS.items() if t - seen > STALE_AFTER_S]
    for k in dead:
        _WALKS.pop(k, None)
    if dead:
        logger.debug("[ladder] swept %d stale walk(s)", len(dead))
    return len(dead)


def active() -> int:
    """How many walks are in flight. For status/diagnostics only."""
    return len(_WALKS)


def reset_all() -> None:
    """Drop every walk. Session reset only — never mid-session."""
    n = len(_WALKS)
    _WALKS.clear()
    if n:
        logger.info("[ladder] reset %d walk(s) for a new session", n)


def price_for(key: str, side: str, bid: float, ask: float,
              symbol: str = "", stop_escalation: bool = False,
              structure: Optional[str] = None):
    """(price, why) for THIS attempt, or None when the quote is unusable.

    `stop_escalation=True` is the 15% floor and the 15:45 credit close: no walk,
    go straight to mark and re-price there every tick.

    ⚠️ THE FLOOR DOES NOT WALK, AND THAT IS A RISK RULING NOT AN OPTIMISATION.
    Operator, 2026-08-24: a thesis-invalidated stop that spends six ticks hunting
    a better fill has turned a floor into a negotiation. It escalates to mark
    immediately and re-prices at mark until it fills.

    ⚠️ AND IT STILL NEVER CROSSES. Mark is the floor in BOTH senses here — the
    ladder never posts worse than mark, and the escalation never posts worse
    than mark either. Nothing in this system crosses the spread; the operator
    takes assignment over a bad fill.
    """
    try:
        b, a = float(bid), float(ask)
    except (TypeError, ValueError):
        return None
    # r99 — `b <= 0` re-introduced the zero-bid guard r98 removed from
    # `rungs()`: bid 0.00 / ask 1.00 is the operator's own worked example and a
    # routine 0DTE quote. Unusable is a missing quote, a non-positive ASK, or a
    # crossed book — the same test `rungs()` applies.
    if b < 0 or a <= 0 or a < b:
        return None

    if stop_escalation:
        from execution.entry_ladder import _increment, _snap_mark_in_our_favour
        mark = (a + b) / 2.0
        sell = str(side).lower().startswith("s")
        px = _snap_mark_in_our_favour(mark, _increment(symbol, mark, b, a), sell)
        return round(px, 4), "mark (stop escalation — no walk)"

    return get(key, side, symbol).next_price(b, a, structure=structure)


def refuse(key: str, price: float) -> None:
    """Record that `price` did not COMPLETELY fill, and advance the rung.

    ⚠️ A PARTIAL IS A REFUSAL FOR THE REMAINDER. Operator's definition: a
    refusal is "didn't completely fill at that price". The filled part is a
    real position and is booked; the rest walks on from the next rung.
    """
    st = _WALKS.get(key)
    if st is None:
        return
    st[0].refuse(price)
    _WALKS[key] = (st[0], time.time())
