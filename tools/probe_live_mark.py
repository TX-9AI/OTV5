#!/usr/bin/env python3
"""tools/probe_live_mark.py — v1.0
ASK THE BROKER FOR A FEW OPTION MARKS THROUGH THE BOT'S OWN LIVE FALLBACK — READ ONLY, NO ORDER OF ANY KIND.

v1.0 (2026-10-20) — OTV4TEST r308 (PRB.3, LIVE.1 F4 proof). The operator, 2026-10-20 10:53 ET: "Concur" (a read-only
      F4 probe as a small delivery, run after the close). r246 (mirror of otv4 r468) repaired
      PositionManager._get_option_mark - a LIVE box with no chain in hand prices a position through the REST
      market-data endpoint - and tests/check_live_mark_fallback.py proves it against a fake SDK only. Nothing has
      ever called it against the real broker. If it fails live, F3 (r256) posts NO close for want of a mark and
      pages until the 15:55 cross: safe, but a stop that should fire does not.

WHAT IT DOES: picks six contracts on the nearest expiry (three puts, three calls, around the middle of the listed
strikes; SPX: SPXW only), and for each one
  1. calls the REAL execution.position_manager.PositionManager._get_option_mark (the function itself, not a copy)
     with data.tasty_client.get_client() - exactly what the live no-chain path passes - and times it;
  2. prints the raw REST fields it read from (bid / ask / mark / last) so a None can be told apart: an empty
     book after the bell, a refused call, or a transport failure.
SAFETY, by construction: it imports nothing from tastytrade.order or tastytrade.account and calls no order,
account or balance method; tests/check_probe_live_mark.py proves that by AST and drives main() offline.
AFTER THE BELL a book may be empty (bid/ask 0) and the function falls back to mark/last - that proves the call
path and the transport, not a mid-session mark.
Run ONLY through the r176 wrapper (it carries the bot's TT_* keys, never prints them):
    /home/ubuntu/options-trader/venv/bin/python /home/ubuntu/options-trader/tools/run_with_bot_env.py probe_live_mark.py
"""
import os
import sys
import time
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tastytrade.instruments import get_option_chain, OptionType                    # noqa: E402
from tastytrade.market_data import get_market_data                                 # noqa: E402
from tastytrade.instruments import InstrumentType                                  # noqa: E402
from data.tasty_client import get_client, sdk_result                               # noqa: E402
from execution.position_manager import PositionManager                             # noqa: E402

SYM = (os.environ.get("OT_INSTRUMENT") or "").strip().upper()


def _pick(chain):
    """Six contracts on the nearest expiry: three puts and three calls around the middle listed strike."""
    future = sorted(d for d in chain if d >= date.today())
    if not future:
        return None, []
    d0 = future[0]
    opts = [o for o in chain[d0] if SYM != "SPX" or getattr(o, "root_symbol", "") == "SPXW"]
    out = []
    for kind in (OptionType.PUT, OptionType.CALL):
        side = sorted((o for o in opts if o.option_type == kind), key=lambda o: float(o.strike_price))
        if len(side) >= 3:
            m = len(side) // 2
            out += side[m - 1:m + 2]
    return d0, out


def main() -> int:
    if not SYM:
        print("probe_live_mark: no OT_INSTRUMENT - run it through tools/run_with_bot_env.py")
        return 2
    client = get_client()
    print(f"client object: {type(client).__name__} (the live no-chain path passes this to _get_option_mark)")
    chain = sdk_result(get_option_chain(client, SYM))
    d0, picks = _pick(chain)
    if not picks:
        print(f"no contracts to probe on {SYM}")
        return 3
    pm = PositionManager.__new__(PositionManager)      # the real method; no __init__ (no stores, no broker state)
    pm._mark_fail_warned = set()
    print(f"\n{SYM} {d0}: {len(picks)} contracts (PositionManager._get_option_mark, then the raw REST fields)")
    got = 0
    for o in picks:
        t0 = time.monotonic()
        v = PositionManager._get_option_mark(pm, client, o.symbol)
        ms = (time.monotonic() - t0) * 1000
        try:
            md = sdk_result(get_market_data(client, o.symbol, InstrumentType.EQUITY_OPTION))
            raw = " ".join(f"{k}={getattr(md, k, None)}" for k in ("bid", "ask", "mark", "last"))
        except Exception as exc:  # noqa: BLE001
            raw = f"raw read failed: {type(exc).__name__}: {str(exc)[:120]}"
        got += v is not None
        print(f"  {o.symbol:24s} mark={'None' if v is None else f'{v:.4f}':>9s}  {ms:6.0f} ms  {raw}")
    print(f"\nRESULT: {got} of {len(picks)} priced"
          + ("" if got == len(picks) else " - a None above is what a LIVE close would see (F3: no close, page)"))
    return 0 if got else 1


if __name__ == "__main__":
    sys.exit(main())
