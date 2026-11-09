#!/usr/bin/env python3
"""
tests/check_retired_gone.py  v5.3
v5.3  2026-11-09  OTV5 r103 (RETIRE.5 step 2) - THE GEX PIN BUTTERFLY IS GONE TOO. The operator, 2026-11-08: "I concur on both, in that
      order". G1/G2 add strategy/gex_pin_butterfly.py and its names (GEXPinButterflyStrategy, _gex_bfly_strategy,
      _attempt_butterfly, mark_pin_played); G3 moves GEXPinButterfly to the removed trades; G4 adds GEX_BFLY_* /
      GEX_BUTTERFLY_ENABLED / HOLD_TO_CLOSE_STRATEGIES and the fly's debit and window keys; G5 is the four live setups
      and G5b the fly's singleton; new G12 (the strip tool takes OT_GEX_BUTTERFLY, OT_BFLY_* and OT_GEX_BFLY_* off a
      unit).
v5.2  2026-11-08  OTV5 r88 (RETIRE.3) - THE TCS SHADOW IS GONE TOO. The operator, 2026-11-08: "Delete". G1/G2 add the three
      TCS shadow modules and their names; G3 moves TrendCreditSpread to the removed trades; G4 adds the TCS_* / TREND_CREDIT
      keys; G5 is the five live setups and G5b the TCS singletons and shadow passes; G9b pins strike_beyond_sweep gone. New
      G10 (no runtime reader is left: readiness, management, exits, warehouse, plan state, main; G10b the credit window is
      value-identical) and G11 (the strip tool takes the TCS keys off a unit; G11b it never overwrites .bak-retire1). The
      G8 fixtures' kept key is OT_PARK=log where it was OT_TCS_ACTIVE=log, which r88 retires.
v5.1  2026-11-08  OTV5 r78 (RETIRE.2) - G8e-G8h: the strip tool on units as setup_ec2.sh / configure.sh write them
      (Environment="KEY=v", 'KEY=v', several assignments a line, an unparsable line). v5.0 of the tool matched none
      of the quoted lines and reported 0 on 14/14 boxes that each still held two retired keys.
v5.0  2026-11-08  OTV5 r76 (RETIRE.1) — THE RETIRED TRADES ARE GONE, THE LIVE ONES ARE WIRED, THE ENGINE STAYS.
      The operator, 2026-11-07: "The orb engine is a trading state distinctly different from the orb 'trade' which
      was retired. Running dead code and logging dead code activity is unnecessary drag. Yes, I want all of those
      things fixed."

  G1  nothing live imports any of the nine removed modules (checked before the lander's DEL step, so not by file)
  G2  no live file (outside tests/ and docs/) imports them, names their classes or calls the removed functions
  G3  plan_state, ENTRY_WINDOWS and the admission table hold the live trades and no removed one
  G4  config carries none of the removed keys; SWEEP_CS_MAX_REJECTION_PCT (derived/levels) and the ramp TOP stay
  G5  main still builds and dispatches the five live setups (r88: no TCS shadow), and the removed singletons are gone
  G6  the opening-range ENGINE is intact: its module imports and keeps the API Runaway, Breakout and the Hunt use
  G7  the start banner: ramp_top= and scaling BRK=, no scaling ORB / VOLT, no ORCS=, no contract_scale=
  G8  tools/strip_retired_env.sh on a scratch unit: removes exactly the retired lines, keeps every other line,
      prints no value, is idempotent, and --check changes nothing; G8e-G8h the quoted, single-quoted, mixed and
      unparsable forms (RETIRE.2)
  G9  the kept helpers still answer: orb_plan.select_contract (Breakout) and sweep_credit_spread.is_breach_exit
      (trade_logger); strike_beyond_sweep went with the TCS (r88)
  G10 (r88) no runtime reader of the TCS shadow is left; G10b the credit window is value-identical without its row
  G11 (r88) the strip tool takes OT_TCS_* / OT_TR_TCS_* / OT_TR_W_TCS_* / OT_SHADOW_TRADES_DB off a unit; G11b it
      never overwrites an existing .bak-retire1

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
                   "strategy/orcs_plan.py", "strategy/sweep_plan.py", "execution/handoff.py",
                   # r88 (RETIRE.3): the TCS shadow
                   "strategy/trend_credit_spread.py", "strategy/tcs_plan.py", "execution/shadow_book.py",
                   # r103 (RETIRE.5): the GEX pin butterfly
                   "strategy/gex_pin_butterfly.py")
REMOVED_TRADES = ("ORBStrategy", "VOLT", "ATPButterfly", "OpeningRangeCreditSpread", "SweepCreditSpread",
                  "TrendCreditSpread",                                                     # r88
                  "GEXPinButterfly")                                                       # r103
LIVE_TRADES = ("RunawayContinuation", "Breakout", "LiquidityHunt", "PARK")

# ── G1 ───────────────────────────────────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(ROOT, "tests"))
from retired_names import importers                            # noqa: E402
# ⚠️ NOT A FILE-ABSENCE TEST: the lander runs every CHECK before its DEL step, so the payload's deleted files are
# still on disk while this runs. What matters on a box is that nothing live imports them.
_live_imp = {m: importers(m[:-3].replace("/", ".")) for m in REMOVED_MODULES}
_live_imp = {k: v for k, v in _live_imp.items() if v}
check("G1 nothing live imports any of the thirteen removed modules (r88: + the three TCS shadow modules; r103: + the GEX fly)", not _live_imp,
      str(_live_imp))

# ── G2 ───────────────────────────────────────────────────────────────────────────────────────────────
PAT = re.compile(
    r"(strategy\.(orb_strategy|volt_strategy|volt_plan|atp_butterfly|atp_butterfly_plan|orcs|orcs_plan|sweep_plan)\b"
    r"|from strategy import (orb_strategy|volt_strategy|volt_plan|atp_butterfly|orcs|orcs_plan|sweep_plan)\b"
    r"|execution import handoff\b|execution\.handoff\b"
    r"|strategy\.(trend_credit_spread|tcs_plan)\b|from strategy import (trend_credit_spread|tcs_plan)\b"      # r88
    r"|execution import shadow_book\b|execution\.shadow_book\b|\b(TrendCreditSpread|TCSPlan|ShadowBook)\("
    r"|\b(_shadow_manage|_shadow_eod|_shadow_resume|_retired_reason|_trend_credit_strategy|strike_beyond_sweep"
    r"|is_trend_participation|TREND_CREDIT_ACTIVE|TCS_MODE|SHADOW_TRADES_DB)\b"
    r"|strategy\.gex_pin_butterfly\b|from strategy import gex_pin_butterfly\b"                          # r103
    r"|\b(GEXPinButterflyStrategy|_gex_bfly_strategy|_attempt_butterfly|mark_pin_played|GEX_BUTTERFLY_ENABLED"
    r"|HOLD_TO_CLOSE_STRATEGIES)\b"
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
    r"^(VOLT_|ORCS_|ATP_|VELOCITY_|SCALE_ORB$|SCALE_VOLT$|CONTRACT_SCALE|HANDOFF_TTL_TICKS$|SWEEP_CS_"
    r"|TCS_|_TCS_|_tcs_|TREND_CREDIT_ACTIVE$"                                            # r88: the TCS keys
    r"|GEX_BFLY_|GEX_BUTTERFLY_ENABLED$|HOLD_TO_CLOSE_STRATEGIES$|BUTTERFLY_MAX_DEBIT|BUTTERFLY_MIN_DEBIT"
    r"|BUTTERFLY_DEBIT_CEILING$|BUTTERFLY_DISC_CONV_|BUTTERFLY_ENTRY_|BUTTERFLY_WING_|BUTTERFLY_GEX_PIN"
    r"|VIX_BUTTERFLY_HALF_SIZE$)", n)                                                    # r103: the GEX fly keys
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
        "_breakout": "Breakout", "_park_strategy": "Park"}                       # r103: the GEX fly removed
wired = {k: type(getattr(M, k, None)).__name__ for k in want}
calls = all(c in src for c in ('_safe_strategy("RunawayContinuation"', '_safe_strategy("Breakout"',
                                '_safe_strategy("LiquidityHunt"', '_safe_strategy("PARK"',
                                '_attempt_hunt(', '_attempt_park('))
check("G5 main builds the four live setups and dispatches each (r88: the TCS shadow removed; r103: the GEX fly)",
      wired == want and calls, f"{wired} calls={calls}")
check("G5b the removed singletons are gone from main",
      not any(hasattr(M, n) for n in ("_orb_strategy", "_volt_strategy", "_sweep_cs_strategy",
                                      "_atp_bfly_strategy", "_orcs_strategy", "_handoff",
                                      # r88 (RETIRE.3)
                                      "_trend_credit_strategy", "_retired_reason", "_shadow_manage",
                                      "_gex_bfly_strategy", "_attempt_butterfly",                       # r103
                                      "_shadow_eod", "_shadow_resume")))

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
        "Environment=OT_SCALE_BREAKOUT=1", "Environment=OT_PARK=log", "Environment=OT_ORCS_NOTE_X=keep"]   # r88: OT_TCS_ACTIVE is retired now
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

# ── G8e-G8h: the units as setup_ec2.sh / configure.sh write them (RETIRE.2: v5.0 matched none of these) ─────
unit2 = os.path.join(_SCR, "optionsbot_q.service")
KEEP2 = ["[Service]", 'Environment="TT_USERNAME=SECRETVALUE3"', 'Environment="OT_ORB_BUDGET_USD=10000"',
         "Environment='OT_RISK_USD=1050'", 'Environment="OT_VOLTAGE=9"']
DROP2 = ['Environment="OT_SCALE_ORB=1"', 'Environment="OT_SCALE_VOLT=1"', "Environment='OT_VOLT_BUDGET_USD=SECRETVALUE4'",
         'Environment="OT_VELOCITY_ENFORCE=0" "OT_SWEEP_CS=0"']
MIXED = 'Environment="OT_PARK=log" "OT_SCALE_ORB=1" OT_SCALE_BREAKOUT=1'            # r88: OT_TCS_ACTIVE is retired now
MIXED_SQ = "Environment='OT_NOTE=a b' OT_SCALE_VOLT=1"          # a single-quoted value holding a space
open(unit2, "w").write("\n".join(KEEP2[:2] + DROP2[:2] + [MIXED] + KEEP2[2:] + DROP2[2:] + [MIXED_SQ]
                                 + ["ExecStart=/bin/true"]) + "\n")
chk2 = subprocess.run(["bash", tool, "--check", unit2], capture_output=True, text=True, env=env)
run3 = subprocess.run(["bash", tool, unit2], capture_output=True, text=True, env=env)
body2 = [l for l in open(unit2).read().split("\n") if l]
run4 = subprocess.run(["bash", tool, unit2], capture_output=True, text=True, env=env)
out2 = chk2.stdout + run3.stdout + run4.stdout + chk2.stderr + run3.stderr + run4.stderr
check('G8e the quoted form (Environment="KEY=v" and \'KEY=v\') is found: --check counts 7 assignments',
      "7 retired line(s) would go" in chk2.stdout, chk2.stdout.strip())
check("G8f a line of only retired assignments goes; a mixed line keeps its live assignments verbatim",
      run3.returncode == 0 and body2 == KEEP2[:2] + ['Environment="OT_PARK=log" OT_SCALE_BREAKOUT=1']
      + KEEP2[2:] + ["Environment='OT_NOTE=a b'", "ExecStart=/bin/true"], f"{len(body2)} lines kept")
check("G8g quoted units: no value printed, and a second run is clean",
      "SECRETVALUE" not in out2 and "=1050" not in out2 and run4.returncode == 0 and "0 retired line(s)" in run4.stdout,
      run4.stdout.strip())
unit3 = os.path.join(_SCR, "optionsbot_bad.service")
BAD = 'Environment="OT_SCALE_ORB=1'
open(unit3, "w").write("[Service]\n" + BAD + "\nEnvironment=OT_VOLT=0\n")
run5 = subprocess.run(["bash", tool, unit3], capture_output=True, text=True, env=env)
b3 = open(unit3).read().split("\n")
check("G8h an unparsable line is left exactly as it was and the run exits 1 (the parsable retired line still goes)",
      run5.returncode == 1 and BAD in b3 and "Environment=OT_VOLT=0" not in b3, run5.stdout.strip())

# ── G9 ───────────────────────────────────────────────────────────────────────────────────────────────
from strategy import orb_plan as OP                             # noqa: E402
from strategy import sweep_credit_spread as SCS                 # noqa: E402
C = lambda k, m, d, b=None, a=None: types.SimpleNamespace(strike=k, mark=m, delta=d, bid=b or m - 0.05,  # noqa: E731
                                                          ask=a or m + 0.05)
ch = types.SimpleNamespace(calls=[C(709, 1.2, 0.45), C(710, 0.9, 0.40), C(711, 0.6, 0.33)], puts=[])
sel = OP.select_contract(ch, "long", 710.2)
check("G9 Breakout's selector still takes the nearest listed live strike (710 for a 710.2 reach)",
      sel is not None and sel.strike == 710, f"{getattr(sel, 'strike', None)}")
check("G9b the kept sweep helper answers (is_breach_exit); strike_beyond_sweep went with the TCS (r88)",
      SCS.is_breach_exit("tcs_breach: x") and not SCS.is_breach_exit("nickel_close")
      and not hasattr(SCS, "strike_beyond_sweep"))

# ── G10 (r88, RETIRE.3): the TCS shadow is gone from every runtime reader ─────────────────────────────
from analysis import trade_readiness as TR                      # noqa: E402
from strategy import management as MG                           # noqa: E402
from warehouse import s3_push as SP                             # noqa: E402
_xe = open(os.path.join(ROOT, "execution", "exit_engine.py"), encoding="utf-8").read()
_xe_code = "\n".join(l for l in _xe.split("\n") if not l.strip().startswith("#"))
_sp = open(os.path.join(ROOT, "warehouse", "s3_push.py"), encoding="utf-8").read()
_ps = open(os.path.join(ROOT, "strategy", "plan_state.py"), encoding="utf-8").read()
_gone10 = {
    "readiness track": "trend_credit_spread" in TR.TradeReadinessEngine.STRATEGIES,
    "management COVERED": "TrendCreditSpread" in MG.COVERED,
    "exit engine tcs_stop / tcs_breach": ('f"tcs_stop_' in _xe_code or 'f"tcs_breach' in _xe_code),
    "s3_push shadow_trades stage": ('("shadow_trades"' in _sp or hasattr(SP, "SHADOW_TRADES_DB")),
    "plan_state OT_TCS_ACTIVE": 'os.environ.get("OT_TCS_ACTIVE"' in _ps,
    "main._credit_window_end reads the TCS plan": "tcs_plan" in src[src.index("def _credit_window_end"):
                                                               src.index("def _post_credit_vertical")],
}
check("G10 no runtime reader of the TCS shadow is left (readiness, management, exits, warehouse, plan state, main)",
      not any(_gone10.values()), str([k for k, v in _gone10.items() if v]))
_cv = config
check("G10b the credit window is value-identical without the TCS row (CREDIT_ENTRY_START_ET 11:31; the end = entries stop)",
      tuple(_cv.CREDIT_ENTRY_START_ET) == (11, 31) and tuple(_cv.CONDOR_ENTRY_CUTOFF_ET)
      == tuple(_cv.EOD_SCHEDULE["entries_stop"]) == tuple(_cv.CREDIT_ENTRY_END_ET),
      f"{_cv.CREDIT_ENTRY_START_ET} -> {_cv.CREDIT_ENTRY_END_ET}")

# ── G11 (r88): the strip tool takes the TCS keys off a unit and never overwrites an earlier backup ─────
unit4 = os.path.join(_SCR, "optionsbot_tcs.service")
KEEP4 = ["[Service]", 'Environment="OT_PARK=log"', 'Environment="OT_RISK_USD=1050"']
DROP4 = ['Environment="OT_TCS_ACTIVE=log"', 'Environment="OT_TCS_MIN_POP=0.7"', 'Environment="OT_TR_TCS_MOM_ACC=1"',
         'Environment="OT_TR_W_TCS_ROOM=0.2"', 'Environment="OT_SHADOW_TRADES_DB=/x/shadow_trades.db"']
open(unit4, "w").write("\n".join(KEEP4[:2] + DROP4 + KEEP4[2:] + ["ExecStart=/bin/true"]) + "\n")
open(unit4 + ".bak-retire1", "w").write("THE FIRST BACKUP\n")
run6 = subprocess.run(["bash", tool, unit4], capture_output=True, text=True, env=env)
b4 = [l for l in open(unit4).read().split("\n") if l]
check("G11 the TCS keys (OT_TCS_*, OT_TR_TCS_*, OT_TR_W_TCS_*, OT_SHADOW_TRADES_DB) are stripped; the rest kept",
      run6.returncode == 0 and b4 == KEEP4 + ["ExecStart=/bin/true"] and "removed 5 retired line(s)" in run6.stdout,
      run6.stdout.strip())
check("G11b an existing .bak-retire1 is kept as it was; the new backup is .bak-retire2",
      open(unit4 + ".bak-retire1").read() == "THE FIRST BACKUP\n" and os.path.exists(unit4 + ".bak-retire2")
      and "OT_TCS_ACTIVE" in open(unit4 + ".bak-retire2").read(), run6.stdout.strip())

# ── G12 (r103): the strip tool takes the GEX fly's keys off a unit; the readiness knobs OT_TR_BFLY_* stay ──────
unit5 = os.path.join(_SCR, "optionsbot_bfly.service")
KEEP5 = ["[Service]", 'Environment="OT_PARK=log"', 'Environment="OT_TR_BFLY_PIN_NEAR=0.25"',
         'Environment="OT_RISK_USD=1050"']
DROP5 = ['Environment="OT_GEX_BUTTERFLY=0"', 'Environment="OT_BFLY_DEBIT_CEILING=0.5"',
         'Environment="OT_BFLY_DISC_CONV_LO=0.3"', 'Environment="OT_GEX_BFLY_WING_EM_FRAC=0.25"']
open(unit5, "w").write("\n".join(KEEP5[:2] + DROP5 + KEEP5[2:] + ["ExecStart=/bin/true"]) + "\n")
run7 = subprocess.run(["bash", tool, unit5], capture_output=True, text=True, env=env)
b5 = [l for l in open(unit5).read().split("\n") if l]
check("G12 the GEX fly keys (OT_GEX_BUTTERFLY, OT_BFLY_*, OT_GEX_BFLY_*) are stripped; OT_TR_BFLY_* and the rest kept",
      run7.returncode == 0 and b5 == KEEP5 + ["ExecStart=/bin/true"] and "removed 4 retired line(s)" in run7.stdout,
      run7.stdout.strip())

print()
if FAIL:
    print(f"FAIL ({len(FAIL)}): {' '.join(FAIL)}")
    sys.exit(1)
print("ALL PASS")
