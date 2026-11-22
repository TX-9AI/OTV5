#!/usr/bin/env python3
"""tests/check_no_half_day_entries.py  v5.0
v5.0  2026-11-22  OTV5 r145 (HALF.1) — NEW. NOTHING OPENS ON A 13:00 HALF DAY; A FULL DAY IS UNCHANGED.
      The operator, 2026-11-22: "given our trading system, I don't think we should trade on half days" ("our end of
      day sequence is already structured for a 1600 close"); ruling: "Yes, just treat them as bank holidays. No
      trading." The boxes still wake and record data, so this is not a wake change: every opening path refuses on
      the day, every close-side time and the data path are untouched. Red on r144 (6745e72) at G2a G3a G4 G5a G5c G6 G8a
      G9 (8 of 18); G2b G3b G5b G7a are r144's own digests, identical on both trees; 8 revert mutants red.

Every instant is pinned (the module clock, utils.time_utils.now_et, and the copies entry_engine and session_guard
import by name). Half days: 2026-11-27 and 2026-12-24 (the next two). Full days: 2026-11-25 and 2026-12-23.

  G1  the calendar: both half days are listed in market_calendar.EARLY_CLOSES at 13:00, are sessions
      (is_trading_day) and is_half_day; both full days are not half days
  G2  entries_open() is False at every minute 09:00-17:00 on both half days; the full days' minute vector is the
      digest r144 produced (FULL_ENTRIES_DIGEST)
  G3  EVERY SETUP, AT THE ORDER: for each setup in config.ENTRY_WINDOWS (Runaway, the Hunt, PARK, OGAP) at every
      minute of its own window on both half days, the real paper EntryEngine.enter() returns None before the
      order (a tripwire _place_single_leg and trade logger are never reached) and the walk's re-offer
      (_window_open) says closed; on the full days the per-setup, per-minute vector (enter reached / held, the
      re-offer verdict) over 09:00-16:30 is the digest r144 produced (FULL_SETUPS_DIGEST), and inside each window
      enter() reaches the order (G3c)
  G4  the credit choke point: main._execute_condor_leg returns before it reads the signal's side on both half days
      (10:00, 11:00, 12:30) and reaches it on the full days (10:00)
  G5  THE DISPATCH: risk/session_guard.can_enter refuses with HALF_DAY_REASON on both half days, trading pass and
      rehearsal, at 09:35 10:00 11:02 12:30 13:30 16:53; main.attempt_new_entry on a half day writes one
      entry_blocked skip and asks no setup (_attempt_hunt / _attempt_park / _attempt_ogap / _execute_entry_signal
      are tripwires); on a full day at 10:00 it goes past the gate; the full days' can_enter verdict vector
      (09:00-17:00, both modes) is the digest r144 produced (FULL_GUARD_DIGEST)
  G6  ONE LINE A DAY: 60 can_enter ticks on 11-27 then 60 on 12-24 log exactly one "[half-day] <date> ... NO ENTRIES
      TODAY" INFO line per date; 60 ticks on a full day log none
  G7  EXITS AND THE CLOSE SIDE UNCHANGED: is_rth, is_hard_close_time, eod_close_due (both kinds), close_anchored
      (the hard close) and past_close_anchor (15:40) at every minute 09:00-17:00 on all four days are the digest
      r144 produced (CLOSE_SIDE_DIGEST); no exit or data-capture module names the predicate or entries_open
  G8  no key: config has no HALF_DAY_ENTRY_LEAD_MIN and no code token anywhere reads it; time_utils and
      session_guard read no environment key r144's did not
  G9  ONE PREDICATE: entries_open and SessionGuard.can_enter both call time_utils.no_entries_today, which calls
      market_calendar.is_half_day

Run:  python3 tests/check_no_half_day_entries.py   (under the venv; exit 0 green, 1 red, 2 not run)
"""
from __future__ import annotations

import ast
import glob as _glob
import hashlib
import io
import logging
import os
import sys
import tokenize
from datetime import date, datetime, time as dtime
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    sys.path.insert(1, _sp)

FAILS: list = []

# Pinned on r144 (6745e72); identical on r145.
FULL_ENTRIES_DIGEST = "6b69d357489c12b7"
FULL_SETUPS_DIGEST = "7f477e16a3e3d4e5"
FULL_GUARD_DIGEST = "5b9876e887313612"
CLOSE_SIDE_DIGEST = "0ece697e8fba1edd"
R144_ENV_KEYS = ()     # r144's time_utils and session_guard name no OT_ key


def check(name, ok, det=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {det}" if det else ""))
    if not ok:
        FAILS.append(name)


def dig(rows) -> str:
    return hashlib.sha256("\n".join(map(str, rows)).encode()).hexdigest()[:16]


try:
    import pandas, pytz                                           # noqa: F401,E401
except ImportError as _exc:
    print(f"NOT RUN — this interpreter cannot import the trading stack ({_exc}); run under the venv")
    sys.exit(2)

print("\ncheck_no_half_day_entries\n")
import config                                                     # noqa: E402
import utils.time_utils as tu                                     # noqa: E402
from utils import market_calendar as mc                           # noqa: E402
import risk.session_guard as sg                                   # noqa: E402
import execution.entry_engine as ee                               # noqa: E402

ET = tu.ET
HALF = (date(2026, 11, 27), date(2026, 12, 24))
FULL = (date(2026, 11, 25), date(2026, 12, 23))
_REAL = {"tu": tu.now_et, "ee": getattr(ee, "now_et", None), "sg": getattr(sg, "now_et", None)}


def at(d, h, m):
    return ET.localize(datetime.combine(d, dtime(h, m)))


def set_clock(when):
    f = (lambda: when)
    tu.now_et = f
    if _REAL["ee"] is not None:
        ee.now_et = f
    if _REAL["sg"] is not None:
        sg.now_et = f


def reset_clock():
    tu.now_et = _REAL["tu"]
    if _REAL["ee"] is not None:
        ee.now_et = _REAL["ee"]
    if _REAL["sg"] is not None:
        sg.now_et = _REAL["sg"]


def minutes(h0=9, m0=0, h1=17, m1=0):
    t = h0 * 60 + m0
    while t <= h1 * 60 + m1:
        yield t // 60, t % 60
        t += 1


class _Reached(Exception):
    """A tripwire past the gate was hit: the path went on toward an order."""


try:
    # ── G1 the calendar ──────────────────────────────────────────────────────
    g1 = all(mc.EARLY_CLOSES.get(d.isoformat()) == "13:00" and mc.is_trading_day(d) and mc.is_half_day(d)
             for d in HALF) and not any(mc.is_half_day(d) for d in FULL)
    check("G1  2026-11-27 and 2026-12-24 are listed 13:00 early closes, sessions, is_half_day; 11-25 and 12-23 are not",
          g1, f"{[(d.isoformat(), mc.EARLY_CLOSES.get(d.isoformat())) for d in HALF]}")

    # ── G2 entries_open ──────────────────────────────────────────────────────
    open_half = [(d.isoformat(), h, m) for d in HALF for h, m in minutes() if tu.entries_open(at(d, h, m))]
    check("G2a entries_open() is False at every minute 09:00-17:00 on both half days", not open_half,
          f"{len(open_half)} open minute(s), first {open_half[:3]}")
    full_vec = [(d.isoformat(), h, m, tu.entries_open(at(d, h, m))) for d in FULL for h, m in minutes()]
    fd = dig(full_vec)
    check("G2b the full days' entries_open minute vector is r144's", fd == FULL_ENTRIES_DIGEST,
          f"{fd} (pinned {FULL_ENTRIES_DIGEST}; {sum(r[3] for r in full_vec)} open minutes)")

    # ── G3 every setup at the order ──────────────────────────────────────────
    from strategy.base_strategy import OptionsSignal
    from data.options_chain import OptionContract

    class _Boom:
        def __getattr__(self, k):
            raise _Reached("trade logger")

    def _trip(*_a, **_k):
        raise _Reached("_place_single_leg")

    class _Sizing:
        allowed, contracts, total_cost = True, 1, 85.0

    windows = dict(getattr(config, "ENTRY_WINDOWS", {}) or {})
    want = {"RunawayContinuation", "LiquidityHunt", "PARK", "OGAP"}
    check("G3- the four live setups each have an entry window on record", want <= set(windows),
          f"{sorted(windows)}")

    def enter_outcome(name, when) -> str:
        set_clock(when)
        try:
            eng = ee.EntryEngine(paper_trading=True)
            eng._trade_logger = _Boom()
            eng._place_single_leg = _trip
            sig = OptionsSignal(strategy_name=name, setup_type="orb_long", option_side="call", strike=81.0,
                                entry_premium=0.85, underlying_entry=80.0,
                                contract=OptionContract(symbol="X", strike=81.0, mark=0.85))
            try:
                r = eng.enter(sig, _Sizing())
            except _Reached:
                return "reached"
            return "held" if r is None else "booked"
        finally:
            reset_clock()

    def reoffer(name, when) -> bool:
        set_clock(when)
        try:
            return bool(ee.EntryEngine._window_open(name)[0])
        finally:
            reset_clock()

    bad = []
    for d in HALF:
        for name in sorted(want & set(windows)):
            (sh, sm), (eh, em) = windows[name]
            for h, m in minutes(sh, sm, eh, em):
                o, w = enter_outcome(name, at(d, h, m)), reoffer(name, at(d, h, m))
                if o != "held" or w:
                    bad.append((d.isoformat(), name, f"{h}:{m:02d}", o, w))
    check("G3a every setup, every minute of its own window, both half days: enter() holds before the order and "
          "the re-offer says closed", not bad, f"{len(bad)} open: {bad[:4]}")

    vec, inside = [], []
    for d in FULL:
        for name in sorted(want & set(windows)):
            (sh, sm), (eh, em) = windows[name]
            for h, m in minutes(9, 0, 16, 30):
                o, w = enter_outcome(name, at(d, h, m)), reoffer(name, at(d, h, m))
                vec.append((d.isoformat(), name, h, m, o, w))
                if sh * 60 + sm <= h * 60 + m < eh * 60 + em:
                    inside.append(o == "reached" and w)
    sd = dig(vec)
    check("G3b the full days' per-setup, per-minute vector (enter, re-offer) 09:00-16:30 is r144's",
          sd == FULL_SETUPS_DIGEST, f"{sd} (pinned {FULL_SETUPS_DIGEST})")
    check("G3c on the full days every setup reaches the order at every minute of its window (opens as before)",
          bool(inside) and all(inside), f"{sum(inside)}/{len(inside)}")

    # ── G4 the credit choke point ────────────────────────────────────────────
    import main as M

    class _CreditSig:
        strategy_name = "CreditVertical"
        vix_at_signal = 20.0

        @property
        def option_side(self):
            raise _Reached("option_side")

    _saved = (M._stamp_vix, M._stamp_adx, M._log_only)
    M._stamp_vix = M._stamp_adx = (lambda *a, **k: None)
    M._log_only = (lambda *a, **k: False)

    def credit(when) -> str:
        set_clock(when)
        try:
            M._execute_condor_leg(_CreditSig(), SimpleNamespace(paper_trading=True), {})
            return "held"
        except _Reached:
            return "reached"
        finally:
            reset_clock()
    try:
        ch = [credit(at(d, h, m)) for d in HALF for h, m in ((10, 0), (11, 0), (12, 30))]
        cf = [credit(at(d, 10, 0)) for d in FULL]
    finally:
        M._stamp_vix, M._stamp_adx, M._log_only = _saved
    check("G4  _execute_condor_leg holds before the signal's side on both half days and reaches it on the full days",
          set(ch) == {"held"} and set(cf) == {"reached"}, f"half {ch} full {cf}")

    # ── G5 the dispatch ──────────────────────────────────────────────────────
    reason = getattr(sg, "HALF_DAY_REASON", None)
    guard = sg.SessionGuard()

    def verdict(when, rehearsal):
        set_clock(when)
        try:
            return guard.can_enter(None, rehearsal=rehearsal)
        finally:
            reset_clock()

    g5 = [(d.isoformat(), h, m, r, verdict(at(d, h, m), r))
          for d in HALF for h, m in ((9, 35), (10, 0), (11, 2), (12, 30), (13, 30), (16, 53)) for r in (False, True)]
    g5bad = [x for x in g5 if not (reason and x[4] == (False, reason))]
    check("G5a can_enter refuses with HALF_DAY_REASON on both half days, trading pass and rehearsal",
          reason is not None and not g5bad, f"reason={reason!r}; {len(g5bad)} other: {g5bad[:2]}")
    gv = [(d.isoformat(), h, m, r, verdict(at(d, h, m), r)[0], verdict(at(d, h, m), r)[1]
           if "rehearsal (" not in verdict(at(d, h, m), r)[1] else "rehearsal")
          for d in FULL for h, m in minutes() for r in (False, True)]
    gd = dig(gv)
    check("G5b the full days' can_enter verdicts (09:00-17:00, both modes) are r144's", gd == FULL_GUARD_DIGEST,
          f"{gd} (pinned {FULL_GUARD_DIGEST})")

    class _Ctx(dict):
        def get(self, k, default=None):
            if k == "macro":
                return None
            raise _Reached(f"ctx[{k!r}]")

        def __getitem__(self, k):
            if k == "macro":
                return None
            raise _Reached(f"ctx[{k!r}]")

    def dispatch(when):
        skips, asked = [], []
        names = ("_attempt_hunt", "_attempt_park", "_attempt_ogap", "_execute_entry_signal")
        saved = {n: getattr(M, n) for n in names}
        saved.update({n: getattr(M, n) for n in ("_plan_skip_all", "get_risk_manager", "get_entry_engine")})
        for n in names:
            setattr(M, n, (lambda _n: (lambda *a, **k: asked.append(_n)))(n))
        M._plan_skip_all = lambda reason, gate="": skips.append((reason, gate))
        M.get_risk_manager = lambda *a, **k: SimpleNamespace(is_halted=lambda: False)
        M.get_entry_engine = lambda *a, **k: SimpleNamespace()
        set_clock(when)
        out = "returned"
        try:
            M.attempt_new_entry(_Ctx(macro=None), None, SimpleNamespace(paper_trading=True))
        except _Reached:
            out = "past the gate"
        except Exception as exc:                                  # noqa: BLE001
            out = f"past the gate ({type(exc).__name__})"
        finally:
            reset_clock()
            for n, f in saved.items():
                setattr(M, n, f)
        return out, skips, asked

    dh = [dispatch(at(d, 10, 0)) for d in HALF]
    ok_h = all(o == "returned" and not a and s == [(f"entry blocked: {reason}", "entry_blocked")] for o, s, a in dh)
    check("G5c attempt_new_entry at 10:00 on both half days: one entry_blocked skip, no setup asked", ok_h,
          f"{[(o, s[:1], a) for o, s, a in dh]}")
    dfu = [dispatch(at(d, 10, 0)) for d in FULL]
    ok_f = all(o.startswith("past the gate") and not any(g == "entry_blocked" for _r, g in s) for o, s, _a in dfu)
    check("G5d attempt_new_entry at 10:00 on the full days goes past the session gate", ok_f,
          f"{[(o, s[:1]) for o, s, _a in dfu]}")

    # ── G6 one line a day ────────────────────────────────────────────────────
    lines = []

    class _H(logging.Handler):
        def emit(self, r):
            if "[half-day]" in r.getMessage():
                lines.append((r.levelname, r.getMessage()))
    h = _H()
    lg = logging.getLogger(sg.__name__)
    lg.addHandler(h)
    _lvl = lg.level
    lg.setLevel(logging.INFO)
    try:
        if hasattr(sg, "_half_day_said"):
            sg._half_day_said.clear()
        for d in FULL[:1] + HALF:
            for i in range(60):
                verdict(at(d, 9, 30 + i % 30), bool(i % 2))
    finally:
        lg.removeHandler(h)
        lg.setLevel(_lvl)
    ok6 = (len(lines) == 2 and all(lv == "INFO" and "NO ENTRIES TODAY" in msg for lv, msg in lines)
           and HALF[0].isoformat() in lines[0][1] and HALF[1].isoformat() in lines[1][1])
    check("G6  60 ticks on each half day log ONE [half-day] INFO line per date; 60 on a full day log none", ok6,
          f"{len(lines)} line(s): {[m[:90] for _l, m in lines[:3]]}")

    # ── G7 exits and the close side ──────────────────────────────────────────
    cs = []
    for d in FULL + HALF:
        for hh, mm in minutes():
            n = at(d, hh, mm)
            cs.append((d.isoformat(), hh, mm, tu.is_rth(n), tu.is_hard_close_time(n), tu.eod_close_due(True, n),
                       tu.eod_close_due(False, n), tu.close_anchored(tu.HARD_CLOSE, n),
                       tu.past_close_anchor((15, 40), n)))
    cd = dig(cs)
    check("G7a is_rth, is_hard_close_time, eod_close_due, close_anchored, past_close_anchor on all four days are r144's",
          cd == CLOSE_SIDE_DIGEST, f"{cd} (pinned {CLOSE_SIDE_DIGEST})")
    touch = []
    for rel in ("execution/exit_engine.py", "execution/position_manager.py", "data/candle_feed.py",
                "data/market_data.py", "warehouse/s3_push.py", "data/options_chain.py"):
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            src = open(p, encoding="utf-8").read()
            for tok in ("no_entries_today", "entries_open(", "can_enter("):
                if tok in src:
                    touch.append(f"{rel}:{tok}")
    check("G7b no exit or data-capture module names no_entries_today, entries_open or can_enter", not touch,
          f"{touch}")

    # ── G8 no key ────────────────────────────────────────────────────────────
    readers = []
    for p in _glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
        rel = os.path.relpath(p, ROOT)
        if rel.startswith(("venv", ".git")) or rel == os.path.join("tests", "check_no_half_day_entries.py"):
            continue
        try:
            toks = tokenize.generate_tokens(io.StringIO(open(p, encoding="utf-8").read()).readline)
            if any(t.type == tokenize.NAME and t.string == "HALF_DAY_ENTRY_LEAD_MIN" for t in toks):
                readers.append(rel)
        except Exception:                                         # noqa: BLE001
            pass
    check("G8a config has no HALF_DAY_ENTRY_LEAD_MIN and no code anywhere names it",
          not hasattr(config, "HALF_DAY_ENTRY_LEAD_MIN") and not readers, f"{readers}")
    import re
    env = set()
    for rel in ("utils/time_utils.py", "risk/session_guard.py"):
        env |= set(re.findall(r"[\"'](OT_[A-Z0-9_]+)[\"']", open(os.path.join(ROOT, rel), encoding="utf-8").read()))
    check("G8b time_utils and session_guard read no environment key r144's did not",
          R144_ENV_KEYS is not None and env <= set(R144_ENV_KEYS), f"{sorted(env)}")

    # ── G9 one predicate ─────────────────────────────────────────────────────
    def calls_in(path, fn_name, cls=None):
        tree = ast.parse(open(os.path.join(ROOT, path), encoding="utf-8").read())
        scope = tree
        if cls:
            scope = next((n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == cls), None)
        fn = next((n for n in ast.walk(scope) if isinstance(n, ast.FunctionDef) and n.name == fn_name), None) \
            if scope is not None else None
        if fn is None:
            return None
        out = set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Call):
                f = n.func
                out.add(f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else "")
        return out
    eo = calls_in("utils/time_utils.py", "entries_open") or set()
    ce = calls_in("risk/session_guard.py", "can_enter", "SessionGuard") or set()
    ne = calls_in("utils/time_utils.py", "no_entries_today")
    check("G9  entries_open and SessionGuard.can_enter call no_entries_today, which calls market_calendar.is_half_day",
          "no_entries_today" in eo and "no_entries_today" in ce and ne is not None and "is_half_day" in ne,
          f"entries_open={'no_entries_today' in eo} can_enter={'no_entries_today' in ce} predicate={ne}")
except Exception as exc:                                          # noqa: BLE001
    import traceback
    traceback.print_exc()
    check("the gate ran to the end", False, f"{type(exc).__name__}: {exc}")
finally:
    reset_clock()

print()
if FAILS:
    print(f"check_no_half_day_entries: FAIL ({len(FAILS)}): {', '.join(FAILS)}")
    sys.exit(1)
print("check_no_half_day_entries: ALL PASS")
