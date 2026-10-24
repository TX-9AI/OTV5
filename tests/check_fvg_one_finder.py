#!/usr/bin/env python3
"""
tests/check_fvg_one_finder.py  v1.0
v1.0  2026-10-03  OTV4TEST r221 (UTIL.1) — ONE FAIR-VALUE-GAP FINDER, AND IT FINDS EXACTLY WHAT THE TWO COPIES FOUND.

  The 10-03 audit (C11): analysis/structure_analyzer and execution/exit_engine
  each carried the same 3-candle FVG loop. The operator, 2026-10-03: "yes I
  want the centralized modules ... thoroughly and proven."

  The two OLD loops are kept here, verbatim, as the reference.
  F1  on 300 random frames (and the empty, 2-bar and flat cases) the shared
      finder returns exactly the structure analyzer's old gaps, in order
  F2  the REAL exit_engine._find_1m_fvgs returns exactly its old result
  F3  the REAL StructureAnalyzer._find_fvgs fills the map exactly as before
      (newest first, at most ten)
  F4  neither module still carries the loop (a source check, stated as one)

Run:  python3 tests/check_fvg_one_finder.py   (exit 0 green, 1 red)
"""
import glob as _glob
import os
import random
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_fvg_one_finder_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def old_structure(df, MIN):
    out = []
    if len(df) < 3:
        return out
    for i in range(2, len(df)):
        gap_bot = float(df["high"].iloc[i - 2])
        gap_top = float(df["low"].iloc[i])
        if gap_top > gap_bot:
            size_pct = (gap_top - gap_bot) / gap_bot
            if size_pct >= MIN:
                out.append((gap_top, gap_bot, size_pct, "bullish", i))
        gap_top2 = float(df["low"].iloc[i - 2])
        gap_bot2 = float(df["high"].iloc[i])
        if gap_bot2 < gap_top2:
            size_pct = (gap_top2 - gap_bot2) / gap_top2
            if size_pct >= MIN:
                out.append((gap_top2, gap_bot2, size_pct, "bearish", i))
    return out


def frames():
    import pandas as pd
    rnd = random.Random(20261003)
    out = [pd.DataFrame({"open": [], "high": [], "low": [], "close": []}),
           pd.DataFrame({"open": [1.0, 1.0], "high": [1.1, 1.1], "low": [0.9, 0.9], "close": [1.0, 1.0]}),
           pd.DataFrame({"open": [5.0] * 20, "high": [5.0] * 20, "low": [5.0] * 20, "close": [5.0] * 20})]
    for _ in range(300):
        n = rnd.randint(3, 90); px = rnd.uniform(5, 800); rows = []
        for _i in range(n):
            px *= 1 + rnd.gauss(0, 0.004)
            hi = px * (1 + abs(rnd.gauss(0, 0.0015))); lo = px * (1 - abs(rnd.gauss(0, 0.0015)))
            rows.append((px, hi, lo, rnd.uniform(lo, hi)))
        out.append(pd.DataFrame(rows, columns=["open", "high", "low", "close"]))
    return out


def main():
    try:
        from config import FVG_MIN_SIZE_PCT as MIN
        from utils.math_utils import find_fvgs
        F = frames()
        bad = [i for i, df in enumerate(F) if find_fvgs(df, MIN) != old_structure(df, MIN)]
        total = sum(len(old_structure(df, MIN)) for df in F)
        check(f"F1 the shared finder equals the old loop on {len(F)} frames ({total} gaps)", not bad and total > 500,
              f"differs on frames {bad[:5]}, gaps {total}")
    except Exception as exc:                                  # noqa: BLE001
        check("F1 (did not run)", False, f"{type(exc).__name__}: {exc}")
        F, MIN = [], 0.0

    try:
        import execution.exit_engine as XE
        bad = []
        for i, df in enumerate(F):
            want = [(t, b, d, ix) for t, b, _s, d, ix in sorted(old_structure(df, MIN), key=lambda g: g[4], reverse=True)]
            got = [(g.top, g.bottom, g.direction, g.index) for g in XE._find_1m_fvgs(df)]
            if got != want:
                bad.append(i)
        check("F2 exit_engine._find_1m_fvgs returns exactly its old result (newest first)", not bad and bool(F), f"differs on {bad[:5]}")
    except Exception as exc:                                  # noqa: BLE001
        check("F2 (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        import analysis.structure_analyzer as SA
        an = SA.StructureAnalyzer.__new__(SA.StructureAnalyzer)
        bad = []
        for i, df in enumerate(F):
            smap = SA.StructureMap()
            an._find_fvgs(smap, df, "5m")
            want = sorted(old_structure(df, MIN), key=lambda g: g[4], reverse=True)[:10]
            got = [(g.top, g.bottom, g.size_pct, g.direction, g.index) for g in smap.fvgs]
            if got != want:
                bad.append(i)
        check("F3 StructureAnalyzer._find_fvgs fills the map exactly as before (newest first, at most ten)",
              not bad and bool(F), f"differs on {bad[:5]}")
    except Exception as exc:                                  # noqa: BLE001
        check("F3 (did not run)", False, f"{type(exc).__name__}: {exc}")

    try:
        a = open(os.path.join(_root, "analysis", "structure_analyzer.py")).read()
        b = open(os.path.join(_root, "execution", "exit_engine.py")).read()
        check("F4 neither module still carries the loop; both call utils.math_utils.find_fvgs",
              "gap_bot2" not in a and "gap_bot2" not in b and a.count("find_fvgs(df, FVG_MIN_SIZE_PCT)") == 1
              and b.count("find_fvgs(df_1m, FVG_MIN_SIZE_PCT)") == 1)
    except Exception as exc:                                  # noqa: BLE001
        check("F4 (did not run)", False, f"{type(exc).__name__}: {exc}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — one FVG finder, identical to both old copies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
