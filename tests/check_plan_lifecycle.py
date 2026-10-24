#!/usr/bin/env python3
"""
tests/check_plan_lifecycle.py  v1.1
v1.1  2026-10-19  OTV4TEST r303 (PSTATE.1) — its subject SweepCreditSpread is DORMANT by default and a dormant plan now
      writes nothing by ruling, so this run switches it ACTIVE (OT_SWEEP_CS=1); what it pins is unchanged.
v1.0  2026-09-01  r212 (chunk D) — A PLAN CLOSES WHEN ITS TRADE DOES.

🔴 THE DEFECT, MEASURED FROM THE OPERATOR'S OWN PANEL. On 2026-09-01 QQQ showed
SEVEN `RunawayContinuation TRIGGERED @ 708.43` rows, every one flagged `<- LIVE`
— while six of those trades had closed hours earlier. `PlanTick.take()` opens a
`plan_ledger` row on every fire, and `transition()` had exactly TWO callers,
main.py's ORB plan and the condor's `_plan_id`. Nothing closed a row opened
through `Plan._ledger_open`, so `closed_ts` stayed NULL for the session and
`live_plans()` returned every fired plan forever.

🔴 AND r199 MISDIAGNOSED IT AS DUPLICATION. It saw two rows for one strategy at
one trigger, called them duplicates, collapsed them for display and printed the
count so "the duplication stays visible". They were never duplicates — they
were real, distinct plans that had not been closed, and the collapse was
merging trades with different outcomes because the key (strategy, state,
trigger) cannot tell two runaway fires at one boundary apart. RPT.5 recorded
that the WRITE side had never been examined; this is that examination.

⚠️ TWO LEAKS, NOT ONE. A plan that FILLS is closed by its exit. A plan that
FIRES and is then refused — sizing rejection, no priced contract, a failed
order — links no trade at all, so the exit hook can never reach it. Both are
covered, and they are kept DISTINCT: "fired and lost" and "fired and never
filled" are the two populations this ledger exists to separate.

⚠️ EVERY CHECK BELOW EXECUTES. WORKING_AGREEMENT 21 — a test that reads source
proves nothing about runtime, and this whole defect is a call that was never
made.

Born red at 631b0e9 (r211), where L1-L5 all fail.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ["OT_SWEEP_CS"] = "1"   # r303: the subject writes (check_plan_states pins dormant)

_fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


class _Store:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

    def commit(self):
        self.conn.commit()


def main():
    from derived.plan_ledger import PlanLedger

    # ⚠️ DEGRADE TO A NAMED FAILURE, never an AttributeError (r192): "the
    # checker crashed" and "the invariant is violated" must not look alike.
    missing = [n for n in ("close_for_trade", "close_unfilled")
               if not hasattr(PlanLedger, n)]
    if missing:
        for n in missing:
            check(f"L0 PlanLedger.{n} exists", False, "not implemented")
        print()
        print(f"FAILED {len(_fails)}: plan_ledger is pre-r212 "
              f"(missing {', '.join(missing)})")
        return 1

    def _fresh():
        st = _Store()
        return st, PlanLedger(st, "QQQ")

    # ── L1 — THE 2026-09-01 SHAPE: seven fires, six closed trades ────────
    st, led = _fresh()
    ids = []
    for i in range(7):
        pid = led.open_plan("RunawayContinuation", "TRIGGERED", {"price": 708.43},
                            trigger_price=708.43)
        led.link_trade("RunawayContinuation", f"t{i}")
        ids.append(pid)
    before = len(led.live_plans())
    for i in range(6):
        led.close_for_trade(f"t{i}", "hard_stop_20%")
    after = led.live_plans()
    check("L1 seven fires, six trades closed -> exactly one plan still live",
          before == 7 and len(after) == 1,
          f"{before} live before, {len(after)} after (want 7 -> 1)")

    # ⚠️ AND THE SURVIVOR IS THE RIGHT ONE — the plan whose trade is still
    # open, not simply the newest row.
    check("L1b the surviving plan is the one whose trade never closed",
          len(after) == 1 and after[0]["plan_id"] == ids[6],
          f"live={after[0]['plan_id'][:8] if after else None} want={ids[6][:8]}")

    # ── L2 — closing is keyed on the TRADE, not the strategy ─────────────
    # 🔑 `link_trade` resolves the most-recent-live plan and records that as an
    # ⟨ASSUMPTION⟩. Closing has an exact key available, so it must not inherit
    # that heuristic: closing trade t2 closes t2's plan and nothing else.
    st, led = _fresh()
    a = led.open_plan("SweepCreditSpread", "TRIGGERED", {"price": 100.0})
    led.link_trade("SweepCreditSpread", "ta")
    b = led.open_plan("SweepCreditSpread", "TRIGGERED", {"price": 101.0})
    led.link_trade("SweepCreditSpread", "tb")
    led.close_for_trade("ta", "stopped")
    live = {p["plan_id"] for p in led.live_plans()}
    check("L2 closing one trade closes ITS plan, not the newest",
          a not in live and b in live,
          f"a_closed={a not in live} b_live={b in live}")

    # ── L3 — a plan that never filled is superseded, not left live ───────
    st, led = _fresh()
    led.open_plan("GEXPinButterfly", "TRIGGERED", {"price": 50.0})
    n = led.close_unfilled("GEXPinButterfly", "superseded — never filled")
    check("L3 an unfilled plan is closed when the next one fires",
          n == 1 and not led.live_plans(), f"closed {n}")

    # ── L4 — AND A FILLED PLAN IS NEVER SUPERSEDED ──────────────────────
    # 🔴 THE CHECK THAT PROTECTS THE DATA. If supersession swept filled plans
    # too, "fired and lost" and "fired and never filled" would collapse into
    # one bucket — and those are the two populations the whole ledger exists to
    # tell apart. A filled plan is closed by its EXIT and by nothing else.
    st, led = _fresh()
    f = led.open_plan("SweepCreditSpread", "TRIGGERED", {"price": 100.0})
    led.link_trade("SweepCreditSpread", "tf")
    n = led.close_unfilled("SweepCreditSpread", "superseded")
    check("L4 a plan holding a trade is NOT closed by supersession",
          n == 0 and any(p["plan_id"] == f for p in led.live_plans()),
          f"swept {n} (want 0)")

    # ── L5 — the terminal reason is recorded, not just the closure ───────
    # A row that closes with no reason cannot answer "how did this plan end",
    # which is the question the ledger is for.
    st, led = _fresh()
    p5 = led.open_plan("RunawayContinuation", "TRIGGERED", {"price": 1.0})
    led.link_trade("RunawayContinuation", "t5")
    led.close_for_trade("t5", "target_hit pnl=111.6%")
    row = st.conn.execute(
        "SELECT state, terminal_reason, closed_ts FROM plan_ledger"
        " WHERE plan_id=?", (p5,)).fetchone()
    check("L5 the close records its state, reason and timestamp",
          row and row["state"] == "CLOSED" and row["closed_ts"]
          and "target_hit" in (row["terminal_reason"] or ""),
          f"{dict(row) if row else None}")

    # ── L6 — an unknown trade closes nothing, silently and safely ────────
    st, led = _fresh()
    led.open_plan("SweepCreditSpread", "TRIGGERED", {"price": 1.0})
    led.link_trade("SweepCreditSpread", "tz")
    got = led.close_for_trade("not-a-trade", "x")
    check("L6 an unmatched trade_id closes nothing and does not raise",
          got is None and len(led.live_plans()) == 1)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_plan_lifecycle: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
