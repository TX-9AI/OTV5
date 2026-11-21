#!/usr/bin/env python3
"""
tests/check_ogap_mark.py  v5.0
v5.0  2026-11-21  OTV5 r136 (OGAP.3) — OGAP READS THE MARK WHEREVER PARK'S SPEC READS THE ASK OR THE BID. The operator,
      2026-11-20: "Ours needs the modification to account for how I would trade it, never pay the spread." / "Mark is
      the worst buy or sell we accept." Every case below is built so the ask / bid reading and the mark reading give
      DIFFERENT answers, so the gate is red on r135 (ask in, bid out) and green on r136. OT_RISK_USD is pinned to 1050
      (the operator's size). The clock of _evaluate_ogap is pinned through exit_engine's `datetime` seam.

M1   the plan sizes on the mark: bid 3.40 / ask 3.60 at the 11-05 fill minute -> entry_premium 3.50, contracts
     floor(1050 / 350) = 3 (the ask would buy 2); the signal carries no ogap_ask; notes carry mark=3.50
M2   the 0.50 floor reads the mark: bid 0.46 / ask 0.52 (mark 0.49) -> no signal (the ask 0.52 would trade);
     bid 0.50 / ask 0.52 (mark 0.51) -> a signal
M3   the band reads the mark: bid 10.40 / ask 10.60 (mark 10.50) -> 1 contract on $1050 (the ask buys 0);
     bid 10.50 / ask 10.54 (mark 10.52) -> no signal
M4   the FIRE line names the mark first: "@ mark 3.50 (bid 3.40, ask 3.60)", "exits on the mark"
M5   the real funnel (main._execute_entry_signal, real RiskManager, spy entry engine): the M1 signal -> 3; an OGAP
     signal at mark 3.50 carrying a stray ogap_ask 3.60 -> 3 (never read); PARK at the same mark -> the box's risk
     on the mark (3), unchanged
M6   fill basis: ogap_fill_of = the booked entry_premium 4.65 though entry_ask 4.66 and notes ask=4.66 are on the row
M7   peak on the mark: _evaluate_ogap at 10:40 with mark 6.00 / bid 5.80 -> state peak 6.00
M8   the 1.6x lock on the mark (fill 4.65: arm 7.44, floor 5.58): mark 7.45 / bid 7.30 arms; then mark 5.58 / bid
     5.50 exits ogap_lock (on the bid vs the ask the lock never armed: 7.30 < 7.456)
M9   no exit while the MARK is above the floor though the bid is below it: arm at mark 7.50 / bid 7.48, then mark
     5.62 / bid 5.50 -> hold (the bid would sell at 5.50 <= 5.592)
M10  the 2.0x trail on the mark (11-20 shape): mark 9.32 / bid 9.20 -> floor 0.60 x 9.32 = 5.592; mark 5.59 / bid
     5.44 -> ogap_trail (the bid path never armed the trail: 9.20 < 9.32)
M11  the 14:00 sweep on the mark: mark 3.49 / bid 3.45 at 14:00 -> no sweep (3.49 >= 0.75 x 4.65 = 3.4875; the bid
     would sweep), checked once (14:01 mark 3.00 -> hold); another trade at mark 3.48 / bid 3.47 -> ogap_sweep_1400
M12  the 15:45 bell still sells; the restart seed (max_premium_seen 7.50) arms the lock on the fill 4.65 and the mark
     5.58 exits though the bid 5.60 sits above the bid path's floor 5.592
M13  the ogap_exit counterfactual row: basis "mark", fill 4.65, the mark that decided, the bid beside it
M14  no code outside tests reads or writes `ogap_ask`; Park's numbers are unchanged (0.50, 1.6, 1.2, 2.0, 0.60,
     (14, 0), 0.75, (15, 45)) and no OT_OGAP* key exists
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
"""
import ast
import json
import os
import re
import sys
import tempfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_ogap_mark_")
for _k, _v in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"),
               ("OT_LOG_FILE", "bot.log"), ("OT_SIGNAL_JOURNAL_DIR", "sj")):
    os.environ[_k] = os.path.join(_TD, _v)
CF = os.path.join(_TD, "cf")
os.environ["OT_COUNTERFACTUAL_DIR"] = CF
os.environ["OT_INSTRUMENT"] = "QQQ"
os.environ["OT_RISK_USD"] = "1050"          # the operator's size ("I like 1050 for most trades")
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


def main():
    try:
        import config
        from strategy import ogap_plan as OP
        from strategy.ogap import Ogap
        from execution import exit_engine as EE
        import main as MN
        from strategy.base_strategy import OptionsSignal
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN — imports failed: {type(exc).__name__}: {exc}")
        return 2
    if float(config.RISK_PER_TRADE_USD) != 1050.0:
        print(f"RED — OT_RISK_USD=1050 did not reach config (RISK_PER_TRADE_USD {config.RISK_PER_TRADE_USD})")
        return 1

    fx = json.load(open(FIX))
    d = "2026-11-05"
    day = date.fromisoformat(d)
    bars = {int(k): tuple(v) for k, v in fx[d]["bars"].items()}
    fill = fx[d]["expect"]["fill"]
    spot = bars[fill][0]
    spec = Ogap()

    def sig_at(bid, ask):
        return spec.generate_signal(price_now=spot, now_et=OP.hhmm(fill), chain=Chain(d, round(spot), bid, ask),
                                    day=day, symbol="QQQ", bars=bars, prior_close=fx[d]["prior_close"])

    # ── M1 size on the mark ──
    s1 = sig_at(3.40, 3.60)
    check("M1 the plan at bid 3.40 / ask 3.60 -> entry_premium 3.50, 3 contracts (the ask buys 2), no ogap_ask, "
          "notes mark=3.50",
          s1 is not None and abs(float(s1.entry_premium) - 3.50) < 1e-9 and getattr(s1, "ogap_contracts", None) == 3
          and getattr(s1, "ogap_ask", None) is None and "mark=3.50" in str(getattr(s1, "notes", "")),
          f"sig={s1 and (s1.entry_premium, getattr(s1, 'ogap_contracts', None), getattr(s1, 'ogap_ask', None), s1.notes)}")

    # ── M2 the 0.50 floor ──
    s2a, s2b = sig_at(0.46, 0.52), sig_at(0.50, 0.52)
    check("M2 the 0.50 floor on the mark: mark 0.49 (ask 0.52) -> none; mark 0.51 -> a signal",
          s2a is None and s2b is not None, f"0.49={s2a} 0.51={s2b}")

    # ── M3 the band ──
    s3a, s3b = sig_at(10.40, 10.60), sig_at(10.50, 10.54)
    check("M3 the band on the mark at $1050: mark 10.50 (ask 10.60) -> 1 contract; mark 10.52 -> none",
          s3a is not None and getattr(s3a, "ogap_contracts", None) == 1 and s3b is None,
          f"10.50={s3a and getattr(s3a, 'ogap_contracts', None)} 10.52={s3b}")

    # ── M4 the FIRE line ──
    prep = spec.prepare(price_now=spot, now_et=OP.hhmm(fill), chain=Chain(d, round(spot), 3.40, 3.60), day=day,
                        symbol="QQQ", bars=bars, prior_close=fx[d]["prior_close"])
    tl = prep.trade_line() if prep is not None and getattr(prep, "ready", False) else ""
    check("M4 the FIRE line: '@ mark 3.50 (bid 3.40, ask 3.60)' and 'exits on the mark'",
          "@ mark 3.50 (bid 3.40, ask 3.60)" in tl and "exits on the mark" in tl, tl)

    # ── M5 the real funnel ──
    class _Spy:
        def __init__(self):
            self.sz = []

        def enter(self, signal=None, sizing=None, **kw):
            self.sz.append((getattr(signal, "strategy_name", "?"), getattr(sizing, "contracts", None)))
            return None

    class _State:
        paper_trading = True

    def funnel(sg):
        spy = _Spy()
        _ge = MN.get_entry_engine
        MN.get_entry_engine = lambda *a, **kw: spy
        try:
            MN._execute_entry_signal(sg, {"price": 600.0, "macro": type("M", (), {"butterfly_half_size": False})()},
                                     None, _State(), None, additive=True)
        finally:
            MN.get_entry_engine = _ge
        return spy.sz

    def mk(name, mark, stray_ask=None):
        sg = OptionsSignal(strategy_name=name, setup_type="ogap_long", direction="long", option_side="call",
                           underlying_entry=600.0, underlying_stop=0.0, strike=600.0, entry_premium=mark,
                           stop_loss_pct=1.0)
        if stray_ask is not None:
            sg.ogap_ask = stray_ask
        return sg
    f_plan = funnel(s1) if s1 is not None else None
    f_stray = funnel(mk("OGAP", 3.50, 3.60))
    f_park = funnel(mk("PARK", 3.50))
    check("M5 the real funnel at $1050: the plan's signal (mark 3.50) -> 3; OGAP mark 3.50 with a stray ogap_ask 3.60 "
          "-> 3; PARK mark 3.50 -> 3 (unchanged)",
          f_plan == [("OGAP", 3)] and f_stray == [("OGAP", 3)] and f_park == [("PARK", 3)],
          f"plan={f_plan} stray={f_stray} park={f_park}")

    # ── the exits, through _evaluate_ogap with the clock pinned ──
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
    _real_dt = EE.datetime
    _clock = {"t": None}

    class _FakeDT(_real_dt):
        @classmethod
        def now(cls, tz=None):
            t = _clock["t"]
            return t if tz is None else t.astimezone(tz)

    def at(hh, mm):
        _clock["t"] = _real_dt(2026, 11, 20, hh, mm, 5, tzinfo=_ET)

    _hc = EE.is_hard_close_time
    EE.datetime = _FakeDT
    EE.is_hard_close_time = lambda: False
    eng = EE.ExitEngine()

    def rec(tid, **kw):
        r = {"trade_id": tid, "strategy": "OGAP", "symbol": "QQQ", "entry_premium": 4.65, "entry_ask": 4.66,
             "entry_bid": 4.64, "contracts": 2, "notes": "ogap gap=0.1 mark=4.65 ask=4.66 bid=4.64",
             "option_symbol": "QQQ  261120P00633000"}
        r.update(kw)
        return r

    def tick(r, hh, mm, mark, bid):
        at(hh, mm)
        r["_exit_bid"] = bid
        return eng._evaluate_ogap(r, mark)

    try:
        # M6
        check("M6 fill basis = the booked entry_premium 4.65 (entry_ask 4.66 and notes ask=4.66 on the row)",
              abs(EE.ogap_fill_of(rec("m6")) - 4.65) < 1e-9, f"{EE.ogap_fill_of(rec('m6'))}")
        # M7
        r7 = rec("m7")
        d7 = tick(r7, 10, 40, 6.00, 5.80)
        st7 = r7.get("_ogap_state") or {}
        check("M7 peak on the mark: mark 6.00 / bid 5.80 -> peak 6.00, no exit",
              abs(float(st7.get("peak") or 0) - 6.00) < 1e-9 and not d7.should_exit, f"{st7} {d7.exit_reason}")
        # M8
        r8 = rec("m8")
        d8a = tick(r8, 10, 45, 7.45, 7.30)
        d8b = tick(r8, 10, 50, 5.58, 5.50)
        check("M8 the 1.6x lock on the mark: mark 7.45 arms (bid 7.30 would not), mark 5.58 <= floor 5.58 -> ogap_lock",
              not d8a.should_exit and d8b.should_exit and str(d8b.exit_reason).startswith("ogap_lock"),
              f"{d8a.exit_reason!r} {d8b.exit_reason!r} st={r8.get('_ogap_state')}")
        # M9
        r9 = rec("m9")
        d9a = tick(r9, 10, 45, 7.50, 7.48)
        d9b = tick(r9, 10, 50, 5.62, 5.50)
        check("M9 the mark 5.62 above the floor 5.58 holds though the bid 5.50 is below it",
              not d9a.should_exit and not d9b.should_exit, f"{d9a.exit_reason!r} {d9b.exit_reason!r}")
        # M10
        r10 = rec("m10")
        d10a = tick(r10, 11, 0, 9.32, 9.20)
        d10b = tick(r10, 11, 30, 5.59, 5.44)
        st10 = r10.get("_ogap_state") or {}
        check("M10 the 2.0x trail on the mark: peak 9.32 -> floor 5.592; mark 5.59 -> ogap_trail (the bid never "
              "armed it)",
              not d10a.should_exit and d10b.should_exit and str(d10b.exit_reason).startswith("ogap_trail")
              and abs(float(st10.get("floor") or 0) - 0.60 * 9.32) < 1e-9,
              f"{d10a.exit_reason!r} {d10b.exit_reason!r} st={st10}")
        # M11
        r11 = rec("m11")
        d11a = tick(r11, 14, 0, 3.49, 3.45)
        d11b = tick(r11, 14, 1, 3.00, 2.90)
        r11c = rec("m11c")
        d11c = tick(r11c, 14, 0, 3.48, 3.47)
        check("M11 the 14:00 sweep on the mark: mark 3.49 holds (bid 3.45 would sweep), once only (14:01 mark 3.00 "
              "holds); mark 3.48 -> ogap_sweep_1400",
              not d11a.should_exit and not d11b.should_exit and d11c.should_exit
              and str(d11c.exit_reason).startswith("ogap_sweep_1400"),
              f"{d11a.exit_reason!r} {d11b.exit_reason!r} {d11c.exit_reason!r}")
        # M12
        r12 = rec("m12")
        d12 = tick(r12, 15, 45, 4.70, 4.60)
        r12b = rec("m12b", max_premium_seen=7.50)
        d12b = tick(r12b, 12, 0, 5.58, 5.60)
        check("M12 the 15:45 bell sells; the restart seed 7.50 arms the lock on 4.65 and the mark 5.58 exits (bid 5.60 "
              "is above the bid path's 5.592)",
              d12.should_exit and str(d12.exit_reason) == "ogap_close_1545" and d12b.should_exit
              and str(d12b.exit_reason).startswith("ogap_lock"),
              f"{d12.exit_reason!r} {d12b.exit_reason!r}")
        # M13
        rows = []
        try:
            with open(os.path.join(CF, "ogap_exit.jsonl")) as fh:
                rows = [json.loads(x) for x in fh if x.strip()]
        except OSError:
            pass
        r13 = [x for x in rows if x.get("trade_id") == "m10"]
        check("M13 the ogap_exit row: basis mark, fill 4.65, mark 5.59, bid 5.44 beside it",
              len(r13) == 1 and r13[0].get("basis") == "mark" and abs(float(r13[0].get("fill") or 0) - 4.65) < 1e-9
              and abs(float(r13[0].get("mark") or 0) - 5.59) < 1e-9 and abs(float(r13[0].get("bid") or 0) - 5.44) < 1e-9,
              f"{r13}")
    finally:
        EE.datetime = _real_dt
        EE.is_hard_close_time = _hc

    # ── M14 source ──
    hits = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [x for x in dn if x not in (".git", "venv", "tests", "docs", "__pycache__", "data", "logs")]
        for n in fn:
            if not n.endswith(".py"):
                continue
            path = os.path.join(dp, n)
            try:
                tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
            except SyntaxError:
                continue
            for nd in ast.walk(tree):
                if (isinstance(nd, ast.Attribute) and nd.attr == "ogap_ask") or \
                        (isinstance(nd, ast.Constant) and nd.value == "ogap_ask") or \
                        (isinstance(nd, ast.Constant) and isinstance(nd.value, str)
                         and re.fullmatch(r"OT_OGAP\w*", nd.value)):
                    hits.append(f"{os.path.relpath(path, ROOT)}:{nd.lineno}")
    nums = (config.OGAP_MIN_ASK, config.OGAP_LOCK_ARM, config.OGAP_LOCK_FLOOR, config.OGAP_TRAIL_ARM,
            config.OGAP_TRAIL_KEEP, tuple(config.OGAP_SWEEP_ET), config.OGAP_SWEEP_BELOW, tuple(config.OGAP_CLOSE_ET))
    check("M14 no code reads or writes ogap_ask, no OT_OGAP* key; Park's numbers unchanged",
          not hits and nums == (0.50, 1.6, 1.2, 2.0, 0.60, (14, 0), 0.75, (15, 45)), f"hits={hits} nums={nums}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
