#!/usr/bin/env python3
"""
tests/check_brk_delta_floor.py  v1.0
BREAKOUT'S DELTA FLOOR (BRK.13).
v1.0  2026-10-18  OTV4TEST r288. The operator, 2026-10-17 19:12 ET: "A is fine" (to: trade the Breakout delta floor
      on QQQ-TEST with a counterfactual). Rule BF of /var/tmp/sat_1017/bdelta/PREREG_BRK_DELTA.md (sha 0c21a4b1,
      picks sha 3cfc0c0d): from 10 min after entry, |delta| <= 0.30 closes the Breakout; added to today's stack.
  D1  trade mode: the REAL ManagementPlan.decide CLOSES a Breakout at |delta| 0.25, condition "delta_floor"
  D2  log mode: the same trade HOLDS, and one counterfactual row (acted false, mode log, delta) is written
  D3  |delta| 0.31 (above the floor): no close
  D4  the 10-minute wait: 599 s after entry undecided, 600 s decided (breakout_delta_floor, now_epoch)
  D5  an UNREAD delta (None, 0.0) holds - never read as zero
  D6  off mode: no close and no row
  D7  the hard stop outranks it (premium through stop_premium -> hard_stop)
  D8  a SHORT (put, delta -0.20) Breakout: closed on |delta|
  D9  deterministic + recorded once: decide twice -> CLOSE twice, ONE row (acted true)
  D10 Breakout only: a RunawayContinuation record at delta 0.20 never closes on delta_floor
  D11 config: OT_BRK_DFLOOR unset -> trade; log / OFF honoured; junk -> log, refused named
  D12 the Service mode line names brk_dfloor= and park= (the REAL main._banner_dials)
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_brk_delta_floor_")
os.environ["OT_TRADES_DB"] = os.path.join(_TD, "t.db")
os.environ["OT_DERIVED_DB"] = os.path.join(_TD, "d.db")
os.environ["OT_FEED_DB"] = os.path.join(_TD, "f.db")
os.environ["OT_LOG_FILE"] = os.path.join(_TD, "bot.log")
os.environ["OT_SIGNAL_JOURNAL_DIR"] = os.path.join(_TD, "sj")
os.environ["OT_RESTING_DB"] = os.path.join(_TD, "r.db")
CF = os.path.join(_TD, "cf")
os.environ["OT_COUNTERFACTUAL_DIR"] = CF
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


ENTRY_UTC = "2026-10-08T13:35:30+00:00"


def _df():
    import pandas as pd
    rows = [{"open": 101.0, "high": 101.2, "low": 100.9, "close": 101.0, "volume": 100}] * 12
    return pd.DataFrame(rows, index=pd.date_range("2026-10-08 09:30", periods=12, freq="1min", tz="America/New_York"))


def _rec(tid, delta, direction="long", strategy="Breakout"):
    long_ = direction == "long"
    return {"trade_id": tid, "strategy": strategy, "symbol": "QQQ", "direction": direction,
            "option_side": "call" if long_ else "put", "entry_premium": 2.0, "stop_premium": 1.0,
            "target_premium": 0.0, "underlying_entry": 101.30 if long_ else 100.70,
            "underlying_stop": 100.55 if long_ else 101.45, "entry_time": ENTRY_UTC, "contracts": 10,
            "option_symbol": "QQQ   261008C00101000", "current_delta": delta, "is_butterfly": 0}


def _rows():
    f = os.path.join(CF, "breakout_delta_floor.jsonl")
    return [json.loads(x) for x in open(f)] if os.path.exists(f) else []


def _cfg_probe(env):
    e = {k: v for k, v in os.environ.items() if k != "OT_BRK_DFLOOR"}
    e.update(env)
    code = "import config,json;print(json.dumps([config.BRK_DFLOOR_MODE, config.BRK_DFLOOR_ENV_REFUSED]))"
    p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=e, capture_output=True, text=True, timeout=120)
    return json.loads(p.stdout.strip().splitlines()[-1]) if p.returncode == 0 and p.stdout.strip() else p.stderr[-300:]


def main():
    print("check_brk_delta_floor")
    try:
        import pandas  # noqa: F401
        import config
        import strategy.management as M
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2
    if not hasattr(M, "breakout_delta_floor") or not hasattr(config, "BRK_DFLOOR_MODE"):
        check("D0 the delta floor exists (management.breakout_delta_floor, config.BRK_DFLOOR_MODE)", False,
              "absent - this tree predates r288")
        print("\nRED — 1 of 1 failed: D0")
        return 1
    plan = M.get_management_plan()
    config.BRK_NOPROG_MODE = "off"                    # isolate: the bars here would stall

    def decide(rec, prem=1.6, mode="trade"):
        config.BRK_DFLOOR_MODE = mode
        return plan.decide(rec, prem, df_1m=_df(), open_records=[rec], current_price=101.0,
                           ctx={}, exit_engine=None)

    i1 = decide(_rec("d1-trade", 0.25))
    check("D1 trade mode: |delta| 0.25 is CLOSED with condition delta_floor",
          i1 is not None and i1.action == "CLOSE" and i1.condition == "delta_floor" and i1.reason.startswith("delta_floor:"),
          f"{getattr(i1, 'action', None)} {getattr(i1, 'condition', None)} {getattr(i1, 'reason', None)!r}")

    i2 = decide(_rec("d2-log", 0.25), mode="log")
    r2 = [r for r in _rows() if r["trade_id"] == "d2-log"]
    check("D2 log mode: HOLDS and one row (acted false, mode log, delta 0.25) is written",
          i2 is not None and i2.action != "CLOSE" and len(r2) == 1 and r2[0]["acted"] is False
          and r2[0]["mode"] == "log" and abs(r2[0]["delta"] - 0.25) < 1e-9, f"{getattr(i2, 'action', None)} rows={r2}")

    i3 = decide(_rec("d3-above", 0.31))
    check("D3 |delta| 0.31 is above the floor: no close, no row",
          i3 is not None and i3.action != "CLOSE" and not [r for r in _rows() if r["trade_id"] == "d3-above"],
          f"{getattr(i3, 'condition', None)}")

    from datetime import datetime
    t0 = datetime.fromisoformat(ENTRY_UTC).timestamp()
    a, b = (M.breakout_delta_floor(_rec("d4", 0.25), now_epoch=t0 + 599),
            M.breakout_delta_floor(_rec("d4", 0.25), now_epoch=t0 + 600))
    check("D4 the 10-minute wait: 599 s undecided, 600 s decided", a is None and b == 0.25, f"{a} / {b}")

    i5a, i5b = decide(_rec("d5-none", None)), decide(_rec("d5-zero", 0.0))
    check("D5 an UNREAD delta (None, 0.0) holds",
          i5a.action != "CLOSE" and i5b.action != "CLOSE"
          and not [r for r in _rows() if r["trade_id"] in ("d5-none", "d5-zero")],
          f"{i5a.condition} {i5b.condition}")

    n0 = len(_rows())
    i6 = decide(_rec("d6-off", 0.25), mode="off")
    check("D6 off mode: no close and no row", i6.action != "CLOSE" and len(_rows()) == n0, f"{i6.condition}")

    i7 = decide(_rec("d7-hard", 0.25), prem=0.95)
    check("D7 the hard stop outranks it: premium through stop_premium closes as hard_stop",
          i7.action == "CLOSE" and i7.condition == "hard_stop", f"{i7.condition}")

    i8 = decide(_rec("d8-short", -0.20, "short"))
    check("D8 a SHORT (put, delta -0.20) Breakout is closed on |delta|",
          i8.action == "CLOSE" and i8.condition == "delta_floor", f"{i8.condition}")

    x, y = decide(_rec("d9-twice", 0.2)), decide(_rec("d9-twice", 0.2))
    r9 = [r for r in _rows() if r["trade_id"] == "d9-twice"]
    check("D9 deterministic + recorded once: CLOSE twice, ONE row, acted true",
          x.action == "CLOSE" and y.action == "CLOSE" and len(r9) == 1 and r9[0]["acted"] is True, f"rows={r9}")

    i10 = decide(_rec("d10-run", 0.20, strategy="RunawayContinuation"))
    check("D10 Breakout only: a Runaway at delta 0.20 is never closed on delta_floor",
          i10 is None or i10.condition != "delta_floor", f"{getattr(i10, 'condition', None)}")

    m = [_cfg_probe({}), _cfg_probe({"OT_BRK_DFLOOR": "log"}), _cfg_probe({"OT_BRK_DFLOOR": "OFF"}),
         _cfg_probe({"OT_BRK_DFLOOR": "yes"})]
    check("D11 OT_BRK_DFLOOR: unset -> trade; log / OFF honoured; 'yes' -> log, refused named",
          m[0] == ["trade", ""] and m[1] == ["log", ""] and m[2] == ["off", ""] and m[3] == ["log", "yes"], f"{m}")

    e = dict(os.environ, OT_BRK_DFLOOR="log", OT_PARK="trade", OT_INSTRUMENT=os.environ.get("OT_INSTRUMENT", "QQQ"))
    p = subprocess.run([sys.executable, "-c", "import main;print(main._banner_dials())"], cwd=ROOT, env=e,
                       capture_output=True, text=True, timeout=240)
    out = (p.stdout.strip().splitlines() or [""])[-1]
    check("D12 the Service mode line names 'brk_dfloor=log' and 'park=trade' (the REAL main._banner_dials)",
          p.returncode == 0 and "brk_dfloor=log" in out and "park=trade" in out, out or p.stderr[-300:])

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
