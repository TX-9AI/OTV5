#!/usr/bin/env python3
"""
tests/check_manifold_board.py  v1.0
THE HEALTH BOARD SHOWS EVERY LIVE STREAM, AND READS FAST ENOUGH TO BE READ.

v1.0  2026-09-18  OTV4TEST r38 — born red at r37 (0423b3a), where `STREAMS`
      tuples are 6-wide with no WHERE, the underlying's quote has no line, and
      `collect()` runs an unfiltered COUNT(*) on a 22.8M-row table.

🔴 TWO DEFECTS, ONE MENU ITEM. The operator opened the board and it printed its
header, then nothing, for long enough that he reported it broken — then
corrected himself: *"it's not broken. It was just slow."*
  · SLOW: `SELECT COUNT(*) FROM quote_series` scans 22.8M rows. MEASURED 56.72s,
    against 0.09s for the same count capped and 0.00s for the indexed MAX(ts).
    A board that looks hung stops being read, and a board that stops being read
    is the same as no board — §17's "an alarm that spams is an alarm that gets
    filtered", one step further along.
  · BLIND: r36 subscribed the underlying's own Quote (FEED.2) and it landed in
    `quote_series` beside 22.8M option quotes, so the ONLY source of resting
    depth on this box was invisible on the health board.
"""
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    import tools.manifold_health as mh

    check("M1 every STREAMS row carries a WHERE field (7-wide)",
          all(len(t) == 7 for t in mh.STREAMS),
          f"widths {sorted({len(t) for t in mh.STREAMS})}")

    labels = [t[3] for t in mh.STREAMS]
    check("M2 the underlying's own quote has a line of its own",
          any("underlying" in l for l in labels), str(labels))

    und = [t for t in mh.STREAMS if "underlying" in t[3]]
    check("M2b ...scoped to the ticker, not the whole 22.8M-row table",
          bool(und) and und[0][6] and "streamer_symbol" in und[0][6],
          und[0][6] if und else "-")
    check("M2c ...and NOT critical — nothing consumes it yet (§31)",
          bool(und) and und[0][4] is False,
          "an unread stream must not paint the rollup red")

    # r125's ruling stands: underlying_series and theo_series stay OFF the board
    tables = {t[0] for t in mh.STREAMS}
    check("M3 r125's removal holds — underlying_series and theo_series stay off",
          "underlying_series" not in tables and "theo_series" not in tables,
          "operator's ruling, 2026-08-25")

    check("M4 counts are CAPPED, and the cap is a real ceiling",
          isinstance(getattr(mh, "ROW_CAP", None), int) and mh.ROW_CAP > 0,
          f"ROW_CAP={getattr(mh, 'ROW_CAP', None)}")

    src = open(os.path.join(ROOT, "tools", "manifold_health.py"), encoding="utf-8").read()
    # ⚠️ THE FIRST CUT OF M4b WAS TOO BROAD and is recorded rather than quietly
    # narrowed: it banned `COUNT(*), MAX(` anywhere in `collect()`, which also
    # caught the candles GROUP BY (23k rows) and the derived loop (882k) — both
    # legitimate, neither the 56-second query. A canary that fires on correct
    # code is the one that gets loosened and then misses the real thing (§20).
    # Scoped to the STREAMS loop, which is the one that reads the 22.8M table.
    # ⚠️ AND IT MUST REPORT AT AN OLDER HEAD, NOT CRASH. The 7-wide loop does
    # not exist before r38, so a bare .index() raises and the run ends with four
    # checks unreported — the same fault check_level_source shipped this morning.
    marker = "for tbl, tscol, budget, label, critical, after_hours, where"
    loop = ""
    if marker in src:
        loop = src[src.index(marker):]
        loop = loop[:loop.index('out["streams"].append')]
    check("M4b the STREAMS loop counts through the cap, never unfiltered",
          "LIMIT {ROW_CAP}" in loop and not re.search(r"COUNT\(\*\),\s*MAX\(", loop),
          "the 56-second query is gone")
    check("M4c the render says when a count was capped, rather than implying exactness",
          '"+"' in src or "'+'" in src or '}+"' in src, "capped counts are marked")

    # ── it actually runs, and fast enough to read ───────────────────────────
    db = os.path.join(ROOT, "data", "feed_store.db")
    if os.path.exists(db):
        t0 = time.time()
        rep = mh.collect(db, os.path.join(ROOT, "data", "derived_store.db"), False)
        dt = time.time() - t0
        check("M5 collect() finishes in under 20s (it took 56.72s on one query at r37)",
              dt < 20.0, f"{dt:.2f}s")
        got = {s["label"] for s in rep.get("streams", [])}
        check("M6 the underlying quote appears in a real collect()",
              any("underlying" in g for g in got), str(sorted(got)))
    else:
        check("M5 skipped — no feed store on this box", True, "not a box")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
