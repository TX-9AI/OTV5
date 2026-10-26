#!/usr/bin/env python3
"""
tests/check_volt_exit_text.py  v5.0
v5.0  2026-10-25  (DOC.31) — new. VOLT'S EXIT REASONS NAME THE FRAME THEY READ. _evaluate_volt reads the close of the
      newest COMPLETED 5m bar (df_5m.iloc[-2], the operator's 2026-09-21 frame ruling) and wrote "1m close" into both its
      structure-stop and trail-stop reasons, so every VOLT exit row misdescribed its own evidence; and its docstring
      still described a "3x5m structural extreme" stop and R = |entry-stop|, both superseded by OTV4TEST r72. Born red on
      ffe10bf at T1, T2, T3 and T4.

DRIVEN: execution.exit_engine.ExitEngine()._evaluate_volt runs on fixture records and 5m frames, with the clock seam
(is_hard_close_time) pinned so the hard close cannot fire.

  T1  a long VOLT whose newest completed 5m bar closes below the stop (= the entry) exits with a reason that says
      "volt_structure_stop: 5m close" — and the exit itself still fires (no logic change)
  T2  an armed trail breached on a 5m close exits with "volt_trail_stop: 5m close", the floor where it always was
  T3  the docstring no longer describes the 3x5m structural extreme or R = |entry-stop|, and names underlying_target
  T4  no string constant in _evaluate_volt's code (docstring and comments aside) says "1m close"
"""
import ast
import datetime as dt
import inspect
import os
import sys
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


def _frame(pd, closes):
    return pd.DataFrame(
        [{"open": c, "high": c, "low": c, "close": c, "volume": 1.0} for c in closes],
        index=pd.DatetimeIndex([dt.datetime(2026, 9, 21, 10, 5 * i) for i in range(len(closes))]))


def main():
    import pandas as pd
    import execution.exit_engine as EE

    base = {"trade_id": "VOLTTEXT", "strategy": "VOLT", "direction": "long", "entry_premium": 1.00,
            "contracts": 1, "underlying_entry": 100.0, "underlying_stop": 100.0, "underlying_target": 101.0,
            "stop_premium": 0.75}
    orig = EE.is_hard_close_time
    EE.is_hard_close_time = lambda: False
    try:
        d1 = EE.ExitEngine()._evaluate_volt(dict(base), 1.10, None, _frame(pd, (100.0, 99.40, 99.50)))
        rec2 = dict(base, _volt_peak=102.0)
        d2 = EE.ExitEngine()._evaluate_volt(rec2, 1.20, None, _frame(pd, (101.5, 100.90, 100.95)))
    finally:
        EE.is_hard_close_time = orig

    r1 = d1.exit_reason or ""
    check("T1 a 5m close through the stop exits as 'volt_structure_stop: 5m close ...'",
          d1.should_exit and r1.startswith("volt_structure_stop: 5m close 99.40") and "1m close" not in r1,
          "exit=%s reason=%r" % (d1.should_exit, r1))

    r2 = d2.exit_reason or ""
    check("T2 an armed trail breached on a 5m close exits as 'volt_trail_stop: 5m close ...', floor 101.00",
          d2.should_exit and r2.startswith("volt_trail_stop: 5m close 100.90") and "lock 101.00" in r2
          and abs((d2.new_trail_stop or 0) - 101.0) < 1e-9,
          "exit=%s reason=%r trail=%s" % (d2.should_exit, r2, d2.new_trail_stop))

    doc = inspect.getdoc(EE.ExitEngine._evaluate_volt) or ""
    flat = " ".join(doc.split())
    check("T3 the docstring drops the 3x5m extreme and R = |entry-stop|, and names underlying_target",
          "3x5m structural extreme" not in flat and "R = |entry-stop|" not in flat and "underlying_target" in flat,
          "doc still says: %s" % [p for p in ("3x5m structural extreme", "R = |entry-stop|") if p in flat])

    fn = ast.parse(textwrap.dedent(inspect.getsource(EE.ExitEngine._evaluate_volt))).body[0]
    body = fn.body[1:] if (fn.body and isinstance(fn.body[0], ast.Expr)
                           and isinstance(getattr(fn.body[0], "value", None), ast.Constant)) else fn.body
    consts = [n.value for b in body for n in ast.walk(b) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    bad = [c for c in consts if "1m close" in c]
    check("T4 no string in _evaluate_volt's code says '1m close'", not bad and len(consts) > 5,
          "found %s (of %d strings)" % (bad, len(consts)))

    print("\n%d/%d GREEN" % (len(RAN) - len(FAILED), len(RAN)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
