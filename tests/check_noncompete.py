#!/usr/bin/env python3
"""
tests/check_noncompete.py  v1.1
EVERY ADMITTED STRATEGY FIRES ON ITS OWN. NOTHING CLAIMS A SLOT.

v1.1  2026-09-18  OTV4TEST r49 — N8: a fire must not end the tick. N1 tests the
      cascade's SHAPE (a dispatch under a test of `signal`) and cannot see an
      unconditional `return` after a fire, which ends the tick just as
      completely. r43 removed that return from the TCS block and left the
      sweep's; the operator found the survivor by reading the plan board.
v1.0  2026-09-18  OTV4TEST r43 (ADM.1) — born red at r42 (b07f356), where
      `attempt_new_entry` ran a winner-take-all cascade and `main_loop` gated
      entry behind `has_blocking_position()`.

THE OPERATOR'S RULING, 2026-09-18: *"I want the orb, hunt, breakout & sweep all
able to fire & non-competing. We only have one session at a time so we need to
maximize every opportunity on these setups. In live trading, we will revert back
to hierarchy-based."*

⚠️ THE POSTURE IS TEST-BOX-ONLY. Non-compete exists to harvest the maximum
number of comparable setups from ONE session; the fleet reverts to hierarchy,
and because the admission table overlays from `config.ADMISSION_RULES` that
reversion is a CONFIG CHANGE and not a revision.

🔑 N1 IS THE ONE THAT MATTERS AND IT IS STRUCTURAL, NOT TEXTUAL. The competition
was never a named gate — it was the SHAPE of the code: one `signal` variable and
five `if signal is None` guards, so the first strategy to fire consumed the tick
and the rest were never asked. Live evidence, 2026-09-18 10:06:32: the plan board
read "slot claimed by RunawayContinuation" for TrendCreditSpread, GEXPinButterfly
and ATPButterfly — three strategies crowded out rather than refused on merit.
N1 walks the AST and fails if ANY strategy dispatch sits under a test of
`signal`, which is the rule itself rather than a spelling of it.
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def guard(name, fn, detail=""):
    """Run a predicate; a MISSING symbol is a RED LINE, never a traceback.

    ⚠️ `detail` MAY BE A CALLABLE, AND OFTEN MUST BE. A plain string argument is
    evaluated BEFORE `fn()` runs, so any detail computed from state the predicate
    sets is stale — r49's N8 printed "no fire-then-return" on a FAILING check,
    which is the diagnostic saying the opposite of the truth. Pass a lambda to
    have it rendered AFTER the predicate.
    """
    try:
        ok = fn()
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"{type(exc).__name__}: {exc}")
        return False
    try:
        det = detail() if callable(detail) else detail
    except Exception:                                           # noqa: BLE001
        det = ""
    check(name, ok, det)
    return ok


def main():
    src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "attempt_new_entry"), None)
    if fn is None:
        check("N0 attempt_new_entry exists", False)
        print("\nRED — attempt_new_entry not found")
        return 1

    # ── parent map, so a dispatch can be asked what it sits under ──────────
    parent = {}
    for node in ast.walk(fn):
        for kid in ast.iter_child_nodes(node):
            parent[kid] = node

    def ancestors(n):
        while n in parent:
            n = parent[n]
            yield n

    def mentions_signal(test) -> bool:
        return any(isinstance(x, ast.Name) and x.id == "signal" for x in ast.walk(test))

    dispatches = [n for n in ast.walk(fn)
                  if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_safe_strategy"]

    def no_slot_guard():
        bad = []
        for d in dispatches:
            for a in ancestors(d):
                if isinstance(a, ast.If) and mentions_signal(a.test):
                    nm = d.args[0].value if d.args and isinstance(d.args[0], ast.Constant) else "?"
                    bad.append(f"{nm}@L{d.lineno}")
                    break
        no_slot_guard.bad = bad
        return not bad

    guard("N1 NO strategy dispatch sits under a test of `signal` — the cascade is gone",
          no_slot_guard,
          lambda: ", ".join(getattr(no_slot_guard, "bad", []))
          or f"{len(dispatches)} dispatches, none gated")

    # ⚠️ FOUR, NOT FIVE: the butterflies dispatch through `_attempt_butterfly`,
    # which is a SEPARATE function and therefore not inside `attempt_new_entry`'s
    # own tree. N1b exists only so N1 cannot pass by finding nothing.
    guard("N1b there ARE dispatches to check — N1 cannot pass vacuously",
          lambda: len(dispatches) >= 4, f"{len(dispatches)} _safe_strategy call(s)")

    # ── N2/N3 — the per-signal executor ────────────────────────────────────
    fire = next((n for n in ast.walk(fn)
                 if isinstance(n, ast.FunctionDef) and n.name == "_fire"), None)
    guard("N2 a per-signal executor `_fire()` exists", lambda: fire is not None)

    def fire_has_afd():
        return any(isinstance(n, ast.Call)
                   and getattr(n.func, "id", "") == "_afternoon_debit_blocked"
                   for n in ast.walk(fire))
    guard("N3 the afternoon-debit gate is applied PER SIGNAL, inside _fire",
          fire_has_afd,
          "a tail gate would catch only the last signal once there is no winner")

    def fire_is_additive():
        for n in ast.walk(fire):
            if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_execute_entry_signal":
                for kw in n.keywords:
                    if kw.arg == "additive" and getattr(kw.value, "value", None) is True:
                        return True
        return False
    guard("N4 _fire executes ADDITIVE — a second fire must append, never replace",
          fire_is_additive,
          "set_open_position would drop the first position from management")

    # ── N5 — the tick loop no longer gates entry ───────────────────────────
    guard("N5 has_blocking_position() no longer gates attempt_new_entry",
          lambda: "if not pos_mgr.has_blocking_position():" not in src,
          "the last of r35's seven admission mechanisms")

    # ── N6 — one dispatcher, called once ───────────────────────────────────
    # ⚠️ THE FIRST CUT OF N6 DEMANDED ONE CALL SITE FOR `attempt_new_entry` TOO,
    # AND THAT WAS WRONG ABOUT THE CODE. It legitimately has three: the
    # outside-RTH rehearsal (r102), the position-open branch, and the flat
    # branch. The rule is not "called once" — it is (a) the two helpers are not
    # asked TWICE a tick, which is the double-ask r40 named, and (b) entry is
    # reachable from BOTH branches of the manage/enter split, which is what
    # closing ADM.1 actually means.
    counts = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            nm = getattr(n.func, "id", "")
            if nm in ("_attempt_hunt", "_attempt_sweep_on_grant", "attempt_new_entry"):
                counts.setdefault(nm, []).append(n.lineno)

    guard("N6 hunt and sweep-on-grant are dispatched ONCE — no double-ask",
          lambda: len(counts.get("_attempt_hunt", [])) == 1
          and len(counts.get("_attempt_sweep_on_grant", [])) == 1,
          f"hunt={counts.get('_attempt_hunt')} grant={counts.get('_attempt_sweep_on_grant')}")

    def both_branches():
        loop = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                     and n.name == "main_loop"), None)
        if loop is None:
            return False
        for node in ast.walk(loop):
            if not isinstance(node, ast.If) or not node.orelse:
                continue
            def calls_entry(body):
                return any(isinstance(c, ast.Call) and getattr(c.func, "id", "") == "attempt_new_entry"
                           for stmt in body for c in ast.walk(stmt))
            if calls_entry(node.body) and calls_entry(node.orelse):
                return True
        return False
    guard("N6b entry is reached from BOTH branches of the manage/enter split",
          both_branches, "with a position open AND flat — ADM.1's whole point")

    # ── N7 — the orphan is gone AND its guard survived the removal ─────────
    # ── N7 — ONE butterfly path, not two ───────────────────────────────────
    # 🔴 THIS ASSERTION WAS BACKWARDS IN ITS FIRST CUT, AND THE CHECKERS SAID SO.
    # I deleted `_attempt_butterfly` and inlined it, and `check_atp_butterfly`
    # — which drives that function DIRECTLY to prove the one-per-session cap —
    # crashed with "module 'main' has no attribute '_attempt_butterfly'".
    # Inlining destroyed a TESTABLE SEAM: a behaviour reachable only through a
    # 700-line dispatch is a behaviour that stops being tested. The right
    # survivor was the function, not the inline copy. The RULE was always "one
    # path"; only my choice of which one was wrong.
    bfly = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                 and n.name == "_attempt_butterfly"), None)

    def inline_copy_gone():
        return not any(isinstance(n, ast.Call)
                       and getattr(getattr(n.func, "value", None), "id", "") == "_gex_bfly_strategy"
                       for n in ast.walk(fn))
    guard("N7 exactly ONE butterfly path — the helper, with no inline copy beside it",
          lambda: bfly is not None and inline_copy_gone(),
          "two paths for one behaviour is how they drift")

    guard("N7b 🔴 r178's mark_pin_played is ON that path",
          lambda: bfly is not None and any(
              isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "mark_pin_played"
              for n in ast.walk(bfly)),
          "the guard against the 2026-08-28 five-in-ninety-seconds stack")

    # ══ N8 — A FIRE MUST NOT END THE TICK ═════════════════════════════════
    # 🔴 r43 MISSED ONE AND THIS IS WHY N8 EXISTS. N1 tests for dispatches
    # sitting under a test of `signal` — the cascade's *shape*. It cannot see an
    # UNCONDITIONAL `return` placed immediately after a fire, which ends the
    # tick just as completely. r43 removed that return from the TCS block and
    # left the identical one in the sweep block, so a sweep fill still silenced
    # every strategy below it. MEASURED LIVE 2026-09-18: the sweep filled at
    # 12:34 and `IronCondorStrategy` sat on the dispatch-gap default for the
    # next 204 minutes, 140 lines below the return. The operator found it by
    # READING THE BOARD — *"I want the messaging to look intentional and not
    # like an error"* — which is the plan board catching a dispatch defect that
    # a structural checker could not.
    def no_fire_then_return():
        bad = []
        FIRES = {"_execute_condor_leg", "_execute_entry_signal"}
        for node in ast.walk(fn):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            for a, b in zip(body, body[1:]):
                fired = (isinstance(a, ast.Expr) and isinstance(a.value, ast.Call)
                         and getattr(a.value.func, "id", "") in FIRES)
                if fired and isinstance(b, ast.Return):
                    bad.append(f"{getattr(a.value.func,'id','?')}@L{a.lineno}")
        no_fire_then_return.bad = bad
        return not bad
    guard("N8 no fire is followed by a `return` — a fill must not end the tick",
          no_fire_then_return,
          lambda: ", ".join(getattr(no_fire_then_return, "bad", [])) or "no fire-then-return")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
