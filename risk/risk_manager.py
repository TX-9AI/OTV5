"""
risk/risk_manager.py  v5.2
v5.2  2026-10-31  OTV5 r67 (PARC.4) — size_for("parc") and _size_parc (rule parc_ramp) are removed,
      with size_for's value_at_stop argument (PARC's only). The CAP_EXCLUDED_STRATEGIES getattr defaults name
      ("PARK",), config's value again. The operator, 2026-10-31: "On PARC, no. It was an idea. It failed. It's done." and "Yes" to removing its code. Every other
      rule is unchanged. Gate tests/check_no_parc.py.
v5.1  2026-10-27  OTV5 r46 (PARC.1) — size_for("parc") -> _size_parc, rule "parc_ramp": BREAKOUT'S configure.sh RAMP FOR A
      CREDIT SPREAD. The operator, 2026-10-27: "adopt the same scaling model we use for breakout, meaning the stop
      distance will determine our position size"; "I want 1050 to be the floor & use the same ramp in configure.sh (most
      are set to $2500)". Per spread: max_loss = (width - credit) x 100; loss_at_stop = (the spread's estimated value
      with the underlying AT the structure stop - credit) x 100, capped at max_loss (no value - no IV - or a value at or
      under the credit -> max_loss, never a smaller invented number). by_risk = floor(risk per trade [OT_RISK_USD, the
      ramp START/MIN] / loss_at_stop), by_top = floor(ORB_BUDGET_USD [OT_ORB_BUDGET_USD, the ramp TOP] / max_loss),
      contracts = max(1, min(by_risk, by_top)); one spread's max_loss over the TOP is REFUSED (as _size_geometry's
      orb_budget refusal). The CAP_EXCLUDED_STRATEGIES getattr defaults name ("PARK", "PARC"), config's value.
      Gate tests/check_parc.py P4.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.14 2026-10-18  OTV4TEST r298 (CAP.4) — the restart seed (_ensure_seeded) takes the CAP's number, realized_pnl_today
      with CAP_EXCLUDED_STRATEGIES, not today_summary's all-strategy total: a boot after a PARK loss past the limit read
      halted and the first is_halted() logged a RE-ARMED event nothing had hit (audit 2026-10-18 A5). The getattr default
      for CAP_EXCLUDED_STRATEGIES now equals config's ("PARK",), not ().
v4.13 2026-10-18  OTV4TEST r288 (PARK.1) — day_realized_pnl() - the number the catastrophic cap gates on - leaves out
      config.CAP_EXCLUDED_STRATEGIES (PARK: its own budget, the operator 2026-10-17). A PARK loss never halts the morning
      strategies or the flies; a PARK win never buys them room.
v4.12 2026-10-03  OTV4TEST r208 (CAP.4) — THE CAP COUNTERFACTUAL, LOG-ONLY. note_entry_risk(record) writes one JSON
      line to cap_counterfactual.jsonl (beside trades.db, so a checker's scratch DB takes it too) for EVERY entry: its risk at the stop and at max loss, the day's
      realized net, the limit, the headroom, and whether a rule "refuse an entry whose planned risk would breach
      the cap" WOULD have refused it. Nothing is refused. The operator, 2026-10-03: "No, allow it. But do a
      counter factual study with a set review date in 2 weeks" (review 2026-10-17). Never raises.
v4.11 2026-10-03  OTV4TEST r199 (AUD.7) — A CAP EPISODE IS RECORDED IN circuit_breaker_events. is_halted writes
      one row when the cap is hit (where the page is decided, so once per episode and not again after a
      restart inside it) and one when it re-arms. TradeLogger.log_circuit_breaker had zero callers; query.py
      read and s3_push pushed a table nothing wrote. And a cap page that fails to send now WARNS (it was
      `except: pass`). The halt decision itself is untouched.
v4.10 2026-10-03  OTV4TEST r190 (AUD.1, SHARED WITH otv4 CND.12) — _ensure_seeded marks itself seeded
      only after a successful read, and warns and retries on failure (it set the flag first, swallowed
      the error and never retried). The halt itself is unaffected: is_halted reads the DB on every call.
      Function text verbatim with otv4 (getsource b212705d...). Pinned by tests/check_risk_seed_retry.py.
v4.9 2026-09-30  OTV4TEST r181 (ALRT.2) — THE CAP PAGE IS ONCE PER EPISODE ACROSS A
      RESTART. 2026-09-29 16:01 ET the r175 restart re-sent the 11:08 cap page: a
      fresh process starts un-halted, reads the day's realized loss, sees the
      transition INTO the halt and pages again. The operator's standing rule
      (WDOG.1): no duplicate notifications for a single event; he approved this
      fix 2026-09-30 ("Yes", then "Agree on all"). The page now writes a stamp,
      data/CAP_PAGED beside the trades store (so a checker's scratch store gets a
      scratch stamp), holding today's ET date and whether the episode is still
      open. A process that finds today's episode still open does NOT page and
      logs that it did not; a re-open (back under the limit) closes the episode,
      in this process or the next, so a later breach pages again as r162 ruled.
      A stamp that cannot be read or written never suppresses a page.
v4.8 2026-09-27  OTV4TEST r162 (CAP.1) — THE DAILY CATASTROPHIC LOSS CAP RE-ARMS. The
      operator, 2026-09-27: "Manage what's open but no new entries. If the open
      TRADES put us back under the limit again after they close, it can open
      trades again." is_halted() LATCHED for the rest of the day once breached;
      it is now RECOMPUTED on every call from the day's REALIZED (closed-trade)
      net P&L: at or beyond -limit no new entries, back under it entries re-open.
      The halt pages ONCE PER EPISODE (a new breach after a re-open pages again,
      WA 17); the re-open is a WARNING in the log. This also removes an
      inconsistency: reset_session() (every restart) already re-derived the
      state from the DB, so a restart un-halted a recovered day while a running
      process stayed halted. Open positions were never gated by it (only the
      entry path, main.py, reads it) and still are not.
v4.7 2026-09-27  OTV4TEST r161 (SIZE.2) — size_for(scaled=False) SIZES FLAT. The operator,
      2026-09-27: keep the structure stop, "just use a flat dollar amount for the
      entry". A long debit that supplies geometry but is switched OFF takes the
      BUDGET rule (rule "flat") AFTER the r93 noise floor, which moves out of
      _size_geometry into _noise_floor_refusal so both paths run the SAME gate:
      a stop inside one bar is §36 FEASIBILITY and is refused with scaling on or
      off. scaled defaults True, so every caller that does not pass it sizes
      exactly as before.
v4.6 2026-09-22  OTV4TEST r93 — _size_geometry REFUSES a stop inside the noise floor,
      before any sizing arithmetic, with the floor NAMED in the reason.
      Operator's ruling 2026-09-22: refuse, not floor. Section 36 FEASIBILITY —
      a setup whose stop the tape crosses within one bar cannot pay. A zero
      floor disarms the gate (pre-r93 behaviour) and distance <= 0 stays the
      DEGENERATE case, not a noise-floor refusal.
v4.5  2026-09-22  OTV4TEST r91 — A STOP WIDER THAN THE RANGE IS NO LONGER
      DEGENERATE. That branch forced ONE CONTRACT whenever `distance > width`,
      bypassing the risk budget entirely — measured at distance 2.00 on a 1.02
      range: 1 contract, $80 deployed against a $1,050 target. It made sense
      while GEOMETRY set the size; it does not now that RISK does, and a deep
      impulsive candle is a legitimate setup the operator's own rule already
      handles (wide stop -> small position). Operator: *"I DO NOT want $30 ORB
      TRADES."* ⚠️ `distance <= 0` is STILL degenerate and still sizes 1.
v4.4  2026-09-18  OTV4TEST r44 — THE ORB GEOMETRY RULE GAINS A SCALE.
      🔑 THE OPERATOR'S MODEL WAS RIGHT AND IS KEPT — tight stop big, wide stop
      small. The algebra shows why it was never enough: contracts = width/dist
      and risk/contract = dist x delta x 100, so total risk = width x delta x
      100 and the DISTANCE CANCELS. The rule is exactly risk-normalised — to a
      constant set by the OPENING RANGE rather than the risk budget. Measured on
      a 0.97 range: every stop from 0.54 to 0.01 risked $26-32 while the count
      swung 1 to 80. `by_risk` is the same 1/distance curve with the constant
      the operator banks against. ⚠️ A MISSING STOP PREMIUM FALLS BACK TO
      GEOMETRY — my first cut used `premium - 0`, a constant that flattened the
      curve to one count at every distance; check_orb_budget B3 caught it.
v4.3  2026-08-31  r201 — ORB GEOMETRY IS CLAMPED BY A BUDGET. `min(geometry,
      floor(budget / cost_per_contract))`, and the operator's scaling curve
      falls out of the two clamps meeting rather than needing a ramp. A
      single contract dearer than the whole budget REFUSES rather than
      flooring to one, matching `_size_budget`. Both clamps are recorded on
      the result so a future budget change is a query, not a guess.
v4.2  2026-08-30  r192 — ONE SIZING HANDLER, FOUR RULES, KEYED ON STRUCTURE.
      Operator: "normalize the entry sizing, but use the stop size logic we
      just wrote for orb specifically, and make it active — it shipped
      inert/broken."
      🔴 THE BUG THIS FIXES STRUCTURALLY, NOT JUST ONCE. r181 computed ORB's
      geometry count IN THE CALLER (main.py) and assigned it to
      `signal.contracts` — a field written four times and read ZERO times
      tree-wide — while `entry_engine.enter()` ordered `sizing.contracts`.
      Every ORB trade since the 08-28 bake has been a 1-lot while the log
      printed "[orb-size] r181 geometry: ... -> N (was M)". A rule applied
      by the CALLER is the only one of the four that can compute a number the
      order never sees. Now every rule returns a SizingResult and the order
      reads only SizingResult.contracts, which makes the failure
      UNREPRESENTABLE rather than merely corrected.
      🔑 NOTE WHAT DID NOT CHANGE: entry_engine is untouched. It already
      ordered `sizing.contracts`; it was the sizer that was not answering.
      That is the test of whether this refactor is the right one.
      ⚠️ KEYED ON `structure`, THE SAME KEY `_afternoon_debit_blocked` USES,
      not on a strategy-name list. That lesson is already paid for: the v3
      cutoff held a name list, two of its three entries were deleted, and the
      new long-debit strategy was silently EXEMPT. A name list rots every
      time a strategy moves, AND IT ROTS PERMISSIVELY. Unknown structure
      falls to the budget rule, which is the restrictive one.
      ⚠️ THE ARITHMETIC OF THE THREE EXISTING RULES IS UNCHANGED — this is a
      move, not a rewrite. `tests/check_sizing_parity.py` pins 25 golden rows
      captured from THIS FILE AT r191 before the refactor, across all three.
      🔴 ORB GEOMETRY BYPASSES THE BUDGET ENTIRELY, by the operator's 08-28
      ruling ("NO notional cap for ORB ... I'm actually good, even with the
      worst case taking the 25% floor on a leveraged position with a tight
      stop"). CONSEQUENCE, STATED PLAINLY BECAUSE IT IS NEW BEHAVIOUR AND NOT
      MERELY AN ACTIVATION: the budget path could REFUSE an ORB entry outright
      with `insufficient_capital` when one contract cost more than the risk
      budget. Geometry has no such rung, so those setups now trade at >=1 lot
      where they previously did not fire at all. Only a non-positive premium
      still refuses. The notional is logged on every geometry size so the
      number is visible rather than inferred.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Position sizing, loss caps, halt state.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

risk/risk_manager.py — Position sizing and session circuit breaker. v3.3
FIX NameError on the condor-leg SUCCESS path: the v3.2
        full-budget change renamed the budget variable (half -> leg_budget)
        but the logger.info f-string still referenced the DELETED old name,
        so every sizing that produced >=1 contract raised NameError AT THE
        LOG LINE (found by check_versions' absence canary in the 2026-07-23
        header audit; reproduced: spread_width=5.0, credit=0.50, risk=1050
        -> NameError). Log now prints leg_budget. No sizing-math change.
        (The old variable name is deliberately not written here — the
        absence canary greps this file for it, prose included.)
compute_condor_leg_size() now sizes each vertical at the
        FULL grade budget (was half). See the method docstring. (Relabeled in
        the 2026-07-23 header audit: this entry originally shipped mis-numbered
        v1.4 — the file was already at v3.1.)
SESSION_LOSS_LIMIT import removed (constant deleted in config
        v3.2). It gated nothing: record_loss() has requested a reassessment on
        EVERY loss since v1.4. The session_losses COUNTER is kept as a statistic.
        The only halt is, and always was, the NET DOLLAR cap DAILY_LOSS_LIMIT_USD.
DAILY CAP MADE DEFINITIVE & RESTART-PROOF:
        (a) is_halted() now reads the day's realized net P&L straight from the
            DB (trade_logger.realized_pnl_today()) on EVERY entry attempt — the
            single source of truth, identical to what query.py/status.py show.
            It no longer trusts an in-memory flag, so a restart (manual, deploy,
            or Restart=always after a crash) can't clear the halt: the loss is
            in trades.db and is re-read immediately. This is the bug that let
            AVGO resume trading after a 09:48 restart wiped the in-memory halt.
        (b) The cap binds to the SAME risk-per-trade the manager is constructed
            with (the value used for sizing), not the module-level
            DAILY_LOSS_LIMIT_USD frozen at import; explicit OT_DAILY_LOSS_LIMIT
            still overrides. Removes the drift that showed a $200 default while
            sizing ran at $1050. update_risk() keeps the cap in lockstep.
        (c) reset_session() no longer sets _seeded=True (that line defeated the
            DB re-seed); a fresh process re-reads the day's realized P&L.
v1.0 — original release
remove TRADE_GRADE_C and Twilio references,
        clean up Grade C sizing logic
        at a count threshold). (b) NET daily loss halt: track session net P&L
        (seeded from today's closed trades so it survives restarts) and halt
        NEW entries when day P&L <= -DAILY_LOSS_LIMIT_USD. Wins offset losses —
        a green day keeps trading. Open positions still exit normally.
add compute_condor_leg_size(): sizes ONE condor vertical
        at HALF the grade budget (each side gets half), against the spread
        max-loss = (width - credit) x 100. Enables two independent verticals.
session loss limit no longer halts the session. Hitting
        main loop) instead of stopping the service. Rationale: a 2-loss count
        breaker was too blunt — it would kill sessions that are still net
        profitable. Removed _fire_circuit_breaker()/systemctl-stop and the
        session_halted semantics.
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
Sizing model:
  - Fixed dollar risk per trade (operator-set at startup)
  - Contracts = floor(risk_usd × grade_multiplier / cost_per_contract)
  - cost_per_contract = mark × 100 (single leg) or net_debit × 100 (butterfly)
  - Always whole contracts; minimum 1 if affordable
  - EVERY losing trade sets a one-shot reassessment request (v1.4). A loss is
    count threshold — the old SESSION_LOSS_LIMIT count was deleted in config
    v3.2 (it had gated nothing since v1.4). `session_losses` is retained purely
    classification. Trading continues; the bot re-reads the market.
  - NOTE (live): this intentionally removes the hard stop. For live capital a
    separate $-based session backstop is advisable — not implemented here.
"""

import logging
import math
import os
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

import config
from config import (
    ORB_BUDGET_USD,
    ORB_RISK_USD,
    RISK_PER_TRADE_USD, GRADE_SIZE_MULTIPLIER, SIZE_ON_RISK_TO_STOP,
    DEPLOY_CAP_MULT,
    CONTRACT_MULTIPLIER, PAPER_TRADING, INSTRUMENT, DAILY_LOSS_LIMIT_USD
)
from utils.time_utils import fmt_et_short
from utils.math_utils import contracts_from_risk

logger = logging.getLogger(__name__)

SERVICE_NAME = "optionsbot"


@dataclass
class SizingResult:
    contracts:          int   = 0
    cost_per_contract:  float = 0.0
    # r121 — what one contract can actually LOSE (premium - stop). Equals
    # cost_per_contract when SIZE_ON_RISK_TO_STOP is off, so a reader can
    # always compare the two and see which rule produced the size.
    risk_per_contract:  float = 0.0
    total_cost:         float = 0.0
    max_loss:           float = 0.0
    grade:              str   = "B"
    grade_multiplier:   float = 1.0
    allowed:            bool  = True
    deploy_capped:      bool  = False    # r121 — risk wanted more than ownership allows
    reject_reason:      str   = ""
    # r192 — WHICH RULE DECIDED THIS SIZE. Written on the trade record and the
    # journal row, so "why is this 10 lots" is answerable from the record
    # instead of reconstructed from the log. r181 was invisible for two days
    # precisely because nothing on the row said which rule had run.
    rule:               str   = ""
    # r201 — BOTH CLAMPS, RECORDED. The operator's decision to set a live
    # budget later is a query against these two numbers, not a guess: every ORB
    # row says what the geometry wanted and what the budget allowed, so
    # "which trades would a $30k budget have clipped" is answerable from paper
    # data already banked. Same shape as r198's wing_stretch.
    geometry_wanted:    int   = 0
    budget_allowed:     int   = 0


@dataclass
class CircuitBreakerState:
    session_halted: bool  = False
    session_losses: int   = 0
    reason:         str   = ""

    @property
    def any_active(self) -> bool:
        return self.session_halted


def cap_cf_path() -> str:
    """r208 — the cap counterfactual's file: BESIDE trades.db, so every checker that points
    OT_TRADES_DB at a scratch directory writes its fixture lines there and never here."""
    import os as _os
    try:                                    # the logger's OWN file, whatever a checker bound it to
        from database.trade_logger import get_trade_logger
        _tdb = get_trade_logger().db_path
    except Exception:                       # noqa: BLE001
        from config import DB_PATH as _tdb
    return _os.path.join(_os.path.dirname(_os.path.abspath(_os.path.expanduser(_tdb))), "cap_counterfactual.jsonl")


class RiskManager:
    """
    Options-specific risk manager.
    Sizes positions in whole contracts based on fixed dollar risk.
    Tracks session losses and halts on circuit breaker.
    """

    def __init__(self, risk_per_trade: float = RISK_PER_TRADE_USD,
                 paper_trading: bool = PAPER_TRADING):
        self._risk_per_trade   = risk_per_trade
        self._paper_trading    = paper_trading
        self._session_losses     = 0
        self._session_halted     = False
        self._reassess_requested = False
        self._session_pnl_usd    = 0.0
        self._daily_loss_limit   = self._resolve_daily_limit(risk_per_trade)
        self._seeded             = False

    @staticmethod
    def _resolve_daily_limit(risk_per_trade: float) -> float:
        """Cap = the risk-per-trade actually in use (what sizing uses), so it
        can never drift to a stale module default. An explicit OT_DAILY_LOSS_LIMIT
        env value still overrides."""
        override = os.environ.get("OT_DAILY_LOSS_LIMIT")
        if override:
            try:
                return float(override)
            except ValueError:
                pass
        return float(risk_per_trade)

    def update_risk(self, risk_usd: float):
        self._risk_per_trade   = risk_usd
        # Keep the daily cap tied to the live risk (unless explicitly overridden).
        self._daily_loss_limit = self._resolve_daily_limit(risk_usd)

    @property
    def risk_per_trade(self) -> float:
        return self._risk_per_trade

    def day_realized_pnl(self) -> float:
        """DEFINITIVE realized net P&L for today, straight from the DB.
        The one number every daily-loss decision references."""
        try:
            from database.trade_logger import get_trade_logger
            return float(get_trade_logger().realized_pnl_today(
                exclude_strategies=getattr(config, "CAP_EXCLUDED_STRATEGIES", ("PARK",))))   # r298: default = config's
        except Exception:
            # If the DB is briefly unavailable, fall back to the in-memory tally.
            return float(self._session_pnl_usd)

    # ══ r192 ── THE ONE DOOR ═══════════════════════════════════════════════
    def size_for(self, structure: str, *,
                 grade: str = "B",
                 premium: float = 0.0,
                 stop_premium: float = 0.0,
                 net_debit: float = 0.0,
                 butterfly_half_size: bool = False,
                 spread_width: float = 0.0,
                 credit: float = 0.0,
                 orb_width: float = 0.0,
                 orb_stop_distance: float = 0.0,
                 budget_usd=None,
                 noise_floor: float = 0.0,
                 scaled: bool = True) -> SizingResult:
        """THE single entry point for position size. Dispatches on STRUCTURE.

        🔑 EVERY RULE RETURNS A SizingResult, AND THE ORDER READS ONLY
        SizingResult.contracts. That is the whole point of this function. r181
        put ORB's rule in the CALLER, which wrote a field the order never read,
        and the fleet sized 1 lot for two days while logging that it had not.
        A rule that cannot return a SizingResult cannot be a sizing rule.

        ⚠️ `structure` is the strategy's own declaration — the same key
        `_afternoon_debit_blocked` reads — never a strategy-name list. An
        unknown structure falls to the BUDGET rule, which is the restrictive
        one.

        Geometry is a sub-rule of `long_debit`, selected by the caller SUPPLYING
        `orb_width` / `orb_stop_distance` rather than by naming ORB. A second
        strategy that wants risk-normalised sizing supplies the geometry; it
        does not get added to a list somewhere that later rots.
        """
        st = (structure or "").strip().lower()
        if st == "vertical":
            return self._size_vertical(spread_width, credit, grade)
        if st == "butterfly":
            return self._size_budget(premium=0.0, grade=grade, is_butterfly=True,
                                     net_debit=net_debit,
                                     butterfly_half_size=butterfly_half_size)
        if st == "long_debit" and (orb_width or orb_stop_distance) and not scaled:
            # r161 (SIZE.2) — SCALING OFF: the r93 floor, then FLAT. The
            # operator: *"retain the original structure stop ... but just use
            # a flat dollar amount for the entry"*. The stop is the signal's,
            # set before sizing; only the contract count changes here.
            _refused = self._noise_floor_refusal(orb_stop_distance, noise_floor,
                                                 grade)
            if _refused is not None:
                return _refused
            flat = self._size_budget(premium=premium, grade=grade,
                                     stop_premium=stop_premium)
            flat.rule = "flat"
            if flat.allowed:
                logger.info(
                    "[size] scaling OFF -> flat: %d contract(s) = $%.0f deployed "
                    "against $%.0f per trade (stop %.3f; the ramp would have "
                    "sized on it)", flat.contracts,
                    flat.contracts * flat.cost_per_contract,
                    self._risk_per_trade, float(orb_stop_distance or 0.0))
            return flat
        if st == "long_debit" and (orb_width or orb_stop_distance):
            return self._size_geometry(premium, orb_width, orb_stop_distance,
                                       grade, budget_usd=budget_usd,
                                       stop_premium=stop_premium,
                                       noise_floor=noise_floor)
        return self._size_budget(premium=premium, grade=grade,
                                 stop_premium=stop_premium)

    def _noise_floor_refusal(self, distance, noise_floor,
                             grade: str = "B"):
        """The r93 gate, shared by the ramp and the flat path (r161): a
        refused SizingResult when the stop sits inside the noise floor, else
        None. Moved VERBATIM out of _size_geometry so there is one gate."""
        result = SizingResult(grade=grade)
        result.rule = "orb_geometry"
        # ── r93 — THE NOISE FLOOR, CHECKED BEFORE ANY ARITHMETIC ──────────
        # 🔴 REFUSED, NOT FLOORED, BY THE OPERATOR'S RULING 2026-09-22.
        # A structural stop the tape crosses inside one ordinary bar is not a
        # stop, and sizing against it is the inversion described in config:
        # maximum position on a coin flip. §36 FEASIBILITY — this cannot pay.
        # ⚠️ FAILS TO TODAY'S BEHAVIOUR, LOUDLY, NEVER SILENTLY. A zero or
        # absent floor means the caller could not measure the tape, and the
        # gate stands down rather than refusing every entry on a feed hiccup —
        # but it SAYS SO, because "could not measure" and "measured and passed"
        # must never look alike (§0.5).
        _nf = float(noise_floor or 0.0)
        if _nf > 0 and 0 < float(distance or 0.0) < _nf:
            result.allowed = False
            result.reject_reason = (f"noise_floor: stop {float(distance):.3f} is "
                                    f"inside the {_nf:.3f} floor "
                                    f"({float(distance) / _nf:.2f}x) — the tape "
                                    f"crosses it within one bar")
            logger.warning("[size] orb_geometry REFUSED: stop %.3f < noise floor "
                           "%.3f (%.2fx) — a stop inside one bar is not a stop",
                           float(distance), _nf, float(distance) / _nf)
            return result
        return None

    def _size_geometry(self, premium: float, width: float, distance: float,
                       grade: str = "B", budget_usd=None,
                       stop_premium: float = 0.0,
                       noise_floor: float = 0.0) -> SizingResult:
        """Risk-normalised size off the impulsive candle. NO BUDGET, NO CAP.

        contracts = max(1, floor(width / stop_distance)); the worst entry — a
        stop the full width away — sizes to exactly 1, so every ORB trade risks
        roughly the same dollars AT THE STRUCTURE STOP by construction.

        🔴 THIS RULE HAS NO `insufficient_capital` RUNG, deliberately, per the
        operator's 2026-08-28 ruling. A setup the budget path would have
        REFUSED outright now trades at one lot or more. The notional is logged
        every time, so that is a visible fact rather than an inferred one.

        ⚠️ DEGENERATE GEOMETRY SIZES 1, LOUDLY — never a leveraged position on
        arithmetic nobody trusts. distance <= 0 or distance > width means the
        entry or the stop is not what the strategy thinks it is.
        """
        result = SizingResult(grade=grade)
        result.rule = "orb_geometry"
        _refused = self._noise_floor_refusal(distance, noise_floor, grade)
        if _refused is not None:
            return _refused
        cost_per_contract = float(premium or 0.0) * CONTRACT_MULTIPLIER
        if cost_per_contract <= 0:
            result.allowed       = False
            result.reject_reason = "zero_premium"
            return result
        # ── r201 — THE BUDGET IS THE OTHER CLAMP ──────────────────────────
        # 🔑 The operator's scaling rule is not a separate ramp; it is what
        # these two clamps produce when they meet. A TIGHT stop makes geometry
        # large, so the BUDGET binds and the position is the biggest the budget
        # allows. A WIDE stop makes geometry small, so GEOMETRY binds and you
        # get one lot. "Smallest stops get the maximum budget, biggest stops
        # get a 1-lot maximum, everything else in between."
        budget = float(budget_usd if budget_usd is not None else ORB_BUDGET_USD)
        by_budget = int(budget // cost_per_contract)
        if by_budget < 1:
            # ⚠️ REFUSED, NOT FLOORED TO ONE. A single contract that costs more
            # than the whole budget cannot be inside a budget, and floor-to-1
            # would silently blow through the exact ceiling this exists to
            # impose. This matches `_size_budget`, which already refuses with
            # `insufficient_capital` on the same arithmetic — ORB now behaves
            # like every other rule at its own budget rather than uniquely.
            result.allowed       = False
            result.reject_reason = (f"orb_budget: one contract costs "
                                    f"${cost_per_contract:.0f}, budget is "
                                    f"${budget:.0f}")
            logger.warning("[size] orb_geometry REFUSED: 1 contract @ $%.0f "
                           "exceeds the $%.0f ORB budget", cost_per_contract,
                           budget)
            return result
        if width > 0 and 0 < distance <= width * 1.0001:
            by_geometry = max(1, int(width // distance))
            # ══ r44 — THE RATIO SETS THE SHAPE; THIS SETS THE SCALE ═══════════
            # 🔑 THE OPERATOR'S MODEL IS CORRECT AND IS KEPT: a tight stop takes
            # a large position, a wide stop a small one, *"because we're
            # accepting massive risk on a turn back"*. `width // distance` says
            # that perfectly. What it does NOT say is HOW MUCH — and the algebra
            # is why:
            #     contracts     = width / distance
            #     risk/contract = distance x delta x 100
            #     total risk    = width x delta x 100     <- distance CANCELS
            # The rule is exactly risk-normalised, and normalises to a constant
            # SET BY THE OPENING RANGE rather than by the risk budget.
            # 🔴 MEASURED 2026-09-18 on a 0.97-wide range: EVERY stop distance
            # from 0.54 down to 0.01 produced a total risk of $26-$32 — 3% of
            # the box's $1,050 per-trade budget — while the contract count swung
            # from 1 to 80. The ORB rode a 3.46pt move to +48.4% and banked $60.
            # ⚠️ SAME SHAPE, NOT A NEW ONE. `by_risk` is also proportional to
            # 1/distance, because `premium - stop_premium` IS the distance in
            # premium terms. It is the identical curve with the constant the
            # operator actually banks against, so nothing about the tight/wide
            # behaviour changes — only where the whole curve sits.
            # ⚠️ IT FAILS BACK TO GEOMETRY. No usable stop premium means no
            # risk-per-contract, and inventing one would size on a number
            # nobody measured.
            # 🔴 A MISSING STOP PREMIUM MUST FALL BACK, NOT GUESS — AND MY FIRST
            # CUT DID GUESS. With `stop_premium` absent it defaults to 0, so
            # `premium - 0` is the WHOLE premium: a constant that does not move
            # with the stop, which flattened the sizing curve to the same count
            # at every distance and destroyed the operator's tight/wide shape
            # outright. `check_orb_budget` B3 caught it — stops 0.10 through
            # 10.0 all returned 2 lots. The risk scale is only meaningful when
            # a REAL stop premium was measured; without one, geometry decides,
            # exactly as it did before r44.
            _sp = float(stop_premium or 0.0)
            _pm = float(premium or 0.0)
            _rpc = (_pm - _sp) * CONTRACT_MULTIPLIER
            if _sp > 0 and _rpc > 0:
                by_risk = max(1, int(ORB_RISK_USD // _rpc))
                _scaled = True
            else:
                by_risk, _scaled = by_geometry, False
            count = min(by_risk, by_budget)
            result.geometry_wanted = by_geometry
            result.budget_allowed  = by_budget
            _bound = ("BUDGET" if by_budget < by_risk
                      else ("risk" if _scaled else "geometry"))
            logger.info(
                "[size] orb_geometry: width %.2f / stop %.2f -> geometry %d, "
                "risk %d ($%.0f target / $%.2f per contract), budget %d "
                "($%.0f / $%.0f) -> %d contract(s) = $%.0f deployed, $%.0f at "
                "risk  [%s binds]", width, distance, by_geometry, by_risk,
                ORB_RISK_USD, _rpc, by_budget, budget, cost_per_contract,
                count, count * cost_per_contract, count * max(_rpc, 0.0), _bound)
        else:
            # 🔴 r91 — A STOP WIDER THAN THE RANGE IS NOT DEGENERATE ANY MORE,
            # AND FORCING 1 LOT HERE WAS THE "$30 ORB TRADE".
            # Operator, 2026-09-22: *"I DO NOT want $30 ORB TRADES. I do
            # actually want the 1050 locked in — that should be a minimum
            # position size."* This branch fired whenever `distance > width`,
            # i.e. whenever the impulsive candle ran deeper than the opening
            # range, and it returned ONE CONTRACT regardless of the risk
            # budget: measured at distance 2.00 on a 1.02 range, 1 contract and
            # $80 deployed against a $1,050 target.
            # 🔑 THE GUARD MADE SENSE WHILE GEOMETRY SET THE SIZE — `width //
            # distance` is meaningless when distance exceeds width. It does NOT
            # make sense now that RISK sets the size, because a deep impulsive
            # candle is a legitimate setup that the operator's own rule already
            # handles: wide stop -> high risk per contract -> small position.
            # Small, not minimal.
            # ⚠️ THE REAL DEGENERACY IS STILL REFUSED. `distance <= 0` means the
            # entry and the stop are the same price or inverted, which is the
            # arithmetic fault this branch was written for, and it still sizes
            # 1 LOUDLY rather than dividing by something meaningless.
            _sp_d = float(stop_premium or 0.0)
            _rpc_d = (float(premium or 0.0) - _sp_d) * CONTRACT_MULTIPLIER
            if distance > 0 and _sp_d > 0 and _rpc_d > 0:
                by_risk_d = max(1, int(ORB_RISK_USD // _rpc_d))
                count = min(by_risk_d, by_budget)
                result.geometry_wanted = 0        # geometry abstains, it does not vote 1
                result.budget_allowed  = by_budget
                logger.info(
                    "[size] orb_geometry WIDE STOP width %.2f < distance %.2f "
                    "-> geometry abstains; risk %d ($%.0f target / $%.2f per "
                    "contract), budget %d -> %d contract(s) = $%.0f deployed, "
                    "$%.0f at risk", width, distance, by_risk_d, ORB_RISK_USD,
                    _rpc_d, by_budget, count, count * cost_per_contract,
                    count * _rpc_d)
            else:
                count = 1
                result.geometry_wanted = 1
                result.budget_allowed  = by_budget
                logger.warning(
                    "[size] orb_geometry DEGENERATE width=%.4f distance=%.4f "
                    "stop_premium=%.4f -> 1 contract. The entry or the stop is "
                    "not what the strategy thinks it is.",
                    width, distance, _sp_d)
        result.contracts         = count
        result.cost_per_contract = cost_per_contract
        # ⚠️ FULL PREMIUM, matching the budget rule's doctrine: max_loss is what
        # a gap THROUGH a soft stop actually costs, and downstream gates read
        # this field assuming the worst rather than the intent.
        result.risk_per_contract = cost_per_contract
        result.total_cost        = count * cost_per_contract
        result.max_loss          = count * cost_per_contract
        result.allowed           = True
        return result

    def _size_budget(self,
                     premium: float,
                     grade: str = "B",
                     is_butterfly: bool = False,
                     net_debit: float = 0.0,
                     butterfly_half_size: bool = False,
                     stop_premium: float = 0.0) -> SizingResult:
        """
        Calculate whole contract count.

        Args:
            premium:             Option mark price (single leg)
            grade:               Setup grade (A or B — C is rejected upstream)
            is_butterfly:        True for butterfly (use net_debit)
            net_debit:           Net debit for butterfly (per share)
            butterfly_half_size: True when VIX 15-20 (halve butterfly size)
        """
        result = SizingResult(grade=grade)
        result.rule = "butterfly" if is_butterfly else "budget"

        cost_per_share = net_debit if is_butterfly else premium
        # ── r121 — THE DENOMINATOR IS THE RISK, WHEN ENABLED ──────────────
        # Premium is what the position COSTS; (premium - stop) is what it can
        # LOSE. Dividing the budget by cost sizes the position; dividing by
        # risk sizes the RISK, which is what RISK_PER_TRADE_USD claims to be.
        # Off by default — see config's SIZE_ON_RISK_TO_STOP for why the soft
        # stop makes this a deliberate choice rather than a correction.
        risk_per_share = cost_per_share
        if SIZE_ON_RISK_TO_STOP and stop_premium and stop_premium > 0:
            _r = abs(cost_per_share - float(stop_premium))
            # A stop at or beyond the premium leaves the full premium at risk —
            # fall back rather than divide by something tiny and size wildly.
            if 0 < _r < cost_per_share:
                risk_per_share = _r
        if cost_per_share <= 0:
            result.allowed       = False
            result.reject_reason = "zero_premium"
            return result

        cost_per_contract = cost_per_share * CONTRACT_MULTIPLIER
        risk_per_contract = risk_per_share * CONTRACT_MULTIPLIER
        grade_mult        = GRADE_SIZE_MULTIPLIER.get(grade, 1.0)

        # ⚠️ r122 — THE BUTTERFLY HALF-SIZE SURVIVES THE GRADE FLATTENING, and
        # deliberately. It is a VOLATILITY rule (VIX 15-20), not a grade rule,
        # so it is not the mechanism the operator retired. Operator, 2026-08-25:
        # "the butterfly is a debit, but I think we will need to see a few
        # trades before it earns a 1.0 sizing trait. The current is ok for that
        # one." AVGO has ONE butterfly all-time; the strategy has not earned
        # full size, and half-size is the conservative default while it proves
        # itself. Left multiplying grade_mult (now always 1.0) rather than
        # rewritten, so the two rules stay visibly separate.
        if is_butterfly and butterfly_half_size:
            grade_mult = grade_mult * 0.5

        count = contracts_from_risk(
            self._risk_per_trade, risk_per_contract, grade_mult
        )
        # ── r121 — THE DEPLOYMENT CEILING ────────────────────────────────
        # Applied AFTER the risk sizing so the intent is visible in the log:
        # this is what risk WANTED, and this is what ownership ALLOWS. Binding
        # is not an error and is not suppressed — a size that was cut is a
        # thing the operator should see, since it means the stop is tight
        # enough that risk-sizing has run past what he is willing to own.
        if SIZE_ON_RISK_TO_STOP and count > 0 and cost_per_contract > 0:
            _cap = int((self._risk_per_trade * DEPLOY_CAP_MULT) // cost_per_contract)
            if _cap < count:
                logger.info(
                    "Deploy cap binds: risk wanted %d contract(s) ($%.0f "
                    "deployed); cap %gx risk budget allows %d ($%.0f)",
                    count, count * cost_per_contract, DEPLOY_CAP_MULT,
                    _cap, _cap * cost_per_contract)
                result.deploy_capped = True
                count = _cap

        if count < 1:
            result.allowed       = False
            result.reject_reason = (
                f"insufficient_capital: need ${cost_per_contract:.2f}/contract, "
                f"risk=${self._risk_per_trade * grade_mult:.2f}"
            )
            return result

        total_cost = count * cost_per_contract

        result.contracts         = count
        result.cost_per_contract = cost_per_contract
        result.total_cost        = total_cost
        # max_loss stays the FULL premium: that is what a gap through a soft
        # stop actually costs, and the field is read by risk gates that must
        # assume the worst rather than the intent.
        result.max_loss          = total_cost
        result.risk_per_contract = risk_per_contract
        result.grade_multiplier  = grade_mult
        result.allowed           = True

        logger.info(
            f"Position size: {count} contract(s) × ${cost_per_contract:.2f} "
            f"= ${total_cost:.2f} total "
            f"grade={grade} mult={grade_mult}x "
            f"{'[BUTTERFLY HALF-SIZE]' if is_butterfly and butterfly_half_size else ''}"
        )
        return result

    def _size_vertical(self, spread_width: float, credit: float,
                                 grade: str = "B") -> SizingResult:
        """Size ONE condor vertical (credit spread) at the FULL grade budget.

        v3.2 (2026-07-23, user directive): was HALF. Each vertical is now sized
        as a standalone position, because that is what it usually IS — 18 of 46
        legs in the 07-07..07-22 sample never got a second side, so half-sizing
        chronically under-sized a structure that never existed.

        When both sides DO fill, the two verticals cannot both reach max loss
        at expiry (price can only be at one extreme), so the notional is less
        risky than 2x suggests. Caveat, stated honestly: a 25% stop that closes
        the tested side breaks that offset — 5 of 14 condor symbol-days in the
        sample had BOTH sides stopped on a whipsaw. Accepted with the ratcheting
        stop (exit_engine v4.1) as mitigation.
        Max loss per contract for a credit spread = (width - credit) x 100.
        """
        result = SizingResult(grade=grade)
        result.rule = "vertical"

        max_loss_per_contract = (spread_width - credit) * CONTRACT_MULTIPLIER
        if max_loss_per_contract <= 0:
            result.allowed       = False
            result.reject_reason = "non_positive_max_loss (credit >= width)"
            return result

        grade_mult  = GRADE_SIZE_MULTIPLIER.get(grade, 1.0)
        # v3.2: FULL budget per vertical (was * 0.5)
        leg_budget = self._risk_per_trade * grade_mult

        count = int(leg_budget // max_loss_per_contract)
        if count < 1:
            result.allowed       = False
            result.reject_reason = (
                f"insufficient_capital: vertical max_loss="
                f"${max_loss_per_contract:.0f} > leg_budget=${leg_budget:.0f}"
            )
            return result

        result.contracts        = count
        result.cost_per_contract = max_loss_per_contract
        result.total_cost       = count * max_loss_per_contract
        result.max_loss         = count * max_loss_per_contract
        result.grade_multiplier = grade_mult
        result.allowed          = True

        logger.info(
            f"Condor leg size: {count} vertical(s) x max_loss "
            f"${max_loss_per_contract:.0f} = ${result.total_cost:.0f} "
            f"(leg budget=${leg_budget:.0f}, grade={grade})"
        )
        return result

    def check_circuit_breaker(self) -> CircuitBreakerState:
        self._ensure_seeded()
        return CircuitBreakerState(
            session_losses=self._session_losses,
            session_halted=self._session_halted,
        )

    def _ensure_seeded(self):
        """Seed session net P&L from today's closed trades so the daily loss
        halt survives restarts within the same session."""
        if self._seeded:
            return
        # 🔴 CND.12 — _seeded was set BEFORE the read and the error swallowed,
        # so one unreadable DB at boot left session P&L at 0 for the whole
        # session with no retry. It is set only once the read SUCCEEDS; a
        # failure is logged and retried on the next call. (The daily-loss halt
        # itself is unaffected: is_halted() re-reads the DB on every call.)
        try:
            from database.trade_logger import get_trade_logger
            _tl = get_trade_logger()
            summary = _tl.today_summary()
            pnl = float(summary.get("total_pnl", 0.0) or 0.0)
            # r298 (CAP.4) — THE SEED IS THE CAP'S NUMBER, NOT THE DISPLAY'S. today_summary() counts every
            # strategy (the displays' figure); the cap excludes CAP_EXCLUDED_STRATEGIES (PARK, r288). Seeding
            # from the display meant a boot after a PARK loss past the limit read HALTED, and the first
            # is_halted() then logged a RE-ARMED event nothing had hit (audit 2026-10-18 A5 / T3-2).
            # The getattr keeps check_risk_seed_retry's shared fixture (a book with today_summary only)
            # honest; the production logger always has realized_pnl_today.
            _rp = getattr(_tl, "realized_pnl_today", None)
            if callable(_rp):
                pnl = float(_rp(exclude_strategies=getattr(config, "CAP_EXCLUDED_STRATEGIES", ("PARK",))))
            self._session_pnl_usd = pnl
            if self._session_pnl_usd <= -self._daily_loss_limit:
                self._session_halted = True
            self._seeded = True
        except Exception as exc:                                # noqa: BLE001
            logger.warning(f"risk seed: today's P&L unreadable ({exc}) — will retry")

    def record_loss(self, pnl_usd: float = 0.0):
        self._session_losses += 1
        self._reassess_requested = True
        # The halt decision comes from the DB (authoritative), not this counter.
        net = self.day_realized_pnl()
        logger.warning(
            f"Session loss #{self._session_losses} (${pnl_usd:+.0f}) — "
            f"day realized ${net:+.0f}; forcing reassessment"
        )
        self.is_halted()   # evaluate + fire the halt alert at close time

    def record_win(self, pnl_usd: float = 0.0):
        net = self.day_realized_pnl()
        logger.info(f"Session win (${pnl_usd:+.0f}) — day realized ${net:+.0f}")

    def _check_daily_loss_limit(self):
        """Back-compat shim — the authoritative check now lives in is_halted()."""
        self.is_halted()

    # ── r181 (ALRT.2) — the page is once per EPISODE, across restarts ────────
    def _cap_stamp_path(self) -> str:
        """data/CAP_PAGED beside the trades store the day's P&L is read from."""
        try:
            from database.trade_logger import get_trade_logger
            base = os.path.dirname(os.path.abspath(get_trade_logger().db_path))
        except Exception:                                      # noqa: BLE001
            from config import DB_PATH
            base = os.path.dirname(os.path.abspath(DB_PATH))
        return os.path.join(base, "data", "CAP_PAGED")

    @staticmethod
    def _et_date() -> str:
        try:
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        except Exception:                                      # noqa: BLE001
            return datetime.utcnow().strftime("%Y-%m-%d")

    def _cap_episode_open(self) -> bool:
        """True only when the stamp says TODAY's episode was paged and has not
        re-opened. Anything unreadable is False: a bad file never silences a page."""
        try:
            with open(self._cap_stamp_path(), encoding="utf-8") as fh:
                d, flag = fh.read().strip().split("|")
            return d == self._et_date() and flag == "1"
        except Exception:                                      # noqa: BLE001
            return False

    def _cap_stamp(self, open_: bool) -> None:
        try:
            p = self._cap_stamp_path()
            os.makedirs(os.path.dirname(p), exist_ok=True)
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(f"{self._et_date()}|{1 if open_ else 0}\n")
            os.replace(tmp, p)
        except Exception as exc:                               # noqa: BLE001
            logger.warning(f"[{INSTRUMENT}] cap stamp not written ({type(exc).__name__}: {exc}) "
                           f"- a restart may page this episode again")

    def _log_cap_event(self, reason: str, net: float) -> None:
        """r199 (AUD.7) — ONE ROW IN circuit_breaker_events PER CAP TRANSITION. The
        table has existed since v3, query.py shows it and s3_push pushes it, and
        TradeLogger.log_circuit_breaker had ZERO callers - so the only record of a
        cap episode was a log line and a page. Written where the page is decided
        (once per episode) and where the re-arm is logged. Never raises: a failed
        write warns and the halt decision is unaffected."""
        try:
            from database.trade_logger import get_trade_logger
            get_trade_logger().log_circuit_breaker(
                reason, int(self._session_losses),
                f"day realized {net:+.2f}; limit {self._daily_loss_limit:.2f}")
        except Exception as exc:                               # noqa: BLE001
            logger.warning(f"[{INSTRUMENT}] cap event NOT recorded ({type(exc).__name__}: {exc})")

    def note_entry_risk(self, record) -> None:
        """r208 (CAP.4) — THE CAP COUNTERFACTUAL, LOG-ONLY. One JSON line per entry in cap_cf_path().

        The cap halts on REALIZED loss, so the last entry before it can carry the day
        well past the limit (the 10-03 audit, A9). The operator ruled the entry stays
        allowed and asked for the study: what would a rule that refuses an entry whose
        planned risk exceeds the remaining headroom have refused, and what did those
        trades go on to do? This writes the left half; trades.db holds the right half.
          risk_stop = (entry - stop) x contracts x multiplier for a long option with a
                      premium stop; absent for a credit structure or a stopless trade
          risk_max  = the record's max_loss, else its total_cost
          headroom  = limit + day realized net (what is left before the halt)
        REFUSES NOTHING, gates nothing, never raises: a failed write warns."""
        try:
            def _f(k):
                try:
                    return float(record.get(k) or 0.0)
                except (TypeError, ValueError):
                    return 0.0
            net = self.day_realized_pnl()
            limit = float(self._daily_loss_limit)
            headroom = limit + net
            entry, stop, n = _f("entry_premium"), _f("stop_premium"), _f("contracts")
            credit = _f("credit_received") > 0 or bool(record.get("is_condor_leg"))
            risk_max = _f("max_loss") or _f("total_cost")
            risk_stop = None
            if not credit and 0 < stop < entry and n > 0:
                risk_stop = (entry - stop) * n * CONTRACT_MULTIPLIER
            exempt = 0
            try:
                from execution.position_manager import rules as _rules
                exempt = int(bool(getattr(_rules().get(str(record.get("strategy") or "")), "cap_exempt", False)))
            except Exception:                                   # noqa: BLE001
                exempt = 0
            basis = risk_stop if risk_stop is not None else risk_max
            import json as _json
            import time as _time
            row = {"ts_epoch": round(_time.time(), 3), "trade_id": str(record.get("trade_id") or ""),
                   "symbol": INSTRUMENT, "strategy": str(record.get("strategy") or ""),
                   "risk_stop": None if risk_stop is None else round(risk_stop, 2), "risk_max": round(risk_max, 2),
                   "realized": round(net, 2), "limit": round(limit, 2), "headroom": round(headroom, 2),
                   "refuse_stop": int(basis > headroom), "refuse_max": int(risk_max > headroom), "exempt": exempt}
            with open(cap_cf_path(), "a") as fh:
                fh.write(_json.dumps(row) + "\n")
        except Exception as exc:                               # noqa: BLE001
            logger.warning(f"[{INSTRUMENT}] cap counterfactual NOT recorded ({type(exc).__name__}: {exc})")

    def is_halted(self) -> bool:
        """Authoritative daily-loss gate. Reads today's realized net P&L from
        the DB on every call (single source of truth — identical to what
        query.py/status.py display), so it survives any restart and can't drift
        from an in-memory tally. Wins offset losses so a net-green day keeps
        trading.

        🔴 r162 — IT NO LONGER LATCHES. The operator, 2026-09-27: *"If the open
        TRADES put us back under the limit again after they close, it can open
        trades again."* The answer is recomputed every call: REALIZED net at or
        beyond -limit halts NEW entries; once closes bring the loss back under
        the limit, entries re-open. Open positions are never gated here.
        ⚠️ ONE PAGE PER EPISODE (WA 17): the page fires on the transition INTO
        the halt; the re-open is logged; a second breach later in the day is a
        new episode and pages again."""
        net = self.day_realized_pnl()
        self._session_pnl_usd = net   # keep the in-memory mirror truthful
        breached = net <= -self._daily_loss_limit
        # r181: an episode that ended (back under the limit) is closed on the
        # stamp too - including one paged by a process that has since restarted.
        if not breached and (self._session_halted or self._cap_episode_open()):
            self._cap_stamp(False)
        if not breached and self._session_halted:
            self._session_halted = False
            logger.warning(
                f"\u2705 [{INSTRUMENT}] DAILY CATASTROPHIC LOSS CAP RE-ARMED: day "
                f"realized ${net:+.0f} is back under the -${self._daily_loss_limit:.0f} "
                f"limit. New entries RE-OPENED."
            )
            self._log_cap_event("daily_cap_rearmed", net)        # r199
        if breached and not self._session_halted:
            self._session_halted = True
            # v-symbol 2026-08-03: NAME THE BOX. One symbol per box and 15 of
            # them can breach independently, so an unattributed alert forces a
            # fleet-wide hunt to find which one halted.
            logger.warning(
                f"\U0001F6D1 [{INSTRUMENT}] DAILY CATASTROPHIC LOSS CAP HIT: day "
                f"realized ${net:+.0f} <= -${self._daily_loss_limit:.0f}. Halting NEW "
                f"entries; open positions are still managed. Entries re-open if "
                f"closes bring the loss back under the limit."
            )
            if self._cap_episode_open():
                # r181 (ALRT.2): this episode was paged before a restart.
                logger.warning(f"[{INSTRUMENT}] cap episode already paged today "
                               f"(data/CAP_PAGED) - not paged again after a restart")
                return self._session_halted
            self._cap_stamp(True)
            self._log_cap_event("daily_cap_hit", net)            # r199: once per episode, with the page
            try:
                from notifications.alert_manager import get_alert_manager
                get_alert_manager()._send(
                    f"\U0001F6D1 {INSTRUMENT} DAILY CATASTROPHIC LOSS CAP HIT — day "
                    f"realized ${net:+.0f} (limit ${self._daily_loss_limit:.0f}). New "
                    f"entries halted; open positions still managed. Entries re-open "
                    f"if closes bring the loss back under the limit."
                )
            except Exception as exc:                           # noqa: BLE001
                # r199: was `pass` - a cap page that failed to send said nothing at all.
                logger.warning(f"[{INSTRUMENT}] cap page NOT sent ({type(exc).__name__}: {exc})")
        return self._session_halted

    def consume_reassess_request(self) -> bool:
        """Edge-triggered. True once after a loss requested a reassessment."""
        if self._reassess_requested:
            self._reassess_requested = False
            return True
        return False

    def reset_session(self):
        self._session_losses     = 0
        self._reassess_requested = False
        self._seeded             = False   # allow the DB re-seed to run
        # Re-derive halt state from the DB rather than blindly clearing it: on a
        # genuine new day realized P&L is 0 (no closed trades) and this clears;
        # on a mid-session restart it re-reads today's loss and STAYS halted
        # while the loss is at or beyond the limit (r162: the same rule
        # is_halted() applies every call, so the two can no longer disagree).
        self._session_pnl_usd    = self.day_realized_pnl()
        self._session_halted     = self._session_pnl_usd <= -self._daily_loss_limit
        logger.info(
            f"Risk manager session reset — day realized "
            f"${self._session_pnl_usd:+.0f}, halted={self._session_halted}"
        )

    @property
    def session_losses(self) -> int:
        return self._session_losses

    def status_report(self) -> str:
        net = self.day_realized_pnl()
        headroom = self._daily_loss_limit + net   # $ left before the halt
        return (
            f"risk=${self._risk_per_trade:.0f}/trade "
            f"day_realized=${net:+.0f} "
            f"daily_limit=${self._daily_loss_limit:.0f} "
            f"headroom=${headroom:.0f} "
            f"halted={self.is_halted()}"
        )


_risk_manager: Optional[RiskManager] = None


def init_risk_manager(risk_per_trade: float = RISK_PER_TRADE_USD,
                      paper_trading: bool = PAPER_TRADING) -> RiskManager:
    global _risk_manager
    _risk_manager = RiskManager(risk_per_trade, paper_trading)
    return _risk_manager


def get_risk_manager() -> RiskManager:
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager()
    return _risk_manager
