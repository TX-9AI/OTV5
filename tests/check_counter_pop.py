#!/usr/bin/env python3
"""
tests/check_counter_pop.py — v1.1
v1.1  2026-09-26  r438 — N6 + N7, shared with OTV4TEST. 🔴 v1.0 NEVER RAN THE
      PATH THAT WRITES: N4 calls `--apply` only with the lock REFUSED, and the
      stub's `load_ledger` returned the ORIGINAL dict, so a correct apply would
      have read back an unchanged ledger and returned rc=1 — the gate could not
      have passed the thing the tool exists to do. ⚠️ MAINLINE'S 31 POPS WERE
      PROVEN ON PRODUCTION, IN THE WRONG ORDER: 31 entries, exact per-box
      counts, SHORT 0 on re-verify — real evidence, obtained by executing on 15
      live boxes because the gate could not supply it. N6 runs `--apply` with
      the lock HELD against a stub whose `load_ledger` returns what was SAVED.
      N7: N1-N6 replace `s3_push` wholesale, so a rename in the REAL module
      stays green here and kills the tool at import ON THE BOX, where the
      operator sees it and we do not — N7 loads the real file and binds every
      name AND call shape the tool uses. Both found by the peer session against
      our agreed definition of a properly-constructed shared fix.

v1.0  2026-09-26  r436 / S3.25 — the gate for the narrow counter repair.

🔴 N2 IS THE SHIP-BLOCKER AND IT IS THE WHOLE POINT OF THE TOOL. A prefix that
is merely SHORT (`got < exp`, `got > 0`) must be REFUSED, never popped. r180's
heal repairs exactly that case on the next clean drain and LOGS it
(`HEALED <prefix> ledger 29 -> 28`). Popping it here would take a repair the
system performs correctly and make it permanent and unlogged — turning a
recoverable one-object gap into a silent lie in the ledger.
📊 MEASURED, SOFI 2026-09-26: ten short prefixes, six at `got=0` and four
partial (27/26, 29/28, 29/28, 2/1). Only six qualify. My own first reading
called all ten emptied; the peer session caught it, which is why this is a
gate and not a comment.

⚠️ N3 — DRY BY DEFAULT. The tool writes to the counter ledger of a live box.
A default that acts is how `--reconcile` became dangerous enough to need
replacing.

⚠️ N4 — NO LOCK, NO RUN, AND SAY SO. r349: a fleet reconcile lost the race to
`s3-push.timer`, returned 0, printed nothing and exited 0 — an operator's
repair indistinguishable from a box with nothing to say, while the fleet stayed
HELD for three nights. Losing the lock must be rc=3 and a named line.

BORN RED, verified 2026-09-26 against the pre-change tree:
  N1-N5 -> "warehouse.counter_pop is absent"

MUTATIONS — each reddens exactly one check:
  * pop on `got < exp` instead of `got == 0`        -> N2 only
  * write without --apply                           -> N3 only
  * proceed when the lock is unavailable            -> N4 only
  * pop a key that is not in the ledger             -> N5 only
  v1.1:
  * pop refused rows inside main() rather than plan() -> N6
  * an --apply that never calls save_ledger           -> N6
  * a name counter_pop reads renamed in s3_push       -> N7
  * acquire_lock no longer takes the wait argument    -> N7
"""
from __future__ import annotations

import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_fails = []


def ck(tag, ok, msg=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {tag}  {msg}")
    if not ok:
        _fails.append(tag)


def _stub_s3_push(tmp, lock_ok=True, saved=None):
    m = types.ModuleType("s3_push")
    m.REGION, m.BUCKET, m.LOCK_WAIT = "us-east-2", "b", 1
    m.COUNTERS_PATH = m.LEDGER_PATH = os.path.join(tmp, "prefix_counters.json")
    m._ledger = {"A/": {"n": 1}, "B/": {"n": 29}, "C/": {"n": 2}}
    m._short = [("A/", 1, 0), ("B/", 29, 28), ("C/", 2, 1), ("GONE/", 1, 0)]

    class _FH:
        def close(self): pass
    m.acquire_lock = (lambda w=0: _FH()) if lock_ok else (lambda w=0: None)
    # v1.1 — reads back what was SAVED, as the real file does. v1.0 returned
    # the original dict, so a correct --apply could only ever read back
    # "unchanged" and report rc=1: the gate could not pass a working tool.
    m.load_ledger = lambda p=None: dict(saved[-1]) if saved else dict(m._ledger)
    m.verify = lambda s3, b, c: (list(m._short), 10, 7)

    def _save(led, p=None):
        if saved is not None:
            saved.append(dict(led))
        return True
    m.save_ledger = _save
    sys.modules["s3_push"] = m
    return m


def main():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="cpop_gate_")
    sys.path.insert(0, os.path.join(ROOT, "warehouse"))
    sys.path.insert(0, ROOT)
    _stub_s3_push(tmp)
    sys.modules.pop("counter_pop", None)
    try:
        import counter_pop as cp
    except Exception as exc:                                      # noqa: BLE001
        for t in ("N1", "N2", "N3", "N4", "N5"):
            ck(t, False, f"warehouse.counter_pop is absent ({type(exc).__name__})")
        print(f"\nRED — {len(_fails)} check(s) failed: {' '.join(_fails)}")
        return 1

    led = {"A/": {"n": 1}, "B/": {"n": 29}, "C/": {"n": 2}}
    short = [("A/", 1, 0), ("B/", 29, 28), ("C/", 2, 1), ("GONE/", 1, 0)]
    pop, refuse = cp.plan(led, short)
    popped = [p[0] for p in pop]
    refused = {r[0]: r[3] for r in refuse}

    ck("N1", popped == ["A/"],
       f"pops only the EMPTY, PRESENT prefix — got {popped}")

    partials_refused = "B/" in refused and "C/" in refused
    ck("N2", partials_refused and "heal" in (refused.get("B/") or ""),
       "a PARTIAL (got>0) is refused and the reason names r180's heal"
       if partials_refused else f"partial was not refused: {popped}")

    # N3 — dry by default: no save without --apply
    saved = []
    _stub_s3_push(tmp, saved=saved)
    sys.modules.pop("counter_pop", None)
    import counter_pop as cp2
    try:
        import boto3                                              # noqa: F401
        rc = cp2.main([])
        ck("N3", rc == 0 and not saved,
           f"dry by default — rc={rc}, ledger writes={len(saved)}")
    except Exception as exc:                                      # noqa: BLE001
        ck("N3", False, f"dry run raised {type(exc).__name__}: {exc}")

    # N4 — no lock, no run, rc=3
    saved2 = []
    _stub_s3_push(tmp, lock_ok=False, saved=saved2)
    sys.modules.pop("counter_pop", None)
    import counter_pop as cp3
    try:
        rc = cp3.main(["--apply"])
        ck("N4", rc == 3 and not saved2,
           f"lock unavailable -> rc={rc}, writes={len(saved2)} (want 3 / 0)")
    except Exception as exc:                                      # noqa: BLE001
        ck("N4", False, f"raised {type(exc).__name__}: {exc}")

    ck("N5", "GONE/" in refused and "ledger" in (refused.get("GONE/") or ""),
       "a key absent from the ledger is refused, not popped")

    # ── N6 — THE PATH THAT WRITES: --apply with the lock HELD ───────────
    saved3 = []
    _stub_s3_push(tmp, saved=saved3)
    sys.modules.pop("counter_pop", None)
    import counter_pop as cp4
    try:
        rc = cp4.main(["--apply"])
        last = saved3[-1] if saved3 else {}
        ck("N6", rc == 0 and len(saved3) == 1 and "A/" not in last
           and "B/" in last and "C/" in last,
           f"--apply: rc={rc}, saves={len(saved3)}, kept={sorted(last)} "
           "(want 0 / 1 / B/ C/ kept, A/ gone)")
    except Exception as exc:                                      # noqa: BLE001
        ck("N6", False, f"--apply raised {type(exc).__name__}: {exc}")

    # ── N7 — THE REAL s3_push STILL CARRIES EVERY NAME AND CALL SHAPE ───
    # ⚠️ exec_module RUNS THE REAL MODULE'S TOP LEVEL. Verified on otv4
    # 2026-09-26: module scope is constants and `os.environ.get` only — no
    # network, no mkdir (its makedirs all sit inside functions), and an exec
    # created nothing under ~/.vertigo_warehouse. If that ever changes this
    # check must move to a subprocess, or the GATE becomes a writer.
    import inspect
    sys.modules.pop("s3_push", None)
    try:
        # 🔴 COMPILED FROM SOURCE, NEVER FROM THE BYTECODE CACHE. Measured
        # 2026-09-26: running the M4 mutant left a .pyc for the MUTATED
        # s3_push, and after restoring the source byte-identically N7 still
        # reported `acquire_lock: too many positional arguments` — it was
        # reading the cache. ⚠️ THE DANGEROUS DIRECTION IS THE OPPOSITE ONE:
        # a renamed constant with a stale GOOD .pyc present would make N7 pass
        # while the tool dies at import on the box, which is precisely the
        # failure N7 exists to catch. A check that can read anything but the
        # file it names is not checking that file.
        _src = os.path.join(ROOT, "warehouse", "s3_push.py")
        real = types.ModuleType("_real_s3_push")
        real.__file__ = _src
        with open(_src, "r", encoding="utf-8") as _fh:
            exec(compile(_fh.read(), _src, "exec"), real.__dict__)
        names = ("REGION", "BUCKET", "LOCK_WAIT", "COUNTERS_PATH",
                 "acquire_lock", "load_ledger", "verify", "save_ledger")
        missing = [n for n in names if not hasattr(real, n)]
        shapes = []
        for fn, args in (("acquire_lock", (1,)), ("load_ledger", ("p",)),
                         ("verify", (None, "b", {})), ("save_ledger", ({}, "p"))):
            try:
                inspect.signature(getattr(real, fn)).bind(*args)
            except (TypeError, AttributeError) as exc:            # noqa: BLE001
                shapes.append(f"{fn}: {exc}")
        ck("N7", not missing and not shapes,
           f"real s3_push — missing={missing} bad_calls={shapes}")
    except Exception as exc:                                      # noqa: BLE001
        ck("N7", False, f"real s3_push would not load: "
                        f"{type(exc).__name__}: {exc}")

    if _fails:
        print(f"\nRED — {len(_fails)} check(s) failed: {' '.join(_fails)}")
        return 1
    print("\nGREEN — only empty prefixes pop; partials heal themselves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
