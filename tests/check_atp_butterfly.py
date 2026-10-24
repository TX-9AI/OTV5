#!/usr/bin/env python3
"""tests/check_atp_butterfly.py  v1.4
v1.4  2026-10-19  OTV4TEST r303 (PSTATE.1) — the ATP fly is DORMANT by default and a dormant plan writes nothing by ruling;
      setting the plan's module ENABLED alone no longer switches it on, so this run sets OT_ATP_BUTTERFLY=1 too.
THE ATP (AT-THE-PIN) BUTTERFLY — ITS PLAN, ITS STRATEGY, ITS EXITS AND ITS SESSION CAP.

v1.3  2026-09-30  OTV4TEST r179 (BFLY.9) — P7 RE-POINTED: the ATP fly's own
      concentration floor is 0.15 by ruling ("Actually .15 sounds better"), so
      the HOLD case is 0.14, not 0.15. check_atp_pin_floor owns the floor itself.
v1.2  2026-09-21  OTV4TEST r85 — S3/S4 RE-POINTED (r33/r43/r64),
      S4b added as the control: with BOTH traded, neither may be asked, so a
      fix that merely deleted the cap cannot pass.
v1.1  2026-09-18  OTV4TEST r43 — S6 reads `_attempt_butterfly`, not
      `attempt_new_entry`: r43 collapsed two butterfly paths into one, so the
      ordering rule (cap on both names, pin fly, then ATP fly) lives in the
      survivor. S6b added — the caller must NOT re-check the cap, because two
      mechanisms for one rule drift.
v1.0  2026-09-14  OTV4TEST r26 (BFLY.6, PLAN_SPEC §39). Operator: "traveling to the pin
      is a different thesis than building it on an already sideways tape" and
      "allow one butterfly or the other, whichever plan produces a viable trade
      1st can take it."

🔑 HOP 0 (WORKING_AGREEMENT §21): the plan cases DRIVE `ATPButterflyStrategy.
generate_signal` and read the plan row it wrote; the ladder is FRIDAY 2026-09-11's
REAL 12:28 ET quotes for QQQ 711-719 puts and calls (quote_series), spot 716.01,
pin 715. The exit cases drive `ManagementPlan.decide`; the session cap drives
main's real `_attempt_butterfly` against a temp trades.db with both strategies
replaced by spies, so "was it asked" is observed, not inferred from source.

  P1  at the pin, settled 15 bars, conc 0.26 -> TAKE the 713/715/717 PUT fly,
      debit 0.56, R 2.57 — Friday's answer (the 1-wide leaves spot outside the
      tent; the 713/715/717 call fly fails its own spread at 1.6x)
  P2  ...the signal is a valid butterfly named ATPButterfly with the 40% stop
  P3  spot 2.00 from the pin at EM 5.21 (0.38x — the TRAVEL fly's regime) -> HOLD
      waiting on at_pin
  P4  at the pin but only 6 closed bars inside the band -> HOLD waiting on settled,
      the row saying how many
  P5  no 1m bars -> HOLD, settled names that there were no bars (never a fire)
  P6  GEX TRENDING -> HOLD waiting on pinning
  P7  conc 0.14 with no VWAP -> HOLD on pin_concentration (pin_strength, this fly's 0.15 floor)
  P8  outside the butterfly slot -> dormant, no fire
  P9  a ladder where no wing contains spot -> DECLINE wing_search naming the tent
  M1  the management plan covers ATPButterfly
  M2  an ATP fly at 0.33 on a 0.56 entry (stop 0.336) -> CLOSE stop, 40%
  M3  an ATP fly at 1.30, above its recorded target -> HOLD, riding to the 15:45 flatten
  S1  nothing traded today -> _attempt_butterfly asks the pin fly, then the ATP fly
  S2  the pin fly fires -> the ATP fly is NOT asked
  S3  an ATPButterfly trade today -> NEITHER is asked (one butterfly of either kind)
  S4  a GEXPinButterfly trade today -> NEITHER is asked
  S5  _STRUCTURE_BY_NAME maps ATPButterfly to "butterfly" (else the cutoff reads it
      as a long debit)
  S6  the in-dispatch slot (attempt_new_entry, not drivable without a full tick)
      checks the cap on both names before asking either, pin fly first

Born red at r25 (1c8f293): every case, since neither module exists there.
Run:  python3 tests/check_atp_butterfly.py
"""
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")
os.environ["OT_ATP_BUTTERFLY"] = "1"   # r303: the subject is active (check_plan_states pins dormant)
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


class _Store:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")

    def commit(self):
        self.conn.commit()


class _C:
    def __init__(self, k, bid, ask, side):
        self.strike, self.bid, self.ask = float(k), float(bid), float(ask)
        self.mark = (bid + ask) / 2
        self.delta, self.gamma, self.theta = 0.3, 0.02, -0.05
        self.expiry, self.open_interest = "2026-09-11", 500
        self.symbol = f".QQQ260911{side}{k}"


# Friday 2026-09-11 12:28 ET, quote_series, last quote at or before the minute.
_PUTS = {711: (0.09, 0.10), 712: (0.13, 0.14), 713: (0.20, 0.21), 714: (0.32, 0.33),
         715: (0.54, 0.55), 716: (0.89, 0.90), 717: (1.44, 1.45), 718: (2.16, 2.21),
         719: (3.02, 3.16)}
_CALLS = {711: (4.94, 5.15), 712: (3.99, 4.22), 713: (3.18, 3.29), 714: (2.36, 2.40),
          715: (1.58, 1.59), 716: (0.94, 0.95), 717: (0.49, 0.50), 718: (0.22, 0.23),
          719: (0.10, 0.11)}


class _Chain:
    def __init__(self, puts=_PUTS, calls=_CALLS):
        self.puts = [_C(k, b, a, "P") for k, (b, a) in puts.items()]
        self.calls = [_C(k, b, a, "C") for k, (b, a) in calls.items()]


class _GEX:
    def __init__(self, env="PINNING", pin=715.0, conc=0.26):
        self.gex_environment, self.pin_strike, self.pin_concentration = env, pin, conc


def main():
    import pandas as pd
    from strategy import plan as P
    import strategy.gex_pin_butterfly as gpb
    import strategy.atp_butterfly_plan as ap
    from strategy.atp_butterfly import ATPButterflyStrategy
    from derived import anchors as A

    st = _Store()
    P.bind_store(st)
    os.environ["OT_RELAXED_ENTRY"] = "0"
    ap.ENABLED = True
    gpb.EARLIEST_ET, gpb.LATEST_ET = "12:00", "15:00"
    # EM pinned to Friday's 12:28 value, so the band is the one the study measured.
    gpb.expected_move = lambda u, iv, now=None: 5.21
    A._store = lambda: None                       # no VWAP: the waiver cannot mask a case

    def bars(closes):
        return pd.DataFrame({"open": closes, "high": closes, "low": closes, "close": closes},
                            index=pd.date_range("2026-09-11 12:00", periods=len(closes),
                                                freq="1min", tz="America/New_York"))

    settled = bars([715.2, 715.6, 716.1, 715.8, 715.4, 714.9, 715.3, 715.7, 716.2, 716.4,
                    715.9, 715.5, 715.1, 715.6, 716.0, 716.0, 716.01])     # 16 closed + forming
    common = dict(now_et="12:28", atm_iv=0.20)
    ts = [100.0]

    def run(**kw):
        S = ATPButterflyStrategy()
        S.planner.symbol = "TST"
        ts[0] += 1.0
        P.begin_tick(ts[0])
        args = dict(common, gex=_GEX(), chain=_Chain(), price_now=716.01, df_1m=settled)
        args.update(kw)
        sig = S.generate_signal(**args)
        row = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='ATPButterfly' "
                              "AND ts_epoch=?", (ts[0],)).fetchone()
        return sig, (row or ("", ""))

    sig, row = run()
    check("P1 at the pin and settled -> TAKE Friday's 713/715/717 PUT fly, debit 0.56, R 2.57",
          sig is not None and row[0] == "TAKE" and "buy 713/715/717 put fly" in row[1]
          and "debit 0.56" in row[1] and "R 2.57" in row[1], f"{row[0]}: {row[1][-120:]}")
    check("P2 ...a valid butterfly signal named ATPButterfly carrying the 40% stop",
          sig is not None and sig.is_valid and sig.is_butterfly and sig.strategy_name == "ATPButterfly"
          and abs(sig.stop_loss_pct - 0.40) < 1e-9 and sig.center_contract.strike == 715.0
          and sig.settled_bars == 16,
          sig and f"valid={sig.is_valid} name={sig.strategy_name} stop={sig.stop_loss_pct} settled={sig.settled_bars}")

    sig, row = run(price_now=717.0, df_1m=bars([717.0] * 17))
    check("P3 spot 2.00 off the pin (0.38x EM: the travel fly's regime) -> HOLD waiting on at_pin",
          sig is None and row[0] == "HOLD" and "at_pin=" in row[1], f"{row[0]}: {row[1][-110:]}")

    sig, row = run(df_1m=bars([719.0] * 10 + [715.5] * 6 + [716.01]))
    check("P4 at the pin but 6 closed bars inside the band -> HOLD waiting on settled, the count named",
          sig is None and row[0] == "HOLD" and "settled=6.00" in row[1], f"{row[0]}: {row[1][-110:]}")

    sig, row = run(df_1m=None)
    check("P5 no 1m bars -> HOLD, settled says there were no bars to read",
          sig is None and row[0] == "HOLD" and "no closed bars to read" in row[1], f"{row[0]}: {row[1][-110:]}")

    sig, row = run(gex=_GEX(env="TRENDING"))
    check("P6 GEX TRENDING -> HOLD waiting on pinning",
          sig is None and row[0] == "HOLD" and "pinning=" in row[1], f"{row[0]}: {row[1][-110:]}")

    sig, row = run(gex=_GEX(conc=0.14))
    check("P7 conc 0.14, no VWAP -> HOLD on pin_concentration (pin_strength, this fly's 0.15 floor)",
          sig is None and row[0] == "HOLD" and "pin_concentration=" in row[1] and "no VWAP" in row[1],
          f"{row[0]}: {row[1][-120:]}")

    S8 = ATPButterflyStrategy(); S8.planner.symbol = "TST"
    ts[0] += 1.0
    P.begin_tick(ts[0])
    sig8 = S8.generate_signal(gex=_GEX(), chain=_Chain(), price_now=716.01, df_1m=settled,
                              now_et="11:59", atm_iv=0.20)
    check("P8 outside the butterfly slot -> dormant, no fire", sig8 is None)

    narrow = {k: v for k, v in _PUTS.items() if 714 <= k <= 716}
    sig, row = run(chain=_Chain(puts=narrow, calls={k: v for k, v in _CALLS.items() if 714 <= k <= 716}))
    check("P9 only 1-wide wings (spot 1.01 off the pin) -> DECLINE wing_search naming the tent",
          sig is None and row[0] == "DECLINE" and "wing_search" in row[1] and "outside the tent" in row[1],
          f"{row[0]}: {row[1][-140:]}")

    # ── exits: the management plan ──────────────────────────────────────────
    from strategy.management import ManagementPlan, covers, EXIT_CONDITIONS
    MP = ManagementPlan()
    fly = {"trade_id": "atp1", "strategy": "ATPButterfly", "option_side": "put",
           "is_butterfly": True, "entry_premium": 0.56, "current_premium": 0.56,
           "stop_premium": round(0.56 * 0.60, 4), "target_premium": 1.20}
    check("M1 the management plan covers ATPButterfly with the pin butterfly's exits",
          covers(fly) and EXIT_CONDITIONS.get("ATPButterfly") == EXIT_CONDITIONS.get("GEXPinButterfly"))
    df = bars([715.5, 715.6])
    ts[0] += 1.0
    P.begin_tick(ts[0])
    it = MP.decide(dict(fly, current_premium=0.33), 0.33, df_1m=df, exit_engine=None)
    check("M2 an ATP fly at 0.33 under its 0.336 stop -> CLOSE stop_40%",
          it is not None and it.action == "CLOSE" and it.condition == "stop" and "40%" in it.reason,
          str(it and it.reason))
    ts[0] += 1.0
    P.begin_tick(ts[0])
    it = MP.decide(dict(fly, current_premium=1.30), 1.30, df_1m=df, exit_engine=None)
    mrow = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='ATPButterfly/manage' "
                           "AND ts_epoch=?", (ts[0],)).fetchone()
    check("M3 an ATP fly at 1.30, above its recorded target -> HOLD, riding to the 15:45 flatten",
          it is not None and it.action == "HOLD" and mrow and "15:45 -> flatten" in mrow[1]
          and "target" not in mrow[1], f"{it and it.action} {mrow}")

    # ── the session cap: main's real _attempt_butterfly, spies for the strategies ──
    import main as M
    import database.trade_logger as TL
    TL._trade_logger = TL.TradeLogger(os.path.join(tempfile.mkdtemp(), "book.db"))
    asked = []

    class _Spy:
        def __init__(self, name, fire=None):
            self.name, self.fire = name, fire

        def generate_signal(self, **kw):
            asked.append(self.name)
            return self.fire

    executed = []
    real_gex, real_atp, real_exec = M._gex_bfly_strategy, M._atp_bfly_strategy, M._execute_entry_signal
    M._execute_entry_signal = lambda sig, *a, **k: executed.append(getattr(sig, "strategy_name", "?"))
    ctx = {"chain": _Chain(), "gex": _GEX(), "price": 716.01, "atm_iv": 0.2, "df_1m": settled}

    class _Fired:
        strategy_name, pin_strike, strike = "GEXPinButterfly", 715.0, 715.0
    try:
        M._gex_bfly_strategy, M._atp_bfly_strategy = _Spy("GEX"), _Spy("ATP")
        asked.clear()
        M._attempt_butterfly(ctx, None, None, additive=True)
        check("S1 nothing traded today -> the pin fly is asked, then the ATP fly", asked == ["GEX", "ATP"], str(asked))

        M._gex_bfly_strategy = _Spy("GEX", fire=_Fired())
        asked.clear(); executed.clear()
        M._attempt_butterfly(ctx, None, None, additive=True)
        check("S2 the pin fly fires -> it executes and the ATP fly is NOT asked",
              asked == ["GEX"] and executed == ["GEXPinButterfly"], f"asked={asked} executed={executed}")
        gpb.GEXPinButterflyStrategy.PLAYED_PINS.clear()

        def _book(strategy):
            TL._trade_logger = TL.TradeLogger(os.path.join(tempfile.mkdtemp(), "book.db"))
            c = TL.get_trade_logger()._connect()
            try:
                c.execute("INSERT INTO trades (trade_id, symbol, strategy, status, entry_time) VALUES (?,?,?,?,?)",
                          (f"{strategy}-1", "QQQ", strategy, "open",
                           datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))
                c.commit()
            finally:
                c.close()

        M._gex_bfly_strategy = _Spy("GEX")
        # ⚠️ RE-POINTED AT r85, NOT DELETED (r33/r43/r64). S3 and S4 asserted
        # that ONE butterfly trade refused BOTH kinds for the session. THAT
        # BELIEF IS SUPERSEDED BY RULING. Operator, 2026-09-21, reading the
        # board after a single GEX pin had fired: *"I think we only hit one
        # butterfly the other one should still be allowed ... Two different
        # scenarios for those to fire under. And on certain days, we might
        # actually hit both."* The admission table ALWAYS agreed with him —
        # GEXFLY and ATPFLY each carry max_tries_per_session=1, one EACH — and
        # `_attempt_butterfly` read them with an `or`, blocking both, AHEAD of
        # admission so the table was never consulted (r71's shape).
        for label, traded, still in (("S3", "ATPButterfly", "GEX"),
                                     ("S4", "GEXPinButterfly", "ATP")):
            _book(traded)
            asked.clear()
            M._attempt_butterfly(ctx, None, None, additive=True)
            check(f"{label} a {traded} trade today -> IT is refused and the other "
                  f"kind is STILL asked", asked == [still],
                  f"asked={asked} — each butterfly carries its OWN session quota")
        # 🔑 S4b IS THE CONTROL AND IT IS THE HALF THAT KEEPS THE CAP HONEST.
        # Loosening a per-session limit is only verified by proving the limit
        # still EXISTS: with BOTH already traded, neither may be asked. A fix
        # that simply deleted the cap would pass S3 and S4 and silently
        # reintroduce r178's 2026-08-28 stack of five in ninety seconds.
        TL._trade_logger = TL.TradeLogger(os.path.join(tempfile.mkdtemp(), "book.db"))
        c = TL.get_trade_logger()._connect()
        try:
            for _st in ("ATPButterfly", "GEXPinButterfly"):
                c.execute("INSERT INTO trades (trade_id, symbol, strategy, status, entry_time)"
                          " VALUES (?,?,?,?,?)",
                          (f"{_st}-1", "QQQ", _st, "open",
                           datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))
            c.commit()
        finally:
            c.close()
        asked.clear()
        M._attempt_butterfly(ctx, None, None, additive=True)
        check("S4b CONTROL: BOTH traded today -> neither is asked (the cap still exists)",
              asked == [], f"asked={asked}")
    finally:
        M._gex_bfly_strategy, M._atp_bfly_strategy, M._execute_entry_signal = real_gex, real_atp, real_exec
    check("S5 _STRUCTURE_BY_NAME maps ATPButterfly to 'butterfly'",
          M._STRUCTURE_BY_NAME.get("ATPButterfly") == "butterfly")
    import ast
    src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    # ⚠️ r43 — S6 NOW READS `_attempt_butterfly`, NOT `attempt_new_entry`.
    # It asserted the ORDER of the in-dispatch copy: cap on both names, then the
    # pin fly, then the ATP fly. r43 collapsed the two butterfly paths into ONE
    # — the helper this file already drives directly in S1-S4 — so the ordering
    # rule is unchanged and simply lives in the surviving path. The assertion
    # follows the rule rather than the address.
    fn = next(x for x in ast.walk(ast.parse(src)) if isinstance(x, ast.FunctionDef)
              and x.name == "_attempt_butterfly")
    body = ast.unparse(fn)
    i_cap, i_gex, i_atp = (body.find("_one_per_session_used('ATPButterfly')"),
                           body.find("_safe_strategy('GEXPinButterfly'"), body.find("_safe_strategy('ATPButterfly'"))
    check("S6 the ONE butterfly path checks the cap on BOTH names before asking either, and asks the ATP fly after the pin fly",
          -1 < i_cap < i_gex < i_atp, f"cap@{i_cap} gex@{i_gex} atp@{i_atp}")
    # and the caller must NOT re-check it — two mechanisms for one rule drift
    anb = next(x for x in ast.walk(ast.parse(src)) if isinstance(x, ast.FunctionDef)
               and x.name == "attempt_new_entry")
    check("S6b the caller does not duplicate the session cap",
          "_one_per_session_used('GEXPinButterfly')" not in ast.unparse(anb),
          "the helper owns it")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: {', '.join(_fails)}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
