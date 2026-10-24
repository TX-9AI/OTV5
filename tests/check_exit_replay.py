#!/usr/bin/env python3
"""tests/check_exit_replay.py — v1.2
THE PREMIUM-REPLAY TOOL IS GATED (RPL.1).

v1.2  2026-09-19  OTV4TEST r64 — X11/X12/X13: r62's credit flip inverted every
      credit vertical and nothing here could see it. Asserted PER LEG BY SYMBOL.
v1.1  2026-09-19  OTV4TEST r63 — X8/X9/X10 added for r63's three repairs to
      r62: the anchored stop regex, and a positive control that can no longer
      pass on an empty set. The band's independence from the derived stop is
      mutation-proven rather than asserted here, and the header says so.
v1.0  2026-09-19  OTV4TEST r62 — `tests/exit_replay.py` carried six defects and
      NOTHING RAN IT. It is not a `check_*.py`, so the sweep never touched it,
      and its `--selftest` takes an argument the lander's CHECK directive cannot
      pass. It therefore sat at 0 of 44 replayed, announcing that the TAPE was
      empty, for as long as anyone had been reading its output. This wrapper
      puts it inside the sweep and inside every land.

🔑 IT RUNS THE TOOL'S OWN SELFTEST AND THEN ASSERTS THE THINGS THAT SELFTEST
CANNOT: that the orientation resolver actually imported (not a silent fallback),
and that the closing verdict is GATED so it can never blame the tape while the
tool is naming its own refusals.

⚠️ NOTHING HERE TOUCHES A LIVE STORE. The selftest is `:memory:`; the verdict
case drives `run()` with an empty fetch and an in-memory row.

  X1  the tool's own selftest passes
  X2  the orientation resolver IMPORTED — no silent fallback to the dead flag
  X3  ...and it resolves a credit structure as credit (it is wired, not merely present)
  X4  OCC -> streamer, including a split-adjusted root and a half-strike
  X5  a butterfly is weighted 1/2/1
  X6  the verdict cannot blame the tape when refusals exist
  X7  `option_symbol` resolves a single-leg debit
  X8  the stop regex is ANCHORED — a prefixed or credit-basis stop is not a premium stop
  X9  a control that applied to NOTHING shouts UNVERIFIED, never passes silently
  X10 ...and when it did apply, the run says to how many
  X11 a CREDIT VERTICAL is NOT inverted — short leg -1, long leg +1, PER SYMBOL
  X12 ...and a single-leg debit is not inverted either
  X13 the flip survives, scoped to the single-leg credit path (guarded, unreachable)

🔴 X11 IS ASSERTED PER LEG BY SYMBOL, NEVER AS A SORTED SIGN LIST. `[-1, 1]` is
the same list whichever leg carries which, so a sorted comparison cannot see an
inversion at all — the control agent's equivalent check stayed GREEN on the
restored defect for exactly that reason, and my own r62 selftest failed on
CORRECT code for the mirror of it. Sorting destroys the association asserted.

⚠️ X9/X10 EXIST BECAUSE THE BAND ITSELF IS NOT DIRECTLY OBSERVABLE FROM HERE.
That the tolerance no longer scales with the derived stop is proven by MUTATION
(revert it and the butterfly row's verdict flips), not by this file — stated so
nobody reads X9 as covering it.

Run:  python3 tests/check_exit_replay.py
"""
import io
import os
import sys
import contextlib

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "tests"))
FAILED, RAN = [], []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    RAN.append(name)
    if not ok:
        FAILED.append(name)


def guard(name, fn):
    try:
        ok, detail = fn()
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"{type(exc).__name__}: {exc}")
        return
    check(name, bool(ok), detail)


import exit_replay as er                                        # noqa: E402

guard("X1 exit_replay's own selftest passes",
      lambda: (er.selftest() == 0, ""))
guard("X2 the orientation resolver imported (no silent fallback)",
      lambda: (bool(er.RESOLVER) and er.RESOLVER_FALLBACKS == 0,
               er.RESOLVER or f"UNAVAILABLE: {er.RESOLVER_ERR}"))
guard("X3 ...and it resolves a credit structure AS credit",
      lambda: (er._is_credit({"strategy": "SweepCreditSpread",
                              "setup_type": "sweep_credit_short"})
               and not er._is_credit({"strategy": "ORBStrategy"}), ""))
guard("X4 OCC -> streamer, adjusted root and half-strike included",
      lambda: (er.streamer_symbol("QQQ   260823C00100000") == ".QQQ260823C100"
               and er.streamer_symbol("CRM   260918C00182500") == ".CRM260918C182.5"
               and er.streamer_symbol("GOOGL1260918C00150000") == ".GOOGL1260918C150"
               and er.streamer_symbol("nonsense") is None, ""))


def _fly():
    legs, why = er.legs_of({"strategy": "GEXPinButterfly",
                            "lower_symbol": "QQQ   260918C00718000",
                            "center_symbol": "QQQ   260918C00720000",
                            "upper_symbol": "QQQ   260918C00722000"})
    return (not why) and sorted(s for _y, s in legs) == [-2, 1, 1], str(legs)


guard("X5 a butterfly is weighted 1/2/1, not 1/1/1", _fly)


def _verdict():
    """A row that refuses must NOT produce the tape-blaming verdict."""
    row = {"strategy": "ORBStrategy", "status": "closed",
           "entry_time": "2026-09-18T13:00:00+00:00",
           "exit_time": "2026-09-18T13:10:00+00:00",
           "option_symbol": "QQQ   260918C00718000",
           "pnl_usd": 0.0, "contracts": 1, "entry_premium": 1.0}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        er.run([row], lambda sym, lo, hi: [])       # no quotes at all
    out = buf.getvalue()
    blamed = "needs its first live" in out or "s3_push" in out
    named = "REFUSED" in out
    return (named and not blamed), ("blamed the tape" if blamed else "refusal named only")


guard("X6 the verdict cannot blame the tape while naming refusals", _verdict)
guard("X7 option_symbol resolves a single-leg debit",
      lambda: (er.legs_of({"strategy": "ORBStrategy",
                           "option_symbol": "QQQ   260823C00100000"})[0]
               == [(".QQQ260823C100", +1)], ""))

def _credit_not_inverted():
    """The combo must be `-(spread value)`: short leg NEGATIVE, long POSITIVE."""
    legs, why = er.legs_of({"strategy": "SweepCreditSpread",
                            "setup_type": "sweep_credit_short",
                            "short_symbol": "QQQ   260918C00718000",
                            "long_symbol": "QQQ   260918C00720000"})
    if why:
        return False, why
    d = dict(legs)
    return (d.get(".QQQ260918C718") == -1 and d.get(".QQQ260918C720") == +1), str(d)


guard("X11 a credit vertical is NOT inverted (per leg, by symbol)",
      _credit_not_inverted)
guard("X12 a single-leg debit is not inverted",
      lambda: (er.legs_of({"strategy": "ORBStrategy",
                           "option_symbol": "QQQ   260823C00100000"})[0]
               == [(".QQQ260823C100", +1)], ""))


def _guarded_flip():
    """DRIVE the guarded branch, do not merely assert it exists.

    ⚠️ A SYNTHETIC ROW IS REQUIRED AND THAT IS THE POINT. No row this book can
    produce reaches this branch — `is_valid` fails closed on a naked short — so
    a mutation that disables the marker changes nothing observable and a gate
    resting on real rows would stay green on it (measured: mutation I did).
    A guarded branch nobody exercises is a branch that rots, so it is called
    here directly with the shape that would reach it if one ever existed.
    """
    naked = er.legs_of({"strategy": "SweepCreditSpread",
                        "setup_type": "sweep_credit_short",
                        "option_symbol": "QQQ   260918C00718000"})[0]
    fires = naked == [(".QQQ260918C718", -1)]        # the flip DID apply
    d = dict(er.legs_of({"strategy": "SweepCreditSpread",
                         "setup_type": "sweep_credit_short",
                         "short_symbol": "QQQ   260918C00718000",
                         "long_symbol": "QQQ   260918C00720000"})[0])
    scoped = d.get(".QQQ260918C718") == -1           # ...and NOT to the spread
    return (fires and scoped), f"single-leg credit={naked}"


guard("X13 the flip survives, scoped to single-leg credit only", _guarded_flip)


def _regex():
    bad = {"tcs_stop_15%_of_credit": None, "stop_15%_of_credit": None,
           "trail_stop_10% pnl=1%": None, "orb_trail_stop pnl=11.8%": None}
    good = {"hard_stop_20% pnl=-25.0%": 0.20, "stop_40% pnl=-40.4%": 0.40,
            "premium_stop_15% pnl=-16.0%": 0.15}
    for k, want in {**bad, **good}.items():
        got = er.recorded_stop_pct({"exit_reason": k})
        if got != want:
            return False, f"{k!r} -> {got}, wanted {want}"
    return True, f"{len(bad)} rejected, {len(good)} accepted"


guard("X8 the stop regex is anchored (prefixed/credit-basis rejected)", _regex)


def _run_capture(rows, fetch):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        er.run(rows, fetch)
    return buf.getvalue()


def _flat_row(exit_reason):
    return {"strategy": "ORBStrategy", "status": "closed", "option_side": "call",
            "entry_time": "2026-09-18T13:00:00+00:00",
            "exit_time": "2026-09-18T13:10:00+00:00",
            "option_symbol": "QQQ   260918C00718000",
            "exit_reason": exit_reason, "pnl_usd": 0.0,
            "contracts": 1, "entry_premium": 1.0}


def _flat_fetch(sym, lo, hi):
    t0 = 1789736400.0          # 2026-09-18 13:00:00Z
    return [(t0 + i * 15.0, 1.0, 1.02) for i in range(41)]


def _zero_applied():
    """Every replayed row exited on something that is NOT a premium stop."""
    out = _run_capture([_flat_row("orb_trail_stop pnl=1.0%")], _flat_fetch)
    return ("APPLIED TO NOTHING" in out and "UNVERIFIED" in out), out.strip()[-70:]


guard("X9 a control applied to NOTHING shouts UNVERIFIED", _zero_applied)


def _applied_count():
    out = _run_capture([_flat_row("hard_stop_25% pnl=-1.0%")], _flat_fetch)
    return ("positive control applied to 1 of 1" in out), out.strip()[-70:]


guard("X10 ...and when it applied, the run says to how many", _applied_count)

print()
if FAILED:
    print(f"  RED — {len(FAILED)} of {len(RAN)} failed: " + ", ".join(FAILED))
    sys.exit(1)
print(f"  GREEN — {len(RAN)} checks")
