#!/usr/bin/env python3
# options-trader-v4/tests/check_purge_batched.py — v1.1
# v1.1 (2026-09-23) — r417 / WH.20. §0.1 correction to this header; checks
#   are UNCHANGED.
# v1.0 (2026-09-22) — r416 / OPS.39. THE PURGE COMMITS AS IT GOES, OR A BOX
#   NEVER CATCHES UP.
#   🔴 THE DEFECT, MEASURED ON TWO LIVE BOXES. Every DELETE ran inside ONE
#   transaction committed after the LAST table. At ~93 seconds per million
#   rows that needed ~28 minutes on PLTR's 18M backlog and ~82 on QQQ's 53M,
#   against the conductor's 900s per-box budget. The run was killed, the whole
#   transaction rolled back — including tables that had finished — and the next
#   night faced MORE rows. PLTR reached 19.8 days against a 3-day policy and
#   97% disk; QQQ reached 19.9 days and 59.5M rows, while the other thirteen
#   boxes sat at 3.8 days and looked fine.
#   🔑 B2 IS THE CHECK THAT MATTERS AND THE ONE THE OLD CODE COULD NOT PASS:
#   **an interrupted run must KEEP what it committed.** That single property
#   converts the ratchet into convergence — a box that cannot drain in one
#   night drains over two instead of resetting to zero forever.
#   ⚠️ B4 EXISTS BECAUSE `removed[table]` IS SET FROM THE COUNT, NEVER FROM
#   THE COMMIT, so a run killed mid-transaction leaves an intact count in the
#   dict. That defect is real and it is QUIETER than this header first said.
#   🔴 §0.1 CORRECTION (r417), MINE, AGAINST MY OWN r416 HEADER: this block
#   read "THE REPORT LIED FOR WEEKS ... the conductor logged
#   `PLTR: plan_check 478,995` on a night PLTR still held 479,001 of them. A
#   number that reports INTENT as OUTCOME". **THAT IS WRONG AND IT IS STRUCK
#   RATHER THAN DELETED** (r240's precedent), because the next reader would
#   otherwise inherit it: `eod_conductor_v2` takes `tail -12` of the purge
#   output, which lands on the `_remaining` block, so EVERY per-box number in
#   that log is ROWS LEFT BEHIND, not rows removed. 478,995 remaining against
#   479,001 still held is CONSISTENT, not contradictory. The BACKLOG row was
#   corrected before r416 landed; this header was not, and a gate that carries
#   a retracted claim teaches it to whoever reads the gate instead of the row.
#   ⚠️ AND A KILLED PROCESS PRINTS NOTHING AT ALL, so no false success was ever
#   logged for the two backlogged boxes — the conductor logged a TIMEOUT.
"""Gate: retention deletes are batched, committed incrementally, and reported
from what committed.

B1   a full run drains the window
B2   an INTERRUPTED run keeps its committed progress (the ratchet fix)
B3   ...and a second run finishes the job
B4   the reported number is what COMMITTED, not what was counted
B5   no COUNT(*) on the apply path (r405's lesson)
"""
import os
import sqlite3
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_fails = []


def ck(tag, ok, msg=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {tag}  {msg}")
    if not ok:
        _fails.append(tag)


def _fixture(path, rows, age_days=10):
    if os.path.exists(path):
        os.remove(path)
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE quote_series (ts_epoch REAL, v TEXT)")
    old = time.time() - age_days * 86400
    c.executemany("INSERT INTO quote_series VALUES (?,?)",
                  [(old, "x") for _ in range(rows)])
    c.commit()
    c.close()


def _count(path):
    c = sqlite3.connect(path)
    n = c.execute("SELECT COUNT(*) FROM quote_series").fetchone()[0]
    c.close()
    return n


def main():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="purgebatch_")
    feed = os.path.join(tmp, "feed_store.db")
    derived = os.path.join(tmp, "derived_store.db")
    _fixture(derived, 0)

    os.environ["OT_PURGE_BATCH_ROWS"] = "500"
    os.environ.pop("OT_PURGE_BUDGET_S", None)
    import importlib
    import warehouse.retention_purge as rp
    importlib.reload(rp)

    # ── B1 — a full run drains the window ──────────────────────────────────
    _fixture(feed, 5000)
    rp.purge(apply=True, feed_db=feed, derived_db=derived)
    left = _count(feed)
    ck("B1", left == 0, f"full run drained 5000 -> {left}")

    # ── B2 — THE RATCHET FIX, DRIVEN ON A FAKE CLOCK SO IT CANNOT PASS
    # VACUOUSLY. The first cut gave the run a 1-SECOND budget and accepted
    # `mid == 0` — so it drained in 0.0s and the check passed WITHOUT EVER
    # INTERRUPTING ANYTHING. §0.4: a test with an escape hatch tests the
    # hatch. The clock now advances 10s per reading, so the deadline is
    # crossed after a known number of batches and the interruption is certain.
    _fixture(feed, 5000)
    importlib.reload(rp)
    rp.BATCH_ROWS = 500
    real_time = time.time
    state = {"t": real_time()}

    def _fake():
        state["t"] += 10.0
        return state["t"]

    # 🔴 getattr-GUARDED. The first cut called `rp._delete_batched` directly
    # and CRASHED at the born-red commit, taking B3, B4 and B5 down with it so
    # nothing after it reported — r400's R1c, the fifth instance this repo has
    # recorded. A check that dies tells the reader less than one that fails.
    _db = getattr(rp, "_delete_batched", None)
    if _db is None:
        ck("B2", False, "retention_purge has no _delete_batched — deletes are "
                        "unbatched, so an interrupted run rolls back entirely")
        got, outcome, mid = 0, "missing", 5000
    else:
        rp.time.time = _fake
        try:
            got, outcome = _db(
                sqlite3.connect(feed), "quote_series", "ts_epoch < ?",
                (real_time(),), [], deadline=state["t"] + 25.0)
        finally:
            rp.time.time = real_time
        mid = _count(feed)
        ck("B2", outcome == "budget" and 0 < mid < 5000 and got == 5000 - mid,
           f"interrupted at the budget after committing {got} row(s); table "
           f"5000 -> {mid}, and the report equals the commits "
           f"(old code would have rolled back to 5000)")

    # ── B3 — and the next run finishes, rather than starting over ──────────
    os.environ.pop("OT_PURGE_BUDGET_S", None)
    importlib.reload(rp)
    rp.BATCH_ROWS = 500
    for _ in range(20):
        rp.purge(apply=True, feed_db=feed, derived_db=derived)
        if _count(feed) == 0:
            break
    ck("B3", _count(feed) == 0,
       f"a following run converges to 0 (left={_count(feed)})")

    # ── B4 — the report is what COMMITTED ──────────────────────────────────
    _fixture(feed, 1200)
    importlib.reload(rp)
    rp.BATCH_ROWS = 500
    rep = rp.purge(apply=True, feed_db=feed, derived_db=derived)
    got = rep.get("quote_series")
    ck("B4", got == 1200 and _count(feed) == 0,
       f"reported {got}, table now {_count(feed)} — report equals commits")

    # ── B5 — no COUNT(*) on the apply path (r405) ──────────────────────────
    src = open(os.path.join(ROOT, "warehouse", "retention_purge.py"),
               encoding="utf-8", errors="replace").read()
    body = src.split("for table, days in ARTIFACT_DAYS.items():", 1)[-1][:1400]
    guarded = "if not apply:" in body and "SELECT COUNT(*)" in body
    ck("B5", guarded,
       "the COUNT survives only behind `if not apply:` — the apply path "
       "never pays for it"
       if guarded else "COUNT(*) is still on the apply path")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: {', '.join(_fails)}")
        return 1
    print("check_purge_batched: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
