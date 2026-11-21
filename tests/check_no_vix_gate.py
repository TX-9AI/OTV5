#!/usr/bin/env python3
"""
tests/check_no_vix_gate.py  v5.0
v5.0  2026-11-21  OTV5 r140 (MACRO.2) — NO ENTRY IS REFUSED ON THE VIX. The operator, 2026-09-17: "VIX crisis — get rid
      of it. That is major opportunity."; restated 2026-11-21: "VIX 'CRISIS' is something that I view as an opportunity
      not as something we sit out." The admission table lost its VIX gate long ago (check_admission X1), but a second
      copy survived in risk/session_guard.can_enter (`if macro and not macro.new_entries_allowed: return False,
      "VIX crisis ..."`), and on Friday 2026-11-20 from 12:17 ET, VIX 39.53, it refused every entry on all 14 boxes.
      This gate drives the REAL SessionGuard.can_enter on a REAL MacroSnapshot (built by MacroManager._fetch with only
      the network reads stubbed), on a pinned clock:

  N1  Fri 2026-11-20 12:17 ET, VIX 39.53 (band CRISIS): can_enter admits, reason "" — the 2026-11-20 refusal
  N2  the same at VIX 80 (band CRISIS), and the same at VIX 39.53 under rehearsal=False / True outside RTH (16:53 ET:
      refused as "outside RTH" / admitted as a rehearsal, never as a VIX refusal)
  N3  MacroSnapshot has no new_entries_allowed (not a field, not an attribute), the macro snapshot log line carries
      no "entries=" verdict, and config has no VIX_NO_ENTRY_THRESHOLD; the VIX band is still CRISIS at >= 30
      (VIX_CRISIS_THRESHOLD), ELEVATED below it
  N4  the other session_guard gates still refuse exactly as before, with and without a CRISIS snapshot: Saturday
      11-21 12:00 (outside RTH), Thanksgiving 11-26 12:00 (outside RTH), 09:34 (opening range still forming), 15:46
      (past the hard close); 09:35 and 15:44 admit; at every one of those clocks the verdict with VIX 39.53 equals the
      verdict with no snapshot
  N5  source scan (AST, every .py under main.py, risk, execution, strategy, derived, analysis, data, utils): no `if`
      whose test reads the VIX (`.vix`, `.vix_band`, a VIX_* name, "CRISIS", new_entries_allowed, or the same names as a
      getattr / subscript string) returns, raises or
      continues — outside macro_data's own fetch and classifier, which only label; can_enter's body never reads
      `macro`; and no code token new_entries_allowed / VIX_NO_ENTRY_THRESHOLD remains (comments and strings aside)
Born red on 9e46acf (r139) at N1-N5 (5 of 5; N4 because the CRISIS snapshot refused 09:35 and 15:44).
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
Run:  python3 tests/check_no_vix_gate.py
"""
import ast
import dataclasses
import io
import logging
import os
import shutil
import sys
import tempfile
import tokenize
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_no_vix_gate_")
os.environ["OT_TRADES_DB"] = os.path.join(_TD, "t.db")
os.environ["OT_DERIVED_DB"] = os.path.join(_TD, "d.db")
os.environ["OT_FEED_DB"] = os.path.join(_TD, "f.db")
os.environ["OT_LOG_FILE"] = os.path.join(_TD, "bot.log")
os.environ["OT_SIGNAL_JOURNAL_DIR"] = os.path.join(_TD, "sj")
os.environ["OT_COUNTERFACTUAL_DIR"] = os.path.join(_TD, "cf")
ET = ZoneInfo("America/New_York")
FAILED = []
SCAN = ("main.py", "risk", "execution", "strategy", "derived", "analysis", "data", "utils")
# the labeller itself: macro_data fetches the VIX and names its band; it refuses nothing.
LABELLERS = {("data/macro_data.py", "_fetch_vix"), ("data/macro_data.py", "_classify_vix")}


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, rec):
        self.lines.append(rec.getMessage())


def _snapshot(md, vix):
    """A real MacroSnapshot from MacroManager._fetch; only the network reads are stubbed."""
    mm = md.MacroManager()
    mm._fetch_vix = lambda: vix
    mm._check_fed_day = lambda: (False, "")
    cap = _Cap()
    lvl = md.logger.level
    md.logger.setLevel(logging.INFO)
    md.logger.addHandler(cap)
    try:
        snap = mm._fetch()
    finally:
        md.logger.removeHandler(cap)
        md.logger.setLevel(lvl)
    return snap, cap.lines


def _files():
    for d in SCAN:
        p = os.path.join(ROOT, d)
        if p.endswith(".py"):
            if os.path.isfile(p):
                yield p
            continue
        for a, dirs, fs in os.walk(p):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in fs:
                if f.endswith(".py"):
                    yield os.path.join(a, f)


def _vixy(node):
    for n in ast.walk(node):
        if isinstance(n, ast.Attribute) and n.attr.lower() in (
                "vix", "vix_band", "vix_at_signal", "vix_at_plan", "new_entries_allowed"):
            return True
        if isinstance(n, ast.Name) and (n.id.upper().startswith("VIX") or n.id.lower() in ("vix", "vix_band")):
            return True
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and (
                n.value == "CRISIS" or n.value.lower() in ("vix", "vix_band", "new_entries_allowed")):
            return True                                # getattr(x, "vix") / d["vix_band"] reads too
    return False


def _refuses(body):
    return any(isinstance(n, (ast.Return, ast.Continue, ast.Raise)) for st in body for n in ast.walk(st))


def _scan():
    hits, tokens = [], []
    for f in _files():
        rel = os.path.relpath(f, ROOT).replace(os.sep, "/")
        src = open(f, encoding="utf-8").read()
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            hits.append(f"{rel}: unparseable ({e})")
            continue
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))] + [tree]:
            name = getattr(fn, "name", "<module>")
            if (rel, name) in LABELLERS:
                continue
            body = fn.body
            # only the statements that belong to this scope (nested defs are scanned on their own)
            stack = list(body)
            while stack:
                n = stack.pop()
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and fn is not tree:
                    continue
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn is tree:
                    continue
                if isinstance(n, ast.If) and _vixy(n.test) and (_refuses(n.body) or _refuses(n.orelse)):
                    hits.append(f"{rel}:{n.lineno} in {name}: if {ast.unparse(n.test)[:100]}")
                stack.extend(c for c in ast.iter_child_nodes(n) if isinstance(c, ast.stmt))
        try:
            for tok in tokenize.generate_tokens(io.StringIO(src).readline):
                if tok.type == tokenize.NAME and tok.string in ("new_entries_allowed", "VIX_NO_ENTRY_THRESHOLD"):
                    tokens.append(f"{rel}:{tok.start[0]} {tok.string}")
        except (tokenize.TokenError, IndentationError):
            pass
    for p in ("config.py",):
        src = open(os.path.join(ROOT, p), encoding="utf-8").read()
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.NAME and tok.string in ("new_entries_allowed", "VIX_NO_ENTRY_THRESHOLD"):
                tokens.append(f"{p}:{tok.start[0]} {tok.string}")
    return sorted(set(hits)), sorted(set(tokens))


def main():
    try:
        import config
        import data.macro_data as md
        import risk.session_guard as sg
        import utils.time_utils as tu
    except Exception as e:                                       # noqa: BLE001
        print(f"NOT RUN — imports failed: {type(e).__name__}: {e}")
        return 2

    real_now = tu.now_et

    def at(y, mo, d, h, mi):
        return datetime(y, mo, d, h, mi, tzinfo=ET)

    def verdict(macro, when, rehearsal=False):
        tu.now_et = lambda: when
        try:
            return sg.SessionGuard().can_enter(macro, rehearsal=rehearsal)
        finally:
            tu.now_et = real_now

    FRI = (2026, 11, 20)
    s39, lines39 = _snapshot(md, 39.53)
    s80, _ = _snapshot(md, 80.0)
    s29, _ = _snapshot(md, 29.99)

    # ── N1 the 2026-11-20 case ──
    v1 = verdict(s39, at(*FRI, 12, 17))
    check("N1 Fri 11-20 12:17 ET, VIX 39.53 (CRISIS): can_enter admits",
          s39.vix_band == "CRISIS" and v1 == (True, ""), f"band={s39.vix_band} verdict={v1}")

    # ── N2 VIX 80, and the rehearsal ──
    v2 = verdict(s80, at(*FRI, 12, 17))
    v2o = verdict(s39, at(*FRI, 16, 53))
    v2r = verdict(s39, at(*FRI, 16, 53), rehearsal=True)
    check("N2 VIX 80 (CRISIS) admits at 12:17; at 16:53 VIX 39.53 is refused only as outside RTH, a rehearsal passes",
          s80.vix_band == "CRISIS" and v2 == (True, "")
          and v2o == (False, "outside RTH")
          and v2r[0] is True and "rehearsal" in v2r[1] and "vix" not in v2r[1].lower(),
          f"band80={s80.vix_band} v80={v2} outside={v2o} rehearsal={v2r}")

    # ── N3 the field is gone; the band stays ──
    fields = {f.name for f in dataclasses.fields(md.MacroSnapshot)}
    line = next((l for l in lines39 if l.startswith("Macro snapshot")), "")
    check("N3 MacroSnapshot has no new_entries_allowed, the log line no entries= verdict, config no "
          "VIX_NO_ENTRY_THRESHOLD; the band is CRISIS at >= 30, ELEVATED at 29.99",
          "new_entries_allowed" not in fields and not hasattr(s39, "new_entries_allowed")
          and line and "entries=" not in line
          and not hasattr(config, "VIX_NO_ENTRY_THRESHOLD")
          and config.VIX_CRISIS_THRESHOLD == 30 and s29.vix_band == "ELEVATED"
          and md.MacroManager()._classify_vix(30.0) == "CRISIS",
          f"fields={sorted(fields)} line={line!r} cfg={hasattr(config, 'VIX_NO_ENTRY_THRESHOLD')} band29={s29.vix_band}")

    # ── N4 the other gates refuse as before; the snapshot changes nothing ──
    grid = [
        (at(2026, 11, 21, 12, 0), False, "outside RTH"),          # Saturday
        (at(2026, 11, 26, 12, 0), False, "outside RTH"),          # Thanksgiving
        (at(*FRI, 9, 34), False, "opening range still forming"),
        (at(*FRI, 15, 46), False, "past 15:45 ET hard close"),
        (at(*FRI, 9, 35), True, ""),
        (at(*FRI, 15, 44), True, ""),
    ]
    bad = []
    for when, ok, why in grid:
        vn, vc = verdict(None, when), verdict(s39, when)
        if vn != vc or vn[0] is not ok or (why and not vn[1].startswith(why)) or (not why and vn[1] != ""):
            bad.append((when.strftime("%m-%d %H:%M"), vn, vc))
    check("N4 outside RTH (Sat, Thanksgiving), 09:34 and 15:46 still refuse; 09:35 and 15:44 admit; VIX 39.53 "
          "changes no verdict", not bad, f"{bad}")

    # ── N5 the source scan ──
    hits, tokens = _scan()
    gsrc = open(os.path.join(ROOT, "risk", "session_guard.py"), encoding="utf-8").read()
    fn = next(n for n in ast.walk(ast.parse(gsrc)) if isinstance(n, ast.FunctionDef) and n.name == "can_enter")
    reads_macro = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Name) and n.id == "macro"]
    check("N5 no code path refuses an entry on the VIX: no VIX-test branch returns/raises/continues outside the "
          "labeller, can_enter never reads macro, no new_entries_allowed / VIX_NO_ENTRY_THRESHOLD token",
          not hits and not reads_macro and not tokens,
          f"hits={hits} can_enter reads macro at {reads_macro} tokens={tokens}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} of 5 failed: {', '.join(FAILED)}")
        return 1
    print("\nGREEN — no entry is refused on the VIX; a CRISIS band is recorded, never sat out (N1-N5)")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        if _TD.startswith(tempfile.gettempdir()) and os.path.basename(_TD).startswith("check_no_vix_gate_"):
            shutil.rmtree(_TD, ignore_errors=True)
    sys.exit(rc)
