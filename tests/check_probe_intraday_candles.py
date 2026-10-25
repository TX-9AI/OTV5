#!/usr/bin/env python3
"""
tests/check_probe_intraday_candles.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-24  PRB.6 — THE INTRADAY-CANDLE PROBE ONLY READS, AND WRITES ONE CSV OF ITS OWN. Born red on 2cc9502
      (OTV4TEST r316; the module is absent - P0).

  The operator, 2026-10-24 16:04 ET: "14, yes worthwhile" - years of 5m bars, so trend-vs-chop studies read ~1,000
  sessions. tools/probe_intraday_candles.py runs with the bot's broker credentials, so what it CANNOT do is the
  point. Mirrors tests/check_probe_daily_candles.py D1-D7:
  P1  it imports nothing from tastytrade.order / tastytrade.account, makes no order, account or balance call, and
      imports no sqlite3 (it never opens a bot store)
  P2  it is on run_with_bot_env's PROBES list (so it runs only committed and unedited)
  P3  DRIVEN, offline: main() over a fake streamer asks ONE subscription per symbol at the ASKED interval, RTH unless
      --ext, starting about YEARS back; --ext asks extended hours
  P4  DRIVEN: one row per bar ts, the LAST update of a re-sent bar, sorted, ts_ms + ET time, NaN / None / another
      interval dropped; exit 0
  P5  DRIVEN: nothing served -> exit 1 and NO file written (a partial history must not look like a short one)
  P6  DRIVEN: the file lands under OUT_DIR as <SYM>_<INTERVAL>_<rth|ext>.csv and nowhere else (temp renamed)
  P7  DRIVEN: a bar with any price <= 0 is dropped - a zero VOLUME is not (an index reports 0 on every bar)
  P8  DRIVEN: the printed session count is the distinct ET DATES - across a DST change and an ET-midnight bar
No network. The tastytrade modules are stubbed BEFORE the probe is loaded, so this runs under the system python3
(which has no tastytrade) as well as the venv. Run: python3 tests/check_probe_intraday_candles.py
"""
import ast
import asyncio
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED = []
_P = os.path.join(_root, "tools", "probe_intraday_candles.py")
_ET = ZoneInfo("America/New_York")


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _stub_modules():
    """The probe imports tastytrade's streamer and the bot's session at load; the gate replaces both before main()."""
    tt = types.ModuleType("tastytrade"); tt.DXLinkStreamer = object
    dx = types.ModuleType("tastytrade.dxfeed"); dx.Candle = object
    tc = types.ModuleType("data.tasty_client"); tc.get_session = lambda: object()
    saved = {k: sys.modules.get(k) for k in ("tastytrade", "tastytrade.dxfeed", "data.tasty_client")}
    sys.modules.update({"tastytrade": tt, "tastytrade.dxfeed": dx, "data.tasty_client": tc})
    return saved


def _load():
    saved = _stub_modules()
    try:
        s = importlib.util.spec_from_file_location("_pic", _P)
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return m


def _ms(y, mo, d, hh, mm):
    return int(datetime(y, mo, d, hh, mm, tzinfo=_ET).timestamp() * 1000)


class _FakeStreamer:
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
    saved = (m.DXLinkStreamer, m.get_session, m.OUT_DIR, sys.argv)
    m.DXLinkStreamer, m.get_session, m.OUT_DIR = _FakeStreamer, (lambda: object()), out_dir
    sys.argv = ["probe_intraday_candles.py"] + argv + ["--idle", "0.3"]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = asyncio.run(m.main())
    finally:
        m.DXLinkStreamer, m.get_session, m.OUT_DIR, sys.argv = saved
    return rc, buf.getvalue(), list(_FakeStreamer.asked)


def _c(sym, t, o, h, l, c, v=1000.0, iv="5m"):
    return SimpleNamespace(event_symbol=f"{sym}{{={iv}}}", time=t, open=o, high=h, low=l, close=c, volume=v)


def _rows(path):
    return open(path).read().splitlines() if os.path.exists(path) else []


def main():
    try:
        src = open(_P, encoding="utf-8").read()
    except OSError as exc:
        check("P0 tools/probe_intraday_candles.py exists", False, str(exc))
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    tree = ast.parse(src)

    # P1 - no order / account module, no order / account / balance call, no sqlite3
    mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    mods += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    bad_mods = [x for x in mods if x.startswith(("tastytrade.order", "tastytrade.account", "sqlite3"))]
    forbid = {"place_order", "replace_order", "delete_order", "cancel_order", "place_complex_order",
              "get_balances", "get_positions", "get_live_orders", "get_order_history", "Account"}
    bad_calls = sorted({(n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", ""))
                        for n in ast.walk(tree) if isinstance(n, ast.Call)} & forbid)
    bad_names = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} & forbid)
    check("P1 no tastytrade.order / tastytrade.account / sqlite3 import and no order, account or balance call",
          not bad_mods and not bad_calls and not bad_names, f"modules={bad_mods} calls={bad_calls} names={bad_names}")

    rw = open(os.path.join(_root, "tools", "run_with_bot_env.py"), encoding="utf-8").read()
    check("P2 it is on run_with_bot_env's PROBES list",
          '"probe_intraday_candles.py": "tools/probe_intraday_candles.py"' in rw, "not listed")

    m = _load()
    nan = float("nan")
    a, b = _ms(2024, 1, 3, 9, 30), _ms(2024, 1, 3, 9, 35)
    feed = [
        _c("QQQ", b, 401.0, 402.0, 400.5, 401.5),
        _c("QQQ", a, 400.0, 401.0, 399.0, 400.5),
        _c("QQQ", b, 401.0, 402.5, 400.0, 402.25, 2000.0),     # re-sent: the LAST one wins
        _c("QQQ", _ms(2024, 1, 3, 9, 40), nan, nan, nan, nan),  # NaN bar: dropped
        _c("QQQ", _ms(2024, 1, 3, 9, 45), None, 1.0, 1.0, 1.0),  # no open: dropped
        _c("QQQ", a, 1.0, 1.0, 1.0, 1.0, iv="1m"),               # another interval: dropped
        _c("QQQ", _ms(2024, 1, 3, 10, 0), 1.0, 1.0, 1.0, 1.0, iv="15m"),  # another interval: dropped
    ]
    with tempfile.TemporaryDirectory() as td:
        rc, out, asked = _drive(m, feed, ["5m", "3", "QQQ"], td)
        ok3 = (len(asked) == 1 and asked[0][0] == ["QQQ"] and asked[0][1] == "5m" and asked[0][3] is False
               and asked[0][2] is not None
               and abs((datetime.now(timezone.utc) - asked[0][2]) - timedelta(days=round(3 * 365.25))) < timedelta(days=2))
        rc_e, _, asked_e = _drive(m, [], ["15m", "1", "SPX", "--ext"], td)
        ok3e = len(asked_e) == 1 and asked_e[0][1] == "15m" and asked_e[0][3] is True
        check("P3 DRIVEN: one subscription per symbol at the asked interval, RTH, about YEARS back; --ext asks EXT",
              ok3 and ok3e, f"asked={asked} ext={asked_e}")
        rows = _rows(os.path.join(td, "QQQ_5m_rth.csv"))
        want = ["ts_ms,et,open,high,low,close,volume",
                f"{a},2024-01-03T09:30-05:00,400.0,401.0,399.0,400.5,1000.0",
                f"{b},2024-01-03T09:35-05:00,401.0,402.5,400.0,402.25,2000.0"]
        check("P4 DRIVEN: one row per bar, last update wins, sorted, ts_ms + ET, junk and other intervals dropped, exit 0",
              rc == 0 and rows == want, f"rc={rc} rows={rows} out={out[-300:]!r}")
        left = sorted(os.listdir(td))
        check("P6 DRIVEN: exactly <SYM>_<INTERVAL>_rth.csv under OUT_DIR, no temp file left (the empty --ext run wrote none)",
              left == ["QQQ_5m_rth.csv"] and rc_e == 1, f"left={left} rc_ext={rc_e}")
    with tempfile.TemporaryDirectory() as td:
        rc, out, _ = _drive(m, [], ["5m", "2", "QQQ"], td)
        check("P5 DRIVEN: nothing served -> exit 1 and no file written", rc == 1 and os.listdir(td) == [],
              f"rc={rc} files={os.listdir(td)} out={out[-200:]!r}")
    z1, z2, z3 = _ms(2024, 2, 1, 9, 30), _ms(2024, 2, 1, 9, 35), _ms(2024, 2, 1, 9, 40)
    zfeed = [
        _c("SPX", z1, 0.0, 0.0, 0.0, 0.0, 0.0),                       # the feed's start placeholder
        _c("SPX", z2, 4900.0, 4905.5, 4898.25, 4904.0, 0.0),          # real, volume 0 (an index)
        _c("SPX", z3, 4904.0, 4910.0, 0.0, 4909.0, 0.0),              # a zero low: dropped
    ]
    with tempfile.TemporaryDirectory() as td:
        rc, out, _ = _drive(m, zfeed, ["5m", "1", "SPX"], td)
        rows = _rows(os.path.join(td, "SPX_5m_rth.csv"))
        check("P7 DRIVEN: a bar with any price <= 0 is dropped, a zero volume is kept",
              rc == 0 and rows == ["ts_ms,et,open,high,low,close,volume",
                                   f"{z2},2024-02-01T09:35-05:00,4900.0,4905.5,4898.25,4904.0,0.0"], f"rc={rc} rows={rows}")
    dfeed = [
        _c("QQQ", _ms(2024, 3, 8, 15, 55), 440.0, 441.0, 439.0, 440.5),   # Friday, EST
        _c("QQQ", _ms(2024, 3, 11, 9, 30), 442.0, 443.0, 441.0, 442.5),   # Monday, EDT (DST began 03-10)
        _c("QQQ", _ms(2024, 3, 11, 23, 55), 443.0, 443.5, 442.5, 443.0),  # 23:55 ET = 03:55 UTC 03-12: still 03-11
    ]
    with tempfile.TemporaryDirectory() as td:
        rc, out, _ = _drive(m, dfeed, ["5m", "1", "QQQ", "--ext"], td)
        line = [l for l in out.splitlines() if l.startswith("QQQ")]
        check("P8 DRIVEN: the session count is distinct ET dates (2 here), across DST and an ET-midnight bar",
              rc == 0 and line and " 2 sessions" in line[0].replace("    ", " ").replace("   ", " ").replace("  ", " "),
              f"rc={rc} line={line}")
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — the intraday-candle probe only reads, and writes one CSV of its own")
    return 0


if __name__ == "__main__":
    sys.exit(main())
