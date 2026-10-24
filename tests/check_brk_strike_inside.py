#!/usr/bin/env python3
"""
tests/check_brk_strike_inside.py  v1.0
ON A CASH INDEX, BREAKOUT BUYS THE NEAREST STRIKE AT OR INSIDE ITS REACH - NEVER ONE PAST IT (STRK.2).

v1.0  2026-10-06  OTV4TEST r259. Found on SPX-TEST 10-06: the 10:08 Breakout long bought the 7845C for a
      7842.79 reach - orb_plan.select_contract takes the NEAREST listed strike (|7845-7842.79| = 2.21 <
      |7840-7842.79| = 2.79), so on SPX's 5-wide grid a strike can sit up to 2.5 points past the reach.
      The operator, 2026-10-06 20:41 ET: "at or inside target".

  K1  the REAL BreakoutPlan.prepare on SPX (research open, a long break): with a strike 2.21 PAST the
      reach and one 2.79 INSIDE it, the plan's contract is the INSIDE strike
  K2  the same, on a chain whose only strikes are PAST the reach: no contract, refused, and the refusal
      names "at or inside"
  K3  select_contract(..., inside=True), a SHORT: of a put 2.21 past (below) the reach and one 2.79 inside
      (above) it, the inside one
  K4  inside=True takes a strike exactly AT the reach
  K5  UNCHANGED - the default (ORB, VOLT, every non-index Breakout): the nearest strike, past or not
  K6  UNCHANGED - Breakout on QQQ passes no inside flag (source of the one call site, read by AST)

Drives the REAL BreakoutPlan.prepare and the REAL orb_plan.select_contract. NOT RUN (exit 2), never FAIL,
when the imports cannot load (e.g. a bare python3 with no pandas).
"""
import ast
import os
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp()
os.environ["OT_TRADES_DB"] = os.path.join(_TD, "t.db")
os.environ["OT_DERIVED_DB"] = os.path.join(_TD, "d.db")
os.environ["OT_FEED_DB"] = os.path.join(_TD, "f.db")
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _c(strike, delta):
    return types.SimpleNamespace(strike=float(strike), mark=2.0, bid=1.9, ask=2.1, delta=delta,
                                 symbol=f"X{strike}", streamer_symbol=f".X{strike}")


def main():
    print("check_brk_strike_inside")
    try:
        import pandas  # noqa: F401
        import strategy.breakout as B
        from strategy.breakout import Breakout
        from strategy.breakout_plan import BreakoutPlan
        from strategy import orb_plan as OP
        from data.candle_feed import FeedStore
        sys.path.insert(0, os.path.join(ROOT, "tests"))
        import check_brk_cash_index as CI                       # its fixtures: the same broken tape
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2

    fs = FeedStore(os.environ["OT_FEED_DB"])
    B.RESEARCH_UNTIL = "2099-12-31"

    LAST = {}

    def prep(symbol, chain):
        plan = BreakoutPlan()
        LAST["plan"] = plan
        return plan.prepare(spec=Breakout, orb=CI._ORB(), price_now=CI.BROKE[-1][3], now_et="10:05",
                            chain=chain, df_1m=CI._df(CI.BROKE), flow_conn=fs.conn, symbol=symbol)

    # the reach this fixture produces, read from the REAL plan (no chain: it stops at the contract)
    p0 = prep("SPX", None)
    T = getattr(p0, "target", None)
    if T is None:
        check("K0 fixture: the plan computes a reach on SPX", False, f"unmet={getattr(p0, 'unmet', None)}")
    else:
        past, inside = round(T + 2.21, 2), round(T - 2.79, 2)
        chain = types.SimpleNamespace(calls=[_c(past, 0.40), _c(inside, 0.55)], puts=[])
        p1 = prep("SPX", chain)
        k1 = getattr(getattr(p1, "contract", None), "strike", None)
        check("K1 SPX long via the REAL prepare: the strike INSIDE the reach, not the nearer one past it",
              k1 == inside, f"reach={T} chose={k1} (past={past}, inside={inside})")
        chain2 = types.SimpleNamespace(calls=[_c(past, 0.40), _c(round(T + 7.21, 2), 0.25)], puts=[])
        p2 = prep("SPX", chain2)
        last = LAST["plan"].planner.last()          # PlanTick.refuse -> _close sets the PLAN's _last (as check_brk_cash_index reads it)
        why = str(last[2]) if last else ""
        check("K2 SPX, only strikes PAST the reach: no contract, the row reads 'contract: ... at or inside'",
              getattr(p2, "contract", "x") is None and why.startswith("contract:") and "at or inside" in why,
              f"contract={getattr(getattr(p2, 'contract', None), 'strike', None)} last={last!r}")

    t = 7812.20
    puts = [_c(round(t - 2.21, 2), -0.40), _c(round(t + 2.79, 2), -0.55)]
    try:
        k3 = OP.select_contract(types.SimpleNamespace(calls=[], puts=puts), "short", t, inside=True)
        k3 = getattr(k3, "strike", None)
    except Exception as exc:                                    # noqa: BLE001
        k3 = f"raised {type(exc).__name__}: {exc}"
    check("K3 inside=True, a SHORT: the put inside (above) the reach", k3 == round(t + 2.79, 2), f"chose={k3}")

    calls = [_c(7840.0, 0.50), _c(7845.0, 0.40)]
    try:
        k4 = getattr(OP.select_contract(types.SimpleNamespace(calls=calls, puts=[]), "long", 7840.0,
                                        inside=True), "strike", None)
    except Exception as exc:                                    # noqa: BLE001
        k4 = f"raised {type(exc).__name__}: {exc}"
    check("K4 inside=True takes a strike exactly AT the reach", k4 == 7840.0, f"chose={k4}")

    k5 = getattr(OP.select_contract(types.SimpleNamespace(calls=calls, puts=[]), "long", 7842.79),
                 "strike", None)
    check("K5 UNCHANGED: the default is the nearest strike (7845 for a 7842.79 reach)", k5 == 7845.0,
          f"chose={k5}")

    src = open(os.path.join(ROOT, "strategy", "breakout_plan.py"), encoding="utf-8").read()
    calls_ = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call)
              and getattr(n.func, "id", getattr(n.func, "attr", "")) == "select_contract"]
    kw = [k.arg for c in calls_ for k in c.keywords]
    seg = ast.get_source_segment(src, calls_[0]) if calls_ else ""
    check("K6 Breakout's one select_contract call passes inside= ONLY as the cash-index flag",
          len(calls_) == 1 and kw == ["inside"] and "cash_index" in seg, f"calls={len(calls_)} kw={kw} src={seg!r}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
