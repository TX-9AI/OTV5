#!/usr/bin/env python3
"""
tests/check_rebuild_1m.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.2  2026-10-11  OTV4TEST r267 (SEED.3, authored on SPX-TEST) — the tool's v1.3: a tick is bucketed by ev_time (the source's
      event time, ms), ts_epoch only when ev_time is missing. The operator, 2026-10-11 09:23 ET (via QQQ-TEST MSG-QQQ-1011-05):
      "1. Yes, 2. B". R14 and R14b are NEW; R1-R13 are unchanged in code. R6's docstring now says its fixture ticks carry
      NO ev_time, so R6 pins open/high/low/close ordering on the fallback path (its assertions are as before).
v1.1  2026-10-09  OTV4TEST r264 (SEED.3, authored on SPX-TEST) — the tool's v1.2: a complete day with a SOURCE GAP (a minute
      under MIN_TICKS_PER_MINUTE, 0 included) is SKIPPED and not counted toward MIN_VERIFIED_DAYS. R7c is INVERTED (it
      pinned v1.1's refusal); R7d R7e R7f R7g are new. A skipped day's minutes at or above the floor are still compared,
      and a disagreement there FAILS as on any day (QQQ-TEST MSG-1009-16): R7g.
v1.0  2026-10-07  OTV4TEST r261 (SEED.3, authored on SPX-TEST) — the gate for tools/rebuild_1m_from_last_trade.py.
      No network: warehouse_source's own _FakeS3 serves raw/last_trade envelopes, and the scratch feed store is built
      by the REAL data/candle_feed.FeedStore, so the schema is the feed's and not a belief about it (WA §0.4). The
      tool's own constants (MIN_TICKS_PER_MINUTE, BAR_TOLERANCE_*, MIN_VERIFIED_DAYS) are read from the tool, never
      copied, so a fixture cannot drift from what it gates.
  R1  a dry run writes nothing (the store's bytes are identical) and prints the would-insert count
  R2  --apply inserts ONLY the missing minutes; a bar the store already held is NOT changed (its value disagrees
      with the ticks on purpose)
  R2b a bar the FEED writes between the plan and the write wins (INSERT OR IGNORE): the fake bucket inserts the
      09:30 bar into the store while the gap day's ticks are being read, after the store was scanned
  R3  a minute with fewer than MIN_TICKS_PER_MINUTE distinct ticks is refused ("thin"), never written
  R3b DUPLICATE ticks do not count twice: a minute of (floor-1) distinct ticks each pushed twice is still thin
  R4  a --symbol other than the box's instrument is refused (rc 2); an UNSET instrument is refused (rc 2)
  R5  ticks outside 09:30-15:59 ET never make a bar (09:29 and 16:00 ticks present in the fixture)
  R6  a rebuilt bar is open = first tick, high = max, low = min, close = last BY ts_epoch - ticks are served out
      of order across two objects; another symbol's ticks filed in the same object and minute are ignored. (v1.2 of
      this gate: these fixture ticks carry no ev_time, so this is the FALLBACK path's ordering.)
  R7  a complete day whose held bars disagree with the ticks beyond the tolerance refuses --apply (rc 4), nothing
      written, with THREE other days verified (so the refusal is the disagreement's); the dry run prints the FAIL
  R7b the same with the HIGH off beyond BAR_TOLERANCE_HL_PTS (open/close exact): --apply rc 4, nothing written
  R7c ONE minute of one of four complete days under MIN_TICKS_PER_MINUTE (bars exact): that day prints "SKIPPED (source
      gap: 1 minutes, 12:50-12:50 ET)", the other three verify, --apply rc 0 and inserts (v1.1 refused: rc 4)
  R7d a 10-08-shaped hole - 0 ticks for 11:44..11:48 - on one of four complete days: SKIPPED (source gap: 5 minutes,
      11:44-11:48 ET), --apply rc 0 and inserts
  R7e a skipped day does NOT count: three complete days, one with a gap -> 2 verified -> --apply rc 4, "only 2", nothing
      written (kills "skipped counted toward the 3")
  R7f a minute with EXACTLY MIN_TICKS_PER_MINUTE ticks is not a gap: three complete days, one with such a minute -> no
      SKIPPED, 3 verified, --apply rc 0 (kills the threshold off by one, and "skip every day")
  R7g a source gap does not hide a bad bar: the R7d hole AND a 10:10 open 5.00 off on the same day (three others
      verify) -> FAIL, --apply rc 4, nothing written (kills "no comparison on a skipped day")
  R8  fewer than MIN_VERIFIED_DAYS verified complete days refuses --apply (rc 4), nothing written
  R9  the insert log records the date, rows inserted and the thinnest minute's ticks
  R10 a re-run inserts 0
  R11 feed_meta is never touched
  R12 zero last_trade objects listed -> rc 3 with a reason
  R13 a weekend date is never targeted, even with ticks filed under it
  R14 (v1.3) ticks are BUCKETED BY ev_time: on a day the store holds nothing for, two minutes whose ticks carry ev_time
      (ms) with ts_epoch 1.08 s later (09-28's measured lag). The last tick of 10:00 (ev 10:00:59.60, ts 10:01:00.68) is
      a +7.00 spike: it must CLOSE and top 10:00, and 10:01 must open on its own first tick - exactly the bars ev_time
      gives (kills ts bucketing, "fallback always taken", and ev_time read as seconds)
  R14b a tick with NO usable ev_time - the key absent, None, "", or 0.0 (event_time is 0.0 on every SPX row) - is
      bucketed by ts_epoch: 10:10/10:11 are built from such ticks only, a 0.0-ev_time tick is 10:10's +7.00 high, and
      the plan line counts them (kills "fallback removed" and "0.0 taken as a time")
Run: python3 tests/check_rebuild_1m.py      (OT_REBUILD_TOOL=<path> points it at another copy - born-red/mutant runs)
     Needs the venv (FeedStore imports the broker SDK): under an interpreter that cannot, it prints NOT RUN, exit 2.
"""
import atexit
import contextlib
import glob as _glob
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ["OT_INSTRUMENT"] = "SPX"
_SCRATCH = tempfile.mkdtemp(prefix="rb1mchk_")
atexit.register(shutil.rmtree, _SCRATCH, True)
os.environ.setdefault("OT_LOG_FILE", os.path.join(_SCRATCH, "bot.log"))

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def main() -> int:
    print("check_rebuild_1m")
    try:
        import data.candle_feed as cf
    except ImportError as exc:
        print(f"NOT RUN — this interpreter cannot import data.candle_feed ({exc}); run under the venv")
        return 2
    tool_path = os.environ.get("OT_REBUILD_TOOL") or os.path.join(ROOT, "tools", "rebuild_1m_from_last_trade.py")
    try:
        spec = importlib.util.spec_from_file_location("rb_tool", tool_path)
        rb = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rb)
    except Exception as exc:                                    # noqa: BLE001
        check("R0 the tool loads", False, f"{type(exc).__name__}: {exc}")
        print(f"\nRED — {sorted(set(FAILED))}")
        return 1
    import warehouse_source as ws

    FLOOR = rb.MIN_TICKS_PER_MINUTE
    now_ms = int(datetime(2026, 10, 8, 0, 30, tzinfo=timezone.utc).timestamp() * 1000)   # 10-07 20:30 ET
    COMPLETE = ["2026-10-05", "2026-10-06", "2026-10-07"]
    GAP = "2026-10-02"
    WEEKEND = "2026-10-04"
    M = 60_000

    def t0(d):
        return rb.rth_open_ms(d)

    def px(d, m):                                               # a deterministic path per day/minute
        return 7000.0 + (int(d[-2:]) * 10) + m * 0.25

    def ticks_for(d, m, n, base=None):
        """n distinct ticks inside minute m; open base, a +2 spike, a -3 dip, close base+1."""
        b = px(d, m) if base is None else base
        start = t0(d) / 1000 + m * 60
        out = []
        for i in range(n):
            p = b + (2.0 if i == 1 else -3.0 if i == 2 else (1.0 if i == n - 1 else 0.01 * i))
            out.append({"symbol": "SPX", "ts_epoch": start + 0.5 + i * (58.0 / max(n, 1)), "price": round(p, 2)})
        return out

    def held_bar(d, m):                                         # what a correct rebuild of ticks_for(d,m,FLOOR+5) gives
        b = px(d, m)
        return (b, b + 2.0, b - 3.0, b + 1.0)

    def env(d, rows, stamp):
        return json.dumps({"schema_version": 1, "datatype": "last_trade", "symbol": "SPX", "dt": d,
                           "pushed_at_utc": stamp, "record": rows}).encode()

    def build_objs(complete_days, disagree=None, thin_day=None, hole_day=None, exact_day=None):
        objs = {}
        n = 0
        for d in complete_days:
            rows = []
            for m in range(390):
                if d == hole_day and 134 <= m <= 138:           # R7d: 11:44..11:48 ET carry no ticks at all
                    continue
                n_m = FLOOR + 5
                if m == 200 and d == thin_day:
                    n_m = FLOOR - 1                             # R7c/R7e: 12:50 one tick under the floor
                elif m == 200 and d == exact_day:
                    n_m = FLOOR                                 # R7f: 12:50 exactly at the floor
                rows.extend(ticks_for(d, m, n_m))
            half = len(rows) // 2                               # two objects, the later one first (R6 order)
            objs[f"{ws.PREFIX}/last_trade/dt={d}/sym=SPX/{n}-b.json"] = env(d, rows[half:], f"{d}T20:00:00+00:00")
            objs[f"{ws.PREFIX}/last_trade/dt={d}/sym=SPX/{n}-a.json"] = env(d, rows[:half], f"{d}T19:00:00+00:00")
            n += 1
        g = []
        g += ticks_for(GAP, 0, FLOOR + 5)                        # 09:30 missing in store -> inserted
        g += ticks_for(GAP, 5, FLOOR - 1)                        # 09:35 missing, thin -> refused (R3)
        dup = ticks_for(GAP, 6, FLOOR - 1)                       # 09:36 missing, floor-1 distinct, each twice (R3b)
        g += dup + [dict(r) for r in dup]
        g += ticks_for(GAP, 10, FLOOR + 5, base=1.0)             # 09:40 HELD in store with other values (R2)
        g += ticks_for(GAP, 20, FLOOR + 5)[::-1]                 # 09:50 missing, served in REVERSE order (R6)
        pre = t0(GAP) / 1000
        g += [{"symbol": "SPX", "ts_epoch": pre - 30 + i * 0.5, "price": 6999.0} for i in range(FLOOR + 5)]  # 09:29
        g += [{"symbol": "SPX", "ts_epoch": pre + 390 * 60 + i, "price": 6998.0} for i in range(FLOOR + 5)]  # 16:00
        g += [{"symbol": "QQQ", "ts_epoch": pre + 20 * 60 + 1 + i, "price": 600.0} for i in range(FLOOR + 5)]  # other sym, IN the missing 09:50
        objs[f"{ws.PREFIX}/last_trade/dt={GAP}/sym=SPX/9-g.json"] = env(GAP, g, f"{GAP}T20:00:00+00:00")
        objs[f"{ws.PREFIX}/last_trade/dt={WEEKEND}/sym=SPX/9-w.json"] = env(
            WEEKEND, ticks_for(WEEKEND, 0, FLOOR + 5), f"{WEEKEND}T20:00:00+00:00")
        return objs

    def build_store(tag, complete_days, disagree_day=None, field="o"):
        d = tempfile.mkdtemp(prefix=f"store_{tag}_", dir=_SCRATCH)
        db = os.path.join(d, "feed_store.db")
        fs = cf.FeedStore(db)                                   # the REAL schema
        rows = []
        for day in complete_days:
            for m in range(390):
                o, h, l, c = held_bar(day, m)
                if day == disagree_day and m == 100:
                    if field == "o":
                        o += 5.0                                # R7: beyond any sane tolerance
                    else:
                        h += 5.0                                # R7b: the high, open/close exact
                rows.append(("SPX", "1m", t0(day) + m * M, o, h, l, c, 0.0))
        for m in range(390):                                    # GAP day: everything held except 0, 5, 6, 20
            if m in (0, 5, 6, 20):
                continue
            v = (1.0, 1.0, 1.0, 1.0) if m == 10 else held_bar(GAP, m)
            rows.append(("SPX", "1m", t0(GAP) + m * M) + v + (0.0,))
        fs.conn.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", rows)
        fs.conn.execute("INSERT INTO feed_meta (symbol, interval, last_write_epoch) VALUES ('SPX','1m',123.0)")
        fs.conn.commit()
        fs.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        fs.conn.close()
        return db

    def go(db, *argv, objs, log=None):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = rb.run(["--db", db] + list(argv), s3=ws._FakeS3(objs), now_ms=now_ms,
                        log_path=log or os.path.join(os.path.dirname(db), "rebuild_1m.log"))
        return rc, buf.getvalue()

    def md5(db):
        h = hashlib.md5()
        for p in (db, db + "-wal"):
            if os.path.exists(p):
                h.update(open(p, "rb").read())
        return h.hexdigest()

    def bars(db, d):
        c = sqlite3.connect(db)
        out = {(ts - t0(d)) // M: (o, h, l, cl) for ts, o, h, l, cl in c.execute(
            "SELECT ts_epoch_ms, open, high, low, close FROM candles WHERE symbol='SPX' AND interval='1m' "
            "AND ts_epoch_ms >= ? AND ts_epoch_ms < ?", (t0(d) - 60 * M, t0(d) + 400 * M))}
        c.close()
        return out

    objs = build_objs(COMPLETE)

    # R1 — dry run
    db = build_store("main", COMPLETE)
    h0 = md5(db)
    rc, out = go(db, objs=objs)
    check("R1 dry run: rc 0, store bytes unchanged, would insert 2 on the gap day",
          rc == 0 and md5(db) == h0 and f"{GAP}: held 386, missing 4, would insert 2" in out,
          f"rc={rc} same={md5(db) == h0}\n{out[-1500:]}")

    # R2/R3/R3b/R5/R6/R9/R11 — apply
    log = os.path.join(os.path.dirname(db), "rebuild_1m.log")
    rc, out = go(db, "--apply", objs=objs, log=log)
    b = bars(db, GAP)
    want0 = held_bar(GAP, 0)
    want20 = held_bar(GAP, 20)
    check("R2 apply inserts only the missing minutes; the held 09:40 bar is unchanged",
          rc == 0 and 0 in b and 20 in b and b.get(10) == (1.0, 1.0, 1.0, 1.0),
          f"rc={rc} keys0/20={0 in b}/{20 in b} held10={b.get(10)}\n{out[-1500:]}")
    check("R3 a thin minute (floor-1 ticks) is refused, never written", 5 not in b, f"09:35={b.get(5)}")
    check("R3b duplicate ticks do not lift a minute over the floor", 6 not in b, f"09:36={b.get(6)}")
    check("R5 09:29 and 16:00 ticks never make a bar", -1 not in b and 390 not in b,
          f"09:29={b.get(-1)} 16:00={b.get(390)}")
    check("R6 open=first, high=max, low=min, close=last by ts_epoch (out-of-order and reversed objects)",
          b.get(0) == want0 and b.get(20) == want20, f"09:30 {b.get(0)} want {want0}; 09:50 {b.get(20)} want {want20}")
    logtxt = open(log).read() if os.path.exists(log) else ""
    check("R9 the insert log names the date, rows inserted and the thinnest minute",
          f" {GAP} inserted=2 " in logtxt and f"min_ticks={FLOOR + 5}" in logtxt, repr(logtxt[-300:]))
    c = sqlite3.connect(db)
    fm = c.execute("SELECT last_write_epoch FROM feed_meta WHERE symbol='SPX' AND interval='1m'").fetchone()
    c.close()
    check("R11 feed_meta untouched", fm == (123.0,), f"{fm}")

    # R2b — the feed writes the 09:30 bar mid-run; its row must win
    dbr = build_store("race", COMPLETE)

    class _RaceS3(ws._FakeS3):
        def get_object(self, Bucket, Key):
            if f"dt={GAP}/" in Key:
                c = sqlite3.connect(dbr)
                c.execute("INSERT OR IGNORE INTO candles VALUES ('SPX','1m',?,42,42,42,42,0)", (t0(GAP),))
                c.commit()
                c.close()
            return super().get_object(Bucket, Key)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = rb.run(["--db", dbr, "--apply"], s3=_RaceS3(objs), now_ms=now_ms,
                    log_path=os.path.join(os.path.dirname(dbr), "rebuild_1m.log"))
    br = bars(dbr, GAP)
    check("R2b a bar the feed wrote mid-run is kept, never overwritten", rc == 0 and br.get(0) == (42, 42, 42, 42),
          f"rc={rc} 09:30={br.get(0)}\n{buf.getvalue()[-600:]}")

    # R10 — re-run
    rc, out = go(db, "--apply", objs=objs, log=log)
    check("R10 a re-run inserts 0", rc == 0 and "0 row(s) inserted" in out.splitlines()[-1], out[-400:])

    # R7 — a complete day disagreeing beyond tolerance
    # FOUR complete days, so three still verify and only the disagreement can refuse (MIN_VERIFIED_DAYS is R8's)
    C7 = ["2026-09-30"] + COMPLETE
    objs7 = build_objs(C7)
    db7 = build_store("r7", C7, disagree_day="2026-10-06")
    h7 = md5(db7)
    rc, out = go(db7, objs=objs7)
    dry_fail = "2026-10-06:" in out and "-> FAIL" in out
    rc, out2 = go(db7, "--apply", objs=objs7)
    check("R7 a disagreeing complete day: dry run prints FAIL; --apply rc 4, nothing written",
          dry_fail and rc == 4 and md5(db7) == h7, f"dry_fail={dry_fail} rc={rc}\n{out2[-600:]}")

    # R7b — the HIGH disagrees beyond BAR_TOLERANCE_HL_PTS, everything else exact
    db7b = build_store("r7b", C7, disagree_day="2026-10-06", field="h")
    h7b = md5(db7b)
    rc, out = go(db7b, "--apply", objs=objs7)
    check("R7b a complete day whose HIGH disagrees: --apply rc 4, nothing written",
          rc == 4 and md5(db7b) == h7b and "-> FAIL" in out, f"rc={rc}\n{out[-600:]}")

    # R7c — one minute of a complete day under the tick floor, bars exact: SKIPPED, the other three verify
    objs7c = build_objs(C7, thin_day="2026-10-06")
    db7c = build_store("r7c", C7)
    rc, out = go(db7c, objs=objs7c)
    dry_skip = "2026-10-06: SKIPPED (source gap: 1 minutes, 12:50-12:50 ET)" in out
    rc, out2 = go(db7c, "--apply", objs=objs7c)
    check("R7c a complete day with one thin minute is SKIPPED; three verify; --apply rc 0 and inserts",
          dry_skip and rc == 0 and "2 row(s) inserted" in out2.splitlines()[-1]
          and "skipped (source gap) 1 ['2026-10-06']" in out2,
          f"dry_skip={dry_skip} rc={rc}\n{out[-700:]}\n{out2[-700:]}")

    # R7d — the 10-08 shape: 0 ticks for five minutes of a complete day
    objs7d = build_objs(C7, hole_day="2026-10-06")
    db7d = build_store("r7d", C7)
    rc, out = go(db7d, "--apply", objs=objs7d)
    check("R7d a 0-tick hole 11:44-11:48 on a complete day: SKIPPED (5 minutes), --apply rc 0 and inserts",
          rc == 0 and "2026-10-06: SKIPPED (source gap: 5 minutes, 11:44-11:48 ET)" in out
          and "2 row(s) inserted" in out.splitlines()[-1], f"rc={rc}\n{out[-900:]}")

    # R7e — a skipped day does not count: 2 verified + 1 skipped refuses
    objs7e = build_objs(COMPLETE, thin_day="2026-10-06")
    db7e = build_store("r7e", COMPLETE)
    h7e = md5(db7e)
    rc, out = go(db7e, "--apply", objs=objs7e)
    check("R7e a skipped day plus 2 verified: --apply rc 4 (\"only 2\"), nothing written",
          rc == 4 and md5(db7e) == h7e and "SKIPPED" in out and "only 2 complete day(s) verified" in out,
          f"rc={rc}\n{out[-700:]}")

    # R7f — exactly MIN_TICKS_PER_MINUTE ticks is not a gap
    objs7f = build_objs(COMPLETE, exact_day="2026-10-06")
    db7f = build_store("r7f", COMPLETE)
    rc, out = go(db7f, "--apply", objs=objs7f)
    check("R7f a minute at exactly the floor is not a gap: no SKIPPED, 3 verified, --apply rc 0",
          rc == 0 and "SKIPPED" not in out and "verified 3 day(s)" in out, f"rc={rc}\n{out[-700:]}")

    # R7g — a gap day with a bad bar elsewhere still FAILS
    db7g = build_store("r7g", C7, disagree_day="2026-10-06")
    h7g = md5(db7g)
    rc, out = go(db7g, "--apply", objs=objs7d)
    check("R7g a gap day with a bar 5.00 off elsewhere: FAIL, --apply rc 4, nothing written",
          rc == 4 and md5(db7g) == h7g and "-> FAIL (source gap: 5 minutes, 11:44-11:48 ET)" in out
          and "SKIPPED" not in out, f"rc={rc}\n{out[-900:]}")

    # R8 — too few verified days
    db8 = build_store("r8", COMPLETE)
    h8 = md5(db8)
    objs8 = build_objs(COMPLETE[1:])                            # 10-05 complete in store, no ticks for it
    rc, out = go(db8, "--apply", objs=objs8)
    check(f"R8 only {rb.MIN_VERIFIED_DAYS - 1} verified day(s): --apply rc 4, nothing written",
          rc == 4 and md5(db8) == h8 and "not verifiable" in out, f"rc={rc}\n{out[-600:]}")

    # R4 — symbol
    rc, out = go(db8, "--symbol", "QQQ", objs=objs)
    ok_sym = rc == 2 and "REFUSED" in out
    from utils import instrument as _instr
    _real = _instr.box_instrument
    _instr.box_instrument = lambda: _instr.UNSET
    try:
        rc2, out2 = go(db8, objs=objs)
    finally:
        _instr.box_instrument = _real
    check("R4 a foreign --symbol and an UNSET instrument are refused (rc 2)", ok_sym and rc2 == 2,
          f"sym rc={rc} unset rc={rc2}\n{out}{out2}")

    # R12 — nothing listed
    rc, out = go(db8, objs={})
    check("R12 zero last_trade objects listed -> rc 3", rc == 3 and "FAILED" in out, f"rc={rc}\n{out[-400:]}")

    # R13 — weekend never targeted
    rc, out = go(db8, objs=objs)
    check("R13 a weekend date with ticks is never targeted", f"{WEEKEND}:" not in out, out[-800:])

    # R14 / R14b (v1.3) — ev_time bucketing, and the ts_epoch fallback
    EVD = "2026-10-01"                                          # in the window, nothing held: every minute a target
    LAG = 1.08

    def ev_minute(m, base, spike_last):
        n = FLOOR + 5
        start = t0(EVD) / 1000 + m * 60
        out = []
        for i in range(n):
            ev = start + 0.05 + i * (59.55 / (n - 1))           # 0.05 .. 59.60 s into the minute
            p = base + (7.0 if (spike_last and i == n - 1) else 0.01 * i)
            out.append({"symbol": "SPX", "ts_epoch": round(ev + LAG, 3), "ev_time": round(ev * 1000.0, 1),
                        "price": round(p, 2)})
        return out

    FORMS = ("absent", None, "", 0.0)

    def fb_minute(m, base, spike_zero):
        n = FLOOR + 5
        start = t0(EVD) / 1000 + m * 60
        out = []
        for i in range(n):
            r = {"symbol": "SPX", "ts_epoch": round(start + 0.3 + i * (59.0 / (n - 1)), 3)}
            form = FORMS[i % len(FORMS)]
            p = base + 0.01 * i
            if spike_zero and i == 3:                           # i % 4 == 3 -> ev_time 0.0, the high
                p = base + 7.0
            if form != "absent":
                r["ev_time"] = form
            r["price"] = round(p, 2)
            out.append(r)
        return out

    e0, e1 = 7100.0, 7100.5
    ev_rows = ev_minute(30, e0, True) + ev_minute(31, e1, False)
    f0, f1 = 7200.0, 7200.5
    fb_rows = fb_minute(40, f0, True) + fb_minute(41, f1, False)
    objs14 = dict(build_objs(COMPLETE))
    objs14[f"{ws.PREFIX}/last_trade/dt={EVD}/sym=SPX/7-e.json"] = env(EVD, ev_rows[::-1] + fb_rows, f"{EVD}T20:00:00+00:00")

    def want_bar(rows, m, key):
        lo, hi = t0(EVD) / 1000 + m * 60, t0(EVD) / 1000 + (m + 1) * 60
        sel = sorted((key(r), r["price"]) for r in rows if lo <= key(r) < hi)
        ps = [x[1] for x in sel]
        return (ps[0], max(ps), min(ps), ps[-1]) if ps else None

    by_ev = lambda r: r["ev_time"] / 1000.0
    w30, w31 = want_bar(ev_rows, 30, by_ev), want_bar(ev_rows, 31, by_ev)
    db14 = build_store("r14", COMPLETE)
    rc, out = go(db14, "--apply", objs=objs14)
    b14 = bars(db14, EVD)
    check("R14 ticks are bucketed by ev_time: 10:00 closes and tops on the boundary spike, 10:01 opens on its own tick",
          rc == 0 and b14.get(30) == w30 and b14.get(31) == w31 and w30[3] == e0 + 7.0 and w31[0] == e1,
          f"rc={rc} 10:00 {b14.get(30)} want {w30}; 10:01 {b14.get(31)} want {w31}\n{out[-900:]}")
    by_ts = lambda r: r["ts_epoch"]
    v40, v41 = want_bar(fb_rows, 40, by_ts), want_bar(fb_rows, 41, by_ts)
    n_fb = len(fb_rows)
    check("R14b a tick with no usable ev_time (absent / None / \"\" / 0.0) is bucketed by ts_epoch, and counted",
          rc == 0 and b14.get(40) == v40 and b14.get(41) == v41 and v40[1] == f0 + 7.0
          and f"; {n_fb} tick(s) without ev_time bucketed by ts_epoch" in out,
          f"rc={rc} 10:10 {b14.get(40)} want {v40}; 10:11 {b14.get(41)} want {v41}\n{out[-900:]}")

    print()
    if FAILED:
        print(f"RED — {len(set(FAILED))} failed: {' '.join(sorted(set(FAILED)))}")
        return 1
    print("GREEN — every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
