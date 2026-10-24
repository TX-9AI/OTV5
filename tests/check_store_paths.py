#!/usr/bin/env python3
"""
tests/check_store_paths.py  v1.0
v1.0  2026-10-03  OTV4TEST r218 (PATH.1) — ONE RULE RESOLVES THE FEED, DERIVED AND RESTING STORE PATHS.

  The 10-03 audit (C4 / D4): six resolutions of the feed store's path in the bot
  process, two hard-coding ~/options-trader, one reading config names that do
  not exist; resting_orders importing a config.DATA_DIR that was never defined.
  The operator, 2026-10-03: "yes I want the centralized modules".

  S1  utils.paths: the OT_* variable wins; unset, each store is under THIS
      checkout's data/ directory
  S2  the feed process's own copy (data.candle_feed.feed_db_path, untouched)
      agrees with it, set and unset
  S3  every runtime consumer returns the same path as the rule, set and unset:
      options_chain, entry_snapshot, derived_store, resting_orders
  S4  no runtime module still spells a home-anchored store path
  S5  config.DATA_DIR and config.QUOTE_FLOOR exist; breakout_plan reads the floor

Run:  python3 tests/check_store_paths.py   (exit 0 green, 1 red)
"""
import glob as _glob
import os
import re
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_store_paths_")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_S, "trades.db"))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []
VARS = {"OT_FEED_DB": "feed_store.db", "OT_DERIVED_DB": "derived_store.db", "OT_RESTING_DB": "resting_orders.db"}


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _with(env):
    for k in VARS:
        os.environ.pop(k, None)
    os.environ.update(env)


def main():
    saved = {k: os.environ.get(k) for k in VARS}
    try:
        try:
            from utils import paths as P
        except Exception as exc:                              # noqa: BLE001
            for n in ("S1", "S2", "S3"):
                check(f"{n} (did not run)", False, f"{type(exc).__name__}: {exc}")
            P = None
        if P is not None:
            fns = {"OT_FEED_DB": P.feed_db_path, "OT_DERIVED_DB": P.derived_db_path, "OT_RESTING_DB": P.resting_db_path}
            scratch = {k: os.path.join(_S, "x", f) for k, f in VARS.items()}
            _with(scratch)
            set_ok = all(fns[k]() == scratch[k] for k in VARS)
            _with({})
            unset = {k: fns[k]() for k in VARS}
            unset_ok = all(unset[k] == os.path.join(_root, "data", VARS[k]) for k in VARS)
            check("S1 the variable wins; unset, each store is <this checkout>/data/<file>", set_ok and unset_ok,
                  f"set {set_ok}; unset {unset}")

            from data.candle_feed import feed_db_path as feed_owner
            _with(scratch); a = feed_owner() == P.feed_db_path()
            _with({}); b = feed_owner() == P.feed_db_path()
            check("S2 the feed process's own resolver agrees, set and unset", a and b, f"set {a}, unset {b}")

            import data.options_chain as OC
            import analysis.entry_snapshot as ES
            import data.derived_store as DS
            import execution.resting_orders as RO
            cons = {"options_chain": (OC._feed_db_path, "OT_FEED_DB"), "entry_snapshot": (ES._feed_db, "OT_FEED_DB"),
                    "derived_store": (DS.derived_db_path, "OT_DERIVED_DB"), "resting_orders": (RO._db_path, "OT_RESTING_DB")}
            bad = []
            for label, env in (("set", scratch), ("unset", {})):
                _with(env)
                for name, (fn, var) in cons.items():
                    if fn() != fns[var]():
                        bad.append((label, name, fn(), fns[var]()))
            check("S3 options_chain, entry_snapshot, derived_store and resting_orders all return the rule's path",
                  not bad, str(bad))
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    try:
        pat = re.compile(r"options-trader[\"'/, ]+\s*[\"']?data[\"'/, ]+\s*[\"']?(feed_store|derived_store|resting_orders)\.db"
                         r"|~/options-trader/data/(feed_store|derived_store|resting_orders)\.db")
        hits = []
        for d in ("", "data", "derived", "execution", "strategy", "analysis", "risk", "utils", "database"):
            for f in sorted(_glob.glob(os.path.join(_root, d, "*.py"))):
                rel = os.path.relpath(f, _root)
                if rel in ("query.py", "status.py") or os.sep + "candle_feed.py" in os.sep + rel:
                    continue                                  # the operator's CLIs and the feed process: not this delivery
                for i, line in enumerate(open(f), 1):
                    if line.lstrip().startswith("#"):
                        continue
                    if pat.search(line) and "expanduser" in line:
                        hits.append(f"{rel}:{i}")
        check("S4 no runtime module still builds a home-anchored store path", not hits, ", ".join(hits))
    except Exception as exc:                                  # noqa: BLE001
        check("S4 (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        import config as C
        from strategy import breakout_plan as BP
        from utils import paths as P2
        check("S5 config.DATA_DIR is the checkout's data dir; QUOTE_FLOOR is 0.01 and breakout_plan reads it",
              C.DATA_DIR == P2.data_dir() and C.QUOTE_FLOOR == 0.01 and BP.QUOTE_FLOOR == 0.01,
              f"{getattr(C, 'DATA_DIR', None)} {getattr(C, 'QUOTE_FLOOR', None)}")
    except Exception as exc:                                  # noqa: BLE001
        check("S5 (did not run)", False, f"{type(exc).__name__}: {exc}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — one rule resolves the three store paths, and every runtime consumer uses it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
