"""tests/check_low_price_symbols.py — v1.0
SOFI AND AAL ARE SELECTABLE, CONFIGURED AS THEIR CHAINS ACTUALLY TRADE, AND A
FRACTIONAL STRIKE INCREMENT IS NOT TRUNCATED.

v1.0  2026-09-25 — OTV4TEST r137. The operator: "I need AAL & SOFI to be
      selectable from configure.sh", then "Make sure we can get quotes for AAL
      and SOFI before you ship it". MEASURED FIRST, through the broker feed
      (/var/tmp/probe_quotes_sofi_aal.py, run by the operator 2026-09-24 night):
      both QUOTABLE - underlying and ATM option quotes live, 390 1m candles,
      nearest weekly 2026-09-25, $0.50 strikes near the money, tick rule $0.01
      below $3.00 / $0.05 above (TastyTrade's own). Cboe's public chain agreed.

  S1  configure.sh's tradeable list - read EXACTLY as change_instrument reads it
      (config.STRIKE_INCREMENTS keys) - offers SOFI and AAL
  S2  both at a 0.5 increment and in PENNY_CLASSES, with the $3.00 boundary the
      broker's tick rule names
  R1  round / floor / ceil give EXACTLY the pre-r137 values, INT TYPE INCLUDED,
      for every whole increment in the table across a dense price grid
  R2  a 0.5 increment is not truncated: 16.70 -> 16.5, 13.38 -> 13.5, floor
      16.70 -> 16.5, ceil 16.20 -> 16.5, and the ORB target helper agrees
  R3  the three runtime callers still resolve a real chain strike (the ORB
      plan's select_contract path is exercised on a 0.5 stub chain)
"""
from __future__ import annotations

import glob as _glob
import math
import os
import subprocess
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def guard(name, fn, detail=lambda: ""):
    try:
        ok = bool(fn())
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, "%s: %s" % (type(exc).__name__, exc))
        return
    try:
        d = detail()
    except Exception:                                           # noqa: BLE001
        d = ""
    check(name, ok, d)


# ── S1: the list configure.sh shows, by configure.sh's own expression ───────
_cfg = open(os.path.join(_root, "configure.sh"), encoding="utf-8").read()
_expr = "import config; print(' '.join(sorted(config.STRIKE_INCREMENTS)))"
guard("S1 configure.sh still reads its tradeable list from config.STRIKE_INCREMENTS",
      lambda: _expr in _cfg)
_r = subprocess.run([sys.executable, "-c", "import sys; sys.path[:0]=%r; " % sys.path[:3] + _expr],
                    capture_output=True, text=True, cwd=_root, timeout=60)
_allowed = _r.stdout.split()
guard("S1 the tradeable list offers SOFI and AAL", lambda: {"SOFI", "AAL"} <= set(_allowed),
      lambda: "%d symbols; stderr %s" % (len(_allowed), _r.stderr[-120:]))

import config                                                   # noqa: E402

guard("S2 SOFI and AAL at a 0.5 strike increment (measured $0.50 strikes)",
      lambda: config.STRIKE_INCREMENTS.get("SOFI") == 0.5 and config.STRIKE_INCREMENTS.get("AAL") == 0.5)
guard("S2 SOFI and AAL are penny class, boundary $3.00 (the broker's tick rule)",
      lambda: {"SOFI", "AAL"} <= config.PENNY_CLASSES and config.PRICE_INCREMENT_BOUNDARY == 3.00)

# ── R1 / R2: the helpers ─────────────────────────────────────────────────────
from utils import math_utils as mu                              # noqa: E402


def _old(fn, price, inc):
    return int(fn(price / inc) * inc)


_whole = sorted({v for v in config.STRIKE_INCREMENTS.values() if float(v).is_integer()})


def _r1():
    bad = []
    for inc in _whole:
        p = 1.0
        while p < 7000:
            for new, old in ((mu.round_to_strike(p, inc), _old(round, p, inc)),
                             (mu.floor_to_strike(p, inc), _old(math.floor, p, inc)),
                             (mu.ceil_to_strike(p, inc), _old(math.ceil, p, inc))):
                if new != old or type(new) is not int:
                    bad.append((inc, p, new, old))
            p = round(p * 1.0137 + 0.013, 4)
    return not bad, bad[:3]


guard("R1 whole increments (%s): identical values and int type across the price grid" % _whole,
      lambda: _r1()[0], lambda: str(_r1()[1]))
guard("R2 0.5 is not truncated: round 16.70->16.5, 13.38->13.5",
      lambda: mu.round_to_strike(16.70, 0.5) == 16.5 and mu.round_to_strike(13.38, 0.5) == 13.5)
guard("R2 0.5 floor 16.70->16.5, ceil 16.20->16.5, whole 17.0 stays int",
      lambda: mu.floor_to_strike(16.70, 0.5) == 16.5 and mu.ceil_to_strike(16.20, 0.5) == 16.5
      and type(mu.round_to_strike(16.9, 0.5)) is int and mu.round_to_strike(16.9, 0.5) == 17)


def _orb_target():
    up = mu.orb_strike_selection(16.9, 16.4, "long", 0.5)     # 16.9 + 0.5 = 17.4 -> 17.5
    dn = mu.orb_strike_selection(16.9, 16.4, "short", 0.5)    # 16.4 - 0.5 = 15.9 -> 16 (int)
    return up == 17.5 and dn == 16 and type(dn) is int, (up, dn)


guard("R2 orb_strike_selection lands on 0.5 strikes both ways (17.5 long, 16 short)",
      lambda: _orb_target()[0], lambda: str(_orb_target()[1]))

# ── R3: a real caller on a 0.5 chain ─────────────────────────────────────────
def _r3():
    from strategy import orb_plan as op

    class C:
        def __init__(self, k, t):
            self.strike, self.option_type, self.mark = k, t, 0.30
            self.bid, self.ask, self.delta, self.volume, self.open_interest = 0.29, 0.31, 0.5, 100, 100

    class Chain:
        calls = [C(k / 2, "C") for k in range(28, 40)]
        puts = [C(k / 2, "P") for k in range(28, 40)]
    long_k = mu.round_to_strike(16.9 + 0.6, 0.5)
    cl = op.select_contract(Chain(), "long", long_k)
    return long_k == 17.5 and cl is not None and cl.strike == 17.5, (long_k, getattr(cl, "strike", None))


guard("R3 the ORB plan's contract selection resolves the exact 0.5 strike", lambda: _r3()[0],
      lambda: str(_r3()[1]))

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
