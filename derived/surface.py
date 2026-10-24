"""
derived/surface.py  v4.3
v4.3  2026-10-24  CD.2 — every row carries quote_ts, the receive stamp of the NEWEST greeks quote in the window it was
      derived from (its market time). The readers (gamma_regime.level, anchors._surface_row, main's charm/vanna port)
      judge a row by it, not by when it was written, so a stale or seeded row is never served as current.
v4.2  2026-10-03  OTV4TEST r215 (DER.3) — gamma_flow IS WRITTEN: the change in a strike's NET GEX since this engine's previous
      reading. docs/DERIVED_STORES.md named the idea ("with a series, gamma flow is measurable - where the wall
      built and when it moved") and no code ever computed it; r212 left it empty and wrongly said no
      definition existed. The operator, 2026-10-03, on the definition proposed (the change in net gamma at
      each strike since the previous reading): "Concur, populate it". The first reading after a start has no
      previous one and writes NULL; a strike absent from either snapshot writes NULL. Never 0 by default.
v4.1  2026-10-03  OTV4TEST r212 (DER.2) — iv, dt_seconds AND d_vol ARE WRITTEN. They were the literal None on every row since
      this file was written (the 10-03 audit, B7; BACKLOG DER.1 said "cause NOT investigated" - this is the
      cause). They come from analysis/second_order, per contract, as measured. gamma_flow STAYS NULL: no
      definition of it exists in this repo or its docs, and a column filled with an invented quantity is
      worse than an empty one. The operator, 2026-10-03: "Gather as much as is available".
Owns `surface_series`. Tier 4 — second-order; impossible without a series.

v4.0  2026-08-22  See docs/DERIVED_STORES.md.

🔴 CHARM and VANNA — operator, 2026-08-22: "absolutely indispensable."

    charm = dDelta/dt      vanna = dDelta/dVol

⚠️ NEITHER WAS COMPUTABLE BEFORE THE MANIFOLD, and not because the maths was
missing. `chain_marks` is PRIMARY KEY (streamer_symbol) — last-write-wins — so
~250 chain symbols ticking all session each overwrote ONE row. Both are
derivatives of delta OVER A SERIES; with one row there is no series and no
derivative. `greeks_series` is what makes this file possible at all.

🔴 FOR 0DTE THIS IS THE AFTERNOON, NOT AN ENHANCEMENT. Charm dominates the
final hours of an expiring contract — it is the mechanism behind pin. A 0DTE
book that cannot compute charm is ASSERTING pin risk rather than measuring it.

⚠️ WE MEASURE, WE DO NOT MODEL. These are finite differences on the VENDOR's
own delta against time and against the VENDOR's own IV. No pricing model is
involved, so the numbers report what the surface DID rather than what a model
says it should have done.

⚠️ CHARM/VANNA/GEX ARE UNIVERSAL PORTS — operator: they must contribute to
every strategy where they could meaningfully contribute. So they are derived
ONCE here and offered to all engines, never recomputed per strategy. Two
consumers computing the same quantity at different points in a tick can
legitimately disagree, and that is a bug nobody would ever find.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from derived.base import DerivedEngine

logger = logging.getLogger(__name__)

LOOKBACK_S = 900.0        # 15 min of greek history is plenty for a difference


def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _strike_of(streamer_symbol: str) -> Optional[float]:
    """Strike out of an OCC-ish streamer symbol. None when unparseable.

    ⚠️ NONE, NOT A GUESS. A mis-parsed strike would attach a real charm to the
    WRONG contract, which is worse than not recording it — the study would
    treat it as evidence.
    """
    try:
        s = streamer_symbol.lstrip(".")
        i = len(s) - 1
        while i >= 0 and (s[i].isdigit() or s[i] == "."):
            i -= 1
        if i < 0 or i == len(s) - 1:
            return None
        if s[i] not in ("C", "P"):
            return None
        return float(s[i + 1:])
    except Exception:                                           # noqa: BLE001
        return None


class SurfaceEngine(DerivedEngine):
    name = "surface"
    table = "surface_series"
    # Reads a 15-min window over ~250 symbols; every 30s is far finer than the
    # rate at which second-order greeks meaningfully move.
    min_interval_s = 30.0

    def __init__(self, store=None, symbol: str = "", feed_conn=None):
        super().__init__(store)
        self.symbol = symbol
        self._feed_conn = feed_conn

    def _conn(self, ctx: dict):
        if self._feed_conn is not None:
            return self._feed_conn
        try:
            import sqlite3
            from data.candle_feed import feed_db_path
            # Read-only: this engine must never contend with the feed writer.
            self._feed_conn = sqlite3.connect(
                f"file:{feed_db_path()}?mode=ro", uri=True, check_same_thread=False)
        except Exception as exc:                                # noqa: BLE001
            logger.debug("surface: no feed connection: %s", exc)
            return None
        return self._feed_conn

    def derive(self, ctx: dict) -> int:
        store = self._store
        conn = self._conn(ctx)
        if store is None or conn is None:
            return 0
        sym = self.symbol or ctx.get("symbol") or ""
        if not sym:
            return 0

        from analysis.second_order import derive_for_symbol, iv_slope

        measured = derive_for_symbol(conn, sym, LOOKBACK_S)
        if not measured:
            # Normal early in a session: not enough series yet to difference.
            # Recording nothing is correct — a row of zeros would be a lie.
            return 0

        now = time.time()
        expiry = str(ctx.get("expiry") or "")
        # 🔴 ctx["gex"] IS A GEXSnapshot OBJECT, NOT A NUMBER (r140).
        # ⚠️ `_f(ctx.get("gex"))` coerced an object to float and got None, so
        # surface_series.gex has been NULL on every row ever written — 1.49M
        # rows across the fleet — and the dashboard prints "GEX=NoneM".
        # I attributed this to the r133 chain-ordering bug and said r133 fixed
        # it. r133 was necessary but NOT sufficient: the chain now arrives, the
        # snapshot is computed, and the read shape was wrong the whole time.
        # ⚠️ SAME FAMILY AS ctm.all(), bars_ago AND open_interest — a shape I
        # assumed rather than read. Fourth today. The scalar wanted here is
        # `net_gex`; the rest of the snapshot has its own columns.
        _gx = ctx.get("gex")
        gex = _f(getattr(_gx, "net_gex", None) if _gx is not None else None)

        # r215 — GAMMA FLOW: each strike's net GEX now, against this engine's previous
        # reading of the same strike. No previous reading (the first tick after a start,
        # or a tick with no snapshot) is NULL, never zero.
        _now_k = {}
        try:
            for _s in (getattr(_gx, "strikes", None) or []):
                _k, _n = _f(getattr(_s, "strike", None)), _f(getattr(_s, "net_gex", None))
                if _k is not None and _n is not None:
                    _now_k[round(_k, 4)] = _n
        except Exception:                                       # noqa: BLE001
            _now_k = {}
        _prev_k = getattr(self, "_prev_gex_by_strike", None) or {}

        def _flow(k):
            a, b = _now_k.get(round(k, 4)), _prev_k.get(round(k, 4))
            return (a - b) if (a is not None and b is not None) else None

        # Smile slope across the chain at this instant, from the same window.
        try:
            cur = conn.execute(
                "SELECT streamer_symbol, volatility FROM greeks_series"
                " WHERE ts_epoch >= ? ", (now - 120.0,))
            pts = []
            for s_sym, iv in cur:
                k = _strike_of(s_sym)
                if k is not None and iv is not None:
                    pts.append((k, iv))
            slope = iv_slope(pts)
        except Exception:                                       # noqa: BLE001
            slope = None

        # CD.2 — the market time of this reading: the newest quote behind it
        try:
            quote_ts = _f(conn.execute("SELECT MAX(ts_epoch) FROM greeks_series WHERE ts_epoch >= ?",
                                       (now - LOOKBACK_S,)).fetchone()[0])
        except Exception:                                       # noqa: BLE001
            quote_ts = None
        rows = []
        for m in measured:
            k = _strike_of(m["streamer_symbol"])
            if k is None:
                continue
            rows.append((sym, now, k, expiry,
                         _f(m.get("charm")), _f(m.get("vanna")),
                         gex, _flow(k),             # r215: the strike's net-GEX change since the last reading
                         _f(m.get("iv")), slope, _f(m.get("dt_seconds")), _f(m.get("d_vol")),
                         quote_ts))                 # CD.2
        if _now_k:
            self._prev_gex_by_strike = _now_k
        return store.append_surface(rows)
