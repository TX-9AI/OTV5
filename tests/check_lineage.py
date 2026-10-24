"""tests/check_lineage.py — v1.0
EVERY NEW TRADE ROW THIS TREE WRITES CARRIES lineage = 'TEST', AND NO ROW THAT
ALREADY EXISTED IS RELABELLED.

v1.0  2026-09-25 — OTV4TEST r140. control's r426/OPS.50 keys every
      per-strategy rollup on (lineage, code): six strategy names exist in
      BOTH engines as DIFFERENT code, so pooling by name pools two designs.
      The field is ONE contract across both repos - name `lineage`, values
      MAIN (mainline) and TEST (this tree). Operator, 2026-09-25: "Yes to the
      lineage question using test."

  L0  the live trades.db is untouched: every store here is scratch, and the
      live file's row count and mtime are compared before and after
  L1  the contract literals: trade_logger.LINEAGE == "TEST", column `lineage`
  L2  a fresh store: the REAL log_entry writes lineage 'TEST', read back by SQL
  L3  a caller cannot relabel: a record handed in with lineage 'MAIN' is
      stored 'TEST' (this tree is the producer; the stamp is not advisory)
  L4  REHYDRATED shape (WA §21): get_open_trades() - SELECT * - returns it
  L5  a PRE-r140 store migrates WITHOUT BACKFILL: the old row stays NULL and
      only the new row is 'TEST'. On an in-place supersede those old rows are
      MAIN's, and a default would relabel - and re-push - that whole history
  L6  the REAL s3_push.push_trades carries it to the warehouse: the envelope's
      record holds lineage 'TEST' for the new row and None for the old one
      (a stub S3 client; nothing leaves the box)
"""
from __future__ import annotations

import glob as _glob
import json
import os
import sqlite3
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

# Scratch BEFORE config is imported: DB_PATH reads OT_TRADES_DB at import (r13).
_tmp = tempfile.mkdtemp(prefix="check_lineage_")
os.environ["OT_TRADES_DB"] = os.path.join(_tmp, "unused_default.db")
os.environ["OT_WAREHOUSE_STATE"] = os.path.join(_tmp, "wh_state")

FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def guard(name, fn, detail=lambda: ""):
    try:
        ok = bool(fn())
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, "%s: %s" % (type(exc).__name__, exc))
        return
    try:
        d = detail()
    except Exception:                                           # noqa: BLE001
        d = ""
    check(name, ok, d)


_LIVE = os.path.expanduser("~/options-trader/trades.db")


def _live_state():
    if not os.path.exists(_LIVE):
        return ("absent",)
    con = sqlite3.connect("file:%s?mode=ro" % _LIVE, uri=True)
    try:
        n = con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    finally:
        con.close()
    return (n, os.path.getmtime(_LIVE))


_before = _live_state()

from database import trade_logger as tl                         # noqa: E402

PAPER = 1


def _rec(tid, **kw):
    r = tl.make_record(trade_id=tid, symbol="QQQ", strategy="Breakout",
                       direction="long", paper_trade=PAPER)
    r.update(kw)
    return r


def _lineage(db, tid):
    con = sqlite3.connect(db)
    try:
        return con.execute("SELECT lineage FROM trades WHERE trade_id=?", (tid,)).fetchone()[0]
    finally:
        con.close()


# ── L1: the contract literals ────────────────────────────────────────────────
guard("L1  trade_logger.LINEAGE is exactly 'TEST'",
      lambda: getattr(tl, "LINEAGE", None) == "TEST",
      lambda: repr(getattr(tl, "LINEAGE", "<absent>")))

# ── L2: a fresh store, the real log_entry ───────────────────────────────────
fresh = os.path.join(_tmp, "fresh.db")
L = tl.TradeLogger(db_path=fresh, paper_trading=True)
guard("L1b the trades table has a `lineage` column",
      lambda: "lineage" in L._columns(), lambda: "columns=%d" % len(L._columns()))
L.log_entry(_rec("t-new"))
guard("L2  log_entry writes lineage 'TEST' (read back by SQL)",
      lambda: _lineage(fresh, "t-new") == "TEST",
      lambda: repr(_lineage(fresh, "t-new")))

# ── L3: a caller cannot relabel ─────────────────────────────────────────────
L.log_entry(_rec("t-claims-main", lineage="MAIN"))
guard("L3  a record handed in as 'MAIN' is stored 'TEST'",
      lambda: _lineage(fresh, "t-claims-main") == "TEST",
      lambda: repr(_lineage(fresh, "t-claims-main")))

# ── L4: rehydrated shape ────────────────────────────────────────────────────
guard("L4  get_open_trades() (SELECT *) returns lineage 'TEST'",
      lambda: {r["trade_id"]: r.get("lineage") for r in L.get_open_trades()}.get("t-new") == "TEST",
      lambda: repr({r["trade_id"]: r.get("lineage") for r in L.get_open_trades()}))

# ── L5: a pre-r140 store migrates without backfill ──────────────────────────
legacy = os.path.join(_tmp, "legacy.db")
_scr = sqlite3.connect(":memory:")
_scr.executescript(tl.TradeLogger.SCHEMA)       # the base CREATE, which never had lineage
_base_cols = [r[1] for r in _scr.execute("PRAGMA table_info(trades)")]
_scr.close()
_con = sqlite3.connect(legacy)
_con.executescript(tl.TradeLogger.SCHEMA)
if "lineage" in _base_cols:                      # a future edit that moves it into the CREATE
    _con.execute("ALTER TABLE trades DROP COLUMN lineage")
_con.execute("INSERT INTO trades (trade_id, symbol, strategy, status, paper_trade, entry_time) "
             "VALUES ('t-old', 'QQQ', 'ORBStrategy', 'open', 1, '2026-09-01 14:00:00')")
_con.commit()
_con.close()
L_old = tl.TradeLogger(db_path=legacy, paper_trading=True)   # runs the migration
L_old.log_entry(_rec("t-after"))
guard("L5  the pre-existing row is NOT backfilled (stays NULL)",
      lambda: _lineage(legacy, "t-old") is None,
      lambda: repr(_lineage(legacy, "t-old")))
guard("L5b a row written after the migration is 'TEST'",
      lambda: _lineage(legacy, "t-after") == "TEST",
      lambda: repr(_lineage(legacy, "t-after")))

# ── L6: the real push_trades carries it ─────────────────────────────────────


class _StubS3:
    def __init__(self):
        self.objs = {}

    def put_object(self, Bucket, Key, Body):
        self.objs[Key] = Body

    def get_object(self, Bucket, Key):
        import io
        return {"Body": io.BytesIO(self.objs[Key])}


def _pushed():
    from warehouse import s3_push
    s3 = _StubS3()
    pushed, failed = s3_push.push_trades(s3, "stub-bucket", legacy, {})
    out = {}
    for body in s3.objs.values():
        rec = json.loads(body)["record"]
        out[rec["trade_id"]] = ("lineage" in rec, rec.get("lineage"))
    return pushed, failed, out


guard("L6  push_trades sends lineage 'TEST' on the new row",
      lambda: _pushed()[2].get("t-after") == (True, "TEST"),
      lambda: repr(_pushed()))
guard("L6b push_trades sends the old row untagged (key present, None)",
      lambda: _pushed()[2].get("t-old") == (True, None),
      lambda: repr(_pushed()[2].get("t-old")))

# ── L0: the live store ──────────────────────────────────────────────────────
_after = _live_state()
check("L0  the live trades.db is untouched (rows, mtime)", _before == _after,
      "before=%r after=%r" % (_before, _after))

print("\n%s — %d checks, %d failed" % ("GREEN" if not FAILED else "RED", len(RAN), len(FAILED)))
if FAILED:
    print("  failed: " + ", ".join(FAILED))
sys.exit(1 if FAILED else 0)
