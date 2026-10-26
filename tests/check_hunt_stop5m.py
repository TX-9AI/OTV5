#!/usr/bin/env python3
"""
tests/check_hunt_stop5m.py  v5.1
v5.1  2026-10-26  OTV5 r38 (HYG.18) — scratch no longer names dir="/var/tmp": mkdtemp honours TMPDIR, which boot_sweep and land.sh point
      at a per-run dir they remove (HYG.14), so a sweep leaves nothing behind (237 dirs had piled up on SOFI). No check changed.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.3  2026-10-24  OTV4TEST r316 (BRK.15) — H8b RE-POINTED, NOT DROPPED (section 38.4): BRK.12's re-arm row shows its mode
      only under OT_BRK_REFIRE=extreme (the rollback); under the default rearm the line reads "rearm=brk:superseded".
      H8b now asks both: the old properties with BRK_REFIRE_MODE=extreme, and "superseded" under rearm.
v1.2  2026-10-18  OTV4TEST r293 (DIAL.2) — H8b: the Service line (main._banner_dials) names hunt_stop and rearm and prints
      a refused OT_HUNT_STOP5M / OT_HUNT_REARM by value; config recorded the refusal and nothing read it (audit 10-18 G2).
      OT_LOG_FILE joins this checker's own scratch env (it imports main now).
v1.1  2026-10-18  OTV4TEST r290 (HUNT.10) — THROUGH THE FRONT DOOR. H1-H7 drove _runaway_thesis_exits directly; the
      live 2026-10-15 Hunt (ddeb0fab) was HELD there and then killed by _evaluate_orb's step 2 on the bare boundary,
      a path this checker never reached. H9a-c drive ExitEngine.evaluate() with the clock seam pinned:
  H9a evaluate(): a close of 100.50 through the boundary, under the 5m line, keeps the trade   (RED before)
  H9b evaluate(): a close of 101.40 beyond the line exits as hunt_thesis_dead, not orb_structure_stop
  H9c the 10-15 replay: real QQQ 5m bars 09:30-09:55 and 1m bars 09:52-10:00, entry 09:54:17, boundary
      717.01, line 721.15 - the 09:59 close of 717.03 keeps the trade                              (RED before)
v1.0  2026-10-14  OTV4TEST r285 (HUNT.8) — THE HUNT'S THESIS LINE IS THE FARTHER OF ITS BOUNDARY AND THE 5m SWING.

THE OPERATOR, 2026-10-14 11:47 ET: "Yes, we have to" (the 5m structure stop for the Hunt as
for Breakout). 10-14 09:58: a right-way Hunt short died at 10:03 on a 1m close of 737.28
back through its 736.90 boundary; QQQ then fell to 732.4. MEASURED
(/var/tmp/structure_hold_1014/v2_hunt.txt, n21, 1m close): -16.3 R -> -5.5 R.

DRIVES THE REAL ExitEngine._runaway_thesis_exits on a scratch feed store (1m frame
handed in, 5m candles in the store) and a scratch counterfactual dir.

  H1  a short whose 5m swing (101.00) is above its boundary (100.00): a 1m close of
      100.50 (through the boundary, under the swing) keeps the trade - not thesis-dead,
      not the 1m fizzle read, not the boundary backstop           (RED before)
  H2  a close beyond the 5m line (101.40) IS thesis-dead, naming the 5m line
  H3  never nearer: a 5m swing INSIDE the boundary leaves the boundary deciding
  H4  a 5m bar ending after the entry time never counts
  H5  OT_HUNT_STOP5M=log: the boundary decides (100.50 is dead) and the 5m line is recorded
  H6  an unreadable feed store keeps the boundary (100.50 is dead), never raises
  H7  counterfactual: a 'line' row per trade, and 'old_line_would_exit' /
      'fizzle_would_exit' rows when the old rules would have ended a trade the 5m
      line keeps                                                  (RED before)
  H8  config: unset -> trade; off/log honoured; junk -> log, refused by name
"""
import glob as _glob
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

for _sp in _glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
SCRATCH = tempfile.mkdtemp(prefix="chk_hunt_s5_")
for k, v in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived.db"), ("OT_RESTING_DB", "resting.db"),
             ("OT_FEED_DB", "feed.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_SIGNAL_JOURNAL_DIR", "sj"),
             ("OT_LOG_FILE", "bot.log")):        # r293: H8b imports main, whose file handler follows config.LOG_FILE
    os.environ[k] = os.path.join(SCRATCH, v)
os.environ.pop("OT_HUNT_STOP5M", None)
FAILED, RAN = [], []
ET = "America/New_York"


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def guard(name, fn):
    try:
        ok, det = fn()
    except Exception as exc:                                    # noqa: BLE001
        ok, det = False, f"{type(exc).__name__}: {exc}"
    check(name, bool(ok), det)


def _o(day):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return int(datetime(day.year, day.month, day.day, 9, 30, tzinfo=ZoneInfo(ET)).timestamp() * 1000)


def _write_feed(day):
    o = _o(day)
    c = sqlite3.connect(os.environ["OT_FEED_DB"])
    c.execute("CREATE TABLE IF NOT EXISTS candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, "
              "ts_epoch_ms INTEGER NOT NULL, open REAL, high REAL, low REAL, close REAL, "
              "volume REAL, PRIMARY KEY (symbol, interval, ts_epoch_ms))")
    rows = {"H5W": [(0, 101.00, 100.00), (5, 100.60, 99.80), (10, 103.00, 99.50)],   # 09:40 bucket ends after a 09:42 entry
            "H5T": [(0, 99.90, 99.50), (5, 99.95, 99.40)]}                            # every high inside the boundary
    for sym, bars in rows.items():
        for m, h, l in bars:
            c.execute("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)",
                      (sym, "5m", o + m * 60_000, h - 0.1, h, l, l + 0.1, 5000.0))
    c.commit()
    c.close()


def _df(day, last_close):
    """A 1m frame: bars 09:42..09:50 with tiny wicks; iloc[-2] closes at `last_close`."""
    import pandas as pd
    o = _o(day)
    rows = []
    for m in range(12, 21):
        cl = last_close if m == 19 else 99.70
        rows.append((o + m * 60_000, cl, cl + 0.01, cl - 0.01, cl, 1000.0))
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df.index = pd.to_datetime(df.pop("ts"), unit="ms", utc=True).dt.tz_convert(ET)
    return df


def _rec(day, sym, tid):
    from datetime import datetime, timezone
    return {"trade_id": tid, "symbol": sym, "strategy": "LiquidityHunt", "direction": "short",
            "underlying_stop": 100.00, "underlying_entry": 99.70, "orb_range_high": 100.00,
            "orb_range_low": 99.00, "entry_premium": 1.00,
            "entry_time": datetime.fromtimestamp((_o(day) + 12 * 60_000 + 5_000) / 1000, timezone.utc).isoformat()}


def _ask(eng, day, sym, tid, close):
    return eng._runaway_thesis_exits(_rec(day, sym, tid), "short", 0.80, 1.00, -20.0, _df(day, close))


def _cf_rows():
    p = os.path.join(os.environ["OT_COUNTERFACTUAL_DIR"], "hunt_stop.jsonl")
    return [json.loads(x) for x in open(p)] if os.path.exists(p) else []


def _cfg(env):
    e = {k: v for k, v in os.environ.items() if k != "OT_HUNT_STOP5M"}
    e.update(env)
    r = subprocess.run([sys.executable, "-c", "import config; print(config.HUNT_STOP5M_MODE, "
                        "repr(getattr(config, 'HUNT_STOP5M_ENV_REFUSED', None)))"],
                       cwd=ROOT, env=e, capture_output=True, text=True, timeout=60)
    return (r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1]


def main():
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        day = datetime.now(ZoneInfo(ET)).date()
        _write_feed(day)
        import config
        import execution.exit_engine as XE
        eng = XE.ExitEngine(paper_trading=True)
    except Exception as exc:                                    # noqa: BLE001
        for n in ("H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H8b", "H9a", "H9b", "H9c"):
            check(f"{n} setup", False, f"{type(exc).__name__}: {exc}")
        return _tail()

    r1 = _ask(eng, day, "H5W", "t-h1", 100.50)
    guard("H1 a close of 100.50 through the 100.00 boundary but under the 101.00 5m swing keeps the trade "
          "(no thesis-dead, no fizzle, no backstop)", lambda: (r1 == "", repr(r1)))
    r2 = _ask(eng, day, "H5W", "t-h2", 101.40)
    guard("H2 a close of 101.40 beyond the 5m line IS thesis-dead, naming 101.00",
          lambda: ("hunt_thesis_dead" in (r2 or "") and "101.00" in r2, repr(r2)))
    r3 = _ask(eng, day, "H5T", "t-h3", 100.50)
    guard("H3 a 5m swing inside the boundary never tightens it: 100.50 is dead on the 100.00 boundary",
          lambda: ("hunt_thesis_dead" in (r3 or "") and "100.00" in r3, repr(r3)))
    guard("H4 the 09:40 5m bucket (high 103.00) ended after the 09:42 entry and never counts: 101.40 is dead",
          lambda: ("hunt_thesis_dead" in (r2 or ""), repr(r2)))

    saved = getattr(config, "HUNT_STOP5M_MODE", None)
    config.HUNT_STOP5M_MODE = "log"
    try:
        r5 = _ask(eng, day, "H5W", "t-h5", 100.50)
    finally:
        config.HUNT_STOP5M_MODE = saved
    rows5 = [x for x in _cf_rows() if x.get("trade_id") == "t-h5" and x.get("event") == "line"]
    guard("H5 OT_HUNT_STOP5M=log: the boundary decides (100.50 is dead) and the 5m line 101.00 is recorded",
          lambda: ("hunt_thesis_dead" in (r5 or "") and rows5 and rows5[0].get("stop_5m") == 101.00
                   and rows5[0].get("line_used") == 100.00, f"{r5!r} {rows5}"))

    feed = os.environ["OT_FEED_DB"]
    os.environ["OT_FEED_DB"] = os.path.join(SCRATCH, "absent", "feed.db")
    try:
        r6 = _ask(eng, day, "H5W", "t-h6", 100.50)
    finally:
        os.environ["OT_FEED_DB"] = feed
    guard("H6 an unreadable feed store keeps the boundary: 100.50 is dead, nothing raised",
          lambda: ("hunt_thesis_dead" in (r6 or "") and "100.00" in r6, repr(r6)))

    rows = [x for x in _cf_rows() if x.get("trade_id") == "t-h1"]
    ev = sorted(x.get("event") for x in rows)
    guard("H7 counterfactual rows for the kept trade: 'line' (101.00 used), 'old_line_would_exit', 'fizzle_would_exit'",
          lambda: (ev == ["fizzle_would_exit", "line", "old_line_would_exit"]
                   and any(x.get("line_used") == 101.00 for x in rows if x["event"] == "line"), repr(rows)))

    got = [_cfg({}), _cfg({"OT_HUNT_STOP5M": "OFF"}), _cfg({"OT_HUNT_STOP5M": "log"}), _cfg({"OT_HUNT_STOP5M": "yes"})]
    guard("H8 config: unset -> trade, OFF -> off, log -> log, junk -> log refused by name",
          lambda: (got == ["trade ''", "off ''", "log ''", "log 'yes'"], repr(got)))

    # r293 (DIAL.2) — "named" has to mean the Service line. config recorded the refusal; nothing printed it.
    def _h8b():
        import main as _MN
        _saved = {k: getattr(config, k) for k in ("HUNT_STOP5M_MODE", "HUNT_STOP5M_ENV_REFUSED",
                                                   "BRK_REARM_MODE", "HUNT_REARM_ENV_REFUSED", "BRK_REFIRE_MODE")}
        try:
            config.BRK_REFIRE_MODE = "rearm"                                  # r316: the default
            config.HUNT_STOP5M_MODE, config.HUNT_STOP5M_ENV_REFUSED = "trade", ""
            config.BRK_REARM_MODE, config.HUNT_REARM_ENV_REFUSED = "log", ""
            sup = _MN._banner_dials()
            config.BRK_REFIRE_MODE = "extreme"                                # the rollback shows BRK.12's mode
            config.HUNT_STOP5M_MODE, config.HUNT_STOP5M_ENV_REFUSED = "trade", ""
            config.BRK_REARM_MODE, config.HUNT_REARM_ENV_REFUSED = "log", ""
            clean = _MN._banner_dials()
            config.HUNT_STOP5M_MODE, config.HUNT_STOP5M_ENV_REFUSED = "log", "1"
            config.BRK_REARM_MODE, config.HUNT_REARM_ENV_REFUSED = "off", "yes"
            typo = _MN._banner_dials()
        finally:
            for k, v in _saved.items():
                setattr(config, k, v)
        ok = (" · rearm=brk:superseded/hunt:" in sup
              and " · hunt_stop=5m(trade)" in clean and " · rearm=brk:log/hunt:" in clean and "REFUSED" not in clean.split("hunt_stop=")[1]
              and " · hunt_stop=1m(log) (OT_HUNT_STOP5M='1' REFUSED)" in typo
              and " · rearm=brk:off/hunt:" in typo and "(OT_HUNT_REARM='yes' REFUSED)" in typo)
        return ok, f"clean={clean[-160:]!r} typo={typo[-200:]!r}"
    guard("H8b the Service line names hunt_stop and rearm, and a refused OT_HUNT_STOP5M / OT_HUNT_REARM by value", _h8b)

    # ── r290 (HUNT.10): the same questions asked of evaluate(), the entry point the bot calls ──
    XE.is_hard_close_time = lambda: False          # the one clock seam every checker pins

    def _ev(sym, tid, close, **kw):
        rec = _rec(day, sym, tid)
        rec.update({"stop_premium": 0.0, "target_premium": 9.99, "trail_activation": 9.99, "contracts": 1})
        rec.update(kw)
        return eng.evaluate(rec, 0.80, df_1m=_df(day, close), df_5m=None)

    d9a = _ev("H5W", "t-h9a", 100.50)
    guard("H9a evaluate(): 100.50 through the boundary, under the 101.00 line, keeps the trade (no step-2 backstop)",
          lambda: (not d9a.should_exit, repr(d9a.exit_reason)))
    d9b = _ev("H5W", "t-h9b", 101.40)
    guard("H9b evaluate(): 101.40 beyond the line exits as hunt_thesis_dead naming 101.00, not orb_structure_stop",
          lambda: (d9b.should_exit and str(d9b.exit_reason).startswith("hunt_thesis_dead") and "101.00" in d9b.exit_reason,
                   repr(d9b.exit_reason)))

    # the 10-15 replay, from the feed store and trades.db of that day
    from datetime import date as _date, datetime as _dtm, timezone as _tz
    import pandas as pd
    d15 = _date(2026, 10, 15)
    o15 = _o(d15)
    c = sqlite3.connect(os.environ["OT_FEED_DB"])
    for m, (op, hi, lo, cl) in {0: (718.57, 719.42, 717.01, 717.89), 5: (717.8, 720.5944, 717.07, 720.47),
                                 10: (720.47, 720.93, 719.19, 720.37), 15: (720.191, 721.15, 718.37, 718.67),
                                 20: (718.63, 719.11, 715.83, 715.84), 25: (715.86, 717.19, 715.435, 717.03)}.items():
        c.execute("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)", ("Q1015", "5m", o15 + m * 60_000, op, hi, lo, cl, 5000.0))
    c.commit(); c.close()
    bars = [(22, 718.5139, 718.5139, 717.1303, 717.5), (23, 717.54, 717.7, 716.21, 716.285), (24, 716.27, 716.62, 715.83, 715.84),
            (25, 715.86, 716.16, 715.6599, 716.06), (26, 716.06, 716.46, 715.61, 716.32), (27, 716.315, 716.45, 715.435, 715.6301),
            (28, 715.6, 716.67, 715.57, 716.61), (29, 716.6, 717.19, 716.26, 717.03), (30, 717.0008, 717.83, 716.94, 717.52)]
    df15 = pd.DataFrame([(o15 + m * 60_000, op, hi, lo, cl, 1000.0) for m, op, hi, lo, cl in bars],
                        columns=["ts", "open", "high", "low", "close", "volume"])
    df15.index = pd.to_datetime(df15.pop("ts"), unit="ms", utc=True).dt.tz_convert(ET)
    rec15 = {"trade_id": "ddeb0fab-replay", "symbol": "Q1015", "strategy": "LiquidityHunt", "direction": "short",
             "underlying_stop": 717.01, "underlying_entry": 716.56, "underlying_target": 715.08,
             "orb_range_high": 719.42, "orb_range_low": 717.01, "entry_premium": 2.56, "stop_premium": 0.0,
             "target_premium": 9.99, "trail_activation": 9.99, "contracts": 4,
             "entry_time": _dtm(2026, 10, 15, 13, 54, 17, tzinfo=_tz.utc).isoformat()}
    d9c = eng.evaluate(rec15, 2.19, df_1m=df15, df_5m=None)
    line15 = [x for x in _cf_rows() if x.get("trade_id") == "ddeb0fab-replay" and x.get("event") == "line"]
    guard("H9c the 10-15 replay: line 721.15 from the 09:35-09:45 5m bars; the 09:59 close 717.03 vs boundary 717.01 is HELD",
          lambda: (not d9c.should_exit and line15 and line15[0].get("line_used") == 721.15,
                   f"{d9c.exit_reason!r} line={line15[:1]}"))
    return _tail()


def _tail():
    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks: the Hunt's thesis line is the 5m swing")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        shutil.rmtree(SCRATCH, ignore_errors=True)
    sys.exit(rc)
