"""
analysis/session_map.py  v1.1
v1.1  2026-09-03  r231 — 🔴 GEOMETRY NOW ASKS ROLE-vs-PRICE, NOT ONLY
      ROLE-vs-RANGE. Operator, 2026-09-03: *"an upper tine can only be
      resistance and a lower tine can only be support. Therefore an upper tine
      below the current price cannot be resistance, and a lower tine above
      price can never be support. Those are invalidated by geometry."*
      ⚠️ THE RANGE TESTS DID NOT COVER THIS. A ceiling between `orb_high` and
      spot passed every one of them — not inside the range, not below
      `orb_low` — while price had already traded through it. The range asks
      where a level sits relative to 09:35; this asks where it sits relative
      to NOW, and only the second can invalidate a level price has traversed.
      🔑 `spot` IS A REQUIRED KEYWORD. An optional one is a rule a caller can
      drop in silence — r230's getattr default wearing a signature. Missing or
      unusable spot returns None (unmeasured), and None is never a pass.
      ⚠️ The in-range rule the operator also asked for was ALREADY HERE and is
      unchanged — *"neither above nor below it, so it is neither a ceiling nor
      a floor this session"* — reported rather than rebuilt.
      `check_geometry` and `build_session_map` thread `spot` through; neither
      has a production caller outside this file, so the change is contained.
v1.0  2026-08-26  r146 — MIGRATED out of `derived/plans.py` (r126-r145), where
      the operator's ruling lived inside a mirror of the strategies that no
      strategy ever read. It now lives where the strategies can call it, and
      `strategy/plan.py` consults it on every credit-spread level before a
      short strike is priced. Logic is the ruling verbatim; the only change is
      that it is CONSUMED.

THE SHARED SESSION MAP — the geometry that invalidates a level.

🔴 THE CENTER IS THE 5-MINUTE ORB RANGE, NOT THE OPENING PRICE. Operator,
2026-08-25: *"Why don't we use the five minute ORB range as the marker? Levels
have to be above the ORB or below to count and they have to be the right
kind."* A ZONE rather than a POINT: a level a few cents from the open is not
meaningfully above or below anything, and the first five minutes routinely
straddle it. A level OUTSIDE the opening range has actually been left behind
by the session's first move. Levels INSIDE the range are neither ceiling nor
floor and are eliminated as such.

⚠️ CONSEQUENCE: THE MAP CANNOT EXIST BEFORE 09:35 ET. Until today's opening
range closes there is no marker — not an empty map, NO map. `classify()`
returns UNMEASURED (None) in that case rather than a verdict, and the plan
records it as such. A geometry check that cannot run must never read as a
pass.

🔴 THE ORIGINAL RULING, 2026-08-25, verbatim: *"The mapper for our session
highs and lows, which are liquidity zones, and the forks have to SHARE A MAP.
Center of the map is gonna be where price currently sits at the open. There
are gonna be some levels above the price that are identified by either
session levels or fork tines. And the same will be below it. The levels below
are the only ones that can be the FLOOR and the levels above are the only
ones that can be the CEILING. No other combination will work."*

⚠️ AND THE CLARIFICATION THAT FOLLOWED. A first reading was "position governs,
the label is only provenance" — so an upper tine that drifted below the open
would become a FLOOR candidate. The operator corrected it: *"an upper tine
below the current open is UNUSABLE as a candidate. It would have to go to the
lower tine to qualify for the put credit spread. Upper tines can only be call
credit spreads, but would be INVALIDATED BY GEOMETRY if they are below the
open."*

⇒ THE TWO FACTS MUST AGREE, AND DISAGREEMENT ELIMINATES:
    ROLE comes from the SOURCE and never changes — an upper tine and a
    session HIGH are CEILINGS (call credit spreads) for the whole session; a
    lower tine and a session LOW are FLOORS (put credit spreads).
    POSITION is measured against the OPENING RANGE, frozen at 09:35.
    A ceiling at or below the range is INVALID. A floor at or above it is
    INVALID. Neither is re-cast as the other side — the displaced upper tine
    does not become the floor; the LOWER tine is the floor, or there is none.

⚠️ THIS IS WHY IT IS STRUCTURAL RATHER THAN A GATE. An inverted condor (PCS
above, CCS below) cannot be CONSTRUCTED from this map, so nothing downstream
has to detect one. It also removes a defect the old builders reproduced and
credit_edge had recorded weeks earlier: pricing a short call beyond an "upper"
tine that had drifted below spot — an ITM short call, something nobody would
sell.

⚠️ THE FORK THESIS, so it is not lost with the file it was written in.
Operator, 2026-08-25: *"The tines are what's of value, not the channel.
Tapping a tine is the trigger for selecting a short strike just outside the
channel. That's the level, but sloped."* No traversal/span gate. Both
timeframes (1h, 1d) valid — *"the hourly is valid too. Same rationale."*
"""
from __future__ import annotations

from typing import Optional, Tuple

CEILING, FLOOR = "ceiling", "floor"


def option_side(role: str) -> str:
    """A CEILING is sold as a CALL spread. A FLOOR as a PUT spread. Always."""
    return "call" if role == CEILING else "put"


def role_of(kind: str) -> Optional[str]:
    """Source label -> role. A level's role is what its SOURCE says it is.

    Accepts the vocabulary the level ledger, the sweep detector and the fork
    observer already use. Returns None for anything it does not recognise —
    an unknown kind gets NO role rather than a guessed one.
    """
    k = str(kind or "").lower()
    if k in ("high", "high_sweep", "call", "upper", "upper_tine", "ceiling"):
        return CEILING
    if k in ("low", "low_sweep", "put", "lower", "lower_tine", "floor"):
        return FLOOR
    return None


def classify(price: float, role: str, orb_high: Optional[float],
             orb_low: Optional[float], name: str = "level", *,
             spot: Optional[float]) -> Tuple[Optional[bool], str]:
    """(valid, why) for ONE level against the opening range.

    valid is True / False / None:
      True  — geometry agrees with the role; the level may be sold
      False — geometry disagrees; the level is INVALIDATED (never re-cast)
      None  — UNMEASURABLE: no opening range yet, or no price. Recorded as
              n/a by the plan; never a pass.
    """
    try:
        px = float(price)
    except (TypeError, ValueError):
        return None, f"{name}: no price to classify"
    if not orb_high or not orb_low or orb_high <= 0 or orb_low <= 0 \
            or orb_high < orb_low:
        return None, (f"{name} at {px:.2f}: no opening range yet — the map "
                      f"cannot exist before 09:35 ET, so geometry is unmeasured")
    if role not in (CEILING, FLOOR):
        return None, f"{name} at {px:.2f}: role '{role}' unknown — not classified"
    if orb_low <= px <= orb_high:
        return False, (f"{name} at {px:.2f} sits INSIDE the opening range "
                       f"{orb_low:.2f}-{orb_high:.2f} — neither above nor below "
                       f"it, so it is neither a ceiling nor a floor this session")
    if role == CEILING and px < orb_low:
        return False, (f"{name} is a CEILING at {px:.2f} but sits BELOW the "
                       f"opening range low {orb_low:.2f} — invalidated by "
                       f"geometry. A ceiling can only be sold as a call credit "
                       f"spread, and this one is beneath the session's first "
                       f"move; the other side's level is the candidate, not "
                       f"this one re-cast")
    if role == FLOOR and px > orb_high:
        return False, (f"{name} is a FLOOR at {px:.2f} but sits ABOVE the "
                       f"opening range high {orb_high:.2f} — invalidated by "
                       f"geometry; a floor can only be sold as a put credit "
                       f"spread")
    # 🔴 r231 — ROLE MUST ALSO AGREE WITH SPOT, NOT ONLY WITH THE RANGE.
    # Operator, 2026-09-03: "an upper tine below the current price cannot be
    # resistance, and a lower tine above price can never be support. Those are
    # invalidated by geometry."
    # ⚠️ THE RANGE TESTS ABOVE DO NOT COVER THIS. A ceiling sitting between
    # `orb_high` and spot passes every test above — it is not inside the range
    # and it is not below `orb_low` — while price has already traded through
    # it. Anchoring only to the opening range asks where the level sits
    # relative to 09:35; this asks where it sits relative to NOW.
    # ⚠️ SPOT IS A REQUIRED KEYWORD, NOT AN OPTIONAL ONE. An optional
    # parameter is a rule a caller can silently omit, which is r230's getattr
    # default wearing a signature: the invalidation would vanish for that
    # caller and nothing would say so. Missing spot returns None (unmeasured),
    # and None is never a pass.
    _sp = None
    try:
        _sp = float(spot) if spot is not None else None
    except (TypeError, ValueError):
        _sp = None
    if _sp is None or _sp <= 0:
        return None, (f"{name} at {px:.2f}: no spot to classify against — "
                      f"role-vs-price geometry is unmeasured")
    if role == CEILING and _sp > px:
        return False, (f"{name} is a CEILING at {px:.2f} but price is ALREADY "
                       f"ABOVE it at {_sp:.2f} — invalidated by geometry. An "
                       f"upper level can only be resistance; price has "
                       f"traversed it, so it is not resistance now and is "
                       f"never re-cast as support")
    if role == FLOOR and _sp < px:
        return False, (f"{name} is a FLOOR at {px:.2f} but price is ALREADY "
                       f"BELOW it at {_sp:.2f} — invalidated by geometry. A "
                       f"lower level can only be support; price has traversed "
                       f"it, so it is not support now")
    side = "above" if role == CEILING else "below"
    return True, (f"{name} at {px:.2f} is a {role} {side} the opening range "
                  f"{orb_low:.2f}-{orb_high:.2f} — geometry agrees")


class MapLevel:
    """One candidate on the shared session map.

    `role` is what the SOURCE says it is and is immutable. `valid` is whether
    the geometry agrees. A level that fails geometry is KEPT with valid=False
    and a reason, never silently dropped — the elimination is the record.
    """
    __slots__ = ("price", "role", "name", "source", "tf", "valid", "why")

    def __init__(self, price, role, name, source, tf=""):
        self.price = round(float(price), 4)
        self.role = role
        self.name = name
        self.source = source          # "ledger" | "fork"
        self.tf = tf                  # "1h" / "1d" for forks, "" otherwise
        self.valid = True
        self.why = ""

    @property
    def option_side(self):
        return option_side(self.role)

    def check_geometry(self, orb_high, orb_low, spot):
        ok, why = classify(self.price, self.role, orb_high, orb_low, self.name,
                           spot=spot)
        self.valid = bool(ok)
        self.why = why
        return self.valid


def build_session_map(orb_high, orb_low, spot, ledger=None, ctm=None):
    """Every credit-spread candidate this session, on ONE map, centered on the
    5-MINUTE OPENING RANGE. Returns (ceilings, floors, invalid) — all three,
    because the eliminated ones are evidence too.

    ⚠️ NO OPENING RANGE ⇒ NO MAP. Returning three empty lists is the CORRECT
    answer before 09:35, not a degraded one.
    ⚠️ `ctm.all_rails()` — the real CondorTriggerMap method. The doomed builder
    called `.all()`, which exists on no real object, and its fixture supplied
    it, so the test passed on a name that did not exist (r133 lesson).
    """
    if (not orb_high or not orb_low or orb_high <= 0 or orb_low <= 0
            or orb_high < orb_low):
        return [], [], []
    cands = []
    try:
        for lv in (getattr(ledger, "levels", None) or []):
            k = getattr(lv, "kind", "")
            role = role_of(k)
            if role is None:
                continue
            cands.append(MapLevel(
                lv.price, role,
                getattr(lv, "name", "") or f"{k} {lv.price:.2f}", "ledger"))
    except Exception:                                           # noqa: BLE001
        pass
    try:
        for t in (ctm.all_rails() if ctm is not None else []):
            # ⚠️ THE FORK'S OWN `side` IS THE ROLE. "call" == upper tine ==
            # CEILING. It is NOT re-derived from position — that is the whole
            # point of the ruling.
            role = role_of(getattr(t, "side", ""))
            if role is None:
                continue
            tf = getattr(t, "tf", "")
            cands.append(MapLevel(float(getattr(t, "rail", 0) or 0), role,
                                  f"{tf} {'upper' if role == CEILING else 'lower'} tine",
                                  "fork", tf))
    except Exception:                                           # noqa: BLE001
        pass

    ceilings, floors, invalid = [], [], []
    for c in cands:
        if c.price <= 0:
            continue
        if not c.check_geometry(orb_high, orb_low, spot):
            invalid.append(c)
        elif c.role == CEILING:
            ceilings.append(c)
        else:
            floors.append(c)
    ceilings.sort(key=lambda c: c.price)     # nearest the opening range first
    floors.sort(key=lambda c: -c.price)
    return ceilings, floors, invalid
