#!/usr/bin/env python3
"""
tests/check_handoff_entry_time.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-24  OTV4TEST r317 (STALE.1, D1) — BORN RED on 2cc9502 (r316).

THE DEFECT: ExitEngine._entry_epoch() returns 0.0 for a record whose entry_time is missing or unreadable, and
_rejected_handoff() then asked derived_store.latest_rejection(sym, 0.0) - "every REJECTED since the epoch". Any
rejection ever written (another day, or a seeded row) beyond the entry could close a live ORB / Runaway / Hunt.
Found by 1-REPORTER's staleness inventory (MSG-1REP-1024-35); the operator, 2026-10-24 16:04 ET: "Yes to all, on the
latent question".

DRIVES THE REAL METHOD: ExitEngine._rejected_handoff with a stand-in `self` carrying the real _entry_epoch, and
data.derived_store.get_derived_store patched to a recording store that returns a stale REJECTED beyond the entry
whenever it is asked for one at or after `since` (it honours `since` exactly as the real query does).

  H1  entry_time missing          -> no handoff, and the store is never asked from epoch 0
  H2  entry_time unreadable       -> the same
  H3  a real entry_time and a rejection after it, beyond the entry -> the handoff exit fires (unchanged)
  H4  a real entry_time and the only rejection before it            -> no handoff (unchanged)
  H5  a numeric (epoch) entry_time is read as before                 -> fires as H3
"""
import os
import sys
import tempfile

import glob as _glob
for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path: sys.path.insert(1, _sp)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_S = tempfile.mkdtemp(prefix="chk_hoet_", dir="/var/tmp")
for _k, _v in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db"), ("OT_FEED_DB", "f.db"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_RESTING_STOP_STATE", "rs.json"), ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(_S, _v)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
FAILED, RAN = [], []

ENTRY_ISO = "2026-10-23T14:00:00+00:00"          # 10:00 ET
ENTRY_EPOCH = 1792764000.0                        # the same instant
STALE_TS = 1792000000.0                           # weeks earlier
FRESH_TS = ENTRY_EPOCH + 300.0


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


class _Store:
    """Answers latest_rejection(sym, since) with the newest row whose ts >= since, as the real query does."""
    def __init__(self, rows):
        self.rows, self.asked = rows, []

    def latest_rejection(self, sym, since, kind=None):
        self.asked.append(float(since))
        hit = [r for r in self.rows if r["ts"] >= float(since) and (kind is None or r["kind"] == kind)]
        return max(hit, key=lambda r: r["ts"]) if hit else None


def _row(ts, price):
    return {"ts": ts, "price": price, "kind": "resistance", "provenance": "prev_day", "depth": "shallow",
            "pierce_pct": 0.0001, "bar_ts": "x"}


def main():
    try:
        import data.derived_store as DS
        from execution.exit_engine import ExitEngine
    except Exception as exc:                                    # noqa: BLE001
        check("H0 setup", False, f"{type(exc).__name__}: {exc}")
        return _tail()

    class _Self:                                               # the real helper, nothing else of the engine
        _entry_epoch = staticmethod(ExitEngine._entry_epoch)

    def run(rec, rows):
        st = _Store(rows)
        orig = DS.get_derived_store
        DS.get_derived_store = lambda *a, **k: st
        try:
            out = ExitEngine._rejected_handoff(_Self(), rec, "long")
        finally:
            DS.get_derived_store = orig
        return out, st.asked

    base = {"trade_id": "t1", "underlying_entry": 100.0, "direction": "long"}
    stale_only = [_row(STALE_TS, 101.0)]                       # beyond the entry, from weeks ago

    out, asked = run(dict(base), stale_only)
    check("H1 entry_time missing: no handoff, and the store is never asked from epoch 0",
          out == "" and 0.0 not in asked, f"out={out[:60]!r} asked={asked}")
    out, asked = run(dict(base, entry_time="not-a-time"), stale_only)
    check("H2 entry_time unreadable: no handoff, and the store is never asked from epoch 0",
          out == "" and 0.0 not in asked, f"out={out[:60]!r} asked={asked}")
    out, asked = run(dict(base, entry_time=ENTRY_ISO), stale_only + [_row(FRESH_TS, 101.5)])
    check("H3 a real entry and a later rejection beyond it: the handoff exit fires (unchanged)",
          out.startswith("handoff: pool 101.50") and asked == [ENTRY_EPOCH], f"out={out[:70]!r} asked={asked}")
    out, asked = run(dict(base, entry_time=ENTRY_ISO), stale_only)
    check("H4 a real entry and only an older rejection: no handoff (unchanged)",
          out == "" and asked == [ENTRY_EPOCH], f"out={out[:60]!r} asked={asked}")
    out, asked = run(dict(base, entry_time=ENTRY_EPOCH), stale_only + [_row(FRESH_TS, 101.5)])
    check("H5 a numeric entry_time is read as before: fires as H3",
          out.startswith("handoff: pool 101.50") and asked == [ENTRY_EPOCH], f"out={out[:70]!r} asked={asked}")
    return _tail()


def _tail():
    print()
    if FAILED:
        print(f"check_handoff_entry_time: {len(FAILED)} FAILED of {len(RAN)}: {' '.join(FAILED)}")
        return 1
    print(f"check_handoff_entry_time: all {len(RAN)} checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
