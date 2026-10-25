#!/usr/bin/env python3
"""tests/check_bar_referee.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.1  2026-10-12  OTV4TEST r277 (FEED.10b) — R11-R13, from 1-REPORTER's critique (MSG-1REP-1012-12). R11: a
      bar's FINAL live update that lands 10 s after its close, while its last 1m is still partial in the store,
      is TAKEN (r276's 5 s grace refereed it against the short 1m sum and kept the stale bar). R12: an
      identical replay of a refereed bar logs nothing. R13: a half day's 12:00 hour has 60 minutes and its
      13:00 hour none (falls back), a full day's 15:00 hour 60.
v1.0  2026-10-12  OTV4TEST r276 (FEED.10, fork-first) — THE 1m REFEREE. FEED.9/9b decide from the two
      versions alone: they refuse a SHRUNKEN replay (10-08's vendor slice) and pass any version with MORE
      volume - and on 2026-10-12 this box's own 16:11/16:17 replays stored every complete QQQ 1h bar at
      EXACTLY 2.0x its 60 minutes (mainline's live-pushed 15:00 bar: 1,629,246 = the 1m sum; ours 3,258,492).
      For a CLOSED 5m/15m/1h bar with every minute held, data/candle_feed.py keeps whichever version is
      closer to the 1m aggregate. The operator, 2026-10-12 19:14 ET: "We need to fix this problem before
      it starts polluting more days than just today".

Drives the REAL FeedStore.upsert_candles on a SCRATCH store; the module clock (`data.candle_feed._time`)
is driven so a bar is closed or forming on demand. R1/R2 use TODAY'S REAL QQQ values (read once from the
live store, read-only, and frozen below).
  R1  today's case: the stored QQQ 1h 15:00 bar at 2.0x its 60 complete minutes; a replay at the 1m volume,
      prices identical, REPLACES it (FEED.9b alone would refuse it: it lost 50%)
  R2  the 10-08 case: a stored complete 5m 11:55 bar with its 5 minutes; the vendor slice is REFUSED
  R3  2 of 5 minutes held (incomplete): the FEED.9b rule decides - the slice refused, a growing bar taken
  R4  a 0-volume index (SPX 1h 09:00, 30 complete minutes): the version matching H/L/O/C beats one
      matching H/L only, in BOTH orders (stored first or replayed first)
  R5  *_EXT is refereed by *_EXT 1m, never by the plain 1m
  R6  the plain 09:00 1h bar is complete with its 30 RTH minutes
  R7  a referee exception falls back to FEED.9b, does not raise, and warns once
  R8  an override is logged with the stored, replayed and 1m-aggregate OHLCV
  R9  a FORMING bar's update does no 1m read (the referee runs only on closed bars)
  R10 1m and 1d are never refereed (1d stays last-write-wins; 1m keeps the 9b rule)
"""
import logging, os, sys, tempfile
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
ET = ZoneInfo("America/New_York")
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name); print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  [{detail}]"))
    if not ok:
        FAILED.append(name.split()[0])


# ── TODAY'S REAL VALUES (QQQ-TEST live store, read-only, 2026-10-12 19:2x ET) ──
H15 = 1791831600000
BAR_1H = (744.96, 746.3794, 744.9, 746.02, 3258492.48272)
MIN_1H = [
    (1791831600000, 744.96, 745.075, 744.9, 745.065, 15940.0) ,
    (1791831660000, 745.01, 745.265, 745.01, 745.2, 12353.0) ,
    (1791831720000, 745.2, 745.27, 745.16, 745.16, 7882.0) ,
    (1791831780000, 745.155, 745.16, 745.04, 745.16, 13104.0) ,
    (1791831840000, 745.15, 745.24, 745.14, 745.21, 9945.0) ,
    (1791831900000, 745.2, 745.28, 745.16, 745.275, 13900.0) ,
    (1791831960000, 745.27, 745.2712, 745.15, 745.19, 6728.0) ,
    (1791832020000, 745.195, 745.225, 745.14, 745.195, 24194.0) ,
    (1791832080000, 745.2042, 745.235, 745.185, 745.225, 15196.0) ,
    (1791832140000, 745.23, 745.23, 744.9401, 744.96, 14982.0) ,
    (1791832200000, 744.965, 745.025, 744.92, 745.02, 15572.0) ,
    (1791832260000, 745.02, 745.1, 745.02, 745.085, 6944.0) ,
    (1791832320000, 745.09, 745.12, 745.045, 745.06, 10784.0) ,
    (1791832380000, 745.065, 745.1, 745.02, 745.03, 10569.0) ,
    (1791832440000, 745.04, 745.225, 745.02, 745.14, 15741.0) ,
    (1791832500000, 745.1499, 745.2, 745.1231, 745.1231, 17559.0) ,
    (1791832560000, 745.125, 745.14, 745.04, 745.085, 16376.0) ,
    (1791832620000, 745.0801, 745.0801, 744.97, 745.005, 8948.0) ,
    (1791832680000, 745.005, 745.225, 745.005, 745.22, 24916.0) ,
    (1791832740000, 745.225, 745.35, 745.225, 745.345, 42025.0) ,
    (1791832800000, 745.325, 745.395, 745.27, 745.395, 32728.00042) ,
    (1791832860000, 745.39, 745.3997, 745.3, 745.365, 24705.0) ,
    (1791832920000, 745.335, 745.4, 745.31, 745.375, 30839.0) ,
    (1791832980000, 745.345, 745.375, 745.27, 745.31, 41916.0) ,
    (1791833040000, 745.315, 745.375, 745.31, 745.37, 12585.0) ,
    (1791833100000, 745.37, 745.409, 745.325, 745.36, 12060.0) ,
    (1791833160000, 745.36, 745.45, 745.325, 745.4412, 8993.0) ,
    (1791833220000, 745.45, 745.5, 745.42, 745.47, 23511.0) ,
    (1791833280000, 745.458, 745.495, 745.39, 745.465, 8557.0) ,
    (1791833340000, 745.45, 745.501, 745.4001, 745.5, 8256.0) ,
    (1791833400000, 745.53, 745.56, 745.42, 745.545, 27457.0) ,
    (1791833460000, 745.545, 745.58, 745.46, 745.49, 12097.0) ,
    (1791833520000, 745.495, 745.63, 745.49, 745.62, 13688.0) ,
    (1791833580000, 745.62, 745.758, 745.57, 745.758, 23418.0) ,
    (1791833640000, 745.765, 746.035, 745.765, 746.02, 43311.0) ,
    (1791833700000, 746.04, 746.275, 746.01, 746.23, 79794.0) ,
    (1791833760000, 746.2317, 746.3794, 746.18, 746.305, 47786.0) ,
    (1791833820000, 746.3, 746.31, 746.185, 746.3, 47361.0) ,
    (1791833880000, 746.295, 746.295, 746.09, 746.13, 14057.0) ,
    (1791833940000, 746.135, 746.145, 746.05, 746.05, 31699.0) ,
    (1791834000000, 746.055, 746.13, 746.01, 746.0201, 26851.0) ,
    (1791834060000, 746.02, 746.0399, 745.88, 745.995, 14160.0) ,
    (1791834120000, 745.995, 745.995, 745.855, 745.86, 11880.0) ,
    (1791834180000, 745.875, 745.935, 745.82, 745.85, 10453.0) ,
    (1791834240000, 745.865, 745.9499, 745.84, 745.93, 16727.0) ,
    (1791834300000, 745.94, 746.0, 745.78, 745.96, 30633.0) ,
    (1791834360000, 745.97, 745.98, 745.85, 745.9, 16132.0) ,
    (1791834420000, 745.9, 745.97, 745.795, 745.845, 20566.0) ,
    (1791834480000, 745.84, 745.93, 745.82, 745.93, 19711.0) ,
    (1791834540000, 745.945, 746.04, 745.89, 746.035, 17341.0) ,
    (1791834600000, 746.02, 746.35, 746.01, 746.1886, 27598.0) ,
    (1791834660000, 746.185, 746.27, 746.0, 746.0, 61965.99664) ,
    (1791834720000, 746.0, 746.0, 745.85, 745.96, 26134.61566) ,
    (1791834780000, 745.975, 746.1101, 745.84, 745.94, 41274.0) ,
    (1791834840000, 745.93, 746.0, 745.68, 745.85, 22183.0) ,
    (1791834900000, 745.87, 746.03, 745.71, 745.9401, 60462.0) ,
    (1791834960000, 745.94, 745.99, 745.87, 745.9017, 73278.0) ,
    (1791835020000, 745.9, 745.95, 745.7912, 745.95, 46146.0) ,
    (1791835080000, 745.9488, 746.04, 745.91, 746.01, 68315.0) ,
    (1791835140000, 746.02, 746.15, 745.83, 746.02, 168959.62864) ,
]
T5 = 1791474900000
BAR_5M = (752.833, 752.94, 752.39, 752.91, 107877.0)
MIN_5M = [
    (1791474900000, 752.833, 752.94, 752.42, 752.46, 38386.0) ,
    (1791474960000, 752.415, 752.55, 752.39, 752.4401, 19084.0) ,
    (1791475020000, 752.48, 752.76, 752.43, 752.76, 20054.0) ,
    (1791475080000, 752.745, 752.745, 752.57, 752.738, 12437.0) ,
    (1791475140000, 752.73, 752.9191, 752.68, 752.91, 17916.0) ,
]


def ms(y, mo, d, h, mi):
    return int(datetime(y, mo, d, h, mi, tzinfo=ET).timestamp() * 1000)


def agg(mins):
    return (mins[0][1], max(m[2] for m in mins), min(m[3] for m in mins), mins[-1][4], sum(m[5] for m in mins))


def main():
    import data.candle_feed as cf
    from data.candle_feed import FeedStore
    clock = [0.0]

    class _T:
        @staticmethod
        def time():
            return clock[0]
    real_time = cf._time
    cf._time = _T
    seen = []

    class _H(logging.Handler):
        def emit(self, rec):
            seen.append(rec.getMessage())
    lg = logging.getLogger("data.candle_feed"); h = _H(); lg.addHandler(h); lg.setLevel(logging.INFO)
    d = tempfile.mkdtemp()
    try:
        st = FeedStore(os.path.join(d, "feed_store.db"))

        def put(*rows, now):
            clock[0] = now
            st.upsert_candles(list(rows)); st.commit()

        def get(sym, iv, ts):
            return st.conn.execute("SELECT open, high, low, close, volume FROM candles WHERE symbol=? "
                                   "AND interval=? AND ts_epoch_ms=?", (sym, iv, ts)).fetchone()

        def mins_in(sym, rows):
            st.conn.executemany("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)",
                                [(sym, "1m") + tuple(m) for m in rows]); st.commit()

        late = H15 / 1000.0 + 6 * 3600                       # long after both bars closed
        # R1 — today's doubled 1h bar
        mins_in("QQQ", MIN_1H)
        st.conn.execute("INSERT INTO candles VALUES ('QQQ','1h',?,?,?,?,?,?)", (H15,) + tuple(BAR_1H)); st.commit()
        a1 = agg(MIN_1H)
        seen.clear()
        put(("QQQ", "1h", H15) + tuple(BAR_1H[:4]) + (a1[4],), now=late)
        g = get("QQQ", "1h", H15)
        check("R1 a doubled stored 1h bar is replaced by the replay at its own 1m volume (9b alone refuses it)",
              g is not None and abs(g[4] - a1[4]) < 1e-6 and abs(BAR_1H[4] / a1[4] - 2.0) < 1e-6,
              f"stored={g} 1m sum={a1[4]} was={BAR_1H[4]}")
        r8 = [m for m in seen if m.startswith("FEED.10")]
        check("R8 the override is logged with the stored, replayed and 1m-aggregate OHLCV",
              len(r8) == 1 and "TOOK the replay" in r8[0] and "stored OHLCV" in r8[0]
              and "replay OHLCV" in r8[0] and "1m aggregate OHLCV" in r8[0], str(r8))

        # R2 — the 10-08 slice against a complete stored 5m bar
        mins_in("QQQ", MIN_5M)
        st.conn.execute("INSERT INTO candles VALUES ('QQQ','5m',?,?,?,?,?,?)", (T5,) + tuple(BAR_5M)); st.commit()
        put(("QQQ", "5m", T5, 752.635, 752.9191, 752.57, 752.91, 33808.0), now=late)
        check("R2 the vendor slice is refused against a complete stored 5m bar",
              get("QQQ", "5m", T5) == tuple(BAR_5M), str(get("QQQ", "5m", T5)))

        # R3 — incomplete minutes: 9b decides
        T3 = T5 + 86_400_000 * 7
        part = [(T3 + 180_000,) + tuple(MIN_5M[3][1:]), (T3 + 240_000,) + tuple(MIN_5M[4][1:])]
        mins_in("QQQ", part)
        st.conn.execute("INSERT INTO candles VALUES ('QQQ','5m',?,?,?,?,?,?)", (T3,) + tuple(BAR_5M)); st.commit()
        put(("QQQ", "5m", T3, 752.635, 752.9191, 752.57, 752.91, 33808.0), now=late + 86400 * 8)
        r3a = get("QQQ", "5m", T3) == tuple(BAR_5M)
        put(("QQQ", "5m", T3, 752.833, 752.95, 752.30, 752.92, 110000.0), now=late + 86400 * 8)
        r3b = get("QQQ", "5m", T3) == (752.833, 752.95, 752.30, 752.92, 110000.0)
        check("R3 with 2 of 5 minutes held the FEED.9b rule decides: slice refused, a growing bar taken",
              r3a and r3b, f"refused={r3a} grown={r3b} now={get('QQQ', '5m', T3)}")

        # R4 — a 0-volume index, complete 30 minutes of the 09:00 hour
        S9 = ms(2026, 9, 4, 9, 0)
        idx = []
        px = 7750.19
        for k in range(30):
            t = ms(2026, 9, 4, 9, 30 + k)
            o = px; c = px - 0.3 if k % 2 else px + 0.1
            idx.append((t, o, max(o, c) + 0.2, min(o, c) - 0.2, c, 0.0)); px = c
        ia = agg(idx)
        good = (ia[0], ia[1], ia[2], ia[3], 0.0)
        hl_only = (ia[0] - 7.0, ia[1], ia[2], ia[3], 0.0)          # H/L right, open wrong
        mins_in("SPX", idx)
        st.conn.execute("INSERT INTO candles VALUES ('SPX','1h',?,?,?,?,?,?)", (S9,) + hl_only); st.commit()
        put(("SPX", "1h", S9) + good, now=late)
        r4a = get("SPX", "1h", S9) == good
        put(("SPX", "1h", S9) + hl_only, now=late)
        r4b = get("SPX", "1h", S9) == good
        check("R4 0-volume index: the version matching H/L/O/C beats H/L-only, stored first and replayed first",
              r4a and r4b, f"took good={r4a} kept good={r4b} now={get('SPX', '1h', S9)}")

        # R5 — *_EXT refereed by *_EXT 1m only
        TE = ms(2026, 10, 9, 20, 0)
        ext_m = [(TE + k * 60_000, 750.0 + k * 0.01, 750.2 + k * 0.01, 749.9 + k * 0.01, 750.1 + k * 0.01, 1000.0)
                 for k in range(5)]
        ea = agg(ext_m)
        mins_in("QQQ_EXT", ext_m)
        st.conn.execute("INSERT INTO candles VALUES ('QQQ_EXT','5m',?,?,?,?,?,?)", (TE,) + tuple(ea[:4]) + (ea[4] * 2,))
        mins_in("QQQ", ext_m)                                   # the plain series holds the same minutes too
        st.conn.execute("INSERT INTO candles VALUES ('QQQ','5m',?,?,?,?,?,?)", (TE,) + tuple(ea[:4]) + (ea[4] * 2,))
        st.conn.execute("DELETE FROM candles WHERE symbol='QQQ_EXT' AND interval='1m' AND ts_epoch_ms=?", (TE + 240_000,))
        st.commit()
        put(("QQQ_EXT", "5m", TE) + tuple(ea[:4]) + (ea[4],), now=late)
        r5a = abs(get("QQQ_EXT", "5m", TE)[4] - ea[4] * 2) < 1e-6            # EXT minutes incomplete: 9b refuses
        mins_in("QQQ_EXT", [ext_m[4]])
        put(("QQQ_EXT", "5m", TE) + tuple(ea[:4]) + (ea[4],), now=late)
        r5b = abs(get("QQQ_EXT", "5m", TE)[4] - ea[4]) < 1e-6                # complete: the referee takes it
        check("R5 *_EXT is refereed by *_EXT 1m only (plain minutes never stand in)",
              r5a and r5b, f"incomplete kept 2x={r5a} complete took 1x={r5b}")

        # R6 — the plain 09:00 hour with its 30 RTH minutes
        H9 = ms(2026, 10, 12, 9, 0)
        m9 = [(ms(2026, 10, 12, 9, 30 + k), 749.0, 749.5, 748.5, 749.2, 1000.0 + k) for k in range(30)]
        a9 = agg(m9)
        mins_in("QQQ", m9)
        st.conn.execute("INSERT INTO candles VALUES ('QQQ','1h',?,?,?,?,?,?)", (H9,) + tuple(a9[:4]) + (a9[4] * 2,)); st.commit()
        put(("QQQ", "1h", H9) + tuple(a9[:4]) + (a9[4],), now=late)
        check("R6 the plain 09:00 1h bar is complete with its 30 RTH minutes (refereed: 2x replaced)",
              abs(get("QQQ", "1h", H9)[4] - a9[4]) < 1e-6, str(get("QQQ", "1h", H9)))

        # R9 — a forming bar does no 1m read
        HF = ms(2026, 10, 13, 10, 0)
        st.conn.execute("INSERT INTO candles VALUES ('QQQ','1h',?,?,?,?,?,?)", (HF, 750.0, 750.5, 749.5, 750.1, 5000.0)); st.commit()
        sql = []
        st.conn.set_trace_callback(sql.append)
        put(("QQQ", "1h", HF, 750.0, 750.6, 749.5, 750.3, 6000.0), now=HF / 1000.0 + 600)
        st.conn.set_trace_callback(None)
        reads = [q for q in sql if "interval='1m'" in q]
        check("R9 a FORMING bar's update does no 1m read and takes the 9b rule",
              not reads and get("QQQ", "1h", HF)[4] == 6000.0, f"1m reads={len(reads)} row={get('QQQ', '1h', HF)}")

        # R10 — 1m and 1d are never refereed
        D = ms(2026, 10, 7, 0, 0)
        md = [(ms(2026, 10, 7, 9, 30) + k * 60_000, 754.0, 754.1, 753.9, 754.0, 100.0) for k in range(390)]
        mins_in("QQQ", md)
        st.conn.execute("INSERT INTO candles VALUES ('QQQ','1d',?,?,?,?,?,?)", (D, 754.0, 754.1, 753.9, 754.0, 39000.0))
        st.commit()
        put(("QQQ", "1d", D, 754.0, 760.0, 750.0, 754.0, 99999.0), now=late)
        r10a = get("QQQ", "1d", D)[4] == 99999.0                  # last-write-wins, though the 1m says otherwise
        put(("QQQ", "1m", md[0][0], 754.0, 754.3, 753.9, 754.2, 98.0), now=late)
        r10b = get("QQQ", "1m", md[0][0]) == (754.0, 754.3, 753.9, 754.2, 98.0)   # 1m: 9b takes (>= 95%); never refereed
        check("R10 1m and 1d are never refereed (1d last-write-wins; 1m takes the 9b rule)",
              r10a and r10b, f"1d took={r10a} 1m took={r10b}")

        # R11 — the final live update of a just-closed bar, its last minute still partial in the store
        T11 = ms(2026, 10, 9, 10, 0)
        m11 = [(T11 + k * 60_000, 750.0, 750.2, 749.9, 750.1, 20000.0) for k in range(5)]
        part = list(m11); part[-1] = (T11 + 4 * 60_000, 750.0, 750.1, 749.95, 750.05, 7000.0)
        mins_in("QQQ", part)
        st.conn.execute("INSERT OR REPLACE INTO candles VALUES ('QQQ','5m',?,?,?,?,?,?)",
                        (T11, 750.0, 750.2, 749.9, 750.05, 87000.0)); st.commit()      # the live bar so far
        put(("QQQ", "5m", T11, 750.0, 750.2, 749.9, 750.1, 100000.0), now=T11 / 1000.0 + 300 + 10)
        g11 = get("QQQ", "5m", T11)
        check("R11 a FINAL live update 10 s after the close is TAKEN while its last minute is still partial",
              g11 is not None and g11[4] == 100000.0, f"stored={g11}")
        # R12 — an identical replay of a refereed (closed, complete) bar is silent
        mins_in("QQQ", m11)
        st.conn.execute("INSERT OR REPLACE INTO candles VALUES ('QQQ','5m',?,?,?,?,?,?)",
                        (T11, 750.0, 750.2, 749.9, 750.1, 100000.0)); st.commit()     # stored == the replay below
        seen.clear()
        put(("QQQ", "5m", T11, 750.0, 750.2, 749.9, 750.1, 100000.0), now=late)
        check("R12 an identical replay of a refereed bar logs no FEED.10 line",
              not [m for m in seen if m.startswith("FEED.10")], str([m for m in seen if m.startswith("FEED.10")]))
        # R13 — half day 2026-11-27 (13:00 bell): the 12:00 hour holds 60 minutes, the 13:00 hour none
        _rm = getattr(cf, "_referee_minutes")
        n12 = len(_rm("QQQ", ms(2026, 11, 27, 12, 0), 60)); n13 = len(_rm("QQQ", ms(2026, 11, 27, 13, 0), 60))
        n15 = len(_rm("QQQ", ms(2026, 11, 25, 15, 0), 60)); n09 = len(_rm("QQQ", ms(2026, 11, 27, 9, 0), 60))
        check("R13 half day: 12:00 hour = 60 minutes, 13:00 hour = none (falls back), 09:00 = 30; full day 15:00 = 60",
              (n12, n13, n09, n15) == (60, 0, 30, 60), f"12:00={n12} 13:00={n13} 09:00={n09} full 15:00={n15}")

        # R7 — a referee exception falls back, does not raise, warns once
        real_min = getattr(cf, "_referee_minutes", None)
        if real_min is None:
            check("R7 a referee exception falls back to FEED.9b, never raises, and warns once", False,
                  "no referee in data.candle_feed (pre-r276)")
            raise SystemExit(_finish())
        cf._referee_minutes = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        seen.clear()
        try:
            st.conn.execute("INSERT OR REPLACE INTO candles VALUES ('QQQ','5m',?,?,?,?,?,?)", (T5,) + tuple(BAR_5M)); st.commit()
            put(("QQQ", "5m", T5, 752.833, 752.94, 752.39, 752.91, 106000.0), now=late)   # 9b takes (>= 95%)
            put(("QQQ", "5m", T5, 752.833, 752.94, 752.39, 752.91, 105000.0), now=late)
            raised = False
        except Exception as e:                                   # noqa: BLE001
            raised = repr(e)
        finally:
            cf._referee_minutes = real_min
        warns = [m for m in seen if "the 1m referee failed" in m]
        check("R7 a referee exception falls back to FEED.9b, never raises, and warns once",
              raised is False and get("QQQ", "5m", T5)[4] == 105000.0 and len(warns) == 1,
              f"raised={raised} row={get('QQQ', '5m', T5)} warns={len(warns)}")
        st.close()
    finally:
        cf._time = real_time
        lg.removeHandler(h)
    return _finish()


def _finish():
    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
