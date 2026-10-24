"""
derived/base.py  v4.1
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

The contract every derived engine implements.

v4.0  2026-08-22  Built with the manifold. See docs/DERIVED_STORES.md.

    raw port -> home -> DERIVER -> derived home -> ctx -> engine

ONE ENGINE PER STORE. Each subclass owns exactly one table in
`data/derived_store.py` end to end: it reads the raw it needs, computes, and
writes its own home. Nothing else writes that table.

⚠️ WHY ONE-PER-STORE AND NOT ONE BIG DERIVER. A single module writing five
tables is a single point whose failure takes all five with it, and a single
place where "did the fork deriver run?" and "did the surface deriver run?"
become the same question. Separate engines fail separately and report
separately — which is the only way `manifold_status` can name WHICH derived
port went dark.

🔴 DERIVERS ARE CONTRIBUTORS, NEVER GATES. Operator's ruling, 2026-08-22.
Derived values INFORM; they never authorise. This class enforces it
structurally: `run()` is wrapped so a subclass CANNOT raise into the caller,
no matter what it does internally. A missing derived value is not an error —
the engine trades without it.

computed that became a veto and stopped the fleet for a whole session. A
deriver that can throw into the tick loop is the same shape: an observation
becoming an authority. It is made impossible here rather than promised in a
comment.

⚠️ ABSENCE IS RECORDED AS ABSENCE. Subclasses return None or an empty list
when they cannot measure. They NEVER substitute 0.0. A measured zero and an
unmeasurable value are different facts (VW.1, the gap prior_dir, the sweep
score — all silent zeros that read as measurements).
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class DerivedEngine:
    """Base class. Subclasses implement `derive(ctx)` and set `name`/`table`."""

    name: str = "base"
    table: str = ""
    # Minimum seconds between runs. A deriver that scans backward does not need
    # to run every tick; one that tracks state does.
    min_interval_s: float = 0.0

    def __init__(self, store=None):
        self._store = store
        self._last_run: float = 0.0
        self._last_rows: int = 0
        self._last_error: Optional[str] = None
        self._runs: int = 0
        self._failures: int = 0

    # ── subclass surface ────────────────────────────────────────────────
    def derive(self, ctx: dict) -> int:
        """Compute and persist. Return rows written. Never called directly."""
        raise NotImplementedError

    # ── driver surface ──────────────────────────────────────────────────
    def run(self, ctx: dict) -> int:
        """Drive one cycle. NEVER raises. Returns rows written (0 on failure).

        ⚠️ THE BARE `except Exception` IS DELIBERATE AND IS THE CONTRACT.
        Narrowing it to expected exception types would let an unexpected one
        through into the tick loop, which is exactly the failure this class
        exists to make impossible.
        """
        now = time.time()
        if self.min_interval_s and (now - self._last_run) < self.min_interval_s:
            return 0
        self._last_run = now
        self._runs += 1
        try:
            n = int(self.derive(ctx) or 0)
            self._last_rows, self._last_error = n, None
            return n
        except Exception as exc:                                # noqa: BLE001
            self._failures += 1
            self._last_error = f"{type(exc).__name__}: {exc}"
            logger.warning("[derived:%s] %s — this derived value is absent "
                           "this cycle; nothing downstream is blocked",
                           self.name, self._last_error)
            self._last_rows = 0
            return 0

    def status(self) -> dict:
        """What this engine has actually been doing. For manifold_status."""
        return {"name": self.name, "table": self.table,
                "runs": self._runs, "failures": self._failures,
                "last_rows": self._last_rows,
                "last_run_age_s": (round(time.time() - self._last_run)
                                   if self._last_run else None),
                "last_error": self._last_error}


# 🔴 THE ENGINES KNEW AND NOBODY COULD ASK — 2026-08-24. `status()` has tracked
# runs / failures / last_rows / last_error since r62 and NOTHING EVER PERSISTED
# OR DISPLAYED IT. On 2026-08-24 `indicator_series` and `surface_series` sat at
# ZERO ROWS on all fifteen boxes while `fork_series` and `level_ledger` filled
# normally — no exception logged, no write failure logged, the engines built
# fine, and the same code writing 1 row on a workstation wrote 0 on a box.
# Diagnosis degenerated into an hour of inference across a dozen greps because
# THE ONE PROCESS THAT KNEW THE ANSWER HAD NO WAY TO SAY IT.
# 🔑 A COUNTER THAT NEVER LEAVES THE PROCESS IS NOT OBSERVABILITY. This writes
# each engine's own account of itself to a table any reader can query — the
# health board, devtools, a person with sqlite3 — so "wrote 0 rows and did not
# fail" becomes a FACT ON DISK instead of something to be deduced.
# ⚠️ IT RECORDS THE ZERO. An engine that returns 0 without raising is the exact
# case that was invisible; a status row that only appeared on failure would
# have been just as silent here.
STATUS_TABLE = "derived_engine_status"


def _persist_status(engines, store) -> None:
    """Write every engine's self-report. NEVER raises — see the class docstring."""
    if store is None:
        return
    try:
        conn = store.conn
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {STATUS_TABLE} (
                name        TEXT PRIMARY KEY,
                table_name  TEXT,
                runs        INTEGER,
                failures    INTEGER,
                last_rows   INTEGER,
                last_run_ts REAL,
                last_error  TEXT,
                updated_ts  REAL
            );""")
        now = time.time()
        for e in engines:
            try:
                st = e.status()
            except Exception:                                   # noqa: BLE001
                continue
            conn.execute(
                f"INSERT INTO {STATUS_TABLE} (name, table_name, runs, failures,"
                f" last_rows, last_run_ts, last_error, updated_ts)"
                f" VALUES (?,?,?,?,?,?,?,?)"
                f" ON CONFLICT(name) DO UPDATE SET table_name=excluded.table_name,"
                f" runs=excluded.runs, failures=excluded.failures,"
                f" last_rows=excluded.last_rows, last_run_ts=excluded.last_run_ts,"
                f" last_error=excluded.last_error, updated_ts=excluded.updated_ts",
                (st.get("name"), st.get("table"), st.get("runs"),
                 st.get("failures"), st.get("last_rows"),
                 getattr(e, "_last_run", None), st.get("last_error"), now))
        conn.commit()
    except Exception as exc:                                    # noqa: BLE001
        logger.debug("engine status not persisted: %s", exc)


def run_all(engines, ctx: dict) -> dict:
    """Drive every engine once. Returns {name: rows}. NEVER raises.

    ⚠️ ONE ENGINE'S FAILURE MUST NOT SKIP THE NEXT. Each `run()` is already
    wrapped, but the loop itself is guarded too: a subclass that somehow breaks
    `run` must not stop the engines after it in the list.
    """
    out = {}
    for e in engines:
        try:
            out[getattr(e, "name", "?")] = e.run(ctx)
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[derived] engine %r broke its own wrapper: %s",
                           getattr(e, "name", e), exc)
            out[getattr(e, "name", "?")] = 0
    # ⚠️ AFTER THE LOOP, ALWAYS — including when every engine returned 0. The
    # store comes off the engines themselves so this needs no new plumbing and
    # cannot disagree with what they actually wrote to.
    _persist_status(engines, next((getattr(e, "_store", None) for e in engines
                                   if getattr(e, "_store", None) is not None),
                                  None))
    return out
