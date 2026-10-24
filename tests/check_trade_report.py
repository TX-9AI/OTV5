#!/usr/bin/env python3
"""
tests/check_trade_report.py  v1.6
v1.6  2026-09-26  OTV4TEST r160 — T13 ADDED: EXIT REASON — DOLLARS is ranked by NET $ (operator: "For Exit
      Reason - Dollars, can you rank them by net?"), even where N would order it the other way.
v1.5  2026-09-26  OTV4TEST r159 — T12 RE-POINTED to the dollar table: per exit reason NET $, AVG $ and mean
      MFE $ / MAE $ of open P&L (operator: "I'd rather see the dollar amounts of the actual exits ...
      MFE/MAE in dollar amounts"); SHARE is gone.
v1.4  2026-09-26  OTV4TEST r158 — T11 no longer expects a per-row `thin` (the label is gone; the kept-whole
      RULE is still pinned by the values). T12 ADDED: the exit-reason table carries median MFE% / MAE%
      per reason (EXIT BEHAVIOUR's fields) and the report prints no `thin` label anywhere. Operator:
      "Exit reason does not have any MFE/MAE — I don't need the report pointing out that a sample
      size of 1 is 'thin'".
v1.3  2026-09-26  OTV4TEST r157 — T11 ADDED: the outliers-removed EV section trims BOTH tails by
      Tukey's fences over the whole book (a +20R winner and a -10R loser are both cut, a +1R and a
      -1R are kept), reports each tail's count, and its trimmed EV is the mean of the rest; and a
      THIN bucket (under min_n) keeps every trade (operator: "In thin samples consider them all
      within the sample").
v1.2  2026-09-26  OTV4TEST r156 — T10 ADDED: every line the report prints, in every menu mode, is
      76 characters or fewer. Operator, on r155 read on his phone: "That report spends too many
      lines. It's too wide. You need to get it to fit single lines."
v1.1  2026-09-26  OTV4TEST r155 — T8 ADDED: every breakdown table carries EV R, the bucket's
      expectancy in R (mean of each trade's P&L over the risk its stop took). Operator: "Can you
      express the returns by setup type on EV multiple and add that to our report 35?"
      T9 ADDED: `pnl=NN%` in an exit reason is never read as a stop (the defect that scored most
      winners exactly +1.00R), a named `hard_stop_NN%` still is, and the tables sort by EV R.
MAINLINE'S TRADE REPORTS ON THIS BOX'S trades.db — driven as the menu runs them.

v1.0  2026-09-23  OTV4TEST r119. Born with tests/trade_report.py (absent at r118).

The operator, 2026-09-23: "let's get those reports borrowed, repurposed & added
to our devtools menu. You can retire our current one option 35 — I hate it."

Every case runs the REAL script as a subprocess on a scratch trades.db built by
the REAL TradeLogger schema, exactly as devtools.sh calls it.

  T1 the breakdown counts closed trades only: an OPEN row is not a trade
  T2 a VOID row is EXCLUDED and the exclusion is printed, by trade_id
  T3 read-only: the database's bytes are unchanged, and --no-json writes
     no reports/ directory
  T4 the trade list renders entry times in ET (13:54 UTC -> 09:54)
  T5 fees are priced (tests/fees.py beside it), never n/a on a known row
  T6 a missing database is a loud tool fault, rc 1 — not an empty book
  T7 the menu: item 35 is TRADE BREAKDOWN, 36 TRADES TAKEN, both run
     tests/trade_report.py, and the old SQL dump (entered_utc) is gone
"""
from __future__ import annotations

import glob as _glob
import hashlib
import os
import re
import sqlite3
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for _sp in _glob.glob(os.path.join(ROOT, "venv", "lib", "python*", "site-packages")):   # r106 bootstrap
    if _sp not in sys.path:
        sys.path.insert(1, _sp)

FAILED, RAN = [], []
WORK = tempfile.mkdtemp(prefix="chk_trade_report-")
REPORT = os.path.join(ROOT, "tests", "trade_report.py")


def check(name, ok, detail=""):
    RAN.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def build_db() -> str:
    from database.trade_logger import TradeLogger
    path = os.path.join(WORK, "trades.db")
    TradeLogger(db_path=path)                                    # the real schema
    rows = [
        # trade_id, strategy, setup_type, direction, entry_time, exit_time, contracts,
        # entry_premium, exit_premium, stop_premium, pnl_usd, status, exit_reason
        ("t-win", "Breakout", "breakout_short", "short", "2026-09-22T13:54:00+00:00",
         "2026-09-22T13:58:00+00:00", 10, 1.00, 1.30, 0.86, 300.0, "closed", "trail_stop_hit pnl=30%"),
        ("t-loss", "VOLT", "VOLT Long", "long", "2026-09-22T14:10:00+00:00",
         "2026-09-22T14:12:00+00:00", 5, 2.00, 1.72, 1.72, -140.0, "closed", "hard_stop_14% pnl=-14%"),
        ("t-void", "ORBStrategy", "ORB Long", "long", "2026-09-22T15:00:00+00:00",
         "2026-09-22T15:01:00+00:00", 1, 1.00, 1.00, 0.75, 0.0, "closed", "VOID: test fixture"),
        ("t-open", "Breakout", "breakout_long", "long", "2026-09-22T15:30:00+00:00",
         None, 3, 1.00, None, 0.86, None, "open", None),
    ]
    c = sqlite3.connect(path)
    c.executemany("INSERT INTO trades (trade_id, symbol, strategy, setup_type, direction, entry_time, "
                  "exit_time, contracts, entry_premium, exit_premium, stop_premium, pnl_usd, status, "
                  "exit_reason, paper_trade) VALUES (?, 'QQQ', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)", rows)
    c.commit(); c.close()
    return path


def run(*args):
    env = dict(os.environ, OT_TRADES_DB=os.path.join(WORK, "unused.db"))
    p = subprocess.run([sys.executable, REPORT, *args], capture_output=True, text=True,
                       cwd=WORK, env=env, timeout=120)
    return p.returncode, p.stdout + p.stderr


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    try:
        db = build_db()
    except Exception as exc:                                    # noqa: BLE001
        check("T0 the fixture database builds from TradeLogger", False, f"{type(exc).__name__}: {exc}")
        return finish()
    before = sha(db)
    rc, out = run("--db", db, "--no-json")
    m = re.search(r"TRADE BREAKDOWN — (\d+) closed trades", out)
    check("T1 the breakdown counts the two closed trades, not the open one",
          rc == 0 and m is not None and m.group(1) == "2", f"rc {rc}; header {m.group(0) if m else None}")
    check("T2 the VOID row is excluded and named", "1 VOID row(s) EXCLUDED: t-void" in out,
          next((l.strip() for l in out.splitlines() if "VOID" in l), "no VOID line"))
    check("T3 read-only: the database is byte-identical and no reports/ was written",
          sha(db) == before and not os.path.exists(os.path.join(ROOT, "reports"))
          and not os.path.exists(os.path.join(WORK, "reports")),
          f"db unchanged {sha(db) == before}")
    rc4, out4 = run("--db", db, "--no-json", "--rows-only")
    line = next((l for l in out4.splitlines() if " BRK " in l), "")
    check("T4 the trade list renders ET: 13:54 UTC reads 09:54", rc4 == 0 and "09-22 09:54" in line,
          line.strip() or out4[-200:])
    frow = next((l for l in out.splitlines() if l.strip().startswith("Breakout")), "")
    check("T5 the FEES column is priced, not n/a", frow != "" and "n/a" not in frow
          and re.search(r"-\d+\.\d\d", frow.split()[-1] if frow.split() else "") is not None, frow.strip())
    # T8 (r155) — EV R: the fixture's Breakout risks (1.00-0.86)x10x100 = $140 and makes $300
    # (+2.14R); the VOLT loss is its 14% hard stop on $1,000 = $140, losing $140 (-1.00R). And the
    # column is the MEAN per trade, not sum(P&L)/sum(risk): driven in-process on two trades.
    try:
        setup = out[out.index("BY SETUP TYPE"):]
        setup = setup[:setup.index("\n\n", 1)] if "\n\n" in setup[1:] else setup
        brk = next((l for l in setup.splitlines() if l.strip().startswith("breakout_short")), "")
        vol = next((l for l in setup.splitlines() if l.strip().startswith("VOLT Long")), "")
        sys.path.insert(0, os.path.dirname(REPORT))
        import importlib
        TR = importlib.import_module("trade_report")
        two = [dict(pnl_usd=300.0, entry_premium=1.00, stop_premium=0.86, contracts=10, exit_reason="trail_stop_hit"),
               dict(pnl_usd=-100.0, entry_premium=1.00, stop_premium=0.90, contracts=100, exit_reason="trail_stop_hit")]
        ev = TR._ev_r(two)
        want = round((300 / 140 + -100 / 1000) / 2, 3)
        check("T8 EV R: header, breakout_short +2.14, VOLT Long -1.00, and the MEAN per trade (not sum/sum)",
              " EV R " in setup and "+2.14" in brk and "-1.00" in vol and ev["ev_r"] == want
              and ev["ev_r_unpriced"] == 0, f"brk={brk.strip()!r} volt={vol.strip()!r} ev={ev} want {want}")
    except Exception as exc:                                    # noqa: BLE001
        check("T8 (did not run)", False, f"raised {type(exc).__name__}: {exc}")
    # T9 (r155) — the stop percentage comes only from a STOP token; tables sort by EV R.
    try:
        TR = sys.modules.get("trade_report") or __import__("trade_report")
        w = dict(exit_reason="orb_trail_stop pnl=30.0%", pnl_usd=300.0, entry_premium=1.00,
                 stop_premium=0.86, contracts=10)
        l = dict(exit_reason="hard_stop_14% pnl=-14%", pnl_usd=-140.0, entry_premium=2.00,
                 stop_premium=1.72, contracts=5)
        import io, contextlib
        buf = io.StringIO()
        d = {"big_dollars_low_ev": {**TR.stats_of([dict(w, pnl_usd=900.0, contracts=100)]), "net": 900.0},
             "small_dollars_high_ev": TR.stats_of([w])}
        d["big_dollars_low_ev"]["ev_r"] = 0.10
        with contextlib.redirect_stdout(buf):
            TR.show("T", d, 8)
        order = [x.split()[0] for x in buf.getvalue().splitlines() if x.strip() and x.split()[0] in d]
        check("T9 pnl=30% is not a stop (winner +2.14R on its floor), hard_stop_14% is (-1.00R), tables sort by EV R",
              TR.stop_pct_from_exit(w) is None and TR.stop_pct_from_exit(l) == 0.14
              and round(TR.modified_r(w), 2) == 2.14 and round(TR.modified_r(l), 2) == -1.00
              and order == ["small_dollars_high_ev", "big_dollars_low_ev"],
              f"w_pct={TR.stop_pct_from_exit(w)} l_pct={TR.stop_pct_from_exit(l)} "
              f"rW={TR.modified_r(w)} rL={TR.modified_r(l)} order={order}")
    except Exception as exc:                                    # noqa: BLE001
        check("T9 (did not run)", False, f"raised {type(exc).__name__}: {exc}")
    # T10 (r156) — the phone shows 76 columns; nothing the report prints may wrap.
    long_lines = []
    for mode in ([], ["--rows"], ["--rows-only"], ["--all-history"], ["--since", "2026-09-01"]):
        _rc, _o = run("--db", db, "--no-json", *mode)
        long_lines += [f"{' '.join(mode) or 'default'}:{len(l)}:{l.strip()[:40]}"
                       for l in _o.splitlines() if len(l) > 76]
    check("T10 every line in every mode fits 76 characters", not long_lines, "; ".join(long_lines[:4]))
    # T11 (r157) — outliers removed, both tails, fixed rule.
    try:
        TR = sys.modules.get("trade_report") or __import__("trade_report")
        import io, contextlib
        def mk(setup, r):   # risk $100 on the entry floor: P&L = r x 100
            return dict(setup_type=setup, exit_reason="trail_stop_hit", entry_premium=1.00,
                        stop_premium=0.90, contracts=10, pnl_usd=100.0 * r)
        book = ([mk("A", x) for x in (1.0, -1.0, 0.5, -0.5, 20.0)]
                + [mk("B", x) for x in (1.0, -1.0, 0.5, -10.0)])
        lo, hi = TR.r_fences(book)
        def render(min_n):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                TR.show_ev_trimmed(book, min_n)
            o = buf.getvalue()
            ra = next((l for l in o.splitlines() if l.strip().startswith("A ")), "")
            rb = next((l for l in o.splitlines() if l.strip().startswith("B ")), "")
            return o, ra.split(), rb.split()
        o, a, b = render(4)             # both buckets >= 4: trimmed
        o8, a8, b8 = render(8)          # both buckets < 8: thin, kept whole
        check("T11 outliers cut on BOTH tails (+20R, -10R) in full buckets; THIN buckets keep every trade",
              lo > -10 and hi < 20 and "1 high, 1 low out" in o
              and a[1:6] == ["5", "1", "0", "+4.00", "+0.00"] and b[1:6] == ["4", "0", "1", "-2.38", "+0.17"]
              and a8[1:6] == ["5", "0", "0", "+4.00", "+4.00"] and a8[-1] != "thin"
              and b8[1:6] == ["4", "0", "0", "-2.38", "-2.38"] and "0 high, 0 low out" in o8
              and all(len(l) <= 76 for l in (o + o8).splitlines()),
              f"fences {lo:+.2f}..{hi:+.2f}; A4={a} B4={b}; A8={a8}")
    except Exception as exc:                                    # noqa: BLE001
        check("T11 (did not run)", False, f"raised {type(exc).__name__}: {exc}")
    # T12 (r158) — MFE% / MAE% per exit reason; no `thin` label anywhere in the report.
    try:
        TR = sys.modules.get("trade_report") or __import__("trade_report")
        rows = [dict(exit_reason="trail_stop_hit pnl=30%", entry_premium=1.00, max_premium_seen=1.40,
                     min_premium_seen=0.95, contracts=10, pnl_usd=300.0, _date="2026-09-22"),
                dict(exit_reason="trail_stop_hit pnl=10%", entry_premium=2.00, max_premium_seen=2.40,
                     min_premium_seen=1.80, contracts=5, pnl_usd=100.0, _date="2026-09-23"),
                dict(exit_reason="hard_stop_20%", entry_premium=1.00, max_premium_seen=None,
                     min_premium_seen=0.78, contracts=10, pnl_usd=-220.0, _date="2026-09-23")]
        cz = TR.exit_concentration(rows, 8)
        tsh, hs = cz.get("trail_stop_hit", {}), cz.get("hard_stop_20%", {})
        # trail: MFE $ = mean(0.40x10x100, 0.40x5x100) = 300; MAE $ = mean(-50, -100) = -75
        thin_hits = [l.strip() for l in out.splitlines() if l.rstrip().endswith("thin") or "<- thin" in l]
        check("T12 exit reasons in DOLLARS: NET/AVG exit P&L, mean MFE $/MAE $; no SHARE; no 'thin' label",
              tsh.get("net") == 400.0 and tsh.get("avg") == 200.0 and tsh.get("mfe_usd") == 300.0
              and tsh.get("mae_usd") == -75.0 and hs.get("mfe_usd") is None and hs.get("mae_usd") == -220.0
              and "MFE $" in out and "MAE $" in out and "SHARE" not in out and not thin_hits,
              f"tsh={tsh} hs={hs} thin={thin_hits[:3]}")
    except Exception as exc:                                    # noqa: BLE001
        check("T12 (did not run)", False, f"raised {type(exc).__name__}: {exc}")
    # T13 (r160) — ranked by NET $, not by N.
    try:
        TR = sys.modules.get("trade_report") or __import__("trade_report")
        import io, contextlib
        conc = {"many_small_losers": dict(n=9, net=-900.0, avg=-100.0, mfe_usd=10.0, mae_usd=-120.0, single_session=False),
                "few_big_winners":  dict(n=2, net=5000.0, avg=2500.0, mfe_usd=3000.0, mae_usd=-50.0, single_session=False),
                "middle":           dict(n=5, net=100.0, avg=20.0, mfe_usd=90.0, mae_usd=-30.0, single_session=True),
                "no_pnl":           dict(n=3, net=None, avg=None, mfe_usd=None, mae_usd=None, single_session=False)}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            TR.show_exit_dollars(conc)
        order = [l.split()[0] for l in buf.getvalue().splitlines() if l.split() and l.split()[0] in conc]
        check("T13 EXIT REASON — DOLLARS ranks by NET $ (best first, no P&L last), not by N",
              order == ["few_big_winners", "middle", "many_small_losers", "no_pnl"]
              and "1-DAY" in buf.getvalue() and all(len(l) <= 76 for l in buf.getvalue().splitlines()),
              f"order={order}")
    except Exception as exc:                                    # noqa: BLE001
        check("T13 (did not run)", False, f"raised {type(exc).__name__}: {exc}")
    rc6, out6 = run("--db", os.path.join(WORK, "nope.db"), "--no-json")
    check("T6 a missing database is rc 1 and says PATH DOES NOT EXIST",
          rc6 == 1 and "PATH DOES NOT EXIST" in out6, f"rc {rc6}")

    src = open(os.path.join(ROOT, "devtools.sh"), encoding="utf-8").read()
    block = src[src.index("\nMENU=(") + 1:]                  # the array, not the comment naming it
    items = re.findall(r'^\s*"ITEM\|([^"]*)\|(\w+)"', block[:block.index("\n)")], re.M)
    n35 = items[34] if len(items) > 34 else ("", "")
    n36 = items[35] if len(items) > 35 else ("", "")
    wired = all(re.search(rf"^{fn}\(\)\s*{{[^\n]*_trade_report", src, re.M) for fn in ("trade_breakdown", "trades_taken"))
    check("T7 menu 35 = TRADE BREAKDOWN, 36 = TRADES TAKEN, both on trade_report.py; the SQL dump is gone",
          n35[1] == "trade_breakdown" and n36[1] == "trades_taken" and wired
          and "tests/trade_report.py" in src and "entered_utc" not in src,
          f"35 {n35[1]}; 36 {n36[1]}; wired {wired}; old dump present {'entered_utc' in src}")
    return finish()


def finish():
    import shutil
    shutil.rmtree(WORK, ignore_errors=True)
    print()
    if FAILED:
        print(f"RED — {len(FAILED)} of {len(RAN)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {len(RAN)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
