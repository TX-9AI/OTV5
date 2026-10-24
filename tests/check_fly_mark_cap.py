#!/usr/bin/env python3
"""
tests/check_fly_mark_cap.py  v1.2
v1.2  2026-10-20  otv4 r495 (B4) — the fake account answers get_live_orders with an empty
      book. B4 posts no live entry until one working-order sweep is clean, so a fake
      without the call refused every fly and C2/C3 went red on a correct path, exactly
      as with F5 below. Nothing else changes.
v1.1  2026-10-05  otv4 r473 (F5) — the fake account answers get_balances with
      ample buying power. F5 refuses a live post when balances are unreadable,
      so a fake without the call refused every fly and C2/C3 went red on a
      correct path. Nothing else changes; OTV4TEST mirrors this with F5.
v1.0  2026-10-03  OTV4TEST r224 (FLY.1) — A BUTTERFLY ENTRY NEVER POSTS ABOVE ITS MARK, BID OR NO BID.

  The operator, 2026-10-03: "They should still not exceed mark on ladder
  entries, even no bid quotes" and "We won't accept a disadvantaged entry just
  because there is low interest."

  Drives the REAL EntryEngine._place_butterfly in live mode with the broker
  stubbed (the placer records every limit; the confirmer never fills) and the
  REAL ladder registry.
  C1  the cap is the mark floored to the cent; under one cent there is none
  C2  A NO-BID WING: legs whose structure bid is really -0.70 (floored to 0)
      and ask 1.00, true mark 0.15 - both attempts post 0.15. The defect:
      the walk posted 0.25 and the retry 0.16
  C3  a tight, healthy fly (mark 0.80): the walk's first rung below the mark
      is untouched; the retry is 0.80, not 0.81
  C4  a mark under one cent posts NOTHING
  C5  single legs, measured on the real ladder: no rung passes the mark on any
      of 32 quotes (no-bid and two-sided, buy and sell)

Run:  python3 tests/check_fly_mark_cap.py   (exit 0 green, 1 red)
"""
import glob as _glob
import os
import sys
import tempfile
import types

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_fly_mark_cap_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _leg(sym, bid, ask):
    return types.SimpleNamespace(symbol=sym, bid=bid, ask=ask, mark=(bid + ask) / 2.0, strike=0.0)


def main():
    import execution.entry_engine as EE
    from execution import ladder_registry as LR
    posted = []

    class _Acct:
        def place_order(self, session, order, dry_run=False):
            posted.append(round(-float(order.price), 2))
            return types.SimpleNamespace(errors=None, order=types.SimpleNamespace(id="X"))

        def get_balances(self, session, currency="USD"):              # F5 (r473)
            return types.SimpleNamespace(derivative_buying_power=1_000_000.0)

        def get_live_orders(self, session):                            # B4 (r495)
            return []
    sv = (EE.get_session, EE.get_account, EE.confirm_order_fill)
    EE.get_session = lambda: object()
    EE.get_account = lambda: _Acct()
    EE.confirm_order_fill = lambda *a, **k: types.SimpleNamespace(
        filled=False, net_price=None, quantity=0, working_order_id=None, detail="dead", order_id="")

    def fly(lo, ce, up, mark, tag):
        LR.reset_all()
        del posted[:]
        eng = EE.EntryEngine.__new__(EE.EntryEngine)
        eng.paper_trading = False
        sig = types.SimpleNamespace(lower_contract=_leg(f"L{tag}", *lo), center_contract=_leg(f"C{tag}", *ce),
                                    upper_contract=_leg(f"U{tag}", *up), net_debit=mark)
        out = eng._place_butterfly(sig, 1)
        return list(posted), out
    try:
        cap = getattr(EE.EntryEngine, "_mark_cap", None)
        check("C1 the cap is the mark floored to the cent: 0.25, 0.257 -> 0.25; 0.009 and None -> no cap",
              cap is not None and (cap(0.25), cap(0.257), cap(0.009), cap(None)) == (0.25, 0.25, None, None),
              "EntryEngine._mark_cap absent" if cap is None else str((cap(0.25), cap(0.257), cap(0.009), cap(None))))
    except Exception as exc:                                  # noqa: BLE001
        check("C1 (did not run)", False, f"{type(exc).__name__}: {exc}")
    try:
        p2, _o = fly((4.90, 5.10), (2.50, 2.80), (0.00, 0.90), 0.15, "a")
        check("C2 a no-bid wing, true mark 0.15: both attempts post 0.15 - nothing above the mark",
              len(p2) == 2 and max(p2) <= 0.15 + 1e-9 and p2 == [0.15, 0.15], f"posted {p2}")
        p3, _o = fly((5.00, 5.02), (2.60, 2.62), (1.00, 1.02), 0.80, "b")
        check("C3 a tight fly, mark 0.80: the first rung stays below the mark; the retry is 0.80, not 0.81",
              len(p3) == 2 and p3[0] < 0.80 and p3[1] == 0.80, f"posted {p3}")
        p4, o4 = fly((0.02, 0.03), (0.01, 0.02), (0.00, 0.01), 0.004, "c")
        check("C4 a mark under one cent posts nothing", p4 == [] and o4 == (None, "", 0), f"posted {p4}, returned {o4}")
    except Exception as exc:                                  # noqa: BLE001
        check("C2 (did not run)", False, f"{type(exc).__name__}: {exc}")
    finally:
        EE.get_session, EE.get_account, EE.confirm_order_fill = sv
    try:
        from execution.entry_ladder import LadderState
        worst, n = 0.0, 0
        for sym in ("QQQ", "SOFI", "AVGO", "SPX"):
            for side in ("buy", "sell"):
                for bid, ask in ((0.0, 0.10), (0.0, 0.35), (0.0, 3.40), (1.95, 2.35)):
                    mark = (bid + ask) / 2.0
                    st = LadderState(side, sym); prev = None
                    for _ in range(60):
                        got = st.next_price(bid, ask)
                        if not got or got[0] == prev:
                            break
                        prev = got[0]; st.refuse(prev)
                        worst = max(worst, (prev - mark) if side == "buy" else (mark - prev))
                    n += 1
        check(f"C5 single legs: across {n} quotes, bid or no bid, no rung passes the mark", worst <= 1e-9 and n == 32,
              f"worst {worst:+.4f} over {n}")
    except Exception as exc:                                  # noqa: BLE001
        check("C5 (did not run)", False, f"{type(exc).__name__}: {exc}")
    if FAILED:
        print(f"\nRED — {len(FAILED)} check(s): {FAILED}")
        return 1
    print("\nGREEN — no butterfly entry posts above its mark; single legs never did")
    return 0


if __name__ == "__main__":
    sys.exit(main())
