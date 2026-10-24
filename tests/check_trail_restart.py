#!/usr/bin/env python3
"""
tests/check_trail_restart.py  v1.0
v1.0  2026-10-18  OTV4TEST r294 (EXIT.6; MIRROR OF otv4 r493 1c60b69) — A RESTART KEEPS THE LOCKED TRAIL.

  Mainline's tests/check_trail_restart.py v1.0 (sha256 bc7a638f...) with ONE adaptation: T1's pins are THIS tree's
  measured sequences. Our _update_trail is not mainline's - the ratchet is r44's _gain_floor and a Breakout seeds the
  structure floor (exit_engine.py v4.43 :3147) - so mainline's Runaway numbers (1.04/1.25/1.52/1.92) do not transfer.
  Measured on 20e660f before the fix (tools: scratchpad measure.py), identical on the build:
    Runaway  (act 1.50): 1.10->0.0  1.30->1.15 1.55->1.275 1.90->1.45 2.40->1.70 1.95->1.70 1.70->EXIT orb_trail_stop
    Breakout (act 1.00): 1.10->0.825 1.30->1.15 1.55->1.275 1.90->1.45 2.40->1.80 1.95->1.80 1.70->EXIT trail_stop_hit
  Restart after the 2.40 tick on 20e660f: Runaway 1.70 -> 1.475 and HOLDS at 1.70; Breakout 1.80 -> 1.4625, HOLDS.

  _seed_trail_from_record restored the persisted trail_stop but re-armed _trail_active only for ADOPTED. For every
  other strategy the first tick at or above trail_activation took _update_trail's first-activation branch and wrote
  the activation seed over the recovered level. Found by the 2026-10-18 audit (A2; repro: entry 1.00, peak 2.00,
  trail 1.50, mark 1.45 -> continuous exits, a fresh engine HOLDS at 1.0875).

  Drives the REAL ExitEngine.evaluate (clock pinned off the hard close):
  T1  Runaway: the uninterrupted trail sequence is the pre-r294 one (pinned) and exits at 1.70
  T1b Breakout (structure floor): the uninterrupted sequence is the pre-r294 one (pinned), exits at 1.70
  T2  Runaway restart after the 2.40 tick (persisted 1.70, peak 2.40) exits at 1.70 as the uninterrupted engine does
  T2b Breakout restart (persisted 1.80, peak 2.40) exits at 1.70                                  (RED before)
  T3  the recovered level is never lowered by the first armed tick (1.95)                         (RED before)
  T4  the audit's repro (Breakout, peak 2.00, trail 1.50, mark 1.45) exits                        (RED before)
  T5  no peak on the row: a recovered level at/above the activation seed arms                     (RED before)
  T6  a PRE-activation level above the seed (1.30, peak 1.45 < 1.50) stays un-armed: the activation
      tick lands where the uninterrupted engine lands (its seed), not at 1.30 - kills arm-always
  T7  ADOPTED still re-arms (unchanged)

Run:  python3 tests/check_trail_restart.py   (exit 0 green, 1 red)
"""
import glob as _glob
import logging
import os
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
_SCR = tempfile.mkdtemp(prefix="chk_trail_restart_")
for _k, _v in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"), ("OT_LOG_FILE", "bot.log"),
               ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_RESTING_DB", "r.db"), ("OT_SIGNAL_JOURNAL_DIR", "sj")):
    os.environ.setdefault(_k, os.path.join(_SCR, _v))

FAILED = []

# the pre-r294 uninterrupted sequences, measured on 20e660f: (mark, trail, exit)
PINNED_RUNAWAY = [(1.10, 0.0, False), (1.30, 1.15, False), (1.55, 1.275, False),
                  (1.90, 1.45, False), (2.40, 1.70, False), (1.95, 1.70, False), (1.70, 1.70, True)]
PINNED_BREAKOUT = [(1.10, 0.825, False), (1.30, 1.15, False), (1.55, 1.275, False),
                   (1.90, 1.45, False), (2.40, 1.80, False), (1.95, 1.80, False), (1.70, 1.80, True)]


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def rec(tid, strategy="RunawayContinuation", act=1.50, **kw):
    r = {"trade_id": tid, "symbol": "QQQ", "strategy": strategy, "setup_type": "x",
         "direction": "long", "option_side": "call", "contracts": 10,
         "entry_premium": 1.00, "stop_premium": 0.80, "target_premium": 3.0,
         "trail_activation": act, "underlying_entry": 720.0, "underlying_stop": 0.0,
         "underlying_target": 725.0, "status": "open", "is_butterfly": 0,
         "is_condor_leg": 0, "trail_stop": 0.0, "orb_range_high": 0.0, "orb_range_low": 0.0}
    r.update(kw)
    return r


def brk(tid, **kw):
    return rec(tid, strategy="Breakout", act=1.00, **kw)


def main():
    logging.disable(logging.CRITICAL)
    import execution.exit_engine as XE
    from execution.exit_engine import ExitEngine
    XE.is_hard_close_time = lambda *a, **k: False

    def trail(e, tid):
        return round(float(e._trail_stops.get(tid, 0.0) or 0.0), 4)

    def run_seq(mk, pins, tid):
        e = ExitEngine(paper_trading=True)
        seq = []
        for px, _, _ in pins:
            d = e.evaluate(mk(tid), px)
            seq.append((px, trail(e, tid), bool(d.should_exit)))
        return seq

    seq = run_seq(lambda t: rec(t), PINNED_RUNAWAY, "u1")
    check("T1 Runaway: the uninterrupted trail sequence is the pre-r294 one", seq == PINNED_RUNAWAY, f"got {seq}")
    seqb = run_seq(lambda t: brk(t), PINNED_BREAKOUT, "u2")
    check("T1b Breakout (structure floor): the uninterrupted sequence is the pre-r294 one", seqb == PINNED_BREAKOUT,
          f"got {seqb}")

    # T2 / T2b / T3 — restart after the 2.40 tick: persisted = the uninterrupted trail at that tick, peak 2.40
    b = ExitEngine(paper_trading=True)
    r = rec("r1", trail_stop=1.70, mfe_premium=2.40, max_premium_seen=2.40)
    d1 = b.evaluate(dict(r), 1.95)
    t_after = trail(b, "r1")
    d2 = b.evaluate(dict(r), 1.70)
    check("T2 Runaway restart (persisted 1.70, peak 2.40) exits at 1.70 exactly as the uninterrupted engine does",
          (not d1.should_exit) and d2.should_exit and "orb_trail_stop" in (d2.exit_reason or ""),
          f"1.95 -> exit={d1.should_exit}; 1.70 -> exit={d2.should_exit} {d2.exit_reason!r} trail={trail(b, 'r1')}")
    bb = ExitEngine(paper_trading=True)
    rb = brk("r2", trail_stop=1.80, mfe_premium=2.40, max_premium_seen=2.40)
    e1 = bb.evaluate(dict(rb), 1.95)
    tb_after = trail(bb, "r2")
    e2 = bb.evaluate(dict(rb), 1.70)
    check("T2b Breakout restart (persisted 1.80, peak 2.40) exits at 1.70 as trail_stop_hit",
          (not e1.should_exit) and e2.should_exit and "trail_stop_hit" in (e2.exit_reason or ""),
          f"1.95 -> exit={e1.should_exit}; 1.70 -> exit={e2.should_exit} {e2.exit_reason!r} trail={trail(bb, 'r2')}")
    check("T3 the first armed tick after a restart keeps the recovered level (Runaway 1.70, Breakout 1.80)",
          t_after == 1.70 and tb_after == 1.80, f"Runaway {t_after} (pre-r294: 1.475), Breakout {tb_after} (pre-r294: 1.4625)")

    # T4 — the audit's repro
    c = ExitEngine(paper_trading=True)
    d = c.evaluate(brk("q1", trail_stop=1.50, mfe_premium=2.00, max_premium_seen=2.00), 1.45)
    check("T4 the audit's repro (Breakout, peak 2.00, trail 1.50, mark 1.45) exits",
          d.should_exit, f"exit={d.should_exit} trail={trail(c, 'q1')} (pre-r294: HOLD at 1.0875)")

    # T5 — no peak on the row, level at/above the activation seed (entry x 1.25)
    e5 = ExitEngine(paper_trading=True)
    d = e5.evaluate(brk("n1", trail_stop=1.50), 1.45)
    check("T5 no peak: a recovered 1.50 (>= seed 1.25) arms and exits at 1.45",
          d.should_exit, f"exit={d.should_exit} trail={trail(e5, 'n1')}")

    # T6 — a pre-activation level ABOVE the activation seed: Runaway restart with persisted 1.30 and peak 1.45
    # (< trail_activation 1.50). The uninterrupted engine arms at 1.50 and writes its activation seed over whatever
    # the earlier trail held (the code's current behaviour; mainline's EXIT.7 is the open ruling on that overwrite),
    # so the restart must land exactly there too - NOT keep 1.30. An arm-always seed keeps 1.30: this is the case
    # that separates "armed wherever the uninterrupted engine would be" from "armed always" on THIS tree, where
    # the Runaway seed (1.25) and the gain floor at 1.50 (1.25) coincide and mainline's 1.24-vs-1.25 case cannot.
    u = ExitEngine(paper_trading=True)
    for px in (1.10, 1.30, 1.50):
        u.evaluate(rec("w1"), px)
    t_unint = trail(u, "w1")
    f = ExitEngine(paper_trading=True)
    f.evaluate(rec("p1", trail_stop=1.30, mfe_premium=1.45, max_premium_seen=1.45), 1.50)
    t6 = trail(f, "p1")
    check("T6 a pre-activation level (1.30, peak 1.45 < 1.50) stays un-armed; the activation tick lands where the "
          "uninterrupted engine lands, not at 1.30",
          t6 == t_unint and t_unint > 0 and t6 != 1.30, f"restart {t6} vs uninterrupted {t_unint}")

    # T7 — ADOPTED unchanged
    g = ExitEngine(paper_trading=True)
    g._seed_trail_from_record(rec("a1", strategy="ADOPTED", trail_stop=1.10))
    check("T7 ADOPTED still re-arms its trail flag", g._trail_active.get("a1") is True,
          f"_trail_active={g._trail_active.get('a1')!r}")

    print()
    if FAILED:
        print(f"RED: {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        import shutil
        shutil.rmtree(_SCR, ignore_errors=True)
    sys.exit(rc)
