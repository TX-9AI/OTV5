#!/usr/bin/env python3
"""
tests/check_market_time.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-24  CD.2 — EVERY READER OF A DERIVED OR SERIES TABLE JUDGES A ROW BY ITS MARKET TIME. The operator,
      2026-10-24: the primer seeds inputs and derivatives rebuild, and "populating those tables should be harmless" -
      which holds only if no reader serves a stale or seeded row as current. Born red on OTV4TEST c825449.
  Each check SEEDS a scratch derived store with (a) a STALE row (an old market time, written now) and/or (b) a FOREIGN
  row (another day), then drives the REAL reader and proves it ignores them, and that a FRESH row is still served.
  M1  level_event: latest_rejection() never serves a row without bar_close_epoch, nor one whose bar closed before
      `since`, whatever its write time; a fresh row (bar closed after `since`) is served, newest bar first
  M2  the exit hand-off: a REJECTED whose bar closed BEFORE the entry is not a hand-off; one after it is (r317 + CD.2)
  M3  sweep_plan: the first look SPENDS the session's existing REJECTED (a restart does not re-fire it); a later fresh
      REJECTED on the same level still fires (§37 as tcs_plan r112)
  M4  surface: gamma_regime.level() ignores a row with quote_ts older than 300 s however recent its write time, and a
      row with no quote_ts; anchors.charm_at ignores quote_ts older than 120 s; gex_between is retired (None)
  M5  forks: fork_dir() ignores a row whose bar_ts_ms is not the frame's latest closed bar (a dead fork written now),
      serves a current built fork, and reports no direction for a current REJECTED row
  M6  indicator_series: anchors.vwap() is vwap_now()[0] - yesterday's anchor is never served
  M7  LevelEngine.board(): a seeded live ledger with NO sync mark -> state "not_synced", empty; a sync mark older
      than BOARD_SYNC_MAX_AGE_S -> "not_synced"; a fresh mark -> "ok" with the levels
  M8  character_engine._hydrate: an open row from before today's session is closed as stale, not adopted; today's is
  M9  plan_ledger.live_plans(): a QUALIFIED plan created before today's session is not live; today's is;
      LEG1_FILLED from before today IS (the broker decides it)
  M10 the writers stamp market time: a level event's bar_close_epoch = bar start + span (1m: 60 s; 1h: 3600 s);
      a rail event is REFUSED when its bar closed more than BOOK_FRESH_S ago
Run: OT_INSTRUMENT=QQQ python3 tests/check_market_time.py
"""
import atexit
import glob as _glob
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
_SCRATCH = tempfile.mkdtemp(prefix="mktchk_")
atexit.register(shutil.rmtree, _SCRATCH, True)
for _k, _v in (("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"), ("OT_TRADES_DB", "t.db"),
               ("OT_LOG_FILE", "bot.log"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_SIGNAL_JOURNAL_DIR", "sj")):
    os.environ.setdefault(_k, os.path.join(_SCRATCH, _v))

ET = ZoneInfo("America/New_York")
FAILED = []
SYM = "QQQ"


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _store():
    from data.derived_store import DerivedStore
    return DerivedStore(path=os.path.join(_SCRATCH, f"d{len(os.listdir(_SCRATCH))}.db"))


def _ev(store, lid, kind, bar_close, write_ts, event="REJECTED", price=100.0, with_mkt=True):
    row = (SYM, lid, datetime.fromtimestamp(bar_close - 60, ET).isoformat(), write_ts, event, price, kind, "ny",
           0.001, "shallow", 1, price - 0.1)
    if with_mkt:
        row = row + (bar_close,)
    return store.insert_level_event(row)


def main() -> int:
    now = time.time()
    day0 = datetime.fromtimestamp(now, ET).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    since = now - 3600.0

    # ── M1 latest_rejection by market time ────────────────────────────────────────────────────────────
    try:
        st = _store()
        _ev(st, "L-nomkt", "resistance", now - 10, now, with_mkt=False)            # no market time: never served
        _ev(st, "L-oldbar", "resistance", since - 7200, now, price=101.0)          # old bar, written NOW
        _ev(st, "L-fresh", "resistance", since + 600, now - 5000, price=102.0)     # fresh bar, written long ago
        _ev(st, "L-fresher", "resistance", since + 1200, now - 9000, price=103.0)  # the newest BAR, oldest write
        r = st.latest_rejection(SYM, since_ts=since, kind="resistance")
        r_none = _store().latest_rejection(SYM, since_ts=since)
        check("M1 latest_rejection: no-market-time and old-bar rows ignored; the newest BAR wins, not the newest write",
              r is not None and r["level_id"] == "L-fresher" and r_none is None, f"{r}")
    except Exception as exc:                                    # noqa: BLE001
        check("M1 latest_rejection", False, f"{type(exc).__name__}: {exc}")

    # ── M2 the exit hand-off compares the bar's close with the entry ─────────────────────────────────
    try:
        import execution.exit_engine as XE
        import data.derived_store as DS
        st = _store()
        saved = DS.get_derived_store
        DS.get_derived_store = lambda: st
        try:
            xe = XE.ExitEngine(paper_trading=True)
            t_entry = now - 600
            rec = {"trade_id": "m2", "strategy": "RunawayContinuation", "direction": "long", "entry_premium": 1.0,
                   "contracts": 1, "underlying_entry": 100.0,
                   "entry_time": datetime.fromtimestamp(t_entry, ET).isoformat()}
            _ev(st, "L-before", "resistance", t_entry - 120, now, price=105.0)     # bar closed BEFORE entry, written now
            h1 = xe._rejected_handoff(dict(rec), "long")
            _ev(st, "L-after", "resistance", t_entry + 120, t_entry + 125, price=106.0)
            h2 = xe._rejected_handoff(dict(rec), "long")
            check("M2 hand-off: a REJECTED whose bar closed before the entry is not a hand-off; one after it is",
                  h1 == "" and "handoff" in h2 and "106.00" in h2, f"h1={h1!r} h2={h2!r}")
        finally:
            DS.get_derived_store = saved
    except Exception as exc:                                    # noqa: BLE001
        check("M2 hand-off", False, f"{type(exc).__name__}: {exc}")

    # ── M3 the sweep's first look spends what exists ──────────────────────────────────────────────────
    try:
        import strategy.sweep_plan as SP
        st = _store()
        st.mark_level_sync(SYM, now)
        lid = f"{SYM}:ny:100.00"
        st.upsert_level((lid, SYM, 100.0, "resistance", "ny", "session", now - 3600, 0, None, 0, None, None, 1))
        _ev(st, lid, "resistance", now - 300, now - 290, price=100.0)            # exists BEFORE this process looks
        SP._symbol_of = lambda: SYM
        plan = SP.SweepPlan(store=st)
        import pandas as pd
        idx = pd.date_range(end=pd.Timestamp.now(tz="America/New_York").floor("min"), periods=5, freq="1min")
        frame = pd.DataFrame({"open": 99.8, "high": 100.2, "low": 99.6, "close": 99.9, "volume": 1}, index=idx)
        kw = dict(price_now=99.9, now_et="10:32", atr_pct=0.08, orb_high=99.5, orb_low=97.5, chain=None,
                  df_1m=frame, session_open_epoch=since)
        try:
            p1 = plan.prepare(**kw)
        except TypeError:
            kw.pop("chain", None)
            p1 = plan.prepare(**kw)
        key_old = (lid, datetime.fromtimestamp(now - 360, ET).isoformat())
        spent_first = key_old in plan._fired_events
        _ev(st, lid, "resistance", now - 60, now - 50, price=100.0)              # a NEW rejection, after the first look
        key_new = (lid, datetime.fromtimestamp(now - 120, ET).isoformat())
        fresh = st.latest_rejection(SYM, since_ts=since)
        check("M3 sweep first look: the pre-existing REJECTED is spent (never fires); a later fresh one is not spent",
              spent_first and getattr(p1, "rejected", None) is None and fresh is not None
              and (fresh["level_id"], fresh["bar_ts"]) == key_new and key_new not in plan._fired_events,
              f"spent={spent_first} p1.rejected={getattr(p1, 'rejected', None)} fresh={fresh and fresh['bar_ts']} "
              f"fired={plan._fired_events}")
    except Exception as exc:                                    # noqa: BLE001
        check("M3 sweep first look", False, f"{type(exc).__name__}: {exc}")

    # ── M4 surface by quote_ts ────────────────────────────────────────────────────────────────────────
    try:
        import derived.gamma_regime as GR
        import derived.anchors as AN
        import data.derived_store as DS
        st = _store()
        saved = DS.get_derived_store
        DS.get_derived_store = lambda: st
        try:
            def srow(write_ts, quote_ts, gex, charm, strike=100.0):
                r = (SYM, write_ts, strike, "2026-10-24", charm, 0.1, gex, None, 0.2, None, 30.0, 0.0)
                st.append_surface([r + (quote_ts,)] if quote_ts is not None else [r])
            srow(now, now - 900, 50e6, 1.0)                     # stale QUOTES, written now
            srow(now - 2, None, 60e6, 2.0)                      # no quote time
            lv_stale = GR.level(now=now)
            ch_stale = AN.charm_at(100.0, now=now)
            srow(now - 3000, now - 30, 70e6, 3.0)               # fresh QUOTES, written long ago
            lv_ok = GR.level(now=now)
            ch_ok = AN.charm_at(100.0, now=now)
            check("M4 surface: stale-quote and no-quote-time rows ignored (level None, charm None); fresh quotes served; "
                  "gex_between retired",
                  lv_stale is None and ch_stale is None and lv_ok == 70.0 and ch_ok == 3.0
                  and AN.gex_between(90.0, 110.0) is None,
                  f"lv_stale={lv_stale} ch_stale={ch_stale} lv_ok={lv_ok} ch_ok={ch_ok}")
        finally:
            DS.get_derived_store = saved
    except Exception as exc:                                    # noqa: BLE001
        check("M4 surface", False, f"{type(exc).__name__}: {exc}")

    # ── M5 forks by bar_ts_ms ─────────────────────────────────────────────────────────────────────────
    try:
        import derived.anchors as AN
        import data.derived_store as DS
        st = _store()
        saved = DS.get_derived_store
        DS.get_derived_store = lambda: st
        try:
            def frow(write_ts, bar_ts, built, direction, reason=None):
                base = (SYM, "1h", write_ts, built, reason, 3, direction, 1.0, 100.0, 2.0, 101.0, 3.0, 99.0, 0.0, 100.0,
                        0.5, 0.9, 70, None, None, None)
                st.append_forks([base + (int(bar_ts * 1000),)] if bar_ts is not None else [base])
            frow(now - 2, now - 5 * 3600, 1, "UP")              # a dead fork (5 h old bar), written just now
            frow(now - 1, None, 1, "DOWN")                      # no market time
            d_stale = AN.fork_dir("1h", now=now)
            frow(now - 3000, now - 3600 - 30, 1, "UP")          # the latest closed hour, written 50 min ago
            d_ok = AN.fork_dir("1h", now=now)
            frow(now, now - 3600, 0, None, "NO_PIVOTS")         # a current REJECTED row supersedes it
            d_rej = AN.fork_dir("1h", now=now)
            r_rej = AN.fork_row("1h", now=now)
            check("M5 forks: a dead fork written now and a no-time row are ignored; a current built fork is served; a "
                  "current REJECTED row gives no direction",
                  d_stale is None and d_ok == "UP" and d_rej is None and r_rej is not None and r_rej["built"] is False,
                  f"stale={d_stale} ok={d_ok} rej={d_rej} row={r_rej}")
        finally:
            DS.get_derived_store = saved
    except Exception as exc:                                    # noqa: BLE001
        check("M5 forks", False, f"{type(exc).__name__}: {exc}")

    # ── M6 vwap() is the decision reader ─────────────────────────────────────────────────────────────
    try:
        import derived.anchors as AN
        import data.derived_store as DS
        st = _store()
        saved = DS.get_derived_store
        DS.get_derived_store = lambda: st
        try:
            y_open = datetime.fromtimestamp(now, ET).replace(hour=9, minute=30, second=0, microsecond=0).timestamp() - 86400
            st.conn.execute("INSERT INTO indicator_series (symbol, interval, ts_epoch, bar_ts_ms, vwap, vwap_anchor_ms)"
                            " VALUES (?,?,?,?,?,?)", (SYM, "5m", now, int((now - 30) * 1000), 123.45, int(y_open * 1000)))
            st.conn.commit()
            v = AN.vwap()
            check("M6 anchors.vwap(): a VWAP anchored to yesterday's open is not served (None), as vwap_now rules",
                  v is None, f"vwap={v}")
        finally:
            DS.get_derived_store = saved
    except Exception as exc:                                    # noqa: BLE001
        check("M6 vwap", False, f"{type(exc).__name__}: {exc}")

    # ── M7 the board fails closed until synced ────────────────────────────────────────────────────────
    try:
        import derived.levels as L
        st = _store()
        st.upsert_level((f"{SYM}:ny:101.00", SYM, 101.0, "resistance", "ny", "session", now - 3600, 0, None, 0, None, None, 1))
        st.upsert_level((f"{SYM}:ny:99.00", SYM, 99.0, "support", "ny", "session", now - 3600, 0, None, 0, None, None, 1))
        eng = L.LevelEngine(st, SYM, forks=None)
        b0 = eng.board(100.0)
        st.mark_level_sync(SYM, now - L.BOARD_SYNC_MAX_AGE_S - 60)
        b1 = eng.board(100.0)
        st.mark_level_sync(SYM, now - 30)
        b2 = eng.board(100.0)
        check("M7 board: no sync mark -> not_synced/empty; a stale mark -> not_synced; a fresh mark -> ok with levels",
              b0["state"] == "not_synced" and not b0["above"] and b1["state"] == "not_synced"
              and b2["state"] == "ok" and len(b2["above"]) == 1 and len(b2["below"]) == 1,
              f"{b0['state']} {b1['state']} {b2['state']} above={len(b2.get('above', []))}")
    except Exception as exc:                                    # noqa: BLE001
        check("M7 board", False, f"{type(exc).__name__}: {exc}")

    # ── M8 character hydrate ──────────────────────────────────────────────────────────────────────────
    try:
        import derived.character_engine as CE
        for label, entered, want_adopt in (("yesterday", day0 - 3600, False), ("today", day0 + 60, True)):
            st = _store()
            ce = CE.CharacterEngine(st, SYM) if "symbol" in CE.CharacterEngine.__init__.__code__.co_varnames \
                else CE.CharacterEngine(st)
            ce.symbol = SYM
            ce._ensure()
            st.conn.execute("INSERT INTO character_ledger (symbol, character, entered_ts) VALUES (?,?,?)",
                            (SYM, "TRENDING", entered))
            st.commit()
            ce._hydrate()
            closed = st.conn.execute("SELECT exited_ts FROM character_ledger WHERE symbol=?", (SYM,)).fetchone()[0]
            adopted = ce._state == "TRENDING"
            check(f"M8 character hydrate: an open row from {label} is {'adopted' if want_adopt else 'closed as stale, not adopted'}",
                  adopted == want_adopt and (closed is None) == want_adopt, f"adopted={adopted} exited_ts={closed}")
    except Exception as exc:                                    # noqa: BLE001
        check("M8 character", False, f"{type(exc).__name__}: {exc}")

    # ── M9 plan_ledger live_plans by session ──────────────────────────────────────────────────────────
    try:
        import derived.plan_ledger as PL
        st = _store()
        pl = PL.PlanLedger(st, SYM) if "symbol" in PL.PlanLedger.__init__.__code__.co_varnames else PL.PlanLedger(st)
        pl.symbol = SYM
        pl._ensure()
        for pid, state, created in (("old-q", "QUALIFIED", day0 - 7200), ("new-q", "QUALIFIED", day0 + 60),
                                    ("old-leg", "LEG1_FILLED", day0 - 7200)):
            st.conn.execute("INSERT INTO plan_ledger (plan_id, symbol, strategy, state, created_ts, updated_ts)"
                            " VALUES (?,?,?,?,?,?)", (pid, SYM, "IronCondorStrategy", state, created, created))
        st.commit()
        live = sorted(p["plan_id"] for p in pl.live_plans())
        check("M9 live_plans: a QUALIFIED plan from before today is not live; today's is; LEG1_FILLED from before is",
              live == ["new-q", "old-leg"], f"{live}")
    except Exception as exc:                                    # noqa: BLE001
        check("M9 plan_ledger", False, f"{type(exc).__name__}: {exc}")

    # ── M10 the writers stamp market time; the rail path refuses an old bar ──────────────────────────
    try:
        import derived.levels as L
        st = _store()
        eng = L.LevelEngine(st, SYM, forks=None)
        bar_ms = int((now - 120) * 1000)
        eng._emit(st, SYM, "L-w", 100.0, "resistance", "ny", "x", now, "REJECTED",
                  {"pierce_pct": 0.0, "depth": "shallow", "closes_back": 1}, 99.9, bar_close_epoch=bar_ms / 1000 + 60)
        got = st.conn.execute("SELECT bar_close_epoch FROM level_event WHERE level_id='L-w'").fetchone()[0]
        # the rail path: a bar that closed long ago is refused before any rail is judged
        import pandas as pd
        old = pd.Timestamp.now(tz="America/New_York").floor("min") - pd.Timedelta(minutes=30)
        df = pd.DataFrame({"open": [100.0, 100.0], "high": [100.5, 100.0], "low": [99.5, 100.0], "close": [100.0, 100.0]},
                          index=[old, old + pd.Timedelta(minutes=1)])
        eng._fork_key = lambda: "fk"
        called = []
        eng.tines_now = lambda *a, **k: called.append(1) or []
        n = eng._rails_sync({"df_1m": df}, SYM)
        check("M10 writers: a level event carries bar start + span as its market time; the rail path refuses a bar "
              "that closed > BOOK_FRESH_S ago before judging any rail",
              abs(float(got) - (bar_ms / 1000 + 60)) < 1e-6 and n == 0 and not called,
              f"got={got} n={n} tines_called={bool(called)}")
    except Exception as exc:                                    # noqa: BLE001
        check("M10 writers", False, f"{type(exc).__name__}: {exc}")

    print(f"\n{'GREEN' if not FAILED else 'RED — ' + str(sorted(set(FAILED)))}")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
