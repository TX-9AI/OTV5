#!/usr/bin/env python3
"""
tests/check_paper_cap_record.py  v5.1
v5.1  2026-11-23  OTV5 r153 (TRIM.2) — RE-POINTED (WA 38.4): the Hunt and OGAP are retired (DORMANT, never asked). drive()
      leaves the two retired names out of what it reports asked and of the plan gates it collects (on any tree), so K2's
      "keeps admitting entries" reads PARK at 11:01 (OGAP is no longer asked at 10:20; neither instant writes a
      catastrophic_cap row), K5's live box at the cap asks NOTHING (r150's walled OGAP is retired), and K6's digest is
      NEVER_DIGEST_EX_RETIRED, the same day measured on r152 c0cfcbf with the same filter. The trades the gate books
      directly (a LiquidityHunt row, the walled OGAP booking) still book through the kept code. K1, K3, K4 unchanged.
v5.0  2026-11-22  OTV5 r151 (CAP.11) — new. ON A PAPER BOX THE DAILY CATASTROPHIC CAP IS RECORD ONLY. The operator,
      2026-11-22: "Is there any way we can make the catastrophic cap only apply to cash? As in, there's no harm in letting
      paper run & we can just note if the breaker would have popped." and "Yes" to the design: a paper box writes one
      "breaker would have popped" record, keeps trading and tags every trade opened while the cap stands tripped
      after_cap = 1; a cash box halts as before. Drives the REAL risk manager, entry booking (EntryEngine._book_fill),
      trade logger and main.attempt_new_entry on scratch stores, the clock pinned to Tue 2026-11-24, the pager a
      recorder, every strategy's generate_signal a recorder (no signal), limit 1,050 (OT_RISK_USD 1050, no override).

  K1  A PAPER DAY THAT CROSSES THE CAP: a -1,100 Runaway close at 10:15 writes EXACTLY ONE circuit_breaker_events row,
      reason daily_cap_would_pop, notes "breaker would have popped at 10:15 ET, day net -$1,100.00 ...", and ONE
      bot.log INFO line saying so; nothing is paged; no daily_cap_hit row; every is_halted() answer of the day is False
      (record_loss's own call at the crossing included) and no "already recorded" line is said inside one process
  K2  IT KEEPS ADMITTING ENTRIES: attempt_new_entry at 10:20 (OGAP's window) and 11:01 (PARK's) asks OGAP and PARK,
      writes no catastrophic_cap plan row, and the risk manager reads not halted
  K3  THE TAG: the two trades opened before the cross carry after_cap NULL; the PARK trade booked at 11:01 carries 1
  K4  AS CASH: that PARK trade's -200 close leaves the cap's day at -1,100 (the display's -1,300) and writes no second
      row; a restart inside the episode (a fresh risk manager) writes no second row, says "already recorded" once and
      keeps tagging; the +200 close
      of a trade opened BEFORE the cross brings the as-cash day to -900 and RE-ARMS (one INFO line), and the next trade
      is untagged. Still exactly one would-pop row for the day
  K5  A LIVE BOX IS UNCHANGED: the same -1,100 cash close halts (is_halted True), pages ONCE, writes one daily_cap_hit
      row and no would-pop row; attempt_new_entry at 10:20 asks no cash setup (each refused at catastrophic_cap) and
      still asks the walled paper OGAP (r150); after_cap_tag() is False and neither a cash booking nor a walled OGAP
      booking (paper_wall.entry_engine) is tagged
  K6  A PAPER DAY THAT NEVER REACHES THE CAP IS BYTE-IDENTICAL TO r150 (digest NEVER_DIGEST over the rows, the cap
      events, the pages, the risk manager's log lines, the cap counterfactual lines, the asks and plan gates, measured on
      r150 dd910c2 and on this tree): the after_cap column, where it exists, is NULL on every row
Born red on r150 (dd910c2) at K1, K2, K3, K4 (a paper box halted and paged at the cap; no after_cap column); K5 and K6
are green on both trees and pin what must not move. Revert mutants red: see the land spec (CAP.11).
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
Run:  python3 tests/check_paper_cap_record.py
"""
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import sys
import tempfile
import types
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["OT_INSTRUMENT"] = "QQQ"
_TD = tempfile.mkdtemp(prefix="check_paper_cap_record_")
for _k, _f in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"),
               ("OT_LOG_FILE", "bot.log"), ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_COUNTERFACTUAL_DIR", "cf"),
               ("OT_ALERT_SPOOL", "alert_spool.jsonl"), ("OT_PLAN_STATES_FILE", "plan_states.json"),
               ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT")):
    os.environ[_k] = os.path.join(_TD, _f)
os.environ.pop("OT_DAILY_LOSS_LIMIT", None)
os.environ.pop("OT_PAPER_TRADING", None)       # the process is a paper box; each scenario sets its own mode
os.environ["OT_RISK_USD"] = "1050"
ET = ZoneInfo("America/New_York")
DAY = "2026-11-24"
LIMIT = 1050.0
NEVER_DIGEST = "82c1c6755be35e01"       # K6 to r152: measured on r150 (dd910c2) and on r151; see the land spec
NEVER_DIGEST_EX_RETIRED = "c113c53e30bfb234"   # K6 v5.1 (r153): the Hunt and OGAP left out of asks and gates, measured on r152
RETIRED_NAMES = ("LiquidityHunt", "OGAP")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def dg(obj) -> str:
    return hashlib.sha256(json.dumps(obj, default=str, sort_keys=True).encode()).hexdigest()[:16]


class _K:
    def __init__(self, strike, bid, ask, expiry, side):
        self.strike, self.bid, self.ask, self.expiry = strike, bid, ask, expiry
        self.mark = round((bid + ask) / 2, 2)
        self.delta = 0.5 if side == "C" else -0.5
        self.iv = 0.2
        self.symbol = f"QQQ  {expiry.replace('-', '')[2:]}{side}{int(strike * 1000):08d}"
        self.streamer_symbol = self.symbol


class _Chain:
    def __init__(self, expiry=DAY, atm=600, bid=2.0, ask=2.02, n=3):
        self.expiry = expiry
        self.calls = [_K(float(s), bid, ask, expiry, "C") for s in range(atm - n, atm + n + 1)]
        self.puts = [_K(float(s), bid, ask, expiry, "P") for s in range(atm - n, atm + n + 1)]
        self.spot_price = self.spot = float(atm)
        self.atm_iv = 0.2


class _MS:
    adx, trend_direction, structure_sequence = 20.0, "NEUTRAL", ""


class _Lines(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.recs = []

    def emit(self, r):
        self.recs.append((r.levelname, r.getMessage()))


def main():
    print("check_paper_cap_record")
    try:
        import pandas  # noqa: F401
        import database.trade_logger as TLM
        import risk.risk_manager as RM
        import execution.entry_engine as ENE
        import execution.position_manager as PMM
        from strategy.base_strategy import OptionsSignal
        import main as MN
        import utils.time_utils as TU
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2
    try:
        import execution.paper_wall as PW
    except Exception:                                           # noqa: BLE001
        PW = None
    import notifications.alert_manager as AM
    pages = []
    AM.get_alert_manager = lambda *a, **k: types.SimpleNamespace(_send=lambda msg, *a2, **k2: pages.append(msg))
    rlog = _Lines()
    logging.getLogger("risk.risk_manager").addHandler(rlog)
    logging.getLogger("risk.risk_manager").setLevel(logging.DEBUG)

    from analysis.orb_engine import get_orb_engine
    _eng = get_orb_engine()
    _eng.data.orb_high, _eng.data.orb_low = 601.0, 599.0           # the range is established (admission's orb_range)
    halts = []                                                  # every is_halted() answer, record_loss's included
    _ih = RM.RiskManager.is_halted

    def _ih_rec(self):
        v = _ih(self)
        halts.append(v)
        return v
    RM.RiskManager.is_halted = _ih_rec
    clock = {"t": datetime(2026, 11, 24, 9, 30, tzinfo=ET)}
    real = {"now_et": TU.now_et, "now_utc": TU.now_utc}
    fake = {"now_et": lambda: clock["t"], "now_utc": lambda: clock["t"].astimezone(timezone.utc)}
    swapped = [(m, n) for m in list(sys.modules.values()) for n in real
               if m is not None and getattr(m, n, None) is real[n]]
    for m, n in swapped:
        setattr(m, n, fake[n])

    def at(hh, mm):
        clock["t"] = datetime(2026, 11, 24, hh, mm, 5, tzinfo=ET)

    state = {}

    def fresh(tag, paper):
        d = os.path.join(_TD, tag)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "trades.db")
        TLM._trade_logger = TLM.TradeLogger(db_path=p, paper_trading=paper)
        RM._risk_manager = RM.RiskManager(risk_per_trade=LIMIT, paper_trading=paper)
        ENE._entry_engine = None
        if PW is not None:
            PW.reset()
        pages.clear()
        rlog.recs.clear()
        state.update(db=p, paper=paper, n=0)
        return p

    def sig(strat, side="call"):
        return OptionsSignal(strategy_name=strat, setup_type=strat.lower() + "_long", direction="long",
                             option_side=side, underlying_entry=600.0, underlying_stop=598.0, underlying_target=604.0,
                             strike=600.0, expiry=DAY, entry_premium=2.0, contracts=5)

    def book(strat, engine=None):
        eng = engine or ENE.EntryEngine(state["paper"])
        state["n"] += 1
        rec = eng._book_fill(sig(strat), 2.0, "PAPER-T%d" % state["n"] if state["paper"] else "LIVE-%d" % state["n"],
                             5, 5)
        return rec["trade_id"]

    def close(tid, pnl):
        TLM._trade_logger.log_exit(trade_id=tid, exit_price=2.0 + pnl / 500.0, pnl_usd=pnl, exit_reason="t")
        rm = RM._risk_manager
        (rm.record_loss if pnl < 0 else rm.record_win)(pnl)

    def rows():
        c = sqlite3.connect(state["db"])
        c.row_factory = sqlite3.Row
        out = [dict(r) for r in c.execute("SELECT * FROM trades ORDER BY entry_time, order_id")]
        ev = [dict(r) for r in c.execute("SELECT reason, session_losses, notes FROM circuit_breaker_events ORDER BY id")]
        c.close()
        return out, ev

    def drive(hh, mm, paper):
        at(hh, mm)
        asked, skips = [], []
        saved = {}
        for attr, nm in (("_runaway_strategy", "RunawayContinuation"), ("_liquidity_hunt", "LiquidityHunt"),
                         ("_park_strategy", "PARK"), ("_ogap_strategy", "OGAP"), ("_breakout", "Breakout")):
            obj = getattr(MN, attr)
            saved[attr] = obj.generate_signal

            def fn(_nm=nm, *a, **kw):
                asked.append(_nm)
                return None
            obj.generate_signal = fn
        s_skip = MN._plan_skip
        MN._plan_skip = lambda n, reason, gate="": skips.append((n, gate)) or s_skip(n, reason, gate)
        s_gpm = MN.get_position_manager
        pm = PMM.PositionManager(paper)
        MN.get_position_manager = lambda *a, **k: pm
        st = MN.BotState()
        st.paper_trading = paper
        err = ""
        try:
            MN.attempt_new_entry({"price": 600.0, "chain": _Chain(), "macro": {}, "symbol": "QQQ",
                                  "gap": {"prior_close": 599.0}}, _MS(), st)
        except Exception as e:                                  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        finally:
            for attr, f in saved.items():
                getattr(MN, attr).generate_signal = f
            MN._plan_skip = s_skip
            MN.get_position_manager = s_gpm
        return (sorted(set(n for n in asked if n not in RETIRED_NAMES)),                 # v5.1 (r153)
                sorted(set(g for _n, g in skips if _n not in RETIRED_NAMES)), err)

    def cf_lines():
        p = os.path.join(os.path.dirname(state["db"]), "cap_counterfactual.jsonl")
        out = []
        if os.path.exists(p):
            for ln in open(p):
                d = json.loads(ln)
                d.pop("ts_epoch", None)
                d.pop("trade_id", None)
                out.append(d)
        return out

    def would_pop(ev):
        return [e for e in ev if e["reason"] == "daily_cap_would_pop"]

    try:
        # ── the PAPER day that crosses ──────────────────────────────────────────────────────────────────────
        fresh("paper_cross", True)
        at(9, 40)
        a = book("RunawayContinuation")
        a2 = book("LiquidityHunt")
        at(10, 15)
        close(a, -1100.0)
        h1 = RM._risk_manager.is_halted()
        h2 = RM._risk_manager.is_halted()
        r1, ev1 = rows()
        again1 = [m for lv, m in rlog.recs if "already recorded" in m]
        halts1 = list(halts)
        info1 = [m for lv, m in rlog.recs if "WOULD HAVE POPPED" in m]
        lvl1 = [lv for lv, m in rlog.recs if "WOULD HAVE POPPED" in m]
        pages1 = list(pages)
        wp = would_pop(ev1)
        check("K1 a paper day crossing the cap: one would-pop row (10:15 ET, day net -$1,100.00), one INFO line, no "
              "page, no daily_cap_hit row, never halted",
              len(wp) == 1 and "breaker would have popped at 10:15 ET, day net -$1,100.00" in wp[0]["notes"]
              and not [e for e in ev1 if e["reason"] == "daily_cap_hit"] and len(info1) == 1 and lvl1 == ["INFO"]
              and "10:15 ET" in info1[0] and pages1 == [] and h1 is False and h2 is False
              and halts1 and not any(halts1) and again1 == [],
              f"events={ev1} info={info1} levels={lvl1} pages={pages1} halted={h1},{h2} every={halts1} again={again1}")

        ask_og, gates_og, e_og = drive(10, 20, True)
        ask_pk, gates_pk, e_pk = drive(11, 1, True)
        h3 = RM._risk_manager.is_halted()
        check("K2 it keeps admitting entries: at 11:01 PARK is asked; no catastrophic_cap plan row at 10:20 or 11:01",
              not e_og and not e_pk and "PARK" in ask_pk
              and "catastrophic_cap" not in gates_og and "catastrophic_cap" not in gates_pk and h3 is False,
              f"10:20 asked={ask_og} gates={gates_og} {e_og} | 11:01 asked={ask_pk} gates={gates_pk} {e_pk} halted={h3}")

        b = book("PARK")
        r2, _ev2 = rows()
        tag = {r["trade_id"]: r.get("after_cap", "NO COLUMN") for r in r2}
        check("K3 the tag: the trades opened before the cross read NULL, the 11:01 PARK reads after_cap = 1",
              tag.get(a) is None and tag.get(a2) is None and tag.get(b) == 1, f"{tag}")

        at(11, 30)
        close(b, -200.0)
        cap_day = round(RM._risk_manager.day_realized_pnl(), 2)
        disp_day = round(TLM._trade_logger.realized_pnl_today(), 2)
        _r3, ev3 = rows()
        at(12, 0)
        RM._risk_manager = RM.RiskManager(risk_per_trade=LIMIT, paper_trading=True)      # a restart in the episode
        h4 = RM._risk_manager.is_halted()
        c_tid = book("LiquidityHunt")
        _r4, ev4 = rows()
        at(13, 0)
        close(a2, 200.0)
        h5 = RM._risk_manager.is_halted()
        rearm = [m for lv, m in rlog.recs if "would have RE-ARMED" in m and lv == "INFO"]
        cash_after = round(RM._risk_manager.day_realized_pnl(), 2)
        at(13, 5)
        d_tid = book("RunawayContinuation")
        r5, ev5 = rows()
        tag5 = {r["trade_id"]: r.get("after_cap") for r in r5}
        again = [m for lv, m in rlog.recs if "already recorded" in m]
        paper_halts = list(halts)
        check("K4 as cash: the after_cap -200 close leaves the cap at -1,100 (display -1,300), no second row; a restart "
              "writes none and keeps tagging; a pre-cross +200 close re-arms at -900 and the next trade is untagged; "
              "one would-pop row for the day",
              cap_day == -1100.0 and disp_day == -1300.0 and len(would_pop(ev3)) == 1 and h4 is False
              and len(would_pop(ev4)) == 1 and tag5.get(c_tid) == 1 and h5 is False and len(rearm) == 1
              and cash_after == -900.0 and tag5.get(d_tid) is None and len(would_pop(ev5)) == 1 and pages == []
              and len(again) == 1 and not any(paper_halts),
              f"cap={cap_day} display={disp_day} rows={len(would_pop(ev3))},{len(would_pop(ev4))},{len(would_pop(ev5))} "
              f"restart_halted={h4} tag_c={tag5.get(c_tid)} rearm={rearm} as_cash={cash_after} tag_d={tag5.get(d_tid)} "
              f"pages={pages} restart_lines={again} any_halt={any(paper_halts)}")

        # ── the LIVE day: unchanged ─────────────────────────────────────────────────────────────────────────
        fresh("live_cross", False)
        at(9, 40)
        la = book("RunawayContinuation")
        at(10, 15)
        close(la, -1100.0)
        lh = RM._risk_manager.is_halted()
        _lr, lev = rows()
        lpages = list(pages)
        lask, lgates, le = drive(10, 20, False)
        ltag = getattr(RM._risk_manager, "after_cap_tag", lambda: False)()
        at(10, 25)
        lb = book("RunawayContinuation")
        wb = book("OGAP", engine=PW.entry_engine()) if PW is not None else None
        lr2, lev2 = rows()
        lt = {r["trade_id"]: r.get("after_cap") for r in lr2}
        check("K5 a live box is unchanged: the cash close halts, pages once, one daily_cap_hit row and no would-pop; at "
              "10:20 no setup is asked (catastrophic_cap; r153: OGAP retired); nothing on a live box is tagged",
              lh is True and len(lpages) == 1 and [e["reason"] for e in lev] == ["daily_cap_hit"]
              and not would_pop(lev2) and not le and lask == []
              and "catastrophic_cap" in lgates and ltag is False
              and lt.get(lb) is None and (wb is None or lt.get(wb) is None) and len(pages) == 1,
              f"halted={lh} pages={lpages} events={lev} asked={lask} gates={lgates} {le} tag_fn={ltag} tags={lt}")

        # ── the PAPER day that never reaches the cap: byte-identical to r150 ───────────────────────────────
        fresh("paper_never", True)
        at(9, 40)
        na = book("RunawayContinuation")
        na2 = book("LiquidityHunt")
        at(10, 15)
        close(na, -400.0)
        nh = [RM._risk_manager.is_halted()]
        n_og = drive(10, 20, True)
        n_pk = drive(11, 1, True)
        nb = book("PARK")
        at(11, 30)
        close(nb, 100.0)
        at(12, 0)
        close(na2, -300.0)
        nh.append(RM._risk_manager.is_halted())
        nr, nev = rows()
        ids = {}
        flat = []
        for r in nr:
            ids.setdefault(r["trade_id"], "T%d" % (len(ids) + 1))
            flat.append({k: (ids[v] if k == "trade_id" else v) for k, v in sorted(r.items()) if k != "after_cap"})
        payload = {"rows": flat, "events": nev, "pages": list(pages), "risk_log": rlog.recs,
                   "cf": cf_lines(), "asks": [n_og, n_pk], "halted": nh,
                   "cap_day": round(RM._risk_manager.day_realized_pnl(), 2)}
        got = dg(payload)
        nulls = [r.get("after_cap") for r in nr if "after_cap" in r]
        print(f"  K6 digest {got} (rows {len(flat)}, cap day {payload['cap_day']})")
        check("K6 a paper day that never reaches the cap is byte-identical to r150 (digest), after_cap NULL on every row",
              got == NEVER_DIGEST_EX_RETIRED and all(v is None for v in nulls),
              f"digest {got} != {NEVER_DIGEST_EX_RETIRED}; tags={nulls}")
    except Exception as exc:                                    # noqa: BLE001
        import traceback
        check("K0 the gate ran", False, f"{type(exc).__name__}: {exc} {traceback.format_exc()[-900:]}")
    finally:
        for m, n in swapped:
            setattr(m, n, real[n])
        RM.RiskManager.is_halted = _ih

    if FAILED:
        print(f"\nRED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("\nGREEN — a paper box records the would-be cap trip once, keeps trading and tags what it opens after it; a "
          "live box halts as before; a day short of the cap is the r150 day (K1-K6)")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        if _TD.startswith(tempfile.gettempdir()) and os.path.basename(_TD).startswith("check_paper_cap_record_"):
            shutil.rmtree(_TD, ignore_errors=True)
    sys.exit(rc)
