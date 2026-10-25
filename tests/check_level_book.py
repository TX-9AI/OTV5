#!/usr/bin/env python3
"""
tests/check_level_book.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
THE LEVEL BOOK, DRIVEN ON HAND-BUILT TAPES.

v1.4  2026-10-18  OTV4TEST r300 (LVL.20) — K15: the RTH block ends at the day's bell (13:00 on the 2026-11-27 half day,
      16:00 on 11-25) in et_blocks, blocks_for and _in_rth. RED on 6bfd250 (fixed 16:00 everywhere).

v1.3  2026-10-01  OTV4TEST FLIP.1 — K5 RE-POINTED BY THE RULING, NOT DELETED: it judges
      the original level's own events; the operator's flip (2026-10-01) adds a
      FLIPPED successor on the same bar, which tests/check_level_flip.py pins.
v1.2  2026-09-23  OTV4TEST r111 — K13 (the lone-print ruling, on build()'s defaults)
      and K14 (the opening-range ruling); each red on r110's book.
v1.1  2026-09-23  OTV4TEST r110 — K11, K12: the book moved to ET-clock blocks built
      from the 1m tape (pre-market ends 09:30), with an hourly fallback.
v1.0  2026-09-23  OTV4TEST LVL.15 step 2 (unlanded WIP). Born RED where
      `derived/level_book.py` does not exist — NAMED failures, not a traceback.

  K1  the day is FOUR contiguous blocks covering 00->24Z in BOTH DST offsets,
      and the last is AFTER-HOURS (16:00-20:00 ET in summer)
  K2  a session STILL FORMING is not a level (ruling 2026-09-22)
  K3  identity is side + price — NO session label; one price printed by two
      sessions is ONE level, dated by the newer formation
  K4  a level becomes live at its session's END, not at its print
  K5  a single level: wick-in + close back = HELD; close beyond + open beyond
      = BREACHED and it leaves the book
  K6  a ZONE: a breach of the FAR edge retires EVERY member (r39 kept)
  K7  a ZONE: a close past the near edge but short of the far one leaves the
      zone LIVE and is NOT a HELD (rulings 09-23, "b")
  K8  the walk: newest first, each older rung only if FURTHER out (r29), and
      a nearer-but-older level is not on the board
  K9  the board anchors on the opening-range edges when given
  K10 no module in the new book imports the old mapper or the old level files
  K11 v1.1: pre-market ends 09:30 ET — a 09:27 low is a pre-market level,
      live at 09:30 (red on v1.0's hour-granular blocks)
  K12 v1.1: an hourly candle wholly inside a block supplies an extreme the
      seeded 1m tape is missing (green on v1.0 too: it pins the fallback)
  K1b/K2b v1.1: K1 and K2 on the ET-clock path build() uses (K1/K2 pin the
      hourly helpers, which build() no longer calls)
  K13 v1.1: the operator's ruling (2026-09-23) — a lone 1m print outside RTH
      is not a session extreme; the same shape inside RTH stays
  K14 v1.1: the operator's ruling (2026-09-23) — a level inside the day's
      5-min opening range retires TRAVERSED at 09:35; one outside stays

"""
from __future__ import annotations

import ast
import os
import sys
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def guard(name, fn):
    try:
        ok, detail = fn()
    except Exception as exc:                                    # noqa: BLE001
        ok, detail = False, f"raised {type(exc).__name__}: {exc}"
    check(name, ok, detail)


try:
    from derived import level_book as B
    from derived import level_rules as R
except Exception as exc:                                        # noqa: BLE001
    _why = f"derived/level_book.py or level_rules.py absent: {type(exc).__name__}: {exc}"

    class _Absent:
        def __getattr__(self, n):
            raise RuntimeError(_why)
    B = R = _Absent()

H = 3_600_000
M = 60_000


def ms(y, mo, d, hh, mm=0):
    return int(datetime(y, mo, d, hh, mm, tzinfo=timezone.utc).timestamp() * 1000)


def flat_hours(start_ms, n, px=100.0, wick=0.1):
    return [(start_ms + i * H, px, px + wick, px - wick, px) for i in range(n)]


# ── K1 ──
def _k1():
    summer, winter = B.blocks_for(date(2026, 9, 23)), B.blocks_for(date(2026, 12, 2))
    ok = True
    for bl in (summer, winter):
        ok &= bl[0][0] == 0 and bl[-1][1] == 24 and all(a[1] == b[0] for a, b in zip(bl, bl[1:]))
    # summer after-hours = 20Z..24Z = 16:00..20:00 EDT
    ok &= summer[-1] == (20, 24) and winter[2] == (14, 21)
    return ok, f"summer {summer} winter {winter}"


guard("K1 four contiguous blocks, 00->24Z in both offsets, the last is AFTER-HOURS", _k1)


# ── K2 / K4 ──
def _k2():
    day = ms(2026, 9, 21, 0)
    h1 = flat_hours(day, 22)                      # 00Z..21Z: the 20Z..24Z block is still forming
    ends = [s["end"] for s in B.closed_sessions(h1, now_ms=day + 22 * H)]
    return (day + 24 * H not in ends and day + 20 * H in ends), f"closed ends (h): {[(e - day) // H for e in ends]}"


guard("K2 a session still forming is NOT a level", _k2)


# ── K3 ──
def _k3():
    d1, d2 = ms(2026, 9, 21, 0), ms(2026, 9, 22, 0)
    h1 = flat_hours(d1, 24) + flat_hours(d2, 24)
    # both days' 00-08Z block print the SAME high, 105.00
    h1 = [(t, o, 105.0 if t in (d1 + 3 * H, d2 + 5 * H) else hi, lo, c) for t, o, hi, lo, c in h1]
    lv = B._levels_from("QQQ", B.closed_sessions(h1, now_ms=d2 + 48 * H))
    hits = [l for l in lv if abs(l.price - 105.0) < 1e-9]
    return (len(hits) == 1 and hits[0].level_id == "QQQ:resistance:105.00"
            and hits[0].formed_ts == d2 + 5 * H), f"{[(l.level_id, l.formed_ts) for l in hits]}"


guard("K3 identity is side+price, no label; one price = one level, dated by the NEWER print", _k3)


def _book_with(level_px, side, tail):
    """A book where ONE session's extreme is `level_px`, then 1m `tail` bars."""
    d = ms(2026, 9, 21, 0)
    h1 = flat_hours(d, 8)                                    # the 00-08Z block
    k = 3
    t, o, hi, lo, c = h1[k]
    h1[k] = (t, o, level_px if side == "resistance" else hi,
             level_px if side == "support" else lo, c)
    return B.build("QQQ", h1, tail, now_ms=d + 8 * H), d + 8 * H


def _k4():
    d = ms(2026, 9, 21, 0)
    h1 = flat_hours(d, 8)
    h1[3] = (h1[3][0], 100.0, 101.0, 99.9, 100.0)
    # a 1m test of 101.00 at 05Z — INSIDE the still-open block — must not count
    early = [(d + 5 * H, 100.5, 101.0, 100.4, 100.6)]
    b = B.build("QQQ", h1, early + [(d + 8 * H, 100.5, 100.6, 100.4, 100.5)], now_ms=d + 8 * H)
    evs = [e for e in b.events if 101.0 in e["prices"]]
    return not evs and "QQQ:resistance:101.00" in b.live, f"events {evs}"


guard("K4 a level goes live at its session's END, never before", _k4)


def _h1_for(px, side):
    d = ms(2026, 9, 21, 0)
    h1 = flat_hours(d, 8)
    t, o, hi, lo, c = h1[3]
    h1[3] = (t, o, px if side == "resistance" else hi, px if side == "support" else lo, c)
    return h1, d + 8 * H


def _k5b():
    h1, t = _h1_for(101.0, "resistance")
    tape = [(t, 100.6, 101.0, 100.5, 100.8),            # reaches, closes under -> HELD
            (t + M, 100.8, 101.3, 100.7, 101.2),        # closes beyond
            (t + 2 * M, 101.25, 101.4, 101.2, 101.3)]   # opens beyond -> BREACHED
    b = B.build("QQQ", h1, tape, now_ms=t)
    # v1.3 (FLIP.1): the flip is the ORIGINAL level's successor and is pinned in
    # check_level_flip; K5 judges the original level's own events only.
    evs = [(e["event"], (e["ts"] - t) // M) for e in b.events
           if 101.0 in e["prices"] and not e.get("flip")]
    ok = evs == [("TESTED", 0), ("HELD", 0), ("TESTED", 1), ("BREACHED", 2)] \
        and "QQQ:resistance:101.00" not in b.live and "QQQ:resistance:101.00" in b.dead
    return ok, f"{evs}"


guard("K5 a single level: HELD, then BREACHED — and it leaves the book", _k5b)


def _zone_book(tape_fn):
    """⚠️ THE FIRST CUT OF THIS FIXTURE WAS WRONG, NOT THE BOOK: 0.10 filler
    wicks made the measured zone width 0.10, so highs 0.20 apart were rightly
    NOT one zone, and the fillers' own 100.10 highs crowded the board. The
    width is MEASURED from the tape (r39), so the fixture must carry the wick
    that makes a zone: 0.30, with the fillers' highs (100.30) 0.70 below."""
    d = ms(2026, 9, 21, 0)
    h1 = flat_hours(d, 24, wick=0.3)
    # two sessions print highs 101.00 and 101.20 — inside one zone width (0.30)
    h1[3] = (h1[3][0], 100.0, 101.0, 99.7, 100.0)          # 00-08Z block
    h1[10] = (h1[10][0], 100.0, 101.2, 99.7, 100.0)        # 08-13Z block
    t = d + 24 * H
    return B.build("QQQ", h1, tape_fn(t), now_ms=t), t


def _k6():
    b, t = _zone_book(lambda t: [(t, 101.1, 101.4, 101.0, 101.3), (t + M, 101.35, 101.5, 101.3, 101.4)])
    zs = [z for z in b.events if set(z["prices"]) == {101.0, 101.2}]
    ok = (b.width is not None and zs and zs[-1]["event"] == "BREACHED"
          and "QQQ:resistance:101.00" not in b.live and "QQQ:resistance:101.20" not in b.live)
    return ok, f"width {b.width} zone events {[(e['event'], e['near'], e['far']) for e in zs]}"


guard("K6 a breach of the zone's FAR edge retires EVERY member", _k6)


def _k7():
    b, t = _zone_book(lambda t: [(t, 100.9, 101.1, 100.85, 101.1),    # into the zone, closes INSIDE
                                 (t + M, 101.1, 101.15, 100.9, 100.95)])  # closes back under near -> HELD
    zs = [(e["event"], (e["ts"] - t) // M) for e in b.events if set(e["prices"]) == {101.0, 101.2}]
    ok = zs == [("TESTED", 0), ("HELD", 1)] and "QQQ:resistance:101.20" in b.live
    return ok, f"{zs}"


guard("K7 a close INSIDE a zone is not HELD; the zone stays live; the close back out is", _k7)


def _k8():
    old_near = {"price": 101.0, "formed_ts": 1, "near": 101.0}
    new_far = {"price": 102.0, "formed_ts": 5, "near": 102.0}
    older_further = {"price": 103.0, "formed_ts": 2, "near": 103.0}
    w = B.walk([old_near, new_far, older_further], 100.0, True)
    got = [r["price"] for r in w]
    return got == [102.0, 103.0], f"walk -> {got} (101.00 is nearer but OLDER than 102.00)"


guard("K8 the walk: newest first, each older rung only if further out", _k8)


def _k9():
    b, t = _zone_book(lambda t: [(t, 100.0, 100.1, 99.9, 100.0)])
    bd_spot = B.board(b, 100.0)
    bd_rng = B.board(b, 100.0, anchor_up=101.1, anchor_dn=99.0)
    return (bool(bd_spot["above"]) and not bd_rng["above"]), \
        f"above from spot {[r['near'] for r in bd_spot['above']]}, from range edge 101.1 {[r['near'] for r in bd_rng['above']]}"


guard("K9 the board anchors on the opening-range edges when given", _k9)


def _k10():
    bad = []
    for f in ("derived/level_book.py", "derived/level_rules.py"):
        tree = ast.parse(open(os.path.join(ROOT, f), encoding="utf-8").read())
        for n in ast.walk(tree):
            mods = []
            if isinstance(n, ast.Import):
                mods = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                mods = [n.module or ""] + [f"{n.module}.{a.name}" for a in n.names]
            for m in mods:
                if any(x in m for x in ("liquidity_mapper", "liquidity_ledger", "level_map",
                                        "derived.levels", "pitchfork_lifecycle")):
                    bad.append((f, m))
    return not bad, f"forbidden imports: {bad}"


guard("K10 the new book imports NOTHING from the old mapper or the old level files", _k10)


# ── K11 / K12 — sessions on the ET clock, extremes from the MINUTE ──
def _k11():
    """09-18: the real pre-market low printed at 09:27 ET. An hour-granular
    block (08-13Z) hands the 13Z hour to RTH, so the low became an RTH level
    live at 16:00 — or vanished under a lower RTH low. Pre-market ends 09:30."""
    d = ms(2026, 9, 21, 0)                                   # Monday, EDT: 09:30 ET = 13:30Z
    h1 = flat_hours(d, 24)
    h1[13] = (h1[13][0], 100.0, 100.1, 99.0, 100.0)          # the 13Z hour carries the 99.00 low
    m1 = [(d + 13 * H + k * M, 100.0, 100.1, 99.0 if k == 27 else 99.9, 100.0)
          for k in range(20, 40)]                            # 13:20..13:39Z; 13:27Z = 09:27 ET
    # driven through build(): by 13:39Z (09:39 ET) the pre-market has CLOSED,
    # so its 09:27 low must already be a LIVE level, dated at its minute
    b = B.build("QQQ", h1, m1, now_ms=d + 24 * H)
    got = b.live.get("QQQ:support:99.00")
    ok = got is not None and got.formed_ts == d + 13 * H + 27 * M and got.live_from == d + 13 * H + 30 * M
    return ok, (f"99.00 formed +{(got.formed_ts - d) // M}m live +{(got.live_from - d) // M}m (want +807m / +810m)"
                if got else f"99.00 not live at 09:39 ET; live {sorted(b.live)[:6]}")


guard("K11 pre-market ends 09:30 ET: a 09:27 low is a PRE-MARKET level, live at 09:30", _k11)


def _k12():
    """The seeded 1m tape misses one minute in five (PRE.5). An hourly candle
    wholly inside a block is an AGGREGATE, so its extreme is the block's even
    when the minute that printed it is missing."""
    d = ms(2026, 9, 21, 0)
    h1 = flat_hours(d, 24)
    h1[10] = (h1[10][0], 100.0, 100.1, 98.5, 100.0)          # 10Z hour, inside pre-market
    m1 = [(d + 10 * H + k * M, 100.0, 100.1, 99.9, 100.0) for k in range(60) if k % 5 != 4]
    lv = {l.level_id for l in B._levels_from("QQQ", B.closed_sessions_et(h1, m1, now_ms=d + 24 * H))}
    return "QQQ:support:98.50" in lv, f"98.50 in book: {'QQQ:support:98.50' in lv}"


guard("K12 an hourly candle wholly inside a block supplies an extreme the 1m tape is missing", _k12)


# ── K1b / K2b — the SAME two rules on the ET-clock path build() actually uses ──
def _k1b():
    from datetime import timedelta
    out = []
    for d in (date(2026, 9, 23), date(2026, 12, 2), date(2026, 11, 2)):   # EDT, EST, the day after the switch
        bl = B.et_blocks(d)
        contiguous = all(a[1] == b[0] for a, b in zip(bl, bl[1:]))
        prev_last = B.et_blocks(d - timedelta(days=1))[-1][1]
        spans_h = [round((b - a) / H, 2) for a, b in bl]
        out.append((str(d), contiguous and prev_last == bl[0][0] and spans_h[1:] == [5.5, 6.5, 4.0], spans_h))
    return all(o[1] for o in out), f"{out}"


guard("K1b ET blocks: overnight 8h / pre 5.5h / RTH 6.5h / AH 4h, contiguous day to day, DST-safe", _k1b)


def _k2b():
    d = ms(2026, 9, 21, 0)
    h1 = flat_hours(d, 24)
    # a LIVE tape never runs past now: at 09:29 the last closed candle is 09:28,
    # and at 09:30 the 09:29 candle has closed (the first cut of this fixture
    # ran the tape to 09:44 and "failed" for that reason — the fixture, not the book)
    m1_0929 = [(d + 13 * H + k * M, 100.0, 100.1, 99.9, 100.0) for k in range(0, 29)]
    m1_0930 = m1_0929 + [(d + 13 * H + 29 * M, 100.0, 100.1, 99.9, 100.0)]
    now = d + 13 * H + 29 * M                                                       # 09:29 ET
    ends_now = [s["end"] for s in B.closed_sessions_et(h1[:13], m1_0929, now_ms=now)]
    pre_end = d + 13 * H + 30 * M
    ok = pre_end not in ends_now
    ends_later = [s["end"] for s in B.closed_sessions_et(h1[:13], m1_0930, now_ms=pre_end)]
    return ok and pre_end in ends_later, f"at 09:29 pre-market closed: {pre_end in ends_now}; at 09:30: {pre_end in ends_later}"


guard("K2b ET path: pre-market is NOT a level at 09:29, and IS at 09:30", _k2b)


# ── K13 — the operator's ruling: a lone print is not a session extreme ──
def _k13():
    """09-21 08:25 ET, as it printed: the market at 728.2-728.4 and ONE candle
    opening 728.22, printing 725.75, closing 728.24. The same shape inside RTH
    is a real flush and must STAY. Driven through build() with its DEFAULTS."""
    d = ms(2026, 9, 21, 0)
    pre = d + 12 * H + 25 * M                       # 08:25 ET
    rth = d + 14 * H + 25 * M                       # 10:25 ET
    h1 = flat_hours(d, 24, px=728.3, wick=0.1)
    h1[12] = (h1[12][0], 728.3, 728.4, 725.75, 728.3)   # the hour carries the print too
    h1[14] = (h1[14][0], 728.3, 728.4, 725.60, 728.3)
    m1 = []
    for base in (d + 12 * H, d + 14 * H):
        for k in range(60):
            t = base + k * M
            if t == pre:
                m1.append((t, 728.22, 728.24, 725.75, 728.24))      # the lone print
            elif t == rth:
                m1.append((t, 728.22, 728.24, 725.60, 728.24))      # same shape, RTH
            else:
                m1.append((t, 728.3, 728.4, 728.2, 728.3))
    # the SESSION EXTREMES, on defaults (a flat fixture re-prints 728.20 as every
    # block's low, so by "the newest print dates it" that level re-dates to a
    # later block — the extremes are the direct statement of the rule)
    lows = {(s_["start"] - d) // M: s_["low"] for s_ in B.closed_sessions_et(h1, m1, now_ms=d + 24 * H)}
    pre_low, rth_low = lows.get(8 * 60), lows.get(13 * 60 + 30)
    b = B.build("QQQ", h1, m1, now_ms=d + 24 * H)
    ids = set(b.live) | set(b.dead)
    ok = (round(pre_low or 0, 2) == 728.2 and round(rth_low or 0, 2) == 725.6 and "QQQ:support:725.75" not in ids
          and "QQQ:support:725.60" in ids)
    return ok, (f"pre-market low {pre_low} (want 728.2, not the 725.75 print); RTH low {rth_low} "
                f"(want 725.6, the flush kept); 725.75 in book: {'QQQ:support:725.75' in ids}")


guard("K13 ruling: a lone print outside RTH is not a session extreme; the same shape in RTH stays", _k13)


# ── K14 — the operator's ruling: a level inside today's 5-min opening range retires ──
def _k14():
    """Two session highs live at 09:30: the OVERNIGHT high 100.50 (INSIDE the
    09:30-09:34 range 100.20-100.80) and the PRE-MARKET high 101.50 (outside).
    At 09:35 the inside one retires TRAVERSED, with no BREACHED; the outside
    one stays live. (The first cut put both in pre-market, where only the
    higher is an extreme — the fixture, not the book.)"""
    d = ms(2026, 9, 21, 0)
    h1 = flat_hours(d, 13, px=100.0, wick=0.1)
    h1[3] = (h1[3][0], 100.0, 100.5, 99.9, 100.0)        # 23:00 ET Sun: the overnight high 100.50
    h1[10] = (h1[10][0], 100.0, 101.5, 99.9, 100.0)      # 06:00 ET: a high of 101.50
    rth = d + 13 * H + 30 * M
    m1 = [(d + 13 * H + k * M, 100.0, 100.05, 99.95, 100.0) for k in range(0, 30)]   # 09:00-09:29
    m1 += [(rth + k * M, 100.3, 100.8 if k == 2 else 100.4, 100.2 if k == 3 else 100.3, 100.35)
           for k in range(0, 5)]                                                    # the opening range
    m1 += [(rth + k * M, 100.3, 100.4, 100.25, 100.3) for k in range(5, 10)]         # 09:35 on
    b = B.build("QQQ", h1, m1, now_ms=rth + 10 * M)
    inside, outside = "QQQ:resistance:100.50", "QQQ:resistance:101.50"
    breached = [e for e in b.events if e["event"] == "BREACHED" and inside in e["level_ids"]]
    ok = (inside in getattr(b, "traversed", set()) and b.dead.get(inside) == rth + 5 * M
          and outside in b.live and not breached)
    return ok, (f"100.50 traversed: {inside in getattr(b, 'traversed', set())} at "
                f"{(b.dead.get(inside, 0) - rth) // M if inside in b.dead else None}m after 09:30; "
                f"101.50 live: {outside in b.live}; breach events on 100.50: {len(breached)}")


guard("K14 ruling: a level inside the 09:30-09:34 opening range retires TRAVERSED at 09:35", _k14)


def _k15():
    """r300 (LVL.20): the RTH block ends at the day's BELL. 2026-11-27 closes 13:00 (utils/market_calendar);
    2026-11-25 is a full day. Pinned against each other so an always-shift mutant dies."""
    from datetime import date, datetime
    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/New_York")

    def _ms(d, hh, mm):
        return int(datetime(d.year, d.month, d.day, hh, mm, tzinfo=et).timestamp() * 1000)
    half, full = date(2026, 11, 27), date(2026, 11, 25)
    eb_h, eb_f = B.et_blocks(half), B.et_blocks(full)
    rth_h_end = datetime.fromtimestamp(eb_h[2][1] / 1000, et).strftime("%H:%M")
    ah_h_start = datetime.fromtimestamp(eb_h[3][0] / 1000, et).strftime("%H:%M")
    rth_f_end = datetime.fromtimestamp(eb_f[2][1] / 1000, et).strftime("%H:%M")
    bf_h, bf_f = B.blocks_for(half), B.blocks_for(full)
    ok = (rth_h_end == "13:00" and ah_h_start == "13:00" and rth_f_end == "16:00"
          and bf_h[2] == (14, 18) and bf_f[2] == (14, 21)
          and B._in_rth(_ms(half, 12, 59)) and not B._in_rth(_ms(half, 13, 0))
          and B._in_rth(_ms(full, 15, 59)) and not B._in_rth(_ms(full, 16, 0)))
    return ok, (f"11-27 RTH ends {rth_h_end}, AH starts {ah_h_start}, blocks {bf_h[2]}; 11-25 RTH ends {rth_f_end}, "
                f"blocks {bf_f[2]}; _in_rth 11-27 12:59/13:00 = {B._in_rth(_ms(half, 12, 59))}/{B._in_rth(_ms(half, 13, 0))}")


guard("K15 the RTH block ends at the day's bell: 13:00 on 2026-11-27, 16:00 on 2026-11-25 (et_blocks, blocks_for, _in_rth)", _k15)

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
