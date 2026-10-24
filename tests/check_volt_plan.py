#!/usr/bin/env python3
"""
tests/check_volt_plan.py  v1.8
v1.8  2026-10-02  OTV4TEST r187 (ROSTER.1) — RE-POINTED BY THE RULING, NOT LOOSENED:
      the strategy is OFF by default from r187; this checker tests its LOGIC,
      so it switches it on for its own run (OT_VOLT=1). check_trade_switches pins the default.
      V1 RE-POINTED to the 09:35-10:30 window (the operator's 10:29 debit cutoff) and V1b to
      'identical to Breakout/Runaway/Hunt': the ORB TRADE is retired and its row is deliberately
      left unchanged (it drives the ORB engine's expiry), so r72's 'identical to the ORB' no
      longer names the trades VOLT controls for.
v1.7  2026-10-02  OTV4TEST r186 (ZBID.1) — the _C
      fixture contract now carries a TWO-SIDED quote (bid/ask around its
      mark), as every live OptionContract does: r186 (ZBID.1) refuses a
      contract with no bid, and this fixture had none. No check changed.
v1.6  2026-09-26  OTV4TEST r149 (EOD.1) — V1 and V3 RE-POINTED: VOLT keeps the ORB's window (V1b, r72's
      control property), and the ORB's window is now 09:35-15:40 by the operator's "extend the debit
      window to all day" / "Stop entries at 1540". V1 pins 09:35-15:40 at both edges; V3's "outside"
      tick is one minute past 15:40.

v1.5  2026-09-21  OTV4TEST r82 — V19c and V19e RE-POINTED, not deleted
      (r33/r43/r64). Both asserted the extrinsic proxy; measurement killed it
      (zero at delta 0.82), so they now pin the opposite with the evidence.
v1.4  2026-09-21  OTV4TEST r80 — V19e/V19f: the two instruments are
      COMPLEMENTARY. Born red 1 of 33 at 8f0e2c1 on V19e, driving the EXACT
      live state r79 failed to exit.
v1.3  2026-09-21  OTV4TEST r79 — V19/V19b/V19c/V19d: PAR DELTA IS AN EXIT.
      Born red 2 of 31 at cd8d775 on V19 and V19c. V19b and V19d are the
      CONTROLS and are green on BOTH sides by design — a rung that exited
      everything would pass V19 alone and silently delete the strategy.
v1.2  2026-09-21  OTV4TEST r75 — V18/V18b: the exit bar must POSTDATE the
      entry. Found LIVE, not in review.
v1.1  2026-09-21  OTV4TEST r74 — V17/V17b/V17c: it must be able to fire from
      the OPEN. Fixtures rebuilt on the 1-minute frame.
v1.0  2026-09-21  OTV4TEST r72 (CTRL.1) — born RED at 7e8a19c, where the VOLT
      modules do not exist and V0's guard refuses to continue. 25 checks.

r72 — VOLT, THE CONTROL ARM. Born RED at 7e8a19c (r71), where the modules do
not exist and V0 refuses to continue.

🔑 WHAT THIS GATE IS REALLY PROTECTING. VOLT's entire value is that it gates on
TWO things. A third gate does not make it a better strategy — it destroys the
measurement the strategy exists to produce. V9 pins the gate COUNT for exactly
that reason: the failure mode here is not a bug, it is a well-meaning addition.

Drives the REAL plan, the REAL admission table and the REAL exit engine against
fixtures (WA §21 — a test that reads source text proves nothing about runtime).

  V0  the modules import and VOLT is registered
  V1  window 09:35-15:40 (r149), half-open at BOTH edges, driven through decide()
  V2  it blocks nothing and is blocked by nothing — the control property
  V3  outside the window the plan is DORMANT and prepares nothing
  V4  the volume gate REFUSES below the prior and PASSES at/above it
  V5  direction is close vs the SESSION OPEN, driven BOTH ways
  V6  the stop is the structural extreme of the last N 5m bars
  V7  the trail arms at exactly ARM_R x R and its floor is NEVER below entry
  V8  the exit engine routes VOLT to its OWN evaluator, not the ORB's
  V9  SCOPE: exactly two gates refuse an otherwise-valid setup

Run:  python3 tests/check_volt_plan.py
"""

from __future__ import annotations
import os as _os_r187
_os_r187.environ["OT_VOLT"] = "1"   # r187: test the strategy's logic switched on
import os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAIL: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])

_imp_err = ""
try:
    import pandas as pd
    import config
    from strategy.volt_plan import (VoltPlan, VOL_MULT, VOL_LOOKBACK_BARS,
                                    MIN_BARS, TRAIL_ARM_R, TRAIL_LOCK_FRAC)
    from strategy.volt_strategy import VoltStrategy
    from execution.position_manager import rules, decide, Facts, VOLT, ORB
    _ok_imports = True
except Exception as exc:                                   # noqa: BLE001
    _imp_err = f"{type(exc).__name__}: {exc}"
    _ok_imports = False

check("V0 VOLT modules import and the strategy is registered", _ok_imports, _imp_err)
if not _ok_imports:
    print(f"\nFAIL: {len(FAIL)} problem(s) {FAIL}")
    sys.exit(1)

T = rules()
check("V0b VOLT is in the admission table", VOLT in T, f"keys={sorted(T)}")

# ── V1 — the window, at both edges, through the REAL decide() ───────────────
def admits(hhmm, **kw):
    return bool(decide(Facts(strategy=VOLT, now_et=hhmm, orb_established=True, **kw)))
w = T[VOLT].window
check("V1 window is 09:35-10:30, half-open at BOTH edges (r187: the 10:29 debit cutoff)",
      w == ((9, 35), (10, 30)) and not admits((9, 34)) and admits((9, 35))
      and admits((10, 29)) and not admits((10, 30)),
      f"window={w} 09:34={admits((9,34))} 09:35={admits((9,35))} "
      f"10:29={admits((10,29))} 10:30={admits((10,30))}")
check("V1b VOLT's window is IDENTICAL to the directional debits it controls for (r187: Breakout, Runaway, Hunt)",
      T[VOLT].window == T["Breakout"].window == T["RunawayContinuation"].window == T["LiquidityHunt"].window,
      f"volt={T[VOLT].window} brk={T['Breakout'].window}")

# ── V2 — the control property: non-competing ───────────────────────────────
blocks = set(getattr(T[VOLT], "blocks", ()) or ())
blocked = set(getattr(T[VOLT], "blocked_by", ()) or ())
check("V2 VOLT blocks nothing and is blocked by nothing",
      not blocks and not blocked, f"blocks={sorted(blocks)} blocked_by={sorted(blocked)}")
check("V2b VOLT still admits with an ORB already open (non-competing)",
      admits((10, 0), open_by_strategy={ORB: 1}), "an open ORB must not exclude the control")

# ── fixtures ───────────────────────────────────────────────────────────────
class _C:
    def __init__(self, strike, mark=1.00, delta=0.5, gamma=0.01):
        self.strike, self.mark, self.delta, self.gamma = strike, mark, delta, gamma
        self.bid, self.ask = max(0.01, mark - 0.02), mark + 0.02   # r186: two-sided
        self.expiry = "2026-09-21"
class _Chain:
    def __init__(self, spot):
        # integer strikes straddling spot, so a nearest-OTM exists either way
        self.calls = [_C(float(int(spot) + i)) for i in (-2, -1, 0, 1, 2)]
        self.puts  = [_C(float(int(spot) + i)) for i in (-2, -1, 0, 1, 2)]

def frame(bars_1m, session_open=100.0):
    """bars_1m: list of (close, volume) — ONE ROW PER MINUTE, because r74 moved
    the gate to the 1-minute frame so VOLT can fire from the open."""
    rows, idx = [], []
    t0 = dt.datetime(2026, 9, 21, 9, 30)
    for bi, (close, vol) in enumerate(bars_1m):
        ts = t0 + dt.timedelta(minutes=bi)
        o = session_open if bi == 0 else close
        rows.append({"open": o, "high": max(o, close) + 0.05,
                     "low": min(o, close) - 0.05, "close": close, "volume": vol})
        idx.append(ts)
    return pd.DataFrame(rows, index=pd.DatetimeIndex(idx))

NEED = VOL_LOOKBACK_BARS + 2
def bars(last_close, last_vol, base_close=100.0, base_vol=1000.0, session_open=100.0):
    b = [(base_close, base_vol)] * NEED
    return b + [(last_close, last_vol), (last_close, last_vol)]   # +forming

plan = VoltPlan()
def prep(last_close, last_vol, now="10:00", session_open=100.0, spot=None):
    df = frame(bars(last_close, last_vol, session_open=session_open), session_open)
    px = spot if spot is not None else last_close
    return plan.prepare(chain=_Chain(px), price_now=px, df_1m=df, now_hhmm=now)

# ── V3 — dormant outside the window ────────────────────────────────────────
p_out = prep(101.0, 5000.0, now="15:41")   # r149: past 15:40
check("V3 outside the window the plan prepares NOTHING",
      not p_out.ready and p_out.contract is None,
      f"ready={p_out.ready}")

# ── V4 — the volume gate, both sides of the prior ──────────────────────────
lo = prep(101.0, 1000.0 * (VOL_MULT - 0.15))
hi = prep(101.0, 1000.0 * (VOL_MULT + 0.50))
check("V4 volume BELOW the prior refuses", not lo.ready,
      f"ratio={lo.vol_ratio} mult={VOL_MULT}")
check("V4b volume ABOVE the prior prepares a trade", hi.ready and hi.contract is not None,
      f"ratio={hi.vol_ratio} ready={hi.ready}")

# ── V5 — direction is close vs the SESSION OPEN, both ways ─────────────────
up   = prep(101.0, 5000.0, session_open=100.0)
down = prep( 99.0, 5000.0, session_open=100.0)
check("V5 close ABOVE the session open -> long/call",
      up.direction == "long" and up.side == "call", f"{up.direction}/{up.side}")
check("V5b close BELOW the session open -> short/put",
      down.direction == "short" and down.side == "put", f"{down.direction}/{down.side}")

# ── V6 — the structure stop is the N-bar extreme ───────────────────────────
# ⚠️ RE-POINTED at r72's ruling, not loosened (r33/r43/r64). The operator,
# 2026-09-21: *"Use a structural stop. A close beyond where the trade opened is
# a dead thesis."* The stop IS the entry. The two designs this replaced — a
# 3-bar structural extreme and the signal bar's own extreme — both allowed the
# stop to land AT the entry when structure was tight, so risk -> 0 and R
# exploded (measured worst -120R and -749R over 19 sessions x 4 symbols).
check("V6 the stop IS the entry — a close back through it is the dead thesis",
      up.stop is not None and abs(up.stop - up.price) < 1e-9,
      f"stop={up.stop} price={up.price}")
check("V6b R comes from the SIGNAL BAR's range, not from the stop distance",
      up.risk_px is not None and up.risk_px > 0,
      f"R={up.risk_px} (the stop supplies no distance, so the trail needs another scale)")

# ── V7 — the trail arms on DISTANCE and can never floor below entry ────────
entry = 100.0
risk = up.risk_px          # the signal bar's range, which is what the trail scales on
armed_at = entry + TRAIL_ARM_R * risk
check("V7 trail arm price is exactly ARM_R x R above entry",
      abs((up.trail_arm_px - up.price) - TRAIL_ARM_R * up.risk_px) < 1e-9,
      f"arm={up.trail_arm_px} price={up.price} R={up.risk_px} ARM_R={TRAIL_ARM_R}")
floors = [entry + TRAIL_LOCK_FRAC * (pk - entry) for pk in (armed_at, entry + 5 * risk)]
check("V7b the trail floor is NEVER below entry (r44's scar)",
      all(fl >= entry for fl in floors), f"floors={[round(f,4) for f in floors]}")

# ── V8 — the exit engine routes VOLT to its OWN evaluator ──────────────────
import execution.exit_engine as EE
seen = {}
class _Spy(EE.ExitEngine):
    def _evaluate_volt(self, record, current_premium, df_1m, df_5m=None):
        seen["volt"] = True
        return EE.ExitDecision()
    def _evaluate_orb(self, record, current_premium, df_1m, df_5m=None):
        seen["orb"] = True
        return EE.ExitDecision()
rec = {"trade_id": "VOLT0001", "strategy": "VOLT", "direction": "long",
       "entry_premium": 1.00, "contracts": 1, "underlying_entry": 100.0,
       "underlying_stop": 99.0, "stop_premium": 0.75, "trail_activation": 1.5}
try:
    _Spy().evaluate(rec, 1.00, df_1m=None, df_5m=None)
except Exception as exc:                                   # noqa: BLE001
    seen["err"] = f"{type(exc).__name__}: {exc}"
check("V8 a VOLT record routes to _evaluate_volt, NOT the ORB evaluator",
      seen.get("volt") and not seen.get("orb"), f"{seen}")

# ── V9 — SCOPE: exactly two gates ──────────────────────────────────────────
gates = set()
if not prep(101.0, 1000.0 * (VOL_MULT - 0.15)).ready: gates.add("volume")
# direction never REFUSES — it only picks a side; it is a gate in the sense
# that it decides WHAT is traded. Both sides must produce a trade.
if up.ready and down.ready: gates.add("direction")
check("V9 SCOPE: two gates and only two — volume refuses, direction selects",
      gates == {"volume", "direction"},
      f"{sorted(gates)}; a THIRD gate belongs in a NEW strategy, not in the control")

# ── V10 — the STRATEGY (not just the plan) builds a usable signal ──────────
# drives VoltStrategy.generate_signal end to end, because a plan that prepares
# and a strategy that never fires is the r51 class of defect.
_sig = VoltStrategy().generate_signal(
    chain=_Chain(101.0), price_now=101.0,
    df_1m=frame(bars(101.0, 1000.0 * (VOL_MULT + 0.50), session_open=100.0), 100.0),
    now_et="10:00")
check("V10 VoltStrategy builds a signal whose stop IS the entry (r72 ruling)",
      _sig is not None and _sig.strategy_name == "VOLT"
      and _sig.direction == "long" and _sig.option_side == "call"
      and _sig.underlying_stop > 0
      and abs(_sig.underlying_stop - _sig.underlying_entry) < 1e-9
      and bool(getattr(_sig, "underlying_stop_is_thesis", False)),
      f"sig={None if _sig is None else (_sig.strategy_name, _sig.direction, _sig.underlying_stop)}")
_sig_lo = VoltStrategy().generate_signal(
    chain=_Chain(101.0), price_now=101.0,
    df_1m=frame(bars(101.0, 1000.0 * (VOL_MULT - 0.15), session_open=100.0), 100.0),
    now_et="10:00")
check("V10b below the volume prior the STRATEGY returns None", _sig_lo is None, f"{_sig_lo}")
# ── V11 — the priors live in config, once ─────────────────────────────────
check("V11 every VOLT prior is declared in config (one source, not two)",
      all(hasattr(config, k) for k in
          ("VOLT_VOL_MULT", "VOLT_VOL_LOOKBACK_BARS",
           "VOLT_TRAIL_ARM_R", "VOLT_TRAIL_LOCK_FRAC"))
      and config.VOLT_VOL_MULT == VOL_MULT and config.VOLT_TRAIL_ARM_R == TRAIL_ARM_R,
      "volt_plan and exit_engine must not carry separate defaults")

# ── V12 — the r61 opt-out is LOAD-BEARING now, not incidental ──────────────
# r61's entry-underwater guard is STRICT ("at or beyond the stop is through")
# and VOLT's stop EQUALS its entry by ruling. Without this declaration the
# guard would refuse EVERY VOLT trade and the control would never fire once.
check("V12 VOLT declares underlying_stop_is_thesis — or r61's strict guard kills every trade",
      _sig is not None and bool(getattr(_sig, "underlying_stop_is_thesis", False))
      and abs(_sig.underlying_stop - _sig.underlying_entry) < 1e-9,
      f"stop={None if _sig is None else _sig.underlying_stop} "
      f"entry={None if _sig is None else _sig.underlying_entry}")

# ── V13 — the trail MUST still arm now that stop == entry ─────────────────
# 🔴 THE RULING BROKE THIS AND THE GATE IS HOW IT WAS CAUGHT. _evaluate_volt
# scaled R on |entry - stop|, which r72 makes ZERO, so the trail would never
# arm and no trade would ever lock a gain — silently, with no error anywhere.
# R now comes from `underlying_target` (= entry + 1R). Driven, not read.
_rec = {"trade_id": "VOLT0002", "strategy": "VOLT", "direction": "long",
        "entry_premium": 1.00, "contracts": 1, "underlying_entry": 100.0,
        "underlying_stop": 100.0, "underlying_target": 101.0, "stop_premium": 0.75}
_df = pd.DataFrame(
    [{"open": 100.0, "high": 100.0, "low": 100.0, "close": c, "volume": 1.0}
     for c in (100.0, 100.9, 100.9)],
    index=pd.DatetimeIndex([dt.datetime(2026, 9, 21, 10, m) for m in (0, 1, 2)]))
# ⚠️ PIN THE CLOCK. `is_hard_close_time()` reads the real wall clock, so this
# check passed or failed depending on the hour it was run — a test whose
# verdict depends on when you run it is not a test (§21's cousin).
_orig_hct = EE.is_hard_close_time
EE.is_hard_close_time = lambda: False
try:
    _d = EE.ExitEngine().evaluate(dict(_rec), 1.20, df_1m=_df, df_5m=_df)
finally:
    EE.is_hard_close_time = _orig_hct
check("V13 the trail ARMS even though the stop equals the entry (on the 5m frame)",
      _d.new_trail_stop is not None and _d.new_trail_stop >= 100.0,
      f"trail={_d.new_trail_stop} (None means it never armed — the r72 ruling's trap)")

# ── V14 — the stop is read on the 5-MINUTE frame, the operator's ruling ───
# Same record, same 1m data, but NO 5m frame: the structure stop must not be
# evaluated off df_1m by accident. Measured: on 1m closes 93% of trades die on
# the stop and the trail almost never arms (win 6.8% vs 18.8% on 5m).
EE.is_hard_close_time = lambda: False
try:
    _d1 = EE.ExitEngine().evaluate(dict(_rec), 1.20, df_1m=_df, df_5m=None)
finally:
    EE.is_hard_close_time = _orig_hct
check("V14 with no 5m frame VOLT does NOT fall back to 1m for the structure stop",
      not _d1.should_exit and _d1.new_trail_stop is None,
      f"exit={_d1.should_exit} reason={_d1.exit_reason!r} — a silent 1m fallback "
      f"would triple the stop-out rate")

# ── V15 — the budget is $1,050, the operator's ruling 2026-09-21 ──────────
# 🔴 IT MUST TRACK RISK_PER_TRADE_USD, **NOT** ORB_BUDGET_USD. Live values
# (configure.sh): OT_RISK_USD=1050, OT_ORB_BUDGET_USD=10000. VOLT uses ONLY the
# budget rule — it does not import the ORB's min(geometry, budget/cost) clamp,
# because that clamp is an ORB prior — so inheriting the $10,000 CEILING sized
# it at ~73 contracts on a $1.36 premium against the handful the ORB takes.
# A control that trades 10-50x the size of the arm it measures produces a P&L
# comparison that means nothing.
check("V15 VOLT's budget tracks RISK_PER_TRADE_USD, not the ORB's ceiling",
      abs(config.VOLT_BUDGET_USD - config.RISK_PER_TRADE_USD) < 1e-9,
      f"volt={config.VOLT_BUDGET_USD} risk_per_trade={config.RISK_PER_TRADE_USD} "
      f"orb_ceiling={config.ORB_BUDGET_USD}")

# ── V16 — the nearest OTM strike, the operator's ruling 2026-09-21 ────────
# long -> strike strictly ABOVE spot; short -> strictly BELOW. Driven both ways
# through the REAL plan, and the chain straddles spot so an ATM pick would be
# available if the rule were wrong.
_up  = prep(101.4, 5000.0, session_open=100.0, spot=101.4)
_dn  = prep( 98.6, 5000.0, session_open=100.0, spot=98.6)
check("V16 a LONG takes the nearest strike ABOVE spot",
      _up.contract is not None and float(_up.contract.strike) > _up.price,
      f"strike={None if _up.contract is None else _up.contract.strike} spot={_up.price}")
check("V16b a SHORT takes the nearest strike BELOW spot",
      _dn.contract is not None and float(_dn.contract.strike) < _dn.price,
      f"strike={None if _dn.contract is None else _dn.contract.strike} spot={_dn.price}")
# and it FAILS CLOSED rather than falling back to ATM
class _OnlyITM:
    def __init__(s, spot):
        s.calls = [_C(float(int(spot) - i)) for i in (1, 2, 3)]   # all below spot
        s.puts  = [_C(float(int(spot) + i)) for i in (1, 2, 3)]   # all above spot
_df_ok = frame(bars(101.4, 1000.0 * (VOL_MULT + 0.50), session_open=100.0), 100.0)
_p_itm = VoltPlan().prepare(chain=_OnlyITM(101.4), price_now=101.4,
                            df_1m=_df_ok, now_hhmm="10:00")
check("V16c with NO OTM strike quoted it refuses rather than falling back to ATM",
      not _p_itm.ready and _p_itm.contract is None,
      f"ready={_p_itm.ready} contract={_p_itm.contract}")

# ── V17 — IT MUST BE ABLE TO FIRE FROM THE OPEN (r74, the operator's spec) ──
# 🔴 r72 GATED ON COMPLETED 5-MINUTE BARS AND DEMANDED EIGHT — 40 minutes of
# session — so a window opening at 09:35 could not fire before 10:15. Measured
# over 18 replayed sessions it NEVER fired in the first 40 minutes. Operator,
# 2026-09-21: *"It should be able to fire immediately. I want to move on the
# first sense that volume is expanding and It needs to jump on."*
# This drives the REAL plan with only MIN_BARS+1 minutes of tape.
_min_df = frame([(100.0, 1000.0)] * MIN_BARS + [(101.0, 1000.0 * (VOL_MULT + 0.5))] * 2,
                session_open=100.0)
_p_min = VoltPlan().prepare(chain=_Chain(101.0), price_now=101.0,
                            df_1m=_min_df, now_hhmm="09:36")
check("V17 fires with only MIN_BARS+1 minutes of tape — no 40-minute warm-up",
      _p_min.ready and _p_min.contract is not None,
      f"ready={_p_min.ready} with {MIN_BARS + 2} one-minute bars "
      f"(r72 needed 8 FIVE-minute bars = 40 minutes)")
check("V17b the warm-up matches the STUDY (3 bars), it does not exceed it",
      MIN_BARS == 3,
      f"MIN_BARS={MIN_BARS}; the study behind the 1.25x threshold used "
      f"mean(vols[max(0,i-6):i]) and required 3")
# and the ENTRY frame is one minute while the EXIT frame stays five
import inspect as _insp
from strategy import volt_plan as _vp
check("V17c the gate reads a ONE-minute frame (entry and exit frames differ)",
      "ts.minute)" in _insp.getsource(_vp._bars_1m)
      and "minute // 5" not in _insp.getsource(_vp._bars_1m),
      "exit_engine._evaluate_volt still reads df_5m — that is the operator's stop ruling")

# ── V18 — THE EXIT BAR MUST POSTDATE THE ENTRY (r75) ──────────────────────
# 🔴 FOUND LIVE, NOT IN A REVIEW. On 2026-09-21 VOLT took SEVEN trades in 90
# seconds, every one stopped in ~14 seconds by "1m close 731.22 below
# structure" — and 731.22 was the 09:45 bar's close, already history when the
# 09:52 trade opened. The stop EQUALS the entry (r72), so a stale completed bar
# on the wrong side kills a trade before it has existed for one tick.
# ⚠️ THE REPLAY HAD THIS GUARD AND THE SHIPPED CODE DID NOT, which is why every
# measurement that authorised the design was blind to it — §21's lesson from
# the other side: a harness that is KINDER than production hides the defect.
_stale_rec = {"trade_id": "VOLT0003", "strategy": "VOLT", "direction": "long",
              "entry_premium": 1.00, "contracts": 1, "underlying_entry": 731.70,
              "underlying_stop": 731.70, "underlying_target": 732.20,
              "stop_premium": 0.75,
              "entry_time": "2026-09-21T13:52:21+00:00"}
# the newest COMPLETED bar closes BELOW the entry but is OLDER than the entry
_stale_df = pd.DataFrame(
    [{"open": 730.8, "high": 731.5, "low": 730.7, "close": 731.22, "volume": 1.0},
     {"open": 731.2, "high": 731.3, "low": 731.0, "close": 731.10, "volume": 1.0},
     {"open": 731.1, "high": 731.2, "low": 731.0, "close": 731.15, "volume": 1.0}],
    index=pd.DatetimeIndex([dt.datetime(2026, 9, 21, 13, 40),
                            dt.datetime(2026, 9, 21, 13, 45),
                            dt.datetime(2026, 9, 21, 13, 50)]))
EE.is_hard_close_time = lambda: False
try:
    _ds = EE.ExitEngine().evaluate(dict(_stale_rec), 1.00, df_1m=_stale_df, df_5m=_stale_df)
finally:
    EE.is_hard_close_time = _orig_hct
check("V18 a completed bar OLDER than the entry does NOT stop the trade",
      not _ds.should_exit,
      f"exit={_ds.should_exit} reason={_ds.exit_reason!r} — the 13:45 close "
      f"predates the 13:52:21 entry; stopping on it is the r75 churn defect")
# and a bar that genuinely postdates the entry still DOES stop it
_fresh_df = _stale_df.copy()
_fresh_df.index = pd.DatetimeIndex([dt.datetime(2026, 9, 21, 13, 55),
                                    dt.datetime(2026, 9, 21, 14, 0),
                                    dt.datetime(2026, 9, 21, 14, 5)])
EE.is_hard_close_time = lambda: False
try:
    _fs = EE.ExitEngine().evaluate(dict(_stale_rec), 1.00, df_1m=_fresh_df, df_5m=_fresh_df)
finally:
    EE.is_hard_close_time = _orig_hct
check("V18b CONTROL: a bar AFTER the entry still stops it — the fix is not a mute",
      _fs.should_exit and "structure_stop" in _fs.exit_reason,
      f"exit={_fs.should_exit} reason={_fs.exit_reason!r}")

# ── V19 — PAR DELTA IS AN EXIT (r79, EXT.1) ───────────────────────────────
# 🔴 THE OPERATOR'S RULING, LIVE, 2026-09-21: *"When Delta reaches PAR, we
# need to get the fuck out."* At par delta the position is stock carrying an
# expiry — no convexity left — so a run-fraction trail costs FULL DOLLARS
# exactly when the trade has already won. Measured on 81b1afae: $4,630 held,
# $2,880 of leash, $45 of theta risk.
# ⚠️ EVERY CASE DRIVES THE REAL `evaluate()`, never the source text (§21), and
# every fixture is deliberately HEALTHY on every other rung — the structure
# stop is far below, the premium floor far under, the trail un-breached — so a
# PASS can only come from rung 2b and not from something else firing.
_par_rec = {"trade_id": "VOLT0079", "strategy": "VOLT", "direction": "long",
            "entry_premium": 1.00, "contracts": 10, "underlying_entry": 733.67,
            "underlying_stop": 733.67, "underlying_target": 733.86,
            "stop_premium": 0.75, "strike": 734.0, "option_side": "call",
            "entry_time": "2026-09-21T14:19:35+00:00"}
_par_df = pd.DataFrame(
    [{"open": 738.9, "high": 739.8, "low": 738.8, "close": 739.60, "volume": 1.0},
     {"open": 739.6, "high": 739.9, "low": 739.4, "close": 739.70, "volume": 1.0},
     {"open": 739.7, "high": 739.8, "low": 739.5, "close": 739.59, "volume": 1.0}],
    index=pd.DatetimeIndex([dt.datetime(2026, 9, 21, 17, 40),
                            dt.datetime(2026, 9, 21, 17, 45),
                            dt.datetime(2026, 9, 21, 17, 50)]))
def _drive_on(frame, rec, prem):
    EE.is_hard_close_time = lambda: False
    try:
        return EE.ExitEngine().evaluate(dict(rec), prem, df_1m=frame, df_5m=frame)
    finally:
        EE.is_hard_close_time = _orig_hct

def _drive(rec, prem):
    EE.is_hard_close_time = lambda: False
    try:
        return EE.ExitEngine().evaluate(dict(rec), prem, df_1m=_par_df, df_5m=_par_df)
    finally:
        EE.is_hard_close_time = _orig_hct

_d1 = _drive({**_par_rec, "current_delta": 0.983}, 5.63)
check("V19 delta AT PAR exits — the operator's ruling, driven through evaluate()",
      _d1.should_exit and "volt_delta_par" in (_d1.exit_reason or ""),
      f"exit={_d1.should_exit} reason={_d1.exit_reason!r}")

# 🔑 THE CONTROL, AND IT IS THE HALF THAT KEEPS THE RULE HONEST: a healthy
# position BELOW par must be UNTOUCHED. A rung that exited everything would
# look identical on V19 alone and would silently delete the strategy.
_atm_df = _par_df.copy()
_atm_df["close"] = [734.4, 734.6, 734.50]          # near the 734 strike
_d2 = _drive_on(_atm_df, {**_par_rec, "current_delta": 0.55}, 2.10)
check("V19b CONTROL: below par the trade is HELD — the rung is not a guillotine",
      not _d2.should_exit,
      f"exit={_d2.should_exit} reason={_d2.exit_reason!r}")

# ⚠️ RE-POINTED AT r82, NOT DELETED (r33/r43/r64). r79 asserted that a missing
# delta must fall back to extrinsic, on the belief that delta->1 and
# extrinsic->0 are one condition. THAT BELIEF IS SUPERSEDED BY MEASUREMENT:
# over 81b1afae's whole life, extrinsic-from-mid reached ZERO AT DELTA 0.82
# (11:39 ET, mark 3.11), because an ITM 0DTE bid sits at parity. The proxy
# fires two hours early and would have cost $2,500 on that trade. With no
# delta the rung now HOLDS — the catastrophic floor and structure stop still
# cover it, and §0.5 cuts both ways: a silent proxy is not better than waiting
# for the instrument.
_d3 = _drive(_par_rec, 5.63)                     # no current_delta at all
check("V19c no delta from the feed -> HOLD, not guess (r82 supersedes r79)",
      not _d3.should_exit,
      f"exit={_d3.should_exit} reason={_d3.exit_reason!r}")

_d4 = _drive(_par_rec, 7.00)                     # 5.59 intrinsic -> 20% extrinsic
check("V19d CONTROL: fat extrinsic and no delta -> HELD, not exited",
      not _d4.should_exit,
      f"exit={_d4.should_exit} reason={_d4.exit_reason!r}")

# ── V19e — EXTRINSIC IS NOT A PROXY FOR PAR (r80 -> r82) ──────────────────
# ⚠️ RE-POINTED, NOT LOOSENED. r80 asserted the OPPOSITE of this check: that a
# position with extrinsic at par must exit even below par delta. It shipped,
# and the measurement that followed killed it — this exact state (delta 0.9675,
# mark 5.97, spot 739.93) reads 0.7% extrinsic while the trade still had
# $2,500 of run left in it. The rung waits for DELTA.
_live_df = _par_df.copy()
_live_df["close"] = [739.80, 739.90, 739.93]       # the ACTUAL 14:08 ET tape
_d5 = _drive_on(_live_df, {**_par_rec, "current_delta": 0.9675}, 5.97)
check("V19e delta BELOW par HOLDS even at zero extrinsic — the proxy is dead",
      not _d5.should_exit,
      f"exit={_d5.should_exit} reason={_d5.exit_reason!r} — extrinsic-from-mid "
      f"hits zero at delta 0.82; exiting here costs $2,500")

# CONTROL: a mid-delta position with real extrinsic is still untouched, so the
# widening did not turn the rung into a guillotine.
_d6 = _drive_on(_live_df, {**_par_rec, "current_delta": 0.9675}, 7.50)
check("V19f CONTROL: same delta, FAT extrinsic -> HELD",
      not _d6.should_exit,
      f"exit={_d6.should_exit} reason={_d6.exit_reason!r}")

print(f"\n{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} problem(s) {FAIL}")
sys.exit(1 if FAIL else 0)
