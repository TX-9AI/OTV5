"""
strategy/runaway_continuation.py  v5.5
v5.5  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ... (v5.0 was already spent by this file's own history, so the reset lands at v5.5.)
v5.4  2026-10-18  OTV4TEST r289 (RUN.9, MIRROR OF otv4 r492 0bd66e9) — THE FALLBACK STRIKE IS THE FIRST OTM OR NOTHING.
      gamma_leverage_pick's "else the first OTM strike" took the nearest SURVIVOR of the filters (mainline UNH
      2026-10-16 09:42: 380P at 0.07, delta 0.02, 16.5 out on a 5.23 run, x161, -$322 in 27 s). The first OTM strike
      is now the chain's own, found before any filter; if it is not a candidate nothing is picked and the caller
      DECLINEs naming the nearest strike that did pass (note= out-param). Inside the run nothing changes; the two early
      returns give 4 values. Function hunks verbatim from 0bd66e9 but for one line: `_n` is imported where it is used
      (this module never imported strategy.plan). Both callers here pass note= - the Runaway plan (its run x band) and
      the Hunt (its runway). The operator, 2026-10-17: "Yes" (to the mirror, directly).
v5.3  2026-10-03  OTV4TEST r193 (CFG.1) — its config dials are read as config.NAME with NO literal fallback; config v4.48 now defines them (they were getattr defaults on names config never had). Values unchanged.
v5.2  2026-09-26  OTV4TEST r148 (WIN.1) — reads its entry window from config with NO literal fallback (one table, config.ENTRY_WINDOWS); a missing name now fails at import instead of silently defaulting. Value unchanged.
v5.1  2026-09-13  OTV4TEST r24 — ONE PER BREAK IS READ FROM trades.db. `FINISHED_BREAKS`
      and `finish_break` are DELETED: a per-process set that a restart wiped,
      which is how 2026-09-09's 11:28 bake let the runaway re-buy a spent break
      four seconds later. `break_last_exit` derives the same fact from the rows
      that already hold it (keyed as r223 fixed: side from option_side, boundary
      from orb_range_high/low) and fails closed when the book is unreadable.
v5.0  2026-09-08  OTV4TEST r3 — THE STRATEGY IS THE SPEC; THE PLAN SELECTS
      (PLAN_SPEC §30, agreed with the operator 2026-09-08). `prepare()` moved
      to `strategy/runaway_plan.py` and grew: the trigger is the engine's own
      `fifty_accepted` latch (a close beyond the 50, held — the same event that
      now invalidates the ORB, orb_engine v4.13), strength is measured ONCE at
      acceptance from the bars since the impulsive candle (pace + acceptance,
      `analysis/trend_strength`) and frozen, and the gamma pick runs inside a
      band the strength sets (grind 0.5x / normal 1.0x / rip 1.5x the run —
      a declared prior). One per break on ANY exit; re-validation on actual
      (the 50 lost on a close, then accepted again) before the same break may
      trade again; the r179 session cap retired for this strategy. The signal
      carries `underlying_tp50` so the exit engine can HOLD while the thesis
      is true and exit when it is not. `runaway_confirmed`, `_break_key`,
      `finish_break`, `gamma_leverage_pick`, `target_delta` and the doctrine
      header stay here — the plan imports them. `prev_close` is no longer read.
v4.8  2026-09-08  r321 — DOCTRINE HEADER CORRECTED, NO BEHAVIOUR CHANGE. The
      GATE CATEGORIES block still read *"SELECTION — relaxed. cutoff 11:30 ->
      14:00"*, which r176 removed on 2026-08-29. Code and `criteria.py` were
      right; the header was stale, and §32 makes that header the thing an
      editor reads before touching the file — so it was advertising exactly the
      afternoon extension the operator had forbidden. Also states plainly what
      IS relaxed here: the R hurdle, muted, and nothing else.
v4.7  2026-08-29  r176: the 11:30 debit cutoff no longer relaxes to 14:00
      (operator: "Debit entries are finished at 1130, period … We are
      burning theta"). Also removes the afternoon slot starvation the
      extension caused — after 11:30 the dispatch slot is the credit book's.
v4.6  2026-08-28  r174 — TWO STRUCTURAL GATES, BOTH FROM THE MORNING'S TAPE
      (operator: "Yes to both, even on relaxed"):
      (1) THE FLOOR MUST CLEAR THE SPREAD. 20% of a $0.15 teenie is three
      cents — inside its own bid/ask, so the "stop" was a coin flip that
      gapped to -27%/-35%, and gain-per-dollar crowned exactly those
      contracts at the band's far edge (AMZN 270C x63 @ $0.17, GOOGL 352.5C
      x77 @ $0.14, every one dead in minutes). gamma_leverage_pick now
      REFUSES any contract whose floor (RUNAWAY_MAX_LOSS_PCT x premium) does
      not exceed its own bid/ask spread; no candidate clears -> structural
      DECLINE naming it. No new knob — the spread is the tape's own number.
      (2) ONE RUNAWAY PER BREAK. A floor stop-out FINISHES that ORB break
      for the session (same doctrine as a credit level finishing on a
      stop): trade_logger's losing-exit hook calls finish_break(); prepare
      refuses a finished (direction, boundary). A NEW break at a new
      boundary is a new trade. In-process registry; a service restart
      clears it, which is acceptable and recorded here. Both gates are
      STRUCTURAL — relaxed does not waive either.
v4.5  2026-08-27  r168 — THE RUNAWAY HAS NO UNDERLYING STOP. Operator,
      2026-08-27: *"the orb structure stop only applies to the orb. The
      runaway stop is the orb boundary — but I think that's a terrible stop
      location. I would prefer (since it's a debit), a decay or adverse
      movement amounting to a 20% loss … The runaway needs room to breathe.
      A few pullbacks in an uptrend are ok."* The floor is a 20% PREMIUM
      loss (RUNAWAY_MAX_LOSS_PCT, via signal.stop_loss_pct -> the record's
      immutable stop_premium); `underlying_stop` is NOT set, so neither the
      management plan's breach check nor the engine's structure stop can
      fire on price. r146-r167 had carried the ORB boundary as the
      invalidation — the rule the operator just retired. The plan's R now
      prices the RISK as that 20% of premium against the modelled gain over
      the run; the ORB boundary remains the origin the run is measured from.
v4.4  2026-08-27  r165 — THE PLAN PREPARES, GAMMA DOES THE HEAVY LIFTING, THE
      STRATEGY BUYS. Operator, 2026-08-27: *"the symbol did not even
      entertain coming back for a retest, it just broke out & ran. We want in
      on the move, but it needs to be over quickly … purchase and wait for
      our trailing stop"* and *"Make gamma do the heavy lifting. Try to get
      just enough OTM to really leverage gamma based on the intensity of the
      move."* `prepare()` is the plan (the sweep's v4.6 shape): dormant past
      the cutoff; each declared CONDITION with its reading (ATR reachable,
      ORB broken with a direction, 1m close beyond the 50% TP and holding);
      the contract SELECTED by `gamma_leverage_pick` — over the run price has
      already made from the ORB boundary (the move's intensity, mirrored as
      the expected continuation), every liquid OTM contract's modelled gain
      δ·run + ½γ·run² per dollar of premium, the highest leverage among
      strikes reachable within the run, else the first OTM. The delta-band
      selector (DELTA_NEAR/DEEP by ATR) is retired for selection; ATR keeps
      its one job — the reachability floor. The R hurdle stays muteable here
      (a debit, no wing to search): strict vetoes, relaxed records.
      `generate_signal()` buys the prepared contract and touches no chain.
      Stops are not encoded in this revision by the operator's instruction.
v4.3  2026-08-27  r148/r149 (RECORDED RETROACTIVELY in r165): two field-name
      defects in r146's wiring fixed — `break_direction` for the handoff
      after the engine invalidates on "runaway", and `target_50pct` (the only
      name that exists; `tp50` printed "50% TP n/a" for a session).
v4.2  2026-08-26  r146 — THE PLAN IS WIRED, AND THE SIGNAL CAN NOW TRADE.
      (1) Every refusal goes through `self.plan` (strategy/plan.py): four
      bare `return None`s that logged nothing — window, price, ATR floor,
      ORB direction, the runaway itself — now write a DECLINE row naming
      the gate. This strategy had ZERO `_gate()` call sites (handoff table).
      (2) 🔴 P0 — THE SIGNAL WAS ALWAYS INVALID. `target_delta` was written
      here and READ NOWHERE (`grep target_delta` — one writer, zero readers,
      the r97 sweep defect exactly). The signal carried no strike, premium or
      contract, so `OptionsSignal.is_valid`'s single-leg arm (`strike > 0 and
      entry_premium > 0`) was False on every fire and main.py logged
      `Invalid signal from RunawayContinuation` and returned. The flagship v4
      entry rule could never place a trade. The contract is now resolved
      HERE against the chain the dispatcher already passes, by the existing
      delta-nearest selector, and the plan prices the what-if off that real
      contract: stop = the ORB boundary, target = the stop distance
      mirrored, R from delta/gamma over those distances.
      (3) The R hurdle is consulted: STRICT refuses below the floor, RELAXED
      records and proceeds (strategy/criteria.py owns the switch).
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Runaway-ORB continuation: the ORB ran to its 50% TP and HELD. Buy the direction
that already proved itself.

v4.0  2026-08-19  Built at the OTV4 split. The FIRST v4 entry rule.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

────────────────────────────────────────────────────────────────────────────
THE PREMISE, AND WHY IT DOES NOT PREDICT DIRECTION
────────────────────────────────────────────────────────────────────────────
Four independent searches failed to find a directional predictor in this data:
entry-time conditions (all ambient - pre-filtered by the strategies' own gates),
recorded columns (gates or empty), opening-candle bias (a coin, forward-only,
797 sessions), and the tape harness (every surviving condition helped UP *and*
DOWN - they predict MOVEMENT, not DIRECTION). The live book agreed: **44.9%
direction accuracy on 715 trades, 95% CI [41.3%, 48.6%] - worse than a coin.**

**So this rule does not predict a direction. It observes one that has already
proven itself.** The ORB broke, ran the full 50% TP distance, and HELD there.
The move is not a forecast; it is in evidence. That is the same reason ORB
itself is the one v3 strategy with a positive record - break-and-retest geometry
is self-validating and consults no label.

whole point of v4.

────────────────────────────────────────────────────────────────────────────
EVERY THRESHOLD BELOW WAS MEASURED, NOT CHOSEN
────────────────────────────────────────────────────────────────────────────
**ATR GATE - the hardest rule here.** `tests/magnitude_estimator.py`, 52,949
bars over 28 dates, scored against the required move from
`tests/chain_feasibility.py` (110,162 contract observations, round-trip spread
included):

    ATR%        0.20-0.35 delta reachable within 90 bars
    < 0.03           0%      <- 2,200 bars, not one reached it
    0.03-0.05        1%
    0.05-0.08       11%
    0.08-0.12       30%
    0.12-0.20       60%
    > 0.20          92%

⚠️ **BELOW 0.05% ATR NO STRIKE IS REACHABLE AT ALL.** The move needed to clear
the spread does not occur - not rarely, NOT AT ALL across 5,517 bars. A long
directional trade in that tape cannot pay no matter how good the entry is, and
this is the likeliest explanation for v3's finding that **82% of
directionally-CORRECT continuation entries never reached +25% MFE.** They were
fired into tape that could not pay them.

**ADX IS NOT USED, AND THAT IS A MEASUREMENT.** Every ADX band from 0-15 to
40-100 produced the SAME median excursion (0.69%-0.74%) and identical strike
reachability. **ADX 45 reaches no further than ADX 12.** It failed as a
direction predictor AND as a magnitude predictor. ATR is monotone across the
same bars - 0.19% -> 0.28% -> 0.43% -> 0.60% -> 1.07%, a 5.6x spread.

**EXIT IS THE TRAILING STOP. BOS IS NOT USED**, and that is measured too:
    orb_trail_stop      85 trades   96% win   +$30,696   worst  -$16
    bos_exit           217 trades   34% win    -$7,085   worst -$735
BOS carries the single largest loss in the v3 book. The trail's worst case
across 85 trades is sixteen dollars.

⚠️ AND THE FLOOR IS WHERE THE MONEY WENT. ORB's `hard_stop_` - 15 trades,
**-$8,757** - is nearly a third of the trail's gains, lost on trades where the
trail NEVER ENGAGED. Fleet-wide `max_loss_floor` was 76 trades and -$28,179.
**Trails make money; floors lose it.** Anything that delays the trail arming is
a defect, not a conservatism.

════════════════════════════════════════════════════════════════════════════
GATE CATEGORIES — required by WA §36. Only SELECTION is ever relaxed.
════════════════════════════════════════════════════════════════════════════
**FOUNDATIONAL — never relaxed.**
  · the ORB ran to its 50% TP and **HELD** it - a 1m CLOSE beyond, still on the
    right side at the next tick. **This is the entire premise: the move is in
    EVIDENCE, not forecast.** Without it there is no runaway, only an ORB and a
    guess - and a guess is what four independent searches found no basis for.
  · direction comes from the ORB state, never from a prediction.

**SELECTION — and NOTHING here relaxes.**
  · the 11:30 cutoff is the only SELECTION gate this strategy has, and r176
    removed its relaxation. Operator, 2026-08-29: *"Debit entries are finished
    at 1130, period. Do not extend it for relaxed. We are burning theta."*
    🔴 THIS BLOCK SAID `cutoff 11:30 -> 14:00` UNTIL r321 — r176 changed the
    code and the criteria table and left the doctrine header describing the
    behaviour it had just removed, so the one document §32 requires an editor
    to read first was telling them the debit window extends to 14:00.
  · **THE ONLY THING RELAXED CHANGES ON THIS TRADE IS THE R HURDLE**, which is
    MUTED: `r_verdict` records the value and does not gate. Everything else —
    trigger, direction, ATR floor, the ATR→delta map, and both r174 teenie
    gates — is identical in both modes.

**FEASIBILITY — never relaxed.**
  · the ATR floor. Below **0.05% ATR the required move was reached on 0% of
    5,517 measured bars** - not rarely, not once. A trade fired there cannot pay
    regardless of entry quality, teaches nothing about stops, and only adds
    noise to the log the relaxed mode exists to read.
  · the ATR->delta map itself. A strike the tape cannot reach is not a cheaper
    trade, it is a lottery ticket.
"""

import logging
from typing import Optional

import config
from strategy import relaxed
from utils.math_utils import safe_float
from strategy.base_strategy import OptionsSignal as Signal

logger = logging.getLogger(__name__)

# ── measured thresholds. Overridable via config so they can be retuned without
#    will drift. A constant in strategy code is a constant nobody revisits.
ATR_FLOOR_PCT = config.RUNAWAY_ATR_FLOOR_PCT
ATR_HARD_VETO_PCT = config.RUNAWAY_ATR_VETO_PCT
ATR_DEEP_PCT = config.RUNAWAY_ATR_DEEP_PCT
CUTOFF_ET = config.RUNAWAY_CUTOFF_ET          # r148: no literal fallback

# ATR -> target delta. From the reachability table above: at 0.12%+ the tape
# reaches 0.20-0.35 on 60% of bars; at 0.20%+ it reaches 0.35-0.50 on 85%.
DELTA_NEAR = config.RUNAWAY_DELTA_NEAR
DELTA_DEEP = config.RUNAWAY_DELTA_DEEP

# ── GATE CATEGORIES AS DATA (WA §36) ───────────────────────────────────────
GATES = {
    "CUTOFF_ET":          "SELECTION",
    # FEASIBILITY - below 0.05% ATR the required move was reached on 0% of
    # 5,517 measured bars. Not rarely. Not once.
    "ATR_FLOOR_PCT":      "FEASIBILITY",
    "ATR_HARD_VETO_PCT":  "FEASIBILITY",
    "ATR_DEEP_PCT":       "FEASIBILITY",
    # r165: DELTA_NEAR/DEEP no longer select the strike — gamma leverage over
    # the move's own run does. Kept as the recorded prior band; not read by
    # the plan. ATR_DEEP_PCT likewise only feeds that retired band.
    "DELTA_NEAR":         "FEASIBILITY",
    "DELTA_DEEP":         "FEASIBILITY",
    # FOUNDATIONAL: the 50% TP HELD, and direction taken from the ORB state.
    # ⚠️ A GATE CAN BE PERFECTLY WINNABLE AND STILL BE FOUNDATIONAL - relaxing
    # the held TP would produce plenty of fills, every one an ORB plus a guess.
    # Tested inline, with no knob.
}


def target_delta(atr_pct: float) -> Optional[float]:
    """Which strike can this tape actually reach? None means DO NOT TRADE.

    ⚠️ RETURNING None IS A REAL ANSWER, NOT A FAILURE PATH. In quiet tape the
    honest output is that no strike is reachable and the trade should not fire.
    v3 had no such concept and fired into 0.03% ATR sessions where the required
    move occurred on 0% of bars.
    """
    # ⚠️ COERCE FIRST. A NaN falls through EVERY `<` test - the stress test
    # found this returning 0.25 on `target_delta(nan)`, i.e. the feasibility
    # veto INVERTING and admitting a trade into tape where 0 of 5,517 bars
    # reached the required move.
    atr_pct = safe_float(atr_pct)
    # ⚠️ FINITE IS NOT SANE. 1e12 passes every type guard and is an absurd
    # claim about the tape. The measured ATR range across 52,949 bars was
    # 0.02%-0.60%; anything past a few percent is a data fault, not a
    # volatile session, and must not select a strike.
    if atr_pct is None or atr_pct <= 0 or atr_pct > 25.0:
        return None
    if atr_pct < ATR_HARD_VETO_PCT or atr_pct < ATR_FLOOR_PCT:
        return None
    return DELTA_DEEP if atr_pct >= ATR_DEEP_PCT else DELTA_NEAR


def runaway_confirmed(orb, price_now: float, prev_close: float,
                      direction: str) -> bool:
    """Did the 1m bar CLOSE beyond the 50% TP and hold at the next tick?

    Operator's spec, 2026-08-19: *"Broke it on a 1-minute candle close, still on
    the right side after the next tick."*

    ⚠️ THE CLOSE IS THE POINT. A wick through the level is a touch, not a
    decision - v3's own liquidity doctrine says so and its sweep detection was
    built on exactly that distinction. Requiring the CLOSE beyond, plus one tick
    still on the right side, rejects the wick-and-fail without waiting for a
    confirmation bar that costs 60 seconds of a move already in progress.
    """
    # 🔴 `target_50pct` — THE ONLY NAME THAT EXISTS (r149). The strategy asked
    # for `tp50` and `underlying_tp50`; NEITHER is a field on the ORB dataclass
    # (orb_engine.py:311 declares `target_50pct`, set at 1043/1064). Both
    # getattr calls returned None, so this function's `if not tp50` guard
    # refused EVERY runaway — the plan row read "no 1m close beyond the 50% TP
    # n/a", and `n/a` was the tell: the level was never read, not never crossed.
    # ⚠️ MEASURED: 2026-08-27, eight boxes sat on INVALIDATED/runaway through
    # the open (AMZN CRM CVX GOOGL META NFLX PLTR TSLA) and every one declined
    # here. r148 unblocked the direction lookup two lines up and this refused
    # them at the very next gate — the SAME defect twice in one function.
    # ⚠️ NO FALLBACK NAMES. `tp50`/`underlying_tp50` exist on NOTHING; keeping
    # them as a chain leaves the ghost in the file for the next reader to copy,
    # and check_attr_fidelity flags them. One name, the real one.
    tp50 = getattr(orb, "target_50pct", None)
    if not tp50 or not prev_close or not price_now:
        return False
    if direction == "long":
        return prev_close > tp50 and price_now > tp50
    return prev_close < tp50 and price_now < tp50


# ── ONE RUNAWAY PER BREAK (r174) — READ FROM THE BOOK (OTV4TEST r24) ──────
# 🔴 THE OPERATOR'S RULE (2026-09-13, DEC.1): *"I don't want anything that our
# trades decide on to only live in memory… They already traded should already
# survive a restart if it's in the trade log."* This was `FINISHED_BREAKS`, a
# per-process set, and a restart wiped it: 2026-09-09 11:28:13 ET a bake, and
# 4 s later the runaway re-bought a spent break — a long at 714.71, 3.66 below
# its own 50, R 9.97, 24 contracts. The break had traded at 10:46; the fact was
# in `trades.db` the whole time.
# 🔑 NOW DERIVED, NOT MIRRORED: a runaway row today on this side and boundary IS
# the finished break. Nothing is written anywhere to remember it — so a
# restart, a bake, or a second process cannot disagree with the book.
# ⚠️ KEYED EXACTLY AS r223 FIXED IT: direction from `option_side` (a call is a
# long break, a put a short one — `direction` is a column nothing writes), the
# boundary from `orb_range_high`/`orb_range_low`, rounded to the cent.


def _break_key(direction: str, boundary) -> tuple:
    try:
        return (str(direction), round(float(boundary), 2))
    except (TypeError, ValueError):
        return (str(direction), None)


def break_last_exit(direction: str, boundary, session_date=None):
    """What `trades.db` says about THIS break today. NEVER raises.

      None          — no runaway has traded this break today: it may trade
      "open"        — a runaway on this break is still open
      "unreadable"  — the book could not be read; callers FAIL CLOSED
      float         — the latest EXIT of a runaway on this break (UTC epoch)

    ANY exit counts — a win finishes the break as surely as a stop (v4.12's
    rule, unchanged here; only where the fact lives has changed).
    """
    from datetime import datetime, timedelta
    try:
        from zoneinfo import ZoneInfo
        _et, _utc = ZoneInfo("America/New_York"), ZoneInfo("UTC")
        day = session_date or datetime.now(_et).date()
        bnd = round(float(boundary), 2)
        lo = (datetime.combine(day, datetime.min.time(), _et)
              - timedelta(hours=1)).astimezone(_utc).isoformat()
        from database.trade_logger import get_trade_logger
        conn = get_trade_logger()._connect()
        try:
            rows = conn.execute(
                "SELECT entry_time, exit_time, status, option_side, orb_range_high, "
                "orb_range_low FROM trades WHERE strategy='RunawayContinuation' "
                "AND entry_time >= ?", (lo,)).fetchall()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[runaway] break status unreadable from trades.db (%s) — "
                       "failing closed", exc)
        return "unreadable"
    last = None
    for et_, xt, status, side, hi, lo_ in rows:
        sd = str(side or "").lower()
        d = "long" if sd.startswith("c") else ("short" if sd.startswith("p") else "")
        if not d or (hi if d == "long" else lo_) is None:
            # ⚠️ NAMED, NEVER SILENT (r223's lesson): a runaway row that cannot be
            # keyed cannot finish its break, so another entry is possible.
            logger.warning("[runaway] a runaway row today has option_side=%r / boundary=%r — "
                           "it CANNOT key a break, so that break is NOT finished", side,
                           hi if d == "long" else lo_)
            continue
        if d != direction:
            continue
        b = hi if d == "long" else lo_
        try:
            if b is None or round(float(b), 2) != bnd:
                continue
            if datetime.fromisoformat(str(et_)).astimezone(_et).date() != day:
                continue
        except (TypeError, ValueError):
            continue
        if not xt:
            return "open"
        try:
            ts = datetime.fromisoformat(str(xt)).timestamp()
        except ValueError:
            continue
        last = ts if last is None else max(last, ts)
    return last


def gamma_leverage_pick(contracts, direction: str, spot: float, run: float,
                        floor_pct: float = 0.20, note: Optional[list] = None):
    """THE STRIKE GAMMA PAYS MOST OVER THE MOVE'S OWN INTENSITY.

    Operator, 2026-08-27: *"Make gamma do the heavy lifting. Try to get just
    enough OTM to really leverage gamma based on the intensity of the move."*

    `run` is the distance price has ALREADY travelled from the ORB boundary —
    the move that proved itself — and is taken as the distance it is expected
    to keep travelling (mirrored, no fitted multiple). For every liquid OTM
    contract on the side of the move, the modelled gain over `run` is
        gain = δ·run + ½·γ·run²
    and the score is gain per dollar of premium — the leverage. The winner is
    the highest leverage among strikes REACHABLE within `run`
    (strike − spot ≤ run, "just enough OTM"); if the increments leave nothing
    inside that band, the first OTM strike. Ties go to the nearer strike.

    r492 / RUN.9 — "the first OTM strike" is the nearest OTM strike OF THE
    CHAIN, found before any filter. If that strike is not itself a candidate
    (it fails the premium, delta or spread floor) there is NO fallback: the
    nearest SURVIVOR can sit many strikes out, past every strike this function
    just ruled untradeable (UNH 2026-10-16: 380P at 0.07, delta 0.02, 16.5 out
    on a 5.23 run, x161, -$322 in 27 s). `note`, when given, receives the
    refusal's reason. Selection inside the run is unchanged.

    Returns (contract, score, candidates_considered, spread_rejected), or
    (None, 0.0, n, spread_rejected) when nothing is picked.
    ⚠️ Reads only fields that exist on OptionContract: strike, mark, ask,
    delta, gamma (check_attr_fidelity, r150).
    """
    try:
        spot = float(spot)
        run = abs(float(run))
    except (TypeError, ValueError):
        return None, 0.0, 0, 0
    if run <= 0:
        return None, 0.0, 0, 0
    cands = []
    spread_rejected = 0
    first_otm, first_dist = None, None      # r492 — the chain's own nearest OTM, unfiltered
    for c in contracts or []:
        try:
            k = float(c.strike)
            prem = float(getattr(c, "ask", 0) or 0) or float(getattr(c, "mark", 0) or 0)
            bid = float(getattr(c, "bid", 0) or 0)
            d = abs(float(getattr(c, "delta", 0) or 0))
            g = float(getattr(c, "gamma", 0) or 0)
        except (TypeError, ValueError, AttributeError):
            continue
        otm = (k > spot) if direction == "long" else (k < spot)
        if otm and (first_dist is None or abs(k - spot) < first_dist):
            first_otm, first_dist = c, abs(k - spot)
        if not otm or prem <= 0.05 or d <= 0:
            continue
        # r174 — THE FLOOR MUST CLEAR THE SPREAD. A stop narrower than the
        # bid/ask is not a stop; it is the next mark wobble, and it gaps.
        # This is what removes the teenies the leverage score would crown.
        if bid <= 0 or (floor_pct * prem) <= (prem - bid):
            spread_rejected += 1
            continue
        dist = abs(k - spot)
        gain = d * run + 0.5 * g * run * run
        cands.append((gain / prem, -dist, dist, c))
    if not cands:
        return None, 0.0, 0, spread_rejected
    inside = [x for x in cands if x[2] <= run]
    if inside:
        pool = inside
    else:
        # r492 / RUN.9 — the fallback is the chain's first OTM strike or nothing.
        pool = [x for x in cands if x[3] is first_otm]
        if not pool:
            from strategy.plan import _n        # r289: imported where used (this module never imported plan)
            near = min(cands, key=lambda x: x[2])
            if note is not None:
                note.append(
                    f"no strike within the {run:.2f} run clears its floors; the first OTM "
                    f"{_n(getattr(first_otm, 'strike', None))} does not either, and the "
                    f"nearest that does is {_n(getattr(near[3], 'strike', None))} "
                    f"({near[2]:.2f} out) - not reachable, not traded")
            return None, 0.0, len(cands), spread_rejected
    best = max(pool, key=lambda x: (x[0], x[1]))
    return best[3], best[0], len(cands), spread_rejected



class RunawayContinuationStrategy:
    """THE SPEC (PLAN_SPEC §30). Fire when every bar the plan reports is met,
    with the plan's variables. Selects nothing.

    OTV4TEST r3 — the bars, read off `prep` from `strategy/runaway_plan.py`:
      1. the 50% level ACCEPTED — a 1m close beyond it, held (the engine's latch)
      2. this break not finished (one per break, any exit) or re-validated on
         actual (the 50 lost on a close, then accepted again)
      3. the tape can reach a strike (ATR floor — FEASIBILITY, kept by ruling)
      4. a contract whose floor clears its own spread, inside the strength band
      5. R (strict only; muted under relaxed through 09-11)
    Exits (exit_engine v4.12 — the runaway shares the ORB evaluator):
      hard close → REJECTED handoff → the 50 lost on a close (thesis dead) →
      fizzle → trail → theta bleed → structure backstop (a close through the
      boundary). No premium stop: HOLD while the entry condition is true.
    """
    name = "RunawayContinuation"
    MAX_LOSS_PCT = float(getattr(config, "RUNAWAY_MAX_LOSS_PCT", 0.20))

    def __init__(self):
        from strategy.runaway_plan import RunawayPlan      # lazy: it imports this module
        self.plan = RunawayPlan()
        self.planner = self.plan.planner                    # same object, as before
        self.PLAN_CHECKS = self.plan.PLAN_CHECKS

    def prepare(self, *, orb, atr_pct, price_now, now_et, chain=None, df_1m=None,
                **_ignored):
        """Kept for callers that ask the strategy for its preparation; the
        plan owns it (WA C.1: one owner)."""
        return self.plan.prepare(orb=orb, atr_pct=atr_pct, price_now=price_now,
                                 now_et=now_et, chain=chain, df_1m=df_1m)

    def generate_signal(self, *, orb, atr_pct: float, price_now: float, now_et: str,
                        chain=None, df_1m=None, **_ignored) -> Optional[Signal]:
        prep = self.plan.prepare(orb=orb, atr_pct=atr_pct, price_now=price_now,
                                 now_et=now_et, chain=chain, df_1m=df_1m)
        if not prep.ready or prep.unmet or prep.structural or prep.starved:
            return prep.tick.already()
        price_now = safe_float(price_now)
        c = prep.contract
        sig = Signal(
            strategy_name=self.name,
            setup_type="runaway_continuation",
            direction=prep.direction,
            option_side=prep.side,
            underlying_entry=price_now,
            underlying_target=(price_now + prep.run if prep.direction == "long"
                               else price_now - prep.run),
            underlying_tp50=prep.tp50,                 # the thesis: HOLD while beyond it
            stop_loss_pct=self.MAX_LOSS_PCT,           # recorded; the exit engine HOLDS
            orb_range_high=getattr(orb, "orb_high", 0.0),
            orb_range_low=getattr(orb, "orb_low", 0.0),
            strike=c.strike,
            expiry=getattr(c, "expiry", ""),
            entry_premium=c.mark,
            contract=c,
        )
        sig.gamma_leverage = prep.leverage
        sig.run_at_entry = prep.run
        sig.atr_pct_at_entry = atr_pct
        sig.strength_at_entry = prep.strength
        sig.strength_pace = prep.pace
        sig.strength_acceptance = prep.acceptance
        sig.strength_band = prep.band
        sig.disarms_retest = True
        relaxed.tag(sig)
        logger.info("[runaway] FIRE %s — %s  (no price stop; the 50 is the thesis)",
                    prep.direction, prep.trade_line())
        return prep.tick.take(sig)
