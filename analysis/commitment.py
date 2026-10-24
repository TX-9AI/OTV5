"""
analysis/commitment.py  v1.0
v1.0  2026-10-12  OTV4TEST r272 (COMMIT.1 / COMMIT.2 / COMMIT.3) — WE ENTER ON COMMITMENT AND EXIT ON ABANDONMENT.
      The operator, 2026-10-12 10:34 ET: "A good place to get out cannot be a good place to get in and vice versa."
      10:35 ET: "We need some way to define that we enter on commitment and we exit on abandonment. We go with the
      market not against it." 11:35 ET: "Yes, do it" - to (1) the state, RECORDED; (2) the ABANDONED-entry gate,
      TRADING on both paper boxes; (3) the caution size, LOGGED only.
      EVIDENCE (/var/tmp/commit_state_1012, terms frozen before results, sha f9081606 / 6dff9f2a after A1): the side's
      state at entry, QQQ-TEST 09-09..10-09 (233 directional trades): COMMITTED n117 45% +10,256 | NEUTRAL n69 +3,947 |
      ABANDONED n47 21% -11,201. Skipping ABANDONED entries (E2): QQQ losing days -28,566 -> -18,519, total +3,003 ->
      +14,203 (chosen after seeing QQQ - disclosed); UNSEEN mainline ORB (273) -22,963 -> -20,029, -14,848 -> -11,206;
      UNSEEN SOFI/AAL (206) -15,021 -> -9,239, -13,500 -> -8,516; both halves improve in all three. SPX-TEST (20 trades)
      red days -1,275 -> -1,340 (-65). The operator's outlier rule (11:32 ET): a lost outlier is acceptable when the
      losing-day dollars saved exceed it.

THE STATE, per side (long / short), on each CLOSED RTH 1m bar - the study's v0 definitions and readings (NOTES N1-N7),
from measures already in this repo, nothing fitted:
  W  with the market: the last CLOSED 5m close vs the 5m 50 SMA, on the EXT series (the operator's 10-02 ruling: the
     SMA direction rule reads extended hours) built from <SYM>_EXT 1m by analysis.entry_snapshot._bars_5m. A symbol with
     no EXT 1m (SPX) reads its RTH 1m instead, and every row NAMES the series.
  M  momentum: ROC5 on the same 5m closes (close[-1] - close[-6]) - the exhaustion exit's own measure, read forward.
  A  acceptance: CLV of the last 8 closed RTH 1m bars (dojis skipped; the window may reach the prior session),
     acc_recent = mean of the last 3, acc_all = mean of all - the Runaway fizzle's rule, read forward.
  COMMITTED = W and M and acc_recent >= 0.5
  ABANDONED = (not M and acc_recent < 0.5 and acc_recent < acc_all) or W holds for the OPPOSITE side
  NEUTRAL   = otherwise; fewer than 50 closed 5m bars or 3 CLVs is NEUTRAL.
  HYSTERESIS: a raw ABANDONED on the bar after a COMMITTED bar of the same session reads NEUTRAL (COMMITTED ->
  ABANDONED passes through NEUTRAL for one closed bar).

Every function here NEVER raises into the caller. An unreadable state (no store, no bars) is state None with a reason:
the gate ALLOWS the entry and records why (fail open - a skip rule that cannot read is the old behaviour).
A ctx with NO "commitment" key is not a tick (main's loop always sets it): not gated and NOT recorded, so a
checker driving the funnel never writes into the box's live data/counterfactual.
Rows: data/counterfactual/commitment.jsonl (one per new closed bar per side), commit_gate.jsonl (every directional
entry the gate saw, with the would-be order so the old rule is replayable), caution_size.jsonl (COMMIT.3, log only: S2 0.5x
and the SCALING-OFF count from the real size_for(scaled=False), both recorded, neither applied).
"""
import datetime as _dt
import json
import logging
import os
import sqlite3
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DIRECTIONAL = ("Breakout", "RunawayContinuation", "LiquidityHunt", "VOLT", "ORBStrategy")
SMA_LEN = 50
ROC_BARS = 5
CLV_BARS = 8
CLV_RECENT = 3
ACC_MIN = 0.5
CAUTION_FACTOR = 0.5
_ET = "America/New_York"

_last_bar: Dict[str, int] = {}     # side -> ts_ms of the last bar recorded
_warned: set = set()


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
        logger.warning("[commit] %s row NOT written: %s", name, exc)


def _symbol() -> str:
    import config                                                # noqa: PLC0415
    return str(getattr(config, "INSTRUMENT", "") or "")


def _et_date(ts_s: float):
    from zoneinfo import ZoneInfo                                # noqa: PLC0415
    return _dt.datetime.fromtimestamp(ts_s, ZoneInfo(_ET)).date()


def _clv(bar, side: str) -> Optional[float]:
    _, h, l, c = bar
    rng = h - l
    if rng <= 0:
        return None
    return (c - l) / rng if side == "long" else (h - c) / rng


def _raw(bars_1m, i: int, five, side: str) -> Dict[str, Any]:
    """The raw state at RTH bar i (decision time = its end), from the 5m closes usable then."""
    t_end = bars_1m[i][0] / 1000.0 + 60
    closes = [b[2] for b in five if b[0] + 300 <= t_end]
    if len(closes) < SMA_LEN:
        return {"raw": "NEUTRAL", "why": f"{len(closes)} closed 5m bars (need {SMA_LEN})"}
    last = closes[-1]
    sma = sum(closes[-SMA_LEN:]) / SMA_LEN
    roc = closes[-1] - closes[-1 - ROC_BARS]
    w = {"long": last > sma, "short": last < sma}
    m = {"long": roc > 0, "short": roc < 0}
    cl = [x for x in (_clv((b[0], b[2], b[3], b[4]), side) for b in bars_1m[max(0, i - CLV_BARS + 1):i + 1])
          if x is not None]
    if len(cl) < CLV_RECENT:
        return {"raw": "NEUTRAL", "why": f"{len(cl)} CLVs (need {CLV_RECENT})"}
    ar = sum(cl[-CLV_RECENT:]) / CLV_RECENT
    aa = sum(cl) / len(cl)
    opp = "short" if side == "long" else "long"
    if w[side] and m[side] and ar >= ACC_MIN:
        s = "COMMITTED"
    elif ((not m[side]) and ar < ACC_MIN and ar < aa) or w[opp]:
        s = "ABANDONED"
    else:
        s = "NEUTRAL"
    return {"raw": s, "w": w[side], "m": m[side], "roc": round(roc, 4), "acc_recent": round(ar, 4),
            "acc_all": round(aa, 4), "sma": round(sma, 4), "last5m": last}


def snapshot(t_epoch: Optional[float] = None, symbol: Optional[str] = None,
             db_path: Optional[str] = None) -> Dict[str, Any]:
    """{"long": {...}, "short": {...}, "bar_ts": ms, "series": ...} at the last RTH 1m bar CLOSED at or before
    t_epoch; on failure {"err": reason}. Read-only. NEVER raises."""
    try:
        t = float(t_epoch if t_epoch is not None else time.time())
        sym = symbol or _symbol()
        if not sym:
            return {"err": "no instrument"}
        if db_path is None:
            from utils.paths import feed_db_path                 # noqa: PLC0415
            db_path = feed_db_path()
        if not os.path.exists(db_path):
            return {"err": f"no feed store at {db_path}"}
        from analysis.entry_snapshot import _bars_5m             # noqa: PLC0415  (r183's loader, reused)
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        try:
            rows = conn.execute(
                "SELECT ts_epoch_ms, high, low, close FROM candles WHERE symbol=? AND interval='1m' "
                "AND ts_epoch_ms <= ? ORDER BY ts_epoch_ms DESC LIMIT ?",
                (sym, int(t * 1000) - 60000, CLV_BARS + 2)).fetchall()
            if len(rows) < 2:
                return {"err": f"{len(rows)} closed RTH 1m bars"}
            bars = [(r[0], None, r[1], r[2], r[3]) for r in reversed(rows)]
            t_end = bars[-1][0] / 1000.0 + 60
            series = sym + "_EXT"
            five = _bars_5m(conn, series, t_end)
            if len([b for b in five if b[0] + 300 <= t_end]) < SMA_LEN:
                series = sym                                     # no EXT 1m (SPX): the RTH series, named
                five = _bars_5m(conn, series, t_end)
        finally:
            conn.close()
        n = len(bars) - 1
        same_session = _et_date(bars[n][0] / 1000.0) == _et_date(bars[n - 1][0] / 1000.0)
        out: Dict[str, Any] = {"bar_ts": bars[n][0], "series": series}
        for side in ("long", "short"):
            cur = _raw(bars, n, five, side)
            prev = _raw(bars, n - 1, five, side)
            st = cur["raw"]
            if st == "ABANDONED" and same_session and prev["raw"] == "COMMITTED":
                st = "NEUTRAL"                                   # hysteresis: through NEUTRAL for one bar
            out[side] = dict(cur, state=st)
        return out
    except Exception as exc:                                     # noqa: BLE001
        if "snapshot" not in _warned:
            _warned.add("snapshot")
            logger.warning("[commit] state unreadable (%s: %s)", type(exc).__name__, exc)
        return {"err": f"{type(exc).__name__}: {exc}"}


def observe(t_epoch: Optional[float] = None) -> Dict[str, Any]:
    """COMMIT.1 - the tick's snapshot (for ctx["commitment"]); one row per side per NEW closed bar. NEVER raises."""
    snap = snapshot(t_epoch)
    try:
        if "err" in snap:
            return snap
        for side in ("long", "short"):
            if _last_bar.get(side) == snap["bar_ts"]:
                continue
            _last_bar[side] = snap["bar_ts"]
            _row("commitment.jsonl", dict(snap[side], side=side, bar_ts=snap["bar_ts"], series=snap["series"],
                                          at=round(time.time(), 3)))
    except Exception as exc:                                     # noqa: BLE001
        logger.warning("[commit] observe row failed: %s", exc)
    return snap


def side_of(signal) -> Optional[str]:
    d = str(getattr(signal, "direction", "") or "").lower()
    if d in ("long", "short"):
        return d
    return {"call": "long", "put": "short"}.get(str(getattr(signal, "option_side", "") or "").lower())


def gate(signal, ctx, *, mode: str, paper: bool, contracts=None) -> bool:
    """COMMIT.2 - True when the entry must NOT be placed: a directional entry whose side is ABANDONED, mode 'trade',
    on a PAPER box. Records every directional entry it sees. Unreadable -> allowed. NEVER raises (an error allows)."""
    try:
        name = str(getattr(signal, "strategy_name", "") or "")
        if mode == "off" or name not in DIRECTIONAL:
            return False
        if not isinstance(ctx, dict) or "commitment" not in ctx:
            # Not a tick: main's loop ALWAYS sets ctx["commitment"] (a state or {"err": ...}). A caller outside the
            # loop (a checker driving the funnel) gets the old behaviour and writes NO row - a fixture must never
            # reach the box's live data/counterfactual (the r194 BOX.16 class).
            logger.debug("[commit] %s: no tick state on ctx - not gated, not recorded", name)
            return False
        side = side_of(signal)
        snap = ctx.get("commitment")
        st = None
        why = ""
        if not isinstance(snap, dict):
            why = "no commitment state on this tick"
        elif "err" in snap:
            why = str(snap["err"])
        elif side not in ("long", "short"):
            why = f"no side for direction {getattr(signal, 'direction', None)!r}"
        else:
            st = (snap.get(side) or {}).get("state")
        effective = mode if (mode != "trade" or paper) else "log"
        block = bool(st == "ABANDONED" and effective == "trade")
        _row("commit_gate.jsonl", {
            "at": round(time.time(), 3), "strategy": name, "side": side, "state": st,
            "why_unread": why or None, "mode": mode, "effective": effective,
            "decision": ("BLOCKED" if block else ("would_block" if st == "ABANDONED" else "allowed")),
            "bar_ts": (snap or {}).get("bar_ts") if isinstance(snap, dict) else None,
            "detail": (snap or {}).get(side) if isinstance(snap, dict) and side in ("long", "short") else None,
            "order": {"strike": getattr(signal, "strike", None),
                      "option_side": getattr(signal, "option_side", None),
                      "premium": getattr(signal, "entry_premium", None),
                      "contracts": contracts,
                      "underlying_entry": getattr(signal, "underlying_entry", None),
                      "underlying_stop": getattr(signal, "underlying_stop", None),
                      "price": (ctx or {}).get("price") if isinstance(ctx, dict) else None}})
        if block:
            logger.info("[commit] BLOCKED %s %s - the %s side is ABANDONED (COMMIT.2; recorded with the would-be "
                        "order)", name, side, side)
        elif st == "ABANDONED":
            logger.info("[commit] would block %s %s - side ABANDONED, mode %s (COMMIT.2)", name, side, effective)
        elif why:
            logger.info("[commit] %s %s allowed - state unreadable: %s (COMMIT.2 fails open)", name, side, why)
        return block
    except Exception as exc:                                     # noqa: BLE001
        logger.warning("[commit] gate error - entry allowed: %s", exc)
        return False


class SizeCall:
    """A pass-through for the order's own RiskManager.size_for call that RECORDS its exact arguments, so COMMIT.3's
    scaling-off candidate is that SAME call with scaled=False (`flat()`), never a re-derivation of sizing."""
    def __init__(self, rm):
        self._rm = rm
        self._args = None

    def size_for(self, structure, **kw):
        self._args = (structure, dict(kw))
        return self._rm.size_for(structure, **kw)

    def flat(self):
        if self._args is None:
            raise RuntimeError("SizeCall.flat() before the order's own size_for call")
        structure, kw = self._args
        return self._rm.size_for(structure, **dict(kw, scaled=False))


def _first_directional_loss_exit(db_path: str, day) -> Optional[str]:
    """The exit_time of the session's first closed directional trade (by exit_time) IF it lost; else None."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
    try:
        rows = conn.execute(
            "SELECT exit_time, pnl_usd, entry_time FROM trades WHERE status='closed' "
            "AND coalesce(relaxed_entry,0)=0 AND strategy IN (%s) AND exit_time IS NOT NULL "
            "ORDER BY exit_time" % ",".join("?" * len(DIRECTIONAL)), DIRECTIONAL).fetchall()
    finally:
        conn.close()
    for x, p, e in rows:
        try:
            if _et_date(_dt.datetime.fromisoformat(e).timestamp()) != day:
                continue
        except Exception:                                        # noqa: BLE001
            continue
        return x if (p or 0) < 0 else None
    return None


def caution(signal, ctx, *, mode: str, contracts, flat_size=None) -> None:
    """COMMIT.3 - LOG ONLY. After the session's first closed directional loss, record BOTH candidate sizes:
    (a) S2 - 0.5x unless the side is COMMITTED; (b) SCALING-OFF - `flat_size()`, the caller's REAL size_for call
    with scaled=False (ORB/Breakout/VOLT; the operator, 2026-10-12 11:52 ET: "Yes"); a strategy with no scaling switch
    is already flat, so (b) = actual. Never changes the order. NEVER raises."""
    try:
        name = str(getattr(signal, "strategy_name", "") or "")
        if mode == "off" or name not in DIRECTIONAL:
            return
        import config                                            # noqa: PLC0415
        now = time.time()
        first = _first_directional_loss_exit(config.DB_PATH, _et_date(now))
        if not first:
            return
        side = side_of(signal)
        snap = (ctx or {}).get("commitment") if isinstance(ctx, dict) else None
        st = (snap.get(side) or {}).get("state") if isinstance(snap, dict) and side in ("long", "short") else None
        factor = 1.0 if st == "COMMITTED" else CAUTION_FACTOR
        n = int(contracts or 0)
        if flat_size is None:
            b, b_src = n, "actual (no scaling switch: already flat)"
        else:
            fr = flat_size()
            b = int(getattr(fr, "contracts", 0) or 0) if getattr(fr, "allowed", False) else 0
            b_src = "size_for(scaled=False)" + ("" if getattr(fr, "allowed", False)
                                               else f" REFUSED: {getattr(fr, 'reject_reason', '')}")
            logger.info("[commit] caution: any '[size] scaling OFF -> flat' line just above is the COUNTERFACTUAL "
                        "scaling-off size (%d) - the order keeps %d (COMMIT.3, log only)", b, n)
        _row("caution_size.jsonl", {"at": round(now, 3), "strategy": name, "side": side, "state": st,
                                    "after_first_loss_exit": first, "contracts_actual": n,
                                    "factor": factor, "contracts_s2": max(1, int(n * factor)) if n else 0,
                                    "contracts_scaling_off": b, "scaling_off_source": b_src,
                                    "mode": mode})
    except Exception as exc:                                     # noqa: BLE001
        logger.warning("[commit] caution row failed: %s", exc)
