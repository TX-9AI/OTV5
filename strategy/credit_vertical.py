"""
strategy/credit_vertical.py  v4.5
v4.5  2026-10-11  OTV4TEST r268 (mirror of otv4 r478) / DEP.12 — bars_left() moves its close to the day's bell
      (utils/time_utils.close_anchored): the condor's horizon is 12:45 on a 13:00
      close, so POP is not computed on three hours that do not exist.
v4.4  2026-09-03  r234 — `search_wing` RETURNS A NAMEDTUPLE AND IS
      BRACKETED FROM BOTH ENDS. r219 added a fifth value and MISSED two guard
      returns still returning four; both callers unpacked five, so a short leg
      with no bid raised ValueError into `_safe_strategy` and read as a clean
      DECLINE. `WingResult` makes that unrepresentable. And the search now has
      a NARROW-side bound — `stop_survivable` — because R rises as the wing
      narrows while the stop narrows with it, so a selector that only
      maximises R optimises INTO the least survivable structure (r208 C.43,
      found in the butterfly and never carried here). `why_key` names which
      rung refused, as a FIELD rather than prose a caller would sniff.
v4.3  2026-09-02  r219 — 🔴 THE ENTRY AND THE MARK WERE ON DIFFERENT SIDES OF THE QUOTE.
      `search_wing` priced the credit as short.BID - long.ASK and that number
      became `sig.entry_premium` — the position's entry of record — while
      `position_manager._fetch_current_premium` marks a credit vertical at
      short.MARK - long.MARK. The gap is BOTH HALF-SPREADS, present the
      instant the position opens, and for a credit vertical a higher mark is a
      LOSS. Measured on the fleet's shape: judged $0.37, booked $0.97, gap
      $0.60 — against a lone stop carrying 60.5 cents of room. The position
      was born at its stop.
      🔑 SWEEP FORENSICS 2026-08-25..09-02 SAYS THE UNDERLYING NEVER DID IT:
      38 of 41 stopped, price NEVER reached the short strike on any of 22
      measurable trades, and moved 0.63 points toward it — implying a spread
      delta of 0.96, which a 5-wide cannot carry.
      ⚠️ OPERATOR RULING 2026-09-02: "I have a ladder for live offers, all
      paper needs to fill at mark, period." The MARK is booked. The BID/ASK
      credit is kept for the R hurdle — deciding on the conservative number
      and booking the mark refuses trades that only clear R when priced
      optimistically, so the error runs in the safe direction.
      ⚠️ AND THE OLD BEHAVIOUR HAD A PASSING TEST: check_plan_prepares S2
      asserted net_credit == 1.30, the bid/ask figure, so the suite certified
      the mismatch. Re-derived to 1.33.
v4.2  2026-08-28  r175: pop_drift() — POP with the session's measured drift,
      signed toward safety, horizon-bounded (operator: "You have to get it
      firing in ESPECIALLY this type of day … A trend day we should be
      killing it & on chop we stay out"). TCS only; pop() unchanged for the
      mean-reversion trades, whose premise is not a drift.
Credit vertical construction, liquidity and POP helpers.

v4.1  2026-08-27  r157 (RECORDED RETROACTIVELY in r159 — r157 added
      `search_wing()` here with no title bump and no entry). `search_wing`
      prices every listed strike beyond the short on BID/ASK and returns the
      highest-R wing; the caller compares it to `r_floor` — R is a
      construction target, not a filter. Shared by all four credit strategies.
v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

strategy/credit_vertical.py — options_trader_v3 — (TCS.1)
SWALLOW T1: this file's silent handler(s) now announce
        themselves once. Behaviour unchanged in every case; only the silence
        was the defect.
SELECTION MATH SHARED BY EVERY CREDIT VERTICAL. OWNED BY NEITHER STRATEGY.
⚠️ WHY THIS MODULE EXISTS, and it is not tidiness.
`TrendCreditSpread` was built inside `IronCondorStrategy`'s plumbing: it borrowed
six `CONDOR_*` constants, five of its methods, set `is_iron_condor = True`, and
executed and exited through `_execute_condor_leg` / `_evaluate_condor_leg`. Two
consequences, one of them already paid for:
  · **CHANGING A CONDOR KNOB SILENTLY RETUNED A DIFFERENT TRADE.** `CONDOR_MIN_POP`
    governed both. Nothing said so.
  · **AND ON 2026-08-14 IT PRODUCED 108 BAD TRADES.** Because TC.6 rode the
    condor's execution path, its identity had to survive as a FLAG on the record
    (`is_trend_credit`) — and when `_execute_condor_leg` hardcoded condor
    identity instead, the flag never arrived, the exit branch never fired, and
    every leg inherited the condor's ratchet and 25% premium stop. **A trade
    living inside another trade's plumbing fails the moment one hop drops a
    field.**
So the math both trades genuinely share lives HERE, imported by both, owned by
neither. Each strategy keeps its OWN constants, so a knob change reaches exactly
the trade it names.
⚠️ **VALUES ARE UNCHANGED BY THIS MOVE.** Every function is lifted verbatim from
`IronCondorStrategy`; the TCS_* defaults equal the CONDOR_* values they replace.
This is a de-coupling, not a re-tune — behaviour must be provably identical, and
a test asserts the defaults still match.
"""

import logging
import math
from typing import List, NamedTuple, Optional, Sequence

from utils.math_utils import safe_float

logger = logging.getLogger(__name__)


# ── SWALLOW T1 REVIEW, 2026-08-17 ────────────────────────────────────────────
# The three handlers below were flagged as silent. **All three FAIL CLOSED and
# their behaviour is correct**: an unreadable quote ranks worst (9.99), fails
# `quote_ok`, or scores POP 0.0 — every path ends in "do not select this
# contract". None of them can grant permission.
# They are noisy-once now because a SYSTEMATIC quote problem would otherwise be
# indistinguishable from a genuinely illiquid chain: every contract silently
# ranked 9.99 looks exactly like a chain with no liquidity, and the strategy
# would simply stop trading with nothing to read.
_WARNED_CV: set = set()


def _cv_warn(where: str, exc: Exception) -> None:
    """Once per site per process. Fail-closed is the behaviour; silence is not."""
    if where in _WARNED_CV:
        return
    _WARNED_CV.add(where)
    logger.warning(
        "[cv] %s could not evaluate a contract (%s) - FAILING CLOSED, this "
        "contract will not be selected. If this repeats across the chain the "
        "quote source is the problem, not the liquidity.", where, exc)


def liquidity_rank(c) -> tuple:
    """Rank key for "most liquid". LOWER IS BETTER.

    BID/ASK WIDTH FIRST, because it is the only liquidity signal that is
    actually populated: `factor_sweep` found `open_interest` and `volume`
    CONSTANT across the entire joined sample, so the old `open_interest + volume`
    sum was 0 for every contract and selection fell through to its "no OI/vol
    data" branch on every call. Width is also what matters on a 0DTE credit
    spread — a nickel-wide quote is what trips a stop on quote noise rather than
    on price. Depth survives only as a tie-break and only when non-zero.
    """
    try:
        bid, ask = float(getattr(c, "bid", 0) or 0), float(getattr(c, "ask", 0) or 0)
        mid = (bid + ask) / 2.0
        width = (ask - bid) / mid if (mid > 0 and ask >= bid) else 9.99
    except Exception as exc:                                   # noqa: BLE001
        _cv_warn("liquidity_rank", exc)
        width = 9.99
    depth = (getattr(c, "open_interest", 0) or 0) + (getattr(c, "volume", 0) or 0)
    return (round(width, 4), -depth)


def quote_ok(c, max_width_pct: float) -> bool:
    """Reject a short leg quoted wider than `max_width_pct` of its mid.

    RANKING ALONE NEVER REFUSES — it returns the least-bad strike even when every
    candidate is broken. On a 0DTE credit spread a nickel of quote noise on a
    wide market moves the spread enough to trip a stop on the QUOTE rather than
    on price. Width needs a FLOOR as well as an ordering.
    """
    try:
        if max_width_pct <= 0:
            return True
        bid, ask = float(getattr(c, "bid", 0) or 0), float(getattr(c, "ask", 0) or 0)
        mid = (bid + ask) / 2.0
        if mid <= 0 or ask < bid:
            return False
        return (ask - bid) / mid <= max_width_pct
    except Exception as exc:                                   # noqa: BLE001
        _cv_warn("quote_ok", exc)
        return False


def pop(distance: float, sigma_per_bar: float, bars_left: float) -> float:
    """P(terminal close on the SAFE side of the short strike) = Phi(z).

        z = distance / (sigma * sqrt(bars_left))

    TIME IS THE POINT: the same distance is a LARGER z later in the session, so a
    strike that fails at 11:15 passes at 14:30 on identical geometry.

    Driftless and normal, deliberately — a drift term would be a forecast, and
    this system's directional forecasts do not separate. Normal understates fat
    tails, so it reads slightly OPTIMISTIC on the extremes.

    Degenerate inputs return 0.0, which FAILS any floor. **A missing ATR must
    never read as a safe trade.**
    """
    try:
        d, sig, n = float(distance), float(sigma_per_bar), float(bars_left)
        if d <= 0 or sig <= 0 or n <= 0:
            return 0.0
        z = d / (sig * math.sqrt(n))
        return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    except Exception as exc:                                   # noqa: BLE001
        _cv_warn("pop", exc)
        return 0.0


def pop_drift(distance: float, sigma_per_bar: float, bars_left: float,
              drift_per_bar: float, horizon_bars: float) -> float:
    """P(terminal close on the SAFE side) WITH the session's measured drift.

    r175, operator on TCS's fleet-wide POP drought during the 2026-08-28
    trend day: *"You have to get it firing in ESPECIALLY this type of day …
    A trend day we should be killing it & on chop we stay out."* The
    driftless pop() priced TCS's own premise at zero — the strategy believed
    the trend at the door (vote + ADX) and disbelieved it at the till.

        z = (d + mu * min(n, horizon)) / (sigma * sqrt(n))

    · mu is MEASURED from the session's own tape (realized per-bar drift),
      never a forecast someone typed. SIGNED toward safety: drift away from
      the short strike raises z; drift TOWARD it lowers z — so a reversal
      day reads WORSE than driftless, which is "on chop we stay out" with
      teeth.
    · min(n, horizon): the measured trend is trusted for a bounded horizon,
      not extrapolated to the bell. horizon is a stated baseline prior
      (TCS_DRIFT_HORIZON_BARS), not a fit.
    · mu = 0 reduces exactly to pop() — chop changes nothing.
    Degenerate inputs return 0.0: a missing ATR must never read safe.
    """
    try:
        d, sig, n = float(distance), float(sigma_per_bar), float(bars_left)
        mu, h = float(drift_per_bar), float(horizon_bars)
        if d <= 0 or sig <= 0 or n <= 0:
            return 0.0
        z = (d + mu * min(n, max(h, 0.0))) / (sig * math.sqrt(n))
        return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    except Exception as exc:                                   # noqa: BLE001
        _cv_warn("pop_drift", exc)
        return 0.0


def bars_left(now_et_dt, bar_minutes: float, close_et) -> float:
    """Bars of `bar_minutes` remaining until `close_et`.

    The caller passes the horizon. For both credit verticals that is the 15:45
    flatten, NOT the bell — the position is closed there, so using 16:00 would
    overstate T and make every POP look worse than the trade really is.
    """
    try:
        from utils.time_utils import close_anchored   # r478: the day's bell
        _c = close_anchored(close_et, now_et_dt)
        end = now_et_dt.replace(hour=_c.hour, minute=_c.minute,
                                second=0, microsecond=0)
        mins = (end - now_et_dt).total_seconds() / 60.0
        return max(0.0, mins / max(1e-9, float(bar_minutes)))
    except Exception:                                          # noqa: BLE001
        return 0.0


def find_contract_at_strike(contracts: Sequence, strike: float):
    for c in contracts or []:
        try:
            if abs(float(c.strike) - float(strike)) < 1e-6:
                return c
        except Exception:                                      # noqa: BLE001
            continue
    return None


def select_beyond_rail(contracts: List, side: str, rail: float,
                       min_distance_level: float,
                       session_extreme: Optional[float],
                       spot: float = 0.0, sigma: float = 0.0,
                       bars: float = 0.0, min_pop: float = 0.0,
                       max_width_pct: float = 0.0):
    """The short strike, or None.

    A strike qualifies only if it is ALL of:
      1. BEYOND THE RAIL           — the anchor the caller nominated
      2. BEYOND THE MIN DISTANCE   — a breathing-room floor; pass +/-inf to disable
      3. NOT EXCEEDED BY PRICE     — beyond the session extreme; pass None to disable
      4. QUOTED TIGHTLY ENOUGH     — bid/ask width within `max_width_pct`
      5. FAR ENOUGH IN TIME        — POP >= `min_pop`
    Among survivors: MOST LIQUID by bid/ask width, tie-break NEAREST the rail —
    the richest premium that still clears everything.

    ⚠️ RETURNS None RATHER THAN FALLING BACK INWARD. **No inside fallback, ever** —
    that fallback is what sold calls on top of spot for ~3 weeks.
    """
    def beyond(k, level):
        return k >= level if side == "call" else k <= level

    eligible = []
    for c in contracts or []:
        if not (getattr(c, "mark", 0) or 0) > 0.01:
            continue
        k = c.strike
        if not beyond(k, rail):
            continue
        if not beyond(k, min_distance_level):
            continue
        if session_extreme is not None and not beyond(k, session_extreme):
            continue
        if not quote_ok(c, max_width_pct):
            continue
        if min_pop > 0 and spot > 0:
            if pop(abs(k - spot), sigma, bars) < min_pop:
                continue
        eligible.append(c)

    if not eligible:
        priced = [c for c in (contracts or []) if (getattr(c, "mark", 0) or 0) > 0.01]
        logger.info(
            "credit-vertical: no %s strike clears rail %.2f / min-dist %.2f / "
            "extreme %s / POP>=%.2f — %d/%d priced. SKIP (no inside fallback).",
            side, rail, min_distance_level,
            f"{session_extreme:.2f}" if session_extreme is not None else "n/a",
            min_pop, len(priced), len(contracts or []))
        return None

    best = min(liquidity_rank(c) for c in eligible)
    cohort = [c for c in eligible
              if liquidity_rank(c)[0] <= best[0] * 1.5 + 1e-9]
    return (min(cohort, key=lambda c: c.strike) if side == "call"
            else max(cohort, key=lambda c: c.strike))


def leg_order_from_slope(slope: float, flat_eps: float):
    """(leg1, leg2) from a channel's slope, or None when it is FLAT.

    UP-sloping: price travels the LOWER rail toward the UPPER one across the
    session, so the PUT side is the one price is leaving and it fills FIRST.
    DOWN-sloping: mirrored.

    **A SIGN IS NOT A SLOPE** — below `flat_eps` the drift is noise, and ordering
    off it would be reading a coin flip as structure. None means "use proximity".
    """
    if slope is None or abs(slope) < flat_eps:
        return None
    return ("put", "call") if slope > 0 else ("call", "put")


# ═══ THE WING SEARCH — R IS A CONSTRUCTION TARGET, NOT A FILTER ═══════════
# 🔴 OPERATOR, 2026-08-27: *"strike selection must net r of 1 or better"*,
# *"make the r-value a requirement outright... and relax something else to
# loosen the entry"*, *"the integrity of the trade mechanics comes first."*
#
# ⚠️ WHAT THIS REPLACES, IN FOUR STRATEGIES: a wing at a FIXED DOLLAR WIDTH
# (`WING_WIDTH = 5.0`, `TCS_WING_WIDTH_*`, `CONDOR_WING_WIDTH_*`), with R
# checked AFTER the fact and MUTED under relaxed. Five dollars is ONE strike
# increment on SPX and SIX on CVX — which is how a 6-wide spread collecting
# $0.58 (R 0.13) looked normal to the code and was entered SEVENTEEN times in
# twelve minutes on 2026-08-27.
# ⚠️ AND THE SPX/QQQ SPLIT MEANT EVERY OTHER SYMBOL TOOK THE QQQ DEFAULT — a
# two-way branch standing in for fifteen instruments with different prices and
# different strike ladders.
#
# THE SHORT STRIKE IS STRUCTURAL: it comes from the level, the fork tine or the
# trend boundary, and never moves. The WING is the only free variable, and the
# tradeoff is monotonic — narrower wing, less credit, less risk, HIGHER R — so
# "the wing that best clears the floor" is computable and "no wing does" is a
# definite answer rather than a guess.
#
# ⚠️ BEST R, NOT FIRST TO PASS. A wider wing sometimes pays enough extra credit
# to beat a narrower one on ratio; taking the first candidate that clears would
# leave that on the table.
# ⚠️ AND `R_FLOOR` IS READ DIRECTLY, NEVER THROUGH `r_hurdle()`, which returns
# None under relaxed. Relaxed widens EVIDENCE (sweep age, pierce depth, level
# hold rate); it does not waive economics. Routing this through the hurdle
# would restore the exact hole that produced the loop.
class WingResult(NamedTuple):
    """What the wing search found. 🔴 r234 - A NAMEDTUPLE, NOT A BARE TUPLE.

    r219 added a FIFTH value and updated the success path and the no-candidate
    path - and MISSED the two guard returns, which kept returning FOUR. Both
    callers unpack five names, so a short leg with `bid <= 0` raised
    `ValueError: not enough values to unpack`, was swallowed by
    `_safe_strategy` into a clean-looking DECLINE, and recorded the strategy as
    never asked. Proven by execution at HEAD; it has never fired on the fleet
    (0 raises on 15 boxes) purely because that guard rarely trips.
    ⚠️ THE FIX IS THE SHAPE, NOT THE PATCH. Fields have defaults and callers
    read by NAME, so adding a value can never again change what a return path
    unpacks to. `_none()` gives every guard one spelling of "nothing found".
    """
    r: float = 0.0                 # credit / (width - credit) - EXPIRY basis
    long: object = None
    credit: float = 0.0            # bid/ask - the economic hurdle (r219)
    width: float = 0.0
    fill: Optional[float] = None   # mark - what gets BOOKED (r219)
    r_stop: Optional[float] = None # credit / stop distance - r234
    stop_dist: Optional[float] = None
    why: str = ""                  # why nothing qualified, when nothing did
    why_key: str = ""              # WHICH check refused - never sniffed
                                   # from the prose (§20 one level over)


def _none(why: str = "") -> WingResult:
    return WingResult(why=why)


def search_wing(contracts, short_contract, side: str, r_floor: float,
                r_floor_stop: float = None, short_bid=None, short_ask=None):
    """WingResult. Read by NAME - see the class docstring for why.

    \U0001f534 r234 - BRACKETED FROM BOTH ENDS, AND SCORED ON THE STOP.

    Prices every listed strike beyond the short on BID/ASK — never mark, because
    the credit has to be one the market would actually pay — and returns the
    highest-R candidate. The caller decides what to do when `best_r < r_floor`;
    this reports, it does not refuse.

    🔴 r219 — AND IT NOW RETURNS A SECOND CREDIT, BECAUSE THE DECISION AND THE
    FILL ARE DIFFERENT QUESTIONS AND WERE BEING ANSWERED WITH ONE NUMBER.
      · `credit`      = short.BID - long.ASK. The ECONOMIC HURDLE. R is judged
        on a credit the market would actually pay, and that is unchanged.
      · `fill_credit` = short.MARK - long.MARK. The PRICE BOOKED. Operator
        ruling, 2026-09-02: "I have a ladder for live offers, all paper needs
        to fill at mark, period."
    ⚠️ MEASURED CONSEQUENCE OF CONFLATING THEM. `entry_premium` was the bid/ask
    credit while `position_manager._fetch_current_premium` marks a credit
    vertical at `short.mark - long.mark` — two bases, differing by BOTH
    half-spreads, charged as a loss at the instant of fill. Sweep forensics,
    2026-08-25..09-02: 38 of 41 exited on the lone stop with 60.5 cents of
    room, while price NEVER reached the short strike on any of 22 measurable
    trades and moved only 0.63 points toward it — a move that implies a spread
    delta of 0.96, which a 5-wide cannot carry. The underlying never explained
    the loss; the basis mismatch did.
    ⚠️ AND THE HURDLE STAYS ON BID/ASK DELIBERATELY. Deciding on the
    conservative credit and booking at the mark refuses trades that only clear
    R when priced optimistically — the error runs in the safe direction.
    """
    try:
        k_short = float(getattr(short_contract, "strike", 0) or 0)
        bid = float(getattr(short_contract, "bid", 0.0) or 0.0)
    except (TypeError, ValueError):
        return _none("short contract strike/bid unreadable")
    if k_short <= 0 or bid <= 0:
        return _none(f"short leg has no usable bid (strike {k_short:g})")

    from strategy.criteria import (stop_distance as _stop_distance,
                                   stop_survivable, R_FLOOR_STOP)
    _floor_stop = R_FLOOR_STOP if r_floor_stop is None else r_floor_stop
    # \u26a0\ufe0f SURVIVABILITY IS MEASURED ON THE SHORT LEG'S QUOTE, which the
    # caller may already hold; falling back to the contract keeps one source.
    _sbid = safe_float(short_bid) if short_bid is not None else bid
    _sask = safe_float(short_ask) if short_ask is not None else \
        safe_float(getattr(short_contract, "ask", None))
    best, _why, _key = None, "", ""
    for c in (contracts or []):
        try:
            k = float(getattr(c, "strike", 0) or 0)
            ask = float(getattr(c, "ask", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        if k <= 0 or k == k_short:
            continue
        # the wing sits BEYOND the short: below for a put, above for a call
        if side == "put" and k >= k_short:
            continue
        if side == "call" and k <= k_short:
            continue
        width = abs(k_short - k)
        credit = max(0.0, bid - ask)
        risk = width - credit
        if credit <= 0 or risk <= 0:
            continue
        r = credit / risk
        # \U0001f534 r234 - SCORED ON THE STOP, AND BRACKETED FROM BOTH ENDS. R rises
        # as the wing narrows while the STOP narrows with it, so a selector
        # that only maximises R walks straight into the least survivable
        # structure and lets a later gate refuse it. That is r208's C.43 -
        # *"the selector does not merely allow the bad case, it OPTIMISES INTO
        # IT"* - found in the butterfly and never carried to the verticals.
        # The butterfly's own fix is the pattern: R on the wide side,
        # survivability on the narrow side.
        _sd = _stop_distance(width, credit)
        _rs = (credit / _sd) if (_sd and _sd > 0) else None
        if _rs is None:
            _why, _key = (_why or "stop distance unpriceable"), (_key or "wing")
            continue
        _ok, _svwhy = stop_survivable(_sd, _sbid, _sask)
        if not _ok:
            # \u26a0\ufe0f NAMED, NOT SILENT. "No wing qualified" and "every wing was
            # too fragile" are different answers and the caller reports which.
            _why, _key = f"narrowest wings refused: {_svwhy}", "stop_vs_spread"
            continue
        if _floor_stop is not None and _rs < _floor_stop:
            if _key != "stop_vs_spread" or _rs > 0:
                _why = f"best stop-basis R {_rs:.2f} < {_floor_stop:.2f}"
                _key = "wing_r_best"
            continue
        # \u26a0\ufe0f RANKED ON THE STOP BASIS. `r_stop = r / LONE_STOP_PCT_OF_RISK`
        # is a MONOTONE transform of `r`, so the winner is the same strike
        # either way - ranking on it changes nothing and says what it means.
        if best is None or _rs > (best.r_stop or -1.0):
            # ⚠️ THE MARK CREDIT IS CARRIED ALONGSIDE, NOT INSTEAD. It is what
            # gets BOOKED; `credit` is what gets JUDGED. If either leg has no
            # usable mark the fill credit is None and the caller must say so
            # rather than substitute the bid/ask number — that substitution is
            # the defect this return value exists to end.
            # ⚠️ `safe_float`, NOT a local `_f` — this file has no such helper
            # and inventing one is the §0.1 failure. utils.math_utils.safe_float
            # is what the rest of the tree uses and it rejects NaN, which a
            # bare float() would let through as a mark.
            _sm = safe_float(getattr(short_contract, "mark", None))
            _lm = safe_float(getattr(c, "mark", None))
            _fill = (round(max(0.0, _sm - _lm), 4)
                     if _sm is not None and _lm is not None else None)
            best = WingResult(r=round(r, 4), long=c, credit=round(credit, 4),
                              width=width, fill=_fill,
                              r_stop=round(_rs, 4), stop_dist=round(_sd, 4))
    if best is None:
        return WingResult(why=(_why or "no strike beyond the short prices a "
                                       "credit"), why_key=(_key or "wing"))
    return best
