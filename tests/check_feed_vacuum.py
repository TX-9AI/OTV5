#!/usr/bin/env python3
"""tests/check_feed_vacuum.py — v5.0
v5.0  2026-11-16  OTV5 r130 (VAC.1) — THE NIGHTLY VACUUM RUNS ONLY ON A QUIET BOX, INSIDE A BOUND, AND LEAVES THE STORE
      AS IT WAS WHEN IT DOES NOT FINISH. AMD 2026-11-16: feed_store.db 1.83 GB with 52% of its pages free after the
      11-13 close, whose purge the conductor killed at its 900 s per-box timeout before the vacuum had finished, and
      the verdict was written only to a tmpfs file the halt erased. The operator, 2026-11-16: "Yes, build it".
      EXECUTED against real WAL stores and a real second process, not by reading source (except F11, said so).

F1   no vacuum inside the weekday 08:00-16:00 ET day (boot + RTH); after 16:00 and on weekends it may run
F2   a running writer unit blocks it, and so does not being able to tell (fail closed)
F2b  _units_active reads `systemctl is-active` output per unit; an error or a short answer is None
F3   another PROCESS holding the store open blocks it (real /proc); this process's own connection does not
F4   reclaim() with a blocked store skips, says why, and leaves the file byte-for-byte as it was
F5   reclaim() on a quiet store vacuums and the file shrinks (the behaviour this revision exists for)
F6   a vacuum past its bound is interrupted and ROLLED BACK: same pages, same rows, integrity ok, WAL returned
F7   a vacuum estimated not to finish before the purge's bound is not started
F8   the disk check comes first: a store that cannot fit is REFUSED before the writer check runs
F9   a vacuum that fails (another process holds a write lock) reports FAILED, the file still exists and is unchanged
F10  each verdict is appended to the box's own logs/reclaim.log by purge()
F11  no env key or config toggle: the r130 constants are literals, and the bound ends before the conductor's 900 s
F12  reclaim()'s default gate is the real _vacuum_blocked (wired, not a stub)
"""
import ast
import hashlib
import os
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


def _store(d, rows=6000, keep_from=4000):
    """A WAL feed store with free pages (a contiguous delete, as the purge leaves it). Closed on return."""
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "feed_store.db")
    c = sqlite3.connect(p)
    c.execute("pragma journal_mode=WAL")
    c.execute("create table quote_series(streamer_symbol text, ts_epoch real, v text)")
    c.executemany("insert into quote_series values(?,?,?)",
                  [("Q", float(i), "z" * 400) for i in range(rows)])
    c.commit()
    c.execute("delete from quote_series where rowid < ?", (keep_from,))
    c.commit()
    c.execute("pragma wal_checkpoint(TRUNCATE)")
    c.close()
    return p


def _pages(p):
    c = sqlite3.connect("file:%s?mode=ro" % p, uri=True)
    try:
        g = lambda q: c.execute("pragma " + q).fetchone()[0]
        return (g("page_count"), g("freelist_count"),
                c.execute("select count(*), sum(ts_epoch) from quote_series").fetchone(),
                g("integrity_check"))
    finally:
        c.close()


def _sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _et(y, m, d, hh, mm):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime(y, m, d, hh, mm, tzinfo=ZoneInfo("America/New_York"))


def _quiet(_p):
    return None


def main():
    try:
        from warehouse import retention_purge as rp
    except Exception as exc:                                    # noqa: BLE001
        check("F0 retention_purge is importable", False, f"{type(exc).__name__}: {exc}")
        print("\nRED — 1 failed: F0")
        return 1
    need = ("_vacuum_blocked", "_vacuum_day", "_units_active", "_holders", "_vacuum_bounded",
            "_vacuum_budget", "VACUUM_RUN_LIMIT_S", "VACUUM_MAX_S", "VACUUM_RATE_MBS")
    missing = [n for n in need if not hasattr(rp, n)]
    if missing:
        check("F0 retention_purge carries the r130 vacuum gate", False, "absent: " + ", ".join(missing))
        print(f"\nRED — 1 failed: F0 (r130 has not landed in this checkout)")
        return 1
    os.environ["OT_VACUUM_MIN_FREE_MB"] = "1"   # the pre-existing floor, through its real path (check_purge_reclaim)
    none = lambda: []                            # no writer unit running
    nobody = lambda _p: []                       # no other holder

    # ── F1 — the trading day ──────────────────────────────────────────────
    cases = [(_et(2026, 11, 16, 9, 15), True), (_et(2026, 11, 16, 8, 0), True), (_et(2026, 11, 16, 15, 59), True),
             (_et(2026, 11, 16, 7, 59), False), (_et(2026, 11, 16, 16, 0), False), (_et(2026, 11, 16, 16, 20), False),
             (_et(2026, 11, 14, 10, 0), False), (_et(2026, 11, 15, 9, 15), False)]
    got = [(c.strftime("%a %H:%M"), rp._vacuum_blocked("/x", now_et=c, units=none, holders=nobody) is not None)
           for c, _ in cases]
    check("F1 blocked weekdays 08:00-16:00 ET, open after 16:00 and on weekends",
          [b for _, b in got] == [w for _, w in cases], str(got))
    night = _et(2026, 11, 16, 16, 20)

    # ── F2 — writer units ────────────────────────────────────────────────
    r_up = rp._vacuum_blocked("/x", now_et=night, units=lambda: ["optionsbot"], holders=nobody)
    r_unknown = rp._vacuum_blocked("/x", now_et=night, units=lambda: None, holders=nobody)
    r_ok = rp._vacuum_blocked("/x", now_et=night, units=none, holders=nobody)
    check("F2 a running unit blocks, an unknown state blocks, stopped units pass",
          bool(r_up) and "optionsbot" in r_up and bool(r_unknown) and r_ok is None,
          f"{r_up!r} / {r_unknown!r} / {r_ok!r}")

    class _R:
        def __init__(self, out):
            self.stdout = out

    def _raise(*_a, **_k):
        raise FileNotFoundError("systemctl")
    p_a = rp._units_active(run=lambda *a, **k: _R("active\ninactive\n"))
    p_b = rp._units_active(run=lambda *a, **k: _R("inactive\nfailed\n"))
    p_c = rp._units_active(run=_raise)
    p_d = rp._units_active(run=lambda *a, **k: _R("inactive\n"))
    p_e = rp._units_active(run=lambda *a, **k: _R("inactive\nactivating\n"))
    check("F2b systemctl is-active parsed per unit; error or short answer -> None",
          p_a == ["optionsbot"] and p_b == [] and p_c is None and p_d is None and p_e == ["candle-feed"],
          f"{p_a} {p_b} {p_c} {p_d} {p_e}")

    with tempfile.TemporaryDirectory() as tmp:
        # ── F3 — a real second process ───────────────────────────────────
        p = _store(os.path.join(tmp, "f3", "data"))
        own = sqlite3.connect(p)                 # this process's own connection is not a holder
        own.execute("select 1").fetchone()
        child = subprocess.Popen([sys.executable, "-c",
                                  "import sqlite3,sys,time; c=sqlite3.connect(sys.argv[1]);"
                                  "c.execute('select count(*) from quote_series').fetchone();"
                                  "print('up', flush=True); time.sleep(60)", p],
                                 stdout=subprocess.PIPE, text=True)
        try:
            child.stdout.readline()
            held = rp._holders(p)
            by_gate = rp._vacuum_blocked(p, now_et=night, units=none)
        finally:
            child.kill()
            child.wait()
        after = rp._holders(p)
        own.close()
        check("F3 another process holding the store blocks it; our own connection does not",
              any(h.startswith(str(child.pid) + " ") for h in held) and by_gate and "held open" in by_gate
              and after == [], f"held={held} gate={by_gate!r} after={after}")

        # ── F4 — reclaim with a blocked store leaves it as it was ────────
        p = _store(os.path.join(tmp, "f4", "data"))
        h0, s0 = _sha(p), os.path.getsize(p)
        v = rp.reclaim([p], apply=True, blocked=lambda _p: "optionsbot still running")["feed_store.db"]
        check("F4 a blocked store is skipped with the reason, file byte-identical",
              "vacuum skipped: optionsbot still running" in v and _sha(p) == h0 and os.path.getsize(p) == s0, v)

        # ── F5 — a quiet store is vacuumed ───────────────────────────────
        p = _store(os.path.join(tmp, "f5", "data"))
        pc0, fl0, rows0, _ = _pages(p)
        v = rp.reclaim([p], apply=True, blocked=_quiet)["feed_store.db"]
        pc1, fl1, rows1, ok1 = _pages(p)
        check("F5 a quiet store is vacuumed: free pages gone, rows kept",
              v.count("vacuumed in") == 1 and fl0 > 100 and fl1 == 0 and pc1 < pc0 and rows1 == rows0 and ok1 == "ok",
              f"{pc0}/{fl0} -> {pc1}/{fl1} | {v}")

        # ── F6 — the bound interrupts and rolls back ─────────────────────
        p = _store(os.path.join(tmp, "f6", "data"), rows=20000, keep_from=10000)
        before = _pages(p)
        v = rp._vacuum_bounded(p, 0.0)
        after6 = _pages(p)
        wal = os.path.getsize(p + "-wal") if os.path.exists(p + "-wal") else 0
        check("F6 past its bound the vacuum is interrupted and rolled back; store unchanged, WAL returned",
              "STOPPED" in v and after6 == before and after6[3] == "ok" and wal == 0,
              f"{before[:3]} -> {after6[:3]} wal={wal} | {v}")

        # ── F7 — not started when it cannot finish ───────────────────────
        p = _store(os.path.join(tmp, "f7", "data"))
        h0 = _sha(p)
        saved = rp._T0
        rp._T0 = time.monotonic() - (rp.VACUUM_RUN_LIMIT_S - 0.001)
        try:
            v = rp.reclaim([p], apply=True, blocked=_quiet)["feed_store.db"]
        finally:
            rp._T0 = saved
        b, e = rp._vacuum_budget(400 * 1048576, now_mono=rp._T0 + 100)
        check("F7 a vacuum that cannot finish before the purge's bound is not started",
              "vacuum skipped" in v and "estimated" in v and _sha(p) == h0
              and b == min(float(rp.VACUUM_MAX_S), rp.VACUUM_RUN_LIMIT_S - 100) and abs(e - 400 / rp.VACUUM_RATE_MBS) < 1e-6,
              f"{v} | budget={b} est={e:.1f}")

        # ── F8 — disk first ──────────────────────────────────────────────
        p = _store(os.path.join(tmp, "f8", "data"))
        calls = []

        class _Tiny:
            f_bavail = 1
            f_frsize = 4096
        real = os.statvfs
        os.statvfs = lambda _p: _Tiny()
        try:
            v = rp.reclaim([p], apply=True, blocked=lambda q: calls.append(q))["feed_store.db"]
        finally:
            os.statvfs = real
        check("F8 not enough free disk -> REFUSED with the arithmetic, before the writer check",
              "vacuum REFUSED: needs" in v and calls == [], f"{v} | writer-check calls={len(calls)}")

        # ── F9 — a failing vacuum reports and changes nothing ────────────
        p = _store(os.path.join(tmp, "f9", "data"))
        h0 = _sha(p)
        locker = subprocess.Popen([sys.executable, "-c",
                                   "import sqlite3,sys,time; c=sqlite3.connect(sys.argv[1], isolation_level=None);"
                                   "c.execute('begin exclusive'); print('locked', flush=True); time.sleep(60)", p],
                                  stdout=subprocess.PIPE, text=True)
        try:
            locker.stdout.readline()
            t = time.monotonic()
            v = rp._vacuum_bounded(p, 60.0)
            dt = time.monotonic() - t
        finally:
            locker.kill()
            locker.wait()
        check("F9 a vacuum that cannot lock reports FAILED quickly; the file still exists and is unchanged",
              "vacuum FAILED" in v and os.path.exists(p) and _sha(p) == h0 and dt < 30, f"{dt:.1f}s | {v}")

        # ── F10 — the box keeps its own record ───────────────────────────
        box = os.path.join(tmp, "f10")
        feed = _store(os.path.join(box, "data"))
        derived = os.path.join(box, "data", "derived_store.db")
        saved_b = rp._vacuum_blocked
        rp._vacuum_blocked = _quiet
        try:
            rp.purge(apply=True, feed_db=feed, derived_db=derived)
        finally:
            rp._vacuum_blocked = saved_b
        log = os.path.join(box, "logs", "reclaim.log")
        text = open(log, encoding="utf-8").read() if os.path.exists(log) else ""
        check("F10 purge() appends the feed store's verdict to <box>/logs/reclaim.log",
              " feed_store.db " in text and "vacuumed in" in text, text.strip()[:200])

    # ── F11 — constants, not knobs (source, parsed) ───────────────────────
    src = open(os.path.join(ROOT, "warehouse", "retention_purge.py"), encoding="utf-8").read()
    consts = {}
    for n in ast.parse(src).body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            consts[n.targets[0].id] = n.value
    names = ("VACUUM_DAY_ET", "VACUUM_WRITER_UNITS", "VACUUM_RUN_LIMIT_S", "VACUUM_MAX_S", "VACUUM_RATE_MBS")
    lit = all(nm in consts and isinstance(consts[nm], (ast.Constant, ast.Tuple))
              and all(isinstance(x, ast.Constant) for x in ast.walk(consts[nm]) if isinstance(x, ast.expr)
                      and not isinstance(x, ast.Tuple)) for nm in names)
    check("F11 the r130 constants are literals (no env key, no toggle), and the bound ends before 900 s",
          lit and rp.VACUUM_RUN_LIMIT_S < 900 and rp.VACUUM_MAX_S <= rp.VACUUM_RUN_LIMIT_S
          and tuple(rp.VACUUM_WRITER_UNITS) == ("optionsbot", "candle-feed"),
          f"literal={lit} limit={rp.VACUUM_RUN_LIMIT_S} max={rp.VACUUM_MAX_S}")

    # ── F12 — the real gate is the default ────────────────────────────────
    seen = []
    saved_b = rp._vacuum_blocked
    rp._vacuum_blocked = lambda q: (seen.append(q), "recorded")[1]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            p = _store(os.path.join(tmp, "data"))
            v = rp.reclaim([p], apply=True)["feed_store.db"]
    finally:
        rp._vacuum_blocked = saved_b
    check("F12 reclaim() without a gate argument consults _vacuum_blocked",
          seen == [p] and "vacuum skipped: recorded" in v, v)

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 13 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
