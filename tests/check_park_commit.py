#!/usr/bin/env python3
"""
tests/check_park_commit.py  v5.3
v5.3  2026-11-08  OTV5 r93 (C8.1) — I1 holds PARK's new C8 condition met (its index fixture ramps above its first hour);
      I1 is about the commitment gate. C8 itself, on indexes and equities, is tests/check_park_c8.py.
v5.2  2026-11-03  OTV5 r72 (PARK.5) — THE TAPE IS WATCHED, PAGED AND RE-PULLED BEFORE 11:01, AND THE PAIR IS ON THE MANIFOLD.
      The operator, 2026-11-03: "Fine, but we need to be more responsive when that happens to mitigate impacts to
      trading"; "Add it to the manifold & the plan should warn if there's a problem." T1-T6 (park_plan v5.5 tape_gaps /
      watch_tape / the starved and failed-closed pages; candle_feed v5.8 _maybe_refill_commit_tape), H1-H5
      (tools/manifold_health v5.1, the pair row). Mutation-tested: tape_gaps returning [] -> red at T1 T2 T4 T5 T6; the
      page dedupe removed -> red at T2 T3; the refill cadence and cap removed -> red at T4 T6; the pair bulb always GREEN
      -> red at H2 H3; no pair row when the store holds none -> red at H3 H4.
  T1  tape_gaps judges only minutes that should have closed: complete -> none; 5 missing since 09:30 -> a gap; 2 missing
      -> none (PARK_TAPE_GAP_BARS 3); no 09:30 bar; the 10:30 bar demanded only once it has closed; 2 prior sessions
  T2  prepare() at 10:15 on CVX with QQQ 5 minutes short pages ONCE (a second tick does not), naming the pair; a clean
      tape and an index box page nothing; the watch writes no condition
  T3  at 11:01 a starved gate pages once ("too thin"), at 11:03 FAILED CLOSED pages once; a tape that recovers at 11:02
      fires (ready) and the window's end pages nothing more
  T4  the feed re-pulls QQQ's short 1m from today's 09:30 on its own streamer (unsubscribe, subscribe 1m RTH) and not the
      clean CVX tape; a pull a minute later is held by the cadence; the forced pull at 11:00:30 goes anyway
  T5  a short PRIOR session re-pulls the own tape PRIME-deep (>= 30 days back); a clean tape pulls nothing; before 10:00
      nothing
  T6  at most PARK_TAPE_REFILL_MAX pulls a day per symbol; an index box (SPX) never pulls
  H1  an equity box: QQQ/1m is a PAIR row (not foreign), GREEN when fresh; QQQ/5m stays foreign; candles rollup GREEN
  H2  QQQ/1m older than PARK_PAIR_STALE_S at 10:00 is RED, rollup RED
  H3  no QQQ in the store: a QQQ/1m row is written (rows 0), RED, rollup RED
  H4  at 09:25 the pair row is GREY; at 09:31:10 yesterday's last bar is not yet stale (GREEN)
  H5  the QQQ and SPX boxes carry no pair row
v5.1  2026-11-03  OTV5 r72 (PARK.5) — P1: warehouse/s3_push v5.7 pushes no candles when the box cannot read its own symbol
      (QQQ's gate tape must never be filed from an equity box).
v5.0  2026-11-03  OTV5 r72 (PARK.5) — new. ON AN EQUITY, PARK ALSO NEEDS THE MARKET'S COMMITMENT; AN INDEX NEVER ASKS. The
      operator, 2026-11-03: "Let's modify the park trade on equities using the new filters — add a gate in the code 'is an
      index=false' and start trading it Monday." strategy/park_plan v5.4 (is_index, session_bars, tape_short, read_name,
      leans, commitment_gate, commitment_read), strategy/park v5.2 (pair_agrees, commitment), config v5.11 (PARK_INDEXES,
      PARK_PAIR_SYMBOL, PARK_COMMIT_*), data/candle_feed v5.7 (_park_pair_symbol; the QQQ 1m route on equity boxes).
  U1  the RANGE lean: a long whose 09:30 open is above the prior session's high is not against, at or below it is; a
      short mirrors it on the prior low
  U2  the REJECT lean: the 10:00-10:59 bar's wick against the move >= 0.50 of its range is against, below is not; a
      long reads the upper wick, a short the lower
  U3  the PART lean: 09:30-10:59 volume below the prior 5 sessions' median is against, at or above is not; a ratio above
      3 or below 1/3 is UNKNOWN (None), never against
  U4  the PAIR: QQQ's own first hour moved >= PARK_MOVE_PCT the SAME way agrees; the other way, or less, does not
  U5  the COMMITMENT: 2 against on the name skips, 2 against on QQQ skips, 1 and 1 passes; passes needs the pair too
  L1  NO LOOK-AHEAD: rewriting every bar from 11:00 to 15:59 today on both names (prices x3, volume x10) changes nothing
      the gate returns
  C1  FAILS CLOSED, no QQQ in the store: the plan STARVES (commit_tape), no signal, and a WARNING names it
  C2  FAILS CLOSED, QQQ's 10:59 bar missing: STARVED, no signal
  C3  FAILS CLOSED, only 2 prior sessions hold the first 90 minutes: STARVED, no signal
  C4  FAILS CLOSED, the name's own 10:00 hour from 40 bars: STARVED, no signal
  E1  an equity (CVX) on a committed tape fires: the signal is built, conditions pair_agrees and commitment are met, and
      the plan row carries is_index, pair_move_pct and every lean check on both names
  E2  QQQ moved the other way: refused at pair_agrees, no signal
  E3  two leans against on the name (open inside yesterday's range, a 10:00 rejection wick): refused at commitment
  I1  AN INDEX IS UNTOUCHED: on QQQ and on SPX the gate is never called (commitment_read replaced by a raiser), no new
      check row or condition is written, and the signal is the one v5.3 built
  F1  the candle feed on an equity box routes ONE extra subscription (QQQ, 1m, RTH) to store symbol QQQ
  F2  the QQQ box and the SPX box add nothing (their routes are v5.6's)
  F3  the route guard accepts the equity box's table (no duplicate key, no shared target)
  F4  _park_pair_symbol is "" for an index, for the pair itself and when the dx symbol is the pair
  R1  THE STUDY, REPLAYED THROUGH THE STORE: the fixture tests/fixtures/park_commit_replay.json (14 fires sampled from
      the study's 197 real-quote equity fires 08-25..11-02, every outcome class: kept long/short, pair disagrees, 2
      against on the name, 2 against on QQQ) is written to a feed store; session_bars -> commitment_gate gives the
      study's kept/skipped flag on every one. (The full 197 were replayed against this tree outside the suite: 27 kept
      +$13,596, 170 skipped -$11,668, 0 mismatches, 0 fail-closed - the study's split exactly.)
  P1  warehouse/s3_push.push_candles with own symbol "" pushes nothing (no put), prints CANDLES SKIPPED and counts one
      failure; with own symbol CVX on a store holding CVX and QQQ it pushes CVX only - QQQ's rows never leave the box
Born red on 358d8c8 (r70's build, no gate): the run stops at import - park_plan has no commitment_gate - exit 1.
Mutation-tested: PARK_COMMIT_SKIP 3 -> red at U5, E3, R1; PARK_PAIR_SYMBOL "SPY" -> red at C3, E1, E2, E3, F1, F4; the
fail-closed check removed (tape_short returning []) -> red at C1..C4.
Run:  python3 tests/check_park_commit.py
"""
import json
import logging
import os
import sqlite3
import sys
import tempfile
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TD = tempfile.mkdtemp(prefix="check_park_commit.")
for _k, _v in (("OT_TRADES_DB", "t.db"), ("OT_DERIVED_DB", "d.db"), ("OT_FEED_DB", "f.db"),
               ("OT_COUNTERFACTUAL_DIR", "cf"), ("OT_LOG_FILE", "bot.log"), ("OT_SIGNAL_JOURNAL_DIR", "sj"),
               ("OT_PLAN_STATES_FILE", "ps.json")):
    os.environ[_k] = os.path.join(_TD, _v)
os.environ.pop("OT_PARK", None)
os.environ.pop("OT_DXFEED_SYMBOL", None)
os.environ["OT_INSTRUMENT"] = "CVX"
ET = ZoneInfo("America/New_York")
DAY = date(2026, 10, 30)
FEED = os.environ["OT_FEED_DB"]
FAILED = []

try:
    import pandas  # noqa: F401,E402
    import config                                               # noqa: E402
    from strategy.park import Park                              # noqa: E402
    from strategy import park_plan as PP                        # noqa: E402
    import data.candle_feed as CF                               # noqa: E402
except Exception as exc:                                        # noqa: BLE001
    print(f"NOT RUN - imports unavailable under {sys.executable}: {type(exc).__name__}: {exc}")
    sys.exit(2)
if not hasattr(PP, "commitment_gate"):
    print("NOT RUN - strategy/park_plan has no commitment_gate (pre-r72 tree)")
    sys.exit(1)


N_CHECKS = 31


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name.split()[0])


def hm(i):
    return "%02d:%02d" % (9 + (30 + i) // 60, (30 + i) % 60)


def prev_days(d, n):
    out, x = [], d
    while len(out) < n:
        x -= timedelta(days=1)
        if x.weekday() < 5:
            out.append(x)
    return out


def session(o, c1030, c1100, vol=2000.0, hour=None):
    """A full RTH 1m session (390 bars) as {"HH:MM": (o, h, l, c, v)}: linear 09:30 open -> 10:30 close -> 11:00 close,
    flat after. `hour` overrides 10:00-10:59 bars ({"HH:MM": (o, h, l, c)})."""
    px = []
    for i in range(390):
        if i <= 60:
            p = o + (c1030 - o) * i / 60.0
        elif i <= 90:
            p = c1030 + (c1100 - c1030) * (i - 60) / 30.0
        else:
            p = c1100
        px.append(p)
    out = {}
    for i in range(390):
        a = px[i - 1] if i else o
        b = px[i]
        out[hm(i)] = (a, max(a, b) + 0.01, min(a, b) - 0.01, b, vol)
    out["09:30"] = (o, max(o, px[0]) + 0.01, min(o, px[0]) - 0.01, px[0], vol)
    for k, v in (hour or {}).items():
        out[k] = (v[0], v[1], v[2], v[3], vol)
    return out


def flat(level, hi, lo, vol=1000.0):
    """A prior session: every bar at `level`, one bar touching `hi`, one `lo`, the last close `level`."""
    out = {hm(i): (level, level + 0.01, level - 0.01, level, vol) for i in range(390)}
    out["12:00"] = (level, hi, level - 0.01, level, vol)
    out["13:00"] = (level, level + 0.01, lo, level, vol)
    return out


def sess_dict(today, prior):
    return {"today": today, "prior": prior}


# ── the canonical committed tape: CVX long (+0.641%), QQQ long (+0.30%) ──
def cvx_ok(**kw):
    t = session(234.07, 235.57, 235.33, vol=kw.get("vol", 2000.0), hour=kw.get("hour"))
    pr = [flat(231.45, kw.get("ph", 232.0), 230.5)] + [flat(231.0, 232.0, 230.0) for _ in range(5)]
    return sess_dict(t, pr)


def qqq_ok(**kw):
    t = session(700.0, kw.get("c1030", 702.1), 702.0, vol=kw.get("vol", 50000.0))
    pr = [flat(699.0, 699.5, 697.0, 30000.0)] + [flat(698.0, 699.0, 697.0, 30000.0) for _ in range(5)]
    return sess_dict(t, pr)


def _ms(d, h, m):
    return int(datetime(d.year, d.month, d.day, h, m, tzinfo=ET).timestamp() * 1000)


def write_store(sessions, day=DAY):
    """sessions: {symbol: sess_dict} -> the feed store at OT_FEED_DB (replaced)."""
    if os.path.exists(FEED):
        os.remove(FEED)
    c = sqlite3.connect(FEED)
    c.execute("CREATE TABLE IF NOT EXISTS candles (symbol TEXT NOT NULL, interval TEXT NOT NULL, "
              "ts_epoch_ms INTEGER NOT NULL, open REAL, high REAL, low REAL, close REAL, volume REAL, "
              "PRIMARY KEY (symbol, interval, ts_epoch_ms))")
    rows = []
    for sym, s in sessions.items():
        days = [(day, s["today"])] + list(zip(prev_days(day, len(s["prior"])), s["prior"]))
        for d, bars in days:
            for k, (o, h, l, cl, v) in bars.items():
                rows.append((sym, "1m", _ms(d, int(k[:2]), int(k[3:])), o, h, l, cl, v))
    c.executemany("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)", rows)
    c.commit()
    c.close()


class K:
    def __init__(self, sym, strike, bid, ask, delta, side):
        self.strike, self.bid, self.ask, self.delta = float(strike), bid, ask, delta
        self.mark, self.expiry, self.option_type = (bid + ask) / 2, str(DAY), side
        self.symbol = f"{sym:<6}{DAY:%y%m%d}{side}{int(strike * 1000):08d}"
        self.streamer_symbol = f".{sym}{DAY:%y%m%d}{side}{strike:g}"


class Chain:
    def __init__(self, sym, spot):
        base = round(spot)
        self.calls = [K(sym, base + d, 1.0, 1.2, 0.5, "C") for d in (-1, 0, 1)]
        self.puts = [K(sym, base + d, 1.0, 1.2, -0.5, "P") for d in (-1, 0, 1)]
        self.expiry = str(DAY)


def run(P, sym, px):
    prep = P.prepare(price_now=px, now_et="11:01", chain=Chain(sym, px), prior_close=None, day=DAY, symbol=sym)
    sig = P.generate_signal(price_now=px, now_et="11:01", chain=Chain(sym, px), prior_close=None, day=DAY, symbol=sym)
    return prep, sig


NEW_CHECKS = ("is_index", "pair_move_pct", "lean_range", "lean_reject", "lean_part", "against",
              "pair_lean_range", "pair_lean_reject", "pair_lean_part", "pair_against")


def main():
    print("check_park_commit")
    config.PARK_MODE = "trade"
    G = PP.commitment_gate

    # ── U: the pure read ──
    r = PP.read_name(*cvx_ok().values())
    lv = PP.leans(r, cvx_ok()["today"], cvx_ok()["prior"], "long")
    s_in = cvx_ok(ph=234.5)
    lv_in = PP.leans(PP.read_name(*s_in.values()), s_in["today"], s_in["prior"], "long")
    s_eq = cvx_ok(ph=234.07)
    lv_eq = PP.leans(PP.read_name(*s_eq.values()), s_eq["today"], s_eq["prior"], "long")
    sh = sess_dict(session(234.07, 233.0, 233.2), [flat(235.0, 236.0, 234.5)] + [flat(235.0, 236, 234) for _ in range(5)])
    lv_s = PP.leans(PP.read_name(*sh.values()), sh["today"], sh["prior"], "short")
    sh2 = sess_dict(session(234.07, 233.0, 233.2), [flat(235.0, 236.0, 233.5)] + [flat(235.0, 236, 234) for _ in range(5)])
    lv_s2 = PP.leans(PP.read_name(*sh2.values()), sh2["today"], sh2["prior"], "short")
    check("U1 RANGE: long open above the prior high not against, inside / equal against; short on the prior low",
          lv["range"] is False and lv_in["range"] is True and lv_eq["range"] is True
          and lv_s["range"] is False and lv_s2["range"] is True,
          f"{lv['range']} {lv_in['range']} {lv_eq['range']} {lv_s['range']} {lv_s2['range']}")

    wick_hour = {hm(30 + i): (235.0, 235.05, 234.95, 235.0) for i in range(60)}
    wick_hour["10:00"] = (235.0, 235.05, 234.95, 235.0)
    wick_hour["10:20"] = (235.0, 236.0, 234.95, 235.0)                 # high 236 -> upper wick 1.0 of range 1.05
    s_w = cvx_ok(hour=wick_hour)
    lv_w = PP.leans(PP.read_name(*s_w.values()), s_w["today"], s_w["prior"], "long")
    lv_ws = PP.leans(PP.read_name(*s_w.values()), s_w["today"], s_w["prior"], "short")
    check("U2 REJECT: a long's upper wick >= 0.50 of the hour's range is against; a short reads the lower wick",
          lv["reject"] is False and lv_w["reject"] is True and lv_ws["reject"] is False
          and abs(lv_w["wick"] - 1.0 / 1.05) < 1e-6, f"{lv['reject']} {lv_w['reject']} {lv_ws['reject']} {lv_w['wick']}")

    def part_for(vol_today):
        s = cvx_ok(vol=vol_today)
        return PP.leans(PP.read_name(*s.values()), s["today"], s["prior"], "long")
    p_hi, p_lo, p_eq, p_big, p_tiny = part_for(2000.0), part_for(900.0), part_for(1000.0), part_for(3100.0), part_for(300.0)
    check("U3 PART: below the prior median against, at / above not; > 3x or < 1/3x UNKNOWN (None), never against",
          p_hi["part"] is False and p_lo["part"] is True and p_eq["part"] is False and p_big["part"] is None
          and p_tiny["part"] is None and abs(p_hi["part_ratio"] - 2.0) < 1e-9,
          f"{p_hi['part']} {p_lo['part']} {p_eq['part']} {p_big['part']} {p_tiny['part']} {p_hi['part_ratio']}")

    g_ok = G(cvx_ok(), qqq_ok(), "long")
    g_dn = G(cvx_ok(), qqq_ok(c1030=698.0), "long")
    g_small = G(cvx_ok(), qqq_ok(c1030=701.0), "long")                 # +0.143% < 0.20%
    g_short = G(cvx_ok(), qqq_ok(c1030=698.0), "short")
    check("U4 PAIR: QQQ >= 0.20% the same way agrees; the other way or less does not",
          g_ok["pair_agrees"] and not g_dn["pair_agrees"] and not g_small["pair_agrees"] and g_short["pair_agrees"],
          f"{g_ok['pair_agrees']} {g_dn['pair_agrees']} {g_small['pair_agrees']} {g_short['pair_agrees']}")

    n2 = G(cvx_ok(ph=234.5, hour=wick_hour), qqq_ok(), "long")         # range + reject against on the name
    q = qqq_ok(vol=20000.0)                                            # part against on QQQ
    q["prior"][0] = flat(699.0, 701.0, 697.0, 30000.0)                 # range against on QQQ
    p2 = G(cvx_ok(), q, "long")
    one_one = G(cvx_ok(ph=234.5), qqq_ok(vol=20000.0), "long")
    check("U5 COMMITMENT: 2 against on the name skips, 2 on QQQ skips, 1 and 1 passes; passes needs the pair",
          g_ok["passes"] and n2["against"] == 2 and not n2["commitment"] and p2["pair_against"] == 2
          and not p2["commitment"] and one_one["against"] == 1 and one_one["pair_against"] == 1
          and one_one["commitment"] and one_one["passes"] and not g_dn["passes"] and g_dn["commitment"],
          f"ok={g_ok['passes']} n2={n2['against']} p2={p2['pair_against']} 1/1={one_one['passes']} dn={g_dn['passes']}")

    # ── L: no look-ahead ──
    def future_rewritten(s):
        t = dict(s["today"])
        for k in list(t):
            if k >= "11:00":
                o, h, l, c, v = t[k]
                t[k] = (o * 3, h * 3, l * 3, c * 3, v * 10)
        return sess_dict(t, s["prior"])
    base = G(cvx_ok(), qqq_ok(), "long")
    fut = G(future_rewritten(cvx_ok()), future_rewritten(qqq_ok()), "long")
    check("L1 NO LOOK-AHEAD: rewriting 11:00-15:59 today on both names changes nothing the gate returns",
          json.dumps(base, sort_keys=True, default=str) == json.dumps(fut, sort_keys=True, default=str))

    # ── C / E / I: through the plan and the store ──
    lines = []

    class _Grab(logging.Handler):
        def emit(self, rec):
            lines.append((rec.levelname, rec.getMessage()))
    logging.getLogger("strategy.park_plan").addHandler(_Grab())
    logging.getLogger("strategy.park_plan").setLevel(logging.INFO)
    P = Park()

    write_store({"CVX": cvx_ok()})
    prep, sig = run(P, "CVX", 235.33)
    check("C1 FAILS CLOSED, no QQQ in the store: STARVED, no signal, a WARNING names it",
          sig is None and not prep.ready and any(lv_ == "WARNING" and "STARVED" in m and "CVX" in m for lv_, m in lines),
          f"ready={prep.ready} sig={sig is not None} notes={prep.tick.notes[-1:]}")

    q = qqq_ok()
    del q["today"]["10:59"]
    write_store({"CVX": cvx_ok(), "QQQ": q})
    prep, sig = run(P, "CVX", 235.33)
    check("C2 FAILS CLOSED, QQQ's 10:59 bar missing: STARVED, no signal",
          sig is None and not prep.ready and any("pair: no 10:59 bar" in n for n in prep.tick.notes),
          f"{prep.tick.notes[-1:]}")

    c3n, c3q = cvx_ok(), qqq_ok()
    c3q["prior"] = c3q["prior"][:2]
    write_store({"CVX": c3n, "QQQ": c3q})
    prep, sig = run(P, "CVX", 235.33)
    check("C3 FAILS CLOSED, 2 prior sessions hold the first 90 minutes: STARVED, no signal",
          sig is None and not prep.ready and any("2 prior sessions" in n for n in prep.tick.notes),
          f"{prep.tick.notes[-1:]}")

    c4 = cvx_ok()
    for i in range(20):
        c4["today"].pop(hm(40 + i), None)                              # 10:10-10:29 gone: the hour from 40 bars
    write_store({"CVX": c4, "QQQ": qqq_ok()})
    prep, sig = run(P, "CVX", 235.33)
    check("C4 FAILS CLOSED, the name's 10:00 hour from 40 bars: STARVED, no signal",
          sig is None and not prep.ready and any("name: hour bar from 40" in n for n in prep.tick.notes),
          f"{prep.tick.notes[-1:]}")

    write_store({"CVX": cvx_ok(), "QQQ": qqq_ok()})
    prep, sig = run(P, "CVX", 235.33)
    ck = prep.tick.checks
    check("E1 a committed equity fires: signal built, pair_agrees + commitment met, every new check row written",
          sig is not None and prep.ready and prep.conditions.get("pair_agrees", (0, 0, False))[2]
          and prep.conditions.get("commitment", (0, 0, False))[2] and all(n in ck for n in NEW_CHECKS),
          f"sig={sig is not None} conds={ {k: v[2] for k, v in prep.conditions.items()} } missing="
          f"{[n for n in NEW_CHECKS if n not in ck]}")

    write_store({"CVX": cvx_ok(), "QQQ": qqq_ok(c1030=698.0)})
    prep, sig = run(P, "CVX", 235.33)
    check("E2 QQQ moved the other way: refused at pair_agrees, no signal",
          sig is None and "pair_agrees" in prep.unmet, f"unmet={prep.unmet}")

    write_store({"CVX": cvx_ok(ph=234.5, hour=wick_hour), "QQQ": qqq_ok()})
    prep, sig = run(P, "CVX", 235.33)
    check("E3 two leans against on the name: refused at commitment, no signal",
          sig is None and prep.unmet == ["commitment"], f"unmet={prep.unmet}")

    # I1 - an index never asks
    _real = PP.commitment_read

    def _boom(*a, **k):
        raise AssertionError("commitment_read called on an index")
    ok_i, det = True, []
    for sym, o, c1030, c1100, pc in (("QQQ", 700.0, 702.1, 702.4, 699.0), ("SPX", 6000.0, 6015.0, 6018.0, 5990.0)):
        write_store({sym: sess_dict(session(o, c1030, c1100), [flat(pc, pc + 1, pc - 5)] + [flat(pc, pc + 1, pc - 5)] * 5)})
        PP.commitment_read = _boom
        # r93 (C8.1): this fixture's ramp ends above its first hour, so C8 would skip it; I1 is about the commitment
        # gate, so C8 is held met here (tests/check_park_c8.py owns C8, on indexes too)
        _c8 = PP.c8_read
        PP.c8_read = lambda t, cond, **k: cond("c8_first_hour_extended", None, True)
        try:
            prep, sig = run(P, sym, c1100)
        except AssertionError as exc:
            prep, sig = None, None
            det.append(str(exc))
        finally:
            PP.commitment_read = _real
            PP.c8_read = _c8
        good = (prep is not None and sig is not None and not any(n in prep.tick.checks for n in NEW_CHECKS)
                and "pair_agrees" not in prep.conditions and "commitment" not in prep.conditions)
        ok_i &= good
        det.append(f"{sym}: sig={sig is not None}")
    check("I1 AN INDEX IS UNTOUCHED: QQQ and SPX never call the gate, write no new row, and fire as v5.3",
          ok_i, "; ".join(det))

    # ── F: the candle feed ──
    def feed_for(instr, dx=""):
        CF.INSTRUMENT = instr
        if dx:
            os.environ["OT_DXFEED_SYMBOL"] = dx
        else:
            os.environ.pop("OT_DXFEED_SYMBOL", None)
        try:
            return CF.CandleFeed(CF.FeedStore(os.path.join(_TD, f"feed_{instr}.db")))
        finally:
            os.environ.pop("OT_DXFEED_SYMBOL", None)
    _instr = CF.INSTRUMENT
    try:
        f_eq = feed_for("CVX")
        f_q, f_s = feed_for("QQQ"), feed_for("SPX")
        extra = [s for s in f_eq.subs if s[0] == "QQQ"]
        check("F1 an equity box routes ONE extra subscription (QQQ, 1m, RTH) to store symbol QQQ",
              len(extra) == 1 and extra[0][1] == "1m" and extra[0][3] is False
              and f_eq.symbol_map.get(("QQQ", "1m", False)) == "QQQ", f"{[(s[0], s[1], s[3]) for s in extra]}")
        check("F2 the QQQ and SPX boxes add nothing (the pair route is absent; their subscription counts match)",
              not [s for s in f_s.subs if s[0] == "QQQ"] and len(f_q.subs) == len(f_s.subs)
              and len(f_eq.subs) == len(f_q.subs) + 1, f"eq {len(f_eq.subs)} qqq {len(f_q.subs)} spx {len(f_s.subs)}")
        check("F3 the route guard accepts the equity box's table (CandleFeed constructed)", f_eq is not None)
        CF.INSTRUMENT = "SPX"
        a = CF._park_pair_symbol()
        CF.INSTRUMENT = "QQQ"
        b = CF._park_pair_symbol()
        CF.INSTRUMENT = "AMD"
        os.environ["OT_DXFEED_SYMBOL"] = "QQQ"
        c_ = CF._park_pair_symbol()
        os.environ.pop("OT_DXFEED_SYMBOL", None)
        d_ = CF._park_pair_symbol()
        check("F4 _park_pair_symbol: '' for an index, for the pair itself, for a pair dx symbol; QQQ for an equity",
              (a, b, c_, d_) == ("", "", "", "QQQ"), f"{(a, b, c_, d_)}")
    finally:
        CF.INSTRUMENT = _instr

    # ── R: the study, replayed through the store ──
    fx = json.load(open(os.path.join(ROOT, "tests", "fixtures", "park_commit_replay.json")))

    def rebuild(p):
        """The fixture's compact session -> a full RTH session holding exactly what the gate reads."""
        t = {}
        o = p["open_0930"]
        v_each = p["vol90"] / 90.0
        for i in range(390):
            t[hm(i)] = (o, o, o, o, v_each if i < 90 else 1.0)
        for k, (bo, bh, bl, bc) in p["hour"].items():
            t[k] = (bo, bh, bl, bc, v_each)
        pr0 = {hm(i): (p["prior_high"], p["prior_high"], p["prior_low"], p["prior_low"], 1.0) for i in range(390)}
        priors = []
        for j, pv in enumerate(p["prior_vol90"]):
            s = dict(pr0) if j == 0 else {hm(i): (o, o, o, o, 1.0) for i in range(390)}
            for i in range(90):
                b = s[hm(i)]
                s[hm(i)] = (b[0], b[1], b[2], b[3], pv / 90.0)
            priors.append(s)
        return sess_dict(t, priors)
    bad = []
    for f in fx["fires"]:
        d = date.fromisoformat(f["day"])
        write_store({f["sym"]: rebuild(fx["sessions"][f["day"] + "|" + f["sym"]]),
                     "QQQ": rebuild(fx["sessions"][f["day"] + "|QQQ"])}, day=d)
        ns, ps = PP.session_bars(f["sym"], d), PP.session_bars("QQQ", d)
        g = PP.commitment_gate(ns, ps, f["dirn"])
        if g["passes"] != f["study_b2"] or g["short"]:
            bad.append((f["day"], f["sym"], f["case"], g["passes"], f["study_b2"], g["short"]))
    cases = sorted({f["case"] for f in fx["fires"]})
    check(f"R1 the study replayed through the store: {len(fx['fires'])} fires, cases {cases}, every kept/skipped flag "
          f"matches", not bad and len(fx["fires"]) >= 12, f"mismatches {bad}")

    # ── P1: a box that cannot read its own symbol pushes no candles (warehouse/s3_push.py v5.7) ──────────────────
    import contextlib
    import io
    import warehouse.s3_push as SP
    pdb = os.path.join(_TD, "push_store.db")
    pc = sqlite3.connect(pdb)
    pc.execute("CREATE TABLE IF NOT EXISTS candles (symbol TEXT, interval TEXT, ts_epoch_ms INTEGER, open REAL, "
               "high REAL, low REAL, close REAL, volume REAL)")
    t0 = int((datetime.now(ZoneInfo("UTC")) - timedelta(days=1)).timestamp() * 1000) // 60000 * 60000
    for sym in ("CVX", "QQQ"):
        for k in range(3):
            pc.execute("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)", (sym, "1m", t0 + k * 60000, 1, 1, 1, 1, 10))
    pc.commit()
    pc.close()
    puts = []
    saved_put = SP.put_and_verify
    try:
        SP.put_and_verify = lambda s3, bucket, key, body, counters=None: puts.append(key) or True
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            r_none = SP.push_candles(None, "bkt", pdb, {}, "")
        none_puts, none_out = list(puts), out.getvalue()
        puts.clear()
        r_cvx = SP.push_candles(None, "bkt", pdb, {}, "CVX")
        cvx_puts = list(puts)
    finally:
        SP.put_and_verify = saved_put
    check("P1 s3_push: own symbol unknown -> no candle is pushed (no put), one CANDLES SKIPPED line, one failure "
          "counted; own symbol CVX -> CVX's bars only, QQQ's gate tape never pushed",
          r_none == (0, 1) and not none_puts and "CANDLES SKIPPED" in none_out
          and r_cvx[0] == 1 and cvx_puts and all("/sym=CVX/" in k for k in cvx_puts)
          and not any("/sym=QQQ/" in k for k in cvx_puts),
          f"none={r_none} puts={none_puts} out={none_out[:80]!r} cvx={r_cvx} keys={cvx_puts}")

    # ── T: the tape is watched, paged and re-pulled before 11:01 (park_plan v5.5, candle_feed v5.8) ──────────────
    import asyncio
    import types
    T_DAY = DAY

    def drop(sd, keys):
        t = dict(sd["today"])
        for k in keys:
            t.pop(k, None)
        return sess_dict(t, sd["prior"])
    full = cvx_ok()
    g_ok = PP.tape_gaps(full, (10, 15))
    g5 = PP.tape_gaps(drop(full, ["10:%02d" % i for i in range(5, 10)]), (10, 15))
    g2 = PP.tape_gaps(drop(full, ["10:05", "10:06"]), (10, 15))
    g930 = PP.tape_gaps(drop(full, ["09:30"]), (10, 15))
    g1030_early = PP.tape_gaps(drop(full, ["10:30"]), (10, 20))
    g1030 = PP.tape_gaps(drop(full, ["10:30"]), (10, 40))
    gpr = PP.tape_gaps(sess_dict(full["today"], full["prior"][:2]), (10, 15))
    check("T1 tape_gaps judges only what should exist by the last closed minute: complete -> none; 5 missing -> a gap; "
          "2 missing -> none (under PARK_TAPE_GAP_BARS); no 09:30 bar; the 10:30 bar demanded only once closed; "
          "2 prior sessions -> short",
          g_ok == [] and any("5 of 46 minutes missing" in x for x in g5) and g2 == []
          and any("no 09:30 bar" in x for x in g930) and g1030_early == [] and any("no 10:30 bar" in x for x in g1030)
          and any("prior sessions" in x for x in gpr),
          f"{g_ok} {g5} {g2} {g930} {g1030_early} {g1030} {gpr}")

    pages = []
    saved_alert = PP._alert
    PP._alert = lambda text: pages.append(text)
    try:
        P = Park()
        PP._TAPE["day"] = None
        write_store({"CVX": cvx_ok(), "QQQ": drop(qqq_ok(), ["10:%02d" % i for i in range(5, 10)])})
        p1 = P.prepare(price_now=235.3, now_et="10:15", chain=None, prior_close=None, day=T_DAY, symbol="CVX")
        PP._TAPE["watched_at"] = 0.0
        P.prepare(price_now=235.3, now_et="10:16", chain=None, prior_close=None, day=T_DAY, symbol="CVX")
        early = list(pages)
        pages.clear()
        PP._TAPE["day"] = None
        write_store({"CVX": cvx_ok(), "QQQ": qqq_ok()})
        P.prepare(price_now=235.3, now_et="10:15", chain=None, prior_close=None, day=T_DAY, symbol="CVX")
        clean = list(pages)
        pages.clear()
        PP._TAPE["day"] = None
        write_store({"QQQ": qqq_ok()})
        P.prepare(price_now=702.0, now_et="10:15", chain=None, prior_close=None, day=T_DAY, symbol="QQQ")
        idx = list(pages)
        check("T2 from 10:00 an equity's two tapes are watched: ONE page at the first gap (it names QQQ's), none on a "
              "clean tape, none on an index; the watch writes no condition",
              len(early) == 1 and "QQQ (pair)" in early[0] and "5 of" in early[0] and not clean and not idx
              and not p1.conditions, f"early={early} clean={clean} idx={idx} conds={p1.conditions}")

        pages.clear()
        PP._TAPE["day"] = None
        write_store({"CVX": cvx_ok(), "QQQ": drop(qqq_ok(), ["10:59"])})
        a1, s1 = run(P, "CVX", 235.33)
        P.prepare(price_now=235.3, now_et="11:02", chain=Chain("CVX", 235.33), prior_close=None, day=T_DAY,
                  symbol="CVX")
        P.prepare(price_now=235.3, now_et="11:03", chain=None, prior_close=None, day=T_DAY, symbol="CVX")
        P.prepare(price_now=235.3, now_et="11:04", chain=None, prior_close=None, day=T_DAY, symbol="CVX")
        starved = list(pages)
        pages.clear()
        PP._TAPE["day"] = None
        write_store({"CVX": cvx_ok(), "QQQ": drop(qqq_ok(), ["10:59"])})
        run(P, "CVX", 235.33)
        write_store({"CVX": cvx_ok(), "QQQ": qqq_ok()})
        a2 = P.prepare(price_now=235.33, now_et="11:02", chain=Chain("CVX", 235.33), prior_close=None, day=T_DAY,
                       symbol="CVX")
        P.prepare(price_now=235.3, now_et="11:03", chain=None, prior_close=None, day=T_DAY, symbol="CVX")
        recovered = list(pages)
        check("T3 FAILS CLOSED, AND SAYS SO: the first starved tick pages once (the window re-reads every tick), the "
              "window's end pages FAILED CLOSED once; a tape that recovers at 11:02 fires and is not paged closed",
              s1 is None and len(starved) == 2 and "cannot read" not in starved[0] and "too thin" in starved[0]
              and "FAILED CLOSED" in starved[1] and len(recovered) == 1 and a2.ready,
              f"starved={starved} recovered={recovered} ready={a2.ready}")
    finally:
        PP._alert = saved_alert

    class FakeStreamer:
        def __init__(self):
            self.calls = []

        async def unsubscribe_candle(self, sym, iv):
            self.calls.append(("un", sym, iv))

        async def subscribe_candle(self, syms, iv, start_time=None, extended_trading_hours=None):
            self.calls.append(("sub", syms[0], iv, start_time, extended_trading_hours))

    def feed_self(dx="CVX"):
        fs = types.SimpleNamespace(dx_symbol=dx, _commit_refill={})
        fs._commit_refill_due = types.MethodType(CF.CandleFeed._commit_refill_due, fs)
        return fs

    def refill(fs, st, h, m, sec=0, d=T_DAY):
        return asyncio.run(CF.CandleFeed._maybe_refill_commit_tape(
            fs, st, now=datetime(d.year, d.month, d.day, h, m, sec, tzinfo=ET)))

    saved_instr = CF.INSTRUMENT
    try:
        CF.INSTRUMENT = "CVX"
        write_store({"CVX": cvx_ok(), "QQQ": drop(qqq_ok(), ["10:%02d" % i for i in range(5, 10)])})
        fs, st = feed_self(), FakeStreamer()
        r1 = refill(fs, st, 10, 15)
        c1 = list(st.calls)
        r2 = refill(fs, st, 10, 16)
        c2 = st.calls[len(c1):]
        r3 = refill(fs, st, 11, 0, 30)
        c3 = st.calls[len(c1) + len(c2):]
        ok_start = (c1 and c1[-1][0] == "sub" and c1[-1][1] == "QQQ" and c1[-1][2] == "1m"
                    and c1[-1][3] == datetime(T_DAY.year, T_DAY.month, T_DAY.day, 9, 30, tzinfo=ET)
                    and c1[-1][4] is False)
        check("T4 the feed re-pulls a short pair tape from today's 09:30 on ITS OWN streamer (unsubscribe, then "
              "subscribe 1m RTH), not the clean own tape; the cadence holds a second pull a minute later; the forced "
              "pull after the 10:59 bar goes whatever the cadence says",
              r1 == ["QQQ"] and ok_start and ("un", "QQQ", "1m") in c1 and r2 == [] and not c2 and r3 == ["QQQ"]
              and len(c3) == 2, f"r1={r1} c1={c1} r2={r2} r3={r3} c3={c3}")

        write_store({"CVX": sess_dict(cvx_ok()["today"], cvx_ok()["prior"][:2]), "QQQ": qqq_ok()})
        fs, st = feed_self(), FakeStreamer()
        r4 = refill(fs, st, 10, 20)
        deep = st.calls[-1][3] if st.calls else None
        write_store({"CVX": cvx_ok(), "QQQ": qqq_ok()})
        fs2, st2 = feed_self(), FakeStreamer()
        r5 = refill(fs2, st2, 10, 20)
        r6 = refill(fs2, st2, 9, 50)
        check("T5 a short PRIOR session re-pulls the own tape PRIME-deep; a clean tape pulls nothing; nothing before "
              "10:00",
              r4 == ["CVX"] and deep is not None and deep.date() <= T_DAY - timedelta(days=30) and r5 == [] and r6 == []
              and not st2.calls, f"r4={r4} deep={deep} r5={r5} r6={r6}")

        write_store({"CVX": cvx_ok(), "QQQ": drop(qqq_ok(), ["10:%02d" % i for i in range(5, 10)])})
        fs, st = feed_self(), FakeStreamer()
        saved_every = config.PARK_TAPE_REFILL_EVERY_S
        config.PARK_TAPE_REFILL_EVERY_S = 0
        try:
            n = sum(len(refill(fs, st, 10, 15 + i)) for i in range(8))
        finally:
            config.PARK_TAPE_REFILL_EVERY_S = saved_every
        CF.INSTRUMENT = "SPX"
        fs3, st3 = feed_self("SPX"), FakeStreamer()
        r7 = refill(fs3, st3, 10, 15)
        check("T6 at most PARK_TAPE_REFILL_MAX pulls a day per symbol; an index box never pulls (no pair route)",
              n == config.PARK_TAPE_REFILL_MAX and r7 == [] and not st3.calls, f"n={n} r7={r7}")
    finally:
        CF.INSTRUMENT = saved_instr

    # ── H: the pair tape on the manifold (tools/manifold_health v5.1) ─────────────────────────────────────────────
    import time as _tm
    import tools.manifold_health as MH
    hdb = os.path.join(_TD, "health_feed.db")

    def hroll(rep):
        """The rollup on the candles alone (this test store holds no raw streams, whose absence is RED on its own)."""
        return MH.rollup(dict(rep, streams=[]))

    def hstore(rows):
        if os.path.exists(hdb):
            os.remove(hdb)
        c = sqlite3.connect(hdb)
        c.execute("CREATE TABLE candles (symbol TEXT, interval TEXT, ts_epoch_ms INTEGER, open REAL, high REAL, "
                  "low REAL, close REAL, volume REAL)")
        for sym, iv, age in rows:
            c.execute("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?)",
                      (sym, iv, int((_tm.time() - age) * 1000), 1, 1, 1, 1, 1))
        c.commit()
        c.close()
    ten = datetime(2026, 11, 4, 10, 0, tzinfo=ET)
    pre = datetime(2026, 11, 4, 9, 25, tzinfo=ET)
    saved_env = os.environ.get("OT_INSTRUMENT")
    try:
        os.environ["OT_INSTRUMENT"] = "CVX"
        hstore([("CVX", "1m", 20), ("VIX", "1m", 20), ("QQQ", "1m", 30), ("QQQ", "5m", 30)])
        rep = MH.collect(hdb, os.path.join(_TD, "none.db"), True, False, now_et=ten)
        pr = [c for c in rep["candles"] if c.get("pair")]
        q5 = [c for c in rep["candles"] if c["label"] == "QQQ/5m"]
        check("H1 on an equity box QQQ/1m is a PAIR item (not foreign), GREEN when fresh; any other QQQ row stays "
              "foreign; the rollup is GREEN",
              len(pr) == 1 and pr[0]["label"] == "QQQ/1m" and pr[0]["bulb"] == MH.GREEN and not pr[0]["foreign"]
              and q5 and q5[0]["foreign"] and hroll(rep) == MH.GREEN, f"{pr} {q5} {hroll(rep)}")
        hstore([("CVX", "1m", 20), ("QQQ", "1m", 600)])
        rep = MH.collect(hdb, os.path.join(_TD, "none.db"), True, False, now_et=ten)
        pr = [c for c in rep["candles"] if c.get("pair")]
        check("H2 QQQ/1m older than PARK_PAIR_STALE_S in RTH is RED and the rollup goes RED",
              pr and pr[0]["bulb"] == MH.RED and hroll(rep) == MH.RED, f"{pr} {hroll(rep)}")
        hstore([("CVX", "1m", 20)])
        rep = MH.collect(hdb, os.path.join(_TD, "none.db"), True, False, now_et=ten)
        pr = [c for c in rep["candles"] if c.get("pair")]
        check("H3 no QQQ in the store at all: a QQQ/1m row is written anyway, RED, rollup RED",
              pr and pr[0]["rows"] == 0 and pr[0]["bulb"] == MH.RED and hroll(rep) == MH.RED, f"{pr}")
        rep = MH.collect(hdb, os.path.join(_TD, "none.db"), False, False, now_et=pre)
        pr = [c for c in rep["candles"] if c.get("pair")]
        early = datetime(2026, 11, 4, 9, 31, 10, tzinfo=ET)
        hstore([("CVX", "1m", 20), ("QQQ", "1m", 60000)])
        rep2 = MH.collect(hdb, os.path.join(_TD, "none.db"), True, False, now_et=early)
        pr2 = [c for c in rep2["candles"] if c.get("pair")]
        check("H4 before 09:31 the pair row is GREY (not judged); at 09:31:10 yesterday's last bar is not yet stale",
              pr and pr[0]["bulb"] == MH.GREY and pr2 and pr2[0]["bulb"] == MH.GREEN, f"{pr} {pr2}")
        for box in ("QQQ", "SPX"):
            os.environ["OT_INSTRUMENT"] = box
            hstore([(box, "1m", 20), ("QQQ", "1m", 600)])
            rep = MH.collect(hdb, os.path.join(_TD, "none.db"), True, None, now_et=ten)
            if any(c.get("pair") for c in rep["candles"]):
                break
        check("H5 the QQQ box and the SPX box carry no pair row", not any(c.get("pair") for c in rep["candles"]),
              f"{box}: {rep['candles']}")
    finally:
        if saved_env is None:
            os.environ.pop("OT_INSTRUMENT", None)
        else:
            os.environ["OT_INSTRUMENT"] = saved_env

    if FAILED:
        print(f"\nRED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print(f"\nGREEN — {N_CHECKS} of {N_CHECKS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
