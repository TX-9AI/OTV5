#!/usr/bin/env python3
"""
tests/check_entry_floor_env.py  v5.0
v5.0  2026-10-30  OTV5 r59 (ENT.1) — born with the fix.

ENTRY_OPEN_ET MUST HOLD ON THE PRODUCTION CLOCK. entries_open() applied the
config floor only when a caller passed `now`; both choke points call it bare,
so on 2026-10-30 the approved session floor OT_ENTRY_OPEN_ET=10,0 on AMZN held
Hunt and Runaway (they read the constant themselves) but AMZN's Breakout
opened at 09:38. Operator: "obviously fix this".

Born RED on 83abcc6 at F1a, F1b, F3b, F4a, and F5a raises (the held entry reached the logger).

  F1  a bare call (the production form) honours a 10:00 floor: closed 09:38, 09:59; open 10:00
  F2  the default (09:35) is unchanged on the bare call: closed 09:34, open 09:35
  F3  an explicit clock gives the same answer as the bare call
  F4  an override EARLIER than the range never opens before ORB_END (09:35)
  F5  the debit choke point `entry_engine.enter()` refuses at 09:38 under a 10:00 floor
      and books nothing; proceeds at 10:00
  F6  malformed override still FAILS CLOSED on the bare call; outside RTH still closed

Run:  python3 tests/check_entry_floor_env.py
"""
from __future__ import annotations
import os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILURES: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)

import config
import utils.time_utils as tu
from utils.time_utils import ET, entries_open

def at(h, m):
    return datetime(2026, 10, 30, h, m, tzinfo=ET)        # a Friday, full RTH day

_saved_floor, _saved_now = config.ENTRY_OPEN_ET, tu.now_et

def bare(h, m):
    tu.now_et = lambda: at(h, m)
    return entries_open()

try:
    # ── F1 — the production (bare) call honours a 10:00 floor ───────────────
    config.ENTRY_OPEN_ET = (10, 0)
    check("F1a bare 09:38 under 10:00 — CLOSED", bare(9, 38) is False)
    check("F1b bare 09:59 under 10:00 — CLOSED", bare(9, 59) is False)
    check("F1c bare 10:00 under 10:00 — open",   bare(10, 0) is True)

    # ── F2 — default unchanged ─────────────────────────────────────────────
    config.ENTRY_OPEN_ET = (9, 35)
    check("F2a bare 09:34 default — closed", bare(9, 34) is False)
    check("F2b bare 09:35 default — open",   bare(9, 35) is True)

    # ── F3 — explicit and bare agree ───────────────────────────────────────
    config.ENTRY_OPEN_ET = (10, 0)
    check("F3a explicit 09:38 under 10:00 — closed", entries_open(at(9, 38)) is False)
    check("F3b bare == explicit at 09:38", bare(9, 38) == entries_open(at(9, 38)))

    # ── F4 — never before the range ────────────────────────────────────────
    config.ENTRY_OPEN_ET = (9, 30)
    check("F4a explicit 09:32 under 09:30 — closed (range not established)",
          entries_open(at(9, 32)) is False)
    check("F4b bare 09:32 under 09:30 — closed", bare(9, 32) is False)
    check("F4c bare 09:35 under 09:30 — open", bare(9, 35) is True)

    # ── F5 — the debit choke point, driven for real ────────────────────────
    import execution.entry_engine as ee
    from strategy.base_strategy import OptionsSignal
    from data.options_chain import OptionContract

    class _Boom:
        def __getattr__(self, k):
            raise AssertionError("the gate let a held entry reach the broker/logger")

    eng = ee.EntryEngine(paper_trading=True)
    eng._trade_logger = _Boom()
    sig = OptionsSignal(strategy_name="BreakoutStrategy", setup_type="breakout_long",
                        option_side="call", strike=245.0, entry_premium=2.10,
                        underlying_entry=244.0,
                        contract=OptionContract(symbol="X", strike=245.0, mark=2.10))
    class _Sizing: allowed, contracts, total_cost = True, 1, 210.0

    config.ENTRY_OPEN_ET = (10, 0)
    tu.now_et = lambda: at(9, 38)
    check("F5a 09:38 under 10:00 — enter() refuses and books nothing",
          eng.enter(sig, _Sizing()) is None)
    tu.now_et = lambda: at(10, 0)
    try:
        eng.enter(sig, _Sizing())
        check("F5b 10:00 — enter() proceeds past the gate", False,
              "returned without touching the logger")
    except AssertionError:
        check("F5b 10:00 — enter() proceeds past the gate", True,
              "reached the trade logger, which is the tripwire")

    # ── F6 — fail closed ──────────────────────────────────────────────────
    config.ENTRY_OPEN_ET = ("ten", "zero")
    check("F6a malformed override, bare 11:00 — CLOSED", bare(11, 0) is False)
    config.ENTRY_OPEN_ET = (10, 0)
    check("F6b bare 16:53 — CLOSED (outside RTH)", bare(16, 53) is False)
finally:
    config.ENTRY_OPEN_ET, tu.now_et = _saved_floor, _saved_now

print()
print("FAIL: " + ", ".join(FAILURES) if FAILURES else "PASS")
sys.exit(1 if FAILURES else 0)
