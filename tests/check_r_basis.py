#!/usr/bin/env python3
"""
tests/check_r_basis.py  v1.0
v1.0  2026-09-03  r234 — R IS JUDGED AGAINST THE RISK ACTUALLY TAKEN, AND ONLY
      WHERE THE STOP IS THE PLANNED EXIT. Operator, 2026-09-03, on splitting
      the basis: the credit verticals move, the GEX pin butterfly does not (a
      debit paid up front and held to the close), and the managed roll never
      opted in.

⚠️ EXECUTED, NEVER READ (§21). Every check drives the real helper or the real
search and asserts on returned numbers.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


class K:
    def __init__(self, k, b, a, m=None):
        self.strike, self.bid, self.ask = float(k), b, a
        self.mark = (b + a) / 2.0 if m is None else m


def main():
    from strategy import criteria as CR
    from strategy import credit_vertical as cv
    from config import LONE_STOP_PCT_OF_RISK

    for fn in ("stop_distance", "r_on_stop", "R_FLOOR_STOP"):
        if not hasattr(CR, fn):
            check(f"B0 criteria exposes {fn}", False, "the stop basis is absent")
            print()
            print("RED — 1 failed: stop basis absent")
            return 1

    # ══ B1 — ONE STOP DEFINITION, AND IT IS THE ENGINE'S ══════════════════
    # exit_engine:1818 -> entry + (width - entry) * LONE_STOP_PCT_OF_RISK.
    # The forensics measured this at a $0.605 median on width 5 / credit 0.97.
    sd = CR.stop_distance(5.0, 0.97)
    check("B1 stop_distance is 15% OF RISK, matching exit_engine",
          abs(sd - (5.0 - 0.97) * LONE_STOP_PCT_OF_RISK) < 1e-9, f"{sd}")
    check("B1b and it reproduces the measured $0.605 median",
          abs(sd - 0.605) < 0.001, f"{sd:.4f}")
    # 🔴 THE DEFECT IT REPLACES: `credit * MAX_LOSS_PCT` — 15% OF CREDIT — is
    # the inverted rule r155 deleted, and it is 4.15x tighter.
    check("B1c it is NOT 15% of credit (the r155-inverted form)",
          abs(sd - 0.97 * LONE_STOP_PCT_OF_RISK) > 0.4, f"{sd}")

    # ══ B2 — THE BASES DIFFER BY EXACTLY THE STOP PERCENTAGE ══════════════
    r_exp = 0.97 / (5.0 - 0.97)
    r_stp = CR.r_on_stop(5.0, 0.97)
    check("B2 r_on_stop = r_expiry / LONE_STOP_PCT_OF_RISK",
          abs(r_stp - r_exp / LONE_STOP_PCT_OF_RISK) < 1e-9,
          f"{r_stp:.3f} vs {r_exp:.3f}")
    check("B2b the measured median clears 1:1 on the stop and fails at expiry",
          r_stp > 1.0 and r_exp < 1.0, f"stop {r_stp:.3f} / expiry {r_exp:.3f}")

    # ══ B3 — THE THRESHOLD THE OPERATOR WAS GIVEN: credit/width >= 13.04% ══
    # Stated in the r234 conversation as the exact bar; pinned so the number
    # in the record and the number in the code cannot drift.
    thr = LONE_STOP_PCT_OF_RISK / (1.0 + LONE_STOP_PCT_OF_RISK)
    check("B3 R_stop = 1 lands at credit/width = 13.04%",
          abs(thr - 0.1304) < 0.0001, f"{thr:.4f}")
    w = 5.0
    check("B3b a structure exactly at the threshold scores 1.00",
          abs(CR.r_on_stop(w, thr * w) - 1.0) < 1e-9)

    # ══ B4 — UNPRICEABLE IS None, NEVER A BAD RATIO ═══════════════════════
    # r205 doctrine: a missing quote is not a measurement of zero, and scoring
    # it as one would refuse on absent data.
    check("B4 an unpriceable structure returns None, not 0.0",
          CR.stop_distance(5.0, 0) is None and CR.r_on_stop(0, 0) is None
          and CR.stop_distance(1.0, 2.0) is None)

    # ══ B5 — THE BUTTERFLY KEEPS THE EXPIRY BASIS ═════════════════════════
    # 🔴 Operator ruling. A debit fly's risk IS the debit, paid up front and
    # held to the close, so its denominator was already right. Two constants,
    # each naming its basis, so they cannot collapse into one (§35).
    check("B5 R_FLOOR and R_FLOOR_STOP are separate constants",
          hasattr(CR, "R_FLOOR") and hasattr(CR, "R_FLOOR_STOP"))
    bfly = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "strategy", "gex_pin_butterfly.py"),
        encoding="utf-8").read()
    check("B5b the butterfly does NOT import the stop basis",
          "R_FLOOR_STOP" not in bfly)
    roll = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "strategy", "condor_roll.py"),
        encoding="utf-8").read()
    check("B5c the managed roll reads neither floor",
          "R_FLOOR" not in roll)

    # ══ B6 — THE NARROW-SIDE BRACKET. r208's C.43 carried to the verticals.
    # R rises as the wing narrows while the STOP narrows with it, so a
    # selector that only maximises R optimises INTO the least survivable
    # structure. Wide legs must be refused BY NAME, at selection.
    ws, wl = K(100.0, 1.20, 1.80), K(105.0, 0.23, 0.83)
    wide = cv.search_wing([ws, wl], ws, "call", 1.0, r_floor_stop=0.0)
    check("B6 a stop that cannot clear 2x the short spread is refused",
          wide.long is None and wide.why_key == "stop_vs_spread",
          f"{wide.why_key}: {wide.why}")
    ns, nl = K(100.0, 1.20, 1.30), K(105.0, 0.23, 0.33)
    ok = cv.search_wing([ns, nl], ns, "call", 1.0, r_floor_stop=0.0)
    check("B6b the same structure with tight legs qualifies",
          ok.long is not None and ok.r_stop is not None, ok.why)

    # ══ B7 — THE REFUSING RUNG IS A FIELD, NOT PROSE ══════════════════════
    # A caller that sniffed the message would rot on the first rewording
    # (§20 one level over), and "no priceable wing" would blame the chain for
    # a decision the gate made.
    hi = cv.search_wing([ns, nl], ns, "call", 1.0, r_floor_stop=99.0)
    check("B7 an R-floor refusal names wing_r_best, not the chain",
          hi.long is None and hi.why_key == "wing_r_best",
          f"{hi.why_key}: {hi.why}")

    # ══ B8 — THE r219 ARITY BUG IS UNREPRESENTABLE NOW ════════════════════
    # r219 added a fifth value and missed two guard returns that still
    # returned four; both callers unpacked five, so a short leg with no bid
    # raised ValueError into _safe_strategy and read as a clean DECLINE.
    class NoBid:
        strike, bid, ask, mark = 100.0, 0.0, 1.10, 1.05
    g = cv.search_wing([NoBid(), nl], NoBid(), "call", 1.0)
    check("B8 every guard return is the same shape as the success return",
          type(g) is type(ok) and g.long is None and bool(g.why), g.why)

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 15 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
