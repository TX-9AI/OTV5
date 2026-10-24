#!/usr/bin/env python3
"""
tests/check_recorder_keys.py  v1.1
v1.1  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.0  2026-10-03  OTV4TEST r213 (REC.1) — THE RECORDERS' MISSING INPUTS ARE PUBLISHED, AND THE NOTE FIELDS FILL.

  The 10-03 audit (B12): derived/notes, derived/snapshot and the plan ledger
  read ten ctx keys nothing ever set, so every field built on them was NULL.
  The operator, 2026-10-03: "Gather as much as is available to serve our
  studies and backtests."

  N1  the REAL main._publish_recorder_keys sets expected_move, gex_pin,
      pin_concentration and prev_close from what the tick holds
  N2  what cannot be read stays ABSENT (no gex, no gap, a zero pin -> no key),
      and a key that already holds a value is not overwritten
  N3  the REAL measure_gap returns prior_close and today_open beside gap_pct
  N4  THE CONSUMER: the REAL NoteWriter's butterfly vector carries the pin,
      its distance over the expected move and the concentration; the
      runaway's carries prev_close - all None before the keys existed
  N5  it is called once, after _apply_vol_ports and before the engines run
      (a source check, stated as one)

Run:  python3 tests/check_recorder_keys.py   (exit 0 green, 1 red)
"""
import glob as _glob
import os
import sys
import tempfile
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_recorder_keys_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ["OT_PAPER_TRADING"] = "1"

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    import main as M
    pub = getattr(M, "_publish_recorder_keys", None)
    gex = types.SimpleNamespace(pin_strike=752.0, pin_concentration=0.31, net_gex=1.0)
    full = {"price": 750.0, "gex": gex, "expected_move_iv": 4.0,
            "gap": {"gap_pct": 0.4, "gap_abs_pct": 0.4, "prior_close": 747.0, "today_open": 750.0}}
    try:
        ctx = dict(full)
        pub(ctx)
        check("N1 expected_move 4.0, gex_pin 752, pin_concentration 0.31 and prev_close 747 are published",
              (ctx.get("expected_move"), ctx.get("gex_pin"), ctx.get("pin_concentration"), ctx.get("prev_close"))
              == (4.0, 752.0, 0.31, 747.0), str({k: ctx.get(k) for k in ("expected_move", "gex_pin", "pin_concentration", "prev_close")}))
        bare = {"price": 750.0, "gex": types.SimpleNamespace(pin_strike=0.0, pin_concentration=None), "gap": None,
                "prev_close": 123.0}
        pub(bare)
        check("N2 a zero pin, no concentration, no gap and no implied move publish NOTHING; an existing value is kept",
              "gex_pin" not in bare and "pin_concentration" not in bare and "expected_move" not in bare
              and bare.get("prev_close") == 123.0, str({k: v for k, v in bare.items() if k not in ("gex",)}))
    except Exception as exc:                                  # noqa: BLE001
        check("N1 (did not run)", False, f"{type(exc).__name__}: {exc}")
        check("N2 (did not run)", False, "see N1")

    try:
        import pandas as pd
        from analysis.gap_measure import measure_gap
        idx = list(pd.date_range("2026-10-02 15:50", periods=2, freq="5min", tz="America/New_York")) + \
            list(pd.date_range("2026-10-05 09:30", periods=2, freq="5min", tz="America/New_York"))
        df = pd.DataFrame({"open": [746.0, 746.5, 750.0, 750.5], "high": [747, 747.2, 751, 751],
                           "low": [745.8, 746.4, 749.5, 750.2], "close": [746.5, 747.0, 750.5, 750.8]}, index=idx)
        g = measure_gap(df)
        check("N3 measure_gap returns prior_close 747.0 and today_open 750.0 beside the same gap_pct",
              g is not None and g.get("prior_close") == 747.0 and g.get("today_open") == 750.0
              and abs(g.get("gap_pct") - round(100 * 3.0 / 747.0, 4)) < 1e-9, str(g))
    except Exception as exc:                                  # noqa: BLE001
        check("N3 (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        from derived.notes import NoteWriter
        nw = NoteWriter(None, "QQQ")
        before = dict(full); before["_flow_conn"] = None
        b_fly = nw._specific("GEXPinButterfly", before)
        b_run = nw._specific("RunawayContinuation", before)
        after = dict(full); after["_flow_conn"] = None
        pub(after)
        a_fly = nw._specific("GEXPinButterfly", after)
        a_run = nw._specific("RunawayContinuation", after)
        check("N4 the butterfly note gains pin 752, distance/EM 0.5 and concentration 0.31; the runaway note prev_close 747",
              b_fly.get("gex_pin") is None and b_run.get("prev_close") is None
              and a_fly.get("gex_pin") == 752.0 and abs(a_fly.get("pin_distance_over_em") - 0.5) < 1e-9
              and a_fly.get("pin_concentration") == 0.31 and a_run.get("prev_close") == 747.0,
              f"before {b_fly} / {b_run}; after {a_fly} / {a_run}")
    except Exception as exc:                                  # noqa: BLE001
        check("N4 (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        src = open(os.path.join(_root, "main.py")).read()
        i_vol = src.find("    _apply_vol_ports(ctx)")
        i_pub = src.find("    _publish_recorder_keys(ctx)")
        i_run = src.find("run_all(", i_vol)
        check("N5 called once, after _apply_vol_ports and before the engines run (source check)",
              0 < i_vol < i_pub < i_run and src.count("    _publish_recorder_keys(ctx)") == 1,
              f"positions vol {i_vol}, publish {i_pub}, run_all {i_run}")
    except Exception as exc:                                  # noqa: BLE001
        check("N5 (did not run)", False, f"{type(exc).__name__}: {exc}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — the recorders' inputs are published and the note fields fill")
    return 0


if __name__ == "__main__":
    sys.exit(main())
