#!/usr/bin/env python3
"""
tests/check_control_contract.py  v1.0
v1.0  2026-10-03  OTV4TEST r201 (CTL.1) — WHAT CONTROL CALLS ON A BOX IS WHERE CONTROL CALLS IT.

  The 10-03 audit measured this tree against the control-to-box contract
  1-REPORTER read out of day_trader_pro (dtp 766d6fc). Two calls would have
  failed on a box running this tree, because r14 moved the scripts to deploy/:
      bash ~/options-trader/push.sh --deploy          (fleet.py:469)
      bash ~/options-trader/pull_today_ohlc.sh        (eod_backfill.py:114)
  Mainline will be repointed at this tree when it becomes OTV5, so the paths
  control uses are pinned here.

  K1  the two ROOT shims exist, are executable, and FORWARD every argument to
      their deploy/ script (driven: the real shim file, a stub deploy script)
  K2  every path control runs or reads exists where control looks for it
  K3  the trades columns control's standings query selects, and `lineage`,
      exist in the schema the REAL TradeLogger creates
  K4  s3_push still prints the DRAIN line control's conductor parses, and
      accepts --verify and --reconcile; retention_purge accepts --apply

Run:  python3 tests/check_control_contract.py   (exit 0 green, 1 red)
"""
import glob as _glob
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_control_contract_")
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


def main():
    # K1 — the shims, driven: copy the REAL shim beside a stub deploy script and call it
    got = {}
    for name in ("push.sh", "pull_today_ohlc.sh"):
        shim = os.path.join(_root, name)
        if not os.path.isfile(shim):
            got[name] = "MISSING at the repo root"
            continue
        if not os.access(shim, os.X_OK):
            got[name] = "not executable"
            continue
        d = tempfile.mkdtemp(prefix="shim_", dir=_S)
        os.makedirs(os.path.join(d, "deploy"))
        shutil.copy2(shim, os.path.join(d, name))
        with open(os.path.join(d, "deploy", name), "w") as fh:
            fh.write('#!/bin/bash\necho "DEPLOY %s $*"\n' % name)
        r = subprocess.run(["bash", os.path.join(d, name), "--deploy", "--no restart", "x"],
                           capture_output=True, text=True, timeout=30, cwd=_S)
        got[name] = r.stdout.strip() or r.stderr.strip()[-120:]
    want = {n: "DEPLOY %s --deploy --no restart x" % n for n in ("push.sh", "pull_today_ohlc.sh")}
    check("K1 push.sh and pull_today_ohlc.sh at the repo root forward every argument to deploy/",
          got == want, str(got))

    # K2 — paths control runs or reads
    paths = ["status.py", "query.py", "push.sh", "pull_today_ohlc.sh", "deploy/push.sh",
             "deploy/pull_today_ohlc.sh", "warehouse/s3_push.py", "warehouse/retention_purge.py",
             "tools/manifold_health.py", "main.py", "config.py"]
    missing = [p for p in paths if not os.path.isfile(os.path.join(_root, p))]
    check("K2 every path control runs or reads exists where control looks for it", not missing,
          f"missing: {missing}")

    # K3 — the columns standings.py selects, in the REAL schema
    try:
        from database import trade_logger as tl
        db = os.path.join(_S, "contract_trades.db")
        tl.TradeLogger(db_path=db, paper_trading=True)
        con = sqlite3.connect(db)
        cols = {r[1] for r in con.execute("PRAGMA table_info(trades)")}
        con.close()
        need = ["entry_time", "exit_time", "symbol", "strategy", "entry_premium", "current_premium",
                "exit_premium", "contracts", "pnl_usd", "credit_received", "option_side",
                "is_short_position", "is_condor_leg", "center_symbol", "status", "lineage",
                "trade_id", "exit_reason", "stop_premium"]
        lacking = [c for c in need if c not in cols]
        check("K3 the trades columns control selects (and lineage) exist in the real schema",
              not lacking, f"lacking: {lacking}")
    except Exception as exc:                                  # noqa: BLE001
        check("K3 (did not run)", False, f"{type(exc).__name__}: {exc}")

    # K4 — the lines and flags control parses. Source-level by necessity: running
    # s3_push or the purge for real is exactly what a gate must not do.
    try:
        sp = open(os.path.join(_root, "warehouse", "s3_push.py"), encoding="utf-8").read()
        rp = open(os.path.join(_root, "warehouse", "retention_purge.py"), encoding="utf-8").read()
        ok = ('"DRAIN host={} sym={} drained={} pushed={} failed={} "' in sp
              and '"--verify" in argv' in sp and '"--reconcile" in argv' in sp
              and '"--apply" in argv' in rp and "WOULD remove" in rp)
        check("K4 s3_push keeps the DRAIN line and --verify/--reconcile; the purge keeps --apply", ok,
              "one of the strings control's conductor parses is gone")
    except Exception as exc:                                  # noqa: BLE001
        check("K4 (did not run)", False, f"{type(exc).__name__}: {exc}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — the paths, columns and lines control depends on are where it looks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
