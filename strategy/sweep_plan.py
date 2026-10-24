"""
strategy/sweep_plan.py  v1.18
v1.18  2026-10-24  CD.2 — (1) THE FIRST LOOK SPENDS WHAT IS ALREADY THERE (§37, as tcs_plan r112 does): _fired_events is
      process memory, so a mid-session restart re-fired today's latest REJECTED whatever its age, against
      levels.py's own rule that an interrupted firing sequence is never re-entered. (2) The trigger's window is
      TODAY's session in MARKET time - latest_rejection now filters on the judging bar's close (derived_store v4.9) and
      `since` is today's 09:30 with no now-86400 fallback before the open. (3) rejection_age_bars is measured from the
      bar's close, not from when the row was written. The operator, 2026-10-24: approved.
v1.17  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.16  2026-10-03  OTV4TEST r220 (TIME.1) — its private HH:MM parser is utils.time_utils.parse_hm (eight plans carried the same copy), and an UNREADABLE clock is DORMANT - no trade - instead of skipping the window check.
v1.15 2026-10-03  OTV4TEST r193 (CFG.1) — its config dials are read as config.NAME with NO literal fallback; config v4.48 now defines them (they were getattr defaults on names config never had). Values unchanged.
v1.14 2026-09-26  OTV4TEST r148 (WIN.1) — reads its entry window from config with NO literal fallback (one table, config.ENTRY_WINDOWS); a missing name now fails at import instead of silently defaulting. Value unchanged. 🔴 Its fallback END was (14, 0) against a live 15:40 — r81 pre-armed.
v1.13 2026-09-24  OTV4TEST r129 - "stop_vs_spread" IS RECORDED, WITH ITS RATIO. It
      was declared (r128) and never written on a pass. `sv_ratio` = the chosen
      wing's `stop_dist` (credit_vertical.search_wing's own number) / the short's
      bid-ask - the two quantities `criteria.stop_survivable` compares against
      STOP_VS_SPREAD_MIN (2.0) - recorded True beside credit/width/r. A refusal
      under that key still writes its row through `t.refuse`; search_wing does
      not return the refused wings' ratios, so that row's value stays empty
      (the report counts it as "refused, ratio unmeasured"). RECORD ONLY:
      nothing reads a check to decide (strategy/plan.py:491). Operator,
      2026-09-24: a stop-vs-spread report reviewed on Saturdays.
v1.12 2026-09-24  OTV4TEST r128 - "stop_vs_spread" DECLARED IN PLAN_CHECKS. It is
      a refusal gate this plan already raises: `_structure` calls
      `credit_vertical.search_wing`, which refuses a wing whose stop cannot
      survive its own bid-ask under the key "stop_vs_spread"
      (credit_vertical.py:460), and that key reaches `t.refuse` through
      `prep.structural`. TCSPlan declares it (tcs_plan.py:218); this plan did
      not, so check_structure_viable V7 read a string in sweep_credit_spread.py
      that fork r5 had moved here. Declaration only: `Plan.checks` is read by
      nothing (strategy/plan.py:769) - no behaviour changes.
v1.11 2026-09-23  OTV4TEST r113 - NO DEPTH GRADING (LVL.15 step 3, the sweep). The
      pierce floor (MIN_REJECTION_PCT, "a touch, not a sweep") and the relaxed
      ceiling (MAX_REJECTION_PCT) no longer refuse: the operator's definition
      of HELD has no depth, and step 3 was approved ("agree on all"). The floor
      was this box's most common sweep refusal (315 rows, 8 sessions); the
      ceiling never refused. The pierce is still RECORDED on every row.
v1.10 2026-09-22  OTV4TEST r106 - THE REJECTION FRESHNESS GATE IS GONE.
      Operator: "I'm done with rejection fresh bars, get rid of it altogether."
      A REJECTED older than REJECTION_FRESH_BARS left `chosen` unset, so the
      trade silently never fired - the LAST place any age decided anything,
      contradicting the ruling that age exists to ORDER the levels by recency
      and is "not relevant to anything else". PLAN_SPEC 31.1 has said it since
      the fork began: "Age does not matter. A previously held extreme is
      enough." The constant and its config key are removed; the age is still
      RECORDED, verdict None, gating nothing. Re-fire is still prevented by
      `_fired_events` on (level_id, bar_ts) - the clock never was what stopped
      a repeat.
v1.9  2026-09-22  OTV4TEST r104 - `levels_in_play` now ranks through the
      SHARED `rails_after_held` rather than its own copy. Three copies of
      "rails last" is three chances to drift, which is how three plans ended
      up with three private compositions before r33.
v1.8  2026-09-22  OTV4TEST r103 - THE HELD EXTREMES CLAIM THEIR SLOTS AND
      THE RAILS JOIN AFTER. `levels_in_play()` extracted so a checker drives the
      real composition. r33 wrote `levels = levels + tines` one line above the
      cap, in the revision titled "THE FORK BESIDE IT AS AN OR LEVEL", so a
      nearer rail evicted the furthest-out held extreme. Also records the rail
      projection, which was computed every tick and discarded here.
v1.7  2026-09-22  OTV4TEST r102 - THE RECORD-ONLY TELEMETRY THIS FILE'S OWN
      HEADER HAS PROMISED SINCE r5, RESTORED. mainline r233 added pierce_pts,
      level_dist_pts and level_dist_pct record-only; r5 rewrote the sweep into
      this file and carried the PARAGRAPH forward WITHOUT the CODE, so the
      header documented telemetry that did not exist and SWEEP.10 was
      unanswerable. Ported from r233 rather than reinvented. Also carries
      `age_bars` on the preparation - computed every tick since r5 and thrown
      away at the end of the function.
v1.6  2026-09-17  OTV4TEST r33 — THE PRIVATE MAP IS GONE; THIS PLAN READS THE ONE
      BOARD. It called `live_levels()`, ran its OWN `level_map.walk()` over the
      result, and then APPENDED the fork's rails into the same list — so a moving
      1h rail and a held session extreme arrived as one indistinguishable
      product. r19 stopped the rails reaching the ledger; this rebuilt the
      conjunction one layer up, in memory, at read time. Now: `board(price)` —
      no ORB bounds, so the walk is from SPOT — with levels in `above`/`below`
      and the rails returned SEPARATELY in `tines`. The rails stay IN PLAY for
      this plan (r5: "3 named up, 3 named down, plus the 1h pitchfork's tines")
      and the operator's 2026-09-17 ruling that the fork is an **OR** level, not
      an AND: one of the mapped levels OR a fork rail. What changed is that they
      arrive LABELLED, so nothing is silently conjoined, and `fork == "absent"`
      is an answer rather than a gap. Levels in play are unchanged in meaning
      and in count.
v1.5  2026-09-14  OTV4TEST r29 — the levels in play are WALKED (derived/level_map.walk):
      the newest held level each side of price, older ones only if further out —
      the same map the hunt's board reads, so the plans parse one set of levels
      (mainline PLAN_SPEC §38). The rails are added after the walk, unchanged.
v1.4  2026-09-12  OTV4TEST r15 — the rails come from `tines_now` (never a stored row); the
      PDH/PDL ladder is visible now that pools are classified by side (levels v4.3).
v1.3  2026-09-09  OTV4TEST r12 — anchors on the chosen structure (record only): GEX at the
      level, OI at the short, aggressor share at the level, charm at the short, nearest tine.
v1.2  2026-09-09  OTV4TEST r11 — `complement_richness`: as a condor's second leg the
      structure must be at least as rich as leg one, or it is REJECTED by name.
v1.1  2026-09-09  OTV4TEST r10 — `LAST_PREP`: the most recent preparation, so the
      condor's management plan can name the complement it is waiting on.
v1.0  2026-09-08  OTV4TEST r5 — THE SWEEP CREDIT SPREAD PLAN (PLAN_SPEC §31),
      agreed with the operator 2026-09-08/09. The thesis: a previously held
      extreme is swept and rejected; THE LEVEL HOLDS TO THE CLOSE. Sell a
      credit vertical against it, near the money, while it is rich.

      LEVELS IN PLAY — read from the derived level store (`live_levels`),
      never from a private map: the 3 nearest live named levels ABOVE spot
      (resistances) and the 3 nearest BELOW (supports), plus the 1h fork's
      tines (in the store since derived/levels v4.2, keyed on the tine, the
      tine rule applied there). Nothing inside the opening range exists (the
      store retired it TRAVERSED). The geometry gate (session_map.classify)
      still runs per level.

      BOTH SIDES PREPARED EVERY TICK FROM 09:35 — for every level in play the
      structure it WOULD sell if rejected: short strike = the first listed
      strike at/beyond THE LEVEL (the held extreme — operator's ruling, not the
      wick's extreme; a deep pierce is a weak level, so the cushion was
      protecting the trades least worth taking), wing searched with
      `credit_vertical.search_wing` against R_FLOOR on bid/ask, credit, width,
      R, and RICHNESS = credit / width recorded as a dial. The row carries the
      nearest candidate each side: "nearest above: PDH 712.40 — would sell
      713/718C for 0.85 (R 1.10, 17% of width) — waiting on: REJECTED".

      THE TRIGGER IS THE FACT. `DerivedStore.latest_rejection()` — a REJECTED
      event on a level in play, on the trade's side of spot, ~~FRESH (within
      REJECTION_FRESH_BARS of its bar)~~ — STRUCK at r106, the operator: "I'm
      done with rejection fresh bars, get rid of it altogether", superseding
      "it has to decide quickly"; the age is recorded and gates nothing, and
      a level does not stop being a swept held extreme because a clock ran.
      Struck rather than deleted, per §35 — pierce depth inside the band (MIN/MAX_REJECTION_PCT, the
      relaxed x3 ceiling as before), each event fired at most once. On a
      shallow pierce that is the wicking bar's own close; on a deep one, the
      next. Nothing is computed at the fire that was not on the row the tick
      before.

      THE BARS the strategy reads (PLAN_SPEC §31.2): window 09:35–14:00 ·
      REJECTED on a level in play · level not spent · price on the profitable
      side · ATR <= ATR_MAX_PCT (FEASIBLE) · the wing clears R_FLOOR
      (ECONOMICAL) · geometry. Sizing is the env default for verticals.
      The condor complement (`required_side`, `_can_open_credit_spread`) is
      untouched — the sweep may still form the other side of a condor; its
      spec comes last.

      OUTSIDE THE WINDOW THE PLAN OBSERVES AND DOES NOT WRITE (dormant).
"""
from __future__ import annotations

import logging
import time
import config
from strategy import credit_vertical as cv
from strategy import relaxed
from strategy.criteria import R_FLOOR, R_FLOOR_STOP
from strategy.plan import Plan, _n
from strategy.sweep_credit_spread import (
    ATR_MAX_PCT,
    is_spent, strike_beyond_sweep, tine_spent_key, _symbol_of,
)
from utils.math_utils import safe_float

logger = logging.getLogger(__name__)

GATES = {
    "EARLIEST_ET":          "SELECTION",
    "LATEST_ET":            "SELECTION",
    "LEVELS_EACH_SIDE":     "SELECTION",
}

EARLIEST_ET          = config.SWEEP_CS_EARLIEST_ET_FORK     # operator 2026-09-09; r148: no literal fallback
LATEST_ET            = config.SWEEP_CS_LATEST_ET_FORK       # r148: was a (14, 0) fallback against a live 15:40
LEVELS_EACH_SIDE     = int(config.SWEEP_CS_LEVELS_EACH_SIDE)


def _session_open_epoch() -> float:
    """Today's 09:30 ET as an epoch — the rejection must be today's."""
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
        n = datetime.now(et)
        return n.replace(hour=9, minute=30, second=0, microsecond=0).timestamp()
    except Exception:                                           # noqa: BLE001
        return 0.0


from utils.time_utils import parse_hm as _hm      # r220 (TIME.1): the one parser


class Candidate:
    __slots__ = ("level_id", "price", "kind", "provenance", "side", "boundary",
                 "short", "long", "credit", "width", "r", "r_stop", "richness",
                 "stop_prem", "why", "why_key", "geometry", "sv_ratio")   # r129

    def __init__(self, lvl):
        self.level_id, self.price = lvl["level_id"], float(lvl["price"])
        self.kind, self.provenance = lvl["kind"], lvl["provenance"]
        self.side = "call" if self.kind == "resistance" else "put"
        self.boundary = "ceiling" if self.kind == "resistance" else "floor"
        self.short = self.long = None
        self.credit = self.width = self.r = self.r_stop = self.richness = self.stop_prem = None
        self.sv_ratio = None                          # r129 - stop / short bid-ask
        self.why = self.why_key = ""
        self.geometry = None

    @property
    def sellable(self) -> bool:
        return self.short is not None and self.long is not None and (self.credit or 0) > 0

    def line(self) -> str:
        if not self.sellable:
            return f"{self.provenance} {self.price:.2f}: {self.why or 'no structure'}"
        return (f"{self.provenance} {self.price:.2f} — would sell "
                f"{float(self.short.strike):g}/{float(self.long.strike):g}"
                f"{'C' if self.side == 'call' else 'P'} for {_n(self.credit)} "
                f"(R {_n(self.r)}, {self.richness:.0%} of width)")



def levels_in_play(levels, tines, price_now, limit: int = None):
    """r103 — THE HELD EXTREMES CLAIM THEIR SLOTS FIRST; THE RAILS JOIN AFTER.

    Returns (above, below, held_above, held_below).

    🔴 THE DEFECT THIS EXISTS TO STOP, AND r33 WROTE IT ITSELF. r33's own title
    is "THE FORK BESIDE IT AS AN OR LEVEL" and its docstring says the rails sit
    "BESIDE the levels, never hidden in them" — and the same revision added
    `levels = levels + tines` one line before the `[:limit]` slice. So a rail
    nearer to spot took one of the three slots and the furthest-out held extreme
    fell off the board. `board()` forbids exactly this: "THE FORK IS A SECOND
    PRODUCT, NOT A LEVEL IN THIS LIST ... NEVER merged into above/below (r19:
    co-inform, do not conjoin)".

    🔑 r15, r19 AND r33 ALL SETTLED THIS AT THE PRODUCER AND GATED THE PRODUCER.
    `board()` has been correct since r19. Nothing checked what a CONSUMER did
    with its output, so the conjunction was rebuilt one layer up, at read time,
    and every gate stayed green (§23 — fix every reader, not just the writer).
    EXTRACTED so the checker drives THIS function rather than a paraphrase of it.

    🔑 WHY THEY ARE DIFFERENT KINDS OF THING, operator 2026-09-22: "The
    pitchfork is a co-informer and does not live in the liquidity level levels
    ... since it's a slope over time, it's a moving target it has to be a
    separate artifact", and "It's not a LIQUIDITY level. It's just a respected
    level." A held extreme is a fixed price that printed on a bar, with resting
    stops beyond it — that pool is what a sweep RAIDS. A rail is a diagonal that
    moves every bar and holds no pool. Ranking them together by distance
    compares two different quantities.

    ⚠️ THE RAILS REMAIN SELLABLE, BY RULING. r5 ("3 named up, 3 named down,
    PLUS the 1h pitchfork's tines"), r33 ("an OR level not an AND — one of the
    mapped levels or a fork rail"), and the operator on 2026-09-22 asked
    directly whether they should be dropped from this plan entirely: "The sweep
    still works with the pitchfork, because the channel is respected." A
    rejection off a respected rail is a real event even though no stops were
    taken there. PLUS, not competing — that is the whole of the change.

    ⚠️ `limit` CAPS THE HELD EXTREMES ONLY, and is a PREFERENCE rather than a
    bound — operator: "Three would be ideal ... if there's more I would like to
    have more, if there's less we can accept that too." Fewer than `limit` is an
    answer, never padded.
    """
    if limit is None:
        limit = LEVELS_EACH_SIDE
    px = float(price_now)
    above = sorted([l for l in levels
                    if l["kind"] == "resistance" and float(l["price"]) > px],
                   key=lambda l: float(l["price"]))[:limit]
    below = sorted([l for l in levels
                    if l["kind"] == "support" and float(l["price"]) < px],
                   key=lambda l: -float(l["price"]))[:limit]
    held_up, held_dn = len(above), len(below)
    # r104 — ONE DEFINITION OF THE INVARIANT, shared with tcs_plan and
    # liquidity_hunt. Three copies of "rails last" is three chances to drift.
    from derived.levels import rails_after_held as _raf
    above = _raf(above, [t for t in tines
                         if t["kind"] == "resistance" and float(t["price"]) > px],
                 key=lambda l: float(l["price"]))
    below = _raf(below, [t for t in tines
                         if t["kind"] == "support" and float(t["price"]) < px],
                 key=lambda l: -float(l["price"]))
    return above, below, held_up, held_dn


class SweepPreparation:
    __slots__ = ("tick", "above", "below", "nearest_above", "nearest_below", "rejected",
                 "chosen", "side", "boundary", "pool", "name", "rej_pct", "depth",
                 "short", "long", "credit", "width", "r", "stop_prem", "stop_dist",
                 "richness", "structural", "starved", "unmet", "ready",
                 "tines",          # r33 — the fork, BESIDE the levels, never hidden in them
                 "age_bars")       # r102 — the MEASUREMENT r241 kept, carried again

    def __init__(self, tick):
        self.tick = tick
        self.above, self.below = [], []
        self.nearest_above = self.nearest_below = None
        self.rejected = None
        self.chosen = None
        self.side = self.boundary = self.name = ""
        self.pool = self.rej_pct = None
        self.depth = ""
        self.short = self.long = None
        self.credit = self.width = self.r = self.stop_prem = self.stop_dist = self.richness = None
        self.structural, self.starved, self.unmet = [], [], []
        self.tines = []                     # r33 — "absent" is an answer, not a gap
        # 🔴 r102 — None, NOT 0. "How old is this rejection" and "it happened on
        # this bar" are different answers, and 0 is a plausible reading of both.
        self.age_bars = None
        self.ready = False

    def trade_line(self) -> str:
        return self.chosen.line() if self.chosen else "no trade prepared"


LAST_PREP = None          # r10: the condor's management plan reads the complement from here


class SweepPlan:
    name = "SweepCreditSpread"
    PLAN_CHECKS = ("entry_window", "price", "atr_pct", "levels_above", "levels_below",
                   "nearest_above", "nearest_above_credit", "nearest_above_r",
                   "nearest_below", "nearest_below_credit", "nearest_below_r",
                   "held_above", "held_below", "rails_in_play",   # r103
                   "rejected", "rejection_age_bars", "rejection", "pierce_depth",
                   "side_of_pool", "spent_level", "geometry", "short_anchor", "contract",
                   "credit", "width", "richness", "r", "r_stop", "stop_premium",
                   "complement_richness",
                   "stop_vs_spread",   # r128 - search_wing's survivability refusal (credit_vertical.py:460)
                   # r102 — record-only telemetry, restored; gates nothing
                   "pierce_pts", "level_dist_pts", "level_dist_pct")

    def __init__(self, store=None):
        self.planner = Plan(self.name, self.PLAN_CHECKS,
                            record_only=True, self_ledgers=True)
        self._store = store
        self._fired_events: set = set()      # (level_id, bar_ts) — each REJECTED fires once
        self._first_look_done = False         # CD.2: the session's existing REJECTED is spent at the first look

    def _board_(self, price: float):
        """r33 — THE ONE ACCESSOR, through the one shared entry point. No ORB
        bounds: this plan walks from SPOT, which is the operator's rule (r5/r29).
        Levels in `above`/`below`, the fork's rails separately in `tines` with
        `fork` naming built or absent. `board_for` prefers the LIVE engine (the
        only thing holding a fork) and falls back to the store this plan is
        BOUND to — r13: a plan uses its own store and never reaches a global."""
        try:
            from derived.levels import board_for
            return board_for(self._store_(), _symbol_of(), float(price))
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[sweep] level board unavailable — no levels in play: %s", exc)
            return {"state": "no_store", "above": [], "below": [], "tines": [], "fork": "absent"}

    def _store_(self):
        if self._store is not None:
            return self._store
        try:
            from data.derived_store import get_derived_store
            return get_derived_store()
        except Exception:                                       # noqa: BLE001
            return None

    # ── selection for one level: the structure it would sell ─────────────
    def _structure(self, cand: Candidate, chain) -> Candidate:
        contracts = chain.calls if cand.side == "call" else chain.puts
        if not contracts:
            cand.why, cand.why_key = "no contracts on this side", "chain"
            return cand
        inc = float(getattr(config, "STRIKE_INCREMENT", 1) or 1)
        # ANCHORED ON THE LEVEL, not the wick: sweep_price == pool_price
        k = strike_beyond_sweep(cand.price, cand.price, cand.boundary == "ceiling",
                                contracts=contracts, increment=inc)
        if k is None:
            cand.why, cand.why_key = "no listed strike at/beyond the level", "short_anchor"
            return cand
        short = next((c for c in contracts if abs(float(c.strike) - k) < 1e-6), None)
        if short is None or not (float(getattr(short, "mark", 0) or 0) > 0):
            cand.why, cand.why_key = f"no live quote at {k:g}", "contract"
            return cand
        w = cv.search_wing(contracts, short, cand.side, R_FLOOR, r_floor_stop=R_FLOOR_STOP)
        cand.short = short
        if w.long is None or not (w.credit or 0) > 0:
            cand.why, cand.why_key = (w.why or "no wing clears the R floor"), (w.why_key or "r")
            return cand
        cand.long, cand.credit, cand.width = w.long, float(w.credit), float(w.width)
        cand.r, cand.r_stop = float(w.r), (float(w.r_stop) if w.r_stop is not None else None)
        cand.richness = (cand.credit / cand.width) if cand.width > 0 else None
        cand.stop_prem = (float(w.fill) + float(w.stop_dist)) if (w.fill is not None and w.stop_dist is not None) else None
        _sb, _sa = safe_float(getattr(short, "bid", None)), safe_float(getattr(short, "ask", None))
        cand.sv_ratio = (round(float(w.stop_dist) / (_sa - _sb), 4)                       # r129
                         if (w.stop_dist is not None and _sb is not None and _sa is not None and _sa > _sb) else None)
        return cand

    # ══════════════════════════════════════════════════════════════════════
    def prepare(self, *, price_now, now_et, atr_pct=None, chain=None,
                orb_high=None, orb_low=None, df_1m=None, required_side: str = "",
                session_open_epoch: float = 0.0,
                complement_min_richness: float = 0.0) -> SweepPreparation:
        global LAST_PREP
        t = self.planner.tick(price_now)
        prep = SweepPreparation(t)
        LAST_PREP = prep
        hm = _hm(now_et)
        if hm is None:                                           # r220: a window that cannot be checked is not open
            t.dormant("entry_window", "the clock could not be read — no trade")
            return prep
        if hm is not None and hm >= tuple(LATEST_ET):
            t.dormant("entry_window", f"past {LATEST_ET[0]:02d}:{LATEST_ET[1]:02d} ET — observing only")
            return prep
        if hm is not None and hm < tuple(EARLIEST_ET):
            t.dormant("entry_window", f"before {EARLIEST_ET[0]:02d}:{EARLIEST_ET[1]:02d} ET — the opening "
                                      f"range is forming; observing only")
            return prep
        t.check("entry_window", None, True)
        price_now = safe_float(price_now)
        if not price_now or price_now <= 0 or price_now > 1e7:
            prep.starved.append("price_now"); t.starved("price_now"); return prep
        t.check("price", price_now, True)
        _atr = safe_float(atr_pct)
        atr_ok = _atr is None or _atr <= ATR_MAX_PCT
        t.check("atr_pct", _atr, atr_ok)
        if not atr_ok:
            prep.unmet.append(("atr_pct", f"ATR {_atr:.3f}% above the {ATR_MAX_PCT}% ceiling — "
                                          f"a boundary does not hold in that tape"))

        store = self._store_()
        if store is None:
            prep.starved.append("level_store"); t.starved("level_store"); return prep
        sym = _symbol_of()
        if not self._first_look_done:
            # CD.2 (§37) — whatever REJECTED already exists the first time this process looks is spent: an
            # interrupted firing sequence is MISSED, never re-entered (the TCS has done this since r112). Here,
            # before the board, so it runs on the first in-window look whatever else this tick does.
            self._first_look_done = True
            try:
                _s0 = float(session_open_epoch or _session_open_epoch())
                _prior = store.latest_rejection(sym, since_ts=_s0)
                if _prior:
                    self._fired_events.add((_prior["level_id"], _prior["bar_ts"]))
                    logger.info("[sweep] first look: %s REJECTED at %s predates this process - MISSED, never "
                                "re-entered (§37)", _prior["level_id"], _prior["bar_ts"])
            except Exception as exc:                            # noqa: BLE001
                logger.warning("[sweep] first-look read failed - no prior event marked: %s", exc)
        # r33 — THE ONE BOARD. This block built its OWN map: `live_levels()`,
        # then a local `level_map.walk()`, then the rails APPENDED INTO the same
        # list — so a moving 1h rail and a held session extreme arrived as one
        # indistinguishable product. r19 stopped the rails reaching the ledger;
        # this rebuilt the conjunction one layer up, in memory, at read time.
        # The board walks from SPOT (no ORB bounds — the operator's rule) and
        # hands the fork back SEPARATELY. Levels in play are unchanged in
        # meaning and in count; only the composition moved to one place.
        _b = self._board_(price_now)
        t.check("level_board", _b.get("state"), None)
        t.check("fork", _b.get("fork"), None)
        levels = list(_b.get("above", [])) + list(_b.get("below", []))
        tines = list(_b.get("tines", []))
        prep.tines = tines
        # r5 keeps the rails IN PLAY for this plan — "3 named up, 3 named down,
        # plus the 1h pitchfork's tines" — so they are still sellable here. What
        # changed is that they arrive LABELLED as the fork's, and a caller can
        # tell them apart; they are not silently indistinguishable from a held
        # session extreme. `fork == "absent"` is an answer, never a gap.
        # 🔴 r103 — THE CAP IS APPLIED TO THE HELD EXTREMES ALONE, AND THE RAILS
        # ARE ADDED AFTER IT. They used to be merged into `levels` BEFORE the
        # slice, so a rail nearer to spot took one of the three slots and the
        # furthest-out held extreme fell off the board. That is the exact thing
        # `board()` forbids — "THE FORK IS A SECOND PRODUCT, NOT A LEVEL IN THIS
        # LIST ... NEVER merged into above/below (r19: co-inform, do not
        # conjoin)" — and r5's wording was always "3 named up, 3 named down,
        # PLUS the 1h pitchfork's tines". Plus, not competing.
        # 🔑 THE OPERATOR'S REASON, 2026-09-22: "The pitchfork is a co-informer
        # and does not live in the liquidity level levels ... since it's a slope
        # over time, it's a moving target it has to be a separate artifact."
        # A rail's price is a function of TIME; a held extreme is a fixed price
        # that printed on a bar. Ranking them in one list by distance compares
        # two different kinds of thing.
        # ⚠️ THE RAILS ARE STILL SELLABLE HERE (r5) — they are added back as
        # their own entries once the held extremes have claimed their places, so
        # nothing this plan could trade before is withdrawn.
        above, below, _held_up, _held_dn = levels_in_play(levels, tines, price_now)
        t.check("held_above", _held_up, None)
        t.check("held_below", _held_dn, None)
        t.check("rails_in_play",
                (len(above) - _held_up) + (len(below) - _held_dn), None)
        t.check("levels_above", len(above), None)
        t.check("levels_below", len(below), None)
        if required_side:
            above = above if required_side == "call" else []
            below = below if required_side == "put" else []

        if chain is None:
            prep.starved.append("chain"); t.starved("chain"); return prep
        prep.above = [self._structure(Candidate(l), chain) for l in above]
        prep.below = [self._structure(Candidate(l), chain) for l in below]
        for c in prep.above + prep.below:
            c.geometry = t.level(c.price, c.boundary, c.provenance, orb_high, orb_low, price_now)
        na = next((c for c in prep.above if c.sellable), None) or (prep.above[0] if prep.above else None)
        nb = next((c for c in prep.below if c.sellable), None) or (prep.below[0] if prep.below else None)
        prep.nearest_above, prep.nearest_below = na, nb
        if na:
            t.check("nearest_above", na.price, None)
            t.check("nearest_above_credit", na.credit, None if na.credit is None else na.credit > 0)
            t.check("nearest_above_r", na.r, None)
        if nb:
            t.check("nearest_below", nb.price, None)
            t.check("nearest_below_credit", nb.credit, None if nb.credit is None else nb.credit > 0)
            t.check("nearest_below_r", nb.r, None)
        head = (f"in play: {len(prep.above)} above / {len(prep.below)} below — "
                f"nearest above: {na.line() if na else 'none'}; "
                f"nearest below: {nb.line() if nb else 'none'}")

        # ── the trigger: a fresh REJECTED on a level in play ──────────────
        # CD.2 — TODAY's session, by the bar's market time; no fallback to yesterday before the open
        _since = float(session_open_epoch or _session_open_epoch())
        rej = store.latest_rejection(sym, since_ts=_since)
        in_play = {c.level_id: c for c in prep.above + prep.below}
        chosen = None
        if rej and rej["level_id"] in in_play:
            key = (rej["level_id"], rej["bar_ts"])
            age_s = max(0.0, time.time() - float(rej.get("bar_close_epoch") or rej["ts_epoch"] or 0.0))  # CD.2
            age_bars = age_s / 60.0
            # r102 — COMPUTED HERE AND THROWN AWAY UNTIL NOW. The strategy wrote
            # a literal 0 to `sig.sweep_age_bars` because this never reached it.
            prep.age_bars = round(age_bars, 2)
            t.check("rejected", rej["price"], True)
            # 🔴 r106 — THE FRESHNESS GATE IS GONE. Operator, 2026-09-22: *"I'm
            # done with rejection fresh bars, get rid of it altogether."* A
            # rejection older than REJECTION_FRESH_BARS used to leave `chosen`
            # unset, so the trade silently never fired. That was the LAST place
            # any age decided anything, and it contradicted the ruling that age
            # exists to ORDER the levels by recency and is *"not relevant to
            # anything else"*.
            # 🔑 THE LEVEL IS WHAT MATTERS, NOT THE CLOCK. A previously held
            # extreme that was swept and rejected is the setup whether that
            # happened two bars ago or twenty — PLAN_SPEC 31.1 has said so
            # since the fork began: *"Age does not matter. A previously held
            # extreme is enough."* The gate was the one survivor of the age
            # rule r241 retired.
            # ⚠️ EACH EVENT STILL FIRES ONCE — `_fired_events` is keyed on
            # (level_id, bar_ts) and is what stops a re-fire, not the clock.
            # ⚠️ THE AGE IS STILL RECORDED, verdict None, gating nothing (§31):
            # removing the gate must not destroy the evidence that would show
            # whether stale-rejection fires behave differently.
            t.check("rejection_age_bars", round(age_bars, 2), None)
            if key in self._fired_events:
                t.check("rejected", rej["price"], False)
            else:
                chosen = in_play[rej["level_id"]]
                prep.rejected = rej
        else:
            t.check("rejected", None, False)

        if not chosen:
            if prep.unmet:
                gate, why = prep.unmet[0]
                t.refuse(gate, f"{head}. {why}")
                return prep
            t.hold(f"{head}. Waiting on: REJECTED")
            return prep

        # ── the bars, on the rejected level ───────────────────────────────
        prep.chosen, prep.side, prep.boundary = chosen, chosen.side, chosen.boundary
        prep.pool, prep.name = chosen.price, chosen.provenance
        prep.rej_pct, prep.depth = float(rej.get("pierce_pct") or 0.0), str(rej.get("depth") or "")
        t.anchor(invalidation=chosen.price)
        # 🔴 r113 — NO DEPTH GRADING. The operator's final definitions (LVL.15,
        # 2026-09-22): HELD is a wick in that failed to claim beyond — "NO
        # grading, depth, ranking or touch counts" — and step 3 was approved
        # 2026-09-23 ("Step 3, agree on all"). The pierce floor (MIN_REJECTION_PCT,
        # "a touch, not a sweep") was the sweep's MOST COMMON refusal on this box
        # (315 DECLINE rows over 8 sessions); the ceiling never refused. Both are
        # RECORDED, verdict None, so the evidence survives (§31) — a shallow HELD
        # and a deep one can still be told apart afterwards, they just both fire.
        t.check("rejection", prep.rej_pct, None)
        t.check("pierce_depth", prep.rej_pct, None)
        on_side = (price_now < chosen.price) if chosen.boundary == "ceiling" else (price_now > chosen.price)
        t.check("side_of_pool", price_now - chosen.price, on_side)
        if not on_side:
            prep.unmet.append(("side_of_pool", f"price {price_now:.2f} is not on the profitable side of "
                                               f"{chosen.price:.2f}"))
        _sk = tine_spent_key(chosen.provenance) or chosen.price
        # r11 — as a condor's complement, the second leg is rich or it is not taken:
        # at least as rich (credit / width) as the leg already on. A comparison,
        # not an invented number (operator 2026-09-09).
        if required_side and complement_min_richness > 0 and chosen.sellable:
            t.check("complement_richness", chosen.richness, (chosen.richness or 0) >= complement_min_richness)
            if (chosen.richness or 0) < complement_min_richness:
                prep.unmet.append(("complement_richness",
                                   f"as leg two: {chosen.richness:.0%} of width is thinner than leg one's "
                                   f"{complement_min_richness:.0%} — not rich enough to complete a condor"))
        spent, spent_why = is_spent(sym, chosen.side, _sk)
        t.check("spent_level", 1.0 if spent else 0.0, not spent)
        if spent:
            prep.structural.append(("spent_level", f"{chosen.provenance} {chosen.price:.2f} is SPENT — {spent_why}"))
        if chosen.geometry is False:
            prep.structural.append(("geometry", t.last_why))
        if not chosen.sellable:
            prep.structural.append((chosen.why_key or "contract", chosen.why))
        else:
            prep.short, prep.long = chosen.short, chosen.long
            prep.credit, prep.width, prep.r = chosen.credit, chosen.width, chosen.r
            prep.richness, prep.stop_prem = chosen.richness, chosen.stop_prem
            t.check("short_anchor", float(chosen.short.strike), True)
            t.check("contract", float(chosen.short.strike), True)
            t.check("credit", chosen.credit, chosen.credit > 0)
            t.check("width", chosen.width, None)
            t.check("richness", round(chosen.richness, 4) if chosen.richness else None, None)
            t.check("r", chosen.r, chosen.r >= R_FLOOR)
            t.check("r_stop", chosen.r_stop, None)
            t.check("stop_premium", chosen.stop_prem, None)
            t.check("stop_vs_spread", chosen.sv_ratio, True)   # r129 - search_wing passed it
            t.credit_spread(chosen.short.strike, chosen.long.strike, chosen.credit,
                            invalidation=chosen.price)
            # r12 — ANCHORS, record only: is the pool a gamma wall; who traded the rejection;
            # charm's sign into the close (the thesis is HOLDS TO THE CLOSE)
            from derived import anchors as _A
            _A.stamp(t, gex_at_level=_A.gex_at(chosen.price), oi_at_short=_A.oi_at(chosen.short.strike, chain),
                     aggressor_at_level=_A.aggressor_share(chosen.price), charm_at_short=_A.charm_at(chosen.short.strike),
                     tine_to_level=_A.nearest_tine(chosen.price),
                     # r103 — THE RAIL PROJECTION, RECORDED AT LAST. Computed on
                     # every 15s tick since the fork was built and discarded at
                     # this boundary every time. The plan can now tell "0.3%
                     # from a HARD held extreme with stops behind it" from "0.3%
                     # from a SOFT respected rail", and knows when the rail
                     # arrives (`bars_to_contact`) rather than only where it is.
                     **_A.rail_context(price_now))
            # ══ r102 — THE TELEMETRY r5's REWRITE DROPPED, RESTORED ═════════
            # 🔴 THIS FILE'S OWN HEADER HAS PROMISED THESE THREE SINCE r5 AND
            # NOTHING IMPLEMENTED THEM. mainline r233 added them record-only to
            # the OLD strategy; r5 rewrote the sweep into this file and carried
            # the PARAGRAPH forward without the CODE, so the header documented
            # telemetry that did not exist and SWEEP.10 was unanswerable.
            # ⚠️ IT WAS MASKED BY A SECOND FAULT: check_strike_beyond S3 asserts
            # exactly this, but died on an AttributeError before reaching it.
            # 🔑 PORTED, NOT REINVENTED. r233 recorded abs(pool - sweep_price):
            # the width of the TESTED RANGE the strike must clear. Here the pool
            # IS `chosen.price` and the wick is `level x (1 + pierce_pct)`, since
            # derived/levels computes `pierce = (hi - lvl) / lvl` — so that same
            # distance is `rej_pct x level`. Points AND percent, because points
            # alone are not comparable across a $83 NFLX and a $7,700 SPX.
            # RECORDED, GATING NOTHING (§31).
            _lvl = float(chosen.price or 0.0)
            _rp = float(prep.rej_pct or 0.0)
            if _lvl > 0:
                t.check("pierce_pts", round(_rp * _lvl, 4), None)
                _ld = abs(_lvl - price_now)
                t.check("level_dist_pts", round(_ld, 4), None)
                t.check("level_dist_pct",
                        round(_ld / price_now, 6) if price_now else None, None)
        if prep.starved:
            t.starved(*prep.starved); return prep
        if prep.structural:
            gate, why = prep.structural[0]
            t.refuse(gate, f"{chosen.provenance} {chosen.price:.2f} REJECTED ({prep.depth}): {why}")
            return prep
        if prep.unmet:
            gate, why = prep.unmet[0]
            t.refuse(gate, f"{chosen.provenance} {chosen.price:.2f} REJECTED ({prep.depth}): {why}")
            return prep
        self._fired_events.add((rej["level_id"], rej["bar_ts"]))
        prep.ready = True
        t.note(f"{chosen.provenance} {chosen.price:.2f} REJECTED ({prep.depth}, "
               f"{prep.rej_pct*100:.3f}%): {chosen.line()}")
        return prep
