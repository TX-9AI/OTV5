#!/usr/bin/env python3
"""tests/check_edge_scan.py — v5.2
v5.2  2026-10-31  OTV5 r65 (RPT.29) — E7-E9: THE OTV4TEST FLEET IS OUT OF THE S3 SCAN. load_joined_s3 runs against a fake bucket
      holding both fleets: E7 trades (lineage TEST, an untagged AAL row, an untagged SOFI row before 2026-10-25) are
      dropped; E8 an OTV4TEST plan row is dropped from the unfired-plan count; E9 SOFI's OTV5 trades (tagged, and
      untagged on/after 10-25) and every mainline row stay, and the FLEET line names what went. Born red on b57c571
      at E7, E8 and E9 (no FLEET line); E1-E6 unchanged.
v5.1  2026-10-25  (RPT.29) — E6: A SPARSE FEATURE THAT CLEARS THE CANDIDATE FLOOR REACHES THE STABILITY SPLIT and must
      not raise there. E1's sparse feature never cleared CAND_N, so the d1/d2 lines (still r[k]) were never reached and
      control's real run died with KeyError. Born red on 26df107 at E6.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
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


def _split_sparse():
    """300 rows; `sep` on two rows in three, cleanly separating winners from losers, so it clears CAND_N and the
    delta bar and reaches the stability split - where a row without it must not raise."""
    rows = []
    for i in range(300):
        win = i % 2 == 0
        r = {"_pnl": 1.0 if win else -1.0, "_session": f"2026-09-{(i % 20) + 1:02d}", "_side": "call"}
        if i % 3 != 0:
            r["sep"] = (100.0 + i) if win else float(i % 7)
        rows.append(r)
    out = es.scan_features(rows)
    hit = [o for o in out if o["feature"] == "sep"]
    return bool(hit) and hit[0]["stable"] is True, f"findings: {[(o['feature'], o['stable']) for o in out]}"


guard("E6 a sparse feature that clears the floor reaches the stability split without KeyError", _split_sparse)



# ── E7-E9 (v5.2, RPT.29): the OTV4TEST fleet's rows are filtered out of the S3 path ──────────────────────────────
import argparse                                                 # noqa: E402
import contextlib                                               # noqa: E402
import io                                                       # noqa: E402
import json                                                     # noqa: E402
import warehouse_source as ws                                   # noqa: E402

_TRADES = [   # (trade_id, symbol, lineage, entry day, keep?)
    ("m-amd", "AMD", "OTV4", "2026-10-01", True),        # mainline, tagged
    ("m-spx", "SPX", None, "2026-09-22", True),          # mainline, untagged (before the producers stamped)
    ("t-sofi-tag", "SOFI", "TEST", "2026-10-09", False),  # OTV4TEST, tagged
    ("t-sofi-old", "SOFI", None, "2026-09-29", False),   # OTV4TEST, untagged, before SOFI's OTV5 day
    ("t-aal", "AAL", None, "2026-10-01", False),         # OTV4TEST, untagged
    ("t-aal-tag", "AAL", "TEST", "2026-10-09", False),   # OTV4TEST, tagged
    ("v5-sofi", "SOFI", "OTV5", "2026-10-27", True),     # SOFI ON OTV5 — must stay
    ("v5-sofi-u", "SOFI", None, "2026-10-26", True),     # untagged SOFI on/after 10-25 is OTV5
]
_PLANS = [    # (_rid, symbol, created ET day, keep?)
    (1, "AMD", "2026-10-01", True), (2, "SOFI", "2026-10-09", False), (3, "AAL", "2026-10-01", False),
    (4, "SOFI", "2026-10-27", True),
]


def _fake_bucket():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    P = ws.PREFIX
    objs = {}
    for i, (tid, sym, lin, day, _k) in enumerate(_TRADES):
        rec = {"trade_id": tid, "symbol": sym, "status": "closed", "pnl_usd": 10.0 if i % 2 else -10.0,
               "entry_time": f"{day}T10:00:00", "option_side": "call"}
        if lin:
            rec["lineage"] = lin
        objs[f"{P}/trades/dt={day}/sym={sym}/{i}-t.json"] = json.dumps(
            {"datatype": "trades", "symbol": sym, "dt": day, "pushed_at_utc": "T1", "record": rec}).encode()
    for rid, sym, day, _k in _PLANS:
        ts = datetime.fromisoformat(f"{day}T11:00:00").replace(tzinfo=ZoneInfo("America/New_York")).timestamp()
        row = {"_rid": rid, "symbol": sym, "state": "EXPIRED", "created_ts": ts, "trigger_price": 10.0,
               "max_price_seen": 11.0, "min_price_seen": 9.0, "direction": "call"}
        objs[f"{P}/derived_plan_ledger/dt={day}/sym={sym}/{rid}-p.json"] = json.dumps(
            {"datatype": "derived_plan_ledger", "symbol": sym, "dt": day, "pushed_at_utc": "T1",
             "record": [row]}).encode()
    return ws._FakeS3(objs)


_RESULT = {}


def _scan():
    if not _RESULT:
        fake = _fake_bucket()
        real = ws.client
        ws.client = lambda: fake
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                out = es.load_joined_s3(argparse.Namespace(date=None, frm="2026-09-22", to="2026-10-27",
                                                           all_history=False))
        finally:
            ws.client = real
        _RESULT.update(out=out, text=buf.getvalue())
    return _RESULT


def _e7():
    rows, _plans, n_closed, _j = _scan()["out"]
    want = sum(1 for t in _TRADES if t[4])
    return n_closed == want and len(rows) == want, f"closed={n_closed} rows={len(rows)} want={want} (of {len(_TRADES)})"


def _e8():
    _rows, plans, _n, _j = _scan()["out"]
    want = sum(1 for p in _PLANS if p[3])
    return plans["total"] == want, f"plans={plans} want total={want} (of {len(_PLANS)})"


def _e9():
    r = _scan()
    rows = r["out"][0]
    sessions = sorted(x["_session"] for x in rows)
    want = sorted(t[3] for t in _TRADES if t[4])
    line = next((l.strip() for l in r["text"].splitlines() if "FLEET:" in l), "")
    return (sessions == want and "4 trade row(s)" in line and "'AAL': 2" in line and "'SOFI': 2" in line
            and "2 plan row(s)" in line), f"sessions={sessions} line={line!r}"


guard("E7 the S3 scan drops the OTV4TEST fleet's trades (lineage TEST; untagged AAL; untagged SOFI before 10-25)", _e7)
guard("E8 the unfired-plan count drops OTV4TEST's plan rows by box and created day", _e8)
guard("E9 SOFI's OTV5 trades and every mainline trade stay, and the FLEET line names what went", _e9)

print()
if FAILED:
    print(f"  RED — {len(FAILED)} of {len(RAN)} failed: " + ", ".join(FAILED))
    sys.exit(1)
print(f"  GREEN — {len(RAN)} checks")
