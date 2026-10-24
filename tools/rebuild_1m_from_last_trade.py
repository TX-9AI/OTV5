#!/usr/bin/env python3
"""
tools/rebuild_1m_from_last_trade.py  v1.4
v1.4  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.3  2026-10-11  OTV4TEST r267 (SEED.3, authored on SPX-TEST) — A TICK IS BUCKETED BY ITS SOURCE TIME (ev_time), NOT BY
      WHEN THE BOX RECEIVED IT (ts_epoch). The operator, 2026-10-11 09:23 ET (relayed by QQQ-TEST, MSG-QQQ-1011-05):
      "1. Yes, 2. B" - (1) bucket on ev_time, ts_epoch only when ev_time is missing; (2) the 453 minutes v1.2 already
      wrote are NOT re-derived: they age out of the 1m window. WHY: ts_epoch is the receiving box's time.time()
      (data/candle_feed.py _on_trade) and runs 0.07-1.08 s behind ev_time on a per-day plateau, with rare bursts to
      ~40 s (measured 2026-10-11 on the 29 SEED.3 days, /var/tmp/spx_t2b_1011). The feed's candles are cut on event
      time, so a tick with ev_time 10:29:59.021 and ts_epoch 10:30:00.113 closed the feed's 10:15 15m bar but opened
      v1.2's 10:30 1m bar - check_level_tape T2b found 2 such 15m bars on 09-28 narrower than their minutes. Under
      ev_time 453 of v1.2's 2,258 inserted minutes would differ (max |dO| 1.20 |dH| 0.49 |dL| 0.45 |dC| 1.12) and T2b
      reads 0 narrower on all 29 days. ev_time is epoch MILLISECONDS; a missing, empty, non-numeric or non-positive
      ev_time (event_time is 0.0 on every SPX row, so 0 is "absent", not 1970) falls back to ts_epoch, and the day's
      fallback count is printed. The insert log gains bucket=ev_time so a v1.3 row can be told from a v1.2 one.
      Dedupe, the window, the floor, HL 1.00, OC 3.00 and the 3 verified days are unchanged.
v1.2  2026-10-09  OTV4TEST r264 (SEED.3, authored on SPX-TEST) — A COMPLETE DAY WITH A SOURCE GAP IS SKIPPED, NOT COUNTED;
      A BAD BAR ON ITS OTHER MINUTES STILL FAILS THE RUN.
      The operator, 2026-10-09 20:28 ET (SPX-TEST's thread): "Yes, fill in the missing bars"; QQQ-TEST MSG-1009-15:
      build. WHY: SPX's last_trade stream went silent 11:44:26-11:48:38 ET on 10-08 on this box AND in the warehouse
      (QQQ's had no gap: a source-side hole). 10-08's held bars are complete, so v1.1 verified it, found minutes under
      MIN_TICKS_PER_MINUTE and refused every --apply until 10-08 aged out of the 1m window (~20 days). NOW a complete day
      with any RTH minute under MIN_TICKS_PER_MINUTE (0 ticks included) prints "SKIPPED (source gap: N minutes,
      HH:MM-HH:MM ET)" and does NOT count toward MIN_VERIFIED_DAYS - but every minute it DOES hold at or above the floor
      is still compared, and an HL > 1.00 or OC > 3.00 disagreement FAILS the run as on any day (QQQ-TEST MSG-1009-16,
      the controller's call: "a source gap must not hide a real bad bar"). HL 1.00, OC 3.00, the 30-tick floor on
      inserted minutes and the 3 verified days are unchanged.
v1.1  2026-10-08  OTV4TEST r262 (SEED.3) — BAR_TOLERANCE_OC_PTS 1.00 -> 3.00, BY HIS RULING. The operator, 2026-10-08 16:40 ET:
      "Yes, to all" (QQQ-TEST's recommendation of 3.00, 10-07: the 10-06 15:50 open is off 2.49 because last_trade never
      carried the value the feed's bar opened at). High/low (1.00), the tick floor (30) and the 3 verified days are unchanged.
v1.0  2026-10-07  OTV4TEST r261 (SEED.3, authored on SPX-TEST) — THE SEED GAPS ARE REBUILT FROM THE INDEX'S OWN TICKS,
      ONLY WHERE THE STORE HAS NO BAR. The operator, 2026-10-07 19:35 ET: "Let's re-seed"; told a re-seed cannot
      work, 20:17 ET: "Yes" (to bringing this to QQQ-TEST, who asked for it built and gated: MSG-1007-12).
      WHY A RE-SEED CANNOT: seed_candles v1.1 (r237) refuses a bar pushed before it closed, and mainline's pusher
      shipped ~1 in 5 1m bars only at its first ~30 s and never again (CNDL.1 history). The 10-04 repair deleted
      those 2,722 partial SPX bars, so every seeded day 08-14..10-02 holds 312 of 390 RTH 1m bars - one per 5m
      bucket, nearly always its first minute (census 2026-10-07, /var/tmp/spx_seedgap_1007). The re-seed dry run
      10-07 would insert 0 and rejects exactly 2,722 as partial.
      WHAT IT DOES. Reads raw/last_trade for THE BOX'S instrument through tests/warehouse_source.stream_series
      (the one reader, WA §36a/§38.1; rows folded as they arrive, never accumulated) and builds each RTH minute's
      bar from its ticks: open = first price, high = max, low = min, close = last, by the tick's ev_time (v1.3;
      ts_epoch only when ev_time is missing).
      Volume is 0.0 - an index has none, and the seeded/feed bars carry 0.0 too.
      It writes a minute ONLY where the store has no 1m row (INSERT OR IGNORE; a held bar is never changed),
      only on a trading day (utils.market_calendar), only 09:30-15:59 ET, only within RETENTION_DAYS['1m']
      (imported: an older row would be purged that night), only with at least MIN_TICKS_PER_MINUTE distinct ticks,
      and only if the bar passes the feed's poison rule. feed_meta is never touched (a rebuild of old bars is not
      fresh). Each rebuilt day is logged to logs/rebuild_1m.log (date, minutes inserted, the thinnest minute's
      ticks): the candles table has no provenance column, so this log is how a rebuilt bar is traced afterwards.
      BEFORE --apply IT PROVES ITSELF: every COMPLETE held day (all 390 RTH 1m bars present) inside the window is
      rebuilt from its ticks and compared bar for bar with the store; a high/low off by more than BAR_TOLERANCE_HL_PTS
      or an open/close off by more than BAR_TOLERANCE_OC_PTS refuses the apply. A complete day with a minute under
      MIN_TICKS_PER_MINUTE ticks is SKIPPED (v1.2; it refused before) and does not count; its minutes at or above the
      floor are still compared, and a disagreement there refuses as on any day. A complete day the
      warehouse has no ticks for is printed as "not verifiable" and does not count; fewer than MIN_VERIFIED_DAYS
      verified days refuses the apply. The comparison is printed on every run, dry or not.
      DRY RUN BY DEFAULT (the store is opened read-only).
      FAILS LOUDLY, non-zero and named: no instrument; a disagreeing --symbol; the store missing or with no candles
      table; AWS credentials not resolving (a boolean, WA §38.7); the warehouse unreadable; zero objects listed.

THE NUMBERS, WITH THEIR BASIS (measured 2026-10-07 on SPX, warehouse raw/last_trade vs this box's held 1m bars):
  MIN_TICKS_PER_MINUTE = 30   every RTH minute of 10-05/10-06/10-07/09-23 had ticks; the thinnest held 54-58
                              (median 60, ~1/s). Half the normal rate is a thin minute, refused rather than guessed.
  BAR_TOLERANCE_HL_PTS = 1.00 high/low. 1,170 bars on 10-05..10-07: max |dH| 0.47, max |dL| 0.63 (~0.008% of
                              price); an extreme is robust to which minute a boundary tick lands in.
  BAR_TOLERANCE_OC_PTS = 3.00 open/close - RULED 2026-10-08 (r262; was 1.00). The same 1,170 bars: max |dO| 2.49, |dC| 0.79; 1,169 within
                              0.79. The 2.49 is 10-06 15:50: the feed's bar opened 7823.13, a value at the minute mark
                              that last_trade never carried (its ticks: 7823.09 at -0.7 s, 7820.64 at +1.5 s; the
                              sequence numbers show no tick missing; ev_time orders them the same). An open/close is
                              one tick, so it is off by whatever moved in ~1 s around the boundary. At 1.00 the
                              verification failed on 10-06 and --apply refused; 3.00 clears it (2.49).
  MIN_VERIFIED_DAYS    = 3    the three complete days the box has (10-05, 10-06, 10-07).

Run:   python3 tools/rebuild_1m_from_last_trade.py                       (dry run, full 1m depth)
       python3 tools/rebuild_1m_from_last_trade.py --date 2026-09-23     (one date)
       python3 tools/rebuild_1m_from_last_trade.py --apply               (WRITES - the operator's yes first)
Gate:  tests/check_rebuild_1m.py
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

import warehouse_source as ws                                   # noqa: E402  the ONE reader
from utils import instrument as _instr                          # noqa: E402
from utils import paths as _paths                               # noqa: E402
from utils.market_calendar import is_trading_day                # noqa: E402
from warehouse.retention_purge import RETENTION_DAYS            # noqa: E402

MIN_TICKS_PER_MINUTE = 30
BAR_TOLERANCE_HL_PTS = 1.00
BAR_TOLERANCE_OC_PTS = 3.00                                     # r262: his ruling 2026-10-08 (was 1.00)
MIN_VERIFIED_DAYS = 3

IV = "1m"
MIN_MS = 60_000
DAY_MS = 86_400_000
RTH_MINUTES = 390                                               # 09:30 .. 15:59 ET
# data/candle_feed.py's poison window, mirrored as seed_candles does (that module pulls in the broker SDK).
TS_MS_MIN = 1_262_304_000_000
TS_MAX_AHEAD_MS = 172_800_000
LOG_PATH = os.path.join(ROOT, "logs", "rebuild_1m.log")


class Refused(Exception):
    """A named reason not to run. rc 2."""


def _et():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("America/New_York")
    except Exception:                                           # noqa: BLE001
        return None


def rth_open_ms(d: str) -> int:
    """09:30 ET on date d, in epoch ms (DST-correct)."""
    y, m, dd = (int(x) for x in d.split("-"))
    return int(datetime(y, m, dd, 9, 30, tzinfo=_et()).timestamp() * 1000)


def _creds_resolve() -> bool:
    try:
        import boto3
        return boto3.Session().get_credentials() is not None
    except Exception:                                           # noqa: BLE001
        return False


def _dates(date, days, now_ms):
    if date:
        return [ws._valid(date)]
    today = datetime.fromtimestamp(now_ms / 1000, _et() or timezone.utc).date()
    return [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def held_minutes(conn, sym, d) -> dict:
    """{minute index 0..389: (o, h, l, c)} of the store's RTH 1m bars on d."""
    t0 = rth_open_ms(d)
    out = {}
    for ts, o, h, l, c in conn.execute(
            "SELECT ts_epoch_ms, open, high, low, close FROM candles WHERE symbol=? AND interval=? "
            "AND ts_epoch_ms >= ? AND ts_epoch_ms < ?", (sym, IV, t0, t0 + RTH_MINUTES * MIN_MS)):
        if (ts - t0) % MIN_MS == 0:
            out[(ts - t0) // MIN_MS] = (o, h, l, c)
    return out


def _event_s(r):
    """v1.3: the tick's SOURCE time in epoch seconds - ev_time (ms) - or None when it is missing, empty,
    non-numeric or not positive (event_time is 0.0 on every SPX row; a 0 is absent, never 1970)."""
    try:
        e = float(r.get("ev_time"))
    except (TypeError, ValueError):
        return None
    return e / 1000.0 if e > 0 else None


def fold_day(sym, d, s3, meta, fallback=None):
    """Stream one date's last_trade for sym into {minute: [first, high, low, last, n]}. Ticks are de-duplicated
    on (ts_epoch, price) - an object can be re-pushed - and BUCKETED AND ORDERED BY ev_time (v1.3), ts_epoch
    only for a tick whose ev_time is missing. `fallback`, a dict, receives {"n": ticks that fell back}."""
    t0 = rth_open_ms(d) / 1000.0
    seen = set()
    bars = {}
    fb = 0
    for r in ws.stream_series("last_trade", [d], symbols={sym}, s3=s3, meta=meta):
        if r.get("symbol", sym) != sym:
            continue
        try:
            ts = float(r.get("ts_epoch"))
            p = float(r.get("price"))
        except (TypeError, ValueError):
            continue
        t = _event_s(r)
        missing = t is None
        if missing:
            t = ts
        if not (p > 0) or not (t0 <= t < t0 + RTH_MINUTES * 60):
            continue
        if (ts, p) in seen:
            continue
        seen.add((ts, p))
        fb += missing
        m = int((t - t0) // 60)
        b = bars.get(m)
        if b is None:
            bars[m] = [t, p, p, p, t, p, 1]                     # first_t, open, high, low, last_t, close, n
        else:
            if t < b[0]:
                b[0], b[1] = t, p
            if t >= b[4]:
                b[4], b[5] = t, p
            b[2] = max(b[2], p)
            b[3] = min(b[3], p)
            b[6] += 1
    if fallback is not None:
        fallback["n"] = fb
    return {m: (b[1], b[2], b[3], b[5], b[6]) for m, b in bars.items()}


def _hhmm(m: int) -> str:
    """Minute index 0..389 as HH:MM ET (09:30 + m)."""
    return f"{(570 + m) // 60:02d}:{(570 + m) % 60:02d}"


def _poison_ok(ts, o, h, l, c, max_ms) -> bool:
    return TS_MS_MIN <= ts <= max_ms and min(o, h, l, c) > 0


def run(argv=None, s3=None, now_ms=None, log_path=None) -> int:
    ap = argparse.ArgumentParser(description="Rebuild MISSING RTH 1m bars for this box's instrument from the "
                                             "warehouse's last_trade ticks (INSERT OR IGNORE).")
    ap.add_argument("--apply", action="store_true", help="WRITE the missing rows (default: dry run)")
    ap.add_argument("--symbol", help="must equal the box's instrument")
    ap.add_argument("--date", help="one date (YYYY-MM-DD) to rebuild (verification still uses every complete day)")
    ap.add_argument("--db", help="feed store path (default: utils.paths.feed_db_path())")
    a = ap.parse_args(argv)
    now_ms = int(now_ms if now_ms is not None else time.time() * 1000)
    log_path = log_path or LOG_PATH
    try:
        box = _instr.box_instrument()
        if box == _instr.UNSET:
            raise Refused("this box's instrument is UNSET (no OT_INSTRUMENT here or in the bot unit)")
        sym = box
        if a.symbol and a.symbol.strip().upper() != box:
            raise Refused(f"--symbol {a.symbol} is not this box's instrument ({box})")
        depth = RETENTION_DAYS.get(IV)
        if not depth:
            raise Refused(f"RETENTION_DAYS has no finite depth for {IV} ({RETENTION_DAYS})")
        db = a.db or _paths.feed_db_path()
        if not os.path.isfile(db):
            raise Refused(f"feed store not found: {db}")
        ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)
        if not ro.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='candles'").fetchone():
            raise Refused(f"no candles table in {db}")
        if s3 is None:
            if not _creds_resolve():
                raise Refused("AWS credentials do not resolve on this box (checked as a boolean)")
            s3 = ws.client()
    except Refused as exc:
        print(f"REFUSED: {exc}")
        return 2

    cutoff_ms = now_ms - depth * DAY_MS
    window = [d for d in _dates(None, depth, now_ms)
              if is_trading_day(datetime.strptime(d, "%Y-%m-%d").date()) and rth_open_ms(d) >= cutoff_ms
              and rth_open_ms(d) + RTH_MINUTES * MIN_MS <= now_ms]
    held = {d: held_minutes(ro, sym, d) for d in window}
    complete = [d for d in window if len(held[d]) == RTH_MINUTES]
    targets = [d for d in window if len(held[d]) < RTH_MINUTES]
    if a.date:
        want = ws._valid(a.date)
        targets = [d for d in targets if d == want]
    print(f"rebuild_1m_from_last_trade v1.3 - {sym} {IV}, window {window[0] if window else '-'}..{window[-1] if window else '-'} "
          f"({len(window)} trading day(s)), {len(complete)} complete, {len(targets)} with gaps; store {db}; "
          f"{'APPLY' if a.apply else 'DRY RUN (read-only)'}; MIN_TICKS_PER_MINUTE {MIN_TICKS_PER_MINUTE}, "
          f"BAR_TOLERANCE_HL_PTS {BAR_TOLERANCE_HL_PTS:.2f}, BAR_TOLERANCE_OC_PTS {BAR_TOLERANCE_OC_PTS:.2f}, "
          f"MIN_VERIFIED_DAYS {MIN_VERIFIED_DAYS}; ticks bucketed by ev_time (ts_epoch if missing)", flush=True)
    meta = ws.Meta(f"last_trade {window[0] if window else '-'}..{window[-1] if window else '-'} sym={sym}")

    # ── 1. VERIFY on every complete held day ───────────────────────────────────
    verified, verify_fail, skipped = [], [], []
    print("VERIFY - every complete held day rebuilt from its ticks and compared with the store:")
    for d in complete:
        l0 = meta.listed
        built = fold_day(sym, d, s3, meta)
        if meta.error:
            break
        if not built:
            print(f"  {d}: not verifiable - the warehouse has no {sym} last_trade ticks "
                  f"({meta.listed - l0} object(s) listed)")
            continue
        thin = [m for m in range(RTH_MINUTES) if built.get(m, (0, 0, 0, 0, 0))[4] < MIN_TICKS_PER_MINUTE]
        worst = [0.0, 0.0, 0.0, 0.0]
        for m, (o, h, l, c) in held[d].items():
            b = built.get(m)
            if b is None or b[4] < MIN_TICKS_PER_MINUTE:            # v1.2: a gap minute is never compared
                continue
            for i, (x, y) in enumerate(zip((o, h, l, c), b[:4])):
                worst[i] = max(worst[i], abs(x - y))
        bad = max(worst[1], worst[2]) > BAR_TOLERANCE_HL_PTS or max(worst[0], worst[3]) > BAR_TOLERANCE_OC_PTS
        gap = (f"source gap: {len(thin)} minutes, {_hhmm(thin[0])}-{_hhmm(thin[-1])} ET" if thin else "")
        diffs = (f"max |dO| {worst[0]:.2f} |dH| {worst[1]:.2f} |dL| {worst[2]:.2f} |dC| {worst[3]:.2f}")
        if thin and not bad:                                    # v1.2: skipped, never counted toward the 3
            print(f"  {d}: SKIPPED ({gap}) - {len(built)}/{RTH_MINUTES} minutes with ticks, {len(thin)} under "
                  f"{MIN_TICKS_PER_MINUTE}; the rest agree ({diffs}); not counted toward {MIN_VERIFIED_DAYS}")
            skipped.append(d)
            continue
        print(f"  {d}: {len(built)}/{RTH_MINUTES} minutes with ticks, thinnest "
              f"{min((b[4] for b in built.values()), default=0)} tick(s); {diffs} -> {'FAIL' if bad else 'ok'}"
              + (f" ({gap})" if thin else ""))
        (verify_fail if bad else verified).append(d)
    if meta.error:
        print(meta.banner())
        print("FAILED: the warehouse could not be read - nothing was written")
        return 3

    # ── 2. PLAN the missing minutes ────────────────────────────────────────────
    max_ms = now_ms + TS_MAX_AHEAD_MS
    plan = {}
    print("PLAN - missing RTH minutes per day:")
    for d in targets:
        fbk = {}
        built = fold_day(sym, d, s3, meta, fallback=fbk)
        if meta.error:
            break
        t0 = rth_open_ms(d)
        missing = [m for m in range(RTH_MINUTES) if m not in held[d]]
        rows, thin, none, poison = [], 0, 0, 0
        min_n = None
        for m in missing:
            b = built.get(m)
            if b is None:
                none += 1
                continue
            o, h, l, c, n = b
            if n < MIN_TICKS_PER_MINUTE:
                thin += 1
                continue
            ts = t0 + m * MIN_MS
            if not _poison_ok(ts, o, h, l, c, max_ms):
                poison += 1
                continue
            rows.append((sym, IV, ts, o, h, l, c, 0.0))
            min_n = n if min_n is None else min(min_n, n)
        plan[d] = (rows, min_n)
        print(f"  {d}: held {len(held[d])}, missing {len(missing)}, "
              f"{'to insert' if a.apply else 'would insert'} {len(rows)}; refused: no ticks {none}, "
              f"thin {thin}, poison {poison}" + (f"; thinnest inserted minute {min_n} tick(s)" if rows else "")
              + f"; {fbk.get('n', 0)} tick(s) without ev_time bucketed by ts_epoch")
    print(meta.banner())
    if meta.error:
        print("FAILED: the warehouse could not be read - nothing was written")
        return 3
    if meta.listed == 0:
        print("FAILED: the warehouse listed 0 last_trade objects for these dates - nothing to rebuild")
        return 3
    total = sum(len(r) for r, _ in plan.values())
    print(f"TOTAL: {total} minute(s) {'to insert' if a.apply else 'would insert'} on "
          f"{sum(1 for r, _ in plan.values() if r)} day(s); verified {len(verified)} day(s) "
          f"{verified}, failed {len(verify_fail)} {verify_fail}, skipped (source gap) {len(skipped)} {skipped}")
    ro.close()
    if not a.apply:
        print("DRY RUN - nothing written. --apply writes the missing rows (INSERT OR IGNORE).")
        return 0

    # ── 3. APPLY, only if the rebuild proved itself ───────────────────────────
    if verify_fail:
        print(f"REFUSED: the rebuild disagrees with the store on {verify_fail} - nothing written")
        return 4
    if len(verified) < MIN_VERIFIED_DAYS:
        print(f"REFUSED: only {len(verified)} complete day(s) verified (need {MIN_VERIFIED_DAYS}) - nothing written")
        return 4
    rw = sqlite3.connect(db, timeout=30)
    rw.execute("PRAGMA busy_timeout=30000")
    before_all = rw.execute("SELECT COUNT(*) FROM candles WHERE symbol=? AND interval=?", (sym, IV)).fetchone()[0]
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as log:
        for d, (rows, min_n) in plan.items():
            if not rows:
                continue
            b = rw.total_changes
            with rw:                                              # one transaction per day
                rw.executemany("INSERT OR IGNORE INTO candles (symbol, interval, ts_epoch_ms, open, high, low, "
                               "close, volume) VALUES (?,?,?,?,?,?,?,?)", rows)
            n = rw.total_changes - b
            log.write(f"{stamp} {sym} {IV} {d} inserted={n} planned={len(rows)} min_ticks={min_n} "
                      f"source=raw/last_trade bucket=ev_time tol_hl={BAR_TOLERANCE_HL_PTS} tol_oc={BAR_TOLERANCE_OC_PTS} verified={','.join(verified)}\n")
            print(f"  APPLIED {d}: {n} row(s) inserted of {len(rows)} planned")
            if n != len(rows):
                print(f"  ⚠️ {d}: {len(rows) - n} planned row(s) were already present - the feed's rows win")
    after_all = rw.execute("SELECT COUNT(*) FROM candles WHERE symbol=? AND interval=?", (sym, IV)).fetchone()[0]
    rw.close()
    print(f"APPLIED {sym} {IV}: {after_all - before_all} row(s) inserted ({before_all} -> {after_all}); "
          f"logged to {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
