#!/usr/bin/env python3
"""
tests/check_blind_stays_up.py  v5.0
v5.0  2026-11-04  OTV5 r74 (BLIND.1) — A BLIND BOT STAYS UP AND KEEPS MANAGING ITS OPEN POSITIONS.

2026-11-02 the AMZN and GOOGL optionsbot processes exited 5 times ("Too many errors — shutting down"; AMZN 10:12, 10:24,
10:49 ET) while their candle feeds were refused: run_analysis raised "No 5m data available" on every 15 s tick, the
loop's catch-all counted each one and sys.exit(1)'d at 30, and a raising tick never reached manage_open_position. The
operator, 2026-11-03: "Yes to the proposal" (build the two outage-path fixes).

  B1  run_analysis raises FeedBlind - a ValueError, with the SAME text - for no price and for no 5m bars
  B2  main_loop (AST): the main analysis call sits in its own try whose FeedBlind handler calls _blind_tick, ends the
      tick with `continue` and never touches errors_this_hour; it is caught before the loop's catch-all; the 15:40
      vertical manage pass handles FeedBlind with _blind_tick too
  B3  a blind feed with an open position, 40 blind ticks (10 minutes) through the REAL PositionManager (paper, stub
      stores, REST marks patched): the process is not exited, the position is priced from the REST mark and closed by
      the exit engine on its premium stop on the first tick, ONE page for the episode, errors_this_hour untouched
  B4  blind with REST giving nothing: the last known mark is used (no exit, no crash); NOT blind: paper never asks REST
      (no other tick changes)
  B5  sight restored: _blind_clear ends the episode (REST marks off, a new episode pages again)
  B6  ONE page per episode, and it is BOT IS BLIND: with the real latch and the real send_blind_alert, the latch's
      page (tick 3, not before) names "bot STAYS UP, managing 1 open position(s) from TastyTrade REST marks"; 40 ticks
      send nothing else (operator 2026-11-04 "Yes": fold the stays-up note into BOT IS BLIND)
  B7  the latch never trips within BLIND_PAGE_FALLBACK_S: _blind_tick sends the same BOT IS BLIND page (with the note)
      at 90 s, not before; the latch's later ALERT is not paged twice
  B8  the latch paged before the FeedBlind episode began (stale data first): the episode sends no second page
  B9  a page with no episode (managing=None) is the unchanged BOT IS BLIND text, no REST note

Run:  python3 tests/check_blind_stays_up.py
"""
import ast
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def _rec(tid, **kw):
    r = {"trade_id": tid, "strategy": "Breakout", "symbol": "AMZN", "direction": "long", "option_side": "call",
         "entry_premium": 2.00, "stop_premium": 1.00, "target_premium": 0.0, "trail_stop": 0.0,
         "underlying_entry": 0.0, "underlying_stop": 0.0, "contracts": 5, "is_butterfly": 0,
         "option_symbol": "AMZN  261102C00245000", "expiry": "2026-11-06", "current_premium": 1.80,
         "entry_time": "2026-11-02T14:40:00+00:00", "status": "open"}
    r.update(kw)
    return r


def _main_loop_node(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == "main_loop":
            return n
    return None


def _handler_names(h):
    t = h.type
    if t is None:
        return set()
    if isinstance(t, ast.Tuple):
        return {getattr(e, "id", getattr(e, "attr", "")) for e in t.elts}
    return {getattr(t, "id", getattr(t, "attr", ""))}


def b2(src):
    tree = ast.parse(src)
    ml = _main_loop_node(tree)
    found_main = found_hc = False
    detail = []
    for t in ast.walk(ml):
        if not isinstance(t, ast.Try):
            continue
        calls = [c for s in t.body for c in ast.walk(s) if isinstance(c, ast.Call)
                 and getattr(c.func, "id", "") == "run_analysis"]
        if not calls:
            continue
        fb = [h for h in t.handlers if "FeedBlind" in _handler_names(h)]
        if not fb:
            continue
        h = fb[0]
        body_src = ast.unparse(h)
        tick = "_blind_tick(" in body_src
        no_err = "errors_this_hour" not in body_src
        is_main = any(any(k.arg == "chain" for k in c.keywords) for c in calls)
        ends_continue = isinstance(h.body[-1], ast.Continue)
        first = t.handlers.index(h) == 0 or all("Exception" not in _handler_names(x) for x in t.handlers[:t.handlers.index(h)])
        if is_main:
            found_main = tick and no_err and ends_continue and first
            detail.append(f"main: tick={tick} no_err={no_err} continue={ends_continue} first={first}")
        else:
            found_hc = found_hc or (tick and no_err and first)
            detail.append(f"15:40: tick={tick} no_err={no_err} first={first}")
    # the FeedBlind try must be nested inside the loop's catch-all try (so the catch-all still covers everything else)
    outer = [t for t in ast.walk(ml) if isinstance(t, ast.Try)
             and any("errors_this_hour" in ast.unparse(h) for h in t.handlers)]
    nested = any(any(isinstance(x, ast.Try) and any("FeedBlind" in _handler_names(h) for h in x.handlers)
                     for x in ast.walk(o)) for o in outer)
    check("B2 main_loop: FeedBlind caught around the main analysis -> _blind_tick, `continue`, no errors_this_hour, "
          "inside the catch-all; the 15:40 pass too", found_main and found_hc and nested,
          "; ".join(detail) + f"; nested={nested}")


def main():
    print("check_blind_stays_up")
    try:
        import pandas  # noqa: F401
        import main as M
        import execution.position_manager as PM
        import execution.exit_engine as XE
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN: imports failed ({type(exc).__name__}: {exc})")
        return 2

    # ── B1 ──────────────────────────────────────────────────────────────────
    import pandas as pd
    res = {}
    for label, price, df5 in (("price", None, pd.DataFrame({"close": [1.0]})), ("5m", 245.0, pd.DataFrame())):
        M.get_cache = lambda price=price, df5=df5: types.SimpleNamespace(get_all=lambda: {"5m": df5},
                                                                         get_price=lambda: price)
        try:
            M.run_analysis(types.SimpleNamespace())
            res[label] = None
        except Exception as exc:                                # noqa: BLE001
            res[label] = exc
    fb = getattr(M, "FeedBlind", None)
    ok = (fb is not None and issubclass(fb, ValueError)
          and isinstance(res["price"], fb) and str(res["price"]) == "Could not fetch current price"
          and isinstance(res["5m"], fb) and str(res["5m"]) == "No 5m data available")
    check("B1 run_analysis raises FeedBlind (a ValueError, same text) for no price and no 5m bars", ok,
          f"price={type(res['price']).__name__}:{res['price']} 5m={type(res['5m']).__name__}:{res['5m']}")

    # ── B2 ──────────────────────────────────────────────────────────────────
    b2(open(os.path.join(ROOT, "main.py"), encoding="utf-8").read())

    # ── B3/B4/B5: the real PositionManager on paper, stub stores ────────────
    XE.is_hard_close_time = lambda *a, **k: False

    class _TL:
        def __init__(self, recs): self.exits, self.recs = [], recs
        def update_current_premium(self, *a, **k): pass
        def update_trail_stop(self, *a, **k): pass
        def set_exit_contract(self, *a, **k): return True
        def get_open_trades(self): return list(self.recs)
        def get_open_trades_live(self): return list(self.recs)
        def log_exit(self, **k):
            self.exits.append(k)
            self.recs[:] = [x for x in self.recs if x.get("trade_id") != k.get("trade_id")]

    import notifications.alert_manager as AM

    class _Alert(AM.AlertManager):                              # the REAL send_blind_alert; only _send is stubbed
        def __init__(self): self.sent = []
        def _send(self, msg, *a, **k): self.sent.append(msg); return True
    alert = _Alert()
    PM.get_alert_manager = lambda: alert
    M.get_alert_manager = lambda: alert
    PM.get_client = lambda: object()
    M.time.sleep = lambda s: None

    T0 = 1_793_000_000.0                                        # a fixed clock: one tick = 15 s

    def run(marks, ticks, blind=True):
        rec = _rec("b3")
        tl = _TL([rec])
        pm = PM.PositionManager(paper_trading=True)
        pm._trade_logger = tl
        pm._open_records = [rec]
        asked = []
        seq = list(marks)

        def _mark(client, sym):
            asked.append(sym)
            return seq.pop(0) if seq else None
        pm._get_option_mark = _mark
        state = types.SimpleNamespace(blind_since=None, blind_paged=False, blind_last_line=0.0, errors_this_hour=0)
        exited = None
        n0 = len(alert.sent)
        try:
            for i in range(ticks):
                if blind:
                    M._blind_tick(state, pm, M.FeedBlind("No 5m data available"), now=T0 + 15.0 * i)
                else:
                    pm.manage_open_position(chain=None)
        except SystemExit as exc:                               # noqa: BLE001
            exited = exc
        return types.SimpleNamespace(tl=tl, pm=pm, state=state, asked=asked, exited=exited,   # the BLIND pages
                                     pages=[m for m in alert.sent[n0:] if "BLIND" in m], rec=rec)

    r = run([0.80], 40)
    ex = r.tl.exits
    check("B3 40 blind ticks: no exit of the process; the REST mark 0.80 closes the position on its 1.00 stop on the "
          "first tick; ONE page; errors_this_hour untouched",
          r.exited is None and len(ex) == 1 and abs(float(ex[0].get("exit_price", 0)) - 0.80) < 1e-9
          and len(r.pages) == 1 and "BOT IS BLIND" in r.pages[0] and "STAYS UP" in r.pages[0]
          and "REST marks" in r.pages[0] and r.state.errors_this_hour == 0
          and r.pm.blind_rest_marks is True and r.asked[:1] == ["AMZN  261102C00245000"],
          f"exited={r.exited} exits={[(e.get('exit_price'), e.get('exit_reason')) for e in ex]} pages={len(r.pages)} "
          f"errors={r.state.errors_this_hour} asked={r.asked[:2]}")

    r4 = run([], 8)                                             # REST gives nothing
    r5 = run([0.80], 3, blind=False)                            # not blind: paper never asks REST
    check("B4 blind and REST empty: the last known mark (1.80) holds, no exit, no crash; NOT blind: REST never asked",
          r4.exited is None and r4.tl.exits == [] and len(r4.asked) >= 1 and r5.asked == [] and r5.tl.exits == [],
          f"blind-empty exits={r4.tl.exits} asked={len(r4.asked)}; not-blind asked={r5.asked} exits={r5.tl.exits}")

    M._blind_clear(r4.state, r4.pm)
    n0 = len(alert.sent)
    for i in range(8):
        M._blind_tick(r4.state, r4.pm, M.FeedBlind("No 5m data available"), now=T0 + 10_000 + 15.0 * i)
    check("B5 _blind_clear ends the episode (REST marks off, blind_since None); the next blind tick pages again",
          r4.pm.blind_rest_marks is True and r4.state.blind_since is not None and len(alert.sent) - n0 == 1,
          f"rest={r4.pm.blind_rest_marks} since={r4.state.blind_since} pages={len(alert.sent) - n0}")
    M._blind_clear(r4.state, r4.pm)
    check("B5b after _blind_clear: blind_rest_marks False", r4.pm.blind_rest_marks is False)

    # ── B6-B9: the one page per episode is BOT IS BLIND ─────────────────────
    from utils.blindness_latch import BlindnessLatch
    blind_rec = {"cause": "NO_BARS", "symbol": "AMZN", "timeframe": "5m", "fields": {"rows": 0}}
    feed = {"rec": blind_rec}
    M.last_blindness = lambda: feed["rec"]
    M.clear_blindness = lambda: None

    def episode(ticks, latch_ticks, pre_alerted=False):
        rec = _rec("b6", current_premium=1.80)
        tl = _TL([rec])
        pm = PM.PositionManager(paper_trading=True)
        pm._trade_logger = tl
        pm._open_records = [rec]
        pm._get_option_mark = lambda client, sym: 1.80                  # above the 1.00 stop: stays open
        M.get_trade_logger = lambda: tl
        latch = BlindnessLatch(ticks_before_alert=latch_ticks, seconds_before_alert=0)
        state = types.SimpleNamespace(blind_since=None, blind_paged=False, blind_last_line=0.0, blind_managing=0,
                                      errors_this_hour=0, paper_trading=True, blind_latch=latch)
        n0 = len(alert.sent)
        if pre_alerted:                                                  # stale data paged before any FeedBlind
            for _ in range(latch_ticks):
                M._check_blindness(state)
        per_tick = []
        for i in range(ticks):
            M._check_blindness(state)
            M._blind_tick(state, pm, M.FeedBlind("No 5m data available"), now=T0 + 20_000 + 15.0 * i)
            per_tick.append(len(alert.sent) - n0)
        return types.SimpleNamespace(pages=alert.sent[n0:], per_tick=per_tick, tl=tl)   # no exit: every page is BLIND

    e6 = episode(40, 3)
    note = "bot STAYS UP, managing 1 open position(s) from TastyTrade REST marks"
    check("B6 latch + episode: ONE page, BOT IS BLIND on tick 3 (none before), naming the REST-marks management",
          len(e6.pages) == 1 and e6.per_tick[1] == 0 and e6.per_tick[2] == 1 and "BOT IS BLIND" in e6.pages[0]
          and note in e6.pages[0] and "FEED BLIND" not in e6.pages[0] and e6.tl.exits == [],
          f"pages={len(e6.pages)} per_tick={e6.per_tick[:4]} text={e6.pages[:1]}")

    e7 = episode(12, 9)                                    # latch would page at tick 9 (120 s); fallback at 90 s
    fb_tick = next((i for i, n in enumerate(e7.per_tick) if n), None)
    check("B7 latch slower than 90 s: _blind_tick pages BOT IS BLIND (with the note) at tick 7 (90 s), the latch's "
          "later ALERT is not paged twice",
          len(e7.pages) == 1 and fb_tick == 6 and "BOT IS BLIND" in e7.pages[0] and note in e7.pages[0],
          f"pages={len(e7.pages)} first-page tick index={fb_tick}")

    e8 = episode(12, 3, pre_alerted=True)
    check("B8 the latch paged before the episode began: the episode sends no second page",
          len(e8.pages) == 1 and e8.per_tick[0] == 1 and "REST marks" not in e8.pages[0],
          f"pages={len(e8.pages)} per_tick={e8.per_tick[:3]}")

    n0 = len(alert.sent)
    alert.send_blind_alert("AMZN", blind_rec, open_positions=[], paper=True, blind_for_s=50)
    t9 = alert.sent[n0:]
    check("B9 managing=None (no episode): the BOT IS BLIND text is unchanged, no REST note",
          len(t9) == 1 and "BOT IS BLIND" in t9[0] and "REST marks" not in t9[0] and "no open positions" in t9[0],
          f"text={t9}")

    print(f"\n{'ALL PASS' if not FAILED else 'FAILED: ' + ', '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
