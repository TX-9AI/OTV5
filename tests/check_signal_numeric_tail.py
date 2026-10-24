#!/usr/bin/env python3
"""
tests/check_signal_numeric_tail.py  v1.3  (2026-09-24)
v1.3  2026-09-24  OTV4TEST r131 — N5 RE-POINTED, NOT DROPPED: the stop_premium read moved into
      main._sizing_stop_premium (VOLT's 1-R curve); the seam must call it and it must
      read through _sig_num. Red in r131's full sweep until re-pointed; mutation-proven.
v1.2  2026-09-13  OTV4TEST r25 — N6 PASSES A 1m FRAME. r24 requires the last closed bar to
      hold the 50; with no frame the runaway HOLDs, no signal exists, and N6 had
      nothing to resolve. RED SINCE r24 AND SHIPPED THAT WAY (not in r24's gate
      list). Closes at the case's own price, 101.9, so the signal is unchanged.
v1.1  2026-09-08  OTV4TEST r3 — N6's fake ORB carries `fifty_accepted`; no `prev_close`.

EVERY STRATEGY'S SIGNAL SHAPE MUST SURVIVE THE EXECUTION TAIL'S NUMERIC
READS. Born red at c90cdc5: the sizing seam read `signal.stop_premium` with
getattr+float, that name is a METHOD on OptionsSignal, and the r168 runaway
leaves the method exposed — the first fire of 2026-08-28 crashed every tick
fleet-wide (zero trades, restart spam). The missing coverage class was
exactly this: the hypotheticals stopped at the signal and never ran the
tail's reads against each signal's real shape.

  N1  a debit signal that leaves the class METHOD exposed resolves to
      entry x (1 - stop_loss_pct) — the runaway's correct 20% floor
  N2  a signal that shadows the name with an ATTRIBUTE resolves to it
  N3  a signal with neither resolves to 0.0 and raises nothing
  N4  a callable that itself raises resolves to 0.0 and raises nothing
  N5  the sizing call in _execute_entry_signal reads through _sig_num —
      never a bare getattr+float on stop_premium (AST)
  N6  the REAL runaway signal (built by the plan) survives _sig_num with
      the 20% floor
"""
import ast
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


def main():
    import main as M

    class _MethodSig:
        entry_premium, stop_loss_pct = 1.85, 0.20
        def stop_premium(self):
            return self.entry_premium * (1 - self.stop_loss_pct)

    class _AttrSig:
        stop_premium = 1.495

    class _BareSig:
        pass

    class _RaisingSig:
        def stop_premium(self):
            raise RuntimeError("no entry premium yet")

    check("N1 method exposed -> called: 1.85 x 0.80 = 1.48",
          abs(M._sig_num(_MethodSig(), "stop_premium") - 1.48) < 1e-9)
    check("N2 attribute shadowing -> read as-is: 1.495",
          abs(M._sig_num(_AttrSig(), "stop_premium") - 1.495) < 1e-9)
    check("N3 neither -> 0.0, no raise", M._sig_num(_BareSig(), "stop_premium") == 0.0)
    check("N4 a raising callable -> 0.0, no raise",
          M._sig_num(_RaisingSig(), "stop_premium") == 0.0)

    src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    fn = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)
              and n.name == "_execute_entry_signal")
    body = ast.unparse(fn)
    # r131 — RE-POINTED, NOT DROPPED (WA 38.4): the read moved into the sizing
    # helper main._sizing_stop_premium (VOLT's 1-R curve). The seam must CALL the
    # helper, and the helper must read through _sig_num with no bare getattr+float.
    helper = next((n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)
                   and n.name == "_sizing_stop_premium"), None)
    hbody = ast.unparse(helper) if helper is not None else ""
    via_helper = "_sizing_stop_premium(signal)" in body and "_sig_num(signal, 'stop_premium')" in hbody
    direct = "_sig_num(signal, 'stop_premium')" in body
    check("N5 the sizing seam reads stop_premium through _sig_num, not getattr+float",
          (via_helper or direct)
          and "float(getattr(signal, 'stop_premium'" not in body
          and "float(getattr(signal, 'stop_premium'" not in hbody)

    # N6 — the real runaway signal, end to end through the resolver
    import sqlite3
    from strategy import plan as P
    from strategy.runaway_continuation import RunawayContinuationStrategy

    class _S:
        def __init__(self): self.conn = sqlite3.connect(":memory:")
        def commit(self): self.conn.commit()

    class _ORB:
        state, orb_high, orb_low, target_50pct = "OPEN_LONG", 101.0, 100.0, 101.5
        invalidation_reason, break_direction = "", ""
        fifty_accepted, bars_since_break = True, 2      # OTV4TEST r3: the trigger

    class _C:
        def __init__(self, k, prem, d, g):
            self.strike, self.mark, self.ask, self.bid = float(k), prem, prem + 0.02, prem - 0.02
            self.delta, self.gamma, self.expiry, self.open_interest = d, g, "x", 100

    class _Chain:
        calls = [_C(102, 0.95, 0.46, 0.05), _C(103, 0.48, 0.30, 0.058)]
        puts = []

    # OTV4TEST r25 — r24 made entry require the CLOSED 1m bar to hold the 50 NOW
    # (runaway_plan's `fifty_held_now`); live, main.py always passes ctx["df_1m"].
    # A call with no frame therefore HOLDs before it reaches the case under test,
    # so the fixture carries bars whose closes sit at this case's own price.
    import pandas as _pd

    def _bars_at(px):
        return _pd.DataFrame([{"open": px, "high": px, "low": px, "close": px}] * 5,
                             index=_pd.date_range("2026-09-08 10:10", periods=5, freq="1min",
                                                  tz="America/New_York"))

    P.bind_store(_S())
    P.begin_tick(1.0)
    os.environ["OT_RELAXED_ENTRY"] = "1"
    RW = RunawayContinuationStrategy(); RW.planner.symbol = "TST"
    sig = RW.generate_signal(orb=_ORB(), atr_pct=0.14, price_now=101.9,
                             now_et="10:15", chain=_Chain(), df_1m=_bars_at(101.9))
    os.environ["OT_RELAXED_ENTRY"] = "0"
    sp = M._sig_num(sig, "stop_premium") if sig else None
    check("N6 the real runaway signal resolves its 20% floor through the tail's reader",
          sig is not None and sp is not None and abs(sp - sig.entry_premium * 0.80) < 1e-6,
          f"entry={sig and sig.entry_premium} floor={sp}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_signal_numeric_tail: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
