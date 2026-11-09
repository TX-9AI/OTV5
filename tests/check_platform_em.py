#!/usr/bin/env python3
"""
tests/check_platform_em.py  v5.2
v5.2  2026-11-09  OTV5 r103 (RETIRE.5 step 2) — M6 RE-POINTED (WA 38.4): the GEX fly's expected_move wrapper is removed, so M6 holds volatility_measures.expected_move_session to the session formula and pins that the pin gate (its reader) never names the platform function. M1-M5 unchanged.
v5.1  2026-11-08  OTV5 r76 (RETIRE.1) — M5 RE-POINTED (WA 38.4): ORCS is removed, so M5 pins its plan gone (check_expected_move_home E5 pins the condor and
      readiness readers); M1-M4 and M6 unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-03  OTV4TEST r229 (EM.2) — THE EXPECTED MOVE IS THE TASTYTRADE PLATFORM'S.

  The operator, 2026-10-03, with a screenshot of the platform's chain (QQQ 749.53,
  "IVx: 12.1% (± 5.25)"): "Which expected move? Use the one that's built into the
  tasty trade platform." Then, shown that the butterfly's own number is ~3.3x it:
  "Don't mess with the butterfly EV then".

  M1  the formula, by hand: 0.6 x ATM straddle + 0.3 x first strangle + 0.1 x second
  M2  HIS SCREENSHOT: the quotes on it (the two calls above 750 it does not show are
      set where the visible calls' spacing puts them) give 5.2, within 0.10 of 5.25
  M3  a leg with no quote, fewer than two strikes either side, no chain, no spot:
      (None, None) - never a partial sum
  M4  the ATM strike is the nearest listed on BOTH sides
  M5  (r76: ORCS removed) ORCS's implied move IS this function, and the REAL plan records it with the
      old straddle beside it (atm_straddle)
  M6  THE SESSION EM IS UNTOUCHED: volatility_measures.expected_move_session is still the
      session formula, and the pin gate (its reader since r103; the fly's wrapper is removed) never names the platform function

Run:  python3 tests/check_platform_em.py   (exit 0 green, 1 red)
"""
import glob as _glob
import math
import os
import sys
import tempfile
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_platform_em_")
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


def C(k, bid, ask):
    return types.SimpleNamespace(strike=float(k), bid=bid, ask=ask, mark=None)


def chain(calls, puts):
    return types.SimpleNamespace(calls=[C(*x) for x in calls], puts=[C(*x) for x in puts])


def main():
    try:
        from analysis import volatility_measures as VM
        f = VM.expected_move_platform
        ch = chain([(98, 2.9, 3.1), (99, 1.9, 2.1), (100, 0.9, 1.1), (101, 0.4, 0.6), (102, 0.1, 0.3)],
                   [(98, 0.1, 0.3), (99, 0.3, 0.5), (100, 0.8, 1.0), (101, 1.7, 1.9), (102, 2.7, 2.9)])
        want = 0.6 * (1.0 + 0.9) + 0.3 * (0.5 + 0.4) + 0.1 * (0.2 + 0.2)
        em, atm = f(ch, 100.2)
        check("M1 0.6 x ATM straddle + 0.3 x first strangle + 0.1 x second, at the marks",
              em is not None and abs(em - want) < 1e-9 and atm == 100.0, f"{em} want {want}, atm {atm}")
        shot = chain([(748, 4.01, 4.05), (749, 3.38, 3.41), (750, 2.80, 2.83), (751, 2.27, 2.30), (752, 1.80, 1.83)],
                     [(748, 2.07, 2.10), (749, 2.43, 2.45), (750, 2.84, 2.88), (751, 3.3, 3.4), (752, 3.8, 3.9)])
        em2, atm2 = f(shot, 749.53)
        check("M2 the operator's screenshot (749.53, platform ± 5.25): within 0.10, ATM 750",
              em2 is not None and abs(em2 - 5.25) <= 0.10 and atm2 == 750.0, f"{em2} atm {atm2}")
        nob = chain([(98, 2.9, 3.1), (99, 1.9, 2.1), (100, 0.9, 1.1), (101, 0.4, 0.6), (102, 0.0, 0.0)],
                    [(98, 0.1, 0.3), (99, 0.3, 0.5), (100, 0.8, 1.0), (101, 1.7, 1.9), (102, 2.7, 2.9)])
        thin = chain([(99, 1.9, 2.1), (100, 0.9, 1.1), (101, 0.4, 0.6)], [(99, 0.3, 0.5), (100, 0.8, 1.0), (101, 1.7, 1.9)])
        check("M3 a leg with no quote, a thin chain, no chain and no spot are all (None, None)",
              f(nob, 100.2) == (None, None) and f(thin, 100.2) == (None, None) and f(None, 100.0) == (None, None)
              and f(ch, None) == (None, None) and f(ch, 0) == (None, None),
              f"{f(nob, 100.2)} {f(thin, 100.2)} {f(None, 100.0)} {f(ch, None)}")
        lop = chain([(98, 2.9, 3.1), (99, 1.9, 2.1), (100, 0.9, 1.1), (100.5, 0.6, 0.8), (101, 0.4, 0.6), (102, 0.1, 0.3)],
                    [(98, 0.1, 0.3), (99, 0.3, 0.5), (100, 0.8, 1.0), (101, 1.7, 1.9), (102, 2.7, 2.9)])
        check("M4 the ATM strike is the nearest listed on BOTH sides (100.5 is calls-only, so 100)",
              f(lop, 100.45)[1] == 100.0, str(f(lop, 100.45)))
        import importlib.util as _ilu
        check("M5 r76: ORCS (this function's first reader) is removed; the condor and readiness still read it",
              __import__("retired_names").retired("strategy.orcs_plan"))
        from analysis import volatility_measures as VM          # r103: the GEX fly wrapper is removed
        import ast as _ast
        import datetime as _dt
        from zoneinfo import ZoneInfo
        t = _dt.datetime(2026, 10, 5, 13, 0, tzinfo=ZoneInfo("America/New_York"))
        want6 = 750.0 * 0.3 * math.sqrt(3.0 / 6.5) / math.sqrt(252)
        _msrc = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py"), encoding="utf-8").read()
        _pg = next(n for n in _ast.walk(_ast.parse(_msrc)) if isinstance(n, _ast.FunctionDef) and n.name == "pin_proximity_verdict")
        _pgs = _ast.unparse(_pg)
        check("M6 the session EM is still the session formula, and the pin gate reads it, never the platform one (r103)",
              abs(VM.expected_move_session(750.0, 0.3, t) - want6) < 1e-9
              and "expected_move_session" in _pgs and "expected_move_platform" not in _pgs,
              f"{VM.expected_move_session(750.0, 0.3, t)} want {want6}")
    except Exception as exc:                                  # noqa: BLE001
        for n in ("M1", "M2", "M3", "M4", "M5", "M6"):
            if n not in FAILED:
                check(f"{n} (did not run)", False, f"{type(exc).__name__}: {exc}")
    if FAILED:
        print(f"\nRED — {len(set(FAILED))} check(s): {sorted(set(FAILED))}")
        return 1
    print("\nGREEN — the platform's expected move; the session EM is untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
