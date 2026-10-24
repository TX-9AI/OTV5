#!/usr/bin/env python3
"""
tests/check_anchors.py  v1.1
v1.1  2026-09-10  A1 stubs the store accessor, not the singleton: a box with a live
      derived_store.db opened it lazily and returned real VWAP. Found on the first land.
v1.0  2026-09-09  OTV4TEST r12 — ANCHORS ARE RECORDED, NEVER DECIDED ON.

  A1  every read returns None (not an exception) with no store bound
  A2  stamp() writes anchor_* checks with verdict None (record only)
  A3  a string anchor (fork direction) is mapped to ±1, never a bare string
  A4  every plan file stamps at least one anchor (source pin)
  A5  no plan reads an anchor into a decision (no `anchor_` in a refuse/hold/unmet)
  A6  (HYG.1) trade_readiness._combine and momentum_val are module-level and callable

Run:  python3 tests/check_anchors.py
"""
import os
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


def main():
    from derived import anchors as A
    # v1.1 — stub the module's own store accessor: on a box the singleton lazily
    # OPENS the real store, so "no store bound" was not "no store" (r12's first
    # land failed here on the QQQ TEST box with a live derived_store.db).
    _real = A._store
    A._store = lambda: None
    try:
        vals = [A.charm_at(100.0), A.vanna_at(100.0), A.gex_at(100.0), A.gex_between(99, 101), A.vwap(),
                A.fork_dir("15m"), A.nearest_tine(100.0), A.oi_at(100.0, None)]
        check("A1 every read returns None with no store (coverage fact, not an exception)", all(v is None for v in vals), str(vals))
    finally:
        A._store = _real
    from strategy import plan as P
    class St:
        def __init__(s): s.conn = sqlite3.connect(":memory:"); s.conn.row_factory = sqlite3.Row
        def commit(s): s.conn.commit()
    st = St(); P.ensure_tables(st); P.bind_store(st)
    pl = P.Plan("AnchorTest", ("x",), record_only=True, self_ledgers=True)
    P.begin_tick(1.0)
    t = pl.tick(100.0)
    A.stamp(t, charm_at_strike=0.12, fork15="bearish", missing=None)
    check("A2 stamp writes anchor_* checks with verdict None",
          t.checks.get("anchor_charm_at_strike") == (0.12, None) and t.checks.get("anchor_missing") == (None, None),
          str({k: v for k, v in t.checks.items() if k.startswith("anchor_")}))
    check("A3 a direction string is mapped to ±1", t.checks.get("anchor_fork15") == (-1.0, None))
    t.hold("done"); P.close_tick(st, "TST")
    plans = ["strategy/orb_plan.py", "strategy/runaway_plan.py", "strategy/sweep_plan.py",
             "strategy/tcs_plan.py", "strategy/gex_pin_butterfly.py", "strategy/iron_condor_strategy.py"]
    missing = [p for p in plans if "_A.stamp(" not in open(os.path.join(_root, p), encoding="utf-8").read()]
    check("A4 every plan stamps at least one anchor", not missing, str(missing))
    bad = []
    for p in plans:
        src = open(os.path.join(_root, p), encoding="utf-8").read()
        for line in src.splitlines():
            if ("refuse(" in line or "unmet.append(" in line or "structural.append(" in line) and "anchor_" in line:
                bad.append(f"{p}: {line.strip()[:60]}")
    check("A5 no plan decides on an anchor", not bad, str(bad))
    import analysis.trade_readiness as TR
    check("A6 (HYG.1) _combine and momentum_val are module-level and callable",
          callable(getattr(TR, "_combine", None)) and TR._combine([1.0], [0.5], [(1.0, 0.8)]) == 0.4
          and TR.momentum_val("FLAT") == 0.5)
    print()
    if FAILED:
        print(f"FAIL — {len(FAILED)} check(s): {FAILED}"); return 1
    print("PASS — check_anchors"); return 0


if __name__ == "__main__":
    sys.exit(main())
