#!/usr/bin/env python3
"""tools/probe_order_dryrun.py — v5.2
v5.2  2026-11-24  OTV5 r157 (PRB.2 upgrade) — THE PROBE DRY-RUNS THE ORDERS THE BOT ITSELF BUILDS, ON AN EXPIRY STILL
      TRADING, AND CANNOT SEND A LIVE ORDER BY CONSTRUCTION. The operator, 2026-11-24: "Go ahead". The 11-24 rehearsal
      found three gaps: v5.1 always picked TODAY's expiry (every dry run after 16:15 came back
      instruments_stopped_trading), it sent only far-OTM Buy-to-Open limits (never a Sell to Close, never a MARKET), and
      it built its own orders instead of the bot's. Now:
        EXPIRY  pick_expiry(): fetch_chain's own rule (data/options_chain.py: the AM-settled series dropped, then the
                nearest listed date on or after the target) with the target TODAY while today's contracts still trade
                (now < stops_trading_at) and TOMORROW once they have all stopped - so after the stop it is the next
                LISTED expiry (a holiday gap is skipped exactly as fetch_chain skips it). The chain structure comes from
                the bot's OptionsChainFetcher._get_chain_structure (which also caches the venue's tick grid the ladder
                prices on); the quote is the box's own streamed chain_marks row (_read_marks, read-only; nothing is
                published to chain_subs), else one REST market-data read.
        ORDERS  the default mode builds every order with the bot's REAL code: the entry rungs from
                execution.ladder_registry.price_for (the walk _place_single_leg prices, refused rung by rung to the
                mark) wrapped exactly as entry_engine wraps them; every exit through the REAL
                ExitEngine._submit_live_close - the stop at the mark, the stop escalation to the bid and to MARKET
                (config.LIVE_STOP_AT_BID_AFTER / LIVE_STOP_MARKET_AFTER), PARK's walk, the debit_hard_close ladder at
                EOD_LADDER_AT_ET and the force_market cross at EOD_CROSS_AT_ET (each moved to the day's bell, so a
                13:00 half day reads 12:50 / 12:55). The exit clock is pinned per order; the broker sees real time.
        REPORT  per order: type, price and effect, quantity, TIF, side; the broker's verdict (accepted / rejected, the
                reason, the warnings tagged buying power / PDT / approval level, the buying-power CHANGE and fees). A
                Sell / Buy to Close whose only objection is the missing position is EXPECTED - everything else about the
                order passed.
        SAFETY  three layers, gated by tests/check_probe_dryrun.py D6-D8: (1) the bot's code is handed a
                DryRunAccount whose only method, place_order, IGNORES the dry_run the bot asks for and sends the order
                through _dry() - still the ONE place_order call in this file, with the literal dry_run=True; (2)
                install_guards() replaces Account.place_order on the CLASS with a guard that RAISES unless dry_run is
                True, and replace_order / place_complex_order / delete_order / delete_complex_order with refusals;
                (3) guard_session() refuses any order POST that is not a /dry-run, and every order PUT / DELETE. Bot
                pages, the heartbeat and the trades DB are never reached (the engine is built without __init__, its
                page method records only).
      The v5.1 questions (far-OTM single and vertical at 0.05 / 0.07 / 3.10 / 3.05) stay as `--far-otm`, now on the same
      expiry rule. No production module imports this file (check_probe_dryrun D13). No config key, no env key.
v5.1  2026-11-08  OTV5 r84 (VENV.1) — a bare run (control's /usr/bin/python3 3.14, no tastytrade) stops with one
      ModuleNotFoundError line naming the venv to use, not a traceback: utils.venv_guard.require_venv before the first
      third-party import. Under the venv nothing changes.
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
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
  default (v5.2): the chain's roots / settlement by expiry, the expiry chosen and why, the quote used, then the bot's own
     orders on a near-the-money call of that expiry, 1 contract: the entry walk's rungs (Buy to Open, LIMIT, DAY), and
     the exits (Sell to Close): the Runaway stop passes 1-4 (mark, mark, the bid, MARKET), PARK's delta-floor walk, the
     end-of-day ladder and the end-of-day cross (MARKET). With no position held, every Sell to Close is EXPECTED to be
     refused for that reason alone.
  --far-otm (the v5.1 questions):
  1. the chain's roots and settlement types for the next expiries (SPX: is "AM" / "PM" the literal value,
     and do SPX AM and SPXW share a date?)
  2. a 1-lot single BUY_TO_OPEN on a far OTM put at 0.05 (on any grid) and 0.07 (off a 0.05 grid)
  3. the same at 3.10 and 3.05 (the SPX >= 3.00 dime rule)
  4. a 1-lot debit put vertical at 0.05 / 0.07 / 3.10 / 3.05 (the complex-order increment, both sides of $3)
SAFETY, by construction: the ONLY call to place_order is in _dry(), which passes the literal dry_run=True;
tests/check_probe_dryrun.py proves by AST that no other place_order call exists and that dry_run is never set to anything
but True, and (v5.2) drives the three guards above, each with its mutant red.
It prints no account number and no balance - only the CHANGE in buying power, the effect, and fees.
Run ONLY through the r176 wrapper (it carries the bot's TT_* keys, never prints them):
    /home/ubuntu/options-trader/venv/bin/python /home/ubuntu/options-trader/tools/run_with_bot_env.py probe_order_dryrun.py
    /home/ubuntu/options-trader/venv/bin/python /home/ubuntu/options-trader/tools/run_with_bot_env.py probe_order_dryrun.py --far-otm
"""
import inspect
import json
import logging
import os
import sys
import warnings
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from utils.venv_guard import require_venv                         # noqa: E402  (stdlib only)
require_venv('tastytrade')

from tastytrade.account import Account                                          # noqa: E402
from tastytrade.instruments import OptionType, InstrumentType                   # noqa: E402
from tastytrade.order import NewOrder, Leg, OrderAction, OrderType, OrderTimeInForce  # noqa: E402
from data.tasty_client import get_session, get_tt_account_number, sdk_result     # noqa: E402

SYM = (os.environ.get("OT_INSTRUMENT") or "").strip().upper()
_MASK = []                       # strings never printed (filled in main); _scrub replaces them


class LiveSubmitRefused(RuntimeError):
    """A submit that is not a dry run reached a guard. Nothing was sent."""


# ═══ SAFETY ═══════════════════════════════════════════════════════════════════════════════════════════════════════

def _dry(account, session, order):
    """THE ONLY place_order CALL IN THIS FILE. dry_run is the literal True. r242: through sdk_result (B0)."""
    return sdk_result(account.place_order(session, order, dry_run=True))


def install_guards(account_cls=Account):
    """Layer 2: on the Account CLASS, place_order raises unless dry_run is True (and then sends dry_run=True only);
    every other submitting or cancelling method raises. Idempotent."""
    cur = getattr(account_cls, "place_order")
    if getattr(cur, "_prb2_guard", False):
        return
    orig = cur

    async def place_order(self, session, order, dry_run=None):
        if dry_run is not True:
            raise LiveSubmitRefused(f"place_order with dry_run={dry_run!r} refused - the probe only dry-runs")
        res = orig(self, session, order, dry_run=True)
        if inspect.isawaitable(res):
            res = await res
        return res
    place_order._prb2_guard = True
    setattr(account_cls, "place_order", place_order)

    def _refuser(name):
        async def refused(self, *a, **k):
            raise LiveSubmitRefused(f"Account.{name} refused - the probe only dry-runs")
        refused._prb2_guard = True
        return refused
    for name in ("replace_order", "place_complex_order", "delete_order", "delete_complex_order"):
        if hasattr(account_cls, name):
            setattr(account_cls, name, _refuser(name))


def _order_url(url) -> bool:
    u = str(url or "")
    return "/orders" in u or "/complex-orders" in u


def guard_session(session):
    """Layer 3: on THIS session, an order POST must be a /dry-run; an order PUT or DELETE is refused. Fails closed:
    a session whose methods cannot be wrapped raises here, and the probe stops before any order is built."""
    for name in ("_post", "_put", "_delete"):
        orig = getattr(session, name)
        if getattr(orig, "_prb2_guard", False):
            continue

        async def guarded(url, *a, _orig=orig, _name=name, **k):
            if _order_url(url) and (_name != "_post" or not str(url).rstrip("/").endswith("/dry-run")):
                raise LiveSubmitRefused(f"session.{_name} to an order endpoint that is not a dry run - refused")
            return await _orig(url, *a, **k)
        guarded._prb2_guard = True
        setattr(session, name, guarded)
        if getattr(getattr(session, name), "_prb2_guard", False) is not True:
            raise LiveSubmitRefused(f"could not guard session.{name} - nothing sent")
    return session


class DryRunAccount:
    """Layer 1: what the bot's code is handed instead of the Account. place_order ignores the dry_run the bot asks for
    (the bot's own submit asks for a live order) and goes through _dry(). Anything else the bot reaches for raises."""

    def __init__(self, real, session):
        self._real = real
        self._session = session
        self.calls = []

    def place_order(self, session, order, **kw):
        return self.send(order, kw.get("dry_run", "default"))

    def send(self, order, asked="probe"):
        """The one path to the broker: _dry(), whatever `asked` says. Records the order and the answer in .calls."""
        call = {"order": order, "bot_asked": asked}
        self.calls.append(call)
        try:
            call["resp"] = _dry(self._real, self._session, order)
        except Exception as exc:                                     # noqa: BLE001
            call["exc"] = exc
            raise
        return call["resp"]

    def __getattr__(self, name):
        raise LiveSubmitRefused(f"the probe's account has no {name} - only a dry-run place_order")


# ═══ EXPIRY — fetch_chain's rule, plus the stop time ══════════════════════════════════════════════════════════════

def tradeable(chain_map) -> dict:
    """fetch_chain step 1, verbatim rule: every settlement_type "AM" contract dropped; a date left empty is gone."""
    out = {}
    for d, opts in chain_map.items():
        keep = [o for o in opts if str(getattr(o, "settlement_type", "") or "").upper() != "AM"]
        if keep:
            out[d] = keep
    return out


def pick_expiry(chain_map, now):
    """(expiry, its tradeable contracts, why). The target is today while any of today's contracts still trades
    (now < stops_trading_at; a contract with no stop time counts as trading), else tomorrow; then fetch_chain's
    fallback: the nearest listed date on or after the target. (None, [], why) when nothing is listed."""
    t = tradeable(chain_map)
    today = now.date()
    live = [o for o in t.get(today, [])
            if getattr(o, "stops_trading_at", None) is None or now < o.stops_trading_at]
    if live:
        return today, live, f"today's {today} still trades"
    target = today + timedelta(days=1) if t.get(today) else today
    why = (f"today's {today} contracts have stopped trading - the next listed expiry" if t.get(today)
           else f"no {today} expiry - the nearest listed one (fetch_chain's fallback)")
    future = sorted(d for d in t if d >= target)
    if not future:
        return None, [], f"no tradeable expiry on or after {target}"
    return future[0], t[future[0]], why


# ═══ ORDERS — the bot's builders ══════════════════════════════════════════════════════════════════════════════════

def build_entry_order(occ: str, limit: float, qty: int):
    """execution/entry_engine._place_single_leg's order, verbatim: a DAY LIMIT Buy to Open, the price negative (a debit)."""
    leg = Leg(
        instrument_type = InstrumentType.EQUITY_OPTION,
        symbol          = occ,
        action          = OrderAction.BUY_TO_OPEN,
        quantity        = qty,
    )
    return NewOrder(
        time_in_force = OrderTimeInForce.DAY,
        order_type    = OrderType.LIMIT,
        price         = Decimal(str(-limit)),   # - = DEBIT paid to open
        legs          = [leg],
    )


def entry_orders(occ: str, bid: float, ask: float, qty: int, grid_symbol: str, max_rungs: int = 20):
    """[(limit, why, order)]: the entry walk as _place_single_leg prices it (ladder_registry.price_for on the intent
    key of this contract, side buy, the UNDERLYING's grid), each rung refused in turn until the walk re-offers its
    terminal rung or ends. The walk is cleared after."""
    from execution import ladder_registry as lr
    key = lr.intent_key(occ, "open", "single")
    lr.clear(key)
    out, seen = [], []
    try:
        for _ in range(max_rungs):
            got = lr.price_for(key, "buy", bid, ask, grid_symbol)
            if not got:
                break
            limit, why = float(got[0]), str(got[1])
            if any(abs(limit - s) < 1e-9 for s in seen):
                break                                               # the terminal rung re-offered: the walk holds there
            out.append((limit, why, build_entry_order(occ, limit, qty)))
            seen.append(limit)
            lr.refuse(key, limit)
    finally:
        lr.clear(key)
    return out


def exit_scenarios(now):
    """[(title, strategy, reason, unfilled passes, pinned ET clock)] - the closes the two live setups can post."""
    from utils.time_utils import close_anchored, ET
    import config as _c
    import execution.exit_engine as xe
    mid = datetime(now.year, now.month, now.day, 11, 0, tzinfo=ET)

    def _at(hm):
        a = close_anchored(tuple(hm), mid)
        return mid.replace(hour=a.hour, minute=a.minute)
    eod = xe._eod_label({"symbol": SYM, "strategy": "RunawayContinuation"})
    out = []
    for n in range(4):
        out.append((f"Runaway stop (runaway_thesis_dead) pass {n + 1}", "RunawayContinuation",
                    "runaway_thesis_dead", n, mid))
    out.append(("PARK delta floor (park_delta_floor, the walk)", "PARK", "park_delta_floor", 0, mid))
    out.append((f"EOD ladder ({eod}, debit_hard_close)", "RunawayContinuation", eod, 0, _at(_c.EOD_LADDER_AT_ET)))
    out.append((f"EOD cross ({eod}, force_market)", "RunawayContinuation", eod, 0, _at(_c.EOD_CROSS_AT_ET)))
    return out


def run_exits(account, session, occ: str, bid: float, ask: float, qty: int, now, collect=None):
    """Every exit_scenarios() close through the REAL ExitEngine._submit_live_close, the engine's get_session /
    get_account pointing at `session` / `account` and its clock pinned per scenario. Returns
    [(title, policy, why, clock, [the place_order calls it made])]. Pages are recorded, never sent; no trades DB is
    opened (the engine is built without __init__)."""
    import execution.exit_engine as xe
    eng = xe.ExitEngine.__new__(xe.ExitEngine)
    eng._live_exit_alerted = set()
    pages = []
    eng._alert_live_exit_once = lambda tid, kind, msg: pages.append((kind, msg))
    saved = {k: getattr(xe, k) for k in ("get_session", "get_account", "now_et", "_hb_touch")}
    xe.get_session = lambda *a, **k: session
    xe.get_account = lambda *a, **k: account
    xe._hb_touch = lambda *a, **k: True
    lines = []

    class _Grab(logging.Handler):
        def emit(self, r):
            m = r.getMessage()
            if m.startswith("[ladder]"):
                lines.append(m)
    grab = _Grab()
    xe.logger.addHandler(grab)
    level = xe.logger.level
    xe.logger.setLevel(logging.INFO)                               # the "[ladder] ... CLOSE" line names the why
    mark = round((bid + ask) / 2.0, 4)
    out = []
    try:
        for i, (title, strat, reason, unfilled, clock) in enumerate(exit_scenarios(now)):
            xe.now_et = (lambda c: (lambda: c))(clock)
            rec = {"trade_id": f"PRB2X{i:02d}{reason[:16]}", "option_symbol": occ, "symbol": SYM,
                   "strategy": strat, "_exit_bid": bid, "_exit_ask": ask, "_stop_unfilled": unfilled}
            before = len(account.calls)
            lines.clear()
            policy = eng._exit_policy(rec, reason)
            try:
                eng._submit_live_close(rec, qty, mark, reason=reason)
            finally:
                eng._exit_walk_done(rec)
            why = next((m.split(" — ", 1)[-1] for m in lines if " CLOSE " in m), "")
            out.append((title, policy, why, clock, account.calls[before:]))
    finally:
        for k, v in saved.items():
            setattr(xe, k, v)
        xe.logger.removeHandler(grab)
        xe.logger.setLevel(level)
    if collect is not None:
        collect.extend(pages)
    return out


# ═══ REPORT ═══════════════════════════════════════════════════════════════════════════════════════════════════════

_NO_POSITION = ("position", "closing", "to_close", "naked", "uncovered")
_TAGS = (("buying power", ("buying_power", "buying power", "margin", "insufficient_funds")),
         ("PDT", ("pattern_day", "pattern day", "day_trad", "day trad", "pdt")),
         ("approval level", ("approval", "permission", "option_level", "trading_level", "not_permitted",
                             "not permitted", "not_allowed", "not allowed")))


def _scrub(text) -> str:
    s = str(text)
    for m in _MASK:
        if m:
            s = s.replace(m, "[account]")
    return s


def _tag(text: str) -> str:
    low = text.lower()
    tags = [name for name, keys in _TAGS if any(k in low for k in keys)]
    return f"[{', '.join(tags)}] " if tags else ""


def describe(order) -> dict:
    d = json.loads(order.model_dump_json(by_alias=True, exclude_none=True))
    return {"type": d.get("order-type"), "tif": d.get("time-in-force"), "price": d.get("price"),
            "effect": d.get("price-effect"),
            "legs": [(lg.get("action"), lg.get("quantity"), lg.get("symbol")) for lg in d.get("legs", [])]}


def _closing(order) -> bool:
    return any("close" in str(a).lower() for a, _q, _s in describe(order)["legs"])


def verdict(call) -> tuple:
    """(status, [reasons], [warnings]) for one DryRunAccount call. status: ACCEPTED | EXPECTED | REJECTED.
    EXPECTED = a closing order whose EVERY objection is the missing position (no position is held)."""
    if "exc" in call:
        reasons = [ln.strip() for ln in str(call["exc"]).splitlines() if ln.strip()] or [type(call["exc"]).__name__]
        warns = []
    else:
        resp = call.get("resp")
        reasons = [str(e) for e in (getattr(resp, "errors", None) or [])]
        warns = [str(w) for w in (getattr(resp, "warnings", None) or [])]
    if not reasons:
        return "ACCEPTED", [], warns
    if _closing(call["order"]) and all(any(k in r.lower() for k in _NO_POSITION) for r in reasons):
        return "EXPECTED", reasons, warns
    return "REJECTED", reasons, warns


def report(label: str, call, why: str = "") -> str:
    """Print one order and the broker's verdict; returns the status."""
    o = describe(call["order"])
    px = "MARKET" if o["price"] is None else f"{o['price']} {o['effect'] or ''}".strip()
    legs = "; ".join(f"{a} x{q} {s}" for a, q, s in o["legs"])
    print(f"  {label}")
    print(f"      built:   {o['type']} {o['tif']} {px} | {legs}" + (f"   ({_scrub(why)})" if why else ""))
    status, reasons, warns = verdict(call)
    if status == "ACCEPTED":
        resp = call.get("resp")
        bpe = getattr(resp, "buying_power_effect", None)
        fee = getattr(resp, "fee_calculation", None)
        print(f"      broker:  ACCEPTED  bp_change={getattr(bpe, 'change_in_buying_power', '?')} "
              f"effect={getattr(bpe, 'effect', '?')} fees={getattr(fee, 'total_fees', '?')}")
    elif status == "EXPECTED":
        print("      broker:  EXPECTED REJECT - no position to close (everything else about the order passed)")
    else:
        print("      broker:  REJECTED")
    for r in reasons:
        print(f"      reason:  {_tag(r)}{_scrub(r)[:200]}")
    for w in warns:
        print(f"      warning: {_tag(w)}{_scrub(w)[:200]}")
    return status


# ═══ QUOTE ════════════════════════════════════════════════════════════════════════════════════════════════════════

def pick_quote(session, opts):
    """(occ, bid, ask, source) for the near-the-money call of `opts`: the box's streamed chain_marks first (the call
    whose delta is nearest 0.50 with a two-sided book; read-only, nothing published), else one REST market-data read
    of the call nearest the underlying's mark. None when neither has a two-sided quote."""
    calls = [o for o in opts if o.option_type == OptionType.CALL
             and (SYM != "SPX" or getattr(o, "root_symbol", "") == "SPXW")]
    by_stream = {getattr(o, "streamer_symbol", "") or "": o for o in calls}
    by_stream.pop("", None)
    try:
        from data.options_chain import OptionsChainFetcher
        greeks, quotes = OptionsChainFetcher()._read_marks(list(by_stream))
        two = []
        for ss, q in quotes.items():
            b, a = float(q.bid_price or 0), float(q.ask_price or 0)
            g = greeks.get(ss)
            if b > 0 and a > b and g is not None and float(g.delta or 0) > 0:
                two.append((abs(float(g.delta) - 0.5), ss, b, a))
        if two:
            _d, ss, b, a = min(two)
            return by_stream[ss].symbol, b, a, "the box's streamed chain_marks (read-only)"
    except Exception as exc:                                         # noqa: BLE001
        print(f"  (streamed quote unreadable: {type(exc).__name__}: {_scrub(exc)})")
    try:
        from tastytrade.market_data import get_market_data_by_type
        kind = {"indices": [SYM]} if SYM == "SPX" else {"equities": [SYM]}
        und = sdk_result(get_market_data_by_type(session, **kind))
        spot = float((getattr(und[0], "mark", None) or getattr(und[0], "last", None) or 0)) if und else 0.0
        if spot > 0 and calls:
            c = min(calls, key=lambda o: abs(float(o.strike_price) - spot))
            md = sdk_result(get_market_data_by_type(session, options=[c.symbol]))
            if md:
                b, a = float(md[0].bid or 0), float(md[0].ask or 0)
                if b > 0 and a > b:
                    return c.symbol, b, a, "REST market data (one read)"
    except Exception as exc:                                         # noqa: BLE001
        print(f"  (REST quote unreadable: {type(exc).__name__}: {_scrub(exc)})")
    return None


# ═══ MODES ════════════════════════════════════════════════════════════════════════════════════════════════════════

def _put_leg(sym, action):
    return Leg(instrument_type=InstrumentType.EQUITY_OPTION, symbol=sym, action=action, quantity=1)


def _send(acct, session, order):
    """One order through the DryRunAccount; the verdict is read from acct.calls, so a broker refusal is not an error."""
    try:
        acct.send(order)
    except Exception:                                                # noqa: BLE001
        pass
    return acct.calls[-1]


def far_otm(acct, session, d0, opts) -> int:
    """The v5.1 questions, unchanged except the expiry (pick_expiry, not always today)."""
    puts = [o for o in opts if o.option_type == OptionType.PUT
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
        report(f"single BUY_TO_OPEN @ {px}", _send(acct, session, o))
    for px in ("0.05", "0.07", "3.10", "3.05"):
        o = NewOrder(time_in_force=OrderTimeInForce.DAY, order_type=OrderType.LIMIT,
                     price=Decimal("-" + px),
                     legs=[_put_leg(hi.symbol, OrderAction.BUY_TO_OPEN),
                           _put_leg(lo.symbol, OrderAction.SELL_TO_OPEN)])
        report(f"vertical debit @ {px}", _send(acct, session, o))
    return 0


def builders(acct, session, opts, now) -> int:
    """The bot's own orders on the near-the-money call of the chosen expiry, 1 contract."""
    q = pick_quote(session, opts)
    if q is None:
        print("no two-sided quote on the chosen expiry (streamed or REST) - no order built")
        return 3
    occ, bid, ask, src = q
    print(f"\nquote: {occ!r} bid {bid:.2f} / ask {ask:.2f} (mark {(bid + ask) / 2:.3f}) from {src}")
    counts = Counter()
    print("\nENTRY - the walk _place_single_leg posts (ladder_registry.price_for), each rung dry-run:")
    for n, (limit, why, order) in enumerate(entry_orders(occ, bid, ask, 1, SYM), 1):
        counts[report(f"rung {n}: {limit:.2f}", _send(acct, session, order), why)] += 1
    print("\nEXITS - the REAL ExitEngine._submit_live_close, the clock pinned per order (no position is held):")
    pages = []
    for title, policy, why, clock, calls in run_exits(acct, session, occ, bid, ask, 1, now, collect=pages):
        label = f"{title} - policy {policy}, clock {clock:%H:%M} ET"
        if not calls:
            print(f"  {label}\n      built:   NOTHING POSTED")
            counts["NOTHING"] += 1
        for c in calls:
            counts[report(label, c, why)] += 1
    print(f"\n{len(pages)} page(s) the bot would have sent (stop escalation; a dry run's reply carries no order id, which"
          f" the bot reads as a lost close) were recorded, not sent.")
    print("SUMMARY: " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    mode = "far-otm" if "--far-otm" in argv else "builders"
    if not SYM:
        print("probe_order_dryrun: no OT_INSTRUMENT - run it through tools/run_with_bot_env.py")
        return 2
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    logging.getLogger().addHandler(logging.NullHandler())            # the bot's log lines stay out of this output
    install_guards(Account)                                          # layer 2, before any account exists
    session = guard_session(get_session())                           # layer 3
    _MASK.append(get_tt_account_number())
    real = sdk_result(Account.get(session, _MASK[0]))                # the B0 helper, exactly as the bot calls it
    print(f"account object: {type(real).__name__} (B0 check: must be 'Account', not 'coroutine')")
    acct = DryRunAccount(real, session)                              # layer 1
    import data.tasty_client as tc
    tc.get_account = lambda *a, **k: acct                            # nothing in this process reaches the real Account
    from data.options_chain import OptionsChainFetcher
    from utils.time_utils import now_et
    chain = OptionsChainFetcher()._get_chain_structure(session, SYM)  # the bot's REST read (+ its venue tick grid)
    now = now_et()
    future = sorted(d for d in chain if d >= now.date())
    third_fri = [d for d in future if d.weekday() == 4 and 15 <= d.day <= 21 and (d - now.date()).days <= 70]
    dates = sorted(set(future[:8]) | set(third_fri))
    print(f"\n{SYM} chain - roots / settlement by expiry (next {len(dates)}):")
    for d in dates:
        c = Counter((getattr(o, "root_symbol", "?"), getattr(o, "settlement_type", "?")) for o in chain[d])
        print(f"  {d}  " + "  ".join(f"{r}/{s}={n}" for (r, s), n in sorted(c.items())))
    d0, opts, why = pick_expiry(chain, now)
    print(f"\nexpiry: {d0} - {why} (now {now:%Y-%m-%d %H:%M} ET; mode {mode})")
    if d0 is None:
        return 3
    rc = far_otm(acct, session, d0, opts) if mode == "far-otm" else builders(acct, session, opts, now)
    asked = Counter(str(c["bot_asked"]) for c in acct.calls)
    print(f"\n{len(acct.calls)} order(s) sent, every one as a DRY RUN (the caller asked dry_run: "
          + ", ".join(f"{k} x{v}" for k, v in sorted(asked.items())) + ")")
    return rc


if __name__ == "__main__":
    sys.exit(main())
