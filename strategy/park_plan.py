"""
strategy/park_plan.py  v5.7
v5.7  2026-11-08  OTV5 r93 (C8.1) — PARK SKIPS AN ENTRY THE FIRST HOUR HAS ALREADY OUTRUN. The operator, 2026-11-08: "Yes,
      to both" (C8 passed its blind test, ~/reviews/studies/web_setups_1108, FROZEN 18:57 UTC). first_hour_extended(): a
      call is skipped when the 10:59 1m bar's CLOSE is ABOVE the highest high of the 09:30-10:29 1m bars, a put when it
      is BELOW their lowest low (strict: equal is not extended). The 10:59 bar closed at 11:00, before the 11:01 window,
      so nothing still forming is read. FAILS OPEN: no 10:59 bar, no 09:30-10:29 bar, no direction or an unreadable
      store = not extended, said on the row (the study kept those trades as "unknown"). No parameter, no toggle. The
      refusal is condition c8_first_hour_extended (plan_check row + the gate reporter + one [park] SKIP line); it is
      asked AFTER the r90 shadow row (PARK_SMA50 still writes on every directional tick C8 skips) and after GATE-G and
      the commitment gate, before the contract. Index and equity alike. Gates tests/check_park_c8.py.
v5.6  2026-11-08  OTV5 r90 (SHADOW.1) — LOG ONLY: once the first hour gives a direction, and before GATE-G, the commitment
      gate or the contract can refuse it, prepare() records the daily SMA 50 slope's verdict (S4 S1d_slope, on the box's
      own TastyTrade 1d candles) through strategy/shadow_rules.record_park: one plan_check row shadow_park_sma50 per tick,
      one [shadow-rule] line per day and direction. It never decides and never raises (tests/check_shadow_rules.py N2).
v5.5  2026-11-03  OTV5 r72 (PARK.5) — THE GATE'S TAPE IS WATCHED FROM 10:00, AND A PROBLEM IS PAGED, NOT ONLY LOGGED. The
      operator, 2026-11-03: "Fine, but we need to be more responsive when that happens to mitigate impacts to trading" and
      "the plan should warn if there's a problem". (1) tape_gaps(sess, upto): the early read - what is ALREADY missing by
      the last closed minute (a 09:30 / 10:30 bar, >= PARK_TAPE_GAP_BARS minutes since 09:30, a bar without volume, the
      prior sessions' fail-closed reads); tape_short (the 11:01 verdict) is unchanged. (2) prepare() on an equity, inside
      PARK_TAPE_WATCH_ET, reads both tapes every PARK_TAPE_WATCH_EVERY_S (no plan row, no condition) and pages ONCE per
      session at the first gap, so control's triage can act while the candle feed (data/candle_feed v5.8) re-pulls it. (3)
      The fail-closed path pages too: the first STARVED tick of the 11:01-11:03 window (the window re-reads every tick, so
      it is the bounded wait for the refill), and once more when the window ends still starved. A tape that recovers
      inside the window is logged. Every page goes through AlertManager._send (the [alert]/[page] routes, r71/r522). The
      gate's decisions are unchanged (tests/check_park_commit.py R1: the study's 27 / 170 split).
v5.4  2026-11-03  OTV5 r72 (PARK.5) — ON AN EQUITY, PARK ALSO NEEDS THE MARKET'S COMMITMENT. The operator, 2026-11-03: "Let's
      modify the park trade on equities using the new filters — add a gate in the code 'is an index=false' and start
      trading it Monday." is_index(symbol) (config.PARK_INDEXES: SPX, QQQ) -> prepare() runs exactly as v5.3: no new read,
      no new check row (tests/check_no_parc.py N5 and check_park stay byte-identical). Otherwise, once the move and GATE-G
      have cleared and before the contract, commitment_read() narrates two more conditions: pair_agrees (QQQ's own
      09:30 open -> 10:30 close moved >= PARK_MOVE_PCT the same way) and commitment (fewer than PARK_COMMIT_SKIP of the
      three leans - range, reject, part - AGAINST on the name AND on QQQ, both read in the name's direction). The pure
      read is session_bars() (the store, RTH 1m, today + prior sessions) -> read_name() / leans() / commitment_gate(),
      ported from the study's validated draft (~/cont_study/draft/strategy/cont_plan.py: read_name, leans, decide) with
      PARK's own move and direction. A tape too thin to read on either name (config.PARK_COMMIT_MIN_*) is STARVED, never
      read as "unknown": no PARK fires on that equity (FAILS CLOSED), and the plan row names what was short. Every bar
      read closed by 11:00 (the 10:59 bar is required); PARK's window opens 11:01. QQQ's 1m bars reach each equity box on
      its own candle-feed session (data/candle_feed v5.7). Gate tests/check_park_commit.py.
v5.3  2026-10-31  OTV5 r67 (PARC.4) — WORDS ONLY: read_first_hour's docstring and one comment no
      longer say PARC shares the read (PARC is removed; it was the only other caller). No code changed: PARK's
      decisions and rows are identical (tests/check_no_parc.py N5). The operator, 2026-10-31: "On PARC, no. It was an idea. It failed. It's done." and "Yes" to removing its code.
v5.2  2026-10-30  OTV5 r60 (PARK.4) — PARK BUYS AT THE MARK, NOT THE ASK. The operator, 2026-10-30, on CVX's PARK
      (235C bought at the ask 1.56 on a 0.97/1.56 quote, mark 1.265, -$657 booked, -$480 at the mark): "That's not my
      spec… you know park is a borrowed trade. To match my spec, we ladder in from aggressive to mark & never worse
      than mark". prepare() sets the premium to the MARK, (bid + ask) / 2 of the contract it picked - the same mark
      data/options_chain and execution/entry_ladder compute - floored to the cent (entry_engine._mark_cap's rule, r224
      FLY.1; the raw float 1.265 rounded UP to 1.27 in limit_at_mark), so the signal's entry_premium is the mark: paper
      books the mark (entry_engine._paper_fill_single -> limit_ladder.paper_fill_price), the size is floor(risk / (mark
      x 100)) and the +60% / +20% lock keys off the booked mark. Live walks the r104 ladder (entry_engine
      _place_single_leg -> ladder_registry.price_for): 25% in from the bid, one increment a tick toward the mark,
      never above it; unfilled by 11:03 is no trade. The feasibility bar is unchanged (two-sided, ask >=
      PARK_MIN_ASK). The FIRE line reads "@ <mark> (mark, bid/ask b/a)"; park_signal.jsonl keeps the real "ask" and
      "bid" and adds "mark". Every PARK fill 10-26..10-30 (28 of 28) had paid the ask: $651 over the mark, $177 of
      it CVX 10-30. Gate tests/check_park_entry_mark.py.
v5.1  2026-10-27  OTV5 r46 (PARC.1) — THE FIRST-HOUR READ IS ONE FUNCTION, SHARED WITH PARC. The operator, 2026-10-27:
      "under identical entry conditions the PARK trade sells a credit spread ... Call it PARC"; "No shadow mode. We're
      paper. It trades tomorrow." read_first_hour() is the block ParkPlan.prepare ran inline - the store read, the
      starved inputs, the prior-close source, the move, the direction and GATE-G, every plan check in the same order -
      moved verbatim so strategy/parc_plan.py asks the SAME code. PARK's decisions and rows are byte-identical
      (tests/check_park.py, tests/check_parc.py P10).
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.0  2026-10-18  OTV4TEST r288 (PARK.1) — PARK'S PLAN: READS THE FIRST HOUR, PICKS THE CONTRACT, BUILDS THE
      SIGNAL. The specification - what must be true - is strategy/park.py; this file is the search (the
      operator, 2026-10-17 18:30 ET: "Make sure when you build it it's divided properly between the strategy
      and the plan").

      THE READ (frozen, /var/tmp/sat_1017/cont11/PREREG_CONT11.md C0 and cont11.py): the 09:30 1m bar's OPEN, the
      10:30 1m bar's CLOSE and the 11:00 1m bar's CLOSE of TODAY's RTH, and the prior session's last RTH 1m close
      - all read from the feed store (read-only) on every call, so a restart decides the same. The prior close
      falls back to the caller's `prior_close` (main: the gap's prior_close) only when the store has no prior
      session; which one was used is recorded on the row.
      THE CONTRACT: today's chain, the strike nearest the 11:00 close (ties: the lower strike), its side's
      contract, two-sided, ask >= PARK_MIN_ASK. ENTRY = THE MARK (v5.2, the operator 2026-10-30: "we ladder in from
      aggressive to mark & never worse than mark"; it was the ask, the study's fill); the paper fill books
      entry_premium, and the live ladder never pays more than the mark.
      THE SIGNAL carries no premium stop and no underlying stop (stop_loss_pct = 1.0, underlying_stop = 0): the
      exits are PARK's own (execution/exit_engine._evaluate_park).
"""

from __future__ import annotations

import logging
from typing import Optional

import config
from strategy.plan import Plan
from utils.time_utils import parse_hm as _hm

logger = logging.getLogger(__name__)

_ET_ZONE = "America/New_York"
MIN_ASK = float(config.PARK_MIN_ASK)

# WA 36 - a cheaper ask is not a contract this trade can hold (the study's floor).
GATES = {
    "MIN_ASK": "FEASIBILITY",
}


def _f(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def first_hour_bars(symbol: str, day):
    """{"open_0930", "close_1030", "spot_1100", "prior_close"} for `day` from the feed store's 1m candles
    (None where a bar is absent), or a string naming why the store could not be read. NEVER raises.
    prior_close = the last 1m close of the most recent earlier RTH session in the store."""
    from datetime import datetime
    try:
        import sqlite3
        from zoneinfo import ZoneInfo
        from data.candle_feed import feed_db_path
        z = ZoneInfo(_ET_ZONE)

        def ms(h, m):
            return int(datetime(day.year, day.month, day.day, h, m, tzinfo=z).timestamp() * 1000)
        conn = sqlite3.connect(f"file:{feed_db_path()}?mode=ro", uri=True, timeout=5.0)
        try:
            def bar(h, m):
                return conn.execute("SELECT open, close FROM candles WHERE symbol=? AND interval='1m' "
                                    "AND ts_epoch_ms=? AND close > 0", (symbol, ms(h, m))).fetchone()
            b930, b1030 = bar(9, 30), bar(*config.PARK_SIGNAL_BAR_ET)
            b1100 = bar(*config.PARK_SPOT_BAR_ET)
            # the prior session: the newest 1m bar before today's 09:30 whose ET time is inside RTH
            prev = conn.execute(
                "SELECT ts_epoch_ms, close FROM candles WHERE symbol=? AND interval='1m' AND ts_epoch_ms < ? "
                "AND ts_epoch_ms >= ? AND close > 0 ORDER BY ts_epoch_ms DESC LIMIT 600",
                (symbol, ms(9, 30), ms(9, 30) - 6 * 86_400_000)).fetchall()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        return f"1m bars unreadable ({type(exc).__name__}: {exc})"
    prior = None
    for t, c in prev:
        et = datetime.fromtimestamp(t / 1000, z)
        if (9, 30) <= (et.hour, et.minute) < (16, 0):
            prior = float(c)
            break
    return {"open_0930": float(b930[0]) if b930 else None,
            "close_1030": float(b1030[1]) if b1030 else None,
            "spot_1100": float(b1100[1]) if b1100 else None,
            "prior_close": prior}


def read_first_hour(t, cond, *, symbol: str, day, prior_close=None):
    """THE FIRST-HOUR READ (PARK.1), factored out of ParkPlan.prepare at OTV5 r46. Reads the store, writes the plan checks
    in PARK's order on tick `t`, asks `cond` for first_hour_move and gate_g, and returns {"move_pct", "spot",
    "direction", "gap"} - or None when the tick STARVED (it has already said so on `t`). Moved verbatim from
    ParkPlan.prepare: the starved inputs, the prior-close source note, the move and the direction rule
    (up first hour = long), GATE-G (a long needs gap >= 0, a short gap <= 0)."""
    bars = first_hour_bars(symbol, day)
    if isinstance(bars, str):
        t.note(bars)
        t.starved("first_hour_bars")
        return None
    missing = [k for k in ("open_0930", "close_1030", "spot_1100") if bars.get(k) is None]
    if missing:
        t.starved(*missing)
        return None
    o, c1030, spot = bars["open_0930"], bars["close_1030"], bars["spot_1100"]
    prev, src = bars.get("prior_close"), "store"
    if prev is None:
        prev, src = _f(prior_close), "caller"
    if prev is None:
        t.starved("prior_close")
        return None
    for k, v in (("open_0930", o), ("close_1030", c1030), ("spot_1100", spot), ("prior_close", prev)):
        t.check(k, v, None)
    t.note(f"prior close from the {src}")

    move = (c1030 / o - 1.0) * 100.0
    t.check("move_pct", move, None)
    cond("first_hour_move", abs(move), abs(move) >= config.PARK_MOVE_PCT)
    direction = "long" if move > 0 else "short" if move < 0 else ""
    gap = o - prev
    t.check("gap", gap, None)
    cond("gate_g", gap, bool(direction) and ((gap >= 0) if direction == "long" else (gap <= 0)))
    return {"move_pct": move, "spot": spot, "direction": direction, "gap": gap}


# ── v5.7 (C8.1) — THE FIRST HOUR ALREADY OUTRUN ────────────────────────────────────────────────────────────────────
C8_CLOSE_BAR = "10:59"                  # its close is settled at 11:00, before the 11:01 window (closed bars only)
C8_IB = ("09:30", "10:29")              # the first hour's 1m bars (bar START stamps), as the frozen study read them


def first_hour_extended(today: dict, direction: str) -> dict:
    """C8, the frozen blind-tested rule: {"extended": True | False | None, "close_1059", "ib_high", "ib_low", "why"}.
    `today` is session_bars()["today"] ("HH:MM" -> (o, h, l, c, v)). A long is extended when the 10:59 close is ABOVE
    the 09:30-10:29 high, a short when it is BELOW their low; equality is not extended. None (unknown) when the 10:59
    bar, every first-hour bar or the direction is missing - the caller treats unknown as NOT extended (fails open).
    Pure: reads only `today`, never a bar stamped after 10:59."""
    out = {"extended": None, "close_1059": None, "ib_high": None, "ib_low": None, "why": ""}
    today = today or {}
    ib = [today[k] for k in sorted(today) if C8_IB[0] <= k <= C8_IB[1]]
    if ib:
        out["ib_high"], out["ib_low"] = max(float(b[1]) for b in ib), min(float(b[2]) for b in ib)
    b = today.get(C8_CLOSE_BAR)
    if b is not None:
        out["close_1059"] = float(b[3])
    if direction not in ("long", "short"):
        out["why"] = "no direction"
    elif out["close_1059"] is None:
        out["why"] = "no %s 1m bar" % C8_CLOSE_BAR
    elif not ib:
        out["why"] = "no %s-%s 1m bar" % C8_IB
    elif direction == "long":
        out["extended"] = out["close_1059"] > out["ib_high"]
    else:
        out["extended"] = out["close_1059"] < out["ib_low"]
    return out


def c8_read(t, cond, *, symbol: str, day, direction: str) -> dict:
    """Narrate C8 on tick `t` and write condition c8_first_hour_extended through `cond` (met = NOT extended). Unknown
    fails open (met, with the reason as the note). Returns the first_hour_extended() dict. NEVER raises."""
    try:
        sess = session_bars(symbol, day, n_prior=0)
        if isinstance(sess, str):
            r = {"extended": None, "close_1059": None, "ib_high": None, "ib_low": None, "why": sess}
        else:
            r = first_hour_extended(sess.get("today") or {}, direction)
    except Exception as exc:                                    # noqa: BLE001
        r = {"extended": None, "close_1059": None, "ib_high": None, "ib_low": None,
             "why": "C8 read failed (%s: %s)" % (type(exc).__name__, exc)}
    t.check("close_1059", r["close_1059"], None)
    t.check("ib_high", r["ib_high"], None)
    t.check("ib_low", r["ib_low"], None)
    if r["extended"] is None:
        cond("c8_first_hour_extended", r["close_1059"], True, note="unknown, fails open: " + r["why"])
    elif r["extended"]:
        edge = ("above the %s-%s high %.2f" % (C8_IB[0], C8_IB[1], r["ib_high"]) if direction == "long"
                else "below the %s-%s low %.2f" % (C8_IB[0], C8_IB[1], r["ib_low"]))
        note = "the %s close %.2f is already %s" % (C8_CLOSE_BAR, r["close_1059"], edge)
        cond("c8_first_hour_extended", r["close_1059"], False, note=note)
        logger.info("[park] SKIP c8_first_hour_extended %s %s - %s", symbol, direction, note)
    else:
        cond("c8_first_hour_extended", r["close_1059"], True)
    return r


# ── v5.4 (PARK.5) — THE COMMITMENT GATE, EQUITIES ONLY ─────────────────────────────────────────────────────────────
def is_index(symbol: str) -> bool:
    """An index trades PARK ungated (config.PARK_INDEXES)."""
    return str(symbol or "").strip().upper() in tuple(s.upper() for s in config.PARK_INDEXES)


def _hhmm(h, m) -> str:
    return "%02d:%02d" % (h, m)


def session_bars(symbol: str, day, n_prior: int = 6):
    """{"today": {"HH:MM": (o, h, l, c, v)}, "prior": [same, newest first]} of `symbol`'s RTH 1m bars in the feed store
    (read-only), today and up to `n_prior` earlier sessions - or a string naming why the store could not be read.
    NEVER raises. v is None where the store holds no volume. Only bars whose ET minute is inside 09:30-15:59."""
    from datetime import datetime
    try:
        import sqlite3
        from zoneinfo import ZoneInfo
        from data.candle_feed import feed_db_path
        z = ZoneInfo(_ET_ZONE)
        t0 = int(datetime(day.year, day.month, day.day, 9, 30, tzinfo=z).timestamp() * 1000)
        conn = sqlite3.connect(f"file:{feed_db_path()}?mode=ro", uri=True, timeout=5.0)
        try:
            rows = conn.execute(
                "SELECT ts_epoch_ms, open, high, low, close, volume FROM candles WHERE symbol=? AND interval='1m' "
                "AND ts_epoch_ms >= ? AND ts_epoch_ms < ? AND close > 0 ORDER BY ts_epoch_ms",
                (symbol, t0 - (n_prior + 8) * 86_400_000, t0 + 7 * 3_600_000)).fetchall()
        finally:
            conn.close()
    except Exception as exc:                                    # noqa: BLE001
        return f"{symbol} 1m bars unreadable ({type(exc).__name__}: {exc})"
    by = {}
    for t, o, h, l, c, v in rows:
        et = datetime.fromtimestamp(t / 1000, z)
        if not ((9, 30) <= (et.hour, et.minute) < (16, 0)):
            continue
        by.setdefault(et.date(), {})[_hhmm(et.hour, et.minute)] = (
            float(o), float(h), float(l), float(c), _f(v) if v not in (None, "") else None)
    today = by.pop(day, {})
    prior = [by[d] for d in sorted(by, reverse=True) if d < day][:n_prior]
    return {"today": today, "prior": prior}


def _window(bars: dict, a, b):
    lo, hi = _hhmm(*a), _hhmm(*b)
    return [bars[k] for k in sorted(bars) if lo <= k <= hi]


def tape_short(sess: dict) -> list:
    """What makes this name's tape too thin to read the gate (empty = readable). FAILS CLOSED on any of: no 09:30 /
    10:30 / 10:59 bar today; the hour bar from fewer than PARK_COMMIT_MIN_HOUR_BARS 1m bars; the participation window
    from fewer than PARK_COMMIT_MIN_PART_BARS bars, or any of them without volume; fewer than PARK_COMMIT_MIN_PRIOR prior
    sessions holding that window; the prior session from fewer than PARK_COMMIT_MIN_PRIOR_BARS bars."""
    out = []
    today, prior = (sess or {}).get("today") or {}, (sess or {}).get("prior") or []
    for hm in ((9, 30), tuple(config.PARK_SIGNAL_BAR_ET), (10, 59)):
        if _hhmm(*hm) not in today:
            out.append("no %s bar" % _hhmm(*hm))
    if len(_window(today, *config.PARK_COMMIT_HOUR_ET)) < config.PARK_COMMIT_MIN_HOUR_BARS:
        out.append("hour bar from %d 1m bars" % len(_window(today, *config.PARK_COMMIT_HOUR_ET)))

    def part_ok(bars):
        w = _window(bars, *config.PARK_COMMIT_PART_ET)
        return len(w) >= config.PARK_COMMIT_MIN_PART_BARS and all(x[4] is not None for x in w)
    if not part_ok(today):
        out.append("participation window short or without volume today")
    n_ok = sum(1 for p in prior[:config.PARK_COMMIT_LOOKBACK] if part_ok(p))
    if n_ok < config.PARK_COMMIT_MIN_PRIOR:
        out.append("%d prior sessions hold the participation window" % n_ok)
    if not prior or len(prior[0]) < config.PARK_COMMIT_MIN_PRIOR_BARS:
        out.append("prior session from %d bars" % (len(prior[0]) if prior else 0))
    return out


def tape_gaps(sess, upto) -> list:
    """v5.5 — the EARLY read, before 11:01: what is already missing from this name's tape by `upto` (the last CLOSED
    minute, (h, m)), judged only on minutes that should exist by then. Empty = nothing missing so far. Any of: the store
    unreadable (`sess` a string); no 09:30 bar, or no 10:30 bar once it should have closed; >= PARK_TAPE_GAP_BARS 1m bars
    missing since 09:30; a bar without volume; the prior sessions' fail-closed reads (as tape_short). NEVER raises."""
    if isinstance(sess, str):
        return [sess]
    out = []
    today, prior = (sess or {}).get("today") or {}, (sess or {}).get("prior") or []
    try:
        uh, um = int(upto[0]), int(upto[1])
    except Exception:                                           # noqa: BLE001
        return ["no time to judge against"]
    end = min((uh, um), (10, 59))
    want, h, m = [], 9, 30
    while (h, m) <= end:
        want.append(_hhmm(h, m))
        h, m = (h + 1, 0) if m == 59 else (h, m + 1)
    for anchor in ("09:30", _hhmm(*config.PARK_SIGNAL_BAR_ET)):
        if anchor in want and anchor not in today:
            out.append("no %s bar" % anchor)
    miss = [k for k in want if k not in today]
    if len(miss) >= config.PARK_TAPE_GAP_BARS:
        out.append("%d of %d minutes missing since 09:30" % (len(miss), len(want)))
    novol = [k for k in want if k in today and today[k][4] is None]
    if novol:
        out.append("%d bar(s) without volume" % len(novol))
    w_ok = sum(1 for p in prior[:config.PARK_COMMIT_LOOKBACK]
               if len(_window(p, *config.PARK_COMMIT_PART_ET)) >= config.PARK_COMMIT_MIN_PART_BARS
               and all(x[4] is not None for x in _window(p, *config.PARK_COMMIT_PART_ET)))
    if w_ok < config.PARK_COMMIT_MIN_PRIOR:
        out.append("%d prior sessions hold the participation window" % w_ok)
    if not prior or len(prior[0]) < config.PARK_COMMIT_MIN_PRIOR_BARS:
        out.append("prior session from %d bars" % (len(prior[0]) if prior else 0))
    return out


def judged_upto(now_hm) -> tuple:
    """The newest minute an early read may demand: two minutes back, so a bar that closed seconds ago and is still
    in the feed's flush buffer never reads as a gap."""
    h, m = int(now_hm[0]), int(now_hm[1]) - 2
    if m < 0:
        h, m = h - 1, m + 60
    return (h, m)


# v5.5 — one session's tape-watch state for this box (the plan runs once per box; the feed has its own).
_TAPE = {"day": None, "watched_at": 0.0, "paged": set(), "starved": False, "recovered": False}


def _tape_state(day) -> dict:
    if _TAPE["day"] != day:
        _TAPE.update(day=day, watched_at=0.0, paged=set(), starved=False, recovered=False)
    return _TAPE


def _alert(text: str) -> None:
    """Page the operator / control through the bot's one alert path (AlertManager._send: the Telegram send, the ALERT
    line, the [page] line, and on a managed box the [alert] route). NEVER raises; a page that fails is logged."""
    logger.warning("[park] %s", text)
    try:
        from notifications.alert_manager import get_alert_manager
        get_alert_manager()._send(text, "MSG")
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[park] page not sent (%s)", exc)


def _page_once(day, key: str, text: str) -> bool:
    st = _tape_state(day)
    if key in st["paged"]:
        return False
    st["paged"].add(key)
    _alert(text)
    return True


def watch_tape(symbol: str, day, now_hm) -> list:
    """v5.5 — the 10:00-11:00 watch on an equity (the caller checks is_index and the window): both tapes read every
    PARK_TAPE_WATCH_EVERY_S, judged by tape_gaps up to the last closed minute, and ONE page per session at the first gap
    (the candle feed is re-pulling it meanwhile). Returns the gaps found ([] when none, or not read this tick). Writes no
    plan row and no condition. NEVER raises."""
    import time as _t
    try:
        st = _tape_state(day)
        now = _t.monotonic()
        if st["watched_at"] and now - st["watched_at"] < config.PARK_TAPE_WATCH_EVERY_S:
            return []
        st["watched_at"] = now
        h, m = now_hm
        upto = judged_upto(now_hm)
        pair = str(config.PARK_PAIR_SYMBOL)
        gaps = ["%s: %s" % (symbol, g) for g in tape_gaps(session_bars(symbol, day), upto)]
        gaps += ["%s (pair): %s" % (pair, g) for g in tape_gaps(session_bars(pair, day), upto)]
        if gaps:
            _page_once(day, "early", "⚠️ PARK tape gap on %s at %02d:%02d ET - %s. The candle feed is re-pulling it; PARK "
                       "re-checks every tick 11:01-11:03 and fails closed (no trade) only if still short."
                       % (symbol, h, m, "; ".join(gaps[:4])))
        return gaps
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[park] tape watch failed: %s", exc)
        return []


def read_name(today: dict, prior: list) -> dict:
    """One name's first-hour facts for the gate (ported from the study's draft read_name): the 09:30 open, the 10:30
    close, the move, and the prior session's high / low. Keys are None where a bar is absent. NEVER raises."""
    out = dict(open_0930=None, close_1030=None, move_pct=None, prior_high=None, prior_low=None)
    b930, b1030 = today.get("09:30"), today.get(_hhmm(*config.PARK_SIGNAL_BAR_ET))
    out["open_0930"] = b930[0] if b930 else None
    out["close_1030"] = b1030[3] if b1030 else None
    if prior and prior[0]:
        out["prior_high"] = max(x[1] for x in prior[0].values())
        out["prior_low"] = min(x[2] for x in prior[0].values())
    o, c = out["open_0930"], out["close_1030"]
    if o and c:
        out["move_pct"] = (c / o - 1.0) * 100.0
    return out


def leans(r: dict, today: dict, prior: list, direction: str) -> dict:
    """The three leans on ONE name, read in `direction`: each True (AGAINST) / False (not) / None (unknown), with the
    number each was read from (range_edge = open - prior high for a long, prior low - open for a short; wick; ratio).
    Ported from the study's draft leans() byte for byte in its rules."""
    import statistics
    out = {"range": None, "reject": None, "part": None, "range_edge": None, "wick": None, "part_ratio": None}
    if direction not in ("long", "short"):
        return out
    o, ph, pl = r.get("open_0930"), r.get("prior_high"), r.get("prior_low")
    if o is not None and ph is not None and pl is not None:
        out["range_edge"] = (o - ph) if direction == "long" else (pl - o)
        out["range"] = not (o > ph) if direction == "long" else not (o < pl)
    hb = _window(today, *config.PARK_COMMIT_HOUR_ET)
    if len(hb) >= config.PARK_COMMIT_MIN_HOUR_BARS:
        ho, hc = hb[0][0], hb[-1][3]
        hh, hl = max(x[1] for x in hb), min(x[2] for x in hb)
        rng = hh - hl
        if rng > 0:
            wick = (hh - max(ho, hc)) if direction == "long" else (min(ho, hc) - hl)
            out["wick"] = wick / rng
            out["reject"] = wick / rng >= config.PARK_COMMIT_WICK

    def vol(bars):
        v = [x[4] for x in _window(bars, *config.PARK_COMMIT_PART_ET)]
        if len(v) < config.PARK_COMMIT_MIN_PART_BARS or any(x is None for x in v):
            return None
        s = sum(v)
        return s if s > 0 else None
    vt = vol(today)
    vp = [x for x in (vol(p) for p in prior[:config.PARK_COMMIT_LOOKBACK]) if x]
    if vt and len(vp) >= config.PARK_COMMIT_MIN_PRIOR:
        ratio = vt / statistics.median(vp)
        out["part_ratio"] = ratio
        lo, hi = config.PARK_COMMIT_PART_SANE
        if lo <= ratio <= hi:
            out["part"] = ratio < config.PARK_COMMIT_PART_MIN
    return out


def against_count(lv: dict) -> int:
    return sum(1 for k in ("range", "reject", "part") if lv.get(k) is True)


def commitment_gate(name_sess: dict, pair_sess: dict, direction: str) -> dict:
    """THE GATE, pure. `direction` is PARK's own (the name's first-hour sign). Returns the pair's move, pair_agrees, the
    leans and AGAINST counts on each name, `commitment` (fewer than PARK_COMMIT_SKIP against on BOTH) and `passes`
    (pair_agrees and commitment). `short` lists what made either tape unreadable - non-empty means the caller STARVES
    (fails closed) and `passes` is False."""
    short = ["name: " + s for s in tape_short(name_sess)] + ["pair: " + s for s in tape_short(pair_sess)]
    r = read_name(name_sess.get("today") or {}, name_sess.get("prior") or [])
    rp = read_name(pair_sess.get("today") or {}, pair_sess.get("prior") or [])
    pm = rp["move_pct"]
    agrees = (direction in ("long", "short") and pm is not None and abs(pm) >= config.PARK_MOVE_PCT
              and (pm > 0) == (direction == "long"))
    lv = leans(r, name_sess.get("today") or {}, name_sess.get("prior") or [], direction)
    lvp = leans(rp, pair_sess.get("today") or {}, pair_sess.get("prior") or [], direction)
    a, b = against_count(lv), against_count(lvp)
    commit = a < config.PARK_COMMIT_SKIP and b < config.PARK_COMMIT_SKIP
    return dict(pair_move_pct=pm, pair_agrees=bool(agrees), leans=lv, pair_leans=lvp, against=a, pair_against=b,
                commitment=bool(commit), short=short, passes=bool(agrees and commit and not short))


def commitment_read(t, cond, *, symbol: str, day, direction: str) -> bool:
    """Narrate the gate on tick `t` (equities only; the caller checks is_index). Returns True when the plan may go on to
    the contract, False when it must stop: STARVED (a tape too thin - fails closed, said on `t`), or the two conditions
    are written through `cond` (pair_agrees, commitment) and the caller's unmet list refuses."""
    pair = str(config.PARK_PAIR_SYMBOL)
    ns, ps = session_bars(symbol, day), session_bars(pair, day)
    st = _tape_state(day)
    for who, s in (("name", ns), ("pair", ps)):
        if isinstance(s, str):
            t.note(s)
            t.starved("commit_bars_" + who)
            logger.warning("[park] commitment gate STARVED on %s: %s - no PARK on this equity (fails closed)",
                           symbol, s)
            st["starved"] = True
            _page_once(day, "starved", "⚠️ PARK on %s: the commitment gate cannot read its tape (%s). Re-checking every "
                       "tick to %s ET; no trade if it is still short." % (symbol, s, _window_end()))
            return False
    g = commitment_gate(ns, ps, direction)
    t.check("is_index", 0, None)
    t.check("pair_move_pct", g["pair_move_pct"], None)
    for pre, lv, n in (("", g["leans"], g["against"]), ("pair_", g["pair_leans"], g["pair_against"])):
        t.check(pre + "lean_range", lv["range_edge"], None if lv["range"] is None else not lv["range"])
        t.check(pre + "lean_reject", lv["wick"], None if lv["reject"] is None else not lv["reject"])
        t.check(pre + "lean_part", lv["part_ratio"], None if lv["part"] is None else not lv["part"])
        t.check(pre + "against", n, None)
    if g["short"]:
        t.note("commitment gate: tape too thin - " + "; ".join(g["short"]))
        t.starved("commit_tape")
        logger.warning("[park] commitment gate STARVED on %s: %s - no PARK on this equity (fails closed)",
                       symbol, "; ".join(g["short"]))
        st["starved"] = True
        _page_once(day, "starved", "⚠️ PARK on %s: the commitment gate's tape is too thin - %s. The candle feed is "
                   "re-pulling it; re-checking every tick to %s ET, no trade if still short."
                   % (symbol, "; ".join(g["short"][:4]), _window_end()))
        return False
    if st["starved"] and not st["recovered"]:
        st["recovered"] = True
        logger.warning("[park] commitment gate tape RECOVERED on %s inside the window - the gate reads normally",
                       symbol)
    cond("pair_agrees", g["pair_move_pct"], g["pair_agrees"],
         note="" if g["pair_agrees"] else "%s first hour %s, not >= %.2f%% the %s way" % (
             pair, "unread" if g["pair_move_pct"] is None else "%+.3f%%" % g["pair_move_pct"],
             config.PARK_MOVE_PCT, direction))
    cond("commitment", max(g["against"], g["pair_against"]), g["commitment"],
         note="" if g["commitment"] else "%d of 3 leans against on %s, %d on %s (skip at %d)" % (
             g["against"], symbol, g["pair_against"], pair, config.PARK_COMMIT_SKIP))
    return True


def _record_would_fire(prep) -> None:
    """PARK_MODE=log: what PARK would have bought. data/counterfactual/park_signal.jsonl. Never raises."""
    try:
        import json, os, time
        d = os.environ.get("OT_COUNTERFACTUAL_DIR") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "counterfactual")
        os.makedirs(d, exist_ok=True)
        c = prep.contract
        row = {"ts_epoch": time.time(), "rule": "park_signal", "mode": config.PARK_MODE,
               "direction": prep.direction, "move_pct": prep.move_pct, "gap": prep.gap,
               "strike": float(getattr(c, "strike", 0) or 0), "side": prep.side,
               "streamer_symbol": getattr(c, "streamer_symbol", ""), "ask": prep.ask,
               "bid": prep.bid, "mark": prep.premium, "spot_1100": prep.spot}
        with open(os.path.join(d, "park_signal.jsonl"), "a") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("[park] signal counterfactual row NOT written: %s", exc)


class ParkPreparation:
    """What the search found. `ready` is True ONLY when every bar cleared."""

    __slots__ = ("tick", "spec", "conditions", "unmet", "ready", "direction", "side", "move_pct", "gap",
                 "spot", "contract", "premium", "price_now", "bid", "ask")

    def __init__(self, tick, spec):
        self.tick, self.spec = tick, spec
        self.conditions, self.unmet = {}, []
        self.ready = False
        self.direction = self.side = ""
        self.move_pct = self.gap = self.spot = None
        self.contract = self.premium = self.price_now = None
        self.bid = self.ask = None              # v5.2: the quote the mark was taken from

    def cond(self, name, current, met, note: str = ""):
        required = self.spec.CONDITIONS.get(name, "")
        self.conditions[name] = (current, required, bool(met))
        if not met:
            self.unmet.append(name)
        self.tick.check(name, current if isinstance(current, (int, float)) else None, bool(met), note=note)

    def trade_line(self) -> str:
        if not self.ready:
            return "no trade prepared"
        return (f"buy {float(self.contract.strike):g}{self.side[0].upper()} @ {self.premium:.2f} (mark, bid/ask {self.bid:.2f}/{self.ask:.2f}) - first "
                f"hour {self.move_pct:+.3f}%, gap {self.gap:+.2f}; exits: lock +{config.PARK_LOCK_ARM:.0%}/"
                f"+{config.PARK_LOCK_FLOOR:.0%}, |delta| <= {config.PARK_DELTA_FLOOR:.2f} from "
                f"{config.PARK_DELTA_FROM_ET[0]:02d}:{config.PARK_DELTA_FROM_ET[1]:02d}, else "
                f"{config.PARK_CLOSE_ET[0]:02d}:{config.PARK_CLOSE_ET[1]:02d}")

    def record_would_fire(self) -> None:
        _record_would_fire(self)

    def emit(self, strategy_name: str):
        """Build the signal from what the PLAN selected. The strategy picks nothing."""
        from strategy.base_strategy import OptionsSignal as Signal
        c = self.contract
        sig = Signal(
            strategy_name=strategy_name,
            setup_type=f"park_{self.direction}",
            direction=self.direction,
            option_side=self.side,
            underlying_entry=float(self.price_now or self.spot),
            underlying_stop=0.0,                 # no structure stop: PARK's exits are its own
            underlying_target=0.0,
            strike=c.strike, expiry=getattr(c, "expiry", ""),
            entry_premium=float(self.premium),   # THE MARK (v5.2; was the ask)
            contract=c,
            entry_delta=getattr(c, "delta", None),
            stop_loss_pct=1.0,                   # no premium stop (stop_premium = 0)
        )
        logger.info("[park] FIRE %s — %s", self.direction, self.trade_line())
        return self.tick.take(sig)


def _window_end() -> str:
    try:
        return "%02d:%02d" % tuple(config.ENTRY_WINDOWS["PARK"][1])
    except Exception:                                           # noqa: BLE001
        return "the window's end"


class ParkPlan:
    name = "PARK"

    def __init__(self):
        from strategy.park import Park as _Spec
        self.planner = Plan(self.name, _Spec.PLAN_CHECKS, self_ledgers=True)

    @staticmethod
    def _symbol() -> str:
        try:
            return str(getattr(config, "INSTRUMENT", "") or "")
        except Exception:                                       # noqa: BLE001
            return ""

    def prepare(self, *, spec, price_now, now_et, chain=None, prior_close=None, day=None,
                symbol: str = "", **_ignored) -> ParkPreparation:
        from strategy import park as P

        t = self.planner.tick(price_now)
        prep = ParkPreparation(t, spec)
        prep.price_now = _f(price_now)

        # ── the window. DORMANT writes one row and goes quiet ──────────────
        hm, lo, hi = _hm(now_et), _hm(P.EARLIEST_ET), _hm(P.LATEST_ET)
        # v5.5 — before the window: watch an equity's two tapes from 10:00 and page the first gap (no row written);
        # after it: a window that ended still STARVED pages once (the trade was refused for the tape, not the market).
        _sym0 = symbol or self._symbol()
        if hm is not None and _sym0 and not is_index(_sym0):
            if day is None:
                from utils.time_utils import now_et as _now0
                day = _now0().date()
            _w0, _w1 = config.PARK_TAPE_WATCH_ET
            if tuple(_w0) <= tuple(hm) < tuple(_w1) and (lo is None or tuple(hm) < tuple(lo)):
                watch_tape(_sym0, day, hm)
            if hi is not None and tuple(hm) >= tuple(hi):
                _st0 = _tape_state(day)
                if _st0["starved"] and not _st0["recovered"]:
                    _page_once(day, "closed", "⚠️ PARK on %s FAILED CLOSED: the commitment gate's tape was still short "
                               "at %s ET - no PARK today on this box." % (_sym0, P.LATEST_ET))
        if hm is None or lo is None or hi is None or not (lo <= hm < hi):
            t.dormant("entry_window", f"outside {P.EARLIEST_ET}-{P.LATEST_ET} ET")
            return prep
        prep.cond("entry_window", None, True)

        # ── the first hour, from the store (r46: one read) ──
        if day is None:
            from utils.time_utils import now_et as _now
            day = _now().date()
        sym = symbol or self._symbol()
        fh = read_first_hour(t, prep.cond, symbol=sym, day=day, prior_close=prior_close)
        if fh is None:
            return prep
        spot = fh["spot"]
        prep.move_pct, prep.spot = fh["move_pct"], spot
        direction = fh["direction"]
        prep.direction = direction
        prep.side = "call" if direction == "long" else "put" if direction == "short" else ""
        prep.gap = fh["gap"]
        # r90 (SHADOW.1) - LOG ONLY: the daily SMA 50 slope's verdict, on every tick that reached a direction (before
        # GATE-G / the commitment gate / the contract can refuse it). Never decides, never raises.
        from strategy import shadow_rules as _shadow
        _shadow.record_park(t, symbol=sym, day=day, direction=direction, index=is_index(sym))
        if prep.unmet:
            t.refuse(prep.unmet[0], "not this session — " + ", ".join(prep.unmet))
            return prep

        # ── v5.4 (PARK.5): an equity also needs the market's commitment; an index never asks ──
        if not is_index(sym):
            if not commitment_read(t, prep.cond, symbol=sym, day=day, direction=direction):
                return prep                                     # STARVED: fails closed, said on the row
            if prep.unmet:
                t.refuse(prep.unmet[0], "not this session — " + ", ".join(prep.unmet))
                return prep

        # ── v5.7 (C8.1): the first hour already outrun. Index and equity alike; asked AFTER the r90 shadow row (so
        # PARK_SMA50 still writes on every directional tick C8 skips) and after the commitment gate (whose fail-closed
        # tape pages are unchanged), before the contract. ──
        c8_read(t, prep.cond, symbol=sym, day=day, direction=direction)
        if prep.unmet:
            t.refuse(prep.unmet[0], "not this session — " + ", ".join(prep.unmet))
            return prep

        # ── the contract ──────────────────────────────────────────────────
        rows = (getattr(chain, "calls", None) if direction == "long" else getattr(chain, "puts", None)) or []
        if chain is None or not rows:
            t.starved("chain")
            return prep
        best = None
        for k in rows:
            s = _f(getattr(k, "strike", None))
            if s is None:
                continue
            key = (abs(s - spot), s)
            if best is None or key < best[0]:
                best = (key, k)
        k = best[1] if best else None
        bid, ask = (_f(getattr(k, "bid", None)), _f(getattr(k, "ask", None))) if k is not None else (None, None)
        t.check("strike", _f(getattr(k, "strike", None)) if k is not None else None, None)
        t.check("ask", ask, None)
        t.check("bid", bid, None)
        t.check("delta", _f(getattr(k, "delta", None)) if k is not None else None, None)
        ok = (k is not None and bid is not None and ask is not None and ask >= bid > 0
              and ask >= MIN_ASK)
        prep.cond("contract", ask, ok,
                  note="" if ok else "no two-sided ATM contract with ask >= %.2f" % config.PARK_MIN_ASK)
        if not ok:
            t.refuse("contract", "no two-sided ATM contract with ask >= %.2f" % config.PARK_MIN_ASK)
            return prep
        # v5.2 (PARK.4) - THE MARK, NOT THE ASK. The operator, 2026-10-30: "we ladder in from aggressive to mark &
        # never worse than mark". (bid + ask) / 2 - the mark data/options_chain and the entry ladder use - FLOORED TO
        # THE CENT, as entry_engine._mark_cap prices the most a buy may post (r224 FLY.1): the raw 1.265 is
        # 1.2650000000000001 in float and limit_at_mark's round(px, 2) booked it 1.27, a half-cent ABOVE the mark.
        prep.contract, prep.bid, prep.ask = k, bid, ask
        prep.premium = int((bid + ask) / 2.0 * 100.0 + 1e-9) / 100.0
        prep.ready = True
        t.anchor(trigger=spot)
        return prep
