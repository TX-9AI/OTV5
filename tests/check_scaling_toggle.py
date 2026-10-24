#!/usr/bin/env python3
"""
tests/check_scaling_toggle.py  v1.1
v1.1  2026-10-03  OTV4TEST r228 (CFG.4) — S9 RE-POINTED: the menu carries ONE scaling item, 9 =
      Breakout; no menu line dispatches the ORB or VOLT switch (both trades are off; the operator:
      "Yes to the configure change"). change_scaling itself is still driven for all three keys,
      and the switches still reach the sizer (S1-S8 unchanged).

ORB, Breakout and VOLT each have a scaling switch. OFF sizes that trade FLAT
while its structure stop, its exits and the r93 noise floor stay exactly as
they were; ON is the ramp, unchanged. And the ramp START is risk per trade.

v1.0  2026-09-27  OTV4TEST r161 (SIZE.2). The operator, 2026-09-27:
      "Risk per trade/Ramp Start (MIN) · Scaling Position Ramp TOP (MAX) ·
      ORB Scaling OFF/ON · Breakout Scaling OFF/ON · VOLT Scaling OFF/ON";
      "some of the other positions have benefited from the scaling sizes, but
      ultimately the orb has only gotten worse"; "retain the original structure
      stop responsible for scaling the sizes but just use a flat dollar amount
      for the entry"; on the merge, "that was always the intent".

WHAT IT DRIVES, NOT WHAT IT READS (WA 21). S1-S6 call the REAL
main._scaling_on, main._geometry_inputs, main._sizing_stop_premium and
RiskManager.size_for with the entry path's own arguments; S7 is HOP 0, the
dispatch: the entry path's size_for call must pass scaled=_scaling_on(signal),
or every switch is a menu item nothing reads (the r181 shape). S8 asks
config.py - the CONSUMER - what each key means; S9 runs configure.sh's own
function bodies against a temp unit and feeds what they write back to config.

  S1  ORB OFF sizes FLAT: rule "flat", floor(RISK / cost), and the SAME count
      at a tight stop and a wide one (the ramp would give 77 and 19)
  S2  ORB OFF still REFUSES a stop inside the noise floor (section 36 FEASIBILITY)
  S3  each switch moves ONLY its own trade: ORB OFF leaves Breakout and VOLT on
      the ramp; Breakout OFF leaves ORB; VOLT OFF leaves Breakout
  S4  all ON sizes exactly as check_volt_sizing V4 (ORB tight 77, Breakout 52)
  S5  a trade with no switch (the hunt) is untouched: True, budget rule, 11
  S6  OFF changes the COUNT and nothing on the signal: underlying_stop,
      stop_premium(), trail activation and sizes_on_geometry are identical
  S7  HOP 0: the entry path passes scaled=_scaling_on(signal) to size_for
  S8  config: ORB_RISK_USD IS RISK_PER_TRADE_USD whatever OT_ORB_RISK_USD says
      (and the ignored value is kept for the startup warning); only "1" is ON
  S9  configure.sh: items 9/10/11 write 1/0 that config reads as True/False,
      and item 2 removes a leftover OT_ORB_RISK_USD line
  S10 OFF with one contract dearer than the MIN is REFUSED, never floored to 1

BORN RED on 6e1fa68 (r160) - see the ledger row. Runs under the venv AND the
system python3 the lander uses (the first r161 land was refused on the latter).

Run:  python3 tests/check_scaling_toggle.py
"""

from __future__ import annotations

import ast
import atexit
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The lander runs every CHECK under the SYSTEM python3, which has no pytz, so
# `import main` needs the repo venv's packages - check_volt_sizing's idiom.
# The first land of r161 was REFUSED here: this gate had only ever been run
# under the venv (WA 38.9 criterion 3 says both).
import glob as _glob                                           # noqa: E402
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
sys.path.insert(0, ROOT)
if not os.environ.get("OT_TRADES_DB"):
    _scr = tempfile.mkdtemp(prefix="check_scaling_toggle_",
                            dir="/var/tmp" if os.path.isdir("/var/tmp") else None)
    atexit.register(shutil.rmtree, _scr, True)
    os.environ.setdefault("OT_TRADES_DB", os.path.join(_scr, "trades.db"))
    os.environ.setdefault("OT_DERIVED_DB", os.path.join(_scr, "derived_store.db"))
    os.environ.setdefault("OT_RESTING_DB", os.path.join(_scr, "resting.db"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ.setdefault("OT_PAPER_TRADING", "1")
# The live ramp: MIN 1050, TOP 10000 - the same values check_volt_sizing forces.
os.environ["OT_RISK_USD"] = "1050"
os.environ["OT_ORB_BUDGET_USD"] = "10000"
for _k in ("OT_ORB_RISK_USD", "OT_SCALE_ORB", "OT_SCALE_BREAKOUT", "OT_SCALE_VOLT"):
    os.environ.pop(_k, None)

FAIL: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])


print("=" * 68)
print("SCALING SWITCHES: ORB / Breakout / VOLT, and the merged ramp MIN")
print("=" * 68)

import main                                                    # noqa: E402
from risk.risk_manager import RiskManager                      # noqa: E402
from strategy.base_strategy import OptionsSignal               # noqa: E402

RM = RiskManager()
RISK = float(RM._risk_per_trade)
_HAS = hasattr(main, "_scaling_on")
check("S0 main._scaling_on exists", _HAS, "" if _HAS else "absent - no switch reaches the sizer")


def size(signal, noise_floor=0.0):
    """The entry path's size_for call, argument for argument, INCLUDING the
    switch. On a tree without the switch this reports the TypeError as a
    result rather than crashing, so born-red names every missing property."""
    w, d = main._geometry_inputs(signal)
    kw = dict(premium=signal.entry_premium,
              stop_premium=main._sizing_stop_premium(signal),
              grade="UNGRADED", net_debit=0.0, butterfly_half_size=False,
              orb_width=w, orb_stop_distance=d, noise_floor=noise_floor)
    if _HAS:
        kw["scaled"] = main._scaling_on(signal)
    try:
        return RM.size_for("long_debit", **kw)
    except TypeError as exc:
        class _R:                                               # noqa: D401
            rule, contracts, allowed, reject_reason = "TypeError", -1, False, str(exc)
        return _R()


def setsw(orb=True, brk=True, volt=True):
    main.SCALE_ORB, main.SCALE_BREAKOUT, main.SCALE_VOLT = orb, brk, volt


def orb(stop, premium=1.20):
    return OptionsSignal(strategy_name="ORBStrategy", orb_range_high=601.0,
                         orb_range_low=600.0, underlying_entry=601.10,
                         underlying_stop=stop, entry_delta=0.45,
                         entry_premium=premium)


def brk():
    s = OptionsSignal(strategy_name="Breakout", orb_range_high=601.0,
                      orb_range_low=600.0, underlying_entry=601.25,
                      underlying_stop=600.85, entry_delta=0.50, entry_premium=0.95)
    s.sizes_on_geometry = True
    return s


def volt():
    s = OptionsSignal(strategy_name="VOLT", orb_range_high=601.0,
                      orb_range_low=600.0, underlying_entry=601.25,
                      underlying_stop=601.25, entry_delta=0.45, entry_premium=1.20)
    s.sizing_distance = 0.40
    s.underlying_stop_is_thesis = True
    return s


def hunt():
    return OptionsSignal(strategy_name="LiquidityHunt", orb_range_high=601.0,
                         orb_range_low=600.0, underlying_entry=601.25,
                         underlying_stop=600.85, entry_delta=0.50, entry_premium=0.95)


FLAT_120 = int(RISK // 120.0)        # 1050 // (1.20 x 100) = 8
FLAT_95 = int(RISK // 95.0)          # 1050 // (0.95 x 100) = 11

# ── S1 — ORB OFF is FLAT, whatever the stop ─────────────────────────────────
setsw(orb=False)
t, w = size(orb(600.80)), size(orb(599.90))
check("S1 ORB OFF, tight stop: rule 'flat', floor(MIN / cost) contracts",
      t.allowed and t.rule == "flat" and t.contracts == FLAT_120,
      f"rule={t.rule} n={t.contracts} want flat {FLAT_120} ({t.reject_reason})")
check("S1 ORB OFF, wide stop: the SAME count (the ramp would give 77 vs 19)",
      w.allowed and w.rule == "flat" and w.contracts == t.contracts,
      f"tight={t.contracts} wide={w.contracts} rule={w.rule}")

# ── S2 — the noise floor still refuses ──────────────────────────────────────
f = size(orb(601.00), noise_floor=0.21)
check("S2 ORB OFF, stop 0.10 inside a 0.21 floor: REFUSED on the floor",
      not f.allowed and "noise_floor" in (f.reject_reason or ""),
      f"allowed={f.allowed} reason={f.reject_reason!r}")

# ── S3 — each switch moves only its own trade ───────────────────────────────
setsw(orb=False)
b, v = size(brk()), size(volt())
check("S3 ORB OFF leaves Breakout on the ramp (52)",
      b.rule == "orb_geometry" and b.contracts == 52, f"rule={b.rule} n={b.contracts}")
check("S3 ORB OFF leaves VOLT on the ramp",
      v.rule == "orb_geometry" and v.allowed, f"rule={v.rule} n={v.contracts}")
setsw(brk=False)
o, b = size(orb(600.80)), size(brk())
check("S3 Breakout OFF: Breakout flat, ORB still on the ramp (77)",
      b.rule == "flat" and b.contracts == FLAT_95
      and o.rule == "orb_geometry" and o.contracts == 77,
      f"brk={b.rule}/{b.contracts} orb={o.rule}/{o.contracts}")
setsw(volt=False)
v, b = size(volt()), size(brk())
check("S3 VOLT OFF: VOLT flat, Breakout still on the ramp",
      v.rule == "flat" and v.contracts == FLAT_120
      and b.rule == "orb_geometry" and b.contracts == 52,
      f"volt={v.rule}/{v.contracts} brk={b.rule}/{b.contracts}")

# ── S4 — all ON is the ramp, unchanged ──────────────────────────────────────
setsw()
o, b = size(orb(600.80)), size(brk())
check("S4 all ON: ORB tight 77 and Breakout 52 (check_volt_sizing V4)",
      o.rule == b.rule == "orb_geometry" and o.contracts == 77 and b.contracts == 52,
      f"orb={o.rule}/{o.contracts} brk={b.rule}/{b.contracts}")

# ── S5 — a trade with no switch is untouched ────────────────────────────────
setsw(False, False, False)
h = size(hunt())
check("S5 the hunt has no switch: _scaling_on True, budget rule, 11",
      (not _HAS or main._scaling_on(hunt()) is True)
      and h.rule == "budget" and h.contracts == FLAT_95,
      f"rule={h.rule} n={h.contracts}")
setsw()

# ── S6 — OFF changes the count and nothing on the signal ────────────────────
def _face(s):
    return (s.underlying_stop, round(s.stop_premium(), 6),
            round(s.trail_activation_premium(), 6),
            bool(getattr(s, "sizes_on_geometry", False)))


for label, mk in (("ORB", lambda: orb(600.80)), ("Breakout", brk), ("VOLT", volt)):
    s_on = mk()
    setsw()
    size(s_on)
    s_off = mk()
    setsw(False, False, False)
    size(s_off)
    check(f"S6 {label}: stop, stop premium, trail and geometry flag identical ON vs OFF",
          _face(s_on) == _face(s_off), f"on={_face(s_on)} off={_face(s_off)}")
setsw()

# ── S7 — HOP 0: the entry path passes the switch ────────────────────────────
_tree = ast.parse(open(os.path.join(ROOT, "main.py")).read())
_calls = [n for n in ast.walk(_tree) if isinstance(n, ast.Call)
          and isinstance(n.func, ast.Attribute) and n.func.attr == "size_for"
          and any(k.arg == "orb_stop_distance" for k in n.keywords)]
_passes = [c for c in _calls if any(
    k.arg == "scaled" and isinstance(k.value, ast.Call)
    and getattr(k.value.func, "id", "") == "_scaling_on" for k in c.keywords)]
check("S7 the entry path's size_for call passes scaled=_scaling_on(signal)",
      len(_calls) == 1 and len(_passes) == 1,
      f"{len(_calls)} geometry size_for call(s), {len(_passes)} passing the switch")


# ── S8 — config, the consumer ───────────────────────────────────────────────
def _cfg(env_extra, expr):
    env = {k: v for k, v in os.environ.items()
           if k not in ("OT_ORB_RISK_USD", "OT_SCALE_ORB", "OT_SCALE_BREAKOUT", "OT_SCALE_VOLT")}
    env.update(env_extra)
    p = subprocess.run([sys.executable, "-c", f"import config; print({expr})"],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    return p.stdout.strip() or f"IMPORT FAILED: {p.stderr.strip().splitlines()[-1:]}"


got = _cfg({"OT_RISK_USD": "1050", "OT_ORB_RISK_USD": "1001"},
           "config.ORB_RISK_USD, getattr(config, 'ORB_RISK_ENV_IGNORED', None)")
check("S8 OT_ORB_RISK_USD=1001 is NOT obeyed: ORB_RISK_USD is the 1050 MIN, 1001 kept to warn",
      got == "1050.0 1001", got)
got = _cfg({}, "config.SCALE_ORB, config.SCALE_BREAKOUT, config.SCALE_VOLT")
check("S8 unset switches are ON (a fresh box sizes as today)", got == "True True True", got)
got = _cfg({"OT_SCALE_ORB": "0", "OT_SCALE_BREAKOUT": "0", "OT_SCALE_VOLT": "0"},
           "config.SCALE_ORB, config.SCALE_BREAKOUT, config.SCALE_VOLT")
check("S8 '0' is OFF on every switch", got == "False False False", got)
# EVERY switch gets the junk value: a first cut tried it on Breakout alone,
# and a `!= "0"` mutant of SCALE_ORB (a typo read as ON) survived (M8).
got = _cfg({"OT_SCALE_ORB": "yes", "OT_SCALE_BREAKOUT": "on", "OT_SCALE_VOLT": "true"},
           "config.SCALE_ORB, config.SCALE_BREAKOUT, config.SCALE_VOLT")
check("S8 only the literal '1' is ON: 'yes'/'on'/'true' are OFF, the smaller size",
      got == "False False False", got)

# ── S9 — configure.sh writes what config reads ─────────────────────────────
_src = open(os.path.join(ROOT, "configure.sh")).read()


def _functions_only(src):
    out, keep = [], False
    for line in src.splitlines():
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*\(\)\s*\{", line):
            keep = True
        if keep:
            out.append(line)
        if keep and line == "}":
            keep = False
    return "\n".join(out)


def _run(call, start: dict, stdin: str):
    with tempfile.TemporaryDirectory() as tmp:
        envf = os.path.join(tmp, "env")
        with open(envf, "w") as fh:
            for k, v in start.items():
                fh.write(f"{k}={v}\n")
        funcs = os.path.join(tmp, "f.sh")
        with open(funcs, "w") as fh:
            fh.write(_functions_only(_src))
        h = f"""
command_not_found_handle() {{ echo "MISSING_COMMAND: $1" >&2; exit 42; }}
RESET=""; BOLD=""; GREEN=""; YELLOW=""; CYAN=""; RED=""
BOT_DIR="{ROOT}"
source "{funcs}"
get_env() {{ sed -n "s/^$1=//p" "{envf}"; }}
set_env() {{ grep -v "^$1=" "{envf}" > "{envf}.t"; mv "{envf}.t" "{envf}"; echo "$1=$2" >> "{envf}"; }}
drop_env() {{ grep -v "^$1=" "{envf}" > "{envf}.t"; mv "{envf}.t" "{envf}"; }}
reload_daemon() {{ echo RELOAD_CALLED >&2; }}
{call}
"""
        p = subprocess.run(["bash", "-c", h], input=stdin, capture_output=True,
                           text=True, timeout=60)
        vals = dict(ln.strip().split("=", 1) for ln in open(envf) if "=" in ln)
        return vals, p


_defined = set(re.findall(r"^([a-zA-Z_][a-zA-Z0-9_]*)\(\)", _src, re.M))
if "change_scaling" not in _defined:
    check("S9 configure.sh defines change_scaling", False, "absent")
else:
    for item, key, attr, name in (("9", "OT_SCALE_ORB", "SCALE_ORB", "ORB"),
                                  ("10", "OT_SCALE_BREAKOUT", "SCALE_BREAKOUT", "Breakout"),
                                  ("11", "OT_SCALE_VOLT", "SCALE_VOLT", "VOLT")):
        disp = re.findall(r"^\s*\d+\)\s*change_scaling %s (\S+)" % key, _src, re.M)
        if name == "Breakout":
            d9 = re.findall(r"^\s*9\)\s*change_scaling (\S+) (\S+)", _src, re.M)
            check(f"S9 item 9 dispatches change_scaling {key} {attr}", d9 == [(key, attr)], f"9) -> {d9}")
        else:
            check(f"S9 NO menu item dispatches {key} (r228: the {name} trade is off)", disp == [], f"{disp}")
        off, p_off = _run(f'change_scaling {key} {attr} "{name}"', {key: "1"}, "n\n")
        on, p_on = _run(f'change_scaling {key} {attr} "{name}"', {key: "0"}, "y\n")
        c_off = _cfg({key: off.get(key, "")}, f"config.{attr}")
        c_on = _cfg({key: on.get(key, "")}, f"config.{attr}")
        check(f"S9 item {item} 'n' writes {key}=0 and config reads OFF; 'y' writes 1 and reads ON",
              off.get(key) == "0" and c_off == "False" and on.get(key) == "1" and c_on == "True"
              and "RELOAD_CALLED" in p_off.stderr and "RELOAD_CALLED" in p_on.stderr
              and "MISSING_COMMAND" not in p_off.stderr + p_on.stderr,
              f"n->{off.get(key)!r}/{c_off} y->{on.get(key)!r}/{c_on}")
vals, p = _run("change_risk", {"OT_RISK_USD": "1050", "OT_ORB_RISK_USD": "1001"}, "1100\n")
check("S9 item 2 sets the MIN and REMOVES the leftover OT_ORB_RISK_USD",
      vals.get("OT_RISK_USD") == "1100" and "OT_ORB_RISK_USD" not in vals
      and "MISSING_COMMAND" not in p.stderr,
      f"after: {vals} rc={p.returncode} {p.stderr.strip()[-120:]}")

# ── S10 — OFF refuses a contract dearer than the MIN ────────────────────────
setsw(orb=False)
x = size(orb(600.80, premium=12.00))          # $1,200 a contract > $1,050
check("S10 ORB OFF, one contract $1,200 > the $1,050 MIN: REFUSED, not floored to 1",
      not x.allowed and x.contracts == 0, f"allowed={x.allowed} n={x.contracts} {x.reject_reason}")
setsw()

print()
if FAIL:
    print(f"RED — {len(FAIL)} failed: {sorted(set(FAIL))}")
    sys.exit(1)
print("GREEN — every switch moves only its own trade's size")
sys.exit(0)
