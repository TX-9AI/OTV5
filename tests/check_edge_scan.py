#!/usr/bin/env python3
"""tests/check_edge_scan.py — v1.0
THE EDGE SCAN SURVIVES A HETEROGENEOUS BOOK (RPL.3).

v1.0  2026-09-19  OTV4TEST r63 — `edge_scan` CRASHED ON THE REAL BOOK while its
      own selftest printed ALL PASS. `scan_features` built `feats` as the UNION
      of feature keys across rows and then indexed `r[k]` per row, so the first
      row missing a sparse feature raised `KeyError: 'adx'`. It is not a
      `check_*.py`, so the sweep never touched it, and the tool whose whole job
      is finding where the edge lives could not run at all.

🔑 THE FIXTURE IS HETEROGENEOUS ON PURPOSE. The selftest that passed used rows
carrying the SAME keys — which is the one shape that cannot expose this. Real
fire snapshots are sparse (r31/MEAS.4 recorded ADX absent or zero on most
rows), so the gate builds rows where one feature is present on some and missing
on others. A fixture that mirrors the code's assumption cannot fail (§0.4).

  E1  scan_features survives rows with MISSING feature keys (the crash)
  E2  a feature present on only some rows still contributes from the rows that have it
  E3  the tool's own selftest still passes
  E4  the pre-registered bar is unchanged — it is not softened to produce output
  E5  a feature below the candidate floor yields no finding (the bar binds)

Born red at e56acb2 on E1 and E2 (KeyError). E3/E4/E5 are CONTROLS, green on
both sides.
Run:  python3 tests/check_edge_scan.py
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "tests"))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def guard(name, fn):
    try:
        ok, detail = fn()
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"{type(exc).__name__}: {exc}")
        return
    check(name, bool(ok), detail)


import edge_scan as es                                          # noqa: E402


def _rows(n=80):
    """Half the rows carry `adx`, none of the rest do — the real shape."""
    out = []
    for i in range(n):
        r = {"_pnl": 1.0 if i % 2 == 0 else -1.0,
             "_session": f"2026-09-{(i % 12) + 1:02d}",
             "_side": "call",
             "always_here": float(i)}
        # ⚠️ SPARSITY MUST NOT CORRELATE WITH THE PNL SIGN. My first fixture put
        # `adx` on exactly the winning rows, so the `win` comprehension never
        # touched a row missing the key and a mutation to that line alone went
        # UNDETECTED — the gate was green on the restored defect. Every third
        # row, independent of outcome, so BOTH comprehensions meet a gap.
        if i % 3 == 0:
            r["adx"] = float(i)
        out.append(r)
    return out


guard("E1 scan_features survives rows with MISSING feature keys",
      lambda: (isinstance(es.scan_features(_rows()), list), ""))


def _contributes():
    """A sparse feature must still be considered, not silently dropped whole."""
    rows = _rows()
    feats = sorted({k for r in rows for k in r if not k.startswith("_")})
    return ("adx" in feats and "always_here" in feats
            and isinstance(es.scan_features(rows), list)), f"features seen: {feats}"


guard("E2 a sparse feature still contributes from the rows that have it",
      _contributes)
guard("E3 edge_scan's own selftest passes",
      lambda: (es.selftest() == 0, ""))
guard("E4 the pre-registered bar is unchanged (never softened for output)",
      lambda: (es.BAR == {"n": 200, "sessions": 10, "p": 0.05, "delta": 0.147}
               and es.CAND_N == 30, repr(es.BAR)))


def _bar_binds():
    """Below the candidate floor there must be no finding, however clean."""
    rows = [{"_pnl": 1.0 if i % 2 == 0 else -1.0, "_session": "2026-09-01",
             "_side": "call", "sep": (100.0 if i % 2 == 0 else 0.0)}
            for i in range(10)]                 # n=5/side, well under CAND_N
    return es.scan_features(rows) == [], ""


guard("E5 a feature below the candidate floor yields no finding", _bar_binds)

print()
if FAILED:
    print(f"  RED — {len(FAILED)} of {len(RAN)} failed: " + ", ".join(FAILED))
    sys.exit(1)
print(f"  GREEN — {len(RAN)} checks")
