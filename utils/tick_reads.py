"""
utils/tick_reads.py  v5.0
v5.0  2026-11-22  OTV5 r147 (QTIME.1) — new. RECORD WHEN EACH TICK READ ITS QUOTES. Record only: nothing here is read
      by any decision. The operator, 2026-11-22: "Yes to both" (the WS.15 pricer's one unrecorded input).

      WHY: the bot reads bid/ask from the feed store's chain_marks, which data/candle_feed.py refreshes on its
      FLUSH_INTERVAL_S (2 s) flush, so the mark a tick acts on is 0-4 s old; before r147 neither the read time nor the
      store's refresh time of the rows read was in S3, so a replay from raw/quote_series could not pick the quote the
      bot saw (the WS.15 pricer, ~/reviews/studies/pricer_ws1415_v11_20261122/).

      THE THREE TICK TIMES (one dict, the same keys everywhere they are written):
        tick_start_epoch   main_loop's tick_start (time.time() at the top of the tick, before any read);
        marks_read_epoch   when this tick's chain read chain_marks (OptionsChain.marks_read_epoch, set by
                           OptionsChainFetcher._read_marks from the clock it already read for its staleness floor);
        marks_store_epoch  the store's own refresh point for that read: the newest updated_epoch among the chain_marks
                           rows the same SELECT returned (OptionsChain.marks_store_epoch; one SQLite snapshot, no
                           second read). candle_feed writes each row's updated_epoch as the receive time of the event
                           it holds and commits every row of a flush at once, so this is the newest event the last
                           committed flush carried.
      Per row, the priced contract's own chain_marks.updated_epoch rides beside them as quote_epoch (plan_tick) or
      contract.quote_epoch (signal_journal), from OptionContract.quote_epoch (r139).

      TWO VIEWS, because the plan board's rows are written a tick late by close_tick:
        latest()   the tick in progress (main calls begin() at the top of the tick and chain_read() after the chain
                   fetch); analysis/signal_journal stamps every row with it;
        adopted()  the tick the plan board is in: strategy/plan.begin_tick() calls adopt(), which copies latest(), so
                   close_tick's rows for the tick just ended keep that tick's times and every row written after the
                   board's begin_tick (the plans, the /manage rows) carries this tick's.
      A tick that read no chain (blind, the 15:40-15:50 manage branch, the pre-open rehearsal) carries its
      tick_start_epoch and NULL read times; nothing is invented. Values are None when unknown, never 0.

      ZERO broker calls, no file or database access, no config key, no env read: two clock values the tick already
      has and one max() over rows already in memory. Never raises.
"""
from __future__ import annotations

from typing import Optional

KEYS = ("tick_start_epoch", "marks_read_epoch", "marks_store_epoch")

_LATEST: dict = {}
_ADOPTED: dict = {}


def _pos(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def begin(tick_start) -> None:
    """The top of a main-loop tick: a new record with only the tick's start (the reads are not made yet)."""
    global _LATEST
    try:
        _LATEST = {"tick_start_epoch": _pos(tick_start), "marks_read_epoch": None, "marks_store_epoch": None}
    except Exception:                                           # noqa: BLE001
        _LATEST = {}


def chain_read(chain) -> None:
    """After the tick's chain fetch: the read time and the store time that chain carries (None leaves them NULL)."""
    try:
        if chain is None:
            return
        _LATEST["marks_read_epoch"] = _pos(getattr(chain, "marks_read_epoch", None))
        _LATEST["marks_store_epoch"] = _pos(getattr(chain, "marks_store_epoch", None))
    except Exception:                                           # noqa: BLE001
        pass


def adopt() -> None:
    """The plan board's begin_tick: from here the board's rows carry the tick in progress."""
    global _ADOPTED
    try:
        _ADOPTED = dict(_LATEST)
    except Exception:                                           # noqa: BLE001
        _ADOPTED = {}


def latest() -> dict:
    return {k: _LATEST.get(k) for k in KEYS}


def adopted() -> dict:
    return {k: _ADOPTED.get(k) for k in KEYS}


def quote_epoch(obj) -> Optional[float]:
    """A contract's own store time (OptionContract.quote_epoch), None when unknown."""
    try:
        return _pos(getattr(obj, "quote_epoch", None))
    except Exception:                                           # noqa: BLE001
        return None


def reset() -> None:
    global _LATEST, _ADOPTED
    _LATEST, _ADOPTED = {}, {}
