#!/usr/bin/env python3
"""
tests/check_brk_cash_index.py  v1.0
ON A CASH INDEX, BREAKOUT'S TAPE AND BOOK BARS ARE NOT APPLICABLE - NEVER A REFUSAL (BRK.6).

v1.0  2026-10-05  OTV4TEST r251 - found and authored on SPX-TEST. SPX has no time-and-sale and no resting
      size: on 2026-10-05 flow_imbalance and depth_ratio were None on 220 of 220 SPX plan ticks, flow_commit
      FAILED on every one, and Breakout could not trade SPX by construction (mainline's SPX book: 0 Breakout
      in 192 trades). The operator, 11:09 ET: "I agree and we have to get SPX Trading those breakouts";
      11:28 ET, on depth too: "Yes, do it."

  C1  SPX, research window open: flow_commit is MET and says "n/a - cash index, no tape"
  C2  SPX, research window open: depth_thin is MET and says "n/a - cash index, no book"
  C3  SPX, PAST the research window (fitted dials bind): flow_commit still MET
  C4  SPX, PAST the research window: depth_thin still MET
  C5  SPX: the raw readings are still recorded (flow_imbalance, flow_tagged, depth_ratio checks present)
  C6  QQQ (not an index), research window open: a missing flow reading still REFUSES (unchanged)
  C7  QQQ, PAST the research window: missing flow AND missing depth both REFUSE (unchanged)
  C8  the REAL Breakout.generate_signal does not hold an SPX trigger as "trigger incomplete"
      (its PERSISTENT re-check reads the plan's conditions); it reaches the price-vs-trigger test
  C9  CONTROL for C8: the same fire path on QQQ still holds "trigger incomplete - flow_commit"
  C10 _route: an index's absent book is not a FADING book - no HARVEST deferral on SPX on that alone;
      QQQ with the same absent book still defers (unchanged)

Drives the REAL BreakoutPlan.prepare (flow read through a scratch store built by the REAL FeedStore, which
holds no prints, exactly like SPX), the REAL Breakout.generate_signal and the REAL BreakoutPlan._route.
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3 with no pandas).
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp()
os.environ["OT_TRADES_DB"] = os.path.join(_TD, "t.db")
os.environ["OT_DERIVED_DB"] = os.path.join(_TD, "d.db")
os.environ["OT_FEED_DB"] = os.path.join(_TD, "f.db")
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


class _ORB:
    orb_high, orb_low = 101.00, 100.00


# five range bars, a bar CLOSING beyond the high, then the live bar (check_breakout's BROKE)
BROKE = [(100.2, 100.9, 100.0, 100.5, 900)] * 5 + \
        [(100.6, 101.40, 100.55, 101.30, 2400), (101.3, 101.4, 101.2, 101.35, 800)]


def _df(rows):
    import pandas as pd
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c, "volume": v} for o, h, l, c, v in rows],
        index=pd.date_range("2026-10-05 09:30", periods=len(rows), freq="1min"))


def main():
    try:
        import pandas  # noqa: F401
        import strategy.breakout as B
        from strategy.breakout import Breakout
        from strategy.breakout_plan import BreakoutPlan
        from data.candle_feed import FeedStore
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2

    fs = FeedStore(os.environ["OT_FEED_DB"])                    # real schema, ZERO prints: an index's tape
    flow_conn = fs.conn
    research_open, research_closed = "2099-12-31", "2026-10-04"

    def prep(symbol, until):
        B.RESEARCH_UNTIL = until
        plan = BreakoutPlan()
        return plan, plan.prepare(spec=Breakout, orb=_ORB(), price_now=BROKE[-1][3], now_et="10:05",
                                  chain=None, df_1m=_df(BROKE), flow_conn=flow_conn, symbol=symbol)

    def cnd(p, name):
        return p.conditions.get(name, (None, "", None))

    def note(p, name):
        return (getattr(p.tick, "check_notes", {}) or {}).get(name, "")

    _, s_open = prep("SPX", research_open)
    check("C1 SPX (research open): flow_commit MET, 'n/a - cash index, no tape'",
          cnd(s_open, "flow_commit")[2] is True and "flow_commit" not in s_open.unmet
          and "no tape" in note(s_open, "flow_commit"),
          f"met={cnd(s_open, 'flow_commit')[2]} note={note(s_open, 'flow_commit')!r} unmet={s_open.unmet}")
    check("C2 SPX (research open): depth_thin MET, 'n/a - cash index, no book'",
          cnd(s_open, "depth_thin")[2] is True and "no book" in note(s_open, "depth_thin"),
          f"met={cnd(s_open, 'depth_thin')[2]} note={note(s_open, 'depth_thin')!r}")

    _, s_closed = prep("SPX", research_closed)
    check("C3 SPX (PAST research, fitted dials bind): flow_commit still MET",
          cnd(s_closed, "flow_commit")[2] is True and "flow_commit" not in s_closed.unmet,
          f"research_active={B.research_active()} unmet={s_closed.unmet}")
    check("C4 SPX (PAST research): depth_thin still MET",
          cnd(s_closed, "depth_thin")[2] is True and "depth_thin" not in s_closed.unmet,
          f"unmet={s_closed.unmet}")
    check("C5 SPX: the raw readings are still recorded",
          all(k in s_open.tick.checks for k in ("flow_imbalance", "flow_tagged", "depth_ratio")),
          f"recorded={[k for k in ('flow_imbalance', 'flow_tagged', 'depth_ratio') if k in s_open.tick.checks]}")

    _, q_open = prep("QQQ", research_open)
    check("C6 QQQ (research open): a missing flow reading still REFUSES (unchanged)",
          cnd(q_open, "flow_commit")[2] is False and "flow_commit" in q_open.unmet,
          f"unmet={q_open.unmet}")
    _, q_closed = prep("QQQ", research_closed)
    check("C7 QQQ (PAST research): missing flow AND missing depth both REFUSE (unchanged)",
          "flow_commit" in q_closed.unmet and "depth_thin" in q_closed.unmet,
          f"unmet={q_closed.unmet}")

    # ── the REAL fire path: generate_signal re-checks PERSISTENT off the plan's conditions ──
    def fire(symbol):
        plan, p = prep(symbol, research_open)
        p.ready = True                       # every OTHER bar is not under test here
        p.trigger = 999.0                    # price 101.35 is NOT beyond it: the next test after PERSISTENT
        p.tick = plan.planner.tick(p.price_now)   # a READY plan leaves its tick open for the strategy
        strat = Breakout.__new__(Breakout)
        strat._plan = plan
        strat.prepare = lambda **kw: p
        strat.generate_signal()
        return (plan.planner._last or (None, "", ""))[2] if hasattr(plan, "planner") else ""

    why_spx = fire("SPX")
    check("C8 REAL generate_signal: SPX passes the PERSISTENT re-check, reaches the trigger test",
          "trigger incomplete" not in why_spx and "trigger not in place" in why_spx, why_spx[:90])
    why_qqq = fire("QQQ")
    check("C9 CONTROL: QQQ on the same path still holds 'trigger incomplete - flow_commit'",
          "trigger incomplete" in why_qqq and "flow_commit" in why_qqq, why_qqq[:90])

    # ── _route: absent book on an index is not a fading book ──
    def route(symbol):
        plan, p = prep(symbol, research_open)
        p.unmet = list(p.unmet)
        p.pool_dist_r, p.pool_price, p.pool_name = 0.30, 101.80, "rth"
        p.conditions["gamma_regime"] = (-0.5, "", True)        # a regime the fitted dial accepts
        p.verdict = "WAIT"
        plan._route(p, plan.planner.tick(101.35), B)
        return p.verdict
    v_spx, v_qqq = route("SPX"), route("QQQ")
    check("C10 _route: SPX's absent book does not defer as a HARVEST; QQQ's still does (unchanged)",
          v_spx != "DEFER" and v_qqq == "DEFER", f"SPX={v_spx} QQQ={v_qqq}")

    fs.conn.close()
    print(("RED - " + f"{len(FAILED)} of {len(RAN)} failed: " + " ".join(FAILED)) if FAILED
          else f"GREEN - {len(RAN)} of {len(RAN)} passed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
