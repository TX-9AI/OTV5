"""
strategy/park.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-18  OTV4TEST r288 (PARK.1) — PARK, THE 11:00 FIRST-HOUR CONTINUATION: THE SPECIFICATION. The
      operator, 2026-10-17 18:21 ET: "Trade it, don't just log it. Paper is free. Call it PARK (named after my
      friend)"; on SPX: "Use our actual numbers, trade it—don't log it"; 18:30 ET: "Make sure when you build it
      it's divided properly between the strategy and the plan."

      THE SPLIT (as breakout.py / breakout_plan.py): THIS file says what must be true and confirms it on the
      tick it fires; strategy/park_plan.py READS the tape, picks the contract and builds the signal. This file
      searches nothing.

      THE TRADE (his friend's CONT11, frozen in /var/tmp/sat_1017/cont11/PREREG_CONT11.md, cell C0):
        - the first hour moved: the 10:30 1m bar's CLOSE against the 09:30 1m bar's OPEN, |move| >= 0.20%;
        - GATE-G: never against the opening gap (09:30 open vs the prior close);
        - the strike nearest the 11:00 1m bar's close, today's expiry, bought at the ASK 11:01-11:02;
        - sized flat on the box's own risk: floor(RISK_PER_TRADE_USD / (ask x 100)) - $1,050 on QQQ-TEST,
          $2,500 on SPX-TEST ("That whole budget goes to contracts", 10-17);
        - its own budget: outside the catastrophic cap both ways (config.CAP_EXCLUDED_STRATEGIES);
        - one per session.
      Exits live in execution/exit_engine._evaluate_park: the +60% / +20% lock on the bid, the delta floor
      |delta| <= 0.30 from 11:30 (PARK.X, picks sha 85dca420: QQQ n11 +10,550 -> +11,786, SPX n14 +13,320 ->
      +16,370, every winner kept), else the 15:45 close. No premium stop, no trail.

      MEASURED (read-only, fit week 10-12..16 reported separately): QQQ 41 days n11 +10,550 at $1,050, +1,590
      without the fit week; SPX 39 days n14 +13,320 at $2,500. Small n - the book rests on 2-3 days a month.
"""

from __future__ import annotations

import logging

import config

logger = logging.getLogger(__name__)

EARLIEST_ET = "%02d:%02d" % tuple(config.ENTRY_WINDOWS["PARK"][0])
LATEST_ET = "%02d:%02d" % tuple(config.ENTRY_WINDOWS["PARK"][1])
MOVE_PCT = float(config.PARK_MOVE_PCT)

# WA 36 - every gate and its category. The window and GATE-G define the trade (FOUNDATIONAL: a PARK at 10:15, or
# against the gap, is a different trade); the move threshold is a measured preference (0.40 / 0.60 dropped SPX's
# big days, 10-17).
GATES = {
    "EARLIEST_ET": "FOUNDATIONAL",
    "LATEST_ET":   "FOUNDATIONAL",
    "MOVE_PCT":    "SELECTION",
}


class Park:
    """The specification. `park_plan.ParkPlan` satisfies it or stays silent."""

    name = "PARK"

    # ── WHAT MUST BE TRUE. name -> what "true" means ─────────────────────────
    CONDITIONS = {
        "entry_window":     f"{EARLIEST_ET}-{LATEST_ET} ET, once the 11:00 1m bar has closed",
        "first_hour_move":  (f"|10:30 1m close / 09:30 1m open - 1| >= {config.PARK_MOVE_PCT:.2f}% - the first "
                             f"hour moved, and its sign is the direction"),
        "gate_g":           ("the direction is never against the opening gap (09:30 open vs the prior close): "
                             "a call needs gap >= 0, a put gap <= 0. MEASURED: halves QQQ's losers, neutral on SPX"),
        "contract":         (f"the strike nearest the 11:00 1m close, today's expiry, two-sided, ask >= "
                             f"{config.PARK_MIN_ASK:.2f}"),
    }

    # Live state re-read on the firing tick: none. Every bar above is a SETTLED fact by 11:01 - the bars
    # closed, the gap is fixed. The strategy still confirms the quote is two-sided at fire time.
    PERSISTENT = ()

    PLAN_CHECKS = tuple(CONDITIONS) + (
        "move_pct", "gap", "open_0930", "close_1030", "spot_1100", "prior_close",
        "strike", "ask", "bid", "delta",
    )

    def __init__(self):
        # the import stays deferred: park_plan imports this module back (as breakout.py / breakout_plan.py).
        from strategy.park_plan import ParkPlan
        self._plan = ParkPlan()

    def prepare(self, **kw):
        """The plan runs. This file never searches."""
        return self._plan.prepare(spec=self, **kw)

    def generate_signal(self, **kw):
        """CONFIRM the plan's trigger on this tick, then fire it. Picks nothing.

        PARK_MODE=log: the would-be fire is recorded (plan row + data/counterfactual/park_signal.jsonl) and
        nothing is returned to execute."""
        prep = self.prepare(**kw)
        if prep is None:
            return None
        if not getattr(prep, "ready", False):
            return prep.tick.already()
        c = prep.contract
        bid, ask = getattr(c, "bid", None), getattr(c, "ask", None)
        if not (bid is not None and ask is not None and float(ask) >= float(bid) > 0):
            return prep.tick.hold("trigger incomplete — the contract's quote is not two-sided on this tick")
        if config.PARK_MODE == "log":
            prep.record_would_fire()
            from strategy import observe as _observe
            return prep.tick.hold("OT_PARK=log — would take " + prep.trade_line(), verdict=_observe.LOG_ONLY)
        return prep.emit(self.name)
