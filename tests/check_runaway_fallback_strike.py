#!/usr/bin/env python3
"""
tests/check_runaway_fallback_strike.py  v1.0 (OTV4TEST)
v1.0  2026-10-18  OTV4TEST r289 — MIRROR of otv4 r492 0bd66e9's checker (sha256 1ce01879), adapted to this tree: F8
      reads OUR two callers (strategy/runaway_plan.py, strategy/liquidity_hunt.py - this tree's RunawayContinuation
      delegates to its plan); F5b runs F5 at the Runaway plan's run x band (0.5 / 1.0 / 1.5); F9 (new) is the Hunt -
      the UNH chain over a runway picks nothing and the Hunt declines naming the nearest survivor.
v1.0  2026-10-17  r492 / RUN.9 — THE FALLBACK STRIKE IS THE FIRST OTM OR NOTHING.

  UNH 2026-10-16 09:42 ET: "[runaway] FIRE short — buy 380P at 0.07  δ 0.02 ...
  over a 5.23 run (1 strikes considered)", spot 396.565, x161, stopped in 27 s,
  -$322. Every nearer put failed r174's spread floor, and gamma_leverage_pick's
  "else the first OTM strike" took the nearest SURVIVOR instead, 16.5 out.

  Drives the REAL strategy.runaway_continuation.gamma_leverage_pick:
  F1  the UNH chain picks NOTHING (the bug bought 380P)
  F2  the refusal note names the nearest strike that passed and its distance
  F3  the chain's first OTM strike, outside the run but a candidate, is still
      the fallback (calls and puts)
  F4  first OTM fails and the next strike passes, run too short for either:
      NOTHING (kills "nearest survivor under another name", OTV4TEST critique 1)
  F5  inside the run the pick is identical to the pre-r492 algorithm on 400
      seeded chains (OTV4TEST critique 5)
  F6  the early returns give 4 values (OTV4TEST critique 3)
  F7  the long (call) mirror of the UNH chain picks nothing
  F8  both callers here (the Runaway plan, the Hunt) pass note= and DECLINE with it (AST)
  F5b F5 at the plan's run x band (0.5, 1.0, 1.5): identical inside the band
  F9  the Hunt's own call (runway as the reach) on the UNH chain: nothing, and a note naming 380

Run:  python3 tests/check_runaway_fallback_strike.py   (exit 0 green, 1 red)
"""
import ast
import glob as _glob
import os
import random
import sys
from types import SimpleNamespace as C

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
os.environ.setdefault("OT_INSTRUMENT", "UNH")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _old_pick(contracts, direction, spot, run, floor_pct=0.20):
    """The pre-r492 selection, verbatim but for its fallback (F5 compares
    only chains with a candidate inside the run, where the two must agree)."""
    cands = []
    for c in contracts:
        k = float(c.strike)
        prem = float(c.ask or 0) or float(c.mark or 0)
        bid, d, g = float(c.bid or 0), abs(float(c.delta or 0)), float(c.gamma or 0)
        otm = (k > spot) if direction == "long" else (k < spot)
        if not otm or prem <= 0.05 or d <= 0:
            continue
        if bid <= 0 or (floor_pct * prem) <= (prem - bid):
            continue
        dist = abs(k - spot)
        cands.append((((d * run + 0.5 * g * run * run) / prem), -dist, dist, c))
    inside = [x for x in cands if x[2] <= run]
    if not inside:
        return None
    return max(inside, key=lambda x: (x[0], x[1]))[3]


def _unh_puts():
    # 395..381: wide (bid 0.40 / ask 0.60 -> 20% floor 0.12 <= spread 0.20)
    out = [C(strike=float(k), bid=0.40, ask=0.60, mark=0.50, delta=-0.30 + 0.015 * (395 - k),
             gamma=0.03) for k in range(395, 380, -1)]
    out.append(C(strike=380.0, bid=0.06, ask=0.07, mark=0.065, delta=-0.02, gamma=0.005))
    out.append(C(strike=397.5, bid=2.0, ask=2.1, mark=2.05, delta=-0.55, gamma=0.04))  # ITM
    return out


def main():
    from strategy import runaway_continuation as rc
    pick = rc.gamma_leverage_pick

    c = pick(_unh_puts(), "short", 396.565, 5.23, floor_pct=0.20)[0]
    check("F1 the UNH 10-16 chain picks nothing", c is None,
          f"picked {getattr(c, 'strike', None)} (the bug: 380P x161)")
    note = []
    try:
        pick(_unh_puts(), "short", 396.565, 5.23, floor_pct=0.20, note=note)
    except TypeError as e:
        note = [f"(no note= parameter: {e})"]
    check("F2 the refusal note names 380 and its distance",
          bool(note) and "380" in note[0] and "16.5" in note[0], f"note={note!r}")

    # F3: 1-point strikes, first OTM 396 is a candidate, the run (0.30) reaches none
    puts = [C(strike=float(k), bid=1.00, ask=1.05, mark=1.02, delta=-0.40, gamma=0.05)
            for k in (396, 395, 394)]
    c3 = pick(puts, "short", 396.565, 0.30)[0]
    check("F3 put: the chain's first OTM (396) is still the fallback",
          c3 is not None and c3.strike == 396.0, f"picked {getattr(c3, 'strike', None)}")
    calls = [C(strike=float(k), bid=1.00, ask=1.05, mark=1.02, delta=0.40, gamma=0.05)
             for k in (397, 398, 399)]
    c3b = pick(calls, "long", 396.565, 0.30)[0]
    check("F3b call: the chain's first OTM (397) is still the fallback",
          c3b is not None and c3b.strike == 397.0, f"picked {getattr(c3b, 'strike', None)}")

    # F4: first OTM 396 fails the spread, 395 passes, the run reaches neither
    puts4 = [C(strike=396.0, bid=0.40, ask=0.60, mark=0.50, delta=-0.45, gamma=0.05),
             C(strike=395.0, bid=0.98, ask=1.00, mark=0.99, delta=-0.38, gamma=0.05)]
    c4 = pick(puts4, "short", 396.565, 0.30)[0]
    check("F4 first OTM fails, next passes, run reaches neither: nothing",
          c4 is None, f"picked {getattr(c4, 'strike', None)} (nearest survivor)")

    # F5: inside the run, identical to the old algorithm
    rng = random.Random(4920)
    same = tried = 0
    bad = None
    for _ in range(400):
        spot = 100 + rng.random() * 300
        step = rng.choice((0.5, 1.0, 2.5, 5.0))
        direction = rng.choice(("long", "short"))
        run = rng.random() * 6 + 0.1
        base = (spot // step) * step
        ch = []
        for i in range(-3, 15):
            k = base + i * step if direction == "long" else base - i * step + step
            ask = round(max(0.06, rng.random() * 4), 2)
            bid = round(ask * rng.choice((0.0, 0.5, 0.85, 0.95)), 2)
            ch.append(C(strike=k, bid=bid, ask=ask, mark=(ask + bid) / 2,
                        delta=rng.random() * 0.6, gamma=rng.random() * 0.1))
        want = _old_pick(ch, direction, spot, run)
        if want is None:
            continue
        tried += 1
        got = pick(ch, direction, spot, run)[0]
        if got is want:
            same += 1
        elif bad is None:
            bad = (spot, direction, run, getattr(got, "strike", None), want.strike)
    check(f"F5 inside the run: identical pick on {tried} chains",
          tried >= 100 and same == tried, f"{same}/{tried} same; first diff {bad}")

    r0, rx = pick(_unh_puts(), "short", 396.565, 0.0), pick(_unh_puts(), "short", "x", 1.0)
    check("F6 the early returns give 4 values", len(r0) == 4 and len(rx) == 4,
          f"run=0 -> {r0!r}; spot='x' -> {rx!r}")

    calls7 = [C(strike=float(k), bid=0.40, ask=0.60, mark=0.50, delta=0.30, gamma=0.03)
              for k in range(397, 413)]
    calls7.append(C(strike=413.0, bid=0.06, ask=0.07, mark=0.065, delta=0.02, gamma=0.005))
    c7 = pick(calls7, "long", 396.565, 5.23)[0]
    check("F7 the call mirror of the UNH chain picks nothing", c7 is None,
          f"picked {getattr(c7, 'strike', None)}")

    res = {}
    for f in ("runaway_plan.py", "liquidity_hunt.py"):           # OTV4TEST: this tree's two callers
        src = open(os.path.join(_root, "strategy", f)).read()
        tree = ast.parse(src)
        passes_note = uses_note = False
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "gamma_leverage_pick":
                passes_note = passes_note or any(k.arg == "note" for k in n.keywords)
            if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "append":
                seg = ast.get_source_segment(src, n) or ""
                uses_note = uses_note or ("why_none[0]" in seg and "contract" in seg)
        res[f] = (passes_note, uses_note)
    check("F8 both callers (the Runaway plan, the Hunt) pass note= and DECLINE with it",
          all(a and b for a, b in res.values()), f"{res}")

    # F5b: the Runaway plan hands the picker run x band (runaway_plan.band_for: 0.5 / 1.0 / 1.5)
    rng = random.Random(4921)
    same = tried = 0
    bad = None
    for _ in range(300):
        spot = 100 + rng.random() * 300
        step = rng.choice((0.5, 1.0, 2.5, 5.0))
        direction = rng.choice(("long", "short"))
        run = (rng.random() * 6 + 0.1) * rng.choice((0.5, 1.0, 1.5))
        base = (spot // step) * step
        ch = []
        for i in range(-3, 15):
            k = base + i * step if direction == "long" else base - i * step + step
            ask = round(max(0.06, rng.random() * 4), 2)
            bid = round(ask * rng.choice((0.0, 0.5, 0.85, 0.95)), 2)
            ch.append(C(strike=k, bid=bid, ask=ask, mark=(ask + bid) / 2,
                        delta=rng.random() * 0.6, gamma=rng.random() * 0.1))
        want = _old_pick(ch, direction, spot, run)
        if want is None:
            continue
        tried += 1
        got = pick(ch, direction, spot, run)[0]
        if got is want:
            same += 1
        elif bad is None:
            bad = (spot, direction, run, getattr(got, "strike", None), want.strike)
    check(f"F5b at run x band: identical pick on {tried} chains",
          tried >= 80 and same == tried, f"{same}/{tried} same; first diff {bad}")

    # F9: the Hunt calls the same picker with its runway (spot -> target) as the reach
    note9 = []
    c9 = pick(_unh_puts(), "short", 396.565, 4.0, floor_pct=0.20, note=note9)[0]
    check("F9 the Hunt's call (runway 4.0) on the UNH chain: nothing, and the note names 380",
          c9 is None and bool(note9) and "380" in note9[0], f"picked {getattr(c9, 'strike', None)} note={note9!r}")

    print()
    if FAILED:
        print(f"RED: {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
