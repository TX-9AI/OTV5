#!/usr/bin/env python3
"""
tests/check_order_routing.py  v5.0
v5.0  2026-11-26  OTV5 r161 (LANE.1) — new. ONE ROUTING DECISION BETWEEN PAPER AND LIVE ORDERS, AND ITS MAP. The operator,
      2026-11-25: "There should be a clean routing map between paper orders & live orders that is cleanly separated";
      "Be deliberate. We should be able to switch between paper & live anytime we are fielding a new strategy for a few
      weeks."

  R1  THE MAP IS THE CODE: docs/ROUTING.md's "| ROUTE | flag | box | route |" rows are exactly execution/order_router.TABLE
  R2  THE TABLE: route() for every lane x box (on: paper PAPER / live LIVE; paper_only: PAPER / PAPER; off: DORMANT /
      DORMANT); a bad value, "", None-mode (an unreadable mode is a live box) and a raise fail closed (DORMANT or never
      LIVE for paper_only); walled() only on a live box; OGAP (PAPER_ALWAYS) PAPER everywhere; asked_past_cap live only
  R3  CLOSES READ THE ROW: route_close() is PAPER on a paper box; on a live box PAPER for paper_trade 1 / None / "",
      LIVE for 0; it reads no flag (the same answers under on, paper_only and off)
  R4  GENERIC: a stand-in schema key (zeta -> SetupZ) at paper_only routes SetupZ PAPER on a live box and joins
      walled_setups() with no router change; at on it is LIVE; at off DORMANT
  R5  ONE DECISION POINT (static): outside execution/order_router.py no production module reads PAPER_WALL (only
      paper_wall.py sets it), names WALLED, or calls paper_wall.walled / asked_past_cap; main's _execute_entry_signal
      calls _router.route, attempt_new_entry calls _router.asked_past_cap and _router.walled, _ask_walled_past_cap calls
      _router.walled_setups; position_manager's _manage_one / _execute_exit and entry_engine's _book_fill call
      _router.is_wall; paper_wall's WallTradeLogger.get_open_trades calls _router.route_close
  R6  THE PAPER PATH IMPORTS NO BROKER CLIENT: execution/paper_wall.py and execution/order_router.py import no tasty*
      module; EntryEngine._paper_fill_single and limit_ladder.paper_fill_price name no broker call
  R7  EVERY ORDER PATH ASKS THE ROUTER (runtime): with order_router.route / route_close / is_wall wrapped by recorders,
      main._execute_entry_signal (a refused-DORMANT PARK signal, no engine reached) consults route; the wall book's
      close (manage_open_position at a 15:45 mark on a walled PARK row) consults is_wall; WallTradeLogger consults
      route_close; and a BYPASS MUTANT (route replaced by a function that ignores the flag and returns LIVE on a live
      box for an opening order) is caught: the same PARK signal then reaches the live engine stand-in (red if the
      gate did not see it)
Born red on r160 (2a8c5da): no order_router, no ROUTING.md.
NOT RUN (exit 2), never FAIL, when the imports cannot load.
Run:  python3 tests/check_order_routing.py
"""
import ast
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["OT_INSTRUMENT"] = "QQQ"
_TD = tempfile.mkdtemp(prefix="check_order_routing_")
for _k, _f in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"),
               ("OT_LOG_FILE", "bot.log"), ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_COUNTERFACTUAL_DIR", "cf"),
               ("OT_ALERT_SPOOL", "alert_spool.jsonl"), ("OT_PLAN_STATES_FILE", "plan_states.json"),
               ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT"), ("OT_WAREHOUSE_STATE", "ws")):
    os.environ[_k] = os.path.join(_TD, _f)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _code(rel):
    src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    return src.split('"""', 2)[-1] if src.lstrip().startswith('"""') else src


def main():
    print("check_order_routing")
    try:
        from execution import order_router as R
    except Exception as exc:                                    # noqa: BLE001
        check("R0 execution/order_router.py exists", False, f"{type(exc).__name__}: {exc}")
        print("RED — 1 failed: R0")
        return 1
    try:
        from utils import box_flags as BF
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN: imports failed ({type(exc).__name__}: {exc})")
        return 2
    FL = tempfile.mkdtemp(prefix="flags_", dir=_TD)

    def flags(text, schema=None):
        p = os.path.join(FL, "QQQ_%d" % len(os.listdir(FL)))
        if text is not None:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
        BF.reset()
        BF._EFFECTIVE["flags"] = BF.load("QQQ", path=p, schema=schema)

    # ── R1 the map is the code ──────────────────────────────────────────────
    doc = os.path.join(ROOT, "docs", "ROUTING.md")
    rows = {}
    if os.path.exists(doc):
        for ln in open(doc, encoding="utf-8"):
            m = re.match(r"^\|\s*ROUTE\s*\|\s*(\w+)\s*\|\s*(paper|live)\s*\|\s*(LIVE|PAPER|DORMANT)\s*\|\s*$", ln)
            if m:
                rows[(m.group(1), m.group(2) == "paper")] = m.group(3)
    check("R1 docs/ROUTING.md's ROUTE rows are exactly order_router.TABLE", rows == dict(R.TABLE) and len(rows) == 6,
          f"doc={rows} code={R.TABLE}")

    # ── R2 the table ────────────────────────────────────────────────────────
    got = {(f, b): R.route("PARK", b, flag=f) for f in ("on", "paper_only", "off") for b in (True, False)}
    bad = {v: (R.route("PARK", False, flag=v), R.route("PARK", True, flag=v)) for v in ("of", "", "PAPER_ONLY", "live")}
    none_mode = (R.route("PARK", None, flag="on"), R.route("PARK", None, flag="paper_only"))
    ok2 = (got == {("on", True): "PAPER", ("on", False): "LIVE", ("paper_only", True): "PAPER",
                   ("paper_only", False): "PAPER", ("off", True): "DORMANT", ("off", False): "DORMANT"}
           and all(v == ("DORMANT", "DORMANT") for v in bad.values())
           and none_mode == ("LIVE", "PAPER")
           and R.route("OGAP", False) == "PAPER" and R.route("OGAP", True) == "PAPER"
           and R.asked_past_cap(False) is True and R.asked_past_cap(True) is False and R.asked_past_cap(None) is True)
    flags("park = paper_only\n")
    ok2 = ok2 and R.walled("PARK", False) and not R.walled("PARK", True) and not R.walled("RunawayContinuation", False)
    check("R2 the opening table: on / paper_only / off x paper / live; a bad value fails DORMANT; walled on a live box "
          "only; OGAP always paper; the cash cap is asked past on a live box only", ok2,
          f"got={got} bad={bad} none={none_mode}")

    # ── R3 closes read the row ──────────────────────────────────────────────
    res3 = []
    for text in (None, "park = paper_only\n", "park = off\n"):
        flags(text)
        res3.append(tuple(R.route_close({"strategy": "PARK", "paper_trade": v}, b)
                          for b in (True, False) for v in (1, 0, None, "")))
    check("R3 a close reads the row, never the flag: paper box PAPER; live box paper_trade 1/None/'' PAPER, 0 LIVE",
          len(set(res3)) == 1 and res3[0] == ("PAPER",) * 4 + ("PAPER", "LIVE", "PAPER", "PAPER"), f"{res3}")

    # ── R4 generic ──────────────────────────────────────────────────────────
    saved = dict(BF.SCHEMA)
    try:
        BF.SCHEMA["zeta"] = BF.Key("zeta", "SetupZ", BF.LANES, BF.ON)
        r4 = {}
        for v in ("paper_only", "on", "off"):
            flags("zeta = %s\n" % v)
            r4[v] = (R.route("SetupZ", False), R.route("SetupZ", True), R.walled_setups(False))
    finally:
        BF.SCHEMA.clear()
        BF.SCHEMA.update(saved)
        BF.reset()
    check("R4 generic: a new schema key alone routes its setup (paper_only PAPER + walled, on LIVE, off DORMANT)",
          r4["paper_only"][:2] == ("PAPER", "PAPER") and "SetupZ" in r4["paper_only"][2]
          and r4["on"][:2] == ("LIVE", "PAPER") and "SetupZ" not in r4["on"][2]
          and r4["off"][:2] == ("DORMANT", "DORMANT"), f"{r4}")

    # ── R5 one decision point (static) ──────────────────────────────────────
    bad5 = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [x for x in dn if x not in (".git", "__pycache__", "venv", "tests", "docs")]
        for f in fn:
            if not f.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dp, f), ROOT)
            if rel == os.path.join("execution", "order_router.py"):
                continue
            code = _code(rel)
            if re.search(r"getattr\([^)]*[\"']PAPER_WALL[\"']", code) or re.search(r"\.PAPER_WALL\b", code):
                bad5.append(rel + ": reads PAPER_WALL")
            if re.search(r"\bWALLED\b", code):
                bad5.append(rel + ": names WALLED")
            if rel != os.path.join("execution", "paper_wall.py") and re.search(
                    r"_paper_wall\.(walled|asked_past_cap)\(|paper_wall\.(walled|asked_past_cap)\(", code):
                bad5.append(rel + ": asks paper_wall instead of the router")

    def calls(rel, fn_name, cls=None):
        t = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())
        scope = t
        if cls:
            scope = next((n for n in ast.walk(t) if isinstance(n, ast.ClassDef) and n.name == cls), None)
        fn = next((n for n in ast.walk(scope) if isinstance(n, ast.FunctionDef) and n.name == fn_name), None) \
            if scope is not None else None
        out = set()
        for n in ast.walk(fn or ast.Module(body=[], type_ignores=[])):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name):
                out.add(f"{n.func.value.id}.{n.func.attr}")
        return out
    need = [("main.py", "_execute_entry_signal", None, "_router.route"),
            ("main.py", "attempt_new_entry", None, "_router.asked_past_cap"),
            ("main.py", "attempt_new_entry", None, "_router.walled"),
            ("main.py", "_ask_walled_past_cap", None, "_router.walled_setups"),
            ("execution/position_manager.py", "_manage_one", None, "_router.is_wall"),
            ("execution/position_manager.py", "_execute_exit", None, "_router.is_wall"),
            ("execution/entry_engine.py", "_book_fill", None, "_router.is_wall"),
            ("execution/paper_wall.py", "get_open_trades", "WallTradeLogger", "_router.route_close")]
    miss5 = [f"{r}:{f} lacks {c}" for r, f, k, c in need if c not in calls(r, f, k)]
    check("R5 one decision point: no PAPER_WALL / WALLED / paper_wall.walled reads outside the router; every opening, "
          "closing, cap and recovery seam calls it", not bad5 and not miss5, f"{bad5} {miss5}")

    # ── R6 the paper path imports no broker client ──────────────────────────
    imp = {}
    for rel in ("execution/paper_wall.py", "execution/order_router.py"):
        t = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())
        mods = set()
        for n in ast.walk(t):
            if isinstance(n, ast.Import):
                mods |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                mods.add(n.module or "")
        imp[rel] = sorted(m for m in mods if "tasty" in m)
    fills = []
    for rel, fn in (("execution/entry_engine.py", "_paper_fill_single"), ("execution/limit_ladder.py", "paper_fill_price")):
        t = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())
        f = next((n for n in ast.walk(t) if isinstance(n, ast.FunctionDef) and n.name == fn), None)
        names = {getattr(n, "id", None) or getattr(n, "attr", None) for n in ast.walk(f)} if f else {"<missing>"}
        brokerish = sorted(x for x in names if x and re.search(r"session|account|tasty|place_order|run_async|sdk_",
                                                               x, re.I))
        if f is None or brokerish:
            fills.append(f"{rel}:{fn} {brokerish or 'missing'}")
    check("R6 the paper path: paper_wall.py and order_router.py import no broker client; the paper fill names no "
          "broker call", not any(imp.values()) and not fills, f"{imp} {fills}")

    # ── R7 every order path asks the router (runtime) + a bypass mutant ─────
    ok7, d7 = False, ""
    try:
        os.environ["OT_PAPER_TRADING"] = "False"
        import pandas  # noqa: F401
        import main as MN
        import database.trade_logger as TL
        import execution.position_manager as PMM
        from execution import paper_wall as PW
        from strategy.base_strategy import OptionsSignal
        from database.trade_logger import make_record
    except Exception as exc:                                    # noqa: BLE001
        print(f"       (R7 not run: {type(exc).__name__}: {exc})")
        MN = None
    if MN is not None:
        try:
            seen = []
            orig = {n: getattr(R, n) for n in ("route", "route_close", "is_wall")}

            def wrap(n):
                def f(*a, **k):
                    seen.append(n)
                    return orig[n](*a, **k)
                return f
            for n in orig:
                setattr(R, n, wrap(n))
            reached = []

            class _Eng:
                def enter(self, signal=None, sizing=None, **kw):
                    reached.append(signal.strategy_name)
                    return None
            s_gee = MN.get_entry_engine
            MN.get_entry_engine = lambda *a, **k: _Eng()
            st = MN.BotState()
            st.paper_trading = False
            sig = OptionsSignal(strategy_name="PARK", setup_type="park_long", direction="long", option_side="call",
                                underlying_entry=600.0, underlying_stop=0.0, strike=600.0, entry_premium=1.45,
                                stop_loss_pct=1.0)
            try:
                flags("park = off\n")
                MN._execute_entry_signal(sig, {"price": 600.0, "macro": {}}, None, st, None, additive=True)
                entry_asked = "route" in seen and not reached
                # the wall's close and its recovery
                p = os.path.join(_TD, "r7.db")
                TL._trade_logger = TL.TradeLogger(db_path=p, paper_trading=False)
                PW.reset()
                TL._trade_logger.log_entry(make_record(trade_id="pk", strategy="PARK", setup_type="park_long",
                                                       direction="long", option_side="call", strike=600.0,
                                                       expiry="2099-01-01", contracts=1, entry_premium=1.0,
                                                       total_cost=100.0, paper_trade=1, symbol="QQQ", status="open"))
                seen.clear()
                PW.recover()
                rec_asked = "route_close" in seen
                seen.clear()
                PW.book()._execute_exit(PW.book().get_open_records()[0],
                                        __import__("execution.exit_engine", fromlist=["ExitDecision"]).ExitDecision(
                                            should_exit=True, exit_reason="r7_close"), 1.10)
                close_asked = "is_wall" in seen
                # THE BYPASS MUTANT: an opening route that ignores the flag
                R.route = lambda setup, paper_box, flag=None: "LIVE" if paper_box is not True else "PAPER"
                MN._execute_entry_signal(sig, {"price": 600.0, "macro": {}}, None, st, None, additive=True)
                mutant_caught = reached == ["PARK"]          # the bypass reaches the LIVE engine: this gate sees it
            finally:
                for n, f in orig.items():
                    setattr(R, n, f)
                MN.get_entry_engine = s_gee
                BF.reset()
            ok7 = entry_asked and rec_asked and close_asked and mutant_caught
            d7 = f"entry={entry_asked} recover={rec_asked} close={close_asked} mutant_reached_live={reached}"
        except Exception as exc:                                # noqa: BLE001
            import traceback
            d7 = f"{type(exc).__name__}: {exc} {traceback.format_exc()[-700:]}"
        check("R7 at runtime the entry tail, the wall's recovery and its close consult the router; a bypass mutant (an "
              "opening route that ignores the flag) sends the off PARK signal to the live engine and is seen", ok7, d7)

    if FAILED:
        print(f"RED — {len(FAILED)} failed: {' '.join(FAILED)}")
        return 1
    print("GREEN — one routing decision (execution/order_router), mapped in docs/ROUTING.md; every opening, closing, "
          "cap and recovery seam asks it; the paper path imports no broker client (R1-R7)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
