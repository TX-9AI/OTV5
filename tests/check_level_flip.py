#!/usr/bin/env python3
"""
tests/check_level_flip.py  v1.0
A BROKEN LONE LEVEL FLIPS AND WAITS FOR ITS RETEST — RECORD-ONLY (FLIP.1).

v1.0  2026-10-01  OTV4TEST FLIP.1. The operator, 2026-10-01: *"record genuinely
      broken levels as future retest candidates ... every level needs to be
      identified as support or resistance, and when it's broken through, it
      needs to flip"*, with "broken" = accepted by candle closure. His rulings
      the same morning: (1) the existing BREACHED definition; (2) record it any
      way "as long as the flip is recorded"; (3) a ZONE does not flip, it
      retires as before; (4) a flipped level broken AGAIN retires; (5) the
      opening-range TRAVERSED rule applies to flipped levels; (6) the rail
      lock (is_spent) is untouched. RECORD-ONLY: no plan reads a flip until he
      rules one does. Drives the REAL level_book.build() on hand-built tapes and
      the REAL LevelEngine.derive() minute by minute over a scratch feed store
      and a scratch derived store; nothing here opens a live store.

  F1  a lone RESISTANCE accepted through FLIPS to SUPPORT at the bar that
      breached it: id QQQ:flip:support:101.00, flip_of the original, and the
      original leaves the book exactly as before
  F2  record-only in the book: the flip is not in `live`, in any zone, or on
      either side of board()
  F3  the flipped level's retest: wick back to it, close on its new side = HELD
  F4  a second break RETIRES it (ruling 4): BREACHED, in flip_dead, no events
      after, and it never flips back
  F5  a ZONE accepted through never flips (ruling 3)
  F6  a flipped level inside the 09:30-09:34 range retires TRAVERSED at 09:35
      (ruling 5)
  F7  the mirror: a lone SUPPORT flips to RESISTANCE
  F8  the engine writes the flip to level_ledger: kind flip_support, provenance
      'flip', timeframe flip_of:<original>, created at the flip, then retired
      BREACHED by the second break; the original reads BREACHED as before
  F9  level_event carries FLIPPED, FLIP_REJECTED and FLIP_ACCEPTED (kind
      flip_support) and NO REJECTED/ACCEPTED on a flip id; the original's
      ACCEPTED is published once, as before
  F10 every reader a plan trades on is blind to a LIVE flip row: live_levels()
      and board() (non-vacuous: the row is asserted live first)
  F11 the trigger readers are blind: latest_event('REJECTED') and
      latest_rejection() return nothing while FLIP_REJECTED exists
  F12 a flip that flipped AND broke again before the first sync (a restart,
      a gap) is still written to the ledger, retired BREACHED
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# r106 idiom: the lander runs CHECKs under system python3; pandas lives in the venv.
import glob as _glob
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

FAILED, RAN = [], []
H, M = 3_600_000, 60_000
WORK = tempfile.mkdtemp(prefix="chk_lvl_flip-")


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


def ms(y, mo, d, hh, mm=0):
    return int(datetime(y, mo, d, hh, mm, tzinfo=timezone.utc).timestamp() * 1000)


def flat_hours(start_ms, n, px=100.0, wick=0.1):
    return [(start_ms + i * H, px, px + wick, px - wick, px) for i in range(n)]


def flips(b):
    return getattr(b, "flipped", None), getattr(b, "flip_dead", None), getattr(b, "flip_of", None)


# ── the book: one lone level in the 00-08Z block, live at 08Z (04:00 ET) ──────
def _lone(px, side):
    d = ms(2026, 9, 21, 0)
    h1 = flat_hours(d, 8)
    t, o, hi, lo, c = h1[3]
    h1[3] = (t, o, px if side == "resistance" else hi, px if side == "support" else lo, c)
    return h1, d + 8 * H


def _res_tape(t):
    """resistance 101.00: close beyond @1, open beyond @2 (BREACHED -> flip to
    support), the retest wicks 100.95 and closes 101.10 @5 (HELD), close below
    @8, open below @9 (second BREACHED -> retired), then quiet."""
    k = {1: (100.8, 101.3, 100.8, 101.2), 2: (101.25, 101.4, 101.2, 101.3),
         3: (101.3, 101.4, 101.25, 101.3), 4: (101.3, 101.35, 101.2, 101.25),
         5: (101.2, 101.25, 100.95, 101.1), 6: (101.15, 101.3, 101.15, 101.2),
         7: (101.2, 101.25, 101.1, 101.15), 8: (101.1, 101.15, 100.7, 100.8),
         9: (100.75, 100.85, 100.6, 100.7)}
    out = [(t, 100.5, 100.6, 100.4, 100.5)]
    for i in range(1, 14):
        o, h, l, c = k.get(i, (100.7, 100.8, 100.6, 100.7))
        out.append((t + i * M, o, h, l, c))
    return out


def _book_res():
    h1, t = _lone(101.0, "resistance")
    return B.build("QQQ", h1, _res_tape(t), now_ms=t), t


FID_S = "QQQ:flip:support:101.00"
ORIG_R = "QQQ:resistance:101.00"


def _f1():
    b, t = _book_res()
    fl, _fd, of = flips(b)
    ev = [e for e in b.events if e["event"] == "FLIPPED"]
    ok = (fl is not None and of is not None and of.get(FID_S) == ORIG_R
          and len(ev) == 1 and ev[0]["level_ids"] == [FID_S] and ev[0]["side"] == R.SUPPORT
          and (ev[0]["ts"] - t) // M == 2 and ev[0].get("from") == ORIG_R
          and ORIG_R in b.dead and ORIG_R not in b.live)
    return ok, f"FLIPPED {[(e['level_ids'], e['side'], (e['ts'] - t) // M) for e in ev]}; flip_of {of}"


guard("F1 a lone resistance accepted through flips to SUPPORT at the breach bar", _f1)


def _f2():
    h1, t = _lone(101.0, "resistance")
    b = B.build("QQQ", h1, _res_tape(t)[:5], now_ms=t)       # standing at @4: flipped, untested
    fl, _fd, _of = flips(b)
    zs = [m.level_id for z in b.current_zones() for m in z["members"]]
    bd = B.board(b, 101.3)
    on_board = [r for side in ("above", "below") for r in bd[side] if FID_S in r["level_ids"]
                or abs(r["near"] - 101.0) < 1e-9]
    ok = bool(fl) and FID_S in fl and FID_S not in b.live and FID_S not in zs and not on_board
    return ok, f"flipped {sorted(fl or {})}; in live {FID_S in b.live}; zones {zs}; on board {on_board}"


guard("F2 record-only: the flip is not live, not in a zone, not on the board", _f2)


def _f3():
    b, t = _book_res()
    ev = [(e["event"], (e["ts"] - t) // M) for e in b.events if e.get("flip") and FID_S in e["level_ids"]]
    return (("TESTED", 5) in ev and ("HELD", 5) in ev), f"flip events {ev}"


guard("F3 the retest: wick back to the flipped level, close on its new side = HELD", _f3)


def _f4():
    b, t = _book_res()
    fl, fd, _of = flips(b)
    ev = [(e["event"], (e["ts"] - t) // M) for e in b.events if e.get("flip") and FID_S in e["level_ids"]]
    back = [e for e in b.events if e["event"] == "FLIPPED" and e["level_ids"] != [FID_S]]
    ok = (fd is not None and fd.get(FID_S) == t + 9 * M and FID_S not in (fl or {})
          and ev and ev[-1] == ("BREACHED", 9) and not back)
    return ok, f"flip events {ev}; flip_dead {fd}; flipped back {[e['level_ids'] for e in back]}"


guard("F4 a second break RETIRES the flipped level, and it never flips back", _f4)


def _f5():
    d = ms(2026, 9, 21, 0)
    h1 = flat_hours(d, 24, wick=0.3)
    h1[3] = (h1[3][0], 100.0, 101.0, 99.7, 100.0)
    h1[10] = (h1[10][0], 100.0, 101.2, 99.7, 100.0)
    t = d + 24 * H
    b = B.build("QQQ", h1, [(t, 101.1, 101.4, 101.0, 101.3), (t + M, 101.35, 101.5, 101.3, 101.4),
                            (t + 2 * M, 101.4, 101.5, 101.3, 101.4)], now_ms=t)
    fl, _fd, _of = flips(b)
    zb = [e for e in b.events if e["event"] == "BREACHED" and set(e["prices"]) == {101.0, 101.2}]
    # ⚠️ FIXTURE NOTE (first run): the filler sessions' own 100.30 highs are LONE
    # levels these bars also accept through, and they rightly flip — so the
    # check is about the ZONE's members, not "no flip anywhere".
    members = {"QQQ:resistance:101.00", "QQQ:resistance:101.20"}
    fe = [e for e in b.events if e["event"] == "FLIPPED" and e.get("from") in members]
    zf = [f for f in (fl or {}) if f.endswith(":101.00") or f.endswith(":101.20")]
    ok = bool(zb) and fl is not None and not fe and not zf
    return ok, f"zone breached {bool(zb)}; zone-member FLIPPED {len(fe)}; flipped {sorted(fl or {})}"


guard("F5 a ZONE accepted through never flips (ruling 3)", _f5)


def _f6():
    """Overnight high 101.00 (live 04:00 ET), accepted through at 09:00/09:01 ET
    -> flipped support 101.00; the 09:30-09:34 range spans 100.90-101.10, so at
    09:35 the flip retires TRAVERSED."""
    d = ms(2026, 9, 21, 0)
    h1 = flat_hours(d, 13)
    h1[3] = (h1[3][0], 100.0, 101.0, 99.9, 100.0)
    pre = d + 13 * H                                        # 09:00 ET
    m1 = [(pre, 100.8, 101.3, 100.8, 101.2), (pre + M, 101.25, 101.4, 101.2, 101.3)]
    m1 += [(pre + k * M, 101.3, 101.4, 101.25, 101.3) for k in range(2, 30)]
    rth = pre + 30 * M
    m1 += [(rth + k * M, 101.05, 101.1, 100.9 if k == 2 else 101.02, 101.05) for k in range(0, 5)]
    m1 += [(rth + k * M, 101.3, 101.4, 101.25, 101.3) for k in range(5, 8)]
    b = B.build("QQQ", h1, m1, now_ms=rth + 8 * M)
    fl, fd, _of = flips(b)
    tr = [e for e in b.events if e["event"] == "TRAVERSED" and FID_S in e["level_ids"]]
    ok = (fd is not None and fd.get(FID_S) == rth + 5 * M and FID_S in b.traversed
          and FID_S not in (fl or {}) and len(tr) == 1)
    return ok, (f"flip_dead {fd}; traversed {FID_S in b.traversed}; "
                f"TRAVERSED events {len(tr)}")


guard("F6 a flipped level inside the opening range retires TRAVERSED at 09:35 (ruling 5)", _f6)


def _f7():
    h1, t = _lone(99.0, "support")
    tape = [(t, 99.5, 99.6, 99.4, 99.5), (t + M, 99.2, 99.2, 98.7, 98.8),
            (t + 2 * M, 98.75, 98.8, 98.6, 98.7), (t + 3 * M, 98.7, 98.8, 98.6, 98.7)]
    b = B.build("QQQ", h1, tape, now_ms=t)
    fl, _fd, of = flips(b)
    fid = "QQQ:flip:resistance:99.00"
    ok = bool(fl) and fid in fl and fl[fid].side == R.RESISTANCE and of.get(fid) == "QQQ:support:99.00"
    return ok, f"flipped {sorted(fl or {})}"


guard("F7 the mirror: a lone support flips to RESISTANCE", _f7)


# ── the engine, minute by minute, over scratch stores ─────────────────────────
D = ms(2026, 9, 21, 0)                     # Monday (EDT)
RTH = D + 24 * H + 13 * H + 30 * M          # Tuesday 09:30 ET


def _feed_rows():
    rows = []
    for i in range(24 + 13):
        t = D + i * H
        hi = 101.0 if t == D + 24 * H + 10 * H else 100.3     # Tuesday 06:00 ET: the pre-market high
        rows.append(("QQQ", "1h", t, 100.0, hi, 99.7, 100.0, 1.0))
    k = {9: (100.8, 101.3, 100.8, 101.2), 10: (101.25, 101.4, 101.2, 101.3),
         15: (101.2, 101.25, 100.95, 101.1), 20: (101.1, 101.15, 100.7, 100.8),
         21: (100.75, 100.85, 100.6, 100.7)}
    for i in range(0, 30):
        if i in k:
            o, h, l, c = k[i]
        elif i < 9:
            o, h, l, c = 100.5, 100.6, 100.4, 100.5
        elif i < 20:
            o, h, l, c = 101.25, 101.35, 101.15, 101.25
        else:
            o, h, l, c = 100.7, 100.8, 100.6, 100.7
        rows.append(("QQQ", "1m", RTH + i * M, o, h, l, c, 1.0))
    return rows


def _feed(path, rows):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE IF NOT EXISTS candles (symbol TEXT, interval TEXT, ts_epoch_ms INTEGER,"
              " open REAL, high REAL, low REAL, close REAL, volume REAL,"
              " PRIMARY KEY(symbol, interval, ts_epoch_ms))")
    c.executemany("INSERT OR IGNORE INTO candles VALUES (?,?,?,?,?,?,?,?)", rows)
    c.commit()
    c.close()


def _engine():
    import derived.levels as L
    from data.derived_store import DerivedStore
    store = DerivedStore(tempfile.mktemp(dir=WORK, prefix="derived-", suffix=".db"))
    return L, L.LevelEngine(store, "QQQ"), store


def _derive_at(L, eng, k):
    """Stand just after 1m bar k closed: df_1m's [-2] is that bar."""
    import pandas as pd
    L.time.time = lambda: float((RTH + (k + 1) * M) / 1000 + 5)
    idx = pd.to_datetime([RTH + k * M, RTH + (k + 1) * M], unit="ms", utc=True).tz_convert("America/New_York")
    df1 = pd.DataFrame({"open": [100.5] * 2, "high": [100.6] * 2, "low": [100.4] * 2,
                        "close": [100.5] * 2}, index=idx)
    return eng.derive({"symbol": "QQQ", "price": 100.5, "df_1m": df1})


STEPPED = {}


def _stepped():
    """ONE live-shaped run: the feed grows a bar a minute, the engine derives
    once per closed bar. Snapshots taken at 09:47 (flip live, retested) and at
    the end (flip retired)."""
    if STEPPED:
        return STEPPED
    feed = tempfile.mktemp(dir=WORK, prefix="feed-", suffix=".db")
    os.environ["OT_FEED_DB"] = feed
    rows = _feed_rows()
    hours = [r for r in rows if r[1] == "1h"]
    mins = [r for r in rows if r[1] == "1m"]
    _feed(feed, hours)
    L, eng, store = _engine()
    for k in range(0, 30):
        _feed(feed, [mins[k]])
        _derive_at(L, eng, k)
        if k == 17:
            STEPPED["mid_ledger"] = dict((r[0], r[1:]) for r in store.conn.execute(
                "SELECT level_id, kind, provenance, timeframe, created_ts, retired_ts, retired_reason"
                " FROM level_ledger"))
            STEPPED["mid_live_levels"] = store.live_levels("QQQ")
            STEPPED["mid_board"] = eng.board(101.2)
            STEPPED["mid_latest_rej"] = store.latest_event("QQQ", "REJECTED")
            STEPPED["mid_latest_rej2"] = store.latest_rejection("QQQ")
            STEPPED["mid_flip_rej"] = store.latest_event("QQQ", "FLIP_REJECTED")
    STEPPED["ledger"] = dict((r[0], r[1:]) for r in store.conn.execute(
        "SELECT level_id, kind, provenance, timeframe, created_ts, retired_ts, retired_reason FROM level_ledger"))
    STEPPED["events"] = store.conn.execute(
        "SELECT level_id, event, kind, bar_ts FROM level_event ORDER BY ts_epoch, bar_ts").fetchall()
    return STEPPED


def _f8():
    s = _stepped()
    mid, end = s["mid_ledger"], s["ledger"]
    m, e = mid.get(FID_S), end.get(FID_S)
    o = end.get(ORIG_R)
    ok = (m is not None and m[0] == "flip_support" and m[1] == "flip"
          and m[2] == f"flip_of:{ORIG_R}" and abs(m[3] - (RTH + 10 * M) / 1000) < 1e-6
          and m[4] is None
          and e is not None and e[5] == "BREACHED" and abs(e[4] - (RTH + 21 * M) / 1000) < 1e-6
          and o is not None and o[5] == "BREACHED")
    return ok, f"09:47 {m}; end {e}; original {o}"


guard("F8 the engine writes the flip to level_ledger, then retires it on the second break", _f8)


def _f9():
    s = _stepped()
    ev = s["events"]
    flip = [(e[1], e[2], e[3][11:16]) for e in ev if e[0] == FID_S]
    leaked = [e for e in ev if ":flip:" in e[0] and e[1] in ("REJECTED", "ACCEPTED")]
    orig_acc = [e for e in ev if e[0] == ORIG_R and e[1] == "ACCEPTED"]
    want = [("FLIPPED", "flip_support", "09:40"), ("FLIP_REJECTED", "flip_support", "09:45"),
            ("FLIP_ACCEPTED", "flip_support", "09:51")]
    ok = flip == want and not leaked and len(orig_acc) == 1
    return ok, f"flip rows {flip}; leaked {leaked}; original ACCEPTED {len(orig_acc)}"


guard("F9 level_event: FLIPPED / FLIP_REJECTED / FLIP_ACCEPTED, never REJECTED/ACCEPTED on a flip", _f9)


def _f10():
    s = _stepped()
    live_row = s["mid_ledger"].get(FID_S)
    lv = [r["level_id"] for r in s["mid_live_levels"]]
    bd = s["mid_board"]
    on_board = [r for side in ("above", "below") for r in bd.get(side, [])
                if FID_S in str(r) or "flip" in str(r.get("kind", ""))]
    ok = (live_row is not None and live_row[5] is None and FID_S not in lv and not on_board
          and bd.get("state") == "ok")
    return ok, f"flip live in ledger {live_row is not None and live_row[5] is None}; live_levels {lv}; board flip rows {on_board}; state {bd.get('state')}"


guard("F10 live_levels() and board() are blind to a LIVE flip row", _f10)


def _f11():
    s = _stepped()
    fr = s["mid_flip_rej"]
    ok = (fr is not None and fr.get("level_id") == FID_S
          and s["mid_latest_rej"] is None and s["mid_latest_rej2"] is None)
    return ok, (f"FLIP_REJECTED {fr and fr.get('level_id')}; latest REJECTED {s['mid_latest_rej']}; "
                f"latest_rejection {s['mid_latest_rej2']}")


guard("F11 latest_event('REJECTED') and latest_rejection() never return a flip", _f11)


def _f12():
    feed = tempfile.mktemp(dir=WORK, prefix="feedg-", suffix=".db")
    os.environ["OT_FEED_DB"] = feed
    rows = _feed_rows()
    _feed(feed, [r for r in rows if r[1] == "1h" or r[2] <= RTH + 25 * M])
    L, eng, store = _engine()
    _derive_at(L, eng, 25)                                    # first sync AFTER both breaks
    row = store.conn.execute("SELECT kind, retired_reason FROM level_ledger WHERE level_id=?",
                             (FID_S,)).fetchone()
    return (row == ("flip_support", "BREACHED")), f"ledger row {row}"


guard("F12 a flip that flipped and broke again before the first sync is still recorded, retired", _f12)

shutil.rmtree(WORK, ignore_errors=True)
print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
