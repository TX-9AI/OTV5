"""
strategy/runaway_plan.py  v1.8
v1.8 2026-10-18  OTV4TEST r289 (RUN.9, mirror of otv4 r492) — passes note= to gamma_leverage_pick and DECLINEs with its
     reason when the first OTM strike of the chain is not a candidate (no nearest-survivor fallback any more).
v1.7 2026-10-05  OTV4TEST r254 (OBS.1) — THE PLAN ALWAYS LOOKS, THE STRATEGY IS GATED ON THE HOUR: Breakout, Runaway and the Hunt are OBSERVED from their entry end to 15:40 - asked, recorded LOG-ONLY, never executed (the operator, 2026-10-05: "the plan always looks, but the strategies are gated on the hour of the day"; "Have those blocked TRADES just to Log only"). Here: past the cutoff the plan keeps looking only while observed.
v1.6  2026-10-03  OTV4TEST r220 (TIME.1) — its private HH:MM parser is utils.time_utils.parse_hm (eight plans carried the same copy), and an UNREADABLE clock is DORMANT - no trade - instead of skipping the window check.
v1.5  2026-10-03  OTV4TEST r193 (CFG.1) — its config dials are read as config.NAME with NO literal fallback; config v4.48 now defines them (they were getattr defaults on names config never had). Values unchanged.
v1.4  2026-10-03  OTV4TEST r189 (RUNW.1) — NAMES THE RUNAWAY END AT IMPORT. When OT_RUNAWAY_END is set it logs
      the end in force at INFO, and a value config REFUSED (malformed, or outside 09:36..15:40) at WARNING with
      the 10:30 it kept instead, so a box that meant 11:30 and typed 1130 is told, not silently held at 10:30.
      The window itself still comes only from config.ENTRY_WINDOWS (r148).
v1.3  2026-09-26  OTV4TEST r148 (WIN.1) — reads its entry window from config with NO literal fallback (one table, config.ENTRY_WINDOWS); a missing name now fails at import instead of silently defaulting. Value unchanged.
v1.2  2026-09-13  OTV4TEST r24 — THE RUNAWAY CANNOT ENTER BELOW ITS OWN 50, AND ITS BREAK
      STATE IS READ FROM THE BOOKS. (1) `runaway_confirmed` — last closed close
      AND live price beyond the 50 — existed with no caller; wired, so the
      session latch alone no longer admits a fill under the line (09-09 T2/T4/T5,
      09-11 T6). (2) the run is SIGNED, which revives the `run <= 0` guard `abs()`
      had disabled. (3) one-per-break and re-validation are derived every call
      from trades.db (`break_last_exit`) and the closed 1m bars since that exit;
      `_reval`/`_last_bar_ts` are gone, so a restart cannot re-open a spent
      break (09-09 11:28, four seconds after a bake). Fails closed on an
      unreadable book. check_runaway_plan R7/R8 re-derived, R14-R18 added.
v1.1  2026-09-09  OTV4TEST r12 — participation read from the prints at the boundary
      (record only; the composite is unchanged) and anchors stamped: charm/vanna at
      the target strike, 15m fork, VWAP distance.
v1.0  2026-09-08  OTV4TEST r3 — THE RUNAWAY PLAN (PLAN_SPEC §30), agreed with
      the operator 2026-09-08. The intent, his words: *"catch an early high
      velocity move from the market open where there's a lot of participation
      and a lot of volume and we just wanna participate in it and when it
      fizzles out … we want out of it."* Starting at the 50.

      ARM — the 50% level ACCEPTED: a 1m close beyond it that held. That is
      the engine's own latch (`orb.fifty_accepted`, r221), now also what
      invalidates the ORB (orb_engine v4.13) — one event, two consumers.
      Direction is the break's. A wick to the 50 arms nothing.

      MEASURE ONCE, AT ARM, AND FREEZE — the move from the boundary to the 50
      is a complete sample: `analysis.trend_strength.measure()` over the bars
      since the impulsive candle gives PACE (displacement per bar against true
      range — the bars-to-the-50 question, normalised) and ACCEPTANCE (where
      the closes sat in their bars). PARTICIPATION (aggressor share from the
      prints) is not wired here yet — recorded None, filed RUN.6 — so the
      composite is the mean of the two available components. Nothing gates on
      it: it is a DIAL.

      BAND FROM STRENGTH, GAMMA INSIDE IT — `gamma_leverage_pick` is unchanged
      and still runs on `run` (distance from the boundary); the plan hands it
      `run × band` where band is a declared prior: grind (< 0.40) 0.5 — nearer
      the money, pay for delta; normal 1.0 — today's rule; rip (≥ 0.70) 1.5 —
      cheaper, further out, gamma does the work. The teenie gate (a floor that
      does not clear its own spread is not a stop) still bounds the cheap end.
      ⚠️ The cutoffs and multipliers are CATEGORY 1 — a baseline so there is a
      starting point, not a fit. They are recorded on every row and fire.

      ONE PER BREAK, ANY EXIT — read from trades.db since r24 (was `FINISHED_BREAKS`, keyed on (direction,
      boundary) as at r174, but a WIN finishes the break too (trade_logger
      v4.9). RE-VALIDATION ON ACTUAL (operator): after any exit the standing
      state never re-fires; the plan watches the closed bars and re-opens the
      break only when the 50 was LOST on a close and then ACCEPTED again
      (close beyond, held). The r179 one-per-session cap is retired for this
      strategy: a new break is a new trade, as it is for the ORB.

      OUTSIDE 09:35–11:30 THE PLAN OBSERVES AND DOES NOT WRITE (dormant, one
      row on the transition). The feasibility floor (ATR) is KEPT by ruling.

      WHAT IT HANDS THE STRATEGY, ready before the fire: direction, the 50,
      the frozen strength vector and band, the contract, premium, floor, R
      (muteable through 09-11), run. The strategy's bars: 50 accepted, break
      not finished, ATR reachable, a contract, R (strict only). Zero of the
      selection lives in the strategy.
"""
from __future__ import annotations

import logging
from typing import Optional

import config
from strategy import observe as _observe   # r254 (OBS.1)
from strategy.plan import Plan, _n
from strategy.runaway_continuation import (
    ATR_FLOOR_PCT, CUTOFF_ET, _break_key, break_last_exit, gamma_leverage_pick,
    runaway_confirmed, target_delta,
)
from utils.math_utils import safe_float

logger = logging.getLogger(__name__)

# r189 (RUNW.1): say which end is in force when a box set one (WA 0.5).
if getattr(config, "RUNAWAY_END_ENV_REFUSED", ""):
    logger.warning("[runaway] OT_RUNAWAY_END=%r REFUSED (needs HH:MM between 09:36 and the entries stop); "
                   "Runaway's last entry stays before %s", config.RUNAWAY_END_ENV_REFUSED, config.RUNAWAY_CUTOFF_ET)
elif __import__("os").environ.get("OT_RUNAWAY_END", "").strip():
    logger.info("[runaway] OT_RUNAWAY_END in force: entries stop at %s", config.RUNAWAY_CUTOFF_ET)

# ── GATE CATEGORIES AS DATA (WA §36) — the plan's own values ────────────────
GATES = {
    "ATR_FLOOR_PCT": "FEASIBILITY",       # kept by ruling 2026-09-08 (the strategy's)
    "CUTOFF_ET":     "FOUNDATIONAL",      # never relaxed (r176)
    "BAND_GRIND":    "SELECTION",         # prior — a dial, gates nothing
    "BAND_RIP":      "SELECTION",
}

WINDOW_OPEN_ET   = config.ENTRY_OPEN_ET   # r148: no literal fallback
MAX_LOSS_PCT     = float(getattr(config, "RUNAWAY_MAX_LOSS_PCT", 0.20))
# the strength → band prior (category 1: a baseline, recorded, unfitted)
STRENGTH_GRIND   = float(config.RUNAWAY_STRENGTH_GRIND)
STRENGTH_RIP     = float(config.RUNAWAY_STRENGTH_RIP)
BAND_GRIND       = float(config.RUNAWAY_BAND_GRIND)
BAND_NORMAL      = 1.0
BAND_RIP         = float(config.RUNAWAY_BAND_RIP)
MEASURE_MIN_BARS = 2                      # a two-bar rip is a reading, not noise


def band_for(strength: Optional[float]) -> float:
    if strength is None:
        return BAND_NORMAL
    if strength < STRENGTH_GRIND:
        return BAND_GRIND
    if strength >= STRENGTH_RIP:
        return BAND_RIP
    return BAND_NORMAL


from utils.time_utils import parse_hm as _hm      # r220 (TIME.1): the one parser


def _cutoff_hm():
    try:
        h, m = str(CUTOFF_ET).split(":")[:2]
        return int(h), int(m)
    except (ValueError, AttributeError):
        return tuple(config.ENTRY_WINDOWS["RunawayContinuation"][1])   # r148: the table, not a literal


class RunawayPreparation:
    __slots__ = ("tick", "direction", "side", "boundary", "tp50", "run", "strength",
                 "pace", "acceptance", "participation", "band", "contract", "premium",
                 "floor_premium", "leverage", "considered", "r", "structural",
                 "starved", "unmet", "ready", "revalidation")

    def __init__(self, tick):
        self.tick = tick
        self.direction = self.side = ""
        self.boundary = self.tp50 = self.run = None
        self.strength = self.pace = self.acceptance = self.participation = None
        self.band = BAND_NORMAL
        self.contract = None
        self.premium = self.floor_premium = self.leverage = self.r = None
        self.considered = 0
        self.structural, self.starved, self.unmet = [], [], []
        self.ready = False
        self.revalidation = ""

    def trade_line(self) -> str:
        c = self.contract
        if c is None:
            return "no contract selected"
        return (f"buy {float(c.strike):g}{self.side[0].upper()} @ {_n(self.premium)}  "
                f"floor {_n(self.floor_premium)} (-{MAX_LOSS_PCT:.0%})  R {_n(self.r)}  "
                f"band {self.band:g}x run {_n(self.run)} "
                f"(strength {_n(self.strength)}: pace {_n(self.pace)}, "
                f"acceptance {_n(self.acceptance)})  50% {_n(self.tp50)}")


class RunawayPlan:
    name = "RunawayContinuation"
    PLAN_CHECKS = ("entry_window", "price", "atr_pct", "orb_direction", "fifty_accepted",
                   "break_finished", "revalidation", "run", "strength", "pace",
                   "acceptance", "participation", "band", "considered", "spread_rejected",
                   "contract", "leverage", "debit", "stop_premium", "target_distance", "r")

    def __init__(self):
        self.planner = Plan(self.name, self.PLAN_CHECKS,
                            record_only=True, self_ledgers=True)
        self._frozen: dict = {}        # break key -> {"strength","pace","acceptance","band"}
        # r24 — NO re-validation state lives here: it is read from trades.db and
        # the candles on every call (DEC.1). `_frozen` is keyed on the break AND
        # its last exit, so a re-validated new move is measured anew.

    # ── strength, measured once per break ───────────────────────────────
    def _measure(self, key, orb, df_1m, direction):
        if key in self._frozen:
            return self._frozen[key]
        out = {"strength": None, "pace": None, "acceptance": None, "band": BAND_NORMAL,
               "reason": ""}
        try:
            from analysis.trend_strength import measure
            k = int(getattr(orb, "bars_since_break", 0) or 0)
            if df_1m is None or len(df_1m) < MEASURE_MIN_BARS + 1:
                out["reason"] = "not enough bars"
            else:
                # the closed bars since the impulsive candle (k retest bars + the
                # candle); the frame may hold fewer — take what it has
                bars = df_1m.iloc[-(k + 2):-1] if len(df_1m) >= k + 2 else df_1m.iloc[:-1]
                ts = measure(bars, direction, min_bars=MEASURE_MIN_BARS)
                out["pace"] = getattr(ts, "pace", None)
                out["acceptance"] = getattr(ts, "acceptance", None)
                comps = [v for v in (out["pace"], out["acceptance"]) if v is not None]
                out["strength"] = round(sum(comps) / len(comps), 4) if comps else None
                out["reason"] = str(getattr(ts, "reason", "") or "")
        except Exception as exc:                                # noqa: BLE001
            out["reason"] = f"measure failed: {exc}"
        out["band"] = band_for(out["strength"])
        self._frozen[key] = out
        logger.info("[runaway-plan] strength FROZEN for %s: %s -> band %.1fx (%s)",
                    key, out["strength"], out["band"], out["reason"] or "ok")
        return out

    # ── re-validation on actual, after any exit ─────────────────────────
    def _revalidate(self, key, tp50, direction, df_1m, last=None) -> str:
        """"" when the break may trade, else the reason it may not.

        🔴 r24 — DERIVED FROM THE BOOKS ON EVERY CALL, NOTHING REMEMBERED.
        `last` is `break_last_exit()`'s answer from trades.db. The re-validation
        walk runs over the CLOSED 1m bars since that exit: the 50 must be LOST on
        a close, then two consecutive closes beyond it (a close back inside
        resets the pair). The old version counted in a dict that a restart
        emptied — and "not in the set" meant "may trade".
        """
        if last is None:
            return ""
        if last == "unreadable":
            return ("the trade book is unreadable — this break cannot be proven "
                    "untraded, so it does not trade (fails closed)")
        if last == "open":
            return "a runaway on this break is still open"
        try:
            if df_1m is None or len(df_1m) < 2:
                return "break finished — waiting for the 50 to be lost and re-accepted (no bars)"
            import pandas as pd
            closed = df_1m.iloc[:-1]
            cut = pd.Timestamp(float(last), unit="s", tz="UTC")
            idx = closed.index
            if getattr(idx, "tz", None) is None:
                cut = cut.tz_convert("America/New_York").tz_localize(None)
            else:
                cut = cut.tz_convert(idx.tz)
            closes = [float(c) for c in closed[idx >= cut]["close"]]
            lost, pair = False, 0
            for c in closes:
                beyond = c > tp50 if direction == "long" else c < tp50
                if not lost:
                    lost = not beyond
                    continue
                if beyond:
                    pair += 1
                    if pair >= 2:
                        return ""
                else:
                    pair = 0
            if not lost:
                return ("break finished — the 50 must be LOST on a close, then accepted "
                        "again")
            if pair:
                return "the 50 re-crossed on a close — pending the hold"
            return "the 50 was lost on a close — waiting for a fresh acceptance"
        except Exception as exc:                                # noqa: BLE001
            return f"re-validation unreadable: {exc}"

    # ══════════════════════════════════════════════════════════════════════
    def prepare(self, *, orb, atr_pct, price_now, now_et, chain=None,
                df_1m=None, participation=None) -> RunawayPreparation:
        t = self.planner.tick(price_now)
        prep = RunawayPreparation(t)

        # window — outside it, observe only (one dormant row on the transition)
        hm = _hm(now_et)
        if hm is None:                                           # r220: a window that cannot be checked is not open
            t.dormant("entry_window", "the clock could not be read — no trade")
            return prep
        # r254 (OBS.1) - observed past the end: the plan keeps looking, nothing it fires executes.
        _obs = bool(hm is not None and hm >= _cutoff_hm() and _observe.is_active("RunawayContinuation"))
        if hm is not None and hm >= _cutoff_hm() and not _obs:
            t.dormant("entry_window", f"past the {CUTOFF_ET} ET debit cutoff — observing only")
            return prep
        if _obs:
            t.note(f"LOG-ONLY - past the {CUTOFF_ET} ET entry end: observed, recorded, never executed (OBS.1)")
        if hm is not None and hm < tuple(WINDOW_OPEN_ET):
            t.dormant("entry_window", f"before {WINDOW_OPEN_ET[0]:02d}:{WINDOW_OPEN_ET[1]:02d} "
                                      f"ET — the opening range is forming; observing only")
            return prep
        t.check("entry_window", None, True)

        price_now = safe_float(price_now)
        if not price_now or price_now <= 0 or price_now > 1e7:
            prep.starved.append("price_now")
            t.starved("price_now")
            return prep
        t.check("price", price_now, True)

        # feasibility — kept by ruling
        _atr = safe_float(atr_pct)
        reachable = target_delta(atr_pct) is not None
        t.check("atr_pct", _atr, reachable)
        if not reachable:
            prep.unmet.append(("atr_pct", f"ATR {_n(_atr, '.3f')}% below the "
                                          f"{ATR_FLOOR_PCT}% reachability floor"))

        # direction: the break's
        state = str(getattr(orb, "state", "") or "").upper()
        bd = str(getattr(orb, "break_direction", "") or "").lower()
        inval = str(getattr(orb, "invalidation_reason", "") or "")
        direction = ("long" if "LONG" in state else "short" if "SHORT" in state
                     else bd if (inval == "runaway" and bd in ("long", "short")) else "")
        t.check("orb_direction", (1.0 if direction == "long" else -1.0) if direction else None,
                bool(direction))
        if not direction:
            t.hold(f"ORB {state.lower() or 'none'}"
                   + (f" (invalidated: {inval})" if inval else "")
                   + " carries no direction — nothing to prepare until it breaks")
            return prep
        prep.direction, prep.side = direction, "call" if direction == "long" else "put"
        t.direction = direction
        tp50 = safe_float(getattr(orb, "target_50pct", None))
        boundary = safe_float(getattr(orb, "orb_high", None) if direction == "long"
                              else getattr(orb, "orb_low", None))
        if not tp50 or not boundary:
            miss = [n for n, v in (("target_50pct", tp50), ("orb_boundary", boundary)) if not v]
            prep.starved.extend(miss)
            t.starved(*miss)
            return prep
        prep.tp50, prep.boundary = float(tp50), float(boundary)
        t.anchor(trigger=prep.tp50)
        key = _break_key(direction, prep.boundary)

        # one per break, any exit — and re-validation on actual, both READ from
        # trades.db and the candles (r24, DEC.1)
        _sess = None
        try:
            _ix = df_1m.index[-1] if df_1m is not None and len(df_1m) else None
            _sess = _ix.date() if _ix is not None and hasattr(_ix, "date") else None
        except Exception:                                       # noqa: BLE001
            _sess = None
        last = break_last_exit(direction, prep.boundary, _sess)
        why_not = self._revalidate(key, prep.tp50, direction, df_1m, last)
        t.check("break_finished", prep.boundary, not why_not)
        if why_not:
            prep.revalidation = why_not
            t.check("revalidation", None, False)
            t.hold(f"ORB broke {direction} at {prep.boundary:.2f}: {why_not}")
            return prep
        t.check("revalidation", None, True)

        # the trigger: the 50 ACCEPTED (close + hold) — the engine's latch
        accepted = bool(getattr(orb, "fifty_accepted", False))
        t.check("fifty_accepted", prep.tp50, accepted)
        # 🔴 r24 — THE RUN HAS A SIGN. `abs()` counted a move AGAINST the break as a
        # run: 2026-09-09 11:28, a LONG at 714.71 read "run 2.70" off a 717.41
        # boundary, R 9.97 — and it disabled the `run <= 0` guard below, the one
        # line written to refuse a price inside the boundary.
        run = (price_now - prep.boundary) if direction == "long" else (prep.boundary - price_now)
        prep.run = run
        t.check("run", run, run > 0)
        head = (f"ORB broke {direction} at {prep.boundary:.2f}, run {_n(run)} to "
                f"{price_now:.2f}, 50% {prep.tp50:.2f}")
        if not accepted:
            beyond_now = price_now > prep.tp50 if direction == "long" else price_now < prep.tp50
            t.hold(f"{head}: waiting on: the 50 ACCEPTED (a 1m close beyond, held)"
                   f"{' — price is beyond it now, pending the close' if beyond_now else ''}")
            return prep

        # 🔴 r24 — THE 50 MUST BE HELD *NOW*, NOT ONLY LATCHED. `fifty_accepted` is
        # a session latch; three of 2026-09-09's four runaway longs and 09-11's
        # 10:00 long filled UNDER their own 50 on it. `runaway_confirmed` — the
        # last closed 1m close AND the live price beyond the 50 — existed in
        # runaway_continuation and had NO CALLER. Wired here.
        _prev = None
        try:
            if df_1m is not None and len(df_1m) >= 2:
                _prev = float(df_1m.iloc[-2]["close"])
        except Exception:                                       # noqa: BLE001
            _prev = None
        held = runaway_confirmed(orb, price_now, _prev, direction)
        t.check("fifty_held_now", prep.tp50, held)
        if not held:
            t.hold(f"{head}: the 50 is accepted on the latch but NOT held now (last close "
                   f"{_n(_prev)}, price {price_now:.2f}) — no entry on the wrong side of the 50")
            return prep

        # strength, measured once per move and frozen; the band follows it
        m = self._measure((key, last if isinstance(last, float) else None), orb, df_1m, direction)
        prep.strength, prep.pace, prep.acceptance = m["strength"], m["pace"], m["acceptance"]
        # r12 — participation READ from the prints at the boundary (RUN.6, record only
        # this revision: the composite still uses pace + acceptance)
        from derived import anchors as _A
        if participation is None:
            participation = _A.aggressor_share(prep.boundary)
        prep.participation = participation
        prep.band = m["band"]
        t.check("strength", prep.strength, None)
        t.check("pace", prep.pace, None)
        t.check("acceptance", prep.acceptance, None)
        t.check("participation", participation, None)
        t.check("band", prep.band, None)

        if run <= 0:
            prep.structural.append(("run", f"price {price_now:.2f} is at/inside the ORB "
                                           f"boundary {prep.boundary:.2f} — no run to lever"))
        elif chain is None:
            prep.starved.append("chain")
        else:
            contracts = chain.calls if prep.side == "call" else chain.puts
            why_none: list = []
            c, lev, n, spread_rej = gamma_leverage_pick(
                contracts, direction, price_now, run * prep.band, floor_pct=MAX_LOSS_PCT,
                note=why_none)
            t.check("considered", n, n > 0)
            t.check("spread_rejected", spread_rej, None)
            if c is None and why_none:                     # r289 / RUN.9 (mirror of r492)
                prep.structural.append(("contract", f"{prep.side}: {why_none[0]}"))
            elif c is None:
                prep.structural.append(("contract",
                    f"no {prep.side} whose {MAX_LOSS_PCT:.0%} floor clears its own bid/ask "
                    f"spread ({spread_rej} rejected) inside a {prep.band:g}x band on a "
                    f"{run:.2f} run"))
            else:
                prem = float(getattr(c, "ask", 0) or getattr(c, "mark", 0) or 0)
                d_ = abs(float(getattr(c, "delta", 0) or 0))
                g_ = float(getattr(c, "gamma", 0) or 0)
                gain = d_ * run + 0.5 * g_ * run * run
                risk = prem * MAX_LOSS_PCT
                t.debit = prem
                t.reward, t.risk = round(gain, 4), round(risk, 4)
                t.r = round(gain / risk, 4) if risk > 0 else None
                t.check("contract", c.strike, True)
                t.check("leverage", lev, lev > 0)
                t.check("debit", prem, True)
                t.check("stop_premium", round(prem * (1 - MAX_LOSS_PCT), 4), None)
                t.check("target_distance", run, run > 0)
                t.check("r", t.r, None)
                ok, why = t.executable()          # strict vetoes R; relaxed records
                if not ok:
                    prep.structural.append(("r", why))
                else:
                    prep.contract, prep.premium, prep.leverage = c, prem, lev
                    prep.floor_premium = round(prem * (1 - MAX_LOSS_PCT), 4)
                    prep.considered, prep.r = n, t.r
                    t.note(why)

        # r12 — ANCHORS, record only: dealer flow at the target strike, the 15m fork
        _k = float(getattr(prep.contract, "strike", 0) or 0) if prep.contract is not None else None
        _A.stamp(t, charm_at_strike=_A.charm_at(_k), vanna_at_strike=_A.vanna_at(_k),
                 fork15=_A.fork_dir("15m"), vwap_minus_price=(lambda v: None if v is None else v - price_now)(_A.vwap()))
        if prep.starved:
            t.starved(*prep.starved)
            return prep
        if prep.structural:
            gate, why = prep.structural[0]
            t.refuse(gate, f"{head}: {why}")
            return prep
        if prep.unmet:
            gate, why = prep.unmet[0]
            t.refuse(gate, f"{head}: {why}")
            return prep
        prep.ready = True
        t.note(f"{head}: 50 ACCEPTED — {prep.trade_line()}")
        return prep
