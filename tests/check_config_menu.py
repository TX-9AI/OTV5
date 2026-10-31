#!/usr/bin/env python3
"""
tests/check_config_menu.py  v5.0
v5.0  2026-10-31  OTV5 r68 (CFG.5) — new. THE OPERATOR'S MENU HOLDS WHAT HE SETS, AND NOTHING A STUDY ADDED. The operator,
      2026-10-31, on configure.sh's 17 items: "7. Pin gate, default "on" —remove from the menu"; "9. Scaling, default
      on—take it out"; "10&11–defaults are fine, take them out"; "12, same thing. Trade it—I don't want this toggled";
      "13. Resting stop—I NEVER asked for any of this to be added to config. Resting stop was a study. It failed. Get
      this the fuck out of here"; "15&16-same thing. These are DEAD thesis. Do NOT add anything else to my config
      following a study or test".

  M1  the menu lists EXACTLY the kept items, numbered 1-9 in order: Instrument, Risk/trade ramp MIN, Paper / Live,
      Telegram, TastyTrade credentials, Catastrophic cap, Ramp TOP (MAX), Data capture, Done; the case dispatches 1-9
      and nothing else; the prompt names 1-9 and the out-of-range warning names 1 and 9
  M2  configure.sh never names a removed key outside its changelog (no get_env / set_env / drop_env of
      OT_PIN_PROXIMITY_ACTIVE, OT_SCALE_BREAKOUT, OT_RUNAWAY_END, OT_BREAKOUT_END, OT_BRK_NOPROG, OT_RESTING_STOP,
      OT_PARC, OT_TCS_ACTIVE) and defines none of their label / change functions
  M3  the summary (show_config) prints no line for a removed setting
  M4  with NONE of the keys in the environment, config reads the operator's values: pin gate ON, Breakout scaling
      ON, Runaway's and Breakout's entry ends 10:30 (ENTRY_WINDOWS and the *_ET names), Breakout no-progress
      "trade"; TCS keeps its code default "log" (the r57 shadow: only its menu item left)
  M5  NOT TOGGLED: with every one of those keys set to the OPPOSITE (0, 0, 11:30, 15:40, log) config reads the
      same values as M4 - the keys are not read
  M6  the resting stop is gone: no execution/resting_stop.py, no RESTING_STOP_* in config, and no module under the
      trading tree imports resting_stop or reads OT_RESTING_STOP / OT_RESTING_STOP_STATE (AST: code, not comments)
  M7  the installer does not write a removed key either: setup_ec2.sh writes no Environment= line for any of them
      and bootstrap.example.sh exports none of them
  M8  the Service mode line (the REAL main._banner_dials), with the opposite values exported, names pin_gate=ON,
      runaway_end=10:30, breakout_end=10:30, brk_noprog=trade and no resting_stop
BORN RED on 93c7f93 (base) at M1-M8.
NOT RUN (exit 2), never FAIL, when config cannot be imported (a bare python3).
"""
import ast
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED, RAN = [], []

REMOVED_KEYS = ("OT_PIN_PROXIMITY_ACTIVE", "OT_SCALE_BREAKOUT", "OT_RUNAWAY_END", "OT_BREAKOUT_END",
                "OT_BRK_NOPROG", "OT_RESTING_STOP", "OT_PARC", "OT_TCS_ACTIVE")
REMOVED_FUNCS = ("pin_gate_label", "change_pin_gate", "scaling_label", "scaling_short", "change_scaling",
                 "runaway_end_label", "change_runaway_end", "breakout_end_label", "change_breakout_end",
                 "brk_noprog_label", "change_brk_noprog", "resting_stop_label", "change_resting_stop",
                 "parc_label", "change_parc", "tcs_label", "change_tcs")
KEPT = ["Instrument", "Risk/trade, ramp MIN", "Paper / Live mode", "Telegram alerts", "TastyTrade credentials",
        "Catastrophic cap", "Ramp TOP (MAX)", "Data capture", "Done"]
OPPOSITE = {"OT_PIN_PROXIMITY_ACTIVE": "0", "OT_SCALE_BREAKOUT": "0", "OT_RUNAWAY_END": "11:30",
            "OT_BREAKOUT_END": "15:40", "OT_BRK_NOPROG": "log"}
WANT = {"pin": True, "scale_brk": True, "run_end": [10, 30], "brk_end": [10, 30], "run_et": "10:30",
        "brk_et": "10:30", "noprog": "trade"}


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name.split()[0])


def _read(rel):
    with open(os.path.join(ROOT, rel)) as fh:
        return fh.read()


def _code_lines(src):
    """configure.sh without its comment lines (the changelog names every removed key on purpose)."""
    return "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))


def _probe(env):
    e = {k: v for k, v in os.environ.items() if k not in REMOVED_KEYS}
    e.update(env)
    code = ("import config,json;W=config.ENTRY_WINDOWS;print(json.dumps({'pin':config.PIN_PROXIMITY_ACTIVE,"
            "'scale_brk':config.SCALE_BREAKOUT,'run_end':list(W['RunawayContinuation'][1]),"
            "'brk_end':list(W['Breakout'][1]),'run_et':str(config.RUNAWAY_CUTOFF_ET),"
            "'brk_et':str(config.BREAKOUT_LATEST_ET),'noprog':config.BRK_NOPROG_MODE,"
            "'tcs':getattr(config,'TCS_MODE',None)}))")
    p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=e, capture_output=True, text=True, timeout=180)
    if p.returncode != 0 or not p.stdout.strip():
        return {"error": p.stderr[-300:]}
    return json.loads(p.stdout.strip().splitlines()[-1])


def main():
    print("check_config_menu")
    try:
        p = subprocess.run([sys.executable, "-c", "import config"], cwd=ROOT, capture_output=True, text=True,
                           timeout=180)
    except Exception as exc:                                     # noqa: BLE001
        p = None
        print(f"NOT RUN - {exc}")
    if p is None or p.returncode != 0:
        print(f"NOT RUN - config does not import under {sys.executable}: {(p.stderr if p else '')[-200:]}")
        return 2

    src = _read("configure.sh")
    code = _code_lines(src)

    # M1 the menu
    items = re.findall(r'^\s*echo -e "  \$\{BOLD\}(\d+)\.\$\{RESET\}\s+(.+?)(?:\s{2,}\(|\s*\(currently|"$)', src, re.M)
    nums = [int(n) for n, _ in items]
    labels = [lab.strip().rstrip('"') for _, lab in items]
    cases = [int(n) for n in re.findall(r"^\s*(\d+)\)\s", src[src.find('case "$menu_choice"'):], re.M)]
    check("M1 the menu lists exactly the kept items, 1-9 in order",
          nums == list(range(1, 10)) and labels == KEPT, f"nums={nums} labels={labels}")
    check("M1 the case dispatches 1-9 and nothing else; 9 is Done (break), 8 data capture, 7 the ramp TOP",
          cases == list(range(1, 10)) and re.search(r"^\s*9\)\s*break\s*;;", src, re.M)
          and re.search(r"^\s*8\)\s*change_data_capture\s*;;", src, re.M)
          and re.search(r"^\s*7\)\s*change_orb_budget;", src, re.M), f"cases={cases}")
    check("M1 the prompt names 1-9 and the out-of-range warning names 1 and 9",
          'Select [1-9]' in src and "between 1 and 9." in src and "1-17" not in code)

    # M2 no removed key, no removed function
    named = [k for k in REMOVED_KEYS if re.search(r"\b%s\b" % k, code)]
    check("M2 configure.sh names none of the removed keys outside its changelog", not named, f"named {named}")
    writes = re.findall(r'(?:set_env|drop_env)\s+"?(OT_[A-Z_]+)', code)
    check("M2 configure.sh writes none of the removed keys (set_env / drop_env)",
          not [w for w in writes if w in REMOVED_KEYS], f"writes={writes}")
    defined = set(re.findall(r"^([a-z_]+)\(\) \{", src, re.M))
    check("M2 none of the removed label / change functions is defined",
          not (defined & set(REMOVED_FUNCS)), f"{sorted(defined & set(REMOVED_FUNCS))}")

    # M3 the summary
    m = re.search(r"^show_config\(\) \{\n(.*?)^\}", src, re.M | re.S)
    body = m.group(1) if m else ""
    gone = [lab for lab in ("Pin gate:", "Scaling:", "Runaway end:", "Breakout end:", "BRK no-progress:",
                            "Resting stop:", "PARC:", "TCS:") if lab in body]
    check("M3 the summary prints no line for a removed setting", bool(body) and not gone, f"still {gone}")

    # M4 / M5 behaviour with no env, and with the opposite env
    none = _probe({})
    opp = _probe(OPPOSITE)
    want_none = dict(WANT, tcs="log")
    check("M4 no env: pin gate ON, Breakout scaling ON, both ends 10:30, no-progress trade, TCS log",
          none == want_none, f"got {none}")
    check("M5 the opposite env (0, 0, 11:30, 15:40, log) changes nothing: the keys are not read",
          {k: opp.get(k) for k in WANT} == WANT, f"got {opp}")

    # M6 the resting stop
    p6 = subprocess.run([sys.executable, "-c", "import config;print([n for n in dir(config) if 'RESTING_STOP' in n])"],
                        cwd=ROOT, capture_output=True, text=True, timeout=180)
    hits = []
    for top in ("main.py", "config.py", "execution", "strategy", "risk", "analysis", "data", "derived",
                "warehouse", "tools", "utils", "notifications", "database"):
        base = os.path.join(ROOT, top)
        paths = [base] if top.endswith(".py") else [os.path.join(d, f) for d, _, fs in os.walk(base)
                                                       for f in fs if f.endswith(".py")]
        for path in paths:
            try:
                tree = ast.parse(open(path).read())
            except (OSError, SyntaxError):
                continue
            for n in ast.walk(tree):
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    names = [a.name for a in n.names] + [getattr(n, "module", "") or ""]
                    if any("resting_stop" in x for x in names):
                        hits.append(os.path.relpath(path, ROOT))
                elif isinstance(n, ast.Constant) and isinstance(n.value, str) and \
                        n.value in ("OT_RESTING_STOP", "OT_RESTING_STOP_STATE"):
                    hits.append(os.path.relpath(path, ROOT))
                elif isinstance(n, (ast.Name, ast.Attribute)) and \
                        "RESTING_STOP" in (getattr(n, "id", None) or getattr(n, "attr", "")):
                    hits.append(os.path.relpath(path, ROOT))
    check("M6 execution/resting_stop.py is gone", not os.path.exists(os.path.join(ROOT, "execution", "resting_stop.py")))
    check("M6 config defines no RESTING_STOP_* name", p6.returncode == 0 and p6.stdout.strip() == "[]",
          p6.stdout.strip() or p6.stderr[-200:])
    check("M6 no module imports resting_stop or reads OT_RESTING_STOP / OT_RESTING_STOP_STATE",
          not hits, f"{sorted(set(hits))}")

    # M7 the installer
    setup = _read("setup_ec2.sh")
    boot = _code_lines(_read("bootstrap.example.sh"))
    unit_w = [k for k in REMOVED_KEYS if re.search(r"^Environment=%s=" % k, setup, re.M)]
    boot_w = [k for k in REMOVED_KEYS if re.search(r"^\s*export\s+%s=" % k, boot, re.M)]
    check("M7 setup_ec2.sh writes no Environment= line for a removed key", not unit_w, f"{unit_w}")
    check("M7 bootstrap.example.sh exports none of the removed keys", not boot_w, f"{boot_w}")

    # M8 the Service mode line
    e = {k: v for k, v in os.environ.items() if k not in REMOVED_KEYS}
    e.update(OPPOSITE)
    e.update(OT_RESTING_STOP="trade", OT_INSTRUMENT=os.environ.get("OT_INSTRUMENT", "QQQ"))
    p8 = subprocess.run([sys.executable, "-c", "import main;print(main._banner_dials())"], cwd=ROOT, env=e,
                        capture_output=True, text=True, timeout=240)
    out = (p8.stdout.strip().splitlines() or [""])[-1]
    check("M8 the Service mode line names pin_gate=ON, runaway_end=10:30, breakout_end=10:30, brk_noprog=trade, "
          "and no resting_stop",
          p8.returncode == 0 and "pin_gate=ON" in out and "runaway_end=10:30" in out and "breakout_end=10:30" in out
          and "brk_noprog=trade" in out and "resting_stop" not in out and "REFUSED" not in out,
          out or p8.stderr[-300:])

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
