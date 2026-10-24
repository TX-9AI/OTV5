#!/usr/bin/env python3
"""
tests/check_fly_quote_log.py  v1.0
v1.0  2026-10-03  OTV4TEST r225 (FLY.2) — THE BUTTERFLIES RECORD THEIR LEGS' QUOTES AT THE PICK; NOTHING IS GATED.

  The operator, 2026-10-03, to "add the check as a log-only would-have-refused
  record for two weeks, then you decide whether it gates": "Yes" - and, on a
  no-bid wing: "I've bought contracts at mid with no bid plenty of times ...
  I'm not saying it isn't risky - only that it's possible."

  Q1  all three legs two-sided: no wing without a bid, neither rule refuses
  Q2  a NO-BID WING: counted (1), the strict rule would refuse, the role rule
      would NOT (a bought leg needs only an ask)
  Q3  the SOLD body with no bid: both rules would refuse
  Q4  a wing with no ask: both rules would refuse; unreadable quotes do not raise
  Q5  both plans declare the three checks and record them with NO verdict
      (ok=None) right after the wings are picked (a source check, stated as one)

Run:  python3 tests/check_fly_quote_log.py   (exit 0 green, 1 red)
"""
import ast
import glob as _glob
import os
import sys
import tempfile
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_fly_quote_log_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []
KEYS = ("quote_wings_no_bid", "quote_strict_would_refuse", "quote_role_would_refuse")


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def L(bid, ask):
    return types.SimpleNamespace(bid=bid, ask=ask)


def main():
    try:
        from strategy import gex_pin_butterfly as G
        from strategy import atp_butterfly_plan as A
        f = G.leg_quote_facts
        def t(d):
            return (d["wings_no_bid"], d["strict_would_refuse"], d["role_would_refuse"])
        check("Q1 three two-sided legs: no no-bid wing, neither rule would refuse",
              t(f(L(4.9, 5.1), L(2.5, 2.8), L(0.8, 0.9))) == (0.0, 0.0, 0.0), str(f(L(4.9, 5.1), L(2.5, 2.8), L(0.8, 0.9))))
        check("Q2 a no-bid wing: counted, strict would refuse, role would NOT",
              t(f(L(4.9, 5.1), L(2.5, 2.8), L(0.0, 0.9))) == (1.0, 1.0, 0.0), str(f(L(4.9, 5.1), L(2.5, 2.8), L(0.0, 0.9))))
        check("Q3 the sold body with no bid: both rules would refuse",
              t(f(L(4.9, 5.1), L(0.0, 2.8), L(0.8, 0.9))) == (0.0, 1.0, 1.0), str(f(L(4.9, 5.1), L(0.0, 2.8), L(0.8, 0.9))))
        bad = f(L(4.9, 0.0), L(2.5, 2.8), L(None, "x"))
        check("Q4 a wing with no ask: both would refuse; an unreadable quote counts as none and raises nothing",
              bad["strict_would_refuse"] == 1.0 and bad["role_would_refuse"] == 1.0 and bad["wings_no_bid"] == 1.0, str(bad))
        ok5 = all(k in G.GEXPinButterflyStrategy.PLAN_CHECKS for k in KEYS)
        ok5 = ok5 and all(k in A.ATPButterflyPlan.PLAN_CHECKS for k in KEYS)
        for mod, call in ((G, "leg_quote_facts(lower, center, upper)"), (A, "_gpb.leg_quote_facts(lo, center, up)")):
            src = open(mod.__file__).read()
            i = src.rfind(call)                               # the call site, not the def
            ok5 = ok5 and i > 0 and 't.check(f"quote_{_qk}", _qv, None)' in src[i:i + 200]
        check("Q5 both plans declare the three checks and record them with no verdict at the pick (source check)", ok5)
    except Exception as exc:                                  # noqa: BLE001
        for n in ("Q1", "Q2", "Q3", "Q4", "Q5"):
            if n not in FAILED:
                check(f"{n} (did not run)", False, f"{type(exc).__name__}: {exc}")
    if FAILED:
        print(f"\nRED — {len(set(FAILED))} check(s): {sorted(set(FAILED))}")
        return 1
    print("\nGREEN — the butterflies record their legs' quotes at the pick; nothing is gated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
