#!/usr/bin/env python3
"""
tests/check_adx_stamp.py  v5.0
v5.0  2026-10-25  (MEAS.4) — EVERY ENTRY CARRIES THE ADX IT WAS TAKEN AT. Only ORBStrategy set
      signal.adx_at_signal (from MarketState.adx), so adx_at_entry was 0.0 on every non-ORB row
      (27 of 34 at MEAS.4's count). main._stamp_adx stamps it beside _stamp_vix, from the same source.

  Drives the REAL main._stamp_adx and the REAL main.assemble_market_state:
  A1  a signal with no ADX gets ctx["trend"].primary_adx
  A2  UNCHANGED: an ADX the strategy set itself (ORB) is kept
  A3  no trend on ctx, no ctx, or a zero ADX: the field stays 0.0 and nothing raises
  A4  SAME SOURCE AS ORB: the stamped value equals assemble_market_state(ctx).adx, the MarketState field
      ORB's own stamp reads (strategy/orb_strategy.py: signal.adx_at_signal = ms.adx)
  A5  HOP 0: BOTH executors call _stamp_adx(signal, ctx) as the statement right after _stamp_vix(signal, ctx)
      (parsed, the check_vix_stamp V4 pattern; A1-A4 are the driven half)

Born red on ffe10bf at A1 A2 A3 A4 A5 (no _stamp_adx).
Run:  python3 tests/check_adx_stamp.py   (exit 0 green, 1 red)
"""
import ast
import glob as _glob
import os
import sys
import tempfile
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_adx_stamp_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    import main as M
    stamp = getattr(M, "_stamp_adx", None)
    trend = types.SimpleNamespace(primary_adx=27.5, overall_direction="BULLISH")

    def sig(v=0.0):
        return types.SimpleNamespace(adx_at_signal=v, strategy_name="Breakout")

    def run(s, ctx):
        if stamp is None:
            return "ABSENT"
        try:
            stamp(s, ctx)
            return s.adx_at_signal
        except Exception as exc:                              # noqa: BLE001
            return f"{type(exc).__name__}: {exc}"

    got = run(sig(), {"trend": trend})
    check("A1 a signal with no ADX is stamped with ctx['trend'].primary_adx (27.5)", got == 27.5, f"got {got!r}")
    got = run(sig(31.0), {"trend": trend})
    check("A2 UNCHANGED: an ADX the strategy set (31.0) is kept", got == 31.0, f"got {got!r}")
    g = (run(sig(), {}), run(sig(), None), run(sig(), {"trend": types.SimpleNamespace(primary_adx=0.0)}),
         run(sig(), {"trend": types.SimpleNamespace(primary_adx=None)}))
    check("A3 no trend, no ctx, a zero or a None ADX: stays 0.0 and nothing raises",
          g == (0.0, 0.0, 0.0, 0.0), f"got {g!r}")

    # A4 — the same number ORB records: MarketState.adx off the same ctx
    try:
        ctx = {"trend": trend, "vol": None, "structure": None, "macro": None}
        ms = M.assemble_market_state(ctx, "check", types.SimpleNamespace())
        s = sig()
        got = run(s, ctx)
        check("A4 the stamp equals assemble_market_state(ctx).adx (ORB's source)",
              got == float(ms.adx) == 27.5, f"stamp={got!r} ms.adx={getattr(ms, 'adx', None)!r}")
    except Exception as exc:                                  # noqa: BLE001
        check("A4 (did not run)", False, f"{type(exc).__name__}: {exc}")

    # A5 — both executors stamp ADX right after the VIX stamp
    src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    pairs = {}
    for n in ast.parse(src).body:
        if isinstance(n, ast.FunctionDef) and n.name in ("_execute_entry_signal", "_execute_condor_leg"):
            body = n.body[1:] if (isinstance(n.body[0], ast.Expr)
                                  and isinstance(getattr(n.body[0], "value", None), ast.Constant)) else n.body
            pairs[n.name] = tuple(ast.unparse(b) for b in body[:2])
    want = ("_stamp_vix(signal, ctx)", "_stamp_adx(signal, ctx)")
    check("A5 both executors call _stamp_adx(signal, ctx) right after _stamp_vix(signal, ctx)",
          pairs == {"_execute_entry_signal": want, "_execute_condor_leg": want}, str(pairs))

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — every entry is stamped with the ADX it was taken at")
    return 0


if __name__ == "__main__":
    sys.exit(main())
