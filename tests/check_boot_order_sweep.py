#!/usr/bin/env python3
"""
tests/check_boot_order_sweep.py  v1.0
v1.0  2026-10-20  r495 / B4 — A RESTART CANCELS ITS INSTRUMENT'S LEFTOVER WORKING ORDERS
      BEFORE IT POSTS.

  order_guard (B2) is in memory and B1 adopts positions, not working orders, so a
  LIVE restart while an entry order was working forgot it and the next tick could
  post the same intent again. Question from OTV4TEST (MSG-QQQ-1020-15); measured
  on 2c33f1c: no startup path read live orders (MSG-1REP-1020-06).

  S1  sweep_working cancels this instrument's WORKING orders (by underlying or by
      leg root) and nothing else: another instrument, a FILLED/CANCELLED order
  S2  SPX family: an SPXW-root order is the SPX box's; a QQQ order is not
  S3  the ids the box still tracks are KEPT: a resting offer's, an open row's
      live_exit_state order_id and last_order_id (B3)
  S4  a fresh process (sweep pending): clear_to_post sweeps first; an unreadable
      order book posts NOTHING and cancels nothing; once readable the leftover is
      cancelled, the post is cleared, and later posts do not sweep again
  S5  a failed cancel blocks entries; it pages ONCE across repeated attempts, and
      the recovery pages that entries resume
  S6  an unreadable kept-id set cancels NOTHING and blocks
  S7  main._recover_open_position calls boot_sweep under `not state.paper_trading`,
      BEFORE _reconcile_with_broker (a part-fill is adopted by the same start)
  S8  the REAL single-leg entry path on a fresh process: the leftover is cancelled
      BEFORE place_order, then the entry posts
  (OTV4TEST critique MSG-QQQ-1020-18:)
  S9  clean only when every cancelled id READS dead: an id still Cancel Requested at
      the deadline blocks (heartbeat touched while polling); once Cancelled, clean
  S10 an order of the instrument already in Cancel/Replace Requested is NOT
      re-cancelled and the book is not clean while it is there
  S11 a leftover that FILLED is paged by id; reconcile OFF blocks, reconcile ON clean
  S12 the REAL condor roll, guard blocked: nothing is closed or posted (whole or none)
  S13 the REAL condor tent, guard blocked: HOLD — nothing is closed, no hedge is
      bought, it retries next tick (operator 10-20: "A. Hold")

Run:  python3 tests/check_boot_order_sweep.py   (exit 0 green, 1 red)
"""
import ast
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["OT_INSTRUMENT"] = "QQQ"
import config                                                         # noqa: E402
config.LOG_FILE = os.path.join(tempfile.mkdtemp(prefix="check_bsweep_"), "bot.log")
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name.split()[0])


class _St:
    def __init__(self, value):
        self.value = value


class _Leg:
    def __init__(self, sym):
        self.symbol = sym


class _O:
    def __init__(self, oid, status="Live", und=None, legs=()):
        self.id, self.status = oid, _St(status)
        self.underlying_symbol = und
        self.legs = [_Leg(s) for s in legs]


class _Resp:
    def __init__(self, oid):
        self.errors, self.order = None, _O(oid)


class _Acct:
    def __init__(self, live=(), fail_read=False, fail_delete=(), after_cancel="Cancelled"):
        self.live, self.fail_read, self.fail_delete = list(live), fail_read, set(fail_delete)
        self.after_cancel = after_cancel
        self.deleted, self.placed, self.reads, self.events = [], [], 0, []

    async def get_live_orders(self, session):
        self.reads += 1
        if self.fail_read:
            raise RuntimeError("order book unreadable")
        return list(self.live)

    async def delete_order(self, session, oid):
        if oid in self.fail_delete:
            raise RuntimeError("cancel refused")
        self.deleted.append(oid)
        self.events.append(("delete", oid))

    async def place_order(self, session, order, dry_run=False):
        oid = f"N{len(self.placed) + 1}"
        self.placed.append(oid)
        self.events.append(("place", oid))
        return _Resp(oid)

    async def get_order(self, session, oid):
        return _O(oid, self.after_cancel if oid in self.deleted else "Live")

    async def get_balances(self, session, currency="USD"):
        from types import SimpleNamespace
        return SimpleNamespace(derivative_buying_power=1_000_000.0)


def main():
    from execution import order_guard as G
    pages = []
    G._page = pages.append
    no_keep = lambda: set()                                           # noqa: E731
    real_keep = getattr(G, "_kept_order_ids", None)
    if real_keep is None:                     # base: no sweep; S7/S8 still judge the paths
        for t in ("S1", "S2", "S3", "S4", "S5", "S6", "S9", "S10", "S11"):
            check(f"{t} order_guard.sweep_working", False, "missing")
        _paths(G, None)
        _condor(G)
        print(f"\nRED — {len(PROBLEMS)} failed: {', '.join(PROBLEMS)}")
        return 1

    # S1
    G.reset(boot_clean=False); G._kept_order_ids = no_keep
    a = _Acct([_O("A", "Live", "QQQ"), _O("B", "Received", None, ["QQQ   261020C00700000"]),
               _O("C", "Live", "SPY"), _O("D", "Filled", "QQQ"), _O("E", "Cancelled", "QQQ"),
               _O("F", "In Flight", "QQQ")])
    ok, n, why = G.sweep_working(object(), a)
    check("S1 cancels this instrument's WORKING orders only (underlying or leg root)",
          ok and sorted(a.deleted) == ["A", "B", "F"] and n == 3, f"ok={ok} deleted={a.deleted} {why}")

    # S2
    G.reset(boot_clean=False)
    a = _Acct([_O("W", "Live", None, ["SPXW  261020P07700000"]), _O("X", "Live", "SPX"),
               _O("Q", "Live", "QQQ")])
    ok, n, _ = G.sweep_working(object(), a, instrument="SPX")
    check("S2 SPX box: SPX and SPXW orders are its own, QQQ's is not",
          ok and sorted(a.deleted) == ["W", "X"], f"deleted={a.deleted}")

    # S3 — the real _kept_order_ids over patched readers
    G._kept_order_ids = real_keep
    import execution.resting_orders as RO
    import database.trade_logger as TL
    real_ro, real_tl = RO.working, TL.get_trade_logger

    class _TL:
        def get_open_trades(self):
            return [{"live_exit_state": '{"fills": [[1, 1.2]], "order_id": "X1", "last_order_id": "X0"}'},
                    {"live_exit_state": None}, {"live_exit_state": "not json"}]
    try:
        RO.working = lambda d, strategy="": [{"order_id": "R1"}]
        TL.get_trade_logger = lambda: _TL()
        G.reset(boot_clean=False)
        a = _Acct([_O(i, "Live", "QQQ") for i in ("R1", "X1", "X0", "Z9")])
        ok, n, why = G.sweep_working(object(), a)
        check("S3 a resting offer and an open row's exit order ids are KEPT; the rest cancelled",
              ok and a.deleted == ["Z9"] and "kept 3" in why, f"deleted={a.deleted} {why}")

        # S6
        def _boom():
            raise RuntimeError("trades.db locked")
        TL.get_trade_logger = _boom
        G.reset(boot_clean=False); pages.clear()
        a = _Acct([_O("Z9", "Live", "QQQ")])
        ok, n, why = G.sweep_working(object(), a)
        ok2, w2 = G.clear_to_post("k", object(), a)
        check("S6 unreadable kept ids: cancels NOTHING, entries blocked",
              not ok and a.deleted == [] and not ok2 and "boot sweep" in w2, f"deleted={a.deleted} {why}")
    finally:
        RO.working, TL.get_trade_logger = real_ro, real_tl
    G._kept_order_ids = no_keep

    # S4
    G.reset(boot_clean=False); pages.clear()
    a = _Acct([_O("L1", "Live", "QQQ")], fail_read=True)
    ok1, w1 = G.clear_to_post("k", object(), a)
    a.fail_read = False
    ok2, _ = G.clear_to_post("k", object(), a)
    reads = a.reads
    ok3, _ = G.clear_to_post("k", object(), a)
    check("S4 fresh process: unreadable book posts nothing; then the leftover is cancelled "
          "and later posts do not re-sweep",
          not ok1 and "boot sweep" in w1 and ok2 and ok3 and a.deleted == ["L1"] and a.reads == reads == 2,
          f"ok={ok1, ok2, ok3} deleted={a.deleted} reads={a.reads}")

    # S5
    G.reset(boot_clean=False); pages.clear()
    a = _Acct([_O("L1", "Live", "QQQ"), _O("L2", "Live", "QQQ")], fail_delete={"L2"})
    r = [G.clear_to_post("k", object(), a)[0] for _ in range(3)]
    blocked_pages = len(pages)
    a.fail_delete.clear()
    ok, _ = G.clear_to_post("k", object(), a)
    check("S5 a failed cancel blocks; pages once over 3 attempts; recovery pages and clears",
          r == [False] * 3 and blocked_pages == 1 and ok and len(pages) >= 2
          and "L2" in a.deleted, f"r={r} pages={pages} deleted={a.deleted}")

    # S9-S11 — the confirmation poll (deadline shortened for the gate)
    G.CANCEL_CONFIRM_S, G._POLL_S = 0.3, 0.05
    import utils.heartbeat as HB
    touches = []
    real_touch = HB.touch
    HB.touch = lambda note="", file_path=None: touches.append(note) or True
    try:
        G.reset(boot_clean=False); pages.clear()
        a = _Acct([_O("P1", "Live", "QQQ")], after_cancel="Cancel Requested")
        ok1, w1 = G.clear_to_post("k", object(), a)
        a.after_cancel = "Cancelled"; a.live = [_O("P1", "Cancelled", "QQQ")]
        ok2, _ = G.clear_to_post("k", object(), a)
        check("S9 a cancel that has not READ dead blocks (heartbeat polled); once Cancelled, clean",
              not ok1 and "not confirmed" in w1 and ok2 and "boot order sweep" in touches,
              f"ok1={ok1} w1={w1} ok2={ok2} touches={touches[:2]}")

        G.reset(boot_clean=False)
        a = _Acct([_O("Q1", "Cancel Requested", "QQQ"), _O("Q2", "Replace Requested", "QQQ")])
        ok, n, why = G.sweep_working(object(), a)
        check("S10 Cancel/Replace Requested: not re-cancelled, and the book is not clean",
              not ok and a.deleted == [] and "Q1" in why and "Q2" in why, f"ok={ok} {why}")

        import config as CFG
        real_rec = getattr(CFG, "BROKER_RECONCILE_ENABLED", None)
        try:
            CFG.BROKER_RECONCILE_ENABLED = False
            G.reset(boot_clean=False); pages.clear()
            a = _Acct([_O("F1", "Live", "QQQ")], after_cancel="Filled")
            ok_off, _, why_off = G.sweep_working(object(), a)
            paged_off = any("F1" in p and "FILLED" in p for p in pages)
            CFG.BROKER_RECONCILE_ENABLED = True
            G.reset(boot_clean=False); pages.clear()
            a = _Acct([_O("F1", "Live", "QQQ")], after_cancel="Filled")
            ok_on, _, _ = G.sweep_working(object(), a)
            paged_on = any("F1" in p and "adopts" in p for p in pages)
        finally:
            CFG.BROKER_RECONCILE_ENABLED = real_rec
        check("S11 a FILLED leftover is paged by id; reconcile OFF blocks, ON is clean",
              paged_off and not ok_off and paged_on and ok_on,
              f"off={ok_off} {why_off} paged={paged_off} on={ok_on} paged={paged_on}")
    finally:
        HB.touch = real_touch

    _paths(G, real_keep)
    _condor(G)

    print()
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {', '.join(PROBLEMS)}")
        return 1
    print("GREEN")
    return 0


def _paths(G, real_keep):
    # S7 — AST on the real main._recover_open_position
    try:
        tree = ast.parse(open(os.path.join(ROOT, "main.py"), encoding="utf-8").read())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "_recover_open_position")
        sweep_ln = recon_ln = None
        guarded = False
        for node in ast.walk(fn):
            if isinstance(node, ast.If) and "not state.paper_trading" in ast.unparse(node.test):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and ast.unparse(sub.func).endswith("boot_sweep"):
                        guarded, sweep_ln = True, sub.lineno
            if isinstance(node, ast.Call) and ast.unparse(node.func) == "_reconcile_with_broker":
                recon_ln = node.lineno
        check("S7 startup: boot_sweep runs LIVE-only, before the broker reconcile",
              guarded and sweep_ln and recon_ln and sweep_ln < recon_ln,
              f"guarded={guarded} sweep={sweep_ln} reconcile={recon_ln}")
    except Exception as exc:                                          # noqa: BLE001
        check("S7 startup: boot_sweep runs LIVE-only, before the broker reconcile", False,
              f"{type(exc).__name__}: {exc}")

    # S8 — the real single-leg path on a fresh process
    import execution.entry_engine as EE
    from execution import ladder_registry as LR

    class _C:
        def __init__(self, sym, bid, ask):
            self.symbol, self.bid, self.ask = sym, bid, ask

    class _Sig:
        strategy = "RunawayContinuation"
        entry_premium = 1.00

        def __init__(self):
            self.contract = _C("QQQ   261020C00710000", 0.90, 1.10)

    try:
        G.reset(boot_clean=False)
    except TypeError:
        G.reset()
    LR.reset_all()
    acct = _Acct([_O("OLD", "Live", "QQQ")])
    real = (EE.get_session, EE.get_account, EE.confirm_order_fill)
    try:
        EE.get_session, EE.get_account = (lambda: object()), (lambda: acct)
        from execution.order_confirm import EntryFill
        EE.confirm_order_fill = lambda *a, **k: EntryFill(filled=False, detail="probe: not filled")
        eng = EE.EntryEngine.__new__(EE.EntryEngine)
        eng.paper_trading = False
        try:
            eng._place_single_leg(_Sig(), 1)
        except Exception:                                             # noqa: BLE001
            pass
        check("S8 real single-leg entry, fresh process: the leftover is cancelled BEFORE the post",
              acct.events[:1] == [("delete", "OLD")] and ("place", "N1") in acct.events,
              f"events={acct.events}")
    finally:
        EE.get_session, EE.get_account, EE.confirm_order_fill = real
        if real_keep is not None:
            G._kept_order_ids = real_keep



def _condor(G):
    """S12/S13 — the real roll and tent with the guard blocked (a pending book)."""
    import types
    import strategy.condor_roll as CR
    import execution.exit_engine as XE
    import data.tasty_client as TC
    calls = []

    class _XE:
        def place_exit_order(self, rec, reason, mark_price=None):
            calls.append(("exit", rec.get("trade_id"), reason))
            return types.SimpleNamespace(confirmed=True, fill_price=0.10, detail="")
    acct = _Acct([_O("STUCK", "Cancel Requested", "QQQ")])
    acct.place_order = lambda *a, **k: calls.append(("place",)) or _Resp("N")
    real = (XE.get_exit_engine, TC.get_session, TC.get_account)
    XE.get_exit_engine = lambda paper=False: _XE()
    TC.get_session, TC.get_account = (lambda: object()), (lambda: acct)
    state = types.SimpleNamespace(paper_trading=False)
    tested = {"trade_id": "T", "contracts": 1, "credit_received": 1.0}
    untested = {"trade_id": "U", "contracts": 1, "credit_received": 1.0}
    plan = types.SimpleNamespace(contracts=1, close_cost=0.10, roll_credit=0.50,
                                 untested_side="call", new_short_strike=1.0, new_long_strike=2.0)

    class _PM:
        def remove_record(self, tid):
            calls.append(("remove", tid))
    try:
        try:
            G.reset(boot_clean=False)
        except TypeError:
            G.reset()
        calls.clear()
        try:
            r = CR._execute_roll(_PM(), tested, untested, plan, state, None)
        except Exception as exc:                                      # noqa: BLE001
            r = f"raised {type(exc).__name__}"
        check("S12 the REAL roll, guard blocked: nothing closed, nothing posted",
              r is False and calls == [], f"r={r} calls={calls}")

        try:
            G.reset(boot_clean=False)
        except TypeError:
            G.reset()
        calls.clear()
        winner = {"trade_id": "W", "contracts": 1, "credit_received": 1.0}
        keep = {"trade_id": "K", "contracts": 1, "credit_received": 1.0}
        real_lv = CR._leg_value
        CR._leg_value = lambda leg, chain: 0.10
        try:
            try:
                CR._execute_tent(_PM(), winner, keep, object(), 0.20, 1.0, state, None)
            except Exception as exc:                                  # noqa: BLE001
                calls.append(("raised", type(exc).__name__))
        finally:
            CR._leg_value = real_lv
        check("S13 the REAL tent, guard blocked: HOLD - nothing closed, no hedge bought",
              calls == [], f"calls={calls}")
    finally:
        XE.get_exit_engine, TC.get_session, TC.get_account = real


if __name__ == "__main__":
    sys.exit(main())
