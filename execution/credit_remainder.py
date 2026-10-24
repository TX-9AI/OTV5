"""
execution/credit_remainder.py  v1.0
v1.0  2026-09-08  r315 — THE UNFILLED REMAINDER OF A PARTIAL KEEPS WALKING.

THE DEFECT THIS EXISTS FOR, war-gamed 2026-09-08 on synthetic tape against
HEAD 0498534: a credit vertical that PARTIAL-filled on a rung had the filled
part booked, the remainder CANCELLED at the broker, and its ladder walk left in
`ladder_registry` with a comment (main.py 2332) saying the remainder "must
resume one rung further in". Nothing could honour that: the next tick
`has_open_position()` was True, the box took the manage branch, and every
credit strategy was `_plan_skip`'d. The remainder had no order and no caller.
The trade ran undersized for the session and the walk sat in the registry
until the 3600s stale sweep.

THE OPERATOR'S DEFINITION, which this file implements literally:
  · a refusal is "didn't completely fill at that price"
  · "the filled part is a real position and is booked; the rest walks on from
    the next rung" (ladder_registry.refuse, r104)
  · nothing rests at the broker — every rung is posted, confirmed to a per-rung
    deadline, and cancelled if it did not fill (TRADES.md §6)
  · a live confirmation that has not filled "keeps being offered every tick
    until its own window closes" (WORKING_AGREEMENT §37)

THE SHAPE, mirrored from ORB's `_supervise_offers` (r195): supervised from
BEFORE the `has_open_position()` split, because the thing being supervised is
exactly what that split hides. One `Remainder` per open credit record that
still has unfilled size. Each tick, if the parent is still open and the
strategy's entry window is still open, ONE rung is posted for the remaining
quantity through the SAME `_post_credit_vertical` the entry used — same
ladder key, so the ratchet is the one the entry earned — and any fill is
ACCRETED into the existing record: contracts, blended entry_premium, and the
max_loss / total_cost / stop_premium that are arithmetic on those two. One
position at the broker, one row in trades.db, one record under management.

⚠️ WHAT ENDS A REMAINDER, in the order checked:
  1. the parent record is no longer open   → the thesis is done; abandon
  2. the strategy's entry window has closed → §37's own time gate; abandon
  3. the hard-close window is open          → abandon
  4. remaining reaches zero                 → complete; clear the walk
Every abandonment logs at WARNING with the count that never filled, so an
undersized position is a stated fact and not a quiet one.

⚠️ IN-MEMORY, LOST ON RESTART — DELIBERATELY AND RECORDED. The filled part is
already at the broker and in trades.db, so a restart loses only the INTENT to
fill more; nothing phantom survives and nothing is double-booked. That is the
same posture TRADES.md records for `LadderState` itself. WORKING_AGREEMENT §22
says state that must survive a restart rides a column; this state MAY die
with the process, and the cost is one undersized position on a mid-session
restart, logged.

⚠️ PAPER NEVER REGISTERS ONE. Paper fills 100% at mark (limit_ladder) and has
no partial-fill model — a remainder there would be inventing evidence.

⚠️ THE STRIKES ARE FROZEN AT REGISTRATION. The remainder completes THE
STRUCTURE THAT PARTIALLY FILLED, at whatever the ladder will now get for it;
it never re-selects strikes. Re-selection is the strategy's job on a fresh
entry, and a second structure on the same side is exactly the hybrid the
operator asked about — `_can_open_credit_spread` refuses it and this module
never asks.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_REMAINDERS: Dict[str, "Remainder"] = {}


@dataclass
class Remainder:
    key:           str          # the ladder intent key the entry walked on
    trade_id:      str
    record:        dict         # the SAME object the position manager holds
    short_symbol:  str
    long_symbol:   str
    short_strike:  float
    long_strike:   float
    side:          str          # "call" / "put"
    strategy:      str
    requested:     int
    remaining:     int
    stop_pct:      float        # 0.0 = no premium stop (TCS); else the lone floor
    window_end_et: Tuple[int, int]
    registered_at: float = field(default_factory=time.time)
    fills:         int = 0      # supervision passes that filled something


def register(rem: Remainder) -> None:
    """A partial just booked; the rest is now an open intent."""
    _REMAINDERS[rem.key] = rem
    logger.warning("[remainder] %s %s: %d/%d filled — %d still to fill on %s/%s, "
                   "walking until %02d:%02d ET or the position closes",
                   rem.strategy, rem.side, rem.requested - rem.remaining,
                   rem.requested, rem.remaining, rem.short_symbol,
                   rem.long_symbol, *rem.window_end_et)


def active() -> List[Remainder]:
    return list(_REMAINDERS.values())


def drop(key: str, why: str) -> Optional[Remainder]:
    rem = _REMAINDERS.pop(key, None)
    if rem is not None:
        if rem.remaining > 0:
            logger.warning("[remainder] %s %s ABANDONED with %d/%d never filled: %s",
                           rem.strategy, rem.side, rem.remaining, rem.requested, why)
        else:
            logger.info("[remainder] %s %s complete (%d/%d): %s",
                        rem.strategy, rem.side, rem.requested, rem.requested, why)
    return rem


def reset_all() -> None:
    """Session reset only."""
    _REMAINDERS.clear()


def accrete(rem: Remainder, filled: int, credit: float,
            trade_logger=None, multiplier: int = 100) -> dict:
    """Fold `filled` more contracts at `credit` into the parent record.

    Blends the basis and recomputes the three fields that are arithmetic on
    (contracts, credit). Mirrors main._execute_condor_leg's own construction:
    max_loss = (width - credit) * contracts * multiplier; total_cost = max_loss;
    stop_premium = credit * (1 + stop_pct), or 0.0 when the structure carries
    no premium stop. Persists through `trade_logger.log_accretion` when given.
    """
    rec = rem.record
    n1 = int(rec.get("contracts") or 0)
    c1 = float(rec.get("entry_premium") or 0.0)
    n2 = int(filled)
    c2 = float(credit)
    n  = n1 + n2
    c  = ((n1 * c1) + (n2 * c2)) / n if n > 0 else c2
    width    = abs(float(rem.short_strike) - float(rem.long_strike))
    max_loss = (width - c) * n * multiplier
    stop     = 0.0 if not rem.stop_pct else c * (1.0 + float(rem.stop_pct))
    rec["contracts"]     = n
    rec["entry_premium"] = c
    rec["max_loss"]      = max_loss
    rec["total_cost"]    = max_loss
    rec["stop_premium"]  = stop
    rem.remaining = max(0, rem.remaining - n2)
    rem.fills += 1
    if trade_logger is not None:
        trade_logger.log_accretion(rem.trade_id, n, c, max_loss, max_loss, stop)
    logger.info("[remainder] %s %s accreted +%d @ %.4f -> %d @ blended %.4f "
                "(max_loss %.2f, stop %.4f); %d remaining",
                rem.strategy, rem.side, n2, c2, n, c, max_loss, stop, rem.remaining)
    return rec


def _parent_open(trade_id: str, open_ids: Optional[set]) -> bool:
    if open_ids is None:
        return True          # cannot read the book this tick: do not abandon on a read failure
    return trade_id in open_ids


def supervise(chain, now_hm: Tuple[int, int], eod: bool, paper: bool,
              open_trade_ids: Optional[set],
              place: Callable, trade_logger=None,
              multiplier: int = 100) -> int:
    """One supervision pass. Returns how many remainders filled something.

    `place(short_contract, long_contract, qty, key, structure)` must return
    (fill, limit, why) where fill has .filled / .quantity / .net_price — the
    entry path's own `_post_credit_vertical`, so the remainder walks the same
    ladder the entry did.
    """
    if paper or not _REMAINDERS:
        return 0
    booked = 0
    for key, rem in list(_REMAINDERS.items()):
        if not _parent_open(rem.trade_id, open_trade_ids):
            drop(key, "parent position closed"); continue
        if now_hm >= tuple(rem.window_end_et):
            drop(key, f"entry window closed at {rem.window_end_et[0]:02d}:"
                      f"{rem.window_end_et[1]:02d} ET"); continue
        if eod:
            drop(key, "hard-close window open"); continue
        if rem.remaining <= 0:
            drop(key, "nothing left to fill"); continue

        short = long = None
        try:
            pool = (getattr(chain, "puts" if rem.side == "put" else "calls", None)
                    or [])
            short = next((c for c in pool if getattr(c, "symbol", "") == rem.short_symbol), None)
            long  = next((c for c in pool if getattr(c, "symbol", "") == rem.long_symbol), None)
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[remainder] %s: chain read failed (%s)", key, exc)
        if short is None or long is None:
            logger.info("[remainder] %s: structure not on this tick's chain — retry next tick", key)
            continue

        try:
            fill, limit, why = place(short, long, rem.remaining, key,
                                     f"{rem.short_symbol}|{rem.long_symbol}")
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[remainder] %s: post failed (%s) — retry next tick", key, exc)
            continue
        if fill is None or not getattr(fill, "filled", False) \
                or int(getattr(fill, "quantity", 0) or 0) <= 0 \
                or getattr(fill, "net_price", None) is None:
            continue          # the placer already refused the rung
        accrete(rem, int(fill.quantity), float(fill.net_price),
                trade_logger=trade_logger, multiplier=multiplier)
        booked += 1
        if rem.remaining <= 0:
            drop(key, "filled in full")
    return booked
