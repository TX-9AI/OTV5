#!/usr/bin/env python3
"""
tests/check_orb_bounds_capability.py  v5.1
v5.1  2026-11-08  OTV5 r76 (RETIRE.1) — B3 RE-POINTED (WA 38.4): the ORB trade and its r235 confirmation latch are removed, so B3 pins that nothing in
      entry_engine keys on is_orb any more; B1/B2/B4 (the capability check that writes the bounds) unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-09-04  r240 — THE ORB BOUNDS ARE WRITTEN BY CAPABILITY, NOT BY NAME.
      Rebuilds r226, which was cut on 2026-09-03 and NEVER LANDED: no commit
      for it exists on any branch, and its BACKLOG entry reached git only
      because `docs/BACKLOG.md` ships in every archive and r227 — the urgent
      "did you brick my ORB" fix — carried it along.

🔴 `entry_engine` wrote `orb_range_high/low` only `if signal.is_orb`, which is
literally `strategy_name == "ORBStrategy"`. The RUNAWAY populates those fields
(`runaway_continuation:581`) because it is a continuation of the same break,
and the name check discarded them on every runaway fill.

🔴 MEASURED: `calibrate_trend_strength` reported "no ORB boundary on the row :
182" — ALL 182 runaway trades unmeasurable, on the largest strategy in the book
by both count and net. It blocks MOM.1 Stage 1, which r225 filed as the stage
every other stage anchors on.

⚠️ A NAME CHECK IS A LIST, and r35's allow-list rot is what happens to lists.
The next strategy that computes an ORB boundary is covered by HAVING one.
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


class Sig:
    """A signal that carries ORB geometry but is NOT an ORBStrategy signal —
    which is exactly the runaway's shape."""
    strategy_name = "RunawayContinuation"
    orb_range_high = 227.43
    orb_range_low = 226.10

    @property
    def is_orb(self):
        return self.strategy_name == "ORBStrategy"


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(root, "execution", "entry_engine.py"),
               encoding="utf-8").read()

    # ══ B1 — THE RUNAWAY'S SIGNAL FAILS THE OLD TEST AND PASSES THE NEW ═══
    s = Sig()
    check("B1 the runaway signal is NOT is_orb", s.is_orb is False)
    check("B1b but it DOES carry both bounds — the capability is there",
          bool(s.orb_range_high) and bool(s.orb_range_low))

    # ══ B2 — THE WRITE IS GUARDED BY THE FIELDS, NOT THE NAME ═════════════
    # ⚠️ AST on the enclosing `if`, not a grep: the changelog above names
    # `signal.is_orb` while explaining its removal, and a string search would
    # match the explanation (§20). `is_orb` also legitimately survives
    # elsewhere in this file, on the r235 ORB latch, which must NOT trip this.
    tree = ast.parse(src)
    guard_ok = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        writes = [n for n in ast.walk(node)
                  if isinstance(n, ast.Subscript)
                  and isinstance(n.slice, ast.Constant)
                  and n.slice.value in ("orb_range_high", "orb_range_low")]
        if not writes:
            continue
        test = ast.unparse(node.test)
        if "is_orb" in test:
            check("B2 the orb-bounds write is not guarded by is_orb", False, test)
            break
        guard_ok = True
    else:
        check("B2 the orb-bounds write is not guarded by is_orb", guard_ok,
              "no guarded write found" if not guard_ok else "")

    # ══ B3 — AND THE r235 LATCH STILL KEYS ON is_orb, DELIBERATELY ════════
    # 🔴 That one IS an identity question — only the ORB engine has a
    # confirmation to spend — so removing `is_orb` wholesale would have broken
    # the fix that stopped one retest firing three orders.
    latch = [n for n in ast.walk(tree)
             if isinstance(n, ast.If) and "is_orb" in ast.unparse(n.test)]
    _named = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)} | \
        {getattr(n.func, "attr", getattr(n.func, "id", "")) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    check("B3 r76: the r235 latch is removed with the ORB trade - nothing in entry_engine keys on is_orb",
          not latch and "_mark_orb_confirmation_spent" not in _named)

    # ══ B4 — BOTH BOUNDS REQUIRED, NEVER ONE ══════════════════════════════
    # ⚠️ A single bound is not geometry. Writing one and leaving the other
    # null would let the structure stop compute against a missing side, which
    # is the silent-skip this revision exists to end.
    check("B4 the guard requires BOTH bounds",
          "_orb_hi and _orb_lo" in src or "_orb_lo and _orb_hi" in src)

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 5 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
