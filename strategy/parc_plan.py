"""
strategy/parc_plan.py  v5.0
v5.0  2026-10-27  OTV5 r46 (PARC.1) — new. PARC'S PLAN: PARK'S FIRST-HOUR READ, THEN THE SAFER-SIDE CREDIT SPREAD,
      ITS 5m STRUCTURE STOP AND ITS CREDIT. The specification - what must be true - is strategy/parc.py; this file is
      the search. The operator, 2026-10-27: "under identical entry conditions the PARK trade sells a credit spread ATM
      nearest the strike on the safer side ..."; "Call it PARC"; "No shadow mode. We're paper. It trades tomorrow.";
      "I also want to make sure it uses the ladder entry & exit."

      THE READ: park_plan.read_first_hour - PARK's code, not a copy (09:30 open, 10:30 close, 11:00 close, the prior
      close; the move, the direction, GATE-G).
      THE SPREAD: today's chain (main passes the chain PARK is asked with). A long -> puts: the first listed strike
      strictly BELOW the 11:00 close is SOLD, the next listed strike below it BOUGHT. A short -> calls: the first
      strictly ABOVE is sold, the next above bought. Both legs two-sided (ask >= bid > 0).
      THE CREDIT: the mark credit = ((short.bid - long.ask) + (short.ask - long.bid)) / 2 = short mid - long mid,
      r220's structure midpoint - exactly what main._execute_condor_leg books on paper through
      limit_ladder.paper_fill_credit and where the live walk (main._post_credit_vertical) ends. The MIN_CREDIT gate
      reads the price the ladder books: paper -> paper_fill_credit(mark), live -> the mark; the row names it.
      THE STOP: breakout_plan.swing_5m_stop (BRK.11, the feed store, read-only) over BRK_STOP5M_BARS closed 5m bars of
      today's RTH that ENDED by 11:01 (the 11:00 1m bar's close) - read by time, never by frame position. Long: the
      lowest low, which must sit strictly below the 11:00 close; short: the highest high, strictly above it. An
      unreadable store or no swing behind the price is NO TRADE. ENT.1: the price now already through it is no trade.
      THE STOP'S COST: each leg priced by Black-Scholes (r = 0, execution.fill_observers.bs_price) at its own chain IV
      and the real time left to its expiry's 16:00 ET, with the underlying AT the stop; value_at_stop = short - long.
      A leg with no IV -> None (the sizer then uses the max loss; it never invents a smaller number).
"""

from __future__ import annotations

import logging
from datetime import datetime, time as _time
from typing import Optional

import config
from strategy.plan import Plan
from strategy.park_plan import read_first_hour, _f
from utils.time_utils import parse_hm as _hm

logger = logging.getLogger(__name__)

_ET_ZONE = "America/New_York"
MIN_CREDIT = float(config.PARC_MIN_CREDIT)

# WA 36 - a credit the nickel close cannot pay for four times over is not a trade.
GATES = {
    "MIN_CREDIT": "FEASIBILITY",
}


def pick_spread(rows, spot: float, direction: str):
    """(short, long) for `direction` from one side of the chain, or (None, None). A long reads puts: the first
    listed strike strictly below `spot`, then the next listed below that. A short reads calls: the first strictly
    above, then the next above. Strikes the chain lists twice count once (the first contract listed)."""
    by_strike = {}
    for k in rows or []:
        s = _f(getattr(k, "strike", None))
        if s is not None and s not in by_strike:
            by_strike[s] = k
    if direction == "long":
        side = sorted((s for s in by_strike if s < spot), reverse=True)
    elif direction == "short":
        side = sorted(s for s in by_strike if s > spot)
    else:
        side = []
    if len(side) < 2:
        return None, None
    return by_strike[side[0]], by_strike[side[1]]


def two_sided(k) -> bool:
    bid, ask = _f(getattr(k, "bid", None)), _f(getattr(k, "ask", None))
    return bid is not None and ask is not None and ask >= bid > 0


def mark_credit(short, long) -> float:
    """r220's structure midpoint for a SOLD vertical: ((sb - la) + (sa - lb)) / 2."""
    sb, sa = float(short.bid), float(short.ask)
    lb, la = float(long.bid), float(long.ask)
    return ((sb - la) + (sa - lb)) / 2.0


def _years_to_expiry(expiry, now) -> Optional[float]:
    """Calendar years from `now` to 16:00 ET on `expiry` (YYYY-MM-DD), or None."""
    try:
        from zoneinfo import ZoneInfo
        d = datetime.strptime(str(expiry)[:10], "%Y-%m-%d").date()
        end = datetime.combine(d, _time(16, 0), tzinfo=ZoneInfo(_ET_ZONE))
        secs = (end - now).total_seconds()
    except Exception:                                           # noqa: BLE001
        return None
    return max(0.0, secs) / (365.0 * 24 * 3600)


def value_at(short, long, spot: float, now, call: bool):
    """(spread value with the underlying at `spot`, short iv, long iv). Value None when a leg has no IV or no
    expiry - never a guess."""
    from execution.fill_observers import bs_price
    vals, ivs = [], []
    for leg in (short, long):
        iv = _f(getattr(leg, "iv", None)) or 0.0
        ivs.append(iv if iv > 0 else None)
        t = _years_to_expiry(getattr(leg, "expiry", ""), now)
        if iv <= 0 or t is None:
            vals.append(None)
            continue
        vals.append(bs_price(float(spot), float(leg.strike), t, iv, call))
    if None in vals:
        return None, ivs[0], ivs[1]
    return max(0.0, vals[0] - vals[1]), ivs[0], ivs[1]


class ParcPreparation:
    """What the search found. `ready` is True ONLY when every bar cleared."""

    __slots__ = ("tick", "spec", "conditions", "unmet", "ready", "direction", "side", "move_pct", "gap",
                 "spot", "price_now", "short_leg", "long_leg", "width", "credit_mark", "credit", "credit_basis",
                 "stop", "value_at_stop")

    def __init__(self, tick, spec):
        self.tick, self.spec = tick, spec
        self.conditions, self.unmet = {}, []
        self.ready = False
        self.direction = self.side = self.credit_basis = ""
        self.move_pct = self.gap = self.spot = self.price_now = None
        self.short_leg = self.long_leg = None
        self.width = self.credit_mark = self.credit = self.stop = self.value_at_stop = None

    def cond(self, name, current, met, note: str = ""):
        required = self.spec.CONDITIONS.get(name, "")
        self.conditions[name] = (current, required, bool(met))
        if not met:
            self.unmet.append(name)
        self.tick.check(name, current if isinstance(current, (int, float)) else None, bool(met), note=note)

    def trade_line(self) -> str:
        if not self.ready:
            return "no trade prepared"
        kind = "P" if self.side == "put" else "C"
        return (f"sell {float(self.short_leg.strike):g}/{float(self.long_leg.strike):g}{kind} @ {self.credit:.2f} "
                f"({self.credit_basis}; mark {self.credit_mark:.2f}) - first hour {self.move_pct:+.3f}%, gap "
                f"{self.gap:+.2f}; stop {self.stop:.2f} (5m swing); exits: structure touch, nickel "
                f"{config.CONDOR_NICKEL_CLOSE:.2f}, else EOD.1")

    def emit(self, strategy_name: str):
        """Build the signal from what the PLAN selected. The strategy picks nothing."""
        from strategy.base_strategy import OptionsSignal as Signal
        put = self.side == "put"
        sig = Signal(
            strategy_name=strategy_name,
            setup_type=f"parc_{self.direction}",
            direction=self.direction,
            option_side=self.side,
            underlying_entry=float(self.price_now or self.spot),
            underlying_stop=float(self.stop),            # THE 5m SWING: exit_engine._evaluate_parc's structure stop
            underlying_target=0.0,
            strike=self.short_leg.strike, expiry=getattr(self.short_leg, "expiry", ""),
            entry_premium=float(self.credit_mark),       # the mark credit; the ladder books the fill
            contract=self.short_leg,
            entry_delta=getattr(self.short_leg, "delta", None),
            is_credit_vertical=True,
            short_put_contract=self.short_leg if put else None,
            long_put_contract=self.long_leg if put else None,
            short_call_contract=None if put else self.short_leg,
            long_call_contract=None if put else self.long_leg,
            net_credit=float(self.credit_mark),          # main._execute_condor_leg: paper_fill_credit / the live walk
            max_loss_condor=float(self.width) - float(self.credit_mark),
            stop_loss_pct=0.0,                           # no premium stop (stop_premium = 0)
        )
        sig.parc_value_at_stop = self.value_at_stop      # risk_manager._size_parc's loss at the stop
        sig.parc_credit_basis = self.credit_basis
        logger.info("[parc] FIRE %s — %s", self.direction, self.trade_line())
        return self.tick.take(sig)


class ParcPlan:
    name = "PARC"

    def __init__(self):
        from strategy.parc import Parc as _Spec
        self.planner = Plan(self.name, _Spec.PLAN_CHECKS, self_ledgers=True)

    @staticmethod
    def _symbol() -> str:
        try:
            return str(getattr(config, "INSTRUMENT", "") or "")
        except Exception:                                       # noqa: BLE001
            return ""

    def prepare(self, *, spec, price_now, now_et, chain=None, prior_close=None, day=None,
                symbol: str = "", paper=None, now=None, **_ignored) -> ParcPreparation:
        from strategy import parc as S
        from strategy.breakout_plan import swing_5m_stop
        from zoneinfo import ZoneInfo

        t = self.planner.tick(price_now)
        prep = ParcPreparation(t, spec)
        prep.price_now = _f(price_now)

        # ── the window. DORMANT writes one row and goes quiet ──────────────
        hm, lo, hi = _hm(now_et), _hm(S.EARLIEST_ET), _hm(S.LATEST_ET)
        if hm is None or lo is None or hi is None or not (lo <= hm < hi):
            t.dormant("entry_window", f"outside {S.EARLIEST_ET}-{S.LATEST_ET} ET")
            return prep
        prep.cond("entry_window", None, True)

        # ── the first hour: PARK's read, PARK's code ───────────────────────
        if now is None:
            from utils.time_utils import now_et as _now
            now = _now()
        if day is None:
            day = now.date()
        sym = symbol or self._symbol()
        fh = read_first_hour(t, prep.cond, symbol=sym, day=day, prior_close=prior_close)
        if fh is None:
            return prep
        spot, direction = fh["spot"], fh["direction"]
        prep.move_pct, prep.spot, prep.gap, prep.direction = fh["move_pct"], spot, fh["gap"], direction
        prep.side = "put" if direction == "long" else "call" if direction == "short" else ""
        if prep.unmet:
            t.refuse(prep.unmet[0], "not this session — " + ", ".join(prep.unmet))
            return prep

        # ── the spread: the first two listed strikes on the safer side ─────
        rows = (getattr(chain, "puts", None) if direction == "long" else getattr(chain, "calls", None)) or []
        if chain is None or not rows:
            t.starved("chain")
            return prep
        short, long_ = pick_spread(rows, spot, direction)
        ok = short is not None and long_ is not None and two_sided(short) and two_sided(long_)
        t.check("short_strike", _f(getattr(short, "strike", None)), None)
        t.check("long_strike", _f(getattr(long_, "strike", None)), None)
        why = ("no two listed strikes beyond the 11:00 close on the safer side" if short is None else
               "a leg's quote is not two-sided")
        prep.cond("spread", None, ok, note="" if ok else why)
        if not ok:
            t.refuse("spread", why)
            return prep
        width = abs(float(short.strike) - float(long_.strike))
        t.check("width", width, None)
        cm = mark_credit(short, long_)
        if paper is None:
            paper = bool(getattr(config, "PAPER_TRADING", True))
        if paper:
            from execution.limit_ladder import paper_fill_credit
            credit, basis = float(paper_fill_credit(cm)), "paper_fill_credit(mark)"
        else:
            credit, basis = float(cm), "mark (the live walk's last rung)"
        t.check("credit_mark", cm, None)
        ok_c = credit >= MIN_CREDIT and credit < width
        prep.cond("min_credit", credit, ok_c, note=f"credit basis: {basis}")
        if not ok_c:
            t.refuse("min_credit", f"credit {credit:.2f} ({basis}) < {MIN_CREDIT:.2f}" if credit < MIN_CREDIT
                     else f"credit {credit:.2f} >= width {width:.2f}")
            return prep

        # ── the structure stop: Breakout's 5m swing behind the 11:00 price ─
        sig_end_ms = int(datetime(day.year, day.month, day.day, *config.PARK_SPOT_BAR_ET,
                                  tzinfo=ZoneInfo(_ET_ZONE)).timestamp() * 1000) + 60_000
        sw = swing_5m_stop(sym, day, sig_end_ms, direction, int(getattr(config, "BRK_STOP5M_BARS", 3)))
        stop = None if isinstance(sw, str) else _f(sw)
        behind = stop is not None and ((stop < spot) if direction == "long" else (stop > spot))
        px = prep.price_now
        through = (behind and px is not None
                   and ((px <= stop) if direction == "long" else (px >= stop)))
        t.check("stop", stop, None)
        if isinstance(sw, str):
            why = f"{sw} - no structure stop, no trade"
        elif stop is None:
            why = "no closed 5m bar of today's RTH by 11:01 - no structure stop, no trade"
        elif not behind:
            why = (f"the 5m swing {stop:.2f} is not behind the 11:00 close {spot:.2f} - no structure stop, "
                   f"no trade")
        elif through:
            why = f"the price {px:.2f} is already through the stop {stop:.2f} (ENT.1)"
        else:
            why = ""
        prep.cond("structure_stop", stop, not why, note=why)
        if why:
            t.refuse("structure_stop", why)
            return prep

        v, siv, liv = value_at(short, long_, stop, now, call=(direction == "short"))
        t.check("value_at_stop", v, None)
        t.check("short_iv", siv, None)
        t.check("long_iv", liv, None)
        if v is None:
            t.note("a leg has no IV - the sizer uses the max loss at the stop")

        prep.short_leg, prep.long_leg, prep.width = short, long_, width
        prep.credit_mark, prep.credit, prep.credit_basis = cm, credit, basis
        prep.stop, prep.value_at_stop = stop, v
        t.credit, t.short_strike, t.long_strike = credit, float(short.strike), float(long_.strike)
        t.risk = width - credit
        prep.ready = True
        t.anchor(trigger=spot, invalidation=stop)
        return prep
