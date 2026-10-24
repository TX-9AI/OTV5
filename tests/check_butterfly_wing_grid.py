#!/usr/bin/env python3
"""tests/check_butterfly_wing_grid.py  v1.2
v1.2  2026-09-09  OTV4TEST r6 — the persistence bar is set to 1 for these selection fixtures.
v1.1  2026-09-01  r208 — W2/W3/W7 RE-DERIVED AGAINST THE SEARCH. The wing is
      no longer computed from WING_EM_FRAC and snapped to a grid, so W2/W3
      re-implemented arithmetic that no longer exists (C.23: a test that
      re-implements the thing it measures tests itself). They now DRIVE
      generate_signal on the PLTR 2.50 ladder that broke r198 and assert the
      selected legs are LISTED and symmetric about an unmoved pin — which is
      the invariant r198 was really about. W7's stretch pin is retired: with
      the wing searched, `wing_stretch` is always None and the old assertion
      still PASSED while measuring a quantity that can no longer vary.
      W1/W4/W5/W6 stand — `_chain_increment` survives for REPORTING.
THE BUTTERFLY'S WINGS SIT ON STRIKES THAT ACTUALLY EXIST.

v1.0  2026-08-31  r198 — born red at r197: `_chain_increment` does not exist
      there, and the wing is quantised by `config.STRIKE_INCREMENT` through
      `round_to_strike()`, which returns an **int**.

🔴 THE FAILURE THIS PINS, measured on the first live-fleet session. One global
increment for fifteen symbols, and an int-returning rounder:
    PLTR  pin 190,   EM 3.25 -> wing 1 -> legs 189 / 191   ($2.50 ladder)
    AMD   pin 472.5          -> wing 1 -> legs 470.5 / 474.5
Neither pair is listed, so `_exact()` refused — correctly — for **242 and 243
minutes**, roughly 900 ticks each, on both boxes, all session. An arithmetic
problem wearing the costume of a market judgement.

🔑 W3 IS THE CHECK THAT KEEPS THE DOCTRINE. The apex is the trade, and *"a
nearest-strike substitute is a different one"*. Both pins above were LISTED
strikes — only the wings were off-grid. So this must snap the WINGS and never
the apex, and W3 asserts the apex is exactly the pin after snapping.

⚠️ W5 GUARDS THE MEDIAN. A single stray half-strike in a $2.50 ladder would
set a min-based grid to 0.50 and reproduce the bug for that symbol on that day.

Run:  python3 tests/check_butterfly_wing_grid.py
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")

_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


class _K:
    def __init__(self, k):
        self.strike = k


def ladder(step, lo, hi):
    n = int(round((hi - lo) / step))
    return [_K(round(lo + i * step, 2)) for i in range(n + 1)]


def main():
    import strategy.gex_pin_butterfly as b

    if not hasattr(b, "_chain_increment"):
        check("W0 the wing grid is read from the chain", False,
              "_chain_increment is absent — wings are still quantised by one "
              "global STRIKE_INCREMENT for every symbol")
        print("\nFAILED 1: W0 — nothing below can execute")
        return 1

    # ── W1: the real ladders, including the two that failed live ──────────
    cases = [("PLTR $2.50 @190", ladder(2.5, 180, 200), 190.0, 2.5),
             ("AMD  $2.50 @472.5", ladder(2.5, 460, 485), 472.5, 2.5),
             ("SPX  $5    @7660", ladder(5, 7600, 7700), 7660.0, 5.0),
             ("NVDA $1    @180", ladder(1, 170, 190), 180.0, 1.0)]
    bad = [n for n, ks, pin, want in cases
           if abs(b._chain_increment(ks, pin) - want) > 1e-9]
    check("W1 the increment is read off the chain, per symbol", not bad,
          f"wrong: {bad}" if bad else "PLTR/AMD 2.5, SPX 5, NVDA 1")

    # ── W2/W3 — RE-DERIVED AT r208: THE SEARCH IS DRIVEN, NOT THE SNAP ────
    # 🔴 THE OLD W2/W3 COMPUTED `round(WING_EM_FRAC*EM/inc)*inc` IN THE TEST
    # and asserted the result was listed. That constant is deleted and the wing
    # is now SEARCHED over the chain's own strikes — and a test that
    # re-implements the thing it measures tests itself (C.23, the r181 sizing
    # checker that was green for two days over a dead field). These now drive
    # the real `generate_signal` on a PLTR-shaped 2.50 ladder.
    # ⚠️ AND THIS IS THE INVARIANT THE OPERATOR ASKED ABOUT: r198's failure was
    # compute-a-wing-then-DEMAND-it, so an unlisted wing refused the trade for
    # 242 minutes. The search cannot do that — a wing is only a candidate
    # because both legs came back priced — and W2 pins exactly that.
    import sqlite3
    from strategy import plan as P

    class _St:
        def __init__(s):
            s.conn = sqlite3.connect(":memory:"); s.conn.row_factory = sqlite3.Row
        def commit(s): s.conn.commit()

    class _Q:
        def __init__(s, k, m, sp=0.01):
            s.strike, s.mark = float(k), float(m)
            s.bid, s.ask = m - sp, m + sp
            s.delta, s.gamma, s.theta = 0.2, 0.01, -0.03
            s.expiry, s.symbol, s.open_interest = "x", f"O{k}", 100

    class _Ch:
        def __init__(s, c): s.calls, s.puts = c, []

    class _G:
        gex_environment, pin_strike, pin_concentration = "PINNING", 190.0, 0.60

    st2 = _St(); P.ensure_tables(st2); P.bind_store(st2)
    b.ENABLED = True
    _e0, _l0 = b.EARLIEST_ET, b.LATEST_ET
    b.EARLIEST_ET, b.LATEST_ET = "09:30", "16:00"
    _em0 = b.expected_move
    from utils.time_utils import ET as _ET0
    b.expected_move = lambda u, iv, now=None: _em0(
        u, iv, now=b.datetime(2026, 8, 27, 12, 30, tzinfo=_ET0))
    strat = b.GEXPinButterflyStrategy(); strat.planner.symbol = "PLTR"

    # OTV4TEST r6: persistence is a bar (8 ticks); these fixtures assert SELECTION on
    # a single tick, so the bar is set to 1 here and pinned on its own in check_plan_prepares B13.
    import strategy.gex_pin_butterfly as _bfm; _bfm.PERSIST_TICKS = 1
    # atm_iv 0.60 at the pinned 12:30 clock -> EM ~5.2, so the 2.50 pin sits
    # at 48% of it: inside the 30-100% band. At 1.20 the EM is 10.4 and the
    # setup HOLDS on pin_em_fraction — a fixture fault, not a code one.
    pltr = [_Q(k, m) for k, m in ((182.5, 8.60), (185.0, 6.60), (187.5, 4.00),
                                  (190.0, 2.40), (192.5, 1.60), (195.0, 1.10))]
    P.begin_tick(70.0)
    sigw = strat.generate_signal(gex=_G(), price_now=187.5, now_et="12:30",
                                 atm_iv=0.60, chain=_Ch(pltr))
    b.EARLIEST_ET, b.LATEST_ET = _e0, _l0
    b.expected_move = _em0
    _listed = {q.strike for q in pltr}
    _legs = sigw and (sigw.lower_contract.strike, sigw.center_contract.strike,
                      sigw.upper_contract.strike)
    check("W2 every leg the search selects is a LISTED strike",
          sigw is not None and set(_legs) <= _listed,
          f"legs={_legs} listed={sorted(_listed)}")

    # ── W3: THE APEX NEVER MOVES ──────────────────────────────────────────
    # 🔑 The doctrine protects the apex, not the wings: symmetric about the
    # pin, and the pin itself is never rounded.
    check("W3 the wings stay symmetric about the pin, which is never moved",
          sigw is not None and _legs[1] == 190.0
          and abs((_legs[0] + _legs[2]) - 2 * 190.0) < 1e-9,
          f"legs={_legs}")

    # ── W4: the int rounder is not used for the wing any more ─────────────
    # ⚠️ Shape of the CALL, not a mention (WA §20): the v4.7 changelog names
    # round_to_strike while explaining why it cannot be used here.
    src = open(os.path.join(_root, "strategy", "gex_pin_butterfly.py"),
               encoding="utf-8").read()
    body = "\n".join(l for l in src.splitlines()
                     if not l.strip().startswith("#"))
    check("W4 neither round_to_strike() nor WING_EM_FRAC computes the wing",
          "round_to_strike(WING_EM_FRAC" not in body
          and "from utils.math_utils import round_to_strike" not in body
          and not hasattr(b, "WING_EM_FRAC"),
          "it returns an int, so a $2.50 ladder cannot be expressed by it")

    # ── W5: a stray listing must not drag the grid down ───────────────────
    mixed = ladder(2.5, 180, 200) + [_K(189.5)]
    check("W5 one stray half-strike does not set the grid (median, not min)",
          abs(b._chain_increment(mixed, 190.0) - 2.5) < 1e-9,
          str(b._chain_increment(mixed, 190.0)))

    # ── W6: degenerate chains fall back, never crash ──────────────────────
    check("W6 a thin or absent chain falls back to the configured default",
          b._chain_increment([_K(190)], 190.0, 1.0) == 1.0
          and b._chain_increment(None, 190.0, 1.0) == 1.0
          and b._chain_increment([], 190.0, 2.5) == 2.5)

    # ── W7 — RE-DERIVED AT r208: THE STRETCH IS GONE, THE GRID IS RECORDED ─
    # 🔴 W7 USED TO PIN `wing_intended` AND `wing_stretch`, and r198's ruling
    # behind it — a wider-than-intended wing is accepted, on the condition that
    # it bears out in the metrics — DOES NOT SURVIVE r208. There is no intended
    # width any more: the wing is searched over listed strikes, so "stretch"
    # (chosen ÷ intended) is identically 1.0 and `wing_stretch` is always None.
    # ⚠️ LEAVING THE OLD ASSERTION WOULD HAVE BEEN WORSE THAN DELETING IT. It
    # still PASSED — the field names are all still in the source — while
    # measuring a quantity that can no longer vary. A check that cannot fail is
    # the decorative-green class this repo keeps finding in its own tools.
    # What survives is the part still capable of being wrong: the SELECTED wing
    # and the grid it came off ride the record, so BFLY.9's survey can ask
    # "which wing did we take on which ladder" from the trade rows.
    check("W7 the selected wing and its grid ride on the signal",
          "sig.wing_intended" in src and "sig.grid_increment" in src
          and sigw is not None and abs(sigw.wing_intended - 2.5) < 1e-9
          and abs(sigw.grid_increment - 2.5) < 1e-9,
          f"wing={sigw and sigw.wing_intended} grid={sigw and sigw.grid_increment}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_butterfly_wing_grid: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
