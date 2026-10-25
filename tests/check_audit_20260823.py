#!/usr/bin/env python3
"""
tests/check_audit_20260823.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.2  2026-10-19  OTV4TEST r303 (PSTATE.1) — a3 drives IronCondorStrategy's own ledger path, and the condor is DORMANT for
      good (no entry of its own), so a3 lifts the state for that one call; the invariant it pins (an abandoned plan closes its row) is unchanged.
v1.1  2026-09-14  OTV4TEST r26 — 🔴 A1 RAN THE REAL RETENTION PURGE, WITH --apply, ON THE BOX'S
      OWN FEED STORE. `self_close.main()` was driven with only `subprocess.run`
      faked; after the (faked) verifier said OK it called
      `retention_purge.main(["--apply"])` for real. `purge()` honours
      OT_DERIVED_DB but opens `<repo>/data/feed_store.db` unconditionally, so every
      run of this check DELETED live rows past the retention windows (1m candles
      > 5 days; quotes, prints, greeks, last_trade, session_summary > 3 days;
      chain_snapshots > 3 days) and ran the reclaim on the real feed_store.db and
      trades.db. On this box that happened on each full check sweep — r20's and
      the r25/r26 sweeps of 2026-09-13/14 — and cost Thursday 09-10's quotes and
      prints. The purge is now REPLACED by a recorder for the call, and A1b
      asserts self_close still asks for it with --apply (the r162 property)
      without executing it. HYG.10.
Executing pins for the 2026-08-23 adversarial audit (F1, F3, F6, F9).

v1.0  2026-08-23  Born RED at r82 `fe832ae` on all four; green on the fixed
tree. Each pin EXECUTES the path or reads the one token the bug lived on —
never a version string, never a docstring word (WA §20/§21/§24).

  A1  self_close spawns the verifier under SYSTEM python, not sys.executable.
      The bot venv has no boto3; under it s3_push prints "run aborted" and the
      box stays up every night. Pin = the command list's interpreter.
  A2  The ORB rescue asks for THE 09:30 bar, not "any bar since 09:30".
      Pin = a store holding only a 09:45 bar must still trigger the rescue.
  A3  Leg-2 fill reaches plan_ledger as COMPLETE, and a fork-invalidation
      cancel reaches it as CANCELLED. Pin = drive notify_leg_filled on a plan
      with one side already filled and read the ledger back.
  A4  A fire clears the gate block. Pin = block, fire, snapshot must be empty
      and a CLEARED row must exist.

Run:  cd ~/options-trader && python3 tests/check_audit_20260823.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_PAPER_TRADING", "1")

PROBLEMS: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}"
          + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


# ── A1 ─────────────────────────────────────────────────────────────────
def a1():
    import subprocess
    from warehouse import self_close as sc
    seen = {}

    def fake_run(cmd, **kw):
        if isinstance(cmd, list) and any("s3_push.py" in str(c) for c in cmd):
            seen["interp"] = cmd[0]
            return types.SimpleNamespace(stdout="DRAIN host=x sym=X drained=yes "
                                         "pushed=0 failed=0 prefixes=1 local=1 "
                                         "s3=1 short=0 OK", stderr="")
        return types.SimpleNamespace(stdout="", stderr="")
    # ⚠️ THE SANDBOX'S sys.executable IS ALREADY SYSTEM PYTHON, so an
    # environment-true check would pass against the bug. Pretend to be the
    # venv, as the unit really does, and assert the verifier is NOT spawned
    # under it.
    # 🔴 r26 — NEVER THE REAL PURGE. self_close calls it after the verifier says
    # OK, and purge() opens the box's real feed_store.db whatever the env says.
    from warehouse import retention_purge as _rp
    purge_calls = []
    orig_purge = _rp.main
    _rp.main = lambda argv=None: purge_calls.append(list(argv or [])) or 0
    orig, orig_exe = subprocess.run, sys.executable
    subprocess.run = fake_run
    sys.executable = "/home/ubuntu/options-trader/venv/bin/python"
    try:
        sc.main(["self_close.py"])
    finally:
        subprocess.run, sys.executable = orig, orig_exe
        _rp.main = orig_purge
    check("A1b self_close asks for the purge with --apply (recorded, never executed)",
          purge_calls == [["--apply"]], f"calls={purge_calls}")
    interp = seen.get("interp", "")
    check("A1 verifier is NOT spawned under the bot venv (boto3 lives in system python)",
          bool(interp) and "venv" not in interp and interp.endswith("python3"),
          f"interpreter={interp!r}")


# ── A2 ─────────────────────────────────────────────────────────────────
def a2():
    import asyncio
    from datetime import datetime, time as dtime, timedelta
    from data import candle_feed as cf
    feed = cf.CandleFeed.__new__(cf.CandleFeed)
    feed._orb_rescue_done_for = ""
    feed.dx_symbol = "X"
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE candles (symbol TEXT, interval TEXT, ts_epoch_ms INTEGER)")
    # Pin the clock inside the window and plant ONLY a 09:45 bar.
    now = datetime.now(cf.ET).replace(hour=10, minute=0, second=0, microsecond=0)
    while now.weekday() >= 5:
        now -= timedelta(days=1)
    open_ms = int(datetime.combine(now.date(), dtime(9, 30), tzinfo=cf.ET).timestamp() * 1000)
    con.execute("INSERT INTO candles VALUES (?,?,?)", (cf.INSTRUMENT, "5m", open_ms + 15 * 60000))
    feed.store = types.SimpleNamespace(conn=con)
    calls = []

    class S:
        async def unsubscribe_candle(self, *a, **k): calls.append("unsub")
        async def subscribe_candle(self, *a, **k): calls.append("sub")

    class FakeDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return now
    orig = cf.datetime
    cf.datetime = FakeDT
    try:
        attempted = asyncio.run(feed._maybe_rescue_opening_range(S()))
    finally:
        cf.datetime = orig
    check("A2 rescue fires when the 09:30 bar is missing but a later bar exists",
          attempted is True and calls == ["unsub", "sub"],
          f"attempted={attempted} calls={calls}")


# ── A3 ─────────────────────────────────────────────────────────────────
class _Store:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")

    def commit(self):
        self.conn.commit()


def a3():
    from derived.plan_ledger import PlanLedger
    from strategy import iron_condor_strategy as ics
    store = _Store()
    led = PlanLedger(store, "X")
    strat = ics.IronCondorStrategy.__new__(ics.IronCondorStrategy)
    strat._plan = None
    strat._plan_id = None
    strat._orphan_said = False
    strat._last_reset_date = None
    strat._ledger = lambda: led                      # inject, no registry
    # ⚠️ REWRITTEN 2026-08-24 FOR THE CONDOR REMODEL. The original drove
    # `notify_leg_filled` on a LEG1_FILLED plan with leg1_side/leg2_side — the
    # PAIR-EXPECTATION MACHINERY, which the remodel deliberately deleted
    # because the legs are now independently gated and a second leg is ALLOWED,
    # NEVER EXPECTED. The test referenced `CondorState`, which no longer
    # exists, so it failed on an AttributeError rather than on the invariant.
    # 🔑 THE INVARIANT SURVIVES THE REMODEL AND IS WHAT F6 ACTUALLY PROTECTS:
    # a plan that is abandoned MUST close its ledger row. An unclosed row means
    # status.py shows a plan that does not exist, forever — the immortal
    # LEG1_FILLED rows Fable found. The remodel renamed the mechanism to
    # `_ledger_expire`; the requirement is unchanged.
    plan = types.SimpleNamespace(max_price_seen=None, min_price_seen=None,
                                 short_call_strike=0, long_call_strike=0,
                                 short_put_strike=0, long_put_strike=0,
                                 underlying_at_decision=0, expected_move=0)
    strat._plan = plan
    from strategy import plan_state as _ps                 # r303: the condor is DORMANT for good; lift it for a3
    _orig_state = _ps.state
    _ps.state = lambda n: "active" if _ps.base(n) == "IronCondorStrategy" else _orig_state(n)
    try:
        strat._ledger_open(plan, {})
    finally:
        _ps.state = _orig_state
    pid = strat._plan_id
    strat._ledger_expire("past_cutoff")
    row = store.conn.execute("SELECT state, closed_ts FROM plan_ledger WHERE plan_id=?",
                             (pid,)).fetchone()
    check("A3a an abandoned plan closes its ledger row (no immortal rows)",
          row is not None and row[1] is not None,
          f"row={row}")
    # ⚠️ AND THE ID IS RELEASED, or the next expire silently re-closes the old
    # row while the new plan stays open forever.
    check("A3a2 _plan_id is released after expire",
          strat._plan_id is None, f"_plan_id={strat._plan_id}")
    # fork-invalidation cancel path: the DECIDED branch must record CANCELLED
    src = open(os.path.join(ROOT, "strategy", "iron_condor_strategy.py"), encoding="utf-8").read()
    # ⚠️ EVERY abandon path must close the row, not just the one that had a
    # bug. The remodel has four: new day, fork invalidated, past cutoff,
    # session end. A path that clears `self._plan` without telling the ledger
    # is the immortal-row bug returning by a different door.
    import re as _re
    abandons = _re.findall(r"\n(.{0,400}?self\._plan = None)", src, _re.S)
    unclosed = [a.strip().splitlines()[0][:60] for a in abandons
                if "_ledger_expire" not in a and "_ledger_move" not in a
                and "def " not in a.split("self._plan = None")[0][-80:]]
    check("A3b every abandon path closes the ledger row",
          not unclosed, f"paths clearing _plan without a ledger close: {unclosed}")


# ── A4 ─────────────────────────────────────────────────────────────────
def a4():
    from analysis import gate_report as gr
    store = _Store()
    r = gr.GateReporter(store, "X")
    r.blocked("SweepCreditSpread", "age", "too old")
    fired = getattr(r, "fired", None)
    if fired:
        fired("SweepCreditSpread")
    snap = r.snapshot()
    n = store.conn.execute("SELECT COUNT(*) FROM gate_disposition WHERE event='CLEARED'").fetchone()[0]
    check("A4 a fire clears the block (snapshot empty, CLEARED row written)",
          fired is not None and "SweepCreditSpread" not in snap and n == 1,
          f"fired={'present' if fired else 'MISSING'} snap={snap} cleared_rows={n}")


def main() -> int:
    print("=" * 62)
    print("AUDIT 2026-08-23 PINS: F1 self_close · F3 rescue · F6 plans · F9 gates")
    print("=" * 62)
    for fn in (a1, a2, a3, a4):
        try:
            fn()
        except Exception as exc:                                # noqa: BLE001
            check(f"{fn.__name__} executes", False, f"{type(exc).__name__}: {exc}")
    print("-" * 62)
    if PROBLEMS:
        print(f"FAIL  {len(PROBLEMS)} problem(s): {', '.join(PROBLEMS)}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
