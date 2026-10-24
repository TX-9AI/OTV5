#!/usr/bin/env python3
"""tests/check_bfly_vwap_band.py  v1.4
v1.4  2026-10-13  OTV4TEST r278 - A7 drives derived.indicators' module clock to
      its frame's last minute + VWAP_CLOSE_GRACE_S. Since r274 the fold takes
      only closed minutes, so A7 (frame 12:30-12:59 today) was red at any
      wall clock before ~13:00 ET - red on the 10-13 08:00 sweep, both boxes.
v1.3  2026-09-22  OTV4TEST r101 - A8/A9: the cold-start deep fetch
      must use the CALLER's symbol, and an EMPTY fetch must WARN. Born red at
      1104492 where `_accumulate_vwap` takes no symbol and says nothing.
v1.2  2026-09-22  OTV4TEST r96 — A7 pins that a PARTIAL session reports its real start
      rather than the open. Born red against r94, which stamped a one-hour
      VWAP with a session anchor and passed every other check in this file.
v1.1  2026-09-22  OTV4TEST r94 — A5/A6, AND THE OLD FIXTURE IS WHY THIS HID.
      It wrote the literal "primary" and then A4 asserted the reader reads
      "primary" - a closed loop supplying its own answer, section 0.4. A5 now
      writes EVERY interval the engine really emits and demands the reader find
      each, so a reader pinned to any single literal fails; A6 refuses a
      midnight anchor by name. Neither passes against the pre-r94 reader.
A PIN AT TODAY'S VWAP MEETS THE BUTTERFLY'S CONCENTRATION CONDITION (BFLY.5).

v1.0  2026-09-13  OTV4TEST r25. Operator: "VWAP replaces the floor if the pin is
      w/in a predefined portion of VWAP" — "W/in 20% of the expected move,
      expressed as 10% above, 10% below." The VWAP is the bot's own
      midnight-ET-anchored one (indicator_series 'primary'), read through
      `anchors.vwap_now()`, which refuses a prior session's anchor or a stale bar.

🔑 HOP 0 (WORKING_AGREEMENT §21): every case DRIVES the real
`GEXPinButterflyStrategy.generate_signal` against a real DerivedStore in a temp
file holding real indicator_series rows, and reads the verdict off the plan row
it wrote. The fixture ladder is check_plan_prepares' `calls_good`: pin 101,
spot 99, EM 4.12 at the pinned 12:30 clock, so the band is ±0.41.

  W1  conc 0.15 (under the 0.25 floor), today's fresh VWAP 0.20 from the pin
      -> TAKE, and the row says the floor was WAIVED and by how much
  W2  the same with VWAP 1.00 away -> HOLD waiting on pin_concentration, the
      row naming the distance
  W3  a VWAP anchored to a PRIOR session, 0.10 from the pin -> no waiver
      (the engine writes Friday's VWAP all weekend)
  W4  today's anchor but a bar ten minutes old -> no waiver (a stalled feed)
  W5  no VWAP row at all -> no waiver, and the row says there was no VWAP
  W6  control: conc 0.60 meets the floor on its own; no waiver is claimed
  W7  the distance is recorded on the tick as `pin_vwap_dist`, waived or not
  A4  `anchors.vwap()` reads the 'primary' interval the engine actually writes

Born red at r24 (577ceb1) on W1-W5, W7 and A4: no waiver exists there, so W1 holds
instead of taking and no row names a VWAP distance or why there is none, and
vwap() queried '1m'. W6 is the control, green on both sides.
Run:  venv/bin/python tests/check_bfly_vwap_band.py   (or system python3;
      r101 makes the venv resolvable either way)
"""
import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
# ⚠️ r101 — THE LANDER RUNS CHECKS UNDER SYSTEM `python3`, NOT THE VENV, and
# every repo import below reaches `tastytrade`, which lives only in the venv.
# This file was therefore UNRUNNABLE as a declared CHECK — it died on a
# ModuleNotFoundError before evaluating anything. Resolved by glob so the
# interpreter version is never hardcoded; if the SDK still will not import the
# real ImportError is raised, because a gate that cannot run must SAY SO
# rather than be skipped.
import glob as _glob
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*",
                                   "site-packages")):
    if _sp not in sys.path:
        # 🔴 INSERTED AHEAD OF THE SYSTEM PATHS, NOT APPENDED. Appending left
        # /usr/lib/python3/dist-packages first, so the system's older
        # `typing_extensions` shadowed the venv's and anyio died on a missing
        # `sentinel`. Index 1 keeps the repo root (index 0) winning.
        sys.path.insert(1, _sp)
os.environ.setdefault("OT_PAPER_TRADING", "1")
_fails = []
ET = ZoneInfo("America/New_York")


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
    def __init__(self, k, bid, ask):
        self.strike, self.bid, self.ask = float(k), float(bid), float(ask)
        self.mark = (bid + ask) / 2
        self.delta, self.gamma, self.theta = 0.2, 0.01, -0.03
        self.expiry, self.open_interest = "x", 100
        self.symbol = f"C{k}"


class _Chain:
    def __init__(self, calls):
        self.puts, self.calls = [], list(calls)


class _GEX:
    def __init__(self, conc):
        self.gex_environment, self.pin_strike, self.pin_concentration = "PINNING", 101.0, conc


# 🔴 r94 — THE INTERVAL COMES FROM THE ENGINE, NEVER FROM THIS FILE.
# THE OLD FIXTURE WROTE THE LITERAL "primary" AND THEN A4 ASSERTED THAT THE
# READER READS "primary" — a closed loop that supplied its own answer (§0.4),
# and it is the whole reason this went unnoticed for two days. `primary` was
# never a timeframe: it is the FALLBACK row in `indicators.derive()`, emitted
# only `if not rows`. r69 repaired the per-timeframe loop, the fallback stopped
# firing, and `vwap_now()` spent two days querying a row nobody writes —
# MEASURED 2026-09-22: 882 rows each for 5m/15m/1h/1d all carrying a VWAP,
# `primary` last seen 09-20 13:29 ET, the minute r69 landed.
# 🔑 SO THE FIXTURE ASKS THE ENGINE. If the writer's interval set changes
# again, this file follows it instead of pinning a stale literal — and A4
# becomes a real assertion rather than a restatement of its own setup.
# ⚠️ A REAL PRODUCTION INTERVAL, AND MY FIRST CUT GUESSED IT FROM THE SOURCE.
# That helper walked `indicators.py` for string literals and returned
# "primary" — because the real frames arrive at runtime as `vote.timeframe`
# and appear nowhere in the source. It would have kept the fixture writing the
# very dead row this revision exists to stop reading. MEASURED on the live
# store 2026-09-22: the engine writes 5m, 15m, 1h and 1d.
# 🔑 THE FIXTURE'S INTERVAL BARELY MATTERS NOW — A5 below writes EVERY one of
# them and demands the reader find each, which is the property that was
# actually broken. This is just a sane default rather than a load-bearing
# guess.
_ENGINE_INTERVAL = "5m"


def main():
    from strategy import plan as P
    import strategy.gex_pin_butterfly as bf
    from derived import anchors as A
    from data.derived_store import DerivedStore
    from utils.time_utils import ET as _ET_pin

    st = _Store()
    P.bind_store(st)
    os.environ["OT_RELAXED_ENTRY"] = "0"
    bf.ENABLED = True
    bf.EARLIEST_ET, bf.LATEST_ET = "09:30", "16:00"
    bf.PERSIST_TICKS = 1
    _em_real = bf.expected_move
    _fixed_now = bf.datetime(2026, 8, 27, 12, 30, tzinfo=_ET_pin)
    bf.expected_move = lambda u, iv, now=None: _em_real(u, iv, now=_fixed_now)

    calls_good = [_C(k, m - 0.005, m + 0.005) for k, m in
                  ((99, 2.55), (100, 1.70), (101, 1.00), (102, 0.70), (103, 0.45), (104, 0.30))]
    common = dict(price_now=99.0, now_et="12:30", atm_iv=0.90)
    now = time.time()
    # 🔴 r94 — THE FIXTURE ANCHORS AT THE SESSION OPEN, because the writer does.
    # Operator: *"don't anchor VWAP to midnight."* A fixture still built on
    # midnight would fail every case for the RIGHT reason and teach nothing.
    sess = datetime.fromtimestamp(now, ET).replace(hour=9, minute=30, second=0, microsecond=0)
    today_ms = int(sess.timestamp() * 1000)
    prior_ms = int((sess - timedelta(days=1)).timestamp() * 1000)

    def _store_with(vwap=None, anchor_ms=today_ms, bar_age_s=30.0):
        ds = DerivedStore(path=os.path.join(tempfile.mkdtemp(), "derived.db"))
        if vwap is not None:
            ds.append_indicators([("TST", _ENGINE_INTERVAL, now - 5, int((now - bar_age_s) * 1000),
                                   None, None, None, None, None, None, None,
                                   float(vwap), None, None, anchor_ms)])
        A._store = lambda: ds
        A._sym = lambda: "TST"
        return ds

    tick_ts = [30.0]

    def _run(conc, **kw):
        _store_with(**kw)
        B = bf.GEXPinButterflyStrategy()
        B.planner.symbol = "TST"
        tick_ts[0] += 1.0
        P.begin_tick(tick_ts[0])
        sig = B.generate_signal(gex=_GEX(conc), chain=_Chain(calls_good), **common)
        row = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy=? AND ts_epoch=?",
                              ("GEXPinButterfly", tick_ts[0])).fetchone()
        dist = st.conn.execute("SELECT value FROM plan_check WHERE strategy=? AND ts_epoch=? "
                               "AND check_name='pin_vwap_dist'", ("GEXPinButterfly", tick_ts[0])).fetchone()
        return sig, (row or ("", "")), (dist[0] if dist else None)

    sig, row, dist = _run(0.15, vwap=100.8)
    check("W1 conc under the floor, pin 0.20 from today's VWAP (band ±0.41) -> TAKE, the waiver named",
          sig is not None and row[0] == "TAKE" and "WAIVED" in row[1] and "100.80" in row[1],
          f"{row[0]}: {row[1][:160]}")
    check("W7 the pin-to-VWAP distance is on the tick as pin_vwap_dist",
          dist is not None and abs(dist - 0.20) < 1e-6, f"pin_vwap_dist={dist}")

    sig, row, dist = _run(0.15, vwap=100.0)
    check("W2 VWAP 1.00 from the pin -> HOLD waiting on pin_concentration, distance named",
          sig is None and row[0] == "HOLD" and "pin_concentration" in row[1] and "1.00 off" in row[1],
          f"{row[0]}: {row[1][-140:]}")

    sig, row, _ = _run(0.15, vwap=100.9, anchor_ms=prior_ms)
    check("W3 a PRIOR session's VWAP 0.10 from the pin waives nothing",
          sig is None and row[0] == "HOLD" and "WAIVED" not in row[1] and "prior session" in row[1],
          f"{row[0]}: {row[1][-140:]}")

    sig, row, _ = _run(0.15, vwap=100.9, bar_age_s=600.0)
    check("W4 today's VWAP on a bar ten minutes old waives nothing",
          sig is None and row[0] == "HOLD" and "WAIVED" not in row[1] and "stale" in row[1],
          f"{row[0]}: {row[1][-140:]}")

    sig, row, dist = _run(0.15)
    check("W5 no VWAP row -> no waiver, and the row says there was no VWAP",
          sig is None and row[0] == "HOLD" and "no VWAP" in row[1] and dist is None,
          f"{row[0]}: {row[1][-140:]}")

    sig, row, _ = _run(0.60, vwap=95.0)
    check("W6 control: conc 0.60 meets the floor alone -> TAKE, no waiver claimed",
          sig is not None and row[0] == "TAKE" and "WAIVED" not in row[1], f"{row[0]}: {row[1][:120]}")

    _store_with(vwap=715.35)
    check(f"A4 anchors.vwap() reads a real engine interval ('{_ENGINE_INTERVAL}')",
          A.vwap() == 715.35, f"vwap()={A.vwap()}")

    # ══ A5 — THE READER MUST NOT BE PINNED TO ONE INTERVAL (r94) ═══════════
    # 🔴 THE CHECK THAT WOULD HAVE CAUGHT IT, AND NOTHING ABOVE WOULD HAVE.
    # Every W-case and A4 pass just as happily against a reader hardcoded to a
    # single interval, because the fixture supplies that same interval — the
    # closed loop that let `vwap_now()` query a dead `primary` row for two days
    # while the engine wrote 882 rows a day to four other frames.
    # 🔑 SO THIS WRITES EACH INTERVAL THE ENGINE REALLY EMITS, ONE AT A TIME,
    # AND DEMANDS THE READER FIND EVERY ONE. A reader pinned to any single
    # literal fails on the other three. It is a RUNTIME assertion, not a grep
    # over the query string (§21).
    _bad = []
    for _iv in ("5m", "15m", "1h", "1d"):
        _ds = DerivedStore(path=os.path.join(tempfile.mkdtemp(), "derived.db"))
        _ds.append_indicators([("TST", _iv, now - 5, int((now - 30.0) * 1000),
                                None, None, None, None, None, None, None,
                                711.11, None, None, today_ms)])
        A._store = lambda _d=_ds: _d
        A._sym = lambda: "TST"
        _v, _why = A.vwap_now()
        if _v != 711.11:
            _bad.append(f"{_iv}:{_why or _v}")
    check("A5 the reader finds a VWAP on EVERY interval the engine writes",
          not _bad, f"unreadable: {_bad}")

    # ══ A6 — THE ANCHOR IS THE SESSION OPEN, NOT MIDNIGHT (r94) ════════════
    # Operator, twice: *"don't anchor VWAP to midnight"*, *"I want the VWAP
    # anchored correctly."* Midnight folds overnight and pre-market prints —
    # thin, away from the session's value area — into a number the butterfly
    # reads as today's VWAP.
    _mid = int(datetime.fromtimestamp(now, ET).replace(
        hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    _store_with(vwap=712.22, anchor_ms=_mid)
    _v_mid, _why_mid = A.vwap_now()
    check("A6 a MIDNIGHT-anchored row is refused, and the reason says so",
          _v_mid is None and "09:30" in (_why_mid or ""), f"{_v_mid} / {_why_mid}")

    # ══ A7 — A PARTIAL SESSION MAY NOT WEAR A SESSION-OPEN STAMP (r96) ════
    # 🔴 THE DEFECT r94 INTRODUCED AND r96 CLOSES. r94 moved the anchor to the
    # 09:30 open, but the live tick frame is SIXTY BARS — measured 2026-09-22
    # 13:53 ET, 12:55->13:54 — so a cold start folded one hour and stamped it
    # with a session anchor: 745.4264 against a true 744.7697.
    # ⚠️ THAT IS WORSE THAN THE BUG r94 FIXED. A mismatched anchor FAILS CLOSED
    # and says why; a partial-window value PASSES and feeds the butterfly's
    # waiver a plausible wrong number (§0.5).
    # 🔑 SO THE ENGINE REPORTS WHERE THE FOLD REALLY BEGAN, and a short session
    # then fails the reader's own "is this today's open?" test by construction
    # rather than by a second rule that could drift out of step.
    import pandas as _pdq
    from derived.indicators import IndicatorEngine as _IE
    _now_et = datetime.fromtimestamp(now, ET)
    _open = _now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    # a frame that starts THREE HOURS after the open, deep fetch unavailable
    _idx = _pdq.date_range(_open + timedelta(hours=3), periods=30, freq="1min", tz=ET)
    _df = _pdq.DataFrame({"high": 100.5, "low": 99.5, "close": 100.0, "volume": 1000.0},
                         index=_idx)
    import data.market_data as _md
    import derived.indicators as _ind
    _keep = getattr(_md, "fetch_candles", None)
    _md.fetch_candles = lambda *a, **k: None          # force the partial path
    # r278: since r274 the fold takes only CLOSED minutes by the engine's module
    # clock, so a wall clock before ~13:00 ET folded nothing and A7 was red on
    # every 08:00 sweep. Drive that clock to the frame's last minute + grace.
    _t7 = _idx[-1].timestamp() + 60.0 + _ind.VWAP_CLOSE_GRACE_S + 1.0
    class _T7:
        @staticmethod
        def time(): return _t7
    _time7 = _ind.time
    _ind.time = _T7                       # the engine reads ITS module clock; nothing else is patched
    try:
        _e = _IE.__new__(_IE)
        _e.symbol = "TST"; _e._pv = _e._v = 0.0
        _e._anchor_ms = None; _e._last_bar_ms = None; _e._first_bar_ms = None
        _v7, _, _, _a7 = _e._accumulate_vwap(_df)
    finally:
        _ind.time = _time7
        if _keep is not None:
            _md.fetch_candles = _keep
    _open_ms = int(_open.timestamp() * 1000)
    check("A7 a PARTIAL session reports its real start, not the open",
          _v7 is not None and _a7 is not None and abs(_a7 - _open_ms) > 120_000,
          f"vwap={_v7} anchor_off_by={(_a7 - _open_ms)/1000.0 if _a7 else None:.0f}s")

    # ══ A8 — THE DEEP FETCH GETS THE CALLER'S SYMBOL (r101) ═══════════════
    # 🔴 r96's COLD-START REBUILD WAS CALLED WITH AN EMPTY SYMBOL. It read
    # `self.symbol`, but `derive()` resolves `self.symbol or ctx["symbol"]`
    # PRECISELY BECAUSE THE ATTRIBUTE CAN BE BLANK. So `fetch_candles("", ...)`
    # returned nothing, the engine folded the sixty-bar tick frame anyway, and
    # reported 745.4476 against a true 744.7949 — with the anchor still reading
    # 09:30. The repair r96 shipped could not run on the path that needed it.
    # 🔑 THE SPY RECORDS WHAT THE REAL FUNCTION ASKED FOR. Asserting the
    # parameter exists would pass against a body that ignores it (§21).
    _asked = []
    _md.fetch_candles = lambda _s, *a, **k: (_asked.append(_s), None)[1]
    try:
        _e8 = _IE.__new__(_IE)
        _e8.symbol = ""                       # the blank attribute, on purpose
        _e8._pv = _e8._v = 0.0
        _e8._anchor_ms = None; _e8._last_bar_ms = None; _e8._first_bar_ms = None
        _e8._accumulate_vwap(_df, "QQQ")
        _a8_ok, _a8_why = (_asked == ["QQQ"]), f"fetch_candles saw {_asked!r}"
    except TypeError as _te:
        _a8_ok, _a8_why = False, f"the caller's symbol cannot be passed: {_te}"
    finally:
        if _keep is not None:
            _md.fetch_candles = _keep
    check("A8 the cold-start deep fetch uses the CALLER's symbol", _a8_ok, _a8_why)

    # ══ A9 — THE FALL-THROUGH IS LOUD (r101) ══════════════════════════════
    # 🔴 THE FIX r96 SHIPPED FELL THROUGH IN SILENCE when the deep fetch came
    # back empty: the partial frame was folded and nothing said so. §0.5 —
    # silence is the worst failure mode, and this one hands the butterfly's
    # concentration waiver a plausible wrong number. A7 catches the ANCHOR
    # being honest; A9 catches the OPERATOR being told.
    import logging as _lg
    class _Cap(_lg.Handler):
        def __init__(self): super().__init__(); self.msgs = []
        def emit(self, rec): self.msgs.append(rec.getMessage())
    _cap = _Cap(); _cap.setLevel(_lg.WARNING)
    _ilog = _lg.getLogger("derived.indicators")
    _ilog.addHandler(_cap)
    _md.fetch_candles = lambda *a, **k: None          # empty, not an exception
    try:
        _e9 = _IE.__new__(_IE)
        _e9.symbol = "TST"; _e9._pv = _e9._v = 0.0
        _e9._anchor_ms = None; _e9._last_bar_ms = None; _e9._first_bar_ms = None
        _e9._accumulate_vwap(_df, "TST")
    except Exception:                                  # noqa: BLE001
        pass
    finally:
        _ilog.removeHandler(_cap)
        if _keep is not None:
            _md.fetch_candles = _keep
    check("A9 an EMPTY deep fetch warns rather than falling through silently",
          any("deep 1m fetch" in m for m in _cap.msgs),
          f"warnings seen: {_cap.msgs or 'NONE — it fell through in silence'}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: {', '.join(_fails)}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
