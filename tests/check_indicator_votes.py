#!/usr/bin/env python3
"""tests/check_indicator_votes.py — v1.0
THE PER-TIMEFRAME INDICATOR LOOP ACTUALLY RUNS, AND THE EMAs REACH THE STORE.

v1.0  2026-09-20 — OTV4TEST r69 (IND.1). `TrendState.votes` is a
      `Dict[str, TrendVote]`, and `derived/indicators.py` iterated it as
      `list(trend.votes)` — which yields the KEYS. Every "vote" was the string
      '5m'/'15m'/…, every `getattr(vote,"timeframe")` returned None, and the
      loop `continue`d all of them. `rows` stayed empty on every tick and the
      fallback wrote the four EMAs as None.
      🔴 MEASURED BEFORE THE FIX: **0 of 18,529 rows** in `indicator_series`
      had ever carried an `ema_fast`, and **every** row was `interval='primary'`.
      So the per-frame loop — whose own comment says it exists "so ADX is
      recorded PER FRAME rather than only the primary … what a later study
      needs to see disagreement" — had never once executed.
      ⚠️ AND THE 2026-08-24 FALLBACK FIX MASKED IT PERMANENTLY: it keyed the
      fallback on the OUTCOME so a gap renders as thin rows rather than no
      rows. That was correct and it worked — which is exactly why nobody
      looked again. The symptom was fixed; the cause survived.

  V0  the real TrendState really is a Dict (if it ever becomes a list, this
      whole check is about nothing and should be re-derived — §40.1)
  V1  driving the REAL derive() with votes writes ONE ROW PER TIMEFRAME
  V2  ...and those rows carry NON-NULL EMAs
  V3  ...and a non-'primary' interval, which is what the study needs
  V4  CONTROL: with NO votes the fallback still writes exactly one primary row
      (the 2026-08-24 behaviour must not regress)
  V5  CONTROL: the fallback row still carries ADX/ATR/VWAP, only the EMAs null

⚠️ IT COMMITS THE WAY THE REGISTRY DOES. `_write` batches and does not commit;
the real tick calls `store.commit()` afterwards. A first cut omitted that, read
through a second connection, and went red on correct code — recorded at the
call site.

⚠️ IT DRIVES `IndicatorEngine.derive()` AND READS WHAT LANDED IN A REAL SQLITE
STORE — not the source text, and not my own re-implementation of the loop
(§0.4, §21). The store is a scratch file; nothing here can reach a live one.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def guard(name, fn, detail=lambda: ""):
    try:
        ok = bool(fn())
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"raised {type(exc).__name__}: {exc}")
        return False
    try:
        d = detail()
    except Exception:                                           # noqa: BLE001
        d = ""
    check(name, ok, d)
    return ok


TMP = tempfile.mkdtemp(prefix="indvotes_")
os.environ["OT_DERIVED_DB"] = os.path.join(TMP, "derived_store.db")

try:
    from analysis.trend_engine import TrendState, TrendVote
    from derived.indicators import IndicatorEngine
    from data.derived_store import DerivedStore
    IMPORT_ERR = None
except Exception as exc:                                        # noqa: BLE001
    IMPORT_ERR = "%s: %s" % (type(exc).__name__, exc)

if IMPORT_ERR:
    for n in ("V0", "V1", "V2", "V3", "V4", "V5"):
        check(n + " (not reached)", False, IMPORT_ERR)
    print("\nRED — imports failed: " + IMPORT_ERR)
    sys.exit(1)


import dataclasses                                              # noqa: E402

guard("V0 TrendState.votes is a Dict (the premise this check rests on)",
      lambda: "Dict" in str(
          {f.name: f.type for f in dataclasses.fields(TrendState)}["votes"]),
      lambda: str({f.name: f.type for f in dataclasses.fields(TrendState)}["votes"]))


def _store():
    p = os.path.join(TMP, "s_%d.db" % len(os.listdir(TMP)))
    return DerivedStore(p), p


def _vote(tf, ef):
    v = TrendVote(timeframe=tf)
    v.adx = 30.0
    v.ema_fast, v.ema_mid, v.ema_slow, v.ema_anchor = ef, ef - 1, ef - 2, ef - 3
    return v


class _Vol:
    atr_current = 0.44
    atr_normalized = 0.0006


def _run(votes):
    st, path = _store()
    eng = IndicatorEngine(store=st, symbol="QQQ")
    trend = TrendState()
    if votes:
        trend.votes = {v.timeframe: v for v in votes}
    trend.primary_adx = 27.5
    eng.derive({"symbol": "QQQ", "trend": trend, "vol": _Vol(), "df_1m": None})
    # ⚠️ MY OWN FIXTURE WAS WRONG HERE FIRST, AND IT IS RECORDED RATHER THAN
    # TIDIED. `DerivedStore._write` BATCHES — it never commits; the registry
    # calls `store.commit()` once per tick after every engine has written. So
    # a second connection saw 0 rows and all six checks went red against
    # CORRECT code. A fixture that skips a step the real caller performs is
    # testing its own omission (§0.4).
    st.commit()
    con = sqlite3.connect(path)
    rows = con.execute("SELECT interval, adx, atr, ema_fast, ema_mid, ema_slow,"
                       " ema_anchor FROM indicator_series").fetchall()
    con.close()
    return rows


R = {}
guard("V1 driving derive() with votes writes ONE ROW PER TIMEFRAME",
      lambda: len(R.setdefault("multi", _run([_vote("5m", 100.0),
                                              _vote("15m", 200.0),
                                              _vote("1h", 300.0)]))) == 3,
      lambda: "%d row(s): %s" % (len(R.get("multi", [])),
                                 [r[0] for r in R.get("multi", [])]))

guard("V2 those rows carry NON-NULL EMAs",
      lambda: all(r[3] is not None and r[4] is not None
                  and r[5] is not None and r[6] is not None
                  for r in R["multi"]) and len(R["multi"]) == 3,
      lambda: str([(r[0], r[3]) for r in R.get("multi", [])]))

guard("V3 ...and a non-'primary' interval (the per-frame study signal)",
      lambda: {r[0] for r in R["multi"]} == {"5m", "15m", "1h"},
      lambda: str(sorted({r[0] for r in R.get("multi", [])})))

guard("V4 CONTROL: with NO votes the fallback still writes one primary row",
      lambda: len(R.setdefault("none", _run([]))) == 1
      and R["none"][0][0] == "primary",
      lambda: str(R.get("none")))

guard("V5 CONTROL: the fallback row keeps ADX/ATR, only the EMAs are null",
      lambda: R["none"][0][1] is not None and R["none"][0][2] is not None
      and R["none"][0][3] is None,
      lambda: "adx=%s atr=%s ema_fast=%s" % R["none"][0][1:4])

print()
if FAILED:
    print(f"RED — {len(FAILED)} of {len(RAN)}: " + ", ".join(FAILED))
    sys.exit(1)
print(f"GREEN — {len(RAN)} checks")
sys.exit(0)
