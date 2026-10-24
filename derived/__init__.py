"""
derived/  v4.0
The deriving engines. One engine per derived store.

v4.0  2026-08-22  Built with the manifold.

    raw port -> home -> DERIVER -> derived home -> ctx -> engine

Each module here owns exactly ONE table in data/derived_store.py:

    indicators.py  -> indicator_series   ADX, ATR, EMA, VWAP (+accumulators)
    forks.py       -> fork_series        pitchfork forks AND their rejections
    levels.py      -> level_ledger       liquidity levels with lifecycle
    surface.py     -> surface_series     charm, vanna, GEX, IV slope
    snapshot.py    -> fire_snapshot      everything derived at trade fire

🔴 CONTRIBUTORS, NEVER GATES — operator's ruling 2026-08-22. See base.py, where
the rule is enforced structurally rather than promised.

See docs/DERIVED_STORES.md for which values earn a home and why.
"""
from derived.base import DerivedEngine, run_all      # noqa: F401
