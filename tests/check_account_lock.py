#!/usr/bin/env python3
"""tests/check_account_lock.py — v5.0
v5.0  2026-10-25  OTV5 r20 (LIVE.2) — get_account() MUST RETURN. It took tasty_client._session_lock (non-reentrant)
      and then called get_session(), which takes it again: the first call hung forever. Every live order path calls
      it; paper never does and every other gate stubs it, which is why nothing caught it. Found by the 2026-10-25
      fleet field test.

🔑 IT DRIVES THE REAL get_account / get_session. Only the SDK edge is faked (Session and Account.get inside
data.tasty_client, and the three credential getters), so no network call is made and the lock under test is the
production one. Each call runs in a worker thread with a 5 s budget: a deadlock shows as a thread still alive, not
as a hung test.

  A1  a first get_account() returns the account (no deadlock)
  A2  a second call returns the CACHED account (Account.get ran once)
  A3  reset_session() then get_account() builds a fresh session and account
  A4  four threads calling at once all get the same account; Account.get runs once

Born red on 6dc63e2 (OTV5 r19): A1 A2 A3 A4 (the first call never returns).
Run:  python3 tests/check_account_lock.py
"""
import os
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_fails = []


def ck(tag, ok, msg=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {tag}  {msg}")
    if not ok:
        _fails.append(tag)


def _timed(fn, budget=5.0):
    """-> (finished, result). A thread still alive after `budget` is a deadlock."""
    box = {}
    t = threading.Thread(target=lambda: box.setdefault("r", fn()), daemon=True)
    t.start()
    t.join(budget)
    return (not t.is_alive()), box.get("r")


def main():
    import data.tasty_client as tc

    calls = {"session": 0, "account": 0}

    class FakeSession:
        def __init__(self, *a, **k):
            calls["session"] += 1

    class FakeAccount:
        account_number = "5WTEST01"

        @staticmethod
        def get(session, number):
            calls["account"] += 1
            return FakeAccount()

    real = (tc.Session, tc.Account, tc.get_tt_client_secret, tc.get_tt_refresh_token,
            tc.get_tt_account_number, tc._session, tc._account)
    tc.Session, tc.Account = FakeSession, FakeAccount
    tc.get_tt_client_secret = lambda: "x"
    tc.get_tt_refresh_token = lambda: "x"
    tc.get_tt_account_number = lambda: "5WTEST01"
    tc._session = tc._account = None
    try:
        done, acct = _timed(tc.get_account)
        ck("A1", done and isinstance(acct, FakeAccount), "first get_account() returns")
        if not done:
            # the worker holds the lock forever; nothing below can run in this process
            for tag in ("A2", "A3", "A4"):
                ck(tag, False, "blocked behind A1's deadlock")
            return
        done2, acct2 = _timed(tc.get_account)
        ck("A2", done2 and acct2 is acct and calls["account"] == 1, "second call is the cached account")
        tc.reset_session()
        done3, acct3 = _timed(tc.get_account)
        ck("A3", done3 and acct3 is not acct and calls["session"] == 2 and calls["account"] == 2,
           "reset -> a fresh session and account")
        tc._session = tc._account = None
        before = calls["account"]
        got, ths = [], []
        for _ in range(4):
            th = threading.Thread(target=lambda: got.append(tc.get_account()), daemon=True)
            ths.append(th)
            th.start()
        for th in ths:
            th.join(5.0)
        ck("A4", len(got) == 4 and len({id(g) for g in got}) == 1 and calls["account"] - before == 1,
           "four threads, one Account.get, one account")
    finally:
        if not _fails:
            (tc.Session, tc.Account, tc.get_tt_client_secret, tc.get_tt_refresh_token,
             tc.get_tt_account_number, tc._session, tc._account) = real


if __name__ == "__main__":
    main()
    print("FAIL: " + " ".join(_fails) if _fails else "ALL PASS")
    sys.stdout.flush()
    os._exit(1 if _fails else 0)
