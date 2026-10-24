#!/usr/bin/env python3
"""
tests/check_missed_inert.py  v1.1
v1.1  2026-10-19  OTV4TEST r303 (PSTATE.1) — its subject ORBStrategy (M1) / the M2 ledger row is DORMANT by default and a dormant plan now
      writes nothing by ruling, so this run switches it ACTIVE (OT_ORB_TRADE=1, OT_SWEEP_CS=1); what it pins is unchanged.

r95 — A MISSED SETUP IS A HEADSTONE, NOT A LOCK.

🔴 THE OPERATOR'S RULING, 2026-08-24, in two halves that pull against each
other and must BOTH hold:

    "An interrupted firing sequence should never attempt a late entry. Log it
     as missed. But normal entries that weren't filled and weren't interrupted
     should keep trying."

    "The condor is special. Leg 2 is permitted not implied. A miss of one
     firing sequence does not take another valid entry off the table."

The first half is easy to implement and easy to over-implement. The dangerous
failure is the SECOND one: a `MISSED` record that quietly becomes a reason to
refuse the next trade. That would look like caution and read like a bug fix,
and it would cost trades silently — the exact shape of every defect in
`docs/PORT_STATE.md`'s plausible-silence list.

⚠️ SO THE INVARIANT IS: THE PLAN LEDGER IS A RECORD, NOT AN AUTHORITY. Nothing
in the entry path may read it. Today that holds — every gating read is either
process-local (`has_active_plan`) or the trades DB (`_open_credit_sides`,
`_condor_leg_open_without_plan`) — and this file is what stops a later edit
from "improving" that by consulting the ledger.

⚠️ IT CHECKS BEHAVIOUR AND CALL SITES, NEVER SOURCE PROSE (WORKING_AGREEMENT
21/20). M1 drives a real sqlite ledger. M3 parses the import graph for READS,
scoped to the shape of a call, so a changelog line naming the ledger cannot
trip it.

Plain script with an exit code, deliberately not pytest (WORKING_AGREEMENT 36).

Run:  python3 tests/check_missed_inert.py
"""

from __future__ import annotations

import ast
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["OT_ORB_TRADE"] = "1"   # r303: the subject writes (check_plan_states pins dormant)
os.environ["OT_SWEEP_CS"] = "1"   # r303: the subject writes (check_plan_states pins dormant)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


class _Store:
    """Minimal stand-in for the derived store: a real sqlite connection."""

    def __init__(self, path):
        self.conn = sqlite3.connect(path)

    def commit(self):
        self.conn.commit()


def main() -> int:
    print("check_missed_inert — a MISSED plan closes the row and gates nothing")

    from derived.plan_ledger import PlanLedger, TERMINAL, LIVE

    # ── M1: MISSED CLOSES THE ROW ────────────────────────────────────────────
    # Operator: "log it as 'missed' to close out the plan/row". If MISSED were
    # not terminal the row would keep `closed_ts IS NULL`, `live_plans()` would
    # keep returning it, and status.py would show a pending ORB plan for the
    # rest of the session that no process is working on.
    tmp = os.path.join(tempfile.mkdtemp(), "derived.db")
    led = PlanLedger(_Store(tmp), "QQQ")

    pid = led.open_plan("ORBStrategy", "CONFIRMED", {"price": 706.0},
                        direction="LONG", trigger_price=706.0)
    check("M1a a plan opens and is LIVE", bool(pid) and len(led.live_plans()) == 1,
          f"live={len(led.live_plans())}")

    led.transition(pid, "MISSED", "TRIGGER_FIRED_WHILE_DOWN bar=09:39 age_s=1260")
    live_after = led.live_plans()
    row = led._store.conn.execute(
        "SELECT state, closed_ts, terminal_reason FROM plan_ledger"
        " WHERE plan_id=?", (pid,)).fetchone()

    check("M1b MISSED is terminal and closes the row",
          "MISSED" in TERMINAL and row and row[0] == "MISSED" and row[1] is not None,
          f"state={row[0] if row else None} closed_ts={'set' if row and row[1] else 'NULL'}")

    check("M1c a MISSED plan leaves live_plans() — it is not pending work",
          len(live_after) == 0, f"live={len(live_after)}")

    check("M1d the reason survives, so the cost is countable",
          row and row[2] and "WHILE_DOWN" in row[2], f"reason={row[2] if row else None}")

    check("M1e MISSED is NOT in the LIVE set", "MISSED" not in LIVE)

    # ── M2: A MISS DOES NOT OCCUPY A SIDE ────────────────────────────────────
    # "The condor is special. Leg 2 is permitted not implied. A miss of one
    # firing sequence does not take another valid entry off the table."
    # The pairing gate counts OPEN TRADES. A ledger row — of any state — is not
    # a trade and must not consume a side.
    # r303: IronCondorStrategy is DORMANT for good (no entry of its own) and opens no row; M2's rule is
    # strategy-agnostic (a ledger row of any state never consumes a side), so its row is a sweep leg's.
    missed_call = led.open_plan("SweepCreditSpread", "DECIDED", {"price": 706.0},
                                direction="SHORT", short_strike=712.0)
    led.transition(missed_call, "MISSED", "TRIGGER_FIRED_WHILE_DOWN")
    rows = led._store.conn.execute(
        "SELECT COUNT(*) FROM plan_ledger WHERE symbol='QQQ'").fetchone()[0]
    check("M2 both plans are recorded, neither is pending",
          rows == 2 and len(led.live_plans()) == 0,
          f"rows={rows} live={len(led.live_plans())}")

    # ── M3: NOTHING IN THE ENTRY PATH READS THE LEDGER ───────────────────────
    # 🔴 THE ONE THAT ACTUALLY PROTECTS THE RULING. Scoped to READ calls, so a
    # write (recording a plan) is fine and a comment naming the ledger cannot
    # trip it — WORKING_AGREEMENT 20's rule, since Rule 5 guarantees the word
    # appears in changelogs describing this very work.
    READ_CALLS = {"live_plans", "plans_for", "last_plan", "recent_plans"}
    ENTRY_FUNCS = {"attempt_new_entry", "_can_open_credit_spread",
                   "_open_credit_sides", "_condor_leg_open_without_plan"}

    offenders = []
    tree = ast.parse(open(os.path.join(ROOT, "main.py")).read())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in ENTRY_FUNCS:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                    if sub.func.attr in READ_CALLS:
                        offenders.append(f"main.{node.name} -> .{sub.func.attr}()")

    # The strategies decide; none of them may consult the record either.
    sdir = os.path.join(ROOT, "strategy")
    for fn in sorted(os.listdir(sdir)):
        if not fn.endswith(".py"):
            continue
        try:
            st = ast.parse(open(os.path.join(sdir, fn)).read())
        except SyntaxError:
            continue
        for sub in ast.walk(st):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                if sub.func.attr in READ_CALLS:
                    offenders.append(f"strategy/{fn} -> .{sub.func.attr}()")

    check("M3 no entry-path caller READS the plan ledger",
          not offenders, "; ".join(offenders) if offenders else "")

    # ── M4: THE PAIRING GATE STILL READS TRADES ──────────────────────────────
    # The positive half of M3: confirm the gate does consult SOMETHING, so a
    # future edit cannot satisfy M3 by deleting the gate entirely.
    src = open(os.path.join(ROOT, "main.py")).read()
    ocs = ast.parse(src)
    reads_trades = False
    for node in ast.walk(ocs):
        if isinstance(node, ast.FunctionDef) and node.name == "_open_credit_sides":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
                        and sub.func.attr == "get_open_trades":
                    reads_trades = True
    check("M4 the pairing gate reads OPEN TRADES (it is not merely absent)",
          reads_trades)

    print()
    if FAILURES:
        print(f"FAILED {len(FAILURES)}: {', '.join(FAILURES)}")
        return 1
    print("check_missed_inert: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
