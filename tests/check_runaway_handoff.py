#!/usr/bin/env python3
"""check_runaway_handoff.py  v1.2
v1.2  2026-09-08  OTV4TEST r3 — RW9/RW13 read strategy/runaway_plan.py, where the
      direction block and the 50% read now live (one site per module).
v1.1  2026-08-27  r165: runs the real prepare() instead of exec-ing a source slice. — v1.0

🔴 AN ORB INVALIDATED *BY RUNAWAY* IS RunawayContinuation'S TRIGGER, NOT A
DISQUALIFIER.

Measured live, NFLX 2026-08-27: price broke the ORB low 80.08 at 09:41 and ran
to the 50% TP at 79.52 with no retest — the textbook runaway. `orb_engine`
classified it exactly right (`state = INVALIDATED`, `invalidation_reason =
"runaway"`, `break_direction = "short"`). The strategy named after that setup
refused it with *"ORB state 'INVALIDATED' carries no direction."*

⚠️ THE CAUSE: direction was read by string-matching "LONG"/"SHORT" inside
`orb.state`. "INVALIDATED" contains neither, so the function returned at step 3
of its own checklist and never reached step 4, where `runaway_confirmed()`
would have confirmed the setup. The engine had already recorded the direction
in `break_direction` — a field the strategy never read.

⚠️ SAME CLASS AS `all()` vs `all_rails()` AND `oi` vs `open_interest`: reading a
plausible attribute instead of the one carrying the information. It costs more
here because it silently disables an entire strategy on exactly its own setup.

⚠️ `close_inside` MUST STILL REFUSE. That is the opposite tape — price came
back into the range — and is not a handoff.
"""
import ast
import os
import sys
import textwrap

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


class _Refuse(Exception):
    pass


class _ORB:
    def __init__(self, state, reason="", brk=""):
        self.state = state
        self.invalidation_reason = reason
        self.break_direction = brk


def _direction_for(orb):
    """Run the strategy's REAL direction logic against an ORB shape.

    r165: the direction block now lives inside `prepare()` (the plan), so the
    plan itself is run with an in-memory store and the resolved direction is
    read off the preparation — still the real code, never a copy.
    """
    import sqlite3
    from strategy import plan as P
    from strategy.runaway_continuation import RunawayContinuationStrategy

    class _S:
        def __init__(self): self.conn = sqlite3.connect(":memory:")
        def commit(self): self.conn.commit()
    P.bind_store(_S())
    P.begin_tick(1.0)
    orb.orb_high, orb.orb_low, orb.target_50pct = 101.0, 100.0, 101.5
    prep = RunawayContinuationStrategy().prepare(
        orb=orb, atr_pct=0.14, price_now=101.9, prev_close=101.6, now_et="10:15",
        chain=None)
    if not prep.direction:
        raise _Refuse("no direction")
    return prep.direction, prep.side


def main():
    # ── the retest states still work ─────────────────────────────────────
    try:
        check("RW1 OPEN_SHORT gives short/put",
              _direction_for(_ORB("OPEN_SHORT")) == ("short", "put"))
        check("RW2 OPEN_LONG gives long/call",
              _direction_for(_ORB("OPEN_LONG")) == ("long", "call"))
    except _Refuse:
        check("RW1/RW2 the retest states still resolve", False, "refused")

    # ── 🔴 THE HANDOFF — the case that was broken ────────────────────────
    try:
        got = _direction_for(_ORB("INVALIDATED", "runaway", "short"))
        check("RW3 INVALIDATED by runaway (short) resolves — the NFLX case",
              got == ("short", "put"), str(got))
    except _Refuse:
        check("RW3 INVALIDATED by runaway (short) resolves — the NFLX case",
              False, "REFUSED — the strategy is still blind to its own setup")

    try:
        got = _direction_for(_ORB("INVALIDATED", "runaway", "long"))
        check("RW4 INVALIDATED by runaway (long) resolves",
              got == ("long", "call"), str(got))
    except _Refuse:
        check("RW4 INVALIDATED by runaway (long) resolves", False, "REFUSED")

    # ── and the cases that must KEEP refusing ────────────────────────────
    # ⚠️ close_inside is price returning INTO the range — the opposite tape.
    for state, reason, brk, label in (
            ("INVALIDATED", "close_inside", "short",
             "RW5 INVALIDATED by close_inside still refuses"),
            ("INVALIDATED", "runaway", "",
             "RW6 runaway with NO break_direction refuses, never guesses"),
            ("EXPIRED", "", "", "RW7 EXPIRED refuses"),
            ("AWAITING_RETEST", "", "", "RW8 AWAITING_RETEST refuses")):
        try:
            got = _direction_for(_ORB(state, reason, brk))
            check(label, False, f"resolved to {got} — should have refused")
        except _Refuse:
            check(label, True)

    # ⚠️ THE REFUSAL MUST NAME THE REASON. "carries no direction" alone sent
    # the operator hunting; the invalidation reason is what distinguishes a
    # handoff from a disarm.
    src = open(os.path.join(_root, "strategy", "runaway_plan.py"),
               encoding="utf-8").read()
    check("RW9 the refusal message names the invalidation reason (the plan's)",
          "invalidated: {inval}" in src)

    # ── 🔴 RW10-RW12 — THE 50% TP FIELD, THE SECOND HALF OF THE SAME BUG ──
    # r148 unblocked the direction lookup; the very next gate refused all eight
    # boxes anyway because `tp50`/`underlying_tp50` DO NOT EXIST on the ORB
    # dataclass — the field is `target_50pct` (orb_engine.py:311, set 1043/1064).
    # The plan row read "no 1m close beyond the 50% TP n/a" and the `n/a` was
    # the tell: the level was never READ, not never crossed.
    from strategy.runaway_continuation import runaway_confirmed

    class _O:
        def __init__(self, tp):
            self.target_50pct = tp

    # NFLX 2026-08-27: broke the ORB low 80.06, width 1.09 -> tp50 79.515
    check("RW10 a short runaway past the 50% TP confirms",
          runaway_confirmed(_O(79.515), 79.32, 79.40, "short") is True)
    check("RW11 price short of the TP does NOT confirm",
          runaway_confirmed(_O(79.515), 79.55, 79.60, "short") is False)
    # ⚠️ FAIL CLOSED when the field is absent — never assume a level.
    class _Bare:
        pass
    check("RW12 an ORB with no TP field refuses, never guesses",
          runaway_confirmed(_Bare(), 79.32, 79.40, "short") is False)

    src2 = (open(os.path.join(_root, "strategy", "runaway_continuation.py"), encoding="utf-8").read()
            + open(os.path.join(_root, "strategy", "runaway_plan.py"), encoding="utf-8").read())
    _n_sites = src2.count('getattr(orb, "target_50pct"')   # OTV4TEST r3: one per module
    check("RW13 the strategy reads target_50pct at BOTH sites",
          _n_sites == 2, f"{_n_sites} sites (want 2)")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_runaway_handoff: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
