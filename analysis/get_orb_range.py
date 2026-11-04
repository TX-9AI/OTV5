"""
analysis/get_orb_range.py  v5.2
v5.2  2026-11-04  OTV5 r74 (ORP.3) — NEVER ESTABLISHED FROM A PARTIAL TAPE: NEW STATE INCOMPLETE (exit 4). 2026-11-02 the
      AMZN feed was refused 09:31-10:55 ET; at 10:56:51 the five 1m bars were not all on the feed, so the v5.1 fallback
      ESTABLISHED the range from the lone 09:30 5m row - captured when the socket dropped (243.02-244.43 against the
      true 242.28-246.39) - and Hunt traded against it all afternoon. The fallback is removed: the range is ESTABLISHED
      only from the five 1m bars 09:30-09:34 (the official print, ORP.1), with a 09:35+ 1m row and SETTLE_S as before,
      AND analysis/opening_tape.problem() finding them complete - all five present and, when today's 09:30 5m row
      exists, its high and low equal to theirs. From 09:36 a tape that fails that is INCOMPLETE (exit 4): the range
      carried is the last valid one, the reason is written ("reason") and printed, and main._fetch_orb_range keeps the
      day's range unestablished, pages once and retries every tick while data/candle_feed re-pulls 1m and 5m from
      09:30 on its own session. Before 09:36 it is IN_PROGRESS as before; with no tape of today at all it is EXPIRED
      as before. Gate tests/check_orb_incomplete.py; check_orb_establish_closed C4 re-pointed (v5.1).
v5.1  2026-10-27  OTV5 r40 (ORP.2) — ESTABLISHED ONLY FROM A CLOSED OPENING RANGE: THE FIVE 1m BARS, THE OFFICIAL PRINT.
      Until now the range was ESTABLISHED the moment the clock passed 09:34:59 and a 09:30 5m row existed - but the
      feed store writes FORMING bars, so that row could still be moving. CRM 2026-10-26 froze H=250.14 at 09:35:01 ET;
      the 09:34 minute closed at its high of 250.38, and both CRM longs fired on a break the official range does not
      show (-$85). The docstring always said "the candle is closed", and ORP.1's ruling (OTV4TEST r222, 2026-10-03) is
      the high and low of the five 1m bars 09:30-09:34, only when all five are on the feed. Now: ESTABLISHED from those
      five bars once a 1m row at 09:35 or later exists (proof the 09:34 bar is done) and the clock is SETTLE_S past
      09:35:00; failing the five 1m bars, from the 09:30 5m row once a later 5m row exists and a full minute has
      passed (the old source, with proof it closed). Otherwise IN_PROGRESS (exit 2), carrying the last valid range;
      main._fetch_orb_range retries on the next tick, so establishment slips by about one tick.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.2  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v4.1 2026-09-26  OTV4TEST r146 — no QQQ fallback: argv, then utils.instrument.box_instrument() (this process, the bot unit, else UNSET).
Opening-range accessor with the date filter.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

#!/usr/bin/env python3
analysis/get_orb_range.py — Resolve the opening range for the instrument and
write it to orb_range.json with an explicit STATE. Always writes the last
valid range so consumers always have something to show; the state tells them
what that range represents.
CRITICAL: the opening candle is fetched through the bot's own data layer
(data.market_data.fetch_candles) — the SAME source and symbol mapping the rest
of the bot uses. As of repo v3.0 that source is the single shared
TastyTrade/DXFeed store (data/candle_feed.py), the exact tape the bot trades
on. Earlier versions fetched a DIFFERENT Yahoo symbol than the bot's feed, so
the ORB range never matched the bot's price feed or the operator's chart.
Never fetch here with a private symbol map again — always go through
fetch_candles.
Three states only (the "call-out"):
    ESTABLISHED  — today's 9:30-9:35 ET candle is closed. high/low/date are
                   today's. The only tradeable state.
    IN_PROGRESS  — now is inside today's opening candle (09:30:00-09:34:59 ET).
                   Today's range is still forming; high/low/date carry the LAST
                   valid RTH range until the candle closes.
    EXPIRED      — no today range yet (pre-open, or today's candle not on the
                   feed yet). high/low/date carry the LAST valid RTH range
                   (e.g. Friday's on a Monday pre-open).
v1.0 — original — ^GSPC via a direct Yahoo client, most-recent 9:30 candle, no guard.
strict today-only gating (wrote nothing before ready).
three-state model; always write the last valid range.
SOURCE FIX: fetch the opening candle via
        data.market_data.fetch_candles() so the range uses the identical feed
        and symbol as the bot (^SPX for SPX, not ^GSPC). Removed the private
        Yahoo import and SYMBOL_MAP entirely.
YAHOO-FINANCE PURGE / data stream mapping optimization
        (repo v3.0): no logic change — fetch_candles now reads the single
        shared TastyTrade feed store, so the 5m opening candle is the exact
        tape the bot trades on. Docstring scrubbed.
Exit codes (consumed by main._fetch_orb_range):
    0 = ESTABLISHED   1 = hard error (no data / write failure)
    2 = IN_PROGRESS   3 = EXPIRED   4 = INCOMPLETE (r74, ORP.3: today's opening tape is short or disagrees)
"""

import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Make the install root importable so this standalone script can reuse the
# bot's own data layer instead of duplicating symbol maps / fetch logic.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.market_data import fetch_candles
from analysis import opening_tape                     # r74 (ORP.3)

ET = ZoneInfo("America/New_York")
OUTPUT_PATH = os.path.expanduser("~/options-trader/orb_range.json")

STATUS_ESTABLISHED = "ESTABLISHED"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_EXPIRED     = "EXPIRED"
STATUS_INCOMPLETE  = "INCOMPLETE"       # r74 (ORP.3)

EXIT_CODE = {
    STATUS_ESTABLISHED: 0,
    STATUS_IN_PROGRESS: 2,
    STATUS_EXPIRED:     3,
    STATUS_INCOMPLETE:  4,
}
INCOMPLETE_FROM = (9, 36)               # r74 (ORP.3): before this a short tape is still IN_PROGRESS

# Enough 5m candles to always include at least one prior trading day's open
# (for the EXPIRED/IN_PROGRESS carry) even across a weekend.
ORB_CANDLE_LOOKBACK = 200


def resolve_symbol() -> str:
    """argv[1] -> OT_INSTRUMENT -> the bot unit's OT_INSTRUMENT -> UNSET (r146: never QQQ by default)."""
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1].strip()
    from utils.instrument import box_instrument
    return box_instrument()


def _candle_to_range(ts, row, status: str, symbol: str, now: datetime) -> dict:
    high = float(row["high"])
    low = float(row["low"])
    return {
        "status":     status,
        "date":       ts.strftime("%Y-%m-%d"),
        "high":       round(high, 4),
        "low":        round(low, 4),
        "width":      round(high - low, 4),
        "fetched_at": now.strftime("%Y-%m-%d %H:%M:%S ET"),
        "symbol":     symbol,
    }


SETTLE_S = 10          # r40 (ORP.2): seconds past 09:35:00 before the 09:34 bar is taken as final


def _closed_print(df_1m, today, now):
    """r40 (ORP.2) — (high, low) of TODAY's five 1m bars 09:30-09:34 (main._official_print's rule), or None unless
    all five are present, a 1m row at 09:35 or later exists (the store writes forming bars, so a later row is the
    proof the 09:34 bar is done) and the clock is SETTLE_S past 09:35:00."""
    if df_1m is None or getattr(df_1m, "empty", True):
        return None
    if (now.hour, now.minute, now.second) < (9, 35, SETTLE_S):
        return None
    day = [t for t in df_1m.index if t.date() == today]
    win = [t for t in day if t.hour == 9 and 30 <= t.minute <= 34]
    if len({t.minute for t in win}) != 5 or not any((t.hour, t.minute) >= (9, 35) for t in day):
        return None
    rows = df_1m.loc[win]
    hi, lo = float(rows["high"].max()), float(rows["low"].min())
    return (hi, lo) if hi > lo > 0 else None


def resolve_orb_range(symbol: str, now: datetime = None) -> dict:
    """Return the last valid opening range tagged with its state.

    Raises ValueError only when there is no usable data at all.
    """
    now = now or datetime.now(ET)
    today = now.date()
    # Today's opening candle is forming during 09:30:00-09:34:59 ET.
    in_opening_window = (now.hour == 9 and 30 <= now.minute <= 34)

    # SAME feed/symbol as the bot (SPX -> ^SPX). ET-indexed OHLCV, lowercase cols.
    df = fetch_candles(symbol, "5m", ORB_CANDLE_LOOKBACK)
    if df is None or df.empty:
        raise ValueError(f"no 5m data returned for {symbol}")

    opens = [(ts, row) for ts, row in df.iterrows()
             if ts.hour == 9 and ts.minute == 30]
    todays = [(ts, row) for ts, row in opens if ts.date() == today]
    priors = [(ts, row) for ts, row in opens if ts.date() < today]

    def last_valid_prior():
        for ts, row in reversed(priors):
            if float(row["high"]) > float(row["low"]):
                return ts, row
        return None

    # ── IN_PROGRESS: inside today's opening window — carry last valid range ──
    if in_opening_window:
        pv = last_valid_prior()
        if pv is None:
            raise ValueError("no prior valid opening range to carry (IN_PROGRESS)")
        return _candle_to_range(pv[0], pv[1], STATUS_IN_PROGRESS, symbol, now)

    # ── ESTABLISHED: past the window, today's opening range CLOSED (r40, ORP.2) and COMPLETE (r74, ORP.3) ──
    df1 = fetch_candles(symbol, "1m", 400)
    day1 = ([t for t in df1.index if t.date() == today and (t.hour, t.minute) >= (9, 30)]   # RTH rows only
            if df1 is not None and not getattr(df1, "empty", True) else [])
    if todays or day1:
        bars = {}
        for t in day1:
            if t.hour == 9 and 30 <= t.minute <= 34:
                r1 = df1.loc[t]
                bars[t.minute] = (float(r1["high"]), float(r1["low"]))
        b5 = (float(todays[-1][1]["high"]), float(todays[-1][1]["low"])) if todays else None
        pr = _closed_print(df1, today, now)
        why = opening_tape.problem(bars, b5)
        if pr is not None and why is None:
            ts = todays[-1][0] if todays else min(day1)
            return _candle_to_range(ts, {"high": pr[0], "low": pr[1]}, STATUS_ESTABLISHED, symbol, now)
        # r74 (ORP.3): no fallback to the lone 5m row - a partial capture is exactly what it would freeze
        status = STATUS_INCOMPLETE if (now.hour, now.minute) >= INCOMPLETE_FROM else STATUS_IN_PROGRESS
        if status == STATUS_INCOMPLETE and why is None:
            why = "no 1m row at 09:35 or later yet (the 09:34 bar is not proven closed)"
        pv = last_valid_prior()
        out = (_candle_to_range(pv[0], pv[1], status, symbol, now) if pv is not None else
               {"status": status, "date": today.strftime("%Y-%m-%d"), "high": 0.0, "low": 0.0, "width": 0.0,
                "fetched_at": now.strftime("%Y-%m-%d %H:%M:%S ET"), "symbol": symbol})
        if status == STATUS_INCOMPLETE:
            out["reason"] = why
        if pv is not None or status == STATUS_INCOMPLETE:
            return out
        # IN_PROGRESS with no prior to carry - fall through to EXPIRED's error.

    # ── EXPIRED: pre-open, or today's candle not on the feed yet ──
    pv = last_valid_prior()
    if pv is None:
        raise ValueError("no valid opening range found in lookback window")
    return _candle_to_range(pv[0], pv[1], STATUS_EXPIRED, symbol, now)


def main():
    symbol = resolve_symbol()
    try:
        result = resolve_orb_range(symbol)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, "w") as f:
            json.dump(result, f, indent=2)
    except Exception as e:
        print(f"ERROR writing {OUTPUT_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"ORB range [{result['status']}]: {result['symbol']} {result['date']} "
          f"H={result['high']} L={result['low']} W={result['width']}"
          + (f" | {result['reason']}" if result.get("reason") else ""))
    print(f"Written to: {OUTPUT_PATH}")
    sys.exit(EXIT_CODE.get(result["status"], 1))


if __name__ == "__main__":
    main()
