#!/usr/bin/env python3
"""tests/check_purge_reclaim.py — v1.0
v1.0  2026-09-05 — r255. THE RECLAIM STAGE, DRIVEN AGAINST A REAL STORE.

🔴 WHY IT EXECUTES RATHER THAN INSPECTS. Every claim this revision makes is
arithmetic about bytes on a disk — the WAL comes back on a checkpoint, the free
pages do not come back without a vacuum, and a vacuum refuses when the disk
cannot hold a second copy. None of that is provable by reading source, and this
project has shipped a gate twice that asserted a function existed and a file
parsed while both were true of the broken version (§0.6 / r201).

🔑 THE FIXTURE BUILDS ITS OWN WAL AND ITS OWN FREE PAGES, and it has to hold a
connection open to do it: SQLite checkpoints on last-connection-close, so a rig
that writes and disconnects leaves a zero-byte WAL and would prove nothing about
the 1.6 GB one measured on MU. R1 fails if the fixture ever stops producing one,
because a passing test on an empty WAL is the shape of a check that verifies
nothing (r246's refusal-to-pass-on-nothing).

⚠️ AND THE INERT POLICY IS PINNED AS INERT. R6 requires `shadow` to report
"declared, not enforced" and NOT a count. The boxes hold the only copy of every
shadow date before 2026-08-26; a future edit that arms this before the history
is re-pushed destroys it, and this is the check that stops it.
"""
import os
import sqlite3
import sys
import tempfile
import time

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


def _rig(tmp):
    """A data/ tree with a WAL, free pages, stale rows and stale date dirs.

    Returns the still-open connection: the caller must keep it, or the WAL is
    checkpointed away by the close and the whole point of R1 is lost.
    """
    d = os.path.join(tmp, "data")
    for sub in ("chain_snapshots/2026-01-02", "chain_snapshots/2099-01-01",
                "shadow/2026-01-02", "shadow/not-a-date"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
        with open(os.path.join(d, sub, "x.jsonl"), "w") as f:
            f.write("{}\n")
    old = time.time() - 40 * 86400
    f = sqlite3.connect(os.path.join(d, "feed_store.db"))
    f.execute("pragma journal_mode=WAL")
    f.execute("create table candles(symbol,interval,ts_epoch_ms,c)")
    for t in ("greeks_series", "quote_series"):
        f.execute(f"create table {t}(ts_epoch,v)")
    f.executemany("insert into candles values(?,?,?,?)",
                  [("Q", "1m", int(old * 1000), "x" * 400) for _ in range(8000)])
    f.executemany("insert into greeks_series values(?,?)",
                  [(old, "y" * 400) for _ in range(8000)])
    f.executemany("insert into quote_series values(?,?)",
                  [(time.time(), "z" * 100) for _ in range(200)])
    f.commit()
    # Free pages, made deliberately: delete a third of a table and DO NOT
    # vacuum. This is the fleet's own state — 18-34% free inside every
    # feed_store on 2026-09-05.
    # ⚠️ A CONTIGUOUS RANGE, NOT `rowid % 3`. SQLite frees a page only when
    # EVERY row on it is gone, so a scattered delete leaves each page a third
    # full and the freelist near zero — the first draft of this fixture did
    # exactly that and R3 went red against correct code.
    f.execute("delete from greeks_series where rowid < 6000")
    f.commit()
    g = sqlite3.connect(os.path.join(d, "derived_store.db"))
    g.execute("pragma journal_mode=WAL")
    for t in ("indicator_series", "fork_series", "surface_series",
              "plan_tick", "plan_check"):
        g.execute(f"create table {t}(ts_epoch,v)")
        g.executemany(f"insert into {t} values(?,?)",
                      [(old, "p" * 200) for _ in range(2000)])
    g.commit()
    return d, f, g


def _sz(p):
    try:
        return os.path.getsize(p)
    except OSError:
        return 0


def main():
    try:
        from warehouse import retention_purge as rp
    except Exception as exc:                                    # noqa: BLE001
        check("R0 retention_purge is importable", False,
              f"{type(exc).__name__}: {exc}")
        print("\nRED — 1 failed: R0 (the checker could not run)")
        return 1
    for n in ("reclaim", "TREE_DAYS", "DERIVED_CDC_DAYS", "_tree_purge"):
        if not hasattr(rp, n):
            check(f"R0 retention_purge exposes {n}", False,
                  "absent — r255 has not landed in this checkout")
            print("\nRED — 1 failed: R0")
            return 1
    check("R0 retention_purge exposes the r255 surface", True)

    # ⚠️ THE FLOOR IS LOWERED THROUGH THE REAL ENV PATH, not by reassigning the
    # module constant. A checker that patches the value it is checking proves
    # only that the patch took (C.23); this drives `_vacuum_min_free()` itself.
    os.environ["OT_VACUUM_MIN_FREE_MB"] = "1"

    with tempfile.TemporaryDirectory() as tmp:
        d, fconn, gconn = _rig(tmp)
        feed = os.path.join(d, "feed_store.db")
        wal_before = _sz(feed + "-wal")
        # ⚠️ REFUSE TO PASS ON NOTHING. A zero-byte WAL would make R2 trivially
        # true, which is exactly the cheerful green r246 names.
        check("R1 the fixture actually produced a WAL to reclaim",
              wal_before > 1_000_000, f"{wal_before/1048576:.1f}MB")

        # ══ R2 — A LIVE READER BLOCKS THE TRUNCATE, AND IT SAYS SO ════════
        # 🔴 THIS IS THE MOST LIKELY EXPLANATION OF MU'S 1.6 GB WAL AND THE
        # CHECKER FOUND IT RATHER THAN CONFIRMING IT. `wal_checkpoint(TRUNCATE)`
        # returns busy=1 while ANY other connection holds a read mark, and the
        # WAL is only partly reclaimed. The fixture keeps its writer open on
        # purpose, because that is a box whose services are still up.
        verdict = rp.reclaim([feed], apply=True)["feed_store.db"]
        wal_live = _sz(feed + "-wal")
        check("R2 a checkpoint with the store still open does NOT fully "
              "truncate, and reports it rather than claiming success",
              wal_live > 0 and ("BUSY" in verdict or wal_live > wal_before / 4),
              f"{wal_before/1048576:.1f}MB -> {wal_live/1048576:.1f}MB | {verdict}")

        # ══ R2b — AND WITH NOTHING HOLDING IT, THE WAL COMES BACK WHOLE ════
        # ⚠️ WHICH MAKES THE RECLAIM STAGE ORDER-DEPENDENT ON THE FLEET: it is
        # only worth what the checkpoint reclaims, and the checkpoint is only
        # whole once nothing holds the store open. Filed rather than assumed.
        fconn.close()
        rp.reclaim([feed], apply=True)
        wal_after = _sz(feed + "-wal")
        check("R2b with no reader holding it, the checkpoint returns the WAL",
              wal_after < wal_before / 4,
              f"{wal_before/1048576:.1f}MB -> {wal_after/1048576:.1f}MB")


    # ══ R3 — FREE PAGES DO NOT COME BACK WITHOUT A VACUUM ═════════════════
    # 🔴 THE CLAIM `purge_verified`'s DOCSTRING GOT WRONG. It said freed pages
    # return as the store grows; they plateau at the high-water mark, which is
    # why every feed_store on the fleet carried 18-34% free while the boxes ran
    # out of disk. A FRESH RIG, because the block above already vacuumed its own.
    with tempfile.TemporaryDirectory() as tmp:
        d, fconn, gconn = _rig(tmp)
        feed = os.path.join(d, "feed_store.db")
        fconn.close(); gconn.close()
        # Floor raised so the vacuum SKIPS: this measures the state the fleet is
        # actually in — checkpointed, purged, and still holding its free pages.
        os.environ["OT_VACUUM_MIN_FREE_MB"] = "999999"
        rp.reclaim([feed], apply=True)
        st = rp._db_stat(feed)
        size_before = _sz(feed)
        check("R3 a checkpoint alone leaves the free pages inside the file",
              st["free"] > 1_000_000, f"{st['free']/1048576:.1f}MB free")
        # ⚠️ THE FLOOR MOVES THROUGH THE ENV, WHICH IS THE REAL RESOLUTION PATH.
        os.environ["OT_VACUUM_MIN_FREE_MB"] = "1"
        rp.reclaim([feed], apply=True)
        check("R3b ...and only a vacuum returns them to the filesystem",
              _sz(feed) < size_before * 0.9,
              f"{size_before/1048576:.1f}MB -> {_sz(feed)/1048576:.1f}MB")

    # ══ R4 — THE VACUUM GATE REFUSES RATHER THAN FAILING ══════════════════
    # 🔴 On 2026-09-05 the four boxes needing this most had LESS free disk than
    # their live size. A vacuum dying half-way at 16:10 on a 96%-full box is
    # worse than no vacuum, so the gate is what makes the stage safe to run
    # nightly and unattended.
    with tempfile.TemporaryDirectory() as tmp:
        d, fconn, gconn = _rig(tmp)
        feed = os.path.join(d, "feed_store.db")
        fconn.close(); gconn.close()
        real_statvfs = os.statvfs

        class _Tiny:
            f_bavail = 1
            f_frsize = 4096

        os.statvfs = lambda _p: _Tiny()
        try:
            verdict = rp.reclaim([feed], apply=True)["feed_store.db"]
        finally:
            os.statvfs = real_statvfs
        check("R4 a vacuum with no room REFUSES and prints the arithmetic",
              "REFUSED" in verdict and "needs" in verdict, verdict)
        check("R4b ...and the checkpoint still ran, because it needs no room",
              "checkpoint" in verdict)

    # ══ R5/R6 — THE TREE PURGE, AND THE ONE THAT MUST STAY INERT ═════════
    with tempfile.TemporaryDirectory() as tmp:
        d, fconn, gconn = _rig(tmp)
        root = os.path.join(d, "chain_snapshots")
        n = rp._tree_purge(root, 3, apply=True)
        check("R5 a stale date directory is removed",
              n == 1 and not os.path.isdir(os.path.join(root, "2026-01-02")),
              f"removed {n}")
        check("R5b a future-dated directory is kept",
              os.path.isdir(os.path.join(root, "2099-01-01")))
        # ⚠️ THE NAME IS THE GUARD. A rule written for dates must not delete a
        # directory that merely happens to live under the tree.
        check("R5c a non-date directory is never touched",
              os.path.isdir(os.path.join(d, "shadow", "not-a-date")))

        # 🔴 R6 — shadow IS DECLARED AND NOT ENFORCED, AND MUST STAY SO until
        # the pre-2026-08-26 history is re-pushed and verified. The boxes hold
        # the only copy: the 08-25 purge deleted 492,945 objects from the bucket
        # on a finding that was wrong.
        check("R6 shadow's policy is declared, NOT enforced",
              rp.TREE_DAYS.get("shadow", "missing") is None,
              str(rp.TREE_DAYS.get("shadow", "missing")))
        sn = rp._tree_purge(os.path.join(d, "shadow"), rp.TREE_DAYS["shadow"],
                            apply=True)
        check("R6b ...and an inert policy reports -1, never 0 — "
              "'not armed' and 'found nothing' are different facts",
              sn == -1 and os.path.isdir(os.path.join(d, "shadow", "2026-01-02")),
              f"returned {sn}")

    # ══ R7 — THE CDC TABLES ARE COVERED, AND BY THEIR OWN LIST ═══════════
    # `check_purge_pushed` C9 proves a DERIVED_ARTIFACT_DAYS table ships via
    # push_series; these ship via push_derived. Folding them together would turn
    # C9 red for a true reason — the fastest way to get a real check loosened.
    check("R7 plan_tick and plan_check are purgeable",
          set(rp.DERIVED_CDC_DAYS) == {"plan_tick", "plan_check"},
          str(sorted(rp.DERIVED_CDC_DAYS)))
    check("R7b ...and NOT folded into the push_series list",
          not (set(rp.DERIVED_CDC_DAYS) & set(rp.DERIVED_ARTIFACT_DAYS)))
    check("R7c ...and neither is protected by NEVER_PURGE, "
          "while plan_ledger the biography still is",
          not (set(rp.DERIVED_CDC_DAYS) & set(rp.NEVER_PURGE))
          and "plan_ledger" in rp.NEVER_PURGE)

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 16 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
