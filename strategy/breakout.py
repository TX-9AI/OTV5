"""
strategy/breakout.py  v5.1
v5.1  2026-10-29  OTV5 r54 (BRK.16) — BREAKOUT IS PURELY DIRECTIONAL: range_clean AND room_to_run ARE NO LONGER CONDITIONS.
      The operator, 2026-10-29: "I want to take out any levels references that may interfere with the trade the levels
      that I'm talking about are the levels map and the liquidity map. The Hunt trade should be working from levels. The
      breakout trade should be purely directional without regard for levels in its path." Both bars leave CONDITIONS (so
      neither can be unmet and nothing routes on them); their names stay in PLAN_CHECKS, recorded each tick as
      "n/a - Breakout has no level reads", beside pool_price / pool_name / pool_dist_r / reach_pool (None). The dials
      (_DIALS, GATES, FITTED_ROOM_MIN_R, FITTED_RANGE_CLEAN_MAX) are untouched - fitting them is a separate open
      question (BRK.5) - and the LiquidityHunt keeps every level read it has. generate_signal: the fire tick also
      refuses a live price at or beyond the plan's entry_limit (edge +/- BRK_ENTRY_MAX_W x W) - the operator: "It should
      honestly refuse if it's already crossed 1/2W" ("that is runaway's domain"). "entry_limit" joins PLAN_CHECKS.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
THE SPECIFICATION. The plan searches; this declares what it must find.

v1.8  2026-10-24  OTV4TEST r316 (BRK.15) — `FRESH_BREAK`, THE RE-FIRE RULE THAT REPLACES `NEW_EXTREME` (FOUNDATIONAL). The
      operator, 2026-10-24 13:45 ET: "The new session high/low rule needs to be dropped. You established that the move
      was mostly done if we waited for a new extreme"; 13:56 ET: "For now, rearm it on every reentry". A side fires on
      the FIRST 1m close beyond its edge since 09:35 or since its latest close back inside; NEW_EXTREME stays declared
      for OT_BRK_REFIRE=extreme (the rollback) and is recorded beside every disagreement.
v1.7  2026-10-03  OTV4TEST r193 (CFG.1) — its config dials are read as config.NAME with NO literal fallback; config v4.48 now defines them (they were getattr defaults on names config never had). Values unchanged.
v1.6  2026-09-26  OTV4TEST r148 (WIN.1) — reads its entry window from config with NO literal fallback (one table, config.ENTRY_WINDOWS); a missing name now fails at import instead of silently defaulting. Value unchanged. BREAKOUT_LATEST_ET never existed in config; the 11:30 lived here.
v1.5  2026-09-24  OTV4TEST r131 — `NEW_EXTREME`, THE RE-FIRE RULE, declared
      FOUNDATIONAL. THE OPERATOR, 2026-09-24: *"A new reclaimed level has to
      happen before it can fire again? A new high for a long, a new low for a
      short."* The first entry per side per session is today's trigger (a
      closed 1m bar's close beyond the range edge); every later entry on that
      side must CLOSE above the highest high (long) / below the lowest low
      (short) of every prior RTH bar since 09:30. Tape simulation, QQQ 38
      sessions, +2R/-1R: +24.0R against -8.0R as built, trend days +44R vs
      +22R, chop -9R vs -24R. It is his definition of when THIS trade fires
      again, not a tuned band, so it has no knob (WA 36: "the best
      FOUNDATIONAL gate has no knob at all") — the constant is the gate's name.

v1.4  2026-09-21  OTV4TEST r84 — THE PLAN IS BUILT IN `__init__`, NOT ON
      FIRST USE. Lazily constructing it meant `BreakoutPlan()` only ever
      existed inside 09:35-11:30, so outside its window Breakout was in NO
      registry: no heartbeat, absent from the board, and nothing could tell
      "not yet constructed" from "crashed". r77 in a different costume — a
      lazy IMPORT there, a lazy CONSTRUCTION here. The import stays deferred
      (breakout_plan imports this module back); only the construction moves.
v1.3  2026-09-19  OTV4TEST r59 — `accepts_fitted()`. ROUTING IS NOT ADMISSION:
      while acceptance reads "any" nothing is ever unmet, so a fade route keyed
      on the live verdict is DEAD for the whole window. Routing reads the dial.
v1.2  2026-09-19  OTV4TEST r55 — THE OBSERVER POSTURE, AND THE WIDTH BAND WAS
      ANTI-SELECTIVE. Operator: "trade every break that gets a 1-minute candle
      acceptance beyond the boundary… informers are just observers for 2 weeks."
      `observe_only()` auto-expires at BRK_OBSERVE_UNTIL and FAILS CLOSED.
      🔴 orb_range MEASURED ANTI-SELECTIVE on n=747 — it refused 38% of breaks
      and kept the worse half (0.94x in, 1.10x out). Widened to feasibility-only.
      ROOM_MIN_R recategorised FOUNDATIONAL -> SELECTION: a resting pool is
      EVIDENCE about a break, not part of what makes it a Breakout.
v1.1  2026-09-19  OTV4TEST r53 — `flow_commit` STOPS BEING A PRIOR. Measured
      over 255 fleet breaks with prints: signed imbalance >= +0.10 lifts the 1R
      rate from 52.5% to 65.1% (1.24x, keeps 33%). The prior was 0.15, which
      measured 61.3% — right neighbourhood, slightly too strict.
      🔴 AND `tagged_frac` NEVER BINDS: median 1.00, p10 1.00 over the same
      sample. Kept as insurance against a degraded feed, labelled as insurance
      rather than evidence.
v1.0  2026-09-18  OTV4TEST r51 (BRK.1) — the operator's 5-minute opening range
      breakout, taken WITHOUT a retest.

WHY IT EXISTS, IN HIS WORDS. The ORB *"is typically a loser… which is crazy
because we're waiting for the level to prove itself before entering."* **The
retest IS that wait.** This trade pays for immediacy with EVIDENCE gathered at
the moment of the break instead of with time.

🔑 THIS FILE IS A DECLARATION, NOT A SEARCH (PLAN_SPEC §10). Operator,
2026-09-18: *"The strategy file is the specification. It lists the bars that
must be cleared to execute the trade. The plan file is what searches the feed
every tick for the nearest qualifying setup that satisfies the strategy… If it
can't satisfy every single hurdle then it doesn't put forward a plan. The plan
exists for the sole purpose of forming the trigger the strategy executes on.
Literally A, B, C was satisfied at X strike, execute if/when it reaches."*
So: this holds NO chain, picks NO strike, and reads NO feed. It states the
bars; `breakout_plan.py` clears them and hands back a trigger.

⚠️ EVERY CONSTANT BELOW IS A DECLARED PRIOR, AND TWO ARE MEASURED FACTS THAT
CONTRADICT AN EARLIER PRIOR. They are named here, in one place, so a study can
move them without hunting through the plan.
  🔴 VOLUME EXPANSION IS NOT A CONDITION. Measured 2026-09-18 over 736 fleet
     breaks (every warehouse `ohlc` object back to 2026-07-08): the break bar's
     volume multiple does NOT separate a break that reached +1R from one that
     was stopped — medians 0.62 vs 0.59 on the ORB baseline, and the best
     threshold on any of four baselines lifted the hit rate from 50.9% to
     55.3% (1.08x, n=266). **The operator predicted this before the study
     ran:** *"one of the characteristics of a fakeout is taking out stops and
     then turning the other way."* Stops are market orders, so a harvest
     MANUFACTURES the volume spike — it describes that a break happened, never
     whether it holds. It is recorded as context, never gated on.
  🔑 ROOM TO RUN IS THE ONE GATE WITH EVIDENCE, AND IT IS A BINARY. Same study,
     n=327 with a liquidity ledger: breaking into OPEN AIR reached 1R 63.0% of
     the time against 49.5% with a named pool ahead (base 51.4%). ⚠️ n=46 on
     the open-air arm, a standard error near 7 points — suggestive, not
     established. The DISTANCE bands did not behave monotonically (0–0.5R beat
     0.5–1.0R), most likely because a pool that close IS the level that formed
     the range, so no distance threshold is declared.
"""
from __future__ import annotations

import logging

import config

logger = logging.getLogger(__name__)

# ── WA §36 — EVERY GATE CONSTANT, NAMED AND CATEGORISED ─────────────────────
# SELECTION   the operator toggles it as data arrives
# FOUNDATIONAL it changes what the trade IS — his ruling, not a tuning knob
# FEASIBILITY  can the trade physically be done at all
# 🔑 THE THREE FOUNDATIONAL ONES ARE FOUNDATIONAL FOR ONE REASON: they decide
# whether this is a BREAKOUT at all. Take the window away and it is a different
# trade; take the close-beyond away and it is the wick-triggered entry r5 ruled
# out.
# 🔑 STRUCTURALLY THIS IS THE ORB WITHOUT THE RETEST (operator, 2026-09-19:
# *"Make it follow the orb structurally, but without a retest. And with better
# informers."*). Same boundary, same impulsive-candle stop, same geometry
# sizing — the ORB's own rules, reused rather than re-derived. What differs is
# WHEN it enters (immediately on acceptance, not after the level proves itself)
# and WHAT it weighs (the informers below). ⚠️ ROOM_MIN_R WAS FOUNDATIONAL AND
# IS NOT: a resting pool ahead is EVIDENCE about a break, not part of what
# makes it a Breakout — the operator ruled the informers observers, which only
# makes sense for a SELECTION gate.
GATES = {
    "EARLIEST_ET":          "FOUNDATIONAL",
    "LATEST_ET":            "FOUNDATIONAL",
    "FITTED_RANGE_MIN_PCT": "FEASIBILITY",   # dial: "any" — the ORB has no width band
    "FITTED_RANGE_MAX_PCT": "FEASIBILITY",   # dial: "any" — measured neutral, n=747
    "FITTED_ROOM_MIN_R":    "SELECTION",     # dial: "any" until 2026-10-03, then 1.23x on n=46
    "FITTED_FLOW_IMBALANCE_MIN": "SELECTION", # dial: "any" until 2026-10-03, then n=255 1.24x
    "FLOW_TAGGED_MIN":      "SELECTION",     # dial: "any" — and it has NEVER bound (tagged=1.00)
    "FITTED_REGIME_MAX":    "SELECTION",     # dial: "any" — never yet measurable
    "FITTED_DEPTH_DEPLETION_MIN": "SELECTION", # dial: "any" — no history exists to fit it
    "FITTED_R_FLOOR":       "SELECTION",     # dial: "any" (the ORB has no R floor)
    "FITTED_RANGE_CLEAN_MAX": "SELECTION",   # dial: "any" — the ORB has no such rule
    "RESEARCH_UNTIL":       "FOUNDATIONAL",  # the acceptance-ALL window's expiry
    "NEW_EXTREME":          "FOUNDATIONAL",  # r131: a re-fire on a side needs a new session extreme (OT_BRK_REFIRE=extreme)
    "FRESH_BREAK":          "FOUNDATIONAL",  # r316: a side fires on the first close beyond the edge since it was inside
}

# ── r131 — THE RE-FIRE RULE. Operator, 2026-09-24: *"A new reclaimed level has
# to happen before it can fire again? A new high for a long, a new low for a
# short."* The FIRST entry per side per session keeps the break trigger; every
# LATER one on that side needs the last closed 1m bar to CLOSE strictly above
# the highest HIGH (long) / below the lowest LOW (short) of every prior RTH bar
# since 09:30. "Fired" is any Breakout entry that session on that side in
# trades.db (DEC.1). No tolerance and no threshold, so nothing to relax: this
# constant is only the gate's NAME, the one `breakout_plan` refuses under.
NEW_EXTREME = "new_extreme"

# ── r316 (BRK.15) — THE RE-FIRE RULE, SINCE 2026-10-24. The operator: *"The new session high/low rule needs to
# be dropped"*; *"For now, rearm it on every reentry"*. The break trigger is a STATE (the last closed bar beyond
# the edge), so it needs a latch: a side fires only when the signal bar is the FIRST 1m close beyond the edge
# since 09:35 or since the side's latest close back inside it. A break the gates refused still spends that
# break (r282's lesson, kept): only a close back inside re-arms. Read from the feed store (DEC.1), failing
# closed. Like NEW_EXTREME this is only the gate's NAME; there is no number to relax.
FRESH_BREAK = "fresh_break"

# ── the window (admission also carries it; this is the strategy's own claim) ──
EARLIEST_ET = str(config.BREAKOUT_EARLIEST_ET)   # r148: the name now exists; no literal fallback
LATEST_ET = str(config.BREAKOUT_LATEST_ET)     # r148: the name now exists; no literal fallback

# ── the bars, as priors ──────────────────────────────────────────────────────
# ⚠️ UNMEASURED. The study that gives these numbers separates breaks that RAN
# from breaks that REVERTED on the three inputs a stop run cannot manufacture.
# Until it runs these are declared guesses and are labelled as such in the
# CONDITIONS text, so a plan row never implies more confidence than exists.
# 🔑 MEASURED 2026-09-18, n=255 fleet breaks with prints (08-24 → 09-18), streamed
# from the warehouse. Signed imbalance over the 3 minutes from the break bar,
# against the same +1R-before-−1R outcome the volume study used:
#     reached 1R   p25 −0.023   med +0.074   p75 +0.165
#     stopped      p25 −0.073   med +0.013   p75 +0.099
#     base rate 52.5%  ·  >= +0.10 -> 65.1% (lift 1.24x, keeps 33%, n=83)
# The medians sit 6x apart. This is the ONE entry gate with real separation —
# volume had none (n=736, lift 1.08x) and room_to_run is suggestive on n=46.
# ⚠️ WAS 0.15 AS A PRIOR, AND THE DATA MOVED IT DOWN: 0.15 measured 61.3% against
# 0.10's 65.1%, so the guess was in the right place and slightly too strict. The
# dip at 0.15 is almost certainly noise at this sample size; 0.10 is taken
# because it is the best-supported point, not because the curve is smooth.
FITTED_FLOW_IMBALANCE_MIN = float(config.BRK_FLOW_IMBALANCE_MIN)
FLOW_TAGGED_MIN = float(config.BRK_FLOW_TAGGED_MIN)
FITTED_REGIME_MAX = float(config.BRK_REGIME_MAX)
FITTED_DEPTH_DEPLETION_MIN = float(config.BRK_DEPTH_DEPLETION_MIN)
FITTED_ROOM_MIN_R = float(config.BRK_ROOM_MIN_R)
FITTED_R_FLOOR = float(config.BRK_R_FLOOR)
# 🔑 MEASURED 2026-09-19, n=747 breaks. THE OLD BAND (0.05%-1.25%) WAS THE
# DOMINANT FILTER AND IT WAS ANTI-SELECTIVE: it refused 38% of breaks and the
# ones it KEPT did worse than the ones it threw away — 47.3% (0.94x) inside
# against 55.7% (1.10x) outside, the only candidate band scoring below no gate
# at all. ⚠️ AND NO BAND IS AN EDGE: the best of seven candidates managed 1.08x
# on n=302 (~1.4 SE), the volume story again. Width is FEASIBILITY, never a
# prediction. ⚠️ THE ORB HAS NO WIDTH BAND AT ALL — it answers a degenerate
# range by sizing ONE LOT LOUDLY rather than refusing — so a band here is a
# divergence from the trade this one is meant to mirror.
FITTED_RANGE_MIN_PCT = float(config.BRK_RANGE_MIN_PCT)
FITTED_RANGE_MAX_PCT = float(config.BRK_RANGE_MAX_PCT)
FITTED_RANGE_CLEAN_MAX = float(config.BRK_RANGE_CLEAN_MAX)

# ── ACCEPTANCE: "ALL", FOR TWO WEEKS (operator, 2026-09-19) ─────────────────
# *"Have it trade every break that gets a 1-minute candle acceptance beyond the
# boundary… informers are just observers for 2 weeks."* And, on the shape:
# *"I still want the informer set as triggers in the strategy package, but set
# the acceptance to 'all'."*
# 🔑 SO NOTHING IS BYPASSED. Every informer below is still a DECLARED TRIGGER;
# the plan still refuses to form unless every one of them clears; the strategy
# still re-checks the PERSISTENT ones on the firing tick. What widens is the
# ACCEPTANCE BAND, declared here beside the bar it belongs to. An earlier cut of
# r55 made the informers skip the trigger machinery instead, and the operator
# ruled against it — rightly: a bypass has to be un-bypassed later, and the code
# that un-bypasses it is code nobody has run.
# 🔑 THE FIT DOES NOT NEED A NARROW BAND TO BE POSSIBLE. Every informer's
# CONTINUOUS value is recorded on every tick, so any threshold can be fitted
# afterwards from the values themselves — more than a stored boolean verdict
# could have given us.
# 🔑 AND "ALL" IS WHAT MAKES THE OPERATOR'S INVARIANT TRUE: *"if we do get an
# orb trade a breakout trade should've preceded it, because it's the same trade
# but without the retest."* That holds only while Breakout's acceptance is no
# narrower than the ORB's, and the ORB has no width band, no cleanliness rule,
# no pool rule and no R floor. Narrow any of these before the fit and an ORB
# trade can fire that Breakout refused — the two diverge, silently.
# a date guaranteed past any research window, so `accepts_fitted` always
# evaluates the dial rather than the acceptance
from datetime import date as _date
_FITTED_DATE = _date.max

RESEARCH_UNTIL = str(getattr(config, "BRK_RESEARCH_UNTIL", "") or "")


def research_active(today=None) -> bool:
    """Is the acceptance-ALL window still open?  ⚠️ FAILS CLOSED: an unreadable
    or absent date means the FITTED bands bind, never that everything is taken."""
    if not RESEARCH_UNTIL:
        return False
    try:
        from datetime import date, datetime
        from zoneinfo import ZoneInfo
        d = today or datetime.now(ZoneInfo("America/New_York")).date()
        return d <= date.fromisoformat(RESEARCH_UNTIL)
    except Exception:                                            # noqa: BLE001
        return False


# ── THE DIALS ───────────────────────────────────────────────────────────────
# 🔑 ONE ACCEPTANCE PER INFORMER, AND TODAY EVERY ONE OF THEM IS "any".
# Operator, 2026-09-19: *"set the acceptance to 'any' for each of those
# informers that will emerge as dials in 2 weeks."*
# Each entry below IS the dial. Today it reads "any" — the bar is evaluated,
# recorded and narrated exactly as always, and every value clears it. In two
# weeks each one is replaced by the number the data gives, one informer at a
# time, and nothing else in this file or the plan has to change.
# ⚠️ "any" IS AN ACCEPTANCE, NOT AN ABSENCE. The bar is still a declared
# trigger; the plan still refuses to form a plan unless it clears; the strategy
# still re-checks the PERSISTENT ones on the firing tick. A row that reads
# `flow_commit +0.02 (accept any)` is telling the truth about both halves.
_DIALS = {
    # informer        how it is compared          the number it becomes
    "flow_commit":   (">=", "FITTED_FLOW_IMBALANCE_MIN"),
    "gamma_regime":  ("<=", "FITTED_REGIME_MAX"),
    "depth_thin":    (">=", "FITTED_DEPTH_DEPLETION_MIN"),
    "room_to_run":   (">=", "FITTED_ROOM_MIN_R"),
    "range_clean":   ("<=", "FITTED_RANGE_CLEAN_MAX"),
    "orb_range":     ("band", ("FITTED_RANGE_MIN_PCT", "FITTED_RANGE_MAX_PCT")),
    "r":             (">=", "FITTED_R_FLOOR"),
    "flow_tagged":   (">=", "FLOW_TAGGED_MIN"),
}


def _dial(bar: str) -> str:
    """How this informer's acceptance READS on a plan row: "accept any", or the
    number. ⚠️ A row must never imply a threshold that is not being applied."""
    band = acceptance(bar)
    if band == "any":
        return "accept any"
    if isinstance(band, tuple):
        return f"{band[0]:.2%}-{band[1]:.2%}"
    how, _ = _DIALS[bar]
    return f"{how} {band:+.2f}"


def acceptance(bar: str, today=None):
    """This informer's acceptance right now: the string "any", or the dial."""
    if bar not in _DIALS:
        return "any"
    if research_active(today):
        return "any"
    how, ref = _DIALS[bar]
    if how == "band":
        return (globals()[ref[0]], globals()[ref[1]])
    return globals()[ref]


def accepts_fitted(bar: str, value) -> bool:
    """`accepts`, but ALWAYS against the fitted dial, ignoring the research
    window.

    🔑 ROUTING IS NOT ADMISSION. While acceptance reads "any" every value
    clears, so asking "did this bar fail?" to decide where a HARVEST should be
    handed off would answer "never" for the whole window — and the fade route
    to the hunt and the sweep would be silently dead exactly when the operator
    wants both arms covered. The ROUTING question is a fact about the tape
    ("is this shaping up as a grab?"), not a question about admission.
    """
    return accepts(bar, value, _FITTED_DATE)


def accepts(bar: str, value, today=None) -> bool:
    """Does this informer's ACCEPTANCE admit `value`?

    ⚠️ "any" ADMITS AN ABSENT READING TOO. While the acceptance is "any" the
    operator's instruction is to trade every accepted break, so an unreadable
    regime or an empty book must not quietly refuse — that would be a gate
    nobody declared, which is this repo's oldest failure shape.
    """
    band = acceptance(bar, today)
    if band == "any":
        return True
    if value is None:
        return False
    how, _ = _DIALS[bar]
    v = float(value)
    if how == "band":
        return band[0] <= v <= band[1]
    return v >= band if how == ">=" else v <= band


if research_active():
    logger.info("[breakout] ACCEPTANCE=any on %s — each informer is still a "
                "declared trigger; these are the dials that get numbers on %s",
                ", ".join(sorted(_DIALS)), RESEARCH_UNTIL)

class Breakout:
    """The specification. `breakout_plan.BreakoutPlan` satisfies it or stays silent."""

    name = "Breakout"

    # ── WHAT MUST BE TRUE. name -> what "true" means ─────────────────────────
    CONDITIONS = {
        "entry_window":  f"{EARLIEST_ET}-{LATEST_ET} ET",
        "orb_range":     (f"a 5-minute opening range is established and its width is "
                          f"{_dial('orb_range')} of spot — neither a "
                          f"three-cent range nor a gap-day monster"),
        # r54 (BRK.16): "range_clean" is no longer a condition - Breakout reads no levels map
        "break_close":   ("a CLOSED 1m bar's CLOSE beyond the range edge — r5's rule, bodies "
                          "decide and wicks test. This is the anti-fakeout gate that costs "
                          "nothing in TIME, which is the whole point of skipping the retest"),
        "flow_commit":   (f"aggressor imbalance {_dial('flow_commit')} in the break "
                          f"direction with tagged_frac {_dial('flow_tagged')} "
                          f"(MEASURED n=255: >= +0.10 lifts the 1R rate 52.5% -> 65.1%. "
                          f"The tagged floor has never bound — every print carries a side — "
                          f"and is kept as insurance against a degraded feed)"),
        "gamma_regime":  (f"regime {_dial('gamma_regime')} — NOT pinning. A break into a pinning "
                          f"regime is one dealers fade; into a trending regime, one they "
                          f"amplify. (PRIOR, unmeasured)"),
        "depth_thin":    (f"resting depth ahead of price DEPLETING, not refilling "
                          f"({_dial('depth_thin')}) — the book's answer to the same "
                          f"question flow_commit asks of the tape, and independent of it. "
                          f"(PRIOR, unmeasured)"),
        # r54 (BRK.16): "room_to_run" is no longer a condition - "purely directional without regard for
        # levels in its path" (the operator, 2026-10-29)
    }

    # 🔑 WHICH BARS MUST STILL BE TRUE WHEN PRICE ARRIVES (PLAN_SPEC §10:
    # *"on t+1 the strategy checks the declared conditions against the tick and,
    # if all are true, executes THAT trade"*).
    # Operator, 2026-09-18: *"some of those other trigger components may be
    # conditions that need to remain in a particular state, such as pinning, or
    # rising ATR, or above VWAP. So the plan will say if all of those conditions
    # are still true and price reaches X, then everything is satisfied."*
    # ⚠️ THE TRIGGER IS COMPOUND, AND THE SPLIT IS THE POINT. A SETTLED bar is
    # a fact that cannot decay between the plan and the fill — the range was
    # this wide, the bar closed beyond, this strike is listed. A PERSISTENT bar
    # is LIVE STATE: the regime can flip, the tape can stop paying up, the book
    # can refill. Re-checking a settled fact wastes a tick; NOT re-checking live
    # state fires a trade on evidence that has already expired.
    # ⚠️ ADDING ONE IS A ONE-LINE CHANGE — "above VWAP" or "rising ATR" join
    # CONDITIONS and then this tuple. They are deliberately NOT here yet: no
    # study has shown either separates a break that ran from one that reverted,
    # and r51's own volume result is what that costs when it is assumed.
    PERSISTENT = ("flow_commit", "gamma_regime", "depth_thin")

    # the structural bars — selectable facts, not market conditions
    STRUCTURAL = ("contract", "premium", "stop_survivable", "r", "target")

    # everything recorded per tick, whether it gates or not
    PLAN_CHECKS = tuple(CONDITIONS) + STRUCTURAL + (
        "range_width_pct", "break_dir", "break_close_px", "vol_multiple",
        "flow_imbalance", "flow_tagged", "regime", "depth_ratio",
        "pool_price", "pool_name", "pool_dist_r", "reach_measured", "reach_pool",
        "range_clean", "room_to_run",            # r54 (BRK.16): recorded "n/a - Breakout has no level reads"
        "entry_limit",                           # r54 (BRK.16): edge +/- BRK_ENTRY_MAX_W x W
        "verdict", "defer_to", "persist_ok",
        NEW_EXTREME, "side_fired_today", "session_extreme",     # r131
        FRESH_BREAK, "break_run_from",                           # r316 (BRK.15)
    )

    # ⚠️ RECORDED, NEVER GATED. `vol_multiple` is here so the study that
    # rehabilitates or buries it has the value on every row — the same reason
    # `derived/snapshot.py` exists (r240/r243/r244: a field computed, used for a
    # DECISION, and never recorded).
    CONTEXT_ONLY = ("vol_multiple",)

    def __init__(self):
        # 🔴 r84 — THE PLAN IS BUILT HERE, NOT ON FIRST USE, AND THE DEFECT WAS
        # INVISIBILITY RATHER THAN BREAKAGE. `self._plan = None` plus a
        # build-on-demand `_plan_()` meant `BreakoutPlan()` was only ever
        # constructed inside the 09:35-11:30 window, because that is the only
        # time anything calls `prepare()`. A plan registers itself in
        # `strategy.plan.REGISTRY` ON CONSTRUCTION, so outside its window
        # Breakout was in NO registry at all: it wrote no heartbeat, appeared
        # on no board, and NOTHING COULD TELL "not yet constructed" FROM
        # "crashed". Measured 2026-09-21: six restarts after 11:30 and the
        # r83 board read "Breakout NOT RUNNING — never heartbeat today" while
        # the strategy was perfectly healthy and would have worked at 09:35.
        # ⚠️ THIS IS r77 IN A DIFFERENT COSTUME. There the lazy IMPORT inside
        # emit() let check_imports pass green on a strategy that raised on
        # every tick for a whole session; here the lazy CONSTRUCTION hides the
        # plan from every registry-based check. Same class: deferring work
        # past the point where anything inspects it.
        # ⚠️ THE IMPORT STAYS DEFERRED AND THAT IS LOAD-BEARING — `breakout_plan`
        # imports THIS module back (its own `__init__` does
        # `from strategy.breakout import Breakout as _Spec`), so a module-scope
        # import here would cycle. Inside `__init__` this module is already
        # fully loaded, so the cycle cannot form. Verified by construction, not
        # assumed.
        from strategy.breakout_plan import BreakoutPlan
        self._plan = BreakoutPlan()

    def _plan_(self):
        # kept as the accessor every call site already uses; it no longer
        # decides WHEN the plan exists, only hands it back.
        if self._plan is None:                                   # defensive only
            from strategy.breakout_plan import BreakoutPlan
            self._plan = BreakoutPlan()
        return self._plan

    def prepare(self, **kw):
        """The plan runs. This file never searches."""
        return self._plan_().prepare(spec=self, **kw)

    def generate_signal(self, **kw):
        """CONFIRM the plan's trigger, then execute it. Picks nothing.

        🔑 THE STRATEGY DETERMINES WHETHER THE TRIGGER COMPONENTS ARE IN PLACE.
        Operator, 2026-09-18: *"the strategy must determine if all the trigger
        components provided by the plan are in place to fire."* The plan's job
        ended when it handed over a trigger — a strike, a stop, an R, and the
        named conditions that must still hold. This re-reads those components
        against THIS tick and fires only if every one is in place.
        ⚠️ IT DOES NOT RE-DERIVE THEM. Re-searching here would make this a
        second plan, which is exactly the duplication PLAN_SPEC §10 removes; it
        reads what `prepare()` recorded and judges it.
        ⚠️ AND THE CHECK IS NOT REDUNDANT WITH `ready`. `ready` is the PLAN's
        verdict that a qualifying setup exists. This is the STRATEGY's verdict
        that it is still true now, and the two are different questions the same
        way a signed contract and a settled trade are different events.
        """
        prep = self.prepare(**kw)
        if prep is None:
            return None
        if not getattr(prep, "ready", False):
            return prep.tick.already()

        # every PERSISTENT bar must still read true on this tick
        stale = [c for c in self.PERSISTENT
                 if not (prep.conditions.get(c) or (None, "", False))[2]]
        if stale:
            prep.tick.check("persist_ok", None, False,
                            note="decayed since the plan: " + ", ".join(stale))
            return prep.tick.hold(f"trigger incomplete — {', '.join(stale)} no longer true")

        # and the trigger itself: price still beyond the edge the break cleared
        px, edge = prep.price_now, prep.trigger
        if px is None or edge is None:
            return prep.tick.hold("trigger unreadable — price or edge absent")
        held = px > edge if prep.direction == "long" else px < edge
        if not held:
            return prep.tick.hold(
                f"trigger not in place — price {px:.2f} back inside {edge:.2f}")
        # r54 (BRK.16) — AND NOT ALREADY PAST 1/2 W ON THIS TICK. The operator, 2026-10-29: "if we haven't entered
        # before it reaches 1W, absolutely refuse it — that is runaway's domain. It should honestly refuse if it's
        # already crossed 1/2W." The plan refused a break CLOSE past it; this refuses the live price at the fire.
        lim = getattr(prep, "entry_limit", None)
        if lim is not None and (px >= lim if prep.direction == "long" else px <= lim):
            prep.tick.check("persist_ok", None, False, note=f"price {px:.2f} past the 1/2 W limit {lim:.2f}")
            return prep.tick.hold(
                f"refused at the fire — price {px:.2f} already past 1/2 W ({lim:.2f}): runaway's domain")

        return prep.emit(self.name)
