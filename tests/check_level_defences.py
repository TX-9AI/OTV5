#!/usr/bin/env python3
"""
tests/check_level_defences.py  v1.0
v1.0  2026-10-03  OTV4TEST r214 (LVL.18) — A LEVEL'S DEFENCES AND FAILURES ARE COUNTED, AND NOTHING THAT TRADES CAN SEE THEM.

  The operator, 2026-10-03: "a sweep of a level is a successful defense. and
  any level that historically repeats that process is a higher quality level."
  Record-only first: the counts go in NEW level_ledger columns.

  Drives the REAL LevelEngine._record_defences and DerivedStore on a scratch db.
  D1  three HELD events and one TESTED on a level -> defended 3, tested 1,
      failed 0, last_defended_ts = the last HELD bar
  D2  a level that was HELD once and then BREACHED -> defended 1, failed 1
  D3  a ZONE's event credits every member level
  D4  a second sync with the same events rewrites nothing; a new HELD does
  D5  RECORD-ONLY: touch_count and closes_beyond are still 0, and the reader
      plans use (live_levels) returns exactly the keys it did
  D6  _book_sync calls it (a source check, stated as one)

Run:  python3 tests/check_level_defences.py   (exit 0 green, 1 red)
"""
import glob as _glob
import os
import sys
import tempfile
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_level_defences_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ[_k] = os.path.join(_S, _f)
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    try:
        import derived.levels as L
        from data.derived_store import DerivedStore
        store = DerivedStore(os.path.join(_S, "lv.db"))
        eng = L.LevelEngine(store, "QQQ")
        if not hasattr(eng, "_record_defences"):
            raise AttributeError("LevelEngine._record_defences is absent")
        A, B, C = "QQQ:resistance:755.00", "QQQ:support:745.00", "QQQ:resistance:756.00"
        for lid, px, kind in ((A, 755.0, "resistance"), (B, 745.0, "support"), (C, 756.0, "resistance")):
            store.upsert_level((lid, "QQQ", px, kind, "ny", "session:2026-10-02", 1790900000.0, 0, None, 0, None, None, 0))
        keys_before = sorted(store.live_levels("QQQ")[0].keys())

        def ev(e, ts, ids):
            return {"event": e, "ts": ts * 1000, "judged_on": "1m", "side": "resistance", "near": 755.0,
                    "far": 755.0, "level_ids": list(ids), "prices": [755.0]}
        book = types.SimpleNamespace(events=[
            ev("TESTED", 1000, [A]), ev("HELD", 1060, [A]), ev("HELD", 2000, [A]), ev("HELD", 3000, [A, C]),
            ev("HELD", 1500, [B]), ev("BREACHED", 4000, [B]), ev("FLIPPED", 4000, ["QQQ:flip:x"])])
        n1 = eng._record_defences(store, "QQQ", book)

        def row(lid):
            return tuple(store.conn.execute(
                "SELECT defended_count, failed_count, tested_count, last_defended_ts, touch_count, closes_beyond"
                " FROM level_ledger WHERE level_id=?", (lid,)).fetchone())
        a, b, c = row(A), row(B), row(C)
        check("D1 755.00: defended 3, tested 1, failed 0, last defended at the last HELD bar",
              a[:4] == (3, 0, 1, 3000.0), str(a))
        check("D2 745.00: defended once, then failed once", b[:3] == (1, 1, 0) and b[3] == 1500.0, str(b))
        check("D3 a zone's HELD credits its other member too (756.00: defended 1)", c[:3] == (1, 0, 0), str(c))
        n2 = eng._record_defences(store, "QQQ", book)
        book.events.append(ev("HELD", 5000, [A]))
        n3 = eng._record_defences(store, "QQQ", book)
        check("D4 the same events rewrite nothing; one new HELD rewrites one level",
              n1 == 3 and n2 == 0 and n3 == 1 and row(A)[:4] == (4, 0, 1, 5000.0), f"writes {n1},{n2},{n3}; {row(A)}")
        keys_after = sorted(store.live_levels("QQQ")[0].keys())
        check("D5 RECORD-ONLY: touch_count and closes_beyond still 0; live_levels returns the same keys",
              all(r[4] == 0 and r[5] == 0 for r in (row(A), row(B), row(C))) and keys_before == keys_after
              and not any("defend" in k or "failed" in k for k in keys_after), f"{keys_before} -> {keys_after}")
    except Exception as exc:                                  # noqa: BLE001
        for n_ in ("D1", "D2", "D3", "D4", "D5"):
            if n_ not in FAILED:
                check(f"{n_} (did not run)", False, f"{type(exc).__name__}: {exc}")
    try:
        src = open(os.path.join(_root, "derived", "levels.py")).read()
        i = src.find("    def _book_sync(self, sym: str) -> int:")
        j = src.find("\n    def ", i + 10)
        body = src[i:j]
        check("D6 _book_sync records the counts once the book is built (source check)",
              "self._record_defences(store, sym, book)" in body)
    except Exception as exc:                                  # noqa: BLE001
        check("D6 (did not run)", False, f"{type(exc).__name__}: {exc}")
    if FAILED:
        print(f"\nRED — {len(set(FAILED))} check(s): {sorted(set(FAILED))}")
        return 1
    print("\nGREEN — defences and failures are counted per level, in columns nothing that trades reads")
    return 0


if __name__ == "__main__":
    sys.exit(main())
