#!/usr/bin/env python3
"""
tests/check_live_exit_paths.py  v5.1
v5.1  2026-10-31  OTV5 r67 (PARC.4) — L1c's credit vertical is a SweepCreditSpread lone vertical
      (structure CONDOR_LEG, is_condor_leg 0), not a PARC row, and the L4 INFO line is gone: PARC is removed.
      The operator, 2026-10-31: "On PARC, no. It was an idea. It failed. It's done." and "Yes" to removing its code. Every property unchanged.
v5.0  2026-10-28  OTV5 r48 (LIVE.7, PARC.1 nickel) — THE LIVE EXIT PATH'S THREE EDGES FROM THE 2026-10-27 ORDER-PATH
      AUDIT, DRIVEN THROUGH THE REAL ExitEngine AND PositionManager WITH A STUB BROKER.
      (b) position_manager.flatten_all with no live mark handed the ENTRY premium on as the mark: live, a 15:50 close
      posted a sell limit AT ENTRY (marketable when the option is above entry). (c) position_manager._stash_quote was
      never cleared, so a tick priced by the live REST fallback walked / clamped on an earlier tick's quote. (fly) the
      fly's stop is declared `walk` (strategy/management.EXIT_PRICING) but _close_butterfly posted at the mark.

  L1a LIVE 15:52, single-leg long, no mark: flatten_all posts NOTHING (no sell limit at entry before the cross)
  L1b LIVE 15:56, same: the cross closes it (one MARKET order)
  L1c LIVE 15:47, credit vertical with no mark and no best case: nothing posted (base: a buy-back limit AT entry)
  L1d PAPER 15:56, no mark (single): flatten_all still books the ENTRY premium (the paper fetch's own fallback
      and its WARNING)
  L1e PAPER 15:56, no mark (a tent the chain cannot fully see - the fetch returns None): flatten_all still books
      the ENTRY premium with the "P&L approximate" WARNING
  L2a LIVE: a stash from an earlier pricing pass (this pass priced by the REST fallback) is NOT used - the close
      posts at the fresh mark
  L2b LIVE: a stash from this pass but older than EXIT_QUOTE_MAX_AGE_S is not used either
  L2c UNCHANGED: a fresh stash from this pass still walks (the ladder's opener, inside the quote, above the mark)
  L3a the fly's stop is declared `walk` (management.EXIT_PRICING["stop"])
  L3b LIVE: a fly stop posts the walk's opener on the fly's fresh composite quote, not the mark
  L3c LIVE: a fly FLOOR reason (hard_stop) still posts at the mark
  L3d LIVE: the fly's 15:45 resting best case and 15:55 one-tick cross are unchanged
  L5a PAPER: the fly stop books the mark; L5b PAPER: a stale stash changes nothing, the single books the mark;
      L5c PAPER: the no-mark flatten's ledger P&L is $0 at entry (as on base)

Born red on b78fc8f at L1a, L1c, L2a, L2b, L3b. Run both ways (base vs fix).
Run:  python3 tests/check_live_exit_paths.py   (needs the venv's tastytrade)
"""
import datetime as D
import logging
import os
import shutil
import sys
import tempfile
import time
import types
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
_s = tempfile.mkdtemp(prefix="check_live_exit_paths.")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived_store.db"),
               ("OT_RESTING_DB", "resting.db"), ("OT_RESTING_STOP_STATE", "rs.json"),
               ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log")):
    os.environ.setdefault(_k, os.path.join(_s, _f))
ET = ZoneInfo("America/New_York")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


DAY = (2026, 10, 28)                       # a Wednesday, full session


def at(h, m):
    return D.datetime(*DAY, h, m, 5, tzinfo=ET)


class _Acct:
    """The broker: records every order; a posted order dies unfilled (nothing books)."""
    def __init__(self):
        self.orders = []

    def place_order(self, session, order, dry_run=False):
        self.orders.append(order)
        return types.SimpleNamespace(errors=None, order=types.SimpleNamespace(id=f"O{len(self.orders)}"))

    def get_order(self, session, oid):
        from tastytrade.order import OrderStatus
        return types.SimpleNamespace(id=oid, status=OrderStatus.CANCELLED, legs=[], reject_reason=None)

    def delete_order(self, session, oid):
        return None


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(); self.recs = []

    def emit(self, r):
        self.recs.append((r.name, r.levelno, r.getMessage()))


def _c(strike, mark, bid, ask, sym):
    return types.SimpleNamespace(strike=strike, mark=mark, bid=bid, ask=ask, theta=-0.1, delta=0.5,
                                 iv=0.0, symbol=sym)


def main():
    print("check_live_exit_paths")
    try:
        from tastytrade.order import OrderType
    except ImportError as exc:
        print(f"NOT RUN — this interpreter cannot import tastytrade ({exc}); run under the venv")
        return 2
    import config as _cfg
    _cfg.LIVE_FILL_POLL_SECONDS = 0.0
    _cfg.LIVE_FILL_DEADLINE_SECONDS = 0.0
    logging.getLogger("execution.tick_size").setLevel(logging.ERROR)
    import utils.time_utils as TU
    import execution.exit_engine as EE
    import execution.position_manager as PM
    import database.trade_logger as TL
    from execution import ladder_registry as LR
    from strategy import management as MG

    clock = {"t": at(10, 30)}
    EE.now_et = lambda: clock["t"]
    TU.now_et = lambda: clock["t"]
    acct = {"a": _Acct()}
    EE.get_session, EE.get_account = (lambda: "S"), (lambda: acct["a"])
    PM._rs.active_mode = lambda paper: "off"
    cap = _Cap()
    for _ln in ("", "execution.position_manager", "execution.exit_engine"):
        logging.getLogger(_ln).addHandler(cap); logging.getLogger(_ln).setLevel(logging.INFO)
        if _ln:
            logging.getLogger(_ln).propagate = False
    tl = TL.get_trade_logger()

    live = EE.ExitEngine(paper_trading=False)
    live._alert_live_exit_once = lambda tid, kind, msg: None
    paper = EE.ExitEngine(paper_trading=True)

    def mgr(paper_mode):
        pm = PM.PositionManager(paper_trading=paper_mode)
        PM.get_exit_engine = (lambda p=True: paper) if paper_mode else (lambda p=True: live)
        pm._get_option_mark = lambda client, sym: None              # the REST fallback has no mark
        pm._get_option_marks = lambda client, syms: {}
        PM.get_client = lambda: object()
        return pm

    def single(tid, **kw):
        r = TL.make_record(trade_id=tid, symbol="QQQ", strategy="Breakout", setup_type="breakout",
                           direction="long", option_side="call", contracts=2, entry_premium=1.00,
                           total_cost=200.0, max_loss=200.0, stop_premium=0.75, strike=700.0,
                           option_symbol="QQQ   261028C00700000", expiry="2026-10-28")
        r.update(kw)
        return r

    # ── L1 — flatten_all with no live mark ──────────────────────────────────────────────────
    clock["t"] = at(15, 52)
    acct["a"] = _Acct(); LR.reset_all()
    pm = mgr(False)
    r1 = single("L1a-single"); tl.log_entry(r1)
    pm._open_records = [r1]
    try:
        pm.flatten_all("eod", chain=None, spot=701.0)
    except Exception as exc:                                         # noqa: BLE001
        print(f"      (flatten raised: {type(exc).__name__}: {exc})")
    at_entry = [o for o in acct["a"].orders if getattr(o, "price", None) is not None
                and abs(abs(float(o.price)) - 1.00) < 1e-9]
    check("L1a LIVE 15:52 no mark: nothing posted (no sell limit at entry before the cross)",
          not acct["a"].orders,
          f"orders={[(str(o.order_type), getattr(o, 'price', None)) for o in acct['a'].orders]} at_entry={len(at_entry)}")

    clock["t"] = at(15, 56)
    acct["a"] = _Acct(); LR.reset_all()
    r1b = single("L1b-single"); tl.log_entry(r1b)
    pm._open_records = [r1b]
    try:
        pm.flatten_all("eod", chain=None, spot=701.0)
    except Exception as exc:                                         # noqa: BLE001
        print(f"      (flatten raised: {type(exc).__name__}: {exc})")
    check("L1b LIVE 15:56 no mark: the cross closes it (one MARKET order)",
          len(acct["a"].orders) == 1 and acct["a"].orders[0].order_type == OrderType.MARKET,
          f"orders={[(str(o.order_type), getattr(o, 'price', None)) for o in acct['a'].orders]}")

    clock["t"] = at(15, 47)
    acct["a"] = _Acct(); LR.reset_all()
    r1c = TL.make_record(trade_id="L1c-vert", symbol="QQQ", strategy="SweepCreditSpread", setup_type="sweep_credit_spread",
                         direction="long", option_side="put", contracts=3, entry_premium=0.60,
                         total_cost=120.0, max_loss=120.0, short_strike=699.0, long_strike=698.0,
                         short_symbol="QQQ   261028P00699000", long_symbol="QQQ   261028P00698000",
                         spread_width=1.0, expiry="2026-10-28", is_condor_leg=0)
    tl.log_entry(r1c)
    pm._open_records = [r1c]
    try:
        pm.flatten_all("eod", chain=None, spot=None)                 # no spot: no best case
    except Exception as exc:                                         # noqa: BLE001
        print(f"      (flatten raised: {type(exc).__name__}: {exc})")
    check("L1c LIVE 15:47 credit vertical, no mark and no best case: nothing posted",
          not acct["a"].orders,
          f"orders={[(str(o.order_type), getattr(o, 'price', None)) for o in acct['a'].orders]}")

    clock["t"] = at(15, 56)
    pmp = mgr(True)
    r1d = single("L1d-paper"); tl.log_entry(r1d)
    pmp._open_records = [r1d]
    cap.recs.clear()
    try:
        pmp.flatten_all("eod", chain=None, spot=701.0)
    except Exception as exc:                                         # noqa: BLE001
        print(f"      (flatten raised: {type(exc).__name__}: {exc})")
    with tl._db() as conn:
        row = conn.execute("SELECT status, exit_premium, pnl_usd FROM trades WHERE trade_id='L1d-paper'").fetchone()
    warn = [m for n, lv, m in cap.recs if lv == logging.WARNING and "entry premium" in m and "L1d-pap" in m]
    check("L1d PAPER 15:56 no mark (single): books the ENTRY premium with its entry-premium WARNING",
          row is not None and row[1] is not None and abs(float(row[1]) - 1.00) < 1e-9 and len(warn) == 1,
          f"row={tuple(row) if row else None} warnings={len(warn)}")
    check("L5c PAPER no-mark flatten: ledger P&L $0 at entry (as on base)",
          row is not None and row[2] is not None and abs(float(row[2])) < 1e-9, f"row={tuple(row) if row else None}")

    # L1e — the flatten's OWN fallback (the fetch returns None: a tent with a leg the chain cannot see)
    r1e = TL.make_record(trade_id="L1e-tent", symbol="QQQ", strategy="IronCondorStrategy", setup_type="tent",
                         direction="short", option_side="call", contracts=1, entry_premium=0.80,
                         total_cost=80.0, max_loss=120.0, short_strike=702.0, long_strike=703.0,
                         lower_strike=698.0, short_symbol="QQQ   261028C00702000",
                         long_symbol="QQQ   261028C00703000", lower_symbol="QQQ   261028P00698000",
                         spread_width=1.0, expiry="2026-10-28")
    tl.log_entry(r1e)
    pmp._open_records = [r1e]
    cap.recs.clear()
    chain_e = types.SimpleNamespace(calls=[_c(702.0, 0.9, 0.8, 1.0, "QQQ   261028C00702000")], puts=[],
                                    spot_price=701.0, atm_iv=0.0)
    try:
        pmp.flatten_all("eod", chain=chain_e, spot=701.0)
    except Exception as exc:                                         # noqa: BLE001
        print(f"      (flatten raised: {type(exc).__name__}: {exc})")
    with tl._db() as conn:
        row_e = conn.execute("SELECT status, exit_premium, pnl_usd FROM trades WHERE trade_id='L1e-tent'").fetchone()
    warn_e = [m for n, lv, m in cap.recs if lv == logging.WARNING and "P&L approximate" in m and "L1e-ten" in m]
    check("L1e PAPER 15:56 no mark (tent, flatten's fallback): books the ENTRY premium, 'P&L approximate' WARNING",
          row_e is not None and row_e[1] is not None and abs(float(row_e[1]) - 0.80) < 1e-9 and len(warn_e) == 1,
          f"row={tuple(row_e) if row_e else None} warnings={len(warn_e)}")

    # ── L2 — the stashed quote must be THIS pass's ───────────────────────────────────────────
    clock["t"] = at(10, 30)
    chain1 = types.SimpleNamespace(calls=[_c(700.0, 1.10, 1.00, 1.20, "QQQ   261028C00700000")], puts=[],
                                   spot_price=700.5, atm_iv=0.0)
    pm = mgr(False)
    r2 = single("L2a-stale")
    pm._fetch_current_premium(r2, chain=chain1)                     # pass 1: chain, stashes 1.00 / 1.20
    pm._get_option_marks = lambda client, syms: {s: 2.00 for s in syms}
    pm._get_option_mark = lambda client, sym: 2.00
    m2 = pm._fetch_current_premium(r2, chain=None)                  # pass 2: REST fallback, mark 2.00, no stash
    acct["a"] = _Acct(); LR.reset_all()
    live._submit_live_close(r2, 2, m2, reason="target_hit pnl=100%")
    px2 = [abs(float(o.price)) for o in acct["a"].orders if getattr(o, "price", None) is not None]
    check("L2a LIVE: an earlier pass's stash is not used; the REST-priced tick posts at its fresh mark 2.00",
          m2 == 2.00 and px2 == [2.00], f"mark={m2} posted={px2} stash={r2.get('_exit_bid')}/{r2.get('_exit_ask')}")

    pm = mgr(False)
    r2b = single("L2b-old")
    pm._fetch_current_premium(r2b, chain=chain1)
    if r2b.get("_exit_q_mono") is not None:
        r2b["_exit_q_mono"] = time.monotonic() - (getattr(EE, "EXIT_QUOTE_MAX_AGE_S", 10.0) + 5.0)
    else:                                                            # base: no stamp to age; same quote, new mark
        pass
    acct["a"] = _Acct(); LR.reset_all()
    live._submit_live_close(r2b, 2, 2.00, reason="target_hit pnl=100%")
    px2b = [abs(float(o.price)) for o in acct["a"].orders if getattr(o, "price", None) is not None]
    check("L2b LIVE: a stash from this pass but older than EXIT_QUOTE_MAX_AGE_S is not used (posts the mark 2.00)",
          px2b == [2.00], f"posted={px2b}")

    pm = mgr(False)
    r2c = single("L2c-fresh")
    m2c = pm._fetch_current_premium(r2c, chain=chain1)
    acct["a"] = _Acct(); LR.reset_all()
    live._submit_live_close(r2c, 2, m2c, reason="target_hit pnl=10%")
    px2c = [abs(float(o.price)) for o in acct["a"].orders if getattr(o, "price", None) is not None]
    check("L2c UNCHANGED: a fresh stash still walks (opener inside the quote, above the mark)",
          len(px2c) == 1 and m2c < px2c[0] <= 1.20, f"mark={m2c} posted={px2c}")

    # ── L3 — the fly honours its declared pricing ────────────────────────────────────────────
    check("L3a the fly's stop is declared walk", MG.EXIT_PRICING.get("stop") == "walk",
          f"EXIT_PRICING['stop']={MG.EXIT_PRICING.get('stop')!r}")
    fsym = {700.0: "QQQ   261028C00700000", 702.0: "QQQ   261028C00702000", 704.0: "QQQ   261028C00704000"}
    chainf = types.SimpleNamespace(calls=[_c(700.0, 2.50, 2.40, 2.60, fsym[700.0]),
                                          _c(702.0, 1.20, 1.10, 1.30, fsym[702.0]),
                                          _c(704.0, 0.40, 0.30, 0.50, fsym[704.0])],
                                   puts=[], spot_price=701.0, atm_iv=0.0)

    def fly(tid):
        return TL.make_record(trade_id=tid, symbol="QQQ", strategy="GEXPinButterfly", setup_type="fly",
                              direction="long", option_side="call", contracts=1, entry_premium=1.00,
                              total_cost=100.0, max_loss=100.0, is_butterfly=1,
                              lower_strike=700.0, center_strike=702.0, upper_strike=704.0,
                              lower_symbol=fsym[700.0], center_symbol=fsym[702.0], upper_symbol=fsym[704.0],
                              expiry="2026-10-28")
    STOP = "stop_40% pnl=-50.0%"
    pm = mgr(False)
    r3 = fly("L3b-fly")
    m3 = pm._fetch_current_premium(r3, chain=chainf)                # 2.50 + 0.40 - 2.40 = 0.50
    r3["_exit_pricing"] = (STOP, MG.EXIT_PRICING["stop"])           # what _manage_one writes for the intent
    acct["a"] = _Acct(); LR.reset_all()
    live._submit_live_close(r3, 1, m3, reason=STOP)
    px3 = [float(o.price) for o in acct["a"].orders if getattr(o, "price", None) is not None]
    # composite: bid 2.40 + 0.30 - 2*1.30 = 0.10, ask 2.60 + 0.50 - 2*1.10 = 0.90 -> the sell opener sits above the mark
    check("L3b LIVE fly stop walks: posts the ladder's opener above the mark, inside the composite quote",
          len(px3) == 1 and m3 is not None and abs(m3 - 0.50) < 1e-9 and 0.50 < px3[0] <= 0.90,
          f"mark={m3} posted={px3}")
    r3c = fly("L3c-fly")
    pm._fetch_current_premium(r3c, chain=chainf)
    acct["a"] = _Acct(); LR.reset_all()
    live._submit_live_close(r3c, 1, 0.50, reason="hard_stop pnl=-50%")
    px3c = [float(o.price) for o in acct["a"].orders if getattr(o, "price", None) is not None]
    check("L3c LIVE fly floor reason (hard_stop) still posts at the mark 0.50", px3c == [0.50], f"posted={px3c}")

    clock["t"] = at(15, 47)
    r3d = fly("L3d-fly"); pm._fetch_current_premium(r3d, chain=chainf); r3d["_eod_spot"] = 701.0
    acct["a"] = _Acct(); LR.reset_all()
    live._submit_live_close(r3d, 1, 0.50, reason="hard_close_resting_15:45_ET")
    best = EE.ExitEngine._eod_best_case(r3d)
    want = live._round_to_tick(best[0], r3d) if best else None
    rest = [float(o.price) for o in acct["a"].orders if getattr(o, "price", None) is not None]
    clock["t"] = at(15, 56)
    acct["a"] = _Acct(); LR.reset_all()
    live._submit_live_close(r3d, 1, 0.50, reason="hard_close_resting_15:45_ET")
    cross = [float(o.price) for o in acct["a"].orders if getattr(o, "price", None) is not None]
    check("L3d LIVE fly EOD unchanged: 15:47 rests at its best case, 15:56 crosses at one tick",
          want is not None and rest == [want] and cross == [0.01], f"best={best} rest={rest} cross={cross}")

    # ── L5 — paper books exactly what it booked before ───────────────────────────────────────
    clock["t"] = at(10, 30)
    r5 = fly("L5a-fly"); m5 = mgr(True)._fetch_current_premium(r5, chain=chainf)
    r5["_exit_pricing"] = (STOP, "walk")
    f5 = paper.place_exit_order(r5, STOP, mark_price=m5)
    check("L5a PAPER fly stop books the mark", f5.confirmed and abs(f5.fill_price - 0.50) < 1e-9,
          f"fill={f5.fill_price} ({f5.detail})")
    r5b = single("L5b-single"); pmp = mgr(True)
    pmp._fetch_current_premium(r5b, chain=chain1)
    f5b = paper.place_exit_order(r5b, "target_hit pnl=100%", mark_price=2.00)
    check("L5b PAPER stale stash: the single books the mark it is handed (2.00)",
          f5b.confirmed and abs(f5b.fill_price - 2.00) < 1e-9, f"fill={f5b.fill_price}")

    shutil.rmtree(_s, ignore_errors=True)
    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
