"""
strategy/tcs_plan.py  v1.10
v1.10  2026-10-24  CD.2 — the trigger and the first look ask for TODAY's session by the bar's MARKET time (derived_store v4.9
      filters latest_event on the judging bar's close): `since` is today's 09:30 with no now-86400 fallback before the
      open. The HH:MM window test (r112) now has the date beside it. The operator, 2026-10-24: approved.
v1.9  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.8  2026-10-03  OTV4TEST r220 (TIME.1) — its private HH:MM parser is utils.time_utils.parse_hm (eight plans carried the same copy), and an UNREADABLE clock is DORMANT - no trade - instead of skipping the window check.
v1.7  2026-09-26  OTV4TEST r148 (WIN.1) — reads its entry window from config with NO literal fallback (one table, config.ENTRY_WINDOWS); a missing name now fails at import instead of silently defaulting. Value unchanged. 🔴 Its fallback END was (14, 0) against a live 15:40 — r81 pre-armed.
v1.6  2026-09-24  OTV4TEST r129 - "stop_vs_spread" RECORDS THE RATIO THE RULE TESTS.
      It recorded `stop_dist` (DOLLARS) under the ratio's name, and only on a pass,
      so no report could say how close a wing came. `criteria.stop_survivable`
      compares stop distance / the short's bid-ask against STOP_VS_SPREAD_MIN
      (2.0); `sv_ratio` is that number, computed in the same loop from the same
      `sd`, `sb`, `sa`. Recorded True on the chosen wing, and False (the BEST
      ratio among the refused wings) just before a stop_vs_spread refusal, so
      `t.refuse` carries it into the row. RECORD ONLY: `PlanTick.check` writes,
      nothing reads a check to decide (strategy/plan.py:491). Operator,
      2026-09-24: a stop-vs-spread report reviewed on Saturdays.
v1.5  2026-09-23  OTV4TEST r112 - THE TRIGGER COULD NEVER MATCH, AND NOW IT CAN.
      The level engine retires a breached level in the SAME step it publishes
      ACCEPTED, and this plan required the ACCEPTED level to be on the live
      board - so the trigger and its candidate could never meet. 0 of 110
      trades on this box are TCS (LVL.15 recorded it: 0 of 37 ticks matched
      after 43 ACCEPTED events). The candidate now comes FROM THE EVENT when
      the board no longer holds it, priced by the same _structure(). And the
      3-bar freshness gate is REMOVED on the operator's ruling of 2026-09-23;
      the two jobs it did by accident are now stated rules: the breach's own
      bar must be inside the TCS window ("ACCEPTED after 11:30"), and the
      latest ACCEPTED that already existed at this process's first look is
      marked spent (section 37 - a restart never re-enters). Age is still
      recorded as accepted_age_bars, gating nothing.
v1.4  2026-09-22  OTV4TEST r104 - THE RAILS NO LONGER OUTRANK A HELD
      EXTREME. `levels = levels + prep.tines` merged both into ONE distance
      ranking, so a rail nearer than a held session extreme became
      nearest_above/nearest_below and the spread sold against it. Operator:
      "It's SOFTER than held levels." Ordering key and the deliberate
      no-side-filter are UNCHANGED; only the rank between the two kinds moves,
      and the rails stay selectable (r33's OR level). Records rails_in_play as
      its own count and the rail projection as anchors - this plan previously
      knew only that a fork was built or absent.
v1.3  2026-09-17  OTV4TEST r33 — THE `ny` FILTER IS GONE, AND THIS PLAN HAS A FORK
      FOR THE FIRST TIME. From r9 to r32 the level read was
      `live_levels()` filtered to `provenance == "ny"`, which broke the r5 ruling
      in BOTH halves: not "3 named up, 3 named down" — measured on the box the
      day it was found, it saw **3 of 11** held levels, discarding six London and
      two Asia extremes built from the same tape by the same rule — and not
      "plus the 1h pitchfork's tines", which it has never had. The parenthetical
      "(the store's `ny` levels)" was an IMPLEMENTATION NOTE written into an
      agreed definition row in PLAN_SPEC §34.1, and it governed the trade for
      twenty-four revisions. ⚠️ THE PLAN HAS NEVER FIRED — `trades.db` holds no
      TrendCreditSpread row — so nothing realised was lost; the cost is entirely
      opportunity. Now it reads `board(price)` like every other level plan, and
      its candidate set is the mapped levels UNION the rails (the fork is an OR
      level, not an AND). Operator, 2026-09-17: *"I don't give a rat's shit if
      it's a New York level or a London level or an Asia level."*
v1.2  2026-09-14  OTV4TEST r29 — WORDING ONLY: the TRIGGER paragraph said "today's high as
      resistance, today's low as support". The code has never read today's: the
      store's `ny` levels are CLOSED RTH sessions (liquidity_mapper LIQ.6 — a forming
      high is not a level). The text now says what the code does. Which one the TCS
      SHOULD trade is TCS.3, a ruling. No code changed.
v1.1  2026-09-09  OTV4TEST r12 — anchors on the chosen structure (record only).
v1.0  2026-09-09  OTV4TEST r9 — THE TREND CREDIT SPREAD PLAN (PLAN_SPEC §34),
      agreed with the operator 2026-09-09. The purpose, his words: *"catch
      large moves in the afternoon on some macro catalyst good or bad, and let
      theta do the work on our behalf since debits on 0DTE late in the day are
      deteriorating rapidly."*

      TRIGGER — an ESTABLISHED NY LEVEL (the store's `ny` levels: the high and
      low of a CLOSED prior RTH session that price has not accepted through — a
      high is resistance, a low support) ACCEPTED after 11:30 — two closed 1m
      bars beyond it, the level store's own ACCEPTED event — AND the move
      OUTSIDE THE EXPECTED MOVE. ⚠️ NOT today's forming high/low: that is not a
      level until the session closes (LIQ.6), and PLAN_SPEC §34's "today's high /
      low" never matched this code (TCS.3). "Outside" is read against the EM assessment
      that stood BEFORE the move: every tick the plan computes spot ± EM
      (ATM IV, remaining session) and prints it; on the first 1m close beyond
      a live extreme it FREEZES the previous tick's band as that move's
      reference; acceptance (the second close) with price outside the frozen
      band fires. A close back inside before acceptance clears the reference.
      Re-centering each tick would chase the move and never be exceeded.
      Operator: if it never fires, or fires too loosely, the EM gate is the
      first suspect — so the row carries the band and the distance every tick.

      DIRECTION AND ANCHOR — the move's. A high accepted -> sell the PUT spread
      behind it, short at the first strike at/below THE ACCEPTED LEVEL (the
      former resistance is now the floor the trade sells against — near the
      money, rich, and the exit has a name). A low accepted -> the CALL spread
      above it.

      STRUCTURE — r238's rule KEPT on purpose: the WIDEST wing that clears 1:1
      on the expiry basis = the most credit the R floor allows (best-R would
      pick the narrowest, thinnest-credit wing — "it was for nothing"). Bars:
      POP >= TCS_MIN_POP (1 - |short delta|; the theta-not-direction bar),
      credit >= TCS_MIN_CREDIT_PCT_WIDTH of width, the nickel-multiple floor,
      the 15%-of-credit stop survivable against the short's spread. RECORDED:
      ADX (retired as a bar — measured flat; the EM breach is the size read),
      richness = credit / width, and the protective leg's own bid/ask as a
      fraction of the wing (long_leg_spread_pct) — barred once seen.

      ONE PER SESSION is NOT a rule here; leg-one-of-a-condor is: the TCS may
      be the FIRST vertical on the board, never the second (authorize() and
      `_can_open_credit_spread` are untouched — the complement must be a
      sweep). The 15% stop applies to a LONE vertical only (the sibling
      suppresses it when hedged — exit_engine, unchanged mechanism).

      WINDOW 11:31–14:00; outside it the plan observes and does not write.
      The plan prepares BOTH sides every tick: the nearest live extreme each
      way, the EM band, and the spread it would sell if that extreme were
      accepted — "waiting on: ACCEPTED outside the EM".
"""
from __future__ import annotations

import logging
import time

import config
from strategy import credit_vertical as cv
from strategy.criteria import stop_survivable
from strategy.plan import Plan, _n
from strategy.sweep_credit_spread import strike_beyond_sweep, _symbol_of
from utils.math_utils import safe_float

logger = logging.getLogger(__name__)

GATES = {
    "TCS_START_ET":         "FOUNDATIONAL",
    "TCS_ENTRY_END_ET":     "SELECTION",
}

TCS_START_ET        = config.TCS_START_ET        # r148: no literal fallback
TCS_ENTRY_END_ET    = config.TCS_ENTRY_END_ET    # r148: was a (14, 0) fallback against a live 15:40
TCS_MIN_POP         = float(getattr(config, "TCS_MIN_POP", 0.70))
TCS_MIN_CREDIT_PCT  = float(getattr(config, "TCS_MIN_CREDIT_PCT_WIDTH", 0.10))
TCS_R_FLOOR_EXPIRY  = float(getattr(config, "TCS_R_FLOOR_EXPIRY", 1.00))
TCS_STOP_PCT        = float(getattr(config, "TCS_STOP_PCT_OF_CREDIT", 0.15))
TCS_NICKEL_REF      = float(getattr(config, "TCS_NICKEL_REF", 0.05))
TCS_NICKEL_MULT     = float(getattr(config, "TCS_MIN_CREDIT_NICKEL_MULT", 4.0))
# r112 — ACCEPT_FRESH_BARS IS GONE (operator's ruling, 2026-09-23: "the TCS
# freshness gate goes"). Its age is still RECORDED as accepted_age_bars with
# verdict None. The two jobs it was silently doing are now stated rules of their
# own: the breach's own bar must sit INSIDE this plan's window (the spec is
# "ACCEPTED after 11:30"), and an event that already existed when this process
# first looked is never fired (section 37: missed, not re-entered).


def window_end() -> tuple:
    """The TCS entry window's end, for main.py's remainder (HYG.5): read here,
    never from config, so the plan is the one owner of its window."""
    return tuple(TCS_ENTRY_END_ET)


from utils.time_utils import parse_hm as _hm      # r220 (TIME.1): the one parser


def _session_open_epoch() -> float:
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        n = datetime.now(ZoneInfo("America/New_York"))
        return n.replace(hour=9, minute=30, second=0, microsecond=0).timestamp()
    except Exception:                                           # noqa: BLE001
        return 0.0


class Candidate:
    __slots__ = ("level_id", "price", "kind", "provenance", "side", "short", "long", "credit",
                 "width", "r", "stop_dist", "pop", "richness", "long_leg_spread_pct", "why", "why_key",
                 "sv_ratio")                                   # r129

    def __init__(self, lvl):
        self.level_id, self.price = lvl["level_id"], float(lvl["price"])
        self.kind, self.provenance = lvl["kind"], lvl["provenance"]
        # a HIGH accepted -> sell the PUT spread behind it; a LOW -> the CALL spread
        self.side = "put" if self.kind == "resistance" else "call"
        self.short = self.long = None
        self.credit = self.width = self.r = self.stop_dist = self.pop = None
        self.richness = self.long_leg_spread_pct = None
        self.sv_ratio = None                          # r129 - stop / short bid-ask
        self.why = self.why_key = ""

    @property
    def sellable(self):
        return self.short is not None and self.long is not None and (self.credit or 0) > 0

    def line(self):
        if not self.sellable:
            return f"{self.provenance} {self.price:.2f}: {self.why or 'no structure'}"
        return (f"{self.provenance} {self.price:.2f} — would sell "
                f"{float(self.short.strike):g}/{float(self.long.strike):g}"
                f"{'P' if self.side == 'put' else 'C'} for {_n(self.credit)} "
                f"(R {_n(self.r)}, POP {_n(self.pop)}, {self.richness:.0%} of width)")


class TCSPreparation:
    __slots__ = ("tick", "em", "band_lo", "band_hi", "above", "below", "nearest_above",
                 "nearest_below", "accepted", "chosen", "side", "direction", "bound",
                 "short", "long", "credit", "width", "r", "stop_dist", "pop", "richness",
                 "ref_band", "outside_by", "structural", "starved", "unmet", "ready",
                 "tines")          # r33 — the fork, BESIDE the levels, never in them

    def __init__(self, tick):
        self.tick = tick
        self.em = self.band_lo = self.band_hi = None
        self.above, self.below = [], []
        self.nearest_above = self.nearest_below = None
        self.accepted = self.chosen = None
        self.side = self.direction = ""
        self.bound = None
        self.short = self.long = None
        self.credit = self.width = self.r = self.stop_dist = self.pop = self.richness = None
        self.ref_band = None
        self.outside_by = None
        self.structural, self.starved, self.unmet = [], [], []
        self.tines = []                     # r33 — "absent" is an answer, not a gap
        self.ready = False

    def trade_line(self):
        return self.chosen.line() if self.chosen else "no trade prepared"


class TCSPlan:
    name = "TrendCreditSpread"
    PLAN_CHECKS = ("entry_window", "price", "atm_iv", "em", "band_lo", "band_hi",
                   "extremes_above", "extremes_below", "rails_in_play",   # r104
                   "nearest_above", "nearest_above_credit",
                   "nearest_below", "nearest_below_credit", "adx", "accepted",
                   "accepted_age_bars", "ref_band_lo", "ref_band_hi", "outside_by",
                   "outside_em", "contract", "wing", "width", "credit", "credit_pct_width",
                   "r", "r_expiry", "wing_r_best", "stop_vs_spread", "stop_dist", "risk",
                   "pop", "nickel_floor", "richness", "long_leg_spread_pct", "fifty",
                   "fifty_accepted", "holds_fifty", "dist_from_fifty_pts")

    def __init__(self, store=None):
        self.planner = Plan(self.name, self.PLAN_CHECKS, record_only=True, self_ledgers=True)
        self._store = store
        self._prev_band = None            # (lo, hi) from the previous tick
        self._ref: dict = {}              # level_id -> frozen (lo, hi) at the first close beyond
        self._fired: set = set()          # (level_id, bar_ts) — each ACCEPTED fires once
        self._last_bar_ts = ""
        self._first_look_done = False     # r112 — §37: what existed at the first look is spent

    def _store_(self):
        if self._store is not None:
            return self._store
        try:
            from data.derived_store import get_derived_store
            return get_derived_store()
        except Exception:                                       # noqa: BLE001
            return None

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
            logger.warning("[tcs] level board unavailable — no levels in play: %s", exc)
            return {"state": "no_store", "above": [], "below": [], "tines": [], "fork": "absent"}

    def _structure(self, cand: Candidate, chain) -> Candidate:
        contracts = list(getattr(chain, "puts" if cand.side == "put" else "calls", None) or [])
        if not contracts:
            cand.why, cand.why_key = "no contracts on this side", "chain"
            return cand
        inc = float(getattr(config, "STRIKE_INCREMENT", 1) or 1)
        # anchor ON THE LEVEL: the first strike at/beyond it on the sell side
        k = strike_beyond_sweep(cand.price, cand.price, cand.side == "call", contracts=contracts, increment=inc)
        if k is None:
            cand.why, cand.why_key = "no listed strike at/beyond the level", "contract"
            return cand
        short = cv.find_contract_at_strike(contracts, k)
        if short is None:
            cand.why, cand.why_key = f"no contract at {k:g}", "contract"
            return cand
        cand.short = short
        cand.pop = round(1.0 - abs(float(getattr(short, "delta", 0) or 0)), 4)
        sb = safe_float(getattr(short, "bid", 0.0)) or 0.0
        sa = safe_float(getattr(short, "ask", 0.0)) or 0.0
        best, why = None, ""
        _spr = (sa - sb) if sa > sb else None       # r129 - the spread stop_survivable judges against
        _sv_fail = None                             # r129 - best ratio among the refused wings
        for c in contracts:
            kk = safe_float(getattr(c, "strike", 0)) or 0.0
            if kk <= 0 or (kk >= k if cand.side == "put" else kk <= k):
                continue
            ask = safe_float(getattr(c, "ask", None))
            if ask is None or ask < 0:
                continue
            width = abs(k - kk)
            credit = sb - ask                        # judged bid/ask (r219)
            if width <= 0 or credit <= 0 or credit >= width:
                continue
            r_expiry = credit / (width - credit)
            if r_expiry < TCS_R_FLOOR_EXPIRY:
                why = why or f"widest wing clearing 1:1 not found — best R {r_expiry:.2f} at {width:g} wide"
                continue
            sd = credit * TCS_STOP_PCT
            ok, svwhy = stop_survivable(sd, sb, sa)
            _ratio = round(sd / _spr, 4) if _spr else None
            if not ok:
                why = f"15%-of-credit stop is unsurvivable: {svwhy}"
                if _ratio is not None and (_sv_fail is None or _ratio > _sv_fail):
                    _sv_fail = _ratio
                continue
            if best is None or width > best[0]:      # WIDEST clearing 1R = the most credit
                best = (width, c, credit, r_expiry, sd, _ratio)
        if best is None:
            cand.why = why or f"no wing beyond {k:g} prices a credit"
            cand.why_key = "wing_r_best" if "1:1" in cand.why else "stop_vs_spread"
            if cand.why_key == "stop_vs_spread":
                cand.sv_ratio = _sv_fail
            return cand
        width, long_c, credit, r_expiry, sd, cand.sv_ratio = best
        cand.long, cand.credit, cand.width, cand.r, cand.stop_dist = long_c, round(credit, 4), width, round(r_expiry, 4), round(sd, 4)
        cand.richness = round(credit / width, 4) if width else None
        lb, la = safe_float(getattr(long_c, "bid", 0.0)) or 0.0, safe_float(getattr(long_c, "ask", 0.0)) or 0.0
        cand.long_leg_spread_pct = round((la - lb) / width, 4) if width else None
        return cand

    # ══════════════════════════════════════════════════════════════════════
    def prepare(self, *, price_now, now_et, atm_iv=None, chain=None, df_1m=None,
                adx=None, session_open_epoch: float = 0.0) -> TCSPreparation:
        t = self.planner.tick(price_now)
        prep = TCSPreparation(t)
        hm = _hm(now_et)
        # 🔴 r112 — §37 AT THE FIRST LOOK, BEFORE ANY WINDOW TEST. `_fired` lives
        # in memory, so after a restart the session's last ACCEPTED would fire
        # again. Whatever ACCEPTED already exists the first time this process
        # looks is marked spent: an interrupted firing sequence is MISSED, never
        # re-entered. The freshness gate used to do this job by accident.
        if not self._first_look_done:
            self._first_look_done = True
            try:
                _st0 = self._store_()
                _s0 = session_open_epoch or _session_open_epoch()       # CD.2: today's session, no fallback
                _prior = _st0.latest_event(_symbol_of(), "ACCEPTED", since_ts=_s0) if _st0 is not None else None
                if _prior:
                    self._fired.add((_prior["level_id"], _prior["bar_ts"]))
                    logger.info("[tcs] first look: %s ACCEPTED at %s predates this process — "
                                "MISSED, never re-entered (§37)", _prior["level_id"], _prior["bar_ts"])
            except Exception as exc:                            # noqa: BLE001
                logger.warning("[tcs] first-look read failed — no prior event marked: %s", exc)
        if hm is None:                                           # r220: a window that cannot be checked is not open
            t.dormant("entry_window", "the clock could not be read — no trade")
            return prep
        if hm is not None and hm >= tuple(TCS_ENTRY_END_ET):
            t.dormant("entry_window", f"past TCS_ENTRY_END_ET {TCS_ENTRY_END_ET[0]:02d}:{TCS_ENTRY_END_ET[1]:02d} — observing only")
            return prep
        if hm is not None and hm < tuple(TCS_START_ET):
            t.dormant("entry_window", f"before TCS_START_ET {TCS_START_ET[0]:02d}:{TCS_START_ET[1]:02d} — dormant, not looking at the chart")
            return prep
        t.check("entry_window", None, True)
        price_now = safe_float(price_now)
        if not price_now or price_now <= 0:
            prep.starved.append("price_now"); t.starved("price_now"); return prep
        t.check("price", price_now, True)
        t.check("adx", safe_float(adx), None)                    # recorded, never a bar (r9)

        # ── the EM band, every tick ────────────────────────────────────
        from strategy.gex_pin_butterfly import expected_move
        em = expected_move(price_now, atm_iv)
        t.check("atm_iv", safe_float(atm_iv), em is not None)
        if em is None:
            prep.starved.append("atm_iv"); t.starved("atm_iv"); return prep
        prep.em, prep.band_lo, prep.band_hi = em, round(price_now - em, 4), round(price_now + em, 4)
        t.check("em", round(em, 4), None)
        t.check("band_lo", prep.band_lo, None)
        t.check("band_hi", prep.band_hi, None)

        store = self._store_()
        if store is None:
            prep.starved.append("level_store"); t.starved("level_store"); return prep
        sym = _symbol_of()
        # r33 — THE ONE BOARD. This read was `live_levels()` filtered to
        # `provenance == "ny"` from r9 to r32, which is the r5 ruling broken in
        # both halves: not "3 named up, 3 named down" (it saw 3 of 11 held levels
        # on the box the day this was found) and not "plus the 1h pitchfork's
        # tines" (it has never had a fork). The session is a label on the answer,
        # not the query. The fork arrives BESIDE the levels and is never in them.
        _b = self._board_(price_now)
        t.check("level_board", _b.get("state"), None)
        t.check("fork", _b.get("fork"), None)
        levels = list(_b.get("above", [])) + list(_b.get("below", []))
        prep.tines = list(_b.get("tines", []))
        # r33 — THE FORK IS AN "OR" LEVEL, NOT AN "AND" (operator, 2026-09-17).
        # A rail is a level in its OWN right, not a confirmation stacked on a
        # historical one: an upper tine projected above spot IS a resistance, a
        # lower tine below spot IS a support. So the candidate set is the UNION,
        # and an absent fork means fewer candidates — never a blocked plan
        # ("a common informer but not mandatory if it's not there").
        # They arrive LABELLED (provenance `fork1h/*`) so nothing is conjoined:
        # the two products stay distinguishable on the row and in the journal.
        # 🔴 r104 — THE RAILS NO LONGER OUTRANK A HELD EXTREME. `levels = levels
        # + prep.tines` merged the two into ONE distance ranking, so a rail that
        # happened to sit nearer than a held session extreme became
        # `nearest_above`/`nearest_below` and the spread sold against it.
        # 🔑 THE OPERATOR'S RULING, 2026-09-22: *"It's just SEPARATE from held
        # levels with testing orders. It's SOFTER than held levels."* A held
        # extreme has resting stops beyond it; a sloped rail holds no pool.
        # Softer must not beat harder merely by being closer.
        # ⚠️ THE ORDERING KEY IS UNCHANGED AND SO IS THE SIDE BEHAVIOUR — still
        # ABSOLUTE distance, still NOT filtered by side of spot, because after
        # the move the accepted high is BELOW price and is exactly the level the
        # spread sells against. Only the RANK ORDER between the two kinds moves.
        # ⚠️ AND NOTHING IS WITHDRAWN: the rails remain candidates (r33 — "an OR
        # level not an AND"), they simply queue behind the held extremes.
        from derived.levels import rails_after_held as _raf
        _key = lambda l: abs(float(l["price"]) - price_now)      # noqa: E731
        _ha = [l for l in levels if l["kind"] == "resistance"]
        _hb = [l for l in levels if l["kind"] == "support"]
        _ra = [t for t in prep.tines if t["kind"] == "resistance"]
        _rb = [t for t in prep.tines if t["kind"] == "support"]
        above = _raf(_ha, _ra, _key)
        below = _raf(_hb, _rb, _key)
        # ⚠️ THE COUNTS NAME THE HELD SET, NOT THE TOTAL. One combined number
        # makes a board of three rails read identically to three held extremes,
        # which is the conflation r19 exists to prevent.
        t.check("extremes_above", len(_ha), None)
        t.check("extremes_below", len(_hb), None)
        t.check("rails_in_play", len(_ra) + len(_rb), None)
        if chain is None:
            prep.starved.append("chain"); t.starved("chain"); return prep
        prep.above = [self._structure(Candidate(l), chain) for l in above]
        prep.below = [self._structure(Candidate(l), chain) for l in below]
        na = next((c for c in prep.above if c.sellable), None) or (prep.above[0] if prep.above else None)
        nb = next((c for c in prep.below if c.sellable), None) or (prep.below[0] if prep.below else None)
        prep.nearest_above, prep.nearest_below = na, nb
        if na:
            t.check("nearest_above", na.price, None); t.check("nearest_above_credit", na.credit, None)
        if nb:
            t.check("nearest_below", nb.price, None); t.check("nearest_below_credit", nb.credit, None)

        # ── the reference band: frozen on the FIRST close beyond an extreme ──
        try:
            if df_1m is not None and len(df_1m) >= 2:
                bar_ts = str(df_1m.index[-2]); close = float(df_1m.iloc[-2]["close"])
                if bar_ts != self._last_bar_ts:
                    self._last_bar_ts = bar_ts
                    for l in levels:
                        lid, lp, kind = l["level_id"], float(l["price"]), l["kind"]
                        beyond = close > lp if kind == "resistance" else close < lp
                        if beyond and lid not in self._ref and self._prev_band is not None:
                            self._ref[lid] = self._prev_band       # the assessment BEFORE the move
                        elif not beyond and lid in self._ref:
                            self._ref.pop(lid, None)               # the move failed; next attempt refreezes
        except Exception as exc:                                # noqa: BLE001
            logger.debug("tcs ref band read failed: %s", exc)
        self._prev_band = (prep.band_lo, prep.band_hi)

        head = (f"EM ±{em:.2f} ({prep.band_lo:.2f}–{prep.band_hi:.2f}); "
                f"nearest above: {na.line() if na else 'none'}; nearest below: {nb.line() if nb else 'none'}")

        # ── the trigger: a fresh ACCEPTED on a live extreme, outside the frozen band ──
        since = session_open_epoch or _session_open_epoch()            # CD.2: today's session, no fallback
        acc = store.latest_event(sym, "ACCEPTED", since_ts=since)
        cand = None
        if acc:
            key = (acc["level_id"], acc["bar_ts"])
            age_bars = max(0.0, time.time() - float(acc["ts_epoch"] or 0)) / 60.0
            # r112 — the breach's OWN bar must be inside this plan's window: the
            # spec is "ACCEPTED after 11:30". A 10:11 breach is not an afternoon
            # move, and waking at 11:31 to sell against it is a chase (§37).
            _bhm = _hm(str(acc.get("bar_ts") or "")[11:16])
            in_window = (_bhm is not None and tuple(TCS_START_ET) <= _bhm < tuple(TCS_ENTRY_END_ET))
            t.check("accepted", acc["price"], key not in self._fired and in_window)
            t.check("accepted_age_bars", round(age_bars, 2), None)          # recorded, gates nothing (r112)
            if key not in self._fired and in_window:
                # 🔴 r112 — THE LEVEL COMES FROM THE EVENT. The engine retires a
                # breached level in the same step it publishes ACCEPTED, so the
                # board never holds the level this trigger names: the membership
                # test that stood here could never pass (0 of 110 trades on this
                # box, LVL.15). The board's candidate is used when it is still
                # there; otherwise the event's own price, side and identity build
                # it, and it is priced exactly the same way.
                cand = next((c for c in prep.above + prep.below if c.level_id == acc["level_id"]), None)
                if cand is None:
                    cand = self._structure(Candidate({"level_id": acc["level_id"], "price": acc["price"],
                                                      "kind": acc["kind"],
                                                      "provenance": acc.get("provenance") or "level"}), chain)
                prep.accepted = acc
        else:
            t.check("accepted", None, False)
        if cand is None:
            t.hold(f"{head}. Waiting on: a session extreme ACCEPTED outside the EM")
            return prep

        ref = self._ref.get(cand.level_id) or self._prev_band
        prep.ref_band = ref
        t.check("ref_band_lo", ref[0] if ref else None, None)
        t.check("ref_band_hi", ref[1] if ref else None, None)
        outside_by = (price_now - ref[1]) if cand.kind == "resistance" else (ref[0] - price_now)
        prep.outside_by = round(outside_by, 4)
        t.check("outside_by", prep.outside_by, outside_by > 0)
        t.check("outside_em", prep.outside_by, outside_by > 0)
        if outside_by <= 0:
            prep.unmet.append(("outside_em", f"{cand.provenance} {cand.price:.2f} accepted but price {price_now:.2f} "
                                             f"is INSIDE the reference band {ref[0]:.2f}–{ref[1]:.2f} by {-outside_by:.2f} "
                                             f"— not a move beyond the expected move"))
        prep.chosen, prep.side = cand, cand.side
        prep.direction = "long" if cand.side == "put" else "short"
        prep.bound = cand.price
        t.direction = prep.direction
        t.anchor(trigger=cand.price, invalidation=cand.price)
        if not cand.sellable:
            if cand.why_key == "stop_vs_spread":      # r129 - the ratio rides into t.refuse's row
                t.check("stop_vs_spread", cand.sv_ratio, False)
            prep.structural.append((cand.why_key or "contract", cand.why))
        else:
            t.check("contract", float(cand.short.strike), True)
            t.check("wing", float(cand.long.strike), True)
            t.check("width", cand.width, True)
            t.check("credit", cand.credit, True)
            cpw = cand.richness or 0.0
            t.check("credit_pct_width", cpw, cpw >= TCS_MIN_CREDIT_PCT)
            if cpw < TCS_MIN_CREDIT_PCT:
                prep.unmet.append(("credit_pct_width", f"credit {cpw:.0%} of width below the {TCS_MIN_CREDIT_PCT:.0%} floor — not rich"))
            t.check("r_expiry", cand.r, cand.r >= TCS_R_FLOOR_EXPIRY)
            t.check("wing_r_best", cand.r, True)
            t.check("r", cand.r, True)
            t.check("stop_dist", cand.stop_dist, None)
            t.check("stop_vs_spread", cand.sv_ratio, True)   # r129 - the RATIO, not dollars
            t.check("risk", round(cand.width - cand.credit, 4), None)
            t.check("pop", cand.pop, cand.pop >= TCS_MIN_POP)
            if cand.pop < TCS_MIN_POP:
                prep.unmet.append(("pop", f"POP {cand.pop:.2f} below {TCS_MIN_POP:.2f} — too near the money to be a theta trade"))
            nick = TCS_NICKEL_REF * TCS_NICKEL_MULT
            t.check("nickel_floor", cand.credit, cand.credit >= nick)
            if cand.credit < nick:
                prep.structural.append(("nickel_floor", f"credit ${cand.credit:.2f} below the nickel floor ${nick:.2f}"))
            t.check("richness", cand.richness, None)
            t.check("long_leg_spread_pct", cand.long_leg_spread_pct, None)
            prep.short, prep.long, prep.credit, prep.width = cand.short, cand.long, cand.credit, cand.width
            prep.r, prep.stop_dist, prep.pop, prep.richness = cand.r, cand.stop_dist, cand.pop, cand.richness
            t.credit_spread(cand.short.strike, cand.long.strike, cand.credit, invalidation=cand.price)
            # r12 — ANCHORS, record only: vanna at the accepted extreme, aggressor share through it
            from derived import anchors as _A
            _A.stamp(t, vanna_at_level=_A.vanna_at(cand.price), charm_at_short=_A.charm_at(cand.short.strike),
                     aggressor_at_level=_A.aggressor_share(cand.price), fork15=_A.fork_dir("15m"),
                     # r104 — THE RAIL PROJECTION, RECORDED. This plan knew a
                     # fork was "built" or "absent" and nothing more: not how
                     # far the nearest correctly-oriented rail sat, not its
                     # slope, not when it arrives. All three were computed on
                     # every tick and discarded here.
                     **_A.rail_context(price_now))
        if prep.starved:
            t.starved(*prep.starved); return prep
        if prep.structural:
            g, w = prep.structural[0]; t.refuse(g, f"{cand.provenance} {cand.price:.2f} ACCEPTED: {w}"); return prep
        if prep.unmet:
            g, w = prep.unmet[0]; t.refuse(g, f"{cand.provenance} {cand.price:.2f} ACCEPTED: {w}"); return prep
        self._fired.add((acc["level_id"], acc["bar_ts"]))
        prep.ready = True
        t.note(f"{cand.provenance} {cand.price:.2f} ACCEPTED, price {price_now:.2f} outside the EM by "
               f"{outside_by:.2f}: {cand.line()}")
        return prep
