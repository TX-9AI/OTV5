"""
derived/level_rules.py  v1.0
THE OPERATOR'S DEFINITIONS OF HELD AND BREACHED — ONE PLACE, PURE FUNCTIONS.

v1.0  2026-09-23  OTV4TEST LVL.15 step 1 (unlanded WIP, built for review).

🔴 WHY THIS FILE EXISTS. On 2026-09-22 the tree carried THREE definitions of
"breached": the level engine's two closes (`derived/levels.py`), the exit
engine's "two closes beyond the pool", and `is_spent`'s trade-exit lock — and
the TCS's trigger was structurally dead because acceptance retired the level
in the same step. The operator ruled the levels rebuilt from scratch and gave
the definitions; this module is the ONLY place they are written. The level
book, the fork projection, the exit engine and the management plans import it.

THE DEFINITIONS, VERBATIM (2026-09-22 / 09-23, final — do not re-ask):
  · HELD — *"Price wicked into the Level or zone and failed to claim beyond
    it."* "Wicked into" = the wick REACHES the near edge (high >= resistance,
    low <= support); no tolerance, no depth ("Correct", 09-23). A close beyond
    whose NEXT candle opens back inside is HELD, declared at the close back on
    the level's side ("Correct", 09-23).
  · BREACHED — *"Price was accepted beyond the level or zone, as evidenced by
    the closure of a 1-min candle beyond the level/zone [and the] start of a
    one minute candle formation on the pierced side beyond the level's
    extreme."* A 1m close beyond the FAR edge, then the next 1m OPEN beyond it.
  · A ZONE *"stays live until the far edge is accepted"* (09-23) — a close
    INSIDE a zone does not retire it (r39's "a zone containing spot is
    finished" is superseded).
  · NO grading, NO depth tiers, NO touch counting, NO tolerance band.

  · A CLOSE INSIDE A ZONE IS NOT HELD (operator, 2026-09-23: "Yes, b"). HELD
    needs the close back OUTSIDE the zone, on the near side; a close inside
    keeps the episode open until price closes back out (HELD) or is accepted
    beyond the far edge (BREACHED). It was put to him as (a) "short of the far
    edge is HELD" versus (b), because it decides WHEN the sweep may fire: under
    (a) a spread could be sold while price is still working the zone. There is
    deliberately NO switch — a ruled definition is not a dial. For a single
    level near == far and the two readings never differed.

EDGES. For a RESISTANCE the near edge is the zone's bottom and the far edge its
top; SUPPORT is mirrored. A single level has near == far == its price. A RAIL
(the fork projection) passes a callable so each candle is judged against the
rail's price AT THAT CANDLE'S OWN MINUTE — a sloped line has no fixed price.

EPISODES, per closed 1m candle, in order:
  1. if the previous candle CLOSED beyond the far edge, THIS candle's OPEN
     decides: beyond -> BREACHED (stamped at this candle); inside -> the
     episode simply continues.
  2. the wick reaches the near edge -> an episode is open (TESTED).
  3. the candle CLOSES beyond the far edge -> pending (step 1 on the next).
  4. else, an episode is open and the candle closes on the HELD side ->
     HELD (stamped at this candle); the episode ends, the next test opens a
     new one.
Nothing here reads a clock, a store or a config: the same candles give the
same answer on every box, every restart and every replay.
"""
from __future__ import annotations

from typing import Callable, Iterable, List, Optional, Sequence, Tuple, Union

RESISTANCE, SUPPORT = "resistance", "support"

# A candle: (ts, open, high, low, close). `ts` is whatever the caller keys on
# (epoch ms in the book); it is only ever echoed back, never interpreted.
Bar = Tuple[int, float, float, float, float]
Edges = Union[Tuple[float, float], Callable[[int], Optional[Tuple[float, float]]]]

HELD, BREACHED, TESTED = "HELD", "BREACHED", "TESTED"


def edges_of(lo: float, hi: float, side: str) -> Tuple[float, float]:
    """(near, far) for a zone spanning lo..hi (lo == hi for a single level)."""
    lo, hi = (float(lo), float(hi)) if lo <= hi else (float(hi), float(lo))
    if side == RESISTANCE:
        return lo, hi
    if side == SUPPORT:
        return hi, lo
    raise ValueError(f"side must be {RESISTANCE!r} or {SUPPORT!r}, got {side!r}")


def reaches(high: float, low: float, near: float, side: str) -> bool:
    """The wick reaches the near edge — the TEST. No tolerance (ruled)."""
    return high >= near if side == RESISTANCE else low <= near


def beyond(price: float, far: float, side: str) -> bool:
    """Strictly past the far edge — a close or an open that claims beyond it."""
    return price > far if side == RESISTANCE else price < far


def held_side(close: float, near: float, side: str) -> bool:
    """The close is back OUTSIDE on the near side — ruled (b), 2026-09-23."""
    return close <= near if side == RESISTANCE else close >= near


class Episode:
    """ONE object's judgement, advanced one CLOSED 1m candle at a time. The live
    engine steps it per candle; `judge()` steps it over a list. One
    implementation of the rules, two ways of feeding it.

    ⚠️ `dead` is terminal: a breached level or zone never speaks again."""
    __slots__ = ("side", "episode", "pending", "dead")

    def __init__(self, side: str):
        if side not in (RESISTANCE, SUPPORT):
            raise ValueError(f"side must be {RESISTANCE!r} or {SUPPORT!r}, got {side!r}")
        self.side = side
        self.episode = False
        self.pending = False
        self.dead = False

    def step(self, bar: Bar, edges: Optional[Tuple[float, float]]) -> List[str]:
        """Events this candle produces, in order (TESTED, HELD, BREACHED)."""
        if self.dead:
            return []
        if edges is None:                     # the object is not there this minute
            self.episode = self.pending = False
            return []
        _ts, o, h, l, c = bar
        near, far = edges
        out: List[str] = []
        if self.pending:
            self.pending = False
            if beyond(o, far, self.side):
                self.dead = True
                return [BREACHED]
        if not self.episode and reaches(h, l, near, self.side):
            self.episode = True
            out.append(TESTED)
        if beyond(c, far, self.side):
            self.pending = True
            self.episode = True               # a close beyond is inside an episode by definition
            return out
        if self.episode and held_side(c, near, self.side):
            out.append(HELD)
            self.episode = False
        return out


def judge(bars: Iterable[Bar], edges: Edges, side: str) -> List[Tuple[str, int]]:
    """Every TESTED / HELD / BREACHED event over `bars`, in order; stops at the
    breach (a breached level or zone is dead). -> [(event, ts)].

    `edges` is (near, far), or a callable ts -> (near, far) | None for a moving
    rail (None = no rail at that minute: nothing is judged and any open
    episode or pending breach is dropped, because the object it referred to
    is gone)."""
    ep = Episode(side)
    out: List[Tuple[str, int]] = []
    for bar in bars:
        e = edges(bar[0]) if callable(edges) else edges
        for ev in ep.step(bar, e):
            out.append((ev, bar[0]))
        if ep.dead:
            break
    return out


def first(events: Sequence[Tuple[str, int]], kind: str) -> Optional[int]:
    """The ts of the first `kind` event, or None."""
    return next((ts for k, ts in events if k == kind), None)
