#!/usr/bin/env python3
"""
tests/check_retired_gone.py  v5.0
v5.0  2026-11-08  OTV5 r76 (RETIRE.1) — THE RETIRED TRADES ARE GONE, THE LIVE ONES ARE WIRED, THE ENGINE STAYS.
      The operator, 2026-11-07: "The orb engine is a trading state distinctly different from the orb 'trade' which
      was retired. Running dead code and logging dead code activity is unnecessary drag. Yes, I want all of those
      things fixed."

  G1  nothing live imports any of the nine removed modules (checked before the lander's DEL step, so not by file)
  G2  no live file (outside tests/ and docs/) imports them, names their classes or calls the removed functions
  G3  plan_state, ENTRY_WINDOWS and the admission table hold the live trades and no removed one
  G4  config carries none of the removed keys; SWEEP_CS_MAX_REJECTION_PCT (derived/levels) and the ramp TOP stay
  G5  main still builds and dispatches the five live setups and the TCS shadow, and the removed singletons are gone
  G6  the opening-range ENGINE is intact: its module imports and keeps the API Runaway, Breakout and the Hunt use
  G7  the start banner: ramp_top= and scaling BRK=, no scaling ORB / VOLT, no ORCS=, no contract_scale=
  G8  tools/strip_retired_env.sh on a scratch unit: removes exactly the retired lines, keeps every other line,
      prints no value, is idempotent, and --check changes nothing
  G9  the kept helpers still answer: orb_plan.select_contract (Breakout) and sweep_credit_spread.strike_beyond_sweep
      / is_breach_exit (TCS shadow, trade_logger)

Run:  python3 tests/check_retired_gone.py      (exit 0 = all pass)
"""
import os
import re
import subprocess
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_SCR = tempfile.mkdtemp(prefix="check_retired_gone_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived_store.db"),
               ("OT_RESTING_DB", "resting_orders.db"), ("OT_SIGNAL_JOURNAL_DIR", "signal_journal")):
    os.environ.setdefault(_k, os.path.join(_SCR, _f))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAIL = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(label.split()[0])


REMOVED_MODULES = ("strategy/orb_strategy.py", "strategy/volt_strategy.py", "strategy/volt_plan.py",
                   "strategy/atp_butterfly.py", "strategy/atp_butterfly_plan.py", "strategy/orcs.py",
                   "strategy/orcs_plan.py", "strategy/sweep_plan.py", "execution/handoff.py")
REMOVED_TRADES = ("ORBStrategy", "VOLT", "ATPButterfly", "OpeningRangeCreditSpread", "SweepCreditSpread")
LIVE_TRADES = ("RunawayContinuation", "Breakout", "LiquidityHunt", "PARK", "GEXPinButterfly", "TrendCreditSpread")

# ── G1 ───────────────────────────────────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(ROOT, "tests"))
from retired_names import importers                            # noqa: E402
# ⚠️ NOT A FILE-ABSENCE TEST: the lander runs every CHECK before its DEL step, so the payload's deleted files are
# still on disk while this runs. What matters on a box is that nothing live imports them.
_live_imp = {m: importers(m[:-3].replace("/", ".")) for m in REMOVED_MODULES}
_live_imp = {k: v for k, v in _live_imp.items() if v}
check("G1 nothing live imports any of the nine removed modules", not _live_imp, str(_live_imp))

# ── G2 ───────────────────────────────────────────────────────────────────────────────────────────────
PAT = re.compile(
    r"(strategy\.(orb_strategy|volt_strategy|volt_plan|atp_butterfly|atp_butterfly_plan|orcs|orcs_plan|sweep_plan)\b"
    r"|from strategy import (orb_strategy|volt_strategy|volt_plan|atp_butterfly|orcs|orcs_plan|sweep_plan)\b"
    r"|execution import handoff\b|execution\.handoff\b"
    r"|\b(ORBStrategy|VoltStrategy|SweepCreditSpreadStrategy|ATPButterflyStrategy|OpeningRangeCreditSpread)\("
    r"|\b(_attempt_orcs|_attempt_sweep_on_grant|_sweep_stop_premium|_evaluate_volt|_sweep_breach_accepted"
    r"|_velocity_stall|_place_standing_offer|_mark_orb_confirmation_spent|_is_standing_offer)\b"
    r"|\b(_orb_strategy|_volt_strategy|_sweep_cs_strategy|_atp_bfly_strategy|_orcs_strategy)\b)")
hits = []
for dp, dn, fn in os.walk(ROOT):
    rel = os.path.relpath(dp, ROOT)
    if rel.split(os.sep)[0] in ("tests", "docs", ".git") or "__pycache__" in dp:
        continue
    for f in fn:
        if not f.endswith(".py"):
            continue
        p = os.path.join(dp, f)
        for i, line in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
            s = line.strip()
            if s.startswith("#") or not PAT.search(line):
                continue
            hits.append(f"{os.path.relpath(p, ROOT)}:{i}")
# a docstring mention is history, not code: keep only lines that are not inside a triple-quoted block
def _code_hits(hs):
    out = []
    for h in hs:
        path, ln = h.rsplit(":", 1)
        src = open(os.path.join(ROOT, path), encoding="utf-8", errors="replace").read().split("\n")
        n = int(ln) - 1
        depth = sum(l.count('"""') for l in src[:n]) % 2
        if depth == 0:
            out.append(h)
    return out
code = _code_hits(hits)
check("G2 no live file imports a removed module, builds a removed class or calls a removed function",
      not code, str(code[:6]))

# ── G3 ───────────────────────────────────────────────────────────────────────────────────────────────
import config                                                   # noqa: E402
config.LOG_FILE = os.path.join(_SCR, "bot.log")
from strategy import plan_state as PS                           # noqa: E402
from execution import position_manager as PMOD                 # noqa: E402
tab, ew, adm = set(PS.TABLE), set(config.ENTRY_WINDOWS), set(PMOD.rules())
gone = [n for n in REMOVED_TRADES if n in tab or n in ew or n in adm]
missing = [n for n in LIVE_TRADES if n not in tab or n not in ew or n not in adm]
dorm = [n for n in REMOVED_TRADES if PS.state(n) == PS.ACTIVE]
check("G3 plan_state / ENTRY_WINDOWS / admission: every live trade present, no removed one",
      not gone and not missing, f"still present {gone}, missing live {missing}")
check("G3b a removed name is never ACTIVE through a stale alias (ALIAS holds no removed trade)",
      not any(v in REMOVED_TRADES or k in ("ORB", "SweepForLeg2") for k, v in PS.ALIAS.items()), str(PS.ALIAS))

# ── G4 ───────────────────────────────────────────────────────────────────────────────────────────────
bad = sorted(n for n in dir(config) if re.match(
    r"^(VOLT_|ORCS_|ATP_|VELOCITY_|SCALE_ORB$|SCALE_VOLT$|CONTRACT_SCALE|HANDOFF_TTL_TICKS$|SWEEP_CS_)", n)
    and n != "SWEEP_CS_MAX_REJECTION_PCT")
check("G4 config carries no removed key (SWEEP_CS_MAX_REJECTION_PCT stays for derived/levels)",
      not bad and hasattr(config, "SWEEP_CS_MAX_REJECTION_PCT"), str(bad))
check("G4b the ramp TOP and the engine cutoff are unchanged (OT_ORB_BUDGET_USD read; ORB_NO_ENTRY_AFTER_ET = entries stop)",
      hasattr(config, "ORB_BUDGET_USD") and tuple(config.ORB_NO_ENTRY_AFTER_ET)
      == tuple(config.EOD_SCHEDULE["entries_stop"]) and hasattr(config, "DELTA_PAR")
      and hasattr(config, "BREAKOUT_DELTA_PAR"), f"{getattr(config, 'ORB_NO_ENTRY_AFTER_ET', None)}")

# ── G5 ───────────────────────────────────────────────────────────────────────────────────────────────
import logging                                                  # noqa: E402
logging.disable(logging.CRITICAL)
import main as M                                                # noqa: E402
src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
want = {"_runaway_strategy": "RunawayContinuationStrategy", "_liquidity_hunt": "LiquidityHunt",
        "_breakout": "Breakout", "_park_strategy": "Park", "_gex_bfly_strategy": "GEXPinButterflyStrategy",
        "_trend_credit_strategy": "TrendCreditSpread"}
wired = {k: type(getattr(M, k, None)).__name__ for k in want}
calls = all(c in src for c in ('_safe_strategy("RunawayContinuation"', '_safe_strategy("Breakout"',
                                '_safe_strategy("LiquidityHunt"', '_safe_strategy("PARK"',
                                '_safe_strategy("GEXPinButterfly"', '_attempt_hunt(', '_attempt_park(',
                                '_attempt_butterfly('))
check("G5 main builds the five live setups and the TCS shadow and dispatches each",
      wired == want and calls, f"{wired} calls={calls}")
check("G5b the removed singletons are gone from main",
      not any(hasattr(M, n) for n in ("_orb_strategy", "_volt_strategy", "_sweep_cs_strategy",
                                      "_atp_bfly_strategy", "_orcs_strategy", "_handoff")))

# ── G6 ───────────────────────────────────────────────────────────────────────────────────────────────
from analysis import orb_engine as OE                           # noqa: E402
api = ("get_orb_engine", "ORBState")
eng_api = ("update", "release_unowned", "rebuild_from_tape", "state_snapshot", "load_state_file",
           "mark_triggered", "notify_position_closed", "mark_order_placed", "take_missed_confirmation")
eng = OE.get_orb_engine()
miss = [a for a in api if not hasattr(OE, a)] + [a for a in eng_api if not hasattr(eng, a)]
check("G6 the opening-range ENGINE keeps its module API and every method its readers use", not miss, str(miss))

# ── G7 ───────────────────────────────────────────────────────────────────────────────────────────────
b0 = src.index('f"Service mode:')
banner = src[b0:src.index("_banner_dials()", b0)]
check("G7 the banner says ramp_top= and scaling BRK=, and no scaling ORB / VOLT, ORCS= or contract_scale=",
      "ramp_top=" in banner and "scaling BRK=" in banner and not re.search(
          r"orb_budget=|scaling ORB=|VOLT=|ORCS=|contract_scale=", banner), banner[:160].replace("\n", " "))

# ── G8 ───────────────────────────────────────────────────────────────────────────────────────────────
tool = os.path.join(ROOT, "tools", "strip_retired_env.sh")
unit = os.path.join(_SCR, "optionsbot.service")
KEEP = ["[Unit]", "Description=x", "[Service]", "Environment=TT_USERNAME=SECRETVALUE1",
        "Environment=OT_ORB_BUDGET_USD=10000", "Environment=OT_RISK_USD=1050", "Environment=OT_VOLTAGE=9",
        "Environment=OT_SCALE_BREAKOUT=1", "Environment=OT_TCS_ACTIVE=log", "Environment=OT_ORCS_NOTE_X=keep"]
DROP = ["Environment=OT_SCALE_ORB=1", "Environment=OT_SCALE_VOLT=1", "Environment=OT_VOLT=0",
        "Environment=OT_VOLT_BUDGET_USD=SECRETVALUE2", "Environment=OT_ORB_TRADE=0", "Environment=OT_ATP_BUTTERFLY=0",
        "Environment=OT_ORCS=0", "Environment=OT_SWEEP_CS=0", "Environment=OT_SWEEP_CS_WING=5",
        "Environment=OT_CONTRACT_SCALE=7.5", "Environment=OT_VELOCITY_ENFORCE=0"]
open(unit, "w").write("\n".join(KEEP[:3] + DROP[:6] + KEEP[3:] + DROP[6:] + ["ExecStart=/bin/true"]) + "\n")
env = dict(os.environ, OT_STRIP_NO_RELOAD="1")
chk = subprocess.run(["bash", tool, "--check", unit], capture_output=True, text=True, env=env)
after_chk = open(unit).read()
run1 = subprocess.run(["bash", tool, unit], capture_output=True, text=True, env=env)
body = open(unit).read().split("\n")
run2 = subprocess.run(["bash", tool, unit], capture_output=True, text=True, env=env)
out = chk.stdout + run1.stdout + run2.stdout + chk.stderr + run1.stderr + run2.stderr
check("G8 --check counts 11 and changes nothing", "11 retired line(s) would go" in chk.stdout
      and after_chk.count("\n") == len(KEEP) + len(DROP) + 1, chk.stdout.strip())
check("G8b the run removes exactly the 11 retired lines and keeps every other line, in order",
      run1.returncode == 0 and [l for l in body if l] == KEEP + ["ExecStart=/bin/true"]
      and os.path.exists(unit + ".bak-retire1"), run1.stdout.strip())
check("G8c no value is ever printed (key names and counts only)", "SECRETVALUE" not in out and "=1050" not in out)
check("G8d a second run finds nothing and changes nothing", run2.returncode == 0 and "0 retired line(s)" in run2.stdout,
      run2.stdout.strip())

# ── G9 ───────────────────────────────────────────────────────────────────────────────────────────────
from strategy import orb_plan as OP                             # noqa: E402
from strategy import sweep_credit_spread as SCS                 # noqa: E402
C = lambda k, m, d, b=None, a=None: types.SimpleNamespace(strike=k, mark=m, delta=d, bid=b or m - 0.05,  # noqa: E731
                                                          ask=a or m + 0.05)
ch = types.SimpleNamespace(calls=[C(709, 1.2, 0.45), C(710, 0.9, 0.40), C(711, 0.6, 0.33)], puts=[])
sel = OP.select_contract(ch, "long", 710.2)
check("G9 Breakout's selector still takes the nearest listed live strike (710 for a 710.2 reach)",
      sel is not None and sel.strike == 710, f"{getattr(sel, 'strike', None)}")
check("G9b the kept sweep helpers answer (is_breach_exit; strike_beyond_sweep returns a strike)",
      SCS.is_breach_exit("tcs_breach: x") and not SCS.is_breach_exit("nickel_close")
      and SCS.strike_beyond_sweep(99.4, 100.0, False, contracts=None, increment=1.0) is not None)

print()
if FAIL:
    print(f"FAIL ({len(FAIL)}): {' '.join(FAIL)}")
    sys.exit(1)
print("ALL PASS")
