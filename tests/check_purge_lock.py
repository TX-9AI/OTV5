#!/usr/bin/env python3
"""tests/check_purge_lock.py — v1.2
v1.2  2026-10-13 — OTV4TEST r279 (mirror of otv4 r416). K0 pins `_delete_batched`;
`_try_delete` is removed (every DELETE now goes through the batched path).
v1.1  2026-09-14 — OTV4TEST r26 (HYG.9). L1 NO LONGER TAKES THE BOX'S REAL LOCK.
Both the holder subprocess and this process called `acquire_lock` on the module's
`LOCK_PATH` — `<repo>/data/retention_purge.lock` — so every run of this check
created that file in the real checkout (found 2026-09-13 as an untracked file
the r25 archive nearly shipped), and, on a box whose nightly purge was running,
L1 would have raced the real purge for its lock: a checker reaching live state,
the r13/HYG.6 class. Both processes now point `LOCK_PATH` at a scratch file, and
L0 asserts the real path is not created by the run (when it was absent before).
v1.0  2026-09-05 — r256. MUTUAL EXCLUSION AND PARTIAL-FAILURE BEHAVIOUR,
DRIVEN AGAINST REAL PROCESSES AND A REAL LOCKED DATABASE.

🔴 WHAT IT PINS, AND ALL OF IT WAS MEASURED ON THE FLEET FIRST. On 2026-09-05
the conductor's purge phase and a hand-run `--apply` overlapped: four boxes
raised `sqlite3.OperationalError: database is locked` at `DELETE FROM candles`,
the exception escaped `purge()`, killed `main()`, and the RECLAIM never ran —
so those boxes kept their WALs while the eleven that got through returned
8.7 GB. `s3_push` has guarded every invocation path with `flock` since WH.6;
this file, which DELETES, had nothing.

⚠️ L1 TAKES THE LOCK IN A SECOND PROCESS, not by patching a flag. `flock` is
advisory and per-open-file-description — a same-process check would pass
against code that never locks at all, which is the shape of a test that proves
only that it agrees with itself (C.23).

⚠️ AND D1 HOLDS A REAL WRITE TRANSACTION rather than simulating a failure. The
whole finding is that SQLite's five-second default is shorter than one 2 GB
delete; asserting that with a stubbed exception would pin the handler and miss
the timeout, which is the half that actually bit.
"""
import os
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import time

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


def _store(d):
    """A feed store with stale rows in two tables, so a partial failure is
    visible as one table trimmed and one not."""
    old = time.time() - 40 * 86400
    c = sqlite3.connect(os.path.join(d, "feed_store.db"))
    c.execute("pragma journal_mode=WAL")
    c.execute("create table candles(symbol,interval,ts_epoch_ms,c)")
    c.execute("create table greeks_series(ts_epoch,v)")
    c.executemany("insert into candles values(?,?,?,?)",
                  [("Q", "1m", int(old * 1000), "x" * 200) for _ in range(500)])
    c.executemany("insert into greeks_series values(?,?)",
                  [(old, "y" * 200) for _ in range(500)])
    c.commit()
    c.close()


def main():
    try:
        from warehouse import retention_purge as rp
    except Exception as exc:                                    # noqa: BLE001
        check("K0 retention_purge is importable", False,
              f"{type(exc).__name__}: {exc}")
        print("\nRED — 1 failed: K0 (the checker could not run)")
        return 1
    for n in ("acquire_lock", "_delete_batched", "LOCK_PATH", "BUSY_MS"):
        if not hasattr(rp, n):
            check(f"K0 retention_purge exposes {n}", False,
                  "absent — r256 has not landed in this checkout")
            print("\nRED — 1 failed: K0")
            return 1
    check("K0 retention_purge exposes the r256 surface", True)

    # ══ L0 (r26) — THE CHECK NEVER TOUCHES THE REAL LOCK ═══════════════════
    real_lock = rp.LOCK_PATH
    real_existed = os.path.exists(real_lock)
    _l1_dir = tempfile.mkdtemp()
    rp.LOCK_PATH = os.path.join(_l1_dir, "retention_purge.lock")

    # ══ L1 — A SECOND PROCESS CANNOT ENTER WHILE ONE HOLDS THE LOCK ═══════
    # 🔑 REAL PROCESS, REAL flock. Advisory locks are per open-file-description,
    # so acquiring twice in ONE process would succeed even against code that
    # locks nothing, and the check would be theatre.
    holder = subprocess.Popen(
        [sys.executable, "-c", textwrap.dedent(f"""
            import sys, time
            sys.path.insert(0, {_root!r})
            from warehouse import retention_purge as rp
            rp.LOCK_PATH = {rp.LOCK_PATH!r}
            fh = rp.acquire_lock(0)
            print("held" if fh else "nolock", flush=True)
            time.sleep(8)
        """)], stdout=subprocess.PIPE, text=True)
    try:
        first = (holder.stdout.readline() or "").strip()
        check("L1 the first caller acquires the lock", first == "held", first)
        t0 = time.time()
        mine = rp.acquire_lock(2)          # short wait, must give up
        waited = time.time() - t0
        check("L1b a second caller is REFUSED while it is held", mine is None)
        # ⚠️ IT WAITS RATHER THAN FAILING FAST. A purge that declines the
        # instant a drain is still finishing is a purge that silently does not
        # run — the r162 failure in a new costume.
        check("L1c ...and it WAITED for the timeout rather than refusing "
              "immediately", waited >= 1.8, f"{waited:.1f}s")
    finally:
        holder.kill()
        holder.wait()
    after = rp.acquire_lock(2)
    check("L1d once released, the lock is available again", after is not None)
    if after:
        import fcntl
        fcntl.flock(after, fcntl.LOCK_UN)
        after.close()
    rp.LOCK_PATH = real_lock
    check("L0 the run did not create the box's real lock file",
          real_existed or not os.path.exists(real_lock), real_lock)

    # ══ L2 — THE LOCK IS ROUND EVERYTHING, AND A DECLINE IS NAMED ═════════
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "data")
        os.makedirs(d)
        _store(d)
        saved_lock, saved_here, saved_wait = rp.LOCK_PATH, rp.HERE, rp.LOCK_WAIT
        rp.LOCK_PATH = os.path.join(d, "purge.lock")
        rp.HERE = tmp
        # ⚠️ THE PRODUCTION WAIT IS 300s BY DESIGN — a nightly chain has minutes
        # to spare. A checker that inherited it would hang for five minutes,
        # so the WAIT is shortened here and the DEFAULT is pinned by L3.
        rp.LOCK_WAIT = 2
        try:
            blocker = rp.acquire_lock(0)
            check("L2 a run that cannot get the lock returns non-zero and "
                  "deletes NOTHING",
                  blocker is not None and rp.main(["--apply"]) == 3)
            n = sqlite3.connect(os.path.join(d, "feed_store.db")).execute(
                "select count(*) from candles").fetchone()[0]
            check("L2b ...and the rows are still there", n == 500, str(n))
            import fcntl
            fcntl.flock(blocker, fcntl.LOCK_UN)
            blocker.close()
        finally:
            rp.LOCK_PATH, rp.HERE, rp.LOCK_WAIT = saved_lock, saved_here, saved_wait

    # ══ D1 — ONE LOCKED TABLE COSTS THAT TABLE, NOT THE RUN ═══════════════
    # 🔴 THE MEASURED FAILURE. An unguarded DELETE took `main()` with it and the
    # reclaim never executed, which is why four boxes kept their WALs.
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "data")
        os.makedirs(d)
        _store(d)
        feed = os.path.join(d, "feed_store.db")
        # A real, held write transaction — not a stubbed exception. This is
        # what a competing purge looks like from inside.
        blocker = sqlite3.connect(feed)
        blocker.execute("begin exclusive")
        saved_busy, saved_lock, saved_here = rp.BUSY_MS, rp.LOCK_PATH, rp.HERE
        saved_wait = rp.LOCK_WAIT
        rp.LOCK_WAIT = 2
        rp.BUSY_MS = 300                    # keep the case quick
        rp.LOCK_PATH = os.path.join(d, "purge.lock")
        rp.HERE = tmp
        try:
            rc = rp.main(["--apply"])
            check("D1 a locked table does not raise — the run completes",
                  rc == 4, f"rc={rc}")
            # ⚠️ AND IT IS REPORTED, NOT ABSORBED. rc=4 is what lets the
            # conductor's phase say "partial" per box instead of "done".
            check("D1b ...with a non-zero code that names it a PARTIAL purge",
                  rc == 4)
        finally:
            blocker.rollback()
            blocker.close()
            rp.BUSY_MS, rp.LOCK_PATH, rp.HERE = saved_busy, saved_lock, saved_here
            rp.LOCK_WAIT = saved_wait

    # ══ B1 — THE BUSY TIMEOUT IS EXPLICIT AND NOT SQLITE'S DEFAULT ════════
    # 🔴 `_open()` used `sqlite3.connect(path)`, whose default is FIVE SECONDS —
    # shorter than a single 2 GB delete, so a brief overlap raised instead of
    # waiting. Read back from the connection, never from the constant.
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "data")
        os.makedirs(d)
        _store(d)
        c = rp._open(os.path.join(d, "feed_store.db"))
        got = c.execute("pragma busy_timeout").fetchone()[0]
        c.close()
        check("B1 connections carry an explicit busy_timeout well above the "
              "5s default", got >= 30000, f"{got}ms")

    # ══ L3 — AND THE SHIPPED DEFAULTS ARE THE OPERATING ONES ═════════════
    # ⚠️ The cases above shorten LOCK_WAIT and BUSY_MS to stay quick. Without
    # this, a future edit could drop the production wait to two seconds and
    # every check here would still pass — which is the fixture agreeing with
    # itself rather than with the fleet.
    check("L3 the shipped lock wait is long enough for a drain to finish",
          rp.LOCK_WAIT >= 120, f"{rp.LOCK_WAIT}s")
    check("L3b and the shipped busy timeout exceeds SQLite's 5s default by a "
          "wide margin", rp.BUSY_MS >= 30000, f"{rp.BUSY_MS}ms")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 11 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
