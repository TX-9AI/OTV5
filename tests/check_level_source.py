#!/usr/bin/env python3
"""
tests/check_level_source.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.1  CD.2 (2026-10-24) - the fixture marks the level book SYNCED (store.mark_level_sync) after seeding the ledger:
      LevelEngine.board() now fails closed as not_synced until a book sync against a recent closed 1m bar has been
      recorded (derived/levels v6.10). Every expectation is unchanged.
v1.0  2026-09-17  OTV4TEST r33 — born red 12 of 16 at r32 (6587143), which is the
      divergence reproduced exactly: S1/S2/S4 on the sweep's and the TCS's private
      compositions, S5/S6 on a board that could not walk from spot, S9/S11-S16 on
      an accessor that had no anchor, no shared entry point and no fork product.
ONE BOARD FOR EVERY PLAN THAT TRADES LEVELS, AND THE FORK BESIDE IT (OTV4TEST r33).

WHY THIS FILE EXISTS. The operator ruled it at r5 — *"LEVELS IN PLAY come from
the derived store, NEVER A PRIVATE MAP: 3 named up, 3 named down, plus the 1h
pitchfork's tines"* — and on 2026-09-17 three plans had three private
compositions of that one board:
  · `liquidity_hunt` through `board()`                       (correct)
  · `sweep_plan`  through `live_levels()` + a local `level_map.walk()` with the
    rails APPENDED INTO the level list                        (r19 conjoined)
  · `tcs_plan`    through `live_levels()` filtered to `provenance == "ny"`,
    with no fork at all                                       (3 of 11 levels)

⚠️ NOT ONE GATE IN THIS REPO COULD SEE THAT. The write map says who writes a
table; the file map says who imports what; `check_map_accuracy` checks tables,
units and entry points. None of them can tell that two plans ask one store two
different questions. That is why the divergence survived r15, r19, r29 and r30 —
every one of which touched levels — and surfaced only when a human read the code.

S1/S2 are the ABSENCE canaries and are scoped to a CALL SITE, never a mention
(§20): a changelog that says "this no longer calls live_levels()" must not trip
them, which is why they match `store.live_levels(` and `level_map.walk(` rather
than the bare names.
"""
import os
import time
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_TRADES_DB", os.path.join(tempfile.mkdtemp(), "t.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(tempfile.mkdtemp(), "d.db"))

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def src(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


# the plans that trade levels. orb/runaway/butterflies read none by ruling (r20).
LEVEL_PLANS = ("strategy/sweep_plan.py", "strategy/tcs_plan.py", "strategy/liquidity_hunt.py")


def main():
    # ── S1/S2/S3 — no plan composes its own board ───────────────────────────
    # ⚠️ THESE READ THE AST, NOT THE TEXT, AND THE FIRST CUT PROVED WHY. Written
    # as string matches they went red on this revision's OWN changelog line —
    # the comment in `sweep_plan` that says it no longer calls `level_map.walk()`
    # contains `level_map.walk(`. That is §20 exactly: good hygiene creates the
    # false positive, and a canary that fires on documentation is the one that
    # gets loosened and then misses the real regression. Calls only.
    import ast

    def calls(rel):
        """Every call in the module as ('receiver', 'attr') or (None, 'name')."""
        out = []
        for node in ast.walk(ast.parse(src(rel))):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            if isinstance(f, ast.Attribute):
                recv = f.value.id if isinstance(f.value, ast.Name) else (
                    f.value.attr if isinstance(f.value, ast.Attribute) else None)
                out.append((recv, f.attr))
            elif isinstance(f, ast.Name):
                out.append((None, f.id))
        return out

    bad = [p for p in LEVEL_PLANS if any(a == "live_levels" for _, a in calls(p))]
    check("S1 no level-trading plan CALLS live_levels() — one board, not a private read",
          not bad, ", ".join(bad) or "none")

    bad = [p for p in LEVEL_PLANS
           if any(r in ("level_map", "_lm") and a == "walk" for r, a in calls(p))]
    check("S2 no level-trading plan runs its own level_map.walk()",
          not bad, ", ".join(bad) or "none")

    # S3 stays textual BY DESIGN: it is a comparison, not a call, so there is no
    # node to match — and it is scoped to the operator expression, not to "ny".
    bad = [p for p in LEVEL_PLANS
           if re.search(r"provenance\"\]\s*==\s*[\"']ny[\"']", src(p))
           or re.search(r"provenance'\]\s*==\s*[\"']ny[\"']", src(p))]
    check("S3 no plan filters the board by session provenance",
          not bad, ", ".join(bad) or "none")

    # ── S4 — every one of them reaches the single accessor ──────────────────
    missing = [p for p in LEVEL_PLANS
               if "board_for(" not in src(p) and ".board(" not in src(p)]
    check("S4 every level-trading plan reaches the ONE entry point (board_for)",
          not missing, ", ".join(missing) or "none")

    # ── the board itself, driven, not read ──────────────────────────────────
    from data.derived_store import DerivedStore
    from derived.levels import LevelEngine
    ds = DerivedStore(path=os.path.join(tempfile.mkdtemp(), "derived.db"))
    ds.mark_level_sync("TST", time.time())        # CD.2: the book is synced "now"
    eng = LevelEngine.__new__(LevelEngine)
    eng._store = ds
    eng.symbol = "TST"
    eng._forks = None

    import time as _t
    now = _t.time()
    # three up and three down, on THREE DIFFERENT sessions, newest first
    rows = [("TST:ny:105.00", 105.0, "resistance", "ny", now - 100),
            ("TST:london:107.00", 107.0, "resistance", "london", now - 200),
            ("TST:asia:109.00", 109.0, "resistance", "asia", now - 300),
            ("TST:ny:95.00", 95.0, "support", "ny", now - 100),
            ("TST:london:93.00", 93.0, "support", "london", now - 200),
            ("TST:asia:91.00", 91.0, "support", "asia", now - 300)]
    for lid, price, kind, prov, cts in rows:
        ds.upsert_level((lid, "TST", price, kind, prov, "session", cts, 0, None, 0, None, None, 1))

    b = eng.board(100.0)
    provs_up = [l["provenance"] for l in b.get("above", [])]
    provs_dn = [l["provenance"] for l in b.get("below", [])]
    check("S5 with no ORB bounds the board walks from SPOT and is session-blind",
          b.get("state", None) == "ok" and b.get("anchor", None) == "spot"
          and provs_up == ["ny", "london", "asia"] and provs_dn == ["ny", "london", "asia"],
          f"up={provs_up} down={provs_dn} anchor={b.get('anchor')}")

    check("S6 three up and three down, nearest first, each older one further out",
          [l["price"] for l in b.get("above", [])] == [105.0, 107.0, 109.0]
          and [l["price"] for l in b.get("below", [])] == [95.0, 93.0, 91.0],
          f"{[l['price'] for l in b['above']]} / {[l['price'] for l in b['below']]}")

    check("S7 no fork is an EXPLICIT answer, not an empty list",
          b.get("fork", None) == "absent" and b.get("tines", []) == [], f"fork={b['fork']}")

    # the fork is a SECOND product: never inside above/below (r19)
    check("S8 the rails are never in above/below",
          not any(str(l["provenance"]).startswith("fork1h/") for l in b.get("above", []) + b.get("below", [])),
          "no fork1h/* among the levels")

    # ── S9 — the ORB anchoring still answers the hunt's question (r12) ──────
    br = eng.board(100.0, orb_high=106.0, orb_low=94.0)
    check("S9 with ORB bounds it still measures reach from the RANGE EDGE (r12)",
          br.get("anchor", None) == "range" and [l["price"] for l in br.get("above", [])] == [107.0, 109.0]
          and [l["price"] for l in br.get("below", [])] == [93.0, 91.0],
          f"up={[l['price'] for l in br['above']]} down={[l['price'] for l in br['below']]}")

    check("S10 a HALF range is no_range, not a silent spot walk (fails closed)",
          eng.board(100.0, orb_high=106.0).get("state") == "no_range",
          eng.board(100.0, orb_high=106.0).get("state"))

    # ── S12-S15 — THE FORK IS A SECOND PRODUCT AND AN "OR" LEVEL ────────────
    # Operator, 2026-09-17: *"every PLAN that reads levels must also read the
    # fork projection if/while it exists… lower fork tines projected below spot
    # must inform the plan that they are a support level, and upper fork tines
    # projected above spot that a valid resistance exists above spot"*, and
    # *"the fork is an OR level not an AND"* — one of the mapped levels OR a
    # fork rail, never a rail required to confirm a level.
    class _Fork:
        """A 1h fork whose UPPER rail sits above spot and LOWER below it."""
        def __init__(self, up, lo):
            self._up, self._lo = up, lo
            self.p0 = self.p1 = self.p2 = type("P", (), {"idx": 1, "price": 100.0})()
        def upper_at(self, idx):  return self._up
        def lower_at(self, idx):  return self._lo
        def median_at(self, idx): return (self._up + self._lo) / 2.0

    class _FE:
        def __init__(self, fork):
            self.last_forks = {"1h": fork}

    eng._forks = _FE(_Fork(up=103.0, lo=97.0))
    bf = eng.board(100.0)
    provs = [t["provenance"] for t in bf.get("tines", [])]
    check("S12 with a fork held, the rails come back as a SECOND product",
          bf.get("fork", None) == "built" and bf.get("tines", []), f"fork={bf['fork']} rails={provs}")

    by_kind = {t["provenance"]: (t["kind"], t["price"]) for t in bf.get("tines", [])}
    up = by_kind.get("fork1h/upper"); dn = by_kind.get("fork1h/lower")
    check("S13 kind is WHERE THE PROJECTION SITS: upper above spot = resistance, lower below = support",
          up and up[0] == "resistance" and up[1] > 100.0
          and dn and dn[0] == "support" and dn[1] < 100.0, f"upper={up} lower={dn}")

    check("S14 the rails are STILL not in above/below — an OR candidate, not a merged level",
          not any(str(l["provenance"]).startswith("fork1h/")
                  for l in bf.get("above", []) + bf.get("below", []))
          and [l["price"] for l in bf.get("above", [])] == [105.0, 107.0, 109.0],
          "levels unchanged by the fork's presence")

    # r5's TINE RULE: a top tine can never be a floor. Put BOTH rails above spot.
    eng._forks = _FE(_Fork(up=106.0, lo=104.0))
    bw = eng.board(100.0)
    kinds = {t["provenance"]: t["kind"] for t in bw.get("tines", [])}
    check("S15 a rail on the wrong side of spot is DROPPED, never relabelled (r5's tine rule)",
          "fork1h/lower" not in kinds and kinds.get("fork1h/upper") == "resistance",
          f"offered={kinds}")

    # and absence is still an answer, not a gap — the "not mandatory" half
    eng._forks = None
    check("S16 with no fork the plans still get their levels — an OR, never an AND",
          eng.board(100.0).get("fork") == "absent"
          and len(eng.board(100.0).get("above", [])) == 3,
          "levels stand alone")

    # ── S11 — walk() holds no composition of its own ────────────────────────
    w = eng.walk(100.0)
    check("S11 walk() delegates to the board — one implementation, not two",
          [l["price"] for l in w.get("above", [])] == [l["price"] for l in b.get("above", [])]
          and [l["price"] for l in w.get("below", [])] == [l["price"] for l in b.get("below", [])],
          "walk == board(spot)")

    print()
    if FAILED:
        print(f"FAIL — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("PASS — check_level_source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
