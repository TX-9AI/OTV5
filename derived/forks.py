"""
derived/forks.py  v4.6
v4.6  2026-10-24  CD.2 — every row carries bar_ts_ms, the start of the last CLOSED bar of the frame the builder was
      handed (its market time). anchors.fork_row() serves a row only while that bar is the frame's latest closed bar
      (one bar of grace), so a dead or seeded fork is never reported as the current one.
v4.5  2026-09-23  OTV4TEST r117 — THE 1h FORK IS BUILT FROM CLOSED HOURLY BARS ONLY.
      The operator, 2026-09-23: "Closed hourly. I like that." The 1h frame
      carried its still-forming bar, whose close moves every minute, and the
      builder's anchor search and containment read it — so INSIDE one hour
      the fork flipped between two first anchors (fork_series, 09-23 ET: p0
      732.09 at 14:05 -> 727.82 at 14:10; 732.09 from 15:03, then 727.82 at
      15:35 inside the same hour). The forming 1h bar (now <
      its start + 60 min) is now dropped before the build and before the ATR.
      Positions are unchanged by dropping the tail, so `last_idx` and
      `last_bar_start` still name the forming bar and r116's walk of the rail
      to the current minute still applies. The 1d frame is NOT changed here —
      the ruling was about the hourly fork.
v4.4  2026-09-23  OTV4TEST r116 — THE BUILDER'S CONTAINMENT TEST IS THE ONLY JUDGE.
      The operator, asked whether a killed fork the builder serves again argues
      for its persistence: "I agree. If the channel gets disrespected briefly but
      persists it still serving us somewhat of a guide." v4.3 killed a fork on a
      single 1m rail breach and then REFUSED the builder's own rebuild of it —
      two definitions of a fork's life, the stricter overruling the builder
      (measured: the builder kept producing the 14:42-breached fork). The breach-
      kill, the dead-identity set, the refusal and the restart restore are gone:
      a fork lives while this engine can build it. A 1m poke beyond a rail is a
      touch. And `last_bar_start` is recorded so readers walk a rail to the
      current minute (the rails were read at the forming hour's START, a
      staircase: median $0.06/hour of slope, worst $0.69).
v4.3  2026-09-23  OTV4TEST r115 — THE BUILDER DECIDES A FORK'S DEATH. Operator: "I wanna
      make sure that the invalidation of the fork comes from the fork builder's
      engine, not from a strategy-plan" / "it's gone when the engine says it's
      gone, not when a strategy says it's gone". r114 put the breach judgement in
      the LEVEL engine, which kept a private dead-set while this engine kept
      serving the fork to every other reader. Now `_judge_rails` runs here on
      every closed 1m bar: a rail BREACHED (level_rules: 1m close beyond, next
      open beyond) adds the identity to `_dead`, clears `last_forks[tf]` so NO
      consumer receives it, and writes an `INVALIDATED:` row to fork_series;
      the builder's rebuild of that same identity is refused every run after
      (reason INVALIDATED_IDENTITY), and a restart restores the dead set from
      those rows (§22). `fork_identity()` is the ONE identity definition — the
      anchor prices, never `idx`.
v4.2  2026-09-12  OTV4TEST r15 — a failed build clears `last_forks[tf]`/`last_idx[tf]`
      (ported from mainline r364): the level map dies with the fork.
v4.1  2026-09-08  OTV4TEST r5 — the engine KEEPS the last built fork per frame
      (`last_forks[tf]`) and the frame's current bar index (`last_idx[tf]`) so
      derived/levels can ask where a tine IS at the bar — the tines are moving
      levels (time + slope) and the level engine must not recompute the fork.
Owns `fork_series`. Tier 2 — regressive, and dies on restart today.

v4.0  2026-08-22  See docs/DERIVED_STORES.md.

The pitchfork reaches back 60-80 bars to find its anchors and currently lives
in a **process-resident cache** (`pitchfork_observer._cache`). Three costs, all
of which the r59 investigation ran straight into:

  · It dies on every deploy. The 10:39 restart on 2026-08-21 is the same class
    of loss that wiped confirmed ORB setups on four boxes.
  · Nobody can see what it decided. When the condor said "rails=absent" all day
    there was no way to ask what fork it had at 10:15 — the diagnosis had to be
    reconstructed synthetically in a sandbox, which is why it was WRONG TWICE.
  · Rejections are computed and thrown away.

🔴 THE REJECTION REASONS ARE THE POINT. `pitchfork.py` names six —
FRAME_TOO_SHORT, NOT_ANCHOR_TF, NO_ATR, NO_CONTAINED_WINDOW, RECENCY,
SEPARATION — and **not one reaches storage or a log.** "No usable daily
pitchfork (rails=absent)" was a single undifferentiated message covering six
different problems, printed on every box on every tick of a zero-trade session.

⚠️ A REJECTION IS A ROW, NOT A SKIPPED WRITE. `built=0` with the reason and the
scan depth. A table that only records successes cannot answer "why not", which
is the question actually being asked when the condor stands down.

⚠️ CONDOR ANCHOR IS 1h — operator ruling 2026-08-22. The daily fork demands an
excursion between anchors that a single session rarely meets, so gating on it
produces a permanent no-trade rather than a guardrail. Both frames are recorded
here regardless; the ruling decides what the CONDOR reads, not what we keep.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from derived.base import DerivedEngine

logger = logging.getLogger(__name__)

# Both anchor frames are recorded. Keeping the one the condor does not read
# costs almost nothing and means a later ruling change has history behind it.
FRAMES = ("1h", "1d")


def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def fork_identity(fork) -> Optional[tuple]:
    """THE ONE DEFINITION OF A FORK'S IDENTITY — its three anchor PRICES.
    Never the anchors' `idx`: that is a position in the rolling frame and shifts
    by one every bar (one fork, 09-09..09-14, wore 17 idx-keys). The level engine
    and derived/fork_projection call this; nobody keeps a private copy."""
    try:
        return tuple(round(float(getattr(fork, a).price), 4) for a in ("p0", "p1", "p2"))
    except Exception:                                           # noqa: BLE001
        return None


# minutes per frame bar — the rail's slope is per BAR, so a rail is walked back
# along it by (minutes / TF_MINUTES) of a bar to find where it stood at a minute
TF_MINUTES = {"15m": 15, "1h": 60, "1d": 390}

# v4.5 — frames whose still-forming bar is dropped before the build (the
# operator's "closed hourly"). 1d is deliberately absent: not ruled.
CLOSED_BARS_ONLY = ("1h",)


def closed_frame(df, tf: str, now: float):
    """The frame the builder is handed: for a CLOSED_BARS_ONLY frame, without
    its newest bar while that bar is still forming (now < start + one bar).
    Anything that cannot be read is handed through unchanged."""
    if tf not in CLOSED_BARS_ONLY or df is None or len(df) == 0:
        return df
    try:
        start = float(df.index[-1].timestamp())
    except Exception:                                           # noqa: BLE001
        return df
    if now < start + TF_MINUTES[tf] * 60.0:
        return df.iloc[:-1]
    return df


class ForkEngine(DerivedEngine):
    name = "forks"
    table = "fork_series"
    # The scan is the expensive part of this file; 60s is far finer than the
    # rate at which a 1h fork's geometry can meaningfully change.
    min_interval_s = 60.0

    def __init__(self, store=None, symbol: str = ""):
        super().__init__(store)
        self.symbol = symbol
        self.last_forks: dict = {}      # tf -> Pitchfork (v4.1)
        self.last_idx: dict = {}        # tf -> current bar index in that frame
        # v4.4 — the start (epoch s) of the frame's newest, still-forming bar, so
        # a reader can walk a rail to the CURRENT minute instead of the bar start
        self.last_bar_start: dict = {}  # tf -> epoch seconds

    def derive(self, ctx: dict) -> int:
        store = self._store
        if store is None:
            return 0
        sym = self.symbol or ctx.get("symbol") or ""
        data = ctx.get("data") or {}
        if not sym or not data:
            return 0

        from analysis import pitchfork as pf

        now = time.time()
        rows = []
        for tf in FRAMES:
            df = data.get(tf)
            if df is None or getattr(df, "empty", True):
                # ⚠️ RECORDED, NOT SKIPPED. "the frame was not there" is a
                # DIFFERENT failure from "the geometry did not qualify", and
                # on 2026-08-21 the 1d frame was absent from the warehouse
                # entirely — a fact that took hours to establish because
                # nothing wrote it down.
                rows.append((sym, tf, now, 0, "NO_FRAME", 0, None,
                             None, None, None, None, None, None, None, None,
                             None, None, None, None, None, None, None))
                continue
            # v4.5 — the builder sees CLOSED hourly bars only; `df` keeps the
            # forming bar so last_idx/last_bar_start below still name it
            bdf = closed_frame(df, tf, now)
            try:                                                # CD.2: the frame's last closed bar
                bar_ts_ms = int(float(bdf.index[-1].timestamp()) * 1000) if bdf is not None and len(bdf) else None
            except Exception:                                   # noqa: BLE001
                bar_ts_ms = None
            try:
                atr = float((bdf["high"] - bdf["low"]).tail(20).mean())
            except Exception:                                   # noqa: BLE001
                atr = 0.0
            fork = None
            try:
                fork = pf.build_fork_contained(sym, bdf, tf, atr)
            except Exception as exc:                            # noqa: BLE001
                logger.debug("fork build raised for %s %s: %s", sym, tf, exc)
            # r15 (mainline r364's rule): a failed build CLEARS the held fork, so a
            # dead structure cannot be served one tick later — "if the fork stops
            # emitting, then the map has to go with it… out of sight, out of mind."
            reason = None
            try:
                reason = pf.last_reject_reason()
                depth = pf.last_scan_depth()
            except Exception:                                   # noqa: BLE001
                depth = 0
            # 🔴 v4.4 — THE BUILDER'S CONTAINMENT TEST IS THE ONLY JUDGE OF A FORK'S
            # LIFE (operator, 2026-09-23: "If the channel gets disrespected briefly
            # but persists it still serving us somewhat of a guide"). What it builds
            # is served; when it cannot build, the fork is gone. v4.3's separate 1m
            # breach-kill is removed: it overruled this very test.
            if fork is not None:
                self.last_forks[tf] = fork
                self.last_idx[tf] = len(df) - 1
                try:
                    self.last_bar_start[tf] = float(df.index[-1].timestamp())
                except Exception:                               # noqa: BLE001
                    self.last_bar_start.pop(tf, None)
            else:
                self.last_forks.pop(tf, None)
                self.last_idx.pop(tf, None)
                self.last_bar_start.pop(tf, None)

            if fork is None:
                rows.append((sym, tf, now, 0, reason or "UNKNOWN", depth,
                             None, None, None, None, None, None, None,
                             None, None, None, None, None, None, None, None, bar_ts_ms))
                continue

            # Built. Record the anchors so the fork can be REDRAWN later from
            # the row alone — a fork you cannot reconstruct is a number, not a
            # measurement.
            # ⚠️ FIELD NAMES READ FROM THE DATACLASS, NOT ASSUMED. Fork carries
            # p0/p1/p2 as named Pivots (idx, price, kind, k, timeframe) and has
            # NO containment/span/upper/median/lower attributes — the first
            # draft of this file invented all five. Containment and span live
            # inside `filters_passed` as tags like ("CONTAINMENT_0.96",
            # "SPAN_71"), so they are parsed out rather than read.
            def pv(pt, attr):
                try:
                    return _f(getattr(pt, attr))
                except Exception:                               # noqa: BLE001
                    return None
            contain, span = None, None
            for tag in (getattr(fork, "filters_passed", None) or ()):
                t = str(tag)
                if t.startswith("CONTAINMENT_"):
                    contain = _f(t.split("_", 1)[1])
                elif t.startswith("SPAN_"):
                    try:
                        span = int(t.split("_", 1)[1])
                    except (TypeError, ValueError):
                        span = None
            rows.append((
                sym, tf, now, 1, None, depth,
                getattr(fork, "direction", None),
                pv(getattr(fork, "p0", None), "idx"),
                pv(getattr(fork, "p0", None), "price"),
                pv(getattr(fork, "p1", None), "idx"),
                pv(getattr(fork, "p1", None), "price"),
                pv(getattr(fork, "p2", None), "idx"),
                pv(getattr(fork, "p2", None), "price"),
                _f(getattr(fork, "origin_idx", None)),
                _f(getattr(fork, "origin_price", None)),
                _f(getattr(fork, "slope", None)),
                contain, span,
                # The rails themselves are a projection at a given bar index,
                # not stored state — left NULL here and computed on read from
                # origin + slope, which the row fully determines.
                None, None, None,
                bar_ts_ms,                                      # CD.2
            ))
        return store.append_forks(rows)

