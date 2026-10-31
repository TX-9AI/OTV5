#!/usr/bin/env python3
"""
tests/check_park_entry_mark.py  v5.0
v5.0  2026-10-30  OTV5 r60 (PARK.4) — new. PARK IS BOUGHT AT THE MARK, NEVER WORSE. The operator, 2026-10-30, on CVX's
      PARK (235C bought at the ask 1.56 on a 0.97/1.56 quote; -$657 booked, -$480 at the mark 1.265): "That's not my
      spec… you know park is a borrowed trade. To match my spec, we ladder in from aggressive to mark & never worse
      than mark". The fixture is CVX 2026-10-30 at 11:01 ET: 09:30 open 234.07, 10:30 close 235.57 (+0.641%), 11:00
      close 235.33, prior close 231.45 (gap +2.62); the 235C quoted 0.97 / 1.56 (mark 1.265).
  M1  the plan picks the 235C and its signal's entry_premium is the mark 1.265 floored to the cent, 1.26 (was the ask
      1.56). Floored, as entry_engine._mark_cap prices a buy (r224 FLY.1): the raw float 1.2650000000000001 booked
      1.27 through limit_at_mark's round(px, 2), a half-cent ABOVE the mark
  M2  the FIRE line names the mark and the quote: "@ 1.26 (mark, bid/ask 0.97/1.56)"
  M3  the size is floor($1,050 / (mark x 100)) = 8 (RiskManager.size_for long_debit; it was 6 on the ask)
  M4  PAPER: EntryEngine._paper_fill_single books the mark, 1.26 - never above 1.265
  M5  LIVE: EntryEngine._place_single_leg (the broker stubbed, no order can leave) walks the r104 ladder on the PARK
      signal: rung 1 is 25% in from the bid (>= 0.97, < 1.265), each refused rung steps toward the mark, NO rung is
      ever above the mark 1.265, and the walk ends at the mark snapped in our favour (1.26) - never the ask
  M6  LIVE, no usable quote at post time: the fallback price is limit_at_mark(signal.entry_premium) - the mark
      1.26, never above 1.265 (it was the ask 1.56)
  M7  the window ends the walk: at 11:03 PARK is dormant (no signal), so an unfilled ladder is no trade - nothing
      is ever posted worse than the mark to "get it done"
  M8  the feasibility bar is unchanged: a 0.40 / 0.45 quote (ask < PARK_MIN_ASK 0.50) is still refused
THE WALL CLOCK IS PINNED to 2026-10-30 11:01 ET (utils.time_utils.datetime, as tests/check_decay_stop.py pins it): the
lander runs CHECKs after the close. The broker is never reached: get_session / get_account / place_order /
confirm_order_fill / order_guard / buying_power are stubbed in entry_engine's namespace.
Born red on 6543fdc at M1, M2, M3, M4 and M6; a raw-mark build (no floor) was red at M4 and M6 (1.27). M5, M7 and M8
pass on 6543fdc: the live ladder already prices off the quote.
Run:  python3 tests/check_park_entry_mark.py
"""
import logging
import os
import sqlite3
import sys
import tempfile
from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_park_entry_mark.")
for _k, _v in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db"),
               ("OT_FEED_DB", "f.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(_TD, _v)
os.environ.pop("OT_PARK", None)
SYM = "CVX"
os.environ["OT_INSTRUMENT"] = SYM
ET = ZoneInfo("America/New_York")
DAY, PREV = date(2026, 10, 30), date(2026, 10, 29)
FEED = os.environ["OT_FEED_DB"]
BID, ASK = 0.97, 1.56
MARK = (BID + ASK) / 2.0          # 1.265
FAILED = []

try:
    import utils.time_utils as _tu                              # noqa: E402
    _REAL_DT = _tu.datetime

    class _Pinned(_REAL_DT):
        @classmethod
        def now(cls, tz=None):
            t = _REAL_DT(2026, 10, 30, 11, 1, 3, tzinfo=_tu.ET)
            return t.astimezone(tz) if tz is not None else t.replace(tzinfo=None)
    _tu.datetime = _Pinned
    import pandas  # noqa: F401,E402
    import config                                               # noqa: E402
    from strategy.park import Park                              # noqa: E402
    from execution import entry_engine as EE                    # noqa: E402
    from execution import ladder_registry as LR                 # noqa: E402
    from risk.risk_manager import RiskManager                   # noqa: E402
except Exception as exc:                                        # noqa: BLE001
    print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
    sys.exit(2)


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def _ms(d, h, m):
    return int(datetime(d.year, d.month, d.day, h, m, tzinfo=ET).timestamp() * 1000)


def _feed():
    c = sqlite3.connect(FEED)
    c.execute("CREATE TABLE IF NOT EXISTS candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, "
              "ts_epoch_ms INTEGER NOT NULL, open REAL, high REAL, low REAL, close REAL, volume REAL, "
              "PRIMARY KEY (symbol, interval, ts_epoch_ms))")
    rows = [(SYM, "1m", _ms(DAY, 9, 30), 234.07, 234.2, 233.9, 234.1, 1),
            (SYM, "1m", _ms(DAY, 10, 30), 235.5, 235.6, 235.4, 235.57, 1),
            (SYM, "1m", _ms(DAY, 11, 0), 235.3, 235.4, 235.2, 235.33, 1),
            (SYM, "1m", _ms(PREV, 15, 59), 231.5, 231.5, 231.4, 231.45, 1)]
    c.executemany("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)", rows)
    c.commit()
    c.close()


class K:
    def __init__(self, strike, bid, ask, delta, side):
        self.strike, self.bid, self.ask, self.delta = float(strike), bid, ask, delta
        self.mark, self.expiry, self.option_type = (bid + ask) / 2, str(DAY), side
        self.symbol = f"{SYM:<6}{DAY:%y%m%d}{side}{int(strike * 1000):08d}"
        self.streamer_symbol = f".{SYM}{DAY:%y%m%d}{side}{strike:g}"


class Chain:
    def __init__(self, bid=BID, ask=ASK):
        self.calls = [K(232.5, 2.60, 3.10, 0.75, "C"), K(235, bid, ask, 0.56, "C"), K(237.5, 0.30, 0.45, 0.30, "C")]
        self.puts = [K(232.5, 0.20, 0.30, -0.2, "P"), K(235, 0.90, 1.30, -0.44, "P"), K(237.5, 2.2, 2.7, -0.7, "P")]
        self.expiry = str(DAY)


def main():
    print("check_park_entry_mark")
    _feed()
    config.PARK_MODE = "trade"
    P = Park()
    lines = []

    class _Grab(logging.Handler):
        def emit(self, r):
            lines.append(r.getMessage())
    logging.getLogger("strategy.park_plan").addHandler(_Grab())
    logging.getLogger("strategy.park_plan").setLevel(logging.INFO)

    sig = P.generate_signal(price_now=235.33, now_et="11:01", chain=Chain(), prior_close=None, day=DAY, symbol=SYM)
    ep = float(getattr(sig, "entry_premium", 0) or 0) if sig is not None else None
    check("M1 the CVX 10-30 235C signal's entry_premium is the mark 1.265 floored to the cent, 1.26 (bid 0.97 / ask "
          "1.56), not the ask",
          sig is not None and float(sig.strike) == 235 and sig.option_side == "call" and abs(ep - 1.26) < 1e-9,
          f"{sig and (sig.strike, sig.option_side)} entry_premium={ep}")
    fire = [x for x in lines if "[park] FIRE" in x]
    check("M2 the FIRE line names the mark and the quote: '@ 1.26 (mark, bid/ask 0.97/1.56)'",
          bool(fire) and "@ 1.26 (mark, bid/ask 0.97/1.56)" in fire[-1], f"{fire[-1:]}")
    if sig is None:
        print("\nRED — no signal; the rest cannot run")
        return 1

    z = RiskManager(risk_per_trade=1050.0, paper_trading=True).size_for("long_debit", premium=ep, grade="UNGRADED")
    n = int(getattr(z, "contracts", 0) or 0)
    check("M3 sized on the mark: floor($1,050 / 126.00) = 8 (6 on the ask)", n == 8, f"contracts={n}")

    eng = EE.EntryEngine(paper_trading=True)
    px, _oid, q = eng._paper_fill_single(sig, 8)
    check("M4 PAPER books the mark: 1.26, never above 1.265",
          abs(px - 1.26) < 1e-9 and px <= MARK + 1e-9 and q == 8, f"fill={px} qty={q}")

    # ── LIVE, the broker stubbed in entry_engine's namespace: nothing can leave this process ──
    posted = []

    class _Acct:
        def place_order(self, session, order, dry_run=False):
            posted.append(-float(order.price))
            return SimpleNamespace(errors=[], order=SimpleNamespace(id="T"))
    EE.get_session = lambda: object()
    EE.get_account = lambda: _Acct()
    EE.sdk_result = lambda r: r
    EE.Leg = lambda **kw: SimpleNamespace(**kw)
    EE.NewOrder = lambda **kw: SimpleNamespace(**kw)
    EE.confirm_order_fill = lambda *a, **k: SimpleNamespace(filled=False, net_price=None, working_order_id=None,
                                                            detail="stub: refused", order_id="", quantity=0)
    EE._guard.clear_to_post = lambda *a, **k: (True, "")
    EE._guard.after_failure = lambda *a, **k: None
    EE._bp.affordable = lambda *a, **k: (True, "")
    EE.EntryEngine._page_if_working = staticmethod(lambda *a, **k: None)
    LR.clear(LR.intent_key(sig.contract.symbol, "open", "single"))
    live = EE.EntryEngine(paper_trading=False)
    res = [live._place_single_leg(sig, 8) for _ in range(40)]
    above = [p for p in posted if p > MARK + 1e-9]
    check("M5 LIVE walks the ladder on the PARK signal: rung 1 in from the bid, steps up, NO rung above the mark "
          "1.265, ends at 1.26",
          len(posted) == 40 and not above and BID <= posted[0] < MARK and posted == sorted(posted)
          and abs(posted[-1] - 1.26) < 1e-9 and all(r[2] == 0 for r in res),
          f"rungs {posted[:3]}..{posted[-2:]} above-mark {above} first-8 ticks {posted[:8]}")

    posted.clear()
    bad = SimpleNamespace(**{**vars(sig.contract), "bid": 0.0, "ask": 0.0, "symbol": sig.contract.symbol + "X"})
    _c, sig.contract = sig.contract, bad
    try:
        live._place_single_leg(sig, 8)
    finally:
        sig.contract = _c
    check("M6 LIVE with no usable quote posts the fallback at the mark 1.26, never above 1.265 (was the ask 1.56)",
          len(posted) == 1 and posted[0] <= MARK + 1e-9, f"posted {posted}")

    s7 = P.generate_signal(price_now=235.33, now_et="11:03", chain=Chain(), prior_close=None, day=DAY, symbol=SYM)
    check("M7 the window ends the walk: at 11:03 PARK is dormant (no signal) - an unfilled ladder is no trade",
          s7 is None, f"{s7}")

    p8 = P.prepare(price_now=235.33, now_et="11:01", chain=Chain(bid=0.40, ask=0.45), prior_close=None, day=DAY,
                   symbol=SYM)
    check("M8 feasibility unchanged: ask 0.45 < PARK_MIN_ASK 0.50 is still refused at contract",
          not p8.ready and "contract" in p8.unmet, f"ready={p8.ready} unmet={p8.unmet}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("\nGREEN — 8 of 8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
