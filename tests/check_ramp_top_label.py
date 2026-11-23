#!/usr/bin/env python3
"""tests/check_ramp_top_label.py — v5.1
v5.1  2026-11-23  OTV5 r153 (TRIM.2) — R4 RE-POINTED (WA 38.4): the Hunt and OGAP are retired (DORMANT, no switch), so R4's
      live setups are Runaway and PARK (ACTIVE) and the Hunt and OGAP read DORMANT; R1-R3, R5, R6 unchanged.
v5.0  2026-11-21  OTV5 r141 (RAMP.1; the Saturday brief 2026-11-21 R5a, section 5 item 2) — THE RAMP TOP SIZES ONLY
      BREAKOUT, WHICH IS DORMANT, AND WHAT THE OPERATOR SEES SAYS SO. OT_BREAKOUT_BUDGET_USD is read only by
      risk/risk_manager._size_geometry, which only a signal carrying `sizes_on_geometry` reaches (main._geometry_inputs
      gives every other signal (0, 0), so size_for takes the budget rule on RISK_PER_TRADE_USD), only
      strategy/breakout_plan.py sets that flag, and Breakout is DORMANT with no switch since r110. Runaway, the Hunt,
      PARK and OGAP size on OT_RISK_USD. Before cash the operator sets "size, ramp and cap"; the banner, configure.sh
      item 7 and the bootstrap template presented the ramp as live. This gate pins the claim and the text together, so
      a change that makes the ramp live again turns R1-R5 red before the label can lie.

R1  outside tests/, BREAKOUT_BUDGET_USD is named only in config.py (its definition), main.py (the banner) and
    risk/risk_manager.py, where every use but the import sits inside _size_geometry
R2  main._geometry_inputs returns (0.0, 0.0) unless the signal carries sizes_on_geometry, and _execute_entry_signal
    passes its result to size_for (so no other signal reaches the geometry rule)
R3  outside tests/, the only code that sets sizes_on_geometry = True is strategy/breakout_plan.py
R4  plan_state: Breakout is DORMANT by default with no switch key; Runaway and PARK are ACTIVE (r153: the Hunt and
    OGAP are DORMANT, retired)
R5  EXECUTED (two child interpreters, OT_RISK_USD=1050, OT_BREAKOUT_BUDGET_USD=1 vs 1000000): the budget rule
    (no geometry) sizes the same contracts under both ramp tops; CONTROL: the geometry rule does not (the key bites
    only there)
R6  the text: the Service line's ramp_top= is followed by "(Breakout only - dormant r110; live setups size on risk=)",
    the interactive start line says "Breakout only - dormant r110", configure.sh item 7 and its screen say
    "Breakout only - dormant", and the bootstrap template's item-7 line says "Breakout only - dormant r110"
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
Run:  venv/bin/python tests/check_ramp_top_label.py
"""
import ast
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  [{detail}]"))
    if not ok:
        FAILED.append(name.split()[0])


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def code_files():
    for d, dirs, files in os.walk(ROOT):
        rel = os.path.relpath(d, ROOT)
        top = rel.split(os.sep)[0]
        if top in ("tests", ".git", "venv", "__pycache__") or "/__pycache__" in d:
            dirs[:] = []
            continue
        for f in files:
            if f.endswith(".py"):
                yield os.path.normpath(os.path.join(rel, f))


print("check_ramp_top_label — the ramp TOP sizes Breakout only (dormant), and the labels say so")

# ── R1 ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
named, outside = {}, []
for rel in code_files():
    try:
        tree = ast.parse(read(rel))
    except (SyntaxError, UnicodeDecodeError):
        continue
    hits = [n for n in ast.walk(tree) if (isinstance(n, ast.Name) and n.id == "BREAKOUT_BUDGET_USD")
            or (isinstance(n, ast.alias) and n.name == "BREAKOUT_BUDGET_USD")
            or (isinstance(n, ast.Attribute) and n.attr == "BREAKOUT_BUDGET_USD")]
    if hits:
        named[rel] = len(hits)
    if rel == os.path.join("risk", "risk_manager.py"):
        spans = [(f.lineno, f.end_lineno) for f in ast.walk(tree)
                 if isinstance(f, ast.FunctionDef) and f.name == "_size_geometry"]
        for n in hits:
            if isinstance(n, ast.alias):
                continue
            if not any(a <= n.lineno <= b for a, b in spans):
                outside.append(n.lineno)
check("R1 BREAKOUT_BUDGET_USD is named only in config, main (the banner) and risk_manager._size_geometry",
      set(named) == {"config.py", "main.py", os.path.join("risk", "risk_manager.py")} and not outside,
      "named in %s; risk_manager uses outside _size_geometry at %s" % (sorted(named), outside))

# ── R2 ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
main_src = read("main.py")
_gi = main_src[main_src.find("def _geometry_inputs(signal):"):]
_gi = _gi[:_gi.find("\ndef ", 10)]
check("R2 main._geometry_inputs gives (0, 0) to a signal without sizes_on_geometry, and the funnel passes it to size_for",
      'if not getattr(signal, "sizes_on_geometry", False):\n        return 0.0, 0.0' in _gi
      and "orb_width           = _orb_w," in main_src and "orb_stop_distance   = _orb_d," in main_src
      and "_orb_w, _orb_d = _geometry_inputs(signal)" in main_src,
      "the geometry hand-off changed")

# ── R3 ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
setters = []
for rel in code_files():
    try:
        tree = ast.parse(read(rel))
    except (SyntaxError, UnicodeDecodeError):
        continue
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Attribute) and t.attr == "sizes_on_geometry"
                                             for t in n.targets):
            if isinstance(n.value, ast.Constant) and n.value.value is True:
                setters.append(rel)
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "setattr" and len(n.args) >= 2 \
                and isinstance(n.args[1], ast.Constant) and n.args[1].value == "sizes_on_geometry":
            setters.append(rel + " (setattr)")
check("R3 only strategy/breakout_plan.py sets sizes_on_geometry = True",
      setters == [os.path.join("strategy", "breakout_plan.py")], "setters: %s" % setters)

# ── R4 / R5: child interpreters (config reads the env at import) ────────────────────────────────────────────────────
PROG = r"""
import json, os, sys
sys.path.insert(0, os.getcwd())
from strategy import plan_state as ps
from risk.risk_manager import RiskManager
import config
rm = RiskManager(paper_trading=True)
plain = rm.size_for("long_debit", premium=2.00, grade="UNGRADED")
geo = rm.size_for("long_debit", premium=0.50, orb_width=6.0, orb_stop_distance=0.5, grade="UNGRADED")
print(json.dumps({
  "top": config.BREAKOUT_BUDGET_USD, "risk": config.RISK_PER_TRADE_USD,
  "plain": [plain.allowed, plain.contracts, plain.rule], "geo": [geo.allowed, geo.contracts, geo.rule],
  "brk": [ps.default("Breakout"), ps.switch("Breakout"), ps.state("Breakout")],
  "live": {n: ps.state(n) for n in ("RunawayContinuation", "LiquidityHunt", "PARK", "OGAP")},
}))
"""


def child(top):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OT_BREAKOUT", "OT_ORB_", "OT_RUNAWAY", "OT_HUNT",
                                                                     "OT_PARK", "OT_SCALE"))}
    env.update(OT_RISK_USD="1050", OT_BREAKOUT_BUDGET_USD=str(top), OT_INSTRUMENT=env.get("OT_INSTRUMENT", "QQQ"))
    r = subprocess.run([sys.executable, "-c", PROG], cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        if "ModuleNotFoundError" in r.stderr or "ImportError" in r.stderr:
            print("NOT RUN — the imports cannot load under %s: %s" % (sys.executable, r.stderr.strip().splitlines()[-1]))
            sys.exit(2)
        return {"error": r.stderr.strip()[-400:]}
    return json.loads(r.stdout.strip().splitlines()[-1])


lo, hi = child(1), child(1000000)
ok4 = ("error" not in lo and lo["brk"] == ["dormant", "", "dormant"]
       and lo["live"] == {"RunawayContinuation": "active", "LiquidityHunt": "dormant", "PARK": "active", "OGAP": "dormant"})
check("R4 Breakout is DORMANT with no switch; Runaway and PARK are ACTIVE; the Hunt and OGAP DORMANT (retired r153)", ok4,
      lo.get("error") or (lo["brk"], lo["live"]))
ok5 = ("error" not in lo and "error" not in hi and lo["top"] == 1.0 and hi["top"] == 1000000.0
       and lo["plain"] == hi["plain"] and lo["plain"][0] and lo["plain"][1] == 5 and lo["plain"][2] == "budget"
       and lo["geo"] != hi["geo"])
check("R5 EXECUTED: the budget rule sizes 5 contracts at $2.00 under a $1 and a $1,000,000 ramp TOP (OT_RISK_USD 1050); "
      "CONTROL: the geometry rule does not", ok5, (lo.get("error") or hi.get("error") or (lo, hi)))

# ── R6: the text ────────────────────────────────────────────────────────────────────────────────────────────────────
cfg_sh, boot = read("configure.sh"), read("bootstrap.example.sh")
_i = main_src.find('f" · ramp_top=${BREAKOUT_BUDGET_USD:.0f}"')
_svc = main_src[_i:_i + 400] if _i >= 0 else ""
_item7 = [ln for ln in cfg_sh.splitlines() if "${BOLD}7.${RESET}  Ramp TOP (MAX)" in ln]
_scr = cfg_sh[cfg_sh.find("change_orb_budget() {"):]
_scr = _scr[:_scr.find("\n}\n")]
_bl = [ln for ln in boot.splitlines() if "OT_BREAKOUT_BUDGET_USD=" in ln and "configure.sh item 7" in ln]
check("R6 the Service line, the start line, configure.sh item 7 and its screen, and the bootstrap template say "
      "Breakout only - dormant",
      '(Breakout only - dormant r110; live setups size on risk=)' in _svc
      and 'Ramp top:      ${BREAKOUT_BUDGET_USD:.0f} (Breakout only - dormant r110; live setups size on Risk/trade)' in main_src
      and "per setup" not in main_src[main_src.find("  Ramp top:"):main_src.find("  Ramp top:") + 120]
      and len(_item7) == 1 and "Breakout only - dormant r110" in _item7[0]
      and "Breakout only - dormant (r110)." in _scr and "size on item 2 (Risk/trade, OT_RISK_USD)" in _scr
      and len(_bl) == 1 and "Breakout only - dormant r110" in _bl[0],
      "service=%r item7=%r boot=%r" % (_svc[:160], _item7, _bl))

print()
if FAILED:
    print("FAILED: " + ", ".join(FAILED))
    sys.exit(1)
print("GREEN — the ramp TOP sizes Breakout only, which is dormant, and every label says so (R1-R6)")
