#!/usr/bin/env python3
"""tools/boot_sweep.py — v1.8
v1.8 (2026-10-20) — OTV4TEST r307 (GATE.4). OT_PLAN_STATES_FILE IS SCRATCH: r303's plans panel reads data/plan_states.json
(the bot writes it at start; VOLT is dormant in it), so check_foreign_symbol_board F7's stale-VOLT control row vanished
and the 10-20 08:00 sweep went RED on QQQ-TEST and SPX-TEST alike - green in every worktree, which has no such file. A
checker that drives main's start would also have rewritten the live file. check_boot_sweep B3/B3b.

v1.7 (2026-10-18) — OTV4TEST r292 (GATE.1). THREE MORE STORES ARE SCRATCH: OT_FEED_DB (the live feed_store.db -
42 checkers import modules whose r284/r285/r288 paths resolve feed_db_path() at call time, so under the sweep they READ
the live 2.5 GB tape and a checker's verdict depended on live retention), OT_RESTING_STOP_STATE (a checker driving the
resting stop would write the live data/resting_stop_state.json) and OT_WAREHOUSE_STATE (the push/purge ledgers under
~/.vertigo_warehouse). Found by the 2026-10-18 audit (B4). check_boot_sweep B3/B3b.

v1.6 (2026-10-15) — OTV4TEST r287 (CFDIR.1). THE COUNTERFACTUAL LOGS ARE SCRATCH TOO: run_one sets
  OT_COUNTERFACTUAL_DIR under the same bootsweep- mkdtemp, so a checker that drives an exit, entry or
  plan path no longer appends fixture rows to the live data/counterfactual/. check_boot_sweep B3/B3b.

v1.5 (2026-10-06) — OTV4TEST r257. A SWEEP NEVER STARTS INSIDE ANOTHER SWEEP. check_boot_sweep's B1b drives
  `boot_sweep --only check_boot_sweep`, which runs check_boot_sweep, which drives it again - nothing bounded
  the depth. Found by SPX-TEST 10-06: its 08:05 sweep's chain outlived B1b's 180 s timeout (unit peak 1 GB,
  688 MB swap, the bot running); reproduced by hand at 60+ levels. run_one now hands every checker
  OT_SWEEP_NESTED=1, and main() refuses at once under it: prints NESTED, runs nothing, writes no result,
  exits 0. Depth is now at most 2. check_boot_sweep B8/B8b.

v1.4 (2026-10-03) — OTV4TEST r194. THE LOG IS SCRATCH TOO (BOX.16): run_one sets OT_LOG_FILE under
  the same bootsweep- mkdtemp, so a checker that imports main no longer writes the live bot.log.
v1.3 (2026-09-26) — OTV4TEST r146. Checkers get OT_INSTRUMENT=QQQ EXPLICITLY when the
      sweep's environment has none: config no longer falls back to QQQ, and the
      checkers were written against it. A fixture symbol stated here, not guessed.

v1.2 (2026-09-25) — OTV4TEST r144. THE SIGNAL JOURNAL IS SCRATCH TOO.
      2026-09-25: the boot sweep's ORB checkers wrote 126 retest_check fixture events into the LIVE
      data/signal_journal/<date>/QQQ.jsonl on this box every morning, and on SOFI and AAL the pusher
      filed them under sym=QQQ in the warehouse - ~76 per box per BOOT, about 320 fabricated
      events in QQQ's real partition (byte-identical 71,944-byte files on two boxes). r13 and r109
      isolated the three stores; the journal was the fourth writer and nobody had redirected it.
      run_one now sets OT_SIGNAL_JOURNAL_DIR under the run's mkdtemp; check_boot_sweep
      B3/B3b require it.

v1.1 (2026-09-23) — OTV4TEST r109. THE RESTING-ORDER STORE IS SCRATCH TOO. Every
      sweep wrote a `check_entry_gate` fixture offer (symbol X, strike 81) into
      the LIVE `data/resting_orders.db` — 91 of its 101 rows by 2026-09-23 —
      because only OT_TRADES_DB and OT_DERIVED_DB were redirected. `run_one`
      now sets OT_RESTING_DB as well; check_boot_sweep B3b drives it.
v1.0 (2026-09-21) — OTV4TEST r74 / SWEEP.1. THE FULL CHECK SET RUNS AT BOOT,
SO A DELIVERY DOES NOT HAVE TO PAY FOR IT.

🔴 THE PROBLEM THIS SOLVES, MEASURED. Landing a ONE-LINE change was costing
**297 checker invocations** — 7 the lander genuinely forces, and 290 a full
sweep of 145 checkers across two trees, about 11 minutes. The operator,
2026-09-21: *"that is entirely ludicrous… The 30-minute per commit cycle is
choking our commit rate for needed changes."* His fix, and it is better than
the one proposed to him: *"You have an AWS auto boot daily at 0800. Why not run
the full set then & do the abbreviated when we're actively trying to land."*

🔑 THE SIGNAL IS THE DIFF, NOT THE COUNT. This tree carries 11 STANDING REDS.
A run that reports "134 of 145" tells nobody anything — what matters is that a
TWELFTH appeared. So the previous run is kept and every result is reported as
NEW / FIXED / unchanged against it. A sweep with no baseline is a number, and
§18's whole subject is numbers that look like answers.

⚠️ IT NEVER ABORTS EARLY. The operator's ruling on what to do with a failure:
*"Flag it, finish the sweep, brief it with the proposed fix and rationale why
the fix works."* Stopping at the first red would hide every red behind it, and
the brief he wants is impossible without the whole picture.

⚠️ THE BRIEF IS NOT WRITTEN HERE, AND THAT IS DELIBERATE. This script DETECTS
and RECORDS. The boot agent — raised by `tools/claude_boot.py` at the same boot
— DIAGNOSES and briefs, because a proposed fix with a rationale is not
something a sweep runner can produce. Same division as r67's shutdown cause and
r68's agent status: the thing that KNOWS writes a stamp, the thing that can
SPEAK reads it.

⚠️ NOTHING HERE IS LOAD-BEARING FOR TRADING (§29). It runs AFTER the bot and
the feed are up, never before: a sweep that delayed the 08:00 start would make
itself load-bearing, and 5.5 minutes is not 45 seconds (r68 bounded its raiser
at that for the same reason). It is niced to 19, it exits 0 on every path, and
it SKIPS ITSELF if memory is tight rather than competing with the live bot.
MEASURED on this box before it was written: with the sweep, the bot and the
feed all running, available memory floored at **298 MB of 908 MB** and swap
rose 176 -> 482 MB. Safe, but not by so much that the guard is decoration.

⚠️ AND IT NEVER TOUCHES THE LIVE STORES. Every checker runs with
OT_TRADES_DB / OT_DERIVED_DB pointed at a fresh scratch pair — r13's finding
(a fixture landed as a live open position) and the operator's own standing
rule that a check once purged live data.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ⚠️ THE RESULT ARTIFACT GETS THE SAME SCRATCH DISCIPLINE AS THE STORES, AND
# IT WAS ADDED BECAUSE THIS TOOL'S OWN CHECKER CONTAMINATED IT. r86's B1b
# drives the real binary three times to prove it exits 0 on every path (§21),
# and each of those runs OVERWROTE data/SWEEP_RESULT — so the first thing the
# 08:00 agent would have read was a test fixture reporting "no checkers found".
# Exactly r13's finding and r72's replay, one artifact over: a check that
# writes where production reads is a check that breaks production.
_OUT = os.environ.get("OT_SWEEP_RESULT_DIR") or os.path.join(_root, "data")
RESULT = os.path.join(_OUT, "SWEEP_RESULT")
PREV = os.path.join(_OUT, "SWEEP_PREV")
TESTS = os.path.join(_root, "tests")
PY = os.path.join(_root, "venv", "bin", "python")

# ⚠️ THE INTERPRETER IS PINNED, NOT INHERITED. ENV.1: system python3 on this box
# is 3.14 with NO pandas, so a sweep run under it turns every pandas-dependent
# checker red for a reason unrelated to its content — §36's named failure, a
# verification going red on ENVIRONMENT rather than CONTENT. A unit reads no
# profile, so PATH cannot be relied on here at all.
MIN_FREE_MB = int(os.environ.get("OT_SWEEP_MIN_FREE_MB", "180"))
PER_CHECK_TIMEOUT_S = int(os.environ.get("OT_SWEEP_TIMEOUT_S", "300"))


def _free_mb() -> int:
    """MemAvailable in MB, or -1 if it cannot be read."""
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        pass
    return -1


def _checkers() -> list:
    try:
        return sorted(f for f in os.listdir(TESTS)
                      if f.startswith("check_") and f.endswith(".py"))
    except OSError:
        return []


def run_one(name: str) -> bool:
    """True if the checker exits 0. Scratch stores, pinned interpreter, niced."""
    d = tempfile.mkdtemp(prefix="bootsweep-")
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["OT_TRADES_DB"] = os.path.join(d, "trades.db")
    env["OT_DERIVED_DB"] = os.path.join(d, "derived_store.db")
    env["OT_RESTING_DB"] = os.path.join(d, "resting_orders.db")     # r109
    env["OT_SIGNAL_JOURNAL_DIR"] = os.path.join(d, "signal_journal")  # r144
    env["OT_LOG_FILE"] = os.path.join(d, "bot.log")                   # r194 (BOX.16)
    env["OT_COUNTERFACTUAL_DIR"] = os.path.join(d, "counterfactual")  # r287 (CFDIR.1)
    env["OT_FEED_DB"] = os.path.join(d, "feed_store.db")              # r292 (GATE.1): the 2.5 GB live tape
    env["OT_RESTING_STOP_STATE"] = os.path.join(d, "resting_stop_state.json")   # r292: a rest survives a restart
    env["OT_WAREHOUSE_STATE"] = os.path.join(d, "warehouse_state")    # r292: the push/purge ledgers
    env["OT_PLAN_STATES_FILE"] = os.path.join(d, "plan_states.json")  # r307 (GATE.4): the live bot's plan states
    env["OT_SWEEP_NESTED"] = "1"     # r257: a checker that drives this tool gets a refusal, not a sweep
    env.setdefault("OT_INSTRUMENT", "QQQ")   # r146: an EXPLICIT fixture symbol; config no longer guesses one
    try:
        p = subprocess.run([PY, os.path.join(TESTS, name)],
                           cwd=_root, env=env, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=PER_CHECK_TIMEOUT_S)
        return p.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _load(path: str) -> dict:
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def sweep(dry: bool = False, only: str = "") -> dict:
    """Run every checker. Returns the result dict; never raises."""
    started = time.time()
    names = _checkers()
    if only:
        # SELECTION ONLY — the checkers still run from tests/ with the same
        # interpreter, scratch stores and nice level, so a smoke run exercises
        # the real path and not a simplified one (§21).
        _want = {n if n.endswith(".py") else f"{n}.py"
                 for n in (x.strip() for x in only.split(",")) if n}
        names = [n for n in names if n in _want]
        _missing = sorted(_want - set(names))
        if _missing:
            print(f"boot_sweep: --only named {len(_missing)} unknown checker(s): "
                  f"{', '.join(_missing)}", file=sys.stderr)
    if not names:
        return {"state": "ERROR", "why": "no checkers found", "at": started}

    free = _free_mb()
    if free != -1 and free < MIN_FREE_MB:
        # ⚠️ SKIPPED IS A RESULT, NOT A SILENCE (§0.5). "could not run" and
        # "ran and found nothing" must never look alike.
        return {"state": "SKIPPED", "why": f"only {free}MB available, "
                f"below the {MIN_FREE_MB}MB floor — refusing to compete with "
                f"the live bot for memory", "at": started, "free_mb": free}
    if dry:
        return {"state": "DRY", "why": f"{len(names)} checkers would run",
                "at": started, "free_mb": free}

    failed = []
    for n in names:
        if not run_one(n):
            failed.append(n)
    return {"state": "RAN", "at": started, "secs": round(time.time() - started, 1),
            "total": len(names), "failed": sorted(failed), "free_mb": free}


def diff(now: dict, prev: dict) -> dict:
    """NEW / FIXED against the previous run. The whole point of keeping one."""
    if now.get("state") != "RAN" or prev.get("state") != "RAN":
        return {"new": [], "fixed": [], "baseline": False}
    a, b = set(prev.get("failed") or []), set(now.get("failed") or [])
    return {"new": sorted(b - a), "fixed": sorted(a - b), "baseline": True}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    # ⚠️ --only EXISTS SO THIS TOOL CAN BE SMOKE-TESTED IN PLACE. RPL.3's
    # finding is that the instruments are the least-tested code in the repo —
    # `edge_scan` crashed on the real book while its own selftest printed ALL
    # PASS. A sweep runner with no way to exercise a SUBSET can only be tested
    # by running all 150, which nobody does during a session, so it never gets
    # tested at all. The checkers still run FROM tests/ so their sys.path
    # bootstrap resolves to the repo root; only the SELECTION narrows.
    ap.add_argument("--only", default="", help="comma-separated checker names "
                                               "(smoke-testing; selection only)")
    ap.add_argument("--show", action="store_true", help="print the last result")
    a = ap.parse_args(argv)

    if a.show:
        r = _load(RESULT)
        print(json.dumps(r, indent=2) if r else "no sweep result recorded")
        return 0

    if os.environ.get("OT_SWEEP_NESTED") == "1":
        # 🔴 r257 — a sweep inside a sweep recursed without bound (SPX-TEST, 10-06).
        print("boot_sweep: NESTED inside another sweep's checker - refusing; nothing run, no result written")
        return 0
    prev = _load(RESULT)
    now = sweep(dry=a.dry_run, only=a.only)
    now["diff"] = diff(now, prev)
    try:
        os.makedirs(os.path.dirname(RESULT), exist_ok=True)
        if prev:
            with open(PREV, "w") as fh:
                json.dump(prev, fh)
        with open(RESULT, "w") as fh:
            json.dump(now, fh, indent=1)
    except OSError as exc:
        print(f"boot_sweep: could not record result: {exc}", file=sys.stderr)

    d = now.get("diff") or {}
    if now.get("state") == "RAN":
        print(f"boot_sweep: {now['total'] - len(now['failed'])}/{now['total']} pass "
              f"in {now['secs']}s; {len(now['failed'])} red")
        if d.get("new"):
            print(f"boot_sweep: NEW FAILURES ({len(d['new'])}): {', '.join(d['new'])}")
        if d.get("fixed"):
            print(f"boot_sweep: fixed since last run: {', '.join(d['fixed'])}")
        if not d.get("baseline"):
            print("boot_sweep: no previous run — this one becomes the baseline")
    else:
        print(f"boot_sweep: {now.get('state')} — {now.get('why')}")
    # ⚠️ ALWAYS 0. A non-zero exit would mark the unit failed and put a red in
    # `systemctl status` for a finding that is not an infrastructure fault.
    return 0


if __name__ == "__main__":
    # 🔴 r86 — NOTHING ESCAPES. `main()` returning 0 on every path is not the
    # same as this process exiting 0: an uncaught exception bypasses every
    # return and marks the systemd unit FAILED. Found by the smoke test — a
    # NameError in the --only wiring exited 1 while B1 still read green,
    # because B1 walked the AST for `return` statements and never DROVE the
    # tool. §21 exactly: a test reading source text proves nothing about
    # runtime. The tool now cannot put a red in `systemctl status` for
    # anything short of the interpreter failing to start.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as _exc:                               # noqa: BLE001
        print(f"boot_sweep: CRASHED — {type(_exc).__name__}: {_exc}", file=sys.stderr)
        raise SystemExit(0)
