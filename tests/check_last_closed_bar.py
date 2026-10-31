#!/usr/bin/env python3
"""
tests/check_last_closed_bar.py  v5.1
v5.1  2026-10-31  OTV5 r68 (CFG.5) — OT_RESTING_STOP_STATE leaves the scratch env: the resting stop and its state file are deleted
      (the operator, 2026-10-31: "Resting stop was a study. It failed. Get this the fuck out of here"). No check changed.
v5.0  2026-10-27  OTV5 r44 (BAR.1) — THE LAST CLOSED BAR IS FOUND BY TIME, NOT BY POSITION.
      META 2026-10-27, trade 3f2b1372: a Breakout short fired at 10:10:00 ET. Its plan line logged "1m stop 623.57",
      the 10:08 bar's high (623.5659): the frame's newest row was 10:09 (no 10:10 row existed yet), so iloc[-2] - "the
      last CLOSED bar" everywhere - was 10:08 (close 623.01, below the 623.20 opening-range low). 10:09 had already
      closed back inside at 623.21, so the bot fired on a break the market had undone. utils.time_utils.closed_pos /
      closed_part judge a row closed when start + bar length <= now. The META bars below are the feed store's.
      Driven through the REAL BreakoutPlan.prepare (scratch feed store and trades.db; only the order-flow reader is
      stubbed, as check_breakout_rearm does) and the REAL exit_engine.BOSTracker.

  C1  the helper: META's frame to 10:09 at 10:10:00.2 -> 10:09; with a 10:10 forming row -> 10:09; at 10:09:59.9
      -> 10:08 (10:09 still forming); a 5m frame (bar_s 300) at the 10:10 boundary -> 10:05; a frame not live
      (newest row 3+ bars old), an empty, a one-row and an untimed frame keep today's -2; closed_part agrees
  C2  BreakoutPlan.prepare on META at 10:10:00 with the 10:10 row ABSENT does not fire a short off 10:08: it reads
      10:09 (break_close 623.21, inside) - the old code reads 10:08 (623.01) and fires
  C3  the same tick with the 10:10 forming row PRESENT reads 10:09 and does not fire (old and new alike), and the
      next minute's normal tick (10:11 forming) reads 10:10 (622.655) and fires the fresh short (old and new alike)
  C4  exit side: BOSTracker.update (sweep BOS) at 10:10:00.2 with no 10:10 row reads 10:09, not 10:08; with the
      forming row present it reads 10:09 as before

Born red on 7c44791 at C1, C2 and C4a.
Run:  python3 tests/check_last_closed_bar.py
"""
import datetime as D
import os
import shutil
import sqlite3
import sys
import tempfile
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_s = tempfile.mkdtemp(prefix="check_last_closed_bar.")
for _k, _v in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived.db"), ("OT_RESTING_DB", "resting.db"),
               ("OT_FEED_DB", "feed.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(_s, _v)                  # scratch stores, always (the plan reads the feed store)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ["OT_BRK_RESEARCH_UNTIL"] = "2099-12-31"          # informers accept any (as check_breakout_rearm)
ET = ZoneInfo("America/New_York")
FAILED = []
DAY = D.date(2026, 10, 27)
ORB_HI, ORB_LO = 628.01, 623.20


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def at(h, m, s=0.0):
    return D.datetime(2026, 10, 27, h, m, int(s), int(round((s % 1) * 1e6)), tzinfo=ET)


# META 1m, 2026-10-27 (feed store): minute after 09:30 -> (open, high, low, close)
M1 = {0: (627.39, 628.01, 625.0, 626.03), 1: (625.9, 626.84, 624.5, 625.25), 2: (625.2, 625.46, 623.2, 624.73),
      3: (624.73, 625.64, 623.63, 624.02), 4: (624.1508, 626.0, 623.31, 625.59), 5: (625.615, 626.0, 624.5, 625.275),
      6: (625.18, 625.99, 624.67, 624.9), 7: (624.8254, 625.7585, 624.4, 624.775), 8: (624.65, 624.8495, 623.44, 623.475),
      9: (623.44, 625.2, 623.28, 625.045), 10: (624.92, 625.0376, 624.239, 624.53), 11: (624.64, 625.1, 624.17, 624.275),
      12: (624.275, 625.2368, 623.82, 625.2368), 13: (625.18, 625.88, 624.17, 625.0), 14: (624.925, 625.419, 623.9105, 624.93),
      15: (624.92, 625.4, 624.415, 624.6), 16: (624.625, 625.35, 624.0, 624.305), 17: (624.2101, 624.82, 623.9, 624.32),
      18: (624.34, 624.87, 623.76, 624.645), 19: (624.71, 624.83, 624.0, 624.215), 20: (624.17, 624.17, 623.0, 623.06),
      21: (623.0899, 623.23, 622.25, 623.0), 22: (623.01, 623.0299, 621.47, 622.17), 23: (622.1823, 622.7699, 622.0, 622.685),
      24: (622.61, 623.0, 622.49, 622.57), 25: (622.565, 623.09, 622.5, 622.91), 26: (622.86, 624.8, 622.86, 624.4706),
      27: (624.4796, 625.0, 623.08, 624.0), 28: (624.0, 624.5, 623.49, 624.135), 29: (624.02, 624.7, 623.89, 624.23),
      30: (624.23, 624.362, 623.8, 624.01), 31: (623.9201, 624.46, 623.12, 623.12), 32: (623.13, 624.0, 623.05, 623.8801),
      33: (623.88, 623.94, 623.09, 623.09), 34: (623.1254, 623.28, 622.76, 623.195), 35: (623.215, 623.66, 622.868, 623.5413),
      36: (623.53, 623.59, 622.5, 622.87), 37: (622.86, 623.49, 622.77, 623.49), 38: (623.49, 623.5659, 622.5, 623.01),
      39: (623.01, 623.56, 623.01, 623.21), 40: (623.2699, 623.84, 622.5, 622.655), 41: (622.51, 622.81, 622.0, 622.415)}
# META 5m, 2026-10-27 09:30..10:05 (closed bars)
M5 = {0: (627.39, 628.01, 623.2, 625.59), 5: (625.615, 626.0, 623.28, 625.045), 10: (624.92, 625.88, 623.82, 624.93),
      15: (624.92, 625.4, 623.76, 624.215), 20: (624.17, 624.17, 621.47, 622.57), 25: (622.565, 625.0, 622.5, 624.23),
      30: (624.23, 624.46, 622.76, 623.195), 35: (623.215, 623.66, 622.5, 623.21)}
O_MS = int(at(9, 30).timestamp() * 1000)


def _write_feed(upto_min):
    """The scratch feed store as of the tick: 1m rows through `upto_min` (the rows that existed), 5m closed."""
    p = os.environ["OT_FEED_DB"]
    if os.path.exists(p):
        os.remove(p)
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, ts_epoch_ms INTEGER NOT NULL, "
              "open REAL, high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY (symbol, interval, ts_epoch_ms))")
    for m, (o, h, l, cl) in M1.items():
        if m <= upto_min:
            c.execute("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", ("META", "1m", O_MS + m * 60_000, o, h, l, cl, 5e4))
    for m, (o, h, l, cl) in M5.items():
        if m + 5 <= upto_min + 1:
            c.execute("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", ("META", "5m", O_MS + m * 60_000, o, h, l, cl, 3e5))
    c.commit()
    c.close()


def frame(upto_min, forming=None, src=M1, step=1):
    """A tz-aware ET frame of `src` bars through minute `upto_min`; `forming` appends that minute's first tick."""
    import pandas as pd
    mins = [m for m in sorted(src) if m <= upto_min]
    rows = [src[m] for m in mins]
    if forming is not None:
        o = src[forming][0] if forming in src else M1[forming][0]
        mins.append(forming)
        rows.append((o, o, o, o))
    idx = pd.DatetimeIndex([pd.Timestamp(at(9, 30)) + pd.Timedelta(minutes=m) for m in mins])
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    df["volume"] = 5e4
    return df


class _ORB:
    orb_high, orb_low = ORB_HI, ORB_LO


class _C:
    def __init__(self, k):
        self.strike, self.mark, self.delta, self.gamma, self.expiry = k, 4.42, -0.4, 0.05, "2026-10-28"
        self.ask, self.bid = 4.50, 4.35


class _Chain:
    def __init__(self, px):
        ks = [float(round(px) + i) + f for i in range(-8, 9) for f in (0.0, 0.5)]
        self.calls, self.puts = [_C(k) for k in ks], [_C(k) for k in ks]


def _tick(clock, df, px, hhmm):
    """BreakoutPlan.prepare as main.py calls it (now_et is "HH:MM"; the clock is utils.time_utils.now_et)."""
    import utils.time_utils as TU
    from strategy.breakout import Breakout
    from strategy.breakout_plan import BreakoutPlan
    BreakoutPlan._flow = staticmethod(lambda conn, symbol: (-0.3, 1.0))   # short-side commitment
    spec = Breakout()
    plan = BreakoutPlan()
    _real = TU.now_et
    TU.now_et = lambda: clock
    try:
        return plan.prepare(spec=spec, orb=_ORB(), price_now=px, now_et=hhmm, chain=_Chain(px),
                            df_1m=df, flow_conn=None, symbol="META")
    finally:
        TU.now_et = _real


def _desc(p):
    t = p.tick
    why = (t.plan.last()[2] if getattr(t, "closed", False) else "-")
    return (f"ready={p.ready} dir={p.direction or '-'} break_close={p.break_close} stop_1m={p.stop_1m} "
            f"why={str(why)[:90]!r}")


def c1():
    try:
        from utils.time_utils import closed_pos, closed_part
    except Exception as exc:                                    # noqa: BLE001
        check("C1 utils.time_utils.closed_pos / closed_part exist", False, f"{type(exc).__name__}: {exc}")
        return
    import pandas as pd
    f9 = frame(39)
    f9f = frame(39, forming=40)
    def ts(df, p):
        return df.index[p].strftime("%H:%M")
    got = {
        "to 10:09 @10:10:00.2": ts(f9, closed_pos(f9, at(10, 10, 0.2))),
        "10:10 forming @10:10:00.2": ts(f9f, closed_pos(f9f, at(10, 10, 0.2))),
        "to 10:09 @10:09:59.9": ts(f9, closed_pos(f9, at(10, 9, 59.9))),
        "epoch now": ts(f9, closed_pos(f9, at(10, 10, 0.2).timestamp())),
    }
    want = {"to 10:09 @10:10:00.2": "10:09", "10:10 forming @10:10:00.2": "10:09",
            "to 10:09 @10:09:59.9": "10:08", "epoch now": "10:09"}
    check("C1a META's frame: no 10:10 row -> 10:09; 10:10 forming -> 10:09; at 10:09:59.9 -> 10:08",
          got == want, str(got))
    f5 = frame(35, src=M5)
    g5 = (ts(f5, closed_pos(f5, at(10, 10, 0.2), 300.0)), ts(f5, closed_pos(f5, at(10, 9, 59.0), 300.0)))
    check("C1b a 5m frame (bar_s 300) at the 10:10 boundary -> 10:05; a second before -> 10:00",
          g5 == ("10:05", "10:00"), str(g5))
    one = frame(0)
    untimed = pd.DataFrame({"close": [1.0, 2.0, 3.0]})
    legacy = (closed_pos(f9, at(10, 12, 0.0)), closed_pos(f9.iloc[:0]), closed_pos(None),
              closed_pos(one, at(9, 30, 10.0)), closed_pos(untimed, at(10, 10, 0.2)), closed_pos(f9, "10:10"))
    check("C1c not live (3 bars old), empty, None, one forming row, untimed -> -2 (today's reading)",
          legacy[:5] == (-2, -2, -2, -2, -2), f"{legacy[:5]}")
    import utils.time_utils as TU
    _real = TU.now_et
    try:
        TU.now_et = lambda: at(10, 10, 0.2)
        dflt = (closed_pos(f9), closed_pos(f9, "10:10"), closed_pos(f9, None))
    finally:
        TU.now_et = _real
    check("C1d with no usable `now` (None, \"HH:MM\") it reads the clock utils.time_utils.now_et",
          dflt == (-1, -1, -1), str(dflt))
    cp = (len(closed_part(f9, at(10, 10, 0.2))), len(closed_part(f9f, at(10, 10, 0.2))), len(f9))
    check("C1e closed_part keeps a closed newest row and drops a forming one",
          cp == (len(f9), len(f9f) - 1, len(f9)), str(cp))


def c2_c3():
    from database.trade_logger import get_trade_logger
    get_trade_logger()                                          # the scratch trades.db (no Breakout yet today)
    _write_feed(39)
    p2 = _tick(at(10, 10, 0.2), frame(39), 623.27, "10:10")
    check("C2 10:10:00, no 10:10 row: does NOT fire a short off 10:08 - reads 10:09 (623.21, inside 623.20)",
          (not p2.ready) and p2.direction == "" and p2.break_close is not None
          and abs(p2.break_close - 623.21) < 1e-9, _desc(p2))
    _write_feed(40)
    p3 = _tick(at(10, 10, 0.2), frame(39, forming=40), 623.27, "10:10")
    check("C3a 10:10:00 with the 10:10 forming row: reads 10:09 and does not fire (unchanged)",
          (not p3.ready) and p3.direction == "" and p3.break_close is not None
          and abs(p3.break_close - 623.21) < 1e-9, _desc(p3))
    _write_feed(41)
    p4 = _tick(at(10, 11, 0.5), frame(40, forming=41), 622.51, "10:11")
    check("C3b 10:11:00 with the 10:11 forming row: reads 10:10 (622.655) and fires the fresh short (unchanged)",
          p4.ready and p4.direction == "short" and p4.break_close is not None
          and abs(p4.break_close - 622.655) < 1e-9 and abs((p4.stop_1m or 0) - 623.84) < 1e-9, _desc(p4))


def c4():
    import execution.exit_engine as EE
    _real = EE.now_et
    try:
        EE.now_et = lambda: at(10, 10, 0.2)
        a = EE.BOSTracker("short", 623.30)
        a.update(frame(39))
        b = EE.BOSTracker("short", 623.30)
        b.update(frame(39, forming=40))
    finally:
        EE.now_et = _real
    check("C4a BOSTracker at 10:10:00.2, no 10:10 row: reads 10:09 (LL close 623.21, LH 623.56), not 10:08",
          abs(a.peak_close - 623.21) < 1e-9 and abs((a.protected_level or 0) - 623.56) < 1e-9,
          f"peak_close={a.peak_close} protected={a.protected_level}")
    check("C4b ...and with the 10:10 forming row it reads 10:09 as before",
          abs(b.peak_close - 623.21) < 1e-9 and abs((b.protected_level or 0) - 623.56) < 1e-9,
          f"peak_close={b.peak_close} protected={b.protected_level}")


def main():
    for fn in (c1, c2_c3, c4):
        try:
            fn()
        except Exception as exc:                                # noqa: BLE001
            check(f"{fn.__name__.upper().split('_')[0]} raised", False, f"{type(exc).__name__}: {exc}")
    shutil.rmtree(_s, ignore_errors=True)
    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
