"""
strategy/atp_butterfly_plan.py  v1.5
v1.5  2026-10-19  OTV4TEST r303 (PSTATE.1) — the `enabled` condition is met when the plan is ACTIVE (ENABLED, as before)
      or switched to LOG (OT_ATP_BUTTERFLY=log): LOG reaches take(), which records LOG-ONLY. DORMANT is never asked.
v1.4  2026-10-03  OTV4TEST r225 (FLY.2) — records the same three leg-quote facts as the pin butterfly on the wings it picks (gex_pin_butterfly.leg_quote_facts). Log-only.
v1.3  2026-09-30  OTV4TEST r179 (BFLY.9) — THE ATP FLY'S OWN PIN-CONCENTRATION FLOOR, 0.15.
      The operator, 2026-09-30, reading the ATP fly HOLD all afternoon on a PINNING tape at the pin: "The ATP fly should be accepting the plan for the EXACT reason GEX pin fly is declining (price too close to pin)", then "Drop the ATP to .19" and, minutes later, "Actually .15 sounds better".
      MEASURED that day: PINNING at 745, spot 0.5-1.5 off the pin, a 743/745/747 fly PREPARED at
      about 0.40 for R 4.0, and all 148 ticks from 12:00 to 12:40 ET waiting on this one condition
      (concentration 0.18-0.20 against the shared 0.25; the pin 2.0 from VWAP, so no waiver). The
      regime needs only 0.15 to read PINNING, so between 0.15 and 0.25 the pin fly declined for
      being too close and this fly declined for a weak pin. `PIN_CONC_MIN` here reads
      config.ATP_BFLY_PIN_CONC_MIN. ROUTE B, ruled the same afternoon: The operator, 2026-09-30: "Allow a non-pinning ATP if it qualifies on STRICT VWAP & NOT TRENDING", "Route B for VWAP if A fails", and yes to NEUTRAL and to ±0.05 x EM.
      So the fly qualifies on ROUTE A - PINNING and concentration >= 0.15 - or, only when A
      fails, on ROUTE B - a regime that is NOT TRENDING (PINNING or NEUTRAL, never unknown) with
      the pin within ±0.05 x EM of today's VWAP, read through anchors.vwap_now(), which fails
      closed on a missing or stale VWAP. This fly no longer calls the shared `pin_strength()`
      (whose waiver band is 0.10 x EM); the pin fly still does and is unchanged. The route that
      admitted a fly is named in its plan row and noted on the tick.
v1.2  2026-09-30  OTV4TEST r178 (CAP.2) — COMMENT ONLY. The header below said the
      once-per-session cap counts BOTH butterflies; that stopped being true at r85
      (2026-09-21: each butterfly has its OWN session quota - both fired on 09-22),
      and the stale line was quoted to the operator as fact on 2026-09-30. Corrected.
      Also recorded: both butterflies are exempt from the daily catastrophic loss
      cap (position_manager v5.9, main v4.78). No code changes here.
v1.1  2026-09-17  OTV4TEST r31 (BFLY.7) — the pinning REGIME stamped on the row,
      record-only and at ZERO WEIGHT, the same `derived/gamma_regime.read()` the
      travel fly stamps, so the two butterflies cannot disagree about the regime any
      more than they can about pin strength (v1.0 shares `pin_strength`). Concentration
      says WHERE gamma is; this says whether the pinning regime exists at all — on
      2026-09-16 the two disagreed for six hours. `GAMMA_RAMP_WEIGHT` is 0.0, so
      nothing here is sized by it (§31); see BFLY.8 for why it stays that way.
v1.0  2026-09-14  OTV4TEST r26 — THE ATP BUTTERFLY'S PLAN (PLAN_SPEC §39, BFLY.6).
      Operator, 2026-09-13: *"that is a different trade. Code it and allow one
      butterfly or the other, whichever plan produces a viable trade 1st can take
      it. Call it something different, because traveling to the pin is a
      different thesis than building it on an already sideways tape."* — and he
      named it the ATP (at-the-pin) butterfly.

      THE THESIS. GEXPinButterfly buys a fly for price to TRAVEL to a pin 0.30-1.00
      of the expected move away, with its wings never crossing spot. The ATP fly
      is built where that trade refuses to: price is ALREADY AT the pin and the
      tape has been sitting there. On Friday 09-11 the travel fly refused 696
      ticks because price was too close to the pin for any wing — the tape this
      trade exists for.

      THE CONDITIONS (the priors are declared in config and recorded every tick):
        entry_window       the butterfly slot, shared with GEXPinButterfly
        enabled            ATP_BUTTERFLY_ENABLED
        pinning            GEX environment PINNING with a pin strike
        pin_concentration  `gex_pin_butterfly.pin_strength` — the SAME function the
                           travel fly uses, with THIS fly's own floor since r179:
                           conc >= 0.15 (the travel fly's is 0.25), or the pin
                           within ±0.10 x EM of today's VWAP (r25)
        expected_move      from the chain's ATM IV, no fallback
        at_pin             |price - pin| <= ATP_BFLY_AT_PIN_EM_FRAC x EM ⟨PRIOR 0.30⟩
                           — the exact complement of the travel fly's reach, so on
                           any one tick at most one of the two can be viable
        settled            the last ATP_BFLY_SETTLED_BARS ⟨PRIOR 15⟩ CLOSED 1m bars
                           all closed inside that band — "an already sideways
                           tape", READ FROM THE CANDLES (DEC.1), never counted in
                           memory. The value is how many consecutive closed bars
                           back from now are inside, so a HOLD says how far along
      ⚠️ NO TICK-PERSISTENCE COUNTER AND NO PLAYED-PIN SET. The travel fly's
      `_persist` and `PLAYED_PINS` live in process memory (DEC.1 debt, recorded);
      this plan's persistence is the settled-bars read, and its once-per-session is
      main.py's trades.db cap - ONE ATP fly per session, counted on its own name
      (r85; the pin fly has its own quota, and both may fire on one day).

      THE STRUCTURE. Both sides priced (at the pin neither is "the OTM side"); every
      symmetric wing from the LISTED strikes, apex exactly on the pin; a wing must
      put spot INSIDE the tent (width > |price - pin|); R >= R_FLOOR; the stop at
      BUTTERFLY_STOP_LOSS_PCT must clear the fly's own three-leg spread by
      STOP_VS_SPREAD_MIN. The pick is the MAX R (the r6 ruling for butterflies).

      MEASURED BEFORE BUILDING (this box, 12:00-15:00): Wed 09-09 and Thu 09-10 —
      no qualifying minute (GEX read TRENDING); Fri 09-11 — 36 qualifying minutes,
      first 12:28 (pin 715, spot 716.01, EM 5.21, conc 0.26). On Friday's real 12:28
      quotes the search takes the 713/715/717 PUT fly: debit 0.56, R 2.57, stop 0.224
      = 5.6x its 0.04 spread (the 1-wide leaves spot outside the tent; the 713/715/717
      CALL fly fails at 1.6x). Its worst mid to the flatten was 0.38 at 13:25 against
      a 0.336 stop — it survives by four cents — and it was worth 1.135 at 15:44.
      One day is a mechanism, not a rule.
"""
from __future__ import annotations

import logging
from typing import Optional

import config
from strategy import gex_pin_butterfly as _gpb
from strategy.criteria import stop_survivable, R_FLOOR, STOP_VS_SPREAD_MIN
from strategy.plan import Plan
from utils.math_utils import safe_float

logger = logging.getLogger(__name__)

NAME = "ATPButterfly"
ENABLED = bool(getattr(config, "ATP_BUTTERFLY_ENABLED", True))
AT_PIN_EM_FRAC = float(getattr(config, "ATP_BFLY_AT_PIN_EM_FRAC", 0.30))     # ⟨PRIOR⟩
SETTLED_BARS = int(getattr(config, "ATP_BFLY_SETTLED_BARS", 15))            # ⟨PRIOR⟩
# r179 (BFLY.9): this fly's own floor. Falls back to the pin fly's if the key is absent.
PIN_CONC_MIN = float(getattr(config, "ATP_BFLY_PIN_CONC_MIN", _gpb.PIN_CONC_MIN))
# r179 (BFLY.9): route B's strict VWAP band, as a fraction of EM.
VWAP_STRICT_EM_FRAC = float(getattr(config, "ATP_BFLY_VWAP_STRICT_EM_FRAC", 0.05))

# WA 36 — every gate named with its category. NOTHING here is relaxable: the two
# priors ARE the thesis ("at the pin", "an already sideways tape"), so a relaxed
# version is a different trade, not a worse example of this one. The shared
# pin-strength floor and the slot are §32's, declared in gex_pin_butterfly's GATES.
GATES = {
    "AT_PIN_EM_FRAC": "FOUNDATIONAL",   # ⟨PRIOR 0.30⟩ the complement of §32's reach
    "SETTLED_BARS":   "FOUNDATIONAL",   # ⟨PRIOR 15⟩ the settled-tape bar
    "PIN_CONC_MIN":   "FOUNDATIONAL",   # 0.15 by ruling (r179); the pin fly's is 0.25
    "VWAP_STRICT_EM_FRAC": "FOUNDATIONAL",   # 0.05 by ruling (r179): route B, only when A fails
}


def _nr(v):
    return "n/a" if v is None else f"{v:.2f}"


def settled_run(df_1m, pin: float, band: float) -> Optional[int]:
    """Consecutive CLOSED 1m bars, counting back from now, that closed within ±band
    of the pin. None when there are no closed bars to read (the forming bar, the
    last row, is never counted)."""
    try:
        if df_1m is None or len(df_1m) < 2:
            return None
        closes = [float(c) for c in df_1m["close"].iloc[:-1]]
    except Exception:                                           # noqa: BLE001
        return None
    n = 0
    for c in reversed(closes):
        if abs(c - pin) > band:
            break
        n += 1
    return n


class ATPPreparation:
    """What the plan hands the strategy each tick of the slot — never executable."""
    __slots__ = ("tick", "pin", "side", "conc", "em", "dist", "settled", "wing",
                 "lower", "center", "upper", "debit", "width", "r", "ratio",
                 "conditions", "unmet", "structural", "starved", "ready", "vwap_waiver", "route")

    def __init__(self, tick):
        self.tick = tick
        self.pin = self.conc = self.em = self.dist = self.wing = 0.0
        self.settled = None
        self.side = ""
        self.lower = self.center = self.upper = None
        self.debit = self.width = self.r = self.ratio = None
        self.conditions, self.unmet, self.structural, self.starved = {}, [], [], []
        self.ready = False
        self.vwap_waiver = ""
        self.route = ""                   # r179: "A", "B" or "" (not qualified)

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
                f"R {self.r:.2f} (min {R_FLOOR:.2f})")


class ATPButterflyPlan:
    CONDITIONS = {
        "entry_window":      "the butterfly slot (shared with GEXPinButterfly)",
        "enabled":           "ATP_BUTTERFLY_ENABLED is on",
        "pinning":           "a pin strike and a regime that is NOT TRENDING (PINNING, or NEUTRAL for route B)",
        "pin_concentration": (f"route A: PINNING and conc >= {PIN_CONC_MIN:.2f}; or, only when A fails, route B: "
                              f"the pin within ±{VWAP_STRICT_EM_FRAC:.2f}x EM of today's VWAP"),
        "expected_move":     "an expected move from the chain's ATM IV (no fallback)",
        "at_pin":            f"price within {AT_PIN_EM_FRAC:.2f}x EM of the pin",
        "settled":           f"the last {SETTLED_BARS} closed 1m bars all closed within that band",
    }
    STRUCTURAL = ("legs", "wing_search")
    PLAN_CHECKS = tuple(CONDITIONS) + STRUCTURAL + (
        "gex", "open_interest", "pin_vwap_dist", "wing_candidates", "r",
        "stop_vs_spread", "width", "debit",
        "quote_wings_no_bid", "quote_strict_would_refuse", "quote_role_would_refuse")

    def __init__(self):
        self.planner = Plan(NAME, self.PLAN_CHECKS)

    def prepare(self, *, gex, price_now, now_et, atm_iv=None, chain=None, df_1m=None,
                **_ignored) -> ATPPreparation:
        t = self.planner.tick(price_now)
        prep = ATPPreparation(t)
        _early, _late = _gpb.EARLIEST_ET, _gpb.LATEST_ET
        if now_et and not (_early <= now_et <= _late):
            t.dormant("entry_window", f"outside the butterfly slot {_early}-{_late}")
            return prep
        prep.cond("entry_window", None, self.CONDITIONS["entry_window"], True)
        from strategy import plan_state as _ps                  # r303: LOG is "enabled" too (recorded only)
        _on = bool(ENABLED) or _ps.is_log("ATPButterfly")
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
        # The same park as the travel fly (§32.2): GEX with no open interest is
        # gamma-squared, and its "pin" sits at spot — which is exactly where this
        # trade looks, so for THIS trade the park matters more, not less.
        _oi_sum = 0
        try:
            for _c in (list(getattr(chain, "calls", []) or []) + list(getattr(chain, "puts", []) or [])):
                _oi_sum += int(getattr(_c, "open_interest", 0) or 0)
        except Exception:                                       # noqa: BLE001
            _oi_sum = 0
        t.check("open_interest", float(_oi_sum), _oi_sum > 0)
        if chain is not None and _oi_sum <= 0:
            prep.starved.append("open_interest")
            t.starved("open_interest")
            return prep

        env = str(getattr(gex, "gex_environment", "") or "")
        conc = float(getattr(gex, "pin_concentration", 0.0) or 0.0)
        pin = float(getattr(gex, "pin_strike", 0.0) or 0.0)
        prep.pin, prep.conc = pin, conc
        # r179 (BFLY.9): NOT TRENDING, never an unknown regime (fails closed).
        prep.cond("pinning", pin or None,
                  f"a pin and a regime that is NOT TRENDING (now {env or 'unknown'})",
                  pin > 0 and env in ("PINNING", "NEUTRAL"))
        em = _gpb.expected_move(price_now, atm_iv)
        prep.em = em or 0.0
        # r179 (BFLY.9): ROUTE A, or ROUTE B only when A fails.
        _vw, _vw_why = None, "not read"
        try:
            from derived import anchors as _A0
            _vw, _vw_why = _A0.vwap_now()
        except Exception as _e:                     # noqa: BLE001
            _vw, _vw_why = None, f"VWAP read failed: {_e}"
        _band = VWAP_STRICT_EM_FRAC * em if (em and em > 0) else None
        _vdist = abs(pin - _vw) if (_vw is not None and pin > 0) else None
        t.check("pin_vwap_dist", _vdist,
                None if (_vdist is None or _band is None) else _vdist <= _band)
        _route_a = env == "PINNING" and pin > 0 and conc >= PIN_CONC_MIN
        _route_b = (not _route_a and env in ("PINNING", "NEUTRAL") and pin > 0
                    and _vdist is not None and _band is not None and _vdist <= _band)
        prep.route = "A" if _route_a else ("B" if _route_b else "")
        _met = _route_a or _route_b
        _need = (f"route A: PINNING and conc >= {PIN_CONC_MIN:.2f}; route B: pin within "
                 + (f"±{_band:.2f} ({VWAP_STRICT_EM_FRAC:.2f}x EM) of VWAP" if _band is not None
                    else f"{VWAP_STRICT_EM_FRAC:.2f}x EM of VWAP (no EM)")
                 + (f" (now {_vdist:.2f} off)" if _vdist is not None else f" (no VWAP: {_vw_why})"))
        if _route_b:
            prep.vwap_waiver = (f"ROUTE B (strict VWAP): regime {env}, conc {conc:.2f}, pin {pin:g} is "
                                f"{_vdist:.2f} from VWAP {_vw:.2f} (band ±{_band:.2f})")
            t.note(prep.vwap_waiver)
        try:            # r31 (BFLY.7) — the pinning REGIME, record only, zero weight
            from derived import anchors as _A
            from derived import gamma_regime as _G
            _A.stamp(t, **_G.read())
        except Exception:                           # noqa: BLE001
            pass
        prep.cond("pin_concentration", conc, _need, _met)
        prep.cond("expected_move", em or None, self.CONDITIONS["expected_move"], bool(em and em > 0))

        if pin > 0 and em and em > 0:
            band = AT_PIN_EM_FRAC * em
            prep.dist = abs(price_now - pin)
            prep.cond("at_pin", prep.dist, f"<= {band:.2f} ({AT_PIN_EM_FRAC:.2f}x EM {em:.2f})",
                      prep.dist <= band)
            prep.settled = settled_run(df_1m, pin, band)
            prep.cond("settled", None if prep.settled is None else float(prep.settled),
                      f">= {SETTLED_BARS} closed 1m bars within ±{band:.2f} of the pin"
                      + ("" if prep.settled is not None else " (no closed bars to read)"),
                      prep.settled is not None and prep.settled >= SETTLED_BARS)
            t.anchor(trigger=pin)
            if chain is None:
                prep.starved.append("chain")
            else:
                self._search(t, prep, chain, pin, price_now)
        else:
            prep.cond("at_pin", None, self.CONDITIONS["at_pin"], False)
            prep.cond("settled", None, self.CONDITIONS["settled"], False)

        head = (f"pin {pin:g} ({env or 'no env'}, conc {conc:.2f}, spot {price_now:.2f} is "
                f"{prep.dist:.2f} off, EM {prep.em:.2f}"
                + (f", route {prep.route}" if prep.route else "") + ")")
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

    # ── the structure: both sides, symmetric listed wings, spot inside the tent ──
    def _search(self, t, prep, chain, pin, price_now):
        stop_pct = float(getattr(config, "BUTTERFLY_STOP_LOSS_PCT", 0.40))
        cands, rej_tent, rej_r, rej_surv = [], 0, 0, 0
        best_r = best_ratio = None
        centers = 0
        for side in ("put", "call"):
            contracts = list((chain.puts if side == "put" else chain.calls) or [])

            def _exact(k, _cs=contracts):
                for c in _cs:
                    try:
                        if abs(float(c.strike) - k) < 1e-9 and float(c.mark or 0) > 0:
                            return c
                    except (TypeError, ValueError, AttributeError):
                        continue
                return None

            center = _exact(pin)
            if center is None:
                continue
            centers += 1
            wings = sorted({round(float(c.strike) - pin, 4) for c in contracts
                            if float(getattr(c, "strike", 0) or 0) > pin})
            for w in wings:
                lo, up = _exact(pin - w), _exact(pin + w)
                if lo is None or up is None:
                    continue                       # asymmetric ladder — not a fly
                if w <= prep.dist + 1e-9:
                    rej_tent += 1                  # spot outside the tent: a travel fly
                    continue
                d = float(lo.mark) - 2.0 * float(center.mark) + float(up.mark)
                if d <= 0 or w <= d:
                    continue
                r = (w - d) / d
                best_r = r if best_r is None else max(best_r, r)
                if r < R_FLOOR:
                    rej_r += 1
                    continue
                b, a = _gpb._structure_quote(lo, center, up)
                sd = d * stop_pct
                ok, _why = stop_survivable(sd, b, a)
                ratio = sd / (a - b) if (a - b) > 0 else None
                if ratio is not None:
                    best_ratio = ratio if best_ratio is None else max(best_ratio, ratio)
                if not ok:
                    rej_surv += 1
                    continue
                cands.append((r, side, w, lo, center, up, d, ratio))
        t.check("wing_candidates", float(len(cands)))
        t.check("r", best_r)
        t.check("stop_vs_spread", best_ratio)
        if centers == 0:
            t.check("legs", 0, False)
            prep.structural.append(("legs", f"no priced contract at the pin {pin:g} on either side "
                                            f"— the apex IS the trade"))
            return
        if not cands:
            t.check("legs", 0, False)
            prep.structural.append(("wing_search",
                f"no wing qualifies at pin {pin:g} on either side: {rej_tent} leave spot "
                f"({price_now:.2f}) outside the tent, {rej_r} under R {R_FLOOR:.2f} "
                f"(best R {_nr(best_r)}), {rej_surv} too narrow to clear their own spread "
                f"(best {_nr(best_ratio)}x of {STOP_VS_SPREAD_MIN:.1f}x)"))
            return
        r, side, w, lo, center, up, d, ratio = max(cands, key=lambda c: c[0])
        prep.side, prep.wing, prep.width = side, w, w
        prep.lower, prep.center, prep.upper = lo, center, up
        prep.debit, prep.r, prep.ratio = d, r, ratio
        for _qk, _qv in _gpb.leg_quote_facts(lo, center, up).items():
            t.check(f"quote_{_qk}", _qv, None)                          # r225: recorded, never gating
        t.direction = side
        t.check("width", w)
        t.check("debit", d)
        prep.ready = True
