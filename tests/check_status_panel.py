#!/usr/bin/env python3
"""
tests/check_status_panel.py  v1.1
v1.1  2026-09-01  r212 — C2 AND C7 RE-DERIVED, exactly as chunk C said they
      would be. C2 required the plan collapse to REMAIN, which was right while
      the writer was unfixed; r212 fixed the writer and disproved the premise
      (they were never duplicates), so both the warning and the collapse are
      gone and C2 pins their absence.
v1.0  2026-09-01  r211 (chunk C) — THE MIDDLE OF THE STATUS BOARD.

Operator, 2026-09-01, going through `status.py`: open positions "just list the
number (nothing else)"; the duplicate-plan warning "what do I need this for —
get rid of that"; ORB "on expired, just say that without all the other
qualifiers, it's unimportant, it's just expired"; and "add a line for
Character. I know it's not activated yet, so put 'inactive' until it is."

🔑 THE CHARACTER LINE WAS ALREADY THERE AND HAS NEVER PRINTED. r75 wrote it and
gated it on `current()` returning a character; r85 then set BANDS_SET=False
because the old bands were calibrated against the wrong quantity — a per-bar
volatility RATIO, silent about direction, which scored a trend 1.00 and
ALTERNATING CHOP 1.00 as well. So the engine emits no state and the line has
been invisible on every box since. ABSENT AND INACTIVE ARE DIFFERENT FACTS and
printing nothing said neither.

🔴 AND THE EXPIRED LABEL WAS STALE. It read "past 11:00 ET cutoff"; r193 moved
`ORB_NO_ENTRY_AFTER_ET` to 11:30 on 2026-08-30 and the label kept the old
number. A line nobody reads is a line nobody notices going stale — which is the
argument for deleting it rather than correcting it.

⚠️ C2 IS THE ONE THAT MATTERS MOST. Removing the duplicate-count line does NOT
mean the duplication is gone: r199 printed that count so the ledger defect
stayed visible, and RPT.5 records the WRITE side was never examined. Chunk D
repairs the writer. Until then the collapse must REMAIN, or two identical plans
render as two rows and the panel is wrong in the other direction.

Born red at ff5140b (r210), where C1, C2, C3, C4 and C5 all fail.
"""
from __future__ import annotations

import ast
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

_fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


def main():
    path = os.path.join(_root, "status.py")
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src, "status.py")

    # Only STRING CONSTANTS, never the file's prose. §20: rule 5 requires the
    # changelog to name what it removed, so a text search is guaranteed to
    # match the documentation the version discipline demands. `#` comments are
    # not AST nodes.
    lits = [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    joined = "\n".join(lits)

    # ── C1 — open positions is a COUNT, not a card ───────────────────────
    check("C1 the open-position block is one counted line",
          any("Open positions:" in s for s in lits)
          and not any("Total cost:" in s for s in lits)
          and not any("Trail at:" in s for s in lits),
          "the per-position cards live in query.py, which runs beside this")

    # ── C2 — the warning is gone AND the collapse survives ───────────────
    # 🔴 BOTH HALVES, OR THIS IS A REGRESSION. Deleting the collapse with the
    # warning would render two identical plans as two rows — the very thing
    # r199 added it to stop.
    fn_src = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            fn_src[n.name] = ast.get_source_segment(src, n) or ""
    body = fn_src.get("main", "")
    # 🔴 RE-DERIVED AT r212, AS CHUNK C SAID IT WOULD BE. C2 required the
    # collapse to REMAIN — correct while the writer was unfixed, because
    # removing both halves would have rendered two identical plans as two rows.
    # r212 then showed the premise was wrong: they were never duplicates.
    # `PlanTick.take()` opens a row per FIRE and nothing closed them, so every
    # fired plan stayed live all session; the collapse was merging DISTINCT
    # plans that shared a trigger price. Fixed at the writer, so both the
    # warning and the collapse are gone and this pins their absence.
    check("C2 neither the duplicate warning nor the collapse survives",
          "duplicate plan row" not in joined
          and "_seen" not in body and "_rows.append" not in body,
          "the writer closes plans now; there is nothing to merge")

    # ── C3 — EXPIRED says EXPIRED ────────────────────────────────────────
    # ⚠️ SCOPED TO WHAT REACHES THE TERMINAL AND TO THE LABEL TABLE, not to
    # every literal in the file. The first draft scanned all string constants
    # and matched this revision's OWN CHANGELOG, which names the stale "past
    # 11:00 ET cutoff" while explaining its removal — §20, and rule 5 makes
    # that prose mandatory, so the canary was guaranteed to trip on it.
    printed = []
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "print"):
            printed += [c.value for c in ast.walk(n)
                        if isinstance(c, ast.Constant) and isinstance(c.value, str)]
    labels = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "ORB_STATE_LABELS"
                for t in n.targets):
            labels += [c.value for c in ast.walk(n)
                       if isinstance(c, ast.Constant) and isinstance(c.value, str)]
    check("C3 EXPIRED carries no cutoff qualifier, in either place",
          "EXPIRED" in printed + labels
          and not any("past 11:" in x for x in printed + labels),
          "it was stale in BOTH the live branch and ORB_STATE_LABELS")

    # ── C4 — and the attempt/latch trivia is suppressed there too ────────
    check("C4 attempt and break latches are suppressed on EXPIRED",
          "_quals" in body and "_expired" in body,
          "live states keep them; a finished session does not need them")

    # ── C5 — CHARACTER prints unconditionally, below the pin ─────────────
    check("C5 the character line always prints, defaulting to inactive",
          any(s == "inactive" for s in lits)
          and any("Character:" in s for s in lits),
          "absent and inactive are different facts")

    _pin = body.find("GEX pin:")
    _chr = body.find("Character:")
    check("C5b the character line sits BELOW the pin line",
          _pin != -1 and _chr != -1 and _chr > _pin,
          f"pin at {_pin}, character at {_chr}")

    # ⚠️ AND AN UNREADABLE ENGINE IS NOT AN INACTIVE ONE. Three states, three
    # words — the silent-zero habit this repo has paid for repeatedly.
    check("C5c an engine that raises reads 'unavailable', not 'inactive'",
          any(s == "unavailable" for s in lits))

    # ── C6 — what the operator kept is still here ────────────────────────
    kept = ("TODAY'S SESSION", "GEX pin:", "ORB High:", "Active plan:")
    missing = [k for k in kept if k not in joined]
    check("C6 the session, pin, ORB and active-plan lines survive",
          not missing, f"missing: {missing}")

    # ── C7 — more than one active plan still renders as more than one ────
    check("C7 every active plan is listed, not just the first",
          "for _p in _live:" in body,
          "operator: 'Active plan: keep. If there's more than 1, list them' — "
          "and at r212 it iterates the LIVE rows directly, not a deduped copy")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_status_panel: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
