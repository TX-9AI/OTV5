#!/usr/bin/env python3
"""
tests/check_sma50_mtf.py  v1.0
EVERY ENTRY RECORDS THE 50 SMA ON 5m / 15m / 1h / 1d, IN POINTS, PERCENT AND ATR UNITS.

v1.0  2026-10-23  OTV4TEST r315 (SMA.2) — born red at r314, where the entry snapshot
      records the 5m 50 SMA only, in points, and has no "sma50_mtf" key.

WHY. The operator, 2026-10-23 13:04 ET: "distance from the 50 SMA upon entry and if
our success rate correlates to either winning the trade or getting the direction
right". The scope he passed on at 13:06 ET: ATR units and percent, on 5m/15m/1h/1d,
signed by trade direction, SMA slope and cross-frame agreement. 13:08 ET: "yes to all".

FIXTURE FROM ARITHMETIC, NOT FROM THE CODE (§0.4). A throwaway feed store (the real
`candles` schema) holds a 1m series whose every value is a closed-form function of its
minute index, so each expected SMA / ATR / slope is computed here from the formula, never
by calling the code under test. Nothing reads or writes the box's real stores.

  M1  build() writes "sma50_mtf" beside an UNCHANGED "sma50_5m", schema v3
  M2  5m / 15m / 1h SMA, ATR and distance equal the closed-form values
  M3  the sign follows the trade: long +, short -; side with / against; pct = dist/sma
  M4  only CLOSED bars count: an in-progress 1m bar at the entry minute changes nothing
  M5  1d excludes the session's in-progress daily bar
  M6  slope_atr equals the closed-form per-bar SMA change over ATR, signed by direction
  M7  a starved frame says why; "agree"/"of" count only frames that were read
  M8  it never raises: a missing store is {"err": ...}, and build() still returns
"""
import json
import os
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# the lander runs checks with system python3, which has no pytz: borrow the venv's
# site-packages, as check_sma50_record does
import glob as _glob                                           # noqa: E402
for _base in (ROOT, os.path.expanduser("~/options-trader")):
    _found = _glob.glob(os.path.join(_base, "venv", "lib", "python*", "site-packages"))
    for _sp in _found:
        if _sp not in sys.path:
            sys.path.insert(1, _sp)
    if _found:
        break
sys.path.insert(0, ROOT)
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name,
                          ("  — " + detail) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


def close(a, b, tol=1e-3):
    return a is not None and b is not None and abs(a - b) <= tol


# ── the fixture: a rising 1m series that WOBBLES inside each bar and WIDENS over time, so the
#    bar high is not its last minute's high and no two bars' true ranges are alike (a straight
#    line made ATR's length and the high's max() untestable - both mutants survived v1.0's draft).
T0 = 1_790_000_000 - 1_790_000_000 % 3600         # an hour boundary (epoch-aligned)
N1M = 60 * 70                                      # 70 hours of 1m bars: enough 1h bars
T_ENTRY = T0 + N1M * 60 + 25                       # 25 s into the minute after the last bar
STEP, HALF = 0.01, 0.1


def c(i):
    # + a 1.0 step at every hour boundary (up, then down): a GAP between bars on every frame,
    # so the true range differs from high - low (that mutant survived the gap-free draft)
    return 100.0 + STEP * i + 0.05 * (((i * 7) % 5) - 2) + 1.0 * ((i // 60) % 2)


def hi(i):
    return c(i) + HALF + 0.0002 * i + 0.03 * (i % 4 == 1)


def lo(i):
    return c(i) - HALF - 0.0001 * i - 0.02 * (i % 3 == 2)


def _store(path, extra=None):
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE candles (symbol TEXT NOT NULL, interval TEXT NOT NULL,
                   ts_epoch_ms INTEGER NOT NULL, open REAL, high REAL, low REAL, close REAL,
                   volume REAL, PRIMARY KEY (symbol, interval, ts_epoch_ms))""")
    rows = []
    for sym in ("FIX", "FIX_EXT"):
        for i in range(N1M):
            rows.append((sym, "1m", (T0 + 60 * i) * 1000, c(i), hi(i), lo(i), c(i), 10.0))
    # 60 daily bars: day k close = 50 + k, range 2.0; the last is "today" (in progress)
    day0 = T_ENTRY - T_ENTRY % 86400 - 59 * 86400
    for k in range(60):
        v = 50.0 + k
        rows.append(("FIX", "1d", (day0 + 86400 * k) * 1000, v, v + 1, v - 1, v, 0.0))
    rows += extra or []
    con.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()


def expected(span_min):
    """Closed-form 50 SMA, ATR(14), slope for bars of span_min 1m bars, all closed by T_ENTRY,
    computed from the fixture's own formulas c/hi/lo - never by the code under test."""
    nbars = N1M // span_min                        # every bar closes by T_ENTRY (T0 aligned)
    mins = lambda j: range(j * span_min, (j + 1) * span_min)  # noqa: E731
    cl = lambda j: c((j + 1) * span_min - 1)                  # noqa: E731
    bh = lambda j: max(hi(i) for i in mins(j))                # noqa: E731
    bl = lambda j: min(lo(i) for i in mins(j))                # noqa: E731
    sma = sum(cl(j) for j in range(nbars - 50, nbars)) / 50
    tr = lambda j: max(bh(j) - bl(j), abs(bh(j) - cl(j - 1)), abs(bl(j) - cl(j - 1)))  # noqa: E731
    atr = sum(tr(j) for j in range(nbars - 14, nbars)) / 14
    prev = sum(cl(j) for j in range(nbars - 55, nbars - 5)) / 50
    return sma, atr, (sma - prev) / 5 / atr


def main():
    from analysis import entry_snapshot as es

    tmp = tempfile.mkdtemp(prefix="chk_sma50_mtf_")
    db = os.path.join(tmp, "feed_store.db")
    _store(db)
    price = c(N1M - 1) + 0.5

    long_ = es.sma50_mtf_context(T_ENTRY, price, "long", db_path=db, symbol="FIX")
    short = es.sma50_mtf_context(T_ENTRY, price, "short", db_path=db, symbol="FIX")

    # M1 — build() payload
    import config
    old = getattr(config, "INSTRUMENT", None)
    os.environ["OT_FEED_DB"] = db
    try:
        config.INSTRUMENT = "FIX"
        payload = es.build({"price": price}, "long")
    finally:
        config.INSTRUMENT = old
    check("M1 build() writes sma50_mtf beside an unchanged sma50_5m, v3",
          payload.get("v") == 3 and "sma50_mtf" in payload and "sma50_5m" in payload
          and set((payload.get("sma50_5m") or {}).keys()) <= {"rth", "ext", "err"},
          json.dumps({k: payload.get(k) for k in ("v", "err")}))

    # M2 — closed-form values
    bad = []
    for name, span in (("5m", 5), ("15m", 15), ("1h", 60)):
        sma, atr, _ = expected(span)
        f = long_["rth"][name]
        if not (close(f.get("sma"), sma) and close(f.get("atr"), atr)
                and close(f.get("dist"), price - sma) and close(f.get("d_atr"), (price - sma) / atr, 2e-3)):
            bad.append((name, f, round(sma, 4), round(atr, 4)))
    check("M2 5m/15m/1h SMA, ATR, distance = closed form", not bad, "%s" % bad)

    # M3 — the sign follows the trade
    f5l, f5s = long_["rth"]["5m"], short["rth"]["5m"]
    check("M3 long +, short -, side with/against, pct = dist/sma",
          close(f5l["dist"], -f5s["dist"]) and f5l["side"] == "with" and f5s["side"] == "against"
          and close(f5l["pct"], f5l["dist"] / f5l["sma"] * 100, 1e-3), "%s %s" % (f5l, f5s))

    # M4 — an in-progress bar (the entry minute) with an absurd close changes nothing
    db2 = os.path.join(tmp, "feed_store_open.db")
    _store(db2, [("FIX", "1m", (T0 + 60 * N1M) * 1000, 1e6, 1e6, 1e6, 1e6, 1.0)])
    lp = es.sma50_mtf_context(T_ENTRY, price, "long", db_path=db2, symbol="FIX")
    check("M4 only CLOSED bars count", all(lp["rth"][n] == long_["rth"][n] for n in ("5m", "15m", "1h")),
          "%s vs %s" % (lp["rth"]["5m"], long_["rth"]["5m"]))

    # M5 — 1d excludes today's bar: closed bars are k = 0..58 -> SMA of 50 + (9..58)
    d = long_["rth"]["1d"]
    exp_sma = sum(50.0 + k for k in range(9, 59)) / 50
    check("M5 1d excludes the in-progress daily bar", close(d.get("sma"), exp_sma),
          "%s expected %.4f" % (d, exp_sma))

    # M6 — slope, signed
    _, _, slope5 = expected(5)
    check("M6 slope_atr = closed form, signed by direction",
          close(f5l.get("slope_atr"), slope5, 1e-4) and close(f5s.get("slope_atr"), -slope5, 1e-4),
          "%s %s expected %.5f" % (f5l.get("slope_atr"), f5s.get("slope_atr"), slope5))

    # M7 — a starved frame (FIX_EXT has no 1d) says why; agree/of count read frames only
    ext = long_["ext"]
    check("M7 starved frame says why; agree/of count read frames",
          ext["1d"].get("sma") is None and "why" in ext["1d"] and ext["of"] == 3
          and ext["agree"] == sum(1 for n in ("5m", "15m", "1h") if ext[n].get("side") == "with")
          and long_["rth"]["of"] == 4, "%s" % {k: ext[k] for k in ("1d", "agree", "of")})

    # M8 — never raises
    gone = es.sma50_mtf_context(T_ENTRY, price, "long", db_path=os.path.join(tmp, "nope", "x.db"),
                                symbol="FIX")
    os.environ["OT_FEED_DB"] = os.path.join(tmp, "nope", "x.db")
    try:
        config.INSTRUMENT = "FIX"
        p2 = es.build({"price": price}, "long")
    finally:
        config.INSTRUMENT = old
        os.environ.pop("OT_FEED_DB", None)
    check("M8 never raises: missing store -> err, build() still returns",
          "err" in gone and isinstance(p2, dict) and p2.get("v") == 3
          and "err" in (p2.get("sma50_mtf") or {}), "%s %s" % (gone, p2.get("sma50_mtf")))

    print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:                                   # noqa: BLE001
        print("  FAIL  M0 the checker could not run: %s: %s" % (type(exc).__name__, exc))
        sys.exit(1)
