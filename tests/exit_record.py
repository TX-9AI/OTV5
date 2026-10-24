#!/usr/bin/env python3
"""
tests/exit_record.py  v4.1
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Which exit had the better record in v3? Per exit reason, per strategy.

v4.0  2026-08-19  Built at the OTV4 split. ROADMAP Phase 1.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

THE QUESTION.
The runaway-ORB rule specifies "BOS exit or trailing stop - whichever has a
better record under v3." That is answerable rather than arguable, and this
answers it.

⚠️ WHY THE EXITS ARE THE ONE THING NOT UNDER SUSPICION. Every entry-side
measurement this week came back null - direction accuracy 44.9% (95% CI
[41.3%, 48.6%], worse than a coin), entry conditions ambient, opening bias a
coin forward, four independent searches for direction all empty. **The exits
are the opposite**: orb_trail_stop 95% win / 107 trades / +$37,848, theta_bleed
100% / 107, continuation_trail 85% / 149. Operator, 2026-08-19: *"every day
where P&L was green or very green is nearly entirely based on the ORB trade and
the quality of our stops."*

⚠️ AND A WIN RATE IS NOT A RECORD. An exit that fires on 95% winners may simply
be the exit that fires when a trade is already winning - selection, not skill.
Net dollars, median P&L and the LOSS TAIL are reported beside it, because an
exit taking many small wins and a few catastrophic losses shows 90%+ and loses
money. That asymmetry is exactly what a stop is supposed to prevent, so it is
the number that decides.

⚠️ EXITS ARE NOT INDEPENDENT OF EACH OTHER. Each trade takes exactly one, so a
trailing stop only sees trades a structure stop did not take first. Comparing
them head-to-head compares POPULATIONS as much as MECHANISMS - which is why the
per-strategy split matters and why the honest output is a table, not a winner.
"""

import argparse
import collections
import glob
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TRADES = os.path.expanduser("~/day_trader_pro/trades/*/*_trades_*.db")
POLLUTED = {"2026-08-14"}


def _pct(v, p):
    if not v:
        return float("nan")
    s = sorted(v)
    return s[min(len(s) - 1, int(p / 100.0 * len(s)))]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", default=TRADES)
    ap.add_argument("--strategy", default="")
    ap.add_argument("--since", default="2026-07-13")
    a = ap.parse_args(argv[1:])

    rows = []
    for db in sorted(glob.glob(os.path.expanduser(a.trades))):
        if "_archive" in db or db.endswith(".bak"):
            continue
        m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(db))
        if not m or m.group(1) < a.since or m.group(1) in POLLUTED:
            continue
        try:
            con = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
            recs = con.execute(
                "SELECT * FROM trades WHERE status='closed'").fetchall()
        except Exception:                                      # noqa: BLE001
            continue
        for r in recs:
            r = dict(r)
            if a.strategy and str(r.get("strategy") or "") != a.strategy:
                continue
            # ⚠️ NORMALISE BEFORE GROUPING. v3 writes the trade's OWN P&L into
            # - so EVERY DISTINCT PERCENTAGE BECAME ITS OWN EXIT REASON. The
            # first run of this tool showed 415 reasons collapsed under n<5 and
            # **ORBStrategy's entire 107-trade record was invisible**: nothing
            # printed at all. A grouping key that carries a per-trade value is
            # not a key, and the failure looks exactly like "no data".
            reason = str(r.get("exit_reason") or "").strip() or "(none)"
            reason = re.sub(r"\s*pnl=-?[\d.]+%?", "", reason)
            reason = re.sub(r"\s*[\d.]+%", "", reason)
            reason = re.sub(r"_\d+pct", "_Npct", reason)
            reason = re.sub(r"\s+", " ", reason).strip() or "(none)"
            try:
                pnl = float(r.get("pnl_usd") or 0.0)
            except Exception:                                  # noqa: BLE001
                continue
            rows.append((reason, pnl, str(r.get("strategy") or ""),
                         m.group(1)))

    if not rows:
        print("no closed trades matched. ABSENT MEASUREMENT, not a null.")
        return 1

    print("=" * 92)
    print("EXIT RECORD - which exit actually did the work?")
    print(f"  {len(rows):,} closed trades"
          + (f", strategy={a.strategy}" if a.strategy else ""))
    print("=" * 92)

    by = collections.defaultdict(list)
    for reason, pnl, _s, _d in rows:
        by[reason].append(pnl)

    print(f"\n  {'exit reason':30}{'n':>7}{'win%':>7}{'net $':>11}"
          f"{'med $':>9}{'p10 $':>9}{'worst':>10}")
    print("  " + "-" * 84)
    for reason, v in sorted(by.items(), key=lambda kv: -sum(kv[1])):
        if len(v) < 5:
            continue
        wins = sum(1 for x in v if x > 0)
        print(f"  {reason[:29]:30}{len(v):>7}{wins/len(v):>6.0%}"
              f"{sum(v):>11,.0f}{_pct(v,50):>9,.0f}{_pct(v,10):>9,.0f}"
              f"{min(v):>10,.0f}")

    thin = [(r, v) for r, v in by.items() if len(v) < 5]
    if thin:
        print(f"\n  ({len(thin)} exit reason(s) with n<5 omitted - "
              "REPORTED AS ABSENT, not as zero)")

    print("\n  ⚠️ READ `worst` AND `p10` BEFORE `win%`. An exit showing 95% is")
    print("     often the exit that fires when a trade is ALREADY winning -")
    print("     that is selection, not skill. The number that decides a STOP is")
    print("     the loss tail it permits, because preventing that tail is the")
    print("     entire job.")
    print("  ⚠️ AND THESE POPULATIONS ARE NOT INDEPENDENT. Each trade takes")
    print("     exactly ONE exit, so a trailing stop only ever saw trades a")
    print("     structure stop did not take first. This compares POPULATIONS as")
    print("     much as MECHANISMS.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
