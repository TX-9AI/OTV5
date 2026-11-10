#!/usr/bin/env python3
"""
tools/capture_all.py  v5.7 — EVERYTHING TASTYTRADE SERVES THAT THE FEED DOES NOT ALREADY KEEP, INTO THE WAREHOUSE.
v5.7  2026-11-09  OTV5 r105 (CAP.7) — ONE STREAM PER BOX, AND A REFUSED SESSION WAITS ITS TURN. Measured on the fleet the
      night r104 landed: with 8 boxes running option-candles at OPT_STREAMS = 2 beside 6 backfill streams, NVDA's run
      died "The number of user sessions has exceeded the configured limit" - the account's DXLink sessions are shared by
      all 14 boxes (the limit sits near 15: r99 measured 10 of 13 refused with the feed up), so 14 boxes x 2 streams
      breaches it at the close. OPT_STREAMS = 1; and a stream refused for the session limit is retried after
      OPT_RETRY_S x attempt (up to OPT_RETRIES), so a box that starts while another still holds a session waits rather
      than abandoning the night. Any other error still ends the run (the state keeps every finished series).
v5.6  2026-11-09  OTV5 r104 (CAP.7) — THE DAY'S OPTION CANDLES, EVERY NIGHT, BEFORE TASTYTRADE ROLLS THEM OFF. dxFeed serves
      option Candle history for expired contracts, but only for a rolling window (measured 11-09 on the AMD/UNH boxes):
      1m from 09-27 (about 6 weeks), 5m from 08-11 (about 90 days), 1h from 07-01 or earlier, 1d the contract's life;
      and the `price=bid` / `price=ask` / `price=mark` candles - the ONLY historical quote series there is (no
      historical NBBO or greeks exist) - from about 10-27, two weeks. raw/chain_snapshots keeps the front chain every 5
      minutes; nothing kept each contract's 1-minute bars or its quote candles, so every day not pulled was lost for
      good. NEW mode `option-candles` (started by the conductor right after candles-recent, dtp r545, and by self_close):
      the box's own front-expiry chain for each day not yet captured (from the bot's data/chain_snapshots/<day>/,
      strikes within 15% of that morning's underlying), every series in OPT_SERIES, the most perishable first, at most
      OPT_CHUNK symbols per stream ("Your subscription size for event type 'Candle' is too big" above about 100, 11-09).
      Progress is kept per (day, series) in data/option_candles_state.json, so a run the takedown cuts short resumes at
      the next close. Key pulled=<ET day>_opt.csv.gz: never the `candles` key (the 11-09 backfill wrote
      pulled=<day>.csv.gz for option symbols) and never `_recent` - gate O3, the CAP.6 lesson.
v5.5  2026-11-08  OTV5 r102 (CAP.6) — A LIVE MARKET NEVER LET A STREAM END. _candles ended a pull after idle_s with no
      event, but every live update of the forming bar reset that clock: on the SPX box on a Sunday evening (CME futures
      open from 18:00 ET) the stream ran on to max_s (600 s) for EACH of the four lookbacks - 9 minutes and still in the
      first, measured. The same holds at 16:1x ET, when the futures still trade. Now only a bar the pull has not seen
      before resets the idle clock; an update to a known bar is still stored (the latest version wins) but does not.
v5.4  2026-11-08  OTV5 r101 (CAP.6) — EACH INTERVAL IS WRITTEN AS SOON AS ITS STREAM ENDS. v5.0-v5.3 collected all four
      lookbacks and wrote at the end, so a run cut short wrote NOTHING; on the SPX box (45 symbols: CONTEXT + futures)
      one run outlasted 300 s, the conductor's bound, and a takedown can stop any box first. Now 1d, 1d_eth, 1h, 5m are
      each written when their stream ends (dailies first), so a cut keeps what finished.
v5.3  2026-11-08  OTV5 r100 (CAP.6) — 🔴 candles-recent OVERWROTE THE BACKFILL. Both modes wrote
      raw/candles_full/interval=<i>/sym=<S>/pulled=<ET day>.csv.gz, so the first live candles-recent run (11-08 evening,
      ET day 2026-11-08 - the backfill's day) replaced 36 backfill objects (12 symbols x 1d / 1h / 5m: history from 2023 /
      01-27 / 08-10) with its 21 / 5 / 3-day lookbacks. Restored the same evening by re-pulling the backfill ranges from
      TastyTrade (AMD's box). candles-recent now writes pulled=<day>_recent.csv.gz, a key `candles` never writes, so a
      lookback can never replace a history again (gate L2). Readers that take the newest key per prefix still sort it last.
v5.2  2026-11-08  OTV5 r99 (CAP.6) — MEASURED ON THE FLEET, r98's 16:12 SLOT WAS WRONG ON TWO COUNTS. (1) With optionsbot
      stopped and candle-feed still up, 10 of 13 boxes were REFUSED ("The number of user sessions has exceeded the
      configured limit"); with candle-feed stopped too, 13 of 13 pulled. The feed's streamer is the one that counts, and at
      16:12 it is still running (the conductor stops it only after the drain verifies). So candles-recent now refuses
      while optionsbot OR candle-feed is active, and its timer is REMOVED (it would skip every night); the conductor
      starts it on each verified box right after it stops both (dtp r543), and self_close step 2c does the same on a box
      that closes itself. (2) On the SPX box the front-futures lookup went through tasty_client.run_async (its own event
      loop), binding the session's HTTP pool to that loop, so the stream in asyncio.run failed "bound to a different
      event loop". The lookup now awaits session._get inside the SAME loop as the streams (pick_front is the pure rule).
v5.1  2026-11-08  OTV5 r98 (CAP.6) — raw/candles_full HAD NO FORWARD CAPTURE, AND TASTYTRADE LAGS THE RTH DAILY. The
      earnings study found the equity daily candles ending 11-04. Measured on AMD's box 11-08: the {=d,tho=true} daily
      history TastyTrade serves stops two sessions back for every equity and ETF (NVDA/AMD/SPY 1d: ..11-04 on a Sunday),
      while SPX/VIX and the futures are current and the extended-hours {=d} daily is current for all (NVDA ..11-06).
      r94 only ever ran `candles` by hand (the 11-08 backfill), so nothing would ever fill those days. NEW mode
      `candles-recent` (v5.2: started by the conductor / self_close once optionsbot AND candle-feed are stopped; the r98
      16:12 timer is gone): one DXLink stream at a time, so the streamer-session count never goes above the
      trading-hours count. Each run re-pulls a LOOKBACK - 1d RTH 21 days, 1d extended hours 21 days
      (interval=1d_eth), 1h 5 days, 5m 3 days - so a bar TastyTrade publishes late is picked up by a later night, and
      the SPX box also pulls the CONTEXT symbols and the front-month futures (resolved from /instruments/futures each run).
v5.0  2026-11-08  OTV5 r94 (CAP.1). The operator, 2026-11-08: "download fucking everything whether we use it or not
      ... We might need it later." / "If they offer it, we better be downloading it. Non-negotiable. It all goes to the
      fucking warehouse."

RECORDING ONLY. No trading code imports this file and it imports no trading code beyond data.tasty_client.get_session
(gate tests/check_capture_all.py C1/C2 prove both directions). It runs in its OWN process from its own timer, REST
only in the scheduled modes (no DXLink stream, so the streamer-session ceiling and the per-node limit are untouched).
The `candles` mode opens ONE DXLink stream and is for a stopped bot only (backfill / off-hours); the timer never runs it.

Every response is stored RAW (the JSON TastyTrade returned, or every Candle field), gzip, one object per call, so no
field is dropped by a model or a column list. Objects go straight to S3 from a local spool that is deleted on a
successful PUT (a failed PUT leaves the file for the next run; retention_purge removes spool files older than 3 days).

MODES (each is one call of this script; the timers run metrics / chain / events; candles-recent is started by the
conductor and by self_close after the close):
  metrics  /market-metrics for the box family + CONTEXT symbols: IV index/rank/percentile (tw + tos), IV per expiry,
           IV30, HV30/60/90, IV-HV, beta, corr_spy, liquidity, earnings + dividend dates, borrow rate, lendability...
           -> raw/market_metrics/dt=<ET day>/sym=<box>/<HHMMSS>.json.gz
  chain    the FULL nested option chain (every expiry, every strike) and /market-data/by-type for every option symbol
           in batches of 100: bid/ask/sizes, mark, mid, last, volume, OPEN INTEREST, day OHLC, prev close, halts,
           AND delta/gamma/theta/vega/rho, volatility (IV) and theo-price per contract (measured 11-08: the REST
           by-type row carries them), so every expiry gets the greeks raw/chain_snapshots keeps for the front only.
           --max-dte limits expiries (default: all). -> raw/chain_rest/dt=/sym=/<HHMMSS>.json.gz (+ the nested chain
           itself once per day -> raw/chain_listing/dt=/sym=/chain.json.gz)
  events   earnings-report history + dividend history per equity symbol, and the risk-free rate.
           -> raw/corporate_events/kind=<earnings|dividends|risk_free>/sym=<SYM>/pulled=<ET day>.json.gz
  candles  DXLink Candle with EVERY field (OHLC, volume, vwap, bid/ask volume, imp_volatility, open_interest, count)
           for --symbols at --interval from --since. -> raw/candles_full/interval=<i>/sym=<SYM>/pulled=<day>.csv.gz
           (the feed's raw/candles keeps OHLCV only: vwap / bid-ask volume / imp_volatility / OI were never stored).
  candles-recent  the same Candle fields over a LOOKBACK (RECENT below), with the bot AND the feed stopped (it refuses
           while either is active): the box's own symbol, plus CONTEXT and the front futures on the SPX box.
           -> raw/candles_full/interval=<1d|1d_eth|1h|5m>/sym=<SYM>/pulled=<ET day>_recent.csv.gz (v5.3: never the
              `candles` key, which r98-r99 shared and so overwrote the backfill)
  option-candles  (v5.6) every Candle field for each contract of the box's front-expiry chain, strikes within 15% of
           spot, for each day not yet captured: 1m quote candles (bid / ask / mark), then 1m, 5m, 1h, 1d trade candles,
           with the bot and the feed stopped (refuses like candles-recent).
           -> raw/candles_full/interval=<1m_bid|1m_ask|1m_mark|1m|5m|1h|1d>/sym=.<ROOT><YYMMDD><C|P><strike>/
              pulled=<ET day>_opt.csv.gz, and one run manifest -> raw/option_candles_runs/dt=<ET day>/sym=<box>/HHMMSS.json.gz

Usage:  python3 tools/capture_all.py metrics|chain|events|candles-recent|option-candles [--symbols A,B] [--max-dte N] [--dry-run] [--force]
        python3 tools/capture_all.py candles --symbols SPX,VIX --interval 1d --since 2015-01-01
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import gzip
import io
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ET = ZoneInfo("America/New_York")
BUCKET = os.environ.get("OT_S3_BUCKET", "vertigo-warehouse-tx9ai")
SPOOL = os.path.join(ROOT, "data", "capture_spool")
BATCH = 100                     # /market-data/by-type: combined limit across all types is 100
PAUSE_S = 0.5                   # between REST batches: the bot's own REST calls share the account's rate budget

# Index underlyings are fetched as "index" in /market-data/by-type and have no earnings / dividends.
INDEXES = {"SPX", "VIX", "VIX9D", "VVIX", "VIX3M", "NDX", "RUT", "XSP"}
# Context symbols captured once, by the SPX box (the same ownership rule s3_push applies to VIX).
CONTEXT = ["VIX", "VIX9D", "VVIX", "VIX3M", "SPY", "QQQ", "IWM", "DIA", "TLT", "GLD", "USO", "HYG",
           "XLK", "XLF", "XLE", "XLV", "XLY", "XLC", "XLI", "XLP", "XLU", "XLB", "XLRE", "SMH"]
# candles-recent: (interval, lookback days, extended hours, stored interval label). The RTH daily lags two sessions at
# TastyTrade for equities (measured 11-08), so 21 days of lookback re-pulls it until it has been published.
RECENT = (("1d", 21, False, "1d"), ("1d", 21, True, "1d_eth"), ("1h", 5, False, "1h"), ("5m", 3, False, "5m"))
# Front-month futures the SPX box pulls (the 11-08 backfill's set), resolved to streamer symbols each run.
FUT_PRODUCTS = ("ES", "NQ", "RTY", "YM", "ZN", "ZB", "CL", "GC", "6E", "VX")
# option-candles (v5.6): (interval string asked, stored label), most perishable first - the quote candles keep about two
# weeks, 1m about six, 5m about ninety days, 1h and 1d longer (measured 11-09).
OPT_SERIES = (("1m,price=bid", "1m_bid"), ("1m,price=ask", "1m_ask"), ("1m,price=mark", "1m_mark"),
              ("1m", "1m"), ("5m", "5m"), ("1h", "1h"), ("1d", "1d"))
OPT_CHUNK = 60                  # symbols per stream: above about 100 dxFeed refuses the subscription (11-09)
OPT_BAND = 0.15                 # strikes within 15% of the morning's underlying
OPT_CATCHUP_DAYS = 12           # a day missed is retried for this many calendar days (the quote candles keep about 14)
OPT_IDLE_S = 8.0                # history arrives in one burst; a closed contract has no live updates
OPT_STREAMS = 1                 # streams at once per box: the account's session limit (~15) is shared by all 14 boxes (v5.7)
OPT_RETRIES = 6                 # a stream refused for the session limit is retried this many times ...
OPT_RETRY_S = 20.0              # ... after OPT_RETRY_S x attempt seconds
OPT_STATE = os.path.join(ROOT, "data", "option_candles_state.json")
CHAIN_DIR = os.path.join(ROOT, "data", "chain_snapshots")


def _load_service_env() -> int:
    """The bot unit's Environment into THIS process only (never printed): get_session reads its login from it."""
    try:
        env = subprocess.run(["systemctl", "show", "optionsbot", "-p", "Environment", "--value"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return 0
    n = 0
    for kv in shlex.split(env):
        if "=" in kv:
            k, v = kv.split("=", 1)
            os.environ.setdefault(k, v)
            n += 1
    return n


def box_symbol() -> str:
    s = (os.environ.get("OT_INSTRUMENT") or "").strip().upper()
    return "SPX" if s in ("SPXW", "SPX") else s


def et_now() -> datetime:
    return datetime.now(ET)


# ── storage ────────────────────────────────────────────────────────────────────────────────────────────────────────
def spool_put(key: str, payload: bytes, dry: bool) -> str:
    """Write gz bytes to the spool, PUT it, delete on success. Returns 'PUT' / 'KEPT' / 'DRY'."""
    path = os.path.join(SPOOL, key.replace("/", "__"))
    os.makedirs(SPOOL, exist_ok=True)
    with open(path + ".tmp", "wb") as fh:
        fh.write(payload)
    os.replace(path + ".tmp", path)
    if dry:
        os.remove(path)
        return "DRY"
    try:
        import boto3
        boto3.client("s3").put_object(Bucket=BUCKET, Key=key, Body=payload)
    except Exception as e:                                    # kept for the next run's flush
        print(f"PUT FAIL {key}: {type(e).__name__}", flush=True)
        return "KEPT"
    os.remove(path)
    return "PUT"


def flush_spool(dry: bool) -> int:
    """Re-PUT anything a previous run could not deliver."""
    if dry or not os.path.isdir(SPOOL):
        return 0
    n = 0
    for f in sorted(os.listdir(SPOOL)):
        if f.endswith(".tmp"):
            continue
        p = os.path.join(SPOOL, f)
        try:
            import boto3
            with open(p, "rb") as fh:
                boto3.client("s3").put_object(Bucket=BUCKET, Key=f.replace("__", "/"), Body=fh.read())
            os.remove(p)
            n += 1
        except Exception:
            pass
    return n


def gz_json(obj) -> bytes:
    return gzip.compress(json.dumps(obj, default=str, separators=(",", ":")).encode())


def meta(mode: str, **kw) -> dict:
    return {"source": "tastytrade", "mode": mode, "captured_at": datetime.now(timezone.utc).isoformat(),
            "box": box_symbol(), "tool": "tools/capture_all.py v5.7", **kw}


# ── REST modes ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _get(session, path, params=None):
    from data.tasty_client import run_async
    return run_async(session._get(path, params=params))


def do_metrics(session, symbols, dry):
    data = _get(session, "/market-metrics", {"symbols": ",".join(symbols)})
    now = et_now()
    key = f"raw/market_metrics/dt={now.date()}/sym={box_symbol()}/{now:%H%M%S}.json.gz"
    r = spool_put(key, gz_json({"meta": meta("metrics", symbols=symbols), "response": data}), dry)
    items = len((data or {}).get("items", []))
    print(f"METRICS {r} items={items} key={key}", flush=True)
    return items


def _nested_chain(session, sym):
    path_sym = sym.replace("/", "%2F")
    return _get(session, f"/option-chains/{path_sym}/nested")


def _option_symbols(chain_json, max_dte):
    today = et_now().date()
    out = []
    for ch in (chain_json or {}).get("items", []):
        for ex in ch.get("expirations", []):
            try:
                dte = (date.fromisoformat(ex.get("expiration-date")) - today).days
            except Exception:
                dte = 0
            if max_dte is not None and dte > max_dte:
                continue
            for st in ex.get("strikes", []):
                for k in ("call", "put"):
                    if st.get(k):
                        out.append(st[k])
    return out


def do_chain(session, symbols, max_dte, dry):
    total = 0
    now = et_now()
    for sym in symbols:
        t0 = time.time()
        chain = _nested_chain(session, sym)
        lkey = f"raw/chain_listing/dt={now.date()}/sym={sym}/chain.json.gz"
        spool_put(lkey, gz_json({"meta": meta("chain_listing", symbol=sym), "response": chain}), dry)
        opts = _option_symbols(chain, max_dte)
        rows, fails = [], 0
        for i in range(0, len(opts), BATCH):
            part = opts[i:i + BATCH]
            try:
                d = _get(session, "/market-data/by-type", {"equity-option": part})
                rows.extend((d or {}).get("items", []))
            except Exception:
                fails += 1
            time.sleep(PAUSE_S)
        # the underlying's own quote rides along
        try:
            kind = "index" if sym in INDEXES else "equity"
            d = _get(session, "/market-data/by-type", {kind: [sym]})
            under = (d or {}).get("items", [])
        except Exception:
            under = []
        key = f"raw/chain_rest/dt={now.date()}/sym={sym}/{now:%H%M%S}.json.gz"
        body = gz_json({"meta": meta("chain", symbol=sym, max_dte=max_dte, asked=len(opts), batches_failed=fails,
                                     seconds=round(time.time() - t0, 1)),
                        "underlying": under, "options": rows})
        r = spool_put(key, body, dry)
        total += len(rows)
        print(f"CHAIN {r} {sym} asked={len(opts)} got={len(rows)} failed_batches={fails} "
              f"bytes={len(body)} s={time.time() - t0:.1f}", flush=True)
    return total


def do_events(session, symbols, dry):
    day = et_now().date()
    n = 0
    for sym in symbols:
        if sym in INDEXES:
            continue
        for kind, path in (("earnings", f"/market-metrics/historic-corporate-events/earnings-reports/{sym}"),
                           ("dividends", f"/market-metrics/historic-corporate-events/dividends/{sym}")):
            params = {"start-date": "1990-01-01"} if kind == "earnings" else None
            try:
                d = _get(session, path, params)
            except Exception as e:
                print(f"EVENTS {kind} {sym} FAIL {type(e).__name__}", flush=True)
                continue
            key = f"raw/corporate_events/kind={kind}/sym={sym}/pulled={day}.json.gz"
            r = spool_put(key, gz_json({"meta": meta("events", symbol=sym, kind=kind), "response": d}), dry)
            n += len((d or {}).get("items", []))
            print(f"EVENTS {r} {kind} {sym} items={len((d or {}).get('items', []))}", flush=True)
    try:
        d = _get(session, "/margin-requirements-public-configuration")
        rf = d.get("risk-free-rate") if isinstance(d, dict) else None
        key = f"raw/corporate_events/kind=risk_free/sym=ALL/pulled={day}.json.gz"
        spool_put(key, gz_json({"meta": meta("risk_free"), "response": d, "risk_free_rate": rf}), dry)
        print(f"EVENTS risk_free={rf}", flush=True)
    except Exception as e:
        print(f"EVENTS risk_free FAIL {type(e).__name__}", flush=True)
    return n


# ── DXLink candles, every field (stopped bot only) ─────────────────────────────────────────────────────────────────
CANDLE_FIELDS = ["event_symbol", "time", "sequence", "count", "open", "high", "low", "close", "volume", "vwap",
                 "bid_volume", "ask_volume", "imp_volatility", "open_interest", "event_flags", "index"]


async def _candles(session, symbols, interval, since, idle_s=20.0, max_s=600.0, eth=False):
    from tastytrade import DXLinkStreamer
    from tastytrade.dxfeed import Candle
    got = {s: {} for s in symbols}
    async with DXLinkStreamer(session) as streamer:
        await streamer.subscribe_candle(symbols, interval, start_time=since, extended_trading_hours=eth)
        loop = asyncio.get_event_loop()
        t0 = last = loop.time()
        while loop.time() - last < idle_s and loop.time() - t0 < max_s:
            try:
                c = await asyncio.wait_for(streamer.get_event(Candle), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            base = (c.event_symbol or "").split("{", 1)[0]
            if base in got and c.time:
                new_bar = int(c.time) not in got[base]
                got[base][int(c.time)] = {k: getattr(c, k, None) for k in CANDLE_FIELDS}
                if new_bar:                      # v5.5: a live update of a known bar does not hold the stream open
                    last = loop.time()
    return got


def _write_candles(got, label, dry, suffix=""):
    """One raw/candles_full object per symbol: every Candle field, sorted by time. suffix "_recent" (candles-recent)
    keeps a lookback from ever sharing a key with a `candles` history pulled the same day (v5.3)."""
    day = et_now().date()
    for sym, bars in got.items():
        if not bars:
            print(f"CANDLES {sym} {label} 0 bars served", flush=True)
            continue
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(CANDLE_FIELDS + ["source", "pulled_at"])
        pulled = datetime.now(timezone.utc).isoformat()
        for t in sorted(bars):
            w.writerow([bars[t][k] for k in CANDLE_FIELDS] + ["dxfeed_tastytrade", pulled])
        safe = sym.replace("/", "_").replace(":", "_")
        key = f"raw/candles_full/interval={label}/sym={safe}/pulled={day}{suffix}.csv.gz"
        r = spool_put(key, gzip.compress(buf.getvalue().encode()), dry)
        ts = sorted(bars)
        iv = sum(1 for t in ts if bars[t].get("imp_volatility") not in (None, 0) and str(bars[t]["imp_volatility"]) != "NaN")
        first = datetime.fromtimestamp(ts[0] / 1000, timezone.utc).date()
        last = datetime.fromtimestamp(ts[-1] / 1000, timezone.utc).date()
        print(f"CANDLES {r} {sym} {label} rows={len(ts)} {first}..{last} with_iv={iv}", flush=True)


def do_candles(session, symbols, interval, since, dry):
    _write_candles(asyncio.run(_candles(session, symbols, interval, since)), interval, dry)


def streams_active() -> bool:
    """optionsbot or candle-feed running? candles-recent never opens a stream beside them: measured 11-08, with the
    feed up 10 of 13 boxes were refused at the user-session limit; with both stopped 13 of 13 pulled."""
    try:
        for unit in ("optionsbot", "candle-feed"):
            if subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True,
                              timeout=10).stdout.strip() == "active":
                return True
        return False
    except Exception:
        return True                     # unknown counts as active: never risk a session while it may be trading


def pick_front(items):
    """The front contract of one product's /instruments/futures items: the active month, else the nearest expiry;
    None when nothing is live (never guessed)."""
    live = [i for i in items if i.get("streamer-symbol") and not i.get("is-closing-only")]
    act = [i for i in live if i.get("active-month")] or sorted(
        (i for i in live if i.get("expiration-date")), key=lambda i: i["expiration-date"])[:1]
    return act[0]["streamer-symbol"] if act else None


async def _front_futures(session, products=FUT_PRODUCTS):
    """Front-month streamer symbols, fetched in THIS event loop (v5.2: run_async's own loop bound the session's HTTP
    pool to it and the stream then failed). A product that does not answer is skipped and named."""
    out = []
    for p in products:
        try:
            items = ((await session._get("/instruments/futures", params={"product-code[]": [p]})) or {}).get("items", [])
        except Exception as e:
            print(f"FUTURES {p} lookup failed: {type(e).__name__}", flush=True)
            continue
        sym = pick_front(items)
        if sym:
            out.append(sym)
        else:
            print(f"FUTURES {p} no active contract", flush=True)
    return out


async def _candles_recent(session, symbols, today, futures=False, sink=None):
    """Each lookback in RECENT order; `sink(label, got)` is called as soon as its stream ends (v5.4), so a run cut short
    keeps every interval that finished. Returns {label: got} as well."""
    if futures:
        symbols = list(symbols) + [f for f in await _front_futures(session) if f not in symbols]
    got = {}
    for iv, days, eth, label in RECENT:
        since = datetime.combine(today - timedelta(days=days), datetime.min.time(), tzinfo=timezone.utc)
        got[label] = await _candles(session, symbols, iv, since, eth=eth)
        if sink is not None:
            sink(label, got[label])
    return got


def do_candles_recent(session, symbols, dry, futures=False):
    asyncio.run(_candles_recent(session, symbols, et_now().date(), futures,
                                sink=lambda label, g: _write_candles(g, label, dry, suffix="_recent")))


# ── option candles (v5.6) ──────────────────────────────────────────────────────────────────────────────────────────
def occ_to_streamer(occ: str) -> str:
    """'UNH   261113C00395000' -> '.UNH261113C395'; 'SPXW  261109P07402500' -> '.SPXW261109P7402.5'."""
    root, ymd, cp, k = occ[:6].strip(), occ[6:12], occ[12], int(occ[13:]) / 1000
    return f".{root}{ymd}{cp}{int(k) if k == int(k) else ('%g' % k)}"


def front_chain(day, chain_dir=None, band=OPT_BAND):
    """(expiry, [streamer symbols]) of the box's front-expiry chain on `day`, from the first snapshot the bot wrote
    that day (data/chain_snapshots/<day>/<SYM>.jsonl.gz), strikes within `band` of its underlying. None when the day
    has no snapshot (no session, or the box was down) - never guessed."""
    d = os.path.join(chain_dir or CHAIN_DIR, str(day))
    try:
        files = sorted(f for f in os.listdir(d) if f.endswith(".jsonl.gz"))
    except OSError:
        return None
    for f in files:
        try:
            with gzip.open(os.path.join(d, f), "rt") as fh:
                for line in fh:
                    rec = json.loads(line)
                    u = float(rec.get("underlying") or 0)
                    if not u or not rec.get("contracts"):
                        continue
                    syms = sorted({occ_to_streamer(c["occ"]) for c in rec["contracts"]
                                   if c.get("occ") and abs(float(c.get("strike") or int(c["occ"][13:]) / 1000) - u)
                                   <= band * u})
                    return rec.get("expiry"), syms
        except (OSError, ValueError, KeyError, EOFError):
            continue
    return None


def _opt_state(path=None) -> dict:
    try:
        with open(path or OPT_STATE) as fh:
            st = json.load(fh)
        return st if isinstance(st.get("done"), dict) else {"done": {}}
    except (OSError, ValueError, AttributeError):
        return {"done": {}}


def _opt_save(st, path=None):
    path = path or OPT_STATE
    st["done"] = {d: v for d, v in st["done"].items()
                  if d >= str(et_now().date() - timedelta(days=OPT_CATCHUP_DAYS + 7))}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w") as fh:
        json.dump(st, fh, indent=1, sort_keys=True)
    os.replace(path + ".tmp", path)


def option_plan(today, st, chain_dir=None):
    """[(label, interval, since_day, [symbols], [days])] for every series still owed on a day in the catch-up window,
    most perishable first. A contract on several owed days is asked ONCE from the earliest (one key per contract)."""
    plan = []
    chains = {}
    for i in range(OPT_CATCHUP_DAYS, -1, -1):
        day = str(today - timedelta(days=i))
        fc = front_chain(day, chain_dir)
        if fc:
            chains[day] = fc[1]
    for interval, label in OPT_SERIES:
        owed = [d for d in sorted(chains) if label not in st["done"].get(d, [])]
        if not owed:
            continue
        syms = sorted({s for d in owed for s in chains[d]})
        if syms:
            plan.append((label, interval, owed[0], syms, owed))
    return plan


def _session_limited(exc) -> bool:
    """True when `exc` (or anything nested in an ExceptionGroup) is dxFeed's user-session-limit refusal."""
    if "number of user sessions has exceeded" in str(exc):
        return True
    return any(_session_limited(e) for e in getattr(exc, "exceptions", ()) or ())


async def _pull_retrying(session, part, interval, since, sleep=asyncio.sleep):
    for attempt in range(1, OPT_RETRIES + 1):
        try:
            return await _candles(session, part, interval, since, idle_s=OPT_IDLE_S)
        except Exception as exc:                                  # noqa: BLE001 - only the session limit is retried
            if not _session_limited(exc) or attempt == OPT_RETRIES:
                raise
            print(f"OPTION-CANDLES session limit - retry {attempt} in {OPT_RETRY_S * attempt:.0f}s", flush=True)
            await sleep(OPT_RETRY_S * attempt)


async def _option_candles(session, plan, dry, st, state_path, streams=None):
    """Every stream in ONE event loop (v5.2's lesson: a second asyncio.run binds the session's HTTP pool to a new loop
    and the next stream fails). `streams` chunks at a time - never more sessions than the bot and the feed hold all day.
    Each chunk is written as its stream ends; a series is marked done for its days only once every chunk is written."""
    streams = streams or OPT_STREAMS
    n = 0
    summary = []
    for label, interval, since_day, syms, days in plan:
        t0 = time.time()
        since = datetime.combine(date.fromisoformat(since_day), datetime.min.time(), tzinfo=timezone.utc)
        parts = [syms[i:i + OPT_CHUNK] for i in range(0, len(syms), OPT_CHUNK)]
        for j in range(0, len(parts), streams):
            for got in await asyncio.gather(*(_pull_retrying(session, part, interval, since)
                                              for part in parts[j:j + streams])):
                _write_candles(got, label, dry, suffix="_opt")
                n += sum(1 for v in got.values() if v)
        if not dry:
            for d in days:
                st["done"].setdefault(d, [])
                if label not in st["done"][d]:
                    st["done"][d].append(label)
            _opt_save(st, state_path)
        summary.append({"label": label, "days": days, "contracts": len(syms), "seconds": round(time.time() - t0)})
        print(f"OPTION-CANDLES {label} days={','.join(days)} contracts={len(syms)} s={time.time() - t0:.0f}", flush=True)
    return n, summary


def _opt_manifest(plan_summary, served, dry):
    """One small object per run, so a reader (dtp morning_check) can tell a night that ran from one that never started
    - the CAP.6 failure (11-09: candles-recent never started on any box, and nothing said so)."""
    now = et_now()
    key = f"raw/option_candles_runs/dt={now.date()}/sym={box_symbol()}/{now:%H%M%S}.json.gz"
    return spool_put(key, gz_json({"meta": meta("option-candles"), "series": plan_summary,
                                   "contracts_served": served}), dry)


def do_option_candles(session, dry, today=None, chain_dir=None, state_path=None):
    today = today or et_now().date()
    st = _opt_state(state_path)
    plan = option_plan(today, st, chain_dir)
    if not plan:
        print("OPTION-CANDLES nothing owed (no unsent day with a chain snapshot in the window)", flush=True)
        _opt_manifest([], 0, dry)
        return 0
    served, summary = asyncio.run(_option_candles(session, plan, dry, st, state_path))
    print(f"OPTION-CANDLES {_opt_manifest(summary, served, dry)} manifest series={len(summary)} served={served}",
          flush=True)
    return served


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["metrics", "chain", "events", "candles", "candles-recent", "option-candles",
                                         "flush"])
    ap.add_argument("--force", action="store_true", help="candles-recent: run even while optionsbot / candle-feed run")
    ap.add_argument("--symbols", default="")
    ap.add_argument("--max-dte", type=int, default=None)
    ap.add_argument("--interval", default="1d")
    ap.add_argument("--since", default="2015-01-01")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    _load_service_env()
    me = box_symbol()
    if a.symbols:
        syms = [s.strip().upper() for s in a.symbols.split(",") if s.strip()]
    else:
        syms = [me] + (CONTEXT if me == "SPX" and a.mode in ("metrics", "events") else [])
    if not syms or syms == [""]:
        print("no symbol: OT_INSTRUMENT unset and no --symbols", flush=True)
        return 2
    flushed = flush_spool(a.dry_run)
    if flushed:
        print(f"FLUSH re-put {flushed} spooled object(s)", flush=True)
    if a.mode == "flush":
        return 0
    if a.mode in ("candles-recent", "option-candles") and not a.force and streams_active():
        print(f"{a.mode.upper()} SKIP optionsbot or candle-feed is active - no extra DXLink session beside them; a later "
              "run's lookback covers today", flush=True)
        return 0
    from data.tasty_client import get_session
    session = get_session()
    if a.mode == "metrics":
        do_metrics(session, syms, a.dry_run)
    elif a.mode == "chain":
        do_chain(session, syms, a.max_dte, a.dry_run)
    elif a.mode == "events":
        do_events(session, syms, a.dry_run)
    elif a.mode == "candles":
        since = datetime.fromisoformat(a.since).replace(tzinfo=timezone.utc)
        do_candles(session, syms, a.interval, since, a.dry_run)
    elif a.mode == "candles-recent":
        spx = me == "SPX" and not a.symbols
        if spx:
            syms = syms + [c for c in CONTEXT if c not in syms]
        do_candles_recent(session, syms, a.dry_run, futures=spx)
    elif a.mode == "option-candles":
        do_option_candles(session, a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
