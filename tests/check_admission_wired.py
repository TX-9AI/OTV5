#!/usr/bin/env python3
"""
tests/check_admission_wired.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.5  2026-10-19  OTV4TEST r303 (PSTATE.1) — A3's ORB trade is DORMANT by default and a dormant plan is never asked by ruling,
      so this run switches it ACTIVE (OT_ORB_TRADE=1). A5 asks a name NEITHER table carries (UnlistedStrategy):
      IronCondorStrategy is now DORMANT (no entry of its own), and admission's no-opinion rule is what A5 pins.
THE ADMISSION TABLE IS LIVE: A STRATEGY OUTSIDE ITS WINDOW IS NEVER ASKED.

v1.4  2026-10-18  OTV4TEST r293 (ADM.2) — A10: an unreadable rules() table fails CLOSED (nothing asked) and WARNS once;
      _admission_allows returned True with no line (audit 10-18 D1).

v1.3  2026-10-03  OTV4TEST r204 (PREM.2) — A1, A2 and A4 PROBE THE GEX BUTTERFLY, NOT THE TCS. The TCS is retired by
      ruling ("Retire the sweep & TCS") and _safe_strategy no longer asks it whatever admission says, so it
      cannot stand in for "an admitted strategy". The assertions are unchanged; only the probe name moved.
v1.2  2026-09-18  OTV4TEST r43 — A9 INVERTED, which is the point of having
      written it. At r40 it pinned the STATED SCOPE (the gate still stands);
      ADM.1 closed, so the assertion flips to "the gate is gone". A scope pin
      that cannot be flipped when the scope changes is just a comment.
v1.1  2026-09-18  OTV4TEST r42 — A8 accepts the one-pass accessor. It named
      `eligible_now` specifically; r42 asks via `logging_state()` and A8 went red
      on code that satisfies its own rule. Re-pointed at the rule, kept closed.
v1.0  2026-09-17  OTV4TEST r40 — born red at r39 (ae63024), where `_safe_strategy`
      had no admission test at all and `attempt_new_entry` never called
      `eligible_now()`.

WHY THIS FILE EXISTS. r35 moved every entry gate into one table and then said so
plainly: *"NOTHING IS WIRED YET — attempt_new_entry still runs the old gates."*
A table nobody reads is not an admission policy, it is documentation. This is the
revision that reads it, and this is the gate that proves it is read.

⚠️ IT DRIVES `_safe_strategy` RATHER THAN MATCHING ITS TEXT. §21: a checker that
greps for `_admission_allows` passes on a call whose result is discarded. Every
assertion below calls the funnel with a probe that RECORDS whether it ran, so
"not asked" means the strategy function was genuinely never invoked.
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["OT_ORB_TRADE"] = "1"   # r303: A3's subject is active (check_plan_states pins dormant)
os.environ.setdefault("OT_TRADES_DB", os.path.join(tempfile.mkdtemp(), "t.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(tempfile.mkdtemp(), "d.db"))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def guard(name, fn, detail=""):
    """A MISSING symbol is a RED LINE, never a traceback (r39's lesson, kept)."""
    try:
        ok, det = fn(), detail
    except Exception as exc:                                    # noqa: BLE001
        ok, det = False, f"{type(exc).__name__}: {exc}"
    check(name, ok, det)
    return ok


def main():
    import ast
    src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()

    # ── A1/A2 — the funnel consults admission, and a refusal never runs fn ──
    import main as M

    def probe(name, admitted):
        """Returns (was_asked, returned). `admitted` None = no admission set."""
        M._set_admission(admitted)
        ran = {"n": 0}

        def fn():
            ran["n"] += 1
            return "SIGNAL"
        out = M._safe_strategy(name, fn)
        M._set_admission(None)
        return ran["n"] > 0, out

    guard("A1 an ADMITTED strategy is asked and its signal returned",
          lambda: probe("GEXPinButterfly", ["GEXPinButterfly"]) == (True, "SIGNAL"))
    guard("A2 a strategy NOT admitted this tick is NEVER ASKED — fn does not run",
          lambda: probe("GEXPinButterfly", ["SweepCreditSpread"]) == (False, None),
          "this is what removes the NOT ASKED rows: no ask, so no refusal to journal")

    # ── A3 — the ORB dispatches under a label the table does not use ────────
    guard("A3 the dispatch label 'ORB' resolves to the table key 'ORBStrategy'",
          lambda: probe("ORB", ["ORBStrategy"])[0] is True
          and probe("ORB", ["SweepCreditSpread"])[0] is False,
          "an alias miss would silently gate the ORB shut in its own window")

    # ── A4/A5 — fails OPEN, in both directions ─────────────────────────────
    guard("A4 with NO admission computed, every strategy is asked (pre-r40 exactly)",
          lambda: probe("GEXPinButterfly", None)[0] is True)
    guard("A5 a name the table does not carry is asked — admission has no opinion",
          lambda: probe("UnlistedStrategy", ["SweepCreditSpread"])[0] is True,     # r303: IronCondorStrategy is DORMANT
          "IronCondorStrategy is retired as an entry; a silent veto would hide that")
    guard("A5b a management dispatch is never gated by the entry table",
          lambda: probe("CondorManagement", [])[0] is True)

    # ── A6 — every strategy the table DOES carry is genuinely gated ────────
    from execution import position_manager as pm
    names = list(pm.rules())

    def all_gated():
        return all(probe(n, [])[0] is False for n in names)
    guard("A6 EVERY strategy in the table is gated — none is decorative",
          all_gated, f"{len(names)} strategies: {', '.join(names)}")

    # ── A7 — the set is CLEARED at entry, before any early return ──────────
    # ⚠️ THE ORDER IS THE ASSERTION. `_ADMITTED` is module state that outlives
    # the call; a `return` that left last tick's set live would gate this tick
    # on a window that has since closed — r207's stale-snapshot class.
    tree = ast.parse(src)
    fn_ane = next((n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "attempt_new_entry"), None)

    def cleared_first():
        first = fn_ane.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            first = fn_ane.body[1]          # skip the docstring
        return (isinstance(first, ast.Expr) and isinstance(first.value, ast.Call)
                and getattr(first.value.func, "id", "") == "_set_admission"
                and len(first.value.args) == 1
                and isinstance(first.value.args[0], ast.Constant)
                and first.value.args[0].value is None)
    guard("A7 attempt_new_entry CLEARS admission as its first statement",
          cleared_first, "before any gate can return past it")

    # ── A8 — and it actually calls the position manager ────────────────────
    # ⚠️ r42 — A CLOSED SET OF ACCESSORS, NOT ONE METHOD NAME. What A8 exists
    # to prove is that `attempt_new_entry` ASKS THE POSITION MANAGER rather than
    # deciding for itself. r42 moved that call from `eligible_now()` to
    # `logging_state()` — which returns the binary AND the refusing gate in one
    # walk — and A8 went red on code that satisfies it exactly. Pinning the
    # spelling of a correct call is the same fault as pinning a reason string
    # (r41's C7) or a character offset (r39's T6): the rule is unchanged, so
    # the assertion moves to the rule. It stays CLOSED — an unknown accessor,
    # or none, still fails.
    ASKS = {"logging_state", "eligible_now"}

    def calls_eligible():
        return any(isinstance(n, ast.Call) and getattr(n.func, "attr", "") in ASKS
                   for n in ast.walk(fn_ane))
    guard("A8 attempt_new_entry asks the position manager which strategies may be asked",
          calls_eligible, "r35's table is READ, not merely present")

    # ── A9 — the old gate is still standing, and that is deliberate ────────
    # r40 did NOT remove `has_blocking_position()`. This asserts the STATED
    # scope so the next revision can see exactly what it inherits, and so the
    # claim in the changelog cannot drift from the code.
    # 🔴 r43 — A9 IS INVERTED, AND THAT IS THE POINT OF HAVING WRITTEN IT.
    # At r40 it pinned the STATED SCOPE: `has_blocking_position()` still gates
    # the open branch, because removing it needed the three direct calls
    # de-duplicated first. ADM.1 did that de-duplication, so the scope moved and
    # the assertion moves with it — from "the gate is still there" to "the gate
    # is gone". A scope pin that could not be flipped when the scope changed
    # would just be a comment.
    def gate_gone():
        return "if not pos_mgr.has_blocking_position():" not in src
    guard("A9 has_blocking_position() NO LONGER gates the open branch — ADM.1 closed",
          gate_gone, "the last of r35's seven admission mechanisms")

    # r293 (ADM.2) — an UNREADABLE table fails CLOSED and says so once. It returned True with no line.
    def a10():
        import logging as _lg
        from execution import position_manager as _pm
        lines = []

        class _H(_lg.Handler):
            def emit(self, r):
                lines.append((r.levelname, r.getMessage()))
        h = _H(); log = _lg.getLogger("main"); log.addHandler(h); log.setLevel(_lg.INFO)
        _orig = _pm.rules

        def _boom():
            raise RuntimeError("rules table unreadable (fixture)")
        _pm.rules = _boom
        try:
            M._set_admission({"Breakout"})
            r1 = M._admission_allows("Breakout")
            r2 = M._admission_allows("Breakout")
        finally:
            _pm.rules = _orig
            M._set_admission(None)
            log.removeHandler(h)
        warns = [m for lv, m in lines if lv == "WARNING" and "UNREADABLE" in m]
        print(f"        a10: allows={r1},{r2} warnings={len(warns)}")
        return r1 is False and r2 is False and len(warns) == 1      # guard() wants a bool here
    guard("A10 rules() raising: the strategy is NOT asked (fails closed) and one WARNING names it", a10,
          "it returned True with no line when the table could not be read")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
