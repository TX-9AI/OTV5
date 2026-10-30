#!/usr/bin/env python3
"""
tests/check_orcs.py  v5.1
v5.1  2026-10-30  OTV5 r57 (TCS.LOG1) — T6 RE-POINTED (WA section 38.4): TrendCreditSpread is LOG by default (a shadow trade, never
      ordered - the operator: "Can you reactivate TCS Monday as 'log only'? But do not trade it."), so by default it IS asked;
      OT_TCS_ACTIVE=0 is what stops it now. The sweep and its leg two stay retired; the runaway is untouched.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.8  2026-10-11  OTV4TEST r269 (OPS.22, mirror of otv4 r479) - the zone NAME is "America/New_York", the zone the legacy link
      US/Eastern pointed to: identical rules, no behaviour change. tzdata 2026c moved the US/* links into tzdata-legacy;
      without it ZoneInfo of the old name raises (it broke control's fleet.py on 10-09).
v1.7  2026-10-04  OTV4TEST r250 — THE FIXTURE IS A QQQ CHAIN, SO ITS CONTRACT SCALE IS PINNED TO 1.0. Under OT_INSTRUMENT=SPX the r234 scale
      (7.5) put the wing 22.50 out on a 1-dollar fixture and O1 O3 O4 O5 T1 T2 T3 T6 went red for that reason alone (SPX-TEST, 10-04).
v1.6  2026-10-04  OTV4TEST r249 (PREM.6) — O8 RE-POINTED, NOT DROPPED (38.4): ORCS is RETIRED by ruling ("Retire it on this repo"), so the
      default is OFF; the dials and the retired-dial absence are still pinned. T2 still proves OFF signals nothing.
v1.5  2026-10-03  OTV4TEST r230 (PREM.5) — T3, T4, T5 INVERTED BY RULING: "On rolling/defending the ORCS, adopt the condor logic
      verbatim." T3: the leg is booked with the condor leg's stop (credit x 1.15), not 0. T4: over a grid of premiums, lone and
      hedged, an ORCS leg and the same leg named IronCondorStrategy get the SAME exit decision (stop when lone, hold when hedged,
      nickel, EOD). T5: two ORCS legs reach the roll's tested-side read exactly as two condor legs do.
v1.4  2026-10-03  OTV4TEST r229 (EM.2) — THE IMPLIED MOVE IS THE PLATFORM'S EXPECTED MOVE. O2's fixture is unchanged; worked by hand
      its 5.54 straddle is a 4.80 expected move (0.6 x 5.539 + 0.3 x 4.034 + 0.1 x 2.704), so the shorts are 745 (5.2 out; 746 is 4.2)
      and 756 (5.8 out; 755 is 4.8, under 4.804) - was 744 and 756.
v1.3  2026-10-03  OTV4TEST r207 (PREM.4) — THE SHAPE IS DELTA 0.20, A 3-DOLLAR WING, ONE IMPLIED MOVE. The fixture is unchanged;
      the hand-worked strikes move: at 750.20 the put is 747/744 and the call 753/756 (was 746/738, 754/762);
      with the 5.54 straddle 744 and 756 (was 743, 758); at 752.20 the put is 749/746. O8 pins the new dials.
v1.2  2026-10-03  OTV4TEST r206 (PREM.3) — THE ENTRY LADDER GOVERNS THE ENTRY. The operator: "No, we have a ladder for
      entries. THAT has to govern our entry. 'One cent better' is not even a valid increment on most
      contracts". The plan's frozen offer is gone, so O5/O6 (frozen-and-watched, restart) are REPLACED and
      O3, O4, O8, T1-T3 restated. AS OF v1.2 THE CHECKS ARE:
  O1  location (unchanged)            O2  the implied-move floor (unchanged)
  O3  priced at the MARK (mid minus mid), bid/ask credit beside it, both sides READY, the row is TAKE,
      and NO offer_* check is written
  O4  day gates: not 0DTE, a big gap, an unmeasured gap, 09:44 and 10:30 leave nothing ready
  O5  NOTHING IS FROZEN: the located strikes follow spot tick by tick; a TAKEN side is recorded and is
      not ready again while the other side still is
  O8  the dials: five, and the two offer dials are GONE from config
  T1  the first ready tick yields a put AND a call signal, each at its mark credit; once trades.db
      shows both entered, nothing is signalled
  T2  one per side from trades.db; ORCS_ENABLED off signals nothing
  T3  the REAL _execute_condor_leg books paper at limit_ladder.paper_fill_credit(mark) - the house paper
      rule - with stop 0; live is refused before the broker path
  T4-T7 unchanged (exit hold, the roll, retired, admission)
  THE v1.1 AND v1.0 LISTS BELOW DESCRIBE THE OFFER THAT r206 REMOVED.
v1.1  2026-10-03  OTV4TEST r204 (PREM.2) — ORCS IS A TRADE: THE FILLED OFFER BECOMES ONE PAPER SPREAD, HELD TO THE CLOSE;
      THE SWEEP AND THE TCS ARE RETIRED. Renamed from check_orcs_plan.py (r203), whose O1-O6 and O8
      still drive the plan under its new name. NEW:
  T1  the strategy turns the offer that FILLED THIS TICK into one signal priced AT THE LIMIT, on the
      frozen strikes; the next tick signals nothing
  T2  one per side: with an ORCS call leg open in trades.db the call signals nothing (the put still can);
      with config.ORCS_ENABLED off nothing is signalled
  T3  the REAL _execute_condor_leg books it in paper as OpeningRangeCreditSpread at the limit with NO stop,
      and REFUSES it in live mode
  T4  the REAL exit engine HOLDS an ORCS leg marked at ten times its credit (the same leg under the
      condor's name is stopped - the control), and closes it when the end-of-day close is due
  T5  the roll does not see two open ORCS legs as a condor
  T6  RETIRED: _safe_strategy does not call the sweep or the sweep's leg two; the TCS is asked (log, r57) unless OT_TCS_ACTIVE=0; each switch restores it
  T7  ORCS is in the admission table: 09:45-10:30, two of the type, not cap-exempt
v1.0  2026-10-03  OTV4TEST r203 (PREM.1) — THE OPENING PREMIUM SPREAD PLAN FINDS ITS STRIKES AND PLACES NOTHING.

  The operator, 2026-10-03: "build the plan that searches the chain for our
  trigger components' location on the chain", and "we get better than mark or
  we don't trade it."

  Drives the REAL plan with a REAL OptionsChain of OptionContracts and the
  REAL Plan / write_row on a scratch store. The expected strikes are worked by
  hand from the fixture; the expected credits are read off the fixture's own
  bid and ask.
  O1  LOCATION: each side's short is the nearest OTM strike with delta <= 0.15
      (put 747, call 753 at spot 750.20); the long is ~1% of spot further
  O2  THE IMPLIED-MOVE FLOOR BINDS: with a dear straddle the delta-qualified
      strike inside 1.25 implied moves is skipped for the next one out
  O3  PRICED AT THE MARK: credit = mid - mid; bid/ask credit recorded beside it;
      the offer rests one cent better than the mark and is written to the rows
  O4  DAY GATES: not 0DTE, a gap over the limit, an UNMEASURED gap, a tick
      before 09:45, and a tick too late for a full rest each leave no offer
  O5  THE OFFER IS FROZEN AND WATCHED: spot moves, the offer's strikes do not;
      the mark reaching the limit records filled; ten minutes unfilled expires
  O6  A RESTART CONTINUES THE OFFER: a new plan on the same store restores the
      strikes and limit from its own rows instead of re-freezing
  O8  the preliminary dials are config's, at the values the studies chose

Run:  python3 tests/check_orcs.py   (exit 0 green, 1 red)
"""
import ast
import glob as _glob
import math
import os
import sqlite3
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ["OT_CONTRACT_SCALE"] = "1"      # r250: the fixture chain is QQQ-shaped; never the box's SPX 7.5
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_orcs_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []
DAY = "2026-10-05"


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class _Store:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

    def commit(self):
        self.conn.commit()


def _et(h, m):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime(2026, 10, 5, h, m, 0, tzinfo=ZoneInfo("America/New_York"))


def _chain(spot, scale, expiry=DAY, bump=None):
    """Strikes 720..780 by $1. mark = scale*exp(-d/2.5), quoted a cent each side; delta = 0.5*exp(-d/3)."""
    from data.options_chain import OptionsChain, OptionContract
    calls, puts = [], []
    for k in range(720, 781):
        d = abs(k - spot)
        for typ, out in (("C", calls), ("P", puts)):
            m = scale * math.exp(-d / 2.5) + ((bump or {}).get((typ, k), 0.0))
            sign = 1 if typ == "C" else -1
            out.append(OptionContract(symbol=f"Q{typ}{k}", underlying="QQQ", expiry=expiry, option_type=typ,
                                      strike=float(k), bid=round(max(0.0, m - 0.01), 4), ask=round(m + 0.01, 4),
                                      mark=round(m, 4), delta=round(sign * 0.5 * math.exp(-d / 3.0), 4)))
    return OptionsChain(underlying="QQQ", expiry=expiry, spot_price=spot, calls=calls, puts=puts)


def _mid(chain, typ, k):
    c = next(x for x in (chain.calls if typ == "C" else chain.puts) if x.strike == float(k))
    return (c.bid + c.ask) / 2.0, c


def _rows(st, since=0.0):
    return {r["check_name"]: (r["value"], r["verdict"]) for r in st.conn.execute(
        "SELECT check_name, value, verdict FROM plan_check WHERE strategy='OpeningRangeCreditSpread' AND ts_epoch>=? "
        "ORDER BY ts_epoch", (since,))}


def _verdict(st):
    r = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='OpeningRangeCreditSpread' "
                        "ORDER BY ts_epoch DESC LIMIT 1").fetchone()
    return (r["verdict"], r["reason"]) if r else (None, None)


def main():
    # r249 — ORCS is RETIRED (default OFF). The trading cases below test what the trade DOES when switched on
    # (OT_ORCS=1 restores it), so they force it on here; O8 checks the shipped default from _ORCS_DEFAULT.
    import config as _C
    global _ORCS_DEFAULT
    _ORCS_DEFAULT = _C.ORCS_ENABLED
    _C.ORCS_ENABLED = True
    try:
        from strategy import plan as P
        from strategy import orcs_plan as M
    except Exception as exc:                                  # noqa: BLE001
        for n in ("O1", "O2", "O3", "O4", "O5", "O6", "O8", "T1", "T2", "T3", "T4", "T5", "T6", "T7"):
            check(f"{n} (did not run)", False, f"{type(exc).__name__}: {exc}")
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1

    GAP = {"gap_pct": 0.30, "gap_abs_pct": 0.30}
    t0 = _et(9, 45).timestamp()

    def fresh(tag):
        st = _Store(os.path.join(_S, f"{tag}.db"))
        P.bind_store(st)
        P._DORMANT.pop("OpeningRangeCreditSpread", None)
        return st, M.ORCSPlan()

    # ── O1 / O3 / O5 ────────────────────────────────────────────────────────
    st = None
    try:
        st, plan = fresh("a")
        ch = _chain(750.2, 1.0)
        P.begin_tick(t0)
        prep = plan.prepare(price_now=750.2, now_et=_et(9, 45), chain=ch, gap=GAP, today=DAY)
        p, c = prep.sides["put"], prep.sides["call"]
        got = (p.short and p.short.strike, p.long and p.long.strike, c.short and c.short.strike, c.long and c.long.strike)
        check("O1 put 747/744 and call 753/756: nearest strike with delta <= 0.20, long 3 dollars further",
              got == (747.0, 744.0, 753.0, 756.0), f"located {got}")
        ms, s_ = _mid(ch, "P", 747); ml, l_ = _mid(ch, "P", 744)
        rows = _rows(st)
        want_credit, want_nat = round(ms - ml, 4), round(s_.bid - l_.ask, 4)
        offer_rows = sorted(k for k in rows if "offer" in k)
        check("O3 put credit is mid minus mid, bid/ask beside it, both sides READY, the row is TAKE, no offer rows",
              p.credit == want_credit and p.natural == want_nat
              and rows.get("put_credit") == (want_credit, "PASS")
              and rows.get("put_credit_natural", (None,))[0] == want_nat
              and rows.get("put_ready", (0, ""))[1] == "PASS" and rows.get("call_ready", (0, ""))[1] == "PASS"
              and sorted(prep.ready) == ["call", "put"] and _verdict(st)[0] == "TAKE" and not offer_rows
              and not hasattr(plan, "_offers"),
              f"credit {p.credit} want {want_credit}; natural {p.natural} want {want_nat}; ready {prep.ready}; "
              f"verdict {_verdict(st)[0]}; offer rows {offer_rows}")

        t1 = t0 + 120
        P.begin_tick(t1)
        prep2 = plan.prepare(price_now=752.2, now_et=_et(9, 47), chain=_chain(752.2, 1.0), gap=GAP, today=DAY,
                             taken=("call",))
        r2 = _rows(st, t1)
        check("O5 nothing is frozen: at 752.20 the put is 749/746; the TAKEN call is recorded and not ready",
              prep2.sides["put"].short.strike == 749.0 and prep2.sides["put"].long.strike == 746.0
              and prep2.ready == ["put"] and r2.get("call_taken", (0, ""))[1] == "PASS"
              and r2.get("call_ready", (0, ""))[1] == "FAIL" and r2.get("put_ready", (0, ""))[1] == "PASS",
              f"put {prep2.sides['put'].short.strike}/{prep2.sides['put'].long.strike}, ready {prep2.ready}, "
              f"call_taken {r2.get('call_taken')}, call_ready {r2.get('call_ready')}")
        P.begin_tick(t1 + 60)
        prep3 = plan.prepare(price_now=752.2, now_et=_et(9, 48), chain=_chain(752.2, 1.0), gap=GAP, today=DAY,
                             taken=("call", "put"))
        check("O6 both sides taken: nothing ready, the row is HOLD",
              prep3.ready == [] and _verdict(st)[0] == "HOLD", f"ready {prep3.ready}, verdict {_verdict(st)}")
    except Exception as exc:                                  # noqa: BLE001
        check("O1 (did not run)", False, f"{type(exc).__name__}: {exc}")

    # ── O2 — the implied-move floor binds ───────────────────────────────────
    try:
        st, plan = fresh("b")
        ch = _chain(750.2, 3.0)                               # straddle 5.54 -> platform EM 4.80 (r229): 747 (3.2 out) is too near
        P.begin_tick(t0)
        prep = plan.prepare(price_now=750.2, now_et=_et(9, 45), chain=ch, gap=GAP, today=DAY)
        im = prep.im
        p, c = prep.sides["put"], prep.sides["call"]
        check("O2 with a 4.80 expected move (a 5.54 straddle) the shorts step out to 745 and 756 (>= one implied move)",
              im is not None and abs(im - 4.804) < 0.01 and p.short and p.short.strike == 745.0
              and c.short and c.short.strike == 756.0 and p.im_mult >= 1.0,
              f"im {im}, put {p.short and p.short.strike}, call {c.short and c.short.strike}")
    except Exception as exc:                                  # noqa: BLE001
        check("O2 (did not run)", False, f"{type(exc).__name__}: {exc}")

    # ── O4 — day gates ──────────────────────────────────────────────────────
    try:
        out = []
        cases = (("c", {"chain": _chain(750.2, 1.0, expiry="2026-10-06"), "gap": GAP}, (9, 45), "DECLINE", "zero_dte"),
                 ("d", {"chain": _chain(750.2, 1.0), "gap": {"gap_abs_pct": 1.25}}, (9, 45), "DECLINE", "gap_abs_pct"),
                 ("e", {"chain": _chain(750.2, 1.0), "gap": None}, (9, 45), "DECLINE", "gap_abs_pct"),
                 ("f", {"chain": _chain(750.2, 1.0), "gap": GAP}, (9, 44), "DORMANT", "entry_window"),
                 ("g", {"chain": _chain(750.2, 1.0), "gap": GAP}, (10, 30), "DORMANT", "entry_window"),
                 ("h", {"chain": _chain(750.2, 1.0), "gap": GAP}, (10, 29), "TAKE", "READY at the mark, to the entry ladder"))
        for tag, kw, when, want_v, want_gate in cases:
            st, plan = fresh(tag)
            ts = _et(*when).timestamp()
            P.begin_tick(ts)
            prep = plan.prepare(price_now=750.2, now_et=_et(*when), today=DAY, **kw)
            v, why = _verdict(st)
            out.append((tag, v, (why or "").split(":")[0], bool(prep.ready)))
        ok = all(v == c_[3] and g == c_[4] and rdy == (c_[3] == "TAKE") for (_t, v, g, rdy), c_ in zip(out, cases))
        check("O4 not 0DTE, a 1.25% gap, an unmeasured gap, 09:44 and 10:30 leave nothing ready; 10:29 is still ready",
              ok, str(out))
    except Exception as exc:                                  # noqa: BLE001
        check("O4 (did not run)", False, f"{type(exc).__name__}: {exc}")
    finally:
        P.bind_store(None)

    # ── O8 — the dials ──────────────────────────────────────────────────────
    try:
        import config as C
        got = (tuple(C.ENTRY_WINDOWS["OpeningRangeCreditSpread"][0]), tuple(C.ENTRY_WINDOWS["OpeningRangeCreditSpread"][1]),
               C.ORCS_SHORT_DELTA_MAX, C.ORCS_MIN_IM_MULT, C.ORCS_WING_USD, C.ORCS_MIN_CREDIT, C.ORCS_MAX_GAP_PCT)
        want = ((9, 45), (10, 30), 0.20, 1.0, 3.0, 0.10, 0.90)
        gone = [n for n in ("ORCS_LIMIT_IMPROVE", "ORCS_REST_MIN", "ORCS_WING_PCT") if hasattr(C, n) or hasattr(M, n)]
        check("O8 config carries the window and five dials (delta 0.20, wing 3, one implied move), the trade is RETIRED (default OFF, r249), and the retired dials are GONE",
              got == want and (M.ORCS_START_ET, M.ORCS_SHORT_DELTA_MAX) == ((9, 45), 0.20)
              and _ORCS_DEFAULT is False and not gone, f"{got}, shipped ORCS_ENABLED={_ORCS_DEFAULT}, still present {gone}")
    except Exception as exc:                                  # noqa: BLE001
        check("O8 (did not run)", False, f"{type(exc).__name__}: {exc}")

    # ══ r204 — the trade ═══════════════════════════════════════════════════
    try:
        import config as C
        from strategy import orcs as S
        import database.trade_logger as TLM
        from database.trade_logger import TradeLogger, make_record
        TLM._trade_logger = TradeLogger(os.path.join(_S, "trades.db"))

        def strat(tag):
            st = _Store(os.path.join(_S, f"{tag}.db"))
            P.bind_store(st)
            P._DORMANT.pop("OpeningRangeCreditSpread", None)
            return st, S.OpeningRangeCreditSpread()

        def run(sg, spot, hm, ts):
            P.begin_tick(ts)
            return sg.generate_signals(price_now=spot, now_et=_et(*hm), chain=_chain(spot, 1.0), gap=GAP, today=DAY)

        def book(tid, side, short, long_):
            TLM._trade_logger.log_entry(make_record(
                trade_id=tid, symbol="QQQ", strategy="OpeningRangeCreditSpread", setup_type=f"orcs_{side}",
                direction="neutral", option_side=side, strike=short, short_strike=short, long_strike=long_,
                spread_width=8.0, credit_received=0.2, contracts=1, entry_premium=0.2, total_cost=780.0,
                max_loss=780.0, is_condor_leg=1, paper_trade=1, status="open", expiry=DAY))

        # T1 — the first ready tick
        st, sg = strat("t1")
        a = run(sg, 750.2, (9, 45), t0)
        ch0 = _chain(750.2, 1.0)
        want = {"put": round(_mid(ch0, "P", 747)[0] - _mid(ch0, "P", 744)[0], 4),
                "call": round(_mid(ch0, "C", 753)[0] - _mid(ch0, "C", 756)[0], 4)}
        got = {x.option_side: x.net_credit for x in a}
        strikes = {x.option_side: ((x.short_put_contract or x.short_call_contract).strike,
                                   (x.long_put_contract or x.long_call_contract).strike) for x in a}
        sig_call = next((x for x in a if x.option_side == "call"), None)
        mark_call = want["call"]
        check("T1 the first ready tick signals a put AND a call, each AT ITS MARK credit, on the located strikes",
              got == want and strikes == {"put": (747.0, 744.0), "call": (753.0, 756.0)}
              and all(x.strategy_name == "OpeningRangeCreditSpread" for x in a) and _verdict(st)[0] == "TAKE",
              f"credits {got} want {want}; strikes {strikes}")

        # T2 — one per side from trades.db, and the switch
        book("orcs-open-call", "call", 754.0, 762.0)
        only_put = run(sg, 750.2, (9, 46), t0 + 60)
        C.ORCS_ENABLED = False
        try:
            off = run(sg, 750.2, (9, 47), t0 + 120)
        finally:
            C.ORCS_ENABLED = True
        book("orcs-open-put", "put", 746.0, 738.0)
        none = run(sg, 750.2, (9, 48), t0 + 180)
        check("T2 an open ORCS call leaves only the put; the switch off signals nothing; both open signals nothing",
              [x.option_side for x in only_put] == ["put"] and off == [] and none == [],
              f"with call open {[x.option_side for x in only_put]}, switched off {len(off)}, both open {len(none)}")
    except Exception as exc:                                  # noqa: BLE001
        check("T1 (did not run)", False, f"{type(exc).__name__}: {exc}")
        sig_call = None
    finally:
        P.bind_store(None)

    # T3 — the real executor
    try:
        os.environ["OT_PAPER_TRADING"] = "1"
        import main
        import execution.position_manager as PMM
        from execution.limit_ladder import paper_fill_credit as _pfc
        TLM._trade_logger = TradeLogger(os.path.join(_S, "exec", "trades.db")) if os.makedirs(
            os.path.join(_S, "exec"), exist_ok=True) is None else None
        PMM._position_manager = None

        class _Sz:
            allowed, contracts, reject_reason = True, 1, ""
            total_cost = max_loss = 0.0

        class _RM:
            def size_for(self, *a, **k): return _Sz()

        class _AM:
            def _send(self, *a, **k): pass
            def send_entry_alert(self, *a, **k): pass
        saved = (main.get_risk_manager, main.get_alert_manager, main.entries_open, main._post_credit_vertical)
        posted = []

        def _post(*a, **k):
            posted.append(1)
            raise RuntimeError("a live ORCS order reached the broker path")
        main.get_risk_manager, main.get_alert_manager, main.entries_open = (lambda: _RM()), (lambda: _AM()), (lambda: True)
        main._post_credit_vertical = _post
        try:
            state = main.BotState(); state.paper_trading = False
            main._execute_condor_leg(sig_call, state, None)
            live_rows = len(TLM._trade_logger.get_open_trades())
            state.paper_trading = True
            main._execute_condor_leg(sig_call, state, None)
        finally:
            main.get_risk_manager, main.get_alert_manager, main.entries_open, main._post_credit_vertical = saved
        rows = TLM._trade_logger.get_open_trades()
        r = rows[0] if rows else {}
        check("T3 live is REFUSED; paper books OpeningRangeCreditSpread 753/756 at paper_fill_credit(mark) with the condor leg's stop (credit x 1.15)",
              live_rows == 0 and not posted and len(rows) == 1 and r.get("strategy") == "OpeningRangeCreditSpread"
              and float(r.get("entry_premium") or 0) == _pfc(mark_call) == mark_call and abs(float(r.get("stop_premium") or 0) - mark_call * (1 + float(__import__('config').CONDOR_LONE_STOP_PCT))) < 1e-6
              and float(r.get("short_strike") or 0) == 753.0 and float(r.get("long_strike") or 0) == 756.0
              and r.get("option_side") == "call",
              f"live rows {live_rows}, broker path reached {len(posted)}, paper rows {len(rows)}, {dict((k, r.get(k)) for k in ('strategy', 'entry_premium', 'stop_premium', 'short_strike'))}")
    except Exception as exc:                                  # noqa: BLE001
        check("T3 (did not run)", False, f"{type(exc).__name__}: {exc}")
        main = None

    # T4 — the real exit engine
    try:
        import execution.exit_engine as XE
        eng = XE.ExitEngine(paper_trading=True)
        def leg(strategy):
            return make_record(trade_id="x-" + strategy, symbol="QQQ", strategy=strategy, setup_type="orcs_call",
                               direction="neutral", option_side="call", short_strike=754.0, long_strike=762.0,
                               spread_width=8.0, credit_received=0.2, contracts=1, entry_premium=0.2,
                               is_condor_leg=1, paper_trade=1, status="open", underlying_stop=0.0)
        sv = (XE.is_hard_close_time, eng._condor_sibling_open)
        XE.is_hard_close_time = lambda: False
        diffs, seen = [], {}
        try:
            for hedged in (False, True):
                eng._condor_sibling_open = lambda record, default=False, _h=hedged: _h
                for prem in (0.01, 0.05, 0.10, 0.20, 0.50, 1.36, 1.38, 2.00, 7.90):
                    a = eng._evaluate_condor_leg(leg("OpeningRangeCreditSpread"), prem)
                    b = eng._evaluate_condor_leg(leg("IronCondorStrategy"), prem)
                    ra = (a.should_exit, str(a.exit_reason or "").split(" ")[0])
                    rb = (b.should_exit, str(b.exit_reason or "").split(" ")[0])
                    seen[(hedged, prem)] = ra
                    if ra != rb:
                        diffs.append((hedged, prem, ra, rb))
            XE.is_hard_close_time = lambda: True
            sv2 = XE.eod_close_due
            XE.eod_close_due = lambda *a, **k: True
            try:
                eod = eng._evaluate_condor_leg(leg("OpeningRangeCreditSpread"), 2.00)
            finally:
                XE.eod_close_due = sv2
        finally:
            XE.is_hard_close_time, eng._condor_sibling_open = sv
        # the leg: credit 0.20 on an 8-wide spread -> lone stop at 0.20 + 0.15 x 7.80 = 1.37
        check("T4 an ORCS leg gets the condor leg's decision at every premium, lone and hedged: lone stops at 1.37, hedged holds, the nickel closes, EOD closes",
              not diffs and seen[(False, 1.36)][0] is False and seen[(False, 1.38)] == (True, "condor_stop")
              and seen[(True, 7.90)][0] is False and seen[(True, 0.05)] == (True, "nickel_close")
              and seen[(False, 0.01)] == (True, "nickel_close") and seen[(False, 0.20)][0] is False
              and eod.should_exit is True and "hard_close" in str(eod.exit_reason),
              f"differs {diffs[:3]}; lone 1.36 {seen.get((False, 1.36))} 1.38 {seen.get((False, 1.38))}; hedged 7.90 {seen.get((True, 7.90))} "
              f"nickel {seen.get((True, 0.05))}; eod {eod.should_exit} ({eod.exit_reason})")
    except Exception as exc:                                  # noqa: BLE001
        check("T4 (did not run)", False, f"{type(exc).__name__}: {exc}")

    # T5 — the roll
    try:
        from strategy import condor_roll as CR
        import inspect
        class _PM:
            def __init__(self, strat): self.s = strat
            def get_open_records(self):
                return [{"is_condor_leg": 1, "strategy": self.s, "option_side": "put", "short_strike": 746.0,
                         "long_strike": 738.0, "trade_id": "a"},
                        {"is_condor_leg": 1, "strategy": self.s, "option_side": "call", "short_strike": 754.0,
                         "long_strike": 762.0, "trade_id": "b"}]
        seen = {}
        sv = CR.classify_tested
        CR.classify_tested = lambda legs, *a, **k: (seen.setdefault("n", len(legs)) and None, None)
        try:
            r_orcs = CR.check_and_execute_roll(_PM("OpeningRangeCreditSpread"), object(), 750.0, None)
            n_orcs = seen.pop("n", 0)
            try:
                CR.check_and_execute_roll(_PM("IronCondorStrategy"), object(), 750.0, None)
            except Exception:                                 # noqa: BLE001
                pass
            n_ctrl = seen.pop("n", 0)
        finally:
            CR.classify_tested = sv
        check("T5 two ORCS legs reach the roll's tested-side read exactly as two condor legs do (the control)",
              r_orcs is False and n_orcs == 2 and n_ctrl == 2, f"orcs legs seen {n_orcs}, control {n_ctrl}")
    except Exception as exc:                                  # noqa: BLE001
        check("T5 (did not run)", False, f"{type(exc).__name__}: {exc}")

    # T6 — retired
    try:
        import config as C
        called = []
        main._set_admission(None)
        for nm in ("SweepCreditSpread", "SweepForLeg2", "TrendCreditSpread"):
            main._safe_strategy(nm, lambda nm=nm: called.append(nm), None)
        off = list(called)
        _tv = os.environ.get("OT_TCS_ACTIVE")                  # r57: "0" stops the TCS (unset = log, asked)
        os.environ["OT_TCS_ACTIVE"] = "0"
        try:
            main._safe_strategy("TrendCreditSpread", lambda: called.append("TCS-at-0"), None)
        finally:
            if _tv is None:
                os.environ.pop("OT_TCS_ACTIVE", None)
            else:
                os.environ["OT_TCS_ACTIVE"] = _tv
        sv = (C.SWEEP_CS_ENABLED, C.TREND_CREDIT_ACTIVE)
        C.SWEEP_CS_ENABLED = C.TREND_CREDIT_ACTIVE = True
        try:
            for nm in ("SweepCreditSpread", "SweepForLeg2", "TrendCreditSpread"):
                main._safe_strategy(nm, lambda nm=nm: called.append(nm), None)
        finally:
            C.SWEEP_CS_ENABLED, C.TREND_CREDIT_ACTIVE = sv
        main._safe_strategy("RunawayContinuation", lambda: called.append("RunawayContinuation"), None)
        check("T6 the sweep and its leg two are not called, the TCS is (log, r57) and OT_TCS_ACTIVE=0 stops it; each "
              "switch restores them; the runaway is untouched",
              off == ["TrendCreditSpread"] and sv == (False, False)
              and called == ["TrendCreditSpread", "SweepCreditSpread", "SweepForLeg2", "TrendCreditSpread", "RunawayContinuation"],
              f"off {off}, defaults {sv}, after {called}")
    except Exception as exc:                                  # noqa: BLE001
        check("T6 (did not run)", False, f"{type(exc).__name__}: {exc}")

    # T7 — admission
    try:
        import execution.position_manager as PMM
        rule = PMM.rules().get("OpeningRangeCreditSpread")
        check("T7 ORCS is admitted 09:45-10:30, two of the type, NOT exempt from the daily cap",
              rule is not None and tuple(map(tuple, rule.window)) == ((9, 45), (10, 30))
              and rule.max_open_of_type == 2 and rule.cap_exempt is False and not rule.blocks and not rule.blocked_by,
              str(rule))
    except Exception as exc:                                  # noqa: BLE001
        check("T7 (did not run)", False, f"{type(exc).__name__}: {exc}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — ORCS finds its strikes, the house entry prices it, it is defended as a condor; sweep and TCS retired")
    return 0


if __name__ == "__main__":
    sys.exit(main())
