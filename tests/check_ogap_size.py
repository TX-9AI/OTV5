#!/usr/bin/env python3
"""tests/check_ogap_size.py — v5.0
v5.0  2026-11-16  OTV5 r131 (OGAP.2) — OGAP SIZES ON THE RAMP MIN (RISK_PER_TRADE_USD, OT_RISK_USD), NOT A FLAT $500.
      The operator, 2026-11-16: "Do me a favor and size the OGAP to whatever the ramp minimum (risk per trade) is set at
      instead of a flat $500. That $500 is Park's (my friend) preferred position size. I like 1050 for most trades."
      EXECUTED: each case runs in its own child interpreter with its own OT_RISK_USD (config reads it at import), and the
      funnel cases drive the REAL main._execute_entry_signal with the real RiskManager and a spy entry engine.

S1   OT_RISK_USD=1050: contracts_for(3.21 / 6.00 / 10.50 / 11.00) = 3 / 1 / 1 / 0 (floor(1050 / (ask x 100)))
S2   OT_RISK_USD=1050: the plan end to end (strategy.ogap) at ask 3.21 -> a TAKE signal with ogap_contracts 3; ask 6.00
     -> 1; ask 11.00 -> no signal (ogap_ask_band, the feasibility gate follows the ramp MIN)
S3   OT_RISK_USD=1050: the real funnel sizes an OGAP signal on the ASK with the ramp MIN: ask 3.21 -> 3; mark 3.45 /
     ask 3.55 -> 2 (the ask, not the mark: 1050/345 would be 3)
S4   OT_RISK_USD unset: OGAP follows RISK_PER_TRADE_USD's default (contracts_for(a) == floor(default / (a x 100)) at
     0.50 / 1.00 / 2.27, and the default is the one config.py declares for OT_RISK_USD)
S5   no separate knob: config has no OGAP_BUDGET_USD, no module reads one, and no OT_OGAP* env key is read
S6   every other strategy is untouched: at OT_RISK_USD=1050 the real funnel sizes PARK, RunawayContinuation and
     LiquidityHunt (each carrying a stray ogap_ask 1.50, which only OGAP may use: on it each would buy 7) on the MARK with the box's risk, exactly
     as r130 did (mark 2.45 -> 4 each), and size_for without budget_usd is unchanged
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
"""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  [{detail}]"))
    if not ok:
        FAILED.append(name.split()[0])


# ── the child: one OT_RISK_USD, every measurement, printed as JSON ──
def _child():
    sys.path.insert(0, ROOT)
    out = {}
    try:
        import config
        from strategy import ogap_plan as OP
        from strategy.ogap import Ogap
        import main as MN
        from strategy.base_strategy import OptionsSignal
    except Exception as exc:                                    # noqa: BLE001
        print(json.dumps({"import_error": f"{type(exc).__name__}: {exc}"}))
        return 0
    out["risk"] = float(config.RISK_PER_TRADE_USD)
    out["has_ogap_budget"] = hasattr(config, "OGAP_BUDGET_USD")
    out["cf"] = {str(a): OP.contracts_for(a) for a in (0.50, 1.00, 2.27, 3.21, 6.00, 10.50, 11.00)}

    # the plan end to end on the tests/check_ogap fixture (QQQ 11-05 at the fill minute)
    from datetime import date

    class K:
        def __init__(self, strike, bid, ask, side, expiry):
            self.strike, self.bid, self.ask, self.delta = float(strike), bid, ask, 0.5 if side == "C" else -0.5
            self.expiry, self.symbol, self.streamer_symbol = expiry, f"QQQ{side}{strike}", f".QQQ{side}{strike}"

    class Chain:
        def __init__(self, expiry, center, bid, ask):
            self.expiry = expiry
            self.calls = [K(s, bid, ask, "C", expiry) for s in range(int(center) - 5, int(center) + 6)]
            self.puts = [K(s, bid, ask, "P", expiry) for s in range(int(center) - 5, int(center) + 6)]

    fx = json.load(open(os.path.join(ROOT, "tests", "fixtures", "ogap", "replay5.json")))
    d = "2026-11-05"
    bars = {int(k): tuple(v) for k, v in fx[d]["bars"].items()}
    fill = fx[d]["expect"]["fill"]
    spot = bars[fill][0]
    spec = Ogap()
    plan = {}
    for bid, ask in ((3.18, 3.21), (5.97, 6.00), (10.95, 11.00)):
        s = spec.generate_signal(price_now=spot, now_et=OP.hhmm(fill), chain=Chain(d, round(spot), bid, ask),
                                 day=date.fromisoformat(d), symbol="QQQ", bars=bars, prior_close=fx[d]["prior_close"])
        plan[str(ask)] = None if s is None else int(getattr(s, "ogap_contracts", -1))
    out["plan"] = plan

    # the real funnel
    class _Spy:
        def __init__(self):
            self.sz = []

        def enter(self, signal=None, sizing=None, **kw):
            self.sz.append((getattr(signal, "strategy_name", "?"), getattr(sizing, "contracts", None)))
            return None

    class _State:
        paper_trading = True

    def funnel(name, mark, ask):
        sg = OptionsSignal(strategy_name=name, setup_type="ogap_long", direction="long", option_side="call",
                           underlying_entry=600.0, underlying_stop=0.0, strike=600.0, entry_premium=mark,
                           stop_loss_pct=1.0)
        sg.ogap_ask = ask
        spy = _Spy()
        _ge = MN.get_entry_engine
        MN.get_entry_engine = lambda *a, **kw: spy
        try:
            MN._execute_entry_signal(sg, {"price": 600.0, "macro": type("M", (), {"butterfly_half_size": False})()},
                                     None, _State(), None, additive=True)
        finally:
            MN.get_entry_engine = _ge
        return [list(x) for x in spy.sz]

    out["funnel"] = {
        "OGAP@3.21": funnel("OGAP", 3.15, 3.21),
        "OGAP@3.55": funnel("OGAP", 3.45, 3.55),
        "PARK": funnel("PARK", 2.45, 1.50),
        "RunawayContinuation": funnel("RunawayContinuation", 2.45, 1.50),
        "LiquidityHunt": funnel("LiquidityHunt", 2.45, 1.50),
    }
    import risk.risk_manager as RM
    rm = RM.RiskManager()
    out["size_for_plain"] = rm.size_for("long_debit", premium=2.45, grade="UNGRADED").contracts
    out["box_risk"] = float(rm.risk_per_trade)
    print("JSON:" + json.dumps(out))
    return 0


def _run(risk):
    env = {k: v for k, v in os.environ.items() if not k.startswith("OT_RISK_USD")}
    td = tempfile.mkdtemp(prefix="check_ogap_size_")
    env.update(OT_TRADES_DB=os.path.join(td, "t.db"), OT_DERIVED_DB=os.path.join(td, "d.db"),
               OT_FEED_DB=os.path.join(td, "f.db"), OT_LOG_FILE=os.path.join(td, "bot.log"),
               OT_SIGNAL_JOURNAL_DIR=os.path.join(td, "sj"), OT_COUNTERFACTUAL_DIR=os.path.join(td, "cf"),
               OT_INSTRUMENT="QQQ")
    if risk is not None:
        env["OT_RISK_USD"] = risk
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--child"], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=240)
    import shutil
    if td.startswith(tempfile.gettempdir()) and "check_ogap_size_" in td:
        shutil.rmtree(td, ignore_errors=True)
    for line in r.stdout.splitlines():
        if line.startswith("JSON:"):
            return json.loads(line[5:])
        if line.startswith("{"):
            return json.loads(line)
    return {"child_failed": (r.stdout[-800:] + r.stderr[-1500:])}


def main():
    hi = _run("1050")
    if "import_error" in hi:
        print(f"NOT RUN — imports failed: {hi['import_error']}")
        return 2
    lo = _run(None)
    for o in (hi, lo):
        if "child_failed" in o:
            print("RED — the child did not report:\n" + o["child_failed"])
            return 1

    cf = hi["cf"]
    check("S1 OT_RISK_USD=1050: contracts_for 3.21 / 6.00 / 10.50 / 11.00 -> 3 / 1 / 1 / 0",
          hi["risk"] == 1050.0 and [cf["3.21"], cf["6.0"], cf["10.5"], cf["11.0"]] == [3, 1, 1, 0], f"{hi['risk']} {cf}")
    check("S2 OT_RISK_USD=1050: the plan at ask 3.21 -> 3 contracts, 6.00 -> 1, 11.00 -> no signal (ogap_ask_band)",
          hi["plan"] == {"3.21": 3, "6.0": 1, "11.0": None}, f"{hi['plan']}")
    f = hi["funnel"]
    check("S3 OT_RISK_USD=1050: the real funnel sizes OGAP on the ask with the ramp MIN: ask 3.21 -> 3; mark 3.45 / "
          "ask 3.55 -> 2", f["OGAP@3.21"] == [["OGAP", 3]] and f["OGAP@3.55"] == [["OGAP", 2]], f"{f}")

    src = open(os.path.join(ROOT, "config.py"), encoding="utf-8").read()
    m = re.search(r'^RISK_PER_TRADE_USD\s*=\s*float\(os\.environ\.get\("OT_RISK_USD",\s*"([0-9.]+)"\)\)', src, re.M)
    dflt = float(m.group(1)) if m else None
    lcf = lo["cf"]
    exp = {a: int(dflt // round(float(a) * 100)) if dflt else None for a in ("0.5", "1.0", "2.27")}
    check("S4 OT_RISK_USD unset: OGAP follows RISK_PER_TRADE_USD's default ($%s): 0.50 / 1.00 / 2.27 -> %s" % (
          dflt, [exp[a] for a in ("0.5", "1.0", "2.27")]),
          dflt is not None and lo["risk"] == dflt and all(lcf[a] == exp[a] for a in exp), f"{lo['risk']} {lcf} {exp}")

    readers = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [x for x in dn if x not in (".git", "venv", "tests", "docs", "__pycache__", "data", "logs")]
        for n in fn:
            if not n.endswith(".py"):
                continue
            path = os.path.join(dp, n)
            try:
                tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
            except SyntaxError:
                continue
            for nd in ast.walk(tree):
                hit = ((isinstance(nd, ast.Name) and nd.id == "OGAP_BUDGET_USD")
                       or (isinstance(nd, ast.Attribute) and nd.attr == "OGAP_BUDGET_USD")
                       or (isinstance(nd, ast.alias) and nd.name == "OGAP_BUDGET_USD")
                       or (isinstance(nd, ast.Constant) and isinstance(nd.value, str)
                           and re.fullmatch(r"OT_OGAP\w*", nd.value)))
                if hit:
                    readers.append(f"{os.path.relpath(path, ROOT)}:{getattr(nd, 'lineno', '?')}")
    check("S5 no separate knob: config has no OGAP_BUDGET_USD, no code reads one, no OT_OGAP* env key",
          not hi["has_ogap_budget"] and not lo["has_ogap_budget"] and not readers, f"{readers}")

    others = {k: f[k] for k in ("PARK", "RunawayContinuation", "LiquidityHunt")}
    check("S6 PARK / RunawayContinuation / LiquidityHunt at $1050: sized on the MARK with the box's risk, a stray "
          "ogap_ask ignored (2.45 -> 4 each, as r130); size_for without budget_usd -> 4",
          all(v == [[k, 4]] for k, v in others.items()) and hi["size_for_plain"] == 4 and hi["box_risk"] == 1050.0,
          f"{others} plain={hi['size_for_plain']} risk={hi['box_risk']}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 6 checks")
    return 0


if __name__ == "__main__":
    if "--child" in sys.argv:
        sys.exit(_child())
    sys.exit(main())
