"""
strategy/observe.py  v1.1
THE PLAN ALWAYS LOOKS; THE STRATEGY IS GATED ON THE HOUR (OBS.1).

v1.1  2026-10-19  OTV4TEST r303 (PSTATE.1). A plan switched to LOG (strategy/plan_state.py; the operator,
      2026-10-19: "active, dormant or log only") is observed on EVERY tick it is asked: is_active() is True for it,
      so take() records LOG-ONLY and every main.py door refuses the signal. set_active() and the r254 scope are
      unchanged; with every switch unset no plan is LOG, so nothing here moves.
v1.0  2026-10-05  OTV4TEST r254 (OBS.1). The operator, 2026-10-05 09:34 ET: "I think a better
      way to frame it would be the plan always looks, but the strategies are gated on the
      hour of the day"; 09:36 ET, scope: "A for sure" (Breakout, Runaway and the Hunt only);
      09:32 ET: "Have those blocked TRADES just to Log only". Before this, r187's 10:29 end
      stopped each of the three PLANS too - admission never asked the strategy, and each
      plan returned DORMANT 'entry_window' before it looked - so nothing recorded what the
      cutoff blocked (CUT.1 needs exactly that).

WHAT IT IS. One per-tick set: the strategies admission refused ONLY on its window, after that
window ended and before the entries stop (15:40). main.py publishes it each tick
(`set_active`) and clears it at the top of every dispatch. A strategy in it is ASKED, its plan
runs exactly as in the morning, and anything it would fire is RECORDED, never executed:

  · strategy/plan.py `take()` writes the verdict LOG-ONLY (never TAKE), opens no plan_ledger
    row and reports nothing fired;
  · main.py refuses the signal at `_fire`, at the hunt's own door, and again at the top of
    `_execute_entry_signal` - three locks, so no path reaches sizing, an order or trades.db;
  · the Hunt's in-memory FINISHED set is untouched, so tomorrow's state and the real
    one-per-break rule are exactly as they were.

⚠️ FAILS CLOSED. Empty unless main.py published it THIS tick; an exception anywhere here
reads as "not observing", which leaves every plan's own window check in force - the old
behaviour, never a trade.
"""
from __future__ import annotations

import logging
from typing import Iterable

logger = logging.getLogger(__name__)

# Operator's scope, 2026-10-05 ("A for sure"): the three directional plans r187 cut at 10:29.
OBSERVE_AFTER_WINDOW = ("Breakout", "RunawayContinuation", "LiquidityHunt")

LOG_ONLY = "LOG-ONLY"            # the plan_tick verdict; deliberately NOT containing "TAKE"

_ACTIVE: frozenset = frozenset()
_SEEN: set = set()


def set_active(names: Iterable[str]) -> None:
    """Publish this tick's observe set (main.py). Anything outside the scope is dropped."""
    global _ACTIVE
    try:
        _ACTIVE = frozenset(n for n in (names or ()) if n in OBSERVE_AFTER_WINDOW)
    except Exception:                                           # noqa: BLE001
        _ACTIVE = frozenset()


def clear() -> None:
    set_active(())


def is_active(name: str) -> bool:
    """Is `name` being observed (asked, recorded, never executed) this tick? r303: a LOG-state plan always is."""
    try:
        if str(name or "") in _ACTIVE:
            return True
    except Exception:                                           # noqa: BLE001
        return False
    try:
        from strategy import plan_state as _ps
        return _ps.is_log(str(name or ""))
    except Exception:                                           # noqa: BLE001
        return False


def first_time(key) -> bool:
    """True the first time `key` is seen this process - one log line per setup, not per tick."""
    if key in _SEEN:
        return False
    _SEEN.add(key)
    return True
