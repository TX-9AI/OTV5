#!/usr/bin/env python3
"""
tests/check_surface_columns.py  v1.1
v1.1  2026-10-03  OTV4TEST r215 (DER.3) — U3 RESTATED, U5 ADDED: gamma_flow is the change in a strike's net GEX since the
      engine's previous reading ("Concur, populate it"). U3: the FIRST reading writes NULL. U5: the second
      writes now minus before for a strike in both snapshots, and NULL for one that is not.
v1.0  2026-10-03  OTV4TEST r212 (DER.2) — surface_series CARRIES iv, dt_seconds AND d_vol; gamma_flow STAYS EMPTY.

  The 10-03 audit (B7): the three columns were the literal None on every row
  ever written (1.89M on this box). The operator, 2026-10-03: "Gather as much
  as is available to serve our studies and backtests."

  Drives the REAL SurfaceEngine and DerivedStore against a scratch feed db.
  U1  a contract whose delta and IV both moved: the row carries the newest IV
      (0.23), the 600 s between the two samples, and the IV change (+0.03)
  U2  a contract whose IV did NOT move: vanna stays NULL (no denominator) and
      d_vol is the measured 0.0 - a flat IV is a reading, not an absence
  U3  gamma_flow is NULL on the first reading
  U5  on the next reading it is the strike's net-GEX change; NULL where either snapshot lacks the strike
  U4  charm and vanna are the numbers second_order returns - nothing else moved

Run:  python3 tests/check_surface_columns.py   (exit 0 green, 1 red)
"""
import glob as _glob
import os
import sqlite3
import sys
import tempfile
import time

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_surface_columns_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ[_k] = os.path.join(_S, _f)
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    try:
        from data.derived_store import DerivedStore
        from derived.surface import SurfaceEngine
        from analysis import second_order as so
        feed = sqlite3.connect(os.path.join(_S, "feed.db"), check_same_thread=False)
        feed.execute("CREATE TABLE greeks_series (streamer_symbol TEXT, ts_epoch REAL, delta REAL, volatility REAL)")
        now = time.time()
        A, B = ".QQQ261005C750", ".QQQ261005P740"
        rows = [(A, now - 610, 0.40, 0.20), (A, now - 10, 0.38, 0.23),
                (B, now - 610, -0.30, 0.25), (B, now - 10, -0.31, 0.25)]
        feed.executemany("INSERT INTO greeks_series VALUES (?,?,?,?)", rows)
        feed.commit()
        st = DerivedStore()
        eng = SurfaceEngine(st, "QQQ", feed_conn=feed)
        import types
        def _snap(d):
            return types.SimpleNamespace(net_gex=sum(d.values()),
                                         strikes=[types.SimpleNamespace(strike=k, net_gex=v) for k, v in d.items()])
        n = eng.derive({"symbol": "QQQ", "expiry": "2026-10-05", "gex": _snap({750.0: 1000.0, 745.0: 5.0})})
        got = {r[0]: r[1:] for r in st.conn.execute(
            "SELECT strike, charm, vanna, gamma_flow, iv, dt_seconds, d_vol FROM surface_series")}
        a, b = got.get(750.0), got.get(740.0)
        check("U1 the moved contract carries iv 0.23, dt 600 s and d_vol +0.03",
              n == 2 and a is not None and abs(a[3] - 0.23) < 1e-9 and abs(a[4] - 600.0) < 1e-6 and abs(a[5] - 0.03) < 1e-9,
              f"rows {n}, 750 -> {a}")
        check("U2 the flat-IV contract: vanna NULL, d_vol the measured 0.0, iv 0.25",
              b is not None and b[1] is None and b[5] == 0.0 and abs(b[3] - 0.25) < 1e-9 and abs(b[4] - 600.0) < 1e-6,
              f"740 -> {b}")
        check("U3 gamma_flow is NULL on the FIRST reading (nothing to difference against)",
              all(v[2] is None for v in got.values()) and len(got) == 2, str(got))
        ra = [(t, d, v) for s, t, d, v in rows if s == A]
        check("U4 charm and vanna equal second_order's own numbers",
              a is not None and abs(a[0] - so.charm(ra)) < 1e-9 and abs(a[1] - so.vanna(ra)) < 1e-9,
              f"{a and a[:2]} vs {(so.charm(ra), so.vanna(ra))}")
        time.sleep(1.1)                                       # a new ts_epoch: the table's key includes it
        eng.derive({"symbol": "QQQ", "expiry": "2026-10-05", "gex": _snap({750.0: 1400.0, 740.0: -300.0})})
        last = {}
        for k_, gf, ts_ in st.conn.execute("SELECT strike, gamma_flow, ts_epoch FROM surface_series ORDER BY ts_epoch"):
            last[k_] = gf
        check("U5 the second reading: 750 flowed +400 (1400 - 1000); 740, absent from the first snapshot, stays NULL",
              last.get(750.0) == 400.0 and last.get(740.0) is None, str(last))
    except Exception as exc:                                  # noqa: BLE001
        for n_ in ("U1", "U2", "U3", "U4", "U5"):
            if n_ not in FAILED:
                check(f"{n_} (did not run)", False, f"{type(exc).__name__}: {exc}")
    if FAILED:
        print(f"\nRED — {len(set(FAILED))} check(s): {sorted(set(FAILED))}")
        return 1
    print("\nGREEN — the surface rows carry iv, dt_seconds, d_vol and gamma_flow as measured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
