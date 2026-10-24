"""
strategy/structure.py  v4.3
v4.3  2026-09-26  OTV4TEST r149 (EOD.1): has_assignment_risk() — a position with a SHORT leg (credit verticals, condor/trend legs, the tent, butterflies, an adopted short). The end-of-day schedule closes these first, at 15:45, on a resting best-case limit. It FAILS TOWARD RISK: a short leg (short_symbol), a fly body (center_symbol) or a condor-leg flag is assignment risk whatever the strategy string says — of() alone would call an unknown strategy DIRECTIONAL and ladder a short leg at 15:50.
v4.2  2026-08-24  r106: Structure.TENT — the post-roll hedge (short + its wing +
      an opposite-type long equidistant on the breached side). Tested FIRST
      because it keeps the vertical's strategy string and every other test would
      claim it; a misroute hands the hedge long to the directional trail.
v4.1  2026-08-24  r99 — the sweep credit spread classifies as CONDOR_LEG (lone
      vertical: 15% floor, 15:45) instead of TREND_PARTICIPATION (TC.6: breach
      or hold, no premium stop). Its spec names exactly two exits and the TC.6
      arm gave it neither the stop nor the sibling-aware management.
Derives trade structure from PERSISTED fields, never a flag.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

strategy/structure.py — options_trader_v3 — (TCS.2 stage 1)
WHAT KIND OF TRADE IS THIS RECORD? DERIVED, NEVER CARRIED.
────────────────────────────────────────────────────────────────────────────
⚠️ THIS IS A LIVE DEFECT FIX, NOT GROUNDWORK
────────────────────────────────────────────────────────────────────────────
`is_trend_credit` **IS NOT A COLUMN** in the trades table. It is written into
the in-memory `TradeRecord` dict and never persisted. `get_open_trades_live()`
does `SELECT *`, so **a restart rehydrates an open trend-participation position
with the flag GONE** — and `exit_engine`'s TC.6 branch, gated on
`record.get("is_trend_credit")`, silently stops firing. The position drops into
the condor ladder and picks up the ratchet and the 25%% premium stop.
That is the SAME bug fixed on 2026-08-14 (identity hardcoded in
`_execute_condor_leg`), one level down: fixed for the process that opened the
trade, still broken for any process that inherits it. **A flag that has to be
copied at every hop will eventually be dropped at one of them** — and the hop
that drops this one is a systemctl restart, which happens on every bake.
────────────────────────────────────────────────────────────────────────────
THE FIX: DERIVE FROM WHAT ALREADY SURVIVES
────────────────────────────────────────────────────────────────────────────
`strategy` and `setup_type` are REAL COLUMNS, already written correctly by
`_execute_condor_leg` (`"TrendCreditSpread"` / `trend_credit_short`), and they
already round-trip through the database. So the discriminator needs no new
column and no migration — it needs to STOP BEING A PARALLEL BOOLEAN and start
being a reading of the fields that persist.
⚠️ WHY NOT JUST ADD THE COLUMN. A new column fixes tomorrow and not today: every
position opened before the migration still rehydrates without it, and `SELECT *`
on an older row returns None, which reads as False — the exact failure, silently.
Deriving works on rows that already exist, including the ones open right now.
⚠️ FAILS CLOSED. An unrecognised record returns DIRECTIONAL, the most restrictive
reading: it keeps its ordinary stop and never inherits a credit structure's
management. A misread must never hand a position a LOOSER exit than it earned.
"""

from enum import Enum
from typing import Any, Mapping, Optional


class Structure(str, Enum):
    """The trade shapes the exit engine must tell apart.

    `str` mixin so a value compares and serialises as plain text — a record can
    carry it, a log can print it, and a test can assert on it without importing
    this module.
    """

    DIRECTIONAL = "directional"        # ORB, continuation, sweep — debit, long
    BUTTERFLY = "butterfly"            # debit, three legs
    CONDOR_LEG = "condor_leg"          # credit vertical, sibling-aware
    TREND_PARTICIPATION = "trend_participation"   # credit vertical, ORB-bounded
    TENT = "tent"                      # r106 — short + its wing + a HEDGE long
                                       # of the OPPOSITE type, equidistant on
                                       # the breached side. Three legs, two
                                       # types; neither a vertical nor a fly.


CREDIT_STRUCTURES = frozenset({Structure.CONDOR_LEG,
                               Structure.TREND_PARTICIPATION,
                               Structure.TENT})


def of(record: Optional[Mapping[str, Any]]) -> Structure:
    """Classify a trade record. Reads ONLY fields that are real columns.

    Order matters: the most specific test first, because a trend-participation
    leg and a condor leg are both credit verticals and only `strategy` /
    `setup_type` tell them apart.
    """
    if not record:
        return Structure.DIRECTIONAL

    strat = str(record.get("strategy") or "").strip().lower()
    setup = str(record.get("setup_type") or "").strip().lower()

    # TREND PARTICIPATION — `strategy` is authoritative and persisted.
    # `setup_type` is checked too because rows written BEFORE the 2026-08-14
    # identity fix carry `strategy="IronCondorStrategy"` with
    # `setup_type="trend_credit_short"`. Those rows are mislabelled at the
    # strategy level and the setup type is the only surviving truth.
    # 🔴 r106 — TENT FIRST. It is built FROM a credit vertical and keeps the
    # vertical's strategy string, so every test below would claim it. Its
    # management is different from all of them: ONE exit, a 15% floor on
    # CUMULATIVE credit. Misroute it and the hedge long gets handed to the
    # directional trail, which is the 2026-08-14 identity bug exactly.
    if setup.startswith("tent") or "tent" in strat.replace("_", ""):
        return Structure.TENT

    if "trendcredit" in strat.replace("_", "") or setup.startswith("trend_credit"):
        return Structure.TREND_PARTICIPATION

    # SWEEP CREDIT SPREAD (v4.0) - a credit vertical sold against the boundary
    # a swept named pool just became. It IS a credit structure and must be
    # recognised as one, or it falls through to DIRECTIONAL and gets laddered
    # out at 15:40 with the debit positions - giving away the last twenty
    # minutes of the theta it was opened to collect. Credit verticals hold to
    # VERTICAL_HOLD_TO_ET (15:45); debits keep the ladder, because they decay
    # and verticals do not.
    # ⚠️ KEYED ON PERSISTED COLUMNS ONLY, like every rule here. `is_trend_credit`
    # was written onto the record as a flag with NO COLUMN and crash-looped
    # NFLX every 15 seconds; §22 PREFER DERIVING exists because of it.
    if "sweepcredit" in strat.replace("_", "") or setup.startswith("sweep_credit"):
        # r99 — CONDOR_LEG, not TREND_PARTICIPATION. TREND_PARTICIPATION is the
        # TC.6 arm: breach-or-hold, NO premium stop. The sweep's spec is
        # "exactly two exits: 15% stop and the 15:45 hard close" — which is
        # the lone-vertical arm every standalone credit spread gets under the
        # union. Mapping it to TC.6 kept it out of the 15:40 flatten (the
        # original intent) and silently removed its stop (the cost).
        return Structure.CONDOR_LEG

    if "ironcondor" in strat.replace("_", ""):
        return Structure.CONDOR_LEG

    if "butterfly" in strat.replace("_", "") or setup.startswith("butterfly"):
        return Structure.BUTTERFLY

    # ⚠️ FAIL CLOSED. Unknown means ordinary directional management — the most
    # restrictive reading. Never hand a position a looser exit than it earned.
    return Structure.DIRECTIONAL


def has_assignment_risk(record: Optional[Mapping[str, Any]]) -> bool:
    """r149 (EOD.1) — True when the position carries a SHORT option leg, so an
    unclosed finish can be ASSIGNED. The end of day closes these first (15:45,
    resting best-case limit); everything else ladders from 15:50.

    Reads only real columns. A long butterfly IS assignment risk: its body is
    two short options.
    ⚠️ FAILS TOWARD RISK, NOT AWAY FROM IT. `of()` fails closed to DIRECTIONAL
    on an unknown strategy string — right for management, WRONG here: a short
    leg the classifier does not recognise would ladder at 15:50 instead of
    resting at 15:45. So the STRUCTURAL columns decide first — a short leg
    (`short_symbol`), a butterfly body (`center_symbol`), a condor leg
    (`is_condor_leg`), an adopted short — and `of()` only adds to them."""
    if not record:
        return False
    if (record.get("is_short_position") or record.get("short_symbol")
            or record.get("center_symbol") or record.get("is_condor_leg")):
        return True
    return of(record) in (CREDIT_STRUCTURES | {Structure.BUTTERFLY})


def is_credit_vertical(record: Optional[Mapping[str, Any]]) -> bool:
    return of(record) in CREDIT_STRUCTURES


def is_tent(record: Optional[Mapping[str, Any]]) -> bool:
    """r106 — the post-roll hedge structure. Credit-basis like a vertical (it
    holds to 15:45, it prices as a credit), but three legs and ONE exit."""
    return of(record) is Structure.TENT


def is_trend_participation(record: Optional[Mapping[str, Any]]) -> bool:
    """Replaces `record.get("is_trend_credit")`.

    ⚠️ THE OLD FLAG IS STILL HONOURED when present, because a position opened by
    a process running the previous build carries it in memory and its
    `strategy` field is already correct anyway — so the two agree. What changes
    is that its ABSENCE is no longer read as "not a trend participation trade",
    which is what a restart produced.
    """
    if record and record.get("is_trend_credit"):
        return True
    return of(record) is Structure.TREND_PARTICIPATION
