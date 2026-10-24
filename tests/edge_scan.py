#!/usr/bin/env python3
"""
tests/edge_scan.py  v1.3
v1.3  2026-09-19  OTV4TEST r63 — CRASHED ON THE REAL BOOK WHILE ITS SELFTEST
      PASSED. `scan_features` built `feats` as the UNION of feature keys across
      rows and then indexed `r[k]` per row, so the first row missing a sparse
      feature raised `KeyError: 'adx'`. The tool whose job is finding where the
      edge lives could not run at all, and nothing said so because it is not a
      `check_*.py` and was therefore invisible to the sweep.
v1.2  2026-09-07  r299 - relaxed rows kept (operator ruling: it is all paper, and paper vs live is the split that matters).
v1.1  2026-08-23  S3 default source: trades from raw/trades, fire snapshots
and plans from raw/derived_* (s3_push v4.3, latest-per-rid). --db/--derived
remain the explicit local escape hatch. The bar is unchanged and will not be
softened to produce output; NOT YET is the expected answer for weeks.
v1.0  2026-08-23
WHERE THE R MIGHT LIVE — every derived feature at fire time, tested against
dollar outcomes with a PRE-REGISTERED bar; plus the unfired plans, scored.

v1.0  2026-08-23  Built for the R-factor project. This is the "fit our
trades to collected data when a correlation becomes evident" tool — and its
job is mostly to say NOT YET. The bar is registered here, before any data
exists, so nobody (including me) can tune it to produce a pleasing result:

  MEETS THE BAR  (all of): n ≥ 200 rows over ≥ 10 sessions per side ·
                 Mann-Whitney p < 0.05 · |Cliff's delta| ≥ 0.147 ·
                 sign stable across session halves.
  CANDIDATE      (n ≥ 30 per side, |delta| ≥ 0.147): worth watching, moves
                 NOTHING. Thin samples find mechanisms, not conclusions.

Sources joined per trade_id: `fire_snapshot.payload` (the derived vector at
fire — charm, vanna, gex, VRP, expected move, levels, session fraction),
trade columns (adx_at_entry, gap_pct), outcome = pnl_usd. Calls and puts
scanned SEPARATELY (the 34.2% put signature pools away). Relaxed excluded.

UNFIRED PLANS (the free backtests, plan_ledger r69/r70): every EXPIRED /
CANCELLED plan with max/min_price_seen is scored against its own trigger and
strikes — would price have reached the trigger, and where did it go after?
Fired vs unfired outcome distributions measure THE TRIGGER ITSELF.

⚠️ OUTPUT IS LOG-ONLY PROPOSALS. A line that meets the bar prints the exact
number a config change would cite (AUDIT.md §5.1) and stops there. Every
gate ships LOG-ONLY and is judged on outcomes before it may refuse a trade
(VISION.md) — this tool is upstream of even that.

Run:  python3 tests/edge_scan.py [--db trades.db] [--derived derived_store.db]
      python3 tests/edge_scan.py --selftest
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r_ledger import _f, DEFAULT_DB  # noqa: E402

DEFAULT_DERIVED = os.path.join(os.path.expanduser("~"), "options-trader",
                               "data", "derived_store.db")
BAR = {"n": 200, "sessions": 10, "p": 0.05, "delta": 0.147}
CAND_N = 30


def mannwhitney_p(a: list, b: list):
    """Two-sided normal-approximation Mann-Whitney. No scipy on the boxes."""
    n1, n2 = len(a), len(b)
    if n1 < 3 or n2 < 3:
        return None
    allv = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks = {}
    i = 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        r = (i + j + 1) / 2.0
        for k in range(i, j):
            ranks[k] = r
        i = j
    R1 = sum(ranks[k] for k, (_v, g) in enumerate(allv) if g == 0)
    U = R1 - n1 * (n1 + 1) / 2.0
    mu = n1 * n2 / 2.0
    sd = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12.0)
    if sd == 0:
        return None
    z = abs(U - mu) / sd
    # two-sided p from z, erfc
    return math.erfc(z / math.sqrt(2))


def cliffs_delta(a: list, b: list):
    n1, n2 = len(a), len(b)
    if not n1 or not n2:
        return None
    sb = sorted(b)
    import bisect
    gt = lt = 0
    for x in a:
        lt += bisect.bisect_left(sb, x)            # b values < x  -> a greater
        gt += n2 - bisect.bisect_right(sb, x)      # b values > x
    return (lt - gt) / (n1 * n2)


def scan_features(rows: list) -> list:
    """rows: [{feature dict incl. _pnl, _session, _side}] -> findings."""
    out = []
    by_side = defaultdict(list)
    for r in rows:
        by_side[r.get("_side") or "?"].append(r)
    for side, rs in sorted(by_side.items()):
        feats = sorted({k for r in rs for k in r
                        if not k.startswith("_") and _f(r[k]) is not None})
        for k in feats:
            # 🔴 r63 — `feats` is the UNION of keys across rows, so indexing
            # `r[k]` raised KeyError on the first row missing that feature.
            # MEASURED: `edge_scan --db trades.db` died on `KeyError: 'adx'`
            # against the real book while its own selftest passed ALL PASS —
            # the fire snapshots are not homogeneous (r31/MEAS.4 already
            # recorded ADX as sparse). A missing feature must simply not
            # contribute, which is what the `is not None` filter already meant.
            win = [_f(r.get(k)) for r in rs if r["_pnl"] > 0 and _f(r.get(k)) is not None]
            lose = [_f(r.get(k)) for r in rs if r["_pnl"] <= 0 and _f(r.get(k)) is not None]
            if min(len(win), len(lose)) < CAND_N:
                continue
            d = cliffs_delta(win, lose)
            if d is None or abs(d) < BAR["delta"]:
                continue
            p = mannwhitney_p(win, lose)
            sessions = len({r["_session"] for r in rs if _f(r.get(k)) is not None})
            half = len(rs) // 2
            d1 = cliffs_delta([_f(r[k]) for r in rs[:half] if r["_pnl"] > 0 and _f(r[k]) is not None],
                              [_f(r[k]) for r in rs[:half] if r["_pnl"] <= 0 and _f(r[k]) is not None])
            d2 = cliffs_delta([_f(r[k]) for r in rs[half:] if r["_pnl"] > 0 and _f(r[k]) is not None],
                              [_f(r[k]) for r in rs[half:] if r["_pnl"] <= 0 and _f(r[k]) is not None])
            stable = d1 is not None and d2 is not None and (d1 * d2) > 0
            meets = (min(len(win), len(lose)) >= BAR["n"] and sessions >= BAR["sessions"]
                     and p is not None and p < BAR["p"] and abs(d) >= BAR["delta"]
                     and stable)
            med_w = sorted(win)[len(win) // 2]
            med_l = sorted(lose)[len(lose) // 2]
            out.append({"side": side, "feature": k, "n_win": len(win),
                        "n_lose": len(lose), "delta": d, "p": p,
                        "sessions": sessions, "stable": stable, "meets": meets,
                        "med_win": med_w, "med_lose": med_l})
    return out


def load_joined(db, derived):
    tcon = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    tcon.row_factory = sqlite3.Row
    trades = {r["trade_id"]: dict(r) for r in tcon.execute(
        "SELECT * FROM trades WHERE status='closed'")}  # r299 — relaxed kept
    tcon.close()
    snaps = {}
    if os.path.exists(derived):
        dcon = sqlite3.connect(f"file:{derived}?mode=ro", uri=True)
        try:
            for tid, payload in dcon.execute("SELECT trade_id, payload FROM fire_snapshot"):
                try:
                    snaps[tid] = json.loads(payload)
                except Exception:                               # noqa: BLE001
                    pass
        except sqlite3.Error:
            pass
        dcon.close()
    rows = []
    joined = 0
    for tid, t in trades.items():
        pnl = _f(t.get("pnl_usd"))
        if pnl is None:
            continue
        row = {"_pnl": pnl,
               "_session": str(t.get("entry_time") or "")[:10],
               "_side": (t.get("option_side") or "?").lower(),
               "adx_at_entry": t.get("adx_at_entry"),
               "gap_pct": t.get("gap_pct")}
        snap = snaps.get(tid)
        if snap:
            joined += 1
            for k, v in snap.items():
                if _f(v) is not None:
                    row[k] = v
        rows.append(row)
    return rows, len(trades), joined


def score_plans(derived) -> dict:
    """Unfired plans: did price reach the trigger, and by how much?"""
    out = {"total": 0, "reached": 0, "unreached": 0, "unscoreable": 0}
    if not os.path.exists(derived):
        return out
    dcon = sqlite3.connect(f"file:{derived}?mode=ro", uri=True)
    try:
        cur = dcon.execute(
            "SELECT strategy, state, terminal_reason, direction, trigger_price,"
            " max_price_seen, min_price_seen FROM plan_ledger"
            " WHERE state IN ('EXPIRED','CANCELLED')")
    except sqlite3.Error:
        dcon.close()
        return out
    for strat, _st, _why, direction, trig, mx, mn in cur.fetchall():
        out["total"] += 1
        trig, mx, mn = _f(trig), _f(mx), _f(mn)
        if trig is None or (mx is None and mn is None):
            out["unscoreable"] += 1
            continue
        d = (direction or "").lower()
        hit = (mx is not None and mx >= trig) if d in ("call", "up", "long") \
            else (mn is not None and mn <= trig) if d in ("put", "down", "short") \
            else ((mx is not None and mx >= trig) or (mn is not None and mn <= trig))
        out["reached" if hit else "unreached"] += 1
    dcon.close()
    return out


def render(findings: list, plans: dict, n_trades: int, n_joined: int) -> int:
    print("=" * 74)
    print("  EDGE SCAN — features vs dollar outcomes, pre-registered bar")
    print(f"  bar: n≥{BAR['n']}/side over ≥{BAR['sessions']} sessions · "
          f"p<{BAR['p']} · |δ|≥{BAR['delta']} · sign-stable  (candidates: n≥{CAND_N})")
    print("=" * 74)
    print(f"  {n_trades} closed unrelaxed trades · {n_joined} joined to a fire snapshot")
    meets = [f for f in findings if f["meets"]]
    cands = [f for f in findings if not f["meets"]]
    if not findings:
        print("\n  NO FEATURE SEPARATES — and at this book size that is the "
              "expected, honest answer. The scan exists so the day one does, "
              "it is found by a bar set in advance rather than by looking.")
    for label, fs in (("MEETS THE PRE-REGISTERED BAR", meets),
                      ("CANDIDATES (thin — watch, move nothing)", cands)):
        if not fs:
            continue
        print(f"\n  {label}:")
        for f in sorted(fs, key=lambda x: -abs(x["delta"])):
            print(f"    [{f['side']}] {f['feature']:<26} δ={f['delta']:+.3f} "
                  f"p={f['p']:.3f} nW/nL={f['n_win']}/{f['n_lose']} "
                  f"sessions={f['sessions']} med W/L={f['med_win']:.3g}/{f['med_lose']:.3g}"
                  + ("" if f["stable"] else "  ⚠ sign unstable"))
        if label.startswith("MEETS"):
            print("    → proposal form (LOG-ONLY): gate on the median split above, "
                  "cite δ and n verbatim in the config comment, journal refusals "
                  "for one week before it may decline anything.")
    print(f"\n  UNFIRED PLANS (free backtests): {plans['total']} terminal plans — "
          f"{plans['reached']} would have triggered, {plans['unreached']} never "
          f"reached the trigger, {plans['unscoreable']} lack excursion data.")
    if plans["total"] and plans["reached"]:
        print("    → next: when the EOD pass stamps counterfactual outcomes on "
              "reached plans, this section becomes fired-vs-unfired R — the "
              "direct measurement of what the trigger costs.")
    return 0


def selftest() -> int:
    import random
    random.seed(7)
    ok = True
    # planted separation: feature 'charm' high on winners, low on losers
    rows = []
    for i in range(500):
        win = i % 2 == 0
        rows.append({"_pnl": 100.0 if win else -80.0,
                     "_session": f"2026-08-{(i % 12) + 1:02d}",
                     "_side": "call",
                     "charm": random.gauss(1.0 if win else 0.0, 0.4),
                     "noise": random.gauss(0.0, 1.0)})
    f = scan_features(rows)
    hits = {x["feature"]: x for x in f}
    ok &= "charm" in hits and hits["charm"]["meets"]
    ok &= "noise" not in hits                       # deliberate-failure control
    p = mannwhitney_p([1, 2, 3, 4, 5, 6], [10, 11, 12, 13, 14, 15])
    ok &= p is not None and p < 0.01
    d = cliffs_delta([1, 2, 3], [10, 11, 12])
    ok &= d == -1.0
    print("edge_scan selftest:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


def load_joined_s3(a):
    import warehouse_source as ws
    dates = ws.dates_of(a)
    trades, m1 = ws.load_trades(dates)
    snaps_rows, m2 = ws.load_derived("fire_snapshot", dates)
    plans_rows, m3 = ws.load_derived("plan_ledger", dates)
    for m in (m1, m2, m3):
        print("  " + m.banner())
    if m1.error:
        return None, None, None, None
    snaps = {}
    for r in snaps_rows:
        try:
            snaps[r.get("trade_id")] = json.loads(r.get("payload") or "{}")
        except Exception:                                       # noqa: BLE001
            pass
    rows = []
    joined = 0
    closed = [t for t in trades if (t.get("status") or "").lower() == "closed"
]
    for t in closed:
        pnl = _f(t.get("pnl_usd"))
        if pnl is None:
            continue
        row = {"_pnl": pnl, "_session": str(t.get("entry_time") or "")[:10],
               "_side": (t.get("option_side") or "?").lower(),
               "adx_at_entry": t.get("adx_at_entry"), "gap_pct": t.get("gap_pct")}
        snap = snaps.get(t.get("trade_id"))
        if snap:
            joined += 1
            for k, v in snap.items():
                if _f(v) is not None:
                    row[k] = v
        rows.append(row)
    plans = {"total": 0, "reached": 0, "unreached": 0, "unscoreable": 0}
    for r in plans_rows:
        if r.get("state") not in ("EXPIRED", "CANCELLED"):
            continue
        plans["total"] += 1
        trig, mx, mn = _f(r.get("trigger_price")), _f(r.get("max_price_seen")), _f(r.get("min_price_seen"))
        if trig is None or (mx is None and mn is None):
            plans["unscoreable"] += 1
            continue
        d = (r.get("direction") or "").lower()
        hit = (mx is not None and mx >= trig) if d in ("call", "up", "long")             else (mn is not None and mn <= trig) if d in ("put", "down", "short")             else ((mx is not None and mx >= trig) or (mn is not None and mn <= trig))
        plans["reached" if hit else "unreached"] += 1
    return rows, plans, len(closed), joined


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None, help="LOCAL escape hatch")
    ap.add_argument("--derived", default=None, help="LOCAL escape hatch")
    ap.add_argument("--date")
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to", dest="to")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.db:
        derived = a.derived or DEFAULT_DERIVED
        if not os.path.exists(a.db):
            print(f"  SOURCE: local {a.db} — 🔴 PATH DOES NOT EXIST")
            return 1
        print(f"  SOURCE: local sqlite {a.db} + {derived}")
        rows, n_trades, n_joined = load_joined(a.db, derived)
        return render(scan_features(rows), score_plans(derived), n_trades, n_joined)
    rows, plans, n_trades, n_joined = load_joined_s3(a)
    if rows is None:
        return 1
    return render(scan_features(rows), plans, n_trades, n_joined)


if __name__ == "__main__":
    sys.exit(main())
