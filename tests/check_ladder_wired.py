#!/usr/bin/env python3
"""
tests/check_ladder_wired.py  v1.3
v1.3  2026-09-26  OTV4TEST r149 (EOD.1) — L7's hard-close rows and L8b/L8c RE-POINTED to the operator's
      end of day ("Resting limit orders at 1545, ladder exits at 1550 if they're not the assignment
      risk type"; "Best case on the trajectory"): a credit hard close RESTS at its best case before
      15:55 and CROSSES at 15:55, so r105's never-cross (L8b) and nickel-only (L8c) are superseded.
      L7 now pins the clock (15:46 and 15:55) instead of reading the wall clock. The behaviour is
      driven in tests/check_eod_schedule.py E5/E7/E10; these stay as the text-level pins.
v1.2  2026-08-27  r160: L10 re-pinned again — authorize() + the sweep; the
      condor's one-level plan is deleted.
v1.1  2026-08-26  r147: L10 re-pinned — the second-leg window routes through
      the condor's one-level plan and the three direct triggers are gone.

r104 — THE ENTRY LADDER IS CALLED, WALKS, RATCHETS, AND NEVER CROSSES.

Born RED at 3f23ab5 (r103) on L1..L5: entry_ladder.py had ZERO importers and
every live entry posted a single limit at mark. FRC.1: +$2.70/trade gross edge
against $126/trade round-trip friction — half the half-spread is ~$31/trade.

  L1  entry_ladder / ladder_registry HAVE importers in the live order path
  L2  a walk RESUMES across calls (one rung per tick is the whole design) and
      the ratchet never re-offers a refused price
  L3  the walk never posts WORSE THAN MARK, on either side
  L4  a refusal advances the rung; a fill clears the walk (no stale ratchet)
  L5  PAPER IS UNTOUCHED — no paper path imports the ladder
  L6  the per-rung deadline is a SLICE of the entry budget, not all of it

Run:  python3 tests/check_ladder_wired.py
"""
from __future__ import annotations
import ast, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)

# ── L1 — it is actually called ───────────────────────────────────────────────
importers = []
for rel in ("execution/entry_engine.py", "main.py", "execution/exit_engine.py",
            "strategy/condor_roll.py"):
    src = open(os.path.join(ROOT, rel)).read()
    if "ladder_registry" in src or "entry_ladder" in src:
        importers.append(rel)
check("L1 the ladder has importers in the order path", 
      "execution/entry_engine.py" in importers, f"importers: {importers}")

src = open(os.path.join(ROOT, "execution/entry_engine.py")).read()
tree = ast.parse(src)
fns = {n.name: ast.unparse(n) for n in ast.walk(tree)
       if isinstance(n, ast.FunctionDef)}
check("L1a _place_single_leg prices through the walk",
      "_walk_price" in fns.get("_place_single_leg", ""))
check("L1b _place_butterfly prices through the walk",
      "_walk_price" in fns.get("_place_butterfly", ""))
check("L1c single-leg no longer posts a bare limit_at_mark",
      "limit_at_mark" not in fns.get("_place_single_leg", ""))

# ── L2 — the walk resumes and ratchets ───────────────────────────────────────
from execution import ladder_registry as lr
lr.reset_all()
K = lr.intent_key("TEST 260825C81", "open", "single")
seen = []
for _ in range(6):
    got = lr.price_for(K, "buy", 0.00, 1.00, "QQQ")
    assert got, "price_for returned None on a usable quote"
    seen.append(got[0])
    lr.refuse(K, got[0])
check("L2a the walk advances across calls", len(set(seen)) > 1, f"{seen}")
check("L2b it never re-offers a refused price", len(seen) == len(set(seen)), f"{seen}")
check("L2c and it walks TOWARD mark, never past it",
      all(p <= 0.50 + 1e-9 for p in seen), f"{seen} vs mark 0.50")

# ── L3 — never worse than mark, both sides ───────────────────────────────────
lr.reset_all()
K2 = lr.intent_key("T2", "open", "single")
sells = []
for _ in range(6):
    got = lr.price_for(K2, "sell", 0.00, 1.00, "QQQ")
    sells.append(got[0]); lr.refuse(K2, got[0])
check("L3 selling never posts BELOW mark", all(p >= 0.50 - 1e-9 for p in sells), f"{sells}")

# ── L4 — a fill clears the walk ──────────────────────────────────────────────
lr.reset_all()
K3 = lr.intent_key("T3", "open", "single")
lr.price_for(K3, "buy", 0.40, 0.50, "NFLX")
check("L4a a walk in flight is tracked", lr.active() == 1, f"active={lr.active()}")
lr.clear(K3)
check("L4b a filled walk is cleared (no stale ratchet)", lr.active() == 0)

# ── L5 — paper is untouched ──────────────────────────────────────────────────
paper_fns = [n for n in ("_paper_fill_single", "_paper_fill_butterfly")]
leaked = [f for f in paper_fns
          if "ladder_registry" in fns.get(f, "") or "_walk_price" in fns.get(f, "")]
check("L5 no PAPER path touches the ladder", not leaked, f"{leaked}")

# ── L6 — the rung deadline is a slice ────────────────────────────────────────
import config
from execution.entry_engine import EntryEngine
rd = EntryEngine._rung_deadline()
total = float(getattr(config, "LIVE_ENTRY_DEADLINE_SECONDS", 20.0))
check("L6a a rung gets a SLICE of the entry budget", rd < total, f"{rd}s of {total}s")
check("L6b and never so short a fillable price is abandoned unseen", rd >= 4.0, f"{rd}s")
import inspect
from execution.order_confirm import confirm_order_fill
check("L6c confirm_order_fill accepts a per-call deadline",
      "deadline_s" in inspect.signature(confirm_order_fill).parameters)

# ── L7 (r105) — the EXIT policy table, per TRADES.md §6 ──────────────────────
from execution.exit_engine import ExitEngine
_ee = ExitEngine.__new__(ExitEngine)
_credit = {"strategy": "IronCondorStrategy", "setup_type": "1h_fork_call_credit_spread",
           "is_condor_leg": 1}
_debit  = {"strategy": "ORBStrategy", "setup_type": "orb_long"}
import datetime as _dt
from zoneinfo import ZoneInfo as _Z
import execution.exit_engine as _EEm
_real_now = _EEm.now_et
from config import EOD_RESTING_AT_ET as _RA, EOD_LADDER_AT_ET as _LA
_RL, _LL = f"hard_close_resting_{_RA[0]:02d}:{_RA[1]:02d}_ET", f"hard_close_ladder_{_LA[0]:02d}:{_LA[1]:02d}_ET"
for _hm, _want in (((15, 46), "eod_resting"), ((15, 55), "eod_cross")):
    _EEm.now_et = (lambda h=_hm: _dt.datetime(2026, 9, 28, h[0], h[1], 5, tzinfo=_Z("America/New_York")))
    try:
        _got = ExitEngine._exit_policy(_credit, _RL)
    finally:
        _EEm.now_et = _real_now
    check(f"L7 {_want:<18} <- {_RL} at {_hm[0]}:{_hm[1]:02d}", _got == _want, f"got {_got}")
cases = [
    (_debit,  _LL, "debit_hard_close"),
    (_credit, "condor_stop pnl=-15.2% (lone 15%)", "floor"),
    (_debit,  "hard_stop_25% pnl=-25.0%", "floor"),
    (_debit,  "orb_structure_stop: 1m close 99.10 below 99.50", "floor"),
    (_credit, "nickel_close pnl=91.0%", "walk"),
    (_debit,  "target_hit pnl=100.0%", "walk"),
    (_debit,  "orb_trail_stop pnl=42.0%", "walk"),
    (_credit, "rolled_to_broken_wing", "walk"),
]
for rec, reason, want in cases:
    got = ExitEngine._exit_policy(rec, reason)
    check(f"L7 {want:<18} <- {reason[:34]}", got == want, f"got {got}")

# ── L8 (r105) — the floor does NOT walk, and the credit close never crosses ──
src_x = open(os.path.join(ROOT, "execution/exit_engine.py")).read()
tx = ast.parse(src_x)
fx = {n.name: ast.unparse(n) for n in ast.walk(tx) if isinstance(n, ast.FunctionDef)}
check("L8a the floor goes to mark, no walk",
      "no walk" in fx.get("_exit_limit", ""))
check("L8b r149: the cross is no longer refused for a credit vertical (r105's never-cross superseded)",
      "is_credit_vertical(record)" not in fx.get("_submit_live_close", ""))
check("L8c r149: the credit hard close RESTS at its best case (_eod_best_case), not the width",
      "eod_resting" in fx.get("_close_vertical", "") and "_eod_best_case" in fx.get("_exit_limit", ""))
check("L8d a booked exit clears its walk",
      "_exit_walk_done" in fx.get("_book_from_fills", ""))

# ── L9 (r105) — the roll's open half walks IN-LINE (it cannot cross ticks) ───
src_r = open(os.path.join(ROOT, "strategy/condor_roll.py")).read()
fr = {n.name: ast.unparse(n) for n in ast.walk(ast.parse(src_r))
      if isinstance(n, ast.FunctionDef)}
check("L9a the roll open walks rungs", "rungs" in fr.get("_execute_roll", ""))
check("L9b in ONE call — a half-rolled position is never left to next tick",
      "for _rung in _ladder" in fr.get("_execute_roll", ""))

# ── L10 (r147, supersedes r105) — the second-leg window is ONE plan ──────────
# Operator, 2026-08-26: leg two is sold only on a level the tape has REJECTED,
# one level at a time. The four direct attempts (1d fork, sweep, TC.6, and the
# 1h tine on approach) are gone from main_loop; their levels are candidates
# INSIDE the condor's plan_second_leg.
src_m = open(os.path.join(ROOT, "main.py")).read()
lm = next(n for n in ast.walk(ast.parse(src_m))
          if isinstance(n, ast.FunctionDef) and n.name == "main_loop")
lsrc = ast.unparse(lm)
check("L10 second leg: the condor AUTHORIZES a side and the sweep's own plan prepares it",
      ".authorize(" in lsrc and "SweepForLeg2" in lsrc and "plan_second_leg(" not in lsrc)
for tag in ("DailyFork2nd", "SweepCS2nd", "TrendCS2nd"):
    check(f"L10 second leg NO LONGER fires {tag} directly", tag not in lsrc)

print(f"\n{'PASS' if not FAILURES else 'FAIL'}: {len(FAILURES)} problem(s) {FAILURES}")
sys.exit(1 if FAILURES else 0)
