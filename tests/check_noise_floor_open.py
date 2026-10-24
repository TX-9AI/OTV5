"""tests/check_noise_floor_open.py — v1.0
THE r93 NOISE FLOOR IS ARMED AT THE OPEN, NOT FROM ~09:40.

v1.0  2026-09-25 — OTV4TEST r141. The floor refuses a structural stop that sits
      inside one ordinary 1m bar (r93, the operator's "Floor value, agree.
      Refuse, agree."). Its measurement lived inline in main.py and needed TEN
      bars of a frame that is scoped to TODAY'S session, so from 09:35 to ~09:40
      every day it returned 0.0 and the gate STOOD DOWN - logging
      "noise floor UNMEASURABLE (no usable 1m frame)" on every entry. On
      2026-09-25 that let three entries through at 09:36-09:37 on stops of 0.14,
      0.21 and 0.31 against a session floor of ~0.43, at 96-100 contracts each,
      for -$3,170. At 09:42, with 10 bars, the same gate refused a 0.065 stop.
      Operator, 2026-09-25: "Yes" to arming it from the session's own bars.

  F0  main._noise_floor_of exists (born red names it rather than dying)
  F1  TODAY'S 09:30-09:35 TAPE (six closed 1m bars, recorded below from the
      feed store) yields a floor > 0, equal to MULT x the median range computed
      independently here
  F2  with that floor the REAL sizer refuses the three stops that lost
      (0.14 / 0.21 / 0.31) and admits the 0.52 ORB that actually traded at 09:40
  F3  fewer than NOISE_FLOOR_MIN_BARS bars still stands down (0.0) - r93 N3's
      "cannot measure disarms" is preserved; exactly the minimum arms it
  F4  the 60-bar lookback is unchanged: 70 wide bars followed by 60 quiet ones
      measure the quiet 60 only (an unbounded median would read the wide majority)
  F5  the ruled constants: minimum 3 (below the old 10), multiplier 0.5,
      lookback 60
  F6  _execute_entry_signal CALLS _noise_floor_of (the AST, not a grep) and
      carries no inline >= 10 bar test any more
"""
from __future__ import annotations

import ast
import os
import statistics
import sys
import tempfile

import glob as _glob
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
sys.path.insert(0, _root)

_s = tempfile.mkdtemp(prefix="check_noise_floor_open_",
                      dir="/var/tmp" if os.path.isdir("/var/tmp") else None)
os.environ.setdefault("OT_TRADES_DB", os.path.join(_s, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))
os.environ.setdefault("OT_RESTING_DB", os.path.join(_s, "resting.db"))
os.environ.setdefault("OT_PAPER_TRADING", "1")
os.environ.setdefault("OT_RISK_USD", "1050")
os.environ.setdefault("OT_ORB_RISK_USD", "1000")
os.environ.setdefault("OT_ORB_BUDGET_USD", "10000")

FAIL: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])


# ── the fixture: 2026-09-25 QQQ 1m, 09:30-09:35 ET, as the feed store holds it
# (candles, symbol QQQ, interval 1m). (open, high, low, close)
TAPE_0925 = [
    (742.86, 742.86, 741.70, 742.49),     # 09:30
    (742.5001, 742.81, 741.94, 742.055),  # 09:31
    (742.07, 742.54, 741.66, 742.505),    # 09:32
    (742.51, 742.90, 742.25, 742.895),    # 09:33
    (742.90, 743.68, 742.83, 743.615),    # 09:34
    (743.595, 744.10, 743.56, 743.87),    # 09:35 — the break bar both Breakouts fired on
]
LOST = (0.14, 0.21, 0.31)                 # 11ec918c, 3d275e04, 558b18ca
TRADED_0940 = 0.52                        # 799621bd — admitted, and rightly so
WIDTH = 2.02                              # today's opening range, 741.66-743.68


def _frame(rows):
    import pandas as pd
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"])


try:
    import config
    import main
    from risk.risk_manager import get_risk_manager
    _nf = getattr(main, "_noise_floor_of", None)
except Exception as exc:                                        # noqa: BLE001
    check("F0 main imports", False, f"{type(exc).__name__}: {exc}")
    print(f"\nRED — {len(FAIL)} failed: {FAIL}")
    sys.exit(1)

check("F0 main._noise_floor_of exists", _nf is not None,
      "" if _nf is not None else "absent - the floor is still measured inline (pre-r141)")
if _nf is None:
    print(f"\nRED — {len(FAIL)} failed: {FAIL}")
    sys.exit(1)

MULT = config.NOISE_FLOOR_BAR_MULT
expect = MULT * statistics.median(h - l for (_o, h, l, _c) in TAPE_0925)
got = _nf(_frame(TAPE_0925))
check("F1 today's six opening bars measure a floor", got > 0 and abs(got - expect) < 1e-9,
      f"floor {got:.4f}, independent {expect:.4f}")

RM = get_risk_manager()
for d in LOST:
    r = RM.size_for("long_debit", premium=1.02, stop_premium=0.90, grade="UNGRADED",
                    orb_width=WIDTH, orb_stop_distance=d, noise_floor=got)
    check(f"F2 the {d:.2f} stop that lost is REFUSED", (not r.allowed) and r.contracts == 0,
          f"allowed={r.allowed} n={r.contracts} reason={r.reject_reason!r}")
r = RM.size_for("long_debit", premium=1.02, stop_premium=0.84, grade="UNGRADED",
                orb_width=WIDTH, orb_stop_distance=TRADED_0940, noise_floor=got)
check("F2b the 0.52 ORB that traded at 09:40 is still ADMITTED", r.allowed and r.contracts > 0,
      f"allowed={r.allowed} n={r.contracts}")

MINB = config.NOISE_FLOOR_MIN_BARS
check("F3 fewer than the minimum bars stands down (0.0)",
      _nf(_frame(TAPE_0925[:MINB - 1])) == 0.0 and _nf(None) == 0.0,
      f"{MINB - 1} bars -> {_nf(_frame(TAPE_0925[:MINB - 1]))}")
check("F3b exactly the minimum arms it", _nf(_frame(TAPE_0925[:MINB])) > 0,
      f"{MINB} bars -> {_nf(_frame(TAPE_0925[:MINB])):.4f}")

# the WIDE bars are the MAJORITY (70 of 130), so only a real 60-bar lookback
# measures 0.4 - an unbounded median over the whole frame would measure 5.0
wide = [(100.0, 105.0, 100.0, 104.0)] * 70
quiet = [(100.0, 100.4, 100.0, 100.2)] * 60
f4 = _nf(_frame(wide + quiet))
check("F4 the lookback is still the last 60 bars", abs(f4 - MULT * 0.4) < 1e-9,
      f"{f4:.4f} vs {MULT * 0.4:.4f}")

check("F5 the ruled constants: min 3 (< the old 10), mult 0.5, lookback 60",
      MINB == 3 and MULT == 0.5 and config.NOISE_FLOOR_LOOKBACK_BARS == 60,
      f"min={MINB} mult={MULT} lookback={config.NOISE_FLOOR_LOOKBACK_BARS}")

_src = open(os.path.join(_root, "main.py")).read()
_fn = next((n for n in ast.walk(ast.parse(_src))
            if isinstance(n, ast.FunctionDef) and n.name == "_execute_entry_signal"), None)
calls = [n for n in ast.walk(_fn) if isinstance(n, ast.Call)
         and getattr(n.func, "id", None) == "_noise_floor_of"] if _fn else []
inline10 = [n for n in ast.walk(_fn) if isinstance(n, ast.Compare)
            and ("len(_nf_df)" in ast.unparse(n) or "len(_rng)" in ast.unparse(n))] if _fn else []
check("F6 _execute_entry_signal calls _noise_floor_of", bool(calls), f"{len(calls)} call(s)")
check("F6b ...and measures nothing inline any more", not inline10,
      "; ".join(ast.unparse(n) for n in inline10[:3]))

print(f"\n{'GREEN' if not FAIL else 'RED'} — {len(FAIL)} failed" + (f": {FAIL}" if FAIL else ""))
sys.exit(1 if FAIL else 0)
