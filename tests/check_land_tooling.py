#!/usr/bin/env python3
"""
tests/check_land_tooling.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.8  2026-10-25  OTV5 r4 (GATE.6) — T6 also requires OT_HEARTBEAT_FILE under $_scratch on every CHECK line (the watchdog's
      liveness signal; born red on land.sh v1.22).
v1.7  2026-10-24  OTV5 r0 — ONE LEDGER. T4 requires docs/GENESIS.md to carry this tree's own r0 row (the seed) and T5
      requires that no second ledger (docs/GENESIS-TEST.md) exists: the lander's LEDGER default IS this tree's ledger, so a
      spec needs no LEDGER line and a spec that names another file is wrong.
v1.6  2026-10-20  OTV4TEST r307 (GATE.4) — T6 also requires OT_PLAN_STATES_FILE under $_scratch on every CHECK line.
v1.5  2026-10-18  OTV4TEST r292 (GATE.1) — T6 also requires OT_FEED_DB, OT_RESTING_STOP_STATE and OT_WAREHOUSE_STATE under
      $_scratch on every CHECK line (audit 10-18 B4).
v1.4  2026-10-15  OTV4TEST r287 (CFDIR.1) — T6 also requires OT_COUNTERFACTUAL_DIR under $_scratch on every CHECK line.
v1.3  2026-10-03  OTV4TEST r194 (BOX.16) — T6 also requires OT_LOG_FILE under $_scratch on every CHECK line.
v1.2  2026-09-25  OTV4TEST r144 — T6 also requires OT_SIGNAL_JOURNAL_DIR under $_scratch
      on the line that runs a checker: the journal was the fourth live writer.
v1.1  2026-09-23  OTV4TEST r109 — T6: THE CHECK STAGE ISOLATES ALL THREE STORES.
      Anchored on the line that actually RUNS a checker (`python3 "$chk"`),
      not on a mention: it must set OT_TRADES_DB, OT_DERIVED_DB and
      OT_RESTING_DB to paths under `$_scratch`. The resting store was missing
      and 91 checker fixtures reached the live one. Born red at 2c17b2e.
v1.0  2026-09-08  OTV4TEST r1 — THE FORK'S LANDER AND ITS GATE ACTUALLY WORK.

This repo is segregated from control, so it carries its own copy of
`tools/land.sh` and `tools/check_land_discipline.py`. Nothing on the fleet
checks them and nothing on control can reach them. This does.

🔴 WHY THIS FILE EXISTS AS A FILE, rather than a `CHECK` line with a flag.
`land.sh` runs each declared check as `python3 "$chk"` — **quoted**, so the
whole line is one path and a CHECK CANNOT CARRY ARGUMENTS. Declaring
`CHECK tools/check_land_discipline.py --selftest` therefore fails under the
lander and PASSES BY HAND, which is the worst shape of red: it reads as a flaky
test rather than a wiring mistake. Found in rehearsal, 2026-09-08. The lander's
own header warns about that exact shape for a different cause (r279's nested
`LAND_ARCHIVE` leak), which is why it is named here rather than worked around
quietly.

⚠️ IT EXERCISES THE TOOLING'S JOB, NOT ITS PRESENCE. Asserting the files exist,
or that `--ledger` appears in the source, would hand out a green light on a
broken lander — the pytest-bootstrap lesson from mainline. So: the discipline
checker's own selftest is RUN, `land.sh` is PARSED, and the ledger argument is
exercised through argparse rather than grepped for.

Run:  python3 tests/check_land_tooling.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


def main():
    land = os.path.join(ROOT, "tools", "land.sh")
    disc = os.path.join(ROOT, "tools", "check_land_discipline.py")

    check("T0 the fork carries its own lander and gate",
          os.path.exists(land) and os.path.exists(disc),
          f"land.sh={os.path.exists(land)} discipline={os.path.exists(disc)}")
    if FAILED:
        print("\nRED — the tooling is absent; nothing below can run")
        return 1

    # T1 — the lander parses. Same class as SH.1 on mainline, where four shell
    # scripts aborted on a syntax error for fourteen days and nothing noticed.
    r = subprocess.run(["bash", "-n", land], capture_output=True, text=True)
    check("T1 tools/land.sh parses", r.returncode == 0,
          (r.stderr.strip().splitlines() or [""])[-1])

    # T2 — the discipline gate's OWN selftest, executed.
    r = subprocess.run([sys.executable, disc, "--selftest"],
                       capture_output=True, text=True, cwd=ROOT)
    check("T2 check_land_discipline --selftest passes", r.returncode == 0,
          (r.stdout.strip().splitlines() or [""])[-1])

    # T3 — `--ledger` is a real argument, CONSUMED, with the mainline default.
    # ⚠️ THE FIRST CUT OF THIS CHECK GREPPED `--help` FOR THE DEFAULT and was
    # red against a working tool, because argparse does not print defaults
    # unless the help string asks. The tool now says `%(default)s` — and the
    # second assertion below proves the argument is ACTED ON rather than merely
    # accepted, by pointing it at a ledger that does not exist and requiring
    # the tool to say so.
    r = subprocess.run([sys.executable, disc, "--help"],
                       capture_output=True, text=True, cwd=ROOT)
    check("T3 --ledger is offered and shows the mainline default",
          "--ledger" in r.stdout and "docs/GENESIS.md" in r.stdout,
          "not in --help output")

    r = subprocess.run([sys.executable, disc, "--repo", ROOT, "--rev", "r1",
                        "--ledger", "docs/NO-SUCH-LEDGER.md"],
                       capture_output=True, text=True, cwd=ROOT)
    _saw = [l for l in (r.stdout + r.stderr).splitlines()
            if "NO-SUCH-LEDGER" in l]
    check("T3b and the path is actually consumed, not ignored",
          bool(_saw), (_saw[0].strip()[:70] if _saw
                       else "the tool never mentioned the ledger it was handed"))

    # T4 — this repo's ledger is docs/GENESIS.md and it carries the tree's own r0 row (OTV5 r0: the
    # numbering starts at the seed; a ledger without r0 is some other tree's ledger).
    ledger = os.path.join(ROOT, "docs", "GENESIS.md")
    rows = []
    if os.path.exists(ledger):
        rows = [l for l in open(ledger, encoding="utf-8").read().splitlines() if l.startswith("| **r")]
    check("T4 docs/GENESIS.md exists and its first row is r0, the seed",
          bool(rows) and rows[0].startswith("| **r0** |"),
          f"first row: {(rows[0][:60] if rows else 'none')}")

    # T5 — there is NO second ledger. The lander's LEDGER default is docs/GENESIS.md, so every spec for this
    # tree omits LEDGER; a docs/GENESIS-TEST.md here would mean a spec pointed a row at the wrong file.
    second = os.path.join(ROOT, "docs", "GENESIS-TEST.md")
    check("T5 no second ledger (docs/GENESIS-TEST.md) exists in this tree", not os.path.exists(second))

    print()
    # ── T6 (r109) — the check stage hands every checker scratch stores ──────
    _ls = open(os.path.join(ROOT, "tools", "land.sh"), encoding="utf-8").read()
    _runs = [ln for ln in _ls.splitlines()
             if 'python3 "$chk"' in ln and not ln.lstrip().startswith("#")]
    _need = ('OT_TRADES_DB="$_scratch/', 'OT_DERIVED_DB="$_scratch/',
             'OT_RESTING_DB="$_scratch/', 'OT_SIGNAL_JOURNAL_DIR="$_scratch/',
             'OT_LOG_FILE="$_scratch/', 'OT_COUNTERFACTUAL_DIR="$_scratch/',    # r194, r287
             'OT_FEED_DB="$_scratch/', 'OT_RESTING_STOP_STATE="$_scratch/',
             'OT_WAREHOUSE_STATE="$_scratch/',                                  # r292 (GATE.1)
             'OT_PLAN_STATES_FILE="$_scratch/',                                 # r307 (GATE.4)
             'OT_HEARTBEAT_FILE="$_scratch/')                                   # OTV5 r4 (GATE.6)
    _bad = [ln.strip()[:90] for ln in _runs if not all(n in ln for n in _need)]
    check("T6 every CHECK invocation isolates the trades, derived, resting stores, the journal, the log, the counterfactual logs, the feed store, the resting-stop state, the warehouse state and the plan states",
          bool(_runs) and not _bad,
          f"{len(_runs)} invocation line(s)" + (f"; missing on: {_bad}" if _bad else ""))

    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — the land tooling runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
