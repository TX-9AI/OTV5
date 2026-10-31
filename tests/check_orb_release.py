#!/usr/bin/env python3
"""
tests/check_orb_release.py  v5.0
v5.0  2026-10-30  OTV5 r61 (ORB.10) — new. THE RETIRED ORB HELD THE ENGINE OPEN, SO RUNAWAY NEVER SAW THE REVERSAL.
      ORBStrategy is DORMANT; the ORB engine runs for RunawayContinuation, which reads its direction off the engine
      state. After the first break+retest the engine sat in OPEN_LONG / OPEN_SHORT to 15:40 (_advance_state returns
      early there and notify_position_closed, the only release, needs an ORB close, an ORB offer release or a
      same-side Runaway fire). QQQ 2026-10-30: OPEN_LONG 10:00-15:40; the 10:14 close broke the 694.46 low and the
      10:24 / 10:25 closes took the short 50% (692.975), and Runaway could only look long. The operator, 2026-10-30:
      "investigate and fix this".

  Q0  CONTROL: the tape replayed tick by tick WITHOUT a release confirms OPEN_LONG at 10:00 and holds it to 10:40
      (the defect, as the fleet ran 10-26..10-30)
  Q1  with the run_analysis release, the engine leaves OPEN_LONG on the confirming tick (10:00) and is never
      OPEN_* at the end of a tick
  Q2  the 10:14 close below the low arms the SHORT: ARMED_SHORT at 10:15, the short 50% 692.975
  Q3  the 50% short is ACCEPTED at ~10:25 (10:24 close, held): INVALIDATED runaway, break_direction short
  Q4  Runaway's plan (RunawayPlan.prepare) prepares SHORT at 10:15 / 10:18 and is past "the 50 ACCEPTED" at 10:26;
      before the release it could only prepare LONG (Q4c, the base's reading)
  Q5  one confirmation per 1m bar: the released bar is not re-confirmed by the next 15 s ticks
  R1  the tape reach-back with release_open=True (a restart at 10:27) reaches the live loop's state
  R2  CONTROL: release_open left at its default keeps r95's reach-back (OPEN_LONG consumed -> re-armed, MISSED)
  U1  release_unowned() is a no-op off OPEN_*; U2 50% accepted -> INVALIDATED runaway; U3 past the cutoff ->
      EXPIRED; U4 a last close inside -> WAITING_FOR_BREAK; U5 else ARMED on the impulse, attempt + 1, the bar
      remembered (the notify_position_closed outcomes)
  M1  main._orb_release_due: ORB dormant, no offer, no ORB position -> True; OT_ORB_TRADE=1 -> False; an open
      ORB position -> False
  M2  main.run_analysis releases right after get_orb_engine().update() and before orb_state.json is written, and
      the reach-back is called with release_open

The fixture is QQQ's 2026-10-30 1m tape 09:30-10:40 (the box's candles.csv, S3 bundle), range 694.46-697.43
(the box's "ORB range ESTABLISHED" 09:35:18). THE WALL CLOCK IS PINNED to each simulated tick
(utils.time_utils.datetime): the engine and the plan judge "closed" by time, and the lander runs CHECKs at any hour.
Born red on 5ef49e1 at Q1, Q2, Q3, Q4a, Q4b, R1, U1-U5, M1, M2 (Q0, Q4c, Q5 - nothing is released there - and R2
pass); Q5 and R1 go red on the fix without the released-bar skip (10:00 and the 10:18-10:21 retests re-confirm
every 15 s).
Run:  python3 tests/check_orb_release.py
"""
import datetime as D
import logging
import os
import sqlite3
import sys
import tempfile
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_s = tempfile.mkdtemp(prefix="check_orb_release.")
for _k, _v in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived.db"), ("OT_RESTING_DB", "resting.db"),
               ("OT_FEED_DB", "feed.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"), ("OT_RESTING_STOP_STATE", "rs.json"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(_s, _v)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
os.environ.setdefault("OT_PAPER_TRADING", "1")
os.environ.pop("OT_ORB_TRADE", None)                            # the shipped roster: ORB dormant
ET = ZoneInfo("America/New_York")
CLOCK = [D.datetime(2026, 10, 30, 9, 35, 0, tzinfo=ET)]
try:
    import utils.time_utils as _tu                              # noqa: E402
    _REAL_DT = _tu.datetime

    class _Pinned(_REAL_DT):
        @classmethod
        def now(cls, tz=None):
            t = CLOCK[0]
            return t.astimezone(tz) if tz is not None else t.replace(tzinfo=None)
    _tu.datetime = _Pinned
    import pandas as pd                                         # noqa: E402
    import config                                               # noqa: E402
    config.LOG_FILE = os.path.join(_s, "bot.log")               # BOX.16: main's file handler goes to scratch
    from analysis import orb_engine as OE                       # noqa: E402
    from analysis.orb_engine import ORBState as S               # noqa: E402
except Exception as exc:                                        # noqa: BLE001
    print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
    sys.exit(2)

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


HIGH, LOW = 697.43, 694.46
# QQQ 2026-10-30 1m (open, high, low, close), 09:30 .. 10:40 ET
BARS = [
    (697.21, 697.43, 696.0, 696.445), (696.44, 696.61, 695.7, 695.9281), (695.91, 696.0, 695.06, 695.13), (695.15, 695.59, 695.05, 695.4),
    (695.46, 695.48, 694.46, 694.72), (694.62, 694.75, 694.05, 694.5101), (694.52, 695.65, 694.14, 695.46), (695.49, 695.92, 694.99, 695.645),
    (695.645, 696.7, 695.55, 696.685), (696.7, 697.3699, 696.43, 697.29), (697.27, 697.27, 696.44, 696.6), (696.62, 697.23, 696.115, 696.14),
    (696.022, 696.145, 695.47, 695.79), (695.815, 696.13, 695.539, 695.705), (695.74, 696.16, 695.63, 695.91), (695.88, 696.42, 695.58, 695.75),
    (695.71, 696.4967, 695.615, 696.405), (696.42, 696.59, 695.7999, 695.89), (695.88, 695.94, 695.24, 695.75), (695.65, 696.895, 695.65, 696.105),
    (696.1, 696.68, 695.82, 696.68), (696.66, 696.93, 696.12, 696.19), (696.26, 696.61, 696.11, 696.48), (696.48, 697.1, 696.39, 697.0278),
    (697.002, 697.24, 696.71, 697.16), (697.18, 697.21, 696.42, 696.66), (696.64, 697.05, 696.32, 696.43), (696.445, 696.6, 696.06, 696.535),
    (696.5134, 697.94, 696.505, 697.566), (697.55, 698.63, 697.3662, 698.18), (698.18, 698.57, 697.91, 698.33), (698.36, 698.57, 697.86, 697.86),
    (697.855, 697.875, 697.14, 697.2), (697.1915, 697.3528, 696.89, 697.27), (697.32, 697.9, 697.215, 697.5397), (697.466, 697.69, 696.7, 696.86),
    (696.89, 697.59, 696.76, 697.54), (697.58, 697.72, 697.01, 697.15), (697.17, 697.17, 696.71, 696.842), (696.83, 696.83, 696.145, 696.18),
    (696.15, 696.18, 695.59, 695.62), (695.58, 696.01, 695.1801, 695.205), (695.195, 695.3, 694.915, 695.1), (695.1, 695.16, 694.625, 694.89),
    (694.89, 694.98, 694.24, 694.249), (694.23, 694.8, 694.22, 694.5), (694.5, 694.57, 694.17, 694.195), (694.195, 694.5, 694.1601, 694.2899),
    (694.29, 694.85, 694.1, 694.4), (694.3909, 694.64, 694.31, 694.3287), (694.32, 694.66, 694.13, 694.255), (694.27, 694.39, 693.69, 693.93),
    (693.95, 693.9701, 693.5, 693.655), (693.65, 693.87, 692.91, 693.01), (693.005, 693.07, 692.719, 692.9), (692.92, 692.97, 692.68, 692.87),
    (692.85, 693.36, 692.85, 693.05), (693.04, 693.31, 693.0, 693.2101), (693.21, 693.86, 693.195, 693.635), (693.68, 694.185, 693.675, 694.09),
    (694.11, 694.37, 693.89, 694.0601), (694.06, 694.77, 693.9505, 694.58), (694.6, 694.72, 694.03, 694.08), (694.07, 694.9, 693.92, 694.7426),
    (694.84, 695.03, 694.42, 694.5), (694.5, 695.18, 694.5, 694.93), (694.89, 695.2799, 694.82, 694.9), (694.91, 695.48, 694.76, 695.355),
    (695.37, 696.91, 695.3401, 696.9), (696.89, 697.2, 696.61, 696.73), (696.71, 697.26, 696.17, 697.12),
]
IDX = pd.date_range("2026-10-30 09:30", periods=len(BARS), freq="1min", tz=ET)
TAPE = pd.DataFrame([{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in BARS], index=IDX)


def _at(hm, sec=0):
    h, m = map(int, hm.split(":"))
    return D.datetime(2026, 10, 30, h, m, sec, tzinfo=ET)


def _engine():
    e = OE.ORBEngine()
    d = e._data
    d.orb_high, d.orb_low, d.orb_width = HIGH, LOW, round(HIGH - LOW, 4)
    d.state = S.WAITING_FOR_BREAK
    e._range_date = "2026-10-30"
    return e


def _release(e):
    """run_analysis's step after update(): release an OPEN_* nobody can trade (ORB dormant here)."""
    rel = getattr(e, "release_unowned", None)
    if rel is not None and e.data.state in (S.OPEN_LONG, S.OPEN_SHORT):
        rel()


def live(release, until="10:40", observe=None):
    """The 15 s loop on the tape: ticks at :00 :15 :30 :45 of each minute from 09:35, the frame ending at the
    forming bar, the clock pinned to the tick. -> (engine, [(tick hm:ss, state after the tick, seq)])"""
    e = _engine()
    trail = []
    for i in range(5, len(BARS)):
        hm = IDX[i].strftime("%H:%M")
        if hm > until:
            break
        for sec in (0, 15, 30, 45):
            CLOCK[0] = _at(hm, sec)
            e.update(None, TAPE.iloc[:i + 1], BARS[i][3], None)
            if release:
                _release(e)
            d = e.data
            trail.append((f"{hm}:{sec:02d}", str(d.state), d.confirmation_seq, d.attempt_number,
                          d.invalidation_reason, d.break_direction, d.fifty_accepted, d.target_50pct))
            if observe is not None:
                observe(f"{hm}:{sec:02d}", e)
    return e, trail


def first(trail, pred):
    return next((t for t in trail if pred(t)), None)


logging.disable(logging.CRITICAL)

# ── Q0 — the defect, reproduced ────────────────────────────────────────────
e0, tr0 = live(release=False)
c0 = first(tr0, lambda t: t[1] == S.OPEN_LONG)
check("Q0 CONTROL: no release -> OPEN_LONG from 10:00 held to 10:40",
      c0 is not None and c0[0].startswith("10:00") and e0.data.state == S.OPEN_LONG
      and all(t[1] == S.OPEN_LONG for t in tr0 if t[0] >= c0[0]), f"first={c0} end={e0.data.state}")

# ── Q1-Q3, Q5 — the release ─────────────────────────────────────────────────
rc_rows = []
_RP = None
try:
    import database.trade_logger as _TL
    _TL._trade_logger = _TL.TradeLogger(os.path.join(_s, "book.db"))
    from strategy import plan as _P
    from strategy.runaway_plan import RunawayPlan

    class _Store:
        def __init__(self):
            self.conn = sqlite3.connect(":memory:")
            self.conn.row_factory = sqlite3.Row

        def commit(self):
            self.conn.commit()
    _st = _Store()
    _P.ensure_tables(_st)
    _P.bind_store(_st)
    _RP = RunawayPlan()
except Exception as exc:                                        # noqa: BLE001
    print(f"  (runaway plan unavailable: {type(exc).__name__}: {exc})")


def _ask_runaway(tick, e):
    if _RP is None or not tick.endswith(":15"):
        return
    hm = tick[:5]
    i = list(IDX.strftime("%H:%M")).index(hm)
    try:
        _P.begin_tick()
        pr = _RP.prepare(orb=e.data, atr_pct=0.14, price_now=BARS[i][3], now_et=hm, chain=None,
                         df_1m=TAPE.iloc[:i + 1])
        _P.close_tick(_st, "TEST")
        r = _st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='RunawayContinuation' "
                             "ORDER BY rowid DESC LIMIT 1").fetchone()
        rc_rows.append((hm, pr.direction, getattr(pr, "tp50", None), (r["reason"] if r else "") or ""))
    except Exception as exc:                                    # noqa: BLE001
        rc_rows.append((hm, "?", None, f"raised {type(exc).__name__}: {exc}"))


e1, tr1 = live(release=True, observe=_ask_runaway)
c1 = first(tr1, lambda t: t[2] >= 1)
check("Q1 the confirming tick (10:00) leaves OPEN_LONG; no tick ends OPEN_*",
      c1 is not None and c1[0].startswith("10:00") and c1[1] != S.OPEN_LONG
      and not any(t[1] in (S.OPEN_LONG, S.OPEN_SHORT) for t in tr1), f"confirm={c1}")
a2 = first(tr1, lambda t: t[1] == S.ARMED_SHORT)
check("Q2 the 10:14 close below the low arms the SHORT at 10:15",
      a2 is not None and a2[0] == "10:15:00", f"first ARMED_SHORT={a2}")
acc = first(tr1, lambda t: t[1] == S.INVALIDATED and t[0] >= "10:15")
check("Q3 the short 50% 692.975 is ACCEPTED ~10:25 -> INVALIDATED runaway, break short",
      acc is not None and "10:25:00" <= acc[0] <= "10:26:00" and acc[4] == "runaway" and acc[5] == "short"
      and acc[6] is True and abs(acc[7] - 692.975) < 1e-6, f"at={acc}")
_per_bar = {}
for t in tr1:
    _per_bar.setdefault(t[0][:5], set()).add(t[2])
_multi = [hm for hm, seqs in _per_bar.items() if len(seqs) > 1 and max(seqs) - min(seqs) > 1]
_seq_jumps = sum(1 for a, b in zip(tr1, tr1[1:]) if b[2] > a[2] and a[0][:5] == b[0][:5] and not b[0].endswith(":00"))
check("Q5 one confirmation per 1m bar: no 15 s re-read of a released bar confirms again",
      not _multi and _seq_jumps == 0, f"bars with >1 confirm={_multi} same-bar re-confirms={_seq_jumps}")

# ── Q4 — Runaway sees the short ────────────────────────────────────────────
_r = {hm: (d, tp, why) for hm, d, tp, why in rc_rows}
_s15 = _r.get("10:18") or ("", None, "")
_s26 = _r.get("10:26") or ("", None, "")
check("Q4a Runaway's plan prepares SHORT on the re-break (10:15 and 10:18), the short 50% 692.975",
      _s15[0] == "short" and _s15[1] is not None and abs(_s15[1] - 692.975) < 1e-6
      and (_r.get("10:15") or ("",))[0] == "short", f"10:15 {(_r.get('10:15') or ('',))[0]} 10:18 {_s15}")
check("Q4b at 10:26 the plan is SHORT and past 'waiting on: the 50 ACCEPTED'",
      _s26[0] == "short" and "waiting on: the 50 ACCEPTED" not in _s26[2], f"10:26 {_s26}")
rc_rows.clear()
live(release=False, observe=_ask_runaway)
_b = {hm: d for hm, d, tp, why in rc_rows}
check("Q4c CONTROL: without the release the plan can only prepare LONG at 10:18 and 10:26",
      _b.get("10:18") == "long" and _b.get("10:26") == "long", f"10:18={_b.get('10:18')} 10:26={_b.get('10:26')}")

# ── R1 / R2 — the restart reach-back ───────────────────────────────────────
_live27, _ = live(release=True, until="10:26")
CLOCK[0] = _at("10:27", 15)
_cut = TAPE.iloc[:IDX.get_loc(IDX[IDX.strftime("%H:%M") == "10:27"][0]) + 1]
er = _engine()
try:
    ran = er.rebuild_from_tape(_cut, release_open=True)
    rd = er.data
    check("R1 the reach-back with release_open=True reaches the live loop's state at 10:27",
          ran and rd.state == _live27.data.state and rd.fifty_accepted == _live27.data.fifty_accepted
          and rd.break_direction == _live27.data.break_direction and er.broke_low and er.broke_high
          and rd.attempt_number == _live27.data.attempt_number,
          f"replay={rd.state}/{rd.break_direction}/att{rd.attempt_number} live={_live27.data.state}/"
          f"{_live27.data.break_direction}/att{_live27.data.attempt_number}")
except TypeError as exc:
    check("R1 the reach-back with release_open=True reaches the live loop's state at 10:27", False, str(exc))
CLOCK[0] = _at("10:01", 15)
eb = _engine()
eb.rebuild_from_tape(TAPE.iloc[:IDX.get_loc(IDX[IDX.strftime("%H:%M") == "10:01"][0]) + 1])
_m = eb.take_missed_confirmation()
check("R2 CONTROL: default release_open keeps r95 (OPEN_LONG consumed -> re-armed, one MISSED)",
      eb.data.state == S.AWAITING_RANGE_REENTRY and _m is not None and _m.get("direction") == "LONG",
      f"state={eb.data.state} missed={(_m or {}).get('direction')}")


# ── U1-U4 — the release is notify_position_closed ──────────────────────────
def _open_long(**kv):
    e = _engine()
    d = e._data
    d.state, d.break_direction = S.OPEN_LONG, "long"
    d.target_50pct, d.attempt_number, d.confirmation_seq = HIGH + 1.485, 1, 1
    d.last_retest_bar_ts = str(IDX[29])
    for k, v in kv.items():
        setattr(d, k, v)
    return e


CLOCK[0] = _at("10:05")
_rel = getattr(OE.ORBEngine, "release_unowned", None)
if _rel is None:
    for n in ("U1", "U2", "U3", "U4", "U5"):
        check(f"{n} release_unowned() exists", False, "orb_engine has no release_unowned")
else:
    eu = _engine()
    check("U1 off OPEN_* the release is a no-op", eu.release_unowned() is False and eu.data.state == S.WAITING_FOR_BREAK)
    eu = _open_long(fifty_accepted=True)
    eu.release_unowned()
    check("U2 50% accepted -> INVALIDATED runaway", eu.data.state == S.INVALIDATED
          and eu.data.invalidation_reason == "runaway", eu.data.state)
    CLOCK[0] = _at("15:41")
    eu = _open_long()
    eu.release_unowned()
    check("U3 past the ORB cutoff -> EXPIRED", eu.data.state == S.EXPIRED, eu.data.state)
    CLOCK[0] = _at("10:05")
    eu = _open_long(last_close_inside=True)
    eu.release_unowned()
    check("U4 a last close inside -> WAITING_FOR_BREAK (re-armed)", eu.data.state == S.WAITING_FOR_BREAK,
          eu.data.state)
    eu = _open_long()
    eu.release_unowned()
    check("U5 otherwise ARMED_LONG on the original impulse, attempt + 1, the bar remembered",
          eu.data.state == S.ARMED_LONG and eu.data.attempt_number == 2
          and getattr(eu.data, "released_bar_ts", "") == str(IDX[29]), f"{eu.data.state} att={eu.data.attempt_number}")

# ── M1 / M2 — main.py ──────────────────────────────────────────────────────
CLOCK[0] = _at("10:05")
try:
    import main as M                                            # noqa: E402
except Exception as exc:                                        # noqa: BLE001
    M = None
    check("M0 main imports", False, f"{type(exc).__name__}: {exc}")
if M is not None:
    _due = getattr(M, "_orb_release_due", None)

    class _St:
        paper_trading = True

    class _PM:
        def __init__(self, recs):
            self.recs = recs

        def get_open_records(self):
            return self.recs
    if _due is None:
        check("M1 main._orb_release_due exists", False, "absent")
    else:
        _real_pm = M.get_position_manager
        try:
            M.get_position_manager = lambda paper=True: _PM([])
            a = _due(_St())
            os.environ["OT_ORB_TRADE"] = "1"
            b = _due(_St())
            os.environ.pop("OT_ORB_TRADE", None)
            M.get_position_manager = lambda paper=True: _PM([{"strategy": "ORBStrategy"}])
            c = _due(_St())
            M.get_position_manager = lambda paper=True: _PM([{"strategy": "Breakout"}])
            d_ = _due(_St())
        finally:
            M.get_position_manager = _real_pm
            os.environ.pop("OT_ORB_TRADE", None)
        check("M1 _orb_release_due: dormant ORB True, OT_ORB_TRADE=1 False, open ORB position False, other "
              "strategy's position True", a is True and b is False and c is False and d_ is True,
              f"dormant={a} active={b} orb_open={c} other_open={d_}")
    import inspect
    src = inspect.getsource(M.run_analysis)
    iu = src.find("_orb_eng.update(")
    ir = src.find("release_unowned(", iu if iu >= 0 else 0)
    iw = src.find("orb_state.json\"", iu if iu >= 0 else 0)
    check("M2 run_analysis releases right after update() and before orb_state.json; the reach-back passes "
          "release_open", 0 <= iu < ir < iw and "rebuild_from_tape(_deep_1m, release_open=" in src,
          f"update@{iu} release@{ir} write@{iw}")

print()
if FAILED:
    print(f"FAIL — {len(FAILED)} check(s): {FAILED}")
    sys.exit(1)
print("check_orb_release: ALL PASS")
sys.exit(0)
