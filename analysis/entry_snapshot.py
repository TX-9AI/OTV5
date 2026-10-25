"""
analysis/entry_snapshot.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.3  2026-10-23  OTV4TEST r315 (SMA.2) — THE 50 SMA ON EVERY FRAME, IN ATR UNITS, AT EVERY ENTRY. The operator,
      2026-10-23 13:04 ET: "distance from the 50 SMA upon entry and if our success rate correlates to either winning the
      trade or getting the direction right ... Be creative"; the scope he passed on 13:06 ET: "distance to the 50 SMA in
      ATR units and percent ... on each live frame (5m, 15m, 1h, 1d), signed by trade direction ... plus SMA slope and
      cross-frame agreement"; 13:08 ET: "yes to all". New payload key "sma50_mtf": {"rth": {...}, "ext": {...}}, each
      {"5m","15m","1h","1d": frame, "agree": n_with, "of": n_read}. A frame: sma (last 50 CLOSED bars' closes), dist
      (price - sma, signed by direction: + = extended the trade's way), pct (dist / sma x 100), atr (mean true range of
      the last 14 closed bars), d_atr (dist / atr), slope_atr ((sma now - sma 5 bars back) / 5 / atr, signed by
      direction: + = the SMA rising the trade's way), side ("with"/"against"); a frame without 50 closed bars carries
      sma None and "why". 5m/15m/1h are built from the store's 1m bars (r183's one method, so a warehouse backfill can
      build the same objects); 1d is the store's own daily bar, the session's in-progress bar excluded. "sma50_5m"
      is UNCHANGED. SCHEMA_VERSION 2 -> 3. RECORD ONLY: nothing reads it to decide anything; build() still never raises.
v4.2  2026-10-03  OTV4TEST r218 (PATH.1) — _feed_db delegates to utils.paths.feed_db_path (was a hard-coded ~/options-trader default). Same path on the box.
Captures the decision-time context of an entry.

v4.1  2026-09-30  OTV4TEST r183 (SMA.1) — THE 5-MINUTE 50 SMA AND THE OPENING-CANDLE CROSS
      ARE RECORDED ON EVERY TRADE. The operator, 2026-09-30: "On the 5-min, I want to know if
      every directional trade we took above and below the 50 SMA & whether that bias could
      have informed better decisions ... Simply, was that an appropriate read on direction?",
      "I want it in the trades log", and on the opening candle: "when price crossed through
      the 5-min 50 SMA on the opening candle, if it crossed and closed above, it showed
      bullish bias but if it crossed and closed below, the move continued bearish". Then
      "yes" to recording it, backfilling the past trades and testing it out of sample.
      MEASURED THAT DAY, read-only, 198 closed directional trades: right-way at 15 min 60%
      WITH the SMA (n 133) vs 43% AGAINST (n 65); VOLT 85% vs 38%. The open cross held to
      noon on 6 of 7 sessions with the SMA carrying pre-market bars, and was mixed on 4
      with regular-hours bars only - so BOTH are recorded. New payload key "sma50_5m":
      {"rth": {...}, "ext": {...}} - each the SMA of the last 50 CLOSED 5m bars before the
      entry (built from the feed store's 1m bars, the same way live and in the backfill),
      the entry's distance from it signed by direction, "with"/"against", and the session's
      09:30 candle cross ("above"/"below"/"none", null before 09:35). SCHEMA_VERSION 1 -> 2.
      RECORD ONLY: nothing reads it to decide anything; build() still never raises.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

analysis/entry_snapshot.py — the entry-time structural picture, captured. v1.2
the v1.1 fix routed its logs through a helper, and the
        census still counted all five SILENT: it reads the HANDLER BODY, so a
        log behind an indirection is invisible to it. Logger calls are now
        inline; the helper only throttles. Hiding a log from the census would
        defeat the census.
NO SILENT SWALLOWS. v1.0 shipped five `except: return
        None` handlers and the nightly census (tests/swallow_audit.py, backlog
        W.2) counted every one of them as SILENT — in TIER 1, the decision-input
        tier. That is the exact pattern the operator named as the go-live risk,
        added hours after saying so. Each except now routes through _quiet(),
        which logs at DEBUG once per site per process: loud enough that a broken
        capture is findable, quiet enough that it can never spam a session or
        become the reason a fill is not recorded. Behaviour is otherwise
        byte-identical — every handler still returns exactly what it returned.
NEW. Captures, on every filled entry, the FVG zones and
        structural context AS THE LIVE ENGINE HELD THEM at that instant, so the
        TC.2 exit-mechanism bake-off (BoS vs trail vs 5m-FVG, counterfactual on
        identical entries) is computable from banked rows instead of guessed at.
        ROADMAP TC.2 names this precursor and flags it as pre-freeze safe;
        nothing in the repo produced it.
WHY IT CANNOT BE RECONSTRUCTED LATER, which is the whole argument for spending a
column on it:
  - **BoS can be** — and this file deliberately does NOT capture it. `BOSTracker`
    seeds from entry price and direction (both already on the trade row) and
    ratchets forward on closed 1m candles, so a BoS counterfactual is a pure
    function of the post-entry tape. Capturing it would be storage for nothing.
    Stated explicitly because the opposite was assumed before HEAD was read.
  - **The FVG anchor cannot.** The trail anchors to the nearest unfilled in-favor
    gap on the frame `_fvg_frame()` selects, and that frame is the LIVE rolling
    window (`TIMEFRAMES[tf]["candles"]`), which is CONTINUOUS across sessions on
    5m. A replay resampled from the banked RTH 1m tape is session-scoped, so a
    gap formed across the overnight boundary exists live and cannot exist
    offline. That is the same class of divergence defect S found in the replay's
    1m window, and it means an offline reconstruction is not the same object.
  - **Frame DEPTH cannot.** A vote taken on a starved frame is not the vote a
    warm frame would have cast (AK: three of four timeframes had never voted).
    Depth is provenance — it says whether the entry-time picture was even
    entitled to an opinion — and it is gone the moment the tick ends.
CONTRACT — this module is OBSERVABILITY ONLY.
  - It is called AFTER the fill is confirmed and the row is written. It cannot
    reach the entry decision, the size, the strike or any exit.
  - `build()` NEVER raises. A capture failure must never touch a live position;
    it returns a payload carrying `err` and the caller logs it. Silence is the
    failure mode this repo keeps paying for, so the caller gets a boolean and an
    error string rather than a swallowed exception.
  - It reads. It computes nothing the engines do not already compute, and it
    imports the exit engine's OWN gap finders rather than re-deriving them —
    a second lineage would make the counterfactual measure this file instead of
    the trail. The import is deliberately LAZY (inside the function): module-level
    it would drag the TastyTrade SDK into every offline consumer of `analysis/`,
    and the payload is read offline far more often than it is written.
PAYLOAD (JSON, one TEXT column `trades.entry_snapshot`; keys are short because
this is written once per trade and read by tooling, not by eye):
    v      schema version (int) — bump on any key change, never repurpose a key
    at     capture time, UTC ISO (same base as entry_time — never ET)
    px     underlying at capture
    dir    "long" / "short" / "neutral" (condor legs are neutral: no in-favor side)
    frame  "5m" / "1m" — the frame `_fvg_frame()` selected, i.e. the one the
           trail would actually anchor to on this tick
    anchor {t,b} of the nearest unfilled in-favor gap, or null if none existed —
           null is a REAL observation (the trail had no anchor and fell back to
           the percentage leash), not a missing value
    fvg    up to FVG_CAP most-recent gaps on the selected frame: t/b/d/i
    swing  seq / res / sup / hi / lo from the live StructureMap
    depth  bar count per timeframe as held at entry
    err    present ONLY on failure, with the exception text
"""

import json
import os
import time
import logging
from typing import Any, Dict, Optional

from utils.time_utils import ts_for_db

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 3                  # r183: + "sma50_5m"; r315: + "sma50_mtf"

# One DEBUG line per site per process. A capture failure must not spam a session
# (that is how three dead timeframes went unnoticed) and must not be invisible
# either (that is how everything in the 2026-07-27 week hid). See W.2.
_quiet_seen: set = set()


def _first(where: str) -> bool:
    """True the FIRST time a site fails, False forever after.

    The throttle is a helper but the logger call is left INLINE in every
    handler on purpose: tests/swallow_audit.py reads the handler body, so a
    log emitted through an indirection is counted SILENT. Hiding a log from
    the census would defeat the census — v1.1 was written that way and the
    audit caught it.
    """
    if where in _quiet_seen:
        return False
    _quiet_seen.add(where)
    return True

# Bound the row: the gap list is for reconstructing which zones existed, not an
# archive. Most recent first, so the cap drops the oldest and least relevant.
FVG_CAP = 12


def _frames(ctx: Dict[str, Any]):
    """The two frames the trail chooses between, plus the vote frames for depth."""
    data = ctx.get("data") or {}
    df_1m = ctx.get("df_1m")
    df_5m = ctx.get("df_5m")
    return df_1m, df_5m, data


def _depths(df_1m, df_5m, data) -> Dict[str, Optional[int]]:
    out: Dict[str, Optional[int]] = {}
    for name, frame in (("1m", df_1m), ("5m", df_5m),
                        ("15m", data.get("15m")), ("1h", data.get("1h"))):
        try:
            out[name] = int(len(frame)) if frame is not None else None
        except Exception as exc:                             # noqa: BLE001
            if _first(f"depth:{name}"):
                logger.debug("entry_snapshot depth:%s failed (%s: %s) — field "
                             "omitted; once per process", name,
                             type(exc).__name__, exc)
            out[name] = None
    return out


def _swing(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Structural context from the LIVE StructureMap — not recomputed.

    `hi`/`lo` are the most recent swing points the analyzer confirmed, which is
    what a structure-based exit would key off; `res`/`sup` are its nearest
    levels to price. All five can legitimately be None early in a session, and
    None is recorded as None rather than 0.0 — a real level is never exactly
    zero, so a zero here would be indistinguishable from "not formed yet".
    """
    smap = ctx.get("structure")
    if smap is None:
        return {}

    def _last(points):
        try:
            return round(float(points[-1].price), 4) if points else None
        except Exception as exc:                             # noqa: BLE001
            if _first("swing:last"):
                logger.debug("entry_snapshot swing:last failed (%s: %s)",
                             type(exc).__name__, exc)
            return None

    def _lvl(value):
        try:
            return round(float(value), 4) if value is not None else None
        except Exception as exc:                             # noqa: BLE001
            if _first("swing:level"):
                logger.debug("entry_snapshot swing:level failed (%s: %s)",
                             type(exc).__name__, exc)
            return None

    return {
        "seq": getattr(smap, "structure_sequence", None),
        "res": _lvl(getattr(smap, "nearest_resistance", None)),
        "sup": _lvl(getattr(smap, "nearest_support", None)),
        "hi":  _last(getattr(smap, "swing_highs", None)),
        "lo":  _last(getattr(smap, "swing_lows", None)),
    }


def build(ctx: Dict[str, Any], direction: str) -> Dict[str, Any]:
    """Build the entry-time snapshot. NEVER raises — see the module contract."""
    payload: Dict[str, Any] = {"v": SCHEMA_VERSION, "at": ts_for_db()}
    try:
        direction = (direction or "").lower()
        df_1m, df_5m, data = _frames(ctx)
        price = float(ctx.get("price") or 0.0)

        payload["px"] = round(price, 4)
        payload["dir"] = direction
        payload["depth"] = _depths(df_1m, df_5m, data)
        payload["swing"] = _swing(ctx)

        # LAZY, and the module docstring says why. ExitEngine._fvg_frame is a
        # staticmethod, so no engine is constructed and no broker session is
        # touched — we are asking the exit engine which frame IT would use.
        from execution.exit_engine import (            # noqa: PLC0415
            ExitEngine, _find_1m_fvgs, _nearest_unfilled_fvg_in_favor,
        )

        frame = ExitEngine._fvg_frame(df_1m, df_5m)
        payload["frame"] = "5m" if (frame is not None and frame is df_5m) else "1m"

        gaps = _find_1m_fvgs(frame) if frame is not None else []
        payload["fvg"] = [
            {"t": round(float(g.top), 4), "b": round(float(g.bottom), 4),
             "d": g.direction, "i": int(g.index)}
            for g in gaps[:FVG_CAP]
        ]

        # A condor leg has no in-favor side, so it gets no anchor by definition —
        # recorded as null, which is the honest answer rather than an arbitrary
        # side. Its gap list is still worth having: the zones bound where the
        # underlying had room to travel toward either short strike.
        anchor = None
        if direction in ("long", "short") and frame is not None and price > 0:
            g = _nearest_unfilled_fvg_in_favor(frame, current_price=price,
                                               direction=direction)
            if g is not None:
                anchor = {"t": round(float(g.top), 4),
                          "b": round(float(g.bottom), 4)}
        payload["anchor"] = anchor
        # r183 (SMA.1): record only. Its own failure is recorded inside its key.
        payload["sma50_5m"] = sma50_context(time.time(), price, direction)
        # r315 (SMA.2): record only, every frame. Its own failure is recorded inside its key.
        payload["sma50_mtf"] = sma50_mtf_context(time.time(), price, direction)

    except Exception as exc:                                 # noqa: BLE001
        if _first("build"):
            logger.debug("entry_snapshot build failed (%s: %s) — payload "
                         "carries err and the caller warns",
                         type(exc).__name__, exc)
        payload["err"] = f"{type(exc).__name__}: {exc}"

    return payload


# ── r183 (SMA.1) — the 5-minute 50 SMA at entry, and the opening-candle cross ──
SMA_LEN = 50
_ET_TZ = "America/New_York"


def _feed_db() -> str:
    """The same resolution as data/candle_feed.feed_db_path, import-free."""
    from utils.paths import feed_db_path as _fdp      # r218: the one rule (stdlib only)
    return _fdp()


def _bars_5m(conn, symbol: str, t_epoch: float, lookback_s: int = 6 * 86400):
    """[(start_epoch, open, close)] 5m bars built from the store's 1m bars, ending at
    the last bar that CLOSED at or before t_epoch. One method, live and in backfill."""
    rows = conn.execute(
        "SELECT ts_epoch_ms/1000, open, close FROM candles WHERE symbol=? AND interval='1m' "
        "AND ts_epoch_ms BETWEEN ? AND ? ORDER BY ts_epoch_ms",
        (symbol, int((t_epoch - lookback_s) * 1000), int(t_epoch * 1000))).fetchall()
    out: list = []
    for ts, o, c in rows:
        k = int(ts) - int(ts) % 300
        if out and out[-1][0] == k:
            out[-1][2] = c
        else:
            out.append([k, o, c])
    return [b for b in out if b[0] + 300 <= t_epoch]


def _sma_one(conn, symbol: str, t_epoch: float, price: float, direction: str) -> Dict[str, Any]:
    from zoneinfo import ZoneInfo                              # noqa: PLC0415
    import datetime as _dt                                     # noqa: PLC0415
    bars = _bars_5m(conn, symbol, t_epoch)
    if len(bars) < SMA_LEN:
        return {"sma": None, "why": f"{len(bars)} closed 5m bars (need {SMA_LEN})"}
    sma = sum(b[2] for b in bars[-SMA_LEN:]) / SMA_LEN
    out: Dict[str, Any] = {"sma": round(sma, 4)}
    sign = 1 if direction == "long" else -1 if direction == "short" else 0
    if price and sign:
        out["dist"] = round((price - sma) * sign, 4)
        out["side"] = "with" if (price - sma) * sign > 0 else "against"
    # the session's 09:30 candle against the SMA of the 50 closed bars before it
    et = ZoneInfo(_ET_TZ)
    day = _dt.datetime.fromtimestamp(t_epoch, et).date()
    cross = None
    for i, b in enumerate(bars):
        bt = _dt.datetime.fromtimestamp(b[0], et)
        if bt.date() == day and (bt.hour, bt.minute) == (9, 30):
            if i >= SMA_LEN:
                s0 = sum(x[2] for x in bars[i - SMA_LEN:i]) / SMA_LEN
                o, c = b[1], b[2]
                cross = ("above" if c > s0 else "below") if (o - s0) * (c - s0) < 0 else "none"
                out["open_sma"] = round(s0, 4)
            break
    out["open_cross"] = cross
    return out


def sma50_context(t_epoch: float, price: float, direction: str,
                  db_path: Optional[str] = None, symbol: Optional[str] = None) -> Dict[str, Any]:
    """{"rth": {...}, "ext": {...}} or {"err": ...}. NEVER raises; read-only."""
    try:
        import sqlite3                                         # noqa: PLC0415
        if symbol is None:
            import config                                      # noqa: PLC0415
            symbol = str(getattr(config, "INSTRUMENT", "") or "")
        if not symbol:
            return {"err": "no instrument"}
        conn = sqlite3.connect(f"file:{db_path or _feed_db()}?mode=ro", uri=True, timeout=5)
        try:
            return {"rth": _sma_one(conn, symbol, t_epoch, price, (direction or "").lower()),
                    "ext": _sma_one(conn, symbol + "_EXT", t_epoch, price, (direction or "").lower())}
        finally:
            conn.close()
    except Exception as exc:                                   # noqa: BLE001
        if _first("sma50"):
            logger.debug("entry_snapshot sma50 failed (%s: %s)", type(exc).__name__, exc)
        return {"err": f"{type(exc).__name__}: {exc}"}


# ── r315 (SMA.2) — the 50 SMA on 5m / 15m / 1h / 1d, in points, percent and ATR units ──
MTF_FRAMES = (("5m", 300), ("15m", 900), ("1h", 3600))
ATR_LEN = 14
SLOPE_BARS = 5
_MTF_LOOKBACK_S = 21 * 86400        # 55 RTH hours is ~9 sessions; 3 weeks covers weekends + a holiday


def _bars_1m_hlc(conn, symbol: str, t_epoch: float, lookback_s: int = _MTF_LOOKBACK_S):
    return conn.execute(
        "SELECT ts_epoch_ms/1000, open, high, low, close FROM candles WHERE symbol=? AND interval='1m' "
        "AND ts_epoch_ms BETWEEN ? AND ? ORDER BY ts_epoch_ms",
        (symbol, int((t_epoch - lookback_s) * 1000), int(t_epoch * 1000))).fetchall()


def _agg(rows, span: int, t_epoch: float):
    """[(start, o, h, l, c)] bars of `span` seconds from 1m rows, epoch-aligned, only bars CLOSED by t_epoch."""
    out: list = []
    for ts, o, h, l, c in rows:
        k = int(ts) - int(ts) % span
        if out and out[-1][0] == k:
            b = out[-1]
            b[2] = max(b[2], h)
            b[3] = min(b[3], l)
            b[4] = c
        else:
            out.append([k, o, h, l, c])
    return [b for b in out if b[0] + span <= t_epoch]


def _bars_1d(conn, symbol: str, t_epoch: float):
    """The store's daily bars (stamped 00:00 UTC of their session) that CLOSED before t_epoch's session."""
    rows = conn.execute(
        "SELECT ts_epoch_ms/1000, open, high, low, close FROM candles WHERE symbol=? AND interval='1d' "
        "AND ts_epoch_ms <= ? ORDER BY ts_epoch_ms", (symbol, int(t_epoch * 1000))).fetchall()
    return [list(r) for r in rows if int(r[0]) + 86400 <= t_epoch]


def _frame_read(bars, price: float, sign: int) -> Dict[str, Any]:
    if len(bars) < SMA_LEN:
        return {"sma": None, "why": f"{len(bars)} closed bars (need {SMA_LEN})"}
    closes = [b[4] for b in bars]
    sma = sum(closes[-SMA_LEN:]) / SMA_LEN
    out: Dict[str, Any] = {"sma": round(sma, 4)}
    trs = []
    for i in range(max(1, len(bars) - ATR_LEN), len(bars)):
        h, l, pc = bars[i][2], bars[i][3], bars[i - 1][4]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr = sum(trs) / len(trs) if trs else None
    out["atr"] = round(atr, 4) if atr else None
    if price and sign:
        dist = (price - sma) * sign
        out["dist"] = round(dist, 4)
        out["pct"] = round(dist / sma * 100.0, 4)
        out["d_atr"] = round(dist / atr, 3) if atr else None
        out["side"] = "with" if dist > 0 else "against"
        if len(closes) >= SMA_LEN + SLOPE_BARS and atr:
            prev = sum(closes[-SMA_LEN - SLOPE_BARS:-SLOPE_BARS]) / SMA_LEN
            out["slope_atr"] = round((sma - prev) / SLOPE_BARS / atr * sign, 4)
        else:
            out["slope_atr"] = None
    return out


def _mtf_one(conn, symbol: str, t_epoch: float, price: float, direction: str) -> Dict[str, Any]:
    sign = 1 if direction == "long" else -1 if direction == "short" else 0
    rows = _bars_1m_hlc(conn, symbol, t_epoch)
    out: Dict[str, Any] = {}
    for name, span in MTF_FRAMES:
        out[name] = _frame_read(_agg(rows, span, t_epoch), price, sign)
    out["1d"] = _frame_read(_bars_1d(conn, symbol, t_epoch), price, sign)
    read = [f for f in (out[n] for n in ("5m", "15m", "1h", "1d")) if f.get("side")]
    out["agree"] = sum(1 for f in read if f["side"] == "with")
    out["of"] = len(read)
    return out


def sma50_mtf_context(t_epoch: float, price: float, direction: str,
                      db_path: Optional[str] = None, symbol: Optional[str] = None) -> Dict[str, Any]:
    """{"rth": {...}, "ext": {...}} or {"err": ...}. NEVER raises; read-only."""
    try:
        import sqlite3                                         # noqa: PLC0415
        if symbol is None:
            import config                                      # noqa: PLC0415
            symbol = str(getattr(config, "INSTRUMENT", "") or "")
        if not symbol:
            return {"err": "no instrument"}
        conn = sqlite3.connect(f"file:{db_path or _feed_db()}?mode=ro", uri=True, timeout=5)
        try:
            d = (direction or "").lower()
            return {"rth": _mtf_one(conn, symbol, t_epoch, price, d),
                    "ext": _mtf_one(conn, symbol + "_EXT", t_epoch, price, d)}
        finally:
            conn.close()
    except Exception as exc:                                   # noqa: BLE001
        if _first("sma50_mtf"):
            logger.debug("entry_snapshot sma50_mtf failed (%s: %s)", type(exc).__name__, exc)
        return {"err": f"{type(exc).__name__}: {exc}"}


def to_json(ctx: Dict[str, Any], direction: str) -> str:
    """Serialised `build()`. Also never raises — a payload that cannot be
    serialised still returns valid JSON carrying the reason, because a row with
    unparseable text in this column would be worse than a row with none."""
    payload = build(ctx, direction)
    try:
        return json.dumps(payload, separators=(",", ":"))
    except Exception as exc:                                 # noqa: BLE001
        if _first("serialise"):
            logger.debug("entry_snapshot serialise failed (%s: %s)",
                         type(exc).__name__, exc)
        return json.dumps({"v": SCHEMA_VERSION, "at": ts_for_db(),
                           "err": f"serialise {type(exc).__name__}: {exc}"})
