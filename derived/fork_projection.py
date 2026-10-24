"""
derived/fork_projection.py  v1.2
v1.2  2026-09-23  OTV4TEST r115 — fork_key delegates to derived.forks.fork_identity (one definition).
THE 1-HOUR PITCHFORK'S RAILS AS A PROJECTION — SEPARATE FROM THE LEVEL BOOK.

v1.1  2026-09-23  OTV4TEST r114 — fork_key is the anchors' PRICES + KINDS, not `idx`,
      which is a position in the rolling frame and shifted every bar.
v1.0  2026-09-23  OTV4TEST LVL.15 step 3 (unlanded WIP, built for review).

🔴 THE OPERATOR'S RULINGS, FINAL:
  · *"The pitchfork is a sloped channel projected over time & may be transient,
    or not present & its presence should be polled every tick. The projection
    is what should inform the Plans that use it. If the pitchfork is absent,
    the plan should be informed that there isn't one. It's a secondary
    contributor of a moving level entirely separate from the historical
    extremes in the level ledger."* (2026-09-22)
  · *"If it's more complicated than that, you're doing it wrong."*
  · For TRADES a rail is *"a valid accept or reject point because of that
    channel being respected, that is a legitimate place to sweep"* — SOFTER
    than a held level (r104: held first, rails after). (2026-09-23)
  · THE TINE RULE (r5, proven at r103): the upper rail is resistance only, the
    lower rail support only, the median by the side price is on; a rail on the
    wrong side of price is NOT a candidate and is never relabelled.
  · A new fork is a new projection (r19): identity is the three anchors.

WHAT IT IS: pure functions over one `analysis.pitchfork.Fork` and the 1h bar
index "now". Nothing is stored and nothing has a level id — a sloped line has no
fixed price to key on (r19's 22 ghost rows came from pretending it did).
HELD/BREACHED at a rail come from `derived/level_rules`, judged against the
rail's price AT EACH CANDLE'S OWN MINUTE — the same rules as a level, the same
module, so "held" means one thing everywhere.

REPLACES `LevelEngine.tines_now` / `rail_projection` / `_fork_key` in
`derived/levels.py`, which lived inside the level engine and therefore could not
be deleted with it.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional, Sequence, Tuple

from derived import level_rules as R

RAILS = ("upper", "median", "lower")
HORIZONS_MIN = (0, 15, 30, 60)


def fork_key(fork) -> Optional[tuple]:
    """The fork's identity: its three anchors (r19). None when there is none."""
    if fork is None:
        return None
    try:
        # r115 — the ONE identity definition lives in the fork's builder
        from derived.forks import fork_identity
        return fork_identity(fork)
    except Exception:                                           # noqa: BLE001
        return None


def rail_at(fork, rail: str, idx: float) -> float:
    return {"upper": fork.upper_at, "median": fork.median_at, "lower": fork.lower_at}[rail](idx)


def role(rail: str, rail_px: float, price: float) -> str:
    """The TINE RULE: upper resistance, lower support, median by price's side."""
    if rail == "upper":
        return R.RESISTANCE
    if rail == "lower":
        return R.SUPPORT
    return R.RESISTANCE if price < rail_px else R.SUPPORT


def oriented(rail: str, rail_px: float, price: float) -> bool:
    """Is this rail a candidate RIGHT NOW? An upper rail below price cannot be
    resistance and is not turned into support; the same for a lower above."""
    if rail == "upper":
        return rail_px > price
    if rail == "lower":
        return rail_px < price
    return True


def projection(fork, idx_now: Optional[float], price: float,
               horizons: Sequence[int] = HORIZONS_MIN) -> dict:
    """What a plan reads every tick. ALWAYS answers — `present: False` when
    there is no fork (an explicit absence, never an empty list to interpret).

    -> {present, fork_key, direction, slope_per_hour,
        rails: {name: {price, role, oriented, at: {minutes: price}}},
        above: nearest ORIENTED rail above price or None,
        below: nearest ORIENTED rail below price or None}
    `at` walks each rail FORWARD along its own slope at a standing price — where
    the RAIL will be, never a forecast of where price goes."""
    if fork is None or idx_now is None:
        return {"present": False, "fork_key": None, "direction": None,
                "slope_per_hour": None, "rails": {}, "above": None, "below": None}
    rails: Dict[str, dict] = {}
    for name in RAILS:
        px = float(rail_at(fork, name, idx_now))
        rails[name] = {"price": px, "role": role(name, px, price),
                       "oriented": oriented(name, px, price),
                       "at": {int(m): float(rail_at(fork, name, idx_now + m / 60.0))
                              for m in horizons}}
    slope = float(fork.slope)

    def _near(up: bool):
        c = [(n, r) for n, r in rails.items() if r["oriented"]
             and (r["price"] > price if up else r["price"] < price)]
        if not c:
            return None
        n, r = min(c, key=lambda x: abs(x[1]["price"] - price))
        gap = r["price"] - price
        # hours for the rail to reach a STANDING price; None when it moves away
        bars = (-gap / slope) if slope else None
        return {"rail": n, "price": r["price"], "role": r["role"],
                "dist_pts": round(abs(gap), 4),
                "dist_pct": round(abs(gap) / price * 100.0, 4) if price else None,
                "hours_to_contact": round(bars, 2) if bars is not None and bars > 0 else None}

    return {"present": True, "fork_key": fork_key(fork),
            "direction": getattr(fork, "direction", None), "slope_per_hour": slope,
            "rails": rails, "above": _near(True), "below": _near(False)}


def rail_edges(fork, rail: str, idx_now: float, ts_now_ms: int
               ) -> Callable[[int], Optional[Tuple[float, float]]]:
    """edges(ts) for `level_rules`: the rail's price at candle `ts`'s OWN minute
    (r19: "recorded at the moment of the interaction, not in hindsight").
    idx(ts) = idx_now + (ts - ts_now) / 1h, the fork's index being 1h bars."""
    def _e(ts: int):
        p = float(rail_at(fork, rail, idx_now + (ts - ts_now_ms) / 3_600_000.0))
        return (p, p)
    return _e


def from_engine(fork_engine, timeframe: str = "1h"):
    """(fork, idx_now) from the live ForkEngine, or (None, None). The engine
    clears both on a failed build, so a dead fork is None here the next tick."""
    if fork_engine is None:
        return None, None
    f = (getattr(fork_engine, "last_forks", {}) or {}).get(timeframe)
    i = (getattr(fork_engine, "last_idx", {}) or {}).get(timeframe)
    return (f, float(i)) if (f is not None and i is not None) else (None, None)
