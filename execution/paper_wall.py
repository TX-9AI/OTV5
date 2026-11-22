"""
execution/paper_wall.py  v5.0
v5.0  2026-11-22  OTV5 r150 (OGAP.5) — new. ON A LIVE BOX OGAP KEEPS PAPER-TRADING, WALLED OFF FROM THE CASH ACCOUNT.
      The operator, 2026-11-22: "I want it paper trading even on the cash boxes. It's under evaluation. Why the fuck would
      I want to stop evaluating it?" and earlier "Can we have it run as 'log only' or essentially continue paper trading
      it even after a box flips to cash? Maybe like a shadow trader". r149 made OGAP DORMANT on a live box; this replaces
      that rule. OGAP is ALWAYS PAPER: on a paper box it books exactly as before (the box's own paper engines, nothing
      here runs); on a LIVE box (BotState.paper_trading False) every OGAP entry and exit goes through THIS book.

      THE WALLS (each is a gate mutant in tests/check_ogap_paper_on_live.py):
        W1 ENTRY    - main._execute_entry_signal hands a walled signal to entry_engine() below: a paper EntryEngine
                      (_paper_fill_single, limit_ladder.paper_fill_price at the mark). No order, no dry run, no buying
                      power read, no order_guard.clear_to_post, no live entry walk, no freeze_contract; the row is
                      paper_trade = 1; the cap counterfactual (risk_manager.note_entry_risk, a cash-cap study) is not
                      written for it.
        W2 BOOK     - the record goes to book() below, never to the live PositionManager, so the live admission table,
                      has_blocking_position, the floor watch, the blind REST pricing and the live hard close never see
                      it. A paper position cannot block, delay or displace a cash entry or exit.
        W3 EXIT     - book() manages with its OWN paper ExitEngine (get_exit_engine is a singleton built LIVE on a live
                      box): the paper exit at the mark; its own 15:45 close (ogap_close_1545) at the mark; at the hard
                      close the paper EOD rule (held to the 15:55 cross, booked at the mark), never the live cross or the
                      debit ladder. blind_rest_marks stays False (no REST quote read: a blind tick skips the book).
        W4 CAP      - THE OPERATOR'S RULING, 2026-11-22: "The cap on a live box is for live trades only. Full stop."
                      On a LIVE box the daily catastrophic cap counts the cash trades only and governs cash trading
                      only: trade_logger.realized_pnl_today reads COALESCE(paper_trade,1) = the box's mode (0 live), so
                      a paper_trade = 1 row never counts toward it, whatever its size; this book's close never calls
                      risk_manager.record_win / record_loss; and a tripped cash cap does NOT stop the walled OGAP
                      (main._ask_walled_past_cap asks it after every cash refusal, asked_past_cap()). On a PAPER box
                      nothing here is read: every row is paper and OGAP is inside the cap as r137 CAP.10 ("both trades
                      should fall under the catastrophic cap"). The budget is the box's RISK_PER_TRADE_USD (configure.sh
                      item 2, OT_RISK_USD) on every box, as main's sizer already reads for OGAP (the operator,
                      2026-11-22: "it should get its budget from configure.sh like the rest").
        W5 RECONCILE- the boot reconcile, the intraday reconcile and adoption, the startup cancel of working orders
                      (order_guard.boot_sweep keeps the order ids of the open rows it reads) and the suspect resolution
                      all read the live TradeLogger, which on a live box reads paper_trade = 0 rows only; this book reads
                      its own logger (paper_trade = 1, OGAP rows only). No OGAP position ever reaches the broker, so no
                      "at bot, not at broker" phantom can exist for it.
        W6 RESTART  - recover() (after main._recover_open_position) closes an expired walled row (flagged pnl 0, no
                      broker read for the settlement) and resumes the open ones on this book.
      Rows live in the box's one trades.db (configure.sh item 3 archives the paper trades.db when the box goes live; the
      fresh live trades.db then holds the cash rows with paper_trade = 0 and OGAP's with paper_trade = 1), so the
      warehouse push, S3 and control's held-contracts page (per-row paper_trade) see them, and every report can tell
      them apart. The entry alert already says [PAPER] (it reads the row); the exit alert's setup reads "PAPER <setup>".
      No config key, no env read, no box flag value: OGAP is paper on every box until the operator says otherwise.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from database.trade_logger import TradeLogger, TradeRecord, get_trade_logger
from execution.entry_engine import EntryEngine
from execution.exit_engine import ExitEngine
from execution.position_manager import PositionManager

logger = logging.getLogger(__name__)

GATES = {}        # WA section 36: this file owns no gate constant

# The setups that book paper on EVERY box (the operator, 2026-11-22). A name here is never sent to the broker.
WALLED = ("OGAP",)


def asked_past_cap(paper_box) -> bool:
    """W4 — True on a LIVE box: a tripped cash cap does not stop the walled setups (the operator, 2026-11-22: "The cap
    on a live box is for live trades only. Full stop."). False on a paper box (r137 CAP.10: OGAP is inside the cap)."""
    return paper_box is not True


def walled(strategy, paper_box) -> bool:
    """True when `strategy` books on this walled paper book: a LIVE box (paper_box is not True) and a WALLED setup.
    A paper box is never walled (its own engines are already paper). An unreadable mode counts as live (walled):
    the walled path makes no broker call, so the wrong answer here can only ever be paper."""
    return paper_box is not True and str(strategy or "") in WALLED


class WallTradeLogger(TradeLogger):
    """The paper-mode logger, narrowed to the WALLED setups: on a live box the only paper_trade = 1 rows the bot writes
    are walled ones (configure.sh item 3 starts the live trades.db empty), and this keeps any other paper row out of
    this book even if one was left behind. Writes are trade_id-keyed and shared with TradeLogger."""

    def get_open_trades(self) -> List[TradeRecord]:
        return [r for r in super().get_open_trades() if str(r.get("strategy") or "") in WALLED]


class PaperWallEntry(EntryEngine):
    """A paper EntryEngine (paper_trading=True: _place_single_leg returns _paper_fill_single, the mark). PAPER_WALL
    skips the cap counterfactual in _book_fill (a cash-cap study)."""
    PAPER_WALL = True

    def __init__(self):
        super().__init__(paper_trading=True)


class PaperWallBook(PositionManager):
    """A paper PositionManager with its own paper ExitEngine and the walled logger. PAPER_WALL skips the risk tally
    (record_win / record_loss) and labels the exit alert PAPER in _execute_exit."""
    PAPER_WALL = True

    def __init__(self):
        super().__init__(paper_trading=True)
        self._trade_logger = WallTradeLogger(db_path=get_trade_logger().db_path, paper_trading=True)
        self._paper_exit = ExitEngine(paper_trading=True)
        self.blind_rest_marks = False

    def _exit_engine(self) -> ExitEngine:
        return self._paper_exit


_BOOK: Optional[PaperWallBook] = None
_ENTRY: Optional[PaperWallEntry] = None


def book() -> PaperWallBook:
    global _BOOK
    if _BOOK is None:
        _BOOK = PaperWallBook()
    return _BOOK


def entry_engine() -> PaperWallEntry:
    global _ENTRY
    if _ENTRY is None:
        _ENTRY = PaperWallEntry()
    return _ENTRY


def reset() -> None:
    """Drop both singletons (tests; a new trades.db)."""
    global _BOOK, _ENTRY
    _BOOK = _ENTRY = None


def recover() -> int:
    """W6 — at start on a LIVE box (main calls it after _recover_open_position): close an EXPIRED walled row (pnl 0,
    flagged; no settlement read, which would ask the broker), then load the open walled rows onto book(). Returns the
    number resumed. Never raises."""
    try:
        from utils.time_utils import now_et
        b = book()
        today = now_et().strftime("%Y-%m-%d")
        rows = b._trade_logger.get_open_trades()
        keep = []
        for r in rows:
            exp = TradeLogger._expiry_date(r.get("expiry", ""))
            if exp and exp < today:
                b._trade_logger.close_phantom(str(r.get("trade_id") or ""), reason="expired_orphan_autoclosed_paper_wall")
            else:
                keep.append(r)
        b.set_open_positions(keep)
        if keep:
            logger.warning("[paper-wall] resumed %d walled paper position(s) on the paper book: %s", len(keep),
                           ", ".join("%s %s" % (r.get("strategy"), str(r.get("trade_id") or "")[:8]) for r in keep))
        return len(keep)
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[paper-wall] recovery skipped (%s: %s) - the book reloads from trades.db on its next pass",
                       type(exc).__name__, exc)
        return 0
