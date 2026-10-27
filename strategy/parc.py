"""
strategy/parc.py  v5.0
v5.0  2026-10-27  OTV5 r46 (PARC.1) — new. PARC, PARK'S ENTRY SOLD AS A CREDIT SPREAD ON THE SAFER SIDE: THE
      SPECIFICATION. The operator, 2026-10-27: "under identical entry conditions the PARK trade sells a credit spread
      ATM nearest the strike on the safer side (1st mark below the current price for a long: put spread, or 1st mark
      above current price for a short: call spread) ... adopt the same scaling model we use for breakout, meaning the
      stop distance will determine our position size. Get rid of the delta stop. This will be a hold to 1550 or stop
      on structure ... also add a nickel close — if price makes an aggressive move away from our spread"; "Call it
      PARC"; "I want 1050 to be the floor & use the same ramp in configure.sh (most are set to $2500)"; "No shadow
      mode. We're paper. It trades tomorrow."; "I also want to make sure it uses the ladder entry & exit."

      THE SPLIT (as park.py / park_plan.py): THIS file says what must be true and confirms it on the tick it fires;
      strategy/parc_plan.py READS the tape, picks the two strikes, the stop and the credit, and builds the signal.
      This file searches nothing.

      THE TRADE:
        - ENTRY = PARK's, unchanged and read by the SAME code (park_plan.read_first_hour): the 10:30 1m close against
          the 09:30 1m open, |move| >= PARK_MOVE_PCT (0.20%), up = long; GATE-G against the opening gap; the window
          ENTRY_WINDOWS["PARC"] = 11:01-11:03 once the 11:00 1m bar has closed; one per session; its own budget
          (cap-exempt, config.CAP_EXCLUDED_STRATEGIES). PARC runs BESIDE PARK - both may fire the same minute.
        - THE SPREAD, today's chain: a LONG sells the first listed put strictly BELOW the 11:00 close and buys the
          next listed put below it (a bull put credit spread); a SHORT sells the first listed call strictly ABOVE it
          and buys the next call above (a bear call credit spread). Width = that one strike step. Both legs
          two-sided.
        - THE CREDIT is the one the standard credit-vertical ladder books (main._execute_condor_leg): paper books
          limit_ladder.paper_fill_credit(mark credit), live walks the entry ladder from the best credit toward the
          mark (main._post_credit_vertical). The mark credit = short mid - long mid. PARC_MIN_CREDIT 0.20 (4 x the
          nickel) on the credit the ladder would book; the row says which price that was.
        - THE STRUCTURE STOP: the 5m swing behind the 11:00 price, Breakout's own (breakout_plan.swing_5m_stop,
          BRK.11; BRK_STOP5M_BARS closed 5m bars that ended by 11:01): a long's swing LOW below the 11:00 close, a
          short's swing HIGH above it. No swing behind the price -> no trade (fail closed).
        - SIZE: Breakout's configure.sh ramp (risk_manager._size_parc, rule "parc_ramp"): risk RISK_PER_TRADE_USD at
          the stop, never more than ORB_BUDGET_USD of max loss deployed, at least one lot; one lot over the top
          refuses.
      Exits live in execution/exit_engine._evaluate_parc, FIRST MATCH WINS: the structure stop (a touch through
      underlying_stop, Breakout's rule), the nickel close (bought back at 0.05), else EOD.1 like every short-leg
      structure (15:45 resting best case, 15:55 cross). No delta exit, no PARK lock, no premium stop, no trail.
"""

from __future__ import annotations

import logging

import config

logger = logging.getLogger(__name__)

EARLIEST_ET = "%02d:%02d" % tuple(config.ENTRY_WINDOWS["PARC"][0])
LATEST_ET = "%02d:%02d" % tuple(config.ENTRY_WINDOWS["PARC"][1])
MIN_CREDIT = float(config.PARC_MIN_CREDIT)

# WA 36 - every gate and its category. The window, GATE-G and the structure stop define the trade (FOUNDATIONAL:
# a PARC without a swing behind the price has no stop to size on); the move threshold is PARK's measured
# preference; the minimum credit is what a nickel close can still pay for (FEASIBILITY, parc_plan.GATES).
GATES = {
    "EARLIEST_ET": "FOUNDATIONAL",
    "LATEST_ET":   "FOUNDATIONAL",
    "MOVE_PCT":    "SELECTION",
    "MIN_CREDIT":  "FEASIBILITY",
}


class Parc:
    """The specification. `parc_plan.ParcPlan` satisfies it or stays silent."""

    name = "PARC"

    # ── WHAT MUST BE TRUE. name -> what "true" means ─────────────────────────
    CONDITIONS = {
        "entry_window":     f"{EARLIEST_ET}-{LATEST_ET} ET, once the 11:00 1m bar has closed",
        "first_hour_move":  (f"|10:30 1m close / 09:30 1m open - 1| >= {config.PARK_MOVE_PCT:.2f}% - the first "
                             f"hour moved, and its sign is the direction (PARK's read)"),
        "gate_g":           ("the direction is never against the opening gap (09:30 open vs the prior close): "
                             "a long needs gap >= 0, a short gap <= 0 (PARK's read)"),
        "spread":           ("today's chain: a long sells the first listed put strictly below the 11:00 close and "
                             "buys the next put below; a short sells the first call strictly above and buys the "
                             "next call above; both legs two-sided"),
        "min_credit":       (f"the credit the entry ladder books (paper: paper_fill_credit of the mark credit; "
                             f"live: the mark the walk ends at) >= {config.PARC_MIN_CREDIT:.2f}"),
        "structure_stop":   ("the 5m swing behind the 11:00 close (Breakout's swing_5m_stop): a long's swing low "
                             "below it, a short's swing high above it; the price now not already through it"),
    }

    # Live state re-read on the firing tick: none. Every bar above is a SETTLED fact by 11:01. The strategy still
    # confirms both legs are two-sided at fire time.
    PERSISTENT = ()

    PLAN_CHECKS = tuple(CONDITIONS) + (
        "move_pct", "gap", "open_0930", "close_1030", "spot_1100", "prior_close",
        "short_strike", "long_strike", "width", "credit_mark", "credit", "stop", "value_at_stop",
        "short_iv", "long_iv",
    )

    def __init__(self):
        # the import stays deferred: parc_plan imports this module back (as park.py / park_plan.py).
        from strategy.parc_plan import ParcPlan
        self._plan = ParcPlan()

    def prepare(self, **kw):
        """The plan runs. This file never searches."""
        return self._plan.prepare(spec=self, **kw)

    def generate_signal(self, **kw):
        """CONFIRM the plan's trigger on this tick, then fire it. Picks nothing.

        OT_PARC=log: the plan's TAKE is recorded LOG-ONLY (strategy/plan_state LOG -> main's credit door refuses
        it); nothing here differs between log and trade."""
        prep = self.prepare(**kw)
        if prep is None:
            return None
        if not getattr(prep, "ready", False):
            return prep.tick.already()
        for leg in (prep.short_leg, prep.long_leg):
            bid, ask = getattr(leg, "bid", None), getattr(leg, "ask", None)
            if not (bid is not None and ask is not None and float(ask) >= float(bid) > 0):
                return prep.tick.hold("trigger incomplete — a leg's quote is not two-sided on this tick")
        return prep.emit(self.name)
