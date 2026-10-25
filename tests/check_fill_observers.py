#!/usr/bin/env python3
"""
tests/check_fill_observers.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.1  2026-10-13  OTV4TEST r280 (EXIT.5). O3 RE-POINTED, NOT DROPPED (section 38.4): "off" now sets BOTH OT_FILL_OBSERVE and
      OT_FLOOR_WATCH, because the acting watch (default trade) is its own switch; F6 in check_floor_watch pins that.
TWO FILL OBSERVERS, RECORD ONLY (PMAP.1 + FILL.2, execution/fill_observers.py).
v1.0  2026-10-11  OTV4TEST r270. The operator, 2026-10-11 19:14 ET: "I think we should have both 1 & 2, observe only to
      see if we can use it to improve fills".
  O1  watched_stop: the trail when armed, else stop_premium, on a single long; NONE for the Hunt (held floor), VOLT
      (underlying trail), ORB, a butterfly, a spread, and a position already RESTING (r266)
  O2  the model: implied vol round-trips Black-Scholes; U* re-prices to the stop level (call and put)
  O3  the watch, on a real sqlite chain_marks: a fresh crossed quote writes ONE row; a stale quote (> 4 s), a quote
      above the level, a Hunt, a second crossing inside 10 s, and OT_FILL_OBSERVE=off write none
  O4  sleep_observing sleeps the SAME total in 2 s slices, observes between them, and survives an observer that raises
  O5  through the REAL PositionManager._manage_one (paper, stub stores): one map row per position per minute with iv
      and u_at_stop, the next minute carries the previous map's prediction error; the trade's exit is IDENTICAL with
      the observers on and off
  O6  RECORD ONLY: the module imports no exit, order or position code and calls no exit function (AST)
  O7  main: the end-of-tick sleep is sleep_observing (AST, in main_loop) and the Service mode line names
      fill_observe=on / off
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
"""
import ast
import json
import os
import sqlite3
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_fill_observers_")
for k, v in {"OT_TRADES_DB": "t.db", "OT_DERIVED_DB": "d.db", "OT_FEED_DB": "f.db", "OT_LOG_FILE": "bot.log",
             "OT_RESTING_DB": "r.db", "OT_SIGNAL_JOURNAL_DIR": "sj", "OT_COUNTERFACTUAL_DIR": "cf",
             "OT_RESTING_STOP_STATE": "rest_state.json"}.items():
    os.environ[k] = os.path.join(_TD, v)
os.environ.pop("OT_FILL_OBSERVE", None)
os.environ.pop("OT_FLOOR_WATCH", None)
os.environ.pop("OT_RESTING_STOP", None)
FAILED, RAN = [], []
NOW = 1791822000.0          # 2026-10-12 12:20 ET - 3 h 40 m before the 10-12 expiry's 16:00 bell


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _rows(name):
    f = os.path.join(_TD, "cf", name)
    return [json.loads(x) for x in open(f)] if os.path.exists(f) else []


def _rec(tid, **kw):
    r = {"trade_id": tid, "strategy": "Breakout", "symbol": "QQQ", "direction": "long", "option_side": "call",
         "entry_premium": 2.00, "stop_premium": 1.00, "target_premium": 0.0, "trail_stop": 0.0,
         "underlying_entry": 0.0, "underlying_stop": 0.0, "contracts": 10, "is_butterfly": 0,
         "option_symbol": "QQQ   261012C00750000", "expiry": "2026-10-12",
         "entry_time": "2026-10-12T13:40:00+00:00", "status": "open"}
    r.update(kw)
    return r


class _C:
    def __init__(self, strike, sym): self.strike, self.streamer_symbol = strike, sym


class _Chain:
    def __init__(self, spot=748.0):
        self.spot_price = spot
        self.calls = [_C(750.0, ".QQQ261012C750"), _C(752.0, ".QQQ261012C752")]
        self.puts = [_C(745.0, ".QQQ261012P745")]


def _feed(rows):
    p = os.path.join(_TD, f"feed_{len(os.listdir(_TD))}.db")
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE chain_marks (streamer_symbol TEXT PRIMARY KEY, bid REAL, ask REAL, delta REAL, gamma REAL,"
              " theta REAL, vega REAL, iv REAL, updated_epoch REAL NOT NULL)")
    c.executemany("INSERT INTO chain_marks (streamer_symbol, bid, ask, updated_epoch) VALUES (?,?,?,?)", rows)
    c.commit(); c.close()
    return p


def main():
    print("check_fill_observers")
    try:
        import pandas  # noqa: F401
        import config
        import execution.exit_engine as XE
        import execution.position_manager as PM
        import execution.resting_stop as RS
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2
    try:
        import execution.fill_observers as F
    except Exception as exc:                                    # noqa: BLE001
        check("O0 execution/fill_observers.py exists", False, f"{type(exc).__name__}: {exc} - this tree predates r270")
        print("\nRED — 1 of 1 failed: O0")
        return 1

    # ── O1 watched_stop ─────────────────────────────────────────────────────
    RS.begin(_rec("rest1"), "hard_stop_50%", 0.95, 1.00, now=NOW)
    got = [F.watched_stop(_rec("a")), F.watched_stop(_rec("b", trail_stop=2.40)),
           F.watched_stop(_rec("c", strategy="LiquidityHunt")), F.watched_stop(_rec("d", strategy="VOLT", trail_stop=752.9)),
           F.watched_stop(_rec("e", strategy="ORBStrategy")), F.watched_stop(_rec("f", center_symbol="x")),
           F.watched_stop(_rec("g", short_symbol="y", spread_width=2.0)), F.watched_stop(_rec("rest1"))]
    RS.finish("rest1", 1.0, "filled at the level", now=NOW)
    check("O1 watched_stop: 1.00 / trail 2.40; None for Hunt, VOLT, ORB, a fly, a spread, a resting row",
          got == [1.00, 2.40, None, None, None, None, None, None], f"{got}")

    # ── O2 the model ────────────────────────────────────────────────────────
    T = 3.5 / (365 * 24)
    vc = F.implied_vol(1.10, 748.0, 750.0, T, True); vp = F.implied_vol(0.90, 748.0, 745.0, T, False)
    uc = F.underlying_at(0.80, 750.0, T, vc, True, 748.0) if vc else None
    up = F.underlying_at(0.60, 745.0, T, vp, False, 748.0) if vp else None
    ok2 = (vc and vp and abs(F.bs_price(748.0, 750.0, T, vc, True) - 1.10) < 1e-6
           and abs(F.bs_price(748.0, 745.0, T, vp, False) - 0.90) < 1e-6
           and uc and up and abs(F.bs_price(uc, 750.0, T, vc, True) - 0.80) < 1e-4 and uc < 748.0
           and abs(F.bs_price(up, 745.0, T, vp, False) - 0.60) < 1e-4 and up > 748.0)
    check("O2 implied vol round-trips Black-Scholes; U* re-prices to the stop (call below spot, put above)", ok2,
          f"vc={vc} vp={vp} uc={uc} up={up}")

    # ── O3 the watch ────────────────────────────────────────────────────────
    ch = _Chain()
    db = _feed([(".QQQ261012C750", 0.94, 0.98, NOW - 2.0), (".QQQ261012C752", 0.70, 0.74, NOW - 6.0),
                (".QQQ261012P745", 1.20, 1.30, NOW - 1.0)])
    n0 = len(_rows("quote_watch.jsonl"))
    w1 = F.observe_watch([_rec("w1")], ch, now=NOW, db_path=db)                                      # 0.96 <= 1.00, 2 s
    w2 = F.observe_watch([_rec("w2", option_symbol="QQQ   261012C00752000")], ch, now=NOW, db_path=db)  # stale 6 s
    w3 = F.observe_watch([_rec("w3", option_symbol="QQQ   261012P00745000", option_side="put")], ch, now=NOW, db_path=db)
    w4 = F.observe_watch([_rec("w4", strategy="LiquidityHunt")], ch, now=NOW, db_path=db)
    w5 = F.observe_watch([_rec("w1")], ch, now=NOW + 5.0,                                          # inside 10 s, FRESH
                         db_path=_feed([(".QQQ261012C750", 0.94, 0.98, NOW + 4.0)]))
    w6 = F.observe_watch([_rec("w1")], ch, now=NOW + 3.0 + 10.0, db_path=_feed([(".QQQ261012C750", 0.94, 0.98, NOW + 12.0)]))
    os.environ["OT_FILL_OBSERVE"] = "off"; os.environ["OT_FLOOR_WATCH"] = "off"   # r280: the acting watch has its own switch
    w7 = F.observe_watch([_rec("w7")], ch, now=NOW + 60.0, db_path=_feed([(".QQQ261012C750", 0.94, 0.98, NOW + 59.0)]))
    os.environ.pop("OT_FILL_OBSERVE"); os.environ.pop("OT_FLOOR_WATCH")
    rows3 = _rows("quote_watch.jsonl")[n0:]
    check("O3 the watch: one row for a fresh crossed quote; none stale / above / Hunt / inside 10 s / off; again after 10 s",
          len(w1) == 1 and w1[0]["mid"] == 0.96 and abs(w1[0]["quote_age_s"] - 2.0) < 1e-9 and w1[0]["level"] == 1.00
          and w2 == [] and w3 == [] and w4 == [] and w5 == [] and len(w6) == 1 and w7 == []
          and [r["trade_id"] for r in rows3] == ["w1", "w1"], f"w1={w1} w2={w2} w3={w3} w4={w4} w5={w5} w6={w6} w7={w7} rows={rows3}")

    # ── O4 sleep_observing ──────────────────────────────────────────────────
    clock = [0.0]; slept = []; calls = []
    def _sl(s): slept.append(s); clock[0] += s
    F.sleep_observing(11.0, lambda: calls.append(1) or [], lambda: None, _sleep=_sl, _clock=lambda: clock[0])
    def _boom(): raise RuntimeError("observer failure")
    clock2 = [0.0]; slept2 = []
    raised = None
    try:
        F.sleep_observing(5.0, _boom, lambda: None, _sleep=lambda s: (slept2.append(s), clock2.__setitem__(0, clock2[0] + s)),
                          _clock=lambda: clock2[0])
    except Exception as exc:                                    # noqa: BLE001
        raised = exc
    check("O4 sleep_observing: the same total (11 s) in 2 s slices, observing between; a raising observer is contained",
          abs(sum(slept) - 11.0) < 1e-9 and max(slept) <= 2.0 and len(calls) == len(slept) == 6
          and raised is None and abs(sum(slept2) - 5.0) < 1e-9, f"slept={slept} calls={len(calls)} raised={raised}")

    # ── O5 through the REAL _manage_one ─────────────────────────────────────
    XE.is_hard_close_time = lambda *a, **k: False
    config.RESTING_STOP_MODE = "off"

    class _TL:
        def __init__(self): self.exits = []
        def update_current_premium(self, *a, **k): pass
        def update_trail_stop(self, *a, **k): pass
        def set_exit_contract(self, *a, **k): return True
        def get_open_trades(self): return []
        def log_exit(self, **k): self.exits.append(k)

    class _Alert:
        def __getattr__(self, n): return lambda *a, **k: None
    PM.get_alert_manager = lambda: _Alert()

    class _T:
        def __init__(self, t): self.t = t
        def time(self): return self.t
    real_time = F.time

    def run(tid, marks, times):
        pm = PM.PositionManager(paper_trading=True); tl = _TL(); pm._trade_logger = tl
        rec = _rec(tid); seq = list(marks); kept = []
        pm._fetch_current_premium = lambda record, chain=None: seq.pop(0)
        for t in times:
            F.time = _T(t)
            kept.append(pm._manage_one(rec, None, _Chain(748.0)))
        F.time = real_time
        return tl.exits, kept

    m0 = len(_rows("premium_map.jsonl"))
    ex_on, k_on = run("m1", [1.50, 1.45, 1.40, 0.95], [NOW, NOW + 30, NOW + 61, NOW + 75])
    maps = [r for r in _rows("premium_map.jsonl")[m0:] if r["trade_id"] == "m1"]
    os.environ["OT_FILL_OBSERVE"] = "off"
    m1 = len(_rows("premium_map.jsonl"))
    ex_off, k_off = run("m2", [1.50, 1.45, 1.40, 0.95], [NOW, NOW + 30, NOW + 61, NOW + 75])
    off_rows = len(_rows("premium_map.jsonl")) - m1
    os.environ.pop("OT_FILL_OBSERVE")
    same = (k_on == k_off == [True, True, True, False] and len(ex_on) == len(ex_off) == 1
            and ex_on[0]["exit_price"] == ex_off[0]["exit_price"] and ex_on[0]["exit_reason"] == ex_off[0]["exit_reason"])
    check("O5 real _manage_one: one map row per minute (iv, u_at_stop; the 2nd carries prev_err); off writes none; "
          "the exit is IDENTICAL on and off",
          len(maps) == 2 and maps[0].get("iv") and maps[0].get("u_at_stop") and maps[0]["watched_stop"] == 1.00
          and "prev_err" in maps[1] and abs(maps[1]["prev_age_s"] - 61.0) < 1e-9 and off_rows == 0 and same,
          f"maps={maps} off_rows={off_rows} on={k_on, ex_on and ex_on[0].get('exit_reason')} off={k_off, ex_off and ex_off[0].get('exit_reason')}")

    # ── O6 record only ──────────────────────────────────────────────────────
    src = open(os.path.join(ROOT, "execution", "fill_observers.py")).read()
    tree = ast.parse(src)
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    calls_ = {(c.func.attr if isinstance(c.func, ast.Attribute) else getattr(c.func, "id", ""))
              for c in ast.walk(tree) if isinstance(c, ast.Call)}
    bad_mods = [m for m in mods if m and any(x in m for x in ("exit_engine", "position_manager", "order", "tasty",
                                                               "limit_ladder", "entry_engine", "broker"))]
    bad_calls = [c for c in calls_ if any(x in c.lower() for x in ("exit", "order", "flatten", "place_"))
]                       # every exit path is named so: _execute_exit, place_exit_order, flatten_all
    check("O6 RECORD ONLY: no exit/order/position import, no exit/order call", not bad_mods and not bad_calls,
          f"imports={bad_mods} calls={bad_calls}")

    # ── O7 main ─────────────────────────────────────────────────────────────
    mt = ast.parse(open(os.path.join(ROOT, "main.py")).read())
    runbot = next((n for n in ast.walk(mt) if isinstance(n, ast.FunctionDef) and n.name == "main_loop"), None)
    wired = runbot is not None and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                                       and c.func.attr == "sleep_observing" for c in ast.walk(runbot))
    e = dict(os.environ, OT_INSTRUMENT=os.environ.get("OT_INSTRUMENT", "QQQ"))
    p1 = subprocess.run([sys.executable, "-c", "import main;print(main._banner_dials())"], cwd=ROOT, env=e,
                        capture_output=True, text=True, timeout=240)
    p2 = subprocess.run([sys.executable, "-c", "import main;print(main._banner_dials())"], cwd=ROOT,
                        env=dict(e, OT_FILL_OBSERVE="off"), capture_output=True, text=True, timeout=240)
    o1 = (p1.stdout.strip().splitlines() or [""])[-1]; o2 = (p2.stdout.strip().splitlines() or [""])[-1]
    check("O7 main_loop's end-of-tick sleep is sleep_observing; the Service mode line names fill_observe=on / off",
          wired and "fill_observe=on" in o1 and "fill_observe=off" in o2, f"wired={wired} on={o1[-80:]} off={o2[-80:]}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
