"""
analysis/gap_measure.py  v4.3
v4.3  2026-10-24  CD.3 (DISC.4) — THE GAP IS MEASURED FROM THE PRIOR SESSION'S DAILY BAR, AND IT IS CLASSIFIED. Two
      defects, both silent: (1) `classify` was imported from tests.gap_backfill, a module that never existed in this
      tree, so gap_class was never emitted (mainline DISC.4); it now comes from analysis/gap_class.py. (2) the gap
      was read off the 5m FRAME, which sees the prior session only when the frame happens to reach it - gap_pct was
      populated on 11 of 314 trade rows on QQQ-TEST (OTV4TEST, 2026-10-24). measure_gap now prefers the FEED STORE:
      the prior session = the newest 1d bar whose session date is before `day` (prior_close/high/low), today's open =
      the 09:30 1m bar; the frame is the fallback and gives the same gap_pct it always did. New record-only keys:
      gap_class, gap_bucket (the operator's <0.25 / 0.25-0.75 / >0.75), range_gap_pct (his range definition),
      prior_high, prior_low, prior_date, source ("store" | "frame"). Still None - never 0.0 - when neither can see.
v4.2  2026-10-03  OTV4TEST r213 (REC.1) — measure_gap also returns prior_close and today_open: the two prices the gap
      is measured from. derived/notes read ctx["prev_close"], which nothing ever set. Additive; gap_pct unchanged.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Overnight gap, measured rather than inherited as an ATR spike.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

#!/usr/bin/env python3
analysis/gap_measure.py — (A2.6b live path)
MEASURE THE OVERNIGHT GAP INSTEAD OF INHERITING IT AS AN ATR SPIKE.
    from analysis.gap_measure import measure_gap
    g = measure_gap(df_5m)          # -> {"gap_pct": .., "gap_class": ..} or None
────────────────────────────────────────────────────────────────────────────
WHY
────────────────────────────────────────────────────────────────────────────
Operator, 2026-08-01: *"the gaps you see overnight from previous close to
current open are big and meaningful, and they have to be reflected somewhere."*
**They are reflected — anonymously.** `atr_series` uses proper true range with
`prev_close = close.shift(1)` and the 5m tape is continuous, so the first 5m bar
after the open carries `|high − prev_close|` and a large gap **spikes ATR
immediately**, then decays over the window. The 25-bar angle correctly never
sees it (1m is session-scoped; a regression must not span a gap).
⚠️ **NOWHERE IS THE GAP MEASURED AS ITSELF.** No `gap_pct`, no `gap_class`,
nothing conditions on it. Every consumer sees a volatility number that is
partly last night's news and cannot tell which part.
⚠️ **AND IT IS THE ONLY PRE-OPEN DECISION-TIME INPUT IN THE STACK.** Every
bars from the session to exist. The gap is **fully formed at 09:30**, before a
single RTH bar prints. If anything collected can speak before the day starts,
this is it.
⚠️ AND UNLIKE EVERYTHING ELSE THIS WEEK, IT IS **FULLY BACKFILLABLE**.
`tests/gap_backfill.py` v1.1 already computes it per (date, symbol) from banked
OHLC. This module is the LIVE path; **the classification is imported from that
tool rather than reimplemented**, so the historical and live numbers cannot
drift apart (§7 — one lineage per quantity).
"""

from datetime import datetime, timezone
from typing import Dict, Optional
from zoneinfo import ZoneInfo

# CD.3 — the classifier lives on the shipped surface (analysis/gap_class.py); the tests.gap_backfill import that
# stood here was never satisfiable in this tree, so _classify was None on every box since the split.
from analysis.gap_class import classify as _classify, bucket as _bucket, range_gap_pct as _range_gap, FLAT_PCT

_ET = ZoneInfo("America/New_York")


def prior_session_from_store(symbol: str, day, db_path: Optional[str] = None) -> Optional[Dict[str, float]]:
    """{"prior_close", "prior_high", "prior_low", "prior_date"} from the feed store's newest 1d bar whose session is
    BEFORE `day` (a daily bar is stamped 00:00 UTC of its session), or None. Never raises."""
    try:
        import sqlite3
        from data.candle_feed import feed_db_path
        day_utc_ms = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1000)
        conn = sqlite3.connect(f"file:{db_path or feed_db_path()}?mode=ro", uri=True, timeout=5.0)
        try:
            r = conn.execute(
                "SELECT ts_epoch_ms, high, low, close FROM candles WHERE symbol=? AND interval='1d' "
                "AND ts_epoch_ms < ? AND close > 0 AND high > 0 AND low > 0 ORDER BY ts_epoch_ms DESC LIMIT 1",
                (symbol, day_utc_ms)).fetchone()
        finally:
            conn.close()
        if not r:
            return None
        return {"prior_close": float(r[3]), "prior_high": float(r[1]), "prior_low": float(r[2]),
                "prior_date": datetime.fromtimestamp(int(r[0]) / 1000, timezone.utc).date().isoformat()}
    except Exception:                                          # noqa: BLE001
        return None


def today_open_from_store(symbol: str, day, db_path: Optional[str] = None) -> Optional[float]:
    """The open of `day`'s 09:30 ET 1m bar from the feed store, or None. Never raises."""
    try:
        import sqlite3
        from data.candle_feed import feed_db_path
        ms = int(datetime(day.year, day.month, day.day, 9, 30, tzinfo=_ET).timestamp() * 1000)
        conn = sqlite3.connect(f"file:{db_path or feed_db_path()}?mode=ro", uri=True, timeout=5.0)
        try:
            r = conn.execute("SELECT open FROM candles WHERE symbol=? AND interval='1m' AND ts_epoch_ms=? AND open > 0",
                             (symbol, ms)).fetchone()
        finally:
            conn.close()
        return float(r[0]) if r else None
    except Exception:                                          # noqa: BLE001
        return None


def _finish(prior_close, today_open, prior_dir, flat_pct, source, prior_high=None, prior_low=None,
            prior_date=None) -> Optional[Dict[str, object]]:
    if prior_close is None or today_open is None or prior_close <= 0:
        return None
    gap_pct = 100.0 * (today_open - prior_close) / prior_close
    out = {"gap_pct": round(gap_pct, 4),
           "gap_abs_pct": round(abs(gap_pct), 4),
           "prior_close": round(prior_close, 4),     # r213
           "today_open": round(today_open, 4),
           "gap_class": _classify(gap_pct, prior_dir, flat_pct),       # CD.3
           "gap_bucket": _bucket(abs(gap_pct)),                          # CD.3
           "source": source}
    if prior_high is not None and prior_low is not None:
        out["prior_high"], out["prior_low"] = round(float(prior_high), 4), round(float(prior_low), 4)
        out["range_gap_pct"] = _range_gap(today_open, prior_high, prior_low, prior_close)
    if prior_date:
        out["prior_date"] = prior_date
    return out


def measure_gap(df_5m, prior_dir: int = 0, flat_pct: float = FLAT_PCT, symbol: Optional[str] = None,
                day=None, db_path: Optional[str] = None) -> Optional[Dict[str, object]]:
    """Overnight gap, or None when it cannot be established.

    CD.3 — WITH `symbol` (and `day`, default today ET) THE FEED STORE IS THE SOURCE: the prior session's 1d bar and
    today's 09:30 1m bar, which exist whether or not the 5m frame reaches yesterday. The frame is the fallback and
    yields exactly the gap_pct it did before.

    ⚠️ RETURNS None RATHER THAN 0.0 WHEN THE PRIOR SESSION CANNOT BE SEEN.
    A gap of exactly zero is a real and meaningful reading — the market opened
    unchanged. **A default of 0.0 would be indistinguishable from it**, which is
    precisely the confusion that made `flat_angle_deg`, `level_strength` and
    `vix_at_entry` look like measured nulls this week rather than empty columns.
    """
    try:
        if symbol:
            d = day or datetime.now(_ET).date()
            prior = prior_session_from_store(symbol, d, db_path)
            t_open = today_open_from_store(symbol, d, db_path)
            if prior and t_open is not None:
                return _finish(prior["prior_close"], t_open, prior_dir, flat_pct, "store",
                               prior["prior_high"], prior["prior_low"], prior["prior_date"])
        if df_5m is None or len(df_5m) < 2:
            return None
        idx = df_5m.index
        today = idx[-1].date()
        prior_i = None
        for i in range(len(df_5m) - 1, -1, -1):
            if idx[i].date() != today:
                prior_i = i
                break
        if prior_i is None:
            return None          # only today in frame — cannot see the gap
        prior_close = float(df_5m["close"].iloc[prior_i])
        # first bar OF TODAY, not the latest bar
        today_open = float(df_5m["open"].iloc[prior_i + 1])
        return _finish(prior_close, today_open, prior_dir, flat_pct, "frame")
    except Exception:                                          # noqa: BLE001
        return None
