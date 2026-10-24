"""
analysis/order_flow.py  v4.0
Signed aggression and depth, measured from the tape.

v4.0  2026-08-25  Built on the r64 streams. See docs/FEED_MANIFOLD.md.

Two questions this repo could never ask before r64:

  1. **WHO IS PAYING UP?** `TimeAndSale.aggressor_side` is buy- vs
     sell-initiated per print. The feed did not subscribe TimeAndSale at all,
     so "a move in evidence" could only mean *price moved* — never *someone
     lifted offers to move it*.

  2. **IS THERE ANYTHING THERE?** `Quote.bid_size`/`ask_size` — depth at the
     touch. FRC.1 put gross edge at ~2% of round-trip spread, computed from
     spread WIDTH alone. A 0.05 spread with 400 bid is a different market
     from the same spread with 3.

🔴 THIS REPLACES A PROXY WITH THE MEASUREMENT. TRADES.md on the sweep: "A DEEP
PIERCE MEANS A WEAK LEVEL, NOT A STRONG REJECTION — 1.28% median adverse
against 0.46%. Price went that far because it was WILLING TO." That is
aggression, inferred through distance because aggression was unavailable.

⚠️ CONFIRMATORY, NOT PREDICTIVE. Everything here describes what HAS happened:
who paid up, how much traded, what depth remains. v4's discipline is observing
a move already in evidence — flow is evidence, not a view.

⚠️ CONTRIBUTOR, NEVER A GATE. Returns None when the window is too thin.
**None means "not measurable", never 0.0** — a balanced tape (imbalance 0.0) is
a real reading; no prints is the absence of one.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

MIN_PRINTS = 12
DEFAULT_WINDOW_S = 300.0


def _side(v) -> str:
    s = str(v or "").strip().upper()
    if s.startswith("B"):
        return "BUY"
    if s.startswith("S"):
        return "SELL"
    return ""


def aggression(conn, symbol: str, window_s: float = DEFAULT_WINDOW_S,
               near_price: Optional[float] = None,
               band_pct: float = 0.0015) -> Optional[dict]:
    """Signed aggression over a window, optionally only near a price level.

    ⚠️ `near_price` IS WHAT MAKES THIS A LEVEL MEASUREMENT. Aggression across
    the whole tape says the session is bid; aggression WITHIN A BAND OF THE
    SHORT STRIKE says the thing that threatens a credit position. Same data,
    completely different question — measured 2026-08-22: whole tape -0.63
    while flow at the level read +0.60. Opposite conclusions.

    imbalance in [-1, +1]: +1 every contract lifted the offer, 0 balanced
    (A REAL READING), -1 every contract hit the bid.
    """
    try:
        since = time.time() - float(window_s)
        rows = conn.execute(
            "SELECT price, size, aggressor_side FROM prints"
            " WHERE symbol=? AND ts_epoch >= ?", (symbol, since)).fetchall()
    except Exception as exc:                                    # noqa: BLE001
        logger.debug("aggression read failed: %s", exc)
        return None
    if not rows:
        return None

    buy_v = sell_v = tot_v = 0.0
    n = 0
    for price, size, side in rows:
        if price is None or size is None:
            continue
        if near_price:
            if abs(float(price) - float(near_price)) > float(near_price) * band_pct:
                continue
        s = _side(side)
        sz = float(size)
        tot_v += sz
        n += 1
        if s == "BUY":
            buy_v += sz
        elif s == "SELL":
            sell_v += sz

    if n < MIN_PRINTS or tot_v <= 0:
        return None
    # ⚠️ UNTAGGED VOLUME STAYS IN THE DENOMINATOR. Dropping it would inflate
    # the imbalance of whichever side happened to be tagged — which is how a
    # thin, mostly-untagged tape starts reporting conviction it does not have.
    return {"prints": n, "volume": tot_v, "buy_volume": buy_v,
            "sell_volume": sell_v, "imbalance": (buy_v - sell_v) / tot_v,
            "tagged_frac": (buy_v + sell_v) / tot_v,
            "window_s": window_s, "near_price": near_price}


def depth(conn, streamer_symbol: str, window_s: float = 60.0) -> Optional[dict]:
    """Depth at the touch now, and how it changed across the window.

    🔴 DEPTH DEPLETION IS WHAT A REAL PUSH THROUGH LOOKS LIKE. A level about to
    fail empties out ahead of price; a level that holds keeps its size.
    """
    try:
        since = time.time() - float(window_s)
        rows = conn.execute(
            "SELECT ts_epoch, bid_price, ask_price, bid_size, ask_size"
            " FROM quote_series WHERE streamer_symbol=? AND ts_epoch >= ?"
            " ORDER BY ts_epoch", (streamer_symbol, since)).fetchall()
    except Exception as exc:                                    # noqa: BLE001
        logger.debug("depth read failed: %s", exc)
        return None
    clean = [r for r in rows if r[3] is not None and r[4] is not None]
    if len(clean) < 2:
        return None
    first, last = clean[0], clean[-1]
    bid_sz, ask_sz = float(last[3]), float(last[4])
    tot = bid_sz + ask_sz
    spread = None
    if last[1] is not None and last[2] is not None:
        mid = (float(last[1]) + float(last[2])) / 2.0
        if mid > 0:
            spread = (float(last[2]) - float(last[1])) / mid
    return {"bid_size": bid_sz, "ask_size": ask_sz,
            "book_imbalance": ((bid_sz - ask_sz) / tot) if tot > 0 else None,
            "bid_depth_ratio": (bid_sz / float(first[3])) if first[3] else None,
            "ask_depth_ratio": (ask_sz / float(first[4])) if first[4] else None,
            "spread_pct_of_mid": spread, "samples": len(clean)}


def pressure_into_level(conn, symbol: str, level_price: float, kind: str,
                        window_s: float = DEFAULT_WINDOW_S) -> Optional[dict]:
    """Is flow pressing INTO a level in the direction that would break it?

    ⚠️ THE SIGN IS RELATIVE TO THE LEVEL, NOT THE MARKET. A short call spread
    is threatened by BUYING; a short put spread by SELLING. Returning a raw
    imbalance would leave every caller to get that mapping right, and one of
    them eventually would not — and a study built on it would then "prove"
    flow exits are backwards.

    `threat` in [-1, +1]: positive = flow is pressing the level toward failure.
    """
    agg = aggression(conn, symbol, window_s, near_price=level_price)
    if agg is None:
        return None
    imb = agg["imbalance"]
    out = dict(agg)
    out["kind"] = kind
    out["threat"] = imb if str(kind).lower().startswith("res") else -imb
    return out
