#!/usr/bin/env python3
"""
tests/check_order_guard.py  v1.1
v1.1  2026-10-05  r473 / F5 — the fake account answers get_balances with ample
      buying power. F5 refuses a live post when balances are unreadable, so a
      fake without the call now refused every post and G2-G4 went red on a
      path that is correct. Nothing else changes.
v1.0  2026-10-04  r466 / B2 — AN ORDER THAT WAS SENT IS NEVER FORGOTTEN BY AN ERROR.

  🔴 Found by OTV4TEST's live-readiness audit, measured on mainline: in every
  live entry path an exception AFTER place_order returned was logged and
  swallowed — no refused rung, no order id kept, no working-order check — so
  the next tick could post the same intent again while the first order still
  worked: a double position the DB never sees.

  OFFLINE (fake async account, no network):
  G1  order_guard: a suspect order blocks its intent while LIVE, clears when
      CANCELLED, blocks and pages when FILLED, blocks when unreadable
  G2  the REAL _place_single_leg: place_order succeeds, confirmation RAISES ->
      the order is CANCELLED and remembered, and the next tick (order still
      LIVE) places NOTHING
  G3  ...once the broker says CANCELLED, the next tick posts again at a
      DIFFERENT (later) rung — the failed rung was refused
  G4  the REAL main._post_credit_vertical: confirmation raises -> cancel +
      remember, then the next call places nothing while the order is LIVE
  BORN RED on otv4 7562317: G1-G4 with no order_guard; and WITH order_guard but
  today's entry paths, G2 G3 G4 by behaviour (O1 then O2 re-posted at the same
  -0.95, nothing cancelled — the duplicate itself).

Run:  python3 tests/check_order_guard.py
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import config                                                         # noqa: E402
config.LOG_FILE = os.path.join(tempfile.mkdtemp(prefix="check_guard_"), "bot.log")
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


class _St:
    def __init__(self, name):
        self.name = name


class _Order:
    def __init__(self, oid, status="LIVE"):
        self.id, self.status = oid, _St(status)


class _Resp:
    def __init__(self, oid):
        self.errors, self.order = None, _Order(oid)


class _Acct:
    def __init__(self):
        self.placed, self.deleted, self.status, self.prices = [], [], "LIVE", []

    async def place_order(self, session, order, dry_run=False):
        oid = f"O{len(self.placed) + 1}"
        self.placed.append(oid)
        try:
            self.prices.append(float(order.price))
        except Exception:
            self.prices.append(None)
        return _Resp(oid)

    async def get_order(self, session, oid):
        if self.status == "BOOM":
            raise RuntimeError("unreadable")
        return _Order(oid, self.status)

    async def delete_order(self, session, oid):
        self.deleted.append(oid)

    async def get_balances(self, session, currency="USD"):           # F5 (r473)
        from types import SimpleNamespace
        return SimpleNamespace(derivative_buying_power=1_000_000.0)


class _C:
    def __init__(self, sym, bid, ask):
        self.symbol, self.bid, self.ask = sym, bid, ask


class _Sig:
    strategy = "RunawayContinuation"
    entry_premium = 1.00

    def __init__(self):
        self.contract = _C("QQQ   261005C00710000", 0.90, 1.10)


def main():
    try:
        from execution import order_guard as G
    except Exception as exc:                                          # noqa: BLE001
        for t in ("G1", "G2", "G3", "G4"):
            check(t, False, f"order_guard missing ({type(exc).__name__})")
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1

    # G1
    G.reset(); a = _Acct()
    G.after_failure("k1", _Order("X1"), object(), a, "probe")
    a.status = "LIVE"; ok_live, _ = G.clear_to_post("k1", object(), a)
    a.status = "FILLED"; ok_fill, w_fill = G.clear_to_post("k1", object(), a)
    a.status = "BOOM"; ok_boom, _ = G.clear_to_post("k1", object(), a)
    a.status = "CANCELLED"; ok_dead, _ = G.clear_to_post("k1", object(), a)
    ok_after, _ = G.clear_to_post("k1", object(), a)
    check("G1 suspect blocks while LIVE/FILLED/unreadable, clears when CANCELLED",
          a.deleted == ["X1"] and not ok_live and not ok_fill and not ok_boom
          and ok_dead and ok_after and "FILLED" in w_fill,
          f"deleted={a.deleted} live={ok_live} fill={ok_fill} boom={ok_boom} dead={ok_dead}")

    # G2/G3 — the real single-leg path
    import execution.entry_engine as EE
    from execution import ladder_registry as LR
    G.reset(); LR.reset_all()
    acct = _Acct()
    real = (EE.get_session, EE.get_account, EE.confirm_order_fill)
    try:
        EE.get_session, EE.get_account = (lambda: object()), (lambda: acct)

        def _boom(*a, **k):
            raise RuntimeError("confirm blew up after placement")
        EE.confirm_order_fill = _boom
        eng = EE.EntryEngine.__new__(EE.EntryEngine)
        eng.paper_trading = False
        r1 = eng._place_single_leg(_Sig(), 1)
        acct.status = "LIVE"
        r2 = eng._place_single_leg(_Sig(), 1)
        check("G2 an error after placement cancels + remembers; the next tick places NOTHING",
              r1 == (None, "", 0) and acct.deleted == ["O1"] and acct.placed == ["O1"]
              and r2 == (None, "", 0),
              f"r1={r1} placed={acct.placed} deleted={acct.deleted}")
        acct.status = "CANCELLED"
        eng._place_single_leg(_Sig(), 1)
        check("G3 once CANCELLED, it posts again at a DIFFERENT rung (the failed one refused)",
              len(acct.placed) == 2 and len(acct.prices) == 2 and acct.prices[0] != acct.prices[1],
              f"placed={acct.placed} prices={acct.prices}")
    except Exception as exc:                                          # noqa: BLE001
        check("G2/G3 single-leg path runs", False, f"{type(exc).__name__}: {exc}")
    finally:
        EE.get_session, EE.get_account, EE.confirm_order_fill = real

    # G4 — the real credit-vertical path
    try:
        import main as M
        import data.tasty_client as tc
        import execution.order_confirm as OC
        G.reset(); LR.reset_all()
        acct2 = _Acct()
        realc = (tc.get_session, tc.get_account, OC.confirm_order_fill)
        tc.get_session, tc.get_account = (lambda: object()), (lambda: acct2)
        OC.confirm_order_fill = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("confirm blew up"))
        sc = _C("QQQ   261005P00700000", 0.50, 0.60); lc = _C("QQQ   261005P00695000", 0.20, 0.30)
        key = "QQQ|open|credit_vertical"
        try:
            M._post_credit_vertical(sc, lc, 1, key, "credit_vertical", mark_fallback=0.30)
        except Exception:
            pass
        acct2.status = "LIVE"
        try:
            M._post_credit_vertical(sc, lc, 1, key, "credit_vertical", mark_fallback=0.30)
        except Exception:
            pass
        check("G4 credit vertical: cancel + remember, then nothing placed while LIVE",
              acct2.placed == ["O1"] and acct2.deleted == ["O1"],
              f"placed={acct2.placed} deleted={acct2.deleted}")
    except Exception as exc:                                          # noqa: BLE001
        check("G4 credit-vertical path runs", False, f"{type(exc).__name__}: {exc}")
    finally:
        try:
            tc.get_session, tc.get_account, OC.confirm_order_fill = realc
        except Exception:
            pass

    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — a placed order is never forgotten by an error")
    return 0


if __name__ == "__main__":
    sys.exit(main())
