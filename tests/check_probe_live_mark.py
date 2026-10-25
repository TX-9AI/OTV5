#!/usr/bin/env python3
"""
tests/check_probe_live_mark.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.1  2026-10-20  OTV4TEST r310 (F4.2 mirror of otv4 r496) — _get_option_mark now prices through ONE
      get_market_data_by_type(options=[...]) call; the fake broker answers it (as otv4 r496's
      check_live_mark_fallback v1.1 did) and the spy counts it. Every expected value unchanged.
v1.0  2026-10-20  OTV4TEST r308 (PRB.3) — THE LIVE-MARK PROBE ONLY READS, AND IT ASKS THE BOT'S OWN FUNCTION.

  The operator, 2026-10-20 10:53 ET: "Concur" (a read-only LIVE.1 F4 probe, run after the close).
  tools/probe_live_mark.py runs with the bot's broker credentials, so what it CANNOT do is the point:
  L1  it imports nothing from tastytrade.order / tastytrade.account and makes no order, account or balance call
      (place_order, replace_order, delete_order, cancel_order, get_balances, get_positions, Account.get ...)
  L2  it prices through the REAL PositionManager._get_option_mark - it calls that attribute and defines no
      _get_option_mark of its own (a copy would prove the copy, not the bot)
  L3  it is on run_with_bot_env's PROBES list (so it runs only committed and unedited)
  L4  DRIVEN, offline: main() over a fake chain and a fake REST quote prices all six contracts at the mid, through
      the real _get_option_mark (a spy on get_market_data and get_market_data_by_type sees every call), and exits 0
  L5  DRIVEN: a REST call that raises -> every contract reads None, the RESULT line says 0 of 6, exit 1
  L6  DRIVEN: on SPX only SPXW contracts are probed (his 10-04 ruling: never the AM expiry)
No network. Run: python3 tests/check_probe_live_mark.py
"""
import ast
import contextlib
import io
import os
import sys
import importlib.util
from datetime import date
from types import SimpleNamespace

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED = []
_P = os.path.join(_root, "tools", "probe_live_mark.py")


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _load():
    s = importlib.util.spec_from_file_location("_plm", _P)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _drive(m, sym, md_fn, roots=("QQQ",)):
    """Run the real main() over a fake chain; md_fn answers tastytrade.market_data.get_market_data
    and (r310) get_market_data_by_type, one row per asked symbol."""
    import tastytrade.market_data as tmd
    from tastytrade.instruments import OptionType
    calls = []

    def spy(session, symbol, itype):
        calls.append(symbol)
        return md_fn(symbol)

    def spy_batch(session, options=None, **kw):             # r310: the bot's batch call
        rows = []
        for symbol in options or []:
            calls.append(symbol)
            md = md_fn(symbol)
            rows.append(SimpleNamespace(symbol=symbol, **vars(md)))
        return rows
    opts = []
    for root in roots:
        for k, kind in enumerate((OptionType.PUT, OptionType.CALL)):
            for i in range(7):
                opts.append(SimpleNamespace(symbol=f"{root}_{kind.value}_{i}", option_type=kind,
                                            strike_price=100 + i, root_symbol=root))
    _orig, _orig_b = tmd.get_market_data, tmd.get_market_data_by_type
    tmd.get_market_data, tmd.get_market_data_by_type = spy, spy_batch
    saved = (m.SYM, m.get_client, m.get_option_chain, m.get_market_data, m.sdk_result)
    m.SYM, m.get_client = sym, (lambda: SimpleNamespace())
    m.get_option_chain = lambda client, s: {date.today(): opts}
    m.get_market_data = spy
    m.sdk_result = lambda x: x
    import execution.position_manager as pmod
    _sr = pmod.sdk_result
    pmod.sdk_result = lambda x: x
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = m.main()
    finally:
        tmd.get_market_data, tmd.get_market_data_by_type = _orig, _orig_b
        pmod.sdk_result = _sr
        m.SYM, m.get_client, m.get_option_chain, m.get_market_data, m.sdk_result = saved
    return rc, buf.getvalue(), calls


def main():
    try:
        src = open(_P, encoding="utf-8").read()
    except OSError as exc:
        check("L0 tools/probe_live_mark.py exists", False, str(exc))
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    tree = ast.parse(src)

    # L1 - no order / account module, no order / account / balance call
    bad_mods = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                and (n.module or "").split(".")[:2] in (["tastytrade", "order"], ["tastytrade", "account"])]
    bad_mods += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
                 if a.name.startswith(("tastytrade.order", "tastytrade.account"))]
    forbid = {"place_order", "replace_order", "delete_order", "cancel_order", "place_complex_order",
              "get_balances", "get_positions", "get_live_orders", "get_order_history", "Account"}
    bad_calls = sorted({(n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", ""))
                        for n in ast.walk(tree) if isinstance(n, ast.Call)}
                       & forbid)
    bad_names = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} & forbid)
    check("L1 no tastytrade.order / tastytrade.account import and no order, account or balance call",
          not bad_mods and not bad_calls and not bad_names, f"modules={bad_mods} calls={bad_calls} names={bad_names}")

    # L2 - the real method
    calls_real = any(isinstance(n, ast.Attribute) and n.attr == "_get_option_mark"
                     and isinstance(n.value, ast.Name) and n.value.id == "PositionManager" for n in ast.walk(tree))
    own = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_get_option_mark"]
    check("L2 prices through PositionManager._get_option_mark and defines no copy of it",
          calls_real and not own, f"calls_real={calls_real} own={own}")

    # L3 - the wrapper's list
    rw = open(os.path.join(_root, "tools", "run_with_bot_env.py"), encoding="utf-8").read()
    check("L3 it is on run_with_bot_env's PROBES list",
          '"probe_live_mark.py": "tools/probe_live_mark.py"' in rw, "not listed")

    m = _load()
    # L4 - priced at the mid through the real function
    rc, out, calls = _drive(m, "QQQ", lambda s: SimpleNamespace(bid=1.00, ask=1.20, mark=9.0, last=9.0))
    priced = out.count("mark=   1.1000")
    check("L4 DRIVEN: six contracts priced at the mid through the real _get_option_mark, exit 0",
          rc == 0 and priced == 6 and "RESULT: 6 of 6 priced" in out and len(calls) == 12,
          f"rc={rc} priced={priced} rest_calls={len(calls)} out={out[-300:]!r}")

    # L5 - a refused REST call reads None everywhere
    def boom(s):
        raise RuntimeError("no such endpoint")
    rc, out, _ = _drive(m, "QQQ", boom)
    check("L5 DRIVEN: a REST call that raises -> every contract None, 0 of 6, exit 1",
          rc == 1 and out.count("mark=     None") == 6 and "RESULT: 0 of 6 priced" in out,
          f"rc={rc} out={out[-300:]!r}")

    # L6 - SPXW only on SPX
    rc, out, calls = _drive(m, "SPX", lambda s: SimpleNamespace(bid=3.0, ask=3.2, mark=0, last=0),
                            roots=("SPX", "SPXW"))
    check("L6 DRIVEN: on SPX only SPXW contracts are probed",
          rc == 0 and calls and all(c.startswith("SPXW_") for c in calls), f"calls={calls}")

    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — the live-mark probe only reads, through the bot's own function")
    return 0


if __name__ == "__main__":
    sys.exit(main())
