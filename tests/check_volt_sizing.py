#!/usr/bin/env python3
"""
tests/check_volt_sizing.py  v1.5
v1.5  2026-10-02  OTV4TEST r187 (ROSTER.1) — RE-POINTED BY THE RULING, NOT LOOSENED:
      the strategy is OFF by default from r187; this checker tests its LOGIC,
      so it switches it on for its own run (OT_VOLT=1). check_trade_switches pins the default.
v1.4  2026-10-02  OTV4TEST r186 (ZBID.1) — the _C
      fixture contract now carries a TWO-SIDED quote (bid/ask around its
      mark), as every live OptionContract does: r186 (ZBID.1) refuses a
      contract with no bid, and this fixture had none. No check changed.
v1.3  2026-09-27  OTV4TEST r161 — THE RAMP START IS RISK PER TRADE (the operator: "Merge
      it"). OT_ORB_RISK_USD is no longer read, so the fixture's forced START of 1000
      became 1050 (OT_RISK_USD). V4 is RE-CAPTURED, NOT LOOSENED: HEAD 6e1fa68's own
      size_for, run with OT_ORB_RISK_USD=1050, returns ORB tight 77, ORB wide 19,
      Breakout 50->52, hunt 11 - exactly what the merged tree returns. Hand check:
      1050 // (0.45 x 0.30 x 100) = 77; 1050 // 54 = 19; 1050 // 20 = 52.
v1.2  2026-09-25  OTV4TEST r141 — V7 RE-POINTED, NOT DROPPED (§38.4): the noise floor
      moved into main._noise_floor_of(df_1m). V7 now requires the call site to
      pass only ctx["df_1m"], and the helper to use NOISE_FLOOR_BAR_MULT and never
      see a signal or strategy - the same "no VOLT exemption" property.

v1.1  2026-09-24  OTV4TEST r131 OPTION 2 — the operator ruled VOLT takes
      Breakout's 1-R CURVE, not the flat scale-up: sizing stop premium =
      premium - |delta| x signal range (main._sizing_stop_premium), SIZING
      ONLY. V1 re-pointed to rpc = |delta| x range x 100 (property moved, WA
      38.4: the count is still min(risk//rpc, budget//cost)); V6b/V6d pin
      that the RECORDED stop premium is untouched; V7 pins the stop_premium
      argument; V8 the curve (tight range sizes larger than wide); V9 no
      delta -> the flat floor, LOUDLY.

v1.0  2026-09-24  OTV4TEST r131 — VOLT ADOPTS THE BREAKOUT SIZING MODEL. The
      operator, 2026-09-24: *"VOLT needs to adopt the breakout sizing model."*
      Born RED on b1b6594 (r130), where `main._geometry_inputs` does not exist
      and a VOLT signal carries no `sizing_distance`.

🔑 WHAT IT PINS. A VOLT signal, built by the REAL VoltStrategy from a fixture
tape, reaches the contract count through the REAL main._geometry_inputs (the
geometry inputs of `_execute_entry_signal`'s sizing block, extracted verbatim
in r131) and the REAL RiskManager.size_for called with the arguments main.py
builds. Nothing here re-implements the sizer (WA §21, §0.4).

  V1  a VOLT signal sizes on the geometry/risk rule ('orb_geometry'), count =
      min(ORB_RISK_USD // rpc, ORB_BUDGET_USD // cost) — not the budget rule
  V2  the distance the sizer sees is the SIGNAL BAR'S RANGE, not
      |entry - stop| (which is 0 by the 2026-09-21 stop ruling)
  V3  a VOLT range inside the day's noise floor is REFUSED (r93), exactly as
      a Breakout stop is — and one just outside it is sized
  V4  PARITY PIN: ORB, Breakout and a non-geometry long debit (the hunt shape,
      carrying orb_range but no flag) produce the SAME inputs, rule and count
      as HEAD b1b6594 — numbers captured by running HEAD's code
  V5  ENT.1 still sees VOLT's `underlying_stop_is_thesis`, and its stop still
      equals its entry
  V6  VOLT's EXITS are untouched: not sizes_on_structure(), the percentage
      stop premium (> 0, so by_risk engages) and the +50% trail activation
  V7  main's size_for call is wired to the helper's inputs, the sizing stop
      premium and the MEASURED noise floor, with no strategy-conditioned
      floor (AST, one function)
  V8  THE CURVE: a tight signal range sizes larger than a wide one
  V9  no delta at fire time -> the flat MAX_LOSS_PCT floor, with a WARNING

Run:  python3 tests/check_volt_sizing.py
"""

from __future__ import annotations
import os as _os_r187
_os_r187.environ["OT_VOLT"] = "1"   # r187: test the strategy's logic switched on

import atexit
import datetime as dt
import os
import shutil
import sys
import tempfile

import glob as _glob
for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path: sys.path.insert(1, _sp)

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

# ⚠️ SCRATCH STORES, NEVER THE LIVE ONES. The plan writes a row per tick; if
# the harness did not point the stores somewhere, this does, under /var/tmp
# (/tmp is a small RAM tmpfs, HYG.14), and removes it on exit.
if not all(os.environ.get(k) for k in ("OT_TRADES_DB", "OT_DERIVED_DB", "OT_RESTING_DB")):
    _scr = tempfile.mkdtemp(prefix="check_volt_sizing_",
                            dir="/var/tmp" if os.path.isdir("/var/tmp") else None)
    atexit.register(shutil.rmtree, _scr, True)
    os.environ.setdefault("OT_TRADES_DB", os.path.join(_scr, "trades.db"))
    os.environ.setdefault("OT_DERIVED_DB", os.path.join(_scr, "derived_store.db"))
    os.environ.setdefault("OT_RESTING_DB", os.path.join(_scr, "resting.db"))
os.environ.setdefault("OT_PAPER_TRADING", "1")
# The operator's live ramp values, 2026-09-24 (START risk, TOP budget), FORCED
# so V4's HEAD-captured golden numbers do not move with the shell's env.
# r161: the ramp START IS OT_RISK_USD (merged); OT_ORB_RISK_USD is not read.
os.environ["OT_ORB_BUDGET_USD"] = "10000"
os.environ["OT_RISK_USD"] = "1050"          # risk per trade = ramp MIN (V1, V1b, V4)

FAIL: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])


_err = ""
try:
    import pandas as pd
    import main
    from risk import risk_manager as _rmm
    from risk.risk_manager import RiskManager
    from strategy.base_strategy import OptionsSignal
    from strategy.volt_strategy import VoltStrategy, MAX_LOSS_PCT
    from strategy.volt_plan import VOL_LOOKBACK_BARS, VOL_MULT
    _geo = getattr(main, "_geometry_inputs", None)
    if _geo is None:
        _err = "main._geometry_inputs does not exist"
except Exception as exc:                                   # noqa: BLE001
    _err = f"{type(exc).__name__}: {exc}"
    _geo = None

check("V0 main._geometry_inputs and the VOLT modules import", _geo is not None, _err)
if _geo is None:
    if "main" not in sys.modules:
        print(f"\nFAIL: {len(FAIL)} problem(s) {FAIL}")
        sys.exit(1)

    def _pre_r131_inputs(signal):
        """ONLY on a pre-r131 tree, so the born-red run says WHICH property is
        missing instead of stopping at V0: b1b6594's inline block, verbatim
        (main.py 4745-4785). The build never takes this path — V0 is red."""
        _orb_w = _orb_d = 0.0
        if (getattr(signal, "strategy_name", "") == "ORBStrategy"
                or getattr(signal, "sizes_on_geometry", False)):
            _orb_w = abs(float(getattr(signal, "orb_range_high", 0) or 0)
                         - float(getattr(signal, "orb_range_low", 0) or 0))
            _orb_d = abs(float(getattr(signal, "underlying_entry", 0) or 0)
                         - float(getattr(signal, "underlying_stop", 0) or 0))
        return _orb_w, _orb_d
    main._geometry_inputs = _pre_r131_inputs

if not hasattr(main, "_sizing_stop_premium"):
    check("V0c main._sizing_stop_premium exists (r131 option 2)", False,
          "absent — HEAD's `_sig_num(signal, 'stop_premium')` is used below")
    main._sizing_stop_premium = lambda signal: main._sig_num(signal, "stop_premium")

RISK, BUDGET = float(_rmm.ORB_RISK_USD), float(_rmm.ORB_BUDGET_USD)
RM = RiskManager()


def size_like_main(signal, noise_floor=0.0):
    """`_execute_entry_signal`'s size_for call, argument for argument (main.py
    `sizing = risk_mgr.size_for(...)`), for a long_debit that is not a fly."""
    w, d = main._geometry_inputs(signal)
    return (w, d), RM.size_for(
        "long_debit",
        premium=signal.entry_premium,
        stop_premium=main._sizing_stop_premium(signal),
        grade="UNGRADED",
        net_debit=0.0,
        butterfly_half_size=False,
        orb_width=w,
        orb_stop_distance=d,
        noise_floor=noise_floor,
    )


# ── the fixture: a real VOLT fire from the real strategy ──────────────────
class _C:
    def __init__(self, strike, mark, delta=0.45, gamma=0.02):
        self.strike, self.mark, self.delta, self.gamma = strike, mark, delta, gamma
        self.bid, self.ask = max(0.01, mark - 0.02), mark + 0.02   # r186: two-sided
        self.expiry = "2026-09-24"


class _Chain:
    def __init__(self, spot, mark):
        self.calls = [_C(float(int(spot) + i), mark) for i in (-2, -1, 0, 1, 2)]
        self.puts = [_C(float(int(spot) + i), mark) for i in (-2, -1, 0, 1, 2)]


DELTA = 0.45          # every fixture contract's quoted delta (_C default)


def volt_signal(sig_range, mark=1.36, spot=601.40):
    """A long VOLT fire whose signal bar spans `sig_range` points."""
    rows, idx = [], []
    t0 = dt.datetime(2026, 9, 24, 9, 40)
    n_base = VOL_LOOKBACK_BARS + 2
    for i in range(n_base):
        rows.append({"open": 600.0, "high": 600.05, "low": 599.95,
                     "close": 600.0, "volume": 1000.0})
    hi = spot + 0.02
    rows.append({"open": hi - sig_range, "high": hi, "low": hi - sig_range,
                 "close": spot, "volume": 1000.0 * (VOL_MULT + 1.0)})   # signal bar
    rows.append({"open": spot, "high": spot, "low": spot,
                 "close": spot, "volume": 10.0})                         # forming
    for i in range(len(rows)):
        idx.append(t0 + dt.timedelta(minutes=i))
    df = pd.DataFrame(rows, index=pd.DatetimeIndex(idx))
    return VoltStrategy().generate_signal(chain=_Chain(spot, mark), price_now=spot,
                                          df_1m=df, now_et="10:00")


R = 0.62
sig = volt_signal(R)
check("V0b the real VoltStrategy fires on the fixture", sig is not None,
      "" if sig is not None else "no signal — the fixture no longer satisfies VOLT's two gates")
if sig is None:
    print(f"\nFAIL: {len(FAIL)} problem(s) {FAIL}")
    sys.exit(1)

# ── V1 — the geometry/risk rule, not the budget rule ─────────────────────
(w, d), res = size_like_main(sig)
_cost = sig.entry_premium * 100.0
_sp = main._sig_num(sig, "stop_premium")          # the RECORDED stop (flat floor)
_rpc = DELTA * R * 100.0                            # Breakout's 1-R: |delta| x distance
_want = min(max(1, int(RISK // _rpc)), int(BUDGET // _cost))
check("V1 a VOLT signal sizes on 'orb_geometry', count = min(risk//(|delta|xRx100), budget//cost)",
      res.allowed and res.rule == "orb_geometry" and res.contracts == _want,
      f"rule={res.rule!r} count={res.contracts} want={_want} "
      f"(risk ${RISK:.0f} / rpc ${_rpc:.2f}, budget ${BUDGET:.0f} / cost ${_cost:.0f})")
_budget_rule = RM.size_for("long_debit", premium=sig.entry_premium,
                           stop_premium=_sp, grade="UNGRADED")
check("V1b ...and that is NOT what the budget rule would have given",
      _budget_rule.rule != "orb_geometry" and _budget_rule.contracts != res.contracts,
      f"budget rule {_budget_rule.rule!r} -> {_budget_rule.contracts}, "
      f"geometry -> {res.contracts}")
check("V1c width 0 (VOLT has no opening range) -> geometry abstains, risk sizes it",
      res.rule == "orb_geometry" and w == 0.0 and res.geometry_wanted == 0
      and d > 0,
      f"width={w} geometry_wanted={res.geometry_wanted} (WIDE STOP branch)")

# ── V2 — the distance is the signal range ────────────────────────────────
_ent_stop = abs(sig.underlying_entry - sig.underlying_stop)
check("V2 the sizing distance is the signal bar's range, not |entry - stop|",
      abs(d - R) < 1e-9 and _ent_stop == 0.0,
      f"distance={d:.4f} signal range={R} |entry-stop|={_ent_stop}")
check("V2b the signal carries it as `sizing_distance` == the plan's risk_px",
      abs(float(getattr(sig, "sizing_distance", -1)) - R) < 1e-9,
      f"sizing_distance={getattr(sig, 'sizing_distance', None)}")

# ── V3 — the noise floor applies to VOLT's distance ──────────────────────
_, r_in = size_like_main(sig, noise_floor=R * 1.25)
check("V3 a VOLT range inside the noise floor is REFUSED",
      not r_in.allowed and "noise_floor" in str(r_in.reject_reason),
      f"allowed={r_in.allowed} reason={r_in.reject_reason!r}")
_, r_out = size_like_main(sig, noise_floor=R * 0.8)
check("V3b ...and one just outside it is sized (the gate is the floor, not a wall)",
      r_out.allowed and r_out.contracts == res.contracts,
      f"allowed={r_out.allowed} count={r_out.contracts}")

# ── V4 — PARITY: ORB, Breakout and the hunt shape exactly as on HEAD ─────
# (label, signal kwargs, extra attrs, noise_floor) -> HEAD's (w, d, rule, n, allowed)
# 🔑 GOLDEN captured 2026-09-24 by running b1b6594's inline sizing block and
# size_for on these exact signals (OT_ORB_RISK_USD=1000, OT_ORB_BUDGET_USD=10000,
# OT_RISK_USD=1050). RE-CAPTURED 2026-09-27 (r161) at START = 1050 by running
# HEAD 6e1fa68 with OT_ORB_RISK_USD=1050: the merge moves the START, never the
# arithmetic, so parity with HEAD at the same START is what this still pins.
_CASES = [
    ("ORB tight", dict(strategy_name="ORBStrategy", orb_range_high=601.0,
                       orb_range_low=600.0, underlying_entry=601.10,
                       underlying_stop=600.80, entry_delta=0.45,
                       entry_premium=1.20), {}, 0.0),
    ("ORB wide", dict(strategy_name="ORBStrategy", orb_range_high=601.0,
                      orb_range_low=600.6, underlying_entry=601.10,
                      underlying_stop=599.90, entry_delta=0.45,
                      entry_premium=1.20), {}, 0.0),
    ("ORB in-floor", dict(strategy_name="ORBStrategy", orb_range_high=601.0,
                          orb_range_low=600.0, underlying_entry=601.10,
                          underlying_stop=601.00, entry_delta=0.45,
                          entry_premium=1.20), {}, 0.21),
    ("Breakout", dict(strategy_name="Breakout", orb_range_high=601.0,
                      orb_range_low=600.0, underlying_entry=601.25,
                      underlying_stop=600.85, entry_delta=0.50,
                      entry_premium=0.95), {"sizes_on_geometry": True}, 0.21),
    ("Hunt shape", dict(strategy_name="LiquidityHunt", orb_range_high=601.0,
                        orb_range_low=600.0, underlying_entry=601.25,
                        underlying_stop=600.85, entry_delta=0.50,
                        entry_premium=0.95), {}, 0.21),
]
GOLD = {
    "ORB tight":    (1.0, 0.30, "orb_geometry", 77, True),
    "ORB wide":     (0.4, 1.20, "orb_geometry", 19, True),
    "ORB in-floor": (1.0, 0.10, "orb_geometry", 0, False),
    "Breakout":     (1.0, 0.40, "orb_geometry", 52, True),
    "Hunt shape":   (0.0, 0.0, "budget", 11, True),
}
for label, kw, extra, nf in _CASES:
    s = OptionsSignal(**kw)
    for k, v in extra.items():
        setattr(s, k, v)
    (gw, gd), gr = size_like_main(s, noise_floor=nf)
    got = (round(gw, 6), round(gd, 6), gr.rule, gr.contracts, gr.allowed)
    exp = GOLD[label]
    check(f"V4 {label} sizes exactly as on HEAD",
          (round(exp[0], 6), round(exp[1], 6), exp[2], exp[3], exp[4]) == got,
          f"got {got} want {exp}")

# ── V5 — ENT.1 still sees the thesis flag ────────────────────────────────
check("V5 VOLT still declares underlying_stop_is_thesis (ENT.1's opt-out)",
      getattr(sig, "underlying_stop_is_thesis", False) is True
      and sig.underlying_stop == sig.underlying_entry,
      f"flag={getattr(sig, 'underlying_stop_is_thesis', None)} "
      f"stop={sig.underlying_stop} entry={sig.underlying_entry}")

# ── V6 — exits untouched ─────────────────────────────────────────────────
check("V6 VOLT is NOT sizes_on_structure() (the trail/stop anchor is untouched)",
      not sig.sizes_on_structure() and not getattr(sig, "sizes_on_geometry", False),
      f"sizes_on_structure={sig.sizes_on_structure()}")
check("V6b its stop premium is the flat percentage and > 0, so by_risk engages",
      _sp > 0 and abs(_sp - sig.entry_premium * (1 - MAX_LOSS_PCT)) < 1e-9,
      f"stop_premium={_sp:.4f} entry={sig.entry_premium} MAX_LOSS_PCT={MAX_LOSS_PCT}")
check("V6c its trail still activates at +50% of the target, not at entry",
      abs(sig.trail_activation_premium()
          - sig.entry_premium * (1 + sig.tp_pct * 0.5)) < 1e-9,
      f"trail_activation={sig.trail_activation_premium():.4f}")

# ── V7 — main's size_for call is wired to exactly these inputs ──────────
# ⚠️ V1-V4 drive `_geometry_inputs` and `size_for` for real, but the noise
# floor is measured inside `_execute_entry_signal` from ctx["df_1m"], which
# needs a live context to execute. So this AST-scopes that one function: the
# size_for call takes orb_width/orb_stop_distance/noise_floor from `_orb_w`,
# `_orb_d`, `_noise_floor`; `_orb_w, _orb_d` come ONLY from
# `_geometry_inputs(signal)`; and `_noise_floor` is set only by the measured
# block (0.0, then the median), never conditioned on the strategy. A VOLT
# exemption from the floor would have to break one of these.
import ast as _ast
_src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
_fn = next((n for n in _ast.walk(_ast.parse(_src))
            if isinstance(n, _ast.FunctionDef) and n.name == "_execute_entry_signal"), None)
_kw, _geo_src, _nf_assign, _od_assign = {}, [], [], []
if _fn is not None:
    for n in _ast.walk(_fn):
        if (isinstance(n, _ast.Call) and isinstance(n.func, _ast.Attribute)
                and n.func.attr == "size_for"):
            _kw = {k.arg: _ast.unparse(k.value) for k in n.keywords}
        if isinstance(n, (_ast.Assign, _ast.AugAssign, _ast.AnnAssign)):
            _tg = n.targets if isinstance(n, _ast.Assign) else [n.target]
            _names = {x.id for t in _tg for x in _ast.walk(t) if isinstance(x, _ast.Name)}
            if "_noise_floor" in _names:
                _nf_assign.append(_ast.unparse(n.value))
            if _names & {"_orb_w", "_orb_d"}:
                _od_assign.append(_ast.unparse(n.value))
# r141 — the measurement MOVED into main._noise_floor_of(df_1m). The property is
# unchanged and re-pointed, not dropped (§38.4): the call site hands the helper
# ONLY the tape frame from ctx, and the helper uses the multiplier and never
# sees a signal or a strategy name.
_nfdf_assign, _helper_ok = [], False
if _fn is not None:
    for n in _ast.walk(_fn):
        if isinstance(n, _ast.Assign) and any(getattr(t, "id", None) == "_nf_df" for t in n.targets):
            _nfdf_assign.append(_ast.unparse(n.value))
_hf = next((n for n in _ast.walk(_ast.parse(_src))
            if isinstance(n, _ast.FunctionDef) and n.name == "_noise_floor_of"), None)
if _hf is not None:
    _hsrc = "\n".join(_ast.unparse(x) for x in _hf.body[1:])     # body without the docstring
    _helper_ok = ([a.arg for a in _hf.args.args] == ["df_1m"]
                  and "NOISE_FLOOR_BAR_MULT" in _hsrc
                  and "signal" not in _hsrc and "strategy" not in _hsrc)
check("V7 main's size_for takes orb_width/_stop_distance/noise_floor from the helper and the tape",
      _kw.get("orb_width") == "_orb_w" and _kw.get("orb_stop_distance") == "_orb_d"
      and _kw.get("noise_floor") == "_noise_floor"
      and _od_assign == ["_geometry_inputs(signal)"]
      and len(_nf_assign) == 2 and _nf_assign[0] == "0.0"
      and _nf_assign[1] == "_noise_floor_of(_nf_df)" and _nfdf_assign == ["ctx.get('df_1m')"]
      and _helper_ok,
      f"kwargs={ {k: _kw.get(k) for k in ('orb_width', 'orb_stop_distance', 'noise_floor')} } "
      f"_orb_w/_orb_d <- {_od_assign} _noise_floor <- {_nf_assign}")

check("V7b ...and its stop_premium argument is the SIZING stop, not the recorded one",
      _kw.get("stop_premium") == "_sizing_stop_premium(signal)",
      f"stop_premium={_kw.get('stop_premium')}")

# ── V8 — the 1-R CURVE: tight range big, wide range small ────────────────
_, r_tight = size_like_main(volt_signal(0.30))
_, r_wide = size_like_main(volt_signal(0.90))
_wt = min(max(1, int(RISK // (DELTA * 0.30 * 100))), int(BUDGET // _cost))
_ww = min(max(1, int(RISK // (DELTA * 0.90 * 100))), int(BUDGET // _cost))
check("V8 the curve: a 0.30 range sizes LARGER than a 0.90 range, each at |delta|xR",
      r_tight.contracts == _wt and r_wide.contracts == _ww and _wt > _ww,
      f"0.30 -> {r_tight.contracts} (want {_wt}), 0.90 -> {r_wide.contracts} (want {_ww})")

# ── V9 — no delta -> the flat floor, loudly ──────────────────────────────
import logging as _lg


class _Grab(_lg.Handler):
    def __init__(self):
        super().__init__(_lg.WARNING); self.msgs = []

    def emit(self, rec):
        self.msgs.append(rec.getMessage())


_g = _Grab(); _lg.getLogger().addHandler(_g)
_nd = volt_signal(R)
_nd.sizing_delta = None
_sp_nd = main._sizing_stop_premium(_nd)
_lg.getLogger().removeHandler(_g)
check("V9 no delta at fire time -> the flat MAX_LOSS_PCT floor, with a WARNING",
      abs(_sp_nd - _nd.entry_premium * (1 - MAX_LOSS_PCT)) < 1e-9
      and any("FLAT stop premium" in m for m in _g.msgs),
      f"sizing stop={_sp_nd:.4f} warnings={[m[:60] for m in _g.msgs]}")

# ── V6d — the recorded stop is still the flat floor AFTER every sizing call ─
check("V6d sizing never wrote back: the signal's stop_premium() is still the flat floor",
      "stop_premium" not in vars(sig)
      and abs(main._sig_num(sig, "stop_premium") - sig.entry_premium * (1 - MAX_LOSS_PCT)) < 1e-9,
      f"stop_premium()={main._sig_num(sig, 'stop_premium'):.4f}")

if FAIL:
    print(f"\nFAIL: {len(FAIL)} problem(s) {FAIL}")
    sys.exit(1)
print("\nPASS: VOLT sizes on the Breakout model; ORB/Breakout at parity with HEAD")
