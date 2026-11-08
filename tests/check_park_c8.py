#!/usr/bin/env python3
"""
tests/check_park_c8.py  v5.0
v5.0  2026-11-08  OTV5 r93 (C8.1) — new. PARK SKIPS AN ENTRY THE FIRST HOUR HAS ALREADY OUTRUN (strategy/park_plan v5.7,
      strategy/park v5.3). The operator, 2026-11-08: "Yes, to both". The rule is the frozen, blind-passed C8 of
      ~/reviews/studies/web_setups_1108 (FROZEN.txt 18:57 UTC): skip a call when the 10:59 1m close is above the
      09:30-10:29 1m high, a put when it is below their low.

  U1  call, 10:59 close above the first-hour high -> extended
  U2  call, 10:59 close EQUAL to the high -> not extended (strict, as the study's C4: C > max)
  U3  call, close inside the range -> not extended; a 10:30-10:58 bar above the high is NOT part of the first hour
  U4  put, close below the low -> extended; equal to the low -> not extended; a put is never read against the high
  U5  missing 10:59 bar / no 09:30-10:29 bar / no direction -> unknown (None), with the reason
  U6  closed bars only: an 11:00 bar (closing 11:01, the window's first minute) far outside the range changes nothing
  W1  wired, QQQ (an index): an extended long is refused at c8_first_hour_extended - no signal, unmet is exactly that,
      the condition and close_1059 / ib_high / ib_low rows are on the tick, one "[park] SKIP c8_first_hour_extended"
      line is logged - AND the r90 shadow_park_sma50 row is on the same skipped tick
  W2  wired, QQQ: a long that is not extended fires (signal built, condition met)
  W3  wired, QQQ: no 10:59 bar -> FAILS OPEN: the signal is built, the condition is met with "unknown, fails open"
  W4  wired, QQQ: an extended short is refused at c8_first_hour_extended
  W5  wired, CVX (an equity, the commitment gate held met): an extended long is refused at c8_first_hour_extended - C8
      is asked on equities, after the commitment gate
  R1  REPLAY: first_hour_extended re-run on the study's 254 PARK trades (tests/fixtures/park_c8/study_trades.json,
      frozen from the study's own bars) reproduces its verdict on EVERY trade: 63 of 254 skipped over the window,
      13 of 77 on the 18 sealed (blind) days, 0 unknown
  C1  no parameter: no PARK_C8 / C8_ key in config.py, no os.environ read in the C8 code, no configure.sh item

Mutants (each red): > -> >= (U2, U4); the first hour to 10:59 (U3, R1); long/short swapped (U1, U4, W1, W4, R1); unknown
treated as extended (U5, W3); c8_read call removed (W1, W4, W5); the shadow call moved after C8 (W1).
Run:  python3 tests/check_park_c8.py      (exit 0 green, 1 red)
"""
import json
import logging
import os
import re
import sqlite3
import sys
import tempfile
from datetime import date, datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_park_c8_")
FEED = os.path.join(_TD, "f.db")
for _k, _v in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_RESTING_DB", "r.db"), ("OT_COUNTERFACTUAL_DIR", "cf"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json"), ("OT_RESTING_STOP_STATE", "rs.json")):
    os.environ[_k] = os.path.join(_TD, _v)
os.environ["OT_FEED_DB"] = FEED
os.environ.update(OT_RISK_USD="1050", OT_INSTRUMENT="QQQ")
for _k in ("OT_PARK", "OT_DECAY_STOP"):
    os.environ.pop(_k, None)
ET = ZoneInfo("America/New_York")
FIX = os.path.join(ROOT, "tests", "fixtures", "park_c8", "study_trades.json")
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  - {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def hm(i):                       # minute index from 09:30
    return "%02d:%02d" % divmod(9 * 60 + 30 + i, 60)


def flat_day(lo=99.0, hi=101.0, c1059=100.0):
    """09:30-10:29 bars inside [lo, hi] (one bar touches each edge), 10:30-10:58 at 100, 10:59 closing at c1059."""
    d = {}
    for i in range(60):
        d[hm(i)] = (100.0, 100.5, 99.5, 100.0, 1.0)
    d["09:45"] = (100.0, hi, 99.8, 100.0, 1.0)
    d["10:05"] = (100.0, 100.2, lo, 100.0, 1.0)
    for i in range(60, 89):
        d[hm(i)] = (100.0, 100.2, 99.8, 100.0, 1.0)
    d["10:59"] = (100.0, max(100.0, c1059) + .1, min(100.0, c1059) - .1, c1059, 1.0)
    return d


def main():
    from strategy import park_plan as PP
    f = PP.first_hour_extended

    # ── U: the pure rule ──
    check("U1 call, 10:59 close above the first-hour high -> extended", f(flat_day(c1059=101.01), "long")["extended"] is True)
    check("U2 call, 10:59 close EQUAL to the high -> not extended (strict)",
          f(flat_day(c1059=101.0), "long")["extended"] is False)
    d3 = flat_day(c1059=100.5)
    d3["10:40"] = (100.0, 105.0, 99.0, 100.0, 1.0)                 # after the first hour: not part of it
    r3 = f(d3, "long")
    d3b = flat_day(c1059=102.0)
    d3b["10:40"] = (100.0, 105.0, 99.0, 100.0, 1.0)
    check("U3 call inside the range -> not extended; a 10:40 bar above the high is not part of the first hour",
          r3["extended"] is False and r3["ib_high"] == 101.0 and f(d3b, "long")["extended"] is True, f"{r3}")
    check("U4 put below the low -> extended; equal -> not; a put is never read against the high",
          f(flat_day(c1059=98.99), "short")["extended"] is True and f(flat_day(c1059=99.0), "short")["extended"] is False
          and f(flat_day(c1059=101.5), "short")["extended"] is False)
    no59 = flat_day(c1059=102.0)
    no59.pop("10:59")
    noib = {k: v for k, v in flat_day(c1059=102.0).items() if k > "10:29"}
    r5 = [f(no59, "long"), f(noib, "long"), f(flat_day(c1059=102.0), "")]
    check("U5 missing 10:59 / no 09:30-10:29 bar / no direction -> unknown with the reason",
          all(r["extended"] is None and r["why"] for r in r5), f"{[(r['extended'], r['why']) for r in r5]}")
    d6 = flat_day(c1059=100.0)
    d6["11:00"] = (100.0, 130.0, 70.0, 130.0, 1.0)
    d6s = flat_day(c1059=100.0)
    d6s["11:00"] = (100.0, 130.0, 70.0, 70.0, 1.0)
    check("U6 closed bars only: an 11:00 bar far outside the range changes nothing",
          f(d6, "long")["extended"] is False and f(d6s, "short")["extended"] is False)

    # ── W: wired into ParkPlan.prepare / generate_signal ──
    import config  # noqa: F401
    from strategy.park import Park
    day, prev = date(2026, 10, 28), date(2026, 10, 27)
    exp = day.isoformat()

    def ms(d, h, m):
        return int(datetime(d.year, d.month, d.day, h, m, tzinfo=ET).timestamp() * 1000)

    def write(sym, today, prev_close):
        if os.path.exists(FEED):
            os.remove(FEED)
        c = sqlite3.connect(FEED)
        c.execute("CREATE TABLE candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, ts_epoch_ms INTEGER NOT NULL, "
                  "open REAL, high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY (symbol, interval, ts_epoch_ms))")
        rows = [(sym, "1m", ms(day, int(k[:2]), int(k[3:])), *v) for k, v in today.items()]
        rows.append((sym, "1m", ms(prev, 15, 59), prev_close, prev_close, prev_close, prev_close, 1.0))
        c.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", rows)
        c.commit()
        c.close()

    class K:
        def __init__(self, sym, strike, bid, ask, side):
            self.strike, self.bid, self.ask, self.delta, self.iv = float(strike), bid, ask, 0.5 if side == "C" else -0.5, .2
            self.mark, self.expiry, self.option_type = (bid + ask) / 2, exp, side
            self.symbol = f"{sym:<6}{day:%y%m%d}{side}{int(strike * 1000):08d}"
            self.streamer_symbol = f".X{side}{strike:g}"

    class Chain:
        def __init__(self, sym, spot):
            self.expiry, self.spot_price, self.calls, self.puts = exp, spot, [], []
            for s in range(int(spot) - 12, int(spot) + 13):
                for call, lst in ((True, self.calls), (False, self.puts)):
                    intr = max(spot - s, 0.0) if call else max(s - spot, 0.0)
                    mid = intr + max(0.05, 1.20 - 0.25 * abs(s - spot))
                    lst.append(K(sym, s, round(mid - .03, 2), round(mid + .03, 2), "C" if call else "P"))

    def session(o, c1030, c1059, c1100, ib_hi=None, ib_lo=None):
        """09:30 open o, a first hour drifting to c1030 inside [ib_lo, ib_hi], flat to 10:58, 10:59 at c1059."""
        d = {}
        for i in range(61):
            p = o + (c1030 - o) * i / 60.0
            d[hm(i)] = (p, p + .05, p - .05, p, 1.0)
        if ib_hi is not None:
            d["09:50"] = (o, ib_hi, o - .05, o, 1.0)
        if ib_lo is not None:
            d["10:10"] = (o, o + .05, ib_lo, o, 1.0)
        for i in range(61, 89):
            d[hm(i)] = (c1030, c1030 + .05, c1030 - .05, c1030, 1.0)
        if c1059 is not None:
            d["10:59"] = (c1030, max(c1030, c1059) + .05, min(c1030, c1059) - .05, c1059, 1.0)
        d["11:00"] = (c1100, c1100 + .05, c1100 - .05, c1100, 1.0)
        return d

    logs = []

    class H(logging.Handler):
        def emit(self, rec):
            logs.append(rec.getMessage())
    lg = logging.getLogger("strategy.park_plan")
    lg.addHandler(H())
    lg.setLevel(logging.INFO)

    def run(sym, today, prev_close, px, hm_now="11:01"):
        write(sym, today, prev_close)
        P = Park()
        prep = P.prepare(price_now=px, now_et=hm_now, chain=Chain(sym, px), prior_close=None, day=day, symbol=sym)
        write(sym, today, prev_close)
        sig = Park().generate_signal(price_now=px, now_et=hm_now, chain=Chain(sym, px), prior_close=None, day=day,
                                     symbol=sym)
        return prep, sig

    # QQQ long, first hour 700 -> 702.1 (inside a 702.5 high), 10:59 at 703.0 = above the high -> extended
    del logs[:]
    prep, sig = run("QQQ", session(700.0, 702.1, 703.0, 703.0, ib_hi=702.5), 699.0, 703.0)
    ck = prep.tick.checks
    check("W1 QQQ extended long: refused at c8_first_hour_extended, rows written, SKIP logged, shadow row on the same tick",
          sig is None and prep.unmet == ["c8_first_hour_extended"]
          and prep.conditions.get("c8_first_hour_extended", (0, 0, True))[2] is False
          and all(k in ck for k in ("close_1059", "ib_high", "ib_low", "c8_first_hour_extended"))
          and "shadow_park_sma50" in ck
          and any("[park] SKIP c8_first_hour_extended QQQ long" in m for m in logs),
          f"sig={sig is not None} unmet={prep.unmet} keys={sorted(ck)[:40]} logs={logs[-2:]}")
    prep, sig = run("QQQ", session(700.0, 702.1, 702.3, 702.4, ib_hi=702.5), 699.0, 702.4)
    check("W2 QQQ long not extended: fires, condition met",
          sig is not None and prep.conditions.get("c8_first_hour_extended", (0, 0, False))[2] is True,
          f"sig={sig is not None} unmet={prep.unmet}")
    prep, sig = run("QQQ", session(700.0, 702.1, None, 703.0, ib_hi=702.5), 699.0, 703.0)
    check("W3 QQQ no 10:59 bar: FAILS OPEN - fires, condition met (unknown)",
          sig is not None and prep.conditions.get("c8_first_hour_extended", (0, 0, False))[2] is True
          and prep.ready, f"sig={sig is not None} unmet={prep.unmet}")
    prep, sig = run("QQQ", session(700.0, 697.9, 697.0, 697.0, ib_lo=697.5), 701.0, 697.0)
    check("W4 QQQ extended short: refused at c8_first_hour_extended",
          sig is None and prep.unmet == ["c8_first_hour_extended"], f"sig={sig is not None} unmet={prep.unmet}")
    _cr = PP.commitment_read

    def _met(t, cond, **k):
        cond("pair_agrees", 1.0, True)
        cond("commitment", 0, True)
        return True
    PP.commitment_read = _met
    try:
        prep, sig = run("CVX", session(230.0, 231.0, 232.0, 232.0, ib_hi=231.5), 229.0, 232.0)
    finally:
        PP.commitment_read = _cr
    check("W5 CVX (equity, commitment held met) extended long: refused at c8_first_hour_extended",
          sig is None and prep.unmet == ["c8_first_hour_extended"]
          and list(prep.conditions).index("commitment") < list(prep.conditions).index("c8_first_hour_extended"),
          f"sig={sig is not None} unmet={prep.unmet} conds={list(prep.conditions)}")

    # ── R: the study's own trades ──
    fx = json.load(open(FIX))["trades"]
    mism, sk, unk, bl, blsk = [], 0, 0, 0, 0
    for r in fx:
        today = {k: (0.0, h, l, 0.0, 1.0) for k, (h, l) in r["ib"].items()}
        if r["c1059"] is not None:
            today["10:59"] = (0.0, 0.0, 0.0, r["c1059"], 1.0)
        v = f(today, "long" if r["side"] == "call" else "short")["extended"]
        if v is None:
            unk += 1
        if v is not r["study_extended"]:
            mism.append((r["day"], r["sym"], r["side"], v, r["study_extended"]))
        sk += bool(v)
        if r["sealed"]:
            bl += 1
            blsk += bool(v)
    check(f"R1 replay on the study's trades: skips {sk}/{len(fx)} (study 63/254), blind {blsk}/{bl} (study 13/77), "
          f"unknown {unk}, every verdict equal",
          not mism and (sk, len(fx), blsk, bl, unk) == (63, 254, 13, 77, 0), f"mismatches {mism[:5]}")

    # ── C: no parameter ──
    cfg = open(os.path.join(ROOT, "config.py")).read()
    src = open(os.path.join(ROOT, "strategy", "park_plan.py")).read()
    c8src = src[src.index("# ── v5.7 (C8.1) — THE FIRST HOUR ALREADY OUTRUN"):src.index("# ── v5.4 (PARK.5) — THE COMMITMENT GATE")]
    conf = open(os.path.join(ROOT, "configure.sh")).read() if os.path.exists(os.path.join(ROOT, "configure.sh")) else ""
    check("C1 no parameter: no C8 key in config.py, no os.environ in the C8 code, no configure.sh item",
          not re.search(r"\bC8|PARK_C8|FIRST_HOUR_EXT", cfg) and "environ" not in c8src
          and not re.search(r"(?i)c8|first.hour.ext", conf))

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} of {len(RAN)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
