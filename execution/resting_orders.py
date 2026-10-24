#!/usr/bin/env python3
"""
execution/resting_orders.py  v1.5
v1.5  2026-10-04  OTV4TEST r242 (LIVE.1 B0, MIRROR OF otv4 r463 c912ce7, WA 38.2) — every Account call goes through tasty_client.sdk_result: on tastytrade 13.x the Account methods are coroutines and a bare call placed and closed NOTHING live (paper never calls them). Hunks applied verbatim from c912ce7.
v1.4  2026-10-03  OTV4TEST r218 (PATH.1) — _db_path delegates to utils.paths: it imported config.DATA_DIR, which never existed, and always took a ~/options-trader fallback. Same path on the box.
v1.3  2026-10-03  OTV4TEST r210 (AUD.9) — note_fill_price IS PUBLIC, for the paper filler. fill_price was 0 on 16 of 16
      FILLED rows: only the live poll wrote it and every fill on this box is a paper fill, which closes the
      offer at placement and never polls. entry_engine now notes the price paper booked. No behaviour change.
v1.2  2026-09-25  OTV4TEST r143 — EVERY CONNECTION IS CLOSED. The block form committed and
      never closed - AAL held 44 leaked handles on resting_orders.db when it hit
      the 1024 file limit (see database/trade_logger.py v4.18). All 5 sites now
      use `_session()`, same commit/rollback, then close.
v1.1  2026-09-01  r207 — PAPER FILLS THE WHOLE OFFER. The v1.0 paper branch
      compared the UNDERLYING price against the OPTION STRIKE
      (`price >= row["strike"]`) and called that "the underlying has come back
      to the level the offer was anchored on". Those are different quantities:
      on a short ORB with a 705 put and spot at 709 it is trivially true, so
      the model would have filled instantly on any OTM offer and never on an
      ITM one — backwards, and undetected only because `_place_single_leg`
      short-circuited to the paper filler before an offer was ever placed, so
      this branch has never executed. Operator, 2026-09-01: "in paper mode,
      they ALL fill." The comparison is deleted rather than corrected; there
      is no partial-fill evidence to model and inventing one is worse than
      admitting the residual gap.

THE ORB STANDING OFFER: one limit at mark, posted once, left to rest.

v1.0  2026-08-30  r195 — backlog ORB.2. Operator, 2026-08-30: *"leave it as a
      standing offer until it gets fully filled, or the trade sequence makes it
      ineligible (ran away past the 50% TP or price came back and stopped out
      on the structure)."*

🔑 WHY ORB LEAVES THE LADDER, AND ONLY ORB. The entry ladder (r104,
`ladder_registry` over `entry_ladder.LadderState`) exists because of FRC.1: the
fleet's gross edge is +$2.70/trade against $126/trade of round-trip friction,
so capturing half the half-spread is worth ~$31/trade — an order of magnitude
more than anything on the trade-selection list. That arithmetic is right for
the credit spreads, the butterfly and the runaway, and they keep the walk.

It is wrong for ORB, because the walk buys that $31 by SPENDING TICKS, and an
ORB entry that misses its retest window does not lose $31 — it loses the whole
setup. Operator's words, kept verbatim because they are the reasoning a future
reader needs: *"I don't want to blow an entry trying to save $25 by dicking
around over pennies."* The edge is in being IN the break, not in the fill.

⚠️ THIS IS A BIGGER CHANGE THAN "LET THE ORDER SIT". Before r195 an ORB entry
posted ONE RUNG PER TICK with a ~5s per-rung deadline (`_rung_deadline()` is a
quarter of LIVE_ENTRY_DEADLINE_SECONDS), was cancelled, and the strategy
re-signalled next tick against a fresh quote — an active price walk. r195
replaces that with a single DAY limit that is never re-priced. The file's own
v3.8 header still described the pre-ladder "post at mark and let it sit"
behaviour, which r104 had already superseded; do not read that comment as
current.

━━ THE THREE SURFACES (operator's ruling, and the reason this module is small)
  1. PLACEMENT is a logged EVENT. It is never a position.
  2. OPEN POSITIONS are a projection of the BROKER's positions endpoint,
     grouped by strike+type — discovered, never declared by us.
  3. WORKING ORDERS — this file — are their own informational surface, kept
     OFF the trades log.

🔑 SURFACE 2 IS WHY THERE IS NO REMAINING-QUANTITY HERE. `get_open_option_positions()`
already returns `{symbol, underlying, quantity, direction, average_open_price}`
and its own docstring already says *"the brokerage is the source of truth for
whether a position exists"*. **The broker averages the basis across partial
fills**, so accretion needs no arithmetic of ours and nothing to reconcile. We
record what we OFFERED; the broker tells us what we OWN.

⚠️ ADOPTION IS SCOPED TO A STRIKE/SIDE WE HOLD AN OFFER FOR, AND THAT IS NOT A
DETAIL. `_intraday_reconcile` deliberately *"does not adopt brand-new broker
positions intraday, so a manual trade you place is left alone."* Widening that
refusal is only safe because this file says which contract we asked for — which
is what makes surface 1 load-bearing rather than decorative. A discovery path
that adopted any new broker position would hijack the operator's own fills.

⚠️ DURABLE, NOT IN-PROCESS. State lives in its own SQLite table beside the
trades DB, following r179's precedent: an offer must survive a restart, because
a bot that forgets it has a live order at the broker is exactly how an orphan
is born. r178's in-process lock is the failure this avoids.

━━ CANCEL TRIGGERS (operator's set, and the ONLY set)
  • FULLY FILLED        — nothing left to cancel
  • PAST THE 50% TP     — the runaway case; the contract is dearer than our
                          offer anyway, so this is tidiness more than defence
  • STRUCTURE STOP      — 1m close beyond the impulsive low/high, the SAME
                          close-based test the exit engine uses, evaluated on
                          the same tick as the exit
  • EOD FLATTEN         — backstop; nothing may be working overnight

⚠️ 11:30 IS NOT A CANCEL TRIGGER. Operator: *"1130 is the cutoff for new orb
entries or a single attempt runaway that has not yet fired during the
session."* It gates PLACING. An offer placed in-window keeps accreting after
it, so a position can open in the afternoon — deliberate, and the debit block
does not apply because the ORDER is not new.

🔑 A RE-ARM DOES NOT CANCEL THE OFFER, AND I HAD THIS BACKWARDS. Operator:
*"if price reenters the range without hitting the stop then the original trade
geometry STANDS as VALID."* He is right, and the exit engine already agrees —
`exit_engine.py:990`: *"Merely closing back inside the range does NOT stop the
trade: price is allowed to breathe inside the range as long as it holds the
impulsive origin."* The engine's attempt test is the RANGE BOUNDARY; the trade's
test is the IMPULSIVE ORIGIN, which sits below it. Price in that gap kills the
attempt and not the thesis, and cancelling there would judge the offer more
harshly than the position it is trying to become.

⚠️ THE DUPLICATE-OFFER PROBLEM IS SOLVED UPSTREAM, NOT HERE. r195 stops
the engine re-arming at SIGNAL time — it now waits for the trade to resolve —
and main.py refuses to ask ORB for a signal while an offer is working. No
second attempt can form while this one stands, so the offer never needs
cancelling for a reason that is not its own stop.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Beside the trades DB, not inside it: this is not a trade and must never be
# read by anything that counts trades. r179's cap reads `trades`, and an offer
# that has not filled is not a trade by any definition the operator uses.
_DB_ENV = "OT_RESTING_DB"


def _db_path() -> str:
    from utils.paths import resting_db_path as _rdp   # r218: was config.DATA_DIR (never defined) then a home-anchored fallback
    return _rdp()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS resting_orders (
    order_id      TEXT PRIMARY KEY,
    session_date  TEXT NOT NULL,
    strategy      TEXT NOT NULL,
    symbol        TEXT NOT NULL,   -- OCC option symbol: strike+type live here
    underlying    TEXT NOT NULL,
    side          TEXT NOT NULL,   -- call | put
    strike        REAL NOT NULL,
    offered_qty   INTEGER NOT NULL,
    offer_price   REAL NOT NULL,
    placed_ts     REAL NOT NULL,
    state         TEXT NOT NULL,   -- WORKING | FILLED | CANCELLED
    cancel_reason TEXT DEFAULT '',
    last_seen_qty INTEGER DEFAULT 0,
    -- The attempt's OWN levels, frozen at placement. ⚠️ NOT re-read from the
    -- ORB engine at supervision time: the engine may have re-armed onto a new
    -- attempt with different levels, and this offer belongs to the attempt
    -- that placed it. Judging an old offer by a new attempt's stop is how you
    -- cancel a good order for a reason that never applied to it.
    signal_json   TEXT DEFAULT '',   -- the fields make_record() needs, frozen
    direction     TEXT DEFAULT '',
    target_50pct  REAL DEFAULT 0,
    structure_stop REAL DEFAULT 0,
    fill_price    REAL DEFAULT 0
);
"""


@contextmanager
def _session():
    """One block's connection: commit/rollback as `with c:` did, then CLOSE (r143)."""
    c = _conn()
    try:
        with c:
            yield c
    finally:
        c.close()


def _conn() -> sqlite3.Connection:
    path = _db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = sqlite3.connect(path, timeout=10)
    c.row_factory = sqlite3.Row
    c.executescript(_SCHEMA)
    return c


def record_placement(*, order_id: str, session_date: str, strategy: str,
                     symbol: str, underlying: str, side: str, strike: float,
                     offered_qty: int, offer_price: float,
                     direction: str = "", target_50pct: float = 0.0,
                     structure_stop: float = 0.0, signal_json: str = "") -> None:
    """Surface 1: the offer was PLACED. This is an event, not a position.

    ⚠️ Written BEFORE anything is known about fills, and deliberately so. An
    order that exists at the broker and not in our state is the orphan this
    whole module exists to prevent — so the write happens the moment the broker
    accepts it, and a fill discovered later joins a row that is already there.
    """
    try:
        with _session() as c:
            c.execute(
                "INSERT OR REPLACE INTO resting_orders (order_id, session_date,"
                " strategy, symbol, underlying, side, strike, offered_qty,"
                " offer_price, placed_ts, state, cancel_reason, last_seen_qty,"
                " direction, target_50pct, structure_stop,"
                " signal_json)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,'WORKING','',0,?,?,?,?)",
                (str(order_id), session_date, strategy, symbol, underlying,
                 side, float(strike), int(offered_qty), float(offer_price),
                 time.time(), direction, float(target_50pct),
                 float(structure_stop), signal_json))
        logger.info("[offer] PLACED %s %s x%d @ %.2f (order %s) — standing "
                    "until filled or the sequence ends it",
                    symbol, side, offered_qty, offer_price, order_id)
    except sqlite3.Error as exc:
        # ⚠️ LOUD, AND THE CALLER MUST STILL SEE THE ORDER. Failing to record
        # does not un-place the order at the broker; swallowing this quietly
        # would leave a live offer nobody is watching.
        logger.error("[offer] COULD NOT RECORD placement of %s (%s) — the "
                     "order IS live at the broker and is now unsupervised",
                     order_id, exc)


def working(session_date: str, strategy: str = "") -> List[Dict]:
    """Every offer still WORKING this session. Survives a restart by design."""
    try:
        with _session() as c:
            q = ("SELECT * FROM resting_orders WHERE state='WORKING' "
                 "AND session_date=?")
            args: list = [session_date]
            if strategy:
                q += " AND strategy=?"
                args.append(strategy)
            return [dict(r) for r in c.execute(q, args).fetchall()]
    except sqlite3.Error as exc:
        # Fail EMPTY, not closed: an unreadable state file must not stop the
        # trading loop. The 10-minute broker reconcile is the backstop.
        logger.error("[offer] state unreadable (%s) — no offers supervised "
                     "this tick", exc)
        return []


def note_seen_qty(order_id: str, qty: int) -> None:
    """Record how much the broker says has filled so far. Informational."""
    try:
        with _session() as c:
            c.execute("UPDATE resting_orders SET last_seen_qty=? WHERE "
                      "order_id=?", (int(qty), str(order_id)))
    except sqlite3.Error:
        pass


def close_out(order_id: str, state: str, reason: str = "") -> None:
    """Mark an offer FILLED or CANCELLED. Never deletes: the session's offers
    are a record of what we asked for, including what never filled — which is
    the population the fill-rate question needs and the one nobody keeps."""
    try:
        with _session() as c:
            c.execute("UPDATE resting_orders SET state=?, cancel_reason=? "
                      "WHERE order_id=?", (state, reason, str(order_id)))
        logger.info("[offer] %s %s%s", order_id, state,
                    f" — {reason}" if reason else "")
    except sqlite3.Error as exc:
        logger.error("[offer] could not close out %s (%s)", order_id, exc)


# ── cancel triggers ────────────────────────────────────────────────────────
def cancel_reason(row: Dict, *, price: float, last_1m_close: Optional[float],
                  target_50pct: float, structure_stop: float,
                  direction: str, eod: bool = False) -> str:
    """Which trigger ends this offer, or "" to keep standing.

    🔑 EVALUATED ON EVERY TICK, INCLUDING TICKS WITH NO POSITION. An offer that
    has not filled has no trade record, so the manage branch never runs for it
    — the supervisor must be called from BOTH branches of the loop or an
    unfilled offer is supervised by nothing at all.

    ⚠️ THE STRUCTURE TEST USES THE LAST CLOSED 1m BAR, exactly as the exit
    engine does. Two different tests for one level is how the offer and the
    position come to disagree about whether the trade is still alive.
    """
    if eod:
        return "eod_flatten"
    if direction == "long":
        if target_50pct and price >= target_50pct:
            return f"ran_past_50pct_tp ({price:.2f} >= {target_50pct:.2f})"
        if (structure_stop and last_1m_close is not None
                and last_1m_close < structure_stop):
            return (f"structure_stop (1m close {last_1m_close:.2f} < "
                    f"{structure_stop:.2f})")
    else:
        if target_50pct and price <= target_50pct:
            return f"ran_past_50pct_tp ({price:.2f} <= {target_50pct:.2f})"
        if (structure_stop and last_1m_close is not None
                and last_1m_close > structure_stop):
            return (f"structure_stop (1m close {last_1m_close:.2f} > "
                    f"{structure_stop:.2f})")
    return ""


def positions_by_strike_type(broker_rows: List[Dict]) -> Dict[tuple, Dict]:
    """Surface 2: the broker's open positions, keyed (symbol, direction).

    ⚠️ THE KEY IS THE CONTRACT, NOT AN ORDER ID. That is the operator's ruling
    working for us: a second fill on the same contract simply raises the
    quantity of the same group, and `average_open_price` from the broker is
    already the blended basis. There is nothing to accrete by hand and no
    partial-fill arithmetic to get wrong.
    """
    out: Dict[tuple, Dict] = {}
    for r in broker_rows or []:
        sym = str(r.get("symbol") or "")
        if not sym:
            continue
        out[(sym, str(r.get("direction") or ""))] = dict(r)
    return out


# ── the supervisor ─────────────────────────────────────────────────────────
def supervise(*, price: float, last_1m_close, eod: bool = False,
              paper: bool = False, adopt=None) -> int:
    """Called EVERY TICK, from BOTH branches of the loop. Returns offers closed.

    🔑 BOTH BRANCHES IS THE WHOLE POINT. An offer that has not filled has no
    trade record, so `pos_mgr.has_open_position()` is False and the manage
    branch never runs for it. Supervising only from the manage branch would
    leave every unfilled offer unwatched — which is the exact orphan this
    module exists to prevent, reintroduced one level up.

    Order of operations, and it is deliberate:
      1. POLL the order for filled quantity — cheap, one order id.
      2. On a fill delta, DISCOVER the position from the broker and adopt it.
      3. THEN evaluate the cancel triggers.
    Discovery runs BEFORE cancellation so a fill that arrived on the same tick
    as a trigger is still adopted. Cancelling first would drop a position we
    already own at the broker and leave it unmanaged.

    ⚠️ `adopt` is injected, not imported. This module knows about offers; it
    must not also know how a trade record is built, or the two grow into one
    tangle and neither can be tested alone.
    """
    from utils.time_utils import now_et
    closed = 0
    for row in working(now_et().date().isoformat()):
        oid = row["order_id"]

        # ── 1. how much has actually filled? ──────────────────────────────
        filled = _filled_qty(oid, row, paper=paper, price=price)
        if filled is None:
            # ⚠️ UNREADABLE IS NOT ZERO. A failed poll leaves the offer
            # standing and says so; treating it as zero fills would let a
            # trigger cancel an order that may be fully filled at the broker.
            logger.warning("[offer] %s: could not read fill state — standing, "
                           "unchanged this tick", oid)
            continue
        if filled != int(row.get("last_seen_qty") or 0):
            note_seen_qty(oid, filled)
            logger.info("[offer] %s: %d/%d filled", oid, filled,
                        row["offered_qty"])
            if adopt is not None and filled > 0:
                try:
                    adopt(row, filled)
                except Exception as exc:                        # noqa: BLE001
                    # LOUD. A fill we cannot adopt is a live position nobody
                    # is managing — the worst state in the system.
                    logger.error("[offer] %s: ADOPTION FAILED for %d filled "
                                 "contract(s) (%s) — the position exists at "
                                 "the broker and is UNMANAGED", oid, filled, exc)

        # ── 2. fully filled ends the offer with nothing to cancel ─────────
        if filled >= int(row["offered_qty"]):
            close_out(oid, "FILLED")
            closed += 1
            continue

        # ── 3. the triggers ───────────────────────────────────────────────
        why = cancel_reason(row, price=price, last_1m_close=last_1m_close,
                            target_50pct=float(row.get("target_50pct") or 0.0),
                            structure_stop=float(row.get("structure_stop") or 0.0),
                            direction=str(row.get("direction") or "long"),
                            eod=eod)
        if why:
            if _cancel(oid, paper=paper):
                close_out(oid, "CANCELLED", why)
                closed += 1
                # 🔑 THE ENGINE IS WAITING ON THIS. r195 moved ORB's re-arm
                # from signal-fired to trade-resolved, so the engine sits in
                # OPEN_* until something here says the setup is finished. Skip
                # it and ORB takes no further setup for the rest of the day.
                _release_engine("offer cancelled: %s" % why)
            else:
                # An uncancellable order may still fill. Say so plainly and
                # leave the row WORKING so the next tick tries again; the
                # 10-minute broker reconcile is the backstop underneath.
                logger.error("[offer] %s: CANCEL FAILED (%s) — it may still "
                             "fill; still supervised", oid, why)
    return closed


def _filled_qty(order_id: str, row: dict, *, paper: bool, price: float):
    """Filled quantity for this offer, or None when it cannot be read.

    🔴 r207 — PAPER FILLS THE WHOLE OFFER, ALWAYS. Operator's ruling. v1.0
    tried to model no-fill risk and compared the UNDERLYING price to the
    OPTION STRIKE, which are different quantities — on a short ORB with a 705
    put and spot at 709 the test was trivially true, so it filled instantly on
    every OTM offer and never on an ITM one. It never executed, because
    `_place_single_leg` reached the paper filler before an offer was ever
    placed, so the error sat behind a green board.

    ⚠️ THE RESIDUAL GAP IS STATED RATHER THAN MODELLED. Paper is optimistic on
    fill rate and we know it; a model built on no evidence would make it
    optimistic in a way nobody could see. Under r207 the paper path fills and
    closes the offer at placement, so this branch is a backstop for a row that
    somehow survives — and its answer must be the same one.
    """
    if paper:
        return int(row["offered_qty"])
    try:
        from data.tasty_client import get_session, get_account, sdk_result
        from execution.order_confirm import net_from_fills
        session, account = get_session(), get_account()
        placed = sdk_result(account.get_order(session, order_id))   # B0
        # 🔑 THE REPO ALREADY HAS A FILL READER, AND ONE IS THE RIGHT NUMBER.
        # `net_from_fills` is what confirm_order_fill uses; a second hand-rolled
        # walk over legs[].fills[] would be a parallel lineage that looks
        # correct in isolation and disagrees under partials — WORKING_AGREEMENT
        # 7 exactly. The basis is the single long leg.
        got = net_from_fills(placed, [(row["symbol"], 1, +1)])
        if got is None:
            return 0            # accepted by the broker, nothing filled yet
        units, net = got
        _note_fill_price(order_id, float(net))
        return int(units)
    except Exception as exc:                                    # noqa: BLE001
        logger.debug("[offer] %s poll failed: %s", order_id, exc)
        return None


def note_fill_price(order_id: str, net: float) -> None:
    """r210 — the public name: the paper filler notes the price it booked."""
    _note_fill_price(order_id, net)


def _note_fill_price(order_id: str, net: float) -> None:
    """The broker's actual net fill price for this offer.

    ⚠️ THE RECORD MUST BOOK THIS, NOT OUR OFFER. They are usually equal for a
    limit that filled at its own price, but "usually" is not a basis for P&L —
    v3.7 fixed exactly this bug, where `placed.price or signal.entry_premium`
    booked the mark because a market order has no price.
    """
    try:
        with _session() as c:
            c.execute("UPDATE resting_orders SET fill_price=? WHERE order_id=?",
                      (float(net), str(order_id)))
    except sqlite3.Error:
        pass


def _cancel(order_id: str, *, paper: bool) -> bool:
    if paper:
        return True
    try:
        from data.tasty_client import get_session, get_account, sdk_result
        session, account = get_session(), get_account()
        # Same call confirm_order_fill uses at its deadline.
        sdk_result(account.delete_order(session, order_id))   # B0
        return True
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[offer] cancel of %s failed: %s", order_id, exc)
        return False


# ── surface 2: the broker declares the position ────────────────────────────
def adopt_fill(row: dict, filled: int, *, paper: bool = False) -> bool:
    """Turn a broker-confirmed fill on a standing offer into the trade record.

    🔑 THE BROKER DECLARES THE POSITION, NOT US. Operator's ruling: *"broker-side
    open positions is the only thing that can declare an 'open' position in the
    live book."* So this reads `get_open_option_positions()`, finds the group
    for THIS contract, and books what the broker says we own — quantity and
    `average_open_price` both. We never compute a blended basis: the broker has
    already done it across every partial, and a second averaging is a second
    answer.

    ⚠️ ADOPTION IS SCOPED TO THE CONTRACT WE OFFERED ON. `_intraday_reconcile`
    deliberately *"does not adopt brand-new broker positions intraday, so a
    manual trade you place is left alone."* That refusal is a feature. This
    widens it by EXACTLY ONE symbol — the one named on a WORKING offer we
    placed — which is what makes the placement log load-bearing rather than
    decorative. A manual fill on any other contract is still left alone.

    ⚠️ IDEMPOTENT BY trade_id. The supervisor calls this on every fill DELTA,
    so a 4-then-10 partial calls it twice. The second call must UPDATE the
    existing row's size, not open a second position — double-booking a position
    that exists once at the broker is worse than not booking it at all.

    Returns True when a record exists afterwards.
    """
    from database.trade_logger import get_trade_logger, make_record
    import json

    symbol = row["symbol"]
    tl = get_trade_logger()

    # ── what does the broker actually say we own? ─────────────────────────
    qty, basis = filled, float(row.get("fill_price") or row["offer_price"])
    if not paper:
        try:
            from data.tasty_client import get_open_option_positions
            groups = positions_by_strike_type(get_open_option_positions())
            hit = None
            for (sym, _dirn), pos in groups.items():
                if sym == symbol:
                    hit = pos
                    break
            if hit is None:
                # 🔴 THE ORDER SAYS FILLED AND THE BOOK SAYS NOTHING. Do not
                # invent a position from the order alone — that is precisely
                # what "the broker is the only thing that can declare a
                # position" forbids. Page and let the next tick or the
                # 10-minute reconcile resolve it.
                logger.error("[offer] %s: order reports %d filled but the "
                             "broker's positions do not list %s — NOT booking "
                             "a position we cannot see. Retrying next tick.",
                             row["order_id"], filled, symbol)
                return False
            qty = abs(int(hit.get("quantity") or 0)) or filled
            basis = float(hit.get("average_open_price") or basis)
        except Exception as exc:                                # noqa: BLE001
            logger.error("[offer] %s: positions read failed (%s) — not booking "
                         "this tick", row["order_id"], exc)
            return False

    # ── one row per offer, updated in place on later partials ─────────────
    trade_id = "orb-%s" % row["order_id"]
    existing = None
    try:
        for r in (tl.get_open_trades_live() or []):
            if str(r.get("trade_id")) == trade_id:
                existing = r
                break
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[offer] open-trade read failed (%s) — proceeding", exc)

    total_cost = basis * qty * 100.0
    if existing is not None:
        if int(existing.get("contracts") or 0) == qty:
            return True                     # nothing new to say
        try:
            tl.update_fields(trade_id, contracts=qty, entry_premium=basis,
                             total_cost=total_cost, max_loss=total_cost)
            logger.info("[offer] %s: position GREW to %d @ %.2f (broker basis)",
                        row["order_id"], qty, basis)
        except Exception as exc:                                # noqa: BLE001
            logger.error("[offer] %s: could not grow the record (%s)",
                         row["order_id"], exc)
            return False
        return True

    try:
        snap = json.loads(row.get("signal_json") or "{}")
    except Exception:                                           # noqa: BLE001
        snap = {}
    snap.pop("orb_range_high", None)
    snap.pop("orb_range_low", None)
    rec = make_record(
        trade_id=trade_id, contracts=qty, entry_premium=basis,
        total_cost=total_cost, max_loss=total_cost,
        order_id=row["order_id"], paper_trade=1 if paper else 0,
        status="open", **snap)
    try:
        tl.log_entry(rec)
    except Exception as exc:                                    # noqa: BLE001
        logger.error("[offer] %s: log_entry FAILED (%s) — the position exists "
                     "at the broker and is UNRECORDED", row["order_id"], exc)
        return False
    logger.info("[offer] %s: position DISCOVERED — %s x%d @ %.2f (broker "
                "declares it; we only offered)", row["order_id"], symbol,
                qty, basis)
    return True


def _release_engine(why: str) -> None:
    """Tell the ORB engine its setup is over so it can re-arm.

    ⚠️ NEVER RAISES. A failure here leaves the engine OPEN for the session and
    costs every later setup, so it is logged loudly; the 10-minute reconcile
    and the EOD flatten remain underneath.
    """
    try:
        from analysis.orb_engine import get_orb_engine
        get_orb_engine().notify_position_closed()
        logger.info("[offer] engine released — %s", why)
    except Exception as exc:                                    # noqa: BLE001
        logger.error("[offer] COULD NOT RELEASE THE ORB ENGINE (%s) — it will "
                     "stay OPEN and take no further setup today", exc)


def cancel_all_working(reason: str, *, strategy: str = "ORBStrategy",
                       paper: bool = False) -> int:
    """End every working offer for this setup. Returns how many were cancelled.

    🔑 THE SETUP ENDING IS THE TRIGGER, NOT A LIST OF EXIT REASONS. Operator:
    a re-arm cancels any previous offer, because a new impulsive candle has a
    different high and low and therefore a *different offer composition* —
    different stop distance, different contract count, a different mark. A
    stale offer is not merely redundant, it is priced for a setup that no
    longer exists.

    ⚠️ THIS IS THE CASE THE TRIGGER LIST COULD NOT REACH. Offer 10, four fill,
    the position opens and then exits on `theta_bleed` — or the velocity stall,
    or the trail, or the 15:45 flatten. None of those is "fully filled", "past
    the 50% TP" or "structure stop", so the remaining six kept standing with no
    position behind them while the engine hunted a new setup. The exit engine
    has seven exit paths and will grow more; enumerating them rots. Anything
    that ends the setup ends the offer, by construction.

    ⚠️ A FAILED CANCEL LEAVES THE OFFER WORKING, DELIBERATELY. It may still
    fill — that is the cancel/fill race `confirm_order_fill` already documents
    — so the row stays supervised and the next tick tries again, with the
    10-minute broker reconcile underneath.
    """
    from utils.time_utils import now_et
    n = 0
    for row in working(now_et().date().isoformat(), strategy):
        oid = row["order_id"]
        if _cancel(oid, paper=paper):
            close_out(oid, "CANCELLED", reason)
            n += 1
        else:
            logger.error("[offer] %s: CANCEL FAILED on setup end (%s) — it may "
                         "still fill; still supervised", oid, reason)
    if n:
        logger.info("[offer] %d working offer(s) cancelled — %s", n, reason)
    return n
