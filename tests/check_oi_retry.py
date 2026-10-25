#!/usr/bin/env python3
"""tests/check_oi_retry.py — v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
THE OI WARNING FIRES ONLY WHEN THE RETRY ALSO FAILS (OI.1).

v1.1  2026-10-18  OTV4TEST r294 (OI.2) — the fixture keeps the REAL `tastytrade` package and replaces only
      `tastytrade.market_data` (carrying the real module's other names): r294's _await imports data.tasty_client,
      which imports tastytrade.Session, and the old fake package had no Session (O1/O2/O4 red on the mirror for a
      fixture reason). No check changed.

v1.0  2026-09-19  OTV4TEST r66 — `OI: fetch failed for 100 symbol(s)` fires on
      13 of 13 cycles and is a FALSE ALARM. v4.2's guard keys only the LOGGING
      to the string "loop is closed"; the `for attempt in (1, 2)` loop retries
      either way, so the batch recovers on attempt 2 and the very next line
      reads `fetched 534 symbol(s), 534 cached`.
      ⚠️ THIS CHECK EXISTS BECAUSE I READ THAT WARNING AS 100 LOST CONTRACTS
      AND WAS WRONG. O1 is the assertion that caught it: it PASSES at base,
      which is what proves the retry already worked. A born-red set that had
      included O1 would have been the defect I was claiming, and it is not
      there — the base column is the evidence, not the build column.

🔑 IT DRIVES THE REAL FUNCTION. A fake `tastytrade.market_data` is injected into
`sys.modules` so the production import inside `fetch_open_interest` resolves to
it; the fake raises the REAL error text once per batch, then succeeds. Grepping
for the guard would prove only that somebody wrote a condition (§21).

⚠️ THE FIXTURE RAISES THE VERBATIM MESSAGE FROM THE JOURNAL, not a paraphrase.
A guard keyed to a string is defeated by a fixture that invents its own string —
that would be the same defect one level up (§0.4).

  O1  a batch that fails ONCE with the real error still returns its OI
  O2  ...and the failure is not logged as a failure (the retry succeeded)
  O3  a batch that fails TWICE returns nothing for those symbols
  O4  ...and THAT is logged, naming the retry
  O5  the old string-keyed guard would NOT have rescued O1 (the defect, pinned)
  O6  plan_tick / plan_check hold 90 days — the wargaming corpus

Born red at 5876d49 on O2, O4 and O6. ⚠️ O1, O3 and O5 PASS at base and that
is the point: the retry was never broken, only mis-narrated.
Run:  python3 tests/check_oi_retry.py
"""
import importlib
import logging
import os
import sys
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED, RAN = [], []

REAL_ERR = ("<asyncio.locks.Event object at 0x7603e7909c10 [unset]> "
            "is bound to a different event loop")


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


class _Row:
    def __init__(self, sym, oi):
        self.symbol, self.open_interest = sym, oi


def _install_fake(fail_times):
    """Inject a fake SDK whose call fails `fail_times` per batch, then works."""
    state = {"n": 0}

    async def get_market_data_by_type(session, options=None):
        state["n"] += 1
        if state["n"] <= fail_times:
            raise RuntimeError(REAL_ERR)
        return [_Row(s, 100 + i) for i, s in enumerate(options or [])]

    # r294 (OI.2): the REAL package stays - _await now imports data.tasty_client, which needs
    # tastytrade.Session; only the market_data submodule is replaced, and the fake carries the
    # real module's other names so any `from tastytrade.market_data import X` still resolves.
    try:
        import tastytrade as pkg                       # the real one, if the venv has it
        import tastytrade.market_data as _real_md
        _real_attrs = dict(vars(_real_md))
    except Exception:                                  # noqa: BLE001
        pkg = sys.modules.get("tastytrade") or types.ModuleType("tastytrade")
        _real_attrs = {}
    mod = types.ModuleType("tastytrade.market_data")
    for _k, _v in _real_attrs.items():
        if not _k.startswith("__"):
            setattr(mod, _k, _v)
    mod.get_market_data_by_type = get_market_data_by_type
    sys.modules["tastytrade"] = pkg
    sys.modules["tastytrade.market_data"] = mod
    setattr(pkg, "market_data", mod)
    return state


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, r):
        self.lines.append(r.getMessage())


def _run(fail_times, syms=("AAA", "BBB")):
    """Drive the REAL fetch with a fresh module state each time."""
    for m in ("data.open_interest",):
        sys.modules.pop(m, None)
    _install_fake(fail_times)
    oi = importlib.import_module("data.open_interest")
    cap = _Cap()
    lg = logging.getLogger("data.open_interest")
    lg.addHandler(cap)
    lg.setLevel(logging.DEBUG)
    try:
        got = oi.fetch_open_interest(object(), list(syms), force=True)
    finally:
        lg.removeHandler(cap)
    return got, cap.lines


guard("O1 a batch failing ONCE with the real error still returns its OI",
      lambda: (_run(1)[0] == {"AAA": 100, "BBB": 101}, str(_run(1)[0])))
guard("O2 ...and it is not logged as a failure",
      lambda: (not any("fetch failed" in l for l in _run(1)[1]),
               " | ".join(_run(1)[1])[:70]))
guard("O3 a batch failing TWICE returns nothing for those symbols",
      lambda: (_run(9)[0] == {}, str(_run(9)[0])))
guard("O4 ...and THAT is logged, naming the retry",
      lambda: (any("after retry" in l for l in _run(9)[1]),
               " | ".join(l for l in _run(9)[1] if "fetch failed" in l)[:70]))


def _old_guard_would_have_failed():
    """The DEFECT, pinned: the v4.2 condition does not match the real error."""
    return ("loop is closed" not in REAL_ERR.lower()), REAL_ERR[:56]


guard("O5 the old string-keyed guard would NOT have matched this error",
      _old_guard_would_have_failed)


def _retention():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "rp", os.path.join(_root, "warehouse", "retention_purge.py"))
    rp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rp)
    d = rp.DERIVED_CDC_DAYS
    return (d.get("plan_tick") == 90 and d.get("plan_check") == 90), str(d)


guard("O6 plan_tick / plan_check hold 90 days (the wargaming corpus)", _retention)

print()
if FAILED:
    print(f"  RED — {len(FAILED)} of {len(RAN)} failed: " + ", ".join(FAILED))
    sys.exit(1)
print(f"  GREEN — {len(RAN)} checks")
