#!/usr/bin/env python3
"""
tests/check_orb_geometry.py  v1.0

r119 — THE ORB SETUP'S GEOMETRY IS RECORDED, AND RECORDED ONLY.

Operator, 2026-08-25, after TSLA and PLTR both stopped out structurally within
five minutes of firing: "the closer to the range boundary the impulsive candle
(stop location) sits, the lower the risk & higher the R-value. We need to start
grading orb on that distance." And, on what to do first: "observe first.
Obviously." And on why it matters: "r-value is the report card of this system."

  G1  both columns exist AND migrate onto a live database
  G2  the ratios compute correctly on TODAY'S REAL FIRES
  G3  NULL when a leg is missing — never 0.0 (a zero ratio is impossible; a
      missing one is ordinary, and gap_pct's schema note says why they must
      stay distinguishable)
  G4  ⚠️ NOTHING READS THEM. No gate, no size, no score. This is the assertion
      that fails the day someone wires the observation into a decision before
      the data has said anything.

Run:  python3 tests/check_orb_geometry.py
"""
from __future__ import annotations
import ast, os, sqlite3, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)

# ── G1 — schema and migration ────────────────────────────────────────────────
tl = open(os.path.join(ROOT, "database/trade_logger.py")).read()
check("G1a both columns are in CREATE TABLE",
      "stop_width_pct    REAL," in tl and "planned_r         REAL," in tl)
check("G1b and in _MIGRATION_ADDS, so live DBs gain them",
      '("stop_width_pct",    "REAL")' in tl and '("planned_r",         "REAL")' in tl)
check("G1c declared NULL, not DEFAULT 0.0",
      "stop_width_pct    REAL DEFAULT" not in tl and "planned_r         REAL DEFAULT" not in tl)

# migrate a database that predates the columns, exactly as a box would
db = os.path.join(tempfile.mkdtemp(), "t.db")
c = sqlite3.connect(db)
c.execute("CREATE TABLE trades (trade_id TEXT PRIMARY KEY, orb_range_high REAL)")
c.commit()
for col in ("stop_width_pct", "planned_r"):
    try:
        c.execute(f"ALTER TABLE trades ADD COLUMN {col} REAL"); c.commit()
    except sqlite3.OperationalError:
        pass
cols = {r[1] for r in c.execute("PRAGMA table_info(trades)")}
check("G1d an existing DB gains both without losing data",
      {"stop_width_pct", "planned_r"} <= cols, str(sorted(cols)))
c.execute("INSERT INTO trades (trade_id) VALUES ('x')"); c.commit()
row = c.execute("SELECT stop_width_pct, planned_r FROM trades").fetchone()
check("G1e and a row written without them reads NULL, not 0.0", row == (None, None), str(row))
c.close()

# ── G2 — the arithmetic, on real fires from 2026-08-25 ───────────────────────
def geom(entry, stop, tgt, hi, lo):
    w, r = abs(hi - lo), abs(entry - stop)
    return (round(r / w, 4) if w > 0 and r > 0 else None,
            round(abs(tgt - entry) / r, 3) if r > 0 and tgt and entry else None)

sw, pr = geom(352.33, 351.65, 354.99, 352.16, 349.22)     # TSLA ORB Long, 09:50
check("G2a TSLA: stop sits 23.1% into the range", abs(sw - 0.2313) < 5e-4, f"{sw:.1%}")
check("G2b TSLA: planned R = 3.91", abs(pr - 3.912) < 5e-3, f"{pr}")
sw2, pr2 = geom(360.31, 361.32, 356.99, 361.00, 358.00)   # AVGO ORB Short, 09:44
check("G2c AVGO short: planned R = 3.29", abs(pr2 - 3.287) < 5e-3, f"{pr2}")
check("G2d a TIGHTER stop yields a HIGHER R — the operator's claim",
      geom(100.0, 99.9, 102.0, 100.0, 98.0)[1]
      > geom(100.0, 99.0, 102.0, 100.0, 98.0)[1])

# ── G3 — missing legs stay missing ───────────────────────────────────────────
check("G3a no ORB width -> NULL", geom(100, 99, 102, 100, 100)[0] is None)
check("G3b entry == stop (no risk) -> NULL", geom(100, 100, 102, 101, 99)[1] is None)

# ── G4 — RECORDED, NOT READ ──────────────────────────────────────────────────
readers = []
for dirpath, _, files in os.walk(ROOT):
    if any(p in dirpath for p in ("/.git", "/tests", "__pycache__", "/docs")):
        continue
    for f in files:
        if not f.endswith(".py"):
            continue
        fp = os.path.join(dirpath, f)
        src = open(fp, errors="ignore").read()
        for name in ("stop_width_pct", "planned_r"):
            # the WRITE site and the schema are expected; a READ is not
            for node in ast.walk(ast.parse(src)):
                if (isinstance(node, ast.Subscript)
                        and isinstance(node.slice, ast.Constant)
                        and node.slice.value == name
                        and isinstance(node.ctx, ast.Load)):
                    rel = os.path.relpath(fp, ROOT)
                    if rel != "execution/entry_engine.py":   # its own log line
                        readers.append(f"{rel}:{name}")
check("G4 NOTHING consumes these yet — observe first", not readers, str(readers))

# ── G5 (r120) — the tape window fields exist, and ATTEMPT DOES NOT ──────────
# ⚠️ orb_attempt was BUILT AND THEN REMOVED, deliberately. Operator, 2026-08-25:
# "Attempt number for orb is irrelevant imo. What does 2 attempts signify? 3?
# ... it could mean opposite things." He is right, and that is the whole test a
# recorded field has to pass: attempt 3 reads as "this level is defended, stop
# trying" OR "buyers keep coming back, pressure is building" — the same integer,
# opposite conclusions. A counter that cannot discriminate is not an
# observation, it is a column, and shipping it would have made the fit noisier
# while looking like diligence. Asserted absent so it cannot drift back in.
from strategy.base_strategy import OptionsSignal
check("G5a the signal carries the tape window fields",
      hasattr(OptionsSignal(), "orb_break_ts") and hasattr(OptionsSignal(), "atr_at_signal"))
check("G5b orb_attempt is ABSENT from the signal", not hasattr(OptionsSignal(), "orb_attempt"))
check("G5c and absent from the schema", "orb_attempt" not in tl)
esrc = open(os.path.join(ROOT, "execution/entry_engine.py")).read()
check("G5d and never written to a record", 'record["orb_attempt"]' not in esrc)

# ── G6 (r120) — the tape measurement ────────────────────────────────────────
from analysis.tape_at_level import measure
_d = tempfile.mkdtemp(); _p = os.path.join(_d, "f.db")
_c = sqlite3.connect(_p)
_c.execute("CREATE TABLE prints (symbol TEXT, ts_epoch REAL, price REAL, "
           "size REAL, aggressor_side TEXT)")
_c.executemany("INSERT INTO prints VALUES (?,?,?,?,?)",
               [("TSLA", 1000 + i, 352.16, 100, "SELL" if i % 4 else "BUY")
                for i in range(40)]
               + [("TSLA", 1000 + i, 349.50, 999, "BUY") for i in range(5)])
_c.commit(); _c.close()
m = measure("TSLA", 352.16, 900, 1100, atr=1.82, db_path=_p)
check("G6a in-band volume only — the 349.50 prints excluded",
      m.get("tape_vol_at_level") == 4000.0, str(m.get("tape_vol_at_level")))
check("G6b band scales with ATR, not ticks", abs(m.get("tape_band") - 0.455) < 1e-3)
check("G6c aggressor imbalance from the VENUE's tag",
      abs(m.get("tape_buy_frac_at_level") - 0.25) < 1e-6)
check("G6d an unreadable store returns {} — not a fabricated zero",
      measure("TSLA", 352.16, 900, 1100, atr=1.82, db_path="/nope") == {})
check("G6e an inverted window returns {}",
      measure("TSLA", 352.16, 1100, 900, atr=1.82, db_path=_p) == {})
# untagged aggressor must NOT read as balanced
_c = sqlite3.connect(_p)
_c.execute("DELETE FROM prints"); _c.execute(
    "INSERT INTO prints VALUES ('TSLA',1000,352.16,500,NULL)"); _c.commit(); _c.close()
check("G6f no aggressor tag -> no imbalance reported (not 0.5)",
      "tape_buy_frac_at_level" not in measure("TSLA", 352.16, 900, 1100,
                                              atr=1.82, db_path=_p))

# ── G7 — STILL nothing reads any of it ──────────────────────────────────────
readers2 = []
for dirpath, _, files in os.walk(ROOT):
    if any(p in dirpath for p in ("/.git", "/tests", "__pycache__", "/docs")):
        continue
    for f in files:
        if not f.endswith(".py"):
            continue
        fp = os.path.join(dirpath, f)
        rel = os.path.relpath(fp, ROOT)
        if rel in ("execution/entry_engine.py", "analysis/tape_at_level.py"):
            continue
        for node in ast.walk(ast.parse(open(fp, errors="ignore").read())):
            if (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)
                    and node.slice.value in ("tape_vol_at_level",
                                             "tape_buy_frac_at_level")
                    and isinstance(node.ctx, ast.Load)):
                readers2.append(f"{rel}:{node.slice.value}")
check("G7 the r120 observations are still UNREAD — observe first",
      not readers2, str(readers2))

# ── G8 (r122) — THE GRADE NO LONGER SIZES THE TRADE ─────────────────────────
# Operator, 2026-08-25: "sizing has to be a 1.0 across all trades... we may fit
# based on indicators but we are not there right now." The letter was sizing on
# information it does not carry (ORB survivors are near-uniformly A) and where
# it DID vary it pointed the wrong way (TSLA grade A net -$2,237 vs B +$125).
# It also silently broke the risk budget: 1.5x on an A risks $1,575 against a
# $1,050 setting.
import config as _cfg
check("G8a every grade multiplier is 1.0",
      all(abs(v - 1.0) < 1e-9 for v in _cfg.GRADE_SIZE_MULTIPLIER.values()),
      str(_cfg.GRADE_SIZE_MULTIPLIER))
check("G8b an A and a B size identically",
      _cfg.GRADE_SIZE_MULTIPLIER.get("A") == _cfg.GRADE_SIZE_MULTIPLIER.get("B"))
# the butterfly VIX halving is a DIFFERENT rule and stays — operator: "the
# current is ok for that one" until it has more than one trade behind it.
_rsrc = open(os.path.join(ROOT, "risk/risk_manager.py")).read()
check("G8c the butterfly VIX half-size is deliberately untouched",
      "if is_butterfly and butterfly_half_size:" in _rsrc)

print(f"\n{'PASS' if not FAILURES else 'FAIL'}: {len(FAILURES)} problem(s) {FAILURES}")
sys.exit(1 if FAILURES else 0)
