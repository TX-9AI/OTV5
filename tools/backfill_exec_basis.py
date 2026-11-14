#!/usr/bin/env python3
"""
tools/backfill_exec_basis.py  v5.1
v5.1  2026-11-14  OTV5 r111 (AM.1) — new. THE EXECUTABLE-PRICE BASIS FOR THE TRADES BOOKED BEFORE r111. READ-ONLY: it
      reads the warehouse trade rows (tests/warehouse_source.load_trades, OTV4TEST rows out by mainline()) and writes
      ONE CSV off the warehouse (default ~/reviews/exec_basis_backfill.csv); it never writes S3 or a trades store.
      The prices are the ones the bot already recorded on each row at the tick it traded: entry_bid / entry_ask
      (set_entry_contract, the entry tick's contract quote) and exit_bid / exit_ask (set_exit_contract, the closing
      tick's quote) - the same inputs database/trade_logger v5.6 now turns into entry_exec_premium, exit_exec_premium,
      pnl_exec_usd and would_fill_live at the time of the trade. A row is NOT PRICED, with the reason, when it is open,
      not a single leg, or missing a side of either quote; nothing is filled in from elsewhere. The operator,
      2026-11-14: "Let's fix the top 10 today" (amnesty bucket AM.1).

Run:  /home/ubuntu/day_trader_pro/venv/bin/python tools/backfill_exec_basis.py 2026-10-26 2026-11-13 [--out PATH]
"""
import argparse
import csv
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, ROOT)

COLS = ("trade_id", "day", "symbol", "strategy", "short", "contracts", "entry_premium", "exit_premium", "pnl_usd",
        "entry_bid", "entry_ask", "exit_bid", "exit_ask", "entry_exec_premium", "exit_exec_premium", "pnl_exec_usd",
        "would_fill_live", "priced", "why_not")


def _f(v):
    try:
        x = float(v)
        return x if x > 0 and x == x and x < 1e6 else None
    except (TypeError, ValueError):
        return None


def price_row(r: dict) -> dict:
    """One warehouse trade row -> the executable basis, exactly as trade_logger v5.6 computes it live."""
    short = bool(int(r.get("is_short_position") or 0))
    out = {k: r.get(k) for k in ("trade_id", "symbol", "strategy", "contracts", "entry_premium", "exit_premium",
                                 "pnl_usd", "entry_bid", "entry_ask", "exit_bid", "exit_ask")}
    out["day"] = str(r.get("entry_time") or "")[:10]
    out["short"] = int(short)
    out.update(entry_exec_premium=None, exit_exec_premium=None, pnl_exec_usd=None, would_fill_live=None,
               priced=0, why_not="")
    if str(r.get("status") or "") != "closed":
        out["why_not"] = "not closed"
        return out
    if any(r.get(k) for k in ("short_symbol", "long_symbol", "lower_symbol", "center_symbol", "upper_symbol")) \
            or int(r.get("is_butterfly") or 0):
        out["why_not"] = "not a single leg"
        return out
    e = _f(r.get("entry_bid") if short else r.get("entry_ask"))
    x = _f(r.get("exit_ask") if short else r.get("exit_bid"))
    m = _f(r.get("entry_premium"))
    if e is not None:
        out["entry_exec_premium"] = round(e, 4)
        if m is not None:
            out["would_fill_live"] = int((e >= m - 1e-9) if short else (e <= m + 1e-9))
    if x is not None:
        out["exit_exec_premium"] = round(x, 4)
    n = r.get("contracts")
    if e is None or x is None or not n:
        out["why_not"] = ("no entry quote" if e is None else "") + (" + " if e is None and x is None else "") + \
                         ("no exit quote" if x is None else "") or "no contracts"
        return out
    per = (e - x) if short else (x - e)
    out["pnl_exec_usd"] = round(per * float(n) * 100.0, 2)
    out["priced"] = 1
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("start")
    ap.add_argument("end")
    ap.add_argument("--out", default=os.path.expanduser("~/reviews/exec_basis_backfill.csv"))
    a = ap.parse_args(argv)
    from warehouse_source import load_trades, mainline, _span
    days = _span(a.start, a.end)
    rows, meta = load_trades(days)
    rows, dropped = mainline(rows, day_of=lambda r: str(r.get("entry_time") or "")[:10])
    if dropped:
        print(f"OTV4TEST filter dropped {sum(dropped.values())} row(s): {dropped}")
    priced = [price_row(r) for r in rows]
    priced.sort(key=lambda o: (o["day"], str(o.get("symbol")), str(o.get("trade_id"))))
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for o in priced:
            w.writerow(o)
    closed = [o for o in priced if o["why_not"] != "not closed"]
    ok = [o for o in closed if o["priced"]]
    by = defaultdict(lambda: [0, 0.0, 0.0])
    for o in ok:
        b = by[o["strategy"]]
        b[0] += 1
        b[1] += float(o["pnl_usd"] or 0.0)
        b[2] += float(o["pnl_exec_usd"] or 0.0)
    why = defaultdict(int)
    for o in closed:
        if not o["priced"]:
            why[o["why_not"]] += 1
    print(f"exec basis {a.start}..{a.end}: {len(closed)} closed rows, {len(ok)} priced, {len(closed) - len(ok)} not "
          f"({dict(why)}); wrote {a.out}")
    for k in sorted(by):
        n, mk, ex = by[k]
        print(f"  {k:22s} n={n:4d}  mark {mk:+11.2f}  exec {ex:+11.2f}  spread cost {ex - mk:+10.2f}")
    if ok:
        mk = sum(float(o["pnl_usd"] or 0) for o in ok)
        ex = sum(float(o["pnl_exec_usd"] or 0) for o in ok)
        wf = [o for o in ok if o["would_fill_live"] is not None]
        print(f"  ALL priced             n={len(ok):4d}  mark {mk:+11.2f}  exec {ex:+11.2f}  spread cost {ex - mk:+10.2f}"
              f"  would_fill_live={sum(int(o['would_fill_live']) for o in wf)}/{len(wf)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
