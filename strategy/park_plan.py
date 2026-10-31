"""
strategy/park_plan.py  v5.2
v5.2  2026-10-30  OTV5 r60 (PARK.4) — PARK BUYS AT THE MARK, NOT THE ASK. The operator, 2026-10-30, on CVX's PARK
      (235C bought at the ask 1.56 on a 0.97/1.56 quote, mark 1.265, -$657 booked, -$480 at the mark): "That's not my
      spec… you know park is a borrowed trade. To match my spec, we ladder in from aggressive to mark & never worse
      than mark". prepare() sets the premium to the MARK, (bid + ask) / 2 of the contract it picked - the same mark
      data/options_chain and execution/entry_ladder compute - floored to the cent (entry_engine._mark_cap's rule, r224
      FLY.1; the raw float 1.265 rounded UP to 1.27 in limit_at_mark), so the signal's entry_premium is the mark: paper
      books the mark (entry_engine._paper_fill_single -> limit_ladder.paper_fill_price), the size is floor(risk / (mark
      x 100)) and the +60% / +20% lock keys off the booked mark. Live walks the r104 ladder (entry_engine
      _place_single_leg -> ladder_registry.price_for): 25% in from the bid, one increment a tick toward the mark,
      never above it; unfilled by 11:03 is no trade. The feasibility bar is unchanged (two-sided, ask >=
      PARK_MIN_ASK). The FIRE line reads "@ <mark> (mark, bid/ask b/a)"; park_signal.jsonl keeps the real "ask" and
      "bid" and adds "mark". Every PARK fill 10-26..10-30 (28 of 28) had paid the ask: $651 over the mark, $177 of
      it CVX 10-30. Gate tests/check_park_entry_mark.py.
v5.1  2026-10-27  OTV5 r46 (PARC.1) — THE FIRST-HOUR READ IS ONE FUNCTION, SHARED WITH PARC. The operator, 2026-10-27:
      "under identical entry conditions the PARK trade sells a credit spread ... Call it PARC"; "No shadow mode. We're
      paper. It trades tomorrow." read_first_hour() is the block ParkPlan.prepare ran inline - the store read, the
      starved inputs, the prior-close source, the move, the direction and GATE-G, every plan check in the same order -
      moved verbatim so strategy/parc_plan.py asks the SAME code. PARK's decisions and rows are byte-identical
      (tests/check_park.py, tests/check_parc.py P10).
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-18  OTV4TEST r288 (PARK.1) — PARK'S PLAN: READS THE FIRST HOUR, PICKS THE CONTRACT, BUILDS THE
      SIGNAL. The specification - what must be true - is strategy/park.py; this file is the search (the
      operator, 2026-10-17 18:30 ET: "Make sure when you build it it's divided properly between the strategy
      and the plan").

      THE READ (frozen, /var/tmp/sat_1017/cont11/PREREG_CONT11.md C0 and cont11.py): the 09:30 1m bar's OPEN, the
      10:30 1m bar's CLOSE and the 11:00 1m bar's CLOSE of TODAY's RTH, and the prior session's last RTH 1m close
      - all read from the feed store (read-only) on every call, so a restart decides the same. The prior close
      falls back to the caller's `prior_close` (main: the gap's prior_close) only when the store has no prior
      session; which one was used is recorded on the row.
      THE CONTRACT: today's chain, the strike nearest the 11:00 close (ties: the lower strike), its side's
      contract, two-sided, ask >= PARK_MIN_ASK. ENTRY = THE MARK (v5.2, the operator 2026-10-30: "we ladder in from
      aggressive to mark & never worse than mark"; it was the ask, the study's fill); the paper fill books
      entry_premium, and the live ladder never pays more than the mark.
      THE SIGNAL carries no premium stop and no underlying stop (stop_loss_pct = 1.0, underlying_stop = 0): the
      exits are PARK's own (execution/exit_engine._evaluate_park).
"""

from __future__ import annotations

import logging
from typing import Optional

import config
from strategy.plan import Plan
from utils.time_utils import parse_hm as _hm

logger = logging.getLogger(__name__)

_ET_ZONE = "America/New_York"
MIN_ASK = float(config.PARK_MIN_ASK)

# WA 36 - a cheaper ask is not a contract this trade can hold (the study's floor).
GATES = {
    "MIN_ASK": "FEASIBILITY",
}


def _f(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def first_hour_bars(symbol: str, day):
    """{"open_0930", "close_1030", "spot_1100", "prior_close"} for `day` from the feed store's 1m candles
    (None where a bar is absent), or a string naming why the store could not be read. NEVER raises.
    prior_close = the last 1m close of the most recent earlier RTH session in the store."""
    from datetime import datetime
    try:
        import sqlite3
        from zoneinfo import ZoneInfo
        from data.candle_feed import feed_db_path
        z = ZoneInfo(_ET_ZONE)

        def ms(h, m):
            return int(datetime(day.year, day.month, day.day, h, m, tzinfo=z).timestamp() * 1000)
        conn = sqlite3.connect(f"file:{feed_db_path()}?mode=ro", uri=True, timeout=5.0)
        try:
            def bar(h, m):
                return conn.execute("SELECT open, close FROM candles WHERE symbol=? AND interval='1m' "
                                    "AND ts_epoch_ms=? AND close > 0", (symbol, ms(h, m))).fetchone()
            b930, b1030 = bar(9, 30), bar(*config.PARK_SIGNAL_BAR_ET)
            b1100 = bar(*config.PARK_SPOT_BAR_ET)
            # the prior session: the newest 1m bar before today's 09:30 whose ET time is inside RTH
            prev = conn.execute(
                "SELECT ts_epoch_ms, close FROM candles WHERE symbol=? AND interval='1m' AND ts_epoch_ms < ? "
                "AND ts_epoch_ms >= ? AND close > 0 ORDER BY ts_epoch_ms DESC LIMIT 600",
                (symbol, ms(9, 30), ms(9, 30) - 6 * 86_400_000)).fetchall()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        return f"1m bars unreadable ({type(exc).__name__}: {exc})"
    prior = None
    for t, c in prev:
        et = datetime.fromtimestamp(t / 1000, z)
        if (9, 30) <= (et.hour, et.minute) < (16, 0):
            prior = float(c)
            break
    return {"open_0930": float(b930[0]) if b930 else None,
            "close_1030": float(b1030[1]) if b1030 else None,
            "spot_1100": float(b1100[1]) if b1100 else None,
            "prior_close": prior}


def read_first_hour(t, cond, *, symbol: str, day, prior_close=None):
    """THE FIRST-HOUR READ (PARK.1), shared by PARK and PARC (OTV5 r46). Reads the store, writes the plan checks
    in PARK's order on tick `t`, asks `cond` for first_hour_move and gate_g, and returns {"move_pct", "spot",
    "direction", "gap"} - or None when the tick STARVED (it has already said so on `t`). Moved verbatim from
    ParkPlan.prepare: the starved inputs, the prior-close source note, the move and the direction rule
    (up first hour = long), GATE-G (a long needs gap >= 0, a short gap <= 0)."""
    bars = first_hour_bars(symbol, day)
    if isinstance(bars, str):
        t.note(bars)
        t.starved("first_hour_bars")
        return None
    missing = [k for k in ("open_0930", "close_1030", "spot_1100") if bars.get(k) is None]
    if missing:
        t.starved(*missing)
        return None
    o, c1030, spot = bars["open_0930"], bars["close_1030"], bars["spot_1100"]
    prev, src = bars.get("prior_close"), "store"
    if prev is None:
        prev, src = _f(prior_close), "caller"
    if prev is None:
        t.starved("prior_close")
        return None
    for k, v in (("open_0930", o), ("close_1030", c1030), ("spot_1100", spot), ("prior_close", prev)):
        t.check(k, v, None)
    t.note(f"prior close from the {src}")

    move = (c1030 / o - 1.0) * 100.0
    t.check("move_pct", move, None)
    cond("first_hour_move", abs(move), abs(move) >= config.PARK_MOVE_PCT)
    direction = "long" if move > 0 else "short" if move < 0 else ""
    gap = o - prev
    t.check("gap", gap, None)
    cond("gate_g", gap, bool(direction) and ((gap >= 0) if direction == "long" else (gap <= 0)))
    return {"move_pct": move, "spot": spot, "direction": direction, "gap": gap}


def _record_would_fire(prep) -> None:
    """PARK_MODE=log: what PARK would have bought. data/counterfactual/park_signal.jsonl. Never raises."""
    try:
        import json, os, time
        d = os.environ.get("OT_COUNTERFACTUAL_DIR") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "counterfactual")
        os.makedirs(d, exist_ok=True)
        c = prep.contract
        row = {"ts_epoch": time.time(), "rule": "park_signal", "mode": config.PARK_MODE,
               "direction": prep.direction, "move_pct": prep.move_pct, "gap": prep.gap,
               "strike": float(getattr(c, "strike", 0) or 0), "side": prep.side,
               "streamer_symbol": getattr(c, "streamer_symbol", ""), "ask": prep.ask,
               "bid": prep.bid, "mark": prep.premium, "spot_1100": prep.spot}
        with open(os.path.join(d, "park_signal.jsonl"), "a") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[park] signal counterfactual row NOT written: %s", exc)


class ParkPreparation:
    """What the search found. `ready` is True ONLY when every bar cleared."""

    __slots__ = ("tick", "spec", "conditions", "unmet", "ready", "direction", "side", "move_pct", "gap",
                 "spot", "contract", "premium", "price_now", "bid", "ask")

    def __init__(self, tick, spec):
        self.tick, self.spec = tick, spec
        self.conditions, self.unmet = {}, []
        self.ready = False
        self.direction = self.side = ""
        self.move_pct = self.gap = self.spot = None
        self.contract = self.premium = self.price_now = None
        self.bid = self.ask = None              # v5.2: the quote the mark was taken from

    def cond(self, name, current, met, note: str = ""):
        required = self.spec.CONDITIONS.get(name, "")
        self.conditions[name] = (current, required, bool(met))
        if not met:
            self.unmet.append(name)
        self.tick.check(name, current if isinstance(current, (int, float)) else None, bool(met), note=note)

    def trade_line(self) -> str:
        if not self.ready:
            return "no trade prepared"
        return (f"buy {float(self.contract.strike):g}{self.side[0].upper()} @ {self.premium:.2f} (mark, bid/ask {self.bid:.2f}/{self.ask:.2f}) - first "
                f"hour {self.move_pct:+.3f}%, gap {self.gap:+.2f}; exits: lock +{config.PARK_LOCK_ARM:.0%}/"
                f"+{config.PARK_LOCK_FLOOR:.0%}, |delta| <= {config.PARK_DELTA_FLOOR:.2f} from "
                f"{config.PARK_DELTA_FROM_ET[0]:02d}:{config.PARK_DELTA_FROM_ET[1]:02d}, else "
                f"{config.PARK_CLOSE_ET[0]:02d}:{config.PARK_CLOSE_ET[1]:02d}")

    def record_would_fire(self) -> None:
        _record_would_fire(self)

    def emit(self, strategy_name: str):
        """Build the signal from what the PLAN selected. The strategy picks nothing."""
        from strategy.base_strategy import OptionsSignal as Signal
        c = self.contract
        sig = Signal(
            strategy_name=strategy_name,
            setup_type=f"park_{self.direction}",
            direction=self.direction,
            option_side=self.side,
            underlying_entry=float(self.price_now or self.spot),
            underlying_stop=0.0,                 # no structure stop: PARK's exits are its own
            underlying_target=0.0,
            strike=c.strike, expiry=getattr(c, "expiry", ""),
            entry_premium=float(self.premium),   # THE MARK (v5.2; was the ask)
            contract=c,
            entry_delta=getattr(c, "delta", None),
            stop_loss_pct=1.0,                   # no premium stop (stop_premium = 0)
        )
        logger.info("[park] FIRE %s — %s", self.direction, self.trade_line())
        return self.tick.take(sig)


class ParkPlan:
    name = "PARK"

    def __init__(self):
        from strategy.park import Park as _Spec
        self.planner = Plan(self.name, _Spec.PLAN_CHECKS, self_ledgers=True)

    @staticmethod
    def _symbol() -> str:
        try:
            return str(getattr(config, "INSTRUMENT", "") or "")
        except Exception:                                       # noqa: BLE001
            return ""

    def prepare(self, *, spec, price_now, now_et, chain=None, prior_close=None, day=None,
                symbol: str = "", **_ignored) -> ParkPreparation:
        from strategy import park as P

        t = self.planner.tick(price_now)
        prep = ParkPreparation(t, spec)
        prep.price_now = _f(price_now)

        # ── the window. DORMANT writes one row and goes quiet ──────────────
        hm, lo, hi = _hm(now_et), _hm(P.EARLIEST_ET), _hm(P.LATEST_ET)
        if hm is None or lo is None or hi is None or not (lo <= hm < hi):
            t.dormant("entry_window", f"outside {P.EARLIEST_ET}-{P.LATEST_ET} ET")
            return prep
        prep.cond("entry_window", None, True)

        # ── the first hour, from the store (r46: one read, shared with PARC) ──
        if day is None:
            from utils.time_utils import now_et as _now
            day = _now().date()
        fh = read_first_hour(t, prep.cond, symbol=symbol or self._symbol(), day=day, prior_close=prior_close)
        if fh is None:
            return prep
        spot = fh["spot"]
        prep.move_pct, prep.spot = fh["move_pct"], spot
        direction = fh["direction"]
        prep.direction = direction
        prep.side = "call" if direction == "long" else "put" if direction == "short" else ""
        prep.gap = fh["gap"]
        if prep.unmet:
            t.refuse(prep.unmet[0], "not this session — " + ", ".join(prep.unmet))
            return prep

        # ── the contract ──────────────────────────────────────────────────
        rows = (getattr(chain, "calls", None) if direction == "long" else getattr(chain, "puts", None)) or []
        if chain is None or not rows:
            t.starved("chain")
            return prep
        best = None
        for k in rows:
            s = _f(getattr(k, "strike", None))
            if s is None:
                continue
            key = (abs(s - spot), s)
            if best is None or key < best[0]:
                best = (key, k)
        k = best[1] if best else None
        bid, ask = (_f(getattr(k, "bid", None)), _f(getattr(k, "ask", None))) if k is not None else (None, None)
        t.check("strike", _f(getattr(k, "strike", None)) if k is not None else None, None)
        t.check("ask", ask, None)
        t.check("bid", bid, None)
        t.check("delta", _f(getattr(k, "delta", None)) if k is not None else None, None)
        ok = (k is not None and bid is not None and ask is not None and ask >= bid > 0
              and ask >= MIN_ASK)
        prep.cond("contract", ask, ok,
                  note="" if ok else "no two-sided ATM contract with ask >= %.2f" % config.PARK_MIN_ASK)
        if not ok:
            t.refuse("contract", "no two-sided ATM contract with ask >= %.2f" % config.PARK_MIN_ASK)
            return prep
        # v5.2 (PARK.4) - THE MARK, NOT THE ASK. The operator, 2026-10-30: "we ladder in from aggressive to mark &
        # never worse than mark". (bid + ask) / 2 - the mark data/options_chain and the entry ladder use - FLOORED TO
        # THE CENT, as entry_engine._mark_cap prices the most a buy may post (r224 FLY.1): the raw 1.265 is
        # 1.2650000000000001 in float and limit_at_mark's round(px, 2) booked it 1.27, a half-cent ABOVE the mark.
        prep.contract, prep.bid, prep.ask = k, bid, ask
        prep.premium = int((bid + ask) / 2.0 * 100.0 + 1e-9) / 100.0
        prep.ready = True
        t.anchor(trigger=spot)
        return prep
