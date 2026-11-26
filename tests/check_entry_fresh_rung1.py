#!/usr/bin/env python3
"""
tests/check_entry_fresh_rung1.py — v5.0
v5.0  2026-11-26  OTV5 r162 (FILL.4; the before-cash audit 2026-11-22 F4, the cash-readiness review 2026-11-25) — new.
      THE FIRST RUNG OF A LIVE ENTRY IS PRICED ON THE STREAMED QUOTE AS IT STANDS AT POSTING, NOT THE TICK'S COPY.
      2026-11-25: SPX PARK 7010P priced rung 1 on the tick's 29.7 / 29.9 (3.4 s old) against a streamed 29.2 / 29.5 -
      the rung was marketable and paid the 29.50 ask over the 29.35 mark; QQQ Runaway 606P on 3.54 / 3.56 (5.7 s old)
      against 3.63 / 3.66 - the rung could not fill and cost a rung deadline.
DRIVEN THROUGH THE REAL PATH, as tests/check_entry_ladder_5s.py drives it: EntryEngine._place_single_leg -> the real
order_guard, buying_power, ladder_registry, entry_ladder, tick_size and order_confirm.confirm_order_fill against
tests/broker_harness.MisbehavingBroker (every broker method counted), the streamed quote read from a scratch
feed_store.db chain_marks row through the real OptionsChainFetcher._read_marks. The clock is fake (it moves only when
the code sleeps; each sleep runs a strict-touch market: a working buy fills at its limit once the ask is at or below
it). QQQ, venue rule 0.01. The contract's own bid / ask is the TICK's quote; the chain_marks row is the stream's.
  F1  the book moved DOWN (tick 29.70 / 29.90, stream 29.20 / 29.50, mark 29.35): rung 1 is the fresh table's first
      rung 29.27, no rung is posted above the fresh mark 29.35 and nothing fills (on the tick's table rung 1 was 29.75,
      over the stream's ask: a fill above the mark)
  F2  the book moved UP (tick 3.54 / 3.56, stream 3.63 / 3.66): rung 1 is on the fresh grid, 3.63 (the tick's table
      gave 3.54, unfillable), then 3.64 - the fresh table, never above the fresh mark 3.645
  F3  the WHOLE walk is the fresh quote's: tick 3.40 / 3.50, stream 3.43 / 3.45: 3.43, then the fresh mark rung 3.44,
      and the walk hands back on the MARK RUNG refused (the stop reads the fresh table), with budget to spare
  F4  no fresh streamed quote (a) no chain_marks row, (b) a row older than OT_CHAIN_STALE_S: nothing posts, ZERO
      broker calls, one "[ladder] ... not posted - no fresh streamed quote" line (the walk's own rule after a refusal)
  F5  a contract with no streamer symbol keeps the tick's quote (the r132 shape): 3.42, one rung
  F6  ZERO ADDED BROKER CALLS: a stale tick quote under a 3.40 / 3.50 stream makes exactly the broker calls, in order,
      and the posts, of the same entry whose tick quote already was 3.40 / 3.50
  F7  the first rung's [ladder] line names the streamed quote, its age (<= 1 s here) and the tick's quote
  F8  PAPER unchanged: a paper entry on a stale quote books paper_fill_price(entry_premium), never reads the stream,
      reaches no broker call; the paper battery's digest equals PAPER_DIGEST (measured on r161 a235fd4)
  F9  THE WALL unchanged: execution/paper_wall.PaperWallEntry on a stale quote makes ZERO broker calls and never reads
      the stream
Born red on r161 (a235fd4) at F1, F2, F3, F4, F6 and F7; F5, F8 and F9 pin unchanged behaviour and pass there.
Mutants (each red): the fresh read removed (r161: F1 F2 F3 F4 F6 F7); read but not priced on (F1 F2 F3 F6 F7); a missing
fresh quote falls back to the tick's (F4); the streamer-symbol guard dropped (F5); the read moved above the paper
return (F8 F9).
Run:  python3 tests/check_entry_fresh_rung1.py
"""
import datetime as _dt
import hashlib
import json
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
_TD = tempfile.mkdtemp(prefix="check_entry_fresh_rung1.")
for _k, _v in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"),
               ("OT_FEED_DB", "f.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_PLAN_STATES_FILE", "ps.json"),
               ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT")):
    os.environ.setdefault(_k, os.path.join(_TD, _v))
os.environ["OT_INSTRUMENT"] = "QQQ"
FAILED = []

try:
    import config                                               # noqa: E402,F401
    from execution import entry_engine as EE                    # noqa: E402
    from execution import order_confirm as OC                   # noqa: E402
    from execution import ladder_registry as LR                 # noqa: E402
    from execution import order_guard as OG                     # noqa: E402
    from execution import buying_power as BP                    # noqa: E402
    from execution import tick_size as TS                       # noqa: E402
    from execution import paper_wall as PW                      # noqa: E402
    from execution.limit_ladder import paper_fill_price         # noqa: E402
    from data.options_chain import OptionContract, OT_CHAIN_STALE_S   # noqa: E402
    from broker_harness import MisbehavingBroker, bind          # noqa: E402
except Exception as exc:                                        # noqa: BLE001
    print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
    sys.exit(2)

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:                                               # noqa: BLE001
    _ET = _dt.timezone(_dt.timedelta(hours=-5))

OCC, STREAM = "QQQ   261130P00606000", ".QQQ261130P606"
# PAPER_DIGEST: the F8 paper battery's (price, qty, id prefix, broker calls, stream reads), measured on r161 a235fd4.
PAPER_DIGEST = "7731bf18e0916b6d"


class Clock:
    def __init__(self):
        self.t, self.market, self.sleeps = 0.0, None, 0

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


def set_quote(stream, bid, ask, age_s=0.0):
    c = _feed()
    c.execute("INSERT OR REPLACE INTO chain_marks (streamer_symbol, bid, ask, updated_epoch) VALUES (?,?,?,?)",
              (stream, bid, ask, _real_time.time() - age_s))
    c.commit()
    c.close()


class Market:
    """The stream's (bid, ask), written to chain_marks at t=0; a working buy fills at its limit when ask <= limit."""

    def __init__(self, broker, bid, ask, touch=True):
        self.b, self.q, self.touch = broker, (bid, ask), touch
        set_quote(STREAM, bid, ask)

    def step(self, t):
        if not self.touch:
            return
        for oid in self.b.working():
            lim = abs(float(self.b.order(oid).price))
            if self.q[1] <= lim + 1e-9:
                self.b.fill(oid, lim)


class CountingBroker(MisbehavingBroker):
    """Every broker method call, in order, by name."""

    def __init__(self):
        super().__init__()
        self.calls = []

    async def place_order(self, session, order, dry_run=False):
        self.calls.append("place_order")
        return await super().place_order(session, order, dry_run)

    async def get_order(self, session, oid):
        self.calls.append("get_order")
        return await super().get_order(session, oid)

    async def get_live_orders(self, session):
        self.calls.append("get_live_orders")
        return await super().get_live_orders(session)

    async def delete_order(self, session, oid):
        self.calls.append("delete_order")
        return await super().delete_order(session, oid)

    async def get_positions(self, session, **kw):
        self.calls.append("get_positions")
        return await super().get_positions(session, **kw)

    async def get_balances(self, session, currency="USD"):
        self.calls.append("get_balances")
        return await super().get_balances(session, currency)


LOG, READS = [], []
_REAL_FRESH = EE.EntryEngine.__dict__["_fresh_quote"]


def _counting_fresh(contract):
    READS.append(str(getattr(contract, "streamer_symbol", "") or ""))
    return _REAL_FRESH.__func__(contract)


EE.EntryEngine._fresh_quote = staticmethod(_counting_fresh)
BASE = _dt.datetime(2026, 11, 30, 10, 0, 0, tzinfo=_ET)


def _setup():
    CLOCK.t, CLOCK.sleeps, CLOCK.market = 0.0, 0, None
    OC.time = CLOCK
    EE.time = CLOCK
    EE.now_et = lambda: BASE + _dt.timedelta(seconds=CLOCK.t)
    EE.entries_open = lambda: True
    EE._hb_touch = lambda note="", *a, **k: True
    EE.EntryEngine._page_if_working = staticmethod(lambda fill, what: None)
    OG._page = lambda text: None
    OG.reset(boot_clean=True)
    BP.reset()
    LR.reset_all()
    EE._PINS.clear()
    LOG.clear()
    READS.clear()
    TS.cache_venue_rule("QQQ", [SimpleNamespace(threshold=None, value=0.01)])
    c = _feed()
    c.execute("DELETE FROM chain_marks")
    c.commit()
    c.close()


def contract(bid, ask, stream=STREAM, epoch_age=4.0):
    c = OptionContract(symbol=OCC, underlying="QQQ", expiry="2026-11-30", option_type="P", strike=606.0,
                       bid=bid, ask=ask, mark=round((bid + ask) / 2, 4), streamer_symbol=stream)
    c.quote_epoch = _real_time.time() - epoch_age
    return c


def signal(c, strategy="RunawayContinuation"):
    return SimpleNamespace(contract=c, strike=c.strike, expiry=c.expiry, entry_premium=c.mark,
                           strategy_name=strategy, setup_type="t", direction="short", option_side="put")


def posts(b):
    return [round(-float(p), 4) for p in b.placed_prices]


class _Grab(logging.Handler):
    def emit(self, r):
        LOG.append(r.getMessage())


_lg = logging.getLogger("execution.entry_engine")
_lg.addHandler(_Grab())
_lg.setLevel(logging.INFO)
_lg.propagate = False
for _n in ("execution.order_confirm", "execution.order_guard", "execution.tick_size", "execution.buying_power",
           "data.options_chain"):
    logging.getLogger(_n).setLevel(logging.CRITICAL)


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def _live_run(tick_bid, tick_ask, stream_q, touch=True, stream=STREAM, stale_row=None):
    """One live call. stream_q: (bid, ask) written to chain_marks, or None for no row. -> (ret, posts, broker)."""
    _setup()
    b = CountingBroker()
    with bind(b, EE):
        if stream_q is not None:
            CLOCK.market = Market(b, *stream_q, touch=touch)
        if stale_row is not None:
            set_quote(STREAM, *stale_row, age_s=OT_CHAIN_STALE_S + 180.0)
        r = EE.EntryEngine(paper_trading=False)._place_single_leg(signal(contract(tick_bid, tick_ask, stream)), 1)
    return r, posts(b), b


def _guard(fn, label):
    try:
        fn()
    except Exception as exc:                                    # noqa: BLE001
        check(f"{label} raised", False, f"{type(exc).__name__}: {exc}")


def f1():
    r, p, b = _live_run(29.70, 29.90, (29.20, 29.50))
    ok = bool(p) and p[0] == 29.27 and all(x <= 29.35 + 1e-9 for x in p) and r == (None, "", 0) and not b.filled()
    check("F1 book moved DOWN (tick 29.70/29.90, stream 29.20/29.50): rung 1 = 29.27 on the fresh table, no rung above "
          "the fresh mark 29.35, no fill", ok, f"posts {p} ret {r} filled {len(b.filled())}")


def f2():
    r, p, b = _live_run(3.54, 3.56, (3.63, 3.66), touch=False)
    ok = p[:2] == [3.63, 3.64] and all(x <= 3.645 + 1e-9 for x in p)
    check("F2 book moved UP (tick 3.54/3.56, stream 3.63/3.66): rung 1 = 3.63 on the fresh grid, then 3.64, never "
          "above the fresh mark 3.645", ok, f"posts {p} ret {r}")


def f3():
    r, p, b = _live_run(3.40, 3.50, (3.43, 3.45), touch=False)
    ok = p == [3.43, 3.44] and any("the mark rung was refused" in m for m in LOG) and r == (None, "", 0)
    check("F3 the whole walk is the fresh quote's: tick 3.40/3.50, stream 3.43/3.45 -> 3.43, the fresh mark 3.44, then "
          "the mark-rung stop", ok, f"posts {p} stop {[m for m in LOG if 'REFUSED' in m][-1:]}")


def f4():
    res = {}
    for name, kw in (("no row", dict(stream_q=None)), ("stale row", dict(stream_q=None, stale_row=(3.40, 3.50)))):
        r, p, b = _live_run(3.54, 3.56, **kw)
        line = [m for m in LOG if "not posted" in m and "no fresh streamed quote" in m]
        res[name] = (r, p, list(b.calls), len(line))
    ok = all(v[0] == (None, "", 0) and v[1] == [] and v[2] == [] and v[3] == 1 for v in res.values())
    check("F4 no fresh streamed quote (no row / a row past OT_CHAIN_STALE_S): nothing posts, ZERO broker calls, one "
          "'not posted - no fresh streamed quote' line", ok, f"{res}")


def f5():
    r, p, b = _live_run(3.40, 3.50, (3.60, 3.70), stream="", touch=False)
    ok = p == [3.42] and r == (None, "", 0) and READS[:1] == [""]
    check("F5 no streamer symbol: the tick's quote, one rung 3.42 (the r132 shape)", ok, f"posts {p} reads {READS}")


def f6():
    _r0, p0, b0 = _live_run(3.40, 3.50, (3.40, 3.50), touch=False)
    _r1, p1, b1 = _live_run(3.30, 3.36, (3.40, 3.50), touch=False)
    ok = p0 == p1 == [3.42, 3.43] and b0.calls == b1.calls and len(b1.calls) > 0
    check("F6 ZERO ADDED BROKER CALLS: a stale tick quote makes the same broker calls, in order, and the same posts "
          "as a fresh one", ok, f"posts {p0} / {p1}; calls {len(b0.calls)} / {len(b1.calls)} "
          f"equal={b0.calls == b1.calls}")


def f7():
    _live_run(29.70, 29.90, (29.20, 29.50))
    line = [m for m in LOG if "first rung priced on the streamed quote" in m]
    ok = False
    if line:
        m = line[0]
        try:
            age = float(m.split("29.20 / 29.50 (")[1].split(" s old")[0])
        except (IndexError, ValueError):
            age = None
        ok = age is not None and age <= 1.0 and "the tick's 29.70 / 29.90" in m
    check("F7 the first rung's line names the streamed quote, its age (<= 1 s) and the tick's quote", ok, f"{line[:1]}")


def _paper_battery(engine_cls):
    out = []
    for tb, ta, sq in ((29.70, 29.90, (29.20, 29.50)), (3.54, 3.56, (3.63, 3.66)), (3.40, 3.50, None),
                       (0.00, 0.05, (0.01, 0.06))):
        _setup()
        b = CountingBroker()
        with bind(b, EE):
            if sq is not None:
                set_quote(STREAM, *sq)
            sig = signal(contract(tb, ta))
            px, oid, q = engine_cls()._place_single_leg(sig, 3)
        out.append((px, q, str(oid)[:6], list(b.calls), list(READS), paper_fill_price(float(sig.entry_premium or 0.0),
                                                                                      floor=0.01)))
    return out


def f8():
    out = _paper_battery(lambda: EE.EntryEngine(paper_trading=True))
    dg = hashlib.sha256(json.dumps(out, default=str, sort_keys=True).encode()).hexdigest()[:16]
    print(f"       (F8 paper digest {dg})")
    ok = (all(o[0] == o[5] and o[1] == 3 and o[2] == "PAPER-" and o[3] == [] and o[4] == [] for o in out)
          and dg == PAPER_DIGEST)
    check("F8 PAPER unchanged: books paper_fill_price(entry_premium), no stream read, no broker call; digest "
          "PAPER_DIGEST", ok, f"digest={dg} want={PAPER_DIGEST} {out}")


def f9():
    out = _paper_battery(PW.PaperWallEntry)
    ok = all(o[3] == [] and o[4] == [] and o[2] == "PAPER-" for o in out)
    check("F9 THE WALL unchanged: PaperWallEntry makes ZERO broker calls and never reads the stream", ok, f"{out}")


def main():
    print("check_entry_fresh_rung1")
    for fn, label in ((f1, "F1"), (f2, "F2"), (f3, "F3"), (f4, "F4"), (f5, "F5"), (f6, "F6"), (f7, "F7"),
                      (f8, "F8"), (f9, "F9")):
        _guard(fn, label)
    if FAILED:
        print(f"\nRED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("\nGREEN — 9 of 9")
    return 0


if __name__ == "__main__":
    sys.exit(main())
