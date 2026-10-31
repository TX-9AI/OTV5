#!/usr/bin/env python3
"""
tests/check_no_parc.py  v5.1
v5.1  2026-10-31  OTV5 r68 (CFG.5) — N4 RE-POINTED, NOT DROPPED (section 38.4): seven more items left configure.sh's menu, TCS's
      among them (the operator, 2026-10-31: "15&16-same thing. These are DEAD thesis"; "Just the menu item for TCS, keep
      briefing the shadow."), so Done is 9 and the prompt names 1-9. The PARC property (no item, no key) is unchanged.
v5.0  2026-10-31  OTV5 r67 (PARC.4) — new. PARC IS REMOVED AND PARK IS UNCHANGED. The operator, 2026-10-31: "On PARC,
      no. It was an idea. It failed. It's done." and "Yes" to removing its code. PARC (PARK's entry sold as a credit
      spread, OTV5 r46; paused to log at r50) was never an active strategy. This gate pins that nothing can reach it
      any more, and that PARK - which shared its first-hour read with PARC - decides exactly as it did on 93c7f93.

  N1  config: no ENTRY_WINDOWS["PARC"], no PARC_MODE / PARC_ENV_REFUSED / PARC_MIN_CREDIT, CAP_EXCLUDED_STRATEGIES
      without PARC (with PARK), and no code reads OT_PARC
  N2  plan_state: PARC is not in TABLE (state() falls to the unknown-name default; known() is False)
  N3  dispatch: strategy/parc.py and strategy/parc_plan.py are gone (the import fails); main.py has no _attempt_parc,
      no _parc_strategy and no _STRUCTURE_BY_NAME["PARC"]; the admission table has no PARC rule; risk_manager has no
      _size_parc; exit_engine has no _evaluate_parc / _parc_nickel; structure.of() names no PARC; and an AST sweep of
      every non-test .py finds no identifier and no (non-docstring) string naming PARC
  N4  configure.sh: no parc_label / change_parc / OT_PARC outside comments; (r68) Done is 9, the prompt
      names 1-9
  N5  PARK unchanged: on a fixture (a long, a short, a quiet first hour, GATE-G against the gap, the 11:03 dormant
      minute) PARK's prepared checks, conditions and signal, its admission rule, its size, its plan state, its window
      and its cap exclusion equal tests/fixtures/park_plan_93c7f93.json, captured on base 93c7f93 by this file's
      --probe

Born red on 93c7f93 at N1, N2, N3, N4 (N5 green on both: PARK is not what changes).
Run:  python3 tests/check_no_parc.py          (exit 0 green, 1 red, 2 not run)
      python3 tests/check_no_parc.py --probe  (print PARK's fixture output as JSON)
"""
import ast
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "tests", "fixtures", "park_plan_93c7f93.json")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


# ── N5's probe: runs in a fresh interpreter with scratch stores ─────────────
def probe():
    import sqlite3
    import tempfile
    from datetime import date, datetime
    from zoneinfo import ZoneInfo
    sys.path.insert(0, ROOT)
    td = tempfile.mkdtemp(prefix="check_no_parc_")
    for k, v in {"OT_TRADES_DB": "t.db", "OT_DERIVED_DB": "d.db", "OT_FEED_DB": "f.db", "OT_LOG_FILE": "bot.log",
                 "OT_SIGNAL_JOURNAL_DIR": "sj", "OT_RESTING_DB": "r.db", "OT_RESTING_STOP_STATE": "rs.json",
                 "OT_COUNTERFACTUAL_DIR": "cf", "OT_PLAN_STATES_FILE": "ps.json"}.items():
        os.environ[k] = os.path.join(td, v)
    os.environ.update(OT_RISK_USD="1050", OT_ORB_BUDGET_USD="2500", OT_INSTRUMENT="QQQ")
    for k in ("OT_PARK", "OT_PARC"):
        os.environ.pop(k, None)
    feed_db = os.environ["OT_FEED_DB"]
    et = ZoneInfo("America/New_York")
    day, prev, sym = date(2026, 10, 28), date(2026, 10, 27), "QQQ"
    exp = day.isoformat()

    def ms(d, h, m):
        return int(datetime(d.year, d.month, d.day, h, m, tzinfo=et).timestamp() * 1000)

    def feed(o930, c1030, c1100, prev_close):
        if os.path.exists(feed_db):
            os.remove(feed_db)
        c = sqlite3.connect(feed_db)
        c.execute("CREATE TABLE candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, ts_epoch_ms INTEGER NOT NULL, "
                  "open REAL, high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY (symbol, interval, ts_epoch_ms))")
        c.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", [
            (sym, "1m", ms(day, 9, 30), o930, o930 + .1, o930 - .1, o930 + .05, 1),
            (sym, "1m", ms(day, 10, 30), c1030, c1030 + .1, c1030 - .1, c1030, 1),
            (sym, "1m", ms(day, 11, 0), c1100, c1100 + .1, c1100 - .1, c1100, 1),
            (sym, "1m", ms(prev, 15, 59), 1, 1, 1, prev_close, 1),
            (sym, "1m", ms(prev, 16, 5), 1, 1, 1, prev_close + 5, 1)])
        c.commit()
        c.close()

    class K:
        def __init__(self, strike, bid, ask, delta, side):
            self.strike, self.bid, self.ask, self.delta, self.iv = float(strike), bid, ask, delta, 0.20
            self.mark, self.expiry, self.option_type = (bid + ask) / 2, exp, side
            self.symbol = f"{sym:<6}{day:%y%m%d}{side}{int(strike * 1000):08d}"
            self.streamer_symbol = f".X{side}{strike:g}"

    class Chain:
        def __init__(self, spot):
            self.expiry, self.spot_price, self.calls, self.puts = exp, spot, [], []
            for s in range(690, 716):
                for call, lst in ((True, self.calls), (False, self.puts)):
                    intr = max(spot - s, 0.0) if call else max(s - spot, 0.0)
                    mid = intr + max(0.05, 1.20 - 0.25 * abs(s - spot))
                    lst.append(K(s, round(mid - 0.03, 2), round(mid + 0.03, 2), 0.5 if call else -0.5,
                                 "C" if call else "P"))

    def canon(v):
        if isinstance(v, float):
            return round(v, 9)
        if isinstance(v, (str, int, bool)) or v is None:
            return v
        if isinstance(v, dict):
            return {str(k): canon(x) for k, x in sorted(v.items(), key=lambda kv: str(kv[0]))}
        if isinstance(v, (list, tuple)):
            return [canon(x) for x in v]
        if isinstance(v, K):
            return {"strike": v.strike, "side": v.option_type, "bid": v.bid, "ask": v.ask}
        return type(v).__name__

    import config
    from strategy.park import Park
    from strategy import plan_state as PS
    from risk.risk_manager import RiskManager
    from execution import position_manager as PM
    spec = Park()
    out = {}
    cases = {"long": (700.0, 702.1, 702.4, 699.0, 702.4, "11:01"),
             "short": (700.0, 697.9, 697.6, 701.0, 697.6, "11:02"),
             "quiet": (700.0, 700.9, 701.0, 699.0, 701.0, "11:01"),
             "gate_g": (700.0, 702.1, 702.4, 701.0, 702.4, "11:01"),
             "dormant": (700.0, 702.1, 702.4, 699.0, 702.4, "11:03")}
    for name, (o, c1030, c1100, pc, px, hm) in cases.items():
        feed(o, c1030, c1100, pc)
        prep = spec.prepare(price_now=px, now_et=hm, chain=Chain(px), prior_close=None, day=day, symbol=sym)
        feed(o, c1030, c1100, pc)
        sig = spec.generate_signal(price_now=px, now_et=hm, chain=Chain(px), prior_close=None, day=day, symbol=sym)
        p = {} if prep is None else {k: canon(getattr(prep, k, None)) for k in prep.__slots__
                                     if k not in ("tick", "spec")}
        if prep is not None:
            p["checks"] = canon(dict(prep.tick.checks))
        s = None if sig is None else canon({k: v for k, v in vars(sig).items() if not k.startswith("_")})
        out[name] = {"prep": p, "signal": s}
    rule = PM._DEFAULT_RULES[PM.PARK]
    out["admission"] = canon({k: getattr(rule, k) for k in ("window", "max_open_of_type", "max_tries_per_session",
                                                            "cap_exempt") if hasattr(rule, k)})
    sz = RiskManager().size_for("long_debit", premium=1.62)
    out["size"] = canon({"contracts": sz.contracts, "allowed": sz.allowed, "rule": sz.rule})
    out["state"] = PS.state("PARK")
    out["window"] = canon(config.ENTRY_WINDOWS["PARK"])
    out["cap_excludes_park"] = "PARK" in tuple(config.CAP_EXCLUDED_STRATEGIES)
    import shutil
    shutil.rmtree(td, ignore_errors=True)
    print(json.dumps(out, sort_keys=True))


def _fresh(code):
    env = {k: v for k, v in os.environ.items() if not k.startswith("OT_")}
    env["OT_INSTRUMENT"] = "QQQ"
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:                                           # noqa: BLE001
        return {"_error": (r.stderr or r.stdout)[-400:]}


_IDENT = re.compile(r"(^|_)parc(_|$)", re.I)
_WORD = re.compile(r"\bPARC\b|\bOT_PARC\b|^parc(_|$)")


def _ast_hits(path):
    """Identifiers and non-docstring string constants that name PARC."""
    try:
        tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    except (SyntaxError, UnicodeDecodeError):
        return []
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            b = getattr(node, "body", None) or []
            if b and isinstance(b[0], ast.Expr) and isinstance(getattr(b[0], "value", None), ast.Constant):
                docs.add(id(b[0].value))
    hits = []
    for node in ast.walk(tree):
        name = None
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Attribute):
            name = node.attr
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name
        elif isinstance(node, ast.alias):
            name = node.asname or node.name
        elif isinstance(node, ast.ImportFrom):
            name = node.module or ""
        if name and any(_IDENT.search(part) for part in re.split(r"[.]", name)):
            hits.append(f"{os.path.relpath(path, ROOT)}:{getattr(node, 'lineno', '?')} {name}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            if _WORD.search(node.value):
                hits.append(f"{os.path.relpath(path, ROOT)}:{node.lineno} {node.value[:60]!r}")
    return hits


def main():
    if "--probe" in sys.argv:
        probe()
        return 0
    print("check_no_parc")
    try:
        import pandas  # noqa: F401
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2

    # ── N1 config ─────────────────────────────────────────────────────────────
    n1 = _fresh("import json, config as c\nprint(json.dumps({'ew': 'PARC' in c.ENTRY_WINDOWS, "
                "'attrs': [a for a in ('PARC_MODE', 'PARC_ENV_REFUSED', 'PARC_MIN_CREDIT') if hasattr(c, a)], "
                "'cap': list(c.CAP_EXCLUDED_STRATEGIES)}))")
    readers = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in (".git", "venv", "__pycache__", "tests")]
        for f in fn:
            fp = os.path.join(dp, f)
            if f.endswith(".py"):                               # code, not a changelog: AST, docstrings excluded
                readers += [h for h in _ast_hits(fp) if "OT_PARC" in h]
            elif f.endswith(".sh"):
                for i, line in enumerate(open(fp, encoding="utf-8", errors="replace"), 1):
                    if not line.lstrip().startswith("#") and re.search(r"\bOT_PARC\b", line):
                        readers.append(f"{os.path.relpath(fp, ROOT)}:{i}")
    check("N1 config: no ENTRY_WINDOWS['PARC'], no PARC_MODE / PARC_ENV_REFUSED / PARC_MIN_CREDIT, "
          "CAP_EXCLUDED_STRATEGIES == ('PARK',), and nothing reads OT_PARC",
          n1.get("ew") is False and n1.get("attrs") == [] and n1.get("cap") == ["PARK"] and not readers,
          f"{n1} readers={readers[:6]}")

    # ── N2 plan_state ─────────────────────────────────────────────────────────
    n2 = _fresh("import json\nfrom strategy import plan_state as S\n"
                "print(json.dumps({'table': 'PARC' in S.TABLE, 'known': bool(S.known('PARC'))}))")
    check("N2 plan_state: PARC is not in TABLE and is not known",
          n2.get("table") is False and n2.get("known") is False, f"{n2}")

    # ── N3 dispatch ───────────────────────────────────────────────────────────
    gone = [p for p in ("strategy/parc.py", "strategy/parc_plan.py") if os.path.exists(os.path.join(ROOT, p))]
    n3 = _fresh(
        "import json, importlib\n"
        "out = {}\n"
        "for m in ('strategy.parc', 'strategy.parc_plan'):\n"
        "    try:\n"
        "        importlib.import_module(m); out[m] = 'imported'\n"
        "    except ImportError:\n"
        "        out[m] = 'absent'\n"
        "from execution import position_manager as PM\n"
        "from execution.exit_engine import ExitEngine\n"
        "from risk.risk_manager import RiskManager\n"
        "from strategy import structure as ST\n"
        "out['pm'] = [k for k in PM._DEFAULT_RULES if 'PARC' in str(k).upper()] + (['PARC'] if hasattr(PM, 'PARC') else [])\n"
        "out['ee'] = [a for a in ('_evaluate_parc', '_parc_nickel') if hasattr(ExitEngine, a)]\n"
        "out['rm'] = hasattr(RiskManager, '_size_parc')\n"
        "out['of'] = str(ST.of({'strategy': 'PARC', 'setup_type': 'parc_long'}))\n"
        "print(json.dumps(out))")
    main_src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    mtree = ast.parse(main_src)
    main_defs = [n.name for n in ast.walk(mtree) if isinstance(n, ast.FunctionDef) and "parc" in n.name.lower()]
    sbn = []
    for n in ast.walk(mtree):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_STRUCTURE_BY_NAME" for t in n.targets) \
                and isinstance(n.value, ast.Dict):
            sbn = [getattr(k, "value", None) for k in n.value.keys]
    sweep = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in (".git", "venv", "__pycache__", "tests")]
        for f in fn:
            if f.endswith(".py"):
                sweep += _ast_hits(os.path.join(dp, f))
    check("N3 dispatch: parc.py / parc_plan.py gone and unimportable; main has no _attempt_parc / _parc_strategy / "
          "_STRUCTURE_BY_NAME['PARC']; no PARC admission rule, _size_parc, _evaluate_parc or _parc_nickel; "
          "structure.of() names no PARC; no non-test code names PARC",
          not gone and n3.get("strategy.parc") == "absent" and n3.get("strategy.parc_plan") == "absent"
          and not main_defs and "_parc_strategy" not in main_src and sbn and "PARC" not in sbn
          and n3.get("pm") == [] and n3.get("ee") == [] and n3.get("rm") is False
          and "CONDOR_LEG" not in str(n3.get("of")) and not sweep,
          f"gone={gone} {n3} main_defs={main_defs} sbn_has={'PARC' in sbn} sweep={sweep[:8]}")

    # ── N4 configure.sh ───────────────────────────────────────────────────────
    cfg = open(os.path.join(ROOT, "configure.sh"), encoding="utf-8").read()
    live = "\n".join(l for l in cfg.splitlines() if not l.lstrip().startswith("#"))
    bad = [w for w in ("parc_label", "change_parc", "OT_PARC", "PARC") if re.search(rf"\b{w}\b", live)]
    check("N4 configure.sh: no PARC item outside comments; 9) break, the prompt names 1-9 (r68: TCS's item left too)",
          not bad and re.search(r"^\s*9\)\s*break", cfg, re.M)
          and "Select [1-9]" in cfg and "Select [1-17]" not in cfg and "Select [1-16]" not in cfg, f"live mentions {bad}")

    # ── N5 PARK unchanged ─────────────────────────────────────────────────────
    env = {k: v for k, v in os.environ.items() if not k.startswith("OT_")}
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--probe"], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=240)
    try:
        got = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:                                           # noqa: BLE001
        got = {"_error": (r.stderr or r.stdout)[-400:]}
    want = json.load(open(GOLDEN))
    diff = sorted(k for k in set(want) | set(got) if want.get(k) != got.get(k))
    check("N5 PARK unchanged on the fixture: prepared checks, conditions, signal (long 702C, short 698P, at the mark), "
          "quiet / GATE-G refusals, the 11:03 dormant minute, admission, size, state, window and cap exclusion equal "
          "93c7f93's",
          not diff and got.get("long", {}).get("signal") is not None, f"differs at {diff} {got.get('_error', '')}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — N1-N5")
    return 0


if __name__ == "__main__":
    sys.exit(main())
