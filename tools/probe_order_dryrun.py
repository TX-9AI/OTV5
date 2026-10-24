#!/usr/bin/env python3
"""tools/probe_order_dryrun.py — v1.2
ASK THE BROKER WHAT IT WOULD DO WITH OUR ORDERS — DRY RUN ONLY, NOTHING IS PLACED, NO MONEY MOVES.

v1.2 (2026-10-04) — OTV4TEST r242 (LIVE.1 B0 mirror) — every broker call goes through data.tasty_client.sdk_result, the helper
      mainline r463 added (check_sdk_async A4 reads every non-test file): the probe now proves the bot's OWN helper live.
v1.1 (2026-10-04) — OTV4TEST r240 (PRB.2) — the two questions v1.0 left open on SPX (SPX-TEST's run, 14:06 ET):
      the chain listing now adds every third-Friday expiry in the next ~70 days (where SPX lists its AM monthly
      beside SPXW - the AM literal and both roots on one date), and the vertical is also dry-run at 3.10 and
      3.05 (does a complex order go to dimes at $3?). Still dry_run=True only; tests/check_probe_dryrun.py unchanged.
v1.0 (2026-10-04) — OTV4TEST r239 (PRB.2). The operator, 2026-10-04 13:57 ET: "Yes, to the dry run if you
      can do it without actually spending money." Two audits that day (QQQ-TEST generic, SPX-TEST SPX) left
      questions only the broker can answer, and found B0: on tastytrade 13.x every Account method is a
      coroutine, while data/tasty_client.get_account() calls Account.get WITHOUT awaiting it - so a live
      box caches a coroutine and every order call fails (proven offline; 1-REPORTER confirmed on a mainline
      box, 13.0.0). This probe AWAITS every call, so it also proves the corrected pattern against the real API.

WHAT IT ASKS (each order is account.place_order(..., dry_run=True): the broker validates and prices it and
returns errors / warnings / buying-power effect / fees; it is NOT an order and cannot fill):
  1. the chain's roots and settlement types for the next expiries (SPX: is "AM" / "PM" the literal value,
     and do SPX AM and SPXW share a date?)
  2. a 1-lot single BUY_TO_OPEN on a far OTM put at 0.05 (on any grid) and 0.07 (off a 0.05 grid)
  3. the same at 3.10 and 3.05 (the SPX >= 3.00 dime rule)
  4. a 1-lot debit put vertical at 0.05 / 0.07 / 3.10 / 3.05 (the complex-order increment, both sides of $3)
SAFETY, by construction: the ONLY call to place_order is in _dry(), which passes the literal dry_run=True;
tests/check_probe_dryrun.py proves by AST that no other place_order call exists and that dry_run is never set to anything but True.
It prints no account number and no balance - only the CHANGE in buying power, the effect, and fees.
Run ONLY through the r176 wrapper (it carries the bot's TT_* keys, never prints them):
    /home/ubuntu/options-trader/venv/bin/python /home/ubuntu/options-trader/tools/run_with_bot_env.py probe_order_dryrun.py
"""
import os
import sys
from collections import Counter
from datetime import date
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tastytrade.account import Account                                          # noqa: E402
from tastytrade.instruments import get_option_chain, OptionType, InstrumentType  # noqa: E402
from tastytrade.order import NewOrder, Leg, OrderAction, OrderType, OrderTimeInForce  # noqa: E402
from data.tasty_client import get_session, get_tt_account_number, sdk_result     # noqa: E402

SYM = (os.environ.get("OT_INSTRUMENT") or "").strip().upper()


def _dry(account, session, order):
    """THE ONLY place_order CALL IN THIS FILE. dry_run is the literal True. r242: through sdk_result (B0)."""
    return sdk_result(account.place_order(session, order, dry_run=True))


def _put_leg(sym, action):
    return Leg(instrument_type=InstrumentType.EQUITY_OPTION, symbol=sym, action=action, quantity=1)


def _report(label, resp=None, exc=None):
    if exc is not None:
        print(f"  {label:34s} REJECTED  {type(exc).__name__}: {str(exc)[:160]}")
        return
    errs = getattr(resp, "errors", None) or []
    warns = getattr(resp, "warnings", None) or []
    bpe = getattr(resp, "buying_power_effect", None)
    fee = getattr(resp, "fee_calculation", None)
    print(f"  {label:34s} {'ERRORS' if errs else 'ACCEPTED'}"
          f"  bp_change={getattr(bpe, 'change_in_buying_power', '?')} effect={getattr(bpe, 'effect', '?')}"
          f"  fees={getattr(fee, 'total_fees', '?')}")
    for e in errs:
        print(f"      error:   {str(e)[:160]}")
    for w in warns:
        print(f"      warning: {str(w)[:160]}")


def main() -> int:
    if not SYM:
        print("probe_order_dryrun: no OT_INSTRUMENT - run it through tools/run_with_bot_env.py")
        return 2
    session = get_session()
    account = sdk_result(Account.get(session, get_tt_account_number()))  # the B0 helper, exactly as the bot calls it
    print(f"account object: {type(account).__name__} (B0 check: must be 'Account', not 'coroutine')")
    chain = sdk_result(get_option_chain(session, SYM))
    future = sorted(d for d in chain if d >= date.today())
    third_fri = [d for d in future if d.weekday() == 4 and 15 <= d.day <= 21 and (d - date.today()).days <= 70]
    dates = sorted(set(future[:8]) | set(third_fri))
    print(f"\n{SYM} chain - roots / settlement by expiry (next {len(dates)}):")
    for d in dates:
        c = Counter((getattr(o, "root_symbol", "?"), getattr(o, "settlement_type", "?")) for o in chain[d])
        print(f"  {d}  " + "  ".join(f"{r}/{s}={n}" for (r, s), n in sorted(c.items())))
    d0 = dates[0]
    puts = [o for o in chain[d0] if o.option_type == OptionType.PUT
            and (SYM != "SPX" or getattr(o, "root_symbol", "") == "SPXW")]
    puts.sort(key=lambda o: float(o.strike_price))
    if len(puts) < 8:
        print(f"too few puts on {d0} to pick a far OTM pair ({len(puts)})")
        return 3
    hi, lo = puts[len(puts) // 6], puts[len(puts) // 6 - 1]                    # far OTM, adjacent strikes
    print(f"\ndry-run legs on {d0}: long {hi.symbol!r} / short {lo.symbol!r} (1 lot each)")
    print("ORDERS (dry_run=True - validated and priced by the broker, never placed):")
    for px in ("0.05", "0.07", "3.10", "3.05"):
        o = NewOrder(time_in_force=OrderTimeInForce.DAY, order_type=OrderType.LIMIT,
                     price=Decimal("-" + px), legs=[_put_leg(hi.symbol, OrderAction.BUY_TO_OPEN)])
        try:
            _report(f"single BUY_TO_OPEN @ {px}", _dry(account, session, o))
        except Exception as exc:  # noqa: BLE001
            _report(f"single BUY_TO_OPEN @ {px}", exc=exc)
    for px in ("0.05", "0.07", "3.10", "3.05"):
        o = NewOrder(time_in_force=OrderTimeInForce.DAY, order_type=OrderType.LIMIT,
                     price=Decimal("-" + px),
                     legs=[_put_leg(hi.symbol, OrderAction.BUY_TO_OPEN),
                           _put_leg(lo.symbol, OrderAction.SELL_TO_OPEN)])
        try:
            _report(f"vertical debit @ {px}", _dry(account, session, o))
        except Exception as exc:  # noqa: BLE001
            _report(f"vertical debit @ {px}", exc=exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
