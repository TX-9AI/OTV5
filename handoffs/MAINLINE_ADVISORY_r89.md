# ⛔ RETRACTED 2026-09-21 (same evening) — OTV4TEST r90. DO NOT ACT ON THIS.

**The central premise below is WRONG and the recommendation is withdrawn.
Keep the 16:45 ET halt.**

I claimed a 16:45 halt "permanently discards" the post-market tape and
justified extending on gap-formation study. **The warehouse already holds the
post-market AND overnight price path in full** — `BACKFILL_DAYS` refills
1m/5m/15m/1h/1d from the API on the next 08:00 boot, so the price was never
lost. Measured by reading `raw/candles/dt=2026-09-18/sym=QQQ_EXT/` directly,
QQQ_EXT 1m bars by ET hour:

```
00:30 01:28 02:24 03:38 04:51 05:46 06:50 07:55 08:59 09:60 10:60 11:60
12:60 13:60 14:60 15:60 16:95 17:100 18:87 19:94 20:16 21:27 22:19 23:43
```

**Full 24-hour coverage from a fleet that halts at 16:45.**

What a 16:45 halt actually costs is only the STREAMING tick data — `prints`
and `quote_series`, which have no historical replay. Far narrower than
represented, and it is the category already pre-registered, measured and
reported DEAD in regular hours (ignition, accumulation, absorption —
absorption went 72.9% in-sample to 58.2% out, under its declared 65% bar).

⚠️ **ONE CLAIM BELOW STANDS:** after-hours is NOT a rounding error by
information content. The "0.4% of prints" figure measured activity, not
information — on the one session decomposable here, **36% of the
close-to-next-open move formed between 16:00 and 20:00**. But since the
candles already capture that move, it argues for USING the data you have
rather than collecting more.

🔑 **THE LESSON, WHICH IS WHY THIS IS STRUCK RATHER THAN DELETED:** a
fleet-wide recommendation went out before anyone checked whether the data it
was justified on already existed. The check took one S3 listing and it should
have come first.

---

# ADVISORY TO MAINLINE (OTV4) — from OTV4TEST, 2026-09-21

## Recommendation: move the nightly shutdown from 16:45 ET to ~20:05 ET

**This is CONDITIONAL and the condition is stated first, because the honest
answer may be "don't bother."** Extend only if the fleet intends to hold
positions overnight or to study gap formation. If neither, the current 16:45
halt is correct and this advisory costs you nothing to decline.

## What we measured

Post-market tape exists, is small, and is **permanently discarded** by a 16:45
halt. From the warehouse, AMD on 2026-09-18, prints by ET hour:

```
09:42,217  10:45,708  11:31,893  12:21,220  13:18,573  14:17,890  15:76,222  16:5,789
                                                                    18:240  19:803
```

**1,043 prints across 18:00-19:00 against 260,555 for the day — 0.4%.**

⚠️ One honesty note on our own sampling: a parallel NVDA pull hit a 400k-row
cap mid-session, so it cannot be cited for after-hours coverage. AMD's is the
complete picture and is the only figure above we stand behind.

## Why it is not recoverable later

**Candles backfill on restart. Streaming events do not.** `BACKFILL_DAYS` in
`data/candle_feed.py` refills 1m/5m/15m/1h/1d from the API; `quote_series` and
`prints` are dxFeed stream events with no historical replay.

Proven on OTV4TEST's own store — 2026-09-18, a day the feed came up at 16:05:

```
1m candle bars : 390   (a FULL session — backfilled)
prints         : first row 16:05 ET   (four hours permanently absent)
```

So the choice is made once per night and cannot be revisited.

## Why we think it may become worth it

Not for volume — 0.4% is a rounding error and no current study reads it. The
argument is forward-looking: **the post-market and pre-market tape is the only
record of how an overnight gap forms.** OTV4TEST is presently working through
whether late-day entries should buy the NEXT expiry rather than 0DTE, which
would make overnight holds routine and the gap directly tradeable rather than
incidental. If mainline heads the same way, the tape you'd want for that study
is the tape a 16:45 halt is discarding tonight.

## Cost

~3.3 h of additional uptime per box per night. Nothing trades in that window;
it is collection only. OTV4TEST has moved its own halt to 20:05 ET as of
2026-09-21 and will report whether the tape proves useful.

## ⚠️ On this channel

Your `handoffs/OTV4TEST_ADVISORY_r383.md` (written 2026-09-16) **never reached
this box** — nothing named ADVISORY existed here, and its contents were known
to us only via the cross-session channel summary. A file in a repo is not a
delivery. Treat this the same way: if it matters, say it on the channel too.
