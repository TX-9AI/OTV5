#!/usr/bin/env python3
"""tests/check_entry_underwater.py — v1.1

v1.1  2026-10-15  OTV4TEST r287 (CFDIR.1) — OT_COUNTERFACTUAL_DIR is set to a scratch directory before
      main is imported. Driving the entry path writes caution_size.jsonl (analysis/commitment.py, COMMIT.3)
      once the day has a first loss, and with nothing set that is the repo's data/counterfactual - the
      LIVE log when run in the live tree. Found on r286's build 2026-10-15 (14 rows in a worktree after
      the 10:00 loss); the operator, 2026-10-15 17:25 ET: "Yes" (to building the check_entry_underwater fix). No check changed.
NO TRADE OPENS ALREADY THROUGH ITS OWN STOP (ENT.1).

v1.0  2026-09-19  OTV4TEST r61 — built for the operator's ENT.1 ruling: STRICT
      (at or beyond the stop is through) and UNCONDITIONAL (*"any strategy…it
      should NEVER happen"*). Drives `main._execute_entry_signal`, the one
      function every entry opens through, with a spy on `entry_engine.enter`,
      and asks whether the ORDER WAS PLACED rather than whether the source
      contains a guard (§21). Born red 5 of 10 at 375dd68.

Operator's ruling, 2026-09-19: *"any strategy check on the firing tick one final
time that the entry is not crossing the stop before the trade even opens — not
that it would happen often otherwise, but that it should NEVER happen."* STRICT:
at or beyond the stop is through. No band, no constant.

🔑 IT DRIVES `main._execute_entry_signal` AND ASKS WHETHER THE ORDER WAS PLACED.
Not whether the source contains a guard — WORKING_AGREEMENT 21: twelve tests once
asserted the source text held a call whose NAME WAS NEVER BOUND, over a NameError
that crash-looped every box. The probe here is a spy on `entry_engine.enter`:
refused means `enter` was never reached.

⚠️ THE FIXTURES ARE VALID SIGNALS FIRST. A signal that fails `is_valid` is refused
one branch EARLIER, for a different reason, and every case would pass vacuously —
the §21 trap wearing this revision's clothes. E0 proves the fixture fires when it
is not underwater, so a refusal downstream means the guard and nothing else.

  E0  a clean long fires          (the fixture is not self-refuting)
  E1  long, price BELOW its stop        -> REFUSED
  E1b short, price ABOVE its stop       -> REFUSED
  E2  STRICT: price EXACTLY the stop    -> REFUSED   (no band, no tolerance)
  E3  control: clean short fires
  E4  control: a THESIS stop (LiquidityHunt) fires though it is "through"
  E5  control: no underlying stop at all (runaway/credit shape) fires
  E6  LiquidityHunt DECLARES the opt-out, as an assignment (§20, not a mention)
  E7  OptionsSignal defaults to CHECKED — the opt-out is opt-OUT
  E8  one funnel: `enter(signal=` appears exactly once in main.py

Born red at 375dd68 (r60) on E1, E1b, E2. E0/E3/E4/E5/E7/E8 are CONTROLS, green
on both sides; E6 is red at base because the declaration does not exist there.
Run:  python3 tests/check_entry_underwater.py
"""
import ast
import os
import sys
import tempfile
os.environ.setdefault("OT_COUNTERFACTUAL_DIR", tempfile.mkdtemp(prefix="cf_", dir="/var/tmp"))   # r287: never the live log

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def guard(name, fn, detail=""):
    """r39 — a checker that DIES cannot say which behaviour is absent, and reads
    identically to a checker that is simply broken. Any escape becomes a RED."""
    try:
        ok = fn()
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"{type(exc).__name__}: {exc}")
        return
    check(name, bool(ok), detail() if callable(detail) else detail)


import main                                                     # noqa: E402
from strategy.base_strategy import OptionsSignal                # noqa: E402


class _Sizing:
    allowed = True
    contracts = 1
    total_cost = 100.0
    reject_reason = None


class _Risk:
    def size_for(self, *a, **kw):
        return _Sizing()


class _Spy:
    """Records whether the order was placed. `enter` returns None so nothing
    downstream of it runs — this check is about reaching it, not about filling."""
    def __init__(self):
        self.entered = []

    def enter(self, signal=None, sizing=None, **kw):
        self.entered.append(getattr(signal, "strategy_name", "?"))
        return None


class _Macro:
    butterfly_half_size = False


class _State:
    paper_trading = True


def _sig(direction, price, stop, *, name="ORBStrategy", thesis=False):
    s = OptionsSignal(
        strategy_name=name,
        setup_type="fixture",
        direction=direction,
        option_side="call" if direction == "long" else "put",
        underlying_entry=float(price),
        underlying_stop=float(stop),
        strike=100.0,
        entry_premium=1.25,
    )
    if thesis:
        s.underlying_stop_is_thesis = True
    return s


def _fired(signal, price):
    """Drive the REAL funnel. True if the order was placed."""
    spy = _Spy()
    _gr, _ge = main.get_risk_manager, main.get_entry_engine
    main.get_risk_manager = lambda *a, **kw: _Risk()
    main.get_entry_engine = lambda *a, **kw: spy
    try:
        main._execute_entry_signal(
            signal, {"price": float(price), "macro": _Macro()},
            None, _State(), None, additive=True)
    finally:
        main.get_risk_manager, main.get_entry_engine = _gr, _ge
    return bool(spy.entered)


print("  ENT.1 — no trade opens already through its own stop")

guard("E0 a clean long fires (the fixture is not self-refuting)",
      lambda: _fired(_sig("long", 100.0, 99.0), 100.0))
guard("E1 long with price BELOW its own stop is REFUSED",
      lambda: not _fired(_sig("long", 100.0, 101.0), 100.0))
guard("E1b short with price ABOVE its own stop is REFUSED",
      lambda: not _fired(_sig("short", 100.0, 99.0), 100.0))
guard("E2 STRICT — price EXACTLY at the stop is REFUSED",
      lambda: not _fired(_sig("long", 100.0, 100.0), 100.0))
guard("E3 control: a clean short fires",
      lambda: _fired(_sig("short", 100.0, 101.0), 100.0))
guard("E4 control: a THESIS stop fires though price is beyond it",
      lambda: _fired(_sig("long", 100.0, 101.0, name="LiquidityHunt",
                          thesis=True), 100.0))
guard("E5 control: no underlying stop at all still fires",
      lambda: _fired(_sig("long", 100.0, 0.0, name="RunawayContinuation"), 100.0))


def _hunt_declares():
    src = open(os.path.join(_root, "strategy", "liquidity_hunt.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if (isinstance(t, ast.Attribute)
                        and t.attr == "underlying_stop_is_thesis"
                        and isinstance(n.value, ast.Constant)
                        and n.value.value is True):
                    return True
    return False


guard("E6 LiquidityHunt DECLARES the opt-out as an assignment", _hunt_declares)
guard("E7 OptionsSignal defaults to CHECKED (the opt-out is opt-OUT)",
      lambda: OptionsSignal().underlying_stop_is_thesis is False)


def _one_funnel():
    src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    return src.count("enter(signal=") == 1


guard("E8 one funnel — main.py places an order in exactly one place", _one_funnel)

print()
if FAILED:
    print(f"  RED — {len(FAILED)} of {len(RAN)} failed: " + ", ".join(FAILED))
    sys.exit(1)
print(f"  GREEN — {len(RAN)} checks")
