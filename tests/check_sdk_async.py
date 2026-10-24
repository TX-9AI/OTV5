#!/usr/bin/env python3
"""
tests/check_sdk_async.py  v1.0
v1.0  2026-10-04  r464 / B0 — EVERY ACCOUNT CALL IS AWAITED ON AN ASYNC SDK.

  🔴 On tastytrade 13.x (the boxes run 13.0.0) every Account method is a
  COROUTINE (inspect.iscoroutinefunction is True for get, place_order,
  get_order, delete_order, get_positions, …). tasty_client.get_account() did
  `Account.get(session, n)` bare, so it CACHED A COROUTINE, and every live
  place_order / get_order / delete_order raised or returned a coroutine inside
  a try/except that only logged — a LIVE box could open and close nothing.
  Paper never calls these, which is why weeks of paper never showed it.
  Found by OTV4TEST (MSG-1004-06), confirmed on a mainline box's own SDK.

  All OFFLINE — no network, no credentials:
  A1  get_account() on an async Account.get returns the ACCOUNT, not a coroutine
  A2  sdk_result runs a coroutine and passes a plain value through unchanged
      (so the fix is also right on a sync SDK)
  A3  the REAL ExitEngine._place, handed an account whose place_order is a
      coroutine, returns the placed order (the defect: AttributeError /
      'coroutine' has no attribute 'errors' path)
  A4  AST: every account.<place_order|get_order|delete_order|get_live_orders|
      get_balances|get_order_history> call and every Account.get call in
      non-test code is wrapped in sdk_result(...)
  BORN RED on otv4 0f852ee at A1 A2 A3 A4.

Run:  python3 tests/check_sdk_async.py
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


class _Placed:
    id = "ORD-1"


class _Resp:
    errors = None
    order = _Placed()


class _FakeAccount:
    account_number = "TEST123"

    async def place_order(self, session, order, dry_run=False):
        return _Resp()

    @classmethod
    async def get(cls, session, number):
        return cls()


def main():
    import data.tasty_client as tc
    real = (tc.Account, tc.get_session, getattr(tc, "get_tt_account_number", None), tc._account)
    try:
        tc.Account = _FakeAccount
        tc.get_session = lambda: object()
        tc.get_tt_account_number = lambda: "TEST123"
        tc._account = None
        acct = tc.get_account()
        check("A1 get_account returns the Account, not a coroutine",
              isinstance(acct, _FakeAccount), f"got {type(acct).__name__}")
        if not isinstance(acct, _FakeAccount):
            try:
                acct.close()
            except Exception:
                pass
    except Exception as exc:                                          # noqa: BLE001
        check("A1 get_account returns the Account, not a coroutine", False,
              f"{type(exc).__name__}: {exc}")
    finally:
        tc.Account, tc.get_session = real[0], real[1]
        if real[2] is not None:
            tc.get_tt_account_number = real[2]
        tc._account = real[3]

    sr = getattr(tc, "sdk_result", None)
    async def _seven():
        return 7
    ok2 = sr is not None and sr(_seven()) == 7 and sr(5) == 5
    check("A2 sdk_result runs a coroutine and passes a plain value through", ok2,
          "sdk_result absent" if sr is None else "wrong result")

    try:
        from execution.exit_engine import ExitEngine
        eng = ExitEngine.__new__(ExitEngine)
        placed = eng._place(object(), _FakeAccount(), object(), "probe")
        check("A3 the real ExitEngine._place returns the placed order on an async SDK",
              getattr(placed, "id", None) == "ORD-1", f"got {placed!r}")
    except Exception as exc:                                          # noqa: BLE001
        check("A3 the real ExitEngine._place returns the placed order on an async SDK",
              False, f"{type(exc).__name__}: {exc}")

    METHODS = {"place_order", "get_order", "delete_order", "get_live_orders",
               "get_balances", "get_order_history"}
    bare = []
    for dp, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ("venv", ".git", "tests", "__pycache__")]
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(dp, f)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read())
            except SyntaxError:
                continue
            wrapped = set()
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "sdk_result" and node.args):
                    wrapped.add(id(node.args[0]))
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                    continue
                f_ = node.func
                is_acct = (f_.attr in METHODS and isinstance(f_.value, ast.Name)
                           and f_.value.id in ("account", "acct"))
                is_get = (f_.attr == "get" and isinstance(f_.value, ast.Name)
                          and f_.value.id == "Account")
                if (is_acct or is_get) and id(node) not in wrapped:
                    bare.append(f"{os.path.relpath(path, ROOT)}:{node.lineno}")
    check("A4 every Account call in non-test code goes through sdk_result",
          not bare, f"bare: {bare}")

    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — every Account call is awaited on an async SDK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
