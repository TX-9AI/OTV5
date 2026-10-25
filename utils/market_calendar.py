#!/usr/bin/env python3
"""
utils/market_calendar.py  v5.0
v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
v1.3  2026-10-11  OTV4TEST r268 (mirror of otv4 r478) / DEP.12 - EARLY CLOSES. EARLY_CLOSES (52 sessions,
2026-2050, generated from the NYSE rules and identical to dtp's list),
close_time(), is_half_day(), close_shift_minutes(). Nothing here changes
is_trading_day(); a half day stays a trading day. Fails toward a FULL day.
v1.2  2026-09-07  r310 - THE HORIZON GOES TO 2050. Operator's call once the
2035 boundary was named as the arbitrary prior it was: the list is GENERATED
and the oracle verifies every date, so extending it costs bytes and nothing
else. 250 closures. The only exposure is a RULES change - Juneteenth was added
in 2022 - making later years wrong, and that fails toward TRADING. D3's
five-years-ahead assertion stops being something anyone has to think about.
v1.1  2026-09-07  r307 / DEP.13 - THE STANDARD CLOSURES ARE HARDCODED THROUGH
2035 AND VERIFIED AGAINST THE RULES THAT PRODUCE THEM. The list previously ran
to 2027, so 2028 was a cliff: every unlisted weekday reads as a session, which
fails safe but would have armed the fleet on ten closed days a year until
someone noticed. Operator: hardcode the standard days, account for one-offs by
hand. Generated from the NYSE rules OFFLINE and pinned by a checker that
regenerates them - verified arithmetic, not trusted transcription, and no rule
evaluation on the live path. AD_HOC_CLOSURES is the hand-maintained override
for the closures no algorithm can produce.
v1.0  2026-09-07  r304 / DEP.9 — ONE HOLIDAY CALENDAR FOR THE WHOLE PROGRAM.

Surfaced 2026-09-07, Labor Day: the market was shut, the orchestrator and the
morning brief knew it, the bots were correctly left down — and devtools item 35
refused a bake as *"inside RTH"*. Two clocks, one question, and only one
consulted a calendar. `utils/time_utils.is_rth()` tested `weekday() >= 5` and a
09:30–16:00 window, nothing else, and `entries_open()` wraps it — which r102
made the universal floor every order site sits behind. **On a market holiday
the trading path believed the market was open.**

🔴 THE FAIL-SAFE DIRECTION IS THE OPPOSITE OF `shadow/trading_day.py`'s, AND
THAT IS THE MOST IMPORTANT LINE IN THIS FILE. That module's own header reasons:
*"a wrong 'holiday' just means shadow doesn't observe that day (no harm); a
missed holiday means it observes an empty tape (harmless noise), never a
trade."* For the TRADING clock the asymmetry inverts:

  · a WRONG holiday — a real session listed here — means THE FLEET DOES NOT
    TRADE. Silent, total, and it looks exactly like a quiet tape.
  · a MISSED holiday means the fleet is armed against a closed market. No
    data arrives, no order fills, and the blind-alert fires. Harmless.

**So this must fail toward TRADING, always.** An unlisted date is a trading
day. There is deliberately NO expiry guard that starts refusing once the list
runs out: a forgotten refresh must cost a few pointless armed mornings, never
a silent dark fleet. `coverage()` exists so staleness is VISIBLE instead of
being enforced.

⚠️ THIS IS THE ONLY HOLIDAY LIST IN otv4. `shadow/trading_day.py` imports it
rather than keeping its own — that copy is where these dates came from, and two
lists meaning one thing is the drift this repo keeps finding. day_trader_pro
has its own `market_calendar.py` on the control side; the repos cannot import
each other, so they are two copies by necessity, and DEP.11 records the
obligation to refresh both together.

⚠️ HALF DAYS ARE TRADING DAYS, and since r478 (DEP.12) they are MODELLED:
EARLY_CLOSES lists the 13:00 sessions, close_time()/close_shift_minutes() say
when the bell rings, and utils/time_utils.close_anchored() moves every
close-anchored constant to it. Before r478 nothing shortened the session, so
the 15:40 flatten and 15:45 cross would have fired ~3 h after a 13:00 bell.

Run:  python3 utils/market_calendar.py            # today's verdict
      python3 utils/market_calendar.py --selftest
"""
from __future__ import annotations

import datetime as _dt
import sys
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# NYSE full-day closes (observed dates). Refresh each year — see coverage().
# ── THE STANDARD CLOSURES, HARDCODED THROUGH 2050 ───────────────────────────
# Operator, 2026-09-07: *"If we know the standard days, then hard code them. I
# can manually account for 1-offs."*
#
# 🔑 THESE WERE GENERATED FROM THE NYSE RULES, NOT TYPED. Nine of the ten are
# fixed-date or nth-weekday; Good Friday is Easter minus two, and Easter has an
# exact closed form. `tests/check_market_calendar.py` REGENERATES this set from
# those rules and fails if a single date disagrees - so the list is verified
# arithmetic rather than trusted transcription, and the rules never run on a
# box.
#
# ⚠️ THE OBSERVANCE RULE IS NYSE'S, NOT THE FEDERAL ONE, and they differ:
# Columbus Day and Veterans Day are federal holidays and the exchange TRADES.
# Anything sourced from a generic `holidays` package would close on both. That
# is the concrete reason these are written out.
#
# ⚠️ NOTE 2027-12-31: New Year's Day 2028 falls on a Saturday, so the observed
# close lands in the PREVIOUS year. A list organised by year is exactly where
# that gets missed; it is generated, so it is not.
#
# ⚠️ AD-HOC CLOSURES ARE NOT HERE AND CANNOT BE COMPUTED - presidential
# funerals (Carter 2025-01-09, Bush 2018-12-05), 9/11, Hurricane Sandy. They
# are announced days or weeks ahead. Add them to AD_HOC_CLOSURES below by hand;
# that is the operator's job by his own ruling, and it is the only part of this
# file that will ever need touching before 2051.
US_MARKET_HOLIDAYS = {
    # 2026
    "2026-01-01",  # New Year's Day
    "2026-01-19",  # MLK Jr. Day
    "2026-02-16",  # Presidents' Day
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day
    "2026-06-19",  # Juneteenth
    "2026-07-03",  # Independence Day (observed)
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving
    "2026-12-25",  # Christmas
    # 2027
    "2027-01-01",  # New Year's Day
    "2027-01-18",  # MLK Jr. Day
    "2027-02-15",  # Presidents' Day
    "2027-03-26",  # Good Friday
    "2027-05-31",  # Memorial Day
    "2027-06-18",  # Juneteenth (observed)
    "2027-07-05",  # Independence Day (observed)
    "2027-09-06",  # Labor Day
    "2027-11-25",  # Thanksgiving
    "2027-12-24",  # Christmas (observed)
    # 2028
    "2027-12-31",  # New Year's Day (observed)
    "2028-01-17",  # MLK Jr. Day
    "2028-02-21",  # Presidents' Day
    "2028-04-14",  # Good Friday
    "2028-05-29",  # Memorial Day
    "2028-06-19",  # Juneteenth
    "2028-07-04",  # Independence Day
    "2028-09-04",  # Labor Day
    "2028-11-23",  # Thanksgiving
    "2028-12-25",  # Christmas
    # 2029
    "2029-01-01",  # New Year's Day
    "2029-01-15",  # MLK Jr. Day
    "2029-02-19",  # Presidents' Day
    "2029-03-30",  # Good Friday
    "2029-05-28",  # Memorial Day
    "2029-06-19",  # Juneteenth
    "2029-07-04",  # Independence Day
    "2029-09-03",  # Labor Day
    "2029-11-22",  # Thanksgiving
    "2029-12-25",  # Christmas
    # 2030
    "2030-01-01",  # New Year's Day
    "2030-01-21",  # MLK Jr. Day
    "2030-02-18",  # Presidents' Day
    "2030-04-19",  # Good Friday
    "2030-05-27",  # Memorial Day
    "2030-06-19",  # Juneteenth
    "2030-07-04",  # Independence Day
    "2030-09-02",  # Labor Day
    "2030-11-28",  # Thanksgiving
    "2030-12-25",  # Christmas
    # 2031
    "2031-01-01",  # New Year's Day
    "2031-01-20",  # MLK Jr. Day
    "2031-02-17",  # Presidents' Day
    "2031-04-11",  # Good Friday
    "2031-05-26",  # Memorial Day
    "2031-06-19",  # Juneteenth
    "2031-07-04",  # Independence Day
    "2031-09-01",  # Labor Day
    "2031-11-27",  # Thanksgiving
    "2031-12-25",  # Christmas
    # 2032
    "2032-01-01",  # New Year's Day
    "2032-01-19",  # MLK Jr. Day
    "2032-02-16",  # Presidents' Day
    "2032-03-26",  # Good Friday
    "2032-05-31",  # Memorial Day
    "2032-06-18",  # Juneteenth (observed)
    "2032-07-05",  # Independence Day (observed)
    "2032-09-06",  # Labor Day
    "2032-11-25",  # Thanksgiving
    "2032-12-24",  # Christmas (observed)
    # 2033
    "2032-12-31",  # New Year's Day (observed)
    "2033-01-17",  # MLK Jr. Day
    "2033-02-21",  # Presidents' Day
    "2033-04-15",  # Good Friday
    "2033-05-30",  # Memorial Day
    "2033-06-20",  # Juneteenth (observed)
    "2033-07-04",  # Independence Day
    "2033-09-05",  # Labor Day
    "2033-11-24",  # Thanksgiving
    "2033-12-26",  # Christmas (observed)
    # 2034
    "2034-01-02",  # New Year's Day (observed)
    "2034-01-16",  # MLK Jr. Day
    "2034-02-20",  # Presidents' Day
    "2034-04-07",  # Good Friday
    "2034-05-29",  # Memorial Day
    "2034-06-19",  # Juneteenth
    "2034-07-04",  # Independence Day
    "2034-09-04",  # Labor Day
    "2034-11-23",  # Thanksgiving
    "2034-12-25",  # Christmas
    # 2035
    "2035-01-01",  # New Year's Day
    "2035-01-15",  # MLK Jr. Day
    "2035-02-19",  # Presidents' Day
    "2035-03-23",  # Good Friday
    "2035-05-28",  # Memorial Day
    "2035-06-19",  # Juneteenth
    "2035-07-04",  # Independence Day
    "2035-09-03",  # Labor Day
    "2035-11-22",  # Thanksgiving
    "2035-12-25",  # Christmas
    # 2036
    "2036-01-01",  # New Year's Day
    "2036-01-21",  # MLK Jr. Day
    "2036-02-18",  # Presidents' Day
    "2036-04-11",  # Good Friday
    "2036-05-26",  # Memorial Day
    "2036-06-19",  # Juneteenth
    "2036-07-04",  # Independence Day
    "2036-09-01",  # Labor Day
    "2036-11-27",  # Thanksgiving
    "2036-12-25",  # Christmas
    # 2037
    "2037-01-01",  # New Year's Day
    "2037-01-19",  # MLK Jr. Day
    "2037-02-16",  # Presidents' Day
    "2037-04-03",  # Good Friday
    "2037-05-25",  # Memorial Day
    "2037-06-19",  # Juneteenth
    "2037-07-03",  # Independence Day (observed)
    "2037-09-07",  # Labor Day
    "2037-11-26",  # Thanksgiving
    "2037-12-25",  # Christmas
    # 2038
    "2038-01-01",  # New Year's Day
    "2038-01-18",  # MLK Jr. Day
    "2038-02-15",  # Presidents' Day
    "2038-04-23",  # Good Friday
    "2038-05-31",  # Memorial Day
    "2038-06-18",  # Juneteenth (observed)
    "2038-07-05",  # Independence Day (observed)
    "2038-09-06",  # Labor Day
    "2038-11-25",  # Thanksgiving
    "2038-12-24",  # Christmas (observed)
    # 2039
    "2038-12-31",  # New Year's Day (observed)
    "2039-01-17",  # MLK Jr. Day
    "2039-02-21",  # Presidents' Day
    "2039-04-08",  # Good Friday
    "2039-05-30",  # Memorial Day
    "2039-06-20",  # Juneteenth (observed)
    "2039-07-04",  # Independence Day
    "2039-09-05",  # Labor Day
    "2039-11-24",  # Thanksgiving
    "2039-12-26",  # Christmas (observed)
    # 2040
    "2040-01-02",  # New Year's Day (observed)
    "2040-01-16",  # MLK Jr. Day
    "2040-02-20",  # Presidents' Day
    "2040-03-30",  # Good Friday
    "2040-05-28",  # Memorial Day
    "2040-06-19",  # Juneteenth
    "2040-07-04",  # Independence Day
    "2040-09-03",  # Labor Day
    "2040-11-22",  # Thanksgiving
    "2040-12-25",  # Christmas
    # 2041
    "2041-01-01",  # New Year's Day
    "2041-01-21",  # MLK Jr. Day
    "2041-02-18",  # Presidents' Day
    "2041-04-19",  # Good Friday
    "2041-05-27",  # Memorial Day
    "2041-06-19",  # Juneteenth
    "2041-07-04",  # Independence Day
    "2041-09-02",  # Labor Day
    "2041-11-28",  # Thanksgiving
    "2041-12-25",  # Christmas
    # 2042
    "2042-01-01",  # New Year's Day
    "2042-01-20",  # MLK Jr. Day
    "2042-02-17",  # Presidents' Day
    "2042-04-04",  # Good Friday
    "2042-05-26",  # Memorial Day
    "2042-06-19",  # Juneteenth
    "2042-07-04",  # Independence Day
    "2042-09-01",  # Labor Day
    "2042-11-27",  # Thanksgiving
    "2042-12-25",  # Christmas
    # 2043
    "2043-01-01",  # New Year's Day
    "2043-01-19",  # MLK Jr. Day
    "2043-02-16",  # Presidents' Day
    "2043-03-27",  # Good Friday
    "2043-05-25",  # Memorial Day
    "2043-06-19",  # Juneteenth
    "2043-07-03",  # Independence Day (observed)
    "2043-09-07",  # Labor Day
    "2043-11-26",  # Thanksgiving
    "2043-12-25",  # Christmas
    # 2044
    "2044-01-01",  # New Year's Day
    "2044-01-18",  # MLK Jr. Day
    "2044-02-15",  # Presidents' Day
    "2044-04-15",  # Good Friday
    "2044-05-30",  # Memorial Day
    "2044-06-20",  # Juneteenth (observed)
    "2044-07-04",  # Independence Day
    "2044-09-05",  # Labor Day
    "2044-11-24",  # Thanksgiving
    "2044-12-26",  # Christmas (observed)
    # 2045
    "2045-01-02",  # New Year's Day (observed)
    "2045-01-16",  # MLK Jr. Day
    "2045-02-20",  # Presidents' Day
    "2045-04-07",  # Good Friday
    "2045-05-29",  # Memorial Day
    "2045-06-19",  # Juneteenth
    "2045-07-04",  # Independence Day
    "2045-09-04",  # Labor Day
    "2045-11-23",  # Thanksgiving
    "2045-12-25",  # Christmas
    # 2046
    "2046-01-01",  # New Year's Day
    "2046-01-15",  # MLK Jr. Day
    "2046-02-19",  # Presidents' Day
    "2046-03-23",  # Good Friday
    "2046-05-28",  # Memorial Day
    "2046-06-19",  # Juneteenth
    "2046-07-04",  # Independence Day
    "2046-09-03",  # Labor Day
    "2046-11-22",  # Thanksgiving
    "2046-12-25",  # Christmas
    # 2047
    "2047-01-01",  # New Year's Day
    "2047-01-21",  # MLK Jr. Day
    "2047-02-18",  # Presidents' Day
    "2047-04-12",  # Good Friday
    "2047-05-27",  # Memorial Day
    "2047-06-19",  # Juneteenth
    "2047-07-04",  # Independence Day
    "2047-09-02",  # Labor Day
    "2047-11-28",  # Thanksgiving
    "2047-12-25",  # Christmas
    # 2048
    "2048-01-01",  # New Year's Day
    "2048-01-20",  # MLK Jr. Day
    "2048-02-17",  # Presidents' Day
    "2048-04-03",  # Good Friday
    "2048-05-25",  # Memorial Day
    "2048-06-19",  # Juneteenth
    "2048-07-03",  # Independence Day (observed)
    "2048-09-07",  # Labor Day
    "2048-11-26",  # Thanksgiving
    "2048-12-25",  # Christmas
    # 2049
    "2049-01-01",  # New Year's Day
    "2049-01-18",  # MLK Jr. Day
    "2049-02-15",  # Presidents' Day
    "2049-04-16",  # Good Friday
    "2049-05-31",  # Memorial Day
    "2049-06-18",  # Juneteenth (observed)
    "2049-07-05",  # Independence Day (observed)
    "2049-09-06",  # Labor Day
    "2049-11-25",  # Thanksgiving
    "2049-12-24",  # Christmas (observed)
    # 2050
    "2049-12-31",  # New Year's Day (observed)
    "2050-01-17",  # MLK Jr. Day
    "2050-02-21",  # Presidents' Day
    "2050-04-08",  # Good Friday
    "2050-05-30",  # Memorial Day
    "2050-06-20",  # Juneteenth (observed)
    "2050-07-04",  # Independence Day
    "2050-09-05",  # Labor Day
    "2050-11-24",  # Thanksgiving
    "2050-12-26",  # Christmas (observed)
}
# One-off exchange closures. Hand-maintained, by operator ruling.
# ⚠️ ADDING A DATE HERE CLOSES THE MARKET FOR THE FLEET. A wrong entry means
# the fleet does not trade that day - silent, and it looks exactly like a quiet
# tape. Get the date right; the fail-open guarantee does not protect you here,
# because this set is an explicit close.
AD_HOC_CLOSURES: set = set()

US_MARKET_HOLIDAYS |= AD_HOC_CLOSURES

def coverage() -> tuple:
    """(first_year, last_year) the list actually covers."""
    years = sorted({int(d[:4]) for d in US_MARKET_HOLIDAYS})
    return (years[0], years[-1]) if years else (0, 0)


def is_covered(d: _dt.date | None = None) -> bool:
    """Is this date inside the years the list knows about?

    ⚠️ A CALLER MAY REPORT THIS. NOTHING MAY REFUSE ON IT. See the header:
    refusing outside coverage would turn a forgotten refresh into a dark fleet.
    """
    d = d or _dt.datetime.now(ET).date()
    lo, hi = coverage()
    return lo <= d.year <= hi


def is_trading_day(d: _dt.date | None = None) -> bool:
    """True if the US equity market holds a full or half session on `d`.

    Weekends are closed. Listed holidays are closed. EVERYTHING ELSE IS OPEN —
    including dates beyond the list's coverage, deliberately.
    """
    d = d or _dt.datetime.now(ET).date()
    if d.weekday() >= 5:
        return False
    return d.isoformat() not in US_MARKET_HOLIDAYS


# ── EARLY CLOSES — r478 / DEP.12 ────────────────────────────────────────────
# The 13:00 ET sessions. GENERATED from the NYSE rules, like the closures above,
# and `tests/check_market_calendar.py` regenerates them (C6/C7) and diffs them
# against day_trader_pro's EARLY_CLOSES (C8), the control-side copy that has
# driven the morning brief's half-day banner since dtp r319.
#   · the day after Thanksgiving, always;
#   · July 3 when July 4 falls Tue-Fri (Sat: Jul 3 is the holiday itself;
#     Sun/Mon: no early close);
#   · December 24 when it falls Mon-Thu (Fri: it is the observed Christmas).
#
# ⚠️ THE FAIL-SAFE DIRECTION IS A FULL DAY. An unlisted half day runs the
# 16:00 clock, which is exactly the behaviour before r478. A date wrongly
# PRESENT flattens a full session three hours early — so this list is verified
# arithmetic, never hand-typed.
# Value = the close as "HH:MM" ET, so a future close other than 13:00 is one
# entry, and close_shift_minutes() derives from it rather than assuming 3 h.
EARLY_CLOSES: dict = {
    "2026-11-27": "13:00",  # day after Thanksgiving
    "2026-12-24": "13:00",  # Christmas Eve
    "2027-11-26": "13:00",  # day after Thanksgiving
    "2028-07-03": "13:00",  # July 3
    "2028-11-24": "13:00",  # day after Thanksgiving
    "2029-07-03": "13:00",  # July 3
    "2029-11-23": "13:00",  # day after Thanksgiving
    "2029-12-24": "13:00",  # Christmas Eve
    "2030-07-03": "13:00",  # July 3
    "2030-11-29": "13:00",  # day after Thanksgiving
    "2030-12-24": "13:00",  # Christmas Eve
    "2031-07-03": "13:00",  # July 3
    "2031-11-28": "13:00",  # day after Thanksgiving
    "2031-12-24": "13:00",  # Christmas Eve
    "2032-11-26": "13:00",  # day after Thanksgiving
    "2033-11-25": "13:00",  # day after Thanksgiving
    "2034-07-03": "13:00",  # July 3
    "2034-11-24": "13:00",  # day after Thanksgiving
    "2035-07-03": "13:00",  # July 3
    "2035-11-23": "13:00",  # day after Thanksgiving
    "2035-12-24": "13:00",  # Christmas Eve
    "2036-07-03": "13:00",  # July 3
    "2036-11-28": "13:00",  # day after Thanksgiving
    "2036-12-24": "13:00",  # Christmas Eve
    "2037-11-27": "13:00",  # day after Thanksgiving
    "2037-12-24": "13:00",  # Christmas Eve
    "2038-11-26": "13:00",  # day after Thanksgiving
    "2039-11-25": "13:00",  # day after Thanksgiving
    "2040-07-03": "13:00",  # July 3
    "2040-11-23": "13:00",  # day after Thanksgiving
    "2040-12-24": "13:00",  # Christmas Eve
    "2041-07-03": "13:00",  # July 3
    "2041-11-29": "13:00",  # day after Thanksgiving
    "2041-12-24": "13:00",  # Christmas Eve
    "2042-07-03": "13:00",  # July 3
    "2042-11-28": "13:00",  # day after Thanksgiving
    "2042-12-24": "13:00",  # Christmas Eve
    "2043-11-27": "13:00",  # day after Thanksgiving
    "2043-12-24": "13:00",  # Christmas Eve
    "2044-11-25": "13:00",  # day after Thanksgiving
    "2045-07-03": "13:00",  # July 3
    "2045-11-24": "13:00",  # day after Thanksgiving
    "2046-07-03": "13:00",  # July 3
    "2046-11-23": "13:00",  # day after Thanksgiving
    "2046-12-24": "13:00",  # Christmas Eve
    "2047-07-03": "13:00",  # July 3
    "2047-11-29": "13:00",  # day after Thanksgiving
    "2047-12-24": "13:00",  # Christmas Eve
    "2048-11-27": "13:00",  # day after Thanksgiving
    "2048-12-24": "13:00",  # Christmas Eve
    "2049-11-26": "13:00",  # day after Thanksgiving
    "2050-11-25": "13:00",  # day after Thanksgiving
}

RTH_CLOSE_HM = (16, 0)   # the full-session bell every close-anchored constant assumes


def close_time(d: _dt.date | None = None) -> _dt.time:
    """The session's closing bell: the listed early close, else 16:00."""
    d = d or _dt.datetime.now(ET).date()
    hm = EARLY_CLOSES.get(d.isoformat()) if is_trading_day(d) else None
    if hm:
        h, m = (int(x) for x in hm.split(":"))
        return _dt.time(h, m)
    return _dt.time(*RTH_CLOSE_HM)


def is_half_day(d: _dt.date | None = None) -> bool:
    """True on a listed early close. A half day is a TRADING day."""
    c = close_time(d)
    return (c.hour, c.minute) != RTH_CLOSE_HM


def close_shift_minutes(d: _dt.date | None = None) -> int:
    """Minutes the bell is EARLY versus 16:00: 180 on a 13:00 day, else 0.

    🔑 Every close-anchored constant in the tree (15:40 flatten, 15:45 cross
    and credit hold, 15:50 watchdog, 16:00 bell) is written against a 16:00
    bell; on an early close each moves earlier by exactly this many minutes.
    """
    c = close_time(d)
    return max(0, RTH_CLOSE_HM[0] * 60 + RTH_CLOSE_HM[1] - (c.hour * 60 + c.minute))


def _selftest() -> int:
    F = []

    def ck(n, ok, det=""):
        print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f"  — {det}" if det else ""))
        if not ok:
            F.append(n)

    D = _dt.date
    ck("M1  Labor Day 2026-09-07 is NOT a trading day",
       not is_trading_day(D(2026, 9, 7)))
    ck("M2  the next weekday IS", is_trading_day(D(2026, 9, 8)))
    ck("M3  Saturday is not", not is_trading_day(D(2026, 9, 5)))
    # 🔴 M4 IS THE ONE THAT MATTERS. A date past the list must be TRADING.
    ck("M4  a date BEYOND coverage is a TRADING day — fails toward trading",
       is_trading_day(D(2055, 3, 15)) and not is_covered(D(2055, 3, 15)),
       "a forgotten refresh costs armed mornings, never a dark fleet")
    ck("M4b and a weekend beyond coverage is still closed",
       not is_trading_day(D(2055, 3, 13)))
    ck("M7  2027-12-31 is closed — NYD 2028 is a Saturday, observed in the "
       "PREVIOUS year", not is_trading_day(D(2027, 12, 31)))
    ck("M8  2028 is covered — the old cliff", is_trading_day(D(2028, 1, 3))
       and not is_trading_day(D(2028, 1, 17)), "MLK 2028")
    ck("M5  coverage() now reaches 2050", coverage() == (2026, 2050),
       str(coverage()))
    ck("M6  a half day is a TRADING day", is_trading_day(D(2026, 11, 27)),
       "DEP.12")
    ck("M9  2026-11-27 closes at 13:00, shift 180 min",
       close_time(D(2026, 11, 27)) == _dt.time(13, 0)
       and close_shift_minutes(D(2026, 11, 27)) == 180, "r478 / DEP.12")
    ck("M10 a full day closes at 16:00, shift 0",
       close_time(D(2026, 11, 25)) == _dt.time(16, 0)
       and close_shift_minutes(D(2026, 11, 25)) == 0 and not is_half_day(D(2026, 11, 25)))
    print()
    if F:
        print(f"market_calendar selftest: FAIL ({len(F)})")
        return 1
    print("market_calendar selftest: ALL PASS")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    t = _dt.datetime.now(ET).date()
    lo, hi = coverage()
    print(f"{t}  trading_day={is_trading_day(t)}  covered={is_covered(t)} "
          f"({lo}-{hi})")
    raise SystemExit(0 if is_trading_day(t) else 1)
