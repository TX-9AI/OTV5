#!/usr/bin/env python3
"""
tools/capture_all.py  v5.2 — EVERYTHING TASTYTRADE SERVES THAT THE FEED DOES NOT ALREADY KEEP, INTO THE WAREHOUSE.
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
           -> raw/candles_full/interval=<1d|1d_eth|1h|5m>/sym=<SYM>/pulled=<ET day>.csv.gz

Usage:  python3 tools/capture_all.py metrics|chain|events|candles-recent [--symbols A,B] [--max-dte N] [--dry-run] [--force]
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
            "box": box_symbol(), "tool": "tools/capture_all.py v5.2", **kw}


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
                got[base][int(c.time)] = {k: getattr(c, k, None) for k in CANDLE_FIELDS}
                last = loop.time()
    return got


def _write_candles(got, label, dry):
    """One raw/candles_full object per symbol: every Candle field, sorted by time."""
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
        key = f"raw/candles_full/interval={label}/sym={safe}/pulled={day}.csv.gz"
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


async def _candles_recent(session, symbols, today, futures=False):
    if futures:
        symbols = list(symbols) + [f for f in await _front_futures(session) if f not in symbols]
    got = {}
    for iv, days, eth, label in RECENT:
        since = datetime.combine(today - timedelta(days=days), datetime.min.time(), tzinfo=timezone.utc)
        got[label] = await _candles(session, symbols, iv, since, eth=eth)
    return got


def do_candles_recent(session, symbols, dry, futures=False):
    for label, g in asyncio.run(_candles_recent(session, symbols, et_now().date(), futures)).items():
        _write_candles(g, label, dry)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["metrics", "chain", "events", "candles", "candles-recent", "flush"])
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
    if a.mode == "candles-recent" and not a.force and streams_active():
        print("CANDLES-RECENT SKIP optionsbot or candle-feed is active - no extra DXLink session beside them; a later "
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
