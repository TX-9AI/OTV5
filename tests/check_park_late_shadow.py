#!/usr/bin/env python3
"""
tests/check_park_late_shadow.py  v5.2
v5.2  2026-10-31  OTV5 r68 (CFG.5) — OT_RESTING_STOP_STATE leaves the scratch env: the resting stop and its state file are deleted
      (the operator, 2026-10-31: "Resting stop was a study. It failed. Get this the fuck out of here"). No check changed.
v5.1  2026-10-31  OTV5 r67 (PARC.4) — B1's _evaluate_route pin RE-POINTED (WA section 38.4): 83462494db328bc4 ->
      ad64d87edd0b44fa. The function's only change is the removed `elif strategy == "PARC"` arm (4 lines: the test,
      two comment lines, the _evaluate_parc call), which no PARK record can reach; _evaluate_park, _park_cf and
      _decay_read keep their 0e4d240 hashes and D1 (decisions ON vs OFF) is unchanged. PARC is removed. The operator,
      2026-10-31: "On PARC, no. It was an idea. It failed. It's done." and "Yes" to removing its code.
v5.0  2026-10-31  OTV5 r63 (PARK.LATE1) — THE PARK LATE-DAY PEAK SHADOW. RECORD ONLY: IT NEVER CLOSES OR CHANGES A PARK TRADE.
      The operator, 2026-10-30: "Giveback: $18,764 of $43,258 peak open profit; PARK accounts for $13,780 of it - this is
      disgusting ... We have to figure this out."; 2026-10-31, on the study's log-only shadow: "yes to all of the
      prepared solutions". The rule (scratchpad parkgb, "late X20 arm+50% from 14:30"): from 14:30 ET (close-anchored
      on a half day), armed once the best mark is >= +50% of entry (the r58 decay stop's peak source: this mark,
      mfe_premium, the persisted max_premium_seen), it WOULD exit when open profit p <= peak_p x 0.80.
      Driven through the REAL ExitEngine.evaluate and the REAL ManagementPlan._one; strategy.plan.write_row is
      captured. THE WALL CLOCK IS PINNED to a moving test clock (utils.time_utils.datetime, exit_engine.datetime and
      exit_engine.now_et, as tests/check_decay_stop.py pins its own): the lander runs CHECKs at whatever time it is.

  C1  config: PARK_LATE_SHADOW on, PARK_LATE_FROM_ET (14, 30), PARK_LATE_ARM 0.50, PARK_LATE_X 0.20; OT_PARK_LATE_SHADOW=0
      / OT_PARK_LATE_FROM / OT_PARK_LATE_ARM / OT_PARK_LATE_X read from the environment (a fresh interpreter)
  B1  BYTE-FOR-BYTE: getsource sha256[:16] of _evaluate_park, _park_cf, _decay_read and _evaluate_route equal 0e4d240's;
      DECAY_STOP_EXEMPT is still ("RunawayContinuation", "PARK"); PARK_LOCK_ARM / FLOOR / DELTA_FLOOR / DELTA_FROM_ET /
      CLOSE_ET unchanged (0.60 / 0.20 / 0.30 / (11, 30) / (15, 45))
  D1  DECISION PARITY on the 10-30 SPX shape (entry 14.90, peak 92.20 at 14:55, fading to 62.65 at 15:45): every tick's
      (should_exit, exit_reason, pnl) is identical with the shadow ON and OFF; the only close is park_close_15:45_ET
      at 15:45; plus a lock path and a delta-floor path, also identical ON vs OFF
  S1  the 10-30 SPX shape: no reading before 14:30; armed from 14:30; the first tick at p <= 0.80 x peak_p trips
      (15:00:00, mark 76.70), would_exit True on that tick ONLY; later ticks say "tripped earlier"
  L1  the "[park-late shadow] ... WOULD EXIT" line is logged exactly once, with the time and the mark
  A1  arming: a best mark of +49.9% of entry does not arm (no trip on a full fade), +50% arms
  H1  half day (2026-11-27, 13:00 bell): the window opens 11:30 (11:29 no reading, 11:30 a reading)
  P1  restart: a fresh engine on a rehydrated record (max_premium_seen 92.20, mfe_premium None) at 15:05, mark 70.00:
      armed from the persisted peak and trips on its first look
  O1  PARK_LATE_SHADOW off: no reading, same decisions
  N1  not PARK: a Breakout gets no shadow reading (its decay reading still there)
  E1  a real PARK exit on the tripping tick (15:45 close) still fires with its own reason; the reading records
      existing_exit and would_exit
  M1  management._one on the PARK record: park_late_peak_p / park_late_p / park_late_armed on every tick from 14:30,
      none before; park_late_would_exit = 1.0 only on the tripping tick, its note "15:00:00 ET mark 76.70 ..."

Born red on 0e4d240 at C1, S1, L1, A1, H1, P1, E1 and M1 (B1, D1, O1 and N1 pass there: nothing is read, nothing changes).
Run:  python3 tests/check_park_late_shadow.py
"""
import datetime as D
import hashlib
import inspect
import logging
import os
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_s = tempfile.mkdtemp(prefix="check_park_late_shadow.")
for _k, _v in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "derived.db"), ("OT_RESTING_DB", "resting.db"),
               ("OT_FEED_DB", "feed.db"), ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"),
               ("OT_SIGNAL_JOURNAL_DIR", "sj"),
               ("OT_WAREHOUSE_STATE", "ws"), ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(_s, _v)
os.environ.setdefault("OT_INSTRUMENT", "SPX")
for _k in ("OT_PARK_LATE_SHADOW", "OT_PARK_LATE_FROM", "OT_PARK_LATE_ARM", "OT_PARK_LATE_X",
           "OT_DECAY_STOP", "OT_DECAY_STOP_X", "OT_DECAY_STOP_ARM", "OT_DECAY_STOP_EXEMPT"):
    os.environ.pop(_k, None)
ET = ZoneInfo("America/New_York")
CLOCK = {"t": D.datetime(2026, 10, 30, 11, 5, 0, tzinfo=ET)}
try:
    import utils.time_utils as _tu                              # noqa: E402
    _REAL_DT = _tu.datetime

    class _Pinned(_REAL_DT):
        @classmethod
        def now(cls, tz=None):
            t = CLOCK["t"]
            return t.astimezone(tz) if tz is not None else t.replace(tzinfo=None)
    _tu.datetime = _Pinned
    import config                                               # noqa: E402
    from execution import exit_engine as XE                     # noqa: E402
    import strategy.management as M                             # noqa: E402
    import strategy.plan as PL                                  # noqa: E402
except Exception as exc:                                        # noqa: BLE001
    print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
    sys.exit(2)

logging.disable(logging.NOTSET)
logging.getLogger().setLevel(logging.CRITICAL)
FAILED = []
XE.now_et = lambda: CLOCK["t"]
XE.is_hard_close_time = lambda *a, **k: False
XE.datetime = _Pinned            # _evaluate_park reads exit_engine's own `datetime` for its 11:30 / 15:45 clocks


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.lines = []

    def emit(self, r):
        self.lines.append(r.getMessage())


CAP = _Cap()
XE.logger.addHandler(CAP)
XE.logger.setLevel(logging.INFO)
XE.logger.propagate = False


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def at(h, m, s=0, day=(2026, 10, 30)):
    return D.datetime(day[0], day[1], day[2], h, m, s, tzinfo=ET)


def park(tid, **kw):
    r = {"trade_id": tid, "symbol": "SPX", "strategy": "PARK", "setup_type": "park_short", "direction": "short",
         "option_side": "put", "contracts": 3, "entry_premium": 14.90, "stop_premium": 0.0, "target_premium": 0.0,
         "underlying_entry": 7620.29, "underlying_stop": 0.0, "underlying_target": 0.0, "status": "open",
         "is_butterfly": 0, "is_condor_leg": 0, "trail_stop": 0.0, "entry_time": "2026-10-30T15:01:03+00:00",
         "strike": 7620.0, "current_delta": -0.90}
    r.update(kw)
    return r


# THE 10-30 SPX SHAPE (scratchpad parkgb/qp/2026-10-30_SPX.json, bot mfe 91.80): rises through the afternoon, peaks
# 92.20 near 14:55, fades to the 62.65 it was closed at 15:45.  (clock, mark)
SPX_1030 = [((11, 5), 15.6), ((11, 40), 26.0), ((12, 10), 30.4), ((12, 40), 22.55), ((13, 0), 39.6), ((13, 30), 44.8),
            ((14, 0), 58.15), ((14, 25), 82.6), ((14, 30), 84.0), ((14, 45), 88.0), ((14, 55), 92.2),
            ((14, 57, 30), 85.0), ((15, 0), 76.70), ((15, 10), 74.3), ((15, 30), 66.0), ((15, 40), 62.2),
            ((15, 45), 62.65)]


def run(r, path, eng=None, day=(2026, 10, 30)):
    eng = eng or XE.ExitEngine(paper_trading=True)
    out = []
    for hm, m in path:
        CLOCK["t"] = at(*hm, day=day) if len(hm) == 3 else at(hm[0], hm[1], day=day)
        r["current_premium"] = m
        r["mfe_premium"] = max(float(r.get("mfe_premium") or 0.0), m)   # _track_excursion's in-memory best
        d = eng.evaluate(r, m)
        rd = getattr(eng, "park_late_reading", lambda _t: None)(r["trade_id"])
        out.append(((bool(d.should_exit), str(d.exit_reason or ""), round(float(d.current_pnl_usd or 0), 6)), rd))
        if d.should_exit:
            break
    return out


def h16(fn):
    return hashlib.sha256(inspect.getsource(fn).encode()).hexdigest()[:16]


# ── C config ─────────────────────────────────────────────────────────────────────────────────────────
_env = dict(os.environ, OT_PARK_LATE_SHADOW="0", OT_PARK_LATE_FROM="15,0", OT_PARK_LATE_ARM="1.0", OT_PARK_LATE_X="0.25")
try:
    _o = subprocess.run([sys.executable, "-c", "import config as c; print(c.PARK_LATE_SHADOW, c.PARK_LATE_FROM_ET, "
                         "c.PARK_LATE_ARM, c.PARK_LATE_X)"], cwd=ROOT, env=_env, capture_output=True, text=True,
                        timeout=120).stdout.strip().splitlines()[-1:]
except Exception as exc:                                        # noqa: BLE001
    _o = [repr(exc)]
check("C1 config: on / (14, 30) / 0.50 / 0.20 by default; OT_PARK_LATE_SHADOW=0 / _FROM / _ARM / _X from the env",
      getattr(config, "PARK_LATE_SHADOW", None) is True and tuple(getattr(config, "PARK_LATE_FROM_ET", ())) == (14, 30)
      and getattr(config, "PARK_LATE_ARM", None) == 0.50 and getattr(config, "PARK_LATE_X", None) == 0.20
      and _o == ["False (15, 0) 1.0 0.25"], f"env -> {_o}")

# ── B byte-for-byte ──────────────────────────────────────────────────────────────────────────────────
PINNED = {"_evaluate_park": "11f87bb5bfe16b82", "_park_cf": "af8d04371db47fb8",
          "_decay_read": "e2379a457c018f91", "_evaluate_route": "ad64d87edd0b44fa"}       # 0e4d240; route: r67 (PARC arm removed)
got = {n: h16(getattr(XE.ExitEngine, n)) for n in PINNED}
check("B1 PARK's exits, the decay read and the route are byte-for-byte 0e4d240's; PARK stays decay-exempt; PARK knobs",
      got == PINNED and tuple(config.DECAY_STOP_EXEMPT) == ("RunawayContinuation", "PARK")
      and (config.PARK_LOCK_ARM, config.PARK_LOCK_FLOOR, config.PARK_DELTA_FLOOR) == (0.60, 0.20, 0.30)
      and tuple(config.PARK_DELTA_FROM_ET) == (11, 30) and tuple(config.PARK_CLOSE_ET) == (15, 45),
      f"{got}")


# ── D decision parity ────────────────────────────────────────────────────────────────────────────────
def with_shadow(on, fn):
    was = getattr(config, "PARK_LATE_SHADOW", None)
    config.PARK_LATE_SHADOW = on
    try:
        return fn()
    finally:
        if was is None:
            delattr(config, "PARK_LATE_SHADOW")
        else:
            config.PARK_LATE_SHADOW = was


LOCK = [((11, 5), 15.6), ((12, 0), 25.0), ((13, 0), 20.0), ((14, 40), 30.0), ((14, 50), 17.5)]      # armed 23.84, out 17.88
DELTA = [((11, 5), 15.6), ((14, 35), 20.0), ((14, 50), 19.0)]     # under the 23.84 lock arm; |delta| 0.25 at 14:50
d_on = [x for x, _ in with_shadow(True, lambda: run(park("d1"), SPX_1030))]
d_off = [x for x, _ in with_shadow(False, lambda: run(park("d1"), SPX_1030))]
l_on = [x for x, _ in with_shadow(True, lambda: run(park("d2"), LOCK))]
l_off = [x for x, _ in with_shadow(False, lambda: run(park("d2"), LOCK))]


def _dpath():
    r = park("d3")
    out = []
    eng = XE.ExitEngine(paper_trading=True)
    for i, (hm, m) in enumerate(DELTA):
        r["current_delta"] = -0.90 if i < 2 else -0.25
        out += run(r, [(hm, m)], eng=eng)
    return [x for x, _ in out]


x_on, x_off = with_shadow(True, _dpath), with_shadow(False, _dpath)
closes = [(i, x[1]) for i, x in enumerate(d_on) if x[0]]
check("D1 decisions identical ON vs OFF: 10-30 SPX closes only at 15:45 (park_close); lock and delta paths too",
      d_on == d_off and l_on == l_off and x_on == x_off and closes == [(len(SPX_1030) - 1, "park_close_15:45_ET")]
      and l_on[-1][1].startswith("park_lock") and x_on[-1][1].startswith("park_delta_floor"),
      f"closes {closes}; lock {l_on[-1][1]!r}; delta {x_on[-1][1]!r}")

# ── S the 10-30 SPX shape ────────────────────────────────────────────────────────────────────────────
CAP.lines.clear()
s1 = run(park("s1"), SPX_1030)
rds = [rd for _, rd in s1]
pre = [rd for (hm, _), rd in zip(SPX_1030, rds) if hm < (14, 30)]
post = [(hm, rd) for (hm, _), rd in zip(SPX_1030, rds) if hm >= (14, 30)]
wx = [hm for hm, rd in post if rd and rd.get("would_exit")]
trip = next((rd for hm, rd in post if rd and rd.get("would_exit")), None) or {}
after = [rd for hm, rd in post if hm > (15, 0)]
check("S1 10-30 SPX: no reading before 14:30, armed from 14:30, trips once at 15:00:00 mark 76.70 (p <= 0.8 x peak)",
      all(rd is None for rd in pre) and all(rd and rd["armed"] for _, rd in post) and wx == [(15, 0)]
      and trip.get("tripped_at") == "15:00:00" and abs(trip.get("mark", 0) - 76.70) < 1e-9
      and abs(trip.get("peak_p", 0) - (92.2 - 14.9)) < 1e-9 and abs(trip.get("level", 0) - 0.8 * (92.2 - 14.9)) < 1e-9
      and all(rd and rd["trips"] and not rd["would_exit"] and "tripped earlier at 15:00:00" in rd["note"]
              for rd in after),
      f"would_exit at {wx}; trip {trip.get('tripped_at')} {trip.get('mark')} {trip.get('note')}")
logged = [x for x in CAP.lines if x.startswith("[park-late shadow]")]
check("L1 one '[park-late shadow] ... WOULD EXIT' line, with the time and the mark",
      len(logged) == 1 and "WOULD EXIT at 15:00:00 ET" in logged[0] and "mark 76.70" in logged[0], f"{logged}")

# ── A arming ─────────────────────────────────────────────────────────────────────────────────────────
a_no = run(park("a1"), [((14, 30), 14.90 * 1.499), ((14, 40), 15.0), ((14, 50), 14.0)])
a_yes = run(park("a2"), [((14, 30), 14.90 * 1.50), ((14, 40), 15.0)])
check("A1 a best mark of +49.9% never arms (no trip on a full fade); +50% arms",
      all(rd and not rd["armed"] and not rd["trips"] for _, rd in a_no)
      and a_yes[0][1] and a_yes[0][1]["armed"] and a_yes[1][1]["would_exit"],
      f"{[(rd or {}).get('armed') for _, rd in a_no]} {[(rd or {}).get('armed') for _, rd in a_yes]}")

# ── H half day ───────────────────────────────────────────────────────────────────────────────────────
HD = (2026, 11, 27)
h1 = run(park("h1", entry_time="2026-11-27T16:01:03+00:00"), [((11, 29), 30.0), ((11, 30), 30.0)], day=HD)
check("H1 half day 2026-11-27 (13:00 bell): the window opens at 11:30 (close-anchored 14:30)",
      h1[0][1] is None and h1[1][1] is not None and h1[1][1].get("from") == "11:30",
      f"{[None if rd is None else rd.get('from') for _, rd in h1]}")

# ── P restart ────────────────────────────────────────────────────────────────────────────────────────
CLOCK["t"] = at(15, 5)
p_eng = XE.ExitEngine(paper_trading=True)
p_rec = park("p1", max_premium_seen=92.20, mfe_premium=None)
p_d = p_eng.evaluate(p_rec, 70.00)
p_rd = p_eng.park_late_reading("p1") if hasattr(p_eng, "park_late_reading") else None
check("P1 restart: the persisted max_premium_seen 92.20 arms a fresh engine, which trips on its first look",
      p_rd is not None and p_rd["armed"] and p_rd["would_exit"] and abs(p_rd["peak_p"] - 77.3) < 1e-9
      and not p_d.should_exit, f"{p_rd and p_rd.get('note')}")

# ── O off / N not PARK ───────────────────────────────────────────────────────────────────────────────
o1 = with_shadow(False, lambda: run(park("o1"), SPX_1030))
check("O1 PARK_LATE_SHADOW off: no reading on any tick, the same decisions",
      all(rd is None for _, rd in o1) and [x for x, _ in o1] == d_off, "")
CLOCK["t"] = at(15, 0)
n_eng = XE.ExitEngine(paper_trading=True)
n_rec = {"trade_id": "n1", "symbol": "QQQ", "strategy": "Breakout", "setup_type": "x", "direction": "long",
         "option_side": "call", "contracts": 10, "entry_premium": 2.00, "stop_premium": 1.50, "target_premium": 0.0,
         "trail_activation": 3.0, "underlying_entry": 720.0, "underlying_stop": 0.0, "underlying_target": 725.0,
         "status": "open", "is_butterfly": 0, "is_condor_leg": 0, "trail_stop": 0.0, "orb_range_high": 0.0,
         "orb_range_low": 0.0, "entry_time": "2026-10-30T13:40:04+00:00", "strike": 720.0, "mfe_premium": 3.2}
n_eng.evaluate(n_rec, 3.0)
check("N1 a Breakout gets no shadow reading (its decay reading is still kept)",
      getattr(n_eng, "park_late_reading", lambda _t: None)("n1") is None and n_eng.decay_reading("n1") is not None, "")

# ── E a real exit on the tripping tick ───────────────────────────────────────────────────────────────
e1 = run(park("e1"), [((14, 30), 84.0), ((14, 55), 92.2), ((15, 45), 62.65)])
(ex, erd) = e1[-1]
check("E1 the 15:45 close on the tripping tick fires with its own reason; the reading records it",
      ex[0] and ex[1] == "park_close_15:45_ET" and erd and erd["would_exit"] and erd["existing_exit"],
      f"{ex} {erd and erd.get('note')}")

# ── M management rows ────────────────────────────────────────────────────────────────────────────────
ROWS = []
_orig_write = PL.write_row


def _capture(store, symbol, ts, strategy, verdict, reason, direction="", trigger=None, invalidation=None,
             underlying=None, r=None, checks=None, check_notes=None):
    ROWS.append({"strategy": strategy, "verdict": verdict, "reason": reason, "checks": dict(checks or {}),
                 "notes": dict(check_notes or {})})
    return True


NAMES = ("park_late_peak_p", "park_late_p", "park_late_armed")
mrows = []
_eng = XE.ExitEngine(paper_trading=True)
_prev = getattr(XE, "_exit_engine", None)
XE._exit_engine = _eng
PL.write_row = _capture
try:
    m_rec = park("m1")
    for hm, m in SPX_1030[:-1]:
        CLOCK["t"] = at(*hm) if len(hm) == 3 else at(hm[0], hm[1])
        m_rec["current_premium"] = m
        m_rec["mfe_premium"] = max(float(m_rec.get("mfe_premium") or 0.0), m)
        _eng.evaluate(m_rec, m)
        ROWS.clear()
        M.get_management_plan()._one({"_open_records": [m_rec]}, m_rec, 7600.0)
        mine = [x for x in ROWS if x["strategy"] == "PARK/manage"]
        mrows.append((hm, mine[-1] if mine else None))
finally:
    XE._exit_engine = _prev
    PL.write_row = _orig_write
pre_m = [row for hm, row in mrows if hm < (14, 30)]
post_m = [(hm, row) for hm, row in mrows if hm >= (14, 30)]
wx_m = [hm for hm, row in post_m if row and "park_late_would_exit" in row["checks"]]
tr_m = next((row for hm, row in post_m if hm == (15, 0)), None) or {"checks": {}, "notes": {}}
check("M1 _one() on PARK: park_late_* rows every tick from 14:30 (none before); would_exit = 1.0 once, at 15:00 with "
      "its time and mark",
      all(row is not None and not any(n in row["checks"] for n in NAMES + ("park_late_would_exit",)) for row in pre_m)
      and all(row is not None and all(n in row["checks"] for n in NAMES) for _, row in post_m)
      and wx_m == [(15, 0)] and tr_m["checks"].get("park_late_would_exit", (None,))[0] == 1.0
      and tr_m["notes"].get("park_late_would_exit", "").startswith("15:00:00 ET mark 76.70")
      and abs(tr_m["checks"]["park_late_peak_p"][0] - 77.3) < 1e-9
      and all("park_late_would_exit" in M.MGMT_CHECKS and n in M.MGMT_CHECKS for n in NAMES),
      f"would_exit rows at {wx_m}; note {tr_m['notes'].get('park_late_would_exit')!r}")

print()
print("FAILED: " + ", ".join(FAILED) if FAILED else "ALL PASS")
sys.exit(1 if FAILED else 0)
