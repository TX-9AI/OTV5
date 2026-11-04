"""
analysis/opening_tape.py  v5.0
v5.0  2026-11-04  OTV5 r74 (ORP.3) — IS TODAY'S OPENING-RANGE TAPE COMPLETE? ONE ANSWER FOR THE RANGE AND THE FEED.
      2026-11-02 the AMZN feed was refused from 09:31 to 10:55 ET. It held the 09:30 1m and 5m bars as they stood when
      the socket dropped (H 244.43 L 243.02, 0.76M shares; the true 5m bar is H 246.39 L 242.28, 1.94M), and at
      10:56:51 analysis/get_orb_range.py ESTABLISHED the range from that lone 5m row (its fallback when the five 1m
      bars are not all on the feed). Hunt traded against 243.02-244.43 all afternoon. The rule from here: the range
      is the five 1m bars 09:30-09:34 (the official print, ORP.1), and they are complete only when all five are
      present AND, when today's 09:30 5m row exists, its high and low equal theirs (a partial capture leaves the two
      frames disagreeing; on clean TastyTrade history, 90 symbol-days 10-26..11-02, every pair agreed to the cent).
      Pure: no I/O, no clock. get_orb_range asks it before it establishes; data/candle_feed asks it before it
      re-pulls. Gate tests/check_orb_incomplete.py.
"""
from typing import Dict, Optional, Tuple

OPEN_MINUTES = (30, 31, 32, 33, 34)      # the five 1m bars of the 09:30 ET opening range
TOL_ABS = 0.011                          # a cent, with float slack
TOL_REL = 2e-6                           # SPX-sized prices: 2 ppm (~0.013 at 6,500)


def _tol(px: float) -> float:
    return max(TOL_ABS, abs(px) * TOL_REL)


def problem(bars_1m: Dict[int, Tuple[float, float]],
            bar_5m: Optional[Tuple[float, float]] = None) -> Optional[str]:
    """None when today's opening tape is complete, else why not.

    bars_1m: {minute: (high, low)} for today's 09:30-09:34 1m bars that are on the feed (any other minute ignored).
    bar_5m:  (high, low) of today's 09:30 5m row, or None when there is none (the five 1m bars then stand alone).
    """
    try:
        missing = [m for m in OPEN_MINUTES if m not in bars_1m]
        if missing:
            return "1m bar(s) missing at " + ", ".join("09:%02d" % m for m in missing)
        hi = max(float(bars_1m[m][0]) for m in OPEN_MINUTES)
        lo = min(float(bars_1m[m][1]) for m in OPEN_MINUTES)
        if not hi > lo > 0:
            return "degenerate 1m opening bars (high %.4f, low %.4f)" % (hi, lo)
        if bar_5m is not None:
            h5, l5 = float(bar_5m[0]), float(bar_5m[1])
            if abs(h5 - hi) > _tol(hi) or abs(l5 - lo) > _tol(lo):
                return ("the 09:30 5m bar (H %.2f L %.2f) disagrees with its five 1m bars (H %.2f L %.2f) - "
                        "a partial capture" % (h5, l5, hi, lo))
        return None
    except Exception as exc:                                   # noqa: BLE001
        return "opening tape unreadable (%s)" % type(exc).__name__


def print_of(bars_1m: Dict[int, Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    """(high, low) of the five 1m bars, or None unless all five are there."""
    try:
        if any(m not in bars_1m for m in OPEN_MINUTES):
            return None
        hi = max(float(bars_1m[m][0]) for m in OPEN_MINUTES)
        lo = min(float(bars_1m[m][1]) for m in OPEN_MINUTES)
        return (hi, lo) if hi > lo > 0 else None
    except Exception:                                          # noqa: BLE001
        return None
