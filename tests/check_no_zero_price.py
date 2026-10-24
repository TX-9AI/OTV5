#!/usr/bin/env python3
"""
tests/check_no_zero_price.py  v1.0

NO ORDER IS EVER PRICED AT $0.00 - entry ladder, exit ladder, combos.

v1.0  2026-09-27  OTV4TEST r164 (FILL.3). The operator, 2026-09-27: "We can NEVER bid
      or ask $0.00 - this is the one time that we may have to cross Mark. On our ladder
      exit and entries obviously started at the favorable side and start walking it but
      if Mark is ever zero, we have to skip that rung and go to the next one. This is the
      ONLY exception for getting a worse fill than mark." / "Entry AND exit ladder." /
      "Normally you'll see it when there is a positive and negative number in the
      spread & the broker asks 'are you wanting a debit or a credit'?"

DRIVES THE REAL LADDER (WA 21): execution/entry_ladder.rungs and LadderState, and the
exit path execution/ladder_registry.price_for (what ExitEngine._exit_limit calls).

  Z1  no rung is <= $0.00, over a grid of books (penny and nickel), buy and sell
  Z2  no POSTED price is <= $0.00 across a full walk with every rung refused
  Z3  the ruled exception is MINIMAL: a skipped zero posts exactly ONE increment
  Z3b ... and a table emptied by the skip holds exactly one increment (rungs() is read directly too)
  Z4  the unchanged path: books that never touched zero price exactly as at 2c5550b...
      (0.45/0.50, 0.00/1.00, 0.00/0.05 tables pinned)
  Z5  the EXIT path (ladder_registry.price_for) never posts $0.00 - including a combo
      whose net quote straddles zero, as position_manager clamps it (bid max(0, -0.05))
  Z6  a dead 0.00/0.00 book returns no price, and the callers' fallback
      (limit_at_mark with floor = one tick) posts one tick, not zero

BORN RED on 892852b (r163) at Z1, Z2, Z3, Z3b and Z5.
Run:  python3 tests/check_no_zero_price.py
"""
from __future__ import annotations

import glob as _glob
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The lander runs CHECKs under the SYSTEM python3 (no numpy/pytz): borrow the repo venv.
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
sys.path.insert(0, ROOT)
if not os.environ.get("OT_TRADES_DB"):
    _s = tempfile.mkdtemp(prefix="check_no_zero_price_", dir="/var/tmp" if os.path.isdir("/var/tmp") else None)
    os.environ["OT_TRADES_DB"] = os.path.join(_s, "t.db")
    os.environ["OT_DERIVED_DB"] = os.path.join(_s, "d.db")
    os.environ["OT_RESTING_DB"] = os.path.join(_s, "r.db")
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
import logging
logging.disable(logging.CRITICAL)

FAIL: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        FAIL.append(name.split()[0])


print("=" * 68)
print("NO $0.00 ORDER PRICE - entry ladder, exit ladder, combos")
print("=" * 68)

from execution.entry_ladder import rungs, LadderState, _increment      # noqa: E402
from execution import ladder_registry as lr                            # noqa: E402
from execution.limit_ladder import limit_at_mark                        # noqa: E402

# QQQ is a penny class; a symbol off the penny list takes the nickel grid under $3.
SYMS = ("QQQ", "ZZNICKEL")
BOOKS = [(0.00, 0.01), (0.00, 0.02), (0.00, 0.03), (0.00, 0.04), (0.00, 0.05), (0.00, 0.10),
         (0.01, 0.02), (0.01, 0.05), (0.00, 0.15), (0.05, 0.10), (0.00, 1.00), (0.45, 0.50)]

# ── Z1 / Z2 / Z3 ─────────────────────────────────────────────────────────────
z1, z2, z3 = [], [], []
for sym in SYMS:
    for b, a in BOOKS:
        mark = (a + b) / 2
        inc = _increment(sym, mark, b, a)
        for side in ("buy", "sell"):
            t = rungs(b, a, side, sym)
            if any(r <= 1e-9 for r in t):
                z1.append((sym, b, a, side, t))
            L = LadderState(side, sym); seen = []
            for _ in range(40):
                got = L.next_price(b, a)
                if got is None:
                    break
                seen.append(got[0]); L.refuse(got[0])
            if any(p <= 1e-9 for p in seen):
                z2.append((sym, b, a, side, seen[:6]))
            snapped_mark_zero = (side == "buy" and int(mark / inc + 1e-9) == 0)
            if snapped_mark_zero and seen and abs(seen[0] - inc) > 1e-9:
                z3.append((sym, b, a, side, seen[0], inc))
check("Z1 no ladder rung is <= $0.00 (penny + nickel grids, buy + sell)", not z1, str(z1[:3]))
check("Z2 no posted price is <= $0.00 across a full refused walk", not z2, str(z2[:3]))
check("Z3 a skipped zero posts exactly ONE increment (the minimal exception)", not z3, str(z3[:3]))
# Z3b - the TABLE too, not only the posted price: rungs() is also read directly
# (strategy/condor_roll.py), and a first cut of this gate let a two-increment table
# survive because next_price's take-mark clamp hid it (mutant M4, r164).
t3b = rungs(0.00, 0.01, "buy", "QQQ")
check("Z3b a table emptied by the zero skip holds exactly ONE increment", t3b == [0.01], f"rungs={t3b}")

# ── Z4 the unchanged path, pinned from 892852b ───────────────────────────────
GOLD = {("QQQ", 0.45, 0.50, "buy"): [0.46, 0.47], ("QQQ", 0.45, 0.50, "sell"): [0.49, 0.48],
        ("QQQ", 0.00, 0.05, "buy"): [0.01, 0.02], ("QQQ", 0.00, 0.05, "sell"): [0.04, 0.03],
        ("QQQ", 0.00, 1.00, "sell"): [round(0.75 - 0.01 * i, 2) for i in range(24)] + [0.5]}
bad = {k: rungs(k[1], k[2], k[3], k[0]) for k in GOLD if rungs(k[1], k[2], k[3], k[0]) != GOLD[k]}
check("Z4 books that never touch zero price exactly as before", not bad, str(bad))

# ── Z5 the exit path, incl. a combo straddling zero ──────────────────────────
z5 = []
cases = [("close-single", "buy", 0.00, 0.01), ("close-single", "buy", 0.00, 0.02),
         ("close-combo", "buy", max(0.0, 0.00 - 0.05), 0.05 - 0.00),   # net -0.05 / +0.05, clamped
         ("close-combo2", "buy", max(0.0, -0.02), 0.03)]
for tag, side, b, a in cases:
    key = lr.intent_key(f"zz-{tag}", "close", tag)
    walked = 0
    for _ in range(12):
        got = lr.price_for(key, side, b, a, "QQQ")
        if not got:
            break
        walked += 1
        if got[0] <= 1e-9:
            z5.append((tag, b, a, got)); break
        lr.refuse(key, got[0])          # a raise here is a real failure, not a skipped walk
    if walked < 1:
        z5.append((tag, "walked nothing - the case tested no price"))
check("Z5 the exit ladder (ladder_registry.price_for) never posts $0.00, combos included", not z5, str(z5))

# ── Z6 dead book ─────────────────────────────────────────────────────────────
dead = rungs(0.0, 0.0, "buy", "QQQ")
fb = limit_at_mark(0.0, floor=0.01)
check("Z6 a dead 0.00/0.00 book gives no rung, and the fallback posts one tick",
      dead == [] and fb >= 0.01 - 1e-9, f"rungs={dead} fallback={fb}")

print()
if FAIL:
    print(f"RED - {len(FAIL)} failed: {sorted(set(FAIL))}")
    sys.exit(1)
print("GREEN - no order is priced at $0.00")
sys.exit(0)
