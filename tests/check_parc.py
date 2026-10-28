#!/usr/bin/env python3
"""
tests/check_parc.py  v5.1
v5.1  2026-10-28  OTV5 r50 (PARC.3) — PARC'S DEFAULT IS log (paused). P13 now expects unset -> log/log and an unknown value
      -> log, named; the trading checks set OT_PARC=1 explicitly, as a box that opts in would. The operator: "Don't go live on the PARC tomorrow until we find a better stop placement."
v5.0  2026-10-27  OTV5 r46 (PARC.1) — new. PARC: PARK'S ENTRY, A CREDIT SPREAD ON THE SAFER SIDE, THE BREAKOUT RAMP, THE
      STRUCTURE STOP, THE NICKEL, EOD.1, THE LADDER. The operator, 2026-10-27: "under identical entry conditions the PARK
      trade sells a credit spread ATM nearest the strike on the safer side ..."; "Call it PARC"; "I want 1050 to be the
      floor & use the same ramp in configure.sh (most are set to $2500)"; "No shadow mode. We're paper. It trades
      tomorrow."; "I also want to make sure it uses the ladder entry & exit."
      Drives the REAL plan, strategy, RiskManager, ExitEngine, PositionManager._execute_exit, main._attempt_park /
      _attempt_parc / _execute_condor_leg / _post_credit_vertical and the trade ledger, with stubbed chains, clocks,
      frames and a scratch feed store.

  P1  a LONG (up first hour, gap up) sells the first listed put strictly below the 11:00 close and buys the next lower
      put; the 11:00 close ON a strike skips it (strictly below); the stop is the 5m swing LOW behind it
  P2  a SHORT sells the first call strictly above and buys the next call above; the stop is the 5m swing HIGH
  P3  a credit under PARC_MIN_CREDIT (0.20 = 4 x the nickel) is refused at min_credit; no 5m swing behind the price,
      or an unreadable store, is refused at structure_stop (fail closed)
  P4  sizing (risk_manager rule parc_ramp, $1,050 risk / $2,500 top): a tight stop takes min(by_risk, by_top) > 1, a
      wide stop takes 1, one spread over the top REFUSES, no IV sizes on the max loss; the plan's value at the stop is
      a Black-Scholes number at the legs' IV (None without IV)
  P5  the structure stop: a touch through underlying_stop exits "structure_stop: touch X through Y"; inside holds
  P6  the nickel: a spread that can be bought for <= 0.05 exits nickel_close; paper books 0.05; live rests AT 0.05
  P7  EOD.1: at 15:46 a RESTING best-case buy-back (eod_resting; paper holds it, nothing booked); 15:50 still resting
      (EOD.1 has no ladder rung for a short-leg structure); 15:55 crosses (eod_cross; paper books the mark)
  P8  no delta exit, no PARK lock, no premium stop, no management plan ever fires for PARC
  P9  PARC and PARK both fire in the same 11:01 window on one box (main._attempt_park / _attempt_parc), in the normal
      dispatch and the capped branch; both are admitted, cap-exempt, one per session
  P10 PARK unchanged: tests/check_park.py green, and PARK on P1's tape is still the 702 CALL at the ask
  P11 the ladder: paper books limit_ladder.paper_fill_credit (the knob moves the booked credit), live posts the
      entry ladder's rung through _post_credit_vertical (key cv:<sym>:PARC:<side>); exits go through _exit_policy /
      _exit_limit (structure stop: floor at the mark; nickel 0.05; EOD resting best case, cross at 15:55)
  P12 the record: every credit-vertical column, PARK's signal columns, strategy PARC, is_condor_leg 0; P&L for a
      credit (credit - exit) x n x 100; the fee model prices it as a two-leg vertical
  P13 config / switch: OT_PARC unset -> trade, log, 0 -> off, junk named; plan_state; configure.sh item 15

Born red on 9ab0f20 (PARC absent: P0).
Run:  python3 tests/check_parc.py
"""
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from datetime import date, datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_parc_")
os.environ["OT_TRADES_DB"] = os.path.join(_TD, "t.db")
os.environ["OT_DERIVED_DB"] = os.path.join(_TD, "d.db")
FEED = os.path.join(_TD, "f.db")
os.environ["OT_FEED_DB"] = FEED
os.environ["OT_LOG_FILE"] = os.path.join(_TD, "bot.log")
os.environ["OT_SIGNAL_JOURNAL_DIR"] = os.path.join(_TD, "sj")
os.environ["OT_RESTING_DB"] = os.path.join(_TD, "r.db")
os.environ["OT_RESTING_STOP_STATE"] = os.path.join(_TD, "rs.json")
os.environ["OT_COUNTERFACTUAL_DIR"] = os.path.join(_TD, "cf")
os.environ["OT_PLAN_STATES_FILE"] = os.path.join(_TD, "ps.json")
os.environ["OT_RISK_USD"] = "1050"
os.environ["OT_ORB_BUDGET_USD"] = "2500"
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
for _k in ("OT_PARC", "OT_PARK", "OT_PAPER_FILL_SLIPPAGE_PCT"):
    os.environ.pop(_k, None)
os.environ["OT_PARC"] = "1"   # r50: the trading checks run PARC as a box that opts in; P13 probes the default
ET = ZoneInfo("America/New_York")
FAILED, RAN = [], []
DAY, PREV = date(2026, 10, 28), date(2026, 10, 27)
SYM = os.environ["OT_INSTRUMENT"]
EXP = DAY.isoformat()


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _ms(d, h, m):
    return int(datetime(d.year, d.month, d.day, h, m, tzinfo=ET).timestamp() * 1000)


def _feed(o930, c1030, c1100, prev_close, lows5=None, highs5=None, with_5m=True):
    """1m bars as check_park writes them, plus 5m bars 10:40-11:00 (11:00's ends 11:05: never read at 11:01)."""
    if os.path.exists(FEED):
        os.remove(FEED)
    c = sqlite3.connect(FEED)
    c.execute("CREATE TABLE candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, ts_epoch_ms INTEGER NOT NULL, "
              "open REAL, high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY (symbol, interval, ts_epoch_ms))")
    rows = [(SYM, "1m", _ms(DAY, 9, 30), o930, o930 + .1, o930 - .1, o930 + .05, 1),
            (SYM, "1m", _ms(DAY, 10, 30), c1030, c1030 + .1, c1030 - .1, c1030, 1),
            (SYM, "1m", _ms(DAY, 11, 0), c1100, c1100 + .1, c1100 - .1, c1100, 1),
            (SYM, "1m", _ms(PREV, 15, 59), 1, 1, 1, prev_close, 1),
            (SYM, "1m", _ms(PREV, 16, 5), 1, 1, 1, prev_close + 5, 1)]
    if with_5m:
        lows5 = lows5 or [c1100 - 1.0] * 5
        highs5 = highs5 or [c1100 + 1.0] * 5
        for i, mm in enumerate((40, 45, 50, 55)):
            rows.append((SYM, "5m", _ms(DAY, 10, mm), c1100, highs5[i], lows5[i], c1100, 1))
        # the 11:00 5m bar is FORMING at 11:01 - its extreme must never be the stop
        rows.append((SYM, "5m", _ms(DAY, 11, 0), c1100, c1100 + 9, c1100 - 9, c1100, 1))
    c.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", rows)
    c.commit()
    c.close()


class K:
    def __init__(self, strike, bid, ask, delta, side, iv=0.20):
        self.strike, self.bid, self.ask, self.delta, self.iv = float(strike), bid, ask, delta, iv
        self.mark, self.expiry, self.option_type = (bid + ask) / 2, EXP, side
        self.symbol = f"{SYM:<6}{DAY:%y%m%d}{side}{int(strike * 1000):08d}"
        self.streamer_symbol = f".X{side}{strike:g}"


def _px(strike, spot, call):
    """a plausible quote: intrinsic + time value falling off with distance."""
    intr = max(spot - strike, 0.0) if call else max(strike - spot, 0.0)
    tv = max(0.05, 1.20 - 0.25 * abs(strike - spot))
    mid = intr + tv
    return round(mid - 0.03, 2), round(mid + 0.03, 2)


class Chain:
    def __init__(self, spot=702.4, iv=0.20, scale=1.0, oneside_strike=None):
        self.expiry, self.spot_price = EXP, spot
        self.calls, self.puts = [], []
        for s in range(690, 716):
            cb, ca = _px(s, spot, True)
            pb, pa = _px(s, spot, False)
            cb, ca, pb, pa = cb * scale, ca * scale, pb * scale, pa * scale
            if s == oneside_strike:
                pb = cb = 0.0
            self.calls.append(K(s, round(cb, 2), round(ca, 2), 0.5, "C", iv))
            self.puts.append(K(s, round(pb, 2), round(pa, 2), -0.5, "P", iv))


NOW = datetime(2026, 10, 28, 11, 1, 5, tzinfo=ET)


def main():
    print("check_parc")
    try:
        import pandas as pd
        import config
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2
    try:
        from strategy.parc import Parc
    except Exception as exc:                                    # noqa: BLE001
        check("P0 PARC exists (strategy/parc.py, strategy/parc_plan.py)", False, f"{type(exc).__name__}: {exc}")
        print("\nRED — 1 of 1 failed: P0")
        return 1
    from strategy import parc_plan as PP
    S = Parc()

    def ask(price=702.4, chain=None, now="11:01", paper=True):
        return S.generate_signal(price_now=price, now_et=now, chain=chain or Chain(spot=price), prior_close=None,
                                 day=DAY, symbol=SYM, paper=paper, now=NOW)

    def prep(price=702.4, chain=None, now="11:01", paper=True):
        return S.prepare(price_now=price, now_et=now, chain=chain or Chain(spot=price), prior_close=None,
                         day=DAY, symbol=SYM, paper=paper, now=NOW)

    # ── P1 long ──────────────────────────────────────────────────────────────
    _feed(700.0, 702.1, 702.4, 699.0, lows5=[701.30, 701.10, 701.60, 701.90])   # +0.30%, gap +1.0; swing low 701.10
    s1 = ask()
    sp, lp = (getattr(s1, "short_put_contract", None), getattr(s1, "long_put_contract", None)) if s1 else (None, None)
    check("P1 LONG: sells the 702 PUT (first strictly below 702.4), buys the 701 PUT; stop = the 5m swing low 701.10",
          s1 is not None and s1.strategy_name == "PARC" and s1.option_side == "put" and s1.direction == "long"
          and sp is not None and float(sp.strike) == 702 and lp is not None and float(lp.strike) == 701
          and s1.short_call_contract is None and abs(float(s1.underlying_stop) - 701.10) < 1e-9
          and s1.is_credit_vertical and s1.is_valid and s1.setup_type == "parc_long",
          f"{s1 and (s1.option_side, sp and sp.strike, lp and lp.strike, s1.underlying_stop, s1.setup_type)}")
    _feed(700.0, 702.1, 702.0, 699.0, lows5=[701.30, 701.10, 701.60, 701.90])   # the 11:00 close ON 702
    s1b = ask(price=702.0)
    check("P1b the 11:00 close ON a strike: strictly below -> sells 701, buys 700",
          s1b is not None and float(s1b.short_put_contract.strike) == 701 and float(s1b.long_put_contract.strike) == 700,
          f"{s1b and (s1b.short_put_contract.strike, s1b.long_put_contract.strike)}")

    # ── P2 short ─────────────────────────────────────────────────────────────
    _feed(700.0, 697.9, 697.6, 701.0, highs5=[698.40, 698.90, 698.20, 697.95])   # -0.30%, gap -1.0; swing high 698.90
    s2 = ask(price=697.6)
    sc, lc = (getattr(s2, "short_call_contract", None), getattr(s2, "long_call_contract", None)) if s2 else (None, None)
    check("P2 SHORT: sells the 698 CALL (first strictly above 697.6), buys the 699 CALL; stop = the 5m swing high 698.90",
          s2 is not None and s2.option_side == "call" and s2.direction == "short" and sc is not None
          and float(sc.strike) == 698 and lc is not None and float(lc.strike) == 699 and s2.short_put_contract is None
          and abs(float(s2.underlying_stop) - 698.90) < 1e-9 and s2.is_valid,
          f"{s2 and (s2.option_side, sc and sc.strike, lc and lc.strike, s2.underlying_stop)}")

    # ── P3 refusals ──────────────────────────────────────────────────────────
    _feed(700.0, 702.1, 702.4, 699.0, lows5=[701.30, 701.10, 701.60, 701.90])
    p3a = prep(chain=Chain(spot=702.4, scale=0.10))
    p3b = prep(chain=Chain(spot=702.4, oneside_strike=701))
    _feed(700.0, 702.1, 702.4, 699.0, lows5=[702.50, 702.60, 702.70, 702.80])  # every 5m low ABOVE the 11:00 close
    p3c = prep()
    _feed(700.0, 702.1, 702.4, 699.0, with_5m=False)
    p3d = prep()
    _feed(700.0, 702.1, 702.4, 699.0, lows5=[701.30, 701.10, 701.60, 701.90])
    p3e = prep(price=701.05)                                                     # already through 701.10 (ENT.1)
    check("P3 credit under 0.20 refused at min_credit; a one-sided leg refused at spread",
          not p3a.ready and p3a.unmet == ["min_credit"] and not p3b.ready and p3b.unmet == ["spread"]
          and abs(config.PARC_MIN_CREDIT - 4 * config.CONDOR_NICKEL_CLOSE) < 1e-9,
          f"{p3a.unmet} credit={p3a.credit} {p3b.unmet}")
    check("P3b no swing behind the price, no 5m bars, or the price already through the stop -> structure_stop (fail closed)",
          p3c.unmet == ["structure_stop"] and p3d.unmet == ["structure_stop"] and p3e.unmet == ["structure_stop"]
          and not (p3c.ready or p3d.ready or p3e.ready), f"{p3c.unmet} {p3d.unmet} {p3e.unmet}")

    # ── P4 sizing ────────────────────────────────────────────────────────────
    from risk.risk_manager import RiskManager
    rm = RiskManager(risk_per_trade=1050.0, paper_trading=True)

    class _Cap(logging.Handler):
        def __init__(self):
            super().__init__(); self.msgs = []

        def emit(self, r):
            self.msgs.append(r.getMessage())
    cap = _Cap(); logging.getLogger("risk.risk_manager").addHandler(cap); logging.getLogger("risk.risk_manager").setLevel(logging.INFO)
    z_t = rm.size_for("parc", spread_width=1.0, credit=0.40, value_at_stop=0.45, budget_usd=2500)   # $5 at the stop
    z_w = rm.size_for("parc", spread_width=10.0, credit=0.40, value_at_stop=9.00, budget_usd=2500)  # $860 at the stop
    z_x = rm.size_for("parc", spread_width=30.0, credit=0.40, value_at_stop=1.0, budget_usd=2500)   # $2,960 max loss
    z_n = rm.size_for("parc", spread_width=5.0, credit=0.40, value_at_stop=None, budget_usd=2500)   # no IV: $460
    check("P4 tight stop: min(by_risk 210, by_top 41) = 41 > 1, rule parc_ramp, a [size] parc_ramp line",
          z_t.allowed and z_t.contracts == 41 and z_t.rule == "parc_ramp"
          and any(m.startswith("[size] parc_ramp:") for m in cap.msgs), f"{z_t.contracts} {z_t.rule} {cap.msgs[-1:]}")
    check("P4b wide stop takes 1; one spread over the $2,500 top REFUSES; no IV sizes on the max loss (1050 // 460 = 2)",
          z_w.allowed and z_w.contracts == 1 and not z_x.allowed and "parc_budget" in z_x.reject_reason
          and z_n.allowed and z_n.contracts == 2 and abs(z_n.risk_per_contract - 460) < 1e-6,
          f"{z_w.contracts} {z_x.allowed}/{z_x.reject_reason} {z_n.contracts}/{z_n.risk_per_contract}")
    v1 = getattr(s1, "parc_value_at_stop", None)
    _feed(700.0, 702.1, 702.4, 699.0, lows5=[701.30, 701.10, 701.60, 701.90])
    s_noiv = ask(chain=Chain(spot=702.4, iv=0.0))
    from execution.fill_observers import bs_price
    _t = (datetime(2026, 10, 28, 16, 0, tzinfo=ET) - NOW).total_seconds() / (365 * 24 * 3600)
    want = bs_price(701.10, 702, _t, 0.20, False) - bs_price(701.10, 701, _t, 0.20, False)
    check("P4c the plan's value at the stop is Black-Scholes at the legs' IV and real time left; None without IV",
          v1 is not None and abs(v1 - want) < 1e-9 and s_noiv is not None
          and getattr(s_noiv, "parc_value_at_stop", 1) is None, f"{v1} vs {want}; noiv {getattr(s_noiv, 'parc_value_at_stop', 1)}")

    # ── P5-P8 exits ──────────────────────────────────────────────────────────
    import execution.exit_engine as XE
    _real = (XE.is_hard_close_time, XE.datetime, XE.now_et)
    _real_dt = XE.datetime

    def at(h, m):
        class _D(_real_dt):
            @classmethod
            def now(cls, tz=None):
                return _real_dt(2026, 10, 28, h, m, 5, tzinfo=ET)
        XE.datetime = _D
        XE.now_et = lambda: _real_dt(2026, 10, 28, h, m, 5, tzinfo=ET)
        XE.is_hard_close_time = lambda: (h, m) >= (15, 40)
    eng = XE.ExitEngine(paper_trading=True)
    live = XE.ExitEngine(paper_trading=False)
    sps, lps = f"{SYM:<6}261028P00702000", f"{SYM:<6}261028P00701000"

    def rec(tid, **kw):
        r = {"trade_id": tid, "strategy": "PARC", "setup_type": "parc_long", "symbol": SYM, "direction": "long",
             "option_side": "put", "entry_premium": 0.40, "credit_received": 0.40, "contracts": 10,
             "stop_premium": 0.0, "target_premium": 0.05, "underlying_stop": 701.10, "short_strike": 702.0,
             "long_strike": 701.0, "spread_width": 1.0, "short_symbol": sps, "long_symbol": lps,
             "option_symbol": sps, "is_condor_leg": 0, "is_butterfly": 0, "current_delta": 0.05,
             "entry_time": "2026-10-28T15:01:10+00:00"}
        r.update(kw)
        return r

    def df(last):
        return pd.DataFrame({"open": [last, last], "high": [last, last], "low": [last, last], "close": [702.0, last]})
    try:
        at(12, 0)
        d5a = eng.evaluate(rec("p5a"), 0.60, df_1m=df(701.05))
        d5b = eng.evaluate(rec("p5b"), 0.60, df_1m=df(701.15))
        d5c = eng.evaluate(rec("p5c", direction="short", option_side="call", setup_type="parc_short",
                               underlying_stop=698.90), 0.60, df_1m=df(698.95))
        check("P5 structure stop: long touch 701.05 through 701.10 exits; 701.15 holds; a short touch 698.95 > 698.90 exits",
              d5a.should_exit and d5a.exit_reason.startswith("structure_stop: touch 701.05 through 701.10")
              and not d5b.should_exit and d5c.should_exit and d5c.exit_reason.startswith("structure_stop: touch 698.95"),
              f"{d5a.exit_reason!r} {d5b.exit_reason!r} {d5c.exit_reason!r}")

        r6 = rec("p6")
        d6 = eng.evaluate(r6, 0.04, df_1m=df(703.0))
        r6b = rec("p6b", _exit_ask=0.05)
        d6b = eng.evaluate(r6b, 0.06, df_1m=df(703.0))
        d6c = eng.evaluate(rec("p6c", _exit_ask=0.08), 0.07, df_1m=df(703.0))
        f6 = eng.place_exit_order(dict(r6), d6.exit_reason, mark_price=0.04)
        l6 = live._exit_limit(dict(r6), d6.exit_reason, 0.04, "buy", "vertical")
        check("P6 nickel: mark 0.04 or ask 0.05 exits nickel_close, ask 0.08 holds; paper books 0.05; live rests AT 0.05",
              d6.should_exit and d6.exit_reason.startswith("nickel_close") and d6b.should_exit
              and not d6c.should_exit and f6.confirmed and abs(f6.fill_price - 0.05) < 1e-9 and abs(l6[0] - 0.05) < 1e-9,
              f"{d6.exit_reason!r} {d6b.exit_reason!r} {d6c.exit_reason!r} fill={f6.fill_price} live={l6}")

        eod = rec("p7", _eod_spot=703.0, _eod_iv={sps: 0.20, lps: 0.20}, _eod_iv_atm=0.20)
        at(15, 44)
        d7a = eng.evaluate(dict(eod), 0.15, df_1m=df(703.0))
        at(15, 46)
        d7 = eng.evaluate(dict(eod), 0.15, df_1m=df(703.0))
        pol7 = XE.ExitEngine._exit_policy(eod, d7.exit_reason)
        lim7 = live._exit_limit(dict(eod), d7.exit_reason, 0.15, "buy", "vertical")
        f7 = eng.place_exit_order(dict(eod), d7.exit_reason, mark_price=0.15)
        at(15, 50)
        d7c = eng.evaluate(dict(eod), 0.15, df_1m=df(703.0))
        pol7c = XE.ExitEngine._exit_policy(eod, d7c.exit_reason)
        at(15, 55)
        pol7d = XE.ExitEngine._exit_policy(eod, d7c.exit_reason)
        f7d = eng.place_exit_order(dict(eod, _eod_iv={}, _eod_iv_atm=0.0), d7c.exit_reason, mark_price=0.15)
        check("P7 15:44 holds; 15:46 a RESTING best-case buy-back (eod_resting, best-case limit; paper held, not booked)",
              not d7a.should_exit and d7.should_exit and d7.exit_reason == "hard_close_resting_15:45_ET"
              and pol7 == "eod_resting" and "eod resting — best case" in lim7[1]
              and not f7.confirmed and f7.held, f"{d7a.exit_reason!r} {d7.exit_reason!r} {pol7} {lim7} {f7.detail}")
        check("P7b 15:50 still resting (no ladder rung for a short leg in EOD.1); 15:55 crosses, paper books the mark",
              pol7c == "eod_resting" and pol7d == "eod_cross" and f7d.confirmed and abs(f7d.fill_price - 0.15) < 1e-9,
              f"{pol7c} {pol7d} {f7d.fill_price} {f7d.detail}")

        at(12, 30)
        r8 = rec("p8", current_delta=0.02, _exit_bid=0.01, _exit_ask=0.90)
        d8 = [eng.evaluate(r8, m, df_1m=df(703.0)) for m in (0.39, 0.80, 0.95, 0.30)]
        from strategy import management as MG
        check("P8 no delta exit, no PARK lock, no premium stop: |delta| 0.02 and a mark at 2.4x the credit HOLD; "
              "no _park_* state; no management plan covers PARC",
              not any(d.should_exit for d in d8) and not any(k.startswith("_park") for k in r8)
              and not MG.covers(r8, [r8]) and MG.get_management_plan().decide(r8, 0.95, df_1m=df(703.0)) is None,
              f"{[d.exit_reason for d in d8]} {[k for k in r8 if k.startswith('_park')]}")

        # P11 exits through the exit ladder path
        r11 = rec("p11")
        why11 = d5a.exit_reason
        pol11 = XE.ExitEngine._exit_policy(r11, why11)
        lim11 = live._exit_limit(dict(r11, _exit_bid=0.55, _exit_ask=0.65), why11, 0.60, "buy", "vertical")
        f11 = eng.place_exit_order(dict(r11), why11, mark_price=0.60)
    finally:
        XE.is_hard_close_time, XE.datetime, XE.now_et = _real
    from execution.limit_ladder import limit_at_mark
    check("P11b exits: the structure stop is a floor at the mark (limit_at_mark, no walk), paper books the mark",
          pol11 == "floor" and abs(lim11[0] - limit_at_mark(0.60, floor=0.01)) < 1e-9 and "floor" in lim11[1]
          and f11.confirmed and abs(f11.fill_price - 0.60) < 1e-9, f"{pol11} {lim11} {f11.fill_price}")

    # ── P9 / P11 / P12 through main ─────────────────────────────────────────
    import main as MN
    import utils.time_utils as TU
    from execution import position_manager as PMOD
    from database.trade_logger import get_trade_logger
    _keep = (MN.now_et, TU.now_et, MN._execute_entry_signal, MN._execute_condor_leg, MN.entries_open,
             MN.get_alert_manager)
    calls = []

    class _St:
        paper_trading = True
        tick_count = 1
    try:
        MN.now_et = lambda: NOW
        TU.now_et = lambda: NOW
        MN._set_admission(None)
        MN._execute_entry_signal = lambda sig, ctx, ms, state, _sj=None, additive=False: calls.append(("PARK", sig.strategy_name))
        MN._execute_condor_leg = lambda sig, state, ctx=None: calls.append(("PARC", sig.strategy_name))
        _feed(700.0, 702.1, 702.4, 699.0, lows5=[701.30, 701.10, 701.60, 701.90])
        ctx = {"price": 702.4, "chain": Chain(spot=702.4), "gap": {"prior_close": 699.0}}
        MN._attempt_park(ctx, None, _St(), chain=ctx["chain"])
        MN._attempt_parc(ctx, None, _St(), chain=ctx["chain"])
        MN._attempt_park(ctx, None, _St())                    # the capped branch passes no chain
        MN._attempt_parc(ctx, None, _St())
        src = open(os.path.join(ROOT, "main.py")).read()
        capped = src[src.find("if _cap_hit:\n        if not _adm_ok:"):][:700]
        normal = "_attempt_park(ctx, ms, state, chain=chain)" in src and "_attempt_parc(ctx, ms, state, chain=chain)" in src
        adm = {n: PMOD.decide(PMOD.Facts(strategy=n, now_et=(11, 1), trading_day=True, orb_established=True,
                                         cap_intact=False, past_hard_close=False,
                                         open_by_strategy={o: 1})).admitted
               for n, o in (("PARK", "PARC"), ("PARC", "PARK"))}             # each with the OTHER open
        rl = PMOD.rules().get("PARC")
        check("P9 one box, 11:01: PARK and PARC both fire (normal dispatch and capped branch); each admitted at the cap "
              "with the other open; PARC one try, one open, 11:01-11:03",
              calls == [("PARK", "PARK"), ("PARC", "PARC"), ("PARK", "PARK"), ("PARC", "PARC")] and normal
              and "_attempt_parc(ctx, ms, state)" in capped and capped.find("_attempt_park(") < capped.find("_attempt_parc(")
              and adm == {"PARK": True, "PARC": True} and rl is not None and rl.cap_exempt
              and rl.max_tries_per_session == 1 and rl.max_open_of_type == 1
              and tuple(map(tuple, rl.window)) == ((11, 1), (11, 3)) and "PARC" in config.CAP_EXCLUDED_STRATEGIES
              and MN._STRUCTURE_BY_NAME.get("PARC") == "vertical", f"{calls} {adm} {rl}")
    finally:
        MN._execute_entry_signal, MN._execute_condor_leg = _keep[2], _keep[3]

    # P11 / P12: the REAL credit door, paper then live
    import execution.limit_ladder as LL
    from execution import ladder_registry as LR
    try:
        MN.entries_open = lambda: True

        class _Am:
            def _send(self, *a, **k):
                return None
        MN.get_alert_manager = lambda: _Am()
        _feed(700.0, 702.1, 702.4, 699.0, lows5=[701.30, 701.10, 701.60, 701.90])
        sig = ask()
        _fr = LL._paper_friction
        LL._paper_friction = lambda: 0.10
        try:
            MN._execute_condor_leg(sig, _St(), None)
        finally:
            LL._paper_friction = _fr
        rows = [r for r in get_trade_logger().get_open_trades() if r.get("strategy") == "PARC"]
        row = rows[-1] if rows else {}
        want_c = round(sig.net_credit * 0.90, 4)
        check("P11 paper entry books limit_ladder.paper_fill_credit (the knob at 10% books 0.90 x the mark credit)",
              bool(row) and abs(float(row.get("credit_received") or 0) - want_c) < 1e-9
              and abs(float(row.get("entry_premium") or 0) - want_c) < 1e-9,
              f"credit_received={row.get('credit_received')} want={want_c} mark={sig.net_credit}")
        cols = {k: row.get(k) for k in ("strategy", "setup_type", "direction", "option_side", "short_strike",
                                        "long_strike", "short_symbol", "long_symbol", "spread_width",
                                        "credit_received", "max_loss", "total_cost", "underlying_stop",
                                        "underlying_entry", "contracts", "entry_premium", "stop_premium",
                                        "target_premium", "is_condor_leg", "strike", "expiry", "option_symbol",
                                        "paper_trade", "order_id", "status", "setup_grade", "underlying_target",
                                        "is_fed_day", "is_butterfly")}
        n = int(cols["contracts"] or 0)
        w = float(cols["spread_width"] or 0)
        good = (cols["strategy"] == "PARC" and cols["setup_type"] == "parc_long" and cols["direction"] == "long"
                and cols["option_side"] == "put" and float(cols["short_strike"]) == 702 and float(cols["long_strike"]) == 701
                and cols["short_symbol"] == sig.short_put_contract.symbol and cols["long_symbol"] == sig.long_put_contract.symbol
                and w == 1.0 and n >= 1 and abs(float(cols["max_loss"]) - (w - want_c) * n * 100) < 1e-6
                and abs(float(cols["underlying_stop"]) - 701.10) < 1e-9 and float(cols["stop_premium"]) == 0.0
                and abs(float(cols["target_premium"]) - 0.05) < 1e-9 and int(cols["is_condor_leg"]) == 0
                and float(cols["strike"]) == 702 and cols["expiry"] == EXP and int(cols["paper_trade"]) == 1
                and cols["status"] == "open" and cols["underlying_target"] is not None and cols["is_fed_day"] is not None)
        check("P12 the row: every credit-vertical column, PARK's signal columns, strategy PARC, is_condor_leg 0, stop 0",
              good, json.dumps(cols, default=str))
        rm_size = MN.get_risk_manager().size_for("parc", spread_width=1.0, credit=want_c,
                                                 value_at_stop=sig.parc_value_at_stop)
        check("P12b the door sized on parc_ramp (contracts = the rule's)", rm_size.rule == "parc_ramp" and n == rm_size.contracts,
              f"{n} vs {rm_size.contracts} {rm_size.rule}")
        from unittest import mock
        import execution.exit_engine as XE2

        class _Fill(XE2.ExitEngine):
            def place_exit_order(self, record, reason, mark_price=None):
                return XE2.FillResult(confirmed=True, fill_price=0.05, detail="test")
        booked = {}
        tl = get_trade_logger()
        _le = tl.log_exit
        tl.log_exit = lambda trade_id, exit_price, pnl_usd, exit_reason, excursion=None: booked.update(
            pnl=pnl_usd, px=exit_price)
        _gee, _am = PMOD.get_exit_engine, PMOD._rs.active_mode
        try:
            PMOD._rs.active_mode = lambda paper: "off"
            _fe = _Fill(True)
            PMOD.get_exit_engine = lambda paper=True: _fe
            self_ = mock.MagicMock(paper_trading=True, _trade_logger=tl)
            try:
                PMOD.PositionManager._execute_exit(self_, dict(row), XE2.ExitDecision(True, "nickel_close pnl=87%"), 0.05)
            except Exception as exc:                            # noqa: BLE001
                print(f"      (_execute_exit raised after booking: {type(exc).__name__}: {exc})")
        finally:
            PMOD.get_exit_engine, PMOD._rs.active_mode = _gee, _am
            tl.log_exit = _le
        want_pnl = (want_c - 0.05) * n * 100
        sys.path.insert(0, os.path.join(ROOT, "tests"))
        import fees as FZ
        fb = FZ.fees_for(dict(row, status="closed", exit_premium=0.05))
        check("P12c P&L for a credit: (credit - exit) x n x 100; the fee model prices a two-leg credit vertical",
              abs(float(booked.get("pnl", -1e9)) - want_pnl) < 0.02 and getattr(fb, "structure", "") == "condor_leg"
              and {l.leg for l in (getattr(fb, "legs", []) or [])} == {"short", "long"},
              f"pnl={booked.get('pnl')} want={want_pnl:.2f} fees={getattr(fb, 'structure', fb)}")

        # live: the door walks the entry ladder through _post_credit_vertical
        posted = []
        _pcv = MN._post_credit_vertical

        def _wrap(sc, lc, contracts, lkey, structure, **kw):
            from execution.order_confirm import EntryFill

            def placer(legs, limit):
                posted.append((lkey, limit, legs))
                return type("R", (), {"errors": None, "order": "o1"})()

            def confirmer(placed, basis, deadline_s):
                return EntryFill(filled=True, quantity=contracts, net_price=posted[-1][1], order_id="o1")
            return _pcv(sc, lc, contracts, lkey, structure, placer=placer, confirmer=confirmer, **kw)
        MN._post_credit_vertical = _wrap
        LR.reset_all()

        class _Live(_St):
            paper_trading = False
        try:
            MN._execute_condor_leg(sig, _Live(), None)
        finally:
            MN._post_credit_vertical = _pcv
        sb, sa = sig.short_put_contract.bid, sig.short_put_contract.ask
        lb, la = sig.long_put_contract.bid, sig.long_put_contract.ask
        LR.reset_all()
        first = LR.price_for("probe", "sell", max(0.0, sb - la), max(0.0, sa - lb), SYM,
                             structure=f"{sig.short_put_contract.symbol}|{sig.long_put_contract.symbol}")
        LR.reset_all()
        check("P11c live entry: _execute_condor_leg posts through _post_credit_vertical at the entry ladder's first rung "
              "(key cv:<sym>:PARC:put; the walk starts above the mark credit)",
              len(posted) == 1 and posted[0][0] == f"cv:{SYM}:PARC:put" and first is not None
              and abs(posted[0][1] - first[0]) < 1e-9 and posted[0][1] >= sig.net_credit - 1e-9,
              f"{posted} first={first} mark={sig.net_credit}")
    finally:
        (MN.now_et, TU.now_et, MN._execute_entry_signal, MN._execute_condor_leg, MN.entries_open,
         MN.get_alert_manager) = _keep

    # ── P10 PARK unchanged ───────────────────────────────────────────────────
    from strategy.park import Park
    config.PARK_MODE = "trade"
    _feed(700.0, 702.1, 702.4, 699.0, lows5=[701.30, 701.10, 701.60, 701.90])

    class PK:
        def __init__(self):
            ch = Chain(spot=702.4)
            self.calls, self.puts, self.expiry = ch.calls, ch.puts, EXP
    pk = Park().generate_signal(price_now=702.4, now_et="11:01", chain=PK(), prior_close=None, day=DAY, symbol=SYM)
    c702 = next(k for k in PK().calls if k.strike == 702)
    env = {k: v for k, v in os.environ.items() if not k.startswith("OT_")}
    env.update(OT_INSTRUMENT=SYM, TMPDIR=_TD)
    r10 = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "check_park.py")], env=env,
                         capture_output=True, text=True, timeout=280)
    check("P10 PARK unchanged: its signal on P1's tape is the 702 CALL at the ask; tests/check_park.py exits 0",
          pk is not None and pk.strategy_name == "PARK" and pk.option_side == "call" and float(pk.strike) == 702
          and abs(pk.entry_premium - c702.ask) < 1e-9 and float(pk.underlying_stop) == 0 and r10.returncode == 0,
          f"{pk and (pk.option_side, pk.strike, pk.entry_premium)} rc={r10.returncode} {r10.stdout[-300:]}")

    # ── P13 config / switch ─────────────────────────────────────────────────
    def probe(extra):
        e = dict(env); e.update(extra)
        code = ("import config,json;from strategy import plan_state as S;"
                "print(json.dumps([config.PARC_MODE, config.PARC_ENV_REFUSED, S.state('PARC')]))")
        r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=e, capture_output=True, text=True, timeout=60)
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:                                       # noqa: BLE001
            return r.stderr[-200:]
    m = [probe({}), probe({"OT_PARC": "log"}), probe({"OT_PARC": "0"}), probe({"OT_PARC": "yes"})]
    cfg = open(os.path.join(ROOT, "configure.sh")).read()
    check("P13 OT_PARC unset -> log (r50, paused); log -> log; 0 -> off/dormant; 'yes' keeps log, named; configure.sh "
          "item 15 is PARC, Done 16",
          m == [["log", "", "log"], ["log", "", "log"], ["off", "", "dormant"], ["log", "yes", "log"]]
          and re.search(r"^\s*15\)\s*change_parc", cfg, re.M) and re.search(r"^\s*16\)\s*break", cfg, re.M)
          and "Select [1-16]" in cfg, f"{m}")

    import shutil
    shutil.rmtree(_TD, ignore_errors=True)
    if FAILED:
        print(f"\nRED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"\nGREEN — {len(RAN)} checks: PARC is PARK's entry, the safer-side credit spread, the ramp, the structure "
          f"stop, the nickel, EOD.1 and the ladder; PARK unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
