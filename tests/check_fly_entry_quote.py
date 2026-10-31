#!/usr/bin/env python3
"""
tests/check_fly_entry_quote.py  v5.1
v5.1  2026-10-31  OTV5 r67 (PARC.4) — F7's credit vertical is a SweepCreditSpread lone vertical
      (structure CONDOR_LEG, is_condor_leg 0), not a PARC row: PARC is removed. The operator, 2026-10-31: "On PARC, no. It was an idea. It failed. It's done." and "Yes" to removing its code.
      The property (a credit vertical writes its short leg's values) is unchanged.
v5.0  2026-10-29  OTV5 r53 (FLY.3) — A BUTTERFLY'S ENTRY QUOTE AND GREEKS ARE THE FLY'S, NOT ITS BODY LEG'S.
      main._capture_entry_contract matched record["option_symbol"], which on a fly is the CENTER leg, so every fly row
      carried the body's quote and greeks: NVDA 2026-10-28 b495e4a9 (GEXPinButterfly, calls 217.5/220/222.5) booked
      entry_premium 0.58 beside entry_bid/ask 0.21/0.22 and entry_delta 0.164 - the 220 call's. The warehouse's
      quote_series at that entry has the legs at 0.96/0.98, 0.21/0.22, 0.04/0.05: the fly is 0.56/0.61, which brackets
      the 0.58 it was booked at. Same on TSLA 10-28 (0.70 vs 0.10/0.11), AMZN 10-28, AMD and TSLA 10-26.
      Driven through the REAL main._capture_entry_contract into a REAL TradeLogger (a scratch trades.db); the chain is
      a fake carrying the NVDA legs (quotes as the warehouse had them; greeks NVDA-like).

  F1  the NVDA fly row gets the FLY's composite: entry_bid 0.56 = 0.96 + 0.04 - 2 x 0.22, entry_ask 0.61 =
      0.98 + 0.05 - 2 x 0.21 (the position_manager exit composite), and they bracket entry_premium 0.58
  F2  net greeks per fly: delta/gamma/theta = lower + upper - 2 x center; entry_iv = the BODY's IV; chain_iv_rank kept
  F3  it is NOT the center leg's quote any more (0.21/0.22, delta 0.164 - the 2026-10-28 row)
  F4  legs found by strike on the fly's side when the leg symbols are absent: the same values
  F5  a leg missing from the chain writes NOTHING (the columns stay NULL - no fall back to the center leg), returns
      False, and warns once per reason ("fly-leg-not-found:upper")
  F6  UNCHANGED: a single-leg trade (PARK-like long call) still writes its own contract's quote and greeks
  F7  UNCHANGED: a credit-vertical row (option_symbol = its short leg) still writes the short leg's values (FLY.3
      does not touch verticals; reported, not fixed)

Born red on 9e2dc5f at F1b-F1d, F2a-F2c, F3, F4 and F5a-F5c (F1a, F2d, F6, F7 green on both: the base wrote the
body's values, and the body's IV is what a fly records).
Run:  python3 tests/check_fly_entry_quote.py   (exit 0 green, 1 red)
"""
import glob as _glob
import logging
import os
import sqlite3
import sys
import tempfile
import types
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
_s = tempfile.mkdtemp(prefix="check_fly_entry_quote.")
for _k, _v in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived.db"), ("OT_RESTING_DB", "resting.db"),
               ("OT_FEED_DB", "feed.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_RESTING_STOP_STATE", "rs.json"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(_s, _v)
os.environ.setdefault("OT_INSTRUMENT", "NVDA")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def near(a, b, tol=1e-9):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def K(sym, typ, strike, bid, ask, delta, gamma, theta, iv):
    return types.SimpleNamespace(symbol=sym, option_type=typ, strike=strike, bid=bid, ask=ask,
                                 mark=(bid + ask) / 2, delta=delta, gamma=gamma, theta=theta, vega=0.0, iv=iv)


# NVDA 2026-10-28 b495e4a9 legs at 17:02:08 UTC (quotes: warehouse quote_series; greeks NVDA-like)
LO = K("NVDA  261028C00217500", "C", 217.5, 0.96, 0.98, 0.5200, 0.0820, -0.4500, 0.640)
CE = K("NVDA  261028C00220000", "C", 220.0, 0.21, 0.22, 0.1642, 0.0994, -0.2153, 0.621)
UP = K("NVDA  261028C00222500", "C", 222.5, 0.04, 0.05, 0.0283, 0.0290, -0.0700, 0.700)
OTHER = K("NVDA  261028C00215000", "C", 215.0, 2.50, 2.55, 0.80, 0.03, -0.30, 0.66)
PUT = K("NVDA  261028P00220000", "P", 220.0, 1.90, 1.95, -0.83, 0.0994, -0.2153, 0.60)


def chain(calls, puts=(PUT,)):
    return types.SimpleNamespace(calls=list(calls), puts=list(puts), iv_rank=37.5, spot_price=219.05)


def fly_record(**over):
    r = {"trade_id": str(uuid.uuid4()), "symbol": "NVDA", "strategy": "GEXPinButterfly", "setup_type": "gex_pin",
         "direction": "neutral", "option_side": "call", "is_butterfly": 1, "strike": 220.0,
         "lower_strike": 217.5, "center_strike": 220.0, "upper_strike": 222.5,
         "lower_symbol": LO.symbol, "center_symbol": CE.symbol, "upper_symbol": UP.symbol,
         "option_symbol": CE.symbol, "entry_premium": 0.58, "contracts": 8, "paper_trade": 1}
    r.update(over)
    return r


COLS = ("entry_bid", "entry_ask", "entry_delta", "entry_gamma", "entry_theta", "entry_iv", "chain_iv_rank")

print("check_fly_entry_quote (FLY.3)")
import main as M                                                # noqa: E402

tl = M.get_trade_logger()
DB = os.environ["OT_TRADES_DB"]


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__()
        self.msgs = []

    def emit(self, rec):
        self.msgs.append(rec.getMessage())


cap = _Cap()
M.logger.addHandler(cap)


def run(rec, ch):
    tl.log_entry(dict(rec))
    try:
        ok = M._capture_entry_contract({"chain": ch}, rec)
    except Exception as exc:                                    # noqa: BLE001
        ok = f"{type(exc).__name__}: {exc}"
    con = sqlite3.connect(DB)
    try:
        row = con.execute(f"SELECT {', '.join(COLS)} FROM trades WHERE trade_id=?", (rec["trade_id"],)).fetchone()
    finally:
        con.close()
    return ok, dict(zip(COLS, row)) if row else {}


# ── F1-F3 the NVDA fly ────────────────────────────────────────────────────────
ok, got = run(fly_record(), chain([OTHER, LO, CE, UP]))
check("F1a the write is reported (True)", ok is True, f"{ok!r}")
check("F1b entry_bid 0.56 = 0.96 + 0.04 - 2 x 0.22", near(got.get("entry_bid"), 0.56), f"{got.get('entry_bid')}")
check("F1c entry_ask 0.61 = 0.98 + 0.05 - 2 x 0.21", near(got.get("entry_ask"), 0.61), f"{got.get('entry_ask')}")
check("F1d they bracket entry_premium 0.58",
      got.get("entry_bid") is not None and got["entry_bid"] <= 0.58 <= (got.get("entry_ask") or 0), f"{got}")
check("F2a entry_delta = 0.52 + 0.0283 - 2 x 0.1642", near(got.get("entry_delta"), 0.52 + 0.0283 - 2 * 0.1642),
      f"{got.get('entry_delta')}")
check("F2b entry_gamma = 0.082 + 0.029 - 2 x 0.0994", near(got.get("entry_gamma"), 0.082 + 0.029 - 2 * 0.0994),
      f"{got.get('entry_gamma')}")
check("F2c entry_theta = -0.45 - 0.07 + 2 x 0.2153", near(got.get("entry_theta"), -0.45 - 0.07 + 2 * 0.2153),
      f"{got.get('entry_theta')}")
check("F2d entry_iv is the BODY's IV (0.621) and chain_iv_rank 37.5 is kept",
      near(got.get("entry_iv"), 0.621) and near(got.get("chain_iv_rank"), 37.5), f"{got}")
check("F3 not the center leg's 0.21/0.22, delta 0.1642 (the 2026-10-28 row)",
      not (near(got.get("entry_bid"), 0.21) or near(got.get("entry_ask"), 0.22) or near(got.get("entry_delta"), 0.1642)),
      f"{got}")

# ── F4 legs by strike when the symbols are absent ─────────────────────────────
ok, got4 = run(fly_record(lower_symbol="", center_symbol="", upper_symbol=""), chain([OTHER, LO, CE, UP]))
check("F4 legs found by strike on the call side give the same fly values (0.56/0.61, as F1-F2)",
      ok is True and near(got4.get("entry_bid"), 0.56) and near(got4.get("entry_ask"), 0.61)
      and all(near(got4.get(k), got.get(k)) for k in COLS), f"{ok!r} {got4}")

# ── F5 a missing leg writes nothing ───────────────────────────────────────────
cap.msgs.clear()
M._contract_warned.discard("fly-leg-not-found:upper")
ok5, got5 = run(fly_record(), chain([OTHER, LO, CE]))
ok5b, got5b = run(fly_record(), chain([OTHER, LO, CE]))
warn = [m for m in cap.msgs if "entry_contract NOT captured" in m and "fly-leg-not-found:upper" in m]
check("F5a a missing upper leg writes nothing (all columns NULL, no center-leg fallback)",
      ok5 is False and got5 and all(got5[k] is None for k in COLS), f"{ok5!r} {got5}")
check("F5b the second miss writes nothing either", ok5b is False and all(got5b[k] is None for k in COLS),
      f"{ok5b!r} {got5b}")
check("F5c warned once for the reason fly-leg-not-found:upper", len(warn) == 1, f"{cap.msgs}")

# ── F6 single-leg unchanged ───────────────────────────────────────────────────
single = {"trade_id": str(uuid.uuid4()), "symbol": "NVDA", "strategy": "PARK", "setup_type": "park",
          "direction": "long", "option_side": "call", "is_butterfly": 0, "strike": 215.0,
          "option_symbol": OTHER.symbol, "entry_premium": 2.52, "contracts": 3, "paper_trade": 1}
ok6, got6 = run(single, chain([OTHER, LO, CE, UP]))
check("F6 a single-leg trade writes its own contract (2.50/2.55, delta 0.80, iv 0.66)",
      ok6 is True and near(got6.get("entry_bid"), 2.50) and near(got6.get("entry_ask"), 2.55)
      and near(got6.get("entry_delta"), 0.80) and near(got6.get("entry_iv"), 0.66), f"{ok6!r} {got6}")

# ── F7 a credit vertical unchanged ────────────────────────────────────────────
vert = {"trade_id": str(uuid.uuid4()), "symbol": "NVDA", "strategy": "SweepCreditSpread", "setup_type": "sweep_credit_spread",
        "direction": "long", "option_side": "put", "is_butterfly": 0, "is_condor_leg": 0, "strike": 220.0,
        "short_symbol": PUT.symbol, "long_symbol": "NVDA  261028P00217500", "option_symbol": PUT.symbol,
        "entry_premium": 0.80, "contracts": 2, "paper_trade": 1}
ok7, got7 = run(vert, chain([OTHER, LO, CE, UP]))
check("F7 a credit vertical still writes its short leg's values (unchanged by FLY.3)",
      ok7 is True and near(got7.get("entry_bid"), 1.90) and near(got7.get("entry_delta"), -0.83), f"{ok7!r} {got7}")

M.logger.removeHandler(cap)
print("RESULT:", "FAIL " + ",".join(FAILED) if FAILED else "PASS")
sys.exit(1 if FAILED else 0)
