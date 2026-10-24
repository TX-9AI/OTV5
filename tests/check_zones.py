#!/usr/bin/env python3
"""
tests/check_zones.py  v1.2
v1.2  CD.2 (2026-10-24) - the fixture marks the level book SYNCED (store.mark_level_sync) after seeding the ledger:
      LevelEngine.board() now fails closed as not_synced until a book sync against a recent closed 1m bar has been
      recorded (derived/levels v6.10). Every expectation is unchanged.
v1.1  2026-09-23  OTV4TEST r124 — RETARGETED, NOT REMOVED (§38.4), with the code it
      pins: the board's `zones`/`walk` moved from derived/level_map into
      derived/levels (`_zones`/`_walk`, verbatim) and its width now comes from the
      book (level_book.zone_width over hourly BARS, set on the engine as
      `_zone_width`). Every assertion is unchanged; Z1 measures the book's width
      function on the same bars, Z2-Z4 the moved `_zones`, Z5 the board with the
      engine holding the book's width instead of a tape. And the r106 venv
      bootstrap it never had: under system python3 it died on pandas.
CLUSTERED EXTREMES ARE ONE ZONE, AND ONLY ITS OUTER MEMBERS DECLARE ANYTHING.

v1.0  2026-09-18  OTV4TEST r39 — born red at r38 (5c7213b): no `zone_width`, no
      `zones`, and `board()` walks individual levels.

THE OPERATOR'S SPEC, 2026-09-18, verbatim:
  *"When session extremes, by recency first, cluster in close proximity I want
  the extremes of the outermost (highest, lowest) of the cluster to count as a
  touch when the nearest part of the zone is tested, and breached when the
  furthest part of the cluster is accepted beyond"*; *"it's just grouping and
  only the outer members of the group declare anything"*; *"when we have a
  breach of the cluster everything that was a part of the cluster needs to go
  with it"*; *"one zone containing spot isn't a zone, then. It's done — as a
  zone is defined, it's finished. There's no reclaim trade for that."*

⚠️ THE WIDTH IS COMPUTED, NOT STORED — the instrument's own median hourly wick,
recomputed continuously. Measured across three symbols the wick/range ratio
holds at 31-37% while percent-of-spot spans FOUR-FOLD, so a stored percentage
would have been wrong on MU by 4x. That is why Z1 asserts a MEASUREMENT.
"""
import os
import time as _tm
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import glob as _glob                                             # r106 venv bootstrap (r124:
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):   # absent until
    if _sp not in sys.path:                                      # now; it died on pandas under
        sys.path.insert(1, _sp)                                  # the lander's system python3)
os.environ.setdefault("OT_DERIVED_DB", os.path.join(tempfile.mkdtemp(), "d.db"))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def guard(name, fn, detail=""):
    """Run a predicate; a MISSING symbol is a RED LINE, never a traceback.

    ⚠️ THIS IS THE THIRD TIME TODAY. `check_level_source` CRASHED at r32 and
    `check_manifold_board` M4b CRASHED at r37, both at the older HEAD they were
    written to fail at. A checker that dies on `AttributeError` cannot say WHICH
    behaviour is absent, and it reads the same as a checker that is simply
    broken — so the born-red proof it exists to give is worthless. Every
    assertion below goes through here.
    """
    try:
        ok, det = fn(), detail
    except Exception as exc:
        ok, det = False, f"{type(exc).__name__}: {exc}"
    check(name, ok, det if isinstance(det, str) else str(det))
    return ok


def main():
    import pandas as pd
    from derived import level_book as B
    try:                                           # a MISSING symbol is a red line (guard's rule)
        from derived.levels import _zones
    except ImportError:
        _zones = None

    # hourly bars whose median larger-side wick is exactly 1.00
    bars = [(1_788_000_000_000 + i * 3_600_000, 100.0, 101.0, 100.0, 100.0) for i in range(20)]
    guard("Z1 the width is the instrument's own MEDIAN HOURLY WICK, measured",
          lambda: abs(B.zone_width(bars) - 1.0) < 1e-9)
    guard("Z1b an empty frame yields no width, not a zero",
          lambda: B.zone_width([]) is None)

    def L(p, t):
        return {"price": p, "formed_ts": pd.Timestamp(f"2026-09-{t:02d}", tz="UTC")}

    # 100.0 / 100.4 / 100.7 cluster at width 1.0; 103.0 is separate
    lv = [L(100.0, 1), L(100.4, 3), L(100.7, 2), L(103.0, 4)]
    try:
        zs = _zones(lv, 1.0)
    except Exception:
        zs = []
    guard("Z2 levels within a wick of each other are ONE zone",
          lambda: len(zs) == 2 and len(zs[0]["members"]) == 3,
          f"{[(z['lo'], z['hi']) for z in zs]}")
    guard("Z2b the zone's edges are its outermost members",
          lambda: zs[0]["lo"] == 100.0 and zs[0]["hi"] == 100.7)
    guard("Z2c the SEED is the NEWEST member — recency is the first discriminator",
          lambda: zs[0]["seed"]["price"] == 100.4)

    # ── the property that made the first implementation worthless ───────────
    import random

    def _stable():
        sig, same = None, True
        for _ in range(12):
            shuffled = lv[:]
            random.shuffle(shuffled)
            z = _zones(shuffled, 1.0)
            sg = [(round(x["lo"], 6), round(x["hi"], 6), len(x["members"])) for x in z]
            sig = sg if sig is None else sig
            same = same and (sg == sig)
        return same

    guard("Z3 the partition is ORDER-INDEPENDENT — a fixed point, not a first pass",
          _stable, "the first cut printed a price inside another zone's span")
    guard("Z3b zones never overlap",
          lambda: all(zs[i]["hi"] < zs[i + 1]["lo"] for i in range(len(zs) - 1)))
    guard("Z3c every level lands in exactly one zone",
          lambda: sum(len(z["members"]) for z in zs) == len(lv))
    guard("Z4 no width means no grouping — it fails OPEN to the pre-zone board",
          lambda: len(_zones(lv, None)) == len(lv), "one zone per level")

    # ── the board: cluster BEFORE the walk, and no 'inside' answer ──────────
    from derived.levels import LevelEngine
    from data.derived_store import DerivedStore
    ds = DerivedStore(path=os.path.join(tempfile.mkdtemp(), "d.db"))
    ds.mark_level_sync("TST", _tm.time())         # CD.2: the book is synced "now"
    eng = LevelEngine.__new__(LevelEngine)
    eng._store, eng.symbol, eng._forks = ds, "TST", None
    eng._zone_width = B.zone_width(bars)          # what _book_sync sets from the book
    import time
    now = time.time()
    for i, p in enumerate([100.0, 100.4, 100.7, 103.0, 96.0, 95.6]):
        ds.upsert_level((f"TST:ny:{p:.2f}", "TST", p,
                         "resistance" if p > 98 else "support", "ny",
                         "session:2026-09-01", now - 1000 * (i + 1), 0, None, 0, None, None, 1))
    ds.commit()
    b = eng.board(98.0)
    up = b.get("above") or []
    guard("Z5 board() reports a computed width", lambda: b.get("zone_width") == 1.0,
          str(b.get("zone_width")))
    guard("Z5b the cluster reaches the board as ONE rung, not three",
          lambda: up[0]["zone_n"] == 3 and up[0]["near_edge"] == 100.0,
          f"rungs={[(r.get('near_edge'), r.get('zone_n')) for r in up]}")
    guard("Z5c a plan trades the NEAR edge; the FAR edge is what a breach needs",
          lambda: up[0]["near_edge"] == 100.0 and up[0]["far_edge"] == 100.7)
    guard("Z5d a breach carries EVERY member — the ids travel with the rung",
          lambda: len(up[0]["zone_ids"]) == 3)
    guard("Z6 there is no 'inside' answer — a zone holding price is retired, not reported",
          lambda: "inside" not in b, "the operator's ruling")

    # ── and the one that defeated the first build ──────────────────────────
    src = open(os.path.join(ROOT, "derived", "levels.py"), encoding="utf-8").read()
    board = src[src.index("    def board("):src.index("\n    def ", src.index("    def board(") + 10)]
    code = "\n".join(l for l in board.splitlines() if not l.strip().startswith("#"))
    guard("Z7 board() does NOT pre-thin with _walked — it clusters, THEN walks",
          lambda: "_walked(" not in code,
          "r29's per-level walk discarded cluster members before grouping saw them")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
