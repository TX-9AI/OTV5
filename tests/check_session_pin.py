"""tests/check_session_pin.py — v5.0
v5.0  2026-10-25  OTV5 r9 (GATE.7) — new. Found by QQQ-TEST (MSG-QQQ-1025-04): the store-less sweep of r8 at 08:2x ET
      read four checkers red (check_levels_in_play, check_plan_prepares, check_tcs_fifty, check_tcs_plan), all
      green after 09:30 ET.
A PINNED SESSION OPEN REACHES THE PLAN THROUGH THE STRATEGY WRAPPER.

CD.2 bounds the trend and sweep plans' level reads by today's session open with no pre-open fallback
(tcs_plan / sweep_plan: `session_open_epoch or _session_open_epoch()`), and the checkers pin
session_open_epoch so they do not depend on the clock. They pass the pin to the STRATEGY wrappers
(TrendCreditSpread, SweepCreditSpreadStrategy), whose prepare / generate_signal swallowed it in **_ignored, so
before 09:30 ET the plans asked for rows from a future epoch and every fixture level was invisible.
This checker replaces plan.prepare with a spy (no store is opened), so it is red or green by the code alone, at any hour.

  P1  TrendCreditSpread.prepare forwards session_open_epoch to TCSPlan.prepare
  P2  TrendCreditSpread.generate_signal forwards it
  P3  SweepCreditSpreadStrategy.prepare forwards it
  P4  SweepCreditSpreadStrategy.generate_signal forwards it
  P5  with no pin, both wrappers forward 0.0 (a float, as plan.prepare's own default), so the live path
      still reads today's 09:30 ET
  P6  FIXTURE HYGIENE (QQQ-TEST MSG-QQQ-1025-05): every tests/check_*.py call of .prepare / .generate_signal on a
      name bound to TrendCreditSpread() or SweepCreditSpreadStrategy() carries session_open_epoch, as a keyword
      or inside a **dict(...) that names it. P1-P4 prove the wrapper forwards; P6 catches the next fixture that
      drives a wrapper without a pin, which is red only before 09:30 ET and so invisible to an afternoon run.
"""
from __future__ import annotations

import glob as _glob
import os
import sys
import tempfile
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

_tmp = tempfile.mkdtemp(prefix="check_session_pin_")
os.environ["OT_TRADES_DB"] = os.path.join(_tmp, "trades.db")

FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


PIN = 1_700_000_000.0


def _spy(strategy):
    seen = []

    def prepare(**kw):
        seen.append(kw)
        return types.SimpleNamespace(ready=False, unmet=True, structural=False, starved=False,
                                     tick=types.SimpleNamespace(already=lambda: None))
    strategy.plan.prepare = prepare
    return seen


from datetime import datetime                                  # noqa: E402
from zoneinfo import ZoneInfo                                  # noqa: E402

import strategy.sweep_credit_spread as scs                     # noqa: E402
import strategy.trend_credit_spread as tcs                     # noqa: E402

_now_et = datetime(2026, 9, 9, 13, 6, tzinfo=ZoneInfo("America/New_York"))

T = tcs.TrendCreditSpread()
seen = _spy(T)
T.prepare(ms=None, current_price=96.8, now_et=_now_et, session_open_epoch=PIN)
check("P1  TrendCreditSpread.prepare forwards session_open_epoch",
      bool(seen) and seen[-1].get("session_open_epoch") == PIN, f"got={seen[-1].get('session_open_epoch') if seen else None}")
T.generate_signal(ms=None, current_price=96.8, now_et=_now_et, session_open_epoch=PIN)
check("P2  TrendCreditSpread.generate_signal forwards session_open_epoch",
      len(seen) == 2 and seen[-1].get("session_open_epoch") == PIN, f"got={seen[-1].get('session_open_epoch') if seen else None}")
T.generate_signal(ms=None, current_price=96.8, now_et=_now_et)
_t_default = seen[-1].get("session_open_epoch")

S = scs.SweepCreditSpreadStrategy()
seen = _spy(S)
S.prepare(price_now=96.6, now_et="10:32", session_open_epoch=PIN)
check("P3  SweepCreditSpreadStrategy.prepare forwards session_open_epoch",
      bool(seen) and seen[-1].get("session_open_epoch") == PIN, f"got={seen[-1].get('session_open_epoch') if seen else None}")
S.generate_signal(price_now=96.6, now_et="10:32", session_open_epoch=PIN)
check("P4  SweepCreditSpreadStrategy.generate_signal forwards session_open_epoch",
      len(seen) == 2 and seen[-1].get("session_open_epoch") == PIN, f"got={seen[-1].get('session_open_epoch') if seen else None}")
S.generate_signal(price_now=96.6, now_et="10:32")
_s_default = seen[-1].get("session_open_epoch")

check("P5  no pin: both forward 0.0 (the live path reads today's 09:30 ET)",
      isinstance(_t_default, float) and _t_default == 0.0 and isinstance(_s_default, float) and _s_default == 0.0,
      f"tcs={_t_default!r} sweep={_s_default!r}")

import ast                                                     # noqa: E402

_WRAPPERS = ("TrendCreditSpread", "SweepCreditSpreadStrategy")


def _ctor_name(node):
    if isinstance(node, ast.Call):
        f = node.func
        return f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
    return None


def _dict_pins(node, dicts):
    # a **-splat carries the pin if it is dict(..., session_open_epoch=...) / {"session_open_epoch": ...},
    # dict(<name that does>, ...), or a name bound to one of those
    if isinstance(node, ast.Name):
        return dicts.get(node.id, False)
    if isinstance(node, ast.Dict):
        return any(isinstance(k, ast.Constant) and k.value == "session_open_epoch" for k in node.keys)
    if isinstance(node, ast.Call) and _ctor_name(node) == "dict":
        return (any(k.arg == "session_open_epoch" for k in node.keywords)
                or any(_dict_pins(a, dicts) for a in node.args))
    return False


def _unpinned(path):
    tree = ast.parse(open(path, encoding="utf-8").read(), path)
    wrappers, dicts, bad = set(), {}, []
    nodes = sorted((n for n in ast.walk(tree) if hasattr(n, "lineno")), key=lambda n: (n.lineno, n.col_offset))
    for n in nodes:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            if _ctor_name(n.value) in _WRAPPERS:
                wrappers.add(n.targets[0].id)
            elif isinstance(n.value, (ast.Call, ast.Dict)):
                dicts[n.targets[0].id] = _dict_pins(n.value, dicts)
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr in ("prepare", "generate_signal")
                and isinstance(n.func.value, ast.Name) and n.func.value.id in wrappers):
            ok = any(k.arg == "session_open_epoch" for k in n.keywords) or \
                any(k.arg is None and _dict_pins(k.value, dicts) for k in n.keywords)
            if not ok:
                bad.append(f"{os.path.basename(path)}:{n.lineno}")
    return bad


_bad, _seen = [], 0
for _p in sorted(_glob.glob(os.path.join(_root, "tests", "check_*.py"))):
    if os.path.basename(_p) == "check_session_pin.py":
        continue
    _src = open(_p, encoding="utf-8").read()
    if not any(w in _src for w in _WRAPPERS):
        continue
    _seen += 1
    _bad += _unpinned(_p)
check("P6  every fixture call of a trend/sweep wrapper carries session_open_epoch",
      _seen > 0 and not _bad, f"files={_seen} unpinned={_bad[:12]}")

print("\n%s — %d checks, %d failed" % ("GREEN" if not FAILED else "RED", len(RAN), len(FAILED)))
if FAILED:
    print("  failed: " + ", ".join(FAILED))
sys.exit(1 if FAILED else 0)
