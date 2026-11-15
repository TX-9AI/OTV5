#!/usr/bin/env python3
"""
tests/check_ramp_top_key.py  v5.0
v5.0  2026-11-15  OTV5 r125 (HYG.28) — THE RAMP TOP'S KEY IS OT_BREAKOUT_BUDGET_USD, AND NO BOX SIZES DIFFERENTLY.
      The key was OT_ORB_BUDGET_USD, named after the ORB trade retired at r76; Breakout is the setup that rides the
      ramp. config.py v5.23 reads the new key first and the old one as a fallback; tools/strip_retired_env.sh v5.6
      renames the stored assignment on each unit (value and quoting kept); configure.sh v5.9 item 7 writes the new key.

  K1   config: old key only -> the same value, not default, FROM_OLD_KEY true
  K1b  config: new key only -> the value, not default, FROM_OLD_KEY false
  K1c  config: both set -> the NEW key wins, FROM_OLD_KEY false
  K1d  config: neither -> RISK_PER_TRADE_USD, IS_DEFAULT true (the default is unchanged)
  K2   main logs ONE WARNING naming the deprecated key, inside the service branch, when FROM_OLD_KEY (names only)
  K3   strip_retired_env.sh renames the bare, "double" and 'single' quoted forms, keeping value and quoting
  K3b  ...a unit that already carries the new key loses the old assignment and keeps the new one's value
  K3c  ...a mixed line keeps its other assignments verbatim; no value is printed; a second run is clean
  K3d  ...the effective environment (parsed as systemd does) has the same ramp-top value before and after
  K4   configure.sh item 7 writes the NEW key and drops the old bare line; it displays new, else old
  K5   🔒 no code outside the fallback names the old key, and no code names the old Python constants
"""
import ast
import os
import re
import shlex
import subprocess
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
OLD, NEW = "OT_ORB_BUDGET_USD", "OT_BREAKOUT_BUDGET_USD"
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


def _config(env_extra):
    env = {k: v for k, v in os.environ.items() if k not in (OLD, NEW)}
    env.update({"OT_RISK_USD": "1050", "OT_INSTRUMENT": "QQQ"}, **env_extra)
    prog = ("import config as c; print('%r|%r|%r|%r' % (c.BREAKOUT_BUDGET_USD, c.BREAKOUT_BUDGET_IS_DEFAULT,"
            " c.BREAKOUT_BUDGET_FROM_OLD_KEY, c.RISK_PER_TRADE_USD))")
    r = subprocess.run([sys.executable, "-c", prog], cwd=_root, env=env, capture_output=True, text=True, timeout=60)
    return r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else f"rc={r.returncode} {r.stderr[-200:]}"


def _effective(unit_text):
    """The ramp-top value systemd would hand the bot: the last assignment of NEW, else of OLD."""
    env = {}
    for ln in unit_text.splitlines():
        if ln.startswith("Environment="):
            for t in shlex.split(ln[len("Environment="):]):
                k, v = t.split("=", 1)
                env[k] = v
    return env.get(NEW, env.get(OLD))


def main():
    # ── K1: config precedence ────────────────────────────────────────────────────────────────────────
    check("K1 old key only: same value, not default, FROM_OLD_KEY", _config({OLD: "2500"}) == "2500.0|False|True|1050.0",
          _config({OLD: "2500"}))
    check("K1b new key only: the value, not default", _config({NEW: "3000"}) == "3000.0|False|False|1050.0",
          _config({NEW: "3000"}))
    check("K1c both set: the new key wins", _config({OLD: "2500", NEW: "3000"}) == "3000.0|False|False|1050.0",
          _config({OLD: "2500", NEW: "3000"}))
    check("K1d neither: RISK_PER_TRADE_USD and IS_DEFAULT", _config({}) == "1050.0|True|False|1050.0", _config({}))

    # ── K2: main's one deprecation line ──────────────────────────────────────────────────────────────
    tree = ast.parse(open(os.path.join(_root, "main.py")).read())
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "service_mode":
            for sub in ast.walk(node):
                if (isinstance(sub, ast.If) and isinstance(sub.test, ast.Name)
                        and sub.test.id == "BREAKOUT_BUDGET_FROM_OLD_KEY"):
                    calls = [c for c in ast.walk(sub) if isinstance(c, ast.Call)
                             and isinstance(c.func, ast.Attribute) and c.func.attr == "warning"]
                    txt = " ".join(a.value for c in calls for a in ast.walk(c)
                                   if isinstance(a, ast.Constant) and isinstance(a.value, str))
                    hits.append((len(calls), OLD in txt and NEW in txt, len(calls[0].args) if calls else -1))
    check("K2 main warns once, in the service branch, naming both keys and no value", hits == [(1, True, 1)], str(hits))

    # ── K3: the unit rename ──────────────────────────────────────────────────────────────────────────
    tool = os.path.join(_root, "tools", "strip_retired_env.sh")
    env = dict(os.environ, OT_STRIP_NO_RELOAD="1")
    td = tempfile.mkdtemp(prefix="ramp_key_")
    cases = {
        "bare": ("Environment=OT_ORB_BUDGET_USD=2500", "Environment=OT_BREAKOUT_BUDGET_USD=2500"),
        "dq":   ('Environment="OT_ORB_BUDGET_USD=2500"', 'Environment="OT_BREAKOUT_BUDGET_USD=2500"'),
        "sq":   ("Environment='OT_ORB_BUDGET_USD=2500'", "Environment='OT_BREAKOUT_BUDGET_USD=2500'"),
    }
    ok3, det3, outs, eff = True, [], "", True
    for tag, (before, after) in cases.items():
        u = os.path.join(td, f"{tag}.service")
        text = "\n".join(["[Service]", 'Environment="TT_USERNAME=SECRETVALUE9"', before, "Environment=OT_RISK_USD=1050",
                          "ExecStart=/bin/true"]) + "\n"
        open(u, "w").write(text)
        r = subprocess.run(["bash", tool, u], capture_output=True, text=True, env=env)
        body = open(u).read()
        outs += r.stdout + r.stderr
        good = r.returncode == 0 and body == text.replace(before, after)
        eff &= _effective(text) == _effective(body) == "2500"
        ok3 &= good
        det3.append(f"{tag}:{'ok' if good else 'BAD'}")
    check("K3 bare / double / single quoted: the key is renamed, value and quoting kept", ok3, " ".join(det3))

    u = os.path.join(td, "both.service")
    text = "\n".join(["[Service]", "Environment=OT_ORB_BUDGET_USD=2500", 'Environment="OT_BREAKOUT_BUDGET_USD=3000"',
                      "ExecStart=/bin/true"]) + "\n"
    open(u, "w").write(text)
    r = subprocess.run(["bash", tool, u], capture_output=True, text=True, env=env)
    body = open(u).read()
    outs += r.stdout + r.stderr
    eff &= _effective(text) == _effective(body) == "3000"
    check("K3b the new key already set: the old assignment goes, the new one's value stays",
          r.returncode == 0 and OLD not in body and body.count(NEW) == 1 and "3000" in body, body.replace("\n", " | "))

    u = os.path.join(td, "mixed.service")
    text = "\n".join(["[Service]", 'Environment="OT_PARK=log" OT_ORB_BUDGET_USD=2500 \'OT_NOTE=a b\'',
                      "ExecStart=/bin/true"]) + "\n"
    open(u, "w").write(text)
    r = subprocess.run(["bash", tool, u], capture_output=True, text=True, env=env)
    body = open(u).read()
    r2 = subprocess.run(["bash", tool, u], capture_output=True, text=True, env=env)
    outs += r.stdout + r.stderr + r2.stdout + r2.stderr
    eff &= _effective(text) == _effective(body) == "2500"
    check("K3c a mixed line keeps its other assignments verbatim; no value printed; a second run is clean",
          r.returncode == 0 and body.split("\n")[1] == 'Environment="OT_PARK=log" OT_BREAKOUT_BUDGET_USD=2500 \'OT_NOTE=a b\''
          and "SECRETVALUE" not in outs and "2500" not in outs and "3000" not in outs
          and r2.returncode == 0 and "0 retired line(s)" in r2.stdout, body.split("\n")[1])
    check("K3d the effective ramp-top value is identical before and after every rename", eff)

    # ── K4: configure.sh item 7 ──────────────────────────────────────────────────────────────────────
    cfg = os.path.join(_root, "configure.sh")
    u = os.path.join(td, "cfg.service")
    open(u, "w").write("[Service]\nEnvironment=OT_ORB_BUDGET_USD=2500\nExecStartPre=/bin/true\nExecStart=/bin/true\n")
    fns = "; ".join(f'/^{f}() {{/,/^}}/p' for f in ("get_env", "set_env", "drop_env", "get_ramp_top", "set_ramp_top"))
    sh = (f'sudo() {{ "$@"; }}; UNIT_FILE="{u}"; eval "$(sed -n \'{fns}\' "{cfg}")"; '
          'a=$(get_ramp_top); set_ramp_top 4000; b=$(get_ramp_top); echo "$a|$b"')
    r = subprocess.run(["bash", "-c", sh], capture_output=True, text=True, timeout=30)
    body = open(u).read()
    check("K4 item 7 shows the old key's value, then writes the NEW key and drops the old bare line",
          r.stdout.strip() == "2500|4000" and OLD not in body and f"Environment={NEW}=4000" in body,
          f"{r.stdout.strip()!r} {r.stderr.strip()[:120]!r} {body.count(NEW)} new")

    # ── K5: the guard ────────────────────────────────────────────────────────────────────────────────
    # Code (not comments, not docstring headers) may name the old KEY only where the fallback lives, at most this often.
    ALLOWED = {"config.py": 3, "main.py": 1, "setup_ec2.sh": 1, "configure.sh": 2, "tools/strip_retired_env.sh": 1}
    bad = []
    for dp, dns, fns_ in os.walk(_root):
        dns[:] = [d for d in dns if d not in (".git", "venv", "__pycache__", "tests", "docs")]
        for fn in fns_:
            if not fn.endswith((".py", ".sh", ".service", ".timer")):
                continue
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, _root)
            n_key = n_const = 0
            src = open(p, errors="replace").read()
            if fn.endswith(".py"):
                try:
                    t = ast.parse(src)
                except SyntaxError:
                    continue
                doc_ids = {id(n.body[0].value) for n in ast.walk(t)
                           if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                           and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
                for n in ast.walk(t):
                    if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc_ids:
                        n_key += n.value.count(OLD)
                    if isinstance(n, ast.Name) and n.id in ("ORB_BUDGET_USD", "ORB_BUDGET_IS_DEFAULT"):
                        n_const += 1
                    if isinstance(n, ast.alias) and {n.name, n.asname} & {"ORB_BUDGET_USD", "ORB_BUDGET_IS_DEFAULT"}:
                        n_const += 1
                    if isinstance(n, ast.Attribute) and n.attr in ("ORB_BUDGET_USD", "ORB_BUDGET_IS_DEFAULT"):
                        n_const += 1
            else:
                for ln in src.splitlines():
                    code = ln.split("#", 1)[0] if not ln.lstrip().startswith("#") else ""
                    n_key += len(re.findall(r"\bOT_ORB_BUDGET_USD\b", code))
            if n_key > ALLOWED.get(rel, 0) or n_const:
                bad.append(f"{rel}: key x{n_key} (allowed {ALLOWED.get(rel, 0)}), old constant x{n_const}")
    check("K5 no code outside the fallback reads the old key; no code names ORB_BUDGET_USD / ORB_BUDGET_IS_DEFAULT",
          not bad, "; ".join(bad))


if __name__ == "__main__":
    main()
    print(f"\n{'FAIL' if FAILED else 'PASS'}: check_ramp_top_key ({len(FAILED)} failed)")
    sys.exit(1 if FAILED else 0)
