"""
derived/counterfactual.py  v4.1
v4.1  2026-10-03  CND.10 — THIS ENGINE HAS NEVER WRITTEN A ROW. derive() read
      `get_trade_logger().conn`, an attribute TradeLogger has never had; the
      AttributeError was logged at DEBUG and derive returned 0 every tick since
      r66 (2026-08-22). raw/derived_exit_counterfactual/ holds ZERO objects,
      ever. It now reads get_open_trades() and a failure warns once. Found by
      OTV4TEST's audit (shared). Pinned by tests/check_counterfactual_reads.py.
Owns `exit_counterfactual`. Records what a FLOW exit WOULD have done.

v4.0  2026-08-25  Operator's question: could the tape — especially aggressor
flow building — inform an exit better than a mechanical stop? The condor
specifically, possibly the sweep and directional credit spreads too.

🔴 THE ANSWER IS "MEASURE IT", AND THIS REPO HAS PAID ONCE FOR NOT DOING SO.
`bos_exit` — exit on a structural signal instead of a mechanical level —
measured **34% win / 217 trades / -$7,085, with the largest single loss in the
v3 book**, against `orb_trail_stop` at **96% / 85 / +$30,696**. BOS is the same
IDEA and it lost badly when measured. The instinct may still be right; the
burden of proof is high and must be paid in data.

⚠️ THIS MODULE NEVER EXITS ANYTHING. It evaluates the flow condition on every
tick a position is open and writes down WHEN IT WOULD HAVE FIRED. The
mechanical stop runs untouched. After some weeks the same trades carry two exit
policies — one real, one hypothetical — against real outcomes.

⚠️ WHY THE ARGUMENT IS PLAUSIBLE: a mechanical stop on a credit structure is a
PREMIUM stop, and premium is a lagging, noisy proxy for what actually hurts
you. On a four-legged condor the mark is the sum of four spreads, each with its
own staleness and width. Aggressor flow into the short strike is the DAMAGE
MECHANISM ITSELF, observed as it happens. The stop waits for the consequence;
the flow is the cause.

⚠️ AND IT IS STILL CONFIRMATORY. Sellers lifting through the short strike right
now is evidence, not forecast.

⚠️ THE FAILURE MODE UNDER TEST, which is BOS's failure mode: the condor's edge
is a high win rate from DOING NOTHING. An exit that fires on flow that does not
follow through converts winners into small losses, and it takes many avoided
disasters to pay for that. Flow is noisy at exactly this timescale.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from derived.base import DerivedEngine

logger = logging.getLogger(__name__)

# ⚠️ PROVISIONAL, FLAGGED AS SUCH. Starting points for a MEASUREMENT, not
# tuned parameters. Nothing has fitted them and nothing may gate on them.
THREAT_FIRE = 0.45
SUSTAIN_TICKS = 3
WINDOW_S = 300.0


class CounterfactualExitEngine(DerivedEngine):
    name = "counterfactual"
    table = "exit_counterfactual"
    min_interval_s = 15.0

    def __init__(self, store=None, symbol: str = "", feed_conn=None):
        super().__init__(store)
        self.symbol = symbol
        self._feed_conn = feed_conn
        self._streak: dict = {}
        self._fired: dict = {}
        self._made = False

    def _ensure_table(self):
        if self._made:
            return
        try:
            self._store.conn.execute("""
                CREATE TABLE IF NOT EXISTS exit_counterfactual (
                    trade_id TEXT NOT NULL, ts_epoch REAL NOT NULL,
                    symbol TEXT, strategy TEXT,
                    level_price REAL, level_kind TEXT,
                    threat REAL, imbalance REAL, prints INTEGER, volume REAL,
                    would_fire INTEGER NOT NULL, streak INTEGER,
                    reason TEXT, detail TEXT,
                    PRIMARY KEY (trade_id, ts_epoch));""")
            self._store.conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_cf_trade "
                "ON exit_counterfactual(trade_id)")
            self._made = True
        except Exception as exc:                                # noqa: BLE001
            logger.debug("counterfactual table: %s", exc)

    def _conn(self):
        if self._feed_conn is not None:
            return self._feed_conn
        try:
            import sqlite3
            from data.candle_feed import feed_db_path
            self._feed_conn = sqlite3.connect(
                f"file:{feed_db_path()}?mode=ro", uri=True,
                check_same_thread=False)
        except Exception:                                       # noqa: BLE001
            return None
        return self._feed_conn

    @staticmethod
    def _threatened_level(trade: dict):
        """The level whose failure would hurt THIS position, and its kind.

        ⚠️ PER STRUCTURE, NOT PER DIRECTION. A short CALL spread is threatened
        from below by buying; a short PUT spread from above by selling. Getting
        this backwards would record the flow that HELPS a position as the flow
        that kills it, and the study would "prove" flow exits are inverted.
        Verified 2026-08-22: the same tape reads +0.65 against a short call at
        218.40 and -0.65 against a short put at the same strike.
        """
        ss = trade.get("short_strike")
        side = str(trade.get("option_side") or "").lower()
        if ss:
            if side.startswith("c"):
                return float(ss), "resistance"
            if side.startswith("p"):
                return float(ss), "support"
        strike = trade.get("strike")
        if strike:
            d = str(trade.get("direction") or "").upper()
            if d in ("LONG", "BULLISH"):
                return float(strike), "support"
            if d in ("SHORT", "BEARISH"):
                return float(strike), "resistance"
        return None, None

    def evaluate(self, trade: dict) -> Optional[dict]:
        conn = self._conn()
        if conn is None or self._store is None:
            return None
        tid = str(trade.get("trade_id") or "")
        if not tid:
            return None
        level, kind = self._threatened_level(trade)
        if level is None:
            return None

        from analysis.order_flow import pressure_into_level
        p = pressure_into_level(conn, self.symbol, level, kind, WINDOW_S)
        if p is None:
            # ⚠️ RECORDED AS A NON-FIRE WITH A REASON, NOT SKIPPED. "We could
            # not see" and "we saw calm" are different facts and the study must
            # be able to tell them apart.
            self._write(tid, trade, level, kind, None, None, 0, 0, "NO_TAPE")
            return None

        threat = p["threat"]
        breach = threat >= THREAT_FIRE
        streak = self._streak.get(tid, 0) + 1 if breach else 0
        self._streak[tid] = streak
        would = 1 if (breach and streak >= SUSTAIN_TICKS
                      and tid not in self._fired) else 0
        if would:
            self._fired[tid] = time.time()
            logger.info("[counterfactual] %s WOULD HAVE EXITED — threat %.2f "
                        "into %s %.2f, %d prints. NO ACTION TAKEN.",
                        tid[:8], threat, kind, level, p["prints"])
        reason = ("SUSTAINED_PRESSURE" if would
                  else ("PRESSURE" if breach else "CALM"))
        self._write(tid, trade, level, kind, threat, p, would, streak, reason)
        return {"trade_id": tid, "threat": threat, "would_fire": bool(would)}

    def _write(self, tid, trade, level, kind, threat, p, would, streak, reason):
        try:
            self._ensure_table()
            self._store.conn.execute(
                "INSERT OR IGNORE INTO exit_counterfactual (trade_id, ts_epoch,"
                " symbol, strategy, level_price, level_kind, threat, imbalance,"
                " prints, volume, would_fire, streak, reason, detail)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (tid, time.time(), self.symbol, trade.get("strategy"), level,
                 kind, threat, (p or {}).get("imbalance"),
                 (p or {}).get("prints"), (p or {}).get("volume"),
                 int(would), int(streak), reason,
                 json.dumps(p, default=str) if p else None))
        except Exception as exc:                                # noqa: BLE001
            logger.debug("counterfactual write: %s", exc)

    def derive(self, ctx: dict) -> int:
        """Evaluate every open position. NEVER acts on any of them."""
        if self._store is None:
            return 0
        try:
            from database.trade_logger import get_trade_logger
            # 🔴 CND.10 — TradeLogger has NO `.conn` and never had one, so
            # `tl.conn.execute` raised AttributeError on every tick since r66
            # and this engine wrote nothing, ever (S3 holds zero objects). Read
            # through the logger's own query, which opens and CLOSES its handle
            # (r430). And it says so at WARNING once, not at debug forever.
            rows = get_trade_logger().get_open_trades()
        except Exception as exc:                                # noqa: BLE001
            if not getattr(self, "_warned_unreadable", False):
                logger.warning("counterfactual: open positions unreadable: %s", exc)
                self._warned_unreadable = True
            return 0
        n = 0
        for r in rows:
            if self.evaluate(dict(r)):
                n += 1
        if n:
            self._store.commit()
        return n
