"""
strategy/condor_roll.py  v5.1
v5.1  2026-10-27  OTV5 r44 (BAR.1) — THE CLOSED BAR IS THE LAST BAR CLOSED BY TIME. classify_tested's wick test and
      _tent_breached's close read df_1m.iloc[-2], one bar stale on a tick before the new minute's first row exists
      (META 2026-10-27 3f2b1372: a Breakout short fired 10:10:00 ET on the 10:08 bar while 10:09 had already closed back inside the 623.20 edge). Both read utils.time_utils.closed_pos(df_1m) (the clock); unchanged when the forming row is present.
      GATE tests/check_last_closed_bar.py.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.12 2026-10-20  OTV4TEST r309 (B4, MIRROR OF otv4 r495 81cc63c, WA 38.2) — the roll and the tent ask
      order_guard.clear_to_post BEFORE their first leg on LIVE (found by this tree's r495 critique,
      MSG-QQQ-1020-18): both post an OPEN (the rolled vertical; the hedge) and neither passed B2's guard
      or B4's no-entry-before-a-clean-sweep. Whole adjustment or none: a refused roll or tent touches
      NOTHING and retries next tick (operator 10-20: "Hold, retry"). The condor's stops still run: exits
      never pass through the guard. Paper unchanged. _guard_clear and both call sites verbatim from 81cc63c;
      the tent stays uncalled in this tree (v4.8 r11) and is guarded anyway.
v4.11 2026-10-04  OTV4TEST r242 (LIVE.1 B0, MIRROR OF otv4 r463 c912ce7, WA 38.2) — every Account call goes through tasty_client.sdk_result: on tastytrade 13.x the Account methods are coroutines and a bare call placed and closed NOTHING live (paper never calls them). Hunks applied verbatim from c912ce7.
v4.10 2026-10-03  OTV4TEST r230 (PREM.5) — ORCS LEGS ARE ROLLED AND TENTED LIKE ANY CONDOR'S. The operator, 2026-10-03 21:21 ET: "On rolling/defending the ORCS, adopt the condor logic verbatim." Both leg reads take every is_condor_leg record again (v4.9's skip is removed).
v4.9  2026-10-03  OTV4TEST r204 (PREM.2) — ORCS LEGS ARE NEVER ROLLED OR TENTED. Both leg reads skip strategy
      OpeningRangeCreditSpread: its spec is hold to the close (PLAN_SPEC §41.1), and an ORCS put and call
      open together would otherwise read as a formed condor and be handed to the ladder.
v4.8  2026-09-09  OTV4TEST r11 — THE ROLL MAY WIDEN ITS WING (PLAN_SPEC §35 v2).
      Operator's picture: 360/370C breached at 364 -> take the profitable put
      vertical off and SELL 360/337.5P — the short at the tested short's own
      strike (an iron butterfly), the wing widened until the credit clears the
      tested width, so any further upside cannot lose. `find_risk_free_roll`
      used a FIXED wing (the original width) and so could never reach that
      credit; it now searches wings at every candidate short and takes the
      NEAREST short with the NARROWEST wing that clears — least new risk for a
      risk-free tested side. No cap on the widening: the 15%-from-formation
      floor is the protection, and if no strike combination clears, the ladder
      is stop-and-page. Candidates include the tested short's own strike. The
      "invert" and "tent" rungs are RETIRED as separate mechanisms: the iron
      fly IS rung 1 at its limit; `_execute_tent` and friends remain in the
      file, uncalled, until the manifest port removes them.
v4.7  2026-09-09  OTV4TEST r10 — TESTED IS A WICK, NOT A DISTANCE (PLAN_SPEC §35).
      `classify_tested` reads the closed 1m bar when a frame is given: a side
      is TESTED when the bar's wick reached its short strike with the close
      still inside (wicks are tests); a close beyond is the tent's business
      (`_tent_breached`, unchanged). The one-strike proximity rule survives
      only as the fallback when no tape is passed. `check_and_execute_roll`
      takes `df_1m` and hands it through. Same grammar as every plan.
v4.6  2026-08-26  r146 — THE ROLL HAS A PLAN. `check_and_execute_roll` writes
      a `CreditRoll` row through strategy/plan.py at every decision: HOLD
      (no paired condor / already final form / neither side tested / no
      risk-free roll — with the best candidate's roll_credit, close_cost,
      credit_after and tested_width, the "economical question" the operator
      named), ROLL when executed, NO PLAN when the chain is absent. The roll
      logic is unchanged; this narrates the decision it already makes.
      Operator: *"we are already trying to find the farthest strike that
      satisfies the economical question & that is worthy of a tick by tick
      plan."*
v4.5  2026-08-24  r106 THE TENT — operator's post-roll escalation, combining his
      rungs 2 and 3: on a 1-min CLOSE beyond a short strike of an already-rolled
      structure, take the PROFITABLE side off (computed from marks, never
      assumed) and buy a long of the OPPOSITE type, equidistant from the
      remaining short as its wing — "leaving price under the tent". Priced
      BEFORE it is paid: if the hedge's debit alone breaches the 15% floor on
      cumulative credit, the tent is not built and the structure closes. The
      survivor is re-booked as Structure.TENT carrying the CUMULATIVE credit, so
      the floor measures the whole adjusted position.
v4.4  2026-08-24  r105: the roll's OPEN half walks the ladder WITHIN THIS CALL.
      It cannot walk across ticks — by the time the open runs, the old untested
      vertical is already closed, so check_and_execute_roll sees len(legs)!=2
      next tick and never re-enters; an unfilled rung would strand the position
      half-rolled with the tested side unhedged. Bounded rungs in-line, ending
      at mark (the pre-r105 price), each with a short deadline.
v4.3  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).


v4.2  2026-08-21  PHASE B (r58): the rolled record no longer wears RANGING.
Condor roll handling.

v4.1  2026-08-20  AUDIT F8: a light-filled roll no longer wears the risk-free
      label - on shortfall the ladder stays ARMED and is_broken_wing is NOT
      set; the alert states both.
v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

strategy/condor_roll.py — Broken-wing roll of a live iron condor. v1.1
AC: the missing-mark path was a SILENT return. This one
        declines a roll on a LIVE position with one side already tested — the
        roll IS the risk-reduction step, so a quiet refusal is the most
        consequential of the three silent declines. Now names which leg had no
        mark and states the position was left as-is.
paper roll credit routed through limit_ladder
        .paper_fill_credit (audit defect T): the rolled vertical applied
        PAPER_FILL_SLIPPAGE_PCT inline, one of the two credit paths that kept
        a haircut after entry_engine v3.8 dropped it for debits. One authority,
        one knob (default 0.0 = book the mark). Same 4dp precision as before;
        no live-path change.
ROLL IS REAL (audit defect P). Step 1 (close old untested
        vertical): both modes route through place_exit_order and book the
        FillResult's ACTUAL fill price — the old code booked plan.close_cost
        even when the confirmed live fill differed. Step 2 (open rolled
        vertical): a REAL signed-credit limit order is placed and
        fill-confirmed via execution/order_confirm — the old code wrote the
        DB record without placing ANY live order (a fictional position). The
        record books ONLY confirmed contracts at the broker's net credit;
        paper mirrors live friction via PAPER_FILL_SLIPPAGE_PCT. If the open
        fails after the close succeeded, position-truth is preserved (DB
        matches broker), a HALF-COMPLETE page fires, and the roll re-evaluates
        on a later tick with a fresh plan. The risk-free claim is re-checked
        against the ACTUAL fill credit and pages if the fills came in light.
FillResult adoption: the live roll-close of the untested
        vertical now goes through the confirmed-fill contract (place_exit_order
        returns FillResult); the roll aborts and leaves the position OPEN unless
        the close is broker-confirmed, instead of treating order submission as a
        completed close. No paper-path change.
initial build.
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
When BOTH condor verticals are open and price tests ONE side, a professional
adjustment is to roll the UNTESTED side toward price to collect additional
credit. If the cumulative credit collected covers the tested side's width, the
tested side becomes RISK-FREE — the structure is now a broken-wing butterfly.
Risk-free condition (the whole point):
    total_credit_collected  >=  tested_side_width
    (both in per-share terms; ×100 is the dollar figure)
    where total_credit_collected = banked_condor_credit
                                   + roll_credit (new untested vertical)
                                   - close_cost  (buying back the old untested vertical)
This module:
  1. classify_tested()      — which side is being tested, which is untested.
  2. find_risk_free_roll()  — pure premium math over live chain marks; finds the
                              smallest roll of the untested side that makes the
                              tested side risk-free (smallest roll = least new
                              risk on the rolled side).
  3. check_and_execute_roll() — orchestrator: detect, solve, and (only if a
                              risk-free roll exists) execute it, marking the
                              result a broken wing.
HARD CONTRACT: the roll is the FINAL adjustment. Once rolled, every leg is
flagged is_broken_wing=1 and this module never touches it again — it is managed
to exit only (stop / target / nickel), no further rolls.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Optional, List, Tuple

from config import STRIKE_INCREMENT, CONTRACT_MULTIPLIER
from utils.time_utils import fmt_et_short
from utils.time_utils import closed_pos as _closed_pos   # r44 (BAR.1): the last CLOSED bar, by time
from strategy.plan import Plan

logger = logging.getLogger(__name__)

# The roll's informer — management, not entry. Verdicts HOLD / ROLL / NO PLAN.
_ROLL_PLAN = Plan("CreditRoll", ("legs", "final_form", "tested", "roll_credit",
                                 "close_cost", "credit_after", "tested_width",
                                 "risk_free"), self_ledgers=True)


@dataclass
class RollPlan:
    tested_side:        str    # "call" or "put" — the threatened side (goes risk-free)
    untested_side:      str    # the side we roll toward price
    new_short_strike:   float
    new_long_strike:    float
    new_short_symbol:   str
    new_long_symbol:    str
    roll_credit:        float  # per-share credit of the new untested vertical
    close_cost:         float  # per-share debit to buy back the old untested vertical
    total_credit_after: float  # cumulative per-share credit after the roll
    tested_width:       float
    risk_free:          bool
    contracts:          int


def _mark_at(contracts, strike: float) -> Optional[float]:
    return next((c.mark for c in contracts if c.strike == strike and c.mark > 0), None)


def _contract_at(contracts, strike: float):
    return next((c for c in contracts if c.strike == strike and c.mark > 0), None)


def classify_tested(legs: List[dict], current_price: float,
                    proximity_strikes: int = 1, df_1m=None) -> Tuple[Optional[dict], Optional[dict]]:
    """Return (tested_leg, untested_leg). v4.7: with a frame, a side is TESTED
    when the closed bar's wick reached its short strike and the close stayed
    inside (wicks are tests); a close beyond is breached, not tested. Without
    a frame, the old proximity rule."""
    call_leg = next((l for l in legs if l.get("option_side") == "call"), None)
    put_leg  = next((l for l in legs if l.get("option_side") == "put"),  None)
    if not (call_leg and put_leg):
        return None, None

    try:
        if df_1m is not None and len(df_1m) >= 2:
            bar = df_1m.iloc[_closed_pos(df_1m)]                # r44 (BAR.1): by time, was iloc[-2]
            hi, lo, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
            ck, pk = float(call_leg["short_strike"]), float(put_leg["short_strike"])
            if hi >= ck and close <= ck:
                return call_leg, put_leg
            if lo <= pk and close >= pk:
                return put_leg, call_leg
            return None, None
    except Exception:                                           # noqa: BLE001
        pass

    prox = proximity_strikes * STRIKE_INCREMENT
    if current_price >= call_leg["short_strike"] - prox:
        return call_leg, put_leg      # call tested, put untested
    if current_price <= put_leg["short_strike"] + prox:
        return put_leg, call_leg      # put tested, call untested
    return None, None


def find_risk_free_roll(tested_leg: dict, untested_leg: dict, chain,
                        current_price: float,
                        banked_credit: float) -> Optional[RollPlan]:
    """Solve for the smallest roll of the untested side that makes the tested
    side risk-free. Returns the best RollPlan found (risk_free flag set), or
    None if the chain can't be priced."""
    tested_side   = tested_leg["option_side"]
    untested_side = untested_leg["option_side"]
    tested_width  = float(tested_leg["spread_width"])
    wing          = float(untested_leg["spread_width"])
    contracts     = int(untested_leg.get("contracts", 1))

    u_list = chain.puts if untested_side == "put" else chain.calls

    # Cost to buy back the existing (cheap, far-OTM) untested vertical.
    old_short_m = _mark_at(u_list, untested_leg["short_strike"])
    old_long_m  = _mark_at(u_list, untested_leg["long_strike"])
    if old_short_m is None or old_long_m is None:
        # AC 2026-07-31 — was a SILENT return. This refuses a roll on a LIVE
        # position with one side tested: the roll is the risk-reduction step,
        # so declining it quietly is the worst of the three silent declines.
        _missing = ("short" if old_short_m is None else "") + \
                   ("/long" if old_long_m is None else "")
        logger.info(
            f"Condor roll SKIPPED: no mark for the untested {untested_side} "
            f"vertical ({_missing.strip('/')} leg) — strikes "
            f"{untested_leg['short_strike']:g}/{untested_leg['long_strike']:g}, "
            f"{len(u_list)} contracts in chain. Position left as-is."
        )
        return None
    close_cost = max(old_short_m - old_long_m, 0.0)

    # Candidate short strikes for the rolled vertical, marching from the current
    # short strike TOWARD price (roll up for puts, down for calls). Smallest roll
    # that reaches risk-free wins → least new risk on the rolled side.
    inc = STRIKE_INCREMENT
    candidates: List[float] = []
    if untested_side == "put":
        k = untested_leg["short_strike"] + inc
        while k <= current_price:
            candidates.append(k); k += inc
    else:  # call side rolled down toward price
        k = untested_leg["short_strike"] - inc
        while k >= current_price:
            candidates.append(k); k -= inc

    # v4.8 — the tested short's own strike is a candidate (shared body)
    _tk = float(tested_leg.get("short_strike") or 0.0)
    if _tk > 0 and _tk not in candidates:
        if (untested_side == "put" and _tk <= current_price) or (untested_side == "call" and _tk >= current_price):
            candidates.append(_tk)
            candidates.sort(reverse=(untested_side == "put"))
            candidates.sort(key=lambda k: abs(k - float(untested_leg["short_strike"])))
    # v4.8 — the wings to try at each short: the original width first, then wider
    _listed = sorted({float(getattr(c, "strike", 0) or 0) for c in u_list} - {0.0})
    best: Optional[RollPlan] = None
    for new_short in candidates:
        if untested_side == "put":
            wings = [new_short - k for k in _listed if k < new_short]
        else:
            wings = [k - new_short for k in _listed if k > new_short]
        wings = sorted(w for w in wings if w >= wing) or [wing]
        for _w in wings:
            new_long = new_short - _w if untested_side == "put" else new_short + _w
            ns = _contract_at(u_list, new_short)
            nl = _contract_at(u_list, new_long)
            if ns is None or nl is None:
                continue
            roll_credit = ns.mark - nl.mark
            if roll_credit <= 0:
                continue
            total_after = banked_credit + roll_credit - close_cost
            plan = RollPlan(
                tested_side=tested_side, untested_side=untested_side,
                new_short_strike=new_short, new_long_strike=new_long,
                new_short_symbol=ns.symbol, new_long_symbol=nl.symbol,
                roll_credit=roll_credit, close_cost=close_cost,
                total_credit_after=total_after, tested_width=tested_width,
                risk_free=(total_after >= tested_width), contracts=contracts,
            )
            if best is None or plan.total_credit_after > best.total_credit_after:
                best = plan
            if plan.risk_free:
                return plan                # nearest short, narrowest wing that clears
    return best



def check_and_execute_roll(pos_mgr, chain, current_price: float, state, df_1m=None) -> bool:
    """If both condor verticals are open and one side is tested, roll the
    untested side into a broken wing — but ONLY if that roll makes the tested
    side risk-free. Returns True if a roll was executed."""
    t = _ROLL_PLAN.tick(current_price)
    if chain is None:
        t.starved("chain")
        return False

    legs = [r for r in pos_mgr.get_open_records() if r.get("is_condor_leg")]   # r230: ORCS legs included, by ruling
    t.check("legs", len(legs), len(legs) == 2)
    if len(legs) != 2:
        t.hold(f"{len(legs)} condor leg(s) open — a roll needs a pair")
        return False
    # Final-form guard: never touch a position that has already been rolled.
    if any(r.get("is_broken_wing") for r in legs):
        t.check("final_form", 1.0, False)
        t.hold("structure already rolled — final form, no further adjustment")
        return False
    t.check("final_form", 0.0, True)

    tested, untested = classify_tested(legs, current_price, df_1m=df_1m)
    if tested is None:
        t.check("tested", 0.0, False)
        t.hold("neither short strike tested at this price")
        return False
    t.check("tested", 1.0, True)
    t.direction = tested["option_side"]
    t.anchor(trigger=tested.get("short_strike"))

    banked_credit = sum(float(l.get("credit_received", l.get("entry_premium", 0.0)))
                        for l in legs)
    plan = find_risk_free_roll(tested, untested, chain, current_price, banked_credit)
    if plan is not None:
        t.check("roll_credit", plan.roll_credit, plan.roll_credit > 0)
        t.check("close_cost", plan.close_cost, True)
        t.check("credit_after", plan.total_credit_after, True)
        t.check("tested_width", plan.tested_width, True)
        t.check("risk_free", 1.0 if plan.risk_free else 0.0, plan.risk_free)
    if plan is None or not plan.risk_free:
        # No roll available that removes tested-side risk — manage normally.
        if plan is None:
            t.hold(f"{tested['option_side']} side tested at "
                   f"{tested.get('short_strike', 0):g} but the untested vertical "
                   f"cannot be priced — no roll")
        else:
            t.hold(f"{tested['option_side']} side tested at "
                   f"{tested.get('short_strike', 0):g}; best roll to "
                   f"{plan.new_short_strike:g}/{plan.new_long_strike:g} collects "
                   f"{plan.roll_credit:.2f} less {plan.close_cost:.2f} to close = "
                   f"{plan.total_credit_after:.2f} cumulative vs tested width "
                   f"{plan.tested_width:.2f} — NOT risk-free, holding")
        return False

    t.hold(f"ROLL {plan.untested_side} to {plan.new_short_strike:g}/"
           f"{plan.new_long_strike:g}: roll credit {plan.roll_credit:.2f}, close "
           f"cost {plan.close_cost:.2f}, cumulative {plan.total_credit_after:.2f} "
           f">= tested width {plan.tested_width:.2f} — risk-free", verdict="ROLL")
    return _execute_roll(pos_mgr, tested, untested, plan, state, chain)


def _guard_clear(state, what: str) -> bool:
    """r495 / B4 — may a LIVE adjustment that will post an OPEN start at all? Asked before the
    first leg so it is the whole adjustment or none. Paper: always."""
    if state.paper_trading:
        return True
    try:
        from config import INSTRUMENT
        from data.tasty_client import get_session, get_account
        from execution import order_guard as _guard
        ok, why = _guard.clear_to_post(f"{INSTRUMENT}|open|condor_{what}",
                                       get_session(), get_account())
    except Exception as exc:                                    # noqa: BLE001
        ok, why = False, f"guard unavailable ({type(exc).__name__})"
    if not ok:
        logger.warning("[guard] condor %s not started: %s", what, why)
    return ok


def _execute_roll(pos_mgr, tested: dict, untested: dict,
                  plan: RollPlan, state, chain=None) -> bool:
    """Close the old untested vertical, open the rolled vertical, and flag the
    whole structure a broken wing (final form — no further adjustments)."""
    from database.trade_logger import make_record, get_trade_logger
    from execution.exit_engine import get_exit_engine
    from notifications.alert_manager import get_alert_manager
    from config import INSTRUMENT, CONDOR_STOP_LOSS_PCT, CONDOR_NICKEL_CLOSE

    tl        = get_trade_logger()
    mode      = "PAPER" if state.paper_trading else "LIVE"
    contracts = plan.contracts
    if not _guard_clear(state, "roll"):                         # r495 B4: before step 1
        return False

    try:
        # ── 1. Close the OLD untested vertical (buy it back) ──────────────────
        # v3.7 (defect P): BOTH modes route through place_exit_order and book
        # the FillResult's ACTUAL fill price — paper simulates at plan.close_cost
        # (same as every other paper exit), live is the broker's confirmed net.
        # The old code booked plan.close_cost even when the live fill differed.
        fill = get_exit_engine(state.paper_trading).place_exit_order(
            untested, "rolled_to_broken_wing",
            mark_price=plan.close_cost)
        if not fill.confirmed or fill.fill_price is None:
            logger.error("Roll aborted — untested vertical close not confirmed "
                         f"({fill.detail or 'no fill'}); leaving position OPEN")
            return False
        close_price = float(fill.fill_price)
        old_credit = float(untested.get("credit_received", untested.get("entry_premium", 0.0)))
        pnl_close  = (old_credit - close_price) * contracts * CONTRACT_MULTIPLIER
        tl.log_exit(untested["trade_id"], exit_price=close_price,
                    pnl_usd=pnl_close, exit_reason="rolled_to_broken_wing")
        pos_mgr.remove_record(untested["trade_id"])

        # ── 2. Open the ROLLED untested vertical (the new risk side) ──────────
        # v3.7 (defect P): a REAL order, fill-confirmed. The old code wrote the
        # DB record without placing ANY live order — a fictional position. Now:
        # live places the signed-credit limit and books ONLY the confirmed
        # contracts at the broker's net credit; paper mirrors live friction via
        # PAPER_FILL_SLIPPAGE_PCT (same as condor entries). If the open fails
        # AFTER the close succeeded, position-truth is preserved (DB matches
        # broker: old vertical gone, no new one) — we alert loudly and return
        # False; the roll conditions re-evaluate on a later tick with a fresh
        # plan.
        roll_qty = contracts
        if not state.paper_trading:
            from data.tasty_client import get_session, get_account, sdk_result
            from execution.order_confirm import confirm_order_fill
            from tastytrade.order import (
                NewOrder, Leg, OrderAction, OrderType, OrderTimeInForce,
                InstrumentType,
            )
            from decimal import Decimal

            session = get_session()
            account = get_account()
            legs = [
                Leg(instrument_type=InstrumentType.EQUITY_OPTION,
                    symbol=plan.new_short_symbol,
                    action=OrderAction.SELL_TO_OPEN, quantity=contracts),
                Leg(instrument_type=InstrumentType.EQUITY_OPTION,
                    symbol=plan.new_long_symbol,
                    action=OrderAction.BUY_TO_OPEN, quantity=contracts),
            ]
            # ── 🔴 r105 — THE ROLL'S OPEN HALF WALKS, AND IT WALKS *HERE* ────
            # Every other order in this system walks ACROSS ticks: post a rung,
            # return unfilled, resume next tick. THE ROLL CANNOT. By the time
            # this line runs the old untested vertical is already CLOSED, so
            # `check_and_execute_roll` sees `len(legs) != 2` on the next tick
            # and never re-enters — a walk that returned unfilled here would
            # strand the position half-rolled with the tested side no longer
            # hedged and nothing scheduled to finish the job.
            # ⚠️ SO THE WALK IS BOUNDED AND IN-LINE. Rungs are tried in one
            # call, terminating at mark, which is the price the pre-r105 code
            # posted immediately. Worst case is the old behaviour plus a few
            # seconds; best case is the extra credit the ladder exists to win,
            # on the order that is trying to make the tested side FREE.
            from execution.entry_ladder import rungs as _rungs
            _rc = float(plan.roll_credit)
            _ladder = [_rc]
            try:
                _ul = (chain.puts if plan.untested_side == "put"
                       else chain.calls) if chain is not None else []
                _short_c = _contract_at(_ul, plan.new_short_strike)
                _long_c  = _contract_at(_ul, plan.new_long_strike)
                if _short_c is not None and _long_c is not None:
                    _sb = (getattr(_short_c, "bid", 0.0) or 0.0) - (getattr(_long_c, "ask", 0.0) or 0.0)
                    _sa = (getattr(_short_c, "ask", 0.0) or 0.0) - (getattr(_long_c, "bid", 0.0) or 0.0)
                    if _sa > 0:
                        _t = _rungs(max(0.0, _sb), _sa, "sell", INSTRUMENT)
                        if _t:
                            _ladder = _t
            except Exception as _lex:                          # noqa: BLE001
                logger.debug("roll ladder pricing skipped: %s", _lex)
            logger.info("[ladder] ROLL open — %d rung(s) %s (plan credit %.2f)",
                        len(_ladder), [round(x, 2) for x in _ladder], _rc)

            response = None
            for _rung in _ladder:
                order = NewOrder(
                    time_in_force = OrderTimeInForce.DAY,
                    order_type    = OrderType.LIMIT,
                    price         = Decimal(str(round(float(_rung), 2))),  # + = credit
                    legs          = legs,
                )
                response = sdk_result(account.place_order(session, order, dry_run=False))   # B0
                if response.errors:
                    break
                ofill = confirm_order_fill(
                    session, account, response.order,
                    [(plan.new_short_symbol, 1, +1), (plan.new_long_symbol, 1, -1)],
                    what=f"rolled-vertical entry @ {float(_rung):.2f}",
                    deadline_s=6.0)
                if ofill.filled and ofill.net_price is not None and ofill.quantity > 0:
                    break
                if ofill.working_order_id:
                    break      # cannot cancel — do not stack a second order
                logger.info("[ladder] ROLL rung %.2f refused (%s)",
                            float(_rung), ofill.detail)
            if response is not None and response.errors:
                logger.error(f"Rolled vertical order failed: {response.errors}")
                get_alert_manager()._send(
                    f"\U0001F6A8 [{mode}] ROLL HALF-COMPLETE: closed old "
                    f"{plan.untested_side} vertical but the rolled open was "
                    f"REJECTED — tested side is NOT risk-free; will re-evaluate")
                return False
            if not ofill.filled or ofill.net_price is None or ofill.quantity <= 0:
                if ofill.working_order_id:
                    get_alert_manager()._send(
                        f"\U0001F6A8 [{mode}] rolled-vertical order "
                        f"{ofill.working_order_id} could not be cancelled and "
                        f"may still fill — reconcile will adopt it")
                get_alert_manager()._send(
                    f"\U0001F6A8 [{mode}] ROLL HALF-COMPLETE: closed old "
                    f"{plan.untested_side} vertical but the rolled open did NOT "
                    f"fill ({ofill.detail}) — tested side is NOT risk-free; "
                    f"will re-evaluate")
                return False
            roll_credit_fill = float(ofill.net_price)   # broker net, not the plan
            roll_qty         = int(ofill.quantity)
            roll_order_id    = ofill.order_id or ""
            if roll_qty < contracts:
                get_alert_manager()._send(
                    f"\u26A0\uFE0F [{mode}] rolled vertical PARTIAL: "
                    f"{roll_qty}/{contracts} filled — structure quantities "
                    f"are mismatched; booking the filled size")
        else:
            # v3.8: one paper-pricing authority for every path. Default 0.0
            # books the mark; a non-zero knob reduces the credit received.
            from execution.limit_ladder import paper_fill_credit
            roll_credit_fill = paper_fill_credit(plan.roll_credit)
            roll_order_id    = "PAPER"

        new_width  = abs(plan.new_short_strike - plan.new_long_strike)
        new_maxloss = (new_width - roll_credit_fill) * roll_qty * CONTRACT_MULTIPLIER
        rolled = make_record(
            trade_id        = str(uuid.uuid4()),
            symbol          = INSTRUMENT,
            strategy        = "IronCondorStrategy",
            setup_type      = f"BWB rolled {plan.untested_side} vertical",
            setup_grade     = "UNGRADED",   # r152 — no grade exists
            direction       = "neutral",
            option_side     = plan.untested_side,
            strike          = plan.new_short_strike,
            short_strike    = plan.new_short_strike,
            long_strike     = plan.new_long_strike,
            spread_width    = new_width,
            credit_received = roll_credit_fill,       # CONFIRMED credit, not plan
            contracts       = roll_qty,               # CONFIRMED quantity
            entry_premium   = roll_credit_fill,
            total_cost      = new_maxloss,
            max_loss        = new_maxloss,
            stop_premium    = roll_credit_fill * (1 + CONDOR_STOP_LOSS_PCT),
            target_premium  = CONDOR_NICKEL_CLOSE,
            is_condor_leg   = 1,
            is_broken_wing  = 1,                       # FINAL FORM
            short_symbol    = plan.new_short_symbol,
            long_symbol     = plan.new_long_symbol,
            option_symbol   = plan.new_short_symbol,
            order_id        = roll_order_id,
            paper_trade     = 1 if state.paper_trading else 0,
            status          = "open",
        )
        tl.log_entry(rolled)
        pos_mgr.add_condor_leg(rolled)

        # v3.7: the risk-free claim must survive contact with the ACTUAL fill.
        # The plan asserted risk_free using plan.roll_credit; if the confirmed
        # credit came in lighter, re-check and say so — the structure is still
        # booked truthfully either way, but nobody should believe a risk-free
        # label the fills didn't pay for.
        actual_total_credit = (plan.total_credit_after
                               - plan.roll_credit + roll_credit_fill)
        if actual_total_credit < plan.tested_width:
            # ⚠️ AUDIT F8 (2026-08-20): this used to alert "NOT fully
            # risk-free" and then FALL THROUGH — flagging is_broken_wing=1 and
            # announcing "RISK-FREE ... FINAL FORM" from PLAN numbers the fills
            # did not pay for. is_broken_wing stands the roll ladder down
            # (any(is_broken_wing) → no further rolls), so a light fill parked
            # residual risk (width − actual credit) with the primary risk
            # response disarmed and a green label on it. On a shortfall the
            # ladder now stays ARMED — a further smallest-roll can close the
            # gap — and nothing is labelled final.
            get_alert_manager()._send(
                f"\u26A0\uFE0F [{mode}] ROLL FILLED LIGHT: actual credit "
                f"${actual_total_credit:.2f} < tested width "
                f"${plan.tested_width:.2f} — NOT risk-free; ladder stays "
                f"ARMED, no broken-wing flag set")
            logger.warning(
                f"[{mode}] roll filled light "
                f"(${actual_total_credit:.2f} < ${plan.tested_width:.2f}); "
                f"is_broken_wing NOT set — further rolls remain available")
            return True

        # ── 3. Flag the TESTED (now genuinely risk-free) vertical ────────────
        tl.update_fields(tested["trade_id"], is_broken_wing=1)
        tested["is_broken_wing"] = 1
        # r11 — FINAL FORM BASIS: the cost to close the whole structure AS FORMED
        # (the tested vertical's mark + the rolled vertical's fill), stamped on
        # BOTH legs with a shared group id. The only exit from here is a 15%
        # loss from this number (exit_engine v4.16), not from cumulative credit.
        try:
            _tested_mark = float(tested.get("current_premium") or tested.get("entry_premium") or 0.0)
            _basis = round(max(0.05, _tested_mark + float(roll_credit_fill)), 4)
            _grp = f"ff-{tested['trade_id'][:8]}"
            for _leg in (tested, rolled):
                _leg["final_form_basis"] = _basis
                _leg["final_form_group"] = _grp
                _leg["cumulative_credit"] = float(actual_total_credit)
                tl.update_fields(_leg["trade_id"], final_form_basis=_basis,
                                 final_form_group=_grp, cumulative_credit=float(actual_total_credit))
        except Exception as _fe:                                 # noqa: BLE001
            logger.warning("[roll] final-form basis not stamped: %s", _fe)

        get_alert_manager()._send(
            f"\U0001F98B [{mode}] ROLLED TO BROKEN WING | "
            f"{plan.tested_side} side now RISK-FREE "
            f"(credit ${plan.total_credit_after:.2f} >= width ${plan.tested_width:.2f}) | "
            f"rolled {plan.untested_side} to {plan.new_short_strike:.0f}/{plan.new_long_strike:.0f} "
            f"for ${plan.roll_credit:.2f} | final form | {fmt_et_short()}"
        )
        logger.info(
            f"[{mode}] BROKEN-WING ROLL: {plan.tested_side} side risk-free "
            f"(cum credit ${plan.total_credit_after:.2f} >= width ${plan.tested_width:.2f}); "
            f"rolled {plan.untested_side} -> {plan.new_short_strike:.0f}/{plan.new_long_strike:.0f} "
            f"credit ${plan.roll_credit:.2f}. FINAL FORM — no further adjustments."
        )
        return True

    except Exception as e:
        logger.error(f"Broken-wing roll failed: {e}")
        return False


# ═════════════════════════════════════════════════════════════════════════════
# r106 — THE TENT. Operator's spec, 2026-08-24, read back and confirmed.
# ═════════════════════════════════════════════════════════════════════════════
# "If we've already rolled & price breaches the new structure, take off the
#  profitable side, leaving a lone vertical. Purchase a long position
#  equidistant from the short strike as the other long strike, leaving price
#  under the 'tent.' The only remaining adjustment after that should be a 15%
#  floor of the total credit collected. If we can't achieve that, close the
#  entire structure. Close it also if purchasing the new long strike gets us to
#  -15% loss."
#
# WORKED EXAMPLE (the one this was read back against):
#   condor 95/90 put + 105/110 call, price ~100. Call side tested, put side
#   rolled up to 100/95. Price closes above 105 — the breach.
#   → take off the profitable (rolled put) vertical
#   → keep 105/110 call
#   → existing wing is +5 from the short, so the hedge goes -5: a LONG PUT at
#     100. Longs at 100 and 110 bracket price at ~106.
#
# ⚠️ THE HEDGE IS THE OPPOSITE TYPE, AND THAT IS THE WHOLE POINT. A long CALL at
# 100 against short 105 / long 110 goes NET LONG above 110 — uncapped on the far
# tail. A long PUT at 100 caps the upside at width−credit and PAYS if price
# collapses back through. The operator chose the hedge after the payoff of both
# was worked through; it is his ruling on my analysis, not his original spec,
# and it is recorded that way deliberately.
#
# ⚠️ "PROFITABLE" IS COMPUTED, NOT ASSUMED. Which side is winning follows from
# the marks. Deciding it from which side we LABELLED tested would encode a
# reading of "breaches the new structure" that was never pinned down — price
# continuing through the original short, or reversing through the rolled one.
# Reading the book answers it for both cases and neither of us has to be right.
# ⚠️ BREACH = A 1-MIN CANDLE CLOSE BEYOND A SHORT STRIKE. Operator's definition.
# A wick is a touch, not a decision — the same rule the ORB structure stop uses.

def _tent_breached(df_1m, legs: List[dict]) -> Optional[dict]:
    """The leg whose short strike a CLOSED 1m candle has breached, or None."""
    try:
        if df_1m is None or len(df_1m) < 2:
            return None
        last_close = float(df_1m["close"].iloc[_closed_pos(df_1m)])   # newest CLOSED bar (r44 BAR.1: by time)
    except Exception:                                          # noqa: BLE001
        return None
    for leg in legs:
        k = float(leg.get("short_strike") or 0.0)
        if k <= 0:
            continue
        if leg.get("option_side") == "call" and last_close > k:
            return leg
        if leg.get("option_side") == "put" and last_close < k:
            return leg
    return None


def _leg_value(leg: dict, chain) -> Optional[float]:
    """Current cost to close this vertical (short mark − long mark)."""
    lst = chain.puts if leg.get("option_side") == "put" else chain.calls
    s = _mark_at(lst, leg.get("short_strike"))
    l = _mark_at(lst, leg.get("long_strike"))
    return None if s is None or l is None else max(0.0, s - l)


def check_and_execute_tent(pos_mgr, chain, current_price: float, state,
                           df_1m=None) -> bool:
    """Rung 2+3 of the condor ladder, combined per the operator: on a breach of
    an ALREADY-ROLLED structure, take the profitable side off and buy the hedge.

    Returns True if the structure was adjusted or closed.
    """
    from config import TENT_ENABLED, TENT_FLOOR_PCT, INSTRUMENT, CONTRACT_MULTIPLIER
    from database.trade_logger import make_record, get_trade_logger
    from execution.exit_engine import get_exit_engine
    from notifications.alert_manager import get_alert_manager
    import uuid

    if not TENT_ENABLED or chain is None:
        return False
    legs = [r for r in pos_mgr.get_open_records() if r.get("is_condor_leg")]   # r230: ORCS legs included, by ruling
    if len(legs) != 2:
        return False
    # ⚠️ ONLY AFTER A ROLL. The tent is the rung BELOW the roll, not an
    # alternative to it: an unrolled condor still has the roll available and the
    # roll is strictly better (it collects credit rather than paying a debit).
    if not any(r.get("is_broken_wing") for r in legs):
        return False

    breached = _tent_breached(df_1m, legs)
    if breached is None:
        return False
    keep = next((l for l in legs if l is not breached), None)
    if keep is None:
        return False

    # Which side is actually winning? The book decides.
    v_keep = _leg_value(keep, chain)
    v_breach = _leg_value(breached, chain)
    if v_keep is None or v_breach is None:
        logger.info("[tent] a leg has no mark — declining this pass, position "
                    "left as-is (the roll's silent-refusal lesson)")
        return False
    c_keep = float(keep.get("credit_received", keep.get("entry_premium", 0.0)))
    c_breach = float(breached.get("credit_received", breached.get("entry_premium", 0.0)))
    profit_keep, profit_breach = c_keep - v_keep, c_breach - v_breach
    winner, loser = ((keep, breached) if profit_keep >= profit_breach
                     else (breached, keep))
    logger.info("[tent] BREACH beyond the %s short %.2f — winner is the %s side "
                "(+%.2f vs +%.2f)", breached.get("option_side"),
                float(breached.get("short_strike") or 0), winner.get("option_side"),
                max(profit_keep, profit_breach), min(profit_keep, profit_breach))

    # ── price the hedge BEFORE paying for it ────────────────────────────────
    side = loser.get("option_side")
    short_k = float(loser.get("short_strike") or 0.0)
    long_k  = float(loser.get("long_strike") or 0.0)
    width   = abs(short_k - long_k)
    hedge_k = short_k - width if side == "call" else short_k + width
    hedge_list = chain.puts if side == "call" else chain.calls   # OPPOSITE type
    hedge = _contract_at(hedge_list, hedge_k)
    hedge_ask = float(getattr(hedge, "ask", 0.0) or 0.0) if hedge else 0.0
    cum_credit = c_keep + c_breach
    winner_take = float(_leg_value(winner, chain) or 0.0)
    # Cumulative credit AFTER buying back the winner and paying for the hedge.
    net_after = cum_credit - winner_take - hedge_ask

    if hedge is None or hedge_ask <= 0:
        logger.warning("[tent] no priced %s hedge at %.2f — CLOSING the whole "
                       "structure instead (a tent that cannot be built is a "
                       "close)", "put" if side == "call" else "call", hedge_k)
        return _tent_close_all(pos_mgr, legs, chain, state, "tent_unavailable")
    if net_after <= cum_credit * (1.0 - TENT_FLOOR_PCT) - 1e-9:
        logger.warning("[tent] the hedge at %.2f costs %.2f — that alone puts "
                       "the structure at %.1f%% of cumulative credit %.2f, past "
                       "the %.0f%% floor. NOT BUYING IT; closing instead.",
                       hedge_k, hedge_ask,
                       (net_after / cum_credit * 100.0) if cum_credit else 0.0,
                       cum_credit, TENT_FLOOR_PCT * 100.0)
        return _tent_close_all(pos_mgr, legs, chain, state, "tent_unaffordable")

    logger.info("[tent] BUILDING: keep %s %.0f/%.0f, hedge LONG %s %.2f "
                "(ask %.2f), cumulative credit %.2f -> %.2f after",
                side, short_k, long_k, "put" if side == "call" else "call",
                hedge_k, hedge_ask, cum_credit, net_after)
    return _execute_tent(pos_mgr, winner, loser, hedge, hedge_ask,
                         net_after, state, chain)


def _tent_close_all(pos_mgr, legs: List[dict], chain, state, reason: str) -> bool:
    """Close every open leg. Used when the tent cannot be built or afforded —
    the operator's "if we can't achieve that, close the entire structure"."""
    from execution.exit_engine import get_exit_engine
    from database.trade_logger import get_trade_logger
    tl, ok = get_trade_logger(), True
    for leg in list(legs):
        mark = _leg_value(leg, chain)
        fill = get_exit_engine(state.paper_trading).place_exit_order(
            leg, reason, mark_price=mark)
        if not fill.confirmed or fill.fill_price is None:
            logger.error("[tent] %s close NOT confirmed (%s) — leg stays OPEN",
                         str(leg.get("trade_id", ""))[:8], fill.detail)
            ok = False
            continue
        credit = float(leg.get("credit_received", leg.get("entry_premium", 0.0)))
        tl.log_exit(leg["trade_id"], exit_price=float(fill.fill_price),
                    pnl_usd=(credit - float(fill.fill_price))
                    * int(leg.get("contracts", 1)) * CONTRACT_MULTIPLIER,
                    exit_reason=reason)
        pos_mgr.remove_record(leg["trade_id"])
    return ok


def _execute_tent(pos_mgr, winner: dict, keep: dict, hedge, hedge_ask: float,
                  net_after: float, state, chain) -> bool:
    """Close the winning vertical, buy the hedge, and re-book the survivor as a
    TENT carrying the CUMULATIVE credit.

    ⚠️ ORDER MATTERS AND IT IS THE RISK ORDERING. The winner comes off FIRST
    (it is the profitable side and closing it is a credit), then the hedge is
    bought. If the hedge fails after the winner is gone we are left with the
    lone vertical the operator already manages on a floor — a known state, not
    an orphan. Doing it the other way round would leave a bought hedge attached
    to a structure we then failed to simplify.
    """
    from config import INSTRUMENT, CONTRACT_MULTIPLIER, TENT_FLOOR_PCT
    from database.trade_logger import make_record, get_trade_logger
    from execution.exit_engine import get_exit_engine
    from notifications.alert_manager import get_alert_manager
    import uuid

    tl   = get_trade_logger()
    mode = "PAPER" if state.paper_trading else "LIVE"
    qty  = int(keep.get("contracts", 1))
    if not _guard_clear(state, "tent"):                         # r495 B4: before step 1
        return False                                            # HOLD: touch nothing, retry next tick

    # ── 1. take the profitable side off ─────────────────────────────────────
    w_mark = _leg_value(winner, chain)
    fill = get_exit_engine(state.paper_trading).place_exit_order(
        winner, "tent_take_profitable_side", mark_price=w_mark)
    if not fill.confirmed or fill.fill_price is None:
        logger.error("[tent] the profitable side did not close (%s) — nothing "
                     "adjusted, position left intact", fill.detail)
        return False
    w_credit = float(winner.get("credit_received", winner.get("entry_premium", 0.0)))
    tl.log_exit(winner["trade_id"], exit_price=float(fill.fill_price),
                pnl_usd=(w_credit - float(fill.fill_price)) * qty * CONTRACT_MULTIPLIER,
                exit_reason="tent_take_profitable_side")
    pos_mgr.remove_record(winner["trade_id"])

    # ── 2. buy the hedge ────────────────────────────────────────────────────
    hedge_fill, order_id = hedge_ask, "PAPER"
    if not state.paper_trading:
        from data.tasty_client import get_session, get_account, sdk_result
        from execution.order_confirm import confirm_order_fill
        from tastytrade.order import (NewOrder, Leg, OrderAction, OrderType,
                                      OrderTimeInForce, InstrumentType)
        from decimal import Decimal
        session, account = get_session(), get_account()
        order = NewOrder(
            time_in_force=OrderTimeInForce.DAY, order_type=OrderType.LIMIT,
            price=Decimal(str(-round(float(hedge_ask), 2))),   # − = debit paid
            legs=[Leg(instrument_type=InstrumentType.EQUITY_OPTION,
                      symbol=hedge.symbol, action=OrderAction.BUY_TO_OPEN,
                      quantity=qty)])
        resp = sdk_result(account.place_order(session, order, dry_run=False))   # B0
        if getattr(resp, "errors", None):
            get_alert_manager()._send(
                f"\U0001F6A8 [{mode}] {INSTRUMENT} TENT HALF-BUILT: the winning "
                f"side is closed but the hedge was REJECTED. The remaining "
                f"vertical keeps its floor. {resp.errors}")
            return False
        hf = confirm_order_fill(session, account, resp.order,
                                [(hedge.symbol, 1, +1)], what="tent hedge")
        if not hf.filled or hf.net_price is None:
            get_alert_manager()._send(
                f"\U0001F6A8 [{mode}] {INSTRUMENT} TENT HALF-BUILT: hedge did "
                f"not fill ({hf.detail}). The remaining vertical keeps its "
                f"floor and is managed as a lone vertical.")
            return False
        hedge_fill, order_id = float(hf.net_price), (hf.order_id or "")

    # ── 3. re-book the survivor AS A TENT, carrying cumulative credit ───────
    # ⚠️ THE OLD ROW IS CLOSED AND A NEW ONE OPENED, rather than mutating in
    # place. `structure.of` reads setup_type, the exit engine routes on it, and
    # the P&L basis has changed from this vertical's own credit to the whole
    # structure's — three things that must move together or not at all.
    cum = float(keep.get("credit_received", keep.get("entry_premium", 0.0))) \
        + w_credit - float(fill.fill_price) - float(hedge_fill)
    # OTV4TEST r10 — THE FINAL-FORM FLOOR IS MEASURED FROM WHERE THE STRUCTURE
    # STANDS AT FORMATION, not from cumulative credit (operator 2026-09-09:
    # "15% of wherever our credit is from that point, not including the
    # previous rolls and other transactions"). The basis is the cost to close
    # the tent as formed — the kept vertical's mark less the hedge's — and the
    # floor is that basis grown 15%. Cumulative credit stays on the record as
    # the account of what was collected; it is no longer the stop's basis.
    _keep_mark = float(keep.get("current_premium") or keep.get("entry_premium") or 0.0)
    form_basis = max(0.0, _keep_mark - float(hedge_fill))
    if form_basis <= 0.05:
        form_basis = max(0.05, cum)          # a degenerate basis falls back to the credit standing
    tl.log_exit(keep["trade_id"], exit_price=float(keep.get("entry_premium", 0.0)),
                pnl_usd=0.0, exit_reason="tent_rebooked")
    pos_mgr.remove_record(keep["trade_id"])

    side  = keep.get("option_side")
    rec = make_record(
        trade_id=str(uuid.uuid4()), symbol=INSTRUMENT,
        strategy="IronCondorStrategy", setup_type=f"tent_{side}",
        setup_grade="UNGRADED", direction="neutral", option_side=side,
        strike=keep.get("short_strike"), short_strike=keep.get("short_strike"),
        long_strike=keep.get("long_strike"),
        lower_strike=float(getattr(hedge, "strike", 0.0) or 0.0),
        spread_width=float(keep.get("spread_width") or 0.0),
        credit_received=cum, contracts=qty,
        entry_premium=form_basis,                # r10: the floor's basis = the structure as formed
        final_form_basis=form_basis,
        cumulative_credit=cum,
        stop_premium=form_basis * (1 + TENT_FLOOR_PCT),
        total_cost=abs(cum) * qty * CONTRACT_MULTIPLIER,
        max_loss=abs(float(keep.get("spread_width") or 0.0) - cum) * qty * CONTRACT_MULTIPLIER,
        short_symbol=keep.get("short_symbol"), long_symbol=keep.get("long_symbol"),
        lower_symbol=getattr(hedge, "symbol", ""),   # r106: the hedge leg
        option_symbol=keep.get("short_symbol"),
        is_condor_leg=1, condor_leg_num=0, is_broken_wing=1,
        order_id=order_id, paper_trade=1 if state.paper_trading else 0,
        status="open",
    )
    tl.log_entry(rec)
    pos_mgr.add_condor_leg(rec)
    get_alert_manager()._send(
        f"\u26F0\uFE0F [{mode}] {INSTRUMENT} TENT BUILT | keep {side} "
        f"{keep.get('short_strike')}/{keep.get('long_strike')} + hedge LONG "
        f"{'put' if side == 'call' else 'call'} {getattr(hedge, 'strike', 0)} "
        f"@ {hedge_fill:.2f} | cumulative credit ${cum:.2f} | "
        f"floor ${cum * (1 + TENT_FLOOR_PCT):.2f} ({TENT_FLOOR_PCT:.0%}) | "
        f"{fmt_et_short()}")
    logger.info("[tent] BUILT: %s %s/%s + hedge %.2f, cumulative credit %.2f, "
                "floor %.2f — one adjustment remains", side,
                keep.get("short_strike"), keep.get("long_strike"),
                getattr(hedge, "strike", 0), cum, cum * (1 + TENT_FLOOR_PCT))
    return True
