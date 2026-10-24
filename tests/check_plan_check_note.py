#!/usr/bin/env python3
"""
tests/check_plan_check_note.py  v1.0
v1.0  2026-10-03  OTV4TEST r197 (AUD.6) — A CHECK'S TEXT IS STORED.

  Found by the 10-03 audit: plan_check.value is REAL and write_row cast every
  reading to float or wrote NULL; the note= argument went nowhere. So every
  text-valued check - Breakout's break_dir, pool_name, verdict and contract,
  the ORB's engine_state, the sweep's fork - was NULL on every row ever kept.

  Drives the REAL Plan / PlanTick / write_row on a scratch store:
  N1  check(name, None, None, note="WAIT") -> note 'WAIT', value NULL
  N2  check(name, "long")                  -> note 'long' (a value that is a word)
  N3  UNCHANGED: a numeric check keeps its value and verdict, note NULL
  N4  a numeric check WITH a note keeps both
  N5  MIGRATION: a store whose plan_check predates the column gains it, and
      its old rows survive with note NULL

Run:  python3 tests/check_plan_check_note.py   (exit 0 green, 1 red)
"""
import glob as _glob
import os
import sqlite3
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_plan_check_note_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class _Store:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

    def commit(self):
        self.conn.commit()


def _cols(st):
    return [r[1] for r in st.conn.execute("PRAGMA table_info(plan_check)")]


def main():
    from strategy import plan as P

    st = _Store(os.path.join(_S, "gate.db"))
    P.bind_store(st)
    try:
        P.REGISTRY.pop("GateNote", None)
        plan = P.Plan("GateNote", ("verdict", "break_dir", "width", "r"))
        plan.symbol = "TST"
        P.begin_tick(1000.0)
        t = plan.tick(100.0, "long")
        t.check("verdict", None, None, note="WAIT")
        t.check("break_dir", "long", None)
        t.check("width", 0.5, True)
        t.check("r", 2.25, False, note="below the floor")
        t.hold("gate")
        rows = {}
        if "note" in _cols(st):
            rows = {r["check_name"]: (r["value"], r["verdict"], r["note"]) for r in st.conn.execute(
                "SELECT check_name, value, verdict, note FROM plan_check WHERE strategy='GateNote'")}
        else:
            rows = {r["check_name"]: (r["value"], r["verdict"], "<no note column>") for r in st.conn.execute(
                "SELECT check_name, value, verdict FROM plan_check WHERE strategy='GateNote'")}
        check("N1 a check with only a note stores the note ('WAIT'), value NULL",
              rows.get("verdict") == (None, "n/a", "WAIT"), str(rows.get("verdict")))
        check("N2 a check whose VALUE is a word keeps the word ('long') in note",
              rows.get("break_dir") == (None, "n/a", "long"), str(rows.get("break_dir")))
        check("N3 UNCHANGED: a numeric check keeps value 0.5, PASS, note NULL",
              rows.get("width") == (0.5, "PASS", None), str(rows.get("width")))
        check("N4 a numeric check with a note keeps both (2.25, FAIL, the note)",
              rows.get("r") == (2.25, "FAIL", "below the floor"), str(rows.get("r")))
    except Exception as exc:                                  # noqa: BLE001
        check("N1 (did not run)", False, f"{type(exc).__name__}: {exc}")
    finally:
        P.bind_store(None)

    # N5 — a store created before the column
    try:
        old = _Store(os.path.join(_S, "old.db"))
        old.conn.execute("""CREATE TABLE plan_check (ts_epoch REAL NOT NULL, symbol TEXT NOT NULL,
            strategy TEXT NOT NULL, check_name TEXT NOT NULL, value REAL, verdict TEXT,
            tick_id INTEGER DEFAULT 0, direction TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (ts_epoch, symbol, strategy, direction, check_name))""")
        old.conn.execute("INSERT INTO plan_check (ts_epoch, symbol, strategy, check_name, value, verdict)"
                         " VALUES (1.0, 'TST', 'Old', 'width', 0.4, 'PASS')")
        old.commit()
        if hasattr(old, "_plan_tables_ready"):
            del old._plan_tables_ready
        P.ensure_tables(old)
        has = "note" in _cols(old)
        kept = old.conn.execute("SELECT value, verdict" + (", note" if has else "") +
                                " FROM plan_check WHERE strategy='Old'").fetchone()
        check("N5 MIGRATION: an older plan_check gains the note column and keeps its rows",
              has and kept is not None and tuple(kept) == (0.4, "PASS", None),
              f"note column={has} row={tuple(kept) if kept else None}")
    except Exception as exc:                                  # noqa: BLE001
        check("N5 (did not run)", False, f"{type(exc).__name__}: {exc}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — a check's text reaches plan_check.note; numbers are unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
