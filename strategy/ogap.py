"""
strategy/ogap.py  v5.2
v5.2  2026-11-21  OTV5 r136 (OGAP.3) — the ogap_contract condition reads the MARK (mark >= OGAP_MIN_ASK, floor(RISK_PER_TRADE_USD / (mark x 100)) >= 1), not the ask: the operator, 2026-11-20, "never pay the spread". The two-sided quote check is unchanged (a mark needs both sides).
v5.1  2026-11-16  OTV5 r131 (OGAP.2) — the ogap_contract description reads RISK_PER_TRADE_USD (the ramp MIN), not the deleted OGAP_BUDGET_USD.
v5.0  2026-11-14  OTV5 (OGAP.1) — OGAP, PARK'S FRIEND'S ORB-GAP: THE SPECIFICATION. The operator, 2026-11-14: "let's
      design & paper trade the OGAP on QQQ". A faithful PAPER copy of a borrowed trade (docs/OGAP_SPEC.md; Park's spec
      of record 2026-11-13): its signal, sizing and exits are his, unchanged; only the plumbing is ours.

      THE SPLIT (as park.py / park_plan.py): THIS file says what must be true and confirms the quote on the tick it
      fires; strategy/ogap_plan.py READS the tape, picks the contract and builds the signal.

      MEASURED (~/reviews/studies/park_orbgap_20261113, ogap_equities_20261113 sealed 2026-11-13 22:04 UTC): QQQ T1 real
      quotes n=7 +$148/row [-124, +454], T2 n=32 +$137 [-87, +421]; equities FAILED the sealed bar (T1 -$96 [-160, -22]),
      so OGAP trades QQQ only (config.OGAP_SYMBOLS). Its own $500 budget, cap-exempt, decay-exempt, pin-exempt.
"""

from __future__ import annotations

import logging

import config

logger = logging.getLogger(__name__)

EARLIEST_ET = "%02d:%02d" % tuple(config.ENTRY_WINDOWS["OGAP"][0])
LATEST_ET = "%02d:%02d" % tuple(config.ENTRY_WINDOWS["OGAP"][1])

GATES = {
    "EARLIEST_ET": "FOUNDATIONAL",
    "LATEST_ET":   "FOUNDATIONAL",
}


class Ogap:
    """The specification. `ogap_plan.OgapPlan` satisfies it or stays silent."""

    name = "OGAP"

    CONDITIONS = {
        "ogap_entry_window": f"{EARLIEST_ET}-{LATEST_ET} ET (the last signal bar 10:30, the last fill 10:31)",
        "ogap_range":        (f"the 09:30-09:44 1m range: >= {config.OGAP_RANGE_MIN_BARS} bars and W > 0"),
        "ogap_gate_g":       (f"|gap| >= {config.OGAP_GATE_G_W:.2f}W: only the gap's side; else both; unread: both"),
        "ogap_signal":       (f"the first 1m close beyond the range 09:45-10:30, then a retest within "
                              f"{config.OGAP_RETEST_BARS} bars at +/-{config.OGAP_RETEST_W:.2f}W closing back beyond "
                              f"the level; filled the next minute or never"),
        "ogap_contract":     (f"today's expiry, the strike nearest the fill-minute open (tie lower), two-sided, mark >= "
                              f"{config.OGAP_MIN_ASK:.2f}, floor({config.RISK_PER_TRADE_USD:.0f} / (mark x 100)) >= 1"),
    }

    PERSISTENT = ()

    PLAN_CHECKS = tuple(CONDITIONS) + (
        "ogap_not_this_symbol", "ogap_range_w", "ogap_range_bars", "ogap_gap", "ogap_allowed",
        "ogap_break_c", "ogap_break_p", "ogap_signal_c", "ogap_signal_p", "ogap_gateg_shadow",
        "ogap_no_range", "ogap_stale", "ogap_no_0dte", "ogap_ask_floor", "ogap_ask_band", "ogap_bars", "ogap_read",
        "strike", "ask", "bid", "contracts",
    )

    def __init__(self):
        from strategy.ogap_plan import OgapPlan
        self._plan = OgapPlan()

    def prepare(self, **kw):
        return self._plan.prepare(spec=self, **kw)

    def generate_signal(self, **kw):
        """CONFIRM the plan's trigger on this tick, then fire it. Picks nothing."""
        prep = self.prepare(**kw)
        if prep is None:
            return None
        if not getattr(prep, "ready", False):
            return prep.tick.already()
        c = prep.contract
        bid, ask = getattr(c, "bid", None), getattr(c, "ask", None)
        if not (bid is not None and ask is not None and float(ask) >= float(bid) > 0):
            return prep.tick.hold("trigger incomplete — the contract's quote is not two-sided on this tick")
        return prep.emit(self.name)
