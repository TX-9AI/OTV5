#!/usr/bin/env python3
"""
tests/brief_bias_join.py  v5.0
v5.0  2026-11-08  OTV5 r82 (OTV4DEP.1) — PORTED FROM THE FROZEN otv4 TREE. dtp's tools/brief_sigint.py put
      ~/options-trader-v4/tests on sys.path to import `composite_call` / `SPX_PROXY` from this file, the ONE weighting
      rule its SPX row and this study share (a local copy is how the two drift, so the board refuses one). The file had
      no OTV5 copy, so the board read the predecessor tree. It is ported byte-for-byte below this header; brief_sigint
      v1.2 (dtp r532) now reads it from ${DTP_OTV5_DIR:-~/OTV5}/tests. Every entry below this line is the predecessor's
      history (cited by its own prefix).
otv4 v1.5  2026-09-10  r339 - `leg_weight` and `composite_call` extracted so the
DAILY BOARD and this study share ONE weighting rule. `tools/brief_sigint.py`
now prints an SPX call every morning and this file scores it against the tape;
two implementations would drift and the board would end up advertising a
signal the study never measured. Same reason `price_bias` lives in exactly one
place. No behaviour change to table F - `spx_composite` calls the extracted
helper and its numbers are unchanged.
otv4 v1.4  2026-09-10  r338 - TABLE F: an SPX call built from the constituents the
brief DOES score. Operator: *"we cannot have our largest net symbol be silent
on that brief."* SPX is in market_brief's `_NON_EQUITY`, never polled, and is
the largest net symbol in the book. Thirteen panel names are members and are
scored daily. Conviction-weighted sum, NOT a vote count - a count would let
five weak calls outrank two strong ones, and r336 established a call below the
floor is worse than no call. Printed twice, ungated and floor-gated, so the
floor's effect on the composite is visible rather than assumed. EQUAL WEIGHT
is a limitation and is labelled as one: index weights are nowhere in these
repos, so this tests DIRECTION only and buys real weights only if direction
works. QQQ and SPX are excluded from the members - an index and an ETF are not
constituents, and including SPX would put the predicted thing on both sides.
otv4 v1.3  2026-09-10  r336 - TABLE D (conviction) and TABLE E (per symbol). Operator:
*"I also want to know if per symbol conviction correlates."* D buckets each
call by conviction QUARTILE OF THE DATA rather than an assumed 0..1 scale -
the range is documented nowhere this repo owns, and hardcoded cut points are
how `selector` silently broke when the brief's `scores` payload changed scale.
Cut points are printed. BOTH tables are PER DIRECTION: the LONG calls carry
~0 edge and the SHORT calls may carry some, so pooling would let three times
as many uninformative LONG calls dilute the SHORT signal, or let the LONG base
rate masquerade as conviction working. A conviction of NULL is EXCLUDED and
counted, never bucketed as zero.
otv4 v1.2  2026-09-10  r335 - `--rows`: ONE LINE PER SYMBOL-DAY. Operator, on reading
v1.1's output: *"It's not by sym by day like I asked for."* The JOIN was always
per symbol-day; the OUTPUT collapsed straight to five bucket totals, so a single
busy name - META traded 28 times in one session - can carry a bucket with nobody
able to see it happen. Table C prints what the brief said, what the tape did,
what we did and what it made, per symbol per day, off the SAME join, so the two
views cannot disagree. `ours` reads MIXED when a symbol-day holds trades both
ways, because averaging those would invent a position nobody took.
otv4 v1.1  2026-09-10  r334 - REFUSES WHEN EVERY TRADE READ FAILED. v1.0 printed
"no closed trades in the window" while all 10,741 objects had been denied by
IAM - an absence the tool manufactured, rendered in the same font as a real
one. That is the shape this whole session has been finding, and it reached
production inside the tool built to avoid it.
otv4 v1.0  2026-09-10  r333 / BRF.1 step 2 — DOES THE MORNING BRIEF PREDICT THE
      TAPE, AND DOES TRADING AGAINST IT COST MONEY? Operator's experiment.

🔑 TWO QUESTIONS, DELIBERATELY NOT COLLAPSED — different samples, different
failure modes, and only one of them is about our P&L:

  A. BRIEF vs TAPE — did `composites.direction` match the realized
     close-to-close move? NO TRADES INVOLVED, so it holds on every symbol-day
     the brief scored including days we never traded the name. It is the
     larger sample and the one that decides whether a gate is worth building.
  B. TRADES vs BRIEF — closed trades split AGREE / DISAGREE / NEUTRAL against
     the brief's call for that symbol-day, compared on EXPECTANCY.

A brief that predicts nothing cannot be worth trading with; a brief that
predicts well may still cost nothing to trade against if we rarely do it.
One table cannot answer both, so two are printed and neither is summed.

🔴 CLOSE-TO-CLOSE, GAP INCLUDED — OPERATOR'S RULING, 2026-09-10: *"The gap
should be included because the report is cut before the open."* The brief
publishes ~09:00 ET, so the move it calls begins at the PRIOR SESSION'S close.
Open-to-close would credit it for a call the gap had already resolved.

🔴 THE BASE RATE IS THE TRAP, AND IT IS ALREADY VISIBLE. BULLISH 703 ·
BEARISH 344 · NEUTRAL 156 across 50 sessions — roughly 2:1. If the tape rose
on most days, a blended hit rate reads as skill on the skew alone. **Skill is
reported PER DIRECTION against the tape's own base rate in the same window,
and a blended number is never printed.**

🔑 TWO IMPORTS, NO FALLBACKS, BY DESIGN:
  · `price_bias` from day_trader_pro/standings.py — the ONLY definition of
    which way a position leans (call-ness XOR credit-ness, because a call
    credit spread is bearish). A local copy would drift from the report the
    operator reads.
  · `load_trades_versioned` from warehouse_source (r332) — reads the
    pre-epoch trades r314 soft-deleted, so the study gets all 50 sessions.
If either is missing this tool REFUSES. A fallback would silently answer a
smaller question and print it in the same font as the real one.

⚠️ PRIOR SESSION IS PER SYMBOL, FROM THE TAPE. Not "the calendar day before"
and not "the previous row in the composites table": a holiday, a weekend, or
a box that sat out would otherwise drop the session — and Monday, the highest
gap of the week, is exactly the one you cannot afford to lose.

⚠️ DESCRIPTIVE. Nothing here sizes or gates anything. A counter-bias veto
changes WHAT GETS TRADED and is the operator's call on evidence, not this
tool's (WA §31, §5).

Run (CONTROL):
    python3 tests/brief_bias_join.py                   # 09-01 onward
    python3 tests/brief_bias_join.py --all-history     # every composite
    python3 tests/brief_bias_join.py --from 2026-07-06 --to 2026-08-31
    python3 tests/brief_bias_join.py --selftest
"""
from __future__ import annotations

import argparse
import collections
import csv
import io
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BRIEF_DB = os.environ.get("SCREENER_DB",
                          os.path.expanduser("~/market-brief/screener.db"))
DTP_DIR = os.environ.get("DTP_DIR", os.path.expanduser("~/day_trader_pro"))
EPOCH = "2026-09-01"
DIR_MAP = {"BULLISH": "LONG", "BEARISH": "SHORT", "NEUTRAL": "NEUT"}


def load_price_bias():
    """The ONE definition, imported from the report the operator reads."""
    if DTP_DIR not in sys.path:
        sys.path.insert(0, DTP_DIR)
    try:
        from standings import price_bias                        # noqa: WPS433
    except Exception as exc:                                    # noqa: BLE001
        raise SystemExit(
            "  🔴 cannot import price_bias from {}/standings.py: {}\n"
            "     That module owns the call/put x debit/credit rule and this\n"
            "     tool will not restate it. Set DTP_DIR if control's repo is\n"
            "     elsewhere.".format(DTP_DIR, exc))
    return price_bias


def load_composites(lo, hi, db=None):
    """{(date, ticker): (LONG|SHORT|NEUT, score, conviction)}"""
    db = db or BRIEF_DB
    if not os.path.exists(db):
        raise SystemExit("  🔴 brief db not found: {} (set SCREENER_DB)".format(db))
    con = sqlite3.connect("file:{}?mode=ro".format(db), uri=True)
    con.row_factory = sqlite3.Row
    out = {}
    # ⚠️ ORDERED so the LAST composite of a day wins. A day can carry more
    # than one report tier; the latest call is the one that stood when the
    # bell rang, and averaging two calls would invent a third that nobody made.
    for r in con.execute(
            "SELECT report_date, ticker, score, direction, conviction "
            "FROM composites WHERE report_date >= ? AND report_date <= ? "
            "ORDER BY report_date, id", (lo, hi)):
        out[(r["report_date"], r["ticker"])] = (
            DIR_MAP.get(str(r["direction"] or "").upper(), "?"),
            r["score"], r["conviction"])
    con.close()
    return out


def with_lookback(sessions, days=6):
    """The window's sessions PLUS the calendar days before the first one.

    🔴 FOUND BY THE GATE, NOT BY READING: without this the tape is fetched
    only for the composite sessions, so the FIRST session in every window has
    no prior close and is silently dropped — systematically, and worst on a
    short window where one day is a large share of the sample. Six calendar
    days covers a weekend plus a Monday holiday; the extra listings are ~15
    objects each and only the ones that exist are read.
    """
    import datetime as _dt
    first = _dt.date.fromisoformat(sessions[0])
    pre = [(first - _dt.timedelta(days=i)).isoformat()
           for i in range(days, 0, -1)]
    return pre + list(sessions)


def closes_from_envelopes(envs):
    """{(date, symbol): last close} from raw/ohlc day-CSVs.

    ⚠️ The symbol and day come off the ENVELOPE, not off the key. `_wrap`
    stamps both, and parsing a path for data the object already carries is a
    second source of truth for one value.
    """
    out = {}
    for env in envs:
        sym, day = env.get("symbol"), env.get("dt")
        body = env.get("record")
        if not sym or not day or not isinstance(body, str):
            continue
        rows = list(csv.DictReader(io.StringIO(body)))
        if not rows:
            continue
        last = rows[-1]
        val = last.get("close", last.get("Close"))
        try:
            out[(day, sym)] = float(val)
        except (TypeError, ValueError):
            continue
    return out


def prior_sessions(closes):
    """{(date, sym): prior_date} — the previous session THAT SYMBOL traded."""
    by_sym = collections.defaultdict(list)
    for (d, s) in closes:
        by_sym[s].append(d)
    prev = {}
    for s, days in by_sym.items():
        days.sort()
        for i, d in enumerate(days):
            if i:
                prev[(d, s)] = days[i - 1]
    return prev


def realized(closes, prev, date, sym):
    """(LONG|SHORT|FLAT, pct) close-to-close, gap included. (None, None) if
    the prior session's close is missing — UNMEASURABLE IS NOT FLAT."""
    pd_ = prev.get((date, sym))
    if pd_ is None:
        return None, None
    a, b = closes.get((pd_, sym)), closes.get((date, sym))
    if a is None or b is None or not a:
        return None, None
    pct = (b - a) / a * 100.0
    return ("LONG" if pct > 0 else "SHORT" if pct < 0 else "FLAT"), pct


def brief_vs_tape(comps, closes, prev):
    per = collections.defaultdict(lambda: {"n": 0, "hit": 0, "sum": 0.0})
    base = collections.Counter()
    unmeasured = 0
    for (d, t), (called, _s, _c) in sorted(comps.items()):
        actual, pct = realized(closes, prev, d, t)
        if actual is None:
            unmeasured += 1
            continue
        if actual == "FLAT":
            continue
        base[actual] += 1
        if called not in ("LONG", "SHORT"):
            continue
        b = per[called]
        b["n"] += 1
        b["sum"] += pct
        if actual == called:
            b["hit"] += 1
    return per, base, unmeasured


def trades_vs_brief(trades, comps, bias_of):
    out = collections.defaultdict(lambda: {"n": 0, "net": 0.0, "wins": 0})
    for t in trades:
        if str(t.get("status") or "").lower() != "closed":
            continue
        try:
            pnl = float(t.get("pnl_usd"))
        except (TypeError, ValueError):
            continue
        d, sym = str(t.get("_dt") or ""), t.get("symbol") or "?"
        side = bias_of(t.get("option_side"), t.get("is_short_position"),
                       t.get("is_condor_leg", 0), t.get("center_symbol", ""))
        called = (comps.get((d, sym)) or ("", None, None))[0]
        if side in ("NEUT", "?"):
            key = "our trade NEUT/unknown"
        elif not called or called == "?":
            key = "no brief that day"
        elif called == "NEUT":
            key = "brief NEUTRAL"
        else:
            key = "AGREE" if side == called else "DISAGREE"
        b = out[key]
        b["n"] += 1
        b["net"] += pnl
        if pnl > 0:
            b["wins"] += 1
    return out


def _quartiles(vals):
    """Cut points from the DATA, not from an assumed 0..1 scale.

    ⚠️ `conviction`'s range is not documented anywhere this repo owns, and
    hardcoding 0.25/0.50/0.75 would silently put every row in one bucket if
    the scale were 0..8 — which is exactly what happened to `selector` when
    the brief's `scores` payload changed scale (the frozen-file incident).
    Quartiles of what is actually there cannot be wrong about the scale, and
    the cut points are PRINTED so the reader can see them.
    """
    xs = sorted(v for v in vals if v is not None)
    if len(xs) < 8:
        return []
    return [xs[int(len(xs) * f)] for f in (0.25, 0.50, 0.75)]


def by_conviction(comps, closes, prev):
    """Does a stronger call hit more often? Per direction, per quartile.

    🔑 PER DIRECTION, ALWAYS. The brief's LONG calls carry ~0 edge and its
    SHORT calls may carry some; pooling them would let the SHORT signal be
    diluted by three times as many uninformative LONG calls, or worse, let
    the LONG base rate masquerade as conviction working.
    """
    cuts = _quartiles([c for (_d, _t), (_dir, _s, c) in comps.items()])
    out = collections.defaultdict(lambda: {"n": 0, "hit": 0, "sum": 0.0})
    base = collections.Counter()
    nulls = 0
    for (d, t), (called, _score, conv) in comps.items():
        actual, pct = realized(closes, prev, d, t)
        if actual is None or actual == "FLAT":
            continue
        base[actual] += 1
        if called not in ("LONG", "SHORT"):
            continue
        if conv is None:
            nulls += 1
            continue
        q = 0
        for i, c in enumerate(cuts):
            if conv >= c:
                q = i + 1
        b = out[(called, q)]
        b["n"] += 1
        b["sum"] += pct
        if actual == called:
            b["hit"] += 1
    return out, base, cuts, nulls


def by_symbol(comps, closes, prev):
    """Per ticker: does the brief read some names better than others?"""
    out = collections.defaultdict(lambda: collections.defaultdict(
        lambda: {"n": 0, "hit": 0, "sum": 0.0}))
    for (d, t), (called, _s, _c) in comps.items():
        if called not in ("LONG", "SHORT"):
            continue
        actual, pct = realized(closes, prev, d, t)
        if actual is None or actual == "FLAT":
            continue
        b = out[t][called]
        b["n"] += 1
        b["sum"] += pct
        if actual == called:
            b["hit"] += 1
    return out


def render_conviction(out, base, cuts, nulls):
    print("\n  D. DOES CONVICTION CORRELATE?  (quartiles of the data)")
    if not cuts:
        print("     too few scored composites to cut into quartiles.")
        return
    tot = sum(base.values()) or 1
    print("     cut points: {}".format(
        " · ".join("%.3f" % c for c in cuts)))
    print("     {:<8} {:<4} {:>5} {:>8} {:>9} {:>9}".format(
        "called", "q", "n", "hit%", "edge", "avg move"))
    print("     " + "-" * 47)
    for call in ("LONG", "SHORT"):
        br = base.get(call, 0) / tot
        for q in range(4):
            b = out.get((call, q))
            if not b or not b["n"]:
                continue
            hit = b["hit"] / b["n"]
            print("     {:<8} {:<4} {:>5} {:>7.1%} {:>+9.1%} {:>+8.2f}%".format(
                call, "q%d" % (q + 1), b["n"], hit, hit - br, b["sum"] / b["n"]))
    if nulls:
        print("     ⚠️ {} call(s) had NO conviction value and are excluded, "
              "not bucketed as zero.".format(nulls))
    print("     ⚠️ edge is against that DIRECTION's base rate, as in table A.")
    print("        A rising edge down the quartiles is conviction working;")
    print("        a flat one means the number is decoration.")


def render_by_symbol(out):
    print("\n  E. PER SYMBOL — where the brief reads the tape")
    print("     {:<6} {:>4} {:>7} {:>9} {:>4} {:>7} {:>9}".format(
        "sym", "nL", "L hit%", "L move", "nS", "S hit%", "S move"))
    print("     " + "-" * 50)
    for t in sorted(out, key=lambda k: -(out[k]["SHORT"]["n"])):
        L, S = out[t]["LONG"], out[t]["SHORT"]
        def _f(b, key):
            if not b["n"]:
                return "—"
            return ("%.0f%%" % (100.0 * b["hit"] / b["n"]) if key == "hit"
                    else "%+.2f%%" % (b["sum"] / b["n"]))
        print("     {:<6} {:>4} {:>7} {:>9} {:>4} {:>7} {:>9}".format(
            t[:6], L["n"] or "—", _f(L, "hit"), _f(L, "mv"),
            S["n"] or "—", _f(S, "hit"), _f(S, "mv")))
    print("     ⚠️ Thin per-symbol counts. This is for spotting a name the")
    print("        brief cannot read at all, not for ranking the good ones.")


# SPX constituents among the scored panel. QQQ and SPX are excluded: an index
# and an ETF are not members, and including either would let the thing being
# predicted appear on both sides of the join.
SPX_PROXY = ("NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "UNH", "CRM",
             "AMD", "NFLX", "MU", "CVX", "PLTR")


def leg_weight(called, conv, floor=None):
    """One constituent's signed contribution, or None if it does not count.

    🔑 EXTRACTED AT r338 SO THE DAILY BOARD AND THE STUDY SHARE ONE RULE.
    `tools/brief_sigint.py` prints the SPX call every morning and this file
    scores it against the tape; if each implemented the weighting separately
    they would drift, and the board would then be advertising a signal the
    study never measured. Same reason `price_bias` lives in exactly one place.
    """
    if called not in ("LONG", "SHORT") or conv is None:
        return None
    if floor is not None and conv < floor:
        return None
    return conv if called == "LONG" else -conv


def composite_call(rows, floor=None, members=SPX_PROXY):
    """[(ticker, LONG|SHORT|NEUT, score, conviction)] -> (call, avg, n).

    The single-day form the board needs. `call` is NEUT when the signed sum
    is exactly zero or when nothing cleared the floor — a composite with no
    contributors is not a neutral view, and the caller is told n=0 so it can
    say which.
    """
    tot, k = 0.0, 0
    for t, called, _score, conv in rows:
        if t not in members:
            continue
        w = leg_weight(called, conv, floor)
        if w is None:
            continue
        tot += w
        k += 1
    if not k or tot == 0:
        return "NEUT", 0.0, k
    return ("LONG" if tot > 0 else "SHORT"), tot / k, k


def spx_composite(comps, closes, prev, floor=None, members=SPX_PROXY):
    """Can the constituents' calls stand in for the SPX call the brief never makes?

    🔴 WHY THIS EXISTS. SPX sits in market_brief's `_NON_EQUITY` and is never
    polled, so the largest net symbol in the book is silent on the brief every
    single day. These names ARE scored, and most of them move the index.

    ⚠️ EQUAL WEIGHT, DELIBERATELY, AND IT IS A LIMITATION NOT A CHOICE OF
    TASTE. Index weights are nowhere in these repos; NVDA and CRM do not move
    SPX comparably. Equal weight is defensible for DIRECTION and wrong for
    magnitude, so this tests direction only and buys weights only if the
    direction works.

    ⚠️ CONVICTION-WEIGHTED SUM, NOT A VOTE COUNT. A vote count would let five
    weak calls outrank two strong ones, and r336 established that a call below
    the floor is worse than no call — so `floor` drops those entirely rather
    than letting them dilute the sum.
    """
    per_day = collections.defaultdict(lambda: {"sum": 0.0, "n": 0})
    for (d, t), (called, _s, conv) in comps.items():
        if t not in members:
            continue
        w = leg_weight(called, conv, floor)
        if w is None:
            continue
        b = per_day[d]
        b["sum"] += w
        b["n"] += 1
    rows, base = [], collections.Counter()
    for d, b in sorted(per_day.items()):
        if not b["n"]:
            continue
        actual, pct = realized(closes, prev, d, "SPX")
        if actual is None or actual == "FLAT":
            continue
        base[actual] += 1
        called = "LONG" if b["sum"] > 0 else "SHORT" if b["sum"] < 0 else "FLAT"
        rows.append((d, called, b["sum"] / b["n"], b["n"], actual, pct))
    return rows, base


def render_spx(rows, base, floor_label):
    print("\n  F. SPX COMPOSITE from constituents  [{}]".format(floor_label))
    if not rows:
        print("     no measurable SPX sessions — the composite cannot be scored.")
        return
    tot = sum(base.values()) or 1
    print("     SPX base rate: LONG {:.1%} · SHORT {:.1%}   (n={})".format(
        base.get("LONG", 0) / tot, base.get("SHORT", 0) / tot, tot))
    per = collections.defaultdict(lambda: {"n": 0, "hit": 0, "sum": 0.0})
    for _d, called, _str, _k, actual, pct in rows:
        if called == "FLAT":
            continue
        b = per[called]
        b["n"] += 1
        b["sum"] += pct
        if called == actual:
            b["hit"] += 1
    print("     {:<8} {:>5} {:>8} {:>8} {:>9} {:>9}".format(
        "called", "n", "hit%", "base%", "edge", "avg move"))
    print("     " + "-" * 51)
    for call in ("LONG", "SHORT"):
        b = per.get(call)
        if not b or not b["n"]:
            print("     {:<8} {:>5}        —        —         —         —"
                  .format(call, 0))
            continue
        hit = b["hit"] / b["n"]
        br = base.get(call, 0) / tot
        print("     {:<8} {:>5} {:>7.1%} {:>8.1%} {:>+9.1%} {:>+8.2f}%".format(
            call, b["n"], hit, br, hit - br, b["sum"] / b["n"]))
    strong = [r for r in rows if abs(r[2]) >= 0.5 and r[1] != "FLAT"]
    if strong:
        h = sum(1 for r in strong if r[1] == r[4]) / len(strong)
        print("     agreement |avg conv| >= 0.50: n={} hit {:.1%}".format(
            len(strong), h))
    print("     ⚠️ EQUAL WEIGHT — index weights are not in these repos, so this")
    print("        tests DIRECTION only. Magnitude would need real weights.")


def symbol_day_rows(trades, comps, closes, prev, bias_of):
    """One row per (date, symbol) — what the brief said, what the tape did,
    what we did, and what it made.

    🔑 THE BUCKETS ANSWER "DID IT COST US"; THIS ANSWERS "ON WHAT". The join
    was always per symbol-day, but collapsing straight to five totals means a
    single busy name — META traded 28 times on one session — can carry a
    bucket, and nobody can see it happen. Both views come off the same join,
    so they cannot disagree.
    ⚠️ `ours` is MIXED when a symbol-day holds trades in both directions.
    Averaging those into one direction would invent a position nobody took.
    """
    agg = {}
    for t in trades:
        if str(t.get("status") or "").lower() != "closed":
            continue
        try:
            pnl = float(t.get("pnl_usd"))
        except (TypeError, ValueError):
            continue
        d, sym = str(t.get("_dt") or ""), t.get("symbol") or "?"
        side = bias_of(t.get("option_side"), t.get("is_short_position"),
                       t.get("is_condor_leg", 0), t.get("center_symbol", ""))
        a = agg.setdefault((d, sym), {"n": 0, "net": 0.0, "sides": set()})
        a["n"] += 1
        a["net"] += pnl
        a["sides"].add(side)
    rows = []
    for (d, sym), a in sorted(agg.items()):
        called = (comps.get((d, sym)) or ("—", None, None))[0] or "—"
        actual, pct = realized(closes, prev, d, sym)
        sides = a["sides"] - {"?"}
        ours = (sides.pop() if len(sides) == 1 else
                ("MIXED" if len(sides) > 1 else "?"))
        verdict = ("—" if called in ("—", "?", "NEUT") or ours not in
                   ("LONG", "SHORT") else
                   ("agree" if ours == called else "AGAINST"))
        rows.append((d, sym, called, actual or "—", pct, ours, verdict,
                     a["n"], a["net"]))
    return rows


def render_rows(rows):
    print("\n  C. EVERY SYMBOL-DAY WE TRADED")
    print("     {:<10} {:<5} {:<6} {:<6} {:>7} {:<6} {:>8} {:>3} {:>9}".format(
        "date", "sym", "brief", "tape", "move%", "ours", "vs brief", "n", "net"))
    print("     " + "-" * 68)
    for d, sym, called, actual, pct, ours, verdict, n, net in rows:
        print("     {:<10} {:<5} {:<6} {:<6} {:>7} {:<6} {:>8} {:>3} {:>9,.0f}"
              .format(d, sym[:5], called, actual,
                      ("%+.2f" % pct) if pct is not None else "—",
                      ours, verdict, n, net))


def render(per, base, unmeasured, buckets, window, severed):
    print("=" * 72)
    print("  BRIEF BIAS JOIN — close-to-close, gap included   [{}]".format(window))
    print("=" * 72)
    if severed:
        print("  ⚠️ {} trade object(s) read from BEHIND a delete marker "
              "(r314's strip".format(severed))
        print("     is intact; nothing was restored and the engine's view is "
              "unchanged).")
    tot = sum(base.values())
    print("\n  A. BRIEF vs TAPE — no trades involved")
    if not tot:
        print("     no measurable symbol-days — the tape side is empty.")
    else:
        print("     tape base rate: LONG {:.1%} · SHORT {:.1%}   (n={})".format(
            base.get("LONG", 0) / tot, base.get("SHORT", 0) / tot, tot))
        print("     {:<8} {:>5} {:>8} {:>8} {:>9} {:>9}".format(
            "called", "n", "hit%", "base%", "edge", "avg move"))
        print("     " + "-" * 51)
        for call in ("LONG", "SHORT"):
            b = per.get(call)
            if not b or not b["n"]:
                print("     {:<8} {:>5}        —        —         —         —"
                      .format(call, 0))
                continue
            hit = b["hit"] / b["n"]
            br = base.get(call, 0) / tot
            print("     {:<8} {:>5} {:>7.1%} {:>8.1%} {:>+9.1%} {:>+8.2f}%"
                  .format(call, b["n"], hit, br, hit - br, b["sum"] / b["n"]))
        print("     ⚠️ edge = hit% MINUS the tape's own base rate for that")
        print("        direction. The brief calls up about twice as often as")
        print("        down, so a BLENDED hit rate would read as skill on the")
        print("        skew alone. It is not printed.")
    if unmeasured:
        print("     ⚠️ {} composite(s) had no prior-session close and are "
              "EXCLUDED,".format(unmeasured))
        print("        not counted as misses.")

    print("\n  B. TRADES vs BRIEF — this one is about us")
    print("     {:<23} {:>5} {:>11} {:>10} {:>7}".format(
        "bucket", "n", "net", "exp/trade", "win%"))
    print("     " + "-" * 58)
    any_row = False
    for k in ("AGREE", "DISAGREE", "brief NEUTRAL", "no brief that day",
              "our trade NEUT/unknown"):
        b = buckets.get(k)
        if not b or not b["n"]:
            continue
        any_row = True
        print("     {:<23} {:>5} {:>11,.0f} {:>10,.0f} {:>6.0%}".format(
            k, b["n"], b["net"], b["net"] / b["n"], b["wins"] / b["n"]))
    if not any_row:
        print("     no closed trades in the window.")
    print("\n  ⚠️ DESCRIPTIVE. Nothing here sizes or gates anything. A")
    print("     counter-bias veto changes WHAT GETS TRADED and is the")
    print("     operator's call on evidence, not this tool's (WA §31).")


def selftest() -> int:
    ok = True
    closes = {("2026-09-01", "N"): 100.0, ("2026-09-02", "N"): 102.0,
              ("2026-09-03", "N"): 101.0}
    prev = prior_sessions(closes)
    ok &= prev[("2026-09-02", "N")] == "2026-09-01"
    a, pct = realized(closes, prev, "2026-09-02", "N")
    ok &= a == "LONG" and abs(pct - 2.0) < 1e-9
    ok &= realized(closes, prev, "2026-09-03", "N")[0] == "SHORT"
    # first session of a symbol has no prior close -> unmeasurable, not FLAT
    ok &= realized(closes, prev, "2026-09-01", "N") == (None, None)
    # a weekend gap: the prior SESSION, not the calendar day before
    cl2 = {("2026-09-04", "N"): 10.0, ("2026-09-08", "N"): 11.0}
    p2 = prior_sessions(cl2)
    ok &= p2[("2026-09-08", "N")] == "2026-09-04"

    # THE BASE-RATE GUARD: always-LONG on an up-only tape must show ZERO edge.
    comps = {("2026-09-02", "N"): ("LONG", 1.0, 1.0),
             ("2026-09-03", "N"): ("LONG", 1.0, 1.0)}
    cl3 = {("2026-09-01", "N"): 10.0, ("2026-09-02", "N"): 11.0,
           ("2026-09-03", "N"): 12.0}
    per, base, _u = brief_vs_tape(comps, cl3, prior_sessions(cl3))
    edge = per["LONG"]["hit"] / per["LONG"]["n"] - base["LONG"] / sum(base.values())
    ok &= abs(edge) < 1e-9

    # a CSV with a header and two rows yields the LAST close
    env = [{"symbol": "N", "dt": "2026-09-02",
            "record": "ts,open,close\n1,1,5.0\n2,1,7.5\n"}]
    ok &= closes_from_envelopes(env) == {("2026-09-02", "N"): 7.5}
    # the lookback: the window's first session must have a prior day fetched
    # table C: MIXED when a symbol-day was traded both ways
    _cl = {("2026-09-01", "N"): 10.0, ("2026-09-02", "N"): 11.0}
    _pv = prior_sessions(_cl)
    _tr = [{"status": "closed", "pnl_usd": 5.0, "_dt": "2026-09-02",
            "symbol": "N", "option_side": "call", "is_short_position": 0},
           {"status": "closed", "pnl_usd": -2.0, "_dt": "2026-09-02",
            "symbol": "N", "option_side": "put", "is_short_position": 0}]
    _rows = symbol_day_rows(_tr, {("2026-09-02", "N"): ("LONG", 1, 1)},
                            _cl, _pv, lambda side, sh, *_a: (
                                "LONG" if (side == "call") != bool(int(sh))
                                else "SHORT"))
    ok &= len(_rows) == 1 and _rows[0][5] == "MIXED" and _rows[0][7] == 2
    ok &= abs(_rows[0][8] - 3.0) < 1e-9
    wl = with_lookback(["2026-09-02", "2026-09-03"])
    ok &= wl[-2:] == ["2026-09-02", "2026-09-03"] and "2026-08-27" in wl
    print("brief_bias_join selftest:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to", dest="to")
    ap.add_argument("--all-history", action="store_true")
    ap.add_argument("--spx", action="store_true",
                    help="table F: an SPX call built from its constituents")
    ap.add_argument("--floor", type=float, default=0.640,
                    help="conviction floor for the gated composite (r336)")
    ap.add_argument("--by-symbol", action="store_true",
                    help="add table E: per-ticker hit rates")
    ap.add_argument("--rows", action="store_true",
                    help="one line per symbol-day: brief, tape, ours, net")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    import warehouse_source as ws
    if not hasattr(ws, "load_trades_versioned"):
        raise SystemExit("  🔴 warehouse_source has no load_trades_versioned "
                         "(r332). Refusing rather than silently reading only "
                         "the post-epoch window.")
    bias_of = load_price_bias()

    lo = a.frm or ("2026-07-05" if a.all_history else EPOCH)
    hi = a.to or ws._et_today()
    comps = load_composites(lo, hi)
    if not comps:
        print("  no composites in {}..{} — nothing to join.".format(lo, hi))
        return 0
    sessions = sorted({d for d, _t in comps})
    print("  BRIEF : {} — {} composite(s), {} session(s), {}..{}".format(
        BRIEF_DB, len(comps), len(sessions), sessions[0], sessions[-1]))

    tape_days = with_lookback(sessions)
    meta_o = ws.Meta("ohlc {}..{}".format(tape_days[0], tape_days[-1]))
    closes = closes_from_envelopes(
        ws._envelopes(ws.client(), "ohlc", tape_days, meta_o))
    print("  TAPE  : " + meta_o.banner())
    print("          {} symbol-day close(s)".format(len(closes)))

    trades, meta_t = ws.load_trades_versioned(sessions)
    print("  TRADES: " + meta_t.banner())
    # 🔴 r334 — AN EMPTY TABLE B IS A RESULT; A FAILED READ IS NOT. r333
    # rendered "no closed trades in the window" while every one of 10,741
    # objects had been denied, which reads as a finding about the book.
    if meta_t.listed and not meta_t.read:
        raise SystemExit(
            "  🔴 {} trade object(s) listed and NONE could be read. That is a\n"
            "     read failure, not an empty book, and table B would have\n"
            "     rendered it as 'no closed trades'. Refusing.\n"
            "     {}".format(meta_t.listed, meta_t.first_error or ""))

    prev = prior_sessions(closes)
    per, base, unmeasured = brief_vs_tape(comps, closes, prev)
    buckets = trades_vs_brief(trades, comps, bias_of)
    render(per, base, unmeasured, buckets, "{}..{}".format(lo, hi),
           getattr(meta_t, "severed", 0))
    cv, cbase, cuts, nulls = by_conviction(comps, closes, prev)
    render_conviction(cv, cbase, cuts, nulls)
    if a.spx:
        r_all, b_all = spx_composite(comps, closes, prev, floor=None)
        render_spx(r_all, b_all, "all calls")
        r_fl, b_fl = spx_composite(comps, closes, prev, floor=a.floor)
        render_spx(r_fl, b_fl, "floor {:.3f}".format(a.floor))
    if a.by_symbol:
        render_by_symbol(by_symbol(comps, closes, prev))
    if a.rows:
        render_rows(symbol_day_rows(trades, comps, closes, prev, bias_of))
    return 0


if __name__ == "__main__":
    sys.exit(main())
