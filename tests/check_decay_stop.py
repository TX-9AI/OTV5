#!/usr/bin/env python3
"""
tests/check_decay_stop.py  v5.1
v5.1  2026-10-31  OTV5 r68 (CFG.5) — OT_RESTING_STOP_STATE leaves the scratch env: the resting stop and its state file are deleted
      (the operator, 2026-10-31: "Resting stop was a study. It failed. Get this the fuck out of here"). No check changed.
v5.0  2026-10-30  OTV5 r58 (DECAY.1) — THE PEAK-DECAY PROFIT STOP. A TRADING CHANGE, ordered live for Monday 2026-11-02 under
      the operator's explicit override of the benchmark freeze: "I'm thinking like some kind of stop that says we've decayed
      20% from the peak so cut it" ... "I want the decay stop running by Monday". The rule (the study's "V0 B X30 arm+5,
      Runaway exempt", ~/reviews/decay coupled.py / hist.py): p = open profit per unit premium, favourable-positive
      (debit incl. butterfly net: mark - entry; credit: entry - cost to close); armed once peak_p >= 0.05 x entry;
      armed, close when p <= peak_p x (1 - 0.30); every existing exit first; RunawayContinuation exempt, and PARK by default (OT_DECAY_STOP_EXEMPT, after the
      10-30 scoring: the decay stop cut PARK's all-afternoon winners).
      Driven through the REAL ExitEngine.evaluate, the REAL ManagementPlan.decide / _one and the REAL
      PositionManager._fetch_current_premium (butterfly net); only the clock (exit_engine.now_et, is_hard_close_time)
      is pinned and strategy.plan.write_row is captured. THE WALL CLOCK IS PINNED TO 10:05 ET (utils.time_utils.datetime,
      and exit_engine.datetime; as tests/check_tcs_shadow.py pins its manage ticks): the lander runs CHECKs at whatever time it is, and after 15:45 ET
      the real hard close would pre-empt every decay tick here.

  C1  config: DECAY_STOP on, DECAY_STOP_X 0.30, DECAY_STOP_ARM 0.05, DECAY_STOP_EXEMPT ("RunawayContinuation", "PARK");
      OT_DECAY_STOP=0 / OT_DECAY_STOP_X / OT_DECAY_STOP_ARM / OT_DECAY_STOP_EXEMPT read from the environment (a fresh
      interpreter; OT_DECAY_STOP_EXEMPT=RunawayContinuation -> ("RunawayContinuation",))
  A1  a debit peaking at +4.5% of entry never arms, and a full fade from there never fires
  A2  a peak of exactly +5% arms (and +4.99% does not)
  A3  no fire before arming: p falling to 0 before the peak reached +5% holds
  F1  armed at a peak of p 0.20: a fade to p 0.142 (29%) holds, p 0.140 (exactly 30%) CLOSES
  F2  the reason carries the numbers: "decay: open profit +$140.00 (p 0.140) fell 30% from peak +$200.00 (p 0.200),
      armed at 10:05:00 pnl=7.0%"; condition parsers read "decay"; ExitDecision pnl = p / entry and p x contracts x 100
  K1  credit vertical: mark = cost to close, p = entry - mark: a FALLING cost arms and a rebound of 30% of the
      captured credit closes; a RISING cost (a loss) never arms
  B1  butterfly: position_manager prices the net lower + upper - 2 x center, and the decay p is that net - entry;
      the 29% / 30% boundary on the butterfly
  R1  RunawayContinuation: the same path that closes a Breakout does not close it, and no reading is kept
  R2  PARK is exempt by default (no decay close, no reading); with DECAY_STOP_EXEMPT = ("RunawayContinuation",) (what
      OT_DECAY_STOP_EXEMPT=RunawayContinuation sets) the same PARK path closes on decay
  O1  DECAY_STOP off (config.DECAY_STOP = False, what OT_DECAY_STOP=0 sets): the closing path holds, no reading
  E1  an existing exit firing the same tick wins: the engine's stop_hit keeps its reason; the reading says
      "existing exit fired first" and decay_fired = 0
  E2  management.decide: its hard_stop spec exit wins over a decay that would fire the same tick
  P1  restart: a fresh engine on a rehydrated record (max_premium_seen persisted) closes at the 30% fade of the
      persisted peak, "armed at n/a (before a restart)"
  S1  study parity: on 300 random 15 s paths per orientation the first closing tick equals the study's walk() + rule_B
      (copied verbatim from ~/reviews/decay/coupled.py), Runaway excluded
  M1  management.decide on a Breakout: CLOSE condition "decay" on the 30% tick, plan check rows decay_peak_p /
      decay_p / decay_armed / decay_frac / decay_fired on every tick, decay_fired 1 only on the closing tick
  M2  management._one (a record the plan does not cover): the decay_* rows from the running engine's reading
  H1  a SHADOW TCS (r57 TCS.LOG1: execution/shadow_book, its own ExitEngine and ManagementPlan through position_manager's
      _manage_one): the same 30% fade closes it on the shadow store with the decay reason

Born red on 7c5aad6 at C1, A2, F1, F2, K1, B1, R2, E1, P1, S1, M1, M2 and H1 (A1, A3, R1, O1 and E2 pass there: no decay exit exists).
Run:  python3 tests/check_decay_stop.py
"""
import datetime as D
import logging
import os
import random
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_s = tempfile.mkdtemp(prefix="check_decay_stop.")
for _k, _v in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived.db"), ("OT_RESTING_DB", "resting.db"),
               ("OT_FEED_DB", "feed.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(_s, _v)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
for _k in ("OT_DECAY_STOP", "OT_DECAY_STOP_X", "OT_DECAY_STOP_ARM", "OT_DECAY_STOP_EXEMPT"):
    os.environ.pop(_k, None)
try:
    import utils.time_utils as _tu                              # noqa: E402
    _REAL_DT = _tu.datetime

    class _Pinned(_REAL_DT):
        @classmethod
        def now(cls, tz=None):
            t = _REAL_DT.now(_tu.ET).replace(hour=10, minute=5, second=0, microsecond=0)
            return t.astimezone(tz) if tz is not None else t.replace(tzinfo=None)
    _tu.datetime = _Pinned
    import config                                               # noqa: E402
    from execution import exit_engine as XE                     # noqa: E402
    import strategy.management as M                             # noqa: E402
    import strategy.plan as PL                                  # noqa: E402
except Exception as exc:                                        # noqa: BLE001
    print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
    sys.exit(2)

logging.disable(logging.CRITICAL)
ET = ZoneInfo("America/New_York")
FAILED = []
NOW = D.datetime(2026, 10, 29, 10, 5, 0, tzinfo=ET)
XE.now_et = lambda: NOW
XE.is_hard_close_time = lambda *a, **k: False
XE.datetime = _Pinned            # exit_engine reads its own `datetime` (PARK's 15:45 close, _eod_due): 10:05 ET too


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def rec(tid, strategy="Breakout", **kw):
    r = {"trade_id": tid, "symbol": "QQQ", "strategy": strategy, "setup_type": "x", "direction": "long",
         "option_side": "call", "contracts": 10, "entry_premium": 2.00, "stop_premium": 1.50, "target_premium": 0.0,
         "trail_activation": 3.0, "underlying_entry": 720.0, "underlying_stop": 0.0, "underlying_target": 725.0,
         "status": "open", "is_butterfly": 0, "is_condor_leg": 0, "trail_stop": 0.0, "orb_range_high": 0.0,
         "orb_range_low": 0.0, "entry_time": "2026-10-29T13:40:04+00:00", "strike": 720.0}
    r.update(kw)
    return r


def credit_rec(tid, **kw):
    r = rec(tid, "TrendCreditSpread", option_side="put", direction="long", is_credit_vertical=1, is_condor_leg=1,
            short_strike=715.0, long_strike=710.0, entry_premium=1.00, stop_premium=2.00,
            short_symbol="QQQ   261030P00715000", long_symbol="QQQ   261030P00710000")
    r.update(kw)
    return r


def fly_rec(tid, **kw):
    r = rec(tid, "GEXPinButterfly", is_butterfly=1, direction="neutral", lower_strike=715.0, center_strike=720.0,
            upper_strike=725.0, entry_premium=1.00, stop_premium=0.50)
    r.update(kw)
    return r


def run(r, marks, eng=None):
    eng = eng or XE.ExitEngine(paper_trading=True)
    out = []
    for m in marks:
        d = eng.evaluate(r, m)
        rd = getattr(eng, "decay_reading", lambda _t: None)(r["trade_id"])
        out.append((d, rd))
    return out


def closes(out):
    return [bool(d.should_exit) for d, _ in out]


def is_decay(d):
    return bool(d.should_exit) and str(d.exit_reason or "").startswith("decay:")


print("check_decay_stop (DECAY.1)")

# ── C1 config ────────────────────────────────────────────────────────────────────────────────────────
_env = dict(os.environ, OT_DECAY_STOP="0", OT_DECAY_STOP_X="0.25", OT_DECAY_STOP_ARM="0.10",
            OT_DECAY_STOP_EXEMPT=" RunawayContinuation ")
_p = subprocess.run([sys.executable, "-c", "import config as c; print(c.DECAY_STOP, c.DECAY_STOP_X, c.DECAY_STOP_ARM, "
                     "'|'.join(c.DECAY_STOP_EXEMPT))"],
                    cwd=ROOT, env=_env, capture_output=True, text=True)
check("C1 config: defaults on / 0.30 / 0.05 / Runaway + PARK exempt, and OT_DECAY_STOP=0 / _X / _ARM / _EXEMPT from the env",
      getattr(config, "DECAY_STOP", None) is True and getattr(config, "DECAY_STOP_X", None) == 0.30
      and getattr(config, "DECAY_STOP_ARM", None) == 0.05
      and tuple(getattr(config, "DECAY_STOP_EXEMPT", ()) or ()) == ("RunawayContinuation", "PARK")
      and _p.stdout.split() == ["False", "0.25", "0.1", "RunawayContinuation"],
      f"defaults {getattr(config, 'DECAY_STOP', None)} {getattr(config, 'DECAY_STOP_X', None)} "
      f"{getattr(config, 'DECAY_STOP_ARM', None)}; env -> {_p.stdout.strip() or _p.stderr.strip()[-200:]}")

# ── A arming ─────────────────────────────────────────────────────────────────────────────────────────
a1 = run(rec("a1"), [2.05, 2.09, 2.00, 1.90, 1.80])                     # peak +4.5%, then a full fade
check("A1 a peak of +4.5% never arms: the full fade holds", closes(a1) == [False] * 5, f"{closes(a1)}")
a2 = run(rec("a2"), [2.10, 2.07, 2.069])                                 # peak exactly +5% (p 0.10): out at <= 0.07
a2b = run(rec("a2b"), [2.0998, 2.06, 2.00])                              # +4.99%: never armed
check("A2 a peak of exactly +5% arms (closes at the 30% fade) and +4.99% does not",
      closes(a2) == [False, True, True] and is_decay(a2[1][0]) and closes(a2b) == [False, False, False]
      and bool((a2[0][1] or {}).get("armed")) and not (a2b[2][1] or {}).get("armed", False),
      f"+5% {closes(a2)} {a2[1][0].exit_reason!r}; +4.99% {closes(a2b)}")
a3 = run(rec("a3"), [2.04, 2.02, 2.00, 1.98, 2.06])                      # never reached +5% before falling
check("A3 no fire before arming: falling from +2% to -1% holds", closes(a3) == [False] * 5, f"{closes(a3)}")

# ── F fade boundary + reason ─────────────────────────────────────────────────────────────────────────
f1 = run(rec("f1"), [2.10, 2.20, 2.15, 2.142, 2.14])
check("F1 armed, peak p 0.20: 25% / 29% fades hold, exactly 30% (p 0.140) CLOSES",
      closes(f1) == [False, False, False, False, True] and is_decay(f1[4][0]), f"{closes(f1)}")
rs = str(f1[4][0].exit_reason or "")
check("F2 the reason carries the numbers; condition 'decay'; pnl = p / entry and p x contracts x 100",
      rs == "decay: open profit +$140.00 (p 0.140) fell 30% from peak +$200.00 (p 0.200), armed at 10:05:00 pnl=7.0%"
      and rs.split(" ")[0].split(":")[0] == "decay" and rs.split(" pnl=")[0].split(":")[0] == "decay"
      and abs(f1[4][0].current_pnl_pct - 0.07) < 1e-9 and abs(f1[4][0].current_pnl_usd - 140.0) < 1e-6,
      repr(rs))

# ── K credit orientation ─────────────────────────────────────────────────────────────────────────────
k1 = run(credit_rec("k1"), [0.98, 0.90, 0.80, 0.85, 0.858, 0.86])        # cost falls to 0.80 (p 0.20), rebounds
k2 = run(credit_rec("k2"), [1.02, 1.10, 1.20, 1.15, 1.10])                # cost rises: a loss, never armed
check("K1 credit: cost to close falling arms; the 30% rebound (cost 0.86, p 0.140) closes; a rising cost never arms",
      closes(k1) == [False, False, False, False, False, True] and is_decay(k1[5][0])
      and "(p 0.140) fell 30% from peak +$200.00 (p 0.200)" in str(k1[5][0].exit_reason)
      and not any(is_decay(d) for d, _ in k2) and not any((rd or {}).get("armed") for _, rd in k2)
      and bool((k1[5][1] or {}).get("credit")),
      f"{closes(k1)} {k1[5][0].exit_reason!r} rising {[d.exit_reason for d, _ in k2]}")

# ── B butterfly net ──────────────────────────────────────────────────────────────────────────────────
try:
    from execution.position_manager import PositionManager

    class _C:
        def __init__(self, k, m):
            self.strike, self.mark, self.bid, self.ask, self.iv = k, m, m - 0.01, m + 0.01, 0.2

    class _Chain:
        def __init__(self, lo, ce, up):
            self.calls = [_C(715.0, lo), _C(720.0, ce), _C(725.0, up)]
            self.puts = []
            self.spot_price = 720.0
    _pm = PositionManager.__new__(PositionManager)
    _nets = [PositionManager._fetch_current_premium(_pm, fly_rec("bq"), _Chain(lo, ce, up))
             for lo, ce, up in ((6.0, 2.6, 0.3), (6.2, 2.6, 0.2), (6.2, 2.629, 0.2), (6.2, 2.63, 0.2))]
except Exception as exc:                                     # noqa: BLE001
    _nets = [None]
    print(f"    (butterfly pricing not reachable: {exc})")
_nets_r = [round(x, 4) if x is not None else None for x in _nets]
b1 = run(fly_rec("b1"), _nets_r) if None not in _nets_r else []
check("B1 butterfly: the mark is the net lower + upper - 2 x center; p = net - entry; 29% holds, 30% closes",
      _nets_r == [1.10, 1.20, 1.142, 1.14] and [is_decay(d) for d, _ in b1] == [False, False, False, True]
      and abs((b1[2][1] or {}).get("p", 9) - 0.142) < 1e-9 and abs((b1[2][1] or {}).get("peak_p", 9) - 0.20) < 1e-9,
      f"nets {_nets_r} decays {[is_decay(d) for d, _ in b1]} reading {b1[2][1] if b1 else None}")

# ── R exempt, O off ──────────────────────────────────────────────────────────────────────────────────
r1 = run(rec("r1", "RunawayContinuation", stop_premium=1.0), [2.10, 2.20, 2.15, 2.14, 2.10])
check("R1 RunawayContinuation: the path that closes a Breakout holds, no decay reading",
      not any(is_decay(d) for d, _ in r1) and all(rd is None for _, rd in r1), f"{[d.exit_reason for d, _ in r1]}")
_park = [2.10, 2.20, 2.15, 2.14]
r2a = run(rec("r2a", "PARK"), _park)
_wx = getattr(config, "DECAY_STOP_EXEMPT", None)
config.DECAY_STOP_EXEMPT = ("RunawayContinuation",)
try:
    r2b = run(rec("r2b", "PARK"), _park)
finally:
    config.DECAY_STOP_EXEMPT = _wx
check("R2 PARK exempt by default; with OT_DECAY_STOP_EXEMPT=RunawayContinuation the same PARK path closes on decay",
      not any(is_decay(d) for d, _ in r2a) and all(rd is None for _, rd in r2a)
      and [is_decay(d) for d, _ in r2b] == [False, False, False, True],
      f"default {[d.exit_reason for d, _ in r2a]} eligible {[d.exit_reason for d, _ in r2b]}")
_was = getattr(config, "DECAY_STOP", None)
config.DECAY_STOP = False
try:
    o1 = run(rec("o1"), [2.10, 2.20, 2.15, 2.14, 2.10])
finally:
    config.DECAY_STOP = _was
check("O1 DECAY_STOP off: the closing path holds, no reading",
      not any(is_decay(d) for d, _ in o1) and all(rd is None for _, rd in o1), f"{[d.exit_reason for d, _ in o1]}")

# ── E existing exits win ─────────────────────────────────────────────────────────────────────────────
e1 = run(rec("e1"), [2.10, 2.20, 1.40])
rd_e1 = e1[2][1] or {}
check("E1 the engine's stop_hit on the same tick wins; the reading says so and decay_fired = 0",
      e1[2][0].should_exit and str(e1[2][0].exit_reason).startswith("stop_hit")
      and rd_e1.get("would_fire") is True and rd_e1.get("fired") is False
      and "existing exit fired first" in str(rd_e1.get("note", "")),
      f"{e1[2][0].exit_reason!r} {rd_e1.get('note')}")

ROWS = []
_orig_write = PL.write_row


def _capture(store, symbol, ts, strategy, verdict, reason, direction="", trigger=None, invalidation=None,
             underlying=None, r=None, checks=None, check_notes=None):
    ROWS.append({"strategy": strategy, "verdict": verdict, "reason": reason, "checks": dict(checks or {}),
                 "notes": dict(check_notes or {})})
    return True


def decide_run(eng, r, marks):
    plan = M.get_management_plan()
    out = []
    for m in marks:
        ROWS.clear()
        it = plan.decide(r, m, df_1m=None, open_records=[r], current_price=720.0, ctx={}, exit_engine=eng)
        mine = [x for x in ROWS if x["strategy"] == f"{r['strategy']}/manage"]
        out.append((it, mine[-1] if mine else None))
    return out


_saved = (config.BRK_NOPROG_MODE, config.BRK_DFLOOR_MODE)
config.BRK_NOPROG_MODE, config.BRK_DFLOOR_MODE = "off", "off"
PL.write_row = _capture
try:
    e2 = decide_run(XE.ExitEngine(paper_trading=True), rec("e2"), [2.10, 2.20, 1.45])
    m1 = decide_run(XE.ExitEngine(paper_trading=True), rec("m1"), [2.05, 2.10, 2.20, 2.15, 2.142, 2.14])
    # M2: a record the plan does not cover - a formed condor's leg (two open legs: the ladder decides)
    _eng = XE.ExitEngine(paper_trading=True)
    _prev = getattr(XE, "_exit_engine", None)
    XE._exit_engine = _eng
    try:
        leg = credit_rec("m2", strategy="IronCondorStrategy", is_condor_leg=1)
        sib = credit_rec("m2s", strategy="IronCondorStrategy", is_condor_leg=1, option_side="call")
        m2rows = []
        for m in (0.90, 0.80):
            _eng.evaluate(leg, m)
            leg["current_premium"] = m
            ROWS.clear()
            M.get_management_plan()._one({"_open_records": [leg, sib]}, leg, 720.0)
            mine = [x for x in ROWS if x["strategy"] == "IronCondorStrategy/manage"]
            m2rows.append(mine[-1] if mine else None)
    finally:
        XE._exit_engine = _prev
finally:
    PL.write_row = _orig_write
    config.BRK_NOPROG_MODE, config.BRK_DFLOOR_MODE = _saved

it_e2 = e2[2][0]
check("E2 decide(): the hard_stop spec exit wins over a decay that would fire the same tick",
      it_e2 is not None and it_e2.action == "CLOSE" and it_e2.condition == "hard_stop",
      f"{getattr(it_e2, 'condition', None)} {getattr(it_e2, 'reason', None)!r}")

# ── P restart ────────────────────────────────────────────────────────────────────────────────────────
p1 = run(rec("p1", max_premium_seen=2.20, min_premium_seen=1.98, mfe_premium=None), [2.15, 2.14])
check("P1 restart: a fresh engine on a rehydrated record closes at 30% of the PERSISTED peak, arm time unknown",
      closes(p1) == [False, True] and is_decay(p1[1][0])
      and "fell 30% from peak +$200.00 (p 0.200), armed at n/a (before a restart)" in str(p1[1][0].exit_reason),
      f"{closes(p1)} {p1[1][0].exit_reason!r}")


# ── S study parity ───────────────────────────────────────────────────────────────────────────────────
# COPIED VERBATIM from ~/reviews/decay/coupled.py (walk, rule_B; ARM 0.05), the v4 branch dropped (unused by V0 B).
ARM = 0.05


def walk(t, P, decide, v4=False):
    peak = 0.0

    def fill(k):
        q = next((x for x in P[k:] if x is not None), None)
        return t["p_real"] if q is None else q
    for i, p in enumerate(P):
        if p is None: continue
        peak = max(peak, p)
        if peak < ARM * t["e"] or peak <= 0: continue
        ts = t["t0"] + 15 * (i + 1)
        if decide(i, ts, p, peak):
            return p, (fill(i + 1) if i + 1 < len(P) else t["p_real"]), True
    return t["p_real"], t["p_real"], False


def rule_B(X): return lambda i, ts, p, pk: p <= pk * (1 - X)


def study_first(e, s, marks):
    P = [round(s * (m - e), 4) for m in marks]
    hit = {"i": None}

    def dec(i, ts, p, pk):
        ok = rule_B(0.30)(i, ts, p, pk)
        if ok and hit["i"] is None:
            hit["i"] = i
        return ok
    walk({"e": e, "p_real": P[-1], "t0": 0}, P, dec)
    return hit["i"]


rng = random.Random(57)
mism, fired_n = [], 0
for orient in ("debit", "credit"):
    for k in range(300):
        e = round(rng.uniform(0.5, 4.0), 2)
        m, marks = e, []
        for _ in range(60):
            m = max(0.01, m + rng.gauss(0.0, 0.03 * e))
            marks.append(round(m, 4))
        r = (rec(f"s{orient}{k}", entry_premium=e, stop_premium=0.0001) if orient == "debit"
             else credit_rec(f"s{orient}{k}", entry_premium=e, stop_premium=1e5))
        eng = XE.ExitEngine(paper_trading=True)
        bot_i = None
        for i, mk in enumerate(marks):
            d = eng.evaluate(r, mk)
            if is_decay(d):
                bot_i = i
                break
            if d.should_exit:                 # an existing exit ended the trade: compare only up to here
                bot_i = ("other", i)
                break
        st_i = study_first(e, 1 if orient == "debit" else -1, marks)
        if isinstance(bot_i, tuple):
            if st_i is not None and st_i < bot_i[1]:
                mism.append((orient, k, bot_i, st_i))
            continue
        fired_n += bot_i is not None
        if bot_i != st_i:
            mism.append((orient, k, bot_i, st_i))
check("S1 study parity: 600 random paths - the bot's first decay tick equals coupled.py walk() + rule_B(0.30)",
      not mism and fired_n > 100, f"{len(mism)} mismatches {mism[:4]}; {fired_n} paths closed on decay")

# ── M management rows ────────────────────────────────────────────────────────────────────────────────
names = ("decay_peak_p", "decay_p", "decay_armed", "decay_frac", "decay_fired")
conds = [getattr(it, "condition", None) if it is not None and it.action == "CLOSE" else None for it, _ in m1]
has = [row is not None and all(n in row["checks"] for n in names) for _, row in m1]
fired = [(row or {"checks": {}})["checks"].get("decay_fired", (None,))[0] for _, row in m1]
armed = [(row or {"checks": {}})["checks"].get("decay_armed", (None,))[0] for _, row in m1]
last = m1[5][1] or {"checks": {}, "notes": {}}
check("M1 decide() on a Breakout: CLOSE 'decay' on the 30% tick only; decay_* rows every tick; values and note",
      conds == [None, None, None, None, None, "decay"] and all(has)
      and fired == [0.0, 0.0, 0.0, 0.0, 0.0, 1.0] and armed == [0.0, 1.0, 1.0, 1.0, 1.0, 1.0]
      and abs(last["checks"]["decay_peak_p"][0] - 0.20) < 1e-9 and abs(last["checks"]["decay_p"][0] - 0.14) < 1e-9
      and abs(last["checks"]["decay_frac"][0] - 0.30) < 1e-9 and "FIRED" in last["notes"].get("decay_frac", ""),
      f"conds {conds} has {has} fired {fired} armed {armed}")
m2ok = (all(r is not None and all(n in r["checks"] for n in names) for r in m2rows)
        and abs(m2rows[1]["checks"]["decay_peak_p"][0] - 0.20) < 1e-9
        and m2rows[1]["checks"]["decay_armed"][0] == 1.0) if all(m2rows) else False
check("M2 _one() on a formed condor leg (not covered): decay_* rows from the running engine's reading",
      m2ok, f"{[r and {n: r['checks'].get(n) for n in names} for r in m2rows]}")

# ── H shadow TCS ─────────────────────────────────────────────────────────────────────────────────────
try:
    from execution import shadow_book as SB
    from database.trade_logger import make_record

    class _PC:
        def __init__(self, k, m):
            self.strike, self.mark, self.bid, self.ask, self.iv, self.delta, self.theta = k, m, m - 0.01, m + 0.01, 0.2, -0.3, -0.01

    class _PCh:
        def __init__(self, sm, lm):
            self.puts, self.calls, self.spot_price = [_PC(715.0, sm), _PC(710.0, lm)], [], 720.0
    _shdb = os.path.join(_s, "shadow_h1.db")
    _bk = SB.ShadowBook(_shdb)
    _hr = make_record(trade_id="h1", symbol="QQQ", strategy="TrendCreditSpread", setup_type="x", direction="neutral",
                      option_side="put", contracts=2, entry_premium=1.0, stop_premium=0.0, target_premium=0.0,
                      short_strike=715.0, long_strike=710.0, is_condor_leg=1, is_credit_vertical=1,
                      underlying_stop=0.0, expiry="2026-10-30", entry_time="2026-10-30T14:00:00+00:00",
                      short_symbol="QQQ   261030P00715000", long_symbol="QQQ   261030P00710000")
    _booked = _bk.open_entry(_hr, box_paper=True)
    _open = []
    for _sm in (1.30, 1.20, 1.25, 1.258, 1.26):                  # value 0.90, 0.80 (peak p 0.20), 0.85, 0.858, 0.86
        _bk.manage({"chain": _PCh(_sm, 0.40)})
        _open.append(_bk.has_open())
    import sqlite3
    _row = sqlite3.connect(_shdb).execute("SELECT status, exit_reason, exit_premium FROM trades").fetchone()
    _h1 = (_booked and _open == [True, True, True, True, False] and _row[0] == "closed"
           and str(_row[1]).startswith("decay: open profit +$28.00 (p 0.140) fell 30% from peak +$40.00 (p 0.200)")
           and abs(float(_row[2]) - 0.86) < 1e-9)
    _h1d = f"open {_open} row {_row}"
except Exception as exc:                                       # noqa: BLE001
    _h1, _h1d = False, f"{type(exc).__name__}: {exc}"
check("H1 a shadow TCS (its own engine, through _manage_one): the 30% fade closes it with the decay reason", _h1, _h1d)

print("RESULT:", "FAIL " + ",".join(FAILED) if FAILED else "PASS")
sys.exit(1 if FAILED else 0)
