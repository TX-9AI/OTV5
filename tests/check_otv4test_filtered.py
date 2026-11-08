#!/usr/bin/env python3
"""
tests/check_otv4test_filtered.py  v5.0
v5.0  2026-11-08  OTV5 r80 (RSUITE.2) — new. THE S3 R TOOLS NEVER COUNT THE OTV4TEST FLEET. r_ledger.load_s3 returned
      every closed row warehouse_source.load_trades gave it (raw/ holds both fleets), so R LEDGER, the stop surface,
      EXCURSIONS and the exit replay counted OTV4TEST's AAL and SOFI trades in any window before 10-25 - against the
      operator's standing rule that OTV4TEST is filtered out of every warehouse measurement. `load_trades` is
      replaced by a fixture: no S3 read, no network.
  F1  r_ledger.load_s3 drops a TEST-tagged row, an untagged AAL row and an untagged SOFI row before 10-25; it keeps
      an OTV5 row, an untagged SOFI row on 11-02 and a SOFI row tagged OTV5 before 10-25 (the tag wins)
  F2  stop_sweep and excursions read THE SAME load_s3 (no second loader that could skip the filter)
  F3  exit_replay.run_s3 hands run() only the mainline rows
  F4  the filter prints one line with the count by symbol, and "0 row(s)" when nothing is dropped
  F5  every tool under tests/ that reads the S3 trades (`ws.load_trades(` / `warehouse_source.load_trades(`) also
      filters (mainline( or mainline_rows(); trade_report's own load_trades reads one box's trades.db and is not one
Run:  python3 tests/check_otv4test_filtered.py
"""
import contextlib
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAILS, RAN = [], []


def check(n, ok, msg):
    RAN.append(n)
    print("  {:<4} {}  {}".format(n, "PASS" if ok else "FAIL", msg))
    if not ok:
        FAILS.append(n)


ROWS = [
    dict(trade_id="otv5", symbol="NVDA", lineage="OTV5", status="closed", entry_time="2026-10-20T14:01:00"),
    dict(trade_id="tagged", symbol="NVDA", lineage="TEST", status="closed", entry_time="2026-10-20T14:02:00"),
    dict(trade_id="aal", symbol="AAL", status="closed", entry_time="2026-11-03T14:03:00"),
    dict(trade_id="sofi_old", symbol="SOFI", status="closed", entry_time="2026-10-20T14:04:00"),
    dict(trade_id="sofi_new", symbol="SOFI", status="closed", entry_time="2026-11-02T14:05:00"),
    dict(trade_id="sofi_tag5", symbol="SOFI", lineage="OTV5", status="closed", entry_time="2026-10-20T14:06:00"),
]
KEEP = {"otv5", "sofi_new", "sofi_tag5"}


class _Meta:
    error = None

    def banner(self):
        return "SOURCE: fixture"


class _A:
    date, frm, to, all_history = "2026-10-20", None, None, False


def main():
    import warehouse_source as ws
    ws.load_trades = lambda dates, s3=None: ([dict(r) for r in ROWS], _Meta())
    ws.dates_of = lambda a: ["2026-10-20"]
    import r_ledger as rl

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        got = rl.load_s3(_A())
    ids = {r["trade_id"] for r in (got or [])}
    check("F1", ids == KEEP, "kept " + ",".join(sorted(ids)) + ("" if ids == KEEP else "  (want " + ",".join(sorted(KEEP)) + ")"))

    import stop_sweep
    import excursions
    same = stop_sweep.load_s3 is rl.load_s3 and excursions.load_s3 is rl.load_s3
    check("F2", same, "stop_sweep and excursions share r_ledger.load_s3" if same else "a second loader exists")

    import exit_replay as er
    seen = {}
    er.run = lambda rows, fetch: seen.setdefault("ids", {r["trade_id"] for r in rows}) and 0

    class _Fetch:
        error = None

        def __init__(self, rows):
            pass

        def banner(self):
            return "fixture fetch"
    er._S3StreamFetch = _Fetch
    with contextlib.redirect_stdout(io.StringIO()):
        er.run_s3(_A())
    check("F3", seen.get("ids") == KEEP, "exit_replay replays " + ",".join(sorted(seen.get("ids") or [])))

    line = [l for l in buf.getvalue().splitlines() if "OTV4TEST filter" in l]
    with contextlib.redirect_stdout(io.StringIO()) as b0:
        rl.mainline_rows([dict(ROWS[0])])
    zero = "0 row(s) dropped" in b0.getvalue()
    ok4 = len(line) == 1 and "3 row(s) dropped" in line[0] and "AAL 1" in line[0] and "SOFI 1" in line[0] and zero
    check("F4", ok4, (line[0].strip() if line else "no filter line") + ("; 0 printed" if zero else "; 0 NOT printed"))

    bad = []
    for f in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        name = os.path.basename(f)
        if name.startswith("check_") or name in ("warehouse_source.py",):
            continue
        src = open(f).read()
        if re.search(r"\b(ws|warehouse_source)\.load_trades\(", src) and not re.search(r"\bmainline(_rows)?\(", src):
            bad.append(name)
    check("F5", not bad, "every load_trades caller filters" if not bad else "unfiltered: " + ", ".join(bad))

    print("")
    if FAILS:
        print("FAILED: " + ", ".join(FAILS))
        return 1
    print("ALL PASS ({})".format(len(RAN)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
