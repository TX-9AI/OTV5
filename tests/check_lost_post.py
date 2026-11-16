#!/usr/bin/env python3
"""
tests/check_lost_post.py  v5.0
v5.0  2026-11-16  OTV5 r127 (LOP.1, FA.1; the cold audit 2026-11-15, critical) — NEW. A place_order THAT RAISES NEVER LETS
      THE SAME INTENT POST A SECOND ORDER BESIDE A LIVE ONE.

  🔴 THE DEFECT (OTV5 r126 61a5acb): execution/entry_engine._place_single_leg and main._post_credit_vertical ran
  order_guard.after_failure only when place_order had RETURNED. When it raised after the broker accepted the order
  (the reply lost, run_async's 30 s TimeoutError while the coroutine completes, a reset mid-read) nothing was
  cancelled, nothing was a suspect and the boot sweep stayed "clean", so the next tick posted the next rung:
  two contracts at the broker, one (or none) in the DB, the extra one with no stop and no EOD flatten.

  OFFLINE, on the shared misbehaving broker (tests/broker_harness.py; no network, no credentials):
  L1  single leg: rung 1 accepted, reply lost, order rests LIVE -> the order is CANCELLED, the next tick posts
      NOTHING, and the broker holds no working order and no position
  L2  single leg: rung 1 accepted, reply lost, order FILLED at once -> the next ticks post NOTHING; the broker
      holds exactly 1 contract (not 2) and the intent stays blocked
  L3  single leg: the order is still in flight (not in the book for two reads) -> the next tick inside the grace
      posts nothing; once the book shows it, it is cancelled and still nothing is posted beside it
  L4  single leg: place_order raised and the broker accepted NOTHING -> blocked inside the grace, then the intent
      clears and the next tick posts (and fills) one order: a refused post costs a tick, never the trade
  L5  single leg: the broker's book is UNREADABLE after the failed post -> blocked (fail closed)
  L6  credit vertical (main._post_credit_vertical, the entry's and the remainder supervisor's one placer): reply
      lost, order LIVE -> cancelled; the next call posts nothing
  L7  credit vertical: reply lost, order FILLED -> the next call posts nothing; the broker holds one vertical
  L8  paper: _place_single_leg never reaches the broker and registers no suspect
  L9  a close order on the same contract is never cancelled by a lost-post resolution
  BORN RED on r126 61a5acb at L1-L7 (L2: the broker held 3 contracts, L7: 3 verticals); L8 and L9 hold there too.

Run:  python3 tests/check_lost_post.py
"""
import contextlib
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
import config                                                         # noqa: E402
config.LOG_FILE = os.path.join(tempfile.mkdtemp(prefix="check_lost_post_"), "bot.log")
config.LIVE_FILL_POLL_SECONDS = 0.0
from broker_harness import MisbehavingBroker, bind                    # noqa: E402

PROBLEMS = []
SYM = "QQQ   261116C00500000"


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


class _C:
    def __init__(self, sym, bid, ask, strike=0.0):
        self.symbol, self.bid, self.ask, self.strike = sym, bid, ask, strike


class _Sig:
    strategy = strategy_name = "RunawayContinuation"
    entry_premium = 1.00

    def __init__(self):
        self.contract = _C(SYM, 0.90, 1.10)


@contextlib.contextmanager
def _no_grace(G):
    """LOST_GRACE_S = 0 for the block (absent on a tree without the fix: then nothing to change)."""
    had = hasattr(G, "LOST_GRACE_S")
    old = getattr(G, "LOST_GRACE_S", None)
    if had:
        G.LOST_GRACE_S = 0.0
    try:
        yield
    finally:
        if had:
            G.LOST_GRACE_S = old


def _engine(paper=False):
    import execution.entry_engine as EE
    eng = EE.EntryEngine.__new__(EE.EntryEngine)
    eng.paper_trading = paper
    return EE, eng


def _fresh():
    from execution import order_guard as G
    from execution import ladder_registry as LR
    G.reset()
    LR.reset_all()
    return G


def single_leg_cases():
    EE, eng = _engine()

    # L1 — lost reply, order rests LIVE
    G = _fresh(); b = MisbehavingBroker(); b.script_place("lost")
    with bind(b, EE):
        r1 = eng._place_single_leg(_Sig(), 1)
        r2 = eng._place_single_leg(_Sig(), 1)
        r3 = eng._place_single_leg(_Sig(), 1)
    check("L1 lost reply + LIVE order: cancelled, the next ticks post NOTHING, the broker is flat",
          r1 == (None, "", 0) and r2 == (None, "", 0) and r3 == (None, "", 0)
          and b.accepted == ["O1"] and b.place_calls == 1 and "O1" in b.deleted
          and b.working() == [] and b.positions() == {},
          f"place_calls={b.place_calls} accepted={b.accepted} deleted={b.deleted} working={b.working()} "
          f"positions={b.positions()}")

    # L2 — lost reply, the order FILLED at the broker
    G = _fresh(); b = MisbehavingBroker(); b.fill_on_accept = 0.95; b.script_place("lost")
    with bind(b, EE):
        eng._place_single_leg(_Sig(), 1)
        with _no_grace(G):
            eng._place_single_leg(_Sig(), 1)
            eng._place_single_leg(_Sig(), 1)
            ok_post, why = G.clear_to_post(f"{SYM}|open|single", object(), b)
    check("L2 lost reply + FILLED order: nothing posts beside it, the broker holds 1 contract, intent blocked",
          b.place_calls == 1 and b.position(SYM) == 1 and not ok_post and "FILLED" in why,
          f"place_calls={b.place_calls} positions={b.positions()} clear={ok_post} {why}")

    # L3 — still in flight: invisible to the book for the next two reads
    G = _fresh(); b = MisbehavingBroker(); b.script_place("lost", hidden_reads=2)
    with bind(b, EE):
        eng._place_single_leg(_Sig(), 1)             # read 1 (after_lost_post): not visible
        eng._place_single_leg(_Sig(), 1)             # read 2 (clear_to_post): not visible, inside the grace
        calls_in_grace = b.place_calls
        eng._place_single_leg(_Sig(), 1)             # read 3: visible -> cancelled
    check("L3 in-flight order: nothing posts inside the grace; once visible it is cancelled, still no second post",
          calls_in_grace == 1 and b.place_calls == 1 and "O1" in b.deleted and b.working() == [],
          f"in_grace={calls_in_grace} place_calls={b.place_calls} deleted={b.deleted} working={b.working()}")

    # L4 — raised, nothing accepted: blocked inside the grace, then it posts once
    G = _fresh(); b = MisbehavingBroker(); b.fill_on_accept = 0.95; b.script_place("raise")
    with bind(b, EE):
        eng._place_single_leg(_Sig(), 1)
        eng._place_single_leg(_Sig(), 1)
        calls_in_grace = b.place_calls
        _s = G._SUSPECT.get(f"{SYM}|open|single")
        if _s:
            _s["ts"] -= getattr(G, "LOST_GRACE_S", 0.0) + 1
        r = eng._place_single_leg(_Sig(), 1)
    check("L4 raised with nothing accepted: blocked inside the grace, then posts ONE order that fills",
          calls_in_grace == 1 and b.place_calls == 2 and b.accepted == ["O1"] and b.position(SYM) == 1
          and r[0] is not None and r[2] == 1,
          f"in_grace={calls_in_grace} place_calls={b.place_calls} accepted={b.accepted} r={r}")

    # L5 — the book is unreadable
    G = _fresh(); b = MisbehavingBroker(); b.script_place("lost"); b.live_orders_raise = True
    with bind(b, EE):
        eng._place_single_leg(_Sig(), 1)
        with _no_grace(G):
            eng._place_single_leg(_Sig(), 1)
            ok_post, why = G.clear_to_post(f"{SYM}|open|single", object(), b)
    check("L5 unreadable book after a failed post: blocked (fail closed)",
          b.place_calls == 1 and not ok_post and "unreadable" in why,
          f"place_calls={b.place_calls} clear={ok_post} {why}")

    # L8 — paper never reaches the broker
    G = _fresh(); b = MisbehavingBroker(); b.script_place("lost")
    EEp, engp = _engine(paper=True)
    with bind(b, EEp):
        rp = engp._place_single_leg(_Sig(), 1)
    check("L8 paper: no broker call, no suspect, a paper fill",
          b.place_calls == 0 and G._SUSPECT == {} and rp[0] is not None and str(rp[1]).startswith("PAPER-"),
          f"place_calls={b.place_calls} suspects={list(G._SUSPECT)} r={rp}")

    # L9 — a close order on the same contract is not a candidate
    from types import SimpleNamespace
    G = _fresh(); b = MisbehavingBroker()
    import asyncio
    close = asyncio.run(b.place_order(None, SimpleNamespace(price=0.5, legs=[
        SimpleNamespace(symbol=SYM, action="SELL_TO_CLOSE", quantity=1)]))).order
    if hasattr(G, "after_lost_post"):
        G.after_lost_post(f"{SYM}|open|single", [SYM], object(), b, "probe")
    check("L9 a working CLOSE on the same contract is never cancelled by a lost-post resolution",
          close.id not in b.deleted and b.working() == [close.id],
          f"deleted={b.deleted} working={b.working()}")


def credit_cases():
    import main as M
    sc = _C("QQQ   261116P00495000", 0.50, 0.60, 495.0)
    lc = _C("QQQ   261116P00490000", 0.20, 0.30, 490.0)
    key = "cv:QQQ:IronCondorStrategy:put"

    def post():
        try:
            return M._post_credit_vertical(sc, lc, 1, key, f"{sc.symbol}|{lc.symbol}", mark_fallback=0.30)
        except Exception as exc:                                      # noqa: BLE001
            return exc

    # L6 — lost reply, LIVE
    G = _fresh(); b = MisbehavingBroker(); b.script_place("lost")
    with bind(b, M):
        r1 = post(); r2 = post()
    check("L6 credit vertical, lost reply + LIVE: cancelled, the next call posts nothing",
          isinstance(r1, Exception) and b.place_calls == 1 and "O1" in b.deleted and b.working() == []
          and b.positions() == {},
          f"r1={r1!r} place_calls={b.place_calls} deleted={b.deleted} working={b.working()} pos={b.positions()}")

    # L7 — lost reply, FILLED
    G = _fresh(); b = MisbehavingBroker(); b.fill_on_accept = 0.30; b.script_place("lost")
    with bind(b, M):
        post()
        with _no_grace(G):
            post(); post()
    check("L7 credit vertical, lost reply + FILLED: nothing posts beside it; the broker holds ONE vertical",
          b.place_calls == 1 and b.position(sc.symbol) == -1 and b.position(lc.symbol) == 1,
          f"place_calls={b.place_calls} positions={b.positions()}")


def main():
    for fn in (single_leg_cases, credit_cases):
        try:
            fn()
        except Exception as exc:                                      # noqa: BLE001
            import traceback
            traceback.print_exc()
            check(f"{fn.__name__} runs", False, f"{type(exc).__name__}: {exc}")
    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — a place_order that raises never lets the same intent post beside a live order")
    return 0


if __name__ == "__main__":
    sys.exit(main())
