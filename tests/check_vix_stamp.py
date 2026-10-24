#!/usr/bin/env python3
"""
tests/check_vix_stamp.py  v1.0
v1.0  2026-10-03  OTV4TEST r200 (AUD.8) — EVERY ENTRY CARRIES THE VIX IT WAS TAKEN AT.

  Found by the 10-03 audit: only ORBStrategy and VOLT set signal.vix_at_signal,
  and both are off the roster, so vix_at_entry was 0.0 on 141 of 194 closed
  trades since 09-21 (Breakout, Runaway, Hunt, the flies, the credit spreads).

  Drives the REAL main._stamp_vix and both REAL record builders' input:
  V1  a signal with no VIX gets the macro snapshot's VIX
  V2  UNCHANGED: a VIX the strategy set itself is kept
  V3  no macro on ctx, or a zero VIX: the field stays 0.0 and nothing raises
  V4  HOP 0: BOTH executors call _stamp_vix BEFORE anything else reads the
      signal - _execute_entry_signal and _execute_condor_leg (parsed, the
      check_chain_ordering pattern; V1-V3 are the driven half)
  V5  DRIVEN END TO END: the stamped signal's value is what the real
      EntryEngine record carries as vix_at_entry (paper)

Run:  python3 tests/check_vix_stamp.py   (exit 0 green, 1 red)
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
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_vix_stamp_")
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
    stamp = getattr(M, "_stamp_vix", None)
    macro = types.SimpleNamespace(vix=17.35, is_fed_day=False)

    def sig(v=0.0):
        return types.SimpleNamespace(vix_at_signal=v, strategy_name="Breakout")

    def run(s, ctx):
        if stamp is None:
            return "ABSENT"
        try:
            stamp(s, ctx)
            return s.vix_at_signal
        except Exception as exc:                              # noqa: BLE001
            return f"{type(exc).__name__}: {exc}"

    got = run(sig(), {"macro": macro})
    check("V1 a signal with no VIX is stamped with the macro snapshot's (17.35)", got == 17.35, f"got {got!r}")
    got = run(sig(15.0), {"macro": macro})
    check("V2 UNCHANGED: a VIX the strategy set (15.0) is kept", got == 15.0, f"got {got!r}")
    g1, g2, g3 = run(sig(), {}), run(sig(), None), run(sig(), {"macro": types.SimpleNamespace(vix=0.0)})
    check("V3 no macro, no ctx, or a zero VIX: stays 0.0 and nothing raises",
          (g1, g2, g3) == (0.0, 0.0, 0.0), f"got {(g1, g2, g3)!r}")

    # V4 — both executors call it before any other statement reads the signal
    src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    firsts = {}
    for n in ast.parse(src).body:
        if isinstance(n, ast.FunctionDef) and n.name in ("_execute_entry_signal", "_execute_condor_leg"):
            body = n.body[1:] if (isinstance(n.body[0], ast.Expr)
                                  and isinstance(getattr(n.body[0], "value", None), ast.Constant)) else n.body
            firsts[n.name] = ast.unparse(body[0]) if body else ""
    check("V4 both executors call _stamp_vix(signal, ctx) as their FIRST statement",
          firsts == {"_execute_entry_signal": "_stamp_vix(signal, ctx)",
                     "_execute_condor_leg": "_stamp_vix(signal, ctx)"}, str(firsts))

    # V5 — the record the REAL entry engine builds carries the stamped value
    try:
        import inspect
        from execution import entry_engine as EE
        srcs = inspect.getsource(EE)
        reads = "vix_at_entry      = signal.vix_at_signal" in srcs or "vix_at_entry=signal.vix_at_signal" in srcs.replace(" ", "")
        s = sig()
        run(s, {"macro": macro})
        check("V5 the entry engine's record takes vix_at_entry from the signal field that was stamped",
              reads and s.vix_at_signal == 17.35, f"reads_signal_field={reads} stamped={s.vix_at_signal!r}")
    except Exception as exc:                                  # noqa: BLE001
        check("V5 (did not run)", False, f"{type(exc).__name__}: {exc}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — every entry is stamped with the VIX it was taken at")
    return 0


if __name__ == "__main__":
    sys.exit(main())
