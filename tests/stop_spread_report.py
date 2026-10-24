#!/usr/bin/env python3
"""
tests/stop_spread_report.py  v1.0

STOP VS SPREAD — how often a credit or fly structure was refused because its stop
could not survive its own bid-ask, how close the rest came, and whether the rule
was the one that actually declined the tick. For the Saturday review.

v1.0  2026-09-24  OTV4TEST r129. Operator: "Do we have a stop vs spread report? If
      not, we can build that & review it on Saturdays with our other reviews", and
      "Both" — butterflies and verticals. READ-ONLY on the derived store.

THE RULE (strategy/criteria.py `stop_survivable`): ratio = stop distance / the
short leg's bid-ask spread, and the structure must clear STOP_VS_SPREAD_MIN
(2.0, env OT_STOP_VS_SPREAD_MIN). Read from criteria, never restated here.

WHAT THE STORE HOLDS, per strategy (plan_check rows named "stop_vs_spread"):
  · GEXPinButterfly / ATPButterfly — the BEST ratio among the wings that passed
    R, on every tick, verdict n/a. A refusal is DERIVED: best ratio below the
    minimum means no R-passing wing could hold its stop. ⚠️ NO RATIO IS "NOT
    REACHED", NOT A FAILURE: the fly tests R BEFORE survivability
    (gex_pin_butterfly.py:831-834), so an empty ratio means no wing passed R and
    this rule never ran. Counting those against it would blame R's refusals on
    the spread (229 GEXPin ticks 09-14..09-23 — caught before it shipped).
  · SweepCreditSpread / TrendCreditSpread — since r129 the ratio with PASS on the
    chosen wing, and FAIL on a stop_vs_spread refusal (TCS carries the best refused
    ratio; the sweep's refusal row has no ratio because search_wing does not
    return one). Before r129 TCS recorded dollars under this name: those rows are
    counted but their "ratio" is not a ratio, and the report says so.
BINDING = the tick's own plan_tick verdict was DECLINE at gate "stop_vs_spread" or
"wing_search" (the butterflies' name for the same refusal) while the ratio failed.
A failing ratio on a tick declined for some OTHER reason did not cost that tick.

NOT MEASURED YET (stated, not implied): what a refused structure would have done.
That needs the refused wing's strikes on the row and the chain path after it.

Run:  venv/bin/python tests/stop_spread_report.py [--derived PATH]
        [--date YYYY-MM-DD | --from YYYY-MM-DD --to YYYY-MM-DD | --all-history]
      no date flag = the last 7 days (the Saturday week).
"""
from __future__ import annotations

import argparse
import collections
import datetime as D
import os
import sqlite3
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import glob as _glob                                             # r106 venv bootstrap
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
from zoneinfo import ZoneInfo                                    # noqa: E402

ET = ZoneInfo("America/New_York")
BINDING_GATES = ("stop_vs_spread", "wing_search")
TCS_RATIO_SINCE = D.datetime(2026, 9, 24, tzinfo=ET).timestamp()   # r129 changed its unit


def _min_ratio() -> float:
    try:
        from strategy.criteria import STOP_VS_SPREAD_MIN
        return float(STOP_VS_SPREAD_MIN)
    except Exception as exc:                                    # noqa: BLE001
        sys.exit(f"cannot read STOP_VS_SPREAD_MIN from strategy/criteria.py: {exc}")


def _default_db() -> str:
    return os.environ.get("OT_DERIVED_DB") or os.path.join(ROOT, "data", "derived_store.db")


def _window(a) -> tuple:
    def day0(s):
        return D.datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=ET)
    if a.all_history:
        return None, None, "all history"
    if a.date:
        s = day0(a.date)
        return s.timestamp(), (s + D.timedelta(days=1)).timestamp(), a.date
    if a.from_:
        s = day0(a.from_)
        e = day0(a.to) + D.timedelta(days=1) if a.to else s + D.timedelta(days=1)
        return s.timestamp(), e.timestamp(), f"{a.from_} .. {a.to or a.from_}"
    e = D.datetime.now(ET).replace(hour=0, minute=0, second=0, microsecond=0) + D.timedelta(days=1)
    s = e - D.timedelta(days=7)
    return s.timestamp(), e.timestamp(), f"last 7 days ({s:%m-%d} .. {(e - D.timedelta(days=1)):%m-%d})"


def _pct(v, q):
    v = sorted(v)
    if not v:
        return None
    return v[min(len(v) - 1, int(q * (len(v) - 1) + 0.5))]


def _f(x, fmt=".2f"):
    return "-" if x is None else format(x, fmt)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Stop-vs-spread review (read-only)")
    ap.add_argument("--derived", default=_default_db())
    ap.add_argument("--db", help=argparse.SUPPRESS)          # the R-suite menu passes trades.db; unused here
    ap.add_argument("--date")
    ap.add_argument("--from", dest="from_")
    ap.add_argument("--to")
    ap.add_argument("--all-history", action="store_true")
    a = ap.parse_args(argv)
    mn = _min_ratio()
    if not os.path.exists(a.derived):
        print(f"  🔴 no derived store at {a.derived}")
        return 1
    t0, t1, label = _window(a)
    con = sqlite3.connect(f"file:{a.derived}?mode=ro", uri=True)
    where, args = "k.check_name = 'stop_vs_spread'", []
    if t0 is not None:
        where += " AND k.ts_epoch >= ? AND k.ts_epoch < ?"
        args += [t0, t1]
    rows = con.execute(
        "SELECT k.strategy, k.ts_epoch, k.value, k.verdict, t.verdict, t.reason "
        "FROM plan_check k LEFT JOIN plan_tick t ON t.strategy = k.strategy "
        "AND t.ts_epoch = k.ts_epoch AND t.tick_id = k.tick_id "
        f"WHERE {where} ORDER BY k.ts_epoch", args).fetchall()
    rng = con.execute("SELECT MIN(ts_epoch), MAX(ts_epoch) FROM plan_check").fetchone()
    con.close()

    print("=" * 68)
    print(" STOP VS SPREAD — Saturday review (read-only)")
    print("=" * 68)
    print(f"  rule    stop distance / short bid-ask must be >= {mn:g}  (criteria.STOP_VS_SPREAD_MIN)")
    print(f"  window  {label}")
    if rng and rng[0]:
        print(f"  store   plan_check holds {D.datetime.fromtimestamp(rng[0], ET):%m-%d} .. "
              f"{D.datetime.fromtimestamp(rng[1], ET):%m-%d %H:%M} ET  ({a.derived})")
    print(f"  rows    {len(rows)} stop_vs_spread checks in the window")
    if not rows:
        print("\n  Nothing recorded in this window. Not the same as 'never refused':")
        print("  a strategy that never reached wing selection writes no row.")
        return 0

    by = collections.defaultdict(list)
    for s, ts, v, vk, tv, reason in rows:
        dollars = (s == "TrendCreditSpread" and ts < TCS_RATIO_SINCE)
        ratio = None if (v is None or dollars) else float(v)
        if vk in ("PASS", "FAIL"):
            ok = vk == "PASS"                             # the plan said so (verticals)
        elif ratio is None:
            ok = None                                     # fly: no wing passed R - rule not reached
        else:
            ok = ratio >= mn
        gate = (reason or "").split(":", 1)[0].strip()
        binding = (ok is False) and tv == "DECLINE" and gate in BINDING_GATES
        by[s].append((ts, ratio, ok, binding, dollars))

    for s in sorted(by, key=lambda k: -len(by[k])):
        v = by[s]
        rs = [r for _, r, _, _, _ in v if r is not None]
        fail = [x for x in v if x[2] is False]
        reached = [x for x in v if x[2] is not None]
        notreach = len(v) - len(reached)
        bind = [x for x in v if x[3]]
        unmeas = sum(1 for _, r, ok, _, d in v if r is None and ok is False and not d)
        near = sum(1 for r in rs if mn * 0.75 <= r < mn)
        dollars = sum(1 for x in v if x[4])
        days = sorted({D.datetime.fromtimestamp(x[0], ET).date() for x in v})
        print(f"\n  {s}   ({len(days)} session{'s' if len(days) != 1 else ''})")
        print(f"    ticks recorded     {len(v):>6}")
        print(f"    rule not reached   {notreach:>6}  (no wing passed R first — not this rule's refusal)")
        print(f"    rule applied       {len(reached):>6}")
        if reached:
            print(f"    failed the rule    {len(fail):>6}  ({100 * len(fail) / len(reached):.0f}% of applied)"
                  f"   ratio not recorded on {unmeas}")
        print(f"    BINDING refusals   {len(bind):>6}  (the tick was declined BY this rule)")
        print(f"    near misses        {near:>6}  (ratio {mn * 0.75:g} .. {mn:g})")
        if rs:
            print(f"    ratio  p10 {_f(_pct(rs, .10))}  p50 {_f(_pct(rs, .50))}  p90 {_f(_pct(rs, .90))}"
                  f"   min {_f(min(rs))}  max {_f(max(rs))}")
        if dollars:
            print(f"    ⚠️ {dollars} pre-r129 TCS rows recorded DOLLARS under this name — excluded from ratios")
        print(f"    {'day':<6} {'ticks':>6} {'failed':>7} {'binding':>8} {'p50':>6}")
        for d in days:
            dv = [x for x in v if D.datetime.fromtimestamp(x[0], ET).date() == d]
            drs = [x[1] for x in dv if x[1] is not None]
            print(f"    {d:%m-%d} {len(dv):>7} {sum(x[2] is False for x in dv):>7} "
                  f"{sum(x[3] for x in dv):>8} {_f(_pct(drs, .5)):>6}")
    print("\n  NOT MEASURED: what a refused structure would have done afterwards.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
