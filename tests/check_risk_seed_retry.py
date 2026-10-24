#!/usr/bin/env python3
# tests/check_risk_seed_retry.py  v1.0
# v1.0  2026-10-03  OTV4TEST r190 (AUD.1) — shared with otv4 CND.12. Everything after the closing
#       docstring is byte-identical with otv4's gate; these lines and the r106 venv bootstrap sit ABOVE
#       the docstring so the body hash holds and the lander (system python3) can import the modules.
import glob as _g, os as _o, sys as _s          # OTV4TEST: r106 venv bootstrap, kept ABOVE the docstring
for _sp in _g.glob(_o.path.join(_o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))),
                                "venv", "lib", "python*", "site-packages")):
    if _sp not in _s.path:                       # so the shared body below is byte-identical with otv4's
        _s.path.insert(1, _sp)
"""
tests/check_risk_seed_retry.py  v1.0
v1.0  2026-10-03  CND.12 — A FAILED BOOT SEED IS RETRIED, AND SAID.

  🔴 RiskManager._ensure_seeded set _seeded=True BEFORE reading today's P&L
  and swallowed the exception, so one unreadable DB at boot left the session
  P&L at 0 with no retry. Found by OTV4TEST's audit; shared. (is_halted is
  unaffected — it re-reads the DB on every call.)

  R1  the first read fails -> not marked seeded, and a WARNING is logged
  R2  the next call retries and seeds the real P&L
  R3  a loss past the limit on the retry latches the halt flag

  Drives the REAL method with get_trade_logger patched. BORN RED on otv4
  2220461 at R1 R2 R3.

Run:  python3 tests/check_risk_seed_retry.py
"""
import logging
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
    from risk.risk_manager import RiskManager
    from database import trade_logger as tl
    rm = RiskManager()
    limit = rm._daily_loss_limit
    real = tl.get_trade_logger
    records = []
    h = logging.Handler()
    h.emit = lambda r: records.append(r)
    lg = logging.getLogger("risk.risk_manager")
    lg.addHandler(h)
    try:
        def _boom():
            raise RuntimeError("store unreadable")
        tl.get_trade_logger = _boom
        rm._ensure_seeded()
        warned = any(r.levelno >= logging.WARNING for r in records)
        check("R1 a failed read is NOT marked seeded, and warns",
              rm._seeded is False and warned, f"seeded={rm._seeded} warned={warned}")

        class _Book:
            def today_summary(self):
                return {"total_pnl": -(limit + 50.0)}
        tl.get_trade_logger = lambda: _Book()
        rm._ensure_seeded()
        check("R2 the next call retries and seeds the real P&L",
              rm._seeded is True and abs(rm._session_pnl_usd + limit + 50.0) < 1e-9,
              f"seeded={rm._seeded} pnl={rm._session_pnl_usd}")
        check("R3 a loss past the limit on the retry latches the halt flag",
              rm._session_halted is True, f"halted={rm._session_halted}")
    finally:
        tl.get_trade_logger = real
        lg.removeHandler(h)
    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — the boot seed retries until it reads, and says when it cannot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
