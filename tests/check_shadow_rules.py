#!/usr/bin/env python3
"""
tests/check_shadow_rules.py  v5.0
v5.0  2026-11-08  OTV5 r90 (SHADOW.1) - THE TWO LOG-ONLY RULES RECORD ON EVERY DECISION, MATCH THEIR STUDIES, AND
      CANNOT CHANGE A DECISION. The operator, 2026-11-08: "Log only: opening range rule and SMA 50 rule, confirm it's
      logging Monday morning."
  U1  HUNT_OR_EM matches S5's or_width_em to 1e-9 on every study trade entered at/after 09:45 (the full 15-bar range
      was closed), and its verdict equals the frozen rule (< 0.927 would_skip) on each
  U1b the threshold is the frozen 0.927 (0.926 skips, 0.928 keeps)
  U2  NO LOOKAHEAD: an entry at 09:37 reads only the 7 closed bars, says or_bars=7/15 partial, and the ratio is the
      7-bar one (a 15-bar read here is the study's lookahead)
  U3  never silent: no EM and no IV -> verdict unknown with its reason; an unreadable store -> unknown; no closed bar
      -> unknown
  U4  PARK_SMA50 on the box's own TastyTrade 1d closes (fixture: NVDA and SPX, pulled read-only 11-08) agrees with
      S4's S1d_slope on all 31 study trades it can read (61+ prior closes); the math is S4's (sma(dc) vs sma(dc[:-10]))
  U5  fewer than 61 prior closes -> unknown, "the study keeps"; today's forming 1d bar is never read
  N1  Hunt, the REAL generate_signal on check_liquidity_hunt's H2 fixture: the fire writes exactly ONE
      shadow_hunt_or_em plan_check row on the TAKE tick and one [shadow-rule] line; the signal, the plan_tick
      verdict and its reason are IDENTICAL with the shadow on, with it raising inside, and with it removed
  N2  PARK, the REAL generate_signal on check_park's K1 fixture plus 1d closes: TAKE carries one shadow_park_sma50
      row; a first hour refused at gate_g still carries it; signal / verdict / reason identical on, raising, removed
  L1  PARK logs one line per day and direction (a repeated tick writes its row but no second line)
  S1  tools/shadow_rule_status.py: GREEN when every decision has its row and line; RED when a decision's row is missing
  C1  no env knob and no configure item: shadow_rules.py reads no os.environ; config.py names no SHADOW key
Run:  python3 tests/check_shadow_rules.py
"""
import json
import logging
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import types
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_shadow_rules_")
FEED = os.path.join(_TD, "f.db")
for _k, _v in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_RESTING_DB", "r.db"), ("OT_COUNTERFACTUAL_DIR", "cf"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(_TD, _v)
os.environ["OT_FEED_DB"] = FEED
os.environ["OT_DECAY_STOP"] = "0"
os.environ.pop("OT_PARK", None)
ET = ZoneInfo("America/New_York")
FIX = os.path.join(ROOT, "tests", "fixtures", "shadow_rules")
FAILED, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  - {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _ms(d, h, m):
    return int(datetime(d.year, d.month, d.day, h, m, tzinfo=ET).timestamp() * 1000)


def _new_feed(rows):
    if os.path.exists(FEED):
        os.remove(FEED)
    c = sqlite3.connect(FEED)
    c.execute("CREATE TABLE candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, ts_epoch_ms INTEGER NOT NULL, "
              "open REAL, high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY (symbol, interval, ts_epoch_ms))")
    c.executemany("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)", rows)
    c.commit()
    c.close()


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, rec):
        self.lines.append(rec.getMessage())


def main():
    from strategy import shadow_rules as SR
    cap = _Cap()
    logging.getLogger("strategy.shadow_rules").addHandler(cap)
    logging.getLogger("strategy.shadow_rules").setLevel(logging.INFO)

    # ── U1 / U2 / U3 : HUNT_OR_EM against S5 ───────────────────────────────────────────────────────────────────────
    S5 = json.load(open(os.path.join(FIX, "s5_hunt.json")))
    bad, n_full, vbad = [], 0, []
    for tr in S5:
        d = date.fromisoformat(tr["day"])
        rows = []
        for ts, h, l, c in tr["bars"]:
            t = datetime.fromisoformat(ts)
            rows.append((tr["symbol"], "1m", _ms(d, t.hour, t.minute), c, h, l, c, 1))
        _new_feed(rows)
        if tr["min_since_open"] < 15:
            continue
        n_full += 1
        r = SR.hunt_or_em(symbol=tr["symbol"], day=d, now_hm=(10, 30), price=100.0, em_platform=tr["em_platform"])
        if r["value"] is None or abs(r["value"] - tr["study_or_width_em"]) > 1e-9:
            bad.append((tr["trade_id"], r))
        if (r["verdict"] == "would_skip") != (tr["study_or_width_em"] < 0.927):
            vbad.append(tr["trade_id"])
    check(f"U1 HUNT_OR_EM = S5 or_width_em on all {n_full} full-range study trades, verdict = the frozen rule",
          n_full >= 20 and not bad and not vbad, f"{bad[:2]} {vbad[:3]}")
    dd0 = date(2026, 11, 2)
    _new_feed([("TST", "1m", _ms(dd0, 9, 30 + i), 100, 100.9 if i == 3 else 100.5, 100.0, 100.2, 1) for i in range(15)])
    edge = [SR.hunt_or_em(symbol="TST", day=dd0, now_hm=(10, 0), price=100.0, em_platform=0.9 / x)["verdict"]
            for x in (0.90, 0.926, 0.928, 0.95)]
    check("U1b the frozen threshold 0.927: ratio 0.900 / 0.926 would_skip, 0.928 / 0.950 keep",
          SR.HUNT_OR_EM_THRESHOLD == 0.927 and edge == ["would_skip", "would_skip", "keep", "keep"], str(edge))
    tr = next(x for x in S5 if x["min_since_open"] < 15)
    d = date.fromisoformat(tr["day"])
    _new_feed([(tr["symbol"], "1m", _ms(d, datetime.fromisoformat(ts).hour, datetime.fromisoformat(ts).minute),
                c, h, l, c, 1) for ts, h, l, c in tr["bars"]])
    r = SR.hunt_or_em(symbol=tr["symbol"], day=d, now_hm=(9, 37), price=100.0, em_platform=tr["em_platform"])
    b7 = tr["bars"][:7]
    exp7 = (max(b[1] for b in b7) - min(b[2] for b in b7)) / tr["em_platform"]
    check("U2 no lookahead: at 09:37 only the 7 closed bars are read, or_bars=7/15 partial",
          r["value"] is not None and abs(r["value"] - exp7) < 1e-9 and "or_bars=7/15 partial" in r["note"],
          f"{r} exp {exp7}")
    r1 = SR.hunt_or_em(symbol=tr["symbol"], day=d, now_hm=(10, 0), price=100.0, em_platform=None, iv=None)
    os.environ["OT_FEED_DB"] = os.path.join(_TD, "nope", "f.db")
    r2 = SR.hunt_or_em(symbol=tr["symbol"], day=d, now_hm=(10, 0), price=100.0, em_platform=1.0)
    os.environ["OT_FEED_DB"] = FEED
    r3 = SR.hunt_or_em(symbol=tr["symbol"], day=d, now_hm=(9, 30), price=100.0, em_platform=1.0)
    check("U3 never silent: no EM/IV, an unreadable store and no closed bar each answer unknown with a reason",
          all(x["verdict"] == "unknown" and "reason=" in x["note"] for x in (r1, r2, r3)), f"{r1} {r2} {r3}")

    # ── U4 / U5 : PARK_SMA50 against S4 ────────────────────────────────────────────────────────────────────────────
    S4 = json.load(open(os.path.join(FIX, "s4_daily.json")))
    rows = []
    for sym, bars in S4["daily"].items():
        rows += [(sym, "1d", ts, c, c, c, c, 1) for ts, c in bars]
    _new_feed(rows)
    miss = []
    for t in S4["s4"]:
        dd = date.fromisoformat(t["day"])
        r = SR.park_sma50(symbol=t["sym"], day=dd, direction="long" if t["side"] == "call" else "short",
                          index=t["sym"] == "SPX")
        if (r["verdict"] == "keep") != bool(t["s4"]):
            miss.append((t, r))
    check(f"U4 PARK_SMA50 on the box's TT 1d closes agrees with S4's S1d_slope on all {len(S4['s4'])} readable trades",
          len(S4["s4"]) >= 25 and not miss, str(miss[:2]))
    cl = [100.0 + i for i in range(70)]
    s, _ = SR.sma50_slope(cl)
    exp = sum(cl[-50:]) / 50 - sum(cl[:-10][-50:]) / 50
    early = SR.park_sma50(symbol="SPX", day=date(2026, 8, 1), direction="long", index=True)
    first = min(ts for ts, _c in S4["daily"]["SPX"])
    d_last = datetime.fromtimestamp(max(ts for ts, _c in S4["daily"]["SPX"]) / 1000, timezone.utc).date()
    n_before = len(SR.daily_closes_before("SPX", d_last))
    check("U5 S4's math (slope = 10.0 on a +1/day line); < 61 closes -> unknown, the study keeps; today's bar unread",
          abs(s - exp) < 1e-9 and abs(s - 10.0) < 1e-9 and early["verdict"] == "unknown"
          and "keeps" in early["note"] and n_before == len(S4["daily"]["SPX"]) - 1 and first > 0,
          f"{s} {early} {n_before}")

    # ── N1 : the REAL Hunt fire (check_liquidity_hunt H2's fixture) ─────────────────────────────────────────────────
    import pandas as pd
    from strategy import plan as P
    from data.derived_store import DerivedStore
    import strategy.liquidity_hunt as LH

    class St:
        def __init__(s):
            s.conn = sqlite3.connect(":memory:")
            s.conn.row_factory = sqlite3.Row

        def commit(s):
            s.conn.commit()

    class _G:
        def __init__(s, k, prem, delta, gamma):
            s.strike, s.mark, s.ask, s.bid = float(k), prem, prem + 0.02, prem - 0.02
            s.delta, s.gamma, s.theta, s.expiry, s.open_interest, s.symbol = delta, gamma, -0.04, "x", 100, f"O{k}"
            s.iv = 0.30

    today = datetime.now(ET).date()
    _new_feed([("TST", "1m", _ms(today, 9, 30 + i), 100.5, 100.9 - 0.01 * i, 100.1 + 0.01 * i, 100.5, 1)
               for i in range(15)])
    real_record = SR.record_hunt

    def hunt_run(mode):
        st = St()
        P.ensure_tables(st)
        P.bind_store(st)
        ds = DerivedStore(path=os.path.join(tempfile.mkdtemp(dir=_TD), "derived.db"))
        ds.mark_level_sync("TST", time.time())
        LH._symbol_of = lambda: "TST"
        now = time.time()
        ds.upsert_level(("TST:prev_day:102.50", "TST", 102.5, "resistance", "prev_day", "day", now - 3600, 0, None, 0,
                         None, None, 1))
        ds.upsert_level(("TST:london:97.00", "TST", 97.0, "support", "london", "session", now - 3600, 0, None, 0,
                         None, None, 1))
        orb = types.SimpleNamespace(orb_high=101.0, orb_low=100.0)
        calls = [_G(101, 0.95, 0.46, 0.05), _G(102, 0.48, 0.30, 0.058), _G(103, 0.20, 0.17, 0.04),
                 _G(104, 0.10, 0.08, 0.02)]
        chain = types.SimpleNamespace(calls=calls, puts=[])
        hunt = LH.LiquidityHunt()
        hunt._store = ds
        hunt.planner.symbol = "TST"
        LH.FINISHED.clear()
        if mode == "off":
            SR.record_hunt = lambda *a, **k: None
        cap.lines.clear()
        try:
            frame = pd.DataFrame([{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in
                                  [(100.9, 101.4, 100.8, 101.3), (101.3, 101.5, 101.2, 101.4)]],
                                 index=pd.date_range(f"{today} 09:47", periods=2, freq="1min"))
            P.begin_tick(2.0)
            sig = hunt.generate_signal(orb=orb, price_now=101.3, now_et="09:49", atr_pct=0.14, chain=chain,
                                       df_1m=frame, atm_iv=0.25)
            P.close_tick(st, "TST")
        finally:
            SR.record_hunt = real_record
        tick = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='LiquidityHunt' "
                               "ORDER BY rowid DESC LIMIT 1").fetchone()
        shadow = st.conn.execute("SELECT value, note FROM plan_check WHERE check_name='shadow_hunt_or_em'").fetchall()
        key = None if sig is None else (sig.direction, sig.option_side, sig.underlying_entry, sig.underlying_stop,
                                         sig.underlying_target, float(sig.strike), sig.entry_premium, sig.hunt_entry)
        return key, (tick["verdict"], tick["reason"]) if tick else None, [tuple(x) for x in shadow], \
            [x for x in cap.lines if "HUNT_OR_EM" in x]
    on = hunt_run("on")
    orig = SR.hunt_or_em                       # raising INSIDE the shadow: hunt_or_em throws, record_hunt must hold
    SR.hunt_or_em = lambda **k: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        raise_ = hunt_run("plain")
    finally:
        SR.hunt_or_em = orig
    off = hunt_run("off")
    check("N1 Hunt fire: one shadow row + one line; signal / verdict / reason identical with shadow on, raising, off",
          on[0] is not None and on[1][0] == "TAKE" and len(on[2]) == 1 and on[2][0][1].startswith(("keep", "would_skip"))
          and len(on[3]) == 1 and on[0] == raise_[0] == off[0] and on[1] == raise_[1] == off[1]
          and len(raise_[2]) == 1 and raise_[2][0][1].startswith("unknown") and len(off[2]) == 0,
          f"on={on[1:3]} raise={raise_[1:3]} off={off[1:3]}")

    # ── N2 / L1 : the REAL PARK (check_park K1's fixture) ──────────────────────────────────────────────────────────
    import config
    from strategy.park import Park
    import strategy.park_plan as PP
    DAY, PREV = date(2026, 10, 16), date(2026, 10, 15)
    SYM = "SPX"
    config.INSTRUMENT = SYM

    def park_feed(o930, c1030, c1100, prev_close):
        rows = [(SYM, "1m", _ms(DAY, 9, 30), o930, o930 + .1, o930 - .1, o930 + .05, 1),
                (SYM, "1m", _ms(DAY, 10, 30), c1030, c1030 + .1, c1030 - .1, c1030, 1),
                (SYM, "1m", _ms(DAY, 11, 0), c1100, c1100 + .1, c1100 - .1, c1100, 1),
                (SYM, "1m", _ms(PREV, 15, 59), 1, 1, 1, prev_close, 1)]
        rows += [(sym, "1d", ts, c, c, c, c, 1) for sym, bars in S4["daily"].items() for ts, c in bars]
        _new_feed(rows)

    class _K:
        def __init__(s, k, bid, ask, delta):
            s.strike, s.bid, s.ask, s.delta, s.expiry, s.mark, s.symbol = float(k), bid, ask, delta, "x", (bid + ask) / 2, f"O{k}"

    chain = types.SimpleNamespace(calls=[_K(5000, 1.58, 1.62, .5), _K(5005, 1.0, 1.04, .4)],
                                  puts=[_K(5000, 1.5, 1.54, -.5)])
    real_park = SR.record_park

    def park_run(mode, o930, c1030, c1100, prev, hm="11:01"):
        st = St()
        P.ensure_tables(st)
        P.bind_store(st)
        park_feed(o930, c1030, c1100, prev)
        SR._PARK_CACHE.clear()
        SR._LOGGED.clear()
        spec = Park()
        spec._plan.planner.symbol = SYM
        cap.lines.clear()
        orig = SR.park_sma50
        if mode == "off":
            SR.record_park = lambda *a, **k: None
        elif mode == "raise":
            SR.park_sma50 = lambda **k: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            P.begin_tick(3.0)
            sig = spec.generate_signal(price_now=c1100, now_et=hm, chain=chain, day=DAY, symbol=SYM)
            P.close_tick(st, SYM)
            P.begin_tick(4.0)
            spec.generate_signal(price_now=c1100, now_et=hm, chain=chain, day=DAY, symbol=SYM)
            P.close_tick(st, SYM)
        finally:
            SR.record_park = real_park
            SR.park_sma50 = orig
        tick = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='PARK' ORDER BY rowid LIMIT 1").fetchone()
        sh = st.conn.execute("SELECT note FROM plan_check WHERE check_name='shadow_park_sma50' ORDER BY rowid").fetchall()
        key = None if sig is None else (sig.direction, sig.option_side, float(sig.strike), sig.entry_premium)
        return key, (tick["verdict"], tick["reason"]) if tick else None, [x[0] for x in sh], \
            [x for x in cap.lines if "PARK_SMA50" in x]
    # K1: first hour +0.30% on a gap up -> a CALL
    args = (5000.0, 5015.0, 5001.0, 4990.0)
    p_on, p_raise, p_off = park_run("on", *args), park_run("raise", *args), park_run("off", *args)
    # gate_g: an up first hour on a gap DOWN is refused
    g_on, g_off = park_run("on", 5000.0, 5015.0, 5001.0, 5010.0), park_run("off", 5000.0, 5015.0, 5001.0, 5010.0)
    check("N2 PARK: TAKE and a gate_g refusal each carry the shadow row; signal / verdict / reason identical on, raising, off",
          p_on[0] is not None and p_on[1][0] == "TAKE" and len(p_on[2]) == 2 and p_on[2][0].startswith(("keep", "would_skip"))
          and "index" in p_on[2][0] and p_on[0] == p_raise[0] == p_off[0] and p_on[1] == p_raise[1] == p_off[1]
          and p_raise[2] and p_raise[2][0].startswith("unknown") and not p_off[2]
          and g_on[0] is None and g_on[1][0] == "DECLINE" and len(g_on[2]) == 2 and g_on[1] == g_off[1],
          f"on={p_on} raise={p_raise[1:3]} off={p_off[1:3]} g={g_on[1:3]} {g_off[1]}")
    check("L1 PARK logs one line per day and direction: two ticks, two rows, one [shadow-rule] line",
          len(p_on[2]) == 2 and len(p_on[3]) == 1, f"{p_on[2]} {p_on[3]}")

    # ── S1 : the status tool ──────────────────────────────────────────────────────────────────────────────────────
    sd = os.path.join(_TD, "status_derived.db")
    c = sqlite3.connect(sd)
    c.execute("CREATE TABLE plan_tick (ts_epoch REAL, symbol TEXT, strategy TEXT, verdict TEXT)")
    c.execute("CREATE TABLE plan_check (ts_epoch REAL, symbol TEXT, strategy TEXT, check_name TEXT, note TEXT)")
    t0 = datetime.now(ET).replace(hour=9, minute=40, second=0, microsecond=0).timestamp()
    c.execute("INSERT INTO plan_tick VALUES (?,?,?,?)", (t0, "NVDA", "LiquidityHunt", "TAKE"))
    c.execute("INSERT INTO plan_check VALUES (?,?,?,?,?)", (t0, "NVDA", "LiquidityHunt", "shadow_hunt_or_em", "keep ratio=1"))
    c.execute("INSERT INTO plan_check VALUES (?,?,?,?,?)", (t0 + 3600, "NVDA", "PARK", "gap", ""))
    c.execute("INSERT INTO plan_check VALUES (?,?,?,?,?)", (t0 + 3600, "NVDA", "PARK", "shadow_park_sma50", "would_skip slope=-1"))
    c.commit()
    lg = os.path.join(_TD, "status.log")
    stamp = datetime.fromtimestamp(t0 + 60).strftime("%Y-%m-%d %H:%M:%S")
    open(lg, "w").write(f"{stamp} [INFO ] strategy.shadow_rules: [shadow-rule] HUNT_OR_EM NVDA A1 long keep x\n"
                        f"{stamp} [INFO ] strategy.shadow_rules: [shadow-rule] PARK_SMA50 NVDA long would_skip x\n")
    tool = os.path.join(ROOT, "tools", "shadow_rule_status.py")
    g = subprocess.run([sys.executable, tool, "--derived", sd, "--log", lg], capture_output=True, text=True)
    c.execute("DELETE FROM plan_check WHERE check_name='shadow_park_sma50'")
    c.commit()
    c.close()
    rr = subprocess.run([sys.executable, tool, "--derived", sd, "--log", lg], capture_output=True, text=True)
    check("S1 status tool: GREEN (rc 0) when every decision has its row and line; RED (rc 1) when a PARK row is missing",
          g.returncode == 0 and '"status": "GREEN"' in g.stdout and rr.returncode == 1
          and "PARK_SMA50  RED" in rr.stdout, f"{g.returncode} {g.stdout[-300:]} | {rr.returncode} {rr.stdout[-300:]}")

    # ── C1 : defaults live in code ────────────────────────────────────────────────────────────────────────────────
    src = open(os.path.join(ROOT, "strategy", "shadow_rules.py")).read()
    cfg = open(os.path.join(ROOT, "config.py")).read()
    check("C1 no env knob, no configure item: shadow_rules reads no os.environ; config.py has no SHADOW_ key",
          "os.environ" not in src and "getenv" not in src and "SHADOW_RULE" not in cfg and "OT_SHADOW" not in cfg)

    print(f"\n{len(RAN) - len(FAILED)}/{len(RAN)} passed")
    print("GREEN - check_shadow_rules" if not FAILED else "RED - check_shadow_rules: " + " ".join(FAILED))
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
