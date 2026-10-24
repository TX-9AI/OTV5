#!/usr/bin/env python3
"""
tests/check_ext_polarity.py  v4.0

`tho=true` is the RTH echo. Its ABSENCE is the extended one.

v4.0  2026-08-21  Written with candle_feed v4.4, from the live outage.

WHAT HAPPENED. v3.16 identified the right attribute and read it backwards:
`_is_ext_of` returned True when `tho=true` was PRESENT. `tho` is
trading-hours-only, so that is precisely the RTH stream.

  · 1m/5m/15m/1d register only (sym, tf, False). Every RTH echo looked up
    True, missed the route table, and was DROPPED. The entire intraday tape,
    every box, for a whole session. fetch_quote reads the newest 1m bar, so
    the fleet priced off the prior day's close.
  · 1h registers BOTH keys, so nothing missed — the streams SWAPPED. Plain
    took extended, _EXT took RTH. Both current, both wrong, and 1h looking
    healthy is what hid the other four tenors.

⚠️ THE ECHOES BELOW ARE COPIED FROM THE JOURNAL, not invented. Guessing the
vendor's format is how the original defect got written; these are the exact
event_symbols DXFeed sent on NVDA at 13:52 UTC on 2026-08-21.

⚠️ AND C3 IS THE ONE THAT MATTERS. Polarity alone is a coin flip that a
sign-flipped implementation would still pass in one direction. C3 drives the
REAL router — the same three-tuple lookup _on_candle does — and asserts every
tenor resolves to a live route, which is what actually broke.

BORN RED, verified against HEAD f68e228 + r55:
  C1 -> "NVDA{=m,tho=true} reported ext=True - that is the RTH echo"
  C3 -> "1m resolves to NO route - candles are being dropped"

Run:  cd ~/options-trader-v4 && python3 tests/check_ext_polarity.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROBLEMS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


def main() -> int:
    print("=" * 68)
    print("EXT POLARITY: tho=true is RTH, its absence is extended")
    print("=" * 68)

    from data.candle_feed import CandleFeed

    # ── C1/C2 the predicate, on the vendor's real strings ────────────────
    rth = ["NVDA{=m,tho=true}", "NVDA{=5m,tho=true}", "NVDA{=15m,tho=true}",
           "NVDA{=d,tho=true}", "NVDA{=h,tho=true}", "VIX{=m,tho=true}"]
    ext = ["NVDA{=h}"]

    for e in rth:
        check(f"C1 {e} is RTH", CandleFeed._is_ext_of(e) is False,
              f"{e} reported ext=True - that is the RTH echo")
    for e in ext:
        check(f"C2 {e} is EXTENDED", CandleFeed._is_ext_of(e) is True,
              f"{e} reported ext=False - the extended stream would land on the "
              f"plain route and overwrite the RTH tape")

    # ── C3 every tenor resolves to a live route ──────────────────────────
    # The three-tuple lookup _on_candle performs, against a route table built
    # the way the feed builds it.
    import config
    feed = CandleFeed.__new__(CandleFeed)
    smap = {}
    for tf in config.TIMEFRAMES.keys():
        smap[("NVDA", tf, False)] = "NVDA"
    smap[("NVDA", "1h", True)] = "NVDA_EXT"
    feed.symbol_map = smap

    expected = {
        "NVDA{=m,tho=true}":   ("1m",  "NVDA"),
        "NVDA{=5m,tho=true}":  ("5m",  "NVDA"),
        "NVDA{=15m,tho=true}": ("15m", "NVDA"),
        "NVDA{=d,tho=true}":   ("1d",  "NVDA"),
        "NVDA{=h,tho=true}":   ("1h",  "NVDA"),
        "NVDA{=h}":            ("1h",  "NVDA_EXT"),
    }
    for ev, (tf, want) in expected.items():
        got_tf = feed._interval_of(ev)
        got = feed.symbol_map.get(("NVDA", got_tf or "", CandleFeed._is_ext_of(ev)))
        check(f"C3 {tf:3} -> {want}", got == want,
              f"{tf} resolves to {got!r}, wanted {want!r}"
              + (" - candles are being dropped" if got is None else
                 " - the two streams are SWAPPED"))

    print("=" * 68)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        print("  A dropped tenor is silent; a swapped one looks current.")
        return 1
    print("  ALL GREEN - every tenor routes, RTH and extended stay apart")
    return 0


if __name__ == "__main__":
    sys.exit(main())
