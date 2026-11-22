#!/usr/bin/env python3
"""
tests/check_live_stop_escalation.py  v5.3
v5.3  2026-11-22  OTV5 r144 (EXIT.19; the before-cash audit 2026-11-22 F1) — A THESIS-INVALIDATED EXIT ESCALATES AS A STOP.
      On a one-tick book (QQQ bid 1.00 / ask 1.01, mark 1.005), driven through the same real _confirm_and_book_live_exit:
  E8  runaway_thesis_dead posts the floor escalation: LIMIT 1.01 (the mark on the grid, sell rounds up), LIMIT 1.01, LIMIT
      AT THE BID 1.00, MARKET - and makes exactly the broker calls the hard stop makes over the same four passes
  E9  hunt_thesis_dead (a LiquidityHunt row) likewise
  E10 runaway_backstop likewise
  E11 the rejected-pool handoff ("handoff: pool ...") likewise
  E12 orb_trail_stop still walks on that book: four passes, all LIMIT, never the bid, no MARKET
  E13 park_lock (a PARK row) still walks likewise; ogap_trail (an OGAP row) likewise
  E14 the policy of every exit reason Runaway, the Hunt, PARK and OGAP can write (their real formats): exactly the
      thesis line, the backstop, the handoff and the existing stops are floor; every lock, trail, fizzle, theta, decay,
      target, PARK delta / close and OGAP sweep / close walks; the hard closes keep their EOD policies
  E15 each r144 key catches only its own reasons (no key matches a walk reason), and no management intent declares a
      pricing for a thesis / backstop / handoff close (strategy/management EXIT_PRICING; the calculator's condition)
  E16 PAPER is unchanged: every reason above books at the mark in one pass (the paper close never reads _exit_policy);
      the digest of the paper results is the one r143 produced
Born red on r143 (927f74c) at E8 E9 E10 E11 E14 E15.
v5.2  2026-11-15  OTV5 r123 (HYG.27) — OT_RESTING_DB leaves the scratch env (r118 deleted execution/resting_orders.py, its only reader).
v5.1  2026-11-14  OTV5 r112 (AM.2 / LIVE.6) — new. A LIVE STOP STEPS TO THE BID, THEN CROSSES. Driven through the REAL
      ExitEngine._confirm_and_book_live_exit with a stub broker whose every order dies UNFILLED (CANCELLED, no legs), so
      each pass is one unfilled close and the record carries the count to the next pass, as the live retry loop does.

  E1  a hard stop on a long single: pass 1 and pass 2 post LIMIT at the mark (1.10 here)
  E2  pass 3 (config.LIVE_STOP_AT_BID_AFTER = 2 unfilled) posts LIMIT AT THE BID (1.00)
  E3  pass 4 (config.LIVE_STOP_MARKET_AFTER = 3 unfilled) posts a MARKET order
  E4  a target close (walk policy) never escalates: four unfilled passes, no MARKET, none at the bid
  E5  an adopted SHORT's stop buys back AT THE ASK on its third pass (1.20), then MARKET
  E6  at the touch step with no fresh quote (no ask stashed) the stop crosses with MARKET
  E7  the constants are what the spec says (2 and 3) and are not env keys (no OT_ read in config for them)
Born red on r108 (6b380b2): E2 E3 E5 E6 E7 (every pass re-posted at the mark).
Run:  python3 tests/check_live_stop_escalation.py   (needs the venv's tastytrade)
"""
import datetime as D
import logging
import os
import re
import sys
import tempfile
import types
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
_s = tempfile.mkdtemp(prefix="check_live_stop_escalation.")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived_store.db"),
               ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_ALERT_SPOOL", "alert_spool.jsonl")):
    os.environ.setdefault(_k, os.path.join(_s, _f))
ET = ZoneInfo("America/New_York")
FAILED = []
PAPER_DIGEST = "894db8cfed3eb92b"   # E16: the paper results' digest on r143 (927f74c), identical on r144


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


class _Acct:
    """Records every order; every order dies unfilled."""
    def __init__(self):
        self.orders = []

        self.calls = []

    def place_order(self, session, order, dry_run=False):
        self.calls.append("place_order")
        self.orders.append(order)
        return types.SimpleNamespace(errors=None, order=types.SimpleNamespace(id=f"O{len(self.orders)}"))

    def get_order(self, session, oid):
        self.calls.append("get_order")
        from tastytrade.order import OrderStatus
        return types.SimpleNamespace(id=oid, status=OrderStatus.CANCELLED, legs=[], reject_reason=None)

    def delete_order(self, session, oid):
        self.calls.append("delete_order")
        return None


def _desc(o):
    p = getattr(o, "price", None)
    return (str(getattr(o.order_type, "value", o.order_type)), None if p is None else abs(float(p)))


def main():
    print("check_live_stop_escalation")
    try:
        from tastytrade.order import OrderType
    except ImportError as exc:
        print(f"NOT RUN — this interpreter cannot import tastytrade ({exc}); run under the venv")
        return 2
    import config as _cfg
    _cfg.LIVE_FILL_POLL_SECONDS = 0.0
    _cfg.LIVE_FILL_DEADLINE_SECONDS = 0.0
    logging.getLogger("execution.tick_size").setLevel(logging.ERROR)
    import utils.time_utils as TU
    import execution.exit_engine as EE
    import database.trade_logger as TL
    from execution import ladder_registry as LR

    now = D.datetime(2026, 11, 13, 10, 40, 5, tzinfo=ET)
    EE.now_et = lambda: now
    TU.now_et = lambda: now
    acct = {"a": _Acct()}
    EE.get_session, EE.get_account = (lambda: "S"), (lambda: acct["a"])
    tl = TL.get_trade_logger()
    live = EE.ExitEngine(paper_trading=False)
    live._alert_live_exit_once = lambda tid, kind, msg: None

    def single(tid, **kw):
        r = TL.make_record(trade_id=tid, symbol="QQQ", strategy="RunawayContinuation", setup_type="runaway",
                           direction="long", option_side="call", contracts=2, entry_premium=1.40,
                           total_cost=280.0, max_loss=280.0, stop_premium=1.12, strike=700.0,
                           option_symbol="QQQ   261113C00700000", expiry="2026-11-13")
        r.update(kw)
        tl.log_entry(r)
        return r

    def passes(rec, reason, n, mark=1.10, bid=1.00, ask=1.20):
        acct["a"] = _Acct()
        LR.reset_all()
        for _ in range(n):
            if bid is not None:
                rec["_exit_bid"], rec["_exit_ask"] = bid, ask
            else:
                rec.pop("_exit_bid", None); rec.pop("_exit_ask", None)
            live._confirm_and_book_live_exit(rec, reason, mark)
        return [_desc(o) for o in acct["a"].orders]

    got = passes(single("E1-long"), "hard_stop_20% pnl=-21.0%", 4)
    check("E1 hard stop, passes 1-2: LIMIT at the mark 1.10", got[:2] == [("Limit", 1.10), ("Limit", 1.10)], f"{got}")
    check("E2 pass 3 (after 2 unfilled): LIMIT AT THE BID 1.00", len(got) > 2 and got[2] == ("Limit", 1.00), f"{got}")
    check("E3 pass 4 (after 3 unfilled): MARKET", len(got) > 3 and got[3][0] == "Market", f"{got}")

    got = passes(single("E4-target"), "target_hit pnl=100%", 4)
    check("E4 a target close never escalates: no MARKET, never at the bid",
          len(got) == 4 and all(t == "Limit" for t, _ in got) and all(p != 1.00 for _, p in got), f"{got}")

    got = passes(single("E5-short", is_short_position=1, strategy="ADOPTED", setup_type="orphan_adopted"),
                 "adopted_stop", 4)
    check("E5 an adopted short's stop buys back AT THE ASK 1.20 on pass 3, then MARKET",
          len(got) == 4 and got[2] == ("Limit", 1.20) and got[3][0] == "Market", f"{got}")

    got = passes(single("E6-noquote"), "hard_stop_20% pnl=-22.0%", 3, bid=None)
    check("E6 at the touch step with no fresh quote: MARKET", len(got) == 3 and got[2][0] == "Market", f"{got}")

    src = open(os.path.join(ROOT, "config.py")).read()
    no_env = not re.search(r"LIVE_STOP_(AT_BID|MARKET)_AFTER\s*=.*environ", src)
    check("E7 LIVE_STOP_AT_BID_AFTER = 2, LIVE_STOP_MARKET_AFTER = 3, constants (no env key)",
          getattr(_cfg, "LIVE_STOP_AT_BID_AFTER", None) == 2 and getattr(_cfg, "LIVE_STOP_MARKET_AFTER", None) == 3
          and no_env, f"{getattr(_cfg, 'LIVE_STOP_AT_BID_AFTER', None)} {getattr(_cfg, 'LIVE_STOP_MARKET_AFTER', None)}")

    # ── r144 (EXIT.19): a thesis-invalidated exit on a ONE-TICK book (QQQ 1.00 / 1.01) ──
    B, A, M = 1.00, 1.01, 1.005
    FLOOR_POSTS = [("Limit", 1.01), ("Limit", 1.01), ("Limit", 1.00)]

    def floor_run(tag, reason, **kw):
        got = passes(single(tag, **kw), reason, 4, mark=M, bid=B, ask=A)
        return got, list(acct["a"].calls)

    _, stop_calls = floor_run("E8-stop", "hard_stop_20% pnl=-21.0%")
    hunt = dict(strategy="LiquidityHunt", setup_type="hunt")
    for name, tag, reason, kw in (
            ("E8 runaway_thesis_dead", "E8-thesis", "runaway_thesis_dead: 1m close 699.10 back through 699.40 (band 0.039)", {}),
            ("E9 hunt_thesis_dead", "E9-hunt", "hunt_thesis_dead: 1m close 699.10 back through 699.40 (band 0.039)", hunt),
            ("E10 runaway_backstop", "E10-backstop", "runaway_backstop: 1m close 699.10 through the ORB boundary 699.20", {}),
            ("E11 handoff", "E11-handoff", "handoff: pool 701.50 (NY High) REJECTED on close (wick pierce 0.04%, "
                                           "bar 2026-11-13 10:39:00) — sweep owns it", {})):
        got, calls = floor_run(tag, reason, **kw)
        check(f"{name} on 1.00/1.01: LIMIT 1.01, LIMIT 1.01, LIMIT AT THE BID 1.00, MARKET; the hard stop's calls",
              len(got) == 4 and got[:3] == FLOOR_POSTS and got[3][0] == "Market" and calls == stop_calls,
              f"{got} calls={len(calls)} vs stop {len(stop_calls)}")

    def walks(got):
        return len(got) == 4 and all(t == "Limit" for t, _ in got) and all(p != B for _, p in got)

    got = passes(single("E12-trail"), "orb_trail_stop pnl=42.0%", 4, mark=M, bid=B, ask=A)
    check("E12 orb_trail_stop on 1.00/1.01 still walks: all LIMIT, never the bid, no MARKET", walks(got), f"{got}")
    got = passes(single("E13-park", strategy="PARK", setup_type="park"),
                 "park_lock: mark 1.01 <= 1.68 after +60%", 4, mark=M, bid=B, ask=A)
    got2 = passes(single("E13-ogap", strategy="OGAP", setup_type="ogap"),
                  "ogap_trail: mark 1.01 <= floor 1.68 (fill 1.40, peak 2.80)", 4, mark=M, bid=B, ask=A)
    check("E13 park_lock and ogap_trail on 1.00/1.01 still walk", walks(got) and walks(got2), f"{got} {got2}")

    # E14 — every reason the four live setups write, in the code's own formats
    FLOOR = ["runaway_thesis_dead: 1m close 699.10 back through 699.40 (band 0.039)",
             "hunt_thesis_dead: 1m close 699.10 back through 699.40 (band 0.039)",
             "runaway_backstop: 1m close 699.10 through the ORB boundary 699.20",
             "handoff: pool 701.50 (NY High) REJECTED on close (wick pierce 0.04%, bar 2026-11-13 10:39:00) — sweep owns it",
             "hard_stop_20% pnl=-21.0%",
             "orb_structure_stop: 1m close 699.10 below impulsive-candle low 699.20",
             "structure_stop: touch 699.10 through 699.20 pnl=-8.0%"]
    WALK = ["orb_trail_stop pnl=42.0%", "orb_fvg_trail_stop pnl=120.0%", "theta_bleed pnl=12.0%",
            "target_hit pnl=100.0%",
            "runaway_fizzle: higher_low_broken 699.10<699.20; acceptance_decay delta=-0.10 recent=0.40",
            "hunt_target_wicked: target 702.00 reached on a wick, close 701.80 — off",
            "decay: open profit +$40.00 (p 0.200) fell 31% from peak +$58.00 (p 0.290), armed at 09:41:15 pnl=14.0%",
            "park_lock: mark 1.01 <= 1.68 after +60%", "park_delta_floor: |delta| 0.080 <= 0.10",
            "park_close_15:30_ET",
            "ogap_lock: mark 1.60 <= floor 1.68 (fill 1.40, peak 2.30)",
            "ogap_trail: mark 2.00 <= floor 2.16 (fill 1.40, peak 3.60)",
            "ogap_sweep_1400: mark 0.60 < 0.75 x fill 1.40, peak 1.90", "ogap_close_1545",
            "started_close_resume"]
    pol = EE.ExitEngine._exit_policy
    rec0 = {"strategy": "RunawayContinuation", "option_symbol": "QQQ   261113C00700000"}
    bad = [(r[:24], pol(rec0, r)) for r in FLOOR if pol(rec0, r) != "floor"]
    bad += [(r[:24], pol(rec0, r)) for r in WALK if pol(rec0, r) != "walk"]
    eod = pol(rec0, EE._eod_label(rec0))
    check("E14 every Runaway/Hunt/PARK/OGAP reason: thesis, backstop, handoff and the stops floor; the rest walk; "
          "the debit hard close unchanged", not bad and eod == "debit_hard_close", f"bad={bad} eod={eod}")

    # E15 — each added key catches only its own reasons; no intent declares a pricing for them
    NEW = {"thesis_dead": FLOOR[0:2], "runaway_backstop": FLOOR[2:3], "handoff:": FLOOR[3:4]}
    keys = tuple(EE.ExitEngine._FLOOR_REASONS)
    own = {k: [r for r in FLOOR + WALK if k in r.lower()] for k in NEW}
    from strategy import management as MG
    conds = [str(r).split(" ")[0].split(":")[0] for r in FLOOR[:4]]
    declared = [(c, MG.EXIT_PRICING.get(c)) for c in conds if MG.EXIT_PRICING.get(c) is not None]
    check("E15 the r144 keys are in the table, each catches exactly its own reasons, none a walk reason; no declared "
          "pricing for them", all(k in keys for k in NEW) and all(own[k] == NEW[k] for k in NEW)
          and not any(k in w.lower() for k in keys for w in WALK) and not declared,
          f"keys={keys} own={own} declared={declared}")

    # E16 — paper: every reason books at the mark in one pass, digest as r143
    import hashlib
    paper = EE.ExitEngine(paper_trading=True)
    rows = []
    for i, r in enumerate(FLOOR + WALK):
        rec = single(f"E16-{i}")
        res = paper.place_exit_order(rec, r, 1.005)
        rows.append(f"{r}|{bool(res.confirmed)}|{res.fill_price!r}|{getattr(res, 'held', None)!r}")
    dig = hashlib.sha256("\n".join(rows).encode()).hexdigest()[:16]
    check("E16 paper unchanged: every reason confirmed in one pass, the digest r143 produced",
          all("|True|" in x for x in rows) and dig == PAPER_DIGEST, f"digest={dig} first={rows[0]}")

    print("=" * 60)
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {FAILED}")
        return 1
    print("GREEN — a live stop, and a thesis-invalidated exit, steps to the bid, then crosses")
    return 0


if __name__ == "__main__":
    sys.exit(main())
