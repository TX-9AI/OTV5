#!/usr/bin/env python3
"""
tests/check_et_offset.py  v1.0
v1.0  2026-10-03  OTV4TEST r191 (AUD.2) — EASTERN TIME COMES FROM THE TZ DATABASE.

  Found by the 10-03 audit: tools/last_session.py, tools/plan_board.py and
  tools/probe_candle_depth.py hard-coded ET as UTC-4, and tools/eod_summary.py
  filtered "today" with a literal '-4 hours'. DST ends 2026-11-01; from then
  each would be an hour wrong (query.py fixed the same class at r210).

  Drives the REAL module objects at two instants, 2026-10-02 15:00 UTC (EDT)
  and 2026-11-02 15:00 UTC (EST):
  Z1  tools/last_session.ET   -> 11:00 then 10:00
  Z2  tools/plan_board.ET     -> 11:00 then 10:00
  Z3  tools/eod_summary.et_offset_sql -> "-4 hours" then "-5 hours"
  Z4  tools/eod_summary's day filter keeps a 20:30 UTC entry on its own
      Eastern day in November (the real query, on a scratch trades.db)

Run:  python3 tests/check_et_offset.py   (exit 0 green, 1 red)
"""
import datetime as dt
import glob as _glob
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)

FAILED = []
SUMMER = dt.datetime(2026, 10, 2, 15, 0, tzinfo=dt.timezone.utc)
WINTER = dt.datetime(2026, 11, 2, 15, 0, tzinfo=dt.timezone.utc)


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def load(rel):
    spec = importlib.util.spec_from_file_location(rel.replace("/", "_")[:-3], os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    for tag, rel in (("Z1", "tools/last_session.py"), ("Z2", "tools/plan_board.py")):
        try:
            et = load(rel).ET
            got = (SUMMER.astimezone(et).hour, WINTER.astimezone(et).hour)
        except Exception as exc:                              # noqa: BLE001
            got = f"{type(exc).__name__}: {exc}"
        check(f"{tag} {rel} ET is 11:00 on 10-02 and 10:00 on 11-02 (15:00 UTC)", got == (11, 10), f"got {got}")

    try:
        es = load("tools/eod_summary.py")
        fn = getattr(es, "et_offset_sql", None)
        from zoneinfo import ZoneInfo
        ny = ZoneInfo("America/New_York")
        got = (fn(SUMMER.astimezone(ny)), fn(WINTER.astimezone(ny))) if fn else "no et_offset_sql"
    except Exception as exc:                                  # noqa: BLE001
        es, got = None, f"{type(exc).__name__}: {exc}"
    check('Z3 eod_summary.et_offset_sql is "-4 hours" in October and "-5 hours" in November',
          got == ("-4 hours", "-5 hours"), f"got {got}")

    # Z4 — the REAL compute_summary on a scratch store, the clock pinned to a November evening
    try:
        import sqlite3
        import tempfile
        from zoneinfo import ZoneInfo
        ny = ZoneInfo("America/New_York")
        tmp = tempfile.mkdtemp(prefix="check_et_offset_")
        db = os.path.join(tmp, "trades.db")
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE trades (trade_id TEXT, status TEXT, entry_time TEXT, pnl_usd REAL, "
                    "paper_trade INTEGER)")
        # 2026-11-02 23:30 ET = 2026-11-03 04:30 UTC: on the 2nd in Eastern, the 3rd under a -4 filter
        con.execute("INSERT INTO trades VALUES ('late', 'closed', '2026-11-03T04:30:00+00:00', 12.5, 1)")
        con.commit(); con.close()
        es.DB_PATH = db
        es.now_et = lambda: dt.datetime(2026, 11, 2, 23, 45, tzinfo=ny)
        got = es.compute_summary()
        ok = got.get("date_et") == "2026-11-02" and got.get("n_trades") == 1
        detail = f"date_et={got.get('date_et')} n_trades={got.get('n_trades')}"
    except Exception as exc:                                  # noqa: BLE001
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    check("Z4 the November day filter keeps a late-evening Eastern entry on its own day", ok, detail)

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — Eastern time is read from the tz database in every tool checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
