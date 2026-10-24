#!/usr/bin/env python3
"""
tests/check_brk_zero_risk.py  v1.0
A BREAK BAR THAT CLOSED AT ITS OWN EXTREME IS REFUSED AT stop_survivable - NEVER A TypeError (BRK.7).

v1.0  2026-10-08  OTV4TEST r263. Found on SPX-TEST 10-08: 56 "Breakout raised during dispatch ... TypeError:
      unsupported format string passed to NoneType.__format__" (QQQ-TEST: 77 on 10-07). The SHORT break bars
      at 11:57, 11:59 and 12:53 closed AT their high, so stop = close, risk 0, r None; while `r` accepts
      "any" nothing refused, prepare reached TAKE and trade_line formatted R None. The operator, 2026-10-08
      16:40 ET: "Yes, to all".

  Z1  the REAL BreakoutPlan.prepare, a SHORT break bar closing AT its high: no exception, not ready, refused
      at stop_survivable with "zero risk: the break bar closed at its own extreme"
  Z2  the same, a LONG break bar closing AT its low
  Z3  CONTROL - a normal break (risk > 0) on the same chain still reaches TAKE (ready), and stop_survivable
      is not the refusal
  Z4  the refusal writes stop_survivable as a FAILED check on the plan row (recorded, not a gap)

Every case runs the research window OPEN (B.RESEARCH_UNTIL far ahead) - the only state in which the crash
can happen (after it, accepts('r', None) is False and the r refusal fires first). Drives the REAL
BreakoutPlan.prepare on the instrument named by OT_INSTRUMENT. On a cash index (SPX) the whole path is REAL. On
any other symbol the scratch store holds no prints, so flow_commit would refuse first and the zero-risk path
would never be reached (check_brk_strike_inside K6 hit the same wall): there, and ONLY there, BreakoutPlan._flow
is replaced by a committed reading in the break's direction (imbalance +/-0.5, tagged 0.9) - flow is not what
this gate tests. NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
"""
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
REASON = "zero risk: the break bar closed at its own extreme"


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class _ORB:
    orb_high, orb_low = 101.00, 100.00


RANGE = [(100.2, 100.9, 100.0, 100.5, 900)] * 5
# (open, high, low, close, volume): the break bar, then the live bar
SHORT_AT_HIGH = RANGE + [(99.6, 99.70, 99.40, 99.70, 2400), (99.7, 99.75, 99.6, 99.65, 800)]
LONG_AT_LOW = RANGE + [(101.4, 101.60, 101.30, 101.30, 2400), (101.3, 101.4, 101.25, 101.35, 800)]
NORMAL_LONG = RANGE + [(100.6, 101.40, 100.55, 101.30, 2400), (101.3, 101.4, 101.2, 101.35, 800)]


def _df(rows):
    import pandas as pd
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c, "volume": v} for o, h, l, c, v in rows],
        index=pd.date_range("2026-10-08 09:30", periods=len(rows), freq="1min"))


def _c(strike, delta):
    return types.SimpleNamespace(strike=float(strike), mark=2.0, bid=1.9, ask=2.1, delta=delta, gamma=0.05,
                                 symbol=f"X{strike}", streamer_symbol=f".X{strike}")


# strikes on a 0.5 grid around the fixture's prices: one is at/inside any reach this fixture produces
CHAIN = types.SimpleNamespace(
    calls=[_c(k / 2, 0.5) for k in range(196, 208)],
    puts=[_c(k / 2, -0.5) for k in range(194, 206)])


def main():
    print("check_brk_zero_risk")
    try:
        import pandas  # noqa: F401
        import config
        import strategy.breakout as B
        from strategy.breakout import Breakout
        from strategy.breakout_plan import BreakoutPlan
        from data.candle_feed import FeedStore
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2

    symbol = getattr(config, "INSTRUMENT", None) or os.environ.get("OT_INSTRUMENT", "QQQ")
    print(f"  instrument {symbol}")
    fs = FeedStore(os.environ["OT_FEED_DB"])
    B.RESEARCH_UNTIL = "2099-12-31"
    import strategy.breakout_plan as BP
    cash = bool(BP._cash_index(symbol))
    SIDE = {"dir": "long"}
    if not cash:                                                # see the header: flow is stubbed off-index only
        BreakoutPlan._flow = staticmethod(lambda conn, sym: (0.5 if SIDE["dir"] == "long" else -0.5, 0.9))
    print(f"  cash index: {cash} ({'flow REAL, n/a' if cash else 'flow STUBBED, committed with the break'})")

    def run(rows):
        """(prep, plan, last, exc) from the REAL prepare; an exception is CAUGHT and returned, never raised."""
        SIDE["dir"] = "long" if rows[5][3] > _ORB.orb_high else "short"
        plan = BreakoutPlan()
        try:
            p = plan.prepare(spec=Breakout, orb=_ORB(), price_now=rows[-1][3], now_et="10:05",
                             chain=CHAIN, df_1m=_df(rows), flow_conn=fs.conn, symbol=symbol)
            exc = None
        except Exception as e:                                  # noqa: BLE001
            p, exc = None, e
        last = plan.planner.last() if exc is None else None
        return p, plan, last, exc

    def refused_zero(tag, rows, side):
        p, plan, last, exc = run(rows)
        why = str(last[2]) if last else ""
        ok = (exc is None and p is not None and not getattr(p, "ready", True)
              and why.startswith("stop_survivable:") and REASON in why)
        detail = (f"raised {type(exc).__name__}: {exc}" if exc else
                  f"ready={getattr(p, 'ready', None)} risk={getattr(p, 'risk', None)} last={last!r}")
        check(f"{tag} a {side} break bar closing AT its own extreme: refused at stop_survivable, '{REASON}'",
              ok, detail)
        return p

    refused_zero("Z1", SHORT_AT_HIGH, "SHORT")
    p2 = refused_zero("Z2", LONG_AT_LOW, "LONG")

    p3, _, last3, exc3 = run(NORMAL_LONG)
    check("Z3 CONTROL: a normal long break (risk > 0) on the same chain still reaches TAKE",
          exc3 is None and p3 is not None and getattr(p3, "ready", False) and (getattr(p3, "risk", 0) or 0) > 0
          and getattr(p3, "verdict", None) == "TAKE",
          f"raised {type(exc3).__name__}: {exc3}" if exc3 else
          f"ready={getattr(p3, 'ready', None)} verdict={getattr(p3, 'verdict', None)} unmet={getattr(p3, 'unmet', None)} last={last3!r}")

    rec = (getattr(getattr(p2, "tick", None), "checks", {}) or {}).get("stop_survivable") if p2 else None
    check("Z4 the zero-risk refusal records stop_survivable as a FAILED check on the plan row",
          rec is not None and rec[1] is False, f"checks[stop_survivable]={rec!r}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
