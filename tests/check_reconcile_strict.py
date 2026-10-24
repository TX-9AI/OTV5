#!/usr/bin/env python3
"""
tests/check_reconcile_strict.py  v1.0
v1.0  2026-10-04  r465 / B1 — RECONCILE CHECKS EVERY LEG AT ITS QUANTITY, AND READS
      ONLY THIS BOX'S INSTRUMENT.

  🔴 Found by OTV4TEST's live-readiness audit, measured on mainline:
  broker_reconcile.build_plan kept a DB row if ANY leg symbol was at the broker
  and never read quantity, so 2N vs N or a vertical missing a leg read healthy;
  and tasty_client.get_open_option_positions returned EVERY option in the
  account, so boxes sharing one account would adopt each other's legs. The
  operator: "multiple boxes will trade that account but never duplicate
  symbols ever".

  OFFLINE (no broker, no network):
  R1  a vertical with both legs at the expected quantity: kept, no mismatch
  R2  a vertical missing its long: kept AND reported (missing = the long)
  R3  a single leg at 2N where the row expects N: kept AND reported (quantity)
  R4  a butterfly's body at 2N is healthy; at N it is reported
  R5  UNCHANGED: a row with NO leg at the broker is a phantom
  R6  two rows sharing one leg symbol are judged on the SUM (no false report)
  R7  get_open_option_positions keeps only this box's underlying (QQQ), keeps
      SPXW for an SPX box, and returns the whole account for underlying="*"
  BORN RED on otv4 a102c05 at R2 R3 R4 R6 R7 (R6 because plan.mismatch did not exist).

Run:  python3 tests/check_reconcile_strict.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


def bp(sym, qty, direction="Long"):
    return {"symbol": sym, "underlying": sym.split()[0], "quantity": qty,
            "direction": direction, "average_open_price": 1.0}


S = "QQQ   261005P00700000"
L = "QQQ   261005P00695000"
SINGLE = "QQQ   261005C00710000"
LO, CE, UP = "QQQ   261005C00705000", "QQQ   261005C00710000", "QQQ   261005C00715000"


def main():
    from execution.broker_reconcile import build_plan
    vert = {"trade_id": "v1", "contracts": 3, "short_symbol": S, "long_symbol": L}

    p = build_plan([bp(S, 3, "Short"), bp(L, 3)], [vert])
    check("R1 a healthy vertical: kept, no mismatch",
          [r["trade_id"] for r in p.keep] == ["v1"] and not getattr(p, "mismatch", []),
          f"keep={[r['trade_id'] for r in p.keep]} mismatch={getattr(p, 'mismatch', 'ABSENT')}")

    p = build_plan([bp(S, 3, "Short")], [vert])
    mm = getattr(p, "mismatch", None)
    check("R2 a vertical missing its long is kept AND reported",
          [r["trade_id"] for r in p.keep] == ["v1"] and mm and mm[0]["missing"] == [L],
          f"mismatch={mm}")

    single = {"trade_id": "s1", "contracts": 2, "option_symbol": SINGLE}
    p = build_plan([bp(SINGLE, 4)], [single])
    mm = getattr(p, "mismatch", None)
    check("R3 a single at 2N against N is reported",
          mm and mm[0]["quantity"].get(SINGLE) == {"expected": 2, "broker": 4}, f"mismatch={mm}")

    fly = {"trade_id": "f1", "contracts": 1, "lower_symbol": LO, "center_symbol": CE,
           "upper_symbol": UP}
    ok_fly = build_plan([bp(LO, 1), bp(CE, 2, "Short"), bp(UP, 1)], [fly])
    bad_fly = build_plan([bp(LO, 1), bp(CE, 1, "Short"), bp(UP, 1)], [fly])
    check("R4 a fly's body at 2N is healthy; at N it is reported",
          not getattr(ok_fly, "mismatch", ["x"]) and getattr(bad_fly, "mismatch", []),
          f"ok={getattr(ok_fly, 'mismatch', 'ABSENT')} bad={getattr(bad_fly, 'mismatch', 'ABSENT')}")

    p = build_plan([bp("NVDA  261005C00200000", 1)],
                   [{"trade_id": "g1", "contracts": 1, "option_symbol": SINGLE}])
    check("R5 UNCHANGED: no leg at the broker is a phantom", p.close_phantom == ["g1"],
          f"phantom={p.close_phantom}")

    a = {"trade_id": "a1", "contracts": 1, "option_symbol": SINGLE}
    b = {"trade_id": "b1", "contracts": 2, "option_symbol": SINGLE}
    p = build_plan([bp(SINGLE, 3)], [a, b])
    check("R6 two rows sharing a leg are judged on the sum", not getattr(p, "mismatch", ["x"]),
          f"mismatch={getattr(p, 'mismatch', 'ABSENT')}")

    import data.tasty_client as tc

    class _P:
        def __init__(self, sym, und):
            self.instrument_type = "Equity Option"
            self.quantity = 1
            self.quantity_direction = "Long"
            self.symbol, self.underlying_symbol = sym, und
            self.average_open_price = 1.0

    class _Acct:
        def get_positions(self, session):
            return [_P("QQQ   261005C00710000", "QQQ"), _P("NVDA  261005C00200000", "NVDA"),
                    _P("SPXW  261005C07600000", "SPX"), _P("SPX   261016C07600000", "SPX")]
    real = (tc.get_account, tc.get_session, os.environ.get("OT_INSTRUMENT"))
    try:
        tc.get_account, tc.get_session = (lambda: _Acct()), (lambda: object())
        os.environ["OT_INSTRUMENT"] = "QQQ"
        q = [x["symbol"][:4] for x in tc.get_open_option_positions()]
        os.environ["OT_INSTRUMENT"] = "SPX"
        s = sorted(x["symbol"][:4] for x in tc.get_open_option_positions())
        try:
            allp = tc.get_open_option_positions(underlying="*")
        except TypeError:
            allp = tc.get_open_option_positions()
        check("R7 only this box's underlying (QQQ); SPX keeps SPX+SPXW; '*' is the whole account",
              q == ["QQQ "] and s == ["SPX ", "SPXW"] and len(allp) == 4,
              f"qqq={q} spx={s} all={len(allp)}")
    finally:
        tc.get_account, tc.get_session = real[0], real[1]
        if real[2] is None:
            os.environ.pop("OT_INSTRUMENT", None)
        else:
            os.environ["OT_INSTRUMENT"] = real[2]

    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — reconcile checks every leg at its quantity, on this box's instrument only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
