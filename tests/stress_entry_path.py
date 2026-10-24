#!/usr/bin/env python3
"""
tests/stress_entry_path.py  v4.0
Hostile inputs against every entry path. Nothing crashes, nothing fires on
garbage.

v4.0  2026-08-20  Built at the OTV4 split, before the adversarial audit.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

════════════════════════════════════════════════════════════════════════════
TWO FAILURE MODES, AND THEY ARE NOT THE SAME
════════════════════════════════════════════════════════════════════════════
**A STRATEGY THAT CRASHES STOPS THE BOX.** v3's `ctx` NameError halted every
box in the fleet and `import main` passed the whole time. `_safe_strategy`
catches and logs, so a raise degrades to "no signal" - **which means a crashing
strategy looks exactly like a quiet one in the logs.** That is worse than a
crash, not better.

**A STRATEGY THAT FIRES ON GARBAGE TRADES GARBAGE.** A None ATR read as 0.0
passes a `< floor` test. A crossed quote produces a negative spread and a
nonsense ladder. A missing field read via `getattr(x, "y", 0)` becomes a
measured zero. **This project's most repeated defect is a default wearing the
costume of an observation** - `oi_proxy`, `vix_at_entry` at 58%, `max_liq` at 0
for weeks.

So every case below asserts BOTH: no exception escaped, AND no signal fired on
input that cannot support one.

⚠️ THIS IS NOT A SUBSTITUTE FOR THE AUDIT. It is the floor an adversarial
reviewer should not have to spend tokens establishing - the cheap, mechanical
half - so the expensive half can go at logic and design instead.
"""

import math
import os
import sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS, FAIL = [], []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    if not ok:
        print(f"  FAIL  {label}" + (f"  - {detail}" if detail else ""))


def probe(label, fn):
    """Call fn. Assert it neither raises nor returns a signal."""
    try:
        out = fn()
    except Exception as e:                                     # noqa: BLE001
        check(f"{label}: no exception", False, f"{type(e).__name__}: {e}")
        return
    check(f"{label}: no exception", True)
    check(f"{label}: no signal on bad input", out is None,
          f"returned {type(out).__name__}")


# ── hostile values ─────────────────────────────────────────────────────────
# ⚠️ NaN IS THE DANGEROUS ONE AND IT IS EASY TO MISS. Every comparison against
# NaN is False, so `if atr < FLOOR: refuse` does NOT refuse - the veto silently
# inverts and the trade fires in exactly the tape the floor exists to exclude.
HOSTILE = [None, 0, 0.0, -1.0, float("nan"), float("inf"), float("-inf"),
           "", "abc", 1e12]

# ⚠️ 1e12 IS FINITE AND WILL PASS A FINITENESS GUARD. It is included to prove
# that "not NaN" is not the same as "sane" - a 1,000,000,000,000% ATR is a
# well-formed float and an absurd claim about the tape. Absurd-but-finite input
# is caught by RANGE checks, not by type checks, and the two are different
# defences.


def stress_runaway():
    from strategy.runaway_continuation import (RunawayContinuationStrategy,
                                               target_delta)
    s = RunawayContinuationStrategy()
    orb_ok = NS(state="OPEN_LONG", orb_high=101.0, orb_low=100.0, tp50=101.5)

    for v in HOSTILE:
        probe(f"runaway atr={v!r}",
              lambda v=v: s.generate_signal(orb=orb_ok, atr_pct=v,
                                            price_now=101.6, prev_close=101.55,
                                            now_et="10:15"))
        probe(f"runaway price={v!r}",
              lambda v=v: s.generate_signal(orb=orb_ok, atr_pct=0.14,
                                            price_now=v, prev_close=101.55,
                                            now_et="10:15"))
    probe("runaway orb=None",
          lambda: s.generate_signal(orb=None, atr_pct=0.14, price_now=101.6,
                                    prev_close=101.55, now_et="10:15"))
    probe("runaway orb missing every field",
          lambda: s.generate_signal(orb=NS(), atr_pct=0.14, price_now=101.6,
                                    prev_close=101.55, now_et="10:15"))

    # ⚠️ THE NaN VETO TEST. A NaN ATR must NOT be treated as reachable.
    d = target_delta(float("nan"))
    check("runaway: NaN ATR yields NO strike (the veto does not invert)",
          d is None, f"target_delta(nan) = {d}")
    check("runaway: 0.0 ATR yields no strike", target_delta(0.0) is None)
    check("runaway: below-floor ATR yields no strike",
          target_delta(0.04) is None)


def stress_sweep():
    from strategy.sweep_credit_spread import (SweepCreditSpreadStrategy,
                                              pierced_strike,
                                              boundary_from_sweep)
    s = SweepCreditSpreadStrategy()
    sw = NS(swept_named_level="PDH", reclaimed=True, invalidated=False,
            bars_ago=2, rejection_pct=0.0018, kind="high_sweep",
            pool_price=600.0, sweep_price=601.2)

    probe("sweep liq_map=None",
          lambda: s.generate_signal(liq_map=None, price_now=599.0,
                                    now_et="13:30", atr_pct=0.10))
    probe("sweep recent_sweep=None",
          lambda: s.generate_signal(liq_map=NS(recent_sweep=None),
                                    price_now=599.0, now_et="13:30",
                                    atr_pct=0.10))
    probe("sweep object missing every field",
          lambda: s.generate_signal(liq_map=NS(recent_sweep=NS()),
                                    price_now=599.0, now_et="13:30",
                                    atr_pct=0.10))
    for v in HOSTILE:
        probe(f"sweep price={v!r}",
              lambda v=v: s.generate_signal(liq_map=NS(recent_sweep=sw),
                                            price_now=v, now_et="13:30",
                                            atr_pct=0.10))
    # a NaN ATR must not slip past the feasibility ceiling
    r = s.generate_signal(liq_map=NS(recent_sweep=sw), price_now=599.0,
                          now_et="13:30", atr_pct=float("nan"))
    check("sweep: NaN ATR does not bypass the ceiling", r is None,
          "a NaN comparison is False, so `atr > MAX` does not refuse")

    check("sweep: unknown sweep kind -> no boundary",
          boundary_from_sweep("sideways_sweep") is None)
    check("sweep: pierced_strike on garbage -> None",
          pierced_strike(0, 0, True, 0) is None)
    check("sweep: pierced_strike with a NaN sweep price -> None or sane",
          pierced_strike(float("nan"), 600.0, True, 1.0) in (None,)
          or not math.isnan(pierced_strike(float("nan"), 600.0, True, 1.0) or 0))


def stress_butterfly():
    from strategy.gex_pin_butterfly import (GEXPinButterflyStrategy,
                                            expected_move)
    s = GEXPinButterflyStrategy()
    gx = NS(gex_environment="PINNING", pin_concentration=0.40, pin_strike=606.0)
    probe("butterfly gex=None",
          lambda: s.generate_signal(gex=None, price_now=600.0,
                                    now_et="13:00", atm_iv=0.35))
    for v in HOSTILE:
        probe(f"butterfly atm_iv={v!r}",
              lambda v=v: s.generate_signal(gex=gx, price_now=600.0,
                                            now_et="13:00", atm_iv=v))
    check("butterfly: expected_move on NaN IV -> None or finite",
          expected_move(600.0, float("nan")) is None
          or math.isfinite(expected_move(600.0, float("nan")) or 0))
    check("butterfly: expected_move with no IV -> None",
          expected_move(600.0, 0.0) is None)
    check("butterfly: PARKED by default", s.generate_signal(
        gex=gx, price_now=600.0, now_et="13:00", atm_iv=0.35) is None)


def stress_ladder():
    from execution.entry_ladder import rungs, LadderState
    # ⚠️ A CROSSED QUOTE IS NOT HYPOTHETICAL. It appears around the open, on
    # halts, and on thin 0DTE strikes. A negative half-spread would place rungs
    # THROUGH the far side - paying more than the ask.
    for bid, ask, lbl in ((2.50, 1.50, "crossed"), (0, 0, "zero"),
                          (-1, 2, "negative bid"), (1.0, 1.0, "locked"),
                          (float("nan"), 2.0, "NaN bid")):
        try:
            out = rungs(bid, ask, "sell")
            ok = isinstance(out, list) and all(
                isinstance(x, float) and math.isfinite(x) for x in out)
            check(f"ladder {lbl}: returns a sane list", ok, f"{out}")
            if out:
                check(f"ladder {lbl}: never posts through the far side",
                      all(x <= max(bid, ask) + 1e-9 for x in out
                          if math.isfinite(x)), f"{out}")
        except Exception as e:                                 # noqa: BLE001
            check(f"ladder {lbl}: no exception", False,
                  f"{type(e).__name__}: {e}")

    st = LadderState("sell")
    try:
        st.refuse(None)
        st.refuse("abc")
        out = st.next_price(1.5, 2.5)
        check("ladder: survives garbage refusals", out is not None)
    except Exception as e:                                     # noqa: BLE001
        check("ladder: survives garbage refusals", False, str(e))


def stress_relaxed_and_cutoff():
    import os as _os
    from strategy import relaxed
    for k in ("OT_RELAXED_ENTRY", "OT_PAPER_TRADING"):
        _os.environ.pop(k, None)
    check("relaxed: OFF by default", not relaxed.is_allowed())
    _os.environ["OT_RELAXED_ENTRY"] = "1"
    check("relaxed: refuses without an explicit paper assertion",
          not relaxed.is_allowed())
    _os.environ["OT_PAPER_TRADING"] = "1"
    check("relaxed: permitted only with BOTH", relaxed.is_allowed())
    # ⚠️ RELAXED MUST NEVER LOOSEN A FEASIBILITY FLOOR.
    from strategy.runaway_continuation import target_delta
    check("relaxed: cannot make sub-floor ATR tradeable",
          target_delta(0.02) is None)
    for k in ("OT_RELAXED_ENTRY", "OT_PAPER_TRADING"):
        _os.environ.pop(k, None)

    import main
    from datetime import datetime

    class T:
        def __init__(self, h, m):
            self.hour, self.minute = h, m
    check("cutoff: an UNDECLARED strategy fails closed after 11:30",
          main._afternoon_debit_blocked("SomethingBrandNew", T(11, 31)))
    check("cutoff: a vertical is never blocked",
          not main._afternoon_debit_blocked("SweepCreditSpread", T(15, 0)))
    check("cutoff: exact boundary 11:30 blocks",
          main._afternoon_debit_blocked("ORBStrategy", T(11, 30)))
    check("cutoff: 11:29 does not",
          not main._afternoon_debit_blocked("ORBStrategy", T(11, 29)))


def stress_excursion():
    from execution.exit_engine import _track_excursion
    r = {}
    for v in HOSTILE:
        try:
            _track_excursion(r, v)
        except Exception as e:                                 # noqa: BLE001
            check(f"excursion {v!r}: no exception", False, str(e))
            return
    check("excursion: survives every hostile mark", True)
    check("excursion: garbage never became a peak",
          r.get("mfe_premium") in (None, 1e12),
          f"mfe={r.get('mfe_premium')}")


def main_(argv):
    print("STRESS: hostile inputs against every entry path")
    print("=" * 72)
    for fn in (stress_runaway, stress_sweep, stress_butterfly, stress_ladder,
               stress_relaxed_and_cutoff, stress_excursion):
        try:
            fn()
        except Exception as e:                                 # noqa: BLE001
            check(f"{fn.__name__} completed", False,
                  f"{type(e).__name__}: {e}")
    print("=" * 72)
    print(f"  {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("  ⚠️ A CRASH AND A BAD FIRE ARE DIFFERENT BUGS. `_safe_strategy`")
        print("     turns a raise into 'no signal', so a crashing strategy looks")
        print("     exactly like a quiet one in the logs.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main_(sys.argv))
