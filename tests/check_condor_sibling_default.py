#!/usr/bin/env python3
# tests/check_condor_sibling_default.py  v1.0
# v1.0  2026-10-03  OTV4TEST r190 (AUD.1) — shared with otv4 CND.11. Everything after the closing
#       docstring is byte-identical with otv4's gate; these lines and the r106 venv bootstrap sit ABOVE
#       the docstring so the body hash holds and the lander (system python3) can import the modules.
import glob as _g, os as _o, sys as _s          # OTV4TEST: r106 venv bootstrap, kept ABOVE the docstring
for _sp in _g.glob(_o.path.join(_o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))),
                                "venv", "lib", "python*", "site-packages")):
    if _sp not in _s.path:                       # so the shared body below is byte-identical with otv4's
        _s.path.insert(1, _sp)
"""
tests/check_condor_sibling_default.py  v1.0
v1.0  2026-10-03  CND.11 — A SIBLING-PROBE ERROR RETURNS THE CALLER'S DEFAULT.

  🔴 ExitEngine._condor_sibling_open(record, default) returned True in its
  except and ignored `default`. The stop path (exit_engine ~:1990) passes
  default=False so that a probe error leaves the 15% stop ARMED on a lone
  vertical; it got True, read "hedged", and SUPPRESSED the stop. Found by
  OTV4TEST's audit; shared.

  D1  probe raises, default=False -> False (the defect: True)
  D2  probe raises, default=True  -> True  (TP caller semantics unchanged)
  D3  no error, no sibling open   -> False (unchanged)

  Drives the REAL method with get_trade_logger patched to raise / to return an
  empty book. BORN RED on otv4 2220461 at D1.

Run:  python3 tests/check_condor_sibling_default.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


def main():
    from execution.exit_engine import ExitEngine
    from database import trade_logger as tl
    rec = {"trade_id": "leg1", "symbol": "QQQ", "option_side": "put",
           "is_condor_leg": 1}
    probe = ExitEngine._condor_sibling_open
    real = tl.get_trade_logger
    try:
        def _boom():
            raise RuntimeError("store unreadable")
        tl.get_trade_logger = _boom
        got = probe(object(), rec, default=False)
        check("D1 probe error + default=False -> False (stop stays armed)",
              got is False, f"got {got!r}")
        got = probe(object(), rec, default=True)
        check("D2 probe error + default=True -> True (TP caller unchanged)",
              got is True, f"got {got!r}")

        class _Empty:
            def get_open_trades(self):
                return []
        tl.get_trade_logger = lambda: _Empty()
        got = probe(object(), rec, default=True)
        check("D3 no sibling open -> False (unchanged)", got is False, f"got {got!r}")
    finally:
        tl.get_trade_logger = real
    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — a probe error returns what the caller asked for")
    return 0


if __name__ == "__main__":
    sys.exit(main())
