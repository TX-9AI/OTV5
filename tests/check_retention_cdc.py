#!/usr/bin/env python3
"""tests/check_retention_cdc.py — v5.0
v5.0  2026-11-07  OTV5 RET.2 — THE BOX KEEPS 14 DAYS OF PLAN ROWS AND 30 OF NOTES, AND PRUNES ONLY WHAT S3 CONFIRMED.
The operator, 2026-11-07: "Yes to all of your proposed disk size fixes" (SOFI 87.8%, derived_store.db +31% a week).
EXECUTED against a real derived store and a real CDC ledger (s3_push.DerivedLedger's own schema), not by reading.

  P1  policy: plan_tick / plan_check 14 days, strategy_note 30; strategy_note is not NEVER_PURGE; the other
      biographies (plan_ledger, fire_snapshot, gate_disposition, character_ledger, level_ledger, level_event) still are
  P2  no env key and no configure.sh item sets the CDC windows (defaults live in code)
  C1  apply: old rows the ledger confirmed are deleted; rows inside the window are kept
  C2  apply: an old row the ledger has NO hash for is kept, and so is every old row above it (the clamp)
  C3  a box that pushes and has NO ledger deletes nothing from the CDC tables
  C4  a box that provably never pushes is age-only (its unshipped old rows go)
  C5  dry run counts exactly what apply then deletes, and deletes nothing itself
  C6  plan_ledger (NEVER_PURGE) is untouched at any age

Run:  python3 tests/check_retention_cdc.py
"""
import importlib.util
import os
import re
import sqlite3
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(("  ✅ " if ok else "  ❌ ") + name + ("" if ok else "  — " + str(detail)))
    if not ok:
        FAILED.append(name.split()[0])


def load_rp(state_dir):
    os.environ["OT_WAREHOUSE_STATE"] = state_dir
    spec = importlib.util.spec_from_file_location("rp_cdc", os.path.join(ROOT, "warehouse", "retention_purge.py"))
    rp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rp)
    rp._log = lambda m: None
    return rp


DAY = 86400.0
NOW = time.time()


def build(tmp, shipped_rids_by_table, ledger=True):
    """A derived store: per CDC table, rows at ages 40, 35, 20, 16, 5, 1 days; plan_ledger rows at 200 days."""
    db = os.path.join(tmp, "derived_store.db")
    c = sqlite3.connect(db)
    for t in ("plan_tick", "plan_check", "strategy_note"):
        c.execute(f"CREATE TABLE {t} (ts_epoch REAL NOT NULL, symbol TEXT, payload TEXT)")
        for age in (40, 35, 20, 16, 5, 1):
            c.execute(f"INSERT INTO {t} VALUES (?,?,?)", (NOW - age * DAY, "SOFI", "x"))
    c.execute("CREATE TABLE plan_ledger (ts_epoch REAL NOT NULL, symbol TEXT, state TEXT)")
    c.execute("INSERT INTO plan_ledger VALUES (?,?,?)", (NOW - 200 * DAY, "SOFI", "DONE"))
    c.commit()
    c.close()
    if ledger:
        lc = sqlite3.connect(os.path.join(tmp, "derived_ledger.db"))
        lc.execute("CREATE TABLE IF NOT EXISTS seen (tbl TEXT NOT NULL, rid INTEGER NOT NULL, "
                   "sha BLOB NOT NULL, PRIMARY KEY (tbl, rid)) WITHOUT ROWID")
        for t, rids in shipped_rids_by_table.items():
            lc.executemany("INSERT INTO seen VALUES (?,?,?)", [(t, r, b"\x00" * 16) for r in rids])
        lc.commit()
        lc.close()
    return db


def ages(db, t):
    c = sqlite3.connect(db)
    out = sorted(round((NOW - r[0]) / DAY) for r in c.execute(f"SELECT ts_epoch FROM {t}"))
    c.close()
    return out


def run(tmp, rp, apply):
    return rp.purge(apply=apply, feed_db=os.path.join(tmp, "absent_feed.db"),
                    derived_db=os.path.join(tmp, "derived_store.db"))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        rp = load_rp(tmp)
        rp._box_never_pushes = lambda: (False, "")
        d = rp.DERIVED_CDC_DAYS
        check("P1 plan_tick/plan_check 14 days, strategy_note 30",
              d.get("plan_tick") == 14 and d.get("plan_check") == 14 and d.get("strategy_note") == 30, d)
        bios = {"plan_ledger", "fire_snapshot", "gate_disposition", "character_ledger", "level_ledger",
                "level_event"}
        check("P1b strategy_note left NEVER_PURGE; the other biographies did not",
              "strategy_note" not in rp.NEVER_PURGE and bios <= set(rp.NEVER_PURGE),
              sorted(rp.NEVER_PURGE))
        src = open(os.path.join(ROOT, "warehouse", "retention_purge.py"), encoding="utf-8").read()
        blk = src[src.find("DERIVED_CDC_DAYS = {"):]
        blk = blk[:blk.find("}") + 1]
        conf = open(os.path.join(ROOT, "configure.sh"), encoding="utf-8").read()
        check("P2 the CDC windows are constants: no env read in the block, no configure.sh item",
              "environ" not in blk and not re.search(r"CDC_DAYS|STRATEGY_NOTE_DAYS|PLAN_CHECK_DAYS", conf), blk)

        # every table: rowids 1..6 at ages 40,35,20,16,5,1. strategy_note ships 1..6; plan_tick ships all;
        # plan_check ships 1, 3, 4 (rid 2, age 35, is NOT confirmed).
        db = build(tmp, {"plan_tick": range(1, 7), "plan_check": [1, 3, 4, 5, 6], "strategy_note": range(1, 7)})
        dry = run(tmp, rp, apply=False)
        check("C5 dry run deletes nothing", ages(db, "plan_tick") == [1, 5, 16, 20, 35, 40],
              ages(db, "plan_tick"))
        got = run(tmp, rp, apply=True)
        check("C1 confirmed plan_tick rows past 14 days go; the window stays",
              ages(db, "plan_tick") == [1, 5], ages(db, "plan_tick"))
        check("C1b strategy_note keeps 30 days: 40 and 35 go, 20 and 16 stay",
              ages(db, "strategy_note") == [1, 5, 16, 20], ages(db, "strategy_note"))
        check("C2 plan_check stops below its first unshipped row (rid 2): only rid 1 goes",
              ages(db, "plan_check") == [1, 5, 16, 20, 35], ages(db, "plan_check"))
        check("C5b the dry count equals what apply deleted",
              all(dry.get(f"derived/{t}") == got.get(f"derived/{t}")
                  for t in ("plan_tick", "plan_check", "strategy_note")),
              {k: (dry.get(k), got.get(k)) for k in dry if k.startswith("derived/")})
        check("C6 plan_ledger (NEVER_PURGE) untouched at 200 days", ages(db, "plan_ledger") == [200],
              ages(db, "plan_ledger"))

    with tempfile.TemporaryDirectory() as tmp:
        rp = load_rp(tmp)
        rp._box_never_pushes = lambda: (False, "")
        db = build(tmp, {}, ledger=False)
        run(tmp, rp, apply=True)
        check("C3 a pushing box with no CDC ledger deletes nothing from the CDC tables",
              all(ages(db, t) == [1, 5, 16, 20, 35, 40] for t in ("plan_tick", "plan_check", "strategy_note")),
              {t: ages(db, t) for t in ("plan_tick", "plan_check", "strategy_note")})

    with tempfile.TemporaryDirectory() as tmp:
        rp = load_rp(tmp)
        rp._box_never_pushes = lambda: (True, "test: never pushes")
        db = build(tmp, {}, ledger=False)
        run(tmp, rp, apply=True)
        check("C4 a never-push box is age-only",
              ages(db, "plan_tick") == [1, 5] and ages(db, "strategy_note") == [1, 5, 16, 20],
              {t: ages(db, t) for t in ("plan_tick", "strategy_note")})

    print()
    if FAILED:
        print(f"  RED — {len(FAILED)} of {len(RAN)} failed: " + ", ".join(FAILED))
        sys.exit(1)
    print(f"  GREEN — {len(RAN)} checks")


if __name__ == "__main__":
    main()
