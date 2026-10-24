"""
strategy/base_strategy.py  v4.6
v4.6  2026-09-22  OTV4TEST r91 — THE OPERATOR'S 1-R, RESTORED. `stop_premium()`
      returns the IMPULSIVE CANDLE'S EXTREME converted through delta for the
      geometry-sized debits (ORB, Breakout) instead of a flat 25% of premium,
      and `entry_delta` is the new field that makes the conversion possible.
      🔑 THIS ALSO FIXES SIZING WITH NO NEW SIZER ARGUMENT: `_size_geometry`
      computes `(premium - stop_premium) * 100`, which with a FLAT stop is
      proportional to PREMIUM — the distance cancels and every fire lands on
      the same deployed dollars. MEASURED on 21 consecutive Breakout fires
      2026-09-21 10:13-10:18 ET: structural stop swung 0.07->0.70 (10x),
      geometry_wanted 1->59, deployed never left $4,080-$4,209. r44 asserted
      `premium - stop_premium` WAS the distance in premium terms; it was not,
      and is now. `trail_activation_premium()` returns the entry premium for
      those two strategies so the trail arms from the START (operator's
      ruling), every other strategy untouched at +50%.
v4.5  2026-09-19  OTV4TEST r61 (ENT.1) — `underlying_stop_is_thesis` added.
      The entry-underwater guard has to know whether a strategy's
      `underlying_stop` is a PRICE STOP or a THESIS LINE, because the column
      carries both. Defaults to False (a real stop, therefore checked) so the
      guard is opt-OUT: a new strategy is protected without doing anything.
v4.4  2026-09-01  r207 — OptionsSignal gains `orb_stop_distance_px`: the
      impulsive wick measured from the boundary it broke, frozen by the engine
      at break time. ⚠️ RECORDED, NEVER READ IN A DECISION — sizing stays on
      |entry - stop| per the operator, because the stop is a price level and
      what is at stake is the gap between the FILL and it. This field answers
      r119's separate question, how deep inside the range the invalidation
      sits, and check_orb_sequence S8 fails if anything ever sizes off it.
v4.3  2026-08-24  r99 — is_valid's credit-vertical arm accepts a ONE-SIDED
      vertical (the only shape any writer produces since r90) and FAILS CLOSED
      on a naked short, a wing without a short, or a wing inside the short.
      Was demanding all four contracts, so every sweep and fork signal died as
      `Invalid signal`. Pinned by tests/check_sweep_spread.py.
v4.2  2026-08-24  CONDOR REMODEL: add condor_trigger_source to OptionsSignal
      so every credit spread records which trigger fired it (1h_fork, 1d_fork,
      sweep_reversal, trend_orb) enabling per-source grading. Paired with the
      same column in trades (trade_logger v4.2).
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Signal dataclass and the strategy interface.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

strategy/base_strategy.py — Abstract base and OptionsSignal for all strategies.
v3.0 — original release
added orb_range_high/low fields to OptionsSignal for
        strategy-aware exit routing in exit_engine.py
added 4-leg fields for IronCondorStrategy (RANGING
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
"""
# v-obs2 (2026-07-24) — OptionsSignal carries swept_level_name + level_strength for sweep level postmortems.



from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List

from data.options_chain import OptionContract, OptionsChain
from analysis.orb_engine import ORBData


@dataclass
class OptionsSignal:
    """
    A candidate options trade proposal.
    Validated and sized before reaching execution.
    """
    # ── Strategy identity ────────────────────────────────────────────────
    strategy_name:  str   = ""
    setup_type:     str   = ""

    # ── Direction ─────────────────────────────────────────────────────
    direction:      str   = ""      # "long" or "short" (of the UNDERLYING)
    option_side:    str   = ""      # "call" or "put"

    # ── Underlying price levels ─────────────────────────────────────────────
    underlying_entry:   float = 0.0
    underlying_stop:    float = 0.0
    # 🔴 ENT.1 (r61) — IS `underlying_stop` A PROTECTIVE STOP, OR A THESIS LINE?
    # It is not the same quantity in every strategy. ORB and Breakout write a
    # PROTECTIVE stop (the impulsive/acceptance candle's extreme) — price on the
    # far side of it means the trade is already stopped. LiquidityHunt writes
    # `prep.boundary`, the ORB edge it is fading, and entry BEYOND that boundary
    # is the setup's NORMAL state (measured: 3 of 8 banked hunt rows).
    # ⚠️ DEFAULT False = "this IS a protective stop" = CHECKED. The opt-out is
    # deliberate: a NEW strategy inherits the guard and must argue its way out,
    # which is the only way "this should NEVER happen" survives a new file.
    underlying_stop_is_thesis: bool = False
    underlying_target:  float = 0.0
    underlying_tp50:    float = 0.0

    # ── ORB range boundaries (ORB trades only) ──────────────────────────────
    # r120 — the window and the scale the tape measurement needs. WITHOUT these
    # the measurement silently falls back to "last 15 minutes, price-relative
    # band", which measures a DIFFERENT THING than the contested level and
    # would look like a valid reading. A wrong number is worse than none.
    orb_break_ts: float = 0.0      # epoch of the confirming break
    atr_at_signal: float = 0.0
    orb_range_high: float = 0.0
    orb_range_low:  float = 0.0
    # r207 — the FROZEN sizing geometry: |impulsive wick - the boundary it
    # broke|, set by orb_engine at break time. The sizer reads THIS, never
    # |current_price - underlying_stop|, which floated with the fill price and
    # sized a re-entry twelve times larger than the trade that just failed.
    orb_stop_distance_px: float = 0.0

    # ── Option details (single-leg) ───────────────────────────────────────
    strike:         float = 0.0
    expiry:         str   = ""
    entry_premium:  float = 0.0
    contract:       Optional[OptionContract] = None

    # ── Butterfly legs (3-leg) ─────────────────────────────────────────
    is_butterfly:        bool  = False
    lower_contract:      Optional[OptionContract] = None
    center_contract:     Optional[OptionContract] = None
    upper_contract:      Optional[OptionContract] = None
    butterfly_direction: str   = ""
    net_debit:           float = 0.0
    max_profit:          float = 0.0

    # ── Iron Condor legs (4-leg) ─────────────────────────────────────
    # Credit spread: sell short put + buy long put (lower side)
    #                sell short call + buy long call (upper side)
    # ⚠️ RENAMED FROM `is_iron_condor` (TCS.1, 2026-08-14). It NEVER meant "this
    # is a condor" — every use below selects CREDIT-SPREAD MATH: validity by four
    # legs, stop as a RISING spread value, TP as decay toward zero. The old name
    # is why TrendCreditSpread had to declare itself a condor to get correct
    # arithmetic, which is the coupling that produced the 2026-08-14 identity
    # bug. `is_iron_condor` is kept as a read/write ALIAS below so no caller
    # breaks mid-flight.
    is_credit_vertical:   bool  = False
    short_put_contract:   Optional[OptionContract] = None
    long_put_contract:    Optional[OptionContract] = None
    short_call_contract:  Optional[OptionContract] = None
    long_call_contract:   Optional[OptionContract] = None
    net_credit:           float = 0.0   # Total credit received (premium collected)
    max_loss_condor:      float = 0.0   # Wing width - net credit (per side, worse side)
    expected_move:        float = 0.0   # ATM straddle-derived expected move at entry
    expected_move_mult:   float = 0.0   # short strike distance / expected move (guardrail check)

    # ── Risk / sizing ────────────────────────────────────────────────
    contracts:      int   = 0
    total_cost:     float = 0.0
    max_loss:       float = 0.0
    stop_loss_pct:  float = 0.25
    tp_pct:         float = 1.0
    # 🔴 r91 — THE CONTRACT'S DELTA AT SELECTION, AND IT IS A SIZING INPUT.
    # It converts the STRUCTURAL stop (|entry - impulsive candle extreme|, in
    # underlying points) into PREMIUM terms, which is what `stop_premium()`
    # needs to be the structure stop rather than a flat percentage. Without it
    # the 1-R the operator specified cannot reach the sizer at all — see the
    # note on `stop_premium`. Stamped by the geometry-sized strategies from
    # `contract.delta`, the same attribute `main.py` already reads when it
    # writes `entry_delta` to the row. None means UNAVAILABLE and the stop
    # falls back to the percentage, never to a guess.
    entry_delta:    Optional[float] = None

    # ── Quality ─────────────────────────────────────────────────────
    confluence_factors: List[str] = field(default_factory=list)
    conviction:     float = 0.0
    # ⚠️ r152 — the A/B grade is REMOVED (setup_scorer deleted). The field
    # survives because the DB schema and every dashboard read it; UNGRADED is a
    # marker that no selector ran, not a verdict.
    setup_grade:    str   = "UNGRADED"

    # ── Context ──────────────────────────────────────────────────────
    adx_at_signal:  float = 0.0    # v-obs: ADX at entry, for tape-context analysis
    flat_angle_deg: float = 0.0    # v-obs: flat-angle at entry (0 if unavailable)
    swept_level_name: str = ""     # v-obs: name of swept level (PDH/PDL/session) — '' if equal-H/L
    level_strength:   float = 0.0  # v-obs: 0..1 conviction of the swept level (named+touches)
    vix_at_signal:  float = 0.0
    is_fed_day:     bool  = False
    notes:          str   = ""

    # ── Condor / vertical pairing ─────────────────────────────────────────
    # Which trigger produced this spread. Written to the trades row so each
    # leg can be graded independently (the point of this remodel).
    # Values: "1h_fork", "1d_fork", "sweep_reversal", "trend_orb", "".
    # Empty on non-credit-spread signals.
    condor_trigger_source: str = ""

    @property
    def is_orb(self) -> bool:
        return self.strategy_name == "ORBStrategy"

    @property
    def is_sweep(self) -> bool:
        return self.strategy_name == "SweepReversal"

    @property
    def is_valid(self) -> bool:
        if self.is_butterfly:
            return (
                self.butterfly_direction in ("call", "put") and
                self.net_debit > 0 and
                self.lower_contract is not None and
                self.center_contract is not None and
                self.upper_contract is not None
            )
        if self.is_credit_vertical:
            # r99 — A VERTICAL IS VALID WHEN THE SIDE IT HAS IS COMPLETE. The
            # old arm demanded all four contracts, written when this dataclass
            # described a whole condor. r90 made every vertical autonomous —
            # "leg 2 is permitted, not implied" — and changed the WRITERS
            # (sweep, forks, TC.6 all set ONE side) without grepping this
            # reader. Every sweep died as `Invalid signal` (SPX 231x, GOOGL
            # 90x on 2026-08-24). Per side, never "any two contracts present".
            # ⚠️ FAILS CLOSED ON A NAKED SHORT: a short with no wing, or a wing
            # inside the short (a debit spread wearing a credit flag), is
            # undefined risk and never validates.
            return self._credit_side_ok("call") or self._credit_side_ok("put")
        return (
            self.option_side in ("call", "put") and
            self.strike > 0 and
            self.entry_premium > 0 and
            self.underlying_entry > 0
        )

    def _credit_side_ok(self, side: str) -> bool:
        """r99 — one side of a credit vertical is complete: a short, a
        protective wing beyond it, and a positive credit. Any side that is
        PRESENT but incomplete poisons the whole signal (a naked short on the
        put side is not rescued by a clean call side)."""
        if not (self.net_credit > 0):
            return False
        sc, lc = self.short_call_contract, self.long_call_contract
        sp, lp = self.short_put_contract, self.long_put_contract
        # A wing with no short, or a short with no wing, on EITHER side: fail.
        if (sc is None) != (lc is None) or (sp is None) != (lp is None):
            return False
        if sc is None and sp is None:
            return False
        try:
            if sc is not None and not (float(lc.strike) > float(sc.strike)):
                return False                       # call wing must sit ABOVE
            if sp is not None and not (float(lp.strike) < float(sp.strike)):
                return False                       # put wing must sit BELOW
        except (TypeError, ValueError, AttributeError):
            return False
        return (sc is not None) if side == "call" else (sp is not None)

    @property
    def is_iron_condor(self) -> bool:
        """Back-compat alias. ⚠️ Both names address ONE field — a caller setting
        either gets identical behaviour, so a missed rename cannot produce a
        signal that is a credit vertical to one half of the system and a debit
        to the other. That divergence is precisely what the rename exists to
        make impossible."""
        return self.is_credit_vertical

    @is_iron_condor.setter
    def is_iron_condor(self, v: bool) -> None:
        self.is_credit_vertical = bool(v)

    def sizes_on_structure(self) -> bool:
        """True for the geometry-sized debits: ORB and Breakout.

        ⚠️ THE SAME TEST `main.py` USES TO SUPPLY THE GEOMETRY INPUTS, and it
        is deliberately the same shape rather than a second list that later
        rots (§23). A strategy that opts into geometry sizing opts into the
        structural stop with it — the two are one decision, not two.
        """
        return bool(getattr(self, "strategy_name", "") == "ORBStrategy"
                    or getattr(self, "sizes_on_geometry", False))

    def structural_stop_premium(self) -> Optional[float]:
        """The impulsive candle's extreme, converted to PREMIUM. None if unusable.

        🔴 r91 — THE OPERATOR'S 1-R, RESTORED. His specification, 2026-09-22:
        *"position sizing was supposed to be based on the stop distance
        represented by the entry point measured down to the extreme of the
        impulsive candle. That distance is our 1-R."* Deep candle -> wide stop
        -> small position; extreme hugging the boundary -> tight stop -> scale
        up.

        🔑 WHY THIS ONE METHOD ALSO FIXES SIZING, WHICH IS THE WHOLE POINT.
        `_size_geometry` computes `_rpc = (premium - stop_premium) * 100`. When
        `stop_premium` is a flat fraction of premium, that term is proportional
        to PREMIUM and the distance CANCELS — every fire lands on the same
        deployed dollars no matter what the structure says. MEASURED on 21
        consecutive Breakout fires, 2026-09-21 10:13-10:18 ET: the structural
        stop swung 0.07 -> 0.70 (10x), `geometry_wanted` swung 1 -> 59, and
        deployed capital never left $4,080-$4,209. When `stop_premium` is THIS
        value, `premium - stop_premium` IS `distance x delta`, and the sizer
        needs no new argument to do what the operator asked.

        🔴 r44 ASSERTED THIS WAS ALREADY TRUE AND IT WAS NOT. Its own comment
        reads *"`by_risk` is also proportional to 1/distance, because
        `premium - stop_premium` IS the distance in premium terms"* — true only
        if the stop is structural, and it never was. r44 caught the identical
        flattening for `stop_premium = 0` and fixed that case; `k x premium`
        flattens the same way and was not considered. `check_orb_budget` could
        not catch it because its helper passes NO stop premium, so every check
        in that file exercises the fallback branch and never the live one.

        ⚠️ FAILS CLOSED TO THE PERCENTAGE, NEVER TO A GUESS (§22). No delta, no
        distance, or an arithmetic result that is not a usable stop (at or
        below zero, or at or above the entry premium) returns None and the
        caller keeps today's behaviour. Inventing a delta would size real money
        on a number nobody measured.
        """
        if not self.sizes_on_structure():
            return None
        try:
            entry = float(self.underlying_entry or 0.0)
            stop  = float(self.underlying_stop or 0.0)
            delta = abs(float(self.entry_delta or 0.0))
            prem  = float(self.entry_premium or 0.0)
        except (TypeError, ValueError):
            return None
        if not (entry and stop and delta > 0 and prem > 0):
            return None
        move = abs(entry - stop) * delta          # underlying points -> premium
        if move <= 0:
            return None
        if move >= prem:
            # 🔴 THE STOP IS FURTHER AWAY THAN THE OPTION IS WORTH, AND THE
            # HONEST 1-R IS THEN THE WHOLE PREMIUM. Returning None here — my
            # first cut — fell back to the flat 25% stop and UNDERSTATED RISK
            # BY 4x: measured at distance 2.00, delta 0.40, premium 0.80, the
            # fallback sized 52 contracts and called it $1,040 at risk when
            # reaching that stop costs the full $4,160. Sizing small is the
            # operator's rule for a deep candle; sizing LARGE on a stop that
            # cannot be reached without total loss is its exact inversion.
            # ⚠️ A CENT, NOT ZERO, AND THE REASON IS A FALSY TEST. `exit_engine`
            # reads `record.get("stop_premium", 0.0) or entry * (1 - MAX_LOSS_PCT)`
            # in two places, so a 0.0 stop is FALSY and silently restores the
            # very percentage stop this removes (§23). One tick is the smallest
            # truthy value that still means "worthless at the structure stop",
            # and it makes risk-per-contract the full premium less one tick.
            return 0.01
        sp = prem - move
        # A structural stop at or above the entry premium is not a stop.
        if sp <= 0 or sp >= prem:
            return None
        return sp

    def stop_premium(self) -> float:
        """Premium level at which we exit.

        🔴 r91 — STRUCTURAL FOR THE GEOMETRY-SIZED DEBITS, percentage for
        everything else. Operator, 2026-09-22: *"I don't want the 25% premium
        stop anymore... If it doesn't move the structure stop will catch it and
        if it does move the 25% trailing stop will lock it in."* This is the
        first half: the entry-time floor becomes the impulsive candle's
        extreme. The trail is the second half and lives in `exit_engine`.

        ⚠️ THE VALUE CHANGES; THE CONTRACT DOES NOT. Roughly a dozen sites in
        `exit_engine` and `position_manager` read `stop_premium` as *"the
        immutable entry-time floor"* and two of them fall back to
        `entry_prem * (1 - MAX_LOSS_PCT)` when it is absent — so REMOVING the
        percentage stop would have silently reinstated it and looked like the
        change worked (§23). It is re-anchored, not deleted.
        """
        if self.is_butterfly:
            return self.net_debit * (1 - self.stop_loss_pct)
        if self.is_credit_vertical:
            # For a credit spread, "loss" means the spread VALUE rises
            # (we sold it, so rising value = losing money). Stop level
            # is expressed here as the spread value at which we exit.
            return self.net_credit * (1 + self.stop_loss_pct)
        _structural = self.structural_stop_premium()
        if _structural is not None:
            return _structural
        return self.entry_premium * (1 - self.stop_loss_pct)

    def trail_activation_premium(self) -> float:
        """Premium level at which trailing stop activates (50% TP)."""
        if self.is_butterfly:
            return self.net_debit + self.max_profit * 0.5
        if self.is_credit_vertical:
            # Condor profits as the spread value DECAYS toward zero.
            # 50% TP = spread value has decayed to 50% of credit received.
            return self.net_credit * 0.5
        if self.sizes_on_structure():
            # 🔴 r91 — ARMED FROM ENTRY. Operator, 2026-09-22: *"currently the
            # trail activation is at the 50. But I want it from the start."*
            # This is the ARM POINT only; where the trail SITS is
            # `exit_engine._update_trail`, which seeds it on the structure stop
            # and ratchets `peak x 0.75` — the separation `limit_ladder`'s own
            # header insists on, a trigger never anchoring a price.
            # ⚠️ RETURNING THE ENTRY PREMIUM, NOT ZERO, IS THE POINT. The trail
            # arms only once the trade is at or above entry, so a position that
            # goes straight down never arms it and the STRUCTURE STOP catches
            # it — which is exactly the behaviour the operator described.
            return self.entry_premium
        return self.entry_premium * (1 + self.tp_pct * 0.5)

    def target_premium(self) -> float:
        """Full TP premium target."""
        if self.is_butterfly:
            return self.net_debit + self.max_profit * self.tp_pct
        if self.is_credit_vertical:
            # TP = spread value has decayed to (1 - tp_pct) of credit.
            # e.g. tp_pct=0.50 means close at 50% of max profit captured,
            # i.e. spread value has fallen to 50% of the credit received.
            return self.net_credit * (1 - self.tp_pct)
        return self.entry_premium * (1 + self.tp_pct)


class BaseOptionsStrategy(ABC):
    """Abstract base for all options strategies."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def generate_signal(self, *args, **kwargs) -> Optional[OptionsSignal]: ...

    def _add_confluence(self, signal: OptionsSignal, factor: str):
        signal.confluence_factors.append(factor)
