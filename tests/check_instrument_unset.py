"""tests/check_instrument_unset.py — v1.1
v1.1  2026-10-03 — OTV4TEST r194 (BOX.16): the children get OT_LOG_FILE in this check's own scratch. Under the
      new lander/sweep env they inherited the HARNESS's scratch log, which is not under this check's HOME, and
      U3b (the children never log to the live file) went red on the build's full sweep. Same property, re-pointed.
(U3b as landed: WHERE the child logs, not the live log's size - see U3b.)
NO PROCESS GUESSES QQQ WHEN OT_INSTRUMENT IS UNSET.

v1.0  2026-09-26 — OTV4TEST r146. The operator: "That default QQQ variable outside
      the environment has bit us multiple times ... defaulting the QQQ is not the
      answer." config read os.environ.get("OT_INSTRUMENT", "QQQ"), so any process
      without the variable was silently QQQ: right on the QQQ box by luck, wrong
      on every other - r144's fixture events on SOFI/AAL were labelled QQQ, and
      SOFI's self-close alerts and manifold board read QQQ.

  U1  config.INSTRUMENT is "UNSET" when OT_INSTRUMENT is absent or blank, and the
      value itself when set
  U2  a SessionConfig built WITHOUT instrument= raises; with one it does not
  U3  the REAL main.main() refuses to start with it unset: exit 78 and a stderr
      line naming OT_INSTRUMENT - before any login (the child's HOME is scratch,
      so ~/options-trader/bot.log resolves there and the live log is untouched)
  U4  the REAL candle_feed.main() refuses the same way (exit 78)
  U5  utils.instrument.box_instrument(): this process first, else the bot unit's
      OT_INSTRUMENT (a stubbed `systemctl show` carrying a fake secret beside it,
      which must NOT appear in the result), else UNSET
  U6  no runtime file (tests/ excepted) still reads OT_INSTRUMENT with a "QQQ"
      fallback - the literal, not a mention
  U7  the harnesses state a fixture symbol explicitly: boot_sweep.run_one hands
      checkers OT_INSTRUMENT, and land.sh's CHECK line sets it
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

import glob as _glob
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
sys.path.insert(0, _root)
PY = os.path.join(_root, "venv", "bin", "python")
PY = PY if os.path.exists(PY) else sys.executable
FAIL: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])


_s = tempfile.mkdtemp(prefix="check_instrument_unset_",
                      dir="/var/tmp" if os.path.isdir("/var/tmp") else None)


def child(code, instrument=None, timeout=90):
    env = {k: v for k, v in os.environ.items() if k not in ("OT_INSTRUMENT", "PYTHONPATH")}
    env.update(HOME=_s, OT_TRADES_DB=os.path.join(_s, "t.db"),
               OT_DERIVED_DB=os.path.join(_s, "d.db"), OT_RESTING_DB=os.path.join(_s, "r.db"),
               OT_SIGNAL_JOURNAL_DIR=os.path.join(_s, "sj"),
               OT_LOG_FILE=os.path.join(_s, "bot.log"))      # r194: the children's log is THIS check's scratch
    if instrument is not None:
        env["OT_INSTRUMENT"] = instrument
    return subprocess.run([PY, "-c", "import sys; sys.path.insert(0, '.'); " + code],
                          cwd=_root, env=env, capture_output=True, text=True, timeout=timeout)


# ── U1 ────────────────────────────────────────────────────────────────────
vals = {}
for label, inst in (("absent", None), ("blank", "  "), ("SOFI", "SOFI")):
    r = child("import config; print('I=' + config.INSTRUMENT)", inst)
    vals[label] = next((l[2:] for l in r.stdout.splitlines() if l.startswith("I=")), f"rc={r.returncode} {r.stderr[-120:]}")
check("U1 config.INSTRUMENT is UNSET when absent or blank, the value when set",
      vals == {"absent": "UNSET", "blank": "UNSET", "SOFI": "SOFI"}, repr(vals))

# ── U2 ────────────────────────────────────────────────────────────────────
r = child("import config\n"
          "try:\n    config.SessionConfig(paper_trading=True); print('NO_RAISE')\n"
          "except ValueError as e:\n    print('RAISED')\n"
          "config.SessionConfig(paper_trading=True, instrument='SOFI'); print('OK_WITH')", "SOFI")
check("U2 SessionConfig without instrument= raises; with one it builds",
      "RAISED" in r.stdout and "OK_WITH" in r.stdout, (r.stdout + r.stderr)[-200:])

# ── U3 / U4 ───────────────────────────────────────────────────────────────
r = child("import main; main.main()", None, timeout=180)
check("U3 main.main() refuses to start with OT_INSTRUMENT unset (exit 78, named)",
      r.returncode == 78 and "OT_INSTRUMENT is not set" in r.stderr,
      f"rc={r.returncode} {r.stderr.strip()[-160:]}")
r = child("from data import candle_feed; candle_feed.main()", None, timeout=120)
check("U4 candle_feed.main() refuses the same way (exit 78)",
      r.returncode == 78 and "OT_INSTRUMENT is not set" in r.stderr,
      f"rc={r.returncode} {r.stderr.strip()[-160:]}")
# U3b asserts WHERE the child's log resolves, never the live log's size: the live
# bot writes that file itself, so a size comparison failed r146's first land
# (the bot logged at 01:36:27, the check read at 01:36:30) - a check whose SHAPE
# asserted something outside its control (§40.1).
r = child("import config; print('LOG=' + config.LOG_FILE)", "QQQ")
logf = next((l[4:] for l in r.stdout.splitlines() if l.startswith("LOG=")), "")
check("U3b ...the children's bot.log resolves inside their scratch HOME, never the live one",
      bool(logf) and os.path.realpath(logf).startswith(os.path.realpath(_s)), repr(logf))

# ── U5 ────────────────────────────────────────────────────────────────────
try:
    from utils import instrument as ui
    saved_env = os.environ.pop("OT_INSTRUMENT", None)

    class _R:
        def __init__(self, out): self.stdout = out

    fake = "Environment=TT_CLIENT_SECRET=s3cr3t-DO-NOT-LEAK OT_INSTRUMENT=SOFI OT_PAPER_TRADING=True\n"
    orig = ui.subprocess.run
    try:
        ui.subprocess.run = lambda *a, **k: _R(fake)
        from_unit = ui.box_instrument()
        ui.subprocess.run = lambda *a, **k: _R("Environment=OT_PAPER_TRADING=True\n")
        none = ui.box_instrument()
        os.environ["OT_INSTRUMENT"] = "AAL"
        ui.subprocess.run = lambda *a, **k: _R(fake)
        env_wins = ui.box_instrument()
    finally:
        ui.subprocess.run = orig
        os.environ.pop("OT_INSTRUMENT", None)
        if saved_env is not None:
            os.environ["OT_INSTRUMENT"] = saved_env
    check("U5 box_instrument: the unit's value when the process has none, never the rest of the block",
          from_unit == "SOFI" and "s3cr3t" not in from_unit, repr(from_unit))
    check("U5b ...UNSET when neither has it; this process's value wins over the unit's",
          none == "UNSET" and env_wins == "AAL", f"none={none!r} env_wins={env_wins!r}")
except Exception as exc:                                        # noqa: BLE001
    check("U5 box_instrument", False, f"{type(exc).__name__}: {exc}")

# ── U6 ────────────────────────────────────────────────────────────────────
pat = re.compile(r"""(environ\.get|getenv|get_runtime_env)\(\s*["']OT_INSTRUMENT["']\s*,\s*["']QQQ["']""")
hits = []
for d, dirs, files in os.walk(_root):
    dirs[:] = [x for x in dirs if x not in ("venv", ".git", "tests", "__pycache__")]
    for f in files:
        if f.endswith(".py"):
            p = os.path.join(d, f)
            for i, line in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
                if pat.search(line) and not line.lstrip().startswith("#"):
                    hits.append(f"{os.path.relpath(p, _root)}:{i}")
check("U6 no runtime file reads OT_INSTRUMENT with a QQQ fallback", not hits, ", ".join(hits[:6]))

# ── U7 ────────────────────────────────────────────────────────────────────
import importlib.util as _ilu
_bs = _ilu.spec_from_file_location("_bs_u7", os.path.join(_root, "tools", "boot_sweep.py"))
_m = _ilu.module_from_spec(_bs)
_bs.loader.exec_module(_m)
seen = {}


class _RR:
    returncode = 0


_orig = _m.subprocess.run
_m.subprocess.run = lambda cmd, **kw: (seen.update(env=dict(kw.get("env") or {})) or _RR())
_saved = os.environ.pop("OT_INSTRUMENT", None)
try:
    _m.run_one("check_nothing_real.py")
finally:
    _m.subprocess.run = _orig
    if _saved is not None:
        os.environ["OT_INSTRUMENT"] = _saved
land = open(os.path.join(_root, "tools", "land.sh"), encoding="utf-8").read()
runs = [ln for ln in land.splitlines() if 'python3 "$chk"' in ln and not ln.lstrip().startswith("#")]
check("U7 the sweep and the lander hand checkers an explicit OT_INSTRUMENT",
      seen.get("env", {}).get("OT_INSTRUMENT") == "QQQ" and runs and all("OT_INSTRUMENT=" in ln for ln in runs),
      f"sweep={seen.get('env', {}).get('OT_INSTRUMENT')!r} lander_lines={len(runs)}")

print(f"\n{'GREEN' if not FAIL else 'RED'} — {len(FAIL)} failed" + (f": {FAIL}" if FAIL else ""))
sys.exit(1 if FAIL else 0)
