#!/usr/bin/env python3
"""
tests/orb_bleed_study.py  v4.0
How fast do ORB winners get there? The third stop, measured rather than chosen.

v4.0  2026-08-20  Built at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

THE QUESTION.
Operator's exit spec for ORB, 2026-08-20: structure stop first, trailing stop
armed after 50% TP, hard stop at 20% premium loss, **never exit at a TP target -
let winners run and cut losers fast.** One gap remained, in his words: *"we just
need one more to protect sideways grinders and bleeders."*

**A time stop and a decay stop behave very differently**, and the number should
come from the tape rather than from a preference. So: **of the ORB entries that
eventually worked, how quickly did they show it?** If winners declare themselves
in twenty minutes and a position sitting flat at forty rarely recovers, forty
minutes is the stop - and it is measured.

⚠️ MEASURED ON THE UNDERLYING, NOT THE OPTION, AND THAT IS THE POINT.
v3 exited ORB on `orb_trail_stop`, so any option-side statistic is partly a
story about **when the trail let go** rather than about what the move did. The
underlying's excursion from entry is independent of how the exit was managed -
it answers *"did the MOVE stall"*, which is the question a grinder stop is for.
It also covers more trades, because it needs no recorded MFE.

⚠️ AND `100% TP` IS A REFERENCE POINT, NOT AN ACTION. Operator, explicitly. The
100% extension is used here as a YARDSTICK for how far a working ORB travels -
nothing in v4 exits there, and a study that measured "trades that hit TP" would
be measuring a rule the system does not have.
"""

import argparse
import bisect
import csv
import glob
import math
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DTP = os.path.expanduser("~/day_trader_pro")
OHLC = os.path.join(DTP, "ohlc")
TRADES = os.path.join(DTP, "trades", "*", "*_trades_*.db")
POLLUTED = {"2026-08-14"}


def _pct(v, p):
    if not v:
        return float("nan")
    s = sorted(v)
    return s[min(len(s) - 1, int(p / 100.0 * len(s)))]


def load_tape(root, day, sym):
    for pat in (f"{sym}_ohlc_{day}.csv", f"{sym.upper()}_ohlc_{day}.csv"):
        p = os.path.join(root, day, pat)
        if not os.path.exists(p):
            continue
        rows = []
        with open(p) as fh:
            for r in csv.DictReader(fh):
                try:
                    rows.append((r["timestamp"][11:19], float(r["high"]),
                                 float(r["low"]), float(r["close"])))
                except Exception:                              # noqa: BLE001
                    continue
        return rows
    return []


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ohlc", default=OHLC)
    ap.add_argument("--trades", default=TRADES)
    ap.add_argument("--since", default="2026-07-13")
    a = ap.parse_args(argv[1:])

    trades = []
    for db in sorted(glob.glob(os.path.expanduser(a.trades))):
        if "_archive" in db or db.endswith(".bak"):
            continue
        m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(db))
        if not m or m.group(1) < a.since or m.group(1) in POLLUTED:
            continue
        try:
            con = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT * FROM trades WHERE status='closed'").fetchall()
        except Exception:                                      # noqa: BLE001
            continue
        for r in rows:
            r = dict(r)
            if "ORB" not in str(r.get("strategy") or ""):
                continue
            trades.append((m.group(1), r))

    if not trades:
        print("no ORB trades found. ABSENT MEASUREMENT, not a null.")
        return 1

    # ⚠️ THE JOIN REPORTS ITSELF. v4.0's first run printed "p50 = 0 bars" for a
    # 1.00% excursion - half the winners supposedly moving a full percent on the
    # entry bar, which is not credible. `bisect_left` returns 0 when the entry
    # timestamp does not match the tape's format, so those trades were scanned
    # **from the 09:30 open** and hit every level immediately.
    # **A join that silently drops or mis-places rows produces a confident wrong
    # answer**, which is this project's most repeated failure. Every drop is now
    # counted and named, and the run REFUSES if most rows fail.
    drops = {"no_tape": 0, "no_entry_time": 0, "ts_unmatched": 0,
             "no_underlying_entry": 0, "too_late_in_session": 0}
    obs = []
    for day, t in trades:
        sym = str(t.get("symbol") or "").upper()
        tape = load_tape(os.path.expanduser(a.ohlc), day, sym)
        if not tape:
            drops["no_tape"] += 1
            continue
        stamps = [x[0] for x in tape]
        _raw_ts = str(t.get("entry_time") or "")
        if not _raw_ts:
            drops["no_entry_time"] += 1
            continue
        # ⚠️ ACCEPT MORE THAN ONE SHAPE, AND SAY WHEN NONE MATCHES. A fixed
        # [11:19] slice assumes `YYYY-MM-DDTHH:MM:SS`; anything else yields
        # garbage that bisect quietly turns into index 0 - the session open.
        ts = ""
        if "T" in _raw_ts and len(_raw_ts) >= 19:
            ts = _raw_ts[11:19]
        elif " " in _raw_ts and len(_raw_ts) >= 19:
            ts = _raw_ts[11:19]
        elif len(_raw_ts) == 8 and _raw_ts[2] == ":":
            ts = _raw_ts
        if not ts or ts[2] != ":" or not ts[:2].isdigit():
            drops["ts_unmatched"] += 1
            continue
        i = bisect.bisect_left(stamps, ts)
        if i == 0 and ts > stamps[0]:
            # the timestamp is after the first bar but landed at index 0 -
            # the formats disagree. Refuse rather than scan from the open.
            drops["ts_unmatched"] += 1
            continue
        if i >= len(tape) - 10:
            drops["too_late_in_session"] += 1
            continue
        entry = t.get("underlying_entry")
        try:
            entry = float(entry or 0.0)
        except Exception:                                      # noqa: BLE001
            continue
        if entry <= 0:
            drops["no_underlying_entry"] += 1
            continue
        direction = str(t.get("direction") or "").lower()
        long_side = direction.startswith("l") or \
            str(t.get("option_side") or "").lower().startswith("c")
        try:
            pnl = float(t.get("pnl_usd") or 0.0)
        except Exception:                                      # noqa: BLE001
            pnl = 0.0

        # time to each favourable-excursion milestone, in bars
        marks = {}
        best = 0.0
        for k in range(i, min(i + 240, len(tape))):
            h, l = tape[k][1], tape[k][2]
            fav = (h - entry) if long_side else (entry - l)
            pct = fav / entry * 100.0
            best = max(best, pct)
            for lvl in (0.10, 0.25, 0.50, 0.75, 1.00):
                if lvl not in marks and pct >= lvl:
                    marks[lvl] = k - i
        obs.append({"won": pnl > 0, "pnl": pnl, "marks": marks,
                    "best": best, "sym": sym, "day": day})

    print(f"  {len(trades)} ORB trades found, {len(obs)} joined to tape")
    if any(drops.values()):
        print("  DROPPED: " + ", ".join(f"{k}={v}" for k, v in drops.items() if v))
    if not obs:
        print("\n  no ORB trades joined to tape. **ABSENT MEASUREMENT, NOT A")
        print("  NULL** - the drop counts above name which link failed.")
        return 1
    if len(obs) < 0.5 * len(trades):
        print(f"\n  ⚠️ REFUSING: only {len(obs)}/{len(trades)} rows joined.")
        print("  A study on a minority of its own population describes the")
        print("  minority and says nothing about which minority. Fix the join")
        print("  named above before reading any number below it.")
        return 1

    win = [o for o in obs if o["won"]]
    los = [o for o in obs if not o["won"]]
    print("=" * 80)
    print("ORB BLEED STUDY - how fast do winners get there?")
    print(f"  {len(obs)} ORB trades joined to tape "
          f"({len(win)} winners, {len(los)} losers)")
    print("  favourable excursion of the UNDERLYING from entry, in bars")
    print("=" * 80)

    print("\n  1. TIME TO EACH EXCURSION LEVEL - WINNERS")
    print(f"    {'move':10}{'reached':>10}{'p50 bars':>11}{'p75':>7}{'p90':>7}")
    print("    " + "-" * 45)
    for lvl in (0.10, 0.25, 0.50, 0.75, 1.00):
        hit = [o["marks"][lvl] for o in win if lvl in o["marks"]]
        if not hit:
            continue
        print(f"    {lvl:>5.2f}%{'':4}{len(hit)/len(win):>9.0%}"
              f"{_pct(hit,50):>11.0f}{_pct(hit,75):>7.0f}{_pct(hit,90):>7.0f}")

    print("\n  2. THE SAME FOR LOSERS - the separation is the stop")
    print(f"    {'move':10}{'reached':>10}{'p50 bars':>11}")
    print("    " + "-" * 31)
    for lvl in (0.10, 0.25, 0.50):
        hit = [o["marks"][lvl] for o in los if lvl in o["marks"]]
        if not hit:
            continue
        print(f"    {lvl:>5.2f}%{'':4}{len(hit)/max(len(los),1):>9.0%}"
              f"{_pct(hit,50):>11.0f}")

    print("\n  3. THE GRINDER TEST - flat at N bars, did it ever work?")
    print("     ⚠️ THE NUMBER THE THIRD STOP IS MADE OF. Of trades showing less")
    print("        than 0.10% favourable excursion by bar N, what fraction went")
    print("        on to win?")
    print(f"    {'still flat at':16}{'n':>7}{'went on to win':>16}")
    print("    " + "-" * 40)
    for n_bars in (15, 20, 30, 40, 60):
        flat = [o for o in obs
                if o["marks"].get(0.10, 999) > n_bars]
        if len(flat) < 5:
            continue
        w = sum(1 for o in flat if o["won"]) / len(flat)
        print(f"    {f'{n_bars} bars':16}{len(flat):>7}{w:>15.0%}")

    print("\n  ⚠️ READ TABLE 3 AGAINST THE BASE RATE. If ORB wins 60% overall and")
    print("     a trade flat at 30 bars still wins 55%, flatness is not")
    print("     informative and a time stop would be cutting winners.")
    base = len(win) / len(obs)
    print(f"     BASE RATE: {base:.0%} of these ORB trades won.")
    print("  ⚠️ AND THIS IS THE UNDERLYING, NOT THE OPTION. It says whether the")
    print("     MOVE stalled, not whether the trail let go - which is the")
    print("     question a grinder stop is actually for. Theta is a separate")
    print("     cost and is not measured here.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
