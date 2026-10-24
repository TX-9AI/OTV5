"""
analysis/second_order.py  v4.1
v4.1  2026-10-03  OTV4TEST r212 (DER.2) — derive_for_symbol also returns WHAT IT DIFFERENCED: iv (the newest clean sample's
      volatility), dt_seconds and d_vol of the pair charm and vanna were measured on. surface_series has
      carried those three columns NULL on every row (1.89M on this box) because nothing handed them over.
      No measurement changes; None stays None.
CHARM and VANNA from the greeks series. Tier 4 of docs/DERIVED_STORES.md.

v4.0  2026-08-22  Built with the manifold.

    charm = dDelta / dt        (per day)
    vanna = dDelta / dVol      (per 1.00 of IV)

🔴 OPERATOR: "absolutely indispensable." For 0DTE, CHARM DOMINATES THE
AFTERNOON — it is the mechanism behind pin. A 0DTE book that cannot compute
charm is ASSERTING pin risk rather than measuring it.

⚠️ NEITHER WAS COMPUTABLE BEFORE THE MANIFOLD, and not because nobody wrote the
maths: `chain_marks` is PRIMARY KEY (streamer_symbol), last-write-wins, so ~250
chain symbols ticking all session each overwrote ONE row. Both of these are
derivatives of delta OVER A SERIES. With one row there is no series and no
derivative. The greeks_series table is what makes this file possible.

⚠️ CONTRIBUTOR, NEVER A GATE. Operator's ruling: derived values inform, they
never authorise. Every function here returns None rather than raising, and a
None means "not measurable from what we have" — NEVER 0.0. A charm of zero is a
real and meaningful reading (delta is stable); a charm that could not be
computed is the absence of a reading. Conflating them is the VW.1 failure.

⚠️ FINITE DIFFERENCE, NOT A MODEL. We do not price options here. We measure how
the vendor's own delta moved against time and against the vendor's own IV. That
keeps this honest: it reports what the surface DID, not what a model says it
should have done.
"""

from __future__ import annotations

import logging
from typing import Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# A sample pair closer than this in time gives a noisy denominator: dividing a
# delta wobble by a fraction of a second manufactures enormous charm.
MIN_DT_SECONDS = 20.0

# Below this IV change, vanna's denominator is measuring quantisation rather
# than a move in volatility.
MIN_D_VOL = 0.0005

SECONDS_PER_DAY = 86400.0


def _pair(rows: Sequence[Tuple[float, Optional[float], Optional[float]]]):
    """Newest and the newest sample far enough back to be a real denominator.

    rows: (ts_epoch, delta, volatility), ANY order. Returns (new, old) or None.
    """
    clean = [r for r in rows
             if r[0] is not None and r[1] is not None]
    if len(clean) < 2:
        return None
    clean.sort(key=lambda r: r[0])
    new = clean[-1]
    for old in reversed(clean[:-1]):
        if new[0] - old[0] >= MIN_DT_SECONDS:
            return new, old
    return None


def charm(rows) -> Optional[float]:
    """dDelta/dt per DAY. None when not measurable — never 0.0 as a fallback."""
    p = _pair(rows)
    if p is None:
        return None
    new, old = p
    dt = new[0] - old[0]
    if dt <= 0:
        return None
    try:
        return ((new[1] - old[1]) / dt) * SECONDS_PER_DAY
    except (TypeError, ValueError):
        return None


def vanna(rows) -> Optional[float]:
    """dDelta/dVol per 1.00 of IV. None when IV did not meaningfully move.

    ⚠️ A FLAT IV IS NOT A VANNA OF ZERO. If volatility did not move, this
    measurement has no denominator and the honest answer is "unknown" — which
    is why the guard returns None. Returning 0.0 would assert that delta is
    insensitive to volatility, a completely different and much stronger claim.
    """
    p = _pair(rows)
    if p is None:
        return None
    new, old = p
    if new[2] is None or old[2] is None:
        return None
    d_vol = new[2] - old[2]
    if abs(d_vol) < MIN_D_VOL:
        return None
    try:
        return (new[1] - old[1]) / d_vol
    except (TypeError, ValueError):
        return None


def iv_slope(by_strike) -> Optional[float]:
    """Smile slope: dIV/dStrike across the chain at one instant.

    by_strike: iterable of (strike, iv). None if fewer than two usable points.
    """
    pts = sorted((float(k), float(v)) for k, v in by_strike
                 if k is not None and v is not None)
    if len(pts) < 2:
        return None
    lo, hi = pts[0], pts[-1]
    dk = hi[0] - lo[0]
    if dk <= 0:
        return None
    return (hi[1] - lo[1]) / dk


def derive_for_symbol(feed_conn, symbol: str, lookback_s: float = 900.0):
    """Read greeks_series and return per-strike second-order rows.

    Returns a list of dicts; an empty list means "nothing measurable yet",
    which is a normal state early in a session and NOT an error.

    ⚠️ READS THE SERIES, DOES NOT RECOMPUTE IT. The greeks are the vendor's.
    We only difference them.
    """
    out = []
    try:
        import time as _t
        since = _t.time() - lookback_s
        cur = feed_conn.execute(
            "SELECT streamer_symbol, ts_epoch, delta, volatility"
            " FROM greeks_series WHERE ts_epoch >= ? ORDER BY streamer_symbol",
            (since,))
        buckets = {}
        for sym, ts, d, v in cur:
            buckets.setdefault(sym, []).append((ts, d, v))
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("second-order read failed: %s — no charm/vanna this "
                       "cycle; the raw series is unaffected", exc)
        return out

    for sym, rows in buckets.items():
        c, v = charm(rows), vanna(rows)
        if c is None and v is None:
            continue                     # nothing measurable — record nothing
        # r212 — the pair the two numbers above were measured on, handed over as measured
        iv = dt = dv = None
        p = _pair(rows)
        if p is not None:
            new, old = p
            iv = new[2]
            dt = new[0] - old[0]
            dv = (new[2] - old[2]) if (new[2] is not None and old[2] is not None) else None
        out.append({"streamer_symbol": sym, "charm": c, "vanna": v,
                    "samples": len(rows), "iv": iv, "dt_seconds": dt, "d_vol": dv})
    return out
