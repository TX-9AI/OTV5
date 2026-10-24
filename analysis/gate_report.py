"""
analysis/gate_report.py  v4.2
v4.2  2026-09-04  r246 — 🔴 DISPATCH_ALIAS IS COMPOSED FROM THE
      CANONICAL MAP. This held its own dict and was MISSING `ORB` and
      `SweepForLeg2`, so the ORB's `fired()` arrived as "ORB" and never
      resolved — r239's split in a THIRD place. r239 fixed the notes writer,
      the plan board had it right since r147, this one was never told.
      ⚠️ COMPOSED, NOT REPLACED, and FIT.2's "two copies of one map" was the
      wrong diagnosis. `plan.DISPATCH_ALIAS` maps a dispatch label to the CLASS
      NAME; this maps it to THE REPORTER'S OWN name, and `GexPinButterfly`
      (lowercase x) is live at `gex_pin_butterfly:271` while dispatch fires
      under "GEXPinButterfly". Merging them would have broken that.
      ⚠️ THE LOCAL LAYER GOES LAST so a reporter-name override always wins, and
      the import degrades to local names on failure — this file never raises.
v4.1  2026-08-23  AUDIT F9: `cleared()` had ZERO callers, so the CLEARED event
the docstring calls "as important as the block" could never be written, and
snapshot() reported a strategy blocked with a growing held_s forever - after
it fired, after the candidate vanished, all session. Dispatch now reports a
fire through `fired(dispatch_name)`, which maps main.py's dispatch labels onto
the reporter's strategy names and clears. Also `_write` never committed: rows
rode the shared connection until some other engine committed. It commits.
v4.0  2026-08-25
Every gate that can kill an entry says so — ONCE, at INFO, with its reason.

v4.0  2026-08-25  The r61 observability item, and the class fix for
2026-08-21: the fleet declined every setup on every box all session and
COULD NOT SAY WHY.

🔴 WHAT THE SILENCE COST. The signal journal held exactly ONE event type all
Friday. Every other refusal — the sweep's post-strike-selection gates, the
butterfly's pin and expected-move checks, ORB's post-confirmation ladder, the
window cutoffs — was a `logger.debug` line, unjournaled. SPX re-confirmed a
break+retest at 10:46 and sat refused for FORTY-FOUR MINUTES, and the cause is
still unmeasured because nothing recorded which rung said no.

⚠️ THE RUNGS ARE ALREADY WELL-WRITTEN. `[sweep_cs] no trade: %s pierced %.3f%%
- too deep` is a good sentence. It just never leaves DEBUG. This module does
not rewrite the reasons; it makes them VISIBLE and QUERYABLE.

⚠️ EDGE-TRIGGERED, NOT LEVEL-TRIGGERED, AND THAT IS THE WHOLE DESIGN. A tick
loop evaluating every ~15s produces ~240 refusals per hour per strategy. Level
logging at INFO would bury the session in noise and teach the operator to stop
reading — the same way a board that goes red every evening teaches him to stop
looking. **A gate speaks when its verdict CHANGES**, and again when it clears.

⚠️ A REPEATED REFUSAL IS NOT NEW INFORMATION. But a refusal that CHANGES is:
"sweep was blocked on pierce depth, now it is blocked on ATR" is a different
session from "sweep has been blocked on pierce depth for two hours". The
counter makes the second one visible without printing it 480 times.

⚠️ CONTRIBUTOR, NEVER A GATE. This module observes; it can never change a
verdict. Every call is wrapped — a reporting failure must not be able to alter
what trades, which is the rule the retired label system violated.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Re-announce a still-unchanged refusal at most this often, so a long block is
# visible in the log without being spammed. 15 min ~= 60 ticks.
REANNOUNCE_S = 900.0

# main.py dispatches under short labels; strategies report under their class
# names. One map, so a fire can find the block it clears.
# 🔴 r246 — COMPOSED FROM THE CANONICAL MAP, NOT A SECOND COPY OF IT. This held
# its own dict and was MISSING `ORB -> ORBStrategy` and
# `SweepForLeg2 -> SweepCreditSpread`, so the ORB's `fired()` arrived as "ORB"
# and never resolved — r239's split, in a third place. r239 fixed the notes
# writer; the plan board had it right since r147; this one was never told.
# ⚠️ AND IT IS NOT A DUPLICATE, WHICH IS WHY IT IS COMPOSED RATHER THAN
# REPLACED. `plan.DISPATCH_ALIAS` maps a dispatch label to the STRATEGY CLASS
# NAME. This maps a dispatch label to THE REPORTER'S OWN INTERNAL NAME, and
# `GexPinButterfly` (lowercase x) is live: `gex_pin_butterfly:271` calls
# `blocked("GexPinButterfly", ...)` while dispatch fires under
# "GEXPinButterfly". Merging the two would have broken that reconciliation.
# FIT.2 filed this as "two copies of one map"; that was wrong.
# 🔑 THE LOCAL LAYER GOES LAST so a reporter-name override always wins over the
# shared entry — the shared map cannot silently redirect a name this file owns.
try:
    from strategy.plan import DISPATCH_ALIAS as _SHARED_ALIAS
except Exception:                                              # noqa: BLE001
    # ⚠️ NEVER RAISES INTO THE REPORTER. This file's contract is "never raises";
    # an import failure degrades to the local names rather than killing the
    # gate board.
    _SHARED_ALIAS = {}

_REPORTER_NAMES = {
    # the reporter's own spelling, which is NOT the class name
    "GEXPinButterfly": "GexPinButterfly",
}

DISPATCH_ALIAS = {**_SHARED_ALIAS, **_REPORTER_NAMES}


class GateReporter:
    """Per-strategy edge-triggered disposition. Never raises."""

    def __init__(self, store=None, symbol: str = "", journal=None):
        self._store = store
        self.symbol = symbol
        self._journal = journal
        self._last: dict = {}          # strategy -> (reason, first_ts, count, last_log)
        self._made = False

    def _ensure(self):
        if self._made or self._store is None:
            return
        try:
            self._store.conn.execute("""
                CREATE TABLE IF NOT EXISTS gate_disposition (
                    ts_epoch  REAL NOT NULL,
                    symbol    TEXT NOT NULL,
                    strategy  TEXT NOT NULL,
                    gate      TEXT NOT NULL,
                    reason    TEXT,
                    detail    TEXT,
                    event     TEXT NOT NULL,   -- BLOCKED / CHANGED / CLEARED
                    held_s    REAL,
                    ticks     INTEGER,
                    PRIMARY KEY (ts_epoch, symbol, strategy)
                );""")
            self._store.conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_gate_strat "
                "ON gate_disposition(strategy, ts_epoch)")
            self._made = True
        except Exception as exc:                                # noqa: BLE001
            logger.debug("gate_disposition table: %s", exc)

    def _write(self, strategy, gate, reason, detail, event, held, ticks):
        try:
            self._ensure()
            if self._store is None:
                return
            self._store.conn.execute(
                "INSERT OR IGNORE INTO gate_disposition (ts_epoch, symbol,"
                " strategy, gate, reason, detail, event, held_s, ticks)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (time.time(), self.symbol, strategy, gate, reason, detail,
                 event, held, ticks))
            self._store.commit()                                # v4.1
        except Exception as exc:                                # noqa: BLE001
            logger.debug("gate write: %s", exc)

    def fired(self, dispatch_name: str) -> None:
        """v4.1 — a strategy produced a signal: whatever was blocking it has
        cleared. Resolves dispatch labels to reporter names. Never raises."""
        try:
            self.cleared(DISPATCH_ALIAS.get(dispatch_name, dispatch_name))
        except Exception:                                       # noqa: BLE001
            pass

    def blocked(self, strategy: str, gate: str, reason: str = "",
                detail: str = "") -> None:
        """This strategy is refusing, at this gate, for this reason.

        Speaks at INFO only when the verdict CHANGES (or after REANNOUNCE_S).
        """
        try:
            now = time.time()
            prev = self._last.get(strategy)
            if prev and prev[0] == gate:
                # Same gate as last tick — count it, stay quiet unless the
                # re-announce window has elapsed.
                first, count, last_log = prev[1], prev[2] + 1, prev[3]
                self._last[strategy] = (gate, first, count, last_log)
                if now - last_log >= REANNOUNCE_S:
                    held = now - first
                    logger.info("[gate] %s STILL BLOCKED at %s for %.0f min "
                                "(%d ticks) — %s", strategy, gate,
                                held / 60.0, count, reason or "no reason given")
                    self._last[strategy] = (gate, first, count, now)
                    self._write(strategy, gate, reason, detail, "BLOCKED",
                                held, count)
                return
            # ── EDGE: a new gate, or the first refusal after running clear ──
            event = "CHANGED" if prev else "BLOCKED"
            if prev:
                logger.info("[gate] %s block MOVED %s -> %s after %.0f min "
                            "(%d ticks) — %s", strategy, prev[0], gate,
                            (now - prev[1]) / 60.0, prev[2],
                            reason or "no reason given")
            else:
                logger.info("[gate] %s BLOCKED at %s — %s", strategy, gate,
                            reason or "no reason given")
            self._last[strategy] = (gate, now, 1, now)
            self._write(strategy, gate, reason, detail, event, 0.0, 1)
        except Exception:                                       # noqa: BLE001
            pass

    def cleared(self, strategy: str) -> None:
        """This strategy is no longer refusing. Announced once.

        ⚠️ THE CLEAR IS AS IMPORTANT AS THE BLOCK. Friday's silence was
        ambiguous precisely because a gate that stops complaining looks
        identical to a gate that never existed.
        """
        try:
            prev = self._last.pop(strategy, None)
            if not prev:
                return
            now = time.time()
            held = now - prev[1]
            logger.info("[gate] %s CLEARED — was blocked at %s for %.0f min "
                        "(%d ticks)", strategy, prev[0], held / 60.0, prev[2])
            self._write(strategy, prev[0], "", "", "CLEARED", held, prev[2])
        except Exception:                                       # noqa: BLE001
            pass

    def snapshot(self) -> dict:
        """What is currently blocking each strategy — for status.py."""
        out = {}
        try:
            now = time.time()
            for strat, (gate, first, count, _l) in self._last.items():
                out[strat] = {"gate": gate, "held_s": round(now - first),
                              "ticks": count}
        except Exception:                                       # noqa: BLE001
            pass
        return out


_reporter: Optional[GateReporter] = None


def get_gate_reporter(symbol: str = "") -> Optional[GateReporter]:
    """Singleton. None when the derived store will not open — reporting is a
    contributor and its absence must never stop a strategy."""
    global _reporter
    if _reporter is None:
        try:
            from data.derived_store import get_derived_store
            store = get_derived_store()
            _reporter = GateReporter(store, symbol)
        except Exception:                                       # noqa: BLE001
            return None
    return _reporter
