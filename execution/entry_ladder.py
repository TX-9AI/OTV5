"""
execution/entry_ladder.py  v4.3
v4.3  2026-09-27  OTV4TEST r164 — NO ORDER IS EVER PRICED AT $0.00. The operator,
      2026-09-27: "We can NEVER bid or ask $0.00 — this is the one time that we
      may have to cross Mark. On our ladder exit and entries ... if Mark is ever
      zero, we have to skip that rung and go to the next one. This is the ONLY
      exception for getting a worse fill than mark." and "Entry AND exit ladder."
      MEASURED on this code before the fix: a BUY into a 0.00/0.01 book posted
      rungs [0.00], into 0.00/0.02 [0.00, 0.01] - the first post $0.00. Exits walk
      this same LadderState through ladder_registry.price_for, so a buy-to-close of
      a cheap short, or of a combo whose net quote straddles zero (position_manager
      clamps the negative net bid to 0.00 - "debit or credit?"), opened at $0.00.
      Now a rung at or below zero is SKIPPED; when nothing is left the price is ONE
      VENUE INCREMENT (0.01 penny / 0.05 nickel) - worse than mark, and the only
      place this file allows that. Sells snap UP and never reach zero; a dead
      0.00/0.00 book still returns [] and every caller floors it at one tick.
v4.2  2026-09-08  r315 — THE WALK BELONGS TO THE INTENT, NOT TO A STRIKE PAIR.
      `LadderState.next_price` takes an optional `structure` tag. When the tag
      CHANGES mid-walk — the strategy re-selected its strikes because spot
      moved — the RUNG carries and the PRICE RATCHET is dropped. War-gamed
      2026-09-08 on synthetic tape: TCS picks the nearest OTM strike from
      CURRENT price every tick, so on a tape crossing one strike per tick the
      old strike-pair key started a fresh walk at rung 1 on every pair and
      posted rung 1 or 2 five times in eight ticks without ever reaching mark —
      the "hopeless attempt" the 25% start exists to avoid, repeated per
      strike. Rung carries because the operator's rule is one increment per
      tick TOWARD MARK until it fills; the ratchet is dropped because a credit
      refused on one pair says nothing about the fair credit of another. A
      call with no `structure` behaves exactly as v4.1.
v4.1  2026-08-24  r99 — next_price's rule-3 clamp returned the RAW mark; it now
      returns mark snapped to the grid in our favour, like the terminal rung.

The entry ladder: start 25% in from the best price, step ONE VENUE INCREMENT
toward mark, never worse than mark, and never re-offer a refused price.

v4.0  2026-08-20  Built at the OTV4 split. Operator's spec, read back and
confirmed.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

════════════════════════════════════════════════════════════════════════════
WHY FILL QUALITY OUTRANKS EVERY SELECTION LEVER
════════════════════════════════════════════════════════════════════════════
FRC.1 measured the fleet's gross edge at **+$2.70/trade against $126/trade of
round-trip friction - about 2% of the spread it trades in.** Capturing half the
half-spread on entry is worth on the order of **$31/trade**. **Fill quality is
an order of magnitude larger than anything on the trade-selection list**, and
this file is where it is captured or given away.

════════════════════════════════════════════════════════════════════════════
THE SPEC, IN THE OPERATOR'S OWN EXAMPLES
════════════════════════════════════════════════════════════════════════════
Spread 1.00 (bid 0.00 / ask 1.00, mark 0.50), SELLING:
  · $0.05 increments -> start .75, then .70 .65 .60 .55 .50   (six rungs)
  · $0.10 increments -> start .70, then .60 .50               (three rungs)

**Granularity falls out of the venue increment, not a fraction list.** A tighter
grid gives more rungs and more chances at a better fill. The v3 ladder used a
FIXED `[0.50, 0.25, 0.00]` and could not express that: on a dime grid it posted
three prices whether or not more were available, and on a penny grid it skipped
dozens of postable levels between them.

⚠️ 25% AND NOT 50%. Operator: *"always start at 25% of best price to not waste a
lot of time on hopeless attempts."* The half-spread opener spent a fill window
on a price the book was never going to take.

⚠️ .75 -> .70 ON A DIME GRID ROUNDS **TOWARD MARK**, deliberately. v3's
`round_to_increment` rounded a sell UP - away from mark - reasoning that
nearest-rounding would make half the rungs more aggressive than specified. That
is the right instinct for a rung you intend to hold, and the wrong one for an
OPENING rung whose entire purpose is to be plausible. Rounding away from mark
recreates the hopeless attempt the 25% start exists to avoid.

════════════════════════════════════════════════════════════════════════════
THE THREE RULES, AND THEY COMPOSE IN THIS ORDER
════════════════════════════════════════════════════════════════════════════
1. **RATCHET.** The rung index only ever advances. Operator: *"If it's not
   accepting 80 at the first attempt, it won't accept 80 at the next attempt as
   price fluctuates - 80 is off the table."* A refused price never returns, even
   if the market moves back through it.

   ⚠️ THIS IS THE RULE v3 DID NOT HAVE. `entry_ladder_prices` recomputed every
   rung from the LIVE quote each cycle, so a mark that drifted up could place
   rung 2 at or above rung 1 - re-offering a level already refused and burning
   the fill window on it.

2. **REPRICE.** Each attempt recomputes from the CURRENT mark, not the
   entry-time one. A ladder anchored to a stale mark chases a market that has
   already left.

3. **MARK FLOOR - never post worse than mark.** Operator: *"If Mark ever turns
   out to be better than our first offer or subsequent offers, take Mark."*
   Selling posts `max(rung, mark)`; buying posts `min(rung, mark)`.

   ⚠️ THIS RESOLVES THE CONFLICT BETWEEN 1 AND 2. If the mark rises past the
   last refusal, the ratchet alone would hold the order BELOW mark - posting
   worse than the market is offering. The floor takes mark instead, which is the
   terminal rung anyway, so the ladder simply arrives there early. **On a market
   moving in your favour this collapses to mark and fills. That is correct: the
   rungs only ever existed to try for BETTER than mark.**

⚠️ AND IT APPLIES TO EVERY ORDER - debits and credits alike, every strategy.
Not a per-strategy option.
"""

import logging
import math
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

START_FRACTION = 0.25          # 25% in from the best price
MAX_RUNGS = 24                 # a penny grid on a wide quote could go forever


def _increment(symbol: str, price: float, bid: float, ask: float) -> float:
    """The venue's increment. Resolved from the quote where possible.

    ⚠️ THE QUOTE IS BETTER EVIDENCE THAN THE HARDCODED LIST. `tick_size.resolve`
    prefers a venue rule, then PROVES penny eligibility from the observed book,
    and only then falls back to `PENNY_CLASSES` - which FRC.2's own notes call
    "a STARTING list ... unverified - membership is a broker/OCC fact, not
    derivable here", and whose own log calls it the path that should not be
    reached.
    """
    try:
        from execution.tick_size import resolve
        inc, _src = resolve(symbol, price, bid, ask)
        return float(inc) if inc and inc > 0 else 0.05
    except Exception:                                          # noqa: BLE001
        return 0.05


def _snap_toward_mark(px: float, mark: float, inc: float) -> float:
    """Round to the venue grid, TOWARD mark. See the header on why."""
    if inc <= 0:
        return round(px, 2)
    if px > mark:
        return math.floor(px / inc + 1e-9) * inc      # a sell rung: come down
    if px < mark:
        return math.ceil(px / inc - 1e-9) * inc       # a buy rung: come up
    return round(mark / inc) * inc


def _snap_in_our_favour(px: float, inc: float, sell: bool) -> float:
    """Snap `px` to the venue grid IN OUR FAVOUR — up selling, down buying."""
    if inc <= 0:
        return round(px, 2)
    if sell:
        return math.ceil(px / inc - 1e-9) * inc
    return math.floor(px / inc + 1e-9) * inc


def _snap_mark_in_our_favour(mark: float, inc: float, sell: bool) -> float:
    """The TERMINAL rung: mark, snapped to the grid IN OUR FAVOUR.

    🔴 r98 — THE MARK RUNG COULD LAND WORSE THAN MARK, WHICH BREAKS THE ONE
    RULE THE OPERATOR STATED MOST FIRMLY. `_snap_toward_mark` fell through to
    NEAREST rounding when `px == mark`, so a mark on a half-cent snapped the
    wrong way: NFLX bid 0.45 / ask 0.50 gave a BUY table of [0.47, 0.48] with
    mark 0.475 — the terminal rung paying a cent ABOVE mark.

    ⚠️ AND THE CLAMP COULD NOT SAVE IT. Rule 3 in `next_price` clamps a buy to
    `mark` — 0.475 — which is UNPOSTABLE on a penny grid. The venue rejects it
    or silently adjusts it, and `tick_size.py` says exactly what that costs:
    "a silently adjusted limit is a fill at a price nobody chose with nothing
    in the logs to explain it."

    ⚠️ SO THE TERMINAL RUNG ROUNDS IN OUR FAVOUR. Operator, 2026-08-24: "always
    round in our favour." Buying takes the grid price at or BELOW mark; selling
    takes the grid price at or ABOVE mark. Worst case we post exactly mark when
    mark is already on the grid; otherwise we keep the fraction of a cent
    instead of giving it away. On a 5c spread half a cent is 10% of the
    half-spread, on the rung most likely to fill.

    ⚠️ THIS IS THE TERMINAL RUNG ONLY. The intermediate rungs still snap TOWARD
    mark, deliberately — see the header: rounding an OPENING rung away from
    mark "recreates the hopeless attempt the 25% start exists to avoid."
    """
    if inc <= 0:
        return round(mark, 2)
    if sell:
        return math.ceil(mark / inc - 1e-9) * inc     # receive at least mark
    return math.floor(mark / inc + 1e-9) * inc        # pay at most mark


def rungs(bid: float, ask: float, side: str, symbol: str = "") -> list:
    """Every price this ladder will post, in order, ending at mark.

    Returns [] on an unusable quote - crossed, zero or missing. **An empty
    ladder means the caller posts at mark**, never at a guess.
    """
    # ⚠️ float() ACCEPTS NaN AND inf. The stress test crashed here with
    # "cannot convert float NaN to integer" inside the snap - a raise that
    # `_safe_strategy` would have logged as "no signal", hiding it entirely.
    from utils.math_utils import safe_float
    b, a = safe_float(bid), safe_float(ask)
    # 🔴 r98 — A ZERO BID IS A USABLE QUOTE AND THE OLD GUARD KILLED THE LADDER
    # IN THE EXACT CASE ITS OWN HEADER SPECIFIES. `b <= 0` rejected bid 0.00 /
    # ask 1.00 — which is the operator's worked example three inches above this
    # line — so `rungs()` returned [] and the caller fell back to posting at
    # mark. Inert precisely on the widest spreads, where the six rungs are worth
    # the most, and invisible because nothing has ever called this module.
    # ⚠️ THE ZERO IS THE MARKET'S BID, NOT OUR OFFER. Operator, 2026-08-24:
    # "We don't ever bid 0, that's not the intent. We bid 25% of the DISTANCE to
    # Ask." Selling into a 0.00/1.00 book starts at 0.75 and walks to mark 0.50;
    # buying starts at 0.25 and walks up. Nothing about that needs a bid.
    # A zero bid is ROUTINE on cheap 0DTE, so this was not an edge case.
    # What genuinely IS unusable: a missing quote, a non-positive ASK (no offer
    # to work against), or a CROSSED book.
    if b is None or a is None or a <= 0 or b < 0 or a < b:
        return []

    mark = (a + b) / 2.0
    spread = a - b
    if spread <= 0:
        return [round(mark, 4)]

    inc = _increment(symbol, mark, b, a)
    sell = str(side).lower().startswith("s")

    # 25% in from the BEST price - the ask when selling, the bid when buying.
    # 🔴 r98 — THE 25% IS A TARGET, NOT A GRID POSITION, AND THE SNAP GOES IN
    # OUR FAVOUR. Operator, 2026-08-24: "If we're SELLING offer it at 80% of
    # ASK, then 70, 60, stop at 50 (mark)."
    # On a DIME grid, bid 0.00 / ask 1.00: the 25% target is 0.75, which is not
    # postable. Snapping TOWARD MARK gave 0.70 and opened by conceding 30% of
    # the spread before the book had refused anything. Snapping IN OUR FAVOUR
    # gives 0.80 and the walk becomes 0.80 -> 0.70 -> 0.60 -> 0.50: one extra
    # rung, and every rung a better price.
    # ⚠️ IT COSTS NOTHING WHEN THE TARGET IS POSTABLE. On a NICKEL grid the 25%
    # target IS on the grid, so the opener stays 0.75 and the operator's
    # original six-rung example is unchanged: .75 .70 .65 .60 .55 .50.
    # ⚠️ AND IT DOES NOT REVIVE THE HOPELESS ATTEMPT THE HEADER WARNS ABOUT.
    # That warning is about opening SO FAR from mark that the book was never
    # going to take it; one increment better than a 25% standoff is not that,
    # and the ratchet still walks it in on the very next tick.
    start = (a - spread * START_FRACTION) if sell else (b + spread * START_FRACTION)
    start = _snap_in_our_favour(start, inc, sell)

    out, px = [], start
    for _ in range(MAX_RUNGS):
        # ⚠️ NEVER PAST MARK. Mark is the terminal rung, not a waypoint.
        if (sell and px <= mark) or ((not sell) and px >= mark):
            break
        r = round(px, 4)
        if r not in out:
            out.append(r)
        px = px - inc if sell else px + inc

    # r98 — the terminal rung is mark snapped IN OUR FAVOUR, never nearest.
    m = round(_snap_mark_in_our_favour(mark, inc, sell), 4)
    if m not in out:
        out.append(m)
    # 🔴 r164 — NEVER $0.00. A rung at or below zero is SKIPPED to the next; if
    # that empties the table (a buy into 0.00/0.01), the one rung is ONE VENUE
    # INCREMENT - worse than mark, the operator's ONLY ruled exception.
    out = [r for r in out if r > 1e-9]
    if not out:
        out = [round(inc, 4)]
    return out


class LadderState:
    """One order's walk down the ladder. Carries the ratchet.

    ⚠️ STATE IS THE POINT. A stateless ladder recomputed from the live quote
    re-offers refused prices when the mark drifts - which is exactly what v3
    did, and why a refusal cost more than one fill window.
    """

    def __init__(self, side: str, symbol: str = ""):
        self.side = str(side).lower()
        self.symbol = symbol
        self.rung = 0
        self.best_refused: Optional[float] = None
        # v4.2 — which STRUCTURE the ratchet was earned on. None until a caller
        # tags one; a caller that never tags keeps v4.1 behaviour exactly.
        self.structure: Optional[str] = None

    def next_price(self, bid: float, ask: float,
                   structure: Optional[str] = None) -> Optional[Tuple[float, str]]:
        """(price, why) for the next attempt, or None when the quote is unusable.

        Call once per attempt. Advancing the rung is `refuse()`'s job, so a
        caller that re-reads the price without refusing gets the same rung -
        repricing to the current mark, which is rule 2.

        `structure` (v4.2) identifies WHAT is being priced — for a vertical,
        its short/long symbols. When it differs from the structure the ratchet
        was earned on, the rung index is KEPT (the walk keeps stepping toward
        mark; it never restarts at the 25% opener) and `best_refused` is
        DROPPED (a refusal on the old strikes is not evidence about the new
        ones). Rule 3 still clamps the carried rung to mark on the new table.
        """
        if structure is not None and self.structure is not None \
                and structure != self.structure:
            logger.info("[ladder] %s structure changed %s -> %s: rung %d carries, "
                        "ratchet %s dropped", self.symbol, self.structure,
                        structure, self.rung, self.best_refused)
            self.best_refused = None
        if structure is not None:
            self.structure = structure
        table = rungs(bid, ask, self.side, self.symbol)
        if not table:
            return None
        sell = self.side.startswith("s")
        mark = (float(ask) + float(bid)) / 2.0

        idx = min(self.rung, len(table) - 1)
        px = table[idx]
        why = f"rung {idx + 1}/{len(table)}"

        # ── rule 1: the ratchet. A refused price never returns. ─────────────
        if self.best_refused is not None:
            inc = _increment(self.symbol, mark, bid, ask)
            if sell and px >= self.best_refused - 1e-9:
                px = self.best_refused - inc
                why += " (ratcheted below a refusal)"
            elif (not sell) and px <= self.best_refused + 1e-9:
                px = self.best_refused + inc
                why += " (ratcheted above a refusal)"

        # ── rule 3: never worse than mark. If mark is better, TAKE MARK. ────
        # r99 — TAKE MARK SNAPPED IN OUR FAVOUR. r98 fixed the terminal rung in
        # `rungs()` but this clamp still returned the RAW mark (0.475 on a
        # penny grid): unpostable, and exactly the price the r98 comment above
        # says "the clamp could not save".
        if sell and px < mark:
            px = _snap_mark_in_our_favour(mark, _increment(self.symbol, mark, bid, ask), True)
            why = "mark (better than the rung)"
        elif (not sell) and px > mark:
            px = _snap_mark_in_our_favour(mark, _increment(self.symbol, mark, bid, ask), False)
            why = "mark (better than the rung)"

        # 🔴 r164 — NEVER $0.00, whatever rule 1 or rule 3 produced (a sub-tick
        # mark snapped down in our favour is 0.00 on a buy). One increment is
        # the ruled exception: "skip that rung and go to the next one."
        if px <= 1e-9:
            px = _increment(self.symbol, mark, bid, ask)
            why += " (a $0.00 rung skipped: one increment, the ruled exception)"
        return round(px, 4), why

    def refuse(self, price: float):
        """Record a refusal and advance. Called when an attempt does not fill."""
        try:
            p = float(price)
        except (TypeError, ValueError):
            return
        sell = self.side.startswith("s")
        if self.best_refused is None:
            self.best_refused = p
        elif sell:
            self.best_refused = min(self.best_refused, p)
        else:
            self.best_refused = max(self.best_refused, p)
        self.rung += 1
