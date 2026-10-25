"""
derived/level_book.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.4  2026-10-18  OTV4TEST r300 (LVL.20) — THE RTH BLOCK ENDS AT THE DAY'S BELL. _in_rth, et_blocks and blocks_for carried a
      fixed 16:00; on 2026-11-27 (13:00 close) the 13:00-16:00 bars would have been RTH to the book: session extremes,
      spike detection and the opening-range retirement all read the wrong block. One helper, _bell_minutes(d), reads
      utils/market_calendar.close_time. Audit 2026-10-18 H6 (the feed's own fixed bell is mainline-shared: 1-REPORTER).
THE ONE LEVEL BOOK: closed session extremes, walked by recency, grouped into
zones, judged HELD / BREACHED on the 1-minute tape by `derived/level_rules`.

v1.3  2026-10-01  OTV4TEST FLIP.1 — A LONE LEVEL ACCEPTED THROUGH FLIPS AND WAITS FOR ITS
      RETEST; RECORD-ONLY. The operator, 2026-10-01: *"record genuinely broken
      levels as future retest candidates ... when it's broken through, it needs
      to flip"*. His rulings that morning, each in the code: (1) broken = the
      existing BREACHED; (2) the record's form is ours "as long as the flip is
      recorded"; (3) a ZONE never flips — it retires as before (*"A zone is
      similar to a fair value Gap it's not going to hold"*); (4) a flipped
      level broken AGAIN retires (*"If a level isn't respected, then it's not a
      level"*); (5) the opening-range TRAVERSED rule applies to it; (6) the
      rail lock is untouched. On BREACHED of a one-member zone the original
      retires exactly as before AND `Book.flipped` gains `<SYM>:flip:<new
      side>:<price>`, judged ALONE by its own `level_rules.Episode` from the
      NEXT candle; every event it produces carries `flip: True`. Flipped levels
      are NOT in `live`, so current_zones() and board() are unchanged: nothing
      trades a flip until the operator rules a plan reads one.
      tests/check_level_flip.py F1-F7.
v1.2  2026-09-23  OTV4TEST r111 — TWO OPERATOR RULINGS, BOTH IN THE BOOK.
      (1) A LONE PRINT IS NOT A SESSION EXTREME ("1. Yes"): `spike_extremes`
      is ON by default at SPIKE_REJECT_USD $1.00 and judges OUTSIDE RTH ONLY —
      inside RTH the same shape measured as real fast flushes. 09-21's 725.75
      (08:25 ET, one print 2.45 under a market at 728.2, absent from his chart)
      leaves the book; Monday's pre-market low is 726.70. The overnight block
      STAYS ("2. Keep"). (2) "ANY LEVEL THAT'S INSIDE TODAY'S 5-MIN OPENING
      RANGE IS AUTOMATICALLY RETIRED": at the first 1m candle at/after 09:35
      every live level inside the 09:30-09:34 range retires TRAVERSED
      (`Book.traversed`) — r5's rule, which the v1.1 book path had dropped. On
      the real tape since 08-10 it fired 7 times and retired 12 levels. K13,
      K14. ⚠️ r110 LANDED WITHOUT THESE: its archive was parked before the
      rulings and never re-cut — found by the post-land marker check, before
      any bake, so no running process ever held r110's v1.1.
v1.1  2026-09-23  SESSIONS ON THE ET CLOCK, EXTREMES FROM THE MINUTE. v1.0 built
      blocks from HOURLY candles on the hour, so pre-market ended 09:00 and the
      09:00-09:30 half hour belonged to RTH. On 09-18 the real pre-market low
      (717.10, 09:27 ET — the operator's chart) fell into RTH, under a lower
      RTH low, and NEVER BECAME A LEVEL. `closed_sessions_et`: overnight
      20:00-04:00, pre-market 04:00-09:30, RTH 09:30-16:00, after-hours
      16:00-20:00, DST-safe; candidates are every 1m candle in the block plus
      every hourly candle WHOLLY inside it (an aggregate carries the true
      extreme of an hour whose minutes the seeded tape is missing); `build()`
      judges any hour with no 1m candle on its hourly candle. And
      `spike_extremes` + `spike_reject`: a lone-print filter, OFF (0.0) until
      the operator rules — the 09-18 08:14 candle printed 716.38 once, 1.80
      under the market, on the vendor's tape on BOTH QQQ boxes, and his chart
      does not show it. K11 (red on v1.0 through build()), K12.
v1.0  2026-09-23  OTV4TEST LVL.15 step 2 (unlanded WIP, built for review).

🔴 THE OPERATOR'S DEFINITION OF A LEVEL, FINAL (2026-09-22): *"a level is a
place where there's orders resting because it was outside of the extreme of a
session high or low. Starting most recently and working backwards."* And:
*"I don't give a rat's ass if it's New York or Asia or London — just get the
levels, the numbers."* A session STILL FORMING is not a level: a level becomes
live when its session CLOSES.

WHAT THIS REPLACES, AND WHY IT IS A NEW FILE. `derived/levels.py` (1,334 lines)
and `derived/level_map.py` (379) grew by patch over r3..r106: three breach
definitions, depth tiers, touch counts, session labels in identity, a ledger
reconciled against the tape, and `level_map` importing the OLD mapper for its
session clock — the single import that kept two level systems alive. The
operator: *"Anything that has the word level in it needs to be erased ...
Literally start over."* This file imports neither.

REUSED, NOT REINVENTED — the parts that were measured and well built, COPIED
here so the old modules can be deleted without taking them along:
  · the HOURLY tape as the level source (r36: an hourly high/low is the true
    extreme of its hour; 1h reaches 60 days), RTH + `_EXT` merged (r29);
  · the zone width = the instrument's own median larger-side hourly wick,
    recomputed, never stored (r39: the ratio replicates across QQQ/MU/SPX, a
    percentage of spot does not);
  · zones merged to a FIXED POINT (r39: one pass printed an overlapping
    partition);
  · the recency walk (r29): newest first from the anchor, each older rung only
    if FURTHER out — at ZONE granularity, cluster first then walk (r39).

WHAT IS NEW, EACH BY RULING:
  · FOUR contiguous session blocks declared from the RTH boundary alone, so they
    meet by construction in either DST offset — 00->08Z, 08Z->RTH open, RTH,
    RTH close->24Z. The last is AFTER-HOURS (16:00-20:00 ET), which had never
    been a block (r107 patch finding); the EST 08:00-09:00 ET hole is gone.
  · NO LABELS: identity is side + price. Two sessions printing one price are one
    pool of resting orders, one level; the newest formation dates it.
  · HELD / BREACHED come ONLY from `level_rules` (one definition, 1m candles).
  · A ZONE stays live until its FAR edge is accepted; a breach retires every
    member (r39 kept); a close inside a zone is not HELD (ruling b, 09-23).
  · No grading, depth, touch counts, freshness or age gates.

⚠️ THE ONE PLACE THE HOUR STILL JUDGES, STATED RATHER THAN HIDDEN. A level
formed before the 1m tape begins is judged on HOURLY candles until the 1m tape
starts. Hourly close-beyond + next hourly open-beyond IMPLIES the 1m rule, but
the converse fails (LVL.14: 39% of breaches missed or late), so such a level can
be alive here when the minute says dead. Every event carries `judged_on`, and
`Book.hourly_judged` counts the levels that depended on it. r108 keeps 1m for 60
days and the 2026-09-23 backfill reaches 08-24, so this shrinks to nothing as
the minute tape fills the hourly window.

PURE: no store is written, no clock is read; the same tapes give the same book.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from derived import level_rules as R

Bar = Tuple[int, float, float, float, float]      # (ts_ms, open, high, low, close)
HOUR_MS, MIN_MS = 3_600_000, 60_000
_ET = ZoneInfo("America/New_York")
_OVERNIGHT_SPLIT_UTC = 8                        # 04:00 ET in EDT, 03:00 in EST
# 🔴 OPERATOR'S RULING 2026-09-23 ("1. Yes"): a LONE PRINT is not a session
# extreme. The vendor's tape carries single ticks the market never traded at —
# 09-18 08:14 ET 716.38 (market ~718.2) and 09-21 08:25 ET 725.75 (market
# ~728.2), on BOTH QQQ boxes, absent from his chart — and the book made each a
# session low. A 1m extreme its own close AND both neighbours reject by more
# than this is dropped, OUTSIDE RTH ONLY: inside RTH the same shape measured as
# real fast flushes (07-10 10:33 717.00 closing 720.71), which are sweeps.
SPIKE_REJECT_USD = 1.00


# ── the tape ──────────────────────────────────────────────────────────────────
def load_bars(db_path: str, symbol: str, interval: str) -> Optional[List[Bar]]:
    """Every `interval` bar for `symbol`, RTH (`SYM`) and extended (`SYM_EXT`)
    merged and de-duplicated on the stamp. Read-only. None when the store is
    unreadable or empty — never an empty list that reads as "no levels"."""
    try:
        c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0)
    except Exception:                                           # noqa: BLE001
        return None
    try:
        rows = c.execute(
            "SELECT ts_epoch_ms, open, high, low, close FROM candles"
            " WHERE symbol IN (?, ?) AND interval=? AND open > 0 AND close > 0"
            " ORDER BY ts_epoch_ms", (symbol, f"{symbol}_EXT", interval)).fetchall()
    except Exception:                                           # noqa: BLE001
        return None
    finally:
        c.close()
    out: List[Bar] = []
    last = None
    for ts, o, h, l, cl in rows:
        if ts == last:
            continue                      # RTH and EXT stamp the same bar identically (r29)
        out.append((int(ts), float(o), float(h), float(l), float(cl)))
        last = ts
    return out or None


# ── sessions: four contiguous blocks, one declared boundary ───────────────────
def blocks_for(d) -> Tuple[Tuple[int, int], ...]:
    """The day's session blocks as (start_hour_utc, end_hour_utc), covering
    00->24Z with no gap in either DST offset. Only the RTH hours are a fact;
    every other block is the span between its neighbours."""
    off = datetime(d.year, d.month, d.day, 12, tzinfo=_ET).utcoffset()
    r0 = 13 if off == timedelta(hours=-4) else 14
    # r300 (LVL.20): the RTH block ends at the day's BELL, not a fixed 16:00 - on a 13:00
    # close (2026-11-27) the hours 13:00-16:00 ET are after-hours. Hour-granular like r0.
    r1 = r0 + -(-(_bell_minutes(d) - (9 * 60 + 30)) // 60)      # ceil of the RTH span in hours
    return ((0, _OVERNIGHT_SPLIT_UTC), (_OVERNIGHT_SPLIT_UTC, r0), (r0, r1), (r1, 24))


def _bell_minutes(d) -> int:
    """r300 — the session's closing bell on ET day `d`, in minutes after midnight: the listed
    early close (utils/market_calendar.close_time), else 16:00. Never raises; unreadable = 16:00."""
    try:
        from utils import market_calendar as _mc
        b = _mc.close_time(d)
        return b.hour * 60 + b.minute
    except Exception:                                           # noqa: BLE001
        return 16 * 60


def et_blocks(d) -> List[Tuple[int, int]]:
    """The four session blocks that END on ET calendar day `d`, on the ET wall
    clock (DST-safe): overnight 20:00(d-1)->04:00, pre-market 04:00->09:30,
    RTH 09:30->the bell (16:00, 13:00 on a listed half day - r300), after-hours
    the bell->20:00. Epoch ms, contiguous."""
    def at(day, hh, mm):
        return int(datetime(day.year, day.month, day.day, hh, mm, tzinfo=_ET).timestamp() * 1000)
    prev = d - timedelta(days=1)
    bh, bm = divmod(_bell_minutes(d), 60)                        # r300: the day's bell, 13:00 on a half day
    return [(at(prev, 20, 0), at(d, 4, 0)), (at(d, 4, 0), at(d, 9, 30)),
            (at(d, 9, 30), at(d, bh, bm)), (at(d, bh, bm), at(d, 20, 0))]


def _in_rth(ts_ms: int) -> bool:
    t = datetime.fromtimestamp(ts_ms / 1000, _ET)
    return (9 * 60 + 30) <= (t.hour * 60 + t.minute) < _bell_minutes(t.date())    # r300: the day's bell


def spike_extremes(m1: Sequence[Bar], min_reject: float) -> Dict[int, Tuple[bool, bool]]:
    """1m candles OUTSIDE RTH whose LOW (or HIGH) its own close AND both
    neighbours reject by more than `min_reject` — a lone print the market never
    traded at. Returns {ts: (low_is_spike, high_is_spike)}. `min_reject <= 0`
    disables it. RTH candles are never judged (ruling 2026-09-23)."""
    out: Dict[int, Tuple[bool, bool]] = {}
    if min_reject <= 0:
        return out
    for i in range(1, len(m1) - 1):
        p, b, n = m1[i - 1], m1[i], m1[i + 1]
        if _in_rth(b[0]):
            continue                      # inside RTH the shape is a real flush
        if n[0] - p[0] > 2 * MIN_MS:
            continue                      # neighbours not adjacent: cannot judge
        lo = b[4] - b[3] > min_reject and min(p[3], n[3]) - b[3] > min_reject
        hi = b[2] - b[4] > min_reject and b[2] - max(p[2], n[2]) > min_reject
        if lo or hi:
            out[b[0]] = (lo, hi)
    return out


def closed_sessions_et(h1: Sequence[Bar], m1: Sequence[Bar], now_ms: Optional[int] = None,
                       spike_reject: float = SPIKE_REJECT_USD) -> List[dict]:
    """Every CLOSED block on the ET clock. Candidates are every 1m candle in the
    block PLUS every hourly candle lying wholly inside it — an hourly candle is
    an aggregate, so it carries the true extreme of an hour whose minutes are
    missing. A straddling hourly candle (09:00-10:00) is excluded. Extremes a
    spike filter rejects are removed from both, by price."""
    import bisect
    m1 = list(m1 or [])
    if not h1 and not m1:
        return []
    first = min(x[0][0] for x in (h1, m1) if x)
    last = max(x[-1][0] for x in (h1, m1) if x)
    now = max(last + MIN_MS, int(now_ms or 0))
    spikes = spike_extremes(m1, spike_reject)
    bad_lo = {round(m[3], 4) for m in m1 if spikes.get(m[0], (0, 0))[0]}
    bad_hi = {round(m[2], 4) for m in m1 if spikes.get(m[0], (0, 0))[1]}
    days = sorted({datetime.fromtimestamp(ts / 1000, _ET).date() for ts, *_ in (list(h1) + m1)})
    days.append(days[-1] + timedelta(days=1))
    m_ts = [b[0] for b in m1]
    h_ts = [b[0] for b in h1]
    out = []
    for d in days:
        for s, e in et_blocks(d):
            if s < first or e > now:
                continue
            ms = m1[bisect.bisect_left(m_ts, s):bisect.bisect_left(m_ts, e)]
            hs = [b for b in h1[bisect.bisect_left(h_ts, s):bisect.bisect_left(h_ts, e)]
                  if b[0] + HOUR_MS <= e]
            his = ([(b[2], b[0]) for b in ms if not spikes.get(b[0], (0, 0))[1]]
                   + [(b[2], b[0]) for b in hs if round(b[2], 4) not in bad_hi])
            los = ([(b[3], b[0]) for b in ms if not spikes.get(b[0], (0, 0))[0]]
                   + [(b[3], b[0]) for b in hs if round(b[3], 4) not in bad_lo])
            if not his or not los:
                continue                  # no tape (weekend, holiday)
            # ties: the 1m stamp wins over the hour it sits in (it is listed first
            # and is the later/equal stamp only when it is the true minute)
            hi = max(his, key=lambda x: x[0])
            lo = min(los, key=lambda x: x[0])
            out.append({"start": s, "end": e, "high": hi[0], "high_ts": hi[1],
                        "low": lo[0], "low_ts": lo[1]})
    out.sort(key=lambda z: z["start"])
    return out


def closed_sessions(h1: Sequence[Bar], now_ms: Optional[int] = None) -> List[dict]:
    """Every block the hourly tape FULLY covers and that has CLOSED, oldest
    first: {start, end, high, high_ts, low, low_ts} (epoch ms)."""
    if not h1:
        return []
    first, last = h1[0][0], h1[-1][0]
    now = max(last + HOUR_MS, int(now_ms or 0))
    days = sorted({datetime.fromtimestamp(ts / 1000, timezone.utc).date() for ts, *_ in h1})
    out = []
    for d in days:
        day0 = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)
        for a, b in blocks_for(d):
            s, e = day0 + a * HOUR_MS, day0 + b * HOUR_MS
            if s < first:
                continue                  # left-truncated: its extreme is unprovable
            if e > now:
                continue                  # 🔴 still forming — not a level (ruling)
            bars = [x for x in h1 if s <= x[0] < e]
            if not bars:
                continue                  # no tape (weekend, holiday)
            hi = max(bars, key=lambda x: x[2])
            lo = min(bars, key=lambda x: x[3])
            out.append({"start": s, "end": e, "high": hi[2], "high_ts": hi[0],
                        "low": lo[3], "low_ts": lo[0]})
    out.sort(key=lambda z: z["start"])
    return out


# ── zones (r39, copied) ───────────────────────────────────────────────────────
def zone_width(h1: Sequence[Bar]) -> Optional[float]:
    """The instrument's own MEDIAN larger-side hourly wick. None when no tape."""
    wicks = []
    for _ts, o, h, l, c in h1:
        w = max(h - max(o, c), min(o, c) - l)
        if w >= 0:
            wicks.append(w)
    if not wicks:
        return None
    w = float(median(wicks))
    return w if w > 0 else None


def zones(levels: Sequence["Level"], width: Optional[float]) -> List[dict]:
    """Cluster levels into zones {lo, hi, members}, merged to a FIXED POINT so
    the partition cannot depend on arrival order. No width -> one per level."""
    zs = [{"lo": l.price, "hi": l.price, "members": [l]} for l in levels]
    if not width or width <= 0:
        return sorted(zs, key=lambda z: z["lo"])
    changed = True
    while changed:
        changed = False
        zs.sort(key=lambda z: z["lo"])
        out: List[dict] = []
        for z in zs:
            if out and z["lo"] - out[-1]["hi"] <= width:
                out[-1]["hi"] = max(out[-1]["hi"], z["hi"])
                out[-1]["members"] += z["members"]
                changed = True
            else:
                out.append(z)
        zs = out
    return zs


# ── the book ──────────────────────────────────────────────────────────────────
@dataclass
class Level:
    level_id: str
    side: str                 # resistance (a session high) / support (a session low)
    price: float
    formed_ts: int            # the bar the extreme printed on — the recency key
    live_from: int            # its session's END: a forming session is not a level


@dataclass
class Book:
    symbol: str
    width: Optional[float]
    live: Dict[str, Level] = field(default_factory=dict)
    dead: Dict[str, int] = field(default_factory=dict)        # level_id -> breach ts
    traversed: set = field(default_factory=set)               # level_ids retired INSIDE an opening range
    events: List[dict] = field(default_factory=list)
    hourly_judged: int = 0
    as_of: Optional[int] = None
    # v1.3 (FLIP.1) — a LONE level accepted through flips side and waits for its
    # retest. Kept OUT of `live`, so current_zones() and every board are exactly
    # what they were: RECORD-ONLY until the operator rules a plan reads them.
    flipped: Dict[str, Level] = field(default_factory=dict)  # flip_id -> the flipped level (live)
    flip_of: Dict[str, str] = field(default_factory=dict)    # flip_id -> the level_id it came from
    flip_dead: Dict[str, int] = field(default_factory=dict)  # flip_id -> retire ts (2nd break / traversed)

    def current_zones(self) -> List[dict]:
        return zones(list(self.live.values()), self.width)


def level_id(symbol: str, side: str, price: float) -> str:
    """Side + price. NO SESSION LABEL — ruled irrelevant (2026-09-22)."""
    return f"{symbol}:{side}:{price:.2f}"


def flip_id(symbol: str, side: str, price: float) -> str:
    """A flipped level's identity: its NEW side, its price, marked `flip` so it
    can never collide with a session extreme printed at the same price."""
    return f"{symbol}:flip:{side}:{price:.2f}"


def opposite(side: str) -> str:
    return R.SUPPORT if side == R.RESISTANCE else R.RESISTANCE


def _levels_from(symbol: str, sessions: Sequence[dict]) -> List[Level]:
    by_id: Dict[str, Level] = {}
    for s in sessions:
        for side, px, ts in ((R.RESISTANCE, s["high"], s["high_ts"]),
                             (R.SUPPORT, s["low"], s["low_ts"])):
            lid = level_id(symbol, side, px)
            lv = Level(lid, side, float(px), int(ts), int(s["end"]))
            prev = by_id.get(lid)
            # one price, one pool: the NEWEST formation dates it (recency orders)
            if prev is None or lv.formed_ts > prev.formed_ts:
                by_id[lid] = lv
    return sorted(by_id.values(), key=lambda l: l.live_from)


def _zone_side(members: Sequence[Level], ref_price: float) -> Optional[str]:
    sides = {m.side for m in members}
    if len(sides) == 1:
        return sides.pop()
    lo, hi = min(m.price for m in members), max(m.price for m in members)
    if ref_price < lo:
        return R.RESISTANCE
    if ref_price > hi:
        return R.SUPPORT
    return None                       # mixed zone with price inside it: not judged yet


def build(symbol: str, h1: Sequence[Bar], m1: Sequence[Bar],
          now_ms: Optional[int] = None, spike_reject: float = SPIKE_REJECT_USD) -> Book:
    """Replay the tape in time order and return the book as of the last candle.

    Sessions are the ET-clock blocks (`closed_sessions_et`). Every hour that has
    1m candles is judged on them; an hour with NO 1m candle is judged on its
    hourly candle (judged_on '1h' — see the header)."""
    width = zone_width(h1)
    book = Book(symbol=symbol, width=width)
    levels = _levels_from(symbol, closed_sessions_et(h1, m1 or [], now_ms, spike_reject))
    covered = {b[0] // HOUR_MS for b in (m1 or [])}
    tape = sorted([("1h", b) for b in h1 if b[0] // HOUR_MS not in covered]
                  + [("1m", b) for b in (m1 or [])], key=lambda x: x[1][0])
    # 🔴 OPERATOR'S RULING 2026-09-23: "any level that's inside today's 5-min
    # opening range is automatically retired" (r5's rule, carried onto the book).
    # The range is the 09:30-09:34 minutes — the same five minutes as the 09:30
    # 5m candle the ORB arms on. At the first 1m candle at/after 09:35 every LIVE
    # level whose price lies inside [low, high] retires TRAVERSED: price has been
    # through it. Applied on every day of the replay, so today is no special case.
    or_rng: Dict[object, List[float]] = {}
    or_done: set = set()
    pending = list(levels)                 # not yet live, in live_from order
    episodes: Dict[FrozenSet[str], R.Episode] = {}
    flip_eps: Dict[str, R.Episode] = {}                    # FLIP.1 — one per flipped level
    zone_list: List[dict] = []
    dirty = True
    hourly_touched = set()
    for tf, bar in tape:
        ts = bar[0]
        if tf == "1m":
            t_et = datetime.fromtimestamp(ts / 1000, _ET)
            day, hm = t_et.date(), (t_et.hour, t_et.minute)
            if (9, 30) <= hm < (9, 35):
                r = or_rng.setdefault(day, [bar[3], bar[2]])
                r[0], r[1] = min(r[0], bar[3]), max(r[1], bar[2])
            elif hm >= (9, 35) and day in or_rng and day not in or_done:
                or_done.add(day)
                lo_, hi_ = or_rng[day]
                gone = [lid for lid, lv in book.live.items() if lo_ <= lv.price <= hi_]
                for lid in gone:
                    book.dead[lid] = ts
                    book.traversed.add(lid)
                    book.live.pop(lid, None)
                if gone:
                    book.events.append({"event": "TRAVERSED", "ts": ts, "judged_on": "1m",
                                        "side": None, "near": lo_, "far": hi_,
                                        "level_ids": sorted(gone), "prices": sorted(
                                            float(x.rsplit(":", 1)[1]) for x in gone)})
                    dirty = True
                # FLIP.1 ruling 5 ("Yes same concept"): a flipped level inside
                # the opening range retires TRAVERSED too.
                fgone = [fid for fid, fl in book.flipped.items() if lo_ <= fl.price <= hi_]
                for fid in fgone:
                    book.flip_dead[fid] = ts
                    book.traversed.add(fid)
                    book.flipped.pop(fid, None)
                    flip_eps.pop(fid, None)
                if fgone:
                    book.events.append({"event": "TRAVERSED", "ts": ts, "judged_on": "1m",
                                        "side": None, "near": lo_, "far": hi_, "flip": True,
                                        "level_ids": sorted(fgone), "prices": sorted(
                                            float(x.rsplit(":", 1)[1]) for x in fgone)})
        # FLIP.1 — the flipped levels, each judged ALONE on its new side, before
        # this bar's zones so a level flipped on THIS bar starts on the NEXT one.
        # A second BREACHED retires it (ruling 4: "If a level isn't respected,
        # then it's not a level").
        for fid in list(book.flipped):
            fl = book.flipped[fid]
            for ev in flip_eps[fid].step(bar, (fl.price, fl.price)):
                book.events.append({"event": ev, "ts": ts, "judged_on": tf, "flip": True,
                                    "side": fl.side, "near": fl.price, "far": fl.price,
                                    "level_ids": [fid], "prices": [fl.price]})
                if ev == R.BREACHED:
                    book.flip_dead[fid] = ts
                    book.flipped.pop(fid, None)
                    flip_eps.pop(fid, None)
        while pending and pending[0].live_from <= ts:
            lv = pending.pop(0)
            if lv.level_id not in book.dead:
                book.live[lv.level_id] = lv
                dirty = True
        if dirty:
            zone_list = book.current_zones()
            keys = {frozenset(m.level_id for m in z["members"]) for z in zone_list}
            # a zone whose MEMBERSHIP changed is a new object: its episode starts clean
            episodes = {k: v for k, v in episodes.items() if k in keys}
            dirty = False
        for z in zone_list:
            key = frozenset(m.level_id for m in z["members"])
            if not all(k in book.live for k in key):
                continue
            ep = episodes.get(key)
            if ep is None:
                side = _zone_side(z["members"], bar[1])
                if side is None:
                    continue
                ep = episodes[key] = R.Episode(side)
            near, far = R.edges_of(z["lo"], z["hi"], ep.side)
            for ev in ep.step(bar, (near, far)):
                if tf == "1h":
                    hourly_touched |= set(key)
                book.events.append({"event": ev, "ts": ts, "judged_on": tf,
                                    "side": ep.side, "near": near, "far": far,
                                    "level_ids": sorted(key),
                                    "prices": sorted(m.price for m in z["members"])})
                if ev == R.BREACHED:
                    for lid in key:
                        book.dead[lid] = ts
                        book.live.pop(lid, None)
                    dirty = True
                    # FLIP.1 — a LONE level accepted through FLIPS (rulings 1-2);
                    # a ZONE retires as before and never flips (ruling 3: "A zone
                    # is similar to a fair value Gap it's not going to hold").
                    if len(key) == 1:
                        (m,) = z["members"]
                        new_side = opposite(ep.side)
                        fid = flip_id(book.symbol, new_side, m.price)
                        if fid not in book.flipped and fid not in book.flip_dead:
                            book.flipped[fid] = Level(fid, new_side, m.price, m.formed_ts, ts)
                            book.flip_of[fid] = m.level_id
                            flip_eps[fid] = R.Episode(new_side)
                            book.events.append({"event": "FLIPPED", "ts": ts, "judged_on": tf,
                                                "flip": True, "side": new_side,
                                                "near": m.price, "far": m.price,
                                                "level_ids": [fid], "prices": [m.price],
                                                "from": m.level_id})
        book.as_of = ts
    book.hourly_judged = len(hourly_touched)
    return book


def walk(reps: Sequence[dict], anchor: float, up: bool) -> List[dict]:
    """r29's walk (copied): newest first from the anchor, each older rung only
    if FURTHER out. `reps` carry `price` (the NEAR edge) and `formed_ts`."""
    newest_first = sorted(reps, key=lambda r: (-r["formed_ts"], abs(r["price"] - anchor)))
    out, last = [], anchor
    for r in newest_first:
        p = r["price"]
        if (up and p > anchor and p > last) or ((not up) and p < anchor and p < last):
            out.append(r)
            last = p
    return sorted(out, key=lambda r: r["price"], reverse=not up)


def board(book: Book, spot: float, anchor_up: Optional[float] = None,
          anchor_dn: Optional[float] = None) -> dict:
    """{above, below}: zones walked outward from the anchors (spot by default;
    the opening-range edges for the hunt and the breakout). Each rung: near
    edge, far edge, side, members, formed_ts of its newest member. No cap —
    *"three would be ideal ... if there's more I would like to have more"*."""
    up_from = spot if anchor_up is None else anchor_up
    dn_from = spot if anchor_dn is None else anchor_dn
    reps_up, reps_dn = [], []
    for z in book.current_zones():
        newest = max(m.formed_ts for m in z["members"])
        rung = {"lo": z["lo"], "hi": z["hi"], "n": len(z["members"]),
                "level_ids": sorted(m.level_id for m in z["members"]),
                "formed_ts": newest}
        if z["lo"] > up_from:
            reps_up.append({**rung, "price": z["lo"], "near": z["lo"], "far": z["hi"],
                            "side": R.RESISTANCE})
        elif z["hi"] < dn_from:
            reps_dn.append({**rung, "price": z["hi"], "near": z["hi"], "far": z["lo"],
                            "side": R.SUPPORT})
    return {"above": walk(reps_up, up_from, True), "below": walk(reps_dn, dn_from, False),
            "width": book.width, "as_of": book.as_of}
