#!/usr/bin/env python3
"""
tests/check_replay_overwrite.py  v5.0  (OTV4TEST r276: byte-identical with otv4 r486 556bc2c but this line)
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.1  2026-10-12  FEED.9b — A CORRECTION IS TAKEN. v1.0 pinned range as the
  referee, and on its first boot replay the rule refused the vendor's
  correction of CVX's 10-12 daily bar (stored L 211.02 off the tape, 1m low
  213.7501). U11-U13 added; U1-U10 unchanged and still pass.
  U11 an intraday equity bar that gets NARROWER with ~no volume lost (a
      busted print removed) replaces the stored one
  U12 1d is last-write-wins: a correction of the real CVX 10-12 bar is taken
  U13 the refusal log carries the kept and the refused OHLCV
  BORN RED on otv4 eed0069 at U11 U12 U13.
v1.0  2026-10-12  FEED.9 — A HISTORY REPLAY CANNOT SHRINK A BAR WE ALREADY HOLD.

  upsert_candles was INSERT OR REPLACE. DXFeed's replay of 2026-10-08 11:55
  carried only the bar's last ~2 minutes and overwrote the complete live bar
  (QQQ 5m: V 107877 / L 752.39 became V 33808 / L 752.57). Found by OTV4TEST
  (MSG-QQQ-1012-01/02); the same values sit on the mainline QQQ store.

  Drives the REAL FeedStore.upsert_candles on a SCRATCH store:
  U1  a forming bar that grows (volume up, range wider, same open) replaces
      the stored version
  U2  the 10-08 replay slice (the real values) is REFUSED; the stored bar keeps
      V 107877, L 752.39, O 752.833
  U3  a more complete version (our live bar started mid-bar, the vendor's has
      more tape and another open) replaces the stored one
  U4  index bar, volume 0: a close-only update with the same open is taken
  U4b index bar, volume 0: a version with another open and no more range is
      refused (the SPX-TEST case: an hourly bar missing its opening print)
  U5  a bar the store does not hold is inserted
  U6  NULL volume (SQLite stores NaN as NULL) still updates
  U7  an out-of-order live update (an older snapshot of a forming bar
      arriving after a newer one) is refused; the newer bar is kept
  U8  a stored NULL price always yields, so such a bar can still heal
  U9  the real _on_candle rejects a NaN price at the door (it passed `<= 0`)
  U10 a refusal is logged with its symbol and interval, and nothing is logged
      when nothing is refused
  Critiqued by OTV4TEST (MSG-QQQ-1012-06: NULL is sticky, NaN at the door,
  per-key refusal log, out-of-order case).
  BORN RED on otv4 002de2c at U2 U4b U7 U9 U10.

Run:  python3 tests/check_replay_overwrite.py
"""
import logging
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


TS = 1791474900000          # 2026-10-08 11:55 ET


def main():
    from data.candle_feed import FeedStore
    d = tempfile.mkdtemp()
    st = FeedStore(os.path.join(d, "feed_store.db"))

    def put(*rows):
        st.upsert_candles(list(rows))
        st.commit()

    def get(sym, iv="5m", ts=TS):
        return st.conn.execute(
            "SELECT open, high, low, close, volume FROM candles WHERE symbol=? "
            "AND interval=? AND ts_epoch_ms=?", (sym, iv, ts)).fetchone()

    # U1 — the live stream growing a bar
    put(("QQQ", "5m", TS, 752.833, 752.90, 752.42, 752.46, 38386.0))
    put(("QQQ", "5m", TS, 752.833, 752.94, 752.39, 752.91, 107877.0))
    got = get("QQQ")
    check("U1 a growing live bar replaces the stored one",
          got == (752.833, 752.94, 752.39, 752.91, 107877.0), str(got))

    # U2 — the vendor's 10-08 slice
    put(("QQQ", "5m", TS, 752.635, 752.9191, 752.57, 752.91, 33808.0))
    got = get("QQQ")
    check("U2 the 10-08 replay slice is refused",
          got == (752.833, 752.94, 752.39, 752.91, 107877.0), str(got))

    # U3 — our partial bar, then the vendor's complete one
    put(("AMZN", "5m", TS, 258.20, 258.30, 258.135, 257.95, 31097.0))
    put(("AMZN", "5m", TS, 258.38, 258.38, 257.90, 257.95, 63169.0))
    got = get("AMZN")
    check("U3 a more complete version replaces a partial one",
          got == (258.38, 258.38, 257.90, 257.95, 63169.0), str(got))

    # U4 / U4b — an index, volume 0
    put(("SPX", "1h", TS, 7786.36, 7796.28, 7785.90, 7792.56, 0.0))
    put(("SPX", "1h", TS, 7786.36, 7796.28, 7785.90, 7790.00, 0.0))
    got = get("SPX", "1h")
    check("U4 index: a close update with the same open is taken",
          got is not None and got[3] == 7790.00, str(got))
    put(("SPX", "1h", TS, 7789.00, 7796.28, 7785.90, 7790.00, 0.0))
    got = get("SPX", "1h")
    check("U4b index: another open with no more range is refused",
          got is not None and got[0] == 7786.36, str(got))

    # U5 — a new bar
    put(("QQQ", "5m", TS + 300000, 752.91, 753.10, 752.80, 753.0, 50000.0))
    check("U5 a bar the store does not hold is inserted",
          get("QQQ", ts=TS + 300000) is not None)

    # U6 — NaN volume lands as NULL and still updates
    put(("VIX", "5m", TS, 15.48, 15.50, 15.47, 15.47, float("nan")))
    put(("VIX", "5m", TS, 15.48, 15.55, 15.45, 15.45, float("nan")))
    got = get("VIX")
    check("U6 NULL volume still updates", got is not None and got[1] == 15.55,
          str(got))

    # U7 — an older snapshot of a forming bar arriving late
    T7 = TS + 600000
    put(("QQQ", "5m", T7, 753.0, 753.20, 752.90, 753.10, 60000.0))
    put(("QQQ", "5m", T7, 753.0, 753.10, 752.95, 753.05, 41000.0))
    got = get("QQQ", ts=T7)
    check("U7 an older snapshot arriving late is refused",
          got == (753.0, 753.20, 752.90, 753.10, 60000.0), str(got))

    # U8 — a stored NULL price heals
    st.conn.execute("INSERT INTO candles VALUES ('CVX','5m',?,211.4,NULL,"
                    "211.2,211.3,7000.0)", (TS,))
    put(("CVX", "5m", TS, 211.4, 211.5, 211.3, 211.3, 6000.0))
    got = get("CVX")
    check("U8 a stored NULL price yields", got is not None and got[1] == 211.5,
          str(got))

    # U9 — NaN at the door
    from data.candle_feed import CandleFeed

    class _C:
        event_symbol = "QQQ{=5m,tho=true}"
        time = TS
        open, high, low, close, volume = float("nan"), 753.0, 752.0, 752.5, 1.0
    feed = CandleFeed(st)
    feed._on_candle(_C())
    check("U9 _on_candle rejects a NaN price",
          not any(feed.buffer.values()), str(feed.buffer))

    # U10 — the refusal log names the key; silence when nothing is refused
    seen = []

    class _H(logging.Handler):
        def emit(self, rec):
            seen.append(rec.getMessage())
    lg = logging.getLogger("data.candle_feed")
    h = _H()
    lg.addHandler(h)
    lg.setLevel(logging.INFO)
    put(("QQQ", "5m", TS, 752.635, 752.9191, 752.57, 752.91, 33808.0),
        ("AMZN", "5m", TS, 258.38, 258.38, 257.90, 257.95, 63169.0))
    named = [m for m in seen if "FEED.9" in m]
    check("U10 a refusal is logged with its symbol and interval",
          len(named) == 1 and "QQQ 5m" in named[0], str(named))
    seen.clear()
    put(("AMZN", "5m", TS, 258.38, 258.40, 257.90, 257.97, 64000.0))
    check("U10 nothing is logged when nothing is refused",
          not [m for m in seen if "FEED.9" in m], str(seen))
    lg.removeHandler(h)

    # U11 — a busted-print correction on an intraday equity bar
    T11 = TS + 900000
    put(("CVX", "5m", T11, 214.0, 216.67, 211.02, 215.0, 100000.0))
    put(("CVX", "5m", T11, 214.0, 216.67, 213.75, 215.0, 99900.0))
    got = get("CVX", ts=T11)
    check("U11 a narrower correction with ~no volume lost is taken",
          got is not None and got[2] == 213.75, str(got))

    # U12 — 1d is last-write-wins. Stored: the real CVX 10-12 bar; the
    # correction is shaped from its 1m (the refused values were never logged)
    TD = 1791777600000
    put(("CVX", "1d", TD, 214.0, 216.67, 211.02, 215.0, 1999182.0))
    put(("CVX", "1d", TD, 214.75, 216.67, 213.7501, 215.0, 1948276.0))
    got = get("CVX", "1d", TD)
    check("U12 1d takes the vendor's correction",
          got == (214.75, 216.67, 213.7501, 215.0, 1948276.0), str(got))

    # U13 — the log carries both versions
    seen.clear()
    lg.addHandler(h)
    put(("QQQ", "5m", TS, 752.635, 752.9191, 752.57, 752.91, 33808.0))
    named = [m for m in seen if "FEED.9" in m]
    check("U13 the refusal log carries the kept and the refused OHLCV",
          len(named) == 1 and "107877" in named[0] and "33808" in named[0],
          str(named))
    lg.removeHandler(h)

    st.close()
    print("ALL PASS" if not PROBLEMS else f"FAIL: {', '.join(PROBLEMS)}")
    return 0 if not PROBLEMS else 1


if __name__ == "__main__":
    sys.exit(main())
