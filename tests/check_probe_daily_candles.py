#!/usr/bin/env python3
"""
tests/check_probe_daily_candles.py  v1.1
v1.1  2026-10-21  OTV4TEST r312 (PRB.5) — D7: A ZERO BAR IS DROPPED. r311's first real run (19:28 ET) wrote an all-zero
      row on the start date into BOTH files (QQQ, SPX); SPX's study then divided by it. The fixture never sent one.
v1.0  2026-10-21  OTV4TEST r311 (PRB.4) — THE DAILY-CANDLE PROBE ONLY READS, AND WRITES ONE CSV OF ITS OWN.

  The operator, 2026-10-21 19:10 ET: "the daily candle is a yes" (a read-only probe for longer 1D history - the box
  holds QQQ 1d only from 08-10 and the warehouse 1m from 07-08, too short to test his gap / prior-day-extreme thesis).
  tools/probe_daily_candles.py runs with the bot's broker credentials, so what it CANNOT do is the point:
  D1  it imports nothing from tastytrade.order / tastytrade.account, makes no order, account or balance call, and
      imports no sqlite3 (it never opens a bot store)
  D2  it is on run_with_bot_env's PROBES list (so it runs only committed and unedited)
  D3  DRIVEN, offline: main() over a fake streamer asks ONE '1d' subscription per symbol, RTH only, starting about
      YEARS back
  D4  DRIVEN: the CSV holds one row per day, the LAST update of a re-sent bar, dated by the bar's UTC date (a dxFeed
      daily bar is stamped 00:00 UTC of its session), sorted, with NaN / None / other-interval events dropped; exit 0
  D5  DRIVEN: nothing served -> exit 1 and NO file written (a partial history must not look like a short one)
  D6  DRIVEN: the file lands under OUT_DIR and nowhere else (the temp file is renamed, not left behind)
  D7  DRIVEN: a bar with any price <= 0 (the feed's all-zero start bar; a zero low) is dropped - a zero VOLUME is not
      (SPX, an index, reports volume 0 on every bar)
No network. Run: python3 tests/check_probe_daily_candles.py
"""
import ast
import asyncio
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED = []
_P = os.path.join(_root, "tools", "probe_daily_candles.py")


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _load():
    s = importlib.util.spec_from_file_location("_pdc", _P)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _ms(y, mo, d):
    return int(datetime(y, mo, d, tzinfo=timezone.utc).timestamp() * 1000)


class _FakeStreamer:
    """Answers subscribe_candle and get_event(Candle) from a canned list; records what was asked."""
    asked = []

    def __init__(self, session):
        self.events = list(_FakeStreamer.feed)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def subscribe_candle(self, symbols, interval, start_time=None, extended_trading_hours=False, **kw):
        _FakeStreamer.asked.append((list(symbols), interval, start_time, extended_trading_hours))

    async def get_event(self, cls):
        if self.events:
            return self.events.pop(0)
        await asyncio.sleep(10)          # idle: the probe's own idle timer must end the wait


def _drive(m, feed, argv, out_dir):
    _FakeStreamer.feed, _FakeStreamer.asked = feed, []
    saved = (m.DXLinkStreamer, m.get_session, m.OUT_DIR, m.IDLE_S, sys.argv)
    m.DXLinkStreamer, m.get_session, m.OUT_DIR, m.IDLE_S = _FakeStreamer, (lambda: object()), out_dir, 0.3
    sys.argv = ["probe_daily_candles.py"] + argv
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = asyncio.run(m.main())
    finally:
        m.DXLinkStreamer, m.get_session, m.OUT_DIR, m.IDLE_S, sys.argv = saved
    return rc, buf.getvalue(), list(_FakeStreamer.asked)


def _c(sym, t, o, h, l, c, v=1000.0, iv="d"):
    return SimpleNamespace(event_symbol=f"{sym}{{={iv}}}", time=t, open=o, high=h, low=l, close=c, volume=v)


def main():
    try:
        src = open(_P, encoding="utf-8").read()
    except OSError as exc:
        check("D0 tools/probe_daily_candles.py exists", False, str(exc))
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    tree = ast.parse(src)

    # D1 - no order / account module, no order / account / balance call, no sqlite3
    mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    mods += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    bad_mods = [x for x in mods if x.startswith(("tastytrade.order", "tastytrade.account", "sqlite3"))]
    forbid = {"place_order", "replace_order", "delete_order", "cancel_order", "place_complex_order",
              "get_balances", "get_positions", "get_live_orders", "get_order_history", "Account"}
    bad_calls = sorted({(n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", ""))
                        for n in ast.walk(tree) if isinstance(n, ast.Call)} & forbid)
    bad_names = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} & forbid)
    check("D1 no tastytrade.order / tastytrade.account / sqlite3 import and no order, account or balance call",
          not bad_mods and not bad_calls and not bad_names, f"modules={bad_mods} calls={bad_calls} names={bad_names}")

    # D2 - the wrapper's list
    rw = open(os.path.join(_root, "tools", "run_with_bot_env.py"), encoding="utf-8").read()
    check("D2 it is on run_with_bot_env's PROBES list",
          '"probe_daily_candles.py": "tools/probe_daily_candles.py"' in rw, "not listed")

    m = _load()
    nan = float("nan")
    feed = [
        _c("QQQ", _ms(2024, 1, 3), 400.0, 405.0, 398.0, 401.0),
        _c("QQQ", _ms(2024, 1, 2), 390.0, 396.0, 389.0, 395.0),
        _c("QQQ", _ms(2024, 1, 3), 400.0, 406.0, 397.5, 403.5, 2000.0),     # re-sent: the LAST one wins
        _c("QQQ", _ms(2024, 1, 4), nan, nan, nan, nan),                     # NaN bar: dropped
        _c("QQQ", _ms(2024, 1, 5), None, 1.0, 1.0, 1.0),                    # no open: dropped
        _c("QQQ", _ms(2024, 1, 2), 1.0, 1.0, 1.0, 1.0, iv="h"),              # another interval: dropped
    ]
    zfeed = [
        _c("SPX", _ms(2021, 10, 21), 0.0, 0.0, 0.0, 0.0, 0.0),             # the feed's start placeholder
        _c("SPX", _ms(2021, 10, 22), 4546.12, 4559.67, 4524.0, 4544.9, 0.0),  # real, volume 0 (an index)
        _c("SPX", _ms(2021, 10, 25), 4553.69, 4572.62, 0.0, 4566.48, 0.0),   # a zero low: dropped
    ]
    with tempfile.TemporaryDirectory() as td:
        rc, out, asked = _drive(m, feed, ["3", "QQQ"], td)
        # D3 - the subscription
        ok3 = (len(asked) == 1 and asked[0][0] == ["QQQ"] and asked[0][1] == "1d" and asked[0][3] is False
               and asked[0][2] is not None
               and abs((datetime.now(timezone.utc) - asked[0][2]) - timedelta(days=round(3 * 365.25))) < timedelta(days=2))
        check("D3 DRIVEN: one '1d' RTH subscription per symbol, starting about YEARS back", ok3, f"asked={asked}")
        # D4 - the rows
        path = os.path.join(td, "QQQ_1d_rth.csv")
        rows = open(path).read().splitlines() if os.path.exists(path) else []
        want = ["date,open,high,low,close,volume",
                "2024-01-02,390.0,396.0,389.0,395.0,1000.0",
                "2024-01-03,400.0,406.0,397.5,403.5,2000.0"]
        check("D4 DRIVEN: one row per day, last update wins, UTC date, sorted, junk dropped, exit 0",
              rc == 0 and rows == want, f"rc={rc} rows={rows} out={out[-300:]!r}")
        # D6 - only the file, nothing else
        left = sorted(os.listdir(td))
        check("D6 DRIVEN: exactly the one CSV under OUT_DIR, no temp file left", left == ["QQQ_1d_rth.csv"],
              f"left={left}")
    with tempfile.TemporaryDirectory() as td:
        rc, out, _ = _drive(m, [], ["2", "QQQ"], td)
        check("D5 DRIVEN: nothing served -> exit 1 and no file written", rc == 1 and os.listdir(td) == [],
              f"rc={rc} files={os.listdir(td)} out={out[-200:]!r}")

    with tempfile.TemporaryDirectory() as td:
        rc, out, _ = _drive(m, zfeed, ["1", "SPX"], td)
        path = os.path.join(td, "SPX_1d_rth.csv")
        rows = open(path).read().splitlines() if os.path.exists(path) else []
        check("D7 DRIVEN: a bar with any price <= 0 is dropped, a zero volume is kept",
              rc == 0 and rows == ["date,open,high,low,close,volume", "2021-10-22,4546.12,4559.67,4524.0,4544.9,0.0"],
              f"rc={rc} rows={rows}")

    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — the daily-candle probe only reads, and writes one CSV of its own")
    return 0


if __name__ == "__main__":
    sys.exit(main())
