#!/usr/bin/env python3
"""tests/check_tcs_shadow.py  v5.2
v5.2  2026-10-31  OTV5 r59 (ENT.1 land) — the fixture expiry is TODAY (ET), not the literal 2026-10-30: from 10-31 I4's restart
      settled the open shadow as an expired orphan at boot and went red on every tree (83abcc6 included), refusing r59's land.
v5.1  2026-10-30  OTV5 r57 (TCS.LOG1) — M1/M2 manage ticks run on a clock pinned to 13:00 ET (the lander ran M2 at 16:51 ET and the real 15:45 hard close pre-empted the breach on both books).
v5.0  2026-10-30  OTV5 r57 (TCS.LOG1) — new. A LOG-ONLY TCS IS A FULL SHADOW TRADE THAT NEVER ORDERS.
      The operator, 2026-10-30: "Can you reactivate TCS Monday as 'log only'? But do not trade it." then "Make sure TCS
      logs everything an executable trade logs."

Everything below drives the REAL code: main._execute_condor_leg (the credit door), main._shadow_manage /
main._shadow_eod / main._shadow_resume, execution/shadow_book, position_manager, the management plan and the exit
engine, against temp stores. The broker is replaced by functions that RAISE and count, so any order attempt is red.

  D1  OT_TCS_ACTIVE unset -> plan state log, config.TCS_MODE log, TREND_CREDIT_ACTIVE False; "log" -> log;
      "0"/"off" -> dormant/off; "1" -> active/trade; "junk" -> log, named
  D2  by default the TCS is ASKED (no retired reason; _safe_strategy calls it); with "0" it is not asked
  E1  LOG: a TCS signal through the credit door books ONE shadow row (shadow_trades.db), trade_id shadow-*, order_id
      SHADOW, at the paper fill (paper_fill_credit of the signal's credit), with the entry contract / snapshot written
  E2  the shadow row carries EVERY column and every in-memory record key a real TCS row carries (the real one built
      by the ACTIVE path, OT_TCS_ACTIVE=1, on the same inputs) plus exactly shadow / shadow_box_paper /
      shadow_plan_state; the entry fields agree value for value
  M1  _shadow_manage: the shadow is priced at the mark each tick (current_premium on the shadow row) and the
      management plan writes its check rows under "TrendCreditSpread[shadow]/manage" (none under the real label)
  M2  a breach of the bound closes it through the SAME exit code: the shadow and the real TCS, managed on identical
      inputs, close with the same reason prefix, exit price and P&L; the shadow row is closed with exit quote, MFE
      and P&L written
  M3  end of day: _shadow_eod closes an open shadow through flatten_all with a hard_close reason (paper cross)
  M4  a second shadow TCS is refused while one is open (admission's max_open_of_type=1 on the shadow book)
  I1  no broker call: every broker entry point raises and none was reached - on a PAPER box and on a LIVE box (the
      live order block is skipped: _post_credit_vertical never called)
  I2  no risk-manager effect (note_entry_risk / record_win / record_loss not called) and no Telegram (alerts silent)
  I3  nothing real: trades.db has no row, the real position manager holds nothing, has_open_position False,
      count_today("TrendCreditSpread") 0, realized_pnl_today 0, the real pairing gate allows both sides
  I4  restart: a fresh process resumes an open shadow from its store (shadow_book.resume_at_boot via _shadow_resume)
  O1  OT_TCS_ACTIVE=0: the TCS is not asked, and the shadow store is never created by a manage / EOD / boot pass
  A1  OT_TCS_ACTIVE=1: the real path is unchanged - a trades.db row, the real position manager holds it, order_id
      PAPER, note_entry_risk and the Telegram alert called, no shadow store
  S1  the warehouse pushes the shadow store under raw/shadow_trades with datatype shadow_trade, and raw/trades
      carries no shadow row

Born red on f095c4f at D1, D2, E1, E2, I1, I2, M1, M2, M3, M4, I3, I4, O1 and S1 (14 of 15; there is no shadow book,
and a LIVE box's TCS reached the order placer); A1 is the control.
Run:  python3 tests/check_tcs_shadow.py   (exit 0 green, 1 red)
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_tcs_shadow_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived_store.db"),
               ("OT_SHADOW_TRADES_DB", "shadow_trades.db"), ("OT_RESTING_DB", "resting.db"),
               ("OT_FEED_DB", "feed.db"), ("OT_PLAN_STATES_FILE", "plan_states.json"),
               ("OT_LOG_FILE", "bot.log"), ("OT_HEARTBEAT_FILE", "hb"),
               ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_SIGNAL_JOURNAL_DIR", "sj"),
               ("OT_RESTING_STOP_STATE", "rs.json"), ("OT_WAREHOUSE_STATE", "wh")):
    os.environ[_k] = os.path.join(_TD, _f)
os.environ["OT_PAPER_TRADING"] = "1"
os.environ["OT_RISK_USD"] = "2500"
os.environ.setdefault("OT_INSTRUMENT", "SYN")
os.environ.pop("OT_TCS_ACTIVE", None)

FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name.split()[0])


def guard(name, fn):
    try:
        ok = fn()
        check(name, bool(ok[0]) if isinstance(ok, tuple) else bool(ok),
              ok[1] if isinstance(ok, tuple) and len(ok) > 1 else "")
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"{type(exc).__name__}: {exc}")


# ── D1: the switch, read in a FRESH interpreter (config reads it at import) ──
_PROBE = ("import json,sys; sys.path.insert(0, sys.argv[1]); import config as c; from strategy import plan_state as S;"
          "print('@@'+json.dumps([S.state('TrendCreditSpread'), c.TCS_MODE, c.TCS_ENV_REFUSED, c.TREND_CREDIT_ACTIVE]))")


def _probe(v):
    env = {k: x for k, x in os.environ.items() if k != "OT_TCS_ACTIVE"}
    if v is not None:
        env["OT_TCS_ACTIVE"] = v
    r = subprocess.run([sys.executable, "-c", _PROBE, ROOT], env=env, capture_output=True, text=True, timeout=120)
    line = [x for x in r.stdout.splitlines() if x.startswith("@@")]
    return json.loads(line[0][2:]) if line else r.stderr[-200:]


def _d1():
    got = {v: _probe(v) for v in (None, "log", "0", "off", "1", "junk")}
    want = {None: ["log", "log", "", False], "log": ["log", "log", "", False], "0": ["dormant", "off", "", False],
            "off": ["dormant", "off", "", False], "1": ["active", "trade", "", True],
            "junk": ["log", "log", "junk", False]}
    return got == want, str(got)


guard("D1 OT_TCS_ACTIVE unset -> log; log -> log; 0/off -> dormant; 1 -> active; junk -> log, named", _d1)

# ── the fixture: one TCS put spread, its chain, the broker that raises ──────
import main                                                     # noqa: E402
import config as C                                              # noqa: E402
from strategy.base_strategy import OptionsSignal                # noqa: E402
import database.trade_logger as _tl                             # noqa: E402
import execution.position_manager as _pmm                       # noqa: E402
import execution.exit_engine as _xe                             # noqa: E402

try:
    from execution import shadow_book as SB
except Exception as _exc:                                       # noqa: BLE001  (born red on f095c4f)
    SB = None
    print(f"  (execution.shadow_book does not import: {_exc})")

BROKER = []


def _raise(name):
    def f(*a, **k):
        BROKER.append(name)
        raise RuntimeError(f"BROKER CALLED: {name}")
    return f


main._post_credit_vertical = _raise("main._post_credit_vertical")
for _mod in (main, _pmm):
    if hasattr(_mod, "get_client"):
        setattr(_mod, "get_client", _raise(f"{_mod.__name__}.get_client"))
for _nm in ("get_session", "get_account"):
    if hasattr(_xe, _nm):
        setattr(_xe, _nm, _raise(f"exit_engine.{_nm}"))
import data.tasty_client as _tc                                 # noqa: E402
for _nm in ("get_client", "get_session", "get_account"):
    if hasattr(_tc, _nm):
        setattr(_tc, _nm, _raise(f"tasty_client.{_nm}"))

CALLS = []


class _AM:
    def __getattr__(self, name):
        def f(*a, **k):
            CALLS.append(f"alert.{name}")
        return f


main.get_alert_manager = lambda: _AM()
_pmm.get_alert_manager = lambda: _AM()
_RM = main.get_risk_manager()
for _nm in ("note_entry_risk", "record_win", "record_loss"):
    _orig = getattr(_RM, _nm)

    def _wrap(*a, _o=_orig, _n=_nm, **k):
        CALLS.append(f"risk.{_n}")
        return _o(*a, **k)
    setattr(_RM, _nm, _wrap)
main.entries_open = lambda: True

from utils.time_utils import now_et as _now_et
EXP = _now_et().strftime("%Y-%m-%d")   # r59: today, so a restart never settles the fixture as expired


class _Con:
    def __init__(self, sym, strike, bid, ask, delta):
        self.symbol, self.strike, self.bid, self.ask = sym, float(strike), bid, ask
        self.mark = round((bid + ask) / 2, 4)
        self.delta, self.gamma, self.theta, self.vega, self.iv = delta, 0.02, -0.05, 0.03, 0.25
        self.expiry, self.option_type, self.streamer_symbol = EXP, "P", "." + sym


class _Chain:
    def __init__(self, short_bid, short_ask, long_bid, long_ask):
        self.puts = [_Con("SYN   261030P00099000", 99, short_bid, short_ask, -0.30),
                     _Con("SYN   261030P00094000", 94, long_bid, long_ask, -0.10)]
        self.calls = []
        self.spot_price, self.iv_rank, self.atm_iv = 101.0, 0.4, 0.25


def _df(close):
    import pandas as pd
    idx = pd.date_range(f"{EXP} 11:00", periods=30, freq="1min")
    return pd.DataFrame({"open": close, "high": close + 0.05, "low": close - 0.05, "close": close,
                         "volume": 1000}, index=idx)


def _sig(chain):
    s = OptionsSignal()
    s.strategy_name, s.setup_type, s.option_side = "TrendCreditSpread", "TCS 50-accept", "put"
    s.short_put_contract, s.long_put_contract = chain.puts[0], chain.puts[1]
    s.net_credit = round(chain.puts[0].mark - chain.puts[1].mark, 4)
    s.is_trend_credit = True
    s.underlying_stop, s.underlying_entry = 99.5, 101.0
    s.condor_trigger_source = "trend_orb"
    s.direction = "neutral"
    return s


def _ctx(chain, close=101.0):
    return {"chain": chain, "price": close, "df_1m": _df(close), "df_5m": None, "vol": None, "trend": None,
            "gap": {"gap_pct": 0.1}, "derived_engines": []}


def _fresh_stores(tag):
    d = os.path.join(_TD, tag)
    os.makedirs(d, exist_ok=True)
    os.environ["OT_SHADOW_TRADES_DB"] = os.path.join(d, "shadow_trades.db")
    _tl._trade_logger = _tl.TradeLogger(os.path.join(d, "trades.db"))
    _pmm._position_manager = None
    _xe._exit_engine = None
    if SB is not None:
        SB._BOOK = None
    return d


def _rows(path, table="trades"):
    if not os.path.exists(path):
        return []
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(f"SELECT * FROM {table}")]
    except sqlite3.OperationalError:
        return []
    finally:
        c.close()


def _cols(path):
    c = sqlite3.connect(path)
    try:
        return {r[1] for r in c.execute("PRAGMA table_info(trades)")}
    finally:
        c.close()


def _set_tcs(v):
    if v is None:
        os.environ.pop("OT_TCS_ACTIVE", None)
    else:
        os.environ["OT_TCS_ACTIVE"] = v
    C.TREND_CREDIT_ACTIVE = (v == "1")


# ── D2 ───────────────────────────────────────────────────────────────────────
def _d2():
    _set_tcs(None)
    asked = []
    main._set_admission(["TrendCreditSpread"]) if hasattr(main, "_set_admission") else None
    r0 = main._retired_reason("TrendCreditSpread")
    main._safe_strategy("TrendCreditSpread", lambda: asked.append(1))
    _set_tcs("0")
    r1 = main._retired_reason("TrendCreditSpread")
    main._safe_strategy("TrendCreditSpread", lambda: asked.append(2))
    _set_tcs(None)
    return (r0 == "" and asked == [1] and r1 != ""), f"retired={r0!r}/{r1!r} asked={asked}"


guard("D2 by default the TCS is asked (no retired reason); with OT_TCS_ACTIVE=0 it is not", _d2)

# ── E1 / E2 / I1-I3: one shadow (LOG) and one real (ACTIVE) on the same inputs ─
STATE = {}


def _book_shadow(paper=True, tag="shadow"):
    d = _fresh_stores(tag)
    _set_tcs(None)
    ch = _Chain(1.00, 1.10, 0.30, 0.34)
    st = main.BotState()
    st.paper_trading = paper
    main._execute_condor_leg(_sig(ch), st, _ctx(ch))
    return d, ch


def _e1():
    BROKER.clear(); CALLS.clear()
    d, ch = _book_shadow()
    STATE["shadow_dir"] = d
    rows = _rows(os.path.join(d, "shadow_trades.db"))
    from execution.limit_ladder import paper_fill_credit
    want = paper_fill_credit(_sig(ch).net_credit)
    STATE["shadow_row"] = rows[0] if rows else None
    STATE["shadow_rec"] = SB.get_shadow_book().pm.get_open_records()[0] if (SB and rows) else None
    STATE["e1_calls"] = (list(BROKER), list(CALLS))
    r = rows[0] if rows else {}
    ok = (len(rows) == 1 and str(r.get("trade_id", "")).startswith("shadow-") and r.get("order_id") == "SHADOW"
          and abs(float(r.get("entry_premium") or 0) - want) < 1e-9 and r.get("status") == "open"
          and r.get("strategy") == "TrendCreditSpread" and r.get("entry_bid") is not None
          and r.get("entry_snapshot") is not None and r.get("shadow") == 1 and r.get("shadow_plan_state") == "log")
    return ok, f"rows={len(rows)} {({k: r.get(k) for k in ('trade_id', 'order_id', 'entry_premium', 'entry_bid', 'shadow')})}"


guard("E1 LOG: the credit door books ONE shadow row (shadow-*, order_id SHADOW, the paper fill, entry contract)", _e1)


def _real():
    BROKER.clear(); CALLS.clear()
    d = _fresh_stores("real")
    _set_tcs("1")
    ch = _Chain(1.00, 1.10, 0.30, 0.34)
    st = main.BotState()
    st.paper_trading = True
    main._execute_condor_leg(_sig(ch), st, _ctx(ch))
    rows = _rows(os.path.join(d, "trades.db"))
    STATE["real_dir"] = d
    STATE["real_row"] = rows[0] if rows else None
    recs = _pmm.get_position_manager(True).get_open_records()
    STATE["real_rec"] = recs[0] if recs else None
    STATE["real_calls"] = (list(BROKER), list(CALLS))
    STATE["real_shadow_exists"] = os.path.exists(os.path.join(d, "shadow_trades.db"))
    _set_tcs(None)


try:
    _real()
except Exception as _exc:                                       # noqa: BLE001
    print(f"  (the active path raised: {_exc})")

SHADOW_COLS = {"shadow", "shadow_box_paper", "shadow_plan_state"}


def _e2():
    rr, sr = STATE.get("real_row"), STATE.get("shadow_row")
    if not rr or not sr:
        return False, "missing a row"
    rcols = _cols(os.path.join(STATE["real_dir"], "trades.db"))
    scols = _cols(os.path.join(STATE["shadow_dir"], "shadow_trades.db"))
    rk, sk = set(STATE["real_rec"]), set(STATE["shadow_rec"])
    filled_real = {k for k, v in rr.items() if v not in (None, "")}
    filled_sh = {k for k, v in sr.items() if v not in (None, "")}
    same = ("strategy", "setup_type", "option_side", "strike", "short_strike", "long_strike", "spread_width",
            "credit_received", "contracts", "entry_premium", "total_cost", "max_loss", "stop_premium",
            "target_premium", "underlying_stop", "underlying_entry", "short_symbol", "long_symbol", "option_symbol",
            "expiry", "is_condor_leg", "condor_trigger_source", "entry_delta", "entry_bid", "entry_ask", "entry_iv",
            "chain_iv_rank", "gap_pct", "setup_score", "lineage", "paper_trade", "status")
    diff = {k: (rr.get(k), sr.get(k)) for k in same if rr.get(k) != sr.get(k)}
    ok = (scols == rcols | SHADOW_COLS and sk == rk | SHADOW_COLS and filled_real - filled_sh == set() and not diff)
    return ok, (f"cols+{sorted(scols - rcols)} -{sorted(rcols - scols)}; keys+{sorted(sk - rk)} -{sorted(rk - sk)}; "
                f"filled only in real {sorted(filled_real - filled_sh)}; diff {diff}")


guard("E2 the shadow row carries every column and record key a real TCS carries (+3 shadow), entry values equal", _e2)


def _i1():
    b, _c = STATE.get("e1_calls", ([None], []))
    BROKER.clear()
    d, _ch = _book_shadow(paper=False, tag="live")
    rows = _rows(os.path.join(d, "shadow_trades.db"))
    live_ok = len(rows) == 1 and rows[0].get("shadow_box_paper") == 0 and rows[0].get("order_id") == "SHADOW"
    return (b == [] and BROKER == [] and live_ok and not _rows(os.path.join(d, "trades.db"))), \
        f"paper broker={b} live broker={BROKER} live rows={len(rows)}"


guard("I1 no broker call: paper box and LIVE box (the live order block is skipped)", _i1)


def _i2():
    b, c = STATE.get("e1_calls", ([None], [None]))
    rb, rc = STATE.get("real_calls", ([], []))
    return (c == [] and "risk.note_entry_risk" in rc and any(x.startswith("alert.") for x in rc)), \
        f"shadow calls={c}; real calls={rc}"


guard("I2 a shadow entry calls no risk manager and no alert (the real one calls both - control)", _i2)


# ── M1-M4: manage, breach, EOD, the second shadow ────────────────────────────
def _manage_both(chain, close):
    """One tick on identical inputs: the shadow book (via main._shadow_manage) and the real TCS (the real manager).
    v5.1: the tick runs on a clock pinned to 13:00 ET today, so a run after 15:45 ET is not pre-empted by the
    real 15:45 credit-vertical hard close (M2 expects the breach; both books closed hard_close on a 16:51 ET run)."""
    import utils.time_utils as _tu
    _real = _tu.datetime

    class _Pinned(_real):
        @classmethod
        def now(cls, tz=None):
            t = _real.now(_tu.ET).replace(hour=13, minute=0, second=0, microsecond=0)
            return t.astimezone(tz) if tz is not None else t.replace(tzinfo=None)
    ctx = _ctx(chain, close)
    _tu.datetime = _Pinned
    try:
        main._shadow_manage(ctx)
        pm = _pmm.get_position_manager(True)
        if pm.get_open_records():
            pm.manage_open_position(chain=chain, df_1m=ctx["df_1m"], df_5m=None, vol_state=None, trend=None)
    finally:
        _tu.datetime = _real


def _plan_rows():
    p = os.environ["OT_DERIVED_DB"]
    out = {}
    for r in _rows(p, "plan_check"):
        out.setdefault(r["strategy"], 0)
        out[r["strategy"]] += 1
    return out


def _setup_pair():
    """A shadow and a real TCS open side by side (separate stores, same inputs)."""
    BROKER.clear(); CALLS.clear()
    d = _fresh_stores("pair")
    ch = _Chain(1.00, 1.10, 0.30, 0.34)
    st = main.BotState(); st.paper_trading = True
    _set_tcs(None)
    main._execute_condor_leg(_sig(ch), st, _ctx(ch))           # shadow
    _set_tcs("1")
    main._execute_condor_leg(_sig(ch), st, _ctx(ch))           # real
    _set_tcs(None)
    return d


def _m1():
    d = _setup_pair()
    STATE["pair"] = d
    before = _plan_rows()
    ch2 = _Chain(0.80, 0.90, 0.25, 0.29)                       # value fell: the credit is winning
    _manage_both(ch2, 100.6)
    sr = _rows(os.path.join(d, "shadow_trades.db"))[0]
    after = _plan_rows()
    sh_lbl = "TrendCreditSpread[shadow]/manage"
    n_sh = after.get(sh_lbl, 0) - before.get(sh_lbl, 0)
    want = round(ch2.puts[0].mark - ch2.puts[1].mark, 4)
    return (abs(float(sr.get("current_premium") or 0) - want) < 1e-9 and n_sh > 0
            and sr.get("max_premium_seen") is not None), \
        f"current={sr.get('current_premium')} want={want} rows={after}"


guard("M1 each tick the shadow is priced at the mark and writes TrendCreditSpread[shadow]/manage check rows", _m1)


def _m2():
    d = STATE["pair"]
    ch3 = _Chain(1.60, 1.70, 0.50, 0.54)                       # through the bound: 99.2 < 99.5
    _manage_both(ch3, 99.2)
    sr = _rows(os.path.join(d, "shadow_trades.db"))[0]
    rr = _rows(os.path.join(d, "trades.db"))[0]
    ok = (sr.get("status") == "closed" and rr.get("status") == "closed"
          and str(sr.get("exit_reason", "")).startswith("breach")
          and str(sr.get("exit_reason", "")).split(" pnl")[0] == str(rr.get("exit_reason", "")).split(" pnl")[0]
          and abs(float(sr["exit_premium"]) - float(rr["exit_premium"])) < 1e-9
          and abs(float(sr["pnl_usd"]) - float(rr["pnl_usd"])) < 1e-9
          and sr.get("exit_bid") is not None and sr.get("mfe_premium") is not None)
    STATE["m2"] = (sr, rr)
    return ok, (f"shadow {sr.get('status')} {sr.get('exit_reason')} {sr.get('exit_premium')} {sr.get('pnl_usd')} | "
                f"real {rr.get('status')} {rr.get('exit_reason')} {rr.get('exit_premium')} {rr.get('pnl_usd')}")


guard("M2 a breach closes the shadow through the same exit code: same reason, exit price and P&L as the real TCS", _m2)


def _m3():
    import utils.time_utils as _tu
    import execution.limit_ladder as _ll
    d, ch = _book_shadow(tag="eod")
    saved = (_tu.eod_close_due, _ll.hard_close_order_mode, main.get_chain_fetcher, main.get_cache,
             _xe.hard_close_order_mode)

    class _F:
        def fetch_chain(self, *a, **k):
            return ch

    class _K:
        def get_price(self):
            return 101.0
    try:
        _tu.eod_close_due = lambda *a, **k: True
        _ll.hard_close_order_mode = lambda *a, **k: "market"
        _xe.hard_close_order_mode = lambda *a, **k: "market"      # the 15:55 cross (EOD.1)
        main.get_chain_fetcher = lambda: _F()
        main.get_cache = lambda: _K()
        main._shadow_eod(main.BotState(), _ctx(ch))
    finally:
        (_tu.eod_close_due, _ll.hard_close_order_mode, main.get_chain_fetcher, main.get_cache,
         _xe.hard_close_order_mode) = saved
    sr = _rows(os.path.join(d, "shadow_trades.db"))[0]
    return (sr.get("status") == "closed" and "hard_close" in str(sr.get("exit_reason")) and BROKER == []), \
        f"{sr.get('status')} {sr.get('exit_reason')} broker={BROKER}"


guard("M3 end of day: _shadow_eod closes the shadow through flatten_all with a hard_close reason (no broker)", _m3)


def _m4():
    d, ch = _book_shadow(tag="second")
    st = main.BotState(); st.paper_trading = True
    s2 = _sig(ch)
    main._execute_condor_leg(s2, st, _ctx(ch))
    return len(_rows(os.path.join(d, "shadow_trades.db"))) == 1, "a second shadow was booked"


guard("M4 a second shadow TCS is refused while one is open", _m4)


def _i3():
    d = STATE["shadow_dir"]
    tl = _tl.TradeLogger(os.path.join(d, "trades.db"))
    _tl._trade_logger = tl
    _pmm._position_manager = None
    pm = _pmm.get_position_manager(True)
    open_sh = SB.ShadowBook(os.path.join(d, "shadow_trades.db"))
    sh_open = open_sh.has_open()
    both = main._can_open_credit_spread("put") and main._can_open_credit_spread("call")
    return (sh_open and not _rows(os.path.join(d, "trades.db")) and not pm.has_open_position()
            and tl.count_today("TrendCreditSpread") == 0 and float(tl.realized_pnl_today() or 0) == 0.0
            and both and "TrendCreditSpread" not in pm.open_by_strategy()), \
        f"shadow open={sh_open} real rows={len(_rows(os.path.join(d, 'trades.db')))} pairing={both}"


guard("I3 nothing real: no trades.db row, no real position, counts / P&L zero, the pairing gate allows both sides", _i3)


def _i4():
    d = STATE["shadow_dir"]
    os.environ["OT_SHADOW_TRADES_DB"] = os.path.join(d, "shadow_trades.db")
    SB._BOOK = None                                             # a fresh process
    main._shadow_resume()
    b = SB.peek_shadow_book()
    recs = b.pm.get_open_records() if b else []
    return (len(recs) == 1 and str(recs[0]["trade_id"]).startswith("shadow-")), f"resumed={len(recs)}"


guard("I4 restart: a fresh process resumes the open shadow from its store", _i4)


def _o1():
    d = _fresh_stores("dormant")
    _set_tcs("0")
    asked = []
    main._safe_strategy("TrendCreditSpread", lambda: asked.append(1))
    ch = _Chain(1.00, 1.10, 0.30, 0.34)
    main._shadow_manage(_ctx(ch))
    main._shadow_resume()
    main._shadow_eod(main.BotState(), _ctx(ch))
    _set_tcs(None)
    return (asked == [] and not os.path.exists(os.path.join(d, "shadow_trades.db"))
            and not _rows(os.path.join(d, "trades.db"))), f"asked={asked}"


guard("O1 OT_TCS_ACTIVE=0: not asked; no shadow store is created by the manage / boot / EOD passes", _o1)


def _a1():
    rr, rec = STATE.get("real_row"), STATE.get("real_rec")
    rb, rc = STATE.get("real_calls", ([None], []))
    return (rr is not None and rec is not None and rr.get("order_id") == "PAPER"
            and not str(rr.get("trade_id")).startswith("shadow-") and rb == []
            and "risk.note_entry_risk" in rc and not STATE.get("real_shadow_exists", True)), \
        f"row={bool(rr)} rec={bool(rec)} calls={rc} shadow store={STATE.get('real_shadow_exists')}"


guard("A1 OT_TCS_ACTIVE=1: the real path is unchanged (trades.db row, real manager, PAPER, risk + alert, no shadow)", _a1)


def _s1():
    import warehouse.s3_push as sp
    d = STATE["pair"]
    puts = []

    def _pv(s3, bucket, key, body, counters=None):
        puts.append((key, json.loads(body)))
        return True
    saved = sp.put_and_verify
    sp.put_and_verify = _pv
    try:
        sp.push_trades(None, "b", os.path.join(d, "shadow_trades.db"), {}, None, ns="shadow_trades",
                       datatype="shadow_trade", src_file="shadow_trades.db")
        sp.push_trades(None, "b", os.path.join(d, "trades.db"), {}, None)
    finally:
        sp.put_and_verify = saved
    sh = [p for p in puts if "/shadow_trades/" in p[0]]
    tr = [p for p in puts if "/trades/" in p[0] and "/shadow_trades/" not in p[0]]
    src = open(os.path.join(ROOT, "warehouse", "s3_push.py")).read()
    return (len(sh) == 1 and sh[0][1]["datatype"] == "shadow_trade"
            and str(sh[0][1]["trade_id"]).startswith("shadow-")
            and all(not str(p[1]["trade_id"]).startswith("shadow-") for p in tr) and len(tr) == 1
            and '("shadow_trades", lambda: push_trades(s3, BUCKET, SHADOW_TRADES_DB' in src), \
        f"shadow puts={[p[0] for p in sh]} trades puts={[p[0] for p in tr]}"


guard("S1 the warehouse pushes shadows under raw/shadow_trades (datatype shadow_trade); raw/trades has none", _s1)

print()
shutil.rmtree(_TD, ignore_errors=True)
if FAILED:
    print(f"FAILED {len(FAILED)} of {len(RAN)}: {', '.join(FAILED)}")
    sys.exit(1)
print(f"PASS - check_tcs_shadow ({len(RAN)} checks)")
