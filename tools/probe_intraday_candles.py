#!/usr/bin/env python3
"""tools/probe_intraday_candles.py — v1.0
PRB.6: HOW FAR BACK WILL TASTYTRADE SERVE INTRADAY CANDLES, AND WHAT ARE THEY?

v1.0 (2026-10-24) — PRB.6. The operator, 2026-10-24 16:04 ET: "14, yes worthwhile" - years of 5m bars, so a
      trend-vs-chop study reads ~1,000 sessions instead of the ~42 a box's feed store holds. Modelled line for line
      on tools/probe_daily_candles.py v1.1 (PRB.4/PRB.5); the per-box pull and the study/ upload are the 1d corpus's
      tooling (1-REPORTER, 2026-10-24).

READ-ONLY, like probe_daily_candles and probe_candle_depth: one streamer session of its own, ONE candle subscription
per symbol at the asked INTERVAL starting YEARS back (RTH only unless --ext), collects what arrives, closes. It opens
no bot store and touches no service. Its ONLY write is one CSV per symbol under OUT_DIR, written to a temp file and
renamed, so a run that stops half way leaves the previous file or none - never a short history that looks whole.
Nothing served -> exit 1 and no file. Prints counts and dates only - never a credential.

THE DEPTH ANSWER: per symbol it prints the rows, the first and last bar and the number of distinct ET sessions served.
That number is what this probe exists to measure (probe_candle_depth, BOOT.7, only counts 1m/5m/15m over DAYS_BACK
for the box's one symbol and writes nothing).

Rows: ts_ms (the bar's UTC epoch ms, as dxFeed stamps it) and et (its ET wall time, ISO), then OHLCV. A bar re-sent
while the stream settles keeps its LAST values. Dropped: NaN / None prices, any price <= 0 (the feed's all-zero start
placeholder, PRB.5), and events of another interval. A zero VOLUME is kept (an index reports 0 on every bar).

TIMEOUTS ARE LARGER THAN 1d's AND ARE ARGUMENTS: 5m over 5 years is ~98,000 RTH bars per symbol (~390,000 with
--ext), and the history arrives in pages with pauses between them. IDLE (default 60 s without a new bar ends the
symbol's wait) and MAX (default 1800 s wall clock for the whole run) can be raised for longer asks. MEMORY: bars are a
dict per symbol, ~200 bytes a bar -> ~20 MB per symbol at 5m RTH x 5 y; run one symbol at a time on a 908 MB box.

Credentials: the bot's own get_session(), reading TT_* from THIS process's environment - supplied by
tools/run_with_bot_env.py (r176), never printed.

Usage:  venv/bin/python tools/run_with_bot_env.py probe_intraday_candles.py [INTERVAL] [YEARS] [SYMBOL ...]
            [--ext] [--idle SECONDS] [--max SECONDS]
        INTERVAL 1m|5m|15m|30m|1h (default 5m); YEARS default 5; SYMBOL defaults to OT_INSTRUMENT (else QQQ).
        Output: OUT_DIR/<SYMBOL>_<INTERVAL>_<rth|ext>.csv
"""
import asyncio
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.expanduser("~/options-trader"))
from tastytrade import DXLinkStreamer                           # noqa: E402
from tastytrade.dxfeed import Candle                            # noqa: E402
from data.tasty_client import get_session                       # noqa: E402

OUT_DIR = "/var/tmp/intraday_candles"
IDLE_S, MAX_S = 60.0, 1800.0
INTERVALS = ("1m", "5m", "15m", "30m", "1h")
_ET = ZoneInfo("America/New_York")


def _num(x):
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _interval_of(event_symbol: str) -> str:
    """The interval token of a dxFeed candle symbol ("QQQ{=5m}" -> "5m", "QQQ{=5m,tho=true}" -> "5m"); "" if none."""
    if "{=" not in (event_symbol or ""):
        return ""
    return event_symbol.split("{=", 1)[1].rstrip("}").split(",", 1)[0].strip()


def _same_interval(token: str, interval: str) -> bool:
    """dxFeed may spell an hour "1h" or "h" and a minute count with or without its 1; compare the normal forms."""
    def norm(t):
        t = (t or "").strip().lower()
        return ("1" + t) if t in ("m", "h", "d") else t
    return norm(token) == norm(interval)


def _write(sym: str, interval: str, ext: bool, bars: dict) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{sym}_{interval}_{'ext' if ext else 'rth'}.csv")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("ts_ms,et,open,high,low,close,volume\n")
        for ts in sorted(bars):
            o, h, l, c, v = bars[ts]
            et = datetime.fromtimestamp(ts / 1000, _ET).isoformat(timespec="minutes")
            fh.write(f"{ts},{et},{o},{h},{l},{c},{v}\n")
    os.replace(tmp, path)
    return path


def _sessions(bars: dict) -> int:
    """Distinct ET calendar dates the bars fall on (an RTH bar is always inside its ET session date)."""
    return len({datetime.fromtimestamp(ts / 1000, _ET).date() for ts in bars})


def _args(argv):
    ext, idle, mx, pos = False, IDLE_S, MAX_S, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--ext":
            ext = True
        elif a in ("--idle", "--max") and i + 1 < len(argv):
            v = float(argv[i + 1])
            idle, mx = (v, mx) if a == "--idle" else (idle, v)
            i += 1
        else:
            pos.append(a)
        i += 1
    interval = pos[0] if pos and pos[0] in INTERVALS else "5m"
    rest = pos[1:] if pos and pos[0] in INTERVALS else pos
    years = float(rest[0]) if rest else 5.0
    syms = [s.strip().upper() for s in rest[1:] if s.strip()] or \
           [(os.environ.get("OT_INSTRUMENT") or "QQQ").strip().upper()]
    return interval, years, syms, ext, idle, mx


async def main() -> int:
    interval, years, syms, ext, idle, mx = _args(sys.argv[1:])
    start = datetime.now(timezone.utc) - timedelta(days=round(years * 365.25))
    bars = {s: {} for s in syms}
    print(f"symbols {' '.join(syms)} | asking {interval} from {start:%Y-%m-%d} ({years:g} years) | "
          f"{'extended hours' if ext else 'RTH only'} | idle {idle:g}s max {mx:g}s")
    session = get_session()           # inside the running loop, as probe_aux_streams learned
    async with DXLinkStreamer(session) as streamer:
        for s in syms:
            await streamer.subscribe_candle([s], interval, start_time=start, extended_trading_hours=ext)
        loop = asyncio.get_event_loop()
        t0 = last = loop.time()
        while True:
            now = loop.time()
            if now - last > idle or now - t0 > mx:
                break
            try:
                c = await asyncio.wait_for(streamer.get_event(Candle), timeout=min(1.0, idle))
            except asyncio.TimeoutError:
                continue
            es = getattr(c, "event_symbol", "") or ""
            sym = es.split("{", 1)[0]
            vals = [_num(getattr(c, k, None)) for k in ("open", "high", "low", "close")]
            if (sym not in bars or not _same_interval(_interval_of(es), interval) or not c.time
                    or any(v is None or v <= 0 for v in vals)):
                continue
            bars[sym][int(c.time)] = (*vals, _num(getattr(c, "volume", None)) or 0.0)
            last = loop.time()
    rc = 0
    for s in syms:
        b = bars[s]
        if not b:
            print(f"{s:6} 0 {interval} bars served - no file written")
            rc = 1
            continue
        path = _write(s, interval, ext, b)
        ts = sorted(b)
        f = datetime.fromtimestamp(ts[0] / 1000, _ET).strftime("%Y-%m-%d %H:%M")
        l = datetime.fromtimestamp(ts[-1] / 1000, _ET).strftime("%Y-%m-%d %H:%M")
        print(f"{s:6} {len(b):7} {interval} bars  {f} .. {l} ET  {_sessions(b):5} sessions  -> {path}")
    return rc


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
