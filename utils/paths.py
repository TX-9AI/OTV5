"""
utils/paths.py  v1.0
v1.0  2026-10-03  OTV4TEST r218 (PATH.1) — ONE RESOLVER FOR THE THREE STORE PATHS. The 10-03 audit (C4 / D4): the feed store's
      path was resolved six ways in the bot process - two of them hard-coded ~/options-trader and one read
      config names that do not exist - and the derived and resting stores each had their own home-anchored
      default. The operator, 2026-10-03: "yes I want the centralized modules ... one at a time, thoroughly
      and proven."

      THE RULE, the same for all three: the store's OT_* variable if it is set, else <this checkout>/data/<file>.
      Resolved at CALL time (a checker sets the variable after import). Stdlib only, imports nothing of
      ours - so the modules that must stay import-light (options_chain, entry_snapshot) can use it.

      ON THE BOX nothing moves: the checkout IS ~/options-trader. IN A SCRATCH CLONE with no variable set,
      the default is now the clone's own data/ directory instead of the live box's files.
      data/candle_feed.feed_db_path() - the feed process's own copy of the rule - is deliberately left
      untouched (no edit to the feed process); tests/check_store_paths.py pins that the two agree.
"""
import os

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_dir() -> str:
    """<this checkout>/data"""
    return os.path.join(REPO_DIR, "data")


def _resolve(env_name: str, filename: str) -> str:
    v = (os.environ.get(env_name) or "").strip()
    if v:
        return os.path.expanduser(v)
    return os.path.join(data_dir(), filename)


def feed_db_path() -> str:
    """The feed store: $OT_FEED_DB, else <checkout>/data/feed_store.db."""
    return _resolve("OT_FEED_DB", "feed_store.db")


def derived_db_path() -> str:
    """The derived store: $OT_DERIVED_DB, else <checkout>/data/derived_store.db."""
    return _resolve("OT_DERIVED_DB", "derived_store.db")


def resting_db_path() -> str:
    """The standing-offer store: $OT_RESTING_DB, else <checkout>/data/resting_orders.db."""
    return _resolve("OT_RESTING_DB", "resting_orders.db")
