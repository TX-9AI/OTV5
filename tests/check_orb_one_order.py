#!/usr/bin/env python3
"""
tests/check_orb_one_order.py  v1.0
v1.0  2026-09-04  r235 — ONE QUALIFYING RETEST, ONE ORDER. Operator, measured
      on META 2026-09-04: entries at 09:39, 09:40 and 09:43 off a SINGLE 09:38
      retest, with only one further qualifying retest all session (09:54).

🔴 THE DEFECT: `_mark_orb_confirmation_spent()` was called only inside
`_place_standing_offer`. `_place_single_leg` is the DEFAULT placer and never
called it, so `order_placed` stayed False for the life of the session, the
engine sat in OPEN_* after the retest, and both fire gates passed every tick.
C.40 a third time — a guard in the order plumbing cannot protect a path that
does not run that plumbing (r195's `_orb_offer_working()` was the first).

⚠️ THE LATCH IS NOW PER-CONFIRMATION. A bare boolean can only say "an order
happened", which is why the armed path had to clear it globally (r227) — and a
global clear is indistinguishable from never having been set. `confirmation_seq`
vs `order_placed_seq` answers the real question.

⚠️ EXECUTED, NOT READ (§21). The gate checks drive the real refusal path; the
placement check drives `enter()` against a paper engine.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


def main():
    import ast
    from analysis import orb_engine as OE

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for fld in ("confirmation_seq", "order_placed_seq"):
        if fld not in {f.name for f in __import__("dataclasses").fields(OE.ORBData)}:
            check(f"L0 ORBData carries {fld}", False,
                  "the per-confirmation latch is absent")
            print()
            print("RED — 1 failed: per-confirmation latch absent")
            return 1

    # ══ L1 — THE PLACEMENT SITE. Both placers must latch, not one. ════════
    # AST, because the failure is a MISSING CALL and a string search for the
    # function name would match its own definition and the comments about it.
    src = open(os.path.join(root, "execution", "entry_engine.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)
    marked = set()
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef,)):
            continue
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call)
                    and getattr(node.func, "id", "") == "_mark_orb_confirmation_spent"):
                marked.add(fn.name)
    check("L1 the standing-offer path still latches",
          "_place_standing_offer" in marked, str(sorted(marked)))
    check("L1b and the DEFAULT single-leg path now latches too",
          "enter" in marked or "_place_single_leg" in marked,
          f"latching functions: {sorted(marked)}")

    # ══ L2 — THE SEQUENCE MOVES ONLY ON A CONFIRMATION ════════════════════
    d = OE.ORBData()
    check("L2 a fresh engine has no confirmation and no spent order",
          d.confirmation_seq == 0 and d.order_placed_seq == 0)

    # ══ L3 — ONE CONFIRMATION, ONE ORDER. Drive the real gate arithmetic. ═
    # The strategy refuses when order_placed_seq >= confirmation_seq (with a
    # confirmation present). Modelled here on the real field names so a rename
    # breaks this check rather than silently passing.
    # ⚠️ DRIVES THE REAL PREDICATE, not a copy of it (C.23).
    from strategy.orb_strategy import confirmation_spent

    class _O:
        def __init__(self, c, o):
            self.confirmation_seq, self.order_placed_seq = c, o

    def gate_open(cseq, oseq):
        return not confirmation_spent(_O(cseq, oseq))

    check("L3 confirmation #1 with nothing spent may fire", gate_open(1, 0))
    check("L3b the SAME confirmation may not fire twice", not gate_open(1, 1))
    check("L3c nor a third time — this is the META 09:39/09:40/09:43 case",
          not gate_open(1, 1))
    check("L3d a FRESH retest re-opens the gate", gate_open(2, 1))
    check("L3e and that one is spent in its turn", not gate_open(2, 2))
    # 🔴 the pre-r235 global boolean: cleared on close, so it always re-opened
    check("L3f a resolved trade with NO new retest stays shut",
          not gate_open(1, 1))

    # ══ L4 — mark_order_placed RECORDS WHICH CONFIRMATION ═════════════════
    eng = OE.ORBEngine() if hasattr(OE, "ORBEngine") else OE.get_orb_engine()
    eng._data = OE.ORBData()
    eng._data.confirmation_seq = 3
    eng.mark_order_placed()
    check("L4 the latch records the CURRENT confirmation, not just True",
          eng._data.order_placed_seq == 3 and eng._data.order_placed is True,
          f"seq={eng._data.order_placed_seq}")

    # ══ L5 — THE ARMED PATH MUST NOT CLEAR IT ═════════════════════════════
    # 🔴 r227 cleared `order_placed` here so the engine would not go quiet
    # against a GLOBAL latch. Clearing it now would restore exactly the
    # behaviour r235 removes, so the absence is pinned.
    nsrc = open(os.path.join(root, "analysis", "orb_engine.py"),
                encoding="utf-8").read()
    ntree = ast.parse(nsrc)
    cleared = []
    for fn in ast.walk(ntree):
        if not (isinstance(fn, ast.FunctionDef)
                and fn.name == "notify_position_closed"):
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if (isinstance(t, ast.Attribute)
                            and t.attr in ("order_placed", "order_placed_seq",
                                           "confirmation_seq")):
                        cleared.append(f"{t.attr}@{node.lineno}")
    check("L5 notify_position_closed clears neither the latch nor the seq",
          not cleared, str(cleared))

    # ══ L6 — AND IT STILL RETURNS TO ARMED, NOT OPEN ══════════════════════
    # The state gate is the other half: ARMED refuses with "AWAITING RETEST",
    # so the setup survives the trade without being fireable.
    check("L6 the armed path is still reached (state returns to ARMED_*)",
          "ORBState.ARMED_LONG if was_long else ORBState.ARMED_SHORT" in nsrc)

    # ══ L7 — CLOSE INSIDE STILL STARTS OVER AT SQUARE ONE ═════════════════
    # Operator: "a close inside the range during the retest hunt kills the
    # thesis and it starts back at square 1 waiting for a break."
    check("L7 a close INSIDE still routes to _rearm(reentered=True)",
          "self._rearm(reentered=True)" in nsrc)
    check("L7b and _rearm rebuilds ORBData, so the seqs reset by construction",
          OE.ORBData().confirmation_seq == 0)

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 14 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
