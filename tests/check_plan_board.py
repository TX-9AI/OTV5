#!/usr/bin/env python3
"""
tests/check_plan_board.py  v1.1
THE PLAN BOARD REPORTS LAST KNOWN STATUS AND WHEN IT CHANGED — AND WRITES NOTHING.

v1.1  2026-09-18  OTV4TEST r49 — `guard()` takes a CALLABLE detail. Its `detail`
      argument was evaluated BEFORE the predicate ran, so any detail computed
      from state the predicate sets printed STALE — a failing check reporting
      the opposite of its own finding. Rendered after the predicate now.
v1.0  2026-09-18  OTV4TEST r42 — born red at r41 (b3f0144): `tools/plan_board.py`
      did not exist.

Operator, 2026-09-18: *"can you just have each plan report its last known status
& a time stamp? For example, Active plan in progress or Active plan selected or
inactive outside of window."*

⚠️ B5 IS THE ONE THAT MATTERS AND IT IS A ROW COUNT, NOT A STRING. A reader that
writes is the defect class this repo has already paid for — `check_standing_offer`
S5 landed a fixture as a LIVE OPEN POSITION on 2026-09-10, which is why the
lander now points every CHECK at scratch stores. So B5 counts `plan_tick` before
and after and demands they are equal.
"""
import os
import subprocess
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "plan_board.py")
PY = os.path.join(ROOT, "venv", "bin", "python")
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def guard(name, fn, detail=""):
    """Run a predicate; a MISSING symbol is a RED LINE, never a traceback.

    ⚠️ `detail` MAY BE A CALLABLE, AND OFTEN MUST BE. A plain string argument is
    evaluated BEFORE `fn()` runs, so any detail computed from state the predicate
    sets is stale — r49's N8 printed "no fire-then-return" on a FAILING check,
    which is the diagnostic saying the opposite of the truth. Pass a lambda to
    have it rendered AFTER the predicate.
    """
    try:
        ok = fn()
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"{type(exc).__name__}: {exc}")
        return False
    try:
        det = detail() if callable(detail) else detail
    except Exception:                                           # noqa: BLE001
        det = ""
    check(name, ok, det)
    return ok


def run(db, *args):
    r = subprocess.run([PY if os.path.exists(PY) else sys.executable, TOOL, "--db", db, *args],
                       capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout + r.stderr


def seed(db, rows):
    c = sqlite3.connect(db)
    c.execute("""CREATE TABLE IF NOT EXISTS plan_tick
                 (ts_epoch REAL, symbol TEXT, strategy TEXT, verdict TEXT,
                  reason TEXT, trigger_price REAL, invalidation TEXT,
                  underlying REAL, dist_to_trigger REAL, r_now REAL)""")
    for ts, s, v, why in rows:
        c.execute("INSERT INTO plan_tick(ts_epoch,symbol,strategy,verdict,reason)"
                  " VALUES(?,?,?,?,?)", (ts, "TST", s, v, why))
    c.commit()
    c.close()


def main():
    import time
    now = time.time()
    d = tempfile.mkdtemp()
    db = os.path.join(d, "derived.db")

    # NEWEST row per strategy is the status; older ones must be ignored
    seed(db, [
        (now - 9000, "ORBStrategy", "INACTIVE", "inactive — window: outside 09:35-11:30"),
        (now - 60, "ORBStrategy", "ARMED", "break confirmed, waiting on retest"),
        (now - 30, "TrendCreditSpread", "INACTIVE", "inactive — window: outside 11:30-15:00"),
        (now - 45, "SweepCreditSpread", "NO PLAN", "asked and wrote nothing"),
        (now - 20, "ORBStrategy/manage", "INACTIVE", "no open position"),
    ])
    rc, out = run(db)
    guard("B1 the board runs and exits clean", lambda: rc == 0, f"rc={rc}")
    guard("B2 an ACTIVE plan reports its working verdict, not 'inactive'",
          lambda: "ORBStrategy" in out and "active" in out.split("ORBStrategy")[1].split("\n")[0],
          "ARMED must read as active")
    guard("B2b the NEWEST row wins — a stale INACTIVE must not shadow it",
          lambda: "outside 09:35-11:30" not in out,
          "the 9000s-old row for the same strategy is ignored")
    guard("B3 an INACTIVE plan names its gate",
          lambda: "outside 11:30-15:00" in out)
    guard("B3b a NO PLAN row is flagged as a DEFECT, never as a status",
          lambda: "DEFECT" in out, "asked-and-silent is a dispatch gap")
    guard("B4 /manage plans are hidden by default and shown with --all",
          lambda: "ORBStrategy/manage" not in out
          and "ORBStrategy/manage" in run(db, "--all")[1])

    # ── B5 — A READER WRITES NOTHING ───────────────────────────────────────
    def wrote_nothing():
        c = sqlite3.connect(db)
        before = c.execute("SELECT COUNT(*) FROM plan_tick").fetchone()[0]
        c.close()
        run(db)
        run(db, "--all")
        c = sqlite3.connect(db)
        after = c.execute("SELECT COUNT(*) FROM plan_tick").fetchone()[0]
        c.close()
        return before == after
    guard("B5 the board WRITES NOTHING — row count unchanged across runs",
          wrote_nothing, "a reader that writes is the check_standing_offer S5 class")

    # ── B6/B7 — it fails gracefully rather than tracebacking ───────────────
    empty = os.path.join(tempfile.mkdtemp(), "empty.db")
    seed(empty, [])
    rc2, out2 = run(empty)
    guard("B6 an EMPTY plan_tick says so and exits 0, never a traceback",
          lambda: rc2 == 0 and "empty" in out2.lower() and "Traceback" not in out2,
          out2.strip()[:44])
    rc3, out3 = run(os.path.join(d, "nope.db"))
    guard("B7 a MISSING store says so and exits non-zero, never a traceback",
          lambda: rc3 != 0 and "Traceback" not in out3, out3.strip()[:44])

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
