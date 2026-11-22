"""
strategy/ogap_plan.py  v5.3
v5.3  2026-11-22  OTV5 r149 (OGAP.4) — THE SYMBOL TEST GOES: prepare() no longer refuses a box outside
      config.OGAP_SYMBOLS (deleted) with a dormant ogap_not_this_symbol row; OGAP reads the tape of whatever box it runs
      on. Whether it is asked at all is strategy/plan_state (the box flag `ogap`, default on; dormant on a live box), so
      a dormant OGAP is never asked and writes nothing. The operator, 2026-11-22: "I honestly want it paper Trading on all
      of them." The read, the contract pick, the mark floor and the sizing are unchanged.
      AND THE ogap_no_0dte REFUSAL GOES (the operator, 2026-11-22: "No to sitting out on non-expiry days. We just buy the nearest available expiry."): OGAP buys
      the chain's expiry, the one data/options_chain.OptionsChainFetcher.fetch_chain already chose for the tick (today's,
      else the nearest listed on or after today - the same chain and the same fallback every setup reads); no second
      rule here. Same strike pick, sizing and exits (the 15:45 close: flat the same day).
v5.2  2026-11-21  OTV5 r136 (OGAP.3) — OGAP READS THE MARK WHEREVER PARK'S SPEC READS THE ASK. The operator, 2026-11-20:
      "Ours needs the modification to account for how I would trade it, never pay the spread." / "Mark is the worst buy
      or sell we accept." The mark (the two-sided mid, floored to the cent as PARK.4) is computed before the gates, and
      the 0.50 floor (OGAP_MIN_ASK, its name kept, ogap_ask_floor), the size floor(RISK_PER_TRADE_USD / (mark x 100))
      and the band (0 contracts above RISK_PER_TRADE_USD / 100, ogap_ask_band) read it; the signal no longer carries
      ogap_ask (main sizes OGAP on entry_premium, the mark); the FIRE line names the mark first. The ask and the bid are
      still read for the two-sided check and still written to notes and the plan rows, as record only. Park's numbers
      and every other rule unchanged.
v5.1  2026-11-16  OTV5 r131 (OGAP.2) — contracts_for sizes on config.RISK_PER_TRADE_USD (the ramp MIN, OT_RISK_USD), not the
      deleted flat $500 OGAP_BUDGET_USD; the feasibility gate follows (an ask above RISK_PER_TRADE_USD / 100 buys none).
      The operator, 2026-11-16: "size the OGAP to whatever the ramp minimum (risk per trade) is set at instead of a flat $500".
v5.0  2026-11-14  OTV5 (OGAP.1) — THE OGAP PLAN: READS THE TAPE, PICKS THE CONTRACT, BUILDS THE SIGNAL. The operator,
      2026-11-14: "let's design & paper trade the OGAP on QQQ". OGAP is a faithful paper copy of Park's ORB-GAP (his
      spec of record 2026-11-13, docs/OGAP_SPEC.md); its signal, sizing and exits are his, unchanged.

      THE SPLIT (as park.py / park_plan.py): strategy/ogap.py says what must be true; THIS file reads the store's 1m bars,
      finds the range, the gap, gate-G, the break, the retest and the signal bar, picks the contract and builds the
      signal. The read itself is the PURE function `ogap_read()`, so the backtest (~/reviews/studies/park_orbgap_20261113,
      orbgap.day_signal) and the live plan can be compared bar for bar (tests/check_ogap.py replays five days).

      THE RULE (minutes are ET minutes of the day, a 1m bar labelled m covers m..m+1 and is CLOSED once the clock is at
      m+1 or later; only closed bars are read):
        range   - bars 09:30..09:44 (570..584): >= OGAP_RANGE_MIN_BARS of them and W = high - low > 0, else no range.
        gap     - (the 09:30 bar's open - the prior RTH close) / W. |gap| >= OGAP_GATE_G_W: only the gap's side (up ->
                  calls, down -> puts); otherwise both. Unreadable (no 09:30 bar or no prior close): both (fail open).
        break   - per side, the FIRST bar 09:45..10:30 (585..630) whose CLOSE is strictly beyond the range (a call's
                  level is the high, a put's the low). It never re-arms.
        retest  - the first bar within the OGAP_RETEST_BARS bars after the break bar (and <= 10:30): a call's low <=
                  level + 0.10W with its close > level; a put's high >= level - 0.10W with its close < level.
        signal  - the earliest retest bar on an ALLOWED side (a tie goes to the call, as the backtest sorts). A retest on
                  the refused side is a SHADOW: recorded, never traded, never blocking.
        fill    - in the minute right after the signal bar, or never (stale: the tick that first sees it is later).
        contract- the chain's expiry (r149: today's, else the nearest listed); the listed strike nearest the fill-minute open (a tie goes lower); ask >=
                  OGAP_MIN_ASK; contracts = floor(RISK_PER_TRADE_USD / (mark x 100)) >= 1 (a mark over RISK_PER_TRADE_USD / 100 buys none).
                  r136 (OGAP.3): every price here is the MARK (two-sided mid, floored to the cent), never the ask.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

import config
from strategy.plan import Plan

logger = logging.getLogger(__name__)

# WA 36 - each constant and its category. The range, the break window, the retest and gate-G define Park's trade
# (FOUNDATIONAL: another range or another retest is another trade); the ask floor and the budget are feasibility.
GATES = {
    "OGAP_RANGE_ET":      "FOUNDATIONAL",
    "OGAP_BREAK_ET":      "FOUNDATIONAL",
    "OGAP_RETEST_BARS":   "FOUNDATIONAL",
    "OGAP_RETEST_W":      "FOUNDATIONAL",
    "OGAP_GATE_G_W":      "FOUNDATIONAL",
    "OGAP_MIN_ASK":       "FEASIBILITY",                  # r136 OGAP.3: applied to the MARK (name kept)
    "RISK_PER_TRADE_USD": "FEASIBILITY",                  # r131 OGAP.2: the ramp MIN is OGAP's budget
}


def _m(hm) -> int:
    return int(hm[0]) * 60 + int(hm[1])


R0, R1 = _m(config.OGAP_RANGE_ET[0]), _m(config.OGAP_RANGE_ET[1])        # 570, 584
B0, B1 = _m(config.OGAP_BREAK_ET[0]), _m(config.OGAP_BREAK_ET[1])        # 585, 630


def _f(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def hhmm(m) -> str:
    return "%02d:%02d" % (int(m) // 60, int(m) % 60)


def ogap_read(bars: dict, prior_close, now_min: Optional[int] = None) -> dict:
    """THE READ. `bars` = {minute_of_day: (open, high, low, close)} for TODAY's RTH 1m bars; `prior_close` = the last
    RTH 1m close of the prior session (None = unread); `now_min` = the current ET minute (None = every bar is closed,
    the backtest's view). PURE: reads only bars labelled < now_min. NEVER raises. Returns:
      status  - "no range" | "signal" | "gate-refused only" | "break, no retest" | "no break" | "waiting"
      hi, lo, W, gap (None = unread), allowed (sorted sides), sides [{side, brk, signal, allowed}],
      side / signal / fill (the real row, when status == "signal"), stale (True when now_min is past the fill minute),
      shadows [{side, brk, signal}] (refused-side retests)."""
    res = {"status": "", "hi": None, "lo": None, "W": None, "gap": None, "allowed": ["C", "P"], "sides": [],
           "side": "", "signal": None, "fill": None, "stale": False, "shadows": [], "nbars_range": 0}
    try:
        lim = 10 ** 6 if now_min is None else int(now_min)
        b = {int(m): v for m, v in (bars or {}).items() if int(m) < lim}
        rng = [b[m] for m in range(R0, R1 + 1) if m in b]
        res["nbars_range"] = len(rng)
        if len(rng) < int(config.OGAP_RANGE_MIN_BARS):
            res["status"] = "no range"
            return res
        hi, lo = max(float(x[1]) for x in rng), min(float(x[2]) for x in rng)
        W = hi - lo
        res.update(hi=hi, lo=lo, W=W)
        if not W > 0:
            res["status"] = "no range"
            return res
        pc = _f(prior_close)
        if R0 in b and pc is not None:
            gap = (float(b[R0][0]) - pc) / W
            res["gap"] = gap
            g = float(config.OGAP_GATE_G_W)
            allowed = {"C"} if gap >= g else {"P"} if gap <= -g else {"C", "P"}
        else:
            allowed = {"C", "P"}                                    # fail open
        res["allowed"] = sorted(allowed)
        k = float(config.OGAP_RETEST_W)
        sides = []
        for side in "CP":
            brk = None
            for m in range(B0, B1 + 1):
                if m not in b:
                    continue
                c = float(b[m][3])
                if (side == "C" and c > hi) or (side == "P" and c < lo):
                    brk = m
                    break
            if brk is None:
                continue
            lvl = hi if side == "C" else lo
            sig = None
            for m in range(brk + 1, min(brk + int(config.OGAP_RETEST_BARS), B1) + 1):
                if m not in b:
                    continue
                _o, h, l, c = (float(x) for x in b[m][:4])
                if side == "C" and l <= lvl + k * W and c > lvl:
                    sig = m
                    break
                if side == "P" and h >= lvl - k * W and c < lvl:
                    sig = m
                    break
            sides.append({"side": side, "brk": brk, "signal": sig, "allowed": side in allowed})
        res["sides"] = sides
        res["shadows"] = [{"side": s["side"], "brk": s["brk"], "signal": s["signal"]}
                          for s in sides if s["signal"] is not None and not s["allowed"]]
        real = sorted([s for s in sides if s["signal"] is not None and s["allowed"]], key=lambda s: s["signal"])
        if real:
            r0 = real[0]
            res.update(status="signal", side=r0["side"], signal=r0["signal"], fill=r0["signal"] + 1)
            if now_min is not None and int(now_min) > r0["signal"] + 1:
                res["stale"] = True
            return res
        if res["shadows"]:
            res["status"] = "gate-refused only"
        elif sides:
            res["status"] = "break, no retest"
        else:
            res["status"] = "no break"
        return res
    except Exception as exc:                                    # noqa: BLE001
        res["status"] = "unreadable"
        res["err"] = f"{type(exc).__name__}: {exc}"
        return res


def pick_strike(rows, spot: float):
    """The listed strike nearest `spot`; a tie goes to the LOWER strike (orbgap.strike_of). None when no row."""
    best = None
    for c in rows or []:
        s = _f(getattr(c, "strike", None))
        if s is None:
            continue
        key = (abs(s - spot), s)
        if best is None or key < best[0]:
            best = (key, c)
    return best[1] if best else None


def mark_of(bid, ask) -> Optional[float]:
    """r136 (OGAP.3) - THE price OGAP reads: the two-sided mid floored to the cent (PARK.4's rounding). None unless
    ask >= bid > 0."""
    b, a = _f(bid), _f(ask)
    if b is None or a is None or not (a >= b > 0):
        return None
    return int((b + a) / 2.0 * 100.0 + 1e-9) / 100.0


def contracts_for(mark: float) -> int:
    """floor(RISK_PER_TRADE_USD / (mark x 100)); 0 = refused (never rounded up to 1). r131 OGAP.2: the ramp MIN;
    r136 OGAP.3: called with the MARK (Park's book used the ask)."""
    try:
        a = float(mark)
    except (TypeError, ValueError):
        return 0
    if not a > 0:
        return 0
    import math
    return int(math.floor(float(config.RISK_PER_TRADE_USD) / (a * 100.0) + 1e-9))


def today_bars(symbol: str, day):
    """{minute: (o, h, l, c)} of `symbol`'s RTH 1m bars today from the feed store, plus the prior RTH close - or a
    string naming why the store could not be read. NEVER raises. Reuses park_plan's two store reads."""
    from strategy import park_plan as _pp
    sess = _pp.session_bars(symbol, day, n_prior=0)
    if isinstance(sess, str):
        return sess
    out = {}
    for k, v in (sess.get("today") or {}).items():
        try:
            hh, mm = k.split(":")
            out[int(hh) * 60 + int(mm)] = tuple(v[:4])
        except Exception:                                       # noqa: BLE001
            continue
    fh = _pp.first_hour_bars(symbol, day)
    prior = fh.get("prior_close") if isinstance(fh, dict) else None
    return {"bars": out, "prior_close": prior}


_SHADOW_SAID: set = set()


def _cf_dir() -> str:
    return os.environ.get("OT_COUNTERFACTUAL_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "counterfactual")


def record_shadow(symbol: str, day, sh: dict, read: dict, chain=None, spot=None) -> bool:
    """Gate-G's refused side: ONE row per (day, side) in data/counterfactual/ogap_shadow.jsonl (the nightly pricer
    prices it after the close; never in EV). True when written this call. Never raises."""
    key = (str(day), sh.get("side"))
    if key in _SHADOW_SAID:
        return False
    _SHADOW_SAID.add(key)
    try:
        c = None
        if chain is not None and spot is not None:
            rows = getattr(chain, "calls", None) if sh.get("side") == "C" else getattr(chain, "puts", None)
            c = pick_strike(rows, float(spot))
        row = {"ts_epoch": time.time(), "rule": "ogap_gateg_shadow", "symbol": symbol, "day": str(day),
               "side": sh.get("side"), "break": hhmm(sh["brk"]) if sh.get("brk") is not None else None,
               "signal": hhmm(sh["signal"]) if sh.get("signal") is not None else None,
               "gap_w": read.get("gap"), "W": read.get("W"),
               "strike": _f(getattr(c, "strike", None)) if c is not None else None,
               "streamer_symbol": getattr(c, "streamer_symbol", "") if c is not None else "",
               "ask": _f(getattr(c, "ask", None)) if c is not None else None,
               "bid": _f(getattr(c, "bid", None)) if c is not None else None}
        d = _cf_dir()
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "ogap_shadow.jsonl"), "a") as fh:
            fh.write(json.dumps(row) + "\n")
        return True
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[ogap] shadow row NOT written: %s", exc)
        return False


class OgapPreparation:
    """What the read found. `ready` is True ONLY when every bar cleared and the contract was picked."""

    __slots__ = ("tick", "spec", "unmet", "ready", "read", "direction", "side", "contract", "premium",
                 "bid", "ask", "contracts", "spot", "price_now")

    def __init__(self, tick, spec):
        self.tick, self.spec = tick, spec
        self.unmet = []
        self.ready = False
        self.read = {}
        self.direction = self.side = ""
        self.contract = self.premium = self.bid = self.ask = self.spot = self.price_now = None
        self.contracts = 0

    def notes_line(self) -> str:
        r = self.read or {}
        return ("ogap gap=%s W=%s brk=%s sig=%s side=%s allowed=%s mark=%s ask=%s bid=%s" % (
            "n/a" if r.get("gap") is None else "%.3f" % r["gap"],
            "n/a" if r.get("W") is None else "%.4f" % r["W"],
            next((hhmm(s["brk"]) for s in r.get("sides", []) if s["side"] == r.get("side")), "n/a"),
            hhmm(r["signal"]) if r.get("signal") is not None else "n/a",
            r.get("side", ""), ",".join(r.get("allowed", [])),
            "n/a" if self.premium is None else "%.2f" % self.premium,
            "n/a" if self.ask is None else "%.2f" % self.ask,
            "n/a" if self.bid is None else "%.2f" % self.bid))

    def trade_line(self) -> str:
        if not self.ready:
            return "no trade prepared"
        return (f"buy {self.contracts} x {float(self.contract.strike):g}{self.side[0].upper()} @ mark {self.premium:.2f} "
                f"(bid {self.bid:.2f}, ask {self.ask:.2f}) - signal {hhmm(self.read['signal'])}, gap "
                f"{self.read.get('gap')}; exits on the mark: 1.6x -> floor 1.2x, 2.0x -> floor 0.60 x peak, 14:00 sweep < 0.75x, "
                f"15:45 bell")

    def emit(self, strategy_name: str):
        """Build the signal from what the PLAN selected. The strategy picks nothing."""
        from strategy.base_strategy import OptionsSignal as Signal
        c = self.contract
        sig = Signal(
            strategy_name=strategy_name,
            setup_type=f"ogap_{self.direction}",
            direction=self.direction,
            option_side=self.side,
            underlying_entry=float(self.price_now or self.spot),
            underlying_stop=0.0,                 # no structure stop: OGAP's exits are its own
            underlying_target=0.0,
            strike=c.strike, expiry=getattr(c, "expiry", ""),
            entry_premium=float(self.premium),   # THE MARK: paper books the mark like every setup
            contract=c,
            entry_delta=getattr(c, "delta", None),
            stop_loss_pct=1.0,                   # no premium stop (stop_premium = 0)
        )
        sig.notes = self.notes_line()
        # r136 (OGAP.3): the decision basis is the MARK (entry_premium): main sizes OGAP on it and the exits measure every
        # line from the booked fill. No ogap_ask any more (Park's book read the ask; the operator: "never pay the spread").
        sig.ogap_contracts = int(self.contracts)
        logger.info("[ogap] FIRE %s — %s", self.direction, self.trade_line())
        return self.tick.take(sig)


class OgapPlan:
    name = "OGAP"

    def __init__(self):
        from strategy.ogap import Ogap as _Spec
        self.planner = Plan(self.name, _Spec.PLAN_CHECKS, self_ledgers=True)

    @staticmethod
    def _symbol() -> str:
        try:
            return str(getattr(config, "INSTRUMENT", "") or "")
        except Exception:                                       # noqa: BLE001
            return ""

    def prepare(self, *, spec, price_now, now_et, chain=None, day=None, symbol: str = "", bars=None,
                prior_close=None, **_ignored) -> OgapPreparation:
        """`now_et` is "HH:MM" (the tick's ET minute). `bars` / `prior_close` are for tests and the replay; live, the
        feed store is read."""
        from utils.time_utils import parse_hm as _hm
        t = self.planner.tick(price_now)
        prep = OgapPreparation(t, spec)
        prep.price_now = _f(price_now)
        sym = (symbol or self._symbol()).upper()
        # r149 (OGAP.4): no symbol test - plan_state decides whether OGAP is asked on this box (the box flag `ogap`).
        hm = _hm(now_et)
        w0, w1 = config.ENTRY_WINDOWS["OGAP"]
        if hm is None or not (tuple(w0) <= tuple(hm) < tuple(w1)):
            t.dormant("ogap_entry_window", "outside %02d:%02d-%02d:%02d ET" % (w0[0], w0[1], w1[0], w1[1]))
            return prep
        now_min = int(hm[0]) * 60 + int(hm[1])

        if day is None:
            from utils.time_utils import now_et as _now
            day = _now().date()
        if bars is None:
            tb = today_bars(sym, day)
            if isinstance(tb, str):
                t.note(tb)
                return t.starved("ogap_bars") or prep
            bars, store_pc = tb["bars"], tb["prior_close"]
            if prior_close is None:
                prior_close = store_pc
        r = ogap_read(bars, prior_close, now_min)
        prep.read = r
        t.check("ogap_range_w", r.get("W"), None if r.get("W") is None else r.get("W", 0) > 0)
        t.check("ogap_range_bars", float(r.get("nbars_range", 0)), None)
        t.check("ogap_gap", r.get("gap"), None, note="" if r.get("gap") is not None else "gap unread: both sides")
        t.check("ogap_allowed", None, None, note=",".join(r.get("allowed", [])))
        for s in r.get("sides", []):
            t.check(f"ogap_break_{s['side'].lower()}", float(s["brk"]), None, note=hhmm(s["brk"]))
            if s["signal"] is not None:
                t.check(f"ogap_signal_{s['side'].lower()}", float(s["signal"]), bool(s["allowed"]),
                        note=hhmm(s["signal"]) + ("" if s["allowed"] else " (gate-G refused: shadow)"))
        for sh in r.get("shadows", []):
            if record_shadow(sym, day, sh, r, chain=chain, spot=price_now):
                t.check("ogap_gateg_shadow", float(sh["signal"]), None,
                        note="%s %s refused by gate-G (gap %s W) - shadow, never in EV" % (
                            sh["side"], hhmm(sh["signal"]), r.get("gap")))
        st = r.get("status")
        if st != "signal":
            if st == "no range":
                return t.refuse("ogap_no_range", "%d of 15 range bars, W=%s" % (r.get("nbars_range", 0), r.get("W")))
            if st == "unreadable":
                t.note(r.get("err", ""))
                return t.starved("ogap_read") or prep
            return t.hold("ogap_no_signal: " + st) or prep
        if r.get("stale"):
            return t.refuse("ogap_stale", "signal bar %s first seen at %s - never filled late" % (
                hhmm(r["signal"]), now_et))
        side = "call" if r["side"] == "C" else "put"
        prep.side, prep.direction = side, ("long" if side == "call" else "short")
        rows = (getattr(chain, "calls", None) if side == "call" else getattr(chain, "puts", None)) or []
        if chain is None or not rows:
            return t.starved("chain") or prep
        # r149 (OGAP.4): the chain's expiry, whatever it is (today's, else fetch_chain's nearest) - no 0DTE refusal.
        fb = bars.get(now_min) if isinstance(bars, dict) else None
        spot = _f(fb[0]) if fb else None
        if spot is None:
            spot = prep.price_now
        if spot is None:
            return t.starved("spot") or prep
        prep.spot = spot
        k = pick_strike(rows, spot)
        bid, ask = (_f(getattr(k, "bid", None)), _f(getattr(k, "ask", None))) if k is not None else (None, None)
        t.check("strike", _f(getattr(k, "strike", None)) if k is not None else None, None)
        t.check("ask", ask, None)
        t.check("bid", bid, None)
        if k is None or bid is None or ask is None or not (ask >= bid > 0):
            return t.refuse("ogap_contract", "no two-sided ATM contract") or prep
        mark = mark_of(bid, ask)                                      # r136 OGAP.3: THE price every gate reads
        if mark is None:
            return t.refuse("ogap_contract", "no two-sided ATM contract") or prep
        if mark < float(config.OGAP_MIN_ASK):
            return t.refuse("ogap_ask_floor", "mark %.2f < %.2f" % (mark, config.OGAP_MIN_ASK)) or prep
        n = contracts_for(mark)
        t.check("contracts", float(n), n >= 1)
        if n < 1:
            return t.refuse("ogap_ask_band", "mark %.2f buys 0 contracts on $%.0f" % (mark, config.RISK_PER_TRADE_USD)) or prep
        prep.contract, prep.bid, prep.ask, prep.contracts = k, bid, ask, n
        prep.premium = mark                                           # the mark, floored to the cent (PARK.4)
        prep.ready = True
        t.anchor(trigger=spot)
        return prep
