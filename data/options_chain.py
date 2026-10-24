"""
data/options_chain.py  v4.7
v4.7  2026-10-18  OTV4TEST r301 (LOG.1) — A ZERO-MARKS CHAIN OUTSIDE RTH IS SAID ONCE AT INFO, NOT EVERY MINUTE AT ERROR.
      The r101 rehearsal builds the chain every 60 s all evening and the marks are gone after the bell, so FAIL-LOUD
      logged 2,417 ERROR lines in the week of 10-12 - all 16:00-23:59 ET, none inside RTH - and a real ERROR was
      invisible in them (audit 2026-10-18 E3). zero_marks_log_level(): inside RTH unchanged (ERROR every build);
      outside, INFO once per (symbol, expiry) per process, then silent. An unreadable clock stays LOUD.
v4.6  2026-10-04  OTV4TEST r241 (SPXW.1, LIVE.1 F6) — THE MORNING EXPIRATION IS NEVER TRADED. fetch_chain drops every settlement_type "AM" contract BEFORE the date is chosen, so an AM-only date never becomes "today"; the drop is logged once per (symbol, date); chain_map stays whole for the archival aux tenors. The operator, 2026-10-04: "Never trade the morning expiration on SPX." MEASURED by dry-run probe the same day: 10-16 lists 1,060 SPX/AM beside 938 SPXW/PM, 11-20 944 / 840 - the literal is "AM". Authored on SPX-TEST (gate tests/check_spxw_only.py W1-W7, sha 63499c5b...), shared with mainline: 1-REPORTER adopts the same text.
v4.5  2026-10-03  OTV4TEST r218 (PATH.1) — _feed_db_path delegates to utils.paths.feed_db_path: its own copy defaulted to a hard-coded ~/options-trader. Same path on the box.
v4.4  2026-10-02  OTV4TEST r186 (ZBID.1) — A CONTRACT WITH NO BID IS NEVER SELECTED.
      `two_sided(c)` (bid > 0 and ask > 0) arrives at module level and
      select_orb_strike and select_sweep_strike require it beside their
      `mark > 0.05` floor, which a no-bid contract cleared because its mark
      IS its ask. AAL 2026-10-02 lost 3,128 on three VOLTs bought that way.
      Nothing else changes: the mark rule, spread/fly/condor legs and r164's
      order pricing are untouched. Shared with otv4; check_zero_bid_refused.
v4.3  2026-10-02  OTV4TEST r185 (LADR.1) — STRIKES ARE READ FROM THE CHAIN. (1)
      `chain_increment()` arrives at module level, moved verbatim from
      gex_pin_butterfly._chain_increment (r198; the fly keeps the name as an
      alias). (2) `select_butterfly_strikes` is DELETED: 0 callers in either
      tree, and it centred on round_to_strike(spot, STRIKE_INCREMENT) - the
      table BFLY.3 measured wrong. (3) `select_orb_strike` takes a float
      target: the ORB now hands it the RAW 100% target, not a pre-rounded
      one (analysis/orb_engine.py). Its logic is unchanged.
v4.2  2026-08-29  r177: OptionsChain.atm_iv — the field main's butterfly
      dispatch had been reading NEVER EXISTED (getattr default masked it);
      EM starved fleet-wide and GEXPinButterfly could never fire. Median of
      the 3 nearest-to-spot streamed ivs per side, decimal; 0.0 when the
      feed has no ivs, so the no-fallback starvation stays loud.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Chain construction, strike selection, chain_subs publication.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

data/options_chain.py — Options chain data from TastyTrade SDK.
TERM.1: publish a NARROW ATM BAND for the weekly and
        monthly expiries so TERM STRUCTURE becomes computable. Every snapshot
        to date carried a SINGLE expiry equal to the session date - skew and IV
        level available, term slope impossible - and chain history cannot be
        retrieved afterwards, so each day collected single-expiry has no term
        structure permanently.
        ~9 STRIKES PER TENOR, NOT A CHAIN. Term structure needs ATM IV out at a
        date, not walls/GEX/a delta ladder. Full chains x3 would be ~750
        subs/box against the ~40 concurrent-session cap v3.1 measured - the
        constraint that removed the per-box streamer entirely - and SPX has
        already been OOM-KILLED at 419 MB on chain volume. ATM bands are ~270.
        PLACED AFTER THE CHAIN IS BUILT because spot is not known earlier;
        `chain.spot_price` is derived from the ATM strike further up, and an
        earlier call would have banded around 0.0 and published the lowest
        strikes on the board.
        WRITES ONLY TO `chain_subs_aux`. `chain_subs` is CHECK (id = 1) and
        belongs to the bot's own expiry; candle_feed v3.15 unions the aux rows
        and FAILS OPEN if this never runs or writes garbage.
STORE READER (Option 1b — supersedes v3.1's own streamer).
        Live fleet test of v3.1 measured TastyTrade's unpublished session cap
        near ~40 concurrent: 29 candle-feeds + 29 per-box chain streamers do
        NOT fit (only ~6-11 chain streamers were admitted; the rest sat in
        backoff all afternoon). This release removes DXLink from the bot
        process ENTIRELY: candle_feed v3.4 carries the Greeks/Quote
        subscriptions on its existing socket and publishes latest values to a
        chain_marks table in the shared store; this module (a) publishes the
        desired streamer-symbol set + expiry to chain_subs, and (b) reads
        chain_marks like every other store consumer. Fleet steady state:
        29 sessions total — the number proven safe for weeks. Kept from v3.1:
        structure cache (OT_CHAIN_STRUCT_REFRESH_S), staleness ceiling
        (OT_CHAIN_STALE_S — stale marks are refused, never served), and the
        zero-mark FAIL-LOUD (bootstrap-aware: quiet for the first ticks after
        publishing subs while the feed populates). REQUIRES candle_feed v3.4
        on the box — fails loud with a version hint if the tables are absent.
PERSISTENT CHAIN STREAMER (superseded same day; header kept
        for the record). Fail-loud + structure cache introduced here survive.
        The old code opened a NEW DXLinkStreamer websocket on EVERY fetch_chain()
        call — one full REST-token + connect + auth + subscribe + teardown cycle
        per 15 s tick per box. Across the fleet that saturated TastyTrade's
        (unpublished) concurrent-session pool: DXLink returned
        'user sessions has exceeded the configured limit' roughly once per tick
        on 24/29 boxes, quotes/Greeks came back empty, every contract kept
        mark=0.0, the mark>0.05 liquidity filters rejected every strike in every
        plausible-looking "no setup" day. Changes:
        1. ONE long-lived DXLinkStreamer per process (lazy connect on the shared
           tasty_client loop thread, held via AsyncExitStack). Subscriptions are
           RECONCILED (only never-seen symbols subscribed; expiry rollover
           unsubscribes all and resets). Steady state: 2 sessions/box
           (candle-feed + this), ZERO churn.
        2. Reconnect with EXPONENTIAL BACKOFF (5s → 60s cap) on stream failure —
           a saturated pool is never hammered at tick cadence again (the old
           retry-every-15s kept the pool full and made the outage self-sustaining).
        3. Latest-value Greeks/Quote maps persist across ticks (each tick drains
           pending events non-blocking; only never-seen symbols block briefly).
           If the stream is DOWN and the last event is older than
           OT_CHAIN_STALE_S, fetch_chain returns None — stale marks are never
           served as fresh (an open position priced off dead marks would trip
           the -25% floor on garbage).
        4. FAIL-LOUD: a built chain in which NO contract has mark>0 returns None
           with an ERROR log instead of a structurally-valid corpse. Silent
           zero-mark chains are what hid this outage for five hours.
        5. Chain STRUCTURE (REST strike list) is cached OT_CHAIN_STRUCT_REFRESH_S
           (default 30 min) — the 0DTE strike set is static intraday; only
           Greeks/marks need per-tick freshness, and those ride the stream.
        Env knobs: OT_CHAIN_STRUCT_REFRESH_S=1800 · OT_CHAIN_INIT_COLLECT_S=10 ·
        OT_CHAIN_RECONNECT_BASE_S=5 · OT_CHAIN_RECONNECT_MAX_S=60 ·
        OT_CHAIN_STALE_S=120.
delta-band sweep selection (caller passes a strength-scaled
        target delta); ORB nearest-strike snap breaks toward higher/lower delta.
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
Chain fetching:  get_option_chain(session, symbol) → dict[date, list[Option]]
Greeks/marks:    read from the store's chain_marks table (candle_feed v3.4 owns
                 the one DXLink socket and publishes latest values)
Workflow:
  1. get_option_chain() returns all Option objects (no pricing)
  2. Filter to today's expiry (0DTE)
  3. Publish desired symbols to chain_subs; read Greeks/Quotes from chain_marks
  4. Build OptionsChain with fully populated OptionContract objects
"""

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from types import SimpleNamespace
from datetime import date, datetime
from typing import Optional, List, Dict
from decimal import Decimal

from tastytrade.instruments import get_option_chain, Option as TTOption, OptionType

from data.tasty_client import get_session, run_async, TastyClientError
from config import (
    INSTRUMENT, STRIKE_INCREMENT, CONTRACT_MULTIPLIER,
    SWEEP_DELTA_TOLERANCE, ORB_STRIKE_DELTA_BIAS
)
from utils.math_utils import round_to_strike, floor_to_strike, ceil_to_strike

logger = logging.getLogger(__name__)

# ── transport knobs (env-overridable, OT_ convention) ─────────────────────────
OT_CHAIN_STRUCT_REFRESH_S = float(os.environ.get("OT_CHAIN_STRUCT_REFRESH_S", "1800"))
OT_CHAIN_STALE_S          = float(os.environ.get("OT_CHAIN_STALE_S",          "120"))
OT_CHAIN_BOOTSTRAP_S      = float(os.environ.get("OT_CHAIN_BOOTSTRAP_S",      "30"))

def _feed_db_path() -> str:
    """Same resolution as data/candle_feed.feed_db_path (kept import-free so this
    module never drags the feed's SDK surface into the bot process)."""
    from utils.paths import feed_db_path as _fdp      # r218: the one rule (stdlib only)
    return _fdp()


@dataclass
class OptionContract:
    """A single option contract with pricing and greeks."""
    symbol:         str     = ""    # OCC symbol
    underlying:     str     = ""
    expiry:         str     = ""    # YYYY-MM-DD
    option_type:    str     = ""    # "C" or "P"
    strike:         float   = 0.0
    bid:            float   = 0.0
    ask:            float   = 0.0
    mark:           float   = 0.0
    delta:          float   = 0.0
    gamma:          float   = 0.0
    theta:          float   = 0.0
    vega:           float   = 0.0
    iv:             float   = 0.0
    open_interest:  int     = 0
    volume:         int     = 0
    streamer_symbol: str    = ""    # DXFeed streamer symbol


@dataclass
class OptionsChain:
    """Full 0DTE chain snapshot."""
    underlying:     str = ""
    expiry:         str = ""
    spot_price:     float = 0.0
    iv_rank:        float = 0.0
    calls:          List[OptionContract] = field(default_factory=list)
    puts:           List[OptionContract] = field(default_factory=list)

    @property
    def atm_iv(self) -> float:
        """ATM implied vol as a DECIMAL, assembled from the streamed per-
        contract ivs the chain already carries.

        🔴 r177 — THE FIELD MAIN HAD BEEN READING DID NOT EXIST. main's
        butterfly dispatch did `getattr(chain, "atm_iv", 0.0)`; no such
        attribute was ever set, the default masked the absence, expected_move
        starved on every box on every tick, and GEXPinButterfly was
        STRUCTURALLY UNABLE TO FIRE from the inversion (r160) until this —
        while pinning and concentration were passing on ~10 boxes. The exact
        silent-default class SPEC.1 hunts, hidden from check_attr_fidelity by
        the getattr default.

        Median of the ivs of the 3 nearest-to-spot contracts per side that
        carry iv > 0 — robust to one bad quote, no smoothing, no model. If
        the feed has not populated ivs yet this returns 0.0 and the butterfly
        keeps starving LOUDLY (its no-fallback rule is design, not defect):
        we fixed the supply, not the standard.
        """
        try:
            spot = float(self.spot_price or 0.0)
            if spot <= 0:
                return 0.0
            ivs = []
            for side in (self.calls, self.puts):
                near = sorted((c for c in (side or []) if float(getattr(c, "iv", 0) or 0) > 0),
                              key=lambda c: abs(float(c.strike) - spot))[:3]
                ivs.extend(float(c.iv) for c in near)
            if not ivs:
                return 0.0
            ivs.sort()
            return ivs[len(ivs) // 2]
        except Exception:                                       # noqa: BLE001
            return 0.0



_ZERO_MARKS_SAID: set = set()          # r301 (LOG.1): (symbol, expiry) said once per process outside RTH


def zero_marks_log_level(symbol: str, today_str: str, in_rth=None) -> str:
    """r301 (LOG.1) — how loud a ZERO-live-marks chain is. INSIDE RTH it is the v3.1 FAIL-LOUD:
    "error" on every build (a corpse during the session is the failure that costs the session).
    OUTSIDE RTH the chain has no marks by nature - the rehearsal (r101) builds it every 60 s all
    evening - so the first build per (symbol, expiry) per process is "info" and the rest are
    "" (silent). Measured 2026-10-12..16: 2,417 ERROR lines, all 16:00-23:59 ET, 0 inside RTH.
    `in_rth` is injectable for the gate; None reads the clock."""
    try:
        if in_rth is None:
            from utils.time_utils import is_rth
            in_rth = bool(is_rth())
    except Exception:                                           # noqa: BLE001
        in_rth = True                                           # an unreadable clock stays LOUD
    if in_rth:
        return "error"
    key = (str(symbol), str(today_str))
    if key in _ZERO_MARKS_SAID:
        return ""
    _ZERO_MARKS_SAID.add(key)
    return "info"

class OptionsChainFetcher:
    """
    Fetches the 0DTE options chain from TastyTrade and populates
    Greeks/marks from the shared store (chain_marks, fed by candle_feed v3.4).

    v3.2: pure STORE READER. The feed (candle_feed v3.4) owns the one DXLink
    socket; this class publishes the desired symbol set to chain_subs and reads
    latest marks from chain_marks. No async, no websockets, no sessions.
    """

    def __init__(self):
        # chain-structure cache: symbol -> (monotonic_fetched, chain_map)
        self._struct_cache: Dict[str, tuple] = {}
        # last-published subscription request (avoid rewriting an unchanged row)
        self._published: tuple = ("", frozenset())
        self._published_at: float = 0.0        # wall time of last publish
        self._db_ro = None                     # cached read-only connection

    def fetch_chain(self, symbol: str = INSTRUMENT,
                    expiry: Optional[str] = None) -> Optional[OptionsChain]:
        """
        Fetch the 0DTE options chain with Greeks and marks.

        Args:
            symbol: Underlying symbol (QQQ, SPY, SPX)
            expiry: YYYY-MM-DD — defaults to today (0DTE)

        Returns:
            OptionsChain or None on failure
        """
        # 🔴 r125 — TRADING DATE IS AN ET DATE. `date.today()` is the box's,
        # and the boxes run UTC: after 20:00 ET the UTC date has already rolled,
        # so an evening run selects TOMORROW's expiry as "0DTE". Every session
        # after 8pm — which is when most of this fleet's build work happens.
        from utils.time_utils import now_et as _net
        today      = _net().date()
        target_date = date.fromisoformat(expiry) if expiry else today
        today_str  = target_date.isoformat()

        try:
            session = get_session()

            # Step 1: chain STRUCTURE (REST) — cached; the 0DTE strike set is
            # static intraday. v3.1: was fetched every tick for no benefit.
            chain_map = self._get_chain_structure(session, symbol)

            if not chain_map:
                logger.warning(f"Empty option chain for {symbol}")
                return None

            # 🔴 SPXW.1 — NEVER TRADE THE MORNING EXPIRATION (the operator,
            # 2026-10-04: "Never trade the morning expiration on SPX"). The SDK
            # returns an AM-settled series and a PM one expiring the SAME day in
            # ONE list (tastytrade instruments.get_option_chain's own docstring:
            # "e.g. SPXW and SPX AM options") - SPX's third Fridays. The AM
            # series stops trading the day before. It is dropped here, BEFORE a
            # date is chosen, so an AM-only date can never become "today".
            # Equity options are all PM, so the rule is generic. `chain_map`
            # itself stays whole: the archival aux tenors (TERM.1) record the
            # market, not our choices.
            tradeable = {}
            for _d, _opts in chain_map.items():
                _keep = [o for o in _opts
                         if str(getattr(o, "settlement_type", "") or "").upper() != "AM"]
                if _keep:
                    tradeable[_d] = _keep
            # SAID, once per symbol and date: SPX lists AM monthlies months out,
            # so only the REQUESTED date's drop is news (a third Friday), and a
            # per-tick line would bury it.
            _am_today = len(chain_map.get(target_date, [])) - len(tradeable.get(target_date, []))
            _seen = self.__dict__.setdefault("_am_said", set())
            if _am_today and (symbol, target_date) not in _seen:
                _seen.add((symbol, target_date))
                logger.info(f"[chain] {symbol} {target_date}: dropped {_am_today} AM-settled "
                            f"contract(s) - the morning expiration is never traded")

            # Step 2: Find today's expiration
            options_today: List[TTOption] = tradeable.get(target_date, [])

            if not options_today:
                # Try to find the nearest available expiry
                available = sorted(tradeable.keys())
                future    = [d for d in available if d >= target_date]
                if future:
                    target_date   = future[0]
                    today_str     = target_date.isoformat()
                    options_today = tradeable[target_date]
                    logger.info(f"No 0DTE for {today}, using nearest: {today_str}")
                else:
                    logger.warning(f"No options expiring on or after {today_str}")
                    return None

            logger.info(f"Found {len(options_today)} options for {symbol} {today_str}")

            # Step 3: Build OptionContract list (no pricing yet)
            calls_raw: List[OptionContract] = []
            puts_raw:  List[OptionContract] = []

            for opt in options_today:
                oc = OptionContract(
                    symbol       = opt.symbol,
                    underlying   = symbol,
                    expiry       = today_str,
                    option_type  = "C" if opt.option_type == OptionType.CALL else "P",
                    strike       = float(opt.strike_price),
                    streamer_symbol = opt.streamer_symbol or "",
                )
                if opt.option_type == OptionType.CALL:
                    calls_raw.append(oc)
                else:
                    puts_raw.append(oc)

            # Step 4: publish subs + read Greeks/quotes from the store (v3.2)
            streamer_syms = [
                oc.streamer_symbol for oc in calls_raw + puts_raw
                if oc.streamer_symbol
            ]

            # ── v4.0: REAL OPEN INTEREST ────────────────────────────────────
            # `open_interest` was declared on OptionContract and NEVER ASSIGNED,
            # so it defaulted to 0 on every contract for the life of v3. gex_data
            # then fell through to `oi_proxy = 1000 * gamma` and multiplied by
            # gamma AGAIN, making GEX a gamma-SQUARED surface rather than dealer
            # positioning - which is why the "pin" always landed at the money
            # (gamma peaks there) and why it churned 12.4M -> 0.1M -> 2.0M in
            # three minutes on SPX 2026-08-19.
            # ⚠️ REST, NOT A SUBSCRIPTION. OI updates ONCE A DAY; a Summary
            # stream would cost one subscription PER CONTRACT against the ~40
            # concurrent-session cap the fleet already runs close to. That cost
            # is the likeliest reason this was never wired.
            # ⚠️ FAILURE LEAVES OI AT 0 AND SAYS SO. It does not substitute.
            try:
                from data.open_interest import fetch_open_interest
                _occ = [oc.symbol for oc in calls_raw + puts_raw if oc.symbol]
                _oi = fetch_open_interest(session, _occ)
                if _oi:
                    for oc in calls_raw + puts_raw:
                        v = _oi.get(oc.symbol)
                        if v is not None:
                            oc.open_interest = int(v)
            except Exception as _oie:                          # noqa: BLE001
                logger.warning("OI wiring failed (%s) - GEX runs WITHOUT open "
                               "interest this cycle", _oie)

            if streamer_syms:
                greeks_map, quote_map = self._fetch_greeks_and_quotes(
                    session, streamer_syms, expiry=today_str
                )
                self._apply_market_data(calls_raw, greeks_map, quote_map)
                self._apply_market_data(puts_raw,  greeks_map, quote_map)

            # Step 5: Sort by strike
            calls_raw.sort(key=lambda c: c.strike)
            puts_raw.sort(key=lambda c: c.strike)

            chain = OptionsChain(
                underlying = symbol,
                expiry     = today_str,
                calls      = calls_raw,
                puts       = puts_raw,
            )

            # Populate spot_price from ATM call (nearest delta to 0.50)
            liquid_calls = [c for c in chain.calls if c.delta > 0 and c.mark > 0]
            if liquid_calls:
                try:
                    atm = min(liquid_calls, key=lambda c: abs(c.delta - 0.50))
                    chain.spot_price = atm.strike
                except Exception:
                    pass

            # v3.1 FAIL-LOUD: a chain with zero live marks is a corpse, not data.
            # Serving it lets every liquidity filter reject every strike while
            # the logs look like a quiet no-setup day (2026-07-13). Callers
            # already handle None correctly; None is also strictly safer for an
            # OPEN position than zero marks (premium=0 would trip the -25%
            # floor on garbage).
            if not any(c.mark > 0 for c in chain.calls + chain.puts):
                if self._in_bootstrap():
                    logger.info(
                        f"Chain warming: {symbol} {today_str} — subs published "
                        f"{time.time() - self._published_at:.0f}s ago, waiting "
                        f"for the feed to populate chain_marks"
                    )
                else:
                    _lvl = zero_marks_log_level(symbol, today_str)        # r301 (LOG.1)
                    if _lvl == "error":
                        logger.error(
                            f"Chain FAIL-LOUD: {symbol} {today_str} built with ZERO "
                            f"live marks ({len(chain.calls)}C/{len(chain.puts)}P) — "
                            f"feed marks absent/stale; returning None instead of a "
                            f"corpse (is candle-feed v3.4 healthy?)"
                        )
                    elif _lvl == "info":
                        logger.info(
                            f"Chain has no live marks outside RTH: {symbol} {today_str} "
                            f"({len(chain.calls)}C/{len(chain.puts)}P) — expected after the bell; "
                            f"the rehearsal runs without a chain. Said once per expiry per process; "
                            f"inside RTH this is FAIL-LOUD at ERROR on every build."
                        )
                return None

            logger.info(
                f"Chain built: {symbol} {today_str} "
                f"calls={len(chain.calls)} puts={len(chain.puts)} "
                f"spot~=${chain.spot_price:.0f}"
            )

            # ── TERM.1 (2026-08-18) — AUXILIARY TENORS, ARCHIVAL ONLY ────────
            # Publish a NARROW ATM BAND for the weekly and monthly so TERM
            # STRUCTURE becomes computable. Every snapshot to date carried a
            # SINGLE expiry equal to the session date, which leaves skew and IV
            # level available and the term slope impossible — and chain history
            # cannot be retrieved afterwards, so a day collected single-expiry
            # has no term structure permanently.
            # ⚠️ PLACED HERE, AFTER THE CHAIN IS BUILT, BECAUSE SPOT IS NOT
            # KNOWN EARLIER. `chain.spot_price` is derived from the ATM strike
            # further up this function; an earlier call site would have banded
            # around 0.0 and published the lowest strikes on the board.
            # ⚠️ ~9 STRIKES PER TENOR, NOT A CHAIN. Term structure needs ATM IV
            # out at a date — not walls, GEX or a delta ladder. Full chains x3
            # would be ~750 subs/box against the ~40 concurrent-session cap
            # v3.1 measured (the constraint that removed the per-box streamer
            # entirely), and SPX has already been OOM-KILLED at 419 MB on chain
            # volume. ATM bands are ~270 and clear both.
            # ⚠️ WRITES ONLY TO `chain_subs_aux`. `chain_subs` is CHECK (id = 1)
            # and belongs to the bot's own expiry; nothing here can change what
            # the trading path subscribes to, and candle_feed v3.15 fails open
            # if this never runs or writes garbage.
            try:
                from analysis.tenor_publish import publish_aux_tenors
                _aux = publish_aux_tenors(_feed_db_path(), chain_map,
                                          float(chain.spot_price or 0),
                                          target_date)
                if _aux:
                    logger.info("[tenor] aux ATM bands: %s",
                                ", ".join(f"{k}={v}" for k, v in _aux.items()))
            except Exception:                                  # noqa: BLE001
                pass          # archival enrichment never touches the chain path

            return chain

        except Exception as e:
            logger.error(f"Failed to fetch chain for {symbol}: {e}")
            return None

    def _get_chain_structure(self, session, symbol: str):
        """v3.1 — REST strike-list, cached OT_CHAIN_STRUCT_REFRESH_S. On a REST
        failure with a warm cache, serve the cache and warn (structure is
        static intraday; marks ride the stream and stay fresh regardless)."""
        now = time.monotonic()
        cached = self._struct_cache.get(symbol)
        if cached and (now - cached[0]) < OT_CHAIN_STRUCT_REFRESH_S:
            return cached[1]
        try:
            chain_map = run_async(get_option_chain(session, symbol))
            # FRC.3 — the VENUE'S price grid, fetched ONCE PER SYMBOL PER
            # PROCESS. Static instrument metadata, not a quote.
            # ⚠️ THE GUARD IS THE POINT. The first version had this comment and
            # NO CACHE CHECK, so it fired an extra SDK call on EVERY
            # fetch_chain() — and fetch_chain is called from three places in the
            # tick loop. That is hundreds of needless API calls per box per
            # session and real rate-limit exposure, on a live path, described by
            # a comment that claimed the opposite.
            # Best-effort: a failure here must never stop a chain fetch, and a
            # failed attempt is remembered so it is not retried every tick
            # either — a broken fetch must not become the same hot loop.
            try:
                from execution.tick_size import (cache_venue_rule,
                                                 mark_fetch_failed,
                                                 needs_venue_rule)
                if needs_venue_rule(symbol):
                    from tastytrade.instruments import NestedOptionChain
                    # `get`, not `a_get` — this SDK build has no `a_get`, and
                    # `get` is a COROUTINE despite the sync-looking name
                    # (inspect.iscoroutinefunction is True), so it goes through
                    # run_async like every other SDK call here. Both verified
                    # against the installed package; either mistake raises into
                    # the except and falls back to the PENNY_CLASSES guess
                    # FOREVER, silently.
                    _noc = run_async(NestedOptionChain.get(session, symbol))
                    _noc = _noc[0] if isinstance(_noc, list) and _noc else _noc
                    if not cache_venue_rule(symbol, getattr(_noc, "tick_sizes", None)):
                        mark_fetch_failed(symbol)
            except Exception as _tex:                          # noqa: BLE001
                try:
                    from execution.tick_size import mark_fetch_failed
                    mark_fetch_failed(symbol)
                except Exception:                              # noqa: BLE001
                    pass
                logger.debug("tick-size fetch skipped for %s: %s", symbol, _tex)
            if chain_map:
                self._struct_cache[symbol] = (now, chain_map)
            return chain_map
        except Exception as e:
            if cached:
                logger.warning(f"Chain structure refresh failed ({e}) — serving "
                               f"cached structure ({now - cached[0]:.0f}s old)")
                return cached[1]
            raise

    def _fetch_greeks_and_quotes(
        self,
        session,
        streamer_symbols: List[str],
        expiry: str = ""
    ) -> tuple:
        """
        v3.2 — publish the desired symbol set to chain_subs (only when it
        changes), then read latest Greeks/Quotes from chain_marks. Rows older
        than OT_CHAIN_STALE_S are refused. Returns (greeks_map, quote_map)
        shaped exactly like the old streamer maps (attribute access), so
        _apply_market_data is unchanged.
        """
        self._publish_desired_subs(expiry, streamer_symbols)
        return self._read_marks(streamer_symbols)

    def _publish_desired_subs(self, expiry: str, streamer_symbols: List[str]):
        want = (expiry, frozenset(streamer_symbols))
        if want == self._published:
            return
        try:
            conn = sqlite3.connect(_feed_db_path(), timeout=3.0)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS chain_subs (
                        id            INTEGER PRIMARY KEY CHECK (id = 1),
                        expiry        TEXT NOT NULL,
                        symbols       TEXT NOT NULL,
                        updated_epoch REAL NOT NULL
                    );""")
                conn.execute(
                    "INSERT OR REPLACE INTO chain_subs (id, expiry, symbols, "
                    "updated_epoch) VALUES (1, ?, ?, ?)",
                    (expiry, json.dumps(sorted(streamer_symbols)), time.time()))
                conn.commit()
            finally:
                conn.close()
            self._published = want
            self._published_at = time.time()
            logger.info(f"Chain subs published: {len(streamer_symbols)} symbols, "
                        f"expiry {expiry} — feed will subscribe within a flush cycle")
        except Exception as e:
            logger.warning(f"Chain subs publish failed: {e}")

    def _ro_conn(self):
        if self._db_ro is None:
            self._db_ro = sqlite3.connect(
                f"file:{_feed_db_path()}?mode=ro", uri=True, timeout=3.0)
        return self._db_ro

    def _read_marks(self, streamer_symbols: List[str]) -> tuple:
        greeks_map: Dict[str, object] = {}
        quote_map:  Dict[str, object] = {}
        try:
            floor = time.time() - OT_CHAIN_STALE_S
            cur = self._ro_conn().execute(
                "SELECT streamer_symbol, bid, ask, delta, gamma, theta, vega, iv,"
                " updated_epoch FROM chain_marks WHERE updated_epoch >= ?", (floor,))
            rows = {r[0]: r for r in cur.fetchall()}
        except sqlite3.OperationalError as e:
            # table absent (feed still on <= v3.3) or db missing entirely
            self._db_ro = None
            logger.error(f"chain_marks unreadable ({e}) — is candle_feed v3.4 "
                         f"running on this box?")
            return {}, {}
        except Exception as e:
            self._db_ro = None
            logger.warning(f"chain_marks read failed: {e}")
            return {}, {}

        for sym in streamer_symbols:
            r = rows.get(sym)
            if r is None:
                continue
            _, bid, ask, delta, gamma, theta, vega, iv, _ep = r
            if (bid or 0) > 0 or (ask or 0) > 0:
                quote_map[sym] = SimpleNamespace(
                    event_symbol=sym, bid_price=bid or 0.0, ask_price=ask or 0.0)
            if any((delta, gamma, theta, vega, iv)):
                greeks_map[sym] = SimpleNamespace(
                    event_symbol=sym, delta=delta or 0.0, gamma=gamma or 0.0,
                    theta=theta or 0.0, vega=vega or 0.0, volatility=iv or 0.0)
        return greeks_map, quote_map

    def _in_bootstrap(self) -> bool:
        """True during the grace window right after publishing a new sub set —
        the feed needs a flush cycle or two to subscribe and populate."""
        return (time.time() - self._published_at) < OT_CHAIN_BOOTSTRAP_S

    def _apply_market_data(
        self,
        contracts: List[OptionContract],
        greeks_map: Dict[str, object],
        quote_map:  Dict[str, object]
    ):
        """Apply Greeks and Quote data to OptionContract objects."""
        for oc in contracts:
            sym = oc.streamer_symbol

            greek = greeks_map.get(sym)
            if greek:
                oc.delta = float(greek.delta or 0)
                oc.gamma = float(greek.gamma or 0)
                oc.theta = float(greek.theta or 0)
                oc.vega  = float(greek.vega  or 0)
                oc.iv    = float(greek.volatility or 0)

            quote = quote_map.get(sym)
            if quote:
                bid = float(quote.bid_price or 0)
                ask = float(quote.ask_price or 0)
                oc.bid  = bid
                oc.ask  = ask
                oc.mark = (bid + ask) / 2 if bid > 0 and ask > 0 else (bid or ask)

    # ─── Strike Selection ─────────────────────────────────────────────────────

    def select_orb_strike(self, chain: OptionsChain, direction: str,
                           target_strike: float,
                           delta_bias: str = ORB_STRIKE_DELTA_BIAS
                           ) -> Optional[OptionContract]:
        """Nearest liquid strike to target_strike. When strikes bracket the target
        equally, break toward the higher- (more ITM/participation) or lower-
        (further OTM) |delta| per delta_bias."""
        contracts = chain.calls if direction == "long" else chain.puts
        candidates = [c for c in contracts if c.mark > 0.05 and two_sided(c)]   # ZBID.1
        if not candidates:
            logger.warning("No liquid contracts in chain")
            return None
        min_dist = min(abs(c.strike - target_strike) for c in candidates)
        nearest = [c for c in candidates
                   if abs(c.strike - target_strike) <= min_dist + 1e-6]
        if len(nearest) == 1:
            best = nearest[0]
        elif delta_bias == "lower":
            best = min(nearest, key=lambda c: abs(c.delta))
        else:  # "higher" — more ITM / more directional participation
            best = max(nearest, key=lambda c: abs(c.delta))
        logger.info(
            f"ORB strike: {best.option_type} {best.strike} "
            f"mark=${best.mark:.2f} delta={best.delta:.3f} (bias={delta_bias})"
        )
        return best

    def select_sweep_strike(self, chain: OptionsChain,
                             direction: str,
                             target_delta: float,
                             tolerance: float = SWEEP_DELTA_TOLERANCE
                             ) -> Optional[OptionContract]:
        """Select the OTM strike whose |delta| is nearest target_delta (the caller
        scales target_delta by reversal strength). Prefers strikes within
        +/- tolerance of the target; falls back to the nearest available."""
        pool = chain.calls if direction == "long" else chain.puts
        liquid = [c for c in pool if c.mark > 0.05 and two_sided(c)          # ZBID.1
                  and 0.0 < abs(c.delta) <= 0.55]
        if not liquid:
            return None
        band = [c for c in liquid if abs(abs(c.delta) - target_delta) <= tolerance]
        pick_from = band if band else liquid
        best = min(pick_from, key=lambda c: abs(abs(c.delta) - target_delta))
        logger.info(
            f"Sweep strike: {best.option_type} {best.strike} "
            f"mark=${best.mark:.2f} delta={best.delta:.3f} "
            f"(target={target_delta:.2f}{'' if band else ', band empty->nearest'})"
        )
        return best

    def get_iv_rank(self, chain: OptionsChain) -> float:
        """Estimate IV rank. Falls back to ATM call IV."""
        if chain.iv_rank > 0:
            return chain.iv_rank
        if chain.calls:
            atm = min(chain.calls, key=lambda c: abs(c.delta - 0.5))
            return atm.iv * 100
        return 0.0


# Singleton
_fetcher: Optional[OptionsChainFetcher] = None


def two_sided(c) -> bool:
    """🔴 ZBID.1 (r186, shared with otv4) — A CONTRACT WITH NO BID IS NOT A
    LIVE QUOTE. `mark` is the ask when the bid is 0 (the fetch above), so a
    no-bid contract carries its whole ask as its mark and cleared every
    `mark > 0.05` floor. AAL 2026-10-02: VOLT bought P11.5 at delta -0.0009,
    bid 0.00 / ask 0.22, three times, -3,128. The single-contract debit
    selectors require this as well as the floor; gamma_leverage_pick already
    refused `bid <= 0`. Spread, butterfly and condor legs keep their own rules.
    """
    try:
        return float(getattr(c, "bid", 0) or 0) > 0 and float(getattr(c, "ask", 0) or 0) > 0
    except (TypeError, ValueError):
        return False


def chain_increment(contracts, pin: float, default: float = 1.0) -> float:
    """The symbol's ACTUAL strike ladder near `pin`, read off the chain.

    🔑 LADR.1 (r185, shared with otv4) — MOVED HERE VERBATIM from
    strategy/gex_pin_butterfly._chain_increment (r198), which is now an alias,
    so the ladder is read in ONE place. `pin` is any price the ladder is
    wanted near. config.STRIKE_INCREMENTS stays as the fallback `default`
    and as the tradeable list; 18 of its entries disagree with the real
    near-money ladder (measured 2026-09-29), which is why the chain wins.

    🔴 r198 — `config.STRIKE_INCREMENT` IS ONE GLOBAL NUMBER FOR FIFTEEN
    SYMBOLS, and `round_to_strike()` returns an **int**, so every wing was
    quantised to whole dollars whatever the symbol actually lists. Measured
    2026-08-31: PLTR pin 190, EM 3.25 -> wing 1 -> legs at 189/191 on a $2.50
    ladder; AMD pin 472.5 -> legs at 470.5/474.5. Neither pair exists, so
    `_exact()` correctly refused — for 242 and 243 MINUTES respectively, on
    both boxes, all session.

    🔑 THE APEX WAS NEVER THE PROBLEM. PLTR's 190 and AMD's 472.5 are listed
    strikes; `_exact(pin)` would have found them. Only the WINGS were computed
    off a grid that does not exist. So this changes nothing about the apex, and
    the doctrine — *"the apex is the trade; a nearest-strike substitute is a
    different one"* — is untouched: no substitution ever reaches the apex.

    Median gap of the strikes nearest the pin. The MEDIAN, not the minimum:
    one stray half-strike listing in a $2.50 ladder would otherwise set the
    grid to 0.50 and reproduce the bug.
    """
    ks = sorted({float(c.strike) for c in (contracts or [])
                 if getattr(c, "strike", None) is not None})
    if len(ks) < 3:
        return default
    near = sorted(ks, key=lambda k: abs(k - pin))[:9]
    gaps = sorted(round(b - a, 4) for a, b in zip(sorted(near), sorted(near)[1:])
                  if b > a)
    if not gaps:
        return default
    return gaps[len(gaps) // 2] or default


def get_chain_fetcher() -> OptionsChainFetcher:
    global _fetcher
    if _fetcher is None:
        _fetcher = OptionsChainFetcher()
    return _fetcher