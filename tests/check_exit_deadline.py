#!/usr/bin/env python3
"""tests/check_exit_deadline.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
F1 — A LIVE CLOSE BLOCKS THE TICK LOOP FOR ~14 s, NOT ~36 s, AND NEVER GOES SILENT TO THE WATCHDOG.

v1.0  2026-10-18  OTV4TEST r295 (LIVE.2) — MAINLINE's tests/check_exit_deadline.py v1.0 (otv4 r474 674e0cc) adapted:
      OT_INSTRUMENT=QQQ (this config refuses an unlisted instrument), every OT_* store and OT_HEARTBEAT_FILE in a scratch
      dir (the live poll loop now touches the heartbeat), and D5 added: the never-filling close touches the heartbeat on
      every broker poll (>= 4 in 8 s at a 2 s poll) - tools/emergency_watchdog.py (STALE_S 180) would otherwise SIGKILL
      a laddering bot at ~15:53. RED on fa2c08d at D1 D2 D3 D5. Mainline's text follows.
v1.0  2026-10-05  r474. Operator: "get it down to eight seconds." A live close
      waited up to LIVE_FILL_DEADLINE_SECONDS (30) for a fill, then a 6 s cancel
      grace, with nothing else in the bot evaluated meanwhile.

Drives the REAL ExitEngine._confirm_and_book_live_exit in LIVE mode, against a
REAL TradeLogger on a temp DB, with a broker whose order never fills and a FAKE
CLOCK inside exit_engine (time.monotonic / time.sleep), so the timing is
measured, not assumed, and the check takes no real time.

  D1  config.LIVE_FILL_DEADLINE_SECONDS defaults to 8 (fresh interpreter, no
      override)
  D2  the cancel is sent at 8 s on the fake clock (not 30)
  D3  the call returns, unconfirmed, by ~14 s (8 + the 6 s cancel grace)
  D4  UNCHANGED: an order that fills at 3 s books at 3 s, with no cancel

Run:  python3 tests/check_exit_deadline.py   (needs the venv's tastytrade)
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
_SCR = tempfile.mkdtemp(prefix="chk_exit_deadline_")
for _k, _v in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"), ("OT_LOG_FILE", "bot.log"),
               ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_RESTING_DB", "r.db"), ("OT_SIGNAL_JOURNAL_DIR", "sj"),
               ("OT_RESTING_STOP_STATE", "rs.json"), ("OT_HEARTBEAT_FILE", "BOT_HEARTBEAT")):
    os.environ[_k] = os.path.join(_SCR, _v)
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


class _Clock:
    def __init__(self):
        self.t = 1000.0

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.t += float(s)

    def time(self):
        return self.t


class _Order:
    def __init__(self, oid, status, fill=None):
        self.id, self.status, self._fill, self.reject_reason = oid, status, fill, None


def main():
    print("check_exit_deadline")
    env = {k: v for k, v in os.environ.items() if k != "OT_LIVE_FILL_DEADLINE_SECONDS"}
    r = subprocess.run([sys.executable, "-c",
                        f"import sys; sys.path.insert(0, {ROOT!r}); import config; "
                        f"print(config.LIVE_FILL_DEADLINE_SECONDS)"],
                       capture_output=True, text=True, env=env, timeout=120)
    got = (r.stdout.strip().splitlines() or ["?"])[-1]
    check("D1 LIVE_FILL_DEADLINE_SECONDS defaults to 8", got == "8.0", f"got {got!r} rc={r.returncode}")

    try:
        from tastytrade.order import OrderStatus
    except ImportError as exc:
        print(f"NOT RUN — this interpreter cannot import tastytrade ({exc}); run under the venv")
        return 2
    import config as _cfg
    _cfg.LOG_FILE = os.path.join(tempfile.mkdtemp(), "bot.log")
    import database.trade_logger as TL
    import execution.exit_engine as EE

    tmp = tempfile.mkdtemp()
    tl = TL.TradeLogger(os.path.join(tmp, "t.db"), paper_trading=False)
    TL._trade_logger = tl
    clock = _Clock()
    EE.time = clock

    class _Broker:
        def __init__(self, fill_at=None):
            self.fill_at, self.cancel_at, self.submitted = fill_at, None, 0

        def get_order(self, session, oid):
            if self.fill_at is not None and clock.t - 1000.0 >= self.fill_at:
                return _Order(oid, OrderStatus.FILLED, (5.0, 1.10))
            return _Order(oid, OrderStatus.LIVE)

        def delete_order(self, session, oid):
            if self.cancel_at is None:
                self.cancel_at = clock.t - 1000.0
            return None

    def run(fill_at=None, tid="F1"):
        clock.t = 1000.0
        broker = _Broker(fill_at)
        EE.get_session = lambda: "S"
        EE.get_account = lambda: broker
        e = EE.ExitEngine(paper_trading=False)
        e._net_fill_price = lambda record, placed: placed._fill
        e._alert_live_exit_once = lambda *a, **k: None

        def submit(record, contracts, mark, reason=""):
            broker.submitted += 1
            return _Order(f"O{broker.submitted}", OrderStatus.LIVE)
        e._submit_live_close = submit
        rec = TL.make_record(trade_id=tid, symbol="QQQ", strategy="ORBStrategy", setup_type="ORB",
                             option_side="call", contracts=5, entry_premium=1.50, total_cost=750.0,
                             max_loss=750.0, stop_premium=0.0, option_symbol="QQQ   261016C00100000",
                             expiry="2099-01-01")
        tl.log_entry(rec)
        with tl._db() as conn:
            row = conn.execute("SELECT * FROM trades WHERE trade_id=?", (tid,)).fetchone()
        res = e._confirm_and_book_live_exit(TL.make_record(**dict(row)), "target", 1.10)
        return res, broker, clock.t - 1000.0

    res, b, elapsed = run(None, "F1-never")
    check("D2 the cancel is sent at 8 s on the fake clock, not 30",
          b.cancel_at is not None and 8.0 <= b.cancel_at < 10.0, f"cancel_at={b.cancel_at}")
    check("D3 the call returns unconfirmed by ~14 s (8 + 6 s grace)",
          (not res.confirmed) and elapsed <= 16.0, f"confirmed={res.confirmed} elapsed={elapsed}")
    res2, b2, el2 = run(3.0, "F1-fills")
    check("D4 unchanged: an order filling at 3 s books at ~3 s, no cancel",
          res2.confirmed and b2.cancel_at is None and el2 <= 4.0,
          f"confirmed={res2.confirmed} cancel_at={b2.cancel_at} elapsed={el2}")

    # r295 (LIVE.2) — the heartbeat is touched on EVERY poll of a working close, through the real writer
    touches = []
    try:
        _orig_hb = EE._hb_touch
        EE._hb_touch = lambda note="", file_path=None: (touches.append(note), _orig_hb(note, file_path))[1]
        try:
            run(None, "F1-hb")
        finally:
            EE._hb_touch = _orig_hb
        hb_file = os.environ["OT_HEARTBEAT_FILE"]
        body = open(hb_file).read().split() if os.path.exists(hb_file) else []
        check("D5 a never-filling close touches the heartbeat on every poll (>= 4 in 8 s), in the SCRATCH file",
              len(touches) >= 4 and all(t == "live-exit poll" for t in touches) and len(body) >= 2
              and body[1] == "live-exit" if len(body) > 1 else False,
              f"touches={len(touches)} {touches[:2]} file={body}")
    except AttributeError as exc:
        check("D5 a never-filling close touches the heartbeat on every poll (>= 4 in 8 s), in the SCRATCH file",
              False, f"no heartbeat writer in the exit engine: {exc}")

    print()
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {', '.join(p.split()[0] for p in PROBLEMS)}")
        return 1
    print("GREEN — every check passed")
    return 0


if __name__ == "__main__":
    try:
        _rc = main()
    finally:
        import shutil
        shutil.rmtree(_SCR, ignore_errors=True)
    sys.exit(_rc)
