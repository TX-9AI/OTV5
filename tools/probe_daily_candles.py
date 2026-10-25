#!/usr/bin/env python3
"""tools/probe_daily_candles.py — v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
PRB.4: HOW FAR BACK WILL TASTYTRADE SERVE DAILY CANDLES, AND WHAT ARE THEY?

v1.1 (2026-10-21) — OTV4TEST r312 (PRB.5) — A BAR WITH ANY PRICE <= 0 IS DROPPED. r311's first run (19:28 ET) wrote the
      feed's all-zero start bar as the first row of BOTH files; 0.0 is not NaN, so v1.0 kept it, and a study divided
      by it. A zero VOLUME is kept: SPX, an index, reports volume 0 on every bar. check_probe_daily_candles D7.
v1.0 (2026-10-21) — OTV4TEST r311 (PRB.4). The operator, 2026-10-21 19:10 ET: "the daily candle is a yes".
      His gap / prior-day-extreme thesis ("each new day wants to take out a previous day's extreme") needs years
      of 1D history; this box holds QQQ 1d only from 08-10 and the warehouse 1m only from 07-08.

READ-ONLY, like probe_candle_depth (r135/r176): one streamer session of its own, ONE '1d' candle subscription per
symbol starting YEARS back (RTH only, as the feed subscribes), collects what arrives, closes. It opens no bot
store and touches no service. Its ONLY write is one CSV per symbol under OUT_DIR, written to a temp file and
renamed, so a run that stops half way leaves the previous file or none - never a short history that looks whole.
Nothing served -> exit 1 and no file. Prints counts and dates only - never a credential.

A dxFeed daily bar is stamped 00:00 UTC of its session (the local feed store's 1d rows read 20:00 ET the evening
before), so a row's date is the bar's UTC date. A bar re-sent while the stream settles keeps its LAST values.

Credentials: the bot's own get_session(), reading TT_* from THIS process's environment - supplied by
tools/run_with_bot_env.py (r176), never printed.

Usage:  venv/bin/python tools/run_with_bot_env.py probe_daily_candles.py [YEARS] [SYMBOL ...]
        YEARS defaults to 5; SYMBOL defaults to OT_INSTRUMENT (else QQQ). Output: OUT_DIR/<SYMBOL>_1d_rth.csv
"""
import asyncio
import math
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.expanduser("~/options-trader"))
from tastytrade import DXLinkStreamer                           # noqa: E402
from tastytrade.dxfeed import Candle                            # noqa: E402
from data.tasty_client import get_session                       # noqa: E402

OUT_DIR = "/var/tmp/daily_candles"
IDLE_S, MAX_S = 20.0, 300.0


def _num(x):
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _is_daily(event_symbol: str) -> bool:
    if "{=" not in (event_symbol or ""):
        return False
    tok = event_symbol.split("{=", 1)[1].rstrip("}").split(",", 1)[0].strip()
    return tok in ("d", "1d")


def _write(sym: str, bars: dict) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{sym}_1d_rth.csv")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("date,open,high,low,close,volume\n")
        for d in sorted(bars):
            o, h, l, c, v = bars[d]
            fh.write(f"{d},{o},{h},{l},{c},{v}\n")
    os.replace(tmp, path)
    return path


async def main() -> int:
    years = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    syms = [s.strip().upper() for s in sys.argv[2:] if s.strip()] or \
           [(os.environ.get("OT_INSTRUMENT") or "QQQ").strip().upper()]
    start = datetime.now(timezone.utc) - timedelta(days=round(years * 365.25))
    bars = {s: {} for s in syms}
    print(f"symbols {' '.join(syms)} | asking 1d from {start:%Y-%m-%d} ({years:g} years) | RTH only")
    session = get_session()           # inside the running loop, as probe_aux_streams learned
    async with DXLinkStreamer(session) as streamer:
        for s in syms:
            await streamer.subscribe_candle([s], "1d", start_time=start, extended_trading_hours=False)
        loop = asyncio.get_event_loop()
        t0 = last = loop.time()
        while True:
            now = loop.time()
            if now - last > IDLE_S or now - t0 > MAX_S:
                break
            try:
                c = await asyncio.wait_for(streamer.get_event(Candle), timeout=min(1.0, IDLE_S))
            except asyncio.TimeoutError:
                continue
            es = getattr(c, "event_symbol", "") or ""
            sym = es.split("{", 1)[0]
            vals = [_num(getattr(c, k, None)) for k in ("open", "high", "low", "close")]
            if sym not in bars or not _is_daily(es) or not c.time or any(v is None or v <= 0 for v in vals):
                continue
            d = datetime.fromtimestamp(int(c.time) / 1000, timezone.utc).date().isoformat()
            bars[sym][d] = (*vals, _num(getattr(c, "volume", None)) or 0.0)
            last = loop.time()
    rc = 0
    for s in syms:
        b = bars[s]
        if not b:
            print(f"{s:6} 0 daily bars served - no file written")
            rc = 1
            continue
        path = _write(s, b)
        ds = sorted(b)
        print(f"{s:6} {len(b):5} daily bars  {ds[0]} .. {ds[-1]}  -> {path}")
    return rc


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
