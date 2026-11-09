#!/usr/bin/env python3
"""
tests/check_gex_hold_close.py  v5.1
v5.1  2026-11-08  OTV5 r97 (RETIRE.5) — the GEX fly is cut in production (OFF in code); this checker flips it on to exercise its code until step 2 removes it.
v5.0  2026-11-03  OTV5 r73 (BFLY.17) — new. THE GEX PIN BUTTERFLY HOLDS TO THE CLOSE, HONOURS ITS VIX RULE, AND IS PICKIER AT
      THE DOOR. The operator, 2026-11-03: "For the GEX fly, I want no stop except hold to close, I want the VIX rule enforced
      & I want more discriminatory entries." strategy/gex_pin_butterfly v5.14, execution/exit_engine v5.14,
      strategy/management v5.5, config v5.13.
  V1  VIX 19.99 fires; 20.0 and 20.02 (AMZN 11-02's vix_at_entry, the fly that fired FULL size) do not - the plan HOLDs
      on `vix`, and the row carries the value
  V2  no VIX at all (no macro snapshot) is STARVED: no fly, the row names vix
  V3  data/macro_data's bands are unchanged: VIX 14.9 full size, 15.0 and 19.99 half size, 20.0 butterfly_allowed False
  N1  the 09:30 open inside yesterday's range fires; above the high or below the low HOLDs on open_in_prior_range; at the
      high itself is inside; an unread range is STARVED; the row carries prior_low / prior_high
  F1  THE FLOOR MOVES THE PICK: on a ladder whose best-R wing (1-wide, debit 12% of width) is under the 15.5% floor the
      plan takes the 2-wide (20%); with the floor off (0) it takes the 1-wide; wing_under_floor is on the row
  F2  every width under the floor -> DECLINE at wing_search, the reason naming the debit floor
  X1  _evaluate_butterfly: a GEXPinButterfly far below its old floor does not exit; an ATPButterfly at the same marks
      stops out (stop_hit)
  X2  evaluate(): the GEX pin fly never closes on decay and keeps no reading - also with DECAY_STOP_EXEMPT empty (what an
      OT_DECAY_STOP_EXEMPT list that omits it would set); an ATP fly on the same marks closes on decay
  X3  the 15:45 flatten still closes the GEX pin fly (is_hard_close_time and the clock at 15:46 ET)
  X4  the signal carries no premium stop (stop_loss_pct 1.0, stop_premium 0); management declares the flatten only
  R1  THE STUDY, THROUGH THE BUILT GATES: tests/fixtures/gex_r73_replay.json (the 80 first-per-symbol-day flies of
      ~/gex_study, 08-28..11-02: VIX as the row stamped it, the prior range from the warehouse 1m tape, the fly's debit and
      width) through vix_allows / open_in_prior_range / debit_passes_floor: 39 kept, all 5 outliers kept, every flag as
      the replay scored it
Mutation-tested: vix_allows with <= (20.0 fires) -> red at V1; open_in_prior_range always True -> red at N1, R1; the floor
check removed from the wing search -> red at F1, F2, R1 unaffected (R1 asks the function); the hold-to-close skip removed
from _evaluate_butterfly -> red at X1; from evaluate() -> red at X2.
Run:  python3 tests/check_gex_hold_close.py
"""
import json
import os
import sqlite3
import sys
import datetime as _dt
from zoneinfo import ZoneInfo

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
import config as _r97_cfg                                       # noqa: E402  r97 (RETIRE.5): the GEX fly is cut in production (OFF in code); this checker flips it on to exercise its code until step 2 removes it
_r97_cfg.GEX_BUTTERFLY_ENABLED = True
os.environ.setdefault("OT_PAPER_TRADING", "1")
os.environ["OT_RELAXED_ENTRY"] = "0"
ET = ZoneInfo("America/New_York")
FAILED = []
N = [0]


def check(label, cond, detail=""):
    N[0] += 1
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        FAILED.append(label.split()[0])


class _Store:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")

    def commit(self):
        self.conn.commit()


class _C:
    def __init__(self, k, mark, spread=0.001):
        self.strike, self.mark = float(k), float(mark)
        self.bid, self.ask = mark - spread, mark + spread
        self.delta, self.gamma, self.theta = 0.2, 0.01, -0.03
        self.expiry, self.symbol, self.open_interest = "x", f"O{k}", 100


class _Chain:
    def __init__(self, calls):
        self.calls, self.puts = calls, []


class _GEX:
    gex_environment, pin_strike, pin_concentration = "PINNING", 101.0, 0.60


def main():
    from strategy import plan as P
    st = _Store()
    P.bind_store(st)
    import derived.registry as _reg
    from derived.plan_ledger import PlanLedger
    _led = PlanLedger(st, "TST")
    _reg.plan_ledger = lambda symbol="": _led
    import config
    import strategy.gex_pin_butterfly as GB
    GB.ENABLED = True
    GB.EARLIEST_ET, GB.LATEST_ET = "09:30", "16:00"
    GB.PERSIST_TICKS = 1
    _em_real = GB.expected_move
    _fixed = GB.datetime(2026, 8, 27, 12, 30, tzinfo=ET)
    GB.expected_move = lambda u, iv, now=None: _em_real(u, iv, now=_fixed)
    INSIDE = (100.0, 95.0, 105.0)
    # the legs checker's B2 ladder: 100/101/102 at 0.40 (40% of width), 99/101/103 at 1.00 (50%) - both over the floor
    good = [_C(k, m) for k, m in ((99, 2.55), (100, 1.70), (101, 1.00), (102, 0.70), (103, 0.45))]
    tick = [100.0]

    def ask(chain=None, vix=17.0, prior=INSIDE, price=99.0, iv=0.90):
        tick[0] += 1.0
        P.begin_tick(tick[0])
        GB.GEXPinButterflyStrategy.PLAYED_PINS = set()
        b = GB.GEXPinButterflyStrategy()
        b.planner.symbol = "TST"
        sig = b.generate_signal(gex=_GEX(), price_now=price, now_et="12:30", atm_iv=iv, chain=_Chain(chain or good),
                                vix=vix, prior_range=prior)
        row = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='GEXPinButterfly' AND ts_epoch=?",
                              (tick[0],)).fetchone()
        chk = {r[0]: r[1] for r in st.conn.execute(
            "SELECT check_name, value FROM plan_check WHERE strategy='GEXPinButterfly' AND ts_epoch=?", (tick[0],))}
        return sig, row, chk

    # ── V: the VIX rule ──
    s1, r1, c1 = ask(vix=19.99)
    s2, r2, c2 = ask(vix=20.0)
    s3, r3, c3 = ask(vix=20.02)
    check("V1 VIX 19.99 fires; 20.0 and 20.02 (AMZN 11-02) HOLD on vix, the value on the row",
          s1 is not None and s2 is None and s3 is None and r2 and r2[0] == "HOLD" and "vix=" in (r2[1] or "")
          and r3 and r3[0] == "HOLD" and "vix=" in (r3[1] or "") and abs(float(c3.get("vix") or 0) - 20.02) < 1e-9,
          f"{s1 is not None} {r2} {r3} vix_row={c3.get('vix')}")
    saved = GB.vix_now
    GB.vix_now = lambda: None
    try:
        s4, r4, _ = ask(vix=None)
    finally:
        GB.vix_now = saved
    check("V2 no VIX (no macro snapshot) is STARVED: no fly, the row names vix",
          s4 is None and r4 and r4[0] == "NO PLAN" and "vix" in (r4[1] or ""), str(r4))
    import data.macro_data as MD
    bands = []
    for v in (14.9, 15.0, 19.99, 20.0):
        m = MD.MacroManager()
        m._fetch_vix = (lambda vv: (lambda: vv))(v)
        m._check_fed_day = lambda: (False, "")
        s = m._fetch()
        bands.append((v, s.butterfly_allowed, s.butterfly_half_size))
    check("V3 macro bands unchanged: 14.9 full, 15.0 / 19.99 half, 20.0 butterfly_allowed False",
          bands == [(14.9, True, False), (15.0, True, True), (19.99, True, True), (20.0, False, False)], str(bands))

    # ── N: the open inside yesterday's range ──
    n_in, _, cn = ask(prior=(100.0, 95.0, 105.0))
    n_hi, rh, _ = ask(prior=(105.5, 95.0, 105.0))
    n_lo, rl, _ = ask(prior=(94.5, 95.0, 105.0))
    n_eq, _, _ = ask(prior=(105.0, 95.0, 105.0))
    saved = GB.prior_range_read
    GB.prior_range_read = lambda _s, _d: None
    try:
        n_un, ru, _ = ask(prior=None)
    finally:
        GB.prior_range_read = saved
    check("N1 open inside fires; above the high / below the low HOLD on open_in_prior_range; at the high is inside; "
          "unread is STARVED; prior_low / prior_high on the row",
          n_in is not None and n_hi is None and n_lo is None and n_eq is not None
          and rh and rh[0] == "HOLD" and "open_in_prior_range" in (rh[1] or "")
          and rl and "open_in_prior_range" in (rl[1] or "") and n_un is None and ru and ru[0] == "NO PLAN"
          and "prior_range" in (ru[1] or "") and cn.get("prior_low") == 95.0 and cn.get("prior_high") == 105.0,
          f"{n_in is not None} {rh} {rl} {n_eq is not None} {ru} {cn.get('prior_low')} {cn.get('prior_high')}")

    # ── F: the cheap-fly floor ──
    # 1-wide 100/101/102: 1.60 - 2 + 0.52 = 0.12 (12% of width, R 7.33); 2-wide 99/101/103: 2.30 - 2 + 0.10 = 0.40 (20%, R 4)
    cheap = [_C(k, m) for k, m in ((99, 2.30), (100, 1.60), (101, 1.00), (102, 0.52), (103, 0.10))]
    f_on, _, cf = ask(chain=cheap)
    saved_floor = GB.MIN_DEBIT_PCT_WIDTH
    GB.MIN_DEBIT_PCT_WIDTH = 0.0
    try:
        f_off, _, _ = ask(chain=cheap)
    finally:
        GB.MIN_DEBIT_PCT_WIDTH = saved_floor
    w = lambda s: (float(s.upper_contract.strike) - float(s.center_contract.strike)) if s is not None else None
    check("F1 the floor moves the pick: best-R 1-wide (12%) is under it -> the 2-wide (20%); floor off -> the 1-wide; "
          "wing_under_floor on the row",
          w(f_on) == 2.0 and w(f_off) == 1.0 and abs(float(f_on.net_debit) - 0.40) < 1e-9
          and float(cf.get("wing_under_floor") or 0) == 1.0, f"on={w(f_on)} off={w(f_off)} under={cf.get('wing_under_floor')}")
    all_cheap = [_C(k, m) for k, m in ((99, 2.10), (100, 1.60), (101, 1.00), (102, 0.52), (103, 0.18))]
    f2, rf2, _ = ask(chain=all_cheap)
    check("F2 every width under the floor -> DECLINE at wing_search, naming the debit floor",
          f2 is None and rf2 and rf2[0] == "DECLINE" and "wing_search" in (rf2[1] or "")
          and "debit floor" in (rf2[1] or ""), str(rf2))

    # ── X: hold to the close ──
    import execution.exit_engine as XE
    _rhc = XE.is_hard_close_time
    XE.is_hard_close_time = lambda: False
    try:
        eng = XE.ExitEngine(paper_trading=True)

        def fly(tid, strat, **kw):
            r = {"trade_id": tid, "strategy": strat, "symbol": "TST", "is_butterfly": 1, "direction": "neutral",
                 "option_side": "call", "lower_strike": 100.0, "center_strike": 101.0, "upper_strike": 102.0,
                 "entry_premium": 0.40, "stop_premium": 0.24, "target_premium": 1.0, "contracts": 2,
                 "entry_time": "2026-11-03T13:30:00-05:00", "expiry": "2026-11-03", "status": "open"}
            r.update(kw)
            return r
        g = eng._evaluate_butterfly(fly("x1g", "GEXPinButterfly"), 0.05)
        a = eng._evaluate_butterfly(fly("x1a", "ATPButterfly"), 0.05)
        check("X1 _evaluate_butterfly: the GEX pin fly at 0.05 (old floor 0.24) holds; the ATP fly stops out",
              not g.should_exit and a.should_exit and "stop_hit" in (a.exit_reason or ""),
              f"gex={g.should_exit} {g.exit_reason} atp={a.should_exit} {a.exit_reason}")
        marks = [0.50, 0.60, 0.55, 0.41]                     # peak p 0.20, a fade to p 0.01: 95% off the peak
        saved_ex = config.DECAY_STOP_EXEMPT
        out = {}
        try:
            for ex in (saved_ex, ()):
                config.DECAY_STOP_EXEMPT = ex
                for strat in ("GEXPinButterfly", "ATPButterfly"):
                    e2 = XE.ExitEngine(paper_trading=True)
                    rec = fly(f"x2{strat[:3]}{len(ex)}", strat, stop_premium=0.0)
                    res = []
                    for m in marks:
                        d = e2.evaluate(rec, m)
                        rd = getattr(e2, "decay_reading", lambda _t: None)(rec["trade_id"])
                        res.append(("decay" in str(d.exit_reason or "")) if d.should_exit else False)
                        res.append(bool(rd))
                    out[(strat, len(ex))] = res
        finally:
            config.DECAY_STOP_EXEMPT = saved_ex
        gex_clean = all(not x for k, v in out.items() if k[0] == "GEXPinButterfly" for x in v)
        atp_decays = any(out[("ATPButterfly", len(saved_ex))][0::2])
        check("X2 evaluate(): the GEX pin fly never closes on decay and keeps no reading (also with DECAY_STOP_EXEMPT "
              "empty); the ATP fly on the same marks closes on decay", gex_clean and atp_decays, str(out))

        class _F(_dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return _dt.datetime(2026, 11, 3, 15, 46, tzinfo=ET)
        _rdt = XE.datetime
        XE.datetime, XE.is_hard_close_time = _F, (lambda: True)
        try:
            h = eng._evaluate_butterfly(fly("x3", "GEXPinButterfly", stop_premium=0.0), 0.30)
        finally:
            XE.datetime = _rdt
        check("X3 the 15:45 flatten still closes the GEX pin fly (hard close time, 15:46 ET)",
              h.should_exit and h.exit_reason and "stop" not in h.exit_reason, f"{h.should_exit} {h.exit_reason}")
    finally:
        XE.is_hard_close_time = _rhc
    from strategy.management import EXIT_CONDITIONS
    check("X4 the signal carries no premium stop (stop_loss_pct 1.0, stop_premium 0); management declares the "
          "flatten only",
          s1 is not None and abs(float(s1.stop_loss_pct) - 1.0) < 1e-9 and abs(float(s1.stop_premium())) < 1e-9
          and set(EXIT_CONDITIONS.get("GEXPinButterfly") or {}) == {"flatten"}
          and "GEXPinButterfly" in tuple(config.HOLD_TO_CLOSE_STRATEGIES),
          f"{s1 and s1.stop_loss_pct} {s1 and s1.stop_premium()} {EXIT_CONDITIONS.get('GEXPinButterfly')}")

    # ── R: the study through the built gates ──
    fx = json.load(open(os.path.join(_root, "tests", "fixtures", "gex_r73_replay.json"), encoding="utf-8"))
    bad, kept, out_kept, outl = [], 0, 0, 0
    for f in fx["flies"]:
        pr = tuple(f["prior"]) if f["prior"] else None
        keep = (GB.vix_allows(f["vix"]) and GB.open_in_prior_range(pr) is True
                and GB.debit_passes_floor(f["debit"], f["width"]))
        kept += keep
        outl += f["outlier"]
        out_kept += bool(keep and f["outlier"])
        if keep != f["keep"]:
            bad.append((f["day"], f["sym"]))
    check(f"R1 the study's {len(fx['flies'])} flies through the built gates: 39 kept, all 5 outliers kept, every flag as "
          "scored", not bad and kept == 39 and outl == 5 and out_kept == 5,
          f"kept={kept} outliers={out_kept}/{outl} mismatches={bad[:6]}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print(f"\nGREEN — {N[0]} of {N[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
