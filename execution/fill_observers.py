"""
execution/fill_observers.py  v1.1
v1.1  2026-10-13  OTV4TEST r280 (EXIT.5 on TEST; the mechanics of otv4 r482 0353b4e) - THE QUOTE WATCH NOW WAKES THE
      TICK. When a Breakout or Runaway single long's own quote (<= 4 s old) is at or below the stop the engine enforces,
      sleep_observing ENDS THE WAIT and the tick runs at once; the tick's evaluate()/decide() still decides, so the
      resting stop (r266) and every exit rule act exactly as before, only sooner. Nothing here exits or orders.
      The operator, 2026-10-13 13:19 ET: "Yes to all" (the relayed "Exit5, yes"); 13:22 ET, on its scope: "Breakout +
      Runaway". Mainline watches ORB + Runaway (r482); TEST wakes on WAKE_STRATEGIES = Breakout + Runaway (ORB is
      retired here). OT_FLOOR_WATCH=trade|log|off, unset = trade; log = v1.0's record-only behaviour; off = no watch.
      COUNTERFACTUAL (operator 10-10): every wake writes a "woke" row with early_s = the seconds the old rule (the full
      15 s sleep) would still have waited, beside its would_wake row in data/counterfactual/quote_watch.jsonl.
v1.0  2026-10-11  OTV4TEST r270 (PMAP.1 + FILL.2) — TWO FILL OBSERVERS, RECORD ONLY. NOTHING HERE WAKES, EXITS OR ORDERS.
      The operator, 2026-10-11 19:14 ET: "I think we should have both 1 & 2, observe only to see if we can use it to
      improve fills" - (1) the fresh premium map, (2) the 2 s quote watch on premium stops.
      EVIDENCE (/var/tmp/premium_map_1011, PREREG sha 8a1bd8e4, terms before results; QQQ-TEST 09-09..10-09): a
      Black-Scholes map re-anchored to the quote 60 s earlier predicts the option's mid within 1.3c median (1.1% of
      premium, p90 3.1%); a map frozen at entry drifts 2.7% -> 9.4% and, used as a stop trigger, booked WORSE than
      as-run (-15,768 vs -8,624 on 51 hard stops). A 5 s mark watch beat as-run by ~$6.8k on 85 stop exits (36%) -
      an UPPER bound (fills at the mid, zero latency). Mainline is building the live form (otv4 EXIT.5).

(1) THE PREMIUM MAP - observe_map(record, mark, spot, now). Once per minute per open single-leg long, from the tick's
    own mark and the chain's spot: implied vol (r=0, expiry 16:00 ET), the UNDERLYING price at which the option
    would sit at its watched stop (U*), and the mark predicted for THIS minute by the PREVIOUS minute's map (its live
    error - the accuracy the study measured, now measured forward). Rows: data/counterfactual/premium_map.jsonl.
(2) THE QUOTE WATCH - observe_watch(records, chain, now). Called from main's end-of-tick sleep every 2 s (the sleep's
    total length is unchanged). For each open position whose stop is a PREMIUM level (watched_stop), it reads that
    contract's own row in the feed store's chain_marks; when the mid is at or below the level on a quote at most
    4 s old, it records that a watch WOULD have woken the tick (at most once per position per 10 s). The tick that
    actually exits is in trades.db, so the gap (seconds, $) is measured from the two. Rows:
    data/counterfactual/quote_watch.jsonl.

WATCHED STOP - the premium level the engine ENFORCES, never a recorded one: trail_stop when armed (> 0) else
stop_premium, on a single-leg LONG only. EXCLUDED: LiquidityHunt (it RECORDS a floor and holds through it, r209/r227),
VOLT (its trail is an UNDERLYING price) and ORBStrategy (underlying-close stop), any spread/butterfly, and a position
already RESTING (r266: its stop has fired). Bar-based exits (Breakout no-progress, structure stops) are not levels.

OT_FILL_OBSERVE=off turns both off (unset = on: record-only). Every function here NEVER raises into the caller.
"""
import json
import logging
import math
import os
import sqlite3
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WATCH_EVERY_S = 2.0          # the sleep slice
WATCH_MAX_AGE_S = 4.0        # two chain_marks flush cycles
WATCH_MIN_GAP_S = 10.0       # at most one would-wake per position per 10 s
MAP_EVERY_S = 60.0           # one map row per position per minute
EXCLUDED = ("LiquidityHunt", "VOLT", "ORBStrategy")
WAKE_STRATEGIES = ("Breakout", "RunawayContinuation")   # r280: the strategies whose crossed stop WAKES the tick


def floor_watch_mode() -> str:
    """r280: OT_FLOOR_WATCH = trade (unset) | log | off. Unknown values read as log (never act on a typo)."""
    v = (os.environ.get("OT_FLOOR_WATCH", "") or "trade").strip().lower()
    return v if v in ("trade", "log", "off") else "log"

_last_wake: dict = {}        # trade_id -> epoch of its last would-wake row
_last_map: dict = {}         # trade_id -> (epoch, spot, iv, strike, call, expiry_close)


def enabled() -> bool:
    return (os.environ.get("OT_FILL_OBSERVE", "") or "on").strip().lower() != "off"


def _cf_path(name: str) -> str:
    d = os.environ.get("OT_COUNTERFACTUAL_DIR") or os.path.join(_ROOT, "data", "counterfactual")
    return os.path.join(d, name)


def _row(name: str, row: dict) -> None:
    try:
        p = _cf_path(name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception as exc:                                     # noqa: BLE001
        logger.warning("[observe] %s row NOT written: %s", name, exc)


# ── Black-Scholes, r = 0 (0DTE) ─────────────────────────────────────────────
def _N(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(S: float, K: float, T: float, v: float, call: bool) -> float:
    if T <= 0 or v <= 0:
        return max(S - K, 0.0) if call else max(K - S, 0.0)
    d1 = (math.log(S / K) + 0.5 * v * v * T) / (v * math.sqrt(T))
    d2 = d1 - v * math.sqrt(T)
    return S * _N(d1) - K * _N(d2) if call else K * _N(-d2) - S * _N(-d1)


def implied_vol(P: float, S: float, K: float, T: float, call: bool) -> Optional[float]:
    intrinsic = max(S - K, 0.0) if call else max(K - S, 0.0)
    if T <= 0 or S <= 0 or K <= 0 or P <= intrinsic + 1e-4:
        return None
    lo, hi = 1e-4, 5.0
    for _ in range(60):
        m = (lo + hi) / 2
        if bs_price(S, K, T, m, call) < P:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def underlying_at(level: float, K: float, T: float, v: float, call: bool, spot: float) -> Optional[float]:
    """The underlying price at which the option's model value equals `level` (bisection within +-15% of spot)."""
    lo, hi = spot * 0.85, spot * 1.15
    f = lambda u: bs_price(u, K, T, v, call) - level
    try:
        if f(lo) * f(hi) > 0:
            return None
        for _ in range(60):
            m = (lo + hi) / 2
            if f(lo) * f(m) > 0:
                lo = m
            else:
                hi = m
        return (lo + hi) / 2
    except (ValueError, ZeroDivisionError):
        return None


def _contract(record) -> Optional[tuple]:
    """(strike, is_call) of a single-leg long, else None."""
    if record.get("short_symbol") or record.get("center_symbol") or float(record.get("spread_width") or 0) > 0:
        return None
    occ = str(record.get("option_symbol") or "").replace(" ", "")
    try:
        cp = occ[-9]
        return int(occ[-8:]) / 1000.0, cp == "C"
    except (ValueError, IndexError):
        return None


def watched_stop(record) -> Optional[float]:
    """The premium level the engine enforces for this record, or None when it has no watchable premium stop."""
    try:
        if str(record.get("strategy") or "") in EXCLUDED or _contract(record) is None:
            return None
        from execution import resting_stop as _rs
        if _rs.is_resting(str(record.get("trade_id"))):
            return None
        trail = float(record.get("trail_stop") or 0.0)
        if trail > 0:
            return trail
        stop = float(record.get("stop_premium") or 0.0)
        return stop if stop > 0 else None
    except Exception:                                            # noqa: BLE001
        return None


def _expiry_close(record) -> Optional[float]:
    """Epoch of the expiry day's bell (16:00 ET, or a half day's 13:00 via close_anchored). None if unreadable."""
    try:
        from utils.time_utils import ET, close_anchored
        from datetime import time as _t
        d = datetime.strptime(str(record.get("expiry"))[:10], "%Y-%m-%d")
        noon = ET.localize(datetime(d.year, d.month, d.day, 12, 0))
        c = close_anchored(_t(16, 0), noon)
        return ET.localize(datetime(d.year, d.month, d.day, c.hour, c.minute)).timestamp()
    except Exception:                                            # noqa: BLE001
        return None


def observe_map(record, mark: float, spot: float, now: Optional[float] = None) -> Optional[dict]:
    """One premium-map row per position per minute. Returns the row written (None when skipped). Never raises."""
    try:
        if not enabled() or not mark or not spot or mark <= 0 or spot <= 0:
            return None
        con = _contract(record)
        if con is None:
            return None
        K, call = con
        tid = str(record.get("trade_id"))
        now = time.time() if now is None else float(now)
        last = _last_map.get(tid)
        if last is not None and now - last[0] < MAP_EVERY_S:
            return None
        close = _expiry_close(record)
        if close is None:
            return None
        T = max(0.0, (close - now) / (365.0 * 86400.0))
        v = implied_vol(mark, spot, K, T, call)
        row = {"ts_epoch": now, "event": "map", "trade_id": tid, "strategy": record.get("strategy"),
               "strike": K, "call": call, "spot": spot, "mark": mark, "iv": v, "T_years": T}
        if last is not None:                                       # the previous map's prediction for NOW
            _t0, _s0, _v0, _K0, _c0, _close0 = last
            if _v0:
                pred = bs_price(spot, _K0, T, _v0, _c0)
                row.update(prev_pred=pred, prev_err=pred - mark, prev_age_s=now - _t0)
        lvl = watched_stop(record)
        if lvl and v:
            row.update(watched_stop=lvl, u_at_stop=underlying_at(lvl, K, T, v, call, spot))
        _last_map[tid] = (now, spot, v, K, call, close)
        _row("premium_map.jsonl", row)
        return row
    except Exception as exc:                                     # noqa: BLE001
        logger.debug("[observe] map skipped: %s", exc)
        return None


def _streamer(chain, K: float, call: bool) -> Optional[str]:
    try:
        for c in (chain.calls if call else chain.puts):
            if abs(float(c.strike) - K) < 1e-6 and c.streamer_symbol:
                return c.streamer_symbol
    except Exception:                                            # noqa: BLE001
        pass
    return None


def _marks(symbols, db_path: Optional[str] = None) -> dict:
    """{streamer_symbol: (bid, ask, updated_epoch)} from the feed store, READ-ONLY. {} on any failure."""
    if not symbols:
        return {}
    try:
        if db_path is None:
            from data.candle_feed import feed_db_path
            db_path = feed_db_path()
        c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=1.0)
        try:
            q = "SELECT streamer_symbol, bid, ask, updated_epoch FROM chain_marks WHERE streamer_symbol IN (%s)" % \
                ",".join("?" * len(symbols))
            return {r[0]: (r[1], r[2], r[3]) for r in c.execute(q, list(symbols))}
        finally:
            c.close()
    except Exception:                                            # noqa: BLE001
        return {}


def observe_watch(records, chain, now: Optional[float] = None, db_path: Optional[str] = None) -> list:
    """Record each open position whose premium stop the latest quote has crossed. Returns the rows written."""
    out = []
    try:
        if not (enabled() or floor_watch_mode() == "trade") or not records or chain is None:
            return out
        now = time.time() if now is None else float(now)
        want = {}
        for r in records:
            lvl = watched_stop(r)
            con = _contract(r)
            if lvl is None or con is None:
                continue
            s = _streamer(chain, con[0], con[1])
            if s:
                want[s] = (r, lvl)
        if not want:
            return out
        m = _marks(list(want), db_path)
        for s, (r, lvl) in want.items():
            q = m.get(s)
            if not q or not q[0] or not q[1] or q[1] < q[0]:
                continue
            mid, age = (q[0] + q[1]) / 2.0, now - float(q[2])
            tid = str(r.get("trade_id"))
            if mid > lvl or age > WATCH_MAX_AGE_S or age < -1.0:
                continue
            if now - _last_wake.get(tid, 0.0) < WATCH_MIN_GAP_S:
                continue
            _last_wake[tid] = now
            row = {"ts_epoch": now, "event": "would_wake", "trade_id": tid, "strategy": r.get("strategy"),
                   "level": lvl, "kind": "trail" if float(r.get("trail_stop") or 0) > 0 else "stop",
                   "bid": q[0], "ask": q[1], "mid": mid, "quote_age_s": age}
            _row("quote_watch.jsonl", row)
            out.append(row)
    except Exception as exc:                                     # noqa: BLE001
        logger.debug("[observe] watch skipped: %s", exc)
    return out


def sleep_observing(seconds: float, records_fn, chain_fn, _sleep=time.sleep, _clock=time.time) -> Optional[dict]:
    """Sleep `seconds` in WATCH_EVERY_S slices, observing between them; never raises.

    r280 (EXIT.5): with OT_FLOOR_WATCH=trade (the default) a fresh cross on a WAKE_STRATEGIES position ENDS the sleep
    and returns its "woke" row, so the tick runs now. It only wakes: the tick decides. Otherwise the total is unchanged
    and it returns None. A wrong level costs one early tick, never a trade.
    """
    end = _clock() + max(0.0, float(seconds))
    while True:
        left = end - _clock()
        if left <= 0:
            return None
        _sleep(min(WATCH_EVERY_S, left))
        mode = floor_watch_mode()
        if not (enabled() or mode == "trade"):
            continue
        try:
            rows = observe_watch(records_fn() or [], chain_fn())
        except Exception:                                        # noqa: BLE001
            rows = []
        if mode != "trade":
            continue
        for r in rows:
            if r.get("strategy") in WAKE_STRATEGIES:
                woke = dict(r, event="woke", early_s=round(max(0.0, end - _clock()), 3))
                _row("quote_watch.jsonl", woke)
                return woke
