"""
execution/shadow_book.py  v5.0
v5.0  2026-10-30  OTV5 r57 (TCS.LOG1) — new. A LOG-ONLY TrendCreditSpread IS A FULL SHADOW TRADE THAT NEVER ORDERS.
      The operator, 2026-10-30: "Can you reactivate TCS Monday as 'log only'? But do not trade it." then "Make sure
      TCS logs everything an executable trade logs."

WHAT A SHADOW TRADE IS
  strategy/plan_state.py puts TrendCreditSpread in LOG by default (OT_TCS_ACTIVE unset). Its signal then runs the
  REAL credit door, main._execute_condor_leg: the entry gate, the contracts the strategy chose from the box's chain,
  the risk manager's vertical sizing, the paper fill (limit_ladder.paper_fill_credit of the mark - what a paper box
  books), the SAME make_record call. At the one line where a real trade is written and handed to the broker-facing
  position manager, a shadow is handed HERE instead: its trade_id becomes "shadow-<uuid>", it is written to its OWN
  store and managed every tick by the SAME position_manager code (_manage_one / flatten_all / _execute_exit), the
  SAME management plan logic (breach-or-nickel for a TCS) and the SAME exit engine code, at the mark, with paper
  fills - each in a separate instance so no state is shared with the real book.

THE STORE IS A SEPARATE FILE: shadow_trades.db (beside trades.db, or OT_SHADOW_TRADES_DB). Its table is built by the
  trades store's own TradeLogger (so it carries EVERY trades column, by construction, now and after any future add)
  plus three shadow columns: shadow (1), shadow_box_paper (the box's mode: 1 paper, 0 live) and shadow_plan_state
  ("log"). A separate FILE, not a table in trades.db, because then nothing that reads trades.db - the risk manager's
  loss cap and session counts, count_today, the pairing gate, the condor sibling probe, broker reconcile, the
  phantom / orphan / expiry sweeps, query.py, status.py, the warehouse push of raw/trades, dtp's readers - can see a
  shadow row, whatever it selects. The warehouse gets them as their own stream, raw/shadow_trades (s3_push v5.3).

PER-TICK ROWS. The management plan's check rows are written under "TrendCreditSpread[shadow]/manage" (never the real
  "TrendCreditSpread/manage"), the r66 vector under "TrendCreditSpread[shadow]", the premium map / fire snapshot keyed
  by the shadow- trade_id. The legs' quotes are in quote_series exactly as a real trade's are: the box streams every
  contract of the chain it selects from (data/options_chain publishes the whole front-expiry chain to chain_subs),
  and short_symbol / long_symbol on the row are the replay keys tests/exit_replay.py reads.

ISOLATION (pinned by tests/check_tcs_shadow.py)
  - never ordered: the credit door skips the live order block for a shadow (paper fill, order_id "SHADOW"); this
    book's manager is paper-only (paper_trading is forced True and cannot be set), its exit engine refuses the live
    close outright, and nothing here imports the broker client.
  - not a position: never in get_position_manager()'s records, so no slot, no admission cap, no symbol hold, no
    has_open_position branch, no EOD flatten of the real book, no reconcile.
  - not a P&L: no risk_manager.note_entry_risk / record_win / record_loss, no Telegram trade alert (one "[shadow]"
    log line instead), never in trades.db.
  - never blocks a real entry: no real gate reads this store. A shadow is itself refused while a shadow TCS is open
    (admission's TCS rule, max_open_of_type=1, applied to its own book; the real admission counts the real book).

RESTART. The real paper trade resumes: boot closes TRULY EXPIRED open rows (at their settlement value where it can be
  priced, else flagged) and resumes every live one. The shadow book does the same against its own store
  (resume_at_boot), minus anything broker-side. A shadow open at a restart is therefore managed on from the next tick.

DORMANT (OT_TCS_ACTIVE=0) writes nothing: the plan is never asked, and the store is never created.
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

from database.trade_logger import TradeLogger, TradeRecord
from execution.exit_engine import ExitEngine, FillResult
from execution.position_manager import PositionManager

logger = logging.getLogger(__name__)

GATES = {}      # WA §36: this file owns no gate constant

SHADOW_PREFIX = "shadow-"
PLAN_LABEL = "[shadow]"          # "TrendCreditSpread[shadow]/manage"
SHADOW_STRATEGIES = ("TrendCreditSpread",)


def shadow_db_path() -> str:
    """The shadow store, read NOW: OT_SHADOW_TRADES_DB, else shadow_trades.db beside the trades store."""
    p = os.environ.get("OT_SHADOW_TRADES_DB", "")
    if p:
        return p
    import config as _c
    return os.path.join(os.path.dirname(os.path.abspath(_c.DB_PATH)), "shadow_trades.db")


class ShadowTradeLogger(TradeLogger):
    """The trades store's own code against shadow_trades.db, plus three shadow columns. Paper-scoped reads."""

    EXTRA_ADDS = (
        ("shadow",            "INTEGER DEFAULT 1"),   # every row here is a shadow
        ("shadow_box_paper",  "INTEGER"),             # the box's mode when it was booked (1 paper, 0 live)
        ("shadow_plan_state", "TEXT"),                # the plan state that made it a shadow ("log")
    )

    def __init__(self, db_path: str = ""):
        super().__init__(db_path or shadow_db_path(), paper_trading=True)


class ShadowExitEngine(ExitEngine):
    """The exit engine's code, its OWN per-trade state, the shadow store, and paper fills only."""

    def __init__(self, trade_logger: ShadowTradeLogger):
        super().__init__(paper_trading=True)
        self._trade_logger = trade_logger

    @property
    def paper_trading(self):                    # noqa: D401 - always paper, whatever is assigned
        return True

    @paper_trading.setter
    def paper_trading(self, _value):
        pass

    def _confirm_and_book_live_exit(self, record, reason, mark_price=None):   # pragma: no cover - unreachable
        logger.error("[shadow] REFUSED a live close for %s - a shadow never orders", str(record.get("trade_id"))[:15])
        return FillResult(confirmed=False, detail="shadow: never ordered")


def _management_plan_class():
    from strategy.management import ManagementPlan, Plan, MGMT_CHECKS

    class ShadowManagementPlan(ManagementPlan):
        """The management plan's decide() code; its rows under "<Strategy>[shadow]/manage"."""

        def _plan(self, strategy: str):
            key = f"{strategy}{PLAN_LABEL}/manage"
            if key not in self._plans:
                self._plans[key] = Plan(key, MGMT_CHECKS, self_ledgers=True)
            return self._plans[key]

        def _vector(self, ctx, strategy, rec):
            return super()._vector(ctx, f"{strategy}{PLAN_LABEL}", rec)

    return ShadowManagementPlan


class ShadowPositionManager(PositionManager):
    """position_manager's management and close code over the shadow store. Paper only; SHADOW gates the real-book
    side effects of a close (position_manager v5.28)."""

    SHADOW = True

    def __init__(self, trade_logger: ShadowTradeLogger):
        self._open_records: List[TradeRecord] = []
        self._trade_logger = trade_logger
        self._engine = ShadowExitEngine(trade_logger)
        self._mgmt = _management_plan_class()()

    @property
    def paper_trading(self):
        return True

    @paper_trading.setter
    def paper_trading(self, _value):
        pass

    def _exit_engine(self):
        return self._engine

    def _management(self):
        return self._mgmt


class ShadowBook:
    def __init__(self, db_path: str = ""):
        self.logger = ShadowTradeLogger(db_path)
        self.pm = ShadowPositionManager(self.logger)

    # ── entry ────────────────────────────────────────────────────────────────
    def tcs_open(self) -> bool:
        """An open shadow TCS (admission's max_open_of_type=1 for TrendCreditSpread, on this book)."""
        self.pm.has_open_position()
        return any(str(r.get("strategy", "")) == "TrendCreditSpread" for r in self.pm.get_open_records())

    def open_entry(self, record: TradeRecord, *, box_paper: bool) -> bool:
        """Book `record` (built by main._execute_condor_leg) as a shadow. Never raises; False = not booked."""
        try:
            tid = str(record.get("trade_id") or "")
            if not tid.startswith(SHADOW_PREFIX):
                record["trade_id"] = SHADOW_PREFIX + tid
            record["order_id"] = "SHADOW"
            record["paper_trade"] = 1                       # booked at the paper fill, whatever the box's mode
            record["shadow"] = 1
            record["shadow_box_paper"] = 1 if box_paper else 0
            record["shadow_plan_state"] = "log"
            self.logger.log_entry(record)
            self.pm.add_condor_leg(record)
            return True
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[shadow] could not book %s: %s - nothing recorded", str(record.get("trade_id"))[:15], exc)
            return False

    # ── every tick ───────────────────────────────────────────────────────────
    def has_open(self) -> bool:
        return self.pm.has_open_position()

    def manage(self, ctx: dict) -> bool:
        """One management pass over the open shadows (the real loop's manage_open_position call). Never raises."""
        try:
            if not self.pm.has_open_position():
                return False
            ctx = ctx or {}
            return self.pm.manage_open_position(chain=ctx.get("chain"), df_1m=ctx.get("df_1m"),
                                                df_5m=ctx.get("df_5m"), vol_state=ctx.get("vol"),
                                                trend=ctx.get("trend"))
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[shadow] manage pass failed: %s - the shadow stays open", exc)
            return True

    def flatten(self, chain=None, spot: Optional[float] = None) -> List[str]:
        """The end of day: position_manager.flatten_all over the shadows (the same EOD.1 clock and paper cross)."""
        try:
            if not self.pm.has_open_position():
                return []
            return self.pm.flatten_all(chain=chain, spot=spot)
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[shadow] EOD pass failed: %s", exc)
            return []

    # ── restart ──────────────────────────────────────────────────────────────
    def resume_at_boot(self, settle=None) -> int:
        """The real boot's Steps 1-2 against the shadow store: expired rows closed (settled where priceable), the
        live ones resumed. Returns how many are resumed."""
        try:
            expired = self.logger.close_expired_open_trades(settle=settle)
            for r in expired:
                logger.info("[shadow] expired at boot: %s closed (%s)", str(r.get("trade_id"))[:15],
                            r.get("expiry", ""))
            live = self.logger.get_open_trades_live()
            self.pm.set_open_positions(live)
            if live:
                logger.info("[shadow] resumed %d open shadow trade(s) at boot: %s", len(live),
                            ", ".join(str(r.get("trade_id"))[:15] for r in live))
            return len(live)
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[shadow] boot resume failed: %s", exc)
            return 0


_BOOK: Optional[ShadowBook] = None


def get_shadow_book() -> ShadowBook:
    """The book, created on first use (the first shadow entry creates the store)."""
    global _BOOK
    if _BOOK is None:
        _BOOK = ShadowBook()
    return _BOOK


def peek_shadow_book() -> Optional[ShadowBook]:
    """The book if it exists or its store does, else None - so a box that never booked a shadow creates nothing."""
    global _BOOK
    if _BOOK is None and os.path.exists(shadow_db_path()):
        _BOOK = ShadowBook()
    return _BOOK


def is_shadow_signal(signal) -> bool:
    """True when `signal` is a TrendCreditSpread whose plan is in LOG and which is not observed past its entry end
    (OBS.1 refuses that one, as it would a real one). Never raises; False on any doubt (the caller then refuses it
    LOG-ONLY as before - never an order)."""
    try:
        name = str(getattr(signal, "strategy_name", "") or "")
        if not (getattr(signal, "is_trend_credit", False) or name == "TrendCreditSpread"):
            return False
        import config as _c
        if bool(getattr(_c, "TREND_CREDIT_ACTIVE", False)):
            return False
        from strategy import plan_state as _ps
        if not _ps.is_log("TrendCreditSpread"):
            return False
        from strategy import observe as _ob
        if name in getattr(_ob, "_ACTIVE", set()):
            return False
        return True
    except Exception:                                           # noqa: BLE001
        return False
