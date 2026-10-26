#!/usr/bin/env python3
"""tests/check_push_memory.py — v5.0
v5.0  2026-10-25  OTV5 r20 (PUSH.1) — THE DERIVED PUSH STAGE RUNS IN BOUNDED MEMORY. The 2026-10-25 fleet field
      test measured the 5-minute push at ~700 MB peak on 951 MB boxes (1.5 GB on SOFI): derived_ledger.json held a
      hash for every row ever pushed (147-177 MB), json-loaded whole each run, and every derived table was read into
      one list.

🔑 IT DRIVES THE REAL push_derived AND DerivedLedger against a planted derived store and an in-memory S3. Every
assertion is about behaviour: what shipped, what the ledger holds, what memory the stage peaked at.

  M1  production never json-loads the derived ledger: main() opens no load_ledger(DERIVED_LEDGER)
  M2  a legacy derived_ledger.json (> 1 MB, so the scan crosses reads) converts to SQLite row for row WITHOUT
      json.load, and the JSON is removed
  M3  continuity: rows the legacy JSON already confirmed are NOT re-shipped after the conversion
  M4  CDC: an unchanged store ships nothing; one mutated row ships one object holding that one row
  M5  batching: 250 changed rows with DERIVED_BATCH_ROWS=100 ship as 3 objects carrying all 250, none over 100
  M6  bounded: a no-change pass over 60,000 rows peaks under 25 MB of Python allocation (tracemalloc)
  M7  pruning: after the purge removes the oldest rows, their ledger entries are gone

Born red on 6dc63e2 (OTV5 r19): M1-M7 (no DerivedLedger; the ledger is a JSON dict loaded whole).
Run:  python3 tests/check_push_memory.py
"""
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import tracemalloc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "warehouse"))

_fails = []


def ck(tag, ok, msg=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {tag}  {msg}")
    if not ok:
        _fails.append(tag)


class FakeS3:
    def __init__(self):
        self.objs = {}

    def put_object(self, Bucket, Key, Body):
        self.objs[Key] = Body

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objs[Key])}

    def rows(self, table):
        out = []
        for k, v in self.objs.items():
            if "/derived_%s/" % table in k:
                out.append(json.loads(v)["record"])
        return out


def plant(path, n, table="plan_tick"):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE %s (k TEXT, state TEXT, pad TEXT, ts_epoch REAL)" % table)
    con.executemany("INSERT INTO %s VALUES (?,?,?,?)" % table,
                    [("k%d" % i, "OPEN", "x" * 60, float(i)) for i in range(n)])
    con.commit()
    con.close()


def main():
    import s3_push as sp
    tmp = tempfile.mkdtemp()
    try:
        src = open(sp.__file__, encoding="utf-8").read()
        main_src = src[src.index("def main("):]
        ck("M1", "load_ledger(DERIVED_LEDGER)" not in main_src and hasattr(sp, "DerivedLedger"),
           "main() does not json-load the derived ledger")
        if not hasattr(sp, "DerivedLedger"):
            for t in ("M2", "M3", "M4", "M5", "M6", "M7"):
                ck(t, False, "no DerivedLedger in this tree")
            return
        sp.DERIVED_TABLES = ("plan_tick",)

        # M2/M3 — a legacy JSON whose hashes match the planted rows
        db = os.path.join(tmp, "derived.db")
        plant(db, 20000)
        con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        con.row_factory = sqlite3.Row
        legacy = {"plan_tick": {str(r["_rid"]): sp._sha256(sp._canon(dict(r)))
                                for r in con.execute("SELECT rowid AS _rid, * FROM plan_tick")},
                  "other_table": {"1": "a" * 64, "2": "b" * 64}}
        con.close()
        jpath = os.path.join(tmp, "derived_ledger.json")
        with open(jpath, "w") as fh:
            json.dump(legacy, fh, separators=(",", ":"))
        big = os.path.getsize(jpath) > (1 << 20)
        real_load = json.load
        json.load = lambda *a, **k: (_ for _ in ()).throw(AssertionError("json.load called"))
        try:
            led = sp.DerivedLedger(os.path.join(tmp, "derived_ledger.db"), legacy_json=jpath)
        finally:
            json.load = real_load
        n = led.con.execute("SELECT COUNT(*) FROM seen").fetchone()[0]
        ck("M2", big and n == 20002 and not os.path.exists(jpath),
           f"converted {n} of 20002 rows from a {os.path.getsize(jpath) if os.path.exists(jpath) else 'removed'} JSON "
           f"(>1MB={big})")
        s3 = FakeS3()
        p, f = sp.push_derived(s3, "b", db, led, "X", counters=None)
        ck("M3", p == 0 and f == 0, f"after conversion pushed={p} (want 0)")

        # M4 — mutate one row
        c = sqlite3.connect(db)
        c.execute("UPDATE plan_tick SET state='DONE' WHERE rowid=7")
        c.commit()
        c.close()
        p, f = sp.push_derived(s3, "b", db, led, "X", counters=None)
        got = s3.rows("plan_tick")
        ck("M4", p == 1 and len(got) == 1 and len(got[0]) == 1 and got[0][0]["_rid"] == 7,
           f"pushed={p} objects={len(got)}")

        # M5 — 250 changes, batch 100
        c = sqlite3.connect(db)
        c.execute("UPDATE plan_tick SET state='X' WHERE rowid BETWEEN 1000 AND 1249")
        c.commit()
        c.close()
        old_b = sp.DERIVED_BATCH_ROWS
        sp.DERIVED_BATCH_ROWS = 100
        s3b = FakeS3()
        try:
            p, f = sp.push_derived(s3b, "b", db, led, "X", counters=None)
        finally:
            sp.DERIVED_BATCH_ROWS = old_b
        objs = s3b.rows("plan_tick")
        rids = sorted(r["_rid"] for o in objs for r in o)
        ck("M5", p == 3 and rids == list(range(1000, 1250)) and max(len(o) for o in objs) <= 100,
           f"objects={p} rows={len(rids)} sizes={[len(o) for o in objs]}")

        # M6 — bounded memory on a no-change pass over 60k rows
        db2 = os.path.join(tmp, "derived2.db")
        plant(db2, 60000)
        led2 = sp.DerivedLedger(os.path.join(tmp, "l2.db"), legacy_json="")
        sp.push_derived(FakeS3(), "b", db2, led2, "X", counters=None)
        tracemalloc.start()
        p, f = sp.push_derived(FakeS3(), "b", db2, led2, "X", counters=None)
        _cur, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        ck("M6", p == 0 and peak < 25 * (1 << 20), f"no-change pass peak {peak / (1 << 20):.1f} MB, pushed={p}")

        # M7 — purge the oldest rows; their ledger entries go
        c = sqlite3.connect(db2)
        c.execute("DELETE FROM plan_tick WHERE rowid <= 30000")
        c.commit()
        c.close()
        sp.push_derived(FakeS3(), "b", db2, led2, "X", counters=None)
        lo, cnt = led2.con.execute("SELECT MIN(rid), COUNT(*) FROM seen WHERE tbl='plan_tick'").fetchone()
        ck("M7", lo == 30001 and cnt == 30000, f"ledger min rid {lo}, rows {cnt}")
        led.close()
        led2.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
    print("FAIL: " + " ".join(_fails) if _fails else "ALL PASS")
    sys.exit(1 if _fails else 0)
