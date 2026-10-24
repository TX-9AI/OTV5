"""
strategy/gex_pin_butterfly.py  v5.11
v5.11  2026-10-19  OTV4TEST r303 (PSTATE.1) — the `enabled` condition is met when the plan is ACTIVE (ENABLED, as before)
      or switched to LOG (OT_GEX_BUTTERFLY=log): LOG reaches take(), which records LOG-ONLY, and main refuses the
      signal at _execute_entry_signal. A DORMANT fly is never asked (main._safe_strategy).
v5.10  2026-10-03  OTV4TEST r225 (FLY.2) — leg_quote_facts: on the wings it picks, the plan RECORDS how many bought wings had no bid and whether a strict (all three two-sided) or a role (wings need an ask, the sold body a bid) rule would have refused. Log-only for two weeks by ruling; nothing is gated.
v5.9  2026-10-03  OTV4TEST r223 (EM.1) — expected_move delegates to analysis.volatility_measures.expected_move_session (moved verbatim; the 15-minute floor and the 3 h fallback are unchanged).
v5.8  2026-10-03  OTV4TEST r193 (CFG.1) — its config dials are read as config.NAME with NO literal fallback; config v4.48 now defines them (they were getattr defaults on names config never had). Values unchanged.
v5.7  2026-10-02  OTV4TEST r185 (LADR.1) — `_chain_increment` IS NOW AN ALIAS of
      data/options_chain.chain_increment, where the r198 body moved verbatim
      so every caller reads one ladder reader (shared with otv4). No wing,
      apex or gate here changes; check_butterfly_wing_grid W1-W6 still hold.
v5.6  2026-09-26  OTV4TEST r148 (WIN.1) — reads its entry window from config with NO literal fallback (one table, config.ENTRY_WINDOWS); a missing name now fails at import instead of silently defaulting. Value unchanged. GEX_BFLY_LATEST_ET never existed in config; the 15:00 lived here.
v5.5  2026-09-17  OTV4TEST r31 (BFLY.7) — THE PINNING REGIME IS RECORDED, AT ZERO WEIGHT.
      This fly reads the pin STRIKE and the CONCENTRATION at it and has never read
      whether the regime that does the pinning EXISTS or is collapsing. They are
      different axes and 2026-09-16 shows it rather than asserting it: conc
      0.06-0.17 (NEUTRAL, weak) all day against chain net gamma +71M to +123M
      (strongly pinning) — six hours of disagreement — then net gamma crossed ZERO
      at 15:00 (-129M in fifteen minutes) and QQQ went 709.65 to 700.00 in the next
      twenty. The premium stop prices that AFTER the tent is left; the regime
      crossing zero is the CAUSE. `derived/gamma_regime.read()` is stamped through
      `anchors.stamp` as record-only checks (verdict None), so it is scored against
      fires, DECLINEs and HOLDs alike.
      🔴 NOTHING IS SIZED BY IT: `GAMMA_RAMP_WEIGHT` is 0.0, so `ramp()` returns
      exactly 1.0 for every score (§31 — a number never tested against P&L does not
      size anything). BFLY.8 records that the hypothesis behind it was REFUTED on
      421 fleet trades and its reverse killed by confounds, so the weight stays 0.
v5.4  2026-09-14  OTV4TEST r26 — PIN STRENGTH IS ONE FUNCTION, SHARED WITH THE ATP BUTTERFLY.
      r25's inline concentration-or-VWAP-band block is lifted, unchanged in
      behaviour, into module-level `pin_strength(t, pin, conc, em)`, which
      `strategy/atp_butterfly_plan.py` also calls — so the two butterflies can
      never disagree about what a strong pin is. check_bfly_vwap_band and
      check_plan_prepares' butterfly cases are the regression net.
v5.3  2026-09-13  OTV4TEST r25 — A PIN AT VWAP WAIVES THE CONCENTRATION FLOOR (BFLY.5).
      Operator: "VWAP replaces the floor if the pin is w/in a predefined portion
      of VWAP" and "W/in 20% of the expected move, expressed as 10% above, 10%
      below" — so `pin_concentration` is met by conc >= PIN_CONC_MIN OR
      |pin - VWAP| <= VWAP_BAND_EM_FRAC x EM. WHICH VWAP, on his rule "the minimum
      measurement anchored to a derived value that would have allowed that
      fly": the bot's own midnight-ET-anchored VWAP (indicator_series primary).
      Friday 09-11 12:02 ET, pin 715, EM 5.48, band ±0.55: that VWAP read 715.35
      (0.35 off, waived); a 09:30 session VWAP read 715.59 (0.59, would have
      missed); a "pin inside the 5m Bollinger channel" test also passed but
      spans ~3.8 points against a 1.1-point band — looser, not minimal. On Friday
      the waiver matters on exactly the 27 PREPARED ticks where concentration
      was the ONLY failing gate: 12:02-12:07 are waived, 13:25-13:32 (band
      ±0.38, VWAP 0.41 off) are not. Wed and Thu had no such tick.
      ⚠️ FAILS CLOSED ON "NOW": the VWAP is read through `anchors.vwap_now()`,
      which returns nothing for a prior session's anchor or a stale bar — the
      engine keeps writing Friday's VWAP all weekend, and a "latest row" read
      would have waived Monday's open on it. The floor itself is unchanged and
      still FOUNDATIONAL: the waiver is a second way to MEET the condition, not
      a relaxation, and `relaxed_bounds()` does not move it. The distance is
      recorded on every tick as `pin_vwap_dist`, and a waived fire says so on
      its row.
v5.2  2026-09-13  OTV4TEST r24 — THE FLOOR IS 40% (operator's ruling); both readers of
      `BUTTERFLY_STOP_LOSS_PCT` — the signal's stop and the wing search's
      stop-vs-spread feasibility — default to the ruled 0.40, so a box without
      the key cannot disagree with one that has it.
v5.1  2026-09-09  OTV4TEST r12 — anchors on the row (record only): GEX at the pin, VWAP
      distance to the pin, OI at the pin.
v5.0  2026-09-09  OTV4TEST r6 — THE BUTTERFLY ON THE OPERATOR'S RULINGS
      (PLAN_SPEC §32). Anchor = the pin only; regime PINNING; reachable = EM
      0.30–1.00, FIRM (no live relaxed call was left here after r321 —
      confirmed by reading, and now stated). (1) PERSISTENCE, SMOOTHED: the
      acting pin is the MODE of the last SMOOTH_WINDOW instant pins and must
      have held PERSIST_TICKS ticks — a new condition `pin_persistence`; the
      instant pin is recorded as `pin_raw`. (2) BEST PAYOFF ASYMMETRY: every
      listed width is priced (unchanged) and the pick is the MAX R among those
      that clear R_FLOOR and the stop-vs-spread floor — "narrowest first" is
      superseded. (3) OI IS A STARVED INPUT: zero open interest across the
      chain -> NO PLAN starved open_interest, every tick, so the park is a
      fact the row states and un-parks itself when real OI arrives (it did,
      2026-09-09: 226 non-zero strikes by 15:43). (4) ONE PER SESSION, NO
      ADDITIONAL ATTEMPTS: main.py's r179 DB-backed session cap is the lock
      (one owner; a second in-process flag was built and removed in the same
      revision — it blocked nothing the cap does not). Exits unchanged (15% stop = the dead-thesis stop, 15:45). Entry
      unchanged: the whole position through the ladder walk.
v4.9  2026-09-01  r215 — RECORD-ONLY: `pin_dist_pct` and `pin_strike_raw` are
      written to plan_check on every evaluation. `pin_strike` is now BOUNDED to
      PIN_MAX_DIST_PCT of spot in compute_gex (see data/gex_data.py) because
      the argmax was unbounded and wandered — GOOGL published twenty distinct
      pins spanning 245-450 in one session against a ~345 price. That bound is
      a PRIOR; these two checks put the evidence in the warehouse so it can be
      fitted against outcomes rather than defended, the same discipline r208
      applied to EM_MAX_FRAC. NEITHER GATES ANYTHING.
      ⚠️ AND THE REACH GATE HAS BEEN DOING THIS JOB BY ACCIDENT. A wandering
      pin lands far from spot, inflating `pin_em_fraction`, which EM_MAX_FRAC
      then refuses — so EM_MAX_FRAC has been filtering mis-located pins as a
      side effect, with no one aware of it. Anyone loosening that bound on
      reachability grounds must know it was also the pin's sanity check.
gex_pin_butterfly.py  v4.8
v4.8  2026-09-01  r208 — THE WING IS SEARCHED, THE FLOOR MUST CLEAR THE
      SPREAD, AND RELAXED IS GONE FROM THIS STRATEGY.
      🔴 2026-09-01: five flies fired at 12:00:00 and three were stopped out
      INSIDE THE SAME MINUTE — META 577.5 debit 0.17 (25% floor = 4.3c), CRM
      0.21 (5.3c), MU 0.28 (7.0c). A fly's value is `lower + upper -
      2*center`, a small difference of three larger numbers, so THREE legs of
      quote noise compound into a figure itself worth 17 cents. They were not
      stopped by price; they were stopped by their own marks.
      🔑 R AND SURVIVABILITY PULL OPPOSITE WAYS AND ONLY R WAS WIRED. R rises
      as the wing narrows; survivability falls. So the selector steered to the
      LEAST survivable structure available and called it best — META at R 10.8
      was not a fly that happened to be fragile, it was the most fragile
      constructible fly, chosen because it was. Both bounds together require
      width >= 64 x leg-spread, so on a wide-spread symbol NO wing qualifies,
      which is reported as a definite answer rather than a fallback.
      · `stop_survivable` (r154, one caller until now — the sweep) is wired
        here as FEASIBILITY. The butterfly was not even on r154's untouched
        list because on 2026-08-27 it had never fired.
      · `WING_EM_FRAC` DELETED. The wing is searched over the chain's LISTED
        strikes — R_FLOOR caps the wide side, survivability floors the narrow
        side, narrowest qualifying wing wins. Operator: "the wings should be
        a 1-R or better (that's the widest allowed) but prefer narrower."
      · Candidates come from the strikes themselves, NOT from a stride of
        `_chain_increment`'s median gap: a mixed ladder would let the stride
        step PAST listed wings — r198's C.29 in a new costume. `inc` survives
        for reporting only.
      · RELAXED IS REMOVED ENTIRELY from this file (no widen, no window, no
        tag). Operator: "reachability and pin strength are synonymous with
        possible — if either is a no it's much less possible", and the
        butterfly is ONE PER SESSION, so relaxing a dial does not collect a
        marginal trade, it SPENDS the day's only slot on one.
      · GATES: EM_MAX_FRAC, PIN_CONC_MIN and LATEST_ET all SELECTION ->
        FOUNDATIONAL, reversing r196 on the last of those.
v4.7  2026-08-31  r198 — THE WINGS ARE SNAPPED TO THE CHAIN'S REAL STRIKE
      LADDER. `config.STRIKE_INCREMENT` is one global number for fifteen
      symbols and `round_to_strike()` returns an int, so every wing was
      quantised to whole dollars: PLTR pin 190 -> legs 189/191 on a $2.50
      ladder, AMD pin 472.5 -> legs 470.5/474.5. Neither pair exists, and the
      `legs` gate refused for 242 and 243 MINUTES on 2026-08-31 for an
      arithmetic reason, not a market one. 🔑 THE APEX NEVER MOVES — both
      pins were listed strikes; only the wings were off-grid, so the
      nearest-strike-substitute doctrine is untouched. ⚠️ A wider-than-
      intended wing is ACCEPTED by operator ruling and recorded (intended,
      grid, stretch) so the metrics can settle whether it is viable.
v4.6  2026-08-31  r196 — THE NOON FLOOR IS HARD. Operator, on the first live
      open, seeing butterflies fire at 09:45: "the noon floor is
      non-negotiable." 🔴 That 09:45 is `relaxed.window()`'s relaxed_earliest
      default EXACTLY — the fires were the relaxed floor, not a pin forming
      early. EARLIEST_ET moves SELECTION -> FOUNDATIONAL and is passed as its
      own relaxed value so it cannot widen. LATEST_ET stays relaxable.
      🔑 THE RULE THIS TEACHES: relax DIALS, never STRUCTURAL gates. A dial's
      near-misses tell you whether the line is right; a structural gate's
      "near-misses" are a different trade entirely. And think twice before
      relaxing anything on a strategy with a SESSION CAP — there, a relaxed
      gate does not collect a sample, it SPENDS the sample.
v4.5  2026-08-29  r178 — 🔴 ONE BUTTERFLY PER PIN PER SESSION. The hour
      r177 unblocked the starved atm_iv, the strategy fired the SAME UNH
      397.5 fly five times in ninety seconds: the additive exemption (r161)
      let it stack ITSELF and it had no self-lock — it had never once fired
      to need one. PLAYED_PINS registry: a fire marks the pin played (from
      the dispatch, on the signal's pin); prepare() declines a played pin
      STRUCTURALLY (relaxed does not waive it), checked before the
      conditions. A NEW pin is a new trade. In-process; a restart clears it.
v4.4  2026-08-27  r161 — THE PLAN PREPARES, THE STRATEGY EXECUTES; EXEMPT FROM
      THE SINGLE-POSITION RULE. Operator, 2026-08-27: *"I want it to be able
      to fire regardless if any other open trades are found. Reason: it has
      such a high hurdle to clear. GEX pinning, pin reachable, economic
      feasibility. If it can achieve all that, it's earned an entry."*
      `prepare()` is the plan (the sweep's v4.6 shape): DORMANT outside the
      slot; each declared CONDITION with its current reading; the three legs
      SELECTED (apex on the pin, wing from the expected move, exact strikes);
      R = (width-debit)/debit against R_FLOOR as a STRUCTURAL check — the
      operator's third hurdle, so relaxed does not waive it (v4.3 routed it
      through the muteable hurdle; that was wrong for a trade whose entry
      is EARNED by feasibility). `generate_signal()` executes the prepared
      legs. main.py v4.19 asks it every tick of its slot whether or not a
      position is open, and appends its record (position_manager v4.4).
v4.3  2026-08-26  r147 — UNPARKED, AND IT HAS LEGS. Operator: *"I want it
      active. It already has to clear a high bar to fire. The r-value in
      strict should veto, but allow and record on relaxed. The pin should be
      reachable & the strikes should be relatively narrow but not so narrow
      that it has zero breathing room. Purchased as a debit call butterfly
      for below the pin, and put for [above] the pin."*
      · `ENABLED` now reads config.GEX_BUTTERFLY_ENABLED, default ON.
      · THE LEGS: apex ON the pin; wings at ⟨PRIOR⟩ WING_EM_FRAC (0.25) of
        the expected move, rounded to the strike increment, floor ONE
        increment (breathing room), ceiling the distance to the pin (the
        near wing never crosses spot). Call fly when spot is BELOW the pin,
        put fly when spot is ABOVE it — price travels to the magnet.
      · EXACT STRIKES ONLY. `select_butterfly_strikes` centres on spot and
        falls back to the nearest liquid strike; both would silently move the
        apex off the pin, which is the FOUNDATIONAL condition. Three priced
        contracts at exactly lower/pin/upper, or no trade.
      · net_debit = lower.mark − 2·center.mark + upper.mark; max_profit =
        width − debit; R = (width − debit)/debit through the plan, so STRICT
        vetoes below 1:1 and RELAXED records (`r_muted`). debit/width is
        recorded against BUTTERFLY_MAX_DEBIT_PCT_WIDTH as a check, NOT a
        gate — the R hurdle is the economic gate, one rule fleet-wide.
      · The signal is now VALID: is_butterfly, three contracts, direction,
        net_debit — `is_valid`'s butterfly arm is satisfied and
        entry_engine's `_place_butterfly` runs it unchanged.
v4.2  2026-08-26  r146 — THE PLAN IS WIRED. Every refusal (parked, no GEX,
      not PINNING, pin strength, window, no expected move, pin too near/far)
      goes through `self.planner` (strategy/plan.py) and writes a DECLINE row
      naming the gate; `_gate()` kept as an alias. ⚠️ THE WHAT-IF IS NOT
      PRICED HERE YET, DELIBERATELY: this spec sets `center_strike` and never
      selects the three legs, so the signal cannot be valid (`is_butterfly`
      is never set; the single-leg `is_valid` arm needs a strike and premium
      it does not have) — the same one-writer-zero-readers defect r97 found
      in the sweep and r146 found in the runaway. Building the legs is a
      spec decision (which wing width, how far from the pin) and is NOT made
      here; until it is, R records n/a and the hurdle is not consulted.
      Parked anyway (ENABLED False), so nothing trades on it.
Apex on the GEX pin, OUT OF THE MONEY. Buy the move to the magnet.

v4.0  2026-08-19  First version. **The wrong trade** - see v4.1.
v4.1  2026-08-20  Rewritten to the operator's actual spec.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

════════════════════════════════════════════════════════════════════════════
⚠️ STILL PARKED. THE INPUT IS NOT REAL YET.
════════════════════════════════════════════════════════════════════════════
`OptionContract.open_interest` was a DECLARED FIELD WITH NO PRODUCER - 0 on
every contract for the life of v3 - so `gex_data` fell through to
`oi_proxy = max(1, int(1000 * gamma))` and multiplied by gamma AGAIN:

        **GEX ~ 100,000 * gamma^2 * spot**

Confirmed on the live SPX box 2026-08-19: 542 of 542 contracts in the day's
final snapshot carried `"oi": 0`, while the log showed `pin = call_wall = $7725`
with **spot sitting on it** - gamma peaks at the money, so a gamma-squared
surface always "pins" wherever price already is - and GEX swung
**12.4M -> 0.1M -> 2.0M in three minutes**, flipping PINNING/NEUTRAL inside 90
seconds. OI.1 wires real open interest into both repos; ~2 weeks of collection
are needed before any threshold here can be validated.

⚠️ **AND THAT ALSO HID A DUPLICATE.** v3's `butterfly_strategy` centres on SPOT;
this centres on the PIN. **While GEX was gamma-squared the pin WAS spot, so the
two computed the same centre through different arithmetic and nobody could have
noticed.** They diverge for the first time when real OI lands. One of them
retires then; keeping both is how a codebase grows a second lineage nobody
remembers choosing.

════════════════════════════════════════════════════════════════════════════
WHAT v4.0 GOT WRONG, AND WHY THE CORRECTION MATTERS
════════════════════════════════════════════════════════════════════════════
v4.0 built an AT-THE-MONEY butterfly requiring price to be NEAR the pin already,
and vetoed high ATR because "a butterfly wants price to sit still". **Both
backwards.**

Operator, 2026-08-20: *"the intention of this trade is to place the apex on the
pin, which should be OUT OF THE MONEY ... and the farther away the better as
long as it's within the expected move. That's where the asymmetrical payoff
comes into play."*

**THE ASYMMETRY IS THE ENTIRE TRADE.** A butterfly's apex payoff is fixed at the
wing width, but **the DEBIT falls sharply as the apex moves OTM.** A pin at 80%
of the expected move costs a fraction of one at 20% and pays the same at the
apex. Same maximum payoff, much smaller stake.

So distance is the EDGE, not the risk, and the gate is a BAND:
  · too NEAR  - expensive, poor ratio, and you are paying for a move that has
                already happened
  · too FAR   - beyond the expected move, the chain says price probably cannot
                get there
  · **prefer the far edge of what is reachable**

⚠️ AND THE PIN-STRENGTH CONDITION BECOMES LOAD-BEARING. At 80% of the expected
move the trade relies on the magnet actually PULLING price, not on drift
happening to arrive. **A weak pin far away is the worst cell in the matrix; a
strong pin far away is the best.** `pin_concentration` is what tells them apart
- a strike holding 40% of gross |GEX| is one dominant magnet, one holding 8% is
gamma smeared with nothing pinned, **and both read "PINNING"** past the 0.15
threshold.

⚠️ THE EXPECTED MOVE COMES FROM THE CHAIN, NOT FROM VIX. v3 computed it as
`underlying * VIX/100 * sqrt(hours/6.5) / sqrt(252)` - **VIX is SPX 30-day
implied vol applied to any symbol on any 0DTE horizon.** The chain carries
per-symbol ATM IV directly and that is the right input; the time-scaling from v3
is kept because it is sound.

⚠️ AND NOTE WHAT IS *NOT* HERE: NO ATR GATE. v4.0 vetoed above 0.08% ATR on
short-vol reasoning. This trade needs price to TRAVEL to the pin and then sit -
closer to the runaway's requirement than to a short-vol one. The expected-move
band already encodes reachability using the chain's own volatility estimate,
which is a better instrument than an ATR proxy for the same question.

════════════════════════════════════════════════════════════════════════════
GATE CATEGORIES — required by WA §36. Only SELECTION is ever relaxed.
════════════════════════════════════════════════════════════════════════════
**FOUNDATIONAL — never relaxed.**
  · `gex_environment == PINNING`. Without a pin there is no magnet and this is
    an arbitrary OTM butterfly.
  · the apex sits ON the pin. Centring anywhere else is a different trade -
    v3's `butterfly_strategy` centres on SPOT, and that is the duplicate this
    file exists to replace.
  · the pin is OTM. An ATM apex is v4.0's mistake: it pays for a move that has
    already happened and discards the asymmetry that justifies the structure.

**SELECTION — relaxed.**
  · pin concentration 0.25 -> 0.15 floor 0.10. ⚠️ RELAXED WITH RELUCTANCE: at
    the far edge of the expected move the trade RELIES on the magnet pulling
    price. **A weak pin far away is the worst cell in the matrix.** It is
    selection rather than foundational only because a weak pin still IS a pin.
  · window 11:00-15:00 -> 09:45-15:30.
  · EM ceiling 1.00 -> 1.30.

**FEASIBILITY — never relaxed.**
  · no ATM IV means **no trade**, not a fallback. The whole distance band is
    expressed in expected moves; guessing one would put the trade's central
    gate on a number nobody measured.
  · the EM floor at 0.30. Nearer than that the debit is expensive and the payoff
    ratio poor - **the asymmetry IS the trade**, and without it there is no
    reason to prefer this structure over anything else.

⚠️ AND THIS STRATEGY IS RARE BY DESIGN, WHICH IS AN OPPORTUNITY-COST QUESTION
RATHER THAN A DEFECT. It needs a strong pin far from spot - most likely near
monthly expiration, when real positioning sits at a strike rather than a single
day's worth. **It costs nothing while it waits**: no position slot, no capital,
no competition with the other setups. The only real cost is maintenance
attention, and a strategy that fires rarely is one whose plumbing is rarely
exercised - which is what the relaxed toggle is for.
⚠️ ITS EVIDENCE WILL BE STRUCTURAL, NOT STATISTICAL. A handful of fills a month
will never accumulate what the sweep spread got from 2,169 events. The test is
**"when it fires, does the payoff justify having kept it?"** - answerable on a
small sample in a way a win rate is not. That is a weaker footing than the sweep
spread has and it should be said before it goes live, not after a small sample
looks encouraging.
"""

import logging
import math
from datetime import datetime
from typing import Optional

import config
from strategy.base_strategy import OptionsSignal as Signal
from strategy.plan import Plan
from strategy.criteria import stop_survivable, R_FLOOR, STOP_VS_SPREAD_MIN
from utils.math_utils import safe_float
# LADR.1 (r185): the r198 ladder reader lives in data/options_chain; the
# private name stays because check_butterfly_wing_grid and every call below use it.
from data.options_chain import chain_increment as _chain_increment

logger = logging.getLogger(__name__)


def _gate(name: str, reason: str) -> None:
    """r73 — report this rung, edge-triggered. NEVER changes the verdict."""
    try:
        from analysis.gate_report import get_gate_reporter
        from config import INSTRUMENT
        r = get_gate_reporter(INSTRUMENT)
        if r is not None:
            r.blocked("GexPinButterfly", name, reason)
    except Exception:                                           # noqa: BLE001
        pass

# ⚠️ EVERY CONSTANT IS A STATED PRIOR AWAITING MEASUREMENT. Nothing here has
# been validated against outcomes, because the data to do it did not exist until
# 2026-08-19. `GEX_PIN_CONCENTRATION = 0.15` in gex_data was tuned against the
# gamma-squared surface and means nothing for real positioning.
ENABLED = getattr(config, "GEX_BUTTERFLY_ENABLED", True)       # v4.3: ON
# 🔴 r208 — `WING_EM_FRAC` IS DELETED. The wing is no longer a fraction of the
# expected move; it is SEARCHED over the chain's listed strikes, bracketed by
# R_FLOOR on the wide side and survivability on the narrow side, narrowest
# qualifying wing wins. Operator, 2026-09-01: "the wings should be a 1-R or
# better (that's the widest allowed) but prefer narrower if available."
# ⚠️ AND IT WAS DECIDING MORE THAN A PAYOFF SHAPE. At 0.25 of the expected move
# it also set whether a survivable fly existed AT ALL, because the two bounds
# together require width >= 64 x leg-spread. Nobody ever fitted it.
# config.GEX_BFLY_WING_EM_FRAC is left in place, unread, so a box carrying the
# old env var starts cleanly rather than failing on an unknown key.
PIN_CONC_MIN = config.GEX_BFLY_PIN_CONC_MIN
# OTV4TEST r25 (BFLY.5, operator's ruling): a pin within ±this x EM of today's VWAP
# meets pin_concentration without the floor. 0.10 above + 0.10 below = 20% of EM.
VWAP_BAND_EM_FRAC = float(getattr(config, "GEX_BFLY_VWAP_BAND_EM_FRAC", 0.10))
EM_MIN_FRAC = config.GEX_BFLY_EM_MIN_FRAC
EM_MAX_FRAC = config.GEX_BFLY_EM_MAX_FRAC
EARLIEST_ET = config.GEX_BFLY_EARLIEST_ET       # r148: no literal fallback
LATEST_ET = config.GEX_BFLY_LATEST_ET           # r148: the name now exists; no literal fallback
# OTV4TEST r6 — persistence with smoothing (operator 2026-09-09). PRIORS,
# recorded on every row; the first real pins say what they should be.
SMOOTH_WINDOW = int(config.GEX_BFLY_SMOOTH_WINDOW)    # ticks (~3 min)
PERSIST_TICKS = int(config.GEX_BFLY_PERSIST_TICKS)     # ticks (~2 min)

# ── GATE CATEGORIES AS DATA (WA §36) ───────────────────────────────────────
GATES = {
    "SMOOTH_WINDOW":  "SELECTION",     # OTV4TEST r6 prior — a dial, gates nothing
    "PERSIST_TICKS":  "FOUNDATIONAL",  # OTV4TEST r6 — the persistence bar
    # 🔴 r196 — FOUNDATIONAL, NOT SELECTION. Operator, 2026-08-31, watching
    # butterflies open at 09:45 on the first live open: "the noon floor is
    # non-negotiable."
    # The 09:45 was not a marginal call and not GEX pinning early — it is
    # `relaxed.window()`'s `relaxed_earliest` default EXACTLY, so the fires
    # were the relaxed floor, not the market.
    # ⚠️ WHY THE CATEGORY WAS WRONG, WHICH IS THE PART WORTH KEEPING:
    # relaxation only informs a gate that is a DIAL ALONG A CONTINUUM. Widen a
    # dial and you collect the near-misses, whose outcomes tell you whether the
    # line sits in the right place. `PIN_CONC_MIN` and `EM_MAX_FRAC` are dials
    # and are relaxed correctly. This is not a dial. The operator's rule is
    # "any sooner than noon to reach a pin is unlikely to hold all the way to
    # the closing bell" — a claim about TIME TO EXPIRY, not about pin quality.
    # A 09:45 butterfly is not a marginally worse butterfly; it is a different
    # trade with six and a half hours of gamma ahead of it instead of four, and
    # its outcome says nothing about whether noon is the right hour.
    # ⚠️ AND THE WIDENING CAME FROM UNRELATED REASONING. `relaxed.window`'s
    # 09:45 floor is documented as avoiding the opening auction's residue — a
    # QUOTE-QUALITY argument. It silently overrode a TIME-TO-PIN argument. Two
    # different concerns sharing one default.
    # ⚠️ AND THE COST IS WORST HERE BECAUSE THE BUTTERFLY IS ONE PER SESSION.
    # Relaxing a dial spends a marginal trade. Relaxing this spent the day's
    # ONLY attempt, three hours before the thesis is valid.
    "EARLIEST_ET":   "FOUNDATIONAL",
    # 🔴 r208 — SELECTION -> FOUNDATIONAL, reversing r196 on this one bound.
    # Operator, 2026-09-01: "the only relaxing I'm ok with is when wing width
    # gets kind of like diminishing returns." r196 kept this relaxable because
    # "a pin that forms at 15:10 is a marginally worse version of the same
    # trade"; under the reachability ruling it is not one, because a fly opened
    # at 15:20 has twenty minutes to the 15:40 flatten to reach the pin AND
    # hold it. Same argument as the noon floor, other end of the day.
    "LATEST_ET":     "FOUNDATIONAL",
    # 🔴 r208 — SELECTION -> FOUNDATIONAL, AND THIS REVERSES r196's OWN
    # SENTENCE THREE LINES BELOW, WHICH IS WHY IT IS SAID OUT LOUD. r196 wrote
    # that "PIN_CONC_MIN and EM_MAX_FRAC are dials and are relaxed correctly."
    # On 2026-09-01 the x1.3 widening admitted pins at 1.5x the expected move
    # and five flies fired on the first tick of the noon window; three were
    # stopped out inside the same minute. Operator: "can the Pin even be
    # reached? ... if any of those are no then I don't even want a relaxed one
    # taking it."
    # ⚠️ WHY IT IS NOT A DIAL, on the test r196 itself supplied: relaxation only
    # informs a gate along a CONTINUUM, where the near-misses tell you whether
    # the line sits right. A pin the tape cannot reach in the time remaining is
    # not a marginally worse pin trade — the magnet never gets to act, so the
    # outcome says nothing about whether the bound is correct. It is the same
    # shape as the noon floor: a claim about REACHABILITY, not about quality.
    # ⚠️ C.31 APPLIES — when evidence kills a justification, replace it rather
    # than leave the constant defended by a claim the record contradicts.
    "EM_MAX_FRAC":   "FOUNDATIONAL",
    # ⚠️ SELECTION WITH RELUCTANCE. At the far edge of the expected move the
    # trade RELIES on the magnet pulling price, so a weak pin far away is the
    # worst cell in the matrix. It is selection only because a weak pin is
    # still a pin.
    # 🔴 r208 — SELECTION -> FOUNDATIONAL. An earlier cut of r208 kept this a
    # dial on the reading that the operator had named three conditions and
    # strength was not one. He corrected it: "reachability and pin strength are
    # synonymous with POSSIBLE. If either is a no it's much less possible."
    # ⚠️ AND r196's OWN ARGUMENT SUPPORTS HIM AGAINST MY VERSION. Relaxation
    # earns its place by collecting near-misses whose outcomes fit the line.
    # THE BUTTERFLY IS ONE PER SESSION (r179), so a relaxed near-miss does not
    # collect a marginal trade — it SPENDS the day's only slot on one, and the
    # good setup that forms at 13:00 finds the shot already taken. r196 made
    # exactly this argument about the noon floor and it applies to every dial
    # on a capped strategy.
    # ⚠️ CONSEQUENCE, STATED: relaxed now moves NOTHING on the butterfly except
    # LATEST_ET. That means PIN_CONC_MIN and EM_MAX_FRAC can no longer be
    # fitted from relaxed OUTCOMES — the plan table still records their values
    # on every DECLINE, but a decline has no P&L. Fitting them needs the reach
    # study (BFLY.8), not a wider gate.
    "PIN_CONC_MIN":  "FOUNDATIONAL",
    # 🔴 r208 — FEASIBILITY, via criteria.stop_survivable(). "Can the floor
    # clear the spread?" A fly's value is `lower + upper - 2*center`, so three
    # legs' quote noise compounds into a number that was itself 17 cents on
    # 2026-09-01 — against a 4.3c floor. Not a bad trade, a broken one (r154).
    # No knob here: it is one comparison of two numbers off the same chain,
    # which is why it needs no constant per symbol and no debit floor beside
    # it. Never mode-dependent.
    "STOP_VS_SPREAD_MIN": "FEASIBILITY",
    # FEASIBILITY - nearer than this the debit is expensive and the payoff ratio
    # poor. **The asymmetry IS the trade**; without it there is no reason to
    # prefer this structure over anything else.
    "EM_MIN_FRAC":   "FEASIBILITY",
    # FOUNDATIONAL: PINNING, the apex ON the pin, and the pin OTM. Tested
    # inline - no knob.
}


def expected_move(underlying: float, atm_iv: float, now=None) -> Optional[float]:
    """1x expected move for the REMAINING session, from the chain's ATM IV.

    r223 (EM.1): the arithmetic lives in analysis.volatility_measures.expected_move_session,
    moved verbatim (hours to 16:00, 15-minute floor, 3.0 h fallback). This wrapper keeps the
    name every caller imports and reads the clock HERE, so a checker that pins this module's
    `datetime` still pins it."""
    if now is None:
        try:
            from utils.time_utils import ET
            now = datetime.now(ET)
        except Exception:                                      # noqa: BLE001
            now = None
    from analysis.volatility_measures import expected_move_session
    return expected_move_session(underlying, atm_iv, now)


def leg_quote_facts(lower, center, upper) -> dict:
    """r225 (FLY.2) — WHAT THE THREE LEGS' QUOTES LOOKED LIKE WHEN THE WINGS WERE PICKED. RECORDED, GATING NOTHING.

    The operator, 2026-10-03: a no-bid contract CAN be bought at the mark ("I'm not saying it
    isn't risky - only that it's possible"). So both readings are recorded, for two weeks, and he
    rules after:
      wings_no_bid          how many of the two BOUGHT wings had no bid (the risk marker)
      strict_would_refuse   1 if a rule 'all three legs have a bid and an ask' would refuse
      role_would_refuse     1 if a rule 'the wings need an ask, the SOLD body needs a bid' would
    """
    def _q(c):
        try:
            return (float(getattr(c, "bid", 0.0) or 0.0), float(getattr(c, "ask", 0.0) or 0.0))
        except (TypeError, ValueError):
            return (0.0, 0.0)
    lb, la = _q(lower)
    cb, ca = _q(center)
    ub, ua = _q(upper)
    strict_ok = min(lb, cb, ub) > 0 and min(la, ca, ua) > 0
    role_ok = la > 0 and ua > 0 and cb > 0
    return {"wings_no_bid": float((lb <= 0) + (ub <= 0)),
            "strict_would_refuse": 0.0 if strict_ok else 1.0,
            "role_would_refuse": 0.0 if role_ok else 1.0}


def _structure_quote(lower, center, upper):
    """(bid, ask) for the FLY ITSELF, built per leg and conservatively.

    🔑 THE FLY'S SPREAD IS NOT ONE LEG'S SPREAD. Buying the structure costs
    `lower.ask + upper.ask - 2*center.bid`; selling it receives
    `lower.bid + upper.bid - 2*center.ask`. Three legs, so three spreads
    compound — which is the whole reason a 17-cent fly cannot hold a 4-cent
    floor. r105 built exactly this shape for the credit vertical and its own
    note applies here: limit_ladder v1.1 dropped its synthetic walk because
    "the shade was guesswork about a spread we cannot see"; now we can see it.

    ⚠️ A LEG WITH NO QUOTE RETURNS (0, 0), which `stop_survivable` reads as
    UNMEASURABLE and REFUSES. Unmeasurable is not passing — that is the failure
    class this repo keeps finding, a gate that silently never applied.
    """
    def _q(c):
        try:
            return (float(getattr(c, "bid", 0.0) or 0.0),
                    float(getattr(c, "ask", 0.0) or 0.0))
        except (TypeError, ValueError):
            return (0.0, 0.0)
    lb, la = _q(lower)
    cb, ca = _q(center)
    ub, ua = _q(upper)
    if min(la, ca, ua) <= 0:
        return 0.0, 0.0
    return (max(0.0, lb + ub - 2.0 * ca), max(0.0, la + ua - 2.0 * cb))


class ButterflyPreparation:
    """What the plan hands the strategy each tick of the slot — never executable."""
    __slots__ = ("tick", "pin", "side", "conc", "em", "frac", "wing",
                 "wing_intended", "grid_inc", "wing_stretch", "lower", "center",
                 "upper", "debit", "width", "r", "r_min", "conditions", "unmet",
                 "structural", "starved", "ready", "vwap_waiver")

    def __init__(self, tick):
        self.tick = tick
        self.pin = self.conc = self.em = self.frac = self.wing = 0.0
        self.wing_intended = self.grid_inc = 0.0
        self.wing_stretch = None
        self.side = ""
        self.lower = self.center = self.upper = None
        self.debit = self.width = self.r = None
        self.r_min = R_FLOOR
        self.conditions, self.unmet, self.structural, self.starved = {}, [], [], []
        self.ready = False
        self.vwap_waiver = ""

    def cond(self, name, current, required, met):
        self.conditions[name] = (current, required, bool(met))
        if not met:
            self.unmet.append(name)
        self.tick.check(name, current if isinstance(current, (int, float)) else None, bool(met))

    def trade_line(self):
        if not self.ready:
            return "no trade prepared"
        return (f"buy {self.lower.strike:g}/{self.center.strike:g}/{self.upper.strike:g} "
                f"{self.side} fly  debit {self.debit:.2f}  width {self.width:.2f}  "
                f"R {self.r:.2f} (min {self.r_min:.2f})")


class GEXPinButterflyStrategy:
    """THE SPEC. Declares its conditions; executes with the plan's legs.

    🔴 EXEMPT FROM THE SINGLE-POSITION RULE. Operator, 2026-08-27: *"I want it
    to be able to fire regardless if any other open trades are found. Reason:
    it has such a high hurdle to clear. GEX pinning, pin reachable, economic
    feasibility. If it can achieve all that, it's earned an entry."* TRADES.md
    §3 said the same from the start: *"no position slot, no capital, no
    competition."* main.py asks it every tick of its slot, position open or
    not, and appends its record rather than replacing.
    """
    name = "GEXPinButterfly"

    CONDITIONS = {
        "enabled":           "GEX_BUTTERFLY_ENABLED is on",
        "pinning":           "GEX environment is PINNING with a pin strike",
        "pin_concentration": (f"pin concentration >= {PIN_CONC_MIN:.2f} (NOT relaxable, r208), "
                              f"or the pin within ±{VWAP_BAND_EM_FRAC:.2f}x EM of today's VWAP (r25)"),
        "entry_window":      f"{EARLIEST_ET}-{LATEST_ET} ET",
        "expected_move":     "an expected move from the chain's ATM IV (no fallback)",
        "pin_em_fraction":   f"pin at {EM_MIN_FRAC:.0%}-{EM_MAX_FRAC:.0%} of the expected move (NOT relaxable, r208)",
        "pin_persistence":   "the smoothed pin has held for PERSIST_TICKS ticks (OTV4TEST r6)",
    }
    STRUCTURAL = ("legs", "debit", "r", "pin_played", "stop_survivable")
    PLAN_CHECKS = tuple(CONDITIONS) + STRUCTURAL + ("gex", "wing_width", "width",
                                                    "debit_pct_width", "stop_vs_spread",
                                                    "r_muted", "pin_dist_pct",
                                                    "pin_strike_raw", "pin_vwap_dist",
                                                    "quote_wings_no_bid", "quote_strict_would_refuse",
                                                    "quote_role_would_refuse")

    def __init__(self):
        self.planner = Plan(self.name, self.PLAN_CHECKS)

    # ══════════════════════════════════════════════════════════════════════
    # THE PLAN — evaluates the declared conditions, SELECTS the three legs.
    # ══════════════════════════════════════════════════════════════════════
    # ── ONE BUTTERFLY PER PIN PER SESSION (r178) ──────────────────────────
    # 2026-08-28 15:00-15:01: r177 unblocked the starved atm_iv, every
    # condition was genuinely true on UNH's pin, and the strategy fired the
    # SAME 397.5 fly five times in ninety seconds — the additive exemption
    # (r161) let it stack ITSELF, and it had no self-lock because it had
    # never once fired to need one. Same failure class as the runaway
    # re-arm; same doctrine as the fix: a fired pin is PLAYED for the
    # session. A NEW pin (GEX migrates the magnet) is a new trade.
    # In-process registry; a restart clears it, recorded as acceptable.
    PLAYED_PINS: set = set()
    _pins: list = []                     # instant pins, last SMOOTH_WINDOW ticks
    _persist: int = 0                    # ticks the smoothed pin has held
    _last_smoothed: float = 0.0

    def _smoothed_pin(self, pin_raw: float) -> float:
        from collections import Counter
        if pin_raw and pin_raw > 0:
            self._pins = (self._pins + [round(pin_raw, 2)])[-SMOOTH_WINDOW:]
        if not self._pins:
            self._persist = 0
            return 0.0
        mode, _n = Counter(self._pins).most_common(1)[0]
        if mode == self._last_smoothed:
            self._persist += 1
        else:
            self._last_smoothed, self._persist = mode, 1
        return float(mode)

    @classmethod
    def mark_pin_played(cls, pin) -> None:
        try:
            cls.PLAYED_PINS.add(round(float(pin), 2))
        except (TypeError, ValueError):
            pass

    def prepare(self, *, gex, price_now, now_et, atm_iv=None, chain=None,
                **_ignored) -> ButterflyPreparation:
        t = self.planner.tick(price_now)
        prep = ButterflyPreparation(t)
        # r196 — the floor is passed as its OWN relaxed value, so
        # `min(earliest, relaxed_earliest)` can only ever return EARLIEST_ET.
        # LATEST_ET stays relaxable: staying LATER is a dial (a pin that forms
        # at 15:10 is a marginally worse version of the same trade), whereas
        # starting EARLIER is a different trade.
        _early, _late = EARLIEST_ET, LATEST_ET
        if now_et and not (_early <= now_et <= _late):
            # ⚠️ TIME-INVARIANT reason (check_plan_signal PS7): the dormant row
            # is edge-triggered on its text; a clock in it defeats the dedupe.
            t.dormant("entry_window", f"outside the butterfly slot {_early}-{_late}")
            return prep
        prep.cond("entry_window", None, self.CONDITIONS["entry_window"], True)
        from strategy import plan_state as _ps                  # r303: LOG is "enabled" too (recorded only)
        _on = bool(ENABLED) or _ps.is_log("GEXPinButterfly")
        prep.cond("enabled", 1.0 if _on else 0.0, self.CONDITIONS["enabled"], _on)
        price_now = safe_float(price_now)
        if not price_now or price_now <= 0:
            prep.starved.append("price_now")
            t.starved("price_now")
            return prep
        if not gex:
            prep.starved.append("gex")
            t.starved("gex")
            return prep
        t.check("gex", 1.0, True)
        # ── OTV4TEST r6: OI IS A STARVED INPUT, NOT A GUESS. Zero OI across
        #    the chain means GEX is gamma-squared, not positioning — the
        #    parked reason, now a state the row says every tick.
        _oi_sum = 0
        try:
            for _c in (list(getattr(chain, "calls", []) or []) + list(getattr(chain, "puts", []) or [])):
                _oi_sum += int(getattr(_c, "open_interest", 0) or 0)
        except Exception:                                      # noqa: BLE001
            _oi_sum = 0
        t.check("open_interest", float(_oi_sum), _oi_sum > 0)
        if chain is not None and _oi_sum <= 0:
            prep.starved.append("open_interest")
            t.starved("open_interest")
            return prep
        env = str(getattr(gex, "gex_environment", "") or "")
        conc = float(getattr(gex, "pin_concentration", 0.0) or 0.0)
        pin_raw = float(getattr(gex, "pin_strike", 0.0) or 0.0)
        # ── OTV4TEST r6: PERSISTENCE, SMOOTHED. The acting pin is the MODE of
        #    the last SMOOTH_WINDOW instant pins (chatter between adjacent
        #    strikes does not move it; a migration does), and it must have
        #    been the mode for PERSIST_TICKS ticks. Both are declared priors.
        pin = self._smoothed_pin(pin_raw)
        t.check("pin_raw", pin_raw or None)
        t.check("pin_persist_ticks", float(self._persist), self._persist >= PERSIST_TICKS)
        try:                                        # r12 — ANCHORS, record only
            from derived import anchors as _A
            _A.stamp(t, gex_at_pin=_A.gex_at(pin or None),
                     vwap_minus_pin=(lambda v: None if (v is None or not pin) else v - pin)(_A.vwap()),
                     oi_at_pin=_A.oi_at(pin or None, chain))
            # r31 (BFLY.7) — THE PINNING REGIME ITSELF, RECORDED AT ZERO WEIGHT.
            # Concentration says WHERE gamma is; this says whether the regime
            # that does the pinning exists. On 2026-09-16 they disagreed for six
            # hours — conc 0.06-0.17 (weak) against chain net gamma +71M..+123M
            # (strongly pinning) — which is why it is a separate axis and not
            # another vote. `gamma_ramp` is the multiplier it WOULD apply;
            # GAMMA_RAMP_WEIGHT is 0.0, so nothing is sized by it yet (§31).
            from derived import gamma_regime as _G
            _A.stamp(t, **_G.read())
        except Exception:                           # noqa: BLE001
            pass
        prep.cond("pin_persistence", float(self._persist),
                  f">= {PERSIST_TICKS} ticks at one strike (smoothed over {SMOOTH_WINDOW})",
                  self._persist >= PERSIST_TICKS)
        prep.pin, prep.conc = pin, conc
        # r178 — a played pin is a structural DECLINE; relaxed does not waive
        # it, and it is checked BEFORE the conditions so the row names it
        # first (a stacked structure corrupts the sample worse than a missed
        # one). The magnet moving to a new strike is a new trade.
        if pin and round(pin, 2) in self.PLAYED_PINS:
            prep.structural.append(("pin_played",
                f"pin {pin:g} already has a butterfly this session — one "
                f"structure per pin; a NEW pin is a new trade"))
            t.check("pin_played", pin, False)
        pinning = env == "PINNING" and pin > 0
        prep.cond("pinning", pin or None, f"PINNING (now {env or 'unknown'})", pinning)
        # ⚠️ r215 — RECORDED, GATES NOTHING. `pin_strike` is now bounded to
        # PIN_MAX_DIST_PCT of spot in compute_gex, because the argmax was
        # unbounded and wandered (GOOGL published 20 distinct pins spanning
        # 245-450 in one session against a ~345 price). That bound is a PRIOR.
        # This writes the RAW argmax's distance to plan_check on every
        # evaluation so the prior can be fitted against outcomes instead of
        # defended — the same discipline r208 applied to EM_MAX_FRAC.
        t.check("pin_dist_pct", getattr(gex, "pin_dist_pct", None))
        t.check("pin_strike_raw", getattr(gex, "pin_strike_raw", None))
        # 🔴 r208 — BOTH BOUNDS ARE FOUNDATIONAL AND BOTH COME FROM ONE PLACE.
        # See relaxed_bounds(): pinned to themselves, so relaxation moves
        # neither, and a checker can execute the same function the strategy
        # calls rather than re-deriving it.
        em = expected_move(price_now, atm_iv)
        _met, _need, prep.vwap_waiver = pin_strength(t, pin, conc, em)
        prep.cond("pin_concentration", conc, _need, _met)
        prep.em = em or 0.0
        prep.cond("expected_move", em or None, self.CONDITIONS["expected_move"], bool(em and em > 0))
        if pin > 0 and em and em > 0:
            dist = abs(pin - price_now)
            frac = dist / em
            prep.frac = frac
            # 🔴 r208 — REACH IS FOUNDATIONAL AND CANNOT BE WIDENED. Operator,
            # 2026-09-01: "is price pinning right now? can the Pin even be
            # reached? Can the floor clear the spread? If any of those are 'no'
            # then I don't even want a relaxed one taking it."
            # `cap=EM_MAX_FRAC` makes `min(value*1.3, value)` return the value
            # for every input, so the bound cannot move. Kept INSIDE the relax
            # API on purpose — r196's lesson: a gate hardened by leaving the
            # API entirely is a gate check_gates stops watching.
            _em_max = EM_MAX_FRAC
            prep.cond("pin_em_fraction", frac, f"{EM_MIN_FRAC:.2f}-{_em_max:.2f}",
                      EM_MIN_FRAC <= frac <= _em_max)
            t.anchor(trigger=pin)
        else:
            prep.cond("pin_em_fraction", None, self.CONDITIONS["pin_em_fraction"], False)

        # ── SELECTION — the three legs, if the conditions hold next tick ────
        if pin > 0 and em and em > 0:
            side = "call" if pin > price_now else "put"
            prep.side = side
            t.direction = side
            if chain is None:
                prep.starved.append("chain")
            else:
                contracts = chain.calls if side == "call" else chain.puts
                # 🔴 r198 — THE GRID COMES FROM THE CHAIN, NOT FROM ONE GLOBAL
                # CONSTANT. See _chain_increment(). ⚠️ NOT `round_to_strike`:
                # it returns an int, so a $2.50 ladder cannot be represented by
                # it at all and reusing it here would silently reintroduce the
                # very bug this fixes for every half-strike symbol.
                inc = _chain_increment(contracts, pin,
                                       float(getattr(config, "STRIKE_INCREMENT", 1) or 1))
                prep.grid_inc = inc

                def _exact(k):
                    for c in contracts or []:
                        try:
                            if abs(float(c.strike) - k) < 1e-9 and float(c.mark or 0) > 0:
                                return c
                        except (TypeError, ValueError, AttributeError):
                            continue
                    return None

                center = _exact(pin)
                if center is None:
                    t.check("legs", 0, False)
                    prep.structural.append(("legs",
                        f"no priced {side} contract at the pin {pin:g} — the apex "
                        f"IS the trade; a nearest-strike substitute is a "
                        f"different one"))
                else:
                    # ── 🔴 r208 — THE WING IS SEARCHED, NOT COMPUTED ────────
                    # Operator, 2026-09-01: "construct a narrow OTM debit fly
                    # with the pin at the apex. The wings should be a 1-R or
                    # better (that's the widest allowed) but prefer narrower if
                    # available."
                    # WHAT THIS REPLACES: a single wing at WING_EM_FRAC (0.25)
                    # x the expected move, snapped to the grid, with R checked
                    # AFTER the fact. That constant is DELETED. It was a prior
                    # nobody fitted, and it was deciding something bigger than
                    # a payoff shape — see the bracket below.
                    # 🔑 THE TWO BOUNDS PULL OPPOSITE WAYS, AND ONLY ONE WAS
                    # EVER WIRED. R = (width-debit)/debit RISES as the wing
                    # NARROWS; survivability FALLS, because a fly's quote is
                    # FOUR leg-spreads wide - (la-lb) + (ua-ub) + 2*(ca-cb) -
                    # while its debit shrinks. With only R in the code the
                    # selector steered to the least survivable structure
                    # available and called it the best one: on 2026-09-01 five
                    # flies fired at 12:00:00 with R 8.5 to 16.9 and three were
                    # stopped out inside the same minute, on floors of 4.3c,
                    # 5.3c and 7.0c. META at R 10.8 was not a fly that happened
                    # to be fragile; it was the MOST fragile constructible fly,
                    # chosen because it was.
                    # ⚠️ SO THE SEARCH IS BRACKETED FROM BOTH ENDS: R_FLOOR
                    # caps the WIDE side, survivability floors the NARROW side,
                    # and among what is left we take the NARROWEST per the
                    # ruling. Both bounds together require
                    # width >= 64 x leg-spread, so on a wide-spread symbol NO
                    # wing qualifies — which is a definite answer and is
                    # reported as one, not a fallback to something worse.
                    # ⚠️ SYMMETRIC AND EXACT. Both wings must be LISTED and
                    # priced; the apex is never rounded (r198's W3).
                    _cap_dist = abs(pin - price_now)          # never cross spot
                    # 🔑 CANDIDATES COME FROM THE LISTED STRIKES, NOT FROM AN
                    # INCREMENT. A first cut of r208 stepped the search by
                    # `_chain_increment`'s median gap, which is r198's C.29 in a
                    # new costume: an ESTIMATE of the ladder standing in for the
                    # ladder. It cannot demand an unlisted strike the way r198's
                    # snap-and-demand did — every candidate here is only a
                    # candidate because BOTH legs came back priced — but a
                    # mixed ladder (2.50 near the money, 1.00 in the tails, or
                    # half-strikes at ATM) would let the stride step PAST real
                    # wings and silently narrow the search.
                    # Enumerating the chain's own strikes removes the estimate
                    # from the decision path entirely. `inc` survives for
                    # REPORTING only (r198's grid telemetry on the record).
                    _wings = sorted({round(float(c.strike) - pin, 4)
                                     for c in (contracts or [])
                                     if float(getattr(c, "strike", 0) or 0) > pin})
                    _cands, _rej_r, _rej_surv, _best_r, _best_ratio = [], 0, 0, None, None
                    for _w in _wings:
                        if _w <= 0 or _w > _cap_dist + 1e-9:
                            continue
                        _lo, _up = _exact(pin - _w), _exact(pin + _w)
                        if _lo is None or _up is None:
                            continue        # asymmetric ladder — not a fly
                        _d = float(_lo.mark) - 2.0 * float(center.mark) + float(_up.mark)
                        if _d <= 0 or _w <= _d:
                            continue
                        _r = (_w - _d) / _d
                        _best_r = _r if _best_r is None else max(_best_r, _r)
                        if _r < R_FLOOR:
                            _rej_r += 1
                            continue
                        _b, _a = _structure_quote(_lo, center, _up)
                        _sd = _d * float(getattr(config, "BUTTERFLY_STOP_LOSS_PCT", 0.40))
                        _ok, _why = stop_survivable(_sd, _b, _a)
                        if (_a - _b) > 0:
                            _ratio = _sd / (_a - _b)
                            _best_ratio = _ratio if _best_ratio is None else max(_best_ratio, _ratio)
                        if not _ok:
                            _rej_surv += 1
                            continue
                        _cands.append((_w, _lo, _up, _d, _r, _sd / (_a - _b) if (_a - _b) > 0 else None))

                    t.check("wing_candidates", float(len(_cands)))
                    t.check("r", _best_r)
                    t.check("stop_vs_spread", _best_ratio)
                    if not _cands:
                        # NAME WHICH BOUND REFUSED. "No fly" and "no fly that
                        # can hold its stop" are different facts, and the fit
                        # needs to tell them apart.
                        t.check("legs", 0, False)
                        prep.structural.append(("wing_search",
                            f"no wing qualifies at pin {pin:g} on the {inc:g} grid "
                            f"(within {_cap_dist:.2f} of spot): {_rej_r} too wide "
                            f"for R>={R_FLOOR:.2f} (best R {_nr(_best_r)}), "
                            f"{_rej_surv} too narrow to clear their own spread "
                            f"(best {_nr(_best_ratio)}x of {STOP_VS_SPREAD_MIN:.1f}x)"))
                    else:
                        # OTV4TEST r6 — BEST PAYOFF ASYMMETRY, per the operator
                        # (2026-09-09): every listed width is priced and the pick
                        # is the MAX R among those that cleared both bounds.
                        # "Narrowest first" is superseded here.
                        wing, lower, upper, debit, r, _ratio = max(_cands, key=lambda c: c[4])
                        width = wing
                        prep.wing = wing
                        prep.wing_intended = wing        # searched, not intended
                        prep.wing_stretch = None
                        t.check("wing_width", wing, True)
                        t.check("legs", 3, True)
                        for _qk, _qv in leg_quote_facts(lower, center, upper).items():
                            t.check(f"quote_{_qk}", _qv, None)          # r225: recorded, never gating
                        t.butterfly(debit, width, trigger=pin)
                        _pct = debit / width if width else None
                        _dcap = float(getattr(config, "BUTTERFLY_MAX_DEBIT_PCT_WIDTH", 0.33))
                        t.check("debit_pct_width", _pct, None if _pct is None else _pct <= _dcap)
                        t.check("r", r, True)
                        t.check("stop_vs_spread", _ratio)
                        t.check("stop_survivable", None, True)
                        if len(_cands) > 1:
                            logger.info("[gex_bfly] wing search: %d qualified, "
                                        "taking the BEST-R wing %.2f (R %.2f, stop "
                                        "%.2fx its spread); widest was %.2f",
                                        len(_cands), wing, r, _ratio or 0.0,
                                        _cands[-1][0])
                        prep.lower, prep.center, prep.upper = lower, center, upper
                        prep.debit, prep.width, prep.r = debit, width, r
                        prep.ready = True

        head = f"pin {pin:g} ({env or 'no env'}, conc {conc:.2f}, {prep.frac:.0%} of EM {prep.em:.2f})"
        if prep.starved:
            t.starved(*prep.starved)
            return prep
        if prep.structural:
            gate, why = prep.structural[0]
            t.refuse(gate, f"{head}: {why}")
            return prep
        if prep.unmet:
            cur = "; ".join(f"{n}={_nr(prep.conditions[n][0]) if isinstance(prep.conditions[n][0], (int, float)) else 'no'}"
                            f" (need {prep.conditions[n][1]})" for n in prep.unmet)
            t.hold(f"{head}: PREPARED — {prep.trade_line()}. Waiting on: {cur}")
            return prep
        t.note(f"{head}: all {len(self.CONDITIONS)} conditions true — {prep.trade_line()}")
        return prep

    # ══════════════════════════════════════════════════════════════════════
    # THE STRATEGY — conditions true -> execute the plan's legs.
    # ══════════════════════════════════════════════════════════════════════
    def generate_signal(self, *, gex, price_now: float, now_et: str,
                        atm_iv: float = None, chain=None,
                        **_ignored) -> Optional[Signal]:
        prep = self.prepare(gex=gex, price_now=price_now, now_et=now_et,
                            atm_iv=atm_iv, chain=chain)
        if not prep.ready or prep.unmet or prep.structural or prep.starved:
            return prep.tick.already()
        sig = Signal(
            strategy_name=self.name,
            setup_type="gex_pin_butterfly",
            direction="neutral",
            option_side=prep.side,
            underlying_entry=float(price_now),
            underlying_target=prep.pin,
            is_butterfly=True,
            lower_contract=prep.lower,
            center_contract=prep.center,
            upper_contract=prep.upper,
            butterfly_direction=prep.side,
            net_debit=round(prep.debit, 4),
            max_profit=round(prep.width - prep.debit, 4),
            strike=float(prep.center.strike),
            # r178: the pin rides the signal so the fire can mark it PLAYED
            # by the same key prepare() checks

            expiry=getattr(prep.center, "expiry", ""),
            entry_premium=round(prep.debit, 4),
            contract=prep.center,
            stop_loss_pct=float(getattr(config, "BUTTERFLY_STOP_LOSS_PCT", 0.40)),
        )
        sig.center_strike = prep.pin
        sig.pin_concentration = prep.conc
        sig.expected_move = round(prep.em, 4)
        sig.pin_em_fraction = round(prep.frac, 4)
        sig.pin_distance = round(abs(prep.pin - float(price_now)), 4)
        sig.pin_strike = prep.pin          # r178: the mark's key == the plan's key
        # r198 — the metrics need the counterfactual, not just the outcome.
        sig.wing_intended = round(prep.wing_intended, 4)
        sig.wing_actual   = prep.wing
        sig.grid_increment = prep.grid_inc
        sig.wing_stretch  = (round(prep.wing_stretch, 3)
                             if prep.wing_stretch else 1.0)
        logger.info("[gex_bfly] FIRE  %s  pin conc %.2f  spot %.2f",
                    prep.trade_line(), prep.conc, float(price_now))
        return prep.tick.take(sig)


def pin_strength(t, pin: float, conc: float, em) -> tuple:
    """(met, need_text, waiver_text) — IS THIS PIN STRONG? One definition, both butterflies.

    r208: concentration >= PIN_CONC_MIN, FOUNDATIONAL. OTV4TEST r25 (BFLY.5, the
    operator's ruling): OR the pin within ±VWAP_BAND_EM_FRAC x EM of TODAY's VWAP.
    The VWAP is read through `anchors.vwap_now()`, which fails closed on a prior
    session's anchor or a stale bar. Records `pin_vwap_dist` on the tick and, when
    the floor is waived, a note naming by how much. `waiver_text` is "" otherwise.
    """
    _conc_min = PIN_CONC_MIN
    _vw, _vw_why = None, "not read"
    try:
        from derived import anchors as _A
        _vw, _vw_why = _A.vwap_now()
    except Exception as _e:                         # noqa: BLE001
        _vw, _vw_why = None, f"VWAP read failed: {_e}"
    _band = VWAP_BAND_EM_FRAC * em if (em and em > 0) else None
    _vdist = abs(pin - _vw) if (_vw is not None and pin and pin > 0) else None
    _in_band = _vdist is not None and _band is not None and _vdist <= _band
    t.check("pin_vwap_dist", _vdist, None if _vdist is None or _band is None else _in_band)
    waiver = ""
    if conc < _conc_min and _in_band:
        waiver = (f"concentration {conc:.2f} < {_conc_min:.2f} WAIVED — pin {pin:g} is "
                  f"{_vdist:.2f} from today's VWAP {_vw:.2f} (band ±{_band:.2f} = "
                  f"{VWAP_BAND_EM_FRAC:.2f}x EM {em:.2f})")
        t.note(waiver)
    need = f">= {_conc_min:.2f}" + (
        f", or pin within ±{_band:.2f} of VWAP (now {_vdist:.2f} off)" if _vdist is not None and _band
        else f", or pin within {VWAP_BAND_EM_FRAC:.2f}x EM of VWAP (no VWAP: {_vw_why})")
    return (conc >= _conc_min or bool(waiver)), need, waiver


def _nr(v):
    return "n/a" if v is None else f"{v:.2f}"
