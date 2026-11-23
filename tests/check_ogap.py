#!/usr/bin/env python3
"""
tests/check_ogap.py  v5.7
v5.7  2026-11-23  OTV5 r153 (TRIM.2) — OGAP IS RETIRED (DORMANT, no switch; the operator, 2026-11-23: "The hunt & OGAP are
      trash. Retire them both after this session today."). O9's last term is turned around: the plan reads DORMANT on
      this paper box (its code is kept for the purge, so every spec, replay and exit check here still drives it
      directly). Every other check unchanged. tests/check_hunt_ogap_retired.py is the retirement's gate.
v5.6  2026-11-22  OTV5 r149 (OGAP.4) — OGAP ON EVERY BOX (the operator, 2026-11-22: "I honestly want it paper Trading on all of them"). O7: the same fixture on a META box now gives the same OGAP put (the plan reads no symbol list); every other O7 case unchanged. O9: the OGAP_SYMBOLS pin is replaced by "no module reads a symbol list for OGAP" (config has no OGAP_SYMBOLS; no .py outside the docs names it in code) and the plan state is ACTIVE on this paper box. O7 also: a chain on 2026-11-06 (no same-day expiry) now gives the same put on that expiry (the operator, 2026-11-22: "We just buy the nearest available expiry."; ogap_no_0dte is gone). Every other check, the replay R1-R5 and its fixture unchanged. The every-box, live-box and independence checks are tests/check_ogap_all_boxes.py.
v5.5  2026-11-21  OTV5 r137 (CAP.10) — OGAP IS UNDER THE CAP (the operator, 2026-11-21: "both trades should fall under the catastrophic cap"). O9: OGAP is NOT in CAP_EXCLUDED_STRATEGIES and its admission rule is NOT cap-exempt (every other isolation term unchanged). O11: the capped branch asks NOTHING (no _attempt_ogap, no _attempt_park; it returns); the normal path still asks OGAP with the chain. The cap's refusal and P&L for OGAP are driven in tests/check_cap_all.py.
v5.4  2026-11-21  OTV5 r136 (OGAP.3) — OGAP READS THE MARK (the operator, 2026-11-20: "never pay the spread"). O7: the
      signal books entry_premium = the mark 4.24 (4.23 / 4.26), notes carry mark=, no ogap_ask; the band case moves to
      5.01 / 5.03 (mark 5.02 buys 0 on $500; 4.99 / 5.01 is a 5.00 mark and buys 1). O8b: the restart seed arms the 1.2x
      floor on the booked fill 1.00 (1.20) and the MARK 1.19 exits (bid 1.15 beside it decides nothing). O8c: the fill
      basis is entry_premium whatever entry_ask / notes' ask= say. O10: OGAP at mark 2.45 is sized on the mark with
      RISK_PER_TRADE_USD (500 -> 2), a stray ogap_ask 2.55 ignored. R1-R5 still replay Park's book through the pure walk
      (ogap_exit_step takes the price series and the fill it is handed: his ask / bid series reproduce his rows). The
      mark-basis pins of every converted read are tests/check_ogap_mark.py.
v5.3  2026-11-16  OTV5 r131 (OGAP.2) — OGAP sizes on RISK_PER_TRADE_USD (the ramp MIN); OGAP_BUDGET_USD is deleted. This gate
      pins OT_RISK_USD=500 (Park's own size, the basis of the replay R1-R5 and the O6/O7 pins), so every pin holds; O6
      reads config.RISK_PER_TRADE_USD; O10 moves to mark 2.45 / ask 2.55 so ask vs mark still differ at $500 (OGAP 1,
      PARK 2). The sizing at other ramp MINs (1050) is tests/check_ogap_size.py.
v5.2  2026-11-15  OTV5 r123 (HYG.27) — OT_RESTING_DB leaves the scratch env (r118 deleted execution/resting_orders.py, its only reader).
v5.1  2026-11-14  OTV5 r117 (HYG §5.3) — O7b NEW: a one-sided quote (bid 0.00 / ask 4.26, and bid 4.23 / ask 0.00) at the
      fill minute gives no signal. ogap_plan.prepare and ogap.generate_signal each refuse it (`ask >= bid > 0`, two
      guards by design, so O7b goes red only when both are broken) but nothing pinned it; the zero-bid gate
      (check_zero_bid_refused Z1-Z6c) covers the other live selectors.
v5.0  2026-11-14  OTV5 (OGAP.1) — THE OGAP GATE. The operator, 2026-11-14: "let's design & paper trade the OGAP on QQQ".
      O1-O5   the read (strategy/ogap_plan.ogap_read): range bars, gate-G 0.25 vs 0.24 and fail-open, a close ON the edge
              is no break, the 21st bar after the break is no retest, one real row (the earliest allowed side; a
              refused-side retest is a shadow that never blocks), stale.
      O6      sizing: contracts_for(0.50 / 2.27 / 5.00 / 5.01) = 10 / 2 / 1 / 0 on RISK_PER_TRADE_USD (pinned 500 here; r131);
              size_for("long_debit", premium=ask, budget_usd=500) agrees; every caller without budget_usd is unchanged.
      O7      the plan end to end on a feed-less fixture: QQQ 11-05 at the fill minute -> a TAKE signal (put, the strike
              nearest the fill-minute open, notes carry ask=, ogap_ask set); one minute later -> ogap_stale, no signal;
              (r149) a META box -> the same signal; ask 0.49 -> ogap_ask_floor; ask 5.01 -> ogap_ask_band.
      O7b     a one-sided quote at the fill minute (bid 0.00 / ask 4.26; bid 4.23 / ask 0.00) -> no signal.
      O8      the exit walk (execution/exit_engine.ogap_exit_step) and _evaluate_ogap on a record: the lock, the trail,
              the 14:00 sweep once, the 15:45 bell; a restart seeds the peak from max_premium_seen (1.7x -> the 1.2x
              floor is armed); fill = entry_ask, else notes' ask=, else the mark.
      O10     the REAL entry funnel (main._execute_entry_signal, a spy entry engine): an OGAP signal (mark 2.45, a stray
              ogap_ask 2.55) is sized by the real RiskManager on the MARK with RISK_PER_TRADE_USD (500) -> 2 (r136); the same signal named
              PARK is sized on the mark with the box's own risk (unchanged).
      O11     the dispatch, DRIVEN: attempt_new_entry() asks _attempt_ogap WITH the chain on the normal path; (r137) the
              capped branch asks nothing (by text).
      O9      isolation: OGAP in DECAY_STOP_EXEMPT, PIN_EXEMPT, the admission table (one per session; r137: NOT
              cap-exempt, NOT in CAP_EXCLUDED_STRATEGIES), management covers() False, _STRUCTURE_BY_NAME long_debit, QQQ only.
      R1-R5   THE REPLAY (OGAP_PLAN.md §3): the code reproduces Park's backtest rows (~/reviews/studies/
              park_orbgap_20261113, fixture tests/fixtures/ogap/replay5.json) on QQQ 10-30, 11-02, 11-04, 11-05 and
              11-09 - the same signal minute, side, strike, contracts, exit reason, exit minute and P&L within $1.
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
"""
import json
import os
import sys
import tempfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_ogap_")
os.environ["OT_TRADES_DB"] = os.path.join(_TD, "t.db")
os.environ["OT_DERIVED_DB"] = os.path.join(_TD, "d.db")
os.environ["OT_FEED_DB"] = os.path.join(_TD, "f.db")
os.environ["OT_LOG_FILE"] = os.path.join(_TD, "bot.log")
os.environ["OT_SIGNAL_JOURNAL_DIR"] = os.path.join(_TD, "sj")
CF = os.path.join(_TD, "cf")
os.environ["OT_COUNTERFACTUAL_DIR"] = CF
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ["OT_RISK_USD"] = "500"          # r131: OGAP sizes on the ramp MIN; Park's $500 is the replay's basis
FAILED, RAN = [], []
FIX = os.path.join(ROOT, "tests", "fixtures", "ogap", "replay5.json")


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class K:
    def __init__(self, strike, bid, ask, side, expiry):
        self.strike, self.bid, self.ask, self.delta = float(strike), bid, ask, 0.5 if side == "C" else -0.5
        self.expiry, self.symbol, self.streamer_symbol = expiry, f"QQQ{side}{strike}", f".QQQ{side}{strike}"


class Chain:
    def __init__(self, expiry, center, bid, ask):
        self.expiry = expiry
        self.calls = [K(s, bid, ask, "C", expiry) for s in range(int(center) - 5, int(center) + 6)]
        self.puts = [K(s, bid, ask, "P", expiry) for s in range(int(center) - 5, int(center) + 6)]


def _bars(lo=100.0, hi=101.0, n=15):
    """A flat range 09:30.. with n bars, high `hi`, low `lo`."""
    b = {}
    for i in range(n):
        b[570 + i] = (100.5, hi, lo, 100.5)
    return b


def main():
    try:
        import config
        from strategy import ogap_plan as OP
        from strategy.ogap import Ogap
        from execution import exit_engine as EE
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN — imports failed: {type(exc).__name__}: {exc}")
        return 2

    # ── O1 range ──
    b9 = _bars(n=9)
    r = OP.ogap_read(b9, 100.0)
    b10 = _bars(n=10)
    r10 = OP.ogap_read(b10, 100.0)
    check("O1 range: 9 bars -> no range; 10 bars -> W 1.0", r["status"] == "no range" and r10["W"] == 1.0, f"{r} {r10}")

    # ── O2 gate-G ──
    def gap_allowed(open930, prior):
        b = _bars()
        b[570] = (open930, 101.0, 100.0, 100.5)
        return OP.ogap_read(b, prior)["allowed"]
    check("O2 gate-G: gap +0.25W -> C only, +0.24W -> both, -0.25W -> P only, unread -> both",
          gap_allowed(100.25, 100.0) == ["C"] and gap_allowed(100.24, 100.0) == ["C", "P"]
          and gap_allowed(99.75, 100.0) == ["P"] and gap_allowed(100.5, None) == ["C", "P"],
          f"{gap_allowed(100.25, 100.0)} {gap_allowed(100.24, 100.0)} {gap_allowed(99.75, 100.0)}")

    # ── O3 break on the edge / the 21st bar ──
    b = _bars()
    b[585] = (100.9, 101.0, 100.8, 101.0)          # closes ON the high: not a break
    b[586] = (101.0, 101.3, 100.9, 101.2)          # the break
    b[587] = (101.2, 101.4, 101.15, 101.3)         # low 101.15 > 101.1: no retest
    r = OP.ogap_read(b, 100.5)
    brk = [s for s in r["sides"] if s["side"] == "C"]
    b21 = dict(b)
    for m in range(587, 607):
        b21[m] = (101.3, 101.5, 101.2, 101.4)      # no retest for 20 bars
    b21[607] = (101.3, 101.4, 101.05, 101.2)       # the 21st bar after the break would retest
    r21 = OP.ogap_read(b21, 100.5)
    b20 = dict(b21)
    b20[606] = (101.3, 101.4, 101.05, 101.2)       # the 20th does
    r20 = OP.ogap_read(b20, 100.5)
    check("O3 a close on the edge is no break (586 breaks); the 21st bar after the break is no retest, the 20th is",
          brk and brk[0]["brk"] == 586 and r21["status"] == "break, no retest" and r20["signal"] == 606,
          f"{brk} {r21['status']} {r20.get('signal')}")

    # ── O4 one real row; a refused-side retest is a shadow ──
    b = _bars()
    b[570] = (100.4, 101.0, 100.0, 100.5)
    b[585] = (100.5, 100.6, 99.8, 99.9)            # put break 09:45
    b[586] = (99.9, 99.95, 99.7, 99.8)             # put retest 09:46 (high >= 99.9, close < 100)
    b[590] = (100.5, 101.2, 100.9, 101.1)          # call break 09:50
    b[591] = (101.1, 101.2, 101.05, 101.1)         # call retest 09:51
    r_both = OP.ogap_read(b, 100.4)                # gap 0: both allowed -> the earliest (the put)
    r_up = OP.ogap_read(b, 100.0)                  # gap +0.4W: calls only -> the put is a shadow
    check("O4 one real row: both allowed -> the earliest (put 09:46); a gap up -> the call 09:51 trades, the put is "
          "a shadow that does not block",
          r_both["side"] == "P" and r_both["signal"] == 586 and r_up["side"] == "C" and r_up["signal"] == 591
          and [s["side"] for s in r_up["shadows"]] == ["P"], f"{r_both} {r_up}")

    # ── O5 stale ──
    check("O5 stale: seen at the fill minute -> not stale; one minute later -> stale",
          OP.ogap_read(b, 100.4, now_min=587)["stale"] is False and OP.ogap_read(b, 100.4, now_min=588)["stale"] is True,
          "")

    # ── O6 sizing ──
    import risk.risk_manager as RM
    rm = RM.RiskManager() if hasattr(RM, "RiskManager") else None
    sz = [OP.contracts_for(a) for a in (0.50, 2.27, 5.00, 5.01)]
    s1 = rm.size_for("long_debit", premium=2.27, budget_usd=config.RISK_PER_TRADE_USD, grade="UNGRADED") if rm else None
    s2 = rm.size_for("long_debit", premium=2.27, grade="UNGRADED") if rm else None
    s5 = [rm.size_for("long_debit", premium=a, budget_usd=config.RISK_PER_TRADE_USD, grade="UNGRADED") for a in (0.50, 5.00, 5.01)]
    exp2 = int(float(rm.risk_per_trade if hasattr(rm, "risk_per_trade") else rm._risk_per_trade) // 227) if rm else None
    check("O6 sizing: 0.50/2.27/5.00/5.01 -> 10/2/1/0; size_for(budget_usd=500) at 2.27 -> 2; without it the box's "
          "own risk (unchanged)",
          sz == [10, 2, 1, 0] and s1 is not None and s1.contracts == 2 and s2 is not None
          and [x.contracts for x in s5[:2]] == [10, 1] and not s5[2].allowed
          and (s2.contracts == exp2 or (exp2 == 0 and not s2.allowed)),
          f"{sz} {getattr(s1, 'contracts', None)} {getattr(s2, 'contracts', None)} exp2={exp2}")

    # ── O7 the plan end to end ──
    fx = json.load(open(FIX))
    d = "2026-11-05"
    day = date.fromisoformat(d)
    bars = {int(k): tuple(v) for k, v in fx[d]["bars"].items()}
    fill = fx[d]["expect"]["fill"]
    spot = bars[fill][0]
    spec = Ogap()

    def prep_at(now_min, sym="QQQ", bid=4.23, ask=4.26, expiry=d):
        return spec.generate_signal(price_now=spot, now_et=OP.hhmm(now_min), chain=Chain(expiry, round(spot), bid, ask),
                                    day=day, symbol=sym, bars=bars, prior_close=fx[d]["prior_close"])
    s_ok = prep_at(fill)
    s_stale = prep_at(fill + 1)
    s_meta = prep_at(fill, sym="META")
    s_floor = prep_at(fill, bid=0.47, ask=0.49)
    s_band = prep_at(fill, bid=5.01, ask=5.03)                 # r136: mark 5.02 buys 0 on $500
    s_0dte = prep_at(fill, expiry="2026-11-06")
    check("O7 the plan: QQQ 11-05 at the fill minute -> OGAP put, strike %s, entry_premium = the mark 4.24, notes "
          "mark=, no ogap_ask; +1 min -> stale; META -> the same put (r149); mark 0.48 / 5.02 -> none; an 11-06 chain -> the same put on 11-06"
          % fx[d]["expect"]["strike"],
          s_ok is not None and s_ok.strategy_name == "OGAP" and s_ok.option_side == "put"
          and float(s_ok.strike) == float(fx[d]["expect"]["strike"]) and abs(s_ok.entry_premium - 4.24) < 1e-9
          and getattr(s_ok, "ogap_ask", None) is None
          and "mark=4.24" in s_ok.notes and s_ok.ogap_contracts == 1
          and s_stale is None and s_meta is not None and s_meta.option_side == s_ok.option_side
          and float(s_meta.strike) == float(s_ok.strike) and s_meta.entry_premium == s_ok.entry_premium
          and s_floor is None and s_band is None and s_0dte is not None and s_0dte.expiry == "2026-11-06"
          and float(s_0dte.strike) == float(s_ok.strike),
          f"ok={s_ok and (s_ok.option_side, s_ok.strike, s_ok.notes)} stale={s_stale} meta={s_meta} "
          f"floor={s_floor} band={s_band} 0dte={s_0dte}")

    s_nobid = prep_at(fill, bid=0.0, ask=4.26)
    s_noask = prep_at(fill, bid=4.23, ask=0.0)
    check("O7b a one-sided quote at the fill minute -> no signal (bid 0.00 / ask 4.26; bid 4.23 / ask 0.00), while the "
          "two-sided 4.23/4.26 trades",
          s_nobid is None and s_noask is None and s_ok is not None, f"nobid={s_nobid} noask={s_noask}")

    # ── O8 exits ──
    def walk(fill_ask, ticks):
        st = {"peak": 0.0, "floor": None, "swept": False}
        for m, bid in ticks:
            if bid is None:
                continue
            why = EE.ogap_exit_step(st, fill_ask, bid, (m // 60, m % 60))
            if why:
                return why, m, bid, st
        return "", None, None, st
    w_lock = walk(1.00, [(600, 1.65), (601, 1.30), (602, 1.19)])
    w_trail = walk(1.00, [(600, 2.10), (601, 1.30), (602, 1.25)])
    w_sweep = walk(1.00, [(839, 0.70), (840, 0.70)])
    w_nosweep = walk(1.00, [(840, 0.80), (900, 0.10)])
    w_bell = walk(1.00, [(944, 1.10), (945, 1.10)])
    check("O8a the walk: 1.6x then 1.19 -> ogap_lock; 2.1x then 1.25 (floor 1.26) -> ogap_trail; 14:00 at 0.70 -> "
          "sweep; 14:00 at 0.80 -> no sweep, never again; 15:45 -> the bell",
          w_lock[0].startswith("ogap_lock") and w_lock[1] == 602
          and w_trail[0].startswith("ogap_trail") and w_trail[1] == 602
          and w_sweep[0].startswith("ogap_sweep_1400") and w_sweep[1] == 840
          and w_nosweep[0] == "" and w_bell[0] == "ogap_close_1545" and w_bell[1] == 945,
          f"{w_lock[:2]} {w_trail[:2]} {w_sweep[:2]} {w_nosweep[:2]} {w_bell[:2]}")
    rec = {"trade_id": "o8-restart", "strategy": "OGAP", "entry_premium": 1.00, "entry_ask": 1.02, "contracts": 1,
           "max_premium_seen": 1.75, "_exit_bid": 1.15}
    eng = EE.ExitEngine() if hasattr(EE, "ExitEngine") else None
    dec = eng._evaluate_ogap(rec, 1.19) if eng else None
    check("O8b restart: max_premium_seen 1.75 >= 1.6 x the booked fill 1.00 -> the 1.2x floor (1.20) is armed and the "
          "mark 1.19 exits ogap_lock",
          dec is not None and dec.should_exit and dec.exit_reason.startswith("ogap_lock"),
          f"{getattr(dec, 'exit_reason', None)}")
    check("O8c fill basis: the booked entry_premium (the mark), whatever entry_ask or notes' ask= say",
          EE.ogap_fill_of({"entry_ask": 2.5, "notes": "ogap ask=2.4", "entry_premium": 2.3}) == 2.3
          and EE.ogap_fill_of({"notes": "ogap gap=0.1 ask=2.40 bid=2.38", "entry_premium": 2.3}) == 2.3
          and EE.ogap_fill_of({"entry_premium": 2.3}) == 2.3 and EE.ogap_fill_of({}) == 0.0, "")

    # ── O9 isolation ──
    import execution.position_manager as PM
    from strategy import management as MG
    from strategy import plan_state as PS
    rl = PM.rules().get("OGAP")
    mn_src = open(os.path.join(ROOT, "main.py")).read()
    import ast as _ast
    _named = []                                       # r149: no module reads a symbol list for OGAP
    for _dp, _dn, _fn in os.walk(ROOT):
        _dn[:] = [x for x in _dn if x not in (".git", "__pycache__", "docs", "venv")]
        for _f in _fn:
            if not _f.endswith(".py") or _f == "check_ogap.py":
                continue
            _p = os.path.join(_dp, _f)
            try:
                _tree = _ast.parse(open(_p, encoding="utf-8").read())
            except SyntaxError:
                continue
            for _n in _ast.walk(_tree):
                if (isinstance(_n, _ast.Name) and _n.id == "OGAP_SYMBOLS") or (
                        isinstance(_n, _ast.Attribute) and _n.attr == "OGAP_SYMBOLS"):
                    _named.append(os.path.relpath(_p, ROOT))
    check("O9 isolation: decay-exempt, UNDER the cap (r137), pin-exempt, admission one/one not cap-exempt, management does not "
          "cover it, long_debit, no symbol list (r149), plan DORMANT (retired r153)",
          "OGAP" in tuple(config.DECAY_STOP_EXEMPT) and "OGAP" not in tuple(config.CAP_EXCLUDED_STRATEGIES)
          and 'PIN_EXEMPT = ("PARK", "OGAP")' in mn_src and '"OGAP":                 "long_debit"' in mn_src
          and rl is not None and rl.max_open_of_type == 1 and rl.max_tries_per_session == 1 and not rl.cap_exempt
          and MG.covers({"strategy": "OGAP"}) is False and not hasattr(config, "OGAP_SYMBOLS") and not _named
          and PS.state("OGAP") == PS.DORMANT,
          f"rule={rl} OGAP_SYMBOLS read by {sorted(set(_named))}")

    # ── O10 the real funnel sizes OGAP on the ask with its own budget ──
    import main as MN
    from strategy.base_strategy import OptionsSignal

    class _Spy:
        def __init__(self):
            self.sz = []

        def enter(self, signal=None, sizing=None, **kw):
            self.sz.append((getattr(signal, "strategy_name", "?"), getattr(sizing, "contracts", None)))
            return None

    class _State:
        paper_trading = True

    def funnel(name):
        sg = OptionsSignal(strategy_name=name, setup_type="ogap_long", direction="long", option_side="call",
                           underlying_entry=600.0, underlying_stop=0.0, strike=600.0, entry_premium=2.45,
                           stop_loss_pct=1.0)
        if name == "OGAP":
            sg.ogap_ask = 2.55
        spy = _Spy()
        _ge = MN.get_entry_engine
        MN.get_entry_engine = lambda *a, **kw: spy
        try:
            MN._execute_entry_signal(sg, {"price": 600.0, "macro": type("M", (), {"butterfly_half_size": False})()},
                                     None, _State(), None, additive=True)
        finally:
            MN.get_entry_engine = _ge
        return spy.sz
    f_og = funnel("OGAP")
    _rpt = float(getattr(MN.get_risk_manager(), "_risk_per_trade", 0) or 0)
    f_pk = funnel("PARK")
    exp_pk = int(_rpt // 245)
    check("O10 the real funnel: OGAP (mark 2.45, a stray ogap_ask 2.55) -> 2 contracts on the mark at $500; PARK, same "
          "signal -> sized on the mark with the box's risk ($%.0f -> %d)" % (_rpt, exp_pk),
          f_og == [("OGAP", 2)] and (f_pk == [("PARK", exp_pk)] or (exp_pk < 1 and f_pk == [])),
          f"ogap={f_og} park={f_pk}")

    # ── O11 the dispatch asks OGAP ──
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    import utils.time_utils as _TU
    _calls = []
    _orig = MN._attempt_ogap
    MN._attempt_ogap = lambda ctx, ms, state, chain=None: _calls.append(("ogap", chain is not None))

    class _MS:
        adx, trend_direction, structure_sequence = 20.0, "NEUTRAL", ""

    class _Ch:
        calls, puts, spot = [], [], 600.0
    _st = MN.BotState()
    _st.paper_trading = True
    _pin = datetime(2026, 11, 5, 9, 49, 5, tzinfo=ZoneInfo("America/New_York"))
    _real = {"now_et": _TU.now_et, "now_utc": _TU.now_utc}
    _fake = {"now_et": lambda: _pin, "now_utc": lambda: _pin.astimezone(timezone.utc)}
    _sw = [(_m, _n) for _m in list(sys.modules.values()) for _n in _real
           if _m is not None and getattr(_m, _n, None) is _real[_n]]
    for _m, _n in _sw:
        setattr(_m, _n, _fake[_n])
    _err = ""
    try:
        MN.attempt_new_entry({"price": 600.0, "chain": _Ch(), "macro": {}, "symbol": "QQQ"}, _MS(), _st)
    except Exception as _e:                                     # noqa: BLE001
        _err = f"{type(_e).__name__}: {_e}"
    finally:
        MN._attempt_ogap = _orig
        for _m, _n in _sw:
            setattr(_m, _n, _real[_n])
    _cap = mn_src[mn_src.index("    if _cap_hit:\n        if not _adm_ok:"):]
    _cap = _cap[:_cap.index("    # ── Fetch options chain")]
    check("O11 DRIVEN: attempt_new_entry() asks _attempt_ogap WITH the chain; the capped branch asks nothing (r137)",
          ("ogap", True) in _calls and not _err and "_attempt_ogap(" not in _cap and "_attempt_park(" not in _cap
          and _cap.rstrip().endswith("return"),
          f"calls={_calls} err={_err}")

    # ── R1-R5 the replay ──
    for i, dd in enumerate(sorted(fx), 1):
        f = fx[dd]
        e = f["expect"]
        bars = {int(k): tuple(v) for k, v in f["bars"].items()}
        rd = OP.ogap_read(bars, f["prior_close"], now_min=e["fill"])
        side_ok = rd.get("status") == "signal" and rd["side"] == e["side"] and rd["signal"] == e["signal"] \
            and rd["fill"] == e["fill"] and rd["stale"] is False
        spot = bars[e["fill"]][0]
        rows = [K(s, 1.0, 1.1, e["side"], dd) for s in range(int(spot) - 5, int(spot) + 6)]
        k = OP.pick_strike(rows, spot)
        n = OP.contracts_for(f["entry_ask"])
        why, m, bid, _st = walk(f["entry_ask"], [tuple(t) for t in f["ticks"]])
        pnl = n * 100.0 * ((bid or 0.0) - f["entry_ask"])
        reason_map = {"floor (trail)": "ogap_trail", "floor (1.2x lock)": "ogap_lock", "14:00 sweep": "ogap_sweep_1400",
                      "15:45 bell": "ogap_close_1545"}
        check(f"R{i} replay QQQ {dd}: signal {OP.hhmm(e['signal'])} {e['side']}, strike {e['strike']}, "
              f"{e['contracts']} contract(s), {e['reason']} at {OP.hhmm(e['exit_min'])}, P&L {e['pnl']:+.2f}",
              side_ok and k is not None and float(k.strike) == float(e["strike"]) and n == e["contracts"]
              and why.startswith(reason_map.get(e["reason"], "?")) and m == e["exit_min"]
              and abs(pnl - float(e["pnl"])) <= 1.0,
              f"read={ {x: rd.get(x) for x in ('status', 'side', 'signal', 'fill', 'stale')} } strike="
              f"{getattr(k, 'strike', None)} n={n} exit={why[:40]}@{m} bid={bid} pnl={pnl:+.2f}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
