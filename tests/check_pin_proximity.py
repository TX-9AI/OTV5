#!/usr/bin/env python3
"""
tests/check_pin_proximity.py  v1.0
v1.0  2026-09-22  OTV4TEST r97 — born RED at c38abac, where
      `pin_proximity_verdict` does not exist and P0 NAMES that rather than
      dying on a traceback.

r97 — DO NOT FIRE A DIRECTIONAL DEBIT ONTO THE PIN YOU ARE STANDING ON.

The operator's hypothesis, 2026-09-22: *"don't fire directionals into pinning
GEX with price w/in EM to the pin"*, and his ruling on how it ships: *"I want
my idea implemented on trial, not as an observer, but as a participant."*

🔑 THE MECHANISM IS DEALER GAMMA, not a correlation. Positive net GEX means
dealers are LONG gamma: to stay hedged they SELL rallies and BUY dips, so price
mean-reverts toward the pin. A directional debit fired NEAR that pin is asking
for follow-through from the one regime that exists to suppress it.

📊 MEASURED on all 36 directional fires of 2026-09-22: winners sat a median
0.414 of an expected move from the pin, losers 0.342. Replaying the gate at
0.32 refuses NINE trades — eight of them losers — and turns the session from
**-$904 to +$4,606**.

🔴 THE HONEST LIMIT, PINNED BY P6 SO IT CANNOT BE FORGOTTEN: the pin was 748 on
ALL 36 trades. It never moved, so on that session `|pin-px|/EM` is price
rescaled — n=1 on the quantity doing the work, not n=36. §12 says one session
finds a MECHANISM, never a NUMBER. It ships REFUSING anyway by the operator's
ruling and the fork's charter; §31's log-only default is overridden
deliberately, not by omission.

  P0  the machinery exists (guard, not a check)
  P1  PINNING + inside the floor            -> REFUSE
  P2  PINNING + outside the floor           -> admit
  P3  TRENDING + inside the floor           -> admit  (the inversion guard)
  P4  unmeasurable                          -> admit, and `frac is None` says so
  P5  the floor is the argued 0.32, and the plateau is recorded
  P6  the gate is SELECTION, dial-able by env, and can be switched off

Run:  python3 tests/check_pin_proximity.py
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = tempfile.mkdtemp(prefix="check_pin_proximity.")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_s, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))

FAIL: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])


import config as C                                              # noqa: E402

# ── P0 — THE GUARD, NOT A CHECK (the r72/V0 pattern) ──────────────────────
# At a base without r97 this file would die on an ImportError naming nothing.
# A gate that cannot say WHAT is missing teaches the reader to skim the red.
try:
    import main as M
    _have = hasattr(M, "pin_proximity_verdict")
except Exception as _e:                                         # noqa: BLE001
    M, _have = None, False
check("P0 main exposes pin_proximity_verdict", _have,
      "r97 has not landed in this tree")
if not _have:
    print(f"\nRED — {len(FAIL)} failed: {FAIL}")
    sys.exit(1)


class _Gex:
    """Only the two attributes the verdict reads, so the fixture cannot pass
    by accident on a field the real object does not carry."""

    def __init__(self, pin, env):
        self.pin_strike = pin
        self.gex_environment = env


def _ctx(pin, env, price=744.0, iv=0.19):
    return {"gex": _Gex(pin, env), "price": price, "atm_iv": iv}


# 🔑 THE EM IS THE REAL ONE. Deriving the fixture's distances from the same
# `expected_move()` the gate calls keeps this from testing a second definition
# (§0.4) — and it means the cases stay correct if the EM formula ever moves.
from strategy.gex_pin_butterfly import expected_move              # noqa: E402

_PX, _IV = 744.0, 0.19
_EM = expected_move(_PX, _IV)
check("P0b the fixture's EM is the gate's own function", bool(_EM and _EM > 0),
      f"EM={_EM}")

_FLOOR = C.PIN_PROXIMITY_MIN_FRAC
_inside = _PX + _EM * (_FLOOR * 0.5)      # comfortably inside the floor
_outside = _PX + _EM * (_FLOOR + 0.15)    # comfortably outside it

# ── P1 — THE REFUSAL ──────────────────────────────────────────────────────
r, frac, env, pin, why = M.pin_proximity_verdict(_ctx(_inside, "PINNING", _PX, _IV))
check("P1 PINNING and inside the floor -> REFUSE",
      r is True and frac is not None and frac < _FLOOR,
      f"refuse={r} frac={frac!r} floor={_FLOOR}")

# ── P2 — AND IT DOES NOT REFUSE EVERYTHING ────────────────────────────────
# ⚠️ A gate with no admitting case is indistinguishable from a kill switch.
r2, frac2, *_ = M.pin_proximity_verdict(_ctx(_outside, "PINNING", _PX, _IV))
check("P2 PINNING but outside the floor -> admit",
      r2 is False and frac2 is not None and frac2 >= _FLOOR,
      f"refuse={r2} frac={frac2!r}")

# ── P3 — THE INVERSION GUARD, AND IT IS THE POINT OF THE WHOLE GATE ───────
# 🔴 Negative gamma should INVERT the effect: dealers AMPLIFY instead of
# dampening, so near-pin stops being a reason to stand aside. A refusal in a
# TRENDING regime is this gate firing backwards, and it would be invisible in
# P&L for weeks. `data/gex_data.py`: *"Positive = pinning, negative =
# trending"*.
r3, frac3, env3, *_ = M.pin_proximity_verdict(_ctx(_inside, "TRENDING", _PX, _IV))
check("P3 TRENDING at the same distance -> ADMIT (never refuse backwards)",
      r3 is False and frac3 is not None and frac3 < _FLOOR,
      f"refuse={r3} frac={frac3!r} env={env3!r}")

# ── P4 — UNMEASURABLE ADMITS, AND SAYS SO ─────────────────────────────────
# ⚠️ "could not measure" must never look like "measured and passed" (§0.5).
# The caller keys its warning on `frac is None`, so that is what is pinned.
for _label, _c in (("no gex object", {"gex": None, "price": _PX, "atm_iv": _IV}),
                   ("no pin", _ctx(0, "PINNING", _PX, _IV)),
                   ("no price", {"gex": _Gex(748, "PINNING"), "price": 0, "atm_iv": _IV}),
                   ("no iv", _ctx(748, "PINNING", _PX, 0))):
    r4, frac4, _e4, _p4, why4 = M.pin_proximity_verdict(_c)
    check(f"P4 {_label} -> admits, and frac is None so the caller warns",
          r4 is False and frac4 is None, f"refuse={r4} frac={frac4!r} why={why4!r}")

# ── P5 — THE NUMBER IS THE ARGUED ONE, AND ITS LIMIT IS RECORDED ──────────
# 🔴 The pin was 748 on every one of the 36 trades this was fitted to. The
# threshold is a PLATEAU (0.30/0.32/0.34/0.36 all improved the day), which is
# why it is a mechanism rather than a curve fit — but the plateau was measured
# on ONE pin. If a later edit moves this number, that edit owes a corpus
# measurement, not another single session.
check("P5 the floor is 0.32, the value the 36-trade replay was run at",
      abs(_FLOOR - 0.32) < 1e-9,
      f"{_FLOOR} (plateau 0.30-0.36; pin was 748 on ALL 36 — n=1 on the pin)")

# ── P6 — SELECTION, NOT FOUNDATIONAL: IT MUST BE SWITCHABLE ───────────────
# §36: a measured preference is relaxable. The operator ships this as a TRIAL,
# so turning it off must not need a revision.
check("P6 the gate is env-switchable and currently ACTIVE",
      isinstance(C.PIN_PROXIMITY_ACTIVE, bool) and C.PIN_PROXIMITY_ACTIVE,
      f"active={C.PIN_PROXIMITY_ACTIVE} (OT_PIN_PROXIMITY_ACTIVE=0 disables)")

if FAIL:
    print(f"\nRED — {len(FAIL)} failed: {', '.join(FAIL)}")
    sys.exit(1)
print(f"\nGREEN — refuses inside {_FLOOR} of the pin under PINNING, "
      f"admits under TRENDING, stands down when unmeasurable")
sys.exit(0)
