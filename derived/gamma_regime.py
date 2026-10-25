"""
derived/gamma_regime.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.1  2026-10-24  CD.2 — level() and series() judge a surface row by quote_ts (the newest quote behind it - market
      time, surface.py v4.3), not by ts_epoch (write time). The 300 s bound is unchanged in size; it now measures the
      age of the QUOTES. A row with no quote_ts is never served (fail closed). The operator, 2026-10-24: approved.
v1.0  2026-09-16  OTV4TEST r31 (BFLY.7) — THE DEALER-GAMMA REGIME AS A
      CONTINUOUS RAMP INPUT, RECORDED AND APPLIED AT ZERO WEIGHT.

WHAT THIS IS FOR, AND THE ONE MEASUREMENT THAT ARGUES FOR IT.
The butterfly is a bet that dealer gamma PINS price. It already reads the pin
STRIKE, the CONCENTRATION at that strike, the VWAP band (BFLY.5) and EM reach.
It has never read whether the pinning REGIME exists or is collapsing.

Measured on this box 2026-09-16, and the two numbers disagree for six hours,
which is the whole argument that this is a different axis and not another vote:

    pin concentration (what the fly reads)   0.06 - 0.17   NEUTRAL, weak all day
    chain net gamma   (what it did not)      +71M -> +123M strongly pinning

Then at 15:00 ET net gamma crossed ZERO — a -129M swing in fifteen minutes —
and QQQ went 709.65 -> 700.00 in the following twenty. The fly's protection is a
PREMIUM stop, which prices the damage after the tent is left; the regime crossing
zero is the CAUSE, and it is observable first.

🔴 SUMMING `surface_series.gex` IS WRONG, AND I DID IT ONCE BEFORE CHECKING.
`derived/surface.py:133` reads `net_gex` off the GEXSnapshot — the CHAIN TOTAL —
and writes that same value onto EVERY strike row (195 of them on 2026-09-16).
So one row per timestamp IS the whole reading, and a `SUM(gex)` multiplies it by
the strike count. The first pass at this measurement reported +13.8B where the
figure was +71M. The sign and the zero crossing survive a constant multiple, so
the finding held, but the description did not.
⚠️ CONSEQUENCE, RECORDED RATHER THAN WORKED AROUND: per-strike GEX is NEVER
PERSISTED. The strategies read it live from the snapshot, so nothing is broken
today, but no post-hoc study of pin STRUCTURE is possible from this table or
from the warehouse. A gamma FLIP LEVEL (the spot where cumulative GEX crosses
zero) cannot be computed here — only the chain net through time. Filed BFLY.8.

SIGN CONVENTION IS THE REPO'S OWN, NOT MINE — `data/gex_data.py:61`:
    "net_gex_total — sum across all strikes. Positive = pinning, negative = trending"

🔑 THIS SHIPS AT ZERO WEIGHT (WORKING_AGREEMENT §31, §39.2).
`GAMMA_RAMP_WEIGHT` defaults to 0.0, so `ramp()` returns exactly 1.0 and NOTHING
changes size. The score and the multiplier it WOULD have applied are stamped on
every plan row as anchors, so the counterfactual accumulates against fires,
DECLINEs and HOLDs alike. Turning it on is one constant, after the corpus rules.
⚠️ AND THE OPERATOR'S STANDING PREFERENCE IS A RAMP, NOT A GATE (2026-09-16):
"I'm not typically looking for gates unless there is a very strong case for a
block, I would almost always prefer a ramp in almost all cases." So `ramp()` is
continuous and its FLOOR is deliberately non-zero — a weak regime makes the
trade SMALLER, never absent, and a trade that still fires keeps producing data.

GATE CATEGORIES (§36) — for when the weight is ever raised:
    GAMMA_RAMP_WEIGHT   SELECTION   — a size preference, relaxable
    GAMMA_RAMP_FLOOR    SELECTION
    GAMMA_RAMP_CEIL     SELECTION
    GAMMA_SCALE_M       SELECTION   — the normaliser, a declared prior
Nothing here is FOUNDATIONAL or FEASIBILITY: at zero weight it decides nothing,
and at any weight it scales rather than refuses.

⚠️ THE SLOPE IS NOISY AND SAYS SO. Consecutive 15-minute readings on 2026-09-16
ran +33.6, -28.1, +21.0 BEFORE the real break. A raw slope would whipsaw, so
`slope()` is a least-squares fit over a window rather than a difference of two
points, and callers are expected to treat the LEVEL and its ZERO CROSSING as the
firm reading and the slope as the soft one.

Every read is best-effort and returns None when the store, table or row is
absent (the `derived/anchors.py` contract): a None is a fact about coverage, not
a failure, and nothing here raises into a plan.
"""
from __future__ import annotations

import logging
import time
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

try:                                                            # pragma: no cover
    import config as _cfg
except Exception:                                               # noqa: BLE001
    _cfg = None


def _c(name: str, default: float) -> float:
    return float(getattr(_cfg, name, default)) if _cfg is not None else default


# ── declared priors (category 1: a baseline so there is a starting point) ──
# Normaliser. 2026-09-16 ran +71M..+123M positive and -20M..-106M negative, so
# 100M puts a strong regime near tanh(1) ~ 0.76 and leaves room either side.
GAMMA_SCALE_M = _c("GAMMA_SCALE_M", 100.0)
# 🔴 ZERO. The ramp is computed, recorded, and APPLIED AT NOTHING (§31).
GAMMA_RAMP_WEIGHT = _c("GAMMA_RAMP_WEIGHT", 0.0)
GAMMA_RAMP_FLOOR = _c("GAMMA_RAMP_FLOOR", 0.50)
GAMMA_RAMP_CEIL = _c("GAMMA_RAMP_CEIL", 1.50)
SLOPE_WINDOW_S = _c("GAMMA_SLOPE_WINDOW_S", 900.0)      # 15 min
SLOPE_MIN_POINTS = 4


def _store():
    try:
        from data.derived_store import get_derived_store
        return get_derived_store()
    except Exception:                                           # noqa: BLE001
        return None


def _sym() -> str:
    try:
        from config import INSTRUMENT
        return str(INSTRUMENT)
    except Exception:                                           # noqa: BLE001
        return ""


def _q(sql, args=()):
    st = _store()
    if st is None:
        return []
    try:
        with st._lock:
            return st.conn.execute(sql, args).fetchall()
    except Exception:                                           # noqa: BLE001
        return []


def level(max_age_s: float = 300.0, now: Optional[float] = None) -> Optional[float]:
    """Chain net gamma in MILLIONS, signed. + pins, - trends. None if stale/absent.

    ⚠️ ONE ROW, NOT A SUM — see the module header. Every strike row at a given
    timestamp carries the same chain-wide value.
    ⚠️ FAILS CLOSED ON STALENESS rather than returning an old regime: the engine
    keeps the last row after the close, and a regime is a statement about NOW.
    """
    now = time.time() if now is None else float(now)
    rows = _q("SELECT quote_ts, gex FROM surface_series WHERE symbol=? AND gex IS NOT NULL "
              "AND quote_ts IS NOT NULL ORDER BY quote_ts DESC LIMIT 1", (_sym(),))      # CD.2: market time
    if not rows:
        return None
    ts, g = rows[0]
    if g is None or ts is None:
        return None
    if (now - float(ts)) > float(max_age_s):
        return None
    return float(g) / 1e6


def series(secs: float = SLOPE_WINDOW_S, now: Optional[float] = None) -> List[Tuple[float, float]]:
    """[(ts, level_in_millions)] over the trailing window, one point per timestamp."""
    now = time.time() if now is None else float(now)
    rows = _q("SELECT DISTINCT quote_ts, gex FROM surface_series WHERE symbol=? "
              "AND gex IS NOT NULL AND quote_ts IS NOT NULL AND quote_ts >= ? ORDER BY quote_ts",
              (_sym(), now - float(secs)))                      # CD.2: the quotes' time, not the write time
    return [(float(t), float(g) / 1e6) for t, g in rows if t is not None and g is not None]


def slope(secs: float = SLOPE_WINDOW_S, now: Optional[float] = None) -> Optional[float]:
    """Least-squares change in net gamma (millions) PER MINUTE over the window.

    ⚠️ A FIT, NOT A DIFFERENCE OF TWO POINTS. The header records why: consecutive
    15-minute deltas on 2026-09-16 ran +33.6 / -28.1 / +21.0 before the real
    break, so a two-point read is mostly noise.
    """
    pts = series(secs, now)
    if len(pts) < SLOPE_MIN_POINTS:
        return None
    t0 = pts[0][0]
    xs = [(t - t0) / 60.0 for t, _ in pts]
    ys = [g for _, g in pts]
    n = float(len(pts))
    mx = sum(xs) / n
    my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def _tanh(x: float) -> float:
    # stdlib math.tanh, guarded for overflow on absurd inputs
    import math
    if x > 20:
        return 1.0
    if x < -20:
        return -1.0
    return math.tanh(x)


def regime(now: Optional[float] = None) -> Optional[float]:
    """The regime score in [-1, +1]. + pinning, - trending. None when unreadable.

    `tanh(level / GAMMA_SCALE_M)` — bounded, smooth, and monotone in the level,
    so a ramp built on it cannot step. The ZERO CROSSING is exact regardless of
    the scale: tanh(0) == 0, so the normaliser never moves the regime boundary,
    only how fast the score saturates away from it.
    """
    lv = level(now=now)
    if lv is None:
        return None
    return _tanh(lv / GAMMA_SCALE_M) if GAMMA_SCALE_M else None


def ramp(score: Optional[float],
         weight: Optional[float] = None,
         floor: Optional[float] = None,
         ceil: Optional[float] = None) -> float:
    """The size multiplier. CONTINUOUS, clamped, and 1.0 when unreadable.

    🔴 AT THE SHIPPED `GAMMA_RAMP_WEIGHT` OF 0.0 THIS RETURNS EXACTLY 1.0 FOR
    EVERY INPUT. That is the point: the score rides every plan row while the
    book trades exactly as it did before (§31 — a number that has never been
    tested against P&L does not size anything).

    The FLOOR is non-zero by the operator's ruling: a weak regime makes the
    trade smaller, never absent.
    """
    w = GAMMA_RAMP_WEIGHT if weight is None else float(weight)
    lo = GAMMA_RAMP_FLOOR if floor is None else float(floor)
    hi = GAMMA_RAMP_CEIL if ceil is None else float(ceil)
    if score is None or w == 0.0:
        return 1.0
    return max(lo, min(hi, 1.0 + w * float(score)))


def read(now: Optional[float] = None) -> dict:
    """Everything a caller wants, in one pass, for stamping on a plan row.

    Keys are stable because they become `anchor_*` column names in the ledger:
      gamma_net_m     the chain net gamma in millions, signed
      gamma_regime    the [-1,+1] score
      gamma_slope_m   millions per minute, least-squares over the window
      gamma_ramp      the multiplier it WOULD apply (1.0 while the weight is 0)
    """
    lv = level(now=now)
    sc = None if lv is None else _tanh(lv / GAMMA_SCALE_M) if GAMMA_SCALE_M else None
    return {
        "gamma_net_m": lv,
        "gamma_regime": sc,
        "gamma_slope_m": slope(now=now),
        "gamma_ramp": ramp(sc),
    }
