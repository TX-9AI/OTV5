#!/usr/bin/env python3
"""
tests/check_macro_vix_retry.py  v5.0
v5.0  2026-10-27  OTV5 r43 (MACRO.1) — A RATE-LIMITED VIX FETCH IS RETRIED, AND A DEFAULTED SNAPSHOT IS RE-FETCHED SOON.
      2026-10-27 09:15 ET wake: all 14 boxes called TastyTrade GET /market-data/Index/VIX in the same second; CRM,
      GOOGL and NFLX got HTTP 429 at 13:15:36 UTC, logged "Could not fetch VIX — defaulting to 20 (conservative)",
      and ran butterfly_allowed False / RISK_OFF for 60 minutes while the real VIX was 17.88-18.04 (nine trade rows
      carry vix_at_entry 20.0). Driven through the REAL MacroManager; data.market_data.fetch_quote, the calendar's
      requests.get, time.sleep and time.time are stubbed (no network, no real waits).

  V1  a 429 then 17.9: the snapshot carries 17.9, not 20, vix_is_default False, butterfly_allowed True, NEUTRAL
  V2  three failures: the default 20 with vix_is_default True, two INFO retries and the WARNING logged
  V3  a defaulted snapshot is re-fetched by get() after the short interval; a measured one is not before 60 min
  V4  the total retry sleep is bounded (each sleep 0.5-2.0 s, two sleeps, sum <= 5 s over 200 all-fail runs)

Born red on a6d024b at V1, V2, V3 and V4.
Run:  python3 tests/check_macro_vix_retry.py
"""
import logging
import os
import shutil
import sys
import tempfile
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "CRM")
_s = tempfile.mkdtemp(prefix="check_macro_vix_retry.")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_s, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(); self.recs = []

    def emit(self, r):
        if r.name == "data.macro_data":
            self.recs.append((r.levelno, r.getMessage()))


class _Feed:
    """fetch_quote stand-in: plays a script of values / exceptions, then repeats the last."""
    def __init__(self, script):
        self.script, self.calls = list(script), 0

    def __call__(self, symbol):
        assert symbol == "VIX", symbol
        item = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item


def _429():
    return Exception("429 Client Error: Too Many Requests for url: https://api.tastyworks.com/market-data/Index/VIX")


def main():
    import data.macro_data as MD
    import data.market_data as MKT
    cap = _Cap(); lg = logging.getLogger("data.macro_data"); lg.addHandler(cap); lg.setLevel(logging.DEBUG)
    sleeps = []
    clock = [1_793_107_000.0]
    no_cal = mock.MagicMock(status_code=503)

    def run(feed, fn):
        with mock.patch.object(MKT, "fetch_quote", feed), \
             mock.patch.object(MD.requests, "get", lambda *a, **k: no_cal), \
             mock.patch.object(MD.time, "sleep", lambda s: sleeps.append(s)), \
             mock.patch.object(MD.time, "time", lambda: clock[0]):
            return fn()

    # V1 — a 429, then the real value
    cap.recs.clear(); sleeps.clear()
    f1 = _Feed([_429(), 17.9])
    s1 = run(f1, lambda: MD.MacroManager().get())
    check("V1 a 429 then 17.9: the snapshot carries the real VIX and its gates",
          abs(s1.vix - 17.9) < 1e-9 and getattr(s1, "vix_is_default", None) is False
          and s1.butterfly_allowed is True and s1.macro_context == "NEUTRAL" and f1.calls == 2,
          f"vix={s1.vix} default={getattr(s1, 'vix_is_default', 'n/a')} butterfly={s1.butterfly_allowed} "
          f"context={s1.macro_context} calls={f1.calls}")

    # V2 — three failures fall back to the conservative default
    cap.recs.clear(); sleeps.clear()
    f2 = _Feed([_429(), None, _429()])
    s2 = run(f2, lambda: MD.MacroManager().get())
    infos = [m for lv, m in cap.recs if lv == logging.INFO and "retrying" in m]
    warns = [m for lv, m in cap.recs if lv == logging.WARNING and "defaulting to 20" in m]
    check("V2 three failures: default 20, vix_is_default True, two INFO retries, the WARNING",
          s2.vix == 20.0 and getattr(s2, "vix_is_default", None) is True and f2.calls == 3
          and len(infos) == 2 and len(warns) == 1 and s2.butterfly_allowed is False,
          f"vix={s2.vix} default={getattr(s2, 'vix_is_default', 'n/a')} calls={f2.calls} "
          f"infos={len(infos)} warns={len(warns)}")

    # V3 — the defaulted snapshot is re-fetched soon; a measured one keeps the hour
    sleeps.clear()
    mgr = MD.MacroManager()
    f3 = _Feed([_429(), _429(), _429(), 18.0])
    t0 = clock[0]
    a = run(f3, mgr.get)                                 # defaulted at t0 (3 calls)
    clock[0] = t0 + 30
    b = run(f3, mgr.get)                                 # 30 s later: still the cached default
    calls_b = f3.calls
    clock[0] = t0 + 150
    c = run(f3, mgr.get)                                 # 2.5 min later: re-fetched, measured 18.0
    calls_c = f3.calls
    clock[0] = t0 + 150 + 59 * 60
    d = run(f3, mgr.get)                                 # measured, 59 min on: not re-fetched
    calls_d = f3.calls
    clock[0] = t0 + 150 + 61 * 60
    run(f3, mgr.get)                                     # 61 min on: re-fetched
    calls_e = f3.calls
    clock[0] = t0
    check("V3 a defaulted snapshot is re-fetched after the short interval, a measured one keeps 60 min",
          a.vix == 20.0 and b is a and calls_b == 3 and calls_c == 4 and abs(c.vix - 18.0) < 1e-9
          and getattr(c, "vix_is_default", None) is False and d is c and calls_d == 4 and calls_e == 5,
          f"a={a.vix} b_same={b is a} calls={calls_b}/{calls_c}/{calls_d}/{calls_e} c={c.vix} d_same={d is c}")

    # V4 — the retry wait is bounded
    totals, counts, each_ok = [], set(), True
    for _ in range(200):
        sleeps.clear()
        run(_Feed([_429()]), lambda: MD.MacroManager().get())
        totals.append(sum(sleeps)); counts.add(len(sleeps))
        each_ok = each_ok and all(0.5 <= x <= 2.0 for x in sleeps)
    check("V4 total retry sleep bounded: two sleeps of 0.5-2.0 s, sum <= 5 s",
          counts == {2} and each_ok and max(totals) <= 5.0 and min(totals) >= 1.0,
          f"sleeps per run={sorted(counts)} max total={max(totals):.2f}s each_in_range={each_ok}")

    shutil.rmtree(_s, ignore_errors=True)
    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
