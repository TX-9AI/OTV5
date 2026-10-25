"""tests/check_header_series.py — v5.0
v5.0  2026-10-25  OTV5 r12 (HDR.1) — new. The operator, 2026-10-25: every header starts at 5 from the lineage split and
      each edit counts v5.1, v5.2, ... A revision-by-revision audit of r8-r11 found every edit bumped by exactly .1, but
      six files r7's reset never reached still carried the predecessor's numbers (deploy/candle-feed.service v4.0,
      deploy/candle-logger.service v4.0, deploy/s3-push.service v4.0, deploy/s3-push.timer v4.0, feed.info v1.1,
      requirements.txt v1.0): the lander's BUMP check reads .py/.sh/.md only, and none of the six had been edited since r0.
      BORN RED on r11 at H1 and H2.

  H1  every tracked text file whose header (its first 12 lines) names a version names a v5 version.
  H2  the six files r12 reset read v5.0 in their headers (the scan reaches .service, .timer, .info and .txt files).
  H3  the scan is not vacuous: it read more than 500 versioned headers.
  H4  CONTROL: a fixture file headed v4.0 is reported by the same scanner, and one headed v5.3 is not.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


VER = re.compile(r"\bv(\d+)\.(\d+)\b")
HEAD_LINES = 12
SKIP_DIRS = {".git", "venv", "__pycache__", "data", "node_modules"}


def header_version(path):
    """The first vN.M token in the file's first HEAD_LINES lines, or None (no header, or not text)."""
    try:
        with open(path, encoding="utf-8") as f:
            for _i, line in zip(range(HEAD_LINES), f):
                m = VER.search(line)
                if m:
                    return int(m.group(1)), int(m.group(2))
    except (UnicodeDecodeError, OSError):
        return None
    return None


def tracked(root):
    r = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout:
        return [p for p in r.stdout.split("\0") if p and os.path.isfile(os.path.join(root, p))]
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        out += [os.path.relpath(os.path.join(d, f), root) for f in files]
    return out


def off_series(root, files):
    seen, bad = 0, []
    for rel in files:
        v = header_version(os.path.join(root, rel))
        if v is None:
            continue
        seen += 1
        if v[0] != 5:
            bad.append("%s v%d.%d" % (rel, v[0], v[1]))
    return seen, bad


_seen, _bad = off_series(_root, tracked(_root))
check("H1  every versioned header in the tree is in the v5 series", not _bad, "off-series=%s" % _bad[:12])

SIX = ("deploy/candle-feed.service", "deploy/candle-logger.service", "deploy/s3-push.service",
       "deploy/s3-push.timer", "feed.info", "requirements.txt")
_six = {p: header_version(os.path.join(_root, p)) for p in SIX}
check("H2  the six files r7 missed read v5.0", all(v == (5, 0) for v in _six.values()), str(_six))
check("H3  the scan read more than 500 versioned headers", _seen > 500, "seen=%d" % _seen)

with tempfile.TemporaryDirectory(prefix="check_header_series_") as _t:
    with open(os.path.join(_t, "old.service"), "w") as f:
        f.write("# old.service  v4.0\n[Unit]\n")
    with open(os.path.join(_t, "new.py"), "w") as f:
        f.write('"""new.py — v5.3\n"""\n')
    _cs, _cb = off_series(_t, ["old.service", "new.py"])
check("H4  CONTROL: the scanner reports a v4.0 header and passes a v5.3 one",
      _cs == 2 and _cb == ["old.service v4.0"], "seen=%d bad=%s" % (_cs, _cb))

print("\n%s — %d checks, %d failed" % ("GREEN" if not FAILED else "RED", len(RAN), len(FAILED)))
if FAILED:
    print("  failed: " + ", ".join(FAILED))
sys.exit(1 if FAILED else 0)
