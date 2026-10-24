#!/usr/bin/env python3
"""
tests/check_level_tape.py  v2.2
THE LEVEL BOOK IS BUILT FROM THE HOURLY TAPE, AND ITS BREACHES ARE JUDGED ON 1m.

v2.2  2026-10-04  OTV4TEST r237 (SEED.2) — T2b: THE SAME TEST FOR 5m AND 15m. T2 judged only 1h, so when seed v1.0 wrote
      1,297 mid-bar 5m and 380 mid-bar 15m bars into SPX-TEST's store (mainline's raw/candles carries every 5m/15m/1h bar
      as its first ~30 s), only 8 hourly bars showed. A 5m/15m bar is judged when its own minutes are ALL present (5 / 15),
      and must be at least as wide as them. Measured on QQQ-TEST's store before landing: 2,397 5m and 1,024 15m judged, 0 narrower.
v2.1  2026-10-03  OTV4TEST r232 — SYMBOL AGNOSTIC: T7 and T2 read the BOX's instrument (the bot unit, then OT_INSTRUMENT) instead of
      a literal 'QQQ' - red on SPX-TEST for that reason alone (its agent found it). The boot sweep sets OT_INSTRUMENT=QQQ
      for fixtures, so the unit is read first: this check reads the box's REAL feed store.
v2.0  2026-09-23  OTV4TEST r126 — derived/level_map and the old mapper are DELETED
      (LVL.15 step 5), so the checks that pinned THEIR internals retire with
      them, and the three that pin the DATA the book depends on stay:
      KEPT  T2 (no PARTIAL hourly bar - it caught a real corruption on 09-18,
            and the book builds every level from these bars) and T8 (1m
            retention covers 1h, r108 - the book judges BREACHED on 1m).
      MOVED T7 (reach > 30 days) now reads the book's own bar loader,
            derived/level_book.load_bars, not level_map.load_tape.
      RETIRED T1/T1b (load_tape's default interval), T3 (the mapper's section
            hours), T4 (level_map's daily source), T5 (`_derive_events`, the
            legacy engine path) - all four name code that no longer exists.
      COVERED ELSEWHERE T6 (the opening-range rule): check_level_book K14 and
            check_level_engine_book E8 pin it on the book path.
      And the r106 venv bootstrap.

v1.2  2026-09-23  OTV4TEST r108 — T8: 1m RETENTION MUST COVER 1h RETENTION.
      Levels are built from the hourly tape; the operator's BREACHED rule is a
      1-minute rule (a 1m close beyond, the next 1m open beyond). MEASURED on
      08-25..09-22 warehouse tape with hourly bars built from the SAME 1m bars:
      of 142 extremes the 1m rule breached, the hourly test was more than an
      hour late on 50 and never saw 5 — 39% of dead levels left live. So every
      level the 1h tape can build must have 1m bars to judge it. Born RED at
      7b17b77, where RETENTION_DAYS["1m"] is 5 against "1h" 60. T7's label
      named the old 5-day window as a fact; its assertion (> 30 days of hourly
      reach) was always independent of it and is unchanged.
v1.1  2026-09-18  OTV4TEST r39 — T6 WENT RED ON CORRECT CODE, AND THE REFLEX FIX
      WOULD HAVE BLINDED IT. It matched a FIXED 1400-CHARACTER SLICE taken from
      the `in_range` lambda. r39 inserted the zone-traversal rule between that
      lambda and the retirement it guards; the opening-range rule was untouched
      and fully bound, and T6 failed anyway. A canary keyed to a MAGIC DISTANCE
      fires on any insertion above its target, and the obvious repair is to
      raise 1400 until it passes — which is §20's loosened canary, and every
      future insertion buys another raise until the window is wide enough to
      catch nothing. Re-anchored on the BINDING: the `if` that actually reads
      `in_range(lvl_price)`, found wherever it sits.
      ⚠️ AND IT WAS MUTATION-TESTED RATHER THAN ASSUMED, because a re-anchored
      canary that no longer fires is worse than the false red it replaced.
      Four mutants against a CONTROL that must come back clean: dropping the
      `in_range` term, dropping the tine exemption, and renaming TRAVERSED are
      each CAUGHT; inserting forty filler lines above the guard PASSES, which
      is the false red this revision removed.
v1.0  2026-09-18  OTV4TEST r36 — born red at r35 (1006003), where `load_tape`
      reads `interval='1m'` and `daily_levels`/`load_daily` exist.

WHY THE HOUR. Retention kept 1m for FIVE DAYS (until r108) and 1h for SIXTY
(`RETENTION_DAYS`), so the board reached nine days back while twelve weeks of
hourly history sat unread in the same store. Measured 2026-09-17 against the
operator's own 1D chart: three of his five levels above spot were not in the
ledger at all. Operator: *"use 1-hr as far back as you can"*, then *"use the
hour exclusively"*.

WHAT IS PINNED (v2.0):
  T2   an hourly bar's high/low IS the extreme of its hour — no PARTIAL bars
  T2b  r237: the same for 5m and 15m against their own minutes
  T7   reach — the book sees more than 30 days back on the hourly tape
  T8   1m retention >= 1h retention, so a breach can be judged on 1m for
       every level the hourly tape builds (r108)
"""
import os
import sqlite3
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import glob as _glob                                             # r106 venv bootstrap
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    # ── T8 — r108: the minute is kept as long as the hour ────────────────────
    # 🔑 THE LEVEL IS BUILT ON 1h; ITS BREACH IS JUDGED ON 1m. The operator's
    # BREACHED (2026-09-22) is a 1m close beyond and the next 1m open beyond.
    # An hourly close beyond + next hourly open beyond IMPLIES it, but not the
    # reverse — measured, the hourly stand-in left 39% of dead levels live.
    # So the 1m window must reach every level the 1h window can build.
    # ⚠️ READ FROM THE POLICY ITSELF, not a copy of its numbers (§0.4): the
    # fixture is the constant the purge actually executes.
    try:
        from warehouse import retention_purge as _rp
        _rd = getattr(_rp, "RETENTION_DAYS", {}) or {}
        _m, _h = _rd.get("1m"), _rd.get("1h")
        _ok = (_m is None) or (_h is not None and _m >= _h)
        check("T8 1m candles are kept at least as long as 1h (breaches are judged on 1m)",
              _ok, f'RETENTION_DAYS 1m={_m!r} 1h={_h!r}')
    except Exception as _e:                                     # noqa: BLE001
        check("T8 1m candles are kept at least as long as 1h (breaches are judged on 1m)",
              False, f"could not read the policy: {type(_e).__name__}: {_e}")

    # ── the real store: T2, T7 ──────────────────────────────────────────────
    db = os.path.join(ROOT, "data", "feed_store.db")
    if not os.path.exists(db):
        check("T2 skipped — no feed store on this box", True, "not a box")
        print()
        return 1 if FAILED else 0

    # T7 (r126: the book's own loader) — the book reaches more than 30 days back
    from derived import level_book as B
    from utils import instrument as _I                          # r232: the box's symbol, not a literal
    SYM = (_I._from_bot_unit() or os.environ.get("OT_INSTRUMENT") or "QQQ").strip()
    h1 = B.load_bars(db, SYM, "1h") or []
    span_days = ((h1[-1][0] - h1[0][0]) / 86_400_000.0) if len(h1) >= 2 else 0.0
    check("T7 the book reaches more than 30 days back on the hourly tape",
          span_days > 30, f"{span_days:.1f} days of hourly tape ({len(h1)} bars)")

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)

    # T2 — EACH HOURLY BAR AGAINST ITS OWN HOUR OF 1m, which is the only
    # comparison that means anything. The first cut bucketed by UTC DAY and
    # reported 4 of 7 days "mismatched" — true, but it could not say WHICH bar
    # was wrong, and a day-level answer hid that the errors were all in one
    # direction (narrower range = an unfinished bar).
    # 🔴 THIS IS THE CHECK THAT CAUGHT A REAL CORRUPTION. On 2026-09-18 a seed
    # wrote S3 hourly bars over locally-complete ones with INSERT OR REPLACE,
    # and 369 of 1,265 were PARTIAL — pushed mid-hour, so `19:00 UTC` on 09-16
    # read 705.46/704.08 when the true hour was 706.02/700.00. A level at
    # 700.00 that price turned at was invisible. The rule the data demands:
    # a bar is accepted only if its object was pushed at or after its hour ENDED.
    rows = con.execute(
        "SELECT c.symbol, c.ts_epoch_ms, c.high, c.low, m.mh, m.ml, m.n FROM candles c"
        " JOIN (SELECT symbol, (ts_epoch_ms/3600000)*3600000 h, MAX(high) mh, MIN(low) ml,"
        "              COUNT(*) n FROM candles"
        "       WHERE symbol IN (?, ?) AND interval='1m'"
        "       GROUP BY symbol, h) m"
        "   ON m.symbol=c.symbol AND m.h=c.ts_epoch_ms"
        " WHERE c.symbol IN (?, ?) AND c.interval='1h'", (SYM, SYM + "_EXT", SYM, SYM + "_EXT")).fetchall()
    # an hour the 1m tape only partly covers cannot judge the hourly bar
    judged = [r for r in rows if r[6] >= 30]
    bad = [r for r in judged if r[2] < r[4] - 0.02 or r[3] > r[5] + 0.02]
    # T2b (r237) — 5m and 15m against their own minutes, judged only when every minute is present
    bad_b, judged_b = {}, {}
    for iv, span, need in (("5m", 300_000, 5), ("15m", 900_000, 15)):
        got = con.execute(
            "SELECT c.ts_epoch_ms, c.high, c.low, m.mh, m.ml FROM candles c"
            " JOIN (SELECT symbol, (ts_epoch_ms/?)*? h, MAX(high) mh, MIN(low) ml, COUNT(*) n FROM candles"
            "       WHERE symbol IN (?, ?) AND interval='1m' GROUP BY symbol, h) m"
            "   ON m.symbol=c.symbol AND m.h=c.ts_epoch_ms"
            " WHERE c.symbol IN (?, ?) AND c.interval=? AND m.n >= ?",
            (span, span, SYM, SYM + "_EXT", SYM, SYM + "_EXT", iv, need)).fetchall()
        judged_b[iv] = len(got)
        bad_b[iv] = [g for g in got if g[1] < g[3] - 0.02 or g[2] > g[4] + 0.02]
    con.close()
    check("T2b every 5m and 15m bar is at least as wide as its own minutes — no PARTIAL bars",
          all(judged_b.values()) and not any(bad_b.values()),
          "; ".join(f"{iv}: {judged_b[iv]} judged, {len(bad_b[iv])} narrower"
                    + (f" e.g. {bad_b[iv][0][0]} {bad_b[iv][0][1]:.2f}/{bad_b[iv][0][2]:.2f} vs "
                       f"{bad_b[iv][0][3]:.2f}/{bad_b[iv][0][4]:.2f}" if bad_b[iv] else "") for iv in judged_b))
    check("T2 every hourly bar is at least as wide as its own hour of 1m — no PARTIAL bars",
          judged and not bad,
          f"{len(judged)} bars judged, {len(bad)} narrower than the minute truth"
          + (f" e.g. {bad[0][0]} {bad[0][2]:.2f}/{bad[0][3]:.2f} vs {bad[0][4]:.2f}/{bad[0][5]:.2f}" if bad else ""))

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
