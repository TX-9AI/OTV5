"""
strategy/criteria.py  v1.6
v1.6  2026-09-26  OTV4TEST r149 (EOD.1) — runaway_cutoff_et marked SUPERSEDED: the operator ruled directional debits run all day to 15:40 ("A"). The pair is unread by any code; config.ENTRY_WINDOWS governs.
v1.5  2026-09-08  r321 — `sweep_max_age_bars` REMOVED, the residue r241 meant
      to take. r241 deleted the age gate from the strategy and shipped a
      checker for it, but that checker reads ONE module and this file was never
      in its scope — so the pair sat here claiming a strict/relaxed split for a
      gate that no longer exists, in the one file whose job is to answer "what
      does relaxed change?" on one screen.
      ⚠️ IT NEVER AFFECTED A TRADE, AND THAT IS LUCK RATHER THAN DESIGN:
      `criteria.get()` has NO production callers at all. The two remaining
      entries are read by nobody either — the sweep's live pierce-ceiling
      relaxation reaches the code through `relaxed.widen(..., name=...)`
      directly, not through this table. Recorded as DOC.22 rather than
      quietly tidied.
v1.4  2026-09-03  r234 — THE STOP BASIS. `R_FLOOR_STOP`, plus
      `stop_distance()` and `r_on_stop()` — ONE definition of the stop, read
      from the engine's own `LONE_STOP_PCT_OF_RISK`. R was judged against max
      loss at EXPIRY while the stop takes 15% of it, so the gate read 6.67x
      worse than the risk actually taken. Threshold: credit/width >= 13.04%.
      `R_FLOOR` is untouched and keeps the expiry basis for the debit fly.
v1.3  2026-09-01  r208 — `butterfly_reach_max` REMOVED. The butterfly relaxes
      nothing now: reach, strength and both window bounds are strict, and its
      wing is SEARCHED over listed strikes rather than widened. Operator,
      2026-09-01: "reachability and pin strength are synonymous with
      'possible'. If either is a 'no' it's much less possible."
      ⚠️ THE SWEEP'S THREE DIALS ARE UNTOUCHED AND DELIBERATELY STILL LOOSE —
      operator, same day: "the sweep is going to get tightened later. Right
      now we're getting bad TRADES and that's to collect some parameters."
      So this is a butterfly-scoped removal, not the start of a sweep-wide
      one, and the difference is recorded so a later reader does not tidy
      the remaining entries away as leftovers.
v1.2  2026-08-29  r176: runaway_cutoff_et relaxed value = strict 11:30 — the
      debit cutoff does not extend under relaxed (operator ruling).
v1.1  2026-08-27  r154 (RECORDED RETROACTIVELY in r159 — r154 added
      `stop_survivable()` here with no title bump and no entry): a structure
      whose stop distance is inside its own bid-ask spread is BROKEN, not bad,
      and is refused before entry. Structural — never muted by relaxed.
v1.0  2026-08-25

EVERY STRICT AND RELAXED CRITERION, IN ONE FILE.

🔴 OPERATOR, 2026-08-25: *"All of our relaxed & strict criteria could live in 1
file. Not in the strategy, not in the plan. But a separate file that toggles
with the relaxed entry flag & unless already specified, it 'mutes' the r-value
rejection but everything else stays the same. On 'strict' the r-value must
clear the hurdle. Remove the relaxed reference out of the strategies and
plans."*

WHY THIS IS THE RIGHT SHAPE: before this file, answering "what does relaxed
actually change?" meant reading `relaxed.widen()` call sites scattered across
five strategy files. The answer to that question is now one screen.

════════════════════════════════════════════════════════════════════════════
WHAT RELAXED IS FOR — and it is NOT loose entries
════════════════════════════════════════════════════════════════════════════
🔴 OPERATOR, 2026-08-25, and this is the governing statement:
*"The relaxed sample will exercise our stops. Which in my opinion are more
important at this phase than entry price & timing. A good stop placement is
the difference between a modest loss & a catastrophic one."*

So relaxed exists to GENERATE TRADES FOR THE EXITS TO WORK ON. The entries are
knowingly mediocre; that is the point, not a side effect. Measured on
2026-08-25, the exits are earning it: `orb_structure_stop` capped five TSLA
losses between -7.3% and -18.4% of premium, against the OLD engine's
`hard_stop_41%` at -40.6% / -$645 on the same box. Roughly half the damage.
⚠️ NOT YET ESTABLISHED: that the stop CAUSED the tight band. That needs the
premium path from `quote_series` replayed through `exit_replay`; a trade that
stops at -17% might have recovered. Tight is not the same as proven.

════════════════════════════════════════════════════════════════════════════
THE ONE THING RELAXED CHANGES BY DEFAULT
════════════════════════════════════════════════════════════════════════════
**IT MUTES THE R-VALUE REJECTION. NOTHING ELSE, UNLESS NAMED BELOW.**

⚠️ BE CLEAR ABOUT WHAT THAT ADMITS. Muting R lets through trades that are
KNOWN UNPROFITABLE BY THEIR OWN ARITHMETIC. Today's CVX loop is exactly that
population: twelve put spreads at R 0.19, needing an 84% win rate to break
even, every one stopped out for about -$400. Under strict, the R gate refuses
all of them before any other machinery matters. Under relaxed they fire, ON
PURPOSE, so the stops get exercised.

⚠️ CONSEQUENCE THAT MUST NOT BE FORGOTTEN AT FIT TIME: a relaxed session
carries NO R EVIDENCE, because R was not allowed to decide anything. **The R
floor can therefore only ever be fitted from STRICT sessions.** Pooling the two
would fit a threshold on data where the threshold was disabled — the same
class of error as validating a tight threshold on a relaxed sample, which
`relaxed.py` already forbids.

════════════════════════════════════════════════════════════════════════════
WHAT RELAXED MAY NEVER TOUCH
════════════════════════════════════════════════════════════════════════════
🔴 **A TRIGGER OR AN INVALIDATION IS A STRUCTURAL PRICE AND IS NEVER WIDENED.**
Loosening evidence produces MORE PLANS of the same trade. Loosening a trigger
produces A DIFFERENT TRADE WEARING THE SAME NAME, and the two populations stop
being comparable — which destroys the only thing the relaxed/strict split is
for. `assert_not_structural()` below enforces it and `check_criteria.py` fails
the build if any structural constant is routed through this file.

⚠️ AND THE TAGGING STAYS WHERE IT IS. `relaxed.tag(sig)` stamps
`relaxed_entry=1` on the trade record, and `entry_engine` / `trade_logger`
read it. That is the POPULATION LABEL, not a criterion — purging it alongside
the thresholds would make relaxed and strict trades indistinguishable forever,
which is the one property this whole design depends on. Thresholds moved here;
tagging did not move.
"""
from __future__ import annotations

import logging
import os

# ⚠️ r234 — THE ENGINE'S OWN CONSTANT, IMPORTED. `exit_engine` fires the lone
# stop at `risk * LONE_STOP_PCT_OF_RISK`; declaring a second 0.15 here is how
# two spellings of one number drift (r211).
from config import LONE_STOP_PCT_OF_RISK
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ── the switch ──────────────────────────────────────────────────────────
# 🔴 THIS FILE OWNS NO FLAG. It ROUTES through `relaxed.is_allowed()`, which
# already exists and already carries the guard that matters:
#
#     RELAXED IS REFUSED ON A LIVE BOX, whatever the env var says, and
#     `is_live()` FAILS CLOSED — an unreadable flag reads as LIVE.
#
# A first draft of this file read its own `OT_RELAXED_ENTRIES`. That would have
# been a SECOND SOURCE OF TRUTH for the mode, silently bypassing the live
# guard — the exact failure `relaxed.is_live()` documents, where a first draft
# satisfied a guard from a repo default nobody asserted. Operator, 2026-08-25:
# *"Let the flag get set by the new process. Just re-route it."*
#
# ⚠️ READ PER CALL, NOT CACHED AT IMPORT. `configure.sh` may set the flag after
# this module is first imported, and a module-level constant would freeze the
# mode at whatever it was when the first import happened.
def relaxed_active() -> bool:
    """True when relaxed criteria apply. Delegates — never re-decides."""
    try:
        from strategy import relaxed
        return bool(relaxed.is_allowed())
    except Exception:                                          # noqa: BLE001
        # ⚠️ FAIL CLOSED. If the mode cannot be established, STRICT applies —
        # the R hurdle stays up. An unreadable flag must never mute a gate.
        return False


def mode() -> str:
    return "RELAXED" if relaxed_active() else "STRICT"


# ── the R hurdle: the ONLY thing relaxed changes by default ─────────────
R_FLOOR = float(os.environ.get("OT_PLAN_R_FLOOR", "1.00"))

# ── r234 — THE STOP BASIS, FOR STRUCTURES WHOSE STOP IS THE PLANNED EXIT ────
# 🔴 R WAS JUDGED AGAINST A LOSS THE STOP EXISTS TO PREVENT. `search_wing`
# computes `credit / (width - credit)` — MAX LOSS AT EXPIRY — while
# `exit_engine:1818` fires at `entry + (width - entry) * LONE_STOP_PCT_OF_RISK`.
# Same denominator, and the stop takes 15% of it, so the gate read 6.67x worse
# than the risk actually taken. On the fleet's own measured median (credit
# $0.97 on $5.00 of width, 2026-08-25..09-03) that is R 0.241 against R 1.605.
#
# 🔑 THE THRESHOLD, EXACTLY: R_stop >= 1 <=> credit/width >= 13.04%. Panel 6
# measured richness at a 19.4% median (10.8% min, 24.2% max), so most of the
# book already cleared 1:1 on the risk it was actually taking.
#
# ⚠️ IT DOES NOT APPLY TO EVERY STRUCTURE, and the operator's own exit rulings
# draw the line. A CREDIT VERTICAL's stop IS the designed exit — *"the only 2
# ways I want out of this trade is a 15% loss (thesis invalidated) or a session
# hard close"* — so the risk accepted is the stop distance. The GEX PIN
# BUTTERFLY is a debit paid up front and HELD TO THE CLOSE for the pin; its 25%
# floor is a disaster backstop, not the plan, so `R = (width-debit)/debit`
# already has the right denominator and keeps `R_FLOOR` untouched. The MANAGED
# ROLL never opted in at all — `condor_roll` judges on
# `banked_credit + roll_credit - close_cost`, a risk-free-roll test, which is
# the right question for a position you are already in.
#
# ⚠️ BOTH CONSTANTS CARRY THEIR BASIS IN THE NAME so a later reader cannot
# collapse them back into one number with two meanings (§35).
R_FLOOR_STOP = float(os.environ.get("OT_PLAN_R_FLOOR_STOP", "1.00"))


def stop_distance(width, credit) -> Optional[float]:
    """The stop distance a credit vertical ACTUALLY carries, in premium.

    🔴 r234 — ONE DEFINITION, BECAUSE THERE WERE TWO AND THEY DISAGREED 4.15x.
    `sweep_credit_spread` computed `credit * MAX_LOSS_PCT` — 15% OF CREDIT —
    and fed that to `stop_survivable`, while `exit_engine` fires at
    `risk * LONE_STOP_PCT_OF_RISK` — 15% OF RISK. On the measured median that
    is 0.1455 against 0.6045, and the forensics' own "risk-anchored room:
    median $0.605" matches the ENGINE. So survivability was judged against a
    stop 4x tighter than the one that exists, refusing structures that were
    survivable.
    ⚠️ AND THE CREDIT-ANCHORED FORM IS THE RULE r155 DELETED. exit_engine's own
    fallback warning names it: *"15% OF CREDIT, which is the inverted rule r155
    replaced. The trade will stop on noise."* The strategy was still computing
    it.
    ⚠️ IT READS THE ENGINE'S OWN CONSTANT rather than declaring a second 0.15.
    Two spellings of one number is how the first rots unnoticed (r211).
    """
    try:
        w = float(width or 0.0)
        c = float(credit or 0.0)
    except (TypeError, ValueError):
        return None
    risk = w - c
    if w <= 0 or c <= 0 or risk <= 0:
        return None                      # unmeasurable, never a permissive 0.0
    return risk * LONE_STOP_PCT_OF_RISK


def r_on_stop(width, credit) -> Optional[float]:
    """credit / stop_distance — reward against the risk ACTUALLY taken.

    None when the structure is unpriceable, never 0.0: a missing quote is not
    a bad ratio, and scoring it as one would refuse on absent data (r205).
    """
    sd = stop_distance(width, credit)
    if sd is None or sd <= 0:
        return None
    return float(credit) / sd


def r_hurdle() -> Optional[float]:
    """The R a plan must clear, or None when the hurdle is MUTED.

    ⚠️ None MEANS MUTED, NOT ZERO. A floor of 0.0 would still reject a
    negative-R plan and would look like a decision nobody made; None says
    plainly that R did not participate. Same discipline second_order.py uses
    for an unmeasurable greek, and for the same reason: the fit must be able
    to tell "did not gate" from "gated at zero".
    """
    return None if relaxed_active() else R_FLOOR


def r_verdict(r: Optional[float]) -> Tuple[str, str]:
    """(verdict, reason) for a plan's R. The single decision point."""
    h = r_hurdle()
    if h is None:
        # 🔴 MUTED-WITH-A-NUMBER AND MUTED-WITH-NOTHING ARE DIFFERENT ROWS.
        # Operator, 2026-08-25. Under relaxed the hurdle does not gate, but the
        # R VALUE is still recorded — so a relaxed session DOES carry R
        # evidence and the floor can be fitted from it by asking what each
        # threshold would have refused.
        # ⚠️ EXCEPT WHEN R IS UNMEASURABLE. Strict mode FAILS on r=None ("a
        # missing input is not a safe trade"); relaxed takes the trade anyway,
        # and a bare NULL in `plan_check` is then indistinguishable from a
        # column that was never written. Those rows are INVISIBLE to a
        # threshold fit rather than merely uncounted, which silently biases the
        # subset. Say so in the verdict instead.
        if r is None:
            return "MUTED_NO_R", ("R hurdle MUTED (relaxed) AND R is NOT "
                                  "MEASURABLE — this row carries no R evidence "
                                  "at all and must be EXCLUDED from any R fit, "
                                  "not counted as a low-R trade")
        return "MUTED", ("R hurdle MUTED (relaxed) — the trade is taken to "
                         "exercise the exits, not because it pays")
    if r is None:
        return "FAIL", "R not measurable — a missing input is not a safe trade"
    if r < h:
        return "FAIL", f"R {r:.2f} below {h:.2f}"
    return "PASS", f"R {r:.2f} clears {h:.2f}"


# ── WA §36 GATE CATEGORIES ──────────────────────────────────────────────
# ⚠️ REQUIRED, AND `tests/check_gates.py` ENFORCES IT. This file lives in
# strategy/ and mediates relaxable constants, so it owes the same declaration
# every strategy owes: name each gate and say what KIND it is.
#
#   SELECTION     — a measured preference. Loosening gives a WORSE EXAMPLE OF
#                   THE SAME TRADE, which is exactly what a debug session
#                   wants. These are the only things relaxed may touch.
#   FOUNDATIONAL  — relax one and it stops being the trade at all.
#   FEASIBILITY   — physical possibility. Loosening buys nothing because the
#                   trade cannot be executed anyway.
#
# 🔴 `R_FLOOR` IS FOUNDATIONAL, AND IT IS THE INTERESTING CASE. A trade that
# cannot clear 1:1 is not a worse example of the same trade — by its own
# arithmetic it is a losing trade. Muting it is therefore NOT a normal
# relaxation, and this file says so rather than filing it as SELECTION to make
# the categories tidy. It is muted DELIBERATELY and ONLY to generate positions
# for the exits to work on (see the header). Filing it as SELECTION would have
# been the lie that let a future reader loosen it for the ordinary reason.
GATES = {
    "R_FLOOR":                "FOUNDATIONAL",
    "sweep_pierce_ceiling":   "SELECTION",
    "runaway_cutoff_et":      "SELECTION",
    "butterfly_reach_max":    "SELECTION",
    "level_hold_min":         "SELECTION",
}


# ── everything else, named explicitly ───────────────────────────────────
# ⚠️ A CRITERION THAT DIFFERS BETWEEN MODES MUST APPEAR HERE, WITH BOTH
# VALUES SIDE BY SIDE. That is the whole point of the file: "what does relaxed
# change?" is answerable by reading one screen instead of five strategies.
# Anything absent from this table is IDENTICAL in both modes.
#
#   name                       STRICT          RELAXED
CRITERIA = {
    # 🔴 r321 — `sweep_max_age_bars` REMOVED. r241 deleted the age gate from
    # `sweep_credit_spread` — operator, 2026-09-04: *"I do not give a rats ass
    # how old the level is, its still a level"* — and never touched THIS file,
    # so a strict/relaxed pair went on advertising a split for a gate that does
    # not exist. Liveness (`invalidated`) is the test; the clock is not.
    "sweep_pierce_ceiling":   (0.25,           0.75),    # SELECTION
    # r176 — operator 2026-08-29: "Debit entries are finished at 1130,
    # period. Do not extend it for relaxed. We are burning theta."
    # 🔴 r149 — SUPERSEDED 2026-09-26: the operator ruled directional debits run ALL
    # DAY to 15:40 ("A"). This pair is read by no code; config.ENTRY_WINDOWS governs.
    "runaway_cutoff_et":      ("15:40",        "15:40"), # SELECTION — does not relax
    # 🔴 r208 — REMOVED. The butterfly relaxes nothing now: reach, strength and
    # both window bounds are strict, and the wing is SEARCHED rather than
    # widened. Operator, 2026-09-01: "reachability and pin strength are
    # synonymous with possible. If either is a no it's much less possible."
    "level_hold_min":         (0.75,           0.50),    # SELECTION
}

# ⚠️ STRUCTURAL PRICES. Never widened, never routed through here, in EITHER
# mode. Named so the checker can assert their absence from CRITERIA.
STRUCTURAL = (
    "trigger_price", "invalidation", "orb_high", "orb_low",
    "pool_price", "sweep_price", "gex_pin", "short_strike",
)


def get(name: str, default=None):
    """The value of `name` for the CURRENT mode."""
    if name in STRUCTURAL:
        raise ValueError(
            f"'{name}' is a STRUCTURAL price and must never be mode-dependent. "
            "Loosening evidence produces more plans of the same trade; "
            "loosening a trigger produces a different trade wearing the same "
            "name, and the two populations stop being comparable.")
    pair = CRITERIA.get(name)
    if pair is None:
        return default
    return pair[1] if relaxed_active() else pair[0]


# ═══ STRUCTURAL VIABILITY — CAN THIS TRADE PHYSICALLY SURVIVE? ════════════
# 🔴 OPERATOR, 2026-08-27, after CVX re-entered the same 198/192 spread SEVEN
# times in seven minutes, each stopped within a minute, for about -$170:
# *"It's allowed to enter bad trades, but if structurally it can't even survive
# for a minute we need to address the structure."*
#
# ⚠️ THIS IS NOT THE R HURDLE AND IS NOT MUTED BY RELAXED. R asks whether a
# trade PAYS ENOUGH — an economics question, and relaxed exists to collect the
# population R would have refused. THIS asks whether the trade can EXIST: it is
# construction, like a wing that must be present before undefined risk is sold.
# A structure whose stop sits inside its own bid-ask is not a bad trade being
# collected; it is a trade that was closed before it opened, and it teaches the
# sample nothing except how fast the loop can spin.
#
# 🔴 THE MEASUREMENT THAT NAMES IT, from the CVX alerts themselves:
#   credit $0.58 · stop $0.67 (15%) -> THE STOP IS NINE CENTS AWAY.
# On a contract quoted in nickels, one quote update moves the mark further than
# the entire stop distance. The trade was not stopped out by PRICE; it was
# stopped out by its own SPREAD. That is why every attempt died inside a minute
# and why the R value alone would not have explained it.
#
# ⚠️ UNIVERSAL BY CONSTRUCTION — no per-symbol constant. The test compares two
# numbers that both come from the same option chain, so a $9 stock and a $7,000
# index are judged on the same footing. This is deliberate: `WING_WIDTH = 5.0`
# is a FIXED DOLLAR amount, which is one strike increment on SPX and SIX on
# CVX, and that asymmetry is what made a 6-wide spread collecting $0.58 look
# normal to the code.
STOP_VS_SPREAD_MIN = float(os.environ.get("OT_STOP_VS_SPREAD_MIN", "2.0"))


def stop_survivable(stop_distance, bid, ask) -> Tuple[bool, str]:
    """(ok, why) — is the stop further from entry than the quote's own noise?

    ⚠️ ⟨PRIOR⟩ 2.0x. The stop must clear TWICE the bid-ask spread. One times is
    the boundary where a single quote update reaches it; two gives a tick of
    room. Stated, not fitted — the plan table records the ratio on every
    structure so it can be argued with from data rather than from this comment.

    ⚠️ UNMEASURABLE IS NOT PASSING. A missing quote returns False and says so:
    the whole failure class this week has been a gate that silently never
    applied, and a viability check that cannot see the spread is exactly that.
    """
    try:
        sd = float(stop_distance or 0.0)
        b = float(bid or 0.0)
        a = float(ask or 0.0)
    except (TypeError, ValueError):
        return False, "stop or quote unreadable — not a survivable structure"
    if sd <= 0:
        return False, "stop distance is zero or negative — no room to survive"
    if a <= 0 or b < 0 or a < b:
        return False, (f"no usable quote (bid {b:.2f} / ask {a:.2f}) — "
                       f"survivability cannot be measured, so it is not assumed")
    spread = a - b
    if spread <= 0:
        # A locked market: nothing to clear, so the stop is survivable on this
        # test. Say so rather than passing silently.
        return True, f"stop ${sd:.2f} vs a locked quote (no spread)"
    ratio = sd / spread
    if ratio < STOP_VS_SPREAD_MIN:
        return False, (f"stop is ${sd:.2f} but the bid-ask is ${spread:.2f} — "
                       f"{ratio:.2f}x (need {STOP_VS_SPREAD_MIN:.1f}x). The "
                       f"structure is stopped out by its own quote noise, not "
                       f"by price; it cannot survive a minute")
    return True, (f"stop ${sd:.2f} clears the ${spread:.2f} spread "
                  f"{ratio:.2f}x")


def assert_not_structural() -> None:
    """Refuse to start if a structural price ever enters the table."""
    bad = [k for k in CRITERIA if k in STRUCTURAL]
    if bad:
        raise ValueError(f"STRUCTURAL constants in CRITERIA: {bad}")


def describe() -> str:
    """One line per differing criterion — for the log and the status board."""
    _r = relaxed_active()
    rows = [f"{k}: {v[1] if _r else v[0]} "
            f"(strict {v[0]} / relaxed {v[1]})" for k, v in sorted(CRITERIA.items())]
    h = r_hurdle()
    rows.insert(0, f"R hurdle: {'MUTED' if h is None else f'{h:.2f}'}")
    return f"[criteria] MODE={mode()} · " + " · ".join(rows)


assert_not_structural()
# ⚠️ NOT LOGGED AT IMPORT. The mode is not knowable yet if configure.sh sets
# the flag after this module loads. main.py calls describe() once the process
# is configured, alongside relaxed.announce_once().
