"""
derived/anchors.py  v1.5
v1.5  2026-10-24  CD.2 — EVERY ANCHOR READ JUDGES ITS ROW BY MARKET TIME (the operator, 2026-10-24: seeding any table must be
      harmless). charm_at/vanna_at/gex_at: the newest surface row whose quote_ts is within SURFACE_MAX_AGE_S (120 s);
      a row with no quote_ts is never served. gex_between is RETIRED (returns None): surface_series.gex is the chain-wide
      net on every strike row, so a sum over strikes measured nothing (gamma_regime's own header). vwap() is now
      vwap_now()[0] - the same session-anchor and bar-age test as the decision input, instead of no test. fork_dir()
      reads fork_row(): the frame's newest row, served only while its bar_ts_ms is the frame's latest closed bar (one
      bar of grace), and only built=1 gives a direction - a dead fork's direction is no longer reported.
v1.4  2026-10-03  OTV4TEST r218 (PATH.1) — aggressor_share resolves the feed store through utils.paths: it read two config names that do not exist and fell back to a path that ignored OT_FEED_DB.
v1.3  2026-09-22  OTV4TEST r103 - `nearest_tine` READ A TABLE THAT IS
      GUARANTEED EMPTY AND RETURNED None ON EVERY ROW EVER WRITTEN. It queried
      level_ledger for fork1h/%; r19's clause (1) makes _sources() skip every
      pool flagged `moving` so that a rail NEVER becomes a ledger row. MEASURED:
      0 fork1h rows in level_ledger, 83 in level_event, and
      SweepCreditSpread.anchor_tine_to_level banked 639 rows, all None.
      Repointed at the live projection. NEW `rail_context()` carries the rail
      distance, slope and convergence onto the plan row - ALL NUMERIC, because
      stamp() floats its values and plan_check has no text column, which is
      r99's price_vs_vwap defect in a new costume.
v1.2  2026-09-22  OTV4TEST r94 — BOTH READERS STOP QUERYING A ROW NOBODY WRITES.
      `vwap_now()` AND `vwap()` both pinned `interval='primary'` - the FALLBACK
      row in indicators.derive(), emitted only `if not rows`. r69 repaired the
      per-timeframe loop, the fallback stopped firing, and both readers spent
      TWO DAYS on a dead row. MEASURED: 882 rows each for 5m/15m/1h/1d all
      carrying a VWAP; `primary` last seen 09-20 13:29 ET, the minute r69
      landed; the engine reporting 412 runs and ZERO failures throughout.
      They now read the newest row carrying a VWAP on ANY interval, and
      `vwap_now()` validates the anchor against the 09:30 open.
      I FIXED `vwap_now()` FIRST AND MISSED `vwap()` - the bug moved one
      function down the file - and A4 caught it on the next run.
v1.1  2026-09-13  OTV4TEST r25 — THE VWAP READ WAS DEAD, AND ONE ANCHOR NOW DECIDES.
      🔴 `vwap()` queried interval '1m', which indicator_series has NEVER held —
      the engine writes 'primary' only — so it returned None on every call and
      `anchor_vwap_minus_pin` was null on 723 of 723 of Friday's butterfly rows.
      Re-pointed to 'primary'. ⚠️ THE FIRST ANCHOR PROMOTED TO A DECISION INPUT,
      on the operator's ruling (BFLY.5): `vwap_now()` feeds the butterfly's VWAP
      band. It is a SEPARATE reader because "latest row" is not "now": the
      engine keeps writing the last session's VWAP after the close (Sunday
      evening's rows carry Friday's 715.45, anchored Friday midnight). So it
      returns a value only when the row is anchored at TODAY's midnight ET and
      its bar is fresh; anything else is None with the reason, never a stale
      number. `vwap()` stays record-only and unfiltered.
v1.0  2026-09-09  OTV4TEST r12 — ANCHORS: DERIVATIVES RECORDED ON THE PLAN ROW,
      NEVER DECIDED ON. Operator: *"record in our newly crafted plans, not to
      decide, but to see if they offer fitting anchors we can tie to later."*
      Every plan stamps 3–5 of these on its row every tick as record-only
      checks (verdict None), so an anchor is scored against fires, declines
      AND holds — fire_snapshot alone could only ever see the fires.

      Every read is best-effort and returns None when the store, table or
      row is absent; a None is a fact about coverage, not a failure. Nothing
      here raises into a plan.

      READS (all from stores that already exist):
        charm_at / vanna_at / gex_at (strike)  — surface_series, latest row
        vwap ()                                 — indicator_series (primary), latest
        vwap_now (now)                          — the same, ONLY if today's and fresh
        fork_dir (tf)                           — fork_series, latest built
        nearest_tine (price)                    — level_ledger fork1h/* live
        aggressor_share (level, band, secs)     — prints: buy share of size
                                                  within ±band of level, last N s
        gex_between (lo, hi)                    — surface_series sum in [lo, hi]
        oi_at (strike, chain)                   — from the chain in hand
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


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


# CD.2 — a 0DTE surface describes THIS moment: 4 x the engine's 30 s cadence. The operator, 2026-10-24: approved.
SURFACE_MAX_AGE_S = 120.0


def _surface_row(strike: float, now: Optional[float] = None):
    """The newest surface row at `strike` whose quote_ts (market time) is within SURFACE_MAX_AGE_S; else None."""
    if strike is None:
        return None
    now = time.time() if now is None else float(now)
    rows = _q("SELECT charm, vanna, gex FROM surface_series WHERE symbol=? AND ABS(strike-?)<0.01 "
              "AND quote_ts IS NOT NULL AND quote_ts >= ? ORDER BY quote_ts DESC LIMIT 1",
              (_sym(), float(strike), now - SURFACE_MAX_AGE_S))
    return rows[0] if rows else None


def charm_at(strike, now: Optional[float] = None) -> Optional[float]:
    r = _surface_row(strike, now)
    return float(r[0]) if r and r[0] is not None else None


def vanna_at(strike, now: Optional[float] = None) -> Optional[float]:
    r = _surface_row(strike, now)
    return float(r[1]) if r and r[1] is not None else None


def gex_at(strike, now: Optional[float] = None) -> Optional[float]:
    r = _surface_row(strike, now)
    return float(r[2]) if r and r[2] is not None else None


def gex_between(lo, hi) -> Optional[float]:
    """RETIRED (CD.2): always None. surface_series.gex holds the CHAIN-WIDE net on every strike row (gamma_regime.py's
    header), so summing it across strikes multiplied one number by the strike count and mixed rows from different
    days. Per-strike GEX is not persisted; the anchor is recorded as absent until it is."""
    return None


def vwap() -> Optional[float]:
    """The newest recorded VWAP, whatever interval carried it. No freshness test.

    🔴 r94 — THE SIBLING READER, AND I FIXED `vwap_now()` FIRST AND MISSED THIS
    ONE. Both queried `interval='primary'`, the FALLBACK row that r69's repair
    stopped emitting; correcting one and not the other is §23 exactly — the
    bug moved one function down the file. `check_bfly_vwap_band` A4 caught it
    on the next run, which is the only reason it is a comment and not a third
    silent reader.
    ⚠️ THIS ONE DOES NOT VALIDATE THE ANCHOR OR THE BAR AGE — `vwap_now()` is
    the decision input and fails closed; this is the plain accessor. Anything
    making a TRADING decision uses `vwap_now()`."""
    # CD.2 — the same test as the decision input: today's 09:30 anchor and a bar no older than VWAP_MAX_BAR_AGE_S.
    # A plain accessor with no test served yesterday's VWAP against today's price on a restart.
    return vwap_now()[0]


# Friday 09-11, 1,479 RTH rows: written every 15 s, the bar trailing the write by
# at most 63 s. 180 s is three missed bars — a stalled feed, not a slow tick.
VWAP_MAX_BAR_AGE_S = 180.0


def vwap_now(now: Optional[float] = None,
             max_bar_age_s: float = VWAP_MAX_BAR_AGE_S) -> Tuple[Optional[float], str]:
    """(vwap, why) — the bot's SESSION-OPEN-anchored VWAP for TODAY, or (None, reason).

    A decision input (the butterfly's VWAP band), so it FAILS CLOSED: a missing
    row, a null value, a prior session's anchor or a stale bar each return None
    and say which."""
    # zoneinfo, not utils.time_utils.ET: that is pytz, and .replace(hour=0) on a
    # pytz datetime keeps the AFTERNOON's offset, an hour wrong on a DST day.
    ET = ZoneInfo("America/New_York")
    now = time.time() if now is None else float(now)
    # 🔴 r94 — ANY INTERVAL THAT CARRIES A VWAP, NOT THE HARDCODED 'primary'.
    # THE BUG THIS FIXES RAN SILENTLY FOR TWO DAYS. `primary` was never a
    # timeframe — it is the FALLBACK row in `indicators.derive()`, written only
    # `if not rows`, i.e. only when the per-timeframe loop produced nothing.
    # r69 repaired that loop (it *"had never once executed"*), so `rows` became
    # non-empty, the fallback stopped firing, and this query began reading a
    # row nobody writes. MEASURED 2026-09-22: 882 rows each for 5m/15m/1h/1d,
    # ALL carrying a VWAP, while `interval='primary'` last appeared 09-20
    # 13:29 ET — the minute r69 landed. The engine reported 412 runs and ZERO
    # failures throughout. A green writer and a dead reader.
    # 🔑 THE VALUE IS INTERVAL-INDEPENDENT BY CONSTRUCTION: `_accumulate_vwap`
    # folds 1-MINUTE bars once per tick and stamps the same `vwap, pv, v,
    # anchor` into every timeframe row, so the newest row carrying a VWAP is
    # the right answer whichever frame it came from — and this cannot break
    # again when the set of intervals next changes.
    rows = _q("SELECT vwap, bar_ts_ms, vwap_anchor_ms FROM indicator_series WHERE symbol=? "
              "AND vwap IS NOT NULL ORDER BY ts_epoch DESC LIMIT 1", (_sym(),))
    if not rows:
        return None, "no VWAP row in indicator_series"
    v, bar_ms, anchor_ms = rows[0]
    if v is None:
        return None, "the latest VWAP row is null"
    # 🔴 r94 — VALIDATED AGAINST THE SESSION OPEN, because the writer now
    # anchors there. Operator: *"don't anchor VWAP to midnight."* Reader and
    # writer move together or the gate simply stays shut in a new way (§23).
    sess = datetime.fromtimestamp(now, ET).replace(hour=9, minute=30, second=0, microsecond=0)
    if anchor_ms is None or abs(float(anchor_ms) / 1000.0 - sess.timestamp()) > 1.0:
        return None, "the latest VWAP is anchored to a prior session, not today's 09:30 ET open"
    if bar_ms is None or now - float(bar_ms) / 1000.0 > max_bar_age_s:
        return None, f"the latest VWAP bar is older than {max_bar_age_s:.0f}s — stale"
    return float(v), ""


# CD.2 — a fork built on closed bars of `tf` is current until the frame's NEXT bar has closed and the engine
# (60 s cadence) has had FORK_GRACE_S to rebuild. In market time: now <= bar_close + span + grace.
FORK_GRACE_S = 120.0
_FORK_SPAN_S = {"5m": 300.0, "15m": 900.0, "1h": 3600.0, "1d": 390.0 * 60.0}


def fork_row(tf: str, now: Optional[float] = None):
    """The frame's newest fork row (built or rejected) IF it is current by market time, else None.
    -> dict(built, direction, reject_reason, slope, containment, bar_ts_ms). A row with no bar_ts_ms is never served."""
    now = time.time() if now is None else float(now)
    rows = _q("SELECT built, direction, reject_reason, slope, containment, bar_ts_ms FROM fork_series "
              "WHERE symbol=? AND interval=? AND bar_ts_ms IS NOT NULL ORDER BY bar_ts_ms DESC, ts_epoch DESC LIMIT 1",
              (_sym(), tf))
    if not rows:
        return None
    built, d, why, slope, contain, bar_ms = rows[0]
    span = _FORK_SPAN_S.get(tf, 3600.0)
    if now > float(bar_ms) / 1000.0 + span + span + FORK_GRACE_S:
        return None                                             # the frame has moved on; this fork is not current
    return {"built": bool(built), "direction": d, "reject_reason": why, "slope": slope,
            "containment": contain, "bar_ts_ms": int(bar_ms)}


def fork_dir(tf: str = "15m", now: Optional[float] = None) -> Optional[str]:
    r = fork_row(tf, now)
    return str(r["direction"]) if r and r["built"] and r["direction"] else None


def nearest_tine(price) -> Optional[float]:
    """Signed distance (points) from price to the nearest correctly-oriented
    live 1h rail; None without a fork. Positive = the rail is above price.

    🔴 r103 — THIS READ A TABLE THAT IS GUARANTEED EMPTY, AND HAD RETURNED None
    ON EVERY ROW EVER WRITTEN. It queried `level_ledger` for `fork1h/%`. r19's
    clause (1) makes `_sources()` skip any pool flagged `moving`, EXACTLY so a
    rail never becomes a ledger row — after 22 simultaneously-live "1h upper
    tine" rows spanning 5.79 points were found in it. So the writer door was
    closed by ruling and this reader was left pointed at the closed door.
    MEASURED 2026-09-22: 0 `fork1h/` rows in `level_ledger`, 83 in
    `level_event`, and `SweepCreditSpread.anchor_tine_to_level` banked **639
    rows, every one of them None**. `ORBStrategy.anchor_tine_to_target` the
    same. §23 — fix every reader, not just the writer.
    ⚠️ AND A GATE SAT BESIDE IT AGREEING. check_level_rejection F1 asserts the
    ledger holds ZERO rail rows — correctly — while this function queried that
    same table expecting rows. Both passed.
    🔑 IT NOW READS THE LIVE PROJECTION, which is where the rails actually are,
    and inherits the tine rule from it: a rail on the wrong side of spot is not
    a candidate, so price above the top rail can never measure to it as support.
    """
    if price is None:
        return None
    try:
        from derived.levels import rail_projection_for
        pr = rail_projection_for(None, _sym(), float(price))
    except Exception:                                           # noqa: BLE001
        return None
    cands = [pr.get("above"), pr.get("below")]
    dists = [float(c["price"]) - float(price) for c in cands if c]
    return min(dists, key=abs) if dists else None


def rail_context(price) -> dict:
    """The rail projection as flat anchor fields, for a plan row (r103).

    🔑 EVERY ONE OF THESE IS COMPUTED ON EVERY TICK ALREADY and has been
    discarded at the plan boundary since the fork was built: `dist_pct`,
    `bars_to_contact` and `slope_per_bar` come straight off `tines_now`, and the
    horizons come from walking the rail forward along that same slope. Nothing
    here is a new measurement; it is the existing one finally being recorded.
    ⚠️ RECORDED, GATING NOTHING (§31). A threshold set before the measurement
    exists is what PREREG_TRAIL.md exists to prevent.
    """
    if price is None:
        return {}
    try:
        from derived.levels import rail_projection_for
        pr = rail_projection_for(None, _sym(), float(price))
    except Exception:                                           # noqa: BLE001
        return {}
    up, dn = pr.get("above"), pr.get("below")

    # 🔴 EVERY FIELD HERE IS NUMERIC ON PURPOSE. `stamp()` does `float(v)` and
    # swallows the failure, and `plan_check` has no text column — so returning
    # "built" or "fork1h/upper" would store None on every row. That is r99's
    # `price_vs_vwap` defect precisely: a CATEGORICAL floated into oblivion,
    # computed every tick for weeks and thrown away at the record boundary.
    # WHICH rail is therefore encoded as a documented CODE rather than a name.
    def _code(c):
        if not c:
            return None
        pv = str(c.get("provenance") or "")
        return 1.0 if pv.endswith("upper") else (-1.0 if pv.endswith("lower")
                                                 else 0.0)   # median

    return {
        "rail_fork_built": 1.0 if pr.get("fork") == "built" else 0.0,
        "rail_slope_per_bar": pr.get("slope_per_bar"),
        # upper=+1, median=0, lower=-1 — the rail's NATURE, not its side
        "rail_above_which": _code(up),
        "rail_above_price": (up or {}).get("price"),
        "rail_above_dist_pts": (up or {}).get("dist_pts"),
        "rail_above_bars_to_contact": (up or {}).get("bars_to_contact"),
        "rail_below_which": _code(dn),
        "rail_below_price": (dn or {}).get("price"),
        "rail_below_dist_pts": (dn or {}).get("dist_pts"),
        "rail_below_bars_to_contact": (dn or {}).get("bars_to_contact"),
    }


def aggressor_share(level, band: float = 0.05, secs: int = 300) -> Optional[float]:
    """Buy-side share of print SIZE within ±band (fraction of level) in the last secs.
    Reads feed_store.db's prints (aggressor_side is the venue's tag)."""
    if level is None:
        return None
    try:
        import sqlite3
        import config
        from utils.paths import feed_db_path as _fdp   # r218: was two config names that never existed, then a fallback that ignored OT_FEED_DB
        path = _fdp()
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=1.0)
        lo, hi = float(level) * (1 - band), float(level) * (1 + band)
        since = time.time() - secs
        rows = conn.execute("SELECT aggressor_side, SUM(size) FROM prints WHERE symbol=? AND ts_epoch>=? "
                            "AND price BETWEEN ? AND ? GROUP BY aggressor_side", (_sym(), since, lo, hi)).fetchall()
        conn.close()
        tot = sum(float(r[1] or 0) for r in rows)
        if tot <= 0:
            return None
        buy = sum(float(r[1] or 0) for r in rows if str(r[0] or "").upper().startswith("B"))
        return round(buy / tot, 4)
    except Exception:                                           # noqa: BLE001
        return None


def oi_at(strike, chain) -> Optional[int]:
    if chain is None or strike is None:
        return None
    try:
        for c in list(getattr(chain, "calls", []) or []) + list(getattr(chain, "puts", []) or []):
            if abs(float(getattr(c, "strike", 0) or 0) - float(strike)) < 0.01:
                return int(getattr(c, "open_interest", 0) or 0)
    except Exception:                                           # noqa: BLE001
        pass
    return None


def stamp(t, **items) -> None:
    """Write record-only checks (verdict None) on a PlanTick. Names are
    prefixed `anchor_` so readers can filter them out of the verdict row."""
    _dir = {"bullish": 1.0, "up": 1.0, "bearish": -1.0, "down": -1.0}
    for k, v in items.items():
        try:
            if isinstance(v, str):
                v = _dir.get(v.lower())
            t.check(f"anchor_{k}", None if v is None else float(v), None)
        except Exception:                                       # noqa: BLE001
            pass
