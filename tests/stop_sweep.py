#!/usr/bin/env python3
"""
tests/stop_sweep.py  v1.3
v1.3  2026-09-07  r299 - relaxed rows kept (operator ruling); the dead
`include_relaxed` assignment goes with the filter it fed.
v1.2  2026-09-07  r297 - --all-history added: `_r_tool` is shared and now passes it. The default
window also moves from TODAY to DAY ONE ONWARD via warehouse_source.
v1.1  2026-08-23  S3 default source (control-side, boxes untouched); --db is
the explicit local escape hatch. SOURCE line always printed.
v1.0  2026-08-23
WHAT R WOULD THE BOOK HAVE HAD under a different stop / take-profit — swept
against the recorded MFE/MAE excursions. The concrete R lever.

v1.0  2026-08-23  Built for the R-factor project. The r38 columns
(mfe_premium, mae_premium, mfe_bars, mae_bars — units fixed by audit F7)
let every closed trade answer: *would a stop at S have fired, and would it
have fired BEFORE or AFTER the favourable peak?*

MECHANICS, stated so the approximation is honest:
  · Levels are in PERCENT OF ENTRY PREMIUM (debit) / PERCENT OF CREDIT
    (short), matching how the engine's stops are specified.
  · A stop at S fires iff adverse excursion ≥ S.
  · ⚠️ ORDERING IS THE HARD PART AND IT IS BOUNDED, NOT GUESSED. If the stop
    fires and mae_bars < mfe_bars, the stop cut the trade BEFORE its peak —
    a winner becomes a −S loser. If mae_bars > mfe_bars the peak came first
    and the recorded exit stands (the stop only re-prices trades that were
    already losers). When the bars tie or are missing, the trade is counted
    BOTH ways and the report prints a PESSIMISTIC and an OPTIMISTIC line —
    a range that contains the truth beats a point that might not (§18: a
    laundered green is worse than a red).
  · The recorded exits already include a stop; sweeping TIGHTER than the
    live stop is exact, sweeping LOOSER is not (the path after the real stop
    was never traded) — looser-than-live cells print with a ⚠ and use the
    recorded loss as the floor.

⚠️ THIS TOOL PROPOSES NOTHING. It prints the R surface; a level moves into
config only with the number cited (AUDIT.md §5.1) and only after edge_scan's
sample gates are met. Calls/puts separate; relaxed excluded.

Run:  python3 tests/stop_sweep.py [--db trades.db] [--strategy ORB]
      python3 tests/stop_sweep.py --selftest
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r_ledger import position_dollars, _f, DEFAULT_DB, load_s3  # noqa: E402

STOP_GRID = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
TP_GRID = [None, 0.25, 0.50, 0.75, 1.00, 1.50]
MIN_N = 20


def excursion_pcts(r: dict):
    """(fav_pct, adv_pct) of entry premium, sign-aware. None when unmeasured."""
    entry = _f(r.get("entry_premium"))
    if not entry:
        return None, None
    mfe, mae = position_dollars(r)
    lot = 100.0 * (_f(r.get("contracts")) or 1)
    fav = (mfe / lot) / entry if mfe is not None else None
    adv = (mae / lot) / entry if mae is not None else None
    return fav, adv


def replay_row(r: dict, stop: float, tp, pessimistic: bool):
    """Hypothetical pnl_usd for one trade under (stop, tp). None = unusable."""
    entry = _f(r.get("entry_premium"))
    pnl = _f(r.get("pnl_usd"))
    if entry is None or pnl is None:
        return None
    fav, adv = excursion_pcts(r)
    if fav is None or adv is None:
        return None
    lot = 100.0 * (_f(r.get("contracts")) or 1)
    risk_usd = stop * entry * lot
    tp_usd = (tp * entry * lot) if tp else None
    mfe_b = _f(r.get("mfe_bars"))
    mae_b = _f(r.get("mae_bars"))
    stop_hit = adv >= stop
    tp_hit = tp is not None and fav >= tp
    if stop_hit and tp_hit:
        # both reachable — ordering decides; unknown ordering goes to the bound
        if mae_b is not None and mfe_b is not None and mae_b != mfe_b:
            first_is_stop = mae_b < mfe_b
        else:
            first_is_stop = pessimistic
        return -risk_usd if first_is_stop else tp_usd
    if stop_hit:
        # was this trade a winner whose stop would have cut it pre-peak?
        if pnl > 0:
            if mae_b is not None and mfe_b is not None and mae_b != mfe_b:
                return -risk_usd if mae_b < mfe_b else pnl if tp is None else min(pnl, tp_usd)
            return -risk_usd if pessimistic else (pnl if tp is None else min(pnl, tp_usd))
        # loser: stop caps the loss (tighter) or floors at the recorded loss (looser)
        return -min(risk_usd, abs(pnl)) if abs(pnl) > risk_usd else max(pnl, -risk_usd)
    if tp_hit:
        return tp_usd
    return pnl if tp is None else min(pnl, tp_usd) if pnl > 0 else pnl


def sweep(rows: list) -> list:
    out = []
    for stop in STOP_GRID:
        for tp in TP_GRID:
            for tag, pess in (("pess", True), ("opt", False)):
                pnls = [p for p in (replay_row(r, stop, tp, pess) for r in rows)
                        if p is not None]
                if len(pnls) < MIN_N:
                    continue
                wins = [p for p in pnls if p > 0]
                losses = [p for p in pnls if p <= 0]
                aw = sum(wins) / len(wins) if wins else 0.0
                al = sum(losses) / len(losses) if losses else 0.0
                out.append({"stop": stop, "tp": tp, "bound": tag, "n": len(pnls),
                            "net": sum(pnls),
                            "R": (aw / abs(al)) if (wins and losses) else None,
                            "wr": 100.0 * len(wins) / len(pnls)})
    return out


def render(rows: list, label: str) -> None:
    cells = sweep(rows)
    if not cells:
        print(f"  {label}: fewer than {MIN_N} usable rows — no surface (thin "
              f"samples find mechanisms, not conclusions)")
        return
    base_wins = [r["pnl_usd"] for r in rows if _f(r.get("pnl_usd")) and r["pnl_usd"] > 0]
    base_all = [r["pnl_usd"] for r in rows if _f(r.get("pnl_usd")) is not None]
    print(f"\n  {label}  — recorded book: n={len(base_all)} net=${sum(base_all):,.0f}")
    print(f"  {'stop':>5} {'tp':>5} | {'net(pess)':>10} {'net(opt)':>10} "
          f"| {'R(pess)':>8} {'R(opt)':>8} {'WR%':>5}")
    print("  " + "-" * 62)
    merged = {}
    for c in cells:
        merged.setdefault((c["stop"], c["tp"]), {})[c["bound"]] = c
    for (stop, tp), b in sorted(merged.items()):
        p, o = b.get("pess"), b.get("opt")
        if not p or not o:
            continue
        tp_s = f"{tp:.2f}" if tp else "none"
        rp = f"{p['R']:.2f}" if p["R"] else "  — "
        ro = f"{o['R']:.2f}" if o["R"] else "  — "
        print(f"  {stop:>5.2f} {tp_s:>5} | {p['net']:>10,.0f} {o['net']:>10,.0f} "
              f"| {rp:>8} {ro:>8} {p['wr']:>4.0f}%")
    print("  ⚠️ a cell is interesting only when its PESSIMISTIC net beats the")
    print("     recorded book — the optimistic column is a ceiling, not a claim.")


def selftest() -> int:
    # Trade A: winner +$300, peak +400% at bar 20, adverse 12% at bar 3.
    #   stop 0.10 pess -> stopped (-$10·k... 0.10·1.00·100=-$10? entry=1) => -10
    #   stop 0.15 -> survives, +300.
    A = dict(pnl_usd=300.0, entry_premium=1.0, mfe_premium=5.0, mae_premium=0.88,
             mfe_bars=20, mae_bars=3, contracts=1, is_short_position=0)
    B = dict(pnl_usd=-80.0, entry_premium=1.0, mfe_premium=1.05, mae_premium=0.10,
             mfe_bars=2, mae_bars=15, contracts=1, is_short_position=0)
    ok = True
    ok &= replay_row(A, 0.10, None, pessimistic=True) == -10.0      # cut pre-peak
    ok &= replay_row(A, 0.15, None, pessimistic=True) == 300.0      # survives
    ok &= replay_row(B, 0.25, None, pessimistic=True) == -25.0      # loss capped
    ok &= replay_row(A, 0.15, 1.00, pessimistic=True) == 100.0      # TP first
    # deliberate failure: ordering must matter — same trade, bars flipped
    A2 = dict(A, mae_bars=30)
    ok &= replay_row(A2, 0.10, None, pessimistic=True) == 300.0
    print("stop_sweep selftest:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None, help="LOCAL sqlite escape hatch; "
                    "default source is the S3 warehouse")
    ap.add_argument("--date")
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to", dest="to")
    ap.add_argument("--strategy", default=None)
    ap.add_argument("--all-history", action="store_true",
                    help="reach back through the v3 engines; the default "
                         "stops at the 2026-08-25 epoch (r187). Added at r297 "
                         "because `_r_tool` is SHARED by three items and now "
                         "passes this flag - without it argparse would refuse "
                         "and two working menu items would break.")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.db:
        if not os.path.exists(a.db):
            print(f"  SOURCE: local {a.db} — 🔴 PATH DOES NOT EXIST")
            return 1
        print(f"  SOURCE: local sqlite {a.db}")
        con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute(
            "SELECT * FROM trades WHERE status='closed'")]  # r299 — relaxed kept
        con.close()
    else:
        # r299 - relaxed rows are kept; the attribute is gone with the filter.
        rows = load_s3(a)
        if rows is None:
            return 1
    groups = defaultdict(list)
    for r in rows:
        if a.strategy and (r.get("strategy") or "") != a.strategy:
            continue
        groups[(r.get("strategy") or "?", (r.get("option_side") or "?").lower())].append(r)
    print("=" * 66)
    print("  STOP / TP SWEEP over recorded excursions — bounds, not points")
    print("=" * 66)
    for (strat, side), rs in sorted(groups.items()):
        render(rs, f"{strat} · {side}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
