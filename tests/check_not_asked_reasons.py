#!/usr/bin/env python3
"""
tests/check_not_asked_reasons.py  v1.1
v1.1  2026-10-19  OTV4TEST r303 (PSTATE.1) — its subjects SweepCreditSpread / TrendCreditSpread are DORMANT by default, and a
      dormant plan now writes nothing by ruling, so this run switches both ACTIVE (OT_SWEEP_CS=1, OT_TCS_ACTIVE=1)
      to test the board's mechanics on plans that write. tests/check_plan_states.py pins the dormant side.
      N1 RE-POINTED by ruling (the operator, 2026-10-19 09:54 ET: "Yes" - a condition-gated plan writes nothing
      while its condition is absent): on a flat tick NO management plan writes a row, and none reads as a dispatch
      gap. N3 pins the setdefault precedence where it now lives - the skip reasons close_tick reads - since the
      management row it used to read is no longer written.
v1.0  2026-09-01  r213 (chunk E) — EVERY SKIP NAMES ITSELF.

Operator, 2026-09-01, reading the DECISIONS panel: *"I don't like 'NOT ASKED'
as a reason. It makes no sense. Not asked? why or Why not?"*

He was reading rows like `CondorManagement  NOT ASKED  /  not asked this tick —
dispatch gave no reason`, where the reason restated the verdict and told him
nothing.

🔴 THE CAUSE IS NOT THE WORDING, IT IS A GAP. `CondorManagement`, `CreditRoll`
and every `<Strategy>/manage` row are driven ONLY from main.py's
`has_open_position()` branch. On a flat box they are never called, and no skip
site named them, so they fell to the default on every tick of every flat
session. The other half of that same branch already said the reverse out loud —
"position open — managing; only the second-leg window asks the credit
strategies" — so one direction had a sentence and the other did not.

⚠️ AND A `/manage` ENTRY OUTLIVES ITS POSITION. `REGISTRY` persists for the life
of the process, so once a strategy has managed anything its row keeps reporting
for the rest of the day, long after the trade closed.

🔑 THE DEFAULT NOW ADMITS WHAT IT IS. Every skip main.py can name IS named; the
fallback fires only where none is, so it reads as a dispatch gap rather than a
market condition. r73's rule one level up: a refusal that cannot say which rung
refused it is worse than no refusal, because it gets trusted anyway.

⚠️ THE MEMBERSHIP LIST LIVES IN plan.py, NOT main.py. A new management plan is
covered by REGISTERING, not by someone remembering to add it to a list in
another file — r35's allow-list rot, where a name list held three entries, two
of which had been deleted, while the live strategy was silently exempt.

Born red at 540a807 (r212), where N1, N2 and N4 fail.
"""
from __future__ import annotations

import ast
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ["OT_SWEEP_CS"] = "1"     # r303: the subjects write (dormant plans write nothing - check_plan_states)
os.environ["OT_TCS_ACTIVE"] = "1"

_fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


def main():
    from strategy import plan as P

    missing = [n for n in ("skipped_management", "_MANAGEMENT_PLANS")
               if not hasattr(P, n)]
    if missing:
        for n in missing:
            check(f"N0 plan.{n} exists", False, "not implemented")
        print()
        print(f"FAILED {len(_fails)}: plan.py is pre-r213 "
              f"(missing {', '.join(missing)})")
        return 1

    # ── N1 — EXECUTED: a flat tick names every management plan ───────────
    # 🔑 The whole defect is a call that was never made, so reading source
    # would prove nothing (§21). This registers the real plans, runs the real
    # skip, and reads what `close_tick` would write.
    import sqlite3

    class _St:
        def __init__(s):
            s.conn = sqlite3.connect(":memory:"); s.conn.row_factory = sqlite3.Row
        def commit(s): s.conn.commit()

    st = _St(); P.ensure_tables(st); P.bind_store(st)
    P.REGISTRY.clear()
    P.Plan("CondorManagement", ("legs",), self_ledgers=True)
    P.Plan("CreditRoll", ("legs",), self_ledgers=True)
    P.Plan("ORBStrategy/manage", ("legs",), self_ledgers=True)
    P.Plan("SweepCreditSpread", ("age",))

    P.begin_tick(500.0)
    P.skipped_management("no open position — nothing to manage")
    P.close_tick(st, "TST")
    rows = {r["strategy"]: (r["verdict"], r["reason"]) for r in
            st.conn.execute("SELECT strategy, verdict, reason FROM plan_tick"
                            " WHERE ts_epoch=500.0")}
    mgmt = ("CondorManagement", "CreditRoll", "ORBStrategy/manage")
    written = [m for m in mgmt if m in rows]
    check("N1 on a flat tick no management plan writes a row (r303: condition absent), none as a dispatch gap",
          not written, f"written: {[(m, rows[m]) for m in written]}")

    # ── N2 — and an ENTRY strategy is NOT swept up with them ─────────────
    # ⚠️ THE SEPARATION IS THE POINT. "Nothing to manage" is true of the
    # management plans and false of the entry strategies, and a reason that is
    # wrong is worse than one that is missing — it looks like an answer.
    check("N2 an entry strategy is not given a management reason",
          "SweepCreditSpread" in rows
          and "nothing to manage" not in (rows["SweepCreditSpread"][1] or ""),
          f"{rows.get('SweepCreditSpread')}")

    # ── N3 — a more specific reason WINS ────────────────────────────────
    # `setdefault`, not assignment: a plan already skipped for a real cause
    # keeps that cause.
    P.REGISTRY.clear()
    P.Plan("CondorManagement", ("legs",), self_ledgers=True)
    P.begin_tick(501.0)
    P.skipped("CondorManagement", "DIRECTIONAL_ONLY box")
    P.skipped_management("no open position — nothing to manage")
    r501 = P._SKIPPED.get("CondorManagement")                   # r303: the reason close_tick would read
    P.close_tick(st, "TST")
    check("N3 a specific skip reason is not overwritten by the generic one",
          r501 and "DIRECTIONAL_ONLY" in r501, f"{r501!r}")

    # ── N4 — the fallback admits it is a DISPATCH GAP ───────────────────
    # It fires only where main.py named nothing, so it must read as a defect
    # rather than as a status — otherwise it gets scrolled past forever, which
    # is how it survived this long.
    P.REGISTRY.clear()
    P.Plan("TrendCreditSpread", ("adx",))
    P.begin_tick(502.0)
    P.close_tick(st, "TST")
    r502 = st.conn.execute("SELECT verdict, reason FROM plan_tick"
                           " WHERE ts_epoch=502.0").fetchone()
    why = (r502["reason"] or "") if r502 else ""
    check("N4 an unexplained skip says it is a dispatch gap",
          "dispatch gap" in why and "no reason recorded" in why,
          why[:70])
    check("N4b and it no longer merely restates the verdict",
          "dispatch gave no reason" not in why,
          "the old text told the operator nothing")

    # ── N5 — the membership list lives with the registry, not in main ────
    # r35: an allow-list in another file rots permissively. It held three
    # names, two of which had been deleted, while RunawayContinuation was
    # absent and therefore silently EXEMPT from the debit cutoff.
    msrc = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    mtree = ast.parse(msrc, "main.py")
    lits = {n.value for n in ast.walk(mtree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    check("N5 main.py holds no copy of the management-plan names",
          "CondorManagement" not in lits and "CreditRoll" not in lits,
          "membership is decided where the plans register")

    # ── N6 — the flat branch actually calls it ──────────────────────────
    calls = {c.func.id for c in ast.walk(mtree)
             if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    check("N6 main.py's flat branch calls the management skip",
          "_plan_skip_management" in calls)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_not_asked_reasons: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
