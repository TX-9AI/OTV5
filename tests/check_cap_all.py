#!/usr/bin/env python3
"""
tests/check_cap_all.py  v5.1
v5.1  2026-11-22  OTV5 r151 (CAP.11) — C2, C3 and C6 drive a LIVE box's risk manager (paper_trading=False): from r151 (CAP.11) a paper box's cap is record only and never halts (tests/check_paper_cap_record.py), so 'every strategy is under the cap and refused at it' is the cash rule, unchanged. Same checks, same figures.
v5.0  2026-11-21  OTV5 r137 (CAP.10) — EVERY STRATEGY IS UNDER THE DAILY CATASTROPHIC CAP, PARK AND OGAP INCLUDED. The
      operator, 2026-11-21: "both trades should fall under the catastrophic cap & any profit locks need to be on mark".
      From r288 (PARK) and OGAP.1 (OGAP) to r136 both sat outside the cap both ways: config.CAP_EXCLUDED_STRATEGIES
      left their closes out of the cap's realized P&L, their admission rows were cap_exempt, and main's capped branch
      asked _attempt_park and _attempt_ogap. This gate drives the REAL code on scratch stores:

  C1  config: CAP_EXCLUDED_STRATEGIES == (); no admission rule (PARK, OGAP or any other) is cap_exempt
  C2  P&L counts: a -1,100 PARK close alone and a -1,100 OGAP close alone each put RiskManager(1,050).day_realized_pnl()
      at -1,100 (the displays' figure) and is_halted() True
  C3  the restart seed: a fresh RiskManager booting on the PARK row reads -1,100 and latches the halt
  C4  refusal: admission decide() at the cap refuses PARK at 11:01 and OGAP at 09:50 at catastrophic_cap; under the cap
      both are admitted in their windows (the cap is the only difference)
  C5  the capped branch, DRIVEN: attempt_new_entry() with the risk manager halted asks neither _attempt_park nor
      _attempt_ogap (intercepted) and returns; the same call un-halted asks both WITH the chain (normal path)
  C6  the implication, stated as a check: a -1,100 RunawayContinuation close at 10:15 halts the box, so the 11:01 PARK
      is refused at catastrophic_cap; a +300 PARK close after a -1,000 morning brings the day back to -700 (re-armed)
Born red on 4b6f22f (r136) at C1, C2, C3, C4, C5, C6.
NOT RUN (exit 2), never FAIL, when the imports cannot load (e.g. a bare python3, no pandas).
Run:  python3 tests/check_cap_all.py
"""
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_cap_all_")
os.environ["OT_TRADES_DB"] = os.path.join(_TD, "t.db")
os.environ["OT_DERIVED_DB"] = os.path.join(_TD, "d.db")
os.environ["OT_FEED_DB"] = os.path.join(_TD, "f.db")
os.environ["OT_LOG_FILE"] = os.path.join(_TD, "bot.log")
os.environ["OT_SIGNAL_JOURNAL_DIR"] = os.path.join(_TD, "sj")
os.environ["OT_COUNTERFACTUAL_DIR"] = os.path.join(_TD, "cf")
os.environ.pop("OT_DAILY_LOSS_LIMIT", None)
ET = ZoneInfo("America/New_York")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def _rows(*rows):
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(os.environ["OT_TRADES_DB"]) as c:
        c.execute("DELETE FROM trades")
        for tid, strat, pnl in rows:
            c.execute("INSERT INTO trades (trade_id, strategy, status, pnl_usd, entry_time, paper_trade) VALUES "
                      "(?,?,'closed',?,?,1)", (tid, strat, pnl, now_iso))


def main():
    print("check_cap_all")
    try:
        import pandas  # noqa: F401
        import config
        from database.trade_logger import get_trade_logger
        from risk.risk_manager import RiskManager
        from execution import position_manager as PM
        import main as MN
        import utils.time_utils as TU
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
        return 2
    TL = get_trade_logger()
    # the pager is a recorder: a cap hit here must never reach the real alert channel
    import types
    import notifications.alert_manager as AM
    pages = []
    AM.get_alert_manager = lambda *a, **k: types.SimpleNamespace(_send=lambda msg, *a2, **k2: pages.append(msg))

    # ── C1 config + admission table ──
    tbl = PM.rules()
    exempt = sorted(n for n, r in tbl.items() if getattr(r, "cap_exempt", False))
    check("C1 CAP_EXCLUDED_STRATEGIES == () and no admission rule is cap_exempt",
          tuple(config.CAP_EXCLUDED_STRATEGIES) == () and exempt == [] and "PARK" in tbl and "OGAP" in tbl,
          f"excluded={tuple(config.CAP_EXCLUDED_STRATEGIES)} exempt={exempt}")

    # ── C2 P&L counts ──
    got = {}
    for strat in ("PARK", "OGAP"):
        _rows((f"{strat.lower()}-1", strat, -1100.0))
        rm = RiskManager(risk_per_trade=1050.0, paper_trading=False)
        got[strat] = (rm.day_realized_pnl(), TL.realized_pnl_today(), rm.is_halted())
    check("C2 a -1,100 PARK close and a -1,100 OGAP close each count: cap P&L -1,100 = the displays', halted at 1,050",
          all(abs(v[0] + 1100) < 1e-6 and abs(v[1] + 1100) < 1e-6 and v[2] is True for v in got.values()), f"{got}")

    # ── C3 the restart seed ──
    _rows(("park-2", "PARK", -1100.0))
    rs = RiskManager(risk_per_trade=1050.0, paper_trading=False)
    rs._ensure_seeded()
    check("C3 the restart seed on a -1,100 PARK row reads -1,100 and latches the halt",
          rs._seeded is True and abs(rs._session_pnl_usd + 1100) < 1e-6 and rs._session_halted is True,
          f"seeded={rs._seeded} pnl={rs._session_pnl_usd} halted={rs._session_halted}")

    # ── C4 refusal at the cap ──
    def dec(strat, hm, cap_intact):
        return PM.decide(PM.Facts(strategy=strat, now_et=hm, orb_established=True, cap_intact=cap_intact))
    v = {"park_cap": dec("PARK", (11, 1), False), "ogap_cap": dec("OGAP", (9, 50), False),
         "park_ok": dec("PARK", (11, 1), True), "ogap_ok": dec("OGAP", (9, 50), True)}
    check("C4 at the cap PARK (11:01) and OGAP (09:50) are refused at catastrophic_cap; under it both are admitted",
          (not v["park_cap"].admitted and v["park_cap"].gate == "catastrophic_cap"
           and not v["ogap_cap"].admitted and v["ogap_cap"].gate == "catastrophic_cap"
           and v["park_ok"].admitted and v["ogap_ok"].admitted),
          {k: (x.admitted, x.gate) for k, x in v.items()})

    # ── C5 the capped branch, driven ──
    _rows()

    class _MS:
        adx, trend_direction, structure_sequence = 20.0, "NEUTRAL", ""

    class _Ch:
        calls, puts, spot = [], [], 600.0

    def drive(halted, hm):
        calls = []
        o_park, o_ogap, o_rm = MN._attempt_park, MN._attempt_ogap, MN.get_risk_manager
        MN._attempt_park = lambda ctx, ms, state, chain=None: calls.append(("park", chain is not None))
        MN._attempt_ogap = lambda ctx, ms, state, chain=None: calls.append(("ogap", chain is not None))
        real_rm = o_rm()

        class _RM:
            def __getattr__(self, n):
                return getattr(real_rm, n)

            def is_halted(self):
                return halted
        MN.get_risk_manager = lambda *a, **k: _RM()
        st = MN.BotState()
        st.paper_trading = True
        pin = datetime(2026, 11, 5, hm[0], hm[1], 5, tzinfo=ET)
        real = {"now_et": TU.now_et, "now_utc": TU.now_utc}
        fake = {"now_et": lambda: pin, "now_utc": lambda: pin.astimezone(timezone.utc)}
        sw = [(m, n) for m in list(sys.modules.values()) for n in real
              if m is not None and getattr(m, n, None) is real[n]]
        for m, n in sw:
            setattr(m, n, fake[n])
        err = ""
        try:
            MN.attempt_new_entry({"price": 600.0, "chain": _Ch(), "macro": {}, "symbol": "QQQ"}, _MS(), st)
        except Exception as e:                                  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        finally:
            MN._attempt_park, MN._attempt_ogap, MN.get_risk_manager = o_park, o_ogap, o_rm
            for m, n in sw:
                setattr(m, n, real[n])
        return calls, err
    c_cap, e_cap = drive(True, (11, 1))
    c_ok, e_ok = drive(False, (11, 1))
    check("C5 DRIVEN: halted, attempt_new_entry() asks neither PARK nor OGAP; un-halted it asks both with the chain",
          not e_cap and not e_ok and c_cap == [] and ("park", True) in c_ok and ("ogap", True) in c_ok,
          f"capped={c_cap} {e_cap} normal={c_ok} {e_ok}")

    # ── C6 the implication ──
    _rows(("rc-1", "RunawayContinuation", -1100.0))
    rm6 = RiskManager(risk_per_trade=1050.0, paper_trading=False)
    h6 = rm6.is_halted()
    v6 = dec("PARK", (11, 1), not h6)
    _rows(("rc-2", "RunawayContinuation", -1000.0), ("park-3", "PARK", 300.0))
    rm6b = RiskManager(risk_per_trade=1050.0, paper_trading=False)
    p6b, h6b = rm6b.day_realized_pnl(), rm6b.is_halted()
    check("C6 a -1,100 morning Runaway close halts the box and the 11:01 PARK is refused; a +300 PARK after a -1,000 "
          "morning reads -700, open",
          h6 is True and not v6.admitted and v6.gate == "catastrophic_cap" and abs(p6b + 700) < 1e-6 and h6b is False,
          f"halted={h6} park={v6} day={p6b} halted_b={h6b}")

    if FAILED:
        print(f"\nRED — {len(FAILED)} of 6 failed: {', '.join(FAILED)}")
        return 1
    print("\nGREEN — PARK and OGAP are under the daily catastrophic cap both ways (C1-C6)")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        if _TD.startswith(tempfile.gettempdir()) and os.path.basename(_TD).startswith("check_cap_all_"):
            shutil.rmtree(_TD, ignore_errors=True)
    sys.exit(rc)
