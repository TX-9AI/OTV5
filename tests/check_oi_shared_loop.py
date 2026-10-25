#!/usr/bin/env python3
"""
tests/check_oi_shared_loop.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-18  OTV4TEST r294 (OI.2) — MAINLINE's tests/check_oi_shared_loop.py v1.0 (otv4 r493 1c60b69, sha256
      fc3c6e46...) VERBATIM below this line: the same gate run in both trees (WA 38.2). RED on 20e660f at O1 O2 O4.
v1.0  2026-10-18  r493 / OI.2 — THE OI FETCH RUNS ON THE SHARED SDK LOOP.

  data/open_interest._await ran the fetch under asyncio.run(): a throw-away loop,
  closed when the fetch returned. The tastytrade Session holds ONE httpx
  AsyncClient whose pooled connection is bound to the loop it was used on, so
  whichever side came second failed "Event loop is closed": the next
  tasty_client.run_async call (fleet: 19-43 days per box, the 10:00 ET
  structure refresh; on a live box the first entry's buying-power read), or the
  OI batches themselves after a run_async call (QQQ, SPX: 304 lines each).
  Found by OTV4TEST's 2026-10-18 audit (MSG-QQQ-1018-04).

  A fake Session models that one fact: its connection binds to the first loop
  that uses it, and a later use from any other loop raises RuntimeError
  ("Event loop is closed" when that loop is closed). Drives the REAL
  fetch_open_interest and the REAL tasty_client.run_async / get_loop:
  O1  OI first, then an SDK call through run_async: the call succeeds
  O2  an SDK call through run_async first, then OI: every symbol is fetched
  O3  reached from INSIDE the shared loop, the fetch returns within 10 s
      (no deadlock) and raises nothing into its caller
  O4  _await calls no asyncio.run (AST)

Run:  python3 tests/check_oi_shared_loop.py   (exit 0 green, 1 red)
"""
import ast
import asyncio
import glob as _glob
import logging
import os
import sys
import time
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class FakeSession:
    """One pooled connection, bound to the first loop that uses it."""
    def __init__(self):
        self.bound = None

    async def use(self):
        loop = asyncio.get_running_loop()
        if self.bound is None:
            self.bound = loop
        elif self.bound is not loop:
            raise RuntimeError("Event loop is closed" if self.bound.is_closed()
                               else "connection bound to a different event loop")
        await asyncio.sleep(0)


async def fake_by_type(session, options=None, **_):
    await session.use()
    return [types.SimpleNamespace(symbol=s, open_interest=100 + i)
            for i, s in enumerate(options or [])]


async def fake_balances(session):
    await session.use()
    return "balances"


def main():
    logging.disable(logging.CRITICAL)
    try:
        import tastytrade.market_data as md
    except Exception:                                        # noqa: BLE001
        md = types.ModuleType("tastytrade.market_data")
        sys.modules.setdefault("tastytrade", types.ModuleType("tastytrade"))
        sys.modules["tastytrade.market_data"] = md
    md.get_market_data_by_type = fake_by_type

    from data import open_interest as OI
    from data import tasty_client as tc

    def reset():
        OI._CACHE, OI._CACHE_DAY, OI._LAST_ATTEMPT = {}, None, 0.0

    syms = [f".QQQ261019C{700 + i}" for i in range(150)]     # two batches

    # O1 — OI first, then an SDK call on the shared loop
    reset()
    s1 = FakeSession()
    got1 = OI.fetch_open_interest(s1, syms)
    err = None
    try:
        tc.run_async(fake_balances(s1))
    except Exception as e:                                   # noqa: BLE001
        err = e
    check("O1 OI first, then run_async: the SDK call succeeds",
          err is None and len(got1) == len(syms), f"run_async raised {err!r}; OI got {len(got1)}")

    # O2 — an SDK call first, then OI
    reset()
    s2 = FakeSession()
    tc.run_async(fake_balances(s2))
    got2 = OI.fetch_open_interest(s2, syms)
    check("O2 run_async first, then OI: every symbol is fetched",
          len(got2) == len(syms), f"got {len(got2)} of {len(syms)}")

    # O3 — reached from inside the shared loop: no deadlock, nothing raised
    reset()
    s3 = FakeSession()

    async def inside():
        t0 = time.monotonic()
        try:
            OI.fetch_open_interest(s3, syms[:5])
            return None, time.monotonic() - t0
        except Exception as e:                               # noqa: BLE001
            return e, time.monotonic() - t0

    fut = asyncio.run_coroutine_threadsafe(inside(), tc.get_loop())
    try:
        raised, took = fut.result(timeout=10)
        ok3 = raised is None and took < 10
        d3 = f"raised={raised!r} took={took:.1f}s"
    except Exception as e:                                   # noqa: BLE001
        ok3, d3 = False, f"did not return within 10 s ({e!r}): the shared loop deadlocked"
    check("O3 from inside the shared loop: returns, no deadlock, raises nothing", ok3, d3)

    src = open(os.path.join(_root, "data", "open_interest.py")).read()
    fn = next((n for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.FunctionDef) and n.name == "_await"), None)
    uses_run = fn is not None and any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "run" and getattr(n.func.value, "id", "") == "asyncio"
        for n in ast.walk(fn))
    check("O4 _await calls no asyncio.run", fn is not None and not uses_run,
          f"_await found={fn is not None} asyncio.run present={uses_run}")

    print()
    if FAILED:
        print(f"RED: {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
