#!/usr/bin/env python3
"""
tests/check_exec_basis.py  v5.1
v5.1  2026-11-14  OTV5 r111 (AM.1) — new. THE EXECUTABLE-PRICE BASIS IS RECORDED BESIDE THE MARK. Driven through the REAL
      TradeLogger on a scratch store: log_entry, then the two writers the bot already calls with the tick's contract
      quote (set_entry_contract from main._capture_entry_contract, set_exit_contract from position_manager's close).

  B1  a long single: entry ask 1.05 -> entry_exec_premium 1.05; exit bid 1.45 -> exit_exec_premium 1.45;
      pnl_exec_usd = (1.45 - 1.05) x 2 x 100 = 80.00; pnl_usd (the mark's, written by log_exit) unchanged
  B2 would_fill_live: an ask above the mark (1.05 > 1.00) -> 0; an ask at the mark (1.00) -> 1
  B3 a short single (adopted): the BID in (0.95), the ASK out (0.60) -> pnl_exec_usd = (0.95 - 0.60) x 3 x 100 = 105.00;
      would_fill_live 0 (0.95 under the 1.00 mark)
  B4 a vertical (short_symbol + long_symbol) and a butterfly (center_symbol) stay NULL on all four columns
  B5 no ask at entry -> entry_exec_premium and would_fill_live NULL, and the exit's pnl_exec_usd NULL (never invented)
  B6 the four columns exist with NO default (NULL = not captured)
Born red on r108 (6b380b2): B1-B6 (no such columns).
Run:  python3 tests/check_exec_basis.py
"""
import os
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_exec_basis_")
os.environ["OT_TRADES_DB"] = os.path.join(_TD, "trades.db")
os.environ.setdefault("OT_LOG_FILE", os.path.join(_TD, "bot.log"))
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_TD, "derived.db"))
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def main():
    try:
        import database.trade_logger as TL
    except Exception as exc:                                    # noqa: BLE001
        print(f"NOT RUN — the bot's imports cannot load ({type(exc).__name__}: {exc}); run under the venv")
        return 2
    tl = TL.get_trade_logger()

    def row(tid):
        with tl._db() as conn:
            r = conn.execute("SELECT * FROM trades WHERE trade_id=?", (tid,)).fetchone()
        return dict(r) if r else {}

    def get(tid, *ks):
        r = row(tid)
        return tuple(r.get(k) for k in ks)

    def entry(tid, **kw):
        base = dict(trade_id=tid, symbol="QQQ", strategy="RunawayContinuation", setup_type="runaway",
                    direction="long", option_side="call", contracts=2, entry_premium=1.00, total_cost=200.0,
                    max_loss=200.0, stop_premium=0.80, strike=700.0, option_symbol="QQQ   261113C00700000",
                    expiry="2026-11-13")
        base.update(kw)
        r = TL.make_record(**base)
        tl.log_entry(r)
        return r

    K = ("entry_exec_premium", "exit_exec_premium", "pnl_exec_usd", "would_fill_live")

    entry("b1")
    tl.set_entry_contract("b1", {"entry_bid": 0.95, "entry_ask": 1.05, "entry_delta": 0.4})
    tl.log_exit(trade_id="b1", exit_price=1.50, pnl_usd=100.0, exit_reason="target_hit")
    tl.set_exit_contract("b1", {"exit_bid": 1.45, "exit_ask": 1.55, "exit_iv": 0.3})
    e, x, p, f = get("b1", *K)
    pnl_mark = get("b1", "pnl_usd")[0]
    check("B1 long: entry ask 1.05, exit bid 1.45, pnl_exec 80.00; pnl_usd (the mark's) unchanged at 100.00",
          e == 1.05 and x == 1.45 and p == 80.0 and pnl_mark == 100.0, f"{(e, x, p, f, pnl_mark)}")
    entry("b2")
    tl.set_entry_contract("b2", {"entry_bid": 0.96, "entry_ask": 1.00})
    check("B2 would_fill_live: ask 1.05 over the 1.00 mark -> 0; ask at the mark -> 1",
          f == 0 and get("b2", "would_fill_live")[0] == 1, f"b1={f} b2={get('b2', 'would_fill_live')}")

    entry("b3", strategy="ADOPTED", setup_type="orphan_adopted", is_short_position=1, contracts=3)
    tl.set_entry_contract("b3", {"entry_bid": 0.95, "entry_ask": 1.05})
    tl.log_exit(trade_id="b3", exit_price=0.62, pnl_usd=114.0, exit_reason="adopted_stop")
    tl.set_exit_contract("b3", {"exit_bid": 0.55, "exit_ask": 0.60})
    check("B3 short: the bid in 0.95, the ask out 0.60, pnl_exec 105.00, would_fill_live 0",
          get("b3", *K) == (0.95, 0.60, 105.0, 0), f"{get('b3', *K)}")

    entry("b4", strategy="IronCondorStrategy", setup_type="condor_leg", short_symbol="QQQ   261113P00699000",
          long_symbol="QQQ   261113P00698000", option_symbol="")
    tl.set_entry_contract("b4", {"entry_bid": 0.40, "entry_ask": 0.50})
    tl.set_exit_contract("b4", {"exit_bid": 0.10, "exit_ask": 0.15})
    entry("b4f", strategy="ADOPTED", setup_type="butterfly", lower_symbol="QQQ   261113C00699000",
          center_symbol="QQQ   261113C00700000", upper_symbol="QQQ   261113C00701000", option_symbol="")
    tl.set_entry_contract("b4f", {"entry_bid": 0.40, "entry_ask": 0.50})
    tl.set_exit_contract("b4f", {"exit_bid": 0.10, "exit_ask": 0.15})
    check("B4 a vertical and a butterfly stay NULL on all four",
          get("b4", *K) == (None, None, None, None) and get("b4f", *K) == (None, None, None, None),
          f"{get('b4', *K)} {get('b4f', *K)}")

    entry("b5")
    tl.set_entry_contract("b5", {"entry_bid": 0.95, "entry_ask": None, "entry_delta": 0.4})
    tl.set_exit_contract("b5", {"exit_bid": 1.20, "exit_ask": 1.30})
    check("B5 no entry ask: entry_exec and would_fill_live NULL; exit_exec 1.20 but pnl_exec NULL (never invented)",
          get("b5", *K) == (None, 1.20, None, None), f"{get('b5', *K)}")

    with tl._db() as conn:
        info = {r[1]: r[4] for r in conn.execute("PRAGMA table_info(trades)").fetchall()}
    check("B6 the four columns exist with no default", all(k in info and info[k] is None for k in K),
          f"{ {k: info.get(k, 'MISSING') for k in K} }")

    print("=" * 60)
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {FAILED}")
        return 1
    print("GREEN — the executable-price basis is recorded beside the mark")
    return 0


if __name__ == "__main__":
    sys.exit(main())
