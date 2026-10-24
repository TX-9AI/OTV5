#!/usr/bin/env python3
"""
tests/check_brk_stop5m.py  v1.0
v1.0  2026-10-14  OTV4TEST r284 (BRK.11) — BREAKOUT'S STOP IS THE 5m SWING, NOT THE 1m BREAK BAR.

THE OPERATOR, 2026-10-14 11:47 ET: "Yes, we have to" (to: the 5m structure stop for
Breakout, sized to it, every exit logging what the old 1m stop would have done).
MEASURED (/var/tmp/structure_hold_1014/v2_brk.txt, QQQ-TEST's 98 Breakouts, held to
the stop or 15:55, underlying R): the 1m break bar's extreme is a median 0.36 pt stop;
the 5m swing turns winners 12 -> 33, full stops 86 -> 59, the 1m-losing days
-51.2 R -> -31.8 R. 10-14 10:53: a 0.76 pt stop, 46 contracts, out in 2 min on a
1 pt bounce inside a 5 pt trend.

EVERYTHING DRIVES THE REAL PLAN: BreakoutPlan.prepare on synthetic 1m AND 5m candles
in a scratch feed store; only the order-flow reader is stubbed to pass (it reads live
prints), as check_breakout_new_extreme does.

  S1  a short whose last closed 5m bars reach ABOVE the break bar's high: the stop
      is the 5m swing high, not the break bar's high          (RED before r284)
  S2  the stop is never TIGHTER than the 1m stop: 5m highs under the break bar's
      high leave the break bar's high in place
  S3  a 5m bar still forming at the signal bar's close never counts
  S4  a prior session's 5m bars never count
  S5  OT_BRK_STOP5M=log: the 1m stop trades, the 5m swing is recorded on the tick
  S6  an unreadable feed store keeps the 1m stop and says so (never raises)
  S7  the emitted signal carries the 5m stop as underlying_stop (size and the
      structural premium stop follow it, r91), and the FIRE writes the
      counterfactual row (stop_1m, stop_5m, stop_used)      (RED before r284)
  S8  config: unset -> trade; off/log honoured; junk -> log, refused by name
"""
import glob as _glob
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
SCRATCH = tempfile.mkdtemp(prefix="chk_brk_s5_", dir="/var/tmp")
os.environ["OT_TRADES_DB"] = os.path.join(SCRATCH, "trades.db")
os.environ["OT_DERIVED_DB"] = os.path.join(SCRATCH, "derived.db")
os.environ["OT_RESTING_DB"] = os.path.join(SCRATCH, "resting.db")
os.environ["OT_FEED_DB"] = os.path.join(SCRATCH, "feed.db")
os.environ["OT_COUNTERFACTUAL_DIR"] = os.path.join(SCRATCH, "cf")
os.environ["OT_BRK_RESEARCH_UNTIL"] = "2099-12-31"      # informers: accept any
os.environ.pop("OT_BRK_STOP5M", None)
FAILED, RAN = [], []
ET = "America/New_York"


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def guard(name, fn):
    try:
        ok, det = fn()
    except Exception as exc:                                    # noqa: BLE001
        ok, det = False, f"{type(exc).__name__}: {exc}"
    check(name, bool(ok), det)


# ── the session: range 100.00-101.00 (09:30-09:34). A SHORT breaks at 09:40
#    (minute 10): close 99.80, high 100.10 -> the 1m stop is 100.10.
def _session():
    bars = {m: (100.5, 101.00, 100.00, 100.5) for m in range(0, 5)}
    for m in range(5, 10):
        bars[m] = (100.4, 100.60, 100.20, 100.4)
    bars[10] = (100.05, 100.10, 99.70, 99.80)             # 09:40 the break bar
    bars[11] = (99.80, 99.90, 99.60, 99.70)               # 09:41 forming
    return bars


def _write_feed(day):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    c = sqlite3.connect(os.environ["OT_FEED_DB"])
    c.execute("CREATE TABLE IF NOT EXISTS candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, "
              "ts_epoch_ms INTEGER NOT NULL, open REAL, high REAL, low REAL, close REAL, "
              "volume REAL, PRIMARY KEY (symbol, interval, ts_epoch_ms))")
    o = int(datetime(day.year, day.month, day.day, 9, 30, tzinfo=ZoneInfo(ET)).timestamp() * 1000)
    y = o - 24 * 3600 * 1000
    five = {
        # S1: the 09:30 bucket's high 101.00 is ABOVE the break bar's 100.10
        "T5W": [(0, 101.00, 100.00), (5, 100.60, 100.20), (10, 103.00, 99.60)],   # S3: 09:40 bucket forming
        # S2: every closed 5m high is UNDER the break bar's high
        "T5T": [(0, 100.05, 99.95), (5, 100.02, 99.95)],
        # S4: only a prior session's bar is in the store
        "T5Y": [],
    }
    for sym in ("T5W", "T5T", "T5Y", "T5L"):
        for m, (op, h, l, cl) in _session().items():
            if sym == "T5T" and m < 10:
                h = min(h, 100.05)
            c.execute("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)",
                      (sym, "1m", o + m * 60_000, op, h, l, cl, 1000.0))
        for m, h, l in five.get(sym, five["T5W"]):
            c.execute("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)",
                      (sym, "5m", o + m * 60_000, h - 0.1, h, l, l + 0.1, 5000.0))
    c.execute("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)",
              ("T5Y", "5m", y + 380 * 60_000, 150.0, 150.0, 99.0, 100.0, 5000.0))   # yesterday 15:50
    c.commit()
    c.close()


def _frame(sym, day, minute):
    import pandas as pd
    from datetime import datetime
    from zoneinfo import ZoneInfo
    o = int(datetime(day.year, day.month, day.day, 9, 30, tzinfo=ZoneInfo(ET)).timestamp() * 1000)
    c = sqlite3.connect(f"file:{os.environ['OT_FEED_DB']}?mode=ro", uri=True)
    rows = c.execute("SELECT ts_epoch_ms, open, high, low, close, volume FROM candles WHERE symbol=? "
                     "AND interval='1m' AND ts_epoch_ms >= ? AND ts_epoch_ms <= ? ORDER BY ts_epoch_ms",
                     (sym, o, o + minute * 60_000)).fetchall()
    c.close()
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df.index = pd.to_datetime(df.pop("ts"), unit="ms", utc=True).dt.tz_convert(ET)
    return df


class _ORB:
    orb_high, orb_low = 101.00, 100.00


class _C:
    def __init__(self, k):
        self.strike, self.mark, self.delta, self.gamma, self.expiry, self.ask = k, 1.0, -0.5, 0.05, "", 1.05
        self.bid = 0.95


class _Chain:
    def __init__(self, px):
        ks = [round(px) + i for i in range(-6, 7)]
        self.calls, self.puts = [_C(k) for k in ks], [_C(k) for k in ks]


def _tick(plan, spec, sym, day, minute=11):
    df = _frame(sym, day, minute)
    px = float(df.iloc[-1]["open"])
    return plan.prepare(spec=spec, orb=_ORB(), price_now=px, now_et="09:41",
                        chain=_Chain(px), df_1m=df, flow_conn=None, symbol=sym)


def _why(p):
    t = p.tick
    return (f"ready={p.ready} stop={p.stop} stop_1m={getattr(p, 'stop_1m', '-')} "
            f"stop_5m={getattr(p, 'stop_5m', '-')} note={(t.checks.get('stop_5m') or (None, None, None))[-1]!r} "
            f"why={(t.plan.last()[2] if t.closed else '-')[:80]!r}")


def _cfg(env):
    e = {k: v for k, v in os.environ.items() if k != "OT_BRK_STOP5M"}
    e.update(env)
    r = subprocess.run([sys.executable, "-c", "import config; print(config.BRK_STOP5M_MODE, "
                        "repr(getattr(config, 'BRK_STOP5M_ENV_REFUSED', None)))"],
                       cwd=ROOT, env=e, capture_output=True, text=True, timeout=60)
    return (r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1]


def main():
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        day = datetime.now(ZoneInfo(ET)).date()
        _write_feed(day)
        from database.trade_logger import get_trade_logger
        get_trade_logger()
        import config
        from strategy.breakout import Breakout
        import strategy.breakout as B
        B.LATEST_ET = "15:40"                    # the stop, not the window
        from strategy.breakout_plan import BreakoutPlan
        BreakoutPlan._flow = staticmethod(lambda conn, symbol: (-0.2, 1.0))
        spec = Breakout()
        plan = spec._plan_()
    except Exception as exc:                                    # noqa: BLE001
        for n in ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"):
            check(f"{n} setup", False, f"{type(exc).__name__}: {exc}")
        return _tail()

    p1 = _tick(plan, spec, "T5W", day)
    guard("S1 a short's stop is the last closed 5m bars' high (101.00), not the break bar's high (100.10)",
          lambda: (p1.direction == "short" and p1.stop is not None and abs(p1.stop - 101.00) < 1e-9, _why(p1)))
    guard("S3 the 09:40 5m bucket (high 103.00, still forming at the 09:41 signal close) never counts",
          lambda: (p1.stop is not None and p1.stop < 102.0, _why(p1)))
    p2 = _tick(plan, spec, "T5T", day)
    guard("S2 5m highs UNDER the break bar's high never tighten the stop: it stays 100.10",
          lambda: (p2.direction == "short" and p2.stop is not None and abs(p2.stop - 100.10) < 1e-9, _why(p2)))
    p4 = _tick(plan, spec, "T5Y", day)
    guard("S4 a prior session's 5m bar (high 150.00) never counts: the stop stays 100.10",
          lambda: (p4.direction == "short" and p4.stop is not None and abs(p4.stop - 100.10) < 1e-9, _why(p4)))

    saved = getattr(config, "BRK_STOP5M_MODE", None)
    config.BRK_STOP5M_MODE = "log"
    try:
        p5 = _tick(plan, spec, "T5W", day)
    finally:
        config.BRK_STOP5M_MODE = saved
    guard("S5 OT_BRK_STOP5M=log: the 1m stop (100.10) trades and the 5m swing (101.00) is recorded",
          lambda: (abs((p5.stop or 0) - 100.10) < 1e-9 and abs((getattr(p5, "stop_5m", None) or 0) - 101.00) < 1e-9
                   and "stop_5m" in p5.tick.checks, _why(p5)))

    feed = os.environ["OT_FEED_DB"]
    os.environ["OT_FEED_DB"] = os.path.join(SCRATCH, "absent", "feed.db")
    try:
        try:
            from strategy.breakout_plan import swing_5m_stop
            sw = swing_5m_stop("T5W", day, 0, "short")
        except Exception as exc:                                # noqa: BLE001
            sw = exc
    finally:
        os.environ["OT_FEED_DB"] = feed
    guard("S6 an unreadable feed store returns a reason (the 1m stop stands), never raises",
          lambda: (isinstance(sw, str) and "unreadable" in sw, repr(sw)))

    def s7():
        p = _tick(plan, spec, "T5W", day)
        if not p.ready:
            return False, "not ready: " + _why(p)
        sig = p.emit("Breakout")
        cf = os.path.join(os.environ["OT_COUNTERFACTUAL_DIR"], "breakout_stop.jsonl")
        rows = [json.loads(x) for x in open(cf)] if os.path.exists(cf) else []
        last = rows[-1] if rows else {}
        ok = (abs(float(sig.underlying_stop) - 101.00) < 1e-9 and last.get("stop_1m") == 100.10
              and last.get("stop_5m") == 101.00 and last.get("stop_used") == 101.00)
        return ok, f"underlying_stop={sig.underlying_stop} row={last}"
    guard("S7 the signal carries the 5m stop and the FIRE writes stop_1m / stop_5m / stop_used", s7)

    got = [_cfg({}), _cfg({"OT_BRK_STOP5M": "OFF"}), _cfg({"OT_BRK_STOP5M": "log"}), _cfg({"OT_BRK_STOP5M": "yes"})]
    guard("S8 config: unset -> trade, OFF -> off, log -> log, junk -> log refused by name",
          lambda: (got == ["trade ''", "off ''", "log ''", "log 'yes'"], repr(got)))
    return _tail()


def _tail():
    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks: Breakout's stop is the 5m swing")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        shutil.rmtree(SCRATCH, ignore_errors=True)
    sys.exit(rc)
