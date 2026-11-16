#!/usr/bin/env python3
"""
tests/broker_harness.py  v5.0
v5.0  2026-11-16  OTV5 r127 (LOP.1, FA.1) — NEW. THE MISBEHAVING BROKER: one shared, offline fake of the tastytrade
      Account that can LOSE A RESPONSE. Built for the cold audit's live-order fixes (FA.1 here; FA.2 the close-side
      double close and FA.3 intraday adoption reuse it). No network, no credentials, never imports a session.

WHY IT EXISTS. Every older fake in tests/ (check_order_guard, check_boot_order_sweep, check_live_exit_paths, ...)
has a place_order that either succeeds or never ran, so no check could model the case the audit found: the broker
ACCEPTS the order and the reply never arrives (HTTP response lost, run_async's 30 s TimeoutError while the
coroutine completes on the loop, a socket reset mid-read). This fake keeps the broker's TRUE book separately from
what the caller was told, so a test can ask "what is really working / really held" after the bot thinks it failed.

THE API (all Account methods are async, like tastytrade 13.x; the bot reaches them through data.tasty_client.sdk_result):

    sys.path.insert(0, os.path.join(ROOT, "tests")); from broker_harness import MisbehavingBroker, bind

    b = MisbehavingBroker()                       # an empty account, ample buying power
    b.script_place("lost")                        # the NEXT place_order: accepted, then raises TimeoutError
    b.script_place("raise")                       # the NEXT place_order: raises, nothing accepted
    b.script_place("lost", hidden_reads=1)        # accepted, raises, and the next 1 get_live_orders do not show it yet
    b.script_place("lost", exc=ConnectionResetError("reset"))   # any exception
    b.script_place("ok")                          # normal (also the default when nothing is scripted)
    b.fill_on_accept = 0.95                       # every accepted order fills at once at this per-share price
                                                  #   (None = it rests LIVE until the test fills it)
    b.fill(oid, price=0.95, qty=None)             # fill a working order (qty=None: the rest of it)
    b.set_status(oid, "Cancelled")                # force a status (an OrderStatus value or name)
    b.cancel_mode = "ok" | "raise" | "pending"    # delete_order: dead at once / raises / stays Cancel Requested
    b.get_order_raises = True                     # get_order raises (an unreadable order)
    b.live_orders_raise = True                    # get_live_orders raises (an unreadable book)

    with bind(b, EE, M):                          # patches get_session/get_account on each module given AND on
        ...                                       # data.tasty_client, restored on exit

  Reads for the test (the broker's truth, never what the caller was told):
    b.accepted        list of order ids the broker accepted, in order
    b.placed_prices   the signed limit price of every place_order CALL (accepted or not)
    b.place_calls     number of place_order calls
    b.deleted         order ids delete_order was asked to cancel
    b.working()       ids still Received/Routed/In Flight/Live/Contingent/Cancel Requested
    b.filled()        ids with status Filled
    b.position(sym)   signed net contracts held in that option (BTO/BTC +, STO/STC -)
    b.positions()     {symbol: signed qty} for every non-zero holding
    b.order(oid)      the order object itself (status, legs with fills, received_at)

  What the Account methods return, shaped like the SDK's (only the fields the bot reads):
    place_order  -> obj(errors=None, warnings=None, order=<order>)            (or raises, as scripted)
    get_order    -> <order>: id, status (tastytrade OrderStatus), legs[symbol, action, quantity, remaining_quantity,
                    fills[quantity, fill_price]], underlying_symbol, price, received_at / live_at (tz-aware UTC),
                    reject_reason
    get_live_orders -> every visible order placed today (any status), like /accounts/{n}/orders/live
    delete_order -> None; the order reads Cancelled (cancel_mode "ok"); a Filled or dead order raises
    get_positions -> obj(symbol, underlying_symbol, instrument_type, quantity (abs), quantity_direction
                    ("Long"/"Short"), average_open_price, created_at) per non-zero holding
    get_balances -> obj(derivative_buying_power, ...) ample unless b.buying_power is changed

Actions are read from the leg's action value or name ("Buy to Open", BUY_TO_OPEN, or the plain strings the
injected placers use), so both the real SDK Leg and the test-injected tuples work.

Run alone (self-test of the fixture):  python3 tests/broker_harness.py
"""
import contextlib
import datetime as _dt
import os
import sys
from decimal import Decimal
from types import SimpleNamespace

try:
    from tastytrade.order import OrderStatus as _OS
except Exception:                                                     # noqa: BLE001
    import enum

    class _OS(str, enum.Enum):                                        # same values as tastytrade 13.x
        RECEIVED = "Received"; CANCELLED = "Cancelled"; FILLED = "Filled"; EXPIRED = "Expired"
        LIVE = "Live"; REJECTED = "Rejected"; CONTINGENT = "Contingent"; ROUTED = "Routed"
        IN_FLIGHT = "In Flight"; CANCEL_REQUESTED = "Cancel Requested"
        REPLACE_REQUESTED = "Replace Requested"; REMOVED = "Removed"
        PARTIALLY_REMOVED = "Partially Removed"

try:
    from tastytrade.order import InstrumentType as _IT
    _OPTION = _IT.EQUITY_OPTION
except Exception:                                                     # noqa: BLE001
    _OPTION = "Equity Option"

OrderStatus = _OS
_WORKING = {_OS.RECEIVED, _OS.ROUTED, _OS.IN_FLIGHT, _OS.LIVE, _OS.CONTINGENT,
            _OS.CANCEL_REQUESTED, _OS.REPLACE_REQUESTED}
_DEAD = {_OS.CANCELLED, _OS.EXPIRED, _OS.REMOVED, _OS.PARTIALLY_REMOVED, _OS.REJECTED}


def _status(s):
    if isinstance(s, _OS):
        return s
    t = str(s)
    for m in _OS:
        if t in (m.value, m.name):
            return m
    raise ValueError(f"unknown order status {s!r}")


def _action_text(a) -> str:
    v = getattr(a, "value", None) or getattr(a, "name", None) or a
    return str(v).upper().replace(" ", "_")


def _sign(action) -> int:
    """+1 buys (to open or close), -1 sells."""
    return +1 if _action_text(action).startswith("BUY") else -1


def _now():
    return _dt.datetime.now(_dt.timezone.utc)


class _Fill:
    def __init__(self, qty, price):
        self.quantity, self.fill_price = Decimal(str(qty)), Decimal(str(price))


class _Leg:
    def __init__(self, symbol, action, quantity):
        self.instrument_type = _OPTION
        self.symbol, self.action = str(symbol), action
        self.quantity = Decimal(str(quantity))
        self.remaining_quantity = Decimal(str(quantity))
        self.fills = []


class _Order:
    def __init__(self, oid, legs, price):
        self.id = oid
        self.status = _OS.LIVE
        self.legs = legs
        self.price = price
        first = legs[0].symbol if legs else ""
        self.underlying_symbol = first.split()[0] if first else ""
        self.received_at = self.live_at = self.updated_at = _now()
        self.reject_reason = None
        self.size = None


class MisbehavingBroker:
    """An offline tastytrade Account whose place_order can lose its reply. See the module docstring."""

    def __init__(self, buying_power: float = 1_000_000.0):
        self._orders = {}
        self.accepted, self.deleted, self.placed_prices = [], [], []
        self.place_calls = 0
        self._script = []
        self._hidden = {}            # oid -> number of get_live_orders reads that will not show it yet
        self.fill_on_accept = None
        self.cancel_mode = "ok"
        self.get_order_raises = False
        self.live_orders_raise = False
        self.buying_power = buying_power
        self._held = {}              # symbol -> [signed qty, cost basis per share * |qty| (for the average)]
        self._seq = 0

    # ── scripting ──────────────────────────────────────────────────────────
    def script_place(self, mode: str = "ok", exc: BaseException = None, hidden_reads: int = 0):
        if mode not in ("ok", "lost", "raise"):
            raise ValueError(f"script_place mode {mode!r}: ok | lost | raise")
        self._script.append((mode, exc, int(hidden_reads)))

    def fill(self, oid, price: float, qty=None):
        o = self._orders[str(oid)]
        if o.status not in _WORKING:
            raise RuntimeError(f"order {oid} is {o.status.value}, cannot fill")
        for lg in o.legs:
            q = lg.remaining_quantity if qty is None else min(Decimal(str(qty)), lg.remaining_quantity)
            if q <= 0:
                continue
            # one per-share price for the whole order: single legs use it; multi-leg tests set leg prices with
            # fill_leg() when the net matters
            lg.fills.append(_Fill(q, price))
            lg.remaining_quantity -= q
            self._book(lg.symbol, _sign(lg.action) * q, price)
        if all(lg.remaining_quantity <= 0 for lg in o.legs):
            o.status = _OS.FILLED
        o.updated_at = _now()

    def fill_leg(self, oid, symbol, price: float, qty=None):
        """Fill one leg of a multi-leg order at its own price (the order is Filled when every leg is)."""
        o = self._orders[str(oid)]
        for lg in o.legs:
            if lg.symbol == symbol and lg.remaining_quantity > 0:
                q = lg.remaining_quantity if qty is None else min(Decimal(str(qty)), lg.remaining_quantity)
                lg.fills.append(_Fill(q, price))
                lg.remaining_quantity -= q
                self._book(lg.symbol, _sign(lg.action) * q, price)
        if all(lg.remaining_quantity <= 0 for lg in o.legs):
            o.status = _OS.FILLED

    def set_status(self, oid, status):
        self._orders[str(oid)].status = _status(status)

    def hold(self, symbol, qty: int, avg_price: float = 1.0):
        """Seed a position the broker holds (signed: +long, -short), e.g. one the DB never recorded."""
        self._book(symbol, Decimal(int(qty)), avg_price)

    # ── the broker's truth ─────────────────────────────────────────────────
    def order(self, oid):
        return self._orders[str(oid)]

    def working(self):
        return [i for i in self.accepted if self._orders[i].status in _WORKING]

    def filled(self):
        return [i for i in self.accepted if self._orders[i].status == _OS.FILLED]

    def position(self, symbol) -> int:
        return int(self._held.get(str(symbol), [0, 0])[0])

    def positions(self) -> dict:
        return {s: int(v[0]) for s, v in self._held.items() if v[0] != 0}

    def _book(self, symbol, signed_qty, price):
        q, cost = self._held.get(symbol, [Decimal(0), Decimal(0)])
        q2 = q + Decimal(signed_qty)
        if q == 0 or (q > 0) == (Decimal(signed_qty) > 0):
            cost = cost + abs(Decimal(signed_qty)) * Decimal(str(price))
        else:
            cost = (cost / abs(q)) * abs(q2) if q2 != 0 and (q2 > 0) == (q > 0) else abs(q2) * Decimal(str(price))
        self._held[symbol] = [q2, cost if q2 != 0 else Decimal(0)]

    # ── the Account surface (async, like tastytrade 13.x) ─────────────────
    async def place_order(self, session, order, dry_run=False):
        self.place_calls += 1
        try:
            self.placed_prices.append(float(order.price))
        except Exception:                                             # noqa: BLE001
            self.placed_prices.append(None)
        mode, exc, hidden = self._script.pop(0) if self._script else ("ok", None, 0)
        if dry_run:
            return SimpleNamespace(errors=None, warnings=None, order=None)
        if mode == "raise":
            raise exc or ConnectionError("broker refused the connection (nothing accepted)")
        self._seq += 1
        oid = f"O{self._seq}"
        legs = [_Leg(lg.symbol, lg.action, lg.quantity) for lg in (getattr(order, "legs", None) or [])]
        o = _Order(oid, legs, getattr(order, "price", None))
        self._orders[oid] = o
        self.accepted.append(oid)
        if hidden:
            self._hidden[oid] = hidden
        if self.fill_on_accept is not None:
            self.fill(oid, self.fill_on_accept)
        if mode == "lost":
            import concurrent.futures
            raise exc or concurrent.futures.TimeoutError("place_order reply lost (accepted at the broker)")
        return SimpleNamespace(errors=None, warnings=None, order=o)

    async def get_order(self, session, oid):
        if self.get_order_raises:
            raise RuntimeError("get_order unreadable")
        o = self._orders.get(str(oid))
        if o is None:
            raise RuntimeError(f"order {oid} not found")
        return o

    async def get_live_orders(self, session):
        if self.live_orders_raise:
            raise RuntimeError("live orders unreadable")
        out = []
        for oid in self.accepted:
            if self._hidden.get(oid, 0) > 0:
                self._hidden[oid] -= 1
                continue
            out.append(self._orders[oid])
        return out

    async def delete_order(self, session, oid):
        self.deleted.append(str(oid))
        o = self._orders.get(str(oid))
        if o is None:
            raise RuntimeError(f"order {oid} not found")
        if self.cancel_mode == "raise":
            raise RuntimeError("cancel refused")
        if o.status not in _WORKING:
            raise RuntimeError(f"order {oid} is {o.status.value}, not cancellable")
        o.status = _OS.CANCEL_REQUESTED if self.cancel_mode == "pending" else _OS.CANCELLED
        o.updated_at = _now()

    async def get_positions(self, session, **kw):
        out = []
        for sym, (q, cost) in self._held.items():
            if q == 0:
                continue
            out.append(SimpleNamespace(
                symbol=sym, underlying_symbol=sym.split()[0], instrument_type=_OPTION,
                quantity=abs(q), quantity_direction="Long" if q > 0 else "Short",
                average_open_price=(cost / abs(q)) if q else Decimal(0), created_at=_now()))
        return out

    async def get_balances(self, session, currency="USD"):
        bp = self.buying_power
        return SimpleNamespace(derivative_buying_power=bp, option_buying_power=bp,
                               equity_buying_power=bp, cash_balance=bp, net_liquidating_value=bp)


@contextlib.contextmanager
def bind(broker, *modules):
    """Point get_session/get_account at `broker` on data.tasty_client and on every module given (modules that
    imported the names directly, e.g. execution.entry_engine). Everything is restored on exit."""
    import data.tasty_client as tc
    targets = [tc] + [m for m in modules if m is not tc]
    saved = []
    sess = SimpleNamespace(fake=True)
    for m in targets:
        for name, val in (("get_session", lambda: sess), ("get_account", lambda: broker)):
            if hasattr(m, name):
                saved.append((m, name, getattr(m, name)))
                setattr(m, name, val)
    try:
        yield broker
    finally:
        for m, name, val in reversed(saved):
            setattr(m, name, val)


def _selftest() -> int:
    import asyncio
    bad = []
    b = MisbehavingBroker()
    leg = SimpleNamespace(symbol="QQQ   261116C00500000", action="BUY_TO_OPEN", quantity=1)
    order = SimpleNamespace(price=Decimal("-0.95"), legs=[leg])
    b.script_place("lost", hidden_reads=1)
    try:
        asyncio.run(b.place_order(None, order))
        bad.append("H1 a lost reply raised")
    except Exception:                                                 # noqa: BLE001
        pass
    if b.accepted != ["O1"] or b.working() != ["O1"]:
        bad.append(f"H1 lost order accepted and working: {b.accepted} {b.working()}")
    if asyncio.run(b.get_live_orders(None)) != [] or len(asyncio.run(b.get_live_orders(None))) != 1:
        bad.append("H2 hidden_reads hides the order for exactly one read")
    b.fill("O1", 0.95)
    if b.position(leg.symbol) != 1 or b.filled() != ["O1"]:
        bad.append(f"H3 a fill books a position: {b.positions()}")
    b.script_place("raise")
    try:
        asyncio.run(b.place_order(None, order))
    except Exception:                                                 # noqa: BLE001
        pass
    if b.accepted != ["O1"] or b.place_calls != 2:
        bad.append("H4 'raise' accepts nothing")
    o2 = asyncio.run(b.place_order(None, SimpleNamespace(price=Decimal("0.5"), legs=[
        SimpleNamespace(symbol=leg.symbol, action="SELL_TO_CLOSE", quantity=1)]))).order
    asyncio.run(b.delete_order(None, o2.id))
    if o2.status != _OS.CANCELLED or b.position(leg.symbol) != 1:
        bad.append("H5 a cancel kills the order and leaves the position")
    print("broker_harness self-test:", "GREEN" if not bad else f"RED {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.exit(_selftest())
