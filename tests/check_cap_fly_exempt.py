#!/usr/bin/env python3
"""
tests/check_cap_fly_exempt.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.3  2026-10-19  OTV4TEST r303 (PSTATE.1) — its subject ATPButterfly (F6: both flies asked at the cap) is DORMANT by default and a dormant plan now writes
      nothing by ruling, so this run switches it ACTIVE (OT_ATP_BUTTERFLY=1); what it pins is unchanged.
v1.2  2026-10-18  OTV4TEST r288 (PARK.1) — PARK IS THE THIRD CAP-EXEMPT NAME, by ruling (the operator, 2026-10-17: PARK
      on "its own budget outside the morning cap"; "Trade it"). F1 now refuses every strategy that is NOT a butterfly and
      NOT PARK; F12 (new) pins PARK admitted at the cap inside 11:01-11:03; F6 lets PARK reach the funnel (asked every
      tick, refused by its window at 13:30) and still requires that nothing but the two flies is ADMITTED or executed.
v1.1  2026-10-12  OTV4TEST r273 (BFLY.10) — the in-window clock 12:30 -> 13:30 (IN_WINDOW, used by F6-F11). r273 (BFLY.10), by ruling - the operator, 2026-10-12: "reduce the fly window to 1300".

At the DAILY CATASTROPHIC LOSS CAP every strategy is refused EXCEPT the two
butterflies, which are still asked inside their own window and their own
one-per-session quota.

v1.0  2026-09-30  OTV4TEST r178 (CAP.2). The operator, 2026-09-30: "Allow both
      flies to fire even if we've hit the cap. Only one of each TYPE per
      session, not one butterfly per session." Until r178 attempt_new_entry
      returned at is_halted() before any strategy was asked, and the admission
      table's cap universal refused all of them; on 09-25, 09-28 and 09-29 the
      butterflies' window never opened because the morning had spent the cap.

WHAT IT DRIVES (WA 21): the REAL execution.position_manager.decide / rules and
the REAL main.attempt_new_entry and main._attempt_butterfly. The fixtures are
the things a tick is handed - a risk manager that says halted, a session guard
that says RTH, a fixed clock, an established opening range, spies in place of
the two butterfly strategies - and recorders in place of the entry executors.
Stores are scratch (the harness's, or this file's own when run by hand).

  C0   CONTROL: main's log handler points at scratch, not the live bot.log
  F1   cap broken: every NON-butterfly strategy is refused, gate catastrophic_cap
  F2   cap broken: both butterflies are ADMITTED inside their window
  F3   cap broken: a butterfly is still refused outside its window, after its
       one try, and with one already open - the exemption removes the cap only
  F4   config.ADMISSION_RULES can switch an exemption OFF and cannot GRANT one
  F5   cap intact: the exemption changes no verdict (flag on vs flag off, every
       strategy, every half hour 09:30-16:00)
  F6   REAL dispatch, capped, 13:30: the pin fly then the ATP fly are asked, and
       NO other strategy is admitted or reaches the funnel
  F7   REAL dispatch, capped: a butterfly that fires is executed
  F8   REAL dispatch, capped, 10:00 (outside both windows): nothing is asked
  F9   REAL dispatch, capped, admission table unavailable: nothing is asked
       (fails CLOSED), and nothing else is reached
  F10  REAL dispatch, capped, both butterflies already traded today: neither asked
  F11  REAL dispatch, capped, only the ATP fly traded today: the pin fly is
       still asked (one of EACH type)

BORN RED on 2ce8ba2 (r177) under both interpreters at F2, F3, F4, F6, F7 and F11
(verdicts) and F5 (the field is absent); F1, F8, F9 and F10 - the paths the
change must not alter - are green there.

Run:  python3 tests/check_cap_fly_exempt.py
"""
from __future__ import annotations

import glob as _glob
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The lander runs CHECKs under the SYSTEM python3: borrow the repo venv's
# packages (check_loss_cap_rearm's idiom).
# A worktree has no venv of its own, so the box's install is the fallback.
for _base in (ROOT, os.path.expanduser("~/options-trader")):
    _found = _glob.glob(os.path.join(_base, "venv", "lib", "python*", "site-packages"))
    for _sp in _found:
        if _sp not in sys.path:
            sys.path.insert(1, _sp)
    if _found:
        break
sys.path.insert(0, ROOT)
os.environ["OT_ATP_BUTTERFLY"] = "1"   # r303: F6's second fly is active (check_plan_states pins dormant)

# Self-isolating: run by hand without the harness, no live store is touched.
_SCR = tempfile.mkdtemp(prefix="check_cap_fly_exempt_",
                        dir="/var/tmp" if os.path.isdir("/var/tmp") else None)
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived_store.db"),
               ("OT_RESTING_DB", "resting_orders.db"),
               ("OT_SIGNAL_JOURNAL_DIR", "signal_journal")):
    if not os.environ.get(_k):
        os.environ[_k] = os.path.join(_SCR, _f)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ.setdefault("OT_PAPER_TRADING", "1")

FAIL = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(label.split()[0])


def guard(label, fn, detail=lambda: ""):
    try:
        ok = bool(fn())
    except Exception as exc:                                    # noqa: BLE001
        print(f"  FAIL  {label}  [raised {type(exc).__name__}: {exc}]")
        FAIL.append(label.split()[0])
        return
    check(label, ok, detail())


from execution import position_manager as PMOD                  # noqa: E402
import config                                                   # noqa: E402

GEX, ATP = PMOD.GEXFLY, PMOD.ATPFLY
FLIES = (GEX, ATP)
TABLE = PMOD.rules()
IN_WINDOW = (13, 30)            # inside both butterfly windows (r273: was 12:30)


def _facts(name, now=IN_WINDOW, **kw):
    base = dict(strategy=name, now_et=now, trading_day=True, orb_established=True,
                cap_intact=False, past_hard_close=False)
    base.update(kw)
    return PMOD.Facts(**base)


# ── F1 — the cap still refuses everything else ──────────────────────────────
EXEMPT = FLIES + ("PARK",)          # r288: PARK, its own budget
others = [n for n in TABLE if n not in EXEMPT]
_f1 = {n: PMOD.decide(_facts(n)).gate for n in others}
check("F1 cap broken: every strategy but the two butterflies and PARK is refused on catastrophic_cap",
      bool(others) and all(g == "catastrophic_cap" for g in _f1.values()), str(_f1))
# ── F12 (r288) — PARK is admitted at the cap inside its own window ───────────
_f12 = PMOD.decide(_facts("PARK", now=(11, 1)))
check("F12 cap broken: PARK is admitted at 11:01 (cap-exempt, its own budget)",
      bool(_f12.admitted), f"{_f12.admitted} {_f12.gate}")

# ── F2 — both butterflies admitted ──────────────────────────────────────────
_f2 = {n: (PMOD.decide(_facts(n)).admitted, PMOD.decide(_facts(n)).gate) for n in FLIES}
check("F2 cap broken: both butterflies are admitted inside their window",
      all(a for a, _g in _f2.values()), str(_f2))

# ── F3 — the exemption removes the cap and nothing else ─────────────────────
_f3 = {}
for n in FLIES:
    _f3[n] = (PMOD.decide(_facts(n, now=(10, 0))).gate,
              PMOD.decide(_facts(n, tries_used=1)).gate,
              PMOD.decide(_facts(n, open_by_strategy={n: 1})).gate,
              PMOD.decide(_facts(n, orb_established=False)).gate,
              PMOD.decide(_facts(n, past_hard_close=True)).gate)
check("F3 cap broken: a butterfly is still refused by window, tries, max-open, orb range, hard close",
      all(v == ("window", "tries_per_session", "max_open_of_type", "orb_range", "hard_close")
          for v in _f3.values()), str(_f3))

# ── F4 — an override can switch it off, never grant it ──────────────────────
_orb_name = next(n for n in others if "ORB" in n.upper())
_had = getattr(config, "ADMISSION_RULES", None)
try:
    config.ADMISSION_RULES = {ATP: {"cap_exempt": False}, _orb_name: {"cap_exempt": True}}
    _t4 = PMOD.rules()
    _f4 = (PMOD.decide(_facts(ATP), _t4).gate, PMOD.decide(_facts(GEX), _t4).admitted,
           PMOD.decide(_facts(_orb_name, now=(10, 0)), _t4).gate)
finally:
    if _had is None:
        try:
            del config.ADMISSION_RULES
        except AttributeError:
            pass
    else:
        config.ADMISSION_RULES = _had
check("F4 an override switches the ATP exemption OFF, leaves the pin fly's, and cannot grant ORB one",
      _f4 == ("catastrophic_cap", True, "catastrophic_cap"), str(_f4))

# ── F5 — cap intact: the flag changes nothing ───────────────────────────────
import dataclasses                                              # noqa: E402
_flat = {n: (dataclasses.replace(r, cap_exempt=False) if hasattr(r, "cap_exempt") else r)
         for n, r in TABLE.items()}
_diff = []
for n in TABLE:
    for h in range(9, 16):
        for m in (0, 30):
            for tries in (0, 1):
                f = _facts(n, now=(h, m), cap_intact=True, tries_used=tries)
                a, b = PMOD.decide(f, TABLE), PMOD.decide(f, _flat)
                if (a.admitted, a.gate) != (b.admitted, b.gate):
                    _diff.append((n, h, m, tries))
check("F5 cap intact: the exemption changes no verdict for any strategy at any time",
      hasattr(TABLE[GEX], "cap_exempt") and not _diff, str(_diff[:4]))

# ── F6-F11 — the REAL dispatch ──────────────────────────────────────────────
# ⚠️ BOX.16: main attaches a file handler to config.LOG_FILE AT IMPORT, and no
# environment variable overrides it. This gate's first cut wrote 110 fixture
# lines ("CATASTROPHIC LOSS CAP reached", "[admission] table unavailable") into
# the LIVE bot.log on 2026-09-30 08:31-08:36 ET. config.LOG_FILE is pointed at
# scratch BEFORE main is imported, and C0 proves where the handler went.
config.LOG_FILE = os.path.join(_SCR, "bot.log")
import logging                                                  # noqa: E402
import main as M                                                # noqa: E402

_files = sorted({getattr(h, "baseFilename", "") for lg in
                 [logging.getLogger()] + [logging.getLogger(n) for n in
                                          list(logging.root.manager.loggerDict)]
                 for h in getattr(lg, "handlers", []) if getattr(h, "baseFilename", "")})
check("C0 CONTROL: every log file this process writes is in scratch, never the live bot.log",
      bool(_files) and all(f.startswith(_SCR) for f in _files), str(_files))
import database.trade_logger as TL                              # noqa: E402


class _Risk:
    def is_halted(self):
        return True


class _Session:
    def can_enter(self, macro, rehearsal=False):
        return True, "ok"


class _OrbData:
    orb_high, orb_low, state = 720.0, 715.0, None


class _OrbEngine:
    data = _OrbData()


class _State:
    paper_trading, tick_count = True, 1


class _PM(PMOD.PositionManager):
    """The REAL logging_state over an empty book - no broker, no store."""
    def __init__(self):                                         # noqa: D401
        pass

    def open_by_strategy(self):
        return {}


class _Spy:
    def __init__(self, name, log, fire=None):
        self.name, self.log, self.fire = name, log, fire

    def generate_signal(self, **kw):
        self.log.append(self.name)
        return self.fire


class _Fired:
    strategy_name, pin_strike, strike = "GEXPinButterfly", 715.0, 715.0


def _fresh_book(*traded):
    TL._trade_logger = TL.TradeLogger(os.path.join(tempfile.mkdtemp(dir=_SCR), "book.db"))
    c = TL.get_trade_logger()._connect()
    try:
        for st in traded:
            c.execute("INSERT INTO trades (trade_id, symbol, strategy, status, entry_time)"
                      " VALUES (?,?,?,?,?)",
                      (f"{st}-1", "QQQ", st, "open",
                       datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))
        c.commit()
    finally:
        c.close()


_REAL = {k: getattr(M, k) for k in (
    "get_risk_manager", "get_session_guard", "get_entry_engine", "is_rth", "now_et",
    "get_orb_engine", "get_position_manager", "_gex_bfly_strategy", "_atp_bfly_strategy",
    "_execute_entry_signal", "_safe_strategy", "_execute_condor_leg")}


def _drive(hhmm, *, traded=(), fire=None, pm_raises=False):
    """One capped tick through the REAL attempt_new_entry. Returns
    (asked, funnel names, executed, admitted set)."""
    asked, funnel, executed = [], [], []
    admitted = None
    _fresh_book(*traded)
    real_safe = _REAL["_safe_strategy"]

    def _safe(name, fn, ctx=None):
        funnel.append(name)
        return real_safe(name, fn, ctx)

    def _pm(paper=True):
        if pm_raises:
            raise RuntimeError("store unreadable (fixture)")
        return _PM()

    now = _REAL["now_et"]().replace(hour=hhmm[0], minute=hhmm[1], second=0, microsecond=0)
    M.get_risk_manager = lambda: _Risk()
    M.get_session_guard = lambda: _Session()
    M.get_entry_engine = lambda paper=True: object()
    M.is_rth = lambda *a, **k: True
    M.now_et = lambda: now
    M.get_orb_engine = lambda: _OrbEngine()
    M.get_position_manager = _pm
    M._gex_bfly_strategy = _Spy("GEX", asked, fire=fire)
    M._atp_bfly_strategy = _Spy("ATP", asked)
    M._execute_entry_signal = lambda sig, *a, **k: executed.append(
        getattr(sig, "strategy_name", "?"))
    M._execute_condor_leg = lambda sig, *a, **k: executed.append("condor_leg")
    M._safe_strategy = _safe
    try:
        from strategy import gex_pin_butterfly as gpb
        gpb.GEXPinButterflyStrategy.PLAYED_PINS.clear()
    except Exception:                                           # noqa: BLE001
        pass
    ctx = {"macro": None, "orb": None, "chain": object(), "gex": object(),
           "price": 716.0, "atm_iv": 0.2, "df_1m": None}
    try:
        M.attempt_new_entry(ctx, None, _State())
        admitted = None if M._ADMITTED is None else sorted(M._ADMITTED)
    finally:
        for k, v in _REAL.items():
            setattr(M, k, v)
    return asked, funnel, executed, admitted


_R = {}


def _f6():
    _R["f6"] = _drive(IN_WINDOW)
    asked, funnel, executed, admitted = _R["f6"]
    # r288: PARK is ASKED in the capped branch every tick (refused by its window at 13:30, never admitted)
    return (asked == ["GEX", "ATP"] and [f for f in funnel if f != "PARK"] == ["GEXPinButterfly", "ATPButterfly"]
            and executed == [] and admitted == sorted(FLIES))


guard("F6 REAL dispatch, capped, 13:30: the pin fly then the ATP fly are asked; nothing else is admitted or reaches the funnel",
      _f6, lambda: str(_R.get("f6")))


def _f7():
    _R["f7"] = _drive(IN_WINDOW, fire=_Fired())
    asked, funnel, executed, _adm = _R["f7"]
    return asked == ["GEX"] and executed == ["GEXPinButterfly"]


guard("F7 REAL dispatch, capped: a butterfly that fires is executed (and the ATP waits a tick)",
      _f7, lambda: str(_R.get("f7")))


def _f8():
    _R["f8"] = _drive((10, 0))
    return _R["f8"][0] == [] and _R["f8"][2] == []


guard("F8 REAL dispatch, capped, 10:00 (outside both windows): nothing is asked",
      _f8, lambda: str(_R.get("f8")))


def _f9():
    _R["f9"] = _drive(IN_WINDOW, pm_raises=True)
    return _R["f9"][:3] == ([], [], [])


guard("F9 REAL dispatch, capped, admission table unavailable: nothing is asked and nothing is reached (fails CLOSED)",
      _f9, lambda: str(_R.get("f9")))


def _f10():
    _R["f10"] = _drive(IN_WINDOW, traded=("GEXPinButterfly", "ATPButterfly"))
    return _R["f10"][0] == [] and _R["f10"][2] == []


guard("F10 REAL dispatch, capped, both butterflies traded today: neither is asked",
      _f10, lambda: str(_R.get("f10")))


def _f11():
    _R["f11"] = _drive(IN_WINDOW, traded=("ATPButterfly",))
    return _R["f11"][0] == ["GEX"]


guard("F11 REAL dispatch, capped, only the ATP fly traded today: the pin fly is still asked (one of EACH type)",
      _f11, lambda: str(_R.get("f11")))

shutil.rmtree(_SCR, ignore_errors=True)
print()
if FAIL:
    print(f"RED — {len(FAIL)} failed: {sorted(set(FAIL))}")
    sys.exit(1)
print("GREEN — at the cap only the two butterflies are asked, inside their window and quota")
sys.exit(0)
