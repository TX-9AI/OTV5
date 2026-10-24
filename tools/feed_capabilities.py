#!/usr/bin/env python3
"""
tools/feed_capabilities.py  v1.0
v1.0  2026-09-22  OTV4TEST r100 — ASK THE BROKER WHAT IT CARRIES, AND READ THE
      ANSWER. This is the generator behind `feed.info`.

🔑 THE REPLY WAS ALWAYS THERE AND NOBODY READ IT. DXLink negotiates every event
type before it sends a byte. The client sends FEED_SETUP declaring
`acceptEventFields` — every field it can accept — and the server answers
FEED_CONFIG naming the fields it WILL deliver. The tastytrade SDK sends that
request on every subscribe and discards the reply, so "what does our plan
carry?" was guesswork from 2026-08-22 until this tool.

🔴 AN EVENT THE SERVER DECLINES RETURNS FEED_CONFIG WITH NO `eventFields` AND
NO ERROR FRAME. It is accepted, configured with nothing, and silent forever —
indistinguishable from a healthy subscription in the logs, which is exactly how
`underlying_series` stayed empty for a month while the feed logged
"subscribed QQQ Underlying" on every reconnect (§0.5).

⚠️ THE SYMBOL SPACE IS PART OF THE ANSWER. The same event is carried in one
space and declined in the other: TimeAndSale returns 21 fields on the EQUITY
symbol and no schema on options; Greeks returns 13 on OPTIONS and no schema on
the equity. Both are fully carried. Reading "no schema" as "not entitled"
without testing both spaces is how this was got wrong the first time — so this
tool ALWAYS probes both and refuses to report one.

⚠️ PROBE ONLY, AND THAT IS NOT A STYLE CHOICE. It opens its OWN streamer,
writes no table, touches no service and holds no lock. r118 is the precedent
for the alternative: one event type added to the live per-contract subscription
cost SPX its ENTIRE chain feed mid-session on 2026-08-25.

🔑 NEEDS NO LIVE TAPE. Schema negotiation is protocol-level and completes with
the market closed, so this is safe to run at any hour.

  cd ~/options-trader && venv/bin/python tools/feed_capabilities.py          # table
  cd ~/options-trader && venv/bin/python tools/feed_capabilities.py --json   # raw
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.expanduser("~/options-trader"))

from tastytrade import DXLinkStreamer                              # noqa: E402
from tastytrade.streamer import MAP_EVENTS                         # noqa: E402

from data.tasty_client import get_session                          # noqa: E402
from config import INSTRUMENT                                      # noqa: E402

# ⚠️ $OT_FEED_DB OVERRIDES, exactly as candle_feed resolves it. A tool that
# hardcodes the default reads a DIFFERENT store than the feed writes on any box
# where that variable is set, and would report an empty option arm as fact.
FEED_DB = (os.environ.get("OT_FEED_DB", "").strip()
           or os.path.expanduser("~/options-trader/data/feed_store.db"))

SETTLE_SECONDS = 5.0


def _option_symbols(limit: int = 8) -> list:
    """The streamer symbols candle_feed demonstrably subscribes Greeks/Quote to.

    🔴 READ THE STORE, DO NOT FETCH THE CHAIN. `fetch_chain()` is SYNCHRONOUS
    and spins up its OWN asyncio loop, then closes it — and the shared
    `get_session()` singleton binds its httpx client to whichever loop first
    used it. Calling it from inside our loop left the session attached to a
    CLOSED loop and DXLinkStreamer died on "/api-quote-tokens".
    """
    try:
        conn = sqlite3.connect(f"file:{FEED_DB}?mode=ro", uri=True, timeout=5)
        rows = [r[0] for r in conn.execute(
            "SELECT streamer_symbol FROM chain_marks "
            "WHERE streamer_symbol IS NOT NULL AND streamer_symbol != '' "
            "LIMIT ?", (limit,)).fetchall()]
        conn.close()
        return rows
    except Exception as exc:                                       # noqa: BLE001
        print(f"could not read chain_marks ({exc})", file=sys.stderr)
        return []


async def _negotiate(symbols: list, label: str) -> dict:
    """Subscribe every known event to `symbols` and keep the server's replies."""
    cfg: dict = {}
    session = get_session()
    async with DXLinkStreamer(session) as st:
        ws = st._websocket
        _orig = ws.receive_json

        async def _spy():
            msg = await _orig()
            if msg.get("type") == "FEED_CONFIG":
                ch = msg.get("channel")
                # ⚠️ KEEP THE RICHER REPLY. The server sends a bare config
                # first and the schema second; last-write-wins would discard
                # the answer we came for.
                if msg.get("eventFields") or ch not in cfg:
                    cfg[ch] = msg
            return msg

        ws.receive_json = _spy

        fails: list = []
        for name, cls in MAP_EVENTS.items():
            try:
                await asyncio.wait_for(st.subscribe(cls, symbols), timeout=12)
            except Exception as exc:                               # noqa: BLE001
                fails.append(f"{name}:{type(exc).__name__}")
            await asyncio.sleep(0.05)
        await asyncio.sleep(SETTLE_SECONDS)
        rev = st._channels_reversed

    out: dict = {"_subscribe_failures": fails}
    for ch, msg in cfg.items():
        nm = rev.get(ch, str(ch))
        fields = (msg.get("eventFields") or {}).get(nm)
        out[nm] = {"fields": fields,
                   "aggregationPeriod": msg.get("aggregationPeriod"),
                   "dataFormat": msg.get("dataFormat")}
    return out


async def main() -> None:
    session = get_session()
    token = await session._get("/api-quote-tokens")
    # 🔴 THE TOKEN VALUE IS NEVER PRINTED OR STORED. Only its metadata.
    meta = {k: v for k, v in token.items() if k != "token"}

    opts = _option_symbols()
    result = {
        "instrument": INSTRUMENT,
        "token": meta,
        "sdk_event_types": sorted(MAP_EVENTS.keys()),
        "probe_symbols": {"equity": [INSTRUMENT], "option": opts[:3]},
    }
    result["equity"] = await _negotiate([INSTRUMENT], "equity")
    if opts:
        result["option"] = await _negotiate(opts, "option")
    else:
        # ⚠️ ABSENT IS NOT "DECLINED". With no option symbols the option arm
        # cannot be reported at all, and saying so is the only honest output.
        result["option"] = None

    if "--json" in sys.argv:
        print(json.dumps(result, indent=1))
        return

    print(f"instrument  : {INSTRUMENT}")
    print(f"level       : {meta.get('level')}")
    print(f"dxlink-url  : {meta.get('dxlink-url')}")
    print(f"expires-at  : {meta.get('expires-at')}")
    print(f"option syms : {opts[:3] or '(none — option arm NOT probed)'}\n")

    print(f"  {'EVENT':<16}{'EQUITY':>8}{'OPTION':>8}   VERDICT")
    print("  " + "─" * 58)
    for name in sorted(MAP_EVENTS.keys()):
        eq = (result["equity"].get(name) or {}).get("fields")
        op = ((result["option"] or {}).get(name) or {}).get("fields")
        eq_n = str(len(eq)) if eq else "--"
        op_n = str(len(op)) if op else ("--" if result["option"] else "?")
        if eq and op:
            v = "carried, both spaces"
        elif eq:
            v = "EQUITY ONLY"
        elif op:
            v = "OPTION ONLY"
        elif result["option"] is None:
            v = "equity declines; option arm not probed"
        else:
            v = "DECLINED IN BOTH SPACES"
        print(f"  {name:<16}{eq_n:>8}{op_n:>8}   {v}")

    for space in ("equity", "option"):
        blk = result.get(space) or {}
        bad = blk.get("_subscribe_failures") or []
        if bad:
            print(f"\n  subscribe failures ({space}): {bad}")

    print("\n  Field lists: re-run with --json.")
    print("  This table is the source for feed.info — keep them in step.")


if __name__ == "__main__":
    asyncio.run(main())
