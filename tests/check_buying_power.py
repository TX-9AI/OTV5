#!/usr/bin/env python3
"""tests/check_buying_power.py  v1.0
F5 — A LIVE ENTRY IS NOT POSTED IF THE ACCOUNT CANNOT PAY FOR IT.

v1.0  2026-10-05  r473. Found by OTV4TEST's live-readiness audit (F5): no live
      entry path read buying power. Operator ruling: live orders only.

OFFLINE: a fake async account whose get_balances returns a set
derivative_buying_power (or raises); no network. Drives the REAL entry paths.

  P1  buying_power.affordable: enough -> ok; short -> refused with both figures;
      get_balances raising -> refused (fails closed); one page per episode,
      re-armed by a good read
  P2  the REAL _place_single_leg: buying power below limit x n x 100 -> NOTHING
      placed; ample -> placed (control)
  P3  the REAL _place_butterfly: buying power below cap x n x 100 -> nothing
      placed; ample -> placed (control)
  P4  the REAL main._post_credit_vertical: needs (width - credit) x n x 100;
      short -> nothing placed; ample -> placed (control)
  P5  the REAL _place_standing_offer: short -> nothing placed. (Refusal side
      only: the placed side records the offer in the local store, which this
      check must not write.)
  P6  UNCHANGED: paper never reads balances

Run:  python3 tests/check_buying_power.py   (needs the venv's tastytrade)
"""
import os
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


class _Acct:
    def __init__(self, bp):
        self.bp, self.placed, self.balance_reads = bp, [], 0

    async def get_balances(self, session, currency="USD"):
        self.balance_reads += 1
        if isinstance(self.bp, Exception):
            raise self.bp
        return types.SimpleNamespace(derivative_buying_power=self.bp)

    async def place_order(self, session, order, dry_run=False):
        self.placed.append(float(order.price))
        return types.SimpleNamespace(errors=None, order=types.SimpleNamespace(id=f"O{len(self.placed)}"))

    async def get_order(self, session, oid):
        return types.SimpleNamespace(id=oid, status=types.SimpleNamespace(name="CANCELLED"))

    async def delete_order(self, session, oid):
        return None


def _c(sym, bid, ask, strike=0.0):
    return types.SimpleNamespace(symbol=sym, bid=bid, ask=ask, mark=(bid + ask) / 2.0, strike=strike)


def main():
    print("check_buying_power")
    try:
        import config
        config.LOG_FILE = os.path.join(tempfile.mkdtemp(prefix="check_bp_"), "bot.log")
        import tastytrade  # noqa: F401
    except ImportError as exc:
        print(f"NOT RUN — this interpreter cannot import the trading stack ({exc}); run under the venv")
        return 2
    try:
        from execution import buying_power as BP
    except ImportError as exc:
        for t in ("P1", "P2", "P3", "P4", "P5", "P6"):
            check(t, False, f"execution.buying_power missing ({exc})")
        print(f"\nRED — {len(PROBLEMS)} failed: {', '.join(PROBLEMS)}")
        return 1
    import execution.entry_engine as EE
    from execution import ladder_registry as LR
    from execution import order_guard as G
    pages = []
    BP._page.__globals__["_PAGED"].clear()
    real_page = BP._page

    def rec_page(kind, text):
        before = len(BP._PAGED)
        real_page(kind, text)
        if len(BP._PAGED) > before:
            pages.append(kind)
    BP._page = rec_page
    import notifications.alert_manager as AM
    AM.get_alert_manager = lambda: types.SimpleNamespace(_send=lambda t: None)

    # P1
    ok1, w1 = BP.affordable(500, None, _Acct(1000), "probe")
    ok2, w2 = BP.affordable(1500, None, _Acct(1000), "probe")
    BP.affordable(1500, None, _Acct(1000), "probe")              # same episode: no 2nd page
    ok3, w3 = BP.affordable(10, None, _Acct(RuntimeError("down")), "probe")
    BP.affordable(500, None, _Acct(1000), "probe")               # good read re-arms
    BP.affordable(1500, None, _Acct(1000), "probe")              # new episode: pages again
    check("P1 enough ok; short refused with both figures; unreadable refused; one page per episode",
          ok1 and not ok2 and "1,500" in w2 and "1,000" in w2 and not ok3
          and pages == ["short", "unreadable", "short"],
          f"ok={ok1,ok2,ok3} w2={w2!r} pages={pages}")

    sv = (EE.get_session, EE.get_account, EE.confirm_order_fill)
    dead = lambda *a, **k: types.SimpleNamespace(filled=False, net_price=None, quantity=0,
                                                 working_order_id=None, detail="dead", order_id="")
    try:
        EE.get_session, EE.confirm_order_fill = (lambda: object()), dead
        eng = EE.EntryEngine.__new__(EE.EntryEngine)
        eng.paper_trading = False

        def single(bp):
            LR.reset_all(); G.reset(); BP.reset()
            a = _Acct(bp); EE.get_account = lambda: a
            sig = types.SimpleNamespace(strategy="RunawayContinuation", strategy_name="RunawayContinuation",
                                        entry_premium=1.00, contract=_c("QQQ   261005C00710000", 0.90, 1.10))
            eng._place_single_leg(sig, 10)          # ~1.00 x 10 x 100 = ~$1,000
            return a
        a_short, a_ok = single(500.0), single(50_000.0)
        check("P2 single leg: $500 buying power for a ~$1,000 entry -> nothing placed; ample -> placed",
              a_short.placed == [] and a_short.balance_reads == 1 and len(a_ok.placed) >= 1,
              f"short placed={a_short.placed} reads={a_short.balance_reads}; ample placed={a_ok.placed}")

        def fly(bp):
            LR.reset_all(); G.reset(); BP.reset()
            a = _Acct(bp); EE.get_account = lambda: a
            sig = types.SimpleNamespace(lower_contract=_c("L", 5.00, 5.02), center_contract=_c("C", 2.60, 2.62),
                                        upper_contract=_c("U", 1.00, 1.02), net_debit=0.80)
            eng._place_butterfly(sig, 5)            # cap 0.80 x 5 x 100 = $400
            return a
        f_short, f_ok = fly(300.0), fly(50_000.0)
        check("P3 butterfly: $300 for a $400 cap -> nothing placed; ample -> placed",
              f_short.placed == [] and len(f_ok.placed) >= 1,
              f"short placed={f_short.placed}; ample placed={f_ok.placed}")

        LR.reset_all(); G.reset(); BP.reset()
        a5 = _Acct(1.0); EE.get_account = lambda: a5
        osig = types.SimpleNamespace(strategy="ORBStrategy", strategy_name="ORBStrategy",
                                     entry_premium=2.00, contract=_c("QQQ   261005C00710000", 1.95, 2.05))
        eng._place_standing_offer(osig, 3)
        check("P5 standing ORB offer: $1 of buying power -> nothing placed",
              a5.placed == [] and a5.balance_reads == 1,
              f"placed={a5.placed} reads={a5.balance_reads}")

        pa = _Acct(50_000.0); EE.get_account = lambda: pa
        engp = EE.EntryEngine.__new__(EE.EntryEngine); engp.paper_trading = True
        try:
            engp._place_single_leg(types.SimpleNamespace(
                strategy="RunawayContinuation", strategy_name="RunawayContinuation",
                entry_premium=1.00, contract=_c("QQQ   261005C00710000", 0.90, 1.10)), 1)
        except Exception:                                           # noqa: BLE001
            pass
        check("P6 paper never reads balances", pa.balance_reads == 0, f"reads={pa.balance_reads}")
    except Exception as exc:                                        # noqa: BLE001
        check("P2-P6 entry paths run", False, f"{type(exc).__name__}: {exc}")
    finally:
        EE.get_session, EE.get_account, EE.confirm_order_fill = sv

    # P4 — credit vertical through main
    try:
        import main as M
        import data.tasty_client as tc
        import execution.order_confirm as OC
        realc = (tc.get_session, tc.get_account, OC.confirm_order_fill)

        def vert(bp):
            LR.reset_all(); G.reset(); BP.reset()
            a = _Acct(bp)
            tc.get_session, tc.get_account = (lambda: object()), (lambda: a)
            OC.confirm_order_fill = dead
            sc = _c("QQQ   261005P00700000", 0.50, 0.60, 700.0)
            lc = _c("QQQ   261005P00695000", 0.20, 0.30, 695.0)
            M._post_credit_vertical(sc, lc, 2, "QQQ|open|credit_vertical", "credit_vertical",
                                    mark_fallback=0.30)   # (5 - ~0.30) x 2 x 100 = ~$940
            return a
        try:
            v_short, v_ok = vert(500.0), vert(50_000.0)
            check("P4 credit vertical: $500 for ~$940 of width less credit -> nothing placed; ample -> placed",
                  v_short.placed == [] and v_short.balance_reads == 1 and len(v_ok.placed) >= 1,
                  f"short placed={v_short.placed} reads={v_short.balance_reads}; ample placed={v_ok.placed}")
        finally:
            tc.get_session, tc.get_account, OC.confirm_order_fill = realc
    except Exception as exc:                                        # noqa: BLE001
        check("P4 credit-vertical path runs", False, f"{type(exc).__name__}: {exc}")

    print()
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {', '.join(p.split()[0] for p in PROBLEMS)}")
        return 1
    print("GREEN — every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
