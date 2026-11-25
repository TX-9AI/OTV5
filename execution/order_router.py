"""
execution/order_router.py  v5.0
v5.0  2026-11-26  OTV5 r161 (LANE.1) — new. THE ONE ROUTING DECISION BETWEEN PAPER ORDERS AND LIVE ORDERS. The operator,
      2026-11-25: "There should be a clean routing map between paper orders & live orders that is cleanly separated";
      "I want park paperwalled until we enable it on the cash side, which is potentially January, if ever"; "Be
      deliberate. We should be able to switch between paper & live anytime we are fielding a new strategy for a few
      weeks." docs/ROUTING.md is the map; tests/check_order_routing.py holds this table to it.

      TWO QUESTIONS, TWO FACTS, ONE ANSWER EACH:
        route(setup, paper_box, flag=None)  -> LIVE | PAPER | DORMANT    an OPENING order
        route_close(record, paper_box)      -> LIVE | PAPER              a CLOSING order (every exit of an open row)
      paper_box is the box's account mode (config.PAPER_TRADING / BotState.paper_trading, set by configure.sh; True =
      the paper account). flag is the setup's box-flag lane (utils/box_flags: on | off | paper_only), read from this
      box's file when not given; a setup with no schema key reads "on" (or paper_only for PAPER_ALWAYS).

      THE OPENING TABLE (TABLE below; ROUTING.md prints the same rows):
        flag on          paper box -> PAPER (the box's own paper engines)     live box -> LIVE (the broker)
        flag paper_only  paper box -> PAPER (the box's own paper engines)     live box -> PAPER (THE WALL: paper_wall)
        flag off         paper box -> DORMANT (never asked)                   live box -> DORMANT
        anything else    -> DORMANT (a bad or unreadable flag fails closed: a typo can never send a live order)
      On a paper box paper_only is on (byte-identical); on a live box it is the paper wall with every wall guarantee
      (execution/paper_wall's W1-W6: zero broker calls, out of reconcile, the startup cancel, the order guard, buying
      power, the live walk and the 15:55 live cross; outside the cash cap).

      THE CLOSING RULE: AN OPEN POSITION FINISHES IN THE LANE IT OPENED IN. route_close reads the ROW (paper_trade), never
      the flag: a row booked paper (paper_trade = 1) closes paper; a live row (paper_trade = 0) on a live box closes live.
      A flag changed by a land and a restart re-routes NEW entries only; it never moves an open position (the live
      TradeLogger reads paper_trade = 0 rows, the wall's paper_trade = 1 rows, so each book resumes only its own).

      THE BOOK AND THE ENGINE SEAMS: is_wall(obj) is the one reading of PAPER_WALL (the wall's book and entry engine
      carry it), so position_manager / entry_engine ask the router which close engine, tally and cap counterfactual a
      book or an engine belongs to instead of reading the attribute themselves.

      GENERIC: a setup joins by its utils/box_flags.SCHEMA key alone (no change here). This module imports no broker
      client and holds no state; every function is pure over its arguments and the frozen box flags. Never raises:
      route() fails CLOSED (DORMANT), route_close() fails PAPER only when the row says paper, else the row's own mode.
"""
from __future__ import annotations

from typing import Tuple

GATES = {}        # WA section 36: this file owns no gate constant

LIVE, PAPER, DORMANT = "LIVE", "PAPER", "DORMANT"
ON, OFF, PAPER_ONLY = "on", "off", "paper_only"

# The setups that open PAPER on every box with no flag key (r150 OGAP.5; OGAP is retired r153 and never asked, its
# open rows still close paper). A name here is never sent to the broker.
PAPER_ALWAYS: Tuple[str, ...] = ("OGAP",)

# (flag, paper_box) -> route. The ONE table; docs/ROUTING.md prints it and check_order_routing compares them.
TABLE = {
    (ON, True): PAPER,
    (ON, False): LIVE,
    (PAPER_ONLY, True): PAPER,
    (PAPER_ONLY, False): PAPER,
    (OFF, True): DORMANT,
    (OFF, False): DORMANT,
}


def flag_key(setup: str) -> str:
    """The utils/box_flags.SCHEMA key whose setup is `setup` ("" when none)."""
    try:
        from utils import box_flags as _bf
        for k, row in _bf.SCHEMA.items():
            if row.setup == str(setup or ""):
                return k
    except Exception:                                           # noqa: BLE001
        pass
    return ""


def lane(setup: str) -> str:
    """The setup's lane on this box: its box flag's value (read once per process by utils/box_flags), paper_only for a
    PAPER_ALWAYS name, "on" for a setup with no key. An unreadable flag reads "" (route: DORMANT)."""
    s = str(setup or "")
    if s in PAPER_ALWAYS:
        return PAPER_ONLY
    try:
        key = flag_key(s)
        if not key:
            return ON
        from utils import box_flags as _bf
        return str(_bf.value(key) or "")
    except Exception:                                           # noqa: BLE001
        return ""


def route(setup: str, paper_box, flag=None) -> str:
    """LIVE | PAPER | DORMANT for an OPENING order of `setup`. paper_box: True only for the paper account (anything
    else, an unreadable mode included, is a live box: the answer can then only be LIVE where `on` says so, PAPER or
    DORMANT). flag: the lane, read from the box's file when None. Never raises (fails DORMANT)."""
    try:
        f = lane(setup) if flag is None else str(flag)
        if str(setup or "") in PAPER_ALWAYS and f == ON:
            f = PAPER_ONLY
        return TABLE.get((f, paper_box is True), DORMANT)
    except Exception:                                           # noqa: BLE001
        return DORMANT


def walled(setup: str, paper_box) -> bool:
    """True when an opening order of `setup` goes through the paper wall: a LIVE box and route PAPER. A paper box is
    never walled (its own engines are already paper)."""
    return paper_box is not True and route(setup, paper_box) == PAPER


def walled_setups(paper_box, names=None) -> Tuple[str, ...]:
    """The setups this box walls (a live box: route PAPER), sorted: PAPER_ALWAYS plus every schema setup at paper_only.
    () on a paper box."""
    if paper_box is True:
        return ()
    cand = set(PAPER_ALWAYS)
    try:
        from utils import box_flags as _bf
        cand |= {row.setup for row in _bf.SCHEMA.values()}
    except Exception:                                           # noqa: BLE001
        pass
    if names is not None:
        cand |= set(names)
    return tuple(sorted(n for n in cand if walled(n, paper_box)))


def asked_past_cap(paper_box) -> bool:
    """True on a LIVE box: a tripped CASH cap does not stop the walled setups (the operator, 2026-11-22: "The cap on a
    live box is for live trades only. Full stop."). False on a paper box (every row there is inside its cap)."""
    return paper_box is not True


def route_close(record, paper_box) -> str:
    """LIVE | PAPER for a CLOSING order of an open row: the lane it OPENED in, read from the row (paper_trade), never
    from a flag. A paper box closes PAPER. On a live box a row with paper_trade = 1 closes PAPER (the wall), a row
    with paper_trade = 0 closes LIVE; a row with no readable paper_trade reads the trades.db default (1, paper)."""
    if paper_box is True:
        return PAPER
    try:
        v = record.get("paper_trade", 1) if hasattr(record, "get") else getattr(record, "paper_trade", 1)
        v = 1 if v is None or v == "" else int(v)
    except Exception:                                           # noqa: BLE001
        v = 1
    return PAPER if v else LIVE


def is_wall(obj) -> bool:
    """True when `obj` (a position book or an entry engine) is the paper wall's (execution/paper_wall). The one reading
    of PAPER_WALL: position_manager and entry_engine ask here which close engine, tally and cap record they use."""
    return getattr(obj, "PAPER_WALL", False) is True


def describe(setup: str, paper_box) -> str:
    """The Service line's words for a setup's lane: "trade" (on), "off (box flag)", "paper_only (walled on a live
    box)". Text only."""
    f = lane(setup)
    if f == PAPER_ONLY and str(setup or "") not in PAPER_ALWAYS:
        return "paper_only (walled on a live box)"
    r = route(setup, paper_box)
    if r == DORMANT:
        return "off (box flag)"
    return "trade"
