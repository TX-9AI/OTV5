"""
derived/plan_ledger.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.3  2026-10-24  CD.2 — A PLAN DOES NOT OUTLIVE ITS SESSION. live_plans() and close_unfilled() read only rows created on
      or after TODAY's session start (ET midnight), except LEG1_FILLED (real money on; the broker reconcile decides
      it, not a clock). A row from an earlier session - a restart that skipped mark_restart_wipe, or a seeded one -
      was reported live and could be linked to today's fill. The operator, 2026-10-24: approved.
v4.2  2026-10-19  OTV4TEST r303 (PSTATE.1) — A DORMANT PLAN OPENS NO LEDGER ROW. open_plan() returns None for a
      strategy strategy/plan_state.py calls DORMANT (the operator, 2026-10-19: "dormant plans should not write to
      the ledger"). This is the one door every writer passes - Plan._ledger_open, the ORB rows main.run_analysis
      writes from the opening-range ENGINE whatever OT_ORB_TRADE said, and the condor - so none needs its own
      check. A None id is what every caller already handles (an unrecorded plan). The engine itself still runs.
v4.1  2026-09-01  r212 (chunk D) — A PLAN CLOSES WHEN ITS TRADE DOES.
      🔴 ROWS OPENED BY `PlanTick.take()` WERE NEVER CLOSED BY ANYTHING.
      `transition()` had exactly two callers — main.py's ORB plan and the
      condor's `_plan_id` — so every plan opened through `Plan._ledger_open`
      (runaway, sweep, butterfly, TCS, condor leg two) kept `closed_ts` NULL
      for the whole session and `live_plans()` returned it forever. QQQ,
      2026-09-01: SEVEN `RunawayContinuation TRIGGERED @ 708.43` rows, every
      one flagged LIVE, while six of those trades had closed hours earlier.
      🔴 AND r199 MISDIAGNOSED THIS AS DUPLICATION. It saw two rows for one
      strategy at one trigger, called them duplicates and collapsed them for
      display. They were never duplicates — they were distinct plans that had
      not been closed, and the collapse merged trades with different outcomes,
      because (strategy, state, trigger) cannot tell two runaway fires at one
      boundary apart. RPT.5 recorded that the write side had never been
      examined; this is that examination.
      · `close_for_trade(trade_id, reason)` — hooked into
        `trade_logger.log_exit`, the ONE choke point every close passes
        through (r154's precedent). Keyed on the TRADE, so it inherits none of
        `link_trade`'s most-recent-live ⟨ASSUMPTION⟩.
      · `close_unfilled(strategy, reason)` — the SECOND leak: a plan that
        fires and is then refused links no trade, so the exit hook can never
        reach it. Called just before the next plan of that strategy opens.
      ⚠️ THE TWO ARE KEPT DISTINCT ON PURPOSE. A filled plan is closed by its
      EXIT and never by supersession; collapsing them would lose the line
      between "fired and lost" and "fired and never filled", which is exactly
      the population this ledger exists to separate.
      🔴 AND "CLOSED" HAD TO JOIN `TERMINAL`. `transition()` sets `closed_ts`
      only for states in that set and `live_plans()` selects on
      `closed_ts IS NULL`, so the first cut wrote rows reading CLOSED that the
      query still returned as live — the state saying one thing and the lookup
      another, silently.
v4.0
Owns `plan_ledger`. INTENT as a first-class record.

v4.0  2026-08-25  See docs/DERIVED_STORES.md.

**A trade is what happened. A plan is what was INTENDED.** They are different
objects and they diverge in ways that matter:

  · A plan can produce NO TRADE AT ALL — the condor decides, sets strikes, and
    the leg trigger never comes. Nothing in `trades` records that a structure
    was designed and never fired. Today that intent evaporates with the
    process.
  · A plan can produce MORE THAN ONE trade — leg 1 and leg 2 are separate rows
    and nothing links them as halves of one structure except convention.
  · A plan HAS A LIFE: DECIDED -> LEG1_FILLED -> COMPLETE, or -> CANCELLED /
    EXPIRED. Same lifecycle shape as the level ledger, same argument for a
    home: recomputation cannot reconstruct a biography.

🔴 THE PROTECTION. `IronCondorStrategy._plan` lives ONLY in memory — zero
persistence in that file. A restart at LEG1_FILLED means ONE LEG IS LIVE AT THE
BROKER AND THE BOT HAS NO MEMORY THAT A SECOND WAS PLANNED. The position
exists; the intent does not. The repo already warns about orphan legs — but
that is detecting the wreckage, not preventing it.

🔴 THE BIGGER PRIZE — MINING THE PLANS THAT NEVER EXECUTED. An unfired plan
still has a KNOWABLE OUTCOME: the market went somewhere. Score it afterwards
and every unfired plan becomes a FREE BACKTEST ON LIVE DATA — no capital, no
slippage, and the strikes were chosen in real time rather than with hindsight.

⚠️ THAT MEASURES THE TRIGGER ITSELF. If unfired plans would have won at the
same rate as fired ones, the trigger is filtering noise. If they would have
done BETTER, the trigger is costing money. That is the question behind Friday
and behind every "why didn't it fire", and it is unanswerable today.

⚠️ THE LEDGER IS THE RECORD, NOT THE AUTHORITY. On reload a plan is restored as
INTENT and must be RE-QUALIFIED against current structure. A plan resumed blind
after a twenty-minute outage is trading a fork that may no longer exist. The
ledger says what we meant; the tape says whether it is still true.

⚠️ WRITES NEVER RAISE. Same rule as every derived home: a bookkeeping failure
must not be able to affect a live position.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

# ⚠️ `MISSED` IS ITS OWN STATE AND NOT A FLAVOUR OF `WIPED_BY_RESTART` (r95).
# They are different facts and they cost different things:
#   WIPED_BY_RESTART — the plan was still WAITING on its trigger when the
#       process died. Nothing was lost that the tape can prove; the setup may
#       simply not have happened.
#   MISSED           — the trigger DID fire, on the tape, while we were down.
#       This is a real setup the fleet did not take, and it is the number that
#       answers "what do mid-session deploys and crash-loops actually cost us".
# Collapsing the two would bury the second inside the first, which is exactly
# the plausible-silence class this repo keeps finding.
#
# ⚠️ RECORDED, NEVER RESUMED — operator's ruling, 2026-08-24: "An interrupted
# firing sequence should never attempt a late entry. Log it as missed. But
# normal entries that weren't filled and weren't interrupted should keep
# trying." A MISSED row is a headstone, not a queue.
#
# Terminal reasons. ⚠️ `WIPED_BY_RESTART` IS ITS OWN CATEGORY — on 2026-08-21
# four boxes held confirmed break+retest setups at 10:20-10:24 and the 10:39
# deploy erased them. Folding that into CANCELLED would hide the cost of
# deploying mid-session, which is exactly the number worth knowing.
# 🔴 r212 — "CLOSED" JOINS THE TERMINAL SET, AND ITS ABSENCE WAS HALF THE BUG.
# `transition()` sets `closed_ts` only for a state in here, and `live_plans()`
# selects on `closed_ts IS NULL`. So a plan moved to a state NOT in this set is
# marked and updated and STILL RETURNED AS LIVE — the state says one thing and
# the query says another, silently. That is what the first cut of r212 hit: the
# rows read CLOSED with `closed_ts` NULL and the panel still showed them.
# ⚠️ THE SET IS THE AUTHORITY, NOT THE WORD. Any future terminal state must be
# added here or it will look terminal and behave live.
TERMINAL = {"FIRED", "EXPIRED", "CANCELLED", "WIPED_BY_RESTART", "COMPLETE",
            "MISSED", "CLOSED"}
LIVE = {"DECIDED", "LEG1_FILLED", "CONFIRMED", "ARMED"}


def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


class PlanLedger:
    """One row per plan. Never raises into a caller."""

    def __init__(self, store=None, symbol: str = ""):
        self._store = store
        self.symbol = symbol
        self._made = False

    def _ensure(self):
        if self._made or self._store is None:
            return
        try:
            self._store.conn.execute("""
                CREATE TABLE IF NOT EXISTS plan_ledger (
                    plan_id     TEXT NOT NULL PRIMARY KEY,
                    symbol      TEXT NOT NULL,
                    strategy    TEXT NOT NULL,
                    state       TEXT NOT NULL,
                    created_ts  REAL NOT NULL,
                    updated_ts  REAL NOT NULL,
                    closed_ts   REAL,
                    terminal_reason TEXT,
                    -- what was intended
                    direction   TEXT,
                    short_strike REAL, long_strike REAL,
                    short_put_strike REAL, long_put_strike REAL,
                    trigger_price REAL,
                    underlying_at_decision REAL,
                    expected_move REAL,
                    -- why it was intended: the derived vector at decision time
                    justification TEXT,
                    -- what happened to the tape afterwards (EOD scoring pass)
                    max_price_seen REAL, min_price_seen REAL,
                    counterfactual TEXT,
                    trade_ids   TEXT
                );""")
            self._store.conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_plan_live "
                "ON plan_ledger(symbol, state)")
            self._made = True
        except Exception as exc:                                # noqa: BLE001
            logger.debug("plan_ledger table: %s", exc)

    # ── writes ──────────────────────────────────────────────────────────
    def open_plan(self, strategy: str, state: str, ctx: dict,
                  **fields) -> Optional[str]:
        """Record a new intent. Returns plan_id, or None if unrecorded (r303: always None for a DORMANT plan)."""
        if self._store is None:
            return None
        try:
            from strategy import plan_state as _ps
            if _ps.is_dormant(strategy):
                return None
        except Exception:                                       # noqa: BLE001
            pass
        pid = uuid.uuid4().hex[:16]
        now = time.time()
        try:
            self._ensure()
            just = {
                # ⚠️ THE JUSTIFICATION IS THE POINT OF THE STUDY. Scoring an
                # unfired plan tells you IF it would have worked; the
                # justification tells you WHY it was chosen, which is what a
                # fit actually needs.
                "price": _f(ctx.get("price")),
                "adx": _f(getattr(ctx.get("trend"), "primary_adx", None)),
                "atm_iv": _f(ctx.get("atm_iv")),
                "expected_move_iv": _f(ctx.get("expected_move_iv")),
                "variance_risk_premium": _f(ctx.get("variance_risk_premium")),
                "realised_vol_cc": _f(ctx.get("realised_vol_cc")),
                "charm": _f(ctx.get("charm")),
                "vanna": _f(ctx.get("vanna")),
                # ⚠️ ctx["gex"] is a GEXSnapshot OBJECT — _f() on it yields None,
            # which is why this column has been NULL on every row ever
            # written. The scalar is `net_gex`. See derived/surface.py r140.
            "gex": _f(getattr(ctx.get("gex"), "net_gex", None)),
                "session_fraction_remaining": _f(ctx.get("session_fraction_remaining")),
                "levels": ctx.get("levels"),
                "fork": ctx.get("fork_rails"),
            }
            self._store.conn.execute(
                "INSERT OR REPLACE INTO plan_ledger (plan_id, symbol, strategy,"
                " state, created_ts, updated_ts, direction, short_strike,"
                " long_strike, short_put_strike, long_put_strike,"
                " trigger_price, underlying_at_decision, expected_move,"
                " justification) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (pid, self.symbol, strategy, state, now, now,
                 fields.get("direction"), _f(fields.get("short_strike")),
                 _f(fields.get("long_strike")), _f(fields.get("short_put_strike")),
                 _f(fields.get("long_put_strike")), _f(fields.get("trigger_price")),
                 _f(fields.get("underlying_at_decision")),
                 _f(fields.get("expected_move")),
                 json.dumps(just, default=str)))
            self._store.commit()
            logger.info("[plan] OPEN %s %s %s", pid[:8], strategy, state)
            return pid
        except Exception as exc:                                # noqa: BLE001
            logger.debug("open_plan: %s", exc)
            return None

    def transition(self, plan_id: str, state: str,
                   terminal_reason: str = "", trade_id: str = "",
                   max_price: Optional[float] = None,
                   min_price: Optional[float] = None) -> None:
        """Move a plan's state. Terminal states set closed_ts."""
        if self._store is None or not plan_id:
            return
        try:
            self._ensure()
            now = time.time()
            closed = now if state in TERMINAL else None
            row = self._store.conn.execute(
                "SELECT trade_ids FROM plan_ledger WHERE plan_id=?",
                (plan_id,)).fetchone()
            ids = json.loads(row[0]) if (row and row[0]) else []
            if trade_id and trade_id not in ids:
                ids.append(trade_id)
            self._store.conn.execute(
                "UPDATE plan_ledger SET state=?, updated_ts=?, closed_ts=?,"
                " terminal_reason=?, trade_ids=?,"
                " max_price_seen=COALESCE(?, max_price_seen),"
                " min_price_seen=COALESCE(?, min_price_seen)"
                " WHERE plan_id=?",
                (state, now, closed, terminal_reason or None,
                 json.dumps(ids), _f(max_price), _f(min_price), plan_id))
            self._store.commit()
            logger.info("[plan] %s -> %s%s", plan_id[:8], state,
                        f" ({terminal_reason})" if terminal_reason else "")
        except Exception as exc:                                # noqa: BLE001
            logger.debug("transition: %s", exc)

    # ── reads ───────────────────────────────────────────────────────────
    @staticmethod
    def _session_start() -> float:
        """CD.2 — today's session start (ET midnight), epoch s."""
        from datetime import datetime as _dt
        from zoneinfo import ZoneInfo as _Z
        return _dt.now(_Z("America/New_York")).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

    # CD.2 — a live row is this session's, or a condor leg already filled at the broker
    _LIVE_SQL = " AND closed_ts IS NULL AND (created_ts >= ? OR state = 'LEG1_FILLED')"

    def live_plans(self) -> list:
        """Every plan still pending for this symbol. Survives restarts.

        🔴 THIS IS WHAT status.py READS. `orb_state.json` is written by a
        RUNNING bot, so after a restart it reflects whatever the new process
        has rebuilt — and a condor at LEG1_FILLED with a live leg at the broker
        would show as nothing at all. The ledger is on disk independent of who
        is running.
        """
        if self._store is None:
            return []
        try:
            self._ensure()
            cur = self._store.conn.execute(
                "SELECT plan_id, strategy, state, created_ts, direction,"
                " short_strike, trigger_price FROM plan_ledger"
                " WHERE symbol=?" + self._LIVE_SQL, (self.symbol, self._session_start()))
            return [{"plan_id": r[0], "strategy": r[1], "state": r[2],
                     "created_ts": r[3], "direction": r[4],
                     "short_strike": r[5], "trigger_price": r[6]}
                    for r in cur.fetchall()]
        except Exception:                                       # noqa: BLE001
            return []

    def close_for_trade(self, trade_id: str, reason: str = "") -> Optional[str]:
        """Close the plan that produced this trade, now that the trade has.

        🔴 THE ROWS OPENED BY `PlanTick.take()` WERE NEVER CLOSED BY ANYTHING.
        `transition()` had exactly two callers — main.py's ORB plan and the
        condor's `_plan_id` — so every plan opened through `Plan._ledger_open`
        (runaway, sweep, butterfly, TCS, condor leg two) kept `closed_ts` NULL
        for the life of the session. `live_plans()` therefore returned each one
        forever, and status.py printed all of them as `<- LIVE`.
        ⚠️ MEASURED, NOT REASONED: QQQ on 2026-09-01 showed SEVEN
        `RunawayContinuation TRIGGERED @ 708.43` rows all flagged LIVE while
        six of those trades had closed hours earlier.
        🔴 AND r199 MISDIAGNOSED IT. It saw two rows for one strategy at one
        trigger, called it duplication, and collapsed them for display with a
        warning naming the count. They were not duplicates — they were two real
        plans, neither of which had been closed. The collapse was hiding
        distinct plans that happened to share a trigger price, which is why the
        fix is here and not in the panel.

        ⚠️ FOUND BY trade_id, NOT BY STRATEGY. `link_trade` resolves the most
        recent live plan and records that as an ⟨ASSUMPTION⟩; closing has an
        exact key available — the trade that just ended — so it uses it and
        inherits none of that heuristic's risk.
        """
        if self._store is None or not trade_id:
            return None
        try:
            self._ensure()
            cur = self._store.conn.execute(
                "SELECT plan_id, trade_ids FROM plan_ledger"
                " WHERE symbol=?" + self._LIVE_SQL, (self.symbol, self._session_start()))
            for pid, tids in cur.fetchall():
                if not tids:
                    continue
                try:
                    ids = json.loads(tids) or []
                except Exception:                              # noqa: BLE001
                    continue
                if trade_id in ids:
                    self.transition(pid, "CLOSED", reason or "trade closed")
                    return pid
            return None
        except Exception as exc:                               # noqa: BLE001
            # ⚠️ NEVER RAISES INTO log_exit. A bookkeeping failure must not
            # stop a position from being booked closed.
            logger.warning("[plan] close_for_trade failed for %s: %s",
                           trade_id[:8], exc)
            return None

    def close_unfilled(self, strategy: str, reason: str) -> int:
        """Close any live plan of this strategy that never got a fill.

        🔑 THE SECOND LEAK. A plan that FIRES but whose entry is then refused —
        sizing rejection, no priced contract, a failed order — links no trade,
        so `close_for_trade` never reaches it and it stays live for the
        session. Called just before a new plan of the same strategy opens: by
        then the previous fire has resolved either way, because `take()` and
        the entry attempt happen on the same tick.

        ⚠️ ONLY ROWS WITH NO TRADE. A plan that HAS a trade_id is closed by the
        exit, not by being superseded — collapsing the two would lose the
        difference between "fired and lost" and "fired and never filled",
        which is exactly the population the plan ledger exists to keep.
        ⚠️ ORB IS NOT AFFECTED. It sets `self_ledgers`, so `_ledger_open`
        returns early and main.py owns its rows and their EXPIRED transition.
        """
        if self._store is None:
            return 0
        n = 0
        try:
            self._ensure()
            for p in self.live_plans():
                if p.get("strategy") != strategy:
                    continue
                cur = self._store.conn.execute(
                    "SELECT trade_ids FROM plan_ledger WHERE plan_id=?",
                    (p["plan_id"],))
                row = cur.fetchone()
                if row and row[0] and json.loads(row[0] or "[]"):
                    continue                    # it filled; the exit closes it
                self.transition(p["plan_id"], "EXPIRED", reason)
                n += 1
        except Exception as exc:                               # noqa: BLE001
            logger.warning("[plan] close_unfilled failed for %s: %s",
                           strategy, exc)
        return n

    def link_trade(self, strategy: str, trade_id: str) -> Optional[str]:
        """Attach a filled trade to the LIVE plan that produced it.

        🔴 THE JOIN THAT WAS BUILT AND NEVER CONNECTED (r144). `trade_ids` has
        been a column since this file was written, `transition()` has accepted
        a `trade_id` argument the whole time, and the append logic is correct —
        and NOTHING IN THE REPO EVER CALLED IT WITH ONE. Measured 2026-08-26:
        863 plans across 15 boxes, ZERO with a trade_id.
        ⚠️ WHAT THAT COSTS IS THE VISION'S ENTIRE METRIC. docs/VISION.md: *"P&L
        and return on risk. Dollars."* Without this link a plan records what it
        EXPECTED and the trade records what it RETURNED, and nothing joins the
        two — so "did TAKE plans make money" is unanswerable, and any R floor
        fitted from declared R alone is the anti-goal that document exists to
        forbid: the engine measured against its own outputs.

        ⚠️ LOOKED UP, NOT THREADED. Plan ids live in three different places
        (`state._orb_plan_id`, `IronCondorStrategy._plan_id`,
        `PlanEngine._declared`), so requiring every call site to pass one is a
        rule the next strategy will forget — the same failure that left the
        sweep on 11:11 and the butterfly on 11:00. Resolving it here means a
        new strategy is linked by existing.

        ⚠️ ⟨ASSUMPTION⟩ MOST-RECENT-LIVE-PLAN-OF-THAT-STRATEGY. When two plans
        of one strategy are live at once — both condor legs — this attaches to
        the newer. That is a heuristic, not a proof, and it is recorded as one:
        a caller holding an exact plan_id should call `transition()` directly.
        """
        if self._store is None or not trade_id:
            return None
        try:
            cands = [p for p in self.live_plans()
                     if not strategy or p.get("strategy") == strategy]
            if not cands:
                logger.debug("[plan] no live plan for %s — trade %s unlinked",
                             strategy, trade_id[:8])
                return None
            pid = max(cands, key=lambda p: p.get("created_ts") or 0)["plan_id"]
            cur = self._store.conn.execute(
                "SELECT trade_ids FROM plan_ledger WHERE plan_id=?", (pid,))
            row = cur.fetchone()
            ids = []
            if row and row[0]:
                try:
                    ids = json.loads(row[0]) or []
                except Exception:                              # noqa: BLE001
                    ids = []
            if trade_id in ids:
                return pid
            ids.append(trade_id)
            self._store.conn.execute(
                "UPDATE plan_ledger SET trade_ids=? WHERE plan_id=?",
                (json.dumps(ids), pid))
            self._store.commit()
            logger.info("[plan] linked trade %s -> plan %s (%s)",
                        trade_id[:8], pid[:8], strategy)
            return pid
        except Exception as exc:                               # noqa: BLE001
            logger.warning("[plan] link_trade failed for %s/%s: %s",
                           strategy, trade_id[:8], exc)
            return None

    def mark_restart_wipe(self) -> int:
        """Called at boot: any plan left LIVE by a dead process is recorded.

        ⚠️ IT IS RECORDED, NOT RESUMED. The row keeps WIPED_BY_RESTART so the
        cost of deploying mid-session becomes a countable number — four boxes
        lost confirmed setups to the 10:39 deploy on 2026-08-21 and nothing
        wrote that down.
        ⚠️ CONDOR PLANS AT LEG1_FILLED ARE **NOT** WIPED — a leg is live at the
        broker, so the intent must survive for the reconciler to act on. Those
        are left open and re-qualified.
        """
        if self._store is None:
            return 0
        try:
            self._ensure()
            cur = self._store.conn.execute(
                "SELECT plan_id, state FROM plan_ledger"
                " WHERE symbol=? AND closed_ts IS NULL", (self.symbol,))
            n = 0
            for pid, state in cur.fetchall():
                if state == "LEG1_FILLED":
                    continue                     # real money on — keep it open
                self.transition(pid, "CANCELLED", "WIPED_BY_RESTART")
                n += 1
            if n:
                logger.warning("[plan] %d pending plan(s) lost to a restart — "
                               "recorded as WIPED_BY_RESTART", n)
            return n
        except Exception:                                       # noqa: BLE001
            return 0
