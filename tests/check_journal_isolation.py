"""tests/check_journal_isolation.py — v1.1

v1.1  2026-09-26 — OTV4TEST r146. J1b looks only for the child's own ISOCHECK.jsonl in the live
      journal, not for ANY change: the live bot appends there all session, so the
      directory comparison would fail a mid-session land at random - the flaw r146's
      first land exposed in U3b.
A CHECKER'S SIGNAL-JOURNAL WRITES LAND IN ITS SCRATCH, NEVER IN THE LIVE JOURNAL.

v1.0  2026-09-25 — OTV4TEST r144. analysis/signal_journal.py wrote to the repo's
      data/signal_journal/<date>/<SYMBOL>.jsonl with no override, and the symbol
      falls back to config's "QQQ". So every checker that drove the ORB engine -
      the boot sweep runs them all at every instance boot - appended retest_check
      FIXTURES to the live journal: 126 on this box on 2026-09-25 alone (06:13-06:14
      ET, the sweep's window). On SOFI and AAL the pusher filed them under sym=QQQ
      in the warehouse, ~76 per box per boot, about 320 fabricated events in QQQ's
      real partition. 1-REPORTER's control: the live QQQ.jsonl was 71,944 bytes on
      BOTH boxes, byte-identical, which market data cannot be and fixtures are.

  J1  with OT_SIGNAL_JOURNAL_DIR set, a REAL journal() call writes its line under
      that directory
  J1b ...and nothing the child wrote reached the live data/signal_journal (its own
      ISOCHECK.jsonl - the bot's own appends are not this check's business)
  J2  with the variable UNSET the journal still writes to the repo's
      data/signal_journal (the live bot's behaviour is unchanged) - read from
      the module, nothing is written
  ⚠️ SAFETY: the child process runs with OT_INSTRUMENT=ISOCHECK, so a regressed
  build that ignores the override writes ISOCHECK.jsonl, never a live QQQ.jsonl,
  and this checker deletes that stray file after recording the failure.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(_root, "data", "signal_journal")
SYM = "ISOCHECK"
FAIL: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])


def snapshot():
    out = {}
    if os.path.isdir(LIVE):
        for d, _dirs, files in os.walk(LIVE):
            for f in files:
                p = os.path.join(d, f)
                try:
                    out[p] = os.path.getsize(p)
                except OSError:
                    pass
    return out


def child(code, extra_env, drop=()):
    env = dict(os.environ, OT_INSTRUMENT=SYM, **extra_env)
    for k in drop:
        env.pop(k, None)
    env.pop("PYTHONPATH", None)
    py = os.path.join(_root, "venv", "bin", "python")
    return subprocess.run([py if os.path.exists(py) else sys.executable, "-c", code],
                          cwd=_root, env=env, capture_output=True, text=True, timeout=120)


WRITE = ("import sys; sys.path.insert(0, '.'); "
         "from analysis import signal_journal as sj; "
         "sj.journal('retest_check', orb={'state': 'ISOLATION_PROBE'}); "
         "print('OUT_ROOT=' + sj._OUT_ROOT)")
READ = ("import sys; sys.path.insert(0, '.'); "
        "from analysis import signal_journal as sj; print('OUT_ROOT=' + sj._OUT_ROOT)")

scratch = tempfile.mkdtemp(prefix="check_journal_isolation_",
                           dir="/var/tmp" if os.path.isdir("/var/tmp") else None)
jdir = os.path.join(scratch, "signal_journal")
before = snapshot()
r = child(WRITE, {"OT_SIGNAL_JOURNAL_DIR": jdir})
after = snapshot()

written = []
for d, _dirs, files in os.walk(jdir):
    for f in files:
        with open(os.path.join(d, f)) as fh:
            written += [json.loads(l) for l in fh if l.strip()]
probe = [w for w in written if (w.get("orb") or {}).get("state") == "ISOLATION_PROBE"]
check("J1 with OT_SIGNAL_JOURNAL_DIR set, a real journal() call writes under it",
      r.returncode == 0 and len(probe) == 1,
      f"rc={r.returncode} lines_in_scratch={len(written)} {r.stderr.strip()[-160:]}")

# J1b looks ONLY for the child's own file. The live bot appends to its journal
# all session, so comparing the whole directory would fail a mid-session land at
# random - the r146 land found that shape in U3b the hard way (§40.1).
stray = sorted(p for p in after if os.path.basename(p) == f"{SYM}.jsonl")
check("J1b ...and nothing the child wrote reached the live data/signal_journal", not stray,
      ", ".join(os.path.relpath(p, _root) for p in stray[:4]))
for p in stray:                                     # clean up a regressed build's stray write
    try:
        os.remove(p)
    except OSError:
        pass

r2 = child(READ, {}, drop=("OT_SIGNAL_JOURNAL_DIR",))
out = next((l.split("=", 1)[1] for l in r2.stdout.splitlines() if l.startswith("OUT_ROOT=")), "")
check("J2 unset, the journal still writes to the repo's data/signal_journal (live behaviour unchanged)",
      r2.returncode == 0 and os.path.realpath(out) == os.path.realpath(LIVE), repr(out))

print(f"\n{'GREEN' if not FAIL else 'RED'} — {len(FAIL)} failed" + (f": {FAIL}" if FAIL else ""))
sys.exit(1 if FAIL else 0)
