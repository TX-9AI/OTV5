#!/usr/bin/env python3
# tests/check_series_lookback.py — v5.1
# v5.1  2026-10-31  OTV5 r66 (RET.1) — THE FOUR TICK TABLES ARE KEPT ONE DAY ON THE BOX, AND NO TRADING OR
#   INDICATOR CODE READS THEM OLDER THAN TODAY. The operator, 2026-10-31, on GOOGL's disk (92%, feed_store.db
#   1.78G, quote_series 745M of it): "On googl can we delete everything already stored in the warehouse & then
#   cleanup"; asked "does this affect trading or indicators?", and said yes to the long-term change.
#   warehouse/retention_purge v5.1 keeps quote_series, greeks_series, prints and last_trade 1 day (was 3), still
#   clamped to the push mark (_safe_cutoff); a box that never pushes stays age-only.
#   THIS GATE IS THE ANSWER TO THE OPERATOR'S QUESTION, NOT AN ASSERTION OF IT:
#     L1  policy: those four at 1 day, session_summary / theo_series / underlying_series still 3   [red on base]
#     L2  the clamp still holds at 1 day: a push mark 2 days old wins and is named; a never-push box is age-only
#     L3  inventory (AST): every SQL string under strategy/ execution/ analysis/ data/ risk/ derived/ and main.py
#         that READS one of the four tables is one of the seven reviewed readers - a new reader is RED until
#         its window is reviewed here
#     L4  every reviewed reader's SQL carries a lower bound on ts_epoch
#     L5  every call site of a reader (aliases and anchors._A.* included) passes no window, a literal, or a
#         module constant, each <= MAX_WINDOW_S (1 h); tape_at_level's caller falls back to now-900
#     L6  behaviour: on a fixture store, deleting every row older than 1 day leaves all seven readers' outputs
#         unchanged; the negative control (a 2-day window) DOES change, so the fixture can see a long reader
"""Gate: the 1-day tick-table retention cannot change what trading or indicator code reads."""
import ast
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

TABLES = ("quote_series", "greeks_series", "prints", "last_trade")
OTHER_THREE = ("session_summary", "theo_series", "underlying_series")
SCOPE_DIRS = ("strategy", "execution", "analysis", "data", "risk", "derived")
MAX_WINDOW_S = 3600.0
DAY = 86400.0

# (file, function) -> the reviewed look-back. Adding a reader means adding it HERE, with its window.
READERS = {
    ("analysis/order_flow.py", "aggression"): "window_s (DEFAULT_WINDOW_S 300 s)",
    ("analysis/order_flow.py", "depth"): "window_s (60 s)",
    ("analysis/second_order.py", "derive_for_symbol"): "lookback_s (900 s; surface passes LOOKBACK_S 900)",
    ("analysis/tape_at_level.py", "measure"): "since_epoch = the signal's break ts, else now-900 (record-only)",
    ("derived/anchors.py", "aggressor_share"): "secs (300 s)",
    ("derived/surface.py", "derive"): "now-120 s and now-LOOKBACK_S (900 s)",
}
READER_SITES = 7      # derived/surface.derive holds two reads
# function name -> (positional index of the window argument, keyword name)
CALLS = {
    "aggression": (2, "window_s"),
    "depth": (2, "window_s"),
    "pressure_into_level": (4, "window_s"),
    "derive_for_symbol": (2, "lookback_s"),
    "aggressor_share": (2, "secs"),
}
# wrappers allowed to pass their own window parameter through
PASS_THROUGH = {("analysis/order_flow.py", "pressure_into_level")}

_fails = []


def ck(tag, ok, msg=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {tag}  {msg}")
    if not ok:
        _fails.append(tag)


def _files():
    out = [os.path.join(ROOT, "main.py")]
    for d in SCOPE_DIRS:
        for dp, _dn, fs in os.walk(os.path.join(ROOT, d)):
            if "__pycache__" in dp:
                continue
            out += [os.path.join(dp, f) for f in fs if f.endswith(".py")]
    return sorted(out)


READ_RE = re.compile(r"\b(?:FROM|JOIN)\s+(%s)\b" % "|".join(TABLES), re.I)


def _funcs(tree):
    """(func_node, [enclosing names]) for every def, so a nested def is attributed to itself."""
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield n


def _inventory():
    """{(rel, func): [(lineno, table, sql)]} for every SQL string constant that reads a tick table."""
    found = {}
    for f in _files():
        rel = os.path.relpath(f, ROOT)
        try:
            tree = ast.parse(open(f, encoding="utf-8").read())
        except SyntaxError as exc:
            ck("L3", False, f"{rel} does not parse ({exc})")
            continue
        owner = {}
        for fn in _funcs(tree):            # ast.walk is breadth-first: an outer def comes first, an inner one overrides
            for n in ast.walk(fn):
                owner[id(n)] = fn.name
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                for m in READ_RE.finditer(n.value):
                    key = (rel, owner.get(id(n), "<module>"))
                    found.setdefault(key, []).append((n.lineno, m.group(1), n.value))
    return found


def _module_consts(tree):
    out = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and \
                isinstance(n.value.value, (int, float)):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = float(n.value.value)
    return out


def _defaults():
    """{func: default window} read from the readers' own signatures."""
    out = {}
    for rel in ("analysis/order_flow.py", "analysis/second_order.py", "derived/anchors.py"):
        tree = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())
        consts = _module_consts(tree)
        for fn in tree.body:
            if isinstance(fn, ast.FunctionDef) and fn.name in CALLS:
                _pos, kw = CALLS[fn.name]
                names = [a.arg for a in fn.args.args]
                if kw not in names:
                    continue
                i = names.index(kw) - (len(names) - len(fn.args.defaults))
                d = fn.args.defaults[i] if i >= 0 else None
                if isinstance(d, ast.Constant):
                    out[fn.name] = float(d.value)
                elif isinstance(d, ast.Name):
                    out[fn.name] = consts.get(d.id)
    return out


def _call_sites():
    """[(rel, lineno, func, verdict_ok, why)] for every call of a reader in scope."""
    sites = []
    for f in _files():
        rel = os.path.relpath(f, ROOT)
        tree = ast.parse(open(f, encoding="utf-8").read())
        consts = _module_consts(tree)
        alias = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module and \
                    n.module.split(".")[-1] in ("order_flow", "second_order", "anchors"):
                for a in n.names:
                    alias[a.asname or a.name] = a.name
        for fn in _funcs(tree):
            params = {a.arg for a in fn.args.args}
            for n in ast.walk(fn):
                if not isinstance(n, ast.Call):
                    continue
                if isinstance(n.func, ast.Name):
                    name = alias.get(n.func.id)
                elif isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and \
                        n.func.value.id.startswith("_A") and n.func.attr in CALLS:
                    name = n.func.attr                    # `from derived import anchors as _A*`
                else:
                    name = None
                if name not in CALLS:
                    continue
                pos, kw = CALLS[name]
                arg = None
                if len(n.args) > pos:
                    arg = n.args[pos]
                for k in n.keywords:
                    if k.arg == kw:
                        arg = k.value
                if arg is None:
                    sites.append((rel, n.lineno, name, None, "default"))
                elif isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float)):
                    sites.append((rel, n.lineno, name, float(arg.value), "literal"))
                elif isinstance(arg, ast.Name) and arg.id in consts:
                    sites.append((rel, n.lineno, name, consts[arg.id], arg.id))
                elif isinstance(arg, ast.Name) and arg.id in params and (rel, fn.name) in PASS_THROUGH:
                    sites.append((rel, n.lineno, name, "pass", f"{fn.name}({arg.id})"))
                else:
                    sites.append((rel, n.lineno, name, "unknown", ast.dump(arg)[:60]))
    return sites


_L6 = r'''
import json, os, sqlite3, sys, time
sys.path.insert(0, sys.argv[1]); db = sys.argv[2]
now = time.time(); DAY = 86400.0
from analysis.order_flow import aggression, depth, pressure_into_level
from analysis.second_order import derive_for_symbol
from analysis.tape_at_level import measure
from derived import anchors
def read():
    c = sqlite3.connect(db)
    out = {
        "aggression": aggression(c, "GOOGL"),
        "aggression_180": aggression(c, "GOOGL", 180.0),
        "pressure": pressure_into_level(c, "GOOGL", 100.0, "resistance", 300.0),
        "depth": depth(c, ".GOOGL251107C100"),
        "second_order": derive_for_symbol(c, "GOOGL", 900.0),
        "anchors_share": anchors.aggressor_share(100.0),
        "tape": measure("GOOGL", 100.0, now - 900, now, db_path=db),
        "NEG_2day_window": aggression(c, "GOOGL", 2 * DAY),
    }
    c.close()
    return json.loads(json.dumps(out, default=str, sort_keys=True))
before = read()
c = sqlite3.connect(db)
old = {t: c.execute("select count(*) from %s where ts_epoch < ?" % t, (now - DAY,)).fetchone()[0]
       for t in ("quote_series", "greeks_series", "prints", "last_trade")}
for t in old:
    c.execute("delete from %s where ts_epoch < ?" % t, (now - DAY,))
c.commit(); c.close()
after = read()
print(json.dumps({"before": before, "after": after, "old_rows": old}))
'''


def _fixture(path):
    """The four tables with the feed's own CREATE statements (read from data/candle_feed.py's source)."""
    src = open(os.path.join(ROOT, "data", "candle_feed.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    c = sqlite3.connect(path)
    made = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            m = re.search(r"CREATE TABLE IF NOT EXISTS (\w+)", n.value)
            if m and m.group(1) in TABLES:
                c.execute(n.value)
                made.add(m.group(1))
    now = time.time()
    opt = ".GOOGL251107C100"
    for age in (1.5 * DAY, 1.2 * DAY):       # yesterday: what a 1-day purge deletes - big, one-sided
        for i in range(40):
            ts = now - age + i
            c.execute("insert into prints (symbol, ts_epoch, sequence, price, size, aggressor_side)"
                      " values ('GOOGL', ?, ?, 100.0, 5000, 'SELL')", (ts, i))
            c.execute("insert into quote_series (streamer_symbol, ts_epoch, bid_price, ask_price, bid_size, ask_size)"
                      " values (?, ?, 1.0, 1.2, 900, 10)", (opt, ts))
            c.execute("insert into greeks_series (streamer_symbol, ts_epoch, delta, volatility)"
                      " values (?, ?, 0.9, 0.9)", (opt, ts))
            c.execute("insert into last_trade (symbol, ts_epoch, price, size) values ('GOOGL', ?, 100.0, 1)", (ts,))
    for i in range(30):                       # today: the last 150 s
        ts = now - 150 + 5 * i
        c.execute("insert into prints (symbol, ts_epoch, sequence, price, size, aggressor_side)"
                  " values ('GOOGL', ?, ?, 100.0, ?, ?)", (ts, 1000 + i, 10 + i, "BUY" if i % 3 else "SELL"))
        c.execute("insert into quote_series (streamer_symbol, ts_epoch, bid_price, ask_price, bid_size, ask_size)"
                  " values (?, ?, ?, ?, ?, ?)", (opt, ts, 1.0 + i / 100, 1.1 + i / 100, 20 + i, 30 - i / 2))
        c.execute("insert into greeks_series (streamer_symbol, ts_epoch, delta, volatility)"
                  " values (?, ?, ?, ?)", (opt, ts, 0.5 + i / 100, 0.30 + i / 1000))
        c.execute("insert into last_trade (symbol, ts_epoch, price, size) values ('GOOGL', ?, 100.0, 1)", (ts,))
    c.commit()
    c.close()
    return made


def main():
    from warehouse import retention_purge as RP

    # ── L1 policy ────────────────────────────────────────────────────────────
    got = {t: RP.ARTIFACT_DAYS.get(t) for t in TABLES + OTHER_THREE}
    ck("L1", all(got[t] == 1 for t in TABLES) and all(got[t] == 3 for t in OTHER_THREE),
       f"ARTIFACT_DAYS {got} (want the four tick tables 1, the other three 3)")

    # ── L2 the clamp at the shipped value ────────────────────────────────────
    st = tempfile.mkdtemp(prefix="lookback_state_")
    probe = r'''
import json, os, sys, time
sys.path.insert(0, sys.argv[1])
import warehouse.retention_purge as rp
st = os.environ["OT_WAREHOUSE_STATE"]; now = time.time(); DAY = 86400.0
age = now - rp.ARTIFACT_DAYS["quote_series"] * DAY
json.dump({"series|quote_series": now - 2 * DAY}, open(rp.SERIES_LEDGER, "w"))
rp.NEVER_PUSH_DROPIN = os.path.join(st, "none.conf"); rp._unit_state = lambda u: "enabled"; rp._NEVER = None
c, note = rp._safe_cutoff("quote_series", age, rp.SERIES_LEDGER, "series")
can = [round((now - c) / DAY, 3), note[:7]]
rp._unit_state = lambda u: "masked"; rp._NEVER = None
c, note = rp._safe_cutoff("quote_series", age, rp.SERIES_LEDGER, "series")
never = [round((now - c) / DAY, 3), note[:20]]
src = open(os.path.join(sys.argv[1], "warehouse", "retention_purge.py")).read()
body = src.split("for table, days in ARTIFACT_DAYS.items():", 1)[-1][:1500]
print(json.dumps({"can": can, "never": never, "clamped_in_purge": "_safe_cutoff(table, cutoff, SERIES_LEDGER" in body,
                  "days": rp.ARTIFACT_DAYS["quote_series"]}))
'''
    r = subprocess.run([sys.executable, "-c", probe, ROOT], capture_output=True, text=True, timeout=60,
                       env={**os.environ, "OT_WAREHOUSE_STATE": st})
    try:
        L2 = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        L2 = {"err": r.stderr[-200:]}
    ck("L2", L2.get("can") == [2.0, "CLAMPED"] and L2.get("never", [0])[0] == float(L2.get("days", -1))
       and L2.get("never", ["", ""])[1].startswith("push mark IGNORED") and L2.get("clamped_in_purge") is True,
       f"{L2} (a 2-day-old mark wins and is named; a never-push box is age-only; purge() still clamps)")

    # ── L3 inventory ─────────────────────────────────────────────────────────
    inv = _inventory()
    unknown = sorted(k for k in inv if k not in READERS)
    missing = sorted(k for k in READERS if k not in inv)
    n_sites = sum(len(v) for v in inv.values())
    ck("L3", not unknown and not missing and n_sites == READER_SITES,
       f"{n_sites} read site(s) in {len(inv)} function(s); unreviewed={unknown} gone={missing}")

    # ── L4 a lower bound on ts_epoch in every read ───────────────────────────
    unbounded = [(k, ln) for k, v in inv.items() for ln, _t, sql in v
                 if not re.search(r"ts_epoch\s*>=?\s*\?", sql)]
    ck("L4", not unbounded, f"reads without `ts_epoch >= ?`: {unbounded}")

    # ── L5 windows at every call site ────────────────────────────────────────
    dflt = _defaults()
    bad, n = [], 0
    for rel, ln, name, val, why in _call_sites():
        n += 1
        if val is None:
            val = dflt.get(name)
        if val == "pass":
            continue
        if not isinstance(val, float) or val > MAX_WINDOW_S:
            bad.append(f"{rel}:{ln} {name} {why}={val}")
    tsrc = open(os.path.join(ROOT, "execution", "entry_engine.py"), encoding="utf-8").read()
    tape_ok = "since_epoch=_since or (time.time() - 900)" in tsrc and 'getattr(signal, "orb_break_ts"' in tsrc
    ck("L5", not bad and n >= 10 and all(v is not None and v <= MAX_WINDOW_S for v in dflt.values())
       and len(dflt) == len(CALLS) and tape_ok and MAX_WINDOW_S < DAY,
       f"{n} call site(s), defaults {dflt}, over {MAX_WINDOW_S:.0f}s or unresolved: {bad}, "
       f"tape_at_level caller now-900 fallback={tape_ok}")

    # ── L6 behaviour ─────────────────────────────────────────────────────────
    d = tempfile.mkdtemp(prefix="lookback_feed_")
    db = os.path.join(d, "feed_store.db")
    made = _fixture(db)
    r = subprocess.run([sys.executable, "-c", _L6, ROOT, db], capture_output=True, text=True, timeout=120,
                       env={**os.environ, "OT_FEED_DB": db, "OT_INSTRUMENT": "GOOGL", "OT_SWEEP_NESTED": "1"})
    try:
        L6 = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        L6 = None
    if L6 is None:
        ck("L6", False, f"probe failed: {r.stderr[-300:]}")
    else:
        b, a = dict(L6["before"]), dict(L6["after"])
        neg_b, neg_a = b.pop("NEG_2day_window"), a.pop("NEG_2day_window")
        same = [k for k in b if b[k] == a[k]]
        real = [k for k in b if b[k] not in (None, {}, [])]
        ck("L6", made == set(TABLES) and same == list(b) and len(real) == len(b)
           and all(v > 0 for v in L6["old_rows"].values()) and neg_b != neg_a,
           f"old rows deleted {L6['old_rows']}; unchanged {len(same)}/{len(b)}; non-empty {len(real)}/{len(b)}; "
           f"negative control (2-day window) changed={neg_b != neg_a}")

    if _fails:
        print(f"\nRED — {len(_fails)} check(s) failed: {', '.join(_fails)}")
        return 1
    print("\nGREEN — L1-L6")
    return 0


if __name__ == "__main__":
    sys.exit(main())
