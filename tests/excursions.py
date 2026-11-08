#!/usr/bin/env python3
"""
tests/excursions.py  v5.0
v5.0  2026-11-08  OTV5 r79 (RSUITE.1) — PORTED FROM THE FROZEN otv4 TREE. dtp's R SUITE menu (`_r_tool`) ran all
      four R tools from ~/options-trader-v4/tests, so it ran the predecessor's r_ledger, stop_sweep and exit_replay
      (r75's streaming replay and the stop_sweep None fix never reached the menu) and this file had no OTV5 copy. It is ported byte-for-byte below this header and binds to OTV5's
      `r_ledger.position_dollars` / `_f` / `load_s3` (MEAS.6: the side from `is_credit()`, the flag or
      `credit_received > 0`), so it can never carry a second sign rule. Gate: tests/check_excursions_report.py v5.0.
      Every entry below this line is the predecessor's history (cited by its own prefix).
otv4 v1.0  2026-09-09  r327 / RPT.19 — MFE/MAE IN POSITION DOLLARS, PER TRADE AND
      PER BUCKET. Operator's request, 2026-09-09.

WHAT IT IS FOR, AND WHAT IT IS NOT. The R ledger answers *how much of the
available move did we keep* — capture and giveback. This answers the question
underneath it: **how much was available at all.** A capture of 0.41 means
something different when the peak was $1,200 than when it was $60, and the
ledger cannot tell you which.

🔑 IT REUSES `r_ledger.position_dollars` AND MUST CONTINUE TO. That helper
carries the sign rule — for a SHORT position the tracker's *premium* MFE is
the ADVERSE extreme, because a credit position wins when premium FALLS — and
a second implementation of that mapping is exactly the two-rules-one-number
drift this repo keeps finding (the dedup pair, the counter and the offset
ledger). C4 in the gate pins the two tools to the same function.

⚠️ RELATIONSHIP TO `excursion_report.py`. That one is BUNDLE-sourced and needs
`reports/warehouse` populated first; every other R SUITE item reads S3 through
`_r_tool`. This is the S3-native view and does NOT replace it — r189 retired
the excursion MENU ITEMS and kept the script for `report_parity`, and RPT.3
still owns its fate. Two readers, one measurement, and they agree because they
share the conversion.

🔴 UNMEASURED IS NOT ZERO, AND IT IS NEVER FOLDED IN. A row with no excursion
columns is counted and named on its own line. Folding it into "never
favourable" would turn missing instrumentation into a selection finding —
the ledger's own NO TELEMETRY rule (WA §31), and the plausible-silence class
this project is named after.

⚠️ DESCRIPTIVE. Nothing here sizes or gates anything. A level moves into
config only with the number cited and only after edge_scan's pre-registered
bar.

Run:  python3 tests/excursions.py                 # day one onward
      python3 tests/excursions.py --rows           # one line per trade
      python3 tests/excursions.py --all-history --by strategy
      python3 tests/excursions.py --selftest
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r_ledger import position_dollars, _f, load_s3          # noqa: E402

GROUPS = ("strategy", "exit", "symbol")


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2.0


def key_of(row: dict, by: str):
    strat = row.get("strategy") or "?"
    side = (row.get("option_side") or "?").lower()
    if by == "strategy":
        return f"{strat} · {side}"
    if by == "symbol":
        return row.get("symbol") or "?"
    return str(row.get("exit_reason") or "?")[:38]


def measure(rows: list, by: str) -> dict:
    """-> {key: {...}}. Unmeasured rows are counted, never scored."""
    out = {}
    for r in rows:
        k = key_of(r, by)
        b = out.setdefault(k, {"n": 0, "unmeasured": 0, "mfe": [], "mae": [],
                               "never_fav": 0, "pnl": 0.0})
        b["n"] += 1
        b["pnl"] += _f(r.get("pnl_usd")) or 0.0
        mfe, mae = position_dollars(r)
        if mfe is None and mae is None:
            b["unmeasured"] += 1
            continue
        if mfe is not None:
            b["mfe"].append(mfe)
            if mfe <= 0:
                b["never_fav"] += 1
        if mae is not None:
            b["mae"].append(mae)
    return out


def render(buckets: dict, label: str) -> None:
    print("=" * 70)
    print(f"  EXCURSIONS — MFE / MAE in position dollars, by {label}")
    print("=" * 70)
    print(f"  {'bucket':<26} {'n':>3} {'medMFE':>8} {'maxMFE':>8} "
          f"{'medMAE':>8} {'nvrFav':>6} {'unmeas':>6}")
    print("  " + "-" * 66)
    for k in sorted(buckets, key=lambda x: -buckets[x]["n"]):
        b = buckets[k]
        mm = _median(b["mfe"])
        mx = max(b["mfe"]) if b["mfe"] else None
        ma = _median(b["mae"])
        print(f"  {k[:26]:<26} {b['n']:>3} "
              f"{('$%.0f' % mm) if mm is not None else '—':>8} "
              f"{('$%.0f' % mx) if mx is not None else '—':>8} "
              f"{('$%.0f' % ma) if ma is not None else '—':>8} "
              f"{b['never_fav']:>6} {b['unmeasured']:>6}")
    tot_un = sum(b["unmeasured"] for b in buckets.values())
    tot_n = sum(b["n"] for b in buckets.values())
    print()
    if tot_un:
        print(f"  ⚠️ {tot_un} of {tot_n} row(s) carry NO excursion columns. "
              f"They are UNMEASURED,")
        print("     not never-favourable — they are excluded from every "
              "MFE/MAE figure above.")
    else:
        print(f"  every one of {tot_n} row(s) carried excursion telemetry.")
    print("  ⚠️ Descriptive. Nothing here sizes or gates anything (WA §31).")


def render_rows(rows: list) -> None:
    """One line per trade, phone width — the raw values, no aggregation."""
    print()
    print(f"  {'symbol':<7}{'side':<5}{'MFE$':>9}{'MAE$':>9}{'pnl$':>9}")
    print("  " + "-" * 39)
    for r in sorted(rows, key=lambda x: str(x.get("entry_time") or "")):
        mfe, mae = position_dollars(r)
        p = _f(r.get("pnl_usd"))
        print(f"  {str(r.get('symbol') or '?')[:6]:<7}"
              f"{(r.get('option_side') or '?').lower()[:4]:<5}"
              f"{('%.0f' % mfe) if mfe is not None else '—':>9}"
              f"{('%.0f' % mae) if mae is not None else '—':>9}"
              f"{('%.0f' % p) if p is not None else '—':>9}")


def selftest() -> int:
    ok = True
    # A LONG debit: entry 1.00, peak 1.80, trough 0.85, 1 contract.
    lng = dict(entry_premium=1.0, mfe_premium=1.80, mae_premium=0.85,
               contracts=1, is_short_position=0, pnl_usd=40.0,
               strategy="S", option_side="call")
    # A SHORT credit: the premium MFE is the ADVERSE extreme.
    sht = dict(entry_premium=1.0, mfe_premium=1.40, mae_premium=0.60,
               contracts=1, is_short_position=1, pnl_usd=25.0,
               strategy="S", option_side="put")
    m1, a1 = position_dollars(lng)
    m2, a2 = position_dollars(sht)
    ok &= abs(m1 - 80.0) < 1e-6 and abs(a1 - 15.0) < 1e-6
    ok &= abs(m2 - 40.0) < 1e-6 and abs(a2 - 40.0) < 1e-6
    # an unmeasured row is counted apart and never scored as never-favourable
    bare = dict(entry_premium=1.0, contracts=1, is_short_position=0,
                pnl_usd=-10.0, strategy="S", option_side="call")
    b = measure([lng, sht, bare], "strategy")
    ok &= sum(x["unmeasured"] for x in b.values()) == 1
    ok &= sum(x["never_fav"] for x in b.values()) == 0
    print("excursions selftest:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to", dest="to")
    ap.add_argument("--all-history", action="store_true",
                    help="reach back through the v3 engines; the default "
                         "stops at the epoch. `_r_tool` is SHARED and passes "
                         "this, so argparse must accept it (r297).")
    ap.add_argument("--by", default="strategy", choices=sorted(GROUPS))
    ap.add_argument("--rows", action="store_true",
                    help="one line per trade instead of the buckets")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    rows = load_s3(a)
    if rows is None:
        return 1
    if not rows:
        print("  no closed trades in the window.")
        return 0
    if a.rows:
        render_rows(rows)
        return 0
    render(measure(rows, a.by), a.by)
    return 0


if __name__ == "__main__":
    sys.exit(main())
