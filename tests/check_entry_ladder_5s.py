#!/usr/bin/env python3
"""
tests/check_entry_ladder_5s.py — v5.0
v5.0  2026-11-20  OTV5 r133 (D2 + D3) — new. THE LIVE ENTRY WALK POSTS ITS NEXT RUNG AS SOON AS THE LAST ONE IS READ
      DEAD, INSIDE ONE TICK, AND THE CONTRACT IS FROZEN FOR THE WALK'S LIFE. The forward-edge study 2026-11-20 (D2, D3;
      ~/reviews/studies/forward_edge_20261120/REPORT.md). The operator, 2026-11-20: "If the ladder was fast enough to
      update every 5 seconds, I would prefer that" and "Yes to both".
DRIVEN THROUGH THE REAL PATH: EntryEngine._place_single_leg -> the real order_guard, buying_power, ladder_registry,
entry_ladder, tick_size and order_confirm.confirm_order_fill, against tests/broker_harness.MisbehavingBroker, with the
streamed quote read from a scratch feed_store.db chain_marks row through the real OptionsChainFetcher._read_marks.
TIME IS FAKE: order_confirm's and entry_engine's `time` are a clock that only moves when the code sleeps, and every
sleep runs a strict-touch market (a working buy fills at its limit once the scripted ask is at or below it).
QQQ, venue rule 0.01 cached under QQQ (r132).
  L1  one call (one tick) posts rung after rung: on a static 3.40/3.50 book it posts 3.42 then 3.43, the second 5-8 s
      after the first, then stops on the TICK BUDGET (no rung starts whose 5 s rest would end past 15 s) - every post
      at or below the mark 3.45; the heartbeat is touched between rungs
  L2  quote drift re-prices the next rung from the fresh streamed quote: the book moving up to 3.45/3.55 posts 3.48
      (one rung in, on the new table - the small penalty against us, never above the new mark 3.50); moving down to
      3.33/3.43 posts the new mark 3.38 (the discount: below the refused 3.42, since the mark cap applies after the
      ratchet)
  L3  a refused price is re-offered once it becomes the mark: 3.42 refused on 3.40/3.50, the book moves to 3.37/3.47
      (mark 3.42) - the next rung is 3.42
  L4  a fill during the cancel is honoured exactly once: (a) the broker fills rung 2 as the cancel arrives (the cancel
      raises "not cancellable") - the call returns 1 @ 3.43 and the broker holds exactly 1; (b) the cancel sits in
      Cancel Requested and the fill lands - the same; neither posts a third order
  L5  the stops: (a) the MARK RUNG refused ends the call (3.43/3.45: 3.43, then the mark 3.44, then back to the tick,
      even with budget to spare); (b) the strategy's entry window ending (LiquidityHunt, 10:29:57 ET, window ends 10:30)
      ends the walk after one rung and CLEARS it (no walk, no pin left); (c) an unconfirmed cancel ends the call and the
      next call posts nothing beside the possibly-live order (order_guard holds the intent)
  L6  D3, the contract is frozen across a re-pick: tick 1 walks 600C (3.42, 3.43); tick 2's signal re-picked 601C -
      freeze_contract puts it back on 600C (re-quoted from the stream: entry_premium = its mark) and tick 2 continues
      600C's walk at 3.44 (not the 25% opener of 601C); a pin idle past PIN_IDLE_S, another strategy and the other
      direction are never frozen; main._execute_entry_signal calls freeze_contract before sizing
  L7  paper untouched: a paper entry books the mark with a PAPER- id and reaches no broker call; freeze_contract is a
      no-op in paper
  L8  a contract with no streamer symbol keeps one rung per call (the r132 shape, which the older fakes rely on), and
      exits are untouched: a QQQ single-leg close still walks 3.48, 3.47, 3.46, 3.45; LIVE_STOP_AT_BID_AFTER 2 and
      LIVE_STOP_MARKET_AFTER 3
Born red on r132 (7e5fee8): L1-L6 (one rung per call; no freeze_contract); L7-L8 pin unchanged behaviour and pass on
r132. Mutants (each red): the loop's `while True` -> one pass (L1-L5); the mark-rung stop removed (L5a); the window stop
removed (L5b); the unconfirmed-cancel guard removed (L5c); freeze_contract returning False (L6); the paper early return
removed (L7).
Run:  python3 tests/check_entry_ladder_5s.py
"""
import datetime as _dt
import logging
import os
import sqlite3
import sys
import tempfile
import time as _real_time
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
_TD = tempfile.mkdtemp(prefix="check_entry_ladder_5s.")
for _k, _v in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"),
               ("OT_FEED_DB", "f.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_PLAN_STATES_FILE", "ps.json"),
               ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT")):
    os.environ.setdefault(_k, os.path.join(_TD, _v))
os.environ["OT_INSTRUMENT"] = "QQQ"
FAILED = []

try:
    import config                                               # noqa: E402
    from execution import entry_engine as EE                    # noqa: E402
    from execution import order_confirm as OC                   # noqa: E402
    from execution import ladder_registry as LR                 # noqa: E402
    from execution import order_guard as OG                     # noqa: E402
    from execution import buying_power as BP                    # noqa: E402
    from execution import tick_size as TS                       # noqa: E402
    from data.options_chain import OptionContract               # noqa: E402
    from broker_harness import MisbehavingBroker, bind          # noqa: E402
except Exception as exc:                                        # noqa: BLE001
    print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
    sys.exit(2)

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:                                               # noqa: BLE001
    _ET = _dt.timezone(_dt.timedelta(hours=-5))

X_OCC, X_STREAM = "QQQ   261120C00600000", ".QQQ261120C600"
Y_OCC, Y_STREAM = "QQQ   261120C00601000", ".QQQ261120C601"


# ── the fake clock and the strict-touch market ───────────────────────────────
class Clock:
    def __init__(self):
        self.t = 0.0
        self.market = None
        self.sleeps = 0

    def monotonic(self):
        return self.t

    def time(self):
        return _real_time.time()

    def sleep(self, s):
        self.sleeps += 1
        if self.sleeps > 5000:
            raise RuntimeError("fake clock: runaway sleep loop")
        self.t += max(0.0, float(s))
        if self.market is not None:
            self.market.step(self.t)


CLOCK = Clock()


def _feed():
    c = sqlite3.connect(os.environ["OT_FEED_DB"])
    c.execute("CREATE TABLE IF NOT EXISTS chain_marks (streamer_symbol TEXT PRIMARY KEY, bid REAL, ask REAL, "
              "delta REAL, gamma REAL, theta REAL, vega REAL, iv REAL, updated_epoch REAL NOT NULL)")
    return c


def set_quote(stream, bid, ask):
    c = _feed()
    c.execute("INSERT OR REPLACE INTO chain_marks (streamer_symbol, bid, ask, updated_epoch) VALUES (?,?,?,?)",
              (stream, bid, ask, _real_time.time()))
    c.commit()
    c.close()


class Market:
    """path: list of (from_t, bid, ask) for X_STREAM; a working buy fills at its limit when ask <= limit."""

    def __init__(self, broker, path, stream=X_STREAM, touch=True):
        self.b, self.path, self.stream, self.touch = broker, sorted(path), stream, touch
        self.cur = None
        self.step(CLOCK.t)

    def quote(self, t):
        q = None
        for t0, b, a in self.path:
            if t >= t0 - 1e-9:
                q = (b, a)
        return q

    def step(self, t):
        q = self.quote(t)
        if q != self.cur and q is not None:
            set_quote(self.stream, *q)
            self.cur = q
        if not self.touch or q is None:
            return
        for oid in self.b.working():
            o = self.b.order(oid)
            lim = abs(float(o.price))
            if q[1] <= lim + 1e-9:
                self.b.fill(oid, lim)


# ── wiring ───────────────────────────────────────────────────────────────────
PAGES, HB = [], []
BASE = _dt.datetime(2026, 11, 20, 10, 0, 0, tzinfo=_ET)


def _setup(start_et=BASE):
    CLOCK.t, CLOCK.sleeps, CLOCK.market = 0.0, 0, None
    OC.time = CLOCK
    EE.time = CLOCK
    EE.now_et = lambda: start_et + _dt.timedelta(seconds=CLOCK.t)
    EE.entries_open = lambda: True
    EE._hb_touch = lambda note="", *a, **k: HB.append((CLOCK.t, note)) or True
    EE.EntryEngine._page_if_working = staticmethod(lambda fill, what: PAGES.append(("working", what)))
    OG._page = lambda text: PAGES.append(("guard", text))
    OG.reset(boot_clean=True)
    BP.reset()
    LR.reset_all()
    if hasattr(EE, "_PINS"):
        EE._PINS.clear()
    PAGES.clear()
    HB.clear()
    LOG.clear()
    TS.cache_venue_rule("QQQ", [SimpleNamespace(threshold=None, value=0.01)])
    c = _feed()
    c.execute("DELETE FROM chain_marks")
    c.commit()
    c.close()


def contract(occ=X_OCC, stream=X_STREAM, strike=600.0, bid=3.40, ask=3.50):
    return OptionContract(symbol=occ, underlying="QQQ", expiry="2026-11-20", option_type="C", strike=strike,
                          bid=bid, ask=ask, mark=round((bid + ask) / 2, 4), streamer_symbol=stream)


def signal(c, strategy="LiquidityHunt", direction="long", side="call"):
    return SimpleNamespace(contract=c, strike=c.strike, expiry=c.expiry, entry_premium=c.mark,
                           strategy_name=strategy, setup_type="t", direction=direction, option_side=side)


def posts(b):
    return [round(-float(p), 4) for p in b.placed_prices]


def live():
    return EE.EntryEngine(paper_trading=False)


LOG = []


class _Grab(logging.Handler):
    def emit(self, r):
        LOG.append(r.getMessage())


_lg = logging.getLogger("execution.entry_engine")
_lg.addHandler(_Grab())
_lg.setLevel(logging.INFO)
_lg.propagate = False
for _n in ("execution.order_confirm", "execution.order_guard", "execution.tick_size", "execution.buying_power"):
    logging.getLogger(_n).setLevel(logging.CRITICAL)


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


class TimedBroker(MisbehavingBroker):
    """Records the fake time of every place_order call."""

    def __init__(self):
        super().__init__()
        self.post_t = []

    async def place_order(self, session, order, dry_run=False):
        self.post_t.append(CLOCK.t)
        return await super().place_order(session, order, dry_run)


def _run(fn):
    try:
        return fn()
    except Exception as exc:                                    # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"


# ── the checks ───────────────────────────────────────────────────────────────
def l1():
    _setup()
    b = TimedBroker()
    with bind(b, EE):
        CLOCK.market = Market(b, [(0, 3.40, 3.50)])
        r = live()._place_single_leg(signal(contract()), 1)
    p = posts(b)
    gap = (b.post_t[1] - b.post_t[0]) if len(b.post_t) > 1 else None
    hb = [n for _t, n in HB if n == "entry ladder"]
    ok = (r == (None, "", 0) and p == [3.42, 3.43] and gap is not None and 5.0 <= gap <= 8.0
          and all(x <= 3.45 + 1e-9 for x in p) and any("tick budget" in m for m in LOG) and len(hb) >= 1
          and b.working() == [])
    check("L1 one call posts 3.42 then 3.43 (5-8 s apart) on a static 3.40/3.50 book, stops on the tick budget, "
          "never above the mark, heartbeat touched between rungs", ok,
          f"posts {p} at {b.post_t} gap {gap} hb {len(hb)} working {b.working()} ret {r}")


def l2():
    out = {}
    for name, nb, na in (("up", 3.45, 3.55), ("down", 3.33, 3.43)):
        _setup()
        b = TimedBroker()
        with bind(b, EE):
            CLOCK.market = Market(b, [(0, 3.40, 3.50), (3.0, nb, na)])
            live()._place_single_leg(signal(contract()), 1)
        out[name] = posts(b)
    ok = (out["up"][:2] == [3.42, 3.48] and all(x <= 3.50 + 1e-9 for x in out["up"])
          and out["down"][:2] == [3.42, 3.38] and len(out["down"]) == 2)
    check("L2 drift re-prices the next rung from the streamed quote: up to 3.45/3.55 posts 3.48 (never above 3.50); "
          "down to 3.33/3.43 posts the new mark 3.38 (below the refused 3.42)", ok, f"{out}")


def l3():
    _setup()
    b = TimedBroker()
    with bind(b, EE):
        CLOCK.market = Market(b, [(0, 3.40, 3.50), (3.0, 3.37, 3.47)])
        live()._place_single_leg(signal(contract()), 1)
    p = posts(b)
    check("L3 the refused 3.42 is re-offered once it is the mark (book 3.37/3.47)", p[:2] == [3.42, 3.42], f"posts {p}")


def l4():
    res = {}
    # (a) the fill lands as the cancel arrives: the cancel raises "not cancellable"
    _setup()
    b = TimedBroker()

    orig = b.delete_order

    async def racing_delete(session, oid):
        o = b.order(oid)
        if len(b.accepted) == 2 and o.status in (OC.OrderStatus.LIVE,):
            b.fill(oid, abs(float(o.price)))
        return await orig(session, oid)
    b.delete_order = racing_delete
    with bind(b, EE):
        CLOCK.market = Market(b, [(0, 3.40, 3.50)], touch=False)
        r = live()._place_single_leg(signal(contract()), 1)
    res["a"] = (r, posts(b), b.position(X_OCC), len(b.filled()), LR.active())
    # (b) the cancel sits in Cancel Requested, then the fill lands
    _setup()
    b2 = TimedBroker()
    b2.cancel_mode = "pending"

    class M2(Market):
        def step(self, t):
            super().step(t)
            for oid in self.b.working():
                if self.b.order(oid).status == OC.OrderStatus.CANCEL_REQUESTED:
                    if len(self.b.accepted) == 1:
                        self.b.set_status(oid, "Cancelled")       # rung 1: the cancel completes
                    else:
                        self.b.fill(oid, abs(float(self.b.order(oid).price)))   # rung 2: filled in the race
    with bind(b2, EE):
        CLOCK.market = M2(b2, [(0, 3.40, 3.50)], touch=False)
        r2 = live()._place_single_leg(signal(contract()), 1)
    res["b"] = (r2, posts(b2), b2.position(X_OCC), len(b2.filled()), LR.active())
    ok = all(v[0][0] == 3.43 and v[0][2] == 1 and v[1] == [3.42, 3.43] and v[2] == 1 and v[3] == 1 and v[4] == 0
             for v in res.values())
    check("L4 a fill during the cancel (raced / Cancel Requested) is booked once: 1 @ 3.43, the broker holds 1, no "
          "third post, the walk cleared", ok, f"{res}")


def l5():
    # (a) the mark rung refused ends the call even with budget left
    _setup()
    b = TimedBroker()
    _orig = EE.EntryEngine.__dict__.get("_walk_budget_s")
    EE.EntryEngine._walk_budget_s = staticmethod(lambda: 60.0)
    try:
        with bind(b, EE):
            CLOCK.market = Market(b, [(0, 3.43, 3.45)])
            live()._place_single_leg(signal(contract(bid=3.43, ask=3.45)), 1)
    finally:
        if _orig is not None:
            EE.EntryEngine._walk_budget_s = _orig
        else:
            del EE.EntryEngine._walk_budget_s
    pa = posts(b)
    oka = pa == [3.43, 3.44] and any("mark rung was refused" in m for m in LOG)
    # (b) the window ends: LiquidityHunt 09:35-10:30, start 10:29:57
    _setup(start_et=_dt.datetime(2026, 11, 20, 10, 29, 57, tzinfo=_ET))
    b2 = TimedBroker()
    with bind(b2, EE):
        CLOCK.market = Market(b2, [(0, 3.40, 3.50)])
        live()._place_single_leg(signal(contract()), 1)
    pb = posts(b2)
    db = (LR.active(), dict(getattr(EE, "_PINS", {"r132": "no _PINS"})))
    okb = pb == [3.42] and any("entry window" in m and "ended" in m for m in LOG) and db == (0, {})
    # (c) the cancel cannot be confirmed: nothing posts beside it, this call or the next
    _setup()
    b3 = TimedBroker()
    b3.cancel_mode = "raise"
    with bind(b3, EE):
        CLOCK.market = Market(b3, [(0, 3.40, 3.50)])
        e = live()
        e._place_single_leg(signal(contract()), 1)
        n1 = b3.place_calls
        e._place_single_leg(signal(contract()), 1)
    okc = n1 == 1 and b3.place_calls == 1 and b3.working() == [b3.accepted[0]]
    check("L5a the mark rung refused ends the call (3.43/3.45 posts 3.43 then the mark 3.44, budget to spare)", oka,
          f"posts {pa}")
    check("L5b the strategy's window ending ends the walk after one rung and clears it (no walk, no pin)", okb,
          f"posts {pb} (walks, pins) {db}")
    check("L5c an unconfirmed cancel ends the call and the next call posts nothing beside it", okc,
          f"place calls {n1} then {b3.place_calls}, working {b3.working()}")


def l6():
    _setup()
    b = TimedBroker()
    fz = getattr(EE, "freeze_contract", None)
    det = {}
    with bind(b, EE):
        CLOCK.market = Market(b, [(0, 3.40, 3.50)])
        set_quote(Y_STREAM, 2.90, 3.00)
        e = live()
        e._place_single_leg(signal(contract()), 1)                 # tick 1: 3.42, 3.43 on 600C
        CLOCK.t += 3.0
        s2 = signal(contract(Y_OCC, Y_STREAM, 601.0, 2.90, 3.00))    # tick 2: the strategy re-picked 601C
        swapped = fz(s2, False) if fz else None
        det["swap"] = (swapped, s2.contract.symbol, s2.strike, s2.entry_premium)
        e._place_single_leg(s2, 1)
        det["posts"] = posts(b)
        det["legs"] = [b.order(o).legs[0].symbol for o in b.accepted]
        # a pin idle past PIN_IDLE_S, another strategy and the other direction are never frozen
        s_other = signal(contract(Y_OCC, Y_STREAM, 601.0, 2.90, 3.00), strategy="RunawayContinuation")
        s_short = signal(contract(Y_OCC, Y_STREAM, 601.0, 2.90, 3.00), direction="short", side="put")
        det["other"] = (fz(s_other, False) if fz else None, fz(s_short, False) if fz else None)
        CLOCK.t += float(getattr(EE, "PIN_IDLE_S", 45.0)) + 1.0
        s_idle = signal(contract(Y_OCC, Y_STREAM, 601.0, 2.90, 3.00))
        det["idle"] = fz(s_idle, False) if fz else None
    import inspect
    import main as MN
    src = inspect.getsource(MN._execute_entry_signal)
    i_fz, i_sz = src.find("_freeze_contract(signal"), src.find("_size_rec.size_for(")
    det["main"] = (i_fz, i_sz)
    ok = (det["swap"] == (True, X_OCC, 600.0, 3.45) and det["posts"][:3] == [3.42, 3.43, 3.44]
          and set(det["legs"]) == {X_OCC} and det["other"] == (False, False) and det["idle"] is False
          and 0 < i_fz < i_sz)
    check("L6 D3: a re-pick (601C) mid-walk is put back on 600C (re-quoted, mark 3.45) and the walk continues at 3.44; "
          "idle / other strategy / other direction are not frozen; main freezes before sizing", ok, f"{det}")


def l7():
    _setup()
    b = TimedBroker()
    with bind(b, EE):
        r = EE.EntryEngine(paper_trading=True)._place_single_leg(signal(contract()), 2)
        fz = getattr(EE, "freeze_contract", None)
        s_p = signal(contract(Y_OCC, Y_STREAM, 601.0))
        if hasattr(EE, "_PINS"):                                # a live pin on 600C exists; paper ignores it
            EE._PINS[EE._pin_id(s_p)] = {"contract": contract(), "key": "k", "seen": CLOCK.t}
        noop = (fz(s_p, True) if fz else False) or s_p.contract.symbol != Y_OCC
        if hasattr(EE, "_PINS"):
            EE._PINS.clear()
    ok = (r[0] == 3.45 and str(r[1]).startswith("PAPER-") and r[2] == 2 and b.place_calls == 0
          and not b.deleted and noop is False)
    check("L7 paper untouched: books the mark 3.45 x2 with a PAPER- id, no broker call; freeze_contract a no-op",
          ok, f"ret {r} place_calls {b.place_calls}")


def l8():
    _setup()
    b = TimedBroker()
    c = SimpleNamespace(symbol=X_OCC, bid=3.40, ask=3.50)
    sg = SimpleNamespace(contract=c, entry_premium=3.45, strategy_name="LiquidityHunt", setup_type="t",
                         direction="long", option_side="call", strike=600.0, expiry="2026-11-20")
    with bind(b, EE):
        CLOCK.market = Market(b, [(0, 3.40, 3.50)])
        e = live()
        n = []
        for _ in range(3):
            e._place_single_leg(sg, 1)
            n.append(b.place_calls)
    ok_a = n == [1, 2, 3] and posts(b) == [3.42, 3.43, 3.44]
    try:
        from execution.exit_engine import ExitEngine
        LR.reset_all()
        xe = ExitEngine.__new__(ExitEngine)
        rec = {"trade_id": "ladder5s-0001", "symbol": "QQQ", "option_symbol": X_OCC}
        sells = []
        for _ in range(4):
            px, _why = xe._exit_limit(rec, "target", 3.45, "sell", "single", quote=(3.40, 3.50))
            sells.append(round(px, 4))
            xe._exit_walk_refused(rec, px)
        ok_b = sells == [3.48, 3.47, 3.46, 3.45]
    except Exception as exc:                                    # noqa: BLE001
        ok_b, sells = False, f"{type(exc).__name__}: {exc}"
    ok_c = config.LIVE_STOP_AT_BID_AFTER == 2 and config.LIVE_STOP_MARKET_AFTER == 3
    check("L8 no streamer symbol -> one rung per call (3.42, 3.43, 3.44 over three calls); exits unchanged "
          "(3.48, 3.47, 3.46, 3.45); live stop constants 2 / 3", ok_a and ok_b and ok_c,
          f"calls {n} posts {posts(b)} sells {sells}")


def main():
    print("check_entry_ladder_5s")
    for fn in (l1, l2, l3, l4, l5, l6, l7, l8):
        r = _run(fn)
        if isinstance(r, str):
            check(f"{fn.__name__.upper()} raised", False, r)
    if FAILED:
        print(f"\nRED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("\nGREEN — 10 of 10")
    return 0


if __name__ == "__main__":
    sys.exit(main())
