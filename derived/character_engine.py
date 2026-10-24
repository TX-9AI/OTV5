"""
derived/character_engine.py  v4.2
v4.2  2026-10-24  CD.2 — _hydrate adopts the open row only if it entered on or after TODAY's session start (ET midnight); an
      older open row is closed as stale (exited_ts = now) and not adopted. The docstring said "today's open row"; the
      query had no date filter, so a character from days ago - or a seeded one - became the incumbent with a held_s
      of days, and while BANDS_SET is False nothing displaces it.
Owns `character_ledger`. Transitions, not per-tick values.

v4.0  2026-08-25  See analysis/character.py for the measurement and the
operator's rulings. This module only decides WHEN a change is real enough to
record, and writes it down.

🔴 THE ACCEPTANCE GATE IS THE OPERATOR'S 20-YEAR PRIOR: **1-3 character changes
per symbol-day.** The retired L2 engine produced ~20/symbol-day, and that
10-20x gap against the same prior is what made its churn visible at all. If
this deriver yields fifteen a day the design is wrong no matter how sensible
the maths looks — check the count before trusting anything downstream.

⚠️ TRANSITIONS ARE THE OBJECT, NOT SAMPLES. A per-tick character value would
be ~1,560 rows per symbol-day saying almost nothing. What is worth knowing is
that the tape CHANGED, when, and what it changed from. The raw axes stay at
full resolution in the row so a study can see how close the call was.

⚠️ A CHARACTER THAT HELD ALL SESSION AND ONE THAT FLIPPED SIX TIMES ARE
DIFFERENT SESSIONS — operator's point, and the reason the ledger stores
`held_s` on the row that closes.

⚠️ ADX AND ATR ARE RECORDED PARALLEL, NOT FED IN. See analysis/character.py.
They are on the row so a study can ask whether they agree; blending them would
make agreement true by construction.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from derived.base import DerivedEngine

logger = logging.getLogger(__name__)

# Vol baseline window: how many prior readings define "normal for this symbol".
# 🔴 F5: BASELINE_N=40 AT A 15s CADENCE SPANNED TEN MINUTES — and the value it
# sampled is a 120-bar realised vol, so the "baseline" was two bars deep. A
# tripling of volatility showed vol_ratio 1.000 for the next 150 ticks because
# the spike had already walked into the baseline it was being compared against.
# ⚠️ THE FIX IS A STRIDE, NOT A BIGGER N. Sampling every tick makes the window
# short in TIME however many samples it holds; sampling every Nth tick makes 60
# samples span a session.
BASELINE_STRIDE_S = 300.0        # one sample per 5 minutes
BASELINE_N = 60                  # 60 samples x 5 min = ~5 hours, a session


def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


class CharacterEngine(DerivedEngine):
    name = "character"
    table = "character_ledger"
    min_interval_s = 15.0

    def __init__(self, store=None, symbol: str = ""):
        super().__init__(store)
        self.symbol = symbol
        self._state: Optional[str] = None
        self._since: float = 0.0
        self._row_id: Optional[int] = None
        self._vol_hist: list = []
        self._last_sample_ts: float = 0.0
        self._made = False
        self._hydrated = False

    def _ensure(self):
        if self._made or self._store is None:
            return
        try:
            self._store.conn.execute("""
                CREATE TABLE IF NOT EXISTS character_ledger (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol      TEXT NOT NULL,
                    character   TEXT NOT NULL,
                    entered_ts  REAL NOT NULL,
                    exited_ts   REAL,
                    held_s      REAL,
                    from_character TEXT,
                    -- the axes AT THE MOMENT OF THE CHANGE, full resolution
                    persistence REAL,
                    vol_ratio   REAL,
                    realised_vol_cc REAL,
                    realised_vol_parkinson REAL,
                    -- ⚠️ PARALLEL CORROBORATORS, NOT INPUTS. Recorded so a
                    -- study can ask whether they agree; feeding them in would
                    -- make agreement true by construction.
                    adx         REAL,
                    atr_normalized REAL,
                    -- ⚠️ THE OPENING GAP, ALSO PARALLEL. Operator's ruling
                    -- 2026-08-25: recorded beside the axes, never fed into
                    -- them. The temptation was real — the volatility axis is
                    -- UNMEASURABLE on the opening rows until the baseline has
                    -- 10 readings, and the gap is the one quantity fully known
                    -- at 09:30. Seeding the axis with it would have made "does
                    -- the gap predict the opening character" UNANSWERABLE,
                    -- because the answer would be built in.
                    -- ⚠️ AND THE v3 SCOPE FLAG APPLIES: a window spanning the
                    -- overnight boundary reads a large slope from the gap
                    -- ALONE, and ATR across the gap spikes. The gap must be
                    -- VISIBLE without CONTAMINATING intraday geometry — which
                    -- is the argument for its own column rather than a blend.
                    gap_pct     REAL,
                    gap_class   TEXT,
                    price       REAL
                );""")
            self._store.conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_char_sym "
                "ON character_ledger(symbol, entered_ts)")
            # ⚠️ THE SAMPLE TABLE IS SEPARATE FROM THE LEDGER ON PURPOSE. The
            # ledger holds TRANSITIONS (a state with a duration); this holds
            # raw axis readings. Merging them would put two different objects
            # in one table and make "how many character changes today" a query
            # that has to filter.
            self._store.conn.execute("""
                CREATE TABLE IF NOT EXISTS character_axis_sample (
                    symbol     TEXT NOT NULL,
                    ts_epoch   REAL NOT NULL,
                    efficiency REAL,
                    vol_ratio  REAL,
                    close_capture REAL,
                    realised_vol_cc REAL,
                    realised_vol_parkinson REAL,
                    adx        REAL,
                    atr_normalized REAL,
                    price      REAL,
                    PRIMARY KEY (symbol, ts_epoch)
                );""")
            self._made = True
        except Exception as exc:                                # noqa: BLE001
            logger.debug("character_ledger table: %s", exc)

    def current(self) -> dict:
        """What status.py reads: the live character and how long it has held."""
        if not self._state:
            return {}
        return {"character": self._state,
                "held_s": round(time.time() - self._since),
                "since": self._since}

    def recent(self, limit: int = 5) -> list:
        """The last N CHANGES with timestamps — what query.py reads."""
        if self._store is None:
            return []
        try:
            self._ensure()
            cur = self._store.conn.execute(
                "SELECT character, from_character, entered_ts, held_s,"
                " persistence, vol_ratio, gap_pct, gap_class"
                " FROM character_ledger"
                " WHERE symbol=? ORDER BY entered_ts DESC LIMIT ?",
                (self.symbol, int(limit)))
            return [{"character": r[0], "from": r[1], "at": r[2],
                     "held_s": r[3], "persistence": r[4], "vol_ratio": r[5],
                     "gap_pct": r[6], "gap_class": r[7]}
                    for r in cur.fetchall()]
        except Exception:                                       # noqa: BLE001
            return []

    def _hydrate(self) -> None:
        """Adopt today's open row as the incumbent. Runs once.

        🔴 F5: `_state`, `_row_id` and `_vol_hist` were PROCESS MEMORY. A
        restart left the open row's `held_s` NULL forever and inserted a
        margin-free spurious transition, because the displacement check
        compares against an incumbent the new process does not have.
        ⚠️ THE LEDGER IS THE INCUMBENT, not the process. Same rule the plan
        ledger already follows.
        """
        if self._hydrated or self._store is None:
            return
        self._hydrated = True
        try:
            self._ensure()
            row = self._store.conn.execute(
                "SELECT id, character, entered_ts FROM character_ledger"
                " WHERE symbol=? AND exited_ts IS NULL"
                " ORDER BY entered_ts DESC LIMIT 1", (self.symbol,)).fetchone()
            if row:
                # CD.2 — today's session only (ET midnight); an older open row is stale, not the incumbent
                from datetime import datetime as _dt
                from zoneinfo import ZoneInfo as _Z
                _now = time.time()
                _day0 = _dt.fromtimestamp(_now, _Z("America/New_York")).replace(
                    hour=0, minute=0, second=0, microsecond=0).timestamp()
                if float(row[2]) >= _day0:
                    self._row_id, self._state, self._since = row[0], row[1], row[2]
                    logger.info("[character] resumed %s from the ledger "
                                "(open since %.0f)", self._state, self._since)
                else:
                    self._store.conn.execute(
                        "UPDATE character_ledger SET exited_ts=?, held_s=? WHERE id=?",
                        (_now, _now - float(row[2]), row[0]))
                    self._store.commit()
                    logger.info("[character] open row %s from %.0f predates today's session - closed as stale, "
                                "not adopted (CD.2)", row[1], float(row[2]))
        except Exception as exc:                                # noqa: BLE001
            logger.debug("character hydrate: %s", exc)

    def derive(self, ctx: dict) -> int:
        self._hydrate()
        from analysis.character import (efficiency, close_capture,
                                        volatility_state, read_character,
                                        qualifies_to_displace)
        if self._store is None:
            return 0
        cc = _f(ctx.get("realised_vol_cc"))
        pk = _f(ctx.get("realised_vol_parkinson"))

        # Volatility is judged against THIS SYMBOL'S OWN recent baseline.
        # ⚠️ NOT AN ABSOLUTE THRESHOLD — see analysis/character.py. A rolling
        # median is used rather than a mean so one spike cannot redefine
        # "normal" for the rest of the session.
        # ⚠️ STRIDED. See BASELINE_STRIDE_S — appending every tick made the
        # baseline a ten-minute window wearing a 40-sample costume.
        now_s = time.time()
        if cc is not None and (now_s - self._last_sample_ts) >= BASELINE_STRIDE_S:
            self._last_sample_ts = now_s
            self._vol_hist.append(cc)
            if len(self._vol_hist) > BASELINE_N:
                self._vol_hist.pop(0)
        base = None
        if len(self._vol_hist) >= 10:
            s = sorted(self._vol_hist)
            base = s[len(s) // 2]

        # ⚠️ EFFICIENCY NEEDS THE CLOSES, not two vol estimates. df_5m is on
        # ctx from `assemble_market_state`; a missing frame yields None, which
        # the ledger records as "not measurable" rather than a midpoint.
        _closes = None
        try:
            _df = ctx.get("df_5m")
            if _df is not None and len(_df):
                _closes = list(_df["close"].tail(120))
        except Exception:                                       # noqa: BLE001
            _closes = None
        p = efficiency(_closes) if _closes else None
        cap = close_capture(cc, pk)
        vr = volatility_state(cc, base)
        challenger = read_character(p, vr)

        # 🔴 THE AXES ARE SAMPLED EVEN WHEN NO STATE IS EMITTED. With
        # BANDS_SET=False `challenger` is always None, so the transition path
        # below never runs — and without this the ledger would record NOTHING,
        # which defeats the whole reason for holding the bands back. **The
        # sample IS the deliverable right now**: one session of real efficiency
        # values is what the bands get derived from.
        # ⚠️ STRIDED, NOT PER TICK. A 15s cadence would write ~1,560 rows per
        # symbol-day to answer a question a few hundred answers just as well.
        try:
            if p is not None or vr is not None:
                if (now_s - getattr(self, "_last_axis_ts", 0.0)) >= BASELINE_STRIDE_S:
                    self._last_axis_ts = now_s
                    self._ensure()
                    self._store.conn.execute(
                        "INSERT INTO character_axis_sample (symbol, ts_epoch,"
                        " efficiency, vol_ratio, close_capture, realised_vol_cc,"
                        " realised_vol_parkinson, adx, atr_normalized, price)"
                        " VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (self.symbol, now_s, p, vr, cap, cc, pk,
                         _f(getattr(ctx.get("trend"), "primary_adx", None)),
                         _f(getattr(ctx.get("vol"), "atr_normalized", None)),
                         _f(ctx.get("price"))))
                    self._store.commit()
        except Exception as exc:                                # noqa: BLE001
            logger.debug("axis sample: %s", exc)

        if not qualifies_to_displace(self._state, challenger, p, vr):
            return 0

        now = time.time()
        try:
            self._ensure()
            # Close the outgoing row so `held_s` is a fact, not a computation.
            if self._row_id is not None:
                self._store.conn.execute(
                    "UPDATE character_ledger SET exited_ts=?, held_s=?"
                    " WHERE id=?", (now, now - self._since, self._row_id))
            cur = self._store.conn.execute(
                "INSERT INTO character_ledger (symbol, character, entered_ts,"
                " from_character, persistence, vol_ratio, realised_vol_cc,"
                " realised_vol_parkinson, adx, atr_normalized, gap_pct,"
                " gap_class, price) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (self.symbol, challenger, now, self._state, p, vr, cc, pk,
                 _f(getattr(ctx.get("trend"), "primary_adx", None)),
                 _f(getattr(ctx.get("vol"), "atr_normalized", None)),
                 _f((ctx.get("gap") or {}).get("gap_pct")),
                 (ctx.get("gap") or {}).get("gap_class"),
                 _f(ctx.get("price"))))
            self._row_id = cur.lastrowid
            self._store.commit()
        except Exception as exc:                                # noqa: BLE001
            logger.debug("character write: %s", exc)
            return 0

        held = (now - self._since) / 60.0 if self._since else 0.0
        if self._state:
            logger.info("[character] %s -> %s after %.0f min "
                        "(persistence %.2f, vol %.2fx)", self._state,
                        challenger, held, p if p is not None else -1,
                        vr if vr is not None else -1)
        else:
            logger.info("[character] %s (persistence %.2f, vol %.2fx)",
                        challenger, p if p is not None else -1,
                        vr if vr is not None else -1)
        self._state, self._since = challenger, now
        return 1
