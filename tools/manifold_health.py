#!/usr/bin/env python3
"""
tools/manifold_health.py  v4.4
v4.4 2026-10-05  OTV4TEST r252 (BOX.18) - A FOREIGN SYMBOL'S CANDLES NO LONGER JUDGE THIS BOX, AND THE TAPE QUESTION IS ASKED OF
      THE BOX'S OWN INSTRUMENT. SPX-TEST was AAL until 2026-10-03 and its store still holds AAL rows: the board painted AAL/*
      amber in RTH, the rollup went DEGRADED, and the 09:35 open scan read it as RED feed:rollup (10-05). And --symbol
      defaulted to the shell's OT_INSTRUMENT, which devtools does not set, so SPX (a cash index) showed prints amber off
      AAL's old tape instead of n/a. A candle whose base symbol is neither the box instrument nor VIX is FOREIGN: shown,
      with its real age, under its own heading, painted n/a, and kept out of the rollup and --bulb. UNSET instrument =
      the old behaviour (everything judged) - never a guess.
v4.3 2026-09-26  OTV4TEST r146 — {SYM} resolves through box_instrument(): devtools runs this from a shell without OT_INSTRUMENT, so the board read QQQ's rows on every box.

One bulb per stream. All green = manifold green.

v4.2  2026-09-18  OTV4TEST r38 — THE BOARD SHOWS THE UNDERLYING'S OWN QUOTE, AND
      READS IN 2.2s INSTEAD OF 56.7s. The operator opened it, saw a header and
      then nothing, and reported it broken — then corrected himself: "it's not
      broken. It was just slow." Both halves were defects.
      🔴 SLOW: one query. `SELECT COUNT(*) FROM quote_series` scans 22.8M rows —
      MEASURED 56.72s, against 0.09s capped and 0.00s for the indexed MAX(ts).
      An exact LIFETIME count on a table the purge trims every three days is not
      a number anyone acts on; the bulb is driven by FRESHNESS. Counts now stop
      at ROW_CAP and SAY so ("1000000+"). A board slow enough to look hung stops
      being read, which is §17's "an alarm that gets filtered" one step on.
      🔴 BLIND: r36 subscribed the underlying's Quote (FEED.2) and it landed in
      `quote_series` beside 22.8M option quotes, so the ONLY source of RESTING
      DEPTH on this box was invisible here. STREAMS tuples gain a 7th field, a
      WHERE, and the ticker gets its own line — scoped by equality on the PK's
      leading column, so it costs nothing to read.
      ⚠️ NOT critical, deliberately: nothing consumes it yet (§31), and an unread
      stream must not paint the rollup red.
      ⚠️ AND THIS IS NOT `underlying_series`, which r125 removed on the operator's
      ruling because it never published. This is the Quote event on the ticker,
      which does — 219 rows in the twenty minutes after the bake.
v4.1  2026-08-24  r95 AFTER-HOURS IS ITS OWN SECTION, AND `prints` ON AN INDEX
IS n/a. Operator: "those sections will never be green during RTH & if used in
the dashboard, it would never show green."

🔴 THE BOARD COULD NOT REACH GREEN DURING RTH, AND THAT IS A DESIGN FAULT IN
THE BOARD RATHER THAN A FAULT IN THE FEED. `<SYM>_EXT` is the NON-RTH route:
every bar outside 09:30-16:00 is segregated to it, which means that during RTH
it correctly receives nothing and ages. VIX_EXT/1m read age=4868s at 10:36 —
a 09:15 bar, exactly as designed. A permanently-amber row is not observability;
it is how a reader is trained to stop looking (WORKING_AGREEMENT 17, and the
CV.1 failure).

⚠️ SO FRESHNESS IS NOW JUDGED IN THE STREAM'S OWN WINDOW. An RTH stream is
judged during RTH and idles after the close; an after-hours stream is judged
outside RTH and idles during it. The rollup only ever considers what is in its
window. This is the SAME rule the file already applied in one direction — it
just never applied it in the other.

⚠️ `prints` ON A CASH INDEX RENDERS n/a, NOT RED. An index is a calculated
value with no order flow, so TimeAndSale can never deliver — empty BY
CONSTRUCTION, not by failure. 🔴 THE SUBSCRIPTION IS UNTOUCHED. Operator's
standing instruction: "DO NOT unsubscribe to ANYTHING. You can choose not to
write it or not to display it, but we subscribe to EVERYTHING, period." That is
docs/FEED_MANIFOLD.md's governing rule, and an unsubscribe is unrecoverable in
a way a suppressed bulb is not — DXFeed history is same-evening only.

⚠️ `underlying` AND `theo price` ARE LEFT ALONE AND STAY RED AT ZERO ROWS.
They are option-chain events an index legitimately has; whether they arrive is
an ENTITLEMENT question this tool cannot answer, and dressing "did not arrive"
up as "cannot exist" is the precise error the board exists to prevent. The
legend now says so out loud.

v4.0  2026-08-25  Operator's design: "every data stream that it's splitting
should have its own red light or green light, and if they're all green,
manifold health is green" — plus a single rollup bulb for status.py.

🔴 WHY THIS EXISTS. On 2026-08-21 the intraday tape was dead from 09:30 and
nothing said so. The operator found it by hand at 09:31; the blind latch pages
ONCE per outage so the silence afterwards meant nothing; the fleet traded zero
and the cause took until evening to establish. **A stream that stops must be
visible in one glance, per stream, before the open.**

⚠️ IT READS THE STORE, NOT THE CODE. A subscription list proves what we ASKED
for. This proves what ARRIVED. Every failure this month lived in that gap.

⚠️ MISSING IS NOT STALE AND NEITHER IS ZERO. Three distinct states:
    GREEN   fresh rows inside the budget
    AMBER   rows exist but the newest is older than the budget  (STALE)
    RED     no rows at all                                      (MISSING)
An entitlement that does not cover a stream and a stream that died look
identical in a row count — so the bulb says which, and never guesses.

⚠️ OFF-HOURS IS NOT A FAULT. Outside RTH every intraday stream is legitimately
stale, and painting fifteen boxes red every evening is how an operator learns
to ignore the board. `--rth-only` (default ON) reports staleness as GREY/IDLE
when the market is shut.

Run:  python3 tools/manifold_health.py            # the board
      python3 tools/manifold_health.py --json     # machine-readable
      python3 tools/manifold_health.py --bulb     # one line, for status.py
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, time as dtime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GREEN, AMBER, RED, GREY = "🟢", "🟡", "🔴", "⚪"
# ⚫ = NOT APPLICABLE to this instrument. A THIRD FACT, distinct from both
# "missing" and "idle": the stream cannot exist here, so no operator action
# will ever change it. RED would be a standing false alarm; GREY would imply it
# is merely resting and might return.
NA = "⚫"

# Freshness budgets, seconds. Generous — this asks "did the pipe break", not
# "is latency good".
CANDLE_BUDGET = {"1m": 180, "5m": 900, "15m": 2700, "1h": 9000, "1d": 200000}

# (table, ts column, budget seconds, label, critical)
# ⚠️ `critical` MARKS WHAT TRADING ACTUALLY DEPENDS ON. prints and theo are
# rich and new; the bot does not yet require them, so their absence must not
# paint the rollup red and teach the operator to ignore it.
# (table, ts column, budget seconds, label, critical, after_hours)
# ⚠️ `after_hours` MEANS "JUDGED OUTSIDE RTH, IDLE DURING IT". `session_summary`
# is a SESSION-BOUNDARY datum carrying prev_day_close_price — it lands once and
# its freshness during the session is meaningless, so at a 3600s budget it went
# amber every day from roughly 10:45 onward and stayed there.
# r38 — a 7th field, WHERE: a SQL predicate scoping the row, or None for the
# whole table. It exists so the UNDERLYING's own quote can have a line of its
# own: `quote_series` is 22.8M rows of option contracts, and the ticker's bid/ask
# was invisible inside that total.
STREAMS = [
    ("greeks_series",     "ts_epoch",      300,  "greeks (series)",   True,  False, None),
    ("quote_series",      "ts_epoch",      300,  "quotes (chain)",    True,  False, None),
    # 🔴 r38 — THE UNDERLYING'S OWN BID/ASK, the r36 stream (FEED.2). It is the
    # ONLY source of RESTING DEPTH on this box — `prints` says what TRADED, and
    # the question "where does size park" cannot be answered from that. Scoped by
    # equality on the PK's leading column, so it costs nothing to read.
    # ⚠️ NOT critical: nothing consumes it yet (§31, collection first), so its
    # absence must not paint the rollup red and teach the operator to skip it.
    # ⚠️ AND THIS IS NOT `underlying_series`, which r125 removed on the operator's
    # ruling — *"I don't want underlying on the manifold at all"* — because that
    # stream never published. This is the Quote event on the ticker, which does.
    ("quote_series",      "ts_epoch",      600,  "quotes (underlying)", False, False,
     "streamer_symbol = '{SYM}'"),
    ("chain_marks",       "updated_epoch", 300,  "chain marks",       True,  False, None),
    ("prints",            "ts_epoch",      600,  "prints (T&S)",      False, False, None),
    ("last_trade",        "ts_epoch",      600,  "last trade",        False, False, None),
    # 🔴 r125 — `underlying` AND `theo price` ARE OFF THE BOARD. Operator,
    # 2026-08-25: "I don't want underlying on the manifold at all. You can also
    # take off THEO. We tried it, it's not worth the traffic burden with no
    # readers."
    # · UNDERLYING never published on either symbol space — probed 2026-08-24
    #   with Trade/Greeks/Quote as live controls, zero events on both arms. A
    #   permanent red for a stream the venue does not send teaches the operator
    #   to ignore red, which is the only thing the board is for.
    # · THEO was proven reachable (r116: 12 events on 12 option symbols) and
    #   then REMOVED in r118 after SPX lost its entire per-contract
    #   subscription with it attached. It has no consumer and never had one.
    # Both TABLES remain and both WRITERS remain — this removes them from the
    # HEALTH VIEW only, so restoring a row is one line if either gains a reader.
    ("session_summary",   "ts_epoch",     3600,  "session summary",   False, True,  None),
]

# Streams that CANNOT EXIST for a cash index — no order flow in the index
# itself, so no time-and-sale. Deliberately NOT extended to underlying/theo:
# see the header.
# 🔴 r38 — THE BOARD TOOK 56.72 SECONDS, AND ALL OF IT WAS ONE QUERY.
# `SELECT COUNT(*) FROM quote_series` scans 22.8M rows; measured 56.72s against
# 0.09s for the same count capped, and MAX(ts) is instant on its index. An exact
# lifetime row count on a purged table is not a number anyone acts on — the bulb
# is driven by FRESHNESS — so the count stops at the cap and SAYS it stopped
# ("1000000+"). A board slow enough to look hung is a board that stops being read.
ROW_CAP = 1_000_000

INDEX_NA_TABLES = {"prints"}

DERIVED = [
    ("indicator_series", "ts_epoch",  600, "indicators (ADX/ATR/VWAP)"),
    ("fork_series",      "ts_epoch",  600, "pitchfork"),
    ("level_ledger",     "created_ts", 0,  "levels"),
    ("surface_series",   "ts_epoch",  900, "surface (charm/vanna)"),
]


def _rth_now(now=None) -> bool:
    """🔴 r125 — MARKET HOURS ARE AN EXCHANGE FACT, SO THIS ASKS IN ET.

    `datetime.now()` was the BOX's clock and the boxes run UTC, so this read
    18:12 at 14:12 ET and declared the session over while it was in progress.
    Found 2026-08-25 from a QQQ board headed "outside RTH" at 2:12pm with
    QQQ/1m at age=1s.

    ⚠️ THE PROJECT'S RULE, operator 2026-08-25: "Backend facing code should
    render in UTC. User facing code should render in EST." THIS IS NEITHER —
    it renders nothing. It is a PREDICATE about the market, and the market
    opens at 09:30 Eastern whatever a server's clock says. So the timezone
    here is not a display choice and must not be read as one: converting a
    STORAGE path to ET on the strength of this line would be the opposite
    mistake. ts_epoch stays UTC; only the question "is the exchange open"
    is asked in the exchange's own frame.

    ⚠️ AND THE CONSEQUENCE WAS NOT COSMETIC. `_in_window` INVERTS on this
    flag, so a false reading made the `_EXT` after-hours rows count as
    in-window and their by-design staleness painted the rollup AMBER — the
    DEGRADED on status.py mid-session. A clock error presented as a data fault.
    """
    from utils.time_utils import ET
    n = now or datetime.now(ET)
    if n.weekday() >= 5:
        return False
    return dtime(9, 30) <= n.time() <= dtime(16, 0)


def _q1(conn, sql, args=()):
    try:
        return conn.execute(sql, args).fetchone()
    except sqlite3.Error:
        return None


def _bulb(rows, age, budget, in_window) -> str:
    """GREEN/AMBER/RED, where AMBER only fires INSIDE the stream's own window.

    ⚠️ `in_window` IS NOT `in_rth`. For an RTH stream they are the same thing;
    for an after-hours stream (`*_EXT`, session summary) it is the INVERSE. A
    stream that is legitimately idle must never paint amber, in either
    direction — that was the whole reason the board could not go green during
    RTH.
    """
    if not rows:
        return RED
    if budget and age is not None and age > budget:
        return AMBER if in_window else GREY
    return GREEN


def _is_after_hours_candle(label: str) -> bool:
    """`<SYM>_EXT/<tenor>` is the non-RTH route — see candle_feed's RTH guard."""
    return label.split("/", 1)[0].endswith("_EXT")


def _box_feed_bases() -> set:
    """v4.4 - the base symbols this box's candle feed writes (its instrument and VIX), or
    an EMPTY set when the instrument is UNSET, which judges every candle as before."""
    from utils.instrument import box_instrument, UNSET
    sym = (box_instrument() or "").strip().upper()
    if not sym or sym == UNSET:
        return set()
    return {sym, "VIX"}


def _is_foreign(label: str, bases: set) -> bool:
    """`<SYM>[_EXT]/<tf>` whose base is not one this box feeds (v4.4)."""
    if not bases:
        return False
    base = label.split("/", 1)[0].upper()
    if base.endswith("_EXT"):
        base = base[:-4]
    return base not in bases


def collect(feed_db: str, derived_db: str, in_rth: bool,
            is_index=None) -> dict:
    now = time.time()
    # v4.4 - None asks the BOX, never the caller's shell (open_scan passed nothing,
    # devtools sets no OT_INSTRUMENT): a cash index has no tape, whoever asks.
    if is_index is None:
        try:
            from utils.instrument import box_instrument
            from config import is_cash_index
            is_index = bool(is_cash_index(box_instrument()))
        except Exception:                                       # noqa: BLE001
            is_index = False
    out = {"streams": [], "candles": [], "derived": [], "in_rth": in_rth,
           "is_index": is_index}

    fc = None
    if os.path.exists(feed_db):
        fc = sqlite3.connect(f"file:{feed_db}?mode=ro", uri=True)

    if fc is None:
        out["fatal"] = f"no feed store at {feed_db}"
        return out

    for tbl, tscol, budget, label, critical, after_hours, where in STREAMS:
        pred = ""
        if where:
            from utils.instrument import box_instrument     # r146: never QQQ by default
            pred = " WHERE " + where.replace("{SYM}", box_instrument())
        # capped count (see ROW_CAP) + an indexed MAX: two cheap queries instead
        # of one 56-second scan.
        r = _q1(fc, f"SELECT COUNT(*) FROM (SELECT 1 FROM {tbl}{pred} LIMIT {ROW_CAP})")
        rows = (r[0] if r else 0) or 0
        capped = rows >= ROW_CAP
        r2 = _q1(fc, f"SELECT MAX({tscol}) FROM {tbl}{pred}")
        age = (now - r2[0]) if (r2 and r2[0]) else None
        # A stream that cannot exist for this instrument is n/a, and n/a is
        # NOT a degraded green — it is the absence of a question.
        if is_index and tbl in INDEX_NA_TABLES:
            bulb = NA
        else:
            bulb = _bulb(rows, age, budget,
                         (not in_rth) if after_hours else in_rth)
        out["streams"].append({
            "label": label, "table": tbl, "rows": rows, "capped": capped,
            "age_s": round(age) if age is not None else None,
            "bulb": bulb, "critical": critical, "after_hours": after_hours})

    r = _q1(fc, "SELECT symbol, interval, COUNT(*), MAX(ts_epoch_ms)"
                " FROM candles GROUP BY symbol, interval")
    try:
        rows = fc.execute("SELECT symbol, interval, COUNT(*), MAX(ts_epoch_ms)"
                          " FROM candles GROUP BY symbol, interval").fetchall()
    except sqlite3.Error:
        rows = []
    bases = _box_feed_bases()
    for sym, iv, n, newest in rows:
        age = now - (newest or 0) / 1000.0
        label = f"{sym}/{iv}"
        ah = _is_after_hours_candle(label)
        foreign = _is_foreign(label, bases)
        out["candles"].append({
            "label": label, "rows": n, "age_s": round(age),
            "after_hours": ah, "foreign": foreign,
            "bulb": NA if foreign else _bulb(n, age, CANDLE_BUDGET.get(iv, 3600),
                                             (not in_rth) if ah else in_rth)})

    if os.path.exists(derived_db):
        dc = sqlite3.connect(f"file:{derived_db}?mode=ro", uri=True)
        # Engine self-reports, if the layer has run at all.
        try:
            _st = dc.execute(
                "SELECT name, runs, failures, last_rows, last_error"
                " FROM derived_engine_status ORDER BY name").fetchall()
            out["engines"] = [{"name": r[0], "runs": r[1], "failures": r[2],
                               "last_rows": r[3], "last_error": r[4]}
                              for r in _st]
        except Exception:                                       # noqa: BLE001
            # ⚠️ NOT AN ERROR ON AN OLD BOX — the table only exists once a box
            # runs the build that writes it. None means "cannot say"; [] would
            # claim the layer ran and reported nothing, which is a real and
            # different finding.
            out["engines"] = None

        for tbl, tscol, budget, label in DERIVED:
            # r38 — capped, same reason as the streams loop: `surface_series`
            # is 882k rows today and only grows, and the bulb is driven by
            # FRESHNESS, not by a lifetime total.
            r = _q1(dc, f"SELECT COUNT(*) FROM (SELECT 1 FROM {tbl} LIMIT {ROW_CAP})")
            r = ((r[0] if r else 0), (_q1(dc, f"SELECT MAX({tscol}) FROM {tbl}") or [None])[0])
            rows = (r[0] if r else 0) or 0
            age = (now - r[1]) if (r and r[1]) else None
            out["derived"].append({
                "label": label, "rows": rows,
                "age_s": round(age) if age is not None else None,
                # ⚠️ DERIVED PORTS NEVER PAINT THE ROLLUP RED. Operator's
                # standing rule: derivers are contributors, never gates. A
                # missing derived value is not an outage.
                "bulb": _bulb(rows, age, budget, in_rth)})
    return out


def _in_window(row: dict, in_rth: bool) -> bool:
    """True when this row is in the window where its freshness MEANS anything."""
    return (not in_rth) if row.get("after_hours") else in_rth


def rollup(rep: dict) -> str:
    """One bulb for status.py. RED only when something TRADING needs is gone.

    ⚠️ AFTER-HOURS ROWS NEVER PAINT THE RTH ROLLUP, AND VICE VERSA. `<SYM>_EXT`
    is the non-RTH route and receives nothing during the session BY DESIGN, so
    counting its staleness against the session rollup made GREEN unreachable
    during RTH — the board could only ever say DEGRADED. A rollup that cannot
    reach its own good state is not a rollup.

    ⚠️ AND n/a IS NOT A FAULT. A stream that cannot exist for this instrument
    is excluded outright rather than being counted as a soft red.
    """
    if rep.get("fatal"):
        return RED
    # 🔴 r125 — AFTER-HOURS ROWS NEVER PAINT THE ROLLUP, IN EITHER DIRECTION.
    # Operator, 2026-08-25: "I don't want manifold health degraded for
    # after-hours sources." The prior rule excluded them during RTH only, so
    # outside RTH they became the rollup — and a `VIX_EXT/1h` that has not
    # ticked since yesterday afternoon is not a fault at 8pm any more than it
    # is at 2pm. VIX simply does not trade after hours the way QQQ does.
    # ⚠️ THIS IS A JUDGEMENT ABOUT WHAT THE BULB IS FOR, not about the data.
    # The rows stay on the BOARD with their real ages — nothing is hidden — but
    # the one-bulb summary now answers only "can this box trade", and no
    # after-hours stream can answer that question either way.
    in_rth = rep.get("in_rth", True)
    crit = [s for s in rep["streams"]
            if s["critical"] and s["bulb"] != NA
            and not s.get("after_hours") and _in_window(s, in_rth)]
    cand = [c for c in rep["candles"]
            if not c.get("after_hours") and not c.get("foreign")
            and _in_window(c, in_rth)]
    # ⚠️ "no candles AT ALL" stays RED — that is a dead store, not a window
    # question — but an empty IN-WINDOW set outside RTH is normal.
    if not [c for c in rep["candles"] if not c.get("foreign")]:
        return RED
    if any(s["bulb"] == RED for s in crit):
        return RED
    if any(c["bulb"] == RED for c in cand):
        return RED
    if any(s["bulb"] == AMBER for s in crit) or any(c["bulb"] == AMBER for c in cand):
        return AMBER
    return GREEN


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--bulb", action="store_true",
                    help="one line for status.py")
    ap.add_argument("--symbol", default=os.environ.get("OT_INSTRUMENT", ""),
                    help="instrument, for per-instrument applicability "
                         "(a cash index has no time-and-sale)")
    ap.add_argument("--feed-db",
                    default=os.path.expanduser("~/options-trader/data/feed_store.db"))
    ap.add_argument("--derived-db",
                    default=os.environ.get(
                        "OT_DERIVED_DB",
                        os.path.expanduser("~/options-trader/data/derived_store.db")))
    a = ap.parse_args()

    in_rth = _rth_now()
    _is_index = None                 # v4.4: no --symbol and no env -> collect() asks the box
    if a.symbol:
        try:
            from config import is_cash_index
            _is_index = is_cash_index(a.symbol)
        except Exception:                                       # noqa: BLE001
            _is_index = False
    rep = collect(a.feed_db, a.derived_db, in_rth, _is_index)
    r = rollup(rep)

    if a.bulb:
        bad = [s["label"] for s in rep.get("streams", [])
               if s["critical"] and s["bulb"] in (RED, AMBER)]
        bad += [c["label"] for c in rep.get("candles", [])
                if not c.get("foreign") and c["bulb"] in (RED, AMBER)]
        # ⚠️ NEVER PRINT A DANGLING ARROW. When the store is missing entirely
        # there are no per-stream labels to name, and "DOWN  ← " reads like a
        # truncated message rather than a diagnosis.
        if rep.get("fatal"):
            bad = ["no feed store"]
        note = ("  ← " + ", ".join(bad[:4])) if (r != GREEN and bad) else ""
        print(f"{r} Manifold:    {'GREEN' if r == GREEN else ('DEGRADED' if r == AMBER else 'DOWN')}{note}")
        return 0 if r == GREEN else 1

    if a.json:
        print(json.dumps({"rollup": r, **rep}, indent=2))
        return 0 if r == GREEN else 1

    print("=" * 62)
    print(f"  MANIFOLD HEALTH   {r}   " +
          ("RTH" if in_rth else "outside RTH — idle streams are ⚪, not faults"))
    print("=" * 62)
    if rep.get("fatal"):
        print(f"  {RED} {rep['fatal']}")
        return 1

    print("  RAW STREAMS")
    for s in rep["streams"]:
        if s.get("after_hours"):
            continue
        age = "—" if s["age_s"] is None else f"{s['age_s']}s"
        star = "*" if s["critical"] else " "
        note = "  n/a — cash index has no tape" if s["bulb"] == NA else ""
        _rows = f"{s['rows']}+" if s.get("capped") else str(s["rows"])
        print(f"   {s['bulb']}{star} {s['label']:<22} rows={_rows:<9} age={age}{note}")

    print("\n  CANDLES")
    for c in sorted(rep["candles"], key=lambda x: x["label"]):
        if c.get("after_hours") or c.get("foreign"):
            continue
        print(f"   {c['bulb']}  {c['label']:<22} rows={c['rows']:<8} age={c['age_s']}s")

    # 🔴 AFTER-HOURS — JUDGED OUTSIDE RTH, IDLE DURING IT. These rows are not
    # second-class: outside the session they are the ONLY live ones, and they
    # drive the rollup then. Splitting them out is what lets the RTH board
    # reach GREEN instead of sitting permanently DEGRADED on rows that are
    # behaving exactly as designed.
    ah_s = [s for s in rep["streams"] if s.get("after_hours")]
    ah_c = [c for c in rep["candles"] if c.get("after_hours") and not c.get("foreign")]
    if ah_s or ah_c:
        print("\n  AFTER-HOURS  " +
              ("(idle now — judged outside RTH)" if rep["in_rth"]
               else "(LIVE now — these drive the rollup outside RTH)"))
        for s in ah_s:
            age = "—" if s["age_s"] is None else f"{s['age_s']}s"
            print(f"   {s['bulb']}  {s['label']:<22} rows={s['rows']:<8} age={age}")
        for c in sorted(ah_c, key=lambda x: x["label"]):
            print(f"   {c['bulb']}  {c['label']:<22} rows={c['rows']:<8} age={c['age_s']}s")

    # v4.4 - SHOWN, NOT HIDDEN, NOT JUDGED: rows this box's feed no longer writes.
    fc_ = [c for c in rep["candles"] if c.get("foreign")]
    if fc_:
        print("\n  FOREIGN  (not this box's instrument - leftovers, never judged)")
        for c in sorted(fc_, key=lambda x: x["label"]):
            print(f"   {c['bulb']}  {c['label']:<22} rows={c['rows']:<8} age={c['age_s']}s")

    if rep["derived"]:
        print("\n  DERIVED  (contributors — never gate trading)")
        for d in rep["derived"]:
            age = "—" if d["age_s"] is None else f"{d['age_s']}s"
            print(f"   {d['bulb']}  {d['label']:<22} rows={d['rows']:<8} age={age}")
    # 🔴 THE ENGINE'S OWN ACCOUNT, NEXT TO THE ROW COUNT. On 2026-08-24 two
    # engines showed rows=0 with no error anywhere, and the row count alone
    # could not distinguish "never ran", "ran and wrote nothing", and "ran and
    # failed". Those are three different faults with three different fixes.
    # ⚠️ ABSENT IS SAID OUT LOUD. An engine missing from the table has never
    # completed a single pass since the last restart, which is itself a finding
    # — and printing nothing for it would hide exactly that.
    st = rep.get("engines")
    if st:
        print("\n  ENGINES  (each engine's own account of itself)")
        for e in st:
            err = e.get("last_error") or ""
            print(f"   {e['name']:<14} runs={e['runs']:<6} fail={e['failures']:<4}"
                  f" last_rows={e['last_rows']:<5}"
                  + (f"  ERR {err[:40]}" if err else ""))
    elif st is not None:
        print("\n  ENGINES  no engine has completed a pass since restart")

    print("=" * 62)
    print(f"  ROLLUP: {r}   (* = trading depends on it)")
    if any(x["bulb"] == NA for x in rep["streams"]):
        print(f"  {NA} = not applicable to this instrument — still SUBSCRIBED "
              f"and stored, simply cannot arrive")
    if any(x["bulb"] == RED and not x["critical"] for x in rep["streams"]):
        print(f"  {RED} on a non-* row = no rows yet. CAUSE UNESTABLISHED — "
              f"entitlement or feed. Check: grep -c 'subscribed .* Underlying' "
              f"bot.log")
    return 0 if r == GREEN else 1


if __name__ == "__main__":
    sys.exit(main())
