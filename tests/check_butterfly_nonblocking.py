#!/usr/bin/env python3
"""tests/check_butterfly_nonblocking.py  v1.1
A BUTTERFLY BLOCKS NOTHING. AN ORB OR RUNAWAY DEBIT STILL BLOCKS CREDIT.

v1.1  2026-09-18  OTV4TEST r43 — B5b's RULE IS UNCHANGED; ITS MECHANISM IS
      GONE. It proved a butterfly-only box reached entry by asserting the gate
      that let it through. ADM.1 removed the gate, so EVERY box is asked — the
      rule holds more strongly than when it was written, and the old assertion
      would have failed on code that satisfies it completely.
v1.0  2026-08-31  r197 — born red at r196 (`has_blocking_position` does not
      exist there, and an open butterfly makes the box refuse every entry).

🔴 THIS IS THE RECIPROCAL HALF OF r161, WHICH WAS ONLY EVER BUILT ONE WAY.
r161 exempted the butterfly from the single-position rule ON ENTRY — operator,
2026-08-27: *"I want it to be able to fire regardless if any other open trades
are found"*, TRADES.md §3: *"no position slot, no capital, no competition."*
But `has_open_position()` still counted it, so the butterfly took no slot going
IN and occupied one once it was THERE.

⚠️ MEASURED, 2026-08-31, the first live-fleet session: MU, NFLX and TSLA each
held a 09:45 butterfly and each sat in the second-leg-only branch when the
credit windows opened at 11:30 — `CondorManagement=HOLD(no credit verticals
open)` on all three, so nothing credit-side justified it. One rare
opportunistic trade removed three boxes from the credit side for the day.

🔑 B3 IS THE ONE THAT KEEPS THE FIX HONEST. Operator, correcting me: *"Credit
trades are blocked while a directional debit trade is open (butterfly exempt).
No credit trades while the orb or runaway debit are still open."* So this is
NOT "one open position no longer blocks" — it is "a butterfly, specifically,
does not count." A test that only proved the butterfly case would pass just as
happily against a version that had unblocked everything.

⚠️ B4 GUARDS THE COLLISION THE FIX MAKES REACHABLE. `set_open_position`
REPLACES `_open_records`. Before r197 an entry could never land on a box that
already held a butterfly, so the wipe was unreachable; now it is, and dropping
a butterfly from management leaves it with no trail and no stop.

Run:  python3 tests/check_butterfly_nonblocking.py
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")

_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def rec(tid, strategy, butterfly=0):
    return {"trade_id": tid, "strategy": strategy, "is_butterfly": butterfly,
            "status": "open", "option_side": "call", "contracts": 1}


def main():
    from execution.position_manager import PositionManager

    if not hasattr(PositionManager, "has_blocking_position"):
        check("B0 PositionManager exposes has_blocking_position()", False,
              "a butterfly still blocks every entry on the box")
        print("\nFAILED 1: B0 — nothing below can execute")
        return 1

    pm = PositionManager(paper_trading=True)

    # ⚠️ STUB THE DB HYDRATION. `has_open_position()` reloads open trades from
    # trades.db on an empty cache — correct in production, and it means a
    # sandbox holding yesterday's rows would make every case here read as
    # "something is open". The logic under test is the CLASSIFICATION of
    # records, so the records must come from this file and nowhere else.
    class _NoTrades:
        @staticmethod
        def get_open_trades():
            return []
    pm._trade_logger = _NoTrades()

    # ── B1: nothing open ──────────────────────────────────────────────────
    pm._open_records = []
    check("B1 an empty box blocks nothing",
          not pm.has_blocking_position() and not pm.has_open_position())

    # ── B2: a butterfly alone ─────────────────────────────────────────────
    pm._open_records = [rec("bf1", "GEXPinButterfly", butterfly=1)]
    check("B2 a butterfly alone is OPEN but does NOT block",
          pm.has_open_position() and not pm.has_blocking_position(),
          "open=%s blocking=%s" % (pm.has_open_position(),
                                   pm.has_blocking_position()))

    # ── B3: the block that must SURVIVE ───────────────────────────────────
    # 🔑 Operator: no credit trades while the ORB or runaway debit are open.
    for name in ("ORBStrategy", "RunawayContinuation", "SweepCreditSpread",
                 "TrendCreditSpread", "IronCondorStrategy"):
        pm._open_records = [rec("x", name)]
        if not pm.has_blocking_position():
            check(f"B3 {name} still blocks", False,
                  "only the butterfly is exempt — this unblocked everything")
            break
    else:
        check("B3 ORB, runaway and every credit strategy STILL block", True)

    # ── B3b: a butterfly alongside a blocker does not rescue the box ──────
    pm._open_records = [rec("bf1", "GEXPinButterfly", butterfly=1),
                        rec("orb1", "ORBStrategy")]
    check("B3b butterfly + ORB still blocks — the exemption is per-record",
          pm.has_blocking_position())

    # ── B4: entering alongside a butterfly must not drop it ───────────────
    pm._open_records = [rec("bf1", "GEXPinButterfly", butterfly=1)]
    pm.add_open_position(rec("orb1", "ORBStrategy"))
    ids = {r["trade_id"] for r in pm.get_open_records()}
    check("B4 add_open_position keeps the butterfly under management",
          ids == {"bf1", "orb1"}, str(sorted(ids)))

    pm._open_records = [rec("bf1", "GEXPinButterfly", butterfly=1)]
    pm.set_open_position(rec("orb1", "ORBStrategy"))
    dropped = {r["trade_id"] for r in pm.get_open_records()} == {"orb1"}
    check("B4b set_open_position REPLACES — which is why main.py must not "
          "call it when anything is open", dropped,
          "if this ever stops replacing, the r197 guard in main is moot")

    # ── B5: main.py decides `additive` from reality, not the call site ────
    src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    check("B5 the entry path appends whenever anything is open",
          "if additive or _pm.has_open_position():" in src)
    # ⚠️ r43 — B5b's RULE IS UNCHANGED; ITS MECHANISM IS GONE. It asserted the
    # butterfly-only box reached `attempt_new_entry` by checking the gate that
    # let it through: `if not pos_mgr.has_blocking_position():`. ADM.1 removed
    # that gate entirely, so EVERY box is asked for entries, butterfly-only or
    # not — the rule holds more strongly than when it was written. Asserting the
    # old mechanism would now fail on code that satisfies the rule completely.
    import ast as _a
    _ml = next(n for n in _a.walk(_a.parse(src))
               if isinstance(n, _a.FunctionDef) and n.name == "main_loop")

    def _calls_entry(body):
        return any(isinstance(c, _a.Call) and getattr(c.func, "id", "") == "attempt_new_entry"
                   for st in body for c in _a.walk(st))
    _both = any(isinstance(n, _a.If) and n.orelse
                and _calls_entry(n.body) and _calls_entry(n.orelse)
                for n in _a.walk(_ml))
    check("B5b a butterfly-only box is still asked for entries "
          "(r43: EVERY box is — entry runs in both branches)",
          _both and "if not pos_mgr.has_blocking_position():" not in src)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_butterfly_nonblocking: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
