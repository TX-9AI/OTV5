#!/usr/bin/env python3
"""
tests/exit_replay.py  v1.6
v1.6  2026-09-19  OTV4TEST r64 — r62'S ORIENTATION REWIRE INVERTED EVERY CREDIT
      VERTICAL. The multi-leg signs already encode favourable orientation
      (`short -1 / long +1` makes the combo `-(spread)`, which rises as the
      seller wins), so applying a credit flip on top inverted it: measured,
      pnl_usd -56.0 against a replayed +28.0 on the one credit row in the book.
      The flip is now scoped to the single-leg `option_symbol` path, where it is
      correct and — because `is_valid` fails closed on a naked short —
      unreachable. Kept guarded rather than deleted.
v1.5  2026-09-19  OTV4TEST r63 — THREE REPAIRS TO r62'S OWN REPAIR. (1) The stop
      regex had no word boundary, so `tcs_stop_15%_of_credit` and
      `trail_stop_10%` both read as premium stops (measured). (2) The reconcile
      band multiplied the tolerance BY the derived stop, so r62 made the check
      LOOSER on wider stops — 56% of entry cost at a butterfly's 40% — which is
      backwards; it is keyed on entry cost alone now, and 0.35 is recorded as
      an UNFITTED prior rather than a measurement. (3) A control that applied to
      ZERO rows passed silently; it now shouts and marks the hypotheticals
      UNVERIFIED, and the applied count is reported on every run.
v1.4  2026-09-19  OTV4TEST r62 — THE TOOL REPLAYED NOTHING AND BLAMED THE TAPE.
      Five defects in one file, four of them masking each other. (1) sys.path
      carried tests/ and not the repo root, so any repo import silently failed —
      harmless until this revision needed one. (2) `legs_of` never read
      `option_symbol`, refusing 25 of 44 banked rows as "no leg symbols".
      (3) it queried `streamer_symbol=?` with an OCC string, matching 0 of 24
      traded contracts where 19 have quotes under the transform. (4) the
      butterfly CENTRE leg was weighted -1 against a position of -2. (5) the
      closing verdict blamed the tape and named a masked service as the remedy.
      Plus: orientation derived via `is_credit_vertical` instead of the
      writer-less `is_short_position`, and a selftest built from real formats
      on both sides instead of one invented string it handed to itself.
v1.3  2026-09-07  r299 - relaxed rows kept (operator ruling: it is all paper, and paper vs live is the split that matters).
v1.2  2026-09-07  r297 - --all-history added: `_r_tool` is shared and now passes it. The default
window also moves from TODAY to DAY ONE ONWARD via warehouse_source.
v1.1  2026-08-23  S3 DEFAULT SOURCE: trades from raw/trades, quote paths from
the raw/quote_series batches (push_series, r86) — loaded once per run and
indexed per streamer symbol, so control replays without touching a box.
--db/--feed remain the explicit local escape hatch. SOURCE lines always
printed; the positive control and the named-refusal machinery are unchanged.
v1.0  2026-08-23
REPLAY EVERY CLOSED TRADE'S REAL PREMIUM PATH — rebuilt from `quote_series` —
under alternative exit ladders. The manifold's first paying consumer.

v1.0  2026-08-23  Built for the R-factor project. stop_sweep.py works on two
extremes per trade; this works on the WHOLE PATH, so trail parameters (arm
level, giveback width) become measurable instead of argued. This is exactly
the data FEED_MANIFOLD.md said was being destroyed when chain_marks was
last-write-wins — kept per tick since r61, consumed here for the first time.

HOW A PATH IS BUILT
  · Legs come from the row's own symbol columns (short/long/lower/center/
    upper). Sign: shorts −, longs +, orientation flipped for
    is_short_position so a RISING path is always FAVOURABLE. Single-leg
    debit rows carry no leg columns and fall back to `symbol`-prefix
    matching in quote_series only when it resolves to EXACTLY ONE contract;
    ambiguity is refused, never guessed.
  · Each leg's mid = (bid+ask)/2, forward-filled onto the union clock.
    Marks outside (0, 1e6) are dropped at ingest — finite is not sane.
  · ⚠️ COVERAGE IS A GATE. Expected points = trade lifetime / 15s. Below
    50% the trade is refused BY NAME with its drop reason (r39: a tool-caused
    absence must not wear the costume of a null). Refusals are summarised;
    a report with silent drops is the defect class this repo keeps finding.

RULES REPLAYED (premium-fraction space, per side convention as live):
  stop only · stop+TP · trail(arm A, give G): once favourable ≥ A, exit when
  path falls G below its running peak. The RECORDED exit is replayed too and
  must reconcile with pnl_usd within tolerance — a path that cannot
  reproduce what actually happened is not trusted to score hypotheticals
  (positive control, DRF.1's lesson).

Run:  python3 tests/exit_replay.py [--db trades.db] [--feed feed_store.db]
      python3 tests/exit_replay.py --selftest
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

# 🔴 r62 — THE REPO ROOT, NOT JUST tests/. This inserted ONLY the directory the
# file lives in, so every `from <repo package> import ...` raised ImportError.
# Nothing noticed because the one repo import here (`warehouse_source`) is a
# SIBLING in tests/ and the wrong path satisfies it. Surfaced by the mainline
# control agent, who hit it rewiring this exact orientation flip and had a
# fail-closed try/except silently swallow it — the rewire compiled, passed
# review, produced a clean report and did nothing.
# ⚠️ MEASURED HERE, AND THE MASK IS AN ENVIRONMENT VARIABLE: this box's
# interactive shell exports PYTHONPATH=<repo>, so the import resolves for a
# human and for the R-suite menu; with `env -u PYTHONPATH` the SAME command
# raises `ModuleNotFoundError: No module named 'database'`. PYTHONPATH is in
# NEITHER systemd unit, so the file behaves one way by hand and another way
# anywhere the environment is clean.
# ⚠️ tests/ STAYS ON THE PATH — `r_ledger` and `warehouse_source` are siblings.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)          # sibling tools: r_ledger, warehouse_source
sys.path.insert(0, _ROOT)          # repo packages: strategy, database, ...
from r_ledger import _f, DEFAULT_DB  # noqa: E402

# 🔴 r62 — THE ORIENTATION RESOLVER, AND ITS FALLBACK IS LOUD BY CONSTRUCTION.
# `is_short_position` is a column with NO WRITER (MEAS.2, r31) — measured 0 of
# 44 rows set — so the flip below was dead code and every CREDIT position was
# being given the LONG sign, reading its wins as losses. `is_credit_vertical`
# DERIVES from `strategy`/`setup_type`, real columns present on every row
# (WORKING_AGREEMENT §22: prefer deriving, it works on rows that already exist).
# ⚠️ A QUIET `except` HERE WOULD REBUILD THE EXACT DEFECT THIS REVISION FIXES,
# so the fallback COUNTS itself, says so by name, and FAILS THE SELFTEST.
# "resolver unavailable" must never again read as "resolver fine".
RESOLVER_FALLBACKS = 0
try:
    from strategy.structure import is_credit_vertical as _resolve_credit  # noqa: E402
    RESOLVER = "strategy.structure.is_credit_vertical"
    RESOLVER_ERR = ""
except Exception as _exc:                                       # noqa: BLE001
    RESOLVER = ""
    RESOLVER_ERR = f"{type(_exc).__name__}: {_exc}"

    def _resolve_credit(row):
        global RESOLVER_FALLBACKS
        RESOLVER_FALLBACKS += 1
        return bool(row.get("is_short_position"))


def _is_credit(row):
    """True when the position is a CREDIT structure, so its combo value falls
    when the trade wins and the path must be inverted to read as favourable."""
    try:
        return bool(_resolve_credit(row))
    except Exception:                                           # noqa: BLE001
        global RESOLVER_FALLBACKS
        RESOLVER_FALLBACKS += 1
        return bool(row.get("is_short_position"))


# 🔴 r62 — OCC -> DXFEED STREAMER. The trade columns hold OCC
# (`QQQ   260911C00718000`); `quote_series` is keyed on streamer
# (`.QQQ260911C718`). This file queried `WHERE streamer_symbol=?` with the OCC
# string, so it matched NOTHING: measured, 19 of 24 traded contracts have
# quotes under the transformed key (up to 44,771 rows on one) and 0 of 24 under
# the key it was using.
# ⚠️ THE ROOT MAY CARRY DIGITS — `GOOGL1`, `TSLA1`: OCC's convention for a
# contract adjusted by a split or special dividend. `[A-Z]+` refuses those and,
# by this file's own rule, refuses the whole trade. Found by the control agent.
_OCC_RE = re.compile(r"^([A-Z][A-Z0-9]*)\s*(\d{6})([CP])(\d{8})$")


def streamer_symbol(occ):
    """`QQQ   260911C00718000` -> `.QQQ260911C718`. None when unparseable."""
    m = _OCC_RE.match(str(occ or "").strip())
    if not m:
        return None
    root, exp, cp, strike = m.groups()
    k = ("%f" % (int(strike) / 1000.0)).rstrip("0").rstrip(".")
    return f".{root}{exp}{cp}{k}"

DEFAULT_FEED = os.path.join(os.path.expanduser("~"), "options-trader", "data",
                            "feed_store.db")
POLL_S = 15.0
MIN_COVERAGE = 0.50
# 🔴 r63 — THE BAND IS KEYED ON ENTRY COST ALONE. r62 derived `rec_stop` per
# row, which was right for the RULE and wrong for the BAND: the old expression
# multiplied the tolerance BY the stop, and the `0.25 * 4` cancelled only at
# 0.25. So deriving the stop silently made the check LOOSER on wider stops —
# 28% of cost at a 20% stop, 35% at 25%, and 56% at a butterfly's 40%. A wider
# stop meaning a looser check is backwards: the band must not move with the
# thing it is testing. Found by the mainline control agent in its own tree and
# reported here before we had noticed it.
# ⚠️ 0.35 IS AN INHERITED PRIOR AND IT IS NOT FITTED. §31 governs: it has never
# been tested against outcomes. Measured on this book 2026-09-19, the ELIGIBLE
# set is n=2 and its deviations are 1.5% and 2.1% of entry cost against a band
# of 35% and 56% — roughly 20x looser than anything observed. That is a
# MECHANISM and not a threshold (§12): two observations cannot set a tolerance,
# so the VALUE is left alone and only its SHAPE is corrected here. Tightening
# it needs a deviation distribution this book cannot yet supply.
RECONCILE_TOL = 0.35        # fraction of ENTRY COST, not of risk

TRAILS = [(0.25, 0.10), (0.25, 0.15), (0.50, 0.15), (0.50, 0.25), (0.75, 0.25)]
STOPS = [0.15, 0.25]


def _ts(v):
    try:
        return datetime.fromisoformat(str(v)).timestamp()
    except Exception:                                           # noqa: BLE001
        return None


def legs_of(row: dict):
    """[(streamer_symbol, weight in FAVOURABLE orientation)] or (None, reason).

    🔴 r62 — THE CONTRACT SAYS *streamer* AND IT NOW RETURNS streamer. It always
    said so; it returned whatever the column held, which is OCC. The transform
    lives HERE, at the one place legs are built, so `wanted`, the S3 index and
    both fetch providers needed no change and cannot drift from it.

    ⚠️ THE `option_symbol` FALLBACK IS NEW AND IS NOT THE ONE THE OLD DOCSTRING
    DESCRIBED. That paragraph claimed a `symbol`-PREFIX match "only when it
    resolves to EXACTLY ONE contract; ambiguity is refused" — **no such fallback
    has ever existed in this function**, and it must not be built: r36
    subscribed the UNDERLYING's quotes, so `quote_series` now holds a row keyed
    exactly `QQQ`, and a prefix match would resolve to it and replay the
    UNDERLYING'S PRICE PATH as a premium path — plausible numbers, wrong
    instrument, no error. `option_symbol` is the exact contract the trade
    recorded; there is nothing to disambiguate.

    ⚠️ A BUTTERFLY IS 1/2/1. The centre was weighted -1 while
    `entry_engine.py:801` builds `(center_contract, 2, -1)` and its own comment
    says *"the debit is lower + upper - 2*center"*. Every replayed butterfly
    path was too high by one centre leg. It could never have shown before,
    because with the symbols wrong no butterfly ever resolved a quote —
    FIXING THE OUTER DEFECT IS WHAT MADE THE INNER ONE REACHABLE.
    """
    short = -1
    long_ = +1
    legs = []
    for col, sign in (("short_symbol", short), ("long_symbol", long_),
                      ("lower_symbol", long_), ("upper_symbol", long_),
                      ("center_symbol", short * 2)):          # r62 — 1/2/1
        s = row.get(col)
        if s:
            legs.append((str(s), sign))
    single_leg = False
    if not legs:
        # r62 — a single-leg debit records its contract in `option_symbol`, a
        # column this function never read: 25 of 44 banked rows carry it and
        # every one was refused as "no leg symbols on row".
        one = row.get("option_symbol")
        if one:
            legs.append((str(one), long_))
            single_leg = True
    if not legs:
        return None, "no leg symbols on row"
    out = []
    for raw, sign in legs:
        sym = streamer_symbol(raw)
        if sym is None:
            # refuse the WHOLE trade, by name. Half a spread is a different
            # position, not a partial answer.
            return None, f"unparseable contract symbol {raw!r}"
        out.append((sym, sign))
    # 🔴 r64 — THE FLIP APPLIES ONLY TO THE SINGLE-LEG PATH, AND r62 GOT THIS
    # BACKWARDS. The multi-leg signs ALREADY encode favourable orientation:
    #   credit vertical  short -1 / long +1 -> combo = -(spread value), which
    #                    RISES as the spread cheapens, i.e. as the seller wins
    #   butterfly        1 / -2 / 1         -> combo = the fly's own debit
    #   single-leg debit +1                 -> premium up is favourable
    # So r62's `flip = -1 if _is_credit(row)` INVERTED every credit vertical.
    # MEASURED on the one replayed credit row: pnl_usd -56.0 against a replayed
    # +28.0 — the book lost, the replay profited. The nine other replayed rows
    # were byte-identical either way.
    # ⚠️ AND IT WAS ACCIDENTALLY CORRECT BEFORE r62: `is_short_position` has no
    # writer (MEAS.2), so `flip` was +1 for every row the tool had ever seen —
    # which is exactly what the spread columns need. r62 replaced a dead flag
    # that was right by accident with a live resolver that was wrong on purpose.
    # Surfaced by the mainline control agent, which had the identical rewire
    # staged and unlanded; reproduced here before it was believed.
    # 🔑 ONLY A SINGLE-LEG CREDIT POSITION NEEDS THE FLIP — a naked short, whose
    # premium falls as it wins. `OptionsSignal.is_valid` FAILS CLOSED on a naked
    # short (no wing, or a wing inside the short), so nothing in this book can
    # reach it. The branch is kept GUARDED AND DEAD rather than deleted, so the
    # next reader does not have to re-derive why it is absent.
    # ⚠️ "UNREACHABLE TODAY" IS EXACTLY THE KIND OF STATEMENT THAT SILENTLY
    # STOPS BEING TRUE — if a naked short ever becomes writable, this fires.
    flip = -1 if (single_leg and _is_credit(row)) else 1
    return [(s, sign * flip) for s, sign in out], ""


def path_for(fetch, legs, t0, t1):
    """Combined signed-mid path on the union clock, forward-filled per leg.

    v1.1 — `fetch(sym, t0, t1)` -> [(ts_epoch, bid, ask)] abstracts the
    source: sqlite locally, the indexed S3 quote batches on control. One path
    builder, two providers, so the two sources cannot drift apart.
    """
    series = {}
    for sym, _sign in legs:
        rows = fetch(sym, t0 - 60, t1 + 60)
        pts = []
        for ts, b, a in rows:
            b, a = _f(b), _f(a)
            if b and a and 0 < b < 1e6 and 0 < a < 1e6 and a >= b:
                pts.append((ts, (b + a) / 2.0))
        if not pts:
            return None, f"no usable quotes for {sym}"
        series[sym] = pts
    clock = sorted({ts for pts in series.values() for ts, _ in pts if t0 <= ts <= t1})
    if not clock:
        return None, "no timestamps inside the trade window"
    idx = {s: 0 for s in series}
    last = {s: None for s in series}
    out = []
    for t in clock:
        val = 0.0
        ok = True
        for (sym, sign) in legs:
            pts = series[sym]
            i = idx[sym]
            while i < len(pts) and pts[i][0] <= t:
                last[sym] = pts[i][1]
                i += 1
            idx[sym] = i
            if last[sym] is None:
                ok = False
                break
            val += sign * last[sym]
        if ok:
            out.append((t, val))
    return out, ""


def replay(path, entry_val, risk, rule):
    """pnl in combo-value points for one rule. rule = ('stop',s) | ('tp',s,t)
    | ('trail',s,arm,give). Favourable = value UP (legs_of already oriented)."""
    kind = rule[0]
    stop = rule[1]
    peak = entry_val
    armed = False
    for _t, v in path:
        move = v - entry_val
        peak = max(peak, v)
        if move <= -stop * risk:
            return -stop * risk
        if kind == "tp" and move >= rule[2] * risk:
            return rule[2] * risk
        if kind == "trail":
            if not armed and move >= rule[2] * risk:
                armed = True
            if armed and (peak - v) >= rule[3] * risk:
                return v - entry_val
    return path[-1][1] - entry_val if path else 0.0


def _sqlite_fetch(fcon):
    def fetch(sym, lo, hi):
        return fcon.execute(
            "SELECT ts_epoch, bid_price, ask_price FROM quote_series"
            " WHERE streamer_symbol=? AND ts_epoch BETWEEN ? AND ?"
            " ORDER BY ts_epoch", (sym, lo, hi)).fetchall()
    return fetch


def _s3_fetch(qrows):
    from collections import defaultdict as _dd
    idx = _dd(list)
    for r in qrows:
        idx[r.get("streamer_symbol")].append(
            (r.get("ts_epoch") or 0, r.get("bid_price"), r.get("ask_price")))
    for v in idx.values():
        v.sort()

    def fetch(sym, lo, hi):
        return [p for p in idx.get(sym, ()) if lo <= p[0] <= hi]
    return fetch


# 🔴 r62 — THE POSITIVE CONTROL WAS MODELLING THE WRONG EXIT RULE.
# It replayed EVERY trade under a hardcoded 25% premium stop and compared the
# result to `pnl_usd`. Most of this book did not exit on a premium stop at all:
# measured, the vocabulary is `hard_stop_NN%` / `stop_NN%` / `premium_stop_NN%`
# (real premium stops), against `orb_trail_stop`, `hard_close_15:45_ET`,
# `sweep_breach_accepted`, `runaway_thesis_dead`, `runaway_fizzle`, `handoff`
# and `orb_structure_stop` (which are not).
# ⚠️ IT SURFACED AS A FALSE ALARM ON A WINNER: a GEXPinButterfly that held to
# `hard_close_15:45_ET` for +$1,630 was replayed under a 25% stop, exited at
# -$130, and the control reported the TOOL as suspect. A butterfly has no
# target and holds to 15:45 behind a 40% floor — the control was asserting a
# rule the trade never ran under. §20: a canary that fires on correct code is
# the one that gets loosened and then misses the real thing.
# ⚠️ AND THE OBVIOUS REGEX IS A TRAP — `(\d+)%` matches the `pnl=-26.5%` tail
# and yields a 1%, 4% or 9% "stop". The percentage is only meaningful when it
# is bound to a STOP TOKEN.
# 🔑 NOT APPLICABLE IS NOT A PASS. A row whose recorded exit was never a
# premium stop is counted and named separately, never folded into either bucket.
# 🔴 r63 — THE WORD BOUNDARY IS THE LOAD-BEARING PART. r62 shipped this
# unanchored and SEARCHED, so the match walked straight through any prefix:
# measured, `tcs_stop_15%_of_credit` -> 0.15 and `trail_stop_10%` -> 0.10, both
# read as premium stops they are not. We emit neither string today, but
# `orb_trail_stop` already exists and a percentage on it is one line away.
# ⚠️ THE LOOKAHEAD IS A BACKSTOP, NOT THE FIX, and the distinction is measured
# rather than assumed: the mainline control agent deleted `(?!_of_)` from its
# own copy expecting red and got GREEN, because with `\b` the character before
# `stop` in `tcs_stop` is `_`, a word character, so the boundary alone rejects
# it. The lookahead only bites on a BARE `stop_15%_of_credit`. Kept, because it
# is free and the next emitter may not carry a prefix — but it is not what
# closes the hole here, and a reader should not think it is.
_STOP_RE = re.compile(r"\b(?:hard_stop|premium_stop|stop)_(\d{1,3})%(?!_of_)")


def recorded_stop_pct(row):
    """The premium stop this row ACTUALLY exited on, or None when its recorded
    exit was not a premium stop and a stop-replay therefore cannot reconcile."""
    m = _STOP_RE.search(str(row.get("exit_reason") or ""))
    if not m:
        return None
    pct = int(m.group(1)) / 100.0
    return pct if 0.0 < pct < 1.0 else None


def run(rows, fetch) -> int:
    refused = defaultdict(int)
    recon_na = defaultdict(int)
    recon_applied = 0
    totals = defaultdict(lambda: defaultdict(float))
    counts = defaultdict(int)
    recon_fail = 0
    for r in rows:
        t0, t1 = _ts(r.get("entry_time")), _ts(r.get("exit_time"))
        if not t0 or not t1 or t1 <= t0:
            refused["bad timestamps"] += 1
            continue
        legs, why = legs_of(r)
        if legs is None:
            refused[why] += 1
            continue
        path, why = path_for(fetch, legs, t0, t1)
        if not path:
            refused[why or "empty path"] += 1
            continue
        cov = len(path) / max(1.0, (t1 - t0) / POLL_S)
        if cov < MIN_COVERAGE:
            refused[f"coverage<{MIN_COVERAGE:.0%}"] += 1
            continue
        entry_val = path[0][1]
        entry_prem = _f(r.get("entry_premium")) or abs(entry_val) or 1.0
        lot = 100.0 * (_f(r.get("contracts")) or 1)
        # positive control: replay the stop this row ACTUALLY exited on and
        # require it to land near pnl_usd. r62 — derived per row, not 0.25 for
        # everything; a row that did not exit on a premium stop is NOT tested.
        rec_stop = recorded_stop_pct(r)
        pnl = _f(r.get("pnl_usd")) or 0.0
        if rec_stop is None:
            why_na = str(r.get("exit_reason") or "?").split(":")[0].split(" ")[0]
            recon_na[why_na or "?"] += 1
        else:
            rec = replay(path, entry_val, entry_prem, ("stop", rec_stop)) * lot
            recon_applied += 1
            if abs(rec - pnl) > max(50.0, RECONCILE_TOL * entry_prem * lot):
                recon_fail += 1
        key = (r.get("strategy") or "?", (r.get("option_side") or "?").lower())
        counts[key] += 1
        totals[key]["recorded"] += pnl
        for s in STOPS:
            totals[key][f"stop {s:.2f}"] += replay(path, entry_val, entry_prem,
                                                   ("stop", s)) * lot
        for arm, give in TRAILS:
            totals[key][f"trail a{arm:.2f}/g{give:.2f}"] += replay(
                path, entry_val, entry_prem, ("trail", 1.0, arm, give)) * lot
    print("=" * 70)
    print("  EXIT REPLAY — real premium paths from quote_series, dollars")
    print("=" * 70)
    for key in sorted(counts):
        print(f"\n  {key[0]} · {key[1]}   n={counts[key]} replayed")
        for rule, net in sorted(totals[key].items(), key=lambda kv: -kv[1]):
            mark = "  <- recorded" if rule == "recorded" else ""
            print(f"    {rule:<22} ${net:>10,.0f}{mark}")
    if refused:
        print("\n  REFUSED (named, per r39 — these are the tool's gaps, not the tape's):")
        for why, n in sorted(refused.items(), key=lambda kv: -kv[1]):
            print(f"    {why:<40} {n}")
    if recon_na:
        tot = sum(recon_na.values())
        print(f"\n  positive control NOT APPLICABLE to {tot} replayed trade(s) — "
              f"their recorded exit was not a premium stop, so a stop-replay "
              f"cannot reconcile. NOT a pass and NOT a failure:")
        for why, n in sorted(recon_na.items(), key=lambda kv: -kv[1]):
            print(f"    {why:<40} {n}")
    # 🔴 r63 — "0 did not reconcile" OUT OF 0 APPLIED IS THE MOST CONVINCING
    # POSSIBLE ZERO AND MEANS NOTHING AT ALL. A silent pass here would certify
    # every hypothetical above on the strength of a check that never ran.
    if counts and not recon_applied:
        print("\n  🔴 POSITIVE CONTROL APPLIED TO NOTHING — not one replayed "
              "trade exited on a premium stop, so the control did not run at "
              "all. EVERY HYPOTHETICAL ABOVE IS UNVERIFIED.")
    elif recon_applied:
        print(f"\n  positive control applied to {recon_applied} of "
              f"{sum(counts.values())} replayed trade(s).")
    if recon_fail:
        print(f"\n  ⚠️ POSITIVE CONTROL: {recon_fail} trade(s) whose replayed "
              f"recorded-rule pnl did not reconcile with pnl_usd — treat every "
              f"hypothetical above as suspect until this is zero or explained.")
    if RESOLVER_FALLBACKS or not RESOLVER:
        print(f"\n  ⚠️ ORIENTATION RESOLVER UNAVAILABLE — {RESOLVER_FALLBACKS} "
              f"fallback(s) to the writer-less `is_short_position` flag. "
              f"Every CREDIT path above is INVERTED. ({RESOLVER_ERR})")
    if not counts and not refused:
        # 🔴 r62 — GATED ON `not refused`, AND THE s3_push CLAUSE IS DELETED.
        # `not counts` is true exactly when nothing replayed, which is exactly
        # when `refused` is populated — so this fired four lines below a block
        # headed "these are the tool's gaps, not the tape's" and blamed the
        # tape anyway, as the LAST thing printed. It also sent the reader to
        # audit `s3_push`, which on THIS box is MASKED BY RULING (r21/BOX.1)
        # and must never run: a remedy that is unreachable by design is a trap,
        # not a remedy. A verdict that can only be true when the tape is absent
        # is now gated on the tape being absent.
        print("\n  nothing replayable yet — quote_series holds no quotes for "
              "any traded contract in this window.")
    return 0


def run_s3(a) -> int:
    import warehouse_source as ws
    dates = ws.dates_of(a)
    trades, m1 = ws.load_trades(dates)
    print("  " + m1.banner())
    if m1.error:
        return 1
    rows = [t for t in trades if (t.get("status") or "").lower() == "closed"
]
    # ⚠️ ONE LIST CALL, NOT ONE PER TRADE. The quote batches for the window
    # are loaded once and indexed per symbol; per-trade fetches against S3
    # would be the expensive path the handoff warns this tool already is.
    qrows, m2 = ws.load_series("quote_series", dates)
    print("  " + m2.banner())
    if m2.error:
        return 1
    return run(rows, _s3_fetch(qrows))


_OCC = "QQQ   260823C00100000"       # r62 — real OCC, as a trade records it
_ST = ".QQQ260823C100"               # r62 — real streamer, as quote_series keys


def selftest() -> int:
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE quote_series (streamer_symbol TEXT, ts_epoch REAL,"
                " bid_price REAL, ask_price REAL)")
    # A long call: mid runs 1.00 -> 2.00 by t=300 then back to 1.20 at t=600
    for i in range(41):
        t = i * 15.0
        mid = 1.0 + (t / 300.0) if t <= 300 else 2.0 - 0.8 * ((t - 300) / 300.0)
        con.execute("INSERT INTO quote_series VALUES (?,?,?,?)",
                    (_ST, 1000 + t, mid - 0.02, mid + 0.02))
    legs = [(_ST, +1)]
    path, why = path_for(_sqlite_fetch(con), legs, 1000, 1600)
    ok = bool(path) and not why and len(path) == 41
    r_hold = replay(path, path[0][1], 1.0, ("stop", 0.25))
    ok &= abs(r_hold - 0.20) < 0.03           # rode up, gave back to +0.20
    r_trail = replay(path, path[0][1], 1.0, ("trail", 1.0, 0.25, 0.15))
    ok &= 0.80 < r_trail < 0.92               # trail keeps ~+0.85 of the +1.00 peak
    r_tp = replay(path, path[0][1], 1.0, ("tp", 0.25, 0.50))
    ok &= abs(r_tp - 0.50) < 1e-9
    # v1.1 — the S3 provider must build the IDENTICAL path from the same data
    qrows = [{"streamer_symbol": _ST, "ts_epoch": t, "bid_price": b,
              "ask_price": a2} for t, b, a2 in con.execute(
                  "SELECT ts_epoch, bid_price, ask_price FROM quote_series")]
    path2, _w = path_for(_s3_fetch(qrows), legs, 1000, 1600)
    ok &= path2 == path
    # deliberate failures: coverage refusal + ambiguity refusal
    sparse, _ = path_for(_sqlite_fetch(con), legs, 0, 20000)
    cov = len(sparse or []) / ((20000 - 0) / POLL_S)
    ok &= cov < MIN_COVERAGE
    lg, why2 = legs_of({})
    ok &= lg is None and "no leg symbols" in why2

    # ── r62 — THE FIXTURE IS BUILT FROM THE REAL FORMATS, BOTH SIDES ────────
    # The old one wrote "X 260823C100" into quote_series AND handed the same
    # invented string to legs_of, so it matched itself and could never fail —
    # §0.4, a fixture built from the assistant's own belief. Every assertion
    # below crosses the OCC/streamer boundary the tool actually crosses.
    ok &= streamer_symbol(_OCC) == _ST                       # the transform
    ok &= streamer_symbol("SPXW  260918P07585000") == ".SPXW260918P7585"
    ok &= streamer_symbol("CRM   260918C00182500") == ".CRM260918C182.5"
    ok &= streamer_symbol("GOOGL1260918C00150000") == ".GOOGL1260918C150"
    ok &= streamer_symbol("not a contract") is None
    # a single-leg debit resolves THROUGH option_symbol and comes back streamer
    lg1, w1 = legs_of({"strategy": "ORBStrategy", "option_symbol": _OCC})
    ok &= (not w1) and lg1 == [(_ST, +1)]
    # a butterfly is 1/2/1, not 1/1/1
    lgb, wb = legs_of({"strategy": "GEXPinButterfly",
                       "lower_symbol": "QQQ   260918C00718000",
                       "center_symbol": "QQQ   260918C00720000",
                       "upper_symbol": "QQQ   260918C00722000"})
    ok &= (not wb) and sorted(sg for _sy, sg in lgb) == [-2, 1, 1]
    # a CREDIT structure inverts; a debit does not — derived, not flag-read
    lgc, _wc = legs_of({"strategy": "SweepCreditSpread",
                        "setup_type": "sweep_credit_short",
                        "short_symbol": "QQQ   260918C00718000",
                        "long_symbol": "QQQ   260918C00720000"})
    lgd, _wd = legs_of({"strategy": "ORBStrategy", "option_symbol": _OCC})
    ok &= lgc is not None and lgd == [(_ST, +1)]
    # ⚠️ COMPARE PER SYMBOL, NOT THE SIGN MULTISET. My first cut asserted the
    # SORTED signs differed — and flipping both legs of a symmetric spread
    # yields the IDENTICAL multiset, so the assertion failed on correct code.
    # A test that cannot distinguish the thing it is testing is worse than none.
    lgo, _wo = legs_of({"strategy": "ORBStrategy",
                        "short_symbol": "QQQ   260918C00718000",
                        "long_symbol": "QQQ   260918C00720000"})
    # 🔴 r64 — THIS ASSERTION ENCODED r62'S DEFECT AS A REQUIREMENT. It read
    # `dict(lgc) != dict(lgo)` — a credit vertical and a debit vertical with the
    # SAME legs must differ — which is only true while the credit flip is being
    # wrongly applied on top of signs that already encode orientation. Rewritten
    # to the contract that replaced it rather than loosened (the r33 precedent):
    # they are IDENTICAL, and the short leg is NEGATIVE in both.
    ok &= dict(lgc) == dict(lgo)
    ok &= dict(lgc).get(".QQQ260918C718") == -1     # short leg, per symbol
    ok &= dict(lgc).get(".QQQ260918C720") == +1     # long leg, per symbol
    # an unparseable leg refuses the WHOLE trade, by name
    lgx, whx = legs_of({"strategy": "ORBStrategy", "option_symbol": "GARBAGE"})
    ok &= lgx is None and "unparseable" in whx
    # 🔴 THE RESOLVER MUST BE PRESENT. A quiet fallback here would rebuild the
    # exact defect r62 fixes, so "unavailable" is a FAILING selftest and not a
    # warning nobody reads.
    resolver_ok = bool(RESOLVER) and RESOLVER_FALLBACKS == 0
    ok &= resolver_ok
    print("exit_replay selftest:", "ALL PASS" if ok else
          f"FAIL hold={r_hold} trail={r_trail} tp={r_tp} cov={cov:.2f} "
          f"resolver={RESOLVER or 'UNAVAILABLE: ' + RESOLVER_ERR} "
          f"fallbacks={RESOLVER_FALLBACKS}")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None, help="LOCAL escape hatch")
    ap.add_argument("--feed", default=None, help="LOCAL escape hatch")
    ap.add_argument("--date")
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to", dest="to")
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
    if a.db or a.feed:
        db, feed = a.db or DEFAULT_DB, a.feed or DEFAULT_FEED
        for pth, name in ((db, "trades db"), (feed, "feed store")):
            if not os.path.exists(pth):
                print(f"  SOURCE: local {pth} — 🔴 {name} DOES NOT EXIST")
                return 1
        print(f"  SOURCE: local sqlite {db} + {feed}")
        tcon = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        tcon.row_factory = sqlite3.Row
        rows = [dict(r) for r in tcon.execute(
            "SELECT * FROM trades WHERE status='closed'"
            )]  # r299 — relaxed rows kept
        fcon = sqlite3.connect(f"file:{feed}?mode=ro", uri=True)
        return run(rows, _sqlite_fetch(fcon))
    return run_s3(a)


if __name__ == "__main__":
    sys.exit(main())
