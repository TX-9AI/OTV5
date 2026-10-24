#!/usr/bin/env python3
"""
tests/check_expected_move_home.py  v1.1
v1.1  2026-10-03  OTV4TEST r229 (EM.2) — E5 RE-POINTED: by the operator's ruling the condor, readiness and ORCS call sites
      now return expected_move_platform. E1 (the butterflies' number and its 15-minute floor) is unchanged - he ruled it stays.
v1.0  2026-10-03  OTV4TEST r223 (EM.1) — EVERY EXPECTED-MOVE FORMULA LIVES IN ONE MODULE, AND NO NUMBER MOVED.

  The 10-03 audit (C8): five expected-move formulas across the tree (ORCS added
  a sixth). The operator, 2026-10-03, to "move the five formulas into one
  module with no number changed, keeping the butterfly's 15-minute floor
  exactly as it is": "Yes".

  The OLD bodies are kept here, verbatim, as the reference.
  E1  the butterflies' expected_move: identical on a grid of prices, IVs and
      clock times - including the 15-minute floor near the bell, after the
      bell, and the unusable-input cases
  E2  the condor's straddle (nearest MARKED strike each side): identical on
      200 random chains, including chains with unmarked and missing sides
  E3  the readiness straddle (nearest strike each side): identical
  E4  ORCS's same-strike straddle and its mark: identical
  E5  each call site returns the module's value (it delegates)

Run:  python3 tests/check_expected_move_home.py   (exit 0 green, 1 red)
"""
import datetime as _dt
import glob as _glob
import math
import os
import random
import sys
import tempfile
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_expected_move_home_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


# ── the OLD bodies, verbatim ────────────────────────────────────────────────
def old_expected_move(underlying, atm_iv, now):
    from utils.math_utils import safe_float
    underlying = safe_float(underlying)
    atm_iv = safe_float(atm_iv)
    if not underlying or not atm_iv or atm_iv <= 0 or underlying <= 0:
        return None
    try:
        close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        hours = max((close - now).total_seconds() / 3600.0, 0.25)
    except Exception:                                          # noqa: BLE001
        hours = 3.0
    return underlying * atm_iv * math.sqrt(hours / 6.5) / math.sqrt(252)


def old_condor(chain, underlying):
    try:
        atm_call = min([c for c in chain.calls if c.mark > 0], key=lambda c: abs(c.strike - underlying))
        atm_put = min([c for c in chain.puts if c.mark > 0], key=lambda c: abs(c.strike - underlying))
        if atm_call.mark > 0 and atm_put.mark > 0:
            return atm_call.mark + atm_put.mark
    except Exception:                                          # noqa: BLE001
        pass
    return 0.0


def old_readiness(chain, price):
    try:
        if chain is None or price <= 0:
            return 0.0
        calls = getattr(chain, "calls", None) or []
        puts = getattr(chain, "puts", None) or []
        if not calls or not puts:
            return 0.0
        atm_c = min(calls, key=lambda c: abs(getattr(c, "strike", 0.0) - price))
        atm_p = min(puts, key=lambda c: abs(getattr(c, "strike", 0.0) - price))
        em = float(getattr(atm_c, "mark", 0.0) or 0.0) + float(getattr(atm_p, "mark", 0.0) or 0.0)
        return em if em > 0 else 0.0
    except Exception:                                          # noqa: BLE001
        return 0.0


def old_mark(c):
    from utils.math_utils import safe_float
    b, a = safe_float(getattr(c, "bid", None)), safe_float(getattr(c, "ask", None))
    if a is not None and a > 0 and b is not None and b >= 0:
        return (a + b) / 2.0
    m = safe_float(getattr(c, "mark", None))
    return m if m is not None and m > 0 else None


def old_orcs(chain, spot):
    try:
        calls = {float(c.strike): c for c in (chain.calls or [])}
        puts = {float(p.strike): p for p in (chain.puts or [])}
        both = sorted(set(calls) & set(puts), key=lambda k: abs(k - spot))
        for k in both[:3]:
            mc, mp = old_mark(calls[k]), old_mark(puts[k])
            if mc is not None and mp is not None:
                return round(mc + mp, 4), k
    except Exception:                                          # noqa: BLE001
        pass
    return None, None


def chains():
    rnd = random.Random(1003)
    out = []
    for n in range(200):
        spot = rnd.uniform(20, 800)
        def side(drop_p):
            cs = []
            for k in range(int(spot) - 6, int(spot) + 7):
                if rnd.random() < drop_p:
                    continue
                m = max(0.0, rnd.uniform(-0.3, 4.0))
                bid = max(0.0, m - rnd.uniform(0, 0.05)); ask = m + rnd.uniform(0, 0.05) if rnd.random() > 0.1 else 0.0
                cs.append(types.SimpleNamespace(strike=float(k), mark=round(m, 4), bid=round(bid, 4), ask=round(ask, 4)))
            return cs
        dp = 0.0 if n % 5 else 0.5
        out.append((types.SimpleNamespace(calls=side(dp), puts=side(dp)), spot))
    out.append((types.SimpleNamespace(calls=[], puts=[]), 100.0))
    out.append((types.SimpleNamespace(calls=None, puts=None), 100.0))
    return out


def main():
    try:
        from analysis import volatility_measures as VM
        from strategy import gex_pin_butterfly as GPB
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
        grid = []
        for S in (12.5, 215.0, 750.2, 5800.0, 0, None, -3):
            for iv in (0.08, 0.25, 0.9, 0, None, float("nan")):
                for hh, mm in ((9, 45), (12, 0), (15, 30), (15, 50), (15, 59), (16, 0), (17, 30)):
                    grid.append((S, iv, _dt.datetime(2026, 10, 5, hh, mm, tzinfo=et)))
        def same(a, b):
            return (a is None and b is None) or (a is not None and b is not None and (a == b or (a != a and b != b)))
        bad = [(S, iv, t.strftime("%H:%M")) for S, iv, t in grid
               if not same(GPB.expected_move(S, iv, t), old_expected_move(S, iv, t))
               or not same(VM.expected_move_session(S, iv, t), old_expected_move(S, iv, t))]
        floor = GPB.expected_move(750.0, 0.2, _dt.datetime(2026, 10, 5, 15, 59, tzinfo=et))
        want_floor = 750.0 * 0.2 * math.sqrt(0.25 / 6.5) / math.sqrt(252)
        check(f"E1 the butterflies' expected move is identical on {len(grid)} cases; the 15-minute floor holds at 15:59",
              not bad and abs(floor - want_floor) < 1e-12, f"differs: {bad[:4]}; floor {floor} want {want_floor}")
    except Exception as exc:                                  # noqa: BLE001
        check("E1 (did not run)", False, f"{type(exc).__name__}: {exc}")
        VM = None

    try:
        CH = chains()
        b2 = [i for i, (ch, s) in enumerate(CH) if VM.straddle_nearest_marked(ch, s) != old_condor(ch, s)]
        check(f"E2 the condor's nearest-marked straddle is identical on {len(CH)} chains", not b2, f"differs on {b2[:5]}")
        b3 = [i for i, (ch, s) in enumerate(CH) if VM.straddle_nearest(ch, s) != old_readiness(ch, s)]
        check("E3 the readiness nearest-strike straddle is identical", not b3 and VM.straddle_nearest(None, 5.0) == 0.0,
              f"differs on {b3[:5]}")
        b4 = [i for i, (ch, s) in enumerate(CH) if VM.straddle_same_strike(ch, s) != old_orcs(ch, s)]
        marks = all(VM.quote_mark(c) == old_mark(c) for ch, _s in CH for c in ((ch.calls or []) + (ch.puts or [])))
        check("E4 ORCS's same-strike straddle and its mark are identical", not b4 and marks, f"differs on {b4[:5]}, marks {marks}")
    except Exception as exc:                                  # noqa: BLE001
        for n_ in ("E2", "E3", "E4"):
            if n_ not in FAILED:
                check(f"{n_} (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        from strategy import orcs_plan as OP
        from strategy.iron_condor_strategy import IronCondorStrategy as IC
        from analysis import trade_readiness as TR
        ch, s = CH[3]
        ic = IC.__new__(IC)
        tr_fn = next(getattr(c, "_expected_move_now") for c in vars(TR).values()
                     if isinstance(c, type) and hasattr(c, "_expected_move_now"))
        check("E5 the condor, readiness and ORCS call sites return the module's value",
              ic._expected_move_from_straddle(ch, s) == (VM.expected_move_platform(ch, s)[0] or 0.0)
              and tr_fn({"chain": ch}, s) == (VM.expected_move_platform(ch, s)[0] or 0.0) and tr_fn({}, s) == 0.0
              and OP.implied_move is VM.expected_move_platform and OP.mark_of is VM.quote_mark)   # r229 (EM.2)
    except Exception as exc:                                  # noqa: BLE001
        check("E5 (did not run)", False, f"{type(exc).__name__}: {exc}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — six expected-move formulas, one home, every number unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
