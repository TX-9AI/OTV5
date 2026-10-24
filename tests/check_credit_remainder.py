#!/usr/bin/env python3
"""tests/check_credit_remainder.py  v1.2
v1.2  2026-09-26  OTV4TEST r146 — the fixture symbol SYN is FORCED, not setdefault: with OT_INSTRUMENT present (QQQ from the sweep harness, or any shell that exports it) the ladder read QQQ's penny ticks (9 rungs, not 3) and keyed on cv:QQQ - C2b/C2c/C7b went red on ENVIRONMENT, not code.
v1.1  2026-09-22  OTV4TEST r92 — C7d reads TCS_ENTRY_END_ET from config instead of the
      literal (14,0). ⚠️ The config import is bound to `_cfg`, NOT `_C` —
      this file already binds `_C` to its contract factory and shadowing it
      made every earlier `_C(...)` an UnboundLocalError.
THE CREDIT LADDER AS SPECIFIED: per-rung deadline, intent-keyed walk, and a
partial that finishes filling.

v1.0  2026-09-08  r315. Born red at 0498534: `execution/credit_remainder.py`
      does not exist there (C0), `LadderState.next_price` has no `structure`
      argument (C1 raises TypeError, reported as a named FAIL), and
      `main._post_credit_vertical` does not exist (C2/C7).

🔑 C7 IS THE ONE THAT MATTERS — HOP 0 (WORKING_AGREEMENT §21). It drives
`_execute_condor_leg` itself, in LIVE mode, through a partial fill, and asserts
that a remainder was REGISTERED against the SAME record object the position
manager holds, keyed on the intent. Everything below C7 could pass while the
entry path never called any of it; C7 is what closes that gap.

⚠️ EVERY FIXTURE HERE IS BUILT FROM THE REPO'S OWN CONSTRUCTORS — a real
`TradeLogger` on a temp DB, the real `OptionsSignal`, the real `BotState`,
the real `LadderState` — never from a dict shaped to match the assertion
(WORKING_AGREEMENT §0.4).

Run:  python3 tests/check_credit_remainder.py
"""
import os
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")
os.environ["OT_INSTRUMENT"] = "SYN"   # r146: FORCED - an ambient OT_INSTRUMENT must not replace the fixture symbol

_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


class _C:
    """A contract as the strategies see one: symbol, strike, bid, ask, mark."""
    def __init__(self, symbol, strike, bid, ask):
        self.symbol, self.strike, self.bid, self.ask = symbol, float(strike), bid, ask
        self.mark = (bid + ask) / 2
        self.delta = -0.3


class _Fill:
    def __init__(self, filled, qty=0, net=None, oid="O1"):
        self.filled, self.quantity, self.net_price = filled, qty, net
        self.order_id, self.detail, self.working_order_id = oid, "", None


class _Resp:
    errors = None
    order = "PLACED"


def main():
    # ── C0: the module exists ────────────────────────────────────────────
    try:
        from execution import credit_remainder as cr
    except ImportError as exc:
        check("C0 execution/credit_remainder.py exists", False, str(exc))
        print("\nFAILED 1: C0 — nothing below can execute")
        return 1
    check("C0 execution/credit_remainder.py exists", True)

    from execution.entry_ladder import LadderState
    from execution import ladder_registry as lr
    from execution.entry_engine import EntryEngine
    from database.trade_logger import TradeLogger, make_record
    import database.trade_logger as _tlmod

    # ── C1: structure change keeps the rung and drops the ratchet ───────
    try:
        st = LadderState("sell", "SYN")
        p1, _ = st.next_price(0.60, 0.90, structure="A")     # rung 1 = 0.85
        st.refuse(p1)
        p2, _ = st.next_price(0.60, 0.90, structure="A")     # rung 2 = 0.80
        st.refuse(p2)
        # new structure, wider quote: rung index 2 should carry (third rung of
        # the NEW table), ratchet should be gone.
        p3, why3 = st.next_price(0.70, 1.10, structure="B")
        tbl = __import__("execution.entry_ladder", fromlist=["rungs"]).rungs(0.70, 1.10, "sell", "SYN")
        check("C1 structure change: rung carries, ratchet dropped",
              st.rung == 2 and st.best_refused is None and abs(p3 - tbl[2]) < 1e-9,
              f"rung={st.rung} best_refused={st.best_refused} posted={p3} table={tbl[:4]}")
        # same structure: ratchet still applies
        st2 = LadderState("sell", "SYN")
        q1, _ = st2.next_price(0.60, 0.90, structure="A"); st2.refuse(q1)
        q2, _ = st2.next_price(0.60, 0.90, structure="A")
        check("C1b same structure: refused price never returns",
              q2 < q1 and st2.best_refused == q1, f"q1={q1} q2={q2}")
    except TypeError as exc:
        check("C1 structure change: rung carries, ratchet dropped", False,
              f"next_price has no structure argument: {exc}")

    # ── C2: the placer — per-rung deadline, ladder price, refuse/clear ──
    os.environ["OT_PAPER_TRADING"] = "1"
    import main
    if not hasattr(main, "_post_credit_vertical"):
        check("C2 main._post_credit_vertical exists", False)
        print("\nFAILED: C2 — placer absent; C7 cannot run")
        return 1
    check("C2 main._post_credit_vertical exists", True)

    short = _C("SYN P99", 99, 1.00, 1.20)
    long_ = _C("SYN P94", 94, 0.30, 0.40)
    seen = {}

    def placer(legs, limit):
        seen["legs"], seen["limit"] = legs, limit
        return _Resp()

    def confirmer(placed, basis, deadline_s):
        seen["deadline"] = deadline_s
        return seen["fill"]

    lr.reset_all()
    key = "cv:SYN:TrendCreditSpread:put"
    seen["fill"] = _Fill(False)
    fill, limit, why = main._post_credit_vertical(short, long_, 4, key, "A",
                                                  placer=placer, confirmer=confirmer)
    check("C2a the rung deadline is the entry_engine slice, not the 20s default",
          abs(seen["deadline"] - EntryEngine._rung_deadline()) < 1e-9
          and seen["deadline"] < 20.0, f"deadline_s={seen.get('deadline')}")
    check("C2b posts the ladder's opener (25% in from best credit 0.90)",
          abs(limit - 0.85) < 1e-9 and seen["limit"] == limit
          and seen["legs"][0][2] == 4, f"limit={limit} why={why}")
    seen["fill"] = _Fill(True, 2, 0.80)
    fill2, limit2, _ = main._post_credit_vertical(short, long_, 4, key, "A",
                                                  placer=placer, confirmer=confirmer)
    check("C2c a non-fill advanced the walk: next post is one rung in",
          abs(limit2 - 0.80) < 1e-9, f"limit2={limit2}")
    check("C2d a PARTIAL refuses the rung (walk kept, ratcheted)",
          lr.active() == 1 and lr.get(key, "sell", "SYN").best_refused == limit2)
    seen["fill"] = _Fill(True, 2, 0.75)
    main._post_credit_vertical(short, long_, 2, key, "A", placer=placer, confirmer=confirmer)
    check("C2e a COMPLETE fill clears the walk", lr.active() == 0)
    seen.clear(); seen["fill"] = _Fill(True, 4, 0.0)
    dead_s, dead_l = _C("SYN P99", 99, 0.0, 0.0), _C("SYN P94", 94, 0.0, 0.0)
    f6, l6, w6 = main._post_credit_vertical(dead_s, dead_l, 4, key, "A",
                                            placer=placer, confirmer=confirmer)
    check("C2f an empty structure quote with no fallback posts NOTHING (never a 0.00 credit)",
          "legs" not in seen and not f6.filled and l6 == 0.0, f"seen={list(seen)} limit={l6}")
    f7, l7, _ = main._post_credit_vertical(dead_s, dead_l, 4, key, "A",
                                           placer=placer, confirmer=confirmer,
                                           mark_fallback=0.75)
    check("C2g the entry's net_credit fallback still posts when the quote is empty",
          seen.get("limit") == 0.75 and l7 == 0.75, f"limit={l7}")

    # ── C3: accretion into the record + the DB row ───────────────────────
    db = os.path.join(tempfile.mkdtemp(), "t.db")
    tl = TradeLogger(db)
    rec = make_record(trade_id="T-1", symbol="SYN", strategy="TrendCreditSpread",
                      setup_type="TCS", option_side="put", contracts=2,
                      entry_premium=0.80, spread_width=5.0, max_loss=(5.0-0.80)*2*100,
                      total_cost=(5.0-0.80)*2*100, stop_premium=0.0,
                      is_condor_leg=1, status="open", paper_trade=0,
                      short_symbol=short.symbol, long_symbol=long_.symbol,
                      option_symbol=short.symbol, expiry="2099-01-01")
    tl.log_entry(rec)
    cr.reset_all()
    rem = cr.Remainder(key=key, trade_id="T-1", record=rec,
                       short_symbol=short.symbol, long_symbol=long_.symbol,
                       short_strike=99.0, long_strike=94.0, side="put",
                       strategy="TrendCreditSpread", requested=4, remaining=2,
                       stop_pct=0.0, window_end_et=(14, 0))
    cr.register(rem)

    class _Chain:
        puts = [short, long_, _C("SYN P98", 98, 1.10, 1.30)]
        calls = []

    calls = []
    def place(sc, lc, q, k, structure):
        calls.append((sc.symbol, lc.symbol, q, k, structure))
        return _Fill(True, 1, 0.70), 0.70, "rung"

    n = cr.supervise(chain=_Chain(), now_hm=(12, 0), eod=False, paper=False,
                     open_trade_ids={"T-1"}, place=place, trade_logger=tl)
    row = tl._get_field("T-1", "contracts"), tl._get_field("T-1", "entry_premium"), \
          tl._get_field("T-1", "max_loss")
    blended = (2*0.80 + 1*0.70) / 3
    check("C3a a remainder fill ACCRETES: record contracts 3, blended credit",
          n == 1 and rec["contracts"] == 3 and abs(rec["entry_premium"] - blended) < 1e-9
          and abs(rec["max_loss"] - (5.0 - blended)*3*100) < 1e-6,
          f"rec={rec['contracts']}@{rec['entry_premium']:.4f} max_loss={rec['max_loss']:.2f}")
    check("C3b the DB row moved with it", row[0] == 3 and abs(row[1] - blended) < 1e-9
          and abs(row[2] - (5.0 - blended)*3*100) < 1e-6, f"row={row}")
    check("C3c the remainder still walks for the last 1, on the SAME strikes and key",
          len(cr.active()) == 1 and cr.active()[0].remaining == 1
          and calls[-1][:2] == (short.symbol, long_.symbol) and calls[-1][3] == key
          and calls[-1][2] == 2, f"calls={calls}")
    n2 = cr.supervise(chain=_Chain(), now_hm=(12, 1), eod=False, paper=False,
                      open_trade_ids={"T-1"}, place=place, trade_logger=tl)
    check("C3d filled in full: remainder dropped, 4 contracts on the row",
          n2 == 1 and cr.active() == [] and tl._get_field("T-1", "contracts") == 4
          and calls[-1][2] == 1)

    # ── C4: the three abandonments ───────────────────────────────────────
    def _fresh():
        cr.reset_all()
        r = cr.Remainder(key=key, trade_id="T-1", record=dict(rec),
                         short_symbol=short.symbol, long_symbol=long_.symbol,
                         short_strike=99.0, long_strike=94.0, side="put",
                         strategy="TrendCreditSpread", requested=4, remaining=2,
                         stop_pct=0.0, window_end_et=(14, 0))
        cr.register(r)
    hit = []
    never = lambda *a: (hit.append(1), (_Fill(False), 0.0, ""))[1]
    _fresh(); cr.supervise(_Chain(), (12, 0), False, False, {"OTHER"}, never)
    check("C4a parent closed -> abandoned, nothing posted", cr.active() == [] and not hit)
    _fresh(); cr.supervise(_Chain(), (14, 0), False, False, {"T-1"}, never)
    check("C4b entry window closed -> abandoned, nothing posted", cr.active() == [] and not hit)
    _fresh(); cr.supervise(_Chain(), (13, 0), True, False, {"T-1"}, never)
    check("C4c hard-close window -> abandoned, nothing posted", cr.active() == [] and not hit)
    _fresh(); cr.supervise(_Chain(), (13, 0), False, False, None, never)
    check("C4d an unreadable book does NOT abandon (fails open to walking)",
          len(cr.active()) == 1 and hit == [1])

    # ── C5: paper never supervises ───────────────────────────────────────
    hit.clear(); _fresh()
    n5 = cr.supervise(_Chain(), (12, 0), False, True, {"T-1"}, never)
    check("C5 paper: supervise is a no-op", n5 == 0 and not hit)

    # ── C6: strikes not on this tick's chain -> retry, never re-select ──
    hit.clear(); _fresh()
    class _NoChain:
        puts = [_C("SYN P98", 98, 1.10, 1.30)]; calls = []
    cr.supervise(_NoChain(), (12, 0), False, False, {"T-1"}, never)
    check("C6 structure absent from the chain: retry next tick, no substitute posted",
          len(cr.active()) == 1 and not hit)

    # ── C7: HOP 0 — the entry path itself registers the remainder ───────
    cr.reset_all(); lr.reset_all()
    db2 = os.path.join(tempfile.mkdtemp(), "live.db")
    _tlmod._trade_logger = TradeLogger(db2)
    import execution.position_manager as _pmm
    _pmm._position_manager = None
    from strategy.base_strategy import OptionsSignal

    class _Sz:
        allowed, contracts, reject_reason = True, 4, ""
        total_cost = max_loss = 0.0
    class _RM:
        def size_for(self, *a, **k): return _Sz()
    class _AM:
        def _send(self, *a, **k): pass
        def send_entry_alert(self, *a, **k): pass
    posted = {}
    def fake_post(sc, lc, q, k, structure, **kw):
        posted.update(sc=sc.symbol, lc=lc.symbol, q=q, key=k, structure=structure)
        return _Fill(True, 1, 0.82, "O7"), 0.85, "rung 1/3"

    _saved = (main.get_risk_manager, main.get_alert_manager, main.entries_open,
              main._post_credit_vertical)
    main.get_risk_manager = lambda: _RM()
    main.get_alert_manager = lambda: _AM()
    main.entries_open = lambda: True
    main._post_credit_vertical = fake_post
    try:
        sig = OptionsSignal()
        sig.strategy_name = "TrendCreditSpread"; sig.setup_type = "TCS 50-accept"
        sig.option_side = "put"; sig.is_trend_credit = True
        sig.short_put_contract = short; sig.long_put_contract = long_
        sig.net_credit = 0.75
        state = main.BotState(); state.paper_trading = False
        main._execute_condor_leg(sig, state, None)
    finally:
        (main.get_risk_manager, main.get_alert_manager, main.entries_open,
         main._post_credit_vertical) = _saved

    pm = _pmm.get_position_manager(False)
    recs = pm.get_open_records()
    rems = cr.active()
    check("C7a a live PARTIAL books the filled 1 and registers the remaining 3",
          len(recs) == 1 and recs[0]["contracts"] == 1 and len(rems) == 1
          and rems[0].remaining == 3 and rems[0].requested == 4,
          f"recs={len(recs)} rems={[(r.requested, r.remaining) for r in rems]}")
    check("C7b the walk is keyed on the INTENT, not the strike pair",
          posted.get("key") == "cv:SYN:TrendCreditSpread:put"
          and posted.get("structure") == f"{short.symbol}|{long_.symbol}",
          f"key={posted.get('key')} structure={posted.get('structure')}")
    check("C7c the remainder holds the SAME record object the position manager manages",
          rems and recs and rems[0].record is recs[0])
    # 🔴 r92 — READ THE END FROM CONFIG, NEVER A LITERAL. This asserted
    # `(14, 0)` and went red the moment r81 moved every credit END to 15:40 by
    # the operator's ruling — the checker was pinning a window the box had
    # stopped using. A literal here is a second copy of a constant that has
    # already moved twice this month.
    # ⚠️ NOT `_C` — this file already binds that name to its contract factory
    # at the top of main(), and importing config over it made every later
    # `_C(...)` call an UnboundLocalError. Python hoists the local binding to
    # the whole function, so the collision broke lines ABOVE this one.
    import config as _cfg
    _end = tuple(_cfg.TCS_ENTRY_END_ET)
    check("C7d TCS remainder carries no premium stop and the TCS window end",
          rems and rems[0].stop_pct == 0.0 and tuple(rems[0].window_end_et) == _end,
          f"stop_pct={rems[0].stop_pct if rems else None} "
          f"end={rems[0].window_end_et if rems else None} want={_end}")
    check("C7e the row in trades.db is the filled size, not the requested size",
          _tlmod._trade_logger._get_field(recs[0]["trade_id"], "contracts") == 1 if recs else False)

    if _fails:
        print(f"\nFAILED {len(_fails)}: " + "; ".join(_fails))
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
