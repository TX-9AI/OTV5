#!/usr/bin/env python3
"""
tests/check_r_ledger_width.py  v1.3
v1.3  2026-09-07  r299 - W9/W9b: relaxed rows survive the read, and the dead
flag is gone rather than left advertising a behaviour the code no longer has.
v1.2  2026-09-07  r298 - W8/W8b: a multi-date read narrates, a single-date one
stays quiet. Silent is indistinguishable from hung.
v1.1  2026-09-07  r297 — W6/W7 added: the ENTER default and the refusal of a
malformed date, both EXECUTED against `warehouse_source.dates_of`.
v1.0  2026-09-07  r296 — THE LAND GATE FOR THE 78-CHARACTER RULE.

🔴 WHY A CHECK AND NOT A CAREFUL EDIT. The first cut of r296 picked field
widths by hand and the rows still came out 80: `_fmt` returns a fixed SEVEN
characters and `{x:>5}` PADS WITHOUT TRUNCATING, so a field declared 5 wide
rendered 7. The bug was not the number chosen — it was that the row width
DEPENDED ON THE DATA, and a layout that holds only while the values stay small
breaks on the first big day, which is the day you most want to read it.

So this gate RENDERS the report and MEASURES every line (WA §21 — reading the
format string proves nothing about what it emits). W2 drives values wide
enough to overflow every column at once; a hand-checked layout passes W1 and
fails W2.

Run:  python3 tests/check_r_ledger_width.py
"""
from __future__ import annotations
import contextlib, io, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import r_ledger                                                  # noqa: E402

RULE = 78
F: list = []
def check(n, ok, d=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f"  — {d}" if d else ""))
    if not ok: F.append(n)

def _rows(mix):
    out = []
    for st, side, n, p in mix:
        for i in range(n):
            out.append(dict(pnl_usd=p if i % 2 else -abs(p) / 2, entry_premium=1.0,
                mfe_premium=2.0, mae_premium=0.6, contracts=1, is_short_position=0,
                strategy=st, option_side=side, status="closed",
                exit_reason="orb_structure_stop: 1m close 9"))
    return out

def widths(rows):
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        r_ledger.render(rows)
    return b.getvalue()

def main() -> int:
    print("\ncheck_r_ledger_width\n")
    ordinary = widths(_rows([("RunawayContinuation", "call", 12, 150.0),
                             ("GEXPinButterfly", "call", 2, -287.0),
                             ("ORBStrategy", "put", 10, -92.0)]))
    over = [(len(l), l) for l in ordinary.splitlines() if len(l) > RULE]
    check(f"W1  every line fits {RULE} on ordinary data", not over,
          f"max={max(len(l) for l in ordinary.splitlines())}"
          + (f"; worst: {over[0][1][:50]}" if over else ""))

    # W2 — THE ONE THAT MATTERS. Values wide enough to burst every column:
    # a six-figure average, a long strategy name, an extreme capture ratio.
    huge = widths(_rows([("RunawayContinuationHandoffXL", "call", 6, 987654.0),
                         ("SweepCreditSpread", "put", 6, 123456.0)]))
    over2 = [(len(l), l) for l in huge.splitlines() if len(l) > RULE]
    check(f"W2  still fits {RULE} when every value overflows its column",
          not over2,
          f"max={max(len(l) for l in huge.splitlines())}"
          + (f"; worst: {over2[0][1][:50]}" if over2 else ""))

    # W3 — the marker is gone from the OUTPUT, not from the source.
    check("W3  `THIN` no longer renders", "THIN" not in ordinary)

    # W4 — THE MARKER WENT, THE THRESHOLD STAYED. R must still be suppressed
    # on a bucket below MIN_N: that is a refusal to compute, not a label, and
    # an R off two trades is worse than no R at all.
    thin = widths(_rows([("GEXPinButterfly", "call", 2, 100.0)]))
    row = [l for l in thin.splitlines() if "GEXPinButterfly" in l][0]
    check("W4  MIN_N still suppresses R on a thin bucket",
          "\u2014" in row, row.strip()[:56])

    # W5 — _col truncates rather than merely padding. The actual defect.
    check("W5  _col TRUNCATES, it does not merely pad",
          r_ledger._col("+$1,234,567", 6) == "+$1,23"
          and r_ledger._col("2.0", 6) == "   2.0",
          f"{r_ledger._col('+$1,234,567', 6)!r}")

    # W6/W7 — r297. The date path, EXECUTED. A malformed value must RAISE,
    # not resolve to an empty window that the banner then calls real.
    import warehouse_source as ws  # noqa: E402  (used by W6-W8)
    class _A:
        def __init__(self, **k):
            self.date = k.get("date"); self.frm = k.get("frm")
            self.to = k.get("to"); self.all_history = k.get("all", False)
    d = ws.dates_of(_A())
    check("W6  ENTER defaults to DAY ONE onward, not today",
          d[0] == ws.DAY_ONE and len(d) > 1, f"{d[0]}..{d[-1]} ({len(d)}d)")
    try:
        ws.dates_of(_A(date="2026-08-31 2026-09-04"))
        check("W7  a malformed date RAISES rather than reading empty", False,
              "it returned a date list")
    except SystemExit as e:
        check("W7  a malformed date RAISES rather than reading empty",
              "NOT A DATE" in str(e), str(e).splitlines()[0].strip())

    # W8 — r298. A MULTI-DATE READ MUST NARRATE. The default window is now 14
    # days of sequential get_object calls; silent is indistinguishable from
    # hung, and the operator killed a run with ^C for exactly that reason.
    import time as _t
    class _S3:
        def get_paginator(self, *a): return self
        def paginate(self, **k):
            return [{"Contents": [{"Key": k.get("Prefix", "") + "o.json"}]}]
        def get_object(self, **k):
            class B: read = staticmethod(
                lambda: b'{"record":{"trade_id":"t","status":"closed"}}')
            return {"Body": B}
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        ws.load_trades(["2026-08-25", "2026-08-26", "2026-08-27"], s3=_S3())
    multi = b.getvalue()
    check("W8  a multi-date read prints a line per date",
          multi.count("2026-08-2") == 3, repr(multi.splitlines()[:1]))
    b2 = io.StringIO()
    with contextlib.redirect_stdout(b2):
        ws.load_trades(["2026-08-25"], s3=_S3())
    check("W8b a single-date read stays quiet - the banner already says it",
          b2.getvalue().strip() == "", repr(b2.getvalue()[:40]))

    # W9 — r299. NO R-SUITE TOOL MAY EXCLUDE RELAXED ROWS. Operator's ruling:
    # it is all paper, and paper-vs-live is the split that matters; a tag
    # applied as a silent filter made report 50 disagree with report 43 by 70%
    # of the book. EXECUTED against load_s3, not grepped: a fake S3 serves one
    # relaxed row and one strict, and both must survive.
    class _S3R:
        def get_paginator(self, *a): return self
        def paginate(self, **k):
            return [{"Contents": [{"Key": k.get("Prefix", "") + f"{i}.json"}
                                  for i in range(2)]}]
        _n = [0]
        def get_object(self, **k):
            i = self._n[0]; self._n[0] += 1
            rel = 1 if i % 2 else 0
            body = (b'{"record":{"trade_id":"t%d","status":"closed",'
                    b'"relaxed_entry":%d,"pnl_usd":10.0}}' % (i, rel))
            class B: read = staticmethod(lambda: body)
            return {"Body": B}
    with contextlib.redirect_stdout(io.StringIO()):
        got, _m = ws.load_trades(["2026-08-25"], s3=_S3R())
    class _A2:
        db = None; date = "2026-08-25"; frm = None; to = None; all_history = False
    with contextlib.redirect_stdout(io.StringIO()):
        kept = r_ledger.load_s3(_A2()) if hasattr(r_ledger, "load_s3") else None
    check("W9  relaxed rows are NOT excluded by load_s3",
          any(r.get("relaxed_entry") for r in got),
          f"{sum(1 for r in got if r.get('relaxed_entry'))} relaxed of {len(got)}")
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "r_ledger.py")).read()
    # ⚠️ WA §20 — ANCHOR ON THE DEFINITION, NEVER THE MENTION. The first cut
    # searched for the bare flag string and went red on r299's OWN CHANGELOG
    # ENTRY, which names the flag while explaining that it was removed. Rule 5
    # requires that entry to exist, so a mention-based canary is guaranteed to
    # trip on the documentation the version discipline demands. This is the
    # same collision the repo has now hit for the fourth time.
    check("W9b the dead --include-relaxed flag is gone, not left as a no-op",
          'add_argument("--include-relaxed"' not in src
          and "a.include_relaxed" not in src,
          "checked as an argparse DEFINITION and a call site, not a string")

    print()
    if F:
        print(f"check_r_ledger_width: FAIL ({len(F)}): {', '.join(F)}")
        return 1
    print("check_r_ledger_width: ALL PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
