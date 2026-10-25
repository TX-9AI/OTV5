#!/usr/bin/env python3
"""tests/check_commitment.py — v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
WE ENTER ON COMMITMENT (COMMIT.1 / COMMIT.2 / COMMIT.3, OTV4TEST r272).

v1.0  2026-10-12  OTV4TEST r272 — the operator, 2026-10-12 10:34 ET: "A good place to get out cannot be a good place
      to get in and vice versa"; 10:35 ET: "we enter on commitment and we exit on abandonment"; 11:35 ET: "Yes, do it"
      (the state recorded, the ABANDONED gate trading on paper, the caution size logged).

THE STATE is driven on a SCRATCH feed store whose bars are built here (a steady advance: long COMMITTED, short
ABANDONED), and the HYSTERESIS through the real snapshot(). THE GATE is driven through the REAL
main._execute_entry_signal with a spy on entry_engine.enter - refused means the order was never reached (WA 21).
Every case's fixture fires when the gate has no reason to refuse it (C0-style controls), so a refusal is the gate.

  K0  analysis.commitment exists (RED on the base: no module)
  K1  steady advance: long COMMITTED, short ABANDONED, series QQQ_EXT named
  K2  hysteresis: raw ABANDONED after raw COMMITTED in the SAME session reads NEUTRAL; across sessions it does not
  K3  no <SYM>_EXT 1m (SPX): the RTH series is used and named
  K4  unreadable store -> {"err": ...}, never raises
  K5  observe(): one row per side per NEW closed bar - a second call on the same bar writes nothing
  G1  ABANDONED + trade + paper -> NOT placed, row BLOCKED with the would-be order (contracts)
  G2  ABANDONED + log -> placed, row would_block
  G3  off -> placed, no row
  G4  LIVE box + trade -> placed (refused), row effective=log
  G5  COMMITTED -> placed          G6  NEUTRAL -> placed
  G7  unreadable (state None / err) -> placed, row names why
  G7b no commitment key on ctx (not a tick, e.g. another checker) -> placed, NO row
  G8  a non-directional (GEXPinButterfly) with its side ABANDONED -> placed, no row
  G9  a malformed state never raises -> placed
  S1  config: unset -> trade; log/off kept; a bogus value -> log and named
  S2  config: OT_CAUTION_SIZE unset -> log; trade REFUSED (-> log, named)
  C1  caution after the session's first directional LOSS: NEUTRAL entry logs factor 0.5, COMMITTED 1.0; the ORDER'S
      contracts unchanged
  C2  caution with no loss yet: no row
  C3  (b) SCALING-OFF is the SAME size_for call with scaled=False (a ramp 7 / flat 4 fixture): row 4, order 7
  C3b a strategy with no scaling switch: (b) = actual, no flat call
  C3c the REAL RiskManager: (b) equals its own size_for(scaled=False) answer
  B1  the Service mode line names commit_gate and caution
  W1  main's loop assigns ctx["commitment"] from analysis.commitment.observe (an assignment, not a mention - WA 20)
NOT RUN (exit 2), never FAIL, when the bot's imports cannot load (e.g. a bare python3, no pytz/pandas).
Run:  OT_INSTRUMENT=QQQ python3 tests/check_commitment.py
"""
import ast
import datetime as _dt
import json
import os
import sqlite3
import subprocess
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_tmp = tempfile.mkdtemp(prefix="check_commitment_")
os.environ["OT_COUNTERFACTUAL_DIR"] = os.path.join(_tmp, "cf")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_tmp, "trades.db"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_tmp, "bot.log"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_tmp, "derived_store.db"))
os.environ.setdefault("OT_RESTING_DB", os.path.join(_tmp, "resting_orders.db"))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_tmp, "signal_journal"))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def guard(name, fn, detail=""):
    try:
        ok = fn()
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"{type(exc).__name__}: {exc}")
        return
    check(name, bool(ok), detail() if callable(detail) else detail)


try:
    import main                                                 # noqa: E402,F401
    from strategy.base_strategy import OptionsSignal            # noqa: E402,F401
except Exception as exc:                                        # noqa: BLE001
    print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
    sys.exit(2)
try:
    from analysis import commitment as cm                      # noqa: E402
except Exception as exc:                                        # noqa: BLE001
    check("K0 analysis.commitment exists", False, f"{type(exc).__name__}: {exc}")
    print(f"\n  RED — {len(FAILED)} of {len(RAN)} failed: " + ", ".join(FAILED))
    sys.exit(1)
check("K0 analysis.commitment exists", True)

# ── a scratch feed store: 2026-10-07, EXT 04:00-10:30 ET, RTH 09:30-10:29, a steady advance ──
from zoneinfo import ZoneInfo                                    # noqa: E402
_ET = ZoneInfo("America/New_York")


def _ms(h, m, day=_dt.date(2026, 10, 7)):
    return int(_dt.datetime(day.year, day.month, day.day, h, m, tzinfo=_ET).timestamp() * 1000)


def _store(path, sym="QQQ", ext=True):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE candles (symbol TEXT, interval TEXT, ts_epoch_ms INTEGER, open REAL, high REAL, "
              "low REAL, close REAL, volume REAL, PRIMARY KEY (symbol, interval, ts_epoch_ms))")
    k = 0
    t = _ms(4, 0)
    while t < _ms(10, 30):
        px = 100 + 0.01 * k
        if ext:
            c.execute("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", (sym + "_EXT", "1m", t, px, px, px - .02, px, 1))
        hm = _dt.datetime.fromtimestamp(t / 1000, _ET)
        if (hm.hour, hm.minute) >= (9, 30) or not ext:
            c.execute("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", (sym, "1m", t, px - .01, px, px - .05, px, 1))
        t += 60000
        k += 1
    c.commit()
    c.close()


DB = os.path.join(_tmp, "feed.db")
_store(DB)
T_DEC = _ms(10, 30) / 1000.0
snap = cm.snapshot(T_DEC, symbol="QQQ", db_path=DB)
guard("K1 steady advance: long COMMITTED, short ABANDONED, series QQQ_EXT",
      lambda: snap.get("long", {}).get("state") == "COMMITTED" and snap.get("short", {}).get("state") == "ABANDONED"
      and snap.get("series") == "QQQ_EXT", lambda: json.dumps({k: snap.get(k) for k in ("series", "err")}))


def _hyst(same_session):
    real = cm._raw
    seq = iter([{"raw": "ABANDONED"}, {"raw": "COMMITTED"}] * 2)
    cm._raw = lambda *a, **k: dict(next(seq))
    real_d = cm._et_date
    if not same_session:
        calls = iter([_dt.date(2026, 10, 7), _dt.date(2026, 10, 6)])
        cm._et_date = lambda ts: next(calls)
    try:
        s = cm.snapshot(T_DEC, symbol="QQQ", db_path=DB)
    finally:
        cm._raw, cm._et_date = real, real_d
    return s.get("long", {}).get("state")


guard("K2 hysteresis: ABANDONED after COMMITTED, same session -> NEUTRAL; new session -> ABANDONED",
      lambda: _hyst(True) == "NEUTRAL" and _hyst(False) == "ABANDONED",
      lambda: f"same={_hyst(True)} cross={_hyst(False)}")
DB2 = os.path.join(_tmp, "feed_spx.db")
_store(DB2, sym="SPX", ext=False)
guard("K3 no SPX_EXT 1m: the RTH series SPX is used and named",
      lambda: cm.snapshot(T_DEC, symbol="SPX", db_path=DB2).get("series") == "SPX")
guard("K4 unreadable store -> err, never raises",
      lambda: "err" in cm.snapshot(T_DEC, symbol="QQQ", db_path=os.path.join(_tmp, "nope.db")))


def _rows(name):
    p = os.path.join(os.environ["OT_COUNTERFACTUAL_DIR"], name)
    if not os.path.exists(p):
        return []
    return [json.loads(x) for x in open(p) if x.strip()]


def _observe_twice():
    os.environ["OT_FEED_DB"] = DB
    real = cm._symbol
    cm._symbol = lambda: "QQQ"
    try:
        n0 = len(_rows("commitment.jsonl"))
        cm.observe(T_DEC)
        n1 = len(_rows("commitment.jsonl"))
        cm.observe(T_DEC + 10)
        n2 = len(_rows("commitment.jsonl"))
    finally:
        cm._symbol = real
        os.environ.pop("OT_FEED_DB", None)
    return (n1 - n0, n2 - n1) == (2, 0)


guard("K5 observe(): 2 rows on a new bar, none on the same bar", _observe_twice)

# ── THE GATE, through the REAL funnel ──
import main                                                     # noqa: E402
from strategy.base_strategy import OptionsSignal                # noqa: E402


class _Sizing:
    allowed = True
    contracts = 7
    total_cost = 700.0
    reject_reason = None


class _Risk:
    def size_for(self, *a, **kw):
        return _Sizing()


class _Spy:
    def __init__(self):
        self.entered = []

    def enter(self, signal=None, sizing=None, **kw):
        self.entered.append((getattr(signal, "strategy_name", "?"), getattr(sizing, "contracts", None)))
        return None


class _Macro:
    butterfly_half_size = False


class _State:
    paper_trading = True


def _sig(name="Breakout", direction="short"):
    return OptionsSignal(strategy_name=name, setup_type="fixture", direction=direction,
                         option_side="call" if direction == "long" else "put",
                         underlying_entry=100.0, underlying_stop=(101.0 if direction == "short" else 99.0),
                         strike=100.0, entry_premium=1.25)


def _state(long_s, short_s):
    return {"bar_ts": 1, "series": "QQQ_EXT", "long": {"state": long_s}, "short": {"state": short_s}}


def _fire(signal, commitment, *, mode="trade", paper=True, has_key=True, risk=None):
    spy = _Spy()
    saved = (main.get_risk_manager, main.get_entry_engine, main.COMMIT_GATE_MODE, main.PAPER_TRADING)
    _r = risk if risk is not None else _Risk()
    main.get_risk_manager = lambda *a, **kw: _r
    main.get_entry_engine = lambda *a, **kw: spy
    main.COMMIT_GATE_MODE, main.PAPER_TRADING = mode, paper
    ctx = {"price": 100.0, "macro": _Macro()}
    if has_key:
        ctx["commitment"] = commitment
    try:
        main._execute_entry_signal(signal, ctx, None, _State(), None, additive=True)
    finally:
        main.get_risk_manager, main.get_entry_engine, main.COMMIT_GATE_MODE, main.PAPER_TRADING = saved
    return spy.entered


def _last_gate():
    r = _rows("commit_gate.jsonl")
    return r[-1] if r else {}


def g1():
    n0 = len(_rows("commit_gate.jsonl"))
    placed = _fire(_sig(), _state("COMMITTED", "ABANDONED"))
    r = _last_gate()
    return (not placed and len(_rows("commit_gate.jsonl")) == n0 + 1 and r.get("decision") == "BLOCKED"
            and r.get("order", {}).get("contracts") == 7)


guard("G1 ABANDONED + trade + paper -> NOT placed, row BLOCKED with contracts", g1, lambda: json.dumps(_last_gate()))
guard("G2 ABANDONED + log -> placed, row would_block",
      lambda: bool(_fire(_sig(), _state("COMMITTED", "ABANDONED"), mode="log"))
      and _last_gate().get("decision") == "would_block")


def g3():
    n0 = len(_rows("commit_gate.jsonl"))
    return bool(_fire(_sig(), _state("COMMITTED", "ABANDONED"), mode="off")) and len(_rows("commit_gate.jsonl")) == n0


guard("G3 off -> placed, no row", g3)
guard("G4 LIVE + trade -> placed, row effective=log",
      lambda: bool(_fire(_sig(), _state("COMMITTED", "ABANDONED"), paper=False))
      and _last_gate().get("effective") == "log")
guard("G5 COMMITTED -> placed", lambda: bool(_fire(_sig(), _state("ABANDONED", "COMMITTED"))))
guard("G6 NEUTRAL -> placed", lambda: bool(_fire(_sig(), _state("ABANDONED", "NEUTRAL"))))
guard("G7 unreadable -> placed, row names why",
      lambda: bool(_fire(_sig(), {"err": "no bars"})) and _last_gate().get("why_unread") == "no bars"
      and bool(_fire(_sig(), None)) and bool(_last_gate().get("why_unread")))


def g7b():
    n0 = len(_rows("commit_gate.jsonl"))
    return bool(_fire(_sig(), None, has_key=False)) and len(_rows("commit_gate.jsonl")) == n0


guard("G7b no tick state on ctx (a caller outside the loop) -> placed, NO row", g7b)


def g8():
    n0 = len(_rows("commit_gate.jsonl"))
    placed = _fire(_sig(name="GEXPinButterfly"), _state("ABANDONED", "ABANDONED"))
    return bool(placed) and len(_rows("commit_gate.jsonl")) == n0


guard("G8 a non-directional with its side ABANDONED -> placed, no row", g8)
guard("G9 a malformed state never raises -> placed",
      lambda: bool(_fire(_sig(), {"short": "x", "long": 3})) and bool(_fire(_sig(), "garbage")))


def _cfg(env):
    e = {k: v for k, v in os.environ.items() if not k.startswith(("OT_COMMIT_GATE", "OT_CAUTION_SIZE"))}
    e.update(env)
    out = subprocess.run([sys.executable, "-c", "import config as c; print(c.COMMIT_GATE_MODE, "
                          "repr(c.COMMIT_GATE_ENV_REFUSED), c.CAUTION_SIZE_MODE, repr(c.CAUTION_SIZE_ENV_REFUSED))"],
                         cwd=_root, env=e, capture_output=True, text=True, timeout=60)
    return out.stdout.strip().splitlines()[-1] if out.stdout.strip() else out.stderr[-200:]


guard("S1 OT_COMMIT_GATE: unset -> trade; log kept; off kept; bogus -> log, named",
      lambda: (_cfg({}).split()[0] == "trade" and _cfg({"OT_COMMIT_GATE": "log"}).split()[0] == "log"
               and _cfg({"OT_COMMIT_GATE": "off"}).split()[0] == "off"
               and _cfg({"OT_COMMIT_GATE": "bogus"}).split()[:2] == ["log", "'bogus'"]),
      lambda: _cfg({"OT_COMMIT_GATE": "bogus"}))
guard("S2 OT_CAUTION_SIZE: unset -> log; trade REFUSED -> log, named",
      lambda: (_cfg({}).split()[2] == "log"
               and _cfg({"OT_CAUTION_SIZE": "trade"}).split()[2:] == ["log", "'trade'"]),
      lambda: _cfg({"OT_CAUTION_SIZE": "trade"}))


# ── caution: a scratch trades.db with today's first directional trade closed at a loss ──
def _trades_db(loss):
    import config                                               # noqa: PLC0415
    p = config.DB_PATH
    if not os.path.realpath(p).startswith((os.path.realpath(tempfile.gettempdir()) + os.sep, "/tmp/")):
        raise RuntimeError(f"refusing to write a fixture trades.db at {p} (not a temp path)")
    if os.path.exists(p):
        os.remove(p)
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE trades (trade_id TEXT PRIMARY KEY, strategy TEXT, status TEXT, relaxed_entry INTEGER, "
              "entry_time TEXT, exit_time TEXT, pnl_usd REAL)")
    now = _dt.datetime.now(_dt.timezone.utc)
    c.execute("INSERT INTO trades VALUES ('x1','Breakout','closed',0,?,?,?)",
              ((now - _dt.timedelta(minutes=20)).isoformat(), (now - _dt.timedelta(minutes=10)).isoformat(),
               -250.0 if loss else 120.0))
    c.commit()
    c.close()


def _caution(loss, short_state, name="Breakout", risk=None):
    _trades_db(loss)
    n0 = len(_rows("caution_size.jsonl"))
    placed = _fire(_sig(name=name), _state("COMMITTED", short_state), mode="log", risk=risk)
    rows = _rows("caution_size.jsonl")[n0:]
    return placed, rows


def c1():
    p1, r1 = _caution(True, "NEUTRAL")
    p2, r2 = _caution(True, "COMMITTED")
    return (p1 and p2 and p1[0][1] == 7 and p2[0][1] == 7 and len(r1) == 1 and len(r2) == 1
            and r1[0]["factor"] == 0.5 and r1[0]["contracts_s2"] == 3 and r2[0]["factor"] == 1.0)


guard("C1 after a first loss: NEUTRAL logs 0.5x, COMMITTED 1.0x; the order's contracts unchanged", c1)
guard("C2 no loss yet: no caution row", lambda: _caution(False, "NEUTRAL")[1] == [])


class _ScaledRisk:
    """size_for answers 7 on the ramp and 4 flat, and records every call - so (b) can only be 4 if it came from the
    SAME call with scaled=False."""
    def __init__(self):
        self.calls = []

    def size_for(self, structure, **kw):
        self.calls.append((structure, dict(kw)))
        r = _Sizing()
        r.contracts = 7 if kw.get("scaled", True) else 4
        return r


def c3():
    rk = _ScaledRisk()
    placed, rows = _caution(True, "NEUTRAL", risk=rk)
    on = [c for c in rk.calls if c[1].get("scaled", True)]
    off = [c for c in rk.calls if not c[1].get("scaled", True)]
    same = bool(on and off) and on[0][0] == off[0][0] and dict(on[0][1], scaled=None) == dict(off[0][1], scaled=None)
    return (placed and placed[0][1] == 7 and len(rows) == 1 and rows[0]["contracts_scaling_off"] == 4
            and rows[0]["scaling_off_source"].startswith("size_for(scaled=False)") and rows[0]["contracts_s2"] == 3
            and same)


guard("C3 Breakout: (b) is the SAME size_for call with scaled=False (7 -> 4), the order keeps 7", c3)


def c3b():
    rk = _ScaledRisk()
    placed, rows = _caution(True, "NEUTRAL", name="RunawayContinuation", risk=rk)
    return (len(rows) == 1 and rows[0]["contracts_scaling_off"] == rows[0]["contracts_actual"] == 7
            and rows[0]["scaling_off_source"].startswith("actual") and all(c[1].get("scaled", True) for c in rk.calls))


guard("C3b Runaway (no scaling switch): (b) = actual, no flat call made", c3b)


def c3c():
    from risk.risk_manager import RiskManager                   # noqa: PLC0415
    seen = []

    class _Rec(RiskManager):
        def size_for(self, structure, **kw):
            r = super().size_for(structure, **kw)
            seen.append((dict(kw), r))
            return r
    placed, rows = _caution(True, "NEUTRAL", risk=_Rec())
    off = [r for kw, r in seen if kw.get("scaled") is False]
    want = (off[0].contracts if off[0].allowed else 0) if off else None
    return len(rows) == 1 and off and rows[0]["contracts_scaling_off"] == want


guard("C3c the REAL RiskManager: (b) equals its own size_for(scaled=False) answer", c3c)
guard("B1 the Service mode line names commit_gate and caution",
      lambda: " · commit_gate=" in main._banner_dials() and " · caution=" in main._banner_dials())


def w1():
    tree = ast.parse(open(os.path.join(_root, "main.py"), encoding="utf-8").read())
    for n in ast.walk(tree):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Subscript)
                and isinstance(n.targets[0].value, ast.Name) and n.targets[0].value.id == "ctx"
                and isinstance(n.targets[0].slice, ast.Constant) and n.targets[0].slice.value == "commitment"
                and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute)
                and n.value.func.attr == "observe"):
            return True
    return False


guard("W1 main assigns ctx['commitment'] from commitment.observe", w1)

print()
if FAILED:
    print(f"  RED — {len(FAILED)} of {len(RAN)} failed: " + ", ".join(FAILED))
    sys.exit(1)
print(f"  GREEN — {len(RAN)} checks")
