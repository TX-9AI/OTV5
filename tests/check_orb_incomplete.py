#!/usr/bin/env python3
"""
tests/check_orb_incomplete.py  v5.0
v5.0  2026-11-04  OTV5 r74 (ORP.3) — THE OPENING RANGE IS NEVER BUILT FROM A PARTIAL TAPE.

2026-11-02 the AMZN feed was refused 09:31-10:55 ET. The store held the 09:30 1m and 5m bars captured when the socket
dropped (H 244.43 L 243.02, 0.76M); TastyTrade's history says H 246.39 L 242.28 (1.94M). At 10:56:51 the five 1m bars
were not all on the feed, so get_orb_range v5.1 ESTABLISHED 243.02-244.43 from the lone 5m row, and Hunt traded against
it all afternoon; the official-print check latched "unverifiable" on an engine range of 0.00-0.00 and never looked
again. The fixture is AMZN 11-02: the store's partial bars and TastyTrade's real ones. The operator, 2026-11-03:
"Yes to the proposal" (build the two outage-path fixes).

  R1  analysis/opening_tape.problem: TastyTrade's five 1m bars + its 5m bar -> complete; a missing minute is named;
      the five 1m bars with the PARTIAL 09:30 1m bar against the partial 5m bar -> "disagrees"; the real 1m bars
      against the partial 5m bar -> "disagrees"; no 5m row -> the five 1m bars stand alone
  R2  get_orb_range at 10:56:51 on the partial store -> INCOMPLETE (exit 4) with a reason, never ESTABLISHED
      243.02-244.43; five 1m bars back but the 09:30 bar still partial -> INCOMPLETE; the refilled store ->
      ESTABLISHED 242.28 / 246.39; a short tape at 09:35:30 -> IN_PROGRESS (not INCOMPLETE); no tape -> EXPIRED
  R3  data/candle_feed rescue: a partial tape at 10:57 re-pulls 5m AND 1m from 09:30 (unsubscribe first); a complete
      tape pulls nothing; a second call inside ORB_RESCUE_EVERY_S pulls nothing; at most ORB_RESCUE_MAX a session;
      outside 09:36-ORB_RESCUE_UNTIL_ET nothing
  R4  main: get_orb_range's exit 4 -> _fetch_orb_range False and _opening_range (None, None) although df_5m holds
      the partial 09:30 bar; ONE page, only from 09:37; a later exit 0 -> one "ESTABLISHED late" note and the tape
      fallback is back; _verify_official_print does not latch while the engine range is 0.00-0.00

Run:  python3 tests/check_orb_incomplete.py
"""
import asyncio
import os
import sqlite3
import sys
import types
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
ET = ZoneInfo("America/New_York")
FAILED = []
DAY = "2026-11-02"

# AMZN 2026-11-02 — TastyTrade candle history (~/reviews/backfill/2026-11-02/candles_tt_1026_1102.csv)
TT_1M = [("09:30", 243.17, 244.46, 242.28, 244.10), ("09:31", 244.16, 245.61, 243.095, 245.42),
         ("09:32", 245.4231, 246.30, 245.02, 246.08), ("09:33", 246.085, 246.39, 245.73, 246.13),
         ("09:34", 246.1648, 246.34, 245.58, 246.29), ("09:35", 246.2804, 248.16, 246.2804, 247.6101)]
TT_5M = [("09:30", 243.17, 246.39, 242.28, 246.29), ("09:35", 246.2804, 249.76, 246.2804, 249.52)]
# the store's capture at 09:31 (warehouse wh_* columns, candles_corrections_1026_1102.csv)
PART_1M_0930 = ("09:30", 243.17, 244.43, 243.02, 244.09)
PART_5M_0930 = ("09:30", 243.17, 244.43, 243.02, 244.09)
LATE_1M = [("10:55", 250.0, 250.5, 249.8, 250.2), ("10:56", 250.2, 250.4, 250.0, 250.1)]
LATE_5M = [("10:55", 250.0, 250.6, 249.7, 250.3)]
PRIOR_5M = ("2026-10-30", "09:30", 240.0, 241.5, 239.2, 241.0)


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def _ts(day, hm):
    return datetime.strptime(f"{day} {hm}", "%Y-%m-%d %H:%M").replace(tzinfo=ET)


def _frame(rows, day=DAY):
    import pandas as pd
    idx, data = [], []
    for r in rows:
        d, (hm, o, h, l, c) = (r[0], r[1:]) if len(r) == 6 else (day, r)
        idx.append(_ts(d, hm))
        data.append({"open": o, "high": h, "low": l, "close": c, "volume": 1.0})
    return pd.DataFrame(data, index=pd.DatetimeIndex(idx))


def r1():
    from analysis import opening_tape as T
    hl = lambda rows: {int(r[0][3:]): (r[2], r[3]) for r in rows if r[0] < "09:35"}
    real = hl(TT_1M)
    part = dict(real)
    part[30] = (PART_1M_0930[2], PART_1M_0930[3])
    a = T.problem(real, (246.39, 242.28))
    b = T.problem({k: v for k, v in real.items() if k != 32}, (246.39, 242.28))
    c = T.problem(part, (244.43, 243.02))
    d = T.problem(real, (244.43, 243.02))
    e = T.problem(real, None)
    check("R1 opening_tape: real tape complete; a missing 09:32 named; partial 09:30 vs partial 5m and real 1m vs "
          "partial 5m both 'disagrees'; no 5m row -> the five 1m bars stand alone",
          a is None and b and "09:32" in b and c and "disagrees" in c and d and "disagrees" in d and e is None,
          f"a={a} b={b} c={c} d={d} e={e}")


def r2():
    import analysis.get_orb_range as G

    def run(m1, m5, hh, mm, ss):
        frames = {"1m": _frame(m1) if m1 else None, "5m": _frame(m5)}
        G.fetch_candles = lambda sym, iv, n: frames[iv]
        return G.resolve_orb_range("AMZN", now=datetime(2026, 11, 2, hh, mm, ss, tzinfo=ET))

    partial = run([PART_1M_0930] + LATE_1M, [PRIOR_5M, PART_5M_0930] + LATE_5M, 10, 56, 51)
    five_part = run([PART_1M_0930] + TT_1M[1:] + LATE_1M, [PRIOR_5M, PART_5M_0930] + LATE_5M, 10, 57, 30)
    refilled = run(TT_1M + LATE_1M, [PRIOR_5M] + TT_5M + LATE_5M, 10, 58, 0)
    early = run([PART_1M_0930], [PRIOR_5M, PART_5M_0930], 9, 35, 30)
    none = run(None, [PRIOR_5M], 10, 0, 0)
    ok = (partial["status"] == "INCOMPLETE" and partial.get("reason") and G.EXIT_CODE["INCOMPLETE"] == 4
          and not (partial["high"] == 244.43 and partial["low"] == 243.02)
          and five_part["status"] == "INCOMPLETE" and "disagrees" in (five_part.get("reason") or "")
          and refilled["status"] == "ESTABLISHED" and refilled["high"] == 246.39 and refilled["low"] == 242.28
          and early["status"] == "IN_PROGRESS" and none["status"] == "EXPIRED")
    check("R2 get_orb_range: partial store at 10:56:51 INCOMPLETE (exit 4, reason), never 243.02-244.43; five bars "
          "with a partial 09:30 INCOMPLETE; refilled ESTABLISHED 242.28/246.39; 09:35:30 IN_PROGRESS; no tape EXPIRED",
          ok, f"partial={partial['status']} {partial.get('reason')} H={partial['high']} | five={five_part['status']} "
              f"{five_part.get('reason')} | refilled={refilled['status']} {refilled['low']}/{refilled['high']} | "
              f"early={early['status']} | none={none['status']}")


def r3():
    from data import candle_feed as cf
    feed = cf.CandleFeed.__new__(cf.CandleFeed)
    feed._orb_rescue = []
    feed.dx_symbol = "AMZN"

    def store(m1, m5):
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE candles (symbol TEXT, interval TEXT, ts_epoch_ms INTEGER, high REAL, low REAL)")
        for iv, rows in (("1m", m1), ("5m", m5)):
            for hm, o, h, l, c in rows:
                con.execute("INSERT INTO candles VALUES (?,?,?,?,?)",
                            (cf.INSTRUMENT, iv, int(_ts(DAY, hm).timestamp() * 1000), h, l))
        return types.SimpleNamespace(conn=con)

    calls = []

    class S:
        async def unsubscribe_candle(self, sym, tf): calls.append(("unsub", tf))
        async def subscribe_candle(self, syms, tf, start_time=None, extended_trading_hours=None):
            calls.append(("sub", tf, start_time.strftime("%H:%M") if start_time else None, extended_trading_hours))

    mono = [1000.0]
    real_mono = cf._time.monotonic
    cf._time.monotonic = lambda: mono[0]
    try:
        at = lambda hh, mm: datetime(2026, 11, 2, hh, mm, 0, tzinfo=ET)
        feed.store = store([PART_1M_0930] + LATE_1M, [PART_5M_0930] + LATE_5M)
        a = asyncio.run(feed._maybe_rescue_opening_range(S(), now=at(10, 57)))
        first = list(calls)
        mono[0] += 30
        b = asyncio.run(feed._maybe_rescue_opening_range(S(), now=at(10, 57)))
        n_after_b = len(calls)
        tries = 1
        for _ in range(10):
            mono[0] += cf.ORB_RESCUE_EVERY_S + 1
            if asyncio.run(feed._maybe_rescue_opening_range(S(), now=at(11, 10))):
                tries += 1
        feed._orb_rescue = []
        calls.clear()
        feed.store = store(TT_1M, TT_5M)
        c = asyncio.run(feed._maybe_rescue_opening_range(S(), now=at(11, 0)))
        feed.store = store([PART_1M_0930], [PART_5M_0930])
        d = asyncio.run(feed._maybe_rescue_opening_range(S(), now=at(9, 35)))
        e = asyncio.run(feed._maybe_rescue_opening_range(S(), now=at(15, 0)))
    finally:
        cf._time.monotonic = real_mono
    ok = (a is True and first == [("unsub", "5m"), ("sub", "5m", "09:30", False),
                                  ("unsub", "1m"), ("sub", "1m", "09:30", False)]
          and b is False and n_after_b == 4 and tries == cf.ORB_RESCUE_MAX
          and c is False and d is False and e is False and calls == [])
    check("R3 feed rescue: partial tape at 10:57 re-pulls 5m and 1m from 09:30; none inside 120 s; at most "
          "ORB_RESCUE_MAX a session; a complete tape, 09:35 and 15:00 pull nothing",
          ok, f"a={a} first={first} b={b} tries={tries}/{cf.ORB_RESCUE_MAX} c={c} d={d} e={e} calls={calls}")


def r4():
    import pandas as pd
    import main as M
    sent = []
    M.get_alert_manager = lambda: types.SimpleNamespace(_send=lambda m, *a, **k: sent.append(m) or True)
    clock = [datetime(2026, 11, 2, 9, 36, 30, tzinfo=ET)]
    M.now_et = lambda: clock[0]
    out = {"rc": 4, "line": "ORB range [INCOMPLETE]: AMZN 2026-10-30 H=241.5 L=239.2 W=2.3 | the 09:30 5m bar disagrees"}

    class _R:
        def __init__(self):
            self.returncode = out["rc"]
            self.stdout = out["line"] + "\nWritten to: x\n"
            self.stderr = ""
    import subprocess
    real_run = subprocess.run
    subprocess.run = lambda *a, **k: _R()
    try:
        M._OR_INCOMPLETE.update(day="", reason="", paged="", since=0.0)
        f1 = M._fetch_orb_range("AMZN")
        pages_0936 = len(sent)
        clock[0] = datetime(2026, 11, 2, 9, 37, 5, tzinfo=ET)
        f2 = M._fetch_orb_range("AMZN")
        f3 = M._fetch_orb_range("AMZN")
        pages_0937 = len(sent)
        df5 = _frame([PRIOR_5M, PART_5M_0930] + LATE_5M)
        held = M._opening_range({"df_5m": df5, "df_1m": None})
        out.update(rc=0, line="ORB range [ESTABLISHED]: AMZN 2026-11-02 H=246.39 L=242.28 W=4.11")
        f4 = M._fetch_orb_range("AMZN")
        back = M._opening_range({"df_5m": df5, "df_1m": None})
        pages_end = len(sent)
    finally:
        subprocess.run = real_run
    eng = types.SimpleNamespace(data=types.SimpleNamespace(orb_high=0.0, orb_low=0.0))
    M.get_orb_engine = lambda: eng
    st = types.SimpleNamespace(orb_range_established_today=True, _orb_print_day="")
    clock[0] = datetime(2026, 11, 2, 10, 56, 51, tzinfo=ET)
    v = M._verify_official_print(st, df_1m=_frame([PART_1M_0930] + LATE_1M))
    ok = (f1 is False and f2 is False and f3 is False and pages_0936 == 0 and pages_0937 == 1
          and "OPENING RANGE INCOMPLETE" in sent[0] and held == (None, None)
          and f4 is True and pages_end == 2 and "ESTABLISHED late" in sent[1]
          and back == (244.43, 243.02) and v == "" and st._orb_print_day == "")
    check("R4 main: exit 4 -> not established and _opening_range (None, None) despite the partial 5m bar; ONE page, "
          "from 09:37; exit 0 later -> one 'ESTABLISHED late' note and the tape fallback returns; the print check "
          "does not latch on 0.00-0.00",
          ok, f"f={f1, f2, f3, f4} pages={pages_0936, pages_0937, pages_end} held={held} back={back} v={v!r} "
              f"latched={st._orb_print_day!r}")


def main():
    print("check_orb_incomplete")
    try:
        import pandas  # noqa: F401
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN: {exc}")
        return 2
    r1()
    r2()
    r3()
    r4()
    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
