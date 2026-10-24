"""
execution/resting_stop.py  v1.0
v1.0  2026-10-10  OTV4TEST r266 (STOP.1) — A PREMIUM STOP THAT FIRES RESTS AT ITS OWN LEVEL BEFORE IT CHASES.
      The operator, 2026-10-10 13:08 ET, on the 18,947 that 85 stop/trail exits booked BELOW their own level:
      "post a resting order when our stop is hit, wait for price to come back to it. This can only go 2 ways, it
      deteriorates further and we ladder an emergency stop, OR price fluctuates, as it typically does & we get
      filled"; 13:10 ET: "I can live with a 5% emergency stop on failed fills"; 18:28 ET: "120 seconds is fine";
      13:37 ET: "Yes, to all. Study, fit & apply."
      EVIDENCE (PREREG_MONDAY.md M3, sha 8beecd81): 82 QQQ-TEST exits 09-21..10-09, W 60 s: +4,445, losing days +835
      (49 came back and filled at the level, 32 hit the emergency); W 120 s: +4,361; a BID check on the 8 exits the
      local store holds came out about flat (-70) - the 5 s mid cache is an upper bound, stated.

THE RULE. When a single-leg LONG premium exit fires on its LEVEL - `hard_stop` (stop_premium) or `trail_stop_hit`
(the trail) - the position is not closed at the mark that tick. It RESTS: a sell at the level L.
  · a later tick's mark >= L          -> filled at L                       ("rested: filled at the level")
  · first a mark <= L - 5% of entry   -> closed at that mark (the ladder)  ("rested: emergency")
  · 120 s pass                        -> closed at that mark (the ladder)  ("rested: timeout")
  · the end-of-day close (15:50 on)   -> the rest is abandoned; the hard close governs
PAPER ONLY. Paper books the mark on the first attempt (exit_engine.place_exit_order); this module decides WHICH
price paper books. A LIVE box refuses it (it would need a real resting order at the broker and the live ladder's
own state): RESTING_STOP_MODE=trade on a live box logs a WARNING and behaves as off. Paper sees the mark only once
per tick (15 s), so a touch of L between ticks is MISSED here although a real resting order would fill - the paper
result is conservative on fills, stated.

STATE IS ON DISK (data/resting_stop_state.json, OT_RESTING_STOP_STATE): a restart resumes the rest - nothing a trade
decides on lives only in memory. COUNTERFACTUAL (the operator, 10-10 13:22 ET: "...as long as we have the evidence of
what would have happened had we NOT made the adjustments"): every rest writes a row to
data/counterfactual/resting_stop.jsonl at its start (the mark the old rule booked: the counterfactual, exact) and at
its end (what was booked, and the difference in dollars).
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

import config

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ELIGIBLE_PREFIXES = ("hard_stop", "trail_stop_hit")


def _state_path() -> str:
    return os.environ.get("OT_RESTING_STOP_STATE") or os.path.join(_ROOT, "data", "resting_stop_state.json")


def _cf_path() -> str:
    d = os.environ.get("OT_COUNTERFACTUAL_DIR") or os.path.join(_ROOT, "data", "counterfactual")
    return os.path.join(d, "resting_stop.jsonl")


def _load() -> dict:
    try:
        with open(_state_path()) as fh:
            v = json.load(fh)
        return v if isinstance(v, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(state: dict) -> None:
    p = _state_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh)
    os.replace(tmp, p)


def _row(row: dict) -> None:
    try:
        p = _cf_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception as exc:                                     # noqa: BLE001
        logger.warning("[rest] counterfactual row NOT written: %s", exc)


def active_mode(paper: bool) -> str:
    """'trade' only on a PAPER box with RESTING_STOP_MODE=trade; everything else 'off'."""
    mode = getattr(config, "RESTING_STOP_MODE", "off")
    if mode != "trade":
        return "off"
    if not paper:
        if not getattr(active_mode, "_said", False):
            active_mode._said = True
            logger.warning("[rest] OT_RESTING_STOP=trade REFUSED on a LIVE box - stops close as before "
                           "(paper only until a broker-side resting close is built)")
        return "off"
    return "trade"


def eligible(record, reason: str) -> bool:
    r = (reason or "").strip()
    if not r.startswith(ELIGIBLE_PREFIXES):
        return False
    if record.get("is_butterfly") or record.get("is_condor_leg") or record.get("is_short_position"):
        return False
    if str(record.get("strategy", "")) == "IronCondorStrategy":
        return False
    return True


def level_for(record, reason: str, trail_level: Optional[float] = None) -> Optional[float]:
    if (reason or "").startswith("hard_stop"):
        v = record.get("stop_premium")
    else:
        v = trail_level if trail_level else record.get("trail_stop")
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def is_resting(trade_id: str) -> bool:
    return str(trade_id) in _load()


def begin(record, reason: str, mark: float, level: float, now: Optional[float] = None) -> dict:
    now = time.time() if now is None else float(now)
    entry = float(record.get("entry_premium") or 0.0)
    st = {"level": float(level), "emergency": float(level) - config.RESTING_STOP_EMERGENCY_FRAC * entry,
          "started": now, "reason": reason, "mark_at_trigger": float(mark), "entry_premium": entry,
          "contracts": record.get("contracts")}
    s = _load()
    s[str(record["trade_id"])] = st
    _save(s)
    logger.info("[rest] %s %s fired at mark %.2f - RESTING a sell at %.2f (emergency %.2f, %ds)",
                str(record["trade_id"])[:8], reason.split(" ")[0], mark, level, st["emergency"],
                int(config.RESTING_STOP_WAIT_S))
    _row({"ts_epoch": now, "event": "start", "trade_id": str(record["trade_id"]), "symbol": record.get("symbol"),
          "strategy": record.get("strategy"), "reason": reason, "level": st["level"], "emergency": st["emergency"],
          "mark_at_trigger": st["mark_at_trigger"], "entry_premium": entry, "contracts": record.get("contracts"),
          "option_symbol": record.get("option_symbol"),
          "counterfactual": "the old rule booked mark_at_trigger on this tick"})
    return st


def step(trade_id: str, mark: Optional[float], now: Optional[float] = None) -> Optional[tuple]:
    """None while resting (or no rest); else (price, label, state) for the close to book."""
    st = _load().get(str(trade_id))
    if not st or mark is None:
        return None
    now = time.time() if now is None else float(now)
    m = float(mark)
    if m >= st["level"]:
        return st["level"], "filled at the level", st
    if m <= st["emergency"]:
        return m, "emergency", st
    if now - st["started"] >= config.RESTING_STOP_WAIT_S:
        return m, "timeout", st
    return None


def finish(trade_id: str, price: float, label: str, now: Optional[float] = None) -> None:
    now = time.time() if now is None else float(now)
    s = _load()
    st = s.pop(str(trade_id), None)
    _save(s)
    if not st:
        return
    n = float(st.get("contracts") or 0)
    diff = (float(price) - st["mark_at_trigger"]) * n * config.CONTRACT_MULTIPLIER
    _row({"ts_epoch": now, "event": "end", "trade_id": str(trade_id), "outcome": label, "booked": float(price),
          "mark_at_trigger": st["mark_at_trigger"], "level": st["level"], "waited_s": round(now - st["started"], 1),
          "usd_vs_old_rule": round(diff, 2)})
    logger.info("[rest] %s %s: booked %.2f vs %.2f at the trigger (%+.2f $ against the old rule) after %.0fs",
                str(trade_id)[:8], label, price, st["mark_at_trigger"], diff, now - st["started"])


def abandon(trade_id: str, why: str) -> None:
    """The end-of-day close or a vanished record: drop the rest (the counterfactual row says so)."""
    s = _load()
    st = s.pop(str(trade_id), None)
    if st is None:
        return
    _save(s)
    _row({"ts_epoch": time.time(), "event": "abandoned", "trade_id": str(trade_id), "why": why,
          "mark_at_trigger": st["mark_at_trigger"], "level": st["level"]})
    logger.info("[rest] %s rest abandoned: %s", str(trade_id)[:8], why)
