"""
derived/plans.py  v2.1
v2.1  2026-09-05  r269 — provenance citation redirected to `docs/PLAN_SPEC.md`
      §8, which holds the as-built record; the r146 handoff that requested the
      rebuild was deleted as a spent thread contract. No code change.
v2.0  2026-08-26  r146 — THE SEVEN BUILDERS ARE DELETED (1,212 lines, lines
      465-1677 of v1.0). They were a second implementation of every strategy
      that guessed at what the real one would do and recorded the guess; zero
      of seven called the strategy they described, and the table read
      `TrendParticipation | TAKE | R 1.43` across the fleet on 2026-08-26
      while those boxes traded nothing. Operator: *"I don't need two
      strategies for every strategy."* Full accounting in
      docs/PLAN_SPEC.md §8 (the as-built record; the r146 handoff that
#      requested it was deleted at r269 as a spent thread contract).
      WHAT MOVED WHERE: the recording layer (plan_tick / plan_check schema,
      NULL-not-zero, starved rows) -> `strategy/plan.py`; the shared session
      map and the operator's geometry ruling -> `analysis/session_map.py`;
      the R hurdle stays in `strategy/criteria.py`. This file is now the
      BOARD: it advances the tick clock and closes each tick with a row for
      every strategy the dispatch did not ask, carrying the dispatcher's own
      reason. It computes nothing about any trade.
v1.0  2026-08-25  r126 — forward plans, declared, priced and recorded.

THE BOARD — one row per strategy per tick, no exceptions.

The strategies write their own rows now (`strategy/plan.py`). What they
cannot write is the row for a tick in which they were NEVER CALLED — ORB
before its engine confirms, the runaway when the ORB has not run away, every
credit strategy when a debit strategy already claimed the slot. Those
silences were the ambiguity that cost the 2026-08-26 session: "ORB did not
set up" and "ORB was never asked" were the same absence.

`derive()` runs at the END of `assemble_market_state` — the one assembly
point — so it sees every tick exactly once:
  1. `close_tick()` — for the tick that just finished, write NOT ASKED rows
     for any registered strategy that wrote nothing, using the reason
     `main.py` gave through `plan.skipped()`. A strategy that WAS asked and
     still wrote nothing gets a NO PLAN row that says so — that is the canary
     for an unwired `return None`, and it goes to the log at WARNING.
  2. `begin_tick()` — advance the shared tick clock so every strategy's row
     this tick carries the same ts.
  3. The board line to the log at INFO, every PLAN_BOARD_LOG_S seconds.

⚠️ OBSERVE-ONLY, STILL. This engine reads nothing a strategy decides on and
writes nothing a strategy reads. The plan's verdict is consulted INSIDE the
strategy, through `strategy/plan.py`; the board only guarantees the record
is complete.
"""
from __future__ import annotations

import logging
import os
import time

from derived.base import DerivedEngine
from strategy import plan as _plan

logger = logging.getLogger(__name__)

# How often the one-line board goes to the log at INFO. The DB rows are the
# verbose record; the log line is the glance.
PLAN_BOARD_LOG_S = float(os.environ.get("OT_PLAN_BOARD_LOG_S", "60"))


class PlanEngine(DerivedEngine):
    """Closes and opens the plan tick. Writes only the NOT ASKED rows."""

    name = "plans"
    table = "plan_tick"
    min_interval_s = 0.0

    def __init__(self, store=None, symbol: str = "", ledger=None):
        super().__init__(store)
        self.symbol = symbol
        self._ledger = ledger          # kept for the registry's call shape
        self._last_board_log = 0.0
        # 🔴 CREATE THE TABLES AT INIT, NOT ON FIRST WRITE (r133). An empty
        # table is a measurement; a missing table is a mystery.
        _plan.ensure_tables(store)
        # one store for the board AND every strategy's plan
        _plan.bind_store(store)

    def derive(self, ctx: dict) -> int:
        n = _plan.close_tick(self._store, self.symbol)
        _plan.begin_tick(time.time())
        now = time.time()
        if PLAN_BOARD_LOG_S and now - self._last_board_log >= PLAN_BOARD_LOG_S:
            line = _plan.board_line()
            if line:
                logger.info("[plans] %s", line)
            self._last_board_log = now
        return n
