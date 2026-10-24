"""
derived/registry.py  v4.2
v4.2  2026-09-12  OTV4TEST r15 — `level_engine()`: the plans read the level board from the
      one engine build_engines() made.
v4.1  2026-09-08  OTV4TEST r5 — the level engine is handed the fork engine so the
      1h tines are levels in the store (moving, keyed on the tine).
Builds the engine set for one box. The single place main.py touches.

v4.0  2026-08-22  See docs/DERIVED_STORES.md.

⚠️ ONE ASSEMBLY POINT, DELIBERATELY. `ctx["chain"]` and `ctx["gex"]` are
written at main.py:2746 INSIDE the dispatch path, so their availability
depends on where in the tick you stand — the same input present for one
consumer and absent for another. Every derived port is built HERE so that
cannot happen to any of them.

⚠️ RETURNS AN EMPTY LIST IF THE STORE WILL NOT OPEN. Derivers are contributors,
never gates: a box with no derived store trades exactly as it does today.
"""

from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger(__name__)


_LEVELS = {"engine": None}       # r15: the one LevelEngine, for plans that read the board


def level_engine():
    """The LevelEngine built by build_engines(), or None before it runs."""
    return _LEVELS["engine"]


def build_engines(symbol: str) -> List:
    """Every derived engine for this box, or [] if the store is unavailable."""
    try:
        from data.derived_store import get_derived_store
        store = get_derived_store()
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("derived registry: store import failed: %s", exc)
        return []
    if store is None:
        logger.warning("derived registry: no store — derived values will not "
                       "be recorded this session; trading is unaffected")
        return []
    try:
        from derived.indicators import IndicatorEngine
        from derived.forks import ForkEngine
        from derived.levels import LevelEngine
        from derived.surface import SurfaceEngine
        from derived.snapshot import SnapshotEngine
        from derived.counterfactual import CounterfactualExitEngine
        from derived.notes import NotesEngine
        from derived.plan_ledger import PlanLedger
        from derived.character_engine import CharacterEngine
        from derived.plans import PlanEngine
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("derived registry: engine import failed: %s", exc)
        return []

    forks = ForkEngine(store, symbol)
    levels = LevelEngine(store, symbol, forks=forks)      # r5: tines are levels
    _LEVELS["engine"] = levels                            # r15: the board's owner
    return [
        IndicatorEngine(store, symbol),
        forks,
        levels,
        SurfaceEngine(store, symbol),
        SnapshotEngine(store, symbol, levels=levels),
        # ⚠️ RECORDS ONLY — evaluates a flow exit on every open
        # position and writes when it WOULD have fired. The
        # mechanical stop is untouched. See the module docstring
        # for why the burden of proof here is high (bos_exit).
        CounterfactualExitEngine(store, symbol),
        # ⚠️ EVENT-DRIVEN, not per-tick: one row per STRATEGY
        # EVALUATION — fired AND declined — written from main's
        # dispatch hook after the decision is already made.
        NotesEngine(store, symbol),
        # ⚠️ CHARACTER IS A STATE WITH DURATION — it records
        # TRANSITIONS, not per-tick samples, and gates nothing.
        CharacterEngine(store, symbol),
        # 🔴 r126 — FORWARD PLANS. Declares and PRICES what each setup would
        # trade from here, logs one INFO line per plan per cycle, and records
        # TAKE plans in plan_ledger. ⚠️ OBSERVE-ONLY: nothing in main.py reads
        # it, so entry and exit behave exactly as they did before. Operator
        # asked for visibility first — "better communication from the bots
        # tomorrow about what they're seeing" — and the plan architecture
        # proper (docs/PLAN_SPEC.md) is a far larger build.
        PlanEngine(store, symbol, ledger=PlanLedger(store, symbol)),
    ]


def snapshot_engine(engines):
    """The SnapshotEngine out of a built set, or None."""
    for e in engines or []:
        if getattr(e, "name", "") == "snapshot":
            return e
    return None


def plan_ledger(symbol: str):
    """The plan ledger for this box, or None.

    ⚠️ NOT AN ENGINE — it is EVENT-DRIVEN (a plan opens when a strategy
    decides, transitions when a leg fills). Modelling it as a tick engine
    would either miss transitions or invent them.
    """
    try:
        from data.derived_store import get_derived_store
        from derived.plan_ledger import PlanLedger
        from derived.character_engine import CharacterEngine
        store = get_derived_store()
        return PlanLedger(store, symbol) if store is not None else None
    except Exception:                                           # noqa: BLE001
        return None
