#!/usr/bin/env python3
"""
tests/check_levels_in_play.py  v5.1
v5.1  2026-11-08  OTV5 r76 (RETIRE.1) — RE-POINTED (WA 38.4): the sweep plan, whose levels_in_play the P and E sections drove, is removed with the
      sweep, so P0-P? and E go with it; C1-C5 (every remaining consumer - the TCS plan and the Hunt - ranks through the one
      shared rails_after_held, declares and records the rails, never lets a rail outrank a held extreme) are kept.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.3  2026-10-24  CD.2 - the seeded REJECTED carries its market time and the session open is pinned; the fixture
      marks the level book SYNCED after creating its store: LevelEngine.board() fails
      closed as not_synced until a recent book sync is recorded (derived/levels v6.10). Expectations unchanged.
v1.2  2026-10-19  OTV4TEST r303 (PSTATE.1) — its subject SweepCreditSpread is DORMANT by default and a dormant plan now
      writes nothing by ruling, so this run switches it ACTIVE (OT_SWEEP_CS=1); what it pins is unchanged.
v1.1  2026-09-22  OTV4TEST r104 - C1-C5: EVERY CONSUMER, NOT JUST THE
      SWEEP. r15, r19 and r33 each settled this at the producer and gated the
      producer; nothing asserted what a READER did next, so the conjunction was
      rebuilt at read time in three different plans while every gate stayed
      green. Born red at 6ab77e2 naming tcs_plan:332 and liquidity_hunt:199-200.
      C2 RESOLVES THE IMPORT ALIAS - it went red on correct code until it
      followed `rails_after_held as _raf` to the name actually called.
v1.0  2026-09-22  OTV4TEST r103 — born RED at 4a7da4f, where `levels_in_play`
      does not exist and P0 NAMES that rather than dying on a traceback.

r103 — THE RAILS MAY NOT TAKE A HELD EXTREME'S SLOT.

🔴 SETTLED THREE TIMES AT THE PRODUCER, NEVER ONCE AT THE CONSUMER. r15 removed
`_tines()` from `_sources()`; r19 stopped any pool flagged `moving` reaching
`level_ledger` at all, after 22 simultaneously-live "1h upper tine" rows
spanning 5.79 points were found in it; r33 gave every level-trading plan ONE
accessor. `board()` has been correct since r19 and says so in its own
docstring: *"THE FORK IS A SECOND PRODUCT, NOT A LEVEL IN THIS LIST ... NEVER
merged into above/below (r19: co-inform, do not conjoin)"*.

🔴 AND r33 WROTE THE CONJUNCTION ITSELF. The same revision titled "THE FORK
BESIDE IT AS AN OR LEVEL" added `levels = levels + tines` ONE LINE ABOVE the
`[:LEVELS_EACH_SIDE]` slice — so a rail nearer to spot claimed a slot and the
furthest-out held extreme fell off the board. Every gate stayed green, because
every gate asserted what `board()` RETURNS and none asserted what a CONSUMER
does with it. §23 — fix every reader, not just the writer.

🔑 THE TWO ARE DIFFERENT KINDS OF THING. Operator 2026-09-22: *"The pitchfork is
a co-informer and does not live in the liquidity level levels ... it's a moving
target it has to be a separate artifact"*, and *"It's not a LIQUIDITY level.
It's just a respected level."* A held extreme is a fixed price with resting
stops beyond it — that pool is what a sweep RAIDS. A rail holds no pool.

⚠️ THE RAILS ARE NOT WITHDRAWN, AND P2 PINS THAT. Asked directly whether they
should leave this plan, the operator ruled: *"The sweep still works with the
pitchfork, because the channel is respected."* PLUS, not competing.

  P0  the machinery exists                      (guard, not a check)
  P1  rails nearer than the held extremes DO NOT displace them
  P2  ...and the rails are still in play        (not a withdrawal)
  P3  held and rail counts stay separable
  P4  fewer than the limit is an answer, never padded
  P5  the cap binds the held extremes, and ONLY them
  P6  the regression line r33 wrote is absent from the plan

Run:  venv/bin/python tests/check_levels_in_play.py
"""
from __future__ import annotations

import glob
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# ⚠️ The lander runs CHECKs under system `python3`; the SDK lives in the venv.
for _sp in glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
_s = tempfile.mkdtemp(prefix="check_levels_in_play.")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_s, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))

FAIL: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])


import ast as _a2                                                # noqa: E402

# ══ C — EVERY CONSUMER, NOT JUST THE SWEEP ════════════════════════════════
# 🔴 THE REASON THIS SUBJECT RECURRED FOR THREE REVISIONS. r15, r19 and r33
# each settled the separation AT THE PRODUCER and gated the producer. Every
# gate asserted what `board()` RETURNS — which was always correct — and none
# asserted what a CONSUMER did next. So the conjunction was rebuilt at read
# time, three times, in three different plans, while every check stayed green.
# §23: fix every reader, not just the writer. This block reads every reader.
_PLANS = {
    "strategy/tcs_plan.py":       "TCSPlan",
    "strategy/liquidity_hunt.py": "LiquidityHunt",
}

# ── C1 — NO PLAN MERGES RAILS INTO THE RANKING ────────────────────────────
# ⚠️ STRUCTURAL, NOT TEXTUAL. Greping the literal went red on its own docstring
# (§20). This walks the AST for an ADD whose two sides mix a rail-ish name with
# a level-ish one, in any spelling: `levels + tines`, `b["above"] + tines_up`.
_merges = []
for _f in _PLANS:
    try:
        _t = _a2.parse(open(os.path.join(ROOT, _f), encoding="utf-8").read())
    except Exception as _pe:                                     # noqa: BLE001
        _merges.append(f"{_f}:unparseable:{_pe}")
        continue
    for _n in _a2.walk(_t):
        if not (isinstance(_n, _a2.BinOp) and isinstance(_n.op, _a2.Add)):
            continue
        try:
            _l, _r = _a2.unparse(_n.left).lower(), _a2.unparse(_n.right).lower()
        except Exception:                                        # noqa: BLE001
            continue
        _railish = lambda x: ("tine" in x or "rail" in x)        # noqa: E731
        _levish = lambda x: ("level" in x or "above" in x or "below" in x
                             or "held" in x)                     # noqa: E731
        if (_railish(_l) and _levish(_r)) or (_railish(_r) and _levish(_l)):
            _merges.append(f"{_f}:{_n.lineno}")
check("C1 no plan merges rails into the level ranking", not _merges,
      f"{_merges}" if _merges else f"{len(_PLANS)} plans walked, clean")

# ── C2 — AND THEY ALL USE THE ONE SHARED INVARIANT ────────────────────────
# ⚠️ ABSENCE OF THE MERGE IS NOT PRESENCE OF THE RULE. A plan could drop the
# rails entirely and pass C1. Three private copies of "rails last" is three
# chances to drift — which is exactly how three plans ended up with three
# private compositions before r33.
_uses = []
for _f in _PLANS:
    _src2 = open(os.path.join(ROOT, _f), encoding="utf-8").read()
    _tt = _a2.parse(_src2)
    # ⚠️ RESOLVE THE ALIAS. All three import it as `rails_after_held as _raf`,
    # so the Call node reads `_raf(...)` and a name match on the original
    # SPELLING finds nothing — this check went red on correct code until it
    # followed the import. Asserting on a name without resolving how it was
    # bound is the same class of error as grepping for a moved symbol.
    _bound = set()
    for _n in _a2.walk(_tt):
        if isinstance(_n, _a2.ImportFrom):
            for _al in _n.names:
                if _al.name == "rails_after_held":
                    _bound.add(_al.asname or _al.name)
    _ok2 = bool(_bound) and any(
        isinstance(_n, _a2.Call)
        and isinstance(_n.func, _a2.Name) and _n.func.id in _bound
        for _n in _a2.walk(_tt))
    if not _ok2:
        _uses.append(_f)
check("C2 every plan ranks through the shared rails_after_held", not _uses,
      f"not using it: {_uses}" if _uses else "one definition, three callers")

# ── C3 — THE RAIL COUNT IS ITS OWN NUMBER, EVERYWHERE ─────────────────────
# 🔴 One combined count makes a board of three rails read identically to three
# held extremes — the conflation r19 exists to prevent, invisible in the data.
_missing_cnt = []
for _f, _cls in _PLANS.items():
    _mod = __import__(_f[:-3].replace("/", "."), fromlist=[_cls])
    _decl = set(getattr(getattr(_mod, _cls), "PLAN_CHECKS", ()) or ())
    if "rails_in_play" not in _decl:
        _missing_cnt.append(_cls)
check("C3 every plan declares rails_in_play separately", not _missing_cnt,
      f"missing: {_missing_cnt}" if _missing_cnt else "all three declare it")

# ── C4 — AND EVERY PLAN RECORDS THE RAIL CONTEXT ──────────────────────────
# 🔑 The distinction the operator drew — "0.3% from a HARD held extreme" vs
# "0.3% from a SOFT respected rail" — is only answerable if the distance is on
# the row. Before r103/r104 the TCS and the hunt recorded `fork: built/absent`
# and nothing else.
_no_ctx = [_f for _f in _PLANS
           if "rail_context" not in open(os.path.join(ROOT, _f), encoding="utf-8").read()]
check("C4 every plan records the rail context", not _no_ctx,
      f"missing: {_no_ctx}" if _no_ctx else "all three stamp it")

# ── C5 — THE INVARIANT ITSELF, SWEPT ──────────────────────────────────────
# ⚠️ Asserted as a PROPERTY over many arrangements rather than at one point: a
# rail must never outrank a held extreme, however the prices fall.
from derived.levels import rails_after_held as _RAF                # noqa: E402
_bad5 = []
for _rp in (0.1, 1.0, 5.0, 50.0):
    _held5 = [{"provenance": "ny", "price": 100.0 + _rp},
              {"provenance": "london", "price": 100.0 + _rp * 2}]
    _rail5 = [{"provenance": "fork1h/upper", "price": 100.0 + _rp / 10.0}]
    _out5 = _RAF(_held5, _rail5, key=lambda l: float(l["price"]))
    if _out5[0]["provenance"].startswith("fork1h/"):
        _bad5.append(_rp)
check("C5 a rail never ranks first while a held extreme exists", not _bad5,
      f"rail won at offsets {_bad5}" if _bad5 else "swept 4 arrangements")

if FAIL:
    print(f"\nRED — {len(FAIL)} failed: {', '.join(FAIL)}")
    sys.exit(1)
print("\nGREEN — held extremes claim their slots; the rails join beside them")
sys.exit(0)
