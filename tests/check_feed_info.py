#!/usr/bin/env python3
"""
tests/check_feed_info.py  v1.0
v1.0  2026-09-22  OTV4TEST r100 — born RED at e11c731, where neither
      `feed.info` nor `tools/feed_capabilities.py` exists and F0 NAMES that
      rather than dying on a traceback.

r100 — THE CAPABILITY TABLE MUST NOT ROT, AND ROT HERE IS PERMISSIVE.

`feed.info` records what the broker's DXLink feed will actually deliver, taken
from the server's own FEED_CONFIG replies. Its failure mode is the one §23 and
r92's `check_cascade_constants` both record: **a mirror list that is a SUBSET
of what it mirrors reports green on everything it forgot to name.** If the SDK
gains an event type, `feed.info` silently becomes incomplete while still
reading as authoritative — and the next reader plans around an event the file
never mentions.

🔴 THIS CHECKER NEEDS NO NETWORK, ON PURPOSE. It cannot re-run the negotiation
— that needs credentials and a socket, and a gate that reaches the vendor would
go red on their outage rather than our defect. So it pins the two things that
CAN rot locally: the event roster, and whether the documented fields are real.

⚠️ WHAT IT CANNOT CATCH, STATED SO NOBODY MISTAKES GREEN FOR FRESH: it cannot
tell whether the ENTITLEMENT still matches. If the vendor starts or stops
carrying an event, this stays green and the file is wrong. Only re-running
`tools/feed_capabilities.py` answers that. The file says so itself.

  F0  the artifact and its generator both exist (guard, not a check)
  F1  every event the SDK knows is named in feed.info   (the subset defect)
  F2  the generator compiles                            (§21: parse, not grep)
  F3  every field feed.info documents is a REAL field of that SDK event
  F4  both symbol spaces are reported, never one
  F5  the declined event carries graded evidence, not a bare verdict

Run:  venv/bin/python tests/check_feed_info.py
"""
from __future__ import annotations

import os
import py_compile
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_s = tempfile.mkdtemp(prefix="check_feed_info.")
os.environ.setdefault("OT_TRADES_DB", os.path.join(_s, "trades.db"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))

FAIL: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])


INFO = os.path.join(ROOT, "feed.info")
GEN = os.path.join(ROOT, "tools", "feed_capabilities.py")

# ── F0 — THE GUARD (the r72/V0 pattern) ───────────────────────────────────
_absent = [p for p in (INFO, GEN) if not os.path.exists(p)]
check("F0 feed.info and tools/feed_capabilities.py both exist", not _absent,
      f"missing: {[os.path.relpath(p, ROOT) for p in _absent]}" if _absent
      else "r100 present")
if FAIL:
    print(f"\nRED — {len(FAIL)} failed: {FAIL}")
    sys.exit(1)

TEXT = open(INFO, encoding="utf-8").read()

# ── F1 — THE SUBSET DEFECT (r92's lesson, a second time) ──────────────────
# ⚠️ THE LANDER RUNS CHECKS UNDER SYSTEM `python3`, NOT THE VENV, and the SDK
# lives only in the venv. So the venv's site-packages is added explicitly when
# the import fails — the same interpreter version, resolved by glob rather than
# hardcoded. 🔴 IF IT STILL CANNOT IMPORT, THIS GOES RED AND SAYS SO. A gate
# that skipped its only substantive assertions on an ImportError would report
# green having verified nothing, which is the shape §40.1 names.
import glob                                                         # noqa: E402
try:
    from tastytrade.streamer import MAP_EVENTS
except ImportError:
    for _sp in glob.glob(os.path.join(ROOT, "venv", "lib", "python*",
                                      "site-packages")):
        if _sp not in sys.path:
            sys.path.insert(0, _sp)
    try:
        from tastytrade.streamer import MAP_EVENTS
    except Exception as _exc:                                       # noqa: BLE001
        check("F1 the SDK event roster is importable", False,
              f"{type(_exc).__name__}: {_exc} — F1/F3 cannot be evaluated")
        print(f"\nRED — {len(FAIL)} failed: {FAIL}")
        sys.exit(1)

_missing = [n for n in MAP_EVENTS if not re.search(rf"\b{re.escape(n)}\b", TEXT)]
check("F1 every SDK event type is named in feed.info", not _missing,
      f"{len(MAP_EVENTS)} known; unnamed: {_missing or 'none'}")

# ── F2 — THE GENERATOR COMPILES ───────────────────────────────────────────
# ⚠️ py_compile, NOT ast.parse. `ast.parse` reported OK on a genuine
# SyntaxError earlier today (an import placed above `from __future__`), which
# is a compile-stage error the parser never sees.
try:
    py_compile.compile(GEN, cfile=os.path.join(_s, "gen.pyc"), doraise=True)
    _ok, _why = True, ""
except Exception as exc:                                            # noqa: BLE001
    _ok, _why = False, f"{type(exc).__name__}: {exc}"
check("F2 the generator compiles", _ok, _why)

# ── F3 — THE DOCUMENTED FIELDS ARE REAL ───────────────────────────────────
# 🔑 The field lists are the server's reply, so they may be a SUBSET of the SDK
# model — but never a SUPERSET. A name in this file that the event does not
# have is an invented field, and someone will plan a study around it.
_block = re.search(r"FIELD LISTS, EXACTLY AS RETURNED(.*?)\n═", TEXT, re.S)
_checked = 0
_bogus: list = []
if _block:
    for m in re.finditer(r"^(\w+)\s+\((?:equity|option|EQUITY|OPTION)[^)]*\)\s*\n"
                         r"((?:[ \t]+\S.*\n)+)", _block.group(1), re.M):
        name, body = m.group(1), m.group(2)
        cls = MAP_EVENTS.get(name)
        if cls is None:
            _bogus.append(f"{name}:not-an-event")
            continue
        real = set(cls.model_json_schema().get("properties", {}).keys())
        for tok in body.split():
            if tok not in real:
                _bogus.append(f"{name}.{tok}")
        _checked += 1
# ⚠️ A CHECKER THAT COMPARED NOTHING MUST FAIL (r92's C2). If the section is
# renamed or reformatted this would otherwise report a cheerful green.
check("F3 every documented field is a real field of that event",
      _checked >= 6 and not _bogus,
      f"{_checked} event blocks parsed; bogus: {_bogus[:6] or 'none'}")

# ── F4 — BOTH SPACES, NEVER ONE ───────────────────────────────────────────
# 🔴 THE ERROR THIS EXISTS TO PREVENT. Reading "no schema" as "not entitled"
# without testing the other symbol space is exactly how Underlying was called
# uncarried on 2026-09-22 off a 45-second probe. TimeAndSale (equity-only) and
# Greeks (option-only) are both FULLY CARRIED and each returns no schema in one
# space. If the file ever reports a single space, that reasoning is back.
check("F4 both symbol spaces are reported",
      bool(re.search(r"EQUITY\s+OPTION", TEXT)) and "EQUITY ONLY" in TEXT
      and "OPTION ONLY" in TEXT,
      "the equity/option table and the mirror pair must both survive")

# ── F5 — THE DECLINED EVENT IS GRADED, NOT ASSERTED ───────────────────────
# §0: a verdict at more strength than the evidence carries is the defect. The
# Underlying finding is MEASURED as absent and INFERRED as an entitlement gap,
# and the file must keep that distinction visible.
check("F5 the declined verdict states measured vs inferred",
      "MEASURED" in TEXT and "INFERRED" in TEXT and "NOT PROVEN" in TEXT,
      "Underlying is evidenced, not proven — the file must keep saying so")

if FAIL:
    print(f"\nRED — {len(FAIL)} failed: {', '.join(FAIL)}")
    sys.exit(1)
print(f"\nGREEN — feed.info covers all {len(MAP_EVENTS)} SDK events, "
      f"{_checked} field blocks verified against the models")
sys.exit(0)
