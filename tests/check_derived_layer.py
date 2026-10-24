#!/usr/bin/env python3
"""
tests/check_derived_layer.py  v4.1
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).


The derived layer informs and never blocks, absence is never zero, and
the 0DTE term decays.

v4.0  2026-08-22  Built with the manifold. See docs/DERIVED_STORES.md.

TWO PROPERTIES, both operator rulings, both of which this repo has violated
before at real cost:

  1. **DERIVERS ARE CONTRIBUTORS, NEVER GATES.** No write path in the derived
     layer may raise into a caller's decision path. A derived value that
     cannot be produced is simply absent; the engine trades without it. This
     a veto that stopped a fleet for a whole session.

  2. **ABSENCE IS NULL, NEVER 0.0.** A charm of zero means delta is stable —
     a real and useful reading. A charm that could not be computed is the
     absence of a reading. VW.1 burned five layers on exactly this confusion;
     the gap prior_dir and the sweep score were both silent zeros that read as
     measurements.

⚠️ C2 IS THE ONE THAT MATTERS AND IT IS ADVERSARIAL. It hands the writers a
poisoned connection and asserts they SWALLOW the failure. A checker that only
tests the happy path would pass against a deriver that takes the bot down.

BORN RED: revert `_write`'s try/except and C2 fails; make `vanna` return 0.0 on
a flat IV and C3 fails.

Run:  cd ~/options-trader && python3 tests/check_derived_layer.py
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROBLEMS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


def main() -> int:
    print("=" * 68)
    print("DERIVED LAYER: contributes, never blocks; absence is never zero")
    print("=" * 68)

    tmp = tempfile.mkdtemp()
    os.environ["OT_DERIVED_DB"] = os.path.join(tmp, "derived.db")
    from data.derived_store import DerivedStore
    from analysis import second_order as so

    st = DerivedStore()

    # ── C1 the homes exist and round-trip ────────────────────────────────
    import time
    now = time.time()
    n = st.append_forks([("T", "1h", now, 0, "NO_CONTAINED_WINDOW", 19, None,
                          None, None, None, None, None, None, None, None,
                          None, None, None, None, None, None)])
    check("C1 a REJECTED fork is a row, with its reason", n == 1,
          "rejections must be stored — six distinct reasons collapsed into "
          "one 'rails absent' message is why r59 was misdiagnosed twice")
    r = st.conn.execute("SELECT reject_reason, scan_depth FROM fork_series"
                        " WHERE built=0").fetchone()
    check("C1 the reason survives the round-trip",
          r == ("NO_CONTAINED_WINDOW", 19), str(r))

    # ── C2 A POISONED WRITER MUST NOT RAISE ──────────────────────────────
    # Adversarial: close the connection under the store, then write.
    st.conn.close()
    raised = None
    try:
        got = st.append_indicators([("T", "5m", now, None, 27.3, 1.8, 0.01,
                                     None, None, None, None, None, None,
                                     None, None)])
    except Exception as exc:                                    # noqa: BLE001
        raised, got = exc, None
    check("C2 a broken derived write does NOT raise", raised is None,
          f"raised {type(raised).__name__} — a deriver that can throw into the "
          f"caller is a GATE, and derivers are contributors only")
    check("C2 it reports zero rows written", got == 0, f"returned {got!r}")

    # ── C3 absence is None, never 0.0 ────────────────────────────────────
    flat_iv = [(1000.0, 0.50, 0.22), (1300.0, 0.44, 0.22)]
    check("C3 vanna on FLAT IV is None, not 0.0",
          so.vanna(flat_iv) is None,
          "a flat IV has no denominator; 0.0 would ASSERT delta is "
          "insensitive to volatility, a much stronger and false claim")
    check("C3 charm with one sample is None", so.charm([(1.0, 0.5, 0.2)]) is None)
    check("C3 charm below the dt floor is None",
          so.charm([(1000.0, 0.50, 0.22), (1005.0, 0.44, 0.25)]) is None,
          "dividing a delta wobble by a fraction of a second manufactures "
          "enormous charm")

    # ── C4 the maths is right when it IS measurable ──────────────────────
    live = [(1000.0, 0.50, 0.22), (1300.0, 0.44, 0.25)]
    c, v = so.charm(live), so.vanna(live)
    check("C4 charm is computed when measurable",
          c is not None and abs(c - (-0.06 / 300.0 * 86400.0)) < 1e-6,
          f"got {c!r}")
    check("C4 vanna is computed when measurable",
          v is not None and abs(v - (-0.06 / 0.03)) < 1e-6, f"got {v!r}")

    # ── C5 an unopenable store degrades to None, not an exception ────────
    os.environ["OT_DERIVED_DB"] = "/proc/cannot/exist/derived.db"
    import importlib
    import data.derived_store as ds
    importlib.reload(ds)
    raised = None
    try:
        s = ds.get_derived_store()
    except Exception as exc:                                    # noqa: BLE001
        raised, s = exc, "raised"
    check("C5 an unopenable derived store returns None, never raises",
          raised is None and s is None,
          f"raised={raised!r} returned={s!r} — the bot must trade without it")

    # ── C6 volatility measures: absence stays absent ─────────────────────
    from analysis import volatility_measures as vm
    from datetime import datetime
    check("C6 thin sample gives None, not a sigma",
          vm.realised_vol_cc([{"close": 100.0}] * 3, "5m") is None,
          "a sigma from 3 bars is noise wearing a number")
    check("C6 VRP with a missing side is None",
          vm.variance_risk_premium(None, 0.18) is None,
          "0.0 would say implied and realised AGREE — a strong claim")
    check("C6 unknown interval gives None",
          vm.realised_vol_cc([{"close": 100.0 + i} for i in range(40)], "7m")
          is None, "annualising an interval we have no factor for invents one")

    # ── C7 THE 0DTE TERM ACTUALLY DECAYS ─────────────────────────────────
    # The whole reason expected move needs the series rather than a scalar.
    f0 = vm.session_fraction_remaining(datetime(2026, 8, 24, 9, 35))
    f1 = vm.session_fraction_remaining(datetime(2026, 8, 24, 14, 0))
    f2 = vm.session_fraction_remaining(datetime(2026, 8, 24, 16, 30))
    check("C7 session fraction decays through the day", f0 > f1 > 0,
          f"09:35={f0} 14:00={f1}")
    check("C7 after the bell the fraction is 0", f2 == 0.0, f"got {f2}")
    em_am = vm.expected_move_iv(215.0, 0.28, f0)
    em_pm = vm.expected_move_iv(215.0, 0.28, f1)
    check("C7 expected move SHRINKS into the afternoon",
          em_am is not None and em_pm is not None and em_pm < em_am,
          f"am={em_am} pm={em_pm} — a constant atm_iv scalar cannot express "
          f"this, which is why the afternoon looked identically sized")

    # ── C8 THE ENGINES: a broken deriver must not stop the others ────────
    # ⚠️ ADVERSARIAL. A subclass that raises on every call is planted into the
    # middle of the set; the engines AFTER it must still run. One deriver's
    # failure taking the rest with it would make "which derived port went
    # dark" unanswerable — the exact blindness that cost Friday.
    from derived.base import DerivedEngine, run_all

    class Exploding(DerivedEngine):
        name = "exploding"
        def derive(self, ctx):
            raise RuntimeError("planted")

    class Counting(DerivedEngine):
        name = "counting"
        def __init__(self):
            super().__init__(None)
            self.calls = 0
        def derive(self, ctx):
            self.calls += 1
            return 7

    boom, after = Exploding(None), Counting()

    # ⚠️ THE TWO GUARDS ARE TESTED SEPARATELY, ON PURPOSE. `run()` wraps
    # derive() and `run_all()` wraps run() — so testing only through run_all
    # lets EITHER guard alone carry the assertion, and the check goes green
    # with half the protection removed. Mutation-proven 2026-08-22: removing
    # either wrapper individually left an earlier draft of this check PASSING.
    # Inner guard: call run() DIRECTLY, no outer net beneath it.
    raised = None
    try:
        direct = boom.run({})
    except Exception as exc:                                    # noqa: BLE001
        raised, direct = exc, None
    check("C8 INNER: engine.run() swallows a raising derive()", raised is None,
          f"raised {type(raised).__name__} — derive() is unwrapped, so a "
          f"deriver can throw straight into the tick loop")
    check("C8 INNER: run() reports 0 rows", direct == 0, f"got {direct!r}")

    # Outer guard: an engine whose run() ITSELF raises, so only run_all can
    # save the loop.
    class BadRun(DerivedEngine):
        name = "badrun"
        def run(self, ctx):
            raise RuntimeError("run itself is broken")
        def derive(self, ctx):
            return 0

    raised = None
    try:
        res_outer = run_all([BadRun(None), Counting()], {})
    except Exception as exc:                                    # noqa: BLE001
        raised, res_outer = exc, {}
    check("C8 OUTER: run_all survives an engine with a broken run()",
          raised is None,
          f"raised {type(raised).__name__} — one engine breaking its own "
          f"wrapper would stop every engine after it")
    check("C8 OUTER: engines after the broken one still ran",
          res_outer.get("counting") == 7, f"got {res_outer!r}")

    raised = None
    try:
        res = run_all([boom, after], {})
    except Exception as exc:                                    # noqa: BLE001
        raised, res = exc, {}
    check("C8 a raising deriver does not propagate", raised is None,
          f"raised {type(raised).__name__}")
    check("C8 it reports 0 rows for itself", res.get("exploding") == 0,
          f"got {res.get('exploding')!r}")
    check("C8 the NEXT engine still ran", after.calls == 1 and res.get("counting") == 7,
          f"calls={after.calls} result={res.get('counting')!r}")
    # `boom` has been run twice by now (once directly for the INNER guard,
    # once through run_all), so the assertion is "every run failed and the
    # reason is retained" — not a hardcoded count that breaks when the test
    # above it grows.
    _st = boom.status()
    check("C8 every failure is counted, with its reason retained",
          _st["failures"] == _st["runs"] and _st["runs"] >= 2
          and "planted" in (_st["last_error"] or ""),
          str(_st))

    # ── C9 the registry degrades to [] rather than raising ───────────────
    import derived.registry as reg
    os.environ["OT_DERIVED_DB"] = "/proc/cannot/exist/d.db"
    import data.derived_store as ds2
    importlib.reload(ds2)
    importlib.reload(reg)
    raised = None
    try:
        eng = reg.build_engines("NVDA")
    except Exception as exc:                                    # noqa: BLE001
        raised, eng = exc, None
    check("C9 an unopenable store yields NO engines, not an exception",
          raised is None and eng == [],
          f"raised={raised!r} engines={eng!r} — the box must trade unchanged")

    print("=" * 68)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        print("  A deriver that can block is a gate, and a zero that means")
        print("  'unknown' is a lie the study will believe.")
        return 1
    print("  ALL GREEN - derived values inform, and absence stays absent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
