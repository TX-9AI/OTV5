#!/usr/bin/env python3
"""
tests/check_park.py  v5.1
v5.1  2026-10-30  OTV5 r58 (DECAY.1) — OT_DECAY_STOP=0 HERE: this checker pins a pre-decay exit in isolation. K10a2 (mark 1.70 / bid 1.50, then bid 1.20) now closes on the peak-decay stop (p 0.70 -> 0.22), which is the r57 rule working, not the PARK lock;
      the decay stop itself is gated by tests/check_decay_stop.py. No assertion changed.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
PARK - THE 11:00 FIRST-HOUR CONTINUATION (PARK.1): THE PLAN, THE STRATEGY, ITS SIZE, ITS EXITS, ITS OWN BUDGET.
v1.4  2026-10-19  OTV4TEST r302 (GATE.2). K13a ran attempt_new_entry() on the WALL CLOCK, so before 09:35 ET
      session_guard refused it ("opening range still forming") and PARK was never asked: RED at every 08:00 boot
      sweep (first seen 2026-10-19), GREEN at the 16:00-19:00 build sweeps that landed it. K13a now pins every
      loaded module's now_et/now_utc to DAY 11:01 ET (PARK's own window, inside RTH) for the one call.
v1.3  2026-10-18  OTV4TEST r298 (CAP.4). K11c: RiskManager._ensure_seeded on K11b's rows (PARK -2,000, Breakout -500) reads
      the cap's -500 and does not latch the halt; it read today_summary's -2,500 and halted (audit 10-18 A5).
v1.2  2026-10-18  OTV4TEST r292 (GATE.1). K13a DRIVES attempt_new_entry() with the PARK attempt intercepted: the
      normal-day call must ask PARK with the chain. K13 pinned only the capped branch, by text; a scratch copy with
      main.py's uncapped call deleted stayed GREEN 21/21 (audit 10-18 B1). K13a is RED on that mutant.
v1.1  2026-10-18  OTV4TEST r291 (PARK.2). K10b was a fixture that hand-set mfe_premium=1.65 - a column no open row ever
      carries - so it proved only the in-memory branch (audit 10-18 A3 / T1-10). Now K10b logs a PARK entry through the
      real TradeLogger, ticks update_current_premium (1.65 then 1.30), rehydrates the row with get_open_trades() and asks
      evaluate() at bid 1.19: park_lock. K10a2: mark 1.70 / bid 1.50 must NOT arm (the bid rule), then bid 1.20 holds.
      Both RED on cdcde8b.
v1.0  2026-10-18  OTV4TEST r288. The operator, 2026-10-17 18:21 ET: "Trade it, don't just log it. Paper is free. Call it
      PARK (named after my friend)"; on SPX: "Use our actual numbers, trade it"; 18:30 ET: "Make sure when you build it
      it's divided properly between the strategy and the plan". Terms: /var/tmp/sat_1017/cont11/PREREG_CONT11.md (C0)
      and PARK.X (/var/tmp/sat_1017/park, picks sha 85dca420).
  K1  the plan, 11:01, first hour +0.30%, gap up: READY, a CALL at the strike nearest the 11:00 close, entry = the ASK;
      the signal: strategy PARK, stop_premium 0 (no premium stop), underlying_stop 0
  K2  a quiet first hour (+0.15%): refused at first_hour_move, no signal
  K3  GATE-G: an up first hour on a gap DOWN is refused at gate_g; a put on a gap up is refused
  K4  the mirror: down first hour on a gap down -> a PUT at the nearest strike
  K5  the window: 11:00 and 11:03 DORMANT (no signal), 11:01 and 11:02 evaluated
  K6  a missing bar (no 11:00 1m bar yet) is STARVED - no signal; the prior close falls back to the caller only
      when the store has no prior session
  K7  the contract: ask < 0.50 refused; a one-sided quote (bid 0) refused
  K8  OT_PARK=log: generate_signal returns NOTHING to execute and writes one park_signal.jsonl row
  K9  the size is the box's own risk, flat: $1,050 at ask 1.62 -> 6; $2,500 at ask 9.00 -> 2 (RiskManager.size_for)
  K10 exits (the REAL ExitEngine.evaluate routes PARK to _evaluate_park):
      a. the lock: bid 1.19 x entry before arming HOLDS; after bid >= 1.60 x entry, bid 1.20 x entry EXITS park_lock
      b. a restart re-arms from the persisted mfe_premium
      c. the delta floor: |delta| 0.29 at 11:29 HOLDS, at 11:30 EXITS park_delta_floor; None / 0.0 HOLD
      d. NO premium stop and NO trail: mark at 10% of entry, delta 0.35, 12:00 -> HOLDS
      e. the close: 15:44 holds, 15:45 EXITS park_close_15:45_ET
      f. one park_exit.jsonl row per trade
  K11 its own budget: the admission rule is cap-exempt, one try, window 11:01-11:03; the cap's day P&L leaves PARK out
      (a -2,000 PARK close and a -500 Breakout close -> -500), the displays' realized P&L does not (-2,500)
  K12 config: OT_PARK unset -> trade; log / OFF honoured; junk -> log, refused named; ENTRY_WINDOWS["PARK"] = 11:01-11:03
  K13 main: PARK is declared long_debit, PIN_EXEMPT names it, and the capped branch asks _attempt_park before
      returning
  K14 THE SPLIT: strategy/park.py reads no store and no chain; the plan registers on construction
  K15 the pin gate's COUNTERFACTUAL on every PARK entry (the operator, 2026-10-17 20:06 ET: "I want a counterfactual
      on the pin gate recorded on the entries"): main._record_pin_counterfactual writes pin_gate.jsonl - would-refuse,
      passed and stood-down each as one row with the entry's strike / side / premium, acted false; an unreadable gate
      still writes a row; the PIN_EXEMPT branch of the entry path calls it
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone, timedelta
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_park_")
os.environ["OT_TRADES_DB"] = os.path.join(_TD, "t.db")
os.environ["OT_DERIVED_DB"] = os.path.join(_TD, "d.db")
FEED = os.path.join(_TD, "f.db")
os.environ["OT_FEED_DB"] = FEED
os.environ["OT_LOG_FILE"] = os.path.join(_TD, "bot.log")
os.environ["OT_SIGNAL_JOURNAL_DIR"] = os.path.join(_TD, "sj")
os.environ["OT_RESTING_DB"] = os.path.join(_TD, "r.db")
CF = os.path.join(_TD, "cf")
os.environ["OT_COUNTERFACTUAL_DIR"] = CF
# r58 (DECAY.1): this checker pins a pre-decay exit in isolation; the peak-decay stop is gated in tests/check_decay_stop.py
os.environ["OT_DECAY_STOP"] = "0"
os.environ.pop("OT_PARK", None)
ET = ZoneInfo("America/New_York")
FAILED, RAN = [], []
DAY, PREV = date(2026, 10, 16), date(2026, 10, 15)
SYM = os.environ.get("OT_INSTRUMENT", "QQQ")


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _ms(d, h, m):
    return int(datetime(d.year, d.month, d.day, h, m, tzinfo=ET).timestamp() * 1000)


def _feed(o930, c1030, c1100, prev_close, with_1100=True, with_prev=True):
    if os.path.exists(FEED):
        os.remove(FEED)
    c = sqlite3.connect(FEED)
    c.execute("CREATE TABLE candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, ts_epoch_ms INTEGER NOT NULL, "
              "open REAL, high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY (symbol, interval, ts_epoch_ms))")
    rows = [(SYM, "1m", _ms(DAY, 9, 30), o930, o930 + .1, o930 - .1, o930 + .05, 1),
            (SYM, "1m", _ms(DAY, 10, 30), c1030, c1030 + .1, c1030 - .1, c1030, 1)]
    if with_1100:
        rows.append((SYM, "1m", _ms(DAY, 11, 0), c1100, c1100 + .1, c1100 - .1, c1100, 1))
    if with_prev:
        rows += [(SYM, "1m", _ms(PREV, 15, 59), 1, 1, 1, prev_close, 1),
                 (SYM, "1m", _ms(PREV, 16, 5), 1, 1, 1, prev_close + 5, 1)]     # after-hours: never the close
    c.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", rows)
    c.commit()
    c.close()


class K:
    def __init__(self, strike, bid, ask, delta, side):
        self.strike, self.bid, self.ask, self.delta = strike, bid, ask, delta
        self.mark, self.expiry, self.streamer_symbol = (bid + ask) / 2, "2026-10-16", f".X{side}{strike:g}"
        self.option_type = side


class Chain:
    def __init__(self, ask=1.62, bid=1.58):
        self.calls = [K(s, bid, ask, 0.5, "C") for s in (701, 702, 703, 704)]
        self.puts = [K(s, bid, ask, -0.5, "P") for s in (696, 697, 698, 699)]
        self.expiry = "2026-10-16"


def main():
    print("check_park")
    try:
        import pandas  # noqa: F401
        import config
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2
    try:
        from strategy.park import Park
    except Exception as exc:                                    # noqa: BLE001
        check("K0 PARK exists (strategy/park.py, strategy/park_plan.py)", False, f"{type(exc).__name__}: {exc}")
        print("\nRED — 1 of 1 failed: K0")
        return 1
    P = Park()

    def ask(now="11:01", chain=None, prior=None, mode="trade"):
        config.PARK_MODE = mode
        return P.generate_signal(price_now=702.4, now_et=now, chain=chain or Chain(), prior_close=prior,
                                 day=DAY, symbol=SYM)

    def prep(now="11:01", chain=None, prior=None):
        return P.prepare(price_now=702.4, now_et=now, chain=chain or Chain(), prior_close=prior, day=DAY, symbol=SYM)

    _feed(700.0, 702.1, 702.4, 699.0)                         # +0.30%, gap +1.0
    s1 = ask()
    check("K1 READY: a CALL at 702 (nearest 702.4), entry = ask 1.62, strategy PARK, stop_premium 0, underlying_stop 0",
          s1 is not None and s1.strategy_name == "PARK" and s1.option_side == "call" and float(s1.strike) == 702
          and abs(s1.entry_premium - 1.62) < 1e-9 and s1.stop_premium() == 0 and float(s1.underlying_stop) == 0,
          f"{s1 and (s1.strategy_name, s1.option_side, s1.strike, s1.entry_premium, s1.stop_premium(), s1.underlying_stop)}")

    _feed(700.0, 701.05, 701.2, 699.0)                        # +0.15%
    p2 = prep()
    check("K2 a quiet first hour (+0.15%) is refused at first_hour_move; no signal",
          not p2.ready and "first_hour_move" in p2.unmet and ask() is None, f"{p2.unmet}")

    _feed(700.0, 702.1, 702.4, 701.0)                         # up first hour, gap DOWN
    p3a = prep()
    _feed(700.0, 697.9, 697.6, 699.0)                         # down first hour, gap UP
    p3b = prep()
    check("K3 GATE-G: up on a gap down refused; down on a gap up refused",
          not p3a.ready and p3a.unmet == ["gate_g"] and not p3b.ready and p3b.unmet == ["gate_g"],
          f"{p3a.unmet} {p3b.unmet}")

    _feed(700.0, 697.9, 697.6, 701.0)                         # down -0.30%, gap down
    s4 = ask()
    check("K4 the mirror: down on a gap down -> a PUT at 698 (nearest 697.6)",
          s4 is not None and s4.option_side == "put" and float(s4.strike) == 698, f"{s4 and (s4.option_side, s4.strike)}")

    _feed(700.0, 702.1, 702.4, 699.0)
    w = {t: ask(now=t) is not None for t in ("11:00", "11:01", "11:02", "11:03")}
    check("K5 the window: 11:00 and 11:03 dormant, 11:01 and 11:02 fire",
          w == {"11:00": False, "11:01": True, "11:02": True, "11:03": False}, f"{w}")

    _feed(700.0, 702.1, 702.4, 699.0, with_1100=False)
    p6a = prep()
    _feed(700.0, 702.1, 702.4, 699.0, with_prev=False)
    p6b, p6c = prep(prior=None), prep(prior=699.0)
    check("K6 no 11:00 bar -> starved; no prior session -> starved, unless the caller gives one (then ready)",
          not p6a.ready and not p6b.ready and p6c.ready, f"{p6a.ready} {p6b.ready} {p6c.ready}")

    _feed(700.0, 702.1, 702.4, 699.0)
    p7a, p7b = prep(chain=Chain(ask=0.45, bid=0.40)), prep(chain=Chain(ask=1.62, bid=0.0))
    check("K7 the contract: ask 0.45 refused; a one-sided quote refused",
          not p7a.ready and p7a.unmet == ["contract"] and not p7b.ready and p7b.unmet == ["contract"],
          f"{p7a.unmet} {p7b.unmet}")

    s8 = ask(mode="log")
    f8 = os.path.join(CF, "park_signal.jsonl")
    r8 = [json.loads(x) for x in open(f8)] if os.path.exists(f8) else []
    check("K8 OT_PARK=log: nothing to execute, one park_signal.jsonl row (call 702 @ 1.62)",
          s8 is None and len(r8) == 1 and r8[0]["side"] == "call" and r8[0]["strike"] == 702 and r8[0]["ask"] == 1.62,
          f"{s8} {r8}")
    config.PARK_MODE = "trade"

    from risk.risk_manager import RiskManager
    z1 = RiskManager(risk_per_trade=1050.0, paper_trading=True).size_for("long_debit", premium=1.62, grade="UNGRADED")
    z2 = RiskManager(risk_per_trade=2500.0, paper_trading=True).size_for("long_debit", premium=9.00, grade="UNGRADED")
    check("K9 sized flat on the box's risk: $1,050 @ 1.62 -> 6; $2,500 @ 9.00 -> 2",
          z1.allowed and z1.contracts == 6 and z2.allowed and z2.contracts == 2, f"{z1.contracts} {z2.contracts}")

    import execution.exit_engine as XE
    XE.is_hard_close_time = lambda: False
    _real_dt = XE.datetime

    def at(h, m):
        class _D(_real_dt):
            @classmethod
            def now(cls, tz=None):
                return _real_dt(2026, 10, 16, h, m, tzinfo=ET)
        XE.datetime = _D
    eng = XE.ExitEngine(paper_trading=True)

    def rec(tid, **kw):
        r = {"trade_id": tid, "strategy": "PARK", "symbol": SYM, "direction": "long", "option_side": "call",
             "entry_premium": 1.0, "contracts": 6, "stop_premium": 0.0, "current_delta": 0.5,
             "entry_time": "2026-10-16T15:01:10+00:00", "option_symbol": "X", "is_butterfly": 0}
        r.update(kw)
        return r

    def ev(r, mark, h, m, bid=None):
        at(h, m)
        if bid is not None:
            r["_exit_bid"] = bid
        return eng.evaluate(r, mark)

    ra = rec("k10a")
    d_pre = ev(ra, 1.21, 12, 0, bid=1.19)
    d_arm = ev(ra, 1.62, 12, 5, bid=1.60)
    d_out = ev(ra, 1.22, 12, 10, bid=1.20)
    check("K10a the lock: 1.19 before arming holds; armed at bid 1.60; bid 1.20 exits park_lock",
          not d_pre.should_exit and not d_arm.should_exit and d_out.should_exit
          and d_out.exit_reason.startswith("park_lock"), f"{d_pre.exit_reason!r} {d_arm.exit_reason!r} {d_out.exit_reason!r}")

    # r291 (PARK.2): the bid arms, not the mark. A tick whose MARK prints +70% while the BID is +50% must not arm.
    ra2 = rec("k10a2")
    d_m1 = ev(ra2, 1.70, 12, 20, bid=1.50)
    d_m2 = ev(ra2, 1.22, 12, 25, bid=1.20)
    check("K10a2 mark 1.70 / bid 1.50 does NOT arm (bid rule); the next bid 1.20 holds, no park_lock",
          not d_m1.should_exit and not d_m2.should_exit, f"{d_m1.exit_reason!r} {d_m2.exit_reason!r}")

    # r291 (PARK.2): the restart re-arm, through the real store - log_entry, per-tick update_current_premium, then
    # get_open_trades() rehydrates the row (mfe_premium is NULL on an open row; max_premium_seen carries the best mark).
    from database.trade_logger import get_trade_logger as _gtl, make_record as _mr
    _TL = _gtl()
    _TL.log_entry(_mr(trade_id="k10b-db", symbol=SYM, strategy="PARK", direction="long", option_side="call",
                      strike=600.0, expiry=str(DAY), contracts=6, entry_premium=1.0, stop_premium=0.0,
                      option_symbol="X", paper_trade=1, is_butterfly=0))
    _TL.update_current_premium("k10b-db", 1.65)
    _TL.update_current_premium("k10b-db", 1.30)
    _rows = [r for r in _TL.get_open_trades() if r.get("trade_id") == "k10b-db"]
    rb = _rows[0] if _rows else rec("k10b-missing")
    rb["current_delta"] = 0.5
    _mfe0, _best0 = rb.get("mfe_premium"), rb.get("max_premium_seen")     # as rehydrated, before evaluate() touches it
    d_b = ev(rb, 1.21, 13, 0, bid=1.19)
    check("K10b a restart re-arms from the PERSISTED best mark: get_open_trades() row (mfe_premium NULL, "
          "max_premium_seen 1.65) at bid 1.19 exits park_lock",
          bool(_rows) and _mfe0 is None and float(_best0 or 0) == 1.65
          and d_b.should_exit and d_b.exit_reason.startswith("park_lock"),
          f"rows={len(_rows)} mfe={_mfe0!r} best={_best0!r} {d_b.exit_reason!r}")
    with sqlite3.connect(os.environ["OT_TRADES_DB"]) as _c:
        _c.execute("DELETE FROM trades WHERE trade_id='k10b-db'")

    rc = rec("k10c", current_delta=0.29)
    d_c1 = ev(rc, 0.6, 11, 29, bid=0.58)
    d_c2 = ev(rc, 0.6, 11, 30, bid=0.58)
    d_c3 = ev(rec("k10c-none", current_delta=None), 0.6, 12, 0, bid=0.58)
    d_c4 = ev(rec("k10c-zero", current_delta=0.0), 0.6, 12, 0, bid=0.58)
    d_c5 = ev(rec("k10c-put", direction="short", option_side="put", current_delta=-0.25), 0.6, 12, 0, bid=0.58)
    check("K10c the delta floor: 0.29 at 11:29 holds, 11:30 exits; None / 0.0 hold; a put at -0.25 exits",
          not d_c1.should_exit and d_c2.should_exit and d_c2.exit_reason.startswith("park_delta_floor")
          and not d_c3.should_exit and not d_c4.should_exit and d_c5.should_exit,
          f"{d_c1.exit_reason!r} {d_c2.exit_reason!r} {d_c3.exit_reason!r} {d_c4.exit_reason!r} {d_c5.exit_reason!r}")

    d_d = ev(rec("k10d", current_delta=0.35), 0.10, 12, 0, bid=0.09)
    check("K10d no premium stop, no trail: mark at 10% of entry, delta 0.35, 12:00 HOLDS",
          not d_d.should_exit, f"{d_d.exit_reason!r}")

    re_ = rec("k10e", current_delta=0.45)
    d_e1, d_e2 = ev(re_, 1.3, 15, 44, bid=1.28), ev(re_, 1.3, 15, 45, bid=1.28)
    check("K10e the close: 15:44 holds, 15:45 exits park_close_15:45_ET",
          not d_e1.should_exit and d_e2.should_exit and d_e2.exit_reason == "park_close_15:45_ET",
          f"{d_e1.exit_reason!r} {d_e2.exit_reason!r}")
    ev(re_, 1.3, 15, 46, bid=1.28)
    fx = os.path.join(CF, "park_exit.jsonl")
    rx = [json.loads(x) for x in open(fx)] if os.path.exists(fx) else []
    check("K10f one park_exit.jsonl row per trade (k10e evaluated twice past the close -> one row)",
          len([r for r in rx if r["trade_id"] == "k10e"]) == 1 and len({r["trade_id"] for r in rx}) == len(rx),
          f"{[r['trade_id'] for r in rx]}")
    XE.datetime = _real_dt

    from execution import position_manager as PM
    rl = PM.rules().get("PARK")
    check("K11a admission: PARK is cap-exempt, one try, one open, window 11:01-11:03",
          rl is not None and rl.cap_exempt and rl.max_tries_per_session == 1 and rl.max_open_of_type == 1
          and tuple(map(tuple, rl.window)) == ((11, 1), (11, 3)), f"{rl}")
    from database.trade_logger import get_trade_logger
    TL = get_trade_logger()
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(os.environ["OT_TRADES_DB"]) as c:
        c.execute("INSERT INTO trades (trade_id, strategy, status, pnl_usd, entry_time, paper_trade) VALUES "
                  "('p1','PARK','closed',-2000,?,1)", (now_iso,))
        c.execute("INSERT INTO trades (trade_id, strategy, status, pnl_usd, entry_time, paper_trade) VALUES "
                  "('b1','Breakout','closed',-500,?,1)", (now_iso,))
    cap = RiskManager(risk_per_trade=1050.0, paper_trading=True).day_realized_pnl()
    disp = TL.realized_pnl_today()
    check("K11b its own budget: the cap's day P&L is -500 (PARK left out), the displays' is -2,500",
          abs(cap + 500) < 1e-6 and abs(disp + 2500) < 1e-6, f"cap={cap} display={disp}")
    # r298 (CAP.4): the RESTART SEED is the cap's number too. A fresh RiskManager booting on these rows must read
    # -500 and NOT halted (limit 1,050); it read -2,500 and halted, then logged a RE-ARMED event nothing had hit.
    _rm2 = RiskManager(risk_per_trade=1050.0, paper_trading=True)
    _rm2._ensure_seeded()
    check("K11c the restart seed reads the cap's -500 (PARK left out) and does not latch the halt",
          _rm2._seeded is True and abs(_rm2._session_pnl_usd + 500) < 1e-6 and _rm2._session_halted is False,
          f"seeded={_rm2._seeded} pnl={_rm2._session_pnl_usd} halted={_rm2._session_halted} limit={_rm2._daily_loss_limit}")

    def probe(env):
        e = {k: v for k, v in os.environ.items() if k != "OT_PARK"}
        e.update(env)
        code = ("import config,json;print(json.dumps([config.PARK_MODE, config.PARK_ENV_REFUSED, "
                "config.ENTRY_WINDOWS['PARK']]))")
        p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=e, capture_output=True, text=True, timeout=120)
        return json.loads(p.stdout.strip().splitlines()[-1]) if p.returncode == 0 and p.stdout.strip() else p.stderr[-300:]
    m = [probe({}), probe({"OT_PARK": "log"}), probe({"OT_PARK": "OFF"}), probe({"OT_PARK": "yes"})]
    check("K12 OT_PARK: unset -> trade; log / OFF honoured; 'yes' -> log, refused named; window 11:01-11:03",
          m[0] == ["trade", "", [[11, 1], [11, 3]]] and m[1][0] == "log" and m[2][0] == "off"
          and m[3][:2] == ["log", "yes"], f"{m}")

    src = open(os.path.join(ROOT, "main.py")).read()
    capped = src[src.index("    if _cap_hit:\n        if not _adm_ok:"):]
    capped = capped[:capped.index("        return\n\n")]
    check("K13 main: PARK declared long_debit, PIN_EXEMPT names it, the capped branch asks _attempt_park",
          '"PARK":                 "long_debit"' in src and 'PIN_EXEMPT = ("PARK",)' in src
          and "_attempt_park(ctx, ms, state)" in capped and "def _attempt_park(" in src, capped[-300:])

    # r292 (GATE.1) — K13a DRIVES THE NORMAL-DAY DISPATCH. K13 pinned the capped branch by text and nothing pinned
    # main.py's uncapped `_attempt_park(ctx, ms, state, chain=chain)`: deleting it left this checker green (audit
    # 10-18 B1). Here attempt_new_entry() itself runs, with the PARK attempt and the butterflies intercepted, on a ctx
    # that already carries a chain (so no fetch) - every other strategy runs its real path on the empty scratch
    # stores and declines. The recorder must see PARK asked WITH the chain (the capped branch passes none).
    import main as _MN0
    _calls = []
    _orig_park, _orig_fly = _MN0._attempt_park, _MN0._attempt_butterfly
    _MN0._attempt_park = lambda ctx, ms, state, chain=None: _calls.append(("park", chain is not None))
    _MN0._attempt_butterfly = lambda *a, **k: _calls.append(("fly",))

    class _MS:
        adx, trend_direction, structure_sequence = 20.0, "NEUTRAL", ""

    class _Chain:
        calls, puts, spot = [], [], 702.4
    _st = _MN0.BotState()
    _st.paper_trading = True
    with sqlite3.connect(os.environ["OT_TRADES_DB"]) as _c:      # K11b's closed rows would trip the cap -> capped branch
        _c.execute("DELETE FROM trades WHERE trade_id IN ('p1', 'b1')")
    _err = ""
    # r302 (GATE.2) - THE CLOCK IS PINNED, not read off the wall: before 09:35 ET session_guard refuses every
    # entry, so an unpinned K13a was red at each 08:00 boot sweep. DAY 11:01 ET is PARK's window, inside RTH.
    # Every loaded module that holds the real now_et / now_utc (by identity) gets the pinned one; restored after.
    import utils.time_utils as _TU
    _pin = datetime(DAY.year, DAY.month, DAY.day, 11, 1, 30, tzinfo=ET)
    _real = {"now_et": _TU.now_et, "now_utc": _TU.now_utc}
    _fake = {"now_et": lambda: _pin, "now_utc": lambda: _pin.astimezone(timezone.utc)}
    _swapped = [(_m, _n) for _m in list(sys.modules.values()) for _n in _real
                if _m is not None and getattr(_m, _n, None) is _real[_n]]
    for _m, _n in _swapped:
        setattr(_m, _n, _fake[_n])
    try:
        _MN0.attempt_new_entry({"price": 702.4, "chain": _Chain(), "macro": {}, "symbol": SYM}, _MS(), _st)
    except Exception as _e:                                     # noqa: BLE001
        _err = f"{type(_e).__name__}: {_e}"
    finally:
        _MN0._attempt_park, _MN0._attempt_butterfly = _orig_park, _orig_fly
        for _m, _n in _swapped:
            setattr(_m, _n, _real[_n])
    check("K13a DRIVEN: attempt_new_entry() asks _attempt_park WITH the chain on the normal-day path",
          ("park", True) in _calls and not _err, f"calls={_calls} err={_err}")

    spec = open(os.path.join(ROOT, "strategy", "park.py")).read()
    from strategy import plan as PL
    check("K14 THE SPLIT: park.py reads no store and no chain; ParkPlan is in the plan registry",
          "sqlite3" not in spec and "chain.calls" not in spec and "feed_db_path" not in spec
          and "PARK" in getattr(PL, "REGISTRY", {}), f"registry={list(getattr(PL, 'REGISTRY', {}))[:12]}")

    import main as MN
    class _Sig:
        strategy_name, direction, option_side, strike, entry_premium = "PARK", "long", "call", 702.0, 1.62
        contract = K(702, 1.58, 1.62, 0.5, "C")
    for v in ((True, 0.12, "PINNING", 700.0, ""), (False, 0.55, "PINNING", 700.0, ""), (False, None, None, None, "no gex")):
        MN._record_pin_counterfactual(_Sig(), {"price": 702.4}, v)
    MN._record_pin_counterfactual(_Sig(), {"price": 702.4}, None, error="RuntimeError: boom")
    fp = os.path.join(CF, "pin_gate.jsonl")
    rp = [json.loads(x) for x in open(fp)] if os.path.exists(fp) else []
    body = open(os.path.join(ROOT, "main.py")).read()
    br = body[body.index("signal.strategy_name in PIN_EXEMPT:"):]
    br = br[:br.index("elif PIN_PROXIMITY_ACTIVE")]
    check("K15 pin-gate counterfactual: 4 rows (refuse / pass / stood down / unreadable), acted false, the entry's "
          "strike / side / premium; the PIN_EXEMPT branch calls it",
          len(rp) == 4 and [r["would_refuse"] for r in rp] == [True, False, None, None]
          and [r["stood_down"] for r in rp] == [False, False, True, True]
          and all(r["acted"] is False and r["strategy"] == "PARK" and r["strike"] == 702.0
                  and r["option_side"] == "call" and r["entry_premium"] == 1.62 for r in rp)
          and "_record_pin_counterfactual(signal, ctx, pin_proximity_verdict(ctx))" in br, f"{rp} | {br[:200]}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
