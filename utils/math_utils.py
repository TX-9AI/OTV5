"""
utils/math_utils.py  v4.2
v4.2  2026-10-03  OTV4TEST r221 (UTIL.1) — find_fvgs: the one Fair Value Gap finder (structure_analyzer and exit_engine each carried the same loop).
Shared numeric helpers.

v4.1  2026-09-25  OTV4TEST r137 — THE STRIKE HELPERS TRUNCATED A FRACTIONAL INCREMENT.
      `int(round(price / increment) * increment)` is right for 1 and 5 and WRONG
      for 0.5: SOFI at 16.70 rounds to the 16.5 strike and `int()` then made it
      16 - a strike that exists, but not the one asked for, silently. Never hit,
      because every increment was whole until SOFI/AAL (0.5) joined
      STRIKE_INCREMENTS. Now the result is snapped to the increment and returned
      as an INT when it is whole - so every existing symbol gets exactly what it
      got before (int type included: no "736.0" can reach a label) - and as a
      float otherwise. check_low_price_symbols pins both halves.
      Also: a duplicate `import math` ABOVE this docstring is removed (the real
      import is below) - it made the docstring not the module docstring and hid
      this changelog from the lander's header check, which refused r137 once.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

utils/math_utils.py — Math helpers for options trading.
Includes ORB calculations, contract sizing, strike rounding, P&L.
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
"""

import math
from typing import Optional
import numpy as np
import pandas as pd


# ─── STRIKE UTILITIES ─────────────────────────────────────────────────────────

def _strike(v: float):
    """r137 — an int when the strike is whole (unchanged for 1 / 5 increments),
    otherwise the value on the cent grid (0.5 increments)."""
    v = round(v, 4)
    return int(v) if float(v).is_integer() else round(v, 2)


def round_to_strike(price: float, increment: float):
    """Round price to nearest valid strike increment."""
    return _strike(round(price / increment) * increment)


def floor_to_strike(price: float, increment: float):
    """Round DOWN to nearest valid strike (for OTM put selection)."""
    return _strike(math.floor(price / increment) * increment)


def ceil_to_strike(price: float, increment: float):
    """Round UP to nearest valid strike (for OTM call selection)."""
    return _strike(math.ceil(price / increment) * increment)


# ─── ORB MATH ─────────────────────────────────────────────────────────────────

def orb_width(orb_high: float, orb_low: float) -> float:
    """Width of the opening range."""
    return orb_high - orb_low


def orb_breakout_target(orb_high: float, orb_low: float, direction: str) -> float:
    """
    Project the 100% TP from an ORB breakout.
    direction: 'long' (price broke above) or 'short' (price broke below)
    """
    width = orb_width(orb_high, orb_low)
    if direction == "long":
        return orb_high + width
    else:
        return orb_low - width


def orb_strike_selection(orb_high: float, orb_low: float,
                          direction: str, strike_increment: int) -> int:
    """
    Select the option strike based on ORB width projection.

    For a downside break: target = orb_low - orb_width
    → buy put at that strike (rounded to nearest increment)

    For an upside break: target = orb_high + orb_width
    → buy call at that strike (rounded to nearest increment)

    Example: QQQ ORB 599–608 (width=9), break below 599
    → target = 599 - 9 = 590 → buy 590 puts
    """
    target = orb_breakout_target(orb_high, orb_low, direction)
    return round_to_strike(target, strike_increment)


# ─── CONTRACT SIZING ──────────────────────────────────────────────────────────

def contracts_from_risk(risk_usd: float, option_cost_per_contract: float,
                         grade_multiplier: float = 1.0) -> int:
    """
    Calculate number of whole contracts to buy.

    contracts = floor(risk_usd × grade_multiplier / cost_per_contract)

    Args:
        risk_usd:               Fixed dollar risk from config
        option_cost_per_contract: Net debit × 100 (contract multiplier)
        grade_multiplier:       From setup grade (A=1.5, B=1.0, C=0.5)

    Returns:
        Whole number of contracts (minimum 1 if affordable)
    """
    if option_cost_per_contract <= 0:
        return 0
    adjusted_risk = risk_usd * grade_multiplier
    count = int(math.floor(adjusted_risk / option_cost_per_contract))
    return max(count, 0)


def option_cost_per_contract(premium: float, multiplier: int = 100) -> float:
    """Cost to buy one options contract."""
    return premium * multiplier


# ─── P&L CALCULATIONS ─────────────────────────────────────────────────────────

def option_pnl_pct(entry_premium: float, current_premium: float) -> float:
    """Current P&L as percentage of entry premium."""
    if entry_premium <= 0:
        return 0.0
    return (current_premium - entry_premium) / entry_premium


def option_pnl_usd(entry_premium: float, current_premium: float,
                    contracts: int, multiplier: int = 100) -> float:
    """Unrealized P&L in USD."""
    return (current_premium - entry_premium) * contracts * multiplier


def butterfly_max_profit(long_wing_premium: float, short_body_premium: float,
                          multiplier: int = 100) -> float:
    """
    Max profit for a debit butterfly:
    = (short body premium × 2 - long wing premium × 2) × multiplier
    Simplified: wing_width - net_debit
    """
    net_debit = long_wing_premium - (2 * short_body_premium)
    # Max profit = wing_width (in strike $) - net_debit, expressed as $ per point
    # We compute this from the actual prices in butterfly_strategy.py
    return net_debit * multiplier   # placeholder — override in strategy


# ─── TECHNICAL INDICATORS ─────────────────────────────────────────────────────

def ema_series(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def atr_series(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high  = df["high"]
    low   = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def bb_bands(series: pd.Series, period: int = 20, std: float = 2.0):
    """Returns (upper, middle, lower)."""
    mid   = series.rolling(period).mean()
    sigma = series.rolling(period).std()
    return (mid + std * sigma), mid, (mid - std * sigma)


def bollinger_bands(series: pd.Series, period: int = 20, std: float = 2.0):
    """Alias for bb_bands — returns (upper, middle, lower)."""
    return bb_bands(series, period, std)


def bb_width(upper: float, lower: float, middle: float) -> float:
    """Bollinger Band width as fraction of middle band."""
    if middle == 0:
        return 0.0
    return (upper - lower) / middle


def bb_width_percentile(widths: list, current_width: float,
                         lookback: int = 50) -> float:
    """
    Return the percentile (0.0–1.0) of current_width within recent history.
    Used to detect squeeze (low percentile) vs expansion (high percentile).
    """
    if not widths or len(widths) < 2:
        return 0.5
    recent = widths[-lookback:] if len(widths) >= lookback else widths
    below  = sum(1 for w in recent if w <= current_width)
    return below / len(recent)


def within_pct(a: float, b: float, pct: float) -> bool:
    """True if a and b are within pct of each other."""
    if a == 0:
        return False
    return abs(a - b) / a <= pct


def adx_series(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute ADX series."""
    high  = df["high"]
    low   = df["low"]
    close = df["close"]

    plus_dm  = high.diff()
    minus_dm = -low.diff()
    plus_dm  = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(span=period, adjust=False).mean()
    di_plus  = 100 * plus_dm.ewm(span=period, adjust=False).mean() / atr
    di_minus = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr
    dx = (abs(di_plus - di_minus) / (di_plus + di_minus + 1e-10)) * 100
    adx = dx.ewm(span=period, adjust=False).mean()
    return adx


def current_adx(df: pd.DataFrame, period: int = 14) -> float:
    """Return the most recent ADX value as a float."""
    try:
        s = adx_series(df, period)
        if s.empty:
            return 0.0
        return float(s.iloc[-1])
    except Exception:
        return 0.0


def find_swing_highs(prices: list, lookback: int = 10):
    """
    Identify swing highs in a list of prices.
    A swing high is a local maximum within ±lookback bars.

    Args:
        prices:   List of price values (e.g. df["high"].tolist())
        lookback: Bars on each side to check

    Yields:
        (index, price) tuples for each swing high found
    """
    n = len(prices)
    for i in range(lookback, n - lookback):
        window = prices[i - lookback: i + lookback + 1]
        if prices[i] == max(window):
            yield i, prices[i]


def find_swing_lows(prices: list, lookback: int = 10):
    """
    Identify swing lows in a list of prices.
    A swing low is a local minimum within ±lookback bars.

    Args:
        prices:   List of price values (e.g. df["low"].tolist())
        lookback: Bars on each side to check

    Yields:
        (index, price) tuples for each swing low found
    """
    n = len(prices)
    for i in range(lookback, n - lookback):
        window = prices[i - lookback: i + lookback + 1]
        if prices[i] == min(window):
            yield i, prices[i]

def safe_float(v, default=None):
    """A FINITE float, or `default`. The guard every numeric gate needs.

    v4.0, 2026-08-20, from the stress test.

    ⚠️ NaN IS THE DANGEROUS INPUT AND IT INVERTS VETOES SILENTLY. **Every
    comparison against NaN is False**, so a gate written as
        `if atr < FLOOR: return None`
    does NOT refuse on NaN - it falls through and trades. The stress test found
    `target_delta(nan)` returning a strike in exactly the tape the floor exists
    to exclude: below 0.05% ATR the required move was reached on **0% of 5,517
    measured bars.** The comment above that function warned about this failure
    and the code had it anyway.

    ⚠️ AND +/-inf IS NOT SAFE EITHER: it passes `< floor` and `> ceiling` tests
    in whichever direction happens to suit, and arithmetic on it produces NaN
    one step later.

    ⚠️ A STRING RAISES ON COMPARISON, and `_safe_strategy` catches the raise and
    logs "no signal" - **so a crashing strategy is indistinguishable from a
    quiet one.** Coercing here turns a hidden crash into an explicit refusal.
    """
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(f):
        return default
    return f


def find_fvgs(df, min_size_pct: float) -> list:
    """Fair Value Gaps (3-candle imbalances) in `df`, in bar order.

    r221 (UTIL.1) — THE ONE FINDER. structure_analyzer and exit_engine each carried
    the same loop. Bullish: bar[i].low > bar[i-2].high; bearish: bar[i].high <
    bar[i-2].low; kept when (top - bottom) / the near edge >= min_size_pct.
    Returns [(top, bottom, size_pct, direction, index), ...] - for each bar the
    bullish gap (if any) then the bearish one, exactly the order both loops built.
    """
    out = []
    if df is None or len(df) < 3:
        return out
    highs, lows = df["high"], df["low"]
    for i in range(2, len(df)):
        gap_bot = float(highs.iloc[i - 2])
        gap_top = float(lows.iloc[i])
        if gap_top > gap_bot:
            size_pct = (gap_top - gap_bot) / gap_bot if gap_bot > 0 else 0
            if size_pct >= min_size_pct:
                out.append((gap_top, gap_bot, size_pct, "bullish", i))
        gap_top2 = float(lows.iloc[i - 2])
        gap_bot2 = float(highs.iloc[i])
        if gap_bot2 < gap_top2:
            size_pct = (gap_top2 - gap_bot2) / gap_top2 if gap_top2 > 0 else 0
            if size_pct >= min_size_pct:
                out.append((gap_top2, gap_bot2, size_pct, "bearish", i))
    return out
