"""
strategy/shadow_rules.py  v5.1
v5.1  2026-11-08  OTV5 r95 (CHK.13) - GATES DECLARED. tests/check_gates.py walks every strategy/*.py and refuses one with no
      GATES dict (WA 36); this file shipped at r90 without one, so check_gates was red from r90 to r94. Its five constants are
      the frozen definition of the two scored rules, so all are FOUNDATIONAL (loosening one scores a different rule than the
      study froze). DATA ONLY: nothing at runtime reads GATES (the checkers read it); no decision, row or log line changes.
v5.0  2026-11-08  OTV5 r90 (SHADOW.1) - TWO RULES THAT NEVER DECIDE, RECORDED ON EVERY DECISION THEY WOULD HAVE TOUCHED.
      The operator, 2026-11-08: "this is one time where a log only is worth doing. We've been burned on 'log-only'
      before, so once we start trading on Monday I want immediate feedback that it's really logging. Log only:
      opening range rule and SMA 50 rule, confirm it's logging Monday morning."
      (The TCS shadow ran a week and wrote nothing; nobody noticed until the Saturday brief.)

  HUNT_OR_EM   S5 Rule 1 (~/reviews/studies/s5_hunt, PREREG sha d7981a1f..., blind PASS 11-08):
               skip a LiquidityHunt entry when the opening-range width / the expected move at entry < 0.927
               (the design median the frozen rule used; "0.93" in the summary is its rounding).
               opening range = high - low of today's 09:30-09:44 1m RTH bars (the study's bars[:15]);
               EM = the em_platform the Hunt's own tick recorded (the tastytrade platform number; the study had
               it on 71/71 trades), else spot x IV x sqrt(max(390 - minutes since 09:30, 1) / 390 / 252).
               ⚠️ LIVE HAS NO LOOKAHEAD. The study read all fifteen 09:30-09:44 bars even for an entry at 09:37
               (49 of its 71 trades entered before 09:45). Live reads only the bars CLOSED at the decision and says
               how many (or_bars=k/15, "partial"); on the study's own 49 early trades that flips 8 verdicts. Both
               facts are on the row, so the forward score can be read either way.
               Recorded ONCE PER FIRE (every Hunt signal, whether it then executes or another gate refuses it).
  PARK_SMA50   S4's equity pick (~/reviews/studies/s4_park_ma, CHOICE.json "S1d_slope", blind FAIL 11-08 - logged
               by the operator's order anyway): keep when the daily SMA 50 slopes the trade's way, skip when it
               slopes against. SMA 50 of the daily closes BEFORE today, against the same SMA 10 sessions earlier;
               needs more than 60 prior closes; a missing reading keeps (as the study's keep()). Daily closes are
               the box's own TastyTrade 1d candles in the feed store (no yfinance on a box). An index is recorded
               too, labelled index (the rule is an equity rule).
               Recorded on EVERY PARK tick that reached a direction (before GATE-G / the commitment gate / the
               contract can refuse it), so a refused PARK still carries its verdict.

WHERE: one plan_check row on the tick that made the decision (check_name shadow_hunt_or_em / shadow_park_sma50,
value = the ratio / the slope in points, verdict n/a, note = "<verdict> ..."), so it ships with the derived stream;
and one bot.log line "[shadow-rule] HUNT_OR_EM|PARK_SMA50 ..." per fire / per PARK direction-and-verdict per day.

NEVER DECIDES, NEVER RAISES, NEVER SILENT: every entry point is wrapped; an input that cannot be read, or an error
in this file, records verdict "unknown" with the reason. It touches only the tick's checks / check_notes (not its
notes, so the plan's reason text is unchanged) and the log. No env knob, no configure item: the thresholds are here.
Gate: tests/check_shadow_rules.py.
"""
from __future__ import annotations

import logging
import math
from typing import Optional

logger = logging.getLogger("strategy.shadow_rules")

HUNT_OR_EM_THRESHOLD = 0.927          # S5 R1, frozen (design median of or_width_em)
OR_FIRST_HM, OR_LAST_HM = (9, 30), (9, 44)
OR_BARS = 15
SMA_N, SMA_LAG, SMA_MIN_CLOSES = 50, 10, 61

# WA 36 gate categories (tests/check_gates.py; asserted by tests/check_shadow_rules.py G1). These never decide a trade -
# they define WHICH rule the forward score measures, so none may be relaxed.
GATES = {
    "HUNT_OR_EM_THRESHOLD": "FOUNDATIONAL",   # S5 R1 frozen 0.927
    "OR_BARS":              "FOUNDATIONAL",   # the 09:30-09:44 range the study read
    "SMA_N":                "FOUNDATIONAL",   # S4 S1d_slope: SMA 50 ...
    "SMA_LAG":              "FOUNDATIONAL",   # ... against itself 10 sessions earlier
    "SMA_MIN_CLOSES":       "FOUNDATIONAL",   # 61+ prior closes, else unknown (the study keeps)
}
CHECK_HUNT, CHECK_PARK = "shadow_hunt_or_em", "shadow_park_sma50"
_LOGGED: dict = {}                    # (rule, day, key) -> last verdict logged (PARK: one line per change)


def _f(v) -> Optional[float]:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if x != x else x


def _record(t, name: str, value, verdict: str, note: str) -> None:
    """The ONLY write to a tick: its checks and check_notes. Never its notes (the reason text)."""
    try:
        v = _f(value)
        t.checks[name] = (round(v, 6) if v is not None else None, None)
        t.check_notes[name] = (verdict + " " + note).strip()[:300]
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[shadow-rule] %s could not be recorded: %s", name, exc)


def _day_today():
    from utils.time_utils import now_et
    return now_et().date()


def _ms(day, h, m) -> int:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return int(datetime(day.year, day.month, day.day, h, m, tzinfo=ZoneInfo("America/New_York")).timestamp() * 1000)


# ── HUNT_OR_EM ──────────────────────────────────────────────────────────────────────────────────────────────────────
def opening_bars(symbol: str, day, now_hm) -> object:
    """[(minute, high, low)] of today's 09:30-09:44 1m bars in the feed store that have CLOSED by now_hm
    (bar start + 1 min <= now_hm), or a string naming why they could not be read. Never raises."""
    try:
        import sqlite3
        from data.candle_feed import feed_db_path
        conn = sqlite3.connect(f"file:{feed_db_path()}?mode=ro", uri=True, timeout=5.0)
        try:
            rows = conn.execute(
                "SELECT ts_epoch_ms, high, low FROM candles WHERE symbol=? AND interval='1m' AND ts_epoch_ms>=? "
                "AND ts_epoch_ms<=? AND close > 0 ORDER BY ts_epoch_ms",
                (symbol, _ms(day, *OR_FIRST_HM), _ms(day, *OR_LAST_HM))).fetchall()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        return f"1m bars unreadable ({type(exc).__name__})"
    t0 = _ms(day, *OR_FIRST_HM)
    now_min = (int(now_hm[0]) * 60 + int(now_hm[1])) - (9 * 60 + 30)
    out = []
    for ts, h, l in rows:
        k = int(round((int(ts) - t0) / 60000))
        if 0 <= k < OR_BARS and k + 1 <= now_min and _f(h) and _f(l):
            out.append((k, float(h), float(l)))
    return out


def hunt_or_em(*, symbol: str, day, now_hm, price, em_platform=None, iv=None) -> dict:
    """{"value", "verdict", "note"} for one Hunt decision. Pure but for the store read. Never raises."""
    try:
        if now_hm is None:
            return {"value": None, "verdict": "unknown", "note": "reason=the clock could not be read"}
        bars = opening_bars(symbol, day, now_hm)
        if isinstance(bars, str):
            return {"value": None, "verdict": "unknown", "note": "reason=" + bars}
        if not bars:
            return {"value": None, "verdict": "unknown", "note": "reason=no closed 09:30-09:44 1m bar in the store"}
        width = max(b[1] for b in bars) - min(b[2] for b in bars)
        em, src = _f(em_platform), "platform"
        if not em or em <= 0:
            px, v = _f(price), _f(iv)
            mins = (int(now_hm[0]) * 60 + int(now_hm[1])) - (9 * 60 + 30)
            em = (px * v * math.sqrt(max(390 - mins, 1) / 390 / 252)) if (px and v and v > 0) else None
            src = "iv"
        if not em or em <= 0:
            return {"value": None, "verdict": "unknown",
                    "note": f"reason=no expected move (no em_platform, no IV) or_width={width:.4f}"}
        ratio = width / em
        verdict = "would_skip" if ratio < HUNT_OR_EM_THRESHOLD else "keep"
        n = len(bars)
        return {"value": ratio, "verdict": verdict,
                "note": (f"ratio={ratio:.3f} thr={HUNT_OR_EM_THRESHOLD} or_width={width:.4f} em={em:.4f} em_src={src} "
                         f"or_bars={n}/{OR_BARS}" + ("" if n == OR_BARS else " partial"))}
    except Exception as exc:                                    # noqa: BLE001
        return {"value": None, "verdict": "unknown", "note": f"reason=error {type(exc).__name__}: {exc}"[:200]}


def record_hunt(t, *, symbol: str, now_et, price, direction: str = "", entry: str = "", contract=None,
                atm_iv=None, observed: bool = False) -> None:
    """Called by LiquidityHunt.generate_signal on every fire, BEFORE take(). Never raises."""
    try:
        from utils.time_utils import parse_hm
        hm = parse_hm(now_et)
        day = _day_today()
        emp = (t.checks.get("em_platform") or (None, None))[0]
        iv = _f(getattr(contract, "iv", None)) or _f(atm_iv)
        r = hunt_or_em(symbol=symbol, day=day, now_hm=hm, price=price, em_platform=emp, iv=iv)
    except Exception as exc:                                    # noqa: BLE001
        r = {"value": None, "verdict": "unknown", "note": f"reason=error {type(exc).__name__}"}
    try:
        _record(t, CHECK_HUNT, r["value"], r["verdict"], r["note"])
        logger.info("[shadow-rule] HUNT_OR_EM %s %s %s %s%s %s", symbol, entry, direction, r["verdict"],
                    " (log-only fire)" if observed else "", r["note"])
    except Exception:                                           # noqa: BLE001
        pass


# ── PARK_SMA50 ──────────────────────────────────────────────────────────────────────────────────────────────────────
def daily_closes_before(symbol: str, day) -> object:
    """The box's TastyTrade 1d closes for `symbol` dated before `day`, oldest first, or a string naming why they could
    not be read. A 1d bar is stamped at its session's UTC midnight. Never raises."""
    try:
        import sqlite3
        from datetime import datetime, timezone
        from data.candle_feed import feed_db_path
        conn = sqlite3.connect(f"file:{feed_db_path()}?mode=ro", uri=True, timeout=5.0)
        try:
            rows = conn.execute("SELECT ts_epoch_ms, close FROM candles WHERE symbol=? AND interval='1d' "
                                "AND close > 0 ORDER BY ts_epoch_ms", (symbol,)).fetchall()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        return f"1d bars unreadable ({type(exc).__name__})"
    out = {}
    for ts, c in rows:
        d = datetime.fromtimestamp(int(ts) / 1000, timezone.utc).date()
        if d < day and _f(c):
            out[d] = float(c)
    return [out[d] for d in sorted(out)]


def sma50_slope(closes: list):
    """(slope, why): SMA 50 now minus SMA 50 ten sessions earlier, as S4 (sma(dc) - sma(dc[:-10]), len > 60)."""
    if len(closes) < SMA_MIN_CLOSES:
        return None, f"{len(closes)} prior daily closes (needs {SMA_MIN_CLOSES})"
    now = sum(closes[-SMA_N:]) / SMA_N
    then_ = closes[:-SMA_LAG]
    was = sum(then_[-SMA_N:]) / SMA_N
    return now - was, ""


def park_sma50(*, symbol: str, day, direction: str, index: bool) -> dict:
    try:
        sgn = 1 if direction == "long" else -1 if direction == "short" else 0
        if not sgn:
            return {"value": None, "verdict": "unknown", "note": "reason=no direction"}
        closes = daily_closes_before(symbol, day)
        if isinstance(closes, str):
            return {"value": None, "verdict": "unknown", "note": "reason=" + closes}
        slope, why = sma50_slope(closes)
        if slope is None:
            return {"value": None, "verdict": "unknown", "note": "reason=" + why + " (the study keeps)"}
        verdict = "keep" if sgn * slope > 0 else "would_skip"
        return {"value": slope, "verdict": verdict,
                "note": (f"slope={slope:+.4f} dir={direction} closes={len(closes)} last={closes[-1]:.2f}"
                         + (" index" if index else " equity"))}
    except Exception as exc:                                    # noqa: BLE001
        return {"value": None, "verdict": "unknown", "note": f"reason=error {type(exc).__name__}: {exc}"[:200]}


_PARK_CACHE: dict = {}                # (symbol, day, direction) -> result: one store read per day per direction


def record_park(t, *, symbol: str, day, direction: str, index: bool) -> None:
    """Called by ParkPlan.prepare once the first hour gave a direction, before any gate can refuse. Never raises."""
    try:
        key = (symbol, str(day), direction)
        r = _PARK_CACHE.get(key)
        if r is None or r["verdict"] == "unknown":
            r = park_sma50(symbol=symbol, day=day, direction=direction, index=index)
            _PARK_CACHE[key] = r
    except Exception as exc:                                    # noqa: BLE001
        r = {"value": None, "verdict": "unknown", "note": f"reason=error {type(exc).__name__}"}
    try:
        _record(t, CHECK_PARK, r["value"], r["verdict"], r["note"])
        lk = ("PARK_SMA50", symbol, str(day), direction)
        if _LOGGED.get(lk) != r["verdict"]:
            _LOGGED[lk] = r["verdict"]
            logger.info("[shadow-rule] PARK_SMA50 %s %s %s %s", symbol, direction, r["verdict"], r["note"])
    except Exception:                                           # noqa: BLE001
        pass
