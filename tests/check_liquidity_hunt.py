#!/usr/bin/env python3
"""
tests/check_liquidity_hunt.py  v5.1
v5.1  2026-10-26  OTV5 r38 (HYG.18) — scratch no longer names dir="/var/tmp": mkdtemp honours TMPDIR, which boot_sweep and land.sh point
      at a per-run dir they remove (HYG.14), so a sweep leaves nothing behind (237 dirs had piled up on SOFI). No check changed.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.6  CD.2 (2026-10-24) - the fixture marks the level book SYNCED (store.mark_level_sync) after seeding the ledger:
      LevelEngine.board() now fails closed as not_synced until a book sync against a recent closed 1m bar has been
      recorded (derived/levels v6.10). Every expectation is unchanged.
v1.5  2026-10-19  OTV4TEST r304 (HUNT.12) - H13a-d: A REFUSED ENTRY DOES NOT SPEND THE BREAK, through main's REAL
      _attempt_hunt door with execution stubbed: a fire whose execution opens nothing (QQQ 10-19 10:13: COMMIT.2 blocked
      the A2) leaves the break open and the next tick fires again (H13a); a fire that left a trades.db row stays spent
      (H13b); an unreadable book stays spent (H13c, fail closed). H13a RED on f07f7a4 (nothing released the break). This
      checker now imports main, so every store main opens is pointed at its own scratch dir first.
v1.4  2026-10-18  OTV4TEST r297 (HUNT.11) - H12a-d: one per break SURVIVES A RESTART. A fresh plan (FINISHED empty) with
      today's Hunt row for the break in the scratch trades.db does not fire (H12a); another boundary's row does not
      block (H12b); an unreadable book holds, named (H12c); no row -> fires as before (H12d). OT_TRADES_DB joins this
      checker's own scratch env (H12 logs rows through the real TradeLogger). H12a and H12c RED on 64c483e.
v1.3  2026-10-15  HUNT.9 (RECORD-ONLY) - H11a-i: after a boundary's A2, a far-side re-close then a close back inside
      writes ONE hunt_rearm row and fires NOTHING (H11c); staying inside records nothing (H11a, H11e); A1 is unchanged
      (H11d, and H11i: an A1 on a finished key is never recorded); off records nothing (H11f); log and off fire the
      same signals (H11g, no order from the re-arm); there is no trade value (H11h). The operator, 2026-10-15 10:16 ET: "Concur on all" (to "record-only").
v1.2  2026-10-14  OTV4TEST r285 (HUNT.8) - OT_COUNTERFACTUAL_DIR is set to a scratch directory before any project
      import: this file drives the exit engine with LiquidityHunt records, and r285's _hunt_cf would otherwise
      write fixture rows into the repo's data/counterfactual/hunt_stop.jsonl - the LIVE log when the boot sweep
      runs in the live tree. No check changed.
v1.1  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.0  2026-09-10  OTV4TEST r12 — THE LIQUIDITY HUNT AND THE HANDOFF GRANT, ON
      HYPOTHETICALS (PLAN_SPEC §37). Real plan, real exit engine, real slot rule,
      a DerivedStore fixture for the levels.

  H1   bias = the nearer live level measured from the RANGE EDGE (above vs below)
  H2   A1: a close out on the bias side -> fires, target = the level, runway known
  H3   a far-side break -> "broke AWAY from the liquidity", not traded, recorded
  H4   A2: the far-side break CLOSES BACK INSIDE -> fires from the far boundary
  H5   one hunt per break key
  H6   exit: the target WICKED with the close short of it -> off, GRANT written
  H7   the target ACCEPTED (close beyond) -> no wick exit; hold (over-delivered)
  H8   thesis dead: a close back through the ENTRY boundary (A2: the far one), not the 50
  H9   slot: an open hunt is NOT blocking; an open ORB does not block a hunt entry
  H10  the grant: live -> consumed on fire / expired after TTL, both recorded
  H11  HUNT.9: a far-side re-close then back inside RECORDS the re-armed A2, never fires it; A1 unchanged

Born red at r11: every H (no module).
Run:  python3 tests/check_liquidity_hunt.py
"""
import os
import sqlite3
import sys
import subprocess
import tempfile
os.environ.setdefault("OT_COUNTERFACTUAL_DIR", tempfile.mkdtemp(prefix="cf_"))   # r285: never the live log
_H12_DIR = tempfile.mkdtemp(prefix="chk_hunt_db_")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_H12_DIR, "trades.db"))   # r297: H12 logs Hunt rows through the real TradeLogger
for _k, _v in (("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"), ("OT_LOG_FILE", "bot.log"),        # r304: H13 imports main
               ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_RESTING_DB", "r.db"), ("OT_RESTING_STOP_STATE", "rs.json"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ.setdefault(_k, os.path.join(_H12_DIR, _v))
import time
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


def _frame(rows, start="09:40"):
    import pandas as pd
    return pd.DataFrame([{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in rows],
                        index=pd.date_range(f"2026-09-10 {start}", periods=len(rows), freq="1min"))


class _G:
    def __init__(s, k, prem, delta, gamma):
        s.strike, s.mark, s.ask, s.bid = float(k), prem, prem + 0.02, prem - 0.02
        s.delta, s.gamma, s.theta, s.expiry, s.open_interest, s.symbol = delta, gamma, -0.04, "x", 100, f"O{k}"


def main():
    from strategy import plan as P
    class St:
        def __init__(s): s.conn = sqlite3.connect(":memory:"); s.conn.row_factory = sqlite3.Row
        def commit(s): s.conn.commit()
    st = St(); P.ensure_tables(st); P.bind_store(st)
    from data.derived_store import DerivedStore
    import strategy.liquidity_hunt as LH
    from execution import handoff as H
    ds = DerivedStore(path=os.path.join(tempfile.mkdtemp(), "derived.db"))
    ds.mark_level_sync("TST", time.time())        # CD.2: the book is synced "now"
    LH._symbol_of = lambda: "TST"
    now = time.time()
    # range 100.00-101.00; PDH 102.50 (1.50 above the edge), london low 97.00 (3.00 below) -> bias LONG
    ds.upsert_level(("TST:prev_day:102.50", "TST", 102.5, "resistance", "prev_day", "day", now - 3600, 0, None, 0, None, None, 1))
    ds.upsert_level(("TST:london:97.00", "TST", 97.0, "support", "london", "session", now - 3600, 0, None, 0, None, None, 1))
    orb = types.SimpleNamespace(orb_high=101.0, orb_low=100.0)
    calls = [_G(101, 0.95, 0.46, 0.05), _G(102, 0.48, 0.30, 0.058), _G(103, 0.20, 0.17, 0.04), _G(104, 0.10, 0.08, 0.02)]
    chain = types.SimpleNamespace(calls=calls, puts=[])
    hunt = LH.LiquidityHunt(); hunt._store = ds; hunt.planner.symbol = "TST"
    LH.FINISHED.clear(); H.reset()

    def row():
        r = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='LiquidityHunt' ORDER BY rowid DESC LIMIT 1").fetchone()
        return (r["verdict"], r["reason"] or "") if r else ("", "")

    def tick(n, px, frame, hhmm="09:41"):
        P.begin_tick(n)
        sig = hunt.generate_signal(orb=orb, price_now=px, now_et=hhmm, atr_pct=0.14, chain=chain, df_1m=frame, atm_iv=0.25)
        P.close_tick(st, "TST")
        return sig, row()

    # H1 + inside the range: waiting
    sig, r = tick(1.0, 100.5, _frame([(100.4, 100.7, 100.3, 100.5), (100.5, 100.6, 100.4, 100.55)], "09:40"))
    check("H1 bias LONG: PDH 1.50 above the edge beats the london low 3.00 below; inside -> waiting on A1 or A2",
          sig is None and r[0] == "HOLD" and "bias LONG" in r[1] and "waiting on: A1" in r[1], r[1][:150])
    # H2 A1
    sig, r = tick(2.0, 101.3, _frame([(100.9, 101.4, 100.8, 101.3), (101.3, 101.5, 101.2, 101.4)], "09:42"))
    check("H2 A1: a close out ABOVE -> fires long, target PDH 102.50, runway known, entry boundary = the range high",
          sig is not None and sig.direction == "long" and sig.underlying_target == 102.5 and sig.underlying_stop == 101.0
          and sig.hunt_entry == "A1" and r[0] == "TAKE", f"sig={sig and (sig.direction, sig.underlying_target, sig.hunt_entry)} {r[0]}")
    # H5 one per break
    sig, r = tick(2.5, 101.4, _frame([(101.3, 101.5, 101.2, 101.4), (101.4, 101.6, 101.3, 101.5)], "09:43"))
    check("H5 the same break does not hunt twice", sig is None and "one per break" in r[1], r[1][-60:])
    # H3 far-side break (fresh hunt object, same store)
    hunt2 = LH.LiquidityHunt(); hunt2._store = ds; hunt2.planner.symbol = "TST"; LH.FINISHED.clear()
    def tick2(n, px, frame, hhmm="09:45"):
        P.begin_tick(n)
        sig = hunt2.generate_signal(orb=orb, price_now=px, now_et=hhmm, atr_pct=0.14, chain=chain, df_1m=frame, atm_iv=0.25)
        P.close_tick(st, "TST")
        return sig, row()
    sig, r = tick2(3.0, 99.7, _frame([(100.1, 100.2, 99.6, 99.7), (99.7, 99.9, 99.6, 99.8)], "09:45"))
    check("H3 a close out BELOW (away from the liquidity) -> not traded, named as a fake-out candidate",
          sig is None and r[0] == "HOLD" and "AWAY" in r[1], r[1][-120:])
    # H4 A2: the fake fails — a close back inside -> fire from the far boundary (100.00)
    sig, r = tick2(4.0, 100.2, _frame([(99.8, 100.3, 99.7, 100.2), (100.2, 100.4, 100.1, 100.3)], "09:47"))
    check("H4 A2: the fake fails (close back inside) -> fires long from the FAR boundary 100.00, target 102.50",
          sig is not None and sig.hunt_entry == "A2" and sig.underlying_stop == 100.0 and sig.underlying_target == 102.5
          and abs(sig.run_at_entry - 2.3) < 1e-6, f"sig={sig and (sig.hunt_entry, sig.underlying_stop, sig.run_at_entry)} {r[1][-80:]}")
    # H11 (HUNT.9) - A RETURN TO THE RANGE RE-ARMS A2: RECORDED, NEVER TRADED. The operator, 2026-10-14 10:28 ET:
    # "It should be permitted if it goes back into the range"; 2026-10-15 10:16 ET: "Concur on all" (to
    # "BRK.12 / HUNT.9: record-only"). Rows go to the scratch OT_COUNTERFACTUAL_DIR set above.
    import json as _json
    import config as _cfg
    _cf = os.path.join(os.environ["OT_COUNTERFACTUAL_DIR"], "hunt_rearm.jsonl")
    def _rows():
        try:
            with open(_cf) as fh:
                return [_json.loads(x) for x in fh if x.strip()]
        except FileNotFoundError:
            return []
    sig, r = tick2(4.5, 100.3, _frame([(100.2, 100.4, 100.1, 100.3), (100.3, 100.4, 100.2, 100.3)], "09:48"))
    check("H11a staying inside after an A2 does not fire again and records nothing",
          sig is None and r[0] == "HOLD" and not _rows(), f"sig={sig and sig.hunt_entry} rows={len(_rows())} {r[1][-70:]}")
    sig, r = tick2(4.6, 99.7, _frame([(100.1, 100.2, 99.6, 99.7), (99.7, 99.8, 99.6, 99.7)], "09:49"))
    check("H11b the far-side break re-asserts (a close back out below) -> not traded, AWAY, nothing recorded yet",
          sig is None and r[0] == "HOLD" and "AWAY" in r[1] and not _rows(), r[1][-90:])
    sig, r = tick2(4.7, 100.2, _frame([(99.8, 100.3, 99.7, 100.2), (100.2, 100.3, 100.1, 100.2)], "09:50"))
    rr = _rows()
    check("H11c ...and it goes BACK INTO THE RANGE -> NO ORDER (no signal), ONE hunt_rearm row: A2 long from 100.00",
          sig is None and r[0] == "HOLD" and "RECORDED ONLY" in r[1] and len(rr) == 1 and rr[0]["entry"] == "A2"
          and rr[0]["direction"] == "long" and rr[0]["boundary"] == 100.0 and rr[0]["mode"] == "log"
          and abs(rr[0]["target"] - 102.5) < 1e-9,
          f"sig={sig and sig.hunt_entry} rows={rr} {r[1][-80:]}")
    sig, r = tick2(4.8, 100.25, _frame([(100.2, 100.3, 100.1, 100.25), (100.25, 100.3, 100.2, 100.25)], "09:51"))
    check("H11e the next bar inside, with no new far-side close, records no second row and fires nothing",
          sig is None and len(_rows()) == 1, f"sig={sig and sig.hunt_entry} rows={len(_rows())}")
    # H11i - with BOTH breaks already hunted, a far-side re-close then a close straight out ABOVE is an A1 on a
    # finished key: refused "one per break" and NOT recorded (the re-arm is A2's, never A1's).
    sig_a1, _ = tick2(4.9, 101.3, _frame([(100.9, 101.4, 100.8, 101.3), (101.3, 101.4, 101.2, 101.3)], "09:56"))
    tick2(4.91, 99.7, _frame([(100.1, 100.2, 99.6, 99.7), (99.7, 99.8, 99.6, 99.7)], "09:57"))
    sig, r = tick2(4.92, 101.3, _frame([(100.9, 101.4, 100.8, 101.3), (101.3, 101.4, 101.2, 101.3)], "09:58"))
    check("H11i a far-side re-close then a close straight out above (A1, already hunted) records NO row",
          sig_a1 is not None and sig_a1.hunt_entry == "A1" and sig is None and "one per break" in r[1]
          and len(_rows()) == 1, f"a1={sig_a1 and sig_a1.hunt_entry} sig={sig and sig.hunt_entry} rows={len(_rows())} {r[1][-50:]}")
    hunt3 = LH.LiquidityHunt(); hunt3._store = ds; hunt3.planner.symbol = "TST"; LH.FINISHED.clear()
    def tick3(n, px, frame, hhmm="09:55"):
        P.begin_tick(n)
        sig = hunt3.generate_signal(orb=orb, price_now=px, now_et=hhmm, atr_pct=0.14, chain=chain, df_1m=frame, atm_iv=0.25)
        P.close_tick(st, "TST")
        return sig, row()
    sig1, _ = tick3(5.0, 101.3, _frame([(100.9, 101.4, 100.8, 101.3), (101.3, 101.4, 101.2, 101.3)], "09:52"))
    tick3(5.1, 99.7, _frame([(100.1, 100.2, 99.6, 99.7), (99.7, 99.8, 99.6, 99.7)], "09:53"))
    tick3(5.2, 100.2, _frame([(99.8, 100.3, 99.7, 100.2), (100.2, 100.3, 100.1, 100.2)], "09:54"))
    sig, r = tick3(5.3, 101.3, _frame([(100.9, 101.4, 100.8, 101.3), (101.3, 101.4, 101.2, 101.3)], "09:55"))
    check("H11d A1 is UNCHANGED: a far-side close never re-arms the bias-side break, and records no A1 row",
          sig1 is not None and sig1.hunt_entry == "A1" and sig is None and "one per break" in r[1]
          and all(x["entry"] == "A2" for x in _rows()),
          f"first={sig1 and sig1.hunt_entry} then={sig and sig.hunt_entry} {r[1][-60:]}")
    # OFF, and NO DECISION CHANGES: the same A2 -> re-assert -> back-inside sequence under log and under off
    # yields the same signals (none after the first A2); off writes nothing.
    def _seq(mode):
        _saved = getattr(_cfg, "HUNT_REARM_MODE", "log"); _cfg.HUNT_REARM_MODE = mode
        try:
            h = LH.LiquidityHunt(); h._store = ds; h.planner.symbol = "TST"; LH.FINISHED.clear()
            out = []
            for n, px, bars, hhmm in ((6.0, 99.7, [(100.1, 100.2, 99.6, 99.7), (99.7, 99.9, 99.6, 99.8)], "10:00"),
                                      (6.1, 100.2, [(99.8, 100.3, 99.7, 100.2), (100.2, 100.4, 100.1, 100.3)], "10:01"),
                                      (6.2, 99.7, [(100.1, 100.2, 99.6, 99.7), (99.7, 99.8, 99.6, 99.7)], "10:02"),
                                      (6.3, 100.2, [(99.8, 100.3, 99.7, 100.2), (100.2, 100.3, 100.1, 100.2)], "10:03")):
                P.begin_tick(n)
                sg = h.generate_signal(orb=orb, price_now=px, now_et=hhmm, atr_pct=0.14, chain=chain,
                                       df_1m=_frame(bars, hhmm), atm_iv=0.25)
                P.close_tick(st, "TST")
                out.append(sg.hunt_entry if sg is not None else None)
            return out
        finally:
            _cfg.HUNT_REARM_MODE = _saved
    n0 = len(_rows()); s_off = _seq("off"); n_off = len(_rows()); s_log = _seq("log"); n_log = len(_rows())
    check("H11f OT_HUNT_REARM=off: nothing recorded", n_off == n0, f"rows {n0}->{n_off}")
    check("H11g RECORD-ONLY: log and off fire exactly the same signals (one A2, then none), log adds one row",
          s_off == s_log == [None, "A2", None, None] and n_log == n_off + 1,
          f"off={s_off} log={s_log} rows {n_off}->{n_log}")
    _o = subprocess.run([sys.executable, "-c", "import config;print(config.HUNT_REARM_MODE, config.HUNT_REARM_ENV_REFUSED)"],
                        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        env=dict(os.environ, OT_HUNT_REARM="trade"), capture_output=True, text=True, timeout=120)
    check("H11h there is no trade value: OT_HUNT_REARM=trade reads as log and is named",
          _o.stdout.split()[-2:] == ["log", "trade"], (_o.stdout + _o.stderr)[-160:])

    # exits
    import datetime as _dt
    from zoneinfo import ZoneInfo
    import execution.exit_engine as XE
    _rdt, _rhc = XE.datetime, XE.is_hard_close_time
    class _F(_dt.datetime):
        @classmethod
        def now(cls, tz=None): return _dt.datetime(2026, 9, 10, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    XE.datetime = _F; XE.is_hard_close_time = lambda: False
    try:
        xe = XE.ExitEngine(paper_trading=True)
        xe._theta_bleed = lambda *a, **k: False
        xe._rejected_handoff = lambda *a, **k: ""
        base = {"trade_id": "h1", "strategy": "LiquidityHunt", "setup_type": "liquidity_hunt_A2", "direction": "long",
                "option_side": "call", "entry_premium": 0.48, "contracts": 1, "status": "open", "stop_premium": 0.0,
                "target_premium": 0.0, "trail_activation": 0.0, "underlying_entry": 100.2, "underlying_stop": 100.0,
                "underlying_target": 102.5, "orb_range_high": 101.0, "orb_range_low": 100.0, "entry_time": "2026-09-10T09:47:00"}
        H.reset()
        d = xe._evaluate_orb(dict(base), 0.9, _frame([(102.1, 102.6, 102.0, 102.3), (102.3, 102.4, 102.2, 102.35)], "10:05"))
        g = H.live("SweepCreditSpread")
        check("H6 the target WICKED (high 102.6, close 102.3) -> off, and a grant to the sweep is live",
              d.should_exit and "hunt_target_wicked" in str(d.exit_reason) and g is not None and g["level"] == 102.5
              and g["side"] == "call", str(d.exit_reason)[:100])
        d = xe._evaluate_orb(dict(base), 1.2, _frame([(102.3, 102.9, 102.2, 102.8), (102.8, 103.0, 102.7, 102.9)], "10:07"))
        check("H7 the target ACCEPTED (close beyond) -> no wick exit; the runaway's hold logic keeps it",
              not (d.should_exit and "hunt_target_wicked" in str(d.exit_reason)), str(d.exit_reason))
        d = xe._evaluate_orb(dict(base), 0.4, _frame([(100.3, 100.4, 99.7, 99.8), (99.8, 99.9, 99.7, 99.85)], "10:09"))
        check("H8 thesis dead: a close back through the ENTRY boundary (100.0), inside-the-range prices do not trip the 50",
              d.should_exit and ("thesis_dead" in str(d.exit_reason) or "backstop" in str(d.exit_reason)), str(d.exit_reason)[:100])
        d = xe._evaluate_orb(dict(base, trade_id="h1-fresh"), 0.5, _frame([(100.4, 100.7, 100.3, 100.6), (100.6, 100.8, 100.5, 100.7)], "10:11"))   # a fresh id: the trail state is per trade
        check("H8b ...and a bar inside the range above the entry boundary holds", not d.should_exit, str(d.exit_reason))
    finally:
        XE.datetime, XE.is_hard_close_time = _rdt, _rhc
    # H9 the slot
    from execution.position_manager import PositionManager
    pm = PositionManager.__new__(PositionManager)
    pm._open_records = [{"strategy": "LiquidityHunt", "is_liquidity_hunt": 1, "status": "open"}]
    check("H9 an open hunt is not a blocking position", not pm.has_blocking_position())
    pm._open_records = [{"strategy": "ORBStrategy", "status": "open"}]
    check("H9b an open ORB still blocks the credit side (unchanged)", pm.has_blocking_position())
    # H10 the grant lifecycle
    H.reset(); g = H.grant("LiquidityHunt", "SweepCreditSpread", 102.5, "call", ttl=2)
    check("H10 a fresh grant is live", H.live("SweepCreditSpread") is g)
    H.tick(); H.tick(); H.tick()
    check("H10b ...expires after its TTL, recorded, no longer live", g["expired"] and H.live("SweepCreditSpread") is None)
    H.reset(); g2 = H.grant("LiquidityHunt", "SweepCreditSpread", 102.5, "call", ttl=8); H.tick(); H.consume(g2)
    check("H10c ...or is consumed on the sweep's fire, with the tick it fired on", g2["fired"] and g2.get("fired_tick") == 1)

    # ── H12 (r297, HUNT.11): one per break SURVIVES A RESTART - trades.db decides, the set only remembers ──
    from database.trade_logger import get_trade_logger as _gtl, make_record as _mr
    _TL = _gtl()

    def _hunt_row(tid, boundary):
        _TL.log_entry(_mr(trade_id=tid, symbol="TST", strategy="LiquidityHunt", direction="long", option_side="call",
                          strike=101.0, expiry="2026-09-10", contracts=5, entry_premium=0.95, stop_premium=0.0,
                          underlying_stop=float(boundary), orb_range_high=101.0, orb_range_low=100.0,
                          option_symbol="O101", paper_trade=1, is_butterfly=0))

    def _fresh():                                            # a new process: nothing in memory
        h = LH.LiquidityHunt(); h._store = ds; h.planner.symbol = "TST"; LH.FINISHED.clear(); H.reset()
        return h

    def _tick(h, n):
        P.begin_tick(n)
        sg = h.generate_signal(orb=orb, price_now=101.3, now_et="09:42", atr_pct=0.14, chain=chain,
                               df_1m=_frame([(100.9, 101.4, 100.8, 101.3), (101.3, 101.5, 101.2, 101.4)], "09:42"),
                               atm_iv=0.25)
        P.close_tick(st, "TST")
        return sg, row()

    _hunt_row("h12a", 101.0)                                 # today's Hunt on THIS break, from before the "restart"
    sig, r = _tick(_fresh(), 9.0)
    check("H12a after a restart (FINISHED empty) today's Hunt row on the 101.00 break stops the A1: no fire, one per break",
          sig is None and "one per break" in r[1], f"sig={sig and sig.hunt_entry} {r[1][-80:]}")
    with sqlite3.connect(os.environ["OT_TRADES_DB"]) as _c:
        _c.execute("DELETE FROM trades WHERE trade_id='h12a'")
    _hunt_row("h12b", 100.0)                                 # a Hunt on the OTHER boundary only
    sig, r = _tick(_fresh(), 9.1)
    check("H12b a row for another boundary (100.00) does not block the 101.00 break: it fires",
          sig is not None and sig.hunt_entry == "A1" and sig.underlying_stop == 101.0, f"sig={sig and sig.hunt_entry} {r[0]}")
    with sqlite3.connect(os.environ["OT_TRADES_DB"]) as _c:
        _c.execute("DELETE FROM trades WHERE trade_id='h12b'")
    _orig_fin = getattr(LH, "break_finished_in_book", None)     # absent before r297: a FAIL line, not a crash
    if _orig_fin is not None:
        LH.break_finished_in_book = lambda *a, **k: "unreadable"
    try:
        sig, r = _tick(_fresh(), 9.2)
    finally:
        if _orig_fin is not None:
            LH.break_finished_in_book = _orig_fin
    check("H12c an UNREADABLE book fails closed: no fire, the hold names it",
          _orig_fin is not None and sig is None and "UNREADABLE" in r[1] and "one per break" in r[1],
          f"reader={'present' if _orig_fin else 'ABSENT'} sig={sig and sig.hunt_entry} {r[1][-90:]}")
    sig, r = _tick(_fresh(), 9.3)
    check("H12d with no Hunt row today the fresh process fires as before (the book is read, nothing found)",
          sig is not None and sig.hunt_entry == "A1", f"sig={sig and sig.hunt_entry} {r[0]}")
    # ── H13 (r304, HUNT.12): a REFUSED entry does not spend the break - main's real _attempt_hunt door ──
    try:
        import main as _M
        _M._set_admission(None)
        _orig_exec, _orig_lh = _M._execute_entry_signal, _M._liquidity_hunt
        _execs = []
        _M._execute_entry_signal = lambda *a, **k: _execs.append(1)     # execution opens NOTHING (a refusal)

        class _St:
            paper_trading = True

        def _door(h, n):
            _M._liquidity_hunt = h
            P.begin_tick(n)
            _M._attempt_hunt({"price": 101.3, "df_1m": _frame([(100.9, 101.4, 100.8, 101.3), (101.3, 101.5, 101.2, 101.4)],
                                                                  "09:42"), "atm_iv": 0.25},
                             None, _St(), orb=orb, chain=chain, now_hhmm="09:42", atr_pct=0.14)
            P.close_tick(st, "TST")
            return row()
        try:
            h13 = _fresh()
            _door(h13, 9.4)
            r2 = _door(h13, 9.5)
            check("H13a a fire whose execution opened nothing leaves the break OPEN: the next tick fires again",
                  len(_execs) == 2 and ("FIRES" in r2[1] or r2[0] == "TAKE"),
                  f"executions {len(_execs)}, second tick: {r2[0]} {r2[1][-80:]}")
            h13b = _fresh(); _execs.clear()
            _door(h13b, 9.6)                                 # fires; this time it TRADED (the row is in the book)
            _hunt_row("h13b", 101.0)
            _M._release_unfilled_hunt(types.SimpleNamespace(direction="long", underlying_stop=101.0, hunt_entry="A1"), _St())
            r3 = _door(h13b, 9.7)
            check("H13b a fire that left today's trades.db row stays SPENT: one per break",
                  len(_execs) == 1 and "one per break" in r3[1], f"executions {len(_execs)}, {r3[1][-80:]}")
            with sqlite3.connect(os.environ["OT_TRADES_DB"]) as _c:
                _c.execute("DELETE FROM trades WHERE trade_id='h13b'")
            _fresh()
            _orig_fin = LH.break_finished_in_book
            LH.FINISHED.add(("long", 101.0))                 # what the fire does, before execution
            LH.break_finished_in_book = lambda *a, **k: "unreadable"
            try:
                _M._release_unfilled_hunt(types.SimpleNamespace(direction="long", underlying_stop=101.0, hunt_entry="A1"), _St())
                held = ("long", 101.0) in LH.FINISHED
            finally:
                LH.break_finished_in_book = _orig_fin
            check("H13c ...but with the book UNREADABLE the break stays spent (fail closed)", held, f"held {held}")
        finally:
            _M._execute_entry_signal, _M._liquidity_hunt = _orig_exec, _orig_lh
    except Exception as exc:                                    # noqa: BLE001
        check("H13 main's _attempt_hunt door could be driven", False, f"{type(exc).__name__}: {exc}")
    print()
    if FAILED:
        print(f"FAIL — {len(FAILED)} check(s): {FAILED}"); return 1
    print("PASS — check_liquidity_hunt"); return 0


if __name__ == "__main__":
    sys.exit(main())
