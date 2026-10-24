#!/usr/bin/env python3
"""
tests/check_plan_states.py  v1.1
v1.1  2026-10-19  OTV4TEST r305 (GATE.3) — D8/D10 write their heartbeat rows under the symbol the plans panel READS
      (query.INSTRUMENT, which takes the live unit's OT_INSTRUMENT before the checker's), not a literal 'QQQ': on
      SPX-TEST the panel filters WHERE symbol='SPX', so D10 saw no row and went RED 12/13 (found by SPX-TEST,
      MSG-SPX-1019-06; a scratch copy with only that literal changed was GREEN 13/13). Test-only.
EVERY PLAN IS ACTIVE, LOG ONLY OR DORMANT, AND DORMANT WRITES NOTHING (PSTATE.1).

v1.0  2026-10-19  OTV4TEST r303 (PSTATE.1). The operator, 2026-10-19 08:34 ET: "Going forward, I want all the
      trades that are turned off to stop writing to the plan Log"; 08:43 ET: "The intent is dormant plans should
      not write to the ledger, unless we are studying them as 'log only' - I would like each plan to have 3
      states: active, dormant or log only, they can be further categorized as hour-gated or conditional gated";
      08:45 ET: "That looks right to me". ORCS included; CondorManagement / CreditRoll off the [plans] line while
      no credit position is open.

  S1  defaults, fresh interpreter, every switch unset: active = Runaway, Breakout, Hunt, PARK, GEX fly,
      CondorManagement, CreditRoll; dormant = VOLT, ORB trade, ORCS, ATP fly, Sweep, TCS, the condor entry
  S2  every plan the bot registers (import main) has a state and a category (hour / condition)
  S3  the switch values: "1" / "active" = active, "log" = log, "true" on a default-off trade = dormant (and the
      value is named), OT_GEX_BUTTERFLY=0 dormant / =log log, OT_PARK=off dormant / =log log, OT_RUNAWAY=off /
      =log, ORCS via its config flag (a checker's flip still flips the trade)
  D1  a DORMANT plan through a whole board tick (main._plan_skip + close_tick + heartbeat + board_line) writes
      NO plan_tick row, NO plan_heartbeat row and is not on the [plans] line
  D2  a DORMANT plan is never asked: main._safe_strategy does not call it
  D3  the ledger door: PlanLedger.open_plan for the dormant ORB trade returns None and writes no row (the ORB
      rows main.run_analysis writes from the opening-range ENGINE)
  D4  LOG: take() writes LOG-ONLY, opens no plan_ledger row, and main._log_only refuses the signal
  D5  ACTIVE is unchanged: take() writes TAKE and opens the plan_ledger row
  D6  the credit door: a LOG sweep's vertical stops at the top of main._execute_condor_leg; _retired_reason lets a
      LOG sweep be asked and still refuses the default
  D7  CondorManagement is off the [plans] line with 0 legs, on it with 2
  D8  the plans panel (query.show_decisions) reads data/plan_states.json: a dormant plan's old heartbeat is listed
      as DORMANT, not STALE, and an absent one is not NOT RUNNING
  D9  CONDITION-gated silence (the operator, 09:54 ET: "Yes"): on a flat tick a /manage plan and CondorManagement
      write no row and no heartbeat (no "nothing to manage", no "dispatch gap"); CondorManagement's legs=0 HOLD is
      not written, its legs=2 row is
  D10 the panel: a /manage plan's old heartbeat reads IDLE (nothing to manage) with no open position of its
      strategy, and STALE while one is open
D1-D10 drive the real code on scratch stores and run on the previous HEAD too (where each is RED).
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
"""
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stdout
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_plan_states_")
for _k, _v in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"),
               ("OT_LOG_FILE", "bot.log"), ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_RESTING_DB", "r.db"),
               ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_RESTING_STOP_STATE", "rs.json"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "plan_states.json")):
    os.environ[_k] = os.path.join(_TD, _v)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
SWITCHES = ("OT_VOLT", "OT_ORB_TRADE", "OT_ATP_BUTTERFLY", "OT_ORCS", "OT_SWEEP_CS", "OT_TCS_ACTIVE",
            "OT_GEX_BUTTERFLY", "OT_PARK", "OT_RUNAWAY", "OT_BREAKOUT", "OT_HUNT")
for _k in SWITCHES:
    os.environ.pop(_k, None)
ET = ZoneInfo("America/New_York")
FAILED, RAN = [], []
PY = sys.executable


def check(name, ok, detail=""):
    RAN.append(name)
    print(("  PASS  " if ok else "  FAIL  ") + name + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name)


def fresh(code, env_extra=None):
    """Run `code` in a fresh interpreter with every switch unset (plus env_extra); its last stdout line, JSON."""
    env = {k: v for k, v in os.environ.items() if k not in SWITCHES}
    env.update(env_extra or {})
    p = subprocess.run([PY, "-c", "import sys; sys.path.insert(0, %r)\n%s" % (ROOT, code)],
                       capture_output=True, text=True, env=env, cwd=ROOT, timeout=120)
    out = (p.stdout or "").strip().splitlines()
    try:
        return json.loads(out[-1]) if out else {"err": p.stderr[-400:]}
    except Exception:                                           # noqa: BLE001
        return {"err": (p.stderr or p.stdout)[-400:]}


class _Sig:
    def __init__(self, name, side="call"):
        self.strategy_name = name
        self.option_side = side
        self.direction = "long"
        self.strike = 700.0
        self.entry_premium = 1.0
        self.underlying_stop = 699.0


def rows(dc, sql, args=()):
    try:
        return dc.execute(sql, args).fetchall()
    except Exception:                                           # noqa: BLE001
        return []


def main():
    try:
        import main as M
        from strategy import plan as P
        from data.derived_store import get_derived_store
        from derived.plan_ledger import PlanLedger
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN — imports failed: {type(exc).__name__}: {exc}")
        return 2
    store = get_derived_store()
    P.bind_store(store)
    P.ensure_tables(store)
    try:
        PlanLedger(store, "QQQ")
    except Exception:                                           # noqa: BLE001
        pass
    dc = store.conn

    # ── S1-S3: the states, read in fresh interpreters (config reads several switches at import) ──
    ruled_active = ["Breakout", "CondorManagement", "CreditRoll", "GEXPinButterfly", "LiquidityHunt", "PARK",
                    "RunawayContinuation"]
    ruled_dormant = ["ATPButterfly", "IronCondorStrategy", "ORBStrategy", "OpeningRangeCreditSpread",
                     "SweepCreditSpread", "TrendCreditSpread", "VOLT"]
    st = fresh("import json\nfrom strategy import plan_state as S\n"
               "print(json.dumps({n: S.state(n) for n in S.TABLE}))")
    act = sorted(k for k, v in st.items() if v == "active")
    dor = sorted(k for k, v in st.items() if v == "dormant")
    check("S1 defaults = today's roster (active / dormant as ruled; nothing LOG)",
          act == ruled_active and dor == ruled_dormant and "log" not in st.values(), f"{st}")

    try:
        from strategy import plan_state as S
        names = sorted(P.REGISTRY)
        bad = [n for n in names if not S.known(n) or S.category(n) not in (S.HOUR, S.CONDITION)]
        check("S2 every registered plan has a state and a category", names and not bad, f"unknown {bad} of {names}")
    except Exception as exc:                                    # noqa: BLE001
        check("S2 every registered plan has a state and a category", False, f"{type(exc).__name__}: {exc}")

    probe = ("import json\nfrom strategy import plan_state as S\n"
             "print(json.dumps([S.state(%r), S.refused()]))")
    cases = [("VOLT", {"OT_VOLT": "1"}, "active"), ("VOLT", {"OT_VOLT": "active"}, "active"),
             ("VOLT", {"OT_VOLT": "log"}, "log"), ("VOLT", {"OT_VOLT": "true"}, "dormant"),
             ("ORBStrategy", {"OT_ORB_TRADE": "log"}, "log"),
             ("GEXPinButterfly", {"OT_GEX_BUTTERFLY": "0"}, "dormant"),
             ("GEXPinButterfly", {"OT_GEX_BUTTERFLY": "log"}, "log"),
             ("PARK", {"OT_PARK": "off"}, "dormant"), ("PARK", {"OT_PARK": "log"}, "log"),
             ("RunawayContinuation", {"OT_RUNAWAY": "off"}, "dormant"),
             ("RunawayContinuation", {"OT_RUNAWAY": "log"}, "log"),
             ("OpeningRangeCreditSpread", {"OT_ORCS": "1"}, "active"),
             ("OpeningRangeCreditSpread", {"OT_ORCS": "log"}, "log"),
             ("SweepCreditSpread", {"OT_SWEEP_CS": "log"}, "log")]
    got = [(n, e, fresh(probe % n, e)) for n, e, _w in cases]
    miss = [(n, e, g) for (n, e, g), (_n, _e, w) in zip(got, cases) if not (isinstance(g, list) and g[0] == w)]
    true_named = next((g for n, e, g in got if e == {"OT_VOLT": "true"}), None)
    check("S3 the switch values (legacy '1', active, log, off, the config flags) and an unknown value is named",
          not miss and isinstance(true_named, list) and "OT_VOLT='true'" in json.dumps(true_named[1]),
          f"wrong: {miss}; 'true' -> {true_named}")

    # ── D1: a dormant VOLT through a whole board tick writes nothing ──
    for k in SWITCHES:
        os.environ.pop(k, None)
    P.begin_tick(time.time())
    M._plan_skip("VOLT", "retired by test", gate="retired")
    P.close_tick(store, "QQQ")
    n_tick = len(rows(dc, "SELECT 1 FROM plan_tick WHERE strategy='VOLT'"))
    n_hb = len(rows(dc, "SELECT 1 FROM plan_heartbeat WHERE plan='VOLT'"))
    line = P.board_line()
    check("D1 a DORMANT plan writes no plan_tick / plan_heartbeat row and is not on the [plans] line",
          n_tick == 0 and n_hb == 0 and "VOLT=" not in line and "Breakout=" in line,
          f"plan_tick {n_tick}, heartbeat {n_hb}, line has VOLT={'VOLT=' in line}")

    # ── D2: a dormant plan is never asked ──
    called = []
    M._set_admission(None)
    M._safe_strategy("VOLT", lambda: called.append(1))
    M._safe_strategy("Breakout", lambda: called.append(2))
    check("D2 main._safe_strategy never asks a DORMANT plan (an active one still is)",
          called == [2], f"called {called}")

    # ── D3: the ledger door ──
    led = PlanLedger(store, "QQQ")
    pid = led.open_plan("ORBStrategy", "CONFIRMED", {"price": 700.0}, direction="LONG")
    n_led = len(rows(dc, "SELECT 1 FROM plan_ledger WHERE strategy='ORBStrategy'"))
    check("D3 PlanLedger.open_plan writes nothing for the DORMANT ORB trade", pid is None and n_led == 0,
          f"pid {pid}, rows {n_led}")

    # ── D4: LOG ──
    os.environ["OT_VOLT"] = "log"
    P.begin_tick(time.time())
    vplan = P.REGISTRY.get("VOLT")
    r4 = None
    if vplan is not None:
        r4 = vplan.tick(700.0, "long").take(_Sig("VOLT"))
    v_rows = rows(dc, "SELECT verdict FROM plan_tick WHERE strategy='VOLT'")
    v_led = len(rows(dc, "SELECT 1 FROM plan_ledger WHERE strategy='VOLT'"))
    refused = M._log_only(_Sig("VOLT"), {})
    check("D4 LOG: take() writes LOG-ONLY, opens no plan_ledger row, and main._log_only refuses the signal",
          vplan is not None and r4 is not None and [v for (v,) in v_rows] == ["LOG-ONLY"] and v_led == 0 and refused,
          f"rows {v_rows}, ledger {v_led}, _log_only {refused}")
    os.environ.pop("OT_VOLT", None)

    # ── D5: ACTIVE unchanged ──
    P.begin_tick(time.time())
    bplan = P.REGISTRY.get("Breakout")
    if bplan is not None:
        bplan.tick(700.0, "long").take(_Sig("Breakout"))
    b_rows = rows(dc, "SELECT verdict FROM plan_tick WHERE strategy='Breakout' AND verdict IN ('TAKE','LOG-ONLY')")
    b_led = len(rows(dc, "SELECT 1 FROM plan_ledger WHERE strategy='Breakout'"))
    check("D5 ACTIVE: take() writes TAKE and opens the plan_ledger row; main._log_only lets it through",
          [v for (v,) in b_rows] == ["TAKE"] and b_led == 1 and not M._log_only(_Sig("Breakout"), {}),
          f"rows {b_rows}, ledger {b_led}")

    # ── D6: the credit door ──
    os.environ["OT_SWEEP_CS"] = "log"
    seen = []

    class _Stop(Exception):
        pass

    def _rec(*a, **k):
        seen.append(1)
        raise _Stop()
    orig = M.entries_open                                    # the first step AFTER the credit door
    M.entries_open = _rec
    try:
        st_ = M.BotState()
        st_.paper_trading = True
        try:
            M._execute_condor_leg(_Sig("SweepCreditSpread", "put"), st_, {})
        except _Stop:
            pass
    finally:
        M.entries_open = orig
    log_reason = M._retired_reason("SweepCreditSpread")
    os.environ.pop("OT_SWEEP_CS", None)
    dflt_reason = M._retired_reason("SweepCreditSpread")
    check("D6 a LOG sweep's vertical stops at the top of _execute_condor_leg; a LOG sweep is asked, the default "
          "still refused", not seen and log_reason == "" and dflt_reason != "",
          f"reached the order path {bool(seen)}, log reason {log_reason!r}, default {dflt_reason!r}")

    # ── D7: CondorManagement on the line only while it has legs ──
    cm = P.REGISTRY.get("CondorManagement") or P.Plan("CondorManagement", ("legs",), self_ledgers=True)
    P.begin_tick(time.time())
    t = cm.tick(700.0)
    t.check("legs", 0, False)
    t.hold("no credit verticals open — nothing to manage")
    off_line = "CondorManagement=" not in P.board_line()
    P.begin_tick(time.time())
    t = cm.tick(700.0)
    t.check("legs", 2, True)
    t.hold("both legs open")
    on_line = "CondorManagement=" in P.board_line()
    check("D7 CondorManagement is off the [plans] line with 0 legs and on it with 2", off_line and on_line,
          f"off with 0: {off_line}, on with 2: {on_line}")

    # ── D8: the plans panel ──
    try:
        from strategy import plan_state as S
        S.write_states_file()
    except Exception:                                           # noqa: BLE001
        pass
    pdb = os.path.join(_TD, "panel.db")
    pc = sqlite3.connect(pdb)
    pc.execute("CREATE TABLE plan_heartbeat (symbol TEXT, plan TEXT, ts_epoch REAL, tick_id INTEGER, state TEXT,"
               " gate TEXT, verdict TEXT, watching TEXT, PRIMARY KEY (symbol, plan))")
    now = datetime.now(ET).replace(hour=10, minute=0, second=0, microsecond=0)
    pc.execute("INSERT INTO plan_heartbeat VALUES ('QQQ','VOLT',?,1,'IDLE','enabled','DORMANT','old')",
               (now.timestamp() - 3600,))
    pc.execute("INSERT INTO plan_heartbeat VALUES ('QQQ','Breakout',?,9,'EVALUATING','','DECLINE','fresh')",
               (now.timestamp() - 5,))
    pc.commit()
    try:
        import query as Q
        _psym = Q.INSTRUMENT if Q.INSTRUMENT and Q.INSTRUMENT != "UNSET" else "QQQ"   # r305: the panel's symbol
        pc.execute("UPDATE plan_heartbeat SET symbol=?", (_psym,))
        pc.commit()
        Q.now_et = lambda: now
        buf = io.StringIO()
        with redirect_stdout(buf):
            Q.show_decisions(pc)
        out = buf.getvalue()
    except Exception as exc:                                    # noqa: BLE001
        out = f"RAISED {type(exc).__name__}: {exc}"
    volt_lines = [ln for ln in out.splitlines() if "VOLT" in ln]
    check("D8 the plans panel lists a DORMANT plan as DORMANT - not STALE, not NOT RUNNING",
          any("DORMANT" in ln for ln in volt_lines) and not any("STALE" in ln or "NOT RUNNING" in ln
                                                                for ln in volt_lines),
          f"VOLT lines: {volt_lines[:4]}")

    # ── D9: condition-gated silence ──
    mg = P.REGISTRY.get("Breakout/manage") or P.Plan("Breakout/manage", ("legs",), self_ledgers=True)
    cm2 = P.REGISTRY.get("CondorManagement") or P.Plan("CondorManagement", ("legs",), self_ledgers=True)
    dc.execute("DELETE FROM plan_tick WHERE strategy IN ('Breakout/manage','CondorManagement')")
    dc.execute("DELETE FROM plan_heartbeat WHERE plan IN ('Breakout/manage','CondorManagement')")
    store.commit()
    P.begin_tick(time.time())
    M._plan_skip_management("no open position — nothing to manage")
    P.close_tick(store, "QQQ")
    P.begin_tick(time.time())
    t = cm2.tick(700.0)
    t.check("legs", 0, False)
    t.hold("no credit verticals open — nothing to manage")
    P.close_tick(store, "QQQ")
    flat_rows = rows(dc, "SELECT strategy, verdict FROM plan_tick WHERE strategy IN ('Breakout/manage','CondorManagement')")
    flat_hb = rows(dc, "SELECT plan FROM plan_heartbeat WHERE plan IN ('Breakout/manage','CondorManagement')")
    P.begin_tick(time.time())
    t = cm2.tick(700.0)
    t.check("legs", 2, True)
    t.hold("both legs open - managing")
    live_rows = rows(dc, "SELECT verdict FROM plan_tick WHERE strategy='CondorManagement'")
    check("D9 a condition-gated plan writes nothing while its condition is absent, and writes once it holds",
          not flat_rows and not flat_hb and [v for (v,) in live_rows] == ["HOLD"],
          f"flat rows {flat_rows}, flat heartbeats {flat_hb}, with legs {live_rows}")

    # ── D10: the panel - IDLE vs STALE for a /manage plan ──
    try:
        import query as Q
        tc = sqlite3.connect(Q.DB_PATH)
        tc.execute("CREATE TABLE IF NOT EXISTS trades (trade_id TEXT PRIMARY KEY, strategy TEXT, status TEXT, "
                   "is_condor_leg INTEGER DEFAULT 0, credit_received REAL)")
        tc.commit()
        _psym = Q.INSTRUMENT if Q.INSTRUMENT and Q.INSTRUMENT != "UNSET" else "QQQ"   # r305: the panel's symbol
        pc.execute("INSERT OR REPLACE INTO plan_heartbeat VALUES (?,'LiquidityHunt/manage',?,1,'IDLE','','INACTIVE','old')",
                   (_psym, now.timestamp() - 7200))
        pc.commit()

        def panel():
            b = io.StringIO()
            with redirect_stdout(b):
                Q.show_decisions(pc)
            return [ln for ln in b.getvalue().splitlines() if "LiquidityHunt/manage" in ln]
        idle = panel()
        tc.execute("INSERT INTO trades (trade_id, strategy, status) VALUES ('h1', 'LiquidityHunt', 'OPEN')")
        tc.commit()
        stale = panel()
        tc.execute("DELETE FROM trades WHERE trade_id='h1'")
        tc.commit()
        ok10 = (any("IDLE" in ln for ln in idle) and not any("STALE" in ln for ln in idle)
                and any("STALE" in ln for ln in stale))
    except Exception as exc:                                    # noqa: BLE001
        idle, stale, ok10 = [f"RAISED {type(exc).__name__}: {exc}"], [], False
    check("D10 a /manage plan's old heartbeat is IDLE with nothing open, STALE while its position is open",
          ok10, f"no position: {idle[:2]}; position open: {stale[:2]}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(n.split()[0] for n in FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
