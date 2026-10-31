#!/usr/bin/env python3
"""
tests/check_brk_noprog.py  v5.1
v5.1  2026-10-31  OTV5 r68 (CFG.5) — N11-N13 RE-POINTED, NOT DROPPED (section 38.4). The operator, 2026-10-31: "10&11–defaults are
      fine, take them out"; "12, same thing. Trade it—I don't want this toggled". config v5.10 reads neither OT_BREAKOUT_END
      nor OT_BRK_NOPROG: N11 pins Breakout's end at 10:30 with the key unset, 15:40 or junk; N12 pins trade with it unset,
      log or off; N13 the banner shows both with the keys set otherwise. N1-N10, N14 (the rule itself) unchanged.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
BREAKOUT'S NO-PROGRESS EXIT (BRK.8) AND ITS PER-BOX ENTRY END (BRK.9).
v1.0  2026-10-10  OTV4TEST r265. The operator, 2026-10-10 13:37 ET: "Yes, to all. Study, fit & apply";
      11:47 ET: "...it should be implemented as long as this counter factual evidence is available for next
      Saturday." Rule N3 of /var/tmp/sat_1010/PREREG_MONDAY.md (sha 8beecd81): after 2 consecutive CLOSED 1m
      bars with no new favourable extreme, a Breakout with < 0.5 R of progress since entry is cut.
  N1  trade mode: the REAL ManagementPlan.decide CLOSES a stalled Breakout, condition "no_progress"
  N2  log mode: the same trade HOLDS, and one counterfactual row (acted false) is written
  N3  progress >= 0.5 R before the stall: no cut, ever (the decision is made once, at the stall)
  N4  a new favourable extreme resets the stall count (undecided)
  N5  the FORMING bar never counts: with only one stalled bar closed, undecided
  N6  off mode: no cut, no row
  N7  the hard stop outranks it (premium through stop_premium -> hard_stop, not no_progress)
  N8  a SHORT (put) Breakout: the mirror on the lows
  N9  deterministic + recorded once: decide twice -> CLOSE twice, ONE row (acted true)
  N10 the exit is priced by the engine's own rule: the mark ladder ("walk")
  N11 config: Breakout's end is 10:30 whatever OT_BREAKOUT_END says (r68: not read)
  N12 config: no-progress is trade whatever OT_BRK_NOPROG says (r68: not read)
  N13 the Service mode line names breakout_end=10:30 and brk_noprog=trade (the REAL main._banner_dials)
  N14 the ENTRY bar never counts: a stalled entry bar + one stalled bar after it is still undecided
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_brk_noprog_")
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


# entry 09:35:30 ET (13:35:30 UTC) at 101.30, stop 100.55 -> R 0.75. Bars are stamped at their OPEN (ET).
ENTRY_UTC = "2026-10-08T13:35:30+00:00"


def _df(highs_lows, start="2026-10-08 09:30"):
    import pandas as pd
    rows = [{"open": (h + l) / 2, "high": h, "low": l, "close": (h + l) / 2, "volume": 100} for h, l in highs_lows]
    return pd.DataFrame(rows, index=pd.date_range(start, periods=len(rows), freq="1min", tz="America/New_York"))


PRE = [(101.0, 100.6)] * 6                        # 09:30-09:35 (09:35 is the entry bar - never counted)
STALL = PRE + [(101.40, 101.20), (101.35, 101.25), (101.38, 101.28), (101.30, 101.20)]   # best 0.13 R
RUN = PRE + [(101.80, 101.30), (101.70, 101.50), (101.75, 101.55), (101.6, 101.5)]       # best 0.67 R
RESET = PRE + [(101.40, 101.20), (101.35, 101.25), (101.45, 101.30), (101.40, 101.30)]  # new extreme at 09:38


def _rec(tid, direction="long"):
    long_ = direction == "long"
    return {"trade_id": tid, "strategy": "Breakout", "symbol": "QQQ", "direction": direction,
            "option_side": "call" if long_ else "put", "entry_premium": 2.0, "stop_premium": 1.0,
            "target_premium": 0.0, "underlying_entry": 101.30 if long_ else 100.70,
            "underlying_stop": 100.55 if long_ else 101.45, "entry_time": ENTRY_UTC, "contracts": 10,
            "option_symbol": "QQQ   261008C00101000", "current_delta": 0.4, "is_butterfly": 0}


def _rows():
    f = os.path.join(CF, "breakout_no_progress.jsonl")
    return [json.loads(x) for x in open(f)] if os.path.exists(f) else []


def _cfg_probe(env):
    e = {k: v for k, v in os.environ.items() if k not in ("OT_BREAKOUT_END", "OT_BRK_NOPROG")}
    e.update(env)
    code = ("import config,json;print(json.dumps([config.ENTRY_WINDOWS['Breakout'][1], None,"
            " config.ENTRY_WINDOWS['RunawayContinuation'][1], config.BRK_NOPROG_MODE, None]))")
    p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=e, capture_output=True, text=True, timeout=120)
    return json.loads(p.stdout.strip().splitlines()[-1]) if p.returncode == 0 and p.stdout.strip() else p.stderr[-300:]


def main():
    print("check_brk_noprog")
    try:
        import pandas  # noqa: F401
        import config
        import strategy.management as M
        import execution.exit_engine as XE
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2
    if not hasattr(M, "breakout_no_progress") or not hasattr(config, "BRK_NOPROG_MODE"):
        check("N0 the no-progress exit exists (management.breakout_no_progress, config.BRK_NOPROG_MODE)", False,
              "absent - this tree predates r265")
        print(f"\nRED — 1 of 1 failed: N0")
        return 1
    plan = M.get_management_plan()

    def decide(rec, df, prem=1.9, mode="trade"):
        config.BRK_NOPROG_MODE = mode
        return plan.decide(rec, prem, df_1m=df, open_records=[rec], current_price=float(df["close"].iloc[-1]),
                           ctx={}, exit_engine=None)

    i1 = decide(_rec("n1-trade"), _df(STALL))
    check("N1 trade mode: a stalled Breakout (best 0.13 R) is CLOSED with condition no_progress",
          i1 is not None and i1.action == "CLOSE" and i1.condition == "no_progress" and i1.reason.startswith("no_progress:"),
          f"{getattr(i1, 'action', None)} {getattr(i1, 'condition', None)} {getattr(i1, 'reason', None)!r}")

    i2 = decide(_rec("n2-log"), _df(STALL), mode="log")
    r2 = [r for r in _rows() if r["trade_id"] == "n2-log"]
    check("N2 log mode: the same trade HOLDS and one counterfactual row (acted false, mode log) is written",
          i2 is not None and i2.action != "CLOSE" and len(r2) == 1 and r2[0]["acted"] is False and r2[0]["mode"] == "log"
          and abs(r2[0]["best_r"] - 0.1333) < 0.001,
          f"{getattr(i2, 'action', None)} rows={r2}")

    i3 = decide(_rec("n3-run"), _df(RUN))
    v3 = M.breakout_no_progress(_rec("n3-run"), _df(RUN))
    check("N3 progress 0.67 R before the stall: decided once, NOT cut; decide does not close",
          v3 is not None and v3["cut"] is False and i3.action != "CLOSE" and not [r for r in _rows() if r["trade_id"] == "n3-run"],
          f"verdict={v3} action={getattr(i3, 'action', None)}")

    v4 = M.breakout_no_progress(_rec("n4"), _df(RESET))
    check("N4 a new favourable extreme resets the stall count (undecided at 09:39)", v4 is None, f"{v4}")

    import pandas as pd
    t_0938_half = pd.Timestamp("2026-10-08 09:38:30", tz="America/New_York").timestamp()
    t_0939_half = pd.Timestamp("2026-10-08 09:39:30", tz="America/New_York").timestamp()
    v5a = M.breakout_no_progress(_rec("n5"), _df(STALL), now_epoch=t_0938_half)
    v5b = M.breakout_no_progress(_rec("n5"), _df(STALL), now_epoch=t_0939_half)
    check("N5 the forming bar never counts: 09:38:30 undecided (one stalled bar closed), 09:39:30 decided",
          v5a is None and v5b is not None and v5b["cut"] is True, f"{v5a} / {v5b}")

    n_before = len(_rows())
    i6 = decide(_rec("n6-off"), _df(STALL), mode="off")
    check("N6 off mode: no cut and no row", i6 is not None and i6.action != "CLOSE" and len(_rows()) == n_before,
          f"{getattr(i6, 'action', None)} rows {n_before}->{len(_rows())}")

    i7 = decide(_rec("n7-hard"), _df(STALL), prem=0.95)
    check("N7 the hard stop outranks it: premium through stop_premium closes as hard_stop",
          i7 is not None and i7.action == "CLOSE" and i7.condition == "hard_stop", f"{getattr(i7, 'condition', None)}")

    SHORT = PRE + [(100.80, 100.60), (100.75, 100.65), (100.72, 100.62), (100.8, 100.7)]   # best (100.70-100.60)/0.75
    i8 = decide(_rec("n8-short", "short"), _df(SHORT))
    check("N8 a SHORT (put) Breakout stalls on the lows and is cut",
          i8 is not None and i8.action == "CLOSE" and i8.condition == "no_progress", f"{getattr(i8, 'condition', None)}")

    a = decide(_rec("n9-twice"), _df(STALL))
    b = decide(_rec("n9-twice"), _df(STALL))
    r9 = [r for r in _rows() if r["trade_id"] == "n9-twice"]
    check("N9 deterministic + recorded once: CLOSE on both ticks, ONE row, acted true",
          a.action == "CLOSE" and b.action == "CLOSE" and len(r9) == 1 and r9[0]["acted"] is True, f"rows={r9}")

    pol = XE.ExitEngine._exit_policy({"strategy": "Breakout"}, i1.reason if i1 else "no_progress:")
    check("N10 the cut is priced by the engine's own rule: the mark ladder ('walk')", pol == "walk", pol)

    # r68 (CFG.5): the operator, 2026-10-31, "10&11–defaults are fine, take them out"; "12, same thing. Trade it—I
    # don't want this toggled". Neither key is read: whatever the unit says, Breakout ends 10:30 and the cut trades.
    c_none = _cfg_probe({})
    c_set = _cfg_probe({"OT_BREAKOUT_END": "15:40"})
    c_junk = _cfg_probe({"OT_BREAKOUT_END": "0940x"})
    check("N11 Breakout's end is 10:30 with OT_BREAKOUT_END unset, 15:40 or junk (the key is not read); Runaway 10:30",
          isinstance(c_none, list) and c_none[0] == [10, 30] and c_none[2] == [10, 30]
          and c_set == c_none and c_junk == c_none, f"none={c_none} set={c_set} junk={c_junk}")

    m_none, m_log, m_off = (_cfg_probe({}), _cfg_probe({"OT_BRK_NOPROG": "log"}), _cfg_probe({"OT_BRK_NOPROG": "off"}))
    check("N12 no-progress is 'trade' with OT_BRK_NOPROG unset, log or off (the key is not read)",
          isinstance(m_none, list) and m_none[3] == "trade" and m_log[3] == "trade" and m_off[3] == "trade",
          f"{m_none} {m_log} {m_off}")

    e = dict(os.environ, OT_BREAKOUT_END="15:40", OT_BRK_NOPROG="log", OT_INSTRUMENT=os.environ.get("OT_INSTRUMENT", "QQQ"))
    p = subprocess.run([sys.executable, "-c", "import main;print(main._banner_dials())"], cwd=ROOT, env=e,
                       capture_output=True, text=True, timeout=240)
    out = (p.stdout.strip().splitlines() or [""])[-1]
    check("N13 the Service mode line names 'breakout_end=10:30' and 'brk_noprog=trade' with the keys set otherwise "
          "(the REAL main._banner_dials)",
          p.returncode == 0 and "breakout_end=10:30" in out and "brk_noprog=trade" in out, out or p.stderr[-300:])

    ENTRY_STALL = [(101.0, 100.6)] * 5 + [(101.25, 101.10), (101.28, 101.15), (101.2, 101.1)]
    t_0937_half = pd.Timestamp("2026-10-08 09:37:30", tz="America/New_York").timestamp()
    v14 = M.breakout_no_progress(_rec("n14"), _df(ENTRY_STALL), now_epoch=t_0937_half)
    check("N14 the ENTRY bar never counts: entry bar + one stalled bar closed by 09:37:30 -> undecided", v14 is None, f"{v14}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
