"""
strategy/plan.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v2.8 2026-10-19  OTV4TEST r303 (PSTATE.1) — A DORMANT PLAN WRITES NOTHING. The operator, 2026-10-19 08:43 ET: "The intent is dormant plans should not write to the ledger, unless we are studying them as 'log only'". strategy/plan_state.py decides each plan's state (active / log / dormant); here, a DORMANT name gets no plan_tick or plan_check row (write_row), no INACTIVE row from close_tick, no plan_heartbeat upsert, and no place on the [plans] line; CondorManagement / CreditRoll leave the line while they have no credit position (the "legs" check both already record, kept per plan by _close as _last_checks). A LOG plan is OBSERVED (strategy/observe.is_active), so take() writes LOG-ONLY as r254 does. AND A CONDITION-GATED PLAN WRITES NOTHING WHILE ITS CONDITION IS ABSENT (the operator, 09:54 ET: "Yes"): a /manage plan or CondorManagement / CreditRoll that was not run this tick gets no INACTIVE row (and no "dispatch gap" default) and no heartbeat, and the condor plans' "legs" < 1 HOLD rows are not written; they write the moment a position of theirs is open, and NO PLAN (asked, wrote nothing) still reports. Nothing here decides a trade. tests/check_plan_states.py.
v2.7 2026-10-06  OTV4TEST r258 (HYG.17) — A NON-WINDOW REASON THAT COMES BACK DECLARES ITSELF. _status_changed kept every token of an inactive episode in one SET, so a reason said once was silent for the rest of the episode: SPX-TEST's Breakout/manage went "no open position" -> "position open — managing" -> "no open position" (10:14 / 10:42 / 10:49 ET 10-06) and the return was never written - plan.last(), the heartbeat and the [plans] line read "managing" on a flat book until 16:00 (_STATUS held the truth). The operator's r42 rule is two-sided: the WINDOW is said once per episode; "if something other than the window made it inactive it should declare that". So a non-window token is now written whenever it differs from the LAST token written for that plan (_LAST_SAID); the window keeps its once-per-episode set exactly as before (window -> cap -> window is still two rows). DISPLAY ONLY - traced 10-06: no trading path reads plan.last(), plan_heartbeat, the latest plan_tick, _STATUS or plan_status(). tests/check_plan_status.py S13-S15 (born red on 2feb827).
v2.6 2026-10-05  OTV4TEST r254 (OBS.1) — THE PLAN ALWAYS LOOKS, THE STRATEGY IS GATED ON THE HOUR: Breakout, Runaway and the Hunt are OBSERVED from their entry end to 15:40 - asked, recorded LOG-ONLY, never executed (the operator, 2026-10-05: "the plan always looks, but the strategies are gated on the hour of the day"; "Have those blocked TRADES just to Log only"). Here: take() writes LOG-ONLY for an observed strategy - never TAKE, no plan_ledger row, no gate-report clear.
v2.5  2026-10-03  OTV4TEST r211 (PLN.2) — EVERY TAKE OPENS ITS PLAN_LEDGER ROW. The ledger held ORB plans and nothing else
      (19 of 20 real rows), for two reasons, both in `_ledger_open`: (1) r6 returned whenever a store was BOUND,
      calling that "tests, not the box" - but the plan board binds the box's own store at start, so the guard
      switched the ledger off in production too; (2) nine plans pass self_ledgers=True and only two strategies
      (the ORB via main, the condor) ever open their own rows. Now: the row is written THROUGH THE BOUND STORE
      (a checker's scratch store takes its own rows; the box's takes the box's), and only the names in
      OWN_LEDGER skip it. ledger_open() is the public door for a strategy that fires without take() (ORCS).
      The operator, 2026-10-03: "Gather as much as is available to serve our studies and backtests".
v2.4  2026-10-03  OTV4TEST r197 (AUD.6) — plan_check GAINS `note TEXT`, AND A CHECK'S TEXT IS STORED IN IT.
      `value` is REAL: write_row cast each reading to float or wrote NULL, and `note=` was appended
      to the tick's reason and stored nowhere per check - so break_dir, pool_name, verdict,
      contract, engine_state, fork... were NULL on every row ever. The column is added by CREATE
      and by an in-place ALTER (old rows read NULL, as tick_id did in r177). `value` and `verdict`
      are untouched. Pinned by tests/check_plan_check_note.py.
v2.3  2026-09-21  OTV4TEST r84 — `skipped_all` carries a gate, forwarded to
      `_SKIP_GATE` exactly as `skipped()` has since r42. Without it the board
      could name only the clock.
v2.2  2026-09-21  OTV4TEST r83 — `plan_heartbeat`: one row per
      plan, UPSERTED every tick, so liveness is a FACT rather than an
      inference from row age. ⚠️ r41's ruling governs the LEDGER; this is
      CURRENT STATE and cannot grow. The gate is CARRIED from both mechanisms
      (`_report_block` and `_SKIP_GATE`) so the board never parses prose.
v2.1  2026-09-18  OTV4TEST r42 — THE OPERATOR'S ASYMMETRY. 2026-09-18: *"if
      something other than the window made it inactive it should declare that,
      but if it's the window, I just need to see that once not repeatedly."*
      WINDOW is announced ONCE PER INACTIVE EPISODE (an episode ends when the
      plan next goes WORKING); every other gate declares itself.
      ⚠️ IT NEEDS A PER-EPISODE SET, NOT A LAST-VALUE SLOT, AND THAT IS THE
      WHOLE SUBTLETY. With one remembered state, `window -> cap -> window`
      RE-ANNOUNCES window, because the slot holds `cap` and window looks like a
      change. S10 is that exact sequence and demands two rows, not three.
      ⚠️ KEYED ON THE GATE, NEVER ON THE PROSE. `skipped()` takes `gate` as its
      own field; recovering it by parsing the reason sentence is how this rule
      would silently stop working the first time someone reworded a message.
      S12 phrases the window refusal three ways and demands one row.
v2.0  2026-09-18  OTV4TEST r41 — EVERY PLAN IS WORKING OR INACTIVE, AND INACTIVE
      SAYS SO ONCE. Operator, 2026-09-18: *"Because we know a plan is inactive
      outside its window, I don't need 10k rows explaining why. I just need 1,
      so I'm aware it at least 'Knows' — each plan should have a current status
      as either 'working' or 'inactive' and if it's working, I want per tick
      logging. If inactive it should just say that, once, until it becomes
      active."*
      🔑 THE ROW IS EDGE-TRIGGERED NOW, NOT LEVEL-TRIGGERED. `close_tick` wrote
      one row per idle plan per TICK; it writes one per TRANSITION. A plan that
      spoke this tick is WORKING and keeps its per-tick row — that half is
      deliberately untouched, because a working plan's row is the one he reads.
      MEASURED on 2026-09-17: 11,931 of 17,585 plan_tick rows were the idle
      restatement, and the top reason alone ("no options chain this tick")
      accounted for 3,672 of them.
      ⚠️ THE STATE IS (day, verdict, reason), NOT MERELY "inactive", AND THAT IS
      A READING OF "once" RATHER THAN A LOOPHOLE. A plan that moves from
      "outside its window" to "catastrophic cap broken" is inactive for a
      DIFFERENT reason, and that is new information about the box; silence there
      would hide a state change behind a rule written to remove noise. A stable
      inactive state still writes exactly one row.
      ⚠️ THE `NO PLAN` WARNING IS EDGE-TRIGGERED TOO. It is a defect report, and
      repeating it every tick for a session is the same noise one channel over —
      which is how a real defect gets filtered out of the log (§17).
      ⚠️ AND THE VERDICT IS `INACTIVE`, NOT `NOT ASKED` — r213 recorded his
      objection to that wording (*"Not asked? why or Why not?"*) and this is the
      column finally holding a STATUS, which is what he asked for both times.
v1.9  2026-09-09  OTV4TEST r6 (HYG.4) — `_ledger_open` returns when a store is BOUND
      (tests): the box's plan_ledger carried TestStrat rows written by the
      lander's checks. A bound store means "not the box".
v1.8  2026-09-03  r231 — `PlanTick.level()` takes `spot` and passes it to
      `classify()`, which now requires it. Geometry asks role-vs-PRICE as well
      as role-vs-range (operator, 2026-09-03), and a level price has already
      traversed is invalidated. Required, not optional: an optional parameter
      is an invalidation a caller can omit without anything saying so.
v1.7  2026-09-01  r213 (chunk E) — EVERY SKIP NAMES ITSELF. Operator,
      2026-09-01: *"I don't like 'NOT ASKED' as a reason. It makes no sense.
      Not asked? why or Why not?"*
      🔴 THE CAUSE WAS A GAP, NOT WORDING. `CondorManagement`, `CreditRoll`
      and every `<Strategy>/manage` row are driven ONLY from main.py's
      `has_open_position()` branch, and no skip site named them — so on a flat
      box they fell to the default on every tick of every session. The other
      half of that same branch already said the reverse out loud ("position
      open — managing; only the second-leg window asks the credit
      strategies"): one direction had a sentence, the other did not.
      ⚠️ AND A `/manage` ENTRY OUTLIVES ITS POSITION — REGISTRY persists for
      the life of the process, so once a strategy has managed anything its row
      keeps reporting for the rest of the day.
      · `skipped_management(reason)` names them all, by REGISTRATION rather
        than by a name list in another file — r35's allow-list rot, where the
        list held three names, two of which had been deleted, while the live
        strategy was silently exempt.
      · `setdefault`, not assignment: a plan already skipped for a specific
        cause keeps that cause.
      🔑 AND THE FALLBACK ADMITS WHAT IT IS. It fires only where main.py named
      nothing, so it now reads as a DISPATCH GAP rather than a market
      condition — r73 one level up: a refusal that cannot say which rung
      refused it is worse than no refusal, because it gets trusted anyway.
v1.6
v1.6  2026-09-01  r212 (chunk D) — `_ledger_open` SUPERSEDES THE PREVIOUS
      UNFILLED PLAN of the same strategy before opening a new one. A plan that
      FIRES and is then refused downstream (sizing rejection, no priced
      contract, a failed order) links no trade, so the exit-side close can
      never reach it and it stayed live all session. Safe here because `take()`
      and the entry attempt happen on the SAME tick.
      ⚠️ ROWS THAT FILLED ARE UNTOUCHED — those close on their exit. See
      derived/plan_ledger.py v4.1.
v1.5
v1.5  2026-08-29  r177: tick_id (begin_tick's monotonic counter) persisted on
      plan_tick and plan_check — the vector<->plan join becomes BY KEY, not by
      timestamp coincidence, before the first fit. In-place ALTER migration;
      pre-r177 rows read 0, which no join should match.
v1.4  2026-08-27  r165: ensure_tables() guards with a flag on the store, not
      id(store) in a set — recycled ids let a fresh store skip CREATE TABLE
      and every row write failed "no such table" (seen in a test that opens a
      store per call; the same class could bite a store re-opened in-process).
v1.3  2026-08-27  r163: the DailyFork aliases retire with the strategy.
v1.2  2026-08-27  r160: DISPATCH_ALIAS — SweepForLeg2 -> SweepCreditSpread; the
      CondorLeg2 alias retires with the deleted level-selection.
v1.1  2026-08-26  r147: DISPATCH_ALIAS — the second-leg window now has one
      caller (CondorLeg2nd -> the condor's leg-2 plan, name `CondorLeg2`);
      the three retired second-leg aliases are removed.
v1.0  2026-08-26  r146 — THE PLAN, REBUILT AS THE OPERATOR SPECIFIED IT.
      Replaces the seven parallel strategy re-implementations that lived in
      `derived/plans.py` r126-r145 (1,200 lines, zero calls into strategy/).
      The recording layer from that file is carried over intact; the
      decision logic is not, because the STRATEGY is the decision.

════════════════════════════════════════════════════════════════════════════
WHAT A PLAN IS — operator, 2026-08-26, verbatim
════════════════════════════════════════════════════════════════════════════
*"The strategy is the spec, the specification. The plan is how it executes
according to the spec."* And: *"I don't need two strategies for every
strategy. I need a strategy, which is the specification, and the plan, that
plans on how to execute it and is verbose about every decision it's making
on each tick."*

And the purpose, in his words: the plan says *"if X happens on the next tick,
we are choosing strikes and calculating r-values (risk:reward) and gating on
1:1, but under relaxed entry rules the gate would still record the value but
not veto"* — and it *"deconflicts competing valid strategies by invalidating
levels or strikes on geometry or economics."* *"The spec is how the setup
functions, but the plan exists to account for other emergent factors that
are antagonistic to the strategies' execution."*

    STRATEGY  = the spec. Detects the setup, fixes the trigger and the
                invalidation, names the level, selects the contracts,
                EXECUTES. It is the only decision path.
    PLAN      = the informer the strategy consults. Prices the what-if
                (credit/debit, risk, R), runs the antagonistic checks
                (geometry against the session map, the R hurdle, the
                clock), RECORDS every check every tick, and hands back a
                verdict the strategy honours.

⚠️ THE PLAN NEVER DETECTS A SETUP AND NEVER SELECTS A STRIKE. If it did, it
would be a second implementation of the strategy — the thing that was
delivered by mistake and had to be torn out. The plan is told what the
strategy found and prices THAT.

⚠️ THE PLAN'S VERDICT IS CONSULTED, NOT DECORATIVE. Under STRICT criteria a
plan that cannot clear the R hurdle REFUSES, and the strategy returns None.
Under RELAXED the R value is recorded, the verdict reads MUTED, and the
strategy proceeds — `strategy/criteria.py` owns that switch and this file
only calls it. The old engine could not affect a trade by design and so
measured nothing that mattered.

════════════════════════════════════════════════════════════════════════════
THE SHAPE OF A STRATEGY'S TICK, and every strategy is written this way
════════════════════════════════════════════════════════════════════════════
    t = self.planner.tick(price_now, direction=...)
    if <spec gate fails>:            return t.refuse("gate_name", "why")
    if <input missing>:              return t.starved("chain")
    ok = t.level(level_price, role, name, orb_high, orb_low, price_now)  # geometry
    if not ok:                        return t.refuse("geometry", t.last_why)
    t.credit_spread(short_k, long_k, credit, invalidation=...)  # the what-if
    ok, why = t.executable()          # the R hurdle, strict/relaxed aware
    if not ok:                        return t.refuse("r_hurdle", why)
    return t.take(signal)

Every terminal — refuse / starved / take / hold — writes the row for this
strategy on this tick, feeds `analysis/gate_report` (edge-triggered log), and
returns what the strategy should return. So `return t.refuse(...)` IS the
refusal, and a strategy cannot refuse without saying why.

════════════════════════════════════════════════════════════════════════════
THE RECORD — carried over from r126b, the split is the whole design
════════════════════════════════════════════════════════════════════════════
  `plan_tick`   THE SPINE. One row per strategy per tick: verdict, reason,
                trigger, invalidation, spot, distance to trigger, R.
                Shared columns, because comparing R ACROSS strategies at one
                instant is the point.
  `plan_check`  LONG FORMAT. One row per variable per strategy per tick, with
                its own PASS/FAIL, so an elimination is a queryable row.
                A check that could not be measured is written NULL / n/a —
                NEVER 0.0/PASS (the VW.1 lesson; pinned by check_plan_wiring).

VERDICTS: TAKE · DECLINE · NO PLAN (input starved) · NOT ASKED (the
dispatch never called this strategy this tick — recorded by the board with
the dispatcher's reason) · HOLD / ROLL / CLOSE (management).
A TAKE under a muted R hurdle is still a TAKE — it was taken — and carries
the `r_muted` check PASS and a reason beginning "R hurdle MUTED (relaxed)",
so the relaxed population is separable by query, never by guess.

⚠️ ONE ROW PER STRATEGY PER TICK, ALWAYS. The board (`derived/plans.py`)
closes each tick: any registered strategy that wrote nothing gets a NOT ASKED
row carrying the reason main.py gave, or, if the strategy WAS asked and
still wrote nothing, a row saying so — that row is the canary for an
unwired `return None`.

⚠️ WRITES NEVER RAISE. A bookkeeping failure cannot change a verdict; the
verdict is computed first and the write is wrapped.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass       # r158 — the Permission carrier
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ── WA §36 GATE CATEGORIES ──────────────────────────────────────────────
# This file OWNS NO GATE CONSTANT. Every threshold a plan applies belongs to
# the strategy that calls it (its own GATES dict) or to strategy/criteria.py
# (R_FLOOR, FOUNDATIONAL). An empty declaration is the honest one, and
# tests/check_gates.py will refuse any relaxed.widen()/window() call here.
GATES = {}

# ── the tick clock, shared by every plan in the process ─────────────────
# One number per tick, set by the board at the assembly point, so every
# strategy's row for a tick carries the SAME ts and joins across strategies
# are exact rather than "within a second".
_TICK: Dict[str, Any] = {"n": 0, "ts": 0.0}

# strategy name -> Plan, so the board can close a tick for everyone
REGISTRY: Dict[str, "Plan"] = {}

# main.py's `_safe_strategy` labels -> the strategy name the plan writes under
# r213 — plans that only run while something is open. Named here rather than
# in main.py so a new management plan is covered by REGISTERING, not by
# remembering to add it to a list in another file (the r35 allow-list rot).
_MANAGEMENT_PLANS = {"CondorManagement", "CreditRoll"}

DISPATCH_ALIAS = {
    "ORB": "ORBStrategy",
    "CondorPlan": "IronCondorStrategy",
    "CondorLeg": "IronCondorStrategy",
    # the second-leg window (main_loop, position open) — r160: the sweep is
    # asked under the condor's authorization and writes under its own name
    "SweepForLeg2": "SweepCreditSpread",
}


# ⚠️ LAST DORMANT (strategy, gate, reason) PER STRATEGY. Module-level because
# a strategy object is rebuilt per tick in some paths; keyed by strategy name so
# a genuine CHANGE of reason always writes.
_DORMANT: dict = {}


def clear_dormant(strategy: str = "") -> None:
    """Forget the dormant state so the next tick writes again. Called when a
    window OPENS, so the transition into tradeable is always recorded."""
    if strategy:
        _DORMANT.pop(strategy, None)
    else:
        _DORMANT.clear()


@dataclass
class Permission:
    """What an informing plan hands to an executing strategy. NOT a trade.

    ⚠️ NO CONTRACTS, NO STRIKES, NO PREMIUM. A side, a level, its provenance
    and the reason. The strategy asked to act on it does its own construction
    under its own rules — which is the whole point of the split.
    """
    side: str = ""
    level: float = 0.0
    source: str = ""
    plan_id: Any = None
    why: str = ""


def begin_tick(ts: Optional[float] = None) -> int:
    """Advance the tick clock. Called ONCE per tick by the board."""
    _TICK["n"] += 1
    _TICK["ts"] = float(ts or time.time())
    return _TICK["n"]


def tick_now() -> Tuple[int, float]:
    return _TICK["n"], _TICK["ts"]


def _n(v, spec: str = ".2f") -> str:
    """Format a value that may be None. None renders as 'n/a', never raises.

    🔴 THE 2026-08-26 CRASH, kept as doctrine: every `why` string formatted
    `r`, `credit` and the strikes with `{x:.2f}`. Under RELAXED entries
    `r_verdict(None)` returns MUTED — NOT FAIL — so execution fell into the
    f-string with r=None and raised on all 15 boxes every tick for a session.
    A value that can be absent must be absent-safe EVERYWHERE it is read.
    """
    if v is None:
        return "n/a"
    try:
        return format(v, spec)
    except Exception:                                          # noqa: BLE001
        return str(v)


_BOUND_STORE = {"store": None}


def bind_store(store) -> None:
    """The board (derived/plans.py) binds the box's derived store here at
    init, so every strategy's plan and the board write ONE store. Tests bind
    an in-memory store the same way."""
    _BOUND_STORE["store"] = store
    for p in REGISTRY.values():
        p._store = store


def _store():
    if _BOUND_STORE["store"] is not None:
        return _BOUND_STORE["store"]
    try:
        from data.derived_store import get_derived_store
        return get_derived_store()
    except Exception:                                          # noqa: BLE001
        return None


def _symbol() -> str:
    try:
        from config import INSTRUMENT
        return str(INSTRUMENT)
    except Exception:                                          # noqa: BLE001
        return ""




def _dormant(name: str) -> bool:
    """r303 (PSTATE.1) — is `name` switched DORMANT (writes nothing)? An error reads False: the row is
    written, which is the old behaviour, never a lost decision."""
    try:
        from strategy import plan_state as _ps
        return _ps.is_dormant(name)
    except Exception:                                          # noqa: BLE001
        return False


def _condition_plan(name: str) -> bool:
    """r303 — a CONDITION-gated plan: run only while a position of its own is open (the /manage plans) or a
    credit position is (CondorManagement, CreditRoll)."""
    n = str(name or "")
    return n.endswith("/manage") or n in _MANAGEMENT_PLANS


def ensure_tables(store) -> bool:
    """CREATE IF NOT EXISTS, at first use — an empty table is a measurement,
    a missing table is a mystery (r133)."""
    if store is None:
        return False
    # v1.4 — the guard is a flag ON THE STORE, not `id(store)` in a set: ids
    # are recycled after garbage collection, so a fresh store could inherit a
    # dead one's "already made" and write into tables that do not exist.
    if getattr(store, "_plan_tables_ready", False):
        return True
    try:
        store.conn.execute("""
            CREATE TABLE IF NOT EXISTS plan_tick (
                ts_epoch     REAL NOT NULL,
                symbol       TEXT NOT NULL,
                strategy     TEXT NOT NULL,
                verdict      TEXT NOT NULL,      -- TAKE / DECLINE / MUTED / NO PLAN / NOT ASKED / HOLD / ROLL / CLOSE
                reason       TEXT,
                trigger_price   REAL,            -- FROZEN by the strategy
                invalidation    REAL,            -- FROZEN by the strategy
                underlying      REAL,            -- LIVE
                dist_to_trigger REAL,            -- LIVE
                r_now           REAL,            -- LIVE, comparable ACROSS plans
                direction    TEXT NOT NULL DEFAULT '',
                tick_id      INTEGER DEFAULT 0,   -- r177: the join key
                PRIMARY KEY (ts_epoch, symbol, strategy, direction)
            );""")
        store.conn.execute("""
            CREATE TABLE IF NOT EXISTS plan_check (
                ts_epoch  REAL NOT NULL,
                symbol    TEXT NOT NULL,
                strategy  TEXT NOT NULL,
                check_name TEXT NOT NULL,
                value     REAL,
                verdict   TEXT,                  -- PASS / FAIL / n/a
                tick_id   INTEGER DEFAULT 0,     -- r177: the join key
                direction TEXT NOT NULL DEFAULT '',
                note      TEXT,                  -- r197: the check's text (verdict, side, contract...)
                PRIMARY KEY (ts_epoch, symbol, strategy, direction, check_name)
            );""")
        # 🔴 r83 — LIVENESS IS A FACT, NOT AN INFERENCE FROM ROW AGE.
        # The board asked "is this plan stale?" by comparing the newest
        # plan_tick row against a 300-second cut — which measures WHETHER THE
        # REASON TEXT CHANGED, not whether the plan ran. r41 made plan rows
        # EDGE-TRIGGERED by ruling, so a correctly-quiet plan writes nothing
        # and turns "stale" five minutes later. MEASURED 2026-09-21 14:44:
        # 16 of 18 rows flagged ⚠️ STALE and ALL 16 WERE BEHAVING CORRECTLY;
        # the only two that read "fresh" were the two whose reason embeds live
        # prices, so every tick is a new string. The marker was measuring
        # punctuation.
        # ⚠️ ONE ROW PER PLAN, UPSERTED — NOT AN APPEND. r41's ruling was about
        # the LEDGER (history); this is CURRENT STATE and it cannot grow. The
        # table is bounded by the number of plans, forever.
        store.conn.execute("""
            CREATE TABLE IF NOT EXISTS plan_heartbeat (
                symbol    TEXT NOT NULL,
                plan      TEXT NOT NULL,
                ts_epoch  REAL NOT NULL,
                tick_id   INTEGER DEFAULT 0,
                state     TEXT NOT NULL DEFAULT '',   -- EVALUATING / IDLE / NO PLAN
                gate      TEXT NOT NULL DEFAULT '',   -- the gate holding it, if IDLE
                verdict   TEXT NOT NULL DEFAULT '',
                watching  TEXT,                       -- what it is reading, verbatim
                PRIMARY KEY (symbol, plan)
            );""")
        store.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_plan_tick "
            "ON plan_tick(symbol, strategy, ts_epoch)")
        store.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_plan_check "
            "ON plan_check(symbol, strategy, check_name, ts_epoch)")
        store.commit()
        # r177 — MIGRATE IN PLACE: stores created before the tick_id column
        # gain it here; existing rows read 0, which no join should match.
        for _tbl in ("plan_tick", "plan_check"):
            try:
                store.conn.execute(f"ALTER TABLE {_tbl} ADD COLUMN tick_id INTEGER DEFAULT 0")
                store.commit()
            except Exception:                                   # noqa: BLE001
                pass                                            # already present
        # r197 — the same in-place migration for plan_check.note; old rows read NULL.
        try:
            store.conn.execute("ALTER TABLE plan_check ADD COLUMN note TEXT")
            store.commit()
        except Exception:                                       # noqa: BLE001
            pass                                                # already present
        try:
            store._plan_tables_ready = True
        except Exception:                                       # noqa: BLE001
            pass
        return True
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("plan tables could not be created: %s", exc)
        return False


def write_row(store, symbol: str, ts: float, strategy: str, verdict: str,
              reason: str, direction: str = "", trigger=None,
              invalidation=None, underlying=None, r=None,
              checks: Optional[Dict[str, Tuple[Any, Optional[bool]]]] = None,
              check_notes: Optional[Dict[str, str]] = None
              ) -> bool:
    """One spine row plus its check rows. Never raises; returns False on a
    failed spine write (and WARNS — a lost row is data lost, r133). r303: a DORMANT plan's row is not
    written at all (returns False, silently - its silence is announced once at start, by name)."""
    if _dormant(strategy):
        return False
    if store is None or not ensure_tables(store):
        return False
    try:
        dist = None
        if trigger is not None and underlying is not None:
            try:
                dist = float(underlying) - float(trigger)
            except (TypeError, ValueError):
                dist = None
        store.conn.execute(
            "INSERT OR REPLACE INTO plan_tick (ts_epoch, symbol, strategy,"
            " verdict, reason, trigger_price, invalidation, underlying,"
            " dist_to_trigger, r_now, direction, tick_id)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (ts, symbol, strategy, verdict, reason, trigger, invalidation,
             underlying, dist, r, direction or "", _TICK["n"]))
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("plan_tick write FAILED for %s: %s: %s",
                       strategy, type(exc).__name__, exc)
        return False
    for name, (val, ok) in (checks or {}).items():
        # ⚠️ ABSENT, NOT ZERO. ok=None means unmeasured -> NULL / n/a.
        v = None
        if val is not None:
            try:
                v = float(val)
            except (TypeError, ValueError):
                v = None
        verdict_c = "n/a" if ok is None else ("PASS" if ok else "FAIL")
        # r197 (AUD.6) — THE TEXT IS KEPT. `value` is REAL, so a check whose reading is
        # a word (a side, a verdict, a contract, a level's name) stored NULL and its
        # note= was never written anywhere: break_dir, pool_name, verdict, contract,
        # engine_state... were NULL on every row ever. The note= wins; else a value
        # that would not cast to a number is kept as its own text.
        note_c = (check_notes or {}).get(name)
        if not note_c and val is not None and v is None:
            note_c = str(val)
        note_c = (str(note_c)[:300] if note_c else None)
        try:
            store.conn.execute(
                "INSERT OR REPLACE INTO plan_check (ts_epoch, symbol,"
                " strategy, check_name, value, verdict, direction, tick_id, note)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (ts, symbol, strategy, name, v, verdict_c, direction or "", _TICK["n"], note_c))
        except Exception as exc:                                # noqa: BLE001
            logger.debug("plan_check write failed %s/%s: %s", strategy, name, exc)
    try:
        store.commit()
    except Exception:                                           # noqa: BLE001
        pass
    return True


class PlanTick:
    """One strategy's narration for one tick. Built by `Plan.tick()`."""

    def __init__(self, plan: "Plan", spot: Optional[float], direction: str):
        self.plan = plan
        self.strategy = plan.strategy
        self.direction = direction or ""
        self.spot = spot
        self.n, self.ts = tick_now()
        self.checks: Dict[str, Tuple[Any, Optional[bool]]] = {}
        self.check_notes: Dict[str, str] = {}      # r197: each check's own note, for plan_check.note
        self.notes: list = []
        self.trigger: Optional[float] = None
        self.invalidation: Optional[float] = None
        self.r: Optional[float] = None
        self.credit: Optional[float] = None
        self.debit: Optional[float] = None
        self.risk: Optional[float] = None
        self.reward: Optional[float] = None
        self.short_strike: Optional[float] = None
        self.long_strike: Optional[float] = None
        self.last_why: str = ""
        self.closed = False
        self.verdict: str = ""

    # ── narration ──────────────────────────────────────────────────────
    def check(self, name: str, value=None, ok: Optional[bool] = None,
              note: str = "") -> "PlanTick":
        """Record one measured variable. ok=None means UNMEASURED (NULL/n/a)."""
        self.checks[name] = (value, ok)
        if note:
            self.notes.append(note)
            self.check_notes[name] = str(note)     # r197
        else:
            self.check_notes.pop(name, None)       # a re-check without a note drops the old one
        return self

    def note(self, text: str) -> "PlanTick":
        self.notes.append(text)
        return self

    def anchor(self, trigger=None, invalidation=None) -> "PlanTick":
        """The structural prices the STRATEGY fixed. Frozen — the plan never
        moves them. Recorded so `dist_to_trigger` is answerable."""
        if trigger is not None:
            self.trigger = float(trigger)
        if invalidation is not None:
            self.invalidation = float(invalidation)
        return self

    # ── geometry: the session-map deconfliction ────────────────────────
    def level(self, price, role_or_kind: str, name: str,
              orb_high, orb_low, spot) -> Optional[bool]:
        """Is this level usable for the side its SOURCE says? Records the
        check. Returns True / False / None (unmeasured — no opening range).

        ⚠️ None IS NOT A PASS. The caller decides what an unmeasured map
        means for its trade; the default in every credit strategy is to
        proceed and say so, because refusing every trade before 09:35 on a
        missing marker would be a clock gate wearing geometry's name.
        """
        from analysis.session_map import classify, role_of, CEILING, FLOOR
        role = role_or_kind if role_or_kind in (CEILING, FLOOR) \
            else role_of(role_or_kind)
        # 🔴 r231 — `spot` is REQUIRED. Geometry now asks role-vs-PRICE as
        # well as role-vs-range (operator, 2026-09-03), and an optional
        # parameter is an invalidation a caller can drop in silence.
        ok, why = classify(price, role or "", orb_high, orb_low, name,
                           spot=spot)
        self.last_why = why
        self.check("geometry", price, ok, why)
        return ok

    # ── economics: the what-if, priced off what the strategy chose ─────
    def credit_spread(self, short_strike, long_strike, credit,
                      invalidation=None, trigger=None) -> "PlanTick":
        """A credit vertical the strategy has already selected.
        R = credit / (width - credit). Real width — never an assumed $5."""
        try:
            self.short_strike = float(short_strike)
            self.long_strike = float(long_strike)
            width = abs(self.long_strike - self.short_strike)
            self.credit = float(credit) if credit is not None else None
        except (TypeError, ValueError):
            width, self.credit = 0.0, None
        self.anchor(trigger, invalidation)
        if self.credit is not None and width > 0:
            self.risk = round(width - self.credit, 4)
            self.reward = round(self.credit, 4)
            self.r = round(self.credit / self.risk, 4) if self.risk > 0 else None
        self.check("credit", self.credit, None if self.credit is None else self.credit > 0)
        self.check("width", width or None, None if not width else True)
        self.check("risk", self.risk, None if self.risk is None else self.risk > 0)
        self.check("r", self.r, None)      # verdict set by executable()
        return self

    def debit_directional(self, premium, delta, gamma, stop_distance,
                          target_distance=None, invalidation=None,
                          trigger=None) -> "PlanTick":
        """A long option. Reward/risk in premium terms from the greeks over
        the structural distances the strategy fixed:
            gain = δ·d_t + ½γ·d_t²      loss = δ·d_s − ½γ·d_s²   (gamma cushions)
        Target defaults to the stop distance MIRRORED — the structure sets
        both ends; no fitted multiple.
        """
        try:
            prem = float(premium)
            d = abs(float(delta or 0.0))
            g = float(gamma or 0.0)
            ds = abs(float(stop_distance))
            dt = abs(float(target_distance)) if target_distance is not None else ds
        except (TypeError, ValueError):
            prem, d, g, ds, dt = 0.0, 0.0, 0.0, 0.0, 0.0
        self.anchor(trigger, invalidation)
        self.debit = prem if prem > 0 else None
        if prem > 0 and d > 0 and ds > 0:
            gain = d * dt + 0.5 * g * dt * dt
            loss = max(0.01, d * ds - 0.5 * g * ds * ds)
            self.reward, self.risk = round(gain, 4), round(loss, 4)
            self.r = round(gain / loss, 4)
        self.check("debit", self.debit, None if self.debit is None else True)
        self.check("delta", d or None, None if not d else d > 0)
        self.check("stop_distance", ds or None, None if not ds else ds > 0)
        self.check("target_distance", dt or None, None if not dt else dt > 0)
        self.check("r", self.r, None)
        return self

    def butterfly(self, debit, width, invalidation=None, trigger=None) -> "PlanTick":
        """A debit fly: max profit = width - debit. R = (width - debit)/debit."""
        try:
            dbt, w = float(debit), float(width)
        except (TypeError, ValueError):
            dbt, w = 0.0, 0.0
        self.anchor(trigger, invalidation)
        self.debit = dbt if dbt > 0 else None
        if dbt > 0 and w > dbt:
            self.risk, self.reward = round(dbt, 4), round(w - dbt, 4)
            self.r = round((w - dbt) / dbt, 4)
        self.check("debit", self.debit, None if self.debit is None else True)
        self.check("width", w or None, None if not w else w > 0)
        self.check("r", self.r, None)
        return self

    # ── the antagonistic verdict ───────────────────────────────────────
    def executable(self) -> Tuple[bool, str]:
        """Apply the R hurdle. STRICT: r < floor (or unmeasurable) refuses.
        RELAXED: recorded, MUTED, proceeds. `strategy/criteria.py` decides.

        ⚠️ ONLY ECONOMICS LIVE HERE. Geometry is `level()` and the strategy
        acts on its answer; the clock is the strategy's own spec. Putting
        either inside this call would let a plan re-decide a setup.
        """
        from strategy.criteria import r_verdict
        v, why = r_verdict(self.r)
        self.last_why = why
        if v == "PASS":
            self.check("r", self.r, True)
            return True, why
        if v in ("MUTED", "MUTED_NO_R"):
            # recorded, not gating — the verdict of the tick becomes MUTED
            self.check("r", self.r, None)
            self.check("r_muted", 1.0, True, why)
            self.verdict = "MUTED"
            return True, why
        self.check("r", self.r, False)
        return False, why

    # ── terminals: each one WRITES and returns what the strategy returns ─
    def refuse(self, gate: str, reason: str = "", *, verdict: str = "DECLINE"):
        """The strategy is not trading this tick, at this gate, for this
        reason. Writes the row, reports the block edge-triggered, returns
        None so `return t.refuse(...)` is the whole refusal."""
        why = reason or self.last_why or gate
        prev = self.checks.get(gate, (None, None))[0]
        self.check(gate, prev, False)
        self._close(verdict, f"{gate}: {why}")
        self.plan._report_block(gate, why)
        return None

    def dormant(self, gate: str, reason: str = ""):
        """OUT OF WINDOW — write ONE row on the transition, then go quiet.

        🔴 OPERATOR, 2026-08-27: *"I don't want the 11:30-onwards credit
        strategies even looking at the chart before their window starts."*
        ⚠️ WHAT THIS REPLACES: three credit strategies calling `refuse()` on
        every tick from 09:35, each writing a plan row that said only "it is not
        11:31 yet". On UNH that was ~900 of roughly 1,300 rows for the morning —
        a per-minute transcript of a CLOCK, which nobody needs and which buried
        the ORB sequence the operator was actually looking for.
        ⚠️ THE RECORD IS NOT LOST, IT IS DEDUPLICATED. The first tick outside
        the window writes the row; every identical tick after it is silent; the
        next CHANGE writes again. "This strategy was dormant from 09:35" is the
        same information as 900 copies of it, and it is readable.
        ⚠️ THE GATE REPORTER IS UNAFFECTED — it was already edge-triggered, so
        the dashboard's GATES panel behaves exactly as before.
        """
        why = reason or self.last_why or gate
        key = (self.plan.strategy, gate, why)
        if _DORMANT.get(self.plan.strategy) == key:
            # ⚠️ MARK THE TICK AS HANDLED WITHOUT WRITING A ROW. `close_tick`
            # writes a NOT ASKED row for any strategy whose `_last` tick number
            # is stale — and for an ASKED strategy that wrote nothing it writes
            # the far louder "a return path is not wired through its plan".
            # Silently returning here would therefore produce a WORSE row than
            # the one being suppressed. Stamping `_last` with the current tick
            # is what makes the strategy genuinely quiet.
            n, _ts = tick_now()
            self.plan._last = (n, "DORMANT", f"{gate}: {why}")
            _ASKED.pop(self.plan.strategy, None)
            return None
        _DORMANT[self.plan.strategy] = key
        self.check(gate, None, False)
        self._close("DORMANT", f"{gate}: {why}")
        self.plan._report_block(gate, why)
        return None

    def permit(self, side: str, level: float, source: str = "",
               plan_id=None, why: str = ""):
        """A PERMISSION, not a signal. The plan's terminal for an informer.

        🔴 OPERATOR, 2026-08-27: *"nothing in the plan is executable. It's an
        information layer to feed the strategy and the strategy will execute."*
        And: *"The condor doesn't construct anything. The condor plan should
        just simply define whether a vertical spread is open and active and
        what's permitted afterwards."*

        ⚠️ THIS RETURNS NO SIGNAL AND NO CONTRACTS — deliberately. `take()`
        hands back an OptionsSignal because the strategy that called it BUILT
        one. A plan that is informing another strategy has nothing to hand over
        but the fact of permission: a side, a level, and why. If this ever
        starts returning something executable, the informer has become a second
        strategy again, which is the exact thing being removed here.

        The row is written as PERMIT so the per-tick account distinguishes
        "informed the strategy" from "took a trade" — they are different events
        and collapsing them is how the duplication hid.
        """
        self._close("PERMIT", why or f"{side} permitted at {level:g}")
        return Permission(side=side, level=float(level or 0.0),
                          source=source, plan_id=plan_id, why=why)

    def starved(self, *inputs: str):
        """An input the strategy needs is absent. NO PLAN row NAMING it —
        'could not evaluate' and 'does not exist' must never look alike."""
        names = ", ".join(inputs) or "unnamed input"
        for k in inputs:
            self.check(k, None, None)
        self._close("NO PLAN", f"input(s) absent: {names} — not evaluated this tick")
        self.plan._report_block("starved", names)
        return None

    def take(self, signal):
        """The strategy is firing. Writes TAKE (or MUTED if the R hurdle was
        muted), clears the gate block, opens the ledger row that
        `link_trade()` will join a fill to. Returns the signal unchanged."""
        # r254 (OBS.1) - an OBSERVED strategy (past its entry end) records LOG-ONLY and stops:
        # no TAKE row, no gate-report "cleared", no plan_ledger row. main.py refuses the signal.
        try:
            from strategy import observe as _observe
            _obs = _observe.is_active(self.strategy)
        except Exception:                                       # noqa: BLE001
            _obs = False
        if _obs:
            self._close(_observe.LOG_ONLY, "; ".join(dict.fromkeys(self.notes)) or "would take")
            return signal
        v = self.verdict or "TAKE"
        if v == "MUTED":
            v = "TAKE"
            if not any("MUTED" in n for n in self.notes):
                self.notes.insert(0, "R hurdle MUTED (relaxed)")
        self._close(v, "; ".join(dict.fromkeys(self.notes)) or "spec satisfied")
        self.plan._report_fired()
        self.plan._ledger_open(self, signal)
        return signal

    def already(self):
        """The plan already wrote this tick's row (DORMANT / NO PLAN / DECLINE /
        HOLD) and the strategy has nothing to add. Returns None so
        `return prep.tick.already()` reads as what it is: the strategy
        declining to act on a tick the plan has fully accounted for."""
        return None

    def hold(self, reason: str, *, verdict: str = "HOLD"):
        """Management verdicts — HOLD / ROLL / CLOSE. Returns None."""
        self._close(verdict, reason)
        return None

    def _close(self, verdict: str, reason: str) -> None:
        if self.closed:
            return
        self.closed = True
        self.verdict = verdict
        self.plan._last_checks = dict(self.checks or {})        # r303: the board reads a condor plan's "legs"
        # r303 (PSTATE.1) — a condor management plan with no credit leg open has nothing to manage: its
        # condition is absent, so the row is not written (and the tick does not count as written).
        if self.strategy in _MANAGEMENT_PLANS:
            try:
                _legs = float((self.checks.get("legs") or (None, None))[0])
            except (TypeError, ValueError):
                _legs = None
            if _legs is not None and _legs < 1:
                logger.debug("[plan] %s silent - no credit leg open (%s)", self.strategy, reason)
                return
        self.plan._last = (self.n, verdict, reason)
        try:
            write_row(self.plan._store_ref(), self.plan.symbol, self.ts,
                      self.strategy, verdict, reason, self.direction,
                      self.trigger, self.invalidation, self.spot, self.r,
                      self.checks, getattr(self, "check_notes", None))
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[plan] %s row not written: %s", self.strategy, exc)
        lvl = logging.INFO if verdict in ("TAKE", "NO PLAN", "ROLL", "CLOSE") \
            else logging.DEBUG
        logger.log(lvl, "[plan] %-22s %-8s %s%s", self.strategy, verdict,
                   f"R {_n(self.r)} · " if self.r is not None else "", reason)


# r211 — the strategies that open their OWN plan_ledger rows (main.py for the ORB; the
# condor's `_plan_id`). Everything else gets its row from take() / ledger_open().
OWN_LEDGER = frozenset({"ORBStrategy", "IronCondorStrategy", "CondorManagement", "CreditRoll"})


class Plan:
    """A strategy's informer. One per strategy instance; registered by name.

    `record_only=True` marks a plan whose verdict is never consulted (ORB —
    operator's ruling, *"leave orb alone"*). The strategy may still narrate
    through it; `executable()` is simply never called.
    """

    def __init__(self, strategy: str, checks: Tuple[str, ...] = (),
                 record_only: bool = False, self_ledgers: bool = False):
        self.strategy = strategy
        self.checks = tuple(checks)
        self.record_only = record_only
        # strategies that already open their own plan_ledger rows (the
        # condor, the daily fork) must not get a second one from take()
        self.self_ledgers = self_ledgers
        self.symbol = _symbol()
        self._store = _BOUND_STORE["store"]
        self._last: Tuple[int, str, str] = (0, "", "")   # (tick n, verdict, reason)
        REGISTRY[strategy] = self

    def _store_ref(self):
        if self._store is None:
            self._store = _store()
        return self._store

    def tick(self, spot=None, direction: str = "") -> PlanTick:
        """Open this tick's narration. Every strategy call starts here."""
        try:
            s = float(spot) if spot is not None else None
        except (TypeError, ValueError):
            s = None
        return PlanTick(self, s, direction)

    # ── did this plan write for the current tick? (the board asks) ─────
    def wrote_this_tick(self) -> bool:
        return self._last[0] == _TICK["n"]

    def last(self) -> Tuple[int, str, str]:
        return self._last

    # ── gate_report bridge — edge-triggered log, unchanged ─────────────
    def _report_block(self, gate: str, reason: str) -> None:
        # 🔑 r83 — THE GATE IS RECORDED, NOT RE-DERIVED FROM THE SENTENCE.
        # The board must distinguish WINDOW CLOSED from STALE (operator's
        # ruling: *"I don't think stale needs to be the same thing as window
        # closed"*), and the first cut of the heartbeat parsed the gate back
        # out of `_last`'s text — which failed immediately, because the window
        # rows read "inactive — window: ..." and the head token is a sentence
        # fragment, not a gate name. Every block passes through here with the
        # gate in hand; stashing it is free and cannot drift from the prose.
        try:
            self._last_gate = str(gate or "")
        except Exception:                                       # noqa: BLE001
            pass
        try:
            from analysis.gate_report import get_gate_reporter
            r = get_gate_reporter(self.symbol)
            if r is not None:
                r.blocked(self.strategy, gate, reason)
        except Exception:                                       # noqa: BLE001
            pass

    def _report_fired(self) -> None:
        try:
            from analysis.gate_report import get_gate_reporter
            r = get_gate_reporter(self.symbol)
            if r is not None:
                r.cleared(self.strategy)
        except Exception:                                       # noqa: BLE001
            pass

    def ledger_open(self, t: "PlanTick", signal, supersede: bool = True) -> None:
        """r211 — the public door: a strategy that fires WITHOUT take() opens its row here,
        immediately before the order, so link_trade() attaches the fill to THIS row.
        supersede=False keeps a sibling's open row (ORCS: a put and a call in one tick)."""
        self._ledger_open(t, signal, supersede=supersede)

    def _ledger_open(self, t: PlanTick, signal, supersede: bool = True) -> None:
        """Open a plan_ledger row for a fired plan so `link_trade()` has a
        live row to attach the fill to. State TRIGGERED — the strategy has
        fired; the fill (or its absence) is what comes next."""
        # r211 — only a strategy that really opens its own rows skips this; the
        # self_ledgers flag was set on nine plans and true of two.
        if self.strategy in OWN_LEDGER or "/" in self.strategy:
            return
        try:
            # r211 — THROUGH THE BOUND STORE. r6 (HYG.4) returned here whenever a
            # store was bound, to keep the lander's TestStrat rows out of the box's
            # ledger; but the plan board binds the BOX's store at start, so nothing
            # was ever opened in production either. Writing through whichever store
            # is bound gives r6 what it wanted - a checker's rows land in its own
            # scratch store - without switching the ledger off.
            store = self._store_ref()
            if store is None:
                return
            from derived.plan_ledger import PlanLedger
            led = PlanLedger(store, self.symbol)
            # 🔴 r212 — THE PREVIOUS UNFILLED PLAN OF THIS STRATEGY IS CLOSED
            # FIRST. A plan that FIRES but whose entry is then refused (sizing
            # rejection, no priced contract, a failed order) links no trade, so
            # the exit hook never reaches it and it stays live all session.
            # Safe here because `take()` and the entry attempt happen on the
            # SAME tick, so by the time the next one fires the previous has
            # resolved either way.
            # ⚠️ ROWS THAT FILLED ARE UNTOUCHED — those are closed by their
            # exit. Collapsing the two would lose the difference between
            # "fired and lost" and "fired and never filled", which is the
            # population this ledger exists to keep.
            if supersede:
                led.close_unfilled(self.strategy, "superseded — never filled")
            ctx = {"price": t.spot}
            sp = getattr(signal, "short_put_contract", None)
            lp = getattr(signal, "long_put_contract", None)
            led.open_plan(
                self.strategy, "TRIGGERED", ctx,
                direction=t.direction or getattr(signal, "option_side", ""),
                short_strike=t.short_strike,
                long_strike=t.long_strike,
                short_put_strike=getattr(sp, "strike", None) if sp else None,
                long_put_strike=getattr(lp, "strike", None) if lp else None,
                trigger_price=t.trigger,
                underlying_at_decision=t.spot)
        except Exception as exc:                                # noqa: BLE001
            logger.debug("[plan] ledger open skipped for %s: %s", self.strategy, exc)


# ── the board's half: rows for strategies that never spoke this tick ────
_SKIPPED: Dict[str, str] = {}      # strategy -> reason main.py gave
_ASKED: Dict[str, Any] = {}        # strategy -> result summary

# ══ r41 — EVERY PLAN IS WORKING OR INACTIVE, AND INACTIVE SAYS SO ONCE ═══
# Operator, 2026-09-18: *"Because we know a plan is inactive outside its
# window, I don't need 10k rows explaining why. I just need 1, so I'm aware it
# at least KNOWS. Each plan should have a current status as either 'working' or
# 'inactive' and if it's working, I want per tick logging. If inactive it
# should just say that, once, until it becomes active."*
#
# 🔑 THE ROW BECOMES EDGE-TRIGGERED, NOT LEVEL-TRIGGERED. A plan that wrote
# this tick is WORKING and keeps its per-tick row — that half is untouched,
# because a working plan's row is the thing he actually reads. A plan that did
# not write is INACTIVE and gets ONE row on the TRANSITION; while the state
# holds, the board stays silent.
#
# ⚠️ THE STATE IS (verdict, reason), NOT JUST "inactive", AND THAT IS A
# DELIBERATE READING OF "once". A plan that goes from "outside its window" to
# "catastrophic cap broken" is inactive for a DIFFERENT reason, and that is new
# information about the box — silence there would hide a state change behind a
# rule written to remove noise. A stable inactive state still writes exactly
# one row, which is what he asked for.
#
# ⚠️ KEYED BY TRADING DATE, so a new session re-announces once rather than
# inheriting yesterday's silence. Restart survival is deliberate too: the dict
# is module state, so a bounce re-announces — which is correct, because after a
# restart nobody can assume the operator saw the pre-restart row.
_STATUS: Dict[str, Tuple[str, str, str]] = {}   # strategy -> (day, verdict, reason)
_SKIP_GATE: Dict[str, str] = {}                # strategy -> admission gate name
_SEEN: Dict[str, set] = {}                     # strategy -> tokens announced THIS episode
_SEEN_DAY: Dict[str, str] = {}                 # strategy -> the day that episode belongs to
_LAST_SAID: Dict[str, object] = {}             # r258 — strategy -> the token its last INACTIVE row carried

# 🔑 r42 — THE OPERATOR'S ASYMMETRY, STATED AS A RULE.
# 2026-09-18: *"if something other than the window made it inactive it should
# declare that, but if it's the window, I just need to see that once not
# repeatedly."*
#   · WINDOW is the expected, boring state — announced ONCE per inactive
#     episode, where an episode ends when the plan next goes WORKING.
#   · ANY OTHER GATE is news — a cap break, a type cap, a tries cap — and
#     declares itself when it becomes the reason.
# ⚠️ IT NEEDS A SET, NOT A LAST-VALUE SLOT, AND THAT IS THE WHOLE SUBTLETY.
# With one slot, `window -> cap -> window` re-announces window, because the
# slot now holds `cap` and window "changed". A per-episode SET remembers that
# window was already said, so the return to window stays silent — which is
# what "once, not repeatedly" actually requires.
QUIET_GATES = frozenset({"window"})


def _episode(name: str, day: str) -> set:
    """The set of reasons already announced in this inactive episode."""
    if _SEEN_DAY.get(name) != day:
        _SEEN_DAY[name] = day
        _SEEN[name] = set()
        _LAST_SAID.pop(name, None)                 # r258: a new day starts unsaid
    return _SEEN.setdefault(name, set())


def _status_changed(name: str, day: str, verdict: str, reason: str,
                    gate: str = "") -> bool:
    """True when this state is NEW for `name` — i.e. write a row.

    Records the state as a side effect, so a caller that gets True has already
    claimed the transition and a second call in the same state returns False."""
    cur = (day, verdict, reason)
    prev = _STATUS.get(name)
    _STATUS[name] = cur

    if verdict == "WORKING":
        # the episode ends: everything may be announced afresh next time it
        # goes quiet, because the operator has seen it trading since.
        _SEEN[name] = set()
        _SEEN_DAY[name] = day
        _LAST_SAID.pop(name, None)                 # r258
        return prev != cur

    seen = _episode(name, day)
    # a QUIET gate collapses to its gate name, so every window refusal in one
    # episode is the same token however the sentence is phrased. Anything else
    # carries its full reason, so a DIFFERENT cap break still declares itself.
    token = gate if gate in QUIET_GATES else (verdict, gate, reason)
    if gate in QUIET_GATES:
        # the WINDOW: once per inactive episode (r42), unchanged.
        if token in seen:
            return False
        seen.add(token)
        _LAST_SAID[name] = token
        return True
    # 🔴 r258 (HYG.17) — EVERY OTHER REASON declares itself when it BECOMES the
    # reason: silent only while it is what the last row already says. Keeping
    # it in the episode set forever hid a return (A -> B -> A showed B all day).
    if token == _LAST_SAID.get(name):
        return False
    seen.add(token)
    _LAST_SAID[name] = token
    return True


def plan_status(name: str) -> str:
    """'working' | 'inactive' | 'unknown' — the board's current view."""
    st = _STATUS.get(name)
    return "unknown" if st is None else ("working" if st[1] == "WORKING" else "inactive")


def skipped(strategy: str, reason: str, gate: str = "") -> None:
    """main.py: this strategy is NOT being asked this tick, and here is why.
    Recorded at close_tick as INACTIVE. Never raises.

    r42 — `gate` is the admission gate that refused it. It is kept SEPARATE
    from the prose because the operator's rule keys on it:
      · gate == "window"  -> announced ONCE per inactive episode
      · anything else     -> declares itself
    Recovering a gate by parsing `reason` would make that rule depend on
    message wording, which is the kind of coupling that fails silently."""
    try:
        k = DISPATCH_ALIAS.get(strategy, strategy)
        _SKIPPED[k] = reason
        _SKIP_GATE[k] = gate or ""
    except Exception:                                           # noqa: BLE001
        pass


def skipped_management(reason: str) -> None:
    """Every MANAGEMENT plan is not being asked, and here is why.

    🔑 r213 (chunk E) — THE ENTRIES NOTHING NAMED. `CondorManagement`,
    `CreditRoll` and every `<Strategy>/manage` row are driven only inside
    main.py's `has_open_position()` branch. With nothing open they are never
    called, and no skip site names them — so they fell to the default and the
    panel said "dispatch gave no reason" on every tick of every flat session.
    ⚠️ AND A `/manage` ENTRY OUTLIVES ITS POSITION. `REGISTRY` persists for the
    life of the process, so once a strategy has managed anything its row keeps
    reporting for the rest of the day.
    ⚠️ `setdefault`, NOT ASSIGNMENT: a management plan that DID write a real
    verdict this tick, or was skipped for a more specific reason, keeps it.
    """
    try:
        for name in list(REGISTRY):
            if name.endswith("/manage") or name in _MANAGEMENT_PLANS:
                _SKIPPED.setdefault(name, reason)
    except Exception:                                           # noqa: BLE001
        pass


def skipped_all(reason: str, gate: str = "") -> None:
    """main.py: NO strategy is being asked this tick (halted, outside the
    session, no chain, a position is open). Never raises.

    🔑 r84 — `gate` IS THE SAME FIELD `skipped()` HAS CARRIED SINCE r42, and
    its absence here is why the board could only ever say a bare "HELD".
    MEASURED 2026-09-21: 15 of 16 skip sites in main.py passed no gate, so
    every refusal that was not the clock arrived at the panel unlabelled —
    including the butterflies' one-per-session quota, which the operator asked
    to see named. `_plan_skip`'s own docstring already warned that recovering
    a gate by parsing the reason sentence is how the rule quietly stops
    working; the fix is to pass it, not to parse it."""
    try:
        for name in list(REGISTRY):
            _SKIPPED.setdefault(name, reason)
            if gate:
                _SKIP_GATE.setdefault(name, gate)
    except Exception:                                           # noqa: BLE001
        pass


def asked(label: str, result) -> None:
    """main.py's `_safe_strategy`: this strategy WAS called and returned
    `result`. Used at close_tick to catch a strategy that was asked and wrote
    no row — an unwired `return None` or a raise."""
    try:
        _ASKED[DISPATCH_ALIAS.get(label, label)] = (
            "signal" if result is not None else "None")
    except Exception:                                           # noqa: BLE001
        pass


def close_tick(store=None, symbol: str = "") -> int:
    """Write NOT ASKED rows for the tick just finished. Called by the board
    at the START of the next tick (so every dispatch return path is
    covered). Returns rows written."""
    n, ts = tick_now()
    if n == 0:
        return 0
    store = store or _store()
    symbol = symbol or _symbol()
    written = 0
    # r41 — the trading date keys the status, so a new session re-announces.
    try:
        from utils.time_utils import now_et as _net
        _day = _net().strftime("%Y-%m-%d")
    except Exception:                                           # noqa: BLE001
        _day = ""
    try:
        for name, plan in list(REGISTRY.items()):
            if _dormant(name):                                  # r303 (PSTATE.1): no row, ever
                continue
            if plan.wrote_this_tick():
                # r41 — WORKING: it spoke for itself this tick, and a working
                # plan keeps its per-tick row. Recording the state here is what
                # makes the next inactive row a TRANSITION rather than a repeat.
                _status_changed(name, _day, "WORKING", "")
                continue
            if name in _ASKED:
                why = (f"ASKED and returned {_ASKED[name]} but wrote no plan "
                       f"row — a return path in this strategy is not wired "
                       f"through its plan (or it raised)")
                verdict = "NO PLAN"
                # ⚠️ r41 — THE WARNING IS EDGE-TRIGGERED TOO. This is a defect
                # report; repeating it every tick for a whole session is the
                # same noise the operator just ruled out, one channel over, and
                # it is how a real defect gets filtered out of the log.
                if _status_changed(name, _day, verdict, why):
                    logger.warning("[plan] %s %s", name, why)
                else:
                    continue
            else:
                if _condition_plan(name):
                    # r303 (PSTATE.1) — not run this tick = its condition is absent: no row, no
                    # "dispatch gap" default (the operator, 2026-10-19 09:54 ET: "Yes").
                    continue
                # 🔴 r213 (chunk E) — THE DEFAULT ADMITS WHAT IT IS. Operator,
                # 2026-09-01: *"I don't like 'NOT ASKED' as a reason. It makes
                # no sense. Not asked? why or Why not?"* He is right: the old
                # text restated the verdict and told him nothing.
                # ⚠️ AN UNEXPLAINED SKIP IS A GAP IN DISPATCH, NOT A MARKET
                # CONDITION, and the row now says so. Every skip main.py can
                # name IS named; this fires only where none is, which makes it
                # a defect report rather than a status — and one that reads as
                # a defect, so it gets fixed instead of scrolled past.
                why = _SKIPPED.get(
                    name, "no reason recorded — main.py reached a return path "
                          "that does not name this strategy. That is a "
                          "dispatch gap, not a market condition")
                verdict = "INACTIVE"
                _gate = _SKIP_GATE.get(name, "")
                # 🔑 r41 — ONE ROW, THEN SILENCE UNTIL THE STATE CHANGES.
                # Operator: *"If inactive it should just say that, once, until
                # it becomes active."* The verdict is INACTIVE rather than NOT
                # ASKED because he ruled on that wording too (r213): *"I don't
                # like 'NOT ASKED' as a reason. It makes no sense."* A status is
                # what he asked for, and a status is what the column now holds.
                if not _status_changed(name, _day, verdict, why, _gate):
                    continue
            if write_row(store, symbol, ts, name, verdict, why):
                written += 1
            plan._last = (n, verdict, why)
        _write_heartbeats(store, symbol, n, ts)
    finally:
        _SKIPPED.clear()
        _SKIP_GATE.clear()
        _ASKED.clear()
    return written


def _write_heartbeats(store, symbol: str, n: int, ts: float) -> None:
    """r83 — CURRENT STATE FOR EVERY PLAN, EVERY TICK, UPSERTED.

    🔑 WHAT THE BOARD COULD NOT ANSWER BEFORE: *"is this plan actively
    evaluating the feed?"* It guessed, by comparing the newest `plan_tick`
    row against a 300-second cut — but r41 made those rows EDGE-TRIGGERED, so
    a plan behaving perfectly writes nothing and looks dead. Measured
    2026-09-21: 16 of 18 flagged STALE, all 16 correct, and the two that
    looked alive were alive only because their reason text carries live
    prices. THE MARKER WAS MEASURING WHETHER A STRING CHANGED.

    Three states, and they are DIFFERENT QUESTIONS the old panel conflated:
      EVALUATING — the plan ran this tick and produced a verdict
      IDLE       — the plan ran and is deliberately quiet (out of window,
                   already traded, nothing to manage). Not a fault.
      NO PLAN    — it was ASKED and wrote nothing. This one is a defect and
                   is the only state that deserves a warning.
    A plan that is never INSTANTIATED cannot appear here at all — REGISTRY is
    populated on construction — so the reader compares this table against the
    expected roster and reports the difference. That gap is not theoretical:
    on 2026-09-21 `Breakout` was absent from the board entirely, its last row
    frozen at 11:30:08, and NOTHING SAID SO — the same blindness that let
    r77's 127 crashes hide behind a stale label for a whole session.

    ⚠️ UPSERT, NEVER APPEND. r41's ruling governs the LEDGER; this is current
    state and is bounded by the number of plans forever. Never raises.
    """
    if store is None:
        return
    try:
        rows = []
        for name, plan in list(REGISTRY.items()):
            if _dormant(name):                                  # r303 (PSTATE.1): no heartbeat either
                continue
            if _condition_plan(name) and not plan.wrote_this_tick() and name not in _ASKED:
                continue                                        # r303: condition absent - silent
            _, verdict, why = plan.last()
            if plan.wrote_this_tick():
                state = "EVALUATING"
            elif name in _ASKED:
                state = "NO PLAN"
            else:
                state = "IDLE"
            # 🔑 THE GATE IS CARRIED, NOT PARSED BY THE READER. `dormant()`
            # and `refuse()` both stamp `_last` as "<gate>: <why>", so the
            # gate is extracted ONCE, here, and the board never string-matches
            # prose. WINDOW CLOSED and STALE are DIFFERENT ANSWERS to
            # different questions and the operator ruled they must read
            # differently: a plan outside its window is WORKING, and only a
            # plan whose heartbeat has STOPPED is stale.
            _why = why or ""
            # 🔑 TWO MECHANISMS CARRY A GATE AND THE BOARD NEEDS BOTH.
            # `_report_block` stamps `_last_gate` for a plan that RAN and
            # refused itself ("entry_window: past 15:40 ET"). A plan that was
            # never ASKED carries its gate in `_SKIP_GATE`, set by main.py's
            # dispatch, and its row reads "inactive — window: ...". The first
            # cut of this read only the former and every window-closed plan
            # came out as a bare HELD — which is precisely the conflation the
            # operator ruled against: *"report window closed if that's the
            # reason."*
            _gate = (str(getattr(plan, "_last_gate", "") or "")
                     or str(_SKIP_GATE.get(name, "") or ""))
            rows.append((symbol, name, ts, n, state, _gate,
                         verdict or "", _why[:400]))
        if not rows:
            return
        store.conn.executemany(
            "INSERT INTO plan_heartbeat (symbol, plan, ts_epoch, tick_id, state,"
            " gate, verdict, watching) VALUES (?,?,?,?,?,?,?,?)"
            " ON CONFLICT(symbol, plan) DO UPDATE SET"
            "   ts_epoch=excluded.ts_epoch, tick_id=excluded.tick_id,"
            "   state=excluded.state, gate=excluded.gate,"
            "   verdict=excluded.verdict, watching=excluded.watching", rows)
        store.commit()
    except Exception:                                           # noqa: BLE001
        pass


def board_line() -> str:
    """One line: every registered strategy's last verdict, for the log. r303 (PSTATE.1): a DORMANT plan is
    not on it, and CondorManagement / CreditRoll are on it only while they have a credit position to manage
    (the operator, 2026-10-19: "2. Yes")."""
    bits = []
    for name, plan in sorted(REGISTRY.items()):
        if _dormant(name):
            continue
        _, v, why = plan.last()
        if name in _MANAGEMENT_PLANS:
            # both condor plans check "legs" on every tick they run; a flat book reads INACTIVE
            try:
                _legs = float(((getattr(plan, "_last_checks", None) or {}).get("legs") or (0, None))[0] or 0)
            except (TypeError, ValueError):
                _legs = 0.0
            if v == "INACTIVE" or _legs < 1:
                continue
        short = (why or "")[:48].replace("\n", " ")
        bits.append(f"{name}={v or '-'}" + (f"({short})" if short else ""))
    return " · ".join(bits)
