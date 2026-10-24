#!/usr/bin/env python3
"""
tests/check_structure_stop_ramp.py  v1.1
v1.1 2026-09-22  OTV4TEST r93 — N1-N5 pin the noise floor: refusal inside, trade
      outside, the boundary itself, unmeasurable-disarms, degenerate-unchanged,
      and that the multiplier is the ARGUED 0.5x rather than the day's best
      fit — a checker drifting to the fitted value is the curve-fit
      PREREG_TRAIL.md exists to prevent.
v1.0  2026-09-22  OTV4TEST r91 — born RED at a26da0c, R0 NAMING the
      missing machinery rather than dying on a traceback. Pins the
      operator's 1-R ramp end to end: the structural stop, the two
      declared ends of the scale, the wide-stop and total-loss holes,
      ORB/Breakout parity, the entry-armed structure-floored trail, and
      the blast radius (every other strategy keeps r44's gain floor).

r91 — THE OPERATOR'S 1-R RAMP, AND THE BLIND SPOT THAT HID ITS ABSENCE.

His specification, 2026-09-22: *"position sizing was supposed to be based on
the stop distance represented by the entry point measured down to the extreme
of the impulsive candle. That distance is our 1-R. If the impulsive candle is
deep in the range, it'll create a large stop distance and risk to the operator
is very high, so we allocate a smaller position size when the extreme of the
impulsive candle is close to the boundary it creates a very small risk to the
operator so we scale up accordingly."*

And the two ends of the ramp: *"that 1050 is a minimum. The orbs entire budget
is the maximum and it's used for scaling."*

🔴 WHY THIS FILE EXISTS RATHER THAN MORE ROWS IN `check_orb_budget`. That file
already claims to prove the curve — B3, *"tight stops get the budget, wide
stops get a 1-lot, monotone in between"*. Its helper is:

    def orb(prem, w, d, budget):
        return rm.size_for("long_debit", premium=prem, orb_width=w,
                           orb_stop_distance=d, budget_usd=budget)

**IT PASSES NO `stop_premium`.** So every check in that file takes the
`_sp > 0` FALSE branch, where `by_risk` falls back to `by_geometry` — the
branch production NEVER takes, because production always supplies a stop. B3
proved the operator's curve on a code path no trade has ever used, stayed
green for four days while the live path was flat, and could not have gone red.
§40.1: a check that is well-formed, passes, and is about nothing.

⚠️ SO EVERY CHECK BELOW SUPPLIES A REAL STOP PREMIUM, and the ones that matter
drive `OptionsSignal.stop_premium()` rather than hand-rolling a number — a
fixture built from the assistant's own belief cannot fail (§0.4).

Run:  python3 tests/check_structure_stop_ramp.py
"""
from __future__ import annotations
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = tempfile.mkdtemp(prefix="check_structure_stop_ramp.")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_s, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))

# 🔴 THE RAMP'S TWO ENDS ARE DECLARED HERE, BEFORE config IS IMPORTED, AND
# THAT IS NOT A CONVENIENCE — IT IS §36.
# A checker runs from `boot_sweep` and from `land.sh` with NO service
# environment, so it reads config's bare defaults ($200) rather than the
# operator's declared numbers. The first run of this file went RED on seven
# checks for exactly that reason: at a $200 ceiling every row clamps to a
# 2-lot and the ramp collapses — a verification going red on ENVIRONMENT
# rather than CONTENT, which is precisely what teaches an operator to skim
# reds (`check_gates` paid for this lesson with pytest).
# ⚠️ THE ASSERTIONS BELOW READ `config.ORB_RISK_USD` / `config.ORB_BUDGET_USD`
# RATHER THAN THESE LITERALS, so the fixture can be re-declared without
# rewriting a single check. What is pinned is the SHAPE of the ramp between
# whatever two ends are set — never the operator's particular dollars, which
# are his to change from `configure.sh` and are not this file's business.
os.environ.setdefault("OT_RISK_USD", "1050")
os.environ.setdefault("OT_ORB_BUDGET_USD", "10000")

FAIL: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])


# ── R0 — THE GUARD, NOT A CHECK (the r72/V0 pattern) ──────────────────────
# At a base without r91 the machinery below does not exist, and this file would
# die on an AttributeError naming nothing. A gate that cannot say WHAT is
# missing teaches the reader to skim the red (§36).
from strategy.base_strategy import OptionsSignal            # noqa: E402

_missing = [n for n in ("structural_stop_premium", "sizes_on_structure")
            if not hasattr(OptionsSignal, n)]
check("R0 OptionsSignal exposes the structural-stop machinery",
      not _missing, f"missing={_missing} — r91 has not landed in this tree")
if _missing:
    print(f"\nRED — {len(FAIL)} failed: {FAIL}")
    sys.exit(1)

import config                                               # noqa: E402
from risk.risk_manager import get_risk_manager              # noqa: E402

RM = get_risk_manager()
WIDTH = 1.02            # the real 2026-09-21 opening range


def _sig(dist, delta, prem, strategy="ORBStrategy", breakout=False):
    s = OptionsSignal(strategy_name=strategy, underlying_entry=733.0,
                      underlying_stop=733.0 - dist, entry_delta=delta,
                      entry_premium=prem)
    if breakout:
        s.sizes_on_geometry = True
    return s


def _size(dist, delta, prem, **kw):
    s = _sig(dist, delta, prem, **kw)
    return s, RM.size_for("long_debit", premium=prem,
                          stop_premium=s.stop_premium(), grade="UNGRADED",
                          orb_width=WIDTH, orb_stop_distance=dist)


# ── R1 — THE STOP IS STRUCTURAL, NOT A PERCENTAGE ─────────────────────────
# 🔑 The whole revision in one assertion. `premium - stop_premium` must equal
# `distance x delta`, which is what makes `_size_geometry`'s existing
# arithmetic the operator's 1-R without a new argument.
s, _ = _size(0.42, 0.345, 0.73)
_implied = (0.73 - s.stop_premium()) * 100.0
_want = 0.42 * 0.345 * 100.0
check("R1 premium - stop_premium IS distance x delta (r44's premise, made true)",
      abs(_implied - _want) < 1e-6, f"${_implied:.4f} vs ${_want:.4f}")

# ⚠️ AND IT MUST NOT BE THE FLAT PERCENTAGE. A structural stop that happens to
# equal `entry x 0.75` would satisfy R1 by coincidence on one row.
check("R1b and it is NOT entry x (1 - stop_loss_pct)",
      abs(s.stop_premium() - 0.73 * (1 - s.stop_loss_pct)) > 1e-6,
      f"structural={s.stop_premium():.4f} flat={0.73 * 0.75:.4f}")

# ── R2 — THE RAMP, AND THIS IS THE ONE THAT WAS FLAT ──────────────────────
# 🔴 MEASURED ON THE LIVE TAPE, 2026-09-21 10:13-10:18 ET: 21 consecutive
# Breakout fires, structural stop wandering 0.07 -> 0.70 (10x), geometry_wanted
# 1 -> 59, and deployed capital never leaving $4,080-$4,209. THAT is what a
# flattened ramp looks like in production, and nothing went red.
_rows = [(d, _size(d, 0.40, 0.80)[1]) for d in (0.07, 0.17, 0.42, 0.70, 1.50, 2.00)]
_dep = [r.total_cost for _, r in _rows]
# ⚠️ NON-INCREASING, NOT STRICTLY FALLING, AND THE DIFFERENCE IS THE CEILING.
# My first cut asserted `a > b` across every pair and went red on a CORRECT
# ramp: the two tightest stops BOTH clamp to the ORB budget, so the top of the
# ramp is legitimately flat at $10,000 -> $10,000. A check that fails on the
# budget doing its job is a check that would be loosened in a week (§20).
check("R2 deployed capital never RISES as the impulsive stop deepens",
      all(a >= b for a, b in zip(_dep, _dep[1:])),
      " -> ".join(f"${x:.0f}" for x in _dep))
# 🔑 AND WHERE THE CEILING IS NOT BINDING IT MUST STRICTLY FALL — otherwise
# "non-increasing" is satisfied by the flat defect this revision removes.
_free = [d for d, r in zip(_dep, [r for _, r in _rows])
         if d < config.ORB_BUDGET_USD * 0.95]
check("R2a ...and STRICTLY falls wherever the budget is not binding",
      len(_free) >= 3 and all(a > b for a, b in zip(_free, _free[1:])),
      " -> ".join(f"${x:.0f}" for x in _free))

# ⚠️ MONOTONE IS NOT ENOUGH — A 2% DRIFT IS MONOTONE. The defect this replaces
# produced $4,080-$4,209 across a 10x swing, which passes any ordering test.
# The ramp must actually SPAN its two declared ends.
check("R2b and the ramp SPANS, rather than drifting",
      _dep[0] > _dep[-1] * 4.0,
      f"top ${_dep[0]:.0f} vs start ${_dep[-1]:.0f} — the flat defect was 4080-4209")

# ── R3 — THE TWO ENDS ARE THE OPERATOR'S TWO CONSTANTS ────────────────────
_, r_tight = _size(0.07, 0.456, 0.99)
check("R3 a tight impulsive candle runs the position to the ORB budget (ramp TOP)",
      r_tight.total_cost > config.ORB_BUDGET_USD * 0.95
      and r_tight.total_cost <= config.ORB_BUDGET_USD,
      f"${r_tight.total_cost:.0f} against a ${config.ORB_BUDGET_USD:.0f} ceiling")

_, r_deep = _size(2.00, 0.400, 0.80)
check("R3b a deep one comes back to the ramp START and stops there",
      abs(r_deep.total_cost - config.ORB_RISK_USD) < config.ORB_RISK_USD * 0.10,
      f"${r_deep.total_cost:.0f} against a ${config.ORB_RISK_USD:.0f} start")

# ── R4 — RISK LANDS ON THE DECLARED NUMBER WHERE RISK BINDS ───────────────
# 🔑 r44's own measurement is the thing being repaired: on a 0.97 range every
# stop from 0.54 to 0.01 risked $26-$32 — 3% of the budget. The operator:
# *"I DO NOT want $30 ORB TRADES."*
for _d, _dl, _p in ((0.42, 0.345, 0.73), (0.70, 0.405, 1.04), (1.50, 0.400, 0.80)):
    _sg, _r = _size(_d, _dl, _p)
    _risk = _r.contracts * (_p - _sg.stop_premium()) * 100.0
    check(f"R4 dist {_d}: risk at the structure stop is the declared start",
          abs(_risk - config.ORB_RISK_USD) < config.ORB_RISK_USD * 0.10,
          f"${_risk:.0f} vs ${config.ORB_RISK_USD:.0f}")

# ── R5 — A STOP BEYOND THE OPTION'S VALUE IS TOTAL LOSS, NOT A FALLBACK ───
# 🔴 MY OWN FIRST CUT FAILED THIS AND IT IS RECORDED RATHER THAN TIDIED.
# Returning None when `distance x delta >= premium` fell back to the flat 25%
# and sized 52 contracts calling it $1,040 at risk, when reaching that stop
# costs the full $4,160 — a 4x UNDERSTATEMENT, and the exact inversion of the
# operator's rule (largest size at the widest stop).
_s_far = _sig(2.00, 0.400, 0.80)
check("R5 a stop past the option's value prices as TOTAL LOSS",
      _s_far.stop_premium() <= 0.01 + 1e-9,
      f"stop_premium={_s_far.stop_premium():.4f} — the flat fallback would be "
      f"{0.80 * 0.75:.4f}")

# ⚠️ ONE TICK, NEVER ZERO. `exit_engine` reads
# `record.get("stop_premium", 0.0) or entry * (1 - MAX_LOSS_PCT)` in TWO
# places, so a 0.0 stop is FALSY and silently restores the percentage stop
# this revision removes (§23 — fix the readers, not just the writer).
check("R5b and it is TRUTHY, so the exit engine's `or` fallback cannot fire",
      bool(_s_far.stop_premium()), f"{_s_far.stop_premium()!r}")

# ── R6 — A WIDE STOP IS NOT DEGENERATE; ZERO STILL IS ─────────────────────
# The "$30 ORB trade" had a second source: `distance > width` forced ONE
# CONTRACT regardless of the risk budget. Measured before the fix at distance
# 2.00 on a 1.02 range: 1 contract, $80 deployed.
_, r_wide = _size(2.00, 0.400, 0.80)
check("R6 a stop wider than the range sizes on RISK, not a forced 1-lot",
      r_wide.contracts > 1 and r_wide.total_cost > config.ORB_RISK_USD * 0.9,
      f"{r_wide.contracts} contract(s) = ${r_wide.total_cost:.0f}")

_s0 = _sig(0.0, 0.400, 0.80)
_r0 = RM.size_for("long_debit", premium=0.80, stop_premium=_s0.stop_premium(),
                  grade="UNGRADED", orb_width=WIDTH, orb_stop_distance=0.0)
check("R6b entry == stop is STILL degenerate and still sizes 1",
      _r0.contracts == 1, f"{_r0.contracts} contract(s)")

# ── R7 — PARITY: BREAKOUT IS THE ORB WITHOUT THE RETEST ───────────────────
# 🔑 The operator's whole reason for the A/B, 2026-09-22: *"The purpose of the
# breakout was to compare the two to see if it was better to chase breakouts or
# wait for a retest. But if breakout gets a larger budget almost every time
# it's not a fair test."* Two strategies, identical inputs, identical answer.
_ob, r_orb = _size(0.42, 0.345, 0.73)
_bk, r_bko = _size(0.42, 0.345, 0.73, strategy="Breakout", breakout=True)
check("R7 ORB and Breakout size IDENTICALLY on identical geometry",
      r_orb.contracts == r_bko.contracts,
      f"ORB {r_orb.contracts} vs Breakout {r_bko.contracts}")
check("R7b ...and resolve the same structural stop",
      abs(_ob.stop_premium() - _bk.stop_premium()) < 1e-9,
      f"{_ob.stop_premium():.4f} vs {_bk.stop_premium():.4f}")
check("R7c ...and the same stop_loss_pct / tp_pct",
      (_ob.stop_loss_pct, _ob.tp_pct) == (_bk.stop_loss_pct, _bk.tp_pct),
      f"{(_ob.stop_loss_pct, _ob.tp_pct)} vs {(_bk.stop_loss_pct, _bk.tp_pct)}")

# ── R8 — THE TRAIL ARMS FROM ENTRY AND IS FLOORED ON THE STRUCTURE ────────
# Operator: *"Put a 25% trailing stop on it that follows the move. If it
# doesn't move the structure stop will catch it and if it does move the 25%
# trailing stop will lock it in."* And: *"I want it from the start."*
from execution.exit_engine import (ExitEngine, _is_structure_trail,   # noqa: E402
                                   STRUCTURE_TRAIL_STRATEGIES)

check("R8 the trail arms at ENTRY, not at +50%",
      abs(_ob.trail_activation_premium() - _ob.entry_premium) < 1e-9,
      f"arms at {_ob.trail_activation_premium():.4f}, entry {_ob.entry_premium:.4f}")

_e = ExitEngine.__new__(ExitEngine)
_e._trail_active, _e._trail_stops = {}, {}
_floor = _ob.stop_premium()
_seq = [0.73, 0.66, 0.80, 1.50, 2.40, 2.00, 1.79]
_trails = []
for _c in _seq:
    _t = _e._update_trail("t", _c, 0.73, _ob.trail_activation_premium(),
                          _floor, structure_trail=True)
    _trails.append(_e._trail_stops.get("t", _t))

check("R8b while it does not move, the STRUCTURE stop governs",
      _trails[1] is not None and abs(_trails[1] - _floor) < 1e-9,
      f"at 0.66 the trail is {_trails[1]}, floor {_floor:.4f}")
check("R8c the trail NEVER sits below the structure floor (r44's 10-of-210)",
      all(t is None or t >= _floor - 1e-9 for t in _trails),
      f"min={min(t for t in _trails if t is not None):.4f} floor={_floor:.4f}")
check("R8d it RATCHETS — a pullback from the peak does not lower it",
      _trails[5] is not None and abs(_trails[5] - _trails[4]) < 1e-9,
      f"peak trail {_trails[4]:.4f} -> pullback {_trails[5]:.4f}")
check("R8e and 25% behind the peak is what it locks",
      abs(_trails[4] - 2.40 * 0.75) < 1e-9,
      f"{_trails[4]:.4f} vs {2.40 * 0.75:.4f}")

# ── R9 — THE NAME LIST CANNOT SILENTLY MISS A STRATEGY ────────────────────
# ⚠️ §23: the v3 cutoff held a name list, two of its three entries were
# deleted, and a new long-debit strategy was silently EXEMPT. A name list rots
# PERMISSIVELY. This pins the trail's list against the strategies that actually
# declare structural sizing, so the next one cannot be added to one and not the
# other.
check("R9 every structure-sized strategy is in STRUCTURE_TRAIL_STRATEGIES",
      _ob.sizes_on_structure() and _bk.sizes_on_structure()
      and _is_structure_trail({"strategy": "ORBStrategy"})
      and _is_structure_trail({"strategy": "Breakout"}),
      f"set={STRUCTURE_TRAIL_STRATEGIES}")

# ── R10 — BLAST RADIUS: EVERY OTHER STRATEGY IS UNTOUCHED ─────────────────
# 🔑 r44 replaced `current * 0.75` for a MEASURED reason — 10 of 210
# trail-exited fleet trades finished NEGATIVE with the trail armed. That
# protection must still cover everyone who is not structure-floored.
check("R10 a non-structure strategy still uses the r44 gain floor",
      not _is_structure_trail({"strategy": "VOLT"})
      and not _is_structure_trail({"strategy": "SweepCreditSpread"}),
      "VOLT / SweepCreditSpread must not be structure-trailed")

_v = OptionsSignal(strategy_name="VOLT", underlying_entry=733.0,
                   underlying_stop=732.5, entry_delta=0.40, entry_premium=1.00)
check("R10b ...and its stop is still the flat percentage",
      abs(_v.stop_premium() - 1.00 * (1 - _v.stop_loss_pct)) < 1e-9,
      f"{_v.stop_premium():.4f}")
check("R10c ...and its trail still arms at +50%",
      abs(_v.trail_activation_premium() - 1.00 * (1 + _v.tp_pct * 0.5)) < 1e-9,
      f"arms at {_v.trail_activation_premium():.4f}")

# ── N — THE NOISE FLOOR (r93) ─────────────────────────────────────────────
# 🔴 THE INVERSION IT CLOSES. The 1-R rule normalises the SIZE of a loss and
# is blind to its FREQUENCY: as the stop tightens, size rises AND so does the
# chance of being hit. Stop -> 0 means size -> budget cap and P(hit) -> 1, so
# expected loss converges on the whole risk budget with certainty.
# 📊 MEASURED LIVE 2026-09-22 10:14-10:25 ET: five Breakouts whose structural
# stop sat inside ONE 1-minute bar (0.075 / 0.050 / 0.190 / 0.225 / 0.010
# against a measured median 1m range of 0.4188) at 55-235 contracts and about
# $10,000 each, for -$3,089.
# ⚠️ THE FIXTURE IS TODAY'S MEASURED TAPE, not a number chosen to pass.
_BAR, _MULT = 0.4188, config.NOISE_FLOOR_BAR_MULT
_NF = _BAR * _MULT

_r_in = RM.size_for("long_debit", premium=0.56, stop_premium=0.42,
                    grade="UNGRADED", orb_width=WIDTH, orb_stop_distance=0.050,
                    noise_floor=_NF)
check("N1 a stop INSIDE the floor is REFUSED",
      (not _r_in.allowed) and _r_in.contracts == 0,
      f"allowed={_r_in.allowed} n={_r_in.contracts}")
check("N1b ...and the refusal NAMES the floor, never a bare no",
      "noise_floor" in (_r_in.reject_reason or ""), repr(_r_in.reject_reason))

_r_out = RM.size_for("long_debit", premium=1.21, stop_premium=1.094,
                     grade="UNGRADED", orb_width=WIDTH, orb_stop_distance=0.340,
                     noise_floor=_NF)
check("N2 a stop OUTSIDE the floor still trades",
      _r_out.allowed and _r_out.contracts > 1,
      f"allowed={_r_out.allowed} n={_r_out.contracts}")

# ⚠️ THE BOUNDARY IS HALF A BAR AND IT IS CHECKED, because "inside one bar"
# and "inside half a bar" are different rules and only one was ruled.
_edge = RM.size_for("long_debit", premium=1.00, stop_premium=0.90,
                    grade="UNGRADED", orb_width=WIDTH,
                    orb_stop_distance=_NF * 1.01, noise_floor=_NF)
check("N2b a stop just ABOVE the floor is admitted (the boundary is real)",
      _edge.allowed, f"allowed={_edge.allowed} at {_NF * 1.01:.4f} vs {_NF:.4f}")

# 🔴 N3 — UNMEASURABLE MUST STAND DOWN, NOT REFUSE EVERYTHING. A feed hiccup
# that blocked every entry would be a worse failure than the one being closed.
_r_nf0 = RM.size_for("long_debit", premium=0.56, stop_premium=0.42,
                     grade="UNGRADED", orb_width=WIDTH, orb_stop_distance=0.050,
                     noise_floor=0.0)
check("N3 floor 0.0 (unmeasurable) DISARMS the gate — pre-r93 behaviour",
      _r_nf0.allowed, f"allowed={_r_nf0.allowed} n={_r_nf0.contracts}")

# ⚠️ N4 — THE DEGENERATE CASE IS STILL THE DEGENERATE CASE. distance <= 0 is
# an arithmetic fault, not a tight stop, and must not be swallowed by the new
# gate's refusal path with a misleading reason.
_r_zero = RM.size_for("long_debit", premium=0.56, stop_premium=0.42,
                      grade="UNGRADED", orb_width=WIDTH, orb_stop_distance=0.0,
                      noise_floor=_NF)
check("N4 distance <= 0 is still degenerate, not a noise-floor refusal",
      _r_zero.allowed and _r_zero.contracts == 1,
      f"allowed={_r_zero.allowed} n={_r_zero.contracts} why={_r_zero.reject_reason!r}")

# 🔑 N5 — THE MULTIPLIER IS ARGUED, NOT FITTED, AND THIS PINS THAT. The
# P&L-optimal value on 2026-09-22 was 0.60x; 0.5x is the mechanism's own
# number (price must travel back to the candle's extreme, and below half a
# typical bar one ordinary bar does it). Eleven closed trades cannot choose a
# threshold (§12), and a checker that drifted to the fitted value would be
# exactly the curve-fit `PREREG_TRAIL.md` exists to prevent.
check("N5 the floor multiplier is the ARGUED 0.5x, not the day's best fit",
      abs(config.NOISE_FLOOR_BAR_MULT - 0.5) < 1e-9,
      f"{config.NOISE_FLOOR_BAR_MULT} (2026-09-22 P&L peak was 0.60x)")

if FAIL:
    print(f"\nRED — {len(FAIL)} failed: {', '.join(FAIL)}")
    sys.exit(1)
print(f"\nGREEN — the ramp spans "
      f"${_dep[-1]:.0f} to ${_dep[0]:.0f}, risk on ${config.ORB_RISK_USD:.0f}")
sys.exit(0)
