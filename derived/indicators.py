"""
derived/indicators.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v4.5  2026-10-12  OTV4TEST r274 (VWAP.2) — THE SESSION VWAP FOLDS ONLY CLOSED 1m BARS. The tick frame's
      last row is the FORMING minute; it was folded the first time it was seen - seconds in - and then
      skipped as already folded, so each minute counted only its first seconds. MEASURED 2026-10-12
      14:52 ET: 940,524 shares summed where the closed bars held 7,138,959 (13%); over 25 sessions the
      value sat a median 0.097 and up to 1.729 (09-28) from the closed-bar VWAP. A bar is folded once
      its minute has ended plus VWAP_CLOSE_GRACE_S (the feed rewrites a bar until its last update
      lands), complete. The operator, 2026-10-12 14:52 ET: "based on correct VWAP plus ranging. I know
      we've struggled a little bit with our VWAP formulas." GATE tests/check_vwap_closed_bars.py V1-V3.
v4.4  2026-09-22  OTV4TEST r101 — r96's COLD-START REBUILD WAS CALLED WITH AN
      EMPTY SYMBOL, AND FELL THROUGH IN SILENCE WHEN IT CAME BACK EMPTY. It
      read `self.symbol`, but `derive()` resolves `self.symbol or
      ctx["symbol"]` precisely because the attribute can be BLANK - so
      `fetch_candles("", "1m", 420)` returned nothing, the sixty-bar tick
      frame was folded anyway, and the engine reported 745.4476 against a
      true 744.7949 with the anchor still reading 09:30. The repair r96
      shipped could not run on the path that needed it. TWO HALVES: the
      symbol now comes from the CALLER, and an empty deep fetch WARNS rather
      than passing a partial window on in silence (SS0.5). GATE: A8, A9.
v4.3  2026-09-22  OTV4TEST r96 — A COLD START REBUILDS FROM THE TAPE, AND r94 WAS
      HALF A FIX. r94 anchored VWAP at the 09:30 open, but the live tick frame
      is SIXTY BARS - measured 2026-09-22 13:53 ET, 12:55->13:54 - so a cold
      start folded one hour and stamped it with a session anchor: 745.4264
      against a true 744.7697. WORSE THAN THE BUG r94 FIXED: a mismatched
      anchor FAILS CLOSED and says why, a partial window PASSES and feeds the
      butterfly's waiver a plausible wrong number. On a fresh anchor it now
      deep-fetches 420 1m bars - the same idiom the ORB engine already uses
      via rebuild_from_tape - and REPORTS WHERE THE FOLD REALLY BEGAN, so a
      short session fails the reader's own test by construction.
v4.2  2026-09-22  OTV4TEST r94 — VWAP ANCHORS AT THE SESSION OPEN, NOT MIDNIGHT.
      Operator, twice: "don't anchor VWAP to midnight" and "I want the VWAP
      anchored correctly". `idx[-1].normalize()` returned MIDNIGHT of the bar's
      day, folding overnight and pre-market prints - thin, away from the
      session's value area - into a number the butterfly reads as today's VWAP.
      Bars before the open are skipped by the existing `ms < anchor_ms` guard,
      so `vwap` stays None until 09:30 ET, which is correct rather than a gap.
Owns `indicator_series`. Tier 1 — path-dependent values.

v4.1  2026-09-20  OTV4TEST r69 (IND.1) — THE PER-TIMEFRAME LOOP HAD NEVER RUN.
      `list(trend.votes)` on a Dict yields its KEYS, so every vote was a string,
      every `getattr(vote,"timeframe")` was None, and the loop skipped all of
      them. 0 of 18,529 rows ever carried an EMA and every row was
      `interval='primary'`. One line: `.values()`. FORWARD-ONLY — history stays
      null. Gated by tests/check_indicator_votes.py.

v4.0  2026-08-22  See docs/DERIVED_STORES.md.

ADX, ATR, EMAs and VWAP. All four share one property: **recomputation is not
idempotent.** Each depends on where its window started, so the number an engine
sees can differ from the number it saw an hour ago for reasons that have
nothing to do with the market.

🔴 THIS IS NOT THEORETICAL. Friday 2026-08-21's rejection logs show ADX
swinging 16 -> 48 on the same symbols across ticks. Some of that is real. Some
may be window artifact, and **there is currently no way to tell** — nothing
keeps the series to compare against. `adx_at_entry` is a column on every trade
and `CONT_BREAKOUT_MIN_ADX` is a live gate, so if there is a recompute wobble,
both the gate and the study are contaminated by it. This table is what makes
that answerable.

🔴 VWAP STORES ITS ACCUMULATORS, NOT JUST THE VALUE. Sum(p*v), Sum(v) and the
anchor they started from. VWAP is cumulative from a FIXED anchor, so it is the
one value where a wrong window does not produce noise — it produces a
different indicator that still looks like a smooth line near price. Nothing
about it looks broken. The accumulators are what make it verifiable later.

⚠️ THE VW.1 SCAR: five wrong layers of analysis, because VWAP orientation was
RECONSTRUCTED after the fact instead of recorded when it happened. Storing the
series turns that class of investigation into a lookup.

⚠️ READS WHAT THE ENGINES ALREADY COMPUTED. This does not re-derive ADX from
bars — `trend_engine` and `volatility_engine` already did that this tick, and
computing it twice would give two numbers for one moment, which is the exact
disease. It records THEIR values.
"""

from __future__ import annotations

import pandas as _pd

# ⚠️ r96 — HOW LATE THE FIRST FOLDED BAR MAY SIT AND STILL COUNT AS THE
# SESSION. Two minutes absorbs a bar the store has not written yet; it
# does not absorb the three-and-a-half-hour gap measured on 2026-09-22.
_COVERAGE_SLACK_MS = 120_000

import logging
import time
from typing import Optional

from derived.base import DerivedEngine

logger = logging.getLogger(__name__)


def _f(v) -> Optional[float]:
    """Float or None. NEVER 0.0 as a fallback — see the module docstring."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f          # NaN -> None, not 0.0


# r274 (VWAP.2): a 1m bar is folded only once its minute ended at least this long ago.
VWAP_CLOSE_GRACE_S = 5.0


class IndicatorEngine(DerivedEngine):
    name = "indicators"
    table = "indicator_series"
    min_interval_s = 0.0                  # cheap: it only records

    def __init__(self, store=None, symbol: str = ""):
        super().__init__(store)
        self.symbol = symbol
        self._first_bar_ms = None
        # VWAP accumulators, per (symbol, session-anchor).
        self._pv: float = 0.0
        self._v: float = 0.0
        self._anchor_ms: Optional[int] = None
        self._last_bar_ms: Optional[int] = None

    # ── VWAP: accumulate rather than recompute ──────────────────────────
    def _accumulate_vwap(self, df_1m, sym: str = "") -> tuple:
        """Fold new 1m bars into the running sums. Returns (vwap, pv, v, anchor).

        ⚠️ FOLDS ONLY BARS NEWER THAN THE LAST ONE SEEN. Re-folding the whole
        frame each tick would double-count volume and drift the VWAP upward in
        a way that looks entirely plausible.
        ⚠️ RESETS ON A NEW SESSION ANCHOR. A VWAP that silently carries
        yesterday's accumulators into today is the wrong-window failure this
        table exists to expose.
        """
        if df_1m is None or getattr(df_1m, "empty", True):
            return None, None, None, None
        try:
            idx = df_1m.index
            # 🔴 r94 — THE SESSION OPEN, NOT MIDNIGHT. Operator's ruling,
            # 2026-09-20: *"don't anchor VWAP to midnight"*, and again
            # 2026-09-22: *"I want the VWAP anchored correctly."*
            # `normalize()` returns MIDNIGHT of the bar's day, so every
            # overnight and pre-market print was folded into a number the
            # butterfly reads as "today's VWAP". Those hours trade thin and
            # away from the session's real value area, so the anchor dragged
            # VWAP toward the overnight range and away from where the session
            # actually traded — a plausible number computed over the wrong
            # window, which is the exact failure this table exists to expose.
            # ⚠️ BARS BEFORE THE OPEN ARE SKIPPED BY THE `ms < anchor_ms`
            # GUARD BELOW, so pre-market accumulates nothing and `vwap` stays
            # None until 09:30 ET. That is correct rather than a gap: there is
            # no session VWAP before the session.
            day0 = idx[-1].normalize() + _pd.Timedelta(hours=9, minutes=30)
            anchor_ms = int(day0.timestamp() * 1000)
            if self._anchor_ms != anchor_ms:      # new session -> new anchor
                self._pv, self._v = 0.0, 0.0
                self._anchor_ms = anchor_ms
                self._last_bar_ms = None
                self._first_bar_ms = None
                # 🔴 r96 — A COLD START MID-SESSION MUST REBUILD FROM THE TAPE,
                # NOT FROM WHATEVER THE TICK FRAME HAPPENS TO HOLD.
                # MEASURED 2026-09-22 13:53 ET, minutes after r94 baked: the
                # live 1m frame is SIXTY BARS (12:55->13:54), so anchoring at
                # 09:30 and folding that frame produced a ONE-HOUR VWAP wearing
                # a session-open anchor — 745.4264 against a true 744.7697.
                # 🔴 AND THAT IS WORSE THAN THE BUG r94 FIXED. Before r94 a
                # mismatched anchor made `vwap_now()` FAIL CLOSED and say why;
                # a partial-window value PASSES validation and feeds the
                # butterfly's waiver a plausible wrong number. §0.5 — silence
                # is the worst failure, and a confident wrong number is worse
                # than silence.
                # 🔑 SAME IDIOM THE ORB ENGINE ALREADY USES on a cold start
                # (`fetch_candles(sym, "1m", ORB_REBUILD_1M_BARS)` ->
                # `rebuild_from_tape`), not a new mechanism.
                # ⚠️ THE SYMBOL COMES FROM THE CALLER, NOT `self.symbol`.
                # `derive()` resolves `self.symbol or ctx.get("symbol")`
                # precisely because the attribute can be empty — and my first
                # cut read the attribute, so the deep fetch was called with ""
                # and returned nothing. The engine then folded the sixty-bar
                # tick frame and reported 745.4476 against a true 744.7949,
                # with the anchor still reading 09:30.
                _dsym = sym or self.symbol or ""
                try:
                    from data.market_data import fetch_candles as _deep
                    _deep_df = _deep(_dsym, "1m", 420) if _dsym else None
                    if _deep_df is not None and not _deep_df.empty:
                        df_1m = _deep_df
                        idx = df_1m.index
                    else:
                        # 🔴 AND IT SAYS SO. My first cut fell through here in
                        # SILENCE, which is how a wrong VWAP reached the store
                        # wearing a correct anchor (§0.5).
                        logger.warning("VWAP cold start: deep 1m fetch returned "
                                       "nothing for %r — folding the tick frame "
                                       "only; coverage will be reported short",
                                       _dsym)
                except Exception as _de:                       # noqa: BLE001
                    logger.warning("VWAP cold start: deep 1m fetch failed (%s) "
                                   "— folding the tick frame only; the value "
                                   "may cover a partial session", _de)
            _closed_before_ms = (time.time() - VWAP_CLOSE_GRACE_S) * 1000.0 - 60_000.0
            for ts, row in df_1m.iterrows():
                ms = int(ts.timestamp() * 1000)
                if ms < anchor_ms:
                    continue                       # belongs to a prior session
                if ms > _closed_before_ms:
                    break                          # r274: still forming - folded complete on a later tick
                if self._last_bar_ms is not None and ms <= self._last_bar_ms:
                    continue                       # already folded
                h, l, c = _f(row.get("high")), _f(row.get("low")), _f(row.get("close"))
                v = _f(row.get("volume"))
                if None in (h, l, c) or v is None or v <= 0:
                    continue
                typical = (h + l + c) / 3.0
                if self._first_bar_ms is None:
                    self._first_bar_ms = ms
                self._pv += typical * v
                self._v += v
                self._last_bar_ms = ms
            # ⚠️ r96 — RECORD WHERE THE FOLD ACTUALLY BEGAN. Even 420 bars
            # can fall short (a late boot, a thin store), and the reader must
            # be able to tell a full session from a partial one rather than
            # trusting the anchor stamp. `vwap_now()` refuses when this sits
            # materially after the anchor.
            if self._v <= 0:
                return None, None, None, self._anchor_ms
            # 🔑 THE ANCHOR WE REPORT IS WHERE THE FOLD REALLY STARTED, not
            # where we wished it had. A partial session then fails the reader's
            # "is this today's open?" test by construction, instead of wearing
            # a session stamp it did not earn — the r94 defect this closes.
            _eff = self._first_bar_ms if self._first_bar_ms is not None else self._anchor_ms
            _covered = abs(float(_eff) - float(self._anchor_ms)) <= _COVERAGE_SLACK_MS
            if not _covered:
                logger.warning("VWAP covers a PARTIAL session — first folded bar "
                               "%.0fs after the anchor; reporting the real start so "
                               "the reader refuses it",
                               (float(_eff) - float(self._anchor_ms)) / 1000.0)
            return (self._pv / self._v, self._pv, self._v,
                    self._anchor_ms if _covered else _eff)
        except Exception as exc:                                # noqa: BLE001
            logger.debug("vwap accumulate skipped: %s", exc)
            return None, None, None, self._anchor_ms

    def derive(self, ctx: dict) -> int:
        store = self._store
        if store is None:
            return 0
        trend = ctx.get("trend")
        vol = ctx.get("vol")
        sym = self.symbol or ctx.get("symbol") or ""
        if not sym:
            return 0
        now = time.time()

        vwap, pv, v, anchor = self._accumulate_vwap(ctx.get("df_1m"), sym)

        rows = []
        # One row per timeframe the trend engine voted on, so ADX is recorded
        # PER FRAME rather than only the primary — the per-frame values are
        # what a later study needs to see disagreement.
        # 🔴 r69 — `TrendState.votes` IS A DICT, AND `list(a_dict)` YIELDS ITS KEYS.
        # This read `list(trend.votes)`, so `votes` was a list of the timeframe
        # STRINGS ('5m', '15m', ...). The loop below then asks each string for
        # `.timeframe`, gets None, and `continue`s EVERY iteration — so `rows`
        # stayed empty on every tick and the fallback below wrote the four EMAs
        # as None. MEASURED: 0 of 18,529 rows in this table have ever carried an
        # `ema_fast`, and EVERY row is `interval='primary'`.
        # 🔑 SO THE PER-FRAME LOOP HAS NEVER ONCE EXECUTED, which costs more than
        # the EMAs: its own comment says it exists "so ADX is recorded PER FRAME
        # rather than only the primary — the per-frame values are what a later
        # study needs to see disagreement." That disagreement signal has never
        # been recorded at all.
        # ⚠️ AND THE 2026-08-24 FIX BELOW MASKED IT PERMANENTLY. That change
        # keyed the fallback on the OUTCOME so a gap shows up as thin rows
        # rather than no rows — correct, and it worked: a row appears every
        # tick, so nothing ever looked broken. The SYMPTOM was fixed and the
        # CAUSE was never found. Thin plausible data instead of an error is the
        # class this repo keeps paying for.
        votes = list(trend.votes.values()) if trend and getattr(trend, "votes", None) else []
        if votes:
            for vote in votes:
                tf = getattr(vote, "timeframe", None)
                if not tf:
                    continue
                rows.append((
                    sym, tf, now, self._last_bar_ms,
                    _f(getattr(vote, "adx", None)),
                    _f(getattr(vol, "atr_current", None)),
                    _f(getattr(vol, "atr_normalized", None)),
                    _f(getattr(vote, "ema_fast", None)),
                    _f(getattr(vote, "ema_mid", None)),
                    _f(getattr(vote, "ema_slow", None)),
                    _f(getattr(vote, "ema_anchor", None)),
                    _f(vwap), _f(pv), _f(v), anchor,
                ))
        # 🔴 THE FALLBACK ASKED THE WRONG QUESTION — found live 2026-08-24.
        # It was `if votes: ... else: <primary row>`, so it fired only when the
        # list was EMPTY. But `TrendVote.timeframe` DEFAULTS TO "" and the loop
        # above does `if not tf: continue` — so a non-empty list of votes that
        # all lack a timeframe skipped every row, took the `if` branch, and
        # left `rows` EMPTY. `_write` returns 0 on an empty list without
        # touching the database: no exception, no write failure, nothing to
        # grep. `indicator_series` held ZERO ROWS on all fifteen boxes while
        # forks, levels and surface filled normally on the same pass.
        # 🔑 KEY THE FALLBACK ON THE OUTCOME, NOT THE INPUT. The original
        # comment states the intent exactly — "a gap in the trend engine shows
        # up as thin rows rather than as no rows at all" — and asking "were
        # there votes?" instead of "did we produce a row?" defeated it.
        if not rows:
            rows.append((
                sym, "primary", now, self._last_bar_ms,
                _f(getattr(trend, "primary_adx", None)) if trend else None,
                _f(getattr(vol, "atr_current", None)),
                _f(getattr(vol, "atr_normalized", None)),
                None, None, None, None,
                _f(vwap), _f(pv), _f(v), anchor,
            ))
        return store.append_indicators(rows)
