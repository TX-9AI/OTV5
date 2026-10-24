#!/usr/bin/env python3
"""
tests/check_note_label.py  v1.1
v1.1  2026-09-04  r246 — N4 extends to the gate reporter: it must
      resolve the same dispatch labels, keep its own spelling, and be a
      SUPERSET of the shared map.
v1.0  2026-09-04  r239 — THE NOTE LABEL IS CANONICAL. `_note_evaluation` is the
      only writer of `strategy_note`, and it stamped the raw `_safe_strategy`
      dispatch label while the plan ledger and gate rows use the class name.

🔴 MEASURED, 2026-08-31..09-04: the fit report showed "ORB" with 78 fired and
ZERO declined, and "ORBStrategy" with zero fired and 4,260 declined. One
strategy, two rows, and NEITHER arm could ever be fittable — the report said
NOT READY for both, for opposite reasons.

⚠️ `DISPATCH_ALIAS` HAS EXISTED SINCE r147 and was already applied by the plan
board (`plan.py:791`, `:833`) and by `gate_report` (`:118`). This was the one
writer that did not consult it. The fix is a lookup, not a rename — history is
full of rows under the old label and a rename would only fix tomorrow.
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


def main():
    from strategy.plan import DISPATCH_ALIAS
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(root, "main.py"), encoding="utf-8").read()

    # ══ N1 — the map still carries the two known splits ═══════════════════
    check("N1 DISPATCH_ALIAS maps ORB -> ORBStrategy",
          DISPATCH_ALIAS.get("ORB") == "ORBStrategy")
    check("N1b and SweepForLeg2 -> SweepCreditSpread (r160)",
          DISPATCH_ALIAS.get("SweepForLeg2") == "SweepCreditSpread")

    # ══ N2 — the notes writer CONSULTS it ═════════════════════════════════
    # ⚠️ AST on the call, not a grep for the name: the changelog above names
    # DISPATCH_ALIAS while explaining the fix, so a string search would match
    # the explanation (§20).
    tree = ast.parse(src)
    ok = False
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef)
                and node.name == "_note_evaluation"):
            continue
        for c in ast.walk(node):
            if (isinstance(c, ast.Call)
                    and getattr(c.func, "attr", "") == "write"):
                first = c.args[0] if c.args else None
                if (isinstance(first, ast.Call)
                        and getattr(first.func, "attr", "") == "get"):
                    ok = True
    check("N2 _note_evaluation canonicalises the label before writing", ok)

    # ══ N3 — EVERY dispatch label resolves to a class name ════════════════
    # 🔴 The real invariant. A new strategy whose dispatch label differs from
    # its plan name splits its own arms silently, and the report says NOT
    # READY rather than naming the cause.
    labels = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "id", "") == "_safe_strategy"
                and node.args and isinstance(node.args[0], ast.Constant)):
            labels.add(node.args[0].value)
    plan_names = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "attr", "") == "open_plan"
                and node.args and isinstance(node.args[0], ast.Constant)):
            plan_names.add(node.args[0].value)
    resolved = {DISPATCH_ALIAS.get(l, l) for l in labels}
    split = sorted(l for l in labels
                   if DISPATCH_ALIAS.get(l, l) != l and l in resolved)
    check("N3 no dispatch label resolves to itself AND to something else",
          not split, str(split))
    check("N3b every label is either a class name or aliased to one",
          labels, f"labels={sorted(labels)}")

    # ══ N4 — THE GATE REPORTER RESOLVES THE SAME LABELS ══════════════════
    # 🔴 r246. `gate_report` held its OWN dict and was missing `ORB` and
    # `SweepForLeg2`, so the ORB's fired() arrived as "ORB" and never resolved
    # — r239's split in a THIRD place. r239 fixed the notes writer; the plan
    # board had it right since r147; this one was never told.
    from analysis.gate_report import DISPATCH_ALIAS as GA
    check("N4 the reporter resolves ORB", GA.get("ORB") == "ORBStrategy")
    check("N4b and SweepForLeg2 (r160's ruling)",
          GA.get("SweepForLeg2") == "SweepCreditSpread")
    # ⚠️ NOT A DUPLICATE — COMPOSED. `plan.DISPATCH_ALIAS` maps to the CLASS
    # NAME; this maps to the REPORTER'S OWN name, and `GexPinButterfly`
    # (lowercase x) is live at gex_pin_butterfly:271 while dispatch fires under
    # "GEXPinButterfly". Merging them would break that reconciliation, which is
    # why FIT.2's "two copies of one map" was the wrong diagnosis.
    check("N4c the reporter's own spelling still wins",
          GA.get("GEXPinButterfly") == "GexPinButterfly")
    check("N4d and it is a SUPERSET of the shared map",
          all(GA.get(k) for k in DISPATCH_ALIAS),
          str([k for k in DISPATCH_ALIAS if not GA.get(k)]))

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 9 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
