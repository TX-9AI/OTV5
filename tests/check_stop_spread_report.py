#!/usr/bin/env python3
"""
tests/check_stop_spread_report.py  v1.0

The stop-vs-spread ratio is RECORDED by the sweep and TCS, and the Saturday report
counts every case the way the rule means it.

v1.0  2026-09-24  OTV4TEST r129. Operator: "Do we have a stop vs spread report? If
      not, we can build that & review it on Saturdays", and "Both" (flies and
      verticals). BORN RED on 8745d11 (r128): SweepPlan/TCSPlan Candidates have no
      `sv_ratio`, and tests/stop_spread_report.py does not exist.

WHAT IS PINNED, AND WHY EACH PART EXISTS
  S1  SweepPlan._structure on a sellable stub chain sets sv_ratio to exactly
      search_wing's stop_dist / the short's bid-ask — the two numbers
      criteria.stop_survivable compares — and >= STOP_VS_SPREAD_MIN.
  S2  TCSPlan._structure: a sellable chain records the chosen wing's ratio; the
      SAME chain with a wide short quote is refused under "stop_vs_spread" AND
      carries the best refused ratio (below the minimum), so t.refuse writes it.
  S3  prepare() writes those checks: the sweep records ("stop_vs_spread",
      chosen.sv_ratio, True) and TCS records the ratio True on a pass and False
      before a stop_vs_spread refusal. AST-scoped to the prepare bodies.
  R1-R6  the report, EXECUTED on a planted store:
      R1 a fly tick with NO ratio is "not reached", never a failure — the fly
         tests R before survivability (gex_pin_butterfly.py:831-834); the first
         cut of this report counted 229 GEXPin R-refusals against the spread.
      R2 a fly ratio below the minimum on a tick DECLINEd at wing_search is a
         BINDING refusal; the same ratio on a tick declined elsewhere is a
         failure but NOT binding.
      R3 a vertical FAIL with no ratio (the sweep's search_wing refusal) counts
         as failed and binding when the tick declined at stop_vs_spread.
      R4 pre-r129 TCS rows (DOLLARS under the ratio's name) are excluded from
         ratio statistics and flagged.
      R5 the minimum is read from criteria.STOP_VS_SPREAD_MIN, not restated.
      R6 the report opens its store READ-ONLY (mode=ro).

Run:  python3 tests/check_stop_spread_report.py
"""
from __future__ import annotations

import ast
import io
import os
import sqlite3
import sys
import tempfile
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import glob as _glob                                             # r106 venv bootstrap
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

PROBLEMS: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


def _fn(tree, name, cls):
    for n in ast.walk(tree):
        if isinstance(n, ast.ClassDef) and n.name == cls:
            return next((f for f in n.body if isinstance(f, ast.FunctionDef) and f.name == name), None)
    return None


def main() -> int:
    print("=" * 68)
    print("STOP VS SPREAD: recorded by sweep + TCS, counted right by the report")
    print("=" * 68)
    from types import SimpleNamespace as NS
    from strategy.criteria import STOP_VS_SPREAD_MIN as MN
    import strategy.credit_vertical as cv
    from strategy import sweep_plan as SP
    from strategy import tcs_plan as TP

    # ── S1 the sweep ─────────────────────────────────────────────────────
    def sweep_chain(ask):
        return NS(calls=[], puts=[
            NS(strike=198.0, bid=2.40, ask=ask, mark=round((2.40 + ask) / 2, 3)),
            NS(strike=197.0, bid=0.40, ask=0.42, mark=0.41),
            NS(strike=196.0, bid=0.10, ask=0.12, mark=0.11),
            NS(strike=195.0, bid=0.03, ask=0.05, mark=0.04),
            NS(strike=193.0, bid=0.01, ask=0.02, mark=0.015)])
    lvl = {"level_id": "s1", "price": 198.0, "kind": "support", "provenance": "PDL"}
    if "sv_ratio" not in getattr(SP.Candidate, "__slots__", ()):
        check("S1 SweepPlan.Candidate carries sv_ratio", False, "no sv_ratio slot")
    else:
        ch = sweep_chain(2.44)
        c = SP.SweepPlan()._structure(SP.Candidate(lvl), ch)
        short = ch.puts[0]
        w = cv.search_wing(ch.puts, short, "put", SP.R_FLOOR, r_floor_stop=SP.R_FLOOR_STOP)
        want = round(float(w.stop_dist) / (short.ask - short.bid), 4) if w.stop_dist else None
        check("S1 the sweep records sv_ratio = search_wing stop_dist / short bid-ask",
              c.sellable and want is not None and c.sv_ratio == want and c.sv_ratio >= MN,
              f"sellable={c.sellable} sv_ratio={c.sv_ratio} want={want} min={MN}")

    # ── S2 TCS ───────────────────────────────────────────────────────────
    def tcs_chain(ask):
        return NS(calls=[], puts=[
            NS(strike=198.0, bid=2.40, ask=ask, mark=round((2.40 + ask) / 2, 3), delta=-0.5),
            NS(strike=197.0, bid=1.60, ask=1.62, mark=1.61, delta=-0.4),
            NS(strike=196.0, bid=1.00, ask=1.02, mark=1.01, delta=-0.3),
            NS(strike=194.0, bid=0.38, ask=0.40, mark=0.39, delta=-0.15)])
    tl = {"level_id": "s2", "price": 198.0, "kind": "resistance", "provenance": "PDH"}
    if "sv_ratio" not in getattr(TP.Candidate, "__slots__", ()):
        check("S2 TCSPlan.Candidate carries sv_ratio", False, "no sv_ratio slot")
    else:
        ok_c = TP.TCSPlan()._structure(TP.Candidate(tl), tcs_chain(2.44))
        exp_ok = round(ok_c.stop_dist / 0.04, 4) if ok_c.stop_dist else None
        check("S2 TCS records the chosen wing's ratio (stop / short bid-ask) on a pass",
              ok_c.sellable and ok_c.sv_ratio is not None and exp_ok is not None
              and abs(ok_c.sv_ratio - exp_ok) < 1e-3 and ok_c.sv_ratio >= MN,
              f"sellable={ok_c.sellable} why={ok_c.why!r} sv_ratio={ok_c.sv_ratio} want={exp_ok}")
        bad = TP.TCSPlan()._structure(TP.Candidate(tl), tcs_chain(2.90))
        check("S2 the same chain on a wide short quote is refused as stop_vs_spread "
              "and carries the best refused ratio (below the minimum)",
              (not bad.sellable) and bad.why_key == "stop_vs_spread"
              and bad.sv_ratio is not None and 0 < bad.sv_ratio < MN,
              f"sellable={bad.sellable} key={bad.why_key!r} sv_ratio={bad.sv_ratio}")

    # ── S3 prepare() writes them ─────────────────────────────────────────
    def calls_in(fn):
        out = []
        for n in ast.walk(fn or ast.parse("")):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "check"
                    and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == "stop_vs_spread"):
                out.append(ast.unparse(n))
        return out
    sp_calls = calls_in(_fn(ast.parse(open(SP.__file__).read()), "prepare", "SweepPlan"))
    tp_calls = calls_in(_fn(ast.parse(open(TP.__file__).read()), "prepare", "TCSPlan"))
    check("S3 SweepPlan.prepare records stop_vs_spread with the chosen ratio, True",
          any("chosen.sv_ratio" in c and c.rstrip(")").endswith("True") for c in sp_calls), f"{sp_calls}")
    check("S3 TCSPlan.prepare records the ratio True on a pass and False before a refusal",
          any("cand.sv_ratio" in c and c.rstrip(")").endswith("True") for c in tp_calls)
          and any("cand.sv_ratio" in c and c.rstrip(")").endswith("False") for c in tp_calls), f"{tp_calls}")

    # ── R1-R6 the report on a planted store ──────────────────────────────
    rp_path = os.path.join(ROOT, "tests", "stop_spread_report.py")
    if not os.path.exists(rp_path):
        check("R0 tests/stop_spread_report.py exists", False, "missing")
    else:
        sys.path.insert(0, os.path.join(ROOT, "tests"))
        import stop_spread_report as R
        src = open(rp_path).read()
        check("R5 the minimum comes from criteria.STOP_VS_SPREAD_MIN",
              "from strategy.criteria import STOP_VS_SPREAD_MIN" in src and R._min_ratio() == MN,
              f"report min {R._min_ratio()} vs criteria {MN}")
        check("R6 the report opens its store read-only", "mode=ro" in src)
        with tempfile.TemporaryDirectory(dir="/var/tmp" if os.path.isdir("/var/tmp") else None) as td:
            db = os.path.join(td, "d.db")
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE plan_check (ts_epoch REAL, symbol TEXT, strategy TEXT, check_name TEXT,"
                        " value REAL, verdict TEXT, tick_id INTEGER, direction TEXT)")
            con.execute("CREATE TABLE plan_tick (ts_epoch REAL, symbol TEXT, strategy TEXT, verdict TEXT,"
                        " reason TEXT, trigger_price REAL, invalidation REAL, underlying REAL,"
                        " dist_to_trigger REAL, r_now REAL, direction TEXT, tick_id INTEGER)")
            T = 1790260000.0   # 2026-09-24 ET
            rows = [  # strategy, value, check verdict, tick verdict, reason
                ("GEXPinButterfly", None, "n/a", "DECLINE", "wing_search: no wing (R)"),     # not reached
                ("GEXPinButterfly", 1.5, "n/a", "DECLINE", "wing_search: too narrow"),       # binding
                ("GEXPinButterfly", 1.4, "n/a", "DECLINE", "entry_window: late"),            # failed, not binding
                ("GEXPinButterfly", 3.0, "n/a", "HOLD", "prepared"),                         # pass
                ("SweepCreditSpread", None, "FAIL", "DECLINE", "stop_vs_spread: narrowest"),  # vertical binding
                ("SweepCreditSpread", 4.0, "PASS", "HOLD", "prepared"),
                ("TrendCreditSpread", 0.30, "PASS", "HOLD", "prepared"),                     # pre-r129 dollars
            ]
            for i, (s, v, vk, tv, rs) in enumerate(rows):
                ts = T + i * 60 - (86400 * 3 if s == "TrendCreditSpread" else 0)
                con.execute("INSERT INTO plan_check VALUES (?,?,?,?,?,?,?,?)", (ts, "QQQ", s, "stop_vs_spread", v, vk, i, ""))
                con.execute("INSERT INTO plan_tick VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (ts, "QQQ", s, tv, rs, None, None, None, None, None, "", i))
            con.commit(); con.close()
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = R.main(["--derived", db, "--all-history"])
            out = buf.getvalue()

        def block(name):
            if name not in out:
                return ""
            b = out.split(name, 1)[1]
            return b.split("\n  ", 1)[0] if False else b.split("\n\n", 1)[0]

        def val(b, label):
            for line in b.splitlines():
                if line.strip().startswith(label):
                    return int(line.strip()[len(label):].split()[0])
            return None
        g = block("GEXPinButterfly")
        check("R1 a fly tick with no ratio is 'not reached', never a failure",
              val(g, "rule not reached") == 1 and val(g, "rule applied") == 3, g[:300])
        check("R2 a fly ratio under the minimum is BINDING only when declined at wing_search",
              val(g, "failed the rule") == 2 and val(g, "BINDING refusals") == 1, g[:400])
        sw = block("SweepCreditSpread")
        check("R3 a vertical FAIL with no ratio counts as failed and binding",
              val(sw, "failed the rule") == 1 and val(sw, "BINDING refusals") == 1, sw[:400])
        tc = block("TrendCreditSpread")
        check("R4 pre-r129 TCS dollar rows are excluded from ratios and flagged",
              "DOLLARS" in tc and "ratio  p10" not in tc, tc[:400])
        check("R6b the planted run exits 0", rc == 0, f"rc={rc}")

    print("=" * 68)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        return 1
    print("  ALL GREEN - the ratio is recorded and the report counts it as the rule means")
    return 0


if __name__ == "__main__":
    sys.exit(main())
