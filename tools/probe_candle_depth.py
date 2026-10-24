#!/usr/bin/env python3
"""tools/probe_candle_depth.py — v1.1
v1.1  2026-10-03 — OTV4TEST r191 (AUD.2): bar times print in real Eastern time (zoneinfo), not a fixed UTC-4.

BOOT.7: HOW MUCH 1m / 5m / 15m HISTORY WILL TASTYTRADE SERVE?

v1.0 (2026-09-29) — OTV4TEST r176. Moved into the repo from /var/tmp so it can
      run under tools/run_with_bot_env.py, which runs only COMMITTED probes.

READ-ONLY, like r135's 1h probe: one streamer session of its own, one candle
subscription per interval starting DAYS_BACK calendar days ago (RTH only, as
the feed subscribes), counts what arrives, closes. Writes no table, touches no
service. Prints counts and dates only - never a credential.

Credentials: the bot's own get_session(), reading TT_* from THIS process's
environment - supplied by tools/run_with_bot_env.py (r176), never printed.

Usage:  venv/bin/python tools/run_with_bot_env.py probe_candle_depth.py [DAYS_BACK]
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.expanduser("~/options-trader"))
from tastytrade import DXLinkStreamer                           # noqa: E402
from tastytrade.dxfeed import Candle                            # noqa: E402
from data.tasty_client import get_session                       # noqa: E402

SYM = (os.environ.get("OT_INSTRUMENT") or "QQQ").strip()
DAYS_BACK = int(sys.argv[1]) if len(sys.argv) > 1 else 45
INTERVALS = ("1m", "5m", "15m")
IDLE_S, MAX_S = 20.0, 300.0
_CANON = {"m": "1m", "h": "1h", "d": "1d"}


def _interval(event_symbol: str):
    if "{=" not in (event_symbol or ""):
        return None
    tok = event_symbol.split("{=", 1)[1].rstrip("}").split(",", 1)[0].strip()
    return _CANON.get(tok, tok)


async def main() -> None:
    session = get_session()           # inside the running loop, as probe_aux_streams learned
    start = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    bars = {iv: set() for iv in INTERVALS}
    print(f"symbol {SYM} | asking {DAYS_BACK} calendar days back from {start:%Y-%m-%d} | RTH only")
    async with DXLinkStreamer(session) as streamer:
        for iv in INTERVALS:
            await streamer.subscribe_candle([SYM], iv, start_time=start, extended_trading_hours=False)
        t0 = last = asyncio.get_event_loop().time()
        while True:
            now = asyncio.get_event_loop().time()
            if now - last > IDLE_S or now - t0 > MAX_S:
                break
            try:
                c = await asyncio.wait_for(streamer.get_event(Candle), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            iv = _interval(getattr(c, "event_symbol", ""))
            if iv in bars and c.time and c.open is not None:
                bars[iv].add(int(c.time))
                last = asyncio.get_event_loop().time()
    try:                                         # r191: tz database, not a fixed UTC-4
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
    except Exception:                                           # noqa: BLE001
        et = timezone(timedelta(hours=-4))
    print(f"{'interval':8} {'bars':>7} {'sessions':>8}  oldest bar (ET)        newest bar (ET)")
    for iv in INTERVALS:
        ts = sorted(bars[iv])
        if not ts:
            print(f"{iv:8} {0:>7} {0:>8}  (nothing served)")
            continue
        days = {datetime.fromtimestamp(t / 1000, et).date() for t in ts}
        o = datetime.fromtimestamp(ts[0] / 1000, et)
        n = datetime.fromtimestamp(ts[-1] / 1000, et)
        print(f"{iv:8} {len(ts):>7} {len(days):>8}  {o:%Y-%m-%d %H:%M}       {n:%Y-%m-%d %H:%M}")


if __name__ == "__main__":
    asyncio.run(main())
