"""
data/macro_data.py  v5.1
v5.1  2026-10-25  (MEAS.3) — THE FED-DAY FLAG IS RECORDED CORRECTLY, AND ONLY RECORDED. _check_fed_day had always
      returned False: the live calendar sends ISO dates ("2026-09-16T14:00:00-04:00") and the parser wanted
      "Jun 21, 2026" (ValueError -> bare continue on every event), and it read `currency` where the payload says
      `country`. _event_et_date reads ISO (to ET) with the old form as fallback; the currency is `country`, then
      `currency`; unreadable dates are counted and logged. The Fed-day `butterfly_allowed = False` line is removed
      (nothing reads it, and the operator's 2026-10-03 ruling is that trading must not change on Fed days).
      Gate tests/check_fed_day_record.py.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.2  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).


      logic; the word goes so a live measurement stops dressing as an artifact.
VIX and macro context snapshot.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

options_trader_v3/data/macro_data.py — VIX level, IV rank, and Fed/FOMC
calendar detection. v3.0
Fed days are a confluence modifier, not a hard block.
VIX level gates butterfly strategy and crisis mode.
YAHOO-FINANCE PURGE / data stream mapping optimization. VIX now
        routes through the single shared TastyTrade feed: candle_feed.py
        subscribes "VIX" and _fetch_vix reads it via
        market_data.fetch_quote("VIX") (store-first, TastyTrade REST
        secondary). Fallback chain preserved: fresh -> stale snapshot ->
        conservative default 20.0, each step logged.
        ENTITLEMENT FLAG: if your DXFeed entitlement lacks the VIX index,
        the store path yields nothing and fetch_quote falls through to the
        TastyTrade REST market-data endpoint (InstrumentType.INDEX, "VIX") —
        that is the ONE sanctioned non-DXFeed alternative (same broker, no
        Yahoo). If BOTH fail on your entitlement, macro logs a WARNING and
        holds stale/default — verify on one box per the candle_feed FIRST-RUN
        CHECKLIST before fleet deploy.
"""

import logging
import json
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, List

import requests

from config import (
    VIX_LOW_THRESHOLD, VIX_BUTTERFLY_DISABLE, VIX_NO_ENTRY_THRESHOLD,
    MACRO_FETCH_INTERVAL_MIN, FOREX_FACTORY_URL, FED_EVENT_KEYWORDS,
    IV_RANK_HIGH
)

logger = logging.getLogger(__name__)


@dataclass
class MacroSnapshot:
    vix:            float = 0.0
    vix_band:       str   = "UNKNOWN"   # LOW / NORMAL / ELEVATED / CRISIS
    # measurement computed from the VIX itself — it never touched the retired
    # classifier and only carried the poisoned word. SessionGuard's crisis
    # lockout and setup_scorer read it; the rename touches every reader.
    iv_rank:        float = 0.0         # 0–100
    is_fed_day:     bool  = False
    fed_event_name: str   = ""
    macro_context:  str   = "NEUTRAL"   # RISK_ON / RISK_OFF / NEUTRAL

    # Derived gates
    butterfly_allowed:  bool = True
    butterfly_half_size: bool = False
    new_entries_allowed: bool = True

    fetched_at: float = 0.0


class MacroManager:
    """
    Manages VIX, IV rank, and economic calendar data.
    Refreshes on a configurable interval (default 60 min).
    """

    def __init__(self):
        self._snapshot: Optional[MacroSnapshot] = None
        self._last_fetch: float = 0

    def get(self, force: bool = False) -> MacroSnapshot:
        elapsed_min = (time.time() - self._last_fetch) / 60
        if force or self._snapshot is None or elapsed_min >= MACRO_FETCH_INTERVAL_MIN:
            self._snapshot = self._fetch()
            self._last_fetch = time.time()
        return self._snapshot

    def _fetch(self) -> MacroSnapshot:
        snap = MacroSnapshot(fetched_at=time.time())

        # ── VIX ───────────────────────────────────────────────────────────────
        snap.vix = self._fetch_vix()
        snap.vix_band = self._classify_vix(snap.vix)

        # Derive gates from VIX
        if snap.vix >= VIX_NO_ENTRY_THRESHOLD:
            snap.new_entries_allowed = False
            snap.butterfly_allowed   = False
            snap.macro_context       = "RISK_OFF"
        elif snap.vix >= VIX_BUTTERFLY_DISABLE:
            snap.butterfly_allowed   = False
            snap.new_entries_allowed = True
            snap.macro_context       = "RISK_OFF"
        elif snap.vix >= 15:
            snap.butterfly_allowed      = True
            snap.butterfly_half_size    = True   # Half size butterfly
            snap.new_entries_allowed    = True
            snap.macro_context          = "NEUTRAL"
        else:
            snap.butterfly_allowed      = True
            snap.butterfly_half_size    = False
            snap.new_entries_allowed    = True
            snap.macro_context          = "RISK_ON"

        # ── Fed Calendar ──────────────────────────────────────────────────────
        is_fed, event_name = self._check_fed_day()
        snap.is_fed_day     = is_fed
        snap.fed_event_name = event_name
        if is_fed:
            # MEAS.3 — RECORD ONLY. This used to set butterfly_allowed = False; that
            # line never ran (the detector always returned False) and nothing reads
            # butterfly_allowed, but the operator's ruling (2026-10-03: "I don't want
            # trading behavior to change on fed days") means a fixed detector must
            # not arm it. The flag is stamped on the snapshot and the rows, no more.
            logger.info(f"FED DAY detected: {event_name} (recorded only)")

        logger.info(
            f"Macro snapshot: VIX={snap.vix:.1f} [{snap.vix_band}] "
            f"butterfly={'YES' if snap.butterfly_allowed else 'NO'} "
            f"fed_day={snap.is_fed_day} "
            f"entries={'YES' if snap.new_entries_allowed else 'NO'}"
        )
        return snap

    def _fetch_vix(self) -> float:
        """
        Fetch current VIX from the single shared TastyTrade feed
        (candle_feed subscribes "VIX"; fetch_quote reads the store first,
        TastyTrade REST market-data second — see v3.0 header for the
        entitlement flag). Falls back to stale value, then conservative
        default, fail-loud at each step.
        """
        try:
            from data.market_data import fetch_quote
            val = fetch_quote("VIX")
            if val is not None and float(val) > 0:
                logger.debug(f"VIX fetched via shared feed: {val:.2f}")
                return float(val)
        except Exception as e:
            logger.warning(f"shared-feed VIX fetch failed: {e}")

        # Use stale value if available
        if self._snapshot and self._snapshot.vix > 0:
            logger.warning("VIX unavailable from feed — using stale snapshot value")
            return self._snapshot.vix

        logger.warning("Could not fetch VIX — defaulting to 20 (conservative)")
        return 20.0

    def _classify_vix(self, vix: float) -> str:
        if vix < VIX_LOW_THRESHOLD:
            return "LOW"
        if vix < VIX_BUTTERFLY_DISABLE:
            return "NORMAL"
        if vix < VIX_NO_ENTRY_THRESHOLD:
            return "ELEVATED"
        return "CRISIS"

    def _check_fed_day(self) -> tuple:
        """
        Check Forex Factory JSON calendar for today's high-impact Fed events.
        Returns (is_fed_day, event_name).
        """
        try:
            resp = requests.get(FOREX_FACTORY_URL, timeout=10)
            if resp.status_code != 200:
                return False, ""

            events     = resp.json()
            # r125 — ET date. A UTC roll at 20:00 ET would ask the calendar
            # about TOMORROW, and `Fed Day: No` on an FOMC morning is a wrong
            # answer that reads exactly like a right one.
            from utils.time_utils import now_et as _net
            _t         = _net().date()
            today_str  = _t.strftime("%m/%d/%Y")  # FF format
            today_date = _t

            unparsed = 0
            for event in events:
                ev_date = _event_et_date(event.get("date", ""))
                if ev_date is None:
                    unparsed += 1
                    continue

                if ev_date != today_date:
                    continue

                title    = event.get("title", "")
                impact   = event.get("impact", "")
                # MEAS.3 — the live payload names the currency `country`
                # (measured 2026-09-16: keys title/country/date/impact/forecast/
                # previous); `currency` is kept as a fallback only.
                currency = event.get("country") or event.get("currency") or ""

                if currency != "USD":
                    continue
                if impact not in ("High",):
                    continue

                for keyword in FED_EVENT_KEYWORDS:
                    if keyword.lower() in title.lower():
                        logger.info(f"Fed event found: '{title}' impact={impact}")
                        return True, title

            if unparsed:
                # MEAS.3 — never silent again: an undated event used to vanish
                # in a bare `continue` and the flag read False forever.
                logger.warning(f"Fed calendar: {unparsed} of {len(events)} event "
                               f"date(s) unreadable — skipped")

        except Exception as e:
            logger.warning(f"Fed calendar fetch failed: {e}")

        return False, ""


def _event_et_date(ev_date_str) -> Optional[date]:
    """MEAS.3 — the calendar event's ET date, or None when unreadable.

    The live feed sends ISO 8601 with an offset ("2026-09-16T14:00:00-04:00");
    the v3 parser expected "Jun 21, 2026" only, raised ValueError on every event
    and so never reached the impact test. ISO is read first and converted to ET
    (an offset-less ISO value is taken as ET); the old form is kept as a fallback.
    """
    s = str(ev_date_str or "").strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            from zoneinfo import ZoneInfo
            dt = dt.astimezone(ZoneInfo("America/New_York"))
        return dt.date()
    except ValueError:
        pass
    try:
        return datetime.strptime(s, "%b %d, %Y").date()
    except ValueError:
        return None


# Singleton
_macro_manager: Optional[MacroManager] = None


def get_macro_manager() -> MacroManager:
    global _macro_manager
    if _macro_manager is None:
        _macro_manager = MacroManager()
    return _macro_manager
