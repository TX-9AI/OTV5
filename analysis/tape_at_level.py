"""
analysis/tape_at_level.py  v1.0

r120 — WHAT THE TAPE DID AT THE BREAK LEVEL, MEASURED AT FIRE TIME.

Operator, 2026-08-25, after TSLA fired three ORB longs at 352.16 and lost all
three: "it can't hold the level." The chart says absorption; the trade record
said nothing at all, because ORB has never seen traded SIZE — it sees named
levels via liq_result and a price-vs-VWAP bias tag, and that is all.

⚠️ CAPTURED AT ENTRY BECAUSE THE INPUTS DO NOT SURVIVE. `prints` is a raw
per-tick stream on a 3-day retention window. A fit run in October cannot reach
August's ticks, and reconstructing "what traded at 352.16 during the 09:50
confirmation" weeks later would be expensive and wrong. Same reasoning as
fire_snapshot: the derived vector is taken AT the fire precisely because the
raw material is gone by the time anyone asks.

⚠️ THREE DEFINITIONAL CHOICES, MADE EXPLICITLY RATHER THAN BURIED:

  1. BAND = ±0.25 × ATR around the level, not a fixed tick count. A tick band
     means something different on CVX at $200 and SPX at $7600; an ATR band
     travels. Falls back to 0.05% of price when ATR is unavailable.
  2. WINDOW = from the break to the fire. That measures THE FIGHT — everything
     that traded while the level was being contested — rather than only the
     retest instant. The operator's observation was about repeated attempts,
     which is a window property, not a moment property.
  3. AGGRESSOR = `prints.aggressor_side`, as the venue tagged it. Not inferred
     from price-vs-mid; DXFeed already classifies it and re-deriving would be
     a worse copy of a fact we are given.

⚠️ RECORDED, NOT GATED. Nothing reads these. Operator: "observe first."
"""
from __future__ import annotations

import logging
import os
import sqlite3
from typing import Optional

logger = logging.getLogger(__name__)


def measure(symbol: str, level: float, since_epoch: float,
            until_epoch: float, atr: Optional[float] = None,
            db_path: Optional[str] = None) -> dict:
    """Volume and aggressor imbalance at `level` between the two timestamps.

    Returns {} when the tape cannot answer — a MISSING measurement, never a
    zero one. Zero volume at a level is a real and interesting reading; an
    unreadable store is not, and the two must not collapse together.
    """
    if not symbol or not level or level <= 0:
        return {}
    if not (until_epoch and since_epoch) or until_epoch <= since_epoch:
        return {}
    try:
        from data.candle_feed import feed_db_path
        path = db_path or feed_db_path()
    except Exception:                                          # noqa: BLE001
        path = db_path or ""
    if not path or not os.path.exists(path):
        return {}

    band = (0.25 * float(atr)) if atr and atr > 0 else (0.0005 * float(level))
    if band <= 0:
        return {}
    lo, hi = level - band, level + band

    try:
        # read-only: this runs inside the entry path and must never block the
        # feed writer, and must never be the reason a fill is not recorded.
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2.0)
        row = conn.execute(
            "SELECT COALESCE(SUM(size),0), "
            "       COALESCE(SUM(CASE WHEN aggressor_side='BUY'  THEN size END),0), "
            "       COALESCE(SUM(CASE WHEN aggressor_side='SELL' THEN size END),0), "
            "       COUNT(*) "
            "FROM prints WHERE symbol=? AND ts_epoch>=? AND ts_epoch<=? "
            "AND price BETWEEN ? AND ?",
            (symbol, since_epoch, until_epoch, lo, hi)).fetchone()
        conn.close()
    except Exception as exc:                                   # noqa: BLE001
        logger.debug("tape_at_level unavailable: %s", exc)
        return {}

    if row is None:
        return {}
    total, buys, sells, n = (float(row[0] or 0), float(row[1] or 0),
                             float(row[2] or 0), int(row[3] or 0))
    out = {
        "tape_vol_at_level":  round(total, 2),
        "tape_prints_at_level": n,
        "tape_band":          round(band, 4),
    }
    # Imbalance only where the venue actually tagged an aggressor. A feed that
    # sends no side would otherwise read as perfectly balanced, which is a
    # fabricated observation.
    tagged = buys + sells
    if tagged > 0:
        out["tape_buy_frac_at_level"] = round(buys / tagged, 4)
    return out
